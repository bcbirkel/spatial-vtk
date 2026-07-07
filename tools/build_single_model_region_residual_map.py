"""Build a single-model residual map with region-grouped boxplots.

This script is intended for large-run validation figures where residuals from
one model should be summarized by mapped GeoJSON regions. It draws one map
panel with station markers and polygon medians, plus a boxplot panel ordered
by region type.
"""

from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.cm import ScalarMappable
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Patch

from spatial_vtk.spatial.map.basemaps import add_contextily_basemap


DEFAULT_METRICS_LONG = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/tables/metrics_long.parquet")
DEFAULT_REGIONS_GEOJSON = Path("/project2/jvidale_1700/spatial-vtk/runs/inputs/geospatial/regions_no_offshore.geojson")
DEFAULT_MODEL_ID = "cvmsi_20260506_material_0p6x1p2_asdf"
DEFAULT_MODEL_LABEL = "CVM-SI"
DEFAULT_EXCLUDED_REGIONS = ("Imperial Valley Basin", "Northern Transverse Range")
DEFAULT_EXCLUDED_EVENTS = ("ci15481673",)
REGION_TYPE_ORDER = ("Basin", "Mountains", "Hills", "Valley", "Other")
REGION_TYPE_COLORS = {
    "Basin": "#b07a00",
    "Mountains": "#2e7d32",
    "Hills": "#00665a",
    "Valley": "#6a3d9a",
    "Other": "#555555",
}
REGION_TYPE_LEGEND = {
    "Basin": "Basins",
    "Mountains": "Mountains",
    "Hills": "Hills",
    "Valley": "Valleys",
    "Other": "Other",
}
METRIC_LABELS = {
    "PGA": "PGA",
    "arias_duration": "Arias Duration",
    "FAS": "FAS",
    "CAV": "CAV",
    "energy_intensity": "Energy Intensity",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-long", default=str(DEFAULT_METRICS_LONG), help="Input metrics_long parquet table.")
    parser.add_argument("--regions-geojson", default=str(DEFAULT_REGIONS_GEOJSON), help="Mapped regions GeoJSON.")
    parser.add_argument("--metric", default="PGA", help="Metric token in metrics_long, for example PGA.")
    parser.add_argument("--passband", default="3-5 sec", help="Passband token in metrics_long, for example '3-5 sec'.")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID, help="Model identifier in metrics_long.")
    parser.add_argument("--model-label", default=DEFAULT_MODEL_LABEL, help="Human-readable model label for the title.")
    parser.add_argument("--output", required=True, help="Output PNG path.")
    parser.add_argument("--summary-output", default=None, help="Optional region summary CSV path.")
    parser.add_argument(
        "--exclude-region",
        action="append",
        default=list(DEFAULT_EXCLUDED_REGIONS),
        help="Region name to exclude. May be repeated.",
    )
    parser.add_argument(
        "--exclude-event",
        action="append",
        default=list(DEFAULT_EXCLUDED_EVENTS),
        help="Event id to exclude. May be repeated.",
    )
    parser.add_argument("--vlim", type=float, default=1.5, help="Symmetric residual color scale limit.")
    parser.add_argument("--basemap-source", default="Esri.WorldImagery", help="Contextily basemap source.")
    parser.add_argument("--dpi", type=int, default=180, help="Output image DPI.")
    return parser


def slug(value: str) -> str:
    text = str(value).strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")
    return text or "no_passband"


def metric_label(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric.replace("_", " ").title())


def residual_colorbar_label(label: str) -> str:
    return f"log2(observed {label}/synthetic {label})"


def boxplot_values(plot_rows: pd.DataFrame, region_order: list[str]) -> list[np.ndarray]:
    values = []
    for region in region_order:
        series = plot_rows.loc[plot_rows["region_name"].eq(region), "log2_residual"].dropna()
        values.append(series.to_numpy())
    return values


def region_axis_labels(plot_rows: pd.DataFrame, region_order: list[str]) -> list[str]:
    station_counts = plot_rows.groupby("region_name")["station"].nunique().to_dict()
    labels = []
    for region in region_order:
        label = f"{region} ({int(station_counts.get(region, 0))})"
        labels.append("\n".join(textwrap.wrap(label, width=20, break_long_words=False)))
    return labels


def region_type_lookup(plot_rows: pd.DataFrame) -> dict[str, str]:
    values = (
        plot_rows[["region_name", "region_type"]]
        .drop_duplicates("region_name")
        .set_index("region_name")["region_type"]
        .to_dict()
    )
    return {str(region): str(region_type) for region, region_type in values.items()}


def region_sort_order(region_summary: pd.DataFrame) -> list[str]:
    rank = {name: idx for idx, name in enumerate(REGION_TYPE_ORDER)}
    ordered = (
        region_summary.assign(region_type_rank=lambda frame: frame["region_type"].map(rank).fillna(len(rank)))
        .sort_values(["region_type_rank", "region_name"])["region_name"]
        .tolist()
    )
    return list(reversed(ordered))


def tukey_whisker_limit(values_by_box: list[np.ndarray]) -> float:
    limit = 1.5
    for values in values_by_box:
        values = np.asarray(values, dtype=float)
        values = values[np.isfinite(values)]
        if values.size == 0:
            continue
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr
        whisker_low = values[values >= lower_fence].min(initial=q1)
        whisker_high = values[values <= upper_fence].max(initial=q3)
        limit = max(limit, abs(float(whisker_low)), abs(float(whisker_high)))
    return float(np.ceil(limit * 2.0) / 2.0)


def load_plot_rows(args: argparse.Namespace) -> tuple[pd.DataFrame, gpd.GeoDataFrame]:
    cols = [
        "event_id",
        "station",
        "component",
        "model",
        "passband",
        "metric",
        "log2_residual",
        "sta_lon",
        "sta_lat",
    ]
    metrics = pd.read_parquet(Path(args.metrics_long), columns=cols)
    rows = metrics.loc[
        metrics["model"].astype(str).eq(str(args.model_id))
        & metrics["metric"].astype(str).eq(str(args.metric))
        & metrics["passband"].astype(str).eq(str(args.passband))
    ].copy()
    rows = rows.dropna(subset=["event_id", "station", "sta_lon", "sta_lat", "log2_residual"])
    excluded_events = {str(event_id) for event_id in args.exclude_event}
    rows = rows.loc[~rows["event_id"].astype(str).isin(excluded_events)].copy()
    if rows.empty:
        raise SystemExit(
            f"No rows for model={args.model_id!r}, metric={args.metric!r}, passband={args.passband!r}."
        )

    regions = gpd.read_file(Path(args.regions_geojson)).to_crs("EPSG:4326")
    regions["region_name"] = regions["long_name"].fillna(regions["short_name"]).astype(str)
    regions["region_type"] = regions["region_type"].fillna("Unknown").astype(str)
    excluded_regions = {str(region) for region in args.exclude_region}
    regions = regions.loc[~regions["region_name"].isin(excluded_regions)].copy()

    stations = rows[["station", "sta_lon", "sta_lat"]].drop_duplicates("station")
    points = gpd.GeoDataFrame(
        stations,
        geometry=gpd.points_from_xy(stations["sta_lon"], stations["sta_lat"]),
        crs="EPSG:4326",
    )
    joined = gpd.sjoin(
        points,
        regions[["region_name", "region_type", "geometry"]],
        how="inner",
        predicate="within",
    )
    station_region = joined[["station", "region_name", "region_type"]].drop_duplicates("station")
    plot_rows = rows.merge(station_region, on="station", how="inner")
    if plot_rows.empty:
        raise SystemExit("No stations fell within the selected polygons.")
    return plot_rows, regions


def summarize_rows(plot_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    station_summary = (
        plot_rows.groupby(["station", "region_name", "region_type"], as_index=False)
        .agg(
            sta_lon=("sta_lon", "median"),
            sta_lat=("sta_lat", "median"),
            station_median=("log2_residual", "median"),
            n=("log2_residual", "size"),
        )
    )
    region_summary = (
        plot_rows.groupby(["region_name", "region_type"], as_index=False)
        .agg(
            rows=("log2_residual", "size"),
            stations=("station", "nunique"),
            events=("event_id", "nunique"),
            median=("log2_residual", "median"),
            q1=("log2_residual", lambda values: np.percentile(values, 25)),
            q3=("log2_residual", lambda values: np.percentile(values, 75)),
        )
    )
    return station_summary, region_summary


def render_figure(
    args: argparse.Namespace,
    plot_rows: pd.DataFrame,
    regions: gpd.GeoDataFrame,
    station_summary: pd.DataFrame,
    region_summary: pd.DataFrame,
) -> bool:
    label = metric_label(str(args.metric))
    minx, miny, maxx, maxy = regions.total_bounds
    padx = 0.07 * (maxx - minx)
    pady = 0.10 * (maxy - miny)
    extent = (minx - padx, maxx + padx, miny - pady, maxy + pady)

    vlim = float(args.vlim)
    norm = TwoSlopeNorm(vmin=-vlim, vcenter=0.0, vmax=vlim)
    cmap = plt.get_cmap("RdBu_r")

    fig = plt.figure(figsize=(19.0, 9.8), dpi=int(args.dpi))
    gs = fig.add_gridspec(
        1,
        2,
        width_ratios=[1.0, 0.58],
        wspace=0.34,
        left=0.055,
        right=0.94,
        top=0.90,
        bottom=0.16,
    )
    map_ax = fig.add_subplot(gs[0, 0])
    box_ax = fig.add_subplot(gs[0, 1])

    model_regions = regions.merge(
        region_summary[["region_name", "region_type", "median", "rows", "stations"]],
        on=["region_name", "region_type"],
        how="left",
    )
    no_data = model_regions["median"].isna()
    if no_data.any():
        model_regions.loc[no_data].plot(
            ax=map_ax,
            facecolor="none",
            edgecolor="0.30",
            linewidth=0.55,
            zorder=3,
        )
    for _, row in model_regions.loc[~no_data].iterrows():
        gpd.GeoSeries([row.geometry], crs=model_regions.crs).plot(
            ax=map_ax,
            color=cmap(norm(float(row["median"]))),
            alpha=0.52,
            edgecolor="black",
            linewidth=0.70,
            zorder=4,
        )

    map_ax.set_xlim(extent[0], extent[1])
    map_ax.set_ylim(extent[2], extent[3])
    basemap_success, _source = add_contextily_basemap(
        map_ax,
        crs="EPSG:4326",
        primary_source=str(args.basemap_source),
        attribution=False,
        cache_download=False,
        on_error="ignore",
    )

    sizes = 10 + np.sqrt(station_summary["n"].to_numpy()) * 5
    map_ax.scatter(
        station_summary["sta_lon"],
        station_summary["sta_lat"],
        c=station_summary["station_median"],
        s=sizes,
        cmap=cmap,
        norm=norm,
        edgecolor="black",
        linewidth=0.25,
        alpha=0.86,
        zorder=6,
    )
    map_ax.set_title(str(args.model_label), fontsize=13, weight="bold", pad=6)
    map_ax.set_xlabel("Longitude")
    map_ax.set_ylabel("Latitude")
    map_ax.grid(alpha=0.16, color="white", linewidth=0.6)
    map_ax.set_aspect("equal", adjustable="box")

    cax = map_ax.inset_axes([0.14, -0.18, 0.72, 0.045])
    fig.colorbar(
        ScalarMappable(norm=norm, cmap=cmap),
        cax=cax,
        ticks=[-vlim, -1.0, -0.5, 0.0, 0.5, 1.0, vlim],
        orientation="horizontal",
    )
    cax.tick_params(labelsize=9)
    cax.set_xlabel(residual_colorbar_label(label), fontsize=10, labelpad=3)

    region_order = region_sort_order(region_summary)
    region_types = region_type_lookup(plot_rows)
    y_base = np.arange(len(region_order))
    values = boxplot_values(plot_rows, region_order)
    box = box_ax.boxplot(
        values,
        positions=y_base,
        vert=False,
        widths=0.42,
        patch_artist=True,
        showfliers=False,
        medianprops={"color": "black", "linewidth": 1.0},
        boxprops={"facecolor": "white", "edgecolor": "0.25", "alpha": 0.92},
        whiskerprops={"color": "0.25", "linewidth": 0.8},
        capprops={"color": "0.25", "linewidth": 0.8},
    )
    for patch, region in zip(box["boxes"], region_order):
        region_type = region_types.get(region, "Other")
        patch.set_facecolor(REGION_TYPE_COLORS.get(region_type, REGION_TYPE_COLORS["Other"]))
        patch.set_alpha(0.90)

    box_ax.axvline(0, color="0.30", linestyle="--", linewidth=0.8)
    box_xlim = tukey_whisker_limit(values)
    box_ax.set_xlim(-box_xlim, box_xlim)
    box_ax.set_yticks(y_base)
    box_ax.set_yticklabels(region_axis_labels(plot_rows, region_order), fontsize=10.2)
    box_ax.tick_params(axis="x", labelsize=9)
    box_ax.set_xlabel("log2 residual", fontsize=10)
    box_ax.grid(axis="x", alpha=0.22)
    box_ax.set_title("Record distributions by region", fontsize=10)
    present_region_types = set(region_summary["region_type"])
    legend_handles = [
        Patch(
            facecolor=REGION_TYPE_COLORS[region_type],
            edgecolor="0.25",
            label=REGION_TYPE_LEGEND[region_type],
        )
        for region_type in REGION_TYPE_ORDER
        if region_type in present_region_types
    ]
    box_ax.legend(
        handles=legend_handles,
        loc="upper left",
        bbox_to_anchor=(1.01, 1.00),
        fontsize=8.5,
        frameon=False,
        borderaxespad=0.0,
    )

    fig.suptitle(
        f"{label} Residuals | {args.passband} | {args.model_label}",
        y=0.955,
        fontsize=16,
        weight="bold",
    )
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return bool(basemap_success)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plot_rows, regions = load_plot_rows(args)
    station_summary, region_summary = summarize_rows(plot_rows)
    if args.summary_output:
        summary_output = Path(args.summary_output).expanduser()
    else:
        output = Path(args.output).expanduser()
        summary_output = output.with_name(output.stem + "_summary.csv")
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    region_summary.to_csv(summary_output, index=False)

    basemap_success = render_figure(args, plot_rows, regions, station_summary, region_summary)
    print(Path(args.output).expanduser())
    print(summary_output)
    print(
        "metric",
        args.metric,
        "passband",
        args.passband,
        "model",
        args.model_label,
        "rows",
        plot_rows.shape[0],
        "events",
        plot_rows.event_id.nunique(),
        "stations",
        plot_rows.station.nunique(),
        "regions_with_data",
        region_summary.shape[0],
        "polygons",
        len(regions),
        "basemap",
        "cached basemap" if basemap_success else "static fallback",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
