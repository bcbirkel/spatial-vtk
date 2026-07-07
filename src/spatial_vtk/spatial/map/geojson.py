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
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

from spatial_vtk.spatial.calculate.geojson import load_geojson_polygons, select_geojson_polygons
from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
from spatial_vtk.visualize.figure_sidecars import finish_figure_with_sidecar, layered_figure_rows


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
    legend_polygons: bool = False,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
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
    legend_polygons
        Whether to add an outside-axes legend that maps polygon colors to
        GeoJSON region names.
    showfig, savefig, outpath
        Standard Spatial-VTK figure display/save controls.
    write_sidecar, sidecar_rows, sidecar_dir
        Optional CSV row-provenance sidecar controls. The sidecar records the
        selected polygon rows and any station/event context rows drawn.

    Returns
    -------
    matplotlib.figure.Figure
        The created figure.
    """

    features = select_geojson_polygons(load_geojson_polygons(geojson_path), selector)
    if not features:
        raise ValueError("No GeoJSON polygons were selected.")

    if legend_polygons:
        fig = plt.figure(figsize=(12.0, 6.4), dpi=180, constrained_layout=True)
        gs = fig.add_gridspec(1, 2, width_ratios=[4.9, 1.25])
        ax = fig.add_subplot(gs[0, 0])
        legend_ax = fig.add_subplot(gs[0, 1])
        legend_ax.axis("off")
    else:
        fig, ax = plt.subplots(figsize=(8.0, 6.4), dpi=180, constrained_layout=False)
        legend_ax = None
    colors = _region_colors(len(features))
    effective_label_polygons = bool(label_polygons) and len(features) <= 8
    legend_handles: list[Any] = []
    for idx, feature in enumerate(features):
        color = colors[idx % len(colors)]
        _plot_feature(ax, feature.geometry, color=color)
        if legend_polygons:
            legend_handles.append(
                Patch(
                    facecolor=color,
                    edgecolor="#202020",
                    alpha=0.42,
                    label=_display_name(feature.name),
                )
            )
        if effective_label_polygons:
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
        station_points = ax.scatter(stations_df[lon_col], stations_df[lat_col], s=28, marker="^", facecolor="#2b83ba", edgecolor="white", linewidth=0.45, zorder=6, label="Stations")
        legend_handles.append(station_points)

    if events_df is not None and not events_df.empty:
        lon_col, lat_col = _resolve_xy(
            events_df,
            lon_candidates=["event_lon", "event_longitude", "source_lon", "source_longitude", "lon", "longitude"],
            lat_candidates=["event_lat", "event_latitude", "source_lat", "source_latitude", "lat", "latitude"],
            label="event",
        )
        event_points = ax.scatter(events_df[lon_col], events_df[lat_col], s=92, marker="*", facecolor="#ffd92f", edgecolor="black", linewidth=0.55, zorder=7, label="Events")
        legend_handles.append(event_points)

    _set_bounds(ax, features, stations_df=stations_df, events_df=events_df)
    if add_basemap:
        add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **dict(basemap_kwargs or {}))
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, alpha=0.18, zorder=1)
    if legend_handles:
        if legend_polygons:
            assert legend_ax is not None
            legend_ax.legend(
                handles=legend_handles,
                title="GeoJSON Region",
                loc="center",
                frameon=True,
                fontsize=5.9,
                title_fontsize=6.7,
                borderpad=0.45,
                labelspacing=0.22,
                handlelength=1.25,
                handletextpad=0.45,
            )
        else:
            fig.tight_layout()
            ax.legend(loc="best", frameon=True)
    else:
        fig.tight_layout()
    sidecar_df = layered_figure_rows(
        (
            ("polygon", _feature_sidecar_rows(features)),
            ("station", stations_df),
            ("event", events_df),
        )
    )
    finish_savefig = savefig
    should_manual_save = legend_polygons and (outpath is not None or output_path is not None)
    if should_manual_save and (savefig is None or bool(savefig)):
        saved_path = Path(outpath if outpath is not None else output_path).expanduser()
        saved_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(saved_path, bbox_inches=None)
        setattr(fig, "spatial_vtk_saved_path", saved_path)
        setattr(fig, "exists", saved_path.exists)
        setattr(fig, "stat", saved_path.stat)
        finish_savefig = False

    return finish_figure_with_sidecar(
        fig,
        output_path,
        outpath=outpath,
        showfig=showfig,
        savefig=finish_savefig,
        bbox_inches=None if legend_polygons else "tight",
        sidecar_df=sidecar_df,
        write_sidecar=write_sidecar,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
    )


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


def _region_colors(count: int) -> np.ndarray:
    """Return visually distinct polygon colors for the selected regions."""

    if count <= 0:
        return plt.get_cmap("tab20")(np.asarray([0]))
    if count <= 20:
        return plt.get_cmap("tab20")(np.arange(count) % 20)
    return plt.get_cmap("hsv")(np.linspace(0.0, 1.0, count, endpoint=False))


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


def _feature_sidecar_rows(features: list[object]) -> pd.DataFrame:
    """Return CSV-friendly provenance rows for selected polygons."""

    rows: list[dict[str, object]] = []
    for index, feature in enumerate(features):
        minx, miny, maxx, maxy = feature.geometry.bounds
        row: dict[str, object] = {
            "polygon_index": index,
            "polygon_name": feature.name,
            "geometry_wkt": feature.geometry.wkt,
            "min_lon": float(minx),
            "min_lat": float(miny),
            "max_lon": float(maxx),
            "max_lat": float(maxy),
        }
        for key, value in feature.properties.items():
            row[f"property_{key}"] = value
        rows.append(row)
    return pd.DataFrame(rows)


__all__ = ["plot_geojson_polygons_map"]
