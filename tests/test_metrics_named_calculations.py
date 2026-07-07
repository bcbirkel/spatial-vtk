from __future__ import annotations

import math

import numpy as np
import pytest

from spatial_vtk.metrics.calculate import (
    CAV,
    FAS,
    PGA,
    PGD,
    PGV,
    PSA,
    arias_duration,
    arias_intensity,
    build_metric_value_row,
    build_spectral_metric_rows,
    compare_metric_values,
    delay_search_cap_s,
    delay_corrected_cc,
    energy_duration,
    energy_intensity,
    original_cc,
    phasenet_cycle_corrected_delay_metrics,
    traveltime_delay,
)
from spatial_vtk.metrics.calculate.transforms import (
    anderson_2004_gof,
    ln_residual,
    log2_residual,
    olsen_mayhew_gof,
    residual,
)
from spatial_vtk.metrics.calculate.gof import _psa_newmark, _psa_newmark_loop


def test_named_trace_metrics_return_finite_values() -> None:
    """Named scalar metrics should expose legacy C-metric concepts directly."""

    dt = 0.01
    time = np.arange(0.0, 5.0, dt)
    acceleration = 120.0 * np.sin(2.0 * np.pi * 1.0 * time)

    assert PGA(acceleration) == pytest.approx(120.0, rel=0.02)
    assert np.isfinite(PGV(acceleration, dt))
    assert np.isfinite(PGD(acceleration, dt))
    assert arias_intensity(acceleration, dt) > 0.0
    assert arias_duration(acceleration, dt) > 0.0
    assert energy_intensity(acceleration, dt) > 0.0
    assert energy_duration(acceleration, dt) > 0.0
    assert CAV(acceleration, dt) > 0.0


def test_named_spectral_metrics_follow_requested_period_grid() -> None:
    """PSA and FAS should return values aligned with requested periods."""

    dt = 0.01
    time = np.arange(0.0, 5.0, dt)
    acceleration = np.sin(2.0 * np.pi * 1.0 * time)
    periods = np.array([0.5, 1.0, 2.0])

    psa = PSA(acceleration, dt, periods)
    fas = FAS(acceleration, dt, periods=periods)

    assert psa.shape == periods.shape
    assert fas.shape == periods.shape
    assert np.all(np.isfinite(psa))
    assert np.all(np.isfinite(fas))
    assert fas[1] > fas[0]


def test_fast_psa_matches_newmark_fallback() -> None:
    """The optimized PSA filter should preserve Newmark response values."""

    dt = 0.01
    time = np.arange(0.0, 20.0, dt)
    acceleration = (
        0.7 * np.sin(2.0 * np.pi * 0.8 * time)
        + 0.2 * np.sin(2.0 * np.pi * 2.2 * time)
    )

    for period in (0.5, 1.0, 2.0, 5.0):
        fast = _psa_newmark(acceleration, dt, 1.0 / period)
        fallback = _psa_newmark_loop(acceleration, dt, 1.0 / period)
        assert fast == pytest.approx(fallback, rel=1e-9, abs=1e-9)


def test_public_delay_correction_uses_shift_needed_to_align_synthetic() -> None:
    """Public delay should be the shift applied to synthetic for alignment."""

    dt = 0.01
    time = np.arange(0.0, 5.0, dt)
    observed = np.sin(2.0 * np.pi * 1.0 * time)
    synthetic = np.roll(observed, 20)

    delay_s = traveltime_delay(observed, synthetic, dt, max_lag_s=0.5)
    assert delay_s == pytest.approx(0.2, abs=dt)
    assert original_cc(observed, synthetic) < 0.5
    assert delay_corrected_cc(observed, synthetic, dt, delay_s=delay_s) == pytest.approx(1.0, abs=1e-6)


def test_bounded_traveltime_delay_limits_full_trace_cycle_skips() -> None:
    """Bounded delay should avoid letting later waveform packets dominate."""

    dt = 0.01
    time = np.arange(0.0, 20.0, dt)

    def packet(center_s: float, amplitude: float, width_s: float = 0.45) -> np.ndarray:
        envelope = np.exp(-0.5 * ((time - center_s) / width_s) ** 2)
        return amplitude * envelope * np.sin(2.0 * np.pi * 1.0 * (time - center_s))

    observed = packet(4.0, 0.6) + packet(10.0, 1.4)
    synthetic = packet(4.2, 0.6) + packet(9.05, 1.6)

    legacy_delay = traveltime_delay(observed, synthetic, dt)
    bounded_delay = traveltime_delay(
        observed,
        synthetic,
        dt,
        method="bounded",
        period_min_s=1.0,
        period_max_s=2.0,
    )

    assert legacy_delay < -0.5
    assert abs(bounded_delay) <= delay_search_cap_s(dt, period_min_s=1.0)
    assert abs(bounded_delay) < abs(legacy_delay)


def test_bounded_delay_corrected_cc_uses_bounded_delay_estimate() -> None:
    """Delay-corrected correlation should forward bounded delay options."""

    dt = 0.01
    time = np.arange(0.0, 5.0, dt)
    observed = np.sin(2.0 * np.pi * 1.0 * time)
    synthetic = np.interp(time - 0.2, time, observed, left=0.0, right=0.0)

    delay_s = traveltime_delay(observed, synthetic, dt, method="bounded", period_min_s=1.0)
    assert delay_s == pytest.approx(0.2, abs=dt)
    assert delay_corrected_cc(observed, synthetic, dt, method="bounded", period_min_s=1.0) > 0.99


def test_phasenet_cycle_corrected_delay_searches_one_low_frequency_period() -> None:
    """Cycle correction should refine a P-pick delay within one passband period."""

    dt = 0.01
    time = np.arange(0.0, 8.0, dt)
    envelope = np.exp(-0.5 * ((time - 4.0) / 1.0) ** 2)
    observed = envelope * np.sin(2.0 * np.pi * 1.0 * time)
    synthetic = np.interp(time - 0.25, time, observed, left=0.0, right=0.0)

    result = phasenet_cycle_corrected_delay_metrics(
        observed,
        synthetic,
        dt,
        obs_pick_s=2.0,
        syn_pick_s=3.25,
        period_min_s=1.0,
        period_max_s=2.0,
    )

    assert result["p_pick_delay_s"] == pytest.approx(1.25)
    assert result["cycle_corrected_delay_s"] == pytest.approx(0.25, abs=dt)
    assert result["cycle_corrected_cc"] > 0.99


def test_metric_transforms_have_explicit_observed_over_synthetic_convention() -> None:
    """Comparison transforms should use the public observed/synthetic contract."""

    assert residual(4.0, 2.0) == pytest.approx(2.0)
    assert log2_residual(4.0, 2.0) == pytest.approx(1.0)
    assert ln_residual(4.0, 2.0) == pytest.approx(math.log(2.0))
    assert anderson_2004_gof(2.0, 2.0) == pytest.approx(10.0)
    assert olsen_mayhew_gof(2.0, 2.0) == pytest.approx(100.0)

    compared = compare_metric_values(
        4.0,
        2.0,
        transforms=("residual", "log2_residual", "ln_residual", "anderson_2004_gof", "olsen_mayhew_gof"),
    )
    assert set(compared) == {"residual", "log2_residual", "ln_residual", "anderson_2004_gof", "olsen_mayhew_gof"}


def test_metric_record_builders_include_requested_transform_columns() -> None:
    """Record helpers should produce long rows with scalar and period outputs."""

    row = build_metric_value_row(
        metric_group="amplitude",
        metric="PGA",
        value_obs=4.0,
        value_syn=2.0,
        event_id="e1",
        station="ABC",
        component="N",
        model="m1",
        passband="1-3s",
        transforms=("residual", "log2_residual"),
    )
    assert row["metric"] == "PGA"
    assert row["residual"] == pytest.approx(2.0)
    assert row["log2_residual"] == pytest.approx(1.0)
    assert np.isnan(row["anderson_2004_gof"])

    rows = build_spectral_metric_rows(
        metric="PSA",
        periods_s=[1.0, 2.0],
        values_obs=[4.0, 8.0],
        values_syn=[2.0, 4.0],
        station="ABC",
        transforms=("log2_residual",),
    )
    assert [item["period_s"] for item in rows] == [1.0, 2.0]
    assert [item["log2_residual"] for item in rows] == [pytest.approx(1.0), pytest.approx(1.0)]
