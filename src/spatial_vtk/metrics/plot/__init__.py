"""Metric plotting helpers.

Purpose
-------
This package exposes metric plotting functions without importing calculation
helpers unless an example metric plot explicitly needs them.

Usage examples
--------------
Render the configured large-run metric figure suite:
  ``from spatial_vtk.metrics.plot import write_large_run_metric_figure_suite_from_notebook_settings``
  ``result = write_large_run_metric_figure_suite_from_notebook_settings(metrics_long_path, settings)``

Use individual functions such as ``plot_psa_period_curve()`` directly only
for focused scripts that already own filtered metric rows.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORT_MODULES = {
    "SyntheticMetricPair": "spatial_vtk.metrics.plot.example_metric_plots",
    "build_example_metric_summary": "spatial_vtk.metrics.plot.example_metric_plots",
    "plot_example_metric_pairs": "spatial_vtk.metrics.plot.example_metric_plots",
    "synthetic_metric_pairs": "spatial_vtk.metrics.plot.example_metric_plots",
    "plot_band_score_distribution": "spatial_vtk.metrics.plot.model_comparison",
    "plot_model_metric_heatmap": "spatial_vtk.metrics.plot.model_comparison",
    "plot_winner_heatmap": "spatial_vtk.metrics.plot.model_comparison",
    "plot_period_score_distribution": "spatial_vtk.metrics.plot.periods",
    "plot_period_spectra": "spatial_vtk.metrics.plot.periods",
    "plot_period_spectrogram": "spatial_vtk.metrics.plot.periods",
    "plot_psa_period_curve": "spatial_vtk.metrics.plot.periods",
    "plot_geology_boxplot": "spatial_vtk.metrics.plot.site_terms",
    "plot_vs30_scatter": "spatial_vtk.metrics.plot.site_terms",
    "plot_metric_trend": "spatial_vtk.metrics.plot.trends",
    "plot_phase_delay_vs_distance": "spatial_vtk.metrics.plot.trends",
    "plot_residuals_vs_depth": "spatial_vtk.metrics.plot.trends",
    "plot_residuals_vs_distance": "spatial_vtk.metrics.plot.trends",
    "plot_score_trends": "spatial_vtk.metrics.plot.trends",
    "MetricFigureContext": "spatial_vtk.metrics.plot.large_run",
    "MetricFigureSuiteResult": "spatial_vtk.metrics.plot.large_run",
    "StandardMetricDiagnosticFigureResult": "spatial_vtk.metrics.plot.large_run",
    "StationMetricMapResult": "spatial_vtk.metrics.plot.large_run",
    "metric_plot_input_summary_frame": "spatial_vtk.metrics.plot.large_run",
    "metric_rows_for_metrics": "spatial_vtk.metrics.plot.large_run",
    "prepare_large_run_metric_figure_context": "spatial_vtk.metrics.plot.large_run",
    "write_large_run_metric_figure_suite_from_notebook_settings": "spatial_vtk.metrics.plot.large_run",
    "write_standard_metric_diagnostic_figures": "spatial_vtk.metrics.plot.large_run",
    "write_station_metric_map_from_notebook_settings": "spatial_vtk.metrics.plot.large_run",
}

__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    """Load one plotting helper lazily.

    Parameters
    ----------
    name
        Public attribute requested from ``spatial_vtk.metrics.plot``.

    Returns
    -------
    object
        The requested plotting helper.
    """

    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module 'spatial_vtk.metrics.plot' has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
