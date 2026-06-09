"""Map wrappers for PCA spatial modes.

Purpose
-------
This module maps station scores from PCA spatial-mode outputs. Basemaps are
enabled by default through the package's shared contextily helper.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import math

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

from collections.abc import Mapping

from spatial_vtk.config.labels import display_label
from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
from spatial_vtk.visualize.figure_context import apply_figure_context, figure_context_text
from spatial_vtk.visualize.fit import FitMethod, draw_scatter_fit
from spatial_vtk.visualize.figure_io import finish_figure


def _xy_columns(df: pd.DataFrame, *, lon_col: str | None = None, lat_col: str | None = None) -> tuple[str, str]:
    """Resolve longitude and latitude columns from common table schemas."""

    lon_candidates = [lon_col, "lon", "station_longitude", "longitude"]
    lat_candidates = [lat_col, "lat", "station_latitude", "latitude"]
    lon_name = next((name for name in lon_candidates if name and name in df.columns), None)
    lat_name = next((name for name in lat_candidates if name and name in df.columns), None)
    if lon_name is None or lat_name is None:
        raise KeyError("Could not resolve longitude/latitude columns.")
    return lon_name, lat_name


def _set_bounds(ax: plt.Axes, df: pd.DataFrame, lon_col: str, lat_col: str, bounds: tuple[float, float, float, float] | None) -> None:
    """Set map bounds from explicit bounds or table coordinates."""

    if bounds is not None:
        west, east, south, north = [float(value) for value in bounds]
    else:
        lon = pd.to_numeric(df[lon_col], errors="coerce").to_numpy(dtype=float)
        lat = pd.to_numeric(df[lat_col], errors="coerce").to_numpy(dtype=float)
        finite = np.isfinite(lon) & np.isfinite(lat)
        if not np.any(finite):
            west, east, south, north = -180.0, 180.0, -90.0, 90.0
        else:
            west, east = float(np.nanmin(lon[finite])), float(np.nanmax(lon[finite]))
            south, north = float(np.nanmin(lat[finite])), float(np.nanmax(lat[finite]))
            pad_x = max(0.03, 0.08 * max(east - west, 0.01))
            pad_y = max(0.03, 0.08 * max(north - south, 0.01))
            west, east, south, north = west - pad_x, east + pad_x, south - pad_y, north + pad_y
    ax.set_xlim(west, east)
    ax.set_ylim(south, north)
    _set_geographic_aspect(ax)


def _finish_map(
    ax: plt.Axes,
    *,
    add_basemap: bool,
    basemap_source: str,
    basemap_kwargs: dict[str, Any] | None,
) -> None:
    """Apply basemap, labels, and grid styling to map axes."""

    if add_basemap:
        kwargs = dict(basemap_kwargs or {})
        add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **kwargs)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, alpha=0.18, zorder=1)


def plot_pca_mode_map(
    station_scores_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    mode: str = "PC1",
    score_col: str | None = None,
    title: str | None = None,
    bounds: tuple[float, float, float, float] | None = None,
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot one PCA station-score mode on a lon/lat map.

    Parameters
    ----------
    station_scores_df
        Station score table from ``compute_pca_spatial_modes``.
    output_path
        Figure path to write.
    mode
        Mode label, such as ``"PC1"``. Used to infer ``score_col``.
    score_col
        Optional explicit score column. Defaults to ``"<mode>_score"``.
    title
        Optional figure title.
    bounds
        Optional ``(west, east, south, north)`` map bounds.
    add_basemap
        Whether to add a contextily basemap layer.
    basemap_source
        Contextily provider selector.
    basemap_kwargs
        Extra keyword arguments passed to the shared basemap helper.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    score_name = score_col or f"{mode}_score"
    fig, ax = plt.subplots(figsize=(8.0, 7.0), dpi=180, constrained_layout=True)
    if station_scores_df.empty or score_name not in station_scores_df.columns:
        ax.text(0.5, 0.5, f"No station scores for {mode}", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
    else:
        lon_col, lat_col = _xy_columns(station_scores_df)
        plot_df = station_scores_df.dropna(subset=[lon_col, lat_col, score_name]).copy()
        if plot_df.empty:
            ax.text(0.5, 0.5, f"No finite station scores for {mode}", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
        else:
            _set_bounds(ax, plot_df, lon_col, lat_col, bounds)
            _finish_map(ax, add_basemap=add_basemap, basemap_source=basemap_source, basemap_kwargs=basemap_kwargs)
            values = pd.to_numeric(plot_df[score_name], errors="coerce").to_numpy(dtype=float)
            vmax = max(float(np.nanmax(np.abs(values))) if np.isfinite(values).any() else 0.0, 1.0e-6)
            scatter = ax.scatter(
                plot_df[lon_col],
                plot_df[lat_col],
                c=values,
                cmap="coolwarm",
                vmin=-vmax,
                vmax=vmax,
                s=44,
                edgecolors="black",
                linewidths=0.35,
                zorder=3,
            )
            fig.colorbar(scatter, ax=ax, pad=0.045, label=display_label(f"{mode} station score"))
    apply_figure_context(ax, station_scores_df, value_col=score_name, title=title or f"{mode} Spatial Mode", max_values=3, include_counts=False, include_value=False, max_line_chars=72)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_pca_summary(
    station_scores_df: pd.DataFrame,
    explained_variance_df: pd.DataFrame,
    feature_loadings_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    mode: str = "PC1",
    score_col: str | None = None,
    feature_label_map: Mapping[str, str] | None = None,
    station_feature_df: pd.DataFrame | None = None,
    station_feature_col: str | None = None,
    station_feature_fit_method: FitMethod = "linear",
    station_feature_lowess_frac: float = 0.65,
    station_col: str = "station",
    station_feature_title: str | None = None,
    event_df: pd.DataFrame | None = None,
    title: str = "PCA Spatial Mode Summary",
    bounds: tuple[float, float, float, float] | None = None,
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot PCA station scores, explained variance, and an interpretation panel."""

    score_name = score_col or f"{mode}_score"
    fig = plt.figure(figsize=(16.0, 5.9), dpi=180, constrained_layout=False)
    grid = fig.add_gridspec(1, 3, left=0.055, right=0.975, bottom=0.27, top=0.82, wspace=0.22, width_ratios=[1.18, 1.0, 1.12])
    axes = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1]), fig.add_subplot(grid[0, 2])]
    colorbar_ax = axes[0].inset_axes([0.15, -0.31, 0.70, 0.055], transform=axes[0].transAxes)
    table_ax = axes[0].inset_axes([0.0, -0.70, 1.0, 0.18], transform=axes[0].transAxes)
    colorbar_ax.set_axis_off()
    table_ax.set_axis_off()
    _draw_pca_map_axis(
        axes[0],
        station_scores_df,
        score_name=score_name,
        mode=mode,
        bounds=bounds,
        add_basemap=add_basemap,
        basemap_source=basemap_source,
        basemap_kwargs=basemap_kwargs,
        fig=fig,
        cbar_ax=colorbar_ax,
        event_df=event_df,
        feature_label_map=feature_label_map,
    )
    axes[0].set_anchor("N")
    _draw_explained_variance_axis(axes[1], explained_variance_df)
    if station_feature_col:
        _draw_station_feature_axis(
            axes[2],
            station_scores_df,
            station_feature_df,
            score_name=score_name,
            feature_col=station_feature_col,
            station_col=station_col,
            title=station_feature_title or f"{mode} station score vs {display_label(station_feature_col)}",
            stats_ax=table_ax,
            fit_method=station_feature_fit_method,
            lowess_frac=station_feature_lowess_frac,
        )
    else:
        table_ax.set_visible(False)
        _draw_feature_loading_axis(axes[2], feature_loadings_df, mode=mode, feature_label_map=feature_label_map)
    context = figure_context_text(station_scores_df, value_col=score_name, max_values=3, include_counts=False, include_value=False)
    fig.suptitle(f"{title}\n{context}" if context else title)
    return finish_figure(fig, output_path, outpath=outpath, output_key="pca_summary", showfig=showfig, savefig=savefig)


def _draw_pca_map_axis(
    ax: plt.Axes,
    station_scores_df: pd.DataFrame,
    *,
    score_name: str,
    mode: str,
    bounds: tuple[float, float, float, float] | None,
    add_basemap: bool,
    basemap_source: str,
    basemap_kwargs: dict[str, Any] | None,
    fig: plt.Figure,
    cbar_ax: plt.Axes,
    event_df: pd.DataFrame | None,
    feature_label_map: Mapping[str, str] | None,
) -> None:
    """Draw one PCA spatial mode on an existing map axis."""

    if station_scores_df.empty or score_name not in station_scores_df.columns:
        ax.text(0.5, 0.5, f"No station scores for {mode}", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        cbar_ax.set_axis_off()
        return
    lon_col, lat_col = _xy_columns(station_scores_df)
    plot_df = station_scores_df.dropna(subset=[lon_col, lat_col, score_name]).copy()
    if plot_df.empty:
        ax.text(0.5, 0.5, f"No finite station scores for {mode}", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        cbar_ax.set_axis_off()
        return
    _set_bounds(ax, plot_df, lon_col, lat_col, bounds)
    _finish_map(ax, add_basemap=add_basemap, basemap_source=basemap_source, basemap_kwargs=basemap_kwargs)
    ax.set_anchor("N")
    values = pd.to_numeric(plot_df[score_name], errors="coerce").to_numpy(dtype=float)
    vmax = max(float(np.nanmax(np.abs(values))) if np.isfinite(values).any() else 0.0, 1.0e-6)
    scatter = ax.scatter(plot_df[lon_col], plot_df[lat_col], c=values, cmap="coolwarm", vmin=-vmax, vmax=vmax, s=44, edgecolors="black", linewidths=0.35, zorder=3)
    cbar_ax.set_axis_on()
    fig.colorbar(scatter, cax=cbar_ax, orientation="horizontal", label=display_label(f"{mode} station score"))
    ax.set_anchor("N")
    if event_df is not None and not event_df.empty:
        event_lon, event_lat = _event_xy_columns(event_df)
        label_map = dict(feature_label_map or {})
        ax.scatter(event_df[event_lon], event_df[event_lat], s=58, marker="*", facecolor="#f58518", edgecolor="black", linewidth=0.45, zorder=5, label="Events")
        for row in event_df.itertuples(index=False):
            raw_id = str(getattr(row, "event_id", getattr(row, "event_title", "")))
            label = label_map.get(raw_id, raw_id)
            ax.annotate(label.replace("Event ", ""), (getattr(row, event_lon), getattr(row, event_lat)), xytext=(4, 4), textcoords="offset points", fontsize=8, weight="bold", zorder=6)
        ax.legend(loc="lower left", frameon=True, fontsize=8)
    ax.set_title(f"{mode} station scores")


def _event_xy_columns(df: pd.DataFrame) -> tuple[str, str]:
    """Resolve event longitude/latitude columns from common schemas."""

    lon_name = next((name for name in ("event_lon", "event_longitude", "source_lon", "lon", "longitude") if name in df.columns), None)
    lat_name = next((name for name in ("event_lat", "event_latitude", "source_lat", "lat", "latitude") if name in df.columns), None)
    if lon_name is None or lat_name is None:
        raise KeyError("Could not resolve event longitude/latitude columns.")
    return lon_name, lat_name


def _draw_explained_variance_axis(ax: plt.Axes, explained_variance_df: pd.DataFrame) -> None:
    """Draw PCA explained variance on an existing axis."""

    if explained_variance_df.empty:
        ax.text(0.5, 0.5, "No PCA modes", ha="center", va="center", transform=ax.transAxes)
        return
    plot_df = explained_variance_df.sort_values("mode_index").copy()
    x = np.arange(len(plot_df))
    ratios = pd.to_numeric(plot_df["explained_variance_ratio"], errors="coerce").to_numpy(dtype=float)
    cumulative = pd.to_numeric(plot_df["cumulative_explained_variance_ratio"], errors="coerce").to_numpy(dtype=float)
    labels = plot_df["mode"].astype(str).tolist()
    ax.bar(x, ratios, color="#4c78a8", alpha=0.9, label="mode")
    ax.plot(x, cumulative, color="#f58518", marker="o", linewidth=1.4, label="cumulative")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0.0, min(1.05, max(1.0, float(np.nanmax(cumulative)) + 0.05)))
    ax.set_ylabel("Explained variance ratio")
    ax.set_title("Explained variance")
    ax.legend(frameon=True, fontsize=8)
    ax.grid(True, axis="y", alpha=0.25)


def _draw_feature_loading_axis(
    ax: plt.Axes,
    feature_loadings_df: pd.DataFrame,
    *,
    mode: str,
    feature_label_map: Mapping[str, str] | None,
    top_n: int = 10,
) -> None:
    """Draw strongest PCA feature loadings on an existing axis."""

    subset = feature_loadings_df.loc[feature_loadings_df.get("mode", "").astype(str) == str(mode)].copy()
    if subset.empty:
        ax.text(0.5, 0.5, f"No loadings for {mode}", ha="center", va="center", transform=ax.transAxes)
        return
    subset = subset.sort_values("absolute_loading", ascending=False).head(int(top_n)).copy()
    subset = subset.sort_values("loading", ascending=True)
    colors = np.where(pd.to_numeric(subset["loading"], errors="coerce") >= 0.0, "#d55e00", "#0072b2")
    y = np.arange(len(subset))
    labels = [dict(feature_label_map or {}).get(str(value), display_label(value)) for value in subset["feature"]]
    ax.barh(y, subset["loading"].to_numpy(dtype=float), color=colors, alpha=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.axvline(0.0, color="black", linewidth=0.8)
    ax.set_xlabel("PCA loading")
    ax.set_title(f"{mode} event residual loadings")
    ax.grid(True, axis="x", alpha=0.25)


def _draw_station_feature_axis(
    ax: plt.Axes,
    station_scores_df: pd.DataFrame,
    station_feature_df: pd.DataFrame | None,
    *,
    score_name: str,
    feature_col: str,
    station_col: str,
    title: str,
    stats_ax: plt.Axes | None = None,
    fit_method: FitMethod = "linear",
    lowess_frac: float = 0.65,
) -> None:
    """Draw PCA station scores against a station-level feature."""

    if station_scores_df.empty or score_name not in station_scores_df.columns:
        ax.text(0.5, 0.5, "No PCA station scores", ha="center", va="center", transform=ax.transAxes)
        return
    work = station_scores_df.copy()
    if feature_col not in work.columns:
        if station_feature_df is None or station_col not in work.columns or station_col not in station_feature_df.columns or feature_col not in station_feature_df.columns:
            ax.text(0.5, 0.5, f"No {display_label(feature_col)} values", ha="center", va="center", transform=ax.transAxes)
            return
        metadata = station_feature_df[[station_col, feature_col]].drop_duplicates(subset=[station_col])
        work = work.merge(metadata, on=station_col, how="left")
    x = pd.to_numeric(work[feature_col], errors="coerce")
    y = pd.to_numeric(work[score_name], errors="coerce")
    finite = x.notna() & y.notna()
    if not finite.any():
        ax.text(0.5, 0.5, f"No finite {display_label(feature_col)} values", ha="center", va="center", transform=ax.transAxes)
        return
    ax.scatter(x[finite], y[finite], s=42, color="#4c78a8", edgecolors="black", linewidths=0.35, alpha=0.88)
    draw_scatter_fit(ax, x[finite].to_numpy(dtype=float), y[finite].to_numpy(dtype=float), fit_method=fit_method, lowess_frac=lowess_frac, color="0.20", label=None, linewidth=1.0, alpha=0.78)
    ax.margins(x=0.10, y=0.10)
    if station_col in work.columns:
        for _, row in work.loc[finite, [station_col, feature_col, score_name]].iterrows():
            ax.annotate(str(row[station_col]), (float(row[feature_col]), float(row[score_name])), xytext=(4, 3), textcoords="offset points", fontsize=7)
    ax.axhline(0.0, color="black", linewidth=0.8, linestyle=":")
    ax.set_xlabel(_station_feature_label(feature_col))
    ax.set_ylabel(display_label(score_name))
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    if stats_ax is not None:
        _draw_station_feature_stats_table(stats_ax, x[finite], y[finite], feature_col=feature_col, score_name=score_name)


def _draw_station_feature_stats_table(
    ax: plt.Axes,
    x: pd.Series,
    y: pd.Series,
    *,
    feature_col: str,
    score_name: str,
) -> None:
    """Draw station-feature association statistics in a dedicated table axis.

    Inputs are finite station-feature values and PCA scores. The output is a
    compact table with effect size and significance diagnostics.
    """

    ax.set_axis_off()
    if len(x) < 3:
        return
    result = stats.linregress(x.to_numpy(dtype=float), y.to_numpy(dtype=float))
    r_squared = float(result.rvalue**2)
    slope_per_100 = float(result.slope * 100.0)
    table = ax.table(
        cellText=[
            [f"{result.rvalue:.2f}", f"{r_squared:.2f}", f"{slope_per_100:.2f}", _p_value_label(float(result.pvalue)), "yes" if float(result.pvalue) < 0.05 else "no", str(int(len(x)))]
        ],
        colLabels=["r", "R^2", "Slope/100", "p", "p<0.05", "n"],
        cellLoc="left",
        colLoc="left",
        colWidths=[0.14, 0.14, 0.22, 0.16, 0.17, 0.17],
        loc="center",
        bbox=[0.0, 0.12, 1.0, 0.72],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7.0)
    for (row_index, _col_index), cell in table.get_celld().items():
        cell.set_edgecolor("0.82")
        if row_index == 0:
            cell.set_facecolor("0.94")
            cell.set_text_props(weight="bold")
        else:
            cell.set_facecolor("white")


def _p_value_label(value: float) -> str:
    """Return a compact p-value label for figure summary tables."""

    if not np.isfinite(value):
        return "n/a"
    if value < 0.001:
        return "<0.001"
    return f"{value:.3f}"


def _station_feature_label(feature_col: str) -> str:
    """Return a readable axis label for a station feature."""

    if str(feature_col).lower() == "vs30":
        return "Vs30 (m/s)"
    return display_label(feature_col)


def _set_geographic_aspect(ax: plt.Axes) -> None:
    """Preserve lon/lat proportions on map axes."""

    lat_min, lat_max = ax.get_ylim()
    lat_mid = 0.5 * (float(lat_min) + float(lat_max))
    cos_lat = math.cos(math.radians(lat_mid))
    if math.isfinite(cos_lat) and abs(cos_lat) > 1.0e-6:
        ax.set_aspect(1.0 / cos_lat, adjustable="box")
