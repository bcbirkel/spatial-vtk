"""Downstream output helpers for metric workflow rows.

Purpose
-------
This module turns file-based metric workflow rows into the standardized tables
used by enrichment, spatial analysis, maps, dashboards, and tutorial notebooks.

Usage examples
--------------
Prepare downstream tables:
  ``tables = prepare_metric_workflow_outputs(metric_rows, events=events, stations=stations)``

Write standard downstream files:
  ``paths = write_metric_outputs(metric_rows, "outputs/metrics", events=events, stations=stations)``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from spatial_vtk.config.runtime import active_config
from spatial_vtk.metrics.calculate.enrich import enrich_metric_table
from spatial_vtk.metrics.workflow.run import write_metric_rows
from spatial_vtk.visualize.dashboard import (
    build_dashboard_summaries,
    prepare_dashboard_metric_table,
    write_dashboard_metric_dataset,
    write_dashboard_summaries,
)


def prepare_metric_workflow_outputs(
    metric_rows: pd.DataFrame | str | Path,
    *,
    events: pd.DataFrame | str | Path | None = None,
    stations: pd.DataFrame | str | Path | None = None,
    residual_column: str | None = None,
    score_column: str | None = None,
    distance_bin_km: float = 10.0,
    azimuth_bin_deg: float = 30.0,
    dashboard_distance_bin_km: float = 10.0,
    dashboard_azimuth_bin_deg: float = 10.0,
) -> dict[str, pd.DataFrame | dict[str, pd.DataFrame]]:
    """Prepare metric workflow rows for downstream package modules.

    Parameters
    ----------
    metric_rows
        Metric workflow output table or path.
    events, stations
        Optional metadata tables joined before spatial/dashboard preparation.
    residual_column
        Optional transform column exposed as canonical ``residual``. When
        omitted, workflow rows prefer ``log2_residual`` if no ``residual``
        column exists.
    score_column
        Optional GOF column exposed as canonical ``score``.
    distance_bin_km, azimuth_bin_deg
        Binning used for path-summary output.
    dashboard_distance_bin_km, dashboard_azimuth_bin_deg
        Binning used for dashboard path summaries.

    Returns
    -------
    dict
        Tables keyed as ``metrics_long``, ``path_table``, ``path_summary``,
        ``dashboard_metrics``, and ``dashboard_summaries``.
    """

    from spatial_vtk.spatial.calculate.paths import build_path_table, summarize_residuals_by_path_bin

    raw = _read_metric_table(metric_rows)
    metrics_long = enrich_metric_table(
        raw,
        events=events,
        stations=stations,
        residual_column=residual_column,
        score_column=score_column,
    )
    path_table = build_path_table(metrics_long)
    path_summary = summarize_residuals_by_path_bin(
        path_table,
        distance_bin_km=distance_bin_km,
        azimuth_bin_deg=azimuth_bin_deg,
    )
    dashboard_metrics = prepare_dashboard_metric_table(metrics_long)
    dashboard_summaries = build_dashboard_summaries(
        dashboard_metrics,
        hex_dist=dashboard_distance_bin_km,
        hex_az=dashboard_azimuth_bin_deg,
    )
    return {
        "metrics_long": metrics_long,
        "path_table": path_table,
        "path_summary": path_summary,
        "dashboard_metrics": dashboard_metrics,
        "dashboard_summaries": dashboard_summaries,
    }


def write_metric_outputs(
    metric_rows: pd.DataFrame | str | Path,
    output_dir: str | Path | None = None,
    *,
    events: pd.DataFrame | str | Path | None = None,
    stations: pd.DataFrame | str | Path | None = None,
    residual_column: str | None = None,
    score_column: str | None = None,
    table_format: str = "parquet",
    dashboard_partitioned: bool = False,
    distance_bin_km: float = 10.0,
    azimuth_bin_deg: float = 30.0,
    dashboard_distance_bin_km: float = 10.0,
    dashboard_azimuth_bin_deg: float = 10.0,
) -> dict[str, Path]:
    """Write standard downstream outputs from metric workflow rows.

    Parameters
    ----------
    metric_rows
        Metric workflow output table or path.
    output_dir
        Directory where standard outputs are written. When omitted,
        ``outputs.tables`` from the active config is used.
    events, stations
        Optional metadata tables joined before output.
    residual_column
        Optional transform column exposed as canonical ``residual``.
    score_column
        Optional GOF column exposed as canonical ``score``.
    table_format
        ``"parquet"`` or ``"csv"`` for tabular outputs.
    dashboard_partitioned
        Whether the dashboard metric dataset should be partitioned by model,
        band, and metric.
    distance_bin_km, azimuth_bin_deg
        Binning used for path-summary output.
    dashboard_distance_bin_km, dashboard_azimuth_bin_deg
        Binning used for dashboard path summaries.

    Returns
    -------
    dict[str, pathlib.Path]
        Written paths keyed by artifact name.
    """

    fmt = str(table_format).strip().lower()
    if fmt not in {"parquet", "csv"}:
        raise ValueError("table_format must be 'parquet' or 'csv'.")
    root = Path(output_dir).expanduser() if output_dir is not None else (active_config().path("outputs.tables") or (active_config().root_dir / "outputs" / "tables"))
    root.mkdir(parents=True, exist_ok=True)
    suffix = ".parquet" if fmt == "parquet" else ".csv"
    tables = prepare_metric_workflow_outputs(
        metric_rows,
        events=events,
        stations=stations,
        residual_column=residual_column,
        score_column=score_column,
        distance_bin_km=distance_bin_km,
        azimuth_bin_deg=azimuth_bin_deg,
        dashboard_distance_bin_km=dashboard_distance_bin_km,
        dashboard_azimuth_bin_deg=dashboard_azimuth_bin_deg,
    )
    metrics_path = write_metric_rows(tables["metrics_long"], root / f"metrics_long{suffix}")
    path_table_path = write_metric_rows(tables["path_table"], root / f"path_table{suffix}")
    path_summary_path = write_metric_rows(tables["path_summary"], root / f"path_summary{suffix}")
    dashboard_root = write_dashboard_metric_dataset(
        tables["dashboard_metrics"],
        root / "dashboard_metrics",
        partitioned=dashboard_partitioned,
    )
    dashboard_summary_paths = write_dashboard_summaries(
        tables["dashboard_summaries"],
        root / "dashboard_summaries",
        format=fmt,
    )
    written: dict[str, Path] = {
        "metrics_long": metrics_path,
        "path_table": path_table_path,
        "path_summary": path_summary_path,
        "dashboard_metrics": dashboard_root,
    }
    written.update({f"dashboard_summary_{name}": path for name, path in dashboard_summary_paths.items()})
    return written


def _read_metric_table(value: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Read metric rows from a dataframe, CSV, or Parquet path.

    Parameters
    ----------
    value
        Metric table or path.

    Returns
    -------
    pandas.DataFrame
        Metric rows.
    """

    if isinstance(value, pd.DataFrame):
        return value.copy()
    path = Path(value).expanduser()
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path)


__all__ = [
    "prepare_metric_workflow_outputs",
    "write_metric_outputs",
]
