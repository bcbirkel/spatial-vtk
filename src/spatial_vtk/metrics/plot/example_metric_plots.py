"""Example metric plots for deterministic observed/synthetic trace pairs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from spatial_vtk.config.labels import metric_display_name
from spatial_vtk.metrics.calculate.gof import compute_metrics_pair
from spatial_vtk.visualize.figure_io import finish_figure


@dataclass(frozen=True)
class SyntheticMetricPair:
    """One deterministic trace-pair scenario used to explain metric behavior."""

    name: str
    observed: np.ndarray
    synthetic: np.ndarray
    dt: float


def synthetic_metric_pairs() -> list[SyntheticMetricPair]:
    """Build deterministic example trace pairs for metric demonstrations."""

    dt = 0.01
    t = np.arange(0.0, 12.0, dt)
    observed = _base_trace(t)
    return [
        SyntheticMetricPair("identical", observed, observed.copy(), dt),
        SyntheticMetricPair("amplitude_scaled", observed, 1.6 * observed, dt),
        SyntheticMetricPair("delayed", observed, _base_trace(t, p_time=2.6, s_time=5.6), dt),
        SyntheticMetricPair("spectrally_smoothed", observed, _smooth_trace(observed, sigma_samples=6.0), dt),
    ]


def build_example_metric_summary() -> list[dict[str, object]]:
    """Compute C-metric summaries for the deterministic example pairs."""

    rows: list[dict[str, object]] = []
    for pair in synthetic_metric_pairs():
        metrics = compute_metrics_pair(pair.observed, pair.synthetic, pair.dt, which=[f"C{i}" for i in range(1, 14)])
        rows.append({"scenario": pair.name, **metrics})
    return rows


def plot_example_metric_pairs(
    output_path: str | Path | None = None,
    *,
    scenarios: list[str] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot deterministic trace pairs and a small metric-score summary."""

    pairs = synthetic_metric_pairs()
    if scenarios is not None:
        wanted = set(scenarios)
        pairs = [pair for pair in pairs if pair.name in wanted]
    if not pairs:
        raise ValueError("No example metric pairs selected.")

    fig, axes = plt.subplots(len(pairs), 1, figsize=(8.0, 2.2 * len(pairs)), dpi=170, sharex=True)
    axes = np.atleast_1d(axes)
    for ax, pair in zip(axes, pairs, strict=True):
        time = np.arange(pair.observed.size) * pair.dt
        metrics = compute_metrics_pair(pair.observed, pair.synthetic, pair.dt, which=["C5", "C10", "C12"])
        ax.plot(time, pair.observed, color="#1f77b4", linewidth=1.1, label="Observed")
        ax.plot(time, pair.synthetic, color="#d62728", linewidth=1.0, alpha=0.85, label="Synthetic")
        title = (
            f"{pair.name.replace('_', ' ').title()}  "
            f"{metric_display_name('C5')} score={metrics.get('C5_score', np.nan):.2f}  "
            f"{metric_display_name('C10')}={metrics.get('C10', np.nan):.2f}  "
            f"{metric_display_name('C12')}={metrics.get('C12', np.nan):.2f}"
        )
        ax.set_title(title, fontsize=9)
        ax.set_ylabel("Amplitude")
        ax.grid(True, alpha=0.25)
    axes[-1].set_xlabel("Time (s)")
    axes[0].legend(frameon=True, loc="upper right")
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _base_trace(t: np.ndarray, *, p_time: float = 2.0, s_time: float = 5.0) -> np.ndarray:
    """Build a simple two-arrival waveform."""

    return _gaussian(t, p_time, 0.08, 0.8) - _gaussian(t, p_time + 0.18, 0.10, 0.45) + _gaussian(t, s_time, 0.18, 1.2) - _gaussian(t, s_time + 0.35, 0.24, 0.65)


def _gaussian(t: np.ndarray, center: float, width: float, amp: float) -> np.ndarray:
    """Return one Gaussian pulse."""

    return amp * np.exp(-0.5 * ((t - center) / width) ** 2)


def _smooth_trace(trace: np.ndarray, sigma_samples: float) -> np.ndarray:
    """Smooth a trace using scipy when available, otherwise a moving average."""

    try:
        from scipy.ndimage import gaussian_filter1d

        return gaussian_filter1d(trace, sigma=float(sigma_samples), mode="nearest")
    except Exception:  # pragma: no cover - scipy is a required dependency
        window = max(3, int(round(4 * sigma_samples)) | 1)
        kernel = np.ones(window, dtype=float) / float(window)
        return np.convolve(trace, kernel, mode="same")
