"""Basic context visualization helpers."""

from __future__ import annotations

from spatial_vtk.visualize.context.figures import (
    build_record_coverage_table,
    build_record_coverage_table_from_qc,
    build_record_coverage_table_from_trace_metadata,
    ContextFigureResult,
    plot_distance_amplitude_diagnostics,
    plot_event_coverage,
    plot_event_trace_comparison,
    plot_record_coverage,
    plot_station_coverage,
    plot_station_event_context,
    plot_study_domain_map,
    summarize_coverage,
    write_context_figures_from_outputs,
    write_large_run_context_figures_from_outputs,
)
from spatial_vtk.visualize.context.maps import (
    plot_event_magnitude_map,
    plot_station_event_beachball_map,
    plot_station_event_network_map,
)

__all__ = [
    "plot_distance_amplitude_diagnostics",
    "build_record_coverage_table",
    "build_record_coverage_table_from_qc",
    "build_record_coverage_table_from_trace_metadata",
    "ContextFigureResult",
    "plot_event_coverage",
    "plot_event_magnitude_map",
    "plot_event_trace_comparison",
    "plot_record_coverage",
    "plot_station_event_beachball_map",
    "plot_station_coverage",
    "plot_station_event_context",
    "plot_station_event_network_map",
    "plot_study_domain_map",
    "summarize_coverage",
    "write_context_figures_from_outputs",
    "write_large_run_context_figures_from_outputs",
]
