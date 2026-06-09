"""QC and retention figure helpers.

Purpose
-------
This module draws public, dataframe-driven QC review figures without depending
on private runtime profiles or production output layouts.

Usage examples
--------------
Plot retention counts:
  ``fig = plot_retention_summary(qc_summary)``
  ``plot_retention_summary(qc_summary, savefig=True, outpath="retention.png")``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from spatial_vtk.config.labels import display_label
from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
from spatial_vtk.visualize.figure_io import finish_figure


def plot_retention_summary(
    qc_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    group_col: str = "stage",
    status_col: str = "qc_status",
    count_col: str | None = None,
    title: str = "QC Retention Summary",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot pass/fail retention counts by workflow stage.

    Parameters
    ----------
    qc_df
        QC summary table.
    output_path, outpath
        Optional destination figure path. ``outpath`` is preferred for new code.
    group_col
        Stage or grouping column.
    status_col
        QC status column.
    count_col
        Optional precomputed count column.
    title
        Figure title.

    Returns
    -------
    matplotlib.figure.Figure
        Created figure.
    """

    if {"retention_percent", "retained_pairs", "total_pairs"} <= set(qc_df.columns):
        return _plot_pair_retention_summary(
            qc_df,
            output_path,
            title=title,
            showfig=showfig,
            savefig=savefig,
            outpath=outpath,
        )
    _require_columns(qc_df, [group_col, status_col])
    if count_col and count_col in qc_df.columns:
        counts = qc_df.groupby([group_col, status_col], dropna=False)[count_col].sum().reset_index(name="count")
    else:
        counts = qc_df.groupby([group_col, status_col], dropna=False).size().reset_index(name="count")
    pivot = counts.pivot_table(index=group_col, columns=status_col, values="count", fill_value=0, aggfunc="sum")
    fig, ax = plt.subplots(figsize=(8.5, 4.8), dpi=180)
    pivot.plot(kind="bar", stacked=True, ax=ax, color=_status_colors(pivot.columns))
    ax.set_title(title)
    ax.set_xlabel(group_col.replace("_", " ").title())
    ax.set_ylabel("Record count")
    ax.tick_params(axis="x", rotation=35)
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(title="Status", frameon=True)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _plot_pair_retention_summary(
    retention_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str,
    showfig: bool | None,
    savefig: bool | None,
    outpath: str | Path | None,
) -> plt.Figure:
    """Plot retained observed/synthetic pairs as percentages by metric.

    Parameters
    ----------
    retention_df
        Pair-retention table with metric, passband, retained count, total
        count, and retention percentage.
    output_path, outpath
        Optional destination figure path.
    title
        Figure title.
    showfig, savefig
        Standard display/save flags.

    Returns
    -------
    matplotlib.figure.Figure
        Created figure.
    """

    df = retention_df.copy()
    if "metric" not in df.columns:
        df["metric"] = "All metrics"
    if "passband" not in df.columns:
        df["passband"] = "All passbands"
    df["retention_percent"] = pd.to_numeric(df["retention_percent"], errors="coerce")
    df["retained_pairs"] = pd.to_numeric(df["retained_pairs"], errors="coerce").fillna(0).astype(int)
    df["total_pairs"] = pd.to_numeric(df["total_pairs"], errors="coerce").fillna(0).astype(int)
    metrics = df["metric"].drop_duplicates().astype(str).tolist()
    passbands = df["passband"].drop_duplicates().astype(str).tolist()
    n_metrics = max(len(metrics), 1)
    n_bands = max(len(passbands), 1)
    fig_width = max(8.5, 1.0 * n_metrics + 1.15 * n_bands + 2.5)
    fig, ax = plt.subplots(figsize=(fig_width, 5.2), dpi=180)
    x = np.arange(n_metrics, dtype=float)
    group_width = min(0.88, max(0.70, 0.16 * n_bands + 0.48))
    bar_width = group_width / n_bands
    colors = plt.get_cmap("tab10")(np.linspace(0.0, 1.0, n_bands))
    for band_index, passband in enumerate(passbands):
        subset = df.loc[df["passband"].astype(str).eq(passband)].copy()
        subset["_metric_key"] = subset["metric"].astype(str)
        subset = subset.set_index("_metric_key")
        heights = []
        labels = []
        for metric in metrics:
            if metric in subset.index:
                row = subset.loc[metric]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[0]
                height = float(row["retention_percent"])
                label = f"{height:.0f}%\n{int(row['retained_pairs'])}/{int(row['total_pairs'])}"
            else:
                height = np.nan
                label = ""
            heights.append(height)
            labels.append(label)
        offsets = x - group_width / 2.0 + bar_width * (band_index + 0.5)
        bars = ax.bar(offsets, heights, width=bar_width * 0.92, label=passband, color=colors[band_index])
        for bar, label in zip(bars, labels):
            if not label or not np.isfinite(bar.get_height()):
                continue
            ax.text(bar.get_x() + bar.get_width() / 2.0, min(bar.get_height() + 2.0, 98.0), label, ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels([display_label(metric) for metric in metrics], rotation=25, ha="right")
    ax.set_ylim(0.0, 108.0)
    ax.set_ylabel("Retained observed/synthetic pairs (%)")
    ax.set_xlabel("Metric")
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(title="Period band", frameon=True, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_data_synthetic_availability(
    availability_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    event_col: str = "event_id",
    station_col: str = "station",
    observed_col: str = "observed_available",
    synthetic_col: str = "synthetic_available",
    title: str = "Observed and Synthetic Availability",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot observed/synthetic availability as an event-station matrix.

    Parameters
    ----------
    availability_df
        Event-station availability table.
    output_path
        Destination figure path.
    event_col, station_col
        Event and station identifier columns.
    observed_col, synthetic_col
        Boolean availability columns.
    title
        Figure title.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    _require_columns(availability_df, [event_col, station_col, observed_col, synthetic_col])
    df = availability_df.copy()
    df["_availability_code"] = df[observed_col].astype(bool).astype(int) + 2 * df[synthetic_col].astype(bool).astype(int)
    matrix = df.pivot_table(index=station_col, columns=event_col, values="_availability_code", aggfunc="max", fill_value=0)
    fig, ax = plt.subplots(figsize=(max(6.5, 0.38 * matrix.shape[1] + 3.0), max(4.8, 0.24 * matrix.shape[0] + 2.0)), dpi=180)
    image = ax.imshow(matrix.to_numpy(dtype=float), aspect="auto", cmap="viridis", vmin=0, vmax=3)
    ax.set_xticks(np.arange(matrix.shape[1]))
    ax.set_xticklabels(matrix.columns.astype(str), rotation=45, ha="right", fontsize=8)
    ax.set_yticks(np.arange(matrix.shape[0]))
    ax.set_yticklabels(matrix.index.astype(str), fontsize=8)
    ax.set_xlabel("Event")
    ax.set_ylabel("Station")
    ax.set_title(title)
    cbar = fig.colorbar(image, ax=ax, ticks=[0, 1, 2, 3])
    cbar.ax.set_yticklabels(["None", "Observed", "Synthetic", "Both"])
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_event_station_retention_heatmap(
    retention_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    event_col: str = "event_id",
    station_col: str = "station",
    value_col: str = "retention_percent",
    retained_col: str = "retained_pairs",
    total_col: str = "total_pairs",
    title: str = "Event-Station Pair Retention",
    show_counts: bool = True,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot retained comparison percentage for each event-station pair.

    Parameters
    ----------
    retention_df
        Event-station retention table with retained and total comparison-pair
        counts across components, passbands, and metrics.
    output_path, outpath
        Optional destination figure path.
    event_col, station_col
        Event and station identifier columns.
    value_col
        Percentage column used for heatmap color.
    retained_col, total_col
        Count columns used for optional in-cell labels.
    title
        Figure title.
    show_counts
        Whether to label each cell with retained/total pair counts.
    showfig, savefig
        Standard display/save flags.

    Returns
    -------
    matplotlib.figure.Figure
        Created figure.
    """

    _require_columns(retention_df, [event_col, station_col, value_col])
    df = retention_df.copy()
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    matrix = df.pivot_table(index=station_col, columns=event_col, values=value_col, aggfunc="mean", fill_value=np.nan)
    fig, ax = plt.subplots(figsize=(max(6.8, 0.42 * matrix.shape[1] + 3.2), max(4.8, 0.24 * matrix.shape[0] + 2.0)), dpi=180)
    image = ax.imshow(matrix.to_numpy(dtype=float), aspect="auto", cmap="viridis", vmin=0.0, vmax=100.0)
    ax.set_xticks(np.arange(matrix.shape[1]))
    ax.set_xticklabels(matrix.columns.astype(str), rotation=45, ha="right", fontsize=8)
    ax.set_yticks(np.arange(matrix.shape[0]))
    ax.set_yticklabels(matrix.index.astype(str), fontsize=8)
    ax.set_xlabel("Event")
    ax.set_ylabel("Station")
    ax.set_title(title)
    if show_counts and {retained_col, total_col} <= set(df.columns):
        counts = df.pivot_table(
            index=station_col,
            columns=event_col,
            values=[retained_col, total_col],
            aggfunc="sum",
            fill_value=0,
        )
        for row_index, station in enumerate(matrix.index):
            for col_index, event in enumerate(matrix.columns):
                try:
                    retained = int(counts.loc[station, (retained_col, event)])
                    total = int(counts.loc[station, (total_col, event)])
                except Exception:
                    continue
                if total <= 0:
                    continue
                value = float(matrix.loc[station, event])
                text_color = "white" if np.isfinite(value) and value < 55.0 else "black"
                ax.text(col_index, row_index, f"{retained}/{total}", ha="center", va="center", fontsize=5.5, color=text_color)
    cbar = fig.colorbar(image, ax=ax, pad=0.025)
    cbar.set_label("Retained observed/synthetic pairs (%)")
    return finish_figure(
        fig,
        output_path,
        outpath=outpath,
        output_key="data_synthetic_availability",
        showfig=showfig,
        savefig=savefig,
    )


def plot_post_qc_station_event_map(
    records_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    station_lon_col: str = "sta_lon",
    station_lat_col: str = "sta_lat",
    event_lon_col: str = "event_lon",
    event_lat_col: str = "event_lat",
    status_col: str = "qc_status",
    pass_values: tuple[str, ...] = ("pass", "passed", "keep", "kept"),
    title: str = "Post-QC Station and Event Coverage",
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot retained and rejected station-event coverage after QC.

    Parameters
    ----------
    records_df
        Event-station table with station and event coordinates.
    output_path
        Destination figure path.
    station_lon_col, station_lat_col, event_lon_col, event_lat_col
        Coordinate columns.
    status_col
        QC status column.
    pass_values
        Status values treated as retained.
    title
        Figure title.
    add_basemap
        Whether to draw a basemap.
    basemap_source
        Contextily provider selector.
    basemap_kwargs
        Extra basemap keyword arguments.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    _require_columns(records_df, [station_lon_col, station_lat_col, event_lon_col, event_lat_col, status_col])
    df = records_df.copy()
    pass_set = {value.lower() for value in pass_values}
    retained = df[status_col].fillna("").astype(str).str.lower().isin(pass_set)
    fig, ax = plt.subplots(figsize=(8.0, 6.8), dpi=180)
    _set_map_bounds(ax, df, [station_lon_col, event_lon_col], [station_lat_col, event_lat_col])
    if add_basemap:
        add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **dict(basemap_kwargs or {}))
    for is_retained, color, label, alpha in [(False, "#d95f02", "Rejected", 0.55), (True, "#1b9e77", "Retained", 0.9)]:
        subset = df.loc[retained == is_retained]
        if subset.empty:
            continue
        ax.scatter(subset[station_lon_col], subset[station_lat_col], s=28, marker="^", c=color, edgecolors="black", linewidths=0.25, alpha=alpha, label=f"{label} stations", zorder=4)
    events = df.drop_duplicates(subset=[event_lon_col, event_lat_col])
    ax.scatter(events[event_lon_col], events[event_lat_col], s=95, marker="*", c="#ffd23f", edgecolors="black", linewidths=0.4, label="Events", zorder=5)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(title)
    ax.grid(True, alpha=0.18)
    ax.legend(frameon=True, fontsize=8)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_qc_drop_cause_diagnostics(
    qc_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    reason_col: str = "qc_reason",
    status_col: str | None = "qc_status",
    fail_values: tuple[str, ...] = ("fail", "failed", "reject", "rejected"),
    group_col: str | None = None,
    max_reasons: int = 12,
    title: str = "QC Drop Causes",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot the most common QC rejection reasons.

    Parameters
    ----------
    qc_df
        QC table.
    output_path
        Destination figure path.
    reason_col
        Rejection-reason column.
    status_col
        Optional QC status column used to keep only rejected rows before
        counting causes. Set to ``None`` when the input table already contains
        only rejected rows.
    fail_values
        Status labels treated as rejected when ``status_col`` is present.
    group_col
        Optional grouping column, commonly source or component. When omitted,
        the figure summarizes each rejection reason once, which avoids mixing
        independent concepts such as reason categories and components.
    max_reasons
        Maximum reason categories to show.
    title
        Figure title.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    _require_columns(qc_df, [reason_col])
    df = qc_df.copy()
    if status_col and status_col in df.columns:
        fail_set = {str(value).strip().lower() for value in fail_values}
        df = df.loc[df[status_col].fillna("").astype(str).str.strip().str.lower().isin(fail_set)].copy()
    if df.empty:
        fig, ax = plt.subplots(figsize=(9.0, 5.2), dpi=180)
        ax.text(0.5, 0.5, "No rejected records in QC table", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        ax.set_title(title)
        return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)
    reason_rows: list[dict[str, object]] = []
    for _, row in df.iterrows():
        raw_reasons = [part.strip() for part in str(row.get(reason_col, "") or "").split(";") if part.strip()]
        for reason in raw_reasons or ["unspecified"]:
            item = row.to_dict()
            item["_reason"] = _readable_qc_reason(reason)
            reason_rows.append(item)
    df = pd.DataFrame(reason_rows)
    top = df["_reason"].value_counts().head(int(max_reasons)).index
    df["_reason"] = df["_reason"].where(df["_reason"].isin(top), "Other")
    fig, ax = plt.subplots(figsize=(9.0, 5.2), dpi=180)
    if group_col and group_col in df.columns:
        counts = df.groupby(["_reason", group_col], dropna=False).size().reset_index(name="count")
        pivot = counts.pivot_table(index="_reason", columns=group_col, values="count", fill_value=0, aggfunc="sum")
        pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=True).index]
        pivot.plot(kind="barh", stacked=True, ax=ax)
        ax.legend(title=group_col.replace("_", " ").title(), frameon=True, fontsize=8)
    else:
        counts = df["_reason"].value_counts().sort_values()
        ax.barh(counts.index.astype(str), counts.values, color="#4c78a8")
    ax.set_xlabel("Rejected record count")
    ax.set_ylabel("QC reason")
    ax.set_title(title)
    ax.grid(True, axis="x", alpha=0.25)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    """Raise a clear error when columns are missing."""

    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")


def _status_colors(columns: pd.Index) -> list[str]:
    """Return stable colors for QC status labels."""

    palette = {"pass": "#1b9e77", "passed": "#1b9e77", "fail": "#d95f02", "failed": "#d95f02", "reject": "#d95f02", "rejected": "#d95f02"}
    return [palette.get(str(column).lower(), "#7570b3") for column in columns]


def _set_map_bounds(ax: plt.Axes, df: pd.DataFrame, lon_cols: list[str], lat_cols: list[str]) -> None:
    """Set padded lon/lat map bounds from multiple coordinate columns."""

    lon = pd.concat([pd.to_numeric(df[column], errors="coerce") for column in lon_cols], ignore_index=True).to_numpy(dtype=float)
    lat = pd.concat([pd.to_numeric(df[column], errors="coerce") for column in lat_cols], ignore_index=True).to_numpy(dtype=float)
    finite = np.isfinite(lon) & np.isfinite(lat)
    if not np.any(finite):
        ax.set_xlim(-180.0, 180.0)
        ax.set_ylim(-90.0, 90.0)
        return
    west, east = float(np.nanmin(lon[finite])), float(np.nanmax(lon[finite]))
    south, north = float(np.nanmin(lat[finite])), float(np.nanmax(lat[finite]))
    ax.set_xlim(west - max(0.03, 0.08 * max(east - west, 0.01)), east + max(0.03, 0.08 * max(east - west, 0.01)))
    ax.set_ylim(south - max(0.03, 0.08 * max(north - south, 0.01)), north + max(0.03, 0.08 * max(north - south, 0.01)))
    _set_geographic_aspect(ax)


def _set_geographic_aspect(ax: plt.Axes) -> None:
    """Preserve lon/lat proportions on QC map axes."""

    lat_min, lat_max = ax.get_ylim()
    lat_mid = 0.5 * (float(lat_min) + float(lat_max))
    cos_lat = math.cos(math.radians(lat_mid))
    if math.isfinite(cos_lat) and abs(cos_lat) > 1.0e-6:
        ax.set_aspect(1.0 / cos_lat, adjustable="box")


def _readable_qc_reason(reason: object) -> str:
    """Return a human-readable QC reason label."""

    labels = {
        "flat_trace": "Flat trace",
        "high_origin_energy": "High origin-window energy",
        "high_preorigin_energy": "High pre-origin energy",
        "insufficient_noise_window": "Insufficient noise window",
        "insufficient_preorigin_window": "Insufficient pre-origin window",
        "insufficient_signal_window": "Insufficient signal window",
        "invalid_samples": "Invalid samples",
        "low_snr": "Low SNR",
        "missing_trace": "Missing trace",
        "missing_waveform_path": "Missing waveform path",
        "record_too_short": "Record too short",
        "end_before_origin_plus_60s": "Record ends before origin + 60 s",
        "unspecified": "Unspecified",
    }
    text = str(reason or "").strip()
    return labels.get(text, text.replace("_", " ").capitalize() if text else "Unspecified")


__all__ = [
    "plot_data_synthetic_availability",
    "plot_post_qc_station_event_map",
    "plot_qc_drop_cause_diagnostics",
    "plot_retention_summary",
]
