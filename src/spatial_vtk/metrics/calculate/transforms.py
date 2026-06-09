"""Observed/synthetic metric comparison transforms.

Purpose
-------
This module separates metric values from comparison methods. Metric functions
measure one observed or synthetic trace; transforms compare the two values.

Usage examples
--------------
Compare one PGA pair:
  ``compare_metric_values(120.0, 100.0, transforms=["log2_residual"])``
"""

from __future__ import annotations

from collections.abc import Iterable
from math import erfc

import numpy as np


VALID_TRANSFORMS: tuple[str, ...] = (
    "residual",
    "log2_residual",
    "ln_residual",
    "anderson_2004_gof",
    "olsen_mayhew_gof",
)


def residual(observed_value: float, synthetic_value: float) -> float:
    """Return the arithmetic observed-minus-synthetic residual.

    Parameters
    ----------
    observed_value
        Observed metric value.
    synthetic_value
        Synthetic metric value.

    Returns
    -------
    float
        ``observed_value - synthetic_value`` or NaN when either value is not
        finite.
    """

    obs, syn = _finite_pair(observed_value, synthetic_value)
    return float(obs - syn) if np.isfinite(obs) and np.isfinite(syn) else np.nan


def log2_residual(observed_value: float, synthetic_value: float) -> float:
    """Return the base-2 logarithmic observed/synthetic residual.

    Parameters
    ----------
    observed_value
        Observed positive metric value.
    synthetic_value
        Synthetic positive metric value.

    Returns
    -------
    float
        ``log2(observed_value / synthetic_value)`` or NaN for non-positive
        values.
    """

    obs, syn = _finite_pair(observed_value, synthetic_value)
    if obs <= 0.0 or syn <= 0.0:
        return np.nan
    return float(np.log2(obs / syn))


def ln_residual(observed_value: float, synthetic_value: float) -> float:
    """Return the natural-log observed/synthetic residual.

    Parameters
    ----------
    observed_value
        Observed positive metric value.
    synthetic_value
        Synthetic positive metric value.

    Returns
    -------
    float
        ``ln(observed_value / synthetic_value)`` or NaN for non-positive
        values.
    """

    obs, syn = _finite_pair(observed_value, synthetic_value)
    if obs <= 0.0 or syn <= 0.0:
        return np.nan
    return float(np.log(obs / syn))


def anderson_2004_gof(observed_value: float, synthetic_value: float) -> float:
    """Return the Anderson-style GOF score used by legacy C metrics.

    Parameters
    ----------
    observed_value
        Observed positive metric value.
    synthetic_value
        Synthetic positive metric value.

    Returns
    -------
    float
        Score on a 0-10 scale, where 10 is a perfect match.
    """

    obs, syn = _finite_pair(observed_value, synthetic_value)
    if obs <= 0.0 or syn <= 0.0:
        return np.nan
    denominator = min(obs, syn)
    return float(min(10.0, 10.0 * np.exp(-(((obs - syn) / denominator) ** 2))))


def olsen_mayhew_gof(observed_value: float, synthetic_value: float) -> float:
    """Return the Olsen-Mayhew broadband GOF scalar score.

    Parameters
    ----------
    observed_value
        Observed positive scalar metric value.
    synthetic_value
        Synthetic positive scalar metric value.

    Returns
    -------
    float
        Score on a 0-100 scale from Olsen and Mayhew's complementary
        error-function normalized residual.
    """

    obs, syn = _finite_pair(observed_value, synthetic_value)
    if obs <= 0.0 or syn <= 0.0:
        return np.nan
    normalized_residual = abs(2.0 * (obs - syn) / (obs + syn))
    return float(100.0 * erfc(normalized_residual))


def compare_metric_values(
    observed_value: float,
    synthetic_value: float,
    *,
    transforms: Iterable[str] = VALID_TRANSFORMS,
) -> dict[str, float]:
    """Apply requested observed/synthetic comparison transforms.

    Parameters
    ----------
    observed_value
        Observed metric value.
    synthetic_value
        Synthetic metric value.
    transforms
        Transform names to calculate.

    Returns
    -------
    dict[str, float]
        Mapping from transform name to calculated value.
    """

    out: dict[str, float] = {}
    for name in transforms:
        token = str(name).strip().lower().replace("-", "_")
        token = _TRANSFORM_ALIASES.get(token, token)
        if token not in _TRANSFORM_FUNCTIONS:
            raise ValueError(f"Unknown metric transform {name!r}. Expected one of {VALID_TRANSFORMS}.")
        out[token] = _TRANSFORM_FUNCTIONS[token](observed_value, synthetic_value)
    return out


def _finite_pair(observed_value: float, synthetic_value: float) -> tuple[float, float]:
    """Return a finite observed/synthetic pair or NaNs.

    Parameters
    ----------
    observed_value
        Observed value.
    synthetic_value
        Synthetic value.

    Returns
    -------
    tuple[float, float]
        Numeric pair with non-finite inputs converted to NaN.
    """

    obs = _finite_float(observed_value)
    syn = _finite_float(synthetic_value)
    return obs, syn


def _finite_float(value: float) -> float:
    """Return a finite float or NaN.

    Parameters
    ----------
    value
        Value to coerce.

    Returns
    -------
    float
        Finite float or NaN.
    """

    try:
        out = float(value)
    except Exception:
        return np.nan
    return out if np.isfinite(out) else np.nan


_TRANSFORM_FUNCTIONS = {
    "residual": residual,
    "log2_residual": log2_residual,
    "ln_residual": ln_residual,
    "anderson_2004_gof": anderson_2004_gof,
    "olsen_mayhew_gof": olsen_mayhew_gof,
}

_TRANSFORM_ALIASES = {
    "olsen_2011_gof": "olsen_mayhew_gof",
    "olsen_mayhew_2011_gof": "olsen_mayhew_gof",
}


__all__ = [
    "VALID_TRANSFORMS",
    "anderson_2004_gof",
    "compare_metric_values",
    "ln_residual",
    "log2_residual",
    "olsen_mayhew_gof",
    "residual",
]
