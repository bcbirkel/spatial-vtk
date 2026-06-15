"""Quality-control workflow modules."""

from __future__ import annotations

from importlib import import_module

from spatial_vtk.qc.build import (
    InventoryBandSpec,
    TraceInventoryLookup,
    build_comparison_eligibility,
    build_event_station_pair_retention_table,
    build_event_station_pair_retention_table_from_qc_inventory,
    build_metric_pair_retention_table,
    build_metric_pair_retention_table_from_qc_inventory,
    build_metric_qc_summary,
    build_post_qc_record_table,
    build_post_qc_record_table_from_qc_inventory,
    build_qc_waveform_comparison_records,
    build_qc_availability_table,
    build_qc_drop_cause_table_from_qc_inventory,
    build_retention_figure_table,
    build_waveform_trace_qc_summary,
    build_waveform_qc_summary,
    companion_rows_from_master,
    determine_available_components,
    discover_event_ids,
    export_manual_review_queue,
    export_manual_review_queue_from_qc_inventory,
    filter_event_station_records_for_source_overlap,
    load_comparison_eligible_records,
    load_trace_inventory_lookup,
    trace_passband_is_accepted,
    write_comparison_eligibility_from_qc_inventory,
)
from spatial_vtk.qc.review import filter_trace_summary, queue_rows_from_filtered_trace_df
from spatial_vtk.qc.summary import classify_station_family, global_trace_reject_reasons, reject_passband

_SLURM_EXPORTS = {"run_qc_inventory_job", "submit_qc_slurm_job", "write_qc_slurm_script"}


def __getattr__(name: str):
    """Lazily expose Slurm helpers without pre-importing worker modules."""

    if name in _SLURM_EXPORTS:
        slurm = import_module("spatial_vtk.qc.build.slurm")
        return getattr(slurm, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "InventoryBandSpec",
    "TraceInventoryLookup",
    "classify_station_family",
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
    "build_waveform_trace_qc_summary",
    "build_waveform_qc_summary",
    "companion_rows_from_master",
    "determine_available_components",
    "discover_event_ids",
    "export_manual_review_queue",
    "export_manual_review_queue_from_qc_inventory",
    "filter_trace_summary",
    "filter_event_station_records_for_source_overlap",
    "global_trace_reject_reasons",
    "load_comparison_eligible_records",
    "load_trace_inventory_lookup",
    "queue_rows_from_filtered_trace_df",
    "reject_passband",
    "run_qc_inventory_job",
    "submit_qc_slurm_job",
    "trace_passband_is_accepted",
    "write_comparison_eligibility_from_qc_inventory",
    "write_qc_slurm_script",
]
