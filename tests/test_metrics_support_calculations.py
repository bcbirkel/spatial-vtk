from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spatial_vtk.metrics.calculate import (
    binned_numeric_midpoints,
    build_station_residual_table,
    calculate_amplitude_ratios,
    compute_amplitude_spectrum_vs_period,
    compute_paired_station_event_maxima,
    compute_period_spectrogram,
    compute_station_event_maxima,
    interpolate_period_spectrum,
    metric_residual_series,
    metric_stems_by_family,
    residual_metric_stems,
    score_metric_stems,
    station_mean_table,
    subset_period_range,
    summarize_long_metric_table,
    summarize_metric_scores,
)


def test_amplitude_summary_helpers_return_ratios_and_maxima() -> None:
    """Amplitude helpers should summarize traces without requiring file IO."""

    observed = np.array([0.0, 20.0, -4.0, 6.0])
    synthetic = np.array([0.0, 10.0, -2.0, 3.0])

    ratios = calculate_amplitude_ratios(observed, synthetic)
    assert ratios["max_amp_obs"] == pytest.approx(20.0)
    assert ratios["max_amp_syn"] == pytest.approx(10.0)
    assert ratios["max_amp_ratio"] == pytest.approx(2.0)
    assert ratios["rms_ratio"] == pytest.approx(np.sqrt(np.mean(observed**2)) / np.sqrt(np.mean(synthetic**2)))

    maxima = compute_station_event_maxima(observed)
    assert maxima["max_amplitude"] == pytest.approx(20.0)
    assert maxima["rms_amplitude"] > 0.0
    assert compute_paired_station_event_maxima(observed, synthetic)["max_amp_ratio"] == pytest.approx(2.0)


def test_period_spectrum_helpers_return_requested_period_outputs() -> None:
    """Spectrum helpers should expose period-domain arrays without plotting."""

    dt = 0.01
    time = np.arange(0.0, 4.0, dt)
    trace = np.sin(2.0 * np.pi * 1.0 * time)

    periods, amplitudes = compute_amplitude_spectrum_vs_period(trace, dt=dt)
    assert np.all(np.diff(periods) >= 0.0)
    assert periods[np.argmax(amplitudes)] == pytest.approx(1.0, abs=0.05)

    subset_periods, subset_amplitudes = subset_period_range(periods, amplitudes, min_period=0.5, max_period=2.0)
    assert subset_periods.min() >= 0.50
    assert subset_periods.max() <= 2.0
    assert subset_periods.size == subset_amplitudes.size

    interpolated = interpolate_period_spectrum(periods, amplitudes, [1.0, 2.0])
    assert interpolated.shape == (2,)
    assert np.isfinite(interpolated[0])

    spec_periods, bins, power = compute_period_spectrogram(trace, dt=dt, nfft=128, noverlap=64)
    assert spec_periods.ndim == 1
    assert bins.ndim == 1
    assert power.shape == (spec_periods.size, bins.size)


def test_wide_metric_summary_helpers_support_legacy_and_named_metrics() -> None:
    """Summary helpers should work on wide metric tables without plotting."""

    metrics = pd.DataFrame(
        {
            "simulation_model": ["m1", "m1", "m1"],
            "simulation_band": ["1-3s", "1-3s", "3-60s"],
            "station_name": ["AAA", "AAA", "BBB"],
            "station_longitude": [-118.0, -118.0, -117.5],
            "station_latitude": [34.0, 34.0, 34.5],
            "C5_obs": [4.0, 8.0, 2.0],
            "C5_syn": [2.0, 4.0, 2.0],
            "C5_score": [7.0, 8.0, 9.0],
            "PSA_T1.0_obs": [3.0, 6.0, 4.0],
            "PSA_T1.0_syn": [1.5, 3.0, 2.0],
            "PGA_obs": [4.0, 8.0, 2.0],
            "PGA_syn": [2.0, 4.0, 1.0],
        }
    )

    assert residual_metric_stems(metrics) == ["C5", "PSA_T1.0", "PGA"]
    assert score_metric_stems(metrics) == ["C5"]
    assert metric_stems_by_family(metrics, "psa") == ["PSA_T1.0"]
    assert metric_stems_by_family(metrics, "legacy") == ["C5"]
    assert metric_stems_by_family(metrics, "named") == ["PSA_T1.0", "PGA"]

    residual = metric_residual_series(metrics, "C5")
    assert residual is not None
    assert residual.iloc[0] == pytest.approx(1.0)

    station_table, residual_col = build_station_residual_table(metrics, "C5")
    assert station_table is not None
    assert residual_col == "C5_residual_log2"
    assert set(station_table.columns) == {"station", "station_lon", "station_lat", residual_col}
    assert station_table.loc[station_table["station"].eq("AAA"), residual_col].iloc[0] == pytest.approx(1.0)

    means = station_mean_table(metrics, value_columns=["C5_score"])
    assert means.loc[means["station"].eq("AAA"), "C5_score"].iloc[0] == pytest.approx(7.5)

    summary = summarize_metric_scores(metrics)
    assert {"simulation_model", "station_name", "simulation_band", "C5_score_mean", "C5_score_count"} <= set(summary.columns)

    bins, labels = binned_numeric_midpoints(pd.Series([1.0, 2.0, 3.0]), step=1.0)
    assert bins is not None
    assert labels is not None
    assert len(labels) == len(bins) - 1


def test_long_metric_summary_helper_uses_public_row_contract() -> None:
    """Long metric summaries should consume the new public row contract."""

    long_metrics = pd.DataFrame(
        {
            "model": ["m1", "m1", "m1"],
            "station": ["AAA", "AAA", "BBB"],
            "passband": ["1-3s", "1-3s", "1-3s"],
            "metric": ["PGA", "PGV", "PGA"],
            "log2_residual": [1.0, -0.5, 0.25],
        }
    )
    summary = summarize_long_metric_table(long_metrics)
    assert {"model", "station", "passband", "metric", "mean", "median", "std", "count"} <= set(summary.columns)
    assert summary.loc[summary["metric"].eq("PGA"), "count"].sum() == 2
