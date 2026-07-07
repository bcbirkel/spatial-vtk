#!/usr/bin/env python3
"""Correlate LA Basin residuals with local vertical CVM-SI Vs gradients."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.stats import rankdata, spearmanr
from shapely.geometry import LineString, Point

from cvmsi_hypothesis_study import (
    COLORS,
    CVM_UTM,
    DEFAULT_METRICS,
    DEFAULT_MODEL_H5,
    DEFAULT_OUTPUT,
    DEFAULT_REGIONS,
    ModelSampler,
    load_regions,
    set_plot_theme,
)
from render_la_basin_axis_profile_sections import BANDS, build_profile_families
from render_la_basin_metric_profile_atlas import PanelSpec, collapse_components, load_metric_rows


CORRIDORS_KM = (5.0, 10.0, 15.0)
DEPTHS_KM = np.linspace(0.0, 15.0, 151)
VS_GRADIENT_WINDOW_HALF_KM = 0.5
MIN_STATIONS = 8
BOOTSTRAP_SAMPLES = 0
RANDOM_SEED = 20260701

PREDICTORS = [
    ("mean signed gradient 0-1 km", "vsgrad_signed_mean_0_1km", False),
    ("mean signed gradient 0-2.5 km", "vsgrad_signed_mean_0_2p5km", False),
    ("mean signed gradient 0-5 km", "vsgrad_signed_mean_0_5km", False),
    ("mean |gradient| 0-1 km", "vsgrad_abs_mean_0_1km", True),
    ("mean |gradient| 0-2.5 km", "vsgrad_abs_mean_0_2p5km", True),
    ("mean |gradient| 0-5 km", "vsgrad_abs_mean_0_5km", True),
    ("max positive gradient 0-3 km", "vsgrad_positive_max_0_3km", False),
    ("max |gradient| 0-3 km", "vsgrad_abs_max_0_3km", True),
]


def residual_panel_specs() -> list[PanelSpec]:
    panels: list[PanelSpec] = []
    for metric in ("PGA", "PGV", "arias_duration"):
        for band, _ in BANDS:
            panels.append(
                PanelSpec(
                    label=band,
                    metric=metric,
                    band=band,
                    value_column="log2_residual",
                    period_s=None,
                    value_label=f"{metric} residual",
                )
            )
    for period, band in ((1.0, "1-2 sec"), (2.0, "2-3 sec"), (3.0, "3-5 sec"), (4.0, "3-5 sec"), (5.0, "3-5 sec")):
        panels.append(
            PanelSpec(
                label=f"PSA {period:g} s",
                metric="PSA",
                band=band,
                value_column="log2_residual",
                period_s=period,
                value_label=f"PSA {period:g} s residual",
            )
        )
    return panels


def section_line_utm(start_ll: tuple[float, float], end_ll: tuple[float, float], transformer: Transformer) -> LineString:
    sx, sy = transformer.transform(*start_ll)
    ex, ey = transformer.transform(*end_ll)
    return LineString([(float(sx), float(sy)), (float(ex), float(ey))])


def station_residual_summary(pairs: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for panel in residual_panel_specs():
        subset = pairs.loc[pairs["metric"].eq(panel.metric) & pairs["band"].eq(panel.band)].copy()
        if panel.period_s is not None:
            subset = subset.loc[np.isclose(subset["period_s"].to_numpy(dtype=float), panel.period_s)]
        if subset.empty:
            continue
        grouped = (
            subset.groupby("station", as_index=False)
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
        grouped["metric"] = panel.metric
        grouped["band"] = panel.band
        grouped["period_s"] = panel.period_s
        grouped["metric_panel"] = f"PSA {panel.period_s:g} s" if panel.period_s is not None else f"{panel.metric} {panel.band}"
        frames.append(grouped)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_projected_station_points(
    station_summary: pd.DataFrame,
    sections: list[tuple[str, tuple[float, float], tuple[float, float]]],
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    transformer = Transformer.from_crs("EPSG:4326", CVM_UTM, always_xy=True)
    station_xy = np.array(
        transformer.transform(
            station_summary["sta_lon"].to_numpy(dtype=float),
            station_summary["sta_lat"].to_numpy(dtype=float),
        )
    ).T
    metadata_index = metadata.set_index("profile_id")
    frames: list[pd.DataFrame] = []
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
                    "metric": station_row.metric,
                    "metric_panel": station_row.metric_panel,
                    "band": station_row.band,
                    "period_s": station_row.period_s,
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
        frames.append(pd.DataFrame(rows))
    return pd.concat(frames, ignore_index=True)


def local_vertical_gradient(vs_km_s: np.ndarray) -> np.ndarray:
    gradients = np.full(vs_km_s.shape, np.nan, dtype=float)
    for index, center_depth_km in enumerate(DEPTHS_KM):
        window = np.abs(DEPTHS_KM - center_depth_km) <= VS_GRADIENT_WINDOW_HALF_KM
        if np.count_nonzero(window) < 2:
            continue
        z = DEPTHS_KM[window].astype(float)
        z_anom = z - float(np.nanmean(z))
        denom = float(np.sum(z_anom**2))
        if denom <= 0.0:
            continue
        y = vs_km_s[:, window]
        y_anom = y - np.nanmean(y, axis=1, keepdims=True)
        gradients[:, index] = np.nansum(y_anom * z_anom[None, :], axis=1) / denom
    return gradients


def summarize_gradient_windows(gradients: np.ndarray) -> pd.DataFrame:
    masks = {
        "0_1km": (DEPTHS_KM >= 0.0) & (DEPTHS_KM <= 1.0),
        "0_2p5km": (DEPTHS_KM >= 0.0) & (DEPTHS_KM <= 2.5),
        "0_3km": (DEPTHS_KM >= 0.0) & (DEPTHS_KM <= 3.0),
        "0_5km": (DEPTHS_KM >= 0.0) & (DEPTHS_KM <= 5.0),
    }
    out = pd.DataFrame(
        {
            "vsgrad_signed_mean_0_1km": np.nanmean(gradients[:, masks["0_1km"]], axis=1),
            "vsgrad_signed_mean_0_2p5km": np.nanmean(gradients[:, masks["0_2p5km"]], axis=1),
            "vsgrad_signed_mean_0_5km": np.nanmean(gradients[:, masks["0_5km"]], axis=1),
            "vsgrad_abs_mean_0_1km": np.nanmean(np.abs(gradients[:, masks["0_1km"]]), axis=1),
            "vsgrad_abs_mean_0_2p5km": np.nanmean(np.abs(gradients[:, masks["0_2p5km"]]), axis=1),
            "vsgrad_abs_mean_0_5km": np.nanmean(np.abs(gradients[:, masks["0_5km"]]), axis=1),
            "vsgrad_positive_max_0_3km": np.nanmax(gradients[:, masks["0_3km"]], axis=1),
            "vsgrad_abs_max_0_3km": np.nanmax(np.abs(gradients[:, masks["0_3km"]]), axis=1),
        }
    )
    return out


def sample_vs_gradient_predictors(sampler: ModelSampler, points: pd.DataFrame) -> pd.DataFrame:
    unique_points = points[["profile_id", "station", "profile_x", "profile_y"]].drop_duplicates().reset_index(drop=True)
    xyz_rows: list[list[float]] = []
    for row in unique_points.itertuples(index=False):
        for depth_km in DEPTHS_KM:
            xyz_rows.append([float(row.profile_x), float(row.profile_y), -1000.0 * float(depth_km)])
    sampled = sampler.sample_xyz(np.asarray(xyz_rows, dtype=float))
    vs = sampled["vs"].to_numpy(dtype=float).reshape(len(unique_points), len(DEPTHS_KM)) / 1000.0
    gradients = local_vertical_gradient(vs)
    summaries = summarize_gradient_windows(gradients)
    out = pd.concat([unique_points, summaries], axis=1)
    return points.merge(out, on=["profile_id", "station", "profile_x", "profile_y"], how="left", validate="many_to_one")


def weighted_corr(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0)
    if int(valid.sum()) < MIN_STATIONS:
        return np.nan
    x = x[valid]
    y = y[valid]
    weights = weights[valid]
    x_mean = np.average(x, weights=weights)
    y_mean = np.average(y, weights=weights)
    x_anom = x - x_mean
    y_anom = y - y_mean
    denom = math.sqrt(float(np.sum(weights * x_anom**2) * np.sum(weights * y_anom**2)))
    if denom <= 0.0:
        return np.nan
    return float(np.sum(weights * x_anom * y_anom) / denom)


def weighted_spearman(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0)
    if int(valid.sum()) < MIN_STATIONS:
        return np.nan
    return weighted_corr(rankdata(x[valid]), rankdata(y[valid]), weights[valid])


def bootstrap_weighted_spearman(x: np.ndarray, y: np.ndarray, weights: np.ndarray, rng: np.random.Generator) -> tuple[float, float]:
    if BOOTSTRAP_SAMPLES <= 0:
        return np.nan, np.nan
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0)
    x = x[valid]
    y = y[valid]
    weights = weights[valid]
    if len(x) < MIN_STATIONS:
        return np.nan, np.nan
    probabilities = weights / weights.sum()
    estimates = []
    for _ in range(BOOTSTRAP_SAMPLES):
        sample = rng.choice(len(x), size=len(x), replace=True, p=probabilities)
        estimate = weighted_spearman(x[sample], y[sample], weights[sample])
        if np.isfinite(estimate):
            estimates.append(estimate)
    if not estimates:
        return np.nan, np.nan
    return tuple(float(value) for value in np.nanquantile(estimates, [0.025, 0.975]))


def correlation_rows(points: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    rows: list[dict[str, object]] = []
    for corridor_km in CORRIDORS_KM:
        corridor_points = points.loc[points["offset_km"].le(corridor_km)].copy()
        groups = corridor_points.groupby(["profile_id", "family", "metric", "metric_panel", "band", "period_s"], dropna=False)
        for group_key, group in groups:
            profile_id, family, metric, metric_panel, band, period_s = group_key
            for residual_stat, residual_column in (
                ("mean residual", "residual_mean"),
                ("median residual", "residual_median"),
                ("residual std", "residual_std"),
            ):
                for predictor_label, predictor_column, absolute_value in PREDICTORS:
                    valid = group[[residual_column, predictor_column, "events"]].replace([np.inf, -np.inf], np.nan).dropna()
                    if len(valid) >= MIN_STATIONS:
                        x = valid[predictor_column].to_numpy(dtype=float)
                        y = valid[residual_column].to_numpy(dtype=float)
                        weights = valid["events"].to_numpy(dtype=float)
                        rho_pearson = weighted_corr(x, y, weights)
                        rho_spearman = weighted_spearman(x, y, weights)
                        ci_low, ci_high = bootstrap_weighted_spearman(x, y, weights, rng)
                        unweighted = spearmanr(x, y)
                        unweighted_p = float(unweighted.pvalue)
                    else:
                        rho_pearson = rho_spearman = ci_low = ci_high = unweighted_p = np.nan
                    rows.append(
                        {
                            "corridor_km": corridor_km,
                            "profile_id": profile_id,
                            "family": family,
                            "metric": metric,
                            "metric_panel": metric_panel,
                            "band": band,
                            "period_s": period_s,
                            "residual_stat": residual_stat,
                            "predictor": predictor_label,
                            "predictor_column": predictor_column,
                            "absolute_gradient": absolute_value,
                            "weighted_pearson_r": rho_pearson,
                            "weighted_spearman_rho": rho_spearman,
                            "weighted_spearman_ci_low": ci_low,
                            "weighted_spearman_ci_high": ci_high,
                            "unweighted_spearman_p": unweighted_p,
                            "stations": int(len(valid)),
                            "event_weight": float(valid["events"].sum()) if len(valid) else 0.0,
                        }
                    )
    return pd.DataFrame(rows)


def summarize_correlations(correlations: pd.DataFrame) -> pd.DataFrame:
    valid = correlations.dropna(subset=["weighted_spearman_rho"]).copy()
    if valid.empty:
        return pd.DataFrame()
    summary = (
        valid.groupby(["corridor_km", "metric", "metric_panel", "residual_stat", "predictor", "predictor_column"], as_index=False)
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
        .sort_values(["corridor_km", "metric_panel", "residual_stat", "mean_abs_weighted_spearman"], ascending=[True, True, True, False])
    )
    summary["consistent_sign_across_iqr"] = (
        (summary["q25_weighted_spearman"] > 0) & (summary["q75_weighted_spearman"] > 0)
    ) | ((summary["q25_weighted_spearman"] < 0) & (summary["q75_weighted_spearman"] < 0))
    return summary


def plot_summary_heatmap(summary: pd.DataFrame, output_path: Path) -> Path:
    subset = summary.loc[
        summary["corridor_km"].eq(10.0)
        & summary["residual_stat"].eq("mean residual")
        & summary["profiles"].ge(6)
    ].copy()
    if subset.empty:
        return output_path
    order = [label for label, _, _ in PREDICTORS]
    metric_order = [
        "PGA 1-2 sec",
        "PGA 2-3 sec",
        "PGA 3-5 sec",
        "PGV 1-2 sec",
        "PGV 2-3 sec",
        "PGV 3-5 sec",
        "arias_duration 1-2 sec",
        "arias_duration 2-3 sec",
        "arias_duration 3-5 sec",
        "PSA 1 s",
        "PSA 2 s",
        "PSA 3 s",
        "PSA 4 s",
        "PSA 5 s",
    ]
    matrix = (
        subset.pivot_table(index="predictor", columns="metric_panel", values="median_weighted_spearman", aggfunc="median")
        .reindex(index=order, columns=metric_order)
    )
    set_plot_theme()
    fig, ax = plt.subplots(figsize=(15.5, 7.2))
    image = ax.imshow(matrix.to_numpy(dtype=float), cmap="RdBu_r", vmin=-0.6, vmax=0.6, aspect="auto")
    ax.set_xticks(np.arange(len(matrix.columns)))
    ax.set_xticklabels(matrix.columns, rotation=35, ha="right", fontsize=9.0)
    ax.set_yticks(np.arange(len(matrix.index)))
    ax.set_yticklabels(matrix.index, fontsize=9.5)
    ax.set_title("Median profile-wise weighted Spearman correlation: mean residual vs local vertical Vs gradient", fontsize=15, fontweight="bold")
    ax.set_xlabel("Metric and passband")
    ax.set_ylabel("Gradient predictor")
    cbar = fig.colorbar(image, ax=ax, shrink=0.86)
    cbar.set_label("Median weighted Spearman rho across profiles")
    ax.text(
        0.0,
        -0.24,
        "Rows use station residual means within the 10 km corridor. Correlations are weighted by station event count; "
        "gradient predictors are computed from overlapping +/-0.5 km vertical windows.",
        transform=ax.transAxes,
        fontsize=9.5,
        color=COLORS["muted"],
        ha="left",
    )
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return output_path


def write_markdown(summary: pd.DataFrame, correlations: pd.DataFrame, output_path: Path) -> Path:
    lines = [
        "# LA Basin Residuals Versus Vertical Vs Gradient",
        "",
        "This analysis tests whether station-level residual summaries correlate with local CVM-SI vertical Vs-gradient "
        "predictors sampled at each station's projected point along the same LA Basin profile corridors. The gradient "
        "is estimated with overlapping +/-0.5 km vertical windows, matching the current Vs-gradient atlas.",
        "",
        "Correlations are computed profile by profile and weighted by the number of contributing events at each station. "
        "The table summaries report the median weighted Spearman rho across profiles.",
        "",
    ]
    if summary.empty:
        lines.append("No valid correlations were available.")
    else:
        robust = summary.loc[
            summary["residual_stat"].eq("mean residual")
            & summary["profiles"].ge(6)
            & summary["consistent_sign_across_iqr"]
        ].copy()
        robust["abs_median_rho"] = robust["median_weighted_spearman"].abs()
        top = robust.sort_values("abs_median_rho", ascending=False).head(12)
        if top.empty:
            lines.append("No mean-residual gradient predictor had a consistent profile-wise sign across the interquartile range.")
        else:
            lines.append("## Strongest Consistent Mean-Residual Associations")
            lines.append("")
            lines.append("| corridor km | metric panel | predictor | median rho | IQR rho | profiles | median stations |")
            lines.append("|---:|---|---|---:|---:|---:|---:|")
            for row in top.itertuples(index=False):
                lines.append(
                    f"| {row.corridor_km:g} | {row.metric_panel} | {row.predictor} | "
                    f"{row.median_weighted_spearman:.2f} | "
                    f"{row.q25_weighted_spearman:.2f} to {row.q75_weighted_spearman:.2f} | "
                    f"{int(row.profiles)} | {row.median_stations:.0f} |"
                )
        overall = (
            summary.loc[summary["residual_stat"].eq("mean residual")]
            .groupby(["corridor_km", "predictor"], as_index=False)
            .agg(
                median_abs_median_rho=("median_weighted_spearman", lambda value: float(np.nanmedian(np.abs(value)))),
                n_metric_panels=("metric_panel", "nunique"),
            )
            .sort_values(["corridor_km", "median_abs_median_rho"], ascending=[True, False])
        )
        lines.extend(["", "## Overall Predictor Strength", ""])
        lines.append("| corridor km | strongest broad predictor | median |rho| over metric panels |")
        lines.append("|---:|---|---:|")
        for corridor_km, group in overall.groupby("corridor_km", sort=True):
            row = group.iloc[0]
            lines.append(f"| {corridor_km:g} | {row['predictor']} | {row['median_abs_median_rho']:.2f} |")
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            "- These are univariate station/profile correlations, not mixed-effects model terms.",
            "- Many metric/predictor/corridor combinations are tested, so isolated high correlations should be treated as screening results.",
            "- The most useful signal is a correlation that keeps the same sign across multiple profiles, passbands, or corridor widths.",
            "",
            f"Correlation rows: {len(correlations):,}.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def main() -> int:
    output_dir = DEFAULT_OUTPUT
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    report_dir = output_dir / "report"
    for directory in (tables_dir, figures_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)

    regions = load_regions(DEFAULT_REGIONS)
    long_sections, perp_sections, metadata = build_profile_families(regions)
    sections = [*long_sections, *perp_sections]
    raw = load_metric_rows(DEFAULT_METRICS)
    pairs = collapse_components(raw)
    residual_summary = station_residual_summary(pairs)
    projected = build_projected_station_points(residual_summary, sections, metadata)
    sampler = ModelSampler(DEFAULT_MODEL_H5, node_stride=2)
    points = sample_vs_gradient_predictors(sampler, projected)

    points_path = tables_dir / "la_basin_vs_gradient_station_points.parquet"
    points_csv_path = tables_dir / "la_basin_vs_gradient_station_points.csv"
    correlations_path = tables_dir / "la_basin_vs_gradient_correlations.csv"
    summary_path = tables_dir / "la_basin_vs_gradient_corridor_summary.csv"
    figure_path = figures_dir / "fig_06t_la_basin_vs_gradient_correlation_heatmap.png"
    markdown_path = report_dir / "la_basin_vs_gradient_correlation_summary.md"

    points.to_parquet(points_path, index=False)
    points.to_csv(points_csv_path, index=False)
    correlations = correlation_rows(points)
    correlations.to_csv(correlations_path, index=False)
    summary = summarize_correlations(correlations)
    summary.to_csv(summary_path, index=False)
    plot_summary_heatmap(summary, figure_path)
    write_markdown(summary, correlations, markdown_path)

    for path in (points_path, points_csv_path, correlations_path, summary_path, figure_path, markdown_path):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
