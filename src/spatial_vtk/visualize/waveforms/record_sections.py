"""Record-section waveform figures.

Purpose
-------
This module exposes record-section APIs under the waveform visualization group.
The existing `spatial_vtk.visualize.record_sections` module remains as a
compatibility path.
"""

from __future__ import annotations

from spatial_vtk.visualize.record_sections import (
    build_record_section_rows,
    normalize_trace,
    plot_observed_synthetic_record_section,
    plot_record_section,
    save_record_section_figure,
    trace_component,
    trace_station,
    trace_to_array,
)

__all__ = [
    "build_record_section_rows",
    "normalize_trace",
    "plot_observed_synthetic_record_section",
    "plot_record_section",
    "save_record_section_figure",
    "trace_component",
    "trace_station",
    "trace_to_array",
]
