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

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from spatial_vtk.config.labels import display_label
from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.config.runtime import SpatialVTKConfig
from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
from spatial_vtk.visualize.figure_io import finish_figure
from spatial_vtk.visualize.figure_sidecars import write_figure_row_sidecar


@dataclass(frozen=True)
class QCFigureResult:
    """Result from writing the large-run QC figure suite."""

    rows: tuple[dict[str, object], ...]

    def status_frame(self) -> pd.DataFrame:
        """Return a compact notebook status table for QC figure outputs."""

        return pd.DataFrame(list(self.rows))


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
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
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
            write_sidecar=write_sidecar,
            sidecar_rows=sidecar_rows,
            sidecar_dir=sidecar_dir,
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
    return _finish_qc_figure(
        fig,
        output_path,
        outpath=outpath,
        showfig=showfig,
        savefig=savefig,
        sidecar_df=counts,
        source_df=qc_df,
        write_sidecar=write_sidecar,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
        metadata={
            "plot": "retention_summary",
            "group_col": group_col,
            "status_col": status_col,
            "count_col": count_col,
        },
    )


def _plot_pair_retention_summary(
    retention_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str,
    showfig: bool | None,
    savefig: bool | None,
    outpath: str | Path | None,
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
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
    return _finish_qc_figure(
        fig,
        output_path,
        outpath=outpath,
        showfig=showfig,
        savefig=savefig,
        sidecar_df=df,
        source_df=retention_df,
        write_sidecar=write_sidecar,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
        metadata={"plot": "pair_retention_summary"},
    )


def plot_data_synthetic_availability(
    availability_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    event_col: str = "event_id",
    station_col: str = "station",
    observed_col: str = "observed_available",
    synthetic_col: str = "synthetic_available",
    title: str = "Observed and Synthetic Availability",
    max_tick_labels: int = 80,
    max_figsize: tuple[float, float] = (18.0, 12.0),
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
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
    max_tick_labels
        Maximum event/station tick labels to draw on each axis before labels
        are thinned.
    max_figsize
        Maximum figure size in inches. Large datasets are drawn as a dense
        raster instead of creating one huge Matplotlib canvas.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    _require_columns(availability_df, [event_col, station_col, observed_col, synthetic_col])
    df = availability_df.copy()
    df["_availability_code"] = df[observed_col].astype(bool).astype(int) + 2 * df[synthetic_col].astype(bool).astype(int)
    matrix = df.pivot_table(index=station_col, columns=event_col, values="_availability_code", aggfunc="max", fill_value=0)
    width = min(float(max_figsize[0]), max(6.8, 0.42 * matrix.shape[1] + 3.2))
    height = min(float(max_figsize[1]), max(4.8, 0.24 * matrix.shape[0] + 2.0))
    fig, ax = plt.subplots(figsize=(width, height), dpi=180)
    image = ax.imshow(matrix.to_numpy(dtype=float), aspect="auto", cmap="viridis", vmin=0, vmax=3)
    _set_sparse_tick_labels(ax, axis="x", labels=matrix.columns.astype(str), max_labels=max_tick_labels)
    _set_sparse_tick_labels(ax, axis="y", labels=matrix.index.astype(str), max_labels=max_tick_labels)
    event_label = "Event"
    station_label = "Station"
    if matrix.shape[1] > int(max_tick_labels):
        event_label = f"Event ({matrix.shape[1]} total; labels sampled)"
    if matrix.shape[0] > int(max_tick_labels):
        station_label = f"Station ({matrix.shape[0]} total; labels sampled)"
    ax.set_xlabel(event_label)
    ax.set_ylabel(station_label)
    ax.set_title(title)
    cbar = fig.colorbar(image, ax=ax, ticks=[0, 1, 2, 3])
    cbar.ax.set_yticklabels(["None", "Observed", "Synthetic", "Both"])
    return _finish_qc_figure(
        fig,
        output_path,
        outpath=outpath,
        output_key="data_synthetic_availability",
        showfig=showfig,
        savefig=savefig,
        sidecar_df=df,
        source_df=availability_df,
        write_sidecar=write_sidecar,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
        metadata={
            "plot": "data_synthetic_availability",
            "event_col": event_col,
            "station_col": station_col,
            "observed_col": observed_col,
            "synthetic_col": synthetic_col,
        },
    )


def write_qc_figures_from_outputs(
    outputs: Any,
    settings: Any,
    *,
    cfg: SpatialVTKConfig | None = None,
    overwrite: bool = False,
) -> QCFigureResult:
    """Write standard QC figures from configured output groups.

    The helper keeps notebooks from repeating compact-table readiness checks,
    table loading, map/figure keyword selection, and figure-output plumbing.
    """

    table_specs = {
        "retention": "retention_path",
        "event_station_retention": "event_station_retention_path",
        "qc_availability": "availability_path",
        "post_qc_records": "post_qc_records_path",
        "drop_causes": "drop_causes_path",
        "drop_causes_overlap": "drop_causes_overlap_path",
    }
    required = [_output_group_path(outputs, path_name) for path_name in table_specs.values()]
    gate = settings.render_gate(
        required,
        missing_message="Skipping figures until all compact QC tables exist.",
    )
    figure_specs: tuple[dict[str, Any], ...] = (
        {
            "artifact": "retention_summary",
            "table": "retention",
            "func": plot_retention_summary,
            "output_key": "retention_summary",
            "title": "QC Pair Retention Summary (Observed/Synthetic Event-Station Overlap)",
        },
        {
            "artifact": "event_station_retention",
            "table": "event_station_retention",
            "func": plot_event_station_retention_heatmap,
            "output_key": "event_station_retention",
            "title": "Post-QC Pair Retention by Event and Station (Event-Station Overlap)",
        },
        {
            "artifact": "data_synthetic_availability",
            "table": "qc_availability",
            "func": plot_data_synthetic_availability,
            "output_key": "data_synthetic_availability",
            "title": "Observed/Synthetic Availability (Post-QC Event-Station Overlap)",
        },
        {
            "artifact": "post_qc_station_event_map",
            "table": "post_qc_records",
            "func": plot_post_qc_station_event_map,
            "output_key": "post_qc_station_event_map",
            "map": True,
        },
        {
            "artifact": "drop_cause_diagnostics",
            "table": "drop_causes",
            "func": plot_qc_drop_cause_diagnostics,
            "output_key": "drop_cause_diagnostics",
            "title": "QC Drop Causes (All Events)",
            "kwargs": {"reason_col": "_reason", "status_col": None, "count_col": "count"},
        },
        {
            "artifact": "qc_drop_cause_diagnostics_overlap",
            "table": "drop_causes_overlap",
            "func": plot_qc_drop_cause_diagnostics,
            "path_name": "drop_causes_overlap_figure_path",
            "output_key": "qc_drop_cause_diagnostics_overlap",
            "title": "QC Drop Causes (Observed/Synthetic Event-Station Overlap)",
            "kwargs": {"reason_col": "_reason", "status_col": None, "count_col": "count"},
        },
    )
    if not gate.ready:
        status = "missing_input" if gate.figures_enabled else "disabled"
        return QCFigureResult(
            tuple(
                _qc_figure_status_row(
                    spec["artifact"],
                    status,
                    table_path=_output_group_path(outputs, table_specs[spec["table"]]),
                    figure_path=_qc_figure_output_path(outputs, spec, cfg=cfg),
                    message=gate.message,
                )
                for spec in figure_specs
            )
        )
    figure_paths = {
        spec["artifact"]: _qc_figure_output_path(outputs, spec, cfg=cfg)
        for spec in figure_specs
    }
    if not overwrite and all(path is not None and path.exists() for path in figure_paths.values()):
        return QCFigureResult(
            tuple(
                _qc_figure_status_row(
                    spec["artifact"],
                    "exists",
                    table_path=_output_group_path(outputs, table_specs[spec["table"]]),
                    figure_path=figure_paths[spec["artifact"]],
                    message=f"skip {figure_paths[spec['artifact']].name}: exists",
                )
                for spec in figure_specs
            )
        )

    try:
        tables = outputs.load_tables(table_specs, cfg=cfg)
    except Exception as exc:
        return QCFigureResult(
            tuple(
                _qc_figure_status_row(
                    spec["artifact"],
                    "load_failed",
                    table_path=_output_group_path(outputs, table_specs[spec["table"]]),
                    figure_path=_qc_figure_output_path(outputs, spec, cfg=cfg),
                    message=f"{type(exc).__name__}: {exc}",
                )
                for spec in figure_specs
            )
        )

    rows: list[dict[str, object]] = []
    for spec in figure_specs:
        artifact = spec["artifact"]
        table_name = spec["table"]
        table = tables[table_name]
        table_path = _output_group_path(outputs, table_specs[table_name])
        figure_path = figure_paths[artifact]
        if figure_path is None:
            rows.append(
                _qc_figure_status_row(
                    artifact,
                    "missing_output",
                    table_path=table_path,
                    figure_path=None,
                    row_count=len(table),
                    message="No figure output path could be resolved.",
                )
            )
            continue
        if figure_path.exists() and not overwrite:
            rows.append(
                _qc_figure_status_row(
                    artifact,
                    "exists",
                    table_path=table_path,
                    figure_path=figure_path,
                    row_count=len(table),
                    message=f"skip {figure_path.name}: exists",
                )
            )
            continue
        plot_kwargs = settings.plot_kwargs(include_basemap=True) if spec.get("map") else settings.plot_kwargs()
        plot_kwargs.update(spec.get("kwargs", {}))
        if "title" in spec:
            plot_kwargs["title"] = spec["title"]
        try:
            spec["func"](
                table,
                outpath=figure_path,
                savefig=True,
                **plot_kwargs,
            )
            plt.close("all")
            rows.append(
                _qc_figure_status_row(
                    artifact,
                    "wrote",
                    table_path=table_path,
                    figure_path=figure_path,
                    row_count=len(table),
                    message=f"wrote {figure_path}",
                )
            )
        except Exception as exc:
            plt.close("all")
            rows.append(
                _qc_figure_status_row(
                    artifact,
                    "plot_failed",
                    table_path=table_path,
                    figure_path=figure_path,
                    row_count=len(table),
                    message=f"{type(exc).__name__}: {exc}",
                )
            )
    return QCFigureResult(tuple(rows))


def write_large_run_qc_figures_from_outputs(
    outputs: Any,
    settings: Any,
    *,
    cfg: SpatialVTKConfig | None = None,
    overwrite: bool = False,
) -> QCFigureResult:
    """Backward-compatible alias for :func:`write_qc_figures_from_outputs`."""

    return write_qc_figures_from_outputs(outputs, settings, cfg=cfg, overwrite=overwrite)


def _output_group_path(outputs: Any, name: str) -> Path | None:
    """Return one path from an output group-like object."""

    if hasattr(outputs, name):
        value = getattr(outputs, name)
        return None if value is None else Path(value)
    paths = getattr(outputs, "paths", None)
    if isinstance(paths, dict) and name in paths:
        value = paths[name]
        return None if value is None else Path(value)
    return None


def _qc_figure_output_path(outputs: Any, spec: dict[str, Any], *, cfg: SpatialVTKConfig | None) -> Path | None:
    """Return one QC figure output path."""

    path_name = spec.get("path_name")
    if path_name:
        configured = _output_group_path(outputs, str(path_name))
        if configured is not None:
            configured.parent.mkdir(parents=True, exist_ok=True)
            return configured
    try:
        return resolve_output_path(str(spec["output_key"]), kind="figure", cfg=cfg, create_parent=True)
    except Exception:
        return None


def _qc_figure_status_row(
    artifact: str,
    status: str,
    *,
    table_path: Path | None,
    figure_path: Path | None,
    row_count: int = 0,
    message: str = "",
) -> dict[str, object]:
    """Return one QC figure status row."""

    return {
        "artifact": artifact,
        "status": status,
        "row_count": int(row_count),
        "table_path": None if table_path is None else str(table_path),
        "figure_path": None if figure_path is None else str(figure_path),
        "message": message,
    }


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
    max_count_labels: int = 2500,
    max_tick_labels: int = 80,
    max_figsize: tuple[float, float] = (18.0, 12.0),
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
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
        Labels are automatically skipped when the heatmap contains more than
        ``max_count_labels`` populated cells.
    max_count_labels
        Maximum number of heatmap cells that may receive retained/total text.
        This keeps large production runs from spending minutes to hours placing
        unreadable labels.
    max_tick_labels
        Maximum event/station tick labels to draw on each axis before labels
        are thinned.
    max_figsize
        Maximum figure size in inches. Large datasets are drawn as a dense
        raster instead of creating one huge Matplotlib canvas.
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
    width = min(float(max_figsize[0]), max(6.8, 0.42 * matrix.shape[1] + 3.2))
    height = min(float(max_figsize[1]), max(4.8, 0.24 * matrix.shape[0] + 2.0))
    fig, ax = plt.subplots(figsize=(width, height), dpi=180)
    image = ax.imshow(matrix.to_numpy(dtype=float), aspect="auto", cmap="viridis", vmin=0.0, vmax=100.0)
    _set_sparse_tick_labels(ax, axis="x", labels=matrix.columns.astype(str), max_labels=max_tick_labels)
    _set_sparse_tick_labels(ax, axis="y", labels=matrix.index.astype(str), max_labels=max_tick_labels)
    event_label = "Event"
    station_label = "Station"
    if matrix.shape[1] > int(max_tick_labels):
        event_label = f"Event ({matrix.shape[1]} total; labels sampled)"
    if matrix.shape[0] > int(max_tick_labels):
        station_label = f"Station ({matrix.shape[0]} total; labels sampled)"
    ax.set_xlabel(event_label)
    ax.set_ylabel(station_label)
    ax.set_title(title)
    cell_count = int(matrix.shape[0] * matrix.shape[1])
    if show_counts and cell_count <= int(max_count_labels) and {retained_col, total_col} <= set(df.columns):
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
    return _finish_qc_figure(
        fig,
        output_path,
        outpath=outpath,
        output_key="event_station_retention",
        showfig=showfig,
        savefig=savefig,
        sidecar_df=df,
        source_df=retention_df,
        write_sidecar=write_sidecar,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
        metadata={
            "plot": "event_station_retention_heatmap",
            "event_col": event_col,
            "station_col": station_col,
            "value_col": value_col,
            "retained_col": retained_col,
            "total_col": total_col,
        },
    )


def _set_sparse_tick_labels(
    ax: plt.Axes,
    *,
    axis: str,
    labels: pd.Index,
    max_labels: int,
) -> None:
    """Set axis tick labels, thinning dense axes for large heatmaps."""

    total = len(labels)
    if total == 0:
        if axis == "x":
            ax.set_xticks([])
        else:
            ax.set_yticks([])
        return
    limit = max(1, int(max_labels))
    step = max(1, math.ceil(total / limit))
    positions = np.arange(0, total, step)
    text = labels[positions]
    if axis == "x":
        ax.set_xticks(positions)
        ax.set_xticklabels(text, rotation=45, ha="right", fontsize=8)
    else:
        ax.set_yticks(positions)
        ax.set_yticklabels(text, fontsize=8)


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
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
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
    return _finish_qc_figure(
        fig,
        output_path,
        outpath=outpath,
        showfig=showfig,
        savefig=savefig,
        sidecar_df=df.assign(_retained=retained.to_numpy(dtype=bool)),
        source_df=records_df,
        write_sidecar=write_sidecar,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
        metadata={
            "plot": "post_qc_station_event_map",
            "station_lon_col": station_lon_col,
            "station_lat_col": station_lat_col,
            "event_lon_col": event_lon_col,
            "event_lat_col": event_lat_col,
            "status_col": status_col,
        },
    )


def plot_qc_drop_cause_diagnostics(
    qc_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    reason_col: str = "qc_reason",
    status_col: str | None = "qc_status",
    count_col: str | None = None,
    fail_values: tuple[str, ...] = ("fail", "failed", "reject", "rejected"),
    group_col: str | None = None,
    max_reasons: int = 12,
    title: str = "QC Drop Causes",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
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
    count_col
        Optional precomputed count column. Use this with chunked reason-count
        summaries to avoid plotting from row-level QC inventories.
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
        return _finish_qc_figure(
            fig,
            output_path,
            outpath=outpath,
            showfig=showfig,
            savefig=savefig,
            sidecar_df=df,
            source_df=qc_df,
            write_sidecar=write_sidecar,
            sidecar_rows=sidecar_rows,
            sidecar_dir=sidecar_dir,
            metadata={"plot": "qc_drop_cause_diagnostics", "empty": True},
        )
    if count_col and count_col in df.columns:
        df[reason_col] = df[reason_col].astype(str).replace("", "Unspecified")
        top = df.groupby(reason_col, dropna=False)[count_col].sum().sort_values(ascending=False).head(int(max_reasons)).index
        df[reason_col] = df[reason_col].where(df[reason_col].isin(top), "Other")
        fig, ax = plt.subplots(figsize=(9.0, 5.2), dpi=180)
        if group_col and group_col in df.columns:
            counts = df.groupby([reason_col, group_col], dropna=False)[count_col].sum().reset_index(name="count")
            pivot = counts.pivot_table(index=reason_col, columns=group_col, values="count", fill_value=0, aggfunc="sum")
            pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=True).index]
            pivot.plot(kind="barh", stacked=True, ax=ax)
            ax.legend(title=group_col.replace("_", " ").title(), frameon=True, fontsize=8)
        else:
            counts = df.groupby(reason_col, dropna=False)[count_col].sum().sort_values()
            ax.barh(counts.index.astype(str), counts.values, color="#4c78a8")
        ax.set_xlabel("Rejected record count")
        ax.set_ylabel("QC reason")
        ax.set_title(title)
        ax.grid(True, axis="x", alpha=0.25)
        sidecar_df = _counts_to_sidecar_frame(counts)
        return _finish_qc_figure(
            fig,
            output_path,
            outpath=outpath,
            showfig=showfig,
            savefig=savefig,
            sidecar_df=sidecar_df,
            source_df=df,
            write_sidecar=write_sidecar,
            sidecar_rows=sidecar_rows,
            sidecar_dir=sidecar_dir,
            metadata={
                "plot": "qc_drop_cause_diagnostics",
                "reason_col": reason_col,
                "status_col": status_col,
                "count_col": count_col,
                "group_col": group_col,
            },
        )
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
    sidecar_df = _counts_to_sidecar_frame(counts)
    return _finish_qc_figure(
        fig,
        output_path,
        outpath=outpath,
        showfig=showfig,
        savefig=savefig,
        sidecar_df=sidecar_df,
        source_df=df,
        write_sidecar=write_sidecar,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
        metadata={
            "plot": "qc_drop_cause_diagnostics",
            "reason_col": reason_col,
            "status_col": status_col,
            "count_col": count_col,
            "group_col": group_col,
        },
    )


def _finish_qc_figure(
    fig: plt.Figure,
    output_path: str | Path | None = None,
    *,
    outpath: str | Path | None = None,
    output_key: str | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    sidecar_df: pd.DataFrame | None = None,
    source_df: pd.DataFrame | None = None,
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
    metadata: dict[str, Any] | None = None,
) -> plt.Figure:
    """Finish a QC figure and optionally write plotted-row sidecars."""

    finished = finish_figure(
        fig,
        output_path,
        outpath=outpath,
        output_key=output_key,
        showfig=showfig,
        savefig=savefig,
    )
    figure_path = getattr(finished, "spatial_vtk_saved_path", None)
    if write_sidecar and figure_path is not None and sidecar_df is not None:
        write_figure_row_sidecar(
            figure_path,
            sidecar_df,
            enabled=True,
            sidecar_rows=sidecar_rows,
            sidecar_dir=sidecar_dir,
            source_rows=source_df,
            metadata=metadata,
        )
    return finished


def _counts_to_sidecar_frame(counts: pd.Series | pd.DataFrame) -> pd.DataFrame:
    """Return count rows in a dataframe shape suitable for sidecars."""

    if isinstance(counts, pd.Series):
        return counts.reset_index(name="count")
    return counts.copy()


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
    "QCFigureResult",
    "plot_data_synthetic_availability",
    "plot_post_qc_station_event_map",
    "plot_qc_drop_cause_diagnostics",
    "plot_retention_summary",
    "write_qc_figures_from_outputs",
    "write_large_run_qc_figures_from_outputs",
]
