"""Period-domain spectrum calculations for metric diagnostics.

Purpose
-------
This module contains reusable spectrum helpers for workflows that need
period-axis amplitude spectra or spectrogram data without rendering figures.

Usage examples
--------------
Compute a period spectrum:
  ``periods, amplitudes = compute_amplitude_spectrum_vs_period(trace, dt=0.02)``
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from scipy import signal

from spatial_vtk.metrics.calculate.amplitudes import coerce_series_and_dt


def compute_amplitude_spectrum_vs_period(trace: Any, dt: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Convert one waveform into a period-axis amplitude spectrum.

    Parameters
    ----------
    trace
        Waveform samples or trace-like object.
    dt
        Optional sample spacing in seconds.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray]
        Period values in seconds and corresponding one-sided FFT amplitudes,
        sorted from short to long period.
    """

    samples, resolved_dt = coerce_series_and_dt(trace, dt)
    if samples.size < 2:
        raise ValueError("trace is too short for FFT-based spectrum computation.")
    spectrum = np.fft.rfft(samples)
    freqs = np.fft.rfftfreq(samples.size, d=resolved_dt)
    mask = freqs > 0.0
    periods = 1.0 / freqs[mask]
    amplitudes = np.abs(spectrum[mask])
    order = np.argsort(periods)
    return periods[order], amplitudes[order]


def subset_period_range(
    periods: Sequence[float],
    amplitudes: Sequence[float],
    min_period: float | None = None,
    max_period: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Filter a period spectrum to one inclusive period range.

    Parameters
    ----------
    periods
        Period axis in seconds.
    amplitudes
        Spectrum amplitudes aligned to ``periods``.
    min_period, max_period
        Optional inclusive period limits.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray]
        Filtered period and amplitude arrays.
    """

    period_array = np.asarray(periods, dtype=float).reshape(-1)
    amplitude_array = np.asarray(amplitudes, dtype=float).reshape(-1)
    if period_array.size != amplitude_array.size:
        raise ValueError("periods and amplitudes must have the same length.")
    mask = np.ones(period_array.size, dtype=bool)
    if min_period is not None:
        mask &= period_array >= float(min_period)
    if max_period is not None:
        mask &= period_array <= float(max_period)
    return period_array[mask], amplitude_array[mask]


def interpolate_period_spectrum(
    periods: Sequence[float],
    amplitudes: Sequence[float],
    target_periods: Sequence[float],
) -> np.ndarray:
    """Interpolate amplitudes onto requested periods.

    Parameters
    ----------
    periods
        Source period axis in seconds.
    amplitudes
        Source amplitudes aligned to ``periods``.
    target_periods
        Requested target periods in seconds.

    Returns
    -------
    numpy.ndarray
        Interpolated amplitudes aligned with ``target_periods``.
    """

    source_periods = np.asarray(periods, dtype=float).reshape(-1)
    source_amplitudes = np.asarray(amplitudes, dtype=float).reshape(-1)
    targets = np.asarray(target_periods, dtype=float).reshape(-1)
    if source_periods.size != source_amplitudes.size:
        raise ValueError("periods and amplitudes must have the same length.")
    out = np.full(targets.shape, np.nan, dtype=float)
    finite = np.isfinite(source_periods) & np.isfinite(source_amplitudes)
    if np.count_nonzero(finite) < 2:
        return out
    order = np.argsort(source_periods[finite])
    sorted_periods = source_periods[finite][order]
    sorted_amplitudes = source_amplitudes[finite][order]
    valid_targets = np.isfinite(targets) & (targets >= sorted_periods[0]) & (targets <= sorted_periods[-1])
    if np.any(valid_targets):
        out[valid_targets] = np.interp(targets[valid_targets], sorted_periods, sorted_amplitudes)
    return out


def compute_period_spectrogram(
    trace: Any,
    dt: float | None = None,
    nfft: int = 256,
    noverlap: int = 192,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute a period-axis spectrogram for one waveform.

    Parameters
    ----------
    trace
        Waveform samples or trace-like object.
    dt
        Optional sample spacing in seconds.
    nfft, noverlap
        Spectrogram window and overlap in samples.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray]
        Period array, time-bin array, and power matrix sorted from short to
        long period.
    """

    samples, resolved_dt = coerce_series_and_dt(trace, dt)
    if samples.size < 2:
        raise ValueError("trace is too short for spectrogram computation.")
    if int(nfft) <= 0:
        raise ValueError("nfft must be positive.")
    if int(noverlap) < 0 or int(noverlap) >= int(nfft):
        raise ValueError("noverlap must satisfy 0 <= noverlap < nfft.")
    sampling_rate = 1.0 / resolved_dt
    freqs, bins, power = signal.spectrogram(
        samples,
        fs=sampling_rate,
        nperseg=min(int(nfft), samples.size),
        noverlap=min(int(noverlap), max(0, min(int(nfft), samples.size) - 1)),
        scaling="density",
        mode="psd",
    )
    mask = freqs > 0.0
    freqs = freqs[mask]
    power = power[mask, :]
    periods = 1.0 / freqs
    order = np.argsort(periods)
    return periods[order], bins, power[order, :]


__all__ = [
    "compute_amplitude_spectrum_vs_period",
    "compute_period_spectrogram",
    "interpolate_period_spectrum",
    "subset_period_range",
]
