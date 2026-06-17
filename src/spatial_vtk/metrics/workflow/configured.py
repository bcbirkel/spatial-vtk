"""Config-backed metric workflow entry points for notebooks and batch scripts.

Purpose
-------
This module mirrors the public metric CLI defaults as importable Python
functions. Large-run notebooks can call these helpers directly through
``run_or_submit_notebook_function()`` while keeping path resolution and Slurm
script writing inside the package.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.config.runtime import SpatialVTKConfig, active_config
from spatial_vtk.io import metric_plan_from_config
from spatial_vtk.io.preprocessing import preprocessed_waveform_metadata_paths
from spatial_vtk.io.tables import write_table
from spatial_vtk.metrics.workflow.execution import (
    merge_batch_outputs,
    metric_manifest_batch_status,
    write_task_manifest,
)
from spatial_vtk.metrics.workflow.inventory import build_metric_waveform_inventories_from_trace_metadata
from spatial_vtk.metrics.workflow.outputs import write_metric_outputs
from spatial_vtk.metrics.workflow.slurm import (
    slurm_settings_from_config,
    submit_metrics_slurm_job,
    write_metrics_slurm_script,
)
from spatial_vtk.metrics.workflow.tasks import plan_metric_tasks, tasks_to_frame


def build_metric_waveform_inventories_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    trace_metadata: str | Path | None = None,
    observed_output: str | Path | None = None,
    synthetic_output: str | Path | None = None,
    synthetic_model: str | None = None,
    observed_path_column: str = "output_file",
    synthetic_path_column: str = "input_file",
    overwrite: bool = True,
    verbose: bool = False,
) -> dict[str, object]:
    """Build observed/synthetic metric inventories from configured metadata."""

    config = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    trace_metadata_path = (
        Path(trace_metadata).expanduser()
        if trace_metadata is not None
        else preprocessed_waveform_metadata_paths(config=config).trace_metadata_path
    )
    observed_path = (
        Path(observed_output).expanduser()
        if observed_output is not None
        else resolve_output_path("observed_metric_inventory", kind="table", cfg=config, create_parent=True)
    )
    synthetic_path = (
        Path(synthetic_output).expanduser()
        if synthetic_output is not None
        else resolve_output_path("synthetic_metric_inventory", kind="table", cfg=config, create_parent=True)
    )
    result = build_metric_waveform_inventories_from_trace_metadata(
        trace_metadata_path,
        observed_path,
        synthetic_path,
        config=config,
        synthetic_model=synthetic_model,
        observed_path_column=observed_path_column,
        synthetic_path_column=synthetic_path_column,
        overwrite=overwrite,
        verbose=verbose,
    )
    return {
        "observed_path": str(result.observed_path),
        "synthetic_path": str(result.synthetic_path),
        "observed_rows": result.observed_rows,
        "synthetic_rows": result.synthetic_rows,
        "reused": bool(result.reused),
    }


def plan_metric_tasks_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    observed_inventory: str | Path | None = None,
    synthetic_inventory: str | Path | None = None,
    qc_table: str | Path | None = None,
    output: str | Path | None = None,
    manifest: bool = True,
    batch_output_dir: str | Path | None = None,
    batch_size: int = 100,
    batch_count: int | None = None,
    no_qc: bool = False,
    include_qc_failed_tasks: bool = False,
    overrides: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Plan metric tasks from configured inventories and optionally write a manifest."""

    config = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    observed_path = (
        Path(observed_inventory).expanduser()
        if observed_inventory is not None
        else resolve_output_path("observed_metric_inventory", kind="table", cfg=config, create_parent=True)
    )
    synthetic_path = (
        Path(synthetic_inventory).expanduser()
        if synthetic_inventory is not None
        else resolve_output_path("synthetic_metric_inventory", kind="table", cfg=config, create_parent=True)
    )
    qc_path = Path(qc_table).expanduser() if qc_table is not None else _default_metric_qc_table(config, no_qc=no_qc)
    output_path = (
        Path(output).expanduser()
        if output is not None
        else resolve_output_path("metric_manifest" if manifest else "metric_tasks", kind="table", cfg=config, create_parent=True)
    )
    plan = metric_plan_from_config(config, command="metrics.calculate", overrides=overrides or {})
    tasks = plan_metric_tasks(
        observed_path,
        synthetic_path,
        plan=plan,
        use_qc=not no_qc,
        qc_table=qc_path,
        require_passing_qc_pairs=not include_qc_failed_tasks,
    )
    payload: dict[str, object] = {
        "task_count": int(len(tasks)),
        "output": str(output_path),
        "observed_inventory": str(observed_path),
        "synthetic_inventory": str(synthetic_path),
        "qc_table": str(qc_path) if qc_path is not None else "",
        "manifest": bool(manifest),
    }
    if manifest:
        selected_batch_size = int(batch_size)
        if batch_count is not None:
            if int(batch_count) <= 0:
                raise ValueError("batch_count must be positive.")
            selected_batch_size = max(1, math.ceil(len(tasks) / int(batch_count)))
        batch_dir = Path(batch_output_dir).expanduser() if batch_output_dir is not None else _metric_workflow_dir(config, "metric_batches")
        written = write_task_manifest(
            tasks,
            output_path,
            output_dir=batch_dir,
            batch_size=selected_batch_size,
            qc_table=qc_path,
        )
        payload.update(
            {
                "manifest_path": str(written.manifest_path),
                "batch_count": int(len(written.batches)),
                "batch_size": int(selected_batch_size),
                "batch_output_dir": str(batch_dir),
            }
        )
    else:
        write_table(tasks_to_frame(tasks), output_path)
    return payload


def write_metrics_slurm_script_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    manifest: str | Path | None = None,
    output: str | Path | None = None,
    incomplete_only: bool = False,
    overwrite_batches: bool = False,
    submit: bool = False,
) -> dict[str, object]:
    """Write or submit a metric Slurm array script from configured defaults."""

    config = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    manifest_path = Path(manifest).expanduser() if manifest is not None else _default_metric_manifest_path(config, prefer_cached=True)
    output_path = Path(output).expanduser() if output is not None else _metric_slurm_script_path(config)
    settings = slurm_settings_from_config(config)
    status = metric_manifest_batch_status(manifest_path)
    batch_indices = status.missing_batches if incomplete_only else None
    if incomplete_only and status.all_complete and not overwrite_batches:
        return {
            "script_path": "",
            "submitted": False,
            "all_complete": True,
            "total_batches": int(status.total_batches),
            "missing_batches": 0,
            "message": "All metric batch outputs already exist; no Slurm script was written.",
        }
    if submit:
        submission = submit_metrics_slurm_job(
            manifest_path,
            output_path,
            settings,
            batch_indices=batch_indices,
            overwrite_batches=overwrite_batches,
        )
        return {
            "script_path": str(submission.script_path),
            "submitted": True,
            "returncode": int(submission.returncode),
            "stdout": submission.stdout,
            "stderr": submission.stderr,
            "total_batches": int(status.total_batches),
            "selected_batches": int(len(batch_indices) if batch_indices is not None else status.total_batches),
        }
    script = write_metrics_slurm_script(
        manifest_path,
        output_path,
        settings,
        batch_indices=batch_indices,
        overwrite_batches=overwrite_batches,
    )
    return {
        "script_path": str(script),
        "submitted": False,
        "total_batches": int(status.total_batches),
        "selected_batches": int(len(batch_indices) if batch_indices is not None else status.total_batches),
        "missing_batches": int(status.missing_count),
    }


def merge_metric_batches_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    manifest: str | Path | None = None,
    output: str | Path | None = None,
    require_all: bool = True,
) -> dict[str, object]:
    """Merge configured metric batch outputs into the standard metric row table."""

    config = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    manifest_path = Path(manifest).expanduser() if manifest is not None else _default_metric_manifest_path(config, prefer_cached=True)
    output_path = Path(output).expanduser() if output is not None else resolve_output_path("metric_rows", kind="table", cfg=config, create_parent=True)
    path = merge_batch_outputs(manifest_path, output_path, require_all=require_all)
    return {"metric_rows": str(path), "manifest": str(manifest_path)}


def write_metric_outputs_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    metric_rows: str | Path | None = None,
    events: str | Path | None = None,
    stations: str | Path | None = None,
    residual_column: str | None = None,
    score_column: str | None = None,
    table_format: str = "parquet",
    dashboard_partitioned: bool = True,
) -> dict[str, str]:
    """Write configured downstream metric tables and dashboard datasets."""

    config = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    metric_rows_path = Path(metric_rows).expanduser() if metric_rows is not None else resolve_output_path("metric_rows", kind="table", cfg=config, create_parent=True)
    events_path = Path(events).expanduser() if events is not None else _existing_output_path("prepared_events", config=config)
    stations_path = Path(stations).expanduser() if stations is not None else _existing_output_path("prepared_stations", config=config)
    written = write_metric_outputs(
        metric_rows_path,
        None,
        events=events_path,
        stations=stations_path,
        residual_column=residual_column,
        score_column=score_column,
        table_format=table_format,
        dashboard_partitioned=dashboard_partitioned,
    )
    return {key: str(path) for key, path in written.items()}


def _workflow_config(*, config_path: str | Path | None, run_scenario: str | None) -> SpatialVTKConfig:
    """Return an activated config for a metric workflow helper."""

    if config_path is not None:
        return SpatialVTKConfig.from_file(config_path, run_scenario=run_scenario).activate()
    cfg = active_config()
    if run_scenario:
        return SpatialVTKConfig.from_file(cfg.config_path, run_scenario=run_scenario).activate()
    return cfg


def _metric_workflow_dir(config: SpatialVTKConfig, name: str) -> Path:
    """Return a standard metric workflow directory below the configured output root."""

    root = config.path("outputs.root", must_exist=False) or (config.root_dir / "outputs")
    path = Path(root) / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _metric_slurm_script_path(config: SpatialVTKConfig) -> Path:
    """Return the standard metric Slurm script path."""

    root = config.path("outputs.root", must_exist=False) or (config.root_dir / "outputs")
    path = Path(root) / "slurm" / "step03_run_metrics.slurm"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _default_metric_manifest_path(config: SpatialVTKConfig, *, prefer_cached: bool = False) -> Path:
    """Return the configured metric manifest path, optionally preferring cached."""

    if prefer_cached:
        cached = resolve_output_path("metric_manifest_cached", kind="table", cfg=config, create_parent=True)
        if cached.exists():
            return cached
    return resolve_output_path("metric_manifest", kind="table", cfg=config, create_parent=True)


def _default_metric_qc_table(config: SpatialVTKConfig, *, no_qc: bool) -> Path | None:
    """Return the configured metric QC table, respecting no-QC mode."""

    if no_qc:
        return None
    overlap = resolve_output_path("qc_inventory_overlap", kind="table", cfg=config, create_parent=True)
    return overlap if overlap.exists() else resolve_output_path("qc_inventory", kind="table", cfg=config, create_parent=True)


def _existing_output_path(key: str, *, config: SpatialVTKConfig) -> Path | None:
    """Return one configured output path only when it already exists."""

    path = resolve_output_path(key, kind="table", cfg=config, create_parent=False)
    return path if path.exists() else None


__all__ = [
    "build_metric_waveform_inventories_from_config",
    "merge_metric_batches_from_config",
    "plan_metric_tasks_from_config",
    "write_metric_outputs_from_config",
    "write_metrics_slurm_script_from_config",
]
