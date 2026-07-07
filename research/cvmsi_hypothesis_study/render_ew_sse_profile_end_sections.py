#!/usr/bin/env python3
"""Render EW CVM-SI cross sections shifted SSE, using only profile-end events."""

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


EVENT_CORRIDOR_KM = 100.0
STATION_CORRIDOR_KM = 10.0
SHIFT_AZIMUTH_DEG = 157.5


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
            f"{row.offset_km:.0f} km SSE, shift E {row.shift_east_km:.1f} km / N {row.shift_north_km:.1f} km, "
            f"LA Basin crossing {row.la_basin_intersection_km:.1f} km",
            fontsize=12,
            fontweight="bold",
        )
        ax.axis("off")
    fig.suptitle("EW CVM-SI cross-section series shifted SSE with profile-end events", fontsize=16, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.985])
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def main() -> int:
    set_plot_theme()
    output_dir = DEFAULT_OUTPUT
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    series_dir = figures_dir / "ew_sse_profile_end_sections"
    series_dir.mkdir(parents=True, exist_ok=True)

    pairs = pd.read_parquet(tables_dir / "pairs.parquet")
    regions = load_regions(DEFAULT_REGIONS)
    sections, metadata = build_southward_ew_section_series(
        regions,
        spacing_km=10.0,
        include_current=True,
        shift_azimuth_deg=SHIFT_AZIMUTH_DEG,
        direction_label="SSE",
    )
    metadata_path = tables_dir / "ew_sse_profile_end_cross_section_series.csv"
    metadata.to_csv(metadata_path, index=False)

    sampler = ModelSampler(DEFAULT_MODEL_H5, node_stride=2)
    rendered_paths: list[Path] = []
    for section, row in zip(sections, metadata.itertuples(index=False)):
        offset_km = int(round(row.offset_km))
        title = f"CVM-SI Vs EW cross section {offset_km:02d} km SSE of current line"
        note = (
            f"Event filter: profile-end PGA 3-5 sec records within {EVENT_CORRIDOR_KM:g} km of the line axis; "
            f"station summaries use those filtered records and stations within {STATION_CORRIDOR_KM:g} km of the profile.\n"
            f"Midpoint lat {row.mid_lat:.3f}; LA Basin crossing {row.la_basin_intersection_km:.1f} km. "
            "Stars mark selected profile-end event epicenters."
        )
        path = plot_model_cross_sections(
            pairs,
            regions,
            sampler,
            series_dir,
            basemap_cache_dir=output_dir / "basemap_cache",
            basemap_zoom=DEFAULT_BASEMAP_ZOOM,
            event_selection="profile_ends",
            event_corridor_km=EVENT_CORRIDOR_KM,
            output_name=f"fig_06e_ew_sse_profile_end_{offset_km:02d}km.png",
            sections=[section],
            figure_title=title,
            figure_note=note,
            figsize=(19.8, 7.8),
            station_corridor_km=STATION_CORRIDOR_KM,
            include_default_event_note=False,
        )
        rendered_paths.append(path)

    contact_path = figures_dir / "fig_06e_ew_sse_profile_end_cross_sections_contact_sheet.png"
    build_contact_sheet(rendered_paths, metadata, contact_path)
    print(metadata_path)
    for path in rendered_paths:
        print(path)
    print(contact_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
