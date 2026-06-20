"""Basic context visualization helpers.

The package exposes context maps, coverage figures, and record-coverage table
builders from one stable public surface while keeping plotting dependencies
lazy until a helper is requested.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MODULES = {
    "build_record_coverage_table": "spatial_vtk.visualize.context.figures",
    "build_record_coverage_table_from_qc": "spatial_vtk.visualize.context.figures",
    "build_record_coverage_table_from_trace_metadata": "spatial_vtk.visualize.context.figures",
    "ContextFigureResult": "spatial_vtk.visualize.context.figures",
    "plot_distance_amplitude_diagnostics": "spatial_vtk.visualize.context.figures",
    "plot_event_coverage": "spatial_vtk.visualize.context.figures",
    "plot_event_trace_comparison": "spatial_vtk.visualize.context.figures",
    "plot_record_coverage": "spatial_vtk.visualize.context.figures",
    "plot_station_coverage": "spatial_vtk.visualize.context.figures",
    "plot_station_event_context": "spatial_vtk.visualize.context.figures",
    "plot_study_domain_map": "spatial_vtk.visualize.context.figures",
    "summarize_coverage": "spatial_vtk.visualize.context.figures",
    "write_context_figures_from_outputs": "spatial_vtk.visualize.context.figures",
    "write_large_run_context_figures_from_outputs": "spatial_vtk.visualize.context.figures",
    "plot_event_magnitude_map": "spatial_vtk.visualize.context.maps",
    "plot_station_event_beachball_map": "spatial_vtk.visualize.context.maps",
    "plot_station_event_network_map": "spatial_vtk.visualize.context.maps",
}

__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    """Load one context visualization helper lazily."""

    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module 'spatial_vtk.visualize.context' has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
