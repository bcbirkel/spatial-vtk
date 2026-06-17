from __future__ import annotations

import pandas as pd
import pytest

from spatial_vtk.visualize.dashboard import (
    dashboard_row_level_columns,
    load_dashboard_metric_dataset,
    load_dashboard_summary_tables,
    validate_dashboard_tables,
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


def test_dashboard_metric_dataset_loader_projects_requested_columns(tmp_path) -> None:
    """Dashboard metric loading should avoid materializing unused wide columns."""

    metrics = pd.DataFrame(
        {
            "model": ["m1", "m1"],
            "band": ["1-3s", "1-3s"],
            "metric": ["PGA", "PGV"],
            "station": ["AAA", "BBB"],
            "event_id": ["e1", "e1"],
            "log2_residual": [0.5, -0.25],
            "unused_payload": ["x" * 100, "y" * 100],
        }
    )
    direct = tmp_path / "metrics_long.parquet"
    metrics.to_parquet(direct, index=False)

    loaded_direct = load_dashboard_metric_dataset(
        direct,
        columns=["model", "metric", "log2_residual", "missing_optional", "model"],
    )

    assert loaded_direct.columns.tolist() == ["model", "metric", "log2_residual"]
    assert "unused_payload" not in loaded_direct.columns
    assert len(loaded_direct) == 2

    root = tmp_path / "dashboard_partitioned"
    part_a = root / "model=m1" / "band=1-3s" / "metric=PGA" / "part.parquet"
    part_b = root / "model=m1" / "band=1-3s" / "metric=PGV" / "part.parquet"
    part_a.parent.mkdir(parents=True)
    part_b.parent.mkdir(parents=True)
    metrics.iloc[[0]].to_parquet(part_a, index=False)
    metrics.iloc[[1]].to_parquet(part_b, index=False)

    loaded_partitioned = load_dashboard_metric_dataset(
        root,
        columns=["station", "event_id", "log2_residual"],
    )

    assert loaded_partitioned.columns.tolist() == ["station", "event_id", "log2_residual"]
    assert loaded_partitioned["station"].tolist() == ["AAA", "BBB"]


def test_dashboard_row_level_columns_are_bounded() -> None:
    """Dashboard row-level tabs should request only needed long-metric columns."""

    columns = dashboard_row_level_columns()

    assert "model" in columns
    assert "metric" in columns
    assert "station" in columns
    assert "event_id" in columns
    assert "log2_residual" in columns
    assert "anderson_2004_gof" in columns
    assert len(columns) == len(set(columns))
    assert "unused_payload" not in columns


def test_dashboard_metric_dataset_loader_ignores_unrelated_parquet(tmp_path) -> None:
    """Dashboard metric loading should not consume unrelated parquet artifacts."""

    root = tmp_path / "dashboard_data"
    unrelated_summary = root / "dashboard_summaries"
    unrelated_summary.mkdir(parents=True)
    pd.DataFrame({"model": ["m1"], "metric": ["PGA"], "n": [1]}).to_parquet(
        unrelated_summary / "model_metric_band.parquet",
        index=False,
    )
    unrelated_model_dir = root / "model=m1"
    unrelated_model_dir.mkdir()
    pd.DataFrame({"not_metric_rows": [1]}).to_parquet(unrelated_model_dir / "notes.parquet", index=False)

    with pytest.raises(FileNotFoundError, match=r"metrics_long\.parquet|model=\*/band=\*/metric=\*/part\.parquet"):
        load_dashboard_metric_dataset(root)


def test_dashboard_summary_loader_tolerates_missing_optional_tables(tmp_path) -> None:
    """Metrics dashboard should open when optional summary tabs are missing."""

    summary_root = tmp_path / "summaries"
    summary_root.mkdir()
    pd.DataFrame({"model": ["m1"], "metric": ["PGA"], "band": ["1-2 sec"], "n": [1]}).to_csv(
        summary_root / "model_metric_band.csv",
        index=False,
    )
    pd.DataFrame({"station": ["STA"], "model": ["m1"], "metric": ["PGA"], "band": ["1-2 sec"], "n": [1]}).to_csv(
        summary_root / "station_rollup.csv",
        index=False,
    )
    pd.DataFrame({"event_id": ["E1"], "model": ["m1"], "metric": ["PGA"], "band": ["1-2 sec"], "n": [1]}).to_csv(
        summary_root / "event_rollup.csv",
        index=False,
    )

    tables = validate_dashboard_tables(load_dashboard_summary_tables(summary_root))

    assert set(tables) == {"model_metric_band", "station_rollup", "event_rollup", "path_hex"}
    assert tables["path_hex"].empty
    assert {"model", "metric", "band", "dist_bin_km", "az_bin_deg", "n"} <= set(tables["path_hex"].columns)
    try:
        load_dashboard_summary_tables(summary_root, allow_missing_optional=False)
    except FileNotFoundError as exc:
        assert "path_hex" in str(exc)
    else:
        raise AssertionError("strict dashboard summary loading should require missing path_hex")


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
