from __future__ import annotations

import pandas as pd
import pytest

from spatial_vtk.config import SpatialVTKConfig
from spatial_vtk.visualize.dashboard import (
    build_dashboard_summaries,
    dashboard_summary_input_columns,
    dashboard_row_level_columns,
    load_dashboard_metric_dataset,
    load_dashboard_summary_tables,
    preview_dashboard_summary_tables,
    validate_dashboard_tables,
    write_configured_dashboard_datasets,
    write_dashboard_metric_dataset,
    write_dashboard_summary_dataset,
)
import spatial_vtk.visualize.dashboard.export as dashboard_export
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


def test_dashboard_metric_dataset_export_replaces_stale_partitions(tmp_path) -> None:
    """Rerunning a partitioned dashboard export should not leave old rows active."""

    output_root = tmp_path / "dashboard_data"
    first = pd.DataFrame(
        {
            "model": ["m1", "m2"],
            "metric": ["PGA", "PGV"],
            "band": ["1-2 sec", "2-3 sec"],
            "event_id": ["ev1", "ev2"],
            "station": ["STA1", "STA2"],
            "value": [1.0, 2.0],
        }
    )
    second = pd.DataFrame(
        {
            "model": ["m1"],
            "metric": ["PGA"],
            "band": ["1-2 sec"],
            "event_id": ["ev1"],
            "station": ["STA1"],
            "value": [3.0],
        }
    )

    write_dashboard_metric_dataset(first, output_root, partitioned=True)
    stale_path = output_root / "model=m2" / "band=2-3_sec" / "metric=PGV" / "part.parquet"
    assert stale_path.exists()

    write_dashboard_metric_dataset(second, output_root, partitioned=True)
    loaded = load_dashboard_metric_dataset(output_root)

    assert not stale_path.exists()
    assert loaded["model"].tolist() == ["m1"]
    assert loaded["metric"].tolist() == ["PGA"]
    assert loaded["value"].tolist() == [3.0]


def test_dashboard_summary_dataset_replaces_stale_cross_format_files(tmp_path) -> None:
    """New summary files should not be shadowed by stale files in another format."""

    metric_root = tmp_path / "dashboard_data"
    summary_root = tmp_path / "dashboard_summaries"
    first = pd.DataFrame(
        {
            "model": ["m1"],
            "metric": ["PGA"],
            "band": ["1-2 sec"],
            "event_id": ["ev1"],
            "station": ["STA1"],
            "value": [1.0],
        }
    )
    second = pd.DataFrame(
        {
            "model": ["m2"],
            "metric": ["PGV"],
            "band": ["2-3 sec"],
            "event_id": ["ev2"],
            "station": ["STA2"],
            "value": [2.0],
        }
    )

    write_dashboard_metric_dataset(first, metric_root, partitioned=False)
    write_dashboard_summary_dataset(metric_root, summary_root, format="parquet")
    assert (summary_root / "model_metric_band.parquet").exists()

    write_dashboard_metric_dataset(second, metric_root, partitioned=False)
    written = write_dashboard_summary_dataset(metric_root, summary_root, format="csv")
    loaded = load_dashboard_summary_tables(summary_root)

    assert written["model_metric_band"] == summary_root / "model_metric_band.csv"
    assert not (summary_root / "model_metric_band.parquet").exists()
    assert loaded["model_metric_band"]["model"].tolist() == ["m2"]
    assert loaded["model_metric_band"]["metric"].tolist() == ["PGV"]


def test_write_configured_dashboard_datasets_uses_registered_paths(tmp_path) -> None:
    """Config-backed dashboard export should not require notebook path plumbing."""

    config_path = tmp_path / "spatial-vtk.yaml"
    metrics_path = tmp_path / "outputs" / "tables" / "metrics_long.parquet"
    metrics_path.parent.mkdir(parents=True)
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
    pd.DataFrame(
        {
            "model": ["m1", "m1"],
            "metric": ["PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec"],
            "event_id": ["ev1", "ev1"],
            "station": ["STA1", "STA2"],
            "component": ["Z", "Z"],
            "event_lat": [34.0, 34.0],
            "event_lon": [-118.0, -118.0],
            "sta_lat": [34.1, 34.2],
            "sta_lon": [-118.1, -118.2],
            "log2_residual": [0.25, -0.5],
        }
    ).to_parquet(metrics_path, index=False)

    written = write_configured_dashboard_datasets(
        cfg=SpatialVTKConfig.from_file(config_path),
        partitioned=True,
        format="parquet",
    )

    assert written["metrics_dashboard_root"] == tmp_path / "outputs" / "dashboards" / "metrics_dashboard"
    assert written["dashboard_summary_root"] == tmp_path / "outputs" / "dashboards" / "dashboard_summaries"
    assert (written["metrics_dashboard_root"] / "model=m1" / "band=1-2_sec" / "metric=PGA" / "part.parquet").exists()
    assert written["dashboard_summary_model_metric_band"].exists()
    summaries = load_dashboard_summary_tables(written["dashboard_summary_root"])
    assert summaries["model_metric_band"]["n"].sum() == 2


def test_write_configured_dashboard_datasets_accepts_config_path(tmp_path) -> None:
    """Notebook Slurm workers should be able to pass a JSON-safe config path."""

    config_path = tmp_path / "spatial-vtk.yaml"
    metrics_path = tmp_path / "outputs" / "tables" / "metrics_long.parquet"
    metrics_path.parent.mkdir(parents=True)
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
    pd.DataFrame(
        {
            "model": ["m1"],
            "metric": ["PGA"],
            "band": ["1-2 sec"],
            "event_id": ["ev1"],
            "station": ["STA1"],
            "component": ["Z"],
            "log2_residual": [0.25],
        }
    ).to_parquet(metrics_path, index=False)

    written = write_configured_dashboard_datasets(cfg=config_path, partitioned=True)

    assert written["metrics_dashboard_root"] == tmp_path / "outputs" / "dashboards" / "metrics_dashboard"
    assert written["dashboard_summary_model_metric_band"].exists()


def test_dashboard_summaries_report_unique_event_and_station_counts() -> None:
    """Dashboard rollups should expose unique counts behind each aggregate."""

    base = pd.DataFrame(
        {
            "model": ["m1", "m1", "m1", "m1"],
            "metric": ["PGA", "PGA", "PGA", "PGA"],
            "band": ["2-4", "2-4", "2-4", "2-4"],
            "component": ["R", "R", "T", "T"],
            "station": ["STA1", "STA1", "STA1", "STA2"],
            "event_id": ["ev1", "ev2", "ev1", "ev1"],
            "sta_lat": [34.0, 34.0, 34.0, 34.1],
            "sta_lon": [-118.1, -118.1, -118.1, -118.2],
            "event_lat": [33.9, 34.2, 33.9, 33.9],
            "event_lon": [-118.3, -117.9, -118.3, -118.3],
            "distance_km": [10.0, 30.0, 12.0, 20.0],
            "azimuth_deg": [45.0, 135.0, 50.0, 90.0],
            "log2_residual": [1.0, 0.5, -0.25, 0.75],
        }
    )

    summaries = validate_dashboard_tables(build_dashboard_summaries(base, hex_dist=1000.0, hex_az=360.0))

    model_row = summaries["model_metric_band"].loc[
        summaries["model_metric_band"]["model"].eq("m1") & summaries["model_metric_band"]["component"].eq("R")
    ].iloc[0]
    assert model_row["n"] == 2
    assert model_row["event_count"] == 2
    assert model_row["station_count"] == 1

    station_row = summaries["station_rollup"].loc[
        summaries["station_rollup"]["station"].eq("STA1")
        & summaries["station_rollup"]["model"].eq("m1")
        & summaries["station_rollup"]["component"].eq("R")
    ].iloc[0]
    assert station_row["n"] == 2
    assert station_row["event_count"] == 2

    event_row = summaries["event_rollup"].loc[
        summaries["event_rollup"]["event_id"].eq("ev1")
        & summaries["event_rollup"]["model"].eq("m1")
        & summaries["event_rollup"]["component"].eq("T")
    ].iloc[0]
    assert event_row["n"] == 2
    assert event_row["station_count"] == 2

    path_row = summaries["path_hex"].loc[
        summaries["path_hex"]["model"].eq("m1") & summaries["path_hex"]["component"].eq("R")
    ].iloc[0]
    assert path_row["n"] == 2
    assert path_row["event_count"] == 2
    assert path_row["station_count"] == 1


def test_dashboard_summaries_preserve_spectral_period_groups() -> None:
    """Dashboard summaries should not collapse PSA oscillator periods into passbands."""

    rows = pd.DataFrame(
        {
            "model": ["m1", "m1", "m1"],
            "metric": ["PSA", "PSA", "PGA"],
            "band": ["", "", "1-2 sec"],
            "period_s": [1.0, 2.0, pd.NA],
            "component": ["R", "R", "R"],
            "station": ["STA", "STA", "STA"],
            "event_id": ["ev1", "ev1", "ev1"],
            "sta_lat": [34.0, 34.0, 34.0],
            "sta_lon": [-118.0, -118.0, -118.0],
            "event_lat": [33.9, 33.9, 33.9],
            "event_lon": [-118.1, -118.1, -118.1],
            "distance_km": [10.0, 10.0, 10.0],
            "azimuth_deg": [45.0, 45.0, 45.0],
            "log2_residual": [0.25, 0.75, -0.5],
        }
    )

    summaries = validate_dashboard_tables(build_dashboard_summaries(rows, hex_dist=1000.0, hex_az=360.0))
    model_summary = summaries["model_metric_band"]
    station_summary = summaries["station_rollup"]
    path_summary = summaries["path_hex"]

    psa_rows = model_summary.loc[model_summary["metric"].eq("PSA")]
    assert sorted(psa_rows["period_s"].dropna().astype(float).tolist()) == [1.0, 2.0]
    assert psa_rows["n"].tolist() == [1, 1]
    assert "period_s" in station_summary.columns
    assert "period_s" in path_summary.columns
    assert station_summary.loc[station_summary["metric"].eq("PSA"), "period_s"].nunique(dropna=True) == 2


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

    loaded_filtered = load_dashboard_metric_dataset(
        root,
        columns=["model", "band", "metric", "station", "log2_residual"],
        models=["m1"],
        bands=["1-3s"],
        metrics=["PGA"],
    )

    assert loaded_filtered.columns.tolist() == ["model", "band", "metric", "station", "log2_residual"]
    assert loaded_filtered["station"].tolist() == ["AAA"]
    assert loaded_filtered["metric"].tolist() == ["PGA"]

    loaded_direct_filtered = load_dashboard_metric_dataset(
        direct,
        columns=["model", "band", "metric", "station", "log2_residual"],
        metrics=["PGV"],
    )

    assert loaded_direct_filtered["station"].tolist() == ["BBB"]


def test_dashboard_summary_dataset_reads_only_summary_columns(tmp_path, monkeypatch) -> None:
    """Dashboard summaries should not materialize unused long-metric payloads."""

    captured: dict[str, tuple[str, ...]] = {}

    def fake_load_dashboard_metric_dataset(input_root, *, columns=None):  # noqa: ANN001
        captured["input_root"] = (str(input_root),)
        captured["columns"] = tuple(columns or ())
        return pd.DataFrame(
            {
                "model": ["m1", "m1"],
                "metric": ["PGA", "PGA"],
                "band": ["1-3s", "1-3s"],
                "component": ["Z", "Z"],
                "station": ["AAA", "BBB"],
                "event_id": ["e1", "e1"],
                "log2_residual": [0.5, -0.25],
                "distance_km": [10.0, 20.0],
                "azimuth_deg": [45.0, 90.0],
                "sta_lat": [34.1, 34.2],
                "sta_lon": [-118.1, -118.2],
                "event_lat": [34.0, 34.0],
                "event_lon": [-118.0, -118.0],
            }
        )

    monkeypatch.setattr(dashboard_export, "load_dashboard_metric_dataset", fake_load_dashboard_metric_dataset)

    written = dashboard_export.write_dashboard_summary_dataset(
        tmp_path / "dashboard_data",
        tmp_path / "dashboard_summaries",
        format="csv",
    )

    columns = captured["columns"]
    assert columns == dashboard_summary_input_columns()
    assert "model" in columns
    assert "metric" in columns
    assert "period_s" in columns
    assert "log2_residual" in columns
    assert "distance_km" in columns
    assert "azimuth_deg" in columns
    assert "unused_payload" not in columns
    assert written["model_metric_band"].exists()
    assert written["path_hex"].exists()


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


def test_dashboard_summary_previews_are_bounded_and_config_backed(tmp_path) -> None:
    """Notebook previews should inspect dashboard summaries without loading full tables."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  dashboards: outputs/dashboards
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    summary_root = tmp_path / "outputs" / "dashboards" / "dashboard_summaries"
    summary_root.mkdir()
    pd.DataFrame(
        {
            "model": ["m1", "m2", "m3"],
            "metric": ["PGA", "PGV", "CAV"],
            "band": ["1-2 sec", "2-3 sec", "3-5 sec"],
            "n": [1, 2, 3],
        }
    ).to_parquet(summary_root / "model_metric_band.parquet", index=False)
    pd.DataFrame(
        {
            "station": ["STA", "STB", "STC"],
            "model": ["m1", "m1", "m1"],
            "metric": ["PGA", "PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec"],
            "n": [1, 2, 3],
        }
    ).to_csv(summary_root / "station_rollup.csv", index=False)

    previews = preview_dashboard_summary_tables(cfg=cfg, nrows=2)

    assert set(previews) == {"model_metric_band", "station_rollup"}
    assert len(previews["model_metric_band"]) == 2
    assert previews["model_metric_band"]["model"].tolist() == ["m1", "m2"]
    assert len(previews["station_rollup"]) == 2
    assert previews["station_rollup"]["station"].tolist() == ["STA", "STB"]
    with pytest.raises(FileNotFoundError, match="path_hex"):
        preview_dashboard_summary_tables(summary_root, missing="raise")
    with pytest.raises(ValueError, match="missing must be"):
        preview_dashboard_summary_tables(summary_root, missing="ignore")


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
