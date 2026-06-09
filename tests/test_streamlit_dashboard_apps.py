from __future__ import annotations

import csv
import importlib

import pandas as pd

from spatial_vtk.visualize.dashboard import (
    available_dashboard_value_columns,
    band_display_label,
    build_event_folium_map,
    build_metric_heatmap_figure,
    build_path_heatmap_figure,
    build_qc_histogram_figure,
    build_station_folium_map,
    build_streamlit_command,
    display_table,
    filter_dashboard_metrics,
    filter_qc_dashboard_rows,
    metric_display_name,
    normalize_manual_review_queue,
    queue_to_csv_bytes,
    validate_dashboard_tables,
    validate_trace_qc_dashboard_table,
    write_manual_review_queue,
)
from spatial_vtk.visualize.dashboard.tables import build_dashboard_summaries
from spatial_vtk.visualize.dashboard.streamlit_metrics import _available_nonempty_value_columns
from spatial_vtk.visualize.selection import FigureSelection, configured_band_options


def _metric_rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "model": ["m1", "m1", "m2", "m2"],
            "metric": ["PGA", "PGA", "PGA", "PGA"],
            "band": ["2-4", "2-4", "2-4", "2-4"],
            "component": ["R", "T", "R", "T"],
            "station": ["STA1", "STA2", "STA1", "STA2"],
            "event_id": ["ev1", "ev1", "ev2", "ev2"],
            "sta_lat": [34.0, 34.1, 34.0, 34.1],
            "sta_lon": [-118.1, -118.2, -118.1, -118.2],
            "event_lat": [33.9, 33.9, 34.2, 34.2],
            "event_lon": [-118.3, -118.3, -117.9, -117.9],
            "distance_km": [10.0, 20.0, 30.0, 40.0],
            "azimuth_deg": [45.0, 90.0, 135.0, 180.0],
            "Vs30": [350.0, 500.0, 350.0, 500.0],
            "value_obs": [2.0, 3.0, 2.5, 3.5],
            "value_syn": [1.0, 4.0, 2.0, 2.5],
            "residual": [1.0, -1.0, 0.5, 1.0],
            "log2_residual": [1.0, -0.415, 0.322, 0.485],
            "ln_residual": [0.693, -0.288, 0.223, 0.336],
            "anderson_2004_gof": [8.0, 7.0, 9.0, 6.0],
            "olsen_mayhew_gof": [80.0, 70.0, 90.0, 60.0],
            "score": [0.8, 0.7, 0.9, 0.6],
        }
    )


def _qc_rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": ["ev1", "ev1", "ev2"],
            "station": ["STA1", "STA1", "STA2"],
            "component": ["R", "T", "R"],
            "network": ["CI", "CI", "CI"],
            "station_family": ["broadband", "broadband", "strong_motion"],
            "magnitude": [4.0, 4.0, 5.0],
            "distance_km": [20.0, 20.0, 50.0],
            "event_date": ["2026-01-01", "2026-01-01", "2026-01-02"],
            "raw_peak_abs": [1.0, 2.0, 3.0],
            "band_peak_abs_2_4s": [0.5, 0.8, 1.2],
            "energy_frac_2_4s": [0.2, 0.3, 0.4],
            "dominant_band_label": ["2-4", "2-4", "4-8"],
            "metadata_warning": ["", "timing", ""],
            "event_lat": [34.0, 34.0, 34.1],
            "event_lon": [-118.0, -118.0, -118.2],
            "station_lat": [34.2, 34.2, 34.3],
            "station_lon": [-118.4, -118.4, -118.5],
            "source_context_count": [1, 1, 2],
            "source_contexts": ["example", "example", "example2"],
        }
    )


def test_dashboard_summaries_preserve_transform_columns():
    summaries = validate_dashboard_tables(build_dashboard_summaries(_metric_rows(), hex_dist=10.0, hex_az=45.0))
    station = summaries["station_rollup"]
    columns = available_dashboard_value_columns(station)
    assert "med_value_obs" in columns
    assert "med_log2_residual" in columns
    assert "med_anderson_2004_gof" in columns
    assert "med_olsen_mayhew_gof" in columns
    assert "component" in station.columns


def test_dashboard_summaries_do_not_require_residual_column():
    rows = _metric_rows().drop(columns=["residual", "score"])
    summaries = validate_dashboard_tables(build_dashboard_summaries(rows, hex_dist=10.0, hex_az=45.0))
    assert summaries["model_metric_band"]["n"].sum() == len(rows)
    columns = available_dashboard_value_columns(summaries["model_metric_band"])
    assert "med_value_obs" in columns
    assert "med_log2_residual" in columns


def test_dashboard_summaries_preserve_pair_only_value_column():
    rows = pd.DataFrame(
        {
            "model": ["m1", "m1"],
            "metric": ["original_cc", "traveltime_delay"],
            "band": ["2-4s", "2-4s"],
            "component": ["R", "R"],
            "station": ["STA1", "STA1"],
            "event_id": ["ev1", "ev1"],
            "value": [0.91, 0.35],
        }
    )
    summaries = validate_dashboard_tables(build_dashboard_summaries(rows))
    columns = available_dashboard_value_columns(summaries["model_metric_band"])
    assert "med_value" in columns
    nonempty = _available_nonempty_value_columns(summaries["model_metric_band"])
    assert nonempty == ["med_value"]
    assert set(summaries["model_metric_band"]["n"]) == {1}
    assert summaries["model_metric_band"]["med_value"].notna().all()


def test_dashboard_labels_and_filters_are_public_facing():
    assert metric_display_name("C5") == "Peak acceleration (PGA)"
    assert metric_display_name("arias_duration") == "Arias duration (5-95%)"
    assert band_display_label("2-4") == "2-4 sec"
    filtered = filter_dashboard_metrics(_metric_rows(), metric="C5", bands=["2-4 sec"], value_column="log2_residual", distance_range_km=(0, 25))
    assert set(filtered["station"]) == {"STA1", "STA2"}
    assert set(filtered["metric"]) == {"PGA"}

    preview = display_table(
        filtered,
        columns=["event_id", "station", "component", "band", "metric", "value_obs", "value_syn", "log2_residual", "anderson_2004_gof"],
        max_rows=1,
    )
    assert list(preview.columns) == [
        "Event ID",
        "Station",
        "Component",
        "Period Band",
        "Metric",
        "Observed Value",
        "Synthetic Value",
        "Log2 Residual",
        "Anderson 2004 GOF",
    ]
    assert preview["Metric"].iloc[0] == "Peak acceleration (PGA)"
    assert preview["Period Band"].iloc[0] == "2-4 sec"


def test_figure_selection_uses_config_for_bands_components_and_sublists(tmp_path):
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
run_defaults:
  commands:
    metrics.dashboard:
      components: [R]
      passbands: ["2-4"]
      events: [ev1]
      stations: [STA1]
      bounds: la
bounds:
  presets:
    la:
      lon_min: -119
      lon_max: -117
      lat_min: 33
      lat_max: 35
""",
        encoding="utf-8",
    )
    selection = FigureSelection.from_config(config_path, command="metrics.dashboard")
    filtered = selection.apply(_metric_rows())
    assert len(filtered) == 1
    assert filtered.iloc[0]["station"] == "STA1"
    assert selection.bounds == (-119.0, -117.0, 33.0, 35.0)
    assert configured_band_options(config_path, command="metrics.dashboard") == ["2-4"]


def test_dashboard_maps_and_charts_render_html_and_figures():
    summaries = build_dashboard_summaries(_metric_rows(), hex_dist=10.0, hex_az=45.0)
    station_map = build_station_folium_map(summaries["station_rollup"], value_col="med_log2_residual", basemap="Carto Light", marker_cluster=False)
    event_map = build_event_folium_map(summaries["event_rollup"], value_col="med_anderson_2004_gof", basemap="Carto Light", marker_cluster=False)
    assert "leaflet" in station_map.get_root().render().lower()
    assert "leaflet" in event_map.get_root().render().lower()
    heat = build_metric_heatmap_figure(summaries["model_metric_band"], value_col="med_log2_residual")
    path = build_path_heatmap_figure(summaries["path_hex"], value_col="med_log2_residual")
    assert heat.layout.title.text
    assert path.layout.title.text


def test_qc_filter_histogram_and_manual_queue_export(tmp_path):
    qc = validate_trace_qc_dashboard_table(_qc_rows())
    filtered = filter_qc_dashboard_rows(qc, component_filter="R", band="2-4 sec")
    assert len(filtered) == 1
    figure = build_qc_histogram_figure(filtered, value_col="band_peak_abs_2_4s")
    assert figure.layout.title.text
    queue = normalize_manual_review_queue([{"event_id": "ev1", "station": "sta1"}])
    assert queue == [
        {
            "event_id": "ev1",
            "station": "STA1",
            "event_title": "",
            "event_lat": "",
            "event_lon": "",
            "station_lat": "",
            "station_lon": "",
            "network": "",
            "distance_km": "",
            "source_context_count": "",
            "source_contexts": "",
        }
    ]
    path = write_manual_review_queue(filtered, tmp_path / "queue.csv")
    with path.open(newline="") as fp:
        rows = list(csv.DictReader(fp))
    assert rows[0]["event_id"] == "ev1"
    assert rows[0]["station"] == "STA1"
    assert set(rows[0]) >= {"event_id", "station", "event_lat", "station_lat", "distance_km"}
    assert b"event_id,station" in queue_to_csv_bytes(queue)


def test_qc_filter_accepts_timezone_aware_event_dates():
    qc = validate_trace_qc_dashboard_table(_qc_rows())
    qc["event_date"] = pd.to_datetime(qc["event_date"], utc=True)
    filtered = filter_qc_dashboard_rows(qc, date_range=(pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-01")))
    assert set(filtered["event_id"]) == {"ev1"}


def test_streamlit_entrypoints_import_and_launch_command():
    importlib.import_module("spatial_vtk.visualize.dashboard.streamlit_metrics")
    importlib.import_module("spatial_vtk.visualize.dashboard.streamlit_qc")
    command = build_streamlit_command("/tmp/app.py", server_address="0.0.0.0", server_port=8509, show=False)
    assert command[:4][-2:] == ["streamlit", "run"]
    assert "--server.port" in command
    assert "8509" in command
