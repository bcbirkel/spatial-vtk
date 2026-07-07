"""Build metric-group spatial consistency, robustness, and waveform diagnostics."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DEFAULT_METRICS_LONG = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/tables/metrics_long.parquet")
DEFAULT_OUTPUT_DIR = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/figures/user_requested_metric_group_diagnostics")
DEFAULT_PROJECT_ROOT = Path("/project2/jvidale_1700/spatial-vtk")
DEFAULT_MODEL = "cvmsi_20260506_material_0p6x1p2_asdf"
PAIR_VALUE_METRICS = {"original_cc", "delay_corrected_cc"}
DELAY_FRACTION_COL = "delay_fraction_dominant_period"
FIELDS = ("value_obs", "value_syn", "metric_value")
FIELD_LABELS = {
    "value_obs": "Observed raw value",
    "value_syn": "Synthetic raw value",
    "metric_value": "Residual / metric-specific value",
}
METRIC_GROUP_ORDER = ("duration", "amplitude", "spectral", "intensity", "delay", "cross_correlation")
METRIC_ORDER = (
    "arias_duration",
    "energy_duration",
    "PGA",
    "PGV",
    "PGD",
    "PSA",
    "FAS",
    "arias_intensity",
    "energy_intensity",
    "CAV",
    "original_cc",
    "delay_corrected_cc",
    "traveltime_delay",
)
PASSBANDS = ("1-2 sec", "2-3 sec", "3-5 sec")
ROBUSTNESS_PERCENTILES = (0.0, 1.0, 2.5, 5.0, 10.0)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    metrics_path = Path(args.metrics_long).expanduser()
    output_dir = Path(args.output_dir).expanduser()
    project_root = Path(args.project_root).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    columns = [
        "event_id",
        "station",
        "component",
        "model",
        "passband",
        "metric_group",
        "metric",
        "period_s",
        "value",
        "value_obs",
        "value_syn",
        "log2_residual",
        "obs_waveform_path",
        "syn_waveform_path",
        "distance_km",
        "event_lat",
        "event_lon",
        "sta_lat",
        "sta_lon",
    ]
    df = pd.read_parquet(metrics_path, columns=columns)
    if args.model:
        df = df.loc[df["model"].astype(str).eq(str(args.model))].copy()
    df = _prepare_metric_values(df)
    groups = _ordered_values(df["metric_group"].dropna().unique(), METRIC_GROUP_ORDER)
    metrics = _ordered_values(df["metric"].dropna().unique(), METRIC_ORDER)
    station_pairs = _station_pairs_within_km(df, max_km=float(args.neighbor_km))

    consistency = _build_spatial_consistency(df, station_pairs)
    robustness = _build_robustness(df)
    consistency_path = output_dir / "weighted_neighbor_spatial_consistency.csv"
    robustness_path = output_dir / "percentile_sensitivity_robustness.csv"
    consistency.to_csv(consistency_path, index=False)
    robustness.to_csv(robustness_path, index=False)

    figures: list[dict[str, object]] = []
    for group in groups:
        group_consistency = consistency.loc[consistency["metric_group"].astype(str).eq(str(group))]
        if not group_consistency.empty:
            path = output_dir / f"spatial_consistency__{_slug(group)}.png"
            _plot_spatial_consistency(group_consistency, path, group=str(group), neighbor_km=float(args.neighbor_km))
            figures.append({"kind": "spatial_consistency", "metric_group": str(group), "figure": str(path)})
        group_robustness = robustness.loc[robustness["metric_group"].astype(str).eq(str(group))]
        if not group_robustness.empty:
            path = output_dir / f"outlier_robustness_percentile_sensitivity__{_slug(group)}.png"
            _plot_robustness(group_robustness, path, group=str(group))
            figures.append({"kind": "outlier_robustness", "metric_group": str(group), "figure": str(path)})

    waveform_records: list[dict[str, object]] = []
    waveform_dir = output_dir / "waveform_examples"
    waveform_dir.mkdir(parents=True, exist_ok=True)
    for metric in metrics:
        metric_rows = df.loc[df["metric"].astype(str).eq(str(metric))].copy()
        selected = _select_waveform_examples(metric_rows, max_records=int(args.waveform_count))
        if selected.empty:
            continue
        path = waveform_dir / f"waveform_examples__{_slug(metric)}.png"
        result_rows = _plot_waveform_examples(selected, path, metric=str(metric), project_root=project_root)
        waveform_records.extend(result_rows)
        figures.append(
            {
                "kind": "waveform_examples",
                "metric": str(metric),
                "selected_rows": int(len(selected)),
                "rendered_rows": int(sum(row.get("status") == "rendered" for row in result_rows)),
                "figure": str(path),
            }
        )

    waveform_path = output_dir / "waveform_example_selection.csv"
    pd.DataFrame(waveform_records).to_csv(waveform_path, index=False)
    manifest = {
        "input_table": str(metrics_path),
        "output_dir": str(output_dir),
        "model": args.model,
        "neighbor_km": float(args.neighbor_km),
        "neighbor_weight": "triangular: max(0, 1 - station_pair_distance_km / neighbor_km)",
        "fields": list(FIELDS),
        "robustness_percentiles": list(ROBUSTNESS_PERCENTILES),
        "waveform_count_per_metric": int(args.waveform_count),
        "station_neighbor_pairs": int(len(station_pairs)),
        "consistency_csv": str(consistency_path),
        "robustness_csv": str(robustness_path),
        "waveform_selection_csv": str(waveform_path),
        "figures": figures,
    }
    manifest_path = output_dir / "metric_group_diagnostics_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-long", default=str(DEFAULT_METRICS_LONG))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--project-root", default=str(DEFAULT_PROJECT_ROOT))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--neighbor-km", type=float, default=10.0)
    parser.add_argument("--waveform-count", type=int, default=30)
    return parser.parse_args(argv)


def _prepare_metric_values(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["period_key"] = pd.to_numeric(out["period_s"], errors="coerce").map(lambda value: f"{value:g}" if np.isfinite(value) else "")
    out[DELAY_FRACTION_COL] = _delay_fraction(out)
    out["metric_value"] = np.nan
    for metric in out["metric"].dropna().astype(str).unique():
        mask = out["metric"].astype(str).eq(metric)
        value_col = _metric_value_column(metric)
        out.loc[mask, "metric_value"] = pd.to_numeric(out.loc[mask, value_col], errors="coerce")
    for column in ("value_obs", "value_syn", "metric_value", "distance_km"):
        out[column] = pd.to_numeric(out[column], errors="coerce")
    return out


def _delay_fraction(df: pd.DataFrame) -> pd.Series:
    delay = pd.to_numeric(df["value"], errors="coerce")
    denominator = df["passband"].map(_period_from_passband_label)
    finite = np.isfinite(delay) & np.isfinite(denominator) & (denominator > 0.0)
    return pd.Series(np.where(finite, delay / denominator, np.nan), index=df.index)


def _period_from_passband_label(value: object) -> float:
    numbers = [float(match) for match in re.findall(r"\d+(?:\.\d+)?", str(value or "").lower())]
    if len(numbers) >= 2 and numbers[0] > 0.0 and numbers[1] > 0.0:
        return float(math.sqrt(numbers[0] * numbers[1]))
    if len(numbers) == 1 and numbers[0] > 0.0:
        return float(numbers[0])
    return float("nan")


def _metric_value_column(metric: str) -> str:
    if metric in PAIR_VALUE_METRICS:
        return "value"
    if metric == "traveltime_delay":
        return DELAY_FRACTION_COL
    return "log2_residual"


def _station_pairs_within_km(df: pd.DataFrame, *, max_km: float) -> pd.DataFrame:
    stations = df.loc[:, ["station", "sta_lat", "sta_lon"]].dropna().drop_duplicates("station").copy()
    rows: list[dict[str, object]] = []
    records = list(stations.itertuples(index=False))
    for i, left in enumerate(records):
        for right in records[i + 1 :]:
            distance = _haversine_km(float(left.sta_lat), float(left.sta_lon), float(right.sta_lat), float(right.sta_lon))
            if distance <= max_km:
                rows.append(
                    {
                        "station_a": str(left.station),
                        "station_b": str(right.station),
                        "station_pair_distance_km": float(distance),
                        "weight": float(max(0.0, 1.0 - distance / max_km)),
                    }
                )
    return pd.DataFrame(rows)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * radius * math.asin(min(1.0, math.sqrt(a)))


def _build_spatial_consistency(df: pd.DataFrame, station_pairs: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if station_pairs.empty:
        return pd.DataFrame()
    key_cols = ["event_id", "component", "model", "passband", "metric", "period_key"]
    for metric, metric_df in df.groupby("metric", sort=False):
        metric_group = _first_nonnull(metric_df["metric_group"])
        for field in FIELDS:
            sub = metric_df.loc[np.isfinite(metric_df[field]), [*key_cols, "station", field]].copy()
            if sub.empty:
                continue
            left = station_pairs.merge(sub, left_on="station_a", right_on="station", how="inner").drop(columns=["station"])
            paired = left.merge(
                sub,
                left_on=[*key_cols, "station_b"],
                right_on=[*key_cols, "station"],
                how="inner",
                suffixes=("_a", "_b"),
            )
            if paired.empty:
                continue
            values_a = pd.to_numeric(paired[f"{field}_a"], errors="coerce").to_numpy(dtype=float)
            values_b = pd.to_numeric(paired[f"{field}_b"], errors="coerce").to_numpy(dtype=float)
            weights = pd.to_numeric(paired["weight"], errors="coerce").to_numpy(dtype=float)
            finite = np.isfinite(values_a) & np.isfinite(values_b) & np.isfinite(weights) & (weights > 0.0)
            if not finite.any():
                continue
            corr = _weighted_corr(values_a[finite], values_b[finite], weights[finite])
            rows.append(
                {
                    "metric_group": metric_group,
                    "metric": metric,
                    "field": field,
                    "nearby_pair_rows": int(finite.sum()),
                    "unique_station_pairs": int(paired.loc[finite, ["station_a", "station_b"]].drop_duplicates().shape[0]),
                    "weighted_neighbor_correlation": corr,
                    "weighted_mean_abs_difference": float(np.average(np.abs(values_a[finite] - values_b[finite]), weights=weights[finite])),
                    "median_station_pair_distance_km": float(np.nanmedian(paired.loc[finite, "station_pair_distance_km"])),
                }
            )
    return pd.DataFrame(rows)


def _weighted_corr(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    if len(x) < 2:
        return float("nan")
    wsum = float(np.sum(w))
    if wsum <= 0.0:
        return float("nan")
    mean_x = float(np.sum(w * x) / wsum)
    mean_y = float(np.sum(w * y) / wsum)
    cov = float(np.sum(w * (x - mean_x) * (y - mean_y)) / wsum)
    var_x = float(np.sum(w * (x - mean_x) ** 2) / wsum)
    var_y = float(np.sum(w * (y - mean_y) ** 2) / wsum)
    denom = math.sqrt(var_x * var_y)
    return cov / denom if denom > 0.0 else float("nan")


def _build_robustness(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (metric_group, metric), metric_df in df.groupby(["metric_group", "metric"], sort=False):
        for field in FIELDS:
            values = pd.to_numeric(metric_df[field], errors="coerce").dropna().to_numpy(dtype=float)
            if values.size == 0:
                continue
            iqr = np.nanpercentile(values, 75.0) - np.nanpercentile(values, 25.0)
            scale = float(iqr) if np.isfinite(iqr) and iqr > 0.0 else float(np.nanstd(values))
            raw_mean = float(np.nanmean(values))
            raw_median = float(np.nanmedian(values))
            for percentile in ROBUSTNESS_PERCENTILES:
                trimmed = _trim_values(values, percentile)
                rows.append(
                    {
                        "metric_group": metric_group,
                        "metric": metric,
                        "field": field,
                        "tail_percentile": float(percentile),
                        "n_raw": int(values.size),
                        "n_after_trim": int(trimmed.size),
                        "raw_mean": raw_mean,
                        "trimmed_mean": float(np.nanmean(trimmed)) if trimmed.size else np.nan,
                        "raw_median": raw_median,
                        "trimmed_median": float(np.nanmedian(trimmed)) if trimmed.size else np.nan,
                        "iqr_scale": scale,
                        "normalized_mean_shift": (
                            float((np.nanmean(trimmed) - raw_mean) / scale)
                            if trimmed.size and np.isfinite(scale) and scale > 0.0
                            else np.nan
                        ),
                    }
                )
    return pd.DataFrame(rows)


def _trim_values(values: np.ndarray, percentile: float) -> np.ndarray:
    finite = values[np.isfinite(values)]
    if finite.size == 0 or percentile <= 0.0:
        return finite
    lo, hi = np.nanpercentile(finite, [percentile, 100.0 - percentile])
    return finite[(finite >= lo) & (finite <= hi)]


def _plot_spatial_consistency(df: pd.DataFrame, output_path: Path, *, group: str, neighbor_km: float) -> None:
    metrics = _ordered_values(df["metric"].dropna().unique(), METRIC_ORDER)
    x = np.arange(len(metrics))
    fig, axes = plt.subplots(1, 2, figsize=(max(10.0, 1.25 * len(metrics) + 3.0), 5.2), dpi=180, constrained_layout=True)
    width = 0.24
    offsets = {"value_obs": -width, "value_syn": 0.0, "metric_value": width}
    for field in FIELDS:
        sub = df.loc[df["field"].eq(field)].set_index("metric")
        axes[0].bar(x + offsets[field], [sub["weighted_neighbor_correlation"].get(metric, np.nan) for metric in metrics], width=width, label=FIELD_LABELS[field])
        axes[1].bar(x + offsets[field], [sub["weighted_mean_abs_difference"].get(metric, np.nan) for metric in metrics], width=width, label=FIELD_LABELS[field])
    axes[0].set_ylabel("Weighted neighbor correlation")
    axes[0].set_ylim(-1.0, 1.0)
    axes[1].set_ylabel("Weighted mean absolute difference")
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(metrics, rotation=35, ha="right")
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_title(f"{group}: nearby station similarity (<={neighbor_km:g} km)")
    axes[1].set_title("Neighbor difference magnitude")
    axes[0].legend(fontsize=8)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def _plot_robustness(df: pd.DataFrame, output_path: Path, *, group: str) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(14.0, 4.8), dpi=180, sharex=True, constrained_layout=True)
    for ax, field in zip(axes, FIELDS):
        sub = df.loc[df["field"].eq(field)].copy()
        for metric in _ordered_values(sub["metric"].dropna().unique(), METRIC_ORDER):
            metric_rows = sub.loc[sub["metric"].astype(str).eq(metric)].sort_values("tail_percentile")
            ax.plot(metric_rows["tail_percentile"], metric_rows["normalized_mean_shift"], marker="o", linewidth=1.2, label=metric)
        ax.axhline(0.0, color="#555555", linewidth=0.8, linestyle="--", alpha=0.65)
        ax.set_title(FIELD_LABELS[field])
        ax.set_xlabel("Symmetric tail trim (%)")
        ax.grid(True, alpha=0.25)
    axes[0].set_ylabel("Mean shift from untrimmed / IQR")
    axes[-1].legend(fontsize=7, loc="best")
    fig.suptitle(f"{group}: percentile sensitivity to outliers", fontsize=12)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def _select_waveform_examples(df: pd.DataFrame, *, max_records: int) -> pd.DataFrame:
    cols = [
        "metric_group",
        "metric",
        "event_id",
        "station",
        "component",
        "passband",
        "period_s",
        "value_obs",
        "value_syn",
        "metric_value",
        "distance_km",
        "event_lat",
        "event_lon",
        "sta_lat",
        "sta_lon",
        "obs_waveform_path",
        "syn_waveform_path",
    ]
    work = df.loc[:, cols].dropna(subset=["obs_waveform_path", "syn_waveform_path", "distance_km", "event_lat", "event_lon", "sta_lat", "sta_lon"]).copy()
    if work.empty:
        return work
    work = work.drop_duplicates(["event_id", "station", "component", "passband"])
    work["distance_bin"] = pd.qcut(work["distance_km"].rank(method="first"), q=min(5, len(work)), labels=False, duplicates="drop")
    work["event_lon_bin"] = pd.qcut(work["event_lon"].rank(method="first"), q=min(5, len(work)), labels=False, duplicates="drop")
    work["sort_key"] = (
        work["passband"].astype(str)
        + "|"
        + work["component"].astype(str)
        + "|"
        + work["distance_bin"].astype(str)
        + "|"
        + work["event_lon_bin"].astype(str)
        + "|"
        + work["event_id"].astype(str)
        + "|"
        + work["station"].astype(str)
    )
    work = work.sort_values(["sort_key", "distance_km", "event_id", "station"])
    strata = ["passband", "component", "distance_bin", "event_lon_bin"]
    selected_parts = []
    for _key, group in work.groupby(strata, dropna=False, sort=True):
        selected_parts.append(group.head(1))
        if sum(len(part) for part in selected_parts) >= max_records:
            break
    selected = pd.concat(selected_parts, ignore_index=True, sort=False) if selected_parts else work.head(0)
    if len(selected) < max_records:
        used = set(zip(selected["event_id"], selected["station"], selected["component"], selected["passband"]))
        extra_rows = []
        for row in work.itertuples(index=False):
            key = (row.event_id, row.station, row.component, row.passband)
            if key in used:
                continue
            extra_rows.append(row._asdict())
            used.add(key)
            if len(selected) + len(extra_rows) >= max_records:
                break
        if extra_rows:
            selected = pd.concat([selected, pd.DataFrame(extra_rows)], ignore_index=True, sort=False)
    return selected.head(max_records).copy()


def _plot_waveform_examples(df: pd.DataFrame, output_path: Path, *, metric: str, project_root: Path) -> list[dict[str, object]]:
    n = min(len(df), 30)
    cols = 5
    rows = int(math.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(18.0, max(3.0, 2.25 * rows)), dpi=160, squeeze=False)
    result_rows: list[dict[str, object]] = []
    for ax in axes.ravel():
        ax.axis("off")
    for idx, row in enumerate(df.head(n).itertuples(index=False)):
        ax = axes.ravel()[idx]
        ax.axis("on")
        obs_path = _resolve_path(getattr(row, "obs_waveform_path"), project_root)
        syn_path = _resolve_path(getattr(row, "syn_waveform_path"), project_root)
        status = "rendered"
        message = ""
        try:
            obs_data, obs_rate = _read_npz_waveform(obs_path)
            syn_data, syn_rate = _read_npz_waveform(syn_path)
            _plot_one_waveform_panel(ax, obs_data, obs_rate, syn_data, syn_rate)
        except Exception as exc:
            status = "failed"
            message = f"{type(exc).__name__}: {exc}"
            ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes, fontsize=7)
        title = f"{row.event_id} {row.station}.{row.component} {row.passband}"
        ax.set_title(title, fontsize=7.5)
        value_text = (
            f"dist={float(row.distance_km):.1f} km\n"
            f"obs={_fmt(row.value_obs)} syn={_fmt(row.value_syn)}\n"
            f"value={_fmt(row.metric_value)}"
        )
        ax.text(0.02, 0.96, value_text, transform=ax.transAxes, va="top", ha="left", fontsize=6.5, bbox={"facecolor": "white", "alpha": 0.72, "edgecolor": "none"})
        result_rows.append(
            {
                "metric": metric,
                "event_id": row.event_id,
                "station": row.station,
                "component": row.component,
                "passband": row.passband,
                "distance_km": row.distance_km,
                "obs_waveform_path": str(obs_path),
                "syn_waveform_path": str(syn_path),
                "status": status,
                "message": message,
                "figure": str(output_path),
            }
        )
    handles = [
        plt.Line2D([0], [0], color="#2B6CB0", linewidth=1.0, label="Observed"),
        plt.Line2D([0], [0], color="#C2410C", linewidth=1.0, label="Synthetic"),
    ]
    fig.legend(handles=handles, loc="upper right")
    fig.suptitle(f"{metric}: deterministic waveform examples", fontsize=13)
    fig.tight_layout(rect=(0, 0, 0.98, 0.97))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return result_rows


def _resolve_path(path_value: object, project_root: Path) -> Path:
    path = Path(str(path_value))
    return path if path.is_absolute() else project_root / path


def _read_npz_waveform(path: Path) -> tuple[np.ndarray, float]:
    data = np.load(path, allow_pickle=False)
    samples = np.asarray(data["data"], dtype=float).reshape(-1)
    sampling_rate = float(np.asarray(data["sampling_rate"]).reshape(-1)[0])
    return samples, sampling_rate


def _plot_one_waveform_panel(ax: plt.Axes, obs: np.ndarray, obs_rate: float, syn: np.ndarray, syn_rate: float) -> None:
    max_seconds = min(90.0, len(obs) / obs_rate if obs_rate > 0 else 90.0, len(syn) / syn_rate if syn_rate > 0 else 90.0)
    obs_n = max(1, min(len(obs), int(max_seconds * obs_rate)))
    syn_n = max(1, min(len(syn), int(max_seconds * syn_rate)))
    obs_t = np.arange(obs_n) / obs_rate
    syn_t = np.arange(syn_n) / syn_rate
    scale = max(float(np.nanmax(np.abs(obs[:obs_n]))) if obs_n else 0.0, float(np.nanmax(np.abs(syn[:syn_n]))) if syn_n else 0.0, 1.0e-12)
    ax.plot(obs_t, obs[:obs_n] / scale, color="#2B6CB0", linewidth=0.75)
    ax.plot(syn_t, syn[:syn_n] / scale, color="#C2410C", linewidth=0.75, alpha=0.85)
    ax.set_xlim(0.0, max_seconds)
    ax.set_ylim(-1.05, 1.05)
    ax.tick_params(labelsize=6)
    ax.grid(True, alpha=0.18)


def _fmt(value: object) -> str:
    try:
        number = float(value)
    except Exception:
        return "nan"
    if not np.isfinite(number):
        return "nan"
    return f"{number:.3g}"


def _first_nonnull(series: pd.Series) -> object:
    values = series.dropna()
    return values.iloc[0] if len(values) else pd.NA


def _ordered_values(values: Iterable[object], preferred: Iterable[object]) -> list[str]:
    texts = [str(value) for value in values]
    order = {str(value): index for index, value in enumerate(preferred)}
    return sorted(texts, key=lambda value: (order.get(value, len(order)), value.casefold()))


def _slug(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", str(value).strip()).strip("_").lower() or "unknown"


if __name__ == "__main__":
    sys.exit(main())
