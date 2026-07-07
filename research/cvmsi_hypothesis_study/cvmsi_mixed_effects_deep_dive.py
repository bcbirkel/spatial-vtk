#!/usr/bin/env python3
"""Fuller mixed-effects analysis for CVM-SI observed/synthetic residuals.

This script is intentionally separate from the first-pass descriptive scans.
It fits nested crossed event/station mixed-effects models to raw log2(obs/syn)
residuals so that event demeaning remains a diagnostic rather than the primary
inferential layer.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import warnings
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

try:
    import seaborn as sns
except Exception:  # pragma: no cover - environment dependent
    sns = None


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "outputs" / "review" / "cvmsi_hypothesis_study" / "tables" / "pairs.csv"
DEFAULT_OUTPUT = REPO_ROOT / "outputs" / "review" / "cvmsi_hypothesis_study" / "mixed_effects"
RANDOM_SEED = 20260630
METRICS = ("PGA", "PGV", "arias_duration", "energy_intensity")

FONT_FAMILY = ["Aptos", "Inter", "Segoe UI", "DejaVu Sans", "Arial", "sans-serif"]
MONO_FONT_FAMILY = ["SF Mono", "Menlo", "Consolas", "DejaVu Sans Mono", "monospace"]

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}

NEUTRAL_MARKS = {
    "open": TOKENS["panel"],
    "xlight": "#F4F5F7",
    "light": "#E2E5EA",
    "base": "#C5CAD3",
    "mid": "#7A828F",
    "dark": "#464C55",
}

COLOR_FAMILIES = {
    "blue": {"open": TOKENS["panel"], "xlight": "#EAF1FE", "light": "#CEDFFE", "base": "#A3BEFA", "mid": "#5477C4", "dark": "#2E4780"},
    "gold": {"open": TOKENS["panel"], "xlight": "#FFF4C2", "light": "#FFEA8F", "base": "#FFE15B", "mid": "#B8A037", "dark": "#736422"},
    "orange": {"open": TOKENS["panel"], "xlight": "#FFEDDE", "light": "#FFBDA1", "base": "#F0986E", "mid": "#CC6F47", "dark": "#804126"},
    "olive": {"open": TOKENS["panel"], "xlight": "#D8ECBD", "light": "#BEEB96", "base": "#A3D576", "mid": "#71B436", "dark": "#386411"},
    "pink": {"open": TOKENS["panel"], "xlight": "#FCDAD6", "light": "#F5BACC", "base": "#F390CA", "mid": "#BD569B", "dark": "#8A3A6F"},
}


@dataclass(frozen=True)
class ModelSpec:
    name: str
    label: str
    formula_rhs: str
    description: str
    requires_vs30: bool = False
    random_slope: bool = False


MODEL_SPECS = (
    ModelSpec(
        "m00_intercepts_only",
        "Random intercepts",
        "1",
        "Only the grand mean plus crossed station and event random intercepts.",
    ),
    ModelSpec(
        "m01_band",
        "Band",
        "C(band)",
        "Adds the period-band mean structure.",
    ),
    ModelSpec(
        "m02_source_distance",
        "Band + source/distance",
        "C(band) + log_distance_z + magnitude_z + event_depth_km_z + C(faulting_type)",
        "Adds source magnitude/depth/mechanism and hypocentral distance.",
    ),
    ModelSpec(
        "m03_path_site",
        "Source + path/site",
        (
            "C(band) + log_distance_z + magnitude_z + event_depth_km_z + C(faulting_type) + "
            "path_basin_fraction_z + path_la_basin_fraction_z + C(path_class) + C(station_region_type)"
        ),
        "Adds basin path fractions, discrete path class, and broad station geomorphology.",
    ),
    ModelSpec(
        "m04_frequency_interactions",
        "Frequency interactions",
        (
            "C(band) * log_distance_z + C(band) * path_basin_fraction_z + "
            "C(band) * path_la_basin_fraction_z + magnitude_z + event_depth_km_z + "
            "C(faulting_type) + C(path_class) + C(station_region_type)"
        ),
        "Allows distance and basin-path effects to vary by period band.",
    ),
)

VS30_SPECS = (
    ModelSpec(
        "m04_frequency_interactions_vs30_subset",
        "Frequency interactions, Vs30 subset",
        MODEL_SPECS[-1].formula_rhs,
        "The full primary model refit on rows with model/Vs30 mismatch available.",
        requires_vs30=True,
    ),
    ModelSpec(
        "m05_velocity_mismatch_subset",
        "Add model/Vs30 mismatch",
        MODEL_SPECS[-1].formula_rhs + " + log2_model_vs30_ratio_z + C(band):log2_model_vs30_ratio_z",
        "Adds local CVM-SI surface Vs versus station Vs30 mismatch on the same reduced row set.",
        requires_vs30=True,
    ),
)

RANDOM_SLOPE_SPECS = (
    ModelSpec(
        "m06_station_distance_random_slope",
        "Station distance random slope",
        MODEL_SPECS[-1].formula_rhs,
        "Sensitivity model with station-specific distance slopes and event random intercepts.",
        random_slope=True,
    ),
)

TERM_LABELS = {
    "log_distance_z": "Distance",
    "path_basin_fraction_z": "Basin path",
    "path_la_basin_fraction_z": "LA basin path",
    "magnitude_z": "Magnitude",
    "event_depth_km_z": "Depth",
    "C(station_region_type)[T.Hills]": "Station hills",
    "C(station_region_type)[T.Valley]": "Station valley",
    "C(band)[T.3-5 sec]:log_distance_z": "3-5 s x distance",
    "C(band)[T.3-5 sec]:path_basin_fraction_z": "3-5 s x basin path",
    "C(band)[T.3-5 sec]:path_la_basin_fraction_z": "3-5 s x LA basin path",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs-csv", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metrics", nargs="+", default=list(METRICS), choices=list(METRICS))
    parser.add_argument("--max-rows-per-metric", type=int, default=0, help="Optional deterministic sample per metric; 0 uses all rows.")
    parser.add_argument("--run-random-slope", action="store_true", help="Run slower station distance random-slope sensitivity models.")
    parser.add_argument("--maxiter", type=int, default=180)
    return parser.parse_args()


def use_chart_theme() -> None:
    rc = {
        "figure.facecolor": TOKENS["surface"],
        "figure.edgecolor": "none",
        "savefig.facecolor": "white",
        "savefig.edgecolor": "none",
        "axes.facecolor": TOKENS["panel"],
        "axes.edgecolor": TOKENS["axis"],
        "axes.labelcolor": TOKENS["ink"],
        "axes.grid": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.color": TOKENS["grid"],
        "grid.linewidth": 0.8,
        "font.family": "sans-serif",
        "font.sans-serif": FONT_FAMILY,
        "font.monospace": MONO_FONT_FAMILY,
        "patch.linewidth": 1.0,
    }
    if sns is not None:
        sns.set_theme(style="whitegrid", rc=rc)
    else:
        plt.rcParams.update(rc)


def add_chart_header(fig: plt.Figure, ax: plt.Axes, title: str, subtitle: str, *, title_width: int = 92, subtitle_width: int = 128) -> None:
    import textwrap

    title = textwrap.fill(str(title).strip(), width=title_width, break_long_words=False)
    subtitle = textwrap.fill(str(subtitle).strip(), width=subtitle_width, break_long_words=False)
    title_lines = title.count("\n") + 1
    subtitle_lines = subtitle.count("\n") + 1
    ax.set_title("")
    fig.subplots_adjust(top=max(0.66, 0.88 - 0.040 * (title_lines - 1) - 0.030 * (subtitle_lines - 1)))
    left = ax.get_position().x0
    fig.text(left, 0.985, title, ha="left", va="top", fontsize=17, fontweight="semibold", color=TOKENS["ink"], linespacing=1.08)
    fig.text(left, 0.94 - 0.044 * (title_lines - 1), subtitle, ha="left", va="top", fontsize=12, color=TOKENS["muted"], linespacing=1.18)
    if sns is not None:
        sns.despine(ax=ax)
    else:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)


def classify_faulting(rake: object) -> str:
    try:
        value = float(rake)
    except Exception:
        return "unknown"
    if not np.isfinite(value):
        return "unknown"
    while value <= -180:
        value += 360
    while value > 180:
        value -= 360
    if -45 <= value <= 45 or value >= 135 or value <= -135:
        return "strike-slip"
    if 45 < value < 135:
        return "reverse"
    if -135 < value < -45:
        return "normal"
    return "oblique"


def metric_label(metric: str) -> str:
    return {
        "PGA": "PGA",
        "PGV": "PGV",
        "arias_duration": "Arias duration",
        "energy_intensity": "Energy intensity",
    }.get(metric, metric)


def read_pairs(path: Path, metrics: list[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"pairs table not found: {path}")
    columns = [
        "event_id",
        "station",
        "metric",
        "band",
        "log2_residual",
        "distance_km",
        "magnitude",
        "event_depth_km",
        "rake",
        "path_basin_fraction",
        "path_la_basin_fraction",
        "path_class",
        "station_region_type",
        "log2_model_vs30_ratio",
    ]
    df = pd.read_csv(path, usecols=lambda column: column in columns)
    df = df.loc[df["metric"].isin(metrics)].copy()
    df["faulting_type"] = df.get("rake", pd.Series(np.nan, index=df.index)).apply(classify_faulting)
    return df


def add_zscore(df: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(df[column], errors="coerce")
    std = float(values.std(skipna=True))
    if np.isfinite(std) and std > 0:
        return (values - float(values.mean(skipna=True))) / std
    return pd.Series(np.nan, index=df.index)


def prepare_metric_frame(pairs: pd.DataFrame, metric: str, *, max_rows: int) -> pd.DataFrame:
    df = pairs.loc[pairs["metric"].eq(metric)].copy()
    numeric = [
        "log2_residual",
        "distance_km",
        "magnitude",
        "event_depth_km",
        "path_basin_fraction",
        "path_la_basin_fraction",
        "log2_model_vs30_ratio",
    ]
    for column in numeric:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    df["log_distance"] = np.log1p(df["distance_km"])
    for column in ["log_distance", "magnitude", "event_depth_km", "path_basin_fraction", "path_la_basin_fraction", "log2_model_vs30_ratio"]:
        df[f"{column}_z"] = add_zscore(df, column)
    for column in ["event_id", "station", "band", "path_class", "station_region_type", "faulting_type"]:
        df[column] = df.get(column, "unknown").fillna("unknown").astype(str)

    required = [
        "event_id",
        "station",
        "band",
        "log2_residual",
        "log_distance_z",
        "magnitude_z",
        "event_depth_km_z",
        "path_basin_fraction_z",
        "path_la_basin_fraction_z",
    ]
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=required).copy()
    if max_rows > 0 and len(df) > max_rows:
        df = df.sample(n=max_rows, random_state=RANDOM_SEED).copy()
    return df


def fit_model(metric: str, spec: ModelSpec, data: pd.DataFrame, *, maxiter: int) -> tuple[list[dict[str, object]], dict[str, object]]:
    import statsmodels.formula.api as smf

    model_data = data.copy()
    if spec.requires_vs30:
        model_data = model_data.dropna(subset=["log2_model_vs30_ratio_z"]).copy()
    formula = f"log2_residual ~ {spec.formula_rhs}"
    re_formula = "1 + log_distance_z" if spec.random_slope else "1"

    attempts = []
    for method in ["lbfgs", "powell", "nm", "cg"]:
        if attempts and attempts[0]["converged"] and method != "lbfgs":
            break
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                model = smf.mixedlm(
                    formula,
                    data=model_data,
                    groups=model_data["station"],
                    re_formula=re_formula,
                    vc_formula={"event": "0 + C(event_id)"},
                )
                result = model.fit(
                    reml=False,
                    method=method,
                    maxiter=maxiter if method == "lbfgs" else max(maxiter, 400),
                    disp=False,
                )
                attempts.append(
                    {
                        "method": method,
                        "result": result,
                        "converged": bool(getattr(result, "converged", False)),
                        "aic": float(result.aic) if np.isfinite(result.aic) else np.inf,
                        "warnings": list(caught),
                        "error": "",
                    }
                )
                if method == "lbfgs" and attempts[-1]["converged"]:
                    break
            except Exception as exc:
                attempts.append(
                    {
                        "method": method,
                        "result": None,
                        "converged": False,
                        "aic": np.inf,
                        "warnings": list(caught),
                        "error": repr(exc),
                    }
                )

    valid = [attempt for attempt in attempts if attempt["result"] is not None]
    if not valid:
        raise RuntimeError("; ".join(f"{attempt['method']}: {attempt['error']}" for attempt in attempts))
    converged = [attempt for attempt in valid if attempt["converged"]]
    selected = min(converged or valid, key=lambda attempt: attempt["aic"])
    result = selected["result"]
    optimizer = str(selected["method"])
    all_warning_text = []
    for attempt in attempts:
        all_warning_text.extend(str(w.message) for w in attempt["warnings"])
        if attempt["error"]:
            all_warning_text.append(f"{attempt['method']} error: {attempt['error']}")

    fixed_rows: list[dict[str, object]] = []
    conf = result.conf_int()
    for term, coef in result.fe_params.items():
        se = float(result.bse_fe.get(term, np.nan))
        fixed_rows.append(
            {
                "metric": metric,
                "model_name": spec.name,
                "model_label": spec.label,
                "term": term,
                "coef": float(coef),
                "se": se,
                "z": float(coef / se) if np.isfinite(se) and se > 0 else np.nan,
                "pvalue": float(result.pvalues.get(term, np.nan)),
                "ci_low": float(conf.loc[term, 0]) if term in conf.index else np.nan,
                "ci_high": float(conf.loc[term, 1]) if term in conf.index else np.nan,
                "nobs": int(result.nobs),
                "converged": bool(getattr(result, "converged", False)),
                "optimizer": optimizer,
                "note": "",
            }
        )

    station_var = float(result.cov_re.iloc[0, 0]) if result.cov_re.shape[0] else np.nan
    station_slope_var = np.nan
    station_slope_cov = np.nan
    if spec.random_slope and result.cov_re.shape[0] > 1:
        station_slope_var = float(result.cov_re.iloc[1, 1])
        station_slope_cov = float(result.cov_re.iloc[0, 1])
    event_var = float(result.vcomp[0]) if len(result.vcomp) else np.nan
    residual_var = float(result.scale)
    total_var = np.nansum([station_var, station_slope_var if spec.random_slope else np.nan, event_var, residual_var])
    compare_row = {
        "metric": metric,
        "model_name": spec.name,
        "model_label": spec.label,
        "description": spec.description,
        "nobs": int(result.nobs),
        "events": int(model_data["event_id"].nunique()),
        "stations": int(model_data["station"].nunique()),
        "fixed_terms": int(len(result.fe_params)),
        "log_likelihood": float(result.llf),
        "aic": float(result.aic),
        "bic": float(result.bic),
        "converged": bool(getattr(result, "converged", False)),
        "station_random_intercept_var": station_var,
        "station_distance_slope_var": station_slope_var,
        "station_intercept_distance_cov": station_slope_cov,
        "event_random_intercept_var": event_var,
        "residual_var": residual_var,
        "total_variance": float(total_var),
        "station_variance_share": safe_divide(station_var, total_var),
        "event_variance_share": safe_divide(event_var, total_var),
        "residual_variance_share": safe_divide(residual_var, total_var),
        "optimizer": optimizer,
        "optimizer_attempts": ",".join(str(attempt["method"]) for attempt in attempts),
        "warning_count": len(all_warning_text),
        "warnings": " | ".join(sorted(set(all_warning_text)))[:900],
        "note": "",
    }
    return fixed_rows, compare_row


def safe_divide(numerator: float, denominator: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0:
        return np.nan
    return float(numerator / denominator)


def fit_all_models(pairs: pd.DataFrame, metrics: list[str], *, max_rows: int, maxiter: int, run_random_slope: bool) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fixed_rows: list[dict[str, object]] = []
    compare_rows: list[dict[str, object]] = []
    support_rows: list[dict[str, object]] = []
    specs = list(MODEL_SPECS) + list(VS30_SPECS)
    if run_random_slope:
        specs.extend(RANDOM_SLOPE_SPECS)

    for metric in metrics:
        data = prepare_metric_frame(pairs, metric, max_rows=max_rows)
        support_rows.append(
            {
                "metric": metric,
                "rows": int(len(data)),
                "events": int(data["event_id"].nunique()),
                "stations": int(data["station"].nunique()),
                "vs30_rows": int(data["log2_model_vs30_ratio_z"].notna().sum()),
                "vs30_events": int(data.loc[data["log2_model_vs30_ratio_z"].notna(), "event_id"].nunique()),
                "vs30_stations": int(data.loc[data["log2_model_vs30_ratio_z"].notna(), "station"].nunique()),
            }
        )
        for spec in specs:
            try:
                rows, compare = fit_model(metric, spec, data, maxiter=maxiter)
                fixed_rows.extend(rows)
                compare_rows.append(compare)
            except Exception as exc:
                compare_rows.append(
                    {
                        "metric": metric,
                        "model_name": spec.name,
                        "model_label": spec.label,
                        "description": spec.description,
                        "nobs": int(len(data)),
                        "events": int(data["event_id"].nunique()),
                        "stations": int(data["station"].nunique()),
                        "fixed_terms": np.nan,
                        "log_likelihood": np.nan,
                        "aic": np.nan,
                        "bic": np.nan,
                        "converged": False,
                        "station_random_intercept_var": np.nan,
                        "station_distance_slope_var": np.nan,
                        "station_intercept_distance_cov": np.nan,
                        "event_random_intercept_var": np.nan,
                        "residual_var": np.nan,
                        "total_variance": np.nan,
                        "station_variance_share": np.nan,
                        "event_variance_share": np.nan,
                        "residual_variance_share": np.nan,
                        "warning_count": np.nan,
                        "warnings": "",
                        "note": repr(exc),
                    }
                )

    fixed = pd.DataFrame(fixed_rows)
    compare = pd.DataFrame(compare_rows)
    support = pd.DataFrame(support_rows)
    compare = add_model_deltas(compare)
    key = build_key_effects(fixed)
    return fixed, compare, support, key


def add_model_deltas(compare: pd.DataFrame) -> pd.DataFrame:
    out = compare.copy()
    out["delta_aic_from_best"] = np.nan
    out["delta_bic_from_best"] = np.nan
    out["total_variance_reduction_from_intercepts"] = np.nan
    out["event_variance_reduction_from_intercepts"] = np.nan
    out["station_variance_reduction_from_intercepts"] = np.nan
    out["residual_variance_reduction_from_intercepts"] = np.nan
    primary = out["model_name"].isin([spec.name for spec in MODEL_SPECS])
    for metric, group in out.loc[primary].groupby("metric"):
        idx = group.index
        out.loc[idx, "delta_aic_from_best"] = group["aic"] - group["aic"].min(skipna=True)
        out.loc[idx, "delta_bic_from_best"] = group["bic"] - group["bic"].min(skipna=True)
        baseline = group.loc[group["model_name"].eq("m00_intercepts_only")]
        if baseline.empty:
            continue
        b = baseline.iloc[0]
        for column, target in [
            ("total_variance", "total_variance_reduction_from_intercepts"),
            ("event_random_intercept_var", "event_variance_reduction_from_intercepts"),
            ("station_random_intercept_var", "station_variance_reduction_from_intercepts"),
            ("residual_var", "residual_variance_reduction_from_intercepts"),
        ]:
            base_value = float(b[column])
            if np.isfinite(base_value) and base_value != 0:
                out.loc[idx, target] = (base_value - group[column]) / base_value

    vs30 = out["model_name"].isin([spec.name for spec in VS30_SPECS])
    for metric, group in out.loc[vs30].groupby("metric"):
        idx = group.index
        out.loc[idx, "delta_aic_from_best"] = group["aic"] - group["aic"].min(skipna=True)
        out.loc[idx, "delta_bic_from_best"] = group["bic"] - group["bic"].min(skipna=True)
    return out


def build_key_effects(fixed: pd.DataFrame) -> pd.DataFrame:
    if fixed.empty:
        return fixed
    full = fixed.loc[fixed["model_name"].eq("m04_frequency_interactions") & fixed["term"].isin(TERM_LABELS)].copy()
    full["term_label"] = full["term"].map(TERM_LABELS)
    full["metric_label"] = full["metric"].map(metric_label)
    full["significant_95"] = (full["ci_low"] > 0) | (full["ci_high"] < 0)
    order = {label: i for i, label in enumerate(TERM_LABELS.values())}
    full["term_order"] = full["term_label"].map(order)
    return full.sort_values(["metric", "term_order"])


def write_tables(tables_dir: Path, fixed: pd.DataFrame, compare: pd.DataFrame, support: pd.DataFrame, key: pd.DataFrame) -> None:
    tables_dir.mkdir(parents=True, exist_ok=True)
    fixed.to_csv(tables_dir / "mixed_deep_fixed_effects.csv", index=False)
    compare.to_csv(tables_dir / "mixed_deep_model_comparison.csv", index=False)
    support.to_csv(tables_dir / "mixed_deep_support.csv", index=False)
    key.to_csv(tables_dir / "mixed_deep_key_effects.csv", index=False)


def plot_variance_decomposition(compare: pd.DataFrame, figures_dir: Path) -> Path:
    figures_dir.mkdir(parents=True, exist_ok=True)
    path = figures_dir / "fig_15_mixed_effects_variance_decomposition.png"
    primary_names = [spec.name for spec in MODEL_SPECS]
    plot_df = compare.loc[compare["model_name"].isin(primary_names) & compare["converged"].eq(True)].copy()
    if plot_df.empty:
        return path
    order = {spec.name: i for i, spec in enumerate(MODEL_SPECS)}
    plot_df["model_order"] = plot_df["model_name"].map(order)
    plot_df["metric_label"] = plot_df["metric"].map(metric_label)
    plot_df = plot_df.sort_values(["metric", "model_order"])

    components = [
        ("event_random_intercept_var", "Event", COLOR_FAMILIES["orange"]["base"], COLOR_FAMILIES["orange"]["dark"]),
        ("station_random_intercept_var", "Station", COLOR_FAMILIES["blue"]["base"], COLOR_FAMILIES["blue"]["dark"]),
        ("residual_var", "Residual", NEUTRAL_MARKS["light"], NEUTRAL_MARKS["dark"]),
    ]
    metrics = [metric for metric in METRICS if metric in set(plot_df["metric"])]
    fig, axes = plt.subplots(2, 2, figsize=(15.5, 11.8), sharex=False)
    axes_flat = axes.ravel()
    for ax, metric in zip(axes_flat, metrics):
        part = plot_df.loc[plot_df["metric"].eq(metric)].copy()
        y = np.arange(len(part))
        left = np.zeros(len(part))
        for column, label, color, edge in components:
            values = part[column].fillna(0).to_numpy(dtype=float)
            ax.barh(y, values, left=left, color=color, edgecolor=edge, linewidth=1.0, label=label)
            left += values
        ax.set_yticks(y, part["model_label"])
        ax.invert_yaxis()
        ax.set_title(metric_label(metric), loc="left", fontsize=13.5, fontweight="semibold", color=TOKENS["ink"])
        ax.set_xlabel("Variance component")
        ax.tick_params(axis="both", labelsize=10.5, colors=TOKENS["ink"])
        ax.grid(axis="x", color=TOKENS["grid"])
        ax.grid(axis="y", visible=False)
    for ax in axes_flat[len(metrics) :]:
        ax.axis("off")
    handles, labels = axes_flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower left", bbox_to_anchor=(0.08, 0.918), ncol=3, frameon=False, fontsize=11)
    add_chart_header(
        fig,
        axes_flat[0],
        "Mixed-effects variance shifts from raw residual scatter toward explicit source, path, site, and frequency terms",
        "Nested ML crossed-intercept models; bars show event, station, and residual variance components on the same rows for each metric.",
        title_width=96,
        subtitle_width=132,
    )
    fig.tight_layout(rect=[0.04, 0.04, 0.98, 0.88])
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_key_effects(key: pd.DataFrame, figures_dir: Path) -> Path:
    figures_dir.mkdir(parents=True, exist_ok=True)
    path = figures_dir / "fig_16_mixed_effects_key_fixed_effects.png"
    if key.empty:
        return path
    metrics = [metric for metric in METRICS if metric in set(key["metric"])]
    term_order = list(TERM_LABELS.values())
    fig, axes = plt.subplots(2, 2, figsize=(15.5, 12.2), sharex=True)
    axes_flat = axes.ravel()
    sig_family = COLOR_FAMILIES["gold"]
    ns_family = NEUTRAL_MARKS
    for ax, metric in zip(axes_flat, metrics):
        part = key.loc[key["metric"].eq(metric)].copy()
        part["term_label"] = pd.Categorical(part["term_label"], categories=term_order[::-1], ordered=True)
        part = part.sort_values("term_label")
        y = np.arange(len(part))
        for i, row in enumerate(part.itertuples(index=False)):
            significant = bool(row.significant_95)
            color = sig_family["base"] if significant else ns_family["base"]
            edge = sig_family["dark"] if significant else ns_family["dark"]
            ax.errorbar(
                row.coef,
                i,
                xerr=np.array([[row.coef - row.ci_low], [row.ci_high - row.coef]]),
                fmt="o",
                color=edge,
                markerfacecolor=color,
                markeredgecolor=edge,
                linewidth=1.2,
                markersize=6.5,
                capsize=3.2,
            )
        ax.axvline(0, color=TOKENS["ink"], linestyle=":", linewidth=1.1)
        ax.set_yticks(y, list(part["term_label"]))
        ax.set_title(metric_label(metric), loc="left", fontsize=13.5, fontweight="semibold", color=TOKENS["ink"])
        ax.set_xlabel("Fixed-effect coefficient, log2(obs/syn)")
        ax.tick_params(axis="both", labelsize=10.5, colors=TOKENS["ink"])
        ax.xaxis.set_major_locator(mticker.MaxNLocator(6))
        ax.grid(axis="x", color=TOKENS["grid"])
        ax.grid(axis="y", visible=False)
    for ax in axes_flat[len(metrics) :]:
        ax.axis("off")
    add_chart_header(
        fig,
        axes_flat[0],
        "After event and station controls, source depth, distance, and basin path remain measurable drivers",
        "Gold intervals exclude zero at 95%; coefficients are standardized except categorical station terms and 3-5 s interaction terms.",
        title_width=98,
        subtitle_width=132,
    )
    fig.tight_layout(rect=[0.04, 0.04, 0.98, 0.88])
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def summarize_results(compare: pd.DataFrame, key: pd.DataFrame, support: pd.DataFrame) -> dict[str, object]:
    primary_full = compare.loc[compare["model_name"].eq("m04_frequency_interactions")].copy()
    baseline = compare.loc[compare["model_name"].eq("m00_intercepts_only")].copy()
    merged = primary_full.merge(
        baseline[["metric", "total_variance", "event_random_intercept_var", "station_random_intercept_var", "residual_var"]],
        on="metric",
        suffixes=("_full", "_baseline"),
        how="left",
    )
    summary = {
        "metrics": list(primary_full["metric"]),
        "support": support.to_dict(orient="records"),
        "full_model_variance_reductions": [],
        "strong_key_terms": [],
    }
    for row in merged.itertuples(index=False):
        summary["full_model_variance_reductions"].append(
            {
                "metric": row.metric,
                "total_variance_reduction": safe_divide(row.total_variance_baseline - row.total_variance_full, row.total_variance_baseline),
                "event_variance_reduction": safe_divide(row.event_random_intercept_var_baseline - row.event_random_intercept_var_full, row.event_random_intercept_var_baseline),
                "station_variance_reduction": safe_divide(row.station_random_intercept_var_baseline - row.station_random_intercept_var_full, row.station_random_intercept_var_baseline),
                "residual_variance_reduction": safe_divide(row.residual_var_baseline - row.residual_var_full, row.residual_var_baseline),
            }
        )
    if not key.empty:
        strong = key.loc[key["significant_95"].eq(True) & key["term"].isin(["log_distance_z", "path_basin_fraction_z", "magnitude_z", "event_depth_km_z"])]
        summary["strong_key_terms"] = strong[["metric", "term", "coef", "ci_low", "ci_high", "pvalue"]].to_dict(orient="records")
    return summary


def write_report(report_dir: Path, compare: pd.DataFrame, key: pd.DataFrame, support: pd.DataFrame, figures: list[Path]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "cvmsi_mixed_effects_deep_dive.md"
    full = compare.loc[compare["model_name"].eq("m04_frequency_interactions")].copy()
    best = compare.loc[compare["model_name"].isin([spec.name for spec in MODEL_SPECS])].sort_values(["metric", "delta_bic_from_best"])
    vs30 = compare.loc[compare["model_name"].isin([spec.name for spec in VS30_SPECS])].copy()
    support_lines = [
        f"- {metric_label(row.metric)}: {int(row.rows):,} rows, {int(row.events)} events, {int(row.stations)} stations"
        + (f"; model/Vs30 subset {int(row.vs30_rows):,} rows" if int(row.vs30_rows) else "")
        for row in support.itertuples(index=False)
    ]
    reduction_lines = []
    for row in full.itertuples(index=False):
        reduction_lines.append(
            f"- {metric_label(row.metric)} full interaction model: event variance share {row.event_variance_share:.2f}, "
            f"station share {row.station_variance_share:.2f}, residual share {row.residual_variance_share:.2f}; "
            f"total variance reduction from random-intercepts baseline {row.total_variance_reduction_from_intercepts:.1%}."
        )
    key_lines = []
    for term, label in TERM_LABELS.items():
        rows = key.loc[key["term"].eq(term) & key["significant_95"].eq(True)]
        if rows.empty:
            continue
        effects = ", ".join(f"{metric_label(r.metric)} {r.coef:+.2f}" for r in rows.itertuples(index=False))
        key_lines.append(f"- {label}: {effects}.")
    vs30_lines = []
    if not vs30.empty:
        for metric, group in vs30.groupby("metric"):
            rows = group.sort_values("model_name")
            if len(rows) == 2:
                base, add = rows.iloc[0], rows.iloc[1]
                vs30_lines.append(
                    f"- {metric_label(metric)}: adding model/Vs30 mismatch changes BIC by {add.bic - base.bic:+.1f} on {int(add.nobs):,} rows."
                )
    figure_lines = [f"- {figure.name}" for figure in figures]
    content = f"""# CVM-SI Mixed-Effects Deep Dive

Generated {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} from `{Path(__file__).name}`.

## Why This Analysis

Event demeaning is useful for maps because it removes each event's average
offset and exposes spatial residual structure. It is still a forced residual,
not a full inferential model. The models here fit raw `log2(observed/synthetic)`
residuals while estimating crossed station and event random intercepts. That
lets the source, path, site, and frequency terms compete directly with event
and station effects rather than being interpreted after the fact.

## Model Design

All primary models are maximum-likelihood mixed-effects models at the
event-station-metric-band grain. The nested sequence is:

1. random intercepts only
2. plus period band
3. plus source magnitude, depth, mechanism, and distance
4. plus basin path fractions, discrete path class, and station geomorphology
5. plus frequency interactions for distance and basin-path terms

The model/Vs30 mismatch term is fit separately because it is only available for
about half of the rows. Station-level random distance slopes are intentionally
optional; the local test did not converge reliably enough to make them a
default finding.

## Support

{chr(10).join(support_lines)}

## Main Result

The strongest formal result is that source, distance, path, site, and frequency
terms reduce variance but do not eliminate event and station structure. This is
scientifically useful: remaining event variance points toward source/source-time
or source-path behavior, while remaining station variance points toward local
site, geology, or unmodeled near-station structure.

{chr(10).join(reduction_lines)}

## Key Fixed Effects

In the full frequency-interaction model, the following 95% intervals exclude
zero:

{chr(10).join(key_lines) if key_lines else '- No selected key terms had 95% intervals excluding zero.'}

## Model/Vs30 Subset

The model/Vs30 mismatch analysis is a reduced-support sensitivity check, not a
replacement for the primary models.

{chr(10).join(vs30_lines) if vs30_lines else '- The model/Vs30 subset did not produce comparison rows.'}

## Figures

{chr(10).join(figure_lines)}

## Tables

- `mixed_deep_model_comparison.csv`: nested model fit, variance components,
  AIC/BIC, and variance-reduction fields.
- `mixed_deep_fixed_effects.csv`: all fixed-effect coefficients.
- `mixed_deep_key_effects.csv`: selected fixed effects used in the coefficient
  figure.
- `mixed_deep_support.csv`: rows, event counts, station counts, and model/Vs30
  subset support.
"""
    path.write_text(content, encoding="utf-8")
    return path


def write_manifest(output_dir: Path, args: argparse.Namespace, compare: pd.DataFrame, figures: list[Path], report_path: Path) -> Path:
    path = output_dir / "manifest.json"
    payload = {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pairs_csv": str(args.pairs_csv.resolve()),
        "output_dir": str(output_dir.resolve()),
        "metrics": list(args.metrics),
        "max_rows_per_metric": int(args.max_rows_per_metric),
        "run_random_slope": bool(args.run_random_slope),
        "models": compare[["metric", "model_name", "nobs", "converged", "aic", "bic", "note"]].to_dict(orient="records"),
        "figures": [str(figure) for figure in figures],
        "report": str(report_path),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    args = parse_args()
    use_chart_theme()
    output_dir = args.output_dir
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    report_dir = output_dir / "report"
    for directory in [tables_dir, figures_dir, report_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    pairs = read_pairs(args.pairs_csv, args.metrics)
    fixed, compare, support, key = fit_all_models(
        pairs,
        list(args.metrics),
        max_rows=args.max_rows_per_metric,
        maxiter=args.maxiter,
        run_random_slope=args.run_random_slope,
    )
    write_tables(tables_dir, fixed, compare, support, key)
    figures = [
        plot_variance_decomposition(compare, figures_dir),
        plot_key_effects(key, figures_dir),
    ]
    summary = summarize_results(compare, key, support)
    (report_dir / "mixed_effects_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    report_path = write_report(report_dir, compare, key, support, figures)
    manifest = write_manifest(output_dir, args, compare, figures, report_path)
    print(f"Wrote {output_dir}")
    print(f"Wrote {manifest}")


if __name__ == "__main__":
    main()
