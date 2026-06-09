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
from spatial_vtk.spatial.map.correlation import (
    plot_block_holdout_error_map,
    plot_cluster_map,
    plot_redcap_cluster_map,
    plot_station_bias_map,
)
from spatial_vtk.spatial.map.pca import plot_pca_mode_map
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
from spatial_vtk.spatial.plot.metrics import plot_geology_contrast
from spatial_vtk.spatial.plot.pca import plot_pca_explained_variance, plot_pca_feature_loadings
from spatial_vtk.visualize.figure_context import value_color_settings


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
