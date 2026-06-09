"""KML export helpers for station and event context maps."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd


def write_station_event_kml(
    stations: pd.DataFrame,
    events: pd.DataFrame,
    output_path: str | Path,
    *,
    station_col: str = "station",
    station_lat_col: str = "lat",
    station_lon_col: str = "lon",
    event_col: str = "event_id",
    event_lat_col: str = "lat",
    event_lon_col: str = "lon",
) -> Path:
    """Write station and event coordinates to a simple KML document.

    Parameters
    ----------
    stations, events
        Tables containing station/event names and coordinates.
    output_path
        Destination KML path.
    station_col, station_lat_col, station_lon_col
        Station name and coordinate columns.
    event_col, event_lat_col, event_lon_col
        Event name and coordinate columns.

    Returns
    -------
    pathlib.Path
        Path to the written KML file.
    """

    _require_columns(stations, [station_col, station_lat_col, station_lon_col], "stations")
    _require_columns(events, [event_col, event_lat_col, event_lon_col], "events")
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    placemarks: list[str] = []
    for _, row in stations.dropna(subset=[station_lat_col, station_lon_col]).iterrows():
        placemarks.append(
            _placemark(
                name=f"Station {row[station_col]}",
                lon=row[station_lon_col],
                lat=row[station_lat_col],
                style="stationStyle",
            )
        )
    for _, row in events.dropna(subset=[event_lat_col, event_lon_col]).iterrows():
        placemarks.append(
            _placemark(
                name=f"Event {row[event_col]}",
                lon=row[event_lon_col],
                lat=row[event_lat_col],
                style="eventStyle",
            )
        )

    text = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<kml xmlns="http://www.opengis.net/kml/2.2">',
            "  <Document>",
            "    <Style id=\"stationStyle\"><IconStyle><color>ff2f80ed</color><scale>0.8</scale></IconStyle></Style>",
            "    <Style id=\"eventStyle\"><IconStyle><color>ff3333cc</color><scale>1.0</scale></IconStyle></Style>",
            *placemarks,
            "  </Document>",
            "</kml>",
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")
    return path


def _placemark(name: str, lon: float, lat: float, style: str) -> str:
    """Create one KML placemark string."""

    return (
        "    <Placemark>"
        f"<name>{escape(str(name))}</name>"
        f"<styleUrl>#{style}</styleUrl>"
        f"<Point><coordinates>{float(lon):.8f},{float(lat):.8f},0</coordinates></Point>"
        "</Placemark>"
    )


def _require_columns(df: pd.DataFrame, columns: list[str], label: str) -> None:
    """Raise a readable error when required columns are missing."""

    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")
