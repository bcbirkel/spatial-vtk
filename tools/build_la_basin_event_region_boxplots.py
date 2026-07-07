#!/usr/bin/env python3
"""Build LA Basin-station residual boxplots grouped by event GeoJSON region."""

from __future__ import annotations

import argparse
import json
import math
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
from shapely.geometry import Point, shape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


DEFAULT_OUTPUT_DIR = Path(
    "/project2/jvidale_1700/spatial-vtk/runs/outputs/figures/user_requested_la_basin_event_region_boxplots"
)
DEFAULT_METRICS = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/tables/metrics_long.parquet")
DEFAULT_GEOJSON = Path("/project2/jvidale_1700/spatial-vtk/runs/inputs/geospatial/regions_updated.geojson")
DEFAULT_MODEL = "cvmsi_20260506_material_0p6x1p2_asdf"
BASELINE_REGION = "Los Angeles Basin"
PASSBAND_SCOPES: tuple[str | None, ...] = (None, "1-2 sec", "2-3 sec", "3-5 sec")
VALUE_METRICS = {"original_cc", "delay_corrected_cc", "traveltime_delay"}
ALPHA = 0.05

FONT_FAMILY = ["Aptos", "Inter", "Segoe UI", "DejaVu Sans", "Arial", "sans-serif"]
MONO_FONT_FAMILY = ["SF Mono", "Menlo", "Consolas", "DejaVu Sans Mono", "monospace"]
TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}
TYPE_COLORS = {
    "Basin": "#A3BEFA",
    "Hills": "#FFE15B",
    "Mountains": "#F0986E",
    "Other": "#C5CAD3",
    "Valley": "#A3D576",
}
TYPE_EDGES = {
    "Basin": "#2E4780",
    "Hills": "#736422",
    "Mountains": "#804126",
    "Other": "#464C55",
    "Valley": "#386411",
}


@dataclass(frozen=True)
class RegionFeature:
    index: int
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
    parser.add_argument("--alpha", type=float, default=ALPHA)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def use_chart_theme() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": TOKENS["surface"],
            "figure.edgecolor": "none",
            "savefig.facecolor": TOKENS["surface"],
            "savefig.edgecolor": "none",
            "axes.facecolor": TOKENS["panel"],
            "axes.edgecolor": TOKENS["axis"],
            "axes.labelcolor": TOKENS["ink"],
            "axes.grid": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": TOKENS["grid"],
            "grid.linewidth": 0.8,
            "font.family": "sans-serif",
            "font.sans-serif": FONT_FAMILY,
            "font.monospace": MONO_FONT_FAMILY,
            "patch.linewidth": 1.0,
        }
    )


def add_chart_header(fig: plt.Figure, ax: plt.Axes, title: str, subtitle: str) -> None:
    title = textwrap.fill(str(title), width=82, break_long_words=False)
    subtitle = textwrap.fill(str(subtitle), width=128, break_long_words=False)
    title_lines = title.count("\n") + 1
    subtitle_lines = subtitle.count("\n") + 1
    ax.set_title("")
    fig.subplots_adjust(
        top=max(0.62, 0.86 - 0.045 * (title_lines - 1) - 0.030 * (subtitle_lines - 1)),
        bottom=0.24,
        left=0.08,
        right=0.985,
    )
    left = ax.get_position().x0
    fig.text(left, 0.985, title, ha="left", va="top", fontsize=13, fontweight="semibold", color=TOKENS["ink"])
    fig.text(
        left,
        0.93 - 0.045 * (title_lines - 1),
        subtitle,
        ha="left",
        va="top",
        fontsize=9,
        color=TOKENS["muted"],
        linespacing=1.18,
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def slug(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "all"


def load_regions(path: Path) -> list[RegionFeature]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    features: list[RegionFeature] = []
    for index, feature in enumerate(payload.get("features", [])):
        props = feature.get("properties", {}) or {}
        geom_payload = feature.get("geometry")
        if not geom_payload:
            continue
        long_name = str(props.get("long_name") or props.get("name") or props.get("short_name") or f"feature_{index}")
        features.append(
            RegionFeature(
                index=index,
                long_name=long_name,
                short_name=str(props.get("short_name") or long_name),
                region_type=str(props.get("region_type") or "Other"),
                geometry=shape(geom_payload),
            )
        )
    if not features:
        raise ValueError(f"No polygon features found in {path}")
    return features


def point_in_geom(lon: object, lat: object, geom: object) -> bool:
    if pd.isna(lon) or pd.isna(lat):
        return False
    point = Point(float(lon), float(lat))
    return bool(geom.contains(point) or geom.touches(point))


def matching_regions(lon: object, lat: object, features: list[RegionFeature]) -> list[RegionFeature]:
    if pd.isna(lon) or pd.isna(lat):
        return []
    point = Point(float(lon), float(lat))
    return [feature for feature in features if feature.geometry.contains(point) or feature.geometry.touches(point)]


def annotate_points(
    rows: pd.DataFrame,
    *,
    id_col: str,
    lon_col: str,
    lat_col: str,
    features: list[RegionFeature],
) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for row in rows[[id_col, lon_col, lat_col]].drop_duplicates(id_col).itertuples(index=False):
        matches = matching_regions(getattr(row, lon_col), getattr(row, lat_col), features)
        primary = matches[0] if matches else None
        records.append(
            {
                id_col: getattr(row, id_col),
                "region": None if primary is None else primary.long_name,
                "region_short_name": None if primary is None else primary.short_name,
                "region_type": None if primary is None else primary.region_type,
                "region_feature_index": None if primary is None else primary.index,
                "matching_region_count": len(matches),
                "matching_regions": ";".join(feature.long_name for feature in matches),
            }
        )
    return pd.DataFrame(records)


def value_column_for_metric(metric: str) -> str:
    return "value" if metric in VALUE_METRICS else "log2_residual"


def value_label(metric: str, value_col: str) -> str:
    if metric == "traveltime_delay":
        return "Traveltime delay (s)"
    if metric in {"original_cc", "delay_corrected_cc"}:
        return "Cross-correlation coefficient"
    if value_col == "log2_residual":
        return "log2(observed / synthetic)"
    return value_col.replace("_", " ").title()


def holm_adjust(pvalues: list[float]) -> list[float]:
    m = len(pvalues)
    adjusted = [math.nan] * m
    finite = [(idx, p) for idx, p in enumerate(pvalues) if np.isfinite(p)]
    running = 0.0
    for rank, (idx, pvalue) in enumerate(sorted(finite, key=lambda item: item[1]), start=1):
        adj = min(1.0, pvalue * (m - rank + 1))
        running = max(running, adj)
        adjusted[idx] = running
    return adjusted


def significance_for_frame(
    frame: pd.DataFrame,
    *,
    metric: str,
    passband_scope: str,
    value_col: str,
    alpha: float,
    region_order: list[str],
) -> pd.DataFrame:
    baseline = pd.to_numeric(
        frame.loc[frame["event_region"].eq(BASELINE_REGION), "plot_value"],
        errors="coerce",
    ).dropna()
    rows: list[dict[str, object]] = []
    for region in region_order:
        if region == BASELINE_REGION:
            continue
        values = pd.to_numeric(frame.loc[frame["event_region"].eq(region), "plot_value"], errors="coerce").dropna()
        if values.empty or baseline.empty:
            pvalue = math.nan
            effect = math.nan
        else:
            pvalue = float(mannwhitneyu(values.to_numpy(), baseline.to_numpy(), alternative="two-sided").pvalue)
            effect = float(np.nanmedian(values.to_numpy()) - np.nanmedian(baseline.to_numpy()))
        rows.append(
            {
                "metric": metric,
                "passband_scope": passband_scope,
                "value_col": value_col,
                "baseline_region": BASELINE_REGION,
                "event_region": region,
                "event_region_type": region_type_for_region(frame, region),
                "n_region": int(values.size),
                "n_baseline": int(baseline.size),
                "median_region": float(np.nanmedian(values)) if not values.empty else math.nan,
                "median_baseline": float(np.nanmedian(baseline)) if not baseline.empty else math.nan,
                "median_difference": effect,
                "p_value": pvalue,
            }
        )
    adjusted = holm_adjust([float(row["p_value"]) for row in rows])
    for row, adj in zip(rows, adjusted):
        row["p_holm"] = adj
        row["alpha"] = alpha
        row["significant_holm"] = bool(np.isfinite(adj) and adj < alpha)
        row["test"] = "Mann-Whitney U, two-sided"
        row["correction"] = "Holm within metric/passband figure"
    return pd.DataFrame(rows)


def region_type_for_region(frame: pd.DataFrame, region: str) -> object:
    values = frame.loc[frame["event_region"].eq(region), "event_region_type"].dropna().astype(str).unique()
    return values[0] if len(values) else pd.NA


def ordered_regions(frame: pd.DataFrame, features: list[RegionFeature]) -> list[str]:
    present = set(frame["event_region"].dropna().astype(str))
    ordered = [BASELINE_REGION] if BASELINE_REGION in present else []
    ordered.extend(feature.long_name for feature in features if feature.long_name in present and feature.long_name != BASELINE_REGION)
    extras = sorted(present.difference(ordered))
    ordered.extend(extras)
    return ordered


def draw_boxplot(
    frame: pd.DataFrame,
    *,
    metric: str,
    passband_scope: str,
    value_col: str,
    region_order: list[str],
    sig_table: pd.DataFrame,
    output_path: Path,
) -> None:
    label_map = {
        region: f"{region} *" if bool(sig_table.loc[sig_table["event_region"].eq(region), "significant_holm"].any()) else region
        for region in region_order
    }
    plot_df = frame.copy()
    plot_df["event_region_label"] = plot_df["event_region"].map(label_map)
    order = [label_map[region] for region in region_order]
    colors = [TYPE_COLORS.get(str(region_type_for_region(frame, region)), "#C5CAD3") for region in region_order]
    edge_colors = [TYPE_EDGES.get(str(region_type_for_region(frame, region)), TOKENS["ink"]) for region in region_order]
    groups = [
        pd.to_numeric(plot_df.loc[plot_df["event_region"].eq(region), "plot_value"], errors="coerce").dropna().to_numpy()
        for region in region_order
    ]
    positions = np.arange(1, len(order) + 1)

    width = max(12.0, min(26.0, 0.82 * len(order) + 5.2))
    fig, ax = plt.subplots(figsize=(width, 7.4), dpi=180)
    box = ax.boxplot(
        groups,
        positions=positions,
        widths=0.62,
        patch_artist=True,
        showfliers=False,
        medianprops={"color": TOKENS["ink"], "linewidth": 1.1},
        whiskerprops={"color": TOKENS["muted"], "linewidth": 1.0},
        capprops={"color": TOKENS["muted"], "linewidth": 1.0},
    )
    for patch, fill, edge in zip(box["boxes"], colors, edge_colors):
        patch.set_facecolor(fill)
        patch.set_edgecolor(edge)
        patch.set_linewidth(1.0)
    rng = np.random.default_rng(42)
    for position, values in zip(positions, groups):
        if len(values) == 0:
            continue
        plotted = values
        if len(plotted) > 3500:
            plotted = rng.choice(plotted, size=3500, replace=False)
        jitter = rng.uniform(-0.22, 0.22, size=len(plotted))
        ax.scatter(
            np.full(len(plotted), position, dtype=float) + jitter,
            plotted,
            s=4.0,
            color="#464C55",
            alpha=0.16,
            linewidths=0,
            zorder=1,
        )
    if value_col == "log2_residual" or metric == "traveltime_delay":
        ax.axhline(0.0, color=TOKENS["ink"], linestyle=":", linewidth=1.0, zorder=0)
    ax.set_xlabel("Event GeoJSON region")
    ax.set_ylabel(value_label(metric, value_col))
    ax.set_xticks(positions)
    ax.set_xticklabels(order)
    ax.tick_params(axis="x", rotation=38, labelsize=8)
    for tick in ax.get_xticklabels():
        tick.set_ha("right")
    ax.tick_params(axis="y", labelsize=8, colors=TOKENS["muted"])
    ax.grid(True, axis="y", alpha=0.8)
    ax.grid(False, axis="x")

    legend_types = [typ for typ in ("Basin", "Hills", "Mountains", "Other", "Valley") if typ in set(plot_df["event_region_type"])]
    handles = [
        Patch(facecolor=TYPE_COLORS[typ], edgecolor=TYPE_EDGES[typ], label=typ)
        for typ in legend_types
    ]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0, 1.02), frameon=False, ncol=len(handles), borderaxespad=0)

    event_count = plot_df["event_id"].nunique()
    station_count = plot_df["station"].nunique()
    row_count = len(plot_df)
    star_count = int(sig_table["significant_holm"].sum()) if not sig_table.empty else 0
    subtitle = (
        f"Stations inside {BASELINE_REGION}; model {DEFAULT_MODEL}; components R/T/Z aggregated; "
        f"{passband_scope}; n={row_count:,} rows, {event_count:,} events, {station_count:,} stations. "
        f"* marks Holm-adjusted Mann-Whitney U p < {ALPHA:g} versus {BASELINE_REGION} events."
    )
    add_chart_header(fig, ax, f"{metric} by event region for LA Basin stations", subtitle)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    if star_count:
        print(f"wrote {output_path} ({star_count} significant regions)")
    else:
        print(f"wrote {output_path}")


def passband_label(scope: str | None) -> str:
    return "all passbands" if scope is None else scope


def main() -> int:
    args = parse_args()
    use_chart_theme()
    output_dir = args.output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    features = load_regions(args.geojson)
    feature_lookup = {feature.long_name: feature for feature in features}
    if BASELINE_REGION not in feature_lookup:
        raise ValueError(f"Baseline region {BASELINE_REGION!r} not present in {args.geojson}")
    la_geom = feature_lookup[BASELINE_REGION].geometry

    columns = [
        "event_id",
        "station",
        "component",
        "model",
        "metric",
        "band",
        "value",
        "log2_residual",
        "event_lat",
        "event_lon",
        "sta_lat",
        "sta_lon",
    ]
    metrics = pd.read_parquet(args.metrics, columns=columns)
    source_rows = len(metrics)
    metrics = metrics.loc[metrics["model"].astype(str).eq(args.model)].copy()
    model_rows = len(metrics)

    station_points = metrics[["station", "sta_lon", "sta_lat"]].drop_duplicates("station").copy()
    station_points["station_in_la_basin"] = [
        point_in_geom(row.sta_lon, row.sta_lat, la_geom) for row in station_points.itertuples(index=False)
    ]
    station_inside = station_points.loc[station_points["station_in_la_basin"], ["station"]].copy()

    event_regions = annotate_points(
        metrics[["event_id", "event_lon", "event_lat"]].drop_duplicates("event_id"),
        id_col="event_id",
        lon_col="event_lon",
        lat_col="event_lat",
        features=features,
    ).rename(
        columns={
            "region": "event_region",
            "region_short_name": "event_region_short_name",
            "region_type": "event_region_type",
            "region_feature_index": "event_region_feature_index",
        }
    )
    event_region_rows = len(event_regions)
    multi_event_regions = int(event_regions["matching_region_count"].gt(1).sum())
    unmapped_events = int(event_regions["event_region"].isna().sum())

    work = metrics.merge(station_inside, on="station", how="inner").merge(event_regions, on="event_id", how="left")
    la_station_rows = len(work)
    work = work.loc[work["event_region"].notna()].copy()
    mapped_event_rows = len(work)

    all_sig: list[pd.DataFrame] = []
    manifest_rows: list[dict[str, object]] = []
    figures: list[Path] = []
    for metric in sorted(work["metric"].dropna().astype(str).unique()):
        value_col = value_column_for_metric(metric)
        if value_col not in work.columns:
            continue
        for scope in PASSBAND_SCOPES:
            scope_label = passband_label(scope)
            frame = work.loc[work["metric"].astype(str).eq(metric)].copy()
            if scope is not None:
                frame = frame.loc[frame["band"].astype(str).eq(scope)].copy()
            frame["plot_value"] = pd.to_numeric(frame[value_col], errors="coerce")
            rows_before_value = len(frame)
            frame = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=["plot_value", "event_region"]).copy()
            region_order = ordered_regions(frame, features)
            baseline_rows = int(frame["event_region"].eq(BASELINE_REGION).sum()) if not frame.empty else 0
            output_path = output_dir / f"{slug(metric)}__{slug(scope_label)}__la_basin_stations_by_event_region.png"
            status = "skipped"
            message = ""
            sig_table = pd.DataFrame()
            if frame.empty:
                message = "no rows after LA Basin station/event-region/value filtering"
            elif len(region_order) < 2:
                message = "fewer than two event regions after filtering"
            elif baseline_rows == 0:
                message = f"baseline event region {BASELINE_REGION!r} has no rows"
            elif output_path.exists() and not args.overwrite:
                status = "exists"
                message = "figure already exists"
                figures.append(output_path)
            else:
                sig_table = significance_for_frame(
                    frame,
                    metric=metric,
                    passband_scope=scope_label,
                    value_col=value_col,
                    alpha=float(args.alpha),
                    region_order=region_order,
                )
                draw_boxplot(
                    frame,
                    metric=metric,
                    passband_scope=scope_label,
                    value_col=value_col,
                    region_order=region_order,
                    sig_table=sig_table,
                    output_path=output_path,
                )
                status = "wrote"
                message = "ok"
                figures.append(output_path)
            if sig_table.empty and not frame.empty and baseline_rows > 0:
                sig_table = significance_for_frame(
                    frame,
                    metric=metric,
                    passband_scope=scope_label,
                    value_col=value_col,
                    alpha=float(args.alpha),
                    region_order=region_order,
                )
            if not sig_table.empty:
                sig_table["figure_path"] = str(output_path)
                all_sig.append(sig_table)
            manifest_rows.append(
                {
                    "metric": metric,
                    "passband_scope": scope_label,
                    "value_col": value_col,
                    "figure_path": str(output_path) if status in {"wrote", "exists"} else "",
                    "status": status,
                    "message": message,
                    "rows_after_la_station_event_region_filter": int(len(frame)),
                    "rows_before_value_filter": int(rows_before_value),
                    "unique_events": int(frame["event_id"].nunique()) if not frame.empty else 0,
                    "unique_stations": int(frame["station"].nunique()) if not frame.empty else 0,
                    "event_region_count": int(frame["event_region"].nunique()) if not frame.empty else 0,
                    "baseline_rows": baseline_rows,
                    "significant_regions_holm": int(sig_table["significant_holm"].sum()) if not sig_table.empty else 0,
                }
            )

    sig_out = output_dir / "la_basin_event_region_boxplot_significance.csv"
    if all_sig:
        pd.concat(all_sig, ignore_index=True).to_csv(sig_out, index=False)
    else:
        pd.DataFrame().to_csv(sig_out, index=False)

    manifest = {
        "metrics_path": str(args.metrics),
        "geojson_path": str(args.geojson),
        "output_dir": str(output_dir),
        "model": args.model,
        "baseline_region": BASELINE_REGION,
        "station_filter": f"station point inside/touching {BASELINE_REGION}",
        "event_region_assignment": (
            "GeoJSON point-in-polygon using feature order; when an event matches multiple regions, "
            "the first matching feature in regions_updated.geojson is used."
        ),
        "statistics": {
            "test": "Mann-Whitney U, two-sided",
            "correction": "Holm within each metric/passband figure family",
            "alpha": float(args.alpha),
        },
        "value_columns": {
            "original_cc": "value",
            "delay_corrected_cc": "value",
            "traveltime_delay": "value",
            "all_other_metrics": "log2_residual",
        },
        "source_rows": int(source_rows),
        "model_rows": int(model_rows),
        "la_basin_station_rows_before_event_region_filter": int(la_station_rows),
        "la_basin_station_rows_with_mapped_event_region": int(mapped_event_rows),
        "station_count_total": int(station_points["station"].nunique()),
        "station_count_inside_la_basin": int(station_inside["station"].nunique()),
        "event_count_total": int(event_region_rows),
        "event_count_unmapped": int(unmapped_events),
        "event_count_multi_region": int(multi_event_regions),
        "figures_written_or_existing": len(figures),
        "significance_csv": str(sig_out),
        "figure_manifest_csv": str(output_dir / "la_basin_event_region_boxplot_manifest.csv"),
        "figures": [str(path) for path in figures],
    }
    manifest_csv = output_dir / "la_basin_event_region_boxplot_manifest.csv"
    pd.DataFrame(manifest_rows).to_csv(manifest_csv, index=False)
    manifest_json = output_dir / "la_basin_event_region_boxplot_manifest.json"
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {sig_out}")
    print(f"wrote {manifest_csv}")
    print(f"wrote {manifest_json}")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
