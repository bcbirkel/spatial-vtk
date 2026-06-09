"""Station-event waveform map figures.

Purpose
-------
This module draws a map of one event and its stations beside waveform panels.
It accepts explicit records and does not discover private waveform roots.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
from spatial_vtk.visualize.figure_context import title_with_subtitle
from spatial_vtk.visualize.figure_io import finish_figure
from spatial_vtk.visualize.record_sections import normalize_trace, trace_to_array
from spatial_vtk.visualize.selection import FigureSelection


def plot_station_event_waveform_map(
    records_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    waveform_col: str = "trace",
    station_col: str = "station",
    station_lon_col: str = "sta_lon",
    station_lat_col: str = "sta_lat",
    event_lon_col: str = "event_lon",
    event_lat_col: str = "event_lat",
    component_col: str | None = "component",
    selection: FigureSelection | None = None,
    dt_col: str = "dt",
    time_offset_col: str | None = "auto",
    time_limits_s: tuple[float, float] | None = None,
    time_limit_s: float | None = None,
    distance_col: str = "distance_km",
    sort_by_distance: bool = True,
    max_traces: int = 12,
    normalize: bool = True,
    title: str = "Station-Event Waveform Map",
    filter_label: str | None = None,
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot station/event geometry beside waveform traces.

    Parameters
    ----------
    records_df
        Table with station/event coordinates and waveform arrays.
    output_path
        Destination figure path.
    waveform_col
        Waveform array or trace-like column.
    station_col
        Station label column.
    station_lon_col, station_lat_col, event_lon_col, event_lat_col
        Coordinate columns.
    component_col
        Optional component label column.
    dt_col
        Sample interval column.
    time_offset_col
        Optional column with trace start time in seconds relative to event
        origin. The default ``"auto"`` uses ``observed_time_offset_s`` for
        observed waveforms and ``synthetic_time_offset_s`` for synthetic
        waveforms when those columns are available, so trace plots are aligned
        with ``t=0`` at the event origin without exposing timing metadata in
        tutorial code.
    time_limits_s, time_limit_s
        Optional x-axis limits in seconds. ``time_limit_s`` is shorthand for
        ``(0, time_limit_s)``.
    distance_col, sort_by_distance
        Distance column and whether traces should be sorted from nearest at
        the bottom to farthest at the top.
    max_traces
        Maximum traces to show.
    normalize
        Whether to normalize each waveform.
    title
        Figure title.
    filter_label
        Optional second title line describing any bandpass or lowpass filter.
    add_basemap
        Whether to draw a basemap.
    basemap_source
        Contextily provider selector.
    basemap_kwargs
        Extra basemap keyword arguments.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    work = selection.apply(records_df, component_col=component_col or "component") if selection is not None else records_df.copy()
    _require_columns(work, [waveform_col, station_col, station_lon_col, station_lat_col, event_lon_col, event_lat_col])
    df = work.copy()
    if sort_by_distance and distance_col in df.columns:
        df[distance_col] = pd.to_numeric(df[distance_col], errors="coerce")
        df = df.sort_values([distance_col, station_col], kind="stable")
    df = df.head(int(max_traces)).copy()
    fig = plt.figure(figsize=(12.0, max(6.0, 0.42 * len(df) + 3.2)), dpi=180)
    grid = fig.add_gridspec(1, 2, width_ratios=[1.05, 1.35], wspace=0.18)
    map_ax = fig.add_subplot(grid[0, 0])
    trace_ax = fig.add_subplot(grid[0, 1])
    _plot_map_panel(map_ax, df, station_lon_col, station_lat_col, event_lon_col, event_lat_col, add_basemap, basemap_source, basemap_kwargs)
    x_limits = (0.0, float(time_limit_s)) if time_limit_s is not None else time_limits_s
    resolved_time_offset_col = _resolve_time_offset_col(df, waveform_col=waveform_col, time_offset_col=time_offset_col)
    _plot_trace_stack(trace_ax, df, waveform_col, station_col, component_col, dt_col, normalize, time_offset_col=resolved_time_offset_col, time_limits_s=x_limits, distance_col=distance_col)
    fig.suptitle(title_with_subtitle(title, filter_label), y=0.995)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _plot_map_panel(ax: plt.Axes, df: pd.DataFrame, sta_lon: str, sta_lat: str, event_lon: str, event_lat: str, add_basemap: bool, basemap_source: str, basemap_kwargs: dict[str, Any] | None) -> None:
    """Draw the station/event map panel."""

    _set_combined_bounds(ax, df, sta_lon, sta_lat, event_lon, event_lat)
    if add_basemap:
        add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **dict(basemap_kwargs or {}))
    ax.scatter(df[sta_lon], df[sta_lat], marker="^", s=34, c="#4c78a8", edgecolors="black", linewidths=0.25, label="Stations", zorder=4)
    events = df.drop_duplicates(subset=[event_lon, event_lat])
    ax.scatter(events[event_lon], events[event_lat], marker="*", s=115, c="#ffd23f", edgecolors="black", linewidths=0.45, label="Event", zorder=5)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Map")
    ax.grid(True, alpha=0.18)
    ax.legend(frameon=True, fontsize=8)


def _plot_trace_stack(
    ax: plt.Axes,
    df: pd.DataFrame,
    waveform_col: str,
    station_col: str,
    component_col: str | None,
    dt_col: str,
    normalize: bool,
    *,
    time_offset_col: str | None,
    time_limits_s: tuple[float, float] | None,
    distance_col: str,
) -> None:
    """Draw stacked waveform traces."""

    for row_index, (_, row) in enumerate(df.iterrows()):
        data, dt = trace_to_array(row[waveform_col], default_dt=float(row.get(dt_col, 1.0)))
        if normalize:
            data = normalize_trace(data)
        offset = _numeric_or_default(row.get(time_offset_col), 0.0) if time_offset_col else 0.0
        time = offset + np.arange(len(data), dtype=float) * dt
        if time_limits_s is not None:
            tmin, tmax = float(time_limits_s[0]), float(time_limits_s[1])
            mask = (time >= tmin) & (time <= tmax)
            if np.any(mask):
                time = time[mask]
                data = data[mask]
        y0 = float(row_index)
        ax.plot(time, y0 + 0.42 * data, color="black", linewidth=0.75)
        label = str(row.get(station_col, ""))
        if distance_col in row.index and np.isfinite(_numeric_or_default(row.get(distance_col), np.nan)):
            label = f"{label} ({_numeric_or_default(row.get(distance_col), np.nan):.1f} km)"
        if component_col and component_col in df.columns:
            label = f"{label} {row.get(component_col, '')}".strip()
        ax.text(1.01, y0, label, transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=7, clip_on=False)
    ax.set_yticks([])
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Trace")
    ax.set_title("Waveforms")
    ax.grid(True, axis="x", alpha=0.2)
    if time_limits_s is not None:
        ax.set_xlim(float(time_limits_s[0]), float(time_limits_s[1]))


def _numeric_or_default(value: object, default: float) -> float:
    """Return a finite float or a fallback value."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(default)
    return number if math.isfinite(number) else float(default)


def _resolve_time_offset_col(df: pd.DataFrame, *, waveform_col: str, time_offset_col: str | None) -> str | None:
    """Choose the event-origin alignment column for a waveform plot.

    Inputs are the records table, requested waveform column, and explicit or
    automatic time-offset setting. The output is a column name to use for
    plotting or ``None`` when no event-origin offset should be applied.
    """

    if time_offset_col != "auto":
        return time_offset_col if time_offset_col in df.columns else None
    candidates: list[str] = []
    waveform_key = str(waveform_col).lower()
    if "synthetic" in waveform_key or waveform_key in {"syn", "synthetic_trace"}:
        candidates.extend(["synthetic_time_offset_s", "time_offset_s"])
    elif "observed" in waveform_key or waveform_key in {"obs", "observed_trace"}:
        candidates.extend(["observed_time_offset_s", "time_offset_s"])
    else:
        candidates.extend(["time_offset_s", "observed_time_offset_s", "synthetic_time_offset_s"])
    return next((column for column in candidates if column in df.columns), None)


def _set_combined_bounds(ax: plt.Axes, df: pd.DataFrame, sta_lon: str, sta_lat: str, event_lon: str, event_lat: str) -> None:
    """Set map bounds from station and event coordinates."""

    lon = pd.concat([pd.to_numeric(df[sta_lon], errors="coerce"), pd.to_numeric(df[event_lon], errors="coerce")], ignore_index=True).to_numpy(dtype=float)
    lat = pd.concat([pd.to_numeric(df[sta_lat], errors="coerce"), pd.to_numeric(df[event_lat], errors="coerce")], ignore_index=True).to_numpy(dtype=float)
    finite = np.isfinite(lon) & np.isfinite(lat)
    if not np.any(finite):
        ax.set_xlim(-180, 180)
        ax.set_ylim(-90, 90)
        return
    west, east = float(np.nanmin(lon[finite])), float(np.nanmax(lon[finite]))
    south, north = float(np.nanmin(lat[finite])), float(np.nanmax(lat[finite]))
    ax.set_xlim(west - max(0.03, 0.08 * max(east - west, 0.01)), east + max(0.03, 0.08 * max(east - west, 0.01)))
    ax.set_ylim(south - max(0.03, 0.08 * max(north - south, 0.01)), north + max(0.03, 0.08 * max(north - south, 0.01)))
    _set_geographic_aspect(ax)


def _set_geographic_aspect(ax: plt.Axes) -> None:
    """Preserve lon/lat proportions on map panels."""

    lat_min, lat_max = ax.get_ylim()
    lat_mid = 0.5 * (float(lat_min) + float(lat_max))
    cos_lat = math.cos(math.radians(lat_mid))
    if math.isfinite(cos_lat) and abs(cos_lat) > 1.0e-6:
        ax.set_aspect(1.0 / cos_lat, adjustable="box")


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    """Raise a clear error for missing columns."""

    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")


__all__ = ["plot_station_event_waveform_map"]
