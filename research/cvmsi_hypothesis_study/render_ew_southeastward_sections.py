#!/usr/bin/env python3
"""Render EW CVM-SI cross sections every 10 km southeast across the LA Basin."""

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


def build_contact_sheet(paths: list[Path], metadata: pd.DataFrame, output_path: Path) -> Path:
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
            f"{row.offset_km:.0f} km SE, shift E {row.shift_east_km:.1f} km / N {row.shift_north_km:.1f} km, "
            f"LA Basin crossing {row.la_basin_intersection_km:.1f} km",
            fontsize=12,
            fontweight="bold",
        )
        ax.axis("off")
    fig.suptitle("EW CVM-SI cross-section series shifted southeast from Santa Monica-Glendale-San Gabriel", fontsize=16, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.985])
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def main() -> int:
    set_plot_theme()
    output_dir = DEFAULT_OUTPUT
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    series_dir = figures_dir / "ew_southeastward_sections"
    series_dir.mkdir(parents=True, exist_ok=True)

    pairs = pd.read_parquet(tables_dir / "pairs.parquet")
    regions = load_regions(DEFAULT_REGIONS)
    sections, metadata = build_southward_ew_section_series(
        regions,
        spacing_km=10.0,
        include_current=True,
        shift_azimuth_deg=135.0,
        direction_label="SE",
    )
    metadata_path = tables_dir / "ew_southeastward_cross_section_series.csv"
    metadata.to_csv(metadata_path, index=False)

    sampler = ModelSampler(DEFAULT_MODEL_H5, node_stride=2)
    rendered_paths: list[Path] = []
    for section, row in zip(sections, metadata.itertuples(index=False)):
        offset_km = int(round(row.offset_km))
        title = f"CVM-SI Vs EW cross section {offset_km:02d} km SE of current line"
        note = (
            "PGA 3-5 sec station medians use all available events, with stations limited to 10 km of the profile. "
            f"Shifted line midpoint lat {row.mid_lat:.3f}; "
            f"LA Basin polygon intersection along this profile is {row.la_basin_intersection_km:.1f} km. "
            "Stars mark event epicenters contributing to the plotted station subset."
        )
        path = plot_model_cross_sections(
            pairs,
            regions,
            sampler,
            series_dir,
            basemap_cache_dir=output_dir / "basemap_cache",
            basemap_zoom=DEFAULT_BASEMAP_ZOOM,
            output_name=f"fig_06d_ew_se_{offset_km:02d}km.png",
            sections=[section],
            figure_title=title,
            figure_note=note,
            figsize=(19.8, 7.8),
            station_corridor_km=10.0,
            show_events_on_map=True,
        )
        rendered_paths.append(path)

    contact_path = figures_dir / "fig_06d_ew_southeastward_cross_sections_contact_sheet.png"
    build_contact_sheet(rendered_paths, metadata, contact_path)
    print(metadata_path)
    for path in rendered_paths:
        print(path)
    print(contact_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
