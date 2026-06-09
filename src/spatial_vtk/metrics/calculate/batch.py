"""Batch wrappers around the public GOF metric kernel."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np
import pandas as pd

from spatial_vtk.metrics.calculate.gof import compute_metrics_pair


def calculate_metrics_for_pairs(
    pairs: Sequence[Any],
    *,
    which: Iterable[str] | None = None,
    dt: float | None = None,
    **kwargs,
) -> pd.DataFrame:
    """Compute GOF metrics for a batch of observed/synthetic pairs.

    Parameters
    ----------
    pairs
        Sequence of mappings with ``observed``, ``synthetic``, and ``dt``
        fields, or tuples shaped like ``(observed, synthetic, dt)``.
    which
        Optional metric keys to compute.
    dt
        Optional fallback sample spacing in seconds.
    **kwargs
        Forwarded to :func:`spatial_vtk.metrics.calculate.gof.compute_metrics_pair`.

    Returns
    -------
    pandas.DataFrame
        One row per pair, preserving mapping metadata columns.
    """

    rows: list[dict[str, Any]] = []
    for item in pairs:
        metadata, observed, synthetic, resolved_dt = _coerce_pair_record(item, dt=dt)
        metrics = compute_metrics_pair(
            np.asarray(observed, dtype=float),
            np.asarray(synthetic, dtype=float),
            float(resolved_dt),
            which=which,
            **kwargs,
        )
        row = dict(metadata)
        row.update(metrics)
        rows.append(row)
    return pd.DataFrame(rows)


def calculate_metric_pair(
    observed: Any,
    synthetic: Any,
    *,
    dt: float,
    metadata: dict[str, Any] | None = None,
    which: Iterable[str] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Compute metrics for one observed/synthetic pair and attach metadata.

    Parameters
    ----------
    observed, synthetic
        One-dimensional waveform samples.
    dt
        Sample spacing in seconds.
    metadata
        Optional metadata copied into the output row.
    which
        Optional metric keys to compute.
    **kwargs
        Forwarded to :func:`compute_metrics_pair`.

    Returns
    -------
    dict
        Metadata plus metric outputs.
    """

    row = dict(metadata or {})
    row.update(compute_metrics_pair(np.asarray(observed, dtype=float), np.asarray(synthetic, dtype=float), float(dt), which=which, **kwargs))
    return row


def _coerce_pair_record(item: Any, *, dt: float | None) -> tuple[dict[str, Any], Any, Any, float]:
    """Coerce one pair record into metadata, observed, synthetic, and dt."""

    if isinstance(item, dict):
        metadata = {
            key: value
            for key, value in item.items()
            if key not in {"observed", "synthetic", "obs", "syn", "dt", "sample_interval_s"}
        }
        observed = item.get("observed", item.get("obs"))
        synthetic = item.get("synthetic", item.get("syn"))
        resolved_dt = item.get("dt", item.get("sample_interval_s", dt))
    else:
        values = tuple(item)
        if len(values) == 3:
            observed, synthetic, resolved_dt = values
        elif len(values) == 2 and dt is not None:
            observed, synthetic = values
            resolved_dt = dt
        else:
            raise ValueError("Pair tuples must be (observed, synthetic, dt), or provide dt as a keyword.")
        metadata = {}
    if observed is None or synthetic is None:
        raise ValueError("Each pair must provide observed and synthetic samples.")
    if resolved_dt is None:
        raise ValueError("Each pair must provide dt or sample_interval_s.")
    return metadata, observed, synthetic, float(resolved_dt)
