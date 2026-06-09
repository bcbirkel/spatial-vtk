"""Prepare metric tables for spatial statistics.

Purpose
-------
This module turns wide observed/synthetic metric tables into event-centered
fields and station-level summaries used by spatial autocorrelation, clustering,
and geology-class tests.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from spatial_vtk.spatial.calculate._common import (
    as_float_series,
    coalesce_column,
    infer_model_from_source,
    metric_sort_key,
)
from spatial_vtk.spatial.calculate.settings import spatial_statistics_settings_from_config


def normalize_metrics_table(
    df: pd.DataFrame,
    *,
    source_path: str | Path | None = None,
    default_model: str | None = None,
) -> pd.DataFrame:
    """Normalize supported metrics tables to a common spatial-statistics schema.

    Parameters
    ----------
    df
        Metrics table with observed/synthetic values and station coordinates.
    source_path
        Optional path used to infer a model label when no model column exists.
    default_model
        Optional model label that overrides path inference.

    Returns
    -------
    pandas.DataFrame
        Copy with canonical model, band, component, event, station, and
        coordinate columns.
    """

    out = df.copy()
    inferred_model = default_model or infer_model_from_source(source_path)
    out["model"] = coalesce_column(out, ["simulation_model", "model", "model_name"], default=inferred_model)
    out["band"] = coalesce_column(out, ["simulation_band", "Band", "band"], default="all")
    out["component"] = coalesce_column(out, ["station_component", "Component", "component"], default="all")
    out["event_id"] = coalesce_column(out, ["event_title", "event_id", "Event"], default=np.nan)
    out["event_name"] = coalesce_column(out, ["event_name", "event_title", "event_id", "Event"], default=np.nan)
    out["event_magnitude"] = as_float_series(coalesce_column(out, ["event_magnitude", "magnitude", "mag"], default=np.nan))
    out["station"] = coalesce_column(out, ["station_name", "Station", "station"], default=np.nan)
    out["lat"] = as_float_series(coalesce_column(out, ["station_latitude", "latitude", "sta_lat", "lat"], default=np.nan))
    out["lon"] = as_float_series(coalesce_column(out, ["station_longitude", "longitude", "sta_lon", "lon"], default=np.nan))
    out["event_lat"] = as_float_series(
        coalesce_column(
            out,
            ["event_latitude", "event_lat", "source_latitude", "source_lat", "hypocenter_latitude", "origin_latitude"],
            default=np.nan,
        )
    )
    out["event_lon"] = as_float_series(
        coalesce_column(
            out,
            ["event_longitude", "event_lon", "source_longitude", "source_lon", "hypocenter_longitude", "origin_longitude"],
            default=np.nan,
        )
    )
    if "rms_ratio" in out.columns:
        out["rms_ratio"] = as_float_series(out["rms_ratio"])

    out["model"] = out["model"].fillna(inferred_model).astype(str)
    out["band"] = out["band"].fillna("all").astype(str)
    out["component"] = out["component"].fillna("all").astype(str)
    out.dropna(subset=["event_id", "station", "lat", "lon"], inplace=True)
    out["event_id"] = out["event_id"].astype(str).str.strip()
    out["station"] = out["station"].astype(str).str.strip()
    out = out.loc[
        (out["event_id"].str.len() > 0)
        & (out["station"].str.len() > 0)
        & (out["event_id"].str.lower() != "nan")
        & (out["station"].str.lower() != "nan")
    ].copy()
    return out


def available_metrics(df: pd.DataFrame) -> list[str]:
    """Return metric families available in a normalized metrics table.

    Parameters
    ----------
    df
        Metrics table.

    Returns
    -------
    list of str
        Metric stems such as ``C5`` and ``PSA_T1``.
    """

    metrics: set[str] = set()
    if "rms_ratio" in df.columns:
        metrics.add("rms_ratio")
    columns = set(df.columns)
    for column in columns:
        if column.endswith("_obs"):
            stem = column[:-4]
            if f"{stem}_syn" in columns:
                metrics.add(stem)
        elif column.endswith("_score"):
            metrics.add(column[:-6])
    metrics.discard("band")
    return sorted(metrics, key=metric_sort_key)


def resolve_metric_name(metric: str, df: pd.DataFrame) -> str:
    """Resolve a user metric token to an available metric family.

    Parameters
    ----------
    metric
        Requested metric token.
    df
        Metrics table.

    Returns
    -------
    str
        Canonical metric family name.
    """

    token = str(metric).strip()
    available = set(available_metrics(df))
    if token in available:
        return token
    if token.endswith("_score") and token[:-6] in available:
        return token[:-6]
    if f"{token}_score" in df.columns or (f"{token}_obs" in df.columns and f"{token}_syn" in df.columns):
        return token
    raise KeyError(f"Metric {metric!r} is not available. Choices: {sorted(available)}")


def build_metric_field(
    df: pd.DataFrame,
    metric: str | None = None,
    *,
    field_mode: str | None = None,
    value_column: str | None = None,
) -> pd.DataFrame:
    """Build an event-station analysis field for one metric.

    Parameters
    ----------
    df
        Normalized metrics table.
    metric
        Metric stem. When omitted, ``spatial.metric`` from the active config is
        used.
    field_mode
        Value selector for the field. For long metric tables this is usually a
        transform column such as ``"log2_residual"``. For wide metric tables,
        ``"auto"``, ``"log2_ratio"``, or ``"score"`` are supported.
    value_column
        Clearer alias for ``field_mode`` when selecting a long-table value
        column.

    Returns
    -------
    pandas.DataFrame
        Field table with ``field_value`` and metadata columns.
    """

    settings = spatial_statistics_settings_from_config()
    metric_token = settings.metric if metric is None else str(metric)
    if field_mode is None:
        field_mode = value_column or (settings.value_column if "metric" in df.columns else "auto")

    if "metric" in df.columns:
        if metric_token.lower() not in {"all", "*"}:
            available_metrics_long = sorted(df["metric"].dropna().astype(str).unique().tolist())
            if metric_token not in available_metrics_long:
                raise KeyError(f"Metric {metric_token!r} is not available. Choices: {available_metrics_long}")
        long_field = _build_long_metric_field(df, metric_token, field_mode=field_mode)
        return long_field

    metric_name = resolve_metric_name(metric_token, df)
    out = df[
        [
            "model",
            "band",
            "component",
            "event_id",
            "event_name",
            "event_magnitude",
            "station",
            "lat",
            "lon",
            "event_lat",
            "event_lon",
        ]
    ].copy()
    if metric_name == "rms_ratio":
        if field_mode not in {"auto", "log2_ratio"}:
            raise ValueError("rms_ratio only supports field_mode='auto' or 'log2_ratio'.")
        with np.errstate(divide="ignore", invalid="ignore"):
            out["field_value"] = np.log2(as_float_series(df["rms_ratio"]))
        source = "log2_ratio"
    else:
        obs_col = f"{metric_name}_obs"
        syn_col = f"{metric_name}_syn"
        score_col = f"{metric_name}_score"
        if field_mode in {"auto", "log2_ratio"} and obs_col in df.columns and syn_col in df.columns:
            with np.errstate(divide="ignore", invalid="ignore"):
                out["field_value"] = np.log2(as_float_series(df[obs_col]) / as_float_series(df[syn_col]))
            source = "log2_obs_over_syn"
        elif score_col in df.columns and field_mode in {"auto", "score"}:
            out["field_value"] = as_float_series(df[score_col])
            source = "score"
        else:
            available = [col for col in (obs_col, syn_col, score_col) if col in df.columns]
            raise ValueError(f"Metric {metric_name!r} does not support field_mode={field_mode!r}. Available columns: {available}")
    out["metric"] = metric_name
    out["field_source"] = source
    out["field_value"] = as_float_series(out["field_value"])
    out.dropna(subset=["field_value", "event_id", "station", "lat", "lon"], inplace=True)
    return out


def _build_long_metric_field(df: pd.DataFrame, metric: str, *, field_mode: str = "auto") -> pd.DataFrame:
    """Build a spatial field from the standard long metrics schema.

    Parameters
    ----------
    df
        Long metrics table with a ``metric`` column.
    metric
        Metric name to keep, or ``"all"`` to use all rows.
    field_mode
        Value column or transform to use. ``"auto"`` prefers
        ``log2_residual``, then ``residual``, then ``score``.

    Returns
    -------
    pandas.DataFrame
        Field table with ``field_value`` and metadata columns.
    """

    token = str(metric).strip()
    work = df.copy()
    if token.lower() not in {"all", "*"}:
        work = work.loc[work["metric"].astype(str).eq(token)].copy()
    if work.empty:
        return pd.DataFrame()

    value_column: str | None = None
    if field_mode in work.columns:
        value_column = field_mode
    elif field_mode in {"auto", "log2_ratio"} and {"value_obs", "value_syn"} <= set(work.columns):
        work = work.copy()
        with np.errstate(divide="ignore", invalid="ignore"):
            work["__field_value"] = np.log2(as_float_series(work["value_obs"]) / as_float_series(work["value_syn"]))
        value_column = "__field_value"
    elif field_mode == "auto":
        for candidate in ("log2_residual", "residual", "score"):
            if candidate in work.columns:
                value_column = candidate
                break
    elif field_mode == "score" and "score" in work.columns:
        value_column = "score"

    if value_column is None:
        available = [column for column in ("log2_residual", "residual", "score", "value_obs", "value_syn") if column in work.columns]
        raise ValueError(f"Long metric table does not support field_mode={field_mode!r}. Available value columns: {available}")

    out = pd.DataFrame(
        {
            "model": coalesce_column(work, ["model", "model_name"], default="unknown"),
            "band": coalesce_column(work, ["band", "passband"], default="all"),
            "component": coalesce_column(work, ["component"], default="all"),
            "event_id": coalesce_column(work, ["event_id", "event_title"], default=np.nan),
            "event_name": coalesce_column(work, ["event_name", "event_id", "event_title"], default=np.nan),
            "event_magnitude": as_float_series(coalesce_column(work, ["event_magnitude", "magnitude", "Mw"], default=np.nan)),
            "station": coalesce_column(work, ["station", "station_name"], default=np.nan),
            "lat": as_float_series(coalesce_column(work, ["lat", "sta_lat", "station_lat", "station_latitude"], default=np.nan)),
            "lon": as_float_series(coalesce_column(work, ["lon", "sta_lon", "station_lon", "station_longitude"], default=np.nan)),
            "event_lat": as_float_series(coalesce_column(work, ["event_lat", "event_latitude"], default=np.nan)),
            "event_lon": as_float_series(coalesce_column(work, ["event_lon", "event_longitude"], default=np.nan)),
            "field_value": as_float_series(work[value_column]),
            "metric": coalesce_column(work, ["metric"], default=token),
            "field_source": str(value_column).strip("_"),
        }
    )
    if token.lower() in {"all", "*"}:
        out["metric"] = "all"
    out.dropna(subset=["field_value", "event_id", "station", "lat", "lon"], inplace=True)
    out["event_id"] = out["event_id"].astype(str).str.strip()
    out["station"] = out["station"].astype(str).str.strip()
    return out


def center_field_by_reference_mask(
    field_df: pd.DataFrame,
    reference_mask: pd.Series | np.ndarray | list[bool],
    *,
    min_stations_per_event: int = 3,
) -> pd.DataFrame:
    """Center event fields using a selected reference subset.

    Parameters
    ----------
    field_df
        Event-station metric field.
    reference_mask
        Boolean mask marking rows used to estimate each event mean.
    min_stations_per_event
        Minimum number of reference stations required for an event.

    Returns
    -------
    pandas.DataFrame
        Copy with event means and centered fields.
    """

    if field_df.empty:
        return field_df.copy()
    work = field_df.copy()
    ref_mask = pd.Series(np.asarray(reference_mask, dtype=bool), index=work.index)
    if len(ref_mask) != len(work):
        raise ValueError("reference_mask must have the same length as field_df.")
    work["is_reference"] = ref_mask.to_numpy(dtype=bool)
    reference = work.loc[work["is_reference"]].copy()
    if reference.empty:
        return work.iloc[0:0].copy()
    event_counts = reference.groupby("event_id")["station"].nunique()
    valid_events = event_counts.index[event_counts >= int(min_stations_per_event)]
    if len(valid_events) == 0:
        return work.iloc[0:0].copy()
    reference = reference.loc[reference["event_id"].isin(valid_events)].copy()
    event_mean = reference.groupby("event_id")["field_value"].mean().rename("event_mean")
    event_std = reference.groupby("event_id")["field_value"].agg(
        lambda s: float(np.nanstd(s.to_numpy(dtype=float), ddof=1)) if len(s) > 1 else np.nan
    ).rename("event_std")
    event_station_count = reference.groupby("event_id")["station"].nunique().rename("event_station_count")
    work = work.loc[work["event_id"].isin(valid_events)].copy()
    work = work.merge(event_mean, left_on="event_id", right_index=True, how="left")
    work = work.merge(event_std, left_on="event_id", right_index=True, how="left")
    work = work.merge(event_station_count, left_on="event_id", right_index=True, how="left")
    work["field_centered"] = work["field_value"] - work["event_mean"]
    work["field_z"] = np.nan
    valid_std = work["event_std"].to_numpy(dtype=float) > 0.0
    work.loc[valid_std, "field_z"] = work.loc[valid_std, "field_centered"] / work.loc[valid_std, "event_std"]
    return work


def center_field_by_event(
    field_df: pd.DataFrame,
    *,
    min_stations_per_event: int | None = None,
    remove_event_mean: bool | None = None,
) -> pd.DataFrame:
    """Center a metric field within each event.

    Parameters
    ----------
    field_df
        Event-station metric field.
    min_stations_per_event
        Minimum number of stations required for an event.
    remove_event_mean
        When false, keep raw values in ``field_centered``. When omitted,
        ``spatial.remove_event_mean`` from the active config is used.

    Returns
    -------
    pandas.DataFrame
        Event-centered field table.
    """

    settings = spatial_statistics_settings_from_config()
    min_stations = settings.min_stations_per_event if min_stations_per_event is None else int(min_stations_per_event)
    remove_mean = settings.remove_event_mean if remove_event_mean is None else bool(remove_event_mean)
    centered = center_field_by_reference_mask(
        field_df,
        np.ones(len(field_df), dtype=bool),
        min_stations_per_event=min_stations,
    )
    if not remove_mean and not centered.empty:
        centered = centered.copy()
        centered["field_centered"] = centered["field_value"]
        centered["field_z"] = np.nan
    return centered


def summarize_station_bias(
    field_df: pd.DataFrame,
    *,
    min_events_per_station: int | None = None,
    value_col: str | None = None,
    center_by_event: bool | None = None,
    min_stations_per_event: int | None = None,
) -> pd.DataFrame:
    """Summarize persistent station bias from raw or event-centered fields.

    Parameters
    ----------
    field_df
        Raw metric field table with ``field_value`` or event-centered field
        table with ``field_centered``.
    min_events_per_station
        Minimum distinct events needed to retain a station. When omitted,
        ``spatial.min_events_per_station`` from the active config is used.
    value_col
        Explicit value column to summarize. When omitted, the helper uses
        ``field_centered`` if present, otherwise raw ``field_value``.
    center_by_event
        When true, first remove the per-event mean before station summaries.
        When omitted, an existing ``field_centered`` column is used as-is, and
        raw fields are summarized without event centering.
    min_stations_per_event
        Minimum station support used only when ``center_by_event=True``.

    Returns
    -------
    pandas.DataFrame
        Station-level bias table.
    """

    columns = [
        "station",
        "lat",
        "lon",
        "n_events",
        "mean_centered",
        "median_centered",
        "std_centered",
        "sem_centered",
        "abs_mean_centered",
        "bias_zscore",
    ]
    settings = spatial_statistics_settings_from_config()
    min_events = settings.min_events_per_station if min_events_per_station is None else int(min_events_per_station)
    if field_df.empty:
        return pd.DataFrame(columns=columns)
    work = field_df.copy()
    if center_by_event is True:
        work = center_field_by_event(
            work,
            min_stations_per_event=min_stations_per_event,
            remove_event_mean=True,
        )
    if value_col is None:
        if center_by_event is False and "field_value" in work.columns:
            value_col = "field_value"
        elif "field_centered" in work.columns:
            value_col = "field_centered"
        elif "field_value" in work.columns:
            value_col = "field_value"
        else:
            raise KeyError("summarize_station_bias requires either 'field_centered' or 'field_value'.")
    if value_col not in work.columns:
        raise KeyError(f"Missing station-bias value column: {value_col}")
    if value_col != "field_centered":
        work = work.copy()
        work["field_centered"] = as_float_series(work[value_col])
    station_df = work.groupby("station", as_index=False).agg(
        lat=("lat", "mean"),
        lon=("lon", "mean"),
        n_events=("event_id", pd.Series.nunique),
        mean_centered=("field_centered", "mean"),
        median_centered=("field_centered", "median"),
        std_centered=("field_centered", lambda s: float(np.nanstd(s.to_numpy(dtype=float), ddof=1)) if len(s) > 1 else np.nan),
    )
    station_df["sem_centered"] = station_df["std_centered"] / np.sqrt(station_df["n_events"].clip(lower=1))
    station_df["abs_mean_centered"] = np.abs(station_df["mean_centered"])
    station_df["bias_zscore"] = station_df["mean_centered"] / station_df["sem_centered"]
    station_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    station_df = station_df.loc[station_df["n_events"] >= int(min_events)].copy()
    station_df.sort_values(["abs_mean_centered", "station"], ascending=[False, True], inplace=True)
    return station_df[columns]


def build_station_feature_table(
    centered_df: pd.DataFrame,
    *,
    station_col: str = "station",
    lat_col: str = "lat",
    lon_col: str = "lon",
    feature_id_col: str = "event_id",
    value_col: str = "field_centered",
    aggfunc: str = "mean",
) -> pd.DataFrame:
    """Build a station-feature matrix for clustering and PCA.

    Parameters
    ----------
    centered_df
        Event-centered metric field table.
    station_col, lat_col, lon_col
        Columns identifying stations and station coordinates.
    feature_id_col
        Column whose values become feature columns, usually ``event_id``.
    value_col
        Numeric value summarized for each station-feature pair.
    aggfunc
        Aggregation used when more than one row exists per station-feature
        pair.

    Returns
    -------
    pandas.DataFrame
        One row per station with coordinate columns and one numeric feature
        column per feature id.
    """

    required = [station_col, lat_col, lon_col, feature_id_col, value_col]
    missing = [column for column in required if column not in centered_df.columns]
    if missing:
        raise KeyError(f"Missing required columns for station feature table: {missing}")
    if centered_df.empty:
        return pd.DataFrame(columns=[station_col, lat_col, lon_col])
    work = centered_df[required].copy()
    work[value_col] = as_float_series(work[value_col])
    work.dropna(subset=[station_col, lat_col, lon_col, feature_id_col, value_col], inplace=True)
    if work.empty:
        return pd.DataFrame(columns=[station_col, lat_col, lon_col])
    features = (
        work.pivot_table(
            index=[station_col, lat_col, lon_col],
            columns=feature_id_col,
            values=value_col,
            aggfunc=aggfunc,
        )
        .reset_index()
        .rename_axis(columns=None)
    )
    features.columns = [str(column) for column in features.columns]
    return features


def summarize_event_locations(field_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize one coordinate point per event.

    Parameters
    ----------
    field_df
        Metric field table with event coordinate columns.

    Returns
    -------
    pandas.DataFrame
        Event coordinate and station-count table.
    """

    columns = ["event_id", "event_name", "event_magnitude", "event_lat", "event_lon", "n_stations"]
    if field_df.empty or "event_lat" not in field_df.columns or "event_lon" not in field_df.columns:
        return pd.DataFrame(columns=columns)
    event_df = field_df[["event_id", "event_name", "event_magnitude", "event_lat", "event_lon", "station"]].copy()
    event_df["event_name"] = event_df["event_name"].fillna("").astype(str).str.strip()
    event_df["event_magnitude"] = as_float_series(event_df["event_magnitude"])
    event_df["event_lat"] = as_float_series(event_df["event_lat"])
    event_df["event_lon"] = as_float_series(event_df["event_lon"])
    event_df.dropna(subset=["event_id", "event_lat", "event_lon"], inplace=True)
    if event_df.empty:
        return pd.DataFrame(columns=columns)

    def first_nonempty(series: pd.Series) -> str:
        tokens = [str(value).strip() for value in series.dropna().tolist() if str(value).strip()]
        return tokens[0] if tokens else ""

    out = event_df.groupby("event_id", as_index=False).agg(
        event_name=("event_name", first_nonempty),
        event_magnitude=("event_magnitude", "mean"),
        event_lat=("event_lat", "mean"),
        event_lon=("event_lon", "mean"),
        n_stations=("station", pd.Series.nunique),
    )
    return out[columns]


def collapse_and_event_demean(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse component rows and subtract each event mean.

    Parameters
    ----------
    df
        Long event-station table with ``value_raw`` and class columns.

    Returns
    -------
    pandas.DataFrame
        Event-station table with event-demeaned ``value``.
    """

    keys = [
        "dataset",
        "metric",
        "bin",
        "event_id",
        "station_name",
        "station_longitude",
        "station_latitude",
        "target_region_zone",
        "target_region_edge_distance_km",
        "mapped_region",
        "mapped_region_type",
    ]
    collapsed = df.groupby(keys, dropna=False).agg(value_raw=("value_raw", "mean"), n_component_rows=("value_raw", "size")).reset_index()
    collapsed["event_mean"] = collapsed.groupby(["dataset", "metric", "bin", "event_id"], dropna=False)["value_raw"].transform("mean")
    collapsed["value"] = collapsed["value_raw"] - collapsed["event_mean"]
    return collapsed.dropna(subset=["value"]).copy()


def collapse_and_reference_demean(df: pd.DataFrame, *, reference: str = "pooled") -> pd.DataFrame:
    """Collapse rows and subtract pooled or per-dataset event references.

    Parameters
    ----------
    df
        Long observed/synthetic event-station table.
    reference
        ``"pooled"`` subtracts one observed+synthetic event mean;
        ``"independent"`` subtracts separate means by dataset.

    Returns
    -------
    pandas.DataFrame
        Event-station table with anomaly values.
    """

    keys = [
        "dataset",
        "metric",
        "bin",
        "event_id",
        "station_name",
        "station_longitude",
        "station_latitude",
        "target_region_zone",
        "target_region_edge_distance_km",
        "mapped_region",
        "mapped_region_type",
    ]
    collapsed = df.groupby(keys, dropna=False).agg(value_raw=("value_raw", "mean"), n_component_rows=("value_raw", "size")).reset_index()
    if reference == "independent":
        ref_keys = ["dataset", "metric", "bin", "event_id"]
    elif reference == "pooled":
        ref_keys = ["metric", "bin", "event_id"]
    else:
        raise ValueError(f"Unknown anomaly reference: {reference!r}")
    collapsed["event_mean"] = collapsed.groupby(ref_keys, dropna=False)["value_raw"].transform("mean")
    collapsed["value"] = collapsed["value_raw"] - collapsed["event_mean"]
    collapsed["anomaly_reference"] = reference
    return collapsed.dropna(subset=["value"]).copy()
