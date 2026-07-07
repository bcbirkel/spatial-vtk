#!/usr/bin/env python3
"""Render LA Basin PGA/model comparison profile pages for CVM-SI and CVM-H."""

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
    DEFAULT_REGIONS,
    ModelSampler,
    load_regions,
    set_plot_theme,
)
from render_la_basin_axis_profile_sections import build_profile_families, render_candidate_map  # noqa: E402
from render_la_basin_metric_profile_atlas import (  # noqa: E402
    ATLAS_LOWESS_FRAC,
    PROFILE_ORDER,
    VS_GRADIENT_WINDOW_HALF_KM,
    add_png_page_to_pdf,
    add_vertical_property_gradient_cells,
    event_marker_size,
    sample_section_grids,
    section_line_utm,
    station_projection,
)
from render_la_basin_metric_profile_split_pages import (  # noqa: E402
    PROPERTY_LABELS,
    SECTION_MAX_DEPTH_KM,
    SPLIT_STATION_CORRIDOR_KM,
    plot_profile_map,
    plot_section_grid,
    property_variants,
    weighted_lowess_by_column,
)
from render_la_basin_pga_obs_syn_corrected_profile_sections import (  # noqa: E402
    VALUE_COLUMN,
    corrected_value_scale,
)


OUTPUT_SLUG = "la_basin_pga_cvm_model_comparison_profiles"
BANDS = ("1-2 sec", "2-3 sec", "3-5 sec")
SERIES_COLORS = {"observed": "#111111", "cvmh_synthetic": "#d34a3f", "cvmsi_synthetic": "#2b6cb0"}
SERIES_LABELS = {"observed": "Observed", "cvmh_synthetic": "CVM-H synthetic", "cvmsi_synthetic": "CVM-SI synthetic"}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cvmh-analysis-dir", type=Path, required=True)
    parser.add_argument("--cvmsi-analysis-dir", type=Path, required=True)
    parser.add_argument("--cvmh-h5", type=Path, required=True)
    parser.add_argument("--cvmsi-h5", type=Path, required=True)
    parser.add_argument("--model-node-stride", type=int, default=2)
    parser.add_argument("--model-property", choices=("vs", "vp"), default="vs")
    parser.add_argument("--component", default=None, help="Optional component label used in corrected-PGA input slugs, e.g. T or Z.")
    return parser.parse_args(argv)


def corrected_slug(model_tag: str, model_property: str, component: str | None) -> str:
    parts = ["la_basin_pga_obs_syn_corrected_profile_sections", model_tag]
    if component:
        parts.append(slugify(component))
    parts.append(model_property)
    return "_".join(parts)


def load_corrected_rows_fast(analysis_dir: Path, slug: str) -> pd.DataFrame:
    path = analysis_dir / "tables" / slug / f"{slug}_corrected_event_rows.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Missing corrected PGA rows: {path}")
    columns = [
        "event_id",
        "station",
        "band",
        "source",
        "event_lon",
        "event_lat",
        "sta_lon",
        "sta_lat",
        VALUE_COLUMN,
    ]
    return pd.read_parquet(path, columns=columns)


def build_series_rows(cvmh_rows: pd.DataFrame, cvmsi_rows: pd.DataFrame) -> pd.DataFrame:
    observed = cvmh_rows.loc[cvmh_rows["source"].eq("observed")].copy()
    observed["series"] = "observed"
    cvmh_syn = cvmh_rows.loc[cvmh_rows["source"].eq("synthetic")].copy()
    cvmh_syn["series"] = "cvmh_synthetic"
    cvmsi_syn = cvmsi_rows.loc[cvmsi_rows["source"].eq("synthetic")].copy()
    cvmsi_syn["series"] = "cvmsi_synthetic"
    rows = pd.concat([observed, cvmh_syn, cvmsi_syn], ignore_index=True)
    rows = rows.loc[rows["band"].astype(str).isin(BANDS)].copy()
    rows[VALUE_COLUMN] = pd.to_numeric(rows[VALUE_COLUMN], errors="coerce")
    return rows.replace([np.inf, -np.inf], np.nan).dropna(subset=[VALUE_COLUMN, "sta_lon", "sta_lat"])


def comparison_station_values(data: pd.DataFrame) -> pd.DataFrame:
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
            events=("event_id", "nunique"),
            records=(VALUE_COLUMN, "size"),
        )
        .replace([np.inf, -np.inf], np.nan)
        .dropna(subset=["sta_lon", "sta_lat", "value"])
    )


def project_series(
    rows: pd.DataFrame,
    sections: list[tuple[str, tuple[float, float], tuple[float, float]]],
    transformer: Transformer,
) -> dict[tuple[str, str, str], pd.DataFrame]:
    summaries: dict[tuple[str, str], pd.DataFrame] = {}
    for band in BANDS:
        for series in SERIES_COLORS:
            data = rows.loc[rows["band"].eq(band) & rows["series"].eq(series)].copy()
            summaries[(band, series)] = comparison_station_values(data)

    projected: dict[tuple[str, str, str], pd.DataFrame] = {}
    for title, start_ll, end_ll in sections:
        profile_id = title.split()[0]
        line = section_line_utm(start_ll, end_ll, transformer)
        for band in BANDS:
            for series in SERIES_COLORS:
                projected[(profile_id, band, series)] = station_projection(
                    line,
                    summaries[(band, series)],
                    transformer,
                    station_corridor_km=SPLIT_STATION_CORRIDOR_KM,
                )
    return projected


def sample_model_grids(
    *,
    cvmh_h5: Path,
    cvmsi_h5: Path,
    node_stride: int,
    sections: list[tuple[str, tuple[float, float], tuple[float, float]]],
    model_property: str,
) -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    cvmh = sample_section_grids(ModelSampler(cvmh_h5, node_stride=node_stride), sections)
    cvmsi = sample_section_grids(ModelSampler(cvmsi_h5, node_stride=node_stride), sections)
    add_vertical_property_gradient_cells(cvmh, model_property)
    add_vertical_property_gradient_cells(cvmsi, model_property)
    return cvmh, cvmsi


def shared_norm(values: list[np.ndarray], minimum: float = 0.05) -> TwoSlopeNorm:
    finite = np.concatenate([value[np.isfinite(value)] for value in values if np.isfinite(value).any()]) if values else np.array([])
    if finite.size:
        span = float(np.nanquantile(np.abs(finite), 0.98))
        span = max(span * 1.05, minimum)
    else:
        span = minimum
    return TwoSlopeNorm(vmin=-span, vcenter=0.0, vmax=span)


def difference_norms(
    cvmh_grids: dict[str, dict[str, object]],
    cvmsi_grids: dict[str, dict[str, object]],
    model_property: str,
) -> tuple[TwoSlopeNorm, TwoSlopeNorm]:
    gradient_key = f"vertical_{model_property}_gradient_cell"
    model_diffs = [np.asarray(cvmsi_grids[key][model_property]) - np.asarray(cvmh_grids[key][model_property]) for key in PROFILE_ORDER]
    grad_diffs = [np.asarray(cvmsi_grids[key][gradient_key]) - np.asarray(cvmh_grids[key][gradient_key]) for key in PROFILE_ORDER]
    return shared_norm(model_diffs, minimum=0.05), shared_norm(grad_diffs, minimum=0.05)


def plot_model_difference(ax: plt.Axes, section_grid: dict[str, object], values: np.ndarray, norm: TwoSlopeNorm, label: str) -> object:
    distances_km = np.asarray(section_grid["distances_km"], dtype=float)
    depths_km = np.asarray(section_grid["depths_km"], dtype=float)
    image = ax.contourf(distances_km, depths_km, values, levels=np.linspace(norm.vmin, norm.vmax, 25), cmap="RdBu_r", norm=norm, extend="both")
    style_section_axis(ax, section_grid, label)
    return image


def plot_gradient_difference(ax: plt.Axes, section_grid: dict[str, object], values: np.ndarray, norm: TwoSlopeNorm, label: str) -> object:
    distances_km = np.asarray(section_grid["distances_km"], dtype=float)
    depths_km = np.asarray(section_grid["depths_km"], dtype=float)
    image = ax.pcolormesh(distances_km, depths_km, values, cmap="RdBu_r", norm=norm, shading="flat", rasterized=True)
    style_section_axis(ax, section_grid, label)
    return image


def style_section_axis(ax: plt.Axes, section_grid: dict[str, object], label: str) -> None:
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


def plot_pga_panel(
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
    nonempty = {series: frame for series, frame in frames.items() if not frame.empty}
    if not nonempty:
        ax.text(0.5, 0.5, "No stations", ha="center", va="center", transform=ax.transAxes, color=COLORS["muted"], fontsize=9)
        return
    for series, frame in frames.items():
        if frame.empty:
            continue
        color = SERIES_COLORS[series]
        yerr = np.vstack([np.clip(frame["value"] - frame["q25"], 0.0, None), np.clip(frame["q75"] - frame["value"], 0.0, None)])
        ax.errorbar(
            frame["projected_km"],
            frame["value"],
            yerr=yerr,
            fmt="none",
            ecolor=color,
            elinewidth=0.55,
            alpha=0.24,
            capsize=1.0,
            zorder=2,
        )
        ax.scatter(
            frame["projected_km"],
            frame["value"],
            color=color,
            s=event_marker_size(frame["events"], event_min, event_max, minimum=12, maximum=48),
            edgecolor=color,
            linewidth=0.18,
            alpha=0.36,
            zorder=3,
        )
        lowess_x, lowess_y = weighted_lowess_by_column(frame, x_col="projected_km")
        if lowess_x.size:
            ax.plot(lowess_x, lowess_y, color=color, linewidth=1.45, alpha=0.86, zorder=4)
    count_text = "; ".join(f"{SERIES_LABELS[series]} {frame['station'].nunique():,} sta" for series, frame in nonempty.items())
    ax.text(
        0.985,
        0.90,
        count_text,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=6.3,
        color=COLORS["muted"],
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.74, "pad": 1.2},
        zorder=5,
    )


def render_profile_page(
    *,
    pdf: PdfPages,
    profile_id: str,
    sections: list[tuple[str, tuple[float, float], tuple[float, float]]],
    metadata: pd.DataFrame,
    regions: list,
    projected: dict[tuple[str, str, str], pd.DataFrame],
    rows: pd.DataFrame,
    cvmh_grids: dict[str, dict[str, object]],
    cvmsi_grids: dict[str, dict[str, object]],
    y_limits: tuple[float, float],
    model_diff_norm: TwoSlopeNorm,
    gradient_diff_norm: TwoSlopeNorm,
    basemap_cache_dir: Path,
    out_png: Path,
    model_property: str,
    component: str | None,
) -> None:
    property_label = PROPERTY_LABELS[model_property]
    absolute_variant, _ = property_variants(model_property)
    cvmh_grid = cvmh_grids[profile_id]
    cvmsi_grid = cvmsi_grids[profile_id]
    gradient_key = f"vertical_{model_property}_gradient_cell"
    row = metadata.set_index("profile_id").loc[profile_id]
    section_length_km = float(cvmsi_grid["length_km"])
    frame_lookup = {
        (band, series): projected[(profile_id, band, series)]
        for band in BANDS
        for series in SERIES_COLORS
    }
    station_frame = (
        pd.concat([frame[["station", "sta_lon", "sta_lat"]] for frame in frame_lookup.values() if not frame.empty], ignore_index=True)
        .drop_duplicates("station")
        if any(not frame.empty for frame in frame_lookup.values())
        else pd.DataFrame(columns=["station", "sta_lon", "sta_lat"])
    )
    station_ids = set(station_frame["station"].astype(str))
    events = (
        rows.loc[rows["station"].astype(str).isin(station_ids), ["event_id", "station", "event_lon", "event_lat"]]
        .dropna(subset=["event_lon", "event_lat"])
        .drop_duplicates("event_id")
    )
    event_values = np.concatenate([frame["events"].to_numpy(dtype=float) for frame in frame_lookup.values() if not frame.empty])
    event_min = float(np.nanmin(event_values)) if event_values.size else 1.0
    event_max = float(np.nanmax(event_values)) if event_values.size else event_min

    fig = plt.figure(figsize=(18.0, 15.2), constrained_layout=False)
    grid = fig.add_gridspec(
        nrows=8,
        ncols=8,
        height_ratios=[0.36, 0.92, 0.92, 0.92, 1.0, 1.0, 1.0, 1.0],
        width_ratios=[1.0, 1.0, 0.050, 1.0, 1.0, 0.050, 0.95, 0.95],
        hspace=0.42,
        wspace=0.25,
    )
    component_text = f" {component.upper()} component" if component else ""
    title = (
        f"CVM-SI/CVM-H{component_text} corrected PGA and {property_label} comparison {profile_id}: "
        f"{row.family.replace('_', ' ')} ({row.bearing_deg:.1f} deg; LA Basin crossing {row.la_basin_intersection_km:.1f} km)"
    )
    fig.suptitle(title, fontsize=16.4, fontweight="bold", color=COLORS["ink"], y=0.988)
    fig.text(
        0.055,
        0.958,
        (
            "PGA panels show observed, CVM-H synthetic, and CVM-SI synthetic station medians of "
            "event-centered log2(PGA x distance^1). Model rows compare absolute model structure and signed vertical-gradient differences."
        ),
        ha="left",
        va="top",
        fontsize=9.3,
        color=COLORS["muted"],
    )
    for row_index, band in enumerate(BANDS, start=1):
        ax = fig.add_subplot(grid[row_index, :5])
        plot_pga_panel(
            ax,
            {series: frame_lookup[(band, series)] for series in SERIES_COLORS},
            band=band,
            y_limits=y_limits,
            event_min=event_min,
            event_max=event_max,
            section_length_km=section_length_km,
        )
        if row_index < len(BANDS):
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

    si_ax = fig.add_subplot(grid[4, :5])
    h_ax = fig.add_subplot(grid[5, :5])
    diff_ax = fig.add_subplot(grid[6, :5])
    grad_diff_ax = fig.add_subplot(grid[7, :5])
    si_img = plot_section_grid(si_ax, cvmsi_grid, variant=absolute_variant, vs_gradient_norm=None)
    h_img = plot_section_grid(h_ax, cvmh_grid, variant=absolute_variant, vs_gradient_norm=None)
    for ax, label in ((si_ax, f"CVM-SI {property_label}"), (h_ax, f"CVM-H {property_label}")):
        style_section_axis(ax, cvmsi_grid, label)
        ax.tick_params(labelbottom=False)
    model_diff = np.asarray(cvmsi_grid[model_property], dtype=float) - np.asarray(cvmh_grid[model_property], dtype=float)
    grad_diff = np.asarray(cvmsi_grid[gradient_key], dtype=float) - np.asarray(cvmh_grid[gradient_key], dtype=float)
    diff_img = plot_model_difference(diff_ax, cvmsi_grid, model_diff, model_diff_norm, f"CVM-SI - CVM-H {property_label}")
    grad_img = plot_gradient_difference(
        grad_diff_ax,
        cvmsi_grid,
        grad_diff,
        gradient_diff_norm,
        f"CVM-SI - CVM-H vertical {property_label} gradient",
    )
    diff_ax.tick_params(labelbottom=False)
    grad_diff_ax.set_xlabel("Distance along profile (km)", fontsize=8.8)

    caxes = [fig.add_subplot(grid[row_index, 5]) for row_index in range(4, 8)]
    cbar = fig.colorbar(si_img, cax=caxes[0])
    cbar.set_label(f"CVM-SI {property_label} (km/s)", fontsize=7.8, labelpad=6)
    cbar = fig.colorbar(h_img, cax=caxes[1])
    cbar.set_label(f"CVM-H {property_label} (km/s)", fontsize=7.8, labelpad=6)
    cbar = fig.colorbar(diff_img, cax=caxes[2], extend="both")
    cbar.set_label(f"Delta {property_label} (km/s)", fontsize=7.8, labelpad=6)
    cbar = fig.colorbar(grad_img, cax=caxes[3], extend="both")
    cbar.set_label(f"Delta gradient ((km/s)/km)", fontsize=7.8, labelpad=6)
    for cax in caxes:
        cax.tick_params(labelsize=6.4)

    source_handles = [
        Line2D([0], [0], color=SERIES_COLORS[key], marker="o", linestyle="-", linewidth=1.45, markersize=4.2, label=SERIES_LABELS[key])
        for key in SERIES_COLORS
    ]
    fig.legend(source_handles, [handle.get_label() for handle in source_handles], loc="upper right", bbox_to_anchor=(0.972, 0.505), frameon=True, fontsize=7.6)
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
            fontsize=7.4,
            title_fontsize=7.8,
        )
    fig.text(
        0.055,
        0.010,
        (
            f"Stations are included within {SPLIT_STATION_CORRIDOR_KM:g} km of the profile. "
            f"LOWESS span is {ATLAS_LOWESS_FRAC:.2f}; station point area scales with event support. "
            f"Vertical-gradient window half-width is {VS_GRADIENT_WINDOW_HALF_KM:g} km."
        ),
        fontsize=8.0,
        color=COLORS["muted"],
        ha="left",
        va="bottom",
    )
    fig.subplots_adjust(left=0.055, right=0.975, top=0.934, bottom=0.064)
    fig.canvas.draw()
    fig.savefig(out_png, dpi=190)
    pdf.savefig(fig)
    plt.close(fig)


def render(args: argparse.Namespace) -> list[Path]:
    set_plot_theme()
    component_slug = slugify(args.component) if args.component else "all"
    run_slug = f"{OUTPUT_SLUG}_{component_slug}_{args.model_property}"
    output_dir = args.output_dir.expanduser().resolve()
    figures_dir = output_dir / "figures" / run_slug
    report_dir = output_dir / "report" / run_slug
    tables_dir = output_dir / "tables" / run_slug
    basemap_cache_dir = output_dir / "basemap_cache"
    for path in (figures_dir, report_dir, tables_dir, basemap_cache_dir):
        path.mkdir(parents=True, exist_ok=True)

    cvmh_slug = corrected_slug("cvm_h", args.model_property, args.component)
    cvmsi_slug = corrected_slug("cvm_si", args.model_property, args.component)
    cvmh_rows = load_corrected_rows_fast(args.cvmh_analysis_dir.expanduser(), cvmh_slug)
    cvmsi_rows = load_corrected_rows_fast(args.cvmsi_analysis_dir.expanduser(), cvmsi_slug)
    rows = build_series_rows(cvmh_rows, cvmsi_rows)
    rows_path = tables_dir / f"{run_slug}_event_rows.parquet"
    rows.to_parquet(rows_path, index=False)

    regions = load_regions(DEFAULT_REGIONS)
    long_sections, perp_sections, metadata = build_profile_families(regions)
    sections = [*long_sections, *perp_sections]
    metadata_path = tables_dir / f"{run_slug}_sections.csv"
    metadata.to_csv(metadata_path, index=False)
    transformer = Transformer.from_crs("EPSG:4326", CVM_UTM, always_xy=True)
    projected = project_series(rows, sections, transformer)
    projected_rows = []
    for (profile_id, band, series), frame in projected.items():
        if frame.empty:
            continue
        out = frame.copy()
        out.insert(0, "profile_id", profile_id)
        out.insert(1, "band", band)
        out.insert(2, "series", series)
        projected_rows.append(out)
    projected_path = tables_dir / f"{run_slug}_projected_stations.csv"
    if projected_rows:
        pd.concat(projected_rows, ignore_index=True).to_csv(projected_path, index=False)
    else:
        pd.DataFrame().to_csv(projected_path, index=False)

    cvmh_grids, cvmsi_grids = sample_model_grids(
        cvmh_h5=args.cvmh_h5.expanduser(),
        cvmsi_h5=args.cvmsi_h5.expanduser(),
        node_stride=args.model_node_stride,
        sections=sections,
        model_property=args.model_property,
    )
    model_diff_norm, gradient_diff_norm = difference_norms(cvmh_grids, cvmsi_grids, args.model_property)
    _, y_limits = corrected_value_scale(projected)
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
                profile_id=profile_id,
                sections=sections,
                metadata=metadata,
                regions=regions,
                projected=projected,
                rows=rows,
                cvmh_grids=cvmh_grids,
                cvmsi_grids=cvmsi_grids,
                y_limits=y_limits,
                model_diff_norm=model_diff_norm,
                gradient_diff_norm=gradient_diff_norm,
                basemap_cache_dir=basemap_cache_dir,
                out_png=out_png,
                model_property=args.model_property,
                component=args.component,
            )
            rendered_pages.append(out_png)
    manifest = {
        "workflow": OUTPUT_SLUG,
        "model_property": args.model_property,
        "component": args.component.upper() if args.component else None,
        "inputs": {
            "cvmh_corrected_slug": cvmh_slug,
            "cvmsi_corrected_slug": cvmsi_slug,
            "cvmh_h5": str(args.cvmh_h5),
            "cvmsi_h5": str(args.cvmsi_h5),
        },
        "outputs": {
            "pdf": str(pdf_path),
            "candidate_map": str(candidate_map_path),
            "profile_pages": [str(path) for path in rendered_pages],
            "event_rows": str(rows_path),
            "projected_stations": str(projected_path),
        },
    }
    manifest_path = report_dir / f"{run_slug}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return [candidate_map_path, *rendered_pages, pdf_path, manifest_path, rows_path, projected_path]


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    for path in render(args):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
