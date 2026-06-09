"""Non-figure summary tables for metric outputs.

Purpose
-------
This module contains calculation-only summary helpers used by metrics
workflows, dashboards, and spatial analysis. It does not render figures or
write files.

Usage examples
--------------
Summarize score columns by station and passband:
  ``summary = summarize_metric_scores(metrics_df)``
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd

from spatial_vtk.spatial.calculate._common import metric_sort_key


STATION_COLUMN_ALIASES: tuple[str, ...] = ("station", "station_name", "sta", "station_id")
STATION_LON_ALIASES: tuple[str, ...] = ("station_lon", "station_longitude", "sta_lon", "lon", "longitude")
STATION_LAT_ALIASES: tuple[str, ...] = ("station_lat", "station_latitude", "sta_lat", "lat", "latitude")
PASSBAND_ALIASES: tuple[str, ...] = ("passband", "band", "simulation_band")
MODEL_ALIASES: tuple[str, ...] = ("model", "simulation_model")


def residual_metric_stems(df: pd.DataFrame, *, include_named: bool = True) -> list[str]:
    """Return metric stems that have observed and synthetic value columns.

    Parameters
    ----------
    df
        Wide metric table.
    include_named
        Whether to include non-``C_i`` metric stems such as ``PSA_T1.0``.

    Returns
    -------
    list[str]
        Sorted metric stems with both ``*_obs`` and ``*_syn`` columns.
    """

    stems: list[str] = []
    for column in df.columns:
        if not str(column).endswith("_obs"):
            continue
        stem = str(column)[:-4]
        if not include_named and not re.fullmatch(r"C\d+", stem, flags=re.IGNORECASE):
            continue
        if f"{stem}_syn" in df.columns:
            stems.append(stem)
    return sorted(set(stems), key=metric_sort_key)


def score_metric_stems(df: pd.DataFrame) -> list[str]:
    """Return metric stems that have score columns.

    Parameters
    ----------
    df
        Wide metric table.

    Returns
    -------
    list[str]
        Sorted metric stems with ``*_score`` columns.
    """

    stems = [str(column)[:-6] for column in df.columns if str(column).endswith("_score")]
    return sorted(set(stems), key=metric_sort_key)


def metric_stems_by_family(df: pd.DataFrame, family: str) -> list[str]:
    """Return residual-capable metric stems for a broad metric family.

    Parameters
    ----------
    df
        Wide metric table.
    family
        Family token. Supported values include ``c``, ``legacy``, ``psa``,
        ``spectral``, and ``named``.

    Returns
    -------
    list[str]
        Sorted metric stems in the requested family.
    """

    stems = residual_metric_stems(df)
    token = str(family).strip().lower()
    if token in {"psa", "spectral"}:
        return [stem for stem in stems if stem.upper().startswith("PSA_T")]
    if token in {"c", "legacy", "ci", "c_i"}:
        return [stem for stem in stems if re.fullmatch(r"C\d+", stem, flags=re.IGNORECASE)]
    if token in {"named", "public"}:
        return [stem for stem in stems if not re.fullmatch(r"C\d+", stem, flags=re.IGNORECASE)]
    return stems


def metric_residual_series(df: pd.DataFrame, metric_stem: str, *, log_base: str = "log2") -> pd.Series | None:
    """Return finite observed/synthetic residuals for one metric stem.

    Parameters
    ----------
    df
        Wide metric table.
    metric_stem
        Metric stem such as ``C5`` or ``PSA_T3.0``.
    log_base
        Residual mode: ``log2``, ``ln``, ``log10``, or ``diff``.

    Returns
    -------
    pandas.Series or None
        Residual series aligned to ``df`` or ``None`` when required columns are
        unavailable.
    """

    obs_col = f"{metric_stem}_obs"
    syn_col = f"{metric_stem}_syn"
    if obs_col not in df.columns or syn_col not in df.columns:
        return None
    obs = pd.to_numeric(df[obs_col], errors="coerce")
    syn = pd.to_numeric(df[syn_col], errors="coerce")
    mode = str(log_base).strip().lower()
    with np.errstate(divide="ignore", invalid="ignore"):
        if mode == "diff":
            residual = obs - syn
        elif mode == "ln":
            residual = np.log(obs / syn)
        elif mode == "log10":
            residual = np.log10(obs / syn)
        elif mode == "log2":
            residual = np.log2(obs / syn)
        else:
            raise ValueError("log_base must be one of 'log2', 'ln', 'log10', or 'diff'.")
    return pd.Series(residual, index=df.index).replace([np.inf, -np.inf], np.nan)


def binned_numeric_midpoints(series: pd.Series | Sequence[float], step: float) -> tuple[np.ndarray, np.ndarray] | tuple[None, None]:
    """Return bin edges and midpoint labels for one numeric series.

    Parameters
    ----------
    series
        Numeric values.
    step
        Bin width.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray] or tuple[None, None]
        Bin edges and labels, or ``(None, None)`` for empty input.
    """

    if step <= 0.0:
        raise ValueError("step must be positive.")
    values = pd.to_numeric(pd.Series(series), errors="coerce")
    values = values[np.isfinite(values)]
    if values.empty:
        return None, None
    vmin = float(values.min())
    vmax = float(values.max())
    if not np.isfinite(vmin) or not np.isfinite(vmax):
        return None, None
    if np.isclose(vmin, vmax):
        vmax = vmin + float(step)
    start = float(step) * np.floor(vmin / float(step))
    stop = float(step) * np.ceil(vmax / float(step)) + float(step)
    bins = np.arange(start, stop + 0.5 * float(step), float(step))
    if bins.size < 2:
        bins = np.array([start, start + float(step)], dtype=float)
    labels = (bins[:-1] + bins[1:]) / 2.0
    return bins, labels


def build_station_residual_table(
    df: pd.DataFrame,
    metric_stem: str,
    *,
    log_base: str = "log2",
) -> tuple[pd.DataFrame, str] | tuple[None, None]:
    """Build one station-mean residual table for a metric stem.

    Parameters
    ----------
    df
        Wide metric table with station coordinates and metric columns.
    metric_stem
        Metric stem such as ``C5`` or ``PSA_T3.0``.
    log_base
        Residual mode passed to :func:`metric_residual_series`.

    Returns
    -------
    tuple[pandas.DataFrame, str] or tuple[None, None]
        Station-mean residual table and residual column name, or
        ``(None, None)`` when required columns are unavailable.
    """

    station_col = _first_existing_column(df, STATION_COLUMN_ALIASES)
    lon_col = _first_existing_column(df, STATION_LON_ALIASES)
    lat_col = _first_existing_column(df, STATION_LAT_ALIASES)
    if station_col is None or lon_col is None or lat_col is None:
        return None, None
    residual = metric_residual_series(df, metric_stem, log_base=log_base)
    if residual is None:
        return None, None
    residual_col = f"{metric_stem}_residual_{log_base}" if log_base != "diff" else f"{metric_stem}_residual"
    work = df[[station_col, lon_col, lat_col]].copy()
    work[residual_col] = residual
    work[lon_col] = pd.to_numeric(work[lon_col], errors="coerce")
    work[lat_col] = pd.to_numeric(work[lat_col], errors="coerce")
    work.dropna(subset=[station_col, lon_col, lat_col, residual_col], inplace=True)
    if work.empty:
        return None, None
    out = (
        work.groupby(station_col, as_index=False)
        .agg(
            station_lon=(lon_col, "mean"),
            station_lat=(lat_col, "mean"),
            **{residual_col: (residual_col, "mean")},
        )
        .rename(columns={station_col: "station"})
    )
    return out, residual_col


def station_mean_table(
    df: pd.DataFrame,
    *,
    value_columns: Sequence[str],
) -> pd.DataFrame:
    """Aggregate metric values to one row per station.

    Parameters
    ----------
    df
        Metric table with station coordinates.
    value_columns
        Numeric columns to average.

    Returns
    -------
    pandas.DataFrame
        Station-mean table with normalized ``station``, ``station_lon``, and
        ``station_lat`` columns.
    """

    station_col = _require_existing_column(df, STATION_COLUMN_ALIASES, "station")
    lon_col = _require_existing_column(df, STATION_LON_ALIASES, "station longitude")
    lat_col = _require_existing_column(df, STATION_LAT_ALIASES, "station latitude")
    selected_values = [column for column in value_columns if column in df.columns]
    if not selected_values:
        raise ValueError("No requested value_columns are present in the table.")
    work = df[[station_col, lon_col, lat_col, *selected_values]].copy()
    for column in [lon_col, lat_col, *selected_values]:
        work[column] = pd.to_numeric(work[column], errors="coerce")
    grouped = work.groupby(station_col, as_index=False).agg(
        station_lon=(lon_col, "mean"),
        station_lat=(lat_col, "mean"),
        **{column: (column, "mean") for column in selected_values},
    )
    return grouped.rename(columns={station_col: "station"})


def summarize_metric_scores(
    df: pd.DataFrame,
    *,
    group_cols: Sequence[str] | None = None,
    score_columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Summarize metric score columns by model/station/passband groups.

    Parameters
    ----------
    df
        Wide metric table.
    group_cols
        Optional explicit grouping columns. Missing columns are ignored.
    score_columns
        Optional score columns. By default, all ``*_score`` columns are used.

    Returns
    -------
    pandas.DataFrame
        Summary table with mean, median, standard deviation, and count for each
        score column.
    """

    if group_cols is None:
        candidates = [
            _first_existing_column(df, MODEL_ALIASES),
            _first_existing_column(df, STATION_COLUMN_ALIASES),
            _first_existing_column(df, PASSBAND_ALIASES),
        ]
        groups = [column for column in candidates if column is not None]
    else:
        groups = [column for column in group_cols if column in df.columns]
    scores = list(score_columns) if score_columns is not None else [f"{stem}_score" for stem in score_metric_stems(df)]
    scores = [column for column in scores if column in df.columns]
    if not groups:
        raise ValueError("No grouping columns are available for metric summary.")
    if not scores:
        raise ValueError("No score columns are available for metric summary.")
    work = df[[*groups, *scores]].copy()
    for column in scores:
        work[column] = pd.to_numeric(work[column], errors="coerce")
    summary = work.groupby(groups, dropna=False)[scores].agg(["mean", "median", "std", "count"])
    summary.columns = ["_".join(column for column in item if column) for item in summary.columns]
    return summary.reset_index()


def summarize_long_metric_table(
    df: pd.DataFrame,
    *,
    value_col: str = "log2_residual",
    group_cols: Sequence[str] = ("model", "station", "passband", "metric"),
) -> pd.DataFrame:
    """Summarize a public long metric table.

    Parameters
    ----------
    df
        Long metric table with a metric value or transform column.
    value_col
        Numeric value column to summarize.
    group_cols
        Grouping columns to use when present.

    Returns
    -------
    pandas.DataFrame
        Summary table with mean, median, standard deviation, and count.
    """

    groups = [column for column in group_cols if column in df.columns]
    if value_col not in df.columns:
        raise ValueError(f"Value column {value_col!r} is not present.")
    if not groups:
        raise ValueError("No grouping columns are available for long metric summary.")
    work = df[[*groups, value_col]].copy()
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
    summary = work.groupby(groups, dropna=False)[value_col].agg(["mean", "median", "std", "count"])
    return summary.reset_index()


def _first_existing_column(df: pd.DataFrame, aliases: Sequence[str]) -> str | None:
    """Return the first available column from an alias list.

    Parameters
    ----------
    df
        Input dataframe.
    aliases
        Candidate column names.

    Returns
    -------
    str or None
        First matching column or ``None``.
    """

    columns = set(df.columns)
    for column in aliases:
        if column in columns:
            return column
    return None


def _require_existing_column(df: pd.DataFrame, aliases: Sequence[str], label: str) -> str:
    """Return the first available column or raise a clear error.

    Parameters
    ----------
    df
        Input dataframe.
    aliases
        Candidate column names.
    label
        Human-readable label for error messages.

    Returns
    -------
    str
        Matching column name.
    """

    column = _first_existing_column(df, aliases)
    if column is None:
        raise ValueError(f"Missing required {label} column. Expected one of {tuple(aliases)}.")
    return column


__all__ = [
    "binned_numeric_midpoints",
    "build_station_residual_table",
    "metric_residual_series",
    "metric_stems_by_family",
    "residual_metric_stems",
    "score_metric_stems",
    "station_mean_table",
    "summarize_long_metric_table",
    "summarize_metric_scores",
]
