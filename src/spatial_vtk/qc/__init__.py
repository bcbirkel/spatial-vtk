"""Quality-control workflow modules.

This package keeps public QC helpers on ``spatial_vtk.qc`` without importing
waveform, metrics, or Slurm worker dependencies until a helper is requested.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_BUILD_EXPORTS = {
    "InventoryBandSpec",
    "TraceInventoryLookup",
    "build_comparison_eligibility",
    "build_event_station_pair_retention_table",
    "build_event_station_pair_retention_table_from_qc_inventory",
    "build_metric_pair_retention_table",
    "build_metric_pair_retention_table_from_qc_inventory",
    "build_metric_sanity_rejection_table",
    "build_metric_qc_summary",
    "build_post_qc_record_table",
    "build_post_qc_record_table_from_qc_inventory",
    "build_qc_waveform_comparison_records",
    "build_qc_availability_table",
    "build_qc_drop_cause_table_from_qc_inventory",
    "build_retention_figure_table",
    "build_waveform_trace_qc_summary",
    "build_waveform_qc_summary",
    "companion_rows_from_master",
    "determine_available_components",
    "discover_event_ids",
    "export_manual_review_queue",
    "export_manual_review_queue_from_qc_inventory",
    "filter_event_station_records_for_source_overlap",
    "load_standard_qc_inputs",
    "load_standard_qc_workflow_outputs",
    "load_comparison_eligible_records",
    "load_trace_inventory_lookup",
    "metric_sanity_settings_from_config",
    "MetricResidualLimit",
    "MetricSanityQCSettings",
    "MetricValueLimit",
    "QCSummaryWorkflowResult",
    "qc_checkpoint_status_frame",
    "qc_inventory_readiness_from_config",
    "qc_overlap_readiness_from_config",
    "qc_summary_readiness_from_config",
    "StandardQCInputResult",
    "StandardQCWorkflowOutputResult",
    "run_qc_summary_workflow",
    "run_qc_summary_workflow_from_config",
    "SpatialResidualOutlierSettings",
    "apply_metric_sanity_rejections_to_metric_table",
    "summarize_metric_sanity_removals",
    "trace_passband_is_accepted",
    "apply_metric_sanity_rejections_to_qc_inventory",
    "write_comparison_eligibility_from_qc_inventory",
    "write_qc_inventory_overlap_from_config",
    "write_qc_inventory_overlap_from_full",
}

_REVIEW_EXPORTS = {
    "filter_trace_summary",
    "queue_rows_from_filtered_trace_df",
}

_SUMMARY_EXPORTS = {
    "classify_station_family",
    "global_trace_reject_reasons",
    "reject_passband",
}

_SLURM_EXPORTS = {
    "run_qc_inventory_from_config",
    "run_qc_inventory_job",
    "slurm_settings_from_config",
    "submit_qc_slurm_job",
    "write_qc_slurm_script",
}

__all__ = sorted(_BUILD_EXPORTS | _REVIEW_EXPORTS | _SUMMARY_EXPORTS | _SLURM_EXPORTS)


def __getattr__(name: str) -> Any:
    """Load public QC helpers lazily."""

    if name in _BUILD_EXPORTS:
        value = getattr(import_module("spatial_vtk.qc.build"), name)
    elif name in _REVIEW_EXPORTS:
        value = getattr(import_module("spatial_vtk.qc.review"), name)
    elif name in _SUMMARY_EXPORTS:
        value = getattr(import_module("spatial_vtk.qc.summary"), name)
    elif name in _SLURM_EXPORTS:
        value = getattr(import_module("spatial_vtk.qc.build.slurm"), name)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value
