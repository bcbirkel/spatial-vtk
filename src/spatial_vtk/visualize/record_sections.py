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
from spatial_vtk.visualize.figure_io import finish_figure
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
        Numeric array or trace object with ``data`` and optional ``stats``.
    default_dt
        Sample interval used when metadata are unavailable.

    Returns
    -------
    tuple
        ``(samples, dt_seconds)``.
    """

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
    components: Iterable[str] | None = None,
    selection: FigureSelection | None = None,
    max_records: int | None = 80,
    normalize: bool = True,
    scale: float = 1.0,
    title: str = "Record Section",
    filter_label: str | None = None,
    default_dt: float = 1.0,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
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

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    input_records = selection.apply(records) if isinstance(records, pd.DataFrame) and selection is not None else records
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
        return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)

    if components is None:
        component_values = sorted(value for value in rows["component"].dropna().astype(str).unique().tolist() if value)
        components = component_values or ["Trace"]
    components = [str(component).upper() for component in components]
    fig, axes = plt.subplots(1, len(components), figsize=(max(6.0, 4.8 * len(components)), 6.6), dpi=180, sharey=True)
    axes = np.atleast_1d(axes)
    for ax, component in zip(axes, components):
        subset = rows if component == "TRACE" else rows.loc[rows["component"].astype(str).str.upper().isin([component, ""])]
        subset = subset.sort_values(["distance_km", "station"], na_position="last")
        if max_records is not None:
            subset = subset.head(int(max_records))
        if subset.empty:
            ax.text(0.5, 0.5, f"No {component} traces", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(f"{component} component")
            continue
        y_positions = _section_y_positions(subset, "distance_km")
        half_height = _trace_half_height(y_positions, scale)
        max_time = 0.0
        for row_idx, (_, row) in enumerate(subset.iterrows()):
            data = np.asarray(row["trace"], dtype=float)
            if normalize:
                data = normalize_trace(data)
            time = np.arange(len(data), dtype=float) * float(row["dt"])
            max_time = max(max_time, float(time[-1]) if len(time) else 0.0)
            y0 = float(y_positions[row_idx])
            ax.plot(time, y0 + data * half_height, color="black", linewidth=0.72)
        ax.set_title(f"{component} component")
        ax.set_xlabel("Time (s)")
        ax.set_xlim(0.0, max(max_time, 1.0))
        ax.grid(True, alpha=0.18)
    if np.isfinite(pd.to_numeric(rows["distance_km"], errors="coerce")).all():
        axes[0].set_ylabel("Distance (km)")
    else:
        axes[0].set_ylabel("Record")
    fig.suptitle(title_with_subtitle(title, filter_label), y=0.99)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


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
    components: Iterable[str] | None = None,
    selection: FigureSelection | None = None,
    max_records: int | None = 80,
    normalize: bool = True,
    scale: float = 1.0,
    title: str = "Observed and Synthetic Record Section",
    filter_label: str | None = None,
    default_dt: float = 1.0,
    time_limit_s: float | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
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
    components
        Optional ordered component subset.
    max_records
        Maximum rows to draw per component.
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
        Optional maximum seconds to display from each trace start.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    required = {observed_col, synthetic_col, station_col}
    missing = required - set(records_df.columns)
    if missing:
        raise KeyError(f"records_df is missing required columns: {sorted(missing)}")
    rows = selection.apply(records_df) if selection is not None else records_df.copy()
    if components is None:
        if component_col and component_col in rows.columns:
            components = sorted(value for value in rows[component_col].dropna().astype(str).unique().tolist() if value) or ["Trace"]
        else:
            components = ["Trace"]
    components = [str(component).upper() for component in components]
    has_time_offsets = observed_time_offset_col in rows.columns or synthetic_time_offset_col in rows.columns
    fig, axes = plt.subplots(1, len(components), figsize=(max(6.0, 4.8 * len(components)), 6.6), dpi=180, sharey=True)
    axes = np.atleast_1d(axes)
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
        if subset.empty:
            ax.text(0.5, 0.5, f"No {component} pairs", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(f"{component} component")
            continue
        y_positions = _section_y_positions(subset, distance_col)
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
        ax.set_title(f"{component} component")
        ax.set_xlabel("Seconds since event origin" if has_time_offsets else "Seconds since trace start")
        ax.set_xlim(0.0, max(max_time, 1.0))
        ax.grid(True, alpha=0.18)
    axes[0].set_ylabel("Distance (km)" if distance_col in rows.columns else "Record")
    axes[0].legend(loc="upper right")
    fig.suptitle(title_with_subtitle(title, filter_label), y=0.99)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


__all__ = [
    "build_record_section_rows",
    "normalize_trace",
    "plot_observed_synthetic_record_section",
    "plot_record_section",
    "row_sample_interval",
    "row_time_offset",
    "save_record_section_figure",
    "trace_component",
    "trace_station",
    "trace_to_array",
]
