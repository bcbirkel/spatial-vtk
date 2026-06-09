"""Pure filtering helpers for dashboard tables."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from spatial_vtk.config.labels import band_display_label, normalize_metric_name


def filter_dashboard_metrics(
    df: pd.DataFrame,
    *,
    models: Iterable[str] | None = None,
    metric: str | None = None,
    bands: Iterable[str] | None = None,
    value_column: str | None = None,
    vs30_range: tuple[float | None, float | None] | None = None,
    distance_range_km: tuple[float | None, float | None] | None = None,
    magnitude_range: tuple[float | None, float | None] | None = None,
    station_query: str = "",
    event_query: str = "",
    component: str | None = None,
    min_count: int | None = None,
) -> pd.DataFrame:
    """Filter one metrics dashboard table."""

    out = df.copy()
    if models and "model" in out.columns:
        keep = {str(model) for model in models}
        out = out[out["model"].astype(str).isin(keep)]
    if metric and "metric" in out.columns:
        public_metric = normalize_metric_name(metric)
        metric_values = out["metric"].map(normalize_metric_name)
        out = out[metric_values == public_metric]
    if bands and "band" in out.columns:
        out = _filter_band_labels(out, bands, band_columns=("band",))
    if value_column and value_column not in out.columns:
        raise ValueError(f"Selected dashboard value column is not available: {value_column}")
    out = _filter_range_any(out, ("Vs30", "vs30"), vs30_range)
    out = _filter_range_any(out, ("med_dist_km", "distance_km", "dist_km"), distance_range_km)
    out = _filter_range_any(out, ("magnitude", "event_magnitude", "mag"), magnitude_range)
    if station_query and "station" in out.columns:
        token = str(station_query).strip().upper()
        out = out[out["station"].astype(str).str.upper().str.contains(token, na=False)]
    if event_query and "event_id" in out.columns:
        token = str(event_query).strip().lower()
        out = out[out["event_id"].astype(str).str.lower().str.contains(token, na=False)]
    if component and "component" in out.columns:
        out = out[out["component"].astype(str).str.upper() == str(component).upper()]
    if min_count is not None and "n" in out.columns:
        out = out[pd.to_numeric(out["n"], errors="coerce").fillna(0) >= int(min_count)]
    return out.reset_index(drop=True)


def filter_qc_dashboard_rows(
    trace_df: pd.DataFrame,
    *,
    event_filter: str = "",
    station_family: str = "all",
    component_filter: str = "all",
    station_query: str = "",
    magnitude_range: tuple[float | None, float | None] | None = None,
    distance_range_km: tuple[float | None, float | None] | None = None,
    date_range: tuple[pd.Timestamp | str | None, pd.Timestamp | str | None] | None = None,
    metadata_warning: str = "",
    reject_reason: str = "",
    band: str | None = None,
) -> pd.DataFrame:
    """Filter one trace-QC dashboard table."""

    out = _basic_qc_filter(
        trace_df,
        event_filter=event_filter,
        station_family=station_family,
        component_filter=component_filter,
        station_query=station_query,
        magnitude_range=magnitude_range,
        distance_range_km=distance_range_km,
        date_range=date_range,
    )
    if metadata_warning and "metadata_warning" in out.columns:
        out = out[out["metadata_warning"].astype(str).str.contains(str(metadata_warning), case=False, na=False)]
    if reject_reason:
        reason_cols = [column for column in out.columns if "reject" in column.lower() and "reason" in column.lower()]
        if reason_cols:
            mask = False
            for column in reason_cols:
                mask = mask | out[column].astype(str).str.contains(str(reject_reason), case=False, na=False)
            out = out[mask]
    if band:
        out = _filter_band_labels(out, (band,), band_columns=("band", "passband", "dominant_band_label"))
    return out.reset_index(drop=True)


def _basic_qc_filter(
    trace_df: pd.DataFrame,
    *,
    event_filter: str,
    station_family: str,
    component_filter: str,
    station_query: str,
    magnitude_range: tuple[float | None, float | None] | None,
    distance_range_km: tuple[float | None, float | None] | None,
    date_range: tuple[pd.Timestamp | str | None, pd.Timestamp | str | None] | None,
) -> pd.DataFrame:
    """Apply dependency-light QC filters."""

    df = trace_df.copy()
    if "event_date" in df.columns:
        df["event_date"] = _datetime_for_filter(df["event_date"])
    if event_filter and "event_id" in df.columns:
        df = df[df["event_id"].astype(str).str.lower() == str(event_filter).strip().lower()]
    family_key = str(station_family or "all").strip().lower()
    if family_key not in {"", "all"} and "station_family" in df.columns:
        df = df[df["station_family"].astype(str).str.lower() == family_key]
    component_key = str(component_filter or "all").strip().upper()
    if component_key not in {"", "ALL"} and "component" in df.columns:
        df = df[df["component"].astype(str).str.upper() == component_key]
    if station_query and "station" in df.columns:
        token = str(station_query).strip().upper()
        df = df[df["station"].astype(str).str.upper().str.contains(token, na=False)]
    if magnitude_range is not None:
        df = _filter_range_any(df, ("magnitude", "event_magnitude"), magnitude_range)
    if distance_range_km is not None:
        df = _filter_range_any(df, ("distance_km", "med_dist_km"), distance_range_km)
    if date_range is not None and "event_date" in df.columns:
        start, end = date_range
        if start is not None:
            df = df[df["event_date"] >= _date_bound_for_filter(start, is_end=False)]
        if end is not None:
            df = df[df["event_date"] <= _date_bound_for_filter(end, is_end=True)]
    return df.reset_index(drop=True)


def _datetime_for_filter(values: pd.Series) -> pd.Series:
    """Return event timestamps normalized for dashboard date filtering."""

    parsed = pd.to_datetime(values, errors="coerce", utc=True)
    return parsed.dt.tz_convert(None)


def _date_bound_for_filter(value: pd.Timestamp | str, *, is_end: bool) -> pd.Timestamp:
    """Return one timezone-free inclusive date bound for dashboard filtering."""

    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert("UTC").tz_localize(None)
    else:
        timestamp = timestamp.tz_localize(None) if getattr(timestamp, "tz", None) is not None else timestamp
    timestamp = timestamp.normalize()
    if is_end:
        timestamp = timestamp + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
    return timestamp


def _filter_range_any(df: pd.DataFrame, columns: tuple[str, ...], bounds: tuple[float | None, float | None] | None) -> pd.DataFrame:
    """Apply a numeric range to the first available column."""

    if bounds is None:
        return df
    column = next((item for item in columns if item in df.columns), None)
    if column is None:
        return df
    lower, upper = bounds
    values = pd.to_numeric(df[column], errors="coerce")
    out = df
    if lower is not None:
        out = out[values >= float(lower)]
        values = values.loc[out.index]
    if upper is not None:
        out = out[values <= float(upper)]
    return out


def _filter_band_labels(df: pd.DataFrame, bands: Iterable[str], *, band_columns: tuple[str, ...]) -> pd.DataFrame:
    """Filter rows by raw band tokens or equivalent display labels."""

    requested_raw = {str(band).strip() for band in bands if str(band).strip()}
    requested_labels = {band_display_label(band) for band in requested_raw}
    if not requested_raw:
        return df
    columns = [column for column in band_columns if column in df.columns]
    if not columns:
        return df
    mask = pd.Series(False, index=df.index)
    for column in columns:
        values = df[column].astype(str).str.strip()
        labels = values.map(band_display_label)
        mask = mask | values.isin(requested_raw) | labels.isin(requested_labels)
    return df.loc[mask]


__all__ = ["filter_dashboard_metrics", "filter_qc_dashboard_rows"]
