"""Waveform processing helpers used by metric calculations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, detrend, sosfilt, sosfiltfilt

from spatial_vtk.metrics.calculate.bands import FILT_ORDER


@dataclass(frozen=True)
class BandpassResult:
    """Filtered waveform data plus validity metadata."""

    data: np.ndarray
    dt: float
    valid_mask: np.ndarray
    low_hz: float
    high_hz: float


def amplitude_spectrum(data: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
    """Compute a one-sided amplitude spectrum.

    Parameters
    ----------
    data
        One-dimensional waveform samples.
    dt
        Sample interval in seconds.

    Returns
    -------
    tuple of numpy.ndarray
        Frequencies in Hz and corresponding one-sided amplitudes.
    """

    samples = np.asarray(data, dtype=float)
    if samples.ndim != 1:
        raise ValueError("data must be one-dimensional.")
    if samples.size == 0:
        return np.array([], dtype=float), np.array([], dtype=float)
    if dt <= 0:
        raise ValueError("dt must be positive.")
    freq = np.fft.rfftfreq(samples.size, float(dt))
    amp = np.abs(np.fft.rfft(samples)) / max(samples.size, 1)
    return freq, amp


def bandpass_with_metadata(
    data: np.ndarray,
    dt: float,
    low_hz: float,
    high_hz: float,
    *,
    order: int = FILT_ORDER,
    taper_fraction: float = 0.05,
) -> BandpassResult:
    """Bandpass filter a waveform and mark samples safe for comparison.

    Parameters
    ----------
    data
        One-dimensional waveform samples.
    dt
        Sample interval in seconds.
    low_hz, high_hz
        Bandpass corner frequencies in Hz.
    order
        Butterworth filter order.
    taper_fraction
        Fraction of the trace length masked at each edge after filtering.

    Returns
    -------
    BandpassResult
        Filtered data and a boolean validity mask.
    """

    samples = np.asarray(data, dtype=float)
    if samples.ndim != 1:
        raise ValueError("data must be one-dimensional.")
    if samples.size < 2:
        raise ValueError("data must contain at least two samples.")
    if dt <= 0:
        raise ValueError("dt must be positive.")
    if low_hz <= 0 or high_hz <= 0 or high_hz <= low_hz:
        raise ValueError("Require 0 < low_hz < high_hz.")
    nyquist = 0.5 / float(dt)
    if high_hz >= nyquist:
        raise ValueError(f"high_hz must be below Nyquist ({nyquist:g} Hz).")

    clean = np.nan_to_num(samples, nan=0.0, posinf=0.0, neginf=0.0)
    clean = detrend(clean, type="linear")
    sos = butter(int(order), [low_hz, high_hz], btype="bandpass", fs=1.0 / float(dt), output="sos")
    filtered = sosfiltfilt(sos, clean)

    mask = np.isfinite(samples)
    edge = int(round(samples.size * float(taper_fraction)))
    if edge > 0 and edge * 2 < samples.size:
        mask[:edge] = False
        mask[-edge:] = False
    return BandpassResult(filtered, float(dt), mask, float(low_hz), float(high_hz))


def lowpass_waveform(
    data: np.ndarray,
    dt: float,
    cutoff_hz: float | None,
    *,
    order: int = FILT_ORDER,
) -> np.ndarray:
    """Lowpass filter one waveform when a cutoff is configured.

    Parameters
    ----------
    data
        One-dimensional waveform samples.
    dt
        Sample interval in seconds.
    cutoff_hz
        Lowpass cutoff in Hz. ``None`` or non-positive values leave the data
        unchanged.
    order
        Butterworth filter order.

    Returns
    -------
    numpy.ndarray
        Filtered samples, or a finite copy of the original samples when no
        cutoff is configured.
    """

    samples = np.asarray(data, dtype=float)
    if samples.ndim != 1:
        raise ValueError("data must be one-dimensional.")
    if samples.size < 2:
        return samples.astype(float, copy=True)
    if dt <= 0:
        raise ValueError("dt must be positive.")
    if cutoff_hz is None:
        return samples.astype(float, copy=True)
    cutoff = float(cutoff_hz)
    if not np.isfinite(cutoff) or cutoff <= 0.0:
        return samples.astype(float, copy=True)
    nyquist = 0.5 / float(dt)
    if cutoff >= nyquist:
        raise ValueError(f"lowpass cutoff_hz must be below Nyquist ({nyquist:g} Hz).")

    clean = np.nan_to_num(samples, nan=0.0, posinf=0.0, neginf=0.0)
    clean = detrend(clean, type="linear")
    sos = butter(int(order), cutoff, btype="lowpass", fs=1.0 / float(dt), output="sos")
    padlen = 3 * (2 * len(sos) + 1)
    if clean.size > padlen:
        return sosfiltfilt(sos, clean)
    return sosfilt(sos, clean)


def apply_filter_validity_mask(data: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
    """Replace samples outside a validity mask with NaN.

    Parameters
    ----------
    data
        One-dimensional samples.
    valid_mask
        Boolean mask with the same length as ``data``.

    Returns
    -------
    numpy.ndarray
        Copy of data with invalid samples set to NaN.
    """

    out = np.asarray(data, dtype=float).copy()
    mask = np.asarray(valid_mask, dtype=bool)
    if out.shape != mask.shape:
        raise ValueError("data and valid_mask must have the same shape.")
    out[~mask] = np.nan
    return out


def trim_to_valid_window(data: np.ndarray, valid_mask: np.ndarray) -> tuple[np.ndarray, slice]:
    """Trim data to the first and last valid sample in a mask.

    Parameters
    ----------
    data
        One-dimensional samples.
    valid_mask
        Boolean validity mask.

    Returns
    -------
    tuple
        Trimmed data and the slice used to trim it.
    """

    samples = np.asarray(data)
    mask = np.asarray(valid_mask, dtype=bool)
    if samples.shape != mask.shape:
        raise ValueError("data and valid_mask must have the same shape.")
    valid = np.flatnonzero(mask)
    if valid.size == 0:
        return samples[:0], slice(0, 0)
    window = slice(int(valid[0]), int(valid[-1]) + 1)
    return samples[window], window


def trim_bandpassed_pair_to_common_valid(
    observed: BandpassResult,
    synthetic: BandpassResult,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Trim two filtered waveforms to their common valid samples.

    Parameters
    ----------
    observed, synthetic
        Filtered waveform results with matching sample intervals.

    Returns
    -------
    tuple of numpy.ndarray
        Observed samples, synthetic samples, and the common validity mask.
    """

    if not np.isclose(observed.dt, synthetic.dt):
        raise ValueError("observed and synthetic traces must have matching dt.")
    n = min(observed.data.size, synthetic.data.size)
    common_mask = observed.valid_mask[:n] & synthetic.valid_mask[:n]
    valid = np.flatnonzero(common_mask)
    if valid.size == 0:
        return observed.data[:0], synthetic.data[:0], common_mask[:0]
    window = slice(int(valid[0]), int(valid[-1]) + 1)
    window_mask = common_mask[window]
    return observed.data[:n][window][window_mask], synthetic.data[:n][window][window_mask], window_mask


def align_streams(observed_stream, synthetic_stream):
    """Trim two ObsPy streams to their common time window.

    Parameters
    ----------
    observed_stream, synthetic_stream
        ObsPy ``Stream`` objects or stream-like objects with ``copy``,
        ``trim``, and trace ``stats.starttime/endtime`` attributes.

    Returns
    -------
    tuple
        Trimmed observed and synthetic streams.
    """

    if len(observed_stream) == 0 or len(synthetic_stream) == 0:
        raise ValueError("Both streams must contain at least one trace.")
    start = max(trace.stats.starttime for trace in observed_stream + synthetic_stream)
    end = min(trace.stats.endtime for trace in observed_stream + synthetic_stream)
    if end <= start:
        raise ValueError("Streams do not share a common time window.")
    observed = observed_stream.copy().trim(starttime=start, endtime=end, pad=False)
    synthetic = synthetic_stream.copy().trim(starttime=start, endtime=end, pad=False)
    return observed, synthetic
