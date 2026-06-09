"""Map helpers and map-producing workflows.

Purpose
-------
This package exposes Spatial-VTK map helpers without importing every map
family at package import time.

Usage examples
--------------
Create a station residual map:
  ``from spatial_vtk.spatial.map import plot_station_metric_map``
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORT_MODULES = {
    "add_contextily_basemap": "spatial_vtk.spatial.map.basemaps",
    "draw_static_basemap_fallback": "spatial_vtk.spatial.map.basemaps",
    "plot_geojson_polygons_map": "spatial_vtk.spatial.map.geojson",
    "plot_block_holdout_error_map": "spatial_vtk.spatial.map.correlation",
    "plot_block_holdout_summary": "spatial_vtk.spatial.map.correlation",
    "plot_cluster_map": "spatial_vtk.spatial.map.correlation",
    "plot_cluster_summary": "spatial_vtk.spatial.map.correlation",
    "plot_redcap_cluster_map": "spatial_vtk.spatial.map.correlation",
    "plot_station_bias_map": "spatial_vtk.spatial.map.correlation",
    "plot_metric_map_by_model": "spatial_vtk.spatial.map.metrics",
    "plot_model_improvement_map": "spatial_vtk.spatial.map.metrics",
    "plot_residual_grid": "spatial_vtk.spatial.map.metrics",
    "plot_score_map": "spatial_vtk.spatial.map.metrics",
    "plot_station_metric_map": "spatial_vtk.spatial.map.metrics",
    "plot_corridor_map": "spatial_vtk.spatial.map.path.corridors",
    "plot_event_residual_map": "spatial_vtk.spatial.map.path.residuals",
    "plot_pca_mode_map": "spatial_vtk.spatial.map.pca",
    "plot_pca_summary": "spatial_vtk.spatial.map.pca",
}

__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    """Load one map helper lazily.

    Parameters
    ----------
    name
        Public attribute requested from ``spatial_vtk.spatial.map``.

    Returns
    -------
    object
        The requested map helper.
    """

    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module 'spatial_vtk.spatial.map' has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
