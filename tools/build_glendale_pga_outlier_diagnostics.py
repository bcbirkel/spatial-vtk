#!/usr/bin/env python3
"""Build map and waveform diagnostics for Glendale PGA high-residual rows."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import Point, shape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Patch
from spatial_vtk.metrics.calculate.waveforms import bandpass_with_metadata


DEFAULT_METRICS = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/tables/metrics_long.parquet")
DEFAULT_GEOJSON = Path("/project2/jvidale_1700/spatial-vtk/runs/inputs/geospatial/regions_updated.geojson")
DEFAULT_PROJECT_ROOT = Path("/project2/jvidale_1700/spatial-vtk")
DEFAULT_OUTPUT_DIR = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/figures/user_requested_glendale_pga_outliers")
DEFAULT_MODEL = "cvmsi_20260506_material_0p6x1p2_asdf"
BASELINE_REGION = "Los Angeles Basin"
TARGET_REGION = "Glendale"
TARGET_METRIC = "PGA"
REGION_COLORS = {
    "Basin": "#B8D4F2",
    "Hills": "#F6C66B",
    "Mountains": "#A8CF8A",
    "Other": "#C9B2CF",
    "Valley": "#C7D889",
}


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    regions = load_regions(args.geojson)
    la_geom = next(region["geometry"] for region in regions if region["long_name"] == BASELINE_REGION)

    columns = [
        "event_id",
        "station",
        "component",
        "model",
        "metric",
        "band",
        "value_obs",
        "value_syn",
        "log2_residual",
        "event_lat",
        "event_lon",
        "sta_lat",
        "sta_lon",
        "distance_km",
        "obs_waveform_path",
        "syn_waveform_path",
    ]
    df = pd.read_parquet(args.metrics, columns=columns)
    df = df.loc[(df["model"].astype(str) == args.model) & (df["metric"].astype(str) == TARGET_METRIC)].copy()
    df["log2_residual"] = pd.to_numeric(df["log2_residual"], errors="coerce")
    df["value_obs"] = pd.to_numeric(df["value_obs"], errors="coerce")
    df["value_syn"] = pd.to_numeric(df["value_syn"], errors="coerce")

    stations = df[["station", "sta_lon", "sta_lat"]].drop_duplicates("station").copy()
    stations["station_in_la_basin"] = [
        contains_point(la_geom, row.sta_lon, row.sta_lat) for row in stations.itertuples(index=False)
    ]
    df = df.merge(stations.loc[stations["station_in_la_basin"], ["station"]], on="station", how="inner")

    event_regions = annotate_events(df[["event_id", "event_lon", "event_lat"]].drop_duplicates("event_id"), regions)
    df = df.merge(event_regions, on="event_id", how="left")
    glendale = df.loc[(df["event_region"] == TARGET_REGION) & np.isfinite(df["log2_residual"])].copy()
    if glendale.empty:
        raise ValueError("No Glendale PGA rows found for LA Basin stations.")

    threshold = float(args.min_log2_residual)
    if math.isnan(threshold):
        threshold = float(np.nanquantile(glendale["log2_residual"], args.quantile))
    selected = glendale.loc[glendale["log2_residual"] >= threshold].copy()
    if selected.empty:
        selected = glendale.sort_values("log2_residual", ascending=False).head(args.top_n).copy()
    selected = selected.sort_values(["log2_residual", "event_id", "station", "band", "component"], ascending=[False, True, True, True, True])
    selected_for_waveforms = selected.head(args.max_waveforms).copy()

    map_path = output_dir / "glendale_pga_high_residual_event_station_map.png"
    wave_path = output_dir / "glendale_pga_high_residual_waveforms.png"
    csv_path = output_dir / "glendale_pga_high_residual_rows.csv"
    manifest_path = output_dir / "glendale_pga_high_residual_manifest.json"

    selected.to_csv(csv_path, index=False)
    plot_map(glendale, selected, regions, map_path)
    waveform_status = plot_waveforms(selected_for_waveforms, wave_path, args.project_root)

    manifest = {
        "input_metrics": str(args.metrics),
        "geojson": str(args.geojson),
        "output_dir": str(output_dir),
        "model": args.model,
        "metric": TARGET_METRIC,
        "event_region": TARGET_REGION,
        "station_filter": f"stations inside/touching {BASELINE_REGION}",
        "value_column": "log2_residual",
        "selection": {
            "quantile": float(args.quantile),
            "min_log2_residual": float(threshold),
            "selected_rows": int(len(selected)),
            "selected_events": int(selected["event_id"].nunique()),
            "selected_stations": int(selected["station"].nunique()),
            "waveform_rows": int(len(selected_for_waveforms)),
        },
        "glendale_rows": int(len(glendale)),
        "glendale_events": int(glendale["event_id"].nunique()),
        "glendale_stations": int(glendale["station"].nunique()),
        "map_png": str(map_path),
        "waveforms_png": str(wave_path),
        "selected_rows_csv": str(csv_path),
        "waveform_status": waveform_status,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--geojson", type=Path, default=DEFAULT_GEOJSON)
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--quantile", type=float, default=0.99)
    parser.add_argument("--min-log2-residual", type=float, default=float("nan"))
    parser.add_argument("--top-n", type=int, default=12)
    parser.add_argument("--max-waveforms", type=int, default=12)
    return parser.parse_args()


def load_regions(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    regions: list[dict[str, object]] = []
    for index, feature in enumerate(payload.get("features", [])):
        props = feature.get("properties", {}) or {}
        geom = feature.get("geometry")
        if not geom:
            continue
        long_name = str(props.get("long_name") or props.get("short_name") or f"feature_{index}")
        regions.append(
            {
                "index": index,
                "long_name": long_name,
                "short_name": str(props.get("short_name") or long_name),
                "region_type": str(props.get("region_type") or "Other"),
                "geometry": shape(geom),
            }
        )
    return regions


def contains_point(geom: object, lon: object, lat: object) -> bool:
    if pd.isna(lon) or pd.isna(lat):
        return False
    point = Point(float(lon), float(lat))
    return bool(geom.contains(point) or geom.touches(point))


def annotate_events(events: pd.DataFrame, regions: list[dict[str, object]]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in events.itertuples(index=False):
        match = None
        point = Point(float(row.event_lon), float(row.event_lat))
        for region in regions:
            geom = region["geometry"]
            if geom.contains(point) or geom.touches(point):
                match = region
                break
        rows.append(
            {
                "event_id": row.event_id,
                "event_region": None if match is None else match["long_name"],
                "event_region_type": None if match is None else match["region_type"],
            }
        )
    return pd.DataFrame(rows)


def plot_map(glendale: pd.DataFrame, selected: pd.DataFrame, regions: list[dict[str, object]], output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 8.2), dpi=180)
    for region in regions:
        draw_geometry(
            ax,
            region["geometry"],
            facecolor=REGION_COLORS.get(str(region["region_type"]), "#D8DDE6"),
            edgecolor="#78808E",
            alpha=0.24 if region["long_name"] not in {BASELINE_REGION, TARGET_REGION} else 0.42,
            linewidth=1.2 if region["long_name"] in {BASELINE_REGION, TARGET_REGION} else 0.7,
        )

    all_pairs = glendale[["event_id", "event_lon", "event_lat", "station", "sta_lon", "sta_lat"]].drop_duplicates()
    for row in all_pairs.itertuples(index=False):
        ax.plot([row.event_lon, row.sta_lon], [row.event_lat, row.sta_lat], color="#9DA5B4", linewidth=0.45, alpha=0.16, zorder=1)

    selected_pairs = selected.groupby(["event_id", "station"], as_index=False).agg(
        event_lon=("event_lon", "first"),
        event_lat=("event_lat", "first"),
        sta_lon=("sta_lon", "first"),
        sta_lat=("sta_lat", "first"),
        max_log2_residual=("log2_residual", "max"),
        rows=("log2_residual", "size"),
    )
    segments = [
        [(float(row.event_lon), float(row.event_lat)), (float(row.sta_lon), float(row.sta_lat))]
        for row in selected_pairs.itertuples(index=False)
    ]
    values = selected_pairs["max_log2_residual"].to_numpy(dtype=float)
    line_collection = LineCollection(segments, cmap="magma", linewidths=2.4, alpha=0.95, zorder=4)
    line_collection.set_array(values)
    line_collection.set_clim(float(np.nanmin(values)), float(np.nanmax(values)))
    ax.add_collection(line_collection)
    fig.colorbar(line_collection, ax=ax, fraction=0.035, pad=0.02, label="max PGA log2 residual for selected pair")

    ax.scatter(glendale["sta_lon"], glendale["sta_lat"], s=16, c="#3D6CA8", alpha=0.42, edgecolor="white", linewidth=0.35, label="LA Basin stations with Glendale-event PGA", zorder=3)
    ax.scatter(glendale["event_lon"], glendale["event_lat"], s=48, c="#C75D4D", marker="*", alpha=0.55, edgecolor="white", linewidth=0.5, label="Glendale events", zorder=5)
    ax.scatter(selected_pairs["sta_lon"], selected_pairs["sta_lat"], s=86, c="#16253D", edgecolor="white", linewidth=0.9, label="selected high-residual station", zorder=6)
    ax.scatter(selected_pairs["event_lon"], selected_pairs["event_lat"], s=130, c="#D94830", marker="*", edgecolor="white", linewidth=0.9, label="selected high-residual event", zorder=7)

    for row in selected_pairs.itertuples(index=False):
        ax.text(row.sta_lon + 0.006, row.sta_lat - 0.006, str(row.station), fontsize=8, color="#16253D", weight="bold", zorder=8)
        ax.text(row.event_lon + 0.006, row.event_lat + 0.006, str(row.event_id), fontsize=7, color="#7A241A", zorder=8)

    lon_values = np.r_[glendale["event_lon"].to_numpy(float), glendale["sta_lon"].to_numpy(float)]
    lat_values = np.r_[glendale["event_lat"].to_numpy(float), glendale["sta_lat"].to_numpy(float)]
    pad_lon = max(0.04, (np.nanmax(lon_values) - np.nanmin(lon_values)) * 0.16)
    pad_lat = max(0.04, (np.nanmax(lat_values) - np.nanmin(lat_values)) * 0.16)
    ax.set_xlim(np.nanmin(lon_values) - pad_lon, np.nanmax(lon_values) + pad_lon)
    ax.set_ylim(np.nanmin(lat_values) - pad_lat, np.nanmax(lat_values) + pad_lat)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(
        "Glendale PGA high-residual event-station paths\n"
        f"Selected rows: {len(selected):,}; pairs: {len(selected_pairs):,}; threshold: log2 residual >= {selected['log2_residual'].min():.2f}",
        fontsize=12,
    )
    ax.grid(True, color="#E1E5ED", linewidth=0.7)
    ax.legend(loc="lower left", fontsize=8, frameon=True)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def draw_geometry(ax: plt.Axes, geom: object, **kwargs: object) -> None:
    if geom.geom_type == "Polygon":
        xs, ys = geom.exterior.xy
        ax.fill(xs, ys, **kwargs)
        return
    if geom.geom_type == "MultiPolygon":
        for poly in geom.geoms:
            xs, ys = poly.exterior.xy
            ax.fill(xs, ys, **kwargs)


def plot_waveforms(rows: pd.DataFrame, output_path: Path, project_root: Path) -> list[dict[str, object]]:
    rows = rows.sort_values(["event_id", "station", "band", "component"]).copy()
    n = len(rows)
    fig, axes = plt.subplots(n, 1, figsize=(13.0, max(2.0 * n, 4.0)), dpi=180, sharex=False)
    if n == 1:
        axes = np.array([axes])
    status: list[dict[str, object]] = []
    for ax, row in zip(axes, rows.itertuples(index=False)):
        obs_path = resolve_path(project_root, row.obs_waveform_path)
        syn_path = resolve_path(project_root, row.syn_waveform_path)
        try:
            obs_data, obs_rate = load_waveform(obs_path, row.component)
            syn_data, syn_rate = load_waveform(syn_path, row.component)
            obs_data = bandpass_for_plot(obs_data, obs_rate, row.band)
            syn_data = bandpass_for_plot(syn_data, syn_rate, row.band)
            obs_time = np.arange(obs_data.size, dtype=float) / obs_rate
            syn_time = np.arange(syn_data.size, dtype=float) / syn_rate
            scale = pair_scale(obs_data, syn_data)
            ax.plot(obs_time, obs_data / scale, color="#1F5FA8", linewidth=0.8, label="obs, bandpassed")
            ax.plot(syn_time, syn_data / scale, color="#D36B39", linewidth=0.8, alpha=0.9, label="syn, bandpassed")
            ax.axhline(0, color="#7A828F", linewidth=0.5)
            ax.set_xlim(0.0, max(float(np.nanmax(obs_time)), float(np.nanmax(syn_time))))
            ax.set_ylim(-1.15, 1.15)
            status_text = "rendered"
        except Exception as exc:  # noqa: BLE001 - record the failing row rather than aborting the whole figure.
            ax.text(0.01, 0.5, f"Could not load waveform: {exc}", transform=ax.transAxes, va="center", fontsize=8)
            status_text = f"error: {exc}"
        ax.set_ylabel(str(row.component), rotation=0, labelpad=18, fontsize=8, weight="bold")
        ax.set_title(
            f"{row.event_id} -> {row.station}; {row.band}; comp {row.component}; "
            f"log2 residual={float(row.log2_residual):.2f}; obs PGA={float(row.value_obs):.3g}; syn PGA={float(row.value_syn):.3g}; "
            f"dist={float(row.distance_km):.1f} km",
            fontsize=8,
            loc="left",
        )
        ax.grid(True, color="#E6E8F0", linewidth=0.6)
        status.append(
            {
                "event_id": row.event_id,
                "station": row.station,
                "component": row.component,
                "band": row.band,
                "log2_residual": float(row.log2_residual),
                "obs_waveform_path": str(obs_path),
                "syn_waveform_path": str(syn_path),
                "status": status_text,
                "plot_filter": f"bandpass {row.band}",
            }
        )
    axes[0].legend(loc="upper right", fontsize=8)
    axes[-1].set_xlabel("Time from waveform start (s)")
    fig.suptitle("Waveforms driving the Glendale PGA high residuals", fontsize=13, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return status


def resolve_path(project_root: Path, value: object) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path
    return project_root / path


def load_waveform(path: Path, component: object) -> tuple[np.ndarray, float]:
    payload = np.load(path, allow_pickle=False)
    data = np.asarray(payload["data"], dtype=float)
    rate = float(np.asarray(payload["sampling_rate"]).reshape(-1)[0])
    channels = [str(item) for item in np.asarray(payload["channels"]).tolist()]
    comp = str(component)
    if data.ndim == 1:
        trace = data
    else:
        idx = component_index(channels, comp)
        trace = data[idx] if data.shape[0] == len(channels) else data[:, idx]
    trace = np.asarray(trace, dtype=float).reshape(-1)
    finite = np.isfinite(trace)
    if not finite.all():
        trace = np.where(finite, trace, 0.0)
    return trace, rate


def bandpass_for_plot(samples: np.ndarray, rate: float, passband: object) -> np.ndarray:
    corners = passband_corner_hz(passband)
    if corners is None:
        return np.asarray(samples, dtype=float)
    low_hz, high_hz = corners
    if not np.isfinite(rate) or rate <= 0:
        return np.asarray(samples, dtype=float)
    result = bandpass_with_metadata(np.asarray(samples, dtype=float), 1.0 / float(rate), low_hz, high_hz)
    filtered = np.asarray(result.data, dtype=float)
    mask = np.asarray(result.valid_mask, dtype=bool)
    if mask.shape == filtered.shape:
        filtered = np.where(mask, filtered, np.nan)
    return filtered


def passband_corner_hz(value: object) -> tuple[float, float] | None:
    numbers = [float(match) for match in re.findall(r"\d+(?:\.\d+)?", str(value or ""))]
    if len(numbers) < 2 or numbers[0] <= 0.0 or numbers[1] <= 0.0:
        return None
    period_min_s, period_max_s = min(numbers[0], numbers[1]), max(numbers[0], numbers[1])
    return 1.0 / period_max_s, 1.0 / period_min_s


def pair_scale(obs: np.ndarray, syn: np.ndarray) -> float:
    finite_obs = obs[np.isfinite(obs)]
    finite_syn = syn[np.isfinite(syn)]
    if finite_obs.size == 0 and finite_syn.size == 0:
        return 1.0
    scale = float(np.nanmax(np.abs(np.concatenate([finite_obs, finite_syn]))))
    return scale if np.isfinite(scale) and scale > 0 else 1.0


def component_index(channels: list[str], component: str) -> int:
    for index, channel in enumerate(channels):
        if channel.upper().endswith(component.upper()):
            return index
    return {"R": 0, "T": 1, "Z": 2}.get(component.upper(), 0)


if __name__ == "__main__":
    raise SystemExit(main())
