"""Downstream output helpers for metric workflow rows.

Purpose
-------
This module turns file-based metric workflow rows into the standardized tables
used by enrichment, spatial analysis, maps, dashboards, and tutorial notebooks.

Usage examples
--------------
Write configured downstream outputs from Step 3 notebooks:
  ``from spatial_vtk.metrics import load_standard_metric_workflow_outputs``
  ``metric_outputs = load_standard_metric_workflow_outputs(cfg=cfg)``
  ``result = metric_outputs.write_configured_outputs(context=context)``

Use ``prepare_metric_workflow_outputs()`` and ``write_metric_outputs()``
directly only in custom scripts that already own metric rows and output paths.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from spatial_vtk.io import table_columns
from spatial_vtk.io.tables import read_table as read_disk_table


ConfigInput = Any | str | Path
METRIC_TEXT_COLUMNS: tuple[str, ...] = (
    "task_id",
    "event_id",
    "station",
    "component",
    "model",
    "passband",
    "metric_group",
    "metric",
    "obs_qc_status",
    "obs_qc_reason",
    "syn_qc_status",
    "syn_qc_reason",
    "comparison_qc_status",
    "comparison_qc_reason",
    "obs_waveform_path",
    "syn_waveform_path",
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

    from spatial_vtk.metrics.calculate.enrich import enrich_metric_table
    from spatial_vtk.spatial.calculate.paths import build_path_table, summarize_residuals_by_path_bin
    from spatial_vtk.visualize.dashboard import build_dashboard_summaries, prepare_dashboard_metric_table

    raw = _read_metric_table(metric_rows, columns=_metric_workflow_output_input_columns(metric_rows))
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
    cfg: ConfigInput | None = None,
    events: pd.DataFrame | str | Path | None = None,
    stations: pd.DataFrame | str | Path | None = None,
    residual_column: str | None = None,
    score_column: str | None = None,
    table_format: str = "parquet",
    dashboard_partitioned: bool = True,
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
        registered table and dashboard output paths from ``cfg`` or the active
        config are used.
    cfg
        Optional config object or config file path used to resolve registered
        outputs when ``output_dir`` is omitted. Passing this explicitly avoids
        relying on global active config state in scripts and configured
        workflow wrappers.
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
        band, and metric. Defaults to ``True`` so configured and CLI workflows
        use the large-run-safe dashboard layout.
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
    root = Path(output_dir).expanduser() if output_dir is not None else None
    if root is not None:
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
    output_paths = _metric_output_paths(root, suffix=suffix, cfg=cfg)
    metrics_path = _write_metric_rows(tables["metrics_long"], output_paths["metrics_long"])
    metrics_enriched_path = _write_metric_rows(tables["metrics_long"], output_paths["metrics_enriched"])
    path_table_path = _write_metric_rows(tables["path_table"], output_paths["path_table"])
    path_summary_path = _write_metric_rows(tables["path_summary"], output_paths["path_summary"])
    from spatial_vtk.visualize.dashboard import write_dashboard_metric_dataset, write_dashboard_summaries

    dashboard_root = write_dashboard_metric_dataset(
        tables["dashboard_metrics"],
        output_paths["dashboard_metrics"],
        partitioned=dashboard_partitioned,
    )
    dashboard_summary_paths = write_dashboard_summaries(
        tables["dashboard_summaries"],
        output_paths["dashboard_summaries"],
        format=fmt,
    )
    written: dict[str, Path] = {
        "metrics_long": metrics_path,
        "metrics_enriched": metrics_enriched_path,
        "path_table": path_table_path,
        "path_summary": path_summary_path,
        "dashboard_metrics": dashboard_root,
    }
    written.update({f"dashboard_summary_{name}": path for name, path in dashboard_summary_paths.items()})
    return written


def _metric_output_paths(root: Path | None, *, suffix: str, cfg: ConfigInput | None = None) -> dict[str, Path]:
    """Return metric downstream output paths for explicit or config-backed roots."""

    if root is not None:
        return {
            "metrics_long": root / f"metrics_long{suffix}",
            "metrics_enriched": root / f"metrics_enriched{suffix}",
            "path_table": root / f"path_table{suffix}",
            "path_summary": root / f"path_summary{suffix}",
            "dashboard_metrics": root / "dashboard_metrics",
            "dashboard_summaries": root / "dashboard_summaries",
        }
    config = cfg or _active_config()
    return {
        "metrics_long": _resolve_output_path("metrics_long", kind="table", cfg=config, create_parent=True),
        "metrics_enriched": _resolve_output_path("metrics_enriched", kind="table", cfg=config, create_parent=True),
        "path_table": _resolve_output_path("path_table", kind="table", cfg=config, create_parent=True),
        "path_summary": _resolve_output_path("path_summary", kind="table", cfg=config, create_parent=True),
        "dashboard_metrics": _resolve_output_path("metrics_dashboard", kind="dashboard", cfg=config, create_parent=True),
        "dashboard_summaries": _resolve_output_path("dashboard_summaries", kind="dashboard", cfg=config, create_parent=True),
    }


def metric_workflow_output_input_columns() -> tuple[str, ...]:
    """Return standard long metric-row columns needed for downstream outputs.

    Path-backed metric workflow rows can use this as a safe projection before
    enrichment, spatial path summaries, and dashboard exports. The list keeps
    common legacy coordinate aliases so older metric-row files still enrich
    correctly. Wide legacy metric matrices are detected separately and read in
    full because their ``*_obs``/``*_syn`` metric columns are data-dependent.
    """

    return tuple(
        dict.fromkeys(
            [
                *METRIC_TEXT_COLUMNS,
                "band",
                "period_s",
                "value",
                "value_obs",
                "value_syn",
                "residual",
                "log2_residual",
                "ln_residual",
                "anderson_2004_gof",
                "olsen_mayhew_gof",
                "score",
                "event_title",
                "event",
                "event_name",
                "event_lat",
                "event_lon",
                "event_latitude",
                "event_longitude",
                "station_name",
                "Station",
                "network",
                "sta_lat",
                "sta_lon",
                "station_lat",
                "station_lon",
                "station_latitude",
                "station_longitude",
                "lat",
                "lon",
                "latitude",
                "longitude",
                "distance_km",
                "azimuth_deg",
                "backazimuth_deg",
                "magnitude",
                "event_magnitude",
                "depth_km",
                "Vs30",
                "vs30",
                "geology_class",
            ]
        )
    )


def _read_metric_table(value: pd.DataFrame | str | Path, *, columns: Sequence[str] | None = None) -> pd.DataFrame:
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
    suffix = path.suffix.lower()
    if suffix not in {".csv", ".parquet", ".pq"}:
        raise ValueError(f"Unsupported metric workflow output table format for {path}. Use Parquet or CSV.")
    selected = _selected_existing_columns(path, columns)
    if selected is None:
        return read_disk_table(path)
    if suffix in {".parquet", ".pq"}:
        return read_disk_table(path, columns=selected)
    wanted = set(selected)
    return read_disk_table(path, usecols=lambda column: column in wanted)


def _metric_workflow_output_input_columns(value: pd.DataFrame | str | Path) -> tuple[str, ...] | None:
    """Return a projection for path-backed long metric rows."""

    if isinstance(value, pd.DataFrame):
        return None
    path = Path(value).expanduser()
    columns = _metric_table_columns(path)
    if "metric" not in columns:
        return None
    return metric_workflow_output_input_columns()


def _selected_existing_columns(path: Path, columns: Sequence[str] | None) -> list[str] | None:
    """Return requested columns that exist in a metric table."""

    if columns is None:
        return None
    requested = list(dict.fromkeys(str(column) for column in columns if str(column).strip()))
    if not requested:
        return []
    available = set(_metric_table_columns(path))
    return [column for column in requested if column in available]


def _metric_table_columns(path: Path) -> list[str]:
    """Return metric table columns without materializing row data."""

    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq", ".csv"}:
        return table_columns(path)
    raise ValueError(f"Unsupported metric workflow output table format for {path}. Use Parquet or CSV.")


def _active_config() -> Any:
    """Return the active config only when config-backed output paths are requested."""

    from spatial_vtk.config.runtime import active_config

    return active_config()


def _resolve_output_path(*args: Any, **kwargs: Any) -> Path:
    """Resolve configured metric output paths only when requested."""

    from spatial_vtk.config.outputs import resolve_output_path

    return resolve_output_path(*args, **kwargs)


def _write_metric_rows(*args: Any, **kwargs: Any) -> Path:
    """Write metric rows only when downstream metric outputs are produced."""

    from spatial_vtk.metrics.workflow.run import write_metric_rows

    return write_metric_rows(*args, **kwargs)


__all__ = [
    "metric_workflow_output_input_columns",
    "prepare_metric_workflow_outputs",
    "write_metric_outputs",
]
