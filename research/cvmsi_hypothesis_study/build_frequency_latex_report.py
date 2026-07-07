#!/usr/bin/env python3
"""Build a standalone LaTeX CVM-SI report with all-passband frequency synthesis.

Every quantitative finding is summarized across 1-2, 2-3, and 3-5 s, and the
LaTeX report places figures next to the findings they support.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import shutil
import textwrap
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    import seaborn as sns
except Exception:  # pragma: no cover - CARC may not have seaborn.
    sns = None


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO_ROOT / "outputs" / "review" / "cvmsi_hypothesis_study"
DEFAULT_OUTPUT = DEFAULT_ROOT / "report_latex"

BAND_ORDER = ["1-2 sec", "2-3 sec", "3-5 sec"]
METRIC_ORDER = ["PGA", "PGV", "arias_duration", "energy_intensity"]
METRIC_LABELS = {
    "PGA": "PGA",
    "PGV": "PGV",
    "arias_duration": "Arias duration",
    "energy_intensity": "Energy intensity",
}
PATH_ORDER = [
    "LA basin local",
    "crosses LA basin",
    "terminates in LA basin",
    "other basin-influenced",
    "mixed non-basin",
    "mountain to mountain",
    "offshore source",
]
PATH_LABELS = {
    "LA basin local": "LA basin local",
    "crosses LA basin": "Crosses LA basin",
    "terminates in LA basin": "Terminates LA basin",
    "other basin-influenced": "Other basin-influenced",
    "mixed non-basin": "Mixed non-basin",
    "mountain to mountain": "Mountain to mountain",
    "offshore source": "Offshore source",
}

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}
COLOR_FAMILIES = {
    "blue": {"xlight": "#EAF1FE", "light": "#CEDFFE", "base": "#A3BEFA", "mid": "#5477C4", "dark": "#2E4780"},
    "gold": {"xlight": "#FFF4C2", "light": "#FFEA8F", "base": "#FFE15B", "mid": "#B8A037", "dark": "#736422"},
    "orange": {"xlight": "#FFEDDE", "light": "#FFBDA1", "base": "#F0986E", "mid": "#CC6F47", "dark": "#804126"},
    "olive": {"xlight": "#D8ECBD", "light": "#BEEB96", "base": "#A3D576", "mid": "#71B436", "dark": "#386411"},
    "pink": {"xlight": "#FCDAD6", "light": "#F5BACC", "base": "#F390CA", "mid": "#BD569B", "dark": "#8A3A6F"},
}
NEUTRAL = {
    "xlight": "#F4F5F7",
    "light": "#E2E5EA",
    "base": "#C5CAD3",
    "mid": "#7A828F",
    "dark": "#464C55",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def use_chart_theme() -> None:
    rc = {
        "figure.facecolor": TOKENS["surface"],
        "figure.edgecolor": "none",
        "savefig.facecolor": TOKENS["surface"],
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
        "font.sans-serif": ["Aptos", "Inter", "Segoe UI", "DejaVu Sans", "Arial", "sans-serif"],
        "font.size": 11,
        "axes.titlesize": 15,
        "axes.labelsize": 12,
        "xtick.labelsize": 10.5,
        "ytick.labelsize": 10.5,
        "legend.fontsize": 10.5,
    }
    if sns is not None:
        sns.set_theme(style="whitegrid", rc=rc)
    else:
        plt.rcParams.update(rc)


def add_chart_header(fig: plt.Figure, title: str, subtitle: str, *, left: float = 0.08) -> None:
    title = "\n".join(textwrap.wrap(title, width=92, break_long_words=False))
    subtitle = "\n".join(textwrap.wrap(subtitle, width=125, break_long_words=False))
    fig.text(left, 0.985, title, ha="left", va="top", fontsize=18, fontweight="bold", color=TOKENS["ink"])
    fig.text(left, 0.94, subtitle, ha="left", va="top", fontsize=11.5, color=TOKENS["muted"], linespacing=1.15)


def savefig(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def fmt_num(value: float, digits: int = 2) -> str:
    if pd.isna(value):
        return "--"
    return f"{value:+.{digits}f}"


def tex_escape(text: object) -> str:
    s = str(text)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in s)


def read_table(root: Path, rel: str) -> pd.DataFrame:
    return pd.read_csv(root / rel)


def band_code(band: str) -> str:
    return {"1-2 sec": "1-2", "2-3 sec": "2-3", "3-5 sec": "3-5"}[band]


def build_frequency_slopes(root: Path) -> pd.DataFrame:
    fixed = read_table(root, "mixed_effects/tables/mixed_deep_fixed_effects.csv")
    terms = {
        "Distance": "log_distance_z",
        "Basin path": "path_basin_fraction_z",
        "LA basin path": "path_la_basin_fraction_z",
    }
    rows: list[dict[str, object]] = []
    for metric in METRIC_ORDER:
        sub = fixed[(fixed.metric == metric) & (fixed.model_name == "m04_frequency_interactions")].set_index("term")
        for label, term in terms.items():
            base = float(sub.loc[term, "coef"])
            for band in BAND_ORDER:
                interaction = 0.0
                if band != "1-2 sec":
                    key = f"C(band)[T.{band}]:{term}"
                    interaction = float(sub.loc[key, "coef"]) if key in sub.index else 0.0
                estimate = base + interaction
                rows.append(
                    {
                        "metric": metric,
                        "metric_label": METRIC_LABELS[metric],
                        "effect": label,
                        "band": band,
                        "estimate": estimate,
                        "base_1_2_coef": base,
                        "interaction_from_1_2": interaction,
                    }
                )
    return pd.DataFrame(rows)


def build_band_offsets(root: Path) -> pd.DataFrame:
    fixed = read_table(root, "mixed_effects/tables/mixed_deep_fixed_effects.csv")
    rows: list[dict[str, object]] = []
    for metric in METRIC_ORDER:
        sub = fixed[(fixed.metric == metric) & (fixed.model_name == "m04_frequency_interactions")].set_index("term")
        for band in ["2-3 sec", "3-5 sec"]:
            key = f"C(band)[T.{band}]"
            row = sub.loc[key]
            rows.append(
                {
                    "metric": metric,
                    "metric_label": METRIC_LABELS[metric],
                    "band": band,
                    "offset_vs_1_2": float(row.coef),
                    "ci_low": float(row.ci_low),
                    "ci_high": float(row.ci_high),
                    "pvalue": float(row.pvalue),
                }
            )
    return pd.DataFrame(rows)


def build_path_consistency(root: Path) -> pd.DataFrame:
    path = read_table(root, "tables/path_summary.csv")
    rows: list[dict[str, object]] = []
    for (metric, path_class), part in path.groupby(["metric", "path_class"]):
        if metric not in METRIC_ORDER or path_class not in PATH_ORDER:
            continue
        med = part.set_index("band").reindex(BAND_ORDER)["median"]
        signs = np.sign(med.fillna(0.0).to_numpy())
        if np.all(med > 0.05):
            pattern = "positive_all_bands"
        elif np.all(med < -0.05):
            pattern = "negative_all_bands"
        elif np.nanmax(med) - np.nanmin(med) < 0.15:
            pattern = "near_stable"
        else:
            pattern = "frequency_dependent"
        rows.append(
            {
                "metric": metric,
                "metric_label": METRIC_LABELS[metric],
                "path_class": path_class,
                "path_label": PATH_LABELS[path_class],
                "median_1_2": med.get("1-2 sec", np.nan),
                "median_2_3": med.get("2-3 sec", np.nan),
                "median_3_5": med.get("3-5 sec", np.nan),
                "min_median": float(np.nanmin(med)),
                "max_median": float(np.nanmax(med)),
                "sign_changes": int(len(set(signs[~np.isnan(signs)])) > 1),
                "pattern": pattern,
            }
        )
    return pd.DataFrame(rows)


def build_component_summary(root: Path) -> pd.DataFrame:
    comp = read_table(root, "extended/tables/component_azimuth_summary.csv")
    rows: list[dict[str, object]] = []
    for (metric, band, component), part in comp.groupby(["metric", "band", "component"]):
        weighted_median = float((part["median"] * part["rows"]).sum() / part["rows"].sum())
        rows.append(
            {
                "metric": metric,
                "metric_label": METRIC_LABELS.get(metric, metric),
                "band": band,
                "component": component,
                "rows": int(part["rows"].sum()),
                "row_weighted_sector_median": weighted_median,
            }
        )
    return pd.DataFrame(rows)


def read_directivity_tables(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    table_dir = root / "component_directivity" / "tables"

    def maybe_read(name: str) -> pd.DataFrame:
        path = table_dir / name
        if path.exists():
            return pd.read_csv(path)
        return pd.DataFrame()

    return (
        maybe_read("component_directivity_model_comparison.csv"),
        maybe_read("component_directivity_key_effects.csv"),
        maybe_read("component_directivity_support.csv"),
    )


def read_model_property_tables(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    table_dir = root / "model_property_mixed_effects" / "tables"

    def maybe_read(name: str) -> pd.DataFrame:
        path = table_dir / name
        if path.exists():
            return pd.read_csv(path)
        return pd.DataFrame()

    return (
        maybe_read("model_property_mixed_model_comparison.csv"),
        maybe_read("model_property_mixed_band_effects.csv"),
        maybe_read("model_property_mixed_support.csv"),
    )


def best_directivity_models(compare: pd.DataFrame) -> pd.DataFrame:
    if compare.empty:
        return pd.DataFrame()
    added = compare[(compare["model_name"] != "m00_source_path_site") & (compare["converged"].astype(bool))].copy()
    if added.empty:
        return added
    idx = added.groupby(["metric", "component"])["delta_bic_from_baseline"].idxmin()
    best = added.loc[idx].copy()
    best["metric_order"] = best["metric"].map({"PGA": 0, "PGV": 1}).fillna(99)
    best["component_order"] = best["component"].map({"R": 0, "T": 1, "Z": 2}).fillna(99)
    return best.sort_values(["metric_order", "component_order"]).drop(columns=["metric_order", "component_order"])


def best_model_property_models(compare: pd.DataFrame) -> pd.DataFrame:
    if compare.empty:
        return pd.DataFrame()
    added = compare[(compare["model_name"] != "m00_source_path_site") & (compare["converged"].astype(bool))].copy()
    if added.empty:
        return added
    idx = added.groupby("metric")["delta_bic_from_baseline"].idxmin()
    best = added.loc[idx].copy()
    best["metric_order"] = best["metric"].map({metric: idx for idx, metric in enumerate(METRIC_ORDER)}).fillna(99)
    return best.sort_values("metric_order").drop(columns="metric_order")


def plot_global_frequency(root: Path, out: Path) -> None:
    global_df = read_table(root, "tables/global_summary.csv")
    use_chart_theme()
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9.5), sharex=True)
    add_chart_header(
        fig,
        "All passbands remain positive, but the size of the underprediction is frequency dependent",
        "Dots show global median raw log2(observed/synthetic) residuals with bootstrap intervals; pale bars show post-QC event-station-metric-band rows.",
    )
    colors = [COLOR_FAMILIES["blue"]["base"], COLOR_FAMILIES["gold"]["base"], COLOR_FAMILIES["orange"]["base"]]
    for ax, metric in zip(axes.flat, METRIC_ORDER):
        part = global_df[global_df.metric == metric].set_index("band").reindex(BAND_ORDER).reset_index()
        x = np.arange(len(BAND_ORDER))
        ax2 = ax.twinx()
        ax2.bar(x, part["rows"], color=NEUTRAL["light"], edgecolor=NEUTRAL["mid"], width=0.62, alpha=0.55, label="Rows")
        yerr = np.vstack([part["median"] - part["bootstrap_ci_low"], part["bootstrap_ci_high"] - part["median"]])
        ax.errorbar(
            x,
            part["median"],
            yerr=yerr,
            fmt="o-",
            color=COLOR_FAMILIES["blue"]["dark"],
            markerfacecolor=COLOR_FAMILIES["gold"]["base"],
            markeredgecolor=COLOR_FAMILIES["gold"]["dark"],
            linewidth=1.3,
            capsize=4,
            label="Median residual",
        )
        for xi, row in zip(x, part.itertuples(index=False)):
            ax.text(xi, row.median + 0.06 * max(1.0, abs(part["median"]).max()), f"n={int(row.rows):,}", ha="center", va="bottom", fontsize=9.0, color=TOKENS["muted"])
        ax.axhline(0, color=TOKENS["ink"], linewidth=1.0, linestyle=":")
        ax.set_title(METRIC_LABELS[metric], loc="left", fontweight="bold", color=TOKENS["ink"])
        ax.set_xticks(x, [band_code(b) for b in BAND_ORDER])
        ax.set_ylabel("Median log2(obs/syn)")
        ax2.set_ylabel("Rows")
        ax2.grid(False)
        ax2.tick_params(axis="y", colors=TOKENS["muted"])
        ax.tick_params(axis="both", colors=TOKENS["ink"])
        ax.set_axisbelow(True)
    fig.tight_layout(rect=[0.06, 0.05, 0.98, 0.88])
    savefig(fig, out)


def plot_mixed_band_slopes(slopes: pd.DataFrame, out: Path) -> None:
    use_chart_theme()
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9.2), sharex=True)
    add_chart_header(
        fig,
        "Distance and basin-path effects diverge by passband in the crossed mixed-effects model",
        "Band-specific point estimates are derived from the full frequency-interaction model. Intervals for combined slopes are not shown because the term covariance matrix is not exported.",
    )
    effect_colors = {
        "Distance": COLOR_FAMILIES["blue"]["dark"],
        "Basin path": COLOR_FAMILIES["olive"]["dark"],
        "LA basin path": COLOR_FAMILIES["orange"]["dark"],
    }
    markers = {"Distance": "o", "Basin path": "s", "LA basin path": "^"}
    x = np.arange(len(BAND_ORDER))
    for ax, metric in zip(axes.flat, METRIC_ORDER):
        part = slopes[slopes.metric == metric]
        for effect, effect_part in part.groupby("effect", sort=False):
            effect_part = effect_part.set_index("band").reindex(BAND_ORDER)
            ax.plot(
                x,
                effect_part["estimate"],
                marker=markers[effect],
                color=effect_colors[effect],
                linewidth=1.4,
                markersize=6.5,
                label=effect,
            )
        ax.axhline(0, color=TOKENS["ink"], linewidth=1.0, linestyle=":")
        ax.set_title(METRIC_LABELS[metric], loc="left", fontweight="bold")
        ax.set_xticks(x, [band_code(b) for b in BAND_ORDER])
        ax.set_ylabel("Coefficient, log2(obs/syn)")
        ax.set_axisbelow(True)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.55, 0.89), ncol=3, frameon=False)
    fig.tight_layout(rect=[0.06, 0.05, 0.98, 0.84])
    savefig(fig, out)


def plot_path_heatmaps(root: Path, out: Path) -> None:
    path = read_table(root, "tables/path_summary.csv")
    use_chart_theme()
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 10.5), sharex=True, sharey=True)
    add_chart_header(
        fig,
        "Path-class medians show which corridor effects persist and which are passband-specific",
        "Cells are event-centered median residuals by metric, path class, and passband; values near zero are neutral after each event's median is removed.",
    )
    cmap = plt.get_cmap("RdBu_r")
    vmin, vmax = -0.65, 0.65
    for ax, metric in zip(axes.flat, METRIC_ORDER):
        matrix = (
            path[path.metric == metric]
            .pivot(index="path_class", columns="band", values="median")
            .reindex(index=PATH_ORDER, columns=BAND_ORDER)
        )
        im = ax.imshow(matrix.to_numpy(), cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_title(METRIC_LABELS[metric], loc="left", fontweight="bold")
        ax.set_xticks(np.arange(len(BAND_ORDER)), [band_code(b) for b in BAND_ORDER])
        ax.set_yticks(np.arange(len(PATH_ORDER)), [PATH_LABELS[p] for p in PATH_ORDER])
        ax.tick_params(axis="x", rotation=0)
        for y in range(matrix.shape[0]):
            for x in range(matrix.shape[1]):
                val = matrix.iloc[y, x]
                if pd.notna(val):
                    ax.text(x, y, f"{val:+.2f}", ha="center", va="center", fontsize=9.2, color=TOKENS["ink"])
        ax.grid(False)
    cbar = fig.colorbar(im, ax=axes, location="right", fraction=0.025, pad=0.025)
    cbar.set_label("Event-centered median log2 residual")
    fig.tight_layout(rect=[0.08, 0.04, 0.92, 0.87])
    savefig(fig, out)


def plot_component_summary(component: pd.DataFrame, out: Path) -> None:
    use_chart_theme()
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.8), sharey=True)
    add_chart_header(
        fig,
        "Radial components are consistently high relative to transverse and vertical components",
        "Cells are row-weighted means of azimuth-sector median component residuals; interpret this descriptive pattern with the source-radiation controls that follow.",
    )
    cmap = plt.get_cmap("RdBu_r")
    vmin, vmax = -0.18, 0.18
    for ax, metric in zip(axes, ["PGA", "PGV"]):
        matrix = (
            component[component.metric == metric]
            .pivot(index="component", columns="band", values="row_weighted_sector_median")
            .reindex(index=["R", "T", "Z"], columns=BAND_ORDER)
        )
        im = ax.imshow(matrix.to_numpy(), cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_title(METRIC_LABELS[metric], loc="left", fontweight="bold")
        ax.set_xticks(np.arange(len(BAND_ORDER)), [band_code(b) for b in BAND_ORDER])
        ax.set_yticks(np.arange(3), ["R", "T", "Z"])
        ax.grid(False)
        for y in range(matrix.shape[0]):
            for x in range(matrix.shape[1]):
                val = matrix.iloc[y, x]
                if pd.notna(val):
                    ax.text(x, y, f"{val:+.2f}", ha="center", va="center", fontsize=11, color=TOKENS["ink"])
    cbar = fig.colorbar(im, ax=axes, location="right", fraction=0.035, pad=0.03)
    cbar.set_label("Row-weighted sector median")
    fig.tight_layout(rect=[0.08, 0.08, 0.90, 0.78])
    savefig(fig, out)


def copy_figures(root: Path, fig_dir: Path) -> dict[str, str]:
    sources = {
        "fig01-map.png": "figures/fig_01_observed_site_anomaly_vs_residual_map.png",
        "fig05-geology.png": "figures/fig_05_geologic_unit_residual_effects.png",
        "fig07-source.png": "extended/figures/fig_07_source_magnitude_depth_faulting.png",
        "fig08-distance.png": "extended/figures/fig_08_distance_attenuation_binned.png",
        "fig10-support.png": "extended/figures/fig_10_support_density_maps.png",
        "fig13-corridors.png": "case_studies/figures/fig_13_case_study_corridors_and_cvm_sections.png",
        "fig14-waveforms.png": "case_studies/figures/fig_14_case_study_waveform_examples.png",
        "fig15-variance.png": "mixed_effects/figures/fig_15_mixed_effects_variance_decomposition.png",
        "fig16-fixed-effects.png": "mixed_effects/figures/fig_16_mixed_effects_key_fixed_effects.png",
        "fig21-directivity-bic.png": "component_directivity/figures/fig_21_component_directivity_model_comparison.png",
        "fig22-directivity-effects.png": "component_directivity/figures/fig_22_component_directivity_key_effects.png",
        "fig23-directivity-support.png": "component_directivity/figures/fig_23_component_directivity_support.png",
        "fig24-model-property-iqr.png": "model_property_mixed_effects/figures/fig_24_model_property_best_iqr_effects.png",
        "fig25-model-property-effects.png": "model_property_mixed_effects/figures/fig_25_model_property_mixed_band_effects.png",
    }
    copied: dict[str, str] = {}
    fig_dir.mkdir(parents=True, exist_ok=True)
    for dest, rel in sources.items():
        src = root / rel
        if src.exists():
            shutil.copy2(src, fig_dir / dest)
            copied[dest] = rel
    return copied


def latex_table_global(global_df: pd.DataFrame) -> str:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Global residual medians by passband in the CVM-SI analysis dataset. Positive values mean CVM-SI underpredicts the observed metric.}",
        r"\small",
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Metric & Band & Rows & Events & Stations & Median \\",
        r"\midrule",
    ]
    for row in global_df.itertuples(index=False):
        lines.append(
            f"{tex_escape(METRIC_LABELS[row.metric])} & {tex_escape(row.band)} & {int(row.rows):,} & "
            f"{int(row.events)} & {int(row.stations)} & {row.median:+.3f} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def latex_table_slopes(slopes: pd.DataFrame) -> str:
    pivot = slopes.pivot_table(index=["metric", "effect"], columns="band", values="estimate").reset_index()
    effect_order = {"Distance": 0, "Basin path": 1, "LA basin path": 2}
    pivot["metric_order"] = pivot["metric"].map({metric: idx for idx, metric in enumerate(METRIC_ORDER)})
    pivot["effect_order"] = pivot["effect"].map(effect_order)
    pivot = pivot.sort_values(["metric_order", "effect_order", "effect"]).drop(
        columns=["metric_order", "effect_order"]
    )
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Band-specific mixed-effects point estimates from the full frequency-interaction model.}",
        r"\small",
        r"\begin{tabular}{llrrr}",
        r"\toprule",
        r"Metric & Effect & 1-2 s & 2-3 s & 3-5 s \\",
        r"\midrule",
    ]
    for _, row in pivot.iterrows():
        lines.append(
            f"{tex_escape(METRIC_LABELS[row['metric']])} & {tex_escape(row['effect'])} & "
            f"{row['1-2 sec']:+.3f} & {row['2-3 sec']:+.3f} & {row['3-5 sec']:+.3f} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def latex_table_directivity_best(compare: pd.DataFrame) -> str:
    best = best_directivity_models(compare)
    if best.empty:
        return (
            r"\begin{table}[H]"
            "\n"
            r"\centering"
            "\n"
            r"\caption{Component radiation/directivity model comparison was unavailable in this build.}"
            "\n"
            r"\begin{tabular}{l}"
            "\n"
            r"\toprule"
            "\n"
            r"Status \\"
            "\n"
            r"\midrule"
            "\n"
            r"No component-directivity model-comparison table was found. \\"
            "\n"
            r"\bottomrule"
            "\n"
            r"\end{tabular}"
            "\n"
            r"\end{table}"
        )

    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Best added source-geometry model for each component-specific residual model, selected by BIC relative to the source/path/site baseline.}",
        r"\small",
        r"\begin{tabular}{lllrrr}",
        r"\toprule",
        r"Metric & Comp. & Best added model & Rows & $\Delta$AIC & $\Delta$BIC \\",
        r"\midrule",
    ]
    for row in best.itertuples(index=False):
        lines.append(
            f"{tex_escape(row.metric)} & {tex_escape(row.component)} & {tex_escape(row.model_label)} & "
            f"{int(row.nobs):,} & {row.delta_aic_from_baseline:+.1f} & {row.delta_bic_from_baseline:+.1f} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def latex_table_model_property_best(compare: pd.DataFrame, effects: pd.DataFrame) -> str:
    best = best_model_property_models(compare)
    if best.empty:
        return (
            r"\begin{table}[H]"
            "\n"
            r"\centering"
            "\n"
            r"\caption{Model-property mixed-effects comparison was unavailable in this build.}"
            "\n"
            r"\begin{tabular}{l}"
            "\n"
            r"\toprule"
            "\n"
            r"Status \\"
            "\n"
            r"\midrule"
            "\n"
            r"No model-property mixed-effects table was found. \\"
            "\n"
            r"\bottomrule"
            "\n"
            r"\end{tabular}"
            "\n"
            r"\end{table}"
        )

    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Selected single model-property extension for each metric, expressed as the fitted residual change across the observed interquartile range of the physical predictor.}",
        r"\small",
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Metric & Predictor & IQR range & 1-2 s & 2-3 s & 3-5 s \\",
        r"\midrule",
    ]
    for row in best.itertuples(index=False):
        part = effects.loc[(effects["metric"].eq(row.metric)) & (effects["predictor"].eq(row.predictor))]
        shifts = part.set_index("band")["iqr_effect"] if not part.empty and "iqr_effect" in part.columns else pd.Series(dtype=float)
        p25 = getattr(row, "predictor_p25", np.nan)
        p75 = getattr(row, "predictor_p75", np.nan)
        units = getattr(row, "predictor_units", "")
        iqr_range = f"{p25:.3g}--{p75:.3g} {units}" if np.isfinite(p25) and np.isfinite(p75) else "--"
        predictor_label = str(row.predictor_label).replace("|grad|", "abs grad")
        lines.append(
            f"{tex_escape(METRIC_LABELS.get(row.metric, row.metric))} & {tex_escape(predictor_label)} & "
            f"{tex_escape(iqr_range)} & {shifts.get('1-2 sec', np.nan):+.3f} & "
            f"{shifts.get('2-3 sec', np.nan):+.3f} & {shifts.get('3-5 sec', np.nan):+.3f} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def latex_itemize(items: Iterable[str]) -> str:
    body = "\n".join(f"  \\item {item}" for item in items)
    return "\\begin{itemize}[leftmargin=*]\n" + body + "\n\\end{itemize}"


def include_figure(filename: str, caption: str, *, width: str = r"0.98\linewidth") -> str:
    return "\n".join(
        [
            r"\begin{figure}[H]",
            r"\centering",
            rf"\includegraphics[width={width}]{{figures/{filename}}}",
            rf"\caption{{{tex_escape(caption)}}}",
            r"\end{figure}",
        ]
    )


def interpretation_block(
    physical: str,
    limitations: str,
    useful: str,
    literature: str,
) -> str:
    return "\n".join(
        [
            r"\subsection*{Interpretation}",
            r"\begin{description}[leftmargin=1.2em,style=nextline,itemsep=0.45em]",
            rf"\item[Physical meaning] {physical}",
            rf"\item[Limitations] {limitations}",
            rf"\item[Use and actionability] {useful}",
            rf"\item[Related literature] {literature}",
            r"\end{description}",
        ]
    )


def build_latex(
    root: Path,
    out_dir: Path,
    global_df: pd.DataFrame,
    slopes: pd.DataFrame,
    offsets: pd.DataFrame,
    consistency: pd.DataFrame,
    directivity_compare: pd.DataFrame,
    directivity_key: pd.DataFrame,
    directivity_support: pd.DataFrame,
    model_property_compare: pd.DataFrame,
    model_property_effects: pd.DataFrame,
    model_property_support: pd.DataFrame,
) -> str:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    extended_manifest = json.loads((root / "extended" / "manifest.json").read_text(encoding="utf-8"))
    counts = manifest["counts"]
    created = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    global_pga = global_df[global_df.metric == "PGA"].set_index("band")
    global_pgv = global_df[global_df.metric == "PGV"].set_index("band")
    global_arias = global_df[global_df.metric == "arias_duration"].set_index("band")
    global_energy = global_df[global_df.metric == "energy_intensity"].set_index("band")
    cross_pga = consistency[(consistency.metric == "PGA") & (consistency.path_class == "crosses LA basin")].iloc[0]
    cross_pgv = consistency[(consistency.metric == "PGV") & (consistency.path_class == "crosses LA basin")].iloc[0]
    arias_cross = consistency[(consistency.metric == "arias_duration") & (consistency.path_class == "crosses LA basin")].iloc[0]
    energy_cross = consistency[(consistency.metric == "energy_intensity") & (consistency.path_class == "crosses LA basin")].iloc[0]
    model_property_best = best_model_property_models(model_property_compare)
    if model_property_compare.empty or model_property_best.empty:
        model_property_summary = (
            "The model-property mixed-effects extension was unavailable when this LaTeX report was built, "
            "so the gradient-versus-basin-depth result is not included in the technical summary."
        )
    else:
        complete_models_mp = int(model_property_compare["converged"].astype(bool).sum())
        model_count_mp = len(model_property_compare)
        support_metrics = len(model_property_support) if not model_property_support.empty else len(model_property_best)
        support_rows_min = int(model_property_support["rows"].min()) if not model_property_support.empty else int(model_property_best["nobs"].min())
        support_rows_max = int(model_property_support["rows"].max()) if not model_property_support.empty else int(model_property_best["nobs"].max())
        best_lookup = model_property_best.set_index("metric")
        pgv_best = best_lookup.loc["PGV"]
        pga_best = best_lookup.loc["PGA"]
        energy_best = best_lookup.loc["energy_intensity"]
        arias_best = best_lookup.loc["arias_duration"]
        best_effects = model_property_effects.merge(
            model_property_best[["metric", "predictor"]],
            on=["metric", "predictor"],
            how="inner",
        )

        def iqr_shift(metric: str, band: str = "1-2 sec") -> float:
            part = best_effects.loc[(best_effects["metric"].eq(metric)) & (best_effects["band"].eq(band))]
            if part.empty or "iqr_effect" not in part.columns:
                return np.nan
            return float(part.iloc[0].iqr_effect)

        model_property_summary = (
            f"The model-property mixed-effects extension fit {complete_models_mp} of {model_count_mp} models "
            f"across {support_metrics} metrics, with {support_rows_min:,}-{support_rows_max:,} rows per metric. "
            f"When the selected physical predictor is moved from its 25th to 75th percentile, the 1-2 s "
            f"PGV residual shifts by {iqr_shift('PGV'):+.2f} log2 units for {pgv_best.predictor_label}, "
            f"and the PGA residual shifts by {iqr_shift('PGA'):+.2f} log2 units for {pga_best.predictor_label}. "
            f"Energy intensity also selects a gradient term ({energy_best.predictor_label}; 1-2 s shift "
            f"{iqr_shift('energy_intensity'):+.2f}), while arias duration selects a basin-depth marker "
            f"({arias_best.predictor_label}; 1-2 s shift {iqr_shift('arias_duration'):+.2f})."
        )
    directivity_best = best_directivity_models(directivity_compare)
    if directivity_best.empty:
        directivity_summary = (
            "The component radiation/directivity refit outputs were not available when this LaTeX report was built, "
            "so the component section remains descriptive."
        )
    else:
        best_counts = directivity_best["model_label"].value_counts()
        radiation_best = int(best_counts.get("Add radiation", 0))
        directivity_best_count = int(best_counts.get("Add directivity", 0))
        complete_models = int(directivity_compare["converged"].astype(bool).sum())
        model_count = len(directivity_compare)
        weakest_bic = float(directivity_best["delta_bic_from_baseline"].max())
        strongest_bic = float(directivity_best["delta_bic_from_baseline"].min())
        support_rows = int(directivity_support["fit_rows"].sum()) if not directivity_support.empty else 0
        directivity_summary = (
            f"Component-specific radiation/directivity refits cover PGA/PGV R, T, and Z with "
            f"{support_rows:,} complete-geometry rows. All {complete_models} of {model_count} nested mixed models "
            f"converged. BIC improvements among the preferred added models range from {weakest_bic:+.1f} "
            f"to {strongest_bic:+.1f}; radiation terms are BIC-preferred for {radiation_best} components, "
            f"while the slip-directivity proxy is preferred for {directivity_best_count} component."
        )

    summary_items = [
        (
            f"The CVM-SI analysis dataset contains {counts['events']} events, "
            f"{counts['stations']} stations, {counts['event_station_metric_band_rows']:,} "
            f"event-station-metric-band records, and {extended_manifest['counts']['component_rows']:,} "
            "component-level PGA/PGV records. Quantitative findings are reported for the 1-2, 2-3, and 3-5 s passbands."
        ),
        (
            "Global underprediction is consistent in sign for all metrics and all passbands, but not in magnitude: "
            f"PGA medians are {global_pga.loc['1-2 sec','median']:+.2f}, "
            f"{global_pga.loc['2-3 sec','median']:+.2f}, and {global_pga.loc['3-5 sec','median']:+.2f}; "
            f"PGV medians are {global_pgv.loc['1-2 sec','median']:+.2f}, "
            f"{global_pgv.loc['2-3 sec','median']:+.2f}, and {global_pgv.loc['3-5 sec','median']:+.2f}."
        ),
        (
            "The most robust frequency divergence is in distance and basin-path behavior. Distance remains positive "
            "for PGA/PGV/energy but weakens from 1-2 s toward 3-5 s; arias duration has the opposite sign."
        ),
        (
            "Path classes should be used as frequency-aware diagnostics. Crossed-LA-basin paths are positive for "
            f"PGA ({cross_pga.median_1_2:+.2f}, {cross_pga.median_2_3:+.2f}, {cross_pga.median_3_5:+.2f}) "
            f"and PGV ({cross_pgv.median_1_2:+.2f}, {cross_pgv.median_2_3:+.2f}, {cross_pgv.median_3_5:+.2f}), "
            f"but arias duration remains negative ({arias_cross.median_1_2:+.2f}, "
            f"{arias_cross.median_2_3:+.2f}, {arias_cross.median_3_5:+.2f})."
        ),
        model_property_summary,
        directivity_summary,
    ]

    finding1_interpretation = interpretation_block(
        "A broadband positive residual means the synthetics are too weak relative to the observations across amplitude, duration, and energy metrics. The different passband behavior is physically important because it points to frequency-dependent source, attenuation, basin, or shallow-site effects rather than one uniform amplitude scale factor.",
        "This finding does not identify a single mechanism. Residual medians combine source-time behavior, moment scaling, attenuation, path structure, and site response, and the saved tables do not yet include a 1-5 s aggregate. Because the synthetics are point-source simulations with a 1 Hz maximum frequency, finite-source effects and higher-frequency scattering are outside the present evidence.",
        "Treat amplitude scaling as frequency dependent. The practical next step is to rerun the metric workflow with a 1-5 s aggregate, then test whether source calibration, attenuation/Q, or shallow-site corrections reduce the residuals consistently across passbands.",
        r"The need to separate source, path, and site terms follows standard seismic wave-propagation theory \cite{akirichards2002}. The SCEC CVM framework provides the model context for interpreting CVM-SI performance as a velocity-model diagnostic rather than only a processing artifact \cite{small2017}.",
    )
    finding2_interpretation = interpretation_block(
        "The distance trends imply that geometric spreading, attenuation, source duration, and path-dependent wavefield evolution are not captured equally for all metrics and periods. Positive distance slopes for PGA/PGV/energy mean farther records are increasingly underpredicted after controls, while negative arias-duration slopes imply that duration behavior is controlled by a different physical combination of scattering, coda, and source/path effects.",
        "The distance terms are empirical mixed-model slopes, not a direct measurement of Q, scattering strength, or geometric spreading. Magnitude, depth, and faulting terms are also source proxies; with point-source synthetics they can absorb source-time and focal-depth effects that would require waveform-level source modeling to separate.",
        "Use the distance and source terms as triage for targeted attenuation and source-duration tests. A useful model-improvement experiment is to compare residuals before and after path-dependent Q, source-time, or focal-depth perturbations, then check whether the sign and frequency dependence of the distance slopes decrease.",
        r"Double-couple radiation, takeoff geometry, and source-depth effects are expected to couple source and path amplitudes \cite{akirichards2002}. The CVM software framework literature is relevant because velocity-model validation should separate model structure from processing and source assumptions \cite{small2017}.",
    )
    finding3_interpretation = interpretation_block(
        "The basin/path result is consistent with frequency-dependent wave guiding, basin-edge conversion, resonance, and impedance-contrast effects. Positive crossed-LA-basin PGA/PGV residuals suggest that CVM-SI may be underpredicting some basin-amplified amplitude behavior, while the negative arias-duration response implies that duration and amplitude do not respond to basin paths in the same way.",
        "The path classes are polygon-line summaries, not finite-frequency sensitivity kernels. A path that crosses a basin polygon does not prove that the wave energy sampled the deepest basin structure, and event/station density can bias which paths dominate each class.",
        "Use these classes to choose cross sections, waveform examples, and perturbation tests. The most actionable checks are basin-edge smoothing, basin-depth sensitivity, shallow Vs/impedance perturbations, and finite-frequency kernels for high-residual crossed-basin paths.",
        r"LA Basin structural complexity and sedimentary architecture are described by Yerkes et al. \cite{yerkes1965}. Basin amplification and 3D/1D differences depend strongly on impedance contrast and basin geometry \cite{mezafajardo2016}, and northern LA-area basins have been argued to channel San Andreas energy toward Los Angeles \cite{zou2024}.",
    )
    finding4_interpretation = interpretation_block(
        "Station geology and geomorphology affect the near-surface part of the wavefield through impedance contrasts, shallow velocity gradients, topographic setting, and local resonance. The frequency-dependent behavior of mapped units suggests that shallow structure is not acting as a simple static station correction.",
        "Mapped geologic unit is a proxy, not a direct Vs, density, damping, or impedance measurement. Unit effects can also be confounded with station installation, local topography, station density, and event azimuth coverage. The 3-5 s geology map is therefore evidence for targeted review, not a complete site-response model.",
        "The actionable path is to combine station geology with measured or inferred Vs profiles, geomorphic class, and station-specific residual random effects. Units with stable residual signs across passbands should be prioritized for shallow-model updates or station-term validation.",
        r"The LA Basin geologic framework in Yerkes et al. supports treating station geology as a physically meaningful proxy \cite{yerkes1965}. General site-effect literature emphasizes that surface layers, impedance contrast, topography, and basin geometry can all amplify or reshape motion \cite{delepine2013,mezafajardo2016}.",
    )
    finding5_model_property_interpretation = interpretation_block(
        "The mixed-effects result strengthens the earlier cross-section screen: amplitude residuals are more strongly associated with local vertical Vp/rho gradient structure than with basin-depth markers alone. Sharp shallow velocity or density gradients are proxies for impedance contrasts, reflection/conversion interfaces, scattering potential, and resonance-producing layering. The fitted signs are mostly negative, so stations with larger local gradients tend to have lower log2(observed/synthetic) residuals after event, station, source, path, faulting, band, and station-context controls.",
        "These models are still diagnostic. Each model-property term is added one at a time to limit collinearity, and station random intercepts make the fixed station-property tests conservative but do not prove causality. The predictors are vertical summaries sampled at station locations; they are not finite-frequency kernels, lateral-gradient terms, impedance kernels, or full waveform sensitivity tests. Density in particular should be treated as a model-property proxy until checked against the CVM-SI construction details.",
        "Use the gradient result to target model perturbations rather than to replace waveform validation. The most useful next tests are shallow Vp/rho/Vs smoothing or sharpening experiments, impedance-gradient perturbations near high-leverage stations, and CVM-SI versus CVM-H reruns once the expanded event set is merged. If the same gradient terms remain important after balanced-region and held-out-station tests, they become practical predictors for where the velocity model is over- or under-structuring shallow contrasts.",
        r"Wave-propagation theory links impedance contrasts to reflection, conversion, and path coupling \cite{akirichards2002}. Basin and site-effect studies show that gradients and impedance structure can modify amplification and duration in ways that are not reducible to basin depth alone \cite{delepine2013,mezafajardo2016}. The CVM framework literature provides the model-validation context for testing whether these residual-gradient relationships are velocity-model artifacts or processing/source effects \cite{small2017}.",
    )
    finding5_interpretation = interpretation_block(
        "Persistent radial, transverse, and vertical differences indicate that CVM-SI performance is not only scalar-amplitude behavior. Component structure can reflect source radiation, Love/Rayleigh wave partitioning, basin-guided surface waves, mode conversion, scattering, and directional site response.",
        "The component heatmap is descriptive because the cells are azimuth-sector medians rather than a full source-corrected inversion. It cannot by itself separate radiation pattern, basin propagation, polarization rotation, anisotropy, and station/site effects.",
        "Use component dependence to design source-aware waveform review. In practice, component-specific residuals should be included in mixed-effects and waveform diagnostics so that radial/transverse/vertical behavior is not averaged away before interpreting basin or station effects.",
        r"Source radiation and takeoff geometry naturally produce component-dependent amplitudes \cite{akirichards2002}. Basin and site-effect studies show why component and polarization behavior can also change through 2D/3D basin propagation \cite{delepine2013,mezafajardo2016}.",
    )
    finding6_interpretation = interpretation_block(
        "The radiation/directivity refit shows that a substantial part of the component residual pattern is source-geometry controlled. This is physically expected: strike, dip, rake, azimuth, and takeoff angle determine how P, SV, and SH energy is radiated toward each station, so component residuals can look path-like unless radiation is modeled.",
        "The takeoff angle is a straight-line approximation and the radiation terms are far-field diagnostic predictors. The slip-alignment terms are not a rupture model, so the result should not be interpreted as proof of finite-fault directivity or rupture propagation effects.",
        "Include radiation predictors in future component, path, and basin models before making regional performance claims. A direct next test is to compare path and basin coefficients with and without radiation terms, then escalate persistent residual azimuth effects to finite-frequency or rupture-aware simulations.",
        r"The focal-mechanism and radiation-pattern interpretation follows standard double-couple source theory \cite{akirichards2002}. The basin/site literature remains relevant because the remaining residuals after radiation control may still reflect propagation or shallow-structure effects \cite{mezafajardo2016}.",
    )
    finding7_interpretation = interpretation_block(
        "The corridor figures translate population-level residual patterns into concrete propagation paths through the CVM-SI structure. They are useful because waveforms and cross sections can reveal whether a statistical residual pattern is plausibly tied to basin depth, velocity gradients, impedance contrasts, or missing structural boundaries.",
        "A single event-station waveform pair is an example, not a robust regional claim. Corridors can also be sensitive to event mechanism, station response, processing choices, and the finite-frequency width of the wavefield, none of which is fully represented by a line on a map.",
        "Use targeted corridors as hypothesis generators for controlled model perturbations. The next actionable step is to assemble statistically supported event-station subsets for each corridor, then test whether specific CVM-SI changes improve both the subset metrics and the representative waveforms.",
        r"The CVM framework describes how community velocity models are constructed and evaluated \cite{small2017}. LA Basin geology and recent basin imaging provide the physical context for choosing corridor perturbations tied to real structures rather than arbitrary map regions \cite{yerkes1965,zou2024}.",
    )

    tex = rf"""\documentclass[11pt]{{article}}
\usepackage[margin=0.82in]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{booktabs}}
\usepackage{{float}}
\usepackage{{placeins}}
\usepackage{{array}}
\usepackage{{longtable}}
\usepackage{{enumitem}}
\usepackage{{caption}}
\usepackage{{microtype}}
\usepackage[colorlinks=true,linkcolor=blue,urlcolor=blue,citecolor=blue]{{hyperref}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{0.62em}}
\captionsetup{{font=small,labelfont=bf}}
\graphicspath{{{{figures/}}}}
\title{{CVM-SI Observed/Synthetic Hypothesis Report\\\large Passband, Path, Site, and Component-Radiation Analysis}}
\author{{Private spatial-vtk analysis}}
\date{{Generated {tex_escape(created)}}}
\begin{{document}}
\maketitle

\textbf{{Private working report. Do not push to the public repository.}}

\section{{Technical summary}}
{latex_itemize(summary_items)}

\section{{Data, passbands, and metric definitions}}
The analysis uses the June 30, 2026 CVM-SI metrics in
\texttt{{metrics\_final\_enriched.parquet}}. Positive residuals mean
\(\log_2(\mathrm{{observed}}/\mathrm{{synthetic}})>0\), so the CVM-SI synthetic is
weaker than the observation for that metric. The saved passband metrics are
1-2, 2-3, and 3-5 s. A 1-5 s aggregate is absent from the saved metric tables;
it is recommended below as a follow-up rerun because it would test a broadband
long-period summary in addition to the narrower passbands.

{latex_table_global(global_df)}

{include_figure('fig17-frequency-global.png', 'Global residual medians and row support by passband. Row counts are shown for each metric so the frequency comparison can be read against its support basis.')}
\FloatBarrier

\section{{Finding 1: Underprediction is broadband, but frequency structure matters}}
CVM-SI underpredicts observed amplitudes, duration, and energy in every analyzed
passband. The sign is stable, but the magnitude is not. PGV and energy
intensity have much larger 1-2 s residuals than 2-3 or 3-5 s residuals, while
arias duration increases toward 3-5 s. This means the model-performance
diagnostic should not be summarized by only one passband.

The all-band mixed model confirms the raw summary: after event and station
random intercepts plus source, path, and site terms, the period-band offsets
are large. For example, PGV is lower than its 1-2 s baseline by
{offsets[(offsets.metric == 'PGV') & (offsets.band == '2-3 sec')].iloc[0].offset_vs_1_2:+.2f}
at 2-3 s and
{offsets[(offsets.metric == 'PGV') & (offsets.band == '3-5 sec')].iloc[0].offset_vs_1_2:+.2f}
at 3-5 s. Arias duration moves in the opposite direction, with positive
controlled offsets at both longer passbands.

{include_figure('fig15-variance.png', 'Nested mixed-effects variance decomposition. Explicit band, source, path, site, and interaction terms reduce variance but leave substantial event and station structure.')}

{finding1_interpretation}
\FloatBarrier

\section{{Finding 2: Source and distance controls are first-order and frequency dependent}}
Source magnitude and event depth remain first-order controls after station and
event random effects. The point-source synthetics used proper moment tensor
forces, so these terms should be treated as source scaling, source-time,
radiation/directivity, focal-depth, or source-path coupling diagnostics rather
than nuisance metadata.

Distance behavior diverges sharply by metric and passband. PGA, PGV, and energy
intensity have positive distance slopes at all three passbands, but those
slopes weaken toward 3-5 s. Arias duration has negative distance slopes at all
three passbands. This is not compatible with one scalar attenuation correction
for every engineering metric.

{latex_table_slopes(slopes)}

{include_figure('fig18-frequency-slopes.png', 'Band-specific mixed-effects point estimates for distance, total basin path, and LA-basin path. The 1-2 s band is the baseline; 2-3 and 3-5 s values add the fitted interaction terms.')}

{include_figure('fig07-source.png', 'Source magnitude, depth, and faulting summaries. Source-level structure must be controlled before assigning residual geography solely to CVM-SI geology.')}

{finding2_interpretation}
\FloatBarrier

\section{{Finding 3: Basin and path effects persist, but the sign and interpretation depend on metric and passband}}
The path diagnostics support basin/path behavior, but not a single LA Basin
multiplier. Crossed-LA-basin paths are positive in all three bands for PGA and
PGV, and also positive for energy intensity. Arias duration is different:
crossed-LA-basin paths are negative in all three bands, and the LA-basin path
interaction is strongly negative at 3-5 s in the mixed model.
Mountain-to-mountain and offshore-source paths also show frequency dependence,
so broad path labels should be used as diagnostics to target
waveform/cross-section review, not as final physical explanations.

{include_figure('fig19-path-heatmaps.png', 'Event-centered median residuals by path class and passband. The heatmaps separate path effects that are stable across passbands from effects that change with frequency.')}

{include_figure('fig08-distance.png', 'Distance attenuation summaries by path class. These binned summaries are descriptive complements to the all-band mixed-effects model.')}

{finding3_interpretation}
\FloatBarrier

\section{{Finding 4: Local geology and geomorphology are stable enough to matter, but not all units behave the same at all frequencies}}
Local station context remains important after controlling for event/station
effects. In the mixed model, hills and valley station contexts are positive for
PGA, PGV, arias duration, and energy intensity. The geologic-unit summaries
show frequency-dependent amplitudes: \texttt{{Tsh}} and \texttt{{Tv-clastic,Tss}}
are positive in all PGA passbands but decline toward 3-5 s, while
\texttt{{Qal-thin}} shifts from near-zero/slightly positive at 1-2 s to clearly
negative at 2-3 and 3-5 s. These effects point toward shallow velocity,
impedance, valley/edge, and station-geology structure rather than a single
broad basin category.

{include_figure('fig05-geology.png', 'Geologic-unit PGA residual effects at 3-5 s. These estimates are one passband-specific geology view and should be read with the all-band mixed-effects and path summaries.')}

{include_figure('fig01-map.png', 'Observed site anomaly and raw CVM-SI residual map at 3-5 s. The basemap supports geographic interpretation; spatial claims in the text are tied to all-band summaries and mixed-effects controls.')}

{finding4_interpretation}
\FloatBarrier

\section{{Finding 5: Local Vp and density gradients explain amplitude residuals better than basin-depth markers alone}}
The earlier cross-section and station-median diagnostics suggested that
amplitude residuals are not simply controlled by deeper basin markers. The
mixed-effects extension tests that relationship at the event-station record
level. It samples CVM-SI station profiles for z(Vs=1.0), z(Vs=2.5), and
moving-window Vp/rho vertical-gradient summaries, then adds one standardized
model-property term at a time, with passband interactions, to the crossed
event/station source-path-site baseline.

The result supports the gradient interpretation for amplitude-like metrics.
PGV and PGA select rho-gradient terms, and energy intensity selects a
Vp-gradient term. Arias duration is the main exception: its selected
model-property addition is z(Vs=1.0), so duration remains more closely tied to
basin-depth structure than PGA/PGV in this diagnostic screen. The table below
reports the physically interpretable quantity: fitted residual change when the
predictor moves from its 25th to 75th percentile in the refreshed event-station
dataset.

{latex_table_model_property_best(model_property_compare, model_property_effects)}

{include_figure('fig24-model-property-iqr.png', 'Selected model-property terms expressed as fitted log2 residual shifts across the observed interquartile range of the physical predictor. Negative values mean residuals decrease between the lower-quartile and upper-quartile station predictor values.')}

The detailed effect figure shows the same physical shift for several z-depth
and gradient summaries. Most retained model-property effects are negative in
each passband, especially for short-period PGV and energy. This means larger
local gradients or deeper markers tend to reduce log2(observed/synthetic)
residuals after the event, station, source, path, and site controls in the
baseline model. The practical interpretation is not that gradients always
reduce ground motion, but that the current CVM-SI synthetics and observations
diverge systematically where the model has sharp shallow vertical property
changes.

{include_figure('fig25-model-property-effects.png', 'Band-specific fitted residual shifts from the 25th to 75th percentile of each physical z-depth or Vp/rho gradient predictor. Grey markers indicate intervals that overlap zero.')}

{finding5_model_property_interpretation}
\FloatBarrier

\section{{Finding 6: Polarization structure is consistent enough to justify component-aware modeling}}
The descriptive component pattern is stable across all three passbands: radial
PGA and PGV residuals are positive, while transverse and vertical residuals are
generally negative. This is not enough by itself to claim a path or site
mechanism, because focal-mechanism radiation and source-to-station geometry can
produce component-dependent residuals. It does, however, identify component and
azimuth as necessary axes for the model-performance analysis.

{include_figure('fig20-component-frequency.png', 'Component residual structure by passband. Cells are row-weighted means of azimuth-sector median component residuals, so the figure is descriptive rather than a source-corrected inference.')}

{finding5_interpretation}
\FloatBarrier

\section{{Finding 7: Radiation explains part of the component structure; slip-directivity is secondary in this diagnostic fit}}
The component-specific mixed-effects analysis fits focal-mechanism predictors
to raw PGA/PGV component residuals. Each model includes crossed event and
station random intercepts plus source, path, basin, distance, faulting, band,
and station-geomorphology controls, then adds approximate takeoff angle, azimuth
relative to strike, double-couple P/SV/SH radiation amplitudes, and
slip-alignment proxies.

The result is strong enough to change the interpretation of the polarization
finding. Radiation terms materially improve BIC in every component, and they
are the preferred added term block for five of the six component fits. The only
BIC-preferred slip-directivity case is PGA transverse, and even there the
radiation-only model is close. This means the radial/vertical/transverse
patterns are partly source-radiation controlled; they should not be interpreted
as pure path, basin, or station-site behavior without these controls.

{include_figure('fig23-directivity-support.png', 'Support for component-specific radiation/directivity fits. All retained component rows have complete strike, dip, rake, azimuth, distance, and depth geometry for the diagnostic predictor set.')}

{latex_table_directivity_best(directivity_compare)}

{include_figure('fig21-directivity-bic.png', 'Nested model comparison for component-specific PGA/PGV residual fits. Negative Delta BIC values indicate improvement relative to the source/path/site baseline.')}

The coefficient pattern is physically interpretable but still diagnostic.
SH-radiation amplitude is positive for radial and vertical residuals, SV
radiation is negative for those same components, and P-radiation is positive
for transverse PGA/PGV. Takeoff angle is negative for PGA radial/vertical and
PGV vertical, but positive for PGV transverse. Relative-azimuth harmonics remain
measurable after radiation terms. These results motivate source-aware waveform
selection and path tests, but the straight-line takeoff approximation and
point-source geometry mean this is not a finite-frequency rupture-directivity
inference.

{include_figure('fig22-directivity-effects.png', 'Key source-geometry coefficients from the full component-directivity model. Coefficients are standardized; intervals crossing zero are visually de-emphasized in the source figure.')}

{finding6_interpretation}
\FloatBarrier

\section{{Finding 8: Targeted corridors are examples, not standalone proof}}
The targeted corridor and waveform figures remain useful because they make the
population-level path, basin, and component results physically inspectable.
They do not by themselves prove a regional model-performance claim. The larger
all-passband mixed-effects, path-class, and component summaries above provide
the statistical support; the waveforms and cross sections show concrete cases
worth testing with finite-frequency sensitivity and model perturbations.

{include_figure('fig13-corridors.png', 'Targeted event-station corridors with CVM-SI Vs cross sections. Map panels use rendered basemaps and equal projected-axis scaling.')}

{include_figure('fig14-waveforms.png', 'Observed and CVM-SI synthetic waveform examples. The examples are selected from supported path/azimuth bins and should be interpreted alongside the larger subsets.')}

{finding7_interpretation}
\FloatBarrier

\section{{Methods and robustness notes}}
\begin{{itemize}}[leftmargin=*]
\item Event-demeaned residual maps are used as diagnostics only. Formal claims rely on mixed-effects models fit to raw residuals with event and station random effects.
\item The mixed-effects passband slopes in this report are point estimates derived by adding the relevant period-band interaction to the 1-2 s baseline term. Confidence intervals for these combined slopes are not shown because the covariance matrix for linear combinations was not exported.
\item The model-property extension adds one standardized z-depth or Vp/rho gradient predictor at a time, with passband interactions, to avoid treating highly correlated station-profile summaries as independent causal effects.
\item Path classes are polygon-line intersections, not finite-frequency kernels or ray-theory paths.
\item Component radiation/directivity models use straight-line takeoff angles and double-couple far-field radiation approximations as diagnostic source controls. They do not replace finite-frequency kernels, rupture simulations, or waveform-level source inversions.
\item Figure QA is tracked in \texttt{{report\_latex/figure\_qa.md}}; map figures retain rendered basemaps, map axes use equal projected scaling where geographic scale matters, and rendered PDF pages were checked for overlapping text, legends, and colorbars.
\end{{itemize}}

\section{{Recommended next work}}
\begin{{enumerate}}[leftmargin=*]
\item Add a 1-5 s aggregate passband to the metric workflow, then rerun the global summaries, mixed-effects models, component models, path diagnostics, and targeted-corridor checks. This should not replace the narrow bands; it should test whether a broadband long-period residual supports or hides the frequency-divergent behavior found here.
\item Export covariance matrices or fit explicit linear-combination contrasts for the mixed-effects frequency interactions so band-specific slopes can be reported with correct confidence intervals.
\item Test shallow model-property mechanisms directly by perturbing Vp, Vs, density, and impedance-gradient structure around the high-leverage stations identified by the model-property mixed-effects fits.
\item Include radiation/directivity controls in the next all-passband and CVM-H comparison reruns, and add finite-frequency or rupture-aware sensitivity tests before interpreting residual azimuth as physical directivity.
\item Convert the targeted high-residual corridors into sensitivity-aware model tests, including basin-edge smoothing and shallow Vs/impedance perturbation experiments.
\item Run held-out-event, held-out-station, and balanced-region validation, especially after any additional CVM-SI/CVM-H events are merged into the QC/metric inputs.
\item Compare CVM-SI with CVM-H once the CVM-H support is large enough to separate CVM-SI-specific structural effects from common processing/source effects.
\end{{enumerate}}

\section{{Bibliography}}
\begin{{thebibliography}}{{9}}
\bibitem{{yerkes1965}} Yerkes, R. F., McCulloh, T. H., Schoellhamer, J. E., and Vedder, J. G. (1965). \textit{{Geology of the Los Angeles Basin, California: An Introduction}}. USGS Professional Paper 420-A.
\bibitem{{small2017}} Small, P., Gill, D., Maechling, P. J., Taborda, R., Callaghan, S., Jordan, T. H., Ely, G. P., Olsen, K. B., and Goulet, C. A. (2017). The SCEC Unified Community Velocity Model Software Framework. \textit{{Seismological Research Letters}}, 88(5).
\bibitem{{mezafajardo2016}} Meza Fajardo, K. C., Semblat, J.-F., Chaillat, S., and Lenti, L. (2016). Seismic wave amplification in 3D alluvial basins: 3D/1D amplification ratios from fast multipole BEM simulations.
\bibitem{{delepine2013}} Delepine, N. and Semblat, J.-F. (2013). Site effects in an alpine valley with strong velocity gradient: interest and limitations of the classical BEM.
\bibitem{{zou2024}} Zou, C. and Clayton, R. W. (2024). Imaging the Northern Los Angeles Basins with Autocorrelations.
\bibitem{{akirichards2002}} Aki, K. and Richards, P. G. (2002). \textit{{Quantitative Seismology}}, 2nd ed. University Science Books.
\end{{thebibliography}}

\end{{document}}
"""
    return tex


def main() -> None:
    args = parse_args()
    root = args.analysis_root.resolve()
    out_dir = args.output_dir.resolve()
    fig_dir = out_dir / "figures"
    table_dir = out_dir / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)

    global_df = read_table(root, "tables/global_summary.csv")
    slopes = build_frequency_slopes(root)
    offsets = build_band_offsets(root)
    consistency = build_path_consistency(root)
    component = build_component_summary(root)
    directivity_compare, directivity_key, directivity_support = read_directivity_tables(root)
    model_property_compare, model_property_effects, model_property_support = read_model_property_tables(root)

    global_df.to_csv(table_dir / "frequency_global_summary.csv", index=False)
    slopes.to_csv(table_dir / "frequency_mixed_band_slopes.csv", index=False)
    offsets.to_csv(table_dir / "frequency_band_offsets.csv", index=False)
    consistency.to_csv(table_dir / "frequency_path_consistency.csv", index=False)
    component.to_csv(table_dir / "frequency_component_summary.csv", index=False)
    if not directivity_compare.empty:
        directivity_compare.to_csv(table_dir / "directivity_model_comparison.csv", index=False)
    if not directivity_key.empty:
        directivity_key.to_csv(table_dir / "directivity_key_effects.csv", index=False)
    if not directivity_support.empty:
        directivity_support.to_csv(table_dir / "directivity_support.csv", index=False)
    if not model_property_compare.empty:
        model_property_compare.to_csv(table_dir / "model_property_mixed_model_comparison.csv", index=False)
    if not model_property_effects.empty:
        model_property_effects.to_csv(table_dir / "model_property_mixed_band_effects.csv", index=False)
    if not model_property_support.empty:
        model_property_support.to_csv(table_dir / "model_property_mixed_support.csv", index=False)

    plot_global_frequency(root, fig_dir / "fig17-frequency-global.png")
    plot_mixed_band_slopes(slopes, fig_dir / "fig18-frequency-slopes.png")
    plot_path_heatmaps(root, fig_dir / "fig19-path-heatmaps.png")
    plot_component_summary(component, fig_dir / "fig20-component-frequency.png")
    copied = copy_figures(root, fig_dir)

    tex = build_latex(
        root,
        out_dir,
        global_df,
        slopes,
        offsets,
        consistency,
        directivity_compare,
        directivity_key,
        directivity_support,
        model_property_compare,
        model_property_effects,
        model_property_support,
    )
    tex_path = out_dir / "cvmsi_frequency_hypothesis_report.tex"
    tex_path.write_text(tex, encoding="utf-8")

    manifest = {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "analysis_root": str(root),
        "output_dir": str(out_dir),
        "tex": str(tex_path),
        "new_figures": [
            "fig17-frequency-global.png",
            "fig18-frequency-slopes.png",
            "fig19-path-heatmaps.png",
            "fig20-component-frequency.png",
        ],
        "copied_figures": copied,
        "tables": [
            "frequency_global_summary.csv",
            "frequency_mixed_band_slopes.csv",
            "frequency_band_offsets.csv",
            "frequency_path_consistency.csv",
            "frequency_component_summary.csv",
            "directivity_model_comparison.csv",
            "directivity_key_effects.csv",
            "directivity_support.csv",
            "model_property_mixed_model_comparison.csv",
            "model_property_mixed_band_effects.csv",
            "model_property_mixed_support.csv",
        ],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {tex_path}")
    print(f"Wrote {out_dir / 'manifest.json'}")
    print(f"Figures: {fig_dir}")
    print(f"Tables: {table_dir}")


if __name__ == "__main__":
    main()
