"""Quality-control dataset construction helpers.

The public ``spatial_vtk.qc.build`` surface is intentionally lazy so simple
imports and docs can inspect available names without importing waveform readers
or metric calculation dependencies.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_FILTERING_EXPORTS = {
    "InventoryBandSpec",
    "TraceInventoryLookup",
    "band_key_from_label",
    "band_label_from_key",
    "event_station_has_any_accepted_component",
    "filter_stream_by_inventory",
    "inventory_lookup_key",
    "load_trace_inventory_lookup",
    "normalize_band_label",
    "normalize_component",
    "normalize_observed_variant",
    "parse_period_band_label",
    "period_band_label",
    "relevant_inventory_bands",
    "trace_has_any_accepted_passband",
    "trace_passband_is_accepted",
}

_INVENTORY_EXPORTS = {
    "build_trace_inventory",
    "build_waveform_trace_qc_summary",
    "companion_rows_from_master",
    "determine_available_components",
    "discover_event_ids",
}

_SPECTRAL_EXPORTS = {
    "qc_fas_periods",
    "qc_psa_periods",
    "spectral_relative_amplitude_mask",
    "spectral_valid_period_bounds",
}

_WORKFLOW_EXPORTS = {
    "build_comparison_eligibility",
    "build_event_station_pair_retention_table",
    "build_event_station_pair_retention_table_from_qc_inventory",
    "build_metric_pair_retention_table",
    "build_metric_pair_retention_table_from_qc_inventory",
    "build_metric_qc_summary",
    "build_post_qc_record_table",
    "build_post_qc_record_table_from_qc_inventory",
    "build_qc_waveform_comparison_records",
    "build_qc_availability_table",
    "build_qc_drop_cause_table_from_qc_inventory",
    "build_retention_figure_table",
    "build_waveform_qc_summary",
    "export_manual_review_queue",
    "export_manual_review_queue_from_qc_inventory",
    "filter_event_station_records_for_source_overlap",
    "load_standard_qc_inputs",
    "load_standard_qc_workflow_outputs",
    "load_comparison_eligible_records",
    "QCSummaryWorkflowResult",
    "StandardQCInputResult",
    "StandardQCWorkflowOutputResult",
    "run_qc_summary_workflow",
    "run_qc_summary_workflow_from_config",
    "write_comparison_eligibility_from_qc_inventory",
    "write_qc_inventory_overlap_from_config",
    "write_qc_inventory_overlap_from_full",
}

_SLURM_EXPORTS = {
    "run_qc_inventory_from_config",
    "run_qc_inventory_job",
    "slurm_settings_from_config",
    "submit_qc_slurm_job",
    "write_qc_slurm_script",
}

__all__ = sorted(_FILTERING_EXPORTS | _INVENTORY_EXPORTS | _SPECTRAL_EXPORTS | _WORKFLOW_EXPORTS | _SLURM_EXPORTS)


def __getattr__(name: str) -> Any:
    """Load one public QC build helper on demand."""

    if name in _FILTERING_EXPORTS:
        value = getattr(import_module("spatial_vtk.qc.build.filtering"), name)
    elif name in _INVENTORY_EXPORTS:
        value = getattr(import_module("spatial_vtk.qc.build.inventory"), name)
    elif name in _SPECTRAL_EXPORTS:
        value = getattr(import_module("spatial_vtk.qc.build.spectral"), name)
    elif name in _WORKFLOW_EXPORTS:
        value = getattr(import_module("spatial_vtk.qc.build.workflow"), name)
    elif name in _SLURM_EXPORTS:
        value = getattr(import_module("spatial_vtk.qc.build.slurm"), name)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value
