#!/usr/bin/env python3
"""Build evidence-backed CVM-SI performance hypotheses.

This script is intentionally private analysis code, not part of the public
spatial-vtk API. It reads the full enriched metrics table, mapped region
polygons, and the CVM-SI material HDF5 model; then writes reproducible tables,
figures, statistical tests, and a report scaffold.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import sys
from typing import Iterable, Sequence

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from scipy.stats import kruskal, spearmanr
from shapely.geometry import LineString, Point, shape
from shapely.ops import transform as shapely_transform


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

DEFAULT_METRICS = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/tables/metrics_final_enriched.parquet")
DEFAULT_REGIONS = Path("/project2/jvidale_1700/spatial-vtk/runs/inputs/geospatial/regions_updated.geojson")
DEFAULT_MODEL_H5 = Path(
    "/project2/jvidale_1700/Salvus_HPC/codebase/slurm_material_meshes/"
    "cvmsi_0.6x1.2_slurm_meshing/cvmsi_0.6x1.2_material_CSrules.h5"
)
DEFAULT_OUTPUT = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/analysis/cvmsi_hypothesis_study")
DEFAULT_MODEL = "cvmsi_20260506_material_0p6x1p2_asdf"
DEFAULT_METRIC_SET = ("PGA", "PGV", "arias_duration", "energy_intensity")
DEFAULT_BANDS = ("1-2 sec", "2-3 sec", "3-5 sec")
FIELD_INDEX = {"qkappa": 0, "qmu": 1, "rho": 2, "vp": 3, "vs": 4}
WGS84 = "EPSG:4326"
WEB_MERCATOR = "EPSG:3857"
CALIFORNIA_ALBERS = "EPSG:3310"
CVM_UTM = "EPSG:32611"
DEFAULT_BASEMAP_SOURCE = "CartoDB.Positron"
DEFAULT_BASEMAP_ZOOM = 9
RANDOM_SEED = 20260630
MIN_GROUP_ROWS = 120

COLORS = {
    "ink": "#1f2937",
    "muted": "#64748b",
    "grid": "#d9dee8",
    "blue": "#356aa0",
    "green": "#2f8f5b",
    "gold": "#d99a00",
    "red": "#b64040",
    "purple": "#7b5ea7",
    "gray": "#8a94a6",
}
REGION_TYPE_COLORS = {
    "Basin": "#356aa0",
    "Valley": "#2f8f5b",
    "Hills": "#d99a00",
    "Mountains": "#b64040",
    "Other": "#7b5ea7",
    "Offshore": "#5899a8",
    "unknown": "#8a94a6",
}


@dataclass(frozen=True)
class RegionRecord:
    name: str
    short_name: str
    region_type: str
    geometry_lonlat: object
    geometry_projected: object


@dataclass
class ModelSampler:
    h5_path: Path
    node_stride: int = 2

    def __post_init__(self) -> None:
        if self.node_stride < 1:
            raise ValueError("node_stride must be >= 1")
        self.coords: np.ndarray | None = None
        self.tree: cKDTree | None = None
        self.values: dict[str, np.ndarray] = {}
        self.bounds_xyz: tuple[float, float, float, float, float, float] | None = None

    def load(self) -> None:
        if self.tree is not None:
            return
        with h5py.File(self.h5_path, "r") as h5:
            coords = np.asarray(h5["/MODEL/coordinates"][:: self.node_stride], dtype=np.float64).reshape(-1, 3)
            data = h5["/MODEL/data"]
            values = {
                field: np.asarray(data[:: self.node_stride, index, :], dtype=np.float32).reshape(-1)
                for field, index in FIELD_INDEX.items()
                if field in {"rho", "vp", "vs"}
            }
        finite = np.isfinite(coords).all(axis=1)
        for value in values.values():
            finite &= np.isfinite(value)
        self.coords = coords[finite]
        self.values = {field: value[finite] for field, value in values.items()}
        minx, miny, minz = np.nanmin(self.coords, axis=0)
        maxx, maxy, maxz = np.nanmax(self.coords, axis=0)
        self.bounds_xyz = (float(minx), float(miny), float(minz), float(maxx), float(maxy), float(maxz))
        self.tree = cKDTree(self.coords)

    def sample_xyz(self, points_xyz: np.ndarray) -> pd.DataFrame:
        self.load()
        assert self.tree is not None
        assert self.coords is not None
        distances, indices = self.tree.query(np.asarray(points_xyz, dtype=np.float64), k=1, workers=1)
        out = pd.DataFrame({"sample_distance_m": distances.astype(float)})
        for field, values in self.values.items():
            out[field] = values[indices].astype(float)
        return out


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--regions", type=Path, default=DEFAULT_REGIONS)
    parser.add_argument("--model-h5", type=Path, default=DEFAULT_MODEL_H5)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--metric", action="append", dest="metrics_focus", default=None)
    parser.add_argument("--band", action="append", dest="bands", default=None)
    parser.add_argument("--model-node-stride", type=int, default=2)
    parser.add_argument("--skip-model-sampling", action="store_true")
    parser.add_argument("--refresh-model-samples", action="store_true")
    parser.add_argument(
        "--skip-inline-mixed-effects",
        action="store_true",
        help="Write pair/summary tables and figures without running this script's inline diagnostic mixed-effects fits.",
    )
    parser.add_argument("--no-cross-sections", action="store_true")
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
    parser.add_argument("--permutation-samples", type=int, default=3000)
    parser.add_argument("--basemap-source", default=DEFAULT_BASEMAP_SOURCE)
    parser.add_argument("--basemap-zoom", type=int, default=DEFAULT_BASEMAP_ZOOM)
    parser.add_argument("--basemap-cache-dir", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = args.output_dir.expanduser().resolve()
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    report_dir = output_dir / "report"
    for directory in (tables_dir, figures_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)
    basemap_cache_dir = args.basemap_cache_dir or (output_dir / "basemap_cache")

    metrics_focus = tuple(args.metrics_focus or DEFAULT_METRIC_SET)
    bands = tuple(args.bands or DEFAULT_BANDS)
    rng = np.random.default_rng(RANDOM_SEED)
    set_plot_theme()

    regions = load_regions(args.regions)
    raw = load_metrics(args.metrics, model=args.model, metrics_focus=metrics_focus, bands=bands)
    pairs = collapse_components(raw)
    paths = build_path_features(pairs, regions)
    pairs = pairs.merge(paths, on=["event_id", "station"], how="left", validate="many_to_one")

    model_samples_path = tables_dir / "station_model_samples.parquet"
    if args.skip_model_sampling:
        station_model = pd.DataFrame()
    elif model_samples_path.exists() and not args.refresh_model_samples:
        station_model = pd.read_parquet(model_samples_path)
    else:
        sampler = ModelSampler(args.model_h5, node_stride=args.model_node_stride)
        station_model = sample_model_at_stations(pairs, sampler)
        station_model.to_parquet(model_samples_path, index=False)

    if not station_model.empty:
        model_merge = station_model.drop(columns=[column for column in ("sta_lon", "sta_lat") if column in station_model.columns])
        pairs = pairs.merge(model_merge, on="station", how="left", validate="many_to_one")
        pairs = add_model_mismatch_columns(pairs)

    station_summary = build_station_summary(pairs)
    global_summary = build_global_summary(pairs, rng, args.bootstrap_samples)
    region_summary = build_region_summary(pairs, rng, args.bootstrap_samples)
    geology_summary = build_geology_summary(pairs, rng, args.bootstrap_samples)
    path_summary = build_path_summary(pairs, rng, args.bootstrap_samples)
    band_contrasts = build_band_contrasts(pairs)
    band_contrast_summary = summarize_band_contrasts(band_contrasts, rng, args.bootstrap_samples)
    tests = run_statistical_tests(pairs, station_summary, band_contrasts, rng, args.permutation_samples)
    if args.skip_inline_mixed_effects:
        mixed_effects = pd.DataFrame()
        mixed_effect_variance = pd.DataFrame()
    else:
        mixed_effects, mixed_effect_variance = run_mixed_effects_models(pairs)

    write_tables(
        tables_dir,
        pairs=pairs,
        paths=paths,
        station_summary=station_summary,
        global_summary=global_summary,
        region_summary=region_summary,
        geology_summary=geology_summary,
        path_summary=path_summary,
        band_contrasts=band_contrasts,
        band_contrast_summary=band_contrast_summary,
        tests=tests,
        mixed_effects=mixed_effects,
        mixed_effect_variance=mixed_effect_variance,
    )

    figure_paths = []
    figure_paths.append(
        plot_observed_and_residual_maps(
            pairs,
            regions,
            figures_dir,
            basemap_source=str(args.basemap_source),
            basemap_cache_dir=basemap_cache_dir,
            basemap_zoom=args.basemap_zoom,
        )
    )
    figure_paths.append(plot_region_period_heatmap(region_summary, figures_dir))
    figure_paths.append(plot_path_period_contrasts(band_contrasts, figures_dir))
    if not station_model.empty:
        figure_paths.append(plot_model_site_mismatch(station_summary, figures_dir))
    figure_paths.append(plot_geology_effects(geology_summary, figures_dir))
    if not args.skip_model_sampling and not args.no_cross_sections:
        sampler = ModelSampler(args.model_h5, node_stride=args.model_node_stride)
        figure_paths.append(
            plot_model_cross_sections(
                pairs,
                regions,
                sampler,
                figures_dir,
                basemap_source=str(args.basemap_source),
                basemap_cache_dir=basemap_cache_dir,
                basemap_zoom=args.basemap_zoom,
            )
        )

    manifest = {
        "inputs": {
            "metrics": str(args.metrics),
            "regions": str(args.regions),
            "model_h5": str(args.model_h5),
            "model": args.model,
            "metrics_focus": list(metrics_focus),
            "bands": list(bands),
            "basemap_source": str(args.basemap_source),
            "basemap_cache_dir": str(basemap_cache_dir),
            "basemap_zoom": args.basemap_zoom,
        },
        "outputs": {
            "output_dir": str(output_dir),
            "tables_dir": str(tables_dir),
            "figures_dir": str(figures_dir),
            "report_dir": str(report_dir),
        },
        "counts": {
            "raw_rows": int(len(raw)),
            "event_station_metric_band_rows": int(len(pairs)),
            "events": int(pairs["event_id"].nunique()),
            "stations": int(pairs["station"].nunique()),
            "regions": int(len(regions)),
        },
        "model_sampling": {
            "skipped": bool(args.skip_model_sampling),
            "node_stride": int(args.model_node_stride),
            "station_model_samples": str(model_samples_path) if not station_model.empty else None,
        },
        "figures": [str(path) for path in figure_paths],
        "random_seed": RANDOM_SEED,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report_scaffold(
        report_dir / "cvmsi_hypotheses_report.md",
        manifest,
        global_summary,
        region_summary,
        geology_summary,
        path_summary,
        band_contrast_summary,
        tests,
        mixed_effects,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def set_plot_theme() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": COLORS["grid"],
            "axes.labelcolor": COLORS["ink"],
            "axes.titlecolor": COLORS["ink"],
            "axes.labelsize": 12,
            "axes.titlesize": 14,
            "font.size": 11.5,
            "font.family": "sans-serif",
            "font.sans-serif": ["Aptos", "Inter", "Segoe UI", "DejaVu Sans", "Arial", "sans-serif"],
            "xtick.labelsize": 10.5,
            "ytick.labelsize": 10.5,
            "xtick.color": COLORS["muted"],
            "ytick.color": COLORS["muted"],
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": COLORS["grid"],
            "grid.linewidth": 0.7,
            "grid.alpha": 0.75,
        }
    )


def load_regions(path: Path) -> list[RegionRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    transformer = Transformer.from_crs(WGS84, CALIFORNIA_ALBERS, always_xy=True)
    records: list[RegionRecord] = []
    for index, feature in enumerate(payload.get("features", []), start=1):
        props = feature.get("properties") or {}
        geom = shape(feature.get("geometry"))
        name = str(props.get("long_name") or props.get("name") or props.get("short_name") or f"region_{index}").strip()
        short_name = str(props.get("short_name") or name).strip()
        region_type = str(props.get("region_type") or "unknown").strip()
        records.append(
            RegionRecord(
                name=name,
                short_name=short_name,
                region_type=region_type,
                geometry_lonlat=geom,
                geometry_projected=shapely_transform(transformer.transform, geom),
            )
        )
    if not records:
        raise ValueError(f"No GeoJSON features found in {path}")
    return records


def load_metrics(path: Path, *, model: str, metrics_focus: Sequence[str], bands: Sequence[str]) -> pd.DataFrame:
    import pyarrow.parquet as pq

    wanted = [
        "event_id",
        "station",
        "component",
        "model",
        "metric",
        "band",
        "log2_residual",
        "value_obs",
        "value_syn",
        "event_lat",
        "event_lon",
        "sta_lat",
        "sta_lon",
        "distance_km",
        "azimuth_deg",
        "backazimuth_deg",
        "event_name",
        "magnitude",
        "event_depth_km",
        "strike",
        "dip",
        "rake",
        "event_region",
        "event_region_type",
        "event_geomorphology",
        "station_region",
        "station_region_type",
        "station_geomorphology",
        "Vs30",
        "geologic_description",
    ]
    available = set(pq.ParquetFile(path).schema.names)
    columns = [column for column in wanted if column in available]
    df = pd.read_parquet(path, columns=columns)
    df = df.loc[
        df["model"].astype(str).eq(str(model))
        & df["metric"].astype(str).isin(metrics_focus)
        & df["band"].astype(str).isin(bands)
    ].copy()
    for column in [
        "log2_residual",
        "value_obs",
        "value_syn",
        "event_lat",
        "event_lon",
        "sta_lat",
        "sta_lon",
        "distance_km",
        "azimuth_deg",
        "backazimuth_deg",
        "magnitude",
        "event_depth_km",
        "strike",
        "dip",
        "rake",
        "Vs30",
    ]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["event_id", "station", "metric", "band", "log2_residual", "event_lat", "event_lon", "sta_lat", "sta_lon"])
    for column in ["event_id", "station", "metric", "band", "component"]:
        if column in df.columns:
            df[column] = df[column].astype(str)
    return df


def first_valid(values: pd.Series) -> object:
    series = values.dropna()
    if series.empty:
        return np.nan
    return series.iloc[0]


def collapse_components(df: pd.DataFrame) -> pd.DataFrame:
    keys = ["event_id", "station", "metric", "band"]
    first_columns = [
        "model",
        "event_name",
        "event_lat",
        "event_lon",
        "sta_lat",
        "sta_lon",
        "distance_km",
        "azimuth_deg",
        "backazimuth_deg",
        "magnitude",
        "event_depth_km",
        "strike",
        "dip",
        "rake",
        "event_region",
        "event_region_type",
        "event_geomorphology",
        "station_region",
        "station_region_type",
        "station_geomorphology",
        "Vs30",
        "geologic_description",
    ]
    agg: dict[str, tuple[str, object]] = {
        "log2_residual": ("log2_residual", "median"),
        "value_obs": ("value_obs", "median"),
        "value_syn": ("value_syn", "median"),
        "components": ("component", lambda x: ",".join(sorted(set(str(v) for v in x.dropna())))),
        "component_count": ("component", "nunique"),
    }
    for column in first_columns:
        if column in df.columns:
            agg[column] = (column, first_valid)
    out = df.groupby(keys, as_index=False).agg(**agg)
    out["obs_log2"] = np.where(out["value_obs"].gt(0), np.log2(out["value_obs"]), np.nan)
    out["syn_log2"] = np.where(out["value_syn"].gt(0), np.log2(out["value_syn"]), np.nan)
    for value_col, centered_col in [
        ("log2_residual", "residual_event_centered"),
        ("obs_log2", "obs_event_centered"),
        ("syn_log2", "syn_event_centered"),
    ]:
        out[centered_col] = out[value_col] - out.groupby(["event_id", "metric", "band"])[value_col].transform("median")
    out["region_type_station"] = out.get("station_region_type", "unknown").fillna("unknown").astype(str)
    out["station_region"] = out.get("station_region", "unknown").fillna("unknown").astype(str)
    out["event_region"] = out.get("event_region", "unknown").fillna("unknown").astype(str)
    out["event_region_type"] = out.get("event_region_type", "unknown").fillna("unknown").astype(str)
    out["geologic_description"] = out.get("geologic_description", "unknown").fillna("unknown").astype(str)
    return out


def build_path_features(pairs: pd.DataFrame, regions: list[RegionRecord]) -> pd.DataFrame:
    transformer = Transformer.from_crs(WGS84, CALIFORNIA_ALBERS, always_xy=True)
    base_cols = [
        "event_id",
        "station",
        "event_lon",
        "event_lat",
        "sta_lon",
        "sta_lat",
        "event_region",
        "event_region_type",
        "station_region",
        "station_region_type",
    ]
    base = pairs[base_cols].drop_duplicates(["event_id", "station"]).copy()
    rows = []
    for row in base.itertuples(index=False):
        event_xy = transformer.transform(float(row.event_lon), float(row.event_lat))
        station_xy = transformer.transform(float(row.sta_lon), float(row.sta_lat))
        line = LineString([event_xy, station_xy])
        total_km = max(float(line.length) / 1000.0, 1e-6)
        by_region: dict[str, float] = {}
        by_type: dict[str, float] = {}
        for region in regions:
            if not line.intersects(region.geometry_projected):
                continue
            length_km = float(line.intersection(region.geometry_projected).length) / 1000.0
            if length_km <= 0.05:
                continue
            by_region[region.name] = by_region.get(region.name, 0.0) + length_km
            by_type[region.region_type] = by_type.get(region.region_type, 0.0) + length_km
        max_region = max(by_region, key=by_region.get) if by_region else "unmapped"
        max_region_length = float(by_region.get(max_region, 0.0))
        basin_km = sum(length for name, length in by_type.items() if name == "Basin")
        mountain_km = sum(length for name, length in by_type.items() if name == "Mountains")
        la_basin_km = float(by_region.get("Los Angeles Basin", 0.0))
        san_fernando_km = float(by_region.get("San Fernando Basin", 0.0))
        san_gabriel_km = float(by_region.get("San Gabriel Basin", 0.0))
        path_class = classify_path(
            event_region=str(row.event_region),
            station_region=str(row.station_region),
            event_region_type=str(row.event_region_type),
            station_region_type=str(row.station_region_type),
            basin_km=basin_km,
            la_basin_km=la_basin_km,
            total_km=total_km,
        )
        rows.append(
            {
                "event_id": row.event_id,
                "station": row.station,
                "path_distance_km": total_km,
                "path_max_region": max_region,
                "path_max_region_km": max_region_length,
                "path_basin_km": float(basin_km),
                "path_mountains_km": float(mountain_km),
                "path_la_basin_km": la_basin_km,
                "path_san_fernando_basin_km": san_fernando_km,
                "path_san_gabriel_basin_km": san_gabriel_km,
                "path_basin_fraction": float(np.clip(basin_km / total_km, 0.0, 1.0)),
                "path_mountains_fraction": float(np.clip(mountain_km / total_km, 0.0, 1.0)),
                "path_la_basin_fraction": float(np.clip(la_basin_km / total_km, 0.0, 1.0)),
                "path_class": path_class,
            }
        )
    return pd.DataFrame(rows)


def classify_path(
    *,
    event_region: str,
    station_region: str,
    event_region_type: str,
    station_region_type: str,
    basin_km: float,
    la_basin_km: float,
    total_km: float,
) -> str:
    basin_fraction = basin_km / max(total_km, 1e-6)
    if event_region == "Los Angeles Basin" and station_region == "Los Angeles Basin":
        return "LA basin local"
    if station_region == "Los Angeles Basin" and la_basin_km >= 5.0:
        return "terminates in LA basin"
    if la_basin_km >= 15.0:
        return "crosses LA basin"
    if basin_fraction >= 0.35 or station_region_type == "Basin" or event_region_type == "Basin":
        return "other basin-influenced"
    if station_region_type == "Mountains" and event_region_type == "Mountains":
        return "mountain to mountain"
    if event_region == "Offshore":
        return "offshore source"
    return "mixed non-basin"


def sample_model_at_stations(pairs: pd.DataFrame, sampler: ModelSampler) -> pd.DataFrame:
    stations = pairs[["station", "sta_lon", "sta_lat"]].drop_duplicates("station").copy()
    transformer = Transformer.from_crs(WGS84, CVM_UTM, always_xy=True)
    x, y = transformer.transform(stations["sta_lon"].to_numpy(dtype=float), stations["sta_lat"].to_numpy(dtype=float))
    depths = [0.0, -500.0, -1000.0, -3000.0]
    pieces = []
    for depth in depths:
        xyz = np.column_stack([x, y, np.full_like(x, depth, dtype=float)])
        sampled = sampler.sample_xyz(xyz)
        sampled = sampled.add_prefix(f"model_{int(abs(depth))}m_")
        sampled["station"] = stations["station"].to_numpy()
        sampled["station_model_sample_depth_m"] = depth
        pieces.append(sampled)
    out = stations.copy()
    for sampled in pieces:
        depth = int(abs(float(sampled["station_model_sample_depth_m"].iloc[0])))
        keep = sampled.drop(columns=["station_model_sample_depth_m"])
        out = out.merge(keep, on="station", how="left", validate="one_to_one")
        if f"model_{depth}m_rho" in out.columns and f"model_{depth}m_vs" in out.columns:
            out[f"model_{depth}m_impedance"] = out[f"model_{depth}m_rho"] * out[f"model_{depth}m_vs"]
    return out


def add_model_mismatch_columns(pairs: pd.DataFrame) -> pd.DataFrame:
    out = pairs.copy()
    if "model_0m_vs" in out.columns and "Vs30" in out.columns:
        out["model_vs30_ratio"] = out["model_0m_vs"] / out["Vs30"].replace(0, np.nan)
        out["log2_model_vs30_ratio"] = np.log2(out["model_vs30_ratio"].where(out["model_vs30_ratio"].gt(0)))
    if "model_1000m_vs" in out.columns and "model_0m_vs" in out.columns:
        out["model_vs_gradient_0_1000m"] = out["model_1000m_vs"] - out["model_0m_vs"]
    if "model_1000m_impedance" in out.columns and "model_0m_impedance" in out.columns:
        out["model_impedance_gradient_0_1000m"] = out["model_1000m_impedance"] - out["model_0m_impedance"]
    return out


def build_station_summary(pairs: pd.DataFrame) -> pd.DataFrame:
    agg_map = {
        "sta_lon": ("sta_lon", "median"),
        "sta_lat": ("sta_lat", "median"),
        "station_region": ("station_region", first_valid),
        "station_region_type": ("station_region_type", first_valid),
        "geologic_description": ("geologic_description", first_valid),
        "Vs30": ("Vs30", "median"),
        "events": ("event_id", "nunique"),
        "rows": ("log2_residual", "size"),
        "median_residual": ("log2_residual", "median"),
        "median_residual_event_centered": ("residual_event_centered", "median"),
        "median_observed_event_centered": ("obs_event_centered", "median"),
    }
    for column in pairs.columns:
        if column.startswith("model_") or column in {"model_vs30_ratio", "log2_model_vs30_ratio", "model_vs_gradient_0_1000m", "model_impedance_gradient_0_1000m"}:
            agg_map[column] = (column, "median")
    summary = pairs.groupby(["station", "metric", "band"], as_index=False).agg(**agg_map)
    return summary


def build_global_summary(pairs: pd.DataFrame, rng: np.random.Generator, samples: int) -> pd.DataFrame:
    return summarize_groups(pairs, ["metric", "band"], "log2_residual", rng, samples)


def build_region_summary(pairs: pd.DataFrame, rng: np.random.Generator, samples: int) -> pd.DataFrame:
    return summarize_groups(pairs, ["metric", "band", "station_region_type", "station_region"], "residual_event_centered", rng, samples)


def build_geology_summary(pairs: pd.DataFrame, rng: np.random.Generator, samples: int) -> pd.DataFrame:
    work = pairs.loc[pairs["geologic_description"].notna()].copy()
    return summarize_groups(work, ["metric", "band", "geologic_description"], "residual_event_centered", rng, samples)


def build_path_summary(pairs: pd.DataFrame, rng: np.random.Generator, samples: int) -> pd.DataFrame:
    return summarize_groups(pairs, ["metric", "band", "path_class"], "residual_event_centered", rng, samples)


def summarize_groups(
    df: pd.DataFrame,
    group_cols: Sequence[str],
    value_col: str,
    rng: np.random.Generator,
    samples: int,
) -> pd.DataFrame:
    rows = []
    for keys, group in df.groupby(list(group_cols), dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        values = pd.to_numeric(group[value_col], errors="coerce").dropna().to_numpy(dtype=float)
        if values.size == 0:
            continue
        lo, hi = bootstrap_ci(values, rng, samples)
        row = {column: value for column, value in zip(group_cols, keys)}
        row.update(
            {
                "value_column": value_col,
                "rows": int(values.size),
                "events": int(group["event_id"].nunique()) if "event_id" in group else np.nan,
                "stations": int(group["station"].nunique()) if "station" in group else np.nan,
                "median": float(np.nanmedian(values)),
                "mean": float(np.nanmean(values)),
                "q25": float(np.nanpercentile(values, 25)),
                "q75": float(np.nanpercentile(values, 75)),
                "bootstrap_ci_low": lo,
                "bootstrap_ci_high": hi,
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def bootstrap_ci(values: np.ndarray, rng: np.random.Generator, samples: int, alpha: float = 0.05) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return (float("nan"), float("nan"))
    if values.size == 1 or samples <= 0:
        value = float(np.nanmedian(values))
        return (value, value)
    indices = rng.integers(0, values.size, size=(samples, values.size))
    medians = np.nanmedian(values[indices], axis=1)
    low, high = np.nanpercentile(medians, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(low), float(high)


def build_band_contrasts(pairs: pd.DataFrame) -> pd.DataFrame:
    meta_cols = [
        "event_id",
        "station",
        "metric",
        "sta_lon",
        "sta_lat",
        "station_region",
        "station_region_type",
        "event_region",
        "event_region_type",
        "geologic_description",
        "path_class",
        "path_basin_km",
        "path_la_basin_km",
        "path_basin_fraction",
        "path_la_basin_fraction",
    ]
    if "log2_model_vs30_ratio" in pairs.columns:
        meta_cols.append("log2_model_vs30_ratio")
    wide = pairs.pivot_table(
        index=["event_id", "station", "metric"],
        columns="band",
        values="residual_event_centered",
        aggfunc="median",
    ).reset_index()
    if {"1-2 sec", "3-5 sec"}.issubset(wide.columns):
        wide["delta_3_5_minus_1_2"] = wide["3-5 sec"] - wide["1-2 sec"]
    if {"1-2 sec", "2-3 sec"}.issubset(wide.columns):
        wide["delta_2_3_minus_1_2"] = wide["2-3 sec"] - wide["1-2 sec"]
    meta = pairs[[column for column in meta_cols if column in pairs.columns]].drop_duplicates(["event_id", "station", "metric"])
    out = wide.merge(meta, on=["event_id", "station", "metric"], how="left", validate="one_to_one")
    return out.replace([np.inf, -np.inf], np.nan)


def summarize_band_contrasts(band_contrasts: pd.DataFrame, rng: np.random.Generator, samples: int) -> pd.DataFrame:
    rows = []
    for contrast_col in ["delta_3_5_minus_1_2", "delta_2_3_minus_1_2"]:
        if contrast_col not in band_contrasts.columns:
            continue
        for keys, group in band_contrasts.groupby(["metric", "path_class"], dropna=False):
            values = pd.to_numeric(group[contrast_col], errors="coerce").dropna().to_numpy(dtype=float)
            if values.size == 0:
                continue
            lo, hi = bootstrap_ci(values, rng, samples)
            rows.append(
                {
                    "metric": keys[0],
                    "path_class": keys[1],
                    "contrast": contrast_col,
                    "rows": int(values.size),
                    "events": int(group["event_id"].nunique()),
                    "stations": int(group["station"].nunique()),
                    "median": float(np.nanmedian(values)),
                    "bootstrap_ci_low": lo,
                    "bootstrap_ci_high": hi,
                }
            )
    return pd.DataFrame(rows)


def run_statistical_tests(
    pairs: pd.DataFrame,
    station_summary: pd.DataFrame,
    band_contrasts: pd.DataFrame,
    rng: np.random.Generator,
    permutation_samples: int,
) -> pd.DataFrame:
    tests = []
    for metric, band in [("PGA", "3-5 sec"), ("arias_duration", "3-5 sec"), ("PGA", "1-2 sec")]:
        subset = pairs.loc[pairs["metric"].eq(metric) & pairs["band"].eq(band)].copy()
        groups = []
        labels = []
        for label, group in subset.groupby("geologic_description"):
            values = group["residual_event_centered"].dropna().to_numpy(dtype=float)
            if values.size >= MIN_GROUP_ROWS:
                groups.append(values)
                labels.append(label)
        if len(groups) >= 3:
            stat, pvalue = kruskal(*groups)
            tests.append(
                {
                    "test": "kruskal_geologic_units",
                    "metric": metric,
                    "band": band,
                    "statistic": float(stat),
                    "pvalue": float(pvalue),
                    "groups": int(len(groups)),
                    "rows": int(sum(group.size for group in groups)),
                    "explanation": "Tests whether event-demeaned residual distributions differ across geologic map units.",
                }
            )

    if "log2_model_vs30_ratio" in station_summary.columns:
        for metric, band in [("PGA", "3-5 sec"), ("PGA", "1-2 sec"), ("arias_duration", "3-5 sec")]:
            subset = station_summary.loc[station_summary["metric"].eq(metric) & station_summary["band"].eq(band)]
            x = pd.to_numeric(subset["log2_model_vs30_ratio"], errors="coerce")
            y = pd.to_numeric(subset["median_residual_event_centered"], errors="coerce")
            valid = x.notna() & y.notna()
            if valid.sum() >= 20:
                rho, pvalue = spearmanr(x[valid], y[valid])
                tests.append(
                    {
                        "test": "spearman_model_vs30_mismatch",
                        "metric": metric,
                        "band": band,
                        "statistic": float(rho),
                        "pvalue": float(pvalue),
                        "groups": np.nan,
                        "rows": int(valid.sum()),
                        "explanation": "Tests whether stations where the CVM-SI surface Vs is high relative to Vs30 have systematically different residuals.",
                    }
                )

    for metric in ["PGA", "arias_duration", "PGV"]:
        subset = band_contrasts.loc[band_contrasts["metric"].eq(metric)].copy()
        if "delta_3_5_minus_1_2" not in subset.columns:
            continue
        target = subset.loc[subset["path_class"].isin(["terminates in LA basin", "crosses LA basin"]), "delta_3_5_minus_1_2"].dropna().to_numpy(dtype=float)
        reference = subset.loc[subset["path_class"].isin(["mountain to mountain", "mixed non-basin"]), "delta_3_5_minus_1_2"].dropna().to_numpy(dtype=float)
        if target.size >= 30 and reference.size >= 30:
            diff, pvalue = permutation_median_difference(target, reference, rng, permutation_samples)
            tests.append(
                {
                    "test": "permutation_la_path_band_contrast",
                    "metric": metric,
                    "band": "3-5 sec minus 1-2 sec",
                    "statistic": float(diff),
                    "pvalue": float(pvalue),
                    "groups": 2,
                    "rows": int(target.size + reference.size),
                    "explanation": "Compares period-dependence in LA-basin-influenced paths against non-basin mountain/mixed paths by random relabeling.",
                }
            )
    return pd.DataFrame(tests)


def permutation_median_difference(
    target: np.ndarray,
    reference: np.ndarray,
    rng: np.random.Generator,
    samples: int,
) -> tuple[float, float]:
    target = np.asarray(target, dtype=float)
    reference = np.asarray(reference, dtype=float)
    observed = float(np.nanmedian(target) - np.nanmedian(reference))
    pooled = np.concatenate([target, reference])
    n_target = target.size
    if samples <= 0:
        return observed, float("nan")
    extreme = 0
    for _ in range(samples):
        perm = rng.permutation(pooled)
        diff = float(np.nanmedian(perm[:n_target]) - np.nanmedian(perm[n_target:]))
        if abs(diff) >= abs(observed):
            extreme += 1
    return observed, float((extreme + 1) / (samples + 1))


def run_mixed_effects_models(pairs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit mixed-effects models for the main residual hypotheses.

    The diagnostic maps use event-demeaned residuals. These models instead fit
    raw log2 residuals while estimating station and event random intercept
    variance, which is closer to the inference problem implied by obs/syn
    validation.
    """

    try:
        import statsmodels.formula.api as smf
    except Exception as exc:  # pragma: no cover - environment dependent
        return (
            pd.DataFrame(
                [
                    {
                        "model_name": "mixed_effects_unavailable",
                        "metric": "all",
                        "band_scope": "all",
                        "term": "error",
                        "coef": np.nan,
                        "se": np.nan,
                        "z": np.nan,
                        "pvalue": np.nan,
                        "ci_low": np.nan,
                        "ci_high": np.nan,
                        "nobs": 0,
                        "converged": False,
                        "note": f"statsmodels import failed: {exc!r}",
                    }
                ]
            ),
            pd.DataFrame(),
        )

    fixed_rows: list[dict[str, object]] = []
    variance_rows: list[dict[str, object]] = []
    for metric in ["PGA", "PGV", "arias_duration"]:
        metric_rows = prepare_mixed_effects_frame(pairs.loc[pairs["metric"].eq(metric)].copy())
        if len(metric_rows) >= 500:
            fit_mixed_effects_model(
                smf=smf,
                data=metric_rows,
                formula=(
                    "log2_residual ~ C(band) + C(station_region_type) + "
                    "C(path_class) + path_basin_fraction + path_la_basin_fraction"
                ),
                model_name="spatial_path",
                metric=metric,
                band_scope="all_bands",
                fixed_rows=fixed_rows,
                variance_rows=variance_rows,
            )
        site_rows = metric_rows.dropna(subset=["log2_model_vs30_ratio_z"]).copy()
        if len(site_rows) >= 500:
            fit_mixed_effects_model(
                smf=smf,
                data=site_rows,
                formula="log2_residual ~ C(band) + C(station_region_type) + log2_model_vs30_ratio_z",
                model_name="site_velocity_mismatch",
                metric=metric,
                band_scope="all_bands_with_vs30",
                fixed_rows=fixed_rows,
                variance_rows=variance_rows,
            )
        for band in ["1-2 sec", "3-5 sec"]:
            geology_rows = prepare_geology_mixed_effects_frame(metric_rows.loc[metric_rows["band"].eq(band)].copy())
            if len(geology_rows) >= 500 and geology_rows["geology_focus"].nunique() >= 3:
                fit_mixed_effects_model(
                    smf=smf,
                    data=geology_rows,
                    formula="log2_residual ~ C(geology_focus)",
                    model_name="geology",
                    metric=metric,
                    band_scope=band,
                    fixed_rows=fixed_rows,
                    variance_rows=variance_rows,
                )
    return pd.DataFrame(fixed_rows), pd.DataFrame(variance_rows)


def prepare_mixed_effects_frame(df: pd.DataFrame) -> pd.DataFrame:
    keep = [
        "log2_residual",
        "event_id",
        "station",
        "band",
        "station_region_type",
        "path_class",
        "path_basin_fraction",
        "path_la_basin_fraction",
        "geologic_description",
        "log2_model_vs30_ratio",
    ]
    out = df[[column for column in keep if column in df.columns]].copy()
    out = out.replace([np.inf, -np.inf], np.nan).dropna(subset=["log2_residual", "event_id", "station", "band"])
    out["event_id"] = out["event_id"].astype(str)
    out["station"] = out["station"].astype(str)
    out["band"] = pd.Categorical(out["band"].astype(str), categories=list(DEFAULT_BANDS), ordered=True)
    out["station_region_type"] = out.get("station_region_type", "unknown").fillna("unknown").astype(str)
    out["path_class"] = out.get("path_class", "unknown").fillna("unknown").astype(str)
    out["path_basin_fraction"] = pd.to_numeric(out.get("path_basin_fraction", 0.0), errors="coerce").fillna(0.0)
    out["path_la_basin_fraction"] = pd.to_numeric(out.get("path_la_basin_fraction", 0.0), errors="coerce").fillna(0.0)
    if "log2_model_vs30_ratio" in out.columns:
        values = pd.to_numeric(out["log2_model_vs30_ratio"], errors="coerce")
        std = float(values.std(skipna=True))
        if np.isfinite(std) and std > 0:
            out["log2_model_vs30_ratio_z"] = (values - float(values.mean(skipna=True))) / std
        else:
            out["log2_model_vs30_ratio_z"] = np.nan
    else:
        out["log2_model_vs30_ratio_z"] = np.nan
    return out


def prepare_geology_mixed_effects_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["geologic_description"] = out.get("geologic_description", "unknown").fillna("unknown").astype(str)
    support = out["geologic_description"].value_counts()
    keep_units = set(support[support >= 180].index)
    out["geology_focus"] = np.where(out["geologic_description"].isin(keep_units), out["geologic_description"], "other_geology")
    return out


def fit_mixed_effects_model(
    *,
    smf: object,
    data: pd.DataFrame,
    formula: str,
    model_name: str,
    metric: str,
    band_scope: str,
    fixed_rows: list[dict[str, object]],
    variance_rows: list[dict[str, object]],
) -> None:
    data = data.copy()
    data = data.dropna(subset=["log2_residual", "station", "event_id"])
    try:
        model = smf.mixedlm(
            formula,
            data=data,
            groups=data["station"],
            re_formula="1",
            vc_formula={"event": "0 + C(event_id)"},
        )
        result = model.fit(reml=False, method="lbfgs", maxiter=200, disp=False)
        params = result.fe_params
        bse = result.bse_fe
        conf = result.conf_int()
        for term, coef in params.items():
            se = float(bse.get(term, np.nan))
            fixed_rows.append(
                {
                    "model_name": model_name,
                    "metric": metric,
                    "band_scope": band_scope,
                    "term": term,
                    "coef": float(coef),
                    "se": se,
                    "z": float(coef / se) if np.isfinite(se) and se > 0 else np.nan,
                    "pvalue": float(result.pvalues.get(term, np.nan)),
                    "ci_low": float(conf.loc[term, 0]) if term in conf.index else np.nan,
                    "ci_high": float(conf.loc[term, 1]) if term in conf.index else np.nan,
                    "nobs": int(result.nobs),
                    "converged": bool(getattr(result, "converged", False)),
                    "note": "",
                }
            )
        station_var = float(result.cov_re.iloc[0, 0]) if result.cov_re.shape[0] else np.nan
        event_var = float(result.vcomp[0]) if len(result.vcomp) else np.nan
        variance_rows.append(
            {
                "model_name": model_name,
                "metric": metric,
                "band_scope": band_scope,
                "nobs": int(result.nobs),
                "station_random_intercept_var": station_var,
                "event_random_intercept_var": event_var,
                "residual_var": float(result.scale),
                "aic": float(result.aic),
                "bic": float(result.bic),
                "converged": bool(getattr(result, "converged", False)),
                "note": "",
            }
        )
    except Exception as exc:
        fixed_rows.append(
            {
                "model_name": model_name,
                "metric": metric,
                "band_scope": band_scope,
                "term": "model_fit_error",
                "coef": np.nan,
                "se": np.nan,
                "z": np.nan,
                "pvalue": np.nan,
                "ci_low": np.nan,
                "ci_high": np.nan,
                "nobs": int(len(data)),
                "converged": False,
                "note": repr(exc),
            }
        )


def write_tables(tables_dir: Path, **tables: pd.DataFrame) -> None:
    parquet_names = {"pairs", "paths", "station_summary", "band_contrasts"}
    for name, table in tables.items():
        if table is None or table.empty:
            continue
        if name in parquet_names:
            table.to_parquet(tables_dir / f"{name}.parquet", index=False)
        table.to_csv(tables_dir / f"{name}.csv", index=False)


def plot_observed_and_residual_maps(
    pairs: pd.DataFrame,
    regions: list[RegionRecord],
    figures_dir: Path,
    *,
    basemap_source: str,
    basemap_cache_dir: Path,
    basemap_zoom: int | None,
) -> Path:
    metric = "PGA"
    band = "3-5 sec"
    subset = pairs.loc[pairs["metric"].eq(metric) & pairs["band"].eq(band)].copy()
    station = (
        subset.groupby("station", as_index=False)
        .agg(
            sta_lon=("sta_lon", "median"),
            sta_lat=("sta_lat", "median"),
            observed=("obs_event_centered", "median"),
            residual=("log2_residual", "median"),
            events=("event_id", "nunique"),
            region_type=("station_region_type", first_valid),
        )
        .dropna(subset=["sta_lon", "sta_lat"])
    )
    transformer = Transformer.from_crs(WGS84, WEB_MERCATOR, always_xy=True)
    station_x, station_y = transformer.transform(station["sta_lon"].to_numpy(dtype=float), station["sta_lat"].to_numpy(dtype=float))
    station["map_x"] = station_x
    station["map_y"] = station_y
    x0, y0 = transformer.transform(-119.35, 33.15)
    x1, y1 = transformer.transform(-116.45, 34.85)
    xlim = (float(min(x0, x1)), float(max(x0, x1)))
    ylim = (float(min(y0, y1)), float(max(y0, y1)))
    projected_regions = [(region.region_type, shapely_transform(transformer.transform, region.geometry_lonlat)) for region in regions]
    fig, axes = plt.subplots(1, 2, figsize=(17.2, 7.1), sharex=True, sharey=True)
    panels = [
        ("observed", "Observed site anomaly\n(event-demeaned log2 PGA)", "BrBG", Normalize(vmin=-1.3, vmax=1.3)),
        ("residual", "CVM-SI residual\nlog2(observed/synthetic PGA)", "RdBu_r", TwoSlopeNorm(vmin=-1.8, vcenter=0.0, vmax=1.8)),
    ]
    for ax, (column, title, cmap, norm) in zip(axes, panels):
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        add_required_basemap(ax, source=basemap_source, cache_dir=basemap_cache_dir, zoom=basemap_zoom)
        draw_projected_regions(ax, projected_regions)
        points = ax.scatter(
            station["map_x"],
            station["map_y"],
            c=station[column],
            cmap=cmap,
            norm=norm,
            s=np.clip(station["events"] * 1.8, 18, 90),
            edgecolor="white",
            linewidth=0.45,
            alpha=0.92,
            zorder=5,
        )
        ax.set_title(title, fontsize=15, fontweight="bold")
        format_projected_map_axis(ax)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        cbar = fig.colorbar(points, ax=ax, shrink=0.78, pad=0.025)
        cbar.set_label(column.replace("_", " "))
        cbar.ax.tick_params(labelsize=10.5)
        cbar.ax.yaxis.label.set_size(12)
    fig.suptitle("Observed PGA site pattern and CVM-SI model residuals, 3-5 sec band", fontsize=20, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93], w_pad=2.2)
    path = figures_dir / "fig_01_observed_site_anomaly_vs_residual_map.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_region_period_heatmap(region_summary: pd.DataFrame, figures_dir: Path) -> Path:
    metric = "PGA"
    subset = region_summary.loc[
        region_summary["metric"].eq(metric)
        & region_summary["station_region"].notna()
        & region_summary["rows"].ge(MIN_GROUP_ROWS)
    ].copy()
    support = subset.groupby("station_region")["rows"].sum().sort_values(ascending=False).head(16).index.tolist()
    subset = subset.loc[subset["station_region"].isin(support)]
    pivot = subset.pivot_table(index="station_region", columns="band", values="median", aggfunc="median")
    pivot = pivot[[column for column in DEFAULT_BANDS if column in pivot.columns]]
    order = pivot.mean(axis=1).sort_values().index.tolist()
    pivot = pivot.loc[order]
    fig, ax = plt.subplots(figsize=(8.8, 7.2))
    image = ax.imshow(pivot.to_numpy(), cmap="RdBu_r", norm=TwoSlopeNorm(vmin=-1.1, vcenter=0.0, vmax=1.1), aspect="auto")
    ax.set_xticks(np.arange(len(pivot.columns)), pivot.columns)
    ax.set_yticks(np.arange(len(pivot.index)), pivot.index)
    ax.set_title("Event-demeaned PGA residual by station region and period band", fontsize=13, fontweight="bold")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            value = pivot.iat[i, j]
            if np.isfinite(value):
                ax.text(j, i, f"{value:+.2f}", ha="center", va="center", fontsize=8, color="black")
    cbar = fig.colorbar(image, ax=ax, shrink=0.82)
    cbar.set_label("Median event-demeaned log2 residual")
    fig.tight_layout()
    path = figures_dir / "fig_02_region_period_residual_heatmap.png"
    fig.savefig(path, dpi=210)
    plt.close(fig)
    return path


def plot_path_period_contrasts(band_contrasts: pd.DataFrame, figures_dir: Path) -> Path:
    metrics = ["PGA", "arias_duration"]
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 6.2), sharey=True)
    for ax, metric in zip(axes, metrics):
        subset = band_contrasts.loc[band_contrasts["metric"].eq(metric)].dropna(subset=["delta_3_5_minus_1_2"]).copy()
        counts = subset["path_class"].value_counts()
        classes = counts[counts >= 30].index.tolist()
        medians = subset.groupby("path_class")["delta_3_5_minus_1_2"].median().reindex(classes).sort_values()
        classes = medians.index.tolist()
        data = [subset.loc[subset["path_class"].eq(label), "delta_3_5_minus_1_2"].to_numpy(dtype=float) for label in classes]
        box = ax.boxplot(data, vert=False, patch_artist=True, showfliers=False)
        for patch in box["boxes"]:
            patch.set_facecolor("#dce8f4")
            patch.set_edgecolor(COLORS["blue"])
        for line in box["medians"]:
            line.set_color(COLORS["red"])
            line.set_linewidth(2.0)
        ax.axvline(0, color=COLORS["ink"], linewidth=1.0)
        labels = [f"{label}\n(n={len(values)})" for label, values in zip(classes, data)]
        ax.set_yticks(np.arange(1, len(classes) + 1), labels)
        ax.set_title(metric.replace("_", " ").title(), fontsize=13, fontweight="bold")
        ax.set_xlabel("Event-demeaned residual contrast: 3-5 sec minus 1-2 sec")
    fig.suptitle("Period dependence differs by event-station path class", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    path = figures_dir / "fig_03_path_period_contrasts.png"
    fig.savefig(path, dpi=210)
    plt.close(fig)
    return path


def plot_model_site_mismatch(station_summary: pd.DataFrame, figures_dir: Path) -> Path:
    panels = [("PGA", "1-2 sec"), ("PGA", "3-5 sec"), ("arias_duration", "3-5 sec")]
    fig, axes = plt.subplots(1, len(panels), figsize=(16.2, 5.8), sharex=True, sharey=True)
    legend_handles = []
    legend_labels = []
    for ax, (metric, band) in zip(axes, panels):
        subset = station_summary.loc[
            station_summary["metric"].eq(metric)
            & station_summary["band"].eq(band)
            & station_summary["log2_model_vs30_ratio"].notna()
            & station_summary["median_residual_event_centered"].notna()
        ].copy()
        for region_type, group in subset.groupby("station_region_type"):
            points = ax.scatter(
                group["log2_model_vs30_ratio"],
                group["median_residual_event_centered"],
                s=np.clip(group["events"] * 2.4, 18, 105),
                color=REGION_TYPE_COLORS.get(str(region_type), COLORS["gray"]),
                edgecolor="white",
                linewidth=0.45,
                alpha=0.78,
                label=str(region_type),
            )
            if str(region_type) not in legend_labels:
                legend_handles.append(points)
                legend_labels.append(str(region_type))
        if not subset.empty:
            bins = pd.qcut(
                subset["log2_model_vs30_ratio"],
                q=min(7, max(2, subset["log2_model_vs30_ratio"].nunique())),
                duplicates="drop",
            )
            binned = subset.groupby(bins, observed=False).agg(
                x=("log2_model_vs30_ratio", "median"),
                y=("median_residual_event_centered", "median"),
            )
            ax.plot(binned["x"], binned["y"], color=COLORS["ink"], linewidth=2.0, marker="o")
            rho, pvalue = spearmanr(subset["log2_model_vs30_ratio"], subset["median_residual_event_centered"])
        else:
            rho, pvalue = np.nan, np.nan
        ax.axhline(0, color=COLORS["ink"], linewidth=1.0)
        ax.axvline(0, color=COLORS["ink"], linewidth=1.0)
        ax.set_title(f"{metric.replace('_', ' ').title()}, {band}\nrho={rho:.2f}, p={pvalue:.2g}", fontsize=12, fontweight="bold")
        ax.set_xlabel("log2(CVM-SI surface Vs / Vs30)")
    axes[0].set_ylabel("Median event-demeaned residual")
    if legend_handles:
        fig.legend(legend_handles, legend_labels, frameon=False, loc="center right", bbox_to_anchor=(1.0, 0.5), fontsize=8)
    fig.suptitle("Station residuals versus CVM-SI site-velocity mismatch", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 0.91, 0.92])
    path = figures_dir / "fig_04_model_vs30_site_mismatch.png"
    fig.savefig(path, dpi=210)
    plt.close(fig)
    return path


def plot_geology_effects(geology_summary: pd.DataFrame, figures_dir: Path) -> Path:
    subset = geology_summary.loc[
        geology_summary["metric"].eq("PGA")
        & geology_summary["band"].eq("3-5 sec")
        & geology_summary["rows"].ge(MIN_GROUP_ROWS)
    ].copy()
    subset = subset.sort_values("median").tail(14)
    fig, ax = plt.subplots(figsize=(8.5, 7.0))
    y = np.arange(len(subset))
    ax.hlines(y, subset["bootstrap_ci_low"], subset["bootstrap_ci_high"], color=COLORS["grid"], linewidth=4)
    ax.scatter(subset["median"], y, s=np.clip(subset["stations"] * 4, 25, 140), color=COLORS["green"], edgecolor="white", linewidth=0.6)
    ax.axvline(0, color=COLORS["ink"], linewidth=1)
    ax.set_yticks(y, [wrap_label(label, 34) for label in subset["geologic_description"]])
    ax.set_xlabel("Median event-demeaned log2 residual with bootstrap 95% CI")
    ax.set_title("Geologic-unit residual effects (PGA, 3-5 sec)", fontsize=13, fontweight="bold")
    fig.tight_layout()
    path = figures_dir / "fig_05_geologic_unit_residual_effects.png"
    fig.savefig(path, dpi=210, bbox_inches="tight")
    plt.close(fig)
    return path


def build_southward_ew_section_series(
    regions: list[RegionRecord],
    *,
    start_ll: tuple[float, float] = (-118.72, 34.12),
    end_ll: tuple[float, float] = (-117.58, 34.12),
    spacing_km: float = 10.0,
    include_current: bool = True,
    shift_azimuth_deg: float = 180.0,
    direction_label: str = "south",
    max_offset_km: float = 180.0,
) -> tuple[list[tuple[str, tuple[float, float], tuple[float, float]]], pd.DataFrame]:
    if spacing_km <= 0:
        raise ValueError("spacing_km must be positive")
    la_basin = next((region for region in regions if region.name.lower() == "los angeles basin"), None)
    if la_basin is None:
        raise ValueError("Los Angeles Basin region was not found")
    transformer = Transformer.from_crs(WGS84, CVM_UTM, always_xy=True)
    inverse = Transformer.from_crs(CVM_UTM, WGS84, always_xy=True)
    basin_utm = shapely_transform(transformer.transform, la_basin.geometry_lonlat)
    sx, sy = transformer.transform(*start_ll)
    ex, ey = transformer.transform(*end_ll)
    shift_azimuth_rad = math.radians(shift_azimuth_deg)
    shift_unit_x = math.sin(shift_azimuth_rad)
    shift_unit_y = math.cos(shift_azimuth_rad)
    first_offset = 0.0 if include_current else spacing_km
    offsets = np.arange(first_offset, max_offset_km + 0.5 * spacing_km, spacing_km)
    sections: list[tuple[str, tuple[float, float], tuple[float, float]]] = []
    rows: list[dict[str, object]] = []
    has_entered_basin = False
    for offset_km in offsets:
        offset_m = float(offset_km) * 1000.0
        shifted_start = (sx + shift_unit_x * offset_m, sy + shift_unit_y * offset_m)
        shifted_end = (ex + shift_unit_x * offset_m, ey + shift_unit_y * offset_m)
        start_shifted_ll = inverse.transform(*shifted_start)
        end_shifted_ll = inverse.transform(*shifted_end)
        mid_lon, mid_lat = inverse.transform((shifted_start[0] + shifted_end[0]) / 2.0, (shifted_start[1] + shifted_end[1]) / 2.0)
        section_line = LineString([shifted_start, shifted_end])
        basin_intersection = section_line.intersection(basin_utm)
        intersects_basin = not basin_intersection.is_empty
        if intersects_basin:
            has_entered_basin = True
        elif has_entered_basin:
            break
        title = f"EW profile {offset_km:02.0f} km {direction_label} of current line (lat {mid_lat:.2f})"
        sections.append((title, start_shifted_ll, end_shifted_ll))
        rows.append(
            {
                "offset_km": float(offset_km),
                "shift_azimuth_deg": float(shift_azimuth_deg),
                "shift_east_km": float(shift_unit_x * offset_km),
                "shift_north_km": float(shift_unit_y * offset_km),
                "mid_lon": float(mid_lon),
                "mid_lat": float(mid_lat),
                "start_lon": float(start_shifted_ll[0]),
                "start_lat": float(start_shifted_ll[1]),
                "end_lon": float(end_shifted_ll[0]),
                "end_lat": float(end_shifted_ll[1]),
                "intersects_los_angeles_basin": bool(intersects_basin),
                "la_basin_intersection_km": float(basin_intersection.length / 1000.0) if intersects_basin else 0.0,
            }
        )
    return sections, pd.DataFrame(rows)


def plot_model_cross_sections(
    pairs: pd.DataFrame,
    regions: list[RegionRecord],
    sampler: ModelSampler,
    figures_dir: Path,
    *,
    basemap_source: str = DEFAULT_BASEMAP_SOURCE,
    basemap_cache_dir: Path | None = None,
    basemap_zoom: int | None = DEFAULT_BASEMAP_ZOOM,
    event_selection: str = "all",
    event_corridor_km: float | None = None,
    metric: str = "PGA",
    band: str = "3-5 sec",
    output_name: str = "fig_06_cvm_si_cross_sections_with_residuals.png",
    sections: Sequence[tuple[str, tuple[float, float], tuple[float, float]]] | None = None,
    figure_title: str | None = None,
    figure_note: str | None = None,
    figsize: tuple[float, float] | None = None,
    station_corridor_km: float = 15.0,
    show_events_on_map: bool = False,
    include_default_event_note: bool = True,
    show_lowess: bool = False,
    lowess_frac: float = 0.45,
    lowess_alpha: float = 0.88,
) -> Path:
    if sections is None:
        sections = [
            ("LA Basin to San Gabriel Mtns", (-118.22, 33.62), (-118.22, 34.46)),
            ("Santa Monica-Glendale-San Gabriel", (-118.72, 34.12), (-117.58, 34.12)),
        ]
    transformer = Transformer.from_crs(WGS84, CVM_UTM, always_xy=True)
    map_transformer = Transformer.from_crs(WGS84, WEB_MERCATOR, always_xy=True)
    metric_pairs = pairs.loc[pairs["metric"].eq(metric) & pairs["band"].eq(band)].copy()
    basemap_cache_dir = basemap_cache_dir or figures_dir.parent / "basemap_cache"
    residual_norm = TwoSlopeNorm(vmin=-1.8, vcenter=0.0, vmax=1.8)

    def station_residuals(pair_subset: pd.DataFrame) -> pd.DataFrame:
        columns = ["station", "sta_lon", "sta_lat", "residual", "q25", "q75", "events"]
        if pair_subset.empty:
            return pd.DataFrame(columns=columns)
        return (
            pair_subset
            .groupby("station", as_index=False)
            .agg(
                sta_lon=("sta_lon", "median"),
                sta_lat=("sta_lat", "median"),
                residual=("log2_residual", "median"),
                q25=("log2_residual", lambda value: float(value.quantile(0.25))),
                q75=("log2_residual", lambda value: float(value.quantile(0.75))),
                events=("event_id", "nunique"),
            )
            .dropna(subset=["sta_lon", "sta_lat", "residual"])
        )

    def event_subset_for_section(pair_subset: pd.DataFrame, sx: float, sy: float, ex: float, ey: float) -> tuple[pd.DataFrame, pd.DataFrame]:
        if event_selection == "all":
            return pair_subset, pd.DataFrame()
        if event_selection != "profile_ends":
            raise ValueError(f"Unknown event_selection: {event_selection}")
        if pair_subset.empty:
            return pair_subset, pd.DataFrame()
        dx = ex - sx
        dy = ey - sy
        length_m = math.hypot(dx, dy)
        ux = dx / length_m
        uy = dy / length_m
        event_x, event_y = transformer.transform(
            pair_subset["event_lon"].to_numpy(dtype=float),
            pair_subset["event_lat"].to_numpy(dtype=float),
        )
        vx = np.asarray(event_x) - sx
        vy = np.asarray(event_y) - sy
        along_m = vx * ux + vy * uy
        offset_m = np.abs(vx * uy - vy * ux)
        mask = (along_m < 0.0) | (along_m > length_m)
        if event_corridor_km is not None:
            mask &= offset_m <= event_corridor_km * 1000.0
        out = pair_subset.loc[mask].copy()
        if out.empty:
            return out, pd.DataFrame()
        out["event_along_km"] = along_m[mask] / 1000.0
        out["event_offset_km"] = offset_m[mask] / 1000.0
        out["event_profile_side"] = np.where(along_m[mask] < 0.0, "start", "end")
        events = out[
            ["event_id", "event_lon", "event_lat", "event_along_km", "event_offset_km", "event_profile_side"]
        ].drop_duplicates("event_id")
        return out, events

    global_residuals = station_residuals(metric_pairs)

    def station_projection(section_line: LineString, residuals: pd.DataFrame) -> pd.DataFrame:
        if residuals.empty:
            return pd.DataFrame(columns=[*residuals.columns, "projected_km", "offset_km"])
        station_xy = np.array(
            transformer.transform(
                residuals["sta_lon"].to_numpy(dtype=float),
                residuals["sta_lat"].to_numpy(dtype=float),
            )
        ).T
        rows: list[dict[str, object]] = []
        for station_row, xy in zip(residuals.itertuples(index=False), station_xy):
            point = Point(float(xy[0]), float(xy[1]))
            offset_km = point.distance(section_line) / 1000.0
            if offset_km > station_corridor_km:
                continue
            row = station_row._asdict()
            row["projected_km"] = section_line.project(point) / 1000.0
            row["offset_km"] = offset_km
            rows.append(row)
        if not rows:
            return pd.DataFrame(columns=[*residuals.columns, "projected_km", "offset_km"])
        return pd.DataFrame(rows).sort_values("projected_km")

    section_meta = []
    for title, start_ll, end_ll in sections:
        sx, sy = transformer.transform(*start_ll)
        ex, ey = transformer.transform(*end_ll)
        pair_subset, selected_events = event_subset_for_section(metric_pairs, sx, sy, ex, ey)
        residuals = global_residuals if event_selection == "all" else station_residuals(pair_subset)
        distances_km = np.linspace(0, math.hypot(ex - sx, ey - sy) / 1000.0, 190)
        depths_km = np.linspace(0, 15, 95)
        frac = distances_km / distances_km[-1]
        xs = sx + frac * (ex - sx)
        ys = sy + frac * (ey - sy)
        section_line = LineString([(sx, sy), (ex, ey)])
        station_section = station_projection(section_line, residuals)
        map_record_count = len(pair_subset)
        if event_selection == "profile_ends":
            map_events = selected_events
        elif show_events_on_map and not station_section.empty:
            station_pair_subset = pair_subset.loc[pair_subset["station"].isin(station_section["station"])]
            map_record_count = len(station_pair_subset)
            map_events = (
                station_pair_subset[["event_id", "event_lon", "event_lat"]]
                .dropna(subset=["event_lon", "event_lat"])
                .drop_duplicates("event_id")
            )
        else:
            map_events = pd.DataFrame()
        section_meta.append(
            {
                "title": title,
                "start_ll": start_ll,
                "end_ll": end_ll,
                "distances_km": distances_km,
                "depths_km": depths_km,
                "xs": xs,
                "ys": ys,
                "pair_rows": len(pair_subset),
                "selected_event_count": int(pair_subset["event_id"].nunique()) if not pair_subset.empty else 0,
                "selected_events": selected_events,
                "map_events": map_events,
                "map_record_count": map_record_count,
                "station_section": station_section,
            }
        )

    section_station_tables = [meta["station_section"] for meta in section_meta if not meta["station_section"].empty]
    all_section_stations = pd.concat(section_station_tables, ignore_index=True) if section_station_tables else pd.DataFrame()
    if all_section_stations.empty:
        residual_ylim = (-1.0, 1.0)
        event_min = event_max = 1.0
    else:
        q25 = all_section_stations["q25"].to_numpy(dtype=float)
        q75 = all_section_stations["q75"].to_numpy(dtype=float)
        residual_values = all_section_stations["residual"].to_numpy(dtype=float)
        finite_spread = np.concatenate(
            [
                q25[np.isfinite(q25)],
                q75[np.isfinite(q75)],
                residual_values[np.isfinite(residual_values)],
            ]
        )
        if finite_spread.size:
            lo = float(np.nanmin(finite_spread))
            hi = float(np.nanmax(finite_spread))
            pad = max(0.35, 0.08 * (hi - lo))
            residual_ylim = (max(-4.0, lo - pad), min(4.8, hi + pad))
        else:
            residual_ylim = (-1.0, 1.0)
        events = all_section_stations["events"].to_numpy(dtype=float)
        event_min = float(np.nanmin(events)) if np.isfinite(events).any() else 1.0
        event_max = float(np.nanmax(events)) if np.isfinite(events).any() else event_min

    def event_marker_size(events: object, *, minimum: float = 34.0, maximum: float = 170.0) -> np.ndarray:
        values = np.asarray(events, dtype=float)
        if not np.isfinite(values).any() or event_max <= event_min:
            return np.full(values.shape, (minimum + maximum) / 2.0)
        scaled = (values - event_min) / (event_max - event_min)
        scaled = np.clip(scaled, 0.0, 1.0)
        return minimum + (maximum - minimum) * np.sqrt(scaled)

    def weighted_lowess(data: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        if data.empty:
            return np.array([]), np.array([])
        x = data["projected_km"].to_numpy(dtype=float)
        y = data["residual"].to_numpy(dtype=float)
        weights = data["events"].to_numpy(dtype=float)
        valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0.0)
        x = x[valid]
        y = y[valid]
        weights = weights[valid]
        if len(np.unique(x)) < 4 or len(x) < 6:
            return np.array([]), np.array([])
        order = np.argsort(x)
        x = x[order]
        y = y[order]
        weights = weights[order]
        n = len(x)
        neighbors = min(n, max(4, int(math.ceil(float(lowess_frac) * n))))
        grid_count = int(np.clip(n * 3, 60, 180))
        x_grid = np.linspace(float(np.min(x)), float(np.max(x)), grid_count)
        y_grid = np.empty_like(x_grid)
        for idx, x0 in enumerate(x_grid):
            distances = np.abs(x - x0)
            bandwidth = float(np.partition(distances, neighbors - 1)[neighbors - 1])
            if bandwidth <= 0.0:
                positive = distances[distances > 0.0]
                bandwidth = float(np.min(positive)) if positive.size else 1.0
            local = np.clip(distances / bandwidth, 0.0, 1.0)
            tricube = (1.0 - local**3) ** 3
            local_weights = weights * tricube
            if np.count_nonzero(local_weights > 0.0) < 3:
                local_weights = weights
            active = local_weights > 0.0
            local_y = y[active]
            local_x = x[active]
            active_weights = local_weights[active]
            fallback = float(np.average(local_y, weights=active_weights))
            if local_y.size < 5 or float(np.ptp(local_x)) <= 1.0e-6:
                y_grid[idx] = fallback
                continue
            design = np.column_stack([np.ones_like(x), x - x0])
            root_weights = np.sqrt(local_weights)
            try:
                beta, *_ = np.linalg.lstsq(design * root_weights[:, None], y * root_weights, rcond=None)
                estimate = float(beta[0])
                local_lo = float(np.min(local_y))
                local_hi = float(np.max(local_y))
                tolerance = max(0.35, 0.25 * (local_hi - local_lo))
                if estimate < local_lo - tolerance or estimate > local_hi + tolerance:
                    estimate = fallback
                y_grid[idx] = estimate
            except np.linalg.LinAlgError:
                y_grid[idx] = fallback
        return x_grid, y_grid

    if figsize is None:
        figsize = (19.8, max(7.0, 6.5 * len(section_meta)))
    fig = plt.figure(figsize=figsize, constrained_layout=False)
    grid = fig.add_gridspec(
        nrows=2 * len(section_meta),
        ncols=3,
        width_ratios=[5.7, 0.14, 2.7],
        height_ratios=[1.05, 2.35] * len(section_meta),
        hspace=0.34,
        wspace=0.24,
    )
    for index, meta in enumerate(section_meta):
        scatter_ax = fig.add_subplot(grid[2 * index, 0])
        ax = fig.add_subplot(grid[2 * index + 1, 0], sharex=scatter_ax)
        cax = fig.add_subplot(grid[2 * index + 1, 1])
        map_ax = fig.add_subplot(grid[2 * index : 2 * index + 2, 2])
        distances_km = meta["distances_km"]
        depths_km = meta["depths_km"]
        xs = meta["xs"]
        ys = meta["ys"]
        grid_xyz = np.column_stack(
            [
                np.repeat(xs, len(depths_km)),
                np.repeat(ys, len(depths_km)),
                -np.tile(depths_km * 1000.0, len(xs)),
            ]
        )
        sampled = sampler.sample_xyz(grid_xyz)
        vs = sampled["vs"].to_numpy().reshape(len(xs), len(depths_km)).T / 1000.0
        image = ax.contourf(distances_km, depths_km, vs, levels=np.linspace(0.5, 4.5, 25), cmap="viridis", extend="both")
        ax.invert_yaxis()
        ax.set_ylabel("Depth (km)")
        ax.grid(color="white", linewidth=0.7, alpha=0.55)
        cbar = fig.colorbar(image, cax=cax)
        cbar.set_label("Vs (km/s)", fontsize=11, labelpad=7)
        cbar.ax.tick_params(labelsize=9)
        ax.set_xlabel("Distance along section (km)")
        x_margin_km = max(1.0, 0.015 * float(distances_km[-1]))
        ax.set_xlim(-x_margin_km, float(distances_km[-1]) + x_margin_km)

        station_section = meta["station_section"].copy()
        scatter_ax.axhline(0.0, color=COLORS["ink"], linewidth=1.0, zorder=1)
        scatter_title = meta["title"]
        if event_selection == "profile_ends":
            scatter_title = f"{scatter_title} ({meta['selected_event_count']} profile-end events)"
        else:
            scatter_title = f"{scatter_title} ({metric} {band}, all events)"
        scatter_ax.set_title(scatter_title, fontsize=15, fontweight="bold", pad=7)
        scatter_ax.set_ylabel(f"{metric} residual\nlog2(obs/syn)")
        scatter_ax.set_ylim(*residual_ylim)
        scatter_ax.set_xlim(-x_margin_km, float(distances_km[-1]) + x_margin_km)
        scatter_ax.grid(True, color=COLORS["grid"], linewidth=0.7, alpha=0.8)
        scatter_ax.tick_params(labelbottom=False)
        if not station_section.empty:
            yerr = np.vstack(
                [
                    np.clip(station_section["residual"] - station_section["q25"], 0.0, None),
                    np.clip(station_section["q75"] - station_section["residual"], 0.0, None),
                ]
            )
            scatter_ax.errorbar(
                station_section["projected_km"],
                station_section["residual"],
                yerr=yerr,
                fmt="none",
                ecolor=COLORS["muted"],
                elinewidth=1.05,
                alpha=0.58,
                capsize=1.7,
                zorder=2,
            )
            scatter_ax.scatter(
                station_section["projected_km"],
                station_section["residual"],
                c=station_section["residual"],
                cmap="RdBu_r",
                norm=residual_norm,
                s=event_marker_size(station_section["events"]),
                edgecolor="black",
                linewidth=0.45,
                alpha=0.92,
                zorder=3,
            )
            lowess_handle = None
            if show_lowess:
                lowess_x, lowess_y = weighted_lowess(station_section)
                if lowess_x.size:
                    finite_lowess = lowess_y[np.isfinite(lowess_y)]
                    if finite_lowess.size:
                        current_lo, current_hi = scatter_ax.get_ylim()
                        lowess_lo = float(np.min(finite_lowess))
                        lowess_hi = float(np.max(finite_lowess))
                        if lowess_lo < current_lo or lowess_hi > current_hi:
                            expanded_lo = min(current_lo, lowess_lo)
                            expanded_hi = max(current_hi, lowess_hi)
                            pad = max(0.25, 0.06 * (expanded_hi - expanded_lo))
                            scatter_ax.set_ylim(max(-4.0, expanded_lo - pad), min(4.8, expanded_hi + pad))
                    scatter_ax.plot(
                        lowess_x,
                        lowess_y,
                        color=COLORS["ink"],
                        linewidth=2.1,
                        alpha=lowess_alpha,
                        zorder=4,
                    )
                    lowess_handle = Line2D(
                        [0],
                        [0],
                        color=COLORS["ink"],
                        linewidth=2.1,
                        alpha=lowess_alpha,
                        label="event-weighted LOWESS",
                    )
            if index == 0:
                count = min(3, max(1, int(event_max - event_min + 1)))
                legend_values = np.unique(np.round(np.linspace(event_min, event_max, count)).astype(int))
                if legend_values.size > 1:
                    handles = [
                        scatter_ax.scatter(
                            [],
                            [],
                            s=event_marker_size([value])[0],
                            facecolor="white",
                            edgecolor=COLORS["ink"],
                            linewidth=0.7,
                        )
                        for value in legend_values
                    ]
                    labels = [f"{value:g} events" for value in legend_values]
                    if lowess_handle is not None:
                        handles.append(lowess_handle)
                        labels.append("LOWESS")
                    scatter_ax.legend(
                        handles,
                        labels,
                        title="Station support",
                        frameon=True,
                        fontsize=8.5,
                        title_fontsize=9,
                        loc="upper left",
                        bbox_to_anchor=(1.012, 0.99),
                        borderpad=0.55,
                        handletextpad=1.1,
                    )

        line_x, line_y = map_transformer.transform(
            [meta["start_ll"][0], meta["end_ll"][0]],
            [meta["start_ll"][1], meta["end_ll"][1]],
        )
        map_x = list(line_x)
        map_y = list(line_y)
        if not station_section.empty:
            station_map_x, station_map_y = map_transformer.transform(
                station_section["sta_lon"].to_numpy(dtype=float),
                station_section["sta_lat"].to_numpy(dtype=float),
            )
            map_x.extend(station_map_x)
            map_y.extend(station_map_y)
        map_events = meta["map_events"]
        if not map_events.empty:
            event_map_x, event_map_y = map_transformer.transform(
                map_events["event_lon"].to_numpy(dtype=float),
                map_events["event_lat"].to_numpy(dtype=float),
            )
            map_x.extend(event_map_x)
            map_y.extend(event_map_y)
        x_pad = max((max(map_x) - min(map_x)) * 0.16, 9000.0)
        y_pad = max((max(map_y) - min(map_y)) * 0.16, 9000.0)
        map_ax.set_xlim(min(map_x) - x_pad, max(map_x) + x_pad)
        map_ax.set_ylim(min(map_y) - y_pad, max(map_y) + y_pad)
        add_required_basemap(map_ax, source=basemap_source, cache_dir=basemap_cache_dir, zoom=basemap_zoom)
        map_ax.plot(line_x, line_y, color=COLORS["red"], linewidth=2.6, zorder=5)
        map_ax.scatter(line_x, line_y, marker="s", s=34, color=COLORS["red"], edgecolor="white", linewidth=0.65, zorder=6)
        if not station_section.empty:
            map_ax.scatter(
                station_map_x,
                station_map_y,
                c=station_section["residual"],
                cmap="RdBu_r",
                norm=residual_norm,
                s=np.clip(event_marker_size(station_section["events"], minimum=20.0, maximum=72.0), 20.0, 72.0),
                edgecolor="white",
                linewidth=0.45,
                alpha=0.94,
                zorder=6,
            )
        if not map_events.empty:
            if "event_profile_side" in map_events.columns:
                event_colors = map_events["event_profile_side"].map({"start": COLORS["gold"], "end": COLORS["purple"]}).fillna(COLORS["gold"])
            else:
                event_colors = COLORS["gold"]
            map_ax.scatter(
                event_map_x,
                event_map_y,
                c=event_colors,
                marker="*",
                s=58,
                edgecolor="black",
                linewidth=0.55,
                alpha=0.82,
                zorder=7,
            )
        map_ax.set_title("Map view", fontsize=12, fontweight="bold")
        format_projected_map_axis(map_ax)
        map_ax.set_xlabel("x (km)")
        map_ax.set_ylabel("y (km)")
        map_ax.tick_params(labelsize=8)
        map_note = f"{len(station_section)} stations within {station_corridor_km:g} km"
        if show_events_on_map and event_selection != "profile_ends" and not map_events.empty:
            map_note = f"{map_note}; {len(map_events)} events\n{meta['map_record_count']:,} records"
        if event_selection == "profile_ends":
            map_note = f"{len(station_section)} stations within {station_corridor_km:g} km; {meta['selected_event_count']} events\n{meta['pair_rows']:,} records"
        map_ax.text(
            0.02,
            0.02,
            map_note,
            transform=map_ax.transAxes,
            fontsize=8.5,
            color=COLORS["ink"],
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78, "pad": 2.0},
            zorder=8,
        )
    note_lines = []
    if event_selection == "profile_ends":
        corridor_text = "no off-axis limit" if event_corridor_km is None else f"<= {event_corridor_km:g} km off profile axis"
        default_title = f"CVM-SI Vs cross sections with profile-end event {metric} residual distributions"
        if include_default_event_note:
            note_lines.append(
                f"Event filter: {metric} {band} records whose epicenters project beyond either profile endpoint ({corridor_text}); station summaries are recomputed from the filtered records. Stars mark selected event epicenters."
            )
    else:
        default_title = f"CVM-SI Vs cross sections with station {metric} residual distributions"
    if figure_note:
        note_lines.append(figure_note)
    fig.suptitle(figure_title or default_title, fontsize=15, fontweight="bold")
    if note_lines:
        fig.text(0.055, 0.025, "\n".join(note_lines), fontsize=10, color=COLORS["muted"])
        rendered_note_lines = sum(line.count("\n") + 1 for line in note_lines)
        bottom = 0.13 + 0.025 * (rendered_note_lines - 1)
    else:
        bottom = 0.06
    top = 0.88 if len(section_meta) == 1 and figure_title else 0.92
    fig.subplots_adjust(left=0.055, right=0.985, bottom=bottom, top=top)
    path = figures_dir / output_name
    fig.savefig(path, dpi=210)
    plt.close(fig)
    return path


def draw_regions(ax: plt.Axes, regions: list[RegionRecord]) -> None:
    for region in regions:
        color = REGION_TYPE_COLORS.get(region.region_type, COLORS["gray"])
        for polygon in iter_polygons(region.geometry_lonlat):
            x, y = polygon.exterior.xy
            ax.plot(x, y, color=color, linewidth=0.9, alpha=0.8, zorder=2)


def draw_projected_regions(ax: plt.Axes, projected_regions: list[tuple[str, object]]) -> None:
    for region_type, geom in projected_regions:
        color = REGION_TYPE_COLORS.get(region_type, COLORS["gray"])
        for polygon in iter_polygons(geom):
            x, y = polygon.exterior.xy
            ax.plot(x, y, color=color, linewidth=0.9, alpha=0.85, zorder=3)


def add_required_basemap(ax: plt.Axes, *, source: str, cache_dir: Path, zoom: int | None) -> str:
    from spatial_vtk.spatial.map.basemaps import add_contextily_basemap

    ok, resolved_source = add_contextily_basemap(
        ax,
        crs=WEB_MERCATOR,
        primary_source=source,
        fallback_sources=("Esri.WorldTopoMap", "OpenStreetMap.Mapnik", "Esri.WorldImagery"),
        zoom=zoom,
        attribution=False,
        cache_dir=cache_dir,
        cache_download=True,
        on_error="raise",
    )
    if not ok:
        raise RuntimeError(f"Required basemap was not rendered: {resolved_source}")
    return str(resolved_source)


def format_projected_map_axis(ax: plt.Axes) -> None:
    ax.set_aspect("equal", adjustable="box")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000.0:.0f}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000.0:.0f}"))
    ax.set_xlabel("Web Mercator x (km)")
    ax.set_ylabel("Web Mercator y (km)")


def iter_polygons(geom: object) -> Iterable[object]:
    if geom.geom_type == "Polygon":
        yield geom
    elif geom.geom_type == "MultiPolygon":
        yield from geom.geoms


def wrap_label(text: object, width: int) -> str:
    value = str(text)
    words = value.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        proposed = " ".join(current + [word])
        if len(proposed) > width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def write_report_scaffold(
    path: Path,
    manifest: dict[str, object],
    global_summary: pd.DataFrame,
    region_summary: pd.DataFrame,
    geology_summary: pd.DataFrame,
    path_summary: pd.DataFrame,
    band_contrast_summary: pd.DataFrame,
    tests: pd.DataFrame,
    mixed_effects: pd.DataFrame,
) -> None:
    pga = global_summary.loc[global_summary["metric"].eq("PGA")].copy()
    pga_lines = [
        f"- {row.band}: median log2(obs/syn) = {row.median:+.2f} "
        f"(95% bootstrap CI {row.bootstrap_ci_low:+.2f} to {row.bootstrap_ci_high:+.2f}, n={int(row.rows)})"
        for row in pga.sort_values("band").itertuples()
    ]
    top_regions = (
        region_summary.loc[region_summary["metric"].eq("PGA") & region_summary["band"].eq("3-5 sec") & region_summary["rows"].ge(MIN_GROUP_ROWS)]
        .sort_values("median", ascending=False)
        .head(8)
    )
    top_region_lines = [
        f"- {row.station_region} ({row.station_region_type}): median event-demeaned residual {row.median:+.2f}, "
        f"stations={int(row.stations)}, events={int(row.events)}"
        for row in top_regions.itertuples()
    ]
    contrast_lines = []
    if not band_contrast_summary.empty:
        subset = band_contrast_summary.loc[band_contrast_summary["contrast"].eq("delta_3_5_minus_1_2")]
        for row in subset.sort_values(["metric", "median"], ascending=[True, False]).head(12).itertuples():
            contrast_lines.append(
                f"- {row.metric}, {row.path_class}: median 3-5 minus 1-2 sec contrast {row.median:+.2f} "
                f"(CI {row.bootstrap_ci_low:+.2f} to {row.bootstrap_ci_high:+.2f}, n={int(row.rows)})"
            )
    test_lines = []
    if not tests.empty:
        for row in tests.itertuples():
            test_lines.append(
                f"- {row.test}, {row.metric}, {row.band}: statistic={row.statistic:.3g}, "
                f"p={row.pvalue:.3g}, n={int(row.rows)}. {row.explanation}"
            )
    mixed_lines = []
    if not mixed_effects.empty:
        terms = [
            "log2_model_vs30_ratio_z",
            "C(path_class)[T.terminates in LA basin]",
            "C(path_class)[T.crosses LA basin]",
            "C(geology_focus)[T.Tsh]",
            "C(geology_focus)[T.Kgr, xtaline]",
        ]
        subset = mixed_effects.loc[mixed_effects["term"].isin(terms)].copy()
        if not subset.empty:
            for row in subset.sort_values(["model_name", "metric", "band_scope", "term"]).itertuples():
                if getattr(row, "term") == "model_fit_error":
                    continue
                mixed_lines.append(
                    f"- {row.model_name}, {row.metric}, {row.band_scope}, {row.term}: "
                    f"coef={row.coef:+.3f}, 95% CI {row.ci_low:+.3f} to {row.ci_high:+.3f}, "
                    f"p={row.pvalue:.3g}, n={int(row.nobs)}"
                )
    text = f"""# CVM-SI Observed/Synthetic Hypotheses

This is an auto-generated scaffold. Add literature context, final narrative
claims, and any manual figure interpretation before sharing.

## Reproducibility

- Metrics table: `{manifest['inputs']['metrics']}`
- Region GeoJSON: `{manifest['inputs']['regions']}`
- CVM-SI HDF5: `{manifest['inputs']['model_h5']}`
- Model id: `{manifest['inputs']['model']}`
- Output directory: `{manifest['outputs']['output_dir']}`
- Event-station-metric-band rows analyzed: `{manifest['counts']['event_station_metric_band_rows']}`
- Events: `{manifest['counts']['events']}`
- Stations: `{manifest['counts']['stations']}`

## Candidate Hypothesis 1: CVM-SI Usually Underpredicts Observed Amplitudes

PGA residuals are mostly positive, meaning observed amplitudes exceed
synthetics after metric calculation:

{chr(10).join(pga_lines) if pga_lines else '- No PGA summary available.'}

Use Figure 1 with the global and regional tables to separate observed-only
site patterns from obs/syn residual patterns.

## Candidate Hypothesis 2: Residual Bias Is Spatially Organized By Region And Geology

Largest positive station-region effects for PGA, 3-5 sec:

{chr(10).join(top_region_lines) if top_region_lines else '- No region summary available.'}

Use Figure 2 and Figure 5. The event-demeaned statistic removes each event's
median level before aggregating, so the reported spatial pattern is less likely
to be a single event/source-strength artifact. This is a diagnostic transform,
not the final inferential model; use the mixed-effects table to confirm which
terms survive simultaneous event and station random effects.

## Candidate Hypothesis 3: Period Dependence Changes Along Basin-Influenced Paths

Band contrasts:

{chr(10).join(contrast_lines) if contrast_lines else '- No band contrast summary available.'}

Use Figure 3 and the permutation test results below. Positive 3-5 minus 1-2 sec
contrasts mean the long-period residual is larger than the short-period residual
for the same event-station pair.

## Candidate Hypothesis 4: Site-Velocity Mismatch Helps Explain Residual Structure

Use Figure 4. The x-axis compares sampled CVM-SI surface Vs against station
Vs30. A positive x value means the model is faster than the site proxy; a
systematic trend would suggest missing shallow low-velocity structure or
over-smoothed basin/site conditions.

## Candidate Hypothesis 5: Cross Sections Can Tie Residuals To Model Geometry

Use Figure 6. The cross sections sample CVM-SI Vs through the Los Angeles,
Glendale, San Fernando, and San Gabriel areas, with nearby station residuals
shown at the surface. These views are intended to identify whether residual
clusters align with basin edges, shallow velocity floors, or strong gradients.

## Statistical Test Notes

{chr(10).join(test_lines) if test_lines else '- No statistical tests were available.'}

## Mixed-Effects Notes

Mixed-effects models are the preferred inferential layer here because they fit
raw log2 residuals while estimating station and event random intercept
variance. Event-demeaned maps remain useful for seeing spatial structure, but
they should be read as diagnostics.

{chr(10).join(mixed_lines) if mixed_lines else '- Mixed-effects models did not produce selected terms; inspect `mixed_effects.csv` for fit errors or full coefficients.'}

Bootstrap confidence intervals estimate how stable a median is under repeated
resampling of the observed records. Kruskal-Wallis tests whether several
geologic groups have residual distributions that are too different to treat as
one population. The permutation test asks whether the LA-basin path contrast is
larger than expected if path labels were exchangeable. Mixed-effects coefficients
estimate residual shifts while accounting for repeated observations from the
same stations and events.

## Figures

- Figure 1: `fig_01_observed_site_anomaly_vs_residual_map.png`
- Figure 2: `fig_02_region_period_residual_heatmap.png`
- Figure 3: `fig_03_path_period_contrasts.png`
- Figure 4: `fig_04_model_vs30_site_mismatch.png`
- Figure 5: `fig_05_geologic_unit_residual_effects.png`
- Figure 6: `fig_06_cvm_si_cross_sections_with_residuals.png`

## Bibliography Placeholder

Add Southern California basin, CVM, and basin-edge literature here after manual
literature review.
"""
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
