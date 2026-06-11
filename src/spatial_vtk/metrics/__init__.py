"""Ground-motion metric and residual calculations.

Purpose
-------
This package exposes metric calculation, plotting, and workflow helpers without
eagerly importing heavy waveform dependencies. Import calculation functions from
``spatial_vtk.metrics`` for convenience, or import focused submodules such as
``spatial_vtk.metrics.plot`` when you only need figures.

Usage examples
--------------
Import a calculation helper only when you need it:
  ``from spatial_vtk.metrics import compute_metrics_pair``
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


_CALCULATE_EXPORTS = {
    "BANDS",
    "CAV",
    "DEFAULT_BANDS",
    "FAS",
    "LONG_METRIC_COLUMNS",
    "METRIC_NAMES",
    "PGA",
    "PGD",
    "PGV",
    "PSA",
    "BandpassResult",
    "amplitude_spectrum",
    "arias_duration",
    "arias_intensity",
    "bandpass_with_metadata",
    "bands_from_list",
    "bands_from_logspace",
    "binned_numeric_midpoints",
    "build_metric_value_row",
    "build_spectral_metric_rows",
    "build_station_residual_table",
    "calculate_amplitude_ratios",
    "calculate_metric_pair",
    "calculate_metrics_for_pairs",
    "compare_metric_values",
    "compute_amplitude_spectrum_vs_period",
    "compute_metrics_pair",
    "compute_paired_station_event_maxima",
    "compute_period_spectrogram",
    "compute_station_event_maxima",
    "delay_corrected_cc",
    "energy_duration",
    "energy_intensity",
    "enrich_metric_table",
    "interpolate_period_spectrum",
    "metric_residual_series",
    "metric_stems_by_family",
    "original_cc",
    "prepare_metric_residual_table",
    "residual_metric_stems",
    "score_metric_stems",
    "set_bands",
    "set_target_fs",
    "station_mean_table",
    "subset_period_range",
    "summarize_long_metric_table",
    "summarize_metric_scores",
    "traveltime_delay",
}

_WORKFLOW_EXPORTS = {
    "MetricWorkflowManifest",
    "MetricWorkflowTask",
    "SlurmSettings",
    "calculate_task_rows",
    "chunk_tasks",
    "merge_batch_outputs",
    "plan_metric_tasks",
    "read_task_manifest",
    "run_manifest_batch",
    "run_metric_tasks",
    "slurm_settings_from_config",
    "submit_metrics_slurm_job",
    "summarize_metric_tasks",
    "tasks_from_frame",
    "tasks_to_frame",
    "write_metric_rows",
    "write_metrics_slurm_script",
    "write_task_manifest",
}

__all__ = sorted(_CALCULATE_EXPORTS | _WORKFLOW_EXPORTS)


def __getattr__(name: str) -> Any:
    """Load public metric helpers lazily.

    Parameters
    ----------
    name
        Public attribute requested from ``spatial_vtk.metrics``.

    Returns
    -------
    object
        The requested helper from ``metrics.calculate`` or ``metrics.workflow``.
    """

    if name in _CALCULATE_EXPORTS:
        value = getattr(import_module("spatial_vtk.metrics.calculate"), name)
        globals()[name] = value
        return value
    if name in _WORKFLOW_EXPORTS:
        value = getattr(import_module("spatial_vtk.metrics.workflow"), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'spatial_vtk.metrics' has no attribute {name!r}")
