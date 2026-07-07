"""Build final enriched metric tables for publication and review.

This module trims empty metric-output columns and attaches the station, event,
GeoJSON region, and geology metadata needed by downstream review notebooks.

Usage
-----
From a run root:
  ``python -m spatial_vtk.metrics.finalize``
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import pandas as pd
from shapely.geometry import Point, shape


BLANK_TEXT_TOKENS = frozenset({"", "nan", "none", "null", "na", "n/a", "<na>"})
DEFAULT_INPUT = Path("runs/outputs/tables/metrics_enriched.parquet")
DEFAULT_STATIONS = Path("runs/outputs/tables/prepared_stations.csv")
DEFAULT_EVENTS = Path("runs/outputs/tables/prepared_events.csv")
DEFAULT_REGIONS = Path("runs/inputs/geospatial/regions_updated.geojson")
DEFAULT_GEOLOGY = Path("runs/inputs/metadata/geologic_metadata.csv")
DEFAULT_OUTPUT_NAME = "metrics_final_enriched.parquet"


def build_final_metrics_table(
    metrics: pd.DataFrame | str | Path = DEFAULT_INPUT,
    *,
    stations: pd.DataFrame | str | Path | None = DEFAULT_STATIONS,
    events: pd.DataFrame | str | Path | None = DEFAULT_EVENTS,
    regions_geojson: str | Path | None = DEFAULT_REGIONS,
    geologic_metadata: pd.DataFrame | str | Path | None = DEFAULT_GEOLOGY,
    geology_coordinate_rounds: Sequence[int] = (3, 2),
) -> pd.DataFrame:
    """Return a final metric table with empty columns removed and metadata joined.

    Parameters
    ----------
    metrics
        Metric table or path. All columns that are entirely null, NaN, empty
        strings, or common text-null tokens are removed before metadata joins.
    stations, events
        Prepared station and event metadata tables. Missing values in canonical
        metric columns are filled from these tables when possible.
    regions_geojson
        GeoJSON polygon file used to add station/event region labels and broad
        geomorphology classes.
    geologic_metadata
        Geologic metadata CSV/table used to add ``Vs30`` and
        ``geologic_description`` by station code, with coordinate fallback.
    geology_coordinate_rounds
        Decimal precisions used for unique coordinate fallback after station
        code matching.

    Returns
    -------
    pandas.DataFrame
        Final enriched metric rows.
    """

    out = _read_table(metrics)
    out = drop_blank_columns(out)
    if stations is not None:
        station_frame = _prepared_station_metadata(stations)
        out = _merge_fill(out, station_frame, on="station")
    if events is not None:
        event_frame = _prepared_event_metadata(events)
        out = _merge_fill(out, event_frame, on="event_id")
    if regions_geojson is not None:
        out = _add_geojson_region_metadata(out, regions_geojson)
    if geologic_metadata is not None:
        out = _add_geologic_metadata(out, geologic_metadata, coordinate_rounds=geology_coordinate_rounds)
    return drop_blank_columns(out)


def write_final_metrics_table(
    metrics: pd.DataFrame | str | Path = DEFAULT_INPUT,
    output: str | Path | None = None,
    *,
    stations: pd.DataFrame | str | Path | None = DEFAULT_STATIONS,
    events: pd.DataFrame | str | Path | None = DEFAULT_EVENTS,
    regions_geojson: str | Path | None = DEFAULT_REGIONS,
    geologic_metadata: pd.DataFrame | str | Path | None = DEFAULT_GEOLOGY,
    geology_coordinate_rounds: Sequence[int] = (3, 2),
) -> Path:
    """Write the final enriched metrics parquet and return its path."""

    input_path = Path(metrics).expanduser() if isinstance(metrics, str | Path) else None
    if output is None:
        output_path = (input_path.parent if input_path is not None else Path(".")) / DEFAULT_OUTPUT_NAME
    else:
        output_path = Path(output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame = build_final_metrics_table(
        metrics,
        stations=stations,
        events=events,
        regions_geojson=regions_geojson,
        geologic_metadata=geologic_metadata,
        geology_coordinate_rounds=geology_coordinate_rounds,
    )
    frame.to_parquet(output_path, index=False)
    return output_path


def drop_blank_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return ``df`` without columns that contain no real values."""

    keep = [column for column in df.columns if _has_real_values(df[column])]
    return df.loc[:, keep].copy()


def _has_real_values(series: pd.Series) -> bool:
    if series.notna().sum() == 0:
        return False
    if _is_text_like(series):
        text = series.astype("string").str.strip().str.casefold()
        return bool((series.notna() & ~text.isin(BLANK_TEXT_TOKENS)).any())
    return bool(series.notna().any())


def _is_text_like(series: pd.Series) -> bool:
    return pd.api.types.is_string_dtype(series) or series.dtype == object


def _read_table(table: pd.DataFrame | str | Path) -> pd.DataFrame:
    if isinstance(table, pd.DataFrame):
        return table.copy()
    path = Path(table).expanduser()
    suffix = path.suffix.casefold()
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if suffix in {"", ".csv"}:
        return pd.read_csv(path, low_memory=False)
    raise ValueError(f"Unsupported table format for {path}. Use Parquet or CSV.")


def _prepared_station_metadata(stations: pd.DataFrame | str | Path) -> pd.DataFrame:
    frame = _read_table(stations)
    rename = {
        "lat": "sta_lat",
        "latitude": "sta_lat",
        "station_latitude": "sta_lat",
        "lon": "sta_lon",
        "longitude": "sta_lon",
        "station_longitude": "sta_lon",
        "elevation": "elev",
    }
    frame = frame.rename(columns={old: new for old, new in rename.items() if old in frame.columns})
    if "station" not in frame.columns:
        raise KeyError("Station metadata must include a 'station' column.")
    frame = frame.copy()
    frame["station"] = _normalize_key(frame["station"])
    columns = [column for column in ("station", "network", "sta_lat", "sta_lon", "elev") if column in frame.columns]
    return _first_nonblank_by_key(frame.loc[:, columns], "station")


def _prepared_event_metadata(events: pd.DataFrame | str | Path) -> pd.DataFrame:
    frame = _read_table(events)
    if "event_id" not in frame.columns:
        raise KeyError("Event metadata must include an 'event_id' column.")
    frame = frame.copy()
    frame["event_id"] = _normalize_key(frame["event_id"])
    if "depth_km" in frame.columns and "event_depth_km" not in frame.columns:
        frame = frame.rename(columns={"depth_km": "event_depth_km"})
    columns = [
        column
        for column in (
            "event_id",
            "event_name",
            "event_lat",
            "event_lon",
            "start",
            "strike",
            "dip",
            "rake",
            "magnitude",
            "event_depth_km",
            "source",
        )
        if column in frame.columns
    ]
    return _first_nonblank_by_key(frame.loc[:, columns], "event_id")


def _merge_fill(left: pd.DataFrame, right: pd.DataFrame, *, on: str) -> pd.DataFrame:
    if on not in left.columns or right.empty or on not in right.columns:
        return left
    out = left.copy()
    out[on] = _normalize_key(out[on])
    value_cols = [column for column in right.columns if column != on]
    merged = out.merge(right, on=on, how="left", suffixes=("", "__metadata"))
    for column in value_cols:
        meta_column = f"{column}__metadata" if column in out.columns else column
        if meta_column not in merged.columns:
            continue
        if column in out.columns:
            merged[column] = _fill_blank_values(merged[column], merged[meta_column])
            if meta_column != column:
                merged = merged.drop(columns=[meta_column])
        else:
            merged = merged.rename(columns={meta_column: column}) if meta_column != column else merged
    return merged


def _add_geojson_region_metadata(df: pd.DataFrame, geojson_path: str | Path) -> pd.DataFrame:
    regions = _load_regions(geojson_path)
    out = df.copy()
    station_lookup = _classify_unique_points(
        out,
        key_col="station",
        lon_col="sta_lon",
        lat_col="sta_lat",
        prefix="station",
        regions=regions,
    )
    if not station_lookup.empty:
        out = _merge_fill(out, station_lookup, on="station")
    event_lookup = _classify_unique_points(
        out,
        key_col="event_id",
        lon_col="event_lon",
        lat_col="event_lat",
        prefix="event",
        regions=regions,
    )
    if not event_lookup.empty:
        out = _merge_fill(out, event_lookup, on="event_id")
    return out


def _load_regions(path: str | Path) -> list[dict[str, Any]]:
    geojson = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    regions: list[dict[str, Any]] = []
    for feature in geojson.get("features", []):
        props = feature.get("properties") or {}
        geom = feature.get("geometry")
        if not geom:
            continue
        region_name = _first_defined(
            props.get("long_name"),
            props.get("region_name"),
            props.get("name"),
            props.get("short_name"),
            props.get("label"),
        )
        region_type = _first_defined(props.get("region_type"), props.get("mapped_region_type"), props.get("class"))
        regions.append(
            {
                "geometry": shape(geom),
                "region": region_name,
                "region_type": region_type,
                "geomorphology": _geomorphology_from_region_type(region_type),
            }
        )
    if not regions:
        raise ValueError(f"No polygon features were loaded from {path}.")
    return regions


def _classify_unique_points(
    df: pd.DataFrame,
    *,
    key_col: str,
    lon_col: str,
    lat_col: str,
    prefix: str,
    regions: Sequence[dict[str, Any]],
) -> pd.DataFrame:
    if key_col not in df.columns or lon_col not in df.columns or lat_col not in df.columns:
        return pd.DataFrame()
    points = df[[key_col, lon_col, lat_col]].dropna(subset=[key_col]).drop_duplicates(key_col).copy()
    if points.empty:
        return pd.DataFrame()
    points[key_col] = _normalize_key(points[key_col])
    records: list[dict[str, Any]] = []
    for row in points.itertuples(index=False):
        key = getattr(row, key_col)
        lon = getattr(row, lon_col)
        lat = getattr(row, lat_col)
        match = _point_region(lon, lat, regions)
        records.append(
            {
                key_col: key,
                f"{prefix}_region": pd.NA if match is None else match["region"],
                f"{prefix}_region_type": pd.NA if match is None else match["region_type"],
                f"{prefix}_geomorphology": pd.NA if match is None else match["geomorphology"],
            }
        )
    return pd.DataFrame.from_records(records)


def _point_region(lon: object, lat: object, regions: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        point = Point(float(lon), float(lat))
    except (TypeError, ValueError):
        return None
    for region in regions:
        if region["geometry"].covers(point):
            return region
    return None


def _geomorphology_from_region_type(value: object) -> object:
    text = str(value).strip().casefold()
    if text == "basin":
        return "Basin"
    if text in {"mountain", "mountains", "hill", "hills"}:
        return "Mountain/hills"
    if text in {"valley", "valleys"}:
        return "Valley"
    if text:
        return str(value).strip()
    return pd.NA


def _add_geologic_metadata(
    df: pd.DataFrame,
    geologic_metadata: pd.DataFrame | str | Path,
    *,
    coordinate_rounds: Sequence[int],
) -> pd.DataFrame:
    if "station" not in df.columns:
        return df
    geo = _geology_lookup(geologic_metadata)
    out = df.copy()
    out["station"] = _normalize_key(out["station"])
    station_lookup = _first_nonblank_by_key(geo[["station", "Vs30", "geologic_description"]], "station")
    out = _merge_fill(out, station_lookup, on="station")
    if "sta_lat" not in out.columns or "sta_lon" not in out.columns:
        return out
    station_geo = out[["station", "sta_lat", "sta_lon", "Vs30", "geologic_description"]].drop_duplicates("station")
    for digits in coordinate_rounds:
        missing = _blank_mask(station_geo["Vs30"]) & _blank_mask(station_geo["geologic_description"])
        if not bool(missing.any()):
            break
        coordinate_lookup = _unique_coordinate_geology(geo, digits=digits)
        if coordinate_lookup.empty:
            continue
        pending = station_geo.loc[missing, ["station", "sta_lat", "sta_lon"]].copy()
        pending["_geo_lat_key"] = pd.to_numeric(pending["sta_lat"], errors="coerce").round(digits)
        pending["_geo_lon_key"] = pd.to_numeric(pending["sta_lon"], errors="coerce").round(digits)
        pending = pending.merge(coordinate_lookup, on=["_geo_lat_key", "_geo_lon_key"], how="left")
        fill_lookup = pending[["station", "Vs30", "geologic_description"]].dropna(how="all", subset=["Vs30", "geologic_description"])
        if fill_lookup.empty:
            continue
        station_geo = _merge_fill(station_geo, fill_lookup, on="station")
    final_lookup = station_geo[["station", "Vs30", "geologic_description"]]
    return _merge_fill(out.drop(columns=[column for column in ("Vs30", "geologic_description") if column in out.columns]), final_lookup, on="station")


def _geology_lookup(geologic_metadata: pd.DataFrame | str | Path) -> pd.DataFrame:
    frame = _read_table(geologic_metadata)
    required = {"Station", "Vs30", "geologic_description"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise KeyError(f"Geologic metadata is missing required column(s): {', '.join(missing)}")
    geo = frame.copy()
    geo["station"] = _normalize_key(geo["Station"])
    geo["Vs30"] = pd.to_numeric(geo["Vs30"], errors="coerce")
    geo.loc[geo["Vs30"] <= 0, "Vs30"] = pd.NA
    geo["geologic_description"] = _clean_text(geo["geologic_description"])
    if "Alternate geologic description" in geo.columns:
        alternate = _clean_text(geo["Alternate geologic description"])
        geo["geologic_description"] = _fill_blank_values(geo["geologic_description"], alternate)
    cols = ["station", "Latitude", "Longitude", "Vs30", "geologic_description"]
    return geo.loc[:, [column for column in cols if column in geo.columns]]


def _unique_coordinate_geology(geo: pd.DataFrame, *, digits: int) -> pd.DataFrame:
    if "Latitude" not in geo.columns or "Longitude" not in geo.columns:
        return pd.DataFrame()
    lookup = geo.copy()
    lookup["_geo_lat_key"] = pd.to_numeric(lookup["Latitude"], errors="coerce").round(digits)
    lookup["_geo_lon_key"] = pd.to_numeric(lookup["Longitude"], errors="coerce").round(digits)
    lookup = lookup.dropna(subset=["_geo_lat_key", "_geo_lon_key"])
    lookup = lookup.loc[:, ["_geo_lat_key", "_geo_lon_key", "Vs30", "geologic_description"]]
    key_counts = lookup.groupby(["_geo_lat_key", "_geo_lon_key"], dropna=False).size().rename("_count").reset_index()
    unique_keys = key_counts.loc[key_counts["_count"].eq(1), ["_geo_lat_key", "_geo_lon_key"]]
    lookup = lookup.merge(unique_keys, on=["_geo_lat_key", "_geo_lon_key"], how="inner")
    return lookup.drop_duplicates(["_geo_lat_key", "_geo_lon_key"])


def _first_nonblank_by_key(df: pd.DataFrame, key: str) -> pd.DataFrame:
    if df.empty:
        return df
    work = df.copy()
    value_cols = [column for column in work.columns if column != key]
    rows: list[dict[str, Any]] = []
    for key_value, group in work.groupby(key, dropna=False, sort=False):
        row: dict[str, Any] = {key: key_value}
        for column in value_cols:
            values = group[column]
            real_values = values.loc[~_blank_mask(values)]
            row[column] = pd.NA if real_values.empty else real_values.iloc[0]
        rows.append(row)
    return pd.DataFrame.from_records(rows, columns=[key, *value_cols])


def _normalize_key(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    text = text.str.replace(r"\.0$", "", regex=True)
    return text


def _clean_text(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    return text.mask(text.str.casefold().isin(BLANK_TEXT_TOKENS))


def _blank_mask(series: pd.Series) -> pd.Series:
    if _is_text_like(series):
        text = series.astype("string").str.strip().str.casefold()
        return series.isna() | text.isin(BLANK_TEXT_TOKENS)
    return series.isna()


def _fill_blank_values(base: pd.Series, fallback: pd.Series) -> pd.Series:
    out = base.copy()
    mask = _blank_mask(out)
    out.loc[mask] = fallback.loc[mask]
    return out


def _first_defined(*values: object) -> object:
    for value in values:
        if pd.isna(value):
            continue
        text = str(value).strip()
        if text and text.casefold() not in BLANK_TEXT_TOKENS:
            return text
    return pd.NA


def _parse_coordinate_rounds(value: str) -> tuple[int, ...]:
    if not value.strip():
        return ()
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-input", type=Path, default=DEFAULT_INPUT, help="Input metrics parquet/csv path.")
    parser.add_argument("--output", type=Path, default=None, help="Output parquet path.")
    parser.add_argument("--stations", type=Path, default=DEFAULT_STATIONS, help="Prepared station metadata table.")
    parser.add_argument("--events", type=Path, default=DEFAULT_EVENTS, help="Prepared event metadata table.")
    parser.add_argument("--regions-geojson", type=Path, default=DEFAULT_REGIONS, help="Region GeoJSON polygon file.")
    parser.add_argument("--geologic-metadata", type=Path, default=DEFAULT_GEOLOGY, help="Geologic metadata CSV/table.")
    parser.add_argument(
        "--geology-coordinate-rounds",
        default="3,2",
        help="Comma-separated coordinate precisions for geology fallback after station-code matching.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point."""

    args = _build_parser().parse_args(argv)
    coordinate_rounds = _parse_coordinate_rounds(args.geology_coordinate_rounds)
    output = write_final_metrics_table(
        args.metrics_input,
        args.output,
        stations=args.stations,
        events=args.events,
        regions_geojson=args.regions_geojson,
        geologic_metadata=args.geologic_metadata,
        geology_coordinate_rounds=coordinate_rounds,
    )
    final = pd.read_parquet(output)
    print(f"wrote={output}")
    print(f"rows={len(final)}")
    print(f"columns={len(final.columns)}")
    print("metadata_columns=" + ",".join(_metadata_columns(final.columns)))
    return 0


def _metadata_columns(columns: Iterable[str]) -> list[str]:
    wanted = {
        "station_region",
        "station_region_type",
        "station_geomorphology",
        "event_region",
        "event_region_type",
        "event_geomorphology",
        "Vs30",
        "geologic_description",
    }
    return [column for column in columns if column in wanted]


if __name__ == "__main__":
    raise SystemExit(main())
