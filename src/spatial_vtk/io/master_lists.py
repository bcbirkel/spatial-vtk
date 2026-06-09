"""Master station and event list construction helpers.

Purpose
-------
This module normalizes common station and event metadata column names into the
stable public Spatial-VTK table schemas.

Usage examples
--------------
Build lists from CSV files:
  ``build_master_station_list(station_tables=[pd.read_csv("stations.csv")])``
  ``build_master_event_list(event_tables=[pd.read_csv("events.csv")])``
"""

from __future__ import annotations

import argparse
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from spatial_vtk.io.waveforms import stream_station_table


STATION_ALIASES: dict[str, tuple[str, ...]] = {
    "network": ("network", "net", "station_network", "network_code", "Network", "Net"),
    "station": ("station", "station_code", "station_name", "code", "Station", "Code", "site"),
    "lat": ("lat", "latitude", "station_lat", "station_latitude", "stationlat", "Lat", "Latitude"),
    "lon": ("lon", "longitude", "station_lon", "station_longitude", "stationlon", "Lon", "Longitude"),
    "elev": ("elev", "elevation", "station_elev", "station_elevation", "Elevation"),
}

EVENT_ALIASES: dict[str, tuple[str, ...]] = {
    "event_id": ("event_id", "event", "id", "evid", "event_name", "event_title", "EventID"),
    "origin_time": ("origin_time", "time", "event_time", "datetime", "timestamp", "origin", "OriginTime"),
    "lat": ("lat", "latitude", "event_lat", "event_latitude", "hypocenter_lat", "Lat", "Latitude"),
    "lon": ("lon", "longitude", "event_lon", "event_longitude", "hypocenter_lon", "Lon", "Longitude"),
    "depth_km": ("depth_km", "depth", "event_depth_km", "hypocenter_depth_km", "DepthKm"),
    "magnitude": ("magnitude", "mag", "mw", "ml", "event_magnitude", "Magnitude"),
}

STATION_COLUMNS = ("network", "station", "lat", "lon", "elev")
EVENT_COLUMNS = ("event_id", "origin_time", "lat", "lon", "depth_km", "magnitude")


def build_master_station_list(
    *,
    station_tables: Sequence[pd.DataFrame | str | Path] | None = None,
    streams: Sequence[Any] | None = None,
    extra_columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Build a deduplicated master station list.

    Parameters
    ----------
    station_tables
        Station metadata tables or CSV paths.
    streams
        Optional waveform streams whose trace metadata includes station fields.
    extra_columns
        Optional extra columns to preserve when present in station tables.

    Returns
    -------
    pandas.DataFrame
        Deduplicated station table with public columns.
    """

    frames: list[pd.DataFrame] = []
    for table in station_tables or ():
        frames.append(normalize_station_table(_read_table(table), extra_columns=extra_columns))
    for stream in streams or ():
        frames.append(normalize_station_table(stream_station_table(stream), extra_columns=extra_columns))
    if not frames:
        return pd.DataFrame(columns=[*STATION_COLUMNS, *(extra_columns or ())])
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for frame in frames:
        for _, row in frame.iterrows():
            station = _normalize_station(row.get("station"))
            if not station:
                continue
            network = _normalize_network(row.get("network"))
            key = (network, station)
            payload = merged.setdefault(key, {"network": network, "station": station})
            for column in [*STATION_COLUMNS[2:], *(extra_columns or ())]:
                if column in row and _has_value(row[column]) and not _has_value(payload.get(column)):
                    payload[column] = row[column]
    return pd.DataFrame(merged.values()).reindex(columns=[*STATION_COLUMNS, *(extra_columns or ())]).sort_values(
        ["network", "station"], kind="stable"
    ).reset_index(drop=True)


def build_master_event_list(
    *,
    event_tables: Sequence[pd.DataFrame | str | Path] | None = None,
    event_records: Sequence[Mapping[str, Any]] | None = None,
    extra_columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Build a deduplicated master event list.

    Parameters
    ----------
    event_tables
        Event metadata tables or CSV paths.
    event_records
        Optional mapping records.
    extra_columns
        Optional extra columns to preserve.

    Returns
    -------
    pandas.DataFrame
        Deduplicated event table with public columns.
    """

    frames: list[pd.DataFrame] = []
    for table in event_tables or ():
        frames.append(normalize_event_table(_read_table(table), extra_columns=extra_columns))
    if event_records:
        frames.append(normalize_event_table(pd.DataFrame(list(event_records)), extra_columns=extra_columns))
    if not frames:
        return pd.DataFrame(columns=[*EVENT_COLUMNS, *(extra_columns or ())])
    merged: dict[str, dict[str, Any]] = {}
    for frame in frames:
        for _, row in frame.iterrows():
            event_id = str(row.get("event_id", "") or "").strip()
            if not event_id:
                continue
            payload = merged.setdefault(event_id, {"event_id": event_id})
            for column in [*EVENT_COLUMNS[1:], *(extra_columns or ())]:
                if column in row and _has_value(row[column]) and not _has_value(payload.get(column)):
                    payload[column] = row[column]
    return pd.DataFrame(merged.values()).reindex(columns=[*EVENT_COLUMNS, *(extra_columns or ())]).sort_values(
        ["event_id"], kind="stable"
    ).reset_index(drop=True)


def normalize_station_table(df: pd.DataFrame, *, extra_columns: Sequence[str] | None = None) -> pd.DataFrame:
    """Normalize station metadata columns.

    Parameters
    ----------
    df
        Raw station table.
    extra_columns
        Extra columns to preserve.

    Returns
    -------
    pandas.DataFrame
        Table with public station columns.
    """

    return _normalize_table(df, aliases=STATION_ALIASES, required=("station", "lat", "lon"), columns=STATION_COLUMNS, extra_columns=extra_columns)


def normalize_event_table(df: pd.DataFrame, *, extra_columns: Sequence[str] | None = None) -> pd.DataFrame:
    """Normalize event metadata columns.

    Parameters
    ----------
    df
        Raw event table.
    extra_columns
        Extra columns to preserve.

    Returns
    -------
    pandas.DataFrame
        Table with public event columns.
    """

    return _normalize_table(df, aliases=EVENT_ALIASES, required=("event_id", "lat", "lon"), columns=EVENT_COLUMNS, extra_columns=extra_columns)


def write_master_station_list(df: pd.DataFrame, path: str | Path, *, overwrite: bool = True) -> Path:
    """Write a master station list CSV."""

    return _write_csv(df.reindex(columns=[column for column in df.columns]), path, overwrite=overwrite)


def write_master_event_list(df: pd.DataFrame, path: str | Path, *, overwrite: bool = True) -> Path:
    """Write a master event list CSV."""

    return _write_csv(df.reindex(columns=[column for column in df.columns]), path, overwrite=overwrite)


def _normalize_table(
    df: pd.DataFrame,
    *,
    aliases: dict[str, tuple[str, ...]],
    required: Sequence[str],
    columns: Sequence[str],
    extra_columns: Sequence[str] | None,
) -> pd.DataFrame:
    """Normalize one metadata table by alias mapping."""

    if df is None or df.empty:
        return pd.DataFrame(columns=[*columns, *(extra_columns or ())])
    out = pd.DataFrame()
    for public_name, candidates in aliases.items():
        source = _find_column(df, candidates)
        if source is not None:
            out[public_name] = df[source]
        else:
            out[public_name] = ""
    missing = [name for name in required if not out[name].map(_has_value).any()]
    if missing:
        expected = {name: aliases[name] for name in missing}
        raise ValueError(
            "Metadata table is missing required columns. Rename your columns to one of these aliases: "
            f"{expected}. Available columns: {list(df.columns)}"
        )
    for column in ("lat", "lon", "elev", "depth_km", "magnitude"):
        if column in out:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    if "network" in out:
        out["network"] = out["network"].map(_normalize_network)
    if "station" in out:
        out["station"] = out["station"].map(_normalize_station)
    for column in extra_columns or ():
        if column in df:
            out[column] = df[column]
    return out.loc[:, [*columns, *(extra_columns or ())]]


def _find_column(df: pd.DataFrame, candidates: Sequence[str]) -> str | None:
    """Find a column by exact or case-insensitive alias."""

    exact = {str(column): str(column) for column in df.columns}
    lowered = {str(column).lower().replace("_", ""): str(column) for column in df.columns}
    for candidate in candidates:
        if candidate in exact:
            return exact[candidate]
        key = str(candidate).lower().replace("_", "")
        if key in lowered:
            return lowered[key]
    return None


def _read_table(table: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Read one table object or path."""

    if isinstance(table, pd.DataFrame):
        return table.copy()
    path = Path(table).expanduser()
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _write_csv(df: pd.DataFrame, path: str | Path, *, overwrite: bool) -> Path:
    """Write one CSV with explicit overwrite handling."""

    output = Path(path).expanduser()
    if output.exists() and not overwrite:
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    return output


def _normalize_station(value: Any) -> str:
    """Normalize one station code."""

    return str(value or "").strip().split(".")[-1].upper()


def _normalize_network(value: Any) -> str:
    """Normalize one network code."""

    text = str(value or "").strip().upper()
    return "UNKNOWN" if text in {"", "--", "NAN", "NONE", "NULL"} else text


def _has_value(value: Any) -> bool:
    """Return whether one scalar carries non-empty information."""

    if value is None:
        return False
    if isinstance(value, float) and not math.isfinite(value):
        return False
    return str(value).strip().lower() not in {"", "nan", "none", "null"}


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the module-level CLI parser."""

    parser = argparse.ArgumentParser(description="Build Spatial-VTK master station or event lists.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    stations = subparsers.add_parser("stations", help="Build a master station list.")
    stations.add_argument("--input", nargs="+", required=True, help="Station CSV/parquet paths.")
    stations.add_argument("--output", required=True, help="Output station CSV.")
    events = subparsers.add_parser("events", help="Build a master event list.")
    events.add_argument("--input", nargs="+", required=True, help="Event CSV/parquet paths.")
    events.add_argument("--output", required=True, help="Output event CSV.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the master-list CLI wrapper."""

    args = build_arg_parser().parse_args(argv)
    if args.command == "stations":
        write_master_station_list(build_master_station_list(station_tables=args.input), args.output)
    elif args.command == "events":
        write_master_event_list(build_master_event_list(event_tables=args.input), args.output)
    return 0


__all__ = [
    "STATION_ALIASES",
    "EVENT_ALIASES",
    "build_master_station_list",
    "build_master_event_list",
    "normalize_station_table",
    "normalize_event_table",
    "write_master_station_list",
    "write_master_event_list",
    "build_arg_parser",
    "main",
]

