#!/usr/bin/env python3
"""Render EW CVM-SI cross sections shifted SSE, using all events by passband."""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from cvmsi_hypothesis_study import (
    DEFAULT_BASEMAP_ZOOM,
    DEFAULT_MODEL_H5,
    DEFAULT_OUTPUT,
    DEFAULT_REGIONS,
    ModelSampler,
    build_southward_ew_section_series,
    load_regions,
    plot_model_cross_sections,
    set_plot_theme,
)


STATION_CORRIDOR_KM = 10.0
SHIFT_AZIMUTH_DEG = 157.5
METRIC = "PGA"
BANDS = (
    ("1-2 sec", "1_2sec"),
    ("2-3 sec", "2_3sec"),
    ("3-5 sec", "3_5sec"),
)


def build_contact_sheet(paths: list[Path], metadata: pd.DataFrame, output_path: Path, *, band: str) -> Path:
    ncols = 2
    nrows = math.ceil(len(paths) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(18.5, 5.2 * nrows))
    axes = axes.ravel() if hasattr(axes, "ravel") else [axes]
    for ax in axes:
        ax.axis("off")
    for ax, path, row in zip(axes, paths, metadata.itertuples(index=False)):
        image = plt.imread(path)
        ax.imshow(image)
        ax.set_title(
            f"{row.offset_km:.0f} km SSE, shift E {row.shift_east_km:.1f} km / N {row.shift_north_km:.1f} km, "
            f"LA Basin crossing {row.la_basin_intersection_km:.1f} km",
            fontsize=12,
            fontweight="bold",
        )
        ax.axis("off")
    fig.suptitle(
        f"EW CVM-SI cross-section series shifted SSE with all-event {METRIC} {band} residuals",
        fontsize=16,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.985])
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def render_band(
    *,
    band: str,
    band_slug: str,
    pairs: pd.DataFrame,
    regions: list,
    sections: list,
    metadata: pd.DataFrame,
    sampler: ModelSampler,
    output_dir: Path,
) -> list[Path]:
    figures_dir = output_dir / "figures"
    series_dir = figures_dir / "ew_sse_all_events_sections" / band_slug
    series_dir.mkdir(parents=True, exist_ok=True)

    rendered_paths: list[Path] = []
    for section, row in zip(sections, metadata.itertuples(index=False)):
        offset_km = int(round(row.offset_km))
        title = f"CVM-SI Vs EW cross section {offset_km:02d} km SSE of current line"
        note = (
            f"{METRIC} {band} station medians use all available events; stations are limited to "
            f"{STATION_CORRIDOR_KM:g} km from the profile. Black curve is LOWESS weighted by station event count.\n"
            f"Midpoint lat {row.mid_lat:.3f}; LA Basin crossing {row.la_basin_intersection_km:.1f} km. "
            "Stars mark event epicenters contributing to the plotted station subset."
        )
        path = plot_model_cross_sections(
            pairs,
            regions,
            sampler,
            series_dir,
            basemap_cache_dir=output_dir / "basemap_cache",
            basemap_zoom=DEFAULT_BASEMAP_ZOOM,
            metric=METRIC,
            band=band,
            output_name=f"fig_06f_ew_sse_all_events_{band_slug}_{offset_km:02d}km.png",
            sections=[section],
            figure_title=title,
            figure_note=note,
            figsize=(19.8, 7.8),
            station_corridor_km=STATION_CORRIDOR_KM,
            show_events_on_map=True,
            show_lowess=True,
            lowess_frac=0.65,
        )
        rendered_paths.append(path)

    contact_path = figures_dir / f"fig_06f_ew_sse_all_events_{band_slug}_cross_sections_contact_sheet.png"
    build_contact_sheet(rendered_paths, metadata, contact_path, band=band)
    return [*rendered_paths, contact_path]


def main() -> int:
    set_plot_theme()
    output_dir = DEFAULT_OUTPUT
    tables_dir = output_dir / "tables"
    pairs = pd.read_parquet(tables_dir / "pairs.parquet")
    regions = load_regions(DEFAULT_REGIONS)
    sections, metadata = build_southward_ew_section_series(
        regions,
        spacing_km=10.0,
        include_current=True,
        shift_azimuth_deg=SHIFT_AZIMUTH_DEG,
        direction_label="SSE",
    )
    metadata_path = tables_dir / "ew_sse_all_events_cross_section_series.csv"
    metadata.to_csv(metadata_path, index=False)

    sampler = ModelSampler(DEFAULT_MODEL_H5, node_stride=2)
    print(metadata_path)
    for band, band_slug in BANDS:
        paths = render_band(
            band=band,
            band_slug=band_slug,
            pairs=pairs,
            regions=regions,
            sections=sections,
            metadata=metadata,
            sampler=sampler,
            output_dir=output_dir,
        )
        for path in paths:
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
