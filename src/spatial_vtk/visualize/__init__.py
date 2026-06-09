"""Visualization and dashboard preparation modules."""

from __future__ import annotations

from spatial_vtk.visualize.dashboard import (
    build_dashboard_summaries,
    launch_metrics_dashboard,
    launch_qc_dashboard,
    load_dashboard_metric_dataset,
    prepare_dashboard_metric_table,
    write_dashboard_metric_dataset,
    write_dashboard_summaries,
    write_dashboard_summary_dataset,
)
from spatial_vtk.visualize.figure_io import DEFAULT_FIGURE_NAMES, default_figure_paths, finish_figure, savefig
from spatial_vtk.visualize.figure_context import (
    apply_figure_context,
    context_value_label,
    figure_context_lines,
    figure_context_text,
    is_log2_ratio_field,
    log2_effect_to_percent,
)
from spatial_vtk.visualize.context import (
    plot_event_magnitude_map,
    plot_station_event_beachball_map,
    plot_station_event_network_map,
)
from spatial_vtk.visualize.record_sections import (
    build_record_section_rows,
    plot_observed_synthetic_record_section,
    plot_record_section,
)
from spatial_vtk.visualize.qc import (
    build_trace_qc_overview_html,
    filter_trace_summary,
    plot_data_synthetic_availability,
    plot_event_station_retention_heatmap,
    plot_post_qc_station_event_map,
    plot_qc_drop_cause_diagnostics,
    plot_retention_summary,
    plot_trace_inventory_samples,
    queue_rows_from_filtered_trace_df,
    write_trace_qc_overview_html,
)
from spatial_vtk.visualize.waveforms import (
    plot_event_radial_trace_section,
    plot_event_trace_comparison,
    plot_station_event_waveform_map,
    plot_waveform_overlay_matrix,
)

__all__ = [
    "DEFAULT_FIGURE_NAMES",
    "apply_figure_context",
    "build_record_section_rows",
    "build_dashboard_summaries",
    "build_trace_qc_overview_html",
    "context_value_label",
    "default_figure_paths",
    "figure_context_lines",
    "figure_context_text",
    "filter_trace_summary",
    "finish_figure",
    "is_log2_ratio_field",
    "launch_metrics_dashboard",
    "launch_qc_dashboard",
    "load_dashboard_metric_dataset",
    "log2_effect_to_percent",
    "plot_data_synthetic_availability",
    "plot_event_station_retention_heatmap",
    "plot_event_magnitude_map",
    "plot_event_trace_comparison",
    "plot_observed_synthetic_record_section",
    "plot_event_radial_trace_section",
    "plot_post_qc_station_event_map",
    "plot_qc_drop_cause_diagnostics",
    "plot_record_section",
    "plot_retention_summary",
    "plot_station_event_beachball_map",
    "plot_station_event_network_map",
    "plot_station_event_waveform_map",
    "plot_trace_inventory_samples",
    "plot_waveform_overlay_matrix",
    "prepare_dashboard_metric_table",
    "queue_rows_from_filtered_trace_df",
    "savefig",
    "write_dashboard_metric_dataset",
    "write_dashboard_summaries",
    "write_dashboard_summary_dataset",
    "write_trace_qc_overview_html",
]
