"""Visualization and dashboard preparation modules.

The public visualization package is lazy so dashboard/config helpers can be
imported without importing Matplotlib-backed plotting modules.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MODULES = {
    "build_dashboard_summaries": "spatial_vtk.visualize.dashboard",
    "dashboard_summary_input_columns": "spatial_vtk.visualize.dashboard",
    "launch_configured_dashboards_from_notebook_settings": "spatial_vtk.visualize.dashboard",
    "launch_configured_metrics_dashboard": "spatial_vtk.visualize.dashboard",
    "launch_configured_qc_dashboard": "spatial_vtk.visualize.dashboard",
    "launch_metrics_dashboard": "spatial_vtk.visualize.dashboard",
    "launch_qc_dashboard": "spatial_vtk.visualize.dashboard",
    "load_dashboard_metric_dataset": "spatial_vtk.visualize.dashboard",
    "prepare_dashboard_metric_table": "spatial_vtk.visualize.dashboard",
    "write_configured_dashboard_datasets": "spatial_vtk.visualize.dashboard",
    "write_dashboard_metric_dataset": "spatial_vtk.visualize.dashboard",
    "write_dashboard_summaries": "spatial_vtk.visualize.dashboard",
    "write_dashboard_summary_dataset": "spatial_vtk.visualize.dashboard",
    "DEFAULT_FIGURE_NAMES": "spatial_vtk.visualize.figure_io",
    "default_figure_paths": "spatial_vtk.visualize.figure_io",
    "finish_figure": "spatial_vtk.visualize.figure_io",
    "savefig": "spatial_vtk.visualize.figure_io",
    "FigureSidecarResult": "spatial_vtk.visualize.figure_sidecars",
    "figure_sidecar_dimension_counts": "spatial_vtk.visualize.figure_sidecars",
    "figure_sidecar_metadata_path": "spatial_vtk.visualize.figure_sidecars",
    "figure_sidecar_status_frame": "spatial_vtk.visualize.figure_sidecars",
    "finish_figure_with_sidecar": "spatial_vtk.visualize.figure_sidecars",
    "layered_figure_rows": "spatial_vtk.visualize.figure_sidecars",
    "read_figure_sidecar_metadata": "spatial_vtk.visualize.figure_sidecars",
    "sidecar_rows_for_write": "spatial_vtk.visualize.figure_sidecars",
    "write_figure_row_sidecar": "spatial_vtk.visualize.figure_sidecars",
    "apply_figure_context": "spatial_vtk.visualize.figure_context",
    "context_value_label": "spatial_vtk.visualize.figure_context",
    "figure_context_lines": "spatial_vtk.visualize.figure_context",
    "figure_context_text": "spatial_vtk.visualize.figure_context",
    "is_log2_ratio_field": "spatial_vtk.visualize.figure_context",
    "log2_effect_to_percent": "spatial_vtk.visualize.figure_context",
    "plot_event_magnitude_map": "spatial_vtk.visualize.context",
    "plot_station_event_beachball_map": "spatial_vtk.visualize.context",
    "plot_station_event_network_map": "spatial_vtk.visualize.context",
    "build_record_section_rows": "spatial_vtk.visualize.record_sections",
    "plot_observed_synthetic_record_section": "spatial_vtk.visualize.record_sections",
    "plot_record_section": "spatial_vtk.visualize.record_sections",
    "build_trace_qc_overview_html": "spatial_vtk.visualize.qc",
    "filter_trace_summary": "spatial_vtk.visualize.qc",
    "plot_data_synthetic_availability": "spatial_vtk.visualize.qc",
    "plot_event_station_retention_heatmap": "spatial_vtk.visualize.qc",
    "plot_post_qc_station_event_map": "spatial_vtk.visualize.qc",
    "plot_qc_drop_cause_diagnostics": "spatial_vtk.visualize.qc",
    "plot_retention_summary": "spatial_vtk.visualize.qc",
    "plot_trace_inventory_samples": "spatial_vtk.visualize.qc",
    "queue_rows_from_filtered_trace_df": "spatial_vtk.visualize.qc",
    "write_trace_qc_overview_html": "spatial_vtk.visualize.qc",
    "plot_event_radial_trace_section": "spatial_vtk.visualize.waveforms",
    "plot_event_trace_comparison": "spatial_vtk.visualize.waveforms",
    "plot_station_event_waveform_map": "spatial_vtk.visualize.waveforms",
    "plot_waveform_overlay_matrix": "spatial_vtk.visualize.waveforms",
    "WaveformComparisonFigureResult": "spatial_vtk.visualize.waveforms",
    "write_large_run_waveform_comparison_from_outputs": "spatial_vtk.visualize.waveforms",
    "write_waveform_comparison_from_outputs": "spatial_vtk.visualize.waveforms",
}

__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    """Load one visualization helper on demand."""

    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
