"""Site-term metric diagnostic figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from spatial_vtk.config.labels import display_label, value_column_display_name
from spatial_vtk.metrics.plot.trends import plot_metric_trend
from spatial_vtk.visualize.figure_context import apply_figure_context
from spatial_vtk.visualize.figure_io import finish_figure
from spatial_vtk.visualize.selection import FigureSpatialSelection, apply_figure_spatial_selection


def plot_vs30_scatter(df: pd.DataFrame, output_path: str | Path | None = None, *, vs30_col: str = "Vs30", value_col: str = "residual", **kwargs) -> plt.Figure:
    """Plot metric residuals or scores against Vs30."""

    return plot_metric_trend(df, output_path, x_col=vs30_col, y_col=value_col, title=kwargs.pop("title", "Metric Response vs Vs30"), **kwargs)


def plot_geology_boxplot(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    geology_col: str = "geology_class",
    value_col: str = "residual",
    title: str = "Metric Response by Geology",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Plot metric residuals or scores by geology class."""

    plot_df, subset_label = apply_figure_spatial_selection(df, spatial_selection, **spatial_kwargs)
    if geology_col not in plot_df.columns or value_col not in plot_df.columns:
        raise KeyError(f"Dataframe must include {geology_col!r} and {value_col!r}.")
    fig, ax = plt.subplots(figsize=(8.2, 5.0), dpi=180)
    work = plot_df[[geology_col, value_col]].dropna()
    labels = sorted(work[geology_col].astype(str).unique())
    values = [pd.to_numeric(work.loc[work[geology_col].astype(str) == label, value_col], errors="coerce").dropna().to_numpy() for label in labels]
    ax.boxplot(values, tick_labels=labels, patch_artist=True)
    if any(token in value_col.lower() for token in ("resid", "delay", "error", "centered")):
        ax.axhline(0.0, color="black", linewidth=0.8, linestyle=":")
    ax.set_xlabel(display_label(geology_col))
    ax.set_ylabel(value_column_display_name(value_col))
    apply_figure_context(ax, plot_df, value_col=value_col, title=title, max_values=3, include_value=False, extra=[subset_label] if subset_label else None)
    ax.tick_params(axis="x", rotation=35)
    ax.grid(True, axis="y", alpha=0.25)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


__all__ = ["plot_geology_boxplot", "plot_vs30_scatter"]
