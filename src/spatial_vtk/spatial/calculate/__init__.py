"""Spatial calculation helpers."""

from __future__ import annotations

from spatial_vtk.spatial.calculate.clustering import assign_redcap_clusters, run_residual_feature_clustering
from spatial_vtk.spatial.calculate.correlation import (
    build_distance_bin_summary,
    build_directional_distance_bin_summary,
    compute_global_morans_i,
    evaluate_spatial_block_holdouts,
    moran_result_to_frame,
)
from spatial_vtk.spatial.calculate.corridors import (
    BoundaryCorridorConfig,
    CorridorAnchorConfig,
    CorridorSelectionConfig,
    PolygonCorridorConfig,
    build_boundary_corridors,
    build_station_edge_corridors,
    classify_records_by_corridors,
    select_records_by_corridors,
    select_events_in_corridors,
    summarize_corridor_event_counts,
)
from spatial_vtk.spatial.calculate.geojson import (
    GeoJSONNoOverlapError,
    GeoJSONPathControl,
    add_geojson_metadata_to_metrics,
    annotate_points_with_geojson,
    apply_geojson_path_control,
    classify_paths_with_geojson,
    load_geojson_polygons,
    select_geojson_polygons,
    summarize_metrics_by_geojson,
)
from spatial_vtk.spatial.calculate.geometry import add_source_station_geometry, forward_azimuth_deg
from spatial_vtk.spatial.calculate.geology import add_station_geology_classes, bootstrap_contrast_table, run_geology_spatial_tests
from spatial_vtk.spatial.calculate.patterns import build_pattern_similarity_station_anomalies, pattern_similarity
from spatial_vtk.spatial.calculate.paths import build_path_table, summarize_residuals_by_path_bin
from spatial_vtk.spatial.calculate.pca import PCASpatialModeResult, compute_pca_spatial_modes
from spatial_vtk.spatial.calculate.polygon_edges import load_polygon_features, select_near_edge_stations
from spatial_vtk.spatial.calculate.prepare_stats import (
    build_metric_field,
    build_station_feature_table,
    center_field_by_event,
    normalize_metrics_table,
    summarize_station_bias,
)
from spatial_vtk.spatial.calculate.rotation import rotate_ne_to_rt, rotate_rt_to_ne
from spatial_vtk.spatial.calculate.settings import SpatialStatisticsSettings, spatial_statistics_settings_from_config
from spatial_vtk.spatial.calculate.workflow import (
    SPATIAL_STATISTICS_OUTPUT_DESCRIPTIONS,
    SPATIAL_STATISTICS_OUTPUT_NAMES,
    spatial_statistics_output_paths,
)

__all__ = [
    "add_source_station_geometry",
    "add_station_geology_classes",
    "add_geojson_metadata_to_metrics",
    "annotate_points_with_geojson",
    "apply_geojson_path_control",
    "assign_redcap_clusters",
    "BoundaryCorridorConfig",
    "build_distance_bin_summary",
    "build_directional_distance_bin_summary",
    "build_boundary_corridors",
    "build_metric_field",
    "build_path_table",
    "build_pattern_similarity_station_anomalies",
    "build_station_edge_corridors",
    "build_station_feature_table",
    "bootstrap_contrast_table",
    "center_field_by_event",
    "classify_paths_with_geojson",
    "classify_records_by_corridors",
    "compute_global_morans_i",
    "compute_pca_spatial_modes",
    "CorridorAnchorConfig",
    "CorridorSelectionConfig",
    "evaluate_spatial_block_holdouts",
    "forward_azimuth_deg",
    "GeoJSONNoOverlapError",
    "GeoJSONPathControl",
    "load_polygon_features",
    "load_geojson_polygons",
    "moran_result_to_frame",
    "normalize_metrics_table",
    "PCASpatialModeResult",
    "pattern_similarity",
    "PolygonCorridorConfig",
    "rotate_ne_to_rt",
    "rotate_rt_to_ne",
    "run_geology_spatial_tests",
    "run_residual_feature_clustering",
    "select_records_by_corridors",
    "select_events_in_corridors",
    "select_geojson_polygons",
    "select_near_edge_stations",
    "SPATIAL_STATISTICS_OUTPUT_DESCRIPTIONS",
    "SPATIAL_STATISTICS_OUTPUT_NAMES",
    "SpatialStatisticsSettings",
    "spatial_statistics_output_paths",
    "spatial_statistics_settings_from_config",
    "summarize_corridor_event_counts",
    "summarize_metrics_by_geojson",
    "summarize_residuals_by_path_bin",
    "summarize_station_bias",
]
