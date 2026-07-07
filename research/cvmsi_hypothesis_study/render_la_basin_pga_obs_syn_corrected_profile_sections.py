#!/usr/bin/env python3
"""Render LA Basin corrected observed/synthetic PGA profile cross sections.

This is an isolated, private analysis workflow. It follows the LA Basin profile
definitions and model-section machinery from the CVM-SI hypothesis study, but
plots geometric-spreading-corrected observed and synthetic PGA anomalies rather
than observed/synthetic residuals.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from pyproj import Transformer

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cvmsi_hypothesis_study import (  # noqa: E402
    COLORS,
    CVM_UTM,
    DEFAULT_METRICS,
    DEFAULT_MODEL,
    DEFAULT_MODEL_H5,
    DEFAULT_OUTPUT,
    DEFAULT_REGIONS,
    ModelSampler,
    load_regions,
    set_plot_theme,
)
from render_la_basin_axis_profile_sections import (  # noqa: E402
    BANDS,
    build_profile_families,
    render_candidate_map,
)
from render_la_basin_metric_profile_atlas import (  # noqa: E402
    ATLAS_LOWESS_FRAC,
    PROFILE_ORDER,
    VS_GRADIENT_WINDOW_HALF_KM,
    add_png_page_to_pdf,
    add_vertical_property_gradient_cells,
    event_marker_size,
    page_value_scale,
    sample_section_grids,
    section_line_utm,
    section_property_gradient_norm,
    station_projection,
    AtlasVariant,
    MetricPage,
    PanelSpec,
)
from render_la_basin_metric_profile_split_pages import (  # noqa: E402
    PROPERTY_LABELS,
    SECTION_MAX_DEPTH_KM,
    SPLIT_STATION_CORRIDOR_KM,
    add_model_depth_columns,
    plot_profile_map,
    plot_section_grid,
    property_variants,
    weighted_lowess_by_column,
)


OUTPUT_SLUG = "la_basin_pga_obs_syn_corrected_profile_sections"
METRIC = "PGA"
VALUE_COLUMN = "pga_corrected_event_centered_log2"
SOURCE_LABELS = {"observed": "Observed", "synthetic": "Synthetic"}
SOURCE_VALUE_COLUMNS = {"observed": "value_obs", "synthetic": "value_syn"}
SOURCE_COLORS = {"observed": "#111111", "synthetic": "#c23532"}
REQUIRED_PAIR_COLUMNS = {
    "event_id",
    "station",
    "metric",
    "band",
    "value_obs",
    "value_syn",
    "event_lat",
    "event_lon",
    "sta_lat",
    "sta_lon",
    "distance_km",
}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument(
        "--pairs",
        type=Path,
        default=None,
        help="Optional pre-collapsed pairs table. Must include value_obs, value_syn, distance_km, and coordinates.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--model-label", default="CVM-SI")
    parser.add_argument(
        "--comparison-model",
        default=None,
        help=(
            "Optional second model name used only to require common event-station-component-band rows. "
            "This makes observed curves directly comparable across model-specific renders."
        ),
    )
    parser.add_argument("--model-h5", type=Path, default=DEFAULT_MODEL_H5)
    parser.add_argument("--model-node-stride", type=int, default=2)
    parser.add_argument("--model-property", default="vs", choices=("vs", "vp"))
    parser.add_argument("--component", default=None, help="Optional component filter, for example T or Z.")
    parser.add_argument("--geometric-spreading-exponent", type=float, default=1.0)
    parser.add_argument(
        "--event-mean-reference",
        choices=("independent", "pooled"),
        default="independent",
        help="Independent removes observed and synthetic event means separately; pooled removes one source-pooled event mean.",
    )
    parser.add_argument("--min-stations-per-event", type=int, default=3)
    parser.add_argument("--bands", nargs="*", default=[band for band, _ in BANDS])
    parser.add_argument(
        "--output-tag",
        default=None,
        help="Optional extra suffix for output subdirectories. Defaults to the model label slug.",
    )
    return parser.parse_args(argv)


def parquet_columns(path: Path) -> set[str]:
    try:
        import pyarrow.parquet as pq

        return set(pq.ParquetFile(path).schema.names)
    except Exception:
        return set(pd.read_parquet(path).columns)


def validate_pair_schema(path: Path, columns: set[str]) -> None:
    missing = sorted(REQUIRED_PAIR_COLUMNS - columns)
    if missing:
        raise ValueError(
            "PGA corrected-profile workflow requires these pair fields: "
            f"{sorted(REQUIRED_PAIR_COLUMNS)}. Missing from {path}: {missing}. "
            "Minimum upstream fields are event_id, station, metric, band, value_obs, value_syn, "
            "event/station lon-lat, and distance_km or an equivalent hypocentral distance column."
        )


def collapse_pga_pairs(df: pd.DataFrame) -> pd.DataFrame:
    keys = ["event_id", "station", "metric", "band"]
    optional_numeric = [
        column
        for column in (
            "period_s",
            "log2_residual",
            "event_lat",
            "event_lon",
            "sta_lat",
            "sta_lon",
            "distance_km",
            "azimuth_deg",
            "backazimuth_deg",
            "magnitude",
            "event_depth_km",
        )
        if column in df.columns
    ]
    aggregations: dict[str, tuple[str, str] | tuple[str, object]] = {
        "value_obs": ("value_obs", "median"),
        "value_syn": ("value_syn", "median"),
        **{column: (column, "median") for column in optional_numeric},
    }
    for column in ("model", "event_name"):
        if column in df.columns:
            aggregations[column] = (column, lambda values: next((str(value) for value in values.dropna()), ""))
    if "component" in df.columns:
        aggregations["components"] = ("component", lambda values: ",".join(sorted(set(str(value) for value in values.dropna()))))
        aggregations["component_count"] = ("component", "nunique")
    out = (
        df.groupby(keys, as_index=False, dropna=False)
        .agg(**aggregations)
        .replace([np.inf, -np.inf], np.nan)
    )
    return out


def filter_common_model_rows(raw: pd.DataFrame, *, model: str, comparison_model: str | None) -> pd.DataFrame:
    if comparison_model is None:
        return raw
    key_columns = ["event_id", "station", "metric", "band"]
    if "component" in raw.columns:
        key_columns.insert(2, "component")
    supported = raw.loc[raw["model"].astype(str).isin([str(model), str(comparison_model)]), key_columns + ["model"]].drop_duplicates()
    common_keys = (
        supported.groupby(key_columns, dropna=False)["model"]
        .nunique()
        .rename("model_count")
        .reset_index()
        .loc[lambda frame: frame["model_count"].ge(2), key_columns]
    )
    return raw.merge(common_keys, on=key_columns, how="inner")


def common_key_columns(frame: pd.DataFrame) -> list[str]:
    key_columns = ["event_id", "station", "metric", "band"]
    if "component" in frame.columns:
        key_columns.insert(2, "component")
    return key_columns


def canonical_observed_fields(raw: pd.DataFrame, key_columns: list[str]) -> pd.DataFrame:
    canonical_columns = [
        column
        for column in ("value_obs", "event_lat", "event_lon", "sta_lat", "sta_lon", "distance_km", "azimuth_deg", "backazimuth_deg")
        if column in raw.columns
    ]
    return raw.groupby(key_columns, as_index=False, dropna=False).agg(**{column: (column, "median") for column in canonical_columns})


def replace_with_canonical_observed(raw: pd.DataFrame, canonical: pd.DataFrame, key_columns: list[str]) -> pd.DataFrame:
    out = raw.merge(canonical, on=key_columns, how="left", suffixes=("", "_canonical"))
    for column in canonical.columns:
        if column in key_columns:
            continue
        canonical_column = f"{column}_canonical"
        if canonical_column in out.columns:
            out[column] = out[canonical_column]
            out = out.drop(columns=[canonical_column])
    return out


def load_pairs(args: argparse.Namespace) -> pd.DataFrame:
    bands = tuple(str(band) for band in args.bands)
    if args.pairs is not None:
        path = args.pairs.expanduser()
        available = parquet_columns(path)
        validate_pair_schema(path, available)
        optional = {
            "model",
            "component",
            "component_count",
            "components",
            "event_name",
            "magnitude",
            "event_depth_km",
            "azimuth_deg",
            "backazimuth_deg",
        }
        columns = sorted(REQUIRED_PAIR_COLUMNS | (optional & available))
        pairs = pd.read_parquet(path, columns=columns)
        if "model" in pairs.columns:
            if args.comparison_model is not None:
                key_columns = ["event_id", "station", "metric", "band"]
                if "component" in pairs.columns:
                    key_columns.insert(2, "component")
                supported = pairs.loc[
                    pairs["model"].astype(str).isin([str(args.model), str(args.comparison_model)]),
                    key_columns + ["model"],
                ].drop_duplicates()
                common_keys = (
                    supported.groupby(key_columns, dropna=False)["model"]
                    .nunique()
                    .rename("model_count")
                    .reset_index()
                    .loc[lambda frame: frame["model_count"].ge(2), key_columns]
                )
                pairs = pairs.merge(common_keys, on=key_columns, how="inner")
            pairs = pairs.loc[pairs["model"].astype(str).eq(str(args.model))].copy()
        if args.component is not None and "component" in pairs.columns:
            pairs = pairs.loc[pairs["component"].astype(str).str.upper().eq(str(args.component).upper())].copy()
    else:
        path = args.metrics.expanduser()
        available = parquet_columns(path)
        validate_pair_schema(path, available)
        raw_columns = [
            "event_id",
            "station",
            "component",
            "model",
            "metric",
            "band",
            "period_s",
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
        ]
        columns = [column for column in raw_columns if column in available]
        raw = pd.read_parquet(path, columns=columns)
        raw = raw.loc[
            raw["metric"].astype(str).eq(METRIC)
            & raw["band"].astype(str).isin(bands)
        ].copy()
        if args.component is not None and "component" in raw.columns:
            raw = raw.loc[raw["component"].astype(str).str.upper().eq(str(args.component).upper())].copy()
        numeric_columns = [
            column
            for column in ("value_obs", "value_syn", "distance_km", "event_lat", "event_lon", "sta_lat", "sta_lon")
            if column in raw.columns
        ]
        for column in numeric_columns:
            raw[column] = pd.to_numeric(raw[column], errors="coerce")
        raw = raw.replace([np.inf, -np.inf], np.nan)
        raw = raw.dropna(subset=["value_obs", "value_syn", "distance_km", "event_lat", "event_lon", "sta_lat", "sta_lon"])
        raw = raw.loc[(raw["value_obs"] > 0.0) & (raw["value_syn"] > 0.0) & (raw["distance_km"] > 0.0)].copy()
        raw = filter_common_model_rows(raw, model=str(args.model), comparison_model=args.comparison_model)
        if args.comparison_model is not None:
            key_columns = common_key_columns(raw)
            canonical = canonical_observed_fields(raw, key_columns)
            raw = replace_with_canonical_observed(raw, canonical, key_columns)
        raw = raw.loc[raw["model"].astype(str).eq(str(args.model))].copy()
        pairs = collapse_pga_pairs(raw)

    pairs = pairs.loc[pairs["metric"].astype(str).eq(METRIC) & pairs["band"].astype(str).isin(bands)].copy()
    for column in ["value_obs", "value_syn", "distance_km", "event_lat", "event_lon", "sta_lat", "sta_lon"]:
        pairs[column] = pd.to_numeric(pairs[column], errors="coerce")
    for column in ["event_id", "station", "metric", "band"]:
        pairs[column] = pairs[column].astype(str)
    pairs = pairs.replace([np.inf, -np.inf], np.nan)
    pairs = pairs.dropna(
        subset=["event_id", "station", "band", "value_obs", "value_syn", "distance_km", "event_lat", "event_lon", "sta_lat", "sta_lon"]
    )
    pairs = pairs.loc[(pairs["value_obs"] > 0.0) & (pairs["value_syn"] > 0.0) & (pairs["distance_km"] > 0.0)].copy()
    if pairs.empty:
        raise ValueError(
            f"No finite positive {METRIC} rows remain after filtering model={args.model!r}, "
            f"comparison_model={args.comparison_model!r}, component={args.component!r}, and bands={bands!r}."
        )
    return pairs


def corrected_source_rows(
    pairs: pd.DataFrame,
    *,
    exponent: float,
    event_mean_reference: str,
    min_stations_per_event: int,
) -> pd.DataFrame:
    base_columns = [
        "event_id",
        "station",
        "metric",
        "band",
        "event_lat",
        "event_lon",
        "sta_lat",
        "sta_lon",
        "distance_km",
    ]
    optional_columns = [
        column
        for column in ("model", "components", "component_count", "event_name", "magnitude", "event_depth_km", "azimuth_deg", "backazimuth_deg")
        if column in pairs.columns
    ]
    pieces: list[pd.DataFrame] = []
    for source, value_column in SOURCE_VALUE_COLUMNS.items():
        piece = pairs[base_columns + optional_columns + [value_column]].copy()
        piece["source"] = source
        piece["pga"] = pd.to_numeric(piece[value_column], errors="coerce")
        piece = piece.drop(columns=[value_column]).dropna(subset=["pga", "distance_km"])
        piece = piece.loc[(piece["pga"] > 0.0) & (piece["distance_km"] > 0.0)].copy()
        piece["pga_corrected"] = piece["pga"] * np.power(piece["distance_km"], float(exponent))
        piece["pga_corrected_log2"] = np.log2(piece["pga_corrected"])
        pieces.append(piece)
    out = pd.concat(pieces, ignore_index=True)
    station_counts = out.groupby(["event_id", "source", "band"], dropna=False)["station"].nunique().rename("event_station_count")
    out = out.merge(station_counts, on=["event_id", "source", "band"], how="left")
    out = out.loc[out["event_station_count"].ge(int(min_stations_per_event))].copy()
    if out.empty:
        raise ValueError(
            "No corrected PGA rows remain after the per-event station support filter. "
            f"Try lowering --min-stations-per-event from {min_stations_per_event}."
        )
    if event_mean_reference == "independent":
        ref_keys = ["source", "event_id", "metric", "band"]
    elif event_mean_reference == "pooled":
        ref_keys = ["event_id", "metric", "band"]
    else:
        raise ValueError(f"Unknown event mean reference: {event_mean_reference!r}")
    out["pga_corrected_event_mean_log2"] = out.groupby(ref_keys, dropna=False)["pga_corrected_log2"].transform("mean")
    out[VALUE_COLUMN] = out["pga_corrected_log2"] - out["pga_corrected_event_mean_log2"]
    out["pga_corrected_event_ratio"] = np.power(2.0, out[VALUE_COLUMN])
    return out.dropna(subset=[VALUE_COLUMN]).copy()


def station_values(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame(columns=["station", "sta_lon", "sta_lat", "value", "q25", "q75", "events", "records"])
    return (
        data.groupby("station", as_index=False)
        .agg(
            sta_lon=("sta_lon", "median"),
            sta_lat=("sta_lat", "median"),
            value=(VALUE_COLUMN, "median"),
            q25=(VALUE_COLUMN, lambda value: float(value.quantile(0.25))),
            q75=(VALUE_COLUMN, lambda value: float(value.quantile(0.75))),
            pga_corrected_median=("pga_corrected", "median"),
            event_ratio_median=("pga_corrected_event_ratio", "median"),
            events=("event_id", "nunique"),
            records=(VALUE_COLUMN, "size"),
        )
        .replace([np.inf, -np.inf], np.nan)
        .dropna(subset=["sta_lon", "sta_lat", "value"])
    )


def page_spec(model_label: str, bands: Sequence[str]) -> MetricPage:
    panels = tuple(
        PanelSpec(
            label=str(band),
            metric=METRIC,
            band=str(band),
            value_column=VALUE_COLUMN,
            value_label="Event-centered log2(PGA x R)",
        )
        for band in bands
    )
    return MetricPage(
        slug="pga_obs_syn_corrected",
        title=f"LA Basin {model_label}: corrected observed and synthetic PGA",
        subtitle=(
            "PGA values are corrected by multiplying by distance^exponent, transformed to log2, "
            "and demeaned within each event before station summaries."
        ),
        panels=panels,
        cmap="RdBu_r",
        y_label="Event-centered log2(PGA x R)",
        colorbar_label="Event-centered log2(PGA x R)",
        value_mode="residual",
    )


def corrected_value_scale(projected: dict[tuple[str, str, str], pd.DataFrame]) -> tuple[TwoSlopeNorm, tuple[float, float]]:
    values: list[np.ndarray] = []
    for frame in projected.values():
        if frame.empty:
            continue
        values.extend([frame["value"].to_numpy(dtype=float), frame["q25"].to_numpy(dtype=float), frame["q75"].to_numpy(dtype=float)])
    finite = np.concatenate([value[np.isfinite(value)] for value in values]) if values else np.array([])
    if finite.size:
        lo = float(np.nanquantile(finite, 0.01))
        hi = float(np.nanquantile(finite, 0.99))
        span = max(abs(lo), abs(hi), 0.75)
        span = min(max(span * 1.08, 1.2), 8.0)
    else:
        span = 2.0
    return TwoSlopeNorm(vmin=-span, vcenter=0.0, vmax=span), (-span, span)


def plot_corrected_panel(
    ax: plt.Axes,
    frames: dict[str, pd.DataFrame],
    *,
    band: str,
    y_limits: tuple[float, float],
    event_min: float,
    event_max: float,
    section_length_km: float,
) -> None:
    ax.grid(True, color=COLORS["grid"], linewidth=0.6, alpha=0.75)
    ax.axhline(0.0, color=COLORS["ink"], linewidth=0.8, alpha=0.62, zorder=1)
    ax.set_xlim(0.0, section_length_km)
    ax.set_ylim(*y_limits)
    ax.tick_params(labelsize=7.4)
    ax.text(
        0.010,
        0.90,
        str(band),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.3,
        fontweight="bold",
        color=COLORS["ink"],
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78, "pad": 1.3},
        zorder=6,
    )
    nonempty_frames = {source: frame for source, frame in frames.items() if not frame.empty}
    if not nonempty_frames:
        ax.text(0.5, 0.5, "No stations", ha="center", va="center", transform=ax.transAxes, color=COLORS["muted"], fontsize=9)
        return
    for source in ("observed", "synthetic"):
        frame = frames.get(source, pd.DataFrame())
        if frame.empty:
            continue
        color = SOURCE_COLORS[source]
        yerr = np.vstack([np.clip(frame["value"] - frame["q25"], 0.0, None), np.clip(frame["q75"] - frame["value"], 0.0, None)])
        ax.errorbar(
            frame["projected_km"],
            frame["value"],
            yerr=yerr,
            fmt="none",
            ecolor=color,
            elinewidth=0.65,
            alpha=0.30,
            capsize=1.2,
            zorder=2,
        )
        ax.scatter(
            frame["projected_km"],
            frame["value"],
            color=color,
            s=event_marker_size(frame["events"], event_min, event_max, minimum=12, maximum=48),
            edgecolor=color,
            linewidth=0.20,
            alpha=0.42,
            zorder=3,
        )
        lowess_x, lowess_y = weighted_lowess_by_column(frame, x_col="projected_km")
        if lowess_x.size:
            ax.plot(lowess_x, lowess_y, color=color, linewidth=1.55, alpha=0.88, zorder=4)
    count_text = "; ".join(
        f"{SOURCE_LABELS[source].lower()} {frame['station'].nunique():,} sta"
        for source, frame in nonempty_frames.items()
    )
    ax.text(
        0.985,
        0.90,
        count_text,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=6.8,
        color=COLORS["muted"],
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.74, "pad": 1.2},
        zorder=5,
    )


def render_profile_page(
    *,
    pdf: PdfPages,
    page: MetricPage,
    profile_id: str,
    sections: list[tuple[str, tuple[float, float], tuple[float, float]]],
    metadata: pd.DataFrame,
    regions: list,
    section_grids: dict[str, dict[str, object]],
    projected: dict[tuple[str, str, str], pd.DataFrame],
    corrected_rows: pd.DataFrame,
    y_limits: tuple[float, float],
    norm: TwoSlopeNorm,
    property_gradient_norm: TwoSlopeNorm,
    basemap_cache_dir: Path,
    out_png: Path,
    model_label: str,
    model_property: str,
    exponent: float,
    event_mean_reference: str,
) -> None:
    section_grid = section_grids[profile_id]
    row = metadata.set_index("profile_id").loc[profile_id]
    property_label = PROPERTY_LABELS[model_property]
    absolute_variant, gradient_variant = property_variants(model_property)
    band_source_frames = {
        (panel.label, source): projected[(profile_id, panel.label, source)]
        for panel in page.panels
        for source in SOURCE_LABELS
    }
    station_frame = (
        pd.concat([frame[["station", "sta_lon", "sta_lat"]] for frame in band_source_frames.values() if not frame.empty], ignore_index=True)
        .drop_duplicates("station")
        if any(not frame.empty for frame in band_source_frames.values())
        else pd.DataFrame(columns=["station", "sta_lon", "sta_lat"])
    )
    station_ids = set(station_frame["station"].astype(str))
    events = (
        corrected_rows.loc[corrected_rows["station"].astype(str).isin(station_ids), ["event_id", "station", "event_lon", "event_lat"]]
        .dropna(subset=["event_lon", "event_lat"])
        .drop_duplicates("event_id")
    )
    event_values = np.concatenate([frame["events"].to_numpy(dtype=float) for frame in band_source_frames.values() if not frame.empty])
    event_min = float(np.nanmin(event_values)) if event_values.size else 1.0
    event_max = float(np.nanmax(event_values)) if event_values.size else event_min

    fig = plt.figure(figsize=(18.0, 12.4), constrained_layout=False)
    grid = fig.add_gridspec(
        nrows=6,
        ncols=8,
        height_ratios=[0.38, 1.0, 1.0, 1.0, 1.08, 1.08],
        width_ratios=[1.0, 1.0, 0.050, 1.0, 1.0, 0.050, 0.95, 0.95],
        hspace=0.42,
        wspace=0.25,
    )
    title = (
        f"{model_label} corrected PGA profile {profile_id}: {row.family.replace('_', ' ')} "
        f"({row.bearing_deg:.1f} deg; LA Basin crossing {row.la_basin_intersection_km:.1f} km)"
    )
    fig.suptitle(title, fontsize=17.0, fontweight="bold", color=COLORS["ink"], y=0.985)
    fig.text(
        0.055,
        0.953,
        (
            f"Observed and synthetic panels show station medians of log2(PGA x distance^{exponent:g}) "
            f"after {event_mean_reference} event-mean removal. Cross sections show absolute {property_label} "
            f"and signed vertical {property_label} gradient to {SECTION_MAX_DEPTH_KM:g} km."
        ),
        ha="left",
        va="top",
        fontsize=9.3,
        color=COLORS["muted"],
    )

    for row_index, panel in enumerate(page.panels, start=1):
        ax = fig.add_subplot(grid[row_index, :5])
        plot_corrected_panel(
            ax,
            {source: band_source_frames[(panel.label, source)] for source in SOURCE_LABELS},
            band=panel.label,
            y_limits=y_limits,
            event_min=event_min,
            event_max=event_max,
            section_length_km=float(section_grid["length_km"]),
        )
        if row_index < len(page.panels):
            ax.tick_params(labelbottom=False)
        else:
            ax.set_xlabel("Distance along profile (km)", fontsize=8.6)
        ax.set_ylabel("Event-centered\nlog2(PGA x R)", fontsize=8.4)

    map_ax = fig.add_subplot(grid[1:4, 6:])
    plot_profile_map(
        map_ax,
        regions=regions,
        sections=sections,
        metadata=metadata,
        profile_id=profile_id,
        stations=station_frame,
        events=events,
        basemap_cache_dir=basemap_cache_dir,
    )

    vs_ax = fig.add_subplot(grid[4, :5])
    grad_ax = fig.add_subplot(grid[5, :5])
    vs_image = plot_section_grid(vs_ax, section_grid, variant=absolute_variant, vs_gradient_norm=None)
    grad_image = plot_section_grid(grad_ax, section_grid, variant=gradient_variant, vs_gradient_norm=property_gradient_norm)
    for ax, label in ((vs_ax, f"Absolute {property_label}"), (grad_ax, f"Vertical {property_label} gradient")):
        ax.invert_yaxis()
        ax.set_xlim(0.0, float(section_grid["length_km"]))
        ax.set_ylim(SECTION_MAX_DEPTH_KM, 0.0)
        ax.grid(color="white", linewidth=0.45, alpha=0.55)
        ax.set_ylabel("Depth (km)", fontsize=8.8)
        ax.tick_params(labelsize=7.5)
        ax.text(
            0.012,
            0.08,
            label,
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=9.0,
            fontweight="bold",
            color=COLORS["ink"],
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.76, "pad": 2.0},
        )
    grad_ax.set_xlabel("Distance along profile (km)", fontsize=8.8)

    vs_cax = fig.add_subplot(grid[4, 5])
    grad_cax = fig.add_subplot(grid[5, 5])
    vs_cbar = fig.colorbar(vs_image, cax=vs_cax)
    grad_cbar = fig.colorbar(grad_image, cax=grad_cax, extend="both")
    vs_cbar.set_label(f"{property_label} (km/s)", fontsize=8.0, labelpad=6)
    grad_cbar.set_label(f"{property_label} gradient ((km/s)/km)", fontsize=8.0, labelpad=6)
    vs_cbar.ax.tick_params(labelsize=6.8)
    grad_cbar.ax.tick_params(labelsize=6.8)

    size_values = np.unique(np.round(np.linspace(event_min, event_max, min(3, max(1, int(event_max - event_min + 1))))).astype(int))
    if size_values.size:
        size_handles = [
            Line2D(
                [0],
                [0],
                marker="o",
                linestyle="none",
                markerfacecolor="white",
                markeredgecolor=COLORS["ink"],
                markersize=math.sqrt(event_marker_size([value], event_min, event_max, minimum=12, maximum=48)[0]),
                label=f"{value:g} events",
            )
            for value in size_values
        ]
        fig.legend(
            size_handles,
            [handle.get_label() for handle in size_handles],
            title="Station support",
            loc="upper right",
            bbox_to_anchor=(0.972, 0.430),
            frameon=True,
            fontsize=7.6,
            title_fontsize=8.0,
        )
    source_handles = [
        Line2D([0], [0], color=SOURCE_COLORS["observed"], marker="o", linestyle="-", linewidth=1.55, markersize=4.5, label="Observed"),
        Line2D([0], [0], color=SOURCE_COLORS["synthetic"], marker="o", linestyle="-", linewidth=1.55, markersize=4.5, label="Synthetic"),
    ]
    fig.legend(
        source_handles,
        [handle.get_label() for handle in source_handles],
        loc="upper right",
        bbox_to_anchor=(0.972, 0.500),
        frameon=True,
        fontsize=7.8,
    )

    fig.text(
        0.055,
        0.010,
        (
            f"Stations are included within {SPLIT_STATION_CORRIDOR_KM:g} km of the profile. "
            f"LOWESS span is {ATLAS_LOWESS_FRAC:.2f}; station point area scales with event support. "
            f"Vertical-gradient window half-width is {VS_GRADIENT_WINDOW_HALF_KM:g} km."
        ),
        fontsize=8.2,
        color=COLORS["muted"],
        ha="left",
        va="bottom",
    )
    fig.subplots_adjust(left=0.055, right=0.975, top=0.928, bottom=0.074)
    fig.canvas.draw()
    fig.savefig(out_png, dpi=190)
    pdf.savefig(fig)
    plt.close(fig)


def render_corrected_profiles(args: argparse.Namespace) -> list[Path]:
    set_plot_theme()
    model_h5 = args.model_h5.expanduser()
    if not model_h5.exists():
        raise FileNotFoundError(
            f"Model HDF5 is required for properly rendered 0-{SECTION_MAX_DEPTH_KM:g} km model sections but was not found: {model_h5}"
        )

    output_dir = args.output_dir.expanduser().resolve()
    output_tag_parts = [slugify(args.output_tag or args.model_label)]
    if args.component is not None and args.output_tag is None:
        output_tag_parts.append(slugify(str(args.component)))
    output_tag = "_".join(part for part in output_tag_parts if part)
    run_slug = f"{OUTPUT_SLUG}_{output_tag}_{args.model_property}"
    figures_dir = output_dir / "figures" / run_slug
    tables_dir = output_dir / "tables" / run_slug
    report_dir = output_dir / "report" / run_slug
    basemap_cache_dir = output_dir / "basemap_cache"
    for directory in (figures_dir, tables_dir, report_dir, basemap_cache_dir):
        directory.mkdir(parents=True, exist_ok=True)

    regions = load_regions(DEFAULT_REGIONS)
    long_sections, perp_sections, metadata = build_profile_families(regions)
    sections = [*long_sections, *perp_sections]
    metadata_path = tables_dir / f"{run_slug}_sections.csv"
    metadata.to_csv(metadata_path, index=False)

    pairs = load_pairs(args)
    pairs_path = tables_dir / f"{run_slug}_pairs.parquet"
    pairs.to_parquet(pairs_path, index=False)
    corrected = corrected_source_rows(
        pairs,
        exponent=args.geometric_spreading_exponent,
        event_mean_reference=args.event_mean_reference,
        min_stations_per_event=args.min_stations_per_event,
    )
    corrected_path = tables_dir / f"{run_slug}_corrected_event_rows.parquet"
    corrected.to_parquet(corrected_path, index=False)

    sampler = ModelSampler(model_h5, node_stride=args.model_node_stride)
    section_grids = sample_section_grids(sampler, sections)
    add_vertical_property_gradient_cells(section_grids, args.model_property)
    property_gradient_norm = section_property_gradient_norm(section_grids, args.model_property)

    display_model_label = (
        f"{args.model_label} {str(args.component).upper()} component" if args.component is not None else args.model_label
    )
    page = page_spec(display_model_label, args.bands)
    transformer = Transformer.from_crs("EPSG:4326", CVM_UTM, always_xy=True)
    station_summaries: dict[tuple[str, str], pd.DataFrame] = {}
    for panel in page.panels:
        for source in SOURCE_LABELS:
            rows = corrected.loc[corrected["band"].eq(panel.band) & corrected["source"].eq(source)].copy()
            station_summaries[(panel.label, source)] = station_values(rows)

    projected: dict[tuple[str, str, str], pd.DataFrame] = {}
    for title, start_ll, end_ll in sections:
        profile_id = title.split()[0]
        line = section_line_utm(start_ll, end_ll, transformer)
        for panel in page.panels:
            for source in SOURCE_LABELS:
                frame = station_projection(
                    line,
                    station_summaries[(panel.label, source)],
                    transformer,
                    station_corridor_km=SPLIT_STATION_CORRIDOR_KM,
                )
                frame = add_model_depth_columns(frame, section_grids[profile_id], gradient_property=args.model_property)
                projected[(profile_id, panel.label, source)] = frame

    norm, y_limits = corrected_value_scale(projected)
    candidate_map_path = figures_dir / f"{run_slug}_candidate_lines_map.png"
    render_candidate_map(regions, sections, metadata, candidate_map_path, basemap_cache_dir=basemap_cache_dir)

    pdf_path = report_dir / f"{run_slug}.pdf"
    rendered_pages: list[Path] = []
    with PdfPages(pdf_path) as pdf:
        add_png_page_to_pdf(pdf, candidate_map_path)
        for profile_id in PROFILE_ORDER:
            out_png = figures_dir / f"{run_slug}_{profile_id}.png"
            render_profile_page(
                pdf=pdf,
                page=page,
                profile_id=profile_id,
                sections=sections,
                metadata=metadata,
                regions=regions,
                section_grids=section_grids,
                projected=projected,
                corrected_rows=corrected,
                y_limits=y_limits,
                norm=norm,
                property_gradient_norm=property_gradient_norm,
                basemap_cache_dir=basemap_cache_dir,
                out_png=out_png,
                model_label=display_model_label,
                model_property=args.model_property,
                exponent=args.geometric_spreading_exponent,
                event_mean_reference=args.event_mean_reference,
            )
            rendered_pages.append(out_png)

    projected_rows = []
    for (profile_id, band, source), frame in projected.items():
        if frame.empty:
            continue
        out = frame.copy()
        out.insert(0, "profile_id", profile_id)
        out.insert(1, "band", band)
        out.insert(2, "source", source)
        projected_rows.append(out)
    projected_path = tables_dir / f"{run_slug}_projected_stations.csv"
    if projected_rows:
        pd.concat(projected_rows, ignore_index=True).to_csv(projected_path, index=False)
    else:
        pd.DataFrame().to_csv(projected_path, index=False)

    manifest = {
        "workflow": OUTPUT_SLUG,
        "model": args.model,
        "comparison_model": args.comparison_model,
        "model_label": args.model_label,
        "model_property": args.model_property,
        "component": str(args.component).upper() if args.component is not None else None,
        "metric": METRIC,
        "bands": [str(band) for band in args.bands],
        "correction": {
            "formula": "log2(PGA * distance_km**exponent) - event_mean",
            "geometric_spreading_exponent": float(args.geometric_spreading_exponent),
            "event_mean_reference": args.event_mean_reference,
            "min_stations_per_event": int(args.min_stations_per_event),
        },
        "inputs": {
            "metrics": str(args.metrics),
            "pairs": str(args.pairs) if args.pairs is not None else None,
            "model_h5": str(model_h5),
            "regions": str(DEFAULT_REGIONS),
        },
        "outputs": {
            "pdf": str(pdf_path),
            "candidate_map": str(candidate_map_path),
            "profile_pages": [str(path) for path in rendered_pages],
            "pairs": str(pairs_path),
            "corrected_event_rows": str(corrected_path),
            "projected_stations": str(projected_path),
            "sections": str(metadata_path),
        },
    }
    manifest_path = report_dir / f"{run_slug}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_csv_path = report_dir / f"{run_slug}_manifest.csv"
    pd.DataFrame(
        [
            {"kind": "candidate_map", "path": str(candidate_map_path)},
            *({"kind": "profile_page", "path": str(path)} for path in rendered_pages),
            {"kind": "pdf", "path": str(pdf_path)},
            {"kind": "manifest_json", "path": str(manifest_path)},
            {"kind": "pairs", "path": str(pairs_path)},
            {"kind": "corrected_event_rows", "path": str(corrected_path)},
            {"kind": "projected_stations", "path": str(projected_path)},
            {"kind": "sections", "path": str(metadata_path)},
        ]
    ).to_csv(manifest_csv_path, index=False)
    return [candidate_map_path, *rendered_pages, pdf_path, manifest_path, manifest_csv_path, projected_path, corrected_path]


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    for path in render_corrected_profiles(args):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
