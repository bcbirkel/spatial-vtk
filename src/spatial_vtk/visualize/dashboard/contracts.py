"""Dashboard data contracts and loading helpers.

Purpose
-------
This module validates the tables consumed by the Streamlit dashboards. It
keeps schema errors clear and independent from the dashboard UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.config.runtime import SpatialVTKConfig


METRICS_TABLES: tuple[str, ...] = ("model_metric_band", "station_rollup", "event_rollup", "path_hex")
REQUIRED_METRICS_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "model_metric_band": ("model", "metric", "band", "n"),
    "station_rollup": ("station", "model", "metric", "band", "n"),
    "event_rollup": ("event_id", "model", "metric", "band", "n"),
    "path_hex": ("model", "metric", "band", "dist_bin_km", "az_bin_deg", "n"),
}
OPTIONAL_METRICS_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "model_metric_band": ("component",),
    "station_rollup": ("component", "sta_lat", "sta_lon", "med_dist_km", "Vs30", "vs30"),
    "event_rollup": ("component", "event_lat", "event_lon", "med_dist_km", "magnitude", "event_magnitude"),
    "path_hex": ("component",),
}


@dataclass(frozen=True)
class MetricsDashboardPaths:
    """Paths used by the metrics dashboard."""

    metrics_root: Path
    summary_root: Path


@dataclass(frozen=True)
class QCDashboardPaths:
    """Paths used by the QC dashboard."""

    trace_summary: Path


def read_dashboard_table(table: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Read a dashboard table from a DataFrame, Parquet, or CSV input."""

    if isinstance(table, pd.DataFrame):
        return table.copy()
    path = Path(table).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Dashboard table does not exist: {path}")
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported dashboard table format for {path}. Use Parquet or CSV.")


def load_dashboard_summary_tables(
    summary_root: str | Path,
    *,
    allow_missing_optional: bool = True,
) -> dict[str, pd.DataFrame]:
    """Load standard metrics dashboard summary tables from one directory.

    Missing optional tab tables are returned as empty schema-correct tables by
    default. This lets the Streamlit dashboard open and show an empty-state tab
    when, for example, a large run has not written path summaries yet.
    """

    root = Path(summary_root).expanduser()
    tables: dict[str, pd.DataFrame] = {}
    for name in METRICS_TABLES:
        path = _find_table(root, name, required=not allow_missing_optional)
        tables[name] = _empty_dashboard_table(name) if path is None else read_dashboard_table(path)
    return tables


def dashboard_summary_table_paths(
    summary_root: str | Path | None = None,
    *,
    cfg: SpatialVTKConfig | None = None,
    create_parent: bool = True,
    format: str = "parquet",
) -> dict[str, Path]:
    """Return expected dashboard summary table paths.

    Existing ``.parquet`` or ``.csv`` files are reported as-is. Missing tables
    are represented with the configured output format so notebook status tables
    can show exactly which dashboard tab inputs are not ready yet.
    """

    suffix = _summary_suffix(format)
    root = (
        Path(summary_root).expanduser()
        if summary_root is not None
        else resolve_output_path("dashboard_summaries", kind="dashboard", cfg=cfg, create_parent=create_parent)
    )
    if create_parent:
        root.mkdir(parents=True, exist_ok=True)
    return {
        f"{name}_summary_path": _find_table(root, name, required=False) or root / f"{name}{suffix}"
        for name in METRICS_TABLES
    }


def dashboard_output_paths(
    *,
    cfg: SpatialVTKConfig | None = None,
    create_parent: bool = True,
    include_summary_tables: bool = True,
    summary_format: str = "parquet",
) -> dict[str, Path]:
    """Resolve the standard metrics and QC dashboard inputs from config."""

    paths = {
        "metrics_long_path": resolve_output_path("metrics_long", kind="table", cfg=cfg, create_parent=create_parent),
        "qc_trace_summary_path": resolve_output_path("qc_trace_summary", kind="table", cfg=cfg, create_parent=create_parent),
        "qc_inventory_path": resolve_output_path("qc_inventory", kind="table", cfg=cfg, create_parent=create_parent),
        "qc_inventory_overlap_path": resolve_output_path("qc_inventory_overlap", kind="table", cfg=cfg, create_parent=create_parent),
        "metrics_dashboard_root": resolve_output_path("metrics_dashboard", kind="dashboard", cfg=cfg, create_parent=create_parent),
        "dashboard_summary_root": resolve_output_path("dashboard_summaries", kind="dashboard", cfg=cfg, create_parent=create_parent),
    }
    if include_summary_tables:
        paths.update(
            dashboard_summary_table_paths(
                paths["dashboard_summary_root"],
                cfg=cfg,
                create_parent=create_parent,
                format=summary_format,
            )
        )
    return paths


def dashboard_output_status_frame(
    *,
    cfg: SpatialVTKConfig | None = None,
    create_parent: bool = True,
    include_summary_tables: bool = True,
    summary_format: str = "parquet",
) -> pd.DataFrame:
    """Return file readiness for standard dashboard inputs and summaries."""

    return pd.DataFrame(
        _status_rows(
            dashboard_output_paths(
                cfg=cfg,
                create_parent=create_parent,
                include_summary_tables=include_summary_tables,
                summary_format=summary_format,
            )
        )
    )


def _status_rows(paths: dict[str, str | Path]) -> list[dict[str, object]]:
    """Return display-ready status rows for dashboard paths."""

    rows: list[dict[str, object]] = []
    for name, raw_path in paths.items():
        path = Path(raw_path)
        row: dict[str, object] = {
            "name": str(name),
            "path": str(path),
            "exists": path.exists(),
            "size_gb": None,
            "modified": None,
        }
        if path.exists():
            stat = path.stat()
            row["size_gb"] = round(stat.st_size / 1024**3, 3)
            row["modified"] = _format_mtime(stat.st_mtime)
        rows.append(row)
    return rows


def _format_mtime(mtime: float) -> str:
    """Format one filesystem modification time."""

    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")


def validate_dashboard_tables(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Validate standard metrics dashboard tables."""

    for name, columns in REQUIRED_METRICS_TABLE_COLUMNS.items():
        if name not in tables:
            raise ValueError(f"Missing dashboard summary table: {name}")
        _require_columns(tables[name], set(columns), table_name=name)
    return tables


def validate_trace_qc_dashboard_table(trace_df: pd.DataFrame) -> pd.DataFrame:
    """Validate the trace-QC dashboard input table."""

    _require_columns(trace_df, {"event_id", "station"}, table_name="trace QC summary")
    return trace_df


def validate_map_columns(df: pd.DataFrame, *, table_name: str, lon_candidates: tuple[str, ...], lat_candidates: tuple[str, ...]) -> tuple[str, str]:
    """Return longitude and latitude columns or raise a clear error."""

    lon_col = next((column for column in lon_candidates if column in df.columns), None)
    lat_col = next((column for column in lat_candidates if column in df.columns), None)
    if lon_col is None or lat_col is None:
        raise ValueError(f"{table_name} requires longitude/latitude columns. Tried lon={lon_candidates}, lat={lat_candidates}.")
    return lon_col, lat_col


def load_metric_long_table(metrics_root: str | Path) -> pd.DataFrame:
    """Load the dashboard long metric table from a dataset root."""

    from spatial_vtk.visualize.dashboard.export import load_dashboard_metric_dataset

    return load_dashboard_metric_dataset(metrics_root)


def _find_table(root: Path, name: str, *, required: bool = True) -> Path | None:
    """Find one named CSV or Parquet table."""

    for suffix in (".parquet", ".csv"):
        candidate = root / f"{name}{suffix}"
        if candidate.exists():
            return candidate
    if not required:
        return None
    raise FileNotFoundError(f"Could not find {name}.parquet or {name}.csv under {root}.")


def _summary_suffix(format: str) -> str:
    """Return the file suffix for one dashboard summary output format."""

    clean = str(format).strip().lower()
    if clean == "parquet":
        return ".parquet"
    if clean == "csv":
        return ".csv"
    raise ValueError("format must be 'csv' or 'parquet'.")


def _empty_dashboard_table(name: str) -> pd.DataFrame:
    """Return an empty table with the schema needed by one dashboard tab."""

    if name not in REQUIRED_METRICS_TABLE_COLUMNS:
        raise KeyError(f"Unknown dashboard summary table: {name}")
    columns = [
        *REQUIRED_METRICS_TABLE_COLUMNS[name],
        *OPTIONAL_METRICS_TABLE_COLUMNS.get(name, ()),
    ]
    return pd.DataFrame(columns=list(dict.fromkeys(columns)))


def _require_columns(df: pd.DataFrame, columns: set[str], *, table_name: str) -> None:
    """Raise a clear error when required columns are missing."""

    missing = sorted(column for column in columns if column not in df.columns)
    if missing:
        raise ValueError(f"{table_name} is missing required columns: {missing}")


__all__ = [
    "METRICS_TABLES",
    "MetricsDashboardPaths",
    "OPTIONAL_METRICS_TABLE_COLUMNS",
    "QCDashboardPaths",
    "REQUIRED_METRICS_TABLE_COLUMNS",
    "dashboard_output_paths",
    "dashboard_output_status_frame",
    "dashboard_summary_table_paths",
    "load_dashboard_summary_tables",
    "load_metric_long_table",
    "read_dashboard_table",
    "validate_dashboard_tables",
    "validate_map_columns",
    "validate_trace_qc_dashboard_table",
]
