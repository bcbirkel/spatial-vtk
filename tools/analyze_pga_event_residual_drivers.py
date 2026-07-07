#!/usr/bin/env python3
"""Summarize whether basin PGA residuals are event-driven."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import Point, shape


DEFAULT_METRICS = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/tables/metrics_long.parquet")
DEFAULT_GEOJSON = Path("/project2/jvidale_1700/spatial-vtk/runs/inputs/geospatial/regions_updated.geojson")
DEFAULT_OUTPUT_DIR = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/figures/user_requested_basin_metric_maps_pga_fas")
DEFAULT_MODEL = "cvmsi_20260506_material_0p6x1p2_asdf"
PASSBANDS = ("1-2 sec", "2-3 sec", "3-5 sec")
DISPLAY_NAMES = {"San Bernadino Basin": "San Bernardino Basin"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--geojson", type=Path, default=DEFAULT_GEOJSON)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser.parse_args()


def display_region(value: object) -> str:
    text = str(value)
    return DISPLAY_NAMES.get(text, text)


def load_basin_features(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    features: list[dict[str, object]] = []
    for index, feature in enumerate(payload.get("features", [])):
        props = feature.get("properties", {}) or {}
        if str(props.get("region_type") or props.get("mapped_region_type") or "") != "Basin":
            continue
        long_name = str(props.get("long_name") or props.get("name") or props.get("short_name") or f"feature_{index}")
        features.append({"long_name": long_name, "geometry": shape(feature["geometry"])})
    return features


def assign_station_regions(df: pd.DataFrame, features: list[dict[str, object]]) -> pd.DataFrame:
    stations = df[["station", "sta_lon", "sta_lat"]].dropna().drop_duplicates("station")
    records: list[dict[str, object]] = []
    for row in stations.itertuples(index=False):
        point = Point(float(row.sta_lon), float(row.sta_lat))
        match = next((feature for feature in features if feature["geometry"].contains(point) or feature["geometry"].touches(point)), None)
        records.append({"station": row.station, "station_region": None if match is None else match["long_name"]})
    return pd.DataFrame(records)


def summarize_passband(df: pd.DataFrame, passband: str) -> tuple[pd.DataFrame, dict[str, object]]:
    band = df.loc[df["band"].astype(str).eq(passband)].copy()
    values = pd.to_numeric(band["log2_residual"], errors="coerce")
    band = band.loc[np.isfinite(values)].copy()
    band["log2_residual"] = pd.to_numeric(band["log2_residual"], errors="coerce")
    event_summary = (
        band.groupby("event_id", dropna=False)
        .agg(
            event_median=("log2_residual", "median"),
            event_mean=("log2_residual", "mean"),
            row_count=("log2_residual", "size"),
            station_count=("station", "nunique"),
            basin_count=("station_region", "nunique"),
            distance_median_km=("distance_km", "median"),
            magnitude=("Mw", "first"),
            event_lat=("event_lat", "first"),
            event_lon=("event_lon", "first"),
        )
        .reset_index()
    )
    event_summary["passband"] = passband
    overall_median = float(np.nanmedian(band["log2_residual"].to_numpy(dtype=float)))
    weighted_mean_of_event_means = float(np.average(event_summary["event_mean"], weights=event_summary["row_count"]))
    positive_event_fraction = float((event_summary["event_median"] > 0.0).mean()) if len(event_summary) else np.nan
    high_event_fraction = float((event_summary["event_median"] > 0.5).mean()) if len(event_summary) else np.nan
    very_high_event_fraction = float((event_summary["event_median"] > 1.0).mean()) if len(event_summary) else np.nan
    top5 = event_summary.sort_values("event_median", ascending=False).head(5)
    bottom5 = event_summary.sort_values("event_median", ascending=True).head(5)
    stats = {
        "passband": passband,
        "rows": int(len(band)),
        "events": int(event_summary["event_id"].nunique()),
        "stations": int(band["station"].nunique()),
        "overall_row_median": overall_median,
        "weighted_mean_of_event_means": weighted_mean_of_event_means,
        "event_median_min": float(event_summary["event_median"].min()),
        "event_median_q25": float(event_summary["event_median"].quantile(0.25)),
        "event_median_median": float(event_summary["event_median"].median()),
        "event_median_q75": float(event_summary["event_median"].quantile(0.75)),
        "event_median_max": float(event_summary["event_median"].max()),
        "positive_event_fraction": positive_event_fraction,
        "high_event_fraction_gt_0p5": high_event_fraction,
        "very_high_event_fraction_gt_1p0": very_high_event_fraction,
        "top5_events": top5[["event_id", "event_median", "row_count", "station_count", "distance_median_km", "magnitude"]].to_dict("records"),
        "bottom5_events": bottom5[["event_id", "event_median", "row_count", "station_count", "distance_median_km", "magnitude"]].to_dict("records"),
    }
    return event_summary, stats


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    columns = [
        "event_id",
        "station",
        "component",
        "model",
        "metric",
        "band",
        "log2_residual",
        "distance_km",
        "Mw",
        "event_lat",
        "event_lon",
        "sta_lat",
        "sta_lon",
    ]
    df = pd.read_parquet(args.metrics, columns=columns)
    df = df.loc[
        df["model"].astype(str).eq(args.model)
        & df["metric"].astype(str).eq("PGA")
        & df["band"].astype(str).isin(PASSBANDS)
    ].copy()
    df["distance_km"] = pd.to_numeric(df["distance_km"], errors="coerce")
    features = load_basin_features(args.geojson)
    station_regions = assign_station_regions(df, features)
    df = df.merge(station_regions, on="station", how="left")
    df = df.loc[df["station_region"].notna()].copy()
    df["station_region_display"] = df["station_region"].map(display_region)

    event_tables: list[pd.DataFrame] = []
    stats_rows: list[dict[str, object]] = []
    for passband in PASSBANDS:
        event_summary, stats = summarize_passband(df, passband)
        event_tables.append(event_summary)
        stats_rows.append(stats)

    event_out = args.output_dir / "pga_basin_event_residual_summary.csv"
    pd.concat(event_tables, ignore_index=True).to_csv(event_out, index=False)
    stats_out = args.output_dir / "pga_basin_event_driver_summary.json"
    stats_out.write_text(json.dumps(stats_rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(stats_rows, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
