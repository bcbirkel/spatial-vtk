"""Frequency-band configuration helpers for metric calculations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

DEFAULT_BANDS: dict[str, tuple[float, float]] = {
    "5-8s": (0.125, 0.2),
    "3-5s": (0.2, 0.33),
    "2-3s": (0.33, 0.5),
    "1-2s": (0.5, 1.0),
}
BANDS: dict[str, tuple[float, float]] = dict(DEFAULT_BANDS)
TARGET_FS = 40.0
FILT_ORDER = 4
DEBUG = False


def dbg(message: str) -> None:
    """Print a debug message when module-level debugging is enabled.

    Parameters
    ----------
    message
        Message to print.

    Returns
    -------
    None
        This function only writes to standard output when debugging is enabled.
    """

    if DEBUG:
        print(f"[spatial-vtk] {message}")


def set_bands(bands: Mapping[str, tuple[float, float]]) -> None:
    """Replace the active metric passbands.

    Parameters
    ----------
    bands
        Mapping from band label to ``(low_hz, high_hz)`` frequency tuple.

    Returns
    -------
    None
        Updates the module-level ``BANDS`` mapping in place.
    """

    BANDS.clear()
    BANDS.update({str(label): (float(lo), float(hi)) for label, (lo, hi) in bands.items()})


def set_target_fs(fs: float) -> None:
    """Set the target sampling rate used by waveform helpers.

    Parameters
    ----------
    fs
        Sampling rate in Hz.

    Returns
    -------
    None
        Updates the module-level ``TARGET_FS`` value.
    """

    global TARGET_FS
    TARGET_FS = float(fs)


def bands_from_logspace(
    min_freq: float,
    max_freq: float,
    n_bands: int,
    *,
    label_format: str = "{low:.3g}-{high:.3g}Hz",
) -> dict[str, tuple[float, float]]:
    """Build logarithmically spaced frequency bands.

    Parameters
    ----------
    min_freq, max_freq
        Frequency range in Hz.
    n_bands
        Number of adjacent bands to create.
    label_format
        Format string with ``low`` and ``high`` fields.

    Returns
    -------
    dict
        Mapping from generated band labels to frequency tuples.
    """

    import numpy as np

    if min_freq <= 0 or max_freq <= 0:
        raise ValueError("min_freq and max_freq must be positive.")
    if max_freq <= min_freq:
        raise ValueError("max_freq must be greater than min_freq.")
    if n_bands < 1:
        raise ValueError("n_bands must be at least 1.")
    edges = np.logspace(np.log10(float(min_freq)), np.log10(float(max_freq)), int(n_bands) + 1)
    return {
        label_format.format(low=edges[i], high=edges[i + 1]): (float(edges[i]), float(edges[i + 1]))
        for i in range(int(n_bands))
    }


def bands_from_list(
    edges: Iterable[float],
    *,
    label_format: str = "{low:.3g}-{high:.3g}Hz",
) -> dict[str, tuple[float, float]]:
    """Build adjacent frequency bands from ordered frequency edges.

    Parameters
    ----------
    edges
        Ordered frequency edges in Hz.
    label_format
        Format string with ``low`` and ``high`` fields.

    Returns
    -------
    dict
        Mapping from generated band labels to adjacent frequency tuples.
    """

    values = [float(edge) for edge in edges]
    if len(values) < 2:
        raise ValueError("At least two edges are required.")
    if any(value <= 0 for value in values):
        raise ValueError("All frequency edges must be positive.")
    if any(high <= low for low, high in zip(values, values[1:], strict=False)):
        raise ValueError("Frequency edges must be strictly increasing.")
    return {
        label_format.format(low=low, high=high): (low, high)
        for low, high in zip(values, values[1:], strict=False)
    }
