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
from spatial_vtk.io import OutputGroup, write_table
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
    SpatialFigureContext,
    prepare_spatial_figure_context_from_notebook_settings,
    write_large_run_geojson_region_figures_from_outputs,
    write_large_run_region_boxplot,
    write_large_run_region_boxplot_from_outputs,
    write_large_run_spatial_summary_figures_from_outputs,
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
    cfg = SpatialVTKConfig.from_file(config_path)
    metrics = normalize_metrics_table(_toy_metrics_table(), default_model="example")
    station_metadata = pd.DataFrame(
        {
            "station": metrics["station"].drop_duplicates().tolist(),
            "mapped_region_type": (["Basin", "Mountains"] * 8)[: metrics["station"].nunique()],
        }
    )

    result = run_spatial_statistics_workflow(metrics, cfg=cfg, metric=("C5",), station_metadata=station_metadata, verbose=True)

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
    cfg = SpatialVTKConfig.from_file(config_path)
    metrics = normalize_metrics_table(_toy_metrics_table(), default_model="example_model")
    summaries = run_spatial_statistics_workflow(metrics, cfg=cfg, metric=("C5",))
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
        cfg=cfg,
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
        cfg=cfg,
    )
    assert set(reused.reused) == {
        "block_holdout_predictions",
        "redcap_clusters",
        "pattern_similarity_station_anomalies",
    }


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


def test_spatial_statistics_config_wrapper_resolves_dotted_path_arguments(tmp_path: Path) -> None:
    """Config-backed spatial helpers should accept dotted config path keys."""

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

    summary = run_spatial_statistics_workflow_from_config(
        config_path=config_path,
        metrics="paths.metric_figure_snapshot",
        station_metadata="paths.site_metadata",
        verbose=True,
    )

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
        metadata={"value_col": "log2_residual", "selection": ("PGA", "1-2 sec")},
    )

    assert result is not None
    assert result.sidecar_path == tmp_path / "figures" / "sidecars" / "station_map.csv"
    assert result.source_sidecar_path == tmp_path / "figures" / "sidecars" / "station_map.source.csv"
    assert result.metadata_path.exists()
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
    assert metadata["plot_station_count"] == 3
    assert metadata["source_station_count"] == 3
    assert metadata["source_model_count"] == 2
    assert metadata["plot_passband_count"] == 1
    assert metadata["source_passband_count"] == 2
    assert metadata["selection"] == ["PGA", "1-2 sec"]

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
    assert "event-station metric field" in status.loc["metric_field", "role"]
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

    assert calls[0]["kwargs"]["title"] == "Event-Centered Azimuthal Residuals"
    assert calls[1]["kwargs"]["title"] == "Event-Centered Polar Residuals"


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
