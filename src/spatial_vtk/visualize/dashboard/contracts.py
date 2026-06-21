"""Dashboard data contracts and loading helpers.

Purpose
-------
This module validates the tables consumed by the Streamlit dashboards. It
keeps schema errors clear and independent from the dashboard UI.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd

from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.config.runtime import SpatialVTKConfig
from spatial_vtk.io import parquet_table_columns, table_row_count


ConfigInput = SpatialVTKConfig | str | Path


METRICS_TABLES: tuple[str, ...] = ("model_metric_band", "station_rollup", "event_rollup", "path_hex")
METRICS_TABLE_TAB_LABELS: dict[str, tuple[str, ...]] = {
    "model_metric_band": ("Overview", "Compare Models"),
    "station_rollup": ("Stations",),
    "event_rollup": ("Events",),
    "path_hex": ("Paths",),
}
METRICS_TABLE_PURPOSES: dict[str, str] = {
    "model_metric_band": "Model, metric, passband, oscillator-period, and component summaries for overview and model-comparison tabs.",
    "station_rollup": "Station-level metric rollups, including PSA oscillator periods when present, used by the station map, station table, and station filters.",
    "event_rollup": "Event-level metric rollups, including PSA oscillator periods when present, used by the event map and event table.",
    "path_hex": "Distance/azimuth path-bin summaries, including PSA oscillator periods when present, used by the paths heatmap.",
}
REQUIRED_METRICS_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "model_metric_band": ("model", "metric", "band", "n"),
    "station_rollup": ("station", "model", "metric", "band", "n"),
    "event_rollup": ("event_id", "model", "metric", "band", "n"),
    "path_hex": ("model", "metric", "band", "dist_bin_km", "az_bin_deg", "n"),
}
OPTIONAL_METRICS_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "model_metric_band": ("period_s", "component", "event_count", "station_count"),
    "station_rollup": ("period_s", "component", "sta_lat", "sta_lon", "med_dist_km", "Vs30", "vs30", "event_count"),
    "event_rollup": ("period_s", "component", "event_lat", "event_lon", "med_dist_km", "magnitude", "event_magnitude", "station_count"),
    "path_hex": ("period_s", "component", "event_count", "station_count"),
}
REQUIRED_TRACE_QC_TABLE_COLUMNS: tuple[str, ...] = ("event_id", "station")
MAP_COORDINATE_CANDIDATES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "station_rollup": (("sta_lon", "station_lon", "lon", "longitude"), ("sta_lat", "station_lat", "lat", "latitude")),
    "event_rollup": (("event_lon", "lon", "longitude"), ("event_lat", "lat", "latitude")),
}
VALUE_COLUMN_FAMILY_ORDER: tuple[str, ...] = ("residual", "score/gof", "observed", "synthetic", "metric value")


@dataclass(frozen=True)
class MetricsDashboardPaths:
    """Paths used by the metrics dashboard.

    ``metrics_dataset_dir`` and ``dashboard_summary_table_dir`` are the
    preferred public names. ``metrics_root`` and ``summary_root`` remain as
    dataclass fields for compatibility with earlier dashboard helpers.
    """

    metrics_root: Path
    summary_root: Path

    @property
    def metrics_dataset_dir(self) -> Path:
        """Metrics dashboard row dataset directory or direct row table."""

        return self.metrics_root

    @property
    def dashboard_summary_table_dir(self) -> Path:
        """Dashboard summary-table directory used by overview tabs."""

        return self.summary_root


@dataclass(frozen=True)
class QCDashboardPaths:
    """Paths used by the QC dashboard.

    ``qc_trace_summary_table`` is the preferred public name. ``trace_summary``
    remains as the dataclass field for compatibility with earlier helpers.
    """

    trace_summary: Path

    @property
    def qc_trace_summary_table(self) -> Path:
        """QC trace-summary CSV/parquet table."""

        return self.trace_summary


@dataclass(frozen=True)
class DashboardOutputReadiness:
    """Notebook-friendly readiness decision for configured dashboard outputs."""

    should_run: bool
    reason: str
    message: str
    metrics_status: pd.DataFrame
    summary_status: pd.DataFrame
    input_status: pd.DataFrame
    qc_status: pd.DataFrame | None = None

    def status_frame(self) -> pd.DataFrame:
        """Return combined input, metric-dataset, summary-table, and QC status.

        The child readiness frames are built by different inspectors. This
        method keeps their detailed columns while normalizing the notebook
        contract used by large-run status cells: ``item_type``,
        ``artifact_label``, ``resolved_path``, ``path``, ``exists``,
        ``readiness``, ``message``, and ``suggested_action`` are always present
        when at least one child frame has rows.
        """

        frame_specs = [
            ("input", self.input_status),
            ("dataset", self.metrics_status),
            ("summary_table", self.summary_status),
            ("qc_table", self.qc_status),
        ]
        if not any(frame is not None and not frame.empty for _, frame in frame_specs):
            return pd.DataFrame()
        rows: list[dict[str, object]] = []
        for item_type, frame in frame_specs:
            if frame is None or frame.empty:
                continue
            for row in frame.astype(object).to_dict("records"):
                normalized = _normalize_dashboard_status_row(row, item_type=item_type)
                rows.append(normalized)
        columns = _dashboard_status_column_order(rows)
        return pd.DataFrame(rows, columns=columns)

    def summary_frame(self) -> pd.DataFrame:
        """Return a compact dashboard/tab readiness summary."""

        return dashboard_readiness_summary_frame(readiness=self)


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
        return pd.read_csv(path, low_memory=False)
    raise ValueError(f"Unsupported dashboard table format for {path}. Use Parquet or CSV.")


def load_dashboard_summary_tables(
    summary_root: str | Path,
    *,
    allow_missing_optional: bool = True,
    skip_tables: Iterable[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Load standard metrics dashboard summary tables from one directory.

    Missing optional tab tables are returned as empty schema-correct tables by
    default. This lets the Streamlit dashboard open and show an empty-state tab
    when, for example, a large run has not written path summaries yet.
    ``skip_tables`` can force known-not-ready optional tables to the same empty
    schema without reading malformed or very large files.
    """

    root = Path(summary_root).expanduser()
    skipped = {str(table) for table in skip_tables or ()}
    tables: dict[str, pd.DataFrame] = {}
    for name in METRICS_TABLES:
        if name in skipped:
            tables[name] = _empty_dashboard_table(name)
            continue
        path = _find_table(root, name, required=not allow_missing_optional)
        tables[name] = _empty_dashboard_table(name) if path is None else read_dashboard_table(path)
    return tables


def load_filtered_dashboard_summary_table(
    summary_root: str | Path,
    table_name: str,
    *,
    models: Iterable[str] | None = None,
    metric: str | None = None,
    bands: Iterable[str] | None = None,
    periods_s: Iterable[float | str] | None = None,
    value_column: str | None = None,
    vs30_range: tuple[float | None, float | None] | None = None,
    distance_range_km: tuple[float | None, float | None] | None = None,
    component: str | None = None,
    max_rows: int | None = None,
    chunksize: int = 50_000,
    allow_missing_optional: bool = True,
) -> pd.DataFrame:
    """Load one filtered dashboard summary table in chunks.

    This is intended for Streamlit tabs that need station, event, or path
    summaries after the user has selected a model, metric, passband, period, or
    component. It avoids materializing large optional summary tables at
    dashboard startup while preserving the same filter semantics as in-memory
    summary filtering.
    """

    name = str(table_name)
    if name not in METRICS_TABLES:
        raise KeyError(f"Unknown dashboard summary table: {name}")
    root = Path(summary_root).expanduser()
    path = _find_table(root, name, required=not allow_missing_optional)
    if path is None:
        return _empty_dashboard_table(name)
    columns = _dashboard_table_columns(path)
    missing = [column for column in REQUIRED_METRICS_TABLE_COLUMNS[name] if column not in columns]
    if missing or (value_column and value_column not in columns):
        return pd.DataFrame(columns=columns)

    from spatial_vtk.visualize.dashboard.filters import filter_dashboard_metrics

    frames: list[pd.DataFrame] = []
    remaining = None if max_rows is None else max(int(max_rows), 0)
    for chunk in _iter_dashboard_table_column_chunks(path, columns, chunksize=chunksize):
        filtered = filter_dashboard_metrics(
            chunk,
            models=models,
            metric=metric,
            bands=bands,
            periods_s=periods_s,
            value_column=value_column,
            vs30_range=vs30_range,
            distance_range_km=distance_range_km,
            component=component,
        )
        if filtered.empty:
            continue
        if remaining is not None:
            if remaining <= 0:
                break
            filtered = filtered.head(remaining)
            remaining -= len(filtered)
        frames.append(filtered)
        if remaining == 0:
            break
    if not frames:
        return pd.DataFrame(columns=columns)
    return pd.concat(frames, ignore_index=True)


def preview_dashboard_summary_tables(
    summary_root: str | Path | None = None,
    *,
    cfg: ConfigInput | None = None,
    nrows: int = 5,
    missing: str = "skip",
    create_parent: bool = True,
    format: str = "parquet",
) -> dict[str, pd.DataFrame]:
    """Return bounded previews for configured dashboard summary tables.

    The helper resolves the dashboard summary directory from the active config
    when ``summary_root`` is omitted and reads at most ``nrows`` per table. It
    is intended for notebooks that need to inspect dashboard-tab inputs without
    loading full large-run summary tables or resolving per-file paths in cells.

    Parameters
    ----------
    summary_root
        Optional dashboard summary directory. When omitted, the configured
        ``dashboard_summaries`` output path is used.
    cfg
        Optional Spatial-VTK config object or config file path used when
        ``summary_root`` is omitted.
    nrows
        Maximum rows to read from each existing summary table.
    missing
        ``"skip"`` to omit missing tables, or ``"raise"`` to fail on the first
        missing table.
    create_parent, format
        Forwarded to :func:`dashboard_summary_table_paths`.

    Returns
    -------
    dict
        Mapping from dashboard summary table name to bounded dataframe preview.
    """

    if missing not in {"skip", "raise"}:
        raise ValueError("missing must be 'skip' or 'raise'.")
    from spatial_vtk.io.tables import read_bounded_table

    paths = dashboard_summary_table_paths(
        summary_root,
        cfg=cfg,
        create_parent=create_parent,
        format=format,
    )
    previews: dict[str, pd.DataFrame] = {}
    for key, path in paths.items():
        name = key.removesuffix("_summary_path")
        if not path.exists():
            if missing == "raise":
                raise FileNotFoundError(f"Dashboard summary table does not exist: {path}")
            continue
        previews[name] = read_bounded_table(path, max_rows=nrows)
    return previews


def display_dashboard_output_previews(
    *,
    cfg: ConfigInput | None = None,
    nrows: int = 5,
    include_metrics_long: bool = True,
    missing: str = "skip",
    display_fn: Any | None = None,
) -> dict[str, pd.DataFrame]:
    """Display bounded previews for dashboard-ready outputs.

    The helper is intended for tutorial notebooks after dashboard datasets have
    been built. It keeps cells from repeating summary-table path resolution,
    ``metrics_long`` path checks, and ``display`` fallback handling. Only
    bounded previews are read, so it is safe for large-run notebooks.

    Parameters
    ----------
    cfg
        Optional Spatial-VTK config object or config file path. When omitted,
        the active config is used by the output resolvers.
    nrows
        Maximum rows to read from each dashboard artifact.
    include_metrics_long
        Whether to include a bounded preview of the configured ``metrics_long``
        source table alongside the dashboard summary tables.
    missing
        ``"skip"`` to print not-ready messages for missing artifacts, or
        ``"raise"`` to fail on the first missing artifact.
    display_fn
        Optional display function. When omitted, IPython's ``display`` is used
        when available, otherwise dataframes are printed as plain text.

    Returns
    -------
    dict
        Mapping from artifact label to preview dataframe.
    """

    if missing not in {"skip", "raise"}:
        raise ValueError("missing must be 'skip' or 'raise'.")

    from spatial_vtk.io.tables import read_bounded_table

    display = _dashboard_display(display_fn)
    previews: dict[str, pd.DataFrame] = {}

    summary_previews = preview_dashboard_summary_tables(cfg=cfg, nrows=nrows, missing=missing)
    if summary_previews:
        for table_name, preview in summary_previews.items():
            label = f"dashboard_summary:{table_name}"
            previews[label] = preview
            print(f"{label} preview:")
            _display_dashboard_preview(preview, display)
    else:
        print("Dashboard summary tables are not ready yet.")

    if include_metrics_long:
        metrics_long_path = dashboard_output_paths(cfg=cfg, create_parent=False, include_summary_tables=False)[
            "metrics_long_path"
        ]
        if metrics_long_path.exists():
            preview = read_bounded_table(metrics_long_path, max_rows=nrows)
            previews["metrics_long"] = preview
            print("metrics_long preview:")
            _display_dashboard_preview(preview, display)
        elif missing == "raise":
            raise FileNotFoundError(f"Dashboard source table does not exist: {metrics_long_path}")
        else:
            print(f"metrics_long table is not ready yet: {metrics_long_path}")

    return previews


def dashboard_summary_table_paths(
    summary_root: str | Path | None = None,
    *,
    cfg: ConfigInput | None = None,
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
    cfg: ConfigInput | None = None,
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
    cfg: ConfigInput | None = None,
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
    cfg: ConfigInput | None = None,
    create_parent: bool = True,
    include_summary_tables: bool = True,
    summary_format: str = "parquet",
) -> pd.DataFrame:
    """Return file readiness for standard dashboard inputs and summaries.

    ``resolved_path`` is the clear notebook-facing path column. ``path`` is
    retained as a compatibility alias for existing dashboard code and user
    notebooks.
    """

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
    status = _attach_dashboard_contract(status)
    status = _attach_dashboard_readiness(status)
    status = _attach_metric_dataset_readiness(status)
    return _attach_qc_trace_readiness(status)


def dashboard_readiness_summary_frame(
    *,
    cfg: ConfigInput | None = None,
    readiness: DashboardOutputReadiness | None = None,
    overwrite: bool = False,
    create_parent: bool = True,
    summary_format: str = "parquet",
) -> pd.DataFrame:
    """Return a compact dashboard/tab readiness summary.

    This is intended for notebooks and preflight displays where users need to
    know which dashboard tabs are ready and why a tab may be blank. The helper
    reuses :func:`dashboard_output_readiness`, so it inspects only paths,
    table metadata, schemas, row counts, and selected value/coordinate columns.
    It does not materialize full large-run metric datasets.
    """

    decision = readiness or dashboard_output_readiness(
        cfg=cfg,
        overwrite=overwrite,
        create_parent=create_parent,
        summary_format=summary_format,
    )
    rows: list[dict[str, object]] = []

    for row in decision.input_status.astype(object).to_dict("records"):
        name = str(row.get("name", ""))
        exists = bool(row.get("exists", False))
        label = str(_blank_if_missing(row.get("artifact_label")) or name)
        ready = dashboard_ready_value(row.get("ready"), default=exists)
        readiness = str(_blank_if_missing(row.get("readiness")) or ("ready" if ready else "missing"))
        message = str(_blank_if_missing(row.get("message")) or (f"{label} is ready." if ready else f"{label} is missing."))
        suggested_action = _blank_if_missing(row.get("suggested_action"))
        if not ready and not suggested_action:
            suggested_action = _dashboard_suggested_action(
                {"name": name, "artifact_role": row.get("artifact_role", ""), "readiness": readiness}
            )
        rows.append(
            {
                "item_type": "input",
                "item": label,
                "artifact_role": _blank_if_missing(row.get("artifact_role")),
                "artifact_label": label,
                "dashboard_table": "",
                "dashboard_tabs": "Dashboard preparation",
                "required_columns": "",
                "ready": ready,
                "readiness": readiness,
                "tab_ready": ready,
                "row_count": "",
                "file_count": "",
                "map_ready": "",
                "missing_columns": "",
                "missing_map_columns": "",
                "value_columns": "",
                "nonempty_value_columns": "",
                "value_families": "",
                "nonempty_value_families": "",
                "message": message,
                "tab_message": message,
                "suggested_action": suggested_action,
                "resolved_path": row.get("resolved_path", row.get("path", "")),
                "path": row.get("path", ""),
            }
        )

    for row in decision.metrics_status.astype(object).to_dict("records"):
        rows.append(_dashboard_summary_row(row, item_type="dataset"))

    for row in decision.summary_status.astype(object).to_dict("records"):
        rows.append(_dashboard_summary_row(row, item_type="summary_table"))

    if decision.qc_status is not None and not decision.qc_status.empty:
        for row in decision.qc_status.astype(object).to_dict("records"):
            rows.append(_dashboard_summary_row(row, item_type="qc_table"))

    columns = [
        "item_type",
        "item",
        "artifact_role",
        "artifact_label",
        "dashboard_table",
        "dashboard_tabs",
        "required_columns",
        "ready",
        "readiness",
        "tab_ready",
        "row_count",
        "file_count",
        "map_ready",
        "missing_columns",
        "missing_map_columns",
        "value_columns",
        "nonempty_value_columns",
        "value_families",
        "nonempty_value_families",
        "message",
        "tab_message",
        "map_message",
        "suggested_action",
        "resolved_path",
        "path",
    ]
    return pd.DataFrame(rows, columns=columns)


def dashboard_metric_dataset_readiness_frame(metrics_root: str | Path) -> pd.DataFrame:
    """Return bounded readiness details for one dashboard metric dataset.

    This checks only the dataset directory, recognized table paths, parquet
    metadata, CSV line counts, and table schemas. It does not materialize the
    full metric rows, so it is safe to call from large-run notebooks.
    """

    path = Path(metrics_root).expanduser()
    row: dict[str, object] = {
        "kind": "dashboard_metrics",
        "name": "metrics_dashboard_root",
        "artifact_role": "dashboard_dataset",
        "artifact_label": "metrics dashboard row dataset",
        "resolved_path": str(path),
        "path": str(path),
        "exists": path.exists(),
        "ready": False,
        "readiness": "missing",
        "file_count": 0,
        "row_count": "",
        "value_columns": "",
        "value_families": "",
        "message": f"Dashboard metric dataset root is missing: {path}",
        "suggested_action": _dashboard_suggested_action({"name": "metrics_dashboard_root", "readiness": "missing"}),
    }
    if not path.exists():
        return pd.DataFrame([row])
    files = _dashboard_metric_files(path)
    row["file_count"] = len(files)
    if not files:
        row.update(
            {
                "readiness": "missing_dataset_files",
                "message": (
                    "Dashboard metric dataset contains no recognized files. "
                    "Expected metrics_long.parquet or model=*/band=*/metric=*/part.parquet."
                ),
                "suggested_action": _dashboard_suggested_action(
                    {"name": "metrics_dashboard_root", "readiness": "missing_dataset_files"}
                ),
            }
        )
        return pd.DataFrame([row])
    try:
        row_count = sum(_dashboard_metric_row_count(file_path) for file_path in files)
        columns = _dashboard_metric_column_union(files)
    except Exception as exc:  # pragma: no cover - integration guardrail
        row.update(
            {
                "readiness": "read_error",
                "row_count": "",
                "message": f"Dashboard metric dataset could not be inspected: {exc}",
                "suggested_action": _dashboard_suggested_action({"name": "metrics_dashboard_root", "readiness": "read_error"}),
            }
        )
        return pd.DataFrame([row])
    value_columns = _dashboard_value_columns(pd.DataFrame(columns=columns))
    value_families = dashboard_value_column_families(value_columns)
    row["row_count"] = row_count
    row["value_columns"] = ", ".join(value_columns)
    row["value_families"] = ", ".join(value_families)
    if row_count <= 0:
        row.update(
            {
                "readiness": "empty",
                "message": "Dashboard metric dataset has no rows.",
                "suggested_action": _dashboard_suggested_action({"name": "metrics_dashboard_root", "readiness": "empty"}),
            }
        )
    elif not value_columns:
        row.update(
            {
                "readiness": "no_value_columns",
                "message": "Dashboard metric dataset has rows but no recognized residual/score/value columns.",
                "suggested_action": _dashboard_suggested_action(
                    {"name": "metrics_dashboard_root", "readiness": "no_value_columns"}
                ),
            }
        )
    else:
        row.update({"ready": True, "readiness": "ready", "message": "Dashboard metric dataset is ready.", "suggested_action": ""})
    return pd.DataFrame([row])


def _rebuildable_dashboard_map_tables(summary_status: pd.DataFrame, metrics_long_path: Path) -> list[str]:
    """Return summary tables whose missing map columns can be rebuilt from source metrics."""

    if summary_status.empty or not metrics_long_path.exists():
        return []
    required = {"dashboard_table", "map_ready"}
    if not required <= set(summary_status.columns):
        return []
    try:
        source_columns = set(_dashboard_table_columns(metrics_long_path))
    except Exception:
        return []
    tables: list[str] = []
    for _, row in summary_status.iterrows():
        table_name = str(row.get("dashboard_table") or "")
        if table_name not in MAP_COORDINATE_CANDIDATES:
            continue
        if dashboard_ready_value(row.get("map_ready"), default=True):
            continue
        lon_candidates, lat_candidates = MAP_COORDINATE_CANDIDATES[table_name]
        has_lon = any(column in source_columns for column in lon_candidates)
        has_lat = any(column in source_columns for column in lat_candidates)
        if has_lon and has_lat:
            tables.append(table_name)
    return sorted(dict.fromkeys(tables))


def dashboard_qc_trace_readiness_frame(
    trace_summary: str | Path | None = None,
    *,
    cfg: ConfigInput | None = None,
    create_parent: bool = True,
) -> pd.DataFrame:
    """Return bounded readiness details for the QC dashboard trace table.

    The check reads only table headers and row counts, so it is safe for large
    CSV or Parquet trace-summary tables. The QC dashboard can still render
    optional charts with additional columns when they exist, but ``event_id``
    and ``station`` are the minimum required columns for a useful dashboard.
    """

    path = (
        Path(trace_summary).expanduser()
        if trace_summary is not None
        else resolve_output_path("qc_trace_summary", kind="table", cfg=cfg, create_parent=create_parent)
    )
    return _attach_qc_trace_readiness(pd.DataFrame(_status_rows({"qc_trace_summary_path": path})))


def dashboard_output_readiness(
    *,
    cfg: ConfigInput | None = None,
    overwrite: bool = False,
    create_parent: bool = True,
    summary_format: str = "parquet",
) -> DashboardOutputReadiness:
    """Return the rebuild decision for dashboard metric and summary outputs.

    The decision checks the configured ``metrics_long`` input, verifies that
    the dashboard metric dataset contains recognized row files, and validates
    each summary table needed by the Streamlit metrics dashboard. Existing
    output directories alone are not treated as complete outputs.
    """

    paths = dashboard_output_paths(
        cfg=cfg,
        create_parent=create_parent,
        include_summary_tables=True,
        summary_format=summary_format,
    )
    metrics_long_path = paths["metrics_long_path"]
    metrics_root = paths["metrics_dashboard_root"]
    summary_root = paths["dashboard_summary_root"]
    input_status = _dashboard_input_status_frame({"metrics_long_path": metrics_long_path})
    qc_status = dashboard_qc_trace_readiness_frame(
        paths["qc_trace_summary_path"],
        cfg=cfg,
        create_parent=create_parent,
    )
    if not metrics_long_path.exists():
        return DashboardOutputReadiness(
            should_run=False,
            reason="missing_inputs",
            message="metrics_long.parquet is not ready yet; finish Step 3 first.",
            metrics_status=dashboard_metric_dataset_readiness_frame(metrics_root),
            summary_status=dashboard_summary_readiness_frame(
                summary_root,
                cfg=cfg,
                create_parent=create_parent,
                summary_format=summary_format,
            ),
            input_status=input_status,
            qc_status=qc_status,
        )
    metrics_status = dashboard_metric_dataset_readiness_frame(metrics_root)
    summary_status = dashboard_summary_readiness_frame(
        summary_root,
        cfg=cfg,
        create_parent=create_parent,
        summary_format=summary_format,
    )
    metrics_ready = bool(metrics_status["ready"].iloc[0]) if "ready" in metrics_status.columns else False
    summary_ready_mask = (
        _dashboard_summary_output_ready_mask(summary_status, metrics_long_path)
        if "ready" in summary_status.columns
        else pd.Series(dtype=bool)
    )
    summaries_ready = bool(summary_ready_mask.all()) if not summary_ready_mask.empty else False
    stale = _dashboard_outputs_stale(metrics_long_path, metrics_root, summary_status)
    if overwrite:
        return DashboardOutputReadiness(
            should_run=True,
            reason="overwrite",
            message="Overwrite requested; rebuilding dashboard datasets.",
            metrics_status=metrics_status,
            summary_status=summary_status,
            input_status=input_status,
            qc_status=qc_status,
        )
    if not metrics_ready:
        return DashboardOutputReadiness(
            should_run=True,
            reason="missing_outputs",
            message=str(metrics_status["message"].iloc[0]),
            metrics_status=metrics_status,
            summary_status=summary_status,
            input_status=input_status,
            qc_status=qc_status,
        )
    if not summaries_ready:
        missing = summary_status.loc[~summary_ready_mask, ["dashboard_table", "message"]]
        first_message = str(missing["message"].iloc[0]) if not missing.empty else "Dashboard summary tables are not ready."
        return DashboardOutputReadiness(
            should_run=True,
            reason="missing_outputs",
            message=first_message,
            metrics_status=metrics_status,
            summary_status=summary_status,
            input_status=input_status,
            qc_status=qc_status,
        )
    incomplete_maps = _rebuildable_dashboard_map_tables(summary_status, metrics_long_path)
    if incomplete_maps:
        table_text = ", ".join(incomplete_maps)
        return DashboardOutputReadiness(
            should_run=True,
            reason="map_incomplete",
            message=(
                f"Dashboard summary maps are missing coordinate columns for {table_text}, "
                "but metrics_long contains the coordinates needed to rebuild them."
            ),
            metrics_status=metrics_status,
            summary_status=summary_status,
            input_status=input_status,
            qc_status=qc_status,
        )
    if stale:
        return DashboardOutputReadiness(
            should_run=True,
            reason="stale_sources",
            message="metrics_long.parquet is newer than one or more dashboard outputs; rebuilding.",
            metrics_status=metrics_status,
            summary_status=summary_status,
            input_status=input_status,
            qc_status=qc_status,
        )
    return DashboardOutputReadiness(
        should_run=False,
        reason="current",
        message="Dashboard datasets are current; skipping.",
        metrics_status=metrics_status,
        summary_status=summary_status,
        input_status=input_status,
        qc_status=qc_status,
    )


def dashboard_summary_readiness_frame(
    summary_root: str | Path | None = None,
    *,
    cfg: ConfigInput | None = None,
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
        resolved = str(path)
        artifact_role, artifact_label = _dashboard_artifact_role_and_label(str(name))
        row: dict[str, object] = {
            "name": str(name),
            "artifact_role": artifact_role,
            "artifact_label": artifact_label,
            "resolved_path": resolved,
            "path": resolved,
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


def _dashboard_input_status_frame(paths: dict[str, str | Path]) -> pd.DataFrame:
    """Return readiness rows for dashboard source inputs."""

    status = pd.DataFrame(_status_rows(paths))
    if status.empty:
        return status
    out = status.copy()
    for column in ("ready", "readiness", "message", "suggested_action"):
        if column not in out.columns:
            out[column] = pd.Series([pd.NA] * len(out), index=out.index, dtype="object")
    for index, row in out.iterrows():
        exists = bool(row.get("exists", False))
        name = str(row.get("name", ""))
        label = str(row.get("artifact_label") or name)
        out.at[index, "ready"] = exists
        out.at[index, "readiness"] = "ready" if exists else "missing"
        out.at[index, "message"] = f"{label} is ready." if exists else f"{label} is missing."
        out.at[index, "suggested_action"] = "" if exists else _dashboard_suggested_action(
            {"name": name, "artifact_role": row.get("artifact_role", ""), "readiness": "missing"}
        )
    return out


def _normalize_dashboard_status_row(row: dict[str, object], *, item_type: str) -> dict[str, object]:
    """Return one stable notebook-facing dashboard readiness row."""

    normalized = dict(row)
    normalized["item_type"] = item_type
    name = str(_blank_if_missing(normalized.get("name")))
    if name and not _blank_if_missing(normalized.get("artifact_role")):
        role, label = _dashboard_artifact_role_and_label(name)
        normalized["artifact_role"] = role
        normalized["artifact_label"] = _blank_if_missing(normalized.get("artifact_label")) or label
    elif name and not _blank_if_missing(normalized.get("artifact_label")):
        normalized["artifact_label"] = name
    elif "artifact_label" not in normalized:
        normalized["artifact_label"] = ""

    resolved_path = _blank_if_missing(normalized.get("resolved_path", normalized.get("path", "")))
    path_alias = _blank_if_missing(normalized.get("path", resolved_path))
    if not resolved_path and path_alias:
        resolved_path = path_alias
    if not path_alias and resolved_path:
        path_alias = resolved_path
    normalized["resolved_path"] = resolved_path
    normalized["path"] = path_alias

    if "exists" not in normalized or _blank_if_missing(normalized.get("exists")) == "":
        normalized["exists"] = Path(str(resolved_path)).exists() if resolved_path else False
    if "ready" not in normalized or _blank_if_missing(normalized.get("ready")) == "":
        normalized["ready"] = bool(normalized.get("exists", False))
    if not _blank_if_missing(normalized.get("readiness")):
        normalized["readiness"] = "ready" if dashboard_ready_value(normalized.get("ready"), default=False) else "missing"
    if not _blank_if_missing(normalized.get("message")):
        label = str(_blank_if_missing(normalized.get("artifact_label")) or name or item_type)
        normalized["message"] = f"{label} is ready." if dashboard_ready_value(normalized.get("ready"), default=False) else f"{label} is missing."
    if "suggested_action" not in normalized:
        normalized["suggested_action"] = ""
    for column in ("dashboard_table", "dashboard_tabs", "required_columns", "purpose"):
        if column not in normalized:
            normalized[column] = ""
    return normalized


def _dashboard_status_column_order(rows: list[dict[str, object]]) -> list[str]:
    """Return stable status columns followed by any inspector-specific details."""

    preferred = [
        "item_type",
        "name",
        "artifact_role",
        "artifact_label",
        "dashboard_table",
        "dashboard_tabs",
        "required_columns",
        "ready",
        "readiness",
        "exists",
        "row_count",
        "file_count",
        "map_ready",
        "missing_columns",
        "missing_map_columns",
        "value_columns",
        "nonempty_value_columns",
        "value_families",
        "nonempty_value_families",
        "message",
        "tab_message",
        "map_message",
        "suggested_action",
        "resolved_path",
        "path",
        "size_gb",
        "modified",
        "purpose",
    ]
    present = {str(column) for row in rows for column in row}
    columns = [column for column in preferred if column in present]
    columns.extend(sorted(column for column in present if column not in set(columns)))
    return columns


def _dashboard_artifact_role_and_label(name: str) -> tuple[str, str]:
    """Return a human-readable role and label for one dashboard artifact name."""

    summary_suffix = "_summary_path"
    if name == "metrics_long_path":
        return "input_table", "metrics_long source table"
    if name == "qc_trace_summary_path":
        return "qc_table", "QC trace-summary table"
    if name == "qc_inventory_path":
        return "qc_table", "full QC inventory"
    if name == "qc_inventory_overlap_path":
        return "qc_table", "observed/synthetic overlap QC inventory"
    if name == "metrics_dashboard_root":
        return "dashboard_dataset", "metrics dashboard row dataset"
    if name == "dashboard_summary_root":
        return "dashboard_summary_dir", "dashboard summary table directory"
    if name.endswith(summary_suffix):
        table_name = name[: -len(summary_suffix)]
        return "dashboard_summary_table", f"{table_name} dashboard summary table"
    return "artifact", name


def _dashboard_summary_row(row: dict[str, object], *, item_type: str) -> dict[str, object]:
    """Return one compact dashboard readiness summary row."""

    item = str(row.get("dashboard_table") or row.get("name") or "")
    if item_type == "dataset" and item == "metrics_dashboard_root":
        item = "metrics_dashboard_dataset"
    tabs = str(row.get("dashboard_tabs") or "")
    if item_type == "dataset" and not tabs:
        tabs = "Overview, Compare Models, Stations, Events, Paths"
    message = str(row.get("message") or "")
    map_message = str(row.get("map_message") or "")
    ready = dashboard_ready_value(row.get("ready"), default=False)
    return {
        "item_type": item_type,
        "item": item,
        "artifact_role": _blank_if_missing(row.get("artifact_role")),
        "artifact_label": _blank_if_missing(row.get("artifact_label")),
        "dashboard_table": _blank_if_missing(row.get("dashboard_table")),
        "dashboard_tabs": tabs,
        "required_columns": _blank_if_missing(row.get("required_columns")),
        "ready": ready,
        "readiness": _blank_if_missing(row.get("readiness")),
        "row_count": _blank_if_missing(row.get("row_count")),
        "file_count": _blank_if_missing(row.get("file_count")),
        "map_ready": _blank_if_missing(row.get("map_ready")),
        "missing_columns": _blank_if_missing(row.get("missing_columns")),
        "missing_map_columns": _blank_if_missing(row.get("missing_map_columns")),
        "tab_ready": _blank_if_missing(row.get("tab_ready")),
        "value_columns": _blank_if_missing(row.get("value_columns")),
        "nonempty_value_columns": _blank_if_missing(row.get("nonempty_value_columns")),
        "value_families": _blank_if_missing(row.get("value_families")),
        "nonempty_value_families": _blank_if_missing(row.get("nonempty_value_families")),
        "message": message,
        "tab_message": _blank_if_missing(row.get("tab_message")),
        "map_message": map_message,
        "suggested_action": _blank_if_missing(row.get("suggested_action")),
        "resolved_path": _blank_if_missing(row.get("resolved_path", row.get("path"))),
        "path": _blank_if_missing(row.get("path")),
    }


def _blank_if_missing(value: object) -> object:
    """Return a display blank for missing scalar values."""

    try:
        missing = bool(pd.isna(value))
    except (TypeError, ValueError):
        missing = False
    if value is None or missing:
        return ""
    return value


def _dashboard_suggested_action(row: dict[str, object]) -> str:
    """Return one bounded remediation hint for a dashboard readiness row."""

    readiness = str(row.get("readiness") or "")
    if readiness == "ready":
        return ""
    name = str(row.get("name") or "")
    role = str(row.get("artifact_role") or "")
    dashboard_table = str(row.get("dashboard_table") or "")
    if name == "metrics_long_path":
        return "Finish the metric workflow outputs so the configured metrics_long table exists."
    if name == "metrics_dashboard_root" or role == "dashboard_dataset":
        return "Run write_configured_dashboard_datasets or the Step 7 dashboard workflow to rebuild the row-level dashboard dataset."
    if name == "qc_trace_summary_path":
        return "Run the Step 2 QC workflow so qc_trace_summary exists with the required event/station/status columns."
    if role == "dashboard_summary_table" or dashboard_table:
        table_text = dashboard_table or "this summary table"
        return f"Run write_configured_dashboard_datasets or the Step 7 dashboard workflow to rebuild {table_text}."
    return "Rebuild this configured dashboard artifact from the active Spatial-VTK config."


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
        "tab_ready",
        "value_columns",
        "nonempty_value_columns",
        "value_families",
        "nonempty_value_families",
        "message",
        "tab_message",
        "map_message",
        "suggested_action",
    ):
        out[column] = pd.Series([pd.NA] * len(out), index=out.index, dtype="object")
    for index, row in out.iterrows():
        table_name = str(row.get("dashboard_table", ""))
        if not table_name:
            continue
        readiness = _inspect_dashboard_summary_table(_dashboard_status_path(row), table_name)
        for key, value in readiness.items():
            out.at[index, key] = value
    return out


def _attach_metric_dataset_readiness(status: pd.DataFrame) -> pd.DataFrame:
    """Attach metrics-dashboard dataset readiness to the dataset-root row."""

    if status.empty or "name" not in status.columns:
        return status
    out = status.copy()
    defaults = {
        "ready": pd.NA,
        "readiness": pd.NA,
        "row_count": pd.NA,
        "file_count": pd.NA,
        "value_columns": pd.NA,
        "value_families": pd.NA,
        "message": pd.NA,
        "suggested_action": pd.NA,
        "dashboard_table": "",
        "dashboard_tabs": "",
        "required_columns": "",
        "purpose": "",
    }
    for column, value in defaults.items():
        if column not in out.columns:
            out[column] = pd.Series([value] * len(out), index=out.index, dtype="object")
    mask = out["name"].astype(str).eq("metrics_dashboard_root")
    if not mask.any():
        return out
    out.loc[mask, "dashboard_table"] = "metrics_dashboard_dataset"
    out.loc[mask, "dashboard_tabs"] = "Overview, Compare Models, Stations, Events, Paths"
    out.loc[mask, "required_columns"] = "recognized residual/score/value column"
    out.loc[mask, "purpose"] = "Partitioned or single-file long metric dataset used by all metrics dashboard tabs."
    for index, row in out.loc[mask].iterrows():
        readiness = dashboard_metric_dataset_readiness_frame(_dashboard_status_path(row)).iloc[0].to_dict()
        for key in ("ready", "readiness", "file_count", "row_count", "value_columns", "value_families", "message", "suggested_action"):
            out.at[index, key] = readiness.get(key, pd.NA)
    return out


def _attach_qc_trace_readiness(status: pd.DataFrame) -> pd.DataFrame:
    """Attach QC dashboard trace-summary readiness to matching status rows."""

    if status.empty or "name" not in status.columns:
        return status
    out = status.copy()
    defaults = {
        "dashboard_table": "",
        "dashboard_tabs": "",
        "required_columns": "",
        "purpose": "",
        "ready": pd.NA,
        "readiness": pd.NA,
        "row_count": pd.NA,
        "missing_columns": pd.NA,
        "message": pd.NA,
        "suggested_action": pd.NA,
    }
    for column, value in defaults.items():
        if column not in out.columns:
            out[column] = pd.Series([value] * len(out), index=out.index, dtype="object")
    mask = out["name"].astype(str).eq("qc_trace_summary_path")
    if not mask.any():
        return out
    out.loc[mask, "dashboard_table"] = "qc_trace_summary"
    out.loc[mask, "dashboard_tabs"] = "QC Overview, Charts, Review Queue"
    out.loc[mask, "required_columns"] = ", ".join(REQUIRED_TRACE_QC_TABLE_COLUMNS)
    out.loc[mask, "purpose"] = "Trace-level QC decisions used by the QC dashboard and manual-review queue."
    for index, row in out.loc[mask].iterrows():
        readiness = _inspect_qc_trace_summary_table(_dashboard_status_path(row))
        for key, value in readiness.items():
            out.at[index, key] = value
    return out


def _dashboard_status_path(row: Any) -> Path:
    """Return the configured path from one dashboard status row."""

    value = row.get("resolved_path", None)
    try:
        missing = bool(pd.isna(value))
    except (TypeError, ValueError):
        missing = False
    if value is None or missing:
        value = row.get("path", "")
    return Path(str(value))


def _inspect_qc_trace_summary_table(path: Path) -> dict[str, object]:
    """Return readiness details for one QC trace-summary table path."""

    required = set(REQUIRED_TRACE_QC_TABLE_COLUMNS)
    if not path.exists():
        return {
            "ready": False,
            "readiness": "missing",
            "row_count": "",
            "missing_columns": ", ".join(REQUIRED_TRACE_QC_TABLE_COLUMNS),
            "message": f"QC trace-summary table is missing: {path}",
            "suggested_action": _dashboard_suggested_action({"name": "qc_trace_summary_path", "readiness": "missing"}),
        }
    try:
        columns = _dashboard_table_columns(path)
        row_count = _dashboard_table_row_count(path)
    except Exception as exc:  # pragma: no cover - integration guardrail
        return {
            "ready": False,
            "readiness": "read_error",
            "row_count": "",
            "missing_columns": "",
            "message": f"QC trace-summary table could not be inspected: {exc}",
            "suggested_action": _dashboard_suggested_action({"name": "qc_trace_summary_path", "readiness": "read_error"}),
        }
    missing = sorted(column for column in required if column not in columns)
    if missing:
        return {
            "ready": False,
            "readiness": "missing_columns",
            "row_count": row_count,
            "missing_columns": ", ".join(missing),
            "message": f"QC trace-summary table is missing required columns: {', '.join(missing)}.",
            "suggested_action": _dashboard_suggested_action(
                {"name": "qc_trace_summary_path", "readiness": "missing_columns"}
            ),
        }
    if row_count == 0:
        return {
            "ready": False,
            "readiness": "empty",
            "row_count": row_count,
            "missing_columns": "",
            "message": "QC trace-summary table has no rows.",
            "suggested_action": _dashboard_suggested_action({"name": "qc_trace_summary_path", "readiness": "empty"}),
        }
    return {
        "ready": True,
        "readiness": "ready",
        "row_count": row_count,
        "missing_columns": "",
        "message": "QC trace-summary table is ready.",
        "suggested_action": "",
    }


def _inspect_dashboard_summary_table(path: Path, table_name: str) -> dict[str, object]:
    """Return readiness details for one dashboard summary table path."""

    required = set(REQUIRED_METRICS_TABLE_COLUMNS[table_name])
    if not path.exists():
        message = f"{table_name} summary file is missing."
        return {
            "ready": False,
            "readiness": "missing",
            "tab_ready": False,
            "row_count": "",
            "missing_columns": ", ".join(sorted(required)),
            "value_columns": "",
            "nonempty_value_columns": "",
            "value_families": "",
            "nonempty_value_families": "",
            "message": message,
            "tab_message": message,
            "suggested_action": _dashboard_suggested_action(
                {"dashboard_table": table_name, "artifact_role": "dashboard_summary_table", "readiness": "missing"}
            ),
        }
    try:
        columns = _dashboard_table_columns(path)
        row_count = _dashboard_table_row_count(path)
    except Exception as exc:  # pragma: no cover - exercised by integration failures
        message = f"{table_name} summary file could not be read: {exc}"
        return {
            "ready": False,
            "readiness": "read_error",
            "tab_ready": False,
            "row_count": "",
            "missing_columns": "",
            "value_columns": "",
            "nonempty_value_columns": "",
            "value_families": "",
            "nonempty_value_families": "",
            "message": message,
            "tab_message": message,
            "suggested_action": _dashboard_suggested_action(
                {"dashboard_table": table_name, "artifact_role": "dashboard_summary_table", "readiness": "read_error"}
            ),
        }
    missing = sorted(column for column in required if column not in columns)
    schema_table = pd.DataFrame(columns=columns)
    value_columns = _dashboard_value_columns(schema_table)
    value_families = dashboard_value_column_families(value_columns)
    map_status = _dashboard_map_readiness_from_path(path, table_name, columns)
    nonempty_value_columns = (
        []
        if missing or row_count == 0
        else _nonempty_dashboard_value_columns_from_path(path, value_columns)
    )
    nonempty_value_families = dashboard_value_column_families(nonempty_value_columns)
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
    tab_state = _dashboard_tab_state(
        ready=ready,
        table_name=table_name,
        message=message,
        map_ready=map_status["ready"],
        map_message=map_status["message"],
    )
    return {
        "ready": ready,
        "readiness": readiness,
        "tab_ready": tab_state["ready"],
        "row_count": row_count,
        "missing_columns": ", ".join(missing),
        "map_ready": map_status["ready"],
        "missing_map_columns": map_status["missing_columns"],
        "value_columns": ", ".join(value_columns),
        "nonempty_value_columns": ", ".join(nonempty_value_columns),
        "value_families": ", ".join(value_families),
        "nonempty_value_families": ", ".join(nonempty_value_families),
        "message": message,
        "tab_message": tab_state["message"],
        "map_message": map_status["message"],
        "suggested_action": _dashboard_suggested_action(
            {"dashboard_table": table_name, "artifact_role": "dashboard_summary_table", "readiness": readiness}
        ),
    }


def _dashboard_tab_state(
    *,
    ready: bool,
    table_name: str,
    message: str,
    map_ready: object,
    map_message: object,
) -> dict[str, object]:
    """Return actual dashboard-tab readiness for one summary table.

    ``ready`` tracks whether the summary data can populate tables/charts.
    ``tab_ready`` also accounts for map-coordinate requirements so station and
    event dashboard tabs do not appear ready when their tables have values but
    their maps cannot render.
    """

    if not bool(ready):
        return {"ready": False, "message": message}
    has_map_requirement = str(table_name) in MAP_COORDINATE_CANDIDATES
    if has_map_requirement and not dashboard_ready_value(map_ready, default=False):
        detail = str(map_message or "").strip()
        return {
            "ready": False,
            "message": detail or f"{table_name} summary data is ready, but the map is missing coordinates.",
        }
    return {"ready": True, "message": f"{table_name} dashboard tab is ready."}


def _dashboard_table_columns(path: Path) -> list[str]:
    """Return dashboard summary columns without loading row data."""

    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return parquet_table_columns(path)
    if suffix == ".csv":
        return list(pd.read_csv(path, nrows=0).columns)
    raise ValueError(f"Unsupported dashboard table format for {path}. Use Parquet or CSV.")


def _dashboard_metric_files(metrics_root: Path) -> list[Path]:
    """Return recognized metric dataset files under a dashboard root."""

    from spatial_vtk.visualize.dashboard.export import dashboard_metric_dataset_paths

    return dashboard_metric_dataset_paths(metrics_root)


def _dashboard_metric_columns(path: Path) -> list[str]:
    """Return one dashboard metric file's columns without loading rows."""

    return _dashboard_table_columns(path)


def _dashboard_metric_column_union(paths: Sequence[Path]) -> list[str]:
    """Return dashboard metric columns seen across all recognized dataset files."""

    columns: list[str] = []
    for path in paths:
        for column in _dashboard_metric_columns(path):
            if column not in columns:
                columns.append(column)
    return columns


def _dashboard_metric_row_count(path: Path) -> int:
    """Return one dashboard metric file row count without loading all data."""

    return _dashboard_table_row_count(path)


def _dashboard_outputs_stale(metrics_long_path: Path, metrics_root: Path, summary_status: pd.DataFrame) -> bool:
    """Return whether dashboard outputs are older than the metric source."""

    if not metrics_long_path.exists():
        return False
    source_mtime = metrics_long_path.stat().st_mtime
    output_paths = [path for path in _dashboard_metric_files(metrics_root) if path.exists()]
    if not summary_status.empty:
        output_paths.extend(
            path
            for path in (_dashboard_status_path(row) for _, row in summary_status.iterrows())
            if path.exists()
        )
    if not output_paths:
        return False
    return any(path.stat().st_mtime < source_mtime for path in output_paths)


def _dashboard_summary_output_ready_mask(summary_status: pd.DataFrame, metrics_long_path: Path) -> pd.Series:
    """Return summary-table readiness for dashboard output rebuild decisions."""

    if summary_status.empty or "ready" not in summary_status.columns:
        return pd.Series(dtype=bool)
    source_has_path_geometry: bool | None = None
    values: list[bool] = []
    for _, row in summary_status.iterrows():
        if dashboard_ready_value(row.get("ready"), default=False):
            values.append(True)
            continue
        table_name = str(row.get("dashboard_table") or "")
        readiness = str(row.get("readiness") or "")
        if table_name == "path_hex" and readiness in {"missing", "empty", "no_value_data", "missing_columns"}:
            if source_has_path_geometry is None:
                source_has_path_geometry = _dashboard_source_has_path_geometry(metrics_long_path)
            values.append(not source_has_path_geometry)
            continue
        values.append(False)
    return pd.Series(values, index=summary_status.index, dtype=bool)


def _dashboard_source_has_path_geometry(metrics_long_path: Path) -> bool:
    """Return whether the source metric table can build path-bin summaries."""

    if not metrics_long_path.exists():
        return False
    try:
        columns = set(_dashboard_table_columns(metrics_long_path))
    except Exception:
        return False
    return {"distance_km", "azimuth_deg"} <= columns


def _bool_status_series(series: pd.Series) -> pd.Series:
    """Return a bool series without pandas object downcast warnings."""

    return series.map(dashboard_ready_value).astype(bool)


def dashboard_ready_value(value: object, *, default: bool = False) -> bool:
    """Coerce one dashboard readiness value to bool.

    Parameters
    ----------
    value
        Readiness value from a status table. Booleans, numeric flags, common
        true/false strings, and missing values are supported.
    default
        Value returned for missing or blank inputs.

    Returns
    -------
    bool
        Parsed readiness flag.
    """

    try:
        missing = bool(pd.isna(value))
    except (TypeError, ValueError):
        missing = False
    if value is None or missing:
        return bool(default)
    if isinstance(value, str):
        text = value.strip().lower()
        if not text:
            return bool(default)
        if text in {"true", "1", "yes", "y", "ready", "pass"}:
            return True
        if text in {"false", "0", "no", "n", "missing", "empty", "fail", "failed"}:
            return False
    return bool(value)


def _dashboard_table_row_count(path: Path) -> int:
    """Return dashboard summary row count without materializing all columns."""

    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq", ".csv"}:
        return table_row_count(path)
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


def _iter_dashboard_table_column_chunks(
    path: Path,
    columns: list[str] | tuple[str, ...],
    *,
    chunksize: int = 50_000,
):
    """Yield projected dashboard table chunks for readiness scans."""

    selected = [column for column in columns if column]
    if not selected:
        return
    size = max(int(chunksize), 1)
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        try:
            import pyarrow.parquet as pq
        except Exception as exc:
            raise RuntimeError(
                f"Could not stream dashboard parquet table {path}: pyarrow is required. "
                "Install the package dependencies or write the table as CSV before dashboard readiness checks."
            ) from exc
        try:
            parquet = pq.ParquetFile(path)
            for batch in parquet.iter_batches(batch_size=size, columns=selected):
                yield batch.to_pandas()
            return
        except Exception as exc:
            raise RuntimeError(
                f"Could not stream dashboard parquet table {path}. "
                "Repair or rewrite the table before dashboard readiness checks."
            ) from exc
    if suffix == ".csv":
        wanted = set(selected)
        yield from pd.read_csv(path, usecols=lambda column: column in wanted, chunksize=size, low_memory=False)
        return
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
    for chunk in _iter_dashboard_table_column_chunks(path, [lon_col, lat_col]):
        coordinates = pd.DataFrame(
            {
                "lon": pd.to_numeric(chunk[lon_col], errors="coerce"),
                "lat": pd.to_numeric(chunk[lat_col], errors="coerce"),
            }
        )
        if not coordinates.dropna(subset=["lon", "lat"]).empty:
            return {"ready": True, "missing_columns": "", "message": f"{table_name} map coordinates are ready."}
    return {
        "ready": False,
        "missing_columns": "",
        "message": f"{table_name} summary has coordinate columns but no finite longitude/latitude pairs for the map.",
    }


def _nonempty_dashboard_value_columns_from_path(path: Path, columns: list[str]) -> list[str]:
    """Return value columns with finite values using chunked projected reads."""

    if not columns:
        return []
    found: set[str] = set()
    for chunk in _iter_dashboard_table_column_chunks(path, columns):
        for column in columns:
            if column in found or column not in chunk.columns:
                continue
            if pd.to_numeric(chunk[column], errors="coerce").notna().any():
                found.add(column)
        if len(found) == len(columns):
            break
    return [column for column in columns if column in found]


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


def dashboard_value_column_families(columns: Iterable[object]) -> tuple[str, ...]:
    """Return dashboard value families represented by one column collection.

    The readiness tables use this bounded schema-level check to tell users
    whether a dashboard dataset contains residuals, GOF scores, observed
    values, synthetic values, or only generic metric values without loading the
    full large-run table.
    """

    families: set[str] = set()
    for raw_column in columns:
        column = str(raw_column or "").strip().lower()
        if not column:
            continue
        if "value_obs" in column:
            families.add("observed")
        elif "value_syn" in column:
            families.add("synthetic")
        elif "gof" in column or "score" in column:
            families.add("score/gof")
        elif "residual" in column or "resid" in column:
            families.add("residual")
        elif column == "value" or column.endswith("_value"):
            families.add("metric value")
    return tuple(family for family in VALUE_COLUMN_FAMILY_ORDER if family in families)


def dashboard_empty_rows_message(row_label: str) -> str:
    """Return a consistent filtered-empty dashboard message."""

    return (
        f"No {row_label} rows match the selected filters. "
        "Clear or broaden the dashboard filters; if this was unexpected, check the Data Status tab."
    )


def dashboard_missing_columns_message(column_label: str, *, table_label: str = "loaded table") -> str:
    """Return a consistent missing-column dashboard message."""

    return (
        f"No {column_label} columns are available in the {table_label}. "
        "Check the Data Status tab and rebuild the dashboard summaries from the active config if the source schema is stale."
    )


def dashboard_chart_columns_or_message(
    df: pd.DataFrame,
    columns: Sequence[str],
    column_label: str,
    *,
    row_label: str,
    table_label: str = "loaded table",
) -> tuple[list[str], str | None]:
    """Return chart columns or an explicit dashboard empty-state message."""

    if df.empty:
        return [], dashboard_empty_rows_message(row_label)
    if not columns:
        return [], dashboard_missing_columns_message(column_label, table_label=table_label)
    return list(columns), None


def dashboard_value_columns_or_message(
    df: pd.DataFrame,
    *,
    row_label: str = "model/metric/passband-or-period",
) -> tuple[list[str], str | None]:
    """Return selectable dashboard value columns with a precise state message."""

    if df.empty:
        return [], dashboard_empty_rows_message(row_label)
    columns = _dashboard_value_columns(df)
    if not columns:
        return [], f"No observed, synthetic, residual, or score value columns are present in the {row_label} summary."
    nonempty = _nonempty_dashboard_value_columns(df, columns)
    if nonempty:
        return nonempty, None
    return (
        columns,
        f"The selected {row_label} rows have dashboard value columns, but all selected values are missing or non-finite.",
    )


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


def dashboard_row_level_columns() -> tuple[str, ...]:
    """Return long-metric columns needed by dashboard row-level tabs."""

    from spatial_vtk.visualize.dashboard.tables import DEFAULT_DASHBOARD_VALUE_COLUMNS

    columns = (
        "model",
        "metric",
        "band",
        "passband",
        "period_s",
        "component",
        "station",
        "event_id",
        "distance_km",
        "med_dist_km",
        "Vs30",
        "vs30",
        *DEFAULT_DASHBOARD_VALUE_COLUMNS,
    )
    return tuple(dict.fromkeys(columns))


def load_metric_long_table(
    metrics_root: str | Path,
    *,
    columns: Sequence[str] | None = None,
    models: Sequence[str] | str | None = None,
    bands: Sequence[str] | str | None = None,
    metrics: Sequence[str] | str | None = None,
    periods_s: Sequence[float | str] | float | str | None = None,
    component: str | None = None,
    distance_range_km: tuple[float | None, float | None] | None = None,
    vs30_range: tuple[float | None, float | None] | None = None,
    max_rows: int | None = None,
    chunksize: int = 50_000,
) -> pd.DataFrame:
    """Load the dashboard long metric table from a dataset root."""

    from spatial_vtk.visualize.dashboard.export import load_dashboard_metric_dataset

    return load_dashboard_metric_dataset(
        metrics_root,
        columns=columns,
        models=models,
        bands=bands,
        metrics=metrics,
        periods_s=periods_s,
        component=component,
        distance_range_km=distance_range_km,
        vs30_range=vs30_range,
        max_rows=max_rows,
        chunksize=chunksize,
    )


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


def _dashboard_display(display_fn: Any | None = None) -> Any | None:
    """Return a notebook display function when available."""

    if display_fn is not None:
        return display_fn
    try:
        from IPython.display import display as ipython_display

        return ipython_display
    except Exception:
        return None


def _display_dashboard_preview(preview: pd.DataFrame, display: Any | None) -> None:
    """Display or print one dashboard preview table."""

    if display is not None:
        display(preview)
    elif hasattr(preview, "to_string"):
        print(preview.to_string(index=False))
    else:
        print(preview)


def _require_columns(df: pd.DataFrame, columns: set[str], *, table_name: str) -> None:
    """Raise a clear error when required columns are missing."""

    missing = sorted(column for column in columns if column not in df.columns)
    if missing:
        raise ValueError(f"{table_name} is missing required columns: {missing}")


__all__ = [
    "METRICS_TABLES",
    "DashboardOutputReadiness",
    "MAP_COORDINATE_CANDIDATES",
    "MetricsDashboardPaths",
    "OPTIONAL_METRICS_TABLE_COLUMNS",
    "QCDashboardPaths",
    "REQUIRED_METRICS_TABLE_COLUMNS",
    "REQUIRED_TRACE_QC_TABLE_COLUMNS",
    "dashboard_metric_dataset_readiness_frame",
    "dashboard_output_paths",
    "dashboard_output_namespace",
    "dashboard_output_readiness",
    "dashboard_output_status_frame",
    "dashboard_qc_trace_readiness_frame",
    "dashboard_ready_value",
    "dashboard_readiness_summary_frame",
    "dashboard_row_level_columns",
    "dashboard_summary_readiness_frame",
    "dashboard_summary_table_contracts",
    "dashboard_summary_table_paths",
    "dashboard_chart_columns_or_message",
    "dashboard_empty_rows_message",
    "dashboard_missing_columns_message",
    "dashboard_value_columns_or_message",
    "dashboard_value_column_families",
    "dashboard_map_readiness",
    "display_dashboard_output_previews",
    "load_filtered_dashboard_summary_table",
    "load_dashboard_summary_tables",
    "load_metric_long_table",
    "preview_dashboard_summary_tables",
    "read_dashboard_table",
    "validate_dashboard_tables",
    "validate_map_columns",
    "validate_trace_qc_dashboard_table",
]
