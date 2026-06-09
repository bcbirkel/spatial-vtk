"""Non-map spatial plotting helpers."""

from __future__ import annotations

from spatial_vtk.spatial.plot.correlation import (
    plot_block_holdout_scatter,
    plot_cluster_feature_heatmap,
    plot_cluster_solution_scores,
    plot_correlogram,
    plot_distance_correlation_by_metric,
    plot_directional_correlogram,
    plot_pattern_similarity,
    plot_semivariogram,
)
from spatial_vtk.spatial.plot.metrics import (
    boxplot,
    heatmap,
    plot_azimuthal_residuals,
    plot_geology_contrast,
    plot_path_bin_summary,
    plot_polar_residuals,
    plot_residual_correlation,
    scatterplot,
)
from spatial_vtk.spatial.plot.pca import plot_pca_explained_variance, plot_pca_feature_loadings

__all__ = [
    "boxplot",
    "heatmap",
    "plot_azimuthal_residuals",
    "plot_block_holdout_scatter",
    "plot_cluster_feature_heatmap",
    "plot_cluster_solution_scores",
    "plot_correlogram",
    "plot_distance_correlation_by_metric",
    "plot_directional_correlogram",
    "plot_geology_contrast",
    "plot_path_bin_summary",
    "plot_pattern_similarity",
    "plot_pca_explained_variance",
    "plot_pca_feature_loadings",
    "plot_polar_residuals",
    "plot_residual_correlation",
    "plot_semivariogram",
    "scatterplot",
]
