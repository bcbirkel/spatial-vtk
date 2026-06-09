"""Public metric row builders.

Purpose
-------
This module defines the standardized long metric row shape used by the public
metrics workflow. It keeps scalar and period-specific rows consistent across
Python, CLI, and notebooks.

Usage examples
--------------
Build one long metric row:
  ``row = build_metric_value_row(metric_group="amplitude", metric="PGA", value_obs=1.2, value_syn=1.0)``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from spatial_vtk.metrics.calculate.transforms import VALID_TRANSFORMS, compare_metric_values


METRIC_CONTEXT_COLUMNS: tuple[str, ...] = (
    "event_id",
    "station",
    "component",
    "model",
    "passband",
)
METRIC_VALUE_COLUMNS: tuple[str, ...] = (
    "metric_group",
    "metric",
    "period_s",
    "value_obs",
    "value_syn",
)
METRIC_QC_COLUMNS: tuple[str, ...] = (
    "obs_qc_status",
    "obs_qc_reason",
    "syn_qc_status",
    "syn_qc_reason",
    "comparison_qc_status",
    "comparison_qc_reason",
)
LONG_METRIC_COLUMNS: tuple[str, ...] = (
    *METRIC_CONTEXT_COLUMNS,
    *METRIC_VALUE_COLUMNS,
    *VALID_TRANSFORMS,
    *METRIC_QC_COLUMNS,
)


@dataclass(frozen=True)
class MetricValueRow:
    """Container for one long metric row.

    Parameters
    ----------
    metric_group
        Public metric family such as ``amplitude`` or ``spectral``.
    metric
        Public metric name such as ``PGA`` or ``PSA``.
    value_obs
        Observed metric value, if available.
    value_syn
        Synthetic metric value, if available.
    period_s
        Spectral period in seconds for period-specific rows.
    context
        Optional event/station/model/passband metadata.
    qc
        Optional QC provenance fields.
    transforms
        Requested observed/synthetic transforms.

    Returns
    -------
    MetricValueRow
        Immutable row object that can be converted to a dictionary.
    """

    metric_group: str
    metric: str
    value_obs: float = np.nan
    value_syn: float = np.nan
    period_s: float | None = None
    context: dict[str, Any] = field(default_factory=dict)
    qc: dict[str, Any] = field(default_factory=dict)
    transforms: tuple[str, ...] = VALID_TRANSFORMS

    def to_dict(self) -> dict[str, Any]:
        """Return this metric row as a flat dictionary.

        Parameters
        ----------
        self
            Metric row instance.

        Returns
        -------
        dict[str, Any]
            Standardized long metric row.
        """

        row: dict[str, Any] = {column: self.context.get(column, np.nan) for column in METRIC_CONTEXT_COLUMNS}
        row.update(
            {
                "metric_group": self.metric_group,
                "metric": self.metric,
                "period_s": np.nan if self.period_s is None else float(self.period_s),
                "value_obs": _finite_or_nan(self.value_obs),
                "value_syn": _finite_or_nan(self.value_syn),
            }
        )
        for column in VALID_TRANSFORMS:
            row[column] = np.nan
        if np.isfinite(row["value_obs"]) and np.isfinite(row["value_syn"]):
            row.update(compare_metric_values(row["value_obs"], row["value_syn"], transforms=self.transforms))
        for column in METRIC_QC_COLUMNS:
            row[column] = self.qc.get(column, np.nan)
        for key, value in self.context.items():
            row.setdefault(key, value)
        for key, value in self.qc.items():
            row.setdefault(key, value)
        return row


def build_metric_value_row(
    *,
    metric_group: str,
    metric: str,
    value_obs: float = np.nan,
    value_syn: float = np.nan,
    period_s: float | None = None,
    transforms: tuple[str, ...] = VALID_TRANSFORMS,
    **metadata: Any,
) -> dict[str, Any]:
    """Build one standardized long metric row.

    Parameters
    ----------
    metric_group
        Public metric family.
    metric
        Public metric name.
    value_obs
        Observed metric value.
    value_syn
        Synthetic metric value.
    period_s
        Optional period for spectral metrics.
    transforms
        Requested comparison transforms.
    metadata
        Additional context or QC columns.

    Returns
    -------
    dict[str, Any]
        Standardized long metric row.
    """

    qc = {key: metadata.pop(key) for key in list(metadata) if key in METRIC_QC_COLUMNS}
    return MetricValueRow(
        metric_group=metric_group,
        metric=metric,
        value_obs=value_obs,
        value_syn=value_syn,
        period_s=period_s,
        context=dict(metadata),
        qc=qc,
        transforms=tuple(transforms),
    ).to_dict()


def build_spectral_metric_rows(
    *,
    metric: str,
    periods_s,
    values_obs=None,
    values_syn=None,
    transforms: tuple[str, ...] = VALID_TRANSFORMS,
    **metadata: Any,
) -> list[dict[str, Any]]:
    """Build one long metric row per spectral period.

    Parameters
    ----------
    metric
        Spectral metric name, usually ``PSA`` or ``FAS``.
    periods_s
        Period grid in seconds.
    values_obs
        Observed values aligned with ``periods_s``.
    values_syn
        Synthetic values aligned with ``periods_s``.
    transforms
        Requested comparison transforms.
    metadata
        Context or QC columns copied to every row.

    Returns
    -------
    list[dict[str, Any]]
        Standardized long spectral rows.
    """

    periods = np.asarray(tuple(periods_s), dtype=float)
    obs = _coerce_value_array(values_obs, periods.size)
    syn = _coerce_value_array(values_syn, periods.size)
    rows: list[dict[str, Any]] = []
    for idx, period_s in enumerate(periods):
        rows.append(
            build_metric_value_row(
                metric_group="spectral",
                metric=metric,
                period_s=float(period_s),
                value_obs=obs[idx],
                value_syn=syn[idx],
                transforms=transforms,
                **metadata,
            )
        )
    return rows


def _coerce_value_array(values, size: int) -> np.ndarray:
    """Return a float array of requested size.

    Parameters
    ----------
    values
        Values to coerce, or ``None``.
    size
        Expected output length.

    Returns
    -------
    numpy.ndarray
        Float array padded or cropped to ``size``.
    """

    out = np.full(int(size), np.nan, dtype=float)
    if values is None:
        return out
    arr = np.asarray(values, dtype=float).reshape(-1)
    n = min(out.size, arr.size)
    if n:
        out[:n] = arr[:n]
    return out


def _finite_or_nan(value: Any) -> float:
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


__all__ = [
    "LONG_METRIC_COLUMNS",
    "METRIC_CONTEXT_COLUMNS",
    "METRIC_QC_COLUMNS",
    "METRIC_VALUE_COLUMNS",
    "MetricValueRow",
    "build_metric_value_row",
    "build_spectral_metric_rows",
]
