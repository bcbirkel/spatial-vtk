"""Dashboard preparation tables for long metric residual data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_DASHBOARD_VALUE_COLUMNS: tuple[str, ...] = (
    "value_obs",
    "value_syn",
    "residual",
    "log2_residual",
    "ln_residual",
    "anderson_2004_gof",
    "olsen_mayhew_gof",
    "score",
    "value",
)
SUMMARY_VALUE_COLUMNS: tuple[str, ...] = (
    "residual",
    "log2_residual",
    "ln_residual",
    "anderson_2004_gof",
    "olsen_mayhew_gof",
    "score",
    "value",
    "value_obs",
    "value_syn",
)


def prepare_dashboard_metric_table(df: pd.DataFrame, *, residual_mode: str = "logratio") -> pd.DataFrame:
    """Prepare a metric table for dashboard summaries.

    Parameters
    ----------
    df
        Wide or long metric table.
    residual_mode
        Residual mode used when converting wide tables.

    Returns
    -------
    pandas.DataFrame
        Long metric residual table with dashboard-compatible columns.
    """

    from spatial_vtk.metrics.calculate.enrich import prepare_metric_residual_table

    out = prepare_metric_residual_table(df, residual_mode=residual_mode)
    for column in ["model", "metric", "band", "station", "event_id"]:
        if column not in out.columns:
            out[column] = "unknown"
    if "score" not in out.columns:
        out["score"] = np.nan
    return out


def build_dashboard_summaries(
    df: pd.DataFrame,
    *,
    hex_dist: float = 10.0,
    hex_az: float = 10.0,
) -> dict[str, pd.DataFrame]:
    """Build dashboard summary tables from long metric residual data.

    Parameters
    ----------
    df
        Wide or long metric table.
    hex_dist
        Distance bin size in kilometers for path summaries.
    hex_az
        Azimuth bin size in degrees for path summaries.

    Returns
    -------
    dict
        Summary tables keyed as ``model_metric_band``, ``station_rollup``,
        ``event_rollup``, and ``path_hex``.
    """

    work = prepare_dashboard_metric_table(df)
    work["_dashboard_row_count"] = 1
    work["_dashboard_value"] = _summary_value_series(work)
    value_aggs = _value_aggregations(work)
    base_value_col = "_dashboard_value"
    summaries: dict[str, pd.DataFrame] = {}
    model_groups = [column for column in ["model", "metric", "band", "component"] if column in work.columns]
    summaries["model_metric_band"] = (
        work.groupby(model_groups, dropna=False)
        .agg(
            IQR=(base_value_col, _iqr),
            n=("_dashboard_row_count", "sum"),
            **value_aggs,
        )
        .reset_index()
    )

    station_groups = [column for column in ["station", "sta_lat", "sta_lon", "Vs30", "vs30", "geology_class", "model", "metric", "band", "component"] if column in work.columns]
    summaries["station_rollup"] = (
        work.groupby(station_groups, dropna=False)
        .agg(
            med_dist_km=("distance_km", "median") if "distance_km" in work.columns else ("_dashboard_row_count", "sum"),
            n=("_dashboard_row_count", "sum"),
            **value_aggs,
        )
        .reset_index()
    )

    event_groups = [column for column in ["event_id", "event_lat", "event_lon", "magnitude", "event_magnitude", "model", "metric", "band", "component"] if column in work.columns]
    summaries["event_rollup"] = (
        work.groupby(event_groups, dropna=False)
        .agg(
            med_dist_km=("distance_km", "median") if "distance_km" in work.columns else ("_dashboard_row_count", "sum"),
            n=("_dashboard_row_count", "sum"),
            **value_aggs,
        )
        .reset_index()
    )

    if {"distance_km", "azimuth_deg"}.issubset(work.columns):
        binned = work.copy()
        binned["dist_bin_km"] = np.floor(pd.to_numeric(binned["distance_km"], errors="coerce") / float(hex_dist)) * float(hex_dist)
        binned["az_bin_deg"] = np.floor((pd.to_numeric(binned["azimuth_deg"], errors="coerce") % 360.0) / float(hex_az)) * float(hex_az)
        summaries["path_hex"] = (
            binned.groupby([column for column in ["model", "metric", "band", "component", "dist_bin_km", "az_bin_deg"] if column in binned.columns], dropna=False)
            .agg(n=("_dashboard_row_count", "sum"), **value_aggs)
            .reset_index()
        )
    else:
        value_cols = list(_value_aggregations(work).keys())
        summaries["path_hex"] = pd.DataFrame(columns=["model", "metric", "band", "dist_bin_km", "az_bin_deg", "n", *value_cols])
    return summaries


def write_dashboard_summaries(summaries: dict[str, pd.DataFrame], output_dir: str | Path, *, format: str = "parquet") -> dict[str, Path]:
    """Write dashboard summary tables to a directory."""

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, table in summaries.items():
        if format == "csv":
            path = out_dir / f"{name}.csv"
            table.to_csv(path, index=False)
        elif format == "parquet":
            path = out_dir / f"{name}.parquet"
            table.to_parquet(path, index=False)
        else:
            raise ValueError("format must be 'csv' or 'parquet'.")
        written[name] = path
    return written


def _iqr(series: pd.Series) -> float:
    """Return interquartile range for one series."""

    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return float("nan")
    return float(values.quantile(0.75) - values.quantile(0.25))


def _value_aggregations(df: pd.DataFrame) -> dict[str, tuple[str, str]]:
    """Return median aggregations for every available dashboard value column."""

    aggregations: dict[str, tuple[str, str]] = {}
    for column in DEFAULT_DASHBOARD_VALUE_COLUMNS:
        if column not in df.columns:
            continue
        if column == "residual":
            aggregations["med_resid"] = (column, "median")
        elif column == "score":
            aggregations["med_score"] = (column, "median")
        else:
            aggregations[f"med_{column}"] = (column, "median")
    return aggregations


def _summary_value_series(df: pd.DataFrame) -> pd.Series:
    """Return one coalesced value series for generic spread summaries."""

    values = pd.Series(np.nan, index=df.index, dtype=float)
    for column in SUMMARY_VALUE_COLUMNS:
        if column not in df.columns:
            continue
        candidate = pd.to_numeric(df[column], errors="coerce")
        values = values.where(values.notna(), candidate)
    if values.notna().any():
        return values
    numeric = [column for column in df.columns if pd.api.types.is_numeric_dtype(df[column])]
    if numeric:
        return pd.to_numeric(df[numeric[0]], errors="coerce")
    return pd.Series(np.nan, index=df.index, dtype=float)
