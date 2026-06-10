"""Metadata preparation helpers for public Spatial-VTK workflows.

Purpose
-------
This module standardizes common station, event, and event-station metadata
tables so notebooks and scripts can start from different column naming
conventions without one-off renaming code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence
import numpy as np
import re

import pandas as pd

from spatial_vtk.io.tables import read_config_table


STATION_COLUMN_CANDIDATES: Mapping[str, tuple[str, ...]] = {
    "station": ("station", "station_id", "stationid", "station_code", "stationcode", "station_name", "stationname", "sta", "sta_id", "site", "site_id"),
    "network": ("network", "network_id", "networkid", "net", "net_id"),
    "lat": ("lat", "latitude", "station_lat", "stationlat", "station_latitude", "stationlatitude", "sta_lat", "stalat", "site_lat", "sitelat"),
    "lon": (
        "lon",
        "long",
        "longitude",
        "station_lon",
        "stationlon",
        "station_longitude",
        "stationlongitude",
        "sta_lon",
        "stalon",
        "site_lon",
        "sitelon",
        "station_lng",
        "lng",
    ),
}

EVENT_COLUMN_CANDIDATES: Mapping[str, tuple[str, ...]] = {
    "event_id": ("event_id", "eventid", "event", "event_name", "eventname", "event_title", "eventtitle", "id", "source_id", "origin_id"),
    "event_lat": ("event_lat", "eventlat", "event_latitude", "eventlatitude", "lat", "latitude", "source_lat", "sourcelat", "origin_lat", "originlat"),
    "event_lon": (
        "event_lon",
        "eventlon",
        "event_longitude",
        "eventlongitude",
        "lon",
        "long",
        "longitude",
        "source_lon",
        "sourcelon",
        "origin_lon",
        "originlon",
        "lng",
    ),
    "magnitude": ("magnitude", "mag", "mw", "ml", "event_magnitude", "eventmag"),
    "depth_km": ("depth_km", "depth", "event_depth_km", "event_depth", "depthkm", "hypocentral_depth_km"),
    "origin_time": ("origin_time", "origintime", "time", "event_time", "eventtime", "datetime", "timestamp"),
}

EVENT_STATION_COLUMN_CANDIDATES: Mapping[str, tuple[str, ...]] = {
    "event_id": EVENT_COLUMN_CANDIDATES["event_id"],
    "station": STATION_COLUMN_CANDIDATES["station"],
    "network": STATION_COLUMN_CANDIDATES["network"],
}


def _normalize_column_name(name: object) -> str:
    """Normalize one column name for permissive matching.

    Parameters
    ----------
    name
        Raw column name.

    Returns
    -------
    str
        Lowercase alphanumeric token used for matching aliases.
    """

    return re.sub(r"[^a-z0-9]+", "", str(name).strip().lower())


def _resolve_column(df: pd.DataFrame, target: str, candidates: Sequence[str], *, required: bool) -> str | None:
    """Resolve one canonical metadata column from accepted aliases.

    Parameters
    ----------
    df
        Metadata table.
    target
        Canonical output column name.
    candidates
        Accepted aliases for ``target``.
    required
        Whether to raise when no alias is present.

    Returns
    -------
    str or None
        Matched input column name, or ``None`` for missing optional columns.
    """

    lookup = {_normalize_column_name(column): str(column) for column in df.columns}
    for candidate in candidates:
        match = lookup.get(_normalize_column_name(candidate))
        if match is not None:
            return match
    if required:
        accepted = ", ".join(candidates)
        available = ", ".join(str(column) for column in df.columns)
        raise KeyError(
            f"Could not find a metadata column for {target!r}. "
            f"Rename one of your columns to one of: {accepted}. "
            f"Available columns: {available}"
        )
    return None


def _coerce_numeric(out: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    """Coerce selected columns to numeric values.

    Parameters
    ----------
    out
        Metadata table.
    columns
        Column names to coerce when present.

    Returns
    -------
    pandas.DataFrame
        Copy with numeric columns converted.
    """

    for column in columns:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    return out


def prepare_station_metadata(
    station_metadata: pd.DataFrame | None = None,
    *,
    required_columns: Sequence[str] = ("station", "lat", "lon"),
    keep_extra_columns: bool = True,
) -> pd.DataFrame:
    """Prepare a station metadata table with canonical station columns.

    Parameters
    ----------
    station_metadata
        Input table with station identifiers and coordinates. When omitted,
        ``paths.station_metadata`` is read from the active config.
    required_columns
        Canonical columns required in the output.
    keep_extra_columns
        Whether to retain input columns not used for canonical names.

    Returns
    -------
    pandas.DataFrame
        Prepared table containing at least ``station``, ``lat``, and ``lon``.
    """

    df = (station_metadata.copy() if station_metadata is not None else read_config_table("paths.station_metadata"))
    mapping: dict[str, str] = {}
    required = set(required_columns)
    for target, candidates in STATION_COLUMN_CANDIDATES.items():
        source = _resolve_column(df, target, candidates, required=target in required)
        if source is not None:
            mapping[source] = target
    out = df.rename(columns=mapping).copy()
    if not keep_extra_columns:
        keep = [column for column in STATION_COLUMN_CANDIDATES if column in out.columns]
        out = out[keep].copy()
    if "station" in out.columns:
        out["station"] = out["station"].astype(str).str.strip().str.upper()
    if "network" in out.columns:
        out["network"] = out["network"].astype(str).str.strip()
    out = _coerce_numeric(out, ["lat", "lon"])
    out.dropna(subset=list(required), inplace=True)
    out.drop_duplicates(subset=["station"], inplace=True)
    return out.reset_index(drop=True)


def read_station_metadata(path: str | Path, **kwargs) -> pd.DataFrame:
    """Read and prepare a station metadata CSV file.

    Parameters
    ----------
    path
        CSV path.
    **kwargs
        Extra arguments passed to ``prepare_station_metadata``.

    Returns
    -------
    pandas.DataFrame
        Prepared station metadata table.
    """

    return prepare_station_metadata(pd.read_csv(path), **kwargs)


def prepare_event_metadata(
    event_metadata: pd.DataFrame | None = None,
    *,
    required_columns: Sequence[str] = ("event_id", "event_lat", "event_lon"),
    keep_extra_columns: bool = True,
) -> pd.DataFrame:
    """Prepare an event metadata table with canonical event columns.

    Parameters
    ----------
    event_metadata
        Input table with event identifiers and hypocenter/source metadata.
        When omitted, ``paths.event_metadata`` is read from the active config.
    required_columns
        Canonical columns required in the output.
    keep_extra_columns
        Whether to retain input columns not used for canonical names.

    Returns
    -------
    pandas.DataFrame
        Prepared table containing at least ``event_id``, ``event_lat``, and
        ``event_lon``.
    """

    df = (event_metadata.copy() if event_metadata is not None else read_config_table("paths.event_metadata"))
    mapping: dict[str, str] = {}
    required = set(required_columns)
    for target, candidates in EVENT_COLUMN_CANDIDATES.items():
        source = _resolve_column(df, target, candidates, required=target in required)
        if source is not None:
            mapping[source] = target
    out = df.rename(columns=mapping).copy()
    if not keep_extra_columns:
        keep = [column for column in EVENT_COLUMN_CANDIDATES if column in out.columns]
        out = out[keep].copy()
    if "event_id" in out.columns:
        out["event_id"] = out["event_id"].astype(str).str.strip()
    out = _coerce_numeric(out, ["event_lat", "event_lon", "magnitude", "depth_km"])
    out.dropna(subset=list(required), inplace=True)
    out.drop_duplicates(subset=["event_id"], inplace=True)
    return out.reset_index(drop=True)


def read_event_metadata(path: str | Path, **kwargs) -> pd.DataFrame:
    """Read and prepare an event metadata CSV file.

    Parameters
    ----------
    path
        CSV path.
    **kwargs
        Extra arguments passed to ``prepare_event_metadata``.

    Returns
    -------
    pandas.DataFrame
        Prepared event metadata table.
    """

    return prepare_event_metadata(pd.read_csv(path), **kwargs)


def prepare_event_station_table(
    event_station_metadata: pd.DataFrame | None = None,
    *,
    station_metadata: pd.DataFrame | None = None,
    event_metadata: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Prepare event-station rows and optionally join station/event metadata.

    Parameters
    ----------
    event_station_metadata
        Table containing event and station identifiers. When omitted and both
        ``station_metadata`` and ``event_metadata`` are provided, every
        event-station pair is generated from those tables. When omitted without
        both metadata tables, ``paths.event_station_table`` is read from the
        active config.
    station_metadata
        Optional prepared station metadata table.
    event_metadata
        Optional prepared event metadata table.

    Returns
    -------
    pandas.DataFrame
        Event-station table with canonical identifiers and joined metadata.
    """

    if event_station_metadata is not None:
        df = event_station_metadata.copy()
    elif station_metadata is not None and event_metadata is not None:
        df = _build_event_station_pairs(station_metadata=station_metadata, event_metadata=event_metadata)
    else:
        df = read_config_table("paths.event_station_table")
    mapping: dict[str, str] = {}
    for target, candidates in EVENT_STATION_COLUMN_CANDIDATES.items():
        source = _resolve_column(df, target, candidates, required=target in {"event_id", "station"})
        if source is not None:
            mapping[source] = target
    out = df.rename(columns=mapping).copy()
    out["event_id"] = out["event_id"].astype(str).str.strip()
    out["station"] = out["station"].astype(str).str.strip()
    out = out.dropna(subset=["event_id", "station"]).drop_duplicates(subset=["event_id", "station"])
    if station_metadata is not None and not station_metadata.empty:
        out = out.merge(station_metadata, on="station", how="left", validate="many_to_one")
    if event_metadata is not None and not event_metadata.empty:
        out = out.merge(event_metadata, on="event_id", how="left", validate="many_to_one", suffixes=("", "_event"))
    out = _add_path_geometry(out)
    return out.reset_index(drop=True)


def _build_event_station_pairs(*, station_metadata: pd.DataFrame, event_metadata: pd.DataFrame) -> pd.DataFrame:
    """Build the full event-station pair table from station and event metadata."""

    if station_metadata.empty or event_metadata.empty:
        return pd.DataFrame(columns=["event_id", "station"])
    station_col = _resolve_column(station_metadata, "station", STATION_COLUMN_CANDIDATES["station"], required=True)
    event_col = _resolve_column(event_metadata, "event_id", EVENT_COLUMN_CANDIDATES["event_id"], required=True)
    stations = station_metadata[[station_col]].rename(columns={station_col: "station"}).copy()
    events = event_metadata[[event_col]].rename(columns={event_col: "event_id"}).copy()
    stations = stations.dropna(subset=["station"])
    events = events.dropna(subset=["event_id"])
    stations["station"] = stations["station"].astype(str).str.strip()
    events["event_id"] = events["event_id"].astype(str).str.strip()
    stations = stations[stations["station"] != ""].drop_duplicates(subset=["station"])
    events = events[events["event_id"] != ""].drop_duplicates(subset=["event_id"])
    return events.merge(stations, how="cross")


def read_event_station_table(path: str | Path, **kwargs) -> pd.DataFrame:
    """Read and prepare an event-station metadata CSV file.

    Parameters
    ----------
    path
        CSV path.
    **kwargs
        Extra arguments passed to ``prepare_event_station_table``.

    Returns
    -------
    pandas.DataFrame
        Prepared event-station table.
    """

    return prepare_event_station_table(pd.read_csv(path), **kwargs)


def _add_path_geometry(df: pd.DataFrame) -> pd.DataFrame:
    """Add source-to-station distance and azimuth columns when coordinates exist.

    Parameters
    ----------
    df
        Event-station table with event and station coordinates.

    Returns
    -------
    pandas.DataFrame
        Copy with ``distance_km``, ``azimuth_deg``, and ``backazimuth_deg``
        filled where coordinates are available.
    """

    out = df.copy()
    station_lat_col = _first_existing_column(out, ("station_lat", "sta_lat", "lat"))
    station_lon_col = _first_existing_column(out, ("station_lon", "sta_lon", "lon"))
    event_lat_col = _first_existing_column(out, ("event_lat", "source_lat", "origin_lat"))
    event_lon_col = _first_existing_column(out, ("event_lon", "source_lon", "origin_lon"))
    if not all((station_lat_col, station_lon_col, event_lat_col, event_lon_col)):
        return out

    station_lat = pd.to_numeric(out[station_lat_col], errors="coerce")
    station_lon = pd.to_numeric(out[station_lon_col], errors="coerce")
    event_lat = pd.to_numeric(out[event_lat_col], errors="coerce")
    event_lon = pd.to_numeric(out[event_lon_col], errors="coerce")
    distance_km, azimuth_deg, backazimuth_deg = _haversine_distance_and_azimuth(
        event_lat=event_lat,
        event_lon=event_lon,
        station_lat=station_lat,
        station_lon=station_lon,
    )
    out["distance_km"] = _fill_numeric_column(out, "distance_km", distance_km)
    out["azimuth_deg"] = _fill_numeric_column(out, "azimuth_deg", azimuth_deg)
    out["backazimuth_deg"] = _fill_numeric_column(out, "backazimuth_deg", backazimuth_deg)
    return out


def _first_existing_column(df: pd.DataFrame, candidates: Sequence[str]) -> str | None:
    """Return the first existing column from a candidate list.

    Parameters
    ----------
    df
        Table to inspect.
    candidates
        Candidate column names in preference order.

    Returns
    -------
    str or None
        First matching column name, or ``None`` when no candidate exists.
    """

    for column in candidates:
        if column in df.columns:
            return column
    return None


def _fill_numeric_column(df: pd.DataFrame, column: str, values: pd.Series) -> pd.Series:
    """Fill missing numeric values without overwriting existing values.

    Parameters
    ----------
    df
        Table that may already contain ``column``.
    column
        Output column name.
    values
        Computed fallback values.

    Returns
    -------
    pandas.Series
        Existing numeric values with missing entries filled from ``values``.
    """

    if column not in df.columns:
        return values
    return pd.to_numeric(df[column], errors="coerce").combine_first(values)


def _haversine_distance_and_azimuth(
    *,
    event_lat: pd.Series,
    event_lon: pd.Series,
    station_lat: pd.Series,
    station_lon: pd.Series,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Compute epicentral distance, azimuth, and backazimuth.

    Parameters
    ----------
    event_lat, event_lon
        Event coordinates in decimal degrees.
    station_lat, station_lon
        Station coordinates in decimal degrees.

    Returns
    -------
    tuple[pandas.Series, pandas.Series, pandas.Series]
        Distance in kilometers, event-to-station azimuth in degrees, and
        station-to-event backazimuth in degrees.
    """

    radius_km = 6371.0088
    event_lat_rad = np.radians(event_lat.astype(float))
    event_lon_rad = np.radians(event_lon.astype(float))
    station_lat_rad = np.radians(station_lat.astype(float))
    station_lon_rad = np.radians(station_lon.astype(float))
    dlat = station_lat_rad - event_lat_rad
    dlon = station_lon_rad - event_lon_rad
    a = np.sin(dlat / 2.0) ** 2 + np.cos(event_lat_rad) * np.cos(station_lat_rad) * np.sin(dlon / 2.0) ** 2
    distance = 2.0 * radius_km * np.arcsin(np.sqrt(a))

    azimuth_y = np.sin(dlon) * np.cos(station_lat_rad)
    azimuth_x = np.cos(event_lat_rad) * np.sin(station_lat_rad) - np.sin(event_lat_rad) * np.cos(station_lat_rad) * np.cos(dlon)
    azimuth = (np.degrees(np.arctan2(azimuth_y, azimuth_x)) + 360.0) % 360.0

    reverse_dlon = -dlon
    backazimuth_y = np.sin(reverse_dlon) * np.cos(event_lat_rad)
    backazimuth_x = np.cos(station_lat_rad) * np.sin(event_lat_rad) - np.sin(station_lat_rad) * np.cos(event_lat_rad) * np.cos(reverse_dlon)
    backazimuth = (np.degrees(np.arctan2(backazimuth_y, backazimuth_x)) + 360.0) % 360.0

    invalid = event_lat.isna() | event_lon.isna() | station_lat.isna() | station_lon.isna()
    return (
        pd.Series(distance, index=event_lat.index).mask(invalid),
        pd.Series(azimuth, index=event_lat.index).mask(invalid),
        pd.Series(backazimuth, index=event_lat.index).mask(invalid),
    )
