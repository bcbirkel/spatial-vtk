#!/usr/bin/env python3
"""Render LA Basin long-axis and perpendicular candidate cross sections."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely.geometry import LineString
from shapely.ops import transform as shapely_transform

from cvmsi_hypothesis_study import (
    COLORS,
    CVM_UTM,
    DEFAULT_BASEMAP_SOURCE,
    DEFAULT_BASEMAP_ZOOM,
    DEFAULT_MODEL_H5,
    DEFAULT_OUTPUT,
    DEFAULT_REGIONS,
    WEB_MERCATOR,
    WGS84,
    ModelSampler,
    add_required_basemap,
    format_projected_map_axis,
    iter_polygons,
    load_regions,
    plot_model_cross_sections,
    set_plot_theme,
)


METRIC = "PGA"
BANDS = (
    ("1-2 sec", "1_2sec"),
    ("2-3 sec", "2_3sec"),
    ("3-5 sec", "3_5sec"),
)
STATION_CORRIDOR_KM = 10.0
PROFILE_COUNT = 5
PROFILE_MARGIN_KM = 18.0
CLOCKWISE_ROTATION_DEG = 10.0
LOWESS_FRAC = 0.10
LOWESS_ALPHA = 0.62


def bearing_from_unit(unit: np.ndarray) -> float:
    return float((math.degrees(math.atan2(float(unit[0]), float(unit[1]))) + 360.0) % 360.0)


def unit_from_bearing(bearing_deg: float) -> np.ndarray:
    radians = math.radians(float(bearing_deg))
    return np.asarray([math.sin(radians), math.cos(radians)], dtype=float)


def circular_delta_deg(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def orient_unit_to_bearing(unit: np.ndarray, target_bearing: float) -> np.ndarray:
    bearing = bearing_from_unit(unit)
    flipped = -unit
    flipped_bearing = bearing_from_unit(flipped)
    if circular_delta_deg(flipped_bearing, target_bearing) < circular_delta_deg(bearing, target_bearing):
        return flipped
    return unit


def basin_boundary_points(geom: object) -> np.ndarray:
    points: list[tuple[float, float]] = []
    for polygon in iter_polygons(geom):
        points.extend((float(x), float(y)) for x, y in polygon.exterior.coords)
    if not points:
        raise ValueError("LA Basin geometry has no polygon boundary points")
    return np.asarray(points, dtype=float)


def basin_axis_basis(basin_utm: object) -> tuple[np.ndarray, np.ndarray]:
    rectangle = basin_utm.minimum_rotated_rectangle
    coords = np.asarray(rectangle.exterior.coords[:-1], dtype=float)
    if coords.shape[0] != 4:
        raise ValueError("Could not derive a rectangular LA Basin orientation")
    edges = []
    for index in range(4):
        edge = coords[(index + 1) % 4] - coords[index]
        length = float(np.linalg.norm(edge))
        if length > 0.0:
            edges.append((length, edge / length))
    axis = max(edges, key=lambda item: item[0])[1]
    axis = orient_unit_to_bearing(axis, 135.0)
    axis = unit_from_bearing(bearing_from_unit(axis) + CLOCKWISE_ROTATION_DEG)
    normal = unit_from_bearing(bearing_from_unit(axis) - 90.0)
    return axis, normal


def projection_extent(points: np.ndarray, center: np.ndarray, unit: np.ndarray) -> tuple[float, float]:
    projected = (points - center) @ unit
    return float(projected.min()), float(projected.max())


def line_lonlat(
    center_xy: np.ndarray,
    direction_unit: np.ndarray,
    half_length_m: float,
    inverse_transformer: Transformer,
) -> tuple[tuple[float, float], tuple[float, float]]:
    start_xy = center_xy - direction_unit * half_length_m
    end_xy = center_xy + direction_unit * half_length_m
    start_ll = inverse_transformer.transform(float(start_xy[0]), float(start_xy[1]))
    end_ll = inverse_transformer.transform(float(end_xy[0]), float(end_xy[1]))
    return (float(start_ll[0]), float(start_ll[1])), (float(end_ll[0]), float(end_ll[1]))


def build_profile_families(regions: list) -> tuple[list[tuple[str, tuple[float, float], tuple[float, float]]], list[tuple[str, tuple[float, float], tuple[float, float]]], pd.DataFrame]:
    la_basin = next((region for region in regions if region.name.lower() == "los angeles basin"), None)
    if la_basin is None:
        raise ValueError("Los Angeles Basin region was not found")

    to_utm = Transformer.from_crs(WGS84, CVM_UTM, always_xy=True)
    from_utm = Transformer.from_crs(CVM_UTM, WGS84, always_xy=True)
    basin_utm = shapely_transform(to_utm.transform, la_basin.geometry_lonlat)
    axis, normal = basin_axis_basis(basin_utm)
    center = np.asarray([basin_utm.centroid.x, basin_utm.centroid.y], dtype=float)
    boundary = basin_boundary_points(basin_utm)
    axis_min, axis_max = projection_extent(boundary, center, axis)
    normal_min, normal_max = projection_extent(boundary, center, normal)
    axis_half = max(abs(axis_min), abs(axis_max)) + PROFILE_MARGIN_KM * 1000.0
    normal_half = max(abs(normal_min), abs(normal_max)) + PROFILE_MARGIN_KM * 1000.0
    normal_offsets = np.linspace(
        -0.38 * (normal_max - normal_min),
        0.38 * (normal_max - normal_min),
        PROFILE_COUNT,
    )
    axis_offsets = np.linspace(
        -0.38 * (axis_max - axis_min),
        0.38 * (axis_max - axis_min),
        PROFILE_COUNT,
    )

    long_sections: list[tuple[str, tuple[float, float], tuple[float, float]]] = []
    perp_sections: list[tuple[str, tuple[float, float], tuple[float, float]]] = []
    rows: list[dict[str, object]] = []

    for idx, offset_m in enumerate(normal_offsets, start=1):
        profile_id = f"L{idx}"
        line_center = center + normal * offset_m
        start_ll, end_ll = line_lonlat(line_center, axis, axis_half, from_utm)
        start_xy = np.asarray(to_utm.transform(*start_ll), dtype=float)
        end_xy = np.asarray(to_utm.transform(*end_ll), dtype=float)
        line = LineString([tuple(start_xy), tuple(end_xy)])
        intersection = line.intersection(basin_utm)
        title = f"{profile_id} LA Basin long-axis profile"
        long_sections.append((title, start_ll, end_ll))
        rows.append(
            {
                "profile_id": profile_id,
                "family": "long_axis",
                "bearing_deg": bearing_from_unit(axis),
                "clockwise_rotation_deg": CLOCKWISE_ROTATION_DEG,
                "offset_km": float(offset_m / 1000.0),
                "center_lon": float(from_utm.transform(float(center[0]), float(center[1]))[0]),
                "center_lat": float(from_utm.transform(float(center[0]), float(center[1]))[1]),
                "start_lon": start_ll[0],
                "start_lat": start_ll[1],
                "end_lon": end_ll[0],
                "end_lat": end_ll[1],
                "la_basin_intersection_km": float(intersection.length / 1000.0) if not intersection.is_empty else 0.0,
            }
        )

    for idx, offset_m in enumerate(axis_offsets, start=1):
        profile_id = f"P{idx}"
        line_center = center + axis * offset_m
        start_ll, end_ll = line_lonlat(line_center, normal, normal_half, from_utm)
        start_xy = np.asarray(to_utm.transform(*start_ll), dtype=float)
        end_xy = np.asarray(to_utm.transform(*end_ll), dtype=float)
        line = LineString([tuple(start_xy), tuple(end_xy)])
        intersection = line.intersection(basin_utm)
        title = f"{profile_id} LA Basin perpendicular profile"
        perp_sections.append((title, start_ll, end_ll))
        rows.append(
            {
                "profile_id": profile_id,
                "family": "perpendicular",
                "bearing_deg": bearing_from_unit(normal),
                "clockwise_rotation_deg": CLOCKWISE_ROTATION_DEG,
                "offset_km": float(offset_m / 1000.0),
                "center_lon": float(from_utm.transform(float(center[0]), float(center[1]))[0]),
                "center_lat": float(from_utm.transform(float(center[0]), float(center[1]))[1]),
                "start_lon": start_ll[0],
                "start_lat": start_ll[1],
                "end_lon": end_ll[0],
                "end_lat": end_ll[1],
                "la_basin_intersection_km": float(intersection.length / 1000.0) if not intersection.is_empty else 0.0,
            }
        )

    return long_sections, perp_sections, pd.DataFrame(rows)


def iter_section_rows(metadata: pd.DataFrame, family: str) -> Iterable[object]:
    yield from metadata.loc[metadata["family"].eq(family)].itertuples(index=False)


def render_candidate_map(
    regions: list,
    sections: list[tuple[str, tuple[float, float], tuple[float, float]]],
    metadata: pd.DataFrame,
    output_path: Path,
    *,
    basemap_cache_dir: Path,
) -> Path:
    la_basin = next(region for region in regions if region.name.lower() == "los angeles basin")
    to_web = Transformer.from_crs(WGS84, WEB_MERCATOR, always_xy=True)
    basin_web = shapely_transform(to_web.transform, la_basin.geometry_lonlat)
    fig, ax = plt.subplots(figsize=(12.8, 9.0))
    line_records = metadata.set_index("profile_id")
    xs: list[float] = []
    ys: list[float] = []
    for _, start_ll, end_ll in sections:
        line_x, line_y = to_web.transform([start_ll[0], end_ll[0]], [start_ll[1], end_ll[1]])
        xs.extend(line_x)
        ys.extend(line_y)
    for polygon in iter_polygons(basin_web):
        x, y = polygon.exterior.xy
        xs.extend(x)
        ys.extend(y)
    pad_x = max((max(xs) - min(xs)) * 0.16, 11000.0)
    pad_y = max((max(ys) - min(ys)) * 0.16, 11000.0)
    ax.set_xlim(min(xs) - pad_x, max(xs) + pad_x)
    ax.set_ylim(min(ys) - pad_y, max(ys) + pad_y)
    add_required_basemap(ax, source=DEFAULT_BASEMAP_SOURCE, cache_dir=basemap_cache_dir, zoom=DEFAULT_BASEMAP_ZOOM)
    for polygon in iter_polygons(basin_web):
        x, y = polygon.exterior.xy
        ax.fill(x, y, facecolor="#FFFFFF", alpha=0.20, edgecolor=COLORS["ink"], linewidth=1.2, zorder=4)
    for title, start_ll, end_ll in sections:
        profile_id = title.split()[0]
        record = line_records.loc[profile_id]
        color = COLORS["blue"] if record["family"] == "long_axis" else COLORS["gold"]
        line_x, line_y = to_web.transform([start_ll[0], end_ll[0]], [start_ll[1], end_ll[1]])
        ax.plot(line_x, line_y, color=color, linewidth=2.7, alpha=0.92, zorder=6)
        ax.scatter(line_x, line_y, marker="s", s=34, color=color, edgecolor="white", linewidth=0.6, zorder=7)
        label_x, label_y = 0.54 * line_x[0] + 0.46 * line_x[1], 0.54 * line_y[0] + 0.46 * line_y[1]
        ax.text(
            label_x,
            label_y,
            profile_id,
            color="white",
            fontsize=10.5,
            fontweight="bold",
            ha="center",
            va="center",
            bbox={"facecolor": color, "edgecolor": "white", "boxstyle": "round,pad=0.22", "linewidth": 0.6, "alpha": 0.95},
            zorder=8,
        )
    format_projected_map_axis(ax)
    ax.set_title("Rotated LA Basin candidate cross-section lines", fontsize=18, fontweight="bold", color=COLORS["ink"], pad=16)
    legend_handles = [
        Line2D([0], [0], color=COLORS["blue"], linewidth=2.7, label="Long-axis family"),
        Line2D([0], [0], color=COLORS["gold"], linewidth=2.7, label="Perpendicular family"),
        Line2D([0], [0], color=COLORS["ink"], linewidth=1.2, label="LA Basin outline"),
    ]
    ax.legend(handles=legend_handles, loc="upper right", frameon=True, fontsize=10.5)
    angle_long = metadata.loc[metadata["family"].eq("long_axis"), "bearing_deg"].iloc[0]
    angle_perp = metadata.loc[metadata["family"].eq("perpendicular"), "bearing_deg"].iloc[0]
    ax.text(
        0.015,
        0.018,
        f"Long-axis bearing {angle_long:.1f} deg; perpendicular bearing {angle_perp:.1f} deg. "
        f"Families are rotated {CLOCKWISE_ROTATION_DEG:.0f} deg clockwise and centered on the LA Basin centroid.",
        transform=ax.transAxes,
        fontsize=10,
        color=COLORS["ink"],
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 4.0},
        zorder=9,
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)
    return output_path


def build_contact_sheet(paths: list[Path], rows: list[object], output_path: Path, *, title: str) -> Path:
    ncols = 2
    nrows = math.ceil(len(paths) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(18.5, 5.2 * nrows))
    axes = axes.ravel() if hasattr(axes, "ravel") else [axes]
    for ax in axes:
        ax.axis("off")
    for ax, path, row in zip(axes, paths, rows):
        image = plt.imread(path)
        ax.imshow(image)
        ax.set_title(
            f"{row.profile_id}: bearing {row.bearing_deg:.1f} deg, LA Basin crossing {row.la_basin_intersection_km:.1f} km",
            fontsize=12,
            fontweight="bold",
        )
        ax.axis("off")
    fig.suptitle(title, fontsize=16, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.985])
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def render_section_family(
    *,
    pairs: pd.DataFrame,
    regions: list,
    sampler: ModelSampler,
    output_dir: Path,
    sections: list[tuple[str, tuple[float, float], tuple[float, float]]],
    rows: list[object],
    family: str,
    band: str,
    band_slug: str,
    contact_title: str,
    contact_name: str,
) -> list[Path]:
    figures_dir = output_dir / "figures"
    family_dir = figures_dir / "la_basin_axis_profile_sections_rot10" / band_slug / family
    family_dir.mkdir(parents=True, exist_ok=True)
    rendered_paths: list[Path] = []
    for section, row in zip(sections, rows):
        title = f"CVM-SI Vs LA Basin {row.profile_id} profile"
        note = (
            f"{METRIC} {band} station medians use all available events; stations are limited to "
            f"{STATION_CORRIDOR_KM:g} km from the profile. Black curve is event-weighted LOWESS "
            f"with span {LOWESS_FRAC:.2f} and alpha {LOWESS_ALPHA:.2f}.\n"
            f"Profile bearing {row.bearing_deg:.1f} deg; LA Basin polygon crossing {row.la_basin_intersection_km:.1f} km. "
            "Stars mark event epicenters contributing to the plotted station subset."
        )
        path = plot_model_cross_sections(
            pairs,
            regions,
            sampler,
            family_dir,
            basemap_cache_dir=output_dir / "basemap_cache",
            basemap_zoom=DEFAULT_BASEMAP_ZOOM,
            metric=METRIC,
            band=band,
            output_name=f"fig_{row.profile_id.lower()}_la_basin_{family}_rot10_{METRIC.lower()}_{band_slug}.png",
            sections=[section],
            figure_title=title,
            figure_note=note,
            figsize=(19.8, 7.8),
            station_corridor_km=STATION_CORRIDOR_KM,
            show_events_on_map=True,
            show_lowess=True,
            lowess_frac=LOWESS_FRAC,
            lowess_alpha=LOWESS_ALPHA,
        )
        rendered_paths.append(path)
    contact_path = figures_dir / contact_name
    build_contact_sheet(rendered_paths, rows, contact_path, title=contact_title)
    return [*rendered_paths, contact_path]


def main() -> int:
    set_plot_theme()
    output_dir = DEFAULT_OUTPUT
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    pairs = pd.read_parquet(tables_dir / "pairs.parquet")
    regions = load_regions(DEFAULT_REGIONS)
    long_sections, perp_sections, metadata = build_profile_families(regions)
    metadata_path = tables_dir / "la_basin_axis_profile_sections_rot10_passbands.csv"
    metadata.to_csv(metadata_path, index=False)

    all_sections = [*long_sections, *perp_sections]
    map_path = figures_dir / "fig_06j_la_basin_axis_candidate_lines_rot10_map.png"
    render_candidate_map(regions, all_sections, metadata, map_path, basemap_cache_dir=output_dir / "basemap_cache")

    sampler = ModelSampler(DEFAULT_MODEL_H5, node_stride=2)
    long_rows = list(iter_section_rows(metadata, "long_axis"))
    perp_rows = list(iter_section_rows(metadata, "perpendicular"))
    rendered_paths: list[Path] = []
    for band, band_slug in BANDS:
        rendered_paths.extend(
            render_section_family(
                pairs=pairs,
                regions=regions,
                sampler=sampler,
                output_dir=output_dir,
                sections=long_sections,
                rows=long_rows,
                family="long_axis",
                band=band,
                band_slug=band_slug,
                contact_title=f"LA Basin rotated long-axis CVM-SI cross sections ({METRIC} {band})",
                contact_name=f"fig_06k_la_basin_long_axis_rot10_{band_slug}_cross_sections_contact_sheet.png",
            )
        )
        rendered_paths.extend(
            render_section_family(
                pairs=pairs,
                regions=regions,
                sampler=sampler,
                output_dir=output_dir,
                sections=perp_sections,
                rows=perp_rows,
                family="perpendicular",
                band=band,
                band_slug=band_slug,
                contact_title=f"LA Basin rotated perpendicular CVM-SI cross sections ({METRIC} {band})",
                contact_name=f"fig_06l_la_basin_perpendicular_rot10_{band_slug}_cross_sections_contact_sheet.png",
            )
        )

    print(metadata_path)
    print(map_path)
    for path in rendered_paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
