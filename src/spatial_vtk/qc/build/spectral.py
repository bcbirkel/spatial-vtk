"""Spectral QC helpers for PSA and FAS period support.

Purpose
-------
This module evaluates which spectral periods are usable for observed and
synthetic traces without requiring a pre-event noise window. It uses relative
spectral amplitude, physical period support, and synthetic max-frequency
limits.

Usage examples
--------------
Find valid FAS periods for a synthetic trace:
  ``qc = qc_fas_periods(trace, dt=0.02, periods_s=[1, 2, 5], synthetic_max_frequency_hz=1.0, source="synthetic")``
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np
import pandas as pd


def spectral_relative_amplitude_mask(
    periods_s: Sequence[float],
    amplitudes: Sequence[float],
    *,
    threshold: float = 0.25,
    min_period_s: float | None = None,
    max_period_s: float | None = None,
    disable_relative_amplitude_qc: bool = False,
) -> np.ndarray:
    """Return valid periods based on relative spectral amplitude.

    Parameters
    ----------
    periods_s
        Period grid in seconds.
    amplitudes
        Spectral amplitudes aligned to ``periods_s``.
    threshold
        Minimum fraction of the maximum finite amplitude required.
    min_period_s, max_period_s
        Optional hard period bounds.
    disable_relative_amplitude_qc
        Whether to skip the relative-amplitude threshold.

    Returns
    -------
    numpy.ndarray
        Boolean validity mask.
    """

    periods = np.asarray(periods_s, dtype=float)
    amps = np.asarray(amplitudes, dtype=float)
    if periods.shape != amps.shape:
        raise ValueError("periods_s and amplitudes must have matching shapes.")
    valid = np.isfinite(periods) & (periods > 0.0) & np.isfinite(amps) & (amps >= 0.0)
    if min_period_s is not None:
        valid &= periods >= float(min_period_s)
    if max_period_s is not None:
        valid &= periods <= float(max_period_s)
    if not bool(disable_relative_amplitude_qc):
        finite_amps = amps[valid]
        max_amp = float(np.nanmax(finite_amps)) if finite_amps.size else np.nan
        if not np.isfinite(max_amp) or max_amp <= 0.0:
            return np.zeros(periods.shape, dtype=bool)
        valid &= amps >= (float(threshold) * max_amp)
    return valid


def spectral_valid_period_bounds(periods_s: Sequence[float], valid_mask: Sequence[bool]) -> tuple[float | None, float | None]:
    """Return minimum and maximum valid period from a validity mask."""

    periods = np.asarray(periods_s, dtype=float)
    mask = np.asarray(valid_mask, dtype=bool)
    if periods.shape != mask.shape:
        raise ValueError("periods_s and valid_mask must have matching shapes.")
    selected = periods[mask & np.isfinite(periods)]
    if selected.size == 0:
        return None, None
    return float(np.min(selected)), float(np.max(selected))


def qc_fas_periods(
    trace: Any,
    *,
    dt: float,
    periods_s: Sequence[float],
    threshold: float = 0.25,
    min_cycles_in_record: float = 3.0,
    synthetic_max_frequency_hz: float | None = None,
    source: str = "observed",
    disable_relative_amplitude_qc: bool = False,
) -> pd.DataFrame:
    """QC FAS values on a requested period grid.

    Parameters
    ----------
    trace
        Waveform samples or trace-like object.
    dt
        Sample interval in seconds.
    periods_s
        Requested periods.
    threshold
        Relative spectral support threshold.
    min_cycles_in_record
        Minimum cycles required in the record.
    synthetic_max_frequency_hz
        Optional synthetic maximum valid frequency.
    source
        ``"observed"`` or ``"synthetic"`` for status reasons.
    disable_relative_amplitude_qc
        Whether to skip relative amplitude support.

    Returns
    -------
    pandas.DataFrame
        Period-level QC rows with FAS amplitudes and pass/fail status.
    """

    samples = _trace_data(trace)
    periods = np.asarray(periods_s, dtype=float)
    amplitudes = _fas_at_periods(samples, float(dt), periods)
    min_period, max_period = _period_support_bounds(
        npts=samples.size,
        dt=float(dt),
        min_cycles_in_record=min_cycles_in_record,
        synthetic_max_frequency_hz=synthetic_max_frequency_hz if str(source).lower() == "synthetic" else None,
    )
    mask = spectral_relative_amplitude_mask(
        periods,
        amplitudes,
        threshold=threshold,
        min_period_s=min_period,
        max_period_s=max_period,
        disable_relative_amplitude_qc=disable_relative_amplitude_qc,
    )
    return _qc_frame("FAS", periods, amplitudes, mask, min_period=min_period, max_period=max_period)


def qc_psa_periods(
    trace: Any,
    *,
    dt: float,
    periods_s: Sequence[float],
    threshold: float = 0.25,
    damping: float = 0.05,
    min_cycles_in_record: float = 3.0,
    synthetic_max_frequency_hz: float | None = None,
    source: str = "observed",
    disable_relative_amplitude_qc: bool = False,
) -> pd.DataFrame:
    """QC PSA values on a requested period grid."""

    from spatial_vtk.metrics.calculate.gof import _psa_newmark

    samples = _trace_data(trace)
    periods = np.asarray(periods_s, dtype=float)
    amplitudes = np.array([
        _psa_newmark(samples, float(dt), 1.0 / period, zeta=float(damping)) if np.isfinite(period) and period > 0.0 else np.nan
        for period in periods
    ], dtype=float)
    min_period, max_period = _period_support_bounds(
        npts=samples.size,
        dt=float(dt),
        min_cycles_in_record=min_cycles_in_record,
        synthetic_max_frequency_hz=synthetic_max_frequency_hz if str(source).lower() == "synthetic" else None,
    )
    mask = spectral_relative_amplitude_mask(
        periods,
        amplitudes,
        threshold=threshold,
        min_period_s=min_period,
        max_period_s=max_period,
        disable_relative_amplitude_qc=disable_relative_amplitude_qc,
    )
    return _qc_frame("PSA", periods, amplitudes, mask, min_period=min_period, max_period=max_period)


def _trace_data(trace: Any) -> np.ndarray:
    """Return trace samples as a one-dimensional array."""

    data = trace.get("data") if isinstance(trace, dict) else getattr(trace, "data", trace)
    samples = np.asarray(data, dtype=float).reshape(-1)
    if samples.size == 0:
        raise ValueError("trace must contain at least one sample.")
    return samples


def _fas_at_periods(samples: np.ndarray, dt: float, periods: np.ndarray) -> np.ndarray:
    """Interpolate one-sided Fourier amplitude spectrum onto periods."""

    if samples.size < 2:
        return np.full(periods.shape, np.nan, dtype=float)
    clean = np.nan_to_num(samples, nan=0.0, posinf=0.0, neginf=0.0)
    freqs = np.fft.rfftfreq(clean.size, d=float(dt))
    amp = np.abs(np.fft.rfft(clean)) / max(clean.size, 1)
    out = np.full(periods.shape, np.nan, dtype=float)
    valid = np.isfinite(periods) & (periods > 0.0)
    target_freqs = 1.0 / periods[valid]
    freq_mask = freqs > 0.0
    if np.count_nonzero(freq_mask) < 2:
        return out
    out[valid] = np.interp(target_freqs, freqs[freq_mask], amp[freq_mask], left=np.nan, right=np.nan)
    return out


def _period_support_bounds(
    *,
    npts: int,
    dt: float,
    min_cycles_in_record: float,
    synthetic_max_frequency_hz: float | None,
) -> tuple[float, float]:
    """Return physically supported period bounds."""

    min_period = max(2.0 * float(dt), (1.0 / float(synthetic_max_frequency_hz)) if synthetic_max_frequency_hz else 0.0)
    record_length_s = max(float(npts) * float(dt), float(dt))
    max_period = record_length_s / max(float(min_cycles_in_record), 1.0)
    return min_period, max_period


def _qc_frame(
    metric: str,
    periods: np.ndarray,
    amplitudes: np.ndarray,
    mask: np.ndarray,
    *,
    min_period: float,
    max_period: float,
) -> pd.DataFrame:
    """Build a period-level spectral QC table."""

    rows = []
    for period, amplitude, accepted in zip(periods, amplitudes, mask, strict=False):
        reason = ""
        if not bool(accepted):
            if not np.isfinite(period) or period <= 0.0:
                reason = "invalid_period"
            elif period < min_period:
                reason = "period_below_min_supported_period"
            elif period > max_period:
                reason = "insufficient_record_length_for_period"
            elif not np.isfinite(amplitude) or amplitude < 0.0:
                reason = "invalid_spectral_amplitude"
            else:
                reason = "below_relative_spectral_amplitude_threshold"
        rows.append(
            {
                "metric_group": "spectral",
                "metric": metric,
                "period_s": float(period) if np.isfinite(period) else np.nan,
                "spectral_amplitude": float(amplitude) if np.isfinite(amplitude) else np.nan,
                "qc_status": "pass" if bool(accepted) else "fail",
                "qc_reason": reason,
            }
        )
    return pd.DataFrame(rows)


__all__ = [
    "spectral_relative_amplitude_mask",
    "spectral_valid_period_bounds",
    "qc_fas_periods",
    "qc_psa_periods",
]
