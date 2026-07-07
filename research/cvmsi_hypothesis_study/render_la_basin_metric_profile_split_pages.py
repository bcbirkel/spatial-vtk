#!/usr/bin/env python3
"""Render one-page-per-profile LA Basin PGA cross-section atlas."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.cm import ScalarMappable
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely.ops import transform as shapely_transform

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cvmsi_hypothesis_study import (  # noqa: E402
    COLORS,
    CVM_UTM,
    DEFAULT_BASEMAP_SOURCE,
    DEFAULT_BASEMAP_ZOOM,
    DEFAULT_METRICS,
    DEFAULT_MODEL,
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
    set_plot_theme,
)
from render_la_basin_axis_profile_sections import (  # noqa: E402
    build_profile_families,
    render_candidate_map,
)
from render_la_basin_metric_profile_atlas import (  # noqa: E402
    ATLAS_LOWESS_FRAC,
    PROFILE_ORDER,
    VS_GRADIENT_WINDOW_HALF_KM,
    add_png_page_to_pdf,
    add_vertical_property_gradient_cells,
    add_vertical_vs_gradient_cells,
    collapse_components,
    event_marker_size,
    filter_panel_rows,
    load_metric_rows,
    page_value_scale,
    plot_section_grid,
    sample_section_grids,
    section_line_utm,
    section_property_gradient_norm,
    section_vs_gradient_norm,
    station_projection,
    station_values,
    AtlasVariant,
    MetricPage,
    PanelSpec,
)


PASSBAND_COLORS = {
    "1-2 sec": COLORS["blue"],
    "2-3 sec": COLORS["gold"],
    "3-5 sec": COLORS["red"],
    "1-5 sec": COLORS["ink"],
}

PGA_BANDS = (
    ("1-2 sec", "1-2 sec"),
    ("2-3 sec", "2-3 sec"),
    ("3-5 sec", "3-5 sec"),
    ("1-5 sec", "1-5 sec"),
)

SECTION_MAX_DEPTH_KM = 12.0
SPLIT_STATION_CORRIDOR_KM = 5.0

PROPERTY_LABELS = {"vs": "Vs", "vp": "Vp"}
PROPERTY_PDF_SUFFIX = {"vs": "", "vp": "_vp"}


def property_variants(model_property: str) -> tuple[AtlasVariant, AtlasVariant]:
    label = PROPERTY_LABELS[model_property]
    suffix = PROPERTY_PDF_SUFFIX[model_property]
    return (
        AtlasVariant(
            mode=model_property,
            output_subdir=f"split_pga{suffix}",
            filename_prefix=f"split_pga{suffix}",
            pdf_name=f"la_basin_metric_profile_split_pga{suffix}.pdf",
            manifest_name=f"la_basin_metric_profile_split_pga{suffix}_manifest.csv",
            title_suffix="",
            section_colorbar_label=f"{label} (km/s)",
            section_note="",
        ),
        AtlasVariant(
            mode=f"{model_property}-gradient",
            output_subdir=f"split_pga{suffix}",
            filename_prefix=f"split_pga{suffix}",
            pdf_name=f"la_basin_metric_profile_split_pga{suffix}.pdf",
            manifest_name=f"la_basin_metric_profile_split_pga{suffix}_manifest.csv",
            title_suffix="",
            section_colorbar_label=f"Vertical {label} gradient ((km/s)/km)",
            section_note="",
        ),
    )

def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--model-h5", type=Path, default=DEFAULT_MODEL_H5)
    parser.add_argument("--model-label", default="CVM-SI")
    parser.add_argument("--model-node-stride", type=int, default=2)
    parser.add_argument("--metric", default="PGA", choices=("PGA",))
    parser.add_argument("--metric-slug", default="pga")
    parser.add_argument("--model-property", default="vs", choices=("vs", "vp"))
    return parser.parse_args(argv)


def pga_page(model_label: str) -> MetricPage:
    panels = tuple(
        PanelSpec(
            label=label,
            metric="PGA",
            band=band,
            value_column="log2_residual",
            value_label="Station median PGA residual, log2(obs/syn)",
        )
        for label, band in PGA_BANDS
    )
    return MetricPage(
        slug="pga",
        title=f"LA Basin {model_label} split profile atlas: PGA",
        subtitle=(
            "One page per cross section. Passband residuals are station medians with "
            "25th-75th percentile event ranges; point area scales with event count."
        ),
        panels=panels,
        cmap="RdBu_r",
        y_label="Station median PGA residual, log2(obs/syn)",
        colorbar_label="Station median PGA residual, log2(obs/syn)",
        value_mode="residual",
    )


def threshold_depth(vs_profile: np.ndarray, depths_km: np.ndarray, threshold: float) -> float:
    valid = np.isfinite(vs_profile) & np.isfinite(depths_km)
    valid &= depths_km <= SECTION_MAX_DEPTH_KM
    if not valid.any():
        return np.nan
    values = vs_profile[valid]
    depths = depths_km[valid]
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


def interpolate_profile_values(section_grid: dict[str, object], projected_km: float, gradient_property: str = "vs") -> dict[str, float]:
    distances = np.asarray(section_grid["distances_km"], dtype=float)
    depths = np.asarray(section_grid["depths_km"], dtype=float)
    vs = np.asarray(section_grid["vs"], dtype=float)
    x = float(np.clip(projected_km, float(np.nanmin(distances)), float(np.nanmax(distances))))
    vs_profile = np.array([np.interp(x, distances, row) for row in vs], dtype=float)

    gradient_key = f"vertical_{gradient_property}_gradient_cell"
    gradients = np.asarray(section_grid[gradient_key], dtype=float)
    cell_depths = 0.5 * (depths[:-1] + depths[1:])
    cell_distances = 0.5 * (distances[:-1] + distances[1:])
    if gradients.size:
        grad_profile = np.array([np.interp(x, cell_distances, row) for row in gradients], dtype=float)
        finite = np.isfinite(grad_profile) & (cell_depths <= SECTION_MAX_DEPTH_KM)
        if finite.any():
            idx = int(np.nanargmax(np.abs(np.where(finite, grad_profile, np.nan))))
            max_grad_depth = float(cell_depths[idx])
            max_grad_value = float(grad_profile[idx])
            max_grad_strength = float(abs(max_grad_value))
        else:
            max_grad_depth = np.nan
            max_grad_value = np.nan
            max_grad_strength = np.nan
    else:
        max_grad_depth = np.nan
        max_grad_value = np.nan
        max_grad_strength = np.nan

    return {
        "z1_depth_km": threshold_depth(vs_profile, depths, 1.0),
        "z2p5_depth_km": threshold_depth(vs_profile, depths, 2.5),
        "max_abs_model_gradient_depth_km": max_grad_depth,
        "max_abs_model_gradient_value": max_grad_value,
        "max_abs_model_gradient_strength": max_grad_strength,
        f"max_abs_{gradient_property}_gradient_depth_km": max_grad_depth,
        f"max_abs_{gradient_property}_gradient_value": max_grad_value,
        f"max_abs_{gradient_property}_gradient_strength": max_grad_strength,
    }


def add_model_depth_columns(frame: pd.DataFrame, section_grid: dict[str, object], gradient_property: str = "vs") -> pd.DataFrame:
    if frame.empty:
        for column in (
            "z1_depth_km",
            "z2p5_depth_km",
            "max_abs_model_gradient_depth_km",
            "max_abs_model_gradient_value",
            "max_abs_model_gradient_strength",
            f"max_abs_{gradient_property}_gradient_depth_km",
            f"max_abs_{gradient_property}_gradient_value",
            f"max_abs_{gradient_property}_gradient_strength",
        ):
            frame[column] = []
        return frame
    rows = [
        interpolate_profile_values(section_grid, projected_km, gradient_property=gradient_property)
        for projected_km in frame["projected_km"].to_numpy(dtype=float)
    ]
    props = pd.DataFrame(rows, index=frame.index)
    return pd.concat([frame.reset_index(drop=True), props.reset_index(drop=True)], axis=1)


def weighted_pearson_r(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> tuple[float, int] | None:
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0.0)
    x = x[valid]
    y = y[valid]
    weights = weights[valid]
    if len(x) < 4 or np.nanstd(x) <= 0.0 or np.nanstd(y) <= 0.0:
        return None
    x_mean = float(np.average(x, weights=weights))
    y_mean = float(np.average(y, weights=weights))
    cov = float(np.average((x - x_mean) * (y - y_mean), weights=weights))
    var_x = float(np.average((x - x_mean) ** 2, weights=weights))
    var_y = float(np.average((y - y_mean) ** 2, weights=weights))
    r = cov / math.sqrt(var_x * var_y) if var_x > 0.0 and var_y > 0.0 else np.nan
    return float(r), int(len(x))


def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0.0)
    values = values[valid]
    weights = weights[valid]
    if values.size == 0:
        return np.nan
    order = np.argsort(values)
    values = values[order]
    weights = weights[order]
    cutoff = 0.5 * float(np.sum(weights))
    return float(values[np.searchsorted(np.cumsum(weights), cutoff, side="left")])


def weighted_lowess_by_column(
    data: pd.DataFrame,
    *,
    x_col: str,
    y_col: str = "value",
    weight_col: str = "events",
    frac: float = ATLAS_LOWESS_FRAC,
) -> tuple[np.ndarray, np.ndarray]:
    if data.empty or x_col not in data or y_col not in data or weight_col not in data:
        return np.array([]), np.array([])
    x = data[x_col].to_numpy(dtype=float)
    y = data[y_col].to_numpy(dtype=float)
    weights = data[weight_col].to_numpy(dtype=float)
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0.0)
    x = x[valid]
    y = y[valid]
    weights = weights[valid]
    if len(np.unique(x)) < 4 or len(x) < 6:
        return np.array([]), np.array([])
    order = np.argsort(x)
    x = x[order]
    y = y[order]
    weights = weights[order]
    n = len(x)
    neighbors = min(n, max(4, int(math.ceil(float(frac) * n))))
    x_grid = np.linspace(float(np.min(x)), float(np.max(x)), int(np.clip(n * 3, 55, 160)))
    y_grid = np.empty_like(x_grid)
    for idx, x0 in enumerate(x_grid):
        distances = np.abs(x - x0)
        bandwidth = float(np.partition(distances, neighbors - 1)[neighbors - 1])
        if bandwidth <= 0.0:
            positive = distances[distances > 0.0]
            bandwidth = float(np.min(positive)) if positive.size else 1.0
        local = np.clip(distances / bandwidth, 0.0, 1.0)
        tricube = (1.0 - local**3) ** 3
        local_weights = weights * tricube
        if np.count_nonzero(local_weights > 0.0) < 3:
            local_weights = weights
        active = local_weights > 0.0
        local_x = x[active]
        local_y = y[active]
        active_weights = local_weights[active]
        fallback = float(np.average(local_y, weights=active_weights))
        if local_y.size < 5 or float(np.ptp(local_x)) <= 1.0e-6:
            y_grid[idx] = fallback
            continue
        design = np.column_stack([np.ones_like(local_x), local_x - x0])
        root_weights = np.sqrt(active_weights)
        try:
            beta, *_ = np.linalg.lstsq(design * root_weights[:, None], local_y * root_weights, rcond=None)
            estimate = float(beta[0])
            local_lo = float(np.min(local_y))
            local_hi = float(np.max(local_y))
            tolerance = max(0.25, 0.25 * (local_hi - local_lo))
            if estimate < local_lo - tolerance or estimate > local_hi + tolerance:
                estimate = fallback
            y_grid[idx] = estimate
        except np.linalg.LinAlgError:
            y_grid[idx] = fallback
    return x_grid, y_grid


def plot_profile_map(
    ax: plt.Axes,
    *,
    regions: list,
    sections: list[tuple[str, tuple[float, float], tuple[float, float]]],
    metadata: pd.DataFrame,
    profile_id: str,
    stations: pd.DataFrame,
    events: pd.DataFrame,
    basemap_cache_dir: Path,
) -> None:
    la_basin = next(region for region in regions if region.name.lower() == "los angeles basin")
    to_web = Transformer.from_crs(WGS84, WEB_MERCATOR, always_xy=True)
    basin_web = shapely_transform(to_web.transform, la_basin.geometry_lonlat)
    records = metadata.set_index("profile_id")
    xs: list[float] = []
    ys: list[float] = []
    for polygon in iter_polygons(basin_web):
        x, y = polygon.exterior.xy
        xs.extend(x)
        ys.extend(y)
    for _, start_ll, end_ll in sections:
        line_x, line_y = to_web.transform([start_ll[0], end_ll[0]], [start_ll[1], end_ll[1]])
        xs.extend(line_x)
        ys.extend(line_y)
    if not stations.empty:
        sx, sy = to_web.transform(stations["sta_lon"].to_numpy(dtype=float), stations["sta_lat"].to_numpy(dtype=float))
        xs.extend(sx)
        ys.extend(sy)
    else:
        sx = sy = np.array([])
    if not events.empty:
        ex, ey = to_web.transform(events["event_lon"].to_numpy(dtype=float), events["event_lat"].to_numpy(dtype=float))
        xs.extend(ex)
        ys.extend(ey)
    else:
        ex = ey = np.array([])

    pad_x = max((max(xs) - min(xs)) * 0.10, 8000.0)
    pad_y = max((max(ys) - min(ys)) * 0.10, 8000.0)
    ax.set_xlim(min(xs) - pad_x, max(xs) + pad_x)
    ax.set_ylim(min(ys) - pad_y, max(ys) + pad_y)
    add_required_basemap(ax, source=DEFAULT_BASEMAP_SOURCE, cache_dir=basemap_cache_dir, zoom=DEFAULT_BASEMAP_ZOOM)
    for polygon in iter_polygons(basin_web):
        x, y = polygon.exterior.xy
        ax.fill(x, y, facecolor="#FFFFFF", alpha=0.18, edgecolor=COLORS["ink"], linewidth=0.9, zorder=4)
    for title, start_ll, end_ll in sections:
        current_id = title.split()[0]
        record = records.loc[current_id]
        color = COLORS["blue"] if record["family"] == "long_axis" else COLORS["gold"]
        line_x, line_y = to_web.transform([start_ll[0], end_ll[0]], [start_ll[1], end_ll[1]])
        is_current = current_id == profile_id
        ax.plot(line_x, line_y, color=color, linewidth=3.1 if is_current else 1.0, alpha=0.98 if is_current else 0.28, zorder=8 if is_current else 6)
        if is_current:
            ax.text(
                0.5 * (line_x[0] + line_x[1]),
                0.5 * (line_y[0] + line_y[1]),
                current_id,
                color="white",
                fontsize=11,
                fontweight="bold",
                ha="center",
                va="center",
                bbox={"facecolor": color, "edgecolor": "white", "boxstyle": "round,pad=0.20", "linewidth": 0.5, "alpha": 0.96},
                zorder=9,
            )
    if len(ex):
        ax.scatter(ex, ey, marker="*", s=22, color=COLORS["gold"], edgecolor=COLORS["ink"], linewidth=0.25, alpha=0.38, zorder=7)
    if len(sx):
        ax.scatter(sx, sy, s=14, color=COLORS["ink"], edgecolor="white", linewidth=0.3, alpha=0.75, zorder=8)
    format_projected_map_axis(ax)
    ax.set_title(f"{profile_id} map: profile line, stations, and events", fontsize=11.5, fontweight="bold", pad=6)
    ax.tick_params(labelsize=7.2)


def plot_residual_panel(
    ax: plt.Axes,
    frame: pd.DataFrame,
    *,
    panel: PanelSpec,
    y_limits: tuple[float, float],
    norm: TwoSlopeNorm,
    cmap,
    event_min: float,
    event_max: float,
    section_length_km: float,
) -> None:
    ax.grid(True, color=COLORS["grid"], linewidth=0.6, alpha=0.75)
    ax.axhline(0.0, color=COLORS["ink"], linewidth=0.8, alpha=0.60, zorder=1)
    ax.set_xlim(0.0, section_length_km)
    ax.set_ylim(*y_limits)
    ax.tick_params(labelsize=7.5)
    ax.set_ylabel("")
    ax.text(
        0.010,
        0.90,
        panel.label,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        fontweight="bold",
        color=COLORS["ink"],
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78, "pad": 1.4},
        zorder=6,
    )
    if frame.empty:
        ax.text(0.5, 0.5, "No stations", ha="center", va="center", transform=ax.transAxes, color=COLORS["muted"], fontsize=9)
        return
    yerr = np.vstack(
        [
            np.clip(frame["value"] - frame["q25"], 0.0, None),
            np.clip(frame["q75"] - frame["value"], 0.0, None),
        ]
    )
    ax.errorbar(
        frame["projected_km"],
        frame["value"],
        yerr=yerr,
        fmt="none",
        ecolor=COLORS["muted"],
        elinewidth=0.75,
        alpha=0.50,
        capsize=1.4,
        zorder=2,
    )
    ax.scatter(
        frame["projected_km"],
        frame["value"],
        c=frame["value"],
        cmap=cmap,
        norm=norm,
        s=event_marker_size(frame["events"], event_min, event_max, minimum=12, maximum=48),
        edgecolor=COLORS["ink"],
        linewidth=0.25,
        alpha=0.92,
        zorder=3,
    )
    lowess_x, lowess_y = weighted_lowess_by_column(frame, x_col="projected_km")
    if lowess_x.size:
        ax.plot(lowess_x, lowess_y, color=COLORS["ink"], linewidth=1.25, alpha=0.72, zorder=4)
    ax.text(
        0.985,
        0.90,
        f"{frame['station'].nunique():,} sta; {int(frame['events'].sum()):,} ev-wt",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=7.0,
        color=COLORS["muted"],
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.74, "pad": 1.2},
        zorder=5,
    )


def scatter_axis(
    ax: plt.Axes,
    frames: dict[str, pd.DataFrame],
    *,
    x_col: str,
    x_label: str,
    y_limits: tuple[float, float],
) -> None:
    ax.grid(True, color=COLORS["grid"], linewidth=0.6, alpha=0.75)
    ax.axhline(0.0, color=COLORS["ink"], linewidth=0.8, alpha=0.60, zorder=1)
    ax.set_ylim(*y_limits)
    all_x: list[np.ndarray] = []
    for band, frame in frames.items():
        if frame.empty or x_col not in frame:
            continue
        data = frame.dropna(subset=[x_col, "value", "events"])
        if data.empty:
            continue
        color = PASSBAND_COLORS.get(band, COLORS["blue"])
        ax.scatter(
            data[x_col],
            data["value"],
            s=event_marker_size(data["events"], float(data["events"].min()), float(data["events"].max()), minimum=12, maximum=42),
            color=color,
            edgecolor=COLORS["ink"],
            linewidth=0.25,
            alpha=0.36,
            label=band,
            zorder=3,
        )
        all_x.append(data[x_col].to_numpy(dtype=float))
        lowess_x, lowess_y = weighted_lowess_by_column(data, x_col=x_col)
        if lowess_x.size:
            ax.plot(lowess_x, lowess_y, color=color, linewidth=0.95, alpha=0.82, zorder=4)
    ax.set_xlabel(x_label, fontsize=8.4)
    ax.set_ylabel("Residual", fontsize=8.4)
    ax.tick_params(labelsize=7.3)
    if all_x:
        finite = np.concatenate([x[np.isfinite(x)] for x in all_x])
        if finite.size:
            lo = float(np.nanmin(finite))
            hi = float(np.nanmax(finite))
            span = hi - lo
            margin = 0.08 * span if span > 0 else 0.5
            ax.set_xlim(lo - margin, hi + margin)

def render_profile_page(
    *,
    pdf: PdfPages,
    page: MetricPage,
    profile_id: str,
    sections: list[tuple[str, tuple[float, float], tuple[float, float]]],
    metadata: pd.DataFrame,
    regions: list,
    section_grids: dict[str, dict[str, object]],
    projected: dict[tuple[str, str], pd.DataFrame],
    plotted_events: pd.DataFrame,
    y_limits: tuple[float, float],
    norm: TwoSlopeNorm,
    vs_gradient_norm: TwoSlopeNorm,
    basemap_cache_dir: Path,
    out_png: Path,
    model_label: str,
    model_property: str,
) -> None:
    cmap = plt.get_cmap(page.cmap)
    section_grid = section_grids[profile_id]
    row = metadata.set_index("profile_id").loc[profile_id]
    property_label = PROPERTY_LABELS[model_property]
    absolute_variant, gradient_variant = property_variants(model_property)
    band_frames = {panel.label: projected[(profile_id, panel.label)] for panel in page.panels}
    station_frame = (
        pd.concat([frame[["station", "sta_lon", "sta_lat"]] for frame in band_frames.values() if not frame.empty], ignore_index=True)
        .drop_duplicates("station")
        if any(not frame.empty for frame in band_frames.values())
        else pd.DataFrame(columns=["station", "sta_lon", "sta_lat"])
    )
    station_ids = set(station_frame["station"].astype(str))
    events = plotted_events.loc[plotted_events["station"].astype(str).isin(station_ids)].drop_duplicates("event_id")
    events_values = np.concatenate([frame["events"].to_numpy(dtype=float) for frame in band_frames.values() if not frame.empty])
    event_min = float(np.nanmin(events_values)) if events_values.size else 1.0
    event_max = float(np.nanmax(events_values)) if events_values.size else event_min

    fig = plt.figure(figsize=(17.0, 12.2), constrained_layout=False)
    grid = fig.add_gridspec(
        nrows=7,
        ncols=7,
        height_ratios=[0.58, 1.0, 1.0, 1.0, 1.0, 1.02, 1.02],
        width_ratios=[1.18, 1.18, 1.18, 0.060, 0.10, 1.0, 1.0],
        hspace=0.48,
        wspace=0.28,
    )
    title = (
        f"{model_label} PGA profile {profile_id}: {row.family.replace('_', ' ')} "
        f"({row.bearing_deg:.1f} deg; LA Basin crossing {row.la_basin_intersection_km:.1f} km)"
    )
    fig.suptitle(title, fontsize=17.0, fontweight="bold", color=COLORS["ink"], y=0.985)
    fig.text(
        0.055,
        0.952,
        f"Residual plots are station medians by passband; cross sections show absolute {property_label} "
        f"and signed vertical {property_label} gradient. "
        "Right-column lines show event-weighted LOWESS residual trends for each passband.",
        ha="left",
        va="top",
        fontsize=9.5,
        color=COLORS["muted"],
    )

    residual_axes = [fig.add_subplot(grid[i, :3]) for i in range(1, 5)]
    for ax, panel in zip(residual_axes, page.panels):
        plot_residual_panel(
            ax,
            band_frames[panel.label],
            panel=panel,
            y_limits=y_limits,
            norm=norm,
            cmap=cmap,
            event_min=event_min,
            event_max=event_max,
            section_length_km=float(section_grid["length_km"]),
        )
    for ax in residual_axes[:-1]:
        ax.tick_params(labelbottom=False)
    residual_axes[-1].set_xlabel("Distance along profile (km)", fontsize=8.8)
    fig.text(
        0.026,
        0.596,
        "Station median PGA residual, log2(obs/syn)",
        rotation=90,
        ha="center",
        va="center",
        fontsize=9.0,
        fontweight="bold",
        color=COLORS["ink"],
    )

    map_ax = fig.add_subplot(grid[1:3, 5:])
    plot_profile_map(
        map_ax,
        regions=regions,
        sections=sections,
        metadata=metadata,
        profile_id=profile_id,
        stations=station_frame,
        events=events,
        basemap_cache_dir=basemap_cache_dir,
    )

    scatter_z1 = fig.add_subplot(grid[3, 5:])
    scatter_z25 = fig.add_subplot(grid[4, 5:])
    scatter_grad_depth = fig.add_subplot(grid[5, 5:])
    scatter_grad_strength = fig.add_subplot(grid[6, 5:])
    scatter_axis(scatter_z1, band_frames, x_col="z1_depth_km", x_label="z(Vs=1.0) depth (km)", y_limits=y_limits)
    scatter_axis(scatter_z25, band_frames, x_col="z2p5_depth_km", x_label="z(Vs=2.5) depth (km)", y_limits=y_limits)
    scatter_axis(
        scatter_grad_depth,
        band_frames,
        x_col="max_abs_model_gradient_depth_km",
        x_label=f"Depth of maximum |vertical {property_label} gradient| (km)",
        y_limits=y_limits,
    )
    scatter_axis(
        scatter_grad_strength,
        band_frames,
        x_col="max_abs_model_gradient_strength",
        x_label=f"Maximum |vertical {property_label} gradient| ((km/s)/km)",
        y_limits=y_limits,
    )
    handles = [
        Line2D([0], [0], marker="o", linestyle="none", markerfacecolor=color, markeredgecolor=COLORS["ink"], markersize=6, label=band)
        for band, color in PASSBAND_COLORS.items()
    ]
    scatter_grad_strength.legend(handles=handles, loc="upper right", fontsize=7.5, frameon=True)

    vs_ax = fig.add_subplot(grid[5, :3])
    grad_ax = fig.add_subplot(grid[6, :3])
    vs_image = plot_section_grid(vs_ax, section_grid, variant=absolute_variant, vs_gradient_norm=None)
    grad_image = plot_section_grid(grad_ax, section_grid, variant=gradient_variant, vs_gradient_norm=vs_gradient_norm)
    for ax, label in ((vs_ax, f"Absolute {property_label}"), (grad_ax, f"Vertical {property_label} gradient")):
        ax.invert_yaxis()
        ax.set_xlim(0.0, float(section_grid["length_km"]))
        ax.set_ylim(SECTION_MAX_DEPTH_KM, 0.0)
        ax.grid(color="white", linewidth=0.45, alpha=0.55)
        ax.set_ylabel("Depth (km)", fontsize=8.8)
        ax.tick_params(labelsize=7.5)
        ax.text(
            0.012,
            0.08,
            label,
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=9.0,
            fontweight="bold",
            color=COLORS["ink"],
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.76, "pad": 2.0},
        )
    grad_ax.set_xlabel("Distance along profile (km)", fontsize=8.8)

    vs_cax = fig.add_subplot(grid[5, 3])
    grad_cax = fig.add_subplot(grid[6, 3])
    vs_cbar = fig.colorbar(vs_image, cax=vs_cax)
    grad_cbar = fig.colorbar(grad_image, cax=grad_cax, extend="both")
    vs_cbar.set_label(f"{property_label} (km/s)", fontsize=8.2, labelpad=6)
    grad_cbar.set_label(f"{property_label} gradient ((km/s)/km)", fontsize=8.2, labelpad=6)
    vs_cbar.ax.tick_params(labelsize=7.0)
    grad_cbar.ax.tick_params(labelsize=7.0)

    residual_cax = fig.add_axes([0.055, 0.900, 0.175, 0.012])
    residual_cbar = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=residual_cax, orientation="horizontal")
    residual_cbar.set_label("Station median PGA residual, log2(obs/syn)", fontsize=8.0)
    residual_cbar.ax.tick_params(labelsize=6.8)

    fig.text(
        0.055,
        0.008,
        (
            f"Stations are included within {SPLIT_STATION_CORRIDOR_KM:g} km of the profile. "
            f"Residual-profile LOWESS span is {ATLAS_LOWESS_FRAC:.2f}; station point area scales with event support."
        ),
        fontsize=8.2,
        color=COLORS["muted"],
        ha="left",
        va="bottom",
    )
    fig.subplots_adjust(left=0.055, right=0.975, top=0.925, bottom=0.078)
    fig.savefig(out_png, dpi=190)
    pdf.savefig(fig)
    plt.close(fig)


def render_split_pga(args: argparse.Namespace) -> list[Path]:
    set_plot_theme()
    output_dir = args.output_dir.expanduser().resolve()
    suffix = PROPERTY_PDF_SUFFIX[args.model_property]
    property_label = PROPERTY_LABELS[args.model_property]
    figures_dir = output_dir / "figures" / f"la_basin_metric_profile_split_pga{suffix}"
    tables_dir = output_dir / "tables"
    report_dir = output_dir / "report"
    basemap_cache_dir = output_dir / "basemap_cache"
    for directory in (figures_dir, tables_dir, report_dir, basemap_cache_dir):
        directory.mkdir(parents=True, exist_ok=True)

    regions = load_regions(DEFAULT_REGIONS)
    long_sections, perp_sections, metadata = build_profile_families(regions)
    sections = [*long_sections, *perp_sections]
    metadata_path = tables_dir / f"la_basin_metric_profile_split_pga{suffix}_sections.csv"
    metadata.to_csv(metadata_path, index=False)

    raw = load_metric_rows(args.metrics.expanduser(), model=args.model)
    raw = raw.loc[raw["component"].astype(str).str.upper().isin(["R", "T"])].copy()
    pairs = collapse_components(raw)
    pairs_path = tables_dir / f"la_basin_metric_profile_split_pga{suffix}_pairs.parquet"
    pairs.to_parquet(pairs_path, index=False)

    sampler = ModelSampler(args.model_h5.expanduser(), node_stride=args.model_node_stride)
    section_grids = sample_section_grids(sampler, sections)
    add_vertical_property_gradient_cells(section_grids, args.model_property)
    vs_gradient_norm = section_property_gradient_norm(section_grids, args.model_property)

    page = pga_page(args.model_label)
    transformer = Transformer.from_crs(WGS84, CVM_UTM, always_xy=True)
    panel_rows = {panel.label: filter_panel_rows(pairs, panel) for panel in page.panels}
    station_summaries = {panel.label: station_values(panel_rows[panel.label], panel.value_column) for panel in page.panels}
    projected: dict[tuple[str, str], pd.DataFrame] = {}
    for title, start_ll, end_ll in sections:
        profile_id = title.split()[0]
        line = section_line_utm(start_ll, end_ll, transformer)
        for panel in page.panels:
            frame = station_projection(line, station_summaries[panel.label], transformer, station_corridor_km=SPLIT_STATION_CORRIDOR_KM)
            frame = add_model_depth_columns(frame, section_grids[profile_id], gradient_property=args.model_property)
            projected[(profile_id, panel.label)] = frame

    norm, y_limits = page_value_scale(projected, page)
    plotted_events = pd.concat(
        [frame[["event_id", "station", "event_lon", "event_lat"]] for frame in panel_rows.values() if not frame.empty],
        ignore_index=True,
    ).dropna(subset=["event_lon", "event_lat"])

    candidate_map_path = figures_dir / f"la_basin_metric_profile_split_pga{suffix}_candidate_lines_map.png"
    render_candidate_map(regions, sections, metadata, candidate_map_path, basemap_cache_dir=basemap_cache_dir)

    pdf_path = report_dir / f"la_basin_metric_profile_split_pga{suffix}.pdf"
    rendered_pages: list[Path] = []
    with PdfPages(pdf_path) as pdf:
        add_png_page_to_pdf(pdf, candidate_map_path)
        for profile_id in PROFILE_ORDER:
            out_png = figures_dir / f"la_basin_metric_profile_split_pga{suffix}_{profile_id}.png"
            render_profile_page(
                pdf=pdf,
                page=page,
                profile_id=profile_id,
                sections=sections,
                metadata=metadata,
                regions=regions,
                section_grids=section_grids,
                projected=projected,
                plotted_events=plotted_events,
                y_limits=y_limits,
                norm=norm,
                vs_gradient_norm=vs_gradient_norm,
                basemap_cache_dir=basemap_cache_dir,
                out_png=out_png,
                model_label=args.model_label,
                model_property=args.model_property,
            )
            rendered_pages.append(out_png)

    projected_rows = []
    for (profile_id, band), frame in projected.items():
        if frame.empty:
            continue
        out = frame.copy()
        out.insert(0, "profile_id", profile_id)
        out.insert(1, "band", band)
        projected_rows.append(out)
    projected_path = tables_dir / f"la_basin_metric_profile_split_pga{suffix}_projected_stations.csv"
    if projected_rows:
        pd.concat(projected_rows, ignore_index=True).to_csv(projected_path, index=False)
    else:
        pd.DataFrame().to_csv(projected_path, index=False)

    manifest_path = report_dir / f"la_basin_metric_profile_split_pga{suffix}_manifest.json"
    manifest = {
        "model": args.model,
        "model_label": args.model_label,
        "model_property": args.model_property,
        "component_filter": ["R", "T"],
        "model_property_label": property_label,
        "metric": "PGA",
        "inputs": {
            "metrics": str(args.metrics),
            "model_h5": str(args.model_h5),
            "station_corridor_km": SPLIT_STATION_CORRIDOR_KM,
            "lowess_frac": ATLAS_LOWESS_FRAC,
            "vs_gradient_window_half_km": VS_GRADIENT_WINDOW_HALF_KM,
        },
        "outputs": {
            "pdf": str(pdf_path),
            "candidate_map": str(candidate_map_path),
            "profile_pages": [str(path) for path in rendered_pages],
            "projected_stations": str(projected_path),
            "pairs": str(pairs_path),
            "sections": str(metadata_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    pd.DataFrame(
        [
            {"kind": "candidate_map", "path": str(candidate_map_path)},
            *({"kind": "profile_page", "path": str(path)} for path in rendered_pages),
            {"kind": "pdf", "path": str(pdf_path)},
            {"kind": "manifest", "path": str(manifest_path)},
            {"kind": "projected_stations", "path": str(projected_path)},
        ]
    ).to_csv(report_dir / f"la_basin_metric_profile_split_pga{suffix}_manifest.csv", index=False)
    return [candidate_map_path, *rendered_pages, pdf_path, manifest_path, projected_path]


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    for path in render_split_pga(args):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
