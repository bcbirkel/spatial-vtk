"""Spatial-statistics workflow helpers.

``spatial_vtk.spatial`` is the stable import surface for spatial calculations,
GeoJSON summaries, corridors, geometry, PCA, clustering, path summaries,
pattern-comparison helpers, and standard Step 5/6 workflow input/status
loaders. Public names are resolved lazily so importing the package does not
load every spatial calculation or plotting backend.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from spatial_vtk.spatial.calculate import _EXPORT_MODULES as _CALCULATE_EXPORT_MODULES


_WORKFLOW_PLOT_EXPORT_MODULES = {
    "load_standard_additional_plotting_output_status": "spatial_vtk.spatial.workflow",
    "load_standard_additional_plotting_inputs": "spatial_vtk.spatial.workflow",
    "load_standard_geojson_workflow_output_status": "spatial_vtk.spatial.workflow",
    "load_standard_geojson_plotting_inputs": "spatial_vtk.spatial.workflow",
}

_EXPORT_MODULES = {
    **_CALCULATE_EXPORT_MODULES,
    **_WORKFLOW_PLOT_EXPORT_MODULES,
}


__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    """Load one spatial calculation helper lazily."""

    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module 'spatial_vtk.spatial' has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
