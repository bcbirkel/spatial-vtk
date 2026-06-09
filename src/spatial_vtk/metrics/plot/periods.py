"""Period-domain metric plotting helpers."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from spatial_vtk.config.labels import value_column_display_name
from spatial_vtk.visualize.figure_context import apply_figure_context
from spatial_vtk.visualize.figure_io import finish_figure
from spatial_vtk.visualize.selection import FigureSpatialSelection, apply_figure_spatial_selection


def plot_psa_period_curve(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    metric: str | None = "PSA",
    metric_col: str = "metric",
    period_col: str = "period_s",
    value_col: str = "residual",
    group_col: str | None = "model",
    title: str = "PSA Period Response",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Plot PSA residuals or scores against oscillator period.

    Parameters
    ----------
    df
        Long metric table. If ``metric`` and ``metric_col`` are available, the
        table is filtered before plotting.
    output_path, outpath
        Optional destination for the figure.
    metric, metric_col
        Metric name and column used to select PSA rows. Set ``metric=None`` to
        plot an already-filtered table.
    period_col, value_col, group_col
        Columns used for period, plotted value, and optional grouping.
    title
        Figure title.
    showfig, savefig
        Notebook/display and file-write controls.

    Returns
    -------
    matplotlib.figure.Figure
        The finished figure.
    """

    plot_df = _select_metric_rows(df, metric=metric, metric_col=metric_col)
    plot_df, subset_label = apply_figure_spatial_selection(plot_df, spatial_selection, **spatial_kwargs)
    if period_col not in plot_df.columns or value_col not in plot_df.columns:
        raise KeyError(f"Dataframe must include {period_col!r} and {value_col!r}.")
    fig, ax = plt.subplots(figsize=(7.4, 5.0), dpi=180)
    groups = [(None, plot_df)] if group_col is None or group_col not in plot_df.columns else list(plot_df.groupby(group_col, dropna=False))
    for label, subset in groups:
        summary = subset.groupby(period_col, dropna=False)[value_col].median().reset_index()
        ax.plot(pd.to_numeric(summary[period_col], errors="coerce"), pd.to_numeric(summary[value_col], errors="coerce"), marker="o", linewidth=1.2, label=str(label) if label is not None else None)
    ax.set_xscale("log")
    ax.axhline(0.0, color="black", linewidth=0.8, linestyle=":")
    ax.set_xlabel("Period (s)")
    ax.set_ylabel(value_column_display_name(value_col))
    apply_figure_context(ax, plot_df, value_col=value_col, title=title, max_values=3, include_period=False, include_metric=False, include_value=False, extra=[subset_label] if subset_label else None)
    ax.grid(True, which="both", alpha=0.25)
    if group_col and group_col in plot_df.columns:
        ax.legend(frameon=True, fontsize=8)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _select_metric_rows(df: pd.DataFrame, *, metric: str | None, metric_col: str) -> pd.DataFrame:
    """Return rows for one metric when a metric column is present.

    Parameters
    ----------
    df
        Long metric table.
    metric
        Metric name to select, or ``None`` to skip filtering.
    metric_col
        Column containing metric names.

    Returns
    -------
    pandas.DataFrame
        Filtered metric rows.
    """

    if metric is None or metric_col not in df.columns:
        return df.copy()
    selected = df.loc[df[metric_col].astype(str).str.upper().eq(str(metric).upper())].copy()
    if selected.empty:
        raise ValueError(f"No rows found for metric {metric!r} in column {metric_col!r}.")
    return selected


def plot_period_spectra(
    spectra_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    period_col: str = "period_s",
    amplitude_col: str = "amplitude",
    group_col: str | None = "series",
    title: str = "Period Spectra",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Plot period spectra from a long spectra table."""

    return plot_psa_period_curve(
        spectra_df,
        output_path,
        period_col=period_col,
        value_col=amplitude_col,
        group_col=group_col,
        title=title,
        showfig=showfig,
        savefig=savefig,
        outpath=outpath,
        spatial_selection=spatial_selection,
        **spatial_kwargs,
    )


def plot_period_spectrogram(
    spectrogram_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    time_col: str = "time_s",
    period_col: str = "period_s",
    value_col: str = "amplitude",
    title: str = "Period Spectrogram",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot a time-period spectrogram from a long table."""

    required = [time_col, period_col, value_col]
    missing = [column for column in required if column not in spectrogram_df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")
    pivot = spectrogram_df.pivot_table(index=period_col, columns=time_col, values=value_col, aggfunc="mean")
    fig, ax = plt.subplots(figsize=(7.5, 5.2), dpi=180)
    image = ax.imshow(pivot.to_numpy(dtype=float), aspect="auto", origin="lower", extent=(float(pivot.columns.min()), float(pivot.columns.max()), float(pivot.index.min()), float(pivot.index.max())), cmap="magma")
    ax.set_yscale("log")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Period (s)")
    apply_figure_context(ax, spectrogram_df, value_col=value_col, title=title, max_values=3, include_value=False)
    fig.colorbar(image, ax=ax, label=value_column_display_name(value_col))
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


__all__ = ["plot_period_spectra", "plot_period_spectrogram", "plot_psa_period_curve"]
