#!/usr/bin/env python3
"""Build basin metric diagnostics with and without event means removed."""

from __future__ import annotations

import argparse
import json
import math
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
from shapely.geometry import MultiPolygon, Point, Polygon, shape


DEFAULT_METRICS = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/tables/metrics_long.parquet")
DEFAULT_GEOJSON = Path("/project2/jvidale_1700/spatial-vtk/runs/inputs/geospatial/regions_updated.geojson")
DEFAULT_OUTPUT_DIR = Path(
    "/project2/jvidale_1700/spatial-vtk/runs/outputs/figures/user_requested_basin_event_centered_diagnostics"
)
DEFAULT_MODEL = "cvmsi_20260506_material_0p6x1p2_asdf"
DEFAULT_TARGET_METRICS = ("arias_duration",)
REGION_TYPE = "Basin"
ALL_REGION_TYPES = "all"
BASELINE_REGION = "Los Angeles Basin"
PASSBANDS = ("1-2 sec", "2-3 sec", "3-5 sec")
COMPONENT_LABEL = "R, T, Z"
DISPLAY_NAMES = {"San Bernadino Basin": "San Bernardino Basin"}


@dataclass(frozen=True)
class RegionFeature:
    long_name: str
    short_name: str
    region_type: str
    geometry: object


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--geojson", type=Path, default=DEFAULT_GEOJSON)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--target-metrics", nargs="+", default=list(DEFAULT_TARGET_METRICS))
    parser.add_argument("--region-type", default=REGION_TYPE, help="GeoJSON region_type to use, or 'all' for all polygon features.")
    parser.add_argument("--exclude-regions", nargs="*", default=[], help="GeoJSON long_name/short_name values to exclude before station assignment and plotting.")
    parser.add_argument("--hide-labels", action="store_true", help="Do not draw polygon labels.")
    parser.add_argument("--drop-empty-polygons", action="store_true", help="For each map, draw only polygons containing stations in that plotted subset.")
    parser.add_argument("--add-basemap", action="store_true", help="Draw a contextily basemap under the polygons when available.")
    parser.add_argument("--basemap-source", default="CartoDB.Positron", help="Contextily provider name for --add-basemap.")
    parser.add_argument("--marker-size", type=float, default=42.0, help="Station marker size in points^2.")
    parser.add_argument("--include-boxplots", action="store_true")
    return parser.parse_args()


def slug(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "unknown"


def display_region(value: object) -> str:
    text = str(value)
    return DISPLAY_NAMES.get(text, text)


def display_region_type(value: object) -> str:
    text = str(value)
    return "All GeoJSON Polygons" if text.strip().lower() == ALL_REGION_TYPES else text


def load_regions(path: Path) -> list[RegionFeature]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    features: list[RegionFeature] = []
    for index, feature in enumerate(payload.get("features", [])):
        props = feature.get("properties", {}) or {}
        geom_payload = feature.get("geometry")
        if not geom_payload:
            continue
        long_name = str(props.get("long_name") or props.get("name") or props.get("short_name") or f"feature_{index}")
        region_type = str(props.get("region_type") or props.get("mapped_region_type") or "unmapped")
        features.append(
            RegionFeature(
                long_name=long_name,
                short_name=str(props.get("short_name") or long_name),
                region_type=region_type,
                geometry=shape(geom_payload),
            )
        )
    if not features:
        raise ValueError(f"No GeoJSON polygon features found in {path}")
    return features


def filter_excluded_regions(features: list[RegionFeature], excluded: Iterable[object]) -> list[RegionFeature]:
    excluded_names = {str(value).strip().casefold() for value in excluded if str(value).strip()}
    if not excluded_names:
        return features
    return [
        feature
        for feature in features
        if feature.long_name.casefold() not in excluded_names and feature.short_name.casefold() not in excluded_names
    ]


def assign_station_regions(metrics: pd.DataFrame, features: list[RegionFeature]) -> pd.DataFrame:
    station_rows = metrics[["station", "sta_lon", "sta_lat"]].dropna().drop_duplicates("station").copy()
    records: list[dict[str, object]] = []
    for row in station_rows.itertuples(index=False):
        point = Point(float(row.sta_lon), float(row.sta_lat))
        matches = [feature for feature in features if feature.geometry.contains(point) or feature.geometry.touches(point)]
        primary = matches[0] if matches else None
        records.append(
            {
                "station": row.station,
                "station_region": None if primary is None else primary.long_name,
                "station_region_type": None if primary is None else primary.region_type,
                "station_region_short": None if primary is None else primary.short_name,
            }
        )
    return pd.DataFrame(records)


def add_event_centered_residuals(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["log2_residual"] = pd.to_numeric(work["log2_residual"], errors="coerce")
    group_cols = ["metric", "band", "model", "event_id"]
    if "period_s" in work.columns and work["period_s"].notna().any():
        group_cols.append("period_s")
    event_stats = (
        work.replace([np.inf, -np.inf], np.nan)
        .dropna(subset=["log2_residual"])
        .groupby(group_cols, dropna=False)
        .agg(event_mean=("log2_residual", "mean"), event_station_count=("station", "nunique"))
        .reset_index()
    )
    work = work.merge(event_stats, on=group_cols, how="left")
    work["event_centered_log2_residual"] = work["log2_residual"] - work["event_mean"]
    return work


def basin_order(df: pd.DataFrame) -> list[str]:
    present = list(df["station_region"].dropna().astype(str).unique())
    out = [BASELINE_REGION] if BASELINE_REGION in present else []
    out.extend(sorted([value for value in present if value != BASELINE_REGION], key=str.casefold))
    return out


def bootstrap_ci(
    values: np.ndarray,
    baseline: np.ndarray,
    *,
    rng: np.random.Generator,
    samples: int = 2000,
) -> tuple[float, float]:
    if values.size == 0 or baseline.size == 0:
        return math.nan, math.nan
    effects = np.empty(samples, dtype=float)
    for index in range(samples):
        left = rng.choice(values, size=values.size, replace=True)
        right = rng.choice(baseline, size=baseline.size, replace=True)
        effects[index] = float(np.nanmedian(left) - np.nanmedian(right))
    return float(np.nanpercentile(effects, 2.5)), float(np.nanpercentile(effects, 97.5))


def comparison_table(df: pd.DataFrame, order: list[str], value_col: str) -> pd.DataFrame:
    baseline = pd.to_numeric(df.loc[df["station_region"].eq(BASELINE_REGION), value_col], errors="coerce").dropna()
    baseline_values = baseline.to_numpy(dtype=float)
    rng = np.random.default_rng(20260624)
    rows: list[dict[str, object]] = []
    for region in order:
        if region == BASELINE_REGION:
            continue
        values = pd.to_numeric(df.loc[df["station_region"].eq(region), value_col], errors="coerce").dropna()
        region_values = values.to_numpy(dtype=float)
        if values.empty or baseline.empty:
            effect = math.nan
            pvalue = math.nan
            ci_low = math.nan
            ci_high = math.nan
        else:
            effect = float(np.nanmedian(region_values) - np.nanmedian(baseline_values))
            pvalue = float(mannwhitneyu(region_values, baseline_values, alternative="two-sided").pvalue)
            ci_low, ci_high = bootstrap_ci(region_values, baseline_values, rng=rng)
        rows.append(
            {
                "Comparison": f"5-95%: {display_region(region)} - {display_region(BASELINE_REGION)}",
                "Effect": effect,
                "CI_low": ci_low,
                "CI_high": ci_high,
                "p": pvalue,
                "n": f"{int(values.size)}/{int(baseline.size)}",
            }
        )
    return pd.DataFrame(rows)


def format_effect(value: object) -> str:
    if not np.isfinite(value):
        return "nan"
    return f"{float(value):+.3g}"


def format_p(value: object) -> str:
    if not np.isfinite(value):
        return "nan"
    return "<0.001" if float(value) < 0.001 else f"{float(value):.3g}"


def format_ci(low: object, high: object) -> str:
    if not np.isfinite(low) or not np.isfinite(high):
        return "nan"
    return f"{format_effect(low)} to {format_effect(high)}"


def draw_boxplot(df: pd.DataFrame, output_path: Path, *, passband: str, value_col: str, model: str) -> dict[str, object]:
    plot_df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=[value_col, "station_region"]).copy()
    order = basin_order(plot_df)
    data = [pd.to_numeric(plot_df.loc[plot_df["station_region"].eq(region), value_col], errors="coerce").dropna().to_numpy() for region in order]
    comparisons = comparison_table(plot_df, order, value_col)

    fig = plt.figure(figsize=(13.6, 9.0), dpi=150)
    ax = fig.add_axes([0.07, 0.33, 0.88, 0.50])
    table_ax = fig.add_axes([0.07, 0.06, 0.88, 0.18])
    table_ax.axis("off")

    box = ax.boxplot(data, positions=np.arange(1, len(order) + 1), widths=0.28, patch_artist=True, showfliers=False)
    for patch in box["boxes"]:
        patch.set(facecolor="#9ecae1", edgecolor="#6baed6", alpha=0.65, linewidth=1.4)
    for element in ("whiskers", "caps"):
        for artist in box[element]:
            artist.set(color="#1f1f1f", linewidth=1.2)
    for artist in box["medians"]:
        artist.set(color="#1f1f1f", linewidth=1.4)

    rng = np.random.default_rng(42)
    for xpos, values in enumerate(data, start=1):
        if len(values) == 0:
            continue
        jitter = rng.normal(0.0, 0.030, size=len(values))
        ax.scatter(
            np.full(len(values), xpos, dtype=float) + jitter,
            values,
            s=30,
            color="#2b83ba",
            edgecolor="#1f4e79",
            linewidth=0.35,
            alpha=0.62,
            zorder=2,
        )
    ax.axhline(0.0, color="black", linestyle=":", linewidth=1.1)
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.8, alpha=0.75)
    ax.set_xticks(np.arange(1, len(order) + 1))
    ax.set_xticklabels([display_region(region) for region in order], rotation=24, ha="right", fontsize=14)
    ax.tick_params(axis="y", labelsize=14)
    ax.set_ylabel("Event-centered log2(observed / synthetic)", fontsize=15)
    ax.set_title(
        "\n".join(
            [
                "arias_duration Residuals by Station Region",
                "Mapped Region Type: Basin",
                f"Model: CVM-SI | Period: {passband.replace(' sec', '')} sec | Component: {COMPONENT_LABEL} | Processing: event mean removed",
                f"Rows: {len(plot_df):,}, Events: {plot_df['event_id'].nunique():,}, Stations: {plot_df['station'].nunique():,}",
            ]
        ),
        fontsize=16,
        pad=8,
    )

    table_data = [
        [row["Comparison"], format_effect(row["Effect"]), format_ci(row["CI_low"], row["CI_high"]), format_p(row["p"]), row["n"]]
        for _, row in comparisons.iterrows()
    ]
    table = table_ax.table(
        cellText=table_data,
        colLabels=["Comparison", "Effect", "95% CI", "p", "n"],
        colLoc="left",
        cellLoc="left",
        loc="center",
        colWidths=[0.44, 0.12, 0.25, 0.10, 0.08],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10.5)
    table.scale(1.0, 1.45)
    for (row, _col), cell in table.get_celld().items():
        cell.set_edgecolor("#d0d0d0")
        if row == 0:
            cell.set_facecolor("#eeeeee")
            cell.set_text_props(weight="bold")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return {
        "figure": str(output_path),
        "rows": int(len(plot_df)),
        "events": int(plot_df["event_id"].nunique()),
        "stations": int(plot_df["station"].nunique()),
        "comparison_rows": int(len(comparisons)),
    }


def iter_polygon_exteriors(geom: object) -> Iterable[np.ndarray]:
    if isinstance(geom, Polygon):
        yield np.asarray(geom.exterior.coords)
    elif isinstance(geom, MultiPolygon):
        for polygon in geom.geoms:
            yield np.asarray(polygon.exterior.coords)


def station_summary(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    values = df.replace([np.inf, -np.inf], np.nan).dropna(subset=[value_col, "sta_lon", "sta_lat"]).copy()
    return (
        values.groupby(["station", "station_region", "sta_lon", "sta_lat"], dropna=False)
        .agg(
            station_residual=(value_col, "median"),
            n_rows=(value_col, "size"),
            n_events=("event_id", "nunique"),
        )
        .reset_index()
    )


def basin_row_medians(df: pd.DataFrame, value_col: str) -> pd.Series:
    values = df.replace([np.inf, -np.inf], np.nan).dropna(subset=[value_col, "station_region"]).copy()
    return values.groupby("station_region", dropna=False)[value_col].median()


def draw_basin_polygons(
    ax: plt.Axes,
    features: list[RegionFeature],
    names: set[str],
    *,
    region_values: pd.Series,
    norm: TwoSlopeNorm,
    cmap: object,
) -> None:
    for feature in features:
        if feature.long_name not in names:
            continue
        value = region_values.get(feature.long_name, np.nan)
        facecolor = "#eeeeee" if not np.isfinite(value) else cmap(norm(float(value)))
        for coords in iter_polygon_exteriors(feature.geometry):
            ax.fill(
                coords[:, 0],
                coords[:, 1],
                facecolor=facecolor,
                edgecolor="#444444",
                alpha=0.50,
                linewidth=1.1,
                zorder=1,
            )


def spread_label_positions(desired: list[float], *, low: float = 0.035, high: float = 0.965) -> list[float]:
    """Return y positions spread across an axes-fraction margin."""

    count = len(desired)
    if count == 0:
        return []
    if count == 1:
        return [float(np.clip(desired[0], low, high))]
    min_sep = min(0.075, (high - low) / max(count - 1, 1))
    order = np.argsort(desired)
    sorted_desired = np.asarray([desired[index] for index in order], dtype=float)
    positions = np.clip(sorted_desired, low, high)
    for index in range(1, count):
        positions[index] = max(positions[index], positions[index - 1] + min_sep)
    overflow = positions[-1] - high
    if overflow > 0:
        positions -= overflow
    for index in range(count - 2, -1, -1):
        positions[index] = min(positions[index], positions[index + 1] - min_sep)
    positions = np.clip(positions, low, high)
    out = [0.0] * count
    for sorted_index, original_index in enumerate(order):
        out[int(original_index)] = float(positions[sorted_index])
    return out


def add_polygon_labels(ax: plt.Axes, features: list[RegionFeature], names: set[str]) -> None:
    """Draw labels outside the polygons with leader lines to reduce map clutter."""

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    x_mid = 0.5 * (xlim[0] + xlim[1])
    y_span = max(float(ylim[1] - ylim[0]), 1e-9)
    left_items: list[tuple[RegionFeature, object, float]] = []
    right_items: list[tuple[RegionFeature, object, float]] = []
    for feature in features:
        if feature.long_name not in names:
            continue
        point = feature.geometry.representative_point()
        y_frac = float((point.y - ylim[0]) / y_span)
        target = left_items if point.x < x_mid else right_items
        target.append((feature, point, y_frac))

    for side, items in (("left", left_items), ("right", right_items)):
        positions = spread_label_positions([item[2] for item in items])
        x_text = -0.045 if side == "left" else 1.045
        ha = "right" if side == "left" else "left"
        rad = 0.08 if side == "left" else -0.08
        for (feature, point, _y_frac), y_text in zip(items, positions, strict=True):
            label = "\n".join(textwrap.wrap(display_region(feature.long_name).replace(" Basin", ""), width=16))
            ax.annotate(
                label,
                xy=(point.x, point.y),
                xycoords="data",
                xytext=(x_text, y_text),
                textcoords="axes fraction",
                ha=ha,
                va="center",
                fontsize=7.2,
                color="#202020",
                bbox={"facecolor": "white", "edgecolor": "#bdbdbd", "alpha": 0.70, "pad": 1.2},
                arrowprops={
                    "arrowstyle": "-",
                    "color": "#404040",
                    "linewidth": 0.55,
                    "alpha": 0.70,
                    "connectionstyle": f"arc3,rad={rad}",
                },
                annotation_clip=False,
                zorder=5,
            )


def feature_bounds(features: list[RegionFeature]) -> tuple[float, float, float, float]:
    bounds = [feature.geometry.bounds for feature in features]
    minx = min(float(item[0]) for item in bounds)
    miny = min(float(item[1]) for item in bounds)
    maxx = max(float(item[2]) for item in bounds)
    maxy = max(float(item[3]) for item in bounds)
    return minx, miny, maxx, maxy


def add_map_basemap(ax: plt.Axes, *, add_basemap: bool, basemap_source: str) -> str | None:
    if not add_basemap:
        return None
    try:
        from spatial_vtk.spatial.map.basemaps import add_contextily_basemap

        ok, source = add_contextily_basemap(
            ax,
            crs="EPSG:4326",
            primary_source=basemap_source,
            fallback_sources=("CartoDB.Positron", "Esri.WorldTopoMap", "OpenStreetMap.Mapnik"),
            attribution=False,
            on_error="warn",
        )
        return source if ok else f"fallback: {source}"
    except Exception as exc:
        ax.set_facecolor("#eef2f4")
        return f"fallback: {type(exc).__name__}: {exc}"


def draw_station_map(
    raw_df: pd.DataFrame,
    centered_df: pd.DataFrame,
    features: list[RegionFeature],
    output_path: Path,
    *,
    metric: str,
    passband: str,
    model: str,
    region_label: str,
    marker_size: float,
    add_basemap: bool,
    basemap_source: str,
    show_labels: bool,
) -> dict[str, object]:
    polygon_names = {feature.long_name for feature in features}
    station_region_names = set(raw_df["station_region"].dropna().astype(str).unique())
    raw_station = station_summary(raw_df, "log2_residual")
    centered_station = station_summary(centered_df, "event_centered_log2_residual")
    raw_basin_medians = basin_row_medians(raw_df, "log2_residual")
    centered_basin_medians = basin_row_medians(centered_df, "event_centered_log2_residual")
    cmap = plt.get_cmap("seismic")

    fig, axes = plt.subplots(1, 2, figsize=(21.0, 9.0), dpi=180, sharex=True, sharey=True)
    fig.subplots_adjust(left=0.105, right=0.895, bottom=0.19, top=0.84, wspace=0.36)
    panels = [
        (axes[0], raw_station, raw_basin_medians, "Event mean not removed"),
        (axes[1], centered_station, centered_basin_medians, "Event mean removed"),
    ]
    minx, miny, maxx, maxy = feature_bounds(features)
    pad_x = max(0.08, (maxx - minx) * 0.04)
    pad_y = max(0.06, (maxy - miny) * 0.04)
    xlim = (minx - pad_x, maxx + pad_x)
    ylim = (miny - pad_y, maxy + pad_y)
    basemap_sources: list[str] = []
    for ax, stations, basin_medians, title in panels:
        panel_values = pd.concat([stations["station_residual"], basin_medians], ignore_index=True)
        vmax = float(np.nanpercentile(np.abs(panel_values.to_numpy(dtype=float)), 95)) if not panel_values.empty else 1.0
        vmax = max(vmax, 0.25)
        norm = TwoSlopeNorm(vcenter=0.0, vmin=-vmax, vmax=vmax)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        basemap_source_used = add_map_basemap(ax, add_basemap=add_basemap, basemap_source=basemap_source)
        if basemap_source_used is not None:
            basemap_sources.append(basemap_source_used)
        draw_basin_polygons(ax, features, polygon_names, region_values=basin_medians, norm=norm, cmap=cmap)
        if show_labels:
            add_polygon_labels(ax, features, polygon_names)
        scatter = ax.scatter(
            stations["sta_lon"],
            stations["sta_lat"],
            c=stations["station_residual"],
            cmap=cmap,
            norm=norm,
            s=marker_size,
            edgecolor="#222222",
            linewidth=0.35,
            alpha=0.92,
            zorder=4,
        )
        colorbar = fig.colorbar(scatter, ax=ax, location="bottom", shrink=0.74, pad=0.11, aspect=38)
        colorbar.set_label("Median log2(observed / synthetic)")
        ax.set_title(title, fontsize=13, weight="semibold")
        ax.set_xlabel("Longitude")
        ax.grid(color="#d0d0d0", linewidth=0.65, alpha=0.65)
        ax.set_aspect("equal", adjustable="box")
        ax.text(
            0.01,
            0.02,
            f"{len(stations):,} stations",
            transform=ax.transAxes,
            fontsize=9,
            ha="left",
            va="bottom",
            bbox={"facecolor": "white", "edgecolor": "#cccccc", "alpha": 0.85, "pad": 3},
        )
    axes[0].set_ylabel("Latitude")

    fig.suptitle(
        f"{metric} Station Residuals in {region_label} | CVM-SI | {passband} | components {COMPONENT_LABEL}",
        fontsize=15,
        y=0.965,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return {
        "figure": str(output_path),
        "raw_station_count": int(len(raw_station)),
        "centered_station_count": int(len(centered_station)),
        "displayed_polygon_count": int(len(features)),
        "station_polygon_count": int(len(station_region_names)),
        "regions_with_stations": sorted(display_region(name) for name in station_region_names),
        "basemap_sources": sorted(set(basemap_sources)),
        "raw_basin_row_medians": {display_region(key): float(value) for key, value in raw_basin_medians.items()},
        "centered_basin_row_medians": {display_region(key): float(value) for key, value in centered_basin_medians.items()},
    }


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    features = load_regions(args.geojson.expanduser())
    requested_region_type = str(args.region_type)
    if requested_region_type.strip().lower() == ALL_REGION_TYPES:
        selected_features = features
    else:
        selected_features = [feature for feature in features if feature.region_type == requested_region_type]
    selected_features = filter_excluded_regions(selected_features, args.exclude_regions)
    if not selected_features:
        raise ValueError(f"No GeoJSON features matched region type {requested_region_type!r} in {args.geojson}")
    region_label = display_region_type(requested_region_type)
    region_slug = "all-regions" if requested_region_type.strip().lower() == ALL_REGION_TYPES else slug(requested_region_type)

    columns = [
        "event_id",
        "station",
        "component",
        "model",
        "metric",
        "band",
        "period_s",
        "log2_residual",
        "sta_lat",
        "sta_lon",
    ]
    metrics = pd.read_parquet(args.metrics.expanduser(), columns=columns)
    manifest: dict[str, object] = {
        "metrics": str(args.metrics),
        "geojson": str(args.geojson),
        "output_dir": str(output_dir),
        "model": args.model,
        "target_metrics": [str(metric) for metric in args.target_metrics],
        "region_type": requested_region_type,
        "displayed_polygon_count": int(len(selected_features)),
        "excluded_regions": [str(value) for value in args.exclude_regions],
        "add_basemap": bool(args.add_basemap),
        "basemap_source": str(args.basemap_source),
        "marker_size": float(args.marker_size),
        "hide_labels": bool(args.hide_labels),
        "drop_empty_polygons": bool(args.drop_empty_polygons),
        "processing": "event mean removed for centered plots; raw log2 residuals retained for comparison maps",
        "event_centering": "metric/band/model/event_id, with period_s included when present",
        "figures": [],
    }

    for metric in [str(value) for value in args.target_metrics]:
        work = metrics.loc[
            metrics["model"].astype(str).eq(str(args.model))
            & metrics["metric"].astype(str).eq(metric)
            & metrics["band"].astype(str).isin(PASSBANDS)
        ].copy()
        if work.empty:
            manifest["figures"].append({"metric": metric, "status": "skipped", "message": "no rows after metric/model/band filter"})
            continue
        work = add_event_centered_residuals(work)
        station_regions = assign_station_regions(work, selected_features)
        work = work.merge(station_regions, on="station", how="left")
        if requested_region_type.strip().lower() == ALL_REGION_TYPES:
            work = work.loc[work["station_region"].notna()].copy()
        else:
            work = work.loc[work["station_region_type"].astype(str).eq(requested_region_type)].copy()
        metric_summary = {
            "metric": metric,
            "source_rows_after_metric_model_band_filter": int(len(work)),
            "region_station_count": int(work["station"].nunique()),
            "displayed_polygon_count": int(len(selected_features)),
            "regions_with_stations": sorted(display_region(name) for name in work["station_region"].dropna().astype(str).unique()),
            "passbands": [],
        }

        for passband in PASSBANDS:
            passband_df = work.loc[work["band"].astype(str).eq(passband)].copy()
            if passband_df.empty:
                metric_summary["passbands"].append({"passband": passband, "status": "skipped", "message": "no rows"})
                continue
            map_features = selected_features
            if args.drop_empty_polygons:
                station_polygon_names = set(passband_df["station_region"].dropna().astype(str).unique())
                map_features = [feature for feature in selected_features if feature.long_name in station_polygon_names]
            box_meta = None
            if args.include_boxplots:
                boxplot_path = output_dir / (
                    f"region_boxplot__{slug(metric)}__{slug(passband.replace(' sec', 's'))}"
                    f"__{region_slug}__all-components__event_mean_removed__log2_residual.png"
                )
                box_meta = draw_boxplot(
                    passband_df,
                    boxplot_path,
                    passband=passband,
                    value_col="event_centered_log2_residual",
                    model=args.model,
                )
            map_path = output_dir / (
                f"station_map__{slug(metric)}__{slug(passband.replace(' sec', 's'))}"
                f"__{region_slug}__raw_vs_event_mean_removed__log2_residual.png"
            )
            map_meta = draw_station_map(
                passband_df,
                passband_df,
                map_features,
                map_path,
                metric=metric,
                passband=passband,
                model=args.model,
                region_label=region_label,
                marker_size=float(args.marker_size),
                add_basemap=bool(args.add_basemap),
                basemap_source=str(args.basemap_source),
                show_labels=not bool(args.hide_labels),
            )
            row = {"passband": passband, "map": map_meta, "status": "wrote"}
            if box_meta is not None:
                row["boxplot"] = box_meta
            metric_summary["passbands"].append(row)
        manifest["figures"].append(metric_summary)

    manifest_path = output_dir / "basin_event_centered_diagnostics_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
