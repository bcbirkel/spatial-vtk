"""Waveform-oriented visualization helpers."""

from __future__ import annotations

from spatial_vtk.visualize.waveforms.comparison import (
    WaveformComparisonFigureResult,
    plot_event_trace_comparison,
    write_large_run_waveform_comparison_from_outputs,
    write_waveform_comparison_from_notebook_settings,
    write_waveform_comparison_from_outputs,
)
from spatial_vtk.visualize.waveforms.overlays import plot_waveform_overlay_matrix
from spatial_vtk.visualize.waveforms.radial_sections import plot_event_radial_trace_section
from spatial_vtk.visualize.waveforms.record_sections import (
    build_record_section_rows,
    plot_observed_synthetic_record_section,
    plot_record_section,
)
from spatial_vtk.visualize.waveforms.station_event import plot_station_event_waveform_map, station_event_waveform_order_frame

__all__ = [
    "build_record_section_rows",
    "WaveformComparisonFigureResult",
    "plot_event_radial_trace_section",
    "plot_event_trace_comparison",
    "plot_observed_synthetic_record_section",
    "plot_record_section",
    "plot_station_event_waveform_map",
    "plot_waveform_overlay_matrix",
    "station_event_waveform_order_frame",
    "write_large_run_waveform_comparison_from_outputs",
    "write_waveform_comparison_from_notebook_settings",
    "write_waveform_comparison_from_outputs",
]
