#!/usr/bin/env python3
"""Correlate LA Basin residuals with CVM-SI z-depth and Vp/rho gradients."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

from cvmsi_hypothesis_study import (
    COLORS,
    DEFAULT_METRICS,
    DEFAULT_MODEL_H5,
    DEFAULT_OUTPUT,
    DEFAULT_REGIONS,
    ModelSampler,
    load_regions,
    set_plot_theme,
)
from render_la_basin_axis_profile_sections import build_profile_families
from render_la_basin_metric_profile_atlas import collapse_components, load_metric_rows
from analyze_la_basin_vs_gradient_correlations import (
    MIN_STATIONS,
    RANDOM_SEED,
    build_projected_station_points,
    station_residual_summary,
)


CORRIDORS_KM = (5.0, 10.0, 15.0)
DEPTHS_KM = np.linspace(0.0, 15.0, 151)
GRADIENT_WINDOW_HALF_KM = 0.5


@dataclass(frozen=True)
class PredictorSpec:
    label: str
    column: str
    family: str
    units: str


PREDICTORS = [
    PredictorSpec("z(Vs=1.0)", "z_vs_1p0_km", "z-depth", "km"),
    PredictorSpec("z(Vs=2.5)", "z_vs_2p5_km", "z-depth", "km"),
    PredictorSpec("Vp mean signed gradient 0-1 km", "vpgrad_signed_mean_0_1km", "Vp gradient", "km/s/km"),
    PredictorSpec("Vp mean signed gradient 0-2.5 km", "vpgrad_signed_mean_0_2p5km", "Vp gradient", "km/s/km"),
    PredictorSpec("Vp mean signed gradient 0-5 km", "vpgrad_signed_mean_0_5km", "Vp gradient", "km/s/km"),
    PredictorSpec("Vp mean |gradient| 0-1 km", "vpgrad_abs_mean_0_1km", "Vp gradient", "km/s/km"),
    PredictorSpec("Vp mean |gradient| 0-2.5 km", "vpgrad_abs_mean_0_2p5km", "Vp gradient", "km/s/km"),
    PredictorSpec("Vp mean |gradient| 0-5 km", "vpgrad_abs_mean_0_5km", "Vp gradient", "km/s/km"),
    PredictorSpec("Vp max positive gradient 0-3 km", "vpgrad_positive_max_0_3km", "Vp gradient", "km/s/km"),
    PredictorSpec("Vp max |gradient| 0-3 km", "vpgrad_abs_max_0_3km", "Vp gradient", "km/s/km"),
    PredictorSpec("rho mean signed gradient 0-1 km", "rhograd_signed_mean_0_1km", "rho gradient", "model rho/km"),
    PredictorSpec("rho mean signed gradient 0-2.5 km", "rhograd_signed_mean_0_2p5km", "rho gradient", "model rho/km"),
    PredictorSpec("rho mean signed gradient 0-5 km", "rhograd_signed_mean_0_5km", "rho gradient", "model rho/km"),
    PredictorSpec("rho mean |gradient| 0-1 km", "rhograd_abs_mean_0_1km", "rho gradient", "model rho/km"),
    PredictorSpec("rho mean |gradient| 0-2.5 km", "rhograd_abs_mean_0_2p5km", "rho gradient", "model rho/km"),
    PredictorSpec("rho mean |gradient| 0-5 km", "rhograd_abs_mean_0_5km", "rho gradient", "model rho/km"),
    PredictorSpec("rho max positive gradient 0-3 km", "rhograd_positive_max_0_3km", "rho gradient", "model rho/km"),
    PredictorSpec("rho max |gradient| 0-3 km", "rhograd_abs_max_0_3km", "rho gradient", "model rho/km"),
]
PREDICTOR_BY_COLUMN = {predictor.column: predictor for predictor in PREDICTORS}


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


def local_vertical_gradient(values: np.ndarray) -> np.ndarray:
    gradients = np.full(values.shape, np.nan, dtype=float)
    for index, center_depth_km in enumerate(DEPTHS_KM):
        window = np.abs(DEPTHS_KM - center_depth_km) <= GRADIENT_WINDOW_HALF_KM
        if np.count_nonzero(window) < 2:
            continue
        z = DEPTHS_KM[window].astype(float)
        z_anom = z - float(np.nanmean(z))
        denom = float(np.sum(z_anom**2))
        if denom <= 0.0:
            continue
        y = values[:, window]
        y_anom = y - np.nanmean(y, axis=1, keepdims=True)
        gradients[:, index] = np.nansum(y_anom * z_anom[None, :], axis=1) / denom
    return gradients


def summarize_gradient_windows(prefix: str, gradients: np.ndarray) -> pd.DataFrame:
    masks = {
        "0_1km": (DEPTHS_KM >= 0.0) & (DEPTHS_KM <= 1.0),
        "0_2p5km": (DEPTHS_KM >= 0.0) & (DEPTHS_KM <= 2.5),
        "0_3km": (DEPTHS_KM >= 0.0) & (DEPTHS_KM <= 3.0),
        "0_5km": (DEPTHS_KM >= 0.0) & (DEPTHS_KM <= 5.0),
    }
    return pd.DataFrame(
        {
            f"{prefix}_signed_mean_0_1km": np.nanmean(gradients[:, masks["0_1km"]], axis=1),
            f"{prefix}_signed_mean_0_2p5km": np.nanmean(gradients[:, masks["0_2p5km"]], axis=1),
            f"{prefix}_signed_mean_0_5km": np.nanmean(gradients[:, masks["0_5km"]], axis=1),
            f"{prefix}_abs_mean_0_1km": np.nanmean(np.abs(gradients[:, masks["0_1km"]]), axis=1),
            f"{prefix}_abs_mean_0_2p5km": np.nanmean(np.abs(gradients[:, masks["0_2p5km"]]), axis=1),
            f"{prefix}_abs_mean_0_5km": np.nanmean(np.abs(gradients[:, masks["0_5km"]]), axis=1),
            f"{prefix}_positive_max_0_3km": np.nanmax(gradients[:, masks["0_3km"]], axis=1),
            f"{prefix}_abs_max_0_3km": np.nanmax(np.abs(gradients[:, masks["0_3km"]]), axis=1),
        }
    )


def sample_model_property_predictors(sampler: ModelSampler, points: pd.DataFrame) -> pd.DataFrame:
    unique_points = points[["profile_id", "station", "profile_x", "profile_y"]].drop_duplicates().reset_index(drop=True)
    xyz_rows: list[list[float]] = []
    for row in unique_points.itertuples(index=False):
        for depth_km in DEPTHS_KM:
            xyz_rows.append([float(row.profile_x), float(row.profile_y), -1000.0 * float(depth_km)])
    sampled = sampler.sample_xyz(np.asarray(xyz_rows, dtype=float))
    n_points = len(unique_points)
    vs = sampled["vs"].to_numpy(dtype=float).reshape(n_points, len(DEPTHS_KM)) / 1000.0
    vp = sampled["vp"].to_numpy(dtype=float).reshape(n_points, len(DEPTHS_KM)) / 1000.0
    rho = sampled["rho"].to_numpy(dtype=float).reshape(n_points, len(DEPTHS_KM))

    summaries = pd.DataFrame(
        {
            "z_vs_1p0_km": [interpolate_depth_to_threshold(profile, 1.0) for profile in vs],
            "z_vs_2p5_km": [interpolate_depth_to_threshold(profile, 2.5) for profile in vs],
        }
    )
    summaries = pd.concat(
        [
            summaries,
            summarize_gradient_windows("vpgrad", local_vertical_gradient(vp)),
            summarize_gradient_windows("rhograd", local_vertical_gradient(rho)),
        ],
        axis=1,
    )
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


def correlation_rows(points: pd.DataFrame) -> pd.DataFrame:
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
                for predictor in PREDICTORS:
                    valid = group[[residual_column, predictor.column, "events"]].replace([np.inf, -np.inf], np.nan).dropna()
                    valid = valid.loc[valid["events"].gt(0)]
                    if len(valid) >= MIN_STATIONS:
                        x = valid[predictor.column].to_numpy(dtype=float)
                        y = valid[residual_column].to_numpy(dtype=float)
                        weights = valid["events"].to_numpy(dtype=float)
                        rho_pearson = weighted_corr(x, y, weights)
                        rho_spearman = weighted_spearman(x, y, weights)
                        unweighted = spearmanr(x, y)
                        unweighted_p = float(unweighted.pvalue) if np.isfinite(unweighted.statistic) else np.nan
                    else:
                        rho_pearson = rho_spearman = unweighted_p = np.nan
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
                            "predictor": predictor.label,
                            "predictor_column": predictor.column,
                            "predictor_family": predictor.family,
                            "predictor_units": predictor.units,
                            "weighted_pearson_r": rho_pearson,
                            "weighted_spearman_rho": rho_spearman,
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
        valid.groupby(
            [
                "corridor_km",
                "metric",
                "metric_panel",
                "residual_stat",
                "predictor_family",
                "predictor",
                "predictor_column",
                "predictor_units",
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
        .sort_values(["corridor_km", "metric_panel", "residual_stat", "mean_abs_weighted_spearman"], ascending=[True, True, True, False])
    )
    summary["consistent_sign_across_iqr"] = (
        (summary["q25_weighted_spearman"] > 0) & (summary["q75_weighted_spearman"] > 0)
    ) | ((summary["q25_weighted_spearman"] < 0) & (summary["q75_weighted_spearman"] < 0))
    return summary


def metric_order() -> list[str]:
    return [
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


def plot_summary_heatmap(summary: pd.DataFrame, output_path: Path) -> Path:
    selected = [
        "z(Vs=1.0)",
        "z(Vs=2.5)",
        "Vp mean signed gradient 0-1 km",
        "Vp mean signed gradient 0-2.5 km",
        "Vp mean |gradient| 0-1 km",
        "Vp mean |gradient| 0-2.5 km",
        "Vp max |gradient| 0-3 km",
        "rho mean signed gradient 0-1 km",
        "rho mean signed gradient 0-2.5 km",
        "rho mean |gradient| 0-1 km",
        "rho mean |gradient| 0-2.5 km",
        "rho max |gradient| 0-3 km",
    ]
    subset = summary.loc[
        summary["corridor_km"].eq(10.0)
        & summary["residual_stat"].eq("mean residual")
        & summary["profiles"].ge(6)
        & summary["predictor"].isin(selected)
    ].copy()
    if subset.empty:
        return output_path
    matrix = (
        subset.pivot_table(index="predictor", columns="metric_panel", values="median_weighted_spearman", aggfunc="median")
        .reindex(index=selected, columns=metric_order())
    )
    set_plot_theme()
    fig, ax = plt.subplots(figsize=(17.0, 9.4))
    image = ax.imshow(matrix.to_numpy(dtype=float), cmap="RdBu_r", vmin=-0.6, vmax=0.6, aspect="auto")
    ax.set_xticks(np.arange(len(matrix.columns)))
    ax.set_xticklabels(matrix.columns, rotation=35, ha="right", fontsize=10.8)
    ax.set_yticks(np.arange(len(matrix.index)))
    ax.set_yticklabels(matrix.index, fontsize=11.0)
    ax.set_title(
        "LA Basin station residual correlations with CVM-SI z-depth, Vp gradient, and rho gradient",
        fontsize=17.0,
        fontweight="bold",
    )
    ax.set_xlabel("Metric and passband", fontsize=12.0)
    ax.set_ylabel("Model predictor", fontsize=12.0)
    cbar = fig.colorbar(image, ax=ax, shrink=0.85)
    cbar.set_label("Median event-count-weighted Spearman rho across profiles", fontsize=11.5)
    cbar.ax.tick_params(labelsize=10.0)
    note = (
        "10 km station corridor; station mean residuals; gradients use overlapping +/-0.5 km vertical windows. "
        "Positive rho means residuals increase where the model predictor is larger/deeper/steeper."
    )
    fig.text(0.11, 0.035, textwrap.fill(note, width=165), fontsize=10.5, color=COLORS["muted"], ha="left", va="bottom")
    fig.tight_layout(rect=[0.0, 0.075, 1.0, 0.98])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)
    return output_path


def write_markdown(summary: pd.DataFrame, correlations: pd.DataFrame, output_path: Path) -> Path:
    def md_cell(value: object) -> str:
        return str(value).replace("|", "\\|")

    lines = [
        "# LA Basin Residuals Versus z-depth, Vp-gradient, and rho-gradient Predictors",
        "",
        "This screen correlates station-level residual summaries with CVM-SI predictors sampled at the station projection "
        "onto each rotated LA Basin profile. z-depth predictors are the first depths where Vs reaches 1.0 and 2.5 km/s. "
        "Vp and rho gradients are local vertical slopes estimated with overlapping +/-0.5 km windows.",
        "",
        "Statistics are computed separately for each profile and corridor width, weighted by station event count, then "
        "summarized as the median weighted Spearman rho across profiles.",
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
        top = robust.sort_values("abs_median_rho", ascending=False).head(20)
        if top.empty:
            lines.append("## Strongest Consistent Mean-Residual Associations")
            lines.append("")
            lines.append("No mean-residual predictor kept a consistent sign across the profile interquartile range.")
        else:
            lines.append("## Strongest Consistent Mean-Residual Associations")
            lines.append("")
            lines.append("| corridor km | metric panel | predictor | family | median rho | IQR rho | profiles | median stations |")
            lines.append("|---:|---|---|---|---:|---:|---:|---:|")
            for row in top.itertuples(index=False):
                lines.append(
                    f"| {row.corridor_km:g} | {md_cell(row.metric_panel)} | {md_cell(row.predictor)} | {md_cell(row.predictor_family)} | "
                    f"{row.median_weighted_spearman:.2f} | "
                    f"{row.q25_weighted_spearman:.2f} to {row.q75_weighted_spearman:.2f} | "
                    f"{int(row.profiles)} | {row.median_stations:.0f} |"
                )
        lines.extend(["", "## Strongest Broad Predictor by Corridor", ""])
        lines.append("| corridor km | predictor family | strongest predictor | median |rho| over metric panels |")
        lines.append("|---:|---|---|---:|")
        broad = (
            summary.loc[summary["residual_stat"].eq("mean residual")]
            .groupby(["corridor_km", "predictor_family", "predictor"], as_index=False)
            .agg(
                median_abs_median_rho=("median_weighted_spearman", lambda value: float(np.nanmedian(np.abs(value)))),
                n_metric_panels=("metric_panel", "nunique"),
            )
            .sort_values(["corridor_km", "predictor_family", "median_abs_median_rho"], ascending=[True, True, False])
        )
        for (corridor_km, family), group in broad.groupby(["corridor_km", "predictor_family"], sort=True):
            row = group.iloc[0]
            lines.append(f"| {corridor_km:g} | {md_cell(family)} | {md_cell(row['predictor'])} | {row['median_abs_median_rho']:.2f} |")
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            "- These are univariate screening correlations, not mixed-effects model terms.",
            "- Many metric/predictor/corridor combinations are tested; isolated large values should not be treated as robust without replication across profiles or passbands.",
            "- z-depth predictors are derived from Vs only; the Vp/rho terms test local vertical gradients in those fields, not impedance gradients or lateral gradients.",
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
    points = sample_model_property_predictors(sampler, projected)

    points_path = tables_dir / "la_basin_model_property_station_points.parquet"
    points_csv_path = tables_dir / "la_basin_model_property_station_points.csv"
    correlations_path = tables_dir / "la_basin_model_property_correlations.csv"
    summary_path = tables_dir / "la_basin_model_property_corridor_summary.csv"
    figure_path = figures_dir / "fig_06u_la_basin_model_property_correlation_heatmap.png"
    markdown_path = report_dir / "la_basin_model_property_correlation_summary.md"

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
