"""Selected waveform overlay figures."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator

from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
from spatial_vtk.visualize.figure_context import title_with_subtitle
from spatial_vtk.visualize.figure_io import finish_figure
from spatial_vtk.visualize.record_sections import normalize_trace, trace_to_array
from spatial_vtk.visualize.selection import FigureSelection


def plot_waveform_overlay_matrix(
    records_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    trace_col: str = "trace",
    group_col: str = "group",
    station_col: str = "station",
    distance_col: str = "distance_km",
    station_lon_col: str = "sta_lon",
    station_lat_col: str = "sta_lat",
    event_lon_col: str = "event_lon",
    event_lat_col: str = "event_lat",
    dt_col: str = "dt",
    selection: FigureSelection | None = None,
    max_groups: int = 6,
    max_traces_per_group: int = 8,
    sort_by_distance: bool = True,
    time_limit_s: float | None = 60.0,
    normalize: bool = True,
    title: str = "Observed Waveform Overlays",
    filter_label: str | None = None,
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot selected waveform groups with a shared map panel.

    Parameters
    ----------
    records_df
        Selected waveform rows. Selection should be done upstream by spatial or
        cluster helper functions.
    output_path
        Destination figure path.
    trace_col
        Waveform column.
    group_col
        Cluster, polygon, corridor, or other selected group column.
    station_col
        Station label column.
    distance_col
        Source-to-station distance column used for default trace sorting and
        station labels when available.
    station_lon_col, station_lat_col, event_lon_col, event_lat_col
        Coordinate columns.
    dt_col
        Sample interval column.
    max_groups
        Maximum groups to show.
    max_traces_per_group
        Maximum traces per group.
    sort_by_distance
        Whether to sort traces from nearest to farthest within each group,
        with the nearest trace plotted at the bottom.
    time_limit_s
        Optional x-axis limit in seconds. Set to ``None`` to show the full trace.
    normalize
        Whether to normalize traces.
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

    work = selection.apply(records_df) if selection is not None else records_df.copy()
    required = [trace_col, group_col, station_col, station_lon_col, station_lat_col, event_lon_col, event_lat_col]
    missing = [column for column in required if column not in work.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")
    groups = list(work[group_col].dropna().astype(str).unique())[: int(max_groups)]
    fig = plt.figure(figsize=(12.0, max(5.5, 2.0 * max(len(groups), 1))), dpi=180)
    grid = fig.add_gridspec(len(groups) or 1, 2, width_ratios=[1.0, 1.55], wspace=0.18, hspace=0.35)
    map_ax = fig.add_subplot(grid[:, 0])
    _plot_map(map_ax, work, group_col, station_lon_col, station_lat_col, event_lon_col, event_lat_col, add_basemap, basemap_source, basemap_kwargs)
    if not groups:
        ax = fig.add_subplot(grid[0, 1])
        ax.text(0.5, 0.5, "No selected waveform rows", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
    figure_event_label = _single_event_label(work)
    for row_index, group in enumerate(groups):
        ax = fig.add_subplot(grid[row_index, 1])
        subset = work.loc[work[group_col].astype(str) == group].copy()
        if sort_by_distance and distance_col in subset.columns:
            subset["_sort_distance"] = pd.to_numeric(subset[distance_col], errors="coerce")
            subset = subset.sort_values(["_sort_distance", station_col], na_position="last", kind="stable")
        subset = subset.head(int(max_traces_per_group))
        group_title = "Observed traces" if figure_event_label and len(groups) == 1 else _group_title(subset, group)
        _plot_group_traces(ax, subset, trace_col, station_col, distance_col, dt_col, normalize, title=group_title, time_limit_s=time_limit_s)
    full_title = title_with_subtitle(_figure_title(work, title), filter_label)
    fig.suptitle(full_title, y=0.985)
    top_margin = 0.8 if full_title.count("\n") >= 2 else 0.88 if "\n" in full_title else 0.93
    fig.subplots_adjust(top=top_margin)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _plot_map(ax: plt.Axes, df: pd.DataFrame, group_col: str, sta_lon: str, sta_lat: str, event_lon: str, event_lat: str, add_basemap: bool, basemap_source: str, basemap_kwargs: dict[str, Any] | None) -> None:
    """Draw shared selected-row map."""

    lon = pd.concat([pd.to_numeric(df[sta_lon], errors="coerce"), pd.to_numeric(df[event_lon], errors="coerce")], ignore_index=True)
    lat = pd.concat([pd.to_numeric(df[sta_lat], errors="coerce"), pd.to_numeric(df[event_lat], errors="coerce")], ignore_index=True)
    ax.set_xlim(float(lon.min()) - 0.05, float(lon.max()) + 0.05)
    ax.set_ylim(float(lat.min()) - 0.05, float(lat.max()) + 0.05)
    _set_geographic_aspect(ax)
    if add_basemap:
        add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **dict(basemap_kwargs or {}))
    groups = list(df.groupby(group_col, dropna=False))
    for index, (group, subset) in enumerate(groups):
        label = "Stations" if len(groups) == 1 else f"Stations: {_group_title(subset, group)}"
        ax.scatter(subset[sta_lon], subset[sta_lat], marker="^", s=32, edgecolors="black", linewidths=0.25, label=label, zorder=4)
    events = df.drop_duplicates(subset=[event_lon, event_lat])
    event_label = "Event" if len(events) == 1 else "Events"
    ax.scatter(events[event_lon], events[event_lat], marker="*", s=100, c="#ffd23f", edgecolors="black", linewidths=0.45, label=event_label, zorder=5)
    ax.set_title("Stations and event")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
    ax.tick_params(axis="x", labelsize=8, pad=1)
    ax.grid(True, alpha=0.18)
    ax.legend(frameon=True, fontsize=7)


def _set_geographic_aspect(ax: plt.Axes) -> None:
    """Preserve lon/lat proportions on map panels."""

    lat_min, lat_max = ax.get_ylim()
    lat_mid = 0.5 * (float(lat_min) + float(lat_max))
    cos_lat = math.cos(math.radians(lat_mid))
    if math.isfinite(cos_lat) and abs(cos_lat) > 1.0e-6:
        ax.set_aspect(1.0 / cos_lat, adjustable="box")


def _plot_group_traces(ax: plt.Axes, subset: pd.DataFrame, trace_col: str, station_col: str, distance_col: str, dt_col: str, normalize: bool, *, title: str, time_limit_s: float | None) -> None:
    """Draw traces for one selected group."""

    row_count = len(subset)
    for idx, (_, row) in enumerate(subset.iterrows()):
        y_position = idx
        data, dt = trace_to_array(row[trace_col], default_dt=float(row.get(dt_col, 1.0)))
        if normalize:
            data = normalize_trace(data)
        time = np.arange(len(data), dtype=float) * dt
        ax.plot(time, y_position + 0.42 * data, color="black", linewidth=0.7)
        ax.text(1.01, y_position, _station_distance_label(row.get(station_col, ""), row.get(distance_col, np.nan)), transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=7, clip_on=False)
    ax.set_title(title, loc="left", fontsize=9)
    ax.set_yticks([])
    ax.set_xlabel("Time (s)")
    if time_limit_s is not None:
        ax.set_xlim(0.0, float(time_limit_s))
    ax.grid(True, axis="x", alpha=0.18)


def _figure_title(df: pd.DataFrame, base_title: str) -> str:
    """Return a figure title with a readable single-event name when available."""

    event_label = _single_event_label(df)
    if event_label and event_label not in str(base_title):
        return f"{base_title}\n{event_label}"
    return str(base_title)


def _group_title(subset: pd.DataFrame, group: object) -> str:
    """Return a readable title for one group/panel."""

    label = _single_event_label(subset)
    return label or str(group)


def _single_event_label(df: pd.DataFrame) -> str:
    """Return one human-readable event label when a dataframe has one event."""

    event_col = _event_identity_column(df)
    if event_col is None or df.empty:
        return ""
    unique_events = df[event_col].dropna().astype(str).str.strip().unique()
    if len(unique_events) != 1:
        return ""
    for label_col in ("event_name", "event_place"):
        if label_col not in df.columns:
            continue
        labels = [str(value).strip() for value in df[label_col].dropna().unique() if str(value).strip()]
        if labels:
            return labels[0]
    return unique_events[0]


def _station_distance_label(station: object, distance: object) -> str:
    """Return station label with distance when distance is finite."""

    station_text = str(station or "").strip()
    try:
        distance_value = float(distance)
    except Exception:
        distance_value = np.nan
    if np.isfinite(distance_value):
        return f"{station_text} ({distance_value:.1f} km)"
    return station_text


def _first_existing_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    """Return the first existing column from candidates."""

    for column in candidates:
        if column in df.columns:
            return column
    return None


def _event_identity_column(df: pd.DataFrame) -> str | None:
    """Return an event identifier column, preferring event ids over titles."""

    if "event_id" in df.columns:
        return "event_id"
    for candidate in ("event_title", "event_name", "event_place"):
        if candidate in df.columns:
            return candidate
    return None


__all__ = ["plot_waveform_overlay_matrix"]
