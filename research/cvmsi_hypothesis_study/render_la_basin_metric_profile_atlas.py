#!/usr/bin/env python3
"""Render mapped LA Basin profile cross-section atlases for selected metrics."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import math
from pathlib import Path
import textwrap
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
from matplotlib.cm import ScalarMappable
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.stats import rankdata
from shapely.geometry import LineString, Point
from shapely.ops import transform as shapely_transform

from cvmsi_hypothesis_study import (
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
from render_la_basin_axis_profile_sections import (
    BANDS,
    LOWESS_ALPHA,
    STATION_CORRIDOR_KM,
    build_profile_families,
    render_candidate_map,
)


PROFILE_ORDER = [f"L{i}" for i in range(1, 6)] + [f"P{i}" for i in range(1, 6)]
DEPTHS_KM = np.linspace(0.0, 15.0, 76)
SECTION_SAMPLES = 150
ATLAS_LOWESS_FRAC = 0.20
VS_GRADIENT_SCALE_QUANTILE = 0.99
VS_GRADIENT_WINDOW_HALF_KM = 0.5
PSA_PERIOD_BANDS = {
    1.0: "1-2 sec",
    2.0: "2-3 sec",
    3.0: "3-5 sec",
    4.0: "3-5 sec",
    5.0: "3-5 sec",
}
PASSBAND_LABELS = [band for band, _ in BANDS]


@dataclass(frozen=True)
class PanelSpec:
    label: str
    metric: str
    band: str
    value_column: str
    period_s: float | None = None
    value_label: str = "Station median residual"


@dataclass(frozen=True)
class MetricPage:
    slug: str
    title: str
    subtitle: str
    panels: tuple[PanelSpec, ...]
    cmap: str
    y_label: str
    colorbar_label: str
    value_mode: str
    y_limits: tuple[float, float] | None = None


@dataclass(frozen=True)
class AtlasVariant:
    mode: str
    output_subdir: str
    filename_prefix: str
    pdf_name: str
    manifest_name: str
    title_suffix: str
    section_colorbar_label: str
    section_note: str


ATLAS_VARIANTS = {
    "vs": AtlasVariant(
        mode="vs",
        output_subdir="la_basin_metric_profile_atlas",
        filename_prefix="fig_06_metric_profile_atlas",
        pdf_name="la_basin_metric_profile_atlas.pdf",
        manifest_name="la_basin_metric_profile_atlas_manifest.csv",
        title_suffix="",
        section_colorbar_label="Vs (km/s)",
        section_note="Left cross sections show CVM-SI absolute Vs in km/s.",
    ),
    "vs-gradient": AtlasVariant(
        mode="vs-gradient",
        output_subdir="la_basin_metric_profile_atlas_vs_gradient",
        filename_prefix="fig_06_metric_profile_atlas_vs_gradient",
        pdf_name="la_basin_metric_profile_atlas_vs_gradient.pdf",
        manifest_name="la_basin_metric_profile_atlas_vs_gradient_manifest.csv",
        title_suffix="vertical Vs-gradient cross sections",
        section_colorbar_label="Vertical Vs gradient ((km/s)/km)",
        section_note=(
            "Left cross sections show signed vertical gradient of CVM-SI Vs from overlapping "
            "\u00b10.5 km vertical windows centered on each plotted depth cell; positive values mean Vs increases downward."
        ),
    ),
}


def section_line_utm(start_ll: tuple[float, float], end_ll: tuple[float, float], transformer: Transformer) -> LineString:
    sx, sy = transformer.transform(*start_ll)
    ex, ey = transformer.transform(*end_ll)
    return LineString([(float(sx), float(sy)), (float(ex), float(ey))])


def load_metric_rows(metrics_path: Path, model: str = DEFAULT_MODEL) -> pd.DataFrame:
    columns = [
        "event_id",
        "station",
        "component",
        "model",
        "metric",
        "band",
        "period_s",
        "value",
        "log2_residual",
        "event_lat",
        "event_lon",
        "sta_lat",
        "sta_lon",
    ]
    df = pd.read_parquet(metrics_path, columns=columns)
    metric_names = {"PGA", "PGV", "arias_duration", "original_cc", "PSA"}
    df = df.loc[
        df["model"].astype(str).eq(model)
        & df["metric"].astype(str).isin(metric_names)
        & df["band"].astype(str).isin([*PASSBAND_LABELS, "1-5 sec", "all"])
    ].copy()
    for column in ["period_s", "value", "log2_residual", "event_lat", "event_lon", "sta_lat", "sta_lon"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    for column in ["event_id", "station", "component", "metric", "band"]:
        df[column] = df[column].astype(str)
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["event_id", "station", "metric", "band", "event_lat", "event_lon", "sta_lat", "sta_lon"])
    return df


def collapse_components(df: pd.DataFrame) -> pd.DataFrame:
    keys = ["event_id", "station", "metric", "band", "period_s"]
    out = (
        df.groupby(keys, as_index=False, dropna=False)
        .agg(
            value=("value", "median"),
            log2_residual=("log2_residual", "median"),
            event_lat=("event_lat", "median"),
            event_lon=("event_lon", "median"),
            sta_lat=("sta_lat", "median"),
            sta_lon=("sta_lon", "median"),
            components=("component", lambda values: ",".join(sorted(set(str(value) for value in values.dropna())))),
            component_count=("component", "nunique"),
        )
        .replace([np.inf, -np.inf], np.nan)
    )
    return out


def page_specs(model_label: str = "CVM-SI") -> list[MetricPage]:
    residual_pages = [
        ("pga", "PGA", "PGA", "Station median PGA residual, log2(obs/syn)"),
        ("pgv", "PGV", "PGV", "Station median PGV residual, log2(obs/syn)"),
        (
            "arias_duration",
            "Arias Duration",
            "arias_duration",
            "Station median Arias-duration residual, log2(obs/syn)",
        ),
    ]
    pages: list[MetricPage] = []
    for slug, title, metric, y_label in residual_pages:
        panels = tuple(
            PanelSpec(label=band, metric=metric, band=band, value_column="log2_residual", value_label=y_label)
            for band in PASSBAND_LABELS
        )
        pages.append(
            MetricPage(
                slug=slug,
                title=f"LA Basin {model_label} profile atlas: {title}",
                subtitle=(
                    "Columns show the 1-2, 2-3, and 3-5 s passbands. Points are station medians, "
                    "vertical bars are the station 25th-75th percentile range across events, and point area scales with event count."
                ),
                panels=panels,
                cmap="RdBu_r",
                y_label=y_label,
                colorbar_label=y_label,
                value_mode="residual",
            )
        )
    cc_panels = tuple(
        PanelSpec(
            label=band,
            metric="original_cc",
            band=band,
            value_column="value",
            value_label="Station median original CC",
        )
        for band in PASSBAND_LABELS
    )
    pages.append(
        MetricPage(
            slug="original_cc",
            title=f"LA Basin {model_label} profile atlas: original cross correlation",
            subtitle=(
                "Columns show raw original cross-correlation values, not obs/syn residuals. "
                "Positive values indicate waveform similarity without timing correction; negative values indicate anti-correlation."
            ),
            panels=cc_panels,
            cmap="RdBu_r",
            y_label="Station median original CC",
            colorbar_label="Station median original CC",
            value_mode="raw_cc",
            y_limits=(-1.0, 1.0),
        )
    )
    psa_panels = tuple(
        PanelSpec(
            label=f"PSA {period:g} s\n{PSA_PERIOD_BANDS[period]}",
            metric="PSA",
            band=PSA_PERIOD_BANDS[period],
            period_s=period,
            value_column="log2_residual",
            value_label="Station median PSA residual, log2(obs/syn)",
        )
        for period in (1.0, 2.0, 3.0, 4.0, 5.0)
    )
    pages.append(
        MetricPage(
            slug="psa_periods",
            title=f"LA Basin {model_label} profile atlas: PSA periods",
            subtitle=(
                "Columns show PSA residuals for periods 1, 2, 3, 4, and 5 s. Each period uses the passband with robust support "
                "(1 s from 1-2 s, 2 s from 2-3 s, and 3-5 s from 3-5 s)."
            ),
            panels=psa_panels,
            cmap="RdBu_r",
            y_label="Station median PSA residual, log2(obs/syn)",
            colorbar_label="Station median PSA residual, log2(obs/syn)",
            value_mode="residual",
        )
    )
    return pages


def filter_panel_rows(pairs: pd.DataFrame, panel: PanelSpec) -> pd.DataFrame:
    data = pairs.loc[pairs["metric"].eq(panel.metric) & pairs["band"].eq(panel.band)].copy()
    if panel.period_s is None:
        data = data.loc[data["period_s"].isna()]
    else:
        data = data.loc[np.isclose(data["period_s"].to_numpy(dtype=float), panel.period_s, atol=1.0e-6, equal_nan=False)]
    data = data.dropna(subset=[panel.value_column, "event_id", "station", "sta_lon", "sta_lat"])
    return data


def station_values(data: pd.DataFrame, value_column: str) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame(columns=["station", "sta_lon", "sta_lat", "value", "q25", "q75", "events", "records"])
    return (
        data.groupby("station", as_index=False)
        .agg(
            sta_lon=("sta_lon", "median"),
            sta_lat=("sta_lat", "median"),
            value=(value_column, "median"),
            q25=(value_column, lambda value: float(value.quantile(0.25))),
            q75=(value_column, lambda value: float(value.quantile(0.75))),
            events=("event_id", "nunique"),
            records=(value_column, "size"),
        )
        .replace([np.inf, -np.inf], np.nan)
        .dropna(subset=["sta_lon", "sta_lat", "value"])
    )


def station_projection(
    section_line: LineString,
    residuals: pd.DataFrame,
    transformer: Transformer,
    *,
    station_corridor_km: float = STATION_CORRIDOR_KM,
) -> pd.DataFrame:
    if residuals.empty:
        return pd.DataFrame(columns=[*residuals.columns, "projected_km", "offset_km"])
    station_xy = np.array(
        transformer.transform(
            residuals["sta_lon"].to_numpy(dtype=float),
            residuals["sta_lat"].to_numpy(dtype=float),
        )
    ).T
    rows: list[dict[str, object]] = []
    for station_row, xy in zip(residuals.itertuples(index=False), station_xy):
        point = Point(float(xy[0]), float(xy[1]))
        offset_km = point.distance(section_line) / 1000.0
        if offset_km > station_corridor_km:
            continue
        record = station_row._asdict()
        record["projected_km"] = section_line.project(point) / 1000.0
        record["offset_km"] = offset_km
        rows.append(record)
    if not rows:
        return pd.DataFrame(columns=[*residuals.columns, "projected_km", "offset_km"])
    return pd.DataFrame(rows).sort_values("projected_km")


def sample_section_grids(
    sampler: ModelSampler,
    sections: Iterable[tuple[str, tuple[float, float], tuple[float, float]]],
) -> dict[str, dict[str, object]]:
    transformer = Transformer.from_crs(WGS84, CVM_UTM, always_xy=True)
    grids: dict[str, dict[str, object]] = {}
    for title, start_ll, end_ll in sections:
        profile_id = title.split()[0]
        sx, sy = transformer.transform(*start_ll)
        ex, ey = transformer.transform(*end_ll)
        length_km = math.hypot(ex - sx, ey - sy) / 1000.0
        distances_km = np.linspace(0.0, length_km, SECTION_SAMPLES)
        frac = distances_km / max(length_km, 1.0e-9)
        xs = sx + frac * (ex - sx)
        ys = sy + frac * (ey - sy)
        grid_xyz = np.column_stack(
            [
                np.repeat(xs, len(DEPTHS_KM)),
                np.repeat(ys, len(DEPTHS_KM)),
                -np.tile(DEPTHS_KM * 1000.0, len(xs)),
            ]
        )
        sampled = sampler.sample_xyz(grid_xyz)
        grids[profile_id] = {
            "title": title,
            "start_ll": start_ll,
            "end_ll": end_ll,
            "line": LineString([(sx, sy), (ex, ey)]),
            "distances_km": distances_km,
            "depths_km": DEPTHS_KM,
            "length_km": length_km,
        }
        for field in ("vp", "vs", "rho"):
            if field not in sampled:
                continue
            values = sampled[field].to_numpy(dtype=float).reshape(len(xs), len(DEPTHS_KM)).T
            if field in {"vp", "vs"}:
                values = values / 1000.0
            grids[profile_id][field] = values
    return grids


def add_vertical_property_gradient_cells(section_grids: dict[str, dict[str, object]], property_name: str = "vs") -> None:
    gradient_key = f"vertical_{property_name}_gradient_cell"
    for section_grid in section_grids.values():
        values = np.asarray(section_grid[property_name], dtype=float)
        depths_km = np.asarray(section_grid["depths_km"], dtype=float)
        cell_values = 0.5 * (values[:, :-1] + values[:, 1:])
        cell_depths_km = 0.5 * (depths_km[:-1] + depths_km[1:])
        gradients = np.full((len(cell_depths_km), cell_values.shape[1]), np.nan, dtype=float)
        for index, center_depth_km in enumerate(cell_depths_km):
            window = np.abs(depths_km - center_depth_km) <= VS_GRADIENT_WINDOW_HALF_KM
            if np.count_nonzero(window) < 2:
                continue
            z = depths_km[window].astype(float)
            z_anom = z - float(np.nanmean(z))
            denom = float(np.sum(z_anom**2))
            if denom <= 0.0:
                continue
            y = cell_values[window, :]
            y_anom = y - np.nanmean(y, axis=0, keepdims=True)
            gradients[index, :] = np.nansum(z_anom[:, None] * y_anom, axis=0) / denom
        section_grid[gradient_key] = gradients


def add_vertical_vs_gradient_cells(section_grids: dict[str, dict[str, object]]) -> None:
    add_vertical_property_gradient_cells(section_grids, "vs")


def section_property_gradient_norm(section_grids: dict[str, dict[str, object]], property_name: str = "vs") -> TwoSlopeNorm:
    gradient_key = f"vertical_{property_name}_gradient_cell"
    values = [
        np.asarray(section_grid[gradient_key], dtype=float).ravel()
        for section_grid in section_grids.values()
        if gradient_key in section_grid
    ]
    finite = np.concatenate([value[np.isfinite(value)] for value in values]) if values else np.array([])
    if finite.size:
        span = float(np.nanquantile(np.abs(finite), VS_GRADIENT_SCALE_QUANTILE))
        span = max(span * 1.04, 0.10)
    else:
        span = 1.0
    return TwoSlopeNorm(vmin=-span, vcenter=0.0, vmax=span)


def section_vs_gradient_norm(section_grids: dict[str, dict[str, object]]) -> TwoSlopeNorm:
    return section_property_gradient_norm(section_grids, "vs")


def plot_section_grid(
    ax: plt.Axes,
    section_grid: dict[str, object],
    *,
    variant: AtlasVariant,
    vs_gradient_norm: TwoSlopeNorm | None,
) -> object:
    distances_km = np.asarray(section_grid["distances_km"], dtype=float)
    depths_km = np.asarray(section_grid["depths_km"], dtype=float)
    if variant.mode.endswith("-gradient"):
        property_name = variant.mode.removesuffix("-gradient")
        if vs_gradient_norm is None:
            raise ValueError("vs_gradient_norm is required for gradient atlas variants")
        return ax.pcolormesh(
            distances_km,
            depths_km,
            np.asarray(section_grid[f"vertical_{property_name}_gradient_cell"], dtype=float),
            cmap="RdBu_r",
            norm=vs_gradient_norm,
            shading="flat",
            rasterized=True,
        )
    property_name = variant.mode
    if property_name == "vp":
        levels = np.linspace(1.5, 7.5, 25)
    else:
        levels = np.linspace(0.5, 4.5, 21)
    return ax.contourf(
        distances_km,
        depths_km,
        np.asarray(section_grid[property_name], dtype=float),
        levels=levels,
        cmap="viridis",
        extend="both",
    )


def weighted_lowess(data: pd.DataFrame, *, frac: float = ATLAS_LOWESS_FRAC) -> tuple[np.ndarray, np.ndarray]:
    if data.empty:
        return np.array([]), np.array([])
    x = data["projected_km"].to_numpy(dtype=float)
    y = data["value"].to_numpy(dtype=float)
    weights = data["events"].to_numpy(dtype=float)
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
        local_y = y[active]
        local_x = x[active]
        active_weights = local_weights[active]
        fallback = float(np.average(local_y, weights=active_weights))
        if local_y.size < 5 or float(np.ptp(local_x)) <= 1.0e-6:
            y_grid[idx] = fallback
            continue
        design = np.column_stack([np.ones_like(x), x - x0])
        root_weights = np.sqrt(local_weights)
        try:
            beta, *_ = np.linalg.lstsq(design * root_weights[:, None], y * root_weights, rcond=None)
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


def event_marker_size(events: object, event_min: float, event_max: float, *, minimum: float = 8.0, maximum: float = 38.0) -> np.ndarray:
    values = np.asarray(events, dtype=float)
    if not np.isfinite(values).any() or event_max <= event_min:
        return np.full(values.shape, 0.5 * (minimum + maximum))
    scaled = np.clip((values - event_min) / (event_max - event_min), 0.0, 1.0)
    return minimum + (maximum - minimum) * np.sqrt(scaled)


def page_value_scale(projected: dict[tuple[str, str], pd.DataFrame], page: MetricPage) -> tuple[object, tuple[float, float]]:
    values: list[np.ndarray] = []
    for frame in projected.values():
        if frame.empty:
            continue
        values.extend(
            [
                frame["value"].to_numpy(dtype=float),
                frame["q25"].to_numpy(dtype=float),
                frame["q75"].to_numpy(dtype=float),
            ]
        )
    finite = np.concatenate([array[np.isfinite(array)] for array in values]) if values else np.array([])
    if page.value_mode == "raw_cc":
        return TwoSlopeNorm(vmin=-1.0, vcenter=0.0, vmax=1.0), (-1.0, 1.0)
    if finite.size:
        lo = float(np.nanquantile(finite, 0.01))
        hi = float(np.nanquantile(finite, 0.99))
        span = max(abs(lo), abs(hi), 1.0)
        span = min(max(span * 1.08, 1.4), 4.8)
    else:
        span = 1.8
    return TwoSlopeNorm(vmin=-span, vcenter=0.0, vmax=span), (-span, span)


def plot_page_map(
    ax: plt.Axes,
    *,
    regions: list,
    sections: list[tuple[str, tuple[float, float], tuple[float, float]]],
    metadata: pd.DataFrame,
    stations: pd.DataFrame,
    events: pd.DataFrame,
    basemap_cache_dir: Path,
) -> None:
    la_basin = next(region for region in regions if region.name.lower() == "los angeles basin")
    to_web = Transformer.from_crs(WGS84, WEB_MERCATOR, always_xy=True)
    basin_web = shapely_transform(to_web.transform, la_basin.geometry_lonlat)
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
    if not stations.empty:
        station_x, station_y = to_web.transform(stations["sta_lon"].to_numpy(dtype=float), stations["sta_lat"].to_numpy(dtype=float))
        xs.extend(station_x)
        ys.extend(station_y)
    else:
        station_x = station_y = np.array([])
    if not events.empty:
        event_x, event_y = to_web.transform(events["event_lon"].to_numpy(dtype=float), events["event_lat"].to_numpy(dtype=float))
        xs.extend(event_x)
        ys.extend(event_y)
    else:
        event_x = event_y = np.array([])
    pad_x = max((max(xs) - min(xs)) * 0.12, 10000.0)
    pad_y = max((max(ys) - min(ys)) * 0.12, 10000.0)
    ax.set_xlim(min(xs) - pad_x, max(xs) + pad_x)
    ax.set_ylim(min(ys) - pad_y, max(ys) + pad_y)
    add_required_basemap(ax, source=DEFAULT_BASEMAP_SOURCE, cache_dir=basemap_cache_dir, zoom=DEFAULT_BASEMAP_ZOOM)
    for polygon in iter_polygons(basin_web):
        x, y = polygon.exterior.xy
        ax.fill(x, y, facecolor="#FFFFFF", alpha=0.18, edgecolor=COLORS["ink"], linewidth=1.0, zorder=4)
    if len(event_x):
        ax.scatter(event_x, event_y, marker="*", s=18, color=COLORS["gold"], edgecolor=COLORS["ink"], linewidth=0.25, alpha=0.42, zorder=5)
    if len(station_x):
        ax.scatter(station_x, station_y, s=8, color=COLORS["ink"], edgecolor="white", linewidth=0.2, alpha=0.56, zorder=6)
    for title, start_ll, end_ll in sections:
        profile_id = title.split()[0]
        record = line_records.loc[profile_id]
        color = COLORS["blue"] if record["family"] == "long_axis" else COLORS["gold"]
        line_x, line_y = to_web.transform([start_ll[0], end_ll[0]], [start_ll[1], end_ll[1]])
        ax.plot(line_x, line_y, color=color, linewidth=2.0, alpha=0.92, zorder=7)
        label_x = 0.54 * line_x[0] + 0.46 * line_x[1]
        label_y = 0.54 * line_y[0] + 0.46 * line_y[1]
        ax.text(
            label_x,
            label_y,
            profile_id,
            color="white",
            fontsize=8.5,
            fontweight="bold",
            ha="center",
            va="center",
            bbox={"facecolor": color, "edgecolor": "white", "boxstyle": "round,pad=0.16", "linewidth": 0.45, "alpha": 0.95},
            zorder=8,
        )
    format_projected_map_axis(ax)
    ax.set_title(
        f"Map view: {len(stations):,} plotted stations and {len(events):,} contributing events",
        fontsize=12.5,
        fontweight="bold",
        pad=6,
    )
    ax.tick_params(labelsize=8.5)
    handles = [
        Line2D([0], [0], color=COLORS["blue"], linewidth=2.2, label="Long-axis profiles"),
        Line2D([0], [0], color=COLORS["gold"], linewidth=2.2, label="Perpendicular profiles"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=COLORS["ink"], markeredgecolor="white", markersize=5, label="Plotted stations"),
        Line2D([0], [0], marker="*", color="none", markerfacecolor=COLORS["gold"], markeredgecolor=COLORS["ink"], markersize=7, label="Events"),
    ]
    ax.legend(handles=handles, loc="upper right", ncol=2, frameon=True, fontsize=8.5)


def render_metric_page(
    *,
    page: MetricPage,
    variant: AtlasVariant,
    pairs: pd.DataFrame,
    regions: list,
    sections: list[tuple[str, tuple[float, float], tuple[float, float]]],
    metadata: pd.DataFrame,
    section_grids: dict[str, dict[str, object]],
    vs_gradient_norm: TwoSlopeNorm | None,
    figures_dir: Path,
    basemap_cache_dir: Path,
    pdf: PdfPages,
    model_label: str = "CVM-SI",
) -> Path:
    transformer = Transformer.from_crs(WGS84, CVM_UTM, always_xy=True)
    panel_rows = {panel.label: filter_panel_rows(pairs, panel) for panel in page.panels}
    station_summaries = {panel.label: station_values(panel_rows[panel.label], panel.value_column) for panel in page.panels}
    projected: dict[tuple[str, str], pd.DataFrame] = {}
    plotted_station_frames: list[pd.DataFrame] = []
    for title, start_ll, end_ll in sections:
        profile_id = title.split()[0]
        line = section_line_utm(start_ll, end_ll, transformer)
        for panel in page.panels:
            frame = station_projection(line, station_summaries[panel.label], transformer)
            projected[(profile_id, panel.label)] = frame
            if not frame.empty:
                plotted_station_frames.append(frame[["station", "sta_lon", "sta_lat"]])
    plotted_stations = (
        pd.concat(plotted_station_frames, ignore_index=True).drop_duplicates("station")
        if plotted_station_frames
        else pd.DataFrame(columns=["station", "sta_lon", "sta_lat"])
    )
    plotted_station_ids = set(plotted_stations["station"].astype(str))
    event_frames = [
        frame.loc[frame["station"].isin(plotted_station_ids), ["event_id", "event_lon", "event_lat"]]
        for frame in panel_rows.values()
        if not frame.empty
    ]
    plotted_events = (
        pd.concat(event_frames, ignore_index=True).dropna(subset=["event_lon", "event_lat"]).drop_duplicates("event_id")
        if event_frames
        else pd.DataFrame(columns=["event_id", "event_lon", "event_lat"])
    )
    norm, y_limits = page_value_scale(projected, page)
    cmap = plt.get_cmap(page.cmap)
    events_values = np.concatenate(
        [
            frame["events"].to_numpy(dtype=float)
            for frame in projected.values()
            if not frame.empty and "events" in frame
        ]
    ) if any(not frame.empty for frame in projected.values()) else np.array([1.0])
    event_min = float(np.nanmin(events_values)) if np.isfinite(events_values).any() else 1.0
    event_max = float(np.nanmax(events_values)) if np.isfinite(events_values).any() else event_min

    n_profiles = len(PROFILE_ORDER)
    n_panels = len(page.panels)
    width = 26.5 if n_panels == 3 else 33.0
    height = 36.0 if n_panels == 3 else 37.0
    fig = plt.figure(figsize=(width, height), constrained_layout=False)
    grid = fig.add_gridspec(
        nrows=n_profiles + 1,
        ncols=n_panels + 1,
        height_ratios=[1.7] + [1.0] * n_profiles,
        width_ratios=[1.65] + [1.0] * n_panels,
        hspace=0.34,
        wspace=0.16,
    )
    map_ax = fig.add_subplot(grid[0, :])
    plot_page_map(
        map_ax,
        regions=regions,
        sections=sections,
        metadata=metadata,
        stations=plotted_stations,
        events=plotted_events,
        basemap_cache_dir=basemap_cache_dir,
    )
    section_axes: list[plt.Axes] = []
    scatter_axes: list[plt.Axes] = []
    row_lookup = metadata.set_index("profile_id")
    last_section_image = None
    for row_index, profile_id in enumerate(PROFILE_ORDER, start=1):
        section_ax = fig.add_subplot(grid[row_index, 0])
        section_axes.append(section_ax)
        section_grid = section_grids[profile_id]
        last_section_image = plot_section_grid(
            section_ax,
            section_grid,
            variant=variant,
            vs_gradient_norm=vs_gradient_norm,
        )
        section_ax.invert_yaxis()
        section_ax.set_xlim(0.0, float(section_grid["length_km"]))
        section_ax.set_ylim(15.0, 0.0)
        section_ax.grid(color="white", linewidth=0.45, alpha=0.55)
        section_ax.tick_params(labelsize=7.2)
        if row_index == n_profiles:
            section_ax.set_xlabel("Distance (km)", fontsize=8.5)
        else:
            section_ax.tick_params(labelbottom=False)
        section_ax.set_ylabel("Depth\n(km)", fontsize=8.3)
        row = row_lookup.loc[profile_id]
        section_ax.text(
            0.012,
            0.08,
            f"{profile_id} {row.family.replace('_', ' ')}\n{row.bearing_deg:.1f} deg; basin {row.la_basin_intersection_km:.1f} km",
            transform=section_ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=8.2,
            color=COLORS["ink"],
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.76, "pad": 2.0},
        )
        for col_index, panel in enumerate(page.panels, start=1):
            scatter_ax = fig.add_subplot(grid[row_index, col_index])
            scatter_axes.append(scatter_ax)
            frame = projected[(profile_id, panel.label)]
            scatter_ax.grid(True, color=COLORS["grid"], linewidth=0.55, alpha=0.75)
            if page.value_mode != "raw_cc":
                scatter_ax.axhline(0.0, color=COLORS["ink"], linewidth=0.8, alpha=0.68, zorder=1)
            scatter_ax.set_xlim(0.0, float(section_grid["length_km"]))
            scatter_ax.set_ylim(*y_limits)
            scatter_ax.tick_params(labelsize=7.2)
            if row_index == 1:
                scatter_ax.set_title(panel.label, fontsize=11.0, fontweight="bold", pad=7)
            if row_index == n_profiles:
                scatter_ax.set_xlabel("Distance (km)", fontsize=8.5)
            else:
                scatter_ax.tick_params(labelbottom=False)
            if col_index == 1:
                scatter_ax.set_ylabel(page.y_label, fontsize=8.0)
            else:
                scatter_ax.tick_params(labelleft=False)
            if frame.empty:
                scatter_ax.text(
                    0.50,
                    0.50,
                    "No stations",
                    transform=scatter_ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=8.5,
                    color=COLORS["muted"],
                )
                continue
            yerr = np.vstack(
                [
                    np.clip(frame["value"] - frame["q25"], 0.0, None),
                    np.clip(frame["q75"] - frame["value"], 0.0, None),
                ]
            )
            scatter_ax.errorbar(
                frame["projected_km"],
                frame["value"],
                yerr=yerr,
                fmt="none",
                ecolor=COLORS["muted"],
                elinewidth=0.65,
                alpha=0.52,
                capsize=1.2,
                zorder=2,
            )
            scatter_ax.scatter(
                frame["projected_km"],
                frame["value"],
                c=frame["value"],
                cmap=cmap,
                norm=norm,
                s=event_marker_size(frame["events"], event_min, event_max),
                edgecolor=COLORS["ink"],
                linewidth=0.25,
                alpha=0.90,
                zorder=3,
            )
            lowess_x, lowess_y = weighted_lowess(frame)
            if lowess_x.size:
                scatter_ax.plot(lowess_x, lowess_y, color=COLORS["ink"], linewidth=1.15, alpha=LOWESS_ALPHA, zorder=4)
            scatter_ax.text(
                0.985,
                0.92,
                f"{frame['station'].nunique():,} sta\n{int(frame['events'].sum()):,} ev-wt",
                transform=scatter_ax.transAxes,
                ha="right",
                va="top",
                fontsize=6.8,
                color=COLORS["muted"],
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.70, "pad": 1.2},
                zorder=5,
            )
    assert last_section_image is not None
    cbar_ax = fig.add_axes([0.905, 0.877, 0.012, 0.068])
    cbar = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=cbar_ax)
    cbar.set_label(page.colorbar_label, fontsize=8.5)
    cbar.ax.tick_params(labelsize=7.4)
    vs_cbar_ax = fig.add_axes([0.935, 0.877, 0.012, 0.068])
    if variant.mode == "vs-gradient":
        vs_cbar = fig.colorbar(last_section_image, cax=vs_cbar_ax, extend="both")
    else:
        vs_cbar = fig.colorbar(last_section_image, cax=vs_cbar_ax)
    vs_cbar.set_label(variant.section_colorbar_label, fontsize=8.5)
    vs_cbar.ax.tick_params(labelsize=7.4)
    size_values = np.unique(np.round(np.linspace(event_min, event_max, min(3, max(1, int(event_max - event_min + 1))))).astype(int))
    if size_values.size:
        size_handles = [
            Line2D(
                [0],
                [0],
                marker="o",
                linestyle="none",
                markerfacecolor="white",
                markeredgecolor=COLORS["ink"],
                markersize=math.sqrt(event_marker_size([value], event_min, event_max)[0]),
                label=f"{value:g} events",
            )
            for value in size_values
        ]
        lowess_handle = Line2D([0], [0], color=COLORS["ink"], linewidth=1.2, alpha=LOWESS_ALPHA, label="LOWESS")
        fig.legend(
            [*size_handles, lowess_handle],
            [handle.get_label() for handle in [*size_handles, lowess_handle]],
            title="Station support",
            loc="upper right",
            bbox_to_anchor=(0.895, 0.962),
            ncol=min(4, len(size_handles) + 1),
            frameon=True,
            fontsize=8.2,
            title_fontsize=8.5,
        )
    title = page.title if not variant.title_suffix else f"{page.title}: {variant.title_suffix}"
    fig.suptitle(title, fontsize=18.0, fontweight="bold", color=COLORS["ink"], y=0.992)
    fig.text(0.055, 0.966, page.subtitle, fontsize=10.5, color=COLORS["muted"], ha="left", va="top")
    footer_text = textwrap.fill(
        (
            f"Stations are included within {STATION_CORRIDOR_KM:g} km of each profile. {model_label} cross sections use the same rotated candidate lines as the locator map. "
            f"LOWESS span is {ATLAS_LOWESS_FRAC:.2f}, weighted by station event count. {variant.section_note}"
        ),
        width=180 if n_panels == 3 else 225,
        break_long_words=False,
    )
    fig.text(
        0.055,
        0.020,
        footer_text,
        fontsize=9.5,
        color=COLORS["muted"],
        ha="left",
        va="bottom",
    )
    fig.subplots_adjust(left=0.055, right=0.89, top=0.952, bottom=0.055)
    output_path = figures_dir / f"{variant.filename_prefix}_{page.slug}.png"
    fig.savefig(output_path, dpi=165)
    pdf.savefig(fig)
    plt.close(fig)
    return output_path


def add_png_page_to_pdf(pdf: PdfPages, image_path: Path) -> None:
    image = plt.imread(image_path)
    height_px, width_px = image.shape[:2]
    fig_width = 14.0
    fig_height = fig_width * height_px / width_px
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.imshow(image)
    ax.axis("off")
    fig.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)
    pdf.savefig(fig)
    plt.close(fig)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--model-h5", type=Path, default=DEFAULT_MODEL_H5)
    parser.add_argument("--model-label", default="CVM-SI")
    parser.add_argument("--model-node-stride", type=int, default=2)
    parser.add_argument(
        "--variant",
        choices=("vs", "vs-gradient", "both"),
        default="vs",
        help="Atlas cross-section display mode. Default preserves the original absolute-Vs atlas output.",
    )
    return parser.parse_args(argv)


def selected_variants(variant: str) -> list[AtlasVariant]:
    if variant == "both":
        return [ATLAS_VARIANTS["vs"], ATLAS_VARIANTS["vs-gradient"]]
    return [ATLAS_VARIANTS[variant]]


def label_variants(variants: list[AtlasVariant], model_label: str) -> list[AtlasVariant]:
    return [
        replace(
            variant,
            section_note=variant.section_note.replace("CVM-SI", model_label),
        )
        for variant in variants
    ]


def render_atlas_variant(
    *,
    variant: AtlasVariant,
    output_dir: Path,
    figures_dir: Path,
    report_dir: Path,
    regions: list,
    sections: list[tuple[str, tuple[float, float], tuple[float, float]]],
    metadata: pd.DataFrame,
    pairs: pd.DataFrame,
    section_grids: dict[str, dict[str, object]],
    pairs_path: Path,
    metadata_path: Path,
    model_label: str = "CVM-SI",
) -> list[Path]:
    atlas_dir = figures_dir / variant.output_subdir
    atlas_dir.mkdir(parents=True, exist_ok=True)
    basemap_cache_dir = output_dir / "basemap_cache"
    candidate_map_path = atlas_dir / f"{variant.filename_prefix}_candidate_lines_map.png"
    render_candidate_map(regions, sections, metadata, candidate_map_path, basemap_cache_dir=basemap_cache_dir)

    vs_gradient_norm = section_vs_gradient_norm(section_grids) if variant.mode == "vs-gradient" else None

    pdf_path = report_dir / variant.pdf_name
    rendered_pages: list[Path] = []
    with PdfPages(pdf_path) as pdf:
        add_png_page_to_pdf(pdf, candidate_map_path)
        for page in page_specs(model_label):
            rendered_pages.append(
                render_metric_page(
                    page=page,
                    variant=variant,
                    pairs=pairs,
                    regions=regions,
                    sections=sections,
                    metadata=metadata,
                    section_grids=section_grids,
                    vs_gradient_norm=vs_gradient_norm,
                    figures_dir=atlas_dir,
                    basemap_cache_dir=basemap_cache_dir,
                    pdf=pdf,
                    model_label=model_label,
                )
            )
    manifest_path = report_dir / variant.manifest_name
    pd.DataFrame(
        [
            {"kind": "candidate_map", "path": str(candidate_map_path)},
            *({"kind": "metric_page", "path": str(path)} for path in rendered_pages),
            {"kind": "pdf", "path": str(pdf_path)},
            {"kind": "pairs", "path": str(pairs_path)},
            {"kind": "sections", "path": str(metadata_path)},
        ]
    ).to_csv(manifest_path, index=False)
    return [candidate_map_path, *rendered_pages, pdf_path, manifest_path]


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    set_plot_theme()
    output_dir = args.output_dir.expanduser().resolve()
    figures_dir = output_dir / "figures"
    tables_dir = output_dir / "tables"
    report_dir = output_dir / "report"
    for directory in (figures_dir, tables_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)

    regions = load_regions(DEFAULT_REGIONS)
    long_sections, perp_sections, metadata = build_profile_families(regions)
    sections = [*long_sections, *perp_sections]
    metadata_path = tables_dir / "la_basin_metric_profile_atlas_sections.csv"
    metadata.to_csv(metadata_path, index=False)

    raw = load_metric_rows(args.metrics.expanduser(), model=args.model)
    pairs = collapse_components(raw)
    pairs_path = tables_dir / "la_basin_metric_profile_atlas_pairs.parquet"
    pairs.to_parquet(pairs_path, index=False)

    sampler = ModelSampler(args.model_h5.expanduser(), node_stride=args.model_node_stride)
    section_grids = sample_section_grids(sampler, sections)
    add_vertical_vs_gradient_cells(section_grids)

    rendered_paths: list[Path] = []
    for variant in label_variants(selected_variants(args.variant), args.model_label):
        rendered_paths.extend(
            render_atlas_variant(
                variant=variant,
                output_dir=output_dir,
                figures_dir=figures_dir,
                report_dir=report_dir,
                regions=regions,
                sections=sections,
                metadata=metadata,
                pairs=pairs,
                section_grids=section_grids,
                pairs_path=pairs_path,
                metadata_path=metadata_path,
                model_label=args.model_label,
            )
        )

    for path in [metadata_path, pairs_path, *rendered_paths]:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
