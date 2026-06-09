"""Metric trend plotting helpers."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from spatial_vtk.config.labels import display_label, metric_display_name, model_display_name, value_column_display_name
from spatial_vtk.visualize.figure_context import apply_figure_context, figure_context_text
from spatial_vtk.visualize.fit import FitMethod, draw_scatter_fit
from spatial_vtk.visualize.figure_io import finish_figure
from spatial_vtk.visualize.selection import FigureSpatialSelection, apply_figure_spatial_selection


def plot_metric_trend(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    x_col: str,
    y_col: str = "residual",
    metric_col: str = "metric",
    group_col: str | None = "model",
    title: str | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    output_key: str | None = None,
    connect_points: bool = True,
    fit_method: FitMethod = None,
    fit: FitMethod = None,
    lowess_frac: float = 0.65,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Plot metric values or residuals against one numeric variable."""

    plot_df, subset_label = apply_figure_spatial_selection(df, spatial_selection, **spatial_kwargs)
    _require_columns(plot_df, [x_col, y_col, metric_col])
    fig, ax = plt.subplots(figsize=(7.5, 5.0), dpi=180)
    groups = [(None, plot_df)] if group_col is None or group_col not in plot_df.columns else list(plot_df.groupby(group_col, dropna=False))
    selected_fit = fit_method if fit_method is not None else fit
    palette = plt.get_cmap("tab10")
    for group_index, (label, subset) in enumerate(groups):
        x = pd.to_numeric(subset[x_col], errors="coerce")
        y = pd.to_numeric(subset[y_col], errors="coerce")
        finite = x.notna() & y.notna()
        plot_subset = pd.DataFrame({"x": x[finite], "y": y[finite]}).sort_values("x")
        if plot_subset.empty:
            continue
        legend_label = _group_label(label, group_col=group_col) if label is not None else None
        color = palette(group_index % 10)
        if connect_points and selected_fit is None and len(plot_subset) > 1:
            ax.plot(plot_subset["x"], plot_subset["y"], marker="o", markersize=4.0, linewidth=1.1, alpha=0.78, color=color, label=legend_label)
        else:
            ax.scatter(plot_subset["x"], plot_subset["y"], s=24, alpha=0.7, color=color, label=legend_label)
            draw_scatter_fit(
                ax,
                plot_subset["x"].to_numpy(dtype=float),
                plot_subset["y"].to_numpy(dtype=float),
                fit_method=selected_fit,
                lowess_frac=lowess_frac,
                color=color,
                label=legend_label,
            )
    if _uses_zero_reference(y_col):
        ax.axhline(0.0, color="black", linewidth=0.8, linestyle=":")
    metric_part = ""
    if metric_col in plot_df.columns and plot_df[metric_col].nunique(dropna=True) == 1:
        metric_part = f" ({metric_display_name(plot_df[metric_col].dropna().iloc[0])})"
    ax.set_xlabel(display_label(x_col))
    ax.set_ylabel(value_column_display_name(y_col))
    apply_figure_context(
        ax,
        plot_df,
        value_col=y_col,
        title=title or f"{value_column_display_name(y_col)} vs {display_label(x_col)}{metric_part}",
        max_values=3,
        include_value=False,
        include_metric=not (group_col == metric_col),
        include_model=not (group_col == "model"),
        extra=[subset_label] if subset_label else None,
    )
    ax.grid(True, alpha=0.25)
    if group_col and group_col in df.columns:
        ax.legend(frameon=True, fontsize=8)
    return finish_figure(fig, output_path, outpath=outpath, output_key=output_key, showfig=showfig, savefig=savefig)


def plot_residuals_vs_distance(df: pd.DataFrame, output_path: str | Path | None = None, **kwargs) -> plt.Figure:
    """Plot residuals against source-station distance."""

    y_col = kwargs.pop("y_col", kwargs.pop("residual_col", "residual"))
    return plot_metric_trend(
        df,
        output_path,
        x_col=kwargs.pop("distance_col", "distance_km"),
        y_col=y_col,
        title=kwargs.pop("title", "Residuals vs Distance"),
        output_key=kwargs.pop("output_key", "residuals_vs_distance"),
        **kwargs,
    )


def plot_residuals_vs_depth(df: pd.DataFrame, output_path: str | Path | None = None, **kwargs) -> plt.Figure:
    """Plot residuals against event depth."""

    y_col = kwargs.pop("y_col", kwargs.pop("residual_col", "residual"))
    return plot_metric_trend(
        df,
        output_path,
        x_col=kwargs.pop("depth_col", "depth_km"),
        y_col=y_col,
        title=kwargs.pop("title", "Residuals vs Depth"),
        output_key=kwargs.pop("output_key", "residuals_vs_depth"),
        **kwargs,
    )


def plot_score_trends(df: pd.DataFrame, output_path: str | Path | None = None, *, x_col: str = "distance_km", score_col: str = "score", **kwargs) -> plt.Figure:
    """Plot GOF scores against one numeric variable."""

    return plot_metric_trend(
        df,
        output_path,
        x_col=x_col,
        y_col=score_col,
        title=kwargs.pop("title", f"{value_column_display_name(score_col)} vs {display_label(x_col)}"),
        output_key=kwargs.pop("output_key", "score_trends"),
        **kwargs,
    )


def plot_phase_delay_vs_distance(df: pd.DataFrame, output_path: str | Path | None = None, *, delay_col: str = "value", distance_col: str = "distance_km", **kwargs) -> plt.Figure:
    """Plot phase or travel-time delay against source-station distance."""

    return plot_metric_trend(
        df,
        output_path,
        x_col=distance_col,
        y_col=delay_col,
        title=kwargs.pop("title", "Delay vs Distance"),
        output_key=kwargs.pop("output_key", "phase_delay_vs_distance"),
        **kwargs,
    )


def plot_residuals_vs_distance_and_depth(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    distance_col: str = "distance_km",
    depth_col: str = "depth_km",
    residual_col: str = "residual",
    metric_col: str = "metric",
    group_col: str | None = "metric",
    title: str = "Residuals vs Distance and Depth",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    fit_method: FitMethod = None,
    fit: FitMethod = None,
    lowess_frac: float = 0.65,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Plot residual trends against distance and depth in one figure."""

    plot_df, subset_label = apply_figure_spatial_selection(df, spatial_selection, **spatial_kwargs)
    _require_columns(plot_df, [distance_col, depth_col, residual_col, metric_col])
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 5.4), dpi=180, constrained_layout=False)
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.28, top=0.84, wspace=0.14)
    selected_fit = fit_method if fit_method is not None else fit
    _draw_trend_axis(axes[0], plot_df, x_col=distance_col, y_col=residual_col, group_col=group_col, fit_method=selected_fit, lowess_frac=lowess_frac)
    _draw_trend_axis(axes[1], plot_df, x_col=depth_col, y_col=residual_col, group_col=group_col, fit_method=selected_fit, lowess_frac=lowess_frac)
    for ax, x_col in zip(axes, (distance_col, depth_col), strict=True):
        if x_col == distance_col:
            ax.set_xlabel("Distance (km)")
        elif x_col == depth_col:
            ax.set_xlabel("Depth (km)")
        else:
            ax.set_xlabel(display_label(x_col))
        ax.set_ylabel(value_column_display_name(residual_col))
        ax.grid(True, alpha=0.25)
        if _uses_zero_reference(residual_col):
            ax.axhline(0.0, color="black", linewidth=0.8, linestyle=":")
    context = figure_context_text(
        plot_df,
        value_col=residual_col,
        max_values=3,
        include_value=False,
        include_metric=not (group_col == metric_col),
        include_model=not (group_col == "model"),
    )
    if subset_label:
        context = f"{context} | {subset_label}" if context else subset_label
    fig.suptitle(f"{title}\n{context}" if context else title)
    if group_col and group_col in df.columns:
        _add_figure_legend(fig, axes[0])
    return finish_figure(fig, output_path, outpath=outpath, output_key="residuals_vs_distance_and_depth", showfig=showfig, savefig=savefig)


def _draw_trend_axis(ax: plt.Axes, df: pd.DataFrame, *, x_col: str, y_col: str, group_col: str | None, fit_method: FitMethod = None, lowess_frac: float = 0.65) -> None:
    """Draw connected trend points on an existing axis."""

    groups = [(None, df)] if group_col is None or group_col not in df.columns else list(df.groupby(group_col, dropna=False))
    palette = plt.get_cmap("tab10")
    for group_index, (label, subset) in enumerate(groups):
        x = pd.to_numeric(subset[x_col], errors="coerce")
        y = pd.to_numeric(subset[y_col], errors="coerce")
        plot_subset = pd.DataFrame({"x": x, "y": y}).dropna().sort_values("x")
        if plot_subset.empty:
            continue
        legend_label = _group_label(label, group_col=group_col) if label is not None else None
        color = palette(group_index % 10)
        if fit_method is None:
            ax.plot(plot_subset["x"], plot_subset["y"], marker="o", markersize=4.0, linewidth=1.1, alpha=0.78, color=color, label=legend_label)
        else:
            ax.scatter(plot_subset["x"], plot_subset["y"], s=24, alpha=0.7, color=color, label=legend_label)
            draw_scatter_fit(ax, plot_subset["x"].to_numpy(dtype=float), plot_subset["y"].to_numpy(dtype=float), fit_method=fit_method, lowess_frac=lowess_frac, color=color, label=legend_label)


def _add_figure_legend(fig: plt.Figure, source_ax: plt.Axes) -> None:
    """Place a shared trend legend outside the data panels.

    Inputs are a figure and one axis containing representative handles. The
    output is an external figure-level legend below the subplot area.
    """

    handles, labels = source_ax.get_legend_handles_labels()
    if not handles:
        return
    if source_ax.legend_:
        source_ax.legend_.remove()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.025),
        ncol=3,
        frameon=True,
        fontsize=8,
    )


def _group_label(label: object, *, group_col: str | None) -> str:
    """Return a readable legend label for trend groups."""

    if group_col == "model":
        return model_display_name(label)
    if group_col == "metric":
        return metric_display_name(label)
    return display_label(label)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    """Raise a clear error for missing columns."""

    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")


def _uses_zero_reference(value_col: str) -> bool:
    """Return whether a metric value should show a zero reference line."""

    lowered = str(value_col).lower()
    return any(token in lowered for token in ("resid", "delay", "error", "centered"))


__all__ = [
    "plot_metric_trend",
    "plot_phase_delay_vs_distance",
    "plot_residuals_vs_depth",
    "plot_residuals_vs_distance_and_depth",
    "plot_residuals_vs_distance",
    "plot_score_trends",
]
