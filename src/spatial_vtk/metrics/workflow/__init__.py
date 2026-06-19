"""File-based metric workflow helpers.

Purpose
-------
This package turns prepared waveform inventories and QC inventories into
metric task manifests, batch outputs, merged metric tables, and generic SLURM
array scripts. Public names are loaded lazily so documentation and CLI help can
inspect the package without importing pandas-heavy workflow modules.

Usage examples
--------------
Plan and run metric tasks from Python:
  ``tasks = plan_metric_tasks(observed_inventory, synthetic_inventory, plan=metric_plan)``
  ``rows = run_metric_tasks(tasks)``
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORT_MODULES = {
    "MetricManifestBatchStatus": "spatial_vtk.metrics.workflow.execution",
    "MetricSlurmSubmissionReadiness": "spatial_vtk.metrics.workflow.execution",
    "MetricWaveformCacheResult": "spatial_vtk.metrics.workflow.cache",
    "MetricWaveformInventoryResult": "spatial_vtk.metrics.workflow.inventory",
    "MetricWorkflowManifest": "spatial_vtk.metrics.workflow.execution",
    "MetricWorkflowTask": "spatial_vtk.metrics.workflow.tasks",
    "SlurmSettings": "spatial_vtk.metrics.workflow.slurm",
    "StandardMetricWorkflowOutputResult": "spatial_vtk.metrics.workflow.standard",
    "build_metric_waveform_inventories_from_config": "spatial_vtk.metrics.workflow.configured",
    "build_metric_waveform_inventories_from_trace_metadata": "spatial_vtk.metrics.workflow.inventory",
    "cache_metric_manifest_waveforms": "spatial_vtk.metrics.workflow.cache",
    "calculate_task_rows": "spatial_vtk.metrics.workflow.run",
    "chunk_tasks": "spatial_vtk.metrics.workflow.execution",
    "load_standard_metric_workflow_outputs": "spatial_vtk.metrics.workflow.standard",
    "merge_batch_outputs": "spatial_vtk.metrics.workflow.execution",
    "merge_metric_batches_from_config": "spatial_vtk.metrics.workflow.configured",
    "metric_batch_merge_readiness_from_config": "spatial_vtk.metrics.workflow.configured",
    "metric_group_for": "spatial_vtk.metrics.workflow.tasks",
    "metric_manifest_batch_status": "spatial_vtk.metrics.workflow.execution",
    "metric_outputs_readiness_from_config": "spatial_vtk.metrics.workflow.configured",
    "metric_slurm_submission_readiness": "spatial_vtk.metrics.workflow.execution",
    "metric_slurm_submission_readiness_from_config": "spatial_vtk.metrics.workflow.configured",
    "plan_metric_tasks": "spatial_vtk.metrics.workflow.tasks",
    "plan_metric_tasks_from_config": "spatial_vtk.metrics.workflow.configured",
    "prepare_metric_workflow_outputs": "spatial_vtk.metrics.workflow.outputs",
    "read_task_manifest": "spatial_vtk.metrics.workflow.execution",
    "resolve_metric_names": "spatial_vtk.metrics.workflow.tasks",
    "run_manifest_batch": "spatial_vtk.metrics.workflow.execution",
    "run_metric_tasks": "spatial_vtk.metrics.workflow.run",
    "slurm_settings_from_config": "spatial_vtk.metrics.workflow.slurm",
    "submit_metrics_slurm_job": "spatial_vtk.metrics.workflow.slurm",
    "summarize_metric_snapshot_tasks_from_config": "spatial_vtk.metrics.workflow.configured",
    "summarize_metric_tasks": "spatial_vtk.metrics.workflow.tasks",
    "tasks_from_frame": "spatial_vtk.metrics.workflow.tasks",
    "tasks_to_frame": "spatial_vtk.metrics.workflow.tasks",
    "write_metric_outputs": "spatial_vtk.metrics.workflow.outputs",
    "write_metric_outputs_from_config": "spatial_vtk.metrics.workflow.configured",
    "write_metric_rows": "spatial_vtk.metrics.workflow.run",
    "write_metrics_slurm_script": "spatial_vtk.metrics.workflow.slurm",
    "write_metrics_slurm_script_from_config": "spatial_vtk.metrics.workflow.configured",
    "write_task_manifest": "spatial_vtk.metrics.workflow.execution",
}

__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    """Load one metric workflow helper lazily."""

    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module 'spatial_vtk.metrics.workflow' has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
