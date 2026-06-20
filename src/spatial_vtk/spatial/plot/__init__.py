"""Non-map spatial plotting helpers.

Purpose
-------
This package exposes Spatial-VTK spatial plotting helpers from one stable
entry point without importing every plot family at package import time.

Usage examples
--------------
Render the configured large-run spatial figure suite:
  ``from spatial_vtk.spatial.plot import write_large_run_spatial_figure_suite_from_notebook_settings``
  ``result = write_large_run_spatial_figure_suite_from_notebook_settings(settings)``

Use individual functions such as ``plot_correlogram()`` directly only for
focused scripts that already own filtered spatial summary tables.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORT_MODULES = {
    "plot_block_holdout_scatter": "spatial_vtk.spatial.plot.correlation",
    "plot_cluster_feature_heatmap": "spatial_vtk.spatial.plot.correlation",
    "plot_cluster_solution_scores": "spatial_vtk.spatial.plot.correlation",
    "plot_correlogram": "spatial_vtk.spatial.plot.correlation",
    "plot_distance_correlation_by_metric": "spatial_vtk.spatial.plot.correlation",
    "plot_directional_correlogram": "spatial_vtk.spatial.plot.correlation",
    "plot_pattern_similarity": "spatial_vtk.spatial.plot.correlation",
    "plot_semivariogram": "spatial_vtk.spatial.plot.correlation",
    "RegionBoxplotResult": "spatial_vtk.spatial.plot.large_run",
    "RegionFigureResult": "spatial_vtk.spatial.plot.large_run",
    "SpatialFigureContext": "spatial_vtk.spatial.plot.large_run",
    "SpatialFigureSuiteResult": "spatial_vtk.spatial.plot.large_run",
    "StandardAdditionalPlottingFigureResult": "spatial_vtk.spatial.plot.large_run",
    "StandardAdditionalPlottingInputResult": "spatial_vtk.spatial.plot.large_run",
    "StandardAdditionalPlottingOutputStatusResult": "spatial_vtk.spatial.plot.large_run",
    "StandardGeoJSONCorridorFigureResult": "spatial_vtk.spatial.plot.large_run",
    "StandardGeoJSONFigureResult": "spatial_vtk.spatial.plot.large_run",
    "StandardGeoJSONPlottingInputResult": "spatial_vtk.spatial.plot.large_run",
    "StandardGeoJSONWorkflowOutputStatusResult": "spatial_vtk.spatial.plot.large_run",
    "StandardSpatialDiagnosticFigureResult": "spatial_vtk.spatial.plot.large_run",
    "StandardSpatialMapFigureResult": "spatial_vtk.spatial.plot.large_run",
    "prepare_spatial_figure_context": "spatial_vtk.spatial.plot.large_run",
    "prepare_spatial_figure_context_from_notebook_settings": "spatial_vtk.spatial.plot.large_run",
    "SpatialSummaryFigureResult": "spatial_vtk.spatial.plot.large_run",
    "load_standard_additional_plotting_output_status": "spatial_vtk.spatial.plot.large_run",
    "load_standard_additional_plotting_inputs": "spatial_vtk.spatial.plot.large_run",
    "load_standard_geojson_workflow_output_status": "spatial_vtk.spatial.plot.large_run",
    "load_standard_geojson_plotting_inputs": "spatial_vtk.spatial.plot.large_run",
    "write_standard_additional_plotting_figures": "spatial_vtk.spatial.plot.large_run",
    "write_standard_geojson_corridor_figures": "spatial_vtk.spatial.plot.large_run",
    "write_standard_geojson_region_figures": "spatial_vtk.spatial.plot.large_run",
    "write_standard_spatial_diagnostic_figures": "spatial_vtk.spatial.plot.large_run",
    "write_standard_spatial_map_figures": "spatial_vtk.spatial.plot.large_run",
    "write_large_run_geojson_region_figures_from_outputs": "spatial_vtk.spatial.plot.large_run",
    "write_large_run_geojson_region_figures_from_notebook_settings": "spatial_vtk.spatial.plot.large_run",
    "write_large_run_region_boxplot": "spatial_vtk.spatial.plot.large_run",
    "write_large_run_region_boxplot_from_outputs": "spatial_vtk.spatial.plot.large_run",
    "write_large_run_region_boxplot_from_notebook_settings": "spatial_vtk.spatial.plot.large_run",
    "write_large_run_spatial_summary_figures_from_outputs": "spatial_vtk.spatial.plot.large_run",
    "write_large_run_spatial_figure_suite_from_notebook_settings": "spatial_vtk.spatial.plot.large_run",
    "boxplot": "spatial_vtk.spatial.plot.metrics",
    "heatmap": "spatial_vtk.spatial.plot.metrics",
    "plot_azimuthal_residuals": "spatial_vtk.spatial.plot.metrics",
    "plot_geology_contrast": "spatial_vtk.spatial.plot.metrics",
    "plot_path_bin_summary": "spatial_vtk.spatial.plot.metrics",
    "plot_polar_residuals": "spatial_vtk.spatial.plot.metrics",
    "plot_residual_correlation": "spatial_vtk.spatial.plot.metrics",
    "scatterplot": "spatial_vtk.spatial.plot.metrics",
    "plot_pca_explained_variance": "spatial_vtk.spatial.plot.pca",
    "plot_pca_feature_loadings": "spatial_vtk.spatial.plot.pca",
}

__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    """Load one spatial plotting helper lazily.

    Parameters
    ----------
    name
        Public attribute requested from ``spatial_vtk.spatial.plot``.

    Returns
    -------
    object
        The requested plotting helper.
    """

    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module 'spatial_vtk.spatial.plot' has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
