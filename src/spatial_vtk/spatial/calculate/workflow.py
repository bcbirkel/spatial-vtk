"""Workflow helpers for spatial-statistics tutorial and CLI outputs.

Purpose
-------
This module names the standard spatial-statistics output tables so notebooks,
scripts, and CLI wrappers can share the same file layout.

Usage examples
--------------
Create standard paths for spatial outputs:
  ``paths = spatial_statistics_output_paths("outputs/tutorials/step_04")``
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from spatial_vtk.io import default_output_paths


SPATIAL_STATISTICS_OUTPUT_NAMES: tuple[str, ...] = (
    "metric_field.parquet",
    "event_centered_residuals.parquet",
    "station_bias.parquet",
    "morans_i",
    "permutation_moran",
    "distance_bin_correlations",
    "clusters.parquet",
    "cluster_scores",
    "cluster_summary",
    "pca_station_scores.parquet",
    "pca_feature_loadings",
    "pca_explained_variance",
    "geology_contrasts",
    "geojson_region_summaries",
)

SPATIAL_STATISTICS_OUTPUT_DESCRIPTIONS: dict[str, str] = {
    "metric_field": "Metric field table",
    "event_centered_residuals": "Event-centered residuals",
    "station_bias": "Station-bias summary",
    "morans_i": "Moran's I summary",
    "permutation_moran": "Permutation Moran test summary",
    "distance_bin_correlations": "Distance-bin correlations",
    "clusters": "Cluster assignments",
    "cluster_scores": "Cluster solution scores",
    "cluster_summary": "Cluster summary",
    "pca_station_scores": "PCA station scores",
    "pca_feature_loadings": "PCA feature loadings",
    "pca_explained_variance": "PCA explained variance",
    "geology_contrasts": "Geology contrast summary",
    "geojson_region_summaries": "GeoJSON region summaries",
}


def spatial_statistics_output_paths(output_dir: str | Path) -> SimpleNamespace:
    """Return standard Step 4 spatial-statistics output paths.

    Parameters
    ----------
    output_dir
        Directory where spatial-statistics tables should be written.

    Returns
    -------
    types.SimpleNamespace
        Namespace with one attribute per standard output table.
    """

    return default_output_paths(output_dir, SPATIAL_STATISTICS_OUTPUT_NAMES)


__all__ = [
    "SPATIAL_STATISTICS_OUTPUT_DESCRIPTIONS",
    "SPATIAL_STATISTICS_OUTPUT_NAMES",
    "spatial_statistics_output_paths",
]
