"""Event radial trace section figures."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.ticker import MaxNLocator

from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
from spatial_vtk.visualize.figure_context import title_with_subtitle
from spatial_vtk.visualize.figure_io import finish_figure
from spatial_vtk.visualize.record_sections import normalize_trace, trace_to_array
from spatial_vtk.visualize.selection import FigureSelection


def plot_event_radial_trace_section(
    records_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    trace_col: str = "trace",
    station_col: str = "station",
    distance_col: str = "distance_km",
    azimuth_col: str = "azimuth_deg",
    station_lon_col: str = "sta_lon",
    station_lat_col: str = "sta_lat",
    event_lon_col: str = "event_lon",
    event_lat_col: str = "event_lat",
    dt_col: str = "dt",
    selection: FigureSelection | None = None,
    normalize: bool = True,
    time_limit_s: float | None = 60.0,
    title: str = "Event Radial Trace Section",
    filter_label: str | None = None,
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot traces ordered by azimuth with a station/event map panel.

    Parameters
    ----------
    records_df
        Table with waveform, geometry, and azimuth columns.
    output_path
        Destination figure path.
    trace_col, station_col, distance_col, azimuth_col
        Trace and sorting/label columns.
    station_lon_col, station_lat_col, event_lon_col, event_lat_col
        Coordinate columns.
    dt_col
        Sample interval column.
    normalize
        Whether to normalize traces.
    time_limit_s
        Optional maximum trace time to draw in seconds. Defaults to 60 seconds.
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
    required = [trace_col, station_col, distance_col, azimuth_col, station_lon_col, station_lat_col, event_lon_col, event_lat_col]
    missing = [column for column in required if column not in work.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")
    df = work.sort_values(azimuth_col).reset_index(drop=True)
    fig = plt.figure(figsize=(13.5, 7.8), dpi=180)
    grid = fig.add_gridspec(1, 2, width_ratios=[1.38, 1.9], wspace=0.26)
    ax_map = fig.add_subplot(grid[0, 0])
    ax_section = fig.add_subplot(grid[0, 1])
    _map_panel(ax_map, df, station_lon_col, station_lat_col, event_lon_col, event_lat_col, azimuth_col, add_basemap, basemap_source, basemap_kwargs)
    _section_panel(ax_section, df, trace_col, station_col, distance_col, azimuth_col, dt_col, normalize, time_limit_s)
    fig.suptitle(title_with_subtitle(title, filter_label), y=0.985)
    fig.subplots_adjust(top=0.88, bottom=0.11, left=0.07, right=0.92)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _map_panel(ax: plt.Axes, df: pd.DataFrame, sta_lon: str, sta_lat: str, event_lon: str, event_lat: str, azimuth_col: str, add_basemap: bool, basemap_source: str, basemap_kwargs: dict[str, Any] | None) -> None:
    """Draw map panel colored by azimuth."""

    lon = pd.concat([df[sta_lon], df[event_lon]], ignore_index=True).astype(float)
    lat = pd.concat([df[sta_lat], df[event_lat]], ignore_index=True).astype(float)
    ax.set_xlim(float(lon.min()) - 0.05, float(lon.max()) + 0.05)
    ax.set_ylim(float(lat.min()) - 0.05, float(lat.max()) + 0.05)
    _set_geographic_aspect(ax)
    if add_basemap:
        add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **dict(basemap_kwargs or {}))
    for _, row in df.iterrows():
        values = pd.to_numeric(pd.Series([row.get(event_lon), row.get(event_lat), row.get(sta_lon), row.get(sta_lat)]), errors="coerce")
        if values.notna().all():
            ax.plot([float(values.iloc[0]), float(values.iloc[2])], [float(values.iloc[1]), float(values.iloc[3])], color="white", linewidth=0.45, alpha=0.45, zorder=2)
            ax.plot([float(values.iloc[0]), float(values.iloc[2])], [float(values.iloc[1]), float(values.iloc[3])], color="black", linewidth=0.2, alpha=0.35, zorder=3)
    scatter = ax.scatter(df[sta_lon], df[sta_lat], c=pd.to_numeric(df[azimuth_col], errors="coerce"), cmap="twilight", s=50, marker="^", edgecolors="black", linewidths=0.35, zorder=4)
    events = df.drop_duplicates(subset=[event_lon, event_lat])
    ax.scatter(events[event_lon], events[event_lat], marker="*", s=145, c="#ffd23f", edgecolors="black", linewidths=0.55, zorder=5)
    ax.set_title("Map")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
    ax.tick_params(axis="x", labelsize=8, pad=1)
    ax.grid(True, alpha=0.18)
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("bottom", size="5%", pad=0.55)
    colorbar = ax.figure.colorbar(scatter, cax=cax, orientation="horizontal")
    colorbar.set_label("Azimuth (deg)")


def _set_geographic_aspect(ax: plt.Axes) -> None:
    """Preserve lon/lat proportions on map panels."""

    lat_min, lat_max = ax.get_ylim()
    lat_mid = 0.5 * (float(lat_min) + float(lat_max))
    cos_lat = math.cos(math.radians(lat_mid))
    if math.isfinite(cos_lat) and abs(cos_lat) > 1.0e-6:
        ax.set_aspect(1.0 / cos_lat, adjustable="box")


def _section_panel(ax: plt.Axes, df: pd.DataFrame, trace_col: str, station_col: str, distance_col: str, azimuth_col: str, dt_col: str, normalize: bool, time_limit_s: float | None) -> None:
    """Draw traces sorted by azimuth."""

    y_values = pd.to_numeric(df[azimuth_col], errors="coerce").to_numpy(dtype=float)
    label_y = _spread_label_positions(y_values)
    for idx, (_, row) in enumerate(df.iterrows()):
        data, dt = trace_to_array(row[trace_col], default_dt=float(row.get(dt_col, 1.0)))
        if time_limit_s is not None and np.isfinite(float(time_limit_s)):
            max_npts = max(1, int(np.floor(float(time_limit_s) / max(float(dt), 1.0e-12))) + 1)
            data = data[:max_npts]
        if normalize:
            data = normalize_trace(data)
        time = np.arange(len(data), dtype=float) * dt
        y0 = y_values[idx] if np.isfinite(y_values[idx]) else float(idx)
        ax.plot(time, y0 + 8.0 * data, color="black", linewidth=0.7)
        label = _station_distance_label(row.get(station_col), row.get(distance_col))
        ax.annotate(
            label,
            xy=(1.0, y0),
            xycoords=ax.get_yaxis_transform(),
            xytext=(1.012, label_y[idx]),
            textcoords=ax.get_yaxis_transform(),
            ha="left",
            va="center",
            fontsize=5.8,
            arrowprops={"arrowstyle": "-", "color": "0.55", "linewidth": 0.35, "shrinkA": 0, "shrinkB": 0} if np.isfinite(y_values[idx]) and abs(label_y[idx] - y0) > 0.1 else None,
            clip_on=False,
        )
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Azimuth (deg)")
    ax.set_title("Radial section")
    ax.set_xlim(0.0, float(time_limit_s) if time_limit_s is not None and np.isfinite(float(time_limit_s)) else max(ax.get_xlim()[1], 1.0))
    finite_y = y_values[np.isfinite(y_values)]
    if len(finite_y):
        ax.set_ylim(max(-5.0, float(finite_y.min()) - 8.0), min(365.0, float(finite_y.max()) + 8.0))
    ax.grid(True, alpha=0.2)


def _station_distance_label(station: object, distance: object) -> str:
    """Return a station label with distance only when distance is finite."""

    station_text = str(station or "").strip()
    try:
        distance_value = float(distance)
    except Exception:
        distance_value = np.nan
    if np.isfinite(distance_value):
        return f"{station_text} ({distance_value:.1f} km)"
    return station_text


def _spread_label_positions(values: np.ndarray, *, min_gap: float = 7.0) -> np.ndarray:
    """Return de-overlapped label positions for azimuth-ordered traces."""

    y = np.asarray(values, dtype=float)
    fallback = np.arange(len(y), dtype=float) * float(min_gap)
    out = np.where(np.isfinite(y), y, fallback)
    order = np.argsort(out, kind="stable")
    sorted_values = out[order].copy()
    for idx in range(1, len(sorted_values)):
        if sorted_values[idx] < sorted_values[idx - 1] + min_gap:
            sorted_values[idx] = sorted_values[idx - 1] + min_gap
    if len(sorted_values):
        overflow = sorted_values[-1] - 360.0
        if overflow > 0.0:
            sorted_values -= overflow
        for idx in range(len(sorted_values) - 2, -1, -1):
            if sorted_values[idx] > sorted_values[idx + 1] - min_gap:
                sorted_values[idx] = sorted_values[idx + 1] - min_gap
    out[order] = sorted_values
    return out


__all__ = ["plot_event_radial_trace_section"]
