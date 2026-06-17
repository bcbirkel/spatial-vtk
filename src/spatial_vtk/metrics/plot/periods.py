"""Period-domain metric plotting helpers."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from spatial_vtk.config.labels import metric_display_name, value_column_display_name
from spatial_vtk.visualize.figure_context import apply_figure_context, apply_robust_axis_limits, context_value_label, value_color_settings
from spatial_vtk.visualize.figure_sidecars import finish_figure_with_sidecar
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
    robust_axis_percentile: float | None = 95.0,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
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
    plot_df = _select_broadband_spectral_rows(plot_df, period_col=period_col, metric=metric, metric_col=metric_col)
    if period_col not in plot_df.columns or value_col not in plot_df.columns:
        raise KeyError(f"Dataframe must include {period_col!r} and {value_col!r}.")
    fig, ax = plt.subplots(figsize=(7.4, 5.0), dpi=180)
    groups = [(None, plot_df)] if group_col is None or group_col not in plot_df.columns else list(plot_df.groupby(group_col, dropna=False))
    sidecar_frames: list[pd.DataFrame] = []
    for label, subset in groups:
        summary = subset.groupby(period_col, dropna=False)[value_col].median().reset_index()
        summary["_plot_group"] = str(label) if label is not None else "all"
        ax.plot(pd.to_numeric(summary[period_col], errors="coerce"), pd.to_numeric(summary[value_col], errors="coerce"), marker="o", linewidth=1.2, label=str(label) if label is not None else None)
        sidecar_frames.append(summary)
    ax.set_xscale("log")
    ax.axhline(0.0, color="black", linewidth=0.8, linestyle=":")
    apply_robust_axis_limits(ax, pd.to_numeric(plot_df[value_col], errors="coerce"), value_col=value_col, df=plot_df, robust_percentile=robust_axis_percentile)
    ax.set_xlabel("Period (s)")
    ax.set_ylabel(context_value_label(value_col, plot_df))
    apply_figure_context(ax, plot_df, value_col=value_col, title=title, max_values=3, include_period=False, include_metric=False, include_value=False, extra=[subset_label] if subset_label else None)
    ax.grid(True, which="both", alpha=0.25)
    if group_col and group_col in plot_df.columns:
        ax.legend(frameon=True, fontsize=8)
    sidecar_df = pd.concat(sidecar_frames, ignore_index=True, sort=False) if sidecar_frames else plot_df.iloc[0:0].copy()
    return finish_figure_with_sidecar(
        fig,
        output_path,
        outpath=outpath,
        showfig=showfig,
        savefig=savefig,
        sidecar_df=sidecar_df,
        source_rows=plot_df,
        write_sidecar=write_sidecar,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
        metadata={"figure_type": "psa_period_curve", "period_col": period_col, "value_col": value_col, "group_col": group_col},
    )


def plot_period_score_distribution(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    metric: str | None = "PSA",
    metric_col: str = "metric",
    period_col: str = "period_s",
    score_col: str = "log2_residual",
    color_col: str | None = "component",
    title: str = "Period Score Distribution",
    robust_axis_percentile: float | None = 95.0,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
) -> plt.Figure:
    """Plot spectral metric distributions grouped by oscillator period.

    This is the period-domain counterpart to passband distribution plots. It is
    intended for broadband spectral metrics such as PSA and FAS, where
    ``period_s`` is the meaningful x-axis and passband labels should not be
    used.
    """

    plot_df = _select_metric_rows(df, metric=metric, metric_col=metric_col)
    plot_df = _select_broadband_spectral_rows(plot_df, period_col=period_col, metric=metric, metric_col=metric_col)
    missing = [column for column in (period_col, score_col) if column not in plot_df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")
    selected_color_col = color_col if color_col and color_col in plot_df.columns else None
    columns = [period_col, score_col] + ([selected_color_col] if selected_color_col else [])
    work = plot_df[columns].copy()
    work[period_col] = pd.to_numeric(work[period_col], errors="coerce")
    work[score_col] = pd.to_numeric(work[score_col], errors="coerce")
    work = work.dropna(subset=[period_col, score_col])

    fig, ax = plt.subplots(figsize=(8.5, 5.0), dpi=180)
    if work.empty:
        ax.text(0.5, 0.5, "No spectral period rows", ha="center", va="center", transform=ax.transAxes)
    else:
        periods = sorted(dict.fromkeys(work[period_col].astype(float)))
        color_values = sorted(dict.fromkeys(work[selected_color_col].astype(str))) if selected_color_col else ["All"]
        centers = np.arange(len(periods), dtype=float) * 1.25
        offsets = np.linspace(-0.30, 0.30, len(color_values)) if len(color_values) > 1 else np.array([0.0])
        width = min(0.56 / max(len(color_values), 1), 0.20)
        palette = plt.get_cmap("tab10")
        for period_index, center in enumerate(centers):
            if period_index % 2 == 0:
                ax.axvspan(center - 0.55, center + 0.55, color="0.96", zorder=0)
            if period_index > 0:
                ax.axvline((centers[period_index - 1] + center) / 2.0, color="0.82", linewidth=0.8, zorder=0)
        for color_index, color_value in enumerate(color_values):
            values = []
            positions = []
            for period_index, period in enumerate(periods):
                selector = work[period_col].eq(float(period))
                if selected_color_col:
                    selector &= work[selected_color_col].astype(str).eq(str(color_value))
                series = work.loc[selector, score_col].dropna().to_numpy(dtype=float)
                values.append(series)
                positions.append(centers[period_index] + offsets[color_index])
            boxplot = ax.boxplot(values, positions=positions, widths=width, patch_artist=True, manage_ticks=False, showfliers=False)
            color = palette(color_index % 10)
            for patch in boxplot["boxes"]:
                patch.set_facecolor(color)
                patch.set_alpha(0.55)
            for median in boxplot["medians"]:
                median.set_color("black")
            label = _period_color_label(color_value, selected_color_col)
            ax.plot([], [], color=color, linewidth=6, alpha=0.55, label=label)
        ax.set_xticks(centers)
        ax.set_xticklabels([_period_tick_label(period) for period in periods], rotation=25, ha="right")
        if selected_color_col:
            ax.legend(title=_period_color_label(selected_color_col, None), frameon=True, fontsize=8, loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0)
            fig.subplots_adjust(right=0.76, bottom=0.18)
    ax.set_ylabel(context_value_label(score_col, plot_df))
    ax.set_xlabel("PSA oscillator period")
    apply_robust_axis_limits(ax, pd.to_numeric(work[score_col], errors="coerce"), value_col=score_col, df=work, robust_percentile=robust_axis_percentile)
    apply_figure_context(ax, plot_df, value_col=score_col, title=title, max_values=3, include_period=False, include_metric=False, include_value=False)
    ax.grid(True, axis="y", alpha=0.25)
    return finish_figure_with_sidecar(
        fig,
        output_path,
        outpath=outpath,
        showfig=showfig,
        savefig=savefig,
        sidecar_df=work,
        source_rows=plot_df,
        write_sidecar=write_sidecar,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
        metadata={"figure_type": "period_score_distribution", "period_col": period_col, "score_col": score_col, "color_col": selected_color_col},
    )


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


def _select_broadband_spectral_rows(
    df: pd.DataFrame,
    *,
    period_col: str,
    metric: str | None,
    metric_col: str,
) -> pd.DataFrame:
    """Prefer broadband spectral rows and reject passband-duplicated periods."""

    if metric is None or period_col not in df.columns:
        return df
    band_col = next((column for column in ("passband", "band") if column in df.columns), None)
    if band_col is None:
        return df
    labels = df[band_col].fillna("").astype(str).str.strip().str.lower()
    broadband = labels.isin(["", "all", "broadband", "none", "nan"])
    if broadband.any():
        return df.loc[broadband].copy()
    key_cols = [
        column
        for column in (
            "event_id",
            "event",
            "event_title",
            "station",
            "station_id",
            "station_code",
            "network",
            "model",
            "component",
            metric_col,
            period_col,
        )
        if column in df.columns
    ]
    if not key_cols:
        return df
    work = df[key_cols].copy()
    work["_spectral_passband"] = labels.to_numpy()
    duplicate_passbands = work.groupby(key_cols, dropna=False)["_spectral_passband"].nunique(dropna=False)
    offenders = duplicate_passbands[duplicate_passbands > 1]
    if offenders.empty:
        return df
    raise ValueError(
        "Spectral period rows include the same event/station/model/component/period "
        "record repeated across passbands. PSA/FAS period figures require broadband "
        "spectral rows calculated once per oscillator period; rebuild the metric "
        "manifest/metrics with broadband spectral metrics or filter to broadband rows."
    )


def _period_tick_label(period: float) -> str:
    """Return a compact PSA period/frequency tick label."""

    if not np.isfinite(period) or period <= 0:
        return "unknown"
    return f"T={period:g}s\nf={1.0 / period:g}Hz"


def _period_color_label(value: object, color_col: str | None) -> str:
    """Return a readable legend label for period distribution groups."""

    if color_col == "metric":
        return metric_display_name(value)
    return str(value).replace("_", " ").title()


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
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Plot period spectra from a long spectra table."""

    return plot_psa_period_curve(
        spectra_df,
        output_path,
        metric=None,
        period_col=period_col,
        value_col=amplitude_col,
        group_col=group_col,
        title=title,
        showfig=showfig,
        savefig=savefig,
        outpath=outpath,
        spatial_selection=spatial_selection,
        write_sidecar=write_sidecar,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
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
    robust_percentile: float | None = 95.0,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
) -> plt.Figure:
    """Plot a time-period spectrogram from a long table."""

    required = [time_col, period_col, value_col]
    missing = [column for column in required if column not in spectrogram_df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")
    pivot = spectrogram_df.pivot_table(index=period_col, columns=time_col, values=value_col, aggfunc="mean")
    fig, ax = plt.subplots(figsize=(7.5, 5.2), dpi=180)
    values = pivot.to_numpy(dtype=float)
    cmap, vmin, vmax = value_color_settings(values, value_col, spectrogram_df, sequential_cmap="magma", robust_percentile=robust_percentile)
    image = ax.imshow(values, aspect="auto", origin="lower", extent=(float(pivot.columns.min()), float(pivot.columns.max()), float(pivot.index.min()), float(pivot.index.max())), cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_yscale("log")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Period (s)")
    apply_figure_context(ax, spectrogram_df, value_col=value_col, title=title, max_values=3, include_value=False)
    fig.colorbar(image, ax=ax, label=value_column_display_name(value_col))
    return finish_figure_with_sidecar(
        fig,
        output_path,
        outpath=outpath,
        showfig=showfig,
        savefig=savefig,
        sidecar_df=spectrogram_df,
        source_rows=spectrogram_df,
        write_sidecar=write_sidecar,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
        metadata={"figure_type": "period_spectrogram", "time_col": time_col, "period_col": period_col, "value_col": value_col},
    )


__all__ = ["plot_period_score_distribution", "plot_period_spectra", "plot_period_spectrogram", "plot_psa_period_curve"]
