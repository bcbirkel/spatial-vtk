"""Shared scatter-fit helpers for Spatial-VTK figures.

Purpose
-------
This module centralizes optional fitted-line behavior for scatter-style plots
so public plotting functions expose the same fit keywords and legend labels.

Usage examples
--------------
Draw a LOWESS line on an axis:
  ``draw_scatter_fit(ax, x, y, fit_method="lowess", color="tab:blue")``
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


if TYPE_CHECKING:
    FitMethod = str | Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray] | pd.DataFrame] | None
else:
    # Avoid evaluating PEP 604 unions against ``tuple[...]`` at import time on
    # older local interpreters used for lightweight validation.
    FitMethod = object


def draw_scatter_fit(
    ax: plt.Axes,
    x: np.ndarray,
    y: np.ndarray,
    *,
    fit_method: FitMethod,
    lowess_frac: float = 0.65,
    color: object = "black",
    label: str | None = None,
    linewidth: float = 1.3,
    alpha: float = 0.88,
) -> None:
    """Draw an optional fitted line for one scatter group.

    Parameters
    ----------
    ax
        Target Matplotlib axis.
    x, y
        Numeric finite x/y arrays.
    fit_method
        ``"point-to-point"``, ``"best"``, ``"linear"``, ``"inverse"``,
        ``"inverse-square"``, ``"quadratic"``, ``"exponential-decay"``,
        ``"lowess"``, a callable, or ``None``.
    lowess_frac
        Fraction of points used by LOWESS.
    color, label, linewidth, alpha
        Matplotlib display controls.

    Returns
    -------
    None
        The fitted line is added to ``ax`` when possible.
    """

    if fit_method is None or len(x) < 2:
        return
    finite = np.isfinite(x) & np.isfinite(y)
    if int(np.count_nonzero(finite)) < 2:
        return
    x = np.asarray(x[finite], dtype=float)
    y = np.asarray(y[finite], dtype=float)
    order = np.argsort(x)
    x_sorted = x[order]
    y_sorted = y[order]
    method = fit_method
    method_name = "custom"
    if callable(method):
        fit_x, fit_y = _call_user_fit(method, x_sorted, y_sorted)
    else:
        method_name = normalize_fit_method(method)
        if method_name == "point-to-point":
            fit_x, fit_y = x_sorted, y_sorted
        elif method_name == "linear":
            fit_x, fit_y = _polynomial_fit(x_sorted, y_sorted, degree=1)
        elif method_name == "inverse":
            fit_x, fit_y = _inverse_fit(x_sorted, y_sorted, power=1)
        elif method_name == "inverse-square":
            fit_x, fit_y = _inverse_fit(x_sorted, y_sorted, power=2)
        elif method_name == "quadratic":
            fit_x, fit_y = _polynomial_fit(x_sorted, y_sorted, degree=2)
        elif method_name == "exponential-decay":
            fit_x, fit_y = _exponential_decay_fit(x_sorted, y_sorted)
        elif method_name == "lowess":
            fit_x, fit_y = _lowess_fit(x_sorted, y_sorted, frac=lowess_frac)
        elif method_name == "best":
            method_name, fit_x, fit_y = _best_fit(x_sorted, y_sorted, lowess_frac=lowess_frac)
        else:
            raise ValueError(
                "fit_method must be one of 'point-to-point', 'best', 'linear', 'inverse', "
                "'inverse-square', 'quadratic', 'exponential-decay', 'lowess', a callable, or None."
            )
    if len(fit_x) == 0:
        return
    fit_label = scatter_fit_label(method_name, x_sorted, y_sorted, fit_x, fit_y, label=label)
    ax.plot(fit_x, fit_y, color=color, linewidth=linewidth, alpha=alpha, label=fit_label)


def normalize_fit_method(method: object) -> str:
    """Normalize a public fit keyword."""

    method_name = str(method).strip().lower().replace("_", "-")
    aliases = {
        "points": "point-to-point",
        "connect": "point-to-point",
        "connected": "point-to-point",
        "1/x": "inverse",
        "reciprocal": "inverse",
        "inverse-squared": "inverse-square",
        "1/x2": "inverse-square",
        "1/x^2": "inverse-square",
        "reciprocal-square": "inverse-square",
        "x2": "quadratic",
        "x^2": "quadratic",
        "second-order": "quadratic",
        "exponential": "exponential-decay",
        "exp-decay": "exponential-decay",
    }
    return aliases.get(method_name, method_name)


def fit_method_has_legend(fit_method: FitMethod) -> bool:
    """Return whether a fit mode should force a visible legend."""

    if fit_method is None:
        return False
    if callable(fit_method):
        return True
    return normalize_fit_method(fit_method) != "point-to-point"


def scatter_fit_label(method_name: str, x: np.ndarray, y: np.ndarray, fit_x: np.ndarray, fit_y: np.ndarray, *, label: str | None) -> str:
    """Return a readable legend label for a scatter fit line."""

    if normalize_fit_method(method_name) == "point-to-point":
        return "_nolegend_"
    prefix = f"{label} " if label else ""
    slope, fit_r = fit_line_stats(x, y, fit_x, fit_y)
    if method_name.startswith("best:"):
        fit_name = scatter_fit_display_name(method_name.split(":", 1)[1])
        return f"{prefix}best fit: {fit_name} (slope={_format_fit_number(slope)}, r={_format_fit_number(fit_r)})"
    fit_name = scatter_fit_display_name(method_name)
    return f"{prefix}{fit_name} best fit (slope={_format_fit_number(slope)}, r={_format_fit_number(fit_r)})"


def scatter_fit_display_name(method_name: str) -> str:
    """Return a readable fit method name for legends."""

    normalized = normalize_fit_method(method_name)
    if normalized == "lowess":
        return "LOWESS"
    if normalized in {"linear", "inverse", "inverse-square", "quadratic", "exponential-decay"}:
        return normalized
    return "custom"


def fit_line_stats(x: np.ndarray, y: np.ndarray, fit_x: np.ndarray, fit_y: np.ndarray) -> tuple[float, float]:
    """Return overall fit-line slope and observed-vs-fit Pearson r."""

    if len(x) < 2 or len(fit_x) < 2 or len(fit_y) < 2:
        return np.nan, np.nan
    slope = _overall_fit_slope(fit_x, fit_y)
    order = np.argsort(fit_x)
    unique_fit_x, unique_indices = np.unique(fit_x[order], return_index=True)
    unique_fit_y = fit_y[order][unique_indices]
    if len(unique_fit_x) < 2:
        return slope, np.nan
    predicted = np.interp(x, unique_fit_x, unique_fit_y)
    if np.nanstd(predicted) == 0.0 or np.nanstd(y) == 0.0:
        fit_r = np.nan
    else:
        fit_r = float(np.corrcoef(y, predicted)[0, 1])
    return slope, fit_r


def _best_fit(x: np.ndarray, y: np.ndarray, *, lowess_frac: float) -> tuple[str, np.ndarray, np.ndarray]:
    """Return the highest-R-squared supported fit for sorted x/y data."""

    candidates: list[tuple[str, np.ndarray, np.ndarray]] = [
        ("linear", *_polynomial_fit(x, y, degree=1)),
        ("inverse", *_inverse_fit(x, y, power=1)),
        ("inverse-square", *_inverse_fit(x, y, power=2)),
        ("quadratic", *_polynomial_fit(x, y, degree=2)),
        ("exponential-decay", *_exponential_decay_fit(x, y)),
        ("lowess", *_lowess_fit(x, y, frac=lowess_frac)),
    ]
    scored: list[tuple[float, str, np.ndarray, np.ndarray]] = []
    for method_name, fit_x, fit_y in candidates:
        score = _fit_r_squared(x, y, fit_x, fit_y)
        if np.isfinite(score):
            scored.append((score, method_name, fit_x, fit_y))
    if not scored:
        return "best", np.array([]), np.array([])
    _score, method_name, fit_x, fit_y = max(scored, key=lambda item: item[0])
    return f"best:{method_name}", fit_x, fit_y


def _fit_r_squared(x: np.ndarray, y: np.ndarray, fit_x: np.ndarray, fit_y: np.ndarray) -> float:
    """Return R-squared between observed values and a fitted curve."""

    if len(x) < 2 or len(fit_x) < 2 or len(fit_y) < 2:
        return np.nan
    order = np.argsort(fit_x)
    unique_fit_x, unique_indices = np.unique(fit_x[order], return_index=True)
    unique_fit_y = fit_y[order][unique_indices]
    if len(unique_fit_x) < 2:
        return np.nan
    predicted = np.interp(x, unique_fit_x, unique_fit_y)
    finite = np.isfinite(predicted) & np.isfinite(y)
    if int(np.sum(finite)) < 2:
        return np.nan
    residual = y[finite] - predicted[finite]
    total = y[finite] - float(np.nanmean(y[finite]))
    ss_total = float(np.nansum(total**2))
    if ss_total <= 0.0:
        return np.nan
    return float(1.0 - np.nansum(residual**2) / ss_total)


def _overall_fit_slope(fit_x: np.ndarray, fit_y: np.ndarray) -> float:
    """Return endpoint slope for a fitted curve."""

    delta_x = float(fit_x[-1] - fit_x[0])
    if not np.isfinite(delta_x) or abs(delta_x) < 1.0e-12:
        return np.nan
    return float((fit_y[-1] - fit_y[0]) / delta_x)


def _format_fit_number(value: float) -> str:
    """Format a compact fit diagnostic for legends."""

    if not np.isfinite(value):
        return "n/a"
    return f"{value:.3g}"


def _call_user_fit(
    fit_function: Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray] | pd.DataFrame],
    x: np.ndarray,
    y: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Call a user-defined fit function and normalize its output."""

    result = fit_function(x, y)
    if isinstance(result, pd.DataFrame):
        if "x" not in result.columns or "y" not in result.columns:
            raise ValueError("User fit dataframe must contain 'x' and 'y' columns.")
        return result["x"].to_numpy(dtype=float), result["y"].to_numpy(dtype=float)
    fit_x, fit_y = result
    return np.asarray(fit_x, dtype=float), np.asarray(fit_y, dtype=float)


def _polynomial_fit(x: np.ndarray, y: np.ndarray, *, degree: int) -> tuple[np.ndarray, np.ndarray]:
    """Return a least-squares polynomial fit line for sorted x/y values."""

    if len(x) < degree + 1:
        return np.array([]), np.array([])
    coefficients = np.polyfit(x, y, deg=degree)
    fit_x = np.linspace(float(np.nanmin(x)), float(np.nanmax(x)), 100)
    return fit_x, np.polyval(coefficients, fit_x)


def _inverse_fit(x: np.ndarray, y: np.ndarray, *, power: int) -> tuple[np.ndarray, np.ndarray]:
    """Return a least-squares inverse-distance fit line."""

    if len(x) < 2:
        return np.array([]), np.array([])
    finite = np.isfinite(x) & np.isfinite(y) & (np.abs(x) > 1.0e-12)
    if int(np.sum(finite)) < 2:
        return np.array([]), np.array([])
    x_valid = x[finite]
    y_valid = y[finite]
    predictor = 1.0 / np.power(x_valid, int(power))
    coefficient, intercept = np.polyfit(predictor, y_valid, deg=1)
    fit_x = np.linspace(float(np.nanmin(x_valid)), float(np.nanmax(x_valid)), 100)
    fit_y = intercept + coefficient / np.power(fit_x, int(power))
    return fit_x, fit_y


def _exponential_decay_fit(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return a simple exponential-decay fit for sorted x/y values."""

    if len(x) < 3:
        return np.array([]), np.array([])
    try:
        from scipy.optimize import curve_fit
        from scipy.optimize import OptimizeWarning

        def model(values: np.ndarray, offset: float, amplitude: float, scale: float) -> np.ndarray:
            return offset + amplitude * np.exp(-values / max(scale, 1.0e-6))

        initial = (float(np.nanmedian(y)), float(y[0] - np.nanmedian(y)), max(float(np.nanmax(x) - np.nanmin(x)), 1.0))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", OptimizeWarning)
            params, _cov = curve_fit(model, x, y, p0=initial, maxfev=5000)
        fit_x = np.linspace(float(np.nanmin(x)), float(np.nanmax(x)), 100)
        return fit_x, model(fit_x, *params)
    except Exception:
        return np.array([]), np.array([])


def _lowess_fit(x: np.ndarray, y: np.ndarray, *, frac: float) -> tuple[np.ndarray, np.ndarray]:
    """Return a LOWESS smooth for sorted x/y values."""

    if len(x) < 3:
        return x, y
    grouped = pd.DataFrame({"x": x, "y": y}).groupby("x", as_index=False)["y"].mean()
    x_unique = grouped["x"].to_numpy(dtype=float)
    y_unique = grouped["y"].to_numpy(dtype=float)
    if len(x_unique) < 3:
        return x_unique, y_unique
    from statsmodels.nonparametric.smoothers_lowess import lowess

    smoothed = lowess(y_unique, x_unique, frac=float(np.clip(frac, 0.05, 1.0)), return_sorted=True)
    fit_x = np.linspace(float(np.nanmin(smoothed[:, 0])), float(np.nanmax(smoothed[:, 0])), 100)
    fit_y = np.interp(fit_x, smoothed[:, 0], smoothed[:, 1])
    return fit_x, fit_y


__all__ = [
    "FitMethod",
    "draw_scatter_fit",
    "fit_line_stats",
    "fit_method_has_legend",
    "normalize_fit_method",
    "scatter_fit_display_name",
]
