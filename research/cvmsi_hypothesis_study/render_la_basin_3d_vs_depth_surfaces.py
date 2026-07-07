#!/usr/bin/env python3
"""Render 3D LA Basin z(Vs) surfaces from a sampled velocity model.

The figures are intended as geometric diagnostics: they show the depth to
Vs=1.0 km/s and Vs=2.5 km/s beneath the LA Basin GeoJSON region, with the basin
outline, a rectangular cutout box, a faint surface basemap when tile access is
available, and labeled city/neighborhood marker lines.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import Normalize
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter
from mpl_toolkits.mplot3d import proj3d
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely import contains_xy
from shapely.geometry import box
from shapely.ops import transform as shapely_transform

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.cvmsi_hypothesis_study.cvmsi_hypothesis_study import (  # noqa: E402
    CVM_UTM,
    DEFAULT_BASEMAP_SOURCE,
    DEFAULT_BASEMAP_ZOOM,
    DEFAULT_MODEL_H5,
    DEFAULT_REGIONS,
    WEB_MERCATOR,
    WGS84,
    ModelSampler,
    add_required_basemap,
    iter_polygons,
    load_regions,
)


DEPTHS_KM = np.linspace(0.0, 15.0, 151)
THRESHOLDS = {
    "z1": (1.0, "z(Vs=1.0 km/s)"),
    "z2p5": (2.5, "z(Vs=2.5 km/s)"),
}

CITY_MARKERS = {
    "Downtown LA": (-118.2437, 34.0522),
    "Long Beach": (-118.1937, 33.7701),
    "Santa Monica": (-118.4912, 34.0195),
    "Whittier": (-118.0328, 33.9792),
    "Pasadena": (-118.1445, 34.1478),
    "Inglewood": (-118.3531, 33.9617),
    "Anaheim": (-117.9143, 33.8366),
}

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
    "blue": "#5477C4",
    "gold": "#B8A037",
    "orange": "#CC6F47",
}


@dataclass(frozen=True)
class BasinGeometry:
    name: str
    lonlat: object
    utm: object
    web_mercator: object
    bbox_utm: object
    bbox_web_mercator: object


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regions", type=Path, default=DEFAULT_REGIONS)
    parser.add_argument("--model-h5", type=Path, default=DEFAULT_MODEL_H5)
    parser.add_argument("--model-label", default="CVM-SI")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/review/cvmsi_hypothesis_study"),
        help="Output root, relative to the repository if not absolute.",
    )
    parser.add_argument("--grid-spacing-km", type=float, default=2.0)
    parser.add_argument("--bbox-pad-km", type=float, default=7.5)
    parser.add_argument("--model-node-stride", type=int, default=2)
    parser.add_argument("--sample-chunk-size", type=int, default=450)
    parser.add_argument("--basemap-source", default=DEFAULT_BASEMAP_SOURCE)
    parser.add_argument("--basemap-zoom", type=int, default=DEFAULT_BASEMAP_ZOOM)
    parser.add_argument("--vertical-exaggeration", type=float, default=6.0)
    parser.add_argument("--z1-vertical-exaggeration", type=float, default=18.0)
    parser.add_argument("--surface-alpha", type=float, default=0.90)
    return parser.parse_args(argv)


def set_theme() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": TOKENS["surface"],
            "axes.facecolor": TOKENS["panel"],
            "axes.edgecolor": TOKENS["axis"],
            "axes.labelcolor": TOKENS["ink"],
            "xtick.color": TOKENS["muted"],
            "ytick.color": TOKENS["muted"],
            "text.color": TOKENS["ink"],
            "font.family": ["sans-serif"],
            "axes.titlesize": 15,
            "axes.labelsize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 10,
        }
    )


def resolve_output_root(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def find_la_basin(regions_path: Path) -> tuple[str, object]:
    regions = load_regions(regions_path)
    ranked: list[tuple[int, str, object]] = []
    for region in regions:
        label = f"{region.name} {region.short_name}".lower()
        score = 0
        if "la basin" in label or "los angeles basin" in label:
            score += 100
        if "basin" in label:
            score += 20
        if "la" in label or "los angeles" in label:
            score += 10
        if region.region_type.lower() == "basin":
            score += 5
        if score:
            ranked.append((score, region.name, region.geometry_lonlat))
    if not ranked:
        raise ValueError(f"Could not identify LA Basin in {regions_path}")
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1], ranked[0][2]


def build_basin_geometry(regions_path: Path, pad_km: float) -> BasinGeometry:
    name, basin_lonlat = find_la_basin(regions_path)
    to_utm = Transformer.from_crs(WGS84, CVM_UTM, always_xy=True)
    to_wm = Transformer.from_crs(WGS84, WEB_MERCATOR, always_xy=True)
    basin_utm = shapely_transform(to_utm.transform, basin_lonlat)
    basin_wm = shapely_transform(to_wm.transform, basin_lonlat)
    minx, miny, maxx, maxy = basin_utm.bounds
    pad_m = pad_km * 1000.0
    bbox_utm = box(minx - pad_m, miny - pad_m, maxx + pad_m, maxy + pad_m)
    to_lonlat = Transformer.from_crs(CVM_UTM, WGS84, always_xy=True)
    bbox_lonlat = shapely_transform(to_lonlat.transform, bbox_utm)
    bbox_wm = shapely_transform(to_wm.transform, bbox_lonlat)
    return BasinGeometry(
        name=name,
        lonlat=basin_lonlat,
        utm=basin_utm,
        web_mercator=basin_wm,
        bbox_utm=bbox_utm,
        bbox_web_mercator=bbox_wm,
    )


def interpolate_depth_to_threshold(vs_km_s: np.ndarray, threshold: float) -> float:
    valid = np.isfinite(vs_km_s)
    if not valid.any():
        return np.nan
    depths = DEPTHS_KM[valid]
    values = vs_km_s[valid]
    above = values >= threshold
    if not above.any():
        return np.nan
    first = int(np.argmax(above))
    if first == 0:
        return float(depths[0])
    x0 = float(values[first - 1])
    x1 = float(values[first])
    z0 = float(depths[first - 1])
    z1 = float(depths[first])
    if x1 == x0:
        return z1
    fraction = np.clip((threshold - x0) / (x1 - x0), 0.0, 1.0)
    return float(z0 + fraction * (z1 - z0))


def build_grid(geom: BasinGeometry, spacing_km: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    minx, miny, maxx, maxy = geom.bbox_utm.bounds
    spacing_m = spacing_km * 1000.0
    xs = np.arange(minx, maxx + 0.5 * spacing_m, spacing_m)
    ys = np.arange(miny, maxy + 0.5 * spacing_m, spacing_m)
    x_grid, y_grid = np.meshgrid(xs, ys)
    basin_mask = contains_xy(geom.utm, x_grid, y_grid)
    return x_grid, y_grid, basin_mask


def sample_depth_surfaces(
    sampler: ModelSampler,
    x_grid: np.ndarray,
    y_grid: np.ndarray,
    mask: np.ndarray,
    chunk_size: int,
) -> dict[str, np.ndarray]:
    points = np.column_stack([x_grid[mask], y_grid[mask]])
    surfaces = {key: np.full(x_grid.shape, np.nan, dtype=float) for key in THRESHOLDS}
    if len(points) == 0:
        return surfaces

    results = {key: [] for key in THRESHOLDS}
    for start in range(0, len(points), chunk_size):
        chunk = points[start : start + chunk_size]
        xyz = np.empty((len(chunk) * len(DEPTHS_KM), 3), dtype=float)
        xyz[:, 0] = np.repeat(chunk[:, 0], len(DEPTHS_KM))
        xyz[:, 1] = np.repeat(chunk[:, 1], len(DEPTHS_KM))
        xyz[:, 2] = np.tile(-1000.0 * DEPTHS_KM, len(chunk))
        sampled = sampler.sample_xyz(xyz)
        vs = sampled["vs"].to_numpy(dtype=float).reshape(len(chunk), len(DEPTHS_KM)) / 1000.0
        for key, (threshold, _) in THRESHOLDS.items():
            results[key].extend(interpolate_depth_to_threshold(profile, threshold) for profile in vs)

    for key in THRESHOLDS:
        surface = surfaces[key]
        surface[mask] = np.asarray(results[key], dtype=float)
    return surfaces


def transform_grid_to_web_mercator(x_grid: np.ndarray, y_grid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    to_lonlat = Transformer.from_crs(CVM_UTM, WGS84, always_xy=True)
    to_wm = Transformer.from_crs(WGS84, WEB_MERCATOR, always_xy=True)
    lon, lat = to_lonlat.transform(x_grid, y_grid)
    wm_x, wm_y = to_wm.transform(lon, lat)
    return np.asarray(wm_x), np.asarray(wm_y)


def relative_xy(wm_x: np.ndarray, wm_y: np.ndarray, center: tuple[float, float]) -> tuple[np.ndarray, np.ndarray]:
    return (np.asarray(wm_x) - center[0]) / 1000.0, (np.asarray(wm_y) - center[1]) / 1000.0


def polygon_to_relative_rings(geom: object, center: tuple[float, float]) -> list[tuple[np.ndarray, np.ndarray]]:
    rings: list[tuple[np.ndarray, np.ndarray]] = []
    for polygon in iter_polygons(geom):
        x, y = polygon.exterior.xy
        rings.append(relative_xy(np.asarray(x), np.asarray(y), center))
    return rings


def load_basemap_texture(
    bbox_wm: object,
    source: str,
    zoom: int,
) -> tuple[np.ndarray, tuple[float, float, float, float]] | None:
    try:
        import contextily as ctx
        import xyzservices.providers as xyz

        west, south, east, north = bbox_wm.bounds
        resolved_source = source
        if source == "CartoDB.Positron":
            resolved_source = xyz.CartoDB.Positron
        elif source == "OpenStreetMap.Mapnik":
            resolved_source = xyz.OpenStreetMap.Mapnik
        elif source == "Esri.WorldImagery":
            resolved_source = xyz.Esri.WorldImagery
        elif source == "Esri.WorldTopoMap":
            resolved_source = xyz.Esri.WorldTopoMap
        image, extent = ctx.bounds2img(
            west,
            south,
            east,
            north,
            zoom=zoom,
            source=resolved_source,
            ll=False,
            max_retries=2,
        )
        image = np.asarray(image)
        if image.ndim != 3 or image.shape[0] < 2 or image.shape[1] < 2:
            return None
        return image, tuple(float(v) for v in extent)
    except Exception:
        return None


def add_basemap_plane(
    ax,
    texture: tuple[np.ndarray, tuple[float, float, float, float]] | None,
    center: tuple[float, float],
    z_km: float = 0.0,
) -> bool:
    if texture is None:
        return False
    image, extent = texture
    west, east, south, north = extent
    x = np.linspace((west - center[0]) / 1000.0, (east - center[0]) / 1000.0, image.shape[1])
    y = np.linspace((south - center[1]) / 1000.0, (north - center[1]) / 1000.0, image.shape[0])
    xx, yy = np.meshgrid(x, y)
    zz = np.full_like(xx, z_km)
    rgb = image[:, :, :3].astype(float) / 255.0
    rgb = rgb[::-1, :, :]
    alpha = np.full((*rgb.shape[:2], 1), 0.34)
    rgba = np.concatenate([rgb, alpha], axis=2)
    ax.plot_surface(
        xx,
        yy,
        zz,
        rstride=max(1, image.shape[0] // 180),
        cstride=max(1, image.shape[1] // 180),
        facecolors=rgba,
        linewidth=0,
        antialiased=False,
        shade=False,
        zorder=0,
    )
    return True


def add_polyline_3d(ax, rings: list[tuple[np.ndarray, np.ndarray]], z: float, **kwargs) -> None:
    for x, y in rings:
        ax.plot(x, y, np.full_like(x, z, dtype=float), **kwargs)


def add_bbox_frame_3d(ax, bbox_wm: object, center: tuple[float, float], z: float, **kwargs) -> None:
    x0, y0, x1, y1 = bbox_wm.bounds
    xs = np.array([x0, x1, x1, x0, x0], dtype=float)
    ys = np.array([y0, y0, y1, y1, y0], dtype=float)
    xr, yr = relative_xy(xs, ys, center)
    ax.plot(xr, yr, np.full_like(xr, z), **kwargs)


def add_city_markers_3d(
    ax,
    center: tuple[float, float],
    depth_limit_km: float,
    azim: float,
    surface_lookup: dict[str, float],
    label_stride: int = 1,
) -> None:
    to_wm = Transformer.from_crs(WGS84, WEB_MERCATOR, always_xy=True)
    markers = []
    view_vector = np.array([math.cos(math.radians(azim)), math.sin(math.radians(azim))])
    for index, (name, (lon, lat)) in enumerate(CITY_MARKERS.items()):
        wm_x, wm_y = to_wm.transform(lon, lat)
        x, y = relative_xy(np.asarray([wm_x]), np.asarray([wm_y]), center)
        view_depth = float(np.dot(np.array([x[0], y[0]]), view_vector))
        markers.append((view_depth, index, name, float(x[0]), float(y[0])))
    markers.sort(key=lambda item: item[0])
    for _, index, name, x, y in markers:
        surface_z = -float(surface_lookup.get(name, 0.0))
        ax.plot(
            [x, x],
            [y, y],
            [0.0, surface_z],
            color="#464C55",
            alpha=0.82,
            linewidth=1.65,
            zorder=20 + index,
        )
        if surface_z > -depth_limit_km:
            ax.plot(
                [x, x],
                [y, y],
                [surface_z, -depth_limit_km],
                color="#464C55",
                alpha=0.22,
                linewidth=1.0,
                linestyle="--",
                zorder=10 + index,
            )
        ax.scatter(
            [x],
            [y],
            [0.0],
            s=42,
            color="#FFE15B",
            edgecolor="#1F2430",
            linewidth=0.85,
            depthshade=False,
            zorder=40 + index,
        )
        if index % label_stride == 0:
            x2, y2, _ = proj3d.proj_transform(x, y, 0.65, ax.get_proj())
            ax.annotate(
                name,
                xy=(x2, y2),
                xycoords="data",
                xytext=(0, 5),
                textcoords="offset points",
                fontsize=9.0,
                ha="center",
                va="bottom",
                color=TOKENS["ink"],
                path_effects=[pe.withStroke(linewidth=3.2, foreground="white", alpha=0.96)],
                zorder=100 + index,
                clip_on=False,
            )


def city_surface_depth_lookup(
    depth: np.ndarray,
    wm_x: np.ndarray,
    wm_y: np.ndarray,
    center: tuple[float, float],
    vertical_exaggeration: float,
) -> dict[str, float]:
    to_wm = Transformer.from_crs(WGS84, WEB_MERCATOR, always_xy=True)
    x_rel, y_rel = relative_xy(wm_x, wm_y, center)
    valid = np.isfinite(depth)
    lookup = {}
    for name, (lon, lat) in CITY_MARKERS.items():
        city_wm_x, city_wm_y = to_wm.transform(lon, lat)
        city_x, city_y = relative_xy(np.asarray([city_wm_x]), np.asarray([city_wm_y]), center)
        distances = np.hypot(x_rel - city_x[0], y_rel - city_y[0])
        distances = np.where(valid, distances, np.inf)
        if np.isfinite(distances).any():
            row, col = np.unravel_index(int(np.nanargmin(distances)), distances.shape)
            lookup[name] = float(depth[row, col]) * vertical_exaggeration
        else:
            lookup[name] = 0.0
    return lookup


def add_basin_sidewalls(
    ax,
    rings: list[tuple[np.ndarray, np.ndarray]],
    z_bottom: float,
    color: str = "#A3BEFA",
) -> None:
    for x, y in rings:
        vertices = []
        for i in range(len(x) - 1):
            vertices.append([(x[i], y[i], 0.0), (x[i + 1], y[i + 1], 0.0), (x[i + 1], y[i + 1], z_bottom), (x[i], y[i], z_bottom)])
        walls = Poly3DCollection(vertices, facecolor=color, edgecolor="none", alpha=0.08)
        ax.add_collection3d(walls)


def format_3d_axis(ax, title: str, xlim: tuple[float, float], ylim: tuple[float, float], zlim: tuple[float, float], ve: float) -> None:
    ax.set_title(title, pad=10, fontsize=13, fontweight="bold")
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_zlim(zlim)
    ax.set_xlabel("Web Mercator x offset (km)", labelpad=7)
    ax.set_ylabel("Web Mercator y offset (km)", labelpad=7)
    ax.set_zlabel("Depth (km)", labelpad=6)
    ax.zaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{abs(value / ve):.0f}"))
    ax.grid(True, alpha=0.28)
    x_span = max(1.0, xlim[1] - xlim[0])
    y_span = max(1.0, ylim[1] - ylim[0])
    z_span = max(1.0, zlim[1] - zlim[0])
    ax.set_box_aspect((x_span, y_span, z_span))


def plot_surface_contact_sheet(
    key: str,
    depth: np.ndarray,
    wm_x: np.ndarray,
    wm_y: np.ndarray,
    geom: BasinGeometry,
    model_label: str,
    texture: tuple[np.ndarray, tuple[float, float, float, float]] | None,
    out_png: Path,
    out_svg: Path,
    vertical_exaggeration: float,
    surface_alpha: float,
) -> plt.Figure:
    _, label = THRESHOLDS[key]
    bbox_center = geom.bbox_web_mercator.centroid
    center = (float(bbox_center.x), float(bbox_center.y))
    x_rel, y_rel = relative_xy(wm_x, wm_y, center)
    depth_masked = np.ma.masked_invalid(depth)
    z_plot = -vertical_exaggeration * depth_masked
    valid_depth = depth[np.isfinite(depth)]
    if len(valid_depth) == 0:
        raise ValueError(f"No valid depth samples for {key}")
    max_depth = float(np.nanmax(valid_depth))
    z_bottom = -vertical_exaggeration * (max_depth + 0.8)
    rings = polygon_to_relative_rings(geom.web_mercator, center)
    marker_surface_depths = city_surface_depth_lookup(depth, wm_x, wm_y, center, vertical_exaggeration)
    views = [
        ("View from northwest", 24, -135),
        ("View from southeast", 24, 45),
        ("View from southwest", 28, -55),
        ("Near overhead, north up", 88, -90),
    ]

    fig = plt.figure(figsize=(18, 13), constrained_layout=False)
    fig.suptitle(
        f"LA Basin {label} surface in {model_label}",
        fontsize=21,
        fontweight="bold",
        y=0.985,
    )
    fig.text(
        0.5,
        0.955,
        f"Surface spans the full padded rectangular model box; GeoJSON basin outline is shown at surface. "
        f"Depth color is true km; vertical scale is {vertical_exaggeration:g}x exaggerated for legibility.",
        ha="center",
        va="top",
        fontsize=12.5,
        color=TOKENS["muted"],
    )

    norm = Normalize(vmin=0.0, vmax=max(3.0, math.ceil(max_depth)))
    cmap = plt.get_cmap("viridis_r")
    xlim = (float(np.nanmin(x_rel)), float(np.nanmax(x_rel)))
    ylim = (float(np.nanmin(y_rel)), float(np.nanmax(y_rel)))
    zlim = (z_bottom, 1.4)
    basemap_used = False

    for index, (view_name, elev, azim) in enumerate(views, start=1):
        ax = fig.add_subplot(2, 2, index, projection="3d")
        basemap_used = add_basemap_plane(ax, texture, center, z_km=0.0) or basemap_used
        facecolors = cmap(norm(depth_masked.filled(np.nan)))
        facecolors[..., -1] = np.where(np.isfinite(depth), surface_alpha, 0.0)
        ax.plot_surface(
            x_rel,
            y_rel,
            z_plot,
            facecolors=facecolors,
            rstride=1,
            cstride=1,
            linewidth=0.08,
            edgecolor=(0.18, 0.22, 0.28, 0.16),
            antialiased=True,
            shade=False,
            zorder=5,
        )
        add_basin_sidewalls(ax, rings, z_bottom)
        add_polyline_3d(ax, rings, 0.04, color="#1F2430", linewidth=2.0, alpha=0.92, zorder=9)
        add_bbox_frame_3d(ax, geom.bbox_web_mercator, center, 0.08, color=TOKENS["orange"], linewidth=2.2, alpha=0.96, zorder=10)
        ax.view_init(elev=elev, azim=azim)
        format_3d_axis(ax, view_name, xlim, ylim, zlim, vertical_exaggeration)
        add_city_markers_3d(
            ax,
            center,
            vertical_exaggeration * (max_depth + 0.2),
            azim=azim,
            surface_lookup=marker_surface_depths,
        )

    cax = fig.add_axes([0.92, 0.18, 0.018, 0.58])
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    cbar = fig.colorbar(sm, cax=cax)
    cbar.set_label(f"{label} depth (km)", fontsize=12.5)
    cbar.ax.tick_params(labelsize=10)
    note = "Surface basemap texture rendered on z=0 plane." if basemap_used else "Basemap texture unavailable; city marker lines provide geographic reference."
    fig.text(0.04, 0.025, note, ha="left", fontsize=10.5, color=TOKENS["muted"])
    fig.subplots_adjust(left=0.03, right=0.9, top=0.92, bottom=0.06, wspace=0.04, hspace=0.1)
    fig.savefig(out_png, dpi=240, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    return fig


def plot_plan_map(
    geom: BasinGeometry,
    output_path: Path,
    source: str,
    zoom: int,
    cache_dir: Path,
    model_label: str,
) -> tuple[plt.Figure, bool]:
    fig, ax = plt.subplots(figsize=(10.5, 10.0))
    west, south, east, north = geom.bbox_web_mercator.bounds
    ax.set_xlim(west, east)
    ax.set_ylim(south, north)
    basemap_ok = False
    try:
        add_required_basemap(ax, source=source, cache_dir=cache_dir, zoom=zoom)
        basemap_ok = True
    except Exception as exc:
        ax.text(0.01, 0.01, f"Basemap unavailable: {exc}", transform=ax.transAxes, fontsize=9, color=TOKENS["muted"])
    for polygon in iter_polygons(geom.web_mercator):
        x, y = polygon.exterior.xy
        ax.fill(x, y, color="#A3BEFA", alpha=0.15, zorder=3)
        ax.plot(x, y, color=TOKENS["blue"], linewidth=2.2, zorder=4, label="LA Basin GeoJSON")
    rect = Rectangle((west, south), east - west, north - south, fill=False, edgecolor=TOKENS["orange"], linewidth=2.4, zorder=5)
    ax.add_patch(rect)
    to_wm = Transformer.from_crs(WGS84, WEB_MERCATOR, always_xy=True)
    for name, (lon, lat) in CITY_MARKERS.items():
        x, y = to_wm.transform(lon, lat)
        ax.scatter(x, y, s=34, color=TOKENS["ink"], edgecolor="white", linewidth=0.8, zorder=6)
        ax.text(
            x + 1200,
            y + 1200,
            textwrap.fill(name, 14),
            fontsize=9.5,
            color=TOKENS["ink"],
            path_effects=[pe.withStroke(linewidth=2.4, foreground="white", alpha=0.9)],
            zorder=7,
        )
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(f"LA Basin GeoJSON cutout box and geographic markers for {model_label}", fontsize=17, fontweight="bold", pad=12)
    ax.set_xlabel("Web Mercator x (m)")
    ax.set_ylabel("Web Mercator y (m)")
    ax.tick_params(labelsize=9)
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles[:1], labels[:1], loc="upper right", frameon=True, framealpha=0.92)
    fig.tight_layout()
    fig.savefig(output_path, dpi=240, bbox_inches="tight")
    return fig, basemap_ok


def build_surface_table(
    x_grid: np.ndarray,
    y_grid: np.ndarray,
    wm_x: np.ndarray,
    wm_y: np.ndarray,
    basin_mask: np.ndarray,
    surfaces: dict[str, np.ndarray],
) -> pd.DataFrame:
    to_lonlat = Transformer.from_crs(CVM_UTM, WGS84, always_xy=True)
    full_mask = np.ones(x_grid.shape, dtype=bool)
    lon, lat = to_lonlat.transform(x_grid[full_mask], y_grid[full_mask])
    out = pd.DataFrame(
        {
            "lon": np.asarray(lon, dtype=float),
            "lat": np.asarray(lat, dtype=float),
            "utm_x_m": x_grid[full_mask].astype(float),
            "utm_y_m": y_grid[full_mask].astype(float),
            "web_mercator_x_m": wm_x[full_mask].astype(float),
            "web_mercator_y_m": wm_y[full_mask].astype(float),
            "inside_la_basin_polygon": basin_mask[full_mask].astype(bool),
        }
    )
    for key, (_, label) in THRESHOLDS.items():
        out[f"{key}_depth_km"] = surfaces[key][full_mask].astype(float)
        out.attrs[f"{key}_label"] = label
    return out


def build_city_marker_table(geom: BasinGeometry) -> pd.DataFrame:
    to_wm = Transformer.from_crs(WGS84, WEB_MERCATOR, always_xy=True)
    to_utm = Transformer.from_crs(WGS84, CVM_UTM, always_xy=True)
    rows = []
    for name, (lon, lat) in CITY_MARKERS.items():
        wm_x, wm_y = to_wm.transform(lon, lat)
        utm_x, utm_y = to_utm.transform(lon, lat)
        rows.append(
            {
                "name": name,
                "lon": lon,
                "lat": lat,
                "web_mercator_x_m": wm_x,
                "web_mercator_y_m": wm_y,
                "utm_x_m": utm_x,
                "utm_y_m": utm_y,
                "inside_la_basin_polygon": bool(geom.lonlat.contains(box(lon, lat, lon, lat).centroid)),
            }
        )
    return pd.DataFrame(rows)


def append_qa_note(report_dir: Path, generated: list[Path], basemap_ok: bool, texture_ok: bool, model_label: str) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    qa_path = report_dir / "figure_qa.md"
    lines = [
        "",
        f"## LA Basin 3D z(Vs) surface figures ({model_label})",
        "",
        "- Checked exported PNG contact sheets for z(Vs=1.0) and z(Vs=2.5): large titles, readable colorbars, separated city labels, and no obvious legend/colorbar overlap.",
        f"- Plan-view map basemap rendered: {'yes' if basemap_ok else 'no'}; 3D surface basemap texture rendered: {'yes' if texture_ok else 'no'}.",
        "- The 3D panels use true depth values in the color scale with explicit vertical exaggeration noted in the subtitle.",
        "- Generated files:",
    ]
    lines.extend(f"  - `{path}`" for path in generated)
    lines.append("")
    with qa_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    set_theme()
    output_root = resolve_output_root(args.output_root).resolve()
    figures_dir = output_root / "figures" / "la_basin_3d_vs_depth_surfaces"
    tables_dir = output_root / "tables"
    report_dir = output_root / "report"
    basemap_cache_dir = output_root / "basemap_cache"
    for directory in (figures_dir, tables_dir, report_dir, basemap_cache_dir):
        directory.mkdir(parents=True, exist_ok=True)

    geom = build_basin_geometry(args.regions, args.bbox_pad_km)
    x_grid, y_grid, basin_mask = build_grid(geom, args.grid_spacing_km)
    full_box_mask = np.ones(x_grid.shape, dtype=bool)
    sampler = ModelSampler(args.model_h5, node_stride=args.model_node_stride)
    surfaces = sample_depth_surfaces(sampler, x_grid, y_grid, full_box_mask, args.sample_chunk_size)
    wm_x, wm_y = transform_grid_to_web_mercator(x_grid, y_grid)
    texture = load_basemap_texture(geom.bbox_web_mercator, args.basemap_source, args.basemap_zoom)

    table_path = tables_dir / "la_basin_3d_vs_depth_surface_grid.parquet"
    csv_table_path = tables_dir / "la_basin_3d_vs_depth_surface_grid.csv"
    city_markers_path = tables_dir / "la_basin_3d_vs_depth_city_markers.csv"
    surface_table = build_surface_table(x_grid, y_grid, wm_x, wm_y, basin_mask, surfaces)
    surface_table.to_parquet(table_path, index=False)
    surface_table.to_csv(csv_table_path, index=False)
    build_city_marker_table(geom).to_csv(city_markers_path, index=False)

    generated: list[Path] = []
    plan_map = figures_dir / "la_basin_3d_sampling_box_map.png"
    plan_fig, plan_basemap_ok = plot_plan_map(geom, plan_map, args.basemap_source, args.basemap_zoom, basemap_cache_dir, args.model_label)
    plt.close(plan_fig)
    generated.append(plan_map)

    surface_figs: list[Path] = []
    for key in THRESHOLDS:
        output_key = "z2p5" if key == "z2p5" else key
        png = figures_dir / f"la_basin_{output_key}_3d_multiangle.png"
        svg = figures_dir / f"la_basin_{output_key}_3d_multiangle.svg"
        fig = plot_surface_contact_sheet(
            key,
            surfaces[key],
            wm_x,
            wm_y,
            geom,
            args.model_label,
            texture,
            png,
            svg,
            args.z1_vertical_exaggeration if key == "z1" else args.vertical_exaggeration,
            args.surface_alpha,
        )
        plt.close(fig)
        surface_figs.extend([png, svg])
        generated.extend([png, svg])

    pdf_path = report_dir / "la_basin_3d_vs_depth_surfaces.pdf"
    with PdfPages(pdf_path) as pdf:
        for image_path in [plan_map] + [path for path in surface_figs if path.suffix == ".png"]:
            img = plt.imread(image_path)
            fig, ax = plt.subplots(figsize=(11, 8.5))
            ax.imshow(img)
            ax.axis("off")
            fig.tight_layout(pad=0)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
    generated.append(pdf_path)

    manifest_path = report_dir / "la_basin_3d_vs_depth_surfaces_manifest.json"
    manifest = {
        "region_name": geom.name,
        "inputs": {
            "regions": str(args.regions),
            "model_h5": str(args.model_h5),
            "model_label": args.model_label,
            "grid_spacing_km": args.grid_spacing_km,
            "bbox_pad_km": args.bbox_pad_km,
            "node_stride": args.model_node_stride,
            "basemap_source": args.basemap_source,
            "basemap_zoom": args.basemap_zoom,
            "vertical_exaggeration": args.vertical_exaggeration,
            "z2p5_vertical_exaggeration": args.vertical_exaggeration,
            "z1_vertical_exaggeration": args.z1_vertical_exaggeration,
            "surface_alpha": args.surface_alpha,
            "surface_extent": "full padded rectangular model box",
        },
        "outputs": {
            "grid": str(table_path),
            "grid_csv": str(csv_table_path),
            "city_markers": str(city_markers_path),
            "figures": [str(plan_map)] + [str(path) for path in surface_figs if path.suffix == ".png"],
            "pdf": str(pdf_path),
        },
        "basemap": {
            "overview_rendered": bool(plan_basemap_ok),
            "surface_texture_rendered": bool(texture is not None),
            "surface_texture_source": args.basemap_source if texture is not None else None,
        },
    }
    write_manifest(manifest_path, manifest)
    generated.append(manifest_path)
    generated.append(table_path)
    append_qa_note(report_dir, generated, plan_basemap_ok, texture is not None, args.model_label)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
