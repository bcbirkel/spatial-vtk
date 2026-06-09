from __future__ import annotations

import numpy as np
import pandas as pd

from spatial_vtk.metrics.calculate import (
    DEFAULT_PICKER,
    PhaseNetUnavailableError,
    calculate_metrics_for_pairs,
    normalize_pick_catalog,
    prepare_metric_residual_table,
    resolve_arrival_picker,
)
from spatial_vtk.metrics.plot import build_example_metric_summary, plot_example_metric_pairs
from spatial_vtk.spatial.calculate import build_path_table, rotate_ne_to_rt, rotate_rt_to_ne, summarize_residuals_by_path_bin
from spatial_vtk.spatial.map.path import plot_event_residual_map
from spatial_vtk.visualize.dashboard import build_dashboard_summaries


def test_metric_outputs_feed_dashboard_and_path_map(tmp_path):
    time = np.arange(0.0, 4.0, 0.01)
    observed = np.sin(2 * np.pi * 1.0 * time)
    synthetic = 1.2 * observed
    pairs = [
        {
            "event_id": "e1",
            "station": "S1",
            "model": "m1",
            "band": "1-2 sec",
            "sta_lat": 34.00,
            "sta_lon": -118.00,
            "event_lat": 34.10,
            "event_lon": -118.20,
            "observed": observed,
            "synthetic": synthetic,
            "dt": 0.01,
        },
        {
            "event_id": "e1",
            "station": "S2",
            "model": "m1",
            "band": "1-2 sec",
            "sta_lat": 34.08,
            "sta_lon": -118.08,
            "event_lat": 34.10,
            "event_lon": -118.20,
            "observed": observed,
            "synthetic": 0.8 * observed,
            "dt": 0.01,
        },
    ]

    wide = calculate_metrics_for_pairs(pairs, which=["C5"])
    assert {"C5_obs", "C5_syn", "C5_score"}.issubset(wide.columns)

    long = prepare_metric_residual_table(wide)
    assert {"metric", "residual", "distance_km", "azimuth_deg"}.issubset(long.columns)
    assert long["metric"].tolist() == ["C5", "C5"]

    summaries = build_dashboard_summaries(long)
    assert summaries["model_metric_band"].loc[0, "n"] == 2
    assert not summaries["station_rollup"].empty
    assert not summaries["path_hex"].empty

    path_table = build_path_table(long)
    path_summary = summarize_residuals_by_path_bin(path_table, distance_bin_km=20.0, azimuth_bin_deg=45.0)
    assert path_summary["n"].sum() == 2

    figure_path = plot_event_residual_map(long, tmp_path / "event_residual_map.png", event_id="e1", metric="C5", add_basemap=False)
    assert figure_path.exists()
    assert figure_path.stat().st_size > 0


def test_arrival_picks_metric_examples_and_rotation(tmp_path):
    assert DEFAULT_PICKER == "phasenet"
    try:
        resolved = resolve_arrival_picker()
    except PhaseNetUnavailableError as exc:
        assert "PhaseNet is the default arrival picker" in str(exc)
    else:
        assert "phasenet" in resolved.lower()

    picks = normalize_pick_catalog(
        pd.DataFrame(
            {
                "event_title": ["e1"],
                "Station": ["S1"],
                "Component": ["Z"],
                "phase_name": ["p"],
                "time_rel_s": [1.2],
                "prob": [0.9],
            }
        ),
        default_method="manual",
    )
    assert list(picks.columns)[0:4] == ["event_id", "station", "component", "phase"]
    assert picks.loc[0, "phase"] == "P"
    assert picks.loc[0, "method"] == "manual"

    summary = build_example_metric_summary()
    assert any(row["scenario"] == "identical" for row in summary)
    figure_path = plot_example_metric_pairs(tmp_path / "metric_examples.png", scenarios=["identical", "amplitude_scaled"])
    assert figure_path.exists()
    assert figure_path.stat().st_size > 0

    north = np.array([1.0, 0.0, -1.0])
    east = np.array([0.0, 1.0, 0.0])
    radial, transverse = rotate_ne_to_rt(north, east, backazimuth_deg=30.0)
    restored_north, restored_east = rotate_rt_to_ne(radial, transverse, backazimuth_deg=30.0)
    np.testing.assert_allclose(restored_north, north)
    np.testing.assert_allclose(restored_east, east)
