"""Config-backed metric workflow entry points for notebooks and batch scripts.

Purpose
-------
This module mirrors the public metric CLI defaults as importable Python
functions. Large-run notebooks should normally start with
``load_standard_metric_workflow_outputs()`` and call that result object's
``run_*_step_if_needed()`` methods so readiness display, skip logic, local
execution, and Slurm script writing stay inside the package. Use the direct
helpers in this module from scripts or custom orchestration that already owns
the configured inputs and output paths.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from spatial_vtk.io.output_paths import OutputReadiness, output_readiness
from spatial_vtk.metrics.workflow.standard import (
    StandardMetricWorkflowOutputResult,
    load_standard_metric_workflow_outputs,
)


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

    from spatial_vtk.io.preprocessing import preprocessed_waveform_metadata_paths
    from spatial_vtk.metrics.workflow.inventory import build_metric_waveform_inventories_from_trace_metadata

    config = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    trace_metadata_path = (
        Path(trace_metadata).expanduser()
        if trace_metadata is not None
        else preprocessed_waveform_metadata_paths(config=config).trace_metadata_path
    )
    observed_path = (
        Path(observed_output).expanduser()
        if observed_output is not None
        else _resolve_output_path("observed_metric_inventory", kind="table", cfg=config, create_parent=True)
    )
    synthetic_path = (
        Path(synthetic_output).expanduser()
        if synthetic_output is not None
        else _resolve_output_path("synthetic_metric_inventory", kind="table", cfg=config, create_parent=True)
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
        "observed_metric_inventory_path": str(result.observed_path),
        "synthetic_metric_inventory_path": str(result.synthetic_path),
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

    from spatial_vtk.io.plans import metric_plan_from_config
    from spatial_vtk.metrics.workflow.execution import write_task_manifest
    from spatial_vtk.metrics.workflow.tasks import plan_metric_tasks, tasks_to_frame

    config = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    observed_path = (
        Path(observed_inventory).expanduser()
        if observed_inventory is not None
        else _resolve_output_path("observed_metric_inventory", kind="table", cfg=config, create_parent=True)
    )
    synthetic_path = (
        Path(synthetic_inventory).expanduser()
        if synthetic_inventory is not None
        else _resolve_output_path("synthetic_metric_inventory", kind="table", cfg=config, create_parent=True)
    )
    qc_path = Path(qc_table).expanduser() if qc_table is not None else _default_metric_qc_table(config, no_qc=no_qc)
    output_path = (
        Path(output).expanduser()
        if output is not None
        else _resolve_output_path("metric_manifest" if manifest else "metric_tasks", kind="table", cfg=config, create_parent=True)
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
        "metric_manifest_path" if manifest else "metric_tasks_path": str(output_path),
        "planned_output_path": str(output_path),
        "output": str(output_path),
        "observed_metric_inventory_path": str(observed_path),
        "synthetic_metric_inventory_path": str(synthetic_path),
        "metric_qc_table_path": str(qc_path) if qc_path is not None else "",
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
        manifest_status = written.status_frame().iloc[0].to_dict()
        payload.update(
            {
                "metric_manifest_path": str(written.manifest_path),
                "metric_manifest_batch_count": int(len(written.batches)),
                "metric_manifest_batch_size": int(selected_batch_size),
                "metric_manifest_batch_output_dir": str(batch_dir),
                "metric_manifest_min_tasks_per_batch": int(manifest_status["min_tasks_per_batch"]),
                "metric_manifest_max_tasks_per_batch": int(manifest_status["max_tasks_per_batch"]),
                "metric_manifest_first_batch_output": str(manifest_status["first_batch_output"]),
                "metric_manifest_last_batch_output": str(manifest_status["last_batch_output"]),
                "manifest_path": str(written.manifest_path),
                "batch_count": int(len(written.batches)),
                "batch_size": int(selected_batch_size),
                "batch_output_dir": str(batch_dir),
                "min_tasks_per_batch": int(manifest_status["min_tasks_per_batch"]),
                "max_tasks_per_batch": int(manifest_status["max_tasks_per_batch"]),
                "first_batch_output": str(manifest_status["first_batch_output"]),
                "last_batch_output": str(manifest_status["last_batch_output"]),
            }
        )
    else:
        write_table(tasks_to_frame(tasks), output_path)
    return payload


def metric_inventories_readiness_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    overwrite: bool = False,
    missing_input_message: str | None = None,
    current_message: str | None = "Metric waveform inventories are current; skipping.",
    rebuild_message: str | None = None,
) -> OutputReadiness:
    """Return readiness for configured observed/synthetic metric inventories.

    The metric inventory workflow depends on preprocessing trace metadata,
    which lives under the preprocessed waveform output root rather than the
    standard metric table directory. This helper keeps that dependency and the
    observed/synthetic inventory output contract in package code.
    """

    config = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    metric_outputs = load_standard_metric_workflow_outputs(cfg=config)
    trace_metadata_path = Path(metric_outputs.trace_metadata_path)
    return metric_outputs.outputs.readiness(
        ("observed_inventory_path", "synthetic_inventory_path"),
        inputs={"trace_metadata_path": trace_metadata_path},
        sources={"trace_metadata_path": trace_metadata_path},
        overwrite=overwrite,
        missing_input_message=missing_input_message or f"Trace metadata is not ready yet: {trace_metadata_path}",
        current_message=current_message,
        rebuild_message=rebuild_message,
    )


def metric_manifest_readiness_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    overwrite: bool = False,
    current_message: str | None = "Metric manifest is current; skipping planning.",
    rebuild_message: str | None = None,
) -> OutputReadiness:
    """Return readiness for planning the configured metric task manifest."""

    config = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    metric_outputs = load_standard_metric_workflow_outputs(cfg=config)
    return metric_outputs.outputs.readiness(
        "metric_manifest_path",
        inputs=("observed_inventory_path", "synthetic_inventory_path", "qc_inventory_overlap_path"),
        sources=("observed_inventory_path", "synthetic_inventory_path", "qc_inventory_overlap_path"),
        overwrite=overwrite,
        missing_input_message="Metric inventories or overlap QC are not ready yet.",
        current_message=current_message,
        rebuild_message=rebuild_message,
    )


def summarize_metric_snapshot_tasks_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    metric_snapshot: str | Path | None = None,
    task_output: str | Path | None = None,
    estimate_output: str | Path | None = None,
    seconds_per_task: float = 60.0,
    memory_gb_per_task: float = 2.0,
    cpus_per_task: int = 1,
    parallel_tasks: int | None = 4,
) -> dict[str, object]:
    """Write a task preview and resource estimate from a configured metric snapshot.

    This helper is for tutorial and review workflows that start from an
    already-calculated metric table rather than waveform inventories. It
    deduplicates event/station/component/model/passband combinations, writes the
    standard ``metric_tasks`` and ``metric_task_estimate`` tables, and returns a
    compact JSON-ready summary.
    """

    from spatial_vtk.io.tables import read_table, write_table
    from spatial_vtk.metrics.workflow.tasks import summarize_metric_tasks

    config = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    snapshot_path = (
        Path(metric_snapshot).expanduser()
        if metric_snapshot is not None
        else _configured_metric_snapshot(config)
    )
    task_path = (
        Path(task_output).expanduser()
        if task_output is not None
        else _resolve_output_path("metric_tasks", kind="table", cfg=config, create_parent=True)
    )
    estimate_path = (
        Path(estimate_output).expanduser()
        if estimate_output is not None
        else _resolve_output_path("metric_task_estimate", kind="table", cfg=config, create_parent=True)
    )
    snapshot = read_table(snapshot_path)
    tasks = _metric_snapshot_task_table(snapshot, config)
    estimate = summarize_metric_tasks(
        tasks,
        seconds_per_task=seconds_per_task,
        memory_gb_per_task=memory_gb_per_task,
        cpus_per_task=cpus_per_task,
        parallel_tasks=parallel_tasks,
    )
    write_table(tasks, task_path)
    write_table(estimate, estimate_path)
    return {
        "metric_tasks_path": str(task_path),
        "metric_task_estimate_path": str(estimate_path),
        "metric_snapshot_path": str(snapshot_path),
        "task_count": int(len(tasks)),
        "estimate_rows": int(len(estimate)),
    }


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

    from spatial_vtk.metrics.workflow.execution import metric_manifest_batch_status
    from spatial_vtk.metrics.workflow.slurm import (
        slurm_settings_from_config,
        submit_metrics_slurm_job,
        write_metrics_slurm_script,
    )

    config = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    manifest_path = Path(manifest).expanduser() if manifest is not None else _default_metric_manifest_path(config, prefer_cached=True)
    output_path = Path(output).expanduser() if output is not None else _metric_slurm_script_path(config)
    settings = slurm_settings_from_config(config)
    status = metric_manifest_batch_status(manifest_path)
    batch_indices = status.missing_batches if incomplete_only else None
    if incomplete_only and status.all_complete and not overwrite_batches:
        return {
            "metric_slurm_script_path": "",
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
            "metric_slurm_script_path": str(submission.script_path),
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
        "metric_slurm_script_path": str(script),
        "script_path": str(script),
        "submitted": False,
        "total_batches": int(status.total_batches),
        "selected_batches": int(len(batch_indices) if batch_indices is not None else status.total_batches),
        "missing_batches": int(status.missing_count),
    }


def metric_slurm_submission_readiness_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    manifest: str | Path | None = None,
    overwrite: bool = False,
) -> OutputReadiness | Any:
    """Return readiness for writing or submitting configured metric Slurm work.

    Standard Step 3 notebooks should call
    ``load_standard_metric_workflow_outputs(...).run_slurm_step_if_needed(...)``
    so the metric result object owns this readiness check and the Slurm script
    writing/submission branch. If the manifest is missing, the decision is a
    non-running ``OutputReadiness`` with the manifest shown as a missing input.
    Once the manifest exists, the decision reports missing metric batch outputs
    through ``metric_slurm_submission_readiness``. Use this direct readiness
    helper from scripts or custom orchestration that already owns execution
    control.
    """

    from spatial_vtk.metrics.workflow.execution import (
        metric_manifest_batch_status,
        metric_slurm_submission_readiness,
    )

    config = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    manifest_path = (
        Path(manifest).expanduser()
        if manifest is not None
        else _default_metric_manifest_path(config, prefer_cached=True)
    )
    script_path = _metric_slurm_script_path(config)
    if not manifest_path.exists():
        return output_readiness(
            {"metric_slurm_script_path": script_path},
            inputs={"metric_manifest_path": manifest_path},
            missing_input_message="Metric manifest is not ready yet.",
        )
    return metric_slurm_submission_readiness(metric_manifest_batch_status(manifest_path), overwrite=overwrite)


def metric_batch_merge_readiness_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    manifest: str | Path | None = None,
    output: str | Path | None = None,
    overwrite: bool = False,
    missing_batch_display_limit: int = 20,
) -> OutputReadiness:
    """Return readiness for merging configured metric batch outputs."""

    from spatial_vtk.metrics.workflow.execution import metric_manifest_batch_status

    config = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    manifest_path = (
        Path(manifest).expanduser()
        if manifest is not None
        else _default_metric_manifest_path(config, prefer_cached=True)
    )
    output_path = (
        Path(output).expanduser()
        if output is not None
        else _resolve_output_path("metric_rows", kind="table", cfg=config, create_parent=True)
    )
    if not manifest_path.exists():
        return output_readiness(
            {"metric_rows_path": output_path},
            inputs={"metric_manifest_path": manifest_path},
            missing_input_message="Metric manifest is not ready yet.",
        )
    status = metric_manifest_batch_status(manifest_path)
    if not status.all_complete:
        batch_inputs = {"metric_manifest_path": manifest_path}
        missing_pairs = tuple(zip(status.missing_batches, status.missing_outputs))
        if missing_batch_display_limit >= 0:
            missing_pairs = missing_pairs[:missing_batch_display_limit]
        batch_inputs.update({f"metric_batch_{index:04d}_path": path for index, path in missing_pairs})
        display_suffix = ""
        if 0 <= missing_batch_display_limit < status.missing_count:
            display_suffix = f" Showing first {missing_batch_display_limit} missing batch path(s)."
        return output_readiness(
            {"metric_rows_path": output_path},
            inputs=batch_inputs,
            missing_input_message=(
                f"Metric batches are incomplete: {status.missing_count} batch output(s) missing. "
                f"Wait for Slurm to finish, then rerun this cell.{display_suffix}"
            ),
        )
    return output_readiness(
        {"metric_rows_path": output_path},
        inputs={"metric_manifest_path": manifest_path},
        sources={
            "metric_manifest_path": manifest_path,
            **{
                f"metric_batch_{index:04d}_path": path
                for index, path in zip(status.completed_batches, status.completed_outputs)
            },
        },
        overwrite=overwrite,
        missing_input_message="Metric manifest is not ready yet.",
        current_message="Merged metric rows are current; skipping.",
    )


def metric_outputs_readiness_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    metric_rows: str | Path | None = None,
    overwrite: bool = False,
) -> OutputReadiness:
    """Return readiness for downstream configured metric output tables."""

    config = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    metric_rows_path = (
        Path(metric_rows).expanduser()
        if metric_rows is not None
        else _resolve_output_path("metric_rows", kind="table", cfg=config, create_parent=True)
    )
    return output_readiness(
        {
            "metrics_long_path": _resolve_output_path("metrics_long", kind="table", cfg=config, create_parent=True),
            "path_table_path": _resolve_output_path("path_table", kind="table", cfg=config, create_parent=True),
            "path_summary_path": _resolve_output_path("path_summary", kind="table", cfg=config, create_parent=True),
        },
        inputs={"metric_rows_path": metric_rows_path},
        sources={"metric_rows_path": metric_rows_path},
        overwrite=overwrite,
        missing_input_message="Merged metric rows are not ready yet.",
        current_message="Downstream metric outputs are current; skipping.",
    )


def merge_metric_batches_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    manifest: str | Path | None = None,
    output: str | Path | None = None,
    require_all: bool = True,
) -> dict[str, object]:
    """Merge configured metric batch outputs into the standard metric row table."""

    from spatial_vtk.metrics.workflow.execution import merge_batch_outputs

    config = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    manifest_path = (
        Path(manifest).expanduser()
        if manifest is not None
        else _default_metric_manifest_path(config, prefer_cached=True)
    )
    output_path = (
        Path(output).expanduser()
        if output is not None
        else _resolve_output_path("metric_rows", kind="table", cfg=config, create_parent=True)
    )
    path = merge_batch_outputs(manifest_path, output_path, require_all=require_all)
    return {
        "metric_rows_path": str(path),
        "metric_manifest_path": str(manifest_path),
        "metric_rows": str(path),
        "manifest": str(manifest_path),
    }


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

    from spatial_vtk.metrics.workflow.outputs import write_metric_outputs

    config = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    metric_rows_path = Path(metric_rows).expanduser() if metric_rows is not None else _configured_metric_rows_or_snapshot(config)
    events_path = Path(events).expanduser() if events is not None else _existing_output_path("prepared_events", config=config)
    stations_path = Path(stations).expanduser() if stations is not None else _existing_output_path("prepared_stations", config=config)
    written = write_metric_outputs(
        metric_rows_path,
        None,
        cfg=config,
        events=events_path,
        stations=stations_path,
        residual_column=residual_column,
        score_column=score_column,
        table_format=table_format,
        dashboard_partitioned=dashboard_partitioned,
    )
    return {key: str(path) for key, path in written.items()}


def _workflow_config(*, config_path: str | Path | None, run_scenario: str | None) -> Any:
    """Return an activated config for a metric workflow helper."""

    from spatial_vtk.config.runtime import SpatialVTKConfig, active_config

    if config_path is not None:
        return SpatialVTKConfig.from_file(config_path, run_scenario=run_scenario).activate()
    cfg = active_config()
    if run_scenario:
        return SpatialVTKConfig.from_file(cfg.config_path, run_scenario=run_scenario).activate()
    return cfg


def _resolve_output_path(*args: Any, **kwargs: Any) -> Path:
    """Resolve configured metric workflow output paths only when needed."""

    from spatial_vtk.config.outputs import resolve_output_path

    return resolve_output_path(*args, **kwargs)


def _metric_workflow_dir(config: Any, name: str) -> Path:
    """Return a standard metric workflow directory below the configured output root."""

    root = config.path("outputs.root", must_exist=False) or (config.root_dir / "outputs")
    path = Path(root) / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _metric_slurm_script_path(config: Any) -> Path:
    """Return the standard metric Slurm script path."""

    root = config.path("outputs.root", must_exist=False) or (config.root_dir / "outputs")
    path = Path(root) / "slurm" / "step03_run_metrics.slurm"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _default_metric_manifest_path(config: Any, *, prefer_cached: bool = False) -> Path:
    """Return the configured metric manifest path, optionally preferring cached."""

    if prefer_cached:
        cached = _resolve_output_path("metric_manifest_cached", kind="table", cfg=config, create_parent=True)
        if cached.exists():
            return cached
    return _resolve_output_path("metric_manifest", kind="table", cfg=config, create_parent=True)


def _default_metric_qc_table(config: Any, *, no_qc: bool) -> Path | None:
    """Return the configured metric QC table, respecting no-QC mode."""

    if no_qc:
        return None
    overlap = _resolve_output_path("qc_inventory_overlap", kind="table", cfg=config, create_parent=True)
    return overlap if overlap.exists() else _resolve_output_path("qc_inventory", kind="table", cfg=config, create_parent=True)


def _configured_metric_snapshot(config: Any) -> Path:
    """Return the configured metric snapshot path."""

    value = config.section("paths.metric_snapshot")
    if value in (None, ""):
        raise ValueError(
            "No metric row table is available and paths.metric_snapshot is not configured. "
            "Provide metric_rows or configure paths.metric_snapshot."
        )
    path = config.path("paths.metric_snapshot", must_exist=True)
    if path is None:
        raise ValueError("paths.metric_snapshot did not resolve to a path.")
    return path


def _configured_metric_rows_or_snapshot(config: Any) -> Path:
    """Return configured metric rows, falling back to the tutorial snapshot."""

    metric_rows = _resolve_output_path("metric_rows", kind="table", cfg=config, create_parent=True)
    if metric_rows.exists():
        return metric_rows
    return _configured_metric_snapshot(config)


def _existing_output_path(key: str, *, config: Any) -> Path | None:
    """Return one configured output path only when it already exists."""

    path = _resolve_output_path(key, kind="table", cfg=config, create_parent=False)
    return path if path.exists() else None


def _metric_snapshot_task_table(snapshot: Any, config: Any) -> Any:
    """Return deduplicated metric tasks from a metric snapshot dataframe."""

    import pandas as pd
    from spatial_vtk.config.metrics import metrics_settings_from_config

    settings = metrics_settings_from_config(config)
    df = pd.DataFrame(snapshot).copy()
    rename = {"passband": "band", "simulation_band": "band", "simulation_model": "model", "station_name": "station"}
    df = df.rename(columns={key: value for key, value in rename.items() if key in df.columns and value not in df.columns})
    key_columns = ["event_id", "station", "component", "model", "band"]
    missing = [column for column in key_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Metric snapshot is missing task columns: {missing}")
    tasks = df.loc[:, key_columns].drop_duplicates().copy()
    tasks["passband"] = tasks["band"]
    tasks["metrics"] = ", ".join(settings.metrics)
    tasks["transforms"] = ", ".join(settings.transforms)
    tasks["output_mode"] = settings.output_mode
    tasks["use_qc"] = True
    return tasks


__all__ = [
    "build_metric_waveform_inventories_from_config",
    "load_standard_metric_workflow_outputs",
    "metric_batch_merge_readiness_from_config",
    "metric_inventories_readiness_from_config",
    "metric_manifest_readiness_from_config",
    "metric_outputs_readiness_from_config",
    "metric_slurm_submission_readiness_from_config",
    "merge_metric_batches_from_config",
    "plan_metric_tasks_from_config",
    "StandardMetricWorkflowOutputResult",
    "summarize_metric_snapshot_tasks_from_config",
    "write_metric_outputs_from_config",
    "write_metrics_slurm_script_from_config",
]
