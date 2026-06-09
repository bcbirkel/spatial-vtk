#!/usr/bin/env python3
"""Goodness-of-fit metrics for observed and synthetic trace pairs.

The module implements the legacy C1-C13 metric bundle while exposing newer
metric names elsewhere in the public package. It includes duration, intensity,
amplitude, spectral, delay, correlation, and cumulative absolute velocity
calculations.

Implementation notes
--------------------

- C5-C7 use the same Gaussian score kernel as C3 and C4.
- C8 uses a Newmark average-acceleration SDOF solver and returns PSA.
- C9 compares native FFT amplitudes over the requested frequency range.
- C1 and C2 compare 5-95 percent duration lengths.
- C11 uses a Gaussian penalty on absolute lag divided by lag cap.
- C12 is the aligned cross-correlation score at the optimal lag.
- C13 is CAV integrated over each trace's 5-95 percent energy-duration window.
- Velocity and displacement metrics use frequency-domain integration.

Inputs are expected to be preprocessed for the period band of interest and to
use consistent physical units.

Usage examples
--------------
Compute one metrics bundle for aligned traces:
  ``from spatial_vtk.metrics.calculate.gof import compute_metrics_pair``
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple
import numpy as np

try:
    from scipy import integrate as _scipy_integrate
    _HAVE_SCIPY = True
except Exception:
    _HAVE_SCIPY = False

# Frequencies for C8 response spectra comparison (within a band)
RS_FREQS_C8 = np.logspace(np.log10(0.1), np.log10(10.0), 40)

# Frequencies for plotting PSA residuals (broadband)
RS_FREQS_PLOT = np.logspace(np.log10(0.1), np.log10(10.0), 250)

# Periods for exported metrics (T=1-10s at 0.5s intervals)
PSA_EXPORT_PERIODS = np.arange(1.0, 10.5, 0.5)
PSA_EXPORT_FREQS = 1.0 / PSA_EXPORT_PERIODS

METRIC_NAMES = {
    'C1': "Arias Duration (5-95%)",
    'C2': "Energy Duration (5-95%)",
    'C3': "Arias Intensity",
    'C4': "Energy Integral",
    'C5': "Peak Acceleration",
    'C6': "Peak Velocity",
    'C7': "Peak Displacement",
    'C8': "Response Spectra (PSA)",
    'C9': "Fourier Spectra",
    'C10': "Cross Correlation (0-lag)",
    'C11': "Phase Delay (Gaussian)",
    'C12': "Aligned Cross Correlation",
    'C13': "CAV",
}

# ---------- Basic helpers ----------

def _cumtrapz(y, dt):
    y = np.asarray(y, float)
    n = y.size
    if n == 0:
        return y
    out = np.empty_like(y)
    out[0] = 0.0
    if n > 1:
        out[1:] = np.cumsum(0.5 * (y[1:] + y[:-1])) * dt
    return out

def _detrend_linear(x, dt):
    """Remove mean and linear trend from x."""
    x = np.asarray(x, float)
    n = x.size
    if n < 2:
        return x - float(np.nanmean(x)) if n else x
    t = np.arange(n, dtype=float) * dt
    # simple least-squares line fit
    A = np.vstack([t, np.ones(n)]).T
    m, b = np.linalg.lstsq(A, x, rcond=None)[0]
    return x - (m * t + b)

def _frequency_integrate(
    series,
    dt: float,
    *,
    order: int = 1,
    fmin: Optional[float] = None,
    return_padded: bool = False,
) -> np.ndarray | tuple[np.ndarray, np.ndarray, int]:
    """Integrate a trace in the frequency domain.

    Inputs:
    - series: evenly sampled input trace.
    - dt: sample spacing in seconds.
    - order: integration order. Use 1 for acceleration-to-velocity or
      velocity-to-displacement, and 2 for acceleration-to-displacement.
    - fmin: optional low-frequency cutoff. Frequencies below this are set to
      zero to avoid reintroducing removed long-period drift.

    Outputs:
    - integrated trace with zero DC, or ``(cropped, padded, pad_samples)`` when
      ``return_padded`` is true. A time shift changes spectral phase but not the
      integrated amplitude, so this is less sensitive to finite-record
      detrending artifacts than cumulative integration plus trend removal.
    """

    arr = np.asarray(series, float)
    if arr.size == 0 or dt <= 0.0:
        empty = np.zeros_like(arr, dtype=float)
        return (empty, empty, 0) if return_padded else empty
    x = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    n_original = x.size
    pad = _integration_pad_samples(n_original, dt, fmin)
    if pad > 0:
        x = np.pad(x, (pad, pad), mode="constant")
    x = x - float(np.mean(x))
    freqs = np.fft.rfftfreq(x.size, d=float(dt))
    omega = 2.0 * np.pi * freqs
    spectrum = np.fft.rfft(x)
    integrated = np.zeros_like(spectrum, dtype=complex)
    valid = omega > 0.0
    if fmin is not None and np.isfinite(fmin) and float(fmin) > 0.0:
        valid &= freqs >= float(fmin)
    if np.any(valid):
        integrated[valid] = spectrum[valid] / ((1j * omega[valid]) ** int(order))
    out = np.fft.irfft(integrated, n=x.size).real
    cropped = out[pad:pad + n_original] if pad > 0 else out
    return (cropped, out, pad) if return_padded else cropped


def _integration_pad_samples(n: int, dt: float, fmin: Optional[float]) -> int:
    """Return zero-padding samples for frequency-domain integration."""

    if n <= 1 or dt <= 0.0:
        return 0
    if fmin is not None and np.isfinite(fmin) and float(fmin) > 0.0:
        low_period_samples = int(np.ceil(4.0 / (float(fmin) * float(dt))))
        return int(min(2 * n, max(n, low_period_samples)))
    return int(n)


def _integrate_acc_to_vel(acc, dt, fmin: Optional[float] = None, return_padded: bool = False):
    """Return velocity from acceleration using frequency-domain integration."""

    return _frequency_integrate(acc, dt, order=1, fmin=fmin, return_padded=return_padded)


def _integrate_vel_to_disp(vel, dt, fmin: Optional[float] = None):
    """Return displacement from velocity using frequency-domain integration."""

    return _frequency_integrate(vel, dt, order=1, fmin=fmin)


def _integrate_acc_to_disp(acc, dt, fmin: Optional[float] = None):
    """Return displacement directly from acceleration in the frequency domain."""

    return _frequency_integrate(acc, dt, order=2, fmin=fmin)

# Edge guard for peak metrics
def _peak_abs(x, edge_frac=0.01):
    x = np.asarray(x, float)
    n = x.size
    if n == 0: 
        return 0.0
    m = max(0, int(round(edge_frac * n)))
    if m <= 0 or m*2 >= n:
        return float(np.nanmax(np.abs(x)))
    return float(np.nanmax(np.abs(x[m:-m])))


def _trapz(y, dt):
    arr = np.asarray(y, float)
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(arr, dx=dt))
    if hasattr(np, "trapz"):
        return float(np.trapz(arr, dx=dt))
    if arr.size < 2:
        return 0.0
    return float(np.sum(0.5 * (arr[1:] + arr[:-1])) * dt)

def _simpson(y, dt):
    if _HAVE_SCIPY:
        return float(_scipy_integrate.simpson(np.asarray(y, float), dx=dt))
    return _trapz(y, dt)

def _integral(x, dt):
    return np.cumsum(np.asarray(x, float)) * dt

def _integral2(x, dt):
    return np.cumsum(_integral(x, dt)) * dt

def _rms(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    if x.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(x * x)))

def _eval_score_decay(p1: float, p2: float) -> float:
    """
    Exponential decay score in [0,10].
    Score is 10 if p1=p2, 5 at 100% diff, 2.5 at 200%, etc.
    """
    if p1 <= 0 or p2 <= 0:
        return 0.0
    # Relative difference: |p1-p2| / min(p1,p2)
    pmin = p1 if p1 < p2 else p2
    relative_diff = abs(p1 - p2) / pmin
    return float(10.0 * (0.5 ** relative_diff))

def _eval_score_anderson(p1: float, p2: float) -> float:
    """
    Anderson-style Gaussian score kernel S(p1,p2) in [0,10].
    Returns 0 if either value is non-positive.
    """
    if p1 <= 0 or p2 <= 0:
        return 0.0
    pmin = p1 if p1 < p2 else p2
    exponent = -(((p1 - p2) / pmin) ** 2)
    return float(min(10.0, 10.0 * np.exp(exponent)))

# --- Scoring function dispatcher ---
_SCORING_FUNCTIONS = {
    'anderson': _eval_score_anderson,
    'decay': _eval_score_decay,
}
_active_scoring_function = _SCORING_FUNCTIONS['decay'] # Default to decay

def set_scoring_function(name: str):
    """Sets the active scoring function for the module for the current process."""
    global _active_scoring_function
    func = _SCORING_FUNCTIONS.get(name)
    if func is None:
        raise ValueError(f"Unknown scoring function: {name}. Available: {list(_SCORING_FUNCTIONS.keys())}")
    _active_scoring_function = func

def _eval_score(p1: float, p2: float) -> float:
    """Dispatches to the currently active scoring function."""
    return _active_scoring_function(p1, p2)

def _cumtrapz_sq(y, dt):
    """Cumulative integral of y^2 via trapezoid rule, I[0]=0."""
    y = np.asarray(y, float)
    n = y.size
    if n == 0:
        return np.zeros(0, float)
    z2 = y * y
    # trapezoid cumulative without a Python loop
    # mid-sum of adjacent samples, then cumulative sum
    mid = 0.5 * (z2[:-1] + z2[1:])
    out = np.empty(n, float)
    out[0] = 0.0
    out[1:] = np.cumsum(mid) * dt
    return out

def _duration_5_95(cum, times):
    if cum.size == 0 or cum[-1] <= 0:
        return 0.0
    norm = cum / cum[-1]
    t5  = float(np.interp(0.05, norm, times))
    t95 = float(np.interp(0.95, norm, times))
    return max(t95 - t5, 0.0)

def _coerce_valid_mask(mask, n: int) -> np.ndarray:
    """Return a boolean validity mask on the metric trace grid.

    Inputs:
    - mask: optional array-like mask. ``None`` means every sample is valid.
    - n: expected sample count.

    Outputs:
    - boolean array of length ``n``. Short masks are padded with ``False`` and
      long masks are cropped so validity failures are conservative.
    """

    n = int(max(n, 0))
    if mask is None:
        return np.ones(n, dtype=bool)
    arr = np.asarray(mask, dtype=bool).reshape(-1)
    if arr.size == n:
        return arr.copy()
    out = np.zeros(n, dtype=bool)
    m = min(n, arr.size)
    if m > 0:
        out[:m] = arr[:m]
    return out

def _valid_interval_s(valid_mask: np.ndarray, dt: float, time_offset_s: float = 0.0) -> Optional[Tuple[float, float]]:
    """Return the inclusive time bounds of valid samples, or ``None``."""

    idx = np.flatnonzero(np.asarray(valid_mask, dtype=bool))
    if idx.size == 0:
        return None
    return float(idx[0] * dt + time_offset_s), float(idx[-1] * dt + time_offset_s)

def _duration_window_5_95(cum, dt, valid_mask=None, trace_label: str = "trace", time_offset_s: float = 0.0) -> dict[str, object]:
    """Return 5-95% cumulative-duration bounds with validity diagnostics.

    Inputs:
    - cum: cumulative non-negative integral on the full filtered trace.
    - dt: sample spacing in seconds.
    - valid_mask: optional filter-validity mask on the same full trace grid.
    - trace_label: label used inside reason strings, such as ``obs`` or ``syn``.

    Outputs:
    - dictionary with duration/window values plus ``status`` and ``reason``.
      ``status`` is ``ok`` only when the cumulative bounds are finite and both
      5% and 95% times lie inside that trace's valid filter interval.
    """

    c = np.asarray(cum, float)
    n = c.size
    mask = _coerce_valid_mask(valid_mask, n)
    out: dict[str, object] = {
        "duration": np.nan,
        "t5": np.nan,
        "t95": np.nan,
        "status": "unreliable",
        "reason": f"{trace_label}_empty_trace",
    }
    if n == 0:
        return out
    total = float(c[-1])
    if not np.isfinite(total) or total <= 0.0:
        out["reason"] = f"{trace_label}_zero_or_nonfinite_energy"
        return out
    times = np.arange(n, dtype=float) * float(dt) + float(time_offset_s)
    norm = c / total
    t5 = float(np.interp(0.05, norm, times))
    t95 = float(np.interp(0.95, norm, times))
    out.update({"duration": max(t95 - t5, 0.0), "t5": t5, "t95": t95})
    valid_interval = _valid_interval_s(mask, dt, time_offset_s=time_offset_s)
    if valid_interval is None:
        out["reason"] = f"{trace_label}_no_valid_window"
        return out
    valid_start, valid_end = valid_interval
    bad_bounds = []
    if t5 < valid_start or t5 > valid_end:
        bad_bounds.append("t5")
    if t95 < valid_start or t95 > valid_end:
        bad_bounds.append("t95")
    if bad_bounds:
        out["reason"] = f"{trace_label}_{'_'.join(bad_bounds)}_outside_valid_window"
        return out
    out["status"] = "ok"
    out["reason"] = ""
    return out

def _metric_residuals(obs: float, syn: float) -> dict[str, float]:
    """Return standard residual columns for one observed/synthetic metric pair."""

    obs_f = float(obs) if np.isfinite(obs) else np.nan
    syn_f = float(syn) if np.isfinite(syn) else np.nan
    out = {"residual": syn_f - obs_f if np.isfinite(obs_f) and np.isfinite(syn_f) else np.nan}
    if np.isfinite(obs_f) and np.isfinite(syn_f) and obs_f > 0.0 and syn_f > 0.0:
        out["residual_log2"] = float(np.log2(syn_f / obs_f))
    else:
        out["residual_log2"] = np.nan
    return out

def _attach_residual_columns(out: Dict[str, float]) -> None:
    """Attach residual and log2-ratio residual columns to obs/syn metric pairs."""

    stems = {
        key[:-4]
        for key in out
        if key.endswith("_obs") and f"{key[:-4]}_syn" in out
    }
    for stem in stems:
        residuals = _metric_residuals(out[f"{stem}_obs"], out[f"{stem}_syn"])
        out.setdefault(f"{stem}_residual", residuals["residual"])
        out.setdefault(f"{stem}_residual_log2", residuals["residual_log2"])

def _merge_status_reasons(*windows: dict[str, object]) -> tuple[str, str]:
    """Combine per-trace window diagnostics into one metric status/reason."""

    reasons = [str(w.get("reason", "")) for w in windows if str(w.get("status", "")) != "ok" and str(w.get("reason", ""))]
    if reasons:
        return "unreliable", ";".join(reasons)
    return "ok", ""

def _finite_or_nan(value: object) -> float:
    """Return a finite float or NaN."""

    try:
        val = float(value)
    except Exception:
        return np.nan
    return val if np.isfinite(val) else np.nan

def _cav_over_window(acc, dt: float, start_s: float, end_s: float) -> float:
    """Compute CAV over an arbitrary time window using interpolated endpoints.

    Inputs:
    - acc: acceleration series on a regular grid.
    - dt: sample spacing in seconds.
    - start_s/end_s: relative seconds defining the CAV integration window.

    Outputs:
    - integral of absolute acceleration from ``start_s`` to ``end_s``.
    """

    arr = np.asarray(acc, float)
    if arr.size == 0 or not np.isfinite(start_s) or not np.isfinite(end_s) or end_s <= start_s:
        return np.nan
    times = np.arange(arr.size, dtype=float) * float(dt)
    if start_s < times[0] or end_s > times[-1]:
        return np.nan
    interior = (times > start_s) & (times < end_s)
    window_t = np.concatenate(([float(start_s)], times[interior], [float(end_s)]))
    abs_acc = np.abs(arr)
    window_y = np.concatenate((
        [float(np.interp(start_s, times, abs_acc))],
        abs_acc[interior],
        [float(np.interp(end_s, times, abs_acc))],
    ))
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(window_y, x=window_t))
    if hasattr(np, "trapz"):
        return float(np.trapz(window_y, x=window_t))
    return float(np.sum(0.5 * (window_y[1:] + window_y[:-1]) * np.diff(window_t)))

# ---------- Core metric primitives ----------

def compute_arias(acc1, acc2, dt, compute_scores=True) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """C1 Arias 5-95% duration and C3 total Arias intensity."""
    g = 981.0  # use 9.81 if working in m/s^2
    acc1 = np.asarray(acc1, float)
    acc2 = np.asarray(acc2, float)
    IA1t = (np.pi / (2 * g)) * _cumtrapz_sq(acc1, dt)
    IA2t = (np.pi / (2 * g)) * _cumtrapz_sq(acc2, dt)

    IA1 = IA1t[-1] if IA1t.size else 0.0
    IA2 = IA2t[-1] if IA2t.size else 0.0
    C3_score = _eval_score(IA1, IA2) if compute_scores else np.nan

    times1 = np.arange(acc1.size) * dt
    times2 = np.arange(acc2.size) * dt
    dur1 = _duration_5_95(IA1t, times1)
    dur2 = _duration_5_95(IA2t, times2)
    C1_score = _eval_score(dur1, dur2) if compute_scores else np.nan
    
    return (dur1, dur2, C1_score), (IA1, IA2, C3_score)

def compute_duration(vel1, vel2, dt, compute_scores=True) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """C2 energy 5-95% duration and C4 energy integral."""
    vel1 = np.asarray(vel1, float); vel2 = np.asarray(vel2, float)
    IE1t = _cumtrapz_sq(vel1, dt)
    IE2t = _cumtrapz_sq(vel2, dt)

    IE1 = IE1t[-1] if IE1t.size else 0.0
    IE2 = IE2t[-1] if IE2t.size else 0.0
    C4_score = _eval_score(IE1, IE2) if compute_scores else np.nan

    times = np.arange(vel1.size) * dt
    dur1 = _duration_5_95(IE1t, times)
    dur2 = _duration_5_95(IE2t, times)
    C2_score = _eval_score(dur1, dur2) if compute_scores else np.nan

    return (dur1, dur2, C2_score), (IE1, IE2, C4_score)


# ---------- Public named metric primitives ----------

def _as_metric_trace(trace) -> np.ndarray:
    """Return a one-dimensional finite float trace for metric calculations.

    Parameters
    ----------
    trace
        Array-like waveform samples.

    Returns
    -------
    numpy.ndarray
        One-dimensional float array with NaNs and infinities replaced by zero.
    """

    arr = np.asarray(trace, dtype=float).reshape(-1)
    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)


def arias_intensity(trace, dt: float) -> float:
    """Calculate Arias intensity for one acceleration trace.

    Parameters
    ----------
    trace
        Acceleration samples with units consistent with ``g = 981 cm/s^2``.
    dt
        Sample spacing in seconds.

    Returns
    -------
    float
        Arias intensity integrated over the trace.
    """

    acc = _as_metric_trace(trace)
    if acc.size == 0 or dt <= 0.0:
        return np.nan
    g = 981.0
    cumulative = (np.pi / (2 * g)) * _cumtrapz_sq(acc, dt)
    return float(cumulative[-1]) if cumulative.size else np.nan


def arias_duration(trace, dt: float) -> float:
    """Calculate 5-95 percent Arias duration for one acceleration trace.

    Parameters
    ----------
    trace
        Acceleration samples.
    dt
        Sample spacing in seconds.

    Returns
    -------
    float
        Duration between 5 and 95 percent cumulative Arias intensity.
    """

    acc = _as_metric_trace(trace)
    if acc.size == 0 or dt <= 0.0:
        return np.nan
    g = 981.0
    cumulative = (np.pi / (2 * g)) * _cumtrapz_sq(acc, dt)
    times = np.arange(acc.size, dtype=float) * float(dt)
    return float(_duration_5_95(cumulative, times))


def energy_intensity(trace, dt: float, *, fmin: Optional[float] = None) -> float:
    """Calculate the velocity-energy integral for one acceleration trace.

    Parameters
    ----------
    trace
        Acceleration samples.
    dt
        Sample spacing in seconds.
    fmin
        Optional low-frequency cutoff for frequency-domain integration.

    Returns
    -------
    float
        Integral of squared velocity over the trace.
    """

    acc = _as_metric_trace(trace)
    if acc.size == 0 or dt <= 0.0:
        return np.nan
    velocity = _integrate_acc_to_vel(acc, dt, fmin=fmin)
    cumulative = _cumtrapz_sq(velocity, dt)
    return float(cumulative[-1]) if cumulative.size else np.nan


def energy_duration(trace, dt: float, *, fmin: Optional[float] = None) -> float:
    """Calculate 5-95 percent velocity-energy duration for one trace.

    Parameters
    ----------
    trace
        Acceleration samples.
    dt
        Sample spacing in seconds.
    fmin
        Optional low-frequency cutoff for frequency-domain integration.

    Returns
    -------
    float
        Duration between 5 and 95 percent cumulative velocity energy.
    """

    acc = _as_metric_trace(trace)
    if acc.size == 0 or dt <= 0.0:
        return np.nan
    velocity = _integrate_acc_to_vel(acc, dt, fmin=fmin)
    cumulative = _cumtrapz_sq(velocity, dt)
    times = np.arange(velocity.size, dtype=float) * float(dt)
    return float(_duration_5_95(cumulative, times))


def PGA(trace, *, edge_frac: float = 0.01) -> float:
    """Calculate peak ground acceleration.

    Parameters
    ----------
    trace
        Acceleration samples.
    edge_frac
        Fraction of samples trimmed from each edge before measuring the peak.

    Returns
    -------
    float
        Peak absolute acceleration.
    """

    return float(_peak_abs(_as_metric_trace(trace), edge_frac=edge_frac))


def PGV(trace, dt: float, *, fmin: Optional[float] = None, edge_frac: float = 0.01) -> float:
    """Calculate peak ground velocity from an acceleration trace.

    Parameters
    ----------
    trace
        Acceleration samples.
    dt
        Sample spacing in seconds.
    fmin
        Optional low-frequency cutoff for integration.
    edge_frac
        Fraction of samples trimmed from each edge before measuring the peak.

    Returns
    -------
    float
        Peak absolute velocity.
    """

    if dt <= 0.0:
        return np.nan
    velocity = _integrate_acc_to_vel(_as_metric_trace(trace), dt, fmin=fmin)
    return float(_peak_abs(velocity, edge_frac=edge_frac))


def PGD(trace, dt: float, *, fmin: Optional[float] = None, edge_frac: float = 0.01) -> float:
    """Calculate peak ground displacement from an acceleration trace.

    Parameters
    ----------
    trace
        Acceleration samples.
    dt
        Sample spacing in seconds.
    fmin
        Optional low-frequency cutoff for integration.
    edge_frac
        Fraction of samples trimmed from each edge before measuring the peak.

    Returns
    -------
    float
        Peak absolute displacement.
    """

    if dt <= 0.0:
        return np.nan
    displacement = _integrate_acc_to_disp(_as_metric_trace(trace), dt, fmin=fmin)
    return float(_peak_abs(displacement, edge_frac=edge_frac))

# ---------- Response spectra (C8) with Newmark-β ----------

def _psa_newmark(acc: np.ndarray, dt: float, freq_hz: float, zeta: float = 0.05) -> float:
    """
    Stable Newmark-β (β=1/4, γ=1/2) SDOF relative motion with base acceleration input.
    Returns PSA = ω^2 * max|u|.
    """
    # ---- Guards & casting ----
    if dt <= 0.0 or freq_hz <= 0.0:
        return 0.0
    acc = np.asarray(acc, dtype=np.float64)
    if acc.size == 0:
        return 0.0
    # Replace NaNs/Infs defensively
    acc = np.nan_to_num(acc, nan=0.0, posinf=0.0, neginf=0.0)

    # ---- System ----
    m = 1.0
    omega = 2.0 * np.pi * float(freq_hz)
    k = m * omega * omega
    c = 2.0 * zeta * omega * m

    # ---- Newmark constants (β=1/4, γ=1/2) ----
    beta = 0.25
    gamma = 0.5
    a0 = 1.0 / (beta * dt * dt)              # 4 / dt^2
    a1 = gamma / (beta * dt)                 # 2 / dt
    a2 = 1.0 / (beta * dt)                   # 4 / dt
    a3 = 1.0 / (2.0 * beta) - 1.0            # 1
    a4 = gamma / beta - 1.0                  # 1
    a5 = dt * (gamma / (2.0 * beta) - 1.0)   # 0

    keff = k + a0 * m + a1 * c               # effective stiffness

    # ---- State ----
    u = 0.0
    v = 0.0
    a_rel = 0.0
    umax = 0.0

    # ---- Time stepping ----
    # Effective load uses current state (u, v, a_rel); no predictor needed.
    # p_eff = -m*ag + m*(a0*u + a2*v + a3*a_rel) + c*(a1*u + a4*v + a5*a_rel)
    for ag in acc:
        p_eff = (-m * ag
                 + m * (a0 * u + a2 * v + a3 * a_rel)
                 + c * (a1 * u + a4 * v + a5 * a_rel))

        u_new = p_eff / keff
        a_rel_new = a0 * (u_new - u) - a2 * v - a3 * a_rel
        v_new = v + dt * ((1.0 - gamma) * a_rel + gamma * a_rel_new)

        u, v, a_rel = u_new, v_new, a_rel_new
        if abs(u) > abs(umax):
            umax = u

    psa = (omega * omega) * abs(umax)
    return float(psa)


def PSA(trace, dt: float, periods: Iterable[float], *, damping: float = 0.05) -> np.ndarray:
    """Calculate pseudo-spectral acceleration at requested periods.

    Parameters
    ----------
    trace
        Acceleration samples.
    dt
        Sample spacing in seconds.
    periods
        Spectral periods in seconds.
    damping
        Damping ratio used by the Newmark SDOF solver.

    Returns
    -------
    numpy.ndarray
        PSA values aligned with ``periods``.
    """

    acc = _as_metric_trace(trace)
    requested_periods = np.asarray(tuple(periods), dtype=float)
    out = np.full(requested_periods.shape, np.nan, dtype=float)
    if acc.size == 0 or dt <= 0.0:
        return out
    for idx, period in enumerate(requested_periods):
        if np.isfinite(period) and period > 0.0:
            out[idx] = _psa_newmark(acc, dt, 1.0 / float(period), zeta=damping)
    return out

def compute_C8(a1, a2, rs_freqs=RS_FREQS_C8, dt=None, damping=0.05, compute_scores=True, fmin: Optional[float] = None, fmax: Optional[float] = None) -> Tuple[float, float, float]:
    if dt is None:
        raise ValueError("dt is required for C8")
    
    freqs_to_use = rs_freqs
    if fmin is not None and fmax is not None:
        freqs_to_use = freqs_to_use[(freqs_to_use >= fmin) & (freqs_to_use <= fmax)]

    scores = []
    psa1_vals = []
    psa2_vals = []

    for f in freqs_to_use:
        # try/except to skip any pathological bins rather than propagating NaNs
        try:
            p1 = _psa_newmark(a1, dt, f, damping)
            p2 = _psa_newmark(a2, dt, f, damping)
            if compute_scores:
                scores.append(_eval_score(p1, p2))
            if p1 > 0: psa1_vals.append(p1)
            if p2 > 0: psa2_vals.append(p2)
        except FloatingPointError:
            continue
    
    score = float(np.nanmean(scores)) if scores else np.nan
    psa1_gmean = float(np.exp(np.mean(np.log(psa1_vals)))) if psa1_vals else 0.0
    psa2_gmean = float(np.exp(np.mean(np.log(psa2_vals)))) if psa2_vals else 0.0
    
    return psa1_gmean, psa2_gmean, score

# ---------- Fourier spectra (C9) on native FFT grid ----------

def _fourier_amp_spectrum(acc, dt, use_hann=True):
    """
    One-sided Fourier Amplitude Spectrum (FAS) with proper scaling.

    - Detrends (remove mean)
    - Optional Hann window (recommended) to reduce leakage
    - Returns one-sided amplitude spectrum in units: (input units) * s
      i.e., consistent with ∫|x(t)| e^{-i2πft} dt
    """
    x = np.asarray(acc, float)
    n = x.size
    if n == 0 or dt <= 0.0:
        return np.zeros(1), np.zeros(1)

    # Detrend mean (assumes you've already bandpassed for trends)
    x = x - float(np.nanmean(x))

    # Window
    if use_hann:
        w = np.hanning(n)
        # coherent gain of Hann is 0.5; compensate amplitude for the window
        cg = np.sum(w) / n  # ~0.5
        xw = x * w
    else:
        cg = 1.0
        xw = x

    # One-sided frequencies and FFT
    f = np.fft.rfftfreq(n, d=dt)                       # Hz
    X = np.fft.rfft(xw)

    # Convert to one-sided *amplitude* spectrum with correct units
    # Start from continuous-time definition: F(f) ≈ dt * |FFT|
    A = dt * np.abs(X)

    # One-sided doubling for bins strictly between DC and Nyquist
    if n > 1:
        A[1:-1] *= 2.0

    # Compensate for window coherent gain so amplitudes are unbiased
    A /= cg

    # Replace NaNs/Infs defensively
    A = np.nan_to_num(A, nan=0.0, posinf=0.0, neginf=0.0)
    return f, A


def FAS(
    trace,
    dt: float,
    *,
    periods: Iterable[float] | None = None,
    frequencies: Iterable[float] | None = None,
    use_hann: bool = True,
) -> np.ndarray | tuple[np.ndarray, np.ndarray]:
    """Calculate Fourier amplitude spectra on a requested period/frequency grid.

    Parameters
    ----------
    trace
        Acceleration samples.
    dt
        Sample spacing in seconds.
    periods
        Optional periods in seconds. Returned values are interpolated at
        ``1 / period``.
    frequencies
        Optional frequencies in Hz. Ignored when ``periods`` is supplied.
    use_hann
        Whether to apply a Hann window before the FFT.

    Returns
    -------
    numpy.ndarray or tuple[numpy.ndarray, numpy.ndarray]
        Interpolated amplitudes aligned with the requested grid. If neither
        ``periods`` nor ``frequencies`` is supplied, returns the native
        ``(frequency_hz, amplitude)`` arrays.
    """

    freq_hz, amplitude = _fourier_amp_spectrum(_as_metric_trace(trace), dt, use_hann=use_hann)
    if periods is None and frequencies is None:
        return freq_hz, amplitude
    if periods is not None:
        grid = np.asarray(tuple(periods), dtype=float)
        target_freqs = np.full(grid.shape, np.nan, dtype=float)
        valid = np.isfinite(grid) & (grid > 0.0)
        target_freqs[valid] = 1.0 / grid[valid]
    else:
        target_freqs = np.asarray(tuple(frequencies or ()), dtype=float)
    out = np.full(target_freqs.shape, np.nan, dtype=float)
    valid = np.isfinite(target_freqs) & (target_freqs >= freq_hz.min()) & (target_freqs <= freq_hz.max())
    if np.any(valid):
        out[valid] = np.interp(target_freqs[valid], freq_hz, amplitude)
    return out

def compute_C9(a1, a2, dt: float, fmin: Optional[float] = None, fmax: Optional[float] = None, compute_scores=True) -> Tuple[float, float, float]:
    """
    Mean Anderson score over one-sided, properly scaled FAS bins in [fmin, fmax].
    """
    f1, A1 = _fourier_amp_spectrum(a1, dt, use_hann=False)
    f2, A2 = _fourier_amp_spectrum(a2, dt, use_hann=False)

    if f1.size != f2.size or not np.allclose(f1, f2):
        A2 = np.interp(f1, f2, A2, left=0.0, right=0.0)
        f, B1, B2 = f1, A1, A2
    else:
        f, B1, B2 = f1, A1, A2

    band = (f >= float(fmin)) & (f <= float(fmax))
    if not np.any(band):
        return 0.0, 0.0, 0.0

    # Optional: smooth amplitudes in log-f (very light, KO-style surrogate)
    # (kept simple; your compute_efas could be plugged here instead)
    score = np.nan
    if compute_scores:
        ss = [_eval_score(float(o), float(s)) for (o, s) in zip(B1[band], B2[band])]
        score = float(np.nanmean(ss)) if ss else 0.0

    fas1_vals = B1[band]
    fas2_vals = B2[band]
    fas1_vals = fas1_vals[fas1_vals > 0]
    fas2_vals = fas2_vals[fas2_vals > 0]
    
    fas1_gmean = float(np.exp(np.mean(np.log(fas1_vals)))) if fas1_vals.size > 0 else 0.0
    fas2_gmean = float(np.exp(np.mean(np.log(fas2_vals)))) if fas2_vals.size > 0 else 0.0

    return fas1_gmean, fas2_gmean, score

# ---------- Cross-correlation (fast FFT) ----------

def _xcorr_fft_full(x: np.ndarray, y: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    FFT-based normalized cross-correlation, returning the full function.
    Returns (lags_in_samples, correlation_coefficients).
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n = min(x.size, y.size)
    if n == 0:
        return None, None
    x = x[:n] - float(np.nanmean(x[:n]))
    y = y[:n] - float(np.nanmean(y[:n]))
    nx = np.linalg.norm(x)
    ny = np.linalg.norm(y)
    if nx <= 0 or ny <= 0:
        return None, None

    # Next power of two for efficient FFT; full correlation length = 2n - 1
    m = int(1 << (2 * n - 1).bit_length())
    X = np.fft.rfft(x, n=m)
    Y = np.fft.rfft(y, n=m)
    c = np.fft.irfft(X * np.conj(Y), n=m)  # unshifted correlation

    # Normalize to get correlation coefficients
    c = c / (nx * ny)

    # Wrap so that zero-lag is centered:
    # irfft returns lags 0..m-1 where indices > n-1 correspond to negative lags
    c = np.concatenate((c[-(n - 1):], c[:n]))

    # Build lag axis (samples)
    lags = np.arange(-(n - 1), n, dtype=int)
    return lags, c

def _xcorr_fft_fast(x: np.ndarray, y: np.ndarray, dt: float,
                    max_lag_s: Optional[float] = None) -> Tuple[float, float]:
    """
    FFT-based normalized cross-correlation.
    Returns (lag_seconds_at_peak, peak_corr_coef).
    If max_lag_s is provided, the peak search is limited to that window.
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n = min(x.size, y.size)
    if n == 0:
        return 0.0, np.nan
    x = x[:n] - float(np.nanmean(x[:n]))
    y = y[:n] - float(np.nanmean(y[:n]))
    nx = np.linalg.norm(x)
    ny = np.linalg.norm(y)
    if nx <= 0 or ny <= 0:
        return 0.0, np.nan

    # Next power of two for efficient FFT; full correlation length = 2n - 1
    m = int(1 << (2 * n - 1).bit_length())
    X = np.fft.rfft(x, n=m)
    Y = np.fft.rfft(y, n=m)
    c = np.fft.irfft(X * np.conj(Y), n=m)  # unshifted correlation

    # Normalize to get correlation coefficients
    c = c / (nx * ny)

    # Wrap so that zero-lag is centered:
    # irfft returns lags 0..m-1 where indices > n-1 correspond to negative lags
    c = np.concatenate((c[-(n - 1):], c[:n]))

    # Build lag axis (samples)
    lags = np.arange(-(n - 1), n, dtype=int)

    if max_lag_s is not None:
        max_k = int(max(1, round(max_lag_s / dt)))
        mask = (lags >= -max_k) & (lags <= max_k)
        c_window = c[mask]
        lags_window = lags[mask]
        k_idx = int(np.nanargmax(c_window))
        lag_samples = int(lags_window[k_idx])
        r_peak = float(c_window[k_idx])
    else:
        k_idx = int(np.nanargmax(c))
        lag_samples = int(lags[k_idx])
        r_peak = float(c[k_idx])

    return lag_samples * dt, r_peak

def get_xcorr_full_func(a1, a2):
    """
    Computes the full normalized cross-correlation function for two signals.
    Returns (lags_in_samples, correlation_coefficients).
    """
    nd = normalize_rms(a1)
    ns = normalize_rms(a2)
    return _xcorr_fft_full(nd, ns)

def compute_cross_correlation_zero_lag(acc1, acc2) -> float:
    """
    C10: zero-lag normalized cross-correlation value.
    """
    a = np.asarray(acc1, float); b = np.asarray(acc2, float)
    n = min(a.size, b.size)
    if n == 0:
        return np.nan
    a = a[:n] - float(np.nanmean(a[:n]))
    b = b[:n] - float(np.nanmean(b[:n]))
    na = np.linalg.norm(a); nb = np.linalg.norm(b)
    if na <= 0 or nb <= 0:
        return np.nan
    r0 = float(np.dot(a, b) / (na * nb))
    return r0

# ---------- Phase/Alignment metrics (C11, C12) ----------

def normalize_rms(x):
    x = np.asarray(x, float)
    if x.size == 0:
        return x
    rms = np.sqrt(np.nanmean(x * x))
    scale = rms if rms > 1e-12 else (np.nanmax(np.abs(x)) or 1.0)
    return x / scale

def compute_phase_metrics(a1, a2, dt, lag_cap_s=None, override_lag_s: Optional[float] = None):
    """Compute delay and aligned-correlation scores for a trace pair.

    C11 is a Gaussian score based on absolute lag divided by the lag cap. C12
    is ``10 * max(r_peak, 0)``, where ``r_peak`` is the peak correlation
    coefficient at the optimal lag.
    """
    if lag_cap_s is None:
        lag_cap_s = 1.0
    if not np.isfinite(lag_cap_s) or lag_cap_s <= 0:
        lag_cap_s = 1.0

    nd = normalize_rms(a1)
    ns = normalize_rms(a2)
    
    if override_lag_s is not None and np.isfinite(override_lag_s):
        lag_s = override_lag_s
        lags_samples, c = _xcorr_fft_full(nd, ns)
        r_peak = np.nan
        if c is not None:
            target_lag_samples = int(round(lag_s / dt))
            # Find correlation value at the target lag, interpolating if necessary
            r_peak = float(np.interp(target_lag_samples, lags_samples, c))
    else:
        lag_s, r_peak = _xcorr_fft_fast(nd, ns, dt, max_lag_s=lag_cap_s)

    # Gaussian penalty on absolute lag (smooth to zero at |lag|=cap)
    C11_score = float(10.0 * np.exp(- (abs(lag_s) / float(lag_cap_s)) ** 2))
    # Aligned correlation score with negatives floored
    C12_score = float(10.0 * max(r_peak, 0.0)) if np.isfinite(r_peak) else 0.0

    return C11_score, C12_score, lag_s, r_peak, lag_cap_s


def traveltime_delay(observed, synthetic, dt: float, *, max_lag_s: Optional[float] = None) -> float:
    """Return the delay that maximizes observed/synthetic cross-correlation.

    Parameters
    ----------
    observed
        Observed acceleration samples.
    synthetic
        Synthetic acceleration samples.
    dt
        Sample spacing in seconds.
    max_lag_s
        Optional maximum absolute lag searched in seconds.

    Returns
    -------
    float
        Delay in seconds to apply to the synthetic trace. Positive values mean
        the synthetic trace is shifted earlier to align with the observed trace.
    """

    if dt <= 0.0:
        return np.nan
    xcorr_lag_s, _r_peak = _xcorr_fft_fast(
        normalize_rms(_as_metric_trace(observed)),
        normalize_rms(_as_metric_trace(synthetic)),
        dt,
        max_lag_s=max_lag_s,
    )
    if not np.isfinite(xcorr_lag_s):
        return np.nan
    return float(-xcorr_lag_s)


def original_cc(observed, synthetic) -> float:
    """Calculate the original zero-lag observed/synthetic correlation.

    Parameters
    ----------
    observed
        Observed waveform samples.
    synthetic
        Synthetic waveform samples.

    Returns
    -------
    float
        Zero-lag normalized correlation coefficient.
    """

    return float(compute_cross_correlation_zero_lag(observed, synthetic))


def delay_corrected_cc(
    observed,
    synthetic,
    dt: float,
    *,
    delay_s: Optional[float] = None,
    max_lag_s: Optional[float] = None,
) -> float:
    """Calculate correlation after applying the travel-time delay.

    Parameters
    ----------
    observed
        Observed waveform samples.
    synthetic
        Synthetic waveform samples.
    dt
        Sample spacing in seconds.
    delay_s
        Optional precomputed delay. When omitted, the delay is estimated with
        :func:`traveltime_delay`.
    max_lag_s
        Optional maximum lag used when estimating ``delay_s``.

    Returns
    -------
    float
        Zero-lag correlation coefficient after delay correction.
    """

    lag_s = traveltime_delay(observed, synthetic, dt, max_lag_s=max_lag_s) if delay_s is None else float(delay_s)
    return float(
        _shifted_whole_waveform_correlation(
            _as_metric_trace(observed),
            _as_metric_trace(synthetic),
            dt,
            lag_s,
        )
    )

def _pick_value(arrival_picks, phase: str, role: str) -> float:
    """Return one arrival pick time in seconds, or NaN when unavailable.

    Inputs:
    - arrival_picks: optional mapping. Supported shapes include
      ``{"P": {"obs": 1.2, "syn": 1.5}}`` and flat keys such as
      ``"P_obs_pick_s"``.
    - phase: phase name such as ``P`` or ``S``.
    - role: ``obs`` or ``syn``.

    Outputs:
    - relative pick time in seconds, or NaN.
    """

    if arrival_picks is None:
        return np.nan
    phase_u = str(phase).upper()
    role_l = str(role).lower()
    role_names = {
        "obs": ("obs", "observed", "data"),
        "syn": ("syn", "synthetic"),
    }.get(role_l, (role_l,))
    if isinstance(arrival_picks, dict):
        phase_entry = arrival_picks.get(phase_u) or arrival_picks.get(phase_u.lower())
        if isinstance(phase_entry, dict):
            for name in role_names:
                for key in (name, f"{name}_pick_s", f"{name}_time_s", f"{name}_arrival_s"):
                    if key in phase_entry:
                        return _finite_or_nan(phase_entry[key])
        for name in role_names:
            for key in (
                f"{phase_u}_{name}",
                f"{phase_u}_{name}_pick_s",
                f"{phase_u}_{name}_time_s",
                f"{phase_u}_{name}_arrival_s",
                f"{phase_u.lower()}_{name}",
                f"{phase_u.lower()}_{name}_pick_s",
            ):
                if key in arrival_picks:
                    return _finite_or_nan(arrival_picks[key])
    return np.nan

def _pick_probability(arrival_picks, phase: str, role: str) -> float:
    """Return one optional pick probability, or NaN when unavailable."""

    if not isinstance(arrival_picks, dict):
        return np.nan
    phase_u = str(phase).upper()
    role_l = str(role).lower()
    role_names = {
        "obs": ("obs", "observed", "data"),
        "syn": ("syn", "synthetic"),
    }.get(role_l, (role_l,))
    phase_entry = arrival_picks.get(phase_u) or arrival_picks.get(phase_u.lower())
    if isinstance(phase_entry, dict):
        for name in role_names:
            for key in (f"{name}_probability", f"{name}_prob", f"{name}_confidence"):
                if key in phase_entry:
                    return _finite_or_nan(phase_entry[key])
    for name in role_names:
        for key in (f"{phase_u}_{name}_probability", f"{phase_u}_{name}_prob", f"{phase_u.lower()}_{name}_prob"):
            if key in arrival_picks:
                return _finite_or_nan(arrival_picks[key])
    return np.nan

def _time_in_valid_mask(time_s: float, valid_mask: np.ndarray, dt: float) -> bool:
    """Return whether a relative time lands on a valid sample."""

    if not np.isfinite(time_s) or dt <= 0.0:
        return False
    mask = np.asarray(valid_mask, dtype=bool)
    if mask.size == 0:
        return False
    idx = int(round(float(time_s) / float(dt)))
    if idx < 0 or idx >= mask.size:
        return False
    return bool(mask[idx])

def _arrival_pick_can_bypass_valid_mask(phase: str, probability: float) -> bool:
    """Return whether a pick should bypass bandpass valid-window rejection.

    Inputs:
    - phase: phase label such as ``P`` or ``S``.
    - probability: picker probability for that phase arrival.

    Outputs:
    - ``True`` for P/S picks with finite picker probabilities. PhaseNet
      thresholds are applied before the catalog reaches metrics, and PhaseNet
      picks are made on broadband traces before metric bandpassing. Accepted
      picks should not be invalidated solely because they precede a filtered
      band's conservative edge-validity window.
    """

    return str(phase).upper() in {"P", "S"} and np.isfinite(probability)

def _arrival_window(series, pick_s: float, dt: float, before_s: float, after_s: float) -> tuple[np.ndarray, int, int]:
    """Extract one local arrival window around a pick.

    Inputs:
    - series: waveform samples.
    - pick_s: relative pick time in seconds.
    - dt: sample spacing in seconds.
    - before_s/after_s: window length before and after the pick.

    Outputs:
    - tuple ``(window, start_index, end_index)`` where ``end_index`` is
      exclusive. Empty windows indicate invalid geometry.
    """

    arr = np.asarray(series, float)
    if arr.size == 0 or not np.isfinite(pick_s) or dt <= 0:
        return np.asarray([], dtype=float), 0, 0
    start = int(max(0, np.floor((float(pick_s) - float(before_s)) / float(dt))))
    end = int(min(arr.size, np.ceil((float(pick_s) + float(after_s)) / float(dt)) + 1))
    if end <= start:
        return np.asarray([], dtype=float), start, end
    return arr[start:end], start, end

def _window_valid(valid_mask: np.ndarray, start: int, end: int) -> bool:
    """Return whether every sample in one local window is valid."""

    mask = np.asarray(valid_mask, dtype=bool)
    if start < 0 or end <= start or end > mask.size:
        return False
    return bool(np.all(mask[start:end]))

def _shifted_whole_waveform_correlation(
    acc_obs,
    acc_syn,
    dt: float,
    lag_s: float,
    obs_valid_mask=None,
    syn_valid_mask=None,
) -> float:
    """Correlate full waveforms after applying one phase-derived delay.

    Inputs:
    - acc_obs/acc_syn: full filtered observed and synthetic acceleration traces.
    - dt: sample spacing in seconds.
    - lag_s: synthetic arrival time minus observed arrival time. Positive
      values shift the synthetic earlier before correlation.
    - obs_valid_mask/syn_valid_mask: optional masks defining reliable samples.

    Outputs:
    - zero-lag correlation of the observed trace and whole-shifted synthetic
      trace over their shared finite, valid overlap, or NaN when the overlap is
      too short.
    """

    obs = np.asarray(acc_obs, float)
    syn = np.asarray(acc_syn, float)
    n = min(obs.size, syn.size)
    if n < 3 or dt <= 0.0 or not np.isfinite(lag_s):
        return np.nan
    obs = obs[:n]
    syn = syn[:n]
    obs_mask = _coerce_valid_mask(obs_valid_mask, n)
    syn_mask = _coerce_valid_mask(syn_valid_mask, n)
    t = np.arange(n, dtype=float) * float(dt)
    source_t = t + float(lag_s)
    shifted_syn = np.interp(source_t, t, syn, left=np.nan, right=np.nan)
    shifted_syn_mask = np.interp(source_t, t, syn_mask.astype(float), left=0.0, right=0.0) >= 0.999
    valid = np.isfinite(obs) & np.isfinite(shifted_syn) & obs_mask & shifted_syn_mask
    if int(np.count_nonzero(valid)) < 3:
        return np.nan
    return compute_cross_correlation_zero_lag(obs[valid], shifted_syn[valid])

def compute_arrival_phase_metrics(
    acc_obs,
    acc_syn,
    dt: float,
    obs_pick_s: float,
    syn_pick_s: float,
    phase: str,
    *,
    obs_valid_mask=None,
    syn_valid_mask=None,
    lag_cap_s: Optional[float] = None,
    window_before_s: float = 1.0,
    window_after_s: float = 2.0,
    obs_probability: float = np.nan,
    syn_probability: float = np.nan,
) -> dict[str, float | str]:
    """Compute arrival-aware phase delay and aligned-correlation metrics.

    Inputs:

    - acc_obs/acc_syn: full filtered observed and synthetic acceleration traces.
    - dt: sample spacing in seconds.
    - obs_pick_s/syn_pick_s: relative P or S pick times in seconds.
    - phase: phase label used in reason strings.
    - obs_valid_mask/syn_valid_mask: optional filter-validity masks.
    - lag_cap_s: lag scale for the Gaussian C11 score.
    - window_before_s/window_after_s: retained for API compatibility; C12 now
      uses the phase delay to align and correlate the whole valid waveform.
    - obs_probability/syn_probability: optional pick probabilities.

    Outputs:

    - dictionary with ``lag_s``, ``score``, ``correlation``, ``confidence``,
      ``status``, and ``reason`` fields. Status is ``ok`` only when both picks
      are inside valid trace regions and the whole-waveform shifted overlap can
      be correlated.
    """

    phase_label = str(phase).upper()
    obs = np.asarray(acc_obs, float)
    syn = np.asarray(acc_syn, float)
    obs_mask = _coerce_valid_mask(obs_valid_mask, obs.size)
    syn_mask = _coerce_valid_mask(syn_valid_mask, syn.size)
    if lag_cap_s is None or not np.isfinite(lag_cap_s) or lag_cap_s <= 0:
        lag_cap_s = max(2.0 * float(dt), 1.0)
    if not np.isfinite(obs_pick_s):
        return {
            "lag_s": np.nan,
            "score": np.nan,
            "correlation": np.nan,
            "confidence": 0.0,
            "status": "unreliable",
            "reason": f"{phase_label}_obs_pick_missing",
        }
    if not np.isfinite(syn_pick_s):
        return {
            "lag_s": np.nan,
            "score": np.nan,
            "correlation": np.nan,
            "confidence": 0.0,
            "status": "unreliable",
            "reason": f"{phase_label}_syn_pick_missing",
        }
    obs_pick_valid = _time_in_valid_mask(obs_pick_s, obs_mask, dt) or _arrival_pick_can_bypass_valid_mask(
        phase_label,
        obs_probability,
    )
    syn_pick_valid = _time_in_valid_mask(syn_pick_s, syn_mask, dt) or _arrival_pick_can_bypass_valid_mask(
        phase_label,
        syn_probability,
    )
    if not obs_pick_valid:
        return {
            "lag_s": np.nan,
            "score": np.nan,
            "correlation": np.nan,
            "confidence": 0.0,
            "status": "unreliable",
            "reason": f"{phase_label}_obs_pick_outside_valid_window",
        }
    if not syn_pick_valid:
        return {
            "lag_s": np.nan,
            "score": np.nan,
            "correlation": np.nan,
            "confidence": 0.0,
            "status": "unreliable",
            "reason": f"{phase_label}_syn_pick_outside_valid_window",
        }

    lag_s = float(syn_pick_s - obs_pick_s)
    r_aligned = _shifted_whole_waveform_correlation(
        obs,
        syn,
        dt,
        lag_s,
        obs_valid_mask=obs_mask,
        syn_valid_mask=syn_mask,
    )
    if not np.isfinite(r_aligned):
        return {
            "lag_s": lag_s,
            "score": np.nan,
            "correlation": np.nan,
            "confidence": 0.0,
            "status": "unreliable",
            "reason": f"{phase_label}_whole_waveform_overlap_empty",
        }
    score = float(10.0 * np.exp(-((abs(lag_s) / float(lag_cap_s)) ** 2)))
    corr_conf = float(max(r_aligned, 0.0)) if np.isfinite(r_aligned) else 0.0
    probs = [p for p in (obs_probability, syn_probability) if np.isfinite(p)]
    pick_conf = float(min(probs)) if probs else 1.0
    confidence = float(max(0.0, min(1.0, corr_conf * pick_conf)))
    return {
        "lag_s": lag_s,
        "score": score,
        "correlation": r_aligned if np.isfinite(r_aligned) else np.nan,
        "confidence": confidence,
        "status": "ok",
        "reason": "",
    }

# ---------- CAV (C13) ----------

def compute_cav(acc, dt):
    return _simpson(np.abs(acc), dt)


def CAV(trace, dt: float, *, window: tuple[float, float] | None = None) -> float:
    """Calculate cumulative absolute velocity for one acceleration trace.

    Parameters
    ----------
    trace
        Acceleration samples.
    dt
        Sample spacing in seconds.
    window
        Optional ``(start_s, end_s)`` integration window. If omitted, the full
        trace is used.

    Returns
    -------
    float
        Integral of absolute acceleration.
    """

    acc = _as_metric_trace(trace)
    if acc.size == 0 or dt <= 0.0:
        return np.nan
    if window is None:
        return float(compute_cav(acc, dt))
    start_s, end_s = window
    return float(_cav_over_window(acc, dt, float(start_s), float(end_s)))

# ---------- Wrapper ----------

def compute_metrics_pair(
    acc_data,
    acc_syn,
    dt: float,
    which: Optional[Iterable[str]] = None,
    rs_freqs=RS_FREQS_C8,
    fmax_for_lag: Optional[float] = None,
    scoring_function: str = 'decay',
    compute_scores: bool = True,
    override_lag_s: Optional[float] = None,
    fmin: Optional[float] = None,
    fmax: Optional[float] = None,
    obs_valid_mask=None,
    syn_valid_mask=None,
    arrival_picks=None,
    arrival_window_before_s: float = 1.0,
    arrival_window_after_s: float = 2.0,
) -> Dict[str, float]:
    """
    Computes requested metrics; if `which` is None, returns all plus RMS helpers.
    NOTE: Inputs should already be bandpassed as desired.
    Arrival-aware C12P/C12S metrics use P/S picks to derive a delay, then
    correlate the whole valid waveform after applying that delay. The
    arrival_window_* arguments are retained for API compatibility and are not
    used by the current whole-waveform C12P/C12S definition.
    """
    set_scoring_function(scoring_function)
    _RMS_KEYS = ['obs_rms', 'syn_rms', 'rms_obs', 'rms_syn', 'rms_ratio']
    _PSA_EXPORT_KEYS = [f'PSA_T{p:.1f}' for p in PSA_EXPORT_PERIODS]
    if which is None:
        keys = set(list(METRIC_NAMES.keys()) + _RMS_KEYS + _PSA_EXPORT_KEYS)
    else:
        keys = set(which)
    out: Dict[str, float] = {}

    acc_data = np.asarray(acc_data, float)
    acc_syn = np.asarray(acc_syn, float)
    obs_mask = _coerce_valid_mask(obs_valid_mask, acc_data.size)
    syn_mask = _coerce_valid_mask(syn_valid_mask, acc_syn.size)

    need_vel = any(k in keys for k in ['C2', 'C4', 'C6', 'C7', 'C13'])
    need_disp = ('C7' in keys)

    vel_a = vel_s = None
    vel_a_energy = vel_s_energy = None
    obs_energy_mask = syn_energy_mask = None
    obs_energy_offset_s = syn_energy_offset_s = 0.0
    if need_vel:
        vel_a, vel_a_energy, obs_pad = _integrate_acc_to_vel(acc_data, dt, fmin=fmin, return_padded=True)
        vel_s, vel_s_energy, syn_pad = _integrate_acc_to_vel(acc_syn, dt, fmin=fmin, return_padded=True)
        obs_energy_mask = np.pad(obs_mask, (obs_pad, obs_pad), mode="constant", constant_values=False) if obs_pad else obs_mask
        syn_energy_mask = np.pad(syn_mask, (syn_pad, syn_pad), mode="constant", constant_values=False) if syn_pad else syn_mask
        obs_energy_offset_s = -float(obs_pad) * float(dt)
        syn_energy_offset_s = -float(syn_pad) * float(dt)
    disp_a = _integrate_acc_to_disp(acc_data, dt, fmin=fmin) if need_disp else None
    disp_s = _integrate_acc_to_disp(acc_syn, dt, fmin=fmin) if need_disp else None

    if 'C1' in keys or 'C3' in keys:
        (dur_a_obs, dur_a_syn, C1_score), (IA_obs, IA_syn, C3_score) = compute_arias(acc_data, acc_syn, dt, compute_scores)
        g = 981.0
        IA_obs_t = (np.pi / (2 * g)) * _cumtrapz_sq(acc_data, dt)
        IA_syn_t = (np.pi / (2 * g)) * _cumtrapz_sq(acc_syn, dt)
        arias_obs_window = _duration_window_5_95(IA_obs_t, dt, obs_mask, "obs_C1")
        arias_syn_window = _duration_window_5_95(IA_syn_t, dt, syn_mask, "syn_C1")
        arias_status, arias_reason = _merge_status_reasons(arias_obs_window, arias_syn_window)
        arias_ok = arias_status == "ok"
        if 'C1' in keys:
            out.update({
                'C1_obs': dur_a_obs if arias_obs_window.get("status") == "ok" else np.nan,
                'C1_syn': dur_a_syn if arias_syn_window.get("status") == "ok" else np.nan,
                'C1_obs_window_start_s': _finite_or_nan(arias_obs_window.get("t5")),
                'C1_obs_window_end_s': _finite_or_nan(arias_obs_window.get("t95")),
                'C1_syn_window_start_s': _finite_or_nan(arias_syn_window.get("t5")),
                'C1_syn_window_end_s': _finite_or_nan(arias_syn_window.get("t95")),
                'C1_status': arias_status,
                'C1_reason': arias_reason,
            })
            if compute_scores: out['C1_score'] = C1_score if arias_ok else np.nan
        if 'C3' in keys:
            out.update({
                'C3_obs': IA_obs if arias_obs_window.get("status") == "ok" else np.nan,
                'C3_syn': IA_syn if arias_syn_window.get("status") == "ok" else np.nan,
                'C3_status': arias_status,
                'C3_reason': arias_reason,
            })
            if compute_scores: out['C3_score'] = C3_score if arias_ok else np.nan

    energy_obs_window = None
    energy_syn_window = None
    energy_status = "ok"
    energy_reason = ""
    energy_ok = True
    if ('C2' in keys or 'C4' in keys or 'C13' in keys) and (vel_a is not None) and (vel_s is not None):
        (dur_c2_obs, dur_c2_syn, C2_score), (IE_obs, IE_syn, C4_score) = compute_duration(vel_a_energy, vel_s_energy, dt, compute_scores)
        IE_obs_t = _cumtrapz_sq(vel_a_energy, dt)
        IE_syn_t = _cumtrapz_sq(vel_s_energy, dt)
        energy_obs_window = _duration_window_5_95(IE_obs_t, dt, obs_energy_mask, "obs_C2", time_offset_s=obs_energy_offset_s)
        energy_syn_window = _duration_window_5_95(IE_syn_t, dt, syn_energy_mask, "syn_C2", time_offset_s=syn_energy_offset_s)
        energy_status, energy_reason = _merge_status_reasons(energy_obs_window, energy_syn_window)
        energy_ok = energy_status == "ok"
        if 'C2' in keys:
            out.update({
                'C2_obs': dur_c2_obs if energy_obs_window.get("status") == "ok" else np.nan,
                'C2_syn': dur_c2_syn if energy_syn_window.get("status") == "ok" else np.nan,
                'C2_obs_window_start_s': _finite_or_nan(energy_obs_window.get("t5")),
                'C2_obs_window_end_s': _finite_or_nan(energy_obs_window.get("t95")),
                'C2_syn_window_start_s': _finite_or_nan(energy_syn_window.get("t5")),
                'C2_syn_window_end_s': _finite_or_nan(energy_syn_window.get("t95")),
                'C2_status': energy_status,
                'C2_reason': energy_reason,
            })
            if compute_scores: out['C2_score'] = C2_score if energy_ok else np.nan
        if 'C4' in keys:
            out.update({
                'C4_obs': IE_obs if energy_obs_window.get("status") == "ok" else np.nan,
                'C4_syn': IE_syn if energy_syn_window.get("status") == "ok" else np.nan,
                'C4_status': energy_status,
                'C4_reason': energy_reason,
            })
            if compute_scores: out['C4_score'] = C4_score if energy_ok else np.nan
    # Peaks using Anderson kernel (fix for C5–C7)
    if 'C5' in keys:
        pga_obs = _peak_abs(acc_data)
        pga_syn = _peak_abs(acc_syn)
        out.update({'C5_obs': pga_obs, 'C5_syn': pga_syn})
        if compute_scores:
            out['C5_score'] = _eval_score(pga_obs, pga_syn)
    if 'C6' in keys and (vel_a is not None) and (vel_s is not None):
        pgv_obs = _peak_abs(vel_a)
        pgv_syn = _peak_abs(vel_s)
        out.update({'C6_obs': pgv_obs, 'C6_syn': pgv_syn})
        if compute_scores:
            out['C6_score'] = _eval_score(pgv_obs, pgv_syn)
    if 'C7' in keys and (disp_a is not None) and (disp_s is not None):
        pgd_obs = _peak_abs(disp_a)
        pgd_syn = _peak_abs(disp_s)
        out.update({'C7_obs': pgd_obs, 'C7_syn': pgd_syn})
        if compute_scores:
            out['C7_score'] = _eval_score(pgd_obs, pgd_syn)

    if 'C8' in keys:
        psa_obs, psa_syn, C8_score = compute_C8(acc_data, acc_syn, rs_freqs, dt, damping=0.05, compute_scores=compute_scores, fmin=fmin, fmax=fmax)
        out.update({'C8_obs': psa_obs, 'C8_syn': psa_syn})
        if compute_scores:
            out['C8_score'] = C8_score
    if 'C9' in keys:
        if fmin is None or fmax is None:
            # Fallback for old behavior if band is not passed
            fmin_c9, fmax_c9 = float(rs_freqs.min()), float(rs_freqs.max())
        else:
            fmin_c9, fmax_c9 = fmin, fmax
        fas_obs, fas_syn, C9_score = compute_C9(acc_data, acc_syn, dt, fmin=fmin_c9, fmax=fmax_c9, compute_scores=compute_scores)
        out.update({'C9_obs': fas_obs, 'C9_syn': fas_syn})
        if compute_scores:
            out['C9_score'] = C9_score

    if 'C10' in keys:
        r0 = compute_cross_correlation_zero_lag(acc_data, acc_syn)
        out['C10_val'] = r0
        if compute_scores:
            out['C10_score'] = 10.0 * max(r0, 0.0) if np.isfinite(r0) else 0.0

    if ('C11' in keys) or ('C12' in keys):
        # Use band info to set a sane lag cap; ensure >= 2*dt
        f_for_lag = fmax_for_lag or fmax
        if f_for_lag is not None:
            lag_cap_s = max(2.0 * dt, 1.0 / max(f_for_lag, 1e-6))
        else:
            lag_cap_s = max(2.0 * dt, 1.0)  # default 1 s, at least two samples
        C11_score, C12_score, lag_s, r_peak, lag_cap_s_used = compute_phase_metrics(acc_data, acc_syn, dt, lag_cap_s, override_lag_s=override_lag_s)
        if 'C11' in keys:
            if compute_scores: out['C11_score'] = C11_score
            out['C11_val'] = lag_s / lag_cap_s_used if lag_cap_s_used > 0 and np.isfinite(lag_s) else 0.0
            out['C11_lag_s'] = lag_s if np.isfinite(lag_s) else np.nan
        if 'C12' in keys:
            if compute_scores: out['C12_score'] = C12_score
            out['C12_val'] = r_peak if np.isfinite(r_peak) else np.nan

    phase_metric_map = {
        "P": ("C11P", "C12P"),
        "S": ("C11S", "C12S"),
    }
    for phase, (delay_key, corr_key) in phase_metric_map.items():
        if delay_key not in keys and corr_key not in keys:
            continue
        f_for_lag = fmax_for_lag or fmax
        if f_for_lag is not None:
            phase_lag_cap_s = max(2.0 * dt, 1.0 / max(f_for_lag, 1e-6))
        else:
            phase_lag_cap_s = max(2.0 * dt, 1.0)
        phase_result = compute_arrival_phase_metrics(
            acc_data,
            acc_syn,
            dt,
            _pick_value(arrival_picks, phase, "obs"),
            _pick_value(arrival_picks, phase, "syn"),
            phase,
            obs_valid_mask=obs_mask,
            syn_valid_mask=syn_mask,
            lag_cap_s=phase_lag_cap_s,
            window_before_s=arrival_window_before_s,
            window_after_s=arrival_window_after_s,
            obs_probability=_pick_probability(arrival_picks, phase, "obs"),
            syn_probability=_pick_probability(arrival_picks, phase, "syn"),
        )
        if delay_key in keys:
            out[f"{delay_key}_lag_s"] = float(phase_result["lag_s"])
            out[f"{delay_key}_confidence"] = float(phase_result["confidence"])
            out[f"{delay_key}_status"] = str(phase_result["status"])
            out[f"{delay_key}_reason"] = str(phase_result["reason"])
            if compute_scores:
                out[f"{delay_key}_score"] = float(phase_result["score"])
        if corr_key in keys:
            out[f"{corr_key}_val"] = float(phase_result["correlation"])
            out[f"{corr_key}_status"] = str(phase_result["status"])
            out[f"{corr_key}_reason"] = str(phase_result["reason"])
            if compute_scores:
                corr_val = float(phase_result["correlation"])
                out[f"{corr_key}_score"] = float(10.0 * max(corr_val, 0.0)) if np.isfinite(corr_val) else np.nan

    if 'C13' in keys:
        if energy_obs_window is None or energy_syn_window is None:
            _vel_a_c13, vel_a_c13_energy, obs_pad_c13 = _integrate_acc_to_vel(acc_data, dt, fmin=fmin, return_padded=True)
            _vel_s_c13, vel_s_c13_energy, syn_pad_c13 = _integrate_acc_to_vel(acc_syn, dt, fmin=fmin, return_padded=True)
            obs_mask_c13 = np.pad(obs_mask, (obs_pad_c13, obs_pad_c13), mode="constant", constant_values=False) if obs_pad_c13 else obs_mask
            syn_mask_c13 = np.pad(syn_mask, (syn_pad_c13, syn_pad_c13), mode="constant", constant_values=False) if syn_pad_c13 else syn_mask
            energy_obs_window = _duration_window_5_95(
                _cumtrapz_sq(vel_a_c13_energy, dt),
                dt,
                obs_mask_c13,
                "obs_C2",
                time_offset_s=-float(obs_pad_c13) * float(dt),
            )
            energy_syn_window = _duration_window_5_95(
                _cumtrapz_sq(vel_s_c13_energy, dt),
                dt,
                syn_mask_c13,
                "syn_C2",
                time_offset_s=-float(syn_pad_c13) * float(dt),
            )
            energy_status, energy_reason = _merge_status_reasons(energy_obs_window, energy_syn_window)
            energy_ok = energy_status == "ok"
        obs_c13_ok = energy_obs_window.get("status") == "ok"
        syn_c13_ok = energy_syn_window.get("status") == "ok"
        cav_a = _cav_over_window(acc_data, dt, _finite_or_nan(energy_obs_window.get("t5")), _finite_or_nan(energy_obs_window.get("t95"))) if obs_c13_ok else np.nan
        cav_s = _cav_over_window(acc_syn, dt, _finite_or_nan(energy_syn_window.get("t5")), _finite_or_nan(energy_syn_window.get("t95"))) if syn_c13_ok else np.nan
        out.update({
            'C13_obs': cav_a,
            'C13_syn': cav_s,
            'C13_obs_window_start_s': _finite_or_nan(energy_obs_window.get("t5")),
            'C13_obs_window_end_s': _finite_or_nan(energy_obs_window.get("t95")),
            'C13_syn_window_start_s': _finite_or_nan(energy_syn_window.get("t5")),
            'C13_syn_window_end_s': _finite_or_nan(energy_syn_window.get("t95")),
            'C13_window_basis': "respective_C2",
            'C13_status': energy_status,
            'C13_reason': energy_reason,
        })
        if compute_scores:
            out['C13_score'] = _eval_score(cav_a, cav_s) if energy_ok and np.isfinite(cav_a) and np.isfinite(cav_s) else np.nan

    # Extra PSA calculations for export
    for period, freq in zip(PSA_EXPORT_PERIODS, PSA_EXPORT_FREQS):
        key = f'PSA_T{period:.1f}'
        if key in keys:
            try:
                psa_obs = _psa_newmark(acc_data, dt, freq, zeta=0.05)
                psa_syn = _psa_newmark(acc_syn, dt, freq, zeta=0.05)
                out.update({
                    f'{key}_obs': psa_obs,
                    f'{key}_syn': psa_syn,
                })
                if compute_scores:
                    out[f'{key}_score'] = _eval_score(psa_obs, psa_syn)
            except FloatingPointError:
                out.update({
                    f'{key}_obs': np.nan,
                    f'{key}_syn': np.nan,
                })
                if compute_scores:
                    out[f'{key}_score'] = np.nan

    if any(k in keys for k in _RMS_KEYS):
        obs_rms = _rms(acc_data)
        syn_rms = _rms(acc_syn)
        if 'obs_rms' in keys or 'rms_obs' in keys:
            out['rms_obs'] = obs_rms
        if 'syn_rms' in keys or 'rms_syn' in keys:
            out['rms_syn'] = syn_rms
        if 'rms_ratio' in keys: out['rms_ratio'] = (obs_rms / syn_rms) if syn_rms > 1e-12 else np.nan

    _attach_residual_columns(out)
    return out
