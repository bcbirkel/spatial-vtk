"""Synthetic data format inspection and Salvus handling choices.

Purpose
-------
This module classifies configured synthetic roots into normalized waveform
products such as MiniSEED, ASDF, or HDF5/H5, and raw Salvus output layouts that
need coordinate and metadata correction before use.

Usage examples
--------------
Inspect one root:
  ``info = inspect_synthetic_format("data/examples/synthetics")``
"""

from __future__ import annotations

from dataclasses import dataclass
import glob
from pathlib import Path
from typing import Any, Iterable, Mapping


SALVUS_ACCELERATION_SCALE_MPS2_TO_CMPS2 = 100.0


@dataclass(frozen=True)
class SyntheticFormatInfo:
    """Description of one synthetic data layout."""

    root: str
    format: str
    normalized: bool
    needs_salvus_handling: bool
    handling_mode: str | None = None
    converted_root: str | None = None


@dataclass(frozen=True)
class SyntheticReadRequest:
    """Request used by the normalized synthetic reader interface."""

    event_id: str | None = None
    station: str | None = None
    component: str | None = None
    stations: tuple[str, ...] | None = None
    components: tuple[str, ...] | None = None
    pattern: str | None = None


@dataclass(frozen=True)
class SalvusConversionRequest:
    """Options for normalizing raw Salvus-style XYZ synthetic traces.

    Parameters
    ----------
    components
        Desired output components. Supported values are ``N``, ``E``, ``Z``,
        ``R``, and ``T``.
    event_latitude, event_longitude
        Event coordinates used to rotate north/east traces to radial/transverse.
    station_coordinates
        Mapping from station code, ``NET.STA``, or ``NET.STA.LOC`` to latitude
        and longitude values.
    starttime_override
        Explicit start time to apply to every output trace.
    component_map
        Optional raw-to-normalized component map. Defaults to ``X -> E``,
        ``Y -> N``, and ``Z -> Z``.
    acceleration_scale
        Multiplicative scale applied while reading raw ``point/acceleration``
        values. Salvus receiver files are commonly written in ``m/s^2`` while
        validation workflows often compare acceleration in ``cm/s^2``; the
        default therefore multiplies by 100.
    input_acceleration_units, output_acceleration_units
        Human-readable unit labels recorded on converted traces and ASDF
        metadata.
    """

    components: tuple[str, ...] = ("N", "E", "R", "T", "Z")
    event_latitude: float | None = None
    event_longitude: float | None = None
    station_coordinates: Mapping[str, Mapping[str, float]] | None = None
    starttime_override: str | None = None
    component_map: Mapping[str, str] | None = None
    acceleration_scale: float = SALVUS_ACCELERATION_SCALE_MPS2_TO_CMPS2
    input_acceleration_units: str = "m/s^2"
    output_acceleration_units: str = "cm/s^2"


def inspect_synthetic_format(input_syn_path: str | Path) -> SyntheticFormatInfo:
    """Inspect one synthetic path and classify its format.

    Parameters
    ----------
    input_syn_path
        Synthetic root, file, or glob template.

    Returns
    -------
    SyntheticFormatInfo
        Format classification.
    """

    root = _inspection_root(input_syn_path)
    if root.is_dir() and next(root.rglob("*.asdf"), None) is not None:
        return SyntheticFormatInfo(str(root), "asdf", True, False)
    files = _sample_files(root)
    suffixes = {path.suffix.lower() for path in files}
    if suffixes & {".asdf"}:
        return SyntheticFormatInfo(str(root), "asdf", True, False)
    if suffixes & {".mseed", ".msd"}:
        return SyntheticFormatInfo(str(root), "mseed", True, False)
    if suffixes & {".h5", ".hdf5"}:
        if _looks_like_raw_salvus(root, files):
            return SyntheticFormatInfo(str(root), "salvus", False, True)
        if _looks_like_salvus_receivers_h5(files):
            return SyntheticFormatInfo(str(root), "salvus", False, True)
        if _looks_like_asdf_hdf5(files):
            return SyntheticFormatInfo(str(root), "asdf", True, False)
        return SyntheticFormatInfo(str(root), "hdf5", True, False)
    if _looks_like_raw_salvus(root, files):
        return SyntheticFormatInfo(str(root), "salvus", False, True)
    return SyntheticFormatInfo(str(root), "unknown", False, False)


def prompt_for_salvus_handling(info: SyntheticFormatInfo) -> SyntheticFormatInfo:
    """Prompt for handling raw Salvus outputs.

    Parameters
    ----------
    info
        Synthetic format info that requires Salvus handling.

    Returns
    -------
    SyntheticFormatInfo
        Updated info with handling mode, or the input info for normalized data.
    """

    if not info.needs_salvus_handling:
        return info
    print(
        "The synthetic root looks like raw Salvus output. Salvus outputs may be "
        "in XYZ coordinates and may have incorrect start times. Choose how to handle this:"
    )
    print("  convert-once: write normalized files for reuse")
    print("  on-the-fly: apply correction whenever traces are read")
    print("  cancel: exit without changing config or running downstream work")
    while True:
        try:
            raw = input("Please answer with convert-once, on-the-fly, or cancel: ").strip().lower()
        except EOFError:
            raw = "cancel"
        if raw in {"cancel", "quit", "exit", "stop", "end"}:
            return SyntheticFormatInfo(info.root, info.format, info.normalized, info.needs_salvus_handling, "cancel", info.converted_root)
        if raw in {"convert-once", "on-the-fly"}:
            return SyntheticFormatInfo(info.root, info.format, info.normalized, info.needs_salvus_handling, raw, info.converted_root)
        print("Please answer with convert-once, on-the-fly, or cancel.")


def normalize_salvus_outputs_once(info: SyntheticFormatInfo, *, output_root: str | Path) -> SyntheticFormatInfo:
    """Record the intended converted output root for raw Salvus products.

    Parameters
    ----------
    info
        Raw Salvus format info.
    output_root
        Root where normalized products should be written.

    Returns
    -------
    SyntheticFormatInfo
        Updated info pointing to the converted root.

    Notes
    -----
    This function records the conversion target. Use
    ``write_normalized_salvus_mseed()`` when an ObsPy stream has already been
    loaded and should be normalized into a reusable MiniSEED product. Raw HDF5
    file layouts still require a schema adapter before they can be converted.
    """

    output = Path(output_root).expanduser()
    output.mkdir(parents=True, exist_ok=True)
    return SyntheticFormatInfo(str(info.root), info.format, False, True, "convert-once", str(output))


def normalize_salvus_stream(stream: Any, request: SalvusConversionRequest | None = None):
    """Return a normalized ObsPy Stream for raw Salvus-style synthetic traces.

    Parameters
    ----------
    stream
        ObsPy Stream containing XYZ or already normalized component suffixes.
    request
        Conversion options. Defaults to N/E/R/T/Z output with ``X -> E``,
        ``Y -> N``, and ``Z -> Z`` mapping.

    Returns
    -------
    obspy.Stream
        New stream with requested components. The input stream is not mutated.
    """

    try:
        from obspy import Stream, UTCDateTime
    except Exception as exc:
        raise RuntimeError("ObsPy is required to normalize Salvus synthetic streams.") from exc

    request = request or SalvusConversionRequest()
    wanted = tuple(str(component).upper() for component in request.components)
    component_map = {key.upper(): value.upper() for key, value in (request.component_map or {"X": "E", "Y": "N", "Z": "Z"}).items()}
    starttime = UTCDateTime(request.starttime_override) if request.starttime_override else None

    nez = Stream()
    for trace in stream:
        raw_component = _component_from_channel(getattr(trace.stats, "channel", ""))
        normalized_component = component_map.get(raw_component, raw_component)
        if normalized_component not in {"N", "E", "Z"}:
            continue
        copied = trace.copy()
        copied.stats.channel = _channel_with_component(getattr(copied.stats, "channel", ""), normalized_component)
        if starttime is not None:
            copied.stats.starttime = starttime
        nez += copied

    output = Stream()
    for component in ("N", "E", "Z"):
        if component in wanted:
            output += _select_component(nez, component)
    if "R" in wanted or "T" in wanted:
        output += _rotate_nez_to_requested_rt(nez, request, wanted)
    return output


def write_normalized_salvus_mseed(
    stream: Any,
    output_root: str | Path,
    *,
    event_id: str,
    request: SalvusConversionRequest | None = None,
) -> Path:
    """Normalize a Salvus-style stream and write one event MiniSEED file.

    Parameters
    ----------
    stream
        ObsPy Stream containing raw Salvus-style traces.
    output_root
        Directory where the normalized event file should be written.
    event_id
        Event identifier used in the output filename.
    request
        Optional conversion request.

    Returns
    -------
    pathlib.Path
        Written MiniSEED path.
    """

    output = Path(output_root).expanduser()
    output.mkdir(parents=True, exist_ok=True)
    normalized = normalize_salvus_stream(stream, request)
    path = output / f"{_safe_token(event_id)}_salvus_normalized.mseed"
    normalized.write(str(path), format="MSEED")
    return path


def read_salvus_receivers_h5(
    path: str | Path,
    *,
    origin_time: str,
    request: SalvusConversionRequest | None = None,
    receiver_start: int = 0,
    receiver_stop: int | None = None,
):
    """Read and normalize one Salvus ``receivers.h5`` file.

    Parameters
    ----------
    path
        HDF5 file containing the supported Salvus receiver schema with
        ``names_ELASTIC_point`` and ``point/acceleration``.
    origin_time
        Authoritative event origin time. The file's ``start_time_in_seconds``
        offset is applied relative to this time.
    request
        Optional conversion request. When omitted, only ``N/E/Z`` components
        are returned because ``R/T`` requires station coordinates.
    receiver_start, receiver_stop
        Optional receiver index range for chunked conversion.

    Returns
    -------
    obspy.Stream
        Normalized stream for the requested receiver range.
    """

    try:
        import h5py
        from obspy import Stream, Trace, UTCDateTime
    except Exception as exc:
        raise RuntimeError("h5py and ObsPy are required to read Salvus receivers.h5 files.") from exc

    h5_path = Path(path).expanduser()
    request = request or SalvusConversionRequest(components=("N", "E", "Z"))
    with h5py.File(h5_path, "r") as handle:
        _validate_salvus_receivers_h5(handle, h5_path)
        raw_names = handle["names_ELASTIC_point"][()]
        receiver_names = [_decode_hdf5_text(name) for name in raw_names]
        data = handle["point/acceleration"]
        sampling_rate_hz = _salvus_sampling_rate(handle)
        start_offset_s = _salvus_start_offset(handle)
        start = max(0, int(receiver_start))
        stop = len(receiver_names) if receiver_stop is None else min(len(receiver_names), int(receiver_stop))
        if stop < start:
            raise ValueError(f"receiver_stop {receiver_stop} is before receiver_start {receiver_start}.")
        origin = UTCDateTime(origin_time)
        trace_start = origin + float(start_offset_s)
        raw_stream = Stream()
        for receiver_index in range(start, stop):
            network, station, location = _parse_salvus_receiver_name(receiver_names[receiver_index])
            receiver_cube = data[receiver_index]
            if receiver_cube.shape[0] < 3:
                raise ValueError(f"{h5_path} point/acceleration receiver {receiver_index} has fewer than three components.")
            acceleration_scale = float(request.acceleration_scale)
            if acceleration_scale <= 0.0:
                raise ValueError("SalvusConversionRequest.acceleration_scale must be > 0.")
            for component_index, component in enumerate(("X", "Y", "Z")):
                trace_data = (receiver_cube[component_index].astype("float32", copy=True) * acceleration_scale).astype("float32", copy=False)
                trace = Trace(data=trace_data)
                trace.stats.network = network
                trace.stats.station = station
                trace.stats.location = location
                trace.stats.channel = f"BH{component}"
                trace.stats.sampling_rate = float(sampling_rate_hz)
                trace.stats.delta = 1.0 / float(sampling_rate_hz)
                trace.stats.starttime = trace_start
                trace.stats.units = str(request.output_acceleration_units)
                trace.stats.processing = [
                    f"spatial_vtk: scaled Salvus acceleration by {acceleration_scale:g} "
                    f"from {request.input_acceleration_units} to {request.output_acceleration_units}"
                ]
                raw_stream.append(trace)
    adjusted_request = SalvusConversionRequest(
        components=tuple(request.components),
        event_latitude=request.event_latitude,
        event_longitude=request.event_longitude,
        station_coordinates=request.station_coordinates,
        starttime_override=str(trace_start),
        component_map=request.component_map,
        acceleration_scale=request.acceleration_scale,
        input_acceleration_units=request.input_acceleration_units,
        output_acceleration_units=request.output_acceleration_units,
    )
    return normalize_salvus_stream(raw_stream, adjusted_request)


def write_salvus_receivers_h5_mseed(
    path: str | Path,
    output_root: str | Path,
    *,
    event_id: str,
    origin_time: str,
    request: SalvusConversionRequest | None = None,
    receiver_start: int = 0,
    receiver_stop: int | None = None,
) -> Path:
    """Convert one Salvus ``receivers.h5`` file into normalized MiniSEED."""

    stream = read_salvus_receivers_h5(
        path,
        origin_time=origin_time,
        request=request,
        receiver_start=receiver_start,
        receiver_stop=receiver_stop,
    )
    output = Path(output_root).expanduser()
    output.mkdir(parents=True, exist_ok=True)
    out_path = output / f"{_safe_token(event_id)}_salvus_normalized.mseed"
    stream.write(str(out_path), format="MSEED")
    return out_path


class SyntheticReader:
    """Read normalized synthetic waveforms through one format-aware interface."""

    def __init__(self, info: SyntheticFormatInfo):
        """Create a reader for one inspected synthetic root."""

        self.info = info

    def read(self, request: SyntheticReadRequest | None = None):
        """Read synthetic traces for one request.

        Parameters
        ----------
        request
            Optional event/station/component constraints.

        Returns
        -------
        object
            ObsPy Stream for MiniSEED and best-effort ASDF reads. HDF5/Salvus
            readers raise clear errors until a project-specific schema adapter
            is supplied.
        """

        request = request or SyntheticReadRequest()
        if self.info.format == "mseed":
            return self._read_mseed(request)
        if self.info.format == "asdf":
            return self._read_asdf(request)
        if self.info.format == "hdf5":
            raise NotImplementedError(
                "Generic HDF5 synthetic reading requires a schema adapter. "
                "Point input-syn-path at normalized MiniSEED/ASDF, or add an HDF5 adapter."
            )
        if self.info.format == "salvus":
            if self.info.handling_mode == "on-the-fly":
                raise NotImplementedError(
                    "Raw Salvus on-the-fly XYZ rotation and metadata correction is not yet wired to a reader."
                )
            if self.info.handling_mode == "convert-once" and self.info.converted_root:
                converted = inspect_synthetic_format(self.info.converted_root)
                return SyntheticReader(converted).read(request)
            raise RuntimeError("Raw Salvus synthetic roots must choose convert-once or on-the-fly before reading.")
        raise RuntimeError(f"Unsupported or unknown synthetic format: {self.info.format}")

    def list_stations(self, request: SyntheticReadRequest | None = None) -> list[str]:
        """List station codes available for one request without loading all traces."""

        request = request or SyntheticReadRequest()
        if self.info.format == "asdf":
            return self._list_asdf_stations(request)
        stream = self.read(request)
        return sorted({str(getattr(trace.stats, "station", "")).strip() for trace in stream if str(getattr(trace.stats, "station", "")).strip()})

    def _read_mseed(self, request: SyntheticReadRequest):
        """Read MiniSEED files with ObsPy."""

        try:
            from obspy import Stream, read
        except Exception as exc:
            raise RuntimeError("ObsPy is required to read MiniSEED synthetic files.") from exc
        paths = _matching_waveform_files(self.info.root, request, suffixes=(".mseed", ".msd"))
        stream = None
        for path in paths:
            current = read(str(path))
            stream = current if stream is None else stream + current
        if stream is None:
            return Stream()
        return _filter_stream(stream, request)

    def _read_asdf(self, request: SyntheticReadRequest):
        """Read ASDF waveforms when pyasdf is installed."""

        try:
            import pyasdf
            from obspy import Stream
        except Exception as exc:
            raise RuntimeError("pyasdf and ObsPy are required to read ASDF synthetic files.") from exc
        paths = _matching_waveform_files(self.info.root, request, suffixes=(".asdf",))
        stream = Stream()
        allowed_stations = _requested_station_tokens(request)
        for path in paths:
            with pyasdf.ASDFDataSet(str(path), mode="r") as dataset:
                for station_name in dataset.waveforms.list():
                    if allowed_stations and not _station_group_matches(station_name, allowed_stations):
                        continue
                    station_waveforms = dataset.waveforms[station_name]
                    for tag in station_waveforms.get_waveform_tags():
                        try:
                            station_stream = _filter_stream(station_waveforms[tag], request)
                            if station_stream:
                                stream += station_stream
                        except Exception:
                            continue
        return _filter_stream(stream, request)

    def _list_asdf_stations(self, request: SyntheticReadRequest) -> list[str]:
        """List ASDF station codes matching one request."""

        try:
            import pyasdf
        except Exception as exc:
            raise RuntimeError("pyasdf is required to inspect ASDF synthetic files.") from exc
        allowed_stations = _requested_station_tokens(request)
        stations: set[str] = set()
        for path in _matching_waveform_files(self.info.root, request, suffixes=(".asdf",)):
            with pyasdf.ASDFDataSet(str(path), mode="r") as dataset:
                for station_name in dataset.waveforms.list():
                    if allowed_stations and not _station_group_matches(station_name, allowed_stations):
                        continue
                    stations.add(station_name.split(".")[-1])
        return sorted(stations)


def synthetic_reader_for(info: SyntheticFormatInfo) -> SyntheticReader:
    """Return a normalized reader for one synthetic format.

    Parameters
    ----------
    info
        Synthetic format info.

    Returns
    -------
    SyntheticReader
        Reader that exposes a common ``read()`` method.
    """

    return SyntheticReader(info)


def _inspection_root(input_syn_path: str | Path) -> Path:
    """Return a concrete root to inspect from a path or template."""

    raw = str(input_syn_path)
    for marker in ("{model}", "{model_name}", "{event_id}"):
        if marker in raw:
            raw = raw.split(marker, 1)[0]
            break
    if any(token in raw for token in "*?[]"):
        return Path(raw).expanduser().parent
    return Path(raw).expanduser()


def _sample_files(root: Path, limit: int = 200) -> list[Path]:
    """Sample files under a synthetic root without walking indefinitely."""

    if root.is_file():
        return [root]
    if not root.exists() or not root.is_dir():
        return []
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file():
            files.append(path)
            if len(files) >= limit:
                break
    return files


def _looks_like_raw_salvus(root: Path, files: list[Path]) -> bool:
    """Return whether sampled files look like raw Salvus output."""

    lower_root = str(root).lower()
    if "salvus" in lower_root or "salvus_out" in lower_root:
        return True
    names = {path.name.lower() for path in files}
    if {"meta.json", "receiver.json"} & names:
        return True
    return any("salvus" in str(path).lower() for path in files)


def _looks_like_salvus_receivers_h5(files: list[Path]) -> bool:
    """Return whether sampled HDF5 files match the Salvus receivers schema."""

    hdf5_files = [path for path in files if path.suffix.lower() in {".h5", ".hdf5"}]
    if not hdf5_files:
        return False
    try:
        import h5py
    except Exception:
        return False
    for path in hdf5_files[:5]:
        try:
            with h5py.File(path, "r") as handle:
                if {"names_ELASTIC_point", "coordinates_ELASTIC_point", "point"} <= set(handle.keys()) and "acceleration" in handle["point"]:
                    return True
        except Exception:
            continue
    return False


def _looks_like_asdf_hdf5(files: list[Path]) -> bool:
    """Return whether sampled HDF5 files look like ASDF containers."""

    hdf5_files = [path for path in files if path.suffix.lower() in {".h5", ".hdf5"}]
    if not hdf5_files:
        return False
    try:
        import h5py
    except Exception:
        return False
    for path in hdf5_files[:5]:
        try:
            with h5py.File(path, "r") as handle:
                file_format = str(handle.attrs.get("file_format", "")).lower()
                if "asdf" in file_format:
                    return True
                if {"Waveforms", "AuxiliaryData", "Provenance"} & set(handle.keys()):
                    return True
        except Exception:
            continue
    return False


def _matching_waveform_files(root: str | Path, request: SyntheticReadRequest, *, suffixes: Iterable[str]) -> list[Path]:
    """Return candidate waveform files for one read request."""

    raw_root = str(root)
    patterns: list[str] = []
    if request.pattern:
        patterns.append(request.pattern)
    elif any(marker in raw_root for marker in ("{event_id}", "{station}", "{component}")):
        patterns.append(
            raw_root.format(
                event_id=request.event_id or "*",
                station=request.station or "*",
                component=request.component or "*",
            )
        )
    elif any(token in raw_root for token in "*?[]"):
        patterns.append(raw_root)
    else:
        path = Path(raw_root).expanduser()
        if path.is_file():
            patterns.append(str(path))
        else:
            event_token = f"*{request.event_id}*" if request.event_id else "*"
            for suffix in suffixes:
                patterns.append(str(path / f"{event_token}{suffix}"))
                patterns.append(str(path / "**" / f"{event_token}{suffix}"))
    paths: list[Path] = []
    wanted_suffixes = {suffix.lower() for suffix in suffixes}
    for pattern in patterns:
        for match in glob.glob(str(Path(pattern).expanduser()), recursive=True):
            candidate = Path(match)
            if candidate.is_file() and candidate.suffix.lower() in wanted_suffixes:
                paths.append(candidate)
    return sorted({path for path in paths})


def _filter_stream(stream: Any, request: SyntheticReadRequest):
    """Filter an ObsPy-like stream by station and component."""

    allowed_stations = _requested_station_tokens(request)
    if allowed_stations:
        stream = stream.__class__(
            [
                tr
                for tr in stream
                if _trace_station_matches(
                    str(getattr(tr.stats, "network", "")),
                    str(getattr(tr.stats, "station", "")),
                    allowed_stations,
                )
            ]
        )
    components = _requested_components(request)
    if components:
        stream = stream.__class__([tr for tr in stream if str(getattr(tr.stats, "channel", "")).upper()[-1:] in components])
    return stream


def _requested_station_tokens(request: SyntheticReadRequest) -> set[str]:
    """Return normalized station selectors from singular and plural fields."""

    values: list[str] = []
    if request.station:
        values.append(request.station)
    values.extend(request.stations or ())
    tokens: set[str] = set()
    for raw in values:
        text = str(raw).strip().upper()
        if not text:
            continue
        tokens.add(text)
        parts = text.split(".")
        if parts:
            tokens.add(parts[-1])
        if len(parts) >= 2:
            tokens.add(".".join(parts[:2]))
    return tokens


def _requested_components(request: SyntheticReadRequest) -> set[str]:
    """Return normalized component suffix selectors."""

    values: list[str] = []
    if request.component:
        values.append(request.component)
    values.extend(request.components or ())
    return {str(value).strip().upper()[-1:] for value in values if str(value).strip()}


def _station_group_matches(station_name: str, allowed_stations: set[str]) -> bool:
    """Return whether an ASDF station group matches requested station tokens."""

    text = str(station_name).strip().upper()
    parts = text.split(".")
    candidates = {text}
    if parts:
        candidates.add(parts[-1])
    if len(parts) >= 2:
        candidates.add(".".join(parts[:2]))
    return bool(candidates & allowed_stations)


def _trace_station_matches(network: str, station: str, allowed_stations: set[str]) -> bool:
    """Return whether one trace's station metadata matches requested tokens."""

    net = str(network or "").strip().upper()
    sta = str(station or "").strip().upper()
    candidates = {sta}
    if net and sta:
        candidates.add(f"{net}.{sta}")
    return bool(candidates & allowed_stations)


def _validate_salvus_receivers_h5(handle: Any, path: Path) -> None:
    """Validate the supported Salvus ``receivers.h5`` schema."""

    missing = [name for name in ("names_ELASTIC_point", "point") if name not in handle]
    if missing:
        raise NotImplementedError(f"{path} is not a supported Salvus receivers.h5 file; missing {missing}.")
    if "acceleration" not in handle["point"]:
        raise NotImplementedError(f"{path} is not a supported Salvus receivers.h5 file; missing point/acceleration.")
    names = handle["names_ELASTIC_point"]
    data = handle["point/acceleration"]
    if len(data.shape) != 3:
        raise NotImplementedError(f"{path} point/acceleration must have shape (receiver, component, sample).")
    if int(data.shape[0]) != int(names.shape[0]):
        raise ValueError(f"{path} names_ELASTIC_point count does not match point/acceleration receiver count.")


def _salvus_sampling_rate(handle: Any) -> float:
    """Return Salvus sampling rate from point attrs."""

    point = handle["point"]
    if "sampling_rate_in_hertz" not in point.attrs:
        raise NotImplementedError("Salvus receivers.h5 point group is missing sampling_rate_in_hertz.")
    raw = point.attrs["sampling_rate_in_hertz"]
    return float(raw[0] if hasattr(raw, "__len__") else raw)


def _salvus_start_offset(handle: Any) -> float:
    """Return Salvus start-time offset from point attrs."""

    raw = handle["point"].attrs.get("start_time_in_seconds", [0.0])
    return float(raw[0] if hasattr(raw, "__len__") else raw)


def _parse_salvus_receiver_name(raw_name: str) -> tuple[str, str, str]:
    """Parse one Salvus receiver name into network, station, and location."""

    parts = str(raw_name).strip().split(".")
    while len(parts) < 3:
        parts.append("")
    return str(parts[0]).strip().upper(), str(parts[1]).strip().upper(), str(parts[2]).strip().upper()


def _decode_hdf5_text(value: Any) -> str:
    """Decode one HDF5 string-like value."""

    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _component_from_channel(channel: str) -> str:
    """Return the final component letter from a channel code."""

    text = str(channel or "").strip().upper()
    return text[-1:] if text else ""


def _channel_with_component(channel: str, component: str) -> str:
    """Return a channel code with the final component replaced."""

    text = str(channel or "").strip()
    if not text:
        return component
    return f"{text[:-1]}{component}"


def _select_component(stream: Any, component: str):
    """Return traces whose channel suffix matches one component."""

    return stream.__class__([trace for trace in stream if _component_from_channel(getattr(trace.stats, "channel", "")) == component])


def _rotate_nez_to_requested_rt(stream: Any, request: SalvusConversionRequest, wanted: tuple[str, ...]):
    """Rotate matching N/E trace pairs to requested R/T components."""

    if request.event_latitude is None or request.event_longitude is None:
        raise ValueError("event_latitude and event_longitude are required when Salvus conversion requests R or T components.")
    if not request.station_coordinates:
        raise ValueError("station_coordinates are required when Salvus conversion requests R or T components.")
    try:
        from obspy import Stream
        from obspy.geodetics import gps2dist_azimuth
        from obspy.signal.rotate import rotate_ne_rt
    except Exception as exc:
        raise RuntimeError("ObsPy geodetics and signal rotation helpers are required for Salvus R/T conversion.") from exc

    output = Stream()
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for trace in stream:
        component = _component_from_channel(getattr(trace.stats, "channel", ""))
        if component not in {"N", "E"}:
            continue
        key = (str(getattr(trace.stats, "network", "")), str(getattr(trace.stats, "station", "")), str(getattr(trace.stats, "location", "")))
        grouped.setdefault(key, {})[component] = trace

    for key, traces in grouped.items():
        north = traces.get("N")
        east = traces.get("E")
        if north is None or east is None:
            continue
        coords = _station_coordinates_for_trace(north, request.station_coordinates)
        if coords is None:
            station_name = ".".join(part for part in key if part)
            raise ValueError(f"Missing station coordinates for {station_name or key[1]} needed for Salvus R/T conversion.")
        _, _, back_azimuth = gps2dist_azimuth(
            float(request.event_latitude),
            float(request.event_longitude),
            float(coords["latitude"]),
            float(coords["longitude"]),
        )
        radial, transverse = rotate_ne_rt(north.data, east.data, back_azimuth)
        if "R" in wanted:
            r_trace = north.copy()
            r_trace.data = radial
            r_trace.stats.channel = _channel_with_component(getattr(r_trace.stats, "channel", ""), "R")
            output += r_trace
        if "T" in wanted:
            t_trace = east.copy()
            t_trace.data = transverse
            t_trace.stats.channel = _channel_with_component(getattr(t_trace.stats, "channel", ""), "T")
            output += t_trace
    return output


def _station_coordinates_for_trace(trace: Any, coordinates: Mapping[str, Mapping[str, float]]) -> Mapping[str, float] | None:
    """Return latitude/longitude for one trace from stats or a lookup mapping."""

    stats_coords = getattr(trace.stats, "coordinates", None)
    if stats_coords is not None and hasattr(stats_coords, "latitude") and hasattr(stats_coords, "longitude"):
        return {"latitude": float(stats_coords.latitude), "longitude": float(stats_coords.longitude)}
    keys = [
        ".".join(part for part in (getattr(trace.stats, "network", ""), getattr(trace.stats, "station", ""), getattr(trace.stats, "location", "")) if part),
        ".".join(part for part in (getattr(trace.stats, "network", ""), getattr(trace.stats, "station", "")) if part),
        str(getattr(trace.stats, "station", "")),
    ]
    for key in keys:
        if key in coordinates:
            value = coordinates[key]
            if "latitude" in value and "longitude" in value:
                return value
            if "lat" in value and "lon" in value:
                return {"latitude": float(value["lat"]), "longitude": float(value["lon"])}
    return None


def _safe_token(value: Any) -> str:
    """Return a filesystem-safe token for converted synthetic filenames."""

    text = str(value).strip()
    safe = "".join(char if char.isalnum() or char in {"-", "_", "."} else "-" for char in text)
    return safe.strip("-_") or "event"


__all__ = [
    "SalvusConversionRequest",
    "SALVUS_ACCELERATION_SCALE_MPS2_TO_CMPS2",
    "SyntheticFormatInfo",
    "SyntheticReadRequest",
    "SyntheticReader",
    "inspect_synthetic_format",
    "normalize_salvus_outputs_once",
    "normalize_salvus_stream",
    "prompt_for_salvus_handling",
    "read_salvus_receivers_h5",
    "synthetic_reader_for",
    "write_normalized_salvus_mseed",
    "write_salvus_receivers_h5_mseed",
]
