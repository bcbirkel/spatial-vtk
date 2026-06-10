"""Catalog readers for event, station, and geologic context tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from spatial_vtk.config.paths import (
    ROOT_DIR,
    default_event_patch_csv,
    default_events_csv,
    default_geology_csv,
    default_regions_geojson,
    default_subbasins_geojson,
)
from spatial_vtk.io.metadata import read_event_metadata, read_station_metadata


def read_events(path: str | Path | None = None, **kwargs) -> pd.DataFrame:
    """Read and standardize an event catalog.

    Parameters
    ----------
    path
        Event catalog path. When omitted, the public example path is used.
    **kwargs
        Additional arguments forwarded to ``pandas.read_csv``.

    Returns
    -------
    pandas.DataFrame
        Event table with standardized event and coordinate columns.
    """

    return read_event_metadata(path or default_events_csv(), **kwargs)


def read_stations(path: str | Path, **kwargs) -> pd.DataFrame:
    """Read and standardize a station catalog.

    Parameters
    ----------
    path
        Station catalog path.
    **kwargs
        Additional arguments forwarded to ``pandas.read_csv``.

    Returns
    -------
    pandas.DataFrame
        Station table with standardized station and coordinate columns.
    """

    return read_station_metadata(path, **kwargs)


def read_event_patch_table(path: str | Path | None = None, **kwargs) -> pd.DataFrame:
    """Read an optional event patch/context table.

    Parameters
    ----------
    path
        Event patch table path. When omitted, the public example path is used.
    **kwargs
        Additional arguments forwarded to ``pandas.read_csv``.

    Returns
    -------
    pandas.DataFrame
        Event patch table.
    """

    return pd.read_csv(path or default_event_patch_csv(), **kwargs)


def context_dataset_paths(root: str | Path | None = None) -> dict[str, Path]:
    """Return default public context-dataset paths.

    Parameters
    ----------
    root
        Optional repository root containing ``examples/data``.

    Returns
    -------
    dict
        Named paths for events, geology, regions, subbasins, and event patches.
    """

    if root is None:
        return {
            "events": default_events_csv(),
            "geology": default_geology_csv(),
            "regions": default_regions_geojson(),
            "subbasins": default_subbasins_geojson(),
            "event_patches": default_event_patch_csv(),
        }

    root_path = Path(root).expanduser().resolve()
    metadata_dir = root_path / "inputs" / "metadata"
    geospatial_dir = root_path / "inputs" / "geospatial"
    example_formats_dir = root_path / "data" / "examples" / "data_formats"
    example_workflow_dir = root_path / "data" / "examples" / "example_five_event_subset"

    def first_existing(candidates: tuple[Path, ...]) -> Path | None:
        """Return the first existing path from a candidate list.

        Parameters
        ----------
        candidates
            Candidate paths in priority order.

        Returns
        -------
        pathlib.Path or None
            First existing path, or ``None`` when no candidate exists.
        """

        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    events = first_existing(
        (
            metadata_dir / "salvus_events_m3above.csv",
            metadata_dir / "master_event_list.csv",
            metadata_dir / "all_events.csv",
            example_workflow_dir / "metadata" / "events.csv",
            example_formats_dir / "example_events.csv",
        )
    )
    if events is None and root_path == ROOT_DIR:
        events = default_events_csv()
    elif events is None:
        raise FileNotFoundError(
            f"No event catalog found under '{metadata_dir}' or '{example_formats_dir}'. "
            "Expected salvus_events_m3above.csv, master_event_list.csv, all_events.csv, "
            "or a public example event catalog."
        )

    return {
        "events": events,
        "geology": first_existing((metadata_dir / "geologic_metadata.csv", example_formats_dir / "example_site_metadata.csv")),
        "regions": first_existing(
            (
                geospatial_dir / "regions_updated.geojson",
                geospatial_dir / "regions.geojson",
                example_workflow_dir / "metadata" / "example_path_regions.geojson",
                example_formats_dir / "example_path_regions.geojson",
            )
        ),
        "subbasins": first_existing((geospatial_dir / "subbasins.geojson",)),
        "event_patches": first_existing((metadata_dir / "events_without_regions_patch.csv",)),
    }
