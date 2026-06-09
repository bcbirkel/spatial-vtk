"""Dashboard preparation helpers."""

from __future__ import annotations

from spatial_vtk.visualize.dashboard.export import (
    add_dashboard_path_geometry,
    forward_azimuth_deg,
    haversine_km,
    load_dashboard_metric_dataset,
    safe_path_token,
    write_dashboard_metric_dataset,
    write_dashboard_summary_dataset,
)
from spatial_vtk.visualize.dashboard.charts import (
    build_metric_heatmap_figure,
    build_path_heatmap_figure,
    build_qc_bar_figure,
    build_qc_histogram_figure,
    build_value_histogram_figure,
    build_value_vs_distance_figure,
)
from spatial_vtk.visualize.dashboard.contracts import (
    load_dashboard_summary_tables,
    read_dashboard_table,
    validate_dashboard_tables,
    validate_trace_qc_dashboard_table,
)
from spatial_vtk.visualize.dashboard.exports import (
    normalize_manual_review_queue,
    queue_to_csv_bytes,
    write_dashboard_filtered_export,
    write_manual_review_queue,
)
from spatial_vtk.visualize.dashboard.filters import filter_dashboard_metrics, filter_qc_dashboard_rows
from spatial_vtk.visualize.dashboard.labels import (
    available_dashboard_value_columns,
    band_display_label,
    column_display_lookup,
    column_display_name,
    display_table,
    metric_display_name,
    value_column_display_name,
)
from spatial_vtk.visualize.dashboard.launch import (
    build_streamlit_command,
    launch_metrics_dashboard,
    launch_qc_dashboard,
    launch_streamlit_dashboard,
)
from spatial_vtk.visualize.dashboard.maps import build_event_folium_map, build_station_folium_map, render_folium_html
from spatial_vtk.visualize.dashboard.tables import (
    build_dashboard_summaries,
    prepare_dashboard_metric_table,
    write_dashboard_summaries,
)

__all__ = [
    "add_dashboard_path_geometry",
    "available_dashboard_value_columns",
    "band_display_label",
    "column_display_lookup",
    "column_display_name",
    "display_table",
    "build_event_folium_map",
    "build_dashboard_summaries",
    "build_metric_heatmap_figure",
    "build_path_heatmap_figure",
    "build_qc_bar_figure",
    "build_qc_histogram_figure",
    "build_station_folium_map",
    "build_streamlit_command",
    "build_value_histogram_figure",
    "build_value_vs_distance_figure",
    "filter_dashboard_metrics",
    "filter_qc_dashboard_rows",
    "forward_azimuth_deg",
    "haversine_km",
    "launch_metrics_dashboard",
    "launch_qc_dashboard",
    "launch_streamlit_dashboard",
    "load_dashboard_metric_dataset",
    "load_dashboard_summary_tables",
    "metric_display_name",
    "normalize_manual_review_queue",
    "prepare_dashboard_metric_table",
    "queue_to_csv_bytes",
    "read_dashboard_table",
    "render_folium_html",
    "safe_path_token",
    "validate_dashboard_tables",
    "validate_trace_qc_dashboard_table",
    "value_column_display_name",
    "write_dashboard_filtered_export",
    "write_dashboard_metric_dataset",
    "write_dashboard_summaries",
    "write_dashboard_summary_dataset",
    "write_manual_review_queue",
]
