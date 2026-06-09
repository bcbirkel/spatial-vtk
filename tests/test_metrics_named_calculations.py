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
    delay_corrected_cc,
    energy_duration,
    energy_intensity,
    original_cc,
    traveltime_delay,
)
from spatial_vtk.metrics.calculate.transforms import (
    anderson_2004_gof,
    ln_residual,
    log2_residual,
    olsen_mayhew_gof,
    residual,
)


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
