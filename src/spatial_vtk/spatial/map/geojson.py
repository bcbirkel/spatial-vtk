"""Map GeoJSON polygon regions with station and event context.

Purpose
-------
This module provides a first-class plotting helper for inspecting polygon
regions used by Spatial-VTK GeoJSON and corridor workflows.

Usage examples
--------------
Plot configured regions with station and event context:
  ``plot_geojson_polygons_map("regions.geojson", stations_df=stations, events_df=events)``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from spatial_vtk.spatial.calculate.geojson import load_geojson_polygons, select_geojson_polygons
from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
from spatial_vtk.visualize.figure_io import finish_figure


def plot_geojson_polygons_map(
    geojson_path: str | Path,
    output_path: str | Path | None = None,
    *,
    selector: object = "all",
    stations_df: pd.DataFrame | None = None,
    events_df: pd.DataFrame | None = None,
    title: str = "GeoJSON Regions",
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    label_polygons: bool = True,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot selected GeoJSON polygons with optional station/event points.

    Parameters
    ----------
    geojson_path
        Path to a GeoJSON file containing Polygon or MultiPolygon features.
    output_path
        Optional destination figure path.
    selector
        Polygon selector accepted by :func:`select_geojson_polygons`.
    stations_df, events_df
        Optional context tables with station and event coordinates.
    title
        Figure title.
    add_basemap
        Whether to draw a basemap underneath the polygon layers.
    basemap_source, basemap_kwargs
        Basemap provider settings forwarded to the shared basemap helper.
    label_polygons
        Whether to annotate polygon names at their representative points.
    showfig, savefig, outpath
        Standard Spatial-VTK figure display/save controls.

    Returns
    -------
    matplotlib.figure.Figure
        The created figure.
    """

    features = select_geojson_polygons(load_geojson_polygons(geojson_path), selector)
    if not features:
        raise ValueError("No GeoJSON polygons were selected.")

    fig, ax = plt.subplots(figsize=(8.0, 6.4), dpi=180, constrained_layout=True)
    colors = plt.get_cmap("tab10")(np.linspace(0.0, 1.0, max(len(features), 1)))
    for idx, feature in enumerate(features):
        _plot_feature(ax, feature.geometry, color=colors[idx % len(colors)])
        if label_polygons:
            point = feature.geometry.representative_point()
            ax.text(
                point.x,
                point.y,
                _display_name(feature.name),
                ha="center",
                va="center",
                fontsize=8.5,
                color="black",
                bbox={"boxstyle": "round,pad=0.22", "facecolor": "white", "edgecolor": "none", "alpha": 0.72},
                zorder=8,
            )

    if stations_df is not None and not stations_df.empty:
        lon_col, lat_col = _resolve_xy(
            stations_df,
            lon_candidates=["station_lon", "station_longitude", "sta_lon", "lon", "longitude"],
            lat_candidates=["station_lat", "station_latitude", "sta_lat", "lat", "latitude"],
            label="station",
        )
        ax.scatter(stations_df[lon_col], stations_df[lat_col], s=28, marker="^", facecolor="#2b83ba", edgecolor="white", linewidth=0.45, zorder=6, label="Stations")

    if events_df is not None and not events_df.empty:
        lon_col, lat_col = _resolve_xy(
            events_df,
            lon_candidates=["event_lon", "event_longitude", "source_lon", "source_longitude", "lon", "longitude"],
            lat_candidates=["event_lat", "event_latitude", "source_lat", "source_latitude", "lat", "latitude"],
            label="event",
        )
        ax.scatter(events_df[lon_col], events_df[lat_col], s=92, marker="*", facecolor="#ffd92f", edgecolor="black", linewidth=0.55, zorder=7, label="Events")

    _set_bounds(ax, features, stations_df=stations_df, events_df=events_df)
    if add_basemap:
        add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **dict(basemap_kwargs or {}))
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, alpha=0.18, zorder=1)
    if stations_df is not None or events_df is not None:
        ax.legend(loc="best", frameon=True)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _plot_feature(ax: plt.Axes, geometry: object, *, color: object) -> None:
    """Plot one Polygon or MultiPolygon geometry on ``ax``."""

    geoms = geometry.geoms if hasattr(geometry, "geoms") else [geometry]
    for geom in geoms:
        if not hasattr(geom, "exterior"):
            continue
        x, y = geom.exterior.xy
        ax.fill(x, y, facecolor=color, edgecolor="#202020", linewidth=1.1, alpha=0.28, zorder=3)
        ax.plot(x, y, color="#202020", linewidth=1.0, alpha=0.9, zorder=4)
        for interior in getattr(geom, "interiors", []):
            hx, hy = interior.xy
            ax.fill(hx, hy, facecolor="white", edgecolor="#202020", linewidth=0.7, alpha=0.6, zorder=4)


def _resolve_xy(df: pd.DataFrame, *, lon_candidates: list[str], lat_candidates: list[str], label: str) -> tuple[str, str]:
    """Resolve coordinate column names from common Spatial-VTK aliases."""

    lon = next((column for column in lon_candidates if column in df.columns), None)
    lat = next((column for column in lat_candidates if column in df.columns), None)
    if lon is None or lat is None:
        raise KeyError(f"Could not resolve {label} longitude/latitude columns.")
    return lon, lat


def _set_bounds(
    ax: plt.Axes,
    features: list[object],
    *,
    stations_df: pd.DataFrame | None,
    events_df: pd.DataFrame | None,
) -> None:
    """Set padded map bounds around polygons and optional points."""

    xs: list[float] = []
    ys: list[float] = []
    for feature in features:
        minx, miny, maxx, maxy = feature.geometry.bounds
        xs.extend([float(minx), float(maxx)])
        ys.extend([float(miny), float(maxy)])
    for frame, lon_candidates, lat_candidates, label in [
        (stations_df, ["station_lon", "station_longitude", "sta_lon", "lon", "longitude"], ["station_lat", "station_latitude", "sta_lat", "lat", "latitude"], "station"),
        (events_df, ["event_lon", "event_longitude", "source_lon", "source_longitude", "lon", "longitude"], ["event_lat", "event_latitude", "source_lat", "source_latitude", "lat", "latitude"], "event"),
    ]:
        if frame is None or frame.empty:
            continue
        lon_col, lat_col = _resolve_xy(frame, lon_candidates=lon_candidates, lat_candidates=lat_candidates, label=label)
        xs.extend(pd.to_numeric(frame[lon_col], errors="coerce").dropna().tolist())
        ys.extend(pd.to_numeric(frame[lat_col], errors="coerce").dropna().tolist())
    x_arr = np.asarray(xs, dtype=float)
    y_arr = np.asarray(ys, dtype=float)
    finite = np.isfinite(x_arr) & np.isfinite(y_arr)
    if not finite.any():
        return
    west, east = float(np.nanmin(x_arr[finite])), float(np.nanmax(x_arr[finite]))
    south, north = float(np.nanmin(y_arr[finite])), float(np.nanmax(y_arr[finite]))
    pad_x = max(0.03, 0.08 * max(east - west, 0.01))
    pad_y = max(0.03, 0.08 * max(north - south, 0.01))
    ax.set_xlim(west - pad_x, east + pad_x)
    ax.set_ylim(south - pad_y, north + pad_y)
    lat_mid = 0.5 * (south + north)
    cos_lat = math.cos(math.radians(lat_mid))
    if math.isfinite(cos_lat) and abs(cos_lat) > 1.0e-6:
        ax.set_aspect(1.0 / cos_lat, adjustable="box")


def _display_name(value: object) -> str:
    """Convert a region token into a short human-readable label."""

    text = str(value).replace("_", " ").strip()
    return text.title() if text.islower() else text


__all__ = ["plot_geojson_polygons_map"]
