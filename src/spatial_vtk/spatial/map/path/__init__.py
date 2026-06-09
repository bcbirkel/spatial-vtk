"""Path-focused map workflows."""

from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORT_MODULES = {
    "plot_corridor_map": "spatial_vtk.spatial.map.path.corridors",
    "plot_event_residual_map": "spatial_vtk.spatial.map.path.residuals",
}

__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    """Load one path-map helper lazily."""

    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module 'spatial_vtk.spatial.map.path' has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
