"""Metric plotting helpers.

Purpose
-------
This package exposes metric plotting functions without importing calculation
helpers unless an example metric plot explicitly needs them.

Usage examples
--------------
Plot PSA residuals by period:
  ``from spatial_vtk.metrics.plot import plot_psa_period_curve``
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
