"""Build station-region boxplots split by mapped region type.

This is a focused large-run helper for user-requested diagnostics. It reads the
large ``metrics_long`` table, annotates stations from the configured GeoJSON,
and writes one boxplot per metric, passband scope, and mapped region type.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shapely.geometry import Point, shape


DEFAULT_METRICS_LONG = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/tables/metrics_long.parquet")
DEFAULT_GEOJSON = Path("/project2/jvidale_1700/spatial-vtk/runs/inputs/geospatial/regions_updated.geojson")
DEFAULT_OUTPUT_DIR = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/figures/user_requested_region_type_boxplots")
DEFAULT_MODEL = "cvmsi_20260506_material_0p6x1p2_asdf"
PASSBANDS = ("1-2 sec", "2-3 sec", "3-5 sec")
PAIR_VALUE_METRICS = {"original_cc", "delay_corrected_cc"}
DELAY_FRACTION_COL = "delay_fraction_dominant_period"
METRIC_ORDER = (
    "arias_duration",
    "energy_duration",
    "PGA",
    "PGV",
    "PGD",
    "PSA",
    "FAS",
    "arias_intensity",
    "energy_intensity",
    "CAV",
    "original_cc",
    "delay_corrected_cc",
    "traveltime_delay",
)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    metrics_path = Path(args.metrics_long).expanduser()
    geojson_path = Path(args.geojson).expanduser()
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    columns = [
        "event_id",
        "station",
        "component",
        "model",
        "passband",
        "metric_group",
        "metric",
        "period_s",
        "value",
        "log2_residual",
        "sta_lon",
        "sta_lat",
    ]
    df = pd.read_parquet(metrics_path, columns=columns)
    if args.model:
        df = df.loc[df["model"].astype(str).eq(str(args.model))].copy()
    df = _with_delay_fraction_column(df)
    stations = _annotate_stations(df, geojson_path)
    df = df.merge(stations, on="station", how="left")

    metrics = _ordered_values(df["metric"].dropna().unique(), METRIC_ORDER)
    region_types = _ordered_values(
        [value for value in df["mapped_region_type"].dropna().unique() if _defined_region_type(value)],
        ("Basin", "Hills", "Mountains", "Other", "Valley"),
    )
    scopes: list[tuple[str, str | None]] = [("all_passbands", None)]
    scopes.extend((_scope_slug(passband), passband) for passband in PASSBANDS)

    manifest: dict[str, object] = {
        "input_table": str(metrics_path),
        "geojson": str(geojson_path),
        "output_dir": str(output_dir),
        "model": args.model,
        "metrics": list(metrics),
        "region_types": list(region_types),
        "scopes": [],
    }
    for metric in metrics:
        metric_df = df.loc[df["metric"].astype(str).eq(str(metric))].copy()
        value_col = _metric_value_column(str(metric))
        for scope_name, passband in scopes:
            scope_df = metric_df if passband is None else metric_df.loc[metric_df["passband"].astype(str).eq(str(passband))].copy()
            for region_type in region_types:
                plot_df = scope_df.loc[scope_df["mapped_region_type"].astype(str).eq(str(region_type))].copy()
                plot_df[value_col] = pd.to_numeric(plot_df[value_col], errors="coerce") if value_col in plot_df.columns else np.nan
                plot_df = plot_df.loc[np.isfinite(plot_df[value_col])]
                if plot_df.empty:
                    continue
                fig_path = output_dir / _figure_name(metric, scope_name, region_type, value_col)
                _plot_boxplot(
                    plot_df,
                    fig_path,
                    metric=str(metric),
                    passband=passband,
                    region_type=str(region_type),
                    value_col=value_col,
                )
                manifest["scopes"].append(
                    {
                        "metric": str(metric),
                        "passband": passband,
                        "scope": scope_name,
                        "mapped_region_type": str(region_type),
                        "value_col": value_col,
                        "rows": int(len(plot_df)),
                        "station_regions": int(plot_df["station_region"].nunique(dropna=True)),
                        "stations": int(plot_df["station"].nunique(dropna=True)),
                        "figure": str(fig_path),
                    }
                )

    manifest_path = output_dir / "region_type_boxplot_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-long", default=str(DEFAULT_METRICS_LONG))
    parser.add_argument("--geojson", default=str(DEFAULT_GEOJSON))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser.parse_args(argv)


def _annotate_stations(df: pd.DataFrame, geojson_path: Path) -> pd.DataFrame:
    features = _load_features(geojson_path)
    stations = (
        df.loc[:, ["station", "sta_lon", "sta_lat"]]
        .dropna(subset=["station", "sta_lon", "sta_lat"])
        .drop_duplicates("station")
        .copy()
    )
    regions: list[str] = []
    region_types: list[str] = []
    for row in stations.itertuples(index=False):
        point = Point(float(row.sta_lon), float(row.sta_lat))
        matches = [feature for feature in features if feature["geometry"].contains(point) or feature["geometry"].touches(point)]
        if matches:
            feature = matches[0]
            regions.append(str(feature["long_name"]))
            region_types.append(str(feature["region_type"]))
        else:
            regions.append("outside")
            region_types.append("outside")
    stations["station_region"] = regions
    stations["mapped_region_type"] = region_types
    return stations.loc[:, ["station", "station_region", "mapped_region_type"]]


def _load_features(path: Path) -> list[dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    features: list[dict[str, object]] = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        features.append(
            {
                "geometry": shape(feature["geometry"]),
                "long_name": props.get("long_name") or props.get("name") or props.get("short_name"),
                "region_type": props.get("region_type") or props.get("mapped_region_type") or "unmapped",
            }
        )
    return features


def _with_delay_fraction_column(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    delay = pd.to_numeric(out["value"], errors="coerce")
    denominator = out["passband"].map(_period_from_passband_label)
    finite = np.isfinite(delay) & np.isfinite(denominator) & (denominator > 0.0)
    out[DELAY_FRACTION_COL] = np.where(finite, delay / denominator, np.nan)
    return out


def _period_from_passband_label(value: object) -> float:
    numbers = [float(match) for match in re.findall(r"\d+(?:\.\d+)?", str(value or "").lower())]
    if len(numbers) >= 2 and numbers[0] > 0.0 and numbers[1] > 0.0:
        return float(math.sqrt(numbers[0] * numbers[1]))
    if len(numbers) == 1 and numbers[0] > 0.0:
        return float(numbers[0])
    return float("nan")


def _metric_value_column(metric: str) -> str:
    key = metric.strip()
    if key in PAIR_VALUE_METRICS:
        return "value"
    if key == "traveltime_delay":
        return DELAY_FRACTION_COL
    return "log2_residual"


def _plot_boxplot(df: pd.DataFrame, output_path: Path, *, metric: str, passband: str | None, region_type: str, value_col: str) -> None:
    regions = sorted(df["station_region"].dropna().astype(str).unique(), key=_region_sort_key)
    data = [pd.to_numeric(df.loc[df["station_region"].astype(str).eq(region), value_col], errors="coerce").dropna().to_numpy() for region in regions]
    width = max(8.0, min(18.0, 1.2 * max(len(regions), 1) + 3.0))
    fig, ax = plt.subplots(figsize=(width, 6.0), dpi=180)
    parts = ax.boxplot(data, tick_labels=regions, showfliers=True, patch_artist=True)
    color = _region_type_color(region_type)
    for patch in parts["boxes"]:
        patch.set_facecolor(color)
        patch.set_alpha(0.68)
        patch.set_edgecolor("#333333")
    for element in ("whiskers", "caps", "medians"):
        for artist in parts[element]:
            artist.set_color("#333333")
            artist.set_linewidth(1.0)
    ax.axhline(0.0, color="#555555", linewidth=0.8, linestyle="--", alpha=0.65)
    scope = "all passbands" if passband is None else passband
    ax.set_title(f"{metric} by Station Region ({region_type}, {scope})")
    ax.set_xlabel("Station region")
    ax.set_ylabel(_value_label(value_col))
    ax.grid(axis="y", alpha=0.25)
    ax.tick_params(axis="x", rotation=35)
    for label in ax.get_xticklabels():
        label.set_ha("right")
    text = f"rows={len(df):,}; stations={df['station'].nunique():,}"
    ax.text(0.99, 0.98, text, ha="right", va="top", transform=ax.transAxes, fontsize=8.5)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def _value_label(value_col: str) -> str:
    if value_col == "value":
        return "Correlation value"
    if value_col == DELAY_FRACTION_COL:
        return "Delay / dominant period"
    return "log2(obs/syn) residual"


def _region_type_color(region_type: object) -> str:
    colors = {
        "Basin": "#4C78A8",
        "Hills": "#F58518",
        "Mountains": "#54A24B",
        "Other": "#B279A2",
        "Valley": "#E45756",
    }
    return colors.get(str(region_type), "#8C8C8C")


def _figure_name(metric: object, scope_name: str, region_type: object, value_col: str) -> str:
    return f"region_type_boxplot__{_slug(metric)}__{scope_name}__{_slug(region_type)}__{_slug(value_col)}.png"


def _scope_slug(passband: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", str(passband).strip()).strip("_").lower()
    return f"passband_{slug or 'blank'}"


def _slug(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", str(value).strip()).strip("_").lower() or "unknown"


def _ordered_values(values: Iterable[object], preferred: Iterable[object]) -> list[str]:
    texts = [str(value) for value in values]
    order = {str(value): index for index, value in enumerate(preferred)}
    return sorted(texts, key=lambda value: (order.get(value, len(order)), value.casefold()))


def _region_sort_key(value: object) -> tuple[int, str]:
    text = str(value)
    return (0 if text != "outside" else 1, text.casefold())


def _defined_region_type(value: object) -> bool:
    text = str(value).strip().casefold()
    return text not in {"", "outside", "unmapped", "unknown", "nan", "none", "null"}


if __name__ == "__main__":
    sys.exit(main())
