from __future__ import annotations

import csv
import importlib
from pathlib import Path
import socket

import pandas as pd
import pytest

from spatial_vtk.config import SpatialVTKConfig, clear_active_config
from spatial_vtk.visualize.dashboard import (
    available_dashboard_value_columns,
    band_display_label,
    build_event_folium_map,
    build_metric_heatmap_figure,
    build_path_heatmap_figure,
    build_qc_histogram_figure,
    build_station_folium_map,
    build_streamlit_command,
    dashboard_map_readiness,
    dashboard_output_namespace,
    dashboard_output_paths,
    dashboard_output_status_frame,
    dashboard_qc_trace_readiness_frame,
    dashboard_ready_value,
    dashboard_summary_readiness_frame,
    dashboard_summary_table_contracts,
    dashboard_summary_table_paths,
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
from spatial_vtk.visualize.dashboard.streamlit_metrics import _empty_rows_message as _metrics_empty_rows_message
import spatial_vtk.visualize.dashboard.streamlit_metrics as streamlit_metrics
from spatial_vtk.visualize.dashboard.streamlit_metrics import _metrics_dashboard_startup_blocker
from spatial_vtk.visualize.dashboard.streamlit_metrics import _summary_readiness_message
from spatial_vtk.visualize.dashboard.streamlit_metrics import _value_columns_or_message
from spatial_vtk.visualize.dashboard.streamlit_qc import _qc_chart_columns_or_message
from spatial_vtk.visualize.dashboard.streamlit_qc import _qc_dashboard_startup_blocker
from spatial_vtk.visualize.dashboard.streamlit_qc import _empty_rows_message as _qc_empty_rows_message
from spatial_vtk.visualize.dashboard.streamlit_qc import _missing_columns_message as _qc_missing_columns_message
import spatial_vtk.visualize.dashboard.streamlit_qc as streamlit_qc
import spatial_vtk.visualize.dashboard.launch as dashboard_launch
from spatial_vtk.visualize.dashboard.launch import _raise_if_port_in_use
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


def test_dashboard_output_helpers_use_configured_roots(tmp_path):
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  tables: outputs/tables
  dashboards: outputs/dashboards
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)

    paths = dashboard_output_paths(cfg=cfg)
    namespace = dashboard_output_namespace(cfg=cfg)
    assert paths["metrics_long_path"] == tmp_path / "outputs" / "tables" / "metrics_long.parquet"
    assert namespace.metrics_long_path == paths["metrics_long_path"]
    assert paths["metrics_dashboard_root"] == tmp_path / "outputs" / "dashboards" / "metrics_dashboard"
    assert namespace.metrics_dashboard_root == paths["metrics_dashboard_root"]
    assert paths["dashboard_summary_root"] == tmp_path / "outputs" / "dashboards" / "dashboard_summaries"
    assert namespace.dashboard_summary_root == paths["dashboard_summary_root"]
    assert paths["station_rollup_summary_path"] == tmp_path / "outputs" / "dashboards" / "dashboard_summaries" / "station_rollup.parquet"
    assert paths["qc_trace_summary_path"] == tmp_path / "outputs" / "tables" / "qc_trace_summary.csv"

    existing = paths["dashboard_summary_root"] / "station_rollup.csv"
    existing.write_text("station,model,metric,band,n\nSTA,m1,PGA,1-2 sec,1\n", encoding="utf-8")
    ready_summary = paths["dashboard_summary_root"] / "model_metric_band.csv"
    ready_summary.write_text("model,metric,band,n,med_log2_residual\nm1,PGA,1-2 sec,1,0.25\n", encoding="utf-8")
    summary_paths = dashboard_summary_table_paths(paths["dashboard_summary_root"])
    assert summary_paths["station_rollup_summary_path"] == existing

    status = dashboard_output_status_frame(cfg=cfg)
    assert "name" in status.columns
    assert "metrics_dashboard_root" in set(status["name"])
    assert "qc_trace_summary_path" in set(status["name"])
    assert "path_hex_summary_path" in set(status["name"])
    assert "dashboard_tabs" in status.columns
    station_status = status.loc[status["name"].eq("station_rollup_summary_path")].iloc[0]
    assert station_status["dashboard_table"] == "station_rollup"
    assert station_status["dashboard_tabs"] == "Stations"
    assert "station" in station_status["required_columns"]
    assert station_status["ready"] is False
    assert station_status["readiness"] == "no_value_data"
    assert station_status["row_count"] == 1
    assert "finite dashboard value" in station_status["message"]
    assert station_status["map_ready"] is False
    assert "coordinate columns" in station_status["map_message"]

    model_status = status.loc[status["name"].eq("model_metric_band_summary_path")].iloc[0]
    assert model_status["ready"] is True
    assert model_status["readiness"] == "ready"
    assert model_status["nonempty_value_columns"] == "med_log2_residual"

    missing_status = status.loc[status["name"].eq("path_hex_summary_path")].iloc[0]
    assert missing_status["ready"] is False
    assert missing_status["readiness"] == "missing"
    assert "dist_bin_km" in missing_status["missing_columns"]

    qc_status = status.loc[status["name"].eq("qc_trace_summary_path")].iloc[0]
    assert qc_status["dashboard_table"] == "qc_trace_summary"
    assert qc_status["dashboard_tabs"] == "QC Overview, Charts, Review Queue"
    assert qc_status["ready"] is False
    assert qc_status["readiness"] == "missing"
    assert "event_id" in qc_status["required_columns"]
    assert "QC trace-summary table is missing" in qc_status["message"]

    readiness = dashboard_summary_readiness_frame(paths["dashboard_summary_root"])
    assert set(readiness["dashboard_table"]) == {"model_metric_band", "station_rollup", "event_rollup", "path_hex"}
    assert readiness.loc[readiness["dashboard_table"].eq("model_metric_band"), "ready"].iloc[0] is True
    assert _metrics_dashboard_startup_blocker(readiness) is None

    blocked = readiness.copy()
    blocked.loc[blocked["dashboard_table"].eq("model_metric_band"), "ready"] = False
    blocked.loc[blocked["dashboard_table"].eq("model_metric_band"), "message"] = "model table is empty"
    assert _metrics_dashboard_startup_blocker(blocked) == "model table is empty"

    contracts = dashboard_summary_table_contracts()
    assert set(contracts["table"]) == {"model_metric_band", "station_rollup", "event_rollup", "path_hex"}
    assert "Compare Models" in contracts.loc[contracts["table"].eq("model_metric_band"), "tabs"].iloc[0]
    assert "oscillator-period" in contracts.loc[contracts["table"].eq("model_metric_band"), "purpose"].iloc[0]
    station_contract = contracts.loc[contracts["table"].eq("station_rollup")].iloc[0]
    event_contract = contracts.loc[contracts["table"].eq("event_rollup")].iloc[0]
    assert "sta_lon" in station_contract["map_coordinate_columns"]
    assert "sta_lat" in station_contract["map_coordinate_columns"]
    assert "event_lon" in event_contract["map_coordinate_columns"]
    assert "event_lat" in event_contract["map_coordinate_columns"]

    station_map_status = dashboard_map_readiness(
        pd.DataFrame({"station": ["STA"], "model": ["m1"], "metric": ["PGA"], "band": ["1-2 sec"], "n": [1], "med_log2_residual": [0.1]}),
        "station_rollup",
    )
    assert station_map_status["ready"] is False
    assert "longitude" in station_map_status["missing_columns"]


def test_dashboard_qc_trace_readiness_is_bounded_and_schema_aware(tmp_path):
    ready_path = tmp_path / "qc_trace_summary.csv"
    ready_path.write_text("event_id,station,component,qc_status\nev1,STA,R,pass\n", encoding="utf-8")

    ready = dashboard_qc_trace_readiness_frame(ready_path)
    ready_row = ready.iloc[0]
    assert ready_row["ready"] is True
    assert ready_row["readiness"] == "ready"
    assert ready_row["row_count"] == 1
    assert ready_row["dashboard_table"] == "qc_trace_summary"

    missing_column_path = tmp_path / "bad_qc_trace_summary.csv"
    missing_column_path.write_text("event_id,component\nev1,R\n", encoding="utf-8")

    missing_column = dashboard_qc_trace_readiness_frame(missing_column_path)
    missing_row = missing_column.iloc[0]
    assert missing_row["ready"] is False
    assert missing_row["readiness"] == "missing_columns"
    assert missing_row["row_count"] == 1
    assert missing_row["missing_columns"] == "station"


def test_qc_dashboard_preflights_trace_summary_before_full_load(tmp_path, monkeypatch):
    """QC dashboard startup should block schema-bad inputs before full table reads."""

    missing_column_path = tmp_path / "bad_qc_trace_summary.csv"
    missing_column_path.write_text("event_id,component\nev1,R\n", encoding="utf-8")
    calls: list[tuple[str, tuple[str, ...]]] = []

    class FakeStreamlit:
        query_params: dict[str, str] = {}

        def __init__(self) -> None:
            self.warnings: list[str] = []
            self.frames: list[pd.DataFrame] = []

        def set_page_config(self, **kwargs):  # noqa: ANN001, ANN003
            return None

        def title(self, text):  # noqa: ANN001
            return None

        def info(self, text):  # noqa: ANN001
            return None

        def warning(self, text):  # noqa: ANN001
            self.warnings.append(str(text))

        def error(self, text):  # noqa: ANN001
            raise AssertionError(f"unexpected Streamlit error: {text}")

        def dataframe(self, frame, **kwargs):  # noqa: ANN001, ANN003
            self.frames.append(frame)

    fake_st = FakeStreamlit()

    def fail_if_loaded(path: str) -> pd.DataFrame:
        calls.append(path)
        raise AssertionError("full trace summary loader should not run for schema-bad input")

    monkeypatch.setenv("SVTK_TRACE_SUMMARY", str(missing_column_path))
    monkeypatch.delenv("SVTK_CONFIG_FILE", raising=False)
    monkeypatch.setattr(streamlit_qc, "st", fake_st)
    monkeypatch.setattr(streamlit_qc, "_load_trace_summary_cached", fail_if_loaded)

    streamlit_qc.main()

    assert calls == []
    assert any("not ready" in message for message in fake_st.warnings)
    assert fake_st.frames
    assert fake_st.frames[0].loc[0, "Readiness"] == "missing_columns"
    assert fake_st.frames[0].loc[0, "Missing Columns"] == "station"


def test_qc_dashboard_startup_blocker_uses_readiness_message(tmp_path):
    """QC dashboard blocker should expose the bounded readiness message."""

    missing_column_path = tmp_path / "bad_qc_trace_summary.csv"
    missing_column_path.write_text("event_id,component\nev1,R\n", encoding="utf-8")
    readiness = dashboard_qc_trace_readiness_frame(missing_column_path)

    message = _qc_dashboard_startup_blocker(readiness)

    assert message is not None
    assert "station" in message


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

    mixed_periods = pd.DataFrame(
        {
            "model": ["m1", "m1", "m1"],
            "metric": ["PSA", "PSA", "PGA"],
            "band": ["", "", "1-2 sec"],
            "period_s": [1.0, 2.0, pd.NA],
            "log2_residual": [0.1, 0.2, -0.3],
        }
    )
    period_filtered = filter_dashboard_metrics(
        mixed_periods,
        bands=["1-2 sec"],
        periods_s=[2.0],
        value_column="log2_residual",
    )
    assert period_filtered["metric"].tolist() == ["PSA", "PGA"]
    assert period_filtered["period_s"].iloc[0] == 2.0
    assert pd.isna(period_filtered["period_s"].iloc[1])

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
    command = build_streamlit_command("/tmp/app.py", server_address="0.0.0.0", server_port=8509, show=False, proxy_mode=True)
    assert command[:4][-2:] == ["streamlit", "run"]
    assert "--server.port" in command
    assert "8509" in command
    assert "--server.enableCORS=false" in command
    assert "--server.enableXsrfProtection=false" in command
    assert "--browser.gatherUsageStats=false" in command


def test_dashboard_empty_state_messages_are_explicit():
    assert _metrics_empty_rows_message("station") == "No station rows match the selected filters."
    assert _qc_empty_rows_message("trace QC") == "No trace QC rows match the selected filters."
    assert _qc_missing_columns_message("timing") == "No timing columns are available in the loaded trace-summary table."


def test_metrics_value_selector_reports_why_no_value_can_be_selected():
    empty = pd.DataFrame(columns=["model", "metric", "band", "med_log2_residual"])
    columns, message = _value_columns_or_message(empty)
    assert columns == []
    assert message == "No model/metric/passband-or-period rows match the selected filters."

    missing_values = pd.DataFrame({"model": ["m1"], "metric": ["PGA"], "band": ["2-4"]})
    columns, message = _value_columns_or_message(missing_values)
    assert columns == []
    assert message == "No observed, synthetic, residual, or score value columns are present in the model/metric/passband-or-period summary."

    all_missing = pd.DataFrame({"model": ["m1"], "metric": ["PGA"], "band": ["2-4"], "med_log2_residual": [pd.NA]})
    columns, message = _value_columns_or_message(all_missing)
    assert columns == ["med_log2_residual"]
    assert message == "The selected model/metric/passband-or-period rows have dashboard value columns, but all selected values are missing or non-finite."

    ready = pd.DataFrame({"model": ["m1"], "metric": ["PGA"], "band": ["2-4"], "med_log2_residual": [0.5]})
    columns, message = _value_columns_or_message(ready)
    assert columns == ["med_log2_residual"]
    assert message is None


def test_metrics_dashboard_main_uses_cached_summary_loader(monkeypatch):
    """Streamlit reruns should use the cached summary-table loader."""

    summaries = {
        "model_metric_band": pd.DataFrame({"model": ["m1"], "metric": ["PGA"], "band": ["2-4"], "n": [1], "med_log2_residual": [0.5]}),
        "station_rollup": pd.DataFrame({"station": ["STA"], "model": ["m1"], "metric": ["PGA"], "band": ["2-4"], "n": [1], "med_log2_residual": [0.5]}),
        "event_rollup": pd.DataFrame({"event_id": ["ev1"], "model": ["m1"], "metric": ["PGA"], "band": ["2-4"], "n": [1], "med_log2_residual": [0.5]}),
        "path_hex": pd.DataFrame({"model": ["m1"], "metric": ["PGA"], "band": ["2-4"], "dist_bin_km": [10.0], "az_bin_deg": [45.0], "n": [1], "med_log2_residual": [0.5]}),
    }
    readiness = pd.DataFrame({"dashboard_table": ["model_metric_band"], "ready": [True], "message": ["ready"]})
    calls: list[str] = []
    rendered: dict[str, object] = {}

    def fake_path_setting(query_key: str, env_key: str) -> str:  # noqa: ARG001
        return {"metrics_root": "metrics-root", "summary_root": "summary-root", "config": ""}.get(query_key, "")

    def fake_cached_loader(summary_root: str, skip_tables: tuple[str, ...] = ()) -> dict[str, pd.DataFrame]:
        calls.append((summary_root, skip_tables))
        return summaries

    def fail_uncached_loader(summary_root: str):  # noqa: ANN001, ARG001
        raise AssertionError("main should use _load_summary_tables_cached")

    def fake_render_dashboard(loaded, long_metrics, config, *, readiness):  # noqa: ANN001
        rendered["summaries"] = loaded
        rendered["long_metrics"] = long_metrics
        rendered["config"] = config
        rendered["readiness"] = readiness

    monkeypatch.setattr(streamlit_metrics, "_path_setting", fake_path_setting)
    monkeypatch.setattr(streamlit_metrics, "_load_summary_tables_cached", fake_cached_loader)
    monkeypatch.setattr(streamlit_metrics, "load_dashboard_summary_tables", fail_uncached_loader)
    monkeypatch.setattr(streamlit_metrics, "dashboard_summary_readiness_frame", lambda *args, **kwargs: readiness)
    monkeypatch.setattr(streamlit_metrics, "_try_load_long_metrics", lambda metrics_root: pd.DataFrame({"metric": ["PGA"]}))
    monkeypatch.setattr(streamlit_metrics, "_load_optional_config", lambda config_path: None)
    monkeypatch.setattr(streamlit_metrics, "_render_dashboard_readiness", lambda frame: None)
    monkeypatch.setattr(streamlit_metrics, "_metrics_dashboard_startup_blocker", lambda frame: None)
    monkeypatch.setattr(streamlit_metrics, "_render_metrics_dashboard", fake_render_dashboard)
    monkeypatch.setattr(streamlit_metrics.st, "set_page_config", lambda **kwargs: None)
    monkeypatch.setattr(streamlit_metrics.st, "title", lambda *args, **kwargs: None)
    monkeypatch.setattr(streamlit_metrics.st, "error", lambda message: (_ for _ in ()).throw(AssertionError(message)))

    streamlit_metrics.main()

    assert calls == [("summary-root", ())]
    assert rendered["summaries"] is summaries
    assert rendered["readiness"] is readiness


def test_metrics_dashboard_main_preflights_before_summary_load(monkeypatch):
    """A missing primary summary should block before full summary tables load."""

    readiness = pd.DataFrame(
        {
            "dashboard_table": ["model_metric_band"],
            "ready": [False],
            "message": ["model_metric_band summary file is missing."],
        }
    )
    warnings: list[str] = []
    rendered_readiness: list[pd.DataFrame] = []

    def fake_path_setting(query_key: str, env_key: str) -> str:  # noqa: ARG001
        return {"metrics_root": "metrics-root", "summary_root": "summary-root", "config": ""}.get(query_key, "")

    def fail_cached_loader(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("main should not load full summaries when readiness blocks startup")

    monkeypatch.setattr(streamlit_metrics, "_path_setting", fake_path_setting)
    monkeypatch.setattr(streamlit_metrics, "dashboard_summary_readiness_frame", lambda *args, **kwargs: readiness)
    monkeypatch.setattr(streamlit_metrics, "_load_summary_tables_cached", fail_cached_loader)
    monkeypatch.setattr(streamlit_metrics, "_render_dashboard_readiness", lambda frame: rendered_readiness.append(frame))
    monkeypatch.setattr(streamlit_metrics, "_try_load_long_metrics", lambda metrics_root: (_ for _ in ()).throw(AssertionError("long metrics should not load")))
    monkeypatch.setattr(streamlit_metrics, "_render_metrics_dashboard", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("dashboard should not render")))
    monkeypatch.setattr(streamlit_metrics.st, "set_page_config", lambda **kwargs: None)
    monkeypatch.setattr(streamlit_metrics.st, "title", lambda *args, **kwargs: None)
    monkeypatch.setattr(streamlit_metrics.st, "warning", lambda message: warnings.append(str(message)))
    monkeypatch.setattr(streamlit_metrics.st, "error", lambda message: (_ for _ in ()).throw(AssertionError(message)))

    streamlit_metrics.main()

    assert rendered_readiness == [readiness]
    assert warnings == ["model_metric_band summary file is missing."]


def test_metrics_dashboard_main_skips_not_ready_optional_summaries(monkeypatch):
    """Optional summaries that fail readiness should not be loaded eagerly."""

    summaries = {
        "model_metric_band": pd.DataFrame({"model": ["m1"], "metric": ["PGA"], "band": ["2-4"], "n": [1], "med_log2_residual": [0.5]}),
        "station_rollup": pd.DataFrame(columns=["station", "model", "metric", "band", "n"]),
        "event_rollup": pd.DataFrame({"event_id": ["ev1"], "model": ["m1"], "metric": ["PGA"], "band": ["2-4"], "n": [1], "med_log2_residual": [0.5]}),
        "path_hex": pd.DataFrame(columns=["model", "metric", "band", "dist_bin_km", "az_bin_deg", "n"]),
    }
    readiness = pd.DataFrame(
        {
            "dashboard_table": ["model_metric_band", "station_rollup", "event_rollup", "path_hex"],
            "ready": [True, False, True, pd.NA],
            "message": ["ready", "station_rollup schema is not ready.", "ready", "path_hex summary file is missing."],
        }
    )
    calls: list[tuple[str, tuple[str, ...]]] = []
    rendered: dict[str, object] = {}

    def fake_path_setting(query_key: str, env_key: str) -> str:  # noqa: ARG001
        return {"metrics_root": "", "summary_root": "summary-root", "config": ""}.get(query_key, "")

    def fake_cached_loader(summary_root: str, skip_tables: tuple[str, ...] = ()) -> dict[str, pd.DataFrame]:
        calls.append((summary_root, skip_tables))
        return summaries

    def fake_render_dashboard(loaded, long_metrics, config, *, readiness):  # noqa: ANN001
        rendered["summaries"] = loaded
        rendered["long_metrics"] = long_metrics
        rendered["config"] = config
        rendered["readiness"] = readiness

    monkeypatch.setattr(streamlit_metrics, "_path_setting", fake_path_setting)
    monkeypatch.setattr(streamlit_metrics, "dashboard_summary_readiness_frame", lambda *args, **kwargs: readiness)
    monkeypatch.setattr(streamlit_metrics, "_load_summary_tables_cached", fake_cached_loader)
    monkeypatch.setattr(streamlit_metrics, "_load_optional_config", lambda config_path: None)
    monkeypatch.setattr(streamlit_metrics, "_render_dashboard_readiness", lambda frame: None)
    monkeypatch.setattr(streamlit_metrics, "_render_metrics_dashboard", fake_render_dashboard)
    monkeypatch.setattr(streamlit_metrics.st, "set_page_config", lambda **kwargs: None)
    monkeypatch.setattr(streamlit_metrics.st, "title", lambda *args, **kwargs: None)
    monkeypatch.setattr(streamlit_metrics.st, "error", lambda message: (_ for _ in ()).throw(AssertionError(message)))

    streamlit_metrics.main()

    assert calls == [("summary-root", ("path_hex", "station_rollup"))]
    assert rendered["summaries"] is summaries
    assert rendered["long_metrics"] is None
    assert rendered["readiness"] is readiness


def test_metrics_tab_readiness_message_explains_optional_summary_gaps():
    """Metrics tabs should show table-readiness causes before generic empty states."""

    readiness = pd.DataFrame(
        {
            "dashboard_table": ["station_rollup", "event_rollup", "path_hex"],
            "dashboard_tabs": ["Stations", "Events", "Paths"],
            "ready": ["False", "True", pd.NA],
            "message": ["station_rollup summary file is missing.", "event_rollup summary is ready.", ""],
        }
    )

    assert dashboard_ready_value("False") is False
    assert _summary_readiness_message(readiness, "station_rollup") == "station_rollup summary file is missing."
    assert _summary_readiness_message(readiness, "event_rollup") is None
    assert _summary_readiness_message(readiness, "path_hex") == "path_hex summary is not ready for Paths. Rebuild dashboard summaries for this run."
    assert _summary_readiness_message(readiness, "model_metric_band") is None
    assert _summary_readiness_message(None, "station_rollup") is None


def test_qc_chart_tab_state_prioritizes_empty_filtered_rows():
    """QC chart tabs should not render blank charts when filters remove all rows."""

    empty = pd.DataFrame(columns=["raw_peak_abs", "dominant_band_label"])
    columns, message = _qc_chart_columns_or_message(empty, ["raw_peak_abs"], "amplitude")
    assert columns == []
    assert message == "No trace QC rows match the selected filters."

    missing = pd.DataFrame({"event_id": ["ev1"]})
    columns, message = _qc_chart_columns_or_message(missing, [], "timing")
    assert columns == []
    assert message == "No timing columns are available in the loaded trace-summary table."

    ready = pd.DataFrame({"raw_peak_abs": [1.0]})
    columns, message = _qc_chart_columns_or_message(ready, ["raw_peak_abs"], "amplitude")
    assert columns == ["raw_peak_abs"]
    assert message is None


def test_qc_dashboard_launcher_defaults_to_trace_summary_output(tmp_path, monkeypatch):
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  tables: outputs/tables
""",
        encoding="utf-8",
    )
    SpatialVTKConfig.from_file(config_path).activate()
    launched = {}

    class FakeProcess:
        pid = 222

    def fake_launch_streamlit_dashboard(entrypoint, **kwargs):
        launched["entrypoint"] = entrypoint
        launched.update(kwargs)
        return FakeProcess()

    monkeypatch.setattr(dashboard_launch, "launch_streamlit_dashboard", fake_launch_streamlit_dashboard)
    try:
        process = dashboard_launch.launch_qc_dashboard(show=False)
    finally:
        clear_active_config()

    assert process.pid == 222
    env = launched["env"]
    assert Path(env["SVTK_TRACE_SUMMARY"]) == tmp_path / "outputs" / "tables" / "qc_trace_summary.csv"
    assert Path(env["SVTK_CONFIG_FILE"]) == config_path.resolve()


def test_dashboard_launch_detects_busy_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        with pytest.raises(RuntimeError, match="already in use"):
            _raise_if_port_in_use("127.0.0.1", port)
