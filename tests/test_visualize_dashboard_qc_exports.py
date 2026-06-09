from __future__ import annotations

import pandas as pd

from spatial_vtk.visualize.dashboard import (
    load_dashboard_metric_dataset,
    write_dashboard_metric_dataset,
    write_dashboard_summary_dataset,
)
from spatial_vtk.visualize.qc import (
    build_trace_qc_overview_html,
    filter_trace_summary,
    queue_rows_from_filtered_trace_df,
    trace_qc_records,
    write_trace_qc_overview_html,
)


def test_dashboard_metric_dataset_export_and_summary_tables(tmp_path) -> None:
    """Dashboard export helpers should write reloadable parquet datasets."""

    metrics = pd.DataFrame(
        {
            "model": ["m1", "m1"],
            "band": ["1-3s", "1-3s"],
            "event_id": ["e1", "e1"],
            "event_lat": [34.0, 34.0],
            "event_lon": [-118.0, -118.0],
            "station": ["AAA", "BBB"],
            "sta_lat": [34.1, 34.2],
            "sta_lon": [-118.1, -118.2],
            "component": ["Z", "Z"],
            "PGA_obs": [4.0, 8.0],
            "PGA_syn": [2.0, 4.0],
            "PGA_score": [8.0, 7.0],
        }
    )

    root = write_dashboard_metric_dataset(metrics, tmp_path / "dashboard_data", partitioned=True)
    loaded = load_dashboard_metric_dataset(root)

    assert {"metric", "residual", "distance_km", "azimuth_deg", "backazimuth_deg"} <= set(loaded.columns)
    assert loaded["metric"].unique().tolist() == ["PGA"]
    assert loaded["distance_km"].notna().all()

    written = write_dashboard_summary_dataset(root, tmp_path / "dashboard_summaries", format="csv")
    assert {"model_metric_band", "station_rollup", "event_rollup", "path_hex"} <= set(written)
    assert written["model_metric_band"].exists()


def test_qc_overview_filter_queue_and_html_helpers(tmp_path) -> None:
    """QC overview helpers should filter rows and produce review queue records."""

    summary = pd.DataFrame(
        {
            "event_id": ["e1", "e1", "e2"],
            "event_title": ["Event 1", "Event 1", "Event 2"],
            "event_date": ["2026-01-01", "2026-01-01", "2026-02-01"],
            "station": ["AAA", "BBB", "AAA"],
            "component": ["Z", "R", "Z"],
            "network": ["CI", "CI", "CI"],
            "station_family": ["broadband", "strong_motion", "broadband"],
            "magnitude": [4.0, 4.0, 5.0],
            "distance_km": [10.0, 20.0, 80.0],
            "event_lat": [34.0, 34.0, 35.0],
            "event_lon": [-118.0, -118.0, -119.0],
            "station_lat": [34.1, 34.2, 35.1],
            "station_lon": [-118.1, -118.2, -119.1],
            "source_context_count": [1, 1, 2],
            "source_contexts": ["obs", "obs", "obs,syn"],
            "metadata_warning": ["", "missing_units", ""],
        }
    )

    filtered = filter_trace_summary(
        summary,
        station_family="broadband",
        component_filter="Z",
        magnitude_range=(3.5, 4.5),
        distance_range_km=(0.0, 50.0),
    )
    assert filtered["event_id"].tolist() == ["e1"]

    queue = queue_rows_from_filtered_trace_df(filtered)
    assert len(queue) == 1
    assert queue[0]["station"] == "AAA"
    assert queue[0]["distance_km"] == "10.000000"

    records = trace_qc_records(filtered)
    assert records[0]["event_date"] == "2026-01-01"

    html_text = build_trace_qc_overview_html(filtered, tmp_path)
    assert "Trace QC Overview" in html_text
    assert "trace-qc-data" in html_text

    output = write_trace_qc_overview_html(filtered, tmp_path / "qc.html")
    assert output.exists()
    assert "Trace QC Overview" in output.read_text(encoding="utf-8")
