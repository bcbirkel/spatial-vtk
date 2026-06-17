"""Tests for public spatial-statistics calculation helpers."""

from __future__ import annotations

from pathlib import Path
import json
import os

import matplotlib
import numpy as np
import pandas as pd
from shapely.geometry import Polygon, mapping

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")
matplotlib.use("Agg", force=True)

from spatial_vtk.config import SpatialVTKConfig, clear_active_config
from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.io import write_table
from spatial_vtk.metrics.plot.large_run import MetricFigureContext
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
from spatial_vtk.spatial.calculate.workflow import run_spatial_statistics_workflow
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
from spatial_vtk.spatial.plot.large_run import SpatialFigureContext, write_large_run_region_boxplot
from spatial_vtk.spatial.plot.metrics import plot_geology_contrast
from spatial_vtk.spatial.plot.pca import plot_pca_explained_variance, plot_pca_feature_loadings
from spatial_vtk.visualize.figure_context import value_color_settings
from spatial_vtk.visualize.figure_sidecars import write_figure_row_sidecar


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
    assert metadata["written_row_count"] == 2
    assert metadata["source_row_count"] == 4
    assert metadata["source_written_row_count"] == 2
    assert metadata["plot_rows_role"] == "figure_plot_rows"
    assert metadata["source_rows_role"] == "figure_source_rows"
    assert metadata["plot_station_count"] == 3
    assert metadata["source_station_count"] == 3
    assert metadata["source_model_count"] == 2
    assert metadata["plot_passband_count"] == 1
    assert metadata["source_passband_count"] == 2
    assert metadata["selection"] == ["PGA", "1-2 sec"]


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
    assert metadata["source_rows_role"] == "pre_aggregation_metric_rows"


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
        df_factory=lambda period_item: context.station_period_summary_for_map(period_item["df"], "log2_residual"),
        source_df_factory=lambda period_item: period_item["df"],
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
