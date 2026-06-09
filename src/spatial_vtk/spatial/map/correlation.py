"""Map wrappers for station bias, clustering, and holdout results.

Purpose
-------
This module draws map figures from public spatial-statistics tables. Basemaps
are enabled by default through the package's contextily helper, but callers can
disable them for tests or fully offline rendering.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import math

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.ticker import MaxNLocator
from mpl_toolkits.axes_grid1 import make_axes_locatable

from spatial_vtk.config.labels import display_label, model_display_name, value_column_display_name
from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
from spatial_vtk.visualize.figure_context import add_below_axes_table, apply_figure_context, figure_context_text, value_color_settings
from spatial_vtk.visualize.figure_io import finish_figure
from spatial_vtk.visualize.selection import FigureSpatialSelection, apply_figure_spatial_selection


def _xy_columns(df: pd.DataFrame, *, lon_col: str | None = None, lat_col: str | None = None) -> tuple[str, str]:
    """Resolve longitude and latitude columns from common table schemas."""

    lon_candidates = [lon_col, "lon", "station_longitude", "longitude"]
    lat_candidates = [lat_col, "lat", "station_latitude", "latitude"]
    lon_name = next((name for name in lon_candidates if name and name in df.columns), None)
    lat_name = next((name for name in lat_candidates if name and name in df.columns), None)
    if lon_name is None or lat_name is None:
        raise KeyError("Could not resolve longitude/latitude columns.")
    return lon_name, lat_name


def _event_xy_columns(df: pd.DataFrame) -> tuple[str, str]:
    """Resolve event longitude and latitude columns from common schemas."""

    lon_name = next((name for name in ("event_lon", "event_longitude", "source_lon", "lon", "longitude") if name in df.columns), None)
    lat_name = next((name for name in ("event_lat", "event_latitude", "source_lat", "lat", "latitude") if name in df.columns), None)
    if lon_name is None or lat_name is None:
        raise KeyError("Could not resolve event longitude/latitude columns.")
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


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    """Raise a clear error when required columns are missing."""

    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")


def _cluster_scatter(
    ax: plt.Axes,
    df: pd.DataFrame,
    lon_col: str,
    lat_col: str,
    labels: np.ndarray,
    *,
    marker_size: float = 42,
) -> tuple[Any, list[int]]:
    """Draw categorical cluster markers with one color for each cluster id."""

    unique_labels = sorted(int(value) for value in np.unique(labels) if np.isfinite(value))
    if not unique_labels:
        unique_labels = [-1]
    label_to_index = {label: index for index, label in enumerate(unique_labels)}
    mapped = np.asarray([label_to_index.get(int(value), -1) for value in labels], dtype=int)
    base = plt.get_cmap("tab20")
    colors = [base(index % base.N) for index in range(len(unique_labels))]
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(np.arange(len(unique_labels) + 1) - 0.5, cmap.N)
    scatter = ax.scatter(
        df[lon_col],
        df[lat_col],
        c=mapped,
        cmap=cmap,
        norm=norm,
        s=marker_size,
        edgecolors="black",
        linewidths=0.35,
        zorder=3,
    )
    return scatter, unique_labels


def plot_station_bias_map(
    station_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "Station Bias",
    value_col: str = "mean_centered",
    value_label: str | None = None,
    bounds: tuple[float, float, float, float] | None = None,
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Plot station bias values on a lon/lat map.

    Inputs are a station-level summary table with coordinates and a numeric
    bias column. The output is a Matplotlib figure with an optional basemap and
    a colorbar whose label can be overridden when the summarized field needs a
    more specific description than the column name provides.
    """

    plot_df, subset_label = apply_figure_spatial_selection(station_df, spatial_selection, **spatial_kwargs)
    fig, ax = plt.subplots(figsize=(10.5, 5.8), dpi=180, constrained_layout=False)
    fig.subplots_adjust(left=0.07, right=0.72, bottom=0.13, top=0.88)
    if plot_df.empty:
        ax.text(0.5, 0.5, "No station bias estimates", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
    else:
        lon_col, lat_col = _xy_columns(plot_df)
        _require_columns(plot_df, [value_col])
        _set_bounds(ax, plot_df, lon_col, lat_col, bounds)
        _finish_map(ax, add_basemap=add_basemap, basemap_source=basemap_source, basemap_kwargs=basemap_kwargs)
        values = pd.to_numeric(plot_df[value_col], errors="coerce").to_numpy(dtype=float)
        cmap, vmin, vmax = value_color_settings(values, value_col, plot_df)
        sizes = 34
        if "n_events" in plot_df.columns:
            sizes = 18 + 8 * np.sqrt(pd.to_numeric(plot_df["n_events"], errors="coerce").fillna(1).clip(lower=1))
        scatter = ax.scatter(plot_df[lon_col], plot_df[lat_col], c=values, cmap=cmap, vmin=vmin, vmax=vmax, s=sizes, edgecolors="black", linewidths=0.35, zorder=3)
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="3.5%", pad=0.12)
        fig.colorbar(scatter, cax=cax, label=value_label or value_column_display_name(value_col))
    apply_figure_context(ax, plot_df, value_col=value_col, title=title, max_values=3, include_counts=False, include_value=False, max_line_chars=72, extra=[subset_label] if subset_label else None)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_cluster_map(
    assignments_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "Residual Clusters",
    cluster_col: str = "cluster_id",
    bounds: tuple[float, float, float, float] | None = None,
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Plot station cluster assignments on a lon/lat map."""

    plot_df, subset_label = apply_figure_spatial_selection(assignments_df, spatial_selection, **spatial_kwargs)
    fig, ax = plt.subplots(figsize=(8.0, 7.0), dpi=180, constrained_layout=True)
    if plot_df.empty:
        ax.text(0.5, 0.5, "No cluster assignments", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
    else:
        lon_col, lat_col = _xy_columns(plot_df)
        _require_columns(plot_df, [cluster_col])
        _set_bounds(ax, plot_df, lon_col, lat_col, bounds)
        _finish_map(ax, add_basemap=add_basemap, basemap_source=basemap_source, basemap_kwargs=basemap_kwargs)
        labels = pd.to_numeric(plot_df[cluster_col], errors="coerce").fillna(-1).to_numpy(dtype=int)
        scatter, unique_labels = _cluster_scatter(ax, plot_df, lon_col, lat_col, labels, marker_size=42)
        colorbar = fig.colorbar(scatter, ax=ax, pad=0.045, ticks=np.arange(len(unique_labels)), label=display_label(cluster_col))
        colorbar.ax.set_yticklabels([str(label) for label in unique_labels])
    apply_figure_context(ax, plot_df, value_col=cluster_col, title=title, max_values=3, include_counts=False, include_value=False, max_line_chars=72, extra=[subset_label] if subset_label else None)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_redcap_cluster_map(
    redcap_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "REDCAP Clusters",
    value_col: str = "avg_observed_metric_distance_scaled_event_demeaned",
    bounds: tuple[float, float, float, float] | None = None,
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Plot station values beside REDCAP cluster assignments."""

    plot_df, subset_label = apply_figure_spatial_selection(redcap_df, spatial_selection, **spatial_kwargs)
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.2), dpi=180, constrained_layout=False)
    fig.subplots_adjust(left=0.055, right=0.965, bottom=0.14, top=0.78, wspace=0.34)
    if plot_df.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "No REDCAP assignments", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
    else:
        lon_col, lat_col = _xy_columns(plot_df)
        _require_columns(plot_df, [value_col, "cluster"])
        values = pd.to_numeric(plot_df[value_col], errors="coerce").to_numpy(dtype=float)
        cmap, vmin, vmax = value_color_settings(values, value_col, plot_df)
        for ax in axes:
            _set_bounds(ax, plot_df, lon_col, lat_col, bounds)
            _finish_map(ax, add_basemap=add_basemap, basemap_source=basemap_source, basemap_kwargs=basemap_kwargs)
            ax.set_anchor("N")
        value_scatter = axes[0].scatter(plot_df[lon_col], plot_df[lat_col], c=values, cmap=cmap, vmin=vmin, vmax=vmax, s=42, edgecolors="black", linewidths=0.35, zorder=3)
        redcap_value_label = _redcap_value_display_name(value_col)
        axes[0].set_title(redcap_value_label, fontsize=11, pad=7)
        value_cax = make_axes_locatable(axes[0]).append_axes("right", size="3%", pad=0.10)
        fig.colorbar(value_scatter, cax=value_cax, label=redcap_value_label)
        labels = pd.to_numeric(plot_df["cluster"], errors="coerce").fillna(-1).to_numpy(dtype=int)
        cluster_scatter, unique_labels = _cluster_scatter(axes[1], plot_df, lon_col, lat_col, labels, marker_size=42)
        k_text = ""
        if "selected_k" in plot_df.columns and plot_df["selected_k"].notna().any():
            k_text = f", k={int(plot_df['selected_k'].dropna().iloc[0])}"
        axes[1].set_title(f"REDCAP clusters{k_text}", fontsize=11, pad=7)
        cluster_cax = make_axes_locatable(axes[1]).append_axes("right", size="3%", pad=0.10)
        colorbar = fig.colorbar(cluster_scatter, cax=cluster_cax, ticks=np.arange(len(unique_labels)), label="Cluster")
        colorbar.ax.set_yticklabels([str(label) for label in unique_labels])
    context = figure_context_text(plot_df, value_col=value_col, max_values=3, include_counts=False, include_value=False, extra=[subset_label] if subset_label else None)
    fig.text(0.5, 0.975, title, ha="center", va="top", fontsize=13)
    if context:
        fig.text(0.5, 0.915, context, ha="center", va="top", fontsize=10.5)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _redcap_value_display_name(value_col: str) -> str:
    """Return compact display text for REDCAP map value columns."""

    if str(value_col) == "avg_observed_metric_distance_scaled_event_demeaned":
        return "Distance-scaled event-demeaned metric"
    return value_column_display_name(value_col)


def plot_block_holdout_error_map(
    prediction_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "Spatial Block Holdout Error",
    bounds: tuple[float, float, float, float] | None = None,
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Plot held-out station prediction errors on a lon/lat map."""

    plot_df, subset_label = apply_figure_spatial_selection(prediction_df, spatial_selection, **spatial_kwargs)
    fig, ax = plt.subplots(figsize=(8.0, 7.0), dpi=180, constrained_layout=True)
    if plot_df.empty:
        ax.text(0.5, 0.5, "No block holdout predictions", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
    else:
        lon_col, lat_col = _xy_columns(plot_df)
        _require_columns(plot_df, ["prediction_error"])
        _set_bounds(ax, plot_df, lon_col, lat_col, bounds)
        _finish_map(ax, add_basemap=add_basemap, basemap_source=basemap_source, basemap_kwargs=basemap_kwargs)
        values = pd.to_numeric(plot_df["prediction_error"], errors="coerce").to_numpy(dtype=float)
        cmap, vmin, vmax = value_color_settings(values, "heldout_bias_error", plot_df)
        scatter = ax.scatter(plot_df[lon_col], plot_df[lat_col], c=values, cmap=cmap, vmin=vmin, vmax=vmax, s=46, edgecolors="black", linewidths=0.35, zorder=3)
        fig.colorbar(scatter, ax=ax, pad=0.045, label=value_column_display_name("heldout_bias_error"))
    apply_figure_context(ax, plot_df, value_col="heldout_bias_error", title=title, max_values=3, include_counts=False, include_value=False, max_line_chars=72, extra=[subset_label] if subset_label else None)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_block_holdout_summary(
    prediction_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "Spatial Block Holdout Summary",
    bounds: tuple[float, float, float, float] | None = None,
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Plot held-out station-bias errors and observed/predicted agreement."""

    plot_df, subset_label = apply_figure_spatial_selection(prediction_df, spatial_selection, **spatial_kwargs)
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(14.2, 6.4),
        dpi=180,
        constrained_layout=True,
        gridspec_kw={"width_ratios": [2.0, 1.0], "wspace": 0.24},
    )
    map_ax, scatter_ax = axes
    if plot_df.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "No block holdout predictions", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
    else:
        lon_col, lat_col = _xy_columns(plot_df)
        _require_columns(plot_df, ["prediction_error", "observed_mean_centered", "predicted_mean_centered"])
        _set_bounds(map_ax, plot_df, lon_col, lat_col, bounds)
        _finish_map(map_ax, add_basemap=add_basemap, basemap_source=basemap_source, basemap_kwargs=basemap_kwargs)
        errors = pd.to_numeric(plot_df["prediction_error"], errors="coerce").to_numpy(dtype=float)
        cmap, vmin, vmax = value_color_settings(errors, "heldout_bias_error", plot_df)
        mapped = map_ax.scatter(plot_df[lon_col], plot_df[lat_col], c=errors, cmap=cmap, vmin=vmin, vmax=vmax, s=46, edgecolors="black", linewidths=0.35, zorder=3)
        map_ax.set_title("Held-out station-bias error map")
        fig.colorbar(mapped, ax=map_ax, shrink=0.86, pad=0.08, orientation="horizontal", label=value_column_display_name("heldout_bias_error"))
        _draw_holdout_scatter(scatter_ax, plot_df)
    context = figure_context_text(plot_df, value_col="heldout_bias_error", max_values=3, include_counts=False, include_value=False, extra=[subset_label] if subset_label else None)
    fig.suptitle(f"{title}\n{context}" if context else title)
    return finish_figure(fig, output_path, outpath=outpath, output_key="block_holdout_summary", showfig=showfig, savefig=savefig)


def plot_cluster_summary(
    assignments_df: pd.DataFrame,
    score_df: pd.DataFrame,
    feature_summary_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "Residual Cluster Summary",
    cluster_col: str = "cluster_id",
    k_column: str = "n_clusters",
    score_column: str = "silhouette",
    feature_label_map: dict[str, str] | None = None,
    event_df: pd.DataFrame | None = None,
    clustered_value_label: str | None = None,
    bounds: tuple[float, float, float, float] | None = None,
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Plot station cluster assignments and silhouette scores together."""

    plot_assignments, subset_label = apply_figure_spatial_selection(assignments_df, spatial_selection, **spatial_kwargs)
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.8), dpi=180, constrained_layout=True, gridspec_kw={"width_ratios": [1.15, 1.0]})
    _draw_cluster_map_axis(axes[0], plot_assignments, cluster_col=cluster_col, bounds=bounds, add_basemap=add_basemap, basemap_source=basemap_source, basemap_kwargs=basemap_kwargs, fig=fig, event_df=None, feature_label_map=feature_label_map)
    _draw_cluster_score_axis(axes[1], score_df, k_column=k_column, score_column=score_column)
    context_parts = []
    if clustered_value_label:
        context_parts.append(f"Clustered value: {clustered_value_label}")
    context = figure_context_text(plot_assignments, value_col=cluster_col, max_values=3, include_counts=False, include_value=False, extra=[subset_label] if subset_label else None)
    if context:
        context_parts.append(context)
    subtitle = " | ".join(context_parts)
    fig.suptitle(f"{title}\n{subtitle}" if subtitle else title)
    return finish_figure(fig, output_path, outpath=outpath, output_key="cluster_summary", showfig=showfig, savefig=savefig)


def _draw_holdout_scatter(ax: plt.Axes, prediction_df: pd.DataFrame) -> None:
    """Draw observed versus predicted held-out station bias on an axis."""

    observed = pd.to_numeric(prediction_df["observed_mean_centered"], errors="coerce").to_numpy(dtype=float)
    predicted = pd.to_numeric(prediction_df["predicted_mean_centered"], errors="coerce").to_numpy(dtype=float)
    finite = np.isfinite(observed) & np.isfinite(predicted)
    if not np.any(finite):
        ax.text(0.5, 0.5, "No finite holdout predictions", ha="center", va="center", transform=ax.transAxes)
        return
    observed = observed[finite]
    predicted = predicted[finite]
    ax.scatter(observed, predicted, s=32, alpha=0.85)
    low = float(np.nanmin(np.concatenate([observed, predicted])))
    high = float(np.nanmax(np.concatenate([observed, predicted])))
    pad = 0.05 * max(high - low, 1.0)
    ax.plot([low - pad, high + pad], [low - pad, high + pad], linestyle="--", linewidth=1.0)
    ax.set_xlim(low - pad, high + pad)
    ax.set_ylim(low - pad, high + pad)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Observed station bias")
    ax.set_ylabel("Predicted station bias")
    ax.set_title("Observed vs predicted held-out bias")
    ax.xaxis.set_major_locator(MaxNLocator(5))
    ax.yaxis.set_major_locator(MaxNLocator(5))
    rmse = float(np.sqrt(np.nanmean((predicted - observed) ** 2)))
    add_below_axes_table(
        ax,
        rows=[["Held-out station bias", f"{rmse:.3f}", f"{int(len(observed))}"]],
        columns=["Prediction target", "RMSE", "Stations"],
        col_widths=[0.55, 0.20, 0.25],
    )
    ax.grid(True, alpha=0.25)


def _draw_cluster_map_axis(
    ax: plt.Axes,
    assignments_df: pd.DataFrame,
    *,
    cluster_col: str,
    bounds: tuple[float, float, float, float] | None,
    add_basemap: bool,
    basemap_source: str,
    basemap_kwargs: dict[str, Any] | None,
    fig: plt.Figure,
    event_df: pd.DataFrame | None,
    feature_label_map: dict[str, str] | None,
) -> None:
    """Draw cluster assignments on an existing map axis."""

    if assignments_df.empty:
        ax.text(0.5, 0.5, "No cluster assignments", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return
    lon_col, lat_col = _xy_columns(assignments_df)
    labels = pd.to_numeric(assignments_df[cluster_col], errors="coerce").fillna(-1).to_numpy(dtype=int)
    _set_bounds(ax, assignments_df, lon_col, lat_col, bounds)
    _finish_map(ax, add_basemap=add_basemap, basemap_source=basemap_source, basemap_kwargs=basemap_kwargs)
    scatter, unique_labels = _cluster_scatter(ax, assignments_df, lon_col, lat_col, labels, marker_size=42)
    colorbar = fig.colorbar(scatter, ax=ax, pad=0.02, ticks=np.arange(len(unique_labels)), label="Cluster")
    colorbar.ax.set_yticklabels([str(label) for label in unique_labels])
    if event_df is not None and not event_df.empty:
        event_lon, event_lat = _event_xy_columns(event_df)
        label_map = dict(feature_label_map or {})
        ax.scatter(event_df[event_lon], event_df[event_lat], s=58, marker="*", facecolor="#f58518", edgecolor="black", linewidth=0.45, zorder=5, label="Events")
        for row in event_df.itertuples(index=False):
            raw_id = str(getattr(row, "event_id", getattr(row, "event_title", "")))
            label = label_map.get(raw_id, raw_id)
            ax.annotate(label.replace("Event ", ""), (getattr(row, event_lon), getattr(row, event_lat)), xytext=(4, 4), textcoords="offset points", fontsize=8, weight="bold", color="black", zorder=6)
        ax.legend(loc="lower left", frameon=True, fontsize=8)
    ax.set_title("Station clusters")


def _draw_cluster_feature_axis(ax: plt.Axes, feature_summary_df: pd.DataFrame, *, value_column: str, feature_label_map: dict[str, str] | None) -> None:
    """Draw a cluster-feature heatmap on an existing axis."""

    if feature_summary_df.empty:
        ax.text(0.5, 0.5, "No cluster feature summary", ha="center", va="center", transform=ax.transAxes)
        return
    pivot = feature_summary_df.pivot(index="cluster_name", columns="feature", values=value_column).sort_index()
    values = pivot.to_numpy(dtype=float)
    cmap, vmin, vmax = value_color_settings(values, value_column, feature_summary_df)
    image = ax.imshow(values, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    label_map = dict(feature_label_map or {})
    ax.set_xticks(np.arange(pivot.shape[1]))
    ax.set_xticklabels([label_map.get(str(token), display_label(token)) for token in pivot.columns], rotation=45, ha="right")
    ax.set_yticks(np.arange(pivot.shape[0]))
    ax.set_yticklabels([display_label(token) for token in pivot.index])
    ax.set_title("Cluster feature means")
    ax.figure.colorbar(image, ax=ax, pad=0.02, label=value_column_display_name(value_column))


def _draw_cluster_score_axis(ax: plt.Axes, score_df: pd.DataFrame, *, k_column: str, score_column: str) -> None:
    """Draw silhouette scores on an existing axis."""

    if score_df.empty:
        ax.text(0.5, 0.5, "No clustering solutions", ha="center", va="center", transform=ax.transAxes)
        return
    plot_df = score_df.sort_values(k_column).copy()
    ax.plot(plot_df[k_column], plot_df[score_column], marker="o", linewidth=1.2)
    ax.set_xticks([int(value) for value in pd.to_numeric(plot_df[k_column], errors="coerce").dropna().unique()])
    ax.set_xlabel("Cluster count")
    ax.set_ylabel("Silhouette score (unitless)")
    ax.set_title("Cluster solution score")
    ax.grid(True, alpha=0.25)


def _set_geographic_aspect(ax: plt.Axes) -> None:
    """Preserve lon/lat proportions on map axes."""

    lat_min, lat_max = ax.get_ylim()
    lat_mid = 0.5 * (float(lat_min) + float(lat_max))
    cos_lat = math.cos(math.radians(lat_mid))
    if math.isfinite(cos_lat) and abs(cos_lat) > 1.0e-6:
        ax.set_aspect(1.0 / cos_lat, adjustable="box")
