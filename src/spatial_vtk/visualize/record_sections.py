"""Record-section figure helpers for Spatial-VTK.

Purpose
-------
This module draws generic record-section figures from explicit waveform tables.
It is intentionally independent of private data roots and accepts arrays,
ObsPy-like traces, or table rows prepared by upstream package functions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from spatial_vtk.visualize.figure_context import title_with_subtitle
from spatial_vtk.visualize.figure_sidecars import finish_figure_with_sidecar
from spatial_vtk.visualize.selection import FigureSelection


def save_record_section_figure(fig: plt.Figure, output_path: str | Path, *, close: bool = True, dpi: int = 180) -> Path:
    """Save a record-section figure and return the written path.

    Parameters
    ----------
    fig
        Matplotlib figure.
    output_path
        Destination image path.
    close
        Whether to close the figure after saving.
    dpi
        Raster resolution.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", dpi=int(dpi))
    if close:
        plt.close(fig)
    return path


def trace_component(trace: Any) -> str:
    """Return the component suffix from an ObsPy-like trace.

    Parameters
    ----------
    trace
        Trace object with optional ``stats.channel`` metadata.

    Returns
    -------
    str
        Uppercase component suffix, or an empty string when unavailable.
    """

    stats = getattr(trace, "stats", None)
    channel = str(getattr(stats, "channel", "") or "").strip().upper()
    return channel[-1:] if channel else ""


def trace_station(trace: Any) -> str:
    """Return a compact station label from an ObsPy-like trace.

    Parameters
    ----------
    trace
        Trace object with optional network/station/location metadata.

    Returns
    -------
    str
        Station label.
    """

    stats = getattr(trace, "stats", None)
    network = str(getattr(stats, "network", "") or "").strip().upper()
    station = str(getattr(stats, "station", "") or "").strip().upper()
    location = str(getattr(stats, "location", "") or "").strip().upper()
    parts = [part for part in (network, station, location) if part]
    return ".".join(parts) if parts else ""


def trace_to_array(value: Any, *, default_dt: float = 1.0) -> tuple[np.ndarray, float]:
    """Convert an array-like value or ObsPy-like trace to waveform samples.

    Parameters
    ----------
    value
        Numeric array, lightweight trace dictionary, or trace object with
        ``data`` and optional ``stats``.
    default_dt
        Sample interval used when metadata are unavailable.

    Returns
    -------
    tuple
        ``(samples, dt_seconds)``.
    """

    if isinstance(value, dict):
        data = np.asarray(value.get("data", []), dtype=float)
        stats = value.get("stats", {})
        dt = stats.get("delta") if isinstance(stats, dict) else getattr(stats, "delta", None)
        if dt is None:
            if isinstance(stats, dict):
                sampling_rate = stats.get("sampling_rate")
            else:
                sampling_rate = getattr(stats, "sampling_rate", None)
            dt = 1.0 / float(sampling_rate) if sampling_rate else default_dt
        return data, float(dt)
    if hasattr(value, "data"):
        data = np.asarray(value.data, dtype=float)
        stats = getattr(value, "stats", None)
        dt = getattr(stats, "delta", None)
        if dt is None:
            sampling_rate = getattr(stats, "sampling_rate", None)
            dt = 1.0 / float(sampling_rate) if sampling_rate else default_dt
        return data, float(dt)
    return np.asarray(value, dtype=float), float(default_dt)


def row_sample_interval(row: pd.Series, column: str | None, default: float = 1.0) -> float:
    """Read a finite positive sample interval from a dataframe row.

    Parameters
    ----------
    row
        Record row that may contain sample interval metadata.
    column
        Column containing sample interval values in seconds.
    default
        Fallback sample interval.

    Returns
    -------
    float
        Sample interval in seconds.
    """

    if column and column in row.index and pd.notna(row.get(column)):
        try:
            value = float(row.get(column))
        except (TypeError, ValueError):
            value = float(default)
        if np.isfinite(value) and value > 0.0:
            return value
    return float(default)


def row_time_offset(row: pd.Series, column: str | None, default: float = 0.0) -> float:
    """Read a finite trace time offset from a dataframe row.

    Parameters
    ----------
    row
        Record row that may contain time-offset metadata.
    column
        Column containing seconds relative to the event origin.
    default
        Fallback offset in seconds.

    Returns
    -------
    float
        Time offset in seconds.
    """

    if column and column in row.index and pd.notna(row.get(column)):
        try:
            value = float(row.get(column))
        except (TypeError, ValueError):
            value = float(default)
        if np.isfinite(value):
            return value
    return float(default)


def normalize_trace(data: np.ndarray) -> np.ndarray:
    """Normalize one trace by peak absolute amplitude.

    Parameters
    ----------
    data
        Waveform samples.

    Returns
    -------
    numpy.ndarray
        Normalized samples.
    """

    samples = np.asarray(data, dtype=float)
    peak = float(np.nanmax(np.abs(samples))) if samples.size else 0.0
    if not np.isfinite(peak) or peak <= 0.0:
        return np.zeros_like(samples, dtype=float)
    return samples / peak


def build_record_section_rows(
    records: pd.DataFrame | Iterable[Any],
    *,
    trace_col: str = "trace",
    station_col: str = "station",
    component_col: str | None = "component",
    distance_col: str = "distance_km",
    default_dt: float = 1.0,
) -> pd.DataFrame:
    """Normalize traces or a record table to the plotting row contract.

    Parameters
    ----------
    records
        DataFrame with trace rows or iterable of trace-like objects.
    trace_col
        Trace column used when ``records`` is a DataFrame.
    station_col
        Station label column.
    component_col
        Optional component column.
    distance_col
        Optional distance column.
    default_dt
        Sample interval used for array inputs without metadata.

    Returns
    -------
    pandas.DataFrame
        Table with ``trace``, ``dt``, ``station``, ``component``, and
        ``distance_km`` columns where available.
    """

    if isinstance(records, pd.DataFrame):
        if trace_col not in records.columns:
            raise KeyError(f"records must include a '{trace_col}' column.")
        rows: list[dict[str, Any]] = []
        for _, row in records.iterrows():
            samples, dt = trace_to_array(row[trace_col], default_dt=default_dt)
            station = row.get(station_col, "") if station_col in records.columns else trace_station(row[trace_col])
            component = row.get(component_col, "") if component_col and component_col in records.columns else trace_component(row[trace_col])
            distance = row.get(distance_col, np.nan) if distance_col in records.columns else np.nan
            rows.append(
                {
                    "trace": samples,
                    "dt": float(dt),
                    "station": str(station),
                    "component": str(component).upper(),
                    "distance_km": pd.to_numeric(distance, errors="coerce"),
                }
            )
        return pd.DataFrame(rows)

    rows = []
    for trace in records:
        samples, dt = trace_to_array(trace, default_dt=default_dt)
        rows.append(
            {
                "trace": samples,
                "dt": float(dt),
                "station": trace_station(trace),
                "component": trace_component(trace),
                "distance_km": getattr(getattr(trace, "stats", None), "distance", np.nan) / 1000.0,
            }
        )
    return pd.DataFrame(rows)


def _prepare_record_section_records(
    records: pd.DataFrame,
    *,
    trace_col: str,
    station_col: str,
    component_col: str | None,
) -> pd.DataFrame:
    """Return record-section rows with path-backed waveforms loaded as traces."""

    if trace_col in records.columns and not _column_contains_waveform_paths(records[trace_col]):
        return records
    out = records.copy()
    path_col = trace_col if trace_col in out.columns else _first_existing_trace_path_column(out.columns)
    if path_col is None:
        return out
    cache: dict[str, object] = {}
    out[trace_col] = [
        _load_trace_for_record_section(row.get(path_col), row, station_col=station_col, component_col=component_col, cache=cache)
        for _, row in out.iterrows()
    ]
    return out


def prepare_waveform_plot_records(
    records: pd.DataFrame,
    *,
    waveform_col: str = "trace",
    station_col: str = "station",
    component_col: str | None = "component",
    station_lon_col: str | None = None,
    station_lat_col: str | None = None,
    event_lon_col: str | None = None,
    event_lat_col: str | None = None,
    distance_col: str | None = None,
    azimuth_col: str | None = None,
    group_col: str | None = None,
    default_group: str = "All records",
) -> pd.DataFrame:
    """Normalize event-station records for single-waveform plotting helpers."""

    out = prepare_waveform_plot_metadata(
        records,
        station_lon_col=station_lon_col,
        station_lat_col=station_lat_col,
        event_lon_col=event_lon_col,
        event_lat_col=event_lat_col,
        distance_col=distance_col,
        azimuth_col=azimuth_col,
        group_col=group_col,
        default_group=default_group,
    )
    return _prepare_record_section_records(
        out,
        trace_col=waveform_col,
        station_col=station_col,
        component_col=component_col,
    )


def prepare_waveform_plot_metadata(
    records: pd.DataFrame,
    *,
    station_lon_col: str | None = None,
    station_lat_col: str | None = None,
    event_lon_col: str | None = None,
    event_lat_col: str | None = None,
    distance_col: str | None = None,
    azimuth_col: str | None = None,
    group_col: str | None = None,
    default_group: str = "All records",
) -> pd.DataFrame:
    """Normalize event-station metadata aliases without loading waveforms."""

    out = records.copy()
    _copy_first_existing_column(out, station_lon_col, ("sta_lon", "station_lon", "station_longitude", "lon", "longitude"))
    _copy_first_existing_column(out, station_lat_col, ("sta_lat", "station_lat", "station_latitude", "lat", "latitude"))
    _copy_first_existing_column(out, event_lon_col, ("event_lon", "event_longitude", "origin_lon", "origin_longitude", "source_lon", "source_longitude"))
    _copy_first_existing_column(out, event_lat_col, ("event_lat", "event_latitude", "origin_lat", "origin_latitude", "source_lat", "source_latitude"))
    _copy_first_existing_column(out, distance_col, ("distance_km", "distance", "source_distance_km", "hypocentral_distance_km", "epicentral_distance_km"))
    _copy_first_existing_column(out, azimuth_col, ("azimuth_deg", "azimuth", "station_azimuth_deg", "source_azimuth_deg"))
    if group_col and group_col not in out.columns:
        out[group_col] = _default_waveform_group(out, default_group=default_group)
    return out


def prepare_observed_synthetic_waveform_records(
    records: pd.DataFrame,
    *,
    observed_col: str = "observed",
    synthetic_col: str = "synthetic",
    station_col: str = "station",
    component_col: str | None = "component",
) -> pd.DataFrame:
    """Normalize event-station records for observed/synthetic waveform plots."""

    out = records.copy()
    cache: dict[str, object] = {}
    out = _prepare_source_waveform_column(
        out,
        target_col=observed_col,
        source="observed",
        station_col=station_col,
        component_col=component_col,
        cache=cache,
    )
    out = _prepare_source_waveform_column(
        out,
        target_col=synthetic_col,
        source="synthetic",
        station_col=station_col,
        component_col=component_col,
        cache=cache,
    )
    return out


def _prepare_source_waveform_column(
    records: pd.DataFrame,
    *,
    target_col: str,
    source: str,
    station_col: str,
    component_col: str | None,
    cache: dict[str, object] | None = None,
) -> pd.DataFrame:
    """Load one observed or synthetic path column into a target waveform column."""

    if target_col in records.columns and not _column_contains_waveform_paths(records[target_col]):
        return records
    out = records.copy()
    path_col = target_col if target_col in out.columns else _first_existing_source_path_column(out.columns, source)
    if path_col is None:
        return out
    out[target_col] = [
        _load_trace_for_record_section(row.get(path_col), row, station_col=station_col, component_col=component_col, cache=cache)
        for _, row in out.iterrows()
    ]
    return out


def _first_existing_source_path_column(columns: Iterable[str], source: str) -> str | None:
    """Return the first likely waveform path column for one source."""

    source_key = str(source).strip().lower()
    aliases = {
        "observed": ("observed", "obs"),
        "synthetic": ("synthetic", "syn"),
    }.get(source_key, (source_key,))
    column_set = {str(column) for column in columns}
    explicit: list[str] = []
    for alias in aliases:
        explicit.extend(
            [
                f"{alias}_processed_waveform",
                f"{alias}_raw_waveform",
                f"{alias}_waveform",
                f"{alias}_waveform_path",
                f"{alias}_path",
                f"{alias}_mseed",
                f"{alias}_pickle",
            ]
        )
    for column in explicit:
        if column in column_set:
            return column
    for column in column_set:
        text = column.strip().lower()
        if not any(text.startswith(f"{alias}_") for alias in aliases):
            continue
        if "preprocessing" in text:
            continue
        if any(token in text for token in ("path", "waveform", "mseed", "pickle", "pkl", "asdf")):
            return column
    return None


def _copy_first_existing_column(out: pd.DataFrame, target_col: str | None, candidates: tuple[str, ...]) -> None:
    """Copy a compatible source column into a missing target column."""

    if not target_col or target_col in out.columns:
        return
    source_col = next((column for column in candidates if column in out.columns), None)
    if source_col is not None:
        out[target_col] = out[source_col]


def _default_waveform_group(records: pd.DataFrame, *, default_group: str) -> object:
    """Return a default group label for overlay figures."""

    for column in ("event_id", "event_name", "event_title"):
        if column in records.columns:
            values = [str(value).strip() for value in records[column].dropna().unique() if str(value).strip()]
            if len(values) == 1:
                return values[0]
    return default_group


def _select_record_section_event(records: pd.DataFrame, *, event_col: str | None, event_id: str | None) -> pd.DataFrame:
    """Keep record-section waveform loading scoped to one event by default."""

    if not event_col or event_col not in records.columns:
        return records
    if event_id is not None:
        event_text = str(event_id).strip()
        if event_text.lower() in {"", "all", "*"}:
            return records
        return records.loc[records[event_col].astype(str).eq(event_text)].copy()
    event_values = records[event_col].dropna().astype(str)
    if event_values.nunique() <= 1:
        return records
    counts = event_values.value_counts(sort=False)
    selected_event = str(counts.idxmax())
    return records.loc[records[event_col].astype(str).eq(selected_event)].copy()


def _preselect_record_section_records(
    records: pd.DataFrame,
    *,
    components: Iterable[str] | None,
    component_col: str | None,
    station_col: str,
    distance_col: str,
    max_records: int | None,
) -> pd.DataFrame:
    """Apply record-section row limits before path-backed waveforms are loaded."""

    if components is None:
        if component_col and component_col in records.columns:
            component_values = sorted(value for value in records[component_col].dropna().astype(str).unique().tolist() if value)
            components = component_values or ["Trace"]
        else:
            components = ["Trace"]
    selected_components = [str(component).upper() for component in components]
    if component_col and component_col not in records.columns and selected_components and all(component != "TRACE" for component in selected_components):
        subset = _sorted_record_section_subset(records.copy(), station_col=station_col, distance_col=distance_col)
        if max_records is not None:
            subset = _limit_record_section_subset(subset, max_records=int(max_records), distance_col=distance_col)
        repeated = subset.loc[subset.index.repeat(len(selected_components))].copy()
        repeated[component_col] = np.tile(selected_components, len(subset))
        return repeated.reset_index(drop=True)
    frames: list[pd.DataFrame] = []
    for component in selected_components:
        subset = records
        if component_col and component_col in records.columns and component != "TRACE":
            subset = subset.loc[subset[component_col].astype(str).str.upper().isin([component, ""])]
        subset = subset.copy()
        if component_col and component_col not in subset.columns and component != "TRACE":
            subset[component_col] = component
        subset = _sorted_record_section_subset(subset, station_col=station_col, distance_col=distance_col)
        if max_records is not None:
            subset = _limit_record_section_subset(subset, max_records=int(max_records), distance_col=distance_col)
        frames.append(subset)
    return pd.concat(frames, ignore_index=True, sort=False) if frames else records.head(0).copy()


def _sorted_record_section_subset(subset: pd.DataFrame, *, station_col: str, distance_col: str) -> pd.DataFrame:
    """Return a stable record-section row order before row limiting."""

    if distance_col in subset.columns:
        subset[distance_col] = pd.to_numeric(subset[distance_col], errors="coerce")
        sort_columns = [distance_col]
        if station_col in subset.columns:
            sort_columns.append(station_col)
        return subset.sort_values(sort_columns, na_position="last")
    if station_col in subset.columns:
        return subset.sort_values(station_col)
    return subset


def _limit_record_section_subset(subset: pd.DataFrame, *, max_records: int, distance_col: str) -> pd.DataFrame:
    """Limit a sorted component subset while preserving distance coverage."""

    if max_records <= 0:
        return subset.head(0).copy()
    if len(subset) <= max_records:
        return subset
    if distance_col not in subset.columns:
        return subset.head(max_records)
    distances = pd.to_numeric(subset[distance_col], errors="coerce")
    finite = np.isfinite(distances.to_numpy(dtype=float))
    if not finite.any():
        return subset.head(max_records)
    finite_subset = subset.loc[finite]
    if len(finite_subset) <= max_records:
        return finite_subset
    indices = np.linspace(0, len(finite_subset) - 1, max_records)
    ilocs = np.unique(np.rint(indices).astype(int))
    return finite_subset.iloc[ilocs].copy()


def _first_existing_trace_path_column(columns: Iterable[str]) -> str | None:
    """Return the first likely waveform path column for a single-trace section."""

    column_set = {str(column) for column in columns}
    explicit = [
        "trace_path",
        "waveform_path",
        "path",
        "file",
        "filename",
        "filepath",
        "observed_processed_waveform",
        "observed_raw_waveform",
        "observed_waveform",
        "observed_waveform_path",
        "observed_path",
        "obs_waveform_path",
        "obs_path",
        "synthetic_processed_waveform",
        "synthetic_raw_waveform",
        "synthetic_waveform",
        "synthetic_waveform_path",
        "synthetic_path",
        "syn_waveform_path",
        "syn_path",
    ]
    for column in explicit:
        if column in column_set:
            return column
    for column in column_set:
        text = column.strip().lower()
        if "preprocessing" in text:
            continue
        if any(token in text for token in ("path", "waveform", "mseed", "pickle", "pkl", "asdf")):
            return column
    return None


def _column_contains_waveform_paths(series: pd.Series) -> bool:
    """Return whether a dataframe column appears to contain waveform paths."""

    for value in series:
        if not _nonempty_waveform_path_value(value):
            continue
        if _is_waveform_path_like(value):
            return True
        return False
    return False


def _is_waveform_path_like(value: object) -> bool:
    """Return whether a value looks like a waveform file path."""

    if isinstance(value, Path):
        return True
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text or text[:1] in {"[", "{"}:
        return False
    suffix = Path(text).suffix.lower()
    if suffix in {".npz", ".npy", ".pkl", ".pickle", ".asdf", ".mseed", ".ms", ".sac"}:
        return True
    return any(separator in text for separator in ("/", "\\"))


def _load_trace_for_record_section(
    value: object,
    row: pd.Series,
    *,
    station_col: str,
    component_col: str | None,
    cache: dict[str, object] | None = None,
) -> object:
    """Load one waveform path cell and select the row's best matching trace."""

    if not _nonempty_waveform_path_value(value):
        return np.asarray([], dtype=float)
    from spatial_vtk.io.waveforms import read_waveform_file

    waveform_path = Path(str(value)).expanduser()
    cache_key = str(waveform_path)
    if cache is not None and cache_key in cache:
        traces = cache.pop(cache_key)
        cache[cache_key] = traces
    else:
        traces = read_waveform_file(waveform_path)
        if cache is not None:
            cache[cache_key] = traces
            while len(cache) > 2:
                cache.pop(next(iter(cache)))
    if isinstance(traces, (list, tuple)):
        return _select_trace_for_record_section(traces, row, station_col=station_col, component_col=component_col)
    if hasattr(traces, "select") and component_col and component_col in row.index:
        component = str(row.get(component_col, "") or "").strip().upper()
        if component:
            try:
                selected = traces.select(component=component)
            except Exception:
                selected = []
            if selected:
                return selected[0]
    if hasattr(traces, "__iter__") and not hasattr(traces, "data") and not isinstance(traces, (str, bytes, dict)):
        trace_list = list(traces)
        if trace_list:
            return _select_trace_for_record_section(trace_list, row, station_col=station_col, component_col=component_col)
    return traces


def _select_trace_for_record_section(
    traces: Iterable[object],
    row: pd.Series,
    *,
    station_col: str,
    component_col: str | None,
) -> object:
    """Select the trace matching the row station/component when available."""

    trace_list = list(traces)
    if not trace_list:
        return np.asarray([], dtype=float)
    station = str(row.get(station_col, "") or "").strip().upper() if station_col in row.index else ""
    component = str(row.get(component_col, "") or "").strip().upper() if component_col and component_col in row.index else ""
    for require_station, require_component in ((True, True), (False, True), (True, False)):
        for trace in trace_list:
            if require_station and station and _trace_station_value(trace) not in {"", station}:
                continue
            if require_component and component and _trace_component_value(trace) not in {"", component}:
                continue
            return trace
    return trace_list[0]


def _trace_station_value(trace: object) -> str:
    """Return a normalized station code from a trace-like object."""

    stats = trace.get("stats", {}) if isinstance(trace, dict) else getattr(trace, "stats", None)
    return str(_trace_stat_value(stats, "station", "") or "").strip().upper()


def _trace_component_value(trace: object) -> str:
    """Return a normalized component code from a trace-like object."""

    stats = trace.get("stats", {}) if isinstance(trace, dict) else getattr(trace, "stats", None)
    component = str(_trace_stat_value(stats, "component", "") or "").strip().upper()
    channel = str(_trace_stat_value(stats, "channel", "") or "").strip().upper()
    return component or (channel[-1:] if channel else "")


def _trace_stat_value(stats: object, key: str, default: object = None) -> object:
    """Read one stat value from mapping- or attribute-style metadata."""

    if stats is None:
        return default
    if isinstance(stats, dict):
        return stats.get(key, default)
    return getattr(stats, key, default)


def _nonempty_waveform_path_value(value: object) -> bool:
    """Return whether a table cell contains a non-empty waveform path."""

    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except Exception:
        pass
    text = str(value).strip()
    return text.lower() not in {"", "nan", "none", "null"}


def _section_y_positions(df: pd.DataFrame, distance_col: str) -> np.ndarray:
    """Return finite y positions for a record section.

    Parameters
    ----------
    df
        Plotting rows.
    distance_col
        Distance column name.

    Returns
    -------
    numpy.ndarray
        Y positions.
    """

    if distance_col in df.columns:
        values = pd.to_numeric(df[distance_col], errors="coerce").to_numpy(dtype=float)
        if np.isfinite(values).all():
            return values
    return np.arange(len(df), dtype=float)


def _trace_half_height(y_positions: np.ndarray, scale: float) -> float:
    """Return a stable vertical half-height for section traces.

    Parameters
    ----------
    y_positions
        Section y positions.
    scale
        User gain multiplier.

    Returns
    -------
    float
        Half-height in y-axis units.
    """

    unique_y = np.unique(np.sort(y_positions))
    diffs = np.diff(unique_y)
    diffs = diffs[diffs > 0.0]
    spacing = float(np.median(diffs)) if len(diffs) else 1.0
    return max(0.25, 0.38 * spacing * float(scale))


def plot_record_section(
    records: pd.DataFrame | Iterable[Any],
    output_path: str | Path | None = None,
    *,
    trace_col: str = "trace",
    station_col: str = "station",
    component_col: str | None = "component",
    distance_col: str = "distance_km",
    event_col: str = "event_id",
    event_id: str | None = None,
    components: Iterable[str] | None = None,
    selection: FigureSelection | None = None,
    max_records: int | None = 80,
    normalize: bool = True,
    scale: float = 1.0,
    title: str = "Record Section",
    filter_label: str | None = None,
    default_dt: float = 1.0,
    time_limit_s: float | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
) -> plt.Figure:
    """Plot one or more component record sections.

    Parameters
    ----------
    records
        Record table or iterable of trace-like objects.
    output_path
        Destination figure path.
    trace_col
        Trace column for DataFrame inputs.
    station_col
        Station label column.
    component_col
        Optional component column.
    distance_col
        Optional distance column.
    event_col
        Optional event identifier column used to keep default record sections
        to a single event before waveform files are loaded.
    event_id
        Optional event id to plot. When omitted and ``event_col`` contains
        multiple events, the event with the most records is used. Set to
        ``"all"`` to disable this default narrowing.
    components
        Optional ordered component subset.
    max_records
        Maximum traces to draw per component.
    normalize
        Whether to normalize each trace before plotting.
    scale
        Multiplicative plotting gain.
    title
        Figure title.
    filter_label
        Optional second title line describing any bandpass or lowpass filter.
    default_dt
        Sample interval used for array inputs without metadata.
    time_limit_s
        Optional upper time limit in seconds. When provided, traces are
        cropped to the plotted window and the x-axis is fixed to
        ``0..time_limit_s``.
    write_sidecar
        Whether to write a CSV/JSON sidecar with the record-section rows
        plotted in the figure. Sidecars are written only when the figure is
        saved.
    sidecar_rows
        Maximum plotted/source rows to write. ``None`` writes all rows.
    sidecar_dir
        Optional directory for sidecar files.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    source_records = records.copy() if isinstance(records, pd.DataFrame) else None
    input_records = selection.apply(records) if isinstance(records, pd.DataFrame) and selection is not None else records
    if isinstance(input_records, pd.DataFrame):
        input_records = _select_record_section_event(input_records, event_col=event_col, event_id=event_id)
        input_records = _preselect_record_section_records(
            input_records,
            components=components,
            component_col=component_col,
            station_col=station_col,
            distance_col=distance_col,
            max_records=max_records,
        )
        input_records = _prepare_record_section_records(
            input_records,
            trace_col=trace_col,
            station_col=station_col,
            component_col=component_col,
        )
    rows = build_record_section_rows(
        input_records,
        trace_col=trace_col,
        station_col=station_col,
        component_col=component_col,
        distance_col=distance_col,
        default_dt=default_dt,
    )
    if rows.empty:
        fig, ax = plt.subplots(figsize=(7.0, 4.0), dpi=180)
        ax.text(0.5, 0.5, "No record-section rows", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        ax.set_title(title)
        return finish_figure_with_sidecar(
            fig,
            output_path,
            outpath=outpath,
            showfig=showfig,
            savefig=savefig,
            sidecar_df=rows,
            source_rows=source_records,
            write_sidecar=write_sidecar,
            sidecar_rows=sidecar_rows,
            sidecar_dir=sidecar_dir,
            metadata={"figure_type": "record_section", "max_records": max_records},
        )

    if components is None:
        component_values = sorted(value for value in rows["component"].dropna().astype(str).unique().tolist() if value)
        components = component_values or ["Trace"]
    components = [str(component).upper() for component in components]
    fig, axes = plt.subplots(1, len(components), figsize=(max(6.0, 4.8 * len(components)), 6.6), dpi=180, sharey=True)
    axes = np.atleast_1d(axes)
    plotted_frames: list[pd.DataFrame] = []
    for ax, component in zip(axes, components):
        subset = rows if component == "TRACE" else rows.loc[rows["component"].astype(str).str.upper().isin([component, ""])]
        subset = subset.sort_values(["distance_km", "station"], na_position="last")
        if max_records is not None:
            subset = subset.head(int(max_records))
        plotted_frames.append(subset.copy())
        if subset.empty:
            ax.text(0.5, 0.5, f"No {component} traces", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(f"{component} component")
            continue
        y_positions = _section_y_positions(subset, "distance_km")
        half_height = _trace_half_height(y_positions, scale)
        max_time = 0.0
        for row_idx, (_, row) in enumerate(subset.iterrows()):
            data = np.asarray(row["trace"], dtype=float)
            if time_limit_s is not None and np.isfinite(float(time_limit_s)) and float(time_limit_s) > 0.0:
                max_npts = max(1, int(np.floor(float(time_limit_s) / max(float(row["dt"]), 1.0e-12))) + 1)
                data = data[:max_npts]
            if normalize:
                data = normalize_trace(data)
            time = np.arange(len(data), dtype=float) * float(row["dt"])
            max_time = max(max_time, float(time[-1]) if len(time) else 0.0)
            y0 = float(y_positions[row_idx])
            ax.plot(time, y0 + data * half_height, color="black", linewidth=0.72)
        ax.set_title(f"{component} component")
        ax.set_xlabel("Time (s)")
        if time_limit_s is not None and np.isfinite(float(time_limit_s)) and float(time_limit_s) > 0.0:
            ax.set_xlim(0.0, float(time_limit_s))
        else:
            ax.set_xlim(0.0, max(max_time, 1.0))
        ax.grid(True, alpha=0.18)
    if np.isfinite(pd.to_numeric(rows["distance_km"], errors="coerce")).all():
        axes[0].set_ylabel("Distance (km)")
    else:
        axes[0].set_ylabel("Record")
    fig.suptitle(title_with_subtitle(title, filter_label), y=0.99)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
    sidecar_df = pd.concat(plotted_frames, ignore_index=True, sort=False) if plotted_frames else pd.DataFrame()
    return finish_figure_with_sidecar(
        fig,
        output_path,
        outpath=outpath,
        showfig=showfig,
        savefig=savefig,
        sidecar_df=sidecar_df,
        source_rows=source_records,
        write_sidecar=write_sidecar,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
        metadata={"figure_type": "record_section", "max_records": max_records, "time_limit_s": time_limit_s},
    )


def plot_observed_synthetic_record_section(
    records_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    observed_col: str = "observed",
    synthetic_col: str = "synthetic",
    dt_col: str = "dt",
    synthetic_dt_col: str = "synthetic_dt",
    observed_time_offset_col: str = "observed_time_offset_s",
    synthetic_time_offset_col: str = "synthetic_time_offset_s",
    station_col: str = "station",
    component_col: str | None = "component",
    distance_col: str = "distance_km",
    event_col: str = "event_id",
    network_col: str = "network",
    event_id: str | None = None,
    components: Iterable[str] | None = None,
    selection: FigureSelection | None = None,
    max_records: int | None = 80,
    normalize: bool = True,
    scale: float = 1.0,
    annotate_records: bool = False,
    title: str = "Observed and Synthetic Record Section",
    filter_label: str | None = None,
    default_dt: float = 1.0,
    time_limit_s: float | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
) -> plt.Figure:
    """Plot observed and synthetic traces on shared record-section axes.

    Parameters
    ----------
    records_df
        Table with observed and synthetic waveform columns.
    output_path
        Destination figure path.
    observed_col, synthetic_col
        Waveform columns.
    dt_col, synthetic_dt_col
        Row-level sample interval columns for array-backed observed and
        synthetic waveforms.
    observed_time_offset_col, synthetic_time_offset_col
        Optional columns giving trace start time in seconds relative to the
        event origin. When present, the x-axis is event-origin-relative.
    station_col
        Station label column.
    component_col
        Optional component column.
    distance_col
        Optional distance column.
    event_col, network_col
        Optional columns used for per-trace labels when ``annotate_records`` is
        true.
    event_id
        Optional event id to plot. When omitted and ``event_col`` contains
        multiple events, the event with the most records is used. Set to
        ``"all"`` to disable this default narrowing.
    components
        Optional ordered component subset.
    max_records
        Maximum rows to draw per component.
    normalize
        Whether to normalize each trace before plotting.
    scale
        Multiplicative plotting gain.
    annotate_records
        Whether to label each plotted trace with station and event identity.
    title
        Figure title.
    filter_label
        Optional second title line describing any bandpass or lowpass filter.
    default_dt
        Sample interval used for array inputs without metadata.
    time_limit_s
        Optional maximum seconds to display from each trace start.
    write_sidecar
        Whether to write a CSV/JSON sidecar with the observed/synthetic rows
        plotted in the figure. Sidecars are written only when the figure is
        saved.
    sidecar_rows
        Maximum plotted/source rows to write. ``None`` writes all rows.
    sidecar_dir
        Optional directory for sidecar files.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    source_records = records_df.copy()
    rows = selection.apply(records_df) if selection is not None else records_df.copy()
    rows = _select_record_section_event(rows, event_col=event_col, event_id=event_id)
    rows = _preselect_record_section_records(
        rows,
        components=components,
        component_col=component_col,
        station_col=station_col,
        distance_col=distance_col,
        max_records=max_records,
    )
    rows = prepare_observed_synthetic_waveform_records(
        rows,
        observed_col=observed_col,
        synthetic_col=synthetic_col,
        station_col=station_col,
        component_col=component_col,
    )
    required = {observed_col, synthetic_col, station_col}
    missing = required - set(rows.columns)
    if missing:
        raise KeyError(f"records_df is missing required columns: {sorted(missing)}")
    if components is None:
        if component_col and component_col in rows.columns:
            components = sorted(value for value in rows[component_col].dropna().astype(str).unique().tolist() if value) or ["Trace"]
        else:
            components = ["Trace"]
    components = [str(component).upper() for component in components]
    has_time_offsets = observed_time_offset_col in rows.columns or synthetic_time_offset_col in rows.columns
    extra_width = 2.2 if annotate_records else 0.0
    fig, axes = plt.subplots(
        1,
        len(components),
        figsize=(max(6.0, 4.8 * len(components)) + extra_width, 6.6),
        dpi=180,
        sharey=True,
    )
    axes = np.atleast_1d(axes)
    plotted_frames: list[pd.DataFrame] = []
    for ax, component in zip(axes, components):
        subset = rows
        if component_col and component_col in rows.columns and component != "TRACE":
            subset = subset.loc[subset[component_col].astype(str).str.upper() == component]
        if distance_col in subset.columns:
            subset = subset.assign(**{distance_col: pd.to_numeric(subset[distance_col], errors="coerce")})
            subset = subset.sort_values([distance_col, station_col], na_position="last")
        else:
            subset = subset.sort_values(station_col)
        if max_records is not None:
            subset = subset.head(int(max_records))
        plotted_frames.append(subset.copy())
        if subset.empty:
            ax.text(0.5, 0.5, f"No {component} pairs", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(f"{component} component")
            continue
        y_positions = _section_y_positions(subset, distance_col)
        label_positions = _spread_record_section_label_positions(y_positions) if annotate_records else y_positions
        half_height = _trace_half_height(y_positions, scale)
        max_time = 0.0
        for row_idx, (_, row) in enumerate(subset.iterrows()):
            obs_default_dt = row_sample_interval(row, dt_col, default_dt)
            syn_default_dt = row_sample_interval(row, synthetic_dt_col, obs_default_dt)
            obs_data, obs_dt = trace_to_array(row[observed_col], default_dt=obs_default_dt)
            syn_data, syn_dt = trace_to_array(row[synthetic_col], default_dt=syn_default_dt)
            if len(obs_data) <= 1 or len(syn_data) <= 1:
                continue
            obs_offset = row_time_offset(row, observed_time_offset_col, 0.0)
            syn_offset = row_time_offset(row, synthetic_time_offset_col, 0.0)
            obs_time = obs_offset + np.arange(len(obs_data), dtype=float) * float(obs_dt)
            syn_time = syn_offset + np.arange(len(syn_data), dtype=float) * float(syn_dt)
            if time_limit_s is not None:
                limit = float(time_limit_s)
                obs_mask = (obs_time >= 0.0) & (obs_time <= limit)
                syn_mask = (syn_time >= 0.0) & (syn_time <= limit)
                obs_data = obs_data[obs_mask]
                syn_data = syn_data[syn_mask]
                obs_time = obs_time[obs_mask]
                syn_time = syn_time[syn_mask]
            if len(obs_data) <= 1 or len(syn_data) <= 1:
                continue
            if normalize:
                obs_data = normalize_trace(obs_data)
                syn_data = normalize_trace(syn_data)
            max_time = max(max_time, float(obs_time[-1]), float(syn_time[-1]))
            y0 = float(y_positions[row_idx])
            ax.plot(obs_time, y0 + obs_data * half_height, color="black", linewidth=0.72, label="Observed" if row_idx == 0 else None)
            ax.plot(syn_time, y0 + syn_data * half_height, color="#d04a35", linewidth=0.72, alpha=0.9, label="Synthetic" if row_idx == 0 else None)
            if annotate_records:
                label_y = float(label_positions[row_idx])
                if abs(label_y - y0) > 1e-9:
                    ax.plot(
                        [1.0, 1.008],
                        [y0, label_y],
                        transform=ax.get_yaxis_transform(),
                        color="0.55",
                        linewidth=0.45,
                        alpha=0.75,
                        clip_on=False,
                    )
                ax.text(
                    1.01,
                    label_y,
                    _record_section_identity_label(
                        row,
                        station_col=station_col,
                        event_col=event_col,
                        network_col=network_col,
                        distance_col=distance_col,
                    ),
                    transform=ax.get_yaxis_transform(),
                    ha="left",
                    va="center",
                    fontsize=6.6,
                    clip_on=False,
                )
        ax.set_title(f"{component} component")
        ax.set_xlabel("Seconds since event origin" if has_time_offsets else "Seconds since trace start")
        ax.set_xlim(0.0, max(max_time, 1.0))
        ax.grid(True, alpha=0.18)
    axes[0].set_ylabel("Distance (km)" if distance_col in rows.columns else "Record")
    axes[0].legend(loc="upper right")
    fig.suptitle(title_with_subtitle(title, filter_label), y=0.99)
    fig.tight_layout(rect=(0.0, 0.0, 0.82 if annotate_records else 1.0, 0.95))
    sidecar_df = pd.concat(plotted_frames, ignore_index=True, sort=False) if plotted_frames else pd.DataFrame()
    return finish_figure_with_sidecar(
        fig,
        output_path,
        outpath=outpath,
        showfig=showfig,
        savefig=savefig,
        sidecar_df=sidecar_df,
        source_rows=source_records,
        write_sidecar=write_sidecar,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
        metadata={"figure_type": "observed_synthetic_record_section", "max_records": max_records},
    )


def _spread_record_section_label_positions(y_positions: np.ndarray, *, min_gap_fraction: float = 0.035) -> np.ndarray:
    """Return y positions adjusted to reduce label overlap."""

    values = np.asarray(y_positions, dtype=float)
    if values.size <= 1:
        return values
    finite = np.isfinite(values)
    if not finite.any():
        return values
    out = values.copy()
    finite_values = values[finite]
    span = float(finite_values.max() - finite_values.min())
    min_gap = max(span * float(min_gap_fraction), 0.18)
    order = np.argsort(finite_values)
    sorted_values = finite_values[order].copy()
    adjusted = sorted_values.copy()
    for index in range(1, len(adjusted)):
        adjusted[index] = max(adjusted[index], adjusted[index - 1] + min_gap)
    top_overflow = adjusted[-1] - sorted_values[-1]
    if top_overflow > 0:
        adjusted -= top_overflow
    for index in range(len(adjusted) - 2, -1, -1):
        adjusted[index] = min(adjusted[index], adjusted[index + 1] - min_gap)
    adjusted_by_original = np.empty_like(adjusted)
    adjusted_by_original[order] = adjusted
    out[np.where(finite)[0]] = adjusted_by_original
    return out


def _record_section_identity_label(
    row: pd.Series,
    *,
    station_col: str,
    event_col: str,
    network_col: str,
    distance_col: str,
) -> str:
    """Return a compact station/event label for one waveform trace."""

    station = str(row.get(station_col, "") or "").strip()
    network = str(row.get(network_col, "") or "").strip()
    event = str(row.get(event_col, "") or "").strip()
    if network and station and not station.startswith(f"{network}."):
        station = f"{network}.{station}"
    parts = [part for part in (station, event) if part]
    try:
        distance = float(row.get(distance_col))
    except (TypeError, ValueError):
        distance = float("nan")
    if np.isfinite(distance):
        parts.append(f"{distance:.1f} km")
    return " | ".join(parts) or "record"


__all__ = [
    "build_record_section_rows",
    "normalize_trace",
    "plot_observed_synthetic_record_section",
    "plot_record_section",
    "prepare_observed_synthetic_waveform_records",
    "prepare_waveform_plot_metadata",
    "prepare_waveform_plot_records",
    "row_sample_interval",
    "row_time_offset",
    "save_record_section_figure",
    "trace_component",
    "trace_station",
    "trace_to_array",
]
