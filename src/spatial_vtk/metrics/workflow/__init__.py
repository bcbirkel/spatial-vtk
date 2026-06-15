"""File-based metric workflow helpers.

Purpose
-------
This package turns prepared waveform inventories and QC inventories into
metric task manifests, batch outputs, merged metric tables, and generic SLURM
array scripts.

Usage examples
--------------
Plan and run metric tasks from Python:
  ``tasks = plan_metric_tasks(observed_inventory, synthetic_inventory, plan=metric_plan)``
  ``rows = run_metric_tasks(tasks)``
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from spatial_vtk.metrics.workflow.outputs import (
    prepare_metric_workflow_outputs,
    write_metric_outputs,
)
from spatial_vtk.metrics.workflow.run import (
    calculate_task_rows,
    run_metric_tasks,
    write_metric_rows,
)
from spatial_vtk.metrics.workflow.slurm import (
    SlurmSettings,
    slurm_settings_from_config,
    submit_metrics_slurm_job,
    write_metrics_slurm_script,
)
from spatial_vtk.metrics.workflow.tasks import (
    MetricWorkflowTask,
    metric_group_for,
    plan_metric_tasks,
    resolve_metric_names,
    summarize_metric_tasks,
    tasks_from_frame,
    tasks_to_frame,
)


_EXECUTION_EXPORTS = {
    "MetricWorkflowManifest",
    "chunk_tasks",
    "merge_batch_outputs",
    "read_task_manifest",
    "run_manifest_batch",
    "write_task_manifest",
}

__all__ = [
    "MetricWorkflowManifest",
    "MetricWorkflowTask",
    "SlurmSettings",
    "calculate_task_rows",
    "chunk_tasks",
    "merge_batch_outputs",
    "metric_group_for",
    "plan_metric_tasks",
    "prepare_metric_workflow_outputs",
    "read_task_manifest",
    "resolve_metric_names",
    "run_manifest_batch",
    "run_metric_tasks",
    "slurm_settings_from_config",
    "submit_metrics_slurm_job",
    "summarize_metric_tasks",
    "tasks_from_frame",
    "tasks_to_frame",
    "write_metric_rows",
    "write_metric_outputs",
    "write_metrics_slurm_script",
    "write_task_manifest",
]


def __getattr__(name: str) -> Any:
    """Load execution helpers lazily to keep ``python -m`` execution clean."""

    if name in _EXECUTION_EXPORTS:
        value = getattr(import_module("spatial_vtk.metrics.workflow.execution"), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'spatial_vtk.metrics.workflow' has no attribute {name!r}")
