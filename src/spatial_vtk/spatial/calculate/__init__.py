"""Spatial calculation helpers.

This package exposes spatial workflow and calculation helpers from one stable
surface while keeping individual calculation modules lazy until a helper is
requested.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORT_MODULES = {
    "add_geojson_metadata_to_metrics": "spatial_vtk.spatial.calculate.geojson",
    "add_source_station_geometry": "spatial_vtk.spatial.calculate.geometry",
    "add_station_geology_classes": "spatial_vtk.spatial.calculate.geology",
    "annotate_points_with_geojson": "spatial_vtk.spatial.calculate.geojson",
    "apply_geojson_path_control": "spatial_vtk.spatial.calculate.geojson",
    "assign_redcap_clusters": "spatial_vtk.spatial.calculate.clustering",
    "BoundaryCorridorConfig": "spatial_vtk.spatial.calculate.corridors",
    "BoundaryCorridorWorkflowResult": "spatial_vtk.spatial.calculate.corridors",
    "boundary_corridor_config_from_config": "spatial_vtk.spatial.calculate.corridors",
    "boundary_corridor_readiness_from_config": "spatial_vtk.spatial.calculate.workflow",
    "bootstrap_contrast_table": "spatial_vtk.spatial.calculate.geology",
    "build_boundary_corridors": "spatial_vtk.spatial.calculate.corridors",
    "build_distance_bin_summary": "spatial_vtk.spatial.calculate.correlation",
    "build_directional_distance_bin_summary": "spatial_vtk.spatial.calculate.correlation",
    "build_geojson_region_summary": "spatial_vtk.spatial.calculate.geojson",
    "build_geojson_region_summary_from_table": "spatial_vtk.spatial.calculate.geojson",
    "build_metric_field": "spatial_vtk.spatial.calculate.prepare_stats",
    "build_path_table": "spatial_vtk.spatial.calculate.paths",
    "build_pattern_similarity_station_anomalies": "spatial_vtk.spatial.calculate.patterns",
    "build_station_edge_corridors": "spatial_vtk.spatial.calculate.corridors",
    "build_station_feature_table": "spatial_vtk.spatial.calculate.prepare_stats",
    "center_field_by_event": "spatial_vtk.spatial.calculate.prepare_stats",
    "classify_paths_with_geojson": "spatial_vtk.spatial.calculate.geojson",
    "classify_records_by_corridors": "spatial_vtk.spatial.calculate.corridors",
    "compute_global_morans_i": "spatial_vtk.spatial.calculate.correlation",
    "compute_pca_spatial_modes": "spatial_vtk.spatial.calculate.pca",
    "CorridorAnchorConfig": "spatial_vtk.spatial.calculate.corridors",
    "corridor_record_pair_frame": "spatial_vtk.spatial.calculate.corridors",
    "corridor_record_preview_frame": "spatial_vtk.spatial.calculate.corridors",
    "CorridorSelectionConfig": "spatial_vtk.spatial.calculate.corridors",
    "evaluate_spatial_block_holdouts": "spatial_vtk.spatial.calculate.correlation",
    "event_station_records_matching_pairs": "spatial_vtk.spatial.calculate.corridors",
    "forward_azimuth_deg": "spatial_vtk.spatial.calculate.geometry",
    "GeoJSONNoOverlapError": "spatial_vtk.spatial.calculate.geojson",
    "GeoJSONPathControl": "spatial_vtk.spatial.calculate.geojson",
    "GeoJSONRegionSummaryWorkflowResult": "spatial_vtk.spatial.calculate.geojson",
    "geojson_matched_record_frame": "spatial_vtk.spatial.calculate.corridors",
    "geojson_metric_region_frame": "spatial_vtk.spatial.calculate.geojson",
    "geojson_metric_subset_frame": "spatial_vtk.spatial.calculate.geojson",
    "geojson_polygon_preview_table": "spatial_vtk.spatial.calculate.geojson",
    "geojson_region_summary_readiness_from_config": "spatial_vtk.spatial.calculate.workflow",
    "load_geojson_polygons": "spatial_vtk.spatial.calculate.geojson",
    "load_polygon_features": "spatial_vtk.spatial.calculate.polygon_edges",
    "load_standard_spatial_workflow_output_status": "spatial_vtk.spatial.calculate.workflow",
    "load_standard_spatial_workflow_outputs": "spatial_vtk.spatial.calculate.workflow",
    "moran_result_to_frame": "spatial_vtk.spatial.calculate.correlation",
    "normalize_metrics_table": "spatial_vtk.spatial.calculate.prepare_stats",
    "pattern_similarity": "spatial_vtk.spatial.calculate.patterns",
    "PCASpatialModeResult": "spatial_vtk.spatial.calculate.pca",
    "PolygonCorridorConfig": "spatial_vtk.spatial.calculate.corridors",
    "rotate_ne_to_rt": "spatial_vtk.spatial.calculate.rotation",
    "rotate_rt_to_ne": "spatial_vtk.spatial.calculate.rotation",
    "run_boundary_corridor_workflow": "spatial_vtk.spatial.calculate.corridors",
    "run_boundary_corridor_workflow_from_config": "spatial_vtk.spatial.calculate.corridors",
    "run_geojson_region_summary_workflow": "spatial_vtk.spatial.calculate.geojson",
    "run_geojson_region_summary_workflow_from_config": "spatial_vtk.spatial.calculate.geojson",
    "run_geology_spatial_tests": "spatial_vtk.spatial.calculate.geology",
    "run_residual_feature_clustering": "spatial_vtk.spatial.calculate.clustering",
    "run_spatial_derived_outputs_workflow": "spatial_vtk.spatial.calculate.workflow",
    "run_spatial_derived_outputs_workflow_from_config": "spatial_vtk.spatial.calculate.workflow",
    "run_spatial_statistics_workflow": "spatial_vtk.spatial.calculate.workflow",
    "run_spatial_statistics_workflow_from_config": "spatial_vtk.spatial.calculate.workflow",
    "select_events_in_corridors": "spatial_vtk.spatial.calculate.corridors",
    "select_geojson_polygons": "spatial_vtk.spatial.calculate.geojson",
    "select_near_edge_stations": "spatial_vtk.spatial.calculate.polygon_edges",
    "select_records_by_corridors": "spatial_vtk.spatial.calculate.corridors",
    "serialize_corridor_geometries": "spatial_vtk.spatial.calculate.corridors",
    "SPATIAL_DERIVED_OUTPUT_KEYS": "spatial_vtk.spatial.calculate.workflow",
    "SPATIAL_DERIVED_OUTPUT_PATH_NAMES": "spatial_vtk.spatial.calculate.workflow",
    "SPATIAL_STATISTICS_OUTPUT_DESCRIPTIONS": "spatial_vtk.spatial.calculate.workflow",
    "SPATIAL_STATISTICS_OUTPUT_NAMES": "spatial_vtk.spatial.calculate.workflow",
    "SPATIAL_SUMMARY_OUTPUT_KEYS": "spatial_vtk.spatial.calculate.workflow",
    "SPATIAL_SUMMARY_OUTPUT_PATH_NAMES": "spatial_vtk.spatial.calculate.workflow",
    "spatial_correlation_preview_frame": "spatial_vtk.spatial.calculate.workflow",
    "spatial_derived_outputs_readiness_from_config": "spatial_vtk.spatial.calculate.workflow",
    "SpatialDerivedOutputsWorkflowResult": "spatial_vtk.spatial.calculate.workflow",
    "spatial_metric_product_frames": "spatial_vtk.spatial.calculate.workflow",
    "spatial_metric_product_summary_frame": "spatial_vtk.spatial.calculate.workflow",
    "spatial_metric_table_frame": "spatial_vtk.spatial.calculate.workflow",
    "spatial_pca_product_frames": "spatial_vtk.spatial.calculate.workflow",
    "spatial_statistics_output_paths": "spatial_vtk.spatial.calculate.workflow",
    "spatial_statistics_settings_from_config": "spatial_vtk.spatial.calculate.settings",
    "SpatialStatisticsSettings": "spatial_vtk.spatial.calculate.settings",
    "SpatialStatisticsWorkflowResult": "spatial_vtk.spatial.calculate.workflow",
    "spatial_summary_readiness_from_config": "spatial_vtk.spatial.calculate.workflow",
    "spatial_workflow_failure_frame": "spatial_vtk.spatial.calculate.workflow",
    "StandardSpatialProductSummaryResult": "spatial_vtk.spatial.calculate.workflow",
    "StandardSpatialWorkflowOutputResult": "spatial_vtk.spatial.calculate.workflow",
    "StandardSpatialWorkflowOutputStatusResult": "spatial_vtk.spatial.calculate.workflow",
    "station_bias_preview_frame": "spatial_vtk.spatial.calculate.workflow",
    "summarize_corridor_event_counts": "spatial_vtk.spatial.calculate.corridors",
    "summarize_metrics_by_geojson": "spatial_vtk.spatial.calculate.geojson",
    "summarize_residuals_by_path_bin": "spatial_vtk.spatial.calculate.paths",
    "summarize_standard_spatial_products": "spatial_vtk.spatial.calculate.workflow",
    "summarize_station_bias": "spatial_vtk.spatial.calculate.prepare_stats",
}

__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    """Load one spatial calculation helper lazily."""

    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module 'spatial_vtk.spatial.calculate' has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
