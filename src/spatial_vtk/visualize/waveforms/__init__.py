"""Waveform-oriented visualization helpers.

The package exposes waveform comparison, overlay, record-section, and
station-event map helpers from one stable public surface while keeping pandas
and plotting imports lazy until a helper is requested.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MODULES = {
    "WaveformComparisonFigureResult": "spatial_vtk.visualize.waveforms.comparison",
    "plot_event_trace_comparison": "spatial_vtk.visualize.waveforms.comparison",
    "write_large_run_waveform_comparison_from_outputs": "spatial_vtk.visualize.waveforms.comparison",
    "write_waveform_comparison_from_notebook_settings": "spatial_vtk.visualize.waveforms.comparison",
    "write_waveform_comparison_from_outputs": "spatial_vtk.visualize.waveforms.comparison",
    "plot_waveform_overlay_matrix": "spatial_vtk.visualize.waveforms.overlays",
    "plot_event_radial_trace_section": "spatial_vtk.visualize.waveforms.radial_sections",
    "build_record_section_rows": "spatial_vtk.visualize.waveforms.record_sections",
    "plot_observed_synthetic_record_section": "spatial_vtk.visualize.waveforms.record_sections",
    "plot_record_section": "spatial_vtk.visualize.waveforms.record_sections",
    "plot_station_event_waveform_map": "spatial_vtk.visualize.waveforms.station_event",
    "station_event_waveform_order_frame": "spatial_vtk.visualize.waveforms.station_event",
}

__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    """Load one waveform visualization helper lazily."""

    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module 'spatial_vtk.visualize.waveforms' has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
