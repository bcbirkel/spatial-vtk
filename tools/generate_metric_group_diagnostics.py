"""Generate user-requested large-run metric-group diagnostic figures.

This script is intentionally self-contained so it can run directly on the
Discovery output tree without importing a dirty local package checkout. It
reads the large-run ``metrics_long.parquet`` table, writes static PNG figures,
CSV summaries, and a JSON manifest under the requested output directory.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from spatial_vtk.metrics.calculate.waveforms import bandpass_with_metadata


GROUP_METRICS: dict[str, tuple[str, ...]] = {
    "duration": ("arias_duration", "energy_duration"),
    "amplitude": ("PGA", "PGV", "PGD"),
    "spectral": ("PSA", "FAS"),
    "intensity": ("arias_intensity", "energy_intensity", "CAV"),
    "delay": ("traveltime_delay",),
    "cross_correlation": ("original_cc", "delay_corrected_cc"),
}

MODEL = "cvmsi_20260506_material_0p6x1p2_asdf"
PASSBANDS = ("1-2 sec", "2-3 sec", "3-5 sec")
TRIM_PERCENTILES = (0.0, 1.0, 2.5, 5.0, 10.0)
NEARBY_DISTANCE_KM = 10.0
DISTANCE_EPSILON_KM = 0.25

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}

COLORS = {
    "blue": "#5477C4",
    "blue_light": "#A3BEFA",
    "gold": "#B8A037",
    "orange": "#CC6F47",
    "olive": "#71B436",
    "pink": "#BD569B",
    "neutral": "#7A828F",
    "neutral_light": "#C5CAD3",
}

VALUE_SOURCES = (
    ("observed", "value_obs", "Raw observed value"),
    ("synthetic", "value_syn", "Raw synthetic value"),
    ("plot_value", "__plot_value", "Metric-specific plot value"),
)


@dataclass(frozen=True)
class RunPaths:
    outputs_root: Path
    metrics_long: Path
    output_dir: Path
    repo_root: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--outputs-root",
        type=Path,
        default=Path("/project2/jvidale_1700/spatial-vtk/runs/outputs"),
        help="Large-run outputs root containing tables/metrics_long.parquet.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/figures/user_requested_metric_group_diagnostics"),
        help="Directory for generated figures and summaries.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("/project2/jvidale_1700/spatial-vtk"),
        help="Root used to resolve relative waveform paths.",
    )
    parser.add_argument("--waveforms-per-metric", type=int, default=30)
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = RunPaths(
        outputs_root=args.outputs_root.expanduser().resolve(),
        metrics_long=(args.outputs_root / "tables" / "metrics_long.parquet").expanduser().resolve(),
        output_dir=args.output_dir.expanduser().resolve(),
        repo_root=args.repo_root.expanduser().resolve(),
    )
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    for subdir in ("spatial_consistency", "outlier_robustness", "waveforms", "summaries"):
        (paths.output_dir / subdir).mkdir(parents=True, exist_ok=True)

    configure_matplotlib()
    df = read_metrics(paths.metrics_long)
    df = prepare_metric_values(df)

    manifest: dict[str, object] = {
        "outputs_root": str(paths.outputs_root),
        "metrics_long": str(paths.metrics_long),
        "output_dir": str(paths.output_dir),
        "model": MODEL,
        "metric_groups": GROUP_METRICS,
        "passbands": PASSBANDS,
        "method": {
            "spatial_consistency": (
                "Nearby station pairs are rows from the same event, metric, passband, component, model, "
                "and spectral period where applicable, with station separation <= 10 km. Pair weights use "
                "inverse distance, w = 1 / max(distance_km, 0.25), then normalize within the stratum. "
                "The plotted consistency statistic is weighted Pearson correlation between paired station "
                "values. CSV summaries also include weighted mean absolute pair difference."
            ),
            "outlier_robustness": (
                "Percentile sensitivity uses deterministic symmetric tail thresholds of "
                "0, 1, 2.5, 5, and 10 percent. The figure plots trimmed-mean and winsorized-mean "
                "changes relative to the 0 percent untrimmed mean, scaled by the source IQR."
            ),
            "waveform_examples": (
                "Thirty rows per metric are selected deterministically from finite metric rows with existing "
                "observed and synthetic waveform paths. Selection prioritizes coverage across passbands, "
                "components, events, station locations, and station-event distance quantile bins."
            ),
            "traveltime_delay_plot_value": (
                "metrics_long does not contain delay_fraction_dominant_period, so traveltime_delay plot value "
                "is value divided by passband midpoint period: 1.5, 2.5, or 4.0 seconds."
            ),
            "cross_correlation_plot_value": "original_cc and delay_corrected_cc use the value column.",
            "ratio_metric_plot_value": "All other metrics use log2_residual as the plot value.",
        },
        "warnings": [],
        "figures": [],
        "summaries": [],
        "row_counts": {},
    }

    manifest["row_counts"] = {
        "metrics_long_rows": int(len(df)),
        "finite_obs_rows": int(np.isfinite(df["value_obs"]).sum()) if "value_obs" in df else 0,
        "finite_syn_rows": int(np.isfinite(df["value_syn"]).sum()) if "value_syn" in df else 0,
        "finite_plot_value_rows": int(np.isfinite(df["__plot_value"]).sum()),
    }

    spatial_summary = build_spatial_consistency(df)
    spatial_csv = paths.output_dir / "summaries" / "spatial_consistency_summary.csv"
    spatial_summary.to_csv(spatial_csv, index=False)
    manifest["summaries"].append(str(spatial_csv))
    plot_spatial_figures(spatial_summary, paths.output_dir, manifest)

    robustness = build_outlier_robustness(df)
    robustness_csv = paths.output_dir / "summaries" / "outlier_robustness_summary.csv"
    robustness.to_csv(robustness_csv, index=False)
    manifest["summaries"].append(str(robustness_csv))
    plot_robustness_figures(robustness, paths.output_dir, manifest)

    selected_rows = select_waveform_examples(df, paths, args.waveforms_per_metric)
    selected_csv = paths.output_dir / "summaries" / "waveform_example_rows.csv"
    selected_rows.to_csv(selected_csv, index=False)
    manifest["summaries"].append(str(selected_csv))
    plot_waveform_examples(selected_rows, paths, manifest)

    missing_sources = summarize_missing_value_sources(df)
    if missing_sources:
        manifest["warnings"].extend(missing_sources)

    manifest_path = paths.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "figures": len(manifest["figures"]), "summaries": len(manifest["summaries"])}, indent=2))


def configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": TOKENS["surface"],
            "savefig.facecolor": TOKENS["surface"],
            "axes.facecolor": TOKENS["panel"],
            "axes.edgecolor": TOKENS["axis"],
            "axes.labelcolor": TOKENS["ink"],
            "axes.titlecolor": TOKENS["ink"],
            "xtick.color": TOKENS["muted"],
            "ytick.color": TOKENS["muted"],
            "grid.color": TOKENS["grid"],
            "grid.linewidth": 0.8,
            "font.family": ["DejaVu Sans", "Arial", "sans-serif"],
            "font.size": 9,
        }
    )


def read_metrics(path: Path) -> pd.DataFrame:
    required = [
        "event_id",
        "station",
        "component",
        "model",
        "passband",
        "metric_group",
        "metric",
        "obs_waveform_path",
        "syn_waveform_path",
        "period_s",
        "value",
        "value_obs",
        "value_syn",
        "log2_residual",
        "distance_km",
        "sta_lat",
        "sta_lon",
        "event_lat",
        "event_lon",
    ]
    df = pd.read_parquet(path, columns=required)
    df = df.loc[df["model"].astype(str).eq(MODEL)].copy()
    df = df.loc[df["metric_group"].astype(str).isin(GROUP_METRICS)].copy()
    df = df.loc[df["passband"].astype(str).isin(PASSBANDS)].copy()
    for col in ["value", "value_obs", "value_syn", "log2_residual", "distance_km", "sta_lat", "sta_lon", "period_s"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def prepare_metric_values(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["__plot_value"] = out["log2_residual"]
    cc_mask = out["metric"].isin(["original_cc", "delay_corrected_cc"])
    out.loc[cc_mask, "__plot_value"] = out.loc[cc_mask, "value"]
    delay_mask = out["metric"].eq("traveltime_delay")
    out.loc[delay_mask, "__plot_value"] = out.loc[delay_mask, "value"] / out.loc[delay_mask, "passband"].map(passband_midpoint_s)
    return out


def passband_midpoint_s(value: object) -> float:
    match = re.search(r"([0-9.]+)\s*-\s*([0-9.]+)", str(value))
    if not match:
        return float("nan")
    return 0.5 * (float(match.group(1)) + float(match.group(2)))


def build_spatial_consistency(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    group_cols = ["metric_group", "metric", "event_id", "passband", "component"]
    if "period_s" in df.columns:
        group_cols.append("period_s")
    for source_name, value_col, source_label in VALUE_SOURCES:
        source_df = df.dropna(subset=[value_col, "sta_lat", "sta_lon"]).copy()
        if source_df.empty:
            for group, metrics in GROUP_METRICS.items():
                for metric in metrics:
                    rows.append(empty_spatial_row(group, metric, source_name, source_label))
            continue
        for keys, sub in source_df.groupby(group_cols, dropna=False, sort=False):
            if len(sub) < 2:
                continue
            sub = sub.drop_duplicates(subset=["station"]).copy()
            if len(sub) < 2:
                continue
            pairs = nearby_pair_stats(sub, value_col)
            if pairs is None:
                continue
            key_map = dict(zip(group_cols, keys if isinstance(keys, tuple) else (keys,)))
            rows.append(
                {
                    "metric_group": key_map["metric_group"],
                    "metric": key_map["metric"],
                    "value_source": source_name,
                    "value_label": source_label,
                    "event_id": key_map["event_id"],
                    "passband": key_map["passband"],
                    "component": key_map["component"],
                    "period_s": key_map.get("period_s", np.nan),
                    **pairs,
                }
            )
    pair_df = pd.DataFrame(rows)
    if pair_df.empty:
        return pd.DataFrame()
    finite = pair_df.loc[pair_df["pair_count"].fillna(0) > 0].copy()
    empty = pair_df.loc[pair_df["pair_count"].fillna(0) <= 0].copy()
    summary_rows: list[dict[str, object]] = []
    for (group, metric, source, label), sub in finite.groupby(["metric_group", "metric", "value_source", "value_label"], sort=False):
        weights = pd.to_numeric(sub["weight_sum"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        corr = pd.to_numeric(sub["weighted_pair_correlation"], errors="coerce").to_numpy(dtype=float)
        mad = pd.to_numeric(sub["weighted_mean_abs_difference"], errors="coerce").to_numpy(dtype=float)
        valid_corr = np.isfinite(corr) & (weights > 0)
        valid_mad = np.isfinite(mad) & (weights > 0)
        summary_rows.append(
            {
                "metric_group": group,
                "metric": metric,
                "value_source": source,
                "value_label": label,
                "stratum_count": int(len(sub)),
                "pair_count": int(pd.to_numeric(sub["pair_count"], errors="coerce").fillna(0).sum()),
                "weighted_pair_correlation": weighted_average(corr[valid_corr], weights[valid_corr]),
                "weighted_mean_abs_difference": weighted_average(mad[valid_mad], weights[valid_mad]),
                "min_distance_km": float(np.nanmin(sub["min_pair_distance_km"])) if len(sub) else np.nan,
                "median_distance_km": float(np.nanmedian(sub["median_pair_distance_km"])) if len(sub) else np.nan,
                "max_distance_km": float(np.nanmax(sub["max_pair_distance_km"])) if len(sub) else np.nan,
            }
        )
    summary = pd.DataFrame(summary_rows)
    # Add no-data rows for expected metric/source combinations.
    existing = set(zip(summary["metric_group"], summary["metric"], summary["value_source"])) if not summary.empty else set()
    for group, metrics in GROUP_METRICS.items():
        for metric in metrics:
            for source_name, _value_col, source_label in VALUE_SOURCES:
                if (group, metric, source_name) not in existing:
                    summary = pd.concat(
                        [summary, pd.DataFrame([empty_spatial_row(group, metric, source_name, source_label)])],
                        ignore_index=True,
                    )
    return summary.sort_values(["metric_group", "metric", "value_source"]).reset_index(drop=True)


def empty_spatial_row(group: str, metric: str, source_name: str, source_label: str) -> dict[str, object]:
    return {
        "metric_group": group,
        "metric": metric,
        "value_source": source_name,
        "value_label": source_label,
        "stratum_count": 0,
        "pair_count": 0,
        "weighted_pair_correlation": np.nan,
        "weighted_mean_abs_difference": np.nan,
        "min_distance_km": np.nan,
        "median_distance_km": np.nan,
        "max_distance_km": np.nan,
    }


def nearby_pair_stats(sub: pd.DataFrame, value_col: str) -> dict[str, float | int] | None:
    values = pd.to_numeric(sub[value_col], errors="coerce").to_numpy(dtype=float)
    lat = pd.to_numeric(sub["sta_lat"], errors="coerce").to_numpy(dtype=float)
    lon = pd.to_numeric(sub["sta_lon"], errors="coerce").to_numpy(dtype=float)
    finite = np.isfinite(values) & np.isfinite(lat) & np.isfinite(lon)
    if finite.sum() < 2:
        return None
    values = values[finite]
    lat = lat[finite]
    lon = lon[finite]
    i, j = np.triu_indices(values.size, k=1)
    distances = haversine_km(lat[i], lon[i], lat[j], lon[j])
    keep = np.isfinite(distances) & (distances <= NEARBY_DISTANCE_KM)
    if not np.any(keep):
        return None
    i = i[keep]
    j = j[keep]
    distances = distances[keep]
    weights = 1.0 / np.maximum(distances, DISTANCE_EPSILON_KM)
    x = values[i]
    y = values[j]
    corr = weighted_corr(x, y, weights)
    mad = float(np.sum(weights * np.abs(x - y)) / np.sum(weights)) if np.sum(weights) > 0 else np.nan
    return {
        "pair_count": int(len(distances)),
        "weight_sum": float(np.sum(weights)),
        "weighted_pair_correlation": corr,
        "weighted_mean_abs_difference": mad,
        "min_pair_distance_km": float(np.min(distances)),
        "median_pair_distance_km": float(np.median(distances)),
        "max_pair_distance_km": float(np.max(distances)),
    }


def weighted_corr(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0)
    if finite.sum() < 3:
        return float("nan")
    x = x[finite]
    y = y[finite]
    w = weights[finite]
    w = w / w.sum()
    mx = float(np.sum(w * x))
    my = float(np.sum(w * y))
    cov = float(np.sum(w * (x - mx) * (y - my)))
    vx = float(np.sum(w * (x - mx) ** 2))
    vy = float(np.sum(w * (y - my) ** 2))
    if vx <= 0 or vy <= 0:
        return float("nan")
    return cov / math.sqrt(vx * vy)


def weighted_average(values: np.ndarray, weights: np.ndarray) -> float:
    if len(values) == 0 or len(weights) == 0 or np.sum(weights) <= 0:
        return float("nan")
    return float(np.sum(values * weights) / np.sum(weights))


def build_outlier_robustness(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for group, metrics in GROUP_METRICS.items():
        for metric in metrics:
            metric_df = df.loc[(df["metric_group"].eq(group)) & (df["metric"].eq(metric))].copy()
            for source_name, value_col, source_label in VALUE_SOURCES:
                values = pd.to_numeric(metric_df[value_col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().to_numpy(dtype=float)
                if values.size == 0:
                    for pct in TRIM_PERCENTILES:
                        rows.append(robustness_empty_row(group, metric, source_name, source_label, pct))
                    continue
                baseline = float(np.nanmean(values))
                q25, q75 = np.nanpercentile(values, [25, 75])
                iqr = float(q75 - q25) if np.isfinite(q75 - q25) and (q75 - q25) != 0 else float(np.nanstd(values))
                if not np.isfinite(iqr) or iqr == 0:
                    iqr = 1.0
                for pct in TRIM_PERCENTILES:
                    low, high = np.nanpercentile(values, [pct, 100.0 - pct])
                    trimmed = values[(values >= low) & (values <= high)]
                    winsor = np.clip(values, low, high)
                    trimmed_mean = float(np.nanmean(trimmed)) if trimmed.size else np.nan
                    winsor_mean = float(np.nanmean(winsor)) if winsor.size else np.nan
                    rows.append(
                        {
                            "metric_group": group,
                            "metric": metric,
                            "value_source": source_name,
                            "value_label": source_label,
                            "tail_percent": pct,
                            "row_count": int(values.size),
                            "trimmed_row_count": int(trimmed.size),
                            "lower_bound": float(low),
                            "upper_bound": float(high),
                            "untrimmed_mean": baseline,
                            "trimmed_mean": trimmed_mean,
                            "winsorized_mean": winsor_mean,
                            "median": float(np.nanmedian(values)),
                            "iqr": iqr,
                            "trimmed_change_iqr": (trimmed_mean - baseline) / iqr if np.isfinite(trimmed_mean) else np.nan,
                            "winsorized_change_iqr": (winsor_mean - baseline) / iqr if np.isfinite(winsor_mean) else np.nan,
                        }
                    )
    return pd.DataFrame(rows)


def robustness_empty_row(group: str, metric: str, source_name: str, source_label: str, pct: float) -> dict[str, object]:
    return {
        "metric_group": group,
        "metric": metric,
        "value_source": source_name,
        "value_label": source_label,
        "tail_percent": pct,
        "row_count": 0,
        "trimmed_row_count": 0,
        "lower_bound": np.nan,
        "upper_bound": np.nan,
        "untrimmed_mean": np.nan,
        "trimmed_mean": np.nan,
        "winsorized_mean": np.nan,
        "median": np.nan,
        "iqr": np.nan,
        "trimmed_change_iqr": np.nan,
        "winsorized_change_iqr": np.nan,
    }


def select_waveform_examples(df: pd.DataFrame, paths: RunPaths, n_per_metric: int) -> pd.DataFrame:
    missing_cols = [col for col in ["obs_waveform_path", "syn_waveform_path"] if col not in df.columns]
    if missing_cols:
        raise RuntimeError(f"metrics_long is missing waveform path columns: {missing_cols}")
    selections: list[pd.DataFrame] = []
    for group, metrics in GROUP_METRICS.items():
        for metric in metrics:
            sub = df.loc[(df["metric_group"].eq(group)) & (df["metric"].eq(metric))].copy()
            sub = sub.loc[np.isfinite(pd.to_numeric(sub["__plot_value"], errors="coerce"))].copy()
            if sub.empty:
                sub = df.loc[(df["metric_group"].eq(group)) & (df["metric"].eq(metric))].copy()
            sub["obs_abs_path"] = sub["obs_waveform_path"].map(lambda p: resolve_waveform_path(paths.repo_root, p))
            sub["syn_abs_path"] = sub["syn_waveform_path"].map(lambda p: resolve_waveform_path(paths.repo_root, p))
            sub = sub.loc[sub["obs_abs_path"].map(lambda p: Path(p).exists()) & sub["syn_abs_path"].map(lambda p: Path(p).exists())].copy()
            if sub.empty:
                raise RuntimeError(f"No existing observed/synthetic waveform paths for metric {metric}.")
            selected = deterministic_diverse_rows(sub, n_per_metric)
            selections.append(selected)
    out = pd.concat(selections, ignore_index=True) if selections else pd.DataFrame()
    keep_cols = [
        "metric_group",
        "metric",
        "event_id",
        "station",
        "component",
        "passband",
        "period_s",
        "distance_km",
        "sta_lat",
        "sta_lon",
        "value_obs",
        "value_syn",
        "__plot_value",
        "obs_abs_path",
        "syn_abs_path",
    ]
    keep_cols = [col for col in keep_cols if col in out.columns]
    return out[keep_cols].rename(columns={"__plot_value": "plot_value"}).reset_index(drop=True)


def deterministic_diverse_rows(sub: pd.DataFrame, n: int) -> pd.DataFrame:
    work = sub.copy()
    work["distance_bin"] = pd.qcut(work["distance_km"].rank(method="first"), q=min(5, max(1, len(work))), labels=False, duplicates="drop")
    work["lat_bin"] = pd.qcut(work["sta_lat"].rank(method="first"), q=min(4, max(1, len(work))), labels=False, duplicates="drop")
    work["lon_bin"] = pd.qcut(work["sta_lon"].rank(method="first"), q=min(4, max(1, len(work))), labels=False, duplicates="drop")
    work["period_token"] = pd.to_numeric(work.get("period_s", np.nan), errors="coerce").round(3).fillna(-1)
    sort_cols = ["passband", "component", "distance_bin", "lat_bin", "lon_bin", "event_id", "station", "period_token"]
    work = work.sort_values(sort_cols, kind="mergesort")
    key_cols = ["passband", "component", "distance_bin", "lat_bin", "lon_bin", "period_token"]
    first_pass = work.drop_duplicates(subset=key_cols, keep="first")
    if len(first_pass) >= n:
        return first_pass.head(n).copy()
    remaining = work.drop(index=first_pass.index, errors="ignore")
    combined = pd.concat([first_pass, remaining], ignore_index=False).drop_duplicates(
        subset=["event_id", "station", "component", "passband", "period_token"],
        keep="first",
    )
    if len(combined) < n:
        combined = pd.concat([combined, work.drop(index=combined.index, errors="ignore")], ignore_index=False)
    return combined.head(n).copy()


def resolve_waveform_path(repo_root: Path, value: object) -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "nan":
        return ""
    path = Path(text)
    if path.is_absolute():
        return str(path)
    return str(repo_root / path)


def plot_spatial_figures(summary: pd.DataFrame, output_dir: Path, manifest: dict[str, object]) -> None:
    for group, metrics in GROUP_METRICS.items():
        plot_df = summary.loc[summary["metric_group"].eq(group)].copy()
        fig, axes = plt.subplots(1, 3, figsize=(15, max(4.0, 0.6 * len(metrics) + 2.4)), dpi=180, sharey=True)
        if len(VALUE_SOURCES) == 1:
            axes = [axes]
        for ax, (source_name, _value_col, source_label) in zip(axes, VALUE_SOURCES):
            sub = plot_df.loc[plot_df["value_source"].eq(source_name)].copy()
            sub["metric"] = pd.Categorical(sub["metric"], categories=list(metrics), ordered=True)
            sub = sub.sort_values("metric")
            y = np.arange(len(metrics))
            values = sub.set_index("metric").reindex(metrics)["weighted_pair_correlation"].to_numpy(dtype=float)
            counts = sub.set_index("metric").reindex(metrics)["pair_count"].fillna(0).to_numpy(dtype=int)
            ax.axvline(0, color=TOKENS["ink"], linewidth=0.8, linestyle=":")
            ax.barh(y, np.nan_to_num(values, nan=0.0), color=COLORS["blue_light"], edgecolor=COLORS["blue"], linewidth=0.8)
            for yi, val, count in zip(y, values, counts):
                label = "no data" if not np.isfinite(val) or count == 0 else f"{val:.2f}  n={count:,}"
                ax.text(0.02 if not np.isfinite(val) else val + (0.03 if val >= 0 else -0.03), yi, label, va="center", ha="left" if (not np.isfinite(val) or val >= 0) else "right", fontsize=7.5, color=TOKENS["muted"])
            ax.set_yticks(y, [metric_label(m) for m in metrics])
            ax.set_xlim(-1.05, 1.05)
            ax.set_xlabel("Weighted nearby-pair correlation")
            ax.set_title(source_label, fontsize=10)
            ax.grid(axis="x", alpha=0.8)
        fig_header(
            fig,
            axes[0],
            f"{group.replace('_', ' ').title()} spatial consistency",
            "Station pairs within 10 km; inverse-distance weights w = 1 / max(distance_km, 0.25). Higher correlation means nearby stations vary more consistently.",
        )
        path = output_dir / "spatial_consistency" / f"{safe_token(group)}_spatial_consistency.png"
        savefig(fig, path)
        manifest["figures"].append(str(path))


def plot_robustness_figures(robustness: pd.DataFrame, output_dir: Path, manifest: dict[str, object]) -> None:
    line_styles = {"trimmed_change_iqr": "-", "winsorized_change_iqr": "--"}
    metric_colors = [COLORS["blue"], COLORS["orange"], COLORS["olive"], COLORS["pink"], COLORS["gold"], COLORS["neutral"]]
    for group, metrics in GROUP_METRICS.items():
        plot_df = robustness.loc[robustness["metric_group"].eq(group)].copy()
        fig, axes = plt.subplots(1, 3, figsize=(15, max(4.0, 0.6 * len(metrics) + 2.4)), dpi=180, sharey=True)
        for ax, (source_name, _value_col, source_label) in zip(axes, VALUE_SOURCES):
            sub = plot_df.loc[plot_df["value_source"].eq(source_name)].copy()
            for idx, metric in enumerate(metrics):
                metric_df = sub.loc[sub["metric"].eq(metric)].sort_values("tail_percent")
                if metric_df["row_count"].max() <= 0:
                    continue
                color = metric_colors[idx % len(metric_colors)]
                for col, style in line_styles.items():
                    label = f"{metric_label(metric)} {'trimmed' if col.startswith('trimmed') else 'capped'}"
                    ax.plot(metric_df["tail_percent"], metric_df[col], linestyle=style, marker="o", markersize=3, linewidth=1.1, color=color, alpha=0.95, label=label)
            ax.axhline(0, color=TOKENS["ink"], linewidth=0.8, linestyle=":")
            ax.set_xlabel("Symmetric tail threshold (%)")
            ax.set_title(source_label, fontsize=10)
            ax.grid(True, alpha=0.8)
        axes[0].set_ylabel("Mean change from 0% threshold (IQR units)")
        handles, labels = axes[-1].get_legend_handles_labels()
        if handles:
            fig.legend(handles, labels, loc="lower center", ncol=min(4, len(labels)), fontsize=7, frameon=False, bbox_to_anchor=(0.5, 0.01))
            fig.subplots_adjust(bottom=0.24)
        fig_header(
            fig,
            axes[0],
            f"{group.replace('_', ' ').title()} outlier robustness",
            "Sensitivity of trimmed and capped means at 0, 1, 2.5, 5, and 10 percent symmetric tail thresholds; y-axis is scaled by each metric/source IQR.",
        )
        path = output_dir / "outlier_robustness" / f"{safe_token(group)}_outlier_robustness.png"
        savefig(fig, path)
        manifest["figures"].append(str(path))


def plot_waveform_examples(selected: pd.DataFrame, paths: RunPaths, manifest: dict[str, object]) -> None:
    for (group, metric), sub in selected.groupby(["metric_group", "metric"], sort=False):
        sub = sub.reset_index(drop=True)
        chunks = [sub.iloc[i : i + 10].copy() for i in range(0, len(sub), 10)]
        for chunk_index, chunk in enumerate(chunks, start=1):
            rows = len(chunk)
            fig, axes = plt.subplots(rows, 1, figsize=(14, max(2.1 * rows, 4.0)), dpi=160, sharex=False)
            if rows == 1:
                axes = [axes]
            for ax, row in zip(axes, chunk.itertuples(index=False)):
                obs_data, obs_rate = load_npz_trace(Path(row.obs_abs_path))
                syn_data, syn_rate = load_npz_trace(Path(row.syn_abs_path))
                obs_data = bandpass_for_plot(obs_data, obs_rate, row.passband)
                syn_data = bandpass_for_plot(syn_data, syn_rate, row.passband)
                obs_t = np.arange(obs_data.size, dtype=float) / obs_rate if obs_rate > 0 else np.arange(obs_data.size)
                syn_t = np.arange(syn_data.size, dtype=float) / syn_rate if syn_rate > 0 else np.arange(syn_data.size)
                obs_scaled, syn_scaled = scale_pair(obs_data, syn_data)
                ax.plot(obs_t, obs_scaled, color=COLORS["blue"], linewidth=0.8, label="Observed")
                ax.plot(syn_t, syn_scaled, color=COLORS["orange"], linewidth=0.8, alpha=0.85, label="Synthetic")
                ax.axhline(0, color=TOKENS["axis"], linewidth=0.6)
                annotation = (
                    f"{row.event_id} | {row.station} {row.component} | {row.passband}"
                    f"{period_text(getattr(row, 'period_s', np.nan))} | dist={float(row.distance_km):.1f} km | "
                    f"obs={fmt(getattr(row, 'value_obs', np.nan))}, syn={fmt(getattr(row, 'value_syn', np.nan))}, plot={fmt(row.plot_value)}"
                )
                ax.text(0.005, 0.92, annotation, transform=ax.transAxes, va="top", ha="left", fontsize=7.2, color=TOKENS["ink"], bbox={"facecolor": TOKENS["panel"], "edgecolor": "none", "alpha": 0.78, "pad": 1.5})
                ax.set_ylabel("scaled", fontsize=7)
                ax.tick_params(labelsize=7)
                ax.grid(True, alpha=0.45)
            axes[0].legend(loc="upper right", frameon=False, fontsize=7, ncol=2)
            axes[-1].set_xlabel("Time from waveform start (s)")
            fig_header(
                fig,
                axes[0],
                f"{metric_label(metric)} waveform examples ({chunk_index}/{len(chunks)})",
                "Deterministic diverse rows from metrics_long; observed and synthetic traces are bandpassed from each row passband before scaling by the pair maximum absolute amplitude.",
                top=0.995,
                subtitle_y=0.973,
            )
            fig.subplots_adjust(hspace=0.55, top=0.93)
            path = paths.output_dir / "waveforms" / f"{safe_token(group)}_{safe_token(metric)}_waveforms_{chunk_index:02d}.png"
            savefig(fig, path)
            manifest["figures"].append(str(path))


def load_npz_trace(path: Path) -> tuple[np.ndarray, float]:
    data = np.load(path, allow_pickle=False)
    samples = np.asarray(data["data"], dtype=float)
    rate = float(np.asarray(data["sampling_rate"]).item()) if "sampling_rate" in data.files else 1.0
    if not np.isfinite(rate) or rate <= 0:
        rate = 1.0
    return samples, rate


def bandpass_for_plot(samples: np.ndarray, rate: float, passband: object) -> np.ndarray:
    corners = passband_corner_hz(passband)
    if corners is None:
        return np.asarray(samples, dtype=float)
    low_hz, high_hz = corners
    if not np.isfinite(rate) or rate <= 0:
        return np.asarray(samples, dtype=float)
    result = bandpass_with_metadata(np.asarray(samples, dtype=float), 1.0 / float(rate), low_hz, high_hz)
    filtered = np.asarray(result.data, dtype=float)
    mask = np.asarray(result.valid_mask, dtype=bool)
    if mask.shape == filtered.shape:
        filtered = np.where(mask, filtered, np.nan)
    return filtered


def passband_corner_hz(value: object) -> tuple[float, float] | None:
    numbers = [float(match) for match in re.findall(r"\d+(?:\.\d+)?", str(value or ""))]
    if len(numbers) < 2 or numbers[0] <= 0.0 or numbers[1] <= 0.0:
        return None
    period_min_s, period_max_s = min(numbers[0], numbers[1]), max(numbers[0], numbers[1])
    return 1.0 / period_max_s, 1.0 / period_min_s


def scale_pair(obs: np.ndarray, syn: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    finite_obs = obs[np.isfinite(obs)]
    finite_syn = syn[np.isfinite(syn)]
    if finite_obs.size == 0 and finite_syn.size == 0:
        return obs, syn
    scale = np.nanmax(np.abs(np.concatenate([finite_obs, finite_syn])))
    if not np.isfinite(scale) or scale <= 0:
        scale = 1.0
    return obs / scale, syn / scale


def summarize_missing_value_sources(df: pd.DataFrame) -> list[str]:
    warnings: list[str] = []
    for group, metrics in GROUP_METRICS.items():
        for metric in metrics:
            sub = df.loc[df["metric"].eq(metric)]
            for source_name, value_col, _label in VALUE_SOURCES:
                finite = int(np.isfinite(pd.to_numeric(sub[value_col], errors="coerce")).sum()) if value_col in sub else 0
                if finite == 0:
                    warnings.append(f"No finite {source_name} values for {group}/{metric}; related figure panels are marked no data.")
    return warnings


def haversine_km(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    radius = 6371.0088
    lat1r = np.radians(lat1)
    lat2r = np.radians(lat2)
    dlat = lat2r - lat1r
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2.0) ** 2
    return 2.0 * radius * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def metric_label(metric: object) -> str:
    labels = {
        "arias_duration": "Arias duration",
        "energy_duration": "Energy duration",
        "PGA": "PGA",
        "PGV": "PGV",
        "PGD": "PGD",
        "PSA": "PSA",
        "FAS": "FAS",
        "arias_intensity": "Arias intensity",
        "energy_intensity": "Energy intensity",
        "CAV": "CAV",
        "traveltime_delay": "Traveltime delay / period",
        "original_cc": "Original cross correlation",
        "delay_corrected_cc": "Delay-corrected cross correlation",
    }
    return labels.get(str(metric), str(metric).replace("_", " ").title())


def fig_header(fig: plt.Figure, ax: plt.Axes, title: str, subtitle: str, *, top: float = 0.985, subtitle_y: float = 0.935) -> None:
    left = ax.get_position().x0
    fig.text(left, top, textwrap.fill(title, 90, break_long_words=False), ha="left", va="top", fontsize=13, fontweight="semibold", color=TOKENS["ink"])
    fig.text(left, subtitle_y, textwrap.fill(subtitle, 145, break_long_words=False), ha="left", va="top", fontsize=8.5, color=TOKENS["muted"])


def savefig(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def safe_token(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_")
    return text or "unknown"


def fmt(value: object) -> str:
    try:
        val = float(value)
    except Exception:
        return "NA"
    if not np.isfinite(val):
        return "NA"
    if abs(val) >= 1000 or (abs(val) < 0.001 and val != 0):
        return f"{val:.2e}"
    return f"{val:.3f}"


def period_text(value: object) -> str:
    try:
        val = float(value)
    except Exception:
        return ""
    if not np.isfinite(val):
        return ""
    return f" | T={val:g}s"


if __name__ == "__main__":
    main()
