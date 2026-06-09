"""Plot wrappers for spatial correlation and clustering results.

Purpose
-------
This module draws lightweight review figures from public spatial-statistics
tables. It does not discover files, run analyses, or depend on private artifact
registries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from spatial_vtk.config.labels import display_label, metric_display_name
from spatial_vtk.spatial.calculate.correlation import CorrelationLengthFit
from spatial_vtk.visualize.figure_context import add_below_axes_table, apply_figure_context, value_color_settings
from spatial_vtk.visualize.fit import FitMethod, draw_scatter_fit
from spatial_vtk.visualize.figure_io import finish_figure
from spatial_vtk.visualize.selection import FigureSpatialSelection, apply_figure_spatial_selection


def _display_label(value: object) -> str:
    """Convert a table or feature token into a readable figure label."""

    return display_label(value)


def plot_correlogram(
    distance_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "Spatial Correlogram",
    fit: CorrelationLengthFit | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot an empirical distance-binned correlogram.

    Parameters
    ----------
    distance_df
        Output from ``build_distance_bin_summary``.
    output_path
        Figure path to write.
    title
        Figure title.
    fit
        Optional exponential correlation-length fit.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    fig, ax = plt.subplots(figsize=(8.0, 5.0), dpi=180)
    plot_df = distance_df.loc[pd.to_numeric(distance_df.get("pair_count", 0), errors="coerce") > 0].copy()
    if plot_df.empty:
        ax.text(0.5, 0.5, "No distance-bin pairs", ha="center", va="center", transform=ax.transAxes)
    else:
        ax.plot(plot_df["distance_center_km"], plot_df["mean_pair_correlation"], marker="o", linewidth=1.2)
        if fit is not None:
            xfit = np.linspace(0.0, float(plot_df["distance_end_km"].max()), 300)
            yfit = np.exp(-xfit / max(float(fit.correlation_length_km), 1.0e-6))
            ax.plot(xfit, yfit, linestyle="--", linewidth=1.2, label="exponential fit")
            _add_correlation_fit_table(ax, fit, r_squared=_fit_r_squared(plot_df, fit))
        ax.axhline(0.0, color="black", linewidth=0.8, linestyle=":")
        ax.set_xlabel("Station separation bin center (km)")
        ax.set_ylabel("Mean pair correlation")
        if fit is not None:
            ax.legend(frameon=True)
    apply_figure_context(ax, distance_df, value_col="mean_pair_correlation", title=title, max_values=3, include_value=False)
    ax.grid(True, alpha=0.25)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_distance_correlation_by_metric(
    distance_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "Spatial Correlation by Distance",
    metric_col: str = "metric",
    distance_col: str = "distance_center_km",
    correlation_col: str = "mean_pair_correlation",
    pair_count_col: str = "pair_count",
    significance_df: pd.DataFrame | None = None,
    significance_metric_col: str = "metric",
    p_col: str | None = None,
    alpha: float = 0.05,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot distance-binned spatial correlation for one or more metrics.

    Parameters
    ----------
    distance_df
        Distance-bin correlation table, usually from
        ``build_distance_bin_summary`` with a metric column added.
    output_path
        Figure path to write.
    title
        Figure title.
    metric_col, distance_col, correlation_col, pair_count_col
        Column names used for the metric grouping, distance bin center,
        binned correlation value, and number of station pairs.
    significance_df
        Optional Moran or permutation test table used to mark significant
        metrics. The table should include a metric column and a p-value column.
    significance_metric_col, p_col, alpha
        Significance table column names and p-value threshold.

    Returns
    -------
    matplotlib.figure.Figure
        Figure containing one line per metric.
    """

    missing = [column for column in [distance_col, correlation_col] if column not in distance_df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")

    plot_df = distance_df.copy()
    if metric_col not in plot_df.columns:
        plot_df[metric_col] = "metric"
    if pair_count_col in plot_df.columns:
        plot_df = plot_df.loc[pd.to_numeric(plot_df[pair_count_col], errors="coerce").fillna(0) > 0].copy()
    plot_df[distance_col] = pd.to_numeric(plot_df[distance_col], errors="coerce")
    plot_df[correlation_col] = pd.to_numeric(plot_df[correlation_col], errors="coerce")
    plot_df = plot_df.dropna(subset=[distance_col, correlation_col])

    sig_lookup, p_lookup, statistic_lookup = _metric_significance_lookup(
        significance_df,
        metric_col=significance_metric_col,
        p_col=p_col,
        alpha=alpha,
    )
    has_significance = any(sig_lookup.values())

    fig, ax = plt.subplots(figsize=(8.4, 5.2), dpi=180)
    if plot_df.empty:
        ax.text(0.5, 0.5, "No distance-bin correlations", ha="center", va="center", transform=ax.transAxes)
    else:
        for metric_name, sub in plot_df.groupby(metric_col, sort=False):
            sub = sub.sort_values(distance_col)
            metric_key = str(metric_name)
            significant = bool(sig_lookup.get(metric_key, False))
            label = f"{metric_display_name(metric_name)}*" if significant else metric_display_name(metric_name)
            ax.plot(
                sub[distance_col],
                sub[correlation_col],
                marker="o",
                markersize=6.0 if significant else 4.5,
                linewidth=2.0 if significant else 1.35,
                label=label,
                zorder=3 if significant else 2,
            )
        ax.axhline(0.0, color="black", linewidth=0.8, linestyle=":")
        ax.set_xlabel("Station separation bin center (km)")
        ax.set_ylabel("Mean pair correlation")
        legend_title = f"Metric (* p<{alpha:g})" if has_significance else "Metric"
        ax.legend(title=legend_title, frameon=True, fontsize=8)
        if significance_df is not None and not significance_df.empty:
            _add_metric_significance_table(
                ax,
                p_lookup=p_lookup,
                statistic_lookup=statistic_lookup,
                sig_lookup=sig_lookup,
                alpha=alpha,
            )
    apply_figure_context(ax, plot_df, value_col=correlation_col, title=title, max_values=3, include_value=False)
    ax.grid(True, alpha=0.25)
    return finish_figure(
        fig,
        output_path,
        outpath=outpath,
        output_key="spatial_correlation_distance",
        showfig=showfig,
        savefig=savefig,
    )


def plot_semivariogram(
    distance_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "Semivariogram",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot an empirical distance-binned semivariogram."""

    fig, ax = plt.subplots(figsize=(8.0, 5.0), dpi=180)
    plot_df = distance_df.loc[pd.to_numeric(distance_df.get("pair_count", 0), errors="coerce") > 0].copy()
    if plot_df.empty:
        ax.text(0.5, 0.5, "No distance-bin pairs", ha="center", va="center", transform=ax.transAxes)
    else:
        ax.plot(plot_df["distance_center_km"], plot_df["mean_semivariance"], marker="o", linewidth=1.2)
        ax.set_xlabel("Station separation bin center (km)")
        ax.set_ylabel("Mean semivariance")
    apply_figure_context(ax, distance_df, value_col="mean_semivariance", title=title, max_values=3, include_value=False)
    ax.grid(True, alpha=0.25)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_directional_correlogram(
    directional_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "Directional Correlogram",
    fit_df: pd.DataFrame | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot distance-binned correlations split by station-pair orientation."""

    fig, ax = plt.subplots(figsize=(8.0, 5.0), dpi=180)
    plot_df = directional_df.loc[pd.to_numeric(directional_df.get("pair_count", 0), errors="coerce") > 0].copy()
    if plot_df.empty:
        ax.text(0.5, 0.5, "No directional distance-bin pairs", ha="center", va="center", transform=ax.transAxes)
    else:
        fit_lookup: dict[float, float] = {}
        if fit_df is not None and not fit_df.empty:
            for row in fit_df.itertuples(index=False):
                value = getattr(row, "correlation_length_km", np.nan)
                if np.isfinite(value):
                    fit_lookup[float(row.direction_center_deg)] = float(value)
        for direction_center_deg, sub in plot_df.groupby("direction_center_deg", sort=True):
            label = str(sub["direction_label"].iloc[0])
            corr_len = fit_lookup.get(float(direction_center_deg))
            legend_label = f"{label} (L={corr_len:.1f} km)" if corr_len is not None else label
            ax.plot(sub["distance_center_km"], sub["mean_pair_correlation"], marker="o", linewidth=1.2, label=legend_label)
        if fit_lookup:
            _add_directional_fit_table(ax, fit_df)
        ax.axhline(0.0, color="black", linewidth=0.8, linestyle=":")
        ax.set_xlabel("Station separation bin center (km)")
        ax.set_ylabel("Mean pair correlation")
        ax.legend(frameon=True, fontsize=8)
    apply_figure_context(ax, directional_df, value_col="mean_pair_correlation", title=title, max_values=3, include_value=False)
    ax.grid(True, alpha=0.25)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_block_holdout_scatter(
    prediction_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "Spatial Block Holdout",
    fit_method: FitMethod = None,
    fit: FitMethod = None,
    lowess_frac: float = 0.65,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Plot predicted versus observed held-out station bias."""

    plot_df, subset_label = apply_figure_spatial_selection(prediction_df, spatial_selection, **spatial_kwargs)
    fig, ax = plt.subplots(figsize=(6.5, 6.0), dpi=180)
    if plot_df.empty:
        ax.text(0.5, 0.5, "No block holdout predictions", ha="center", va="center", transform=ax.transAxes)
    else:
        observed = pd.to_numeric(plot_df["observed_mean_centered"], errors="coerce").to_numpy(dtype=float)
        predicted = pd.to_numeric(plot_df["predicted_mean_centered"], errors="coerce").to_numpy(dtype=float)
        finite = np.isfinite(observed) & np.isfinite(predicted)
        if not np.any(finite):
            ax.text(0.5, 0.5, "No finite holdout predictions", ha="center", va="center", transform=ax.transAxes)
        else:
            observed = observed[finite]
            predicted = predicted[finite]
            ax.scatter(observed, predicted, s=32, alpha=0.85)
            low = float(np.nanmin(np.concatenate([observed, predicted])))
            high = float(np.nanmax(np.concatenate([observed, predicted])))
            pad = 0.05 * max(high - low, 1.0)
            ax.plot([low - pad, high + pad], [low - pad, high + pad], linestyle="--", linewidth=1.0)
            selected_fit = fit_method if fit_method is not None else fit
            draw_scatter_fit(ax, observed, predicted, fit_method=selected_fit, lowess_frac=lowess_frac, color="black", label=None, linewidth=1.1)
            ax.set_xlim(low - pad, high + pad)
            ax.set_ylim(low - pad, high + pad)
            ax.set_xlabel("Observed station bias")
            ax.set_ylabel("Predicted station bias")
            rmse = float(np.sqrt(np.nanmean((predicted - observed) ** 2)))
            _add_holdout_table(ax, rmse=rmse, n_predictions=len(observed))
    apply_figure_context(ax, plot_df, value_col="prediction_error", title=title, max_values=3, include_value=False, extra=[subset_label] if subset_label else None)
    ax.grid(True, alpha=0.25)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_cluster_solution_scores(
    score_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "Cluster Solution Scores",
    k_column: str = "n_clusters",
    score_column: str = "silhouette",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot silhouette score versus candidate cluster count."""

    fig, ax = plt.subplots(figsize=(7.0, 4.5), dpi=180)
    if score_df.empty:
        ax.text(0.5, 0.5, "No clustering solutions", ha="center", va="center", transform=ax.transAxes)
    else:
        plot_df = score_df.sort_values(k_column).copy()
        ax.plot(plot_df[k_column], plot_df[score_column], marker="o", linewidth=1.2)
        best_idx = pd.to_numeric(plot_df[score_column], errors="coerce").idxmax()
        if pd.notna(best_idx):
            best_row = plot_df.loc[best_idx]
            ax.scatter([best_row[k_column]], [best_row[score_column]], s=60)
            _add_cluster_score_table(ax, best_row=best_row, k_column=k_column, score_column=score_column)
        ax.set_xlabel("Cluster count")
        ax.set_ylabel("Silhouette score (unitless)" if str(score_column).lower() == "silhouette" else display_label(score_column))
        ax.set_xticks([int(value) for value in pd.to_numeric(plot_df[k_column], errors="coerce").dropna().unique()])
    apply_figure_context(ax, score_df, value_col=score_column, title=title, max_values=3, include_counts=False, include_value=False)
    ax.grid(True, alpha=0.25)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_cluster_feature_heatmap(
    feature_summary_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "Cluster Feature Summary",
    feature_order: Sequence[str] | None = None,
    feature_label_map: Mapping[str, str] | None = None,
    value_column: str = "feature_mean",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot a cluster-by-feature heatmap from cluster feature summaries."""

    fig, ax = plt.subplots(figsize=(10.0, 4.8), dpi=180)
    if feature_summary_df.empty:
        ax.text(0.5, 0.5, "No cluster feature summary", ha="center", va="center", transform=ax.transAxes)
    else:
        pivot = feature_summary_df.pivot(index="cluster_name", columns="feature", values=value_column)
        if feature_order is not None:
            ordered = [feature for feature in feature_order if feature in pivot.columns]
            remaining = [feature for feature in pivot.columns if feature not in ordered]
            pivot = pivot[ordered + remaining]
        else:
            pivot = pivot[sorted(pivot.columns, key=lambda token: str(token).lower())]
        pivot = pivot.sort_index()
        values = pivot.to_numpy(dtype=float)
        cmap, vmin, vmax = value_color_settings(values, value_column)
        image = ax.imshow(values, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
        label_map = dict(feature_label_map or {})
        ax.set_xticks(np.arange(pivot.shape[1]))
        ax.set_xticklabels([label_map.get(str(token), _display_label(token)) for token in pivot.columns], rotation=45, ha="right")
        ax.set_yticks(np.arange(pivot.shape[0]))
        ax.set_yticklabels([_display_label(token) for token in pivot.index])
        fig.colorbar(image, ax=ax, label=_display_label(value_column))
    apply_figure_context(ax, feature_summary_df, value_col=value_column, title=title, max_values=3, include_counts=False, include_value=False)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_pattern_similarity(
    stations: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    metric: str,
    bin_label: str,
    title: str | None = None,
    fit_method: FitMethod = "linear",
    fit: FitMethod = None,
    lowess_frac: float = 0.65,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Plot observed versus synthetic station anomaly values for one metric/bin."""

    plot_stations, subset_label = apply_figure_spatial_selection(stations, spatial_selection, **spatial_kwargs)
    fig, ax = plt.subplots(figsize=(6.5, 6.0), dpi=180)
    subset = plot_stations.loc[(plot_stations["metric"].astype(str) == str(metric)) & (plot_stations["bin"].astype(str) == str(bin_label))].copy()
    pivot = subset.pivot_table(index="station_name", columns="dataset", values="value", aggfunc="mean")
    if {"observed", "synthetic"}.issubset(pivot.columns):
        matched = pivot[["observed", "synthetic"]].replace([np.inf, -np.inf], np.nan).dropna()
    else:
        matched = pd.DataFrame()
    if matched.empty:
        ax.text(0.5, 0.5, "No matched observed/synthetic stations", ha="center", va="center", transform=ax.transAxes)
    else:
        ax.scatter(matched["observed"], matched["synthetic"], s=34, alpha=0.85)
        low = float(np.nanmin(matched.to_numpy(dtype=float)))
        high = float(np.nanmax(matched.to_numpy(dtype=float)))
        pad = 0.05 * max(high - low, 1.0)
        ax.plot([low - pad, high + pad], [low - pad, high + pad], linestyle="--", linewidth=1.0)
        ax.set_xlim(low - pad, high + pad)
        ax.set_ylim(low - pad, high + pad)
        ax.set_xlabel("Observed station anomaly")
        ax.set_ylabel("Synthetic station anomaly")
        selected_fit = fit if fit is not None else fit_method
        draw_scatter_fit(
            ax,
            matched["observed"].to_numpy(dtype=float),
            matched["synthetic"].to_numpy(dtype=float),
            fit_method=selected_fit,
            lowess_frac=lowess_frac,
            color="black",
            label=None,
            linewidth=1.0,
        )
        if len(matched) >= 2:
            slope, intercept = np.polyfit(matched["observed"].to_numpy(dtype=float), matched["synthetic"].to_numpy(dtype=float), deg=1)
            _add_pattern_similarity_table(ax, pearson_r=float(matched["observed"].corr(matched["synthetic"])), slope=float(slope), n_stations=len(matched))
    apply_figure_context(
        ax,
        subset,
        value_col="value",
        title=title or f"{metric_display_name(metric)} {bin_label} Pattern Similarity",
        max_values=3,
        include_value=False,
        extra=[subset_label] if subset_label else None,
    )
    ax.grid(True, alpha=0.25)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _add_correlation_fit_table(ax: plt.Axes, fit: CorrelationLengthFit, *, r_squared: float | None = None) -> None:
    """Add an exponential-fit summary below a correlogram."""

    add_below_axes_table(
        ax,
        rows=[
            [
                "Exponential fit",
                f"{fit.correlation_length_km:.1f} km",
                f"{fit.effective_range_km:.1f} km",
                f"{r_squared:.2f}" if r_squared is not None and np.isfinite(r_squared) else "",
                f"{getattr(fit, 'n_bins_used', '')}",
            ]
        ],
        columns=["Fit", "Correlation length", "Effective range", "R2", "Bins used"],
        col_widths=[0.30, 0.23, 0.23, 0.12, 0.12],
    )


def _metric_significance_lookup(
    significance_df: pd.DataFrame | None,
    *,
    metric_col: str,
    p_col: str | None,
    alpha: float,
) -> tuple[dict[str, bool], dict[str, float], dict[str, float]]:
    """Build lookup tables for metric-level significance annotations."""

    if significance_df is None or significance_df.empty or metric_col not in significance_df.columns:
        return {}, {}, {}
    p_column = p_col or _first_existing_column(significance_df, ("p_two_sided", "p_value", "p", "pvalue"))
    if p_column is None:
        return {}, {}, {}
    statistic_column = _first_existing_column(significance_df, ("moran_i", "statistic", "test_statistic"))
    sig_lookup: dict[str, bool] = {}
    p_lookup: dict[str, float] = {}
    statistic_lookup: dict[str, float] = {}
    for row in significance_df.itertuples(index=False):
        metric = str(getattr(row, metric_col))
        p_value = pd.to_numeric(getattr(row, p_column), errors="coerce")
        if pd.notna(p_value):
            p_float = float(p_value)
            p_lookup[metric] = p_float
            sig_lookup[metric] = p_float < float(alpha)
        if statistic_column is not None:
            statistic = pd.to_numeric(getattr(row, statistic_column), errors="coerce")
            if pd.notna(statistic):
                statistic_lookup[metric] = float(statistic)
    return sig_lookup, p_lookup, statistic_lookup


def _first_existing_column(df: pd.DataFrame, candidates: Sequence[str]) -> str | None:
    """Return the first candidate column present in ``df``."""

    for column in candidates:
        if column in df.columns:
            return column
    return None


def _add_metric_significance_table(
    ax: plt.Axes,
    *,
    p_lookup: Mapping[str, float],
    statistic_lookup: Mapping[str, float],
    sig_lookup: Mapping[str, bool],
    alpha: float,
) -> None:
    """Add Moran significance details below a distance-correlation plot."""

    rows = []
    for metric in p_lookup:
        statistic = statistic_lookup.get(metric)
        rows.append(
            [
                metric_display_name(metric),
                f"{statistic:.3f}" if statistic is not None and np.isfinite(statistic) else "",
                f"{p_lookup[metric]:.3g}",
                "yes" if sig_lookup.get(metric, False) else "no",
            ]
        )
    if not rows:
        return
    add_below_axes_table(
        ax,
        rows=rows,
        columns=["Metric", "Moran's I", "p", f"p<{alpha:g}"],
        col_widths=[0.44, 0.18, 0.18, 0.20],
        font_size=7.5,
    )


def _fit_r_squared(distance_df: pd.DataFrame, fit: CorrelationLengthFit) -> float:
    """Return R-squared for the exponential correlogram fit."""

    x = pd.to_numeric(distance_df["distance_center_km"], errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(distance_df["mean_pair_correlation"], errors="coerce").to_numpy(dtype=float)
    finite = np.isfinite(x) & np.isfinite(y)
    if np.count_nonzero(finite) < 2:
        return float("nan")
    yhat = np.exp(-x[finite] / max(float(fit.correlation_length_km), 1.0e-6))
    ss_res = float(np.sum((y[finite] - yhat) ** 2))
    ss_tot = float(np.sum((y[finite] - np.nanmean(y[finite])) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0.0 else float("nan")


def _add_holdout_table(ax: plt.Axes, *, rmse: float, n_predictions: int) -> None:
    """Add a spatial holdout summary below a scatter plot."""

    add_below_axes_table(
        ax,
        rows=[["Held-out station bias", f"{rmse:.3f}", f"{int(n_predictions)}"]],
        columns=["Prediction target", "RMSE", "Predictions"],
        col_widths=[0.55, 0.20, 0.25],
    )


def _add_directional_fit_table(ax: plt.Axes, fit_df: pd.DataFrame | None) -> None:
    """Add directional correlation-length fit summaries below a plot."""

    if fit_df is None or fit_df.empty:
        return
    rows = []
    for row in fit_df.head(5).itertuples(index=False):
        direction = getattr(row, "direction_label", getattr(row, "direction_center_deg", "direction"))
        length = getattr(row, "correlation_length_km", np.nan)
        effective = getattr(row, "effective_range_km", np.nan)
        rows.append(
            [
                str(direction),
                f"{float(length):.1f} km" if np.isfinite(length) else "",
                f"{float(effective):.1f} km" if np.isfinite(effective) else "",
            ]
        )
    add_below_axes_table(
        ax,
        rows=rows,
        columns=["Direction", "Correlation length", "Effective range"],
        col_widths=[0.42, 0.29, 0.29],
    )


def _add_cluster_score_table(ax: plt.Axes, *, best_row: pd.Series, k_column: str, score_column: str) -> None:
    """Add selected cluster-solution summary below a score plot."""

    n_samples = best_row.get("n_samples", "")
    n_features = best_row.get("n_features", "")
    rows = [
        [
            f"{int(best_row[k_column])}",
            f"{float(best_row[score_column]):.3f}",
            str(int(n_samples)) if pd.notna(n_samples) and n_samples != "" else "",
            str(int(n_features)) if pd.notna(n_features) and n_features != "" else "",
        ]
    ]
    add_below_axes_table(
        ax,
        rows=rows,
        columns=["Selected k", display_label(score_column), "Samples", "Station features"],
        col_widths=[0.22, 0.28, 0.25, 0.25],
    )


def _add_pattern_similarity_table(ax: plt.Axes, *, pearson_r: float, slope: float, n_stations: int) -> None:
    """Add an observed/synthetic pattern similarity summary below a scatter plot."""

    add_below_axes_table(
        ax,
        rows=[["Observed vs synthetic station anomaly", f"{pearson_r:.3f}", f"{slope:.3f}", f"{int(n_stations)}"]],
        columns=["Comparison", "Pearson r", "Slope", "Stations"],
        col_widths=[0.48, 0.18, 0.16, 0.18],
    )
