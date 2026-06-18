"""Dashboard preparation helpers.

The dashboard package re-exports preparation, readiness, launch, chart, map, and
filter helpers while keeping optional dashboard dependencies lazy. Importing
``spatial_vtk.visualize.dashboard`` should not import Streamlit, Plotly, or
Folium-backed builders until the corresponding helper is requested.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MODULES = {
    "add_dashboard_path_geometry": "spatial_vtk.visualize.dashboard.export",
    "dashboard_metric_dataset_paths": "spatial_vtk.visualize.dashboard.export",
    "forward_azimuth_deg": "spatial_vtk.visualize.dashboard.export",
    "haversine_km": "spatial_vtk.visualize.dashboard.export",
    "load_dashboard_metric_dataset": "spatial_vtk.visualize.dashboard.export",
    "safe_path_token": "spatial_vtk.visualize.dashboard.export",
    "write_configured_dashboard_datasets": "spatial_vtk.visualize.dashboard.export",
    "write_dashboard_metric_dataset": "spatial_vtk.visualize.dashboard.export",
    "write_dashboard_summary_dataset": "spatial_vtk.visualize.dashboard.export",
    "build_metric_heatmap_figure": "spatial_vtk.visualize.dashboard.charts",
    "build_path_heatmap_figure": "spatial_vtk.visualize.dashboard.charts",
    "build_qc_bar_figure": "spatial_vtk.visualize.dashboard.charts",
    "build_qc_histogram_figure": "spatial_vtk.visualize.dashboard.charts",
    "build_value_histogram_figure": "spatial_vtk.visualize.dashboard.charts",
    "build_value_vs_distance_figure": "spatial_vtk.visualize.dashboard.charts",
    "dashboard_map_readiness": "spatial_vtk.visualize.dashboard.contracts",
    "dashboard_metric_dataset_readiness_frame": "spatial_vtk.visualize.dashboard.contracts",
    "dashboard_output_namespace": "spatial_vtk.visualize.dashboard.contracts",
    "dashboard_output_paths": "spatial_vtk.visualize.dashboard.contracts",
    "dashboard_output_readiness": "spatial_vtk.visualize.dashboard.contracts",
    "dashboard_output_status_frame": "spatial_vtk.visualize.dashboard.contracts",
    "dashboard_qc_trace_readiness_frame": "spatial_vtk.visualize.dashboard.contracts",
    "dashboard_ready_value": "spatial_vtk.visualize.dashboard.contracts",
    "dashboard_readiness_summary_frame": "spatial_vtk.visualize.dashboard.contracts",
    "dashboard_row_level_columns": "spatial_vtk.visualize.dashboard.contracts",
    "dashboard_summary_readiness_frame": "spatial_vtk.visualize.dashboard.contracts",
    "dashboard_summary_table_contracts": "spatial_vtk.visualize.dashboard.contracts",
    "dashboard_summary_table_paths": "spatial_vtk.visualize.dashboard.contracts",
    "load_dashboard_summary_tables": "spatial_vtk.visualize.dashboard.contracts",
    "preview_dashboard_summary_tables": "spatial_vtk.visualize.dashboard.contracts",
    "read_dashboard_table": "spatial_vtk.visualize.dashboard.contracts",
    "validate_dashboard_tables": "spatial_vtk.visualize.dashboard.contracts",
    "validate_trace_qc_dashboard_table": "spatial_vtk.visualize.dashboard.contracts",
    "normalize_manual_review_queue": "spatial_vtk.visualize.dashboard.exports",
    "queue_to_csv_bytes": "spatial_vtk.visualize.dashboard.exports",
    "write_dashboard_filtered_export": "spatial_vtk.visualize.dashboard.exports",
    "write_manual_review_queue": "spatial_vtk.visualize.dashboard.exports",
    "filter_dashboard_metrics": "spatial_vtk.visualize.dashboard.filters",
    "filter_optional_dashboard_summary": "spatial_vtk.visualize.dashboard.filters",
    "filter_qc_dashboard_rows": "spatial_vtk.visualize.dashboard.filters",
    "row_value_column_for_summary": "spatial_vtk.visualize.dashboard.filters",
    "available_dashboard_value_columns": "spatial_vtk.visualize.dashboard.labels",
    "band_display_label": "spatial_vtk.visualize.dashboard.labels",
    "column_display_lookup": "spatial_vtk.visualize.dashboard.labels",
    "column_display_name": "spatial_vtk.visualize.dashboard.labels",
    "display_table": "spatial_vtk.visualize.dashboard.labels",
    "metric_display_name": "spatial_vtk.visualize.dashboard.labels",
    "value_column_display_name": "spatial_vtk.visualize.dashboard.labels",
    "build_streamlit_command": "spatial_vtk.visualize.dashboard.launch",
    "DashboardLaunchResult": "spatial_vtk.visualize.dashboard.launch",
    "find_available_port": "spatial_vtk.visualize.dashboard.launch",
    "launch_configured_dashboards_from_notebook_settings": "spatial_vtk.visualize.dashboard.launch",
    "launch_configured_metrics_dashboard": "spatial_vtk.visualize.dashboard.launch",
    "launch_configured_qc_dashboard": "spatial_vtk.visualize.dashboard.launch",
    "launch_metrics_dashboard": "spatial_vtk.visualize.dashboard.launch",
    "launch_qc_dashboard": "spatial_vtk.visualize.dashboard.launch",
    "launch_streamlit_dashboard": "spatial_vtk.visualize.dashboard.launch",
    "build_event_folium_map": "spatial_vtk.visualize.dashboard.maps",
    "build_station_folium_map": "spatial_vtk.visualize.dashboard.maps",
    "render_folium_html": "spatial_vtk.visualize.dashboard.maps",
    "build_dashboard_summaries": "spatial_vtk.visualize.dashboard.tables",
    "dashboard_summary_input_columns": "spatial_vtk.visualize.dashboard.tables",
    "prepare_dashboard_metric_table": "spatial_vtk.visualize.dashboard.tables",
    "write_dashboard_summaries": "spatial_vtk.visualize.dashboard.tables",
}

__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    """Load one dashboard helper on demand."""

    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
