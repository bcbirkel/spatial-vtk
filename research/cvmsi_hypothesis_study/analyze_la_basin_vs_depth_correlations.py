#!/usr/bin/env python3
"""Correlate rotated LA Basin profile residuals with CVM-SI Vs-depth markers."""

from __future__ import annotations

import math
from pathlib import Path
import textwrap
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D
from pyproj import Transformer
from scipy.signal import savgol_filter
from scipy.stats import rankdata, spearmanr
from shapely.geometry import LineString, Point

from cvmsi_hypothesis_study import (
    COLORS,
    CVM_UTM,
    DEFAULT_MODEL_H5,
    DEFAULT_OUTPUT,
    DEFAULT_REGIONS,
    ModelSampler,
    load_regions,
    set_plot_theme,
)
from render_la_basin_axis_profile_sections import BANDS, build_profile_families


METRIC = "PGA"
CORRIDORS_KM = (5.0, 10.0, 15.0)
VS_THRESHOLDS_KM_S = (1.0, 2.5)
DEPTHS_KM = np.linspace(0.0, 15.0, 151)
PROFILE_DX_KM = 0.5
DERIVATIVE_SMOOTH_WINDOW_KM = 5.0
MIN_STATIONS = 8
BOOTSTRAP_SAMPLES = 500
RANDOM_SEED = 20260701
PROFILE_ORDER = [f"L{i}" for i in range(1, 6)] + [f"P{i}" for i in range(1, 6)]
PROFILE_COLORS = {
    "L1": "#2E4780",
    "L2": "#5477C4",
    "L3": "#A3BEFA",
    "L4": "#386411",
    "L5": "#71B436",
    "P1": "#736422",
    "P2": "#B8A037",
    "P3": "#804126",
    "P4": "#CC6F47",
    "P5": "#8A3A6F",
}
COMPARISON_ORDER = [
    "mean residual vs z(Vs=1.0)",
    "mean residual vs z(Vs=2.5)",
    "residual std vs z(Vs=1.0)",
    "residual std vs z(Vs=2.5)",
]
DERIVATIVE_PREDICTORS = [
    ("z1 slope", "depth_vs_1p0_slope", "z(Vs=1.0)", "slope", False),
    ("z1 |slope|", "depth_vs_1p0_abs_slope", "z(Vs=1.0)", "slope", True),
    ("z1 curvature", "depth_vs_1p0_curvature", "z(Vs=1.0)", "curvature", False),
    ("z1 |curvature|", "depth_vs_1p0_abs_curvature", "z(Vs=1.0)", "curvature", True),
    ("z2.5 slope", "depth_vs_2p5_slope", "z(Vs=2.5)", "slope", False),
    ("z2.5 |slope|", "depth_vs_2p5_abs_slope", "z(Vs=2.5)", "slope", True),
    ("z2.5 curvature", "depth_vs_2p5_curvature", "z(Vs=2.5)", "curvature", False),
    ("z2.5 |curvature|", "depth_vs_2p5_abs_curvature", "z(Vs=2.5)", "curvature", True),
]
DERIVATIVE_PREDICTOR_ORDER = [label for label, *_ in DERIVATIVE_PREDICTORS]
DERIVATIVE_COLUMNS = [column for _, column, *_ in DERIVATIVE_PREDICTORS]


def section_line_utm(start_ll: tuple[float, float], end_ll: tuple[float, float], transformer: Transformer) -> LineString:
    sx, sy = transformer.transform(*start_ll)
    ex, ey = transformer.transform(*end_ll)
    return LineString([(float(sx), float(sy)), (float(ex), float(ey))])


def station_residual_summary(pairs: pd.DataFrame) -> pd.DataFrame:
    subset = pairs.loc[pairs["metric"].eq(METRIC) & pairs["band"].isin([band for band, _ in BANDS])].copy()
    return (
        subset.groupby(["band", "station"], as_index=False)
        .agg(
            sta_lon=("sta_lon", "median"),
            sta_lat=("sta_lat", "median"),
            residual_mean=("log2_residual", "mean"),
            residual_median=("log2_residual", "median"),
            residual_std=("log2_residual", lambda value: float(value.std(ddof=1)) if len(value) >= 2 else np.nan),
            residual_q25=("log2_residual", lambda value: float(value.quantile(0.25))),
            residual_q75=("log2_residual", lambda value: float(value.quantile(0.75))),
            events=("event_id", "nunique"),
            records=("log2_residual", "size"),
        )
        .dropna(subset=["sta_lon", "sta_lat", "residual_mean"])
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


def sample_vs_depth_markers(
    sampler: ModelSampler,
    projected_points: pd.DataFrame,
) -> pd.DataFrame:
    if projected_points.empty:
        return projected_points.assign(depth_vs_1p0_km=np.nan, depth_vs_2p5_km=np.nan)
    xyz_rows: list[list[float]] = []
    for row in projected_points.itertuples(index=False):
        for depth_km in DEPTHS_KM:
            xyz_rows.append([float(row.profile_x), float(row.profile_y), -1000.0 * float(depth_km)])
    sampled = sampler.sample_xyz(np.asarray(xyz_rows, dtype=float))
    vs = sampled["vs"].to_numpy(dtype=float).reshape(len(projected_points), len(DEPTHS_KM)) / 1000.0
    out = projected_points.copy()
    out["depth_vs_1p0_km"] = [interpolate_depth_to_threshold(profile, 1.0) for profile in vs]
    out["depth_vs_2p5_km"] = [interpolate_depth_to_threshold(profile, 2.5) for profile in vs]
    return out


def build_profile_station_points(
    station_summary: pd.DataFrame,
    sections: list[tuple[str, tuple[float, float], tuple[float, float]]],
    metadata: pd.DataFrame,
    sampler: ModelSampler,
) -> pd.DataFrame:
    transformer = Transformer.from_crs("EPSG:4326", CVM_UTM, always_xy=True)
    station_xy = np.array(
        transformer.transform(
            station_summary["sta_lon"].to_numpy(dtype=float),
            station_summary["sta_lat"].to_numpy(dtype=float),
        )
    ).T
    profile_rows: list[pd.DataFrame] = []
    metadata_index = metadata.set_index("profile_id")
    for title, start_ll, end_ll in sections:
        profile_id = title.split()[0]
        line = section_line_utm(start_ll, end_ll, transformer)
        length_km = float(line.length / 1000.0)
        rows: list[dict[str, object]] = []
        for station_row, xy in zip(station_summary.itertuples(index=False), station_xy):
            point = Point(float(xy[0]), float(xy[1]))
            projected_m = float(line.project(point))
            projected_point = line.interpolate(projected_m)
            rows.append(
                {
                    "profile_id": profile_id,
                    "family": metadata_index.loc[profile_id, "family"],
                    "bearing_deg": float(metadata_index.loc[profile_id, "bearing_deg"]),
                    "band": station_row.band,
                    "station": station_row.station,
                    "sta_lon": station_row.sta_lon,
                    "sta_lat": station_row.sta_lat,
                    "projected_km": projected_m / 1000.0,
                    "profile_length_km": length_km,
                    "offset_km": point.distance(line) / 1000.0,
                    "profile_x": float(projected_point.x),
                    "profile_y": float(projected_point.y),
                    "residual_mean": station_row.residual_mean,
                    "residual_median": station_row.residual_median,
                    "residual_std": station_row.residual_std,
                    "residual_q25": station_row.residual_q25,
                    "residual_q75": station_row.residual_q75,
                    "events": station_row.events,
                    "records": station_row.records,
                }
            )
        profile_rows.append(pd.DataFrame(rows))
    all_points = pd.concat(profile_rows, ignore_index=True)
    depth_rows: list[pd.DataFrame] = []
    for profile_id, profile_points in all_points.groupby("profile_id", sort=False):
        unique_profile_points = (
            profile_points[["profile_id", "station", "profile_x", "profile_y"]]
            .drop_duplicates(["profile_id", "station"])
            .reset_index(drop=True)
        )
        depth_rows.append(sample_vs_depth_markers(sampler, unique_profile_points))
    depth_lookup = pd.concat(depth_rows, ignore_index=True)
    return all_points.merge(depth_lookup, on=["profile_id", "station", "profile_x", "profile_y"], how="left", validate="many_to_one")


def build_profile_depth_grid(
    sampler: ModelSampler,
    sections: list[tuple[str, tuple[float, float], tuple[float, float]]],
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    transformer = Transformer.from_crs("EPSG:4326", CVM_UTM, always_xy=True)
    metadata_index = metadata.set_index("profile_id")
    profile_frames: list[pd.DataFrame] = []
    for title, start_ll, end_ll in sections:
        profile_id = title.split()[0]
        line = section_line_utm(start_ll, end_ll, transformer)
        length_km = float(line.length / 1000.0)
        distances_km = np.arange(0.0, length_km + PROFILE_DX_KM * 0.5, PROFILE_DX_KM)
        if distances_km[-1] < length_km:
            distances_km = np.append(distances_km, length_km)
        rows: list[dict[str, object]] = []
        for distance_km in distances_km:
            point = line.interpolate(float(distance_km) * 1000.0)
            rows.append(
                {
                    "profile_id": profile_id,
                    "family": metadata_index.loc[profile_id, "family"],
                    "bearing_deg": float(metadata_index.loc[profile_id, "bearing_deg"]),
                    "distance_km": float(distance_km),
                    "profile_length_km": length_km,
                    "profile_x": float(point.x),
                    "profile_y": float(point.y),
                }
            )
        profile_frames.append(sample_vs_depth_markers(sampler, pd.DataFrame(rows)))
    return pd.concat(profile_frames, ignore_index=True)


def derivative_window_length(n_values: int) -> int:
    target = max(5, int(round(DERIVATIVE_SMOOTH_WINDOW_KM / PROFILE_DX_KM)))
    if target % 2 == 0:
        target += 1
    maximum = n_values if n_values % 2 == 1 else n_values - 1
    return max(3, min(target, maximum))


def smooth_depth_and_derivatives(distances_km: np.ndarray, depths_km: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    smoothed = np.full(depths_km.shape, np.nan, dtype=float)
    slope = np.full(depths_km.shape, np.nan, dtype=float)
    curvature = np.full(depths_km.shape, np.nan, dtype=float)
    valid = np.isfinite(distances_km) & np.isfinite(depths_km)
    if int(valid.sum()) < 4:
        return smoothed, slope, curvature
    x_valid = distances_km[valid]
    y_valid = depths_km[valid]
    in_range = (distances_km >= float(x_valid.min())) & (distances_km <= float(x_valid.max()))
    x_segment = distances_km[in_range]
    y_segment = np.interp(x_segment, x_valid, y_valid)
    if len(x_segment) >= 5:
        window_length = derivative_window_length(len(x_segment))
        if window_length >= 5:
            y_segment = savgol_filter(y_segment, window_length=window_length, polyorder=2, mode="interp")
    segment_slope = np.gradient(y_segment, x_segment)
    segment_curvature = np.gradient(segment_slope, x_segment)
    smoothed[in_range] = y_segment
    slope[in_range] = segment_slope
    curvature[in_range] = segment_curvature
    return smoothed, slope, curvature


def add_profile_derivatives(depth_grid: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    depth_markers = [
        ("depth_vs_1p0", "depth_vs_1p0_km"),
        ("depth_vs_2p5", "depth_vs_2p5_km"),
    ]
    for _, group in depth_grid.groupby("profile_id", sort=False):
        out = group.sort_values("distance_km").copy()
        distances_km = out["distance_km"].to_numpy(dtype=float)
        for prefix, depth_column in depth_markers:
            smoothed, slope, curvature = smooth_depth_and_derivatives(
                distances_km,
                out[depth_column].to_numpy(dtype=float),
            )
            out[f"{prefix}_smooth_km"] = smoothed
            out[f"{prefix}_slope"] = slope
            out[f"{prefix}_abs_slope"] = np.abs(slope)
            out[f"{prefix}_curvature"] = curvature
            out[f"{prefix}_abs_curvature"] = np.abs(curvature)
        frames.append(out)
    return pd.concat(frames, ignore_index=True)


def interpolate_profile_values(grid: pd.DataFrame, target_distances_km: np.ndarray, value_column: str) -> np.ndarray:
    x = grid["distance_km"].to_numpy(dtype=float)
    y = grid[value_column].to_numpy(dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    if int(valid.sum()) < 2:
        return np.full(target_distances_km.shape, np.nan, dtype=float)
    return np.interp(target_distances_km, x[valid], y[valid], left=np.nan, right=np.nan)


def attach_profile_derivatives(points: pd.DataFrame, profile_derivatives: pd.DataFrame) -> pd.DataFrame:
    derivative_lookup = {profile_id: group for profile_id, group in profile_derivatives.groupby("profile_id", sort=False)}
    frames: list[pd.DataFrame] = []
    for profile_id, group in points.groupby("profile_id", sort=False):
        out = group.copy()
        grid = derivative_lookup.get(profile_id)
        if grid is None or grid.empty:
            for column in DERIVATIVE_COLUMNS:
                out[column] = np.nan
        else:
            target_distances_km = out["projected_km"].to_numpy(dtype=float)
            for column in DERIVATIVE_COLUMNS:
                out[column] = interpolate_profile_values(grid, target_distances_km, column)
        frames.append(out)
    return pd.concat(frames, ignore_index=True)


def weighted_corr(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0.0)
    if int(valid.sum()) < MIN_STATIONS:
        return np.nan
    x = x[valid]
    y = y[valid]
    weights = weights[valid]
    if float(np.nanstd(x)) == 0.0 or float(np.nanstd(y)) == 0.0:
        return np.nan
    x_mean = float(np.average(x, weights=weights))
    y_mean = float(np.average(y, weights=weights))
    x_centered = x - x_mean
    y_centered = y - y_mean
    covariance = float(np.average(x_centered * y_centered, weights=weights))
    x_var = float(np.average(x_centered**2, weights=weights))
    y_var = float(np.average(y_centered**2, weights=weights))
    if x_var <= 0.0 or y_var <= 0.0:
        return np.nan
    return covariance / math.sqrt(x_var * y_var)


def weighted_spearman(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0.0)
    if int(valid.sum()) < MIN_STATIONS:
        return np.nan
    return weighted_corr(rankdata(x[valid]), rankdata(y[valid]), weights[valid])


def bootstrap_weighted_spearman(x: np.ndarray, y: np.ndarray, weights: np.ndarray, rng: np.random.Generator) -> tuple[float, float]:
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0.0)
    if int(valid.sum()) < MIN_STATIONS:
        return np.nan, np.nan
    x = x[valid]
    y = y[valid]
    weights = weights[valid]
    estimates: list[float] = []
    indices = np.arange(len(x))
    probabilities = weights / weights.sum()
    for _ in range(BOOTSTRAP_SAMPLES):
        sample = rng.choice(indices, size=len(indices), replace=True, p=probabilities)
        estimate = weighted_spearman(x[sample], y[sample], weights[sample])
        if np.isfinite(estimate):
            estimates.append(float(estimate))
    if len(estimates) < 20:
        return np.nan, np.nan
    return tuple(np.quantile(estimates, [0.025, 0.975]).astype(float))


def correlation_rows(points: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    rows: list[dict[str, object]] = []
    stat_columns = {
        "mean residual": "residual_mean",
        "residual std": "residual_std",
    }
    depth_columns = {
        "z(Vs=1.0)": "depth_vs_1p0_km",
        "z(Vs=2.5)": "depth_vs_2p5_km",
    }
    for corridor_km in CORRIDORS_KM:
        corridor_points = points.loc[points["offset_km"].le(corridor_km)].copy()
        for (profile_id, family, band), group in corridor_points.groupby(["profile_id", "family", "band"], sort=False):
            for residual_stat, residual_column in stat_columns.items():
                for depth_label, depth_column in depth_columns.items():
                    valid = group[[residual_column, depth_column, "events"]].replace([np.inf, -np.inf], np.nan).dropna()
                    valid = valid.loc[valid["events"].gt(0)]
                    n_stations = int(len(valid))
                    event_weight = int(valid["events"].sum()) if n_stations else 0
                    if n_stations >= MIN_STATIONS:
                        x = valid[depth_column].to_numpy(dtype=float)
                        y = valid[residual_column].to_numpy(dtype=float)
                        weights = valid["events"].to_numpy(dtype=float)
                        rho_pearson = weighted_corr(x, y, weights)
                        rho_spearman = weighted_spearman(x, y, weights)
                        ci_low, ci_high = bootstrap_weighted_spearman(x, y, weights, rng)
                        unweighted = spearmanr(x, y)
                        unweighted_p = float(unweighted.pvalue) if np.isfinite(unweighted.statistic) else np.nan
                    else:
                        rho_pearson = rho_spearman = ci_low = ci_high = unweighted_p = np.nan
                    rows.append(
                        {
                            "corridor_km": corridor_km,
                            "profile_id": profile_id,
                            "family": family,
                            "band": band,
                            "residual_stat": residual_stat,
                            "depth_marker": depth_label,
                            "comparison": f"{residual_stat} vs {depth_label}",
                            "weighted_pearson_r": rho_pearson,
                            "weighted_spearman_rho": rho_spearman,
                            "weighted_spearman_ci_low": ci_low,
                            "weighted_spearman_ci_high": ci_high,
                            "unweighted_spearman_p": unweighted_p,
                            "stations": n_stations,
                            "event_weight": event_weight,
                        }
                    )
    return pd.DataFrame(rows)


def summarize_correlations(correlations: pd.DataFrame) -> pd.DataFrame:
    valid = correlations.dropna(subset=["weighted_spearman_rho"]).copy()
    if valid.empty:
        return pd.DataFrame()
    return (
        valid.groupby(["band", "corridor_km", "residual_stat", "depth_marker", "comparison"], as_index=False)
        .agg(
            median_weighted_spearman=("weighted_spearman_rho", "median"),
            q25_weighted_spearman=("weighted_spearman_rho", lambda value: float(value.quantile(0.25))),
            q75_weighted_spearman=("weighted_spearman_rho", lambda value: float(value.quantile(0.75))),
            mean_abs_weighted_spearman=("weighted_spearman_rho", lambda value: float(np.mean(np.abs(value)))),
            profiles=("profile_id", "nunique"),
            min_stations=("stations", "min"),
            median_stations=("stations", "median"),
            total_event_weight=("event_weight", "sum"),
        )
    )


def derivative_correlation_rows(points: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED + 1)
    rows: list[dict[str, object]] = []
    stat_columns = {
        "mean residual": "residual_mean",
        "residual std": "residual_std",
    }
    for corridor_km in CORRIDORS_KM:
        corridor_points = points.loc[points["offset_km"].le(corridor_km)].copy()
        for (profile_id, family, band), group in corridor_points.groupby(["profile_id", "family", "band"], sort=False):
            for residual_stat, residual_column in stat_columns.items():
                for predictor_label, predictor_column, depth_marker, derivative_stat, is_absolute in DERIVATIVE_PREDICTORS:
                    valid = group[[residual_column, predictor_column, "events"]].replace([np.inf, -np.inf], np.nan).dropna()
                    valid = valid.loc[valid["events"].gt(0)]
                    n_stations = int(len(valid))
                    event_weight = int(valid["events"].sum()) if n_stations else 0
                    if n_stations >= MIN_STATIONS:
                        x = valid[predictor_column].to_numpy(dtype=float)
                        y = valid[residual_column].to_numpy(dtype=float)
                        weights = valid["events"].to_numpy(dtype=float)
                        rho_pearson = weighted_corr(x, y, weights)
                        rho_spearman = weighted_spearman(x, y, weights)
                        ci_low, ci_high = bootstrap_weighted_spearman(x, y, weights, rng)
                        unweighted = spearmanr(x, y)
                        unweighted_p = float(unweighted.pvalue) if np.isfinite(unweighted.statistic) else np.nan
                    else:
                        rho_pearson = rho_spearman = ci_low = ci_high = unweighted_p = np.nan
                    rows.append(
                        {
                            "corridor_km": corridor_km,
                            "profile_id": profile_id,
                            "family": family,
                            "band": band,
                            "residual_stat": residual_stat,
                            "predictor": predictor_label,
                            "predictor_column": predictor_column,
                            "depth_marker": depth_marker,
                            "derivative_stat": derivative_stat,
                            "absolute_value": bool(is_absolute),
                            "comparison": f"{residual_stat} vs {predictor_label}",
                            "weighted_pearson_r": rho_pearson,
                            "weighted_spearman_rho": rho_spearman,
                            "weighted_spearman_ci_low": ci_low,
                            "weighted_spearman_ci_high": ci_high,
                            "unweighted_spearman_p": unweighted_p,
                            "stations": n_stations,
                            "event_weight": event_weight,
                        }
                    )
    return pd.DataFrame(rows)


def summarize_derivative_correlations(correlations: pd.DataFrame) -> pd.DataFrame:
    valid = correlations.dropna(subset=["weighted_spearman_rho"]).copy()
    if valid.empty:
        return pd.DataFrame()
    return (
        valid.groupby(
            [
                "band",
                "corridor_km",
                "residual_stat",
                "predictor",
                "predictor_column",
                "depth_marker",
                "derivative_stat",
                "absolute_value",
                "comparison",
            ],
            as_index=False,
        )
        .agg(
            median_weighted_spearman=("weighted_spearman_rho", "median"),
            q25_weighted_spearman=("weighted_spearman_rho", lambda value: float(value.quantile(0.25))),
            q75_weighted_spearman=("weighted_spearman_rho", lambda value: float(value.quantile(0.75))),
            mean_abs_weighted_spearman=("weighted_spearman_rho", lambda value: float(np.mean(np.abs(value)))),
            profiles=("profile_id", "nunique"),
            min_stations=("stations", "min"),
            median_stations=("stations", "median"),
            total_event_weight=("event_weight", "sum"),
        )
    )


def ordered_pivot(data: pd.DataFrame, value_column: str) -> pd.DataFrame:
    pivot = data.pivot_table(index="comparison", columns="profile_id", values=value_column, aggfunc="first")
    return pivot.reindex(index=COMPARISON_ORDER, columns=PROFILE_ORDER)


def ordered_derivative_pivot(data: pd.DataFrame, value_column: str) -> pd.DataFrame:
    pivot = data.pivot_table(index="predictor", columns="profile_id", values=value_column, aggfunc="first")
    return pivot.reindex(index=DERIVATIVE_PREDICTOR_ORDER, columns=PROFILE_ORDER)


def plot_profile_heatmap(correlations: pd.DataFrame, output_path: Path) -> Path:
    band_labels = [band for band, _ in BANDS]
    fig, axes = plt.subplots(len(band_labels), len(CORRIDORS_KM), figsize=(20.0, 12.2), sharex=False, sharey=False)
    norm = TwoSlopeNorm(vmin=-1.0, vcenter=0.0, vmax=1.0)
    last_image = None
    for row_index, band in enumerate(band_labels):
        for col_index, corridor_km in enumerate(CORRIDORS_KM):
            ax = axes[row_index, col_index]
            subset = correlations.loc[
                correlations["band"].eq(band) & correlations["corridor_km"].eq(corridor_km)
            ]
            matrix = ordered_pivot(subset, "weighted_spearman_rho")
            values = matrix.to_numpy(dtype=float)
            masked = np.ma.masked_invalid(values)
            last_image = ax.imshow(masked, cmap="RdBu_r", norm=norm, aspect="auto")
            ax.set_title(f"{band}, station corridor <= {corridor_km:g} km", fontsize=12.5, fontweight="bold", pad=8)
            ax.set_xticks(np.arange(len(PROFILE_ORDER)))
            ax.set_xticklabels(PROFILE_ORDER, fontsize=9.5)
            ax.set_yticks(np.arange(len(COMPARISON_ORDER)))
            ax.set_yticklabels(COMPARISON_ORDER if col_index == 0 else [], fontsize=10)
            for y_index in range(values.shape[0]):
                for x_index in range(values.shape[1]):
                    value = values[y_index, x_index]
                    if np.isfinite(value):
                        color = "white" if abs(value) >= 0.58 else COLORS["ink"]
                        ax.text(x_index, y_index, f"{value:+.2f}", ha="center", va="center", fontsize=8.6, color=color)
            ax.tick_params(length=0)
            ax.set_xlabel("Profile" if row_index == len(band_labels) - 1 else "")
    assert last_image is not None
    cax = fig.add_axes([0.925, 0.18, 0.018, 0.66])
    cbar = fig.colorbar(last_image, cax=cax)
    cbar.set_label("Event-count-weighted Spearman rho", fontsize=11.5)
    fig.suptitle("LA Basin profile residuals vs CVM-SI Vs-depth markers", fontsize=17.5, fontweight="bold", y=0.985)
    fig.text(
        0.055,
        0.030,
        textwrap.fill(
            "Each station projected onto a rotated profile contributes one point. Residual means and standard deviations are computed across events at that station; correlations are weighted by station event count. Blank cells have fewer than 8 valid stations.",
            width=210,
        ),
        fontsize=10.5,
        color=COLORS["muted"],
    )
    fig.subplots_adjust(left=0.19, right=0.90, top=0.93, bottom=0.105, hspace=0.36, wspace=0.12)
    fig.savefig(output_path, dpi=210)
    plt.close(fig)
    return output_path


def plot_derivative_heatmap(correlations: pd.DataFrame, residual_stat: str, output_path: Path) -> Path:
    band_labels = [band for band, _ in BANDS]
    fig, axes = plt.subplots(len(band_labels), len(CORRIDORS_KM), figsize=(20.5, 14.4), sharex=False, sharey=False)
    norm = TwoSlopeNorm(vmin=-1.0, vcenter=0.0, vmax=1.0)
    last_image = None
    for row_index, band in enumerate(band_labels):
        for col_index, corridor_km in enumerate(CORRIDORS_KM):
            ax = axes[row_index, col_index]
            subset = correlations.loc[
                correlations["band"].eq(band)
                & correlations["corridor_km"].eq(corridor_km)
                & correlations["residual_stat"].eq(residual_stat)
            ]
            matrix = ordered_derivative_pivot(subset, "weighted_spearman_rho")
            values = matrix.to_numpy(dtype=float)
            masked = np.ma.masked_invalid(values)
            last_image = ax.imshow(masked, cmap="RdBu_r", norm=norm, aspect="auto")
            ax.set_title(f"{band}, station corridor <= {corridor_km:g} km", fontsize=12.7, fontweight="bold", pad=8)
            ax.set_xticks(np.arange(len(PROFILE_ORDER)))
            ax.set_xticklabels(PROFILE_ORDER, fontsize=10.2)
            ax.set_yticks(np.arange(len(DERIVATIVE_PREDICTOR_ORDER)))
            ax.set_yticklabels(DERIVATIVE_PREDICTOR_ORDER if col_index == 0 else [], fontsize=10.5)
            for y_index in range(values.shape[0]):
                for x_index in range(values.shape[1]):
                    value = values[y_index, x_index]
                    if np.isfinite(value):
                        color = "white" if abs(value) >= 0.58 else COLORS["ink"]
                        ax.text(x_index, y_index, f"{value:+.2f}", ha="center", va="center", fontsize=8.5, color=color)
            ax.tick_params(length=0)
            ax.set_xlabel("Profile" if row_index == len(band_labels) - 1 else "")
    assert last_image is not None
    cax = fig.add_axes([0.925, 0.17, 0.018, 0.67])
    cbar = fig.colorbar(last_image, cax=cax)
    cbar.set_label("Event-count-weighted Spearman rho", fontsize=12.0)
    fig.suptitle(
        f"LA Basin {residual_stat} vs CVM-SI z1/z2.5 profile slope and curvature",
        fontsize=17.5,
        fontweight="bold",
        y=0.985,
    )
    fig.text(
        0.055,
        0.030,
        textwrap.fill(
            "Depth markers are sampled every 0.5 km along each profile, smoothed with a 5 km Savitzky-Golay window, and differentiated along profile distance. Signed slope/curvature retain profile orientation; absolute values test steepness or bending independent of direction. Blank cells have fewer than 8 valid stations.",
            width=215,
        ),
        fontsize=10.8,
        color=COLORS["muted"],
    )
    fig.subplots_adjust(left=0.18, right=0.90, top=0.93, bottom=0.105, hspace=0.34, wspace=0.12)
    fig.savefig(output_path, dpi=210)
    plt.close(fig)
    return output_path


def plot_corridor_sensitivity(summary: pd.DataFrame, output_path: Path) -> Path:
    band_labels = [band for band, _ in BANDS]
    stat_labels = ["mean residual", "residual std"]
    threshold_colors = {"z(Vs=1.0)": COLORS["blue"], "z(Vs=2.5)": COLORS["gold"]}
    fig, axes = plt.subplots(len(band_labels), len(stat_labels), figsize=(15.5, 10.2), sharex=True, sharey=True)
    for row_index, band in enumerate(band_labels):
        for col_index, residual_stat in enumerate(stat_labels):
            ax = axes[row_index, col_index]
            subset = summary.loc[summary["band"].eq(band) & summary["residual_stat"].eq(residual_stat)].copy()
            for depth_marker, color in threshold_colors.items():
                line = subset.loc[subset["depth_marker"].eq(depth_marker)].sort_values("corridor_km")
                if line.empty:
                    continue
                x = line["corridor_km"].to_numpy(dtype=float)
                y = line["median_weighted_spearman"].to_numpy(dtype=float)
                low = line["q25_weighted_spearman"].to_numpy(dtype=float)
                high = line["q75_weighted_spearman"].to_numpy(dtype=float)
                ax.plot(x, y, color=color, marker="o", linewidth=2.0, label=depth_marker)
                ax.fill_between(x, low, high, color=color, alpha=0.16, linewidth=0)
            ax.axhline(0.0, color=COLORS["ink"], linewidth=1.0, alpha=0.65)
            ax.grid(True, color=COLORS["grid"], linewidth=0.8, alpha=0.8)
            ax.set_title(f"{band}: {residual_stat}", fontsize=12.5, fontweight="bold")
            ax.set_ylim(-1.0, 1.0)
            ax.set_xticks(CORRIDORS_KM)
            if row_index == len(band_labels) - 1:
                ax.set_xlabel("Station corridor half-width (km)")
            if col_index == 0:
                ax.set_ylabel("Median profile rho")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=True, fontsize=10.5, bbox_to_anchor=(0.53, 0.955))
    fig.suptitle("Sensitivity of residual-depth correlations to station corridor width", fontsize=17.5, fontweight="bold", y=0.99)
    fig.text(
        0.07,
        0.025,
        "Lines show median event-count-weighted Spearman rho across the ten rotated LA Basin profiles; bands show the interquartile range across profiles.",
        fontsize=10.5,
        color=COLORS["muted"],
    )
    fig.subplots_adjust(left=0.08, right=0.985, top=0.90, bottom=0.10, hspace=0.38, wspace=0.12)
    fig.savefig(output_path, dpi=210)
    plt.close(fig)
    return output_path


def event_marker_size(events: object, *, minimum: float = 18.0, maximum: float = 96.0) -> np.ndarray:
    values = np.asarray(events, dtype=float)
    finite = np.isfinite(values)
    if not finite.any():
        return np.full(values.shape, minimum)
    lo = float(np.nanmin(values[finite]))
    hi = float(np.nanmax(values[finite]))
    if hi <= lo:
        return np.full(values.shape, 0.5 * (minimum + maximum))
    scaled = np.clip((values - lo) / (hi - lo), 0.0, 1.0)
    return minimum + (maximum - minimum) * np.sqrt(scaled)


def plot_residual_depth_scatter(points: pd.DataFrame, corridor_km: float, output_path: Path) -> Path:
    band_labels = [band for band, _ in BANDS]
    depth_columns = [
        ("depth_vs_1p0_km", "z(Vs=1.0) depth (km)"),
        ("depth_vs_2p5_km", "z(Vs=2.5) depth (km)"),
    ]
    subset = points.loc[points["offset_km"].le(corridor_km)].replace([np.inf, -np.inf], np.nan).copy()
    subset = subset.dropna(subset=["residual_mean", "events"])
    residual_values = subset["residual_mean"].to_numpy(dtype=float)
    if residual_values.size:
        y_lo = float(np.nanquantile(residual_values, 0.01))
        y_hi = float(np.nanquantile(residual_values, 0.99))
        y_pad = max(0.35, 0.10 * (y_hi - y_lo))
        y_limits = (max(-4.0, y_lo - y_pad), min(4.8, y_hi + y_pad))
    else:
        y_limits = (-2.0, 2.0)
    fig, axes = plt.subplots(len(band_labels), len(depth_columns), figsize=(15.8, 11.2), sharey=True)
    for row_index, band in enumerate(band_labels):
        band_data = subset.loc[subset["band"].eq(band)]
        for col_index, (depth_column, depth_label) in enumerate(depth_columns):
            ax = axes[row_index, col_index]
            axis_data = band_data.dropna(subset=[depth_column]).copy()
            for profile_id in PROFILE_ORDER:
                profile_data = axis_data.loc[axis_data["profile_id"].eq(profile_id)]
                if profile_data.empty:
                    continue
                ax.scatter(
                    profile_data[depth_column],
                    profile_data["residual_mean"],
                    s=event_marker_size(profile_data["events"], minimum=16.0, maximum=82.0),
                    color=PROFILE_COLORS[profile_id],
                    edgecolor="white",
                    linewidth=0.35,
                    alpha=0.58,
                    label=profile_id,
                )
            ax.axhline(0.0, color=COLORS["ink"], linewidth=1.0, alpha=0.65)
            ax.grid(True, color=COLORS["grid"], linewidth=0.75, alpha=0.78)
            ax.set_ylim(*y_limits)
            if not axis_data.empty:
                x_values = axis_data[depth_column].to_numpy(dtype=float)
                x_lo = float(np.nanmin(x_values))
                x_hi = float(np.nanmax(x_values))
                x_pad = max(0.12, 0.06 * (x_hi - x_lo))
                ax.set_xlim(x_lo - x_pad, x_hi + x_pad)
            ax.set_title(f"{band}: {depth_label}", fontsize=12.2, fontweight="bold")
            if row_index == len(band_labels) - 1:
                ax.set_xlabel(depth_label)
            if col_index == 0:
                ax.set_ylabel("Station mean residual\nlog2(obs/syn)")
            support = int(axis_data["station"].nunique()) if not axis_data.empty else 0
            events = int(axis_data["events"].sum()) if not axis_data.empty else 0
            ax.text(
                0.02,
                0.96,
                f"{support} stations; event weight {events}",
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=9.0,
                color=COLORS["muted"],
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.72, "pad": 2.0},
            )
    profile_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markersize=6.5,
            markerfacecolor=PROFILE_COLORS[profile_id],
            markeredgecolor="white",
            label=profile_id,
        )
        for profile_id in PROFILE_ORDER
    ]
    size_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markersize=marker_size,
            markerfacecolor="white",
            markeredgecolor=COLORS["ink"],
            label=label,
        )
        for marker_size, label in [(4.5, "low support"), (7.0, "medium"), (9.5, "high")]
    ]
    profile_legend = fig.legend(
        profile_handles,
        [handle.get_label() for handle in profile_handles],
        title="Profile",
        ncol=10,
        loc="upper center",
        bbox_to_anchor=(0.50, 0.955),
        frameon=True,
        fontsize=9.2,
        title_fontsize=9.5,
    )
    fig.add_artist(profile_legend)
    fig.legend(
        size_handles,
        [handle.get_label() for handle in size_handles],
        title="Event count",
        ncol=3,
        loc="upper right",
        bbox_to_anchor=(0.985, 0.955),
        frameon=True,
        fontsize=9.0,
        title_fontsize=9.2,
    )
    fig.suptitle(
        f"Station residuals vs CVM-SI Vs-depth markers, corridor <= {corridor_km:g} km",
        fontsize=17.0,
        fontweight="bold",
        y=0.992,
    )
    fig.text(
        0.075,
        0.026,
        textwrap.fill(
            "Each point is a station projected onto one rotated LA Basin profile for one passband. The y-axis is the station mean PGA residual across available events; point area scales with station event count and color identifies the profile.",
            width=180,
        ),
        fontsize=10.2,
        color=COLORS["muted"],
    )
    fig.subplots_adjust(left=0.09, right=0.985, top=0.875, bottom=0.10, hspace=0.35, wspace=0.12)
    fig.savefig(output_path, dpi=210)
    plt.close(fig)
    return output_path


def write_markdown_summary(summary: pd.DataFrame, output_path: Path) -> Path:
    rows: list[str] = [
        "# LA Basin Vs-Depth Residual Correlation Summary",
        "",
        "Statistic: event-count-weighted Spearman rho. Each value below is the median across the ten rotated LA Basin profiles.",
        "",
        "| Band | Corridor km | Mean vs z(Vs=1.0) | Mean vs z(Vs=2.5) | Std vs z(Vs=1.0) | Std vs z(Vs=2.5) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    lookup = summary.set_index(["band", "corridor_km", "comparison"])["median_weighted_spearman"]
    for band, _ in BANDS:
        for corridor_km in CORRIDORS_KM:
            values = []
            for comparison in COMPARISON_ORDER:
                value = lookup.get((band, corridor_km, comparison), np.nan)
                values.append("" if not np.isfinite(value) else f"{value:+.2f}")
            rows.append(f"| {band} | {corridor_km:g} | " + " | ".join(values) + " |")
    output_path.write_text("\n".join(rows) + "\n")
    return output_path


def write_derivative_markdown_summary(summary: pd.DataFrame, output_path: Path) -> Path:
    rows: list[str] = [
        "# LA Basin Vs-Depth Slope and Curvature Residual Correlation Summary",
        "",
        "Statistic: event-count-weighted Spearman rho. Each value below is the median across the ten rotated LA Basin profiles.",
        "Depth markers were sampled every 0.5 km along each profile, smoothed with a 5 km Savitzky-Golay window, and differentiated along profile distance.",
        "",
    ]
    if summary.empty:
        rows.append("No valid derivative correlations were available.")
        output_path.write_text("\n".join(rows) + "\n")
        return output_path
    lookup = summary.set_index(["band", "corridor_km", "residual_stat", "predictor"])["median_weighted_spearman"]
    for residual_stat in ["mean residual", "residual std"]:
        rows.extend(
            [
                f"## {residual_stat.title()}",
                "",
                "| Band | Corridor km | "
                + " | ".join(DERIVATIVE_PREDICTOR_ORDER)
                + " |",
                "|---|---:|" + "|".join(["---:"] * len(DERIVATIVE_PREDICTOR_ORDER)) + "|",
            ]
        )
        for band, _ in BANDS:
            for corridor_km in CORRIDORS_KM:
                values = []
                for predictor in DERIVATIVE_PREDICTOR_ORDER:
                    value = lookup.get((band, corridor_km, residual_stat, predictor), np.nan)
                    values.append("" if not np.isfinite(value) else f"{value:+.2f}")
                rows.append(f"| {band} | {corridor_km:g} | " + " | ".join(values) + " |")
        rows.append("")
    output_path.write_text("\n".join(rows) + "\n")
    return output_path


def main() -> int:
    set_plot_theme()
    output_dir = DEFAULT_OUTPUT
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    report_dir = output_dir / "report"
    for directory in (tables_dir, figures_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)

    pairs = pd.read_parquet(tables_dir / "pairs.parquet")
    station_summary = station_residual_summary(pairs)
    regions = load_regions(DEFAULT_REGIONS)
    long_sections, perpendicular_sections, metadata = build_profile_families(regions)
    sections = [*long_sections, *perpendicular_sections]
    sampler = ModelSampler(DEFAULT_MODEL_H5, node_stride=2)
    points = build_profile_station_points(station_summary, sections, metadata, sampler)
    profile_derivatives = add_profile_derivatives(build_profile_depth_grid(sampler, sections, metadata))
    points_with_derivatives = attach_profile_derivatives(points, profile_derivatives)

    station_points_path = tables_dir / "la_basin_vs_depth_station_points.parquet"
    station_points_csv_path = tables_dir / "la_basin_vs_depth_station_points.csv"
    profile_derivatives_path = tables_dir / "la_basin_vs_depth_profile_derivatives.csv"
    station_points_derivative_path = tables_dir / "la_basin_vs_depth_station_points_with_derivatives.parquet"
    station_points_derivative_csv_path = tables_dir / "la_basin_vs_depth_station_points_with_derivatives.csv"
    correlations_path = tables_dir / "la_basin_vs_depth_correlations.csv"
    summary_path = tables_dir / "la_basin_vs_depth_corridor_summary.csv"
    derivative_correlations_path = tables_dir / "la_basin_vs_depth_derivative_correlations.csv"
    derivative_summary_path = tables_dir / "la_basin_vs_depth_derivative_corridor_summary.csv"
    markdown_path = report_dir / "la_basin_vs_depth_correlation_summary.md"
    derivative_markdown_path = report_dir / "la_basin_vs_depth_derivative_correlation_summary.md"
    points.to_parquet(station_points_path, index=False)
    points.to_csv(station_points_csv_path, index=False)
    profile_derivatives.to_csv(profile_derivatives_path, index=False)
    points_with_derivatives.to_parquet(station_points_derivative_path, index=False)
    points_with_derivatives.to_csv(station_points_derivative_csv_path, index=False)
    correlations = correlation_rows(points)
    correlations.to_csv(correlations_path, index=False)
    summary = summarize_correlations(correlations)
    summary.to_csv(summary_path, index=False)
    write_markdown_summary(summary, markdown_path)
    derivative_correlations = derivative_correlation_rows(points_with_derivatives)
    derivative_correlations.to_csv(derivative_correlations_path, index=False)
    derivative_summary = summarize_derivative_correlations(derivative_correlations)
    derivative_summary.to_csv(derivative_summary_path, index=False)
    write_derivative_markdown_summary(derivative_summary, derivative_markdown_path)

    heatmap_path = figures_dir / "fig_06m_la_basin_vs_depth_profile_correlations.png"
    sensitivity_path = figures_dir / "fig_06n_la_basin_vs_depth_corridor_sensitivity.png"
    derivative_mean_path = figures_dir / "fig_06r_la_basin_vs_depth_derivative_mean_correlations.png"
    derivative_std_path = figures_dir / "fig_06s_la_basin_vs_depth_derivative_std_correlations.png"
    plot_profile_heatmap(correlations, heatmap_path)
    plot_corridor_sensitivity(summary, sensitivity_path)
    plot_derivative_heatmap(derivative_correlations, "mean residual", derivative_mean_path)
    plot_derivative_heatmap(derivative_correlations, "residual std", derivative_std_path)
    scatter_paths = [
        figures_dir / "fig_06o_la_basin_vs_depth_residual_scatter_5km.png",
        figures_dir / "fig_06p_la_basin_vs_depth_residual_scatter_10km.png",
        figures_dir / "fig_06q_la_basin_vs_depth_residual_scatter_15km.png",
    ]
    for corridor_km, scatter_path in zip(CORRIDORS_KM, scatter_paths):
        plot_residual_depth_scatter(points, corridor_km, scatter_path)

    for path in [
        station_points_path,
        station_points_csv_path,
        profile_derivatives_path,
        station_points_derivative_path,
        station_points_derivative_csv_path,
        correlations_path,
        summary_path,
        derivative_correlations_path,
        derivative_summary_path,
        markdown_path,
        derivative_markdown_path,
        heatmap_path,
        sensitivity_path,
        derivative_mean_path,
        derivative_std_path,
        *scatter_paths,
    ]:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
