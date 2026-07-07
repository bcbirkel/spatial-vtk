#!/usr/bin/env python3
"""Build representative observed/synthetic waveform examples for basin polygons."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shapely.geometry import Point, shape

from spatial_vtk.metrics.calculate.waveforms import bandpass_with_metadata


DEFAULT_METRICS = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/tables/metrics_long.parquet")
DEFAULT_GEOJSON = Path("/project2/jvidale_1700/spatial-vtk/runs/inputs/geospatial/regions_updated.geojson")
DEFAULT_PROJECT_ROOT = Path("/project2/jvidale_1700/spatial-vtk")
DEFAULT_OUTPUT_DIR = Path(
    "/project2/jvidale_1700/spatial-vtk/runs/outputs/figures/user_requested_basin_representative_waveforms"
)
DEFAULT_MODEL = "cvmsi_20260506_material_0p6x1p2_asdf"
METRIC = "arias_duration"
REGION_TYPE = "Basin"
PASSBANDS = ("1-2 sec", "2-3 sec", "3-5 sec")
BASELINE_REGION = "Los Angeles Basin"
DISPLAY_NAMES = {"San Bernadino Basin": "San Bernardino Basin"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--geojson", type=Path, default=DEFAULT_GEOJSON)
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser.parse_args()


def display_region(value: object) -> str:
    text = str(value)
    return DISPLAY_NAMES.get(text, text)


def slug(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_") or "unknown"


def load_basin_features(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    features: list[dict[str, object]] = []
    for index, feature in enumerate(payload.get("features", [])):
        props = feature.get("properties", {}) or {}
        region_type = str(props.get("region_type") or props.get("mapped_region_type") or "")
        if region_type != REGION_TYPE:
            continue
        long_name = str(props.get("long_name") or props.get("name") or props.get("short_name") or f"feature_{index}")
        features.append(
            {
                "long_name": long_name,
                "display_name": display_region(long_name),
                "geometry": shape(feature["geometry"]),
            }
        )
    if not features:
        raise ValueError(f"No {REGION_TYPE} features found in {path}")
    return features


def assign_station_regions(df: pd.DataFrame, features: list[dict[str, object]]) -> pd.DataFrame:
    station_rows = df[["station", "sta_lon", "sta_lat"]].dropna().drop_duplicates("station").copy()
    records: list[dict[str, object]] = []
    for row in station_rows.itertuples(index=False):
        point = Point(float(row.sta_lon), float(row.sta_lat))
        match = next((feature for feature in features if feature["geometry"].contains(point) or feature["geometry"].touches(point)), None)
        records.append(
            {
                "station": row.station,
                "station_region": None if match is None else match["long_name"],
                "station_region_display": None if match is None else match["display_name"],
            }
        )
    return pd.DataFrame(records)


def basin_order(values: pd.Series) -> list[str]:
    present = set(values.dropna().astype(str))
    ordered = [BASELINE_REGION] if BASELINE_REGION in present else []
    ordered.extend(sorted([value for value in present if value != BASELINE_REGION], key=lambda item: display_region(item).casefold()))
    return ordered


def choose_representatives(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.Series] = []
    for (passband, region), group in df.groupby(["band", "station_region"], dropna=False):
        values = pd.to_numeric(group["log2_residual"], errors="coerce")
        median = float(np.nanmedian(values.to_numpy(dtype=float)))
        candidates = group.loc[np.isfinite(values)].copy()
        if candidates.empty:
            continue
        candidates["selection_target_median"] = median
        candidates["selection_abs_delta"] = (pd.to_numeric(candidates["log2_residual"], errors="coerce") - median).abs()
        candidates = candidates.sort_values(
            ["selection_abs_delta", "distance_km", "event_id", "station", "component"],
            na_position="last",
        )
        rows.append(candidates.iloc[0])
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).reset_index(drop=True)


def resolve_path(project_root: Path, value: object) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else project_root / path


def load_waveform(path: Path, component: object) -> tuple[np.ndarray, float]:
    payload = np.load(path, allow_pickle=False)
    data = np.asarray(payload["data"], dtype=float)
    rate = float(np.asarray(payload["sampling_rate"]).reshape(-1)[0])
    channels = [str(item) for item in np.asarray(payload["channels"]).tolist()] if "channels" in payload.files else []
    comp = str(component).strip().upper()
    if data.ndim == 1:
        trace = data
    else:
        index = component_index(channels, comp)
        trace = data[index] if data.shape[0] == len(channels) else data[:, index]
    trace = np.asarray(trace, dtype=float).reshape(-1)
    return np.where(np.isfinite(trace), trace, 0.0), rate


def component_index(channels: list[str], component: str) -> int:
    for index, channel in enumerate(channels):
        if channel.upper().endswith(component.upper()):
            return index
    return {"R": 0, "T": 1, "Z": 2}.get(component.upper(), 0)


def bandpass_for_plot(samples: np.ndarray, rate: float, passband: object) -> np.ndarray:
    corners = passband_corner_hz(passband)
    if corners is None or not np.isfinite(rate) or rate <= 0.0:
        return np.asarray(samples, dtype=float)
    low_hz, high_hz = corners
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
    finite = np.concatenate([obs[np.isfinite(obs)], syn[np.isfinite(syn)]])
    if finite.size == 0:
        return 1.0
    scale = float(np.nanmax(np.abs(finite)))
    return scale if np.isfinite(scale) and scale > 0.0 else 1.0


def plot_contact_sheet(rows: pd.DataFrame, output_path: Path, *, passband: str, project_root: Path) -> list[dict[str, object]]:
    ordered_regions = basin_order(rows["station_region"])
    rows = rows.set_index("station_region").loc[ordered_regions].reset_index()
    fig, axes = plt.subplots(len(rows), 1, figsize=(13.5, 2.15 * len(rows) + 1.0), dpi=180, sharex=False)
    if len(rows) == 1:
        axes = np.array([axes])
    status_rows: list[dict[str, object]] = []
    for ax, row in zip(axes, rows.itertuples(index=False)):
        obs_path = resolve_path(project_root, row.obs_waveform_path)
        syn_path = resolve_path(project_root, row.syn_waveform_path)
        try:
            obs, obs_rate = load_waveform(obs_path, row.component)
            syn, syn_rate = load_waveform(syn_path, row.component)
            obs = bandpass_for_plot(obs, obs_rate, passband)
            syn = bandpass_for_plot(syn, syn_rate, passband)
            obs_time = np.arange(obs.size, dtype=float) / obs_rate
            syn_time = np.arange(syn.size, dtype=float) / syn_rate
            scale = pair_scale(obs, syn)
            ax.plot(obs_time, obs / scale, color="#1f77b4", linewidth=0.85, label="observed")
            ax.plot(syn_time, syn / scale, color="#d95f02", linewidth=0.85, alpha=0.90, label="synthetic")
            ax.set_xlim(0.0, max(float(np.nanmax(obs_time)), float(np.nanmax(syn_time))))
            ax.set_ylim(-1.18, 1.18)
            status = "rendered"
        except Exception as exc:  # noqa: BLE001
            ax.text(0.01, 0.5, f"Could not load waveform: {exc}", transform=ax.transAxes, va="center", fontsize=8)
            status = f"error: {exc}"
        ax.axhline(0.0, color="#777777", linewidth=0.5)
        ax.grid(True, color="#e5e5e5", linewidth=0.55)
        ax.set_ylabel(str(row.component), rotation=0, labelpad=20, fontsize=9, weight="bold")
        ax.set_title(
            (
                f"{display_region(row.station_region)} | {row.event_id} -> {row.station} | comp {row.component} | "
                f"log2 resid {float(row.log2_residual):+.2f} "
                f"(basin median {float(row.selection_target_median):+.2f}) | "
                f"obs dur {float(row.value_obs):.2f}s, syn dur {float(row.value_syn):.2f}s | "
                f"dist {float(row.distance_km):.1f} km"
            ),
            fontsize=8.5,
            loc="left",
        )
        status_rows.append(
            {
                "passband": passband,
                "station_region": display_region(row.station_region),
                "event_id": row.event_id,
                "station": row.station,
                "component": row.component,
                "log2_residual": float(row.log2_residual),
                "selection_target_median": float(row.selection_target_median),
                "selection_abs_delta": float(row.selection_abs_delta),
                "value_obs": float(row.value_obs),
                "value_syn": float(row.value_syn),
                "distance_km": float(row.distance_km),
                "obs_waveform_path": str(obs_path),
                "syn_waveform_path": str(syn_path),
                "status": status,
            }
        )
    axes[0].legend(loc="upper right", fontsize=8, frameon=False)
    axes[-1].set_xlabel("Time from waveform start (s)")
    fig.suptitle(f"Representative observed vs synthetic waveforms by basin polygon | Arias duration | {passband}", fontsize=13)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.975))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return status_rows


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    features = load_basin_features(args.geojson.expanduser())
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
        "distance_km",
        "sta_lat",
        "sta_lon",
        "obs_waveform_path",
        "syn_waveform_path",
    ]
    df = pd.read_parquet(args.metrics.expanduser(), columns=columns)
    df = df.loc[
        df["model"].astype(str).eq(str(args.model))
        & df["metric"].astype(str).eq(METRIC)
        & df["band"].astype(str).isin(PASSBANDS)
    ].copy()
    df["log2_residual"] = pd.to_numeric(df["log2_residual"], errors="coerce")
    df["value_obs"] = pd.to_numeric(df["value_obs"], errors="coerce")
    df["value_syn"] = pd.to_numeric(df["value_syn"], errors="coerce")
    df["distance_km"] = pd.to_numeric(df["distance_km"], errors="coerce")
    df = df.dropna(subset=["log2_residual", "value_obs", "value_syn", "obs_waveform_path", "syn_waveform_path"])
    station_regions = assign_station_regions(df, features)
    df = df.merge(station_regions, on="station", how="left")
    df = df.loc[df["station_region"].notna()].copy()

    representatives = choose_representatives(df)
    manifest_rows: list[dict[str, object]] = []
    figures: list[str] = []
    for passband in PASSBANDS:
        passband_rows = representatives.loc[representatives["band"].astype(str).eq(passband)].copy()
        if passband_rows.empty:
            continue
        output_path = output_dir / f"representative_waveforms__arias_duration__{slug(passband.replace(' sec', 's'))}__Basin.png"
        status_rows = plot_contact_sheet(passband_rows, output_path, passband=passband, project_root=args.project_root.expanduser())
        manifest_rows.extend(status_rows)
        figures.append(str(output_path))

    manifest_csv = output_dir / "representative_waveform_selection.csv"
    pd.DataFrame(manifest_rows).to_csv(manifest_csv, index=False)
    manifest = {
        "metrics": str(args.metrics),
        "geojson": str(args.geojson),
        "project_root": str(args.project_root),
        "output_dir": str(output_dir),
        "model": args.model,
        "metric": METRIC,
        "selection": "one row per basin/passband closest to the per-basin median raw log2_residual using all event-station-component rows",
        "figures": figures,
        "selection_csv": str(manifest_csv),
        "selection_rows": len(manifest_rows),
    }
    manifest_json = output_dir / "representative_waveform_manifest.json"
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
