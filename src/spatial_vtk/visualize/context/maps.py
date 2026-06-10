"""Context map figure helpers.

Purpose
-------
This module draws overview maps for events, stations, networks, and optional
focal mechanisms from explicit metadata tables.

Usage examples
--------------
Plot event magnitudes:
  ``plot_event_magnitude_map(events, "event_magnitudes.png")``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colors
from matplotlib.cm import ScalarMappable
from mpl_toolkits.axes_grid1 import make_axes_locatable

from spatial_vtk.config.labels import display_label
from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
from spatial_vtk.visualize.figure_io import finish_figure


def plot_event_magnitude_map(
    events_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    magnitude_col: str = "magnitude",
    lon_col: str = "event_lon",
    lat_col: str = "event_lat",
    label_col: str | None = "event_id",
    title: str = "Event Magnitudes",
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot events sized and colored by magnitude.

    Parameters
    ----------
    events_df
        Event metadata table.
    output_path
        Destination figure path.
    magnitude_col, lon_col, lat_col
        Magnitude and coordinate columns.
    label_col
        Optional event label column.
    title
        Figure title.
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

    _require_columns(events_df, [magnitude_col, lon_col, lat_col])
    fig, ax = plt.subplots(figsize=(8.0, 6.8), dpi=180)
    _set_bounds(ax, events_df, lon_col, lat_col)
    if add_basemap:
        add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **dict(basemap_kwargs or {}))
    mag = pd.to_numeric(events_df[magnitude_col], errors="coerce")
    sizes = 28 + 20 * np.square(mag.fillna(mag.median() if mag.notna().any() else 1.0).clip(lower=0.0))
    scatter = ax.scatter(events_df[lon_col], events_df[lat_col], c=mag, s=sizes, marker="*", cmap="autumn_r", edgecolors="black", linewidths=0.45, zorder=4)
    if label_col and label_col in events_df.columns:
        for _, row in events_df.iterrows():
            ax.text(float(row[lon_col]) + 0.01, float(row[lat_col]) + 0.01, str(row[label_col]), fontsize=7.0, zorder=5)
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="4%", pad=0.08)
    cbar = fig.colorbar(scatter, cax=cax)
    cbar.set_label(display_label(magnitude_col))
    _finish_map(ax, title)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_station_event_network_map(
    stations_df: pd.DataFrame,
    events_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    station_lon_col: str = "lon",
    station_lat_col: str = "lat",
    event_lon_col: str = "event_lon",
    event_lat_col: str = "event_lat",
    network_col: str = "network",
    title: str = "Station Networks and Events",
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot station networks and event locations on one map.

    Parameters
    ----------
    stations_df, events_df
        Station and event metadata tables.
    output_path
        Destination figure path.
    station_lon_col, station_lat_col, event_lon_col, event_lat_col
        Coordinate columns.
    network_col
        Station network/category column.
    title
        Figure title.
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

    _require_columns(stations_df, [station_lon_col, station_lat_col])
    _require_columns(events_df, [event_lon_col, event_lat_col])
    fig, ax = plt.subplots(figsize=(8.4, 7.0), dpi=180)
    _set_combined_bounds(ax, stations_df, events_df, station_lon_col, station_lat_col, event_lon_col, event_lat_col)
    if add_basemap:
        add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **dict(basemap_kwargs or {}))
    if network_col in stations_df.columns:
        for network, subset in stations_df.groupby(network_col, dropna=False):
            ax.scatter(subset[station_lon_col], subset[station_lat_col], marker="^", s=35, edgecolors="black", linewidths=0.25, label=str(network), zorder=4)
    else:
        ax.scatter(stations_df[station_lon_col], stations_df[station_lat_col], marker="^", s=35, edgecolors="black", linewidths=0.25, label="Stations", zorder=4)
    ax.scatter(events_df[event_lon_col], events_df[event_lat_col], marker="*", s=105, c="#ffd23f", edgecolors="black", linewidths=0.45, label="Events", zorder=5)
    ax.legend(frameon=True, fontsize=8)
    _finish_map(ax, title)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_station_event_beachball_map(
    events_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    stations_df: pd.DataFrame | None = None,
    event_lon_col: str = "event_lon",
    event_lat_col: str = "event_lat",
    strike_col: str = "strike",
    dip_col: str = "dip",
    rake_col: str = "rake",
    magnitude_col: str = "magnitude",
    color_by_magnitude: bool = True,
    magnitude_cmap: str = "autumn_r",
    station_lon_col: str = "lon",
    station_lat_col: str = "lat",
    title: str = "Event Focal Mechanisms",
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    close: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot focal mechanism beachballs when ObsPy is available.

    Parameters
    ----------
    events_df
        Event metadata with coordinates and optional strike/dip/rake.
    output_path
        Destination figure path.
    stations_df
        Optional station metadata for context.
    event_lon_col, event_lat_col, strike_col, dip_col, rake_col
        Event coordinate and focal mechanism columns.
    magnitude_col
        Event magnitude column used to color beachball compressional quadrants.
    color_by_magnitude
        Whether to color compressional beachball quadrants by magnitude.
    magnitude_cmap
        Matplotlib colormap name for magnitude coloring.
    station_lon_col, station_lat_col
        Station coordinate columns.
    title
        Figure title.
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

    _require_columns(events_df, [event_lon_col, event_lat_col])
    fig, ax = plt.subplots(figsize=(8.4, 7.0), dpi=180)
    if stations_df is not None and {station_lon_col, station_lat_col} <= set(stations_df.columns):
        _set_combined_bounds(ax, stations_df, events_df, station_lon_col, station_lat_col, event_lon_col, event_lat_col)
    else:
        _set_bounds(ax, events_df, event_lon_col, event_lat_col)
    if add_basemap:
        add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **dict(basemap_kwargs or {}))
    if stations_df is not None and {station_lon_col, station_lat_col} <= set(stations_df.columns):
        ax.scatter(stations_df[station_lon_col], stations_df[station_lat_col], marker="^", s=24, c="#4c78a8", edgecolors="black", linewidths=0.2, alpha=1.0, label="Stations", zorder=4)
    magnitude_mappable = None
    if color_by_magnitude and magnitude_col in events_df.columns:
        magnitude_mappable = _magnitude_mappable(events_df[magnitude_col], magnitude_cmap)
    _draw_beachballs_or_markers(
        ax,
        events_df,
        event_lon_col,
        event_lat_col,
        strike_col,
        dip_col,
        rake_col,
        magnitude_col=magnitude_col,
        magnitude_mappable=magnitude_mappable,
    )
    if magnitude_mappable is not None:
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="4%", pad=0.08)
        cbar = fig.colorbar(magnitude_mappable, cax=cax)
        cbar.set_label(display_label(magnitude_col))
    ax.legend(frameon=True, fontsize=8, loc="best")
    _finish_map(ax, title)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig, close=close)


def _magnitude_mappable(magnitudes: pd.Series, cmap: str) -> ScalarMappable | None:
    """Create a scalar mappable for magnitude-colored beachballs.

    Parameters
    ----------
    magnitudes
        Event magnitude values.
    cmap
        Matplotlib colormap name.

    Returns
    -------
    matplotlib.cm.ScalarMappable | None
        Magnitude mappable, or ``None`` when no finite magnitude exists.
    """

    values = pd.to_numeric(magnitudes, errors="coerce").to_numpy(dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return None
    vmin = float(np.nanmin(values))
    vmax = float(np.nanmax(values))
    if math.isclose(vmin, vmax):
        pad = max(0.05, 0.02 * abs(vmin) if vmin else 0.05)
        vmin -= pad
        vmax += pad
    mappable = ScalarMappable(norm=colors.Normalize(vmin=vmin, vmax=vmax), cmap=plt.get_cmap(cmap))
    mappable.set_array(values)
    return mappable


def _event_magnitude_color(row: pd.Series, magnitude_col: str, magnitude_mappable: ScalarMappable | None, fallback: str = "#f7f7f7") -> str | tuple[float, float, float, float]:
    """Return the event's compressional-quadrant color.

    Parameters
    ----------
    row
        Event metadata row.
    magnitude_col
        Magnitude column name.
    magnitude_mappable
        Mappable returned by :func:`_magnitude_mappable`.
    fallback
        Color used when magnitude coloring is unavailable.

    Returns
    -------
    str | tuple
        Matplotlib-compatible color.
    """

    if magnitude_mappable is None or magnitude_col not in row:
        return fallback
    value = pd.to_numeric(pd.Series([row[magnitude_col]]), errors="coerce").iloc[0]
    if not np.isfinite(value):
        return fallback
    return magnitude_mappable.to_rgba(float(value))


def _draw_beachballs_or_markers(
    ax: plt.Axes,
    events_df: pd.DataFrame,
    lon_col: str,
    lat_col: str,
    strike_col: str,
    dip_col: str,
    rake_col: str,
    *,
    magnitude_col: str,
    magnitude_mappable: ScalarMappable | None,
) -> None:
    """Draw ObsPy beachballs, falling back to magnitude-colored star markers.

    Parameters
    ----------
    ax
        Target map axes.
    events_df
        Event metadata table.
    lon_col, lat_col
        Event coordinate columns.
    strike_col, dip_col, rake_col
        Focal mechanism columns.
    magnitude_col
        Magnitude column used for color.
    magnitude_mappable
        Optional magnitude-to-color mapper.

    Returns
    -------
    None
        The map axes are modified in place.
    """

    if {strike_col, dip_col, rake_col} <= set(events_df.columns):
        try:
            from obspy.imaging.beachball import beach
        except Exception:
            beach = None
        if beach is not None:
            width = max(0.03, 0.035 * max(abs(ax.get_xlim()[1] - ax.get_xlim()[0]), 1.0))
            drawn = False
            for _, row in events_df.iterrows():
                values = pd.to_numeric(pd.Series([row[strike_col], row[dip_col], row[rake_col]]), errors="coerce")
                if values.notna().all():
                    facecolor = _event_magnitude_color(row, magnitude_col, magnitude_mappable)
                    patch = beach(values.to_list(), xy=(float(row[lon_col]), float(row[lat_col])), width=width, facecolor=facecolor, bgcolor="white", edgecolor="black", linewidth=0.5, zorder=6)
                    ax.add_collection(patch)
                    drawn = True
            if drawn:
                ax.scatter([], [], marker="o", c="#f7f7f7", edgecolors="black", label="Mechanisms")
                return
    fallback_colors = [
        _event_magnitude_color(row, magnitude_col, magnitude_mappable, fallback="#ffd23f")
        for _, row in events_df.iterrows()
    ]
    ax.scatter(events_df[lon_col], events_df[lat_col], marker="*", s=115, c=fallback_colors, edgecolors="black", linewidths=0.45, label="Events", zorder=5)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    """Raise a clear error for missing columns."""

    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")


def _set_bounds(ax: plt.Axes, df: pd.DataFrame, lon_col: str, lat_col: str) -> None:
    """Set padded map bounds from one coordinate table."""

    lon = pd.to_numeric(df[lon_col], errors="coerce").to_numpy(dtype=float)
    lat = pd.to_numeric(df[lat_col], errors="coerce").to_numpy(dtype=float)
    finite = np.isfinite(lon) & np.isfinite(lat)
    if not np.any(finite):
        ax.set_xlim(-180.0, 180.0)
        ax.set_ylim(-90.0, 90.0)
        return
    west, east = float(np.nanmin(lon[finite])), float(np.nanmax(lon[finite]))
    south, north = float(np.nanmin(lat[finite])), float(np.nanmax(lat[finite]))
    pad_x = max(0.03, 0.08 * max(east - west, 0.01))
    pad_y = max(0.03, 0.08 * max(north - south, 0.01))
    ax.set_xlim(west - pad_x, east + pad_x)
    ax.set_ylim(south - pad_y, north + pad_y)
    _set_geographic_aspect(ax)


def _set_combined_bounds(ax: plt.Axes, stations_df: pd.DataFrame, events_df: pd.DataFrame, station_lon: str, station_lat: str, event_lon: str, event_lat: str) -> None:
    """Set padded map bounds from station and event tables."""

    work = pd.DataFrame(
        {
            "lon": pd.concat([pd.to_numeric(stations_df[station_lon], errors="coerce"), pd.to_numeric(events_df[event_lon], errors="coerce")], ignore_index=True),
            "lat": pd.concat([pd.to_numeric(stations_df[station_lat], errors="coerce"), pd.to_numeric(events_df[event_lat], errors="coerce")], ignore_index=True),
        }
    )
    _set_bounds(ax, work, "lon", "lat")


def _finish_map(ax: plt.Axes, title: str) -> None:
    """Apply common map labels and grid styling."""

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(title)
    ax.grid(True, alpha=0.18)


def _set_geographic_aspect(ax: plt.Axes) -> None:
    """Preserve lon/lat proportions on map axes."""

    lat_min, lat_max = ax.get_ylim()
    lat_mid = 0.5 * (float(lat_min) + float(lat_max))
    cos_lat = math.cos(math.radians(lat_mid))
    if math.isfinite(cos_lat) and abs(cos_lat) > 1.0e-6:
        ax.set_aspect(1.0 / cos_lat, adjustable="box")


__all__ = [
    "plot_event_magnitude_map",
    "plot_station_event_beachball_map",
    "plot_station_event_network_map",
]
