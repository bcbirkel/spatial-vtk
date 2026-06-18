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
DASHBOARD_SUMMARY_GROUP_COLUMNS: tuple[str, ...] = (
    "model",
    "metric",
    "band",
    "period_s",
    "component",
    "station",
    "event_id",
)
DASHBOARD_SUMMARY_GEOMETRY_COLUMNS: tuple[str, ...] = (
    "sta_lat",
    "sta_lon",
    "station_lat",
    "station_lon",
    "lat",
    "lon",
    "event_lat",
    "event_lon",
    "distance_km",
    "azimuth_deg",
    "Vs30",
    "vs30",
    "geology_class",
    "magnitude",
    "event_magnitude",
)


def dashboard_summary_input_columns() -> tuple[str, ...]:
    """Return metric-dataset columns needed to build dashboard summaries.

    The dashboard summary writer can use this as a column projection when it
    reads large Parquet/CSV metric datasets. Missing columns remain optional at
    load time, so older dashboard datasets still work.
    """

    return tuple(
        dict.fromkeys(
            [
                *DASHBOARD_SUMMARY_GROUP_COLUMNS,
                *DASHBOARD_SUMMARY_GEOMETRY_COLUMNS,
                *DEFAULT_DASHBOARD_VALUE_COLUMNS,
                *SUMMARY_VALUE_COLUMNS,
            ]
        )
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
    out = _normalize_dashboard_coordinate_aliases(out)
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
    model_groups = [column for column in ["model", "metric", "band", "period_s", "component"] if column in work.columns]
    summaries["model_metric_band"] = (
        work.groupby(model_groups, dropna=False)
        .agg(
            IQR=(base_value_col, _iqr),
            n=("_dashboard_row_count", "sum"),
            **_unique_count_aggregations(work, events=True, stations=True),
            **value_aggs,
        )
        .reset_index()
    )

    station_groups = [column for column in ["station", "sta_lat", "sta_lon", "Vs30", "vs30", "geology_class", "model", "metric", "band", "period_s", "component"] if column in work.columns]
    summaries["station_rollup"] = (
        work.groupby(station_groups, dropna=False)
        .agg(
            med_dist_km=("distance_km", "median") if "distance_km" in work.columns else ("_dashboard_row_count", "sum"),
            n=("_dashboard_row_count", "sum"),
            **_unique_count_aggregations(work, events=True),
            **value_aggs,
        )
        .reset_index()
    )

    event_groups = [column for column in ["event_id", "event_lat", "event_lon", "magnitude", "event_magnitude", "model", "metric", "band", "period_s", "component"] if column in work.columns]
    summaries["event_rollup"] = (
        work.groupby(event_groups, dropna=False)
        .agg(
            med_dist_km=("distance_km", "median") if "distance_km" in work.columns else ("_dashboard_row_count", "sum"),
            n=("_dashboard_row_count", "sum"),
            **_unique_count_aggregations(work, stations=True),
            **value_aggs,
        )
        .reset_index()
    )

    if {"distance_km", "azimuth_deg"}.issubset(work.columns):
        binned = work.copy()
        binned["dist_bin_km"] = np.floor(pd.to_numeric(binned["distance_km"], errors="coerce") / float(hex_dist)) * float(hex_dist)
        binned["az_bin_deg"] = np.floor((pd.to_numeric(binned["azimuth_deg"], errors="coerce") % 360.0) / float(hex_az)) * float(hex_az)
        summaries["path_hex"] = (
            binned.groupby([column for column in ["model", "metric", "band", "period_s", "component", "dist_bin_km", "az_bin_deg"] if column in binned.columns], dropna=False)
            .agg(
                n=("_dashboard_row_count", "sum"),
                **_unique_count_aggregations(binned, events=True, stations=True),
                **value_aggs,
            )
            .reset_index()
        )
    else:
        value_cols = list(_value_aggregations(work).keys())
        count_cols = list(_unique_count_aggregations(work, events=True, stations=True).keys())
        summaries["path_hex"] = pd.DataFrame(columns=["model", "metric", "band", "period_s", "dist_bin_km", "az_bin_deg", "n", *count_cols, *value_cols])
    return summaries


def write_dashboard_summaries(
    summaries: dict[str, pd.DataFrame],
    output_dir: str | Path,
    *,
    format: str = "parquet",
    replace_existing: bool = True,
) -> dict[str, Path]:
    """Write dashboard summary tables to a directory."""

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, table in summaries.items():
        if replace_existing:
            for stale_suffix in (".parquet", ".csv"):
                stale = out_dir / f"{name}{stale_suffix}"
                if stale.exists():
                    stale.unlink()
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
            aggregations["med_residual"] = (column, "median")
        elif column == "score":
            aggregations["med_score"] = (column, "median")
        else:
            aggregations[f"med_{column}"] = (column, "median")
    return aggregations


def _unique_count_aggregations(
    df: pd.DataFrame,
    *,
    events: bool = False,
    stations: bool = False,
) -> dict[str, tuple[str, str]]:
    """Return optional unique-count aggregations for dashboard audit columns."""

    aggregations: dict[str, tuple[str, str]] = {}
    if events and "event_id" in df.columns:
        aggregations["event_count"] = ("event_id", "nunique")
    if stations and "station" in df.columns:
        aggregations["station_count"] = ("station", "nunique")
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


def _normalize_dashboard_coordinate_aliases(df: pd.DataFrame) -> pd.DataFrame:
    """Copy accepted dashboard coordinate aliases into canonical summary columns."""

    out = df.copy()
    aliases = {
        "sta_lat": ("station_lat", "station_latitude"),
        "sta_lon": ("station_lon", "station_longitude"),
        "event_lat": ("event_latitude",),
        "event_lon": ("event_longitude",),
    }
    for target, candidates in aliases.items():
        if target in out.columns and pd.to_numeric(out[target], errors="coerce").notna().any():
            continue
        for candidate in candidates:
            if candidate in out.columns:
                out[target] = out[candidate]
                break
    return out
