from __future__ import annotations

import json

import pandas as pd
import pytest
from shapely.geometry import Polygon, mapping

from spatial_vtk.config import SpatialVTKConfig, clear_active_config
from spatial_vtk.spatial.calculate import (
    BoundaryCorridorConfig,
    CorridorAnchorConfig,
    CorridorSelectionConfig,
    GeoJSONNoOverlapError,
    GeoJSONPathControl,
    PolygonCorridorConfig,
    add_geojson_metadata_to_metrics,
    annotate_points_with_geojson,
    apply_geojson_path_control,
    build_geojson_region_summary,
    build_geojson_region_summary_from_table,
    build_boundary_corridors,
    build_station_edge_corridors,
    classify_records_by_corridors,
    classify_paths_with_geojson,
    geojson_polygon_preview_table,
    load_geojson_polygons,
    run_geojson_region_summary_workflow,
    select_events_in_corridors,
    select_records_by_corridors,
    summarize_corridor_event_counts,
    summarize_metrics_by_geojson,
)
from spatial_vtk.spatial.map import plot_corridor_map, plot_geojson_polygons_map


def _write_geojson(path, features):
    payload = {"type": "FeatureCollection", "features": features}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _feature(name: str, polygon: Polygon, **properties):
    props = {"name": name, **properties}
    return {"type": "Feature", "properties": props, "geometry": mapping(polygon)}


def test_geojson_point_and_path_controls_are_general(tmp_path):
    geojson = _write_geojson(
        tmp_path / "regions.geojson",
        [
            _feature("West Basin", Polygon([(-118.4, 34.0), (-118.0, 34.0), (-118.0, 34.4), (-118.4, 34.4)]), region_type="basin"),
            _feature("East Block", Polygon([(-117.8, 34.0), (-117.4, 34.0), (-117.4, 34.4), (-117.8, 34.4)]), region_type="block"),
        ],
    )
    metrics = pd.DataFrame(
        {
            "model": ["m1", "m1", "m1"],
            "metric": ["C5", "C5", "C5"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec"],
            "event_id": ["e1", "e2", "e3"],
            "station": ["S1", "S2", "S3"],
            "event_lon": [-118.2, -118.6, -117.6],
            "event_lat": [34.2, 34.2, 34.2],
            "sta_lon": [-118.6, -118.2, -117.9],
            "sta_lat": [34.2, 34.2, 34.2],
            "residual": [0.2, -0.1, 0.3],
        }
    )

    station_annotated = annotate_points_with_geojson(metrics, geojson, point="station", selector={"region_type": "basin"})
    assert "station_geojson_inside_west_basin" in station_annotated.columns
    assert station_annotated["station_geojson_inside_any"].tolist() == [False, True, False]

    event_annotated = add_geojson_metadata_to_metrics(metrics, geojson, target="event", selector="all")
    assert event_annotated["event_geojson_labels"].tolist() == ["West Basin", "", "East Block"]

    crossing = classify_paths_with_geojson(
        metrics,
        geojson,
        relation="crosses_boundary",
        selector="West Basin",
        direction="inside_to_outside",
    )
    assert crossing["path_geojson_matches"].tolist() == [True, False, False]
    assert crossing.loc[0, "path_geojson_cross_direction"] == "inside_to_outside"

    control = GeoJSONPathControl(relation="ends_in", selector=["West Basin"])
    ends_in = apply_geojson_path_control(metrics, geojson, control)
    assert ends_in["path_geojson_matches"].tolist() == [False, True, False]

    summary_path = tmp_path / "geojson_summary.csv"
    summary = summarize_metrics_by_geojson(
        event_annotated,
        label_col="event_geojson_labels",
        value_col="residual",
        savecsv=True,
        outpath=summary_path,
    )
    assert set(summary["geojson_label"]) == {"West Basin", "East Block"}
    assert summary["n"].sum() == 2
    assert summary_path.exists()

    preview = geojson_polygon_preview_table(geojson, selector={"region_type": "basin"})
    assert preview["feature_name"].tolist() == ["West Basin"]
    assert preview.loc[0, "region"] == "West Basin"
    assert preview.loc[0, "geometry_type"] == "Polygon"
    assert preview.loc[0, "min_lon"] == pytest.approx(-118.4)
    assert preview.loc[0, "max_lat"] == pytest.approx(34.4)
    assert preview.loc[0, "properties"]["region_type"] == "basin"
    assert int(preview.loc[0, "property_count"]) == 2

    features = load_geojson_polygons(geojson)
    feature_preview = geojson_polygon_preview_table(features, selector="East Block")
    assert feature_preview["feature_name"].tolist() == ["East Block"]

    region_summary = build_geojson_region_summary(pd.concat([metrics, metrics], ignore_index=True), geojson, verbose=True)
    station_rows = region_summary.loc[region_summary["relation"] == "station_inside"]
    event_rows = region_summary.loc[region_summary["relation"] == "event_inside"]
    path_rows = region_summary.loc[region_summary["relation"] == "crosses_boundary"]
    assert int(station_rows["unique_records"].max()) == 3
    assert int(event_rows["unique_records"].max()) == 3
    assert int(path_rows["unique_records"].max()) == 3
    assert "outside" in set(station_rows["region"])


def test_geojson_region_summary_reads_only_needed_table_columns(tmp_path):
    """GeoJSON summary workflow should handle large metric tables via slim reads."""

    geojson = _write_geojson(
        tmp_path / "regions.geojson",
        [_feature("West Basin", Polygon([(-118.4, 34.0), (-118.0, 34.0), (-118.0, 34.4), (-118.4, 34.4)]))],
    )
    metrics = pd.DataFrame(
        {
            "model": ["m1", "m1", "m1", "m1"],
            "metric": ["PGA", "PGA", "PGV", "PGV"],
            "event_title": ["e1", "e1", "e2", "e2"],
            "station_name": ["S1", "S1", "S2", "S3"],
            "event_lon": [-118.2, -118.2, -118.6, -118.6],
            "event_lat": [34.2, 34.2, 34.2, 34.2],
            "station_longitude": [-118.6, -118.6, -118.2, -117.9],
            "station_latitude": [34.2, 34.2, 34.2, 34.2],
            "large_unused_payload": ["x" * 64, "y" * 64, "z" * 64, "q" * 64],
        }
    )
    metrics_csv = tmp_path / "metrics_long.csv"
    metrics.to_csv(metrics_csv, index=False)

    summary = build_geojson_region_summary_from_table(metrics_csv, geojson, chunksize=2, verbose=True)

    assert set(summary["relation"]) == {"station_inside", "event_inside", "crosses_boundary"}
    assert int(summary["source_rows"].max()) == len(metrics)
    assert int(summary.loc[summary["relation"] == "station_inside", "unique_records"].max()) == 3
    assert "large_unused_payload" not in summary.columns

    clear_active_config()
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
paths:
  region_geojson: regions.geojson
outputs:
  tables: outputs/tables
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    result = run_geojson_region_summary_workflow(metrics_csv, cfg=cfg, chunksize=2, verbose=True)

    assert result.path == tmp_path / "outputs" / "tables" / "geojson_region_summaries.csv"
    assert result.path.exists()
    assert result.rows == len(pd.read_csv(result.path))
    assert result.source_rows == len(metrics)

    parquet_path = tmp_path / "metrics_long.parquet"
    try:
        metrics.to_parquet(parquet_path, index=False)
    except Exception:
        return
    parquet_summary = build_geojson_region_summary_from_table(parquet_path, geojson, verbose=True)
    assert int(parquet_summary["source_rows"].max()) == len(metrics)


def test_geojson_no_overlap_error_is_clear(tmp_path):
    geojson = _write_geojson(
        tmp_path / "far.geojson",
        [_feature("Far Away", Polygon([(10.0, 10.0), (11.0, 10.0), (11.0, 11.0), (10.0, 11.0)]))],
    )
    df = pd.DataFrame({"station": ["S1"], "sta_lon": [-118.0], "sta_lat": [34.0]})
    with pytest.raises(GeoJSONNoOverlapError, match="No station points overlap"):
        annotate_points_with_geojson(df, geojson, point="station")


def test_polygon_edge_corridor_wrapper_selects_events(tmp_path):
    geojson = _write_geojson(
        tmp_path / "corridor_regions.geojson",
        [_feature("West Basin", Polygon([(-118.4, 34.0), (-118.0, 34.0), (-118.0, 34.4), (-118.4, 34.4)]))],
    )
    stations = pd.DataFrame(
        {
            "station": ["EDGE", "FAR"],
            "network": ["XX", "XX"],
            "sta_lon": [-118.39, -117.0],
            "sta_lat": [34.2, 34.2],
        }
    )
    config = PolygonCorridorConfig(
        selector="West Basin",
        near_edge_width_km=3.0,
        corridor_length_km=25.0,
        corridor_width_km=25.0,
        corridor_shape="rectangle",
    )
    corridors = build_station_edge_corridors(stations, geojson, config=config)
    assert corridors["station"].tolist() == ["EDGE"]
    assert corridors.loc[0, "polygon_name"] == "West Basin"
    assert corridors.loc[0, "corridor_geometry"].is_valid

    events = pd.DataFrame(
        {
            "event_id": ["inside_corridor", "outside_corridor"],
            "event_lon": [-118.25, -117.5],
            "event_lat": [34.2, 34.2],
            "event_depth_km": [5.0, 5.0],
        }
    )
    selected = select_events_in_corridors(events, corridors)
    assert selected["event_id"].tolist() == ["inside_corridor"]
    counts = summarize_corridor_event_counts(selected)
    assert counts.loc[0, "event_count"] == 1


def test_boundary_corridors_support_keyword_modes_and_path_selection(tmp_path):
    geojson = _write_geojson(
        tmp_path / "boundary_regions.geojson",
        [_feature("Example Region", Polygon([(-118.4, 34.0), (-118.0, 34.0), (-118.0, 34.4), (-118.4, 34.4)]))],
    )
    config = BoundaryCorridorConfig(
        selector="Example Region",
        mode="through_boundary",
        along_boundary_width_km=18.0,
        inside_length_km=18.0,
        outside_length_km=18.0,
        anchor=CorridorAnchorConfig(source="all_boundary_segments", segment_spacing_km=80.0),
    )
    corridors = build_boundary_corridors(geojson, config=config)
    assert not corridors.empty
    assert set(corridors["corridor_mode"]) == {"through_boundary"}
    assert corridors["corridor_geometry"].map(lambda geom: geom.is_valid).all()

    records = pd.DataFrame(
        {
            "event_id": ["crosses", "inside_only", "far"],
            "station": ["S1", "S2", "S3"],
            "event_lon": [-118.5, -118.2, -117.5],
            "event_lat": [34.2, 34.2, 34.8],
            "sta_lon": [-118.2, -118.25, -117.4],
            "sta_lat": [34.2, 34.25, 34.8],
        }
    )
    selected = select_records_by_corridors(
        records,
        corridors,
        config=CorridorSelectionConfig(
            side_filter="opposite_polygon_sides",
            path_filter="passes_through_corridor",
            min_path_length_km=0.0,
        ),
    )
    assert "crosses" in set(selected["event_id"])
    assert "inside_only" not in set(selected["event_id"])
    assert selected["path_passes_through_corridor"].all()


def test_boundary_corridors_support_station_and_event_anchor_strategies(tmp_path):
    geojson = _write_geojson(
        tmp_path / "anchor_regions.geojson",
        [_feature("Example Region", Polygon([(-118.4, 34.0), (-118.0, 34.0), (-118.0, 34.4), (-118.4, 34.4)]))],
    )
    stations = pd.DataFrame(
        {
            "station": ["BUSY", "QUIET"],
            "sta_lon": [-118.39, -118.02],
            "sta_lat": [34.2, 34.2],
        }
    )
    records = pd.DataFrame({"station": ["BUSY", "BUSY", "BUSY", "QUIET"], "event_id": ["E1", "E2", "E3", "E1"]})
    station_config = BoundaryCorridorConfig(
        selector="Example Region",
        mode="inward",
        along_boundary_width_km=12.0,
        inside_length_km=12.0,
        anchor=CorridorAnchorConfig(source="station", strategy="max_records", top_n=1),
    )
    station_corridors = build_boundary_corridors(geojson, config=station_config, station_df=stations, records_df=records)
    assert station_corridors["anchor_label"].tolist() == ["BUSY"]
    assert station_corridors["outside_length_km"].tolist() == [0.0]

    events = pd.DataFrame(
        {
            "event_id": ["SMALL", "LARGE"],
            "event_lon": [-118.38, -118.01],
            "event_lat": [34.2, 34.2],
            "magnitude": [3.2, 5.4],
        }
    )
    event_config = BoundaryCorridorConfig(
        selector="Example Region",
        mode="outward",
        along_boundary_width_km=12.0,
        outside_length_km=12.0,
        anchor=CorridorAnchorConfig(source="event", strategy="largest_magnitude", top_n=1),
    )
    event_corridors = build_boundary_corridors(geojson, config=event_config, event_df=events)
    assert event_corridors["anchor_label"].tolist() == ["LARGE"]
    assert event_corridors["inside_length_km"].tolist() == [0.0]


def test_corridor_map_wrapper_writes_context_figure(tmp_path):
    geojson = _write_geojson(
        tmp_path / "map_regions.geojson",
        [_feature("Example Region", Polygon([(-118.4, 34.0), (-118.0, 34.0), (-118.0, 34.4), (-118.4, 34.4)]))],
    )
    corridors = build_boundary_corridors(
        geojson,
        config=BoundaryCorridorConfig(
            selector="Example Region",
            mode="through_boundary",
            along_boundary_width_km=16.0,
            inside_length_km=12.0,
            outside_length_km=12.0,
            anchor=CorridorAnchorConfig(source="coordinate", lon=-118.4, lat=34.2),
        ),
    )
    stations = pd.DataFrame({"station": ["S1"], "sta_lon": [-118.2], "sta_lat": [34.2]})
    events = pd.DataFrame({"event_id": ["E1"], "event_lon": [-118.5], "event_lat": [34.2]})
    records = pd.DataFrame({"event_lon": [-118.5], "event_lat": [34.2], "lon": [-118.2], "lat": [34.2]})
    output = plot_corridor_map(
        corridors,
        tmp_path / "corridor_map.png",
        stations_df=stations,
        events_df=events,
        records_df=records,
        add_basemap=False,
        write_sidecar=True,
    )
    assert output.exists()
    assert output.stat().st_size > 0
    sidecar = tmp_path / "sidecars" / "corridor_map.csv"
    assert sidecar.exists()
    metadata = json.loads(sidecar.with_suffix(".json").read_text(encoding="utf-8"))
    rows = pd.read_csv(sidecar)
    assert {"corridor", "station", "event", "path"} <= set(rows["_figure_layer"])
    assert metadata["plot_row_count"] == 4
    assert "corridor_geometry_wkt" in rows.columns


def test_geojson_polygon_map_writes_layer_sidecar(tmp_path):
    geojson = _write_geojson(
        tmp_path / "sidecar_regions.geojson",
        [_feature("Example Region", Polygon([(-118.4, 34.0), (-118.0, 34.0), (-118.0, 34.4), (-118.4, 34.4)]))],
    )
    stations = pd.DataFrame({"station": ["S1"], "sta_lon": [-118.2], "sta_lat": [34.2]})
    events = pd.DataFrame({"event_id": ["E1"], "event_lon": [-118.3], "event_lat": [34.1]})

    output = plot_geojson_polygons_map(
        geojson,
        tmp_path / "geojson_map.png",
        stations_df=stations,
        events_df=events,
        add_basemap=False,
        write_sidecar=True,
    )

    assert output.exists()
    assert output.stat().st_size > 0
    sidecar = tmp_path / "sidecars" / "geojson_map.csv"
    assert sidecar.exists()
    metadata = json.loads(sidecar.with_suffix(".json").read_text(encoding="utf-8"))
    rows = pd.read_csv(sidecar)
    assert {"polygon", "station", "event"} <= set(rows["_figure_layer"])
    assert metadata["plot_row_count"] == 3
    assert "geometry_wkt" in rows.columns
