"""Shared helpers for spatial statistics calculations.

Purpose
-------
This module keeps small numeric, distance, and labeling utilities in one place
so public spatial-statistics modules do not import private workflow scripts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence
import re

import numpy as np
import pandas as pd

EARTH_RADIUS_KM = 6371.0088
DEFAULT_MAX_DISTANCE_KM = 200.0
DEFAULT_BIN_WIDTH_KM = 10.0
DEFAULT_MAX_PAIRS_PER_EVENT = 20000
DEFAULT_DIRECTION_BIN_WIDTH_DEG = 45.0
DEFAULT_BLOCK_SIZE_KM = 50.0
DEFAULT_BLOCK_PREDICTION_K = 8
DEFAULT_BLOCK_DISTANCE_POWER = 2.0
DEFAULT_CLUSTER_MIN_K = 2
DEFAULT_CLUSTER_MAX_K = 6
DEFAULT_CLUSTER_MIN_METRICS_PER_STATION = 2

METRIC_DISPLAY_NAMES = {
    "C1": "Arias Duration (5-95%)",
    "C2": "Energy Duration (5-95%)",
    "C3": "Arias Intensity",
    "C4": "Energy Integral",
    "C5": "Peak Acceleration",
    "C6": "Peak Velocity",
    "C7": "Peak Displacement",
    "C8": "Response Spectra",
    "C9": "Fourier Spectra",
    "C10": "Cross Correlation",
    "C11": "Phase Delay",
    "C11P": "P Arrival Delay",
    "C11S": "S Arrival Delay",
    "C12": "Aligned Cross Correlation",
    "C12P": "P Delay Whole-Waveform Correlation",
    "C12S": "S Delay Whole-Waveform Correlation",
    "C13": "Cumulative Absolute Velocity",
}


def safe_token(value: object) -> str:
    """Return a filesystem-safe token for a label.

    Parameters
    ----------
    value
        Raw value such as a metric name, model name, or event id.

    Returns
    -------
    str
        Token containing only conservative filename characters.
    """

    text = "" if value is None else str(value).strip()
    if not text:
        return "unknown"
    text = re.sub(r"[^A-Za-z0-9._=-]+", "_", text).strip("_")
    return text or "unknown"


def metric_sort_key(metric: str) -> tuple[int, float | int | str]:
    """Return a stable sort key for C metrics, PSA periods, and RMS residuals.

    Parameters
    ----------
    metric
        Metric stem such as ``C5``, ``PSA_T3.0``, ``rms_ratio``, or ``rms``.

    Returns
    -------
    tuple
        Natural ordering key for metric lists.
    """

    token = str(metric)
    c_match = re.fullmatch(r"C(\d+)[A-Za-z]*", token, flags=re.IGNORECASE)
    if c_match:
        return (0, int(c_match.group(1)))
    psa_match = re.fullmatch(r"PSA_T([0-9]+(?:\.[0-9]+)?)", token, flags=re.IGNORECASE)
    if psa_match:
        return (1, float(psa_match.group(1)))
    if token.lower() in {"rms", "rms_ratio"}:
        return (2, 0)
    return (3, token.lower())


def metric_label(metric: str) -> str:
    """Return a human-readable metric label.

    Parameters
    ----------
    metric
        Metric stem or metric column such as ``C5`` or ``PSA_T1.0_obs``.

    Returns
    -------
    str
        Display label suitable for docs, tables, and figures.
    """

    base = str(metric).replace("_obs", "").replace("_syn", "").replace("_score", "")
    if base.startswith("PSA_T"):
        return f"PSA T={base.replace('PSA_T', '')} s"
    return METRIC_DISPLAY_NAMES.get(base, base)


def normalize_passband(label: object) -> str:
    """Normalize one passband label to ``"<low>-<high> sec"`` form.

    Parameters
    ----------
    label
        Raw label such as ``1-2s``, ``1-2 sec``, or ``raw``.

    Returns
    -------
    str
        Normalized passband label.
    """

    text = str(label or "").strip().lower()
    if text == "raw":
        return "raw"
    text = text.replace("seconds", "sec").replace("second", "sec").replace(" ", "")
    if text.endswith("sec"):
        text = text[:-3]
    if text.endswith("s"):
        text = text[:-1]
    return f"{text} sec" if text else "unknown sec"


def as_float_series(series: pd.Series) -> pd.Series:
    """Return one numeric series with infinite values converted to NaN.

    Parameters
    ----------
    series
        Input pandas series.

    Returns
    -------
    pandas.Series
        Numeric series aligned to the input index.
    """

    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)


def coalesce_column(df: pd.DataFrame, candidates: Sequence[str], *, default: object = np.nan) -> pd.Series:
    """Return the first matching dataframe column or a default-filled series.

    Parameters
    ----------
    df
        Input table.
    candidates
        Candidate column names in priority order.
    default
        Value used when none of the candidates exists.

    Returns
    -------
    pandas.Series
        Selected or default series aligned to ``df``.
    """

    for name in candidates:
        if name in df.columns:
            return df[name]
    return pd.Series([default] * len(df), index=df.index)


def infer_model_from_source(source_path: str | Path | None) -> str:
    """Infer a fallback model label from a metrics source path.

    Parameters
    ----------
    source_path
        Optional path to a source table.

    Returns
    -------
    str
        Parent directory name, file stem, or ``"unknown"``.
    """

    if not source_path:
        return "unknown"
    path = Path(source_path)
    return path.parent.name or path.stem or "unknown"


def haversine_km(lat1: object, lon1: object, lat2: object, lon2: object) -> np.ndarray:
    """Compute great-circle distances for matched coordinate arrays.

    Parameters
    ----------
    lat1, lon1, lat2, lon2
        Scalars or array-like coordinates in decimal degrees.

    Returns
    -------
    numpy.ndarray
        Distances in kilometers.
    """

    lat1_rad = np.radians(np.asarray(lat1, dtype=float))
    lat2_rad = np.radians(np.asarray(lat2, dtype=float))
    dlat = lat2_rad - lat1_rad
    dlon = np.radians(np.asarray(lon2, dtype=float) - np.asarray(lon1, dtype=float))
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def lonlat_to_xy_km(lat: np.ndarray, lon: np.ndarray, *, lat0_deg: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Project lon/lat to a local tangent-plane approximation in kilometers.

    Parameters
    ----------
    lat, lon
        Coordinate arrays in decimal degrees.
    lat0_deg
        Optional reference latitude for longitude scaling.

    Returns
    -------
    tuple of numpy.ndarray
        X and Y coordinates in kilometers.
    """

    lat_arr = np.asarray(lat, dtype=float)
    lon_arr = np.asarray(lon, dtype=float)
    lat_rad = np.radians(lat_arr)
    lon_rad = np.radians(lon_arr)
    lat0 = float(np.nanmean(lat_rad)) if lat0_deg is None else float(np.radians(lat0_deg))
    return EARTH_RADIUS_KM * lon_rad * np.cos(lat0), EARTH_RADIUS_KM * lat_rad
