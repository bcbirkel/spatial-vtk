"""Tests for public metadata, inventory, and context figure helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg", force=True)

from spatial_vtk.config import SpatialVTKConfig, clear_active_config
from spatial_vtk.io import (
    build_observed_synthetic_inventory,
    load_or_build_output_table,
    prepare_event_metadata,
    prepare_event_station_table,
    prepare_station_metadata,
    load_output_table,
    preview_output_table,
    read_config_table,
    write_output_tables,
)
from spatial_vtk.visualize.context import (
    plot_event_coverage,
    plot_record_coverage,
    plot_station_coverage,
    plot_station_event_beachball_map,
    plot_station_event_context,
    summarize_coverage,
)


def test_prepare_metadata_accepts_common_aliases() -> None:
    """Metadata helpers should normalize common station and event column names."""

    raw_stations = pd.DataFrame(
        {
            "StationName": ["STA01", "STA02"],
            "Network": ["CI", "CI"],
            "stationlat": [34.1, 34.2],
            "stationlongitude": [-118.2, -118.1],
        }
    )
    stations = prepare_station_metadata(raw_stations)
    assert {"station", "network", "lat", "lon"} <= set(stations.columns)
    assert stations.loc[0, "station"] == "STA01"

    raw_events = pd.DataFrame(
        {
            "EventTitle": ["E01", "E02"],
            "eventlatitude": [34.0, 34.3],
            "event_lon": [-118.4, -118.0],
            "mag": [4.2, 4.5],
            "depth": [8.0, 10.0],
        }
    )
    events = prepare_event_metadata(raw_events)
    assert {"event_id", "event_lat", "event_lon", "magnitude", "depth_km"} <= set(events.columns)

    pairs = prepare_event_station_table(pd.DataFrame({"event": ["E01"], "site": ["STA01"]}), station_metadata=stations, event_metadata=events)
    assert {"event_id", "station", "lat", "lon", "event_lat", "event_lon"} <= set(pairs.columns)


def test_prepare_metadata_can_read_active_config_tables(tmp_path: Path) -> None:
    """Metadata prep helpers should read configured paths when no table is passed."""

    stations_path = tmp_path / "stations.csv"
    events_path = tmp_path / "events.csv"
    pairs_path = tmp_path / "pairs.csv"
    config_path = tmp_path / "spatial-vtk.yaml"
    stations_path.write_text("station,lat,lon\nSTA01,34.1,-118.2\n", encoding="utf-8")
    events_path.write_text("event_id,event_lat,event_lon\nE01,34.0,-118.4\n", encoding="utf-8")
    pairs_path.write_text("event_id,station\nE01,STA01\n", encoding="utf-8")
    config_path.write_text(
        "\n".join(
            [
                "project:",
                "  root_dir: .",
                "paths:",
                "  station_metadata: stations.csv",
                "  event_metadata: events.csv",
                "  event_station_table: pairs.csv",
            ]
        ),
        encoding="utf-8",
    )

    try:
        SpatialVTKConfig.from_file(config_path).activate()
        stations = prepare_station_metadata()
        events = prepare_event_metadata()
        configured_pairs = prepare_event_station_table()
        pairs = prepare_event_station_table(station_metadata=stations, event_metadata=events)
    finally:
        clear_active_config()

    assert stations.loc[0, "station"] == "STA01"
    assert events.loc[0, "event_id"] == "E01"
    assert configured_pairs.loc[0, "station"] == "STA01"
    assert {"event_lat", "event_lon", "lat", "lon"} <= set(pairs.columns)


def test_prepare_event_station_table_builds_pairs_when_config_path_is_missing(tmp_path: Path) -> None:
    """Event-station preparation should generate pairs from provided metadata."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        "\n".join(
            [
                "project:",
                "  root_dir: .",
                "paths:",
                "  event_station_table: missing_pairs.csv",
            ]
        ),
        encoding="utf-8",
    )
    stations = pd.DataFrame({"station": ["STA01", "STA02"], "lat": [34.1, 34.2], "lon": [-118.2, -118.1]})
    events = pd.DataFrame({"event_id": ["E01", "E02"], "event_lat": [34.0, 34.3], "event_lon": [-118.4, -118.0]})

    try:
        SpatialVTKConfig.from_file(config_path).activate()
        pairs = prepare_event_station_table(station_metadata=stations, event_metadata=events)
    finally:
        clear_active_config()

    assert len(pairs) == 4
    assert set(map(tuple, pairs[["event_id", "station"]].to_numpy())) == {
        ("E01", "STA01"),
        ("E01", "STA02"),
        ("E02", "STA01"),
        ("E02", "STA02"),
    }
    assert {"event_lat", "event_lon", "lat", "lon", "distance_km"} <= set(pairs.columns)


def test_prepare_event_station_table_normalizes_supplied_event_metadata_aliases() -> None:
    """Raw event metadata aliases should be canonicalized before pair joins."""

    stations = pd.DataFrame({"station": ["STA01"], "lat": [34.1], "lon": [-118.2]})
    events = prepare_event_metadata(
        pd.DataFrame({"event_title": ["E01"], "lat": [34.0], "lon": [-118.4], "mag": [4.2]})
    )

    pairs = prepare_event_station_table(station_metadata=stations, event_metadata=events)

    assert pairs.loc[0, "event_id"] == "E01"
    assert pairs.loc[0, "event_lat"] == 34.0
    assert pairs.loc[0, "event_lon"] == -118.4
    assert pairs.loc[0, "magnitude"] == 4.2
    assert "event_title" not in pairs.columns
    assert "distance_km" in pairs.columns


def test_prepare_event_station_table_normalizes_station_ids_before_join() -> None:
    """Event-station station aliases should match prepared station metadata."""

    stations = pd.DataFrame({"station": ["STA01"], "lat": [34.1], "lon": [-118.2]})
    events = pd.DataFrame({"event_id": ["E01"], "event_lat": [34.0], "event_lon": [-118.4]})
    raw_pairs = pd.DataFrame({"event": ["E01"], "site": ["sta01"]})

    pairs = prepare_event_station_table(raw_pairs, station_metadata=stations, event_metadata=events)

    assert pairs.loc[0, "station"] == "STA01"
    assert pairs.loc[0, "lat"] == 34.1
    assert pairs.loc[0, "lon"] == -118.2


def test_read_config_table_normalizes_event_metadata_aliases(tmp_path: Path) -> None:
    """Configured event metadata reads should not expose raw event_title IDs."""

    events_path = tmp_path / "events.csv"
    config_path = tmp_path / "spatial-vtk.yaml"
    events_path.write_text("event_title,lat,lon,mag\nE01,34.0,-118.4,4.2\n", encoding="utf-8")
    config_path.write_text(
        "\n".join(
            [
                "project:",
                "  root_dir: .",
                "paths:",
                "  event_metadata: events.csv",
            ]
        ),
        encoding="utf-8",
    )

    try:
        SpatialVTKConfig.from_file(config_path).activate()
        events = read_config_table("paths.event_metadata")
    finally:
        clear_active_config()

    assert events.loc[0, "event_id"] == "E01"
    assert events.loc[0, "event_lat"] == 34.0
    assert events.loc[0, "event_lon"] == -118.4
    assert "event_title" not in events.columns


def test_standard_output_table_helpers_use_active_config(tmp_path: Path) -> None:
    """Standard output helpers should write and read tables by artifact key."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        "\n".join(
            [
                "project:",
                "  root_dir: .",
                "outputs:",
                "  tables: outputs/tables",
            ]
        ),
        encoding="utf-8",
    )

    try:
        cfg = SpatialVTKConfig.from_file(config_path).activate()
        written = write_output_tables(
            prepared_stations=pd.DataFrame({"station": ["STA01"], "lat": [34.1], "lon": [-118.2]}),
            record_coverage=pd.DataFrame({"event_id": ["E01"], "station": ["STA01"], "source": ["observed"]}),
            cfg=cfg,
        )
        stations = load_output_table("prepared_stations")
        preview = preview_output_table("prepared_stations", nrows=1, columns=["station"])
    finally:
        clear_active_config()

    assert written["prepared_stations"].exists()
    assert written["record_coverage"] == tmp_path / "outputs" / "tables" / "record_coverage.csv"
    assert written["record_coverage"].exists()
    assert stations.loc[0, "station"] == "STA01"
    assert preview.to_dict("records") == [{"station": "STA01"}]


def test_load_or_build_output_table_reuses_and_refreshes_stale_tables(tmp_path: Path) -> None:
    """Derived output helpers should rebuild only when requested or stale."""

    config_path = tmp_path / "spatial-vtk.yaml"
    source_path = tmp_path / "source.csv"
    config_path.write_text(
        "\n".join(
            [
                "project:",
                "  root_dir: .",
                "outputs:",
                "  tables: outputs/tables",
            ]
        ),
        encoding="utf-8",
    )
    source_path.write_text("version\n1\n", encoding="utf-8")
    calls = {"count": 0}

    def build_table() -> pd.DataFrame:
        calls["count"] += 1
        return pd.DataFrame({"station": [f"STA{calls['count']:02d}"]})

    try:
        SpatialVTKConfig.from_file(config_path).activate()
        first = load_or_build_output_table("prepared_stations", build_table, source_path=source_path, verbose=False)
        second = load_or_build_output_table("prepared_stations", build_table, source_path=source_path, verbose=False)

        output_path = tmp_path / "outputs" / "tables" / "prepared_stations.csv"
        new_mtime = output_path.stat().st_mtime + 10
        source_path.touch()
        source_path.write_text("version\n2\n", encoding="utf-8")
        source_path.touch()
        os.utime(source_path, (new_mtime, new_mtime))
        refreshed = load_or_build_output_table("prepared_stations", build_table, source_path=source_path, verbose=False)
    finally:
        clear_active_config()

    assert calls["count"] == 2
    assert first.loc[0, "station"] == "STA01"
    assert second.loc[0, "station"] == "STA01"
    assert refreshed.loc[0, "station"] == "STA02"


def test_inventory_and_context_figures_write_outputs(tmp_path: Path) -> None:
    """Inventory and context figure helpers should write public workflow outputs."""

    observed = tmp_path / "observed"
    synthetic = tmp_path / "synthetic"
    observed.mkdir()
    synthetic.mkdir()
    (observed / "obs.mseed").write_bytes(b"observed")
    (synthetic / "syn.mseed").write_bytes(b"synthetic")

    inventory = build_observed_synthetic_inventory(observed, synthetic, relative_to=tmp_path)
    assert set(inventory["dataset"]) == {"observed", "synthetic"}
    assert "sha256" in inventory.columns

    stations = pd.DataFrame({"station": ["S1", "S2"], "lat": [34.0, 34.2], "lon": [-118.4, -118.2]})
    events = pd.DataFrame({"event_id": ["E1"], "event_lat": [34.1], "event_lon": [-118.3]})
    event_station = pd.DataFrame({"event_id": ["E1", "E1"], "station": ["S1", "S2"], "lat": [34.0, 34.2], "lon": [-118.4, -118.2], "event_lat": [34.1, 34.1], "event_lon": [-118.3, -118.3]})

    outputs = [
        plot_station_event_context(stations, events, tmp_path / "context.png", add_basemap=False),
        plot_station_coverage(event_station, tmp_path / "station_coverage.png"),
        plot_event_coverage(event_station, tmp_path / "event_coverage.png"),
    ]
    summary = summarize_coverage(event_station)
    assert summary["event_station_rows"] == 2
    for path in outputs:
        assert path.exists()
        assert path.stat().st_size > 0


def test_context_figures_write_optional_row_sidecars(tmp_path: Path) -> None:
    """Context figures should expose plotted/source rows when requested."""

    stations = pd.DataFrame({"station": ["S1", "S2"], "lat": [34.0, 34.2], "lon": [-118.4, -118.2]})
    events = pd.DataFrame({"event_id": ["E1"], "event_lat": [34.1], "event_lon": [-118.3], "magnitude": [4.1]})
    event_station = pd.DataFrame(
        {
            "event_id": ["E1", "E1"],
            "station": ["S1", "S2"],
            "distance_km": [10.0, 20.0],
        }
    )
    records = event_station.assign(
        observed_start_s=[-2.0, -1.0],
        observed_end_s=[65.0, 66.0],
        synthetic_start_s=[0.0, 0.0],
        synthetic_end_s=[60.0, 60.0],
    )
    sidecar_dir = tmp_path / "sidecars"

    plot_station_event_context(
        stations,
        events,
        tmp_path / "context.png",
        add_basemap=False,
        write_sidecar=True,
        sidecar_rows=1,
        sidecar_dir=sidecar_dir,
    )
    plot_station_coverage(
        event_station,
        tmp_path / "station_coverage.png",
        write_sidecar=True,
        sidecar_rows=1,
        sidecar_dir=sidecar_dir,
    )
    plot_station_event_beachball_map(
        events,
        tmp_path / "beachball.png",
        stations_df=stations,
        add_basemap=False,
        write_sidecar=True,
        sidecar_rows=1,
        sidecar_dir=sidecar_dir,
    )
    plot_record_coverage(
        records,
        tmp_path / "record_coverage.png",
        write_sidecar=True,
        sidecar_rows=1,
        sidecar_dir=sidecar_dir,
    )

    context_rows = pd.read_csv(sidecar_dir / "context.csv")
    context_meta = json.loads((sidecar_dir / "context.json").read_text(encoding="utf-8"))
    station_rows = pd.read_csv(sidecar_dir / "station_coverage.csv")
    station_source = pd.read_csv(sidecar_dir / "station_coverage.source.csv")
    beachball_meta = json.loads((sidecar_dir / "beachball.json").read_text(encoding="utf-8"))
    record_meta = json.loads((sidecar_dir / "record_coverage.json").read_text(encoding="utf-8"))

    assert len(context_rows) == 1
    assert context_meta["plot_row_count"] == 3
    assert context_meta["sampled"] is True
    assert set(station_rows.columns) >= {"station", "event_count"}
    assert len(station_source) == 1
    assert beachball_meta["plot_row_count"] == 3
    assert record_meta["plot_row_count"] == 2
    assert record_meta["source_row_count"] == 2
