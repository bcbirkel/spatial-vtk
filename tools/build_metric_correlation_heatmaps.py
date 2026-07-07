"""Build observed/synthetic/residual correlation heatmaps from metrics_long.

This script is intentionally narrow: it reads a long metric table, keeps
comparable rows with finite observed, synthetic, and residual values, pivots
metric features wide without aggregation, and writes separate correlation
matrices plus heatmap figures for observed, synthetic, and residual values for
all passbands combined and for each passband. PSA and FAS period rows are
collapsed to one feature per metric before correlation/PCA.
"""

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
DEFAULT_OUTPUT_DIR = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/figures/user_requested_metric_correlations")
DEFAULT_MODEL = "cvmsi_20260506_material_0p6x1p2_asdf"
VALUE_COLUMNS = ("value_obs", "value_syn", "residual")
FINITE_COLUMNS = ("value_obs", "value_syn", "residual")
BASE_OBSERVATION_COLUMNS = ("event_id", "station", "component", "model", "passband")
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
VALUE_LABELS = {
    "value_obs": "Observed",
    "value_syn": "Synthetic",
    "residual": "Residual",
}
SPECTRAL_METRICS = {"PSA", "FAS"}


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    table_path = Path(args.metrics_long).expanduser()
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    df = _read_table(table_path)
    _require_columns(df, [*BASE_OBSERVATION_COLUMNS, "metric", "period_s", *FINITE_COLUMNS])
    source_rows = len(df)
    if args.model:
        df = df.loc[df["model"].astype(str).eq(str(args.model))].copy()
    model_rows = len(df)
    work = _finite_comparable_rows(df)
    if work.empty:
        raise ValueError("No rows have finite value_obs, value_syn, and residual after filtering.")

    passbands = _selected_passbands(work, args.passband)
    scopes: list[tuple[str, str | None]] = [("all_passbands", None)]
    scopes.extend((_scope_slug(passband), passband) for passband in passbands)

    manifest: dict[str, object] = {
        "input_table": str(table_path),
        "output_dir": str(output_dir),
        "model": args.model,
        "method": args.method,
        "source_rows": int(source_rows),
        "model_rows": int(model_rows),
        "finite_comparable_rows": int(len(work)),
        "finite_columns": list(FINITE_COLUMNS),
        "observation_columns": list(BASE_OBSERVATION_COLUMNS),
        "metric_feature": "metric, with PSA/FAS collapsed across period_s",
        "spectral_collapse": args.spectral_collapse,
        "pca": {
            "standardization": "z-score each metric feature after median-imputing missing values",
            "components_reported": args.pca_components,
            "grouping_rule": (
                "Each metric is assigned to the reported component with the largest absolute loading; "
                "component sign is kept so same-component opposite-sign metrics remain distinguishable."
            ),
        },
        "scopes": [],
    }

    for scope_name, passband in scopes:
        scope_df = work if passband is None else work.loc[work["passband"].astype(str).eq(str(passband))].copy()
        if scope_df.empty:
            continue
        scope_record: dict[str, object] = {
            "scope": scope_name,
            "passband": passband,
            "input_rows": int(len(scope_df)),
            "value_families": [],
        }
        for value_col in VALUE_COLUMNS:
            wide, variable_order, variable_labels = _build_wide_matrix(scope_df, value_col, collapse=args.spectral_collapse)
            corr = wide[variable_order].corr(method=args.method, min_periods=args.min_periods)
            counts = wide[variable_order].notna().astype(int).T.dot(wide[variable_order].notna().astype(int))
            corr.index = [variable_labels[col] for col in corr.index]
            corr.columns = [variable_labels[col] for col in corr.columns]
            counts.index = [variable_labels[col] for col in counts.index]
            counts.columns = [variable_labels[col] for col in counts.columns]

            stem = f"metric_value_correlation_{scope_name}__{_value_slug(value_col)}"
            corr_path = output_dir / f"{stem}.csv"
            count_path = output_dir / f"{stem}_pair_counts.csv"
            fig_path = output_dir / f"{stem}.png"
            corr.to_csv(corr_path)
            counts.to_csv(count_path)
            min_pair_count = int(counts.replace(0, np.nan).min().min()) if not counts.empty else 0
            max_pair_count = int(counts.max().max()) if not counts.empty else 0
            _plot_heatmap(
                corr,
                fig_path,
                title=_scope_title(passband, value_col=value_col, method=args.method),
                method=args.method,
                min_pair_count=min_pair_count,
                n_observations=int(len(wide)),
            )
            pca_paths = _write_pca_outputs(
                wide,
                variable_order,
                variable_labels,
                output_dir,
                stem,
                title=_pca_title(passband, value_col=value_col),
                n_components=args.pca_components,
            )

            scope_record["value_families"].append(
                {
                    "value_column": value_col,
                    "value_label": VALUE_LABELS[value_col],
                    "observations": int(len(wide)),
                    "variables": int(len(variable_order)),
                    "correlation_csv": str(corr_path),
                    "pair_count_csv": str(count_path),
                    "heatmap_png": str(fig_path),
                    "min_pair_count": min_pair_count,
                    "max_pair_count": max_pair_count,
                    **pca_paths,
                }
            )
        manifest["scopes"].append(scope_record)

    manifest_path = output_dir / "metric_value_correlation_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-long", default=str(DEFAULT_METRICS_LONG), help="Input metrics_long parquet/csv table.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for PNG, CSV, and manifest outputs.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model value to keep. Pass an empty string to disable filtering.")
    parser.add_argument("--passband", action="append", default=None, help="Passband to include. Repeat to override auto-discovered passbands.")
    parser.add_argument("--method", choices=["pearson", "spearman", "kendall"], default="pearson", help="Pandas correlation method.")
    parser.add_argument("--min-periods", type=int, default=2, help="Minimum paired observations for each correlation cell.")
    parser.add_argument(
        "--spectral-collapse",
        choices=["median", "mean"],
        default="median",
        help="How to collapse PSA/FAS period rows to one metric feature per observation.",
    )
    parser.add_argument("--pca-components", type=int, default=6, help="Maximum PCA components to report per value family/scope.")
    return parser.parse_args(argv)


def _read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".tsv", ".txt"}:
        return pd.read_csv(path, sep="\t")
    raise ValueError(f"Unsupported table format for {path}")


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")


def _finite_comparable_rows(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in FINITE_COLUMNS:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    finite = np.isfinite(out.loc[:, FINITE_COLUMNS].to_numpy(dtype=float)).all(axis=1)
    out = out.loc[finite].copy()
    out["metric"] = out["metric"].astype(str)
    out["passband"] = out["passband"].astype(str)
    out["period_s"] = pd.to_numeric(out["period_s"], errors="coerce")
    out["metric_feature"] = [_metric_feature(metric, period) for metric, period in zip(out["metric"], out["period_s"])]
    return out


def _metric_feature(metric: object, period_s: object) -> str:
    metric_text = str(metric)
    if metric_text in SPECTRAL_METRICS:
        return metric_text
    try:
        period = float(period_s)
    except (TypeError, ValueError):
        period = math.nan
    if np.isfinite(period):
        return f"{metric_text}@{period:g}s"
    return metric_text


def _selected_passbands(df: pd.DataFrame, requested: list[str] | None) -> list[str]:
    if requested:
        return list(dict.fromkeys(str(value) for value in requested))
    values = [str(value) for value in pd.unique(df["passband"].dropna()) if str(value).strip()]
    return sorted(values, key=_passband_sort_key)


def _passband_sort_key(value: object) -> tuple[float, str]:
    text = str(value)
    match = re.search(r"[-+]?\d*\.?\d+", text)
    return (float(match.group(0)) if match else float("inf"), text)


def _build_wide_matrix(df: pd.DataFrame, value_col: str, *, collapse: str) -> tuple[pd.DataFrame, list[str], dict[str, str]]:
    id_cols = [column for column in BASE_OBSERVATION_COLUMNS if column in df.columns]
    labels: dict[str, str] = {}
    metric_features = _ordered_metric_features(df["metric_feature"].dropna().unique())
    grouped = df.loc[:, [*id_cols, "metric_feature", value_col]].groupby([*id_cols, "metric_feature"], dropna=False, sort=False)[value_col]
    if collapse == "mean":
        collapsed = grouped.mean().reset_index()
    else:
        collapsed = grouped.median().reset_index()
    wide = collapsed.pivot(index=id_cols, columns="metric_feature", values=value_col)
    wide = wide.reindex(columns=metric_features)
    wide.columns = [f"{value_col}__{feature}" for feature in wide.columns]
    labels.update({f"{value_col}__{feature}": feature for feature in metric_features})
    combined = wide.reset_index()
    variable_order = [f"{value_col}__{feature}" for feature in metric_features]
    combined = combined[id_cols + variable_order]
    return combined, variable_order, labels


def _ordered_metric_features(values: Iterable[object]) -> list[str]:
    return sorted((str(value) for value in values), key=_metric_feature_sort_key)


def _metric_feature_sort_key(value: str) -> tuple[int, str, float]:
    if "@" in value and value.endswith("s"):
        metric, period_text = value.rsplit("@", 1)
        try:
            period = float(period_text[:-1])
        except ValueError:
            period = float("inf")
    else:
        metric = value
        period = -1.0
    try:
        metric_index = METRIC_ORDER.index(metric)
    except ValueError:
        metric_index = len(METRIC_ORDER)
    return (metric_index, metric, period)


def _plot_heatmap(corr: pd.DataFrame, output_path: Path, *, title: str, method: str, min_pair_count: int, n_observations: int) -> None:
    n = max(len(corr), 1)
    width = min(max(8.5, n * 0.32), 24.0)
    height = min(max(7.0, n * 0.32), 24.0)
    fig, ax = plt.subplots(figsize=(width, height), dpi=180)
    image = ax.imshow(corr.to_numpy(dtype=float), cmap="coolwarm", vmin=-1.0, vmax=1.0, interpolation="nearest")
    ax.set_xticks(np.arange(n))
    ax.set_yticks(np.arange(n))
    ax.set_xticklabels(corr.columns, rotation=90, fontsize=6)
    ax.set_yticklabels(corr.index, fontsize=6)
    ax.set_title(f"{title}\nN observations={n_observations:,}; min paired N={min_pair_count:,}", fontsize=11)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(f"{method.title()} correlation")
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def _write_pca_outputs(
    wide: pd.DataFrame,
    variable_order: list[str],
    variable_labels: dict[str, str],
    output_dir: Path,
    stem: str,
    *,
    title: str,
    n_components: int,
) -> dict[str, object]:
    labels = [variable_labels[col] for col in variable_order]
    matrix = wide[variable_order].apply(pd.to_numeric, errors="coerce")
    pca = _pca_from_frame(matrix, labels=labels, n_components=n_components)

    explained_path = output_dir / f"{stem}_pca_explained_variance.csv"
    loadings_path = output_dir / f"{stem}_pca_loadings.csv"
    grouping_path = output_dir / f"{stem}_pca_metric_grouping.csv"
    heatmap_path = output_dir / f"{stem}_pca_loadings.png"
    scatter_path = output_dir / f"{stem}_pca_pc1_pc2.png"

    pca["explained"].to_csv(explained_path, index=False)
    pca["loadings"].to_csv(loadings_path, index=False)
    pca["grouping"].to_csv(grouping_path, index=False)
    _plot_pca_loadings(pca["loadings"], heatmap_path, title=title)
    _plot_pca_scatter(pca["loadings"], scatter_path, title=title)
    return {
        "pca_explained_variance_csv": str(explained_path),
        "pca_loadings_csv": str(loadings_path),
        "pca_metric_grouping_csv": str(grouping_path),
        "pca_loadings_png": str(heatmap_path),
        "pca_pc1_pc2_png": str(scatter_path),
        "pca_complete_rows": int(pca["complete_rows"]),
        "pca_input_rows": int(len(matrix)),
        "pca_imputed_values": int(pca["imputed_values"]),
    }


def _pca_from_frame(matrix: pd.DataFrame, *, labels: list[str], n_components: int) -> dict[str, object]:
    values = matrix.to_numpy(dtype=float)
    complete_rows = int(np.isfinite(values).all(axis=1).sum())
    col_medians = np.nanmedian(values, axis=0)
    col_medians = np.where(np.isfinite(col_medians), col_medians, 0.0)
    missing = ~np.isfinite(values)
    imputed_values = int(missing.sum())
    if imputed_values:
        values = values.copy()
        values[missing] = np.take(col_medians, np.where(missing)[1])
    means = values.mean(axis=0)
    stds = values.std(axis=0, ddof=1)
    stds = np.where(np.isfinite(stds) & (stds > 0), stds, 1.0)
    z = (values - means) / stds
    max_components = max(1, min(int(n_components), z.shape[0] - 1 if z.shape[0] > 1 else 1, z.shape[1]))
    _u, singular, vt = np.linalg.svd(z, full_matrices=False)
    singular = singular[:max_components]
    components = vt[:max_components, :]
    denom = max(z.shape[0] - 1, 1)
    eigenvalues_all = (np.linalg.svd(z, full_matrices=False, compute_uv=False) ** 2) / denom
    total = float(np.sum(eigenvalues_all))
    explained_ratio = (singular**2 / denom) / total if total > 0 else np.full_like(singular, np.nan, dtype=float)
    component_names = [f"PC{i}" for i in range(1, max_components + 1)]

    explained = pd.DataFrame(
        {
            "component": component_names,
            "eigenvalue": singular**2 / denom,
            "explained_variance_ratio": explained_ratio,
            "cumulative_explained_variance_ratio": np.cumsum(explained_ratio),
        }
    )
    loading_rows: list[dict[str, object]] = []
    for feature, vector in zip(labels, components.T):
        row: dict[str, object] = {"metric_feature": feature}
        for name, loading in zip(component_names, vector):
            row[name] = float(loading)
        loading_rows.append(row)
    loadings = pd.DataFrame(loading_rows)
    grouping_rows: list[dict[str, object]] = []
    loading_matrix = loadings[component_names].to_numpy(dtype=float)
    for feature, row in zip(labels, loading_matrix):
        idx = int(np.nanargmax(np.abs(row))) if row.size else 0
        grouping_rows.append(
            {
                "metric_feature": feature,
                "dominant_component": component_names[idx],
                "dominant_loading": float(row[idx]),
                "dominant_abs_loading": float(abs(row[idx])),
                "dominant_sign": "positive" if row[idx] >= 0 else "negative",
                "suggested_group": f"{component_names[idx]}_{'positive' if row[idx] >= 0 else 'negative'}",
            }
        )
    grouping = pd.DataFrame(grouping_rows).sort_values(["dominant_component", "dominant_sign", "dominant_abs_loading"], ascending=[True, True, False])
    return {
        "explained": explained,
        "loadings": loadings,
        "grouping": grouping,
        "complete_rows": complete_rows,
        "imputed_values": imputed_values,
    }


def _plot_pca_loadings(loadings: pd.DataFrame, output_path: Path, *, title: str) -> None:
    component_cols = [col for col in loadings.columns if col.startswith("PC")]
    if not component_cols:
        return
    matrix = loadings.set_index("metric_feature")[component_cols]
    height = min(max(5.5, 0.42 * len(matrix) + 2.0), 12.0)
    width = min(max(8.0, 1.05 * len(component_cols) + 4.5), 12.0)
    fig, ax = plt.subplots(figsize=(width, height), dpi=180)
    image = ax.imshow(matrix.to_numpy(dtype=float), cmap="coolwarm", vmin=-1.0, vmax=1.0, interpolation="nearest", aspect="auto")
    ax.set_xticks(np.arange(len(component_cols)), component_cols, fontsize=8)
    ax.set_yticks(np.arange(len(matrix.index)), matrix.index, fontsize=8)
    ax.set_title(f"{title}\nPCA loadings", fontsize=11)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Loading")
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def _plot_pca_scatter(loadings: pd.DataFrame, output_path: Path, *, title: str) -> None:
    if "PC1" not in loadings.columns or "PC2" not in loadings.columns:
        return
    fig, ax = plt.subplots(figsize=(8.5, 7.0), dpi=180)
    ax.axhline(0.0, color="#7A828F", linewidth=0.8, linestyle=":")
    ax.axvline(0.0, color="#7A828F", linewidth=0.8, linestyle=":")
    ax.scatter(loadings["PC1"], loadings["PC2"], s=42, color="#5477C4", edgecolor="white", linewidth=0.7)
    for row in loadings.itertuples(index=False):
        ax.text(float(row.PC1) + 0.012, float(row.PC2) + 0.012, str(row.metric_feature), fontsize=8)
    ax.set_xlabel("PC1 loading")
    ax.set_ylabel("PC2 loading")
    ax.set_title(f"{title}\nPC1 vs PC2 feature loadings", fontsize=11)
    ax.grid(True, color="#E6E8F0", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def _scope_slug(passband: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", str(passband).strip()).strip("_").lower()
    return f"passband_{slug or 'blank'}"


def _value_slug(value_col: str) -> str:
    return {
        "value_obs": "observed",
        "value_syn": "synthetic",
        "residual": "residual",
    }.get(value_col, re.sub(r"[^A-Za-z0-9]+", "_", value_col).strip("_").lower())


def _scope_title(passband: str | None, *, value_col: str, method: str) -> str:
    scope = "all passbands combined" if passband is None else f"passband {passband}"
    return f"{VALUE_LABELS[value_col]} metric correlation ({method}, {scope})"


def _pca_title(passband: str | None, *, value_col: str) -> str:
    scope = "all passbands combined" if passband is None else f"passband {passband}"
    return f"{VALUE_LABELS[value_col]} metric PCA ({scope})"


if __name__ == "__main__":
    sys.exit(main())
