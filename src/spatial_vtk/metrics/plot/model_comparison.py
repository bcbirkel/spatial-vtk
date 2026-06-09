"""Model comparison and heatmap figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from matplotlib.colors import BoundaryNorm, ListedColormap

from spatial_vtk.config.labels import band_display_label, metric_display_name, model_display_name, value_column_display_name
from spatial_vtk.visualize.figure_context import apply_figure_context, value_color_settings
from spatial_vtk.visualize.figure_io import finish_figure


def plot_model_metric_heatmap(
    summary_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    model_col: str = "model",
    metric_col: str = "metric",
    value_col: str = "med_resid",
    title: str = "Model-Metric Heatmap",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot model-by-metric summary values as a heatmap."""

    _require(summary_df, [model_col, metric_col, value_col])
    work = summary_df.copy()
    work["_metric_label"] = work[metric_col].map(metric_display_name)
    work["_model_label"] = work[model_col].map(model_display_name)
    pivot = work.pivot_table(index="_metric_label", columns="_model_label", values=value_col, aggfunc="median")
    return _heatmap(pivot, output_path, title=title, cbar_label=value_column_display_name(value_col), context_df=summary_df, value_col=value_col, showfig=showfig, savefig=savefig, outpath=outpath)


def plot_winner_heatmap(
    summary_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    row_col: str = "metric",
    col_col: str = "band",
    winner_col: str = "winner",
    title: str = "Winning Model Heatmap",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot categorical winner labels by metric and band."""

    _require(summary_df, [row_col, col_col, winner_col])
    work = summary_df.copy()
    if row_col == "metric":
        work["_row_label"] = work[row_col].map(metric_display_name)
        row_col = "_row_label"
    if col_col in {"band", "passband"}:
        work["_col_label"] = work[col_col].map(band_display_label)
        col_col = "_col_label"
    pivot = work.pivot_table(index=row_col, columns=col_col, values=winner_col, aggfunc=lambda values: str(values.iloc[0]))
    labels = sorted({str(value) for value in pivot.stack().dropna().unique()})
    lookup = {label: index for index, label in enumerate(labels)}
    numeric = pivot.map(lambda value: lookup.get(str(value), np.nan))
    fig, ax = plt.subplots(figsize=(max(6.0, 0.55 * numeric.shape[1] + 3.5), max(4.2, 0.35 * numeric.shape[0] + 2.2)), dpi=180, constrained_layout=True)
    base = plt.get_cmap("tab20")
    cmap = ListedColormap([base(index % base.N) for index in range(max(len(labels), 1))])
    norm = BoundaryNorm(np.arange(len(labels) + 1) - 0.5, cmap.N)
    image = ax.imshow(numeric.to_numpy(dtype=float), aspect="auto", cmap=cmap, norm=norm)
    ax.set_xticks(np.arange(numeric.shape[1]))
    ax.set_xticklabels(numeric.columns.astype(str), rotation=35, ha="right")
    ax.set_yticks(np.arange(numeric.shape[0]))
    ax.set_yticklabels(numeric.index.astype(str))
    cbar = fig.colorbar(image, ax=ax, pad=0.04, ticks=np.arange(len(labels)))
    cbar.ax.set_yticklabels([model_display_name(label) for label in labels])
    apply_figure_context(ax, None, title=title)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_band_score_distribution(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    band_col: str = "band",
    score_col: str = "score",
    model_col: str = "model",
    metric_col: str = "metric",
    color_col: str | None = "metric",
    title: str = "Band Score Distribution",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot score distributions grouped by period band.

    Inputs are a long metric table with one score column and a period-band
    column. The output is a Matplotlib figure with adjacent colored boxplots
    inside each passband group, plus visual separators between passbands.
    """

    _require(df, [band_col, score_col])
    fig, ax = plt.subplots(figsize=(8.5, 5.0), dpi=180)
    selected_color_col = color_col if color_col and color_col in df.columns else (metric_col if metric_col in df.columns else None)
    columns = [band_col, score_col] + ([selected_color_col] if selected_color_col else [])
    work = df[columns].dropna(subset=[band_col, score_col]).copy()
    bands = sorted(dict.fromkeys(work[band_col].astype(str)), key=_band_sort_key)
    color_values = sorted(dict.fromkeys(work[selected_color_col].astype(str)), key=_color_sort_key) if selected_color_col else ["All"]
    centers = np.arange(len(bands), dtype=float) * 1.25
    offsets = np.linspace(-0.30, 0.30, len(color_values)) if len(color_values) > 1 else np.array([0.0])
    width = min(0.56 / max(len(color_values), 1), 0.20)
    palette = plt.get_cmap("tab10")
    for band_index, center in enumerate(centers):
        if band_index % 2 == 0:
            ax.axvspan(center - 0.55, center + 0.55, color="0.96", zorder=0)
        if band_index > 0:
            ax.axvline((centers[band_index - 1] + center) / 2.0, color="0.82", linewidth=0.8, zorder=0)
    for color_index, color_value in enumerate(color_values):
        values = []
        positions = []
        for band_index, band in enumerate(bands):
            selector = work[band_col].astype(str).eq(str(band))
            if selected_color_col:
                selector &= work[selected_color_col].astype(str).eq(str(color_value))
            series = pd.to_numeric(work.loc[selector, score_col], errors="coerce").dropna().to_numpy()
            values.append(series)
            positions.append(centers[band_index] + offsets[color_index])
        boxplot = ax.boxplot(values, positions=positions, widths=width, patch_artist=True, manage_ticks=False, showfliers=False)
        color = palette(color_index % 10)
        for patch in boxplot["boxes"]:
            patch.set_facecolor(color)
            patch.set_alpha(0.55)
        for median in boxplot["medians"]:
            median.set_color("black")
        label = _color_group_label(color_value, selected_color_col)
        ax.plot([], [], color=color, linewidth=6, alpha=0.55, label=label)
    ax.set_xticks(centers)
    ax.set_xticklabels([band_display_label(band) for band in bands], rotation=25, ha="right")
    ax.set_ylabel(value_column_display_name(score_col))
    ax.set_xlabel("Passband")
    apply_figure_context(
        ax,
        df,
        value_col=score_col,
        title=title,
        max_values=3,
        include_metric=selected_color_col != metric_col,
        include_model=False,
        include_period=False,
        include_value=False,
    )
    if selected_color_col:
        ax.legend(title=_color_group_label(selected_color_col, None), frameon=True, fontsize=8, loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0)
        fig.subplots_adjust(right=0.76, bottom=0.18)
    ax.grid(True, axis="y", alpha=0.25)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _heatmap(
    pivot: pd.DataFrame,
    output_path: str | Path | None,
    *,
    title: str,
    cbar_label: str,
    context_df: pd.DataFrame | None = None,
    value_col: str | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Draw a numeric heatmap."""

    values = pivot.to_numpy(dtype=float)
    cmap, vmin, vmax = value_color_settings(values, value_col)
    fig, ax = plt.subplots(figsize=(max(6.2, 0.55 * pivot.shape[1] + 3.5), max(4.2, 0.35 * pivot.shape[0] + 2.2)), dpi=180, constrained_layout=True)
    image = ax.imshow(values, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xticks(np.arange(pivot.shape[1]))
    ax.set_xticklabels(pivot.columns.astype(str), rotation=35, ha="right")
    ax.set_yticks(np.arange(pivot.shape[0]))
    ax.set_yticklabels(pivot.index.astype(str))
    apply_figure_context(ax, context_df, value_col=value_col, title=title, max_values=3, include_counts=False, include_value=False, include_metric=False, include_model=False)
    fig.colorbar(image, ax=ax, pad=0.04, label=cbar_label)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _require(df: pd.DataFrame, columns: list[str]) -> None:
    """Raise a clear error when columns are missing."""

    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")


def _color_group_label(value: object, color_col: str | None) -> str:
    """Return a readable legend label for metric or metric-group colors."""

    if color_col == "metric":
        return metric_display_name(value)
    if color_col == "model":
        return model_display_name(value)
    return str(value).replace("_", " ").title()


def _band_sort_key(value: object) -> tuple[float, str]:
    """Return a stable sort key for period-band labels.

    Inputs are labels such as ``"1-2 sec"``. The output sorts by the first
    numeric period when present, then by the raw label.
    """

    text = str(value)
    token = text.replace("sec", "").replace("s", "").strip().split("-", 1)[0]
    try:
        return (float(token), text)
    except ValueError:
        return (float("inf"), text)


def _color_sort_key(value: object) -> tuple[int, str]:
    """Return a stable metric/group display order for colored boxplots.

    Inputs are metric names or arbitrary category labels. The output keeps
    common metric names in workflow order and falls back to alphabetical text.
    """

    order = {"PGA": 0, "PGV": 1, "PGD": 2, "PSA": 3, "FAS": 4, "CAV": 5}
    text = str(value)
    return (order.get(text, 100), text)


__all__ = ["plot_band_score_distribution", "plot_model_metric_heatmap", "plot_winner_heatmap"]
