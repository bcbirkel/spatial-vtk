"""Horizontal component rotation helpers."""

from __future__ import annotations

import numpy as np


def rotate_ne_to_rt(north, east, backazimuth_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """Rotate north/east components to radial/transverse components.

    Parameters
    ----------
    north, east
        North and east component samples.
    backazimuth_deg
        Backazimuth from station to source in degrees.

    Returns
    -------
    tuple of numpy.ndarray
        Radial and transverse component arrays.
    """

    n = np.asarray(north, dtype=float)
    e = np.asarray(east, dtype=float)
    if n.shape != e.shape:
        raise ValueError("north and east arrays must have the same shape.")
    baz = np.deg2rad(float(backazimuth_deg))
    radial = -np.cos(baz) * n - np.sin(baz) * e
    transverse = np.sin(baz) * n - np.cos(baz) * e
    return radial, transverse


def rotate_rt_to_ne(radial, transverse, backazimuth_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """Rotate radial/transverse components back to north/east components."""

    r = np.asarray(radial, dtype=float)
    t = np.asarray(transverse, dtype=float)
    if r.shape != t.shape:
        raise ValueError("radial and transverse arrays must have the same shape.")
    baz = np.deg2rad(float(backazimuth_deg))
    north = -np.cos(baz) * r + np.sin(baz) * t
    east = -np.sin(baz) * r - np.cos(baz) * t
    return north, east
