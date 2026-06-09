"""General spatial geometry helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from spatial_vtk.spatial.calculate._common import haversine_km


def add_source_station_geometry(
    df: pd.DataFrame,
    *,
    event_lat_col: str = "event_lat",
    event_lon_col: str = "event_lon",
    station_lat_col: str = "sta_lat",
    station_lon_col: str = "sta_lon",
) -> pd.DataFrame:
    """Add distance, azimuth, and backazimuth to source-station rows."""

    out = df.copy()
    required = [event_lat_col, event_lon_col, station_lat_col, station_lon_col]
    missing = [column for column in required if column not in out.columns]
    if missing:
        raise KeyError(f"Missing coordinate columns: {missing}")
    event_lat = pd.to_numeric(out[event_lat_col], errors="coerce").to_numpy(dtype=float)
    event_lon = pd.to_numeric(out[event_lon_col], errors="coerce").to_numpy(dtype=float)
    sta_lat = pd.to_numeric(out[station_lat_col], errors="coerce").to_numpy(dtype=float)
    sta_lon = pd.to_numeric(out[station_lon_col], errors="coerce").to_numpy(dtype=float)
    out["distance_km"] = haversine_km(event_lat, event_lon, sta_lat, sta_lon)
    out["azimuth_deg"] = forward_azimuth_deg(event_lat, event_lon, sta_lat, sta_lon)
    out["backazimuth_deg"] = (out["azimuth_deg"] + 180.0) % 360.0
    return out


def forward_azimuth_deg(lat1, lon1, lat2, lon2):
    """Return forward azimuth from point 1 to point 2 in degrees."""

    lat1r = np.radians(lat1)
    lat2r = np.radians(lat2)
    dlon = np.radians(np.asarray(lon2, dtype=float) - np.asarray(lon1, dtype=float))
    x = np.sin(dlon) * np.cos(lat2r)
    y = np.cos(lat1r) * np.sin(lat2r) - np.sin(lat1r) * np.cos(lat2r) * np.cos(dlon)
    return (np.degrees(np.arctan2(x, y)) + 360.0) % 360.0
