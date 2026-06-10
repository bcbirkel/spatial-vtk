"""Waveform loading and trace-metadata helpers.

Purpose
-------
This module provides the public waveform I/O surface used by Spatial-VTK
workflows. It prefers ObsPy for real seismology formats and includes small
NumPy fallbacks for tests, examples, and simple arrays.

Usage examples
--------------
Load one file and inspect its trace metadata:
  ``stream = read_waveform_file("event.mseed")``
  ``metadata = trace_metadata_table(stream, event_id="ci123")``
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fractions import Fraction
import io
from pathlib import Path
from typing import Any
import pickle

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class WaveformPreprocessing:
    """Configured preprocessing applied before waveform QC, metrics, or figures.

    Parameters
    ----------
    lowpass_hz
        Optional lowpass cutoff in Hz. ``None`` means no configured lowpass.
    highpass_hz
        Optional highpass cutoff in Hz. ``None`` means no configured highpass.
    bandpass_low_hz, bandpass_high_hz
        Optional bandpass corner frequencies in Hz. Set both values to apply a
        bandpass instead of separate highpass/lowpass steps.
    resample_hz
        Optional target sampling rate in Hz after filtering.
    filter_order
        Butterworth filter order used for waveform filters.

    Returns
    -------
    WaveformPreprocessing
        Immutable preprocessing settings.
    """

    lowpass_hz: float | None = None
    highpass_hz: float | None = None
    bandpass_low_hz: float | None = None
    bandpass_high_hz: float | None = None
    resample_hz: float | None = None
    filter_order: int = 4


@dataclass(frozen=True)
class PreprocessedWaveform:
    """Preprocessed waveform samples and updated timing metadata.

    Parameters
    ----------
    data
        One-dimensional preprocessed samples.
    dt
        Updated sample interval in seconds.
    sampling_rate_hz
        Updated sampling rate in Hz.
    processing_label
        Human-readable description of the applied preprocessing.

    Returns
    -------
    PreprocessedWaveform
        Immutable preprocessing result.
    """

    data: np.ndarray
    dt: float
    sampling_rate_hz: float
    processing_label: str


def read_waveform_file(path: str | Path, format: str | None = None) -> Any:
    """Read one waveform file.

    Parameters
    ----------
    path
        Waveform path. ObsPy-supported formats are read with ObsPy when it is
        installed. ``.npz`` and ``.npy`` files are supported without ObsPy.
    format
        Optional format string forwarded to ``obspy.read``.

    Returns
    -------
    object
        ObsPy ``Stream`` when ObsPy handles the file, a list of lightweight
        mapping traces for NumPy files, or the raw object returned by ObsPy for
        non-stream readers.
    """

    source = Path(path).expanduser()
    if not source.exists():
        raise FileNotFoundError(f"Waveform file does not exist: {source}")
    suffix = source.suffix.lower()
    if suffix in {".npz", ".npy"}:
        return _read_numpy_waveform(source)
    if suffix in {".pkl", ".pickle"}:
        return _read_pickle_waveform(source)
    if suffix == ".asdf":
        return _read_asdf_waveform(source)
    obspy = _optional_obspy()
    if obspy is None:
        raise ImportError(
            f"Reading {source.suffix or 'this waveform format'} requires ObsPy. "
            "Install obspy or provide .npz/.npy waveform arrays."
        )
    kwargs = {"format": format} if format else {}
    return obspy.read(str(source), **kwargs)


class _NumpyCompatUnpickler(pickle.Unpickler):
    """Unpickle NumPy objects across NumPy 1.x and 2.x module paths."""

    def find_class(self, module: str, name: str) -> Any:
        if module.startswith("numpy._core"):
            module = "numpy.core" + module[len("numpy._core") :]
        return super().find_class(module, name)


def _read_pickle_waveform(source: Path) -> Any:
    """Read waveform pickle files with a NumPy 1/2 module-path fallback."""

    payload = source.read_bytes()
    try:
        return pickle.loads(payload)
    except ModuleNotFoundError as exc:
        missing = str(exc)
        if "numpy._core" not in missing:
            raise
        return _NumpyCompatUnpickler(io.BytesIO(payload)).load()


def _read_asdf_waveform(source: Path) -> Any:
    """Read all waveform tags from one ASDF file into an ObsPy Stream."""

    try:
        import pyasdf
        from obspy import Stream
    except Exception as exc:
        raise RuntimeError("pyasdf and ObsPy are required to read ASDF waveform files.") from exc

    stream = Stream()
    with pyasdf.ASDFDataSet(str(source), mode="r") as dataset:
        for station_name in dataset.waveforms.list():
            station_waveforms = dataset.waveforms[station_name]
            for tag in station_waveforms.get_waveform_tags():
                try:
                    current = station_waveforms[tag]
                except Exception:
                    continue
                if current:
                    stream += current
    return stream


def load_waveform_collection(paths: Sequence[str | Path], format: str | None = None) -> Any:
    """Load several waveform files and combine them when possible.

    Parameters
    ----------
    paths
        File paths to load.
    format
        Optional ObsPy format forwarded to :func:`read_waveform_file`.

    Returns
    -------
    object
        Combined ObsPy stream when all inputs are ObsPy streams, otherwise a
        flat list of trace-like objects.
    """

    loaded = [read_waveform_file(path, format=format) for path in paths]
    if not loaded:
        return []
    first = loaded[0]
    if _is_obspy_stream_like(first):
        stream = first.copy()
        for item in loaded[1:]:
            stream += item
        return stream
    traces: list[Any] = []
    for item in loaded:
        if isinstance(item, list):
            traces.extend(item)
        elif _is_iterable_stream(item):
            traces.extend(list(item))
        else:
            traces.append(item)
    return traces


def select_waveform_trace(
    stream_or_path: Any,
    *,
    station: str | None = None,
    component: str | None = None,
    prefer_channel_prefixes: Sequence[str] = ("BH", "HN"),
) -> Any:
    """Select one trace from a stream or waveform file.

    Parameters
    ----------
    stream_or_path
        ObsPy stream, iterable of traces, one trace-like object, or a path
        accepted by :func:`read_waveform_file`.
    station
        Optional station code to match.
    component
        Optional component suffix to match, such as ``"Z"``, ``"R"``, or
        ``"T"``.
    prefer_channel_prefixes
        Channel-prefix ordering used when several traces match.

    Returns
    -------
    object
        Selected trace-like object.
    """

    stream = read_waveform_file(stream_or_path) if isinstance(stream_or_path, (str, Path)) else stream_or_path
    traces = list(_iter_traces(stream))
    station_token = str(station or "").strip().upper()
    component_token = str(component or "").strip().upper()
    matches = []
    for trace in traces:
        if station_token and _trace_station_value(trace) != station_token:
            continue
        if component_token and _trace_component_value(trace) != component_token:
            continue
        matches.append(trace)
    if not matches:
        available = sorted(
            f"{_trace_station_value(trace)}.{_trace_channel_value(trace) or _trace_component_value(trace)}"
            for trace in traces
        )
        raise ValueError(
            f"No waveform trace matched station={station!r}, component={component!r}. "
            f"Available traces include: {available[:12]}"
        )
    preference = {str(prefix).upper(): index for index, prefix in enumerate(prefer_channel_prefixes)}

    def _sort_key(trace: Any) -> tuple[int, str]:
        channel = _trace_channel_value(trace)
        rank = min((value for prefix, value in preference.items() if channel.startswith(prefix)), default=len(preference))
        return rank, channel

    return sorted(matches, key=_sort_key)[0]


def trace_metadata_table(
    stream: Any,
    *,
    source: str | Path | None = None,
    event_id: str | None = None,
) -> pd.DataFrame:
    """Extract normalized metadata from trace-like objects.

    Parameters
    ----------
    stream
        ObsPy stream, iterable of trace-like objects, or one trace mapping.
    source
        Optional source label or path copied into the output.
    event_id
        Optional event identifier copied into the output.

    Returns
    -------
    pandas.DataFrame
        One row per trace with stable public metadata columns.
    """

    rows: list[dict[str, Any]] = []
    for trace in _iter_traces(stream):
        rows.append(_trace_metadata(trace, source=source, event_id=event_id))
    columns = [
        "event_id",
        "source",
        "network",
        "station",
        "location",
        "channel",
        "component",
        "starttime",
        "endtime",
        "sampling_rate",
        "delta",
        "npts",
        "lat",
        "lon",
        "elev",
    ]
    return pd.DataFrame(rows, columns=columns)


def write_trace_metadata_csv(stream: Any, path: str | Path, *, source: str | Path | None = None, event_id: str | None = None) -> Path:
    """Write trace metadata to CSV.

    Parameters
    ----------
    stream
        Stream-like object to inspect.
    path
        Output CSV path.
    source, event_id
        Optional metadata copied into every row.

    Returns
    -------
    pathlib.Path
        Written CSV path.
    """

    output = Path(path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    trace_metadata_table(stream, source=source, event_id=event_id).to_csv(output, index=False)
    return output


def stream_station_table(stream: Any) -> pd.DataFrame:
    """Build a deduplicated station table from stream trace metadata.

    Parameters
    ----------
    stream
        Stream-like object.

    Returns
    -------
    pandas.DataFrame
        One row per network/station pair.
    """

    meta = trace_metadata_table(stream)
    if meta.empty:
        return pd.DataFrame(columns=["network", "station", "lat", "lon", "elev"])
    cols = ["network", "station", "lat", "lon", "elev"]
    return (
        meta.loc[:, cols]
        .drop_duplicates(["network", "station"])
        .sort_values(["network", "station"], kind="stable")
        .reset_index(drop=True)
    )


def waveform_preprocessing_from_config(config: Any | None = None) -> WaveformPreprocessing:
    """Read waveform preprocessing settings from a Spatial-VTK config.

    Parameters
    ----------
    config
        Optional ``SpatialVTKConfig``. When omitted, the active or discovered
        config is used when available.

    Returns
    -------
    WaveformPreprocessing
        Parsed lowpass cutoff and filter order.
    """

    cfg = config
    if cfg is None:
        try:
            from spatial_vtk.config import SpatialVTKConfig

            cfg = SpatialVTKConfig.active()
        except Exception:
            cfg = None
    section = {}
    if cfg is not None:
        try:
            section = dict(cfg.section("waveforms.preprocessing", {}) or {})
        except Exception:
            section = {}
    lowpass_hz = _optional_positive_float(section.get("lowpass_hz"))
    highpass_hz = _optional_positive_float(section.get("highpass_hz"))
    bandpass_low_hz, bandpass_high_hz = _parse_bandpass_section(section)
    resample_hz = _optional_positive_float(
        _first_present(
            section,
            "resample_hz",
            "target_sampling_rate_hz",
            "sampling_rate_hz",
            "target_sample_rate_hz",
        )
    )
    filter_order = _optional_positive_int(section.get("filter_order")) or 4
    return WaveformPreprocessing(
        lowpass_hz=lowpass_hz,
        highpass_hz=highpass_hz,
        bandpass_low_hz=bandpass_low_hz,
        bandpass_high_hz=bandpass_high_hz,
        resample_hz=resample_hz,
        filter_order=filter_order,
    )


def apply_waveform_preprocessing(
    data: Any,
    dt: float,
    preprocessing: WaveformPreprocessing | None = None,
    *,
    config: Any | None = None,
) -> np.ndarray:
    """Apply configured waveform preprocessing to one sample array.

    Parameters
    ----------
    data
        One-dimensional waveform samples.
    dt
        Sample interval in seconds.
    preprocessing
        Explicit preprocessing settings. When omitted, settings are read from
        ``config`` or from the active Spatial-VTK config.
    config
        Optional config used only when ``preprocessing`` is omitted.

    Returns
    -------
    numpy.ndarray
        Preprocessed waveform samples.
    """

    return apply_waveform_preprocessing_with_metadata(data, dt, preprocessing, config=config).data


def apply_waveform_preprocessing_with_metadata(
    data: Any,
    dt: float,
    preprocessing: WaveformPreprocessing | None = None,
    *,
    config: Any | None = None,
) -> PreprocessedWaveform:
    """Apply configured preprocessing and return updated timing metadata.

    Parameters
    ----------
    data
        One-dimensional waveform samples.
    dt
        Sample interval in seconds.
    preprocessing
        Explicit preprocessing settings. When omitted, settings are read from
        ``config`` or from the active Spatial-VTK config.
    config
        Optional config used only when ``preprocessing`` is omitted.

    Returns
    -------
    PreprocessedWaveform
        Filtered/resampled samples plus updated ``dt`` and sampling rate.
    """

    settings = preprocessing or waveform_preprocessing_from_config(config)
    _validate_preprocessing(settings, dt)
    samples = np.asarray(data, dtype=float).reshape(-1).copy()
    out_dt = float(dt)
    if samples.size == 0:
        sampling_rate = 1.0 / out_dt if np.isfinite(out_dt) and out_dt > 0.0 else float("nan")
        return PreprocessedWaveform(samples, out_dt, sampling_rate, waveform_preprocessing_label(settings))

    if settings.bandpass_low_hz is not None or settings.bandpass_high_hz is not None:
        if settings.bandpass_low_hz is None or settings.bandpass_high_hz is None:
            raise ValueError("Both bandpass_low_hz and bandpass_high_hz are required for bandpass preprocessing.")
        out = _butter_filter(samples, out_dt, (settings.bandpass_low_hz, settings.bandpass_high_hz), "bandpass", order=settings.filter_order)
    else:
        out = samples
        if settings.highpass_hz is not None:
            out = _butter_filter(out, out_dt, settings.highpass_hz, "highpass", order=settings.filter_order)
        if settings.lowpass_hz is not None:
            out = _butter_filter(out, out_dt, settings.lowpass_hz, "lowpass", order=settings.filter_order)

    if settings.resample_hz is not None:
        out, out_dt = _resample_to_rate(out, out_dt, settings.resample_hz)
    sampling_rate = 1.0 / out_dt if np.isfinite(out_dt) and out_dt > 0.0 else float("nan")
    return PreprocessedWaveform(np.asarray(out, dtype=float), out_dt, sampling_rate, waveform_preprocessing_label(settings))


def waveform_preprocessing_label(preprocessing: WaveformPreprocessing | None = None, *, config: Any | None = None) -> str:
    """Return a human-readable label for configured waveform preprocessing.

    Parameters
    ----------
    preprocessing
        Explicit preprocessing settings. When omitted, settings are read from
        ``config`` or from the active Spatial-VTK config.
    config
        Optional config used only when ``preprocessing`` is omitted.

    Returns
    -------
    str
        Label suitable for waveform figure subtitles.
    """

    settings = preprocessing or waveform_preprocessing_from_config(config)
    parts: list[str] = []
    if settings.bandpass_low_hz is not None or settings.bandpass_high_hz is not None:
        if settings.bandpass_low_hz is not None and settings.bandpass_high_hz is not None:
            parts.append(f"bandpass {settings.bandpass_low_hz:g}-{settings.bandpass_high_hz:g} Hz")
        else:
            parts.append("partial bandpass config")
    else:
        if settings.highpass_hz is not None:
            parts.append(f"highpass {settings.highpass_hz:g} Hz")
        if settings.lowpass_hz is not None:
            parts.append(f"lowpass {settings.lowpass_hz:g} Hz")
    if settings.resample_hz is not None:
        parts.append(f"resample {settings.resample_hz:g} Hz")
    if not parts:
        return "Filter: no configured waveform preprocessing"
    return "Filter: " + "; ".join(parts)


def preprocess_stream(stream: Any, preprocessing: WaveformPreprocessing | None = None, *, config: Any | None = None) -> Any:
    """Apply waveform preprocessing to every trace in a stream-like object.

    Parameters
    ----------
    stream
        ObsPy stream, iterable of traces, or one trace-like mapping/object.
    preprocessing
        Optional preprocessing settings. When omitted, the active config is
        used when available.
    config
        Optional Spatial-VTK config used only when ``preprocessing`` is omitted.

    Returns
    -------
    object
        A copied stream or list of copied trace-like mappings with updated
        samples, sampling rate, and ``delta`` metadata.
    """

    settings = preprocessing or waveform_preprocessing_from_config(config)
    if _is_obspy_stream_like(stream):
        out_stream = stream.copy()
        for trace in out_stream:
            _apply_preprocessing_to_trace_in_place(trace, settings)
        return out_stream
    traces = list(_iter_traces(stream))
    processed = [_processed_trace_copy(trace, settings) for trace in traces]
    if isinstance(stream, dict) and ("data" in stream or "stats" in stream):
        return processed[0] if processed else stream
    return processed


def _validate_preprocessing(settings: WaveformPreprocessing, dt: float) -> None:
    """Validate preprocessing settings against the sample interval."""

    if not np.isfinite(float(dt)) or float(dt) <= 0.0:
        raise ValueError(f"Waveform preprocessing requires a positive sample interval, got {dt!r}.")
    nyquist = 0.5 / float(dt)
    cutoffs = {
        "lowpass_hz": settings.lowpass_hz,
        "highpass_hz": settings.highpass_hz,
        "bandpass_low_hz": settings.bandpass_low_hz,
        "bandpass_high_hz": settings.bandpass_high_hz,
    }
    for name, value in cutoffs.items():
        if value is not None and float(value) >= nyquist:
            raise ValueError(f"{name}={value:g} Hz must be below the Nyquist frequency ({nyquist:g} Hz).")
    if settings.bandpass_low_hz is not None and settings.bandpass_high_hz is not None:
        if settings.bandpass_low_hz >= settings.bandpass_high_hz:
            raise ValueError("bandpass_low_hz must be lower than bandpass_high_hz.")
    if settings.resample_hz is not None and settings.resample_hz <= 0.0:
        raise ValueError("resample_hz must be positive when provided.")


def _butter_filter(data: np.ndarray, dt: float, cutoff: float | tuple[float, float], btype: str, *, order: int) -> np.ndarray:
    """Apply one Butterworth filter and preserve the input length."""

    from scipy.signal import butter, detrend, sosfiltfilt

    samples = np.asarray(data, dtype=float).reshape(-1)
    if samples.size < max(8, int(order) * 3):
        return samples.copy()
    finite = np.isfinite(samples)
    if not np.all(finite):
        samples = samples.copy()
        fill = float(np.nanmedian(samples[finite])) if np.any(finite) else 0.0
        samples[~finite] = fill
    cleaned = detrend(samples, type="constant")
    sos = butter(int(order), cutoff, btype=btype, fs=1.0 / float(dt), output="sos")
    return np.asarray(sosfiltfilt(sos, cleaned), dtype=float)


def _resample_to_rate(data: np.ndarray, dt: float, target_hz: float) -> tuple[np.ndarray, float]:
    """Resample samples to a target rate with a rational polyphase filter."""

    from scipy.signal import resample_poly

    current_hz = 1.0 / float(dt)
    if np.isclose(current_hz, float(target_hz), rtol=1e-6, atol=1e-9):
        return np.asarray(data, dtype=float).copy(), float(dt)
    ratio = Fraction(float(target_hz) / current_hz).limit_denominator(1000)
    out = resample_poly(np.asarray(data, dtype=float), ratio.numerator, ratio.denominator)
    return np.asarray(out, dtype=float), 1.0 / float(target_hz)


def _apply_preprocessing_to_trace_in_place(trace: Any, settings: WaveformPreprocessing) -> None:
    """Update one mutable trace object with preprocessed data and timing."""

    stats = _trace_stats(trace)
    data = _trace_data(trace)
    dt = _trace_dt(stats)
    result = apply_waveform_preprocessing_with_metadata(data, dt, settings)
    trace.data = np.asarray(result.data, dtype=float)
    _set_stat_value(stats, "sampling_rate", result.sampling_rate_hz)
    _set_stat_value(stats, "delta", result.dt)
    _set_stat_value(stats, "npts", int(result.data.size))


def _processed_trace_copy(trace: Any, settings: WaveformPreprocessing) -> dict[str, Any]:
    """Return a lightweight copied trace mapping after preprocessing."""

    stats = _copy_stats_mapping(_trace_stats(trace))
    data = _trace_data(trace)
    dt = _trace_dt(stats)
    result = apply_waveform_preprocessing_with_metadata(data, dt, settings)
    stats["sampling_rate"] = result.sampling_rate_hz
    stats["delta"] = result.dt
    stats["npts"] = int(result.data.size)
    return {"data": np.asarray(result.data, dtype=float), "stats": stats}


def _trace_dt(stats: Any) -> float:
    """Return sample interval from trace stats."""

    sampling_rate = _safe_float(_stat_value(stats, "sampling_rate", None))
    delta = _safe_float(_stat_value(stats, "delta", None))
    return float(delta) if delta not in (None, 0.0) else (1.0 / float(sampling_rate) if sampling_rate not in (None, 0.0) else float("nan"))


def _copy_stats_mapping(stats: Any) -> dict[str, Any]:
    """Convert trace stats into a mutable plain mapping."""

    if stats is None:
        return {}
    if isinstance(stats, dict):
        return dict(stats)
    keys = (
        "network",
        "station",
        "location",
        "channel",
        "component",
        "sampling_rate",
        "delta",
        "npts",
        "starttime",
        "endtime",
        "latitude",
        "longitude",
        "elevation",
    )
    out = {key: getattr(stats, key) for key in keys if hasattr(stats, key)}
    coords = getattr(stats, "coordinates", None)
    if coords is not None:
        out["coordinates"] = coords
    return out


def _set_stat_value(stats: Any, key: str, value: Any) -> None:
    """Set one stats metadata value on a mapping or attribute object."""

    if stats is None:
        return
    try:
        if isinstance(stats, dict):
            stats[key] = value
        else:
            setattr(stats, key, value)
    except Exception:
        return


def _parse_bandpass_section(section: dict[str, Any]) -> tuple[float | None, float | None]:
    """Parse flexible bandpass config values into low/high frequencies."""

    low = _optional_positive_float(_first_present(section, "bandpass_low_hz", "bandpass_low", "low_hz"))
    high = _optional_positive_float(_first_present(section, "bandpass_high_hz", "bandpass_high", "high_hz"))
    pair = _first_present(section, "bandpass_hz", "bandpass")
    if pair not in (None, ""):
        if isinstance(pair, dict):
            low = _optional_positive_float(_first_present(pair, "low_hz", "low", "min_hz"))
            high = _optional_positive_float(_first_present(pair, "high_hz", "high", "max_hz"))
        elif isinstance(pair, (list, tuple)) and len(pair) >= 2:
            low = _optional_positive_float(pair[0])
            high = _optional_positive_float(pair[1])
    return low, high


def _first_present(mapping: dict[str, Any], *keys: str) -> Any:
    """Return the first non-empty value for one of several keys."""

    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


def _read_numpy_waveform(path: Path) -> list[dict[str, Any]]:
    """Read a NumPy waveform file into lightweight trace mappings."""

    if path.suffix.lower() == ".npy":
        data = np.load(path)
        return [{"data": np.asarray(data), "stats": {"station": path.stem, "channel": "", "sampling_rate": 1.0}}]
    payload = np.load(path, allow_pickle=True)
    data = np.asarray(payload["data"] if "data" in payload.files else payload[payload.files[0]])
    if data.ndim == 1:
        data = data[:, np.newaxis]
    if data.ndim != 2:
        raise ValueError("NumPy waveform data must be one- or two-dimensional.")
    channels = _npz_string_list(payload, "channels", default=[f"CH{idx + 1}" for idx in range(data.shape[1])])
    traces: list[dict[str, Any]] = []
    for idx in range(data.shape[1]):
        channel = channels[idx] if idx < len(channels) else f"CH{idx + 1}"
        traces.append(
            {
                "data": np.asarray(data[:, idx]),
                "stats": {
                    "network": _npz_scalar(payload, "network", ""),
                    "station": _npz_scalar(payload, "station", path.stem),
                    "location": _npz_scalar(payload, "location", ""),
                    "channel": channel,
                    "sampling_rate": float(_npz_scalar(payload, "sampling_rate", 1.0)),
                    "starttime": _npz_scalar(payload, "starttime", ""),
                    "latitude": _npz_scalar(payload, "latitude", np.nan),
                    "longitude": _npz_scalar(payload, "longitude", np.nan),
                    "elevation": _npz_scalar(payload, "elevation", np.nan),
                },
            }
        )
    return traces


def _trace_metadata(trace: Any, *, source: str | Path | None, event_id: str | None) -> dict[str, Any]:
    """Return one normalized trace metadata row."""

    stats = _trace_stats(trace)
    data = _trace_data(trace)
    channel = str(_stat_value(stats, "channel", "") or "")
    sampling_rate = _safe_float(_stat_value(stats, "sampling_rate", None))
    delta = _safe_float(_stat_value(stats, "delta", None))
    if sampling_rate is None and delta not in (None, 0.0):
        sampling_rate = 1.0 / float(delta)
    if delta is None and sampling_rate not in (None, 0.0):
        delta = 1.0 / float(sampling_rate)
    npts = _safe_int(_stat_value(stats, "npts", None))
    if npts is None and data is not None:
        npts = int(np.asarray(data).size)
    coords = _stat_value(stats, "coordinates", None)
    lat = _safe_float(_first_stat(stats, coords, "latitude", "lat", "station_lat"))
    lon = _safe_float(_first_stat(stats, coords, "longitude", "lon", "station_lon"))
    elev = _safe_float(_first_stat(stats, coords, "elevation", "elev", "station_elev"))
    return {
        "event_id": str(event_id or ""),
        "source": str(source or ""),
        "network": str(_stat_value(stats, "network", "") or "").strip().upper(),
        "station": str(_stat_value(stats, "station", "") or "").strip().split(".")[-1].upper(),
        "location": str(_stat_value(stats, "location", "") or "").strip(),
        "channel": channel.strip().upper(),
        "component": channel[-1:].upper() if channel else "",
        "starttime": str(_stat_value(stats, "starttime", "") or ""),
        "endtime": str(_stat_value(stats, "endtime", "") or ""),
        "sampling_rate": sampling_rate,
        "delta": delta,
        "npts": npts,
        "lat": lat,
        "lon": lon,
        "elev": elev,
    }


def _trace_station_value(trace: Any) -> str:
    """Return normalized station code for one trace-like object."""

    stats = _trace_stats(trace)
    return str(_stat_value(stats, "station", "") or "").strip().upper()


def _trace_channel_value(trace: Any) -> str:
    """Return normalized channel code for one trace-like object."""

    stats = _trace_stats(trace)
    return str(_stat_value(stats, "channel", "") or "").strip().upper()


def _trace_component_value(trace: Any) -> str:
    """Return normalized component code for one trace-like object."""

    stats = _trace_stats(trace)
    component = str(_stat_value(stats, "component", "") or "").strip().upper()
    channel = _trace_channel_value(trace)
    return component or (channel[-1:] if channel else "")


def _trace_stats(trace: Any) -> Any:
    """Return stats metadata from trace-like objects."""

    if isinstance(trace, dict):
        return trace.get("stats", trace)
    return getattr(trace, "stats", None)


def _trace_data(trace: Any) -> Any:
    """Return trace data from trace-like objects."""

    if isinstance(trace, dict):
        return trace.get("data")
    return getattr(trace, "data", None)


def _stat_value(stats: Any, key: str, default: Any = None) -> Any:
    """Read one metadata value from a mapping or attribute object."""

    if stats is None:
        return default
    if isinstance(stats, dict):
        return stats.get(key, default)
    return getattr(stats, key, default)


def _first_stat(primary: Any, secondary: Any, *keys: str) -> Any:
    """Return the first available metadata value across stats objects."""

    for key in keys:
        value = _stat_value(primary, key, None)
        if value not in (None, ""):
            return value
        value = _stat_value(secondary, key, None)
        if value not in (None, ""):
            return value
    return None


def _safe_float(value: Any) -> float | None:
    """Convert one value to finite float when possible."""

    try:
        out = float(value)
    except Exception:
        return None
    return float(out) if np.isfinite(out) else None


def _safe_int(value: Any) -> int | None:
    """Convert one value to int when possible."""

    try:
        return int(value)
    except Exception:
        return None


def _optional_positive_float(value: Any) -> float | None:
    """Convert one optional config value to a positive finite float."""

    if value in (None, ""):
        return None
    try:
        out = float(value)
    except Exception:
        return None
    return float(out) if np.isfinite(out) and out > 0.0 else None


def _optional_positive_int(value: Any) -> int | None:
    """Convert one optional config value to a positive integer."""

    out = _optional_positive_float(value)
    return int(out) if out is not None else None


def _iter_traces(stream: Any) -> Iterable[Any]:
    """Yield trace-like objects from a stream-like input."""

    if stream is None:
        return []
    if isinstance(stream, dict) and ("data" in stream or "stats" in stream):
        return [stream]
    if hasattr(stream, "data") and hasattr(stream, "stats"):
        return [stream]
    if isinstance(stream, Iterable) and not isinstance(stream, (str, bytes, Path)):
        return stream
    return [stream]


def _is_iterable_stream(value: Any) -> bool:
    """Return whether one value can be iterated as traces."""

    return isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict, Path))


def _is_obspy_stream_like(value: Any) -> bool:
    """Return whether one value behaves like an ObsPy Stream."""

    return not isinstance(value, (list, tuple)) and hasattr(value, "copy") and hasattr(value, "__iadd__") and hasattr(value, "__iter__")


def _optional_obspy() -> Any | None:
    """Import ObsPy when available."""

    try:
        import obspy  # type: ignore
    except Exception:
        return None
    return obspy


def _npz_scalar(payload: Any, key: str, default: Any) -> Any:
    """Read a scalar value from an ``np.load`` payload."""

    if key not in payload.files:
        return default
    value = payload[key]
    try:
        return value.item()
    except Exception:
        return value


def _npz_string_list(payload: Any, key: str, *, default: list[str]) -> list[str]:
    """Read a string-list value from an ``np.load`` payload."""

    if key not in payload.files:
        return default
    value = payload[key]
    if np.ndim(value) == 0:
        return [str(value.item())]
    return [str(item) for item in list(value)]


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the module-level CLI parser."""

    parser = argparse.ArgumentParser(description="Load waveform files and write trace metadata.")
    parser.add_argument("paths", nargs="+", help="Waveform files to inspect.")
    parser.add_argument("--format", default=None, help="Optional ObsPy format string.")
    parser.add_argument("--event-id", default="", help="Event ID copied into output rows.")
    parser.add_argument("--output", required=True, help="Output trace metadata CSV.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the waveform metadata CLI wrapper."""

    args = build_arg_parser().parse_args(argv)
    stream = load_waveform_collection(args.paths, format=args.format)
    write_trace_metadata_csv(stream, args.output, event_id=args.event_id)
    return 0


__all__ = [
    "PreprocessedWaveform",
    "WaveformPreprocessing",
    "read_waveform_file",
    "select_waveform_trace",
    "load_waveform_collection",
    "waveform_preprocessing_from_config",
    "apply_waveform_preprocessing",
    "apply_waveform_preprocessing_with_metadata",
    "waveform_preprocessing_label",
    "preprocess_stream",
    "trace_metadata_table",
    "write_trace_metadata_csv",
    "stream_station_table",
    "build_arg_parser",
    "main",
]
