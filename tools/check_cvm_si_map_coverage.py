#!/usr/bin/env python3
"""Report CVM-SI event/station counts for final all-region maps."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from shapely.geometry import Point, shape


METRICS = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/tables/metrics_long.parquet")
GEOJSON = Path("/project2/jvidale_1700/spatial-vtk/runs/inputs/geospatial/regions_no_offshore.geojson")
MODEL = "cvmsi_20260506_material_0p6x1p2_asdf"
TARGET_METRICS = ("arias_duration", "PGA")
PASSBANDS = ("1-2 sec", "2-3 sec", "3-5 sec")
EXCLUDE = {"Imperial Valley Basin", "Northern Transverse Range"}


def load_features(path: Path) -> list[tuple[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    features: list[tuple[str, object]] = []
    for feature in payload.get("features", []):
        props = feature.get("properties") or {}
        name = str(props.get("long_name") or props.get("short_name") or "")
        if not name or name in EXCLUDE:
            continue
        features.append((name, shape(feature["geometry"])))
    return features


def station_region_lookup(df: pd.DataFrame, features: list[tuple[str, object]]) -> dict[str, str]:
    stations = df[["station", "sta_lon", "sta_lat"]].dropna().drop_duplicates("station")
    out: dict[str, str] = {}
    for row in stations.itertuples(index=False):
        point = Point(float(row.sta_lon), float(row.sta_lat))
        for name, geom in features:
            if geom.contains(point) or geom.touches(point):
                out[str(row.station)] = name
                break
    return out


def summarize(df: pd.DataFrame) -> dict[str, object]:
    out: dict[str, object] = {
        "events": int(df["event_id"].nunique()),
        "stations": int(df["station"].nunique()),
        "rows": int(len(df)),
        "by_metric_band": {},
    }
    by_metric_band: dict[str, object] = {}
    for metric in TARGET_METRICS:
        by_metric_band[metric] = {}
        for band in PASSBANDS:
            group = df[df["metric"].astype(str).eq(metric) & df["band"].astype(str).eq(band)]
            by_metric_band[metric][band] = {
                "events": int(group["event_id"].nunique()),
                "stations": int(group["station"].nunique()),
                "rows": int(len(group)),
            }
    out["by_metric_band"] = by_metric_band
    return out


def main() -> int:
    columns = ["event_id", "station", "component", "model", "metric", "band", "log2_residual", "sta_lat", "sta_lon"]
    metrics = pd.read_parquet(METRICS, columns=columns)
    model_df = metrics[metrics["model"].astype(str).eq(MODEL)].copy()
    target_df = model_df[
        model_df["metric"].astype(str).isin(TARGET_METRICS)
        & model_df["band"].astype(str).isin(PASSBANDS)
    ].copy()
    features = load_features(GEOJSON)
    station_regions = station_region_lookup(target_df, features)
    plotted_df = target_df[target_df["station"].astype(str).isin(station_regions)].copy()
    result = {
        "available_models": sorted(metrics["model"].dropna().astype(str).unique()),
        "target_model": MODEL,
        "all_model_metrics": {
            "events": int(model_df["event_id"].nunique()),
            "stations": int(model_df["station"].nunique()),
            "rows": int(len(model_df)),
        },
        "target_metrics_passbands_before_polygon_filter": summarize(target_df),
        "target_metrics_passbands_after_final_polygon_filter": summarize(plotted_df),
        "displayed_polygon_count": len(set(station_regions.values())),
        "excluded_regions": sorted(EXCLUDE),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
