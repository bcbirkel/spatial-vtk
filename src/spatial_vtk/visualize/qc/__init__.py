"""Quality-control visualization helpers.

The QC visualization package is lazy so table and review helpers can be
imported without importing Matplotlib-backed plotting modules.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MODULES = {
    "build_trace_qc_overview_html": "spatial_vtk.visualize.qc.overview",
    "filter_trace_summary": "spatial_vtk.visualize.qc.overview",
    "load_trace_qc_summary": "spatial_vtk.visualize.qc.overview",
    "normalize_trace_qc_summary": "spatial_vtk.visualize.qc.overview",
    "queue_rows_from_filtered_trace_df": "spatial_vtk.visualize.qc.overview",
    "trace_qc_records": "spatial_vtk.visualize.qc.overview",
    "write_trace_qc_overview_html": "spatial_vtk.visualize.qc.overview",
    "plot_data_synthetic_availability": "spatial_vtk.visualize.qc.retention",
    "plot_event_station_retention_heatmap": "spatial_vtk.visualize.qc.retention",
    "plot_post_qc_station_event_map": "spatial_vtk.visualize.qc.retention",
    "plot_qc_drop_cause_diagnostics": "spatial_vtk.visualize.qc.retention",
    "plot_retention_summary": "spatial_vtk.visualize.qc.retention",
    "plot_trace_inventory_samples": "spatial_vtk.visualize.qc.samples",
}

__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    """Load one QC visualization helper on demand."""

    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
