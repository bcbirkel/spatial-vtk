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
from types import SimpleNamespace
from typing import Any

import pandas as pd

from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.config.runtime import SpatialVTKConfig


METRICS_TABLES: tuple[str, ...] = ("model_metric_band", "station_rollup", "event_rollup", "path_hex")
METRICS_TABLE_TAB_LABELS: dict[str, tuple[str, ...]] = {
    "model_metric_band": ("Overview", "Compare Models"),
    "station_rollup": ("Stations",),
    "event_rollup": ("Events",),
    "path_hex": ("Paths",),
}
METRICS_TABLE_PURPOSES: dict[str, str] = {
    "model_metric_band": "Model, metric, passband, and component summaries for overview and model-comparison tabs.",
    "station_rollup": "Station-level rollups used by the station map, station table, and station filters.",
    "event_rollup": "Event-level rollups used by the event map and event table.",
    "path_hex": "Distance/azimuth path-bin summaries used by the paths heatmap.",
}
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
MAP_COORDINATE_CANDIDATES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "station_rollup": (("sta_lon", "station_lon", "lon", "longitude"), ("sta_lat", "station_lat", "lat", "latitude")),
    "event_rollup": (("event_lon", "lon", "longitude"), ("event_lat", "lat", "latitude")),
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


def dashboard_summary_table_contracts() -> pd.DataFrame:
    """Return the dashboard tab-to-summary-table contract.

    The returned frame is small and display-ready. It documents which summary
    file feeds each metrics-dashboard tab and which columns are required before
    that tab can render meaningful content.
    """

    rows = []
    for name in METRICS_TABLES:
        rows.append(
            {
                "table": name,
                "tabs": ", ".join(METRICS_TABLE_TAB_LABELS.get(name, ())),
                "purpose": METRICS_TABLE_PURPOSES.get(name, ""),
                "required_columns": ", ".join(REQUIRED_METRICS_TABLE_COLUMNS[name]),
                "optional_columns": ", ".join(OPTIONAL_METRICS_TABLE_COLUMNS.get(name, ())),
                "map_coordinate_columns": _map_coordinate_contract_text(name),
            }
        )
    return pd.DataFrame(rows)


def _map_coordinate_contract_text(table_name: str) -> str:
    """Return display text describing map-coordinate requirements."""

    candidates = MAP_COORDINATE_CANDIDATES.get(str(table_name))
    if candidates is None:
        return ""
    lon_candidates, lat_candidates = candidates
    return f"lon: {' | '.join(lon_candidates)}; lat: {' | '.join(lat_candidates)}"


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


def dashboard_output_namespace(
    *,
    cfg: SpatialVTKConfig | None = None,
    create_parent: bool = True,
    include_summary_tables: bool = True,
    summary_format: str = "parquet",
) -> SimpleNamespace:
    """Resolve standard dashboard inputs as an attribute namespace."""

    return SimpleNamespace(
        **dashboard_output_paths(
            cfg=cfg,
            create_parent=create_parent,
            include_summary_tables=include_summary_tables,
            summary_format=summary_format,
        )
    )


def dashboard_output_status_frame(
    *,
    cfg: SpatialVTKConfig | None = None,
    create_parent: bool = True,
    include_summary_tables: bool = True,
    summary_format: str = "parquet",
) -> pd.DataFrame:
    """Return file readiness for standard dashboard inputs and summaries."""

    status = pd.DataFrame(
        _status_rows(
            dashboard_output_paths(
                cfg=cfg,
                create_parent=create_parent,
                include_summary_tables=include_summary_tables,
                summary_format=summary_format,
            )
        )
    )
    return _attach_dashboard_readiness(_attach_dashboard_contract(status))


def dashboard_summary_readiness_frame(
    summary_root: str | Path | None = None,
    *,
    cfg: SpatialVTKConfig | None = None,
    create_parent: bool = True,
    summary_format: str = "parquet",
) -> pd.DataFrame:
    """Return schema and content readiness for metrics-dashboard summaries.

    The returned rows are intentionally small: each standard dashboard summary
    file is checked for existence, required columns, row count, and finite
    dashboard value columns. This is suitable for notebooks and command-line
    preflight checks before launching Streamlit.
    """

    status = pd.DataFrame(
        _status_rows(
            dashboard_summary_table_paths(
                summary_root,
                cfg=cfg,
                create_parent=create_parent,
                format=summary_format,
            )
        )
    )
    return _attach_dashboard_readiness(_attach_dashboard_contract(status))


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


def _attach_dashboard_contract(status: pd.DataFrame) -> pd.DataFrame:
    """Attach dashboard table contract columns to summary-table status rows."""

    if status.empty:
        return status
    out = status.copy()
    out["dashboard_table"] = ""
    out["dashboard_tabs"] = ""
    out["required_columns"] = ""
    out["purpose"] = ""
    contracts = dashboard_summary_table_contracts().set_index("table")
    for table_name, contract in contracts.iterrows():
        mask = out["name"].astype(str).eq(f"{table_name}_summary_path")
        out.loc[mask, "dashboard_table"] = str(table_name)
        out.loc[mask, "dashboard_tabs"] = str(contract["tabs"])
        out.loc[mask, "required_columns"] = str(contract["required_columns"])
        out.loc[mask, "purpose"] = str(contract["purpose"])
    return out


def _attach_dashboard_readiness(status: pd.DataFrame) -> pd.DataFrame:
    """Attach dashboard summary schema/content readiness to status rows."""

    if status.empty:
        return status
    out = status.copy()
    for column in (
        "ready",
        "readiness",
        "row_count",
        "missing_columns",
        "map_ready",
        "missing_map_columns",
        "value_columns",
        "nonempty_value_columns",
        "message",
        "map_message",
    ):
        out[column] = pd.Series([pd.NA] * len(out), index=out.index, dtype="object")
    for index, row in out.iterrows():
        table_name = str(row.get("dashboard_table", ""))
        if not table_name:
            continue
        readiness = _inspect_dashboard_summary_table(Path(str(row["path"])), table_name)
        for key, value in readiness.items():
            out.at[index, key] = value
    return out


def _inspect_dashboard_summary_table(path: Path, table_name: str) -> dict[str, object]:
    """Return readiness details for one dashboard summary table path."""

    required = set(REQUIRED_METRICS_TABLE_COLUMNS[table_name])
    if not path.exists():
        return {
            "ready": False,
            "readiness": "missing",
            "row_count": "",
            "missing_columns": ", ".join(sorted(required)),
            "value_columns": "",
            "nonempty_value_columns": "",
            "message": f"{table_name} summary file is missing.",
        }
    try:
        columns = _dashboard_table_columns(path)
        row_count = _dashboard_table_row_count(path)
    except Exception as exc:  # pragma: no cover - exercised by integration failures
        return {
            "ready": False,
            "readiness": "read_error",
            "row_count": "",
            "missing_columns": "",
            "value_columns": "",
            "nonempty_value_columns": "",
            "message": f"{table_name} summary file could not be read: {exc}",
        }
    missing = sorted(column for column in required if column not in columns)
    schema_table = pd.DataFrame(columns=columns)
    value_columns = _dashboard_value_columns(schema_table)
    value_table = _read_dashboard_table_columns(path, value_columns)
    nonempty_value_columns = _nonempty_dashboard_value_columns(value_table, value_columns)
    map_status = _dashboard_map_readiness_from_path(path, table_name, columns)
    if missing:
        readiness = "missing_columns"
        ready = False
        message = f"{table_name} summary is missing required columns: {', '.join(missing)}."
    elif row_count == 0:
        readiness = "empty"
        ready = False
        message = f"{table_name} summary has no rows."
    elif not nonempty_value_columns:
        readiness = "no_value_data"
        ready = False
        message = f"{table_name} summary has rows but no finite dashboard value columns."
    else:
        readiness = "ready"
        ready = True
        message = f"{table_name} summary is ready."
    return {
        "ready": ready,
        "readiness": readiness,
        "row_count": row_count,
        "missing_columns": ", ".join(missing),
        "map_ready": map_status["ready"],
        "missing_map_columns": map_status["missing_columns"],
        "value_columns": ", ".join(value_columns),
        "nonempty_value_columns": ", ".join(nonempty_value_columns),
        "message": message,
        "map_message": map_status["message"],
    }


def _dashboard_table_columns(path: Path) -> list[str]:
    """Return dashboard summary columns without loading row data."""

    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        try:
            import pyarrow.parquet as pq

            return list(pq.ParquetFile(path).schema.names)
        except Exception:
            return list(pd.read_parquet(path).head(0).columns)
    if suffix == ".csv":
        return list(pd.read_csv(path, nrows=0).columns)
    raise ValueError(f"Unsupported dashboard table format for {path}. Use Parquet or CSV.")


def _dashboard_table_row_count(path: Path) -> int:
    """Return dashboard summary row count without materializing all columns."""

    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        try:
            import pyarrow.parquet as pq

            return int(pq.ParquetFile(path).metadata.num_rows)
        except Exception:
            return int(len(pd.read_parquet(path, columns=[])))
    if suffix == ".csv":
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    raise ValueError(f"Unsupported dashboard table format for {path}. Use Parquet or CSV.")


def _read_dashboard_table_columns(path: Path, columns: list[str] | tuple[str, ...]) -> pd.DataFrame:
    """Read only selected dashboard summary columns."""

    selected = [column for column in columns if column]
    if not selected:
        return pd.DataFrame()
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path, columns=selected)
    if suffix == ".csv":
        wanted = set(selected)
        return pd.read_csv(path, usecols=lambda column: column in wanted, low_memory=False)
    raise ValueError(f"Unsupported dashboard table format for {path}. Use Parquet or CSV.")


def _dashboard_map_readiness_from_path(path: Path, table_name: str, columns: list[str]) -> dict[str, object]:
    """Return map-readiness using only coordinate columns."""

    candidates = MAP_COORDINATE_CANDIDATES.get(str(table_name))
    if candidates is None:
        return {"ready": "", "missing_columns": "", "message": ""}
    lon_candidates, lat_candidates = candidates
    lon_col = next((column for column in lon_candidates if column in columns), None)
    lat_col = next((column for column in lat_candidates if column in columns), None)
    if lon_col is None or lat_col is None:
        return dashboard_map_readiness(pd.DataFrame(columns=columns), table_name)
    return dashboard_map_readiness(_read_dashboard_table_columns(path, [lon_col, lat_col]), table_name)


def dashboard_map_readiness(table: pd.DataFrame, table_name: str) -> dict[str, object]:
    """Return map-coordinate readiness for one dashboard summary table.

    Tables without a map tab return blank map-readiness fields. Station and
    event summaries are considered map-ready only when they contain one
    supported longitude column, one supported latitude column, and at least one
    finite coordinate pair.
    """

    candidates = MAP_COORDINATE_CANDIDATES.get(str(table_name))
    if candidates is None:
        return {"ready": "", "missing_columns": "", "message": ""}
    lon_candidates, lat_candidates = candidates
    lon_col = next((column for column in lon_candidates if column in table.columns), None)
    lat_col = next((column for column in lat_candidates if column in table.columns), None)
    missing_parts: list[str] = []
    if lon_col is None:
        missing_parts.append(f"longitude ({', '.join(lon_candidates)})")
    if lat_col is None:
        missing_parts.append(f"latitude ({', '.join(lat_candidates)})")
    if missing_parts:
        return {
            "ready": False,
            "missing_columns": "; ".join(missing_parts),
            "message": f"{table_name} summary can populate its table, but its map needs coordinate columns: {'; '.join(missing_parts)}.",
        }
    coordinates = pd.DataFrame(
        {
            "lon": pd.to_numeric(table[lon_col], errors="coerce"),
            "lat": pd.to_numeric(table[lat_col], errors="coerce"),
        }
    )
    finite_pairs = coordinates.dropna(subset=["lon", "lat"])
    if finite_pairs.empty:
        return {
            "ready": False,
            "missing_columns": "",
            "message": f"{table_name} summary has coordinate columns but no finite longitude/latitude pairs for the map.",
        }
    return {"ready": True, "missing_columns": "", "message": f"{table_name} map coordinates are ready."}


def _dashboard_value_columns(table: pd.DataFrame) -> list[str]:
    """Return dashboard value columns without importing labels at module load."""

    from spatial_vtk.config.labels import available_dashboard_value_columns

    return available_dashboard_value_columns(table)


def _nonempty_dashboard_value_columns(table: pd.DataFrame, columns: list[str]) -> list[str]:
    """Return value columns that contain at least one finite numeric value."""

    return [
        column
        for column in columns
        if column in table.columns and pd.to_numeric(table[column], errors="coerce").notna().any()
    ]


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
    "MAP_COORDINATE_CANDIDATES",
    "MetricsDashboardPaths",
    "OPTIONAL_METRICS_TABLE_COLUMNS",
    "QCDashboardPaths",
    "REQUIRED_METRICS_TABLE_COLUMNS",
    "dashboard_output_paths",
    "dashboard_output_namespace",
    "dashboard_output_status_frame",
    "dashboard_summary_readiness_frame",
    "dashboard_summary_table_contracts",
    "dashboard_summary_table_paths",
    "dashboard_map_readiness",
    "load_dashboard_summary_tables",
    "load_metric_long_table",
    "read_dashboard_table",
    "validate_dashboard_tables",
    "validate_map_columns",
    "validate_trace_qc_dashboard_table",
]
