"""Metric residual and metadata enrichment helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from spatial_vtk.io.tables import normalize_metric_table, wide_to_long_metrics


def prepare_metric_residual_table(
    df: pd.DataFrame,
    *,
    residual_mode: str = "logratio",
    residual_column: str | None = None,
    score_column: str | None = None,
    ensure_distance: bool = True,
) -> pd.DataFrame:
    """Normalize a wide metric table into long residual form.

    Parameters
    ----------
    df
        Wide table with ``*_obs``/``*_syn`` metric columns or an already-long
        table with ``metric`` and ``residual``.
    residual_mode
        ``"logratio"`` or ``"diff"`` when converting wide tables.
    residual_column
        Optional transform column to expose as canonical ``residual`` for
        downstream spatial and dashboard functions.
    score_column
        Optional GOF column to expose as canonical ``score``.
    ensure_distance
        Whether to add distance and azimuth columns when event/station
        coordinates are available.

    Returns
    -------
    pandas.DataFrame
        Long metric table using the public dashboard/spatial column contract.
    """

    if "metric" in df.columns:
        out = normalize_metric_table(df)
        for column in ["metric", "metric_group", "period_s", "value_obs", "value_syn", "residual", "score"]:
            if column in df.columns:
                out[column] = df[column]
        out = _apply_transform_columns(out, residual_column=residual_column, score_column=score_column)
    else:
        out = wide_to_long_metrics(df, residual_mode=residual_mode)
    out = _standardize_long_metric_columns(out)
    if ensure_distance:
        out = add_path_geometry_columns(out)
    return out


def enrich_metric_table(
    metrics_df: pd.DataFrame,
    *,
    events: pd.DataFrame | str | Path | None = None,
    stations: pd.DataFrame | str | Path | None = None,
    event_key: str = "event_id",
    station_key: str = "station",
    residual_column: str | None = None,
    score_column: str | None = None,
) -> pd.DataFrame:
    """Attach event and station metadata to a metric table.

    Parameters
    ----------
    metrics_df
        Metric table in wide or long form.
    events, stations
        Optional metadata tables or CSV paths.
    event_key, station_key
        Join columns.
    residual_column
        Optional transform column to expose as canonical ``residual``.
    score_column
        Optional GOF column to expose as canonical ``score``.

    Returns
    -------
    pandas.DataFrame
        Enriched long metric table.
    """

    out = prepare_metric_residual_table(metrics_df, residual_column=residual_column, score_column=score_column)
    if events is not None:
        event_df = _load_table(events)
        event_df = _rename_if_present(event_df, {"event_title": event_key, "event": event_key, "lat": "event_lat", "lon": "event_lon"})
        out = _merge_metadata_fill(out, event_df, key=event_key)
    if stations is not None:
        station_df = _load_table(stations)
        station_df = _rename_if_present(
            station_df,
            {
                "station_name": station_key,
                "Station": station_key,
                "station_lat": "sta_lat",
                "station_lon": "sta_lon",
                "station_latitude": "sta_lat",
                "station_longitude": "sta_lon",
                "lat": "sta_lat",
                "lon": "sta_lon",
            },
        )
        out = _merge_metadata_fill(out, station_df, key=station_key)
    return add_path_geometry_columns(out)


def add_path_geometry_columns(
    df: pd.DataFrame,
    *,
    event_lat_col: str = "event_lat",
    event_lon_col: str = "event_lon",
    station_lat_col: str = "sta_lat",
    station_lon_col: str = "sta_lon",
) -> pd.DataFrame:
    """Add source-station distance, azimuth, and backazimuth columns.

    Parameters
    ----------
    df
        Table with event and station coordinates.
    event_lat_col, event_lon_col, station_lat_col, station_lon_col
        Coordinate column names.

    Returns
    -------
    pandas.DataFrame
        Copy with ``distance_km``, ``azimuth_deg``, and ``backazimuth_deg`` when
        coordinates are available.
    """

    out = df.copy()
    required = [event_lat_col, event_lon_col, station_lat_col, station_lon_col]
    if not all(column in out.columns for column in required):
        return out
    event_lat = pd.to_numeric(out[event_lat_col], errors="coerce").to_numpy(dtype=float)
    event_lon = pd.to_numeric(out[event_lon_col], errors="coerce").to_numpy(dtype=float)
    sta_lat = pd.to_numeric(out[station_lat_col], errors="coerce").to_numpy(dtype=float)
    sta_lon = pd.to_numeric(out[station_lon_col], errors="coerce").to_numpy(dtype=float)
    out["distance_km"] = _haversine_km(event_lat, event_lon, sta_lat, sta_lon)
    out["azimuth_deg"] = _forward_azimuth_deg(event_lat, event_lon, sta_lat, sta_lon)
    out["backazimuth_deg"] = (out["azimuth_deg"] + 180.0) % 360.0
    return out


def _standardize_long_metric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Apply canonical long-metric column names."""

    out = df.copy()
    rename = {
        "event_title": "event_id",
        "event_latitude": "event_lat",
        "event_longitude": "event_lon",
        "station_name": "station",
        "station_latitude": "sta_lat",
        "station_longitude": "sta_lon",
        "lat": "sta_lat",
        "lon": "sta_lon",
    }
    out = out.rename(columns={old: new for old, new in rename.items() if old in out.columns and new not in out.columns})
    if "passband" in out.columns and ("band" not in out.columns or out["band"].isna().all()):
        passband = out["passband"].astype("object")
        out["band"] = passband.where(passband.notna() & passband.astype(str).str.strip().ne(""), "all")
    for column in ["model", "band", "event_id", "station", "metric"]:
        if column not in out.columns:
            out[column] = "unknown" if column != "band" else "all"
    if "residual" not in out.columns:
        out["residual"] = np.nan
    if "score" not in out.columns:
        out["score"] = np.nan
    for column in ["value", "residual", "score", "value_obs", "value_syn", "distance_km", "azimuth_deg"]:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    return out


def _apply_transform_columns(
    df: pd.DataFrame,
    *,
    residual_column: str | None,
    score_column: str | None,
) -> pd.DataFrame:
    """Expose selected transform columns through canonical downstream names."""

    out = df.copy()
    residual_candidates = [residual_column] if residual_column else []
    if "residual" not in out.columns or out["residual"].isna().all():
        residual_candidates.extend(["log2_residual", "ln_residual", "residual"])
    for column in residual_candidates:
        if column and column in out.columns:
            out["residual"] = pd.to_numeric(out[column], errors="coerce")
            break
    score_candidates = [score_column] if score_column else []
    if "score" not in out.columns or out["score"].isna().all():
        score_candidates.extend(["anderson_2004_gof", "olsen_mayhew_gof"])
    for column in score_candidates:
        if column and column in out.columns:
            out["score"] = pd.to_numeric(out[column], errors="coerce")
            break
    return out


def _forward_azimuth_deg(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Return forward azimuth from point 1 to point 2."""

    lat1r = np.radians(lat1)
    lat2r = np.radians(lat2)
    dlon = np.radians(lon2 - lon1)
    x = np.sin(dlon) * np.cos(lat2r)
    y = np.cos(lat1r) * np.sin(lat2r) - np.sin(lat1r) * np.cos(lat2r) * np.cos(dlon)
    return (np.degrees(np.arctan2(x, y)) + 360.0) % 360.0


def _haversine_km(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Return great-circle distance in kilometers."""

    radius_km = 6371.0088
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2.0) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2.0) ** 2
    return 2.0 * radius_km * np.arcsin(np.sqrt(a))


def _load_table(value: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Load a metadata table from a dataframe or path."""

    if isinstance(value, pd.DataFrame):
        return value.copy()
    path = Path(value)
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _rename_if_present(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Rename columns only when the target does not already exist."""

    return df.rename(columns={old: new for old, new in mapping.items() if old in df.columns and new not in df.columns})


def _merge_metadata_fill(base: pd.DataFrame, metadata: pd.DataFrame, *, key: str) -> pd.DataFrame:
    """Merge metadata and fill missing normalized columns.

    Parameters
    ----------
    base
        Metric table.
    metadata
        Metadata table with the join key.
    key
        Join column.

    Returns
    -------
    pandas.DataFrame
        Metric table with metadata columns filled where missing.
    """

    if key not in base.columns or key not in metadata.columns:
        return base
    columns = [column for column in metadata.columns if column == key or column not in base.columns or base[column].isna().all()]
    merged = base.merge(metadata[columns], on=key, how="left", suffixes=("", "__metadata"))
    for column in columns:
        if column == key:
            continue
        metadata_column = f"{column}__metadata"
        if metadata_column not in merged.columns:
            continue
        if column not in merged.columns:
            merged[column] = merged[metadata_column]
        else:
            missing = merged[column].isna()
            merged.loc[missing, column] = merged.loc[missing, metadata_column]
        merged = merged.drop(columns=[metadata_column])
    return merged
