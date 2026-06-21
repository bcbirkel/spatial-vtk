from __future__ import annotations

import pathlib
import sys
from types import ModuleType

import numpy as np
import pandas as pd
import pytest

from spatial_vtk.config import SpatialVTKConfig
from spatial_vtk.config.runtime import clear_active_config
from spatial_vtk.visualize.dashboard import (
    build_dashboard_summaries,
    build_dashboard_summaries_from_metric_dataset,
    display_dashboard_output_previews,
    dashboard_metric_dataset_readiness_frame,
    dashboard_output_readiness,
    dashboard_summary_input_columns,
    dashboard_row_level_columns,
    load_dashboard_metric_dataset,
    load_dashboard_summary_tables,
    prepare_configured_dashboard_datasets_from_notebook_settings,
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


def test_dashboard_metric_dataset_export_streams_path_backed_partitions(tmp_path) -> None:
    """Path-backed large-run dashboard exports should not materialize the full table first."""

    metrics_path = tmp_path / "metrics_long.parquet"
    output_root = tmp_path / "dashboard_data"
    pd.DataFrame(
        {
            "model": ["m1", "m1", "m1", "m2", "m2"],
            "metric": ["PGA", "PGA", "PGA", "PGV", "PGV"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec", "2-3 sec", "2-3 sec"],
            "event_id": ["ev1", "ev2", "ev3", "ev4", "ev5"],
            "station": ["STA1", "STA2", "STA3", "STA4", "STA5"],
            "log2_residual": [0.1, 0.2, 0.3, -0.1, -0.2],
        }
    ).to_parquet(metrics_path, index=False)

    root = write_dashboard_metric_dataset(metrics_path, output_root, partitioned=True, chunksize=2)

    pga_root = root / "model=m1" / "band=1-2_sec" / "metric=PGA"
    assert (pga_root / "part.parquet").exists()
    assert (pga_root / "part-000001.parquet").exists()
    loaded = load_dashboard_metric_dataset(root, metrics="PGA")

    assert len(loaded) == 3
    assert loaded["event_id"].tolist() == ["ev1", "ev2", "ev3"]
    assert loaded["log2_residual"].tolist() == [0.1, 0.2, 0.3]


def test_dashboard_metric_dataset_export_projects_path_backed_long_sources(tmp_path) -> None:
    """Path-backed long dashboard exports should skip unused source columns."""

    metrics_path = tmp_path / "metrics_long.csv"
    output_root = tmp_path / "dashboard_data"
    pd.DataFrame(
        {
            "model": ["m1", "m1", "m2"],
            "metric": ["PGA", "PGA", "PGV"],
            "band": ["1-2 sec", "1-2 sec", "2-3 sec"],
            "event_id": ["ev1", "ev2", "ev3"],
            "station": ["STA1", "STA2", "STA3"],
            "log2_residual": [0.1, 0.2, -0.1],
            "unused_large_payload": ["x" * 1000, "y" * 1000, "z" * 1000],
        }
    ).to_csv(metrics_path, index=False)

    root = write_dashboard_metric_dataset(metrics_path, output_root, partitioned=True, chunksize=2)
    loaded = load_dashboard_metric_dataset(root)

    assert loaded["event_id"].tolist() == ["ev1", "ev2", "ev3"]
    assert "unused_large_payload" not in loaded.columns


def test_dashboard_summary_dataset_summarizes_partitioned_metrics_one_partition_at_a_time(tmp_path, monkeypatch) -> None:
    """Partitioned dashboard summaries should avoid loading the full metric dataset."""

    metrics_path = tmp_path / "metrics_long.parquet"
    metric_root = tmp_path / "dashboard_data"
    summary_root = tmp_path / "dashboard_summaries"
    pd.DataFrame(
        {
            "model": ["m1", "m1", "m1", "m2"],
            "metric": ["PGA", "PGA", "PGA", "PGV"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec", "2-3 sec"],
            "event_id": ["ev1", "ev2", "ev3", "ev4"],
            "station": ["STA1", "STA2", "STA3", "STA4"],
            "component": ["Z", "Z", "Z", "R"],
            "log2_residual": [0.1, 0.2, 0.3, -0.5],
        }
    ).to_parquet(metrics_path, index=False)
    write_dashboard_metric_dataset(metrics_path, metric_root, partitioned=True, chunksize=2)

    def fail_full_dataset_load(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise AssertionError("partitioned dashboard summary writer loaded the full dataset")

    monkeypatch.setattr(dashboard_export, "load_dashboard_metric_dataset", fail_full_dataset_load)

    written = write_dashboard_summary_dataset(metric_root, summary_root, format="parquet")
    summaries = load_dashboard_summary_tables(summary_root)
    helper_summaries = build_dashboard_summaries_from_metric_dataset(metric_root)
    pga_row = summaries["model_metric_band"].loc[
        summaries["model_metric_band"]["metric"].eq("PGA")
    ].iloc[0]

    assert written["model_metric_band"] == summary_root / "model_metric_band.parquet"
    assert pga_row["n"] == 3
    assert pga_row["event_count"] == 3
    assert pga_row["station_count"] == 3
    assert pga_row["med_log2_residual"] == pytest.approx(0.2)
    assert helper_summaries["model_metric_band"]["n"].sum() == 4


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


def test_dashboard_writers_accept_explicit_unactivated_config(tmp_path) -> None:
    """Direct dashboard writers should not require global active-config state."""

    clear_active_config()
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
    rows = pd.DataFrame(
        {
            "model": ["m1", "m1"],
            "metric": ["PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec"],
            "component": ["Z", "R"],
            "station": ["STA1", "STA2"],
            "event_id": ["ev1", "ev1"],
            "sta_lat": [34.1, 34.2],
            "sta_lon": [-118.1, -118.2],
            "event_lat": [34.0, 34.0],
            "event_lon": [-118.0, -118.0],
            "distance_km": [10.0, 20.0],
            "azimuth_deg": [45.0, 90.0],
            "log2_residual": [0.25, -0.5],
        }
    )

    try:
        metric_root = write_dashboard_metric_dataset(rows, cfg=cfg)
        summary_paths = write_dashboard_summary_dataset(cfg=cfg)
    finally:
        clear_active_config()

    assert metric_root == tmp_path / "outputs" / "dashboards" / "metrics_dashboard"
    assert not (metric_root / "metrics_long.parquet").exists()
    assert list(metric_root.glob("model=*/band=*/metric=*/part*.parquet"))
    assert summary_paths["model_metric_band"] == (
        tmp_path / "outputs" / "dashboards" / "dashboard_summaries" / "model_metric_band.parquet"
    )
    assert summary_paths["model_metric_band"].exists()


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


def test_dashboard_summaries_normalize_coordinate_aliases_for_maps() -> None:
    """Dashboard summaries should preserve accepted coordinate aliases for map tabs."""

    rows = pd.DataFrame(
        {
            "model": ["m1"],
            "metric": ["PGA"],
            "band": ["1-2 sec"],
            "component": ["R"],
            "station": ["STA"],
            "event_id": ["ev1"],
            "station_lat": [34.1],
            "station_lon": [-118.2],
            "event_latitude": [33.9],
            "event_longitude": [-118.0],
            "distance_km": [25.0],
            "azimuth_deg": [90.0],
            "log2_residual": [0.5],
        }
    )

    summaries = validate_dashboard_tables(build_dashboard_summaries(rows))
    station_summary = summaries["station_rollup"]
    event_summary = summaries["event_rollup"]

    assert station_summary["sta_lat"].tolist() == [34.1]
    assert station_summary["sta_lon"].tolist() == [-118.2]
    assert event_summary["event_lat"].tolist() == [33.9]
    assert event_summary["event_lon"].tolist() == [-118.0]


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


def test_dashboard_metric_dataset_loader_pushes_down_large_run_filters(tmp_path) -> None:
    """Bounded dashboard loads should cap rows after period/component/range filters."""

    rows = pd.DataFrame(
        {
            "model": ["m1", "m1", "m1", "m1"],
            "band": ["1-2 sec", "", "", ""],
            "metric": ["PGA", "PSA", "PSA", "PSA"],
            "period_s": [np.nan, 1.0, 2.0, 1.0],
            "component": ["R", "R", "R", "T"],
            "station": ["BAND", "KEEP", "PERIOD", "COMP"],
            "event_id": ["e1", "e1", "e1", "e1"],
            "distance_km": [20.0, 30.0, 30.0, 30.0],
            "Vs30": [400.0, 500.0, 500.0, 500.0],
            "log2_residual": [0.1, 0.2, 0.3, 0.4],
        }
    )
    direct = tmp_path / "metrics_long.csv"
    rows.to_csv(direct, index=False)

    loaded = load_dashboard_metric_dataset(
        direct,
        columns=["model", "band", "metric", "period_s", "component", "station", "distance_km", "Vs30", "log2_residual"],
        models=["m1"],
        bands=["1-2 sec"],
        metrics=["PSA"],
        periods_s=[1.0],
        component="R",
        distance_range_km=(25.0, 35.0),
        vs30_range=(450.0, 550.0),
        max_rows=1,
        chunksize=1,
    )

    assert loaded["station"].tolist() == ["KEEP"]
    assert loaded["band"].fillna("").tolist() == [""]
    assert loaded["period_s"].tolist() == [1.0]


def test_dashboard_metric_dataset_bounded_parquet_requires_streaming_reader(tmp_path, monkeypatch) -> None:
    """Bounded dashboard parquet loads should not fall back to full materialization."""

    parquet_path = tmp_path / "metrics_long.parquet"
    parquet_path.write_bytes(b"not a real parquet file")

    fake_pyarrow = ModuleType("pyarrow")
    fake_parquet = ModuleType("pyarrow.parquet")

    class BrokenParquetFile:
        def __init__(self, path):  # noqa: ANN001
            raise RuntimeError(f"cannot stream {path}")

    fake_parquet.ParquetFile = BrokenParquetFile
    fake_pyarrow.parquet = fake_parquet
    monkeypatch.setitem(sys.modules, "pyarrow", fake_pyarrow)
    monkeypatch.setitem(sys.modules, "pyarrow.parquet", fake_parquet)

    def fail_full_parquet_read(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise AssertionError("bounded dashboard loads must not full-read parquet fallback data")

    monkeypatch.setattr(dashboard_export.pd, "read_parquet", fail_full_parquet_read)

    with pytest.raises(RuntimeError, match="Could not stream dashboard metric parquet table"):
        load_dashboard_metric_dataset(parquet_path, max_rows=1, chunksize=1)


def test_dashboard_metric_schema_probe_uses_shared_parquet_helper() -> None:
    """Dashboard metric schema probes should follow the shared large-table helper."""

    source = pathlib.Path(dashboard_export.__file__).read_text(encoding="utf-8")
    helper_source = source.split("def _dashboard_metric_table_columns", 1)[1].split("\ndef ", 1)[0]
    assert "parquet_table_columns(path)" in helper_source
    assert "pyarrow.parquet" not in helper_source
    assert "ParquetFile(path).schema" not in helper_source


def test_dashboard_metric_dataset_loader_treats_passband_as_band_alias(tmp_path) -> None:
    """Direct row-level dashboard datasets should filter older passband-only tables."""

    rows = pd.DataFrame(
        {
            "model": ["m1", "m1"],
            "passband": ["1-2 sec", "2-3 sec"],
            "metric": ["PGA", "PGA"],
            "station": ["KEEP", "DROP"],
            "event_id": ["e1", "e1"],
            "log2_residual": [0.1, 0.2],
        }
    )
    direct = tmp_path / "metrics_long.csv"
    rows.to_csv(direct, index=False)

    loaded_unfiltered = load_dashboard_metric_dataset(
        direct,
        columns=["band", "station"],
    )

    assert loaded_unfiltered.columns.tolist() == ["band", "station"]
    assert loaded_unfiltered["band"].tolist() == ["1-2 sec", "2-3 sec"]

    loaded = load_dashboard_metric_dataset(
        direct,
        columns=["model", "band", "passband", "metric", "station", "log2_residual"],
        bands=["1-2 sec"],
        max_rows=10,
        chunksize=1,
    )

    assert loaded["station"].tolist() == ["KEEP"]
    assert loaded["band"].tolist() == ["1-2 sec"]
    assert loaded["passband"].tolist() == ["1-2 sec"]


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


def test_dashboard_metric_dataset_readiness_uses_partition_column_union(tmp_path) -> None:
    """Dataset readiness should not depend on the first partition's schema."""

    root = tmp_path / "dashboard_data"
    first = root / "model=m1" / "band=1-2_sec" / "metric=AAA" / "part.parquet"
    second = root / "model=m1" / "band=1-2_sec" / "metric=PGA" / "part.parquet"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    pd.DataFrame(
        {
            "model": ["m1"],
            "band": ["1-2 sec"],
            "metric": ["AAA"],
            "station": ["STA"],
        }
    ).to_parquet(first, index=False)
    pd.DataFrame(
        {
            "model": ["m1"],
            "band": ["1-2 sec"],
            "metric": ["PGA"],
            "station": ["STB"],
            "log2_residual": [0.25],
        }
    ).to_parquet(second, index=False)

    readiness = dashboard_metric_dataset_readiness_frame(root).iloc[0]

    assert readiness["ready"] is True
    assert readiness["readiness"] == "ready"
    assert readiness["file_count"] == 2
    assert readiness["row_count"] == 2
    assert readiness["value_columns"] == "log2_residual"


def test_dashboard_metric_dataset_readiness_counts_csv_with_quoted_newlines(tmp_path) -> None:
    """Dashboard readiness row counts should use CSV parsing, not raw line counts."""

    dataset = tmp_path / "metrics_long.csv"
    dataset.write_text(
        'model,band,metric,station,log2_residual,notes\n'
        'm1,1-2 sec,PGA,STA,0.2,"line one\nline two"\n'
        "m1,1-2 sec,PGA,STB,0.3,plain\n",
        encoding="utf-8",
    )

    readiness = dashboard_metric_dataset_readiness_frame(dataset).iloc[0]

    assert readiness["ready"] is True
    assert readiness["readiness"] == "ready"
    assert readiness["row_count"] == 2


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


def test_dashboard_output_readiness_accepts_missing_path_summary_without_path_geometry(tmp_path) -> None:
    """Dashboard rebuild decisions should not loop when path bins cannot be built."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  tables: outputs/tables
  dashboards: outputs/dashboards
  metrics_long: metrics_long.csv
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    tables_root = tmp_path / "outputs" / "tables"
    dashboard_root = tmp_path / "outputs" / "dashboards"
    summary_root = dashboard_root / "dashboard_summaries"
    metric_dataset_root = dashboard_root / "metrics_dashboard"
    tables_root.mkdir(parents=True)
    summary_root.mkdir(parents=True)
    metric_dataset_root.mkdir(parents=True)

    source_rows = pd.DataFrame(
        {
            "model": ["m1"],
            "metric": ["PGA"],
            "band": ["1-2 sec"],
            "station": ["STA"],
            "event_id": ["E1"],
            "log2_residual": [0.25],
        }
    )
    source_rows.to_csv(tables_root / "metrics_long.csv", index=False)
    source_rows.to_parquet(metric_dataset_root / "metrics_long.parquet", index=False)
    pd.DataFrame({"model": ["m1"], "metric": ["PGA"], "band": ["1-2 sec"], "n": [1], "med_log2_residual": [0.25]}).to_csv(
        summary_root / "model_metric_band.csv",
        index=False,
    )
    pd.DataFrame({"station": ["STA"], "model": ["m1"], "metric": ["PGA"], "band": ["1-2 sec"], "n": [1], "med_log2_residual": [0.25]}).to_csv(
        summary_root / "station_rollup.csv",
        index=False,
    )
    pd.DataFrame({"event_id": ["E1"], "model": ["m1"], "metric": ["PGA"], "band": ["1-2 sec"], "n": [1], "med_log2_residual": [0.25]}).to_csv(
        summary_root / "event_rollup.csv",
        index=False,
    )

    readiness = dashboard_output_readiness(cfg=cfg, create_parent=False)
    path_status = readiness.summary_status.loc[readiness.summary_status["dashboard_table"].eq("path_hex")].iloc[0]

    assert readiness.should_run is False
    assert readiness.reason == "current"
    assert path_status["readiness"] == "missing"

    source_rows.assign(distance_km=[10.0], azimuth_deg=[45.0]).to_csv(tables_root / "metrics_long.csv", index=False)
    needs_path = dashboard_output_readiness(cfg=cfg, create_parent=False)

    assert needs_path.should_run is True
    assert needs_path.reason == "missing_outputs"
    assert "path_hex" in needs_path.message


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

    previews = preview_dashboard_summary_tables(cfg=config_path, nrows=2)

    assert set(previews) == {"model_metric_band", "station_rollup"}
    assert len(previews["model_metric_band"]) == 2
    assert previews["model_metric_band"]["model"].tolist() == ["m1", "m2"]
    assert len(previews["station_rollup"]) == 2
    assert previews["station_rollup"]["station"].tolist() == ["STA", "STB"]
    with pytest.raises(FileNotFoundError, match="path_hex"):
        preview_dashboard_summary_tables(summary_root, missing="raise")
    with pytest.raises(ValueError, match="missing must be"):
        preview_dashboard_summary_tables(summary_root, missing="ignore")


def test_display_dashboard_output_previews_reads_bounded_dashboard_outputs(tmp_path, capsys) -> None:
    """Dashboard notebook preview helper should avoid manual table path plumbing."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  tables: outputs/tables
  dashboards: outputs/dashboards
  metrics_long: metrics_long.parquet
""",
        encoding="utf-8",
    )
    tables_root = tmp_path / "outputs" / "tables"
    summary_root = tmp_path / "outputs" / "dashboards" / "dashboard_summaries"
    tables_root.mkdir(parents=True)
    summary_root.mkdir(parents=True)
    pd.DataFrame({"event_id": ["e1", "e2", "e3"], "metric": ["PGA", "PGV", "CAV"]}).to_parquet(
        tables_root / "metrics_long.parquet",
        index=False,
    )
    pd.DataFrame(
        {
            "model": ["m1", "m2", "m3"],
            "metric": ["PGA", "PGV", "CAV"],
            "band": ["1-2 sec", "2-3 sec", "3-5 sec"],
            "n": [1, 2, 3],
        }
    ).to_parquet(summary_root / "model_metric_band.parquet", index=False)

    displayed: list[pd.DataFrame] = []
    clear_active_config()
    previews = display_dashboard_output_previews(cfg=config_path, nrows=2, display_fn=displayed.append)

    output = capsys.readouterr().out
    assert "dashboard_summary:model_metric_band preview:" in output
    assert "metrics_long preview:" in output
    assert set(previews) == {"dashboard_summary:model_metric_band", "metrics_long"}
    assert len(previews["dashboard_summary:model_metric_band"]) == 2
    assert len(previews["metrics_long"]) == 2
    assert [len(frame) for frame in displayed] == [2, 2]


def test_dashboard_preparation_result_displays_outputs_from_stored_config(tmp_path, capsys) -> None:
    """Step 7 result objects should preview outputs without notebook config plumbing."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  tables: outputs/tables
  dashboards: outputs/dashboards
  metrics_long: metrics_long.parquet
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    tables_root = tmp_path / "outputs" / "tables"
    summary_root = tmp_path / "outputs" / "dashboards" / "dashboard_summaries"
    tables_root.mkdir(parents=True)
    summary_root.mkdir(parents=True)
    pd.DataFrame({"event_id": ["e1", "e2", "e3"], "metric": ["PGA", "PGV", "CAV"]}).to_parquet(
        tables_root / "metrics_long.parquet",
        index=False,
    )
    pd.DataFrame(
        {
            "model": ["m1", "m2", "m3"],
            "metric": ["PGA", "PGV", "CAV"],
            "band": ["1-2 sec", "2-3 sec", "3-5 sec"],
            "n": [1, 2, 3],
        }
    ).to_parquet(summary_root / "model_metric_band.parquet", index=False)

    result = prepare_configured_dashboard_datasets_from_notebook_settings(cfg=cfg, prepare_locally=False)
    displayed: list[pd.DataFrame] = []
    previews = result.display_output_previews(nrows=2, display_fn=displayed.append)

    output = capsys.readouterr().out
    assert "dashboard_summary:model_metric_band preview:" in output
    assert "metrics_long preview:" in output
    assert set(previews) == {"dashboard_summary:model_metric_band", "metrics_long"}
    assert len(previews["dashboard_summary:model_metric_band"]) == 2
    assert len(previews["metrics_long"]) == 2
    assert [len(frame) for frame in displayed] == [2, 2]


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
