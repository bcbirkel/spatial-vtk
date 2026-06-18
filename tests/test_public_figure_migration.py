"""Tests for migrated public figure families."""

from __future__ import annotations

import json
import inspect
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt

from spatial_vtk.config import SpatialVTKConfig, clear_active_config
from spatial_vtk.metrics.plot import (
    plot_band_score_distribution,
    plot_geology_boxplot,
    plot_metric_trend,
    plot_model_metric_heatmap,
    plot_period_spectra,
    plot_period_score_distribution,
    plot_period_spectrogram,
    plot_phase_delay_vs_distance,
    plot_psa_period_curve,
    plot_residuals_vs_depth,
    plot_residuals_vs_distance,
    plot_score_trends,
    plot_vs30_scatter,
    plot_winner_heatmap,
)
from spatial_vtk.spatial.map import (
    plot_metric_map_by_model,
    plot_model_improvement_map,
    plot_residual_grid,
    plot_score_map,
    plot_station_metric_map,
    plot_station_metric_map_by_period,
)
from spatial_vtk.spatial.plot import (
    boxplot,
    heatmap,
    plot_azimuthal_residuals,
    plot_geology_contrast,
    plot_path_bin_summary,
    plot_polar_residuals,
    plot_residual_correlation,
    scatterplot,
)
from spatial_vtk.visualize.context import (
    plot_event_magnitude_map,
    plot_station_event_beachball_map,
    plot_station_event_network_map,
)
from spatial_vtk.visualize.fit import draw_scatter_fit
from spatial_vtk.visualize.qc import (
    plot_data_synthetic_availability,
    plot_event_station_retention_heatmap,
    plot_post_qc_station_event_map,
    plot_qc_drop_cause_diagnostics,
    plot_retention_summary,
    plot_trace_inventory_samples,
)
from spatial_vtk.visualize import savefig
from spatial_vtk.visualize.waveforms import (
    plot_event_radial_trace_section,
    plot_event_trace_comparison,
    plot_station_event_waveform_map,
    plot_waveform_overlay_matrix,
)


def _assert_png(path: Path) -> None:
    """Assert that an output image exists and is non-empty."""

    assert path.exists()
    assert path.stat().st_size > 0


def test_plot_functions_return_saveable_figures(tmp_path: Path) -> None:
    """Notebook-style plotting should return a figure that can be saved later."""

    qc = pd.DataFrame(
        {
            "stage": ["1-2 sec", "1-2 sec", "2-3 sec"],
            "qc_status": ["pass", "fail", "pass"],
        }
    )
    fig = plot_retention_summary(qc, showfig=False)
    assert hasattr(fig, "savefig")
    output = savefig(fig, tmp_path / "retention_from_figure.png", close=True)
    _assert_png(output)


def test_public_plot_wrappers_expose_sidecar_controls() -> None:
    """Convenience wrappers should advertise figure sidecar parameters."""

    wrappers = [
        plot_residuals_vs_distance,
        plot_residuals_vs_depth,
        plot_score_trends,
        plot_phase_delay_vs_distance,
        plot_vs30_scatter,
        plot_score_map,
        plot_model_improvement_map,
    ]
    for wrapper in wrappers:
        parameters = inspect.signature(wrapper).parameters
        assert {"write_sidecar", "sidecar_rows", "sidecar_dir"} <= set(parameters), wrapper.__name__


def test_scatterplot_keyword_normalization_and_errors(tmp_path: Path, capsys) -> None:
    """Scatterplot should resolve friendly column variants and print options."""

    observed = pd.DataFrame({"distance_km": [10.0, 25.0, 40.0], "PGV": [0.4, 0.7, 0.6], "band": ["1-2 sec", "1-2 sec", "1-2 sec"]})
    output = scatterplot(observed, tmp_path / "normalized_scatter.png", indep="distance-km", dep="pgv", passband="1-2", fit="linear", data_label="Observed")
    _assert_png(output)
    categorical = pd.DataFrame({"geomorphic_province": ["Basin", "Hills", "Basin"], "pgv": [0.4, 0.7, 0.6], "band": ["1-2 sec", "1-2 sec", "1-2 sec"]})
    categorical_output = scatterplot(categorical, tmp_path / "categorical_scatter.png", indep="geomorphic_province", dep="pgv", passband="1-2", fit="linear")
    _assert_png(categorical_output)
    linear_fig = scatterplot(observed, indep="distance", dep="pgv", passband="1-2", fit="linear", data_label="Observed", showfig=False)
    linear_labels = [text.get_text() for text in linear_fig.axes[0].get_legend().get_texts()]
    assert any("linear best fit" in label and "slope=" in label and "r=" in label for label in linear_labels)
    for fit_name in ("inverse", "inverse-square", "quadratic"):
        fit_fig = scatterplot(observed, indep="distance", dep="pgv", passband="1-2", fit=fit_name, data_label="Observed", showfig=False)
        fit_labels = [text.get_text() for text in fit_fig.axes[0].get_legend().get_texts()]
        assert any(f"{fit_name} best fit" in label and "slope=" in label and "r=" in label for label in fit_labels)
    best_fig = scatterplot(observed, indep="distance", dep="pgv", passband="1-2", fit="best", data_label="Observed", showfig=False)
    best_labels = [text.get_text() for text in best_fig.axes[0].get_legend().get_texts()]
    assert any("best fit:" in label and "slope=" in label and "r=" in label for label in best_labels)
    grouped_fig = scatterplot(observed.assign(pga=[0.2, 0.3, 0.1]), indep="distance", dep=["pgv", "pga"], passband="1-2", fit="point-to-point", colorby="dep", showfig=False)
    grouped_labels = [text.get_text() for text in grouped_fig.axes[0].get_legend().get_texts()]
    assert all("fit" not in label.lower() for label in grouped_labels)
    try:
        scatterplot(observed, indep="not_a_column", dep="pgv", showfig=False)
    except KeyError:
        printed = capsys.readouterr().out
        assert "Unknown scatterplot keyword" in printed
        assert "distance_km" in printed
    else:
        raise AssertionError("Expected unknown scatterplot keyword to raise KeyError.")


def test_lowess_fit_collapses_duplicate_x_values() -> None:
    """LOWESS lines should smooth duplicate x-values instead of connecting rows."""

    from matplotlib import pyplot as plt

    fig, ax = plt.subplots()
    x = np.asarray([1.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 4.0, 4.0])
    y = np.asarray([0.0, 2.0, 4.0, 2.0, 3.0, 4.0, 2.0, 5.0, 7.0, 9.0])
    draw_scatter_fit(ax, x, y, fit_method="lowess", lowess_frac=0.8, color="black")
    line = ax.lines[-1]
    fit_x = line.get_xdata()
    fit_y = line.get_ydata()
    assert len(fit_x) == 100
    assert np.all(np.diff(fit_x) > 0.0)
    assert len(fit_y) == len(fit_x)
    plt.close(fig)


def test_categorical_metric_boxplot_and_heatmap(tmp_path: Path) -> None:
    """Open-ended categorical metric plots should resolve friendly aliases."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e1", "e1", "e1", "e2", "e2", "e2", "e2"],
            "station": ["B1", "M1", "B2", "M2"] * 2,
            "band": ["1-2 sec"] * 4 + ["2-3 sec"] * 4,
            "model": ["cvmsi"] * 8,
            "metric": ["PGA", "PGA", "PGV", "PGV"] * 2,
            "mapped_region_type": ["Basin", "Mountains", "Basin", "Mountains"] * 2,
            "value_obs": [1.0, 1.3, 2.0, 2.5, 1.1, 1.4, 2.1, 2.6],
            "log2_residual": [0.1, 0.4, -0.2, 0.0, 0.2, 0.3, -0.1, 0.1],
        }
    )
    output = boxplot(metrics, tmp_path / "boxplot.png", dep="PGA", indep="geomorphic region", value_col="log2_residuals_centered", passband="2-3", model="cvmsi", compare_to="Basin", table=True)
    _assert_png(output)
    grouped_output = boxplot(metrics, tmp_path / "grouped_boxplot.png", dep=["PGV", "PGA"], indep="geomorphic region", value_col="observed", passband="1-2", compare_to="Basin", table=True)
    _assert_png(grouped_output)
    heatmap_output = heatmap(metrics, tmp_path / "heatmap.png", dep=["PGV", "PGA"], indep="geomorphic region", value_col="observed", passband="1-2")
    _assert_png(heatmap_output)
    heatmap_fig = heatmap(metrics, dep=["PGV", "PGA"], indep="geomorphic region", value_col="observed", passband="all", showfig=False)
    assert "Model:" not in heatmap_fig.axes[0].get_title()
    all_band_boxplot = boxplot(metrics, tmp_path / "all_band_boxplot.png", dep="PGA", indep="geomorphic region", value_col="log2_residual", model="cvmsi")
    _assert_png(all_band_boxplot)
    all_band_heatmap = heatmap(metrics, tmp_path / "all_band_heatmap.png", dep=["PGV", "PGA"], indep="geomorphic region", value_col="observed", passband=None)
    _assert_png(all_band_heatmap)


def test_spatial_subset_controls_across_generic_plots(tmp_path: Path) -> None:
    """Generic plots should accept station/event region and corridor selectors."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e1", "e2", "e2"],
            "station": ["B1", "M1", "B2", "M2"],
            "band": ["1-2 sec"] * 4,
            "model": ["cvmsi"] * 4,
            "metric": ["PGA", "PGA", "PGV", "PGV"],
            "distance_km": [10.0, 20.0, 35.0, 50.0],
            "log2_residual": [0.1, 0.4, -0.2, 0.0],
            "value_obs": [1.0, 1.3, 2.0, 2.5],
            "mapped_region_type": ["Basin", "Mountains", "Basin", "Mountains"],
            "event_region": ["LA Basin", "LA Basin", "Mountains", "Mountains"],
            "station_corridor": ["edge", "", "edge", ""],
            "sta_lon": [-118.4, -118.1, -118.3, -118.0],
            "sta_lat": [34.0, 34.2, 34.1, 34.25],
        }
    )
    inside_fig = scatterplot(
        metrics,
        indep="distance",
        dep="PGA",
        value_col="log2_residual",
        passband="1-2",
        model="cvmsi",
        station_region_col="mapped_region_type",
        station_regions="Basin",
        fit="linear",
        showfig=False,
    )
    assert "Stations in Basin" in inside_fig.axes[0].get_title()
    outside_fig = scatterplot(
        metrics,
        indep="distance",
        dep=["PGA", "PGV"],
        value_col="log2_residual",
        passband="1-2",
        model="cvmsi",
        station_region_col="mapped_region_type",
        station_regions="Basin",
        station_region_relation="outside",
        fit="point-to-point",
        showfig=False,
    )
    assert "Stations outside Basin" in outside_fig.axes[0].get_title()
    outputs = [
        boxplot(
            metrics,
            tmp_path / "subset_boxplot.png",
            dep=["PGA", "PGV"],
            indep="mapped_region_type",
            value_col="observed",
            passband="1-2",
            station_corridor_col="station_corridor",
            station_corridors="edge",
        ),
        plot_residuals_vs_distance(
            metrics,
            tmp_path / "subset_trend.png",
            y_col="log2_residual",
            fit_method="best",
            station_region_col="mapped_region_type",
            station_regions="Basin",
            station_region_relation="both",
        ),
        plot_station_metric_map(
            metrics,
            tmp_path / "subset_map.png",
            value_col="log2_residual",
            lon_col="sta_lon",
            lat_col="sta_lat",
            add_basemap=False,
            station_region_col="mapped_region_type",
            station_regions="Basin",
        ),
    ]
    for output in outputs:
        _assert_png(output)


def _waveform_records() -> pd.DataFrame:
    """Build compact waveform records for figure tests."""

    time = np.linspace(0.0, 8.0, 201)
    rows = []
    for idx, station in enumerate(["S1", "S2", "S3"]):
        trace = np.sin(time * (1.0 + 0.1 * idx)) * np.exp(-time / 18.0)
        rows.append(
            {
                "event_id": "E1",
                "station": station,
                "component": "Z",
                "trace": trace,
                "observed": trace,
                "synthetic": 0.85 * np.sin(time * (1.0 + 0.1 * idx) + 0.15) * np.exp(-time / 18.0),
                "dt": float(time[1] - time[0]),
                "sta_lon": -118.4 + idx * 0.15,
                "sta_lat": 34.0 + idx * 0.1,
                "event_lon": -118.25,
                "event_lat": 34.08,
                "distance_km": 20.0 + idx * 15.0,
                "azimuth_deg": 45.0 + idx * 60.0,
                "group": "A" if idx < 2 else "B",
            }
        )
    return pd.DataFrame(rows)


def _metric_rows() -> pd.DataFrame:
    """Build compact metric rows for figure tests."""

    return pd.DataFrame(
        {
            "model": ["m1", "m1", "m2", "m2"],
            "metric": ["PGA", "PSA", "PGA", "PSA"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec", "1-2 sec"],
            "station": ["S1", "S2", "S1", "S2"],
            "event_id": ["E1", "E1", "E1", "E1"],
            "residual": [0.2, -0.1, 0.05, -0.2],
            "score": [8.0, 7.0, 9.0, 6.5],
            "log2_residual": [0.25, -0.15, 0.1, -0.3],
            "value_obs": [2.0, 3.0, 2.2, 3.1],
            "value_syn": [1.7, 3.2, 2.0, 3.4],
            "distance_km": [20.0, 35.0, 20.0, 35.0],
            "azimuth_deg": [45.0, 120.0, 45.0, 120.0],
            "depth_km": [8.0, 8.0, 10.0, 10.0],
            "period_s": [1.0, 2.0, 1.0, 2.0],
            "Vs30": [400.0, 650.0, 400.0, 650.0],
            "geology_class": ["basin", "rock", "basin", "rock"],
            "sta_lon": [-118.4, -118.1, -118.4, -118.1],
            "sta_lat": [34.0, 34.2, 34.0, 34.2],
            "improvement": [0.1, 0.2, -0.1, 0.05],
        }
    )


def test_qc_context_and_waveform_figures(tmp_path: Path) -> None:
    """QC, context, and waveform figure families should write outputs."""

    records = _waveform_records()
    qc = pd.DataFrame(
        {
            "stage": ["raw", "raw", "manual", "manual"],
            "qc_status": ["pass", "fail", "pass", "fail"],
            "qc_reason": ["", "missing_component", "", "low_snr"],
            "component": ["Z", "N", "Z", "E"],
        }
    )
    availability = pd.DataFrame(
        {
            "event_id": ["E1", "E1", "E2"],
            "station": ["S1", "S2", "S1"],
            "observed_available": [True, False, True],
            "synthetic_available": [True, True, False],
        }
    )
    event_station_retention = pd.DataFrame(
        {
            "event_id": ["E1", "E1", "E2"],
            "station": ["S1", "S2", "S1"],
            "total_pairs": [12, 12, 12],
            "retained_pairs": [12, 6, 9],
            "retention_percent": [100.0, 50.0, 75.0],
        }
    )
    station_meta = pd.DataFrame({"station": ["S1", "S2"], "network": ["AA", "BB"], "lon": [-118.4, -118.1], "lat": [34.0, 34.2]})
    event_meta = pd.DataFrame({"event_id": ["E1", "E2"], "event_lon": [-118.25, -118.0], "event_lat": [34.08, 34.25], "magnitude": [4.2, 4.8], "strike": [120.0, 220.0], "dip": [45.0, 50.0], "rake": [90.0, 10.0]})
    qc_map = records.assign(qc_status=["pass", "fail", "pass"])

    outputs = [
        plot_retention_summary(qc, tmp_path / "retention.png"),
        plot_data_synthetic_availability(availability, tmp_path / "availability.png"),
        plot_event_station_retention_heatmap(event_station_retention, tmp_path / "event_station_retention.png"),
        plot_post_qc_station_event_map(qc_map, tmp_path / "post_qc_map.png", add_basemap=False),
        plot_qc_drop_cause_diagnostics(qc, tmp_path / "drop_causes.png"),
        plot_trace_inventory_samples(records.assign(qc_status=["pass", "fail", "pass"]), tmp_path / "trace_samples.png"),
        plot_event_magnitude_map(event_meta, tmp_path / "event_magnitudes.png", add_basemap=False),
        plot_station_event_network_map(station_meta, event_meta, tmp_path / "network_map.png", add_basemap=False),
        plot_station_event_beachball_map(event_meta, tmp_path / "beachballs.png", stations_df=station_meta, add_basemap=False),
        plot_event_trace_comparison(records, tmp_path / "trace_comparison.png"),
        plot_station_event_waveform_map(records, tmp_path / "waveform_map.png", add_basemap=False),
        plot_event_radial_trace_section(records, tmp_path / "radial_section.png", add_basemap=False),
        plot_waveform_overlay_matrix(records, tmp_path / "overlay_matrix.png", add_basemap=False),
    ]
    for output in outputs:
        _assert_png(output)
    beachball_fig = plot_station_event_beachball_map(event_meta, stations_df=station_meta, add_basemap=False, showfig=False)
    assert len(beachball_fig.axes) >= 2
    assert beachball_fig.axes[-1].get_ylabel() == "Magnitude"
    plt.close(beachball_fig)


def test_qc_figures_write_optional_row_sidecars(tmp_path: Path) -> None:
    """Direct QC plotting entry points should expose plotted-row sidecars."""

    qc = pd.DataFrame(
        {
            "stage": ["window", "window", "snr"],
            "qc_status": ["pass", "fail", "fail"],
            "qc_reason": ["", "low_snr", "missing_trace"],
        }
    )
    pair_retention = pd.DataFrame(
        {
            "metric": ["PGA", "PGV"],
            "passband": ["1-2 sec", "1-2 sec"],
            "total_pairs": [10, 10],
            "retained_pairs": [8, 7],
            "retention_percent": [80.0, 70.0],
        }
    )
    event_station_retention = pd.DataFrame(
        {
            "event_id": ["E1", "E1", "E2"],
            "station": ["S1", "S2", "S1"],
            "total_pairs": [12, 12, 12],
            "retained_pairs": [12, 6, 9],
            "retention_percent": [100.0, 50.0, 75.0],
        }
    )
    qc_map = pd.DataFrame(
        {
            "event_id": ["E1", "E1", "E2"],
            "station": ["S1", "S2", "S1"],
            "sta_lon": [-118.2, -118.1, -118.3],
            "sta_lat": [34.1, 34.2, 34.15],
            "event_lon": [-118.0, -118.0, -118.4],
            "event_lat": [34.0, 34.0, 34.3],
            "qc_status": ["pass", "fail", "pass"],
        }
    )
    trace_samples = _waveform_records().assign(qc_status=["pass", "fail", "pass"])

    sidecar_dir = tmp_path / "sidecars"
    figures = [
        plot_retention_summary(
            pair_retention,
            tmp_path / "pair_retention.png",
            write_sidecar=True,
            sidecar_rows=1,
            sidecar_dir=sidecar_dir,
        ),
        plot_event_station_retention_heatmap(
            event_station_retention,
            tmp_path / "event_station.png",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_post_qc_station_event_map(
            qc_map,
            tmp_path / "post_qc.png",
            add_basemap=False,
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_qc_drop_cause_diagnostics(
            qc,
            tmp_path / "drop_causes.png",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_trace_inventory_samples(
            trace_samples,
            tmp_path / "trace_samples.png",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
    ]
    for figure in figures:
        _assert_png(figure.spatial_vtk_saved_path)
        sidecar = sidecar_dir / f"{figure.spatial_vtk_saved_path.stem}.csv"
        metadata_path = sidecar.with_suffix(".json")
        assert sidecar.exists()
        assert metadata_path.exists()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["plot_row_count"] >= metadata["written_row_count"] >= 1
        assert metadata["sidecar"] == str(sidecar)

    pair_sidecar = pd.read_csv(sidecar_dir / "pair_retention.csv")
    pair_metadata = json.loads((sidecar_dir / "pair_retention.json").read_text(encoding="utf-8"))
    assert len(pair_sidecar) == 1
    assert pair_metadata["plot"] == "pair_retention_summary"
    post_qc_sidecar = pd.read_csv(sidecar_dir / "post_qc.csv")
    assert "_retained" in post_qc_sidecar.columns
    trace_metadata = json.loads((sidecar_dir / "trace_samples.json").read_text(encoding="utf-8"))
    assert trace_metadata["figure_type"] == "trace_inventory_samples"
    assert trace_metadata["plot_row_count"] == 3
    assert trace_metadata["written_row_count"] == 2


def test_qc_availability_and_retention_heatmaps_have_distinct_default_outputs(tmp_path: Path) -> None:
    """Config-backed QC heatmaps should not overwrite each other."""

    cfg = SpatialVTKConfig(
        tmp_path / "config.yaml",
        tmp_path,
        {
            "outputs": {
                "root": str(tmp_path / "outputs"),
                "figures": str(tmp_path / "outputs" / "figures"),
            }
        },
    ).activate()
    availability = pd.DataFrame(
        {
            "event_id": ["E1", "E1", "E2"],
            "station": ["S1", "S2", "S1"],
            "observed_available": [True, False, True],
            "synthetic_available": [True, True, False],
        }
    )
    event_station_retention = pd.DataFrame(
        {
            "event_id": ["E1", "E1", "E2"],
            "station": ["S1", "S2", "S1"],
            "total_pairs": [12, 12, 12],
            "retained_pairs": [12, 6, 9],
            "retention_percent": [100.0, 50.0, 75.0],
        }
    )

    try:
        availability_fig = plot_data_synthetic_availability(availability, showfig=False, savefig=True)
        retention_fig = plot_event_station_retention_heatmap(event_station_retention, showfig=False, savefig=True)
        availability_path = Path(availability_fig.spatial_vtk_saved_path)
        retention_path = Path(retention_fig.spatial_vtk_saved_path)
    finally:
        clear_active_config()

    assert cfg.root_dir == tmp_path
    assert availability_path.name == "data_synthetic_availability.png"
    assert retention_path.name == "event_station_retention.png"
    assert availability_path != retention_path
    _assert_png(availability_path)
    _assert_png(retention_path)


def test_metric_and_spatial_figure_families(tmp_path: Path) -> None:
    """Metric trends, model comparisons, spatial plots, and maps should write outputs."""

    metrics = _metric_rows()
    summary = metrics.groupby(["model", "metric", "band"], as_index=False).agg(med_log2_residual=("log2_residual", "median"), med_value_obs=("value_obs", "median"), score=("score", "median"))
    winners = pd.DataFrame({"metric": ["PGA", "PSA"], "band": ["1-2 sec", "1-2 sec"], "winner": ["m2", "m1"]})
    spectra = pd.DataFrame({"period_s": [0.5, 1.0, 2.0, 0.5, 1.0, 2.0], "amplitude": [1.0, 1.4, 0.7, 0.9, 1.2, 0.6], "series": ["obs", "obs", "obs", "syn", "syn", "syn"]})
    spectrogram = pd.DataFrame({"time_s": np.repeat([0.0, 1.0, 2.0], 3), "period_s": [0.5, 1.0, 2.0] * 3, "amplitude": np.linspace(0.2, 1.0, 9)})
    path_summary = pd.DataFrame({"distance_bin_km": [0.0, 20.0, 0.0, 20.0], "azimuth_bin_deg": [0.0, 0.0, 90.0, 90.0], "mean_residual": [0.1, -0.1, 0.2, -0.2]})
    grid = pd.DataFrame({"lon": [-118.4, -118.2, -118.4, -118.2], "lat": [34.0, 34.0, 34.2, 34.2], "residual": [0.1, -0.2, 0.3, -0.1]})
    observed_wide = pd.DataFrame({"distance_km": [10.0, 25.0, 40.0], "pgv": [0.4, 0.7, 0.6], "band": ["1-2 sec", "1-2 sec", "1-2 sec"]})
    path_overlay = pd.DataFrame(
        {
            "event_lon": [-118.5, -118.45],
            "event_lat": [34.05, 34.18],
            "lon": [-118.4, -118.1],
            "lat": [34.0, 34.2],
        }
    )

    outputs = [
        plot_metric_trend(metrics, tmp_path / "metric_trend.png", x_col="distance_km", y_col="log2_residual"),
        plot_residuals_vs_distance(metrics, tmp_path / "resid_distance.png"),
        plot_psa_period_curve(metrics, tmp_path / "psa_period.png"),
        plot_period_spectra(spectra, tmp_path / "spectra.png"),
        plot_period_score_distribution(metrics.assign(passband=""), tmp_path / "period_distribution.png"),
        plot_period_spectrogram(spectrogram, tmp_path / "spectrogram.png"),
        plot_vs30_scatter(metrics, tmp_path / "vs30.png"),
        plot_geology_boxplot(metrics, tmp_path / "geology.png"),
        plot_model_metric_heatmap(summary, tmp_path / "model_heatmap.png", value_col="med_log2_residual"),
        plot_winner_heatmap(winners, tmp_path / "winner_heatmap.png"),
        plot_band_score_distribution(metrics, tmp_path / "band_distribution.png"),
        plot_azimuthal_residuals(metrics, tmp_path / "azimuthal.png"),
        plot_path_bin_summary(path_summary, tmp_path / "path_bins.png"),
        plot_residual_correlation(metrics.rename(columns={"Vs30": "feature_value"}), tmp_path / "residual_correlation.png"),
        scatterplot(metrics, tmp_path / "scatter_long.png", indep="vs30", dep=["pga", "psa"], value_col="log2_residual", model="m1", passband="1-2", colorby="dep", cmap=["r", "b"], fit="point-to-point"),
        scatterplot(observed_wide, tmp_path / "scatter_wide.png", indep="distance", dep="pgv", passband="1-2", fit="linear", data_label="Observed"),
        plot_polar_residuals(metrics, tmp_path / "polar.png"),
        plot_station_metric_map(metrics, tmp_path / "station_metric_map.png", value_col="log2_residual", add_basemap=False),
        plot_station_metric_map(metrics, tmp_path / "station_metric_map_paths.png", value_col="log2_residual", records_df=path_overlay, add_basemap=False),
        plot_station_metric_map_by_period(metrics, tmp_path / "station_metric_map_by_period.png", value_col="log2_residual", add_basemap=False),
        plot_score_map(metrics, tmp_path / "score_map.png", add_basemap=False),
        plot_residual_grid(grid, tmp_path / "residual_grid.png", add_basemap=False),
        plot_metric_map_by_model(metrics, tmp_path / "map_by_model.png", value_col="value_obs", add_basemap=False),
        plot_model_improvement_map(metrics, tmp_path / "improvement_map.png", add_basemap=False),
    ]
    for output in outputs:
        _assert_png(output)


def test_model_metric_heatmap_accepts_raw_metrics_long_value_columns(tmp_path: Path) -> None:
    """Model-metric heatmaps should work from metrics_long without a summary value column."""

    metrics = _metric_rows()

    output = plot_model_metric_heatmap(metrics, tmp_path / "model_heatmap_from_long.png")

    _assert_png(output)


def test_period_spectra_accepts_non_psa_metric_column(tmp_path: Path) -> None:
    """Generic period spectra should not be filtered as PSA rows."""

    spectra = pd.DataFrame(
        {
            "metric": ["FAS", "FAS", "FAS", "FAS"],
            "period_s": [1.0, 2.0, 1.0, 2.0],
            "amplitude": [0.4, 0.8, 0.3, 0.6],
            "series": ["observed", "observed", "synthetic", "synthetic"],
        }
    )

    output = plot_period_spectra(spectra, tmp_path / "fas_spectra.png")

    _assert_png(output)


def test_direct_psa_period_plots_reject_passband_duplicated_rows(tmp_path: Path) -> None:
    """Direct PSA period plots should not silently count passbanded PSA duplicates."""

    duplicated = pd.DataFrame(
        {
            "event_id": ["E1", "E1"],
            "station": ["S1", "S1"],
            "model": ["m1", "m1"],
            "component": ["R", "R"],
            "metric": ["PSA", "PSA"],
            "band": ["1-2 sec", "2-3 sec"],
            "period_s": [1.0, 1.0],
            "log2_residual": [0.2, 0.4],
        }
    )

    message = "repeated across passbands"
    with pytest.raises(ValueError, match=message):
        plot_psa_period_curve(duplicated, tmp_path / "psa_curve.png", value_col="log2_residual")
    with pytest.raises(ValueError, match=message):
        plot_period_score_distribution(duplicated, tmp_path / "psa_distribution.png", score_col="log2_residual")


def test_direct_psa_period_plots_prefer_broadband_rows(tmp_path: Path) -> None:
    """Direct PSA period plots should use broadband rows when passband rows are present."""

    rows = pd.DataFrame(
        {
            "event_id": ["E1", "E1", "E1"],
            "station": ["S1", "S1", "S1"],
            "model": ["m1", "m1", "m1"],
            "component": ["R", "R", "R"],
            "metric": ["PSA", "PSA", "PSA"],
            "band": ["", "1-2 sec", "2-3 sec"],
            "period_s": [1.0, 1.0, 1.0],
            "log2_residual": [0.2, 0.4, -0.2],
        }
    )
    sidecar_dir = tmp_path / "sidecars"

    output = plot_psa_period_curve(
        rows,
        tmp_path / "psa_curve.png",
        value_col="log2_residual",
        write_sidecar=True,
        sidecar_dir=sidecar_dir,
    )

    _assert_png(output)
    metadata = json.loads((sidecar_dir / "psa_curve.json").read_text(encoding="utf-8"))
    source_rows = pd.read_csv(sidecar_dir / "psa_curve.source.csv")
    assert metadata["source_row_count"] == 1
    assert source_rows["band"].fillna("").tolist() == [""]
    assert source_rows["log2_residual"].tolist() == [0.2]


def test_direct_metric_plots_label_event_centered_residuals(tmp_path: Path) -> None:
    """Direct metric plots should identify event-mean-centered log2 residuals."""

    metrics = _metric_rows().assign(event_mean=[0.1, 0.1, 0.1, 0.1])

    trend = plot_metric_trend(
        metrics,
        tmp_path / "trend.png",
        x_col="distance_km",
        y_col="log2_residual",
        group_col=None,
    )
    band = plot_band_score_distribution(
        metrics,
        tmp_path / "band.png",
        score_col="log2_residual",
        color_col=None,
    )
    period = plot_psa_period_curve(
        metrics.assign(band=""),
        tmp_path / "period.png",
        value_col="log2_residual",
        group_col=None,
    )
    period_distribution = plot_period_score_distribution(
        metrics.assign(band=""),
        tmp_path / "period_distribution.png",
        score_col="log2_residual",
        color_col=None,
    )

    assert trend.axes[0].get_ylabel() == "Event-centered log2(observed / synthetic)"
    assert band.axes[0].get_ylabel() == "Event-centered log2(observed / synthetic)"
    assert period.axes[0].get_ylabel() == "Event-centered log2(observed / synthetic)"
    assert period_distribution.axes[0].get_ylabel() == "Event-centered log2(observed / synthetic)"


def test_public_metric_plots_apply_robust_outlier_limits(tmp_path: Path) -> None:
    """Extreme rows should not dominate plot axes or color scales by default."""

    count = 21
    rows = pd.DataFrame(
        {
            "event_id": [f"E{index:02d}" for index in range(count)],
            "station": [f"S{index:02d}" for index in range(count)],
            "metric": ["PGA"] * count,
            "band": ["1-2 sec"] * count,
            "model": ["m1"] * count,
            "component": ["Z"] * count,
            "distance_km": np.linspace(5.0, 105.0, count),
            "sta_lon": np.linspace(-118.5, -117.5, count),
            "sta_lat": np.linspace(33.6, 34.3, count),
            "log2_residual": [*np.linspace(-1.0, 1.0, count - 1), 100.0],
        }
    )

    trend = plot_metric_trend(
        rows,
        tmp_path / "trend_outlier.png",
        x_col="distance_km",
        y_col="log2_residual",
        group_col=None,
    )
    band = plot_band_score_distribution(
        rows,
        tmp_path / "band_outlier.png",
        score_col="log2_residual",
        color_col=None,
    )
    station_map = plot_station_metric_map(
        rows,
        tmp_path / "map_outlier.png",
        value_col="log2_residual",
        add_basemap=False,
    )

    assert max(abs(value) for value in trend.axes[0].get_ylim()) < 5.0
    assert max(abs(value) for value in band.axes[0].get_ylim()) < 5.0
    assert max(abs(value) for value in station_map.axes[0].collections[-1].get_clim()) < 5.0


def test_metric_maps_include_metric_value_titles_and_reserved_colorbar_space(tmp_path: Path) -> None:
    """Metric maps should identify the plotted value without cramped colorbars."""

    metrics = _metric_rows()
    model_map = plot_metric_map_by_model(
        metrics,
        tmp_path / "model_map_title.png",
        value_col="log2_residual",
        add_basemap=False,
    )
    period_map = plot_station_metric_map_by_period(
        metrics,
        tmp_path / "period_map_title.png",
        value_col="log2_residual",
        add_basemap=False,
    )

    model_title = model_map._suptitle.get_text()
    period_title = period_map._suptitle.get_text()
    assert "PGA, PSA" in model_title or "Log2" in model_title
    assert "log2(observed / synthetic)" in model_title
    assert "PSA" in period_title
    assert "PSA oscillator periods" in period_title

    model_colorbar_ax = model_map.axes[-1]
    period_colorbar_ax = period_map.axes[-1]
    assert model_colorbar_ax.get_position().y1 <= 0.70
    assert period_colorbar_ax.get_position().y1 <= 0.80


def test_spatial_metric_maps_write_optional_row_sidecars(tmp_path: Path) -> None:
    """Spatial metric map figures should optionally write plotted/source rows."""

    metrics = _metric_rows().assign(mapped_region_type=["keep", "drop", "keep", "drop"])
    path_overlay = pd.DataFrame(
        {
            "event_lon": [-118.5, -118.45],
            "event_lat": [34.05, 34.18],
            "lon": [-118.4, -118.1],
            "lat": [34.0, 34.2],
        }
    )
    grid = pd.DataFrame({"lon": [-118.4, -118.2, -118.4, -118.2], "lat": [34.0, 34.0, 34.2, 34.2], "residual": [0.1, -0.2, 0.3, -0.1]})
    sidecar_dir = tmp_path / "sidecars"

    outputs = [
        plot_station_metric_map(
            metrics,
            tmp_path / "station_metric_map.png",
            value_col="log2_residual",
            records_df=path_overlay,
            add_basemap=False,
            station_region_col="mapped_region_type",
            station_regions="keep",
            write_sidecar=True,
            sidecar_rows=3,
            sidecar_dir=sidecar_dir,
        ),
        plot_station_metric_map_by_period(
            metrics,
            tmp_path / "station_metric_map_by_period.png",
            value_col="log2_residual",
            add_basemap=False,
            station_region_col="mapped_region_type",
            station_regions="keep",
            write_sidecar=True,
            sidecar_rows=3,
            sidecar_dir=sidecar_dir,
        ),
        plot_residual_grid(
            grid,
            tmp_path / "residual_grid.png",
            add_basemap=False,
            write_sidecar=True,
            sidecar_rows=3,
            sidecar_dir=sidecar_dir,
        ),
        plot_metric_map_by_model(
            metrics,
            tmp_path / "map_by_model.png",
            value_col="value_obs",
            add_basemap=False,
            station_region_col="mapped_region_type",
            station_regions="keep",
            write_sidecar=True,
            sidecar_rows=3,
            sidecar_dir=sidecar_dir,
        ),
        plot_model_improvement_map(
            metrics.assign(improvement=[0.1, -0.2, 0.3, 0.0]),
            tmp_path / "improvement_map.png",
            add_basemap=False,
            write_sidecar=True,
            sidecar_rows=3,
            sidecar_dir=sidecar_dir,
        ),
    ]
    for output in outputs:
        _assert_png(output)

    station_sidecar = sidecar_dir / "station_metric_map.csv"
    station_metadata = json.loads((sidecar_dir / "station_metric_map.json").read_text(encoding="utf-8"))
    station_rows = pd.read_csv(station_sidecar)
    selected_metric_rows = int(metrics["mapped_region_type"].eq("keep").sum())
    assert station_metadata["plot_row_count"] == selected_metric_rows + len(path_overlay)
    assert station_metadata["written_row_count"] == 3
    assert station_metadata["source_row_count"] == selected_metric_rows
    assert set(station_rows["_figure_layer"]).issubset({"metric", "record"})
    station_source = pd.read_csv(sidecar_dir / "station_metric_map.source.csv")
    assert set(station_source["mapped_region_type"]) == {"keep"}

    for stem in ("station_metric_map_by_period", "map_by_model"):
        source_rows = pd.read_csv(sidecar_dir / f"{stem}.source.csv")
        metadata = json.loads((sidecar_dir / f"{stem}.json").read_text(encoding="utf-8"))
        assert metadata["source_row_count"] == selected_metric_rows
        assert set(source_rows["mapped_region_type"]) == {"keep"}

    residual_metadata = json.loads((sidecar_dir / "residual_grid.json").read_text(encoding="utf-8"))
    assert residual_metadata["figure_type"] == "residual_grid"
    assert residual_metadata["source_row_count"] == len(grid)
    assert residual_metadata["written_row_count"] <= 3


def test_metric_plot_functions_write_optional_row_sidecars(tmp_path: Path) -> None:
    """Direct metric plotting functions should write plotted/source row sidecars."""

    metrics = _metric_rows()
    summary = metrics.groupby(["model", "metric", "band"], as_index=False).agg(med_log2_residual=("log2_residual", "median"), score=("score", "median"))
    winners = pd.DataFrame({"metric": ["PGA", "PSA"], "band": ["1-2 sec", "1-2 sec"], "winner": ["m2", "m1"]})
    spectrogram = pd.DataFrame({"time_s": np.repeat([0.0, 1.0, 2.0], 3), "period_s": [0.5, 1.0, 2.0] * 3, "amplitude": np.linspace(0.2, 1.0, 9)})
    sidecar_dir = tmp_path / "metric_sidecars"

    outputs = [
        plot_residuals_vs_distance(
            metrics,
            tmp_path / "resid_distance.png",
            y_col="log2_residual",
            group_col="metric",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_score_trends(
            metrics,
            tmp_path / "score_trends.png",
            score_col="score",
            group_col="metric",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_model_metric_heatmap(
            summary,
            tmp_path / "model_heatmap.png",
            value_col="med_log2_residual",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_winner_heatmap(
            winners,
            tmp_path / "winner_heatmap.png",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_band_score_distribution(
            metrics,
            tmp_path / "band_distribution.png",
            score_col="log2_residual",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_psa_period_curve(
            metrics,
            tmp_path / "psa_period_curve.png",
            value_col="log2_residual",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_period_score_distribution(
            metrics,
            tmp_path / "period_distribution.png",
            score_col="log2_residual",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_period_spectrogram(
            spectrogram,
            tmp_path / "period_spectrogram.png",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_vs30_scatter(
            metrics,
            tmp_path / "vs30.png",
            value_col="log2_residual",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_geology_boxplot(
            metrics,
            tmp_path / "geology.png",
            value_col="log2_residual",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
    ]
    for output in outputs:
        _assert_png(output)

    expected_types = {
        "resid_distance": "metric_trend",
        "score_trends": "metric_trend",
        "model_heatmap": "model_metric_heatmap",
        "winner_heatmap": "winner_heatmap",
        "band_distribution": "band_score_distribution",
        "psa_period_curve": "psa_period_curve",
        "period_distribution": "period_score_distribution",
        "period_spectrogram": "period_spectrogram",
        "vs30": "metric_trend",
        "geology": "geology_boxplot",
    }
    for stem, figure_type in expected_types.items():
        sidecar = sidecar_dir / f"{stem}.csv"
        metadata_path = sidecar.with_suffix(".json")
        source_sidecar = sidecar_dir / f"{stem}.source.csv"
        assert sidecar.exists()
        assert metadata_path.exists()
        assert source_sidecar.exists()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["figure_type"] == figure_type
        assert metadata["plot_row_count"] >= metadata["written_row_count"]
        assert metadata["source_row_count"] >= metadata["source_written_row_count"]
        if stem in {"psa_period_curve", "period_distribution"}:
            source_rows = pd.read_csv(source_sidecar)
            assert set(source_rows["metric"]) == {"PSA"}
            assert metadata["source_row_count"] == int(metrics["metric"].eq("PSA").sum())
            assert metadata["source_metric_count"] == 1


def test_spatial_metric_plot_functions_write_optional_row_sidecars(tmp_path: Path) -> None:
    """Direct spatial metric plots should write audit rows for plotted data."""

    metrics = _metric_rows()
    path_summary = pd.DataFrame({"distance_bin_km": [0.0, 20.0, 0.0, 20.0], "azimuth_bin_deg": [0.0, 0.0, 90.0, 90.0], "mean_residual": [0.1, -0.1, 0.2, -0.2]})
    sidecar_dir = tmp_path / "spatial_plot_sidecars"

    outputs = [
        scatterplot(
            metrics,
            tmp_path / "scatter_long.png",
            indep="distance",
            dep=["pga", "psa"],
            value_col="log2_residual",
            model="m1",
            passband="1-2",
            colorby="dep",
            fit="point-to-point",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        boxplot(
            metrics,
            tmp_path / "boxplot.png",
            dep=["PGA", "PSA"],
            indep="geology_class",
            value_col="log2_residual",
            model="m1",
            passband="1-2",
            table=True,
            compare_to="basin",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        heatmap(
            metrics,
            tmp_path / "heatmap.png",
            dep=["PGA", "PSA"],
            indep="geology_class",
            value_col="log2_residual",
            model="m1",
            passband="1-2",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_azimuthal_residuals(
            metrics,
            tmp_path / "azimuthal.png",
            value_col="log2_residual",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_path_bin_summary(
            path_summary,
            tmp_path / "path_bins.png",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_residual_correlation(
            metrics.rename(columns={"Vs30": "feature_value"}),
            tmp_path / "residual_correlation.png",
            y_col="log2_residual",
            group_col="metric",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_polar_residuals(
            metrics,
            tmp_path / "polar.png",
            value_col="log2_residual",
            facet_col="metric",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
        plot_geology_contrast(
            metrics,
            tmp_path / "geology_contrast.png",
            group_col="geology_class",
            left_values=("basin",),
            right_values=("rock",),
            value_col="log2_residual",
            write_sidecar=True,
            sidecar_rows=2,
            sidecar_dir=sidecar_dir,
        ),
    ]
    for output in outputs:
        _assert_png(output)

    expected_types = {
        "scatter_long": "scatterplot",
        "boxplot": "boxplot",
        "heatmap": "heatmap",
        "azimuthal": "azimuthal_residuals",
        "path_bins": "path_bin_summary",
        "residual_correlation": "residual_correlation",
        "polar": "polar_residuals",
        "geology_contrast": "geology_contrast",
    }
    for stem, figure_type in expected_types.items():
        sidecar = sidecar_dir / f"{stem}.csv"
        metadata_path = sidecar.with_suffix(".json")
        source_sidecar = sidecar_dir / f"{stem}.source.csv"
        assert sidecar.exists()
        assert metadata_path.exists()
        assert source_sidecar.exists()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["figure_type"] == figure_type
        assert metadata["plot_row_count"] >= metadata["written_row_count"]
        assert metadata["source_row_count"] >= metadata["source_written_row_count"]
    heatmap_rows = pd.read_csv(sidecar_dir / "heatmap.csv")
    assert {"geology_class", "dep", "_plot_value"}.issubset(heatmap_rows.columns)
    geology_rows = pd.read_csv(sidecar_dir / "geology_contrast.csv")
    assert "_plot_group" in geology_rows.columns
