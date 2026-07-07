#!/usr/bin/env python3
"""Analyze CVM-SI regional, path, and period-dependent residual patterns.

The workflow focuses on PGA and Arias duration log2 residuals, builds
physically meaningful event-station path features from the region GeoJSON, and
writes summary tables, paired period-dependence tests, and diagnostic figures.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely.geometry import LineString, Point, box, shape
from shapely.ops import transform as shapely_transform

try:
    from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
except Exception:  # pragma: no cover - optional plotting dependency path
    add_contextily_basemap = None


DEFAULT_METRICS = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/tables/metrics_final_enriched.parquet")
DEFAULT_REGIONS = Path("/project2/jvidale_1700/spatial-vtk/runs/inputs/geospatial/regions_updated.geojson")
DEFAULT_OUTPUT_DIR = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/analysis/cvmsi_region_path_period_dependence")
DEFAULT_MODEL = "cvmsi_20260506_material_0p6x1p2_asdf"
METRICS = ("PGA", "arias_duration")
BANDS = ("1-2 sec", "2-3 sec", "3-5 sec")
BAND_PAIRS = (("3-5 sec", "1-2 sec"), ("2-3 sec", "1-2 sec"), ("3-5 sec", "2-3 sec"))
LA_BASIN = "Los Angeles Basin"
REGION_TYPE_ORDER = ("Basin", "Valley", "Hills", "Mountains", "Other", "Offshore", "outside", "unknown")
DIRECTION_BINS = tuple(range(0, 361, 45))
LA_BASIN_ENTRY_SEGMENT_M = 50.0
LOWESS_BOUNDARY_FRACS = (0.08, 0.4, 0.2, 0.1, 0.05, 0.01)
FIXED_SCALING_H_KM = 10.0
FIXED_SCALING_DISTANCE_POWER = 1.0
FIXED_SCALING_MAGNITUDE_B = 0.5
BOUNDARY_CONFIDENCE_BOOTSTRAPS = 30
SUPPORT_LINEWIDTH_MIN = 1.5
SUPPORT_LINEWIDTH_MAX = 8.5
BOOTSTRAP_SAMPLES = 500
PERMUTATION_SAMPLES = 2000
RANDOM_SEED = 20260629
MIN_SUPPORT_EVENTS = 5
MIN_SUPPORT_STATIONS = 8
MIN_SUPPORT_PAIRS = 30

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#687083",
    "grid": "#E6E8F0",
    "axis": "#D5D9E5",
    "blue": "#4C78A8",
    "gold": "#F2B701",
    "orange": "#E4572E",
    "olive": "#59A14F",
    "pink": "#B279A2",
    "purple": "#79706E",
}
REGION_TYPE_COLORS = {
    "Basin": "#4C78A8",
    "Valley": "#59A14F",
    "Hills": "#F2B701",
    "Mountains": "#E4572E",
    "Other": "#9CA3AF",
    "Offshore": "#76B7B2",
    "outside": "#D1D5DB",
    "unknown": "#D1D5DB",
}


@dataclass(frozen=True)
class RegionFeature:
    index: int
    long_name: str
    short_name: str
    region_type: str
    geometry: object
    geometry_projected: object


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        run_self_test()
        return 0

    output_dir = args.output_dir.expanduser()
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    use_chart_theme()

    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3310", always_xy=True)
    regions = load_regions(args.regions_geojson, transformer=transformer)
    source = load_selected_metrics(args.metrics, model=args.model)
    path_features = build_path_features(source, regions=regions, transformer=transformer)
    path_features_path = tables_dir / "cvmsi_pga_arias_path_features.parquet"
    path_features.to_parquet(path_features_path, index=False)

    pair_band = aggregate_event_station_metric_band(source).merge(
        path_features,
        on=["event_id", "station"],
        how="left",
        suffixes=("", "_path"),
    )
    pair_band = add_analysis_bins(pair_band)
    region_summary = summarize_groups(
        pair_band,
        ["metric", "band", "station_region_type", "station_region"],
        family="station_region",
    )
    path_summary = summarize_groups(
        pair_band,
        ["metric", "band", "event_region_type", "event_region", "station_region_type", "station_region"],
        family="event_to_station_region",
    )
    la_summary = build_la_basin_summaries(pair_band)
    tests = build_period_dependence_tests(pair_band)

    region_summary.to_csv(tables_dir / "cvmsi_region_period_summary.csv", index=False)
    path_summary.to_csv(tables_dir / "cvmsi_path_period_summary.csv", index=False)
    la_summary.to_csv(tables_dir / "cvmsi_la_basin_local_vs_regional_summary.csv", index=False)
    tests.to_csv(tables_dir / "cvmsi_la_basin_period_dependence_tests.csv", index=False)

    figure_paths = write_figures(
        pair_band=pair_band,
        region_summary=region_summary,
        path_summary=path_summary,
        la_summary=la_summary,
        tests=tests,
        regions=regions,
        figures_dir=figures_dir,
    )
    manifest = {
        "metrics": str(args.metrics),
        "regions_geojson": str(args.regions_geojson),
        "model": args.model,
        "output_dir": str(output_dir),
        "rows_loaded": int(len(source)),
        "event_station_metric_band_rows": int(len(pair_band)),
        "event_station_path_rows": int(len(path_features)),
        "tables": {
            "path_features": str(path_features_path),
            "region_period_summary": str(tables_dir / "cvmsi_region_period_summary.csv"),
            "path_period_summary": str(tables_dir / "cvmsi_path_period_summary.csv"),
            "la_basin_local_vs_regional_summary": str(tables_dir / "cvmsi_la_basin_local_vs_regional_summary.csv"),
            "la_basin_period_dependence_tests": str(tables_dir / "cvmsi_la_basin_period_dependence_tests.csv"),
        },
        "figures": [str(path) for path in figure_paths],
        "support_thresholds": {
            "min_events": MIN_SUPPORT_EVENTS,
            "min_stations": MIN_SUPPORT_STATIONS,
            "min_event_station_pairs": MIN_SUPPORT_PAIRS,
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--regions-geojson", type=Path, default=DEFAULT_REGIONS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--self-test", action="store_true", help="Run path-classification self-tests and exit.")
    return parser.parse_args(argv)


def use_chart_theme() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": TOKENS["surface"],
            "savefig.facecolor": TOKENS["surface"],
            "axes.facecolor": TOKENS["panel"],
            "axes.edgecolor": TOKENS["axis"],
            "axes.labelcolor": TOKENS["ink"],
            "axes.grid": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.family": "sans-serif",
            "font.sans-serif": ["Aptos", "Inter", "Segoe UI", "DejaVu Sans", "Arial", "sans-serif"],
            "xtick.color": TOKENS["muted"],
            "ytick.color": TOKENS["muted"],
        }
    )


def load_selected_metrics(path: Path, *, model: str) -> pd.DataFrame:
    columns = [
        "event_id",
        "station",
        "component",
        "model",
        "metric",
        "band",
        "passband",
        "value_obs",
        "value_syn",
        "log2_residual",
        "event_lat",
        "event_lon",
        "sta_lat",
        "sta_lon",
        "distance_km",
        "azimuth_deg",
        "backazimuth_deg",
        "event_region",
        "event_region_type",
        "event_geomorphology",
        "station_region",
        "station_region_type",
        "station_geomorphology",
        "Vs30",
        "geologic_description",
        "strike",
        "dip",
        "rake",
        "magnitude",
        "event_depth_km",
        "depth",
    ]
    import pyarrow.parquet as pq

    available = pq.ParquetFile(path).schema.names
    selected_columns = [column for column in columns if column in available]
    df = pd.read_parquet(path, columns=selected_columns)
    df = df.loc[
        df["model"].astype(str).eq(str(model))
        & df["metric"].isin(METRICS)
        & df["band"].isin(BANDS)
        & np.isfinite(pd.to_numeric(df["log2_residual"], errors="coerce"))
        & df[["event_lat", "event_lon", "sta_lat", "sta_lon"]].notna().all(axis=1)
    ].copy()
    df["log2_residual"] = pd.to_numeric(df["log2_residual"], errors="coerce")
    df["station"] = df["station"].astype(str)
    df["event_id"] = df["event_id"].astype(str)
    df["band"] = pd.Categorical(df["band"], categories=BANDS, ordered=True)
    df["fault_type"] = df["rake"].map(fault_type_from_rake) if "rake" in df.columns else "unknown"
    if "event_depth_km" not in df.columns and "depth" in df.columns:
        df["event_depth_km"] = df["depth"]
    return df.reset_index(drop=True)


def load_regions(path: Path, *, transformer: Transformer) -> list[RegionFeature]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    features: list[RegionFeature] = []
    for index, feature in enumerate(payload.get("features", [])):
        props = feature.get("properties") or {}
        geom_payload = feature.get("geometry")
        if not geom_payload:
            continue
        geom = shape(geom_payload)
        long_name = str(props.get("long_name") or props.get("region_name") or props.get("name") or props.get("short_name") or f"region_{index}")
        region_type = str(props.get("region_type") or props.get("mapped_region_type") or "Other")
        features.append(
            RegionFeature(
                index=index,
                long_name=long_name,
                short_name=str(props.get("short_name") or long_name),
                region_type=region_type,
                geometry=geom,
                geometry_projected=project_geometry(geom, transformer),
            )
        )
    if not features:
        raise ValueError(f"No GeoJSON polygon features found in {path}")
    return features


def project_geometry(geom: object, transformer: Transformer) -> object:
    return shapely_transform(transformer.transform, geom)


def build_path_features(df: pd.DataFrame, *, regions: Sequence[RegionFeature], transformer: Transformer) -> pd.DataFrame:
    base_cols = [
        "event_id",
        "station",
        "event_lon",
        "event_lat",
        "sta_lon",
        "sta_lat",
        "distance_km",
        "azimuth_deg",
        "backazimuth_deg",
        "event_region",
        "event_region_type",
        "event_geomorphology",
        "station_region",
        "station_region_type",
        "station_geomorphology",
        "Vs30",
        "geologic_description",
        "fault_type",
        "strike",
        "dip",
        "rake",
        "magnitude",
        "event_depth_km",
    ]
    rows = df[[column for column in base_cols if column in df.columns]].drop_duplicates(["event_id", "station"]).copy()
    records: list[dict[str, object]] = []
    la_feature = first_region(regions, LA_BASIN)
    for row in rows.itertuples(index=False):
        event_lon = float(getattr(row, "event_lon"))
        event_lat = float(getattr(row, "event_lat"))
        sta_lon = float(getattr(row, "sta_lon"))
        sta_lat = float(getattr(row, "sta_lat"))
        line = LineString([(event_lon, event_lat), (sta_lon, sta_lat)])
        line_projected = project_geometry(line, transformer)
        total_length_km = float(line_projected.length / 1000.0)
        rec = {column: getattr(row, column) for column in rows.columns}
        rec["path_length_km_projected"] = total_length_km
        rec["distance_bin"] = distance_bin(getattr(row, "distance_km", np.nan))
        rec["azimuth_bin"] = direction_bin(getattr(row, "azimuth_deg", np.nan))
        rec["backazimuth_bin"] = direction_bin(getattr(row, "backazimuth_deg", np.nan))
        intersected: list[str] = []
        region_lengths: dict[str, float] = {}
        for region in regions:
            length_km = intersection_length_km(line_projected, region.geometry_projected)
            if length_km > 1e-6:
                intersected.append(region.long_name)
            slug = slugify(region.long_name)
            rec[f"path_length_{slug}_km"] = length_km
            rec[f"path_fraction_{slug}"] = safe_divide(length_km, total_length_km)
            region_lengths[region.long_name] = length_km
        rec["path_regions_intersected"] = ";".join(intersected)
        rec["path_region_count"] = len(intersected)
        if la_feature is not None:
            add_la_basin_features(rec, la_feature=la_feature, line_projected=line_projected, total_length_km=total_length_km)
        records.append(rec)
    features = pd.DataFrame.from_records(records)
    for threshold in (2.5, 5.0, 10.0):
        features[f"la_basin_station_position_{threshold:g}km"] = features.apply(
            lambda row: la_basin_station_position(row, la_feature=la_feature, transformer=transformer, threshold_km=threshold),
            axis=1,
        )
    return features


def add_la_basin_features(rec: dict[str, object], *, la_feature: RegionFeature, line_projected: object, total_length_km: float) -> None:
    event_point = Point(float(rec["event_lon"]), float(rec["event_lat"]))
    station_point = Point(float(rec["sta_lon"]), float(rec["sta_lat"]))
    event_inside = bool(la_feature.geometry.covers(event_point))
    station_inside = bool(la_feature.geometry.covers(station_point))
    path_length_km = intersection_length_km(line_projected, la_feature.geometry_projected)
    crosses = bool(line_projected.crosses(la_feature.geometry_projected.boundary) or line_projected.intersects(la_feature.geometry_projected.boundary))
    rec["event_inside_LA_Basin"] = event_inside
    rec["station_inside_LA_Basin"] = station_inside
    rec["path_crosses_LA_Basin_boundary"] = crosses
    rec["path_length_in_LA_Basin_km"] = path_length_km
    rec["path_fraction_in_LA_Basin"] = safe_divide(path_length_km, total_length_km)
    rec["la_basin_path_class"] = path_class(event_inside=event_inside, station_inside=station_inside, path_length_km=path_length_km)
    rec["la_basin_inbound_backazimuth_bin"] = direction_bin(rec.get("backazimuth_deg"))
    rec["la_basin_path_length_bin"] = la_path_length_bin(path_length_km)


def first_region(regions: Sequence[RegionFeature], name: str) -> RegionFeature | None:
    for region in regions:
        if region.long_name == name:
            return region
    return None


def intersection_length_km(line_projected: object, polygon_projected: object) -> float:
    inter = line_projected.intersection(polygon_projected)
    if inter.is_empty:
        return 0.0
    return float(inter.length / 1000.0)


def path_class(*, event_inside: bool, station_inside: bool, path_length_km: float) -> str:
    if event_inside and station_inside:
        return "local_basin"
    if station_inside and not event_inside:
        return "regional_inbound"
    if event_inside and not station_inside:
        return "regional_outbound"
    if path_length_km > 0.0:
        return "through_basin"
    return "outside_basin"


def la_basin_station_position(
    row: pd.Series,
    *,
    la_feature: RegionFeature | None,
    transformer: Transformer,
    threshold_km: float,
) -> str:
    if la_feature is None or pd.isna(row.get("sta_lon")) or pd.isna(row.get("sta_lat")):
        return "unknown"
    point = Point(float(row["sta_lon"]), float(row["sta_lat"]))
    projected_point = project_geometry(point, transformer)
    distance_km = float(projected_point.distance(la_feature.geometry_projected.boundary) / 1000.0)
    inside = bool(la_feature.geometry.covers(point))
    if inside and distance_km > threshold_km:
        return "basin_interior"
    if inside:
        return "basin_edge_inside"
    if distance_km <= threshold_km:
        return "basin_edge_outside"
    return "non_basin"


def aggregate_event_station_metric_band(df: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["event_id", "station", "metric", "band"]
    extra_cols = ["component"]
    grouped = (
        df.groupby(group_cols, dropna=False, observed=True)
        .agg(
            log2_residual=("log2_residual", "median"),
            value_obs=("value_obs", "median") if "value_obs" in df.columns else ("log2_residual", "size"),
            value_syn=("value_syn", "median") if "value_syn" in df.columns else ("log2_residual", "size"),
            mean_component_log2_residual=("log2_residual", "mean"),
            n_rows=("log2_residual", "size"),
            n_components=("component", "nunique") if "component" in df.columns else ("log2_residual", "size"),
        )
        .reset_index()
    )
    return grouped


def add_analysis_bins(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["distance_quantile_bin"] = quantile_bin(out["distance_km"], bins=5, prefix="distance_q")
    out["Vs30_bin"] = quantile_bin(out["Vs30"], bins=4, prefix="Vs30_q") if "Vs30" in out.columns else "unknown"
    out["la_path_fraction_bin"] = quantile_bin(out["path_fraction_in_LA_Basin"], bins=4, prefix="la_fraction_q")
    out["la_path_length_quantile_bin"] = quantile_bin(out["path_length_in_LA_Basin_km"], bins=4, prefix="la_length_q")
    return out


def summarize_groups(df: pd.DataFrame, group_cols: list[str], *, family: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for key, group in df.groupby(group_cols, dropna=False, observed=True, sort=False):
        key_values = key if isinstance(key, tuple) else (key,)
        values = pd.to_numeric(group["log2_residual"], errors="coerce").dropna().to_numpy()
        stats = summary_stats(values)
        rec = {"analysis_family": family}
        rec.update(dict(zip(group_cols, key_values)))
        rec.update(stats)
        rec.update(support_counts(group))
        rec["meets_support"] = meets_support(rec)
        rows.append(rec)
    return pd.DataFrame(rows).sort_values(group_cols).reset_index(drop=True)


def build_la_basin_summaries(pair_band: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    specs = [
        ("la_basin_path_class", ["metric", "band", "la_basin_path_class"]),
        ("la_basin_path_class_by_direction", ["metric", "band", "la_basin_path_class", "la_basin_inbound_backazimuth_bin"]),
        ("la_basin_path_length", ["metric", "band", "la_basin_path_class", "la_path_length_quantile_bin"]),
        ("la_basin_station_position_5km", ["metric", "band", "la_basin_station_position_5km"]),
        ("la_basin_Vs30", ["metric", "band", "la_basin_path_class", "Vs30_bin"]),
        ("la_basin_geologic_description", ["metric", "band", "la_basin_path_class", "geologic_description"]),
    ]
    basin_related = pair_band.loc[
        pair_band["la_basin_path_class"].isin(["local_basin", "regional_inbound", "regional_outbound", "through_basin"])
        | pair_band["station_inside_LA_Basin"].fillna(False)
    ].copy()
    for family, cols in specs:
        valid_cols = [column for column in cols if column in basin_related.columns]
        frames.append(summarize_groups(basin_related, valid_cols, family=family))
    return pd.concat(frames, ignore_index=True, sort=False)


def build_period_dependence_tests(pair_band: pd.DataFrame) -> pd.DataFrame:
    paired = paired_band_differences(pair_band)
    specs = [
        ("global", ["metric", "band_pair"]),
        ("station_region", ["metric", "band_pair", "station_region_type", "station_region"]),
        ("event_to_station_region", ["metric", "band_pair", "event_region_type", "event_region", "station_region_type", "station_region"]),
        ("la_basin_path_class", ["metric", "band_pair", "la_basin_path_class"]),
        ("la_basin_path_class_by_direction", ["metric", "band_pair", "la_basin_path_class", "la_basin_inbound_backazimuth_bin"]),
        ("la_basin_regional_inbound_direction", ["metric", "band_pair", "la_basin_inbound_backazimuth_bin"]),
        ("la_basin_path_length", ["metric", "band_pair", "la_basin_path_class", "la_path_length_quantile_bin"]),
        ("la_basin_station_position_5km", ["metric", "band_pair", "la_basin_station_position_5km"]),
        ("la_basin_Vs30", ["metric", "band_pair", "la_basin_path_class", "Vs30_bin"]),
        ("la_basin_geologic_description", ["metric", "band_pair", "la_basin_path_class", "geologic_description"]),
    ]
    frames = []
    for family, group_cols in specs:
        work = paired.copy()
        if family.startswith("la_basin"):
            work = work.loc[
                work["la_basin_path_class"].isin(["local_basin", "regional_inbound", "regional_outbound", "through_basin"])
                | work["station_inside_LA_Basin"].fillna(False)
            ].copy()
        if family == "la_basin_regional_inbound_direction":
            work = work.loc[work["la_basin_path_class"].eq("regional_inbound")].copy()
        frames.append(test_groups(work, group_cols, family=family))
    tests = pd.concat(frames, ignore_index=True, sort=False)
    tests["q_value"] = tests.groupby("analysis_family", group_keys=False)["p_value"].transform(benjamini_hochberg)
    tests["statistically_supported"] = (
        tests["meets_support"].fillna(False)
        & tests["q_value"].le(0.05)
        & tests["median_band_difference"].abs().ge(0.20)
    )
    return tests


def paired_band_differences(pair_band: pd.DataFrame) -> pd.DataFrame:
    id_cols = ["event_id", "station", "metric"]
    pivot = pair_band.pivot_table(index=id_cols, columns="band", values="log2_residual", aggfunc="median", observed=True).reset_index()
    metadata_cols = [column for column in pair_band.columns if column not in {"band", "log2_residual", "mean_component_log2_residual", "n_rows", "n_components"}]
    meta = pair_band[metadata_cols].drop_duplicates(id_cols)
    rows: list[pd.DataFrame] = []
    for high, low in BAND_PAIRS:
        if high not in pivot.columns or low not in pivot.columns:
            continue
        piece = pivot[id_cols].copy()
        piece["band_pair"] = f"{high}_minus_{low}"
        piece["band_high"] = high
        piece["band_low"] = low
        piece["band_difference"] = pd.to_numeric(pivot[high], errors="coerce") - pd.to_numeric(pivot[low], errors="coerce")
        piece = piece.loc[np.isfinite(piece["band_difference"])].copy()
        rows.append(piece)
    paired = pd.concat(rows, ignore_index=True, sort=False) if rows else pd.DataFrame()
    if paired.empty:
        return paired
    return paired.merge(meta, on=id_cols, how="left")


def test_groups(df: pd.DataFrame, group_cols: list[str], *, family: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if df.empty:
        return pd.DataFrame()
    for key, group in df.groupby(group_cols, dropna=False, observed=True, sort=False):
        key_values = key if isinstance(key, tuple) else (key,)
        values = pd.to_numeric(group["band_difference"], errors="coerce").dropna().to_numpy()
        rec = {"analysis_family": family}
        rec.update(dict(zip(group_cols, key_values)))
        rec["n_pairs_with_band_difference"] = int(len(values))
        rec["median_band_difference"] = float(np.median(values)) if len(values) else math.nan
        ci_low, ci_high = bootstrap_ci(values)
        rec["bootstrap_ci_low"] = ci_low
        rec["bootstrap_ci_high"] = ci_high
        rec["p_value"] = sign_flip_p_value(values)
        rec.update(support_counts(group))
        rec["meets_support"] = meets_support(rec)
        rows.append(rec)
    return pd.DataFrame(rows)


def summary_stats(values: np.ndarray) -> dict[str, float | int]:
    clean = values[np.isfinite(values)]
    ci_low, ci_high = bootstrap_ci(clean)
    return {
        "n_values": int(len(clean)),
        "median_log2_residual": float(np.median(clean)) if len(clean) else math.nan,
        "mean_log2_residual": float(np.mean(clean)) if len(clean) else math.nan,
        "q1_log2_residual": float(np.quantile(clean, 0.25)) if len(clean) else math.nan,
        "q3_log2_residual": float(np.quantile(clean, 0.75)) if len(clean) else math.nan,
        "bootstrap_ci_low": ci_low,
        "bootstrap_ci_high": ci_high,
        "fraction_positive": float(np.mean(clean > 0.0)) if len(clean) else math.nan,
        "fraction_negative": float(np.mean(clean < 0.0)) if len(clean) else math.nan,
    }


def support_counts(group: pd.DataFrame) -> dict[str, int]:
    return {
        "n_event_station_pairs": int(group[["event_id", "station"]].drop_duplicates().shape[0]) if {"event_id", "station"}.issubset(group.columns) else int(len(group)),
        "n_events": int(group["event_id"].nunique(dropna=True)) if "event_id" in group.columns else 0,
        "n_stations": int(group["station"].nunique(dropna=True)) if "station" in group.columns else 0,
        "n_rows": int(group["n_rows"].sum()) if "n_rows" in group.columns else int(len(group)),
    }


def meets_support(row: dict[str, object] | pd.Series) -> bool:
    return (
        int(row.get("n_events", 0)) >= MIN_SUPPORT_EVENTS
        and int(row.get("n_stations", 0)) >= MIN_SUPPORT_STATIONS
        and int(row.get("n_event_station_pairs", 0)) >= MIN_SUPPORT_PAIRS
    )


def bootstrap_ci(values: np.ndarray, *, samples: int = BOOTSTRAP_SAMPLES) -> tuple[float, float]:
    clean = values[np.isfinite(values)]
    if len(clean) < 2:
        return (math.nan, math.nan)
    rng = np.random.default_rng(RANDOM_SEED + len(clean))
    draws = rng.choice(clean, size=(samples, len(clean)), replace=True)
    medians = np.median(draws, axis=1)
    return (float(np.quantile(medians, 0.025)), float(np.quantile(medians, 0.975)))


def sign_flip_p_value(values: np.ndarray, *, samples: int = PERMUTATION_SAMPLES) -> float:
    clean = values[np.isfinite(values)]
    if len(clean) < 5:
        return math.nan
    observed = abs(float(np.median(clean)))
    rng = np.random.default_rng(RANDOM_SEED + 17 * len(clean))
    signs = rng.choice(np.array([-1.0, 1.0]), size=(samples, len(clean)), replace=True)
    medians = np.abs(np.median(signs * clean, axis=1))
    return float((np.sum(medians >= observed) + 1.0) / (samples + 1.0))


def benjamini_hochberg(series: pd.Series) -> pd.Series:
    p = pd.to_numeric(series, errors="coerce")
    out = pd.Series(np.nan, index=series.index, dtype=float)
    valid = p.dropna().sort_values()
    if valid.empty:
        return out
    m = len(valid)
    adjusted = valid.to_numpy() * m / np.arange(1, m + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    out.loc[valid.index] = np.clip(adjusted, 0.0, 1.0)
    return out


def write_figures(
    *,
    pair_band: pd.DataFrame,
    region_summary: pd.DataFrame,
    path_summary: pd.DataFrame,
    la_summary: pd.DataFrame,
    tests: pd.DataFrame,
    regions: Sequence[RegionFeature],
    figures_dir: Path,
) -> list[Path]:
    paths: list[Path] = []
    paths.extend(plot_station_region_heatmaps(region_summary, figures_dir))
    paths.extend(plot_path_heatmaps(path_summary, figures_dir))
    paths.append(plot_la_basin_path_class_boxplots(pair_band, figures_dir))
    paths.append(plot_la_basin_inbound_direction_tests(tests, figures_dir))
    paths.extend(plot_la_basin_regional_inbound_pga_direction_maps(pair_band, regions, figures_dir))
    paths.append(plot_la_basin_path_length(pair_band, figures_dir))
    paths.append(plot_la_basin_vs30(pair_band, figures_dir))
    paths.append(plot_la_basin_geology(pair_band, figures_dir))
    paths.append(plot_strongest_path_period_map(tests, pair_band, regions, figures_dir))
    return [path for path in paths if path is not None and path.exists()]


def plot_station_region_heatmaps(summary: pd.DataFrame, output_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for metric in METRICS:
        data = summary.loc[(summary["metric"].astype(str) == metric) & summary["meets_support"].fillna(False)].copy()
        data = data.loc[defined_region_mask(data["station_region"]) & defined_region_mask(data["station_region_type"])].copy()
        if data.empty:
            continue
        order = region_order(data, "station_region_type", "station_region")
        pivot = data.pivot_table(index="station_region", columns="band", values="median_log2_residual", aggfunc="first", observed=True)
        pivot = pivot.reindex(index=order, columns=list(BANDS))
        fig, ax = plt.subplots(figsize=(8.5, max(6.0, 0.34 * len(pivot) + 2.0)), dpi=180)
        image = ax.imshow(pivot.to_numpy(dtype=float), aspect="auto", cmap="RdBu_r", vmin=-1.0, vmax=1.0)
        ax.set_xticks(np.arange(len(pivot.columns)), labels=pivot.columns)
        ax.set_yticks(np.arange(len(pivot.index)), labels=pivot.index)
        ax.tick_params(axis="y", labelsize=7)
        ax.set_xlabel("Band")
        ax.set_ylabel("Station region, grouped by type")
        add_region_type_separators(ax, data, order)
        add_header(fig, ax, f"{metric}: CVM-SI residuals by station region and period", "Median log2(observed / synthetic); regions are grouped by station region type; support thresholds applied.")
        fig.colorbar(image, ax=ax, label="median log2 residual", shrink=0.75)
        path = output_dir / f"station_region_period_heatmap__{slugify(metric)}.png"
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        paths.append(path)
    return paths


def plot_path_heatmaps(summary: pd.DataFrame, output_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for metric in METRICS:
        for band in BANDS:
            data = summary.loc[
                (summary["metric"].astype(str) == metric)
                & (summary["band"].astype(str) == band)
                & summary["meets_support"].fillna(False)
            ].copy()
            data = data.loc[
                defined_region_mask(data["station_region"])
                & defined_region_mask(data["station_region_type"])
                & defined_region_mask(data["event_region"])
            ].copy()
            if data.empty:
                continue
            top_station = (
                data.groupby(["station_region_type", "station_region"], dropna=False)["n_event_station_pairs"]
                .sum()
                .reset_index()
                .sort_values(["station_region_type", "n_event_station_pairs"], ascending=[True, False])
                .head(18)
            )
            station_order = region_order(top_station, "station_region_type", "station_region")
            event_order = data.groupby("event_region")["n_event_station_pairs"].sum().sort_values(ascending=False).head(18).index.tolist()
            work = data.loc[data["station_region"].isin(station_order) & data["event_region"].isin(event_order)].copy()
            pivot = work.pivot_table(index="event_region", columns="station_region", values="median_log2_residual", aggfunc="first")
            pivot = pivot.reindex(index=event_order, columns=station_order)
            fig, ax = plt.subplots(figsize=(12.0, max(6.0, 0.36 * len(event_order) + 2.0)), dpi=180)
            image = ax.imshow(pivot.to_numpy(dtype=float), aspect="auto", cmap="RdBu_r", vmin=-1.0, vmax=1.0)
            ax.set_xticks(np.arange(len(pivot.columns)), labels=pivot.columns, rotation=55, ha="right", fontsize=7)
            ax.set_yticks(np.arange(len(pivot.index)), labels=pivot.index, fontsize=7)
            ax.set_xlabel("Station region, grouped by type")
            ax.set_ylabel("Event region")
            add_header(fig, ax, f"{metric} {band}: event-region to station-region residuals", "Median log2(observed / synthetic); top supported paths shown; station regions grouped by type.")
            fig.colorbar(image, ax=ax, label="median log2 residual", shrink=0.74)
            path = output_dir / f"path_period_heatmap__{slugify(metric)}__{slugify(band)}.png"
            fig.savefig(path, bbox_inches="tight")
            plt.close(fig)
            paths.append(path)
    return paths


def plot_la_basin_path_class_boxplots(pair_band: pd.DataFrame, output_dir: Path) -> Path:
    data = pair_band.loc[pair_band["la_basin_path_class"].isin(["local_basin", "regional_inbound", "regional_outbound", "through_basin"])].copy()
    data["class_band"] = data["la_basin_path_class"].astype(str) + "\n" + data["band"].astype(str)
    classes = ["local_basin", "regional_inbound", "regional_outbound", "through_basin"]
    labels = [f"{klass}\n{band}" for klass in classes for band in BANDS]
    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5), dpi=180, sharey=True)
    for ax, metric in zip(axes, METRICS):
        metric_df = data.loc[data["metric"].astype(str) == metric].copy()
        arrays = [
            metric_df.loc[(metric_df["la_basin_path_class"] == klass) & (metric_df["band"].astype(str) == band), "log2_residual"].dropna().to_numpy()
            for klass in classes
            for band in BANDS
        ]
        box = ax.boxplot(arrays, tick_labels=labels, showfliers=False, patch_artist=True)
        for patch, label in zip(box["boxes"], labels):
            patch.set_facecolor(TOKENS["blue"] if "regional_inbound" in label else "#DCE3F1")
            patch.set_edgecolor("#344054")
        ax.axhline(0, color="#344054", linewidth=1)
        ax.set_title(metric)
        ax.tick_params(axis="x", labelrotation=55, labelsize=7)
        ax.grid(axis="y", color=TOKENS["grid"], linewidth=0.8)
    axes[0].set_ylabel("log2(observed / synthetic)")
    add_header(fig, axes[0], "LA Basin local vs regional path classes", "CVM-SI residual distributions by path class and period; regional inbound paths are highlighted.")
    path = output_dir / "la_basin_local_vs_regional_boxplots.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_la_basin_inbound_direction_tests(tests: pd.DataFrame, output_dir: Path) -> Path:
    data = tests.loc[
        (tests["analysis_family"] == "la_basin_regional_inbound_direction")
        & (tests["band_pair"] == "3-5 sec_minus_1-2 sec")
    ].copy()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), dpi=180, sharey=True)
    for ax, metric in zip(axes, METRICS):
        work = data.loc[data["metric"].astype(str) == metric].copy()
        work = work.sort_values("la_basin_inbound_backazimuth_bin")
        colors = np.where(work["statistically_supported"].fillna(False), TOKENS["orange"], TOKENS["blue"])
        ax.bar(work["la_basin_inbound_backazimuth_bin"].astype(str), work["median_band_difference"], color=colors)
        ax.axhline(0, color="#344054", linewidth=1)
        ax.set_title(metric)
        ax.set_xlabel("Backazimuth bin")
        ax.tick_params(axis="x", labelrotation=45)
        ax.grid(axis="y", color=TOKENS["grid"], linewidth=0.8)
    axes[0].set_ylabel("Median 3-5 sec minus 1-2 sec log2 residual")
    add_header(fig, axes[0], "LA Basin regional-inbound period dependence by direction", "Orange bars meet support, FDR, and effect-size thresholds; all directions retain support counts in the CSV.")
    path = output_dir / "la_basin_inbound_direction_period_difference.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_la_basin_regional_inbound_pga_direction_maps(
    pair_band: pd.DataFrame,
    regions: Sequence[RegionFeature],
    output_dir: Path,
) -> list[Path]:
    la_feature = first_region(regions, LA_BASIN)
    if la_feature is None:
        return []
    band_data = pair_band.loc[
        pair_band["metric"].astype(str).eq("PGA")
        & pair_band["la_basin_path_class"].eq("regional_inbound")
        & pair_band["station_inside_LA_Basin"].fillna(False)
    ].copy()
    if band_data.empty:
        return []
    band_data = add_la_basin_entry_points(band_data, la_feature)
    band_data = add_mag_distance_corrected_pga_values(band_data)
    difference_data = paired_band_differences(pair_band)
    difference_data = difference_data.loc[
        difference_data["metric"].astype(str).eq("PGA")
        & difference_data["la_basin_path_class"].eq("regional_inbound")
        & difference_data["station_inside_LA_Basin"].fillna(False)
    ].copy()
    difference_data = add_la_basin_entry_points(difference_data, la_feature)
    paths: list[Path] = []
    paths.append(
        plot_regional_inbound_path_map(
            band_data,
            regions,
            la_feature,
            panel_col="band",
            panel_order=list(BANDS),
            value_col="log2_residual",
            title="LA Basin regional-inbound PGA residuals by incoming direction",
            subtitle="Each line is one event-station path with station inside the LA Basin and event outside; color is median component log2(observed / synthetic).",
            colorbar_label="PGA log2 residual",
            colorbar_stem="Residual",
            output_path=output_dir / "la_basin_regional_inbound_pga_path_map_band_residuals.png",
        )
    )
    paths.append(
        plot_regional_inbound_boundary_entry_map(
            band_data,
            regions,
            la_feature,
            panel_col="band",
            panel_order=list(BANDS),
            value_col="log2_residual",
            title="LA Basin PGA residuals at basin-entry sectors",
            subtitle="LA Basin boundary is split into 50 m segments; colored segments show the mean residual for regional-inbound paths entering through each segment.",
            colorbar_label="PGA log2 residual",
            colorbar_stem="Residual",
            output_path=output_dir / "la_basin_regional_inbound_pga_boundary_entry_band_residuals.png",
        )
    )
    paths.extend(plot_lowess_corrected_pga_boundary_maps(band_data, regions, la_feature, output_dir))
    if not difference_data.empty:
        diff_order = [f"{high}_minus_{low}" for high, low in BAND_PAIRS]
        paths.append(
            plot_regional_inbound_path_map(
                difference_data,
                regions,
                la_feature,
                panel_col="band_pair",
                panel_order=diff_order,
                value_col="band_difference",
                title="LA Basin regional-inbound PGA period-difference paths",
                subtitle="Each line is one paired event-station path; color is high-period minus low-period log2 residual for the same event-station pair.",
                colorbar_label="PGA paired log2-residual difference",
                colorbar_stem="Difference",
                output_path=output_dir / "la_basin_regional_inbound_pga_path_map_period_differences.png",
            )
        )
        paths.append(
            plot_regional_inbound_boundary_entry_map(
                difference_data,
                regions,
                la_feature,
                panel_col="band_pair",
                panel_order=diff_order,
                value_col="band_difference",
                title="LA Basin PGA period differences at basin-entry sectors",
                subtitle="LA Basin boundary is split into 50 m segments; colored segments show the mean paired difference for regional-inbound paths entering through each segment.",
                colorbar_label="PGA paired log2-residual difference",
                colorbar_stem="Difference",
                output_path=output_dir / "la_basin_regional_inbound_pga_boundary_entry_period_differences.png",
            )
        )
    return [path for path in paths if path is not None and path.exists()]


def plot_regional_inbound_path_map(
    data: pd.DataFrame,
    regions: Sequence[RegionFeature],
    la_feature: RegionFeature,
    *,
    panel_col: str,
    panel_order: list[str],
    value_col: str,
    title: str,
    subtitle: str,
    colorbar_label: str,
    colorbar_stem: str,
    output_path: Path,
) -> Path:
    work = data.loc[np.isfinite(pd.to_numeric(data[value_col], errors="coerce"))].copy()
    if work.empty:
        return output_path
    values = pd.to_numeric(work[value_col], errors="coerce")
    norm = symmetric_norm(values)
    fig, axes = plt.subplots(1, len(panel_order), figsize=(18.5, 6.7), dpi=180, sharex=True, sharey=True)
    if len(panel_order) == 1:
        axes = [axes]
    extent = map_extent_for_paths(work, la_feature.geometry, margin_fraction=0.08)
    for ax, panel in zip(axes, panel_order):
        panel_df = work.loc[work[panel_col].astype(str).eq(str(panel))].copy()
        set_map_axes(ax, extent)
        add_basemap(ax)
        draw_region_context(ax, regions, la_feature)
        segments = [
            [(float(row.event_lon), float(row.event_lat)), (float(row.sta_lon), float(row.sta_lat))]
            for row in panel_df.itertuples(index=False)
            if coordinates_are_finite(row)
        ]
        if segments:
            collection = LineCollection(
                segments,
                cmap="RdBu_r",
                norm=norm,
                linewidths=0.7,
                alpha=0.16,
                zorder=3,
            )
            collection.set_array(pd.to_numeric(panel_df[value_col], errors="coerce").to_numpy(dtype=float))
            ax.add_collection(collection)
        ax.scatter(panel_df["sta_lon"], panel_df["sta_lat"], s=7, color="#111827", alpha=0.42, linewidths=0, zorder=5)
        ax.scatter(panel_df["event_lon"], panel_df["event_lat"], s=6, color="#6B7280", alpha=0.15, linewidths=0, zorder=2)
        format_map_ticks(ax)
        ax.set_title(f"{format_panel_label(panel)}\nn={len(panel_df):,} paths", fontsize=9, color=TOKENS["ink"])
    axes[0].set_ylabel("Latitude")
    for ax in axes:
        ax.set_xlabel("Longitude")
    mappable = plt.cm.ScalarMappable(norm=norm, cmap="RdBu_r")
    add_header(fig, axes[0], title, subtitle)
    fig.subplots_adjust(top=0.80, right=0.90, bottom=0.18, wspace=0.08)
    cax = fig.add_axes([0.925, 0.25, 0.014, 0.44])
    fig.colorbar(mappable, cax=cax, label=colorbar_label)
    fig.text(0.925, 0.71, colorbar_stem, ha="left", va="bottom", fontsize=8, color=TOKENS["muted"])
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_regional_inbound_boundary_entry_map(
    data: pd.DataFrame,
    regions: Sequence[RegionFeature],
    la_feature: RegionFeature,
    *,
    panel_col: str,
    panel_order: list[str],
    value_col: str,
    title: str,
    subtitle: str,
    colorbar_label: str,
    colorbar_stem: str,
    output_path: Path,
) -> Path:
    work = data.loc[
        np.isfinite(pd.to_numeric(data[value_col], errors="coerce"))
        & data["la_basin_entry_lon"].notna()
        & data["la_basin_entry_lat"].notna()
        & data["la_basin_entry_segment_index"].notna()
    ].copy()
    if work.empty:
        return output_path
    values = pd.to_numeric(work[value_col], errors="coerce")
    norm = symmetric_norm(values)
    fig, axes = plt.subplots(1, len(panel_order), figsize=(18.5, 6.7), dpi=180, sharex=True, sharey=True)
    if len(panel_order) == 1:
        axes = [axes]
    extent = map_extent_for_geometry(la_feature.geometry, margin_fraction=0.22)
    for ax, panel in zip(axes, panel_order):
        panel_df = work.loc[work[panel_col].astype(str).eq(str(panel))].copy()
        set_map_axes(ax, extent)
        add_basemap(ax)
        draw_region_context(ax, regions, la_feature, only_near_la=True)
        segment_summary = summarize_entry_segments(panel_df, value_col=value_col)
        if not segment_summary.empty:
            segments = [
                [(float(row.segment_start_lon), float(row.segment_start_lat)), (float(row.segment_end_lon), float(row.segment_end_lat))]
                for row in segment_summary.itertuples(index=False)
            ]
            linewidths = np.clip(1.4 + 0.22 * np.sqrt(segment_summary["n_event_station_pairs"].to_numpy(dtype=float)), 1.5, 5.0)
            collection = LineCollection(
                segments,
                cmap="RdBu_r",
                norm=norm,
                linewidths=linewidths,
                alpha=0.95,
                capstyle="round",
                zorder=5,
            )
            collection.set_array(segment_summary["mean_value"].to_numpy(dtype=float))
            ax.add_collection(collection)
        ax.set_title(f"{format_panel_label(panel)}\n{len(segment_summary):,} boundary segments; n={len(panel_df):,} paths", fontsize=9, color=TOKENS["ink"])
        format_map_ticks(ax)
    axes[0].set_ylabel("Latitude")
    for ax in axes:
        ax.set_xlabel("Longitude")
    mappable = plt.cm.ScalarMappable(norm=norm, cmap="RdBu_r")
    add_header(fig, axes[0], title, subtitle)
    fig.subplots_adjust(top=0.80, right=0.90, bottom=0.18, wspace=0.08)
    cax = fig.add_axes([0.925, 0.25, 0.014, 0.44])
    fig.colorbar(mappable, cax=cax, label=colorbar_label)
    fig.text(0.925, 0.71, colorbar_stem, ha="left", va="bottom", fontsize=8, color=TOKENS["muted"])
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_lowess_corrected_pga_boundary_maps(
    data: pd.DataFrame,
    regions: Sequence[RegionFeature],
    la_feature: RegionFeature,
    output_dir: Path,
) -> list[Path]:
    required = {
        "magdist_corrected_value_obs",
        "magdist_corrected_value_syn",
        "magdist_corrected_log2_residual",
        "la_basin_entry_segment_index",
    }
    if not required.issubset(data.columns):
        return []
    paths: list[Path] = []
    panel_specs = [
        ("magdist_corrected_value_obs", "Observed PGA", "scaled PGA", "viridis", False),
        ("magdist_corrected_value_syn", "Synthetic PGA", "scaled PGA", "viridis", False),
        ("magdist_corrected_log2_residual", "Residual", "log2 residual", "RdBu_r", True),
    ]
    for frac in LOWESS_BOUNDARY_FRACS:
        for band in BANDS:
            band_df = data.loc[data["band"].astype(str).eq(str(band))].copy()
            if band_df.empty:
                continue
            suffix = "" if math.isclose(float(frac), 0.08) else f"__frac_{slugify_lowess_frac(frac)}"
            output_path = output_dir / f"la_basin_regional_inbound_pga_lowess_boundary_magdist_corrected{suffix}__{slugify(band)}.png"
            paths.append(
                plot_lowess_corrected_pga_boundary_map_for_band(
                    band_df,
                    regions,
                    la_feature,
                    panel_specs=panel_specs,
                    band=str(band),
                    lowess_frac=float(frac),
                    output_path=output_path,
                )
            )
    return [path for path in paths if path.exists()]


def plot_lowess_corrected_pga_boundary_map_for_band(
    band_df: pd.DataFrame,
    regions: Sequence[RegionFeature],
    la_feature: RegionFeature,
    *,
    panel_specs: list[tuple[str, str, str, str, bool]],
    band: str,
    lowess_frac: float,
    output_path: Path,
) -> Path:
    boundary_segments = build_boundary_segments(la_feature)
    extent = map_extent_for_geometry(la_feature.geometry, margin_fraction=0.22)
    fig, axes = plt.subplots(1, len(panel_specs), figsize=(18.5, 6.7), dpi=180, sharex=True, sharey=True)
    if len(panel_specs) == 1:
        axes = [axes]
    colorbars: list[tuple[plt.cm.ScalarMappable, plt.Axes, str]] = []
    panel_payloads: list[dict[str, object]] = []
    for value_col, panel_label, colorbar_label, cmap, diverging in panel_specs:
        segment_summary = summarize_entry_segments(band_df, value_col=value_col)
        smoothed = smooth_segment_values(boundary_segments, segment_summary, la_feature, frac=lowess_frac)
        if value_col in {"magdist_corrected_value_obs", "magdist_corrected_value_syn"}:
            smoothed = np.where(np.isfinite(smoothed), np.maximum(smoothed, 0.0), np.nan)
        support_widths = support_linewidths(boundary_segments, segment_summary, la_feature, frac=lowess_frac)
        panel_payloads.append(
            {
                "value_col": value_col,
                "panel_label": panel_label,
                "colorbar_label": colorbar_label,
                "cmap": cmap,
                "diverging": diverging,
                "segment_summary": segment_summary,
                "smoothed": smoothed,
                "support_widths": support_widths,
            }
        )
    pga_values: list[float] = []
    for payload in panel_payloads:
        if payload["value_col"] in {"magdist_corrected_value_obs", "magdist_corrected_value_syn"}:
            pga_values.extend(pd.Series(payload["smoothed"], dtype=float).dropna().tolist())
    shared_pga_norm = value_norm(pd.Series(pga_values, dtype=float), diverging=False)
    for ax, payload in zip(axes, panel_payloads):
        set_map_axes(ax, extent)
        add_basemap(ax)
        draw_region_context(ax, regions, la_feature, only_near_la=True)
        smoothed = payload["smoothed"]
        support_widths = payload["support_widths"]
        if payload["value_col"] in {"magdist_corrected_value_obs", "magdist_corrected_value_syn"}:
            norm = shared_pga_norm
        else:
            norm = value_norm(pd.Series(smoothed, dtype=float), diverging=bool(payload["diverging"]))
        segments = [
            [(float(row.segment_start_lon), float(row.segment_start_lat)), (float(row.segment_end_lon), float(row.segment_end_lat))]
            for row in boundary_segments.itertuples(index=False)
        ]
        collection = LineCollection(
            segments,
            cmap=str(payload["cmap"]),
            norm=norm,
            linewidths=support_widths,
            alpha=0.98,
            capstyle="round",
            zorder=6,
        )
        collection.set_array(smoothed)
        ax.add_collection(collection)
        colorbars.append((plt.cm.ScalarMappable(norm=norm, cmap=str(payload["cmap"])), ax, str(payload["colorbar_label"])))
        format_map_ticks(ax)
        ax.set_title(
            f"{payload['panel_label']}\n{len(payload['segment_summary']):,} occupied 50 m segments; n={len(band_df):,} paths",
            fontsize=9,
            color=TOKENS["ink"],
        )
    axes[0].set_ylabel("Latitude")
    for ax in axes:
        ax.set_xlabel("Longitude")
    add_header(
        fig,
        axes[0],
        f"LA Basin {band} PGA boundary LOWESS after magnitude and distance correction",
        f"Regional-inbound paths only. Observed/synthetic PGA use fixed M/R scaling; residual uses raw log2 residual. Line thickness shows relative path support. LOWESS frac={lowess_frac:g}.",
    )
    fig.subplots_adjust(top=0.80, right=0.98, bottom=0.25, wspace=0.08)
    for mappable, ax, colorbar_label in colorbars:
        bbox = ax.get_position()
        cax = fig.add_axes([bbox.x0 + 0.08 * bbox.width, 0.125, 0.84 * bbox.width, 0.018])
        fig.colorbar(mappable, cax=cax, orientation="horizontal", label=colorbar_label)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path


def build_target_region_inbound_pga_data(pair_band: pd.DataFrame, target_region: RegionFeature) -> pd.DataFrame:
    data = pair_band.loc[pair_band["metric"].astype(str).eq("PGA")].copy()
    if data.empty:
        return data
    event_inside: list[bool] = []
    station_inside: list[bool] = []
    for row in data.itertuples(index=False):
        event_point = Point(float(getattr(row, "event_lon")), float(getattr(row, "event_lat")))
        station_point = Point(float(getattr(row, "sta_lon")), float(getattr(row, "sta_lat")))
        event_inside.append(bool(target_region.geometry.covers(event_point)))
        station_inside.append(bool(target_region.geometry.covers(station_point)))
    data["_target_event_inside"] = event_inside
    data["_target_station_inside"] = station_inside
    data = data.loc[data["_target_station_inside"] & ~data["_target_event_inside"]].copy()
    if data.empty:
        return data
    data = add_la_basin_entry_points(data, target_region)
    data = add_mag_distance_corrected_pga_values(data)
    return data


def plot_region_boundary_lowess_3x3(
    pair_band: pd.DataFrame,
    regions: Sequence[RegionFeature],
    *,
    target_region_name: str,
    lowess_frac: float,
    output_dir: Path,
) -> Path | None:
    target_region = first_region(regions, target_region_name)
    if target_region is None:
        return None
    data = build_target_region_inbound_pga_data(pair_band, target_region)
    if data.empty:
        return None
    panel_specs = [
        ("magdist_corrected_value_obs", "Observed PGA", "scaled PGA", "rainbow", False),
        ("magdist_corrected_value_syn", "Synthetic PGA", "scaled PGA", "rainbow", False),
        ("magdist_corrected_log2_residual", "Residual", "log2 residual", "RdBu_r", True),
    ]
    boundary_segments = build_boundary_segments(target_region)
    extent = map_extent_for_geometry(target_region.geometry, margin_fraction=0.28)
    fig, axes = plt.subplots(3, 4, figsize=(21.5, 15.0), dpi=180, sharex=True, sharey=True)
    payloads: dict[tuple[str, str], dict[str, object]] = {}
    pga_values_by_band: dict[str, list[float]] = {str(band): [] for band in BANDS}
    residual_values: list[float] = []
    for band in BANDS:
        band_df = data.loc[data["band"].astype(str).eq(str(band))].copy()
        for value_col, panel_label, colorbar_label, cmap, diverging in panel_specs:
            segment_summary = summarize_entry_segments(band_df, value_col=value_col)
            smoothed = smooth_segment_values(boundary_segments, segment_summary, target_region, frac=lowess_frac)
            if value_col in {"magdist_corrected_value_obs", "magdist_corrected_value_syn"}:
                smoothed = np.where(np.isfinite(smoothed), np.maximum(smoothed, 0.0), np.nan)
            support_counts = smooth_support_counts(boundary_segments, segment_summary, target_region, frac=lowess_frac)
            payloads[(str(band), value_col)] = {
                "band_df": band_df,
                "segment_summary": segment_summary,
                "smoothed": smoothed,
                "support_counts": support_counts,
                "panel_label": panel_label,
                "colorbar_label": colorbar_label,
                "cmap": cmap,
                "diverging": diverging,
            }
            values = pd.Series(smoothed, dtype=float).dropna().tolist()
            if value_col in {"magdist_corrected_value_obs", "magdist_corrected_value_syn"}:
                pga_values_by_band[str(band)].extend(values)
            else:
                residual_values.extend(values)
        residual_summary = summarize_entry_segments(band_df, value_col="magdist_corrected_log2_residual")
        residual_support_counts = smooth_support_counts(boundary_segments, residual_summary, target_region, frac=lowess_frac)
        confidence = bootstrap_residual_sign_confidence(
            band_df,
            boundary_segments,
            target_region,
            lowess_frac=lowess_frac,
            samples=BOUNDARY_CONFIDENCE_BOOTSTRAPS,
            seed=RANDOM_SEED + 31 * (BANDS.index(band) + 1) + int(round(lowess_frac * 100000)),
        )
        payloads[(str(band), "residual_bootstrap_confidence")] = {
            "band_df": band_df,
            "segment_summary": residual_summary,
            "smoothed": confidence,
            "support_counts": residual_support_counts,
            "panel_label": "Residual confidence",
            "colorbar_label": "bootstrap sign confidence",
            "cmap": "magma",
            "diverging": False,
        }
    pga_values_by_band = {str(band): [] for band in BANDS}
    residual_values = []
    for band in BANDS:
        support_mask = np.isfinite(np.asarray(payloads[(str(band), "residual_bootstrap_confidence")]["smoothed"], dtype=float))
        for value_col, *_rest in panel_specs:
            values = np.asarray(payloads[(str(band), value_col)]["smoothed"], dtype=float)
            masked_values = np.where(support_mask, values, np.nan)
            payloads[(str(band), value_col)]["smoothed"] = masked_values
            finite_values = pd.Series(masked_values, dtype=float).dropna().tolist()
            if value_col in {"magdist_corrected_value_obs", "magdist_corrected_value_syn"}:
                pga_values_by_band[str(band)].extend(finite_values)
            else:
                residual_values.extend(finite_values)
    all_support_counts = np.concatenate(
        [
            pd.Series(payload["support_counts"], dtype=float).dropna().to_numpy(dtype=float)
            for payload in payloads.values()
            if "support_counts" in payload
        ]
    )
    if len(all_support_counts):
        support_low = float(np.nanquantile(all_support_counts, 0.01))
        support_high = float(np.nanquantile(all_support_counts, 0.99))
    else:
        support_low = math.nan
        support_high = math.nan
    for payload in payloads.values():
        payload["support_widths"] = linewidths_from_support_counts(
            payload["support_counts"],
            low=support_low,
            high=support_high,
        )
    pga_norms = {
        band: value_norm(pd.Series(values, dtype=float), diverging=False)
        for band, values in pga_values_by_band.items()
    }
    residual_norm = value_norm(pd.Series(residual_values, dtype=float), diverging=True)
    confidence_norm = Normalize(vmin=0.5, vmax=1.0)
    segments = [
        [(float(row.segment_start_lon), float(row.segment_start_lat)), (float(row.segment_end_lon), float(row.segment_end_lat))]
        for row in boundary_segments.itertuples(index=False)
    ]
    for row_idx, band in enumerate(BANDS):
        for col_idx, (value_col, panel_label, _colorbar_label, cmap, _diverging) in enumerate(panel_specs):
            ax = axes[row_idx, col_idx]
            payload = payloads[(str(band), value_col)]
            set_map_axes(ax, extent)
            add_basemap(ax)
            draw_region_context(ax, regions, target_region, only_near_la=False)
            norm = pga_norms[str(band)] if value_col in {"magdist_corrected_value_obs", "magdist_corrected_value_syn"} else residual_norm
            collection = LineCollection(
                segments,
                cmap=cmap,
                norm=norm,
                linewidths=payload["support_widths"],
                alpha=0.98,
                capstyle="round",
                zorder=6,
            )
            collection.set_array(payload["smoothed"])
            ax.add_collection(collection)
            format_map_ticks(ax)
            if col_idx < 2:
                ax.tick_params(labelbottom=False)
            seg_count = len(payload["segment_summary"])
            path_count = len(payload["band_df"])
            ax.set_title(f"{band} | {panel_label}\n{seg_count:,} occupied segments; n={path_count:,} paths", fontsize=8.2, color=TOKENS["ink"])
            if col_idx == 0:
                ax.set_ylabel("Latitude")
            if row_idx == 2 and col_idx >= 2:
                ax.set_xlabel("Longitude")
        ax = axes[row_idx, 3]
        payload = payloads[(str(band), "residual_bootstrap_confidence")]
        set_map_axes(ax, extent)
        add_basemap(ax)
        draw_region_context(ax, regions, target_region, only_near_la=False)
        collection = LineCollection(
            segments,
            cmap="magma",
            norm=confidence_norm,
            linewidths=payload["support_widths"],
            alpha=0.98,
            capstyle="round",
            zorder=6,
        )
        collection.set_array(payload["smoothed"])
        ax.add_collection(collection)
        format_map_ticks(ax)
        seg_count = len(payload["segment_summary"])
        path_count = len(payload["band_df"])
        ax.set_title(f"{band} | Residual confidence\n{seg_count:,} occupied segments; n={path_count:,} paths", fontsize=8.2, color=TOKENS["ink"])
        if row_idx == 2:
            ax.set_xlabel("Longitude")
    fig.subplots_adjust(top=0.84, left=0.14, right=0.91, bottom=0.09, wspace=0.08, hspace=0.38)
    add_header(
        fig,
        axes[0, 0],
        f"{target_region_name}: regional-inbound PGA boundary LOWESS",
        f"Rows are passbands; columns are observed scaled PGA, synthetic scaled PGA, raw log2 residual, and bootstrap sign confidence. Obs/syn share one PGA color scale within each row; residual is unadjusted. LOWESS frac={lowess_frac:g}.",
        top=0.84,
        title_y=0.995,
        subtitle_y=0.965,
    )
    for row_idx, band in enumerate(BANDS):
        left_bbox = axes[row_idx, 0].get_position()
        cax = fig.add_axes([left_bbox.x0 - 0.058, left_bbox.y0 + 0.08 * left_bbox.height, 0.010, 0.84 * left_bbox.height])
        cbar = fig.colorbar(
            plt.cm.ScalarMappable(norm=pga_norms[str(band)], cmap="rainbow"),
            cax=cax,
            orientation="vertical",
            label=f"scaled PGA ({band})",
        )
        cbar.ax.yaxis.set_ticks_position("left")
        cbar.ax.yaxis.set_label_position("left")
        cbar.ax.tick_params(labelsize=7, pad=2)
        cbar.ax.yaxis.label.set_size(8)
    support_handles = support_linewidth_legend_handles(all_support_counts, low=support_low, high=support_high)
    if support_handles:
        fig.legend(
            handles=support_handles,
            title="Line width\napprox paths/km",
            loc="upper left",
            bbox_to_anchor=(0.928, 0.83),
            frameon=False,
            fontsize=7.5,
            title_fontsize=8,
            handlelength=2.4,
            borderaxespad=0.0,
        )
    cax_res = fig.add_axes([0.935, 0.43, 0.014, 0.22])
    fig.colorbar(plt.cm.ScalarMappable(norm=residual_norm, cmap="RdBu_r"), cax=cax_res, label="log2 residual")
    cax_conf = fig.add_axes([0.935, 0.13, 0.014, 0.22])
    fig.colorbar(plt.cm.ScalarMappable(norm=confidence_norm, cmap="magma"), cax=cax_conf, label="bootstrap sign confidence")
    suffix = f"frac_{slugify_lowess_frac(lowess_frac)}"
    path = output_dir / f"region_boundary_lowess_3x4_fixed_mr__{slugify(target_region_name)}__{suffix}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_all_region_inset_boundary_overview(
    pair_band: pd.DataFrame,
    regions: Sequence[RegionFeature],
    *,
    bbox: tuple[float, float, float, float],
    lowess_frac: float,
    output_dir: Path,
    inset_m: float = 1500.0,
) -> Path | None:
    min_lon, max_lon, min_lat, max_lat = bbox
    bbox_geometry = box(min_lon, min_lat, max_lon, max_lat)
    target_regions = [
        region
        for region in regions
        if region.geometry.intersects(bbox_geometry)
        and defined_region_mask(pd.Series([region.long_name])).iloc[0]
        and region.region_type not in {"outside", "unknown", "Offshore"}
    ]
    if not target_regions:
        return None

    overview_data = pair_band.loc[
        pair_band["metric"].astype(str).eq("PGA")
        & pd.to_numeric(pair_band["sta_lon"], errors="coerce").between(min_lon, max_lon)
        & pd.to_numeric(pair_band["sta_lat"], errors="coerce").between(min_lat, max_lat)
    ].copy()
    if overview_data.empty:
        return None

    panel_order = ("obs", "syn", "residual", "confidence")
    panel_labels = {
        "obs": "Observed PGA",
        "syn": "Synthetic PGA",
        "residual": "Residual",
        "confidence": "Residual confidence",
    }
    panel_value_cols = {
        "obs": "magdist_corrected_value_obs",
        "syn": "magdist_corrected_value_syn",
        "residual": "magdist_corrected_log2_residual",
    }
    payloads: dict[tuple[str, str], list[dict[str, object]]] = {
        (str(band), panel): [] for band in BANDS for panel in panel_order
    }
    pga_values_by_band: dict[str, list[float]] = {str(band): [] for band in BANDS}
    residual_values: list[float] = []
    support_values: list[float] = []
    skipped_regions: list[str] = []

    for region in target_regions:
        print(f"overview region start: {region.long_name}", flush=True)
        data = build_target_region_inbound_pga_data(overview_data, region)
        if data.empty:
            skipped_regions.append(region.long_name)
            continue
        boundary_segments = build_boundary_segments(region)
        inset_segments = build_inset_boundary_segments(region, boundary_segments, inset_m=inset_m)
        segments = [
            [(float(row.segment_start_lon), float(row.segment_start_lat)), (float(row.segment_end_lon), float(row.segment_end_lat))]
            for row in inset_segments.itertuples(index=False)
        ]
        for band in BANDS:
            band_df = data.loc[data["band"].astype(str).eq(str(band))].copy()
            if band_df.empty:
                continue
            residual_summary = pd.DataFrame()
            residual_support_counts = np.full(len(boundary_segments), np.nan)
            for panel, value_col in panel_value_cols.items():
                segment_summary = summarize_entry_segments(band_df, value_col=value_col)
                if segment_summary.empty:
                    continue
                values = smooth_segment_values(boundary_segments, segment_summary, region, frac=lowess_frac)
                if panel in {"obs", "syn"}:
                    values = np.where(np.isfinite(values), np.maximum(values, 0.0), np.nan)
                    pga_values_by_band[str(band)].extend(pd.Series(values, dtype=float).dropna().tolist())
                else:
                    residual_summary = segment_summary
                    residual_values.extend(pd.Series(values, dtype=float).dropna().tolist())
                support_counts = smooth_support_counts(boundary_segments, segment_summary, region, frac=lowess_frac)
                if panel == "residual":
                    residual_support_counts = support_counts
                support_values.extend(pd.Series(support_counts, dtype=float).dropna().tolist())
                shared = {
                    "region": region,
                    "segments": segments,
                    "support_counts": support_counts,
                    "n_paths": len(band_df),
                    "n_segments": len(segment_summary),
                }
                payloads[(str(band), panel)].append({**shared, "values": values})
            if residual_summary.empty:
                continue
            confidence = bootstrap_residual_sign_confidence(
                band_df,
                boundary_segments,
                region,
                lowess_frac=lowess_frac,
                samples=max(12, BOUNDARY_CONFIDENCE_BOOTSTRAPS // 2),
                seed=RANDOM_SEED
                + 101 * (BANDS.index(band) + 1)
                + 17 * region.index
                + int(round(lowess_frac * 100000)),
            )
            shared = {
                "region": region,
                "segments": segments,
                "support_counts": residual_support_counts,
                "n_paths": len(band_df),
                "n_segments": len(residual_summary),
            }
            payloads[(str(band), "confidence")].append({**shared, "values": confidence})
        print(f"overview region done: {region.long_name} rows={len(data):,}", flush=True)

    pga_values_by_band = {str(band): [] for band in BANDS}
    residual_values = []
    for band in BANDS:
        confidence_masks = {
            int(payload["region"].index): np.isfinite(np.asarray(payload["values"], dtype=float))
            for payload in payloads[(str(band), "confidence")]
        }
        for panel in ("obs", "syn", "residual"):
            for payload in payloads[(str(band), panel)]:
                support_mask = confidence_masks.get(int(payload["region"].index))
                if support_mask is None:
                    payload["values"] = np.full_like(np.asarray(payload["values"], dtype=float), np.nan, dtype=float)
                    continue
                values = np.asarray(payload["values"], dtype=float)
                masked_values = np.where(support_mask, values, np.nan)
                payload["values"] = masked_values
                finite_values = pd.Series(masked_values, dtype=float).dropna().tolist()
                if panel in {"obs", "syn"}:
                    pga_values_by_band[str(band)].extend(finite_values)
                elif panel == "residual":
                    residual_values.extend(finite_values)

    if not residual_values:
        return None

    support_low = float(np.nanquantile(support_values, 0.01)) if support_values else math.nan
    support_high = float(np.nanquantile(support_values, 0.99)) if support_values else math.nan
    pga_norms = {
        band: positive_robust_norm(pd.Series(values, dtype=float), upper_quantile=0.95)
        for band, values in pga_values_by_band.items()
    }
    residual_norm = TwoSlopeNorm(vcenter=0.0, vmin=-2.0, vmax=2.0)
    confidence_norm = Normalize(vmin=0.5, vmax=1.0)

    fig, axes = plt.subplots(3, 4, figsize=(22.5, 14.0), dpi=180, sharex=True, sharey=True)
    extent = (min_lon, max_lon, min_lat, max_lat)
    for row_idx, band in enumerate(BANDS):
        for col_idx, panel in enumerate(panel_order):
            ax = axes[row_idx, col_idx]
            set_map_axes(ax, extent)
            add_basemap(ax)
            draw_bbox_region_context(ax, target_regions, bbox_geometry)
            if panel in {"obs", "syn"}:
                norm = pga_norms[str(band)]
                cmap = "rainbow"
            elif panel == "residual":
                norm = residual_norm
                cmap = "RdBu_r"
            else:
                norm = confidence_norm
                cmap = "magma"
            total_paths = 0
            total_segments = 0
            for payload in payloads[(str(band), panel)]:
                values = np.asarray(payload["values"], dtype=float)
                finite = np.isfinite(values)
                if not finite.any():
                    continue
                segments = [segment for segment, ok in zip(payload["segments"], finite) if ok]
                widths = 0.55 * linewidths_from_support_counts(
                    np.asarray(payload["support_counts"], dtype=float),
                    low=support_low,
                    high=support_high,
                )[finite]
                widths = np.clip(widths, 0.9, 4.8)
                collection = LineCollection(
                    segments,
                    cmap=cmap,
                    norm=norm,
                    linewidths=widths,
                    alpha=0.98,
                    capstyle="round",
                    zorder=7,
                )
                collection.set_array(values[finite])
                ax.add_collection(collection)
                total_paths += int(payload["n_paths"])
                total_segments += int(payload["n_segments"])
            format_map_ticks(ax)
            if col_idx == 0:
                ax.set_ylabel("Latitude")
            if row_idx == 2 and col_idx >= 2:
                ax.set_xlabel("Longitude")
            ax.set_title(
                f"{band} | {panel_labels[panel]}\n{len(payloads[(str(band), panel)]):,} regions; {total_segments:,} occupied segments; n={total_paths:,} paths",
                fontsize=8.4,
                color=TOKENS["ink"],
            )

    fig.subplots_adjust(top=0.86, right=0.89, bottom=0.08, left=0.13, wspace=0.06, hspace=0.30)
    add_header(
        fig,
        axes[0, 0],
        "Regional-inbound PGA on inward-offset region boundaries",
        f"Regions intersecting lon {min_lon:g} to {max_lon:g}, lat {min_lat:g} to {max_lat:g}. Lines are drawn {inset_m / 1000:g} km inside each region; calculations use actual boundary crossings. LOWESS frac={lowess_frac:g}.",
        top=0.86,
        title_y=0.995,
        subtitle_y=0.955,
    )
    for row_idx, band in enumerate(BANDS):
        left_bbox = axes[row_idx, 0].get_position()
        cax = fig.add_axes([left_bbox.x0 - 0.052, left_bbox.y0 + 0.08 * left_bbox.height, 0.009, 0.84 * left_bbox.height])
        cbar = fig.colorbar(
            plt.cm.ScalarMappable(norm=pga_norms[str(band)], cmap="rainbow"),
            cax=cax,
            orientation="vertical",
            label=f"scaled PGA ({band})",
        )
        cbar.ax.yaxis.set_ticks_position("left")
        cbar.ax.yaxis.set_label_position("left")
        cbar.ax.tick_params(labelsize=7, pad=2)
        cbar.ax.yaxis.label.set_size(8)
    support_handles = support_linewidth_legend_handles(np.asarray(support_values, dtype=float), low=support_low, high=support_high, width_scale=0.55)
    if support_handles:
        fig.legend(
            handles=support_handles,
            title="Line width\napprox paths/km",
            loc="upper left",
            bbox_to_anchor=(0.912, 0.82),
            frameon=False,
            fontsize=7.5,
            title_fontsize=8,
            handlelength=2.4,
            borderaxespad=0.0,
        )
    cax_res = fig.add_axes([0.920, 0.43, 0.012, 0.22])
    fig.colorbar(plt.cm.ScalarMappable(norm=residual_norm, cmap="RdBu_r"), cax=cax_res, label="log2 residual")
    cax_conf = fig.add_axes([0.920, 0.14, 0.012, 0.22])
    fig.colorbar(plt.cm.ScalarMappable(norm=confidence_norm, cmap="magma"), cax=cax_conf, label="bootstrap sign confidence")
    slug = f"lon_{min_lon:g}_{max_lon:g}__lat_{min_lat:g}_{max_lat:g}".replace("-", "m").replace(".", "p")
    path = output_dir / f"region_boundary_inset_overview_pga_obs_syn_residual_confidence__{slug}__frac_{slugify_lowess_frac(lowess_frac)}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    if skipped_regions:
        print(f"Skipped {len(skipped_regions)} bbox regions without inbound PGA support.")
    return path


def build_inset_boundary_segments(region: RegionFeature, boundary_segments: pd.DataFrame, *, inset_m: float) -> pd.DataFrame:
    original_boundary = exterior_boundary(region.geometry_projected)
    original_length = float(original_boundary.length)
    inset_geometry = None
    for candidate_inset in (float(inset_m), float(inset_m) * 0.5, float(inset_m) * 0.25, 0.0):
        candidate = region.geometry_projected.buffer(-candidate_inset) if candidate_inset > 0 else region.geometry_projected
        if not candidate.is_empty and float(candidate.length) > 0:
            inset_geometry = candidate
            break
    if inset_geometry is None:
        return boundary_segments
    inset_boundary = exterior_boundary(inset_geometry)
    inset_length = float(inset_boundary.length)
    if not np.isfinite(original_length) or original_length <= 0 or not np.isfinite(inset_length) or inset_length <= 0:
        return boundary_segments
    inverse = Transformer.from_crs("EPSG:3310", "EPSG:4326", always_xy=True)
    rows: list[dict[str, float]] = []
    for row in boundary_segments.itertuples(index=False):
        start_fraction = min(max(float(row.segment_index) * LA_BASIN_ENTRY_SEGMENT_M / original_length, 0.0), 1.0)
        end_fraction = min(max((float(row.segment_index) + 1.0) * LA_BASIN_ENTRY_SEGMENT_M / original_length, 0.0), 1.0)
        center_fraction = min(max(float(row.segment_center_m) / original_length, 0.0), 1.0)
        start_point = inset_boundary.interpolate(start_fraction * inset_length)
        end_point = inset_boundary.interpolate(end_fraction * inset_length)
        start_lon, start_lat = inverse.transform(float(start_point.x), float(start_point.y))
        end_lon, end_lat = inverse.transform(float(end_point.x), float(end_point.y))
        rows.append(
            {
                "segment_index": float(row.segment_index),
                "segment_center_m": center_fraction * inset_length,
                "segment_start_lon": float(start_lon),
                "segment_start_lat": float(start_lat),
                "segment_end_lon": float(end_lon),
                "segment_end_lat": float(end_lat),
            }
        )
    return pd.DataFrame(rows)


def draw_bbox_region_context(ax: plt.Axes, regions: Sequence[RegionFeature], bbox_geometry: object) -> None:
    for region in regions:
        if not region.geometry.intersects(bbox_geometry):
            continue
        for x, y in geometry_boundaries(region.geometry):
            ax.plot(x, y, color="#B8C0CC", linewidth=0.55, alpha=0.70, zorder=1)


def plot_la_basin_path_length(pair_band: pd.DataFrame, output_dir: Path) -> Path:
    data = pair_band.loc[pair_band["la_basin_path_class"].isin(["regional_inbound", "through_basin"])].copy()
    summary = (
        data.groupby(["metric", "band", "la_path_length_quantile_bin"], observed=True, dropna=False)
        .agg(x=("path_length_in_LA_Basin_km", "median"), y=("log2_residual", "median"), pairs=("station", "size"))
        .reset_index()
        .dropna(subset=["x", "y"])
    )
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.5), dpi=180, sharey=True)
    band_colors = {"1-2 sec": TOKENS["blue"], "2-3 sec": TOKENS["gold"], "3-5 sec": TOKENS["orange"]}
    for ax, metric in zip(axes, METRICS):
        work = summary.loc[summary["metric"].astype(str) == metric]
        for band, group in work.groupby("band", observed=True):
            ax.plot(group["x"], group["y"], marker="o", linewidth=2, color=band_colors.get(str(band), TOKENS["blue"]), label=str(band))
        ax.axhline(0, color="#344054", linewidth=1)
        ax.set_title(metric)
        ax.set_xlabel("Median path length in LA Basin (km)")
        ax.grid(axis="y", color=TOKENS["grid"], linewidth=0.8)
    axes[0].set_ylabel("Median log2 residual")
    axes[1].legend(title="Band", frameon=False)
    add_header(fig, axes[0], "LA Basin residuals by path length through basin", "Regional-inbound and through-basin paths, binned by LA Basin path length.")
    path = output_dir / "la_basin_residual_vs_path_length.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_la_basin_vs30(pair_band: pd.DataFrame, output_dir: Path) -> Path:
    data = pair_band.loc[pair_band["station_inside_LA_Basin"].fillna(False) & pair_band["Vs30"].notna()].copy()
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.5), dpi=180, sharey=True)
    for ax, metric in zip(axes, METRICS):
        work = data.loc[data["metric"].astype(str) == metric]
        for band in BANDS:
            band_df = work.loc[work["band"].astype(str) == band]
            grouped = band_df.groupby("Vs30_bin", dropna=False, observed=True).agg(x=("Vs30", "median"), y=("log2_residual", "median")).dropna()
            ax.plot(grouped["x"], grouped["y"], marker="o", linewidth=2, label=band)
        ax.axhline(0, color="#344054", linewidth=1)
        ax.set_title(metric)
        ax.set_xlabel("Vs30 bin median (m/s)")
        ax.grid(axis="y", color=TOKENS["grid"], linewidth=0.8)
    axes[0].set_ylabel("Median log2 residual")
    axes[1].legend(title="Band", frameon=False)
    add_header(fig, axes[0], "LA Basin station residuals by Vs30", "Stations inside LA Basin only; values are binned medians.")
    path = output_dir / "la_basin_residual_vs_vs30.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_la_basin_geology(pair_band: pd.DataFrame, output_dir: Path) -> Path:
    data = pair_band.loc[pair_band["station_inside_LA_Basin"].fillna(False) & pair_band["geologic_description"].notna()].copy()
    summary = data.groupby(["metric", "geologic_description"], dropna=False).agg(median=("log2_residual", "median"), pairs=("station", "size")).reset_index()
    top = summary.groupby("geologic_description")["pairs"].sum().sort_values(ascending=False).head(10).index.tolist()
    summary = summary.loc[summary["geologic_description"].isin(top)].copy()
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), dpi=180, sharex=True)
    for ax, metric in zip(axes, METRICS):
        work = summary.loc[summary["metric"].astype(str) == metric].sort_values("median")
        ax.barh(work["geologic_description"].astype(str), work["median"], color=TOKENS["blue"])
        ax.axvline(0, color="#344054", linewidth=1)
        ax.set_title(metric)
        ax.set_xlabel("Median log2 residual")
        ax.grid(axis="x", color=TOKENS["grid"], linewidth=0.8)
    add_header(fig, axes[0], "LA Basin residuals by geologic description", "Top geologic descriptions by support among LA Basin stations.")
    path = output_dir / "la_basin_residual_by_geologic_description.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_strongest_path_period_map(tests: pd.DataFrame, pair_band: pd.DataFrame, regions: Sequence[RegionFeature], output_dir: Path) -> Path:
    candidates = tests.loc[
        (tests["analysis_family"] == "event_to_station_region")
        & (tests["band_pair"] == "3-5 sec_minus_1-2 sec")
        & tests["meets_support"].fillna(False)
    ].copy()
    candidates["abs_effect"] = candidates["median_band_difference"].abs()
    top = candidates.sort_values("abs_effect", ascending=False).head(10)
    if top.empty:
        top = candidates.head(10)
    fig, ax = plt.subplots(figsize=(9, 8), dpi=180)
    for region in regions:
        for x, y in geometry_boundaries(region.geometry):
            ax.plot(x, y, color="#AAB2C0", linewidth=0.7)
    plotted = 0
    for row in top.itertuples(index=False):
        subset = pair_band.loc[
            (pair_band["metric"].astype(str) == getattr(row, "metric"))
            & (pair_band["event_region"].astype(str) == str(getattr(row, "event_region")))
            & (pair_band["station_region"].astype(str) == str(getattr(row, "station_region")))
        ].drop_duplicates(["event_id", "station"])
        subset = subset.head(20)
        color = TOKENS["orange"] if getattr(row, "median_band_difference") > 0 else TOKENS["blue"]
        for rec in subset.itertuples(index=False):
            ax.plot([rec.event_lon, rec.sta_lon], [rec.event_lat, rec.sta_lat], color=color, alpha=0.14, linewidth=0.8)
            plotted += 1
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal", adjustable="box")
    ax.legend(
        handles=[
            Line2D([0], [0], color=TOKENS["orange"], lw=2, label="3-5 sec more positive than 1-2 sec"),
            Line2D([0], [0], color=TOKENS["blue"], lw=2, label="3-5 sec more negative than 1-2 sec"),
        ],
        frameon=False,
        loc="lower left",
    )
    add_header(fig, ax, "Strongest supported path-period effects", f"Representative event-station paths from top supported event-region to station-region 3-5 minus 1-2 sec effects; {plotted} paths drawn.")
    path = output_dir / "strongest_path_period_effects_map.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def add_la_basin_entry_points(data: pd.DataFrame, la_feature: RegionFeature) -> pd.DataFrame:
    out = data.copy()
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3310", always_xy=True)
    boundary_projected = exterior_boundary(la_feature.geometry_projected)
    entry_lons: list[float] = []
    entry_lats: list[float] = []
    segment_indexes: list[float] = []
    segment_start_lons: list[float] = []
    segment_start_lats: list[float] = []
    segment_end_lons: list[float] = []
    segment_end_lats: list[float] = []
    for row in out.itertuples(index=False):
        point = first_polygon_entry_point(
            float(getattr(row, "event_lon")),
            float(getattr(row, "event_lat")),
            float(getattr(row, "sta_lon")),
            float(getattr(row, "sta_lat")),
            la_feature.geometry,
        )
        if point is None:
            entry_lons.append(math.nan)
            entry_lats.append(math.nan)
            segment_indexes.append(math.nan)
            segment_start_lons.append(math.nan)
            segment_start_lats.append(math.nan)
            segment_end_lons.append(math.nan)
            segment_end_lats.append(math.nan)
        else:
            entry_lons.append(float(point.x))
            entry_lats.append(float(point.y))
            segment = boundary_segment_for_entry(point, boundary_projected, transformer=transformer)
            segment_indexes.append(segment["segment_index"])
            segment_start_lons.append(segment["segment_start_lon"])
            segment_start_lats.append(segment["segment_start_lat"])
            segment_end_lons.append(segment["segment_end_lon"])
            segment_end_lats.append(segment["segment_end_lat"])
    out["la_basin_entry_lon"] = entry_lons
    out["la_basin_entry_lat"] = entry_lats
    out["la_basin_entry_segment_index"] = segment_indexes
    out["la_basin_entry_segment_start_lon"] = segment_start_lons
    out["la_basin_entry_segment_start_lat"] = segment_start_lats
    out["la_basin_entry_segment_end_lon"] = segment_end_lons
    out["la_basin_entry_segment_end_lat"] = segment_end_lats
    return out


def add_mag_distance_corrected_pga_values(data: pd.DataFrame) -> pd.DataFrame:
    out = data.copy()
    out["magdist_corrected_log2_residual"] = pd.to_numeric(out["log2_residual"], errors="coerce")
    magnitude = pd.to_numeric(out.get("magnitude"), errors="coerce")
    distance = pd.to_numeric(out.get("distance_km"), errors="coerce")
    r_eff = np.sqrt(np.square(distance) + FIXED_SCALING_H_KM**2)
    valid_reference = magnitude.notna() & np.isfinite(r_eff)
    if valid_reference.any():
        m_ref = float(magnitude.loc[valid_reference].median())
        r_ref = float(pd.Series(r_eff[valid_reference], index=out.index[valid_reference]).median())
    else:
        m_ref = math.nan
        r_ref = math.nan
    out["fixed_scaling_m_ref"] = m_ref
    out["fixed_scaling_r_eff_ref_km"] = r_ref
    out["fixed_scaling_r_eff_km"] = r_eff
    scale = pd.Series(np.nan, index=out.index, dtype=float)
    valid_scale = magnitude.notna() & np.isfinite(r_eff) & np.isfinite(r_ref) & (r_ref > 0)
    scale.loc[valid_scale] = (
        np.power(r_eff[valid_scale] / r_ref, FIXED_SCALING_DISTANCE_POWER)
        * np.power(10.0, -FIXED_SCALING_MAGNITUDE_B * (magnitude.loc[valid_scale] - m_ref))
    )
    out["fixed_mr_scale_factor"] = scale
    for source_col, target_col in [
        ("value_obs", "magdist_corrected_value_obs"),
        ("value_syn", "magdist_corrected_value_syn"),
    ]:
        source = pd.to_numeric(out.get(source_col), errors="coerce")
        source = source.where(source.gt(0) & np.isfinite(source))
        out[target_col] = source * scale
    return out


def safe_log2(values: object) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    out = pd.Series(np.nan, index=numeric.index, dtype=float)
    valid = numeric.gt(0) & np.isfinite(numeric)
    out.loc[valid] = np.log2(numeric.loc[valid])
    return out


def safe_log10(values: object) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    out = pd.Series(np.nan, index=numeric.index, dtype=float)
    valid = numeric.gt(0) & np.isfinite(numeric)
    out.loc[valid] = np.log10(numeric.loc[valid])
    return out


def build_boundary_segments(la_feature: RegionFeature) -> pd.DataFrame:
    inverse = Transformer.from_crs("EPSG:3310", "EPSG:4326", always_xy=True)
    boundary = exterior_boundary(la_feature.geometry_projected)
    length_m = float(boundary.length)
    rows: list[dict[str, float]] = []
    n_segments = max(1, int(math.ceil(length_m / LA_BASIN_ENTRY_SEGMENT_M)))
    for segment_index in range(n_segments):
        start_m = segment_index * LA_BASIN_ENTRY_SEGMENT_M
        end_m = min(start_m + LA_BASIN_ENTRY_SEGMENT_M, length_m)
        center_m = 0.5 * (start_m + end_m)
        start_point = boundary.interpolate(start_m)
        end_point = boundary.interpolate(end_m)
        start_lon, start_lat = inverse.transform(float(start_point.x), float(start_point.y))
        end_lon, end_lat = inverse.transform(float(end_point.x), float(end_point.y))
        rows.append(
            {
                "segment_index": float(segment_index),
                "segment_center_m": float(center_m),
                "segment_start_lon": float(start_lon),
                "segment_start_lat": float(start_lat),
                "segment_end_lon": float(end_lon),
                "segment_end_lat": float(end_lat),
            }
        )
    return pd.DataFrame(rows)


def smooth_segment_values(
    boundary_segments: pd.DataFrame,
    segment_summary: pd.DataFrame,
    la_feature: RegionFeature,
    *,
    frac: float,
) -> np.ndarray:
    if segment_summary.empty:
        return np.full(len(boundary_segments), np.nan)
    period_m = float(exterior_boundary(la_feature.geometry_projected).length)
    observed = segment_summary.dropna(subset=["segment_index", "median_value"]).copy()
    if observed.empty:
        return np.full(len(boundary_segments), np.nan)
    x_obs = (pd.to_numeric(observed["segment_index"], errors="coerce").to_numpy(dtype=float) + 0.5) * LA_BASIN_ENTRY_SEGMENT_M
    y_obs = pd.to_numeric(observed["median_value"], errors="coerce").to_numpy(dtype=float)
    valid = np.isfinite(x_obs) & np.isfinite(y_obs)
    x_obs = x_obs[valid]
    y_obs = y_obs[valid]
    x_eval = boundary_segments["segment_center_m"].to_numpy(dtype=float)
    return circular_lowess(x_obs, y_obs, x_eval, period_m=period_m, frac=frac)


def bootstrap_residual_sign_confidence(
    band_df: pd.DataFrame,
    boundary_segments: pd.DataFrame,
    la_feature: RegionFeature,
    *,
    lowess_frac: float,
    samples: int,
    seed: int,
) -> np.ndarray:
    work = band_df.loc[
        pd.to_numeric(band_df.get("magdist_corrected_log2_residual"), errors="coerce").notna()
        & band_df.get("la_basin_entry_segment_index").notna()
    ].copy()
    if work.empty:
        return np.full(len(boundary_segments), np.nan)
    rng = np.random.default_rng(seed)
    curves: list[np.ndarray] = []
    row_count = len(work)
    for _ in range(int(samples)):
        sample = work.iloc[rng.integers(0, row_count, size=row_count)].copy()
        segment_summary = summarize_entry_segments(sample, value_col="magdist_corrected_log2_residual")
        curves.append(smooth_segment_values_kernel(boundary_segments, segment_summary, la_feature, frac=lowess_frac))
    if not curves:
        return np.full(len(boundary_segments), np.nan)
    curve_array = np.vstack(curves)
    finite = np.isfinite(curve_array)
    finite_count = finite.sum(axis=0).astype(float)
    positive_share = np.full(curve_array.shape[1], np.nan)
    negative_share = np.full(curve_array.shape[1], np.nan)
    valid_columns = finite_count > 0
    positive_share[valid_columns] = ((curve_array > 0) & finite).sum(axis=0)[valid_columns] / finite_count[valid_columns]
    negative_share[valid_columns] = ((curve_array < 0) & finite).sum(axis=0)[valid_columns] / finite_count[valid_columns]
    confidence = np.maximum(positive_share, negative_share)
    confidence[~np.isfinite(confidence)] = np.nan
    return confidence


def smooth_segment_values_kernel(
    boundary_segments: pd.DataFrame,
    segment_summary: pd.DataFrame,
    la_feature: RegionFeature,
    *,
    frac: float,
) -> np.ndarray:
    if segment_summary.empty:
        return np.full(len(boundary_segments), np.nan)
    period_m = float(exterior_boundary(la_feature.geometry_projected).length)
    observed = segment_summary.dropna(subset=["segment_index", "median_value"]).copy()
    if observed.empty:
        return np.full(len(boundary_segments), np.nan)
    x_obs = (pd.to_numeric(observed["segment_index"], errors="coerce").to_numpy(dtype=float) + 0.5) * LA_BASIN_ENTRY_SEGMENT_M
    y_obs = pd.to_numeric(observed["median_value"], errors="coerce").to_numpy(dtype=float)
    valid = np.isfinite(x_obs) & np.isfinite(y_obs)
    x_obs = x_obs[valid]
    y_obs = y_obs[valid]
    if len(y_obs) == 0:
        return np.full(len(boundary_segments), np.nan)
    x_eval = boundary_segments["segment_center_m"].to_numpy(dtype=float)
    bandwidth = max(float(period_m) * float(frac), 1200.0)
    out = np.full(len(x_eval), np.nan)
    chunk_size = 512
    for start in range(0, len(x_eval), chunk_size):
        stop = min(start + chunk_size, len(x_eval))
        delta = ((x_obs[None, :] - x_eval[start:stop, None] + 0.5 * period_m) % period_m) - 0.5 * period_m
        distance = np.abs(delta)
        scaled = np.clip(distance / max(bandwidth, 1.0), 0.0, 1.0)
        weights = np.where(distance <= bandwidth, (1.0 - scaled**3) ** 3, 0.0)
        denom = weights.sum(axis=1)
        numer = weights @ y_obs
        valid_rows = denom > 0
        out[start:stop][valid_rows] = numer[valid_rows] / denom[valid_rows]
    return out


def support_linewidths(
    boundary_segments: pd.DataFrame,
    segment_summary: pd.DataFrame,
    la_feature: RegionFeature,
    *,
    frac: float,
) -> np.ndarray:
    smoothed_counts = smooth_support_counts(boundary_segments, segment_summary, la_feature, frac=frac)
    return linewidths_from_support_counts(smoothed_counts)


def smooth_support_counts(
    boundary_segments: pd.DataFrame,
    segment_summary: pd.DataFrame,
    la_feature: RegionFeature,
    *,
    frac: float,
) -> np.ndarray:
    if segment_summary.empty or "n_event_station_pairs" not in segment_summary.columns:
        return np.full(len(boundary_segments), np.nan)
    period_m = float(exterior_boundary(la_feature.geometry_projected).length)
    observed = segment_summary.dropna(subset=["segment_index", "n_event_station_pairs"]).copy()
    if observed.empty:
        return np.full(len(boundary_segments), np.nan)
    x_obs = (pd.to_numeric(observed["segment_index"], errors="coerce").to_numpy(dtype=float) + 0.5) * LA_BASIN_ENTRY_SEGMENT_M
    counts = pd.to_numeric(observed["n_event_station_pairs"], errors="coerce").to_numpy(dtype=float)
    valid = np.isfinite(x_obs) & np.isfinite(counts)
    if valid.sum() < 2:
        return np.full(len(boundary_segments), np.nan)
    x_eval = boundary_segments["segment_center_m"].to_numpy(dtype=float)
    return circular_lowess(x_obs[valid], counts[valid], x_eval, period_m=period_m, frac=frac)


def linewidths_from_support_counts(smoothed_counts: np.ndarray, *, low: float | None = None, high: float | None = None) -> np.ndarray:
    finite = smoothed_counts[np.isfinite(smoothed_counts)]
    if len(finite) == 0:
        return np.full(len(smoothed_counts), 3.0)
    if low is None:
        low = float(np.nanquantile(finite, 0.01))
    if high is None:
        high = float(np.nanquantile(finite, 0.99))
    if not np.isfinite(low) or not np.isfinite(high) or high <= low:
        scaled = np.full(len(smoothed_counts), 0.5)
    else:
        scaled = np.clip((smoothed_counts - low) / (high - low), 0.0, 1.0)
    widths = SUPPORT_LINEWIDTH_MIN + (SUPPORT_LINEWIDTH_MAX - SUPPORT_LINEWIDTH_MIN) * np.sqrt(scaled)
    widths[~np.isfinite(widths)] = SUPPORT_LINEWIDTH_MIN
    return widths


def support_linewidth_legend_handles(
    support_counts: np.ndarray,
    *,
    low: float,
    high: float,
    width_scale: float = 1.0,
) -> list[Line2D]:
    finite = pd.Series(support_counts, dtype=float).dropna().to_numpy(dtype=float)
    if len(finite) == 0:
        return []
    quantiles = np.nanquantile(finite, [0.2, 0.5, 0.8])
    rows: list[tuple[float, float]] = []
    seen: set[int] = set()
    for count in quantiles:
        density = float(count) / (LA_BASIN_ENTRY_SEGMENT_M / 1000.0)
        if density < 100:
            rounded_density = int(round(density / 5.0) * 5)
        elif density < 500:
            rounded_density = int(round(density / 25.0) * 25)
        else:
            rounded_density = int(round(density / 100.0) * 100)
        if rounded_density in seen:
            continue
        seen.add(rounded_density)
        width = float(linewidths_from_support_counts(np.asarray([count], dtype=float), low=low, high=high)[0]) * float(width_scale)
        rows.append((width, float(rounded_density)))
    return [
        Line2D([0], [0], color=TOKENS["ink"], lw=width, solid_capstyle="round", label=f"~{density:,.0f}")
        for width, density in rows
    ]


def circular_lowess(x_obs: np.ndarray, y_obs: np.ndarray, x_eval: np.ndarray, *, period_m: float, frac: float) -> np.ndarray:
    if len(y_obs) == 0:
        return np.full(len(x_eval), np.nan)
    if len(y_obs) < 4:
        return np.full(len(x_eval), float(np.nanmedian(y_obs)))
    bandwidth = max(float(period_m) * float(frac), 1200.0)
    min_neighbors = min(max(10, int(0.02 * len(y_obs))), len(y_obs))
    out = np.full(len(x_eval), np.nan)
    for idx, center in enumerate(x_eval):
        delta = circular_delta(x_obs, center, period_m=period_m)
        distance = np.abs(delta)
        local_bandwidth = bandwidth
        mask = distance <= local_bandwidth
        if mask.sum() < min_neighbors:
            kth = np.partition(distance, min_neighbors - 1)[min_neighbors - 1]
            local_bandwidth = max(float(kth), 1.0)
            mask = distance <= local_bandwidth
        scaled = np.clip(distance[mask] / max(local_bandwidth, 1.0), 0.0, 1.0)
        weights = (1.0 - scaled**3) ** 3
        design = np.column_stack([np.ones(mask.sum()), delta[mask]])
        weighted_design = design * weights[:, None]
        try:
            beta = np.linalg.lstsq(weighted_design, y_obs[mask] * weights, rcond=None)[0]
            out[idx] = float(beta[0])
        except np.linalg.LinAlgError:
            out[idx] = float(np.average(y_obs[mask], weights=weights))
    return out


def circular_delta(values: np.ndarray, center: float, *, period_m: float) -> np.ndarray:
    return ((np.asarray(values, dtype=float) - float(center) + 0.5 * period_m) % period_m) - 0.5 * period_m


def exterior_boundary(geometry: object) -> object:
    if hasattr(geometry, "geoms"):
        polygons = [geom for geom in geometry.geoms if hasattr(geom, "exterior")]
        if polygons:
            return max(polygons, key=lambda geom: float(geom.area)).exterior
    if hasattr(geometry, "exterior"):
        return geometry.exterior
    return geometry.boundary


def boundary_segment_for_entry(point: Point, boundary_projected: object, *, transformer: Transformer) -> dict[str, float]:
    x, y = transformer.transform(float(point.x), float(point.y))
    projected_point = Point(x, y)
    distance_m = float(boundary_projected.project(projected_point))
    segment_index = math.floor(distance_m / LA_BASIN_ENTRY_SEGMENT_M)
    start_m = segment_index * LA_BASIN_ENTRY_SEGMENT_M
    end_m = min(start_m + LA_BASIN_ENTRY_SEGMENT_M, float(boundary_projected.length))
    start_point = boundary_projected.interpolate(start_m)
    end_point = boundary_projected.interpolate(end_m)
    inverse = Transformer.from_crs("EPSG:3310", "EPSG:4326", always_xy=True)
    start_lon, start_lat = inverse.transform(float(start_point.x), float(start_point.y))
    end_lon, end_lat = inverse.transform(float(end_point.x), float(end_point.y))
    return {
        "segment_index": float(segment_index),
        "segment_start_lon": float(start_lon),
        "segment_start_lat": float(start_lat),
        "segment_end_lon": float(end_lon),
        "segment_end_lat": float(end_lat),
    }


def first_polygon_entry_point(event_lon: float, event_lat: float, sta_lon: float, sta_lat: float, polygon: object) -> Point | None:
    if not all(np.isfinite([event_lon, event_lat, sta_lon, sta_lat])):
        return None
    line = LineString([(event_lon, event_lat), (sta_lon, sta_lat)])
    candidates = geometry_points(line.intersection(polygon.boundary))
    if not candidates:
        inter = line.intersection(polygon)
        candidates = geometry_points(inter)
    if not candidates:
        return None
    candidates = [point for point in candidates if np.isfinite([point.x, point.y]).all()]
    if not candidates:
        return None
    return min(candidates, key=line.project)


def geometry_points(geometry: object) -> list[Point]:
    if geometry is None or getattr(geometry, "is_empty", True):
        return []
    geom_type = getattr(geometry, "geom_type", "")
    if geom_type == "Point":
        return [geometry]
    if geom_type == "MultiPoint":
        return list(geometry.geoms)
    if geom_type in {"LineString", "LinearRing"}:
        coords = list(geometry.coords)
        if not coords:
            return []
        return [Point(coords[0]), Point(coords[-1])]
    if hasattr(geometry, "geoms"):
        points: list[Point] = []
        for geom in geometry.geoms:
            points.extend(geometry_points(geom))
        return points
    return []


def summarize_entry_bins(panel_df: pd.DataFrame, *, value_col: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for direction, group in panel_df.groupby("la_basin_inbound_backazimuth_bin", dropna=False, observed=True, sort=False):
        values = pd.to_numeric(group[value_col], errors="coerce").dropna()
        if values.empty:
            continue
        counts = support_counts(group)
        rows.append(
            {
                "la_basin_inbound_backazimuth_bin": str(direction),
                "median_value": float(values.median()),
                "entry_lon": float(pd.to_numeric(group["la_basin_entry_lon"], errors="coerce").median()),
                "entry_lat": float(pd.to_numeric(group["la_basin_entry_lat"], errors="coerce").median()),
                **counts,
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        "la_basin_inbound_backazimuth_bin",
        key=lambda series: series.map(direction_bin_sort_key),
    )


def summarize_entry_segments(panel_df: pd.DataFrame, *, value_col: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for segment_index, group in panel_df.groupby("la_basin_entry_segment_index", dropna=True, observed=True, sort=False):
        values = pd.to_numeric(group[value_col], errors="coerce").dropna()
        if values.empty:
            continue
        counts = support_counts(group)
        first = group.iloc[0]
        rows.append(
            {
                "segment_index": float(segment_index),
                "mean_value": float(values.mean()),
                "median_value": float(values.median()),
                "segment_start_lon": float(first["la_basin_entry_segment_start_lon"]),
                "segment_start_lat": float(first["la_basin_entry_segment_start_lat"]),
                "segment_end_lon": float(first["la_basin_entry_segment_end_lon"]),
                "segment_end_lat": float(first["la_basin_entry_segment_end_lat"]),
                **counts,
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("segment_index")


def direction_bin_sort_key(value: object) -> int:
    text = str(value)
    match = re.match(r"^(\d{3})-", text)
    if not match:
        return 999
    return int(match.group(1))


def symmetric_norm(values: pd.Series) -> TwoSlopeNorm:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        limit = 1.0
    else:
        limit = float(np.nanquantile(np.abs(numeric), 0.95))
        limit = max(limit, 0.5)
    return TwoSlopeNorm(vcenter=0.0, vmin=-limit, vmax=limit)


def value_norm(values: pd.Series, *, diverging: bool) -> Normalize:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return TwoSlopeNorm(vcenter=0.0, vmin=-1.0, vmax=1.0) if diverging else Normalize(vmin=0.0, vmax=1.0)
    if diverging:
        return symmetric_norm(numeric)
    low = float(np.nanquantile(numeric, 0.02))
    high = float(np.nanquantile(numeric, 0.98))
    if not np.isfinite(low) or not np.isfinite(high) or low == high:
        center = float(np.nanmedian(numeric)) if len(numeric) else 0.0
        low = center - 0.5
        high = center + 0.5
    return Normalize(vmin=low, vmax=high)


def positive_robust_norm(values: pd.Series, *, upper_quantile: float) -> Normalize:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    numeric = numeric.loc[np.isfinite(numeric) & (numeric >= 0)]
    if numeric.empty:
        return Normalize(vmin=0.0, vmax=1.0)
    high = float(np.nanquantile(numeric, upper_quantile))
    if not np.isfinite(high) or high <= 0:
        high = float(np.nanmax(numeric))
    if not np.isfinite(high) or high <= 0:
        high = 1.0
    return Normalize(vmin=0.0, vmax=high)


def draw_region_context(
    ax: plt.Axes,
    regions: Sequence[RegionFeature],
    la_feature: RegionFeature,
    *,
    only_near_la: bool = False,
) -> None:
    la_bounds = la_feature.geometry.bounds
    la_extent = buffered_bounds(la_bounds, margin_fraction=0.35)
    for region in regions:
        if only_near_la and not bounds_intersect(buffered_bounds(region.geometry.bounds, margin_fraction=0.02), la_extent):
            continue
        is_target = region.long_name == la_feature.long_name
        color = "#4B5563" if is_target else "#C4CAD6"
        linewidth = 1.4 if is_target else 0.6
        alpha = 0.95 if is_target else 0.65
        for x, y in geometry_boundaries(region.geometry):
            ax.plot(x, y, color=color, linewidth=linewidth, alpha=alpha, zorder=1)


def map_extent_for_paths(data: pd.DataFrame, la_geometry: object, *, margin_fraction: float) -> tuple[float, float, float, float]:
    lons = pd.concat([pd.to_numeric(data["event_lon"], errors="coerce"), pd.to_numeric(data["sta_lon"], errors="coerce")]).dropna()
    lats = pd.concat([pd.to_numeric(data["event_lat"], errors="coerce"), pd.to_numeric(data["sta_lat"], errors="coerce")]).dropna()
    minx, miny, maxx, maxy = la_geometry.bounds
    if not lons.empty:
        minx = min(minx, float(lons.quantile(0.01)))
        maxx = max(maxx, float(lons.quantile(0.99)))
    if not lats.empty:
        miny = min(miny, float(lats.quantile(0.01)))
        maxy = max(maxy, float(lats.quantile(0.99)))
    return buffered_bounds((minx, miny, maxx, maxy), margin_fraction=margin_fraction)


def map_extent_for_geometry(geometry: object, *, margin_fraction: float) -> tuple[float, float, float, float]:
    return buffered_bounds(geometry.bounds, margin_fraction=margin_fraction)


def buffered_bounds(bounds: tuple[float, float, float, float], *, margin_fraction: float) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = bounds
    width = max(maxx - minx, 0.01)
    height = max(maxy - miny, 0.01)
    margin_x = width * margin_fraction
    margin_y = height * margin_fraction
    return (minx - margin_x, maxx + margin_x, miny - margin_y, maxy + margin_y)


def bounds_intersect(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    a_minx, a_maxx, a_miny, a_maxy = a
    b_minx, b_maxx, b_miny, b_maxy = b
    return a_minx <= b_maxx and a_maxx >= b_minx and a_miny <= b_maxy and a_maxy >= b_miny


def set_map_axes(ax: plt.Axes, extent: tuple[float, float, float, float]) -> None:
    minx, maxx, miny, maxy = extent
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(color=TOKENS["grid"], linewidth=0.5, alpha=0.55)


def add_basemap(ax: plt.Axes) -> None:
    if add_contextily_basemap is None:
        try:
            import contextily as ctx  # type: ignore

            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            ctx.add_basemap(
                ax,
                source=ctx.providers.CartoDB.Positron,
                crs="EPSG:4326",
                attribution=False,
                zoom=10,
            )
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
            return
        except Exception:
            pass
        ax.set_facecolor("#EEF2F4")
        return
    add_contextily_basemap(
        ax,
        crs="EPSG:4326",
        primary_source="CartoDB.Positron",
        fallback_sources=("Esri.WorldTopoMap", "OpenStreetMap.Mapnik", "Esri.WorldImagery"),
        attribution=False,
        cache_download=True,
        on_error="ignore",
    )


def format_map_ticks(ax: plt.Axes) -> None:
    ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
    ax.tick_params(axis="x", labelsize=7, rotation=30)
    ax.tick_params(axis="y", labelsize=7)


def coordinates_are_finite(row: object) -> bool:
    return bool(
        np.isfinite(
            [
                float(getattr(row, "event_lon")),
                float(getattr(row, "event_lat")),
                float(getattr(row, "sta_lon")),
                float(getattr(row, "sta_lat")),
            ]
        ).all()
    )


def format_panel_label(value: object) -> str:
    return str(value).replace("_minus_", " minus ")


def add_header(
    fig: plt.Figure,
    ax: plt.Axes,
    title: str,
    subtitle: str,
    *,
    top: float = 0.84,
    title_y: float = 0.985,
    subtitle_y: float = 0.925,
) -> None:
    title_wrapped = textwrap.fill(title, width=86, break_long_words=False)
    subtitle_wrapped = textwrap.fill(subtitle, width=132, break_long_words=False)
    fig.subplots_adjust(top=top)
    left = ax.get_position().x0
    fig.text(left, title_y, title_wrapped, ha="left", va="top", fontsize=13, fontweight="semibold", color=TOKENS["ink"])
    fig.text(left, subtitle_y, subtitle_wrapped, ha="left", va="top", fontsize=9, color=TOKENS["muted"])


def geometry_boundaries(geometry: object) -> Iterable[tuple[np.ndarray, np.ndarray]]:
    if hasattr(geometry, "geoms"):
        for geom in geometry.geoms:
            yield from geometry_boundaries(geom)
        return
    if hasattr(geometry, "exterior"):
        x, y = geometry.exterior.xy
        yield np.asarray(x), np.asarray(y)


def defined_region_mask(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip().str.casefold()
    return series.notna() & ~text.isin({"", "nan", "none", "null", "unknown"})


def region_order(df: pd.DataFrame, type_col: str, region_col: str) -> list[str]:
    work = df[[type_col, region_col]].drop_duplicates().copy()
    work["_type_rank"] = work[type_col].map(lambda value: REGION_TYPE_ORDER.index(str(value)) if str(value) in REGION_TYPE_ORDER else len(REGION_TYPE_ORDER))
    work = work.sort_values(["_type_rank", type_col, region_col])
    return work[region_col].astype(str).tolist()


def add_region_type_separators(ax: plt.Axes, data: pd.DataFrame, order: list[str]) -> None:
    lookup = data.drop_duplicates("station_region").set_index("station_region")["station_region_type"].to_dict()
    previous = None
    for idx, region in enumerate(order):
        current = lookup.get(region)
        if previous is not None and current != previous:
            ax.axhline(idx - 0.5, color="#344054", linewidth=0.8)
        previous = current


def fault_type_from_rake(value: object) -> str:
    try:
        rake = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if not np.isfinite(rake):
        return "unknown"
    rake = ((rake + 180.0) % 360.0) - 180.0
    if abs(rake) <= 30.0 or abs(abs(rake) - 180.0) <= 30.0:
        return "strike_slip"
    if 45.0 <= rake <= 135.0:
        return "reverse_thrust"
    if -135.0 <= rake <= -45.0:
        return "normal"
    return "oblique"


def distance_bin(value: object) -> str:
    try:
        distance = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if not np.isfinite(distance):
        return "unknown"
    for upper in (20, 40, 60, 80, 120):
        if distance < upper:
            return f"<{upper} km"
    return ">=120 km"


def direction_bin(value: object) -> str:
    try:
        angle = float(value) % 360.0
    except (TypeError, ValueError):
        return "unknown"
    if not np.isfinite(angle):
        return "unknown"
    start = int(math.floor(angle / 45.0) * 45)
    end = (start + 45) % 360
    return f"{start:03d}-{end:03d}"


def la_path_length_bin(value: object) -> str:
    try:
        length = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if not np.isfinite(length):
        return "unknown"
    if length <= 0:
        return "0 km"
    for upper in (10, 25, 50):
        if length < upper:
            return f"0-{upper} km"
    return ">=50 km"


def quantile_bin(series: pd.Series, *, bins: int, prefix: str) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()
    out = pd.Series("unknown", index=series.index, dtype=object)
    if valid.nunique() < 2:
        return out
    try:
        labels = [f"{prefix}{idx + 1}" for idx in range(bins)]
        out.loc[valid.index] = pd.qcut(valid, q=min(bins, valid.nunique()), duplicates="drop").astype(str)
        ranks = pd.qcut(valid.rank(method="first"), q=min(bins, valid.nunique()), labels=labels, duplicates="drop")
        out.loc[valid.index] = ranks.astype(str)
    except ValueError:
        pass
    return out


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator <= 0 or not np.isfinite(denominator):
        return math.nan
    return float(numerator / denominator)


def slugify(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "value"


def slugify_lowess_frac(value: float) -> str:
    return f"{float(value):g}".replace(".", "p")


def run_self_test() -> None:
    assert path_class(event_inside=True, station_inside=True, path_length_km=1.0) == "local_basin"
    assert path_class(event_inside=False, station_inside=True, path_length_km=1.0) == "regional_inbound"
    assert path_class(event_inside=True, station_inside=False, path_length_km=1.0) == "regional_outbound"
    assert path_class(event_inside=False, station_inside=False, path_length_km=1.0) == "through_basin"
    assert path_class(event_inside=False, station_inside=False, path_length_km=0.0) == "outside_basin"
    assert fault_type_from_rake(0) == "strike_slip"
    assert fault_type_from_rake(90) == "reverse_thrust"
    assert fault_type_from_rake(-90) == "normal"
    print("self_test=passed")


if __name__ == "__main__":
    raise SystemExit(main())
