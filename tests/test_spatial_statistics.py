"""Tests for public spatial-statistics calculation helpers."""

from __future__ import annotations

from pathlib import Path
import json
import os

import matplotlib
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Polygon, mapping

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")
matplotlib.use("Agg", force=True)

from spatial_vtk.config import SpatialVTKConfig, clear_active_config
from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.io import OutputGroup, read_table, write_table
from spatial_vtk.metrics.plot import MetricFigureContext, plot_score_trends
from spatial_vtk.spatial.calculate.clustering import assign_redcap_clusters, run_residual_feature_clustering
from spatial_vtk.spatial.calculate.correlation import (
    build_distance_bin_summary,
    build_directional_distance_bin_summary,
    compute_global_morans_i,
    evaluate_spatial_block_holdouts,
    fit_exponential_correlation_length,
    moran_result_to_frame,
    summarize_directional_fits,
)
from spatial_vtk.spatial.calculate.geology import (
    add_station_geology_classes,
    bootstrap_contrast,
    bootstrap_contrast_table,
    load_region_geometries,
    run_geology_spatial_tests,
    station_summary,
)
from spatial_vtk.spatial.calculate.patterns import build_pattern_similarity_station_anomalies, pattern_similarity
from spatial_vtk.spatial.calculate.pca import compute_pca_spatial_modes
from spatial_vtk.spatial.calculate.prepare_stats import (
    build_metric_field,
    build_station_feature_table,
    center_field_by_event,
    normalize_metrics_table,
    summarize_station_bias,
)
from spatial_vtk.spatial.calculate.workflow import spatial_statistics_output_paths
from spatial_vtk.spatial.calculate.workflow import (
    StandardSpatialProductSummaryResult,
    StandardSpatialWorkflowOutputResult,
    run_spatial_derived_outputs_workflow,
    run_spatial_derived_outputs_workflow_from_config,
    run_spatial_statistics_workflow,
    run_spatial_statistics_workflow_from_config,
    station_bias_preview_frame,
    spatial_correlation_preview_frame,
    spatial_metric_product_frames,
    spatial_metric_product_summary_frame,
    spatial_metric_table_frame,
    spatial_pca_product_frames,
    spatial_workflow_failure_frame,
    summarize_standard_spatial_products,
)
from spatial_vtk.spatial.calculate.corridors import (
    corridor_record_pair_frame,
    corridor_record_preview_frame,
    event_station_records_matching_pairs,
    geojson_matched_record_frame,
)
from spatial_vtk.spatial.map.correlation import (
    plot_block_holdout_error_map,
    plot_cluster_map,
    plot_cluster_summary,
    plot_redcap_cluster_map,
    plot_station_bias_map,
)
from spatial_vtk.spatial.map.pca import plot_pca_mode_map, plot_pca_summary
from spatial_vtk.spatial.plot.correlation import (
    plot_block_holdout_scatter,
    plot_cluster_feature_heatmap,
    plot_cluster_solution_scores,
    plot_correlogram,
    plot_distance_correlation_by_metric,
    plot_directional_correlogram,
    plot_pattern_similarity,
    plot_semivariogram,
)
from spatial_vtk.spatial.plot.large_run import (
    RegionBoxplotResult,
    SpatialFigureContext,
    SpatialFigureSuiteResult,
    StandardAdditionalPlottingFigureResult,
    StandardAdditionalPlottingInputResult,
    StandardGeoJSONCorridorFigureResult,
    StandardGeoJSONFigureResult,
    StandardGeoJSONPlottingInputResult,
    StandardSpatialDiagnosticFigureResult,
    StandardSpatialMapFigureResult,
    prepare_spatial_figure_context_from_notebook_settings,
    write_standard_additional_plotting_figures,
    write_standard_geojson_corridor_figures,
    write_standard_geojson_region_figures,
    write_standard_spatial_diagnostic_figures,
    write_standard_spatial_map_figures,
    write_large_run_geojson_region_figures_from_outputs,
    write_large_run_geojson_region_figures_from_notebook_settings,
    write_large_run_region_boxplot,
    write_large_run_region_boxplot_from_outputs,
    write_large_run_region_boxplot_from_notebook_settings,
    write_large_run_spatial_figure_suite_from_notebook_settings,
    write_large_run_spatial_summary_figures_from_outputs,
    load_standard_additional_plotting_inputs,
    load_standard_geojson_plotting_inputs,
)
from spatial_vtk.spatial.plot.metrics import plot_geology_contrast
from spatial_vtk.spatial.plot.pca import plot_pca_explained_variance, plot_pca_feature_loadings
from spatial_vtk.visualize.figure_context import value_color_settings
from spatial_vtk.visualize.figure_sidecars import (
    figure_sidecar_metadata_path,
    figure_sidecar_status_frame,
    read_figure_sidecar_metadata,
    write_figure_row_sidecar,
)


def _toy_metrics_table() -> pd.DataFrame:
    """Return a small metrics table with spatially coherent station bias."""

    records: list[dict[str, object]] = []
    lat0 = 34.0
    lon0 = -118.4
    for row in range(4):
        for col in range(4):
            station_bias = 0.08 * col + 0.03 * row
            for event_index, event_bias in enumerate([-0.2, -0.05, 0.1, 0.25]):
                log2_ratio = event_bias + station_bias + 0.01 * ((row + col + event_index) % 2)
                records.append(
                    {
                        "simulation_model": "example_model",
                        "simulation_band": "1-2s",
                        "station_component": "Z",
                        "event_title": f"event_{event_index}",
                        "event_magnitude": 4.5,
                        "event_latitude": lat0 + 0.02 * event_index,
                        "event_longitude": lon0 - 0.02 * event_index,
                        "station_name": f"STA_{row}_{col}",
                        "station_latitude": lat0 + 0.12 * row,
                        "station_longitude": lon0 + 0.12 * col,
                        "C5_obs": float(2.0**log2_ratio),
                        "C5_syn": 1.0,
                    }
                )
    return pd.DataFrame(records)


def test_spatial_workflow_failure_frame_formats_result_failures() -> None:
    """Spatial workflow failures should be displayable without notebook dataframe code."""

    frame = spatial_workflow_failure_frame(
        {
            "failures": [
                {
                    "metric": "PGA",
                    "step": "geology_contrasts",
                    "error": "RuntimeError",
                    "message": "missing station metadata",
                }
            ]
        }
    )

    assert list(frame.columns) == ["metric", "step", "error", "message"]
    assert frame.loc[0, "metric"] == "PGA"
    assert frame.loc[0, "step"] == "geology_contrasts"
    assert spatial_workflow_failure_frame({"failures": []}).empty


def test_summarize_standard_spatial_products_returns_products_and_display_frames() -> None:
    """Step 4 notebooks should get per-metric products through package code."""

    metric_field = pd.DataFrame(
        {
            "metric": ["PGA", "PGA", "PGV"],
            "event_id": ["e1", "e2", "e1"],
            "station": ["STA1", "STA2", "STA1"],
            "field_value": [0.1, -0.2, 0.3],
        }
    )
    event_centered = pd.DataFrame(
        {
            "metric": ["PGA", "PGA", "PGV"],
            "event_id": ["e1", "e2", "e1"],
            "station": ["STA1", "STA2", "STA1"],
            "centered_value": [0.05, -0.05, 0.2],
        }
    )
    station_bias = pd.DataFrame(
        {
            "metric": ["PGA", "PGV"],
            "station": ["STA1", "STA1"],
            "mean_centered": [0.05, 0.2],
            "median_centered": [0.05, 0.2],
            "n_events": [2, 1],
        }
    )

    result = summarize_standard_spatial_products(
        {"metrics": ("PGA", "PGV")},
        metric_field=metric_field,
        event_centered=event_centered,
        station_bias=station_bias,
    )

    assert isinstance(result, StandardSpatialProductSummaryResult)
    assert result.metrics == ("PGA", "PGV")
    assert result.spatial_products["PGA"]["field"]["metric"].tolist() == ["PGA", "PGA"]
    assert result.spatial_products["PGV"]["station_bias"]["station"].tolist() == ["STA1"]
    summary = result.summary_frame()
    assert summary["metric"].tolist() == ["PGA", "PGA", "PGA", "PGV", "PGV", "PGV"]
    assert summary.loc[summary["Output"].eq("Metric field"), "Rows"].tolist() == [2, 1]
    preview = result.station_bias_preview_frame()
    assert preview["metric"].tolist() == ["PGA", "PGV"]
    assert preview["station"].tolist() == ["STA1", "STA1"]


def test_write_standard_geojson_region_figures_returns_status_tables(monkeypatch, tmp_path) -> None:
    """Standard Step 5 GeoJSON figures should be orchestrated by package code."""

    import spatial_vtk.spatial as spatial_public

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e1"],
            "station": ["STA1", "STA2"],
            "metric": ["PGA", "PGA"],
            "passband": ["1-2 sec", "1-2 sec"],
            "component": ["Z", "Z"],
            "model": ["m1", "m1"],
            "log2_residual": [0.5, -0.25],
            "lon": [-118.1, -118.2],
            "lat": [34.1, 34.2],
            "event_lon": [-118.0, -118.0],
            "event_lat": [34.0, 34.0],
        }
    )
    stations = pd.DataFrame({"station": ["STA1", "STA2"], "lon": [-118.1, -118.2], "lat": [34.1, 34.2]})
    events = pd.DataFrame({"event_id": ["e1"], "event_name": ["Example"], "event_lon": [-118.0], "event_lat": [34.0]})

    def fake_preview(path):
        return pd.DataFrame({"name": ["LA Basin", "Glendale"], "geometry_type": ["Polygon", "Polygon"]})

    def fake_region_frame(frame, path, *, target, region_col, **kwargs):
        result = frame.copy()
        result[region_col] = "LA Basin" if target == "station" else "Glendale"
        return result

    def fake_subset(frame, **kwargs):
        return frame.copy()

    def fake_field(frame, metric, *, value_column):
        result = frame.copy()
        result["field_value"] = result[value_column]
        return result

    def fake_station_bias(frame, **kwargs):
        return pd.DataFrame(
            {
                "station": ["STA1", "STA2"],
                "lon": [-118.1, -118.2],
                "lat": [34.1, 34.2],
                "mean_centered": [0.5, -0.25],
            }
        )

    monkeypatch.setattr(spatial_public, "geojson_polygon_preview_table", fake_preview)
    monkeypatch.setattr(spatial_public, "geojson_metric_region_frame", fake_region_frame)
    monkeypatch.setattr(spatial_public, "geojson_metric_subset_frame", fake_subset)
    monkeypatch.setattr(spatial_public, "build_metric_field", fake_field)
    monkeypatch.setattr(spatial_public, "summarize_station_bias", fake_station_bias)

    class _Sidecars:
        def kwargs(self):
            return {"write_sidecar": False}

    class _Settings:
        showfig = False
        add_basemap = True
        sidecars = _Sidecars()

    class _Outputs:
        def figure_path(self, name, *, stem_parts):
            return tmp_path / f"{name}__{'_'.join(str(part) for part in stem_parts)}.png"

    calls: list[tuple[str, Path, dict[str, object]]] = []

    def fake_plot(*args, outpath, **kwargs):
        calls.append((str(kwargs.get("title", "")), Path(outpath), kwargs))
        Path(outpath).write_text("figure", encoding="utf-8")

    result = write_standard_geojson_region_figures(
        metrics=metrics,
        stations=stations,
        events=events,
        outputs=_Outputs(),
        settings=_Settings(),
        geojson_path=tmp_path / "regions.geojson",
        geojson_plot_func=fake_plot,
        boxplot_func=fake_plot,
        station_map_func=fake_plot,
        summary_func=lambda **kwargs: {"path": str(tmp_path / "geojson_region_summaries.csv"), "rows": 2},
    )

    assert isinstance(result, StandardGeoJSONFigureResult)
    assert result.model_name == "m1"
    assert list(result.preview_frame()["name"]) == ["LA Basin", "Glendale"]
    assert len(result.metrics_by_regions) == 2
    assert set(result.metrics_by_regions["event_region"]) == {"Glendale"}
    assert result.summary_frame().loc[0, "rows"] == 2
    status = result.status_frame()
    assert {"name", "artifact_label", "resolved_path", "path", "exists"} <= set(status.columns)
    assert status["status"].tolist() == ["wrote", "wrote", "wrote"]
    assert status["figure_exists"].tolist() == [True, True, True]
    assert status["exists"].tolist() == [True, True, True]
    assert status["path"].tolist() == status["figure_path"].tolist()
    assert status["artifact"].tolist() == ["geojson_regions", "pga_region_boxplot", "regional_pga_station_map"]
    assert len(calls) == 3
    assert calls[-1][2]["value_col"] == "mean_centered"


def test_write_standard_geojson_corridor_figures_returns_status_tables(monkeypatch, tmp_path) -> None:
    """Standard Step 5 corridor figures should be orchestrated by package code."""

    import spatial_vtk.config as config_public

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e1"],
            "station": ["STA1", "STA2"],
            "metric": ["PGV", "PGV"],
            "passband": ["1-2 sec", "2-3 sec"],
            "component": ["Z", "Z"],
            "model": ["m1", "m1"],
            "log2_residual": [0.5, -0.25],
            "station_region": ["LA Basin", "LA Basin"],
            "lon": [-118.1, -118.2],
            "lat": [34.1, 34.2],
            "event_lon": [-118.0, -118.0],
            "event_lat": [34.0, 34.0],
        }
    )
    stations = pd.DataFrame({"station": ["STA1", "STA2"], "lon": [-118.1, -118.2], "lat": [34.1, 34.2]})
    events = pd.DataFrame({"event_id": ["e1"], "event_name": ["Example"], "event_lon": [-118.0], "event_lat": [34.0]})
    event_stations = pd.DataFrame(
        {
            "event_id": ["e1", "e1"],
            "station": ["STA1", "STA2"],
            "lon": [-118.1, -118.2],
            "lat": [34.1, 34.2],
            "event_lon": [-118.0, -118.0],
            "event_lat": [34.0, 34.0],
        }
    )
    comparison_eligible = event_stations.copy()

    def fake_render(plot_func, outputs, figure_path_name, settings, *args, **kwargs):
        path = outputs.figure_path(figure_path_name, stem=kwargs.get("stem"), stem_parts=kwargs.get("stem_parts"))
        plot_func(*args, outpath=path, **kwargs)

    monkeypatch.setattr(config_public, "render_notebook_figure", fake_render)

    class _Sidecars:
        def kwargs(self):
            return {"write_sidecar": False}

    class _Settings:
        showfig = False
        add_basemap = False
        sidecars = _Sidecars()

    class _Outputs:
        def figure_path(self, name, *, stem=None, stem_parts=None):
            parts = stem_parts or (stem or name,)
            return tmp_path / f"{name}__{'_'.join(str(part) for part in parts)}.png"

    calls: list[tuple[str, Path, dict[str, object]]] = []

    def fake_plot(*args, outpath, **kwargs):
        calls.append((str(kwargs.get("title", "")), Path(outpath), kwargs))
        Path(outpath).write_text("figure", encoding="utf-8")

    def fake_build_corridors(geojson_path, *, config, station_df=None, event_df=None):
        return pd.DataFrame({"corridor_id": [config.mode], "selector": [config.selector], "geometry": [None]})

    def fake_select_records(records, corridors, *, config):
        result = records.copy()
        result["corridor_id"] = str(corridors["corridor_id"].iloc[0])
        return result

    def fake_classify(records, geojson_path, **kwargs):
        result = records.copy()
        result["path_geojson_matches"] = True
        return result

    def fake_matched(records):
        return records.copy()

    def fake_comparison(left, right):
        return left.copy()

    def fake_waveform_records(records, **kwargs):
        result = records.head(1).copy()
        result["component"] = kwargs["component"]
        result["passband"] = kwargs["passband"]
        return result

    def fake_event_ids(records):
        return ["e1"]

    def fake_event_rows(frame, *, event_ids):
        return frame.loc[frame["event_id"].isin(event_ids)].copy()

    def fake_event_preview(frame):
        return frame[["event_id", "event_name"]].copy()

    def fake_metric_subset(frame, **kwargs):
        return frame.copy()

    def fake_metric_field(frame, metric, *, value_column):
        result = frame.copy()
        result["field_value"] = result[value_column]
        return result

    def fake_station_bias(frame, **kwargs):
        return pd.DataFrame(
            {
                "station": ["STA1", "STA2"],
                "lon": [-118.1, -118.2],
                "lat": [34.1, 34.2],
                "mean_centered": [0.5, -0.25],
            }
        )

    def fake_pair_frame(records):
        return records[["event_id", "station"]].copy()

    def fake_preview(records):
        return records[["event_id", "station", "corridor_id"]].head(2).copy()

    result = write_standard_geojson_corridor_figures(
        metrics_by_regions=metrics,
        stations=stations,
        event_stations=event_stations,
        events=events,
        comparison_eligible=comparison_eligible,
        outputs=_Outputs(),
        spatial_settings=_Settings(),
        waveform_settings=_Settings(),
        geojson_path=tmp_path / "regions.geojson",
        build_corridors_func=fake_build_corridors,
        select_records_func=fake_select_records,
        classify_paths_func=fake_classify,
        matched_records_func=fake_matched,
        comparison_records_func=fake_comparison,
        waveform_records_func=fake_waveform_records,
        event_ids_func=fake_event_ids,
        event_rows_func=fake_event_rows,
        event_preview_func=fake_event_preview,
        metric_subset_func=fake_metric_subset,
        metric_field_func=fake_metric_field,
        station_bias_func=fake_station_bias,
        corridor_pair_func=fake_pair_frame,
        corridor_preview_func=fake_preview,
        corridor_map_func=fake_plot,
        record_section_func=fake_plot,
        station_map_func=fake_plot,
    )

    assert isinstance(result, StandardGeoJSONCorridorFigureResult)
    assert result.boundary_crossing_frame()["corridor_id"].tolist() == ["through_boundary", "through_boundary"]
    assert result.outward_event_frame()["event_id"].tolist() == ["e1"]
    status = result.status_frame()
    assert {"name", "artifact_label", "resolved_path", "path", "exists"} <= set(status.columns)
    assert status["status"].tolist() == ["wrote", "wrote", "wrote", "wrote"]
    assert status["figure_exists"].tolist() == [True, True, True, True]
    assert status["exists"].tolist() == [True, True, True, True]
    assert status["path"].tolist() == status["figure_path"].tolist()
    assert status["artifact"].tolist() == [
        "through_boundary_corridor_map",
        "outward_corridor_map",
        "boundary_crossing_record_section",
        "pgv_outward_corridor_station_map",
    ]
    assert len(calls) == 4
    assert calls[-1][2]["records_df"]["station"].tolist() == ["STA1", "STA2"]


def test_standard_geojson_plotting_inputs_write_figures_from_configured_inputs(monkeypatch, tmp_path) -> None:
    """Standard Step 5 input results should own table/path wiring for figure writers."""

    import spatial_vtk.spatial.plot.large_run as large_run

    metrics = pd.DataFrame({"metric": ["PGA"], "station": ["STA1"], "event_id": ["e1"]})
    stations = pd.DataFrame({"station": ["STA1"]})
    events = pd.DataFrame({"event_id": ["e1"]})
    event_stations = pd.DataFrame({"event_id": ["e1"], "station": ["STA1"]})
    comparison_eligible = pd.DataFrame({"event_id": ["e1"], "station": ["STA1"]})
    geojson_path = tmp_path / "regions.geojson"
    outputs = object()
    spatial_settings = object()
    waveform_settings = object()
    metrics_by_regions = pd.DataFrame({"metric": ["PGA"], "station": ["STA1"], "event_id": ["e1"]})
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_region_writer(**kwargs):
        calls.append(("region", kwargs))
        return StandardGeoJSONFigureResult(
            rows=(),
            region_preview=pd.DataFrame(),
            metrics_by_regions=metrics_by_regions,
            model_name="m1",
            summary={},
        )

    def fake_corridor_writer(**kwargs):
        calls.append(("corridor", kwargs))
        return StandardGeoJSONCorridorFigureResult(
            rows=(),
            boundary_crossing_preview=pd.DataFrame(),
            outward_event_preview=pd.DataFrame(),
            metrics_by_regions=metrics_by_regions,
        )

    monkeypatch.setattr(large_run, "write_standard_geojson_region_figures", fake_region_writer)
    monkeypatch.setattr(large_run, "write_standard_geojson_corridor_figures", fake_corridor_writer)

    inputs = StandardGeoJSONPlottingInputResult(
        metrics=metrics,
        stations=stations,
        events=events,
        event_stations=event_stations,
        comparison_eligible=comparison_eligible,
        geojson_path=geojson_path,
        outputs=outputs,
    )

    region_result = inputs.write_region_figures(
        settings=spatial_settings,
        passbands=["1-2 sec"],
        component="Z",
        station_region="LA Basin",
        event_region="Glendale",
    )
    corridor_result = inputs.write_corridor_figures(
        metrics_by_regions=region_result.metrics_by_regions,
        spatial_settings=spatial_settings,
        waveform_settings=waveform_settings,
        passbands=["1-2 sec"],
        component="Z",
        boundary_region="LA Basin",
        through_anchor_station="OLI",
        outward_event_id="e1",
        corridor_station_region="LA Basin",
    )

    assert isinstance(region_result, StandardGeoJSONFigureResult)
    assert isinstance(corridor_result, StandardGeoJSONCorridorFigureResult)
    assert [kind for kind, _ in calls] == ["region", "corridor"]
    region_kwargs = calls[0][1]
    assert region_kwargs["metrics"] is metrics
    assert region_kwargs["stations"] is stations
    assert region_kwargs["events"] is events
    assert region_kwargs["outputs"] is outputs
    assert region_kwargs["settings"] is spatial_settings
    assert region_kwargs["geojson_path"] == geojson_path
    assert region_kwargs["summary_metrics_table"] == "paths.metric_figure_snapshot"
    assert region_kwargs["summary_geojson_path"] == "paths.region_geojson"
    corridor_kwargs = calls[1][1]
    assert corridor_kwargs["metrics_by_regions"] is metrics_by_regions
    assert corridor_kwargs["stations"] is stations
    assert corridor_kwargs["event_stations"] is event_stations
    assert corridor_kwargs["events"] is events
    assert corridor_kwargs["comparison_eligible"] is comparison_eligible
    assert corridor_kwargs["outputs"] is outputs
    assert corridor_kwargs["spatial_settings"] is spatial_settings
    assert corridor_kwargs["waveform_settings"] is waveform_settings
    assert corridor_kwargs["geojson_path"] == geojson_path


def test_load_standard_geojson_plotting_inputs_reads_metric_columns_only(monkeypatch, tmp_path: Path) -> None:
    """Standard Step 5 inputs should not materialize unused metrics_long columns."""

    import inspect

    import spatial_vtk.io as io_public
    import spatial_vtk.spatial.plot.large_run as large_run_module

    source = inspect.getsource(large_run_module.load_standard_geojson_plotting_inputs)
    assert "_read_if_exists(metrics_path, columns=SPATIAL_EVENT_ROW_COLUMNS)" in source
    assert 'metrics_outputs.load_table("metrics_long"' not in source

    metrics_path = tmp_path / "metrics_long.csv"
    pd.DataFrame(
        {
            "event_id": ["e1"],
            "station": ["STA1"],
            "metric": ["PGA"],
            "passband": ["1-2 sec"],
            "component": ["Z"],
            "model": ["m1"],
            "log2_residual": [0.2],
            "unused_large_payload": ["x" * 1000],
        }
    ).to_csv(metrics_path, index=False)
    stations = pd.DataFrame({"station": ["STA1"], "lon": [-118.1], "lat": [34.1]})
    events = pd.DataFrame({"event_id": ["e1"], "event_name": ["Example"]})
    event_stations = pd.DataFrame({"event_id": ["e1"], "station": ["STA1"]})
    comparison_eligible = pd.DataFrame({"event_id": ["e1"], "station": ["STA1"], "component": ["Z"]})
    geojson_path = tmp_path / "regions.geojson"
    geojson_path.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")

    class _Group:
        def __init__(self, name: str):
            self.name = name
            if name == "step_03_metrics":
                self.metrics_long_path = metrics_path

        def load_tables(self, mapping, *, cfg=None):  # noqa: ANN001, ANN202
            if self.name == "step_01_ingest":
                assert mapping == {
                    "stations": "prepared_stations_path",
                    "events": "prepared_events_path",
                    "event_stations": "event_station_path",
                }
                return {"stations": stations, "events": events, "event_stations": event_stations}
            assert self.name == "step_05_geojson"
            assert mapping == {"comparison_eligible": "comparison_eligible_path"}
            return {"comparison_eligible": comparison_eligible}

        def load_table(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            raise AssertionError("Step 5 GeoJSON inputs should use column-projected path reads.")

    def fake_output_group(name, *, cfg=None):  # noqa: ANN001, ANN202
        return _Group(name)

    def fake_load_configured_input_paths(mapping, *, cfg=None):  # noqa: ANN001, ANN202
        assert mapping == {"region_geojson": "paths.region_geojson"}
        return {"region_geojson": geojson_path}

    monkeypatch.setattr(io_public, "output_group", fake_output_group)
    monkeypatch.setattr(io_public, "load_configured_input_paths", fake_load_configured_input_paths)

    result = load_standard_geojson_plotting_inputs(cfg=object())

    assert isinstance(result, StandardGeoJSONPlottingInputResult)
    assert "unused_large_payload" not in result.metrics.columns
    assert result.metrics[["event_id", "station", "metric", "log2_residual"]].to_dict("records") == [
        {"event_id": "e1", "station": "STA1", "metric": "PGA", "log2_residual": 0.2}
    ]
    assert result.stations is stations
    assert result.events is events
    assert result.event_stations is event_stations
    assert result.comparison_eligible is comparison_eligible
    assert result.geojson_path == geojson_path


def test_load_standard_additional_plotting_inputs_uses_configured_groups(monkeypatch) -> None:
    """Standard Step 6 inputs should load through one package helper."""

    import spatial_vtk.io as io_public

    metrics = pd.DataFrame({"metric": ["PGA"], "event_id": ["e1"], "station": ["STA1"]})
    events = pd.DataFrame({"event_id": ["e1"], "event_name": ["Example"]})
    event_stations = pd.DataFrame({"event_id": ["e1"], "station": ["STA1"]})
    comparison_eligible = pd.DataFrame({"event_id": ["e1"], "station": ["STA1"], "component": ["Z"]})
    calls: list[str] = []

    class _Group:
        def __init__(self, name: str):
            self.name = name

        def load_tables(self, mapping, *, cfg=None):  # noqa: ANN001, ANN202
            calls.append(self.name)
            if self.name == "step_01_ingest":
                assert mapping == {"events": "prepared_events_path", "event_stations": "event_station_path"}
                return {"events": events, "event_stations": event_stations}
            assert mapping == {"comparison_eligible": "comparison_eligible_path"}
            return {"comparison_eligible": comparison_eligible}

    def fake_output_group(name, *, cfg=None):  # noqa: ANN001, ANN202
        return _Group(name)

    def fake_load_configured_input_tables(mapping, *, cfg=None):  # noqa: ANN001, ANN202
        assert mapping == {"metrics": "paths.metric_figure_snapshot"}
        return {"metrics": metrics}

    monkeypatch.setattr(io_public, "output_group", fake_output_group)
    monkeypatch.setattr(io_public, "load_configured_input_tables", fake_load_configured_input_tables)

    result = load_standard_additional_plotting_inputs(cfg=object())

    assert isinstance(result, StandardAdditionalPlottingInputResult)
    assert calls == ["step_01_ingest", "step_06_plotting"]
    assert result.metrics is metrics
    assert result.events is events
    assert result.event_stations is event_stations
    assert result.comparison_eligible is comparison_eligible
    status = result.status_frame()
    assert status["table"].tolist() == ["metrics", "event_stations", "events", "comparison_eligible"]
    assert status["rows"].tolist() == [1, 1, 1, 1]


def test_write_standard_additional_plotting_figures_returns_previews(tmp_path) -> None:
    """Standard Step 6 plotting should be orchestrated by one package helper."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e1"],
            "station": ["STA1", "STA2"],
            "metric": ["PGA", "PGV"],
            "band": ["1-2 sec", "1-2 sec"],
            "passband": ["1-2 sec", "1-2 sec"],
            "component": ["Z", "Z"],
            "model": ["cvmsi", "cvmsi"],
            "distance_km": [10.0, 20.0],
            "log2_residual": [0.1, -0.2],
            "value_obs": [1.1, 0.8],
            "value_syn": [1.0, 1.0],
        }
    )
    event_stations = pd.DataFrame({"event_id": ["e1"], "station": ["STA1"]})
    events = pd.DataFrame({"event_id": ["e1"], "event_name": ["Example event"]})
    comparison_eligible = pd.DataFrame({"event_id": ["e1"], "station": ["STA1"], "component": ["R"]})
    waveform_records = pd.DataFrame(
        {
            "event_id": ["e1"],
            "station": ["STA1"],
            "distance_km": [10.0],
            "component": ["R"],
        }
    )
    pattern_rows = pd.DataFrame({"station_name": ["STA1"], "dataset": ["observed"], "metric": ["PGA"], "bin": ["1-2 sec"], "value": [0.0]})

    class _Settings:
        showfig = False

        def plot_kwargs(self, *, include_basemap=False):
            return {"showfig": False, "add_basemap": bool(include_basemap), "write_sidecar": False}

    class _Outputs:
        def figure_path(self, name, *, stem=None, stem_parts=None):
            filename = stem or "_".join(str(part) for part in (stem_parts or (name,)))
            return tmp_path / f"{name}__{filename}.png"

    calls: list[tuple[str, str]] = []

    def fake_waveform_records(*args, **kwargs):
        return waveform_records.copy()

    def fake_summary(frame, *, comparison_eligible=None):
        return pd.DataFrame({"Input": ["Metric rows"], "Value": [len(frame)]})

    def fake_region(frame, **kwargs):
        result = frame.copy()
        result["station_geojson_region"] = "LA Basin"
        return result

    def fake_pattern(*args, **kwargs):
        return pattern_rows.copy()

    def fake_order(frame, **kwargs):
        return frame[["station", "distance_km", "component"]].copy()

    def fake_plot(*args, outpath=None, **kwargs):
        calls.append((Path(outpath).name, str(kwargs.get("title", ""))))
        Path(outpath).write_text("figure", encoding="utf-8")

    result = write_standard_additional_plotting_figures(
        metrics=metrics,
        event_stations=event_stations,
        events=events,
        comparison_eligible=comparison_eligible,
        outputs=_Outputs(),
        waveform_settings=_Settings(),
        metric_settings=_Settings(),
        waveform_records_func=fake_waveform_records,
        event_label_func=lambda frame, event_id: "Example event",
        metric_summary_func=fake_summary,
        geojson_region_func=fake_region,
        pattern_rows_func=fake_pattern,
        waveform_order_func=fake_order,
        waveform_map_func=fake_plot,
        pattern_plot_func=fake_plot,
        scatterplot_func=fake_plot,
        boxplot_func=fake_plot,
        heatmap_func=fake_plot,
    )

    assert isinstance(result, StandardAdditionalPlottingFigureResult)
    status = result.status_frame()
    assert {"name", "artifact_label", "resolved_path", "path", "exists"} <= set(status.columns)
    assert status["status"].tolist() == ["wrote", "wrote", "wrote", "wrote", "wrote"]
    assert status["figure_exists"].tolist() == [True, True, True, True, True]
    assert status["exists"].tolist() == [True, True, True, True, True]
    assert status["path"].tolist() == status["figure_path"].tolist()
    assert result.metric_summary_frame().loc[0, "Value"] == 2
    assert result.waveform_order_frame().loc[0, "station"] == "STA1"
    assert result.pattern_frame().loc[0, "dataset"] == "observed"
    assert result.pattern_preview_frame(nrows=1).to_dict("records") == [
        {
            "station_name": "STA1",
            "dataset": "observed",
            "metric": "PGA",
            "bin": "1-2 sec",
            "value": 0.0,
        }
    ]
    assert set(result.region_metrics["station_geojson_region"]) == {"LA Basin"}
    assert len(calls) == 5


def test_standard_additional_plotting_input_result_writes_figures(tmp_path) -> None:
    """The standard Step 6 input result should own figure writer arguments."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e1"],
            "station": ["STA1", "STA2"],
            "metric": ["PGA", "PGV"],
            "band": ["1-2 sec", "1-2 sec"],
            "passband": ["1-2 sec", "1-2 sec"],
            "component": ["Z", "Z"],
            "model": ["cvmsi", "cvmsi"],
            "distance_km": [10.0, 20.0],
            "log2_residual": [0.1, -0.2],
        }
    )
    event_stations = pd.DataFrame({"event_id": ["e1"], "station": ["STA1"]})
    events = pd.DataFrame({"event_id": ["e1"], "event_name": ["Example event"]})
    comparison_eligible = pd.DataFrame({"event_id": ["e1"], "station": ["STA1"], "component": ["R"]})
    waveform_records = pd.DataFrame({"event_id": ["e1"], "station": ["STA1"], "distance_km": [10.0], "component": ["R"]})
    pattern_rows = pd.DataFrame(
        {"station_name": ["STA1"], "dataset": ["observed"], "metric": ["PGA"], "bin": ["1-2 sec"], "value": [0.0]}
    )
    calls: list[str] = []

    class _Settings:
        showfig = False

        def plot_kwargs(self, *, include_basemap=False):
            return {"showfig": False, "add_basemap": bool(include_basemap), "write_sidecar": False}

    class _Outputs:
        def figure_path(self, name, *, stem=None, stem_parts=None):
            filename = stem or "_".join(str(part) for part in (stem_parts or (name,)))
            return tmp_path / f"{name}__{filename}.png"

    def fake_plot(*args, outpath=None, **kwargs):
        calls.append(Path(outpath).name)
        Path(outpath).write_text("figure", encoding="utf-8")

    result = StandardAdditionalPlottingInputResult(
        metrics=metrics,
        event_stations=event_stations,
        events=events,
        comparison_eligible=comparison_eligible,
        outputs=_Outputs(),
    ).write_figures(
        waveform_settings=_Settings(),
        metric_settings=_Settings(),
        waveform_records_func=lambda *args, **kwargs: waveform_records.copy(),
        event_label_func=lambda frame, event_id: "Example event",
        metric_summary_func=lambda frame, *, comparison_eligible=None: pd.DataFrame({"Input": ["Metric rows"], "Value": [len(frame)]}),
        geojson_region_func=lambda frame, **kwargs: frame.assign(station_geojson_region="LA Basin"),
        pattern_rows_func=lambda *args, **kwargs: pattern_rows.copy(),
        waveform_order_func=lambda frame, **kwargs: frame[["station", "distance_km", "component"]].copy(),
        waveform_map_func=fake_plot,
        pattern_plot_func=fake_plot,
        scatterplot_func=fake_plot,
        boxplot_func=fake_plot,
        heatmap_func=fake_plot,
    )

    assert isinstance(result, StandardAdditionalPlottingFigureResult)
    status = result.status_frame()
    assert status["status"].tolist() == ["wrote", "wrote", "wrote", "wrote", "wrote"]
    assert status["figure_exists"].tolist() == [True, True, True, True, True]
    assert result.metric_summary_frame().loc[0, "Value"] == 2
    assert result.waveform_order_frame().loc[0, "station"] == "STA1"
    assert len(calls) == 5


def test_spatial_metric_product_summary_frame_counts_rows_events_and_stations() -> None:
    """Per-metric spatial product summaries should come from package code."""

    field = pd.DataFrame({"event_id": ["e1", "e1", "e2"], "station": ["STA1", "STA2", "STA1"]})
    centered = pd.DataFrame({"event_id": ["e1"], "station": ["STA1"]})
    station_bias = pd.DataFrame({"station": ["STA1", "STA2"]})

    summary = spatial_metric_product_summary_frame(
        metric_field=field,
        event_centered=centered,
        station_bias=station_bias,
    ).set_index("Output")

    assert summary.loc["Metric field", "Rows"] == 3
    assert summary.loc["Metric field", "Events"] == 2
    assert summary.loc["Metric field", "Stations"] == 2
    assert summary.loc["Event-centered field", "Rows"] == 1
    assert summary.loc["Event-centered field", "Events"] == 1
    assert summary.loc["Station bias", "Rows"] == 2
    assert pd.isna(summary.loc["Station bias", "Events"])
    assert summary.loc["Station bias", "Stations"] == 2


def test_spatial_metric_table_frame_filters_metric_and_handles_single_metric_tables() -> None:
    """Metric-specific table selection should be package-owned for notebooks."""

    table = pd.DataFrame({"metric": ["PGA", "PGV"], "value": [1, 2]})
    filtered = spatial_metric_table_frame(table, "PGA")

    assert filtered.to_dict("records") == [{"metric": "PGA", "value": 1}]
    assert spatial_metric_table_frame(pd.DataFrame()).empty
    assert spatial_metric_table_frame(pd.DataFrame({"value": [3]}), "PGA").to_dict("records") == [
        {"value": 3}
    ]


def test_spatial_metric_product_frames_selects_all_standard_products() -> None:
    """Step 4 product frames should not require repeated notebook filters."""

    metric_field = pd.DataFrame({"metric": ["PGA", "PGV"], "field_value": [0.1, 0.2]})
    event_centered = pd.DataFrame({"metric": ["PGA", "PGV"], "field_centered": [0.0, 0.1]})
    station_bias = pd.DataFrame({"metric": ["PGA", "PGV"], "mean_centered": [0.3, 0.4]})

    products = spatial_metric_product_frames(
        "PGA",
        metric_field=metric_field,
        event_centered=event_centered,
        station_bias=station_bias,
    )

    assert set(products) == {"field", "centered", "station_bias"}
    assert products["field"]["field_value"].tolist() == [0.1]
    assert products["centered"]["field_centered"].tolist() == [0.0]
    assert products["station_bias"]["mean_centered"].tolist() == [0.3]


def test_write_standard_spatial_map_figures_owns_step04_map_calls(tmp_path: Path) -> None:
    """Standard Step 4 station-bias and residual-grid plotting should be package-owned."""

    products = {
        "PGA": {
            "station_bias": pd.DataFrame(
                {
                    "station": ["STA"],
                    "lon": [-118.0],
                    "lat": [34.0],
                    "mean_centered": [0.2],
                }
            ),
            "centered": pd.DataFrame(
                {
                    "event_id": ["E1"],
                    "station": ["STA"],
                    "lon": [-118.0],
                    "lat": [34.0],
                    "field_centered": [0.1],
                }
            ),
        }
    }
    outputs = OutputGroup(
        name="step_04_spatial",
        paths={
            "station_bias_figure_path": tmp_path / "figures" / "station_bias.png",
            "residual_grid_figure_path": tmp_path / "figures" / "residual_grid.png",
        },
    )
    seen: list[tuple[str, Path, dict[str, object]]] = []

    class Sidecars:
        @staticmethod
        def kwargs(**_kwargs) -> dict[str, object]:
            return {
                "write_sidecar": True,
                "sidecar_rows": 25,
                "sidecar_dir": tmp_path / "sidecars",
            }

    class Settings:
        add_basemap = True
        showfig = False
        sidecars = Sidecars()

    def _fake_station_bias(frame, *, outpath, title, value_col, value_label, **kwargs):
        output = Path(outpath)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("station bias", encoding="utf-8")
        seen.append(
            (
                "station_bias",
                output,
                {
                    "rows": len(frame),
                    "title": title,
                    "value_col": value_col,
                    "value_label": value_label,
                    **kwargs,
                },
            )
        )

    def _fake_residual_grid(frame, *, outpath, title, lon_col, lat_col, value_col, cell_size_deg, **kwargs):
        output = Path(outpath)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("grid", encoding="utf-8")
        seen.append(
            (
                "residual_grid",
                output,
                {
                    "rows": len(frame),
                    "title": title,
                    "lon_col": lon_col,
                    "lat_col": lat_col,
                    "value_col": value_col,
                    "cell_size_deg": cell_size_deg,
                    **kwargs,
                },
            )
        )

    result = write_standard_spatial_map_figures(
        products,
        outputs,
        Settings(),
        station_bias_plot_func=_fake_station_bias,
        residual_grid_plot_func=_fake_residual_grid,
    )

    assert isinstance(result, StandardSpatialMapFigureResult)
    assert [item[0] for item in seen] == ["station_bias", "residual_grid"]
    assert seen[0][1].name == "step_04_pga_station_bias.png"
    assert seen[1][1].name == "step_04_pga_residual_grid.png"
    for _, _, kwargs in seen:
        assert kwargs["add_basemap"] is True
        assert kwargs["showfig"] is False
        assert kwargs["savefig"] is True
        assert kwargs["write_sidecar"] is True
        assert kwargs["sidecar_rows"] == 25
        assert kwargs["sidecar_dir"] == tmp_path / "sidecars"
    status = result.status_frame()
    assert status["artifact"].tolist() == ["station_bias_map", "residual_grid_map"]
    assert set(status["status"]) == {"wrote"}
    assert status["row_count"].tolist() == [1, 1]
    assert status["figure_exists"].tolist() == [True, True]


def test_write_standard_spatial_map_figures_reports_plot_failures(tmp_path: Path) -> None:
    """Standard spatial figure helper should show per-figure failures in notebooks."""

    products = {
        "PGA": {
            "station_bias": pd.DataFrame({"station": ["STA"]}),
            "centered": pd.DataFrame({"station": ["STA"]}),
        }
    }
    outputs = OutputGroup(
        name="step_04_spatial",
        paths={
            "station_bias_figure_path": tmp_path / "figures" / "station_bias.png",
            "residual_grid_figure_path": tmp_path / "figures" / "residual_grid.png",
        },
    )

    class Settings:
        add_basemap = False
        showfig = False

        class sidecars:
            @staticmethod
            def kwargs(**_kwargs) -> dict[str, object]:
                return {}

    def _raise(*_args, **_kwargs):
        raise ValueError("bad plot")

    result = write_standard_spatial_map_figures(
        products,
        outputs,
        Settings(),
        station_bias_plot_func=_raise,
        residual_grid_plot_func=_raise,
    )

    status = result.status_frame()
    assert status["status"].tolist() == ["plot_failed", "plot_failed"]
    assert status["message"].str.contains("ValueError: bad plot").all()


def test_write_standard_spatial_diagnostic_figures_owns_step04_plot_loops(tmp_path: Path) -> None:
    """Standard Step 4 diagnostic plotting should be package-owned."""

    products = {
        "PGA": {
            "centered": pd.DataFrame(
                {
                    "event_id": ["E1"],
                    "station": ["STA"],
                    "field_centered": [0.1],
                }
            )
        }
    }
    spatial_tables = {
        "morans_i": pd.DataFrame({"metric": ["PGA"], "moran_i": [0.2], "p_two_sided": [0.04]}),
        "distance_bins": pd.DataFrame(
            {
                "metric": ["PGA"],
                "distance_center_km": [10.0],
                "mean_pair_correlation": [0.3],
                "pair_count": [12],
            }
        ),
        "geology_contrasts": pd.DataFrame({"metric": ["PGA"], "contrast": ["basin-crust"], "p_value": [0.03]}),
        "pca_station_scores": pd.DataFrame({"metric": ["PGA"], "station": ["STA"], "PC1_score": [0.5]}),
        "pca_feature_loadings": pd.DataFrame({"metric": ["PGA"], "mode": ["PC1"], "feature": ["x"], "loading": [0.7]}),
        "pca_explained_variance": pd.DataFrame({"metric": ["PGA"], "mode": ["PC1"], "variance_ratio": [0.8]}),
    }
    outputs = OutputGroup(
        name="step_04_spatial",
        paths={
            "spatial_correlation_distance_figure_path": tmp_path / "figures" / "spatial_correlation_distance.png",
            "pca_summary_figure_path": tmp_path / "figures" / "pca_summary.png",
            "geology_contrast_figure_path": tmp_path / "figures" / "geology_contrast.png",
        },
    )
    seen: list[tuple[str, Path, int, dict[str, object]]] = []

    class Sidecars:
        @staticmethod
        def kwargs(**_kwargs) -> dict[str, object]:
            return {
                "write_sidecar": True,
                "sidecar_rows": 15,
                "sidecar_dir": tmp_path / "sidecars",
            }

    class Settings:
        add_basemap = True
        showfig = False
        pca_mode = "PC1"
        sidecars = Sidecars()

    def _write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _fake_distance(frame, *, outpath, significance_df, title, **kwargs):
        output = Path(outpath)
        _write(output, "distance")
        seen.append(("distance", output, len(frame), {"significance_rows": len(significance_df), "title": title, **kwargs}))

    def _fake_pca(station_scores, explained, loadings, *, outpath, title, add_basemap, mode, **kwargs):
        output = Path(outpath)
        _write(output, "pca")
        seen.append(
            (
                "pca",
                output,
                len(station_scores),
                {
                    "explained_rows": len(explained),
                    "loading_rows": len(loadings),
                    "title": title,
                    "add_basemap": add_basemap,
                    "mode": mode,
                    **kwargs,
                },
            )
        )

    def _fake_geology(frame, *, outpath, station_metadata, contrast_df, title, **kwargs):
        output = Path(outpath)
        _write(output, "geology")
        seen.append(
            (
                "geology",
                output,
                len(frame),
                {
                    "station_rows": len(station_metadata),
                    "contrast_rows": len(contrast_df),
                    "title": title,
                    **kwargs,
                },
            )
        )

    result = write_standard_spatial_diagnostic_figures(
        products,
        spatial_tables,
        outputs,
        Settings(),
        metrics=("PGA",),
        site_metadata=pd.DataFrame({"station": ["STA"], "geology": ["basin"]}),
        distance_plot_func=_fake_distance,
        pca_plot_func=_fake_pca,
        geology_plot_func=_fake_geology,
    )

    assert isinstance(result, StandardSpatialDiagnosticFigureResult)
    assert [item[0] for item in seen] == ["distance", "pca", "geology"]
    assert seen[0][1].name == "step_04_spatial_correlation_distance.png"
    assert seen[1][1].name == "step_04_pga_pca_summary.png"
    assert seen[2][1].name == "step_04_pga_geology_contrast.png"
    for _, _, _, kwargs in seen:
        assert kwargs["showfig"] is False
        assert kwargs["savefig"] is True
        assert kwargs["write_sidecar"] is True
        assert kwargs["sidecar_rows"] == 15
        assert kwargs["sidecar_dir"] == tmp_path / "sidecars"
    assert seen[1][3]["add_basemap"] is True
    status = result.status_frame()
    assert status["artifact"].tolist() == ["spatial_correlation_distance", "pca_summary", "geology_contrast"]
    assert status["status"].tolist() == ["wrote", "wrote", "wrote"]
    assert status["figure_exists"].tolist() == [True, True, True]
    preview = result.preview_frame()
    assert {"spatial_correlation", "pca_explained_variance", "geology_contrast"} <= set(preview["artifact"])
    assert set(preview["metric"]) == {"PGA"}


def test_standard_spatial_workflow_output_result_writes_figures(tmp_path: Path) -> None:
    """The standard Step 4 result should own map and diagnostic figure wiring."""

    spatial_products = {
        "PGA": {
            "station_bias": pd.DataFrame(
                {"metric": ["PGA"], "station": ["STA"], "lon": [-118.0], "lat": [34.0], "mean_centered": [0.2]}
            ),
            "centered": pd.DataFrame(
                {
                    "metric": ["PGA"],
                    "event_id": ["E1"],
                    "station": ["STA"],
                    "lon": [-118.0],
                    "lat": [34.0],
                    "field_centered": [0.1],
                }
            ),
        }
    }
    spatial_tables = {
        "metric_field": pd.DataFrame({"metric": ["PGA"], "field_value": [0.1]}),
        "event_centered_residuals": spatial_products["PGA"]["centered"],
        "station_bias": spatial_products["PGA"]["station_bias"],
        "morans_i": pd.DataFrame({"metric": ["PGA"], "moran_i": [0.2]}),
        "distance_bins": pd.DataFrame({"metric": ["PGA"], "distance_center_km": [10.0], "pair_count": [5]}),
        "geology_contrasts": pd.DataFrame({"metric": ["PGA"], "contrast": ["basin-crust"]}),
        "pca_station_scores": pd.DataFrame({"metric": ["PGA"], "station": ["STA"], "PC1_score": [0.5]}),
        "pca_feature_loadings": pd.DataFrame({"metric": ["PGA"], "mode": ["PC1"], "feature": ["x"], "loading": [0.7]}),
        "pca_explained_variance": pd.DataFrame({"metric": ["PGA"], "mode": ["PC1"], "variance_ratio": [0.8]}),
    }
    outputs = OutputGroup(
        name="step_04_spatial",
        paths={
            "station_bias_figure_path": tmp_path / "figures" / "station_bias.png",
            "residual_grid_figure_path": tmp_path / "figures" / "residual_grid.png",
            "spatial_correlation_distance_figure_path": tmp_path / "figures" / "distance.png",
            "pca_summary_figure_path": tmp_path / "figures" / "pca.png",
            "geology_contrast_figure_path": tmp_path / "figures" / "geology.png",
        },
    )
    result = StandardSpatialWorkflowOutputResult(
        outputs=outputs,
        tables=spatial_tables,
        product_summary=StandardSpatialProductSummaryResult(
            metrics=("PGA",),
            spatial_products=spatial_products,
            summary_rows=(),
            station_bias_previews=(),
        ),
    )
    seen: list[tuple[str, str, int]] = []

    class Sidecars:
        @staticmethod
        def kwargs(**_kwargs) -> dict[str, object]:
            return {}

    class Settings:
        add_basemap = False
        showfig = False
        pca_mode = "PC1"
        sidecars = Sidecars()

    def _fake_plot(name):
        def _inner(frame: pd.DataFrame, *args, outpath, **_kwargs):
            output = Path(outpath)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(name, encoding="utf-8")
            seen.append((name, output.name, len(frame)))

        return _inner

    map_result = result.write_map_figures(
        Settings(),
        station_bias_plot_func=_fake_plot("station_bias"),
        residual_grid_plot_func=_fake_plot("residual_grid"),
    )
    diagnostic_result = result.write_diagnostic_figures(
        Settings(),
        site_metadata=pd.DataFrame({"station": ["STA"]}),
        distance_plot_func=_fake_plot("distance"),
        pca_plot_func=_fake_plot("pca"),
        geology_plot_func=_fake_plot("geology"),
    )

    assert isinstance(map_result, StandardSpatialMapFigureResult)
    assert isinstance(diagnostic_result, StandardSpatialDiagnosticFigureResult)
    assert [item[0] for item in seen] == ["station_bias", "residual_grid", "distance", "pca", "geology"]
    assert map_result.status_frame()["status"].tolist() == ["wrote", "wrote"]
    assert map_result.status_frame()["figure_exists"].tolist() == [True, True]
    assert diagnostic_result.status_frame()["status"].tolist() == ["wrote", "wrote", "wrote"]
    assert diagnostic_result.status_frame()["figure_exists"].tolist() == [True, True, True]


def test_spatial_pca_product_frames_selects_all_pca_products() -> None:
    """PCA product selection should be package-owned for Step 4 notebooks."""

    scores = pd.DataFrame({"metric": ["PGA", "PGV"], "PC1": [1.0, 2.0]})
    explained = pd.DataFrame({"metric": ["PGA", "PGV"], "variance_ratio": [0.7, 0.5]})
    loadings = pd.DataFrame({"metric": ["PGA", "PGV"], "loading": [0.2, 0.3]})

    products = spatial_pca_product_frames(
        "PGA",
        station_scores=scores,
        explained_variance=explained,
        feature_loadings=loadings,
    )

    assert set(products) == {"station_scores", "explained_variance", "feature_loadings"}
    assert products["station_scores"]["PC1"].tolist() == [1.0]
    assert products["explained_variance"]["variance_ratio"].tolist() == [0.7]
    assert products["feature_loadings"]["loading"].tolist() == [0.2]


def test_station_bias_preview_frame_filters_metric_and_bounds_columns() -> None:
    """Station-bias notebook previews should be package-owned and bounded."""

    station_bias = pd.DataFrame(
        {
            "metric": ["PGA", "PGA", "PGV"],
            "station": ["STA1", "STA2", "STA3"],
            "mean_centered": [0.1, 0.2, 0.3],
            "n_events": [3, 4, 5],
            "extra": ["x", "y", "z"],
        }
    )

    preview = station_bias_preview_frame(station_bias, metric="PGA", nrows=1)

    assert list(preview.columns) == ["metric", "station", "mean_centered", "n_events"]
    assert preview.to_dict("records") == [
        {"metric": "PGA", "station": "STA1", "mean_centered": 0.1, "n_events": 3}
    ]
    assert station_bias_preview_frame(pd.DataFrame()).empty


def test_corridor_record_preview_frame_deduplicates_and_bounds_rows() -> None:
    """Corridor selected-path previews should not require notebook-local slicing."""

    records = pd.DataFrame(
        {
            "event_id": ["e1", "e1", "e2"],
            "station": ["STA1", "STA1", "STA2"],
            "distance_km": [10.0, 10.0, 20.0],
            "path_length_in_corridor_km": [2.5, 2.5, 4.0],
            "unneeded": [1, 2, 3],
        }
    )

    preview = corridor_record_preview_frame(records, nrows=5)

    assert list(preview.columns) == [
        "event_id",
        "station",
        "distance_km",
        "path_length_in_corridor_km",
    ]
    assert preview.to_dict("records") == [
        {
            "event_id": "e1",
            "station": "STA1",
            "distance_km": 10.0,
            "path_length_in_corridor_km": 2.5,
        },
        {
            "event_id": "e2",
            "station": "STA2",
            "distance_km": 20.0,
            "path_length_in_corridor_km": 4.0,
        },
    ]
    assert corridor_record_preview_frame(None).empty


def test_corridor_record_pair_frame_returns_unique_event_station_rows() -> None:
    """Corridor pair selection should be reusable outside notebooks."""

    records = pd.DataFrame(
        {
            "event_id": ["e1", "e1", "e2"],
            "station": ["STA1", "STA1", "STA2"],
            "distance_km": [10.0, 11.0, 20.0],
        }
    )

    full = corridor_record_pair_frame(records)
    keys = corridor_record_pair_frame(records, keep_columns=False)

    assert full.to_dict("records") == [
        {"event_id": "e1", "station": "STA1", "distance_km": 10.0},
        {"event_id": "e2", "station": "STA2", "distance_km": 20.0},
    ]
    assert keys.to_dict("records") == [
        {"event_id": "e1", "station": "STA1"},
        {"event_id": "e2", "station": "STA2"},
    ]
    assert list(corridor_record_pair_frame(None).columns) == ["event_id", "station"]
    with pytest.raises(KeyError, match="missing required pair"):
        corridor_record_pair_frame(pd.DataFrame({"event_id": ["e1"]}))


def test_geojson_matched_record_frame_filters_truthy_rows() -> None:
    """GeoJSON match filtering should be reusable outside notebooks."""

    records = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3", "e4"],
            "path_geojson_matches": [True, False, "yes", None],
        }
    )

    matched = geojson_matched_record_frame(records)

    assert matched["event_id"].tolist() == ["e1", "e3"]
    assert geojson_matched_record_frame(None).empty
    with pytest.raises(KeyError, match="missing match column"):
        geojson_matched_record_frame(pd.DataFrame({"event_id": ["e1"]}))


def test_event_station_records_matching_pairs_preserves_records_and_order() -> None:
    """Pair filtering should replace notebook-local event/station merges."""

    records = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3", "e2"],
            "station": ["STA1", "sta2", "STA3", "STA2"],
            "value": [1, 2, 3, 4],
        }
    )
    pairs = pd.DataFrame({"event_id": ["e2", "e2", "e4"], "station": ["STA2", "STA2", "STA4"]})

    selected = event_station_records_matching_pairs(records, pairs)

    assert selected.to_dict("records") == [
        {"event_id": "e2", "station": "sta2", "value": 2},
        {"event_id": "e2", "station": "STA2", "value": 4},
    ]
    assert event_station_records_matching_pairs(records, None).empty
    assert event_station_records_matching_pairs(None, pairs).empty
    with pytest.raises(KeyError, match="missing required pair"):
        event_station_records_matching_pairs(pd.DataFrame({"event_id": ["e1"]}), pairs)


def test_spatial_correlation_preview_frame_filters_metric_and_bounds_distance_rows() -> None:
    """Correlation diagnostic previews should be package-owned and bounded."""

    morans = pd.DataFrame(
        {
            "metric": ["PGA", "PGV"],
            "moran_i": [0.2, 0.3],
            "p_two_sided": [0.05, 0.1],
        }
    )
    distance = pd.DataFrame(
        {
            "metric": ["PGA", "PGA", "PGA", "PGV"],
            "distance_center_km": [10.0, 20.0, 30.0, 10.0],
            "mean_pair_correlation": [0.8, 0.5, 0.2, 0.7],
        }
    )

    preview = spatial_correlation_preview_frame(
        morans_i=morans,
        distance_bins=distance,
        metric="PGA",
        distance_bin_rows=2,
    )

    assert list(preview["Table"]) == ["Moran's I", "Distance bins", "Distance bins"]
    assert set(preview["metric"]) == {"PGA"}
    assert preview["distance_center_km"].dropna().tolist() == [10.0, 20.0]
    assert spatial_correlation_preview_frame(metric="PGA").empty


def test_prepare_stats_correlation_holdout_and_clustering() -> None:
    """Metric preparation should feed spatial correlation, holdout, and clustering."""

    normalized = normalize_metrics_table(_toy_metrics_table(), default_model="example")
    field = build_metric_field(normalized, "C5")
    raw_station_bias = summarize_station_bias(field, min_events_per_station=2)
    centered = center_field_by_event(field, min_stations_per_event=3)
    station_bias = summarize_station_bias(centered, min_events_per_station=2)
    centered_direct = summarize_station_bias(field, min_events_per_station=2, center_by_event=True, min_stations_per_event=3)

    assert len(raw_station_bias) == 16
    assert len(station_bias) == 16
    assert len(centered_direct) == 16
    compare_raw = raw_station_bias[["station", "mean_centered"]].merge(station_bias[["station", "mean_centered"]], on="station", suffixes=("_raw", "_centered"))
    compare_centered = centered_direct[["station", "mean_centered"]].merge(station_bias[["station", "mean_centered"]], on="station", suffixes=("_direct", "_separate"))
    assert not np.allclose(compare_raw["mean_centered_raw"], compare_raw["mean_centered_centered"])
    assert np.allclose(compare_centered["mean_centered_direct"], compare_centered["mean_centered_separate"])
    moran = compute_global_morans_i(station_bias, k=4, permutations=19, random_seed=7)
    assert moran is not None
    assert moran.n == 16

    distance = build_distance_bin_summary(centered, bin_width_km=20, max_distance_km=120, random_seed=7)
    assert not distance.empty
    assert {"pair_count", "mean_pair_correlation"} <= set(distance.columns)

    blocks, predictions, summary = evaluate_spatial_block_holdouts(
        field,
        block_size_km=15,
        min_block_stations=1,
        min_stations_per_event=3,
        min_events_per_station=2,
        prediction_k=3,
    )
    assert not blocks.empty
    assert not predictions.empty
    assert {"rmse", "skill_vs_baseline"} <= set(summary.columns)

    fingerprint = station_bias[["station", "lat", "lon", "mean_centered"]].copy()
    fingerprint["synthetic_east_west_residual_pattern"] = (
        fingerprint["lon"] - fingerprint["lon"].mean()
    ) / fingerprint["lon"].std(ddof=0)
    assignments, scores, feature_summary, cluster_summary, best, features = run_residual_feature_clustering(
        fingerprint,
        cluster_min_k=2,
        cluster_max_k=4,
        random_seed=7,
    )
    assert best is not None
    assert not assignments.empty
    assert not scores.empty
    assert not feature_summary.empty
    assert not cluster_summary.empty
    assert {"mean_centered", "synthetic_east_west_residual_pattern"} <= set(features)


def test_metric_field_preserves_psa_period_and_path_geometry_for_large_run_figures(tmp_path: Path) -> None:
    """Compact spatial fields should retain columns Step 4 needs for PSA/path plots."""

    metrics = pd.DataFrame(
        {
            "metric": ["PSA", "PSA", "PSA", "PSA"],
            "model": ["m1", "m1", "m1", "m1"],
            "passband": ["", "", "", ""],
            "component": ["Z", "Z", "Z", "Z"],
            "event_id": ["e1", "e1", "e1", "e1"],
            "station": ["STA", "STB", "STA", "STB"],
            "sta_lat": [34.0, 34.1, 34.0, 34.1],
            "sta_lon": [-118.0, -118.1, -118.0, -118.1],
            "event_lat": [33.9, 33.9, 33.9, 33.9],
            "event_lon": [-118.2, -118.2, -118.2, -118.2],
            "period_s": [1.0, 1.0, 2.0, 2.0],
            "distance_km": [10.0, 20.0, 10.0, 20.0],
            "azimuth_deg": [45.0, 90.0, 45.0, 90.0],
            "backazimuth_deg": [225.0, 270.0, 225.0, 270.0],
            "log2_residual": [0.2, -0.1, 0.4, -0.2],
        }
    )

    field = build_metric_field(metrics, metric="PSA", value_column="log2_residual")
    centered = center_field_by_event(field, min_stations_per_event=2)
    context = MetricFigureContext.from_frame(
        centered,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=0,
        value_col="log2_residual",
    )
    items = list(context.iter_metric_frames(split_psa_period=True))

    assert {"period_s", "distance_km", "azimuth_deg", "backazimuth_deg", "log2_residual"} <= set(centered.columns)
    assert sorted(item["period_s"] for item in items) == [1.0, 2.0]
    for item in items:
        assert {"distance_km", "azimuth_deg", "backazimuth_deg"} <= set(item["df"].columns)
    station_period = context.station_period_summary_for_item(
        {"key": "psa", "label": "PSA", "metric": "PSA", "period_s": None, "df": centered}
    )
    assert set(station_period["period_s"]) == {1.0, 2.0}
    assert "log2_residual" in station_period.columns


def test_spatial_workflow_helpers_write_and_prepare_tables(tmp_path: Path) -> None:
    """Spatial workflow helpers should replace notebook-only dataframe handling."""

    normalized = normalize_metrics_table(_toy_metrics_table(), default_model="example")
    field = build_metric_field(normalized, "C5")
    centered = center_field_by_event(field, min_stations_per_event=3)
    station_bias = summarize_station_bias(centered, min_events_per_station=2)
    paths = spatial_statistics_output_paths(tmp_path)

    assert paths.metric_field.name == "metric_field.parquet"
    assert paths.geojson_region_summaries.name == "geojson_region_summaries.csv"

    moran = moran_result_to_frame(compute_global_morans_i(station_bias, k=4, permutations=9, random_seed=7))
    assert {"moran_i", "p_two_sided", "permutations"} <= set(moran.columns)

    features = build_station_feature_table(centered)
    assert {"station", "lat", "lon"} <= set(features.columns)
    assert any(column.startswith("event_") for column in features.columns)

    site = pd.DataFrame(
        {
            "station": centered["station"].drop_duplicates().tolist(),
            "mapped_region_type": ["Basin", "Mountains"] * (centered["station"].nunique() // 2),
        }
    )
    contrast = bootstrap_contrast_table(
        centered,
        station_metadata=site,
        group_col="mapped_region_type",
        left_values=("Basin",),
        right_values=("Mountains",),
        n_bootstrap=10,
        random_seed=7,
        outpath=paths.geology_contrasts,
    )
    assert paths.geology_contrasts.exists()
    assert set(contrast.columns) >= {"contrast_label", "effect_direction", "effect", "bootstrap_p", "n_events"}
    assert contrast["contrast_label"].iloc[0] == "Basin minus Mountains"
    assert contrast["statistic"].iloc[0] == "mean"
    contrast_fig = plot_geology_contrast(
        centered,
        station_metadata=site,
        contrast_df=contrast,
        group_col="mapped_region_type",
        left_values=("Basin",),
        right_values=("Mountains",),
        outpath=tmp_path / "geology_contrast.png",
        savefig=True,
        showfig=False,
    )
    assert contrast_fig.spatial_vtk_saved_path.exists()

    multiclass_site = pd.DataFrame(
        {
            "station": centered["station"].drop_duplicates().tolist(),
            "mapped_region_type": (["Basin", "Mountains", "Valley", "Hills"] * 4)[: centered["station"].nunique()],
        }
    )
    multiclass_contrast = bootstrap_contrast_table(
        centered,
        station_metadata=multiclass_site,
        group_col="mapped_region_type",
        baseline_values=("Basin",),
        compare_values=("Mountains", "Valley", "Hills"),
        min_stations_per_group=1,
        n_bootstrap=10,
        random_seed=7,
    )
    assert set(multiclass_contrast["contrast_label"]) == {
        "Mountains minus Basin",
        "Valley minus Basin",
        "Hills minus Basin",
    }
    assert multiclass_contrast["baseline_values"].eq("Basin").all()
    assert multiclass_contrast["percent_effect"].notna().all()
    assert {"significant_95", "significant_p05"} <= set(multiclass_contrast.columns)
    multiclass_fig = plot_geology_contrast(
        centered,
        station_metadata=multiclass_site,
        contrast_df=multiclass_contrast,
        group_col="mapped_region_type",
        baseline_values=("Basin",),
        compare_values=("Mountains", "Valley", "Hills"),
        outpath=tmp_path / "geology_multiclass_contrast.png",
        savefig=True,
        showfig=False,
    )
    assert multiclass_fig.spatial_vtk_saved_path.exists()


def test_spatial_statistics_workflow_writes_standard_outputs(tmp_path: Path) -> None:
    """The Step 4 spatial workflow should be callable outside notebooks."""

    clear_active_config()
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  tables: outputs/tables
spatial:
  metric: C5
  value_column: log2_residual
  min_stations_per_event: 3
  min_events_per_station: 2
  moran_neighbors: 2
  moran_permutations: 3
  cluster_min_k: 2
  cluster_max_k: 3
  pca_components: 2
  geology_min_stations_per_group: 1
  geology_bootstrap_samples: 3
""",
        encoding="utf-8",
    )
    metrics = normalize_metrics_table(_toy_metrics_table(), default_model="example")
    station_metadata = pd.DataFrame(
        {
            "station": metrics["station"].drop_duplicates().tolist(),
            "mapped_region_type": (["Basin", "Mountains"] * 8)[: metrics["station"].nunique()],
        }
    )

    clear_active_config()
    result = run_spatial_statistics_workflow(metrics, cfg=config_path, metric=("C5",), station_metadata=station_metadata, verbose=True)

    assert result.metrics == ("C5",)
    assert not result.tables["metric_field"].empty
    assert not result.tables["event_centered_residuals"].empty
    assert not result.tables["station_bias"].empty
    assert set(result.paths) >= {"metric_field", "station_bias", "morans_i", "permutation_moran", "geology_contrasts"}
    assert result.paths["metric_field"] == tmp_path / "outputs" / "tables" / "metric_field.parquet"
    assert result.paths["metric_field"].exists()
    assert result.paths["station_bias"].exists()
    assert result.paths["permutation_moran"].exists()
    assert result.tables["permutation_moran"].equals(result.tables["morans_i"])
    assert result.tables["metric_field"]["metric"].eq("C5").all()
    assert result.tables["station_bias"]["metric"].eq("C5").all()

    figure_context = SpatialFigureContext.from_config(
        figure_dir=tmp_path / "figures",
        make_figures=True,
        write_sidecars=True,
        sidecar_rows=2,
    )
    assert figure_context.metric_field is not None
    assert not figure_context.metric_field.empty
    assert figure_context.metric_value_col == "field_value"
    assert figure_context.event_value_col == "field_centered"
    assert figure_context.table("station_bias") is not None

    item = {"key": "c5", "label": "C5", "metric": "C5", "period_s": None, "df": figure_context.metric_field}
    station_summary = figure_context.station_summary_for_map(item["df"], "field_value")
    assert len(station_summary) == 16
    assert {"sta_lon", "sta_lat", "source_row_count", "source_event_count", "aggregation"} <= set(station_summary.columns)
    assert set(station_summary["source_event_count"]) == {4}

    def _dummy_plot(frame: pd.DataFrame, *, output_path, **kwargs) -> None:
        Path(output_path).write_text(str(len(frame)), encoding="utf-8")

    output = figure_context.write_spatial_plot(
        "spatial_debug_station_map",
        item,
        _dummy_plot,
        df=station_summary,
        source_df=item["df"],
        required=["sta_lon", "sta_lat", "field_value"],
        value_col="field_value",
    )
    assert output is not None
    sidecar_path = tmp_path / "figures" / "sidecars" / f"{output.stem}.csv"
    source_sidecar_path = tmp_path / "figures" / "sidecars" / f"{output.stem}.source.csv"
    metadata = json.loads(sidecar_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert sidecar_path.exists()
    assert source_sidecar_path.exists()
    assert metadata["plot_station_count"] == 16
    assert metadata["source_station_count"] == 16
    assert metadata["source_event_count"] == 4
    assert metadata["source_written_row_count"] == 2


def test_spatial_derived_outputs_workflow_writes_optional_plot_inputs(tmp_path: Path) -> None:
    """Optional Step 4 plot-input tables should be generated by a package workflow."""

    clear_active_config()
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  tables: outputs/tables
spatial:
  metric: C5
  value_column: log2_residual
  min_stations_per_event: 3
  min_events_per_station: 2
  cluster_min_k: 2
  cluster_max_k: 3
  block_size_km: 5
  block_min_block_stations: 1
  block_max_folds: 2
  pattern_metric: C5
  pattern_passband: 1-2s
  pattern_component: Z
  pattern_model: example_model
""",
        encoding="utf-8",
    )
    metrics = normalize_metrics_table(_toy_metrics_table(), default_model="example_model")
    clear_active_config()
    summaries = run_spatial_statistics_workflow(metrics, cfg=config_path, metric=("C5",))
    pattern_metrics = summaries.tables["metric_field"][
        ["station", "metric", "band", "component", "model", "field_value"]
    ].copy()
    pattern_metrics.rename(columns={"band": "passband"}, inplace=True)
    pattern_metrics["value_syn"] = 1.0
    pattern_metrics["value_obs"] = np.power(2.0, pd.to_numeric(pattern_metrics["field_value"], errors="coerce"))

    result = run_spatial_derived_outputs_workflow(
        pattern_metrics,
        metric_field=summaries.tables["metric_field"],
        station_bias=summaries.tables["station_bias"],
        cfg=config_path,
        verbose=True,
    )

    assert not result.failures
    assert set(result.paths) == {
        "block_holdout_predictions",
        "redcap_clusters",
        "pattern_similarity_station_anomalies",
    }
    assert result.rows["block_holdout_predictions"] > 0
    assert result.rows["redcap_clusters"] > 0
    assert result.rows["pattern_similarity_station_anomalies"] > 0
    assert result.paths["block_holdout_predictions"].exists()
    assert result.paths["redcap_clusters"].exists()
    assert result.paths["pattern_similarity_station_anomalies"].exists()

    reused = run_spatial_derived_outputs_workflow(
        pattern_metrics,
        metric_field=summaries.tables["metric_field"],
        station_bias=summaries.tables["station_bias"],
        cfg=config_path,
    )
    assert set(reused.reused) == {
        "block_holdout_predictions",
        "redcap_clusters",
        "pattern_similarity_station_anomalies",
    }


def test_spatial_derived_reuse_counts_use_lightweight_table_counter() -> None:
    """Reused derived outputs should not full-read existing large tables for row counts."""

    import inspect

    import spatial_vtk.spatial.calculate.workflow as workflow_module

    source = inspect.getsource(workflow_module.run_spatial_derived_outputs_workflow)
    should_skip_source = source.split("def should_skip", 1)[1].split('if "block_holdout_predictions"', 1)[0]
    assert "table_row_count(path)" in should_skip_source
    assert "len(read_table(path))" not in should_skip_source


def test_spatial_pattern_derived_csv_loads_only_required_metric_columns(tmp_path: Path) -> None:
    """Pattern-similarity derived outputs should not materialize wide metric tables."""

    import inspect

    import spatial_vtk.spatial.calculate.workflow as workflow_module

    source = inspect.getsource(workflow_module._load_metrics_for_derived)
    assert "PATTERN_SIMILARITY_METRIC_COLUMNS" in source
    assert "read_table(path, columns=selected_columns)" in source
    assert "read_table(path, usecols=lambda column: column in selected)" in source

    clear_active_config()
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  tables: outputs/tables
spatial:
  metric: PGA
  value_column: log2_residual
""",
        encoding="utf-8",
    )
    metrics = pd.DataFrame(
        {
            "metric": ["PGA", "PGA", "PGA", "PGA"],
            "station": ["STA01", "STA02", "STA01", "STA02"],
            "passband": ["1-2 sec", "1-2 sec", "2-3 sec", "2-3 sec"],
            "component": ["Z", "Z", "Z", "Z"],
            "model": ["model_a", "model_a", "model_a", "model_a"],
            "value_obs": [2.0, 4.0, 3.0, 5.0],
            "value_syn": [1.0, 2.0, 1.5, 2.5],
            "unused_large_blob": ["x" * 1000, "y" * 1000, "z" * 1000, "w" * 1000],
        }
    )
    metrics_path = tmp_path / "inputs" / "metrics_wide.csv"
    metrics_path.parent.mkdir(parents=True)
    metrics.to_csv(metrics_path, index=False)

    result = run_spatial_derived_outputs_workflow(
        metrics_path,
        cfg=config_path,
        outputs=("pattern_similarity_station_anomalies",),
        overwrite=True,
        verbose=True,
    )

    assert not result.failures
    assert result.rows["pattern_similarity_station_anomalies"] > 0
    output = read_table(result.paths["pattern_similarity_station_anomalies"])
    assert "unused_large_blob" not in output.columns


def test_spatial_statistics_config_wrappers_return_json_ready_payloads(tmp_path: Path) -> None:
    """Notebook Step 4 helpers should run from a config path and summarize outputs."""

    clear_active_config()
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  tables: outputs/tables
spatial:
  metric: C5
  value_column: log2_residual
  min_stations_per_event: 3
  min_events_per_station: 2
  moran_neighbors: 2
  moran_permutations: 3
  cluster_min_k: 2
  cluster_max_k: 3
  pca_components: 2
  geology_min_stations_per_group: 1
  geology_bootstrap_samples: 3
  block_size_km: 5
  block_min_block_stations: 1
  block_max_folds: 2
  pattern_metric: C5
  pattern_passband: 1-2s
  pattern_component: Z
  pattern_model: example_model
""",
        encoding="utf-8",
    )
    metrics = normalize_metrics_table(_toy_metrics_table(), default_model="example_model")
    metrics_path = tmp_path / "outputs" / "tables" / "metrics_long.parquet"
    metrics_path.parent.mkdir(parents=True)
    write_table(metrics, metrics_path)
    station_path = tmp_path / "outputs" / "tables" / "prepared_stations.csv"
    station_metadata = pd.DataFrame(
        {
            "station": metrics["station"].drop_duplicates().tolist(),
            "mapped_region_type": (["Basin", "Mountains"] * 8)[: metrics["station"].nunique()],
        }
    )
    write_table(station_metadata, station_path)

    summary = run_spatial_statistics_workflow_from_config(config_path=config_path, verbose=True)

    assert summary["metrics"] == ["C5"]
    assert summary["failure_count"] == 0
    assert summary["rows"]["metric_field"] > 0
    assert Path(summary["paths"]["metric_field"]) == tmp_path / "outputs" / "tables" / "metric_field.parquet"
    assert summary["output_paths"]["metric_field"] == summary["paths"]["metric_field"]
    assert Path(summary["paths"]["station_bias"]).exists()

    metric_field = pd.read_parquet(summary["paths"]["metric_field"])
    pattern_metrics = metric_field[["station", "metric", "band", "component", "model", "field_value"]].copy()
    pattern_metrics.rename(columns={"band": "passband"}, inplace=True)
    pattern_metrics["value_syn"] = 1.0
    pattern_metrics["value_obs"] = np.power(2.0, pd.to_numeric(pattern_metrics["field_value"], errors="coerce"))
    pattern_metrics_path = tmp_path / "outputs" / "tables" / "pattern_metrics.parquet"
    write_table(pattern_metrics, pattern_metrics_path)

    derived = run_spatial_derived_outputs_workflow_from_config(
        config_path=config_path,
        metrics=pattern_metrics_path,
        overwrite=True,
        verbose=True,
    )

    assert derived["failure_count"] == 0
    assert derived["rows"]["block_holdout_predictions"] > 0
    assert derived["rows"]["redcap_clusters"] > 0
    assert derived["rows"]["pattern_similarity_station_anomalies"] > 0
    assert derived["output_paths"]["block_holdout_predictions"] == derived["paths"]["block_holdout_predictions"]
    assert Path(derived["paths"]["block_holdout_predictions"]).exists()


def test_spatial_statistics_config_wrapper_uses_configured_input_tables(tmp_path: Path) -> None:
    """Config-backed spatial helpers should resolve configured spatial input tables."""

    clear_active_config()
    metrics = normalize_metrics_table(_toy_metrics_table(), default_model="example_model")
    metrics_path = tmp_path / "inputs" / "metric_snapshot.parquet"
    metrics_path.parent.mkdir(parents=True)
    write_table(metrics, metrics_path)
    station_metadata = pd.DataFrame(
        {
            "station": metrics["station"].drop_duplicates().tolist(),
            "mapped_region_type": (["Basin", "Mountains"] * 8)[: metrics["station"].nunique()],
        }
    )
    site_path = tmp_path / "inputs" / "site_metadata.csv"
    write_table(station_metadata, site_path)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
paths:
  metric_figure_snapshot: {metrics_path}
  site_metadata: {site_path}
outputs:
  tables: outputs/tables
spatial:
  metrics_table: paths.metric_figure_snapshot
  station_metadata_table: paths.site_metadata
  metric: C5
  value_column: log2_residual
  min_stations_per_event: 3
  min_events_per_station: 2
  moran_neighbors: 2
  moran_permutations: 3
  cluster_min_k: 2
  cluster_max_k: 3
  pca_components: 2
  geology_min_stations_per_group: 1
  geology_bootstrap_samples: 3
""",
        encoding="utf-8",
    )

    summary = run_spatial_statistics_workflow_from_config(config_path=config_path, verbose=True)

    assert summary["failure_count"] == 0
    assert summary["metrics"] == ["C5"]
    assert Path(summary["paths"]["metric_field"]).exists()


def test_spatial_statistics_workflow_resumes_metric_checkpoints(tmp_path: Path, monkeypatch) -> None:
    """Path-backed spatial workflows should rebuild final outputs from completed checkpoints."""

    clear_active_config()
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  tables: outputs/tables
spatial:
  metric: C5
  value_column: log2_residual
  min_stations_per_event: 3
  min_events_per_station: 2
  moran_neighbors: 2
  moran_permutations: 3
  cluster_min_k: 2
  cluster_max_k: 3
  pca_components: 2
  geology_min_stations_per_group: 1
  geology_bootstrap_samples: 3
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    metrics = normalize_metrics_table(_toy_metrics_table(), default_model="example")
    metrics_path = tmp_path / "metrics.parquet"
    write_table(metrics, metrics_path)
    station_metadata = pd.DataFrame(
        {
            "station": metrics["station"].drop_duplicates().tolist(),
            "mapped_region_type": (["Basin", "Mountains"] * 8)[: metrics["station"].nunique()],
        }
    )
    checkpoint_dir = tmp_path / "spatial_checkpoints"

    first = run_spatial_statistics_workflow(
        metrics_path,
        cfg=cfg,
        metric=("C5",),
        station_metadata=station_metadata,
        checkpoint_dir=checkpoint_dir,
    )
    assert first.paths["metric_field"].exists()
    assert any(checkpoint_dir.glob("*/C5-*/*.parquet"))

    for path in first.paths.values():
        path.unlink(missing_ok=True)

    def _fail_build_metric_field(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise AssertionError("checkpointed run should not recompute metric fields")

    monkeypatch.setattr("spatial_vtk.spatial.calculate.workflow.build_metric_field", _fail_build_metric_field)
    resumed = run_spatial_statistics_workflow(
        metrics_path,
        cfg=cfg,
        metric=("C5",),
        station_metadata=station_metadata,
        checkpoint_dir=checkpoint_dir,
    )

    assert resumed.metrics == ("C5",)
    assert not resumed.tables["metric_field"].empty
    assert resumed.paths["metric_field"].exists()
    assert resumed.paths["station_bias"].exists()


def test_spatial_figure_context_respects_config_and_projects_large_tables(tmp_path: Path) -> None:
    """Spatial figure context should use explicit config paths and avoid unused columns."""

    clear_active_config()
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  tables: outputs/tables
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    metric_field_path = resolve_output_path("metric_field", kind="table", cfg=cfg, create_parent=True)
    event_centered_path = resolve_output_path("event_centered_residuals", kind="table", cfg=cfg, create_parent=True)
    station_path = resolve_output_path("prepared_stations", kind="table", cfg=cfg, create_parent=True)

    metric_field = pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "station": ["STA", "STA"],
            "sta_lon": [-118.0, -118.0],
            "sta_lat": [34.0, 34.0],
            "metric": ["PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec"],
            "component": ["R", "R"],
            "model": ["m1", "m1"],
            "field_value": [0.2, 0.4],
            "unused_large_payload": ["x" * 64, "y" * 64],
        }
    )
    event_centered = metric_field.rename(columns={"field_value": "field_centered"}).assign(
        unused_event_payload=["a" * 64, "b" * 64],
    )
    stations = pd.DataFrame({"station": ["STA"], "lat": [34.0], "lon": [-118.0]})
    write_table(metric_field, metric_field_path)
    write_table(event_centered, event_centered_path)
    write_table(stations, station_path)

    context = SpatialFigureContext.from_config(
        figure_dir=tmp_path / "figures",
        make_figures=False,
        cfg=cfg,
        sample_rows=0,
    )

    assert context.paths["metric_field"] == tmp_path / "outputs" / "tables" / "metric_field.parquet"
    status = context.status_frame().set_index("name")
    assert status.loc["metric_field", "resolved_path"] == str(metric_field_path)
    assert status.loc["metric_field", "path"] == status.loc["metric_field", "resolved_path"]
    assert context.metric_field is not None
    assert context.event_context.metrics_for_figures is not None
    assert "unused_large_payload" not in context.metric_field.columns
    assert "unused_event_payload" not in context.event_context.metrics_for_figures.columns
    assert {"event_id", "station", "metric", "band", "component", "model", "field_value"} <= set(
        context.metric_field.columns
    )
    assert {"event_id", "station", "field_centered"} <= set(context.event_context.metrics_for_figures.columns)
    assert context.metric_value_col == "field_value"
    assert context.event_value_col == "field_centered"
    assert context.site_metadata is not None
    assert context.site_metadata["station"].tolist() == ["STA"]


def test_prepare_spatial_figure_context_from_notebook_settings_delegates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Notebook spatial figures should pass settings through package code."""

    import spatial_vtk.spatial.plot.large_run as large_run_module

    calls: dict[str, object] = {}

    class Settings:
        figure_dir = tmp_path / "figures"

        def context_kwargs(self, *, include_station_aggregation: bool = False) -> dict[str, object]:
            calls["include_station_aggregation"] = include_station_aggregation
            return {
                "make_figures": True,
                "default_model": "from-settings",
                "station_aggregation": "median",
            }

    def _fake_prepare_spatial_figure_context(**kwargs):  # noqa: ANN003, ANN202
        calls["kwargs"] = kwargs
        return "spatial-context"

    monkeypatch.setattr(
        large_run_module,
        "prepare_spatial_figure_context",
        _fake_prepare_spatial_figure_context,
    )

    result = prepare_spatial_figure_context_from_notebook_settings(
        Settings(),
        overwrite=True,
        include_station_aggregation=True,
        default_model="override-model",
    )

    assert result == "spatial-context"
    assert calls["include_station_aggregation"] is True
    assert calls["kwargs"] == {
        "figure_dir": tmp_path / "figures",
        "overwrite": True,
        "make_figures": True,
        "default_model": "override-model",
        "station_aggregation": "median",
    }


def test_write_large_run_spatial_figure_suite_from_notebook_settings_delegates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Full Step 4 figure suite helper should keep plotting orchestration out of notebooks."""

    import spatial_vtk.spatial.plot.large_run as large_run_module

    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    class Settings:
        figure_dir = tmp_path / "figures"
        make_figures = True
        pca_mode = "PC2"

        def context_kwargs(self, *, include_station_aggregation: bool = False) -> dict[str, object]:
            assert include_station_aggregation is True
            return {
                "make_figures": True,
                "default_model": "m1",
                "station_aggregation": "mean",
            }

        def plot_selection_kwargs(self, **kwargs: object) -> dict[str, object]:
            out: dict[str, object] = {
                "passband": "1-2 sec",
                "components": ["Z"],
                "model": "m1",
                "showfig": False,
            }
            out.update(kwargs)
            return out

    class FakeContext:
        metric_value_col = "log2_residual"
        event_value_col = "event_centered_residual"

        def __init__(self, figure_dir: Path) -> None:
            self.figure_dir = figure_dir

        def _record(self, name: str, *args: object, **kwargs: object) -> list[Path]:
            calls.append((name, args, kwargs))
            return [self.figure_dir / f"{name}.png"]

        def write_station_metric_maps(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("station_metric_maps", *args, **kwargs)

        def write_residual_grid_maps(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("residual_grid_maps", *args, **kwargs)

        def write_metric_by_model_maps(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("metric_by_model_maps", *args, **kwargs)

        def write_event_residual_maps(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("event_residual_maps", *args, **kwargs)

        def write_event_centered_azimuthal_plots(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("event_centered_azimuthal_plots", *args, **kwargs)

        def write_event_centered_polar_plots(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("event_centered_polar_plots", *args, **kwargs)

        def write_pca_summary_plots(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("pca_summary_plots", *args, **kwargs)

        def write_overview_plots(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("overview_plots", *args, **kwargs)

    fake_context = FakeContext(tmp_path / "figures")

    monkeypatch.setattr(
        large_run_module,
        "prepare_spatial_figure_context_from_notebook_settings",
        lambda *args, **kwargs: fake_context,
    )

    def _dummy_plot(*_args: object, **_kwargs: object) -> None:
        return None

    result = write_large_run_spatial_figure_suite_from_notebook_settings(
        Settings(),
        overwrite=True,
        station_metric_map_func=_dummy_plot,
        station_metric_map_by_period_func=_dummy_plot,
        residual_grid_func=_dummy_plot,
        metric_by_model_map_func=_dummy_plot,
        event_residual_map_func=_dummy_plot,
        azimuthal_residuals_func=_dummy_plot,
        polar_residuals_func=_dummy_plot,
        pca_summary_func=_dummy_plot,
    )

    assert result.context is fake_context
    assert [call[0] for call in calls] == [
        "station_metric_maps",
        "residual_grid_maps",
        "metric_by_model_maps",
        "event_residual_maps",
        "event_centered_azimuthal_plots",
        "event_centered_polar_plots",
        "pca_summary_plots",
        "overview_plots",
    ]
    assert calls[0][2]["value_col"] == "log2_residual"
    assert calls[2][2]["model"] is None
    assert calls[4][2]["value_col"] == "event_centered_residual"
    assert calls[4][2]["include_robust_axis_percentile"] is True
    assert calls[6][2]["mode"] == "PC2"
    status = result.status_frame()
    assert {"name", "artifact_label", "resolved_path", "path", "exists"} <= set(status.columns)
    assert status["artifact"].tolist() == [call[0] for call in calls]
    assert status["status"].tolist() == ["written"] * 8
    assert status["figure_count"].tolist() == [1] * 8
    assert status["existing_figure_count"].tolist() == [0] * 8
    assert status["figure_paths"].tolist() == [[str(fake_context.figure_dir / f"{call[0]}.png")] for call in calls]
    assert status["first_figure_path"].tolist() == [str(fake_context.figure_dir / f"{call[0]}.png") for call in calls]
    assert status["path"].tolist() == status["first_figure_path"].tolist()
    assert status["exists"].tolist() == [False] * 8


def test_write_large_run_spatial_summary_figures_from_outputs(tmp_path: Path) -> None:
    """Compact Step 4 figure helper should own loading and output routing."""

    station_bias_path = tmp_path / "station_bias.parquet"
    figure_path = tmp_path / "station_bias.png"
    station_bias = pd.DataFrame(
        {
            "station": ["STA"],
            "lat": [34.0],
            "lon": [-118.0],
            "mean_centered": [0.2],
        }
    )
    calls: dict[str, object] = {}

    class Outputs:
        def __init__(self) -> None:
            self.station_bias_path = station_bias_path
            self.station_bias_figure_path = figure_path

        def load_table(self, name: str, *, cfg=None) -> pd.DataFrame:  # noqa: ANN001
            calls["load_name"] = name
            calls["cfg"] = cfg
            return station_bias

    class Settings:
        def render_gate(self, paths, *, missing_message: str):  # noqa: ANN001, ANN202
            calls["gate_paths"] = paths
            return type("Gate", (), {"ready": True, "figures_enabled": True, "message": missing_message})()

        def plot_kwargs(self) -> dict[str, object]:
            return {"showfig": False, "write_sidecar": True}

    def _fake_plot(frame: pd.DataFrame, *, outpath: Path, savefig: bool, **kwargs) -> None:  # noqa: ANN003
        calls["plot_rows"] = len(frame)
        calls["outpath"] = outpath
        calls["savefig"] = savefig
        calls["plot_kwargs"] = kwargs
        Path(outpath).write_text("figure", encoding="utf-8")

    station_bias_path.write_text("ready", encoding="utf-8")
    result = write_large_run_spatial_summary_figures_from_outputs(
        Outputs(),
        Settings(),
        cfg="config",
        plot_station_bias_map_func=_fake_plot,
    )

    assert result.status == "wrote"
    assert result.row_count == 1
    assert result.station_bias_path == station_bias_path
    assert result.station_bias_figure_path == figure_path
    assert calls["gate_paths"] == [station_bias_path]
    assert calls["load_name"] == "station_bias"
    assert calls["cfg"] == "config"
    assert calls["plot_rows"] == 1
    assert calls["outpath"] == figure_path
    assert calls["savefig"] is True
    assert calls["plot_kwargs"] == {"showfig": False, "write_sidecar": True}
    assert figure_path.read_text(encoding="utf-8") == "figure"
    assert result.status_frame().loc[0, "status"] == "wrote"


def test_write_large_run_spatial_summary_figures_skips_existing(tmp_path: Path) -> None:
    """Compact Step 4 figure helper should not rewrite current figures by default."""

    station_bias_path = tmp_path / "station_bias.parquet"
    figure_path = tmp_path / "station_bias.png"
    station_bias_path.write_text("ready", encoding="utf-8")
    figure_path.write_text("old", encoding="utf-8")

    class Outputs:
        def __init__(self) -> None:
            self.station_bias_path = station_bias_path
            self.station_bias_figure_path = figure_path

        def load_table(self, name: str, *, cfg=None) -> pd.DataFrame:  # noqa: ANN001
            raise AssertionError("existing figure should skip table loading")

    class Settings:
        def render_gate(self, paths, *, missing_message: str):  # noqa: ANN001, ANN202
            return type("Gate", (), {"ready": True, "figures_enabled": True, "message": missing_message})()

    result = write_large_run_spatial_summary_figures_from_outputs(Outputs(), Settings())

    assert result.status == "exists"
    assert result.station_bias_figure_path == figure_path
    assert figure_path.read_text(encoding="utf-8") == "old"


def test_write_large_run_spatial_summary_figures_reports_missing_input(tmp_path: Path) -> None:
    """Compact Step 4 figure helper should return a status table for missing inputs."""

    station_bias_path = tmp_path / "missing.parquet"

    class Outputs:
        def __init__(self) -> None:
            self.station_bias_path = station_bias_path
            self.station_bias_figure_path = tmp_path / "station_bias.png"

        def load_table(self, name: str, *, cfg=None) -> pd.DataFrame:  # noqa: ANN001
            raise AssertionError("missing input should skip table loading")

    class Settings:
        def render_gate(self, paths, *, missing_message: str):  # noqa: ANN001, ANN202
            return type("Gate", (), {"ready": False, "figures_enabled": True, "message": missing_message})()

    result = write_large_run_spatial_summary_figures_from_outputs(Outputs(), Settings())

    assert result.status == "missing_input"
    assert result.station_bias_path == station_bias_path
    assert result.row_count == 0
    assert "station_bias table is not ready yet" in result.status_frame().loc[0, "message"]


def test_write_large_run_spatial_summary_figures_reports_missing_output(tmp_path: Path) -> None:
    """Compact Step 4 figure helper should require a configured figure output."""

    station_bias_path = tmp_path / "station_bias.parquet"
    station_bias_path.write_text("ready", encoding="utf-8")

    class Outputs:
        def __init__(self) -> None:
            self.station_bias_path = station_bias_path

        def load_table(self, name: str, *, cfg=None) -> pd.DataFrame:  # noqa: ANN001
            raise AssertionError("missing figure output should skip table loading")

    class Settings:
        def render_gate(self, paths, *, missing_message: str):  # noqa: ANN001, ANN202
            return type("Gate", (), {"ready": True, "figures_enabled": True, "message": missing_message})()

    result = write_large_run_spatial_summary_figures_from_outputs(Outputs(), Settings())

    assert result.status == "missing_output"
    assert result.station_bias_path == station_bias_path
    assert result.station_bias_figure_path is None
    assert "station_bias_figure_path is not configured" in result.message


def test_write_large_run_region_boxplot_from_bounded_table(tmp_path: Path) -> None:
    """Large-run region boxplot helper should replace notebook-local plotting logic."""

    metrics = pd.DataFrame(
        {
            "metric": ["PGA", "PGA", "PGA", "PGA"],
            "band": ["2-3 sec", "2-3 sec", "2-3 sec", "2-3 sec"],
            "component": ["Z", "R", "Z", "R"],
            "model": ["example", "example", "example", "example"],
            "station_region": ["LA_Basin", "LA_Basin", "Mountains", "Mountains"],
            "log2_residual": [0.2, 0.1, -0.2, -0.1],
        }
    )
    metrics_path = tmp_path / "metrics.csv"
    metrics.to_csv(metrics_path, index=False)

    result = write_large_run_region_boxplot(
        metrics_path,
        figure_dir=tmp_path / "figures",
        metric="PGA",
        passband="2-3 sec",
        model="example",
        max_rows=10,
        write_sidecar=True,
        sidecar_rows=2,
        overwrite=True,
        showfig=False,
    )

    assert result.status == "wrote"
    assert result.figure_path is not None
    assert result.figure_path.exists()
    assert result.sidecar_path is not None
    assert result.sidecar_path.exists()
    assert result.figure_path.name == "geojson_region_boxplot__pga__2_3_sec__all_components__example__log2_residual.png"
    assert result.rows == 4
    sidecar_rows = pd.read_csv(result.sidecar_path)
    metadata = json.loads(result.sidecar_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert len(sidecar_rows) == 2
    assert {"station_region", "_plot_value", "dep"} <= set(sidecar_rows.columns)
    assert metadata["source_row_count"] == 4
    assert metadata["written_row_count"] == 2
    assert metadata["sampled"] is True
    assert metadata["category_col"] == "station_region"
    assert metadata["resolved_value_col"] == "log2_residual"
    status = result.status_frame().iloc[0].to_dict()
    assert status["artifact"] == "region_boxplot"
    assert status["status"] == "wrote"
    assert status["row_count"] == 4
    assert status["figure_path"] == str(result.figure_path)
    assert bool(status["figure_exists"]) is True
    assert status["sidecar_path"] == str(result.sidecar_path)
    assert bool(status["sidecar_exists"]) is True

    existing = write_large_run_region_boxplot(
        metrics_path,
        figure_dir=tmp_path / "figures",
        metric="PGA",
        passband="2-3 sec",
        model="example",
        max_rows=10,
        write_sidecar=True,
        sidecar_rows=None,
        overwrite=False,
        showfig=False,
    )
    assert existing.status == "exists"
    assert existing.sidecar_path == result.sidecar_path
    existing_rows = pd.read_csv(existing.sidecar_path)
    existing_metadata = json.loads(existing.sidecar_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert len(existing_rows) == 4
    assert existing_metadata["sampled"] is False


def test_write_large_run_region_boxplot_from_outputs_uses_metric_fallback(tmp_path: Path) -> None:
    """Region boxplot wrapper should select the first available group metric table."""

    metrics = pd.DataFrame(
        {
            "metric": ["PGA", "PGA"],
            "band": ["2-3 sec", "2-3 sec"],
            "component": ["Z", "R"],
            "model": ["example", "example"],
            "station_region": ["LA_Basin", "Mountains"],
            "log2_residual": [0.2, -0.2],
        }
    )
    metrics_long = tmp_path / "metrics_long.csv"
    metrics.to_csv(metrics_long, index=False)
    outputs = OutputGroup(
        name="step_06_plotting",
        paths={
            "metrics_enriched_path": tmp_path / "missing_metrics_enriched.parquet",
            "metrics_long_path": metrics_long,
        },
    )

    result = write_large_run_region_boxplot_from_outputs(
        outputs,
        figure_dir=tmp_path / "figures",
        metric="PGA",
        passband="2-3 sec",
        model="example",
        max_rows=10,
        output_prefix="fallback_region_boxplot",
        overwrite=True,
        showfig=False,
    )

    assert result.status == "wrote"
    assert result.figure_path is not None
    assert result.figure_path.exists()
    assert result.figure_path.name.startswith("fallback_region_boxplot__pga__2_3_sec")


def test_write_large_run_region_boxplot_from_notebook_settings_disabled(tmp_path: Path, monkeypatch) -> None:
    """Step 6 region-boxplot wrapper should report disabled figures without reading data."""

    import spatial_vtk.spatial.plot.large_run as large_run_plot

    def _unexpected_call(*_args, **_kwargs):
        raise AssertionError("disabled region boxplot should not call the output writer")

    monkeypatch.setattr(large_run_plot, "write_large_run_region_boxplot_from_outputs", _unexpected_call)

    class Settings:
        figure_dir = tmp_path / "figures"
        metric = "PGA"
        passband = "2-3 sec"
        component = None
        model = None
        value_col = "log2_residual"
        compare_to = None
        sample_rows = 100
        showfig = False

        class sidecars:
            @staticmethod
            def kwargs() -> dict[str, object]:
                return {"write_sidecar": True}

        def render_gate(self, paths, *, disabled_message: str):  # noqa: ANN001, ANN202
            assert paths == []
            return type(
                "Gate",
                (),
                {
                    "ready": False,
                    "figures_enabled": False,
                    "message": disabled_message,
                },
            )()

    result = write_large_run_region_boxplot_from_notebook_settings(
        OutputGroup(name="step_06_plotting", paths={}),
        Settings(),
    )

    assert result.status == "disabled"
    assert result.rows == 0
    assert result.figure_path is None
    assert "SVTK_MAKE_FIGURES=1" in result.message


def test_write_large_run_region_boxplot_from_notebook_settings_delegates_options(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Step 6 region-boxplot wrapper should translate notebook settings once."""

    import spatial_vtk.spatial.plot.large_run as large_run_plot

    outputs = OutputGroup(name="step_06_plotting", paths={"metrics_long_path": tmp_path / "metrics.csv"})
    seen: dict[str, object] = {}

    def _fake_writer(output_group, **kwargs):
        seen["output_group"] = output_group
        seen["kwargs"] = kwargs
        return RegionBoxplotResult(
            tmp_path / "figures" / "boxplot.png",
            tmp_path / "figures" / "sidecars" / "boxplot.csv",
            12,
            "wrote",
            "wrote region boxplot",
        )

    monkeypatch.setattr(large_run_plot, "write_large_run_region_boxplot_from_outputs", _fake_writer)

    class Settings:
        figure_dir = tmp_path / "figures"
        metric = "PGV"
        passband = "1-2 sec"
        component = "R"
        model = "cvmsi"
        value_col = "log2_residual"
        compare_to = "LA Basin"
        sample_rows = 250
        showfig = True

        class sidecars:
            @staticmethod
            def kwargs() -> dict[str, object]:
                return {
                    "write_sidecar": True,
                    "sidecar_rows": 50,
                    "sidecar_dir": tmp_path / "sidecars",
                }

        def render_gate(self, paths, *, disabled_message: str):  # noqa: ANN001, ANN202
            assert paths == []
            assert "SVTK_MAKE_FIGURES=1" in disabled_message
            return type(
                "Gate",
                (),
                {
                    "ready": True,
                    "figures_enabled": True,
                    "message": "ready",
                },
            )()

    result = write_large_run_region_boxplot_from_notebook_settings(
        outputs,
        Settings(),
        output_prefix="custom_region_boxplot",
        geojson_path=tmp_path / "regions.geojson",
        annotate_if_missing=True,
        overwrite=True,
    )

    assert result.status == "wrote"
    status = result.status_frame().iloc[0]
    assert status["name"] == "region_boxplot"
    assert status["path"] == str(tmp_path / "figures" / "boxplot.png")
    assert bool(status["exists"]) is False
    assert seen["output_group"] is outputs
    kwargs = seen["kwargs"]
    assert kwargs["figure_dir"] == tmp_path / "figures"
    assert kwargs["geojson_path"] == tmp_path / "regions.geojson"
    assert kwargs["metric"] == "PGV"
    assert kwargs["passband"] == "1-2 sec"
    assert kwargs["component"] == "R"
    assert kwargs["model"] == "cvmsi"
    assert kwargs["value_col"] == "log2_residual"
    assert kwargs["compare_to"] == "LA Basin"
    assert kwargs["max_rows"] == 250
    assert kwargs["output_prefix"] == "custom_region_boxplot"
    assert kwargs["write_sidecar"] is True
    assert kwargs["sidecar_rows"] == 50
    assert kwargs["sidecar_dir"] == tmp_path / "sidecars"
    assert kwargs["annotate_if_missing"] is True
    assert kwargs["overwrite"] is True
    assert kwargs["showfig"] is True


def test_write_large_run_geojson_region_figures_from_outputs_orchestrates_notebook_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Step 5 region figure orchestration should live in package code."""

    stations = pd.DataFrame({"station": ["STA"], "sta_lon": [-118.0], "sta_lat": [34.0]})
    events = pd.DataFrame({"event_id": ["e1"], "event_lon": [-118.1], "event_lat": [34.1]})
    metrics = pd.DataFrame(
        {
            "metric": ["PGA", "PGA"],
            "band": ["2-3 sec", "2-3 sec"],
            "component": ["Z", "R"],
            "model": ["example", "example"],
            "station_region": ["LA_Basin", "Mountains"],
            "log2_residual": [0.2, -0.2],
        }
    )
    corridors = pd.DataFrame({"corridor_id": ["c1"], "corridor_geometry": ["POLYGON ((-118 34, -117.9 34, -117.9 34.1, -118 34.1, -118 34))"]})
    stations_path = tmp_path / "prepared_stations.csv"
    events_path = tmp_path / "prepared_events.csv"
    metrics_path = tmp_path / "metrics_long.csv"
    corridors_path = tmp_path / "corridors.csv"
    stations.to_csv(stations_path, index=False)
    events.to_csv(events_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    corridors.to_csv(corridors_path, index=False)

    ingest_outputs = OutputGroup(
        name="step_01_ingest",
        paths={
            "prepared_stations_path": stations_path,
            "prepared_events_path": events_path,
        },
    )
    outputs = OutputGroup(
        name="step_05_geojson",
        paths={
            "metrics_long_path": metrics_path,
            "metrics_enriched_path": tmp_path / "missing_metrics_enriched.parquet",
            "corridors_path": corridors_path,
            "geojson_polygons_map_path": tmp_path / "figures" / "regions.png",
            "corridor_map_path": tmp_path / "figures" / "corridors.png",
        },
    )
    calls: list[tuple[str, Path, bool]] = []

    def _fake_geojson_plot(_geojson_path, *, output_path, add_basemap, **_kwargs):
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("geojson", encoding="utf-8")
        calls.append(("geojson", output, bool(add_basemap)))

    def _fake_corridor_plot(_corridors, output_path=None, *, add_basemap, **_kwargs):
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("corridor", encoding="utf-8")
        calls.append(("corridor", output, bool(add_basemap)))

    import spatial_vtk.spatial.map as spatial_map

    monkeypatch.setattr(spatial_map, "plot_geojson_polygons_map", _fake_geojson_plot)
    monkeypatch.setattr(spatial_map, "plot_corridor_map", _fake_corridor_plot)

    result = write_large_run_geojson_region_figures_from_outputs(
        outputs,
        ingest_outputs,
        geojson_path=tmp_path / "regions.geojson",
        figure_dir=tmp_path / "figures",
        metric="PGA",
        passband="2-3 sec",
        model="example",
        max_rows=10,
        corridor_add_basemap=True,
        write_sidecar=True,
        sidecar_rows=None,
        overwrite=True,
        showfig=False,
    )

    assert result.geojson_status == "wrote"
    assert result.corridor_status == "wrote"
    assert result.geojson_overview_path == outputs.geojson_polygons_map_path
    assert result.corridor_map_path == outputs.corridor_map_path
    assert result.boxplot_result.status == "wrote"
    assert result.boxplot_result.figure_path is not None
    assert result.boxplot_result.figure_path.exists()
    assert ("geojson", outputs.geojson_polygons_map_path, True) in calls
    assert ("corridor", outputs.corridor_map_path, True) in calls
    status = result.status_frame()
    assert status["artifact"].tolist() == ["geojson_overview", "corridor_map", "region_boxplot"]
    assert set(status["status"]) == {"wrote"}
    assert "resolved_path" in status.columns
    assert status.loc[status["artifact"].eq("geojson_overview"), "resolved_path"].iloc[0] == str(
        outputs.geojson_polygons_map_path
    )
    assert status.loc[status["artifact"].eq("geojson_overview"), "path"].iloc[0] == status.loc[
        status["artifact"].eq("geojson_overview"), "resolved_path"
    ].iloc[0]
    assert status["exists"].tolist() == [True, True, True]
    assert bool(status.loc[status["artifact"].eq("region_boxplot"), "sidecar_exists"].iloc[0]) is True


def test_write_large_run_geojson_region_figures_from_notebook_settings_disabled(tmp_path: Path, monkeypatch) -> None:
    """Step 5 notebook wrapper should report disabled figures without loading data."""

    import spatial_vtk.spatial.plot.large_run as large_run_plot

    outputs = OutputGroup(name="step_05_geojson", paths={})
    ingest_outputs = OutputGroup(name="step_01_ingest", paths={})

    class Settings:
        figure_dir = tmp_path / "figures"
        metric = "PGA"
        passband = "2-3 sec"
        component = None
        model = None
        value_col = "log2_residual"
        compare_to = None
        sample_rows = 100
        add_basemap = False
        showfig = False

        class sidecars:
            @staticmethod
            def kwargs() -> dict[str, object]:
                return {"write_sidecar": False}

        def render_gate(self, paths, *, missing_message: str):  # noqa: ANN001, ANN202
            return type("Gate", (), {"ready": False, "figures_enabled": False, "message": "figures disabled"})()

    def fail_if_called(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise AssertionError("disabled figure block should not load GeoJSON figure inputs")

    monkeypatch.setattr(large_run_plot, "write_large_run_geojson_region_figures_from_outputs", fail_if_called)

    result = write_large_run_geojson_region_figures_from_notebook_settings(
        outputs,
        ingest_outputs,
        Settings(),
        geojson_path=tmp_path / "regions.geojson",
    )

    assert result.geojson_status == "disabled"
    assert result.corridor_status == "disabled"
    assert result.boxplot_result.status == "disabled"
    status = result.status_frame()
    assert status["status"].tolist() == ["disabled", "disabled", "disabled"]
    assert status["resolved_path"].isna().all()
    assert status["exists"].tolist() == [False, False, False]


def test_write_large_run_geojson_region_figures_from_notebook_settings_delegates_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Step 5 notebook wrapper should translate figure settings into the lower-level helper."""

    import spatial_vtk.spatial.plot.large_run as large_run_plot

    stations_path = tmp_path / "prepared_stations.csv"
    events_path = tmp_path / "prepared_events.csv"
    geojson_path = tmp_path / "regions.geojson"
    stations_path.write_text("ready", encoding="utf-8")
    events_path.write_text("ready", encoding="utf-8")
    geojson_path.write_text("{}", encoding="utf-8")
    outputs = OutputGroup(name="step_05_geojson", paths={})
    ingest_outputs = OutputGroup(
        name="step_01_ingest",
        paths={
            "prepared_stations_path": stations_path,
            "prepared_events_path": events_path,
        },
    )
    calls: dict[str, object] = {}

    class Settings:
        figure_dir = tmp_path / "figures"
        metric = "PGV"
        passband = "1-2 sec"
        component = "Z"
        model = "example"
        value_col = "log2_residual"
        compare_to = "LA Basin"
        sample_rows = 123
        add_basemap = True
        showfig = False

        class sidecars:
            @staticmethod
            def kwargs() -> dict[str, object]:
                return {"write_sidecar": True, "sidecar_rows": 5}

        def render_gate(self, paths, *, missing_message: str):  # noqa: ANN001, ANN202
            calls["gate_paths"] = list(paths)
            return type("Gate", (), {"ready": True, "figures_enabled": True, "message": "ready"})()

    def fake_write(outputs_arg, ingest_outputs_arg, **kwargs):  # noqa: ANN001, ANN202
        calls["outputs"] = outputs_arg
        calls["ingest_outputs"] = ingest_outputs_arg
        calls["kwargs"] = kwargs
        return large_run_plot.RegionFigureResult(
            geojson_overview_path=tmp_path / "figures" / "regions.png",
            corridor_map_path=None,
            boxplot_result=large_run_plot.RegionBoxplotResult(None, None, 0, "wrote", "ok"),
            geojson_status="wrote",
            corridor_status="missing_input",
            messages=("geojson_overview: ok", "corridor_map: missing", "region_boxplot: ok"),
        )

    monkeypatch.setattr(large_run_plot, "write_large_run_geojson_region_figures_from_outputs", fake_write)

    result = write_large_run_geojson_region_figures_from_notebook_settings(
        outputs,
        ingest_outputs,
        Settings(),
        geojson_path=geojson_path,
        cfg=None,
        overwrite=True,
    )

    assert result.geojson_status == "wrote"
    status = result.status_frame().set_index("name")
    assert {"artifact_label", "resolved_path", "path", "exists"} <= set(status.columns)
    assert "geojson_overview" in status.index
    assert "region_boxplot" in status.index
    assert calls["gate_paths"] == [stations_path, events_path, geojson_path]
    assert calls["outputs"] is outputs
    assert calls["ingest_outputs"] is ingest_outputs
    kwargs = calls["kwargs"]
    assert kwargs["geojson_path"] == geojson_path
    assert kwargs["figure_dir"] == Settings.figure_dir
    assert kwargs["metric"] == "PGV"
    assert kwargs["passband"] == "1-2 sec"
    assert kwargs["component"] == "Z"
    assert kwargs["model"] == "example"
    assert kwargs["compare_to"] == "LA Basin"
    assert kwargs["max_rows"] == 123
    assert kwargs["corridor_add_basemap"] is True
    assert kwargs["write_sidecar"] is True
    assert kwargs["sidecar_rows"] == 5
    assert kwargs["overwrite"] is True


def test_write_figure_row_sidecar_records_plot_and_source_rows(tmp_path: Path) -> None:
    """Shared figure sidecars should capture plotted rows and optional source rows."""

    figure_path = tmp_path / "figures" / "station_map.png"
    plot_rows = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3"],
            "station": ["STA", "STB", "STC"],
            "metric": ["PGA", "PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec"],
            "log2_residual": [0.1, 0.2, -0.1],
        }
    )
    source_rows = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3", "e4"],
            "station_id": ["STA", "STA", "STB", "STC"],
            "metric": ["PGA", "PGA", "PGA", "PGA"],
            "passband": ["1-2 sec", "1-2 sec", "2-3 sec", "2-3 sec"],
            "model": ["m1", "m1", "m1", "m2"],
        }
    )

    result = write_figure_row_sidecar(
        figure_path,
        plot_rows,
        sidecar_rows=2,
        source_rows=source_rows,
        metadata={
            "value_col": "log2_residual",
            "selection": ("PGA", "1-2 sec"),
            "numpy_count": np.int64(4),
            "numpy_value": np.float64(1.25),
            "nonfinite_value": np.float64(np.nan),
            "missing_value": pd.NA,
            "created_at": pd.Timestamp("2026-06-21T12:30:00"),
            "label_set": {"station", "event"},
        },
    )

    assert result is not None
    assert result.figure_path == figure_path
    assert result.sidecar_path == tmp_path / "figures" / "sidecars" / "station_map.csv"
    assert result.source_sidecar_path == tmp_path / "figures" / "sidecars" / "station_map.source.csv"
    assert result.metadata_path.exists()
    result_status = result.status_frame()
    assert result_status["name"].tolist() == ["figure_sidecar_path"]
    assert result_status["figure_path"].tolist() == [str(figure_path)]
    assert result_status["sidecar_path"].tolist() == [str(result.sidecar_path)]
    assert result_status["metadata_path"].tolist() == [str(result.metadata_path)]
    assert result_status["source_sidecar_path"].tolist() == [str(result.source_sidecar_path)]
    assert result_status["sidecar_exists"].tolist() == [True]
    assert result_status["metadata_exists"].tolist() == [True]
    assert result_status["source_sidecar_exists"].tolist() == [True]
    written_rows = pd.read_csv(result.sidecar_path)
    written_source_rows = pd.read_csv(result.source_sidecar_path)
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert len(written_rows) == 2
    assert len(written_source_rows) == 2
    assert metadata["plot_row_count"] == 3
    assert metadata["plot_column_count"] == len(plot_rows.columns)
    assert metadata["plot_columns"] == list(plot_rows.columns)
    assert metadata["written_row_count"] == 2
    assert metadata["source_row_count"] == 4
    assert metadata["source_column_count"] == len(source_rows.columns)
    assert metadata["source_columns"] == list(source_rows.columns)
    assert metadata["source_written_row_count"] == 2
    assert metadata["source_rows_provided"] is True
    assert metadata["source_sidecar_written"] is True
    assert metadata["sidecar_row_limit"] == 2
    assert metadata["sidecar_row_policy"] == "deterministic_sample"
    assert metadata["plot_sidecar_exact"] is False
    assert metadata["source_sidecar_exact"] is False
    assert metadata["sidecar_random_state"] == 42
    assert metadata["plot_rows_role"] == "figure_plot_rows"
    assert metadata["source_rows_role"] == "figure_source_rows"
    assert result_status["plot_row_count"].tolist() == [metadata["plot_row_count"]]
    assert result_status["written_row_count"].tolist() == [metadata["written_row_count"]]
    assert result_status["source_row_count"].tolist() == [metadata["source_row_count"]]
    assert result_status["source_written_row_count"].tolist() == [metadata["source_written_row_count"]]
    assert result_status["sidecar_row_policy"].tolist() == [metadata["sidecar_row_policy"]]
    assert result_status["plot_rows_role"].tolist() == [metadata["plot_rows_role"]]
    assert result_status["source_rows_role"].tolist() == [metadata["source_rows_role"]]
    assert metadata["plot_station_count"] == 3
    assert metadata["source_station_count"] == 3
    assert metadata["source_model_count"] == 2
    assert metadata["plot_passband_count"] == 1
    assert metadata["source_passband_count"] == 2
    assert metadata["selection"] == ["PGA", "1-2 sec"]
    assert metadata["numpy_count"] == 4
    assert metadata["numpy_value"] == 1.25
    assert metadata["nonfinite_value"] is None
    assert metadata["missing_value"] is None
    assert metadata["created_at"] == "2026-06-21T12:30:00"
    assert metadata["label_set"] == ["event", "station"]

    assert figure_sidecar_metadata_path(figure_path) == result.metadata_path
    assert figure_sidecar_metadata_path(result.sidecar_path) == result.metadata_path
    assert figure_sidecar_metadata_path(result.source_sidecar_path) == result.metadata_path
    assert read_figure_sidecar_metadata(figure_path)["plot_row_count"] == 3
    assert read_figure_sidecar_metadata(result.sidecar_path)["source_row_count"] == 4
    assert read_figure_sidecar_metadata(result.source_sidecar_path)["source_sidecar_written"] is True

    all_rows_result = write_figure_row_sidecar(
        tmp_path / "figures" / "station_map_all_rows.png",
        plot_rows,
        sidecar_rows=0,
        source_rows=source_rows,
    )
    assert all_rows_result is not None
    all_rows_metadata = json.loads(all_rows_result.metadata_path.read_text(encoding="utf-8"))
    assert all_rows_metadata["sidecar_row_limit"] is None
    assert all_rows_metadata["sidecar_row_policy"] == "all_rows"
    assert all_rows_metadata["plot_sidecar_exact"] is True
    assert all_rows_metadata["source_sidecar_exact"] is True
    assert all_rows_metadata["written_row_count"] == len(plot_rows)
    assert all_rows_metadata["source_written_row_count"] == len(source_rows)

    status = figure_sidecar_status_frame(result.sidecar_path.parent).set_index("figure")
    row = status.loc["station_map.png"]
    assert row["plot_row_count"] == 3
    assert row["written_row_count"] == 2
    assert bool(row["plot_sidecar_exact"]) is False
    assert row["source_row_count"] == 4
    assert row["source_written_row_count"] == 2
    assert bool(row["source_sidecar_exact"]) is False
    assert bool(row["source_sidecar_written"]) is True
    assert row["sidecar_row_policy"] == "deterministic_sample"
    all_row = status.loc["station_map_all_rows.png"]
    assert bool(all_row["plot_sidecar_exact"]) is True
    assert bool(all_row["source_sidecar_exact"]) is True


def test_write_figure_row_sidecar_makes_zero_column_frames_readable(tmp_path: Path) -> None:
    """Empty no-column sidecars should still be valid CSV audit artifacts."""

    result = write_figure_row_sidecar(
        tmp_path / "figures" / "empty_plot.png",
        pd.DataFrame(index=range(0)),
        source_rows=pd.DataFrame(index=range(2)),
    )

    assert result is not None
    written_rows = pd.read_csv(result.sidecar_path)
    written_source_rows = pd.read_csv(result.source_sidecar_path)
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert written_rows.columns.tolist() == ["__svtk_empty_sidecar"]
    assert written_rows.empty
    assert written_source_rows.columns.tolist() == ["__svtk_empty_sidecar"]
    assert len(written_source_rows) == 2
    assert metadata["plot_row_count"] == 0
    assert metadata["plot_column_count"] == 0
    assert metadata["plot_columns"] == []
    assert metadata["written_row_count"] == 0
    assert metadata["source_row_count"] == 2
    assert metadata["source_column_count"] == 0
    assert metadata["source_columns"] == []
    assert metadata["source_written_row_count"] == 2
    assert metadata["source_rows_provided"] is True
    assert metadata["source_sidecar_written"] is True
    assert metadata["sidecar_row_policy"] == "all_rows"
    assert metadata["plot_sidecar_exact"] is True
    assert metadata["source_sidecar_exact"] is True


def test_metric_station_summary_aggregates_all_events_without_coordinate_splitting(tmp_path: Path) -> None:
    """Station maps should summarize all selected event rows into one row per station."""

    rows = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3", "e4", "e1"],
            "station": ["STA", "STA", "STA", "STA", "STB"],
            "sta_lon": [-118.00, -118.02, -118.00, -118.02, -117.9],
            "sta_lat": [34.00, 34.02, 34.00, 34.02, 34.1],
            "metric": ["PGA", "PGA", "PGA", "PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec", "2-3 sec", "2-3 sec", "1-2 sec"],
            "component": ["R", "R", "T", "T", "R"],
            "model": ["m1", "m1", "m1", "m1", "m1"],
            "log2_residual": [1.0, 3.0, np.nan, 5.0, -2.0],
        }
    )
    context = MetricFigureContext.from_frame(
        rows,
        tmp_path,
        make_figures=True,
        sample_rows=0,
        value_col="log2_residual",
        station_aggregation="mean",
        write_sidecars=True,
        sidecar_rows=None,
    )

    summary = context.station_summary_for_map(rows, "log2_residual")
    sta = summary.loc[summary["station"].eq("STA")].iloc[0]

    assert summary["station"].tolist() == ["STA", "STB"]
    assert sta["source_row_count"] == 3
    assert sta["source_event_count"] == 3
    assert sta["input_row_count"] == 4
    assert sta["input_event_count"] == 4
    assert sta["dropped_nonfinite_row_count"] == 1
    assert sta["dropped_nonfinite_event_count"] == 1
    assert sta["source_coordinate_count"] == 2
    assert sta["log2_residual"] == 3.0
    assert np.isclose(sta["sta_lon"], -118.01)
    assert np.isclose(sta["sta_lat"], 34.01)

    metadata = context.figure_sidecar_metadata(summary, source_df=rows)
    assert metadata["aggregation_contract"] == "station_event_rows_to_station_summary"
    assert metadata["plot_rows_role"] == "post_aggregation_station_summary"
    assert metadata["svtk_aggregation_input_row_count"] == 5
    assert metadata["svtk_aggregation_finite_row_count"] == 4
    assert metadata["svtk_aggregation_input_station_count"] == 2
    assert metadata["svtk_aggregation_finite_station_count"] == 2
    assert metadata["svtk_aggregation_input_event_count"] == 4
    assert metadata["svtk_aggregation_finite_event_count"] == 3
    assert metadata["svtk_aggregation_group_columns"] == ["station"]
    assert metadata["svtk_aggregation_collapsed_columns"] == ["metric", "band", "model", "component"]
    assert metadata["svtk_aggregation_collapsed_unique_counts"] == {
        "metric": 1,
        "band": 2,
        "model": 1,
        "component": 2,
    }
    assert metadata["source_rows_role"] == "pre_aggregation_metric_rows"


def test_sampled_station_map_sidecar_filters_source_rows_to_plotted_groups(tmp_path: Path) -> None:
    """Sampled station maps should write source rows only for plotted stations."""

    rows = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3", "e4", "e1"],
            "station": ["STA", "STA", "STA", "STA", "STB"],
            "sta_lon": [-118.00, -118.02, -118.00, -118.02, -117.9],
            "sta_lat": [34.00, 34.02, 34.00, 34.02, 34.1],
            "metric": ["PGA"] * 5,
            "band": ["1-2 sec"] * 5,
            "component": ["R"] * 5,
            "model": ["m1"] * 5,
            "log2_residual": [1.0, 3.0, 2.0, 5.0, -2.0],
        }
    )
    context = MetricFigureContext.from_frame(
        rows,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=1,
        value_col="log2_residual",
        station_aggregation="mean",
        write_sidecars=True,
        sidecar_rows=None,
    )
    item = {"key": "pga", "label": "PGA", "metric": "PGA", "period_s": None, "df": rows}
    station_df = context.station_summary_for_map(rows, "log2_residual")

    def _write_panel(frame: pd.DataFrame, *, output_path, **kwargs) -> None:  # noqa: ANN001, ANN003
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.scatter(frame["sta_lon"], frame["sta_lat"], c=frame["log2_residual"])
        fig.savefig(output_path)
        plt.close(fig)

    output = context.write_metric_plot(
        "station_metric_map",
        item,
        _write_panel,
        df=station_df,
        source_df=rows,
        required=["sta_lon", "sta_lat", "log2_residual"],
        value_col="log2_residual",
    )

    assert output is not None
    sidecar_path = context.sidecar_output_dir / f"{output.stem}.csv"
    source_path = context.sidecar_output_dir / f"{output.stem}.source.csv"
    metadata = json.loads(sidecar_path.with_suffix(".json").read_text(encoding="utf-8"))
    sidecar = pd.read_csv(sidecar_path)
    source_sidecar = pd.read_csv(source_path)
    plotted_stations = set(sidecar["station"].astype(str))

    assert len(sidecar) == 1
    assert set(source_sidecar["station"].astype(str)) == plotted_stations
    assert len(source_sidecar) == len(rows.loc[rows["station"].astype(str).isin(plotted_stations)])
    assert metadata["plot_row_count"] == 1
    assert metadata["source_rows_filter"] == "aggregation_groups_present_in_plot_rows"
    assert metadata["source_row_count"] == len(source_sidecar)
    assert metadata["aggregation_input_row_count"] == len(rows)


def test_metric_figure_context_status_flags_legacy_psa_passband_rows(tmp_path: Path) -> None:
    """Notebook status should expose legacy passband-scoped PSA rows before plotting."""

    rows = pd.DataFrame(
        {
            "event_id": ["e1", "e1", "e2"],
            "station": ["STA", "STA", "STB"],
            "sta_lon": [-118.0, -118.0, -117.9],
            "sta_lat": [34.0, 34.0, 34.1],
            "metric": ["PSA", "PSA", "PSA"],
            "band": ["", "1-2 sec", "2-3 sec"],
            "component": ["R", "R", "R"],
            "model": ["m1", "m1", "m1"],
            "period_s": [1.0, 1.0, 2.0],
            "log2_residual": [0.1, 0.2, 0.3],
        }
    )
    context = MetricFigureContext.from_frame(
        rows,
        tmp_path / "figures",
        make_figures=True,
        value_col="log2_residual",
    )

    spectral = context.spectral_metric_contract_status().set_index("metric")
    assert spectral.loc["PSA", "row_count"] == 3
    assert spectral.loc["PSA", "broadband_row_count"] == 1
    assert spectral.loc["PSA", "legacy_passband_row_count"] == 2
    assert spectral.loc["PSA", "period_count"] == 2
    assert spectral.loc["PSA", "status"] == "mixed_passband_rows"
    assert "Rebuild metric rows" in spectral.loc["PSA", "message"]

    status = context.status_frame().set_index("name")["value"]
    assert status.loc["spectral_contract_status"] == "needs_rebuild"
    assert "passband-scoped spectral records" in status.loc["spectral_contract_message"]
    assert status.loc["psa_metric_rows"] == 3
    assert status.loc["psa_broadband_rows"] == 1
    assert status.loc["psa_legacy_passband_rows"] == 2
    assert status.loc["psa_period_count"] == 2
    status_rows = context.status_frame().set_index("name")
    assert status_rows.loc["figure_dir", "resolved_path"] == str(tmp_path / "figures")
    assert status_rows.loc["figure_dir", "path"] == str(tmp_path / "figures")
    assert bool(status_rows.loc["figure_dir", "exists"]) is True


def test_spatial_figure_context_reports_spectral_contract_by_table(tmp_path: Path) -> None:
    """Spatial figure status should show which Step 4 table has legacy PSA rows."""

    metric_rows = pd.DataFrame(
        {
            "event_id": ["e1", "e1", "e2"],
            "station": ["STA", "STA", "STB"],
            "sta_lon": [-118.0, -118.0, -117.9],
            "sta_lat": [34.0, 34.0, 34.1],
            "metric": ["PSA", "PSA", "PSA"],
            "band": ["", "1-2 sec", "2-3 sec"],
            "component": ["R", "R", "R"],
            "model": ["m1", "m1", "m1"],
            "period_s": [1.0, 1.0, 2.0],
            "log2_residual": [0.1, 0.2, 0.3],
        }
    )
    event_rows = metric_rows.assign(band=["", "", ""])
    context = SpatialFigureContext(
        figure_dir=tmp_path / "figures",
        make_figures=True,
        metric_context=MetricFigureContext.from_frame(
            metric_rows,
            tmp_path / "figures",
            make_figures=True,
            value_col="log2_residual",
        ),
        event_context=MetricFigureContext.from_frame(
            event_rows,
            tmp_path / "figures",
            make_figures=True,
            value_col="log2_residual",
        ),
    )

    spectral = context.spectral_metric_contract_status().set_index(["table", "metric"])
    assert spectral.loc[("metric_field", "PSA"), "status"] == "mixed_passband_rows"
    assert spectral.loc[("metric_field", "PSA"), "legacy_passband_row_count"] == 2
    assert spectral.loc[("event_centered_residuals", "PSA"), "status"] == "ok"
    assert spectral.loc[("event_centered_residuals", "PSA"), "broadband_row_count"] == 3


def test_spatial_figure_suite_result_displays_context_status_frames() -> None:
    """Spatial figure-suite results should own context status display plumbing."""

    class FakeContext:
        def status_frame(self) -> pd.DataFrame:
            return pd.DataFrame([{"frame": "status"}])

        def dimension_summary_frame(self) -> pd.DataFrame:
            return pd.DataFrame([{"frame": "dimension"}])

        def spectral_metric_contract_status(self) -> pd.DataFrame:
            return pd.DataFrame([{"frame": "spectral"}])

    result = SpatialFigureSuiteResult(context=FakeContext(), rows=())
    displayed: list[pd.DataFrame] = []
    frames = result.display_context_status(display=displayed.append)

    assert list(frames) == ["context_status", "dimension_summary", "spectral_metric_contract"]
    assert [frame["frame"].iloc[0] for frame in displayed] == ["status", "dimension", "spectral"]


def test_psa_period_sheet_existing_file_writes_panel_source_sidecars(tmp_path: Path) -> None:
    """Existing PSA sheets should refresh sidecars for every oscillator panel."""

    rows = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e1", "e2", "e1", "e2", "e1", "e2"],
            "station": ["STA", "STA", "STB", "STB", "STA", "STA", "STB", "STB"],
            "sta_lon": [-118.0, -118.0, -117.9, -117.9, -118.0, -118.0, -117.9, -117.9],
            "sta_lat": [34.0, 34.0, 34.1, 34.1, 34.0, 34.0, 34.1, 34.1],
            "metric": ["PSA"] * 8,
            "band": [""] * 8,
            "component": ["R"] * 8,
            "model": ["m1"] * 8,
            "period_s": [1.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 2.0],
            "log2_residual": [1.0, 3.0, -1.0, 1.0, 2.0, 4.0, -2.0, 2.0],
        }
    )
    context = MetricFigureContext.from_frame(
        rows,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=0,
        value_col="log2_residual",
        station_aggregation="mean",
        write_sidecars=True,
        sidecar_rows=None,
    )
    item = {
        "key": "psa",
        "label": "PSA",
        "metric": "PSA",
        "period_s": None,
        "df": rows,
    }
    output = context.figure_dir / f"{context.figure_name('station_metric_map', item)}.png"
    output.write_bytes(b"existing")

    def _should_not_render(*args, **kwargs) -> None:  # noqa: ANN002, ANN003
        raise AssertionError("existing PSA sheet should not be rendered")

    result = context.write_psa_period_sheet(
        "station_metric_map",
        item,
        _should_not_render,
        df_factory=context.station_period_summary_for_item,
        source_df_factory=context.item_source_rows,
        required=["sta_lon", "sta_lat", "log2_residual"],
        value_col="log2_residual",
    )

    assert result == output
    sidecar_path = context.sidecar_output_dir / f"{output.stem}.csv"
    source_path = context.sidecar_output_dir / f"{output.stem}.source.csv"
    metadata = json.loads(sidecar_path.with_suffix(".json").read_text(encoding="utf-8"))
    sidecar = pd.read_csv(sidecar_path)
    source_sidecar = pd.read_csv(source_path)

    assert set(sidecar["__svtk_panel_period_s"]) == {1.0, 2.0}
    assert len(sidecar) == 4
    assert len(source_sidecar) == 8
    assert set(source_sidecar["__svtk_panel_period_s"]) == {1.0, 2.0}
    assert metadata["aggregation_contract"] == "station_event_rows_to_station_summary"
    assert metadata["plot_rows_role"] == "post_aggregation_station_summary"
    assert metadata["source_rows_role"] == "pre_aggregation_metric_rows"
    assert metadata["svtk_aggregation_kind"] == "station_event_rows_to_station_summary_by_panel"
    assert metadata["svtk_aggregation_panel_count"] == 2
    assert metadata["svtk_aggregation_input_row_count"] == 8
    assert metadata["svtk_aggregation_collapsed_columns"] == ["metric", "band", "model", "component"]
    assert metadata["svtk_aggregation_collapsed_unique_counts"] == {
        "metric": 1,
        "band": 1,
        "model": 1,
        "component": 1,
    }
    assert metadata["source_row_count"] == 8


def test_psa_period_sheet_render_writes_empty_panel_sidecar(tmp_path: Path) -> None:
    """Fresh PSA sheet renders should document empty plotted-row selections."""

    rows = pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "station": ["STA", "STB"],
            "sta_lon": [-118.0, -117.9],
            "sta_lat": [34.0, 34.1],
            "metric": ["PSA", "PSA"],
            "band": ["", ""],
            "component": ["R", "R"],
            "model": ["m1", "m1"],
            "period_s": [1.0, 2.0],
            "log2_residual": [1.0, 2.0],
        }
    )
    context = MetricFigureContext.from_frame(
        rows,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=0,
        value_col="log2_residual",
        write_sidecars=True,
        sidecar_rows=None,
    )
    item = {"key": "psa", "label": "PSA", "metric": "PSA", "period_s": None, "df": rows}

    def _write_panel(frame: pd.DataFrame, *, output_path, **kwargs) -> None:  # noqa: ANN001, ANN003
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, f"rows={len(frame)}", ha="center", va="center")
        fig.savefig(output_path)
        plt.close(fig)

    result = context.write_psa_period_sheet(
        "station_metric_map",
        item,
        _write_panel,
        df_factory=lambda period_item: period_item["df"].iloc[0:0].copy(),
        required=["sta_lon", "sta_lat", "log2_residual"],
        value_col="log2_residual",
    )

    assert result is not None
    sidecar_path = context.sidecar_output_dir / f"{result.stem}.csv"
    metadata = json.loads(sidecar_path.with_suffix(".json").read_text(encoding="utf-8"))
    sidecar = pd.read_csv(sidecar_path)
    assert sidecar.empty
    assert sidecar_path.exists()
    assert metadata["plot_row_count"] == 0
    assert metadata["written_row_count"] == 0
    assert metadata["plot_rows_role"] == "figure_plot_rows"


def test_large_run_score_trend_helper_writes_sidecar_rows(tmp_path: Path) -> None:
    """Large-run score trend helper should preserve plotted/source row audits."""

    rows = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3"],
            "station": ["STA", "STA", "STB"],
            "metric": ["PGA", "PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec"],
            "component": ["R", "T", "R"],
            "model": ["m1", "m1", "m1"],
            "distance_km": [10.0, 20.0, 30.0],
            "log2_residual": [0.1, -0.2, 0.3],
            "anderson_2004_gof": [8.0, 7.0, 9.0],
        }
    )
    context = MetricFigureContext.from_frame(
        rows,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=0,
        value_col="log2_residual",
        write_sidecars=True,
        sidecar_rows=None,
    )

    outputs = context.write_score_trend_plots(
        plot_score_trends,
        score_columns=["anderson_2004_gof"],
        showfig=False,
    )

    assert len(outputs) == 1
    sidecar_path = context.sidecar_output_dir / f"{outputs[0].stem}.csv"
    metadata = json.loads(sidecar_path.with_suffix(".json").read_text(encoding="utf-8"))
    sidecar = pd.read_csv(sidecar_path)

    assert len(sidecar) == len(rows)
    assert set(sidecar["anderson_2004_gof"]) == {7.0, 8.0, 9.0}
    assert set(sidecar["distance_km"]) == {10.0, 20.0, 30.0}
    assert metadata["value_col"] == "log2_residual"
    assert metadata["plot_rows_role"] == "figure_plot_rows"
    assert metadata["plot_sidecar_exact"] is True
    assert metadata["source_sidecar_exact"] is True


def test_spatial_figure_context_accepts_shared_sidecar_settings(tmp_path: Path) -> None:
    """Step 4 large-run notebooks should use the shared sidecar keyword shape."""

    tables = tmp_path / "tables"
    cfg = SpatialVTKConfig(
        tmp_path / "config.yaml",
        tmp_path,
        {
            "outputs": {
                "root": str(tmp_path),
                "tables": str(tables),
                "figures": str(tmp_path / "figures"),
            }
        },
    )
    sidecars = tmp_path / "custom_sidecars"

    context = SpatialFigureContext.from_config(
        cfg=cfg,
        figure_dir=tmp_path / "figures",
        make_figures=False,
        write_sidecars=True,
        sidecar_rows=10,
        sidecar_dir=sidecars,
    )

    assert context.metric_context.write_sidecars is True
    assert context.event_context.write_sidecars is True
    assert context.metric_context.sidecar_rows == 10
    assert context.event_context.sidecar_rows == 10
    assert context.metric_context.sidecar_output_dir == sidecars
    assert context.event_context.sidecar_output_dir == sidecars


def test_spatial_figure_context_writes_overview_plots_with_empty_missing_tables(tmp_path: Path) -> None:
    """Overview orchestration should not fall back to metric rows for missing optional tables."""

    metric_field = pd.DataFrame(
        {
            "event_id": ["e1"],
            "station": ["STA"],
            "metric": ["PGA"],
            "band": ["1-2 sec"],
            "component": ["R"],
            "model": ["m1"],
            "log2_residual": [0.25],
            "distance_center_km": [10.0],
            "mean_pair_correlation": [0.9],
        }
    )
    context = SpatialFigureContext(
        figure_dir=tmp_path / "figures",
        make_figures=True,
        metric_context=MetricFigureContext.from_frame(metric_field, tmp_path / "figures", make_figures=True),
        event_context=MetricFigureContext.from_frame(metric_field, tmp_path / "figures", make_figures=True),
        tables={
            "metric_field": metric_field,
            "event_centered_residuals": metric_field,
            "distance_bin_correlations": None,
            "station_bias": None,
            "pattern_similarity_station_anomalies": None,
            "geology_contrasts": None,
        },
        paths={},
    )
    status = context.status_frame().set_index("name")
    assert bool(status.loc["metric_field", "loaded"]) is True
    assert status.loc["metric_field", "row_count"] == 1
    assert status.loc["metric_field", "value_col"] == "log2_residual"
    assert status.loc["metric_field", "value_role"] == "raw event-station residuals; event means retained"
    assert "event-station metric field" in status.loc["metric_field", "role"]
    assert status.loc["event_centered_residuals", "value_role"] == "event-centered residuals; event means removed"
    assert pd.isna(status.loc["metric_field", "resolved_path"])
    assert pd.isna(status.loc["metric_field", "path"])
    dimensions = context.dimension_summary_frame()
    metric_dimensions = dimensions.loc[dimensions["table"].eq("metric_field")].set_index("dimension")
    assert metric_dimensions.loc["metric", "values_preview"] == "PGA"
    assert metric_dimensions.loc["station", "unique_count"] == 1

    calls: list[dict[str, object]] = []

    def _fake_write_spatial_plot(base, item, func, df=None, **kwargs):  # noqa: ANN001, ANN202
        calls.append({"base": base, "df": df, "kwargs": kwargs})
        return tmp_path / f"{base}.png"

    plot_functions = {
        name: (lambda *args, **kwargs: None)
        for name in (
            "plot_block_holdout_scatter",
            "plot_cluster_feature_heatmap",
            "plot_cluster_solution_scores",
            "plot_correlogram",
            "plot_distance_correlation_by_metric",
            "plot_directional_correlogram",
            "plot_geology_contrast",
            "plot_path_bin_summary",
            "plot_pattern_similarity",
            "plot_pca_explained_variance",
            "plot_pca_feature_loadings",
            "plot_residual_correlation",
            "plot_semivariogram",
        )
    }

    context.write_spatial_plot = _fake_write_spatial_plot  # type: ignore[method-assign]
    outputs = context.write_overview_plots(
        value_col="log2_residual",
        event_value_col="log2_residual",
        showfig=False,
        plot_functions=plot_functions,
    )

    assert len(outputs) == 11
    correlogram = next(call for call in calls if call["base"] == "spatial_correlogram")
    assert isinstance(correlogram["df"], pd.DataFrame)
    assert correlogram["df"].empty
    assert "distance_center_km" not in correlogram["df"].columns
    assert not any(call["base"] == "spatial_pattern_similarity" for call in calls)
    assert not any(call["base"] == "spatial_geology_contrast" for call in calls)


def test_spatial_figure_context_orchestrates_large_run_plot_families(tmp_path: Path) -> None:
    """Step 4 notebook plot families should be package methods with PSA branching."""

    metric_field = pd.DataFrame(
        {
            "event_id": ["e1", "e1"],
            "station": ["STA", "STA"],
            "metric": ["PGA", "PSA"],
            "band": ["1-2 sec", "1-2 sec"],
            "component": ["R", "R"],
            "model": ["m1", "m1"],
            "period_s": [np.nan, 1.0],
            "log2_residual": [0.25, 0.5],
            "sta_lon": [-118.0, -118.0],
            "sta_lat": [34.0, 34.0],
            "lon": [-118.0, -118.0],
            "lat": [34.0, 34.0],
            "azimuth_deg": [45.0, 45.0],
            "distance_km": [10.0, 10.0],
        }
    )
    figure_dir = tmp_path / "figures"
    context = SpatialFigureContext(
        figure_dir=figure_dir,
        make_figures=True,
        add_basemap=True,
        metric_context=MetricFigureContext.from_frame(metric_field, figure_dir, make_figures=True),
        event_context=MetricFigureContext.from_frame(metric_field, figure_dir, make_figures=True),
        tables={
            "metric_field": metric_field,
            "event_centered_residuals": metric_field,
        },
        paths={},
    )
    calls: list[dict[str, object]] = []

    def _fake_plot(base, item, func, df=None, source_df=None, **kwargs):  # noqa: ANN001, ANN202
        calls.append(
            {
                "writer": "plot",
                "base": base,
                "key": item["key"],
                "df": df,
                "source_df": source_df,
                "kwargs": kwargs,
            }
        )
        return figure_dir / f"{base}_{len(calls)}.png"

    def _fake_sheet(base, item, func, df_factory=None, source_df_factory=None, **kwargs):  # noqa: ANN001, ANN202
        calls.append(
            {
                "writer": "sheet",
                "base": base,
                "key": item["key"],
                "df_factory": df_factory,
                "source_df_factory": source_df_factory,
                "kwargs": kwargs,
            }
        )
        return figure_dir / f"{base}_{len(calls)}.png"

    context.write_spatial_plot = _fake_plot  # type: ignore[method-assign]
    context.write_spatial_period_sheet = _fake_sheet  # type: ignore[method-assign]
    plot_func = lambda *args, **kwargs: None

    context.write_station_metric_maps(plot_func, plot_func, value_col="log2_residual")
    context.write_residual_grid_maps(plot_func, value_col="log2_residual")
    context.write_metric_by_model_maps(plot_func, value_col="log2_residual")
    context.write_event_residual_maps(plot_func, value_col="log2_residual")
    context.write_event_centered_azimuthal_plots(plot_func, value_col="log2_residual")
    context.write_event_centered_polar_plots(plot_func, value_col="log2_residual")

    assert [call["base"] for call in calls].count("spatial_station_metric_map") == 2
    assert any(call["base"] == "spatial_residual_grid" and call["writer"] == "sheet" for call in calls)
    assert any(call["base"] == "spatial_metric_by_model_map" and call["writer"] == "sheet" for call in calls)
    assert any(call["base"] == "spatial_event_residual_map" and call["writer"] == "sheet" for call in calls)
    assert any(call["base"] == "spatial_azimuthal_residuals" and call["writer"] == "sheet" for call in calls)
    assert any(call["base"] == "spatial_polar_residuals" and call["writer"] == "sheet" for call in calls)
    assert any(call["source_df"] is not None for call in calls if call["writer"] == "plot")
    assert any(
        getattr(call["source_df_factory"], "__name__", "") == "item_source_rows"
        for call in calls
        if call["writer"] == "sheet"
    )


def test_spatial_figure_context_uses_explicit_table_owner_for_overlapping_schemas(tmp_path: Path) -> None:
    """Metric/event-centered routing should not depend on ambiguous column subsets."""

    metric_field = pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "station": ["STA", "STB"],
            "metric": ["PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec"],
            "component": ["R", "R"],
            "model": ["m1", "m1"],
            "field_value": [0.25, 0.5],
            "sta_lon": [-118.0, -117.9],
            "sta_lat": [34.0, 34.1],
        }
    )
    event_centered = metric_field.assign(event_centered_residual=[0.1, -0.1])
    metric_field.attrs["svtk_spatial_context"] = "metric"
    event_centered.attrs["svtk_spatial_context"] = "event"
    figure_dir = tmp_path / "figures"
    context = SpatialFigureContext(
        figure_dir=figure_dir,
        make_figures=True,
        metric_context=MetricFigureContext.from_frame(
            metric_field,
            figure_dir,
            make_figures=True,
            value_col="field_value",
        ),
        event_context=MetricFigureContext.from_frame(
            event_centered,
            figure_dir,
            make_figures=True,
            value_col="event_centered_residual",
        ),
        tables={
            "metric_field": metric_field,
            "event_centered_residuals": event_centered,
        },
        paths={},
    )

    metric_item = next(context.iter_metric_frames(metric_field, split_psa_period=False))
    event_item = next(context.iter_metric_frames(event_centered, split_psa_period=False))

    assert metric_item["svtk_spatial_context"] == "metric"
    assert event_item["svtk_spatial_context"] == "event"
    assert context._context_for_item(metric_item) is context.metric_context
    assert context._context_for_item(event_item) is context.event_context
    assert context.station_summary_for_item(metric_item, "field_value")["field_value"].tolist() == [0.25, 0.5]


def test_spatial_figure_context_labels_event_centered_path_plots(tmp_path: Path) -> None:
    """Large-run event-centered path plots should state that event means are removed."""

    metric_field = pd.DataFrame(
        {
            "event_id": ["e1"],
            "station": ["STA"],
            "metric": ["PGA"],
            "band": ["1-2 sec"],
            "component": ["R"],
            "model": ["m1"],
            "log2_residual": [0.25],
            "distance_km": [10.0],
            "azimuth_deg": [45.0],
        }
    )
    event_centered = metric_field.assign(event_mean=[0.1])
    figure_dir = tmp_path / "figures"
    context = SpatialFigureContext(
        figure_dir=figure_dir,
        make_figures=True,
        metric_context=MetricFigureContext.from_frame(metric_field, figure_dir, make_figures=True),
        event_context=MetricFigureContext.from_frame(event_centered, figure_dir, make_figures=True),
        tables={
            "metric_field": metric_field,
            "event_centered_residuals": event_centered,
        },
        paths={},
    )
    item = {
        "key": "pga",
        "label": "PGA",
        "metric": "PGA",
        "period_s": None,
        "df": event_centered,
    }
    calls: list[dict[str, object]] = []

    def _fake_metric_plot(base, item, func, **kwargs):  # noqa: ANN001, ANN202
        calls.append({"method": "plot", "base": base, "kwargs": kwargs})
        return figure_dir / f"{base}.png"

    def _fake_period_sheet(base, item, func, **kwargs):  # noqa: ANN001, ANN202
        calls.append({"method": "period", "base": base, "kwargs": kwargs})
        return figure_dir / f"{base}_period.png"

    context.event_context.write_metric_plot = _fake_metric_plot  # type: ignore[method-assign]
    context.event_context.write_psa_period_sheet = _fake_period_sheet  # type: ignore[method-assign]

    context.write_spatial_plot("spatial_azimuthal_residuals", item, lambda *args, **kwargs: None)
    context.write_spatial_period_sheet("spatial_polar_residuals", item, lambda *args, **kwargs: None)

    assert calls[0]["kwargs"]["title"] == "Event-Centered Azimuthal Residuals (Event Mean Removed)"
    assert calls[1]["kwargs"]["title"] == "Event-Centered Polar Residuals (Event Mean Removed)"


def test_spatial_figure_context_writes_pca_summary_with_layered_sidecar(tmp_path: Path) -> None:
    """Large-run Step 4 should expose the standard combined PCA summary figure."""

    metric_field = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3"],
            "station": ["STA", "STB", "STC"],
            "metric": ["PGA", "PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec"],
            "component": ["R", "R", "R"],
            "model": ["m1", "m1", "m1"],
            "log2_residual": [0.1, -0.2, 0.3],
            "lon": [-118.2, -118.0, -117.8],
            "lat": [34.0, 34.1, 34.2],
        }
    )
    pca_scores = pd.DataFrame(
        {
            "station": ["STA", "STB", "STC"],
            "metric": ["PGA", "PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec"],
            "component": ["R", "R", "R"],
            "model": ["m1", "m1", "m1"],
            "lon": [-118.2, -118.0, -117.8],
            "lat": [34.0, 34.1, 34.2],
            "PC1_score": [1.2, -0.6, 0.4],
        }
    )
    explained = pd.DataFrame(
        {
            "metric": ["PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec"],
            "component": ["R", "R"],
            "model": ["m1", "m1"],
            "mode": ["PC1", "PC2"],
            "mode_index": [1, 2],
            "explained_variance_ratio": [0.75, 0.2],
            "cumulative_explained_variance_ratio": [0.75, 0.95],
        }
    )
    loadings = pd.DataFrame(
        {
            "metric": ["PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec"],
            "component": ["R", "R"],
            "model": ["m1", "m1"],
            "mode": ["PC1", "PC1"],
            "feature": ["event_a", "event_b"],
            "loading": [0.8, -0.35],
            "absolute_loading": [0.8, 0.35],
        }
    )
    figure_dir = tmp_path / "figures"
    context = SpatialFigureContext(
        figure_dir=figure_dir,
        make_figures=True,
        metric_context=MetricFigureContext.from_frame(
            metric_field,
            figure_dir,
            make_figures=True,
            write_sidecars=True,
            sidecar_rows=None,
            sidecar_dir=tmp_path / "sidecars",
        ),
        event_context=MetricFigureContext.from_frame(metric_field, figure_dir, make_figures=True),
        tables={
            "metric_field": metric_field,
            "event_centered_residuals": metric_field,
            "pca_station_scores": pca_scores,
            "pca_explained_variance": explained,
            "pca_feature_loadings": loadings,
        },
        paths={},
    )

    outputs = context.write_pca_summary_plots(
        plot_pca_summary,
        passband="1-2 sec",
        components=["R"],
        model="m1",
        mode="PC1",
        showfig=False,
    )

    assert len(outputs) == 1
    assert outputs[0].exists()
    assert "spatial_pca_summary__pga__1-2-sec__R__m1__PC1-score" in outputs[0].stem
    sidecar = pd.read_csv(tmp_path / "sidecars" / f"{outputs[0].stem}.csv")
    metadata = json.loads((tmp_path / "sidecars" / f"{outputs[0].stem}.json").read_text(encoding="utf-8"))
    assert set(sidecar["_figure_layer"]) == {"station_score", "explained_variance", "feature_loading"}
    assert metadata["figure_type"] == "pca_summary"
    assert metadata["mode"] == "PC1"


def test_metric_figure_context_reads_plot_columns_and_filters_defaults(tmp_path: Path) -> None:
    """Large-run figure context should avoid loading unused metric columns."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3", "e4"],
            "station": ["STA", "STA", "STB", "STC"],
            "sta_lon": [-118.0, -118.0, -117.9, -117.8],
            "sta_lat": [34.0, 34.0, 34.1, 34.2],
            "metric": ["PGA", "PGV", "not_a_target_metric", "PGA"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec", "1-2 sec"],
            "component": ["R", "T", "R", "R"],
            "model": ["m1", "m1", "m1", "m2"],
            "distance_km": [10.0, 11.0, 12.0, 13.0],
            "period_s": [np.nan, np.nan, np.nan, np.nan],
            "log2_residual": [0.1, 0.2, 99.0, 0.4],
            "unused_large_payload": ["x" * 50, "y" * 50, "z" * 50, "q" * 50],
        }
    )
    metrics_path = tmp_path / "metrics_long.parquet"
    metrics.to_parquet(metrics_path, index=False)

    context = MetricFigureContext.from_metrics_long(
        metrics_path,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=0,
        value_col="log2_residual",
        default_components=["R"],
        default_model="m1",
    )

    assert context.ready
    assert "unused_large_payload" in context.available_columns
    assert "unused_large_payload" not in context.loaded_columns
    assert "unused_large_payload" not in context.metrics_for_figures.columns
    assert context.loaded_columns == [
        "event_id",
        "station",
        "sta_lon",
        "sta_lat",
        "metric",
        "band",
        "component",
        "model",
        "distance_km",
        "period_s",
        "log2_residual",
    ]
    assert context.metrics_for_figures[["event_id", "metric", "component", "model"]].to_dict("records") == [
        {"event_id": "e1", "metric": "PGA", "component": "R", "model": "m1"}
    ]
    status = context.status_frame().set_index("name")["value"]
    assert bool(status["ready"]) is True
    assert status["selected_metric_rows"] == 1
    assert status["loaded_column_count"] == len(context.loaded_columns)
    assert status["default_components"] == "R"
    assert status["default_model"] == "m1"
    assert pd.isna(status["sample_rows_per_figure"])

    dimensions = context.dimension_summary_frame().set_index("dimension")
    assert dimensions.loc["metric", "unique_count"] == 1
    assert dimensions.loc["metric", "values_preview"] == "PGA"
    assert dimensions.loc["component", "values_preview"] == "R"
    assert dimensions.loc["station", "unique_count"] == 1
    assert dimensions.loc["event", "finite_value_rows"] == 1


def test_redcap_clusters_use_spatial_constraints_and_scores() -> None:
    """REDCAP clustering should assign spatially constrained station regions."""

    rows = []
    for idx in range(10):
        group = 0 if idx < 5 else 1
        rows.append(
            {
                "station": f"S{idx:02d}",
                "station_longitude": -118.5 + 0.03 * idx,
                "station_latitude": 34.0 + 0.01 * group,
                "avg_observed_metric_distance_scaled_event_demeaned": -1.0 if group == 0 else 1.0,
            }
        )
    stations = pd.DataFrame(rows)
    clustered, scores = assign_redcap_clusters(
        stations,
        min_k=2,
        max_k=4,
        n_neighbors=2,
        location_weight=0.1,
        residual_weight=2.0,
    )

    assert not clustered.empty
    assert clustered["cluster"].nunique() >= 2
    assert bool(scores["selected"].any())
    assert {"selected_k", "selected_silhouette_score", "redcap_residual_weight"} <= set(clustered.columns)


def test_pca_spatial_modes_from_station_fingerprints() -> None:
    """PCA modes should summarize station residual-feature matrices."""

    normalized = normalize_metrics_table(_toy_metrics_table(), default_model="example")
    field = build_metric_field(normalized, "C5")
    centered = center_field_by_event(field, min_stations_per_event=3)
    station_bias = summarize_station_bias(centered, min_events_per_station=2)
    fingerprint = station_bias[["station", "lat", "lon", "mean_centered"]].copy()
    fingerprint["synthetic_east_west_residual_pattern"] = (
        fingerprint["lon"] - fingerprint["lon"].mean()
    ) / fingerprint["lon"].std(ddof=0)
    fingerprint["synthetic_north_south_residual_pattern"] = (
        fingerprint["lat"] - fingerprint["lat"].mean()
    ) / fingerprint["lat"].std(ddof=0)

    result = compute_pca_spatial_modes(fingerprint, n_components=2, min_nonmissing_per_station=2)

    assert len(result.station_scores) == len(fingerprint)
    assert {"PC1_score", "PC2_score"} <= set(result.station_scores.columns)
    assert set(result.explained_variance["mode"]) == {"PC1", "PC2"}
    assert result.explained_variance["explained_variance_ratio"].sum() <= 1.0 + 1.0e-12
    assert {"mean_centered", "synthetic_east_west_residual_pattern", "synthetic_north_south_residual_pattern"} <= set(result.feature_columns)
    assert {"mode", "feature", "loading", "absolute_loading"} <= set(result.feature_loadings.columns)


def test_spatial_plot_and_map_wrappers_write_pngs(tmp_path: Path) -> None:
    """Public plot and map wrappers should write figures from calculation outputs."""

    normalized = normalize_metrics_table(_toy_metrics_table(), default_model="example")
    field = build_metric_field(normalized, "C5")
    centered = center_field_by_event(field, min_stations_per_event=3)
    station_bias = summarize_station_bias(centered, min_events_per_station=2)
    distance = build_distance_bin_summary(centered, bin_width_km=20, max_distance_km=120, random_seed=7)
    directional = build_directional_distance_bin_summary(centered, bin_width_km=20, max_distance_km=120, random_seed=7)
    moran = moran_result_to_frame(compute_global_morans_i(station_bias, k=4, permutations=9, random_seed=7))
    fit = fit_exponential_correlation_length(distance, min_pairs_per_bin=1)
    directional_fit = summarize_directional_fits(directional, min_pairs_per_bin=1)
    _blocks, predictions, _summary = evaluate_spatial_block_holdouts(
        field,
        block_size_km=15,
        min_block_stations=1,
        min_stations_per_event=3,
        min_events_per_station=2,
        prediction_k=3,
    )
    fingerprint = station_bias[["station", "lat", "lon", "mean_centered"]].copy()
    fingerprint["synthetic_east_west_residual_pattern"] = (
        fingerprint["lon"] - fingerprint["lon"].mean()
    ) / fingerprint["lon"].std(ddof=0)
    assignments, scores, feature_summary, _cluster_summary, _best, features = run_residual_feature_clustering(
        fingerprint,
        cluster_min_k=2,
        cluster_max_k=4,
        random_seed=7,
    )
    pca_result = compute_pca_spatial_modes(fingerprint, n_components=2)
    redcap_input = station_bias.rename(
        columns={
            "lon": "station_longitude",
            "lat": "station_latitude",
            "mean_centered": "avg_observed_metric_distance_scaled_event_demeaned",
        }
    )
    redcap_df, _redcap_scores = assign_redcap_clusters(redcap_input, min_k=2, max_k=4, n_neighbors=2)
    pattern_input = pd.DataFrame(
        {
            "station_name": [f"S{i}" for i in range(6)] * 2,
            "dataset": ["observed"] * 6 + ["synthetic"] * 6,
            "metric": ["C5"] * 12,
            "bin": ["1-2 sec"] * 12,
            "value": list(np.linspace(-1.0, 1.0, 6)) + list(np.linspace(-0.8, 0.8, 6)),
        }
    )

    outputs = [
        plot_correlogram(distance, tmp_path / "correlogram.png", fit=fit),
        plot_distance_correlation_by_metric(
            distance.assign(metric="C5"),
            tmp_path / "distance_correlation_by_metric.png",
            significance_df=moran.assign(metric="C5"),
        ),
        plot_semivariogram(distance, tmp_path / "semivariogram.png"),
        plot_directional_correlogram(directional, tmp_path / "directional.png", fit_df=directional_fit),
        plot_block_holdout_scatter(predictions, tmp_path / "holdout_scatter.png"),
        plot_cluster_solution_scores(scores, tmp_path / "cluster_scores.png"),
        plot_cluster_feature_heatmap(feature_summary, tmp_path / "cluster_heatmap.png", feature_order=features),
        plot_pca_explained_variance(pca_result.explained_variance, tmp_path / "pca_variance.png"),
        plot_pca_feature_loadings(pca_result.feature_loadings, tmp_path / "pca_loadings.png", mode="PC1"),
        plot_pattern_similarity(pattern_input, tmp_path / "pattern_similarity.png", metric="C5", bin_label="1-2 sec"),
        plot_station_bias_map(station_bias, tmp_path / "station_bias_map.png", add_basemap=False),
        plot_cluster_map(assignments, tmp_path / "cluster_map.png", add_basemap=False),
        plot_pca_mode_map(pca_result.station_scores, tmp_path / "pca_mode_map.png", mode="PC1", add_basemap=False),
        plot_redcap_cluster_map(redcap_df, tmp_path / "redcap_map.png", add_basemap=False),
        plot_block_holdout_error_map(predictions, tmp_path / "holdout_error_map.png", add_basemap=False),
    ]

    for path in outputs:
        assert path.exists(), path
        assert path.stat().st_size > 0, path


def test_spatial_statistics_figures_write_optional_row_sidecars(tmp_path: Path) -> None:
    """Spatial statistics figures should optionally write plotted/source rows."""

    normalized = normalize_metrics_table(_toy_metrics_table(), default_model="example")
    field = build_metric_field(normalized, "C5")
    centered = center_field_by_event(field, min_stations_per_event=3)
    station_bias = summarize_station_bias(centered, min_events_per_station=2)
    moran = moran_result_to_frame(compute_global_morans_i(station_bias, k=4, permutations=9, random_seed=7)).assign(metric="C5")
    distance = build_distance_bin_summary(centered, bin_width_km=20, max_distance_km=120, random_seed=7).assign(metric="C5")
    zero_pair_bin = distance.iloc[[0]].copy()
    zero_pair_bin["distance_center_km"] = 999.0
    zero_pair_bin["pair_count"] = 0
    distance = pd.concat([distance, zero_pair_bin], ignore_index=True)
    predictions = evaluate_spatial_block_holdouts(
        field,
        block_size_km=15,
        min_block_stations=1,
        min_stations_per_event=3,
        min_events_per_station=2,
        prediction_k=3,
    )[1]
    fingerprint = station_bias[["station", "lat", "lon", "mean_centered"]].copy()
    fingerprint["synthetic_east_west_residual_pattern"] = (
        fingerprint["lon"] - fingerprint["lon"].mean()
    ) / fingerprint["lon"].std(ddof=0)
    assignments, scores, feature_summary, _cluster_summary, _best, _features = run_residual_feature_clustering(
        fingerprint,
        cluster_min_k=2,
        cluster_max_k=4,
        random_seed=7,
    )
    pca_result = compute_pca_spatial_modes(fingerprint, n_components=2)
    pca_station_scores = pd.concat(
        [
            pca_result.station_scores,
            pca_result.station_scores.iloc[[0]].assign(station="NO_FINITE_PC1", PC1_score=np.nan),
        ],
        ignore_index=True,
    )
    sidecar_dir = tmp_path / "sidecars"

    figures = [
        plot_distance_correlation_by_metric(
            distance,
            tmp_path / "distance_correlation.png",
            significance_df=moran,
            write_sidecar=True,
            sidecar_rows=None,
            sidecar_dir=sidecar_dir,
        ),
        plot_station_bias_map(
            station_bias,
            tmp_path / "station_bias_map.png",
            add_basemap=False,
            write_sidecar=True,
            sidecar_rows=None,
            sidecar_dir=sidecar_dir,
        ),
        plot_block_holdout_scatter(
            predictions,
            tmp_path / "holdout_scatter.png",
            write_sidecar=True,
            sidecar_rows=None,
            sidecar_dir=sidecar_dir,
        ),
        plot_cluster_summary(
            assignments,
            scores,
            feature_summary,
            tmp_path / "cluster_summary.png",
            add_basemap=False,
            write_sidecar=True,
            sidecar_rows=None,
            sidecar_dir=sidecar_dir,
        ),
        plot_pca_summary(
            pca_station_scores,
            pca_result.explained_variance,
            pca_result.feature_loadings,
            tmp_path / "pca_summary.png",
            mode="PC1",
            add_basemap=False,
            write_sidecar=True,
            sidecar_rows=None,
            sidecar_dir=sidecar_dir,
        ),
    ]
    for figure in figures:
        assert figure.spatial_vtk_saved_path.exists()

    distance_metadata = json.loads((sidecar_dir / "distance_correlation.json").read_text(encoding="utf-8"))
    assert distance_metadata["figure_type"] == "distance_correlation_by_metric"
    distance_rows = pd.read_csv(sidecar_dir / "distance_correlation.csv")
    assert set(distance_rows["_figure_layer"]).issubset({"distance_correlation", "significance"})
    distance_source = pd.read_csv(sidecar_dir / "distance_correlation.source.csv")
    distance_source_rows = distance_source.loc[distance_source["_figure_layer"].eq("distance_correlation")]
    assert not (pd.to_numeric(distance_source_rows["pair_count"], errors="coerce") == 0).any()

    station_metadata = json.loads((sidecar_dir / "station_bias_map.json").read_text(encoding="utf-8"))
    assert station_metadata["figure_type"] == "station_bias_map"
    assert station_metadata["source_row_count"] == len(station_bias)

    cluster_rows = pd.read_csv(sidecar_dir / "cluster_summary.csv")
    assert set(cluster_rows["_figure_layer"]).issubset({"assignment", "score", "feature_summary"})
    pca_rows = pd.read_csv(sidecar_dir / "pca_summary.csv")
    assert set(pca_rows["_figure_layer"]).issubset({"station_score", "explained_variance", "feature_loading"})
    pca_station_rows = pca_rows.loc[pca_rows["_figure_layer"].eq("station_score")]
    assert "NO_FINITE_PC1" not in set(pca_station_rows["station"].astype(str))


def test_residual_color_settings_use_seismic_diverging_scale() -> None:
    """Signed log and centered values use a zero-centered seismic color scale."""

    cmap, vmin, vmax = value_color_settings(np.asarray([-0.2, 0.05, 0.1]), "log2_residual")
    assert cmap == "seismic"
    assert vmin == -vmax

    field_df = pd.DataFrame({"field_source": ["distance-scaled event-demeaned residual"]})
    cmap, vmin, vmax = value_color_settings(np.asarray([-0.3, 0.2]), "field_centered", field_df)
    assert cmap == "seismic"
    assert vmin == -vmax


def test_geology_classes_bootstrap_moran_and_pattern_similarity(tmp_path: Path) -> None:
    """Geology helpers should classify stations and run public spatial tests."""

    target_region = Polygon([(-118.5, 33.9), (-118.0, 33.9), (-118.0, 34.4), (-118.5, 34.4), (-118.5, 33.9)])
    mountain = Polygon([(-117.9, 33.9), (-117.5, 33.9), (-117.5, 34.4), (-117.9, 34.4), (-117.9, 33.9)])
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"short_name": "Example Basin", "region_type": "Basin"}, "geometry": mapping(target_region)},
            {"type": "Feature", "properties": {"short_name": "Example Uplands", "region_type": "Mountains"}, "geometry": mapping(mountain)},
        ],
    }
    geojson_path = tmp_path / "regions.geojson"
    geojson_path.write_text(json.dumps(geojson), encoding="utf-8")
    records, target_geom = load_region_geometries(geojson_path, region_name="Example Basin")

    station_rows = []
    for idx in range(8):
        inside = idx < 4
        station_rows.append(
            {
                "station_name": f"S{idx}",
                "station_longitude": -118.25 if inside else -117.7,
                "station_latitude": 34.1 + 0.01 * idx,
            }
        )
    classified = add_station_geology_classes(pd.DataFrame(station_rows), region_records=records, target_region_geom=target_geom, edge_buffer_km=5.0)
    assert {"target_region_zone", "mapped_region_type"} <= set(classified.columns)
    assert {"Basin", "Mountains"} <= set(classified["mapped_region_type"])

    events = []
    for event in ["E1", "E2", "E3"]:
        for row in classified.itertuples(index=False):
            is_basin = row.mapped_region_type == "Basin"
            value = 1.0 if is_basin else -1.0
            events.append(
                {
                    "dataset": "residual",
                    "metric": "C5",
                    "bin": "1-2 sec",
                    "event_id": event,
                    "station_name": row.station_name,
                    "station_longitude": row.station_longitude,
                    "station_latitude": row.station_latitude,
                    "target_region_zone": row.target_region_zone,
                    "target_region_edge_distance_km": row.target_region_edge_distance_km,
                    "mapped_region": row.mapped_region,
                    "mapped_region_type": row.mapped_region_type,
                    "value": value,
                    "value_raw": value,
                }
            )
    events_df = pd.DataFrame(events)
    contrast = bootstrap_contrast(
        events_df,
        group_col="mapped_region_type",
        left_values=("Basin",),
        right_values=("Mountains",),
        n_bootstrap=20,
        rng=np.random.default_rng(7),
    )
    assert contrast["effect"] > 0.0

    stations = station_summary(events_df, min_events=2)
    contrasts, moran = run_geology_spatial_tests(
        events_df,
        stations,
        bootstrap_samples=20,
        permutation_samples=19,
        moran_neighbors=2,
        seed=7,
    )
    assert not contrasts.empty
    assert not moran.empty

    pattern_input = pd.concat(
        [
            stations.assign(dataset="observed", value=stations["value"]),
            stations.assign(dataset="synthetic", value=stations["value"] * 0.8),
        ],
        ignore_index=True,
    )
    similarity = pattern_similarity(pattern_input)
    assert not similarity.empty
    assert similarity["pearson_r"].iloc[0] > 0.9


def test_build_pattern_similarity_station_anomalies_from_long_metrics() -> None:
    """Long metric rows should convert to station-anomaly rows for plotting."""

    metrics = pd.DataFrame(
        {
            "station": ["S1", "S2", "S1", "S2"],
            "metric": ["PGA", "PGA", "PGV", "PGV"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec", "1-2 sec"],
            "component": ["Z", "Z", "Z", "Z"],
            "model": ["cvmsi", "cvmsi", "cvmsi", "cvmsi"],
            "value_obs": [2.0, 4.0, 10.0, 12.0],
            "value_syn": [1.0, 2.0, 9.0, 11.0],
        }
    )
    anomalies = build_pattern_similarity_station_anomalies(
        metrics,
        metric="PGA",
        passband="1-2 sec",
        component="Z",
        model="cvmsi",
    )
    assert set(anomalies["dataset"]) == {"observed", "synthetic"}
    assert set(anomalies["station_name"]) == {"S1", "S2"}
    assert np.isclose(anomalies.loc[anomalies["dataset"].eq("observed"), "value"].sum(), 0.0)
