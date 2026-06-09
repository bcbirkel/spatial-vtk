"""Dashboard data contracts and loading helpers.

Purpose
-------
This module validates the tables consumed by the Streamlit dashboards. It
keeps schema errors clear and independent from the dashboard UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


METRICS_TABLES: tuple[str, ...] = ("model_metric_band", "station_rollup", "event_rollup", "path_hex")


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


def load_dashboard_summary_tables(summary_root: str | Path) -> dict[str, pd.DataFrame]:
    """Load standard metrics dashboard summary tables from one directory."""

    root = Path(summary_root).expanduser()
    tables: dict[str, pd.DataFrame] = {}
    for name in METRICS_TABLES:
        path = _find_table(root, name)
        tables[name] = read_dashboard_table(path)
    return tables


def validate_dashboard_tables(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Validate standard metrics dashboard tables."""

    required = {
        "model_metric_band": {"model", "metric", "band", "n"},
        "station_rollup": {"station", "model", "metric", "band", "n"},
        "event_rollup": {"event_id", "model", "metric", "band", "n"},
        "path_hex": {"model", "metric", "band", "dist_bin_km", "az_bin_deg", "n"},
    }
    for name, columns in required.items():
        if name not in tables:
            raise ValueError(f"Missing dashboard summary table: {name}")
        _require_columns(tables[name], columns, table_name=name)
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


def _find_table(root: Path, name: str) -> Path:
    """Find one named CSV or Parquet table."""

    for suffix in (".parquet", ".csv"):
        candidate = root / f"{name}{suffix}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not find {name}.parquet or {name}.csv under {root}.")


def _require_columns(df: pd.DataFrame, columns: set[str], *, table_name: str) -> None:
    """Raise a clear error when required columns are missing."""

    missing = sorted(column for column in columns if column not in df.columns)
    if missing:
        raise ValueError(f"{table_name} is missing required columns: {missing}")


__all__ = [
    "METRICS_TABLES",
    "MetricsDashboardPaths",
    "QCDashboardPaths",
    "load_dashboard_summary_tables",
    "load_metric_long_table",
    "read_dashboard_table",
    "validate_dashboard_tables",
    "validate_map_columns",
    "validate_trace_qc_dashboard_table",
]
