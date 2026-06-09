"""Amplitude summary calculations for waveform metrics.

Purpose
-------
This module provides small reusable amplitude calculations used by metric
workflows, QC summaries, and downstream diagnostics.

Usage examples
--------------
Compute observed/synthetic amplitude ratios:
  ``ratios = calculate_amplitude_ratios(obs, syn, dt=0.02)``
"""

from __future__ import annotations

from typing import Any

import numpy as np


def coerce_series_and_dt(series_or_trace: Any, dt: float | None = None) -> tuple[np.ndarray, float]:
    """Convert an array-like or trace-like object to samples and sample spacing.

    Parameters
    ----------
    series_or_trace
        Numeric samples or an ObsPy-like trace with ``data`` and ``stats``.
    dt
        Optional sample spacing in seconds. If omitted for trace-like objects,
        ``stats.delta`` or ``stats.sampling_rate`` is used.

    Returns
    -------
    tuple[numpy.ndarray, float]
        One-dimensional sample array and resolved positive sample spacing.
    """

    resolved_dt = dt
    if hasattr(series_or_trace, "data") and hasattr(series_or_trace, "stats"):
        stats = getattr(series_or_trace, "stats")
        if resolved_dt is None:
            if hasattr(stats, "delta"):
                resolved_dt = float(stats.delta)
            elif hasattr(stats, "sampling_rate"):
                resolved_dt = 1.0 / float(stats.sampling_rate)
        data = np.asarray(series_or_trace.data, dtype=float)
    else:
        data = np.asarray(series_or_trace, dtype=float)
    if resolved_dt is None or float(resolved_dt) <= 0.0:
        raise ValueError("dt is required and must be positive.")
    return data.reshape(-1), float(resolved_dt)


def calculate_amplitude_ratios(obs_data: Any, syn_data: Any, dt: float | None = None) -> dict[str, float]:
    """Compute paired amplitude-ratio summaries for one waveform pair.

    Parameters
    ----------
    obs_data
        Observed samples or trace-like object.
    syn_data
        Synthetic samples or trace-like object.
    dt
        Optional sample spacing in seconds. This is accepted for a consistent
        waveform-helper API, but amplitudes do not depend on ``dt``.

    Returns
    -------
    dict[str, float]
        Peak and RMS amplitudes for both traces plus observed/synthetic ratios.
    """

    observed, _resolved_dt = coerce_series_and_dt(obs_data, dt or 1.0)
    synthetic, _resolved_dt = coerce_series_and_dt(syn_data, dt or 1.0)
    if observed.size == 0 or synthetic.size == 0:
        return {
            "max_amp_obs": np.nan,
            "max_amp_syn": np.nan,
            "max_amp_ratio": np.nan,
            "rms_obs": np.nan,
            "rms_syn": np.nan,
            "rms_ratio": np.nan,
        }
    max_amp_obs = float(np.nanmax(np.abs(observed)))
    max_amp_syn = float(np.nanmax(np.abs(synthetic)))
    rms_obs = float(np.sqrt(np.nanmean(observed**2)))
    rms_syn = float(np.sqrt(np.nanmean(synthetic**2)))
    return {
        "max_amp_obs": max_amp_obs,
        "max_amp_syn": max_amp_syn,
        "max_amp_ratio": max_amp_obs / max_amp_syn if max_amp_syn > 1e-12 else np.inf,
        "rms_obs": rms_obs,
        "rms_syn": rms_syn,
        "rms_ratio": rms_obs / rms_syn if rms_syn > 1e-12 else np.inf,
    }


def compute_station_event_maxima(trace: Any, dt: float | None = None) -> dict[str, float]:
    """Compute peak and RMS amplitudes for one waveform.

    Parameters
    ----------
    trace
        Waveform samples or trace-like object.
    dt
        Optional sample spacing in seconds.

    Returns
    -------
    dict[str, float]
        ``max_amplitude`` and ``rms_amplitude`` for the waveform.
    """

    samples, _resolved_dt = coerce_series_and_dt(trace, dt or 1.0)
    if samples.size == 0:
        return {"max_amplitude": np.nan, "rms_amplitude": np.nan}
    return {
        "max_amplitude": float(np.nanmax(np.abs(samples))),
        "rms_amplitude": float(np.sqrt(np.nanmean(samples**2))),
    }


def compute_paired_station_event_maxima(observed: Any, synthetic: Any, dt: float | None = None) -> dict[str, float]:
    """Compute paired maxima and amplitude ratios for one waveform pair.

    Parameters
    ----------
    observed
        Observed waveform samples or trace-like object.
    synthetic
        Synthetic waveform samples or trace-like object.
    dt
        Optional sample spacing in seconds.

    Returns
    -------
    dict[str, float]
        Combined maxima and amplitude-ratio summary for the pair.
    """

    return calculate_amplitude_ratios(observed, synthetic, dt=dt)


__all__ = [
    "calculate_amplitude_ratios",
    "coerce_series_and_dt",
    "compute_paired_station_event_maxima",
    "compute_station_event_maxima",
]
