#!/usr/bin/env python3
"""Render one-page-per-profile metric residual PDFs in the approved split layout."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import sys
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from PIL import Image
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point, shape
from shapely.ops import transform as shapely_transform

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from cvmsi_hypothesis_study import (  # noqa: E402
    COLORS,
    DEFAULT_BASEMAP_SOURCE,
    DEFAULT_BASEMAP_ZOOM,
    WEB_MERCATOR,
    WGS84,
    add_required_basemap,
    format_projected_map_axis,
    iter_polygons,
    load_regions,
    set_plot_theme,
)


PROFILE_ORDER = [f"L{i}" for i in range(1, 6)] + [f"P{i}" for i in range(1, 6)]
BANDS = ("1-2 sec", "2-3 sec", "3-5 sec")
PASSBAND_COLORS = {"1-2 sec": "#337ab7", "2-3 sec": "#e5a100", "3-5 sec": "#d9534f"}
MODEL_IDS = {
    "cvmsi": "cvmsi_20260506_material_0p6x1p2_asdf",
    "cvmh": "cvmh_20260506_material_0p6x1p2_mseed",
}
MODEL_LABELS = {"cvmsi": "CVM-SI", "cvmh": "CVM-H"}
METRIC_LABELS = {
    "PGA": "PGA",
    "PGV": "PGV",
    "arias_duration": "Arias duration",
    "original_cc": "original cross correlation",
    "energy_intensity": "energy intensity",
    "CAV": "CAV",
}
METRIC_OUTPUT = {
    "PGA": "pga",
    "PGV": "pgv",
    "arias_duration": "arias_duration",
    "original_cc": "cross_correlation",
    "energy_intensity": "energy_intensity",
    "CAV": "cav",
}
METRICS = ("PGA", "PGV", "arias_duration", "original_cc", "energy_intensity", "CAV")
STATION_CORRIDOR_KM = 5.0

INK = "#202938"
MUTED = "#6d7890"
GRID = "#dbe3ee"
AXIS = "#d3dbe8"
SURFACE = "#fbfbfd"
NEUTRAL_POINT = "#f5f0e8"


@dataclass(frozen=True)
class MetricSpec:
    metric: str
    title: str
    value_column: str
    y_label: str
    y_limits: tuple[float, float]
    raw_cc: bool = False


def metric_spec(metric: str) -> MetricSpec:
    if metric == "original_cc":
        return MetricSpec(
            metric=metric,
            title=METRIC_LABELS[metric],
            value_column="value",
            y_label="Station median original CC",
            y_limits=(-1.0, 1.0),
            raw_cc=True,
        )
    return MetricSpec(
        metric=metric,
        title=METRIC_LABELS[metric],
        value_column="log2_residual",
        y_label=f"Station median {METRIC_LABELS[metric]} residual, log2(obs/syn)",
        y_limits=(-3.05, 3.05),
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metrics",
        type=Path,
        default=Path("outputs/review/la_basin_metric_profile_split_layout_20260702/inputs/metrics_final_enriched.parquet"),
    )
    parser.add_argument(
        "--regions",
        type=Path,
        default=Path("outputs/review/la_basin_metric_profile_split_layout_20260702/inputs/regions_updated.geojson"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/review/la_basin_metric_profile_split_layout_20260702"))
    parser.add_argument("--models", nargs="*", default=("cvmsi", "cvmh"), choices=tuple(MODEL_IDS))
    parser.add_argument("--metrics-focus", nargs="*", default=METRICS, choices=METRICS)
    parser.add_argument(
        "--station-corridor-km",
        type=float,
        default=STATION_CORRIDOR_KM,
        help="Maximum station offset from each profile line in km.",
    )
    return parser.parse_args(argv)


def load_section_table(model_key: str) -> pd.DataFrame:
    path = REPO_ROOT / "outputs" / "review" / f"{model_key}_hypothesis_study" / "tables" / "la_basin_metric_profile_atlas_sections.csv"
    sections = pd.read_csv(path)
    return sections.set_index("profile_id").loc[PROFILE_ORDER].reset_index()


def section_line(row: pd.Series) -> LineString:
    transformer = Transformer.from_crs(WGS84, "EPSG:32611", always_xy=True)
    start = transformer.transform(float(row.start_lon), float(row.start_lat))
    end = transformer.transform(float(row.end_lon), float(row.end_lat))
    return LineString([(float(start[0]), float(start[1])), (float(end[0]), float(end[1]))])


def read_metric_rows(path: Path, *, model_key: str, metric: str) -> pd.DataFrame:
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
        "obs_qc_status",
        "syn_qc_status",
        "comparison_qc_status",
    ]
    df = pd.read_parquet(path, columns=columns)
    df = df.loc[
        df["model"].astype(str).eq(MODEL_IDS[model_key])
        & df["metric"].astype(str).eq(metric)
        & df["band"].astype(str).isin(BANDS)
        & df["component"].astype(str).str.upper().isin(["R", "T"])
        & df["obs_qc_status"].astype(str).eq("pass")
        & df["syn_qc_status"].astype(str).eq("pass")
        & df["comparison_qc_status"].astype(str).eq("pass")
    ].copy()
    for column in ["value", "log2_residual", "event_lat", "event_lon", "sta_lat", "sta_lon"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    for column in ["event_id", "station", "component", "metric", "band"]:
        df[column] = df[column].astype(str)
    return df.replace([np.inf, -np.inf], np.nan).dropna(
        subset=["event_id", "station", "band", "event_lat", "event_lon", "sta_lat", "sta_lon"]
    )


def collapse_components(df: pd.DataFrame) -> pd.DataFrame:
    keys = ["event_id", "station", "metric", "band", "period_s"]
    return (
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


def station_values(data: pd.DataFrame, value_column: str) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame(columns=["station", "sta_lon", "sta_lat", "value", "q25", "q75", "events", "records"])
    return (
        data.groupby("station", as_index=False)
        .agg(
            sta_lon=("sta_lon", "median"),
            sta_lat=("sta_lat", "median"),
            value=(value_column, "median"),
            q25=(value_column, lambda values: float(values.quantile(0.25))),
            q75=(value_column, lambda values: float(values.quantile(0.75))),
            events=("event_id", "nunique"),
            records=(value_column, "size"),
        )
        .replace([np.inf, -np.inf], np.nan)
        .dropna(subset=["sta_lon", "sta_lat", "value"])
    )


def project_stations(section: LineString, values: pd.DataFrame, *, corridor_km: float | None = None) -> pd.DataFrame:
    if corridor_km is None:
        corridor_km = STATION_CORRIDOR_KM
    if values.empty:
        return pd.DataFrame(columns=[*values.columns, "projected_km", "offset_km"])
    transformer = Transformer.from_crs(WGS84, "EPSG:32611", always_xy=True)
    xy = np.array(transformer.transform(values["sta_lon"].to_numpy(float), values["sta_lat"].to_numpy(float))).T
    rows: list[dict[str, object]] = []
    for row, coords in zip(values.itertuples(index=False), xy):
        point = Point(float(coords[0]), float(coords[1]))
        offset_km = point.distance(section) / 1000.0
        if offset_km > corridor_km:
            continue
        record = row._asdict()
        record["projected_km"] = section.project(point) / 1000.0
        record["offset_km"] = offset_km
        rows.append(record)
    if not rows:
        return pd.DataFrame(columns=[*values.columns, "projected_km", "offset_km"])
    return pd.DataFrame(rows).sort_values("projected_km")


def load_model_property_reference(model_key: str) -> dict[str, pd.DataFrame]:
    path = (
        REPO_ROOT
        / "outputs"
        / "review"
        / f"{model_key}_hypothesis_study"
        / "tables"
        / "la_basin_metric_profile_split_pga_projected_stations.csv"
    )
    ref = pd.read_csv(path)
    columns = [
        "projected_km",
        "max_abs_vs_gradient_depth_km",
        "max_abs_vs_gradient_strength",
    ]
    out = {}
    for profile_id, frame in ref.groupby("profile_id"):
        props = frame[columns].dropna().sort_values("projected_km")
        props = props.groupby("projected_km", as_index=False).median(numeric_only=True)
        out[str(profile_id)] = props
    return out


def add_model_properties(frame: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        for column in ["max_abs_vs_gradient_depth_km", "max_abs_vs_gradient_strength"]:
            frame[column] = []
        return frame
    if ref.empty:
        frame["max_abs_vs_gradient_depth_km"] = np.nan
        frame["max_abs_vs_gradient_strength"] = np.nan
        return frame
    x_ref = ref["projected_km"].to_numpy(float)
    order = np.argsort(x_ref)
    x_ref = x_ref[order]
    for column in ["max_abs_vs_gradient_depth_km", "max_abs_vs_gradient_strength"]:
        y_ref = ref[column].to_numpy(float)[order]
        valid = np.isfinite(x_ref) & np.isfinite(y_ref)
        if valid.sum() < 2:
            frame[column] = np.nan
        else:
            frame[column] = np.interp(
                frame["projected_km"].to_numpy(float),
                x_ref[valid],
                y_ref[valid],
                left=float(y_ref[valid][0]),
                right=float(y_ref[valid][-1]),
            )
    return frame


def weighted_quantile(values: np.ndarray, weights: np.ndarray, qs: Sequence[float]) -> list[float]:
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0.0)
    values = values[valid]
    weights = weights[valid]
    if values.size == 0:
        return [np.nan for _ in qs]
    order = np.argsort(values)
    values = values[order]
    weights = weights[order]
    cdf = np.cumsum(weights)
    total = float(cdf[-1])
    return [float(values[np.searchsorted(cdf, q * total, side="left")]) for q in qs]


def marker_size(events: pd.Series | np.ndarray, event_min: float, event_max: float, minimum: float = 12.0, maximum: float = 50.0) -> np.ndarray:
    events = np.asarray(events, dtype=float)
    if not np.isfinite(event_min) or not np.isfinite(event_max) or event_max <= event_min:
        scaled = np.full_like(events, 0.5, dtype=float)
    else:
        scaled = (np.sqrt(np.clip(events, event_min, event_max)) - math.sqrt(event_min)) / (
            math.sqrt(event_max) - math.sqrt(event_min)
        )
    return minimum + scaled * (maximum - minimum)


def moving_window(frame: pd.DataFrame, xmax: float, *, half_width: float = 5.0) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    centers = np.arange(0.0, xmax + 0.001, 1.0)
    mean = np.full_like(centers, np.nan, dtype=float)
    lo = np.full_like(centers, np.nan, dtype=float)
    hi = np.full_like(centers, np.nan, dtype=float)
    if frame.empty:
        return centers, mean, lo, hi
    x = frame["projected_km"].to_numpy(float)
    y = frame["value"].to_numpy(float)
    w = frame["events"].to_numpy(float)
    stations = frame["station"].astype(str).to_numpy()
    for idx, center in enumerate(centers):
        mask = np.isfinite(x) & np.isfinite(y) & np.isfinite(w) & (w > 0.0) & (np.abs(x - center) <= half_width)
        if not mask.any() or len(set(stations[mask])) < 3 or float(np.sum(w[mask])) < 15.0:
            continue
        mean[idx] = float(np.average(y[mask], weights=w[mask]))
        lo[idx], hi[idx] = weighted_quantile(y[mask], w[mask], [0.25, 0.75])
    return centers, mean, lo, hi


def weighted_r(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> tuple[float, int]:
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0.0)
    x = x[valid]
    y = y[valid]
    weights = weights[valid]
    if x.size < 4 or np.nanstd(x) <= 0.0 or np.nanstd(y) <= 0.0:
        return np.nan, int(x.size)
    x_mean = float(np.average(x, weights=weights))
    y_mean = float(np.average(y, weights=weights))
    cov = float(np.average((x - x_mean) * (y - y_mean), weights=weights))
    var_x = float(np.average((x - x_mean) ** 2, weights=weights))
    var_y = float(np.average((y - y_mean) ** 2, weights=weights))
    return float(cov / math.sqrt(var_x * var_y)), int(x.size)


def weighted_linear_fit(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> tuple[float, float] | None:
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0.0)
    x = x[valid]
    y = y[valid]
    weights = weights[valid]
    if x.size < 4 or np.ptp(x) <= 0.0:
        return None
    design = np.column_stack([np.ones_like(x), x])
    root = np.sqrt(weights)
    try:
        beta, *_ = np.linalg.lstsq(design * root[:, None], y * root, rcond=None)
    except np.linalg.LinAlgError:
        return None
    return float(beta[0]), float(beta[1])


def binned_curve(data: pd.DataFrame, x_col: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    data = data.dropna(subset=[x_col, "value", "events"])
    if data.empty:
        return np.array([]), np.array([]), np.array([]), np.array([])
    x = data[x_col].to_numpy(float)
    lo = float(np.nanmin(x))
    hi = float(np.nanmax(x))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return np.array([]), np.array([]), np.array([]), np.array([])
    edges = np.linspace(lo, hi, 9)
    centers: list[float] = []
    means: list[float] = []
    q25: list[float] = []
    q75: list[float] = []
    for left, right in zip(edges[:-1], edges[1:]):
        mask = (data[x_col] >= left) & ((data[x_col] <= right) if right == edges[-1] else (data[x_col] < right))
        subset = data.loc[mask]
        if subset["station"].nunique() < 2 or float(subset["events"].sum()) < 8.0:
            continue
        weights = subset["events"].to_numpy(float)
        values = subset["value"].to_numpy(float)
        centers.append(float(np.average(subset[x_col].to_numpy(float), weights=weights)))
        means.append(float(np.average(values, weights=weights)))
        lo_q, hi_q = weighted_quantile(values, weights, [0.25, 0.75])
        q25.append(lo_q)
        q75.append(hi_q)
    return np.asarray(centers), np.asarray(means), np.asarray(q25), np.asarray(q75)


def style_axis(ax: plt.Axes, y_limits: tuple[float, float]) -> None:
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.65, alpha=0.72)
    ax.axhline(0.0, color=INK, linewidth=0.85, alpha=0.45, zorder=1)
    ax.set_ylim(*y_limits)
    ax.tick_params(axis="both", labelsize=8.0, colors="#6c7890")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(AXIS)
    ax.spines["bottom"].set_color(AXIS)


def model_crop_path(model_key: str, profile_id: str) -> Path:
    return (
        REPO_ROOT
        / "outputs"
        / "review"
        / f"{model_key}_hypothesis_study"
        / "figures"
        / "la_basin_metric_profile_split_pga"
        / f"la_basin_metric_profile_split_pga_{profile_id}.png"
    )


def add_model_crops(fig: plt.Figure, model_key: str, profile_id: str) -> None:
    page = Image.open(model_crop_path(model_key, profile_id)).convert("RGB")
    crops = {
        "model": (0, 1618, 1905, 1842),
        "gradient": (0, 1905, 1905, 2258),
    }
    for name, bounds in (
        ("model", [0.000, 0.205, 0.610, 0.160]),
        ("gradient", [0.000, 0.018, 0.610, 0.170]),
    ):
        ax = fig.add_axes(bounds)
        ax.imshow(page.crop(crops[name]), aspect="auto")
        ax.set_axis_off()


def map_extent_from_points(xs: list[float], ys: list[float]) -> tuple[float, float, float, float]:
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    pad_x = max((xmax - xmin) * 0.10, 8000.0)
    pad_y = max((ymax - ymin) * 0.10, 8000.0)
    return xmin - pad_x, xmax + pad_x, ymin - pad_y, ymax + pad_y


def draw_map(
    ax: plt.Axes,
    *,
    regions: list,
    sections: pd.DataFrame,
    profile_id: str | None,
    stations: pd.DataFrame,
    events: pd.DataFrame,
    basemap_cache_dir: Path,
    title: str,
) -> None:
    to_web = Transformer.from_crs(WGS84, WEB_MERCATOR, always_xy=True)
    xs: list[float] = []
    ys: list[float] = []
    for row in sections.itertuples(index=False):
        line_x, line_y = to_web.transform([row.start_lon, row.end_lon], [row.start_lat, row.end_lat])
        xs.extend(line_x)
        ys.extend(line_y)
    if not stations.empty:
        sx, sy = to_web.transform(stations["sta_lon"].to_numpy(float), stations["sta_lat"].to_numpy(float))
        xs.extend(sx)
        ys.extend(sy)
    else:
        sx = sy = np.array([])
    if not events.empty:
        ex, ey = to_web.transform(events["event_lon"].to_numpy(float), events["event_lat"].to_numpy(float))
        xs.extend(ex)
        ys.extend(ey)
    else:
        ex = ey = np.array([])
    for region in regions:
        if "los angeles basin" in region.name.lower():
            basin_web = shapely_transform(to_web.transform, region.geometry_lonlat)
            for polygon in iter_polygons(basin_web):
                px, py = polygon.exterior.xy
                xs.extend(px)
                ys.extend(py)
            break

    xmin, xmax, ymin, ymax = map_extent_from_points(xs, ys)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    add_basemap(ax, basemap_cache_dir=basemap_cache_dir)

    for region in regions:
        if "los angeles basin" not in region.name.lower():
            continue
        basin_web = shapely_transform(to_web.transform, region.geometry_lonlat)
        for polygon in iter_polygons(basin_web):
            px, py = polygon.exterior.xy
            ax.fill(px, py, facecolor="#ffffff", edgecolor=INK, linewidth=0.8, alpha=0.18, zorder=4)
    for row in sections.itertuples(index=False):
        line_x, line_y = to_web.transform([row.start_lon, row.end_lon], [row.start_lat, row.end_lat])
        color = COLORS["blue"] if row.family == "long_axis" else COLORS["gold"]
        is_current = profile_id == row.profile_id
        is_overview = profile_id is None
        linewidth = 3.0 if is_current else 1.75 if is_overview else 1.0
        alpha = 0.98 if is_current else 0.78 if is_overview else 0.30
        ax.plot(line_x, line_y, color=color, linewidth=linewidth, alpha=alpha, zorder=7)
        if is_current or is_overview:
            ax.text(
                0.5 * (line_x[0] + line_x[1]),
                0.5 * (line_y[0] + line_y[1]),
                row.profile_id,
                color="white",
                fontsize=8.0 if is_overview else 10,
                fontweight="bold",
                ha="center",
                va="center",
                bbox={"facecolor": color, "edgecolor": "white", "boxstyle": "round,pad=0.18", "linewidth": 0.5, "alpha": 0.96},
                zorder=9,
            )
    if len(ex):
        ax.scatter(
            ex,
            ey,
            marker="*",
            s=42 if profile_id is None else 30,
            color=COLORS["gold"],
            edgecolor=INK,
            linewidth=0.35,
            alpha=0.70 if profile_id is None else 0.52,
            zorder=6,
        )
    if len(sx):
        ax.scatter(sx, sy, s=14, color=INK, edgecolor="white", linewidth=0.30, alpha=0.70, zorder=8)
    format_projected_map_axis(ax)
    ax.set_title(title, fontsize=11.5, fontweight="bold", color=INK, pad=5)
    ax.tick_params(labelsize=7.0, colors="#6c7890")


def _extent_token_to_float(token: str) -> float:
    sign = -1.0 if token[1] == "m" else 1.0
    return sign * float(token[2:].replace("p", "."))


def cached_basemap_extent(path: Path) -> tuple[float, float, float, float] | None:
    match = re.search(r"_w([mp][0-9p]+)_e([mp][0-9p]+)_s([mp][0-9p]+)_n([mp][0-9p]+)", path.stem)
    if not match:
        match = re.search(r"_w([mp][0-9p]+)_e([mp][0-9p]+)_s([mp][0-9p]+)_n([mp][0-9p]+)", path.name)
    if not match:
        match = re.search(r"_wm([0-9p]+)_em([0-9p]+)_s([0-9p]+)_n([0-9p]+)", path.stem)
        if not match:
            return None
        west = -float(match.group(1).replace("p", "."))
        east = -float(match.group(2).replace("p", "."))
        south = float(match.group(3).replace("p", "."))
        north = float(match.group(4).replace("p", "."))
        return west, east, south, north
    west = _extent_token_to_float("w" + match.group(1))
    east = _extent_token_to_float("e" + match.group(2))
    south = _extent_token_to_float("s" + match.group(3))
    north = _extent_token_to_float("n" + match.group(4))
    return west, east, south, north


def add_cached_basemap(ax: plt.Axes) -> bool:
    candidates = [
        REPO_ROOT / "outputs" / "review" / "la_basin_metric_profile_split_layout_20260702" / "basemap_cache",
        REPO_ROOT / "outputs" / "review" / "cvmsi_hypothesis_study" / "basemap_cache",
    ]
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    for cache_dir in candidates:
        for path in sorted(cache_dir.glob("*.tif")):
            extent = cached_basemap_extent(path)
            if extent is None:
                continue
            west, east, south, north = extent
            covers = west <= xlim[0] and east >= xlim[1] and south <= ylim[0] and north >= ylim[1]
            if not covers:
                continue
            image = Image.open(path).convert("RGB")
            ax.imshow(image, extent=[west, east, south, north], origin="upper", zorder=0)
            return True
    return False


def add_basemap(ax: plt.Axes, *, basemap_cache_dir: Path) -> None:
    try:
        add_required_basemap(ax, source=DEFAULT_BASEMAP_SOURCE, cache_dir=basemap_cache_dir, zoom=DEFAULT_BASEMAP_ZOOM)
    except Exception:
        if not add_cached_basemap(ax):
            raise


def render_overview_page(
    *,
    pdf: PdfPages,
    out_png: Path,
    regions: list,
    sections: pd.DataFrame,
    stations: pd.DataFrame,
    events: pd.DataFrame,
    model_label: str,
    spec: MetricSpec,
    basemap_cache_dir: Path,
) -> None:
    fig = plt.figure(figsize=(17.0, 11.0), dpi=190, facecolor=SURFACE)
    fig.suptitle(f"{model_label} {spec.title}: LA Basin candidate profile lines", y=0.975, fontsize=18, fontweight="bold", color=INK)
    ax = fig.add_axes([0.065, 0.105, 0.870, 0.790])
    draw_map(
        ax,
        regions=regions,
        sections=sections,
        profile_id=None,
        stations=stations,
        events=events,
        basemap_cache_dir=basemap_cache_dir,
        title=f"{len(sections)} cross-section lines with {stations['station'].nunique() if not stations.empty else 0:,} plotted stations and {events['event_id'].nunique() if not events.empty else 0:,} events",
    )
    handles = [
        Line2D([0], [0], color=COLORS["blue"], linewidth=2.5, label="Long-axis profiles"),
        Line2D([0], [0], color=COLORS["gold"], linewidth=2.5, label="Perpendicular profiles"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=INK, markeredgecolor="white", markersize=6, label="Stations"),
        Line2D([0], [0], marker="*", color="none", markerfacecolor=COLORS["gold"], markeredgecolor=INK, markersize=10, label="Events"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=9, frameon=True)
    fig.text(
        0.065,
        0.035,
        f"Stations are included if they fall within {STATION_CORRIDOR_KM:g} km of at least one profile. Components are restricted to R/T before station medians are computed.",
        ha="left",
        va="bottom",
        fontsize=9,
        color=MUTED,
    )
    fig.savefig(out_png, dpi=190)
    pdf.savefig(fig)
    plt.close(fig)


def render_profile_page(
    *,
    pdf: PdfPages,
    out_png: Path,
    model_key: str,
    model_label: str,
    spec: MetricSpec,
    profile_row: pd.Series,
    sections: pd.DataFrame,
    regions: list,
    band_frames: dict[str, pd.DataFrame],
    band_rows: dict[str, pd.DataFrame],
    basemap_cache_dir: Path,
) -> None:
    profile_id = str(profile_row.profile_id)
    all_frames = [frame for frame in band_frames.values() if not frame.empty]
    length_km = math.hypot(
        float(profile_row.end_lon) - float(profile_row.start_lon),
        float(profile_row.end_lat) - float(profile_row.start_lat),
    )
    # Use the already projected station range rather than lon/lat length; keep the visible axis no shorter than the approved pages.
    xmax = max(125.0, *(float(frame["projected_km"].max()) for frame in all_frames)) if all_frames else 125.0
    xmax = max(5.0, math.ceil(xmax / 5.0) * 5.0)
    event_values = np.concatenate([frame["events"].to_numpy(float) for frame in all_frames]) if all_frames else np.array([1.0])
    event_min = float(np.nanmin(event_values))
    event_max = float(np.nanmax(event_values))

    station_frame = (
        pd.concat([frame[["station", "sta_lon", "sta_lat"]] for frame in all_frames], ignore_index=True).drop_duplicates("station")
        if all_frames
        else pd.DataFrame(columns=["station", "sta_lon", "sta_lat"])
    )
    station_ids = set(station_frame["station"].astype(str))
    event_candidates = [rows for rows in band_rows.values() if not rows.empty]
    events = (
        pd.concat(event_candidates, ignore_index=True)
        .loc[lambda data: data["station"].astype(str).isin(station_ids), ["event_id", "event_lon", "event_lat"]]
        .dropna()
        .drop_duplicates("event_id")
        if event_candidates and station_ids
        else pd.DataFrame(columns=["event_id", "event_lon", "event_lat"])
    )

    fig = plt.figure(figsize=(4017 / 190.0, 2631 / 190.0), dpi=190, facecolor=SURFACE)
    title = (
        f"{model_label} {spec.title} profile {profile_id}: {str(profile_row.family).replace('_', ' ')} "
        f"({float(profile_row.bearing_deg):.1f} deg; LA Basin crossing {float(profile_row.la_basin_intersection_km):.1f} km)"
    )
    fig.suptitle(title, x=0.48, y=0.986, fontsize=17.0, fontweight="bold", color=INK)

    residual_bounds = [[0.040, 0.750, 0.566, 0.125], [0.040, 0.595, 0.566, 0.125], [0.040, 0.440, 0.566, 0.125]]
    for idx, band in enumerate(BANDS):
        color = PASSBAND_COLORS[band]
        frame = band_frames[band]
        ax = fig.add_axes(residual_bounds[idx])
        style_axis(ax, spec.y_limits)
        ax.set_xlim(0.0, xmax)
        if frame.empty:
            ax.text(0.5, 0.50, "No stations", transform=ax.transAxes, ha="center", va="center", color=MUTED, fontsize=9)
        else:
            yerr = np.vstack(
                [
                    np.clip(frame["value"].to_numpy(float) - frame["q25"].to_numpy(float), 0.0, None),
                    np.clip(frame["q75"].to_numpy(float) - frame["value"].to_numpy(float), 0.0, None),
                ]
            )
            ax.errorbar(frame["projected_km"], frame["value"], yerr=yerr, fmt="none", ecolor="#aeb7c5", elinewidth=0.72, alpha=0.55, capsize=1.4, zorder=2)
            ax.scatter(
                frame["projected_km"],
                frame["value"],
                s=marker_size(frame["events"], event_min, event_max),
                facecolor=NEUTRAL_POINT,
                edgecolor=INK,
                linewidth=0.36,
                alpha=0.90,
                zorder=3,
            )
            cx, mean, lo, hi = moving_window(frame, xmax)
            finite = np.isfinite(mean) & np.isfinite(lo) & np.isfinite(hi)
            ax.fill_between(cx, lo, hi, where=finite, color=color, alpha=0.12, linewidth=0, zorder=2)
            ax.plot(cx, mean, color=color, linewidth=1.15, alpha=0.95, zorder=4)
            ax.text(
                0.985,
                0.88,
                f"{frame['station'].nunique():,} sta; {int(frame['events'].sum()):,} ev-wt",
                transform=ax.transAxes,
                ha="right",
                va="top",
                fontsize=7.4,
                color=MUTED,
                bbox={"facecolor": SURFACE, "edgecolor": "none", "alpha": 0.78, "pad": 1.0},
            )
        ax.text(
            0.010,
            0.88,
            band,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=9.0,
            fontweight="bold",
            color=INK,
            bbox={"facecolor": SURFACE, "edgecolor": "none", "alpha": 0.82, "pad": 1.2},
            zorder=5,
        )
        if idx < 2:
            ax.tick_params(labelbottom=False)
        else:
            ax.set_xlabel("Distance along profile (km)", fontsize=9.0, color=INK, labelpad=2)
    fig.text(0.016, 0.628, spec.y_label, rotation=90, ha="center", va="center", fontsize=10.0, fontweight="bold", color=INK)

    map_ax = fig.add_axes([0.632, 0.695, 0.345, 0.255])
    draw_map(
        map_ax,
        regions=regions,
        sections=sections,
        profile_id=profile_id,
        stations=station_frame,
        events=events,
        basemap_cache_dir=basemap_cache_dir,
        title=f"{profile_id} map: profile line, stations, and events",
    )

    def plot_scatter(ax: plt.Axes, x_col: str, x_label: str, show_legend: bool = False) -> None:
        style_axis(ax, spec.y_limits)
        all_x: list[np.ndarray] = []
        title_parts: list[str] = []
        for band, color in PASSBAND_COLORS.items():
            data = band_frames[band].dropna(subset=[x_col, "value", "events"]).copy()
            if data.empty:
                continue
            all_x.append(data[x_col].to_numpy(float))
            r, n = weighted_r(data[x_col].to_numpy(float), data["value"].to_numpy(float), data["events"].to_numpy(float))
            title_parts.append(f"{band}: r={r:+.2f} (n={n})" if np.isfinite(r) else f"{band}: n={n}")
            ax.scatter(data[x_col], data["value"], s=20, color=color, alpha=0.17, edgecolors="none", zorder=2)
            bx, by, blo, bhi = binned_curve(data, x_col)
            if bx.size:
                ax.fill_between(bx, blo, bhi, color=color, alpha=0.10, linewidth=0, zorder=3)
                ax.plot(bx, by, color=color, marker="o", markersize=3.0, linewidth=1.05, alpha=0.95, zorder=4)
            fit = weighted_linear_fit(data[x_col].to_numpy(float), data["value"].to_numpy(float), data["events"].to_numpy(float))
            if fit is not None:
                a, b = fit
                xs = np.linspace(float(np.nanmin(data[x_col])), float(np.nanmax(data[x_col])), 80)
                ax.plot(xs, a + b * xs, color=color, linestyle="--", linewidth=0.85, alpha=0.70, zorder=3.5)
        ax.set_xlabel(x_label, fontsize=9.0, color=INK, labelpad=2)
        ax.set_ylabel("Residual" if not spec.raw_cc else "Original CC", fontsize=9.0, color=INK, labelpad=2)
        ax.set_title("   ".join(title_parts), fontsize=7.8, color=MUTED, pad=4, loc="left")
        if all_x:
            finite = np.concatenate([values[np.isfinite(values)] for values in all_x])
            if finite.size:
                lo = float(np.nanmin(finite))
                hi = float(np.nanmax(finite))
                margin = 0.07 * (hi - lo) if hi > lo else 0.5
                ax.set_xlim(lo - margin, hi + margin)
        if show_legend:
            handles = [Line2D([0], [0], color=color, marker="o", markersize=4.0, linewidth=1.05, label=band) for band, color in PASSBAND_COLORS.items()]
            handles.extend(
                [
                    Line2D([0], [0], color="#4c5563", linewidth=1.05, label="binned weighted mean"),
                    Line2D([0], [0], color="#4c5563", linewidth=0.85, linestyle="--", label="weighted linear fit"),
                ]
            )
            ax.legend(handles=handles, loc="lower right", bbox_to_anchor=(1.0, -0.02), fontsize=7.4, frameon=True, borderpad=0.35, labelspacing=0.25)

    plot_scatter(fig.add_axes([0.642, 0.365, 0.340, 0.250]), "max_abs_vs_gradient_depth_km", "Depth of maximum |vertical Vs gradient| (km)")
    plot_scatter(
        fig.add_axes([0.642, 0.073, 0.340, 0.250]),
        "max_abs_vs_gradient_strength",
        "Maximum |vertical Vs gradient| ((km/s)/km)",
        show_legend=True,
    )
    add_model_crops(fig, model_key, profile_id)
    fig.text(
        0.040,
        0.006,
        f"Profile moving-average support: >=3 stations and >=15 event-weight within +/-{STATION_CORRIDOR_KM:g} km. Scatter bins use fixed equal-width bins with >=2 stations and >=8 event-weight; dashed lines are weighted linear fits.",
        fontsize=8.2,
        color=MUTED,
        ha="left",
        va="bottom",
    )
    fig.savefig(out_png, dpi=190)
    pdf.savefig(fig)
    plt.close(fig)


def prepare_projected_frames(model_key: str, spec: MetricSpec, raw: pd.DataFrame, sections: pd.DataFrame, model_ref: dict[str, pd.DataFrame]) -> tuple[dict[tuple[str, str], pd.DataFrame], dict[str, pd.DataFrame]]:
    pairs = collapse_components(raw)
    band_rows = {band: pairs.loc[pairs["band"].eq(band)].dropna(subset=[spec.value_column]).copy() for band in BANDS}
    station_summaries = {band: station_values(band_rows[band], spec.value_column) for band in BANDS}
    projected: dict[tuple[str, str], pd.DataFrame] = {}
    for _, row in sections.iterrows():
        profile_id = str(row.profile_id)
        line = section_line(row)
        ref = model_ref.get(profile_id, pd.DataFrame())
        for band in BANDS:
            frame = project_stations(line, station_summaries[band])
            frame = add_model_properties(frame, ref)
            projected[(profile_id, band)] = frame
    return projected, band_rows


def render_model_metric(
    *,
    model_key: str,
    metric: str,
    metrics_path: Path,
    regions: list,
    output_dir: Path,
) -> dict[str, object]:
    spec = metric_spec(metric)
    model_label = MODEL_LABELS[model_key]
    sections = load_section_table(model_key)
    model_ref = load_model_property_reference(model_key)
    raw = read_metric_rows(metrics_path, model_key=model_key, metric=metric)
    projected, band_rows = prepare_projected_frames(model_key, spec, raw, sections, model_ref)

    metric_slug = METRIC_OUTPUT[metric]
    figures_dir = output_dir / "figures" / model_key / metric_slug
    pdf_dir = output_dir / "pdfs"
    tables_dir = output_dir / "tables" / model_key / metric_slug
    basemap_cache_dir = output_dir / "basemap_cache"
    for directory in (figures_dir, pdf_dir, tables_dir, basemap_cache_dir):
        directory.mkdir(parents=True, exist_ok=True)

    projected_rows = []
    for (profile_id, band), frame in projected.items():
        if frame.empty:
            continue
        out = frame.copy()
        out.insert(0, "profile_id", profile_id)
        out.insert(1, "band", band)
        projected_rows.append(out)
    projected_path = tables_dir / f"{model_key}_{metric_slug}_projected_stations.csv"
    if projected_rows:
        pd.concat(projected_rows, ignore_index=True).to_csv(projected_path, index=False)
    else:
        pd.DataFrame().to_csv(projected_path, index=False)

    all_station_frames = [frame[["station", "sta_lon", "sta_lat"]] for frame in projected.values() if not frame.empty]
    overview_stations = pd.concat(all_station_frames, ignore_index=True).drop_duplicates("station") if all_station_frames else pd.DataFrame(columns=["station", "sta_lon", "sta_lat"])
    station_ids = set(overview_stations["station"].astype(str))
    all_events = (
        pd.concat([rows for rows in band_rows.values() if not rows.empty], ignore_index=True)
        .loc[lambda data: data["station"].astype(str).isin(station_ids), ["event_id", "event_lon", "event_lat"]]
        .dropna()
        .drop_duplicates("event_id")
        if station_ids
        else pd.DataFrame(columns=["event_id", "event_lon", "event_lat"])
    )

    pdf_path = pdf_dir / f"{model_key}_{metric_slug}_profile_split_layout.pdf"
    rendered_pages: list[str] = []
    with PdfPages(pdf_path) as pdf:
        overview_path = figures_dir / f"{model_key}_{metric_slug}_00_candidate_lines_map.png"
        render_overview_page(
            pdf=pdf,
            out_png=overview_path,
            regions=regions,
            sections=sections,
            stations=overview_stations,
            events=all_events,
            model_label=model_label,
            spec=spec,
            basemap_cache_dir=basemap_cache_dir,
        )
        rendered_pages.append(str(overview_path))
        for _, profile_row in sections.iterrows():
            profile_id = str(profile_row.profile_id)
            out_png = figures_dir / f"{model_key}_{metric_slug}_{profile_id}.png"
            render_profile_page(
                pdf=pdf,
                out_png=out_png,
                model_key=model_key,
                model_label=model_label,
                spec=spec,
                profile_row=profile_row,
                sections=sections,
                regions=regions,
                band_frames={band: projected[(profile_id, band)] for band in BANDS},
                band_rows=band_rows,
                basemap_cache_dir=basemap_cache_dir,
            )
            rendered_pages.append(str(out_png))

    manifest = {
        "model_key": model_key,
        "model": MODEL_IDS[model_key],
        "model_label": model_label,
        "metric": metric,
        "metric_slug": metric_slug,
        "value_column": spec.value_column,
        "bands": list(BANDS),
        "component_filter": ["R", "T"],
        "station_corridor_km": STATION_CORRIDOR_KM,
        "inputs": {"metrics": str(metrics_path)},
        "outputs": {"pdf": str(pdf_path), "pages": rendered_pages, "projected_stations": str(projected_path)},
        "raw_rows": int(len(raw)),
    }
    manifest_path = tables_dir / f"{model_key}_{metric_slug}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return {"pdf": str(pdf_path), "manifest": str(manifest_path), "pages": len(rendered_pages), "raw_rows": int(len(raw))}


def main(argv: Sequence[str] | None = None) -> int:
    global STATION_CORRIDOR_KM
    args = parse_args(argv)
    STATION_CORRIDOR_KM = float(args.station_corridor_km)
    set_plot_theme()
    output_dir = args.output_dir.expanduser().resolve()
    regions = load_regions(args.regions.expanduser().resolve())
    summary_rows = []
    for model_key in args.models:
        for metric in args.metrics_focus:
            result = render_model_metric(
                model_key=model_key,
                metric=metric,
                metrics_path=args.metrics.expanduser().resolve(),
                regions=regions,
                output_dir=output_dir,
            )
            summary_rows.append({"model": model_key, "metric": metric, **result})
            print(result["pdf"])
    summary_path = output_dir / "manifest.csv"
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False)
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
