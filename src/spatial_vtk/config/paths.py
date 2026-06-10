"""Centralized filesystem locations for spatial-vtk.

This module defines repository-relative input and output paths that are shared
across the packaged workflow families.

Examples
--------
>>> from spatial_vtk.config.paths import ROOT_DIR, default_events_csv
>>> ROOT_DIR.exists()
True
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional


# Resolve repository root (parent of the `src` tree).
ROOT_DIR: Path = Path(__file__).resolve().parents[3]

# Canonical input locations.
INPUTS_DIR: Path = ROOT_DIR / "inputs"
METADATA_DIR: Path = INPUTS_DIR / "metadata"
GEOSPATIAL_DIR: Path = INPUTS_DIR / "geospatial"
RAW_DATA_DIR: Path = ROOT_DIR / "data"
EXAMPLE_DATA_DIR: Path = RAW_DATA_DIR / "examples"
NOTEBOOKS_DIR: Path = ROOT_DIR / "notebooks"
EXAMPLE_NOTEBOOKS_DIR: Path = NOTEBOOKS_DIR / "examples"

# Canonical output locations.
OUTPUTS_DIR: Path = ROOT_DIR / "outputs"
FIGURES_DIR: Path = OUTPUTS_DIR / "figures"
METRICS_DIR: Path = OUTPUTS_DIR / "metrics"
STATS_DIR: Path = OUTPUTS_DIR / "stats"
CACHE_DIR: Path = OUTPUTS_DIR / "cache"
EXAMPLE_FORMATS_DIR: Path = EXAMPLE_DATA_DIR / "data_formats"
EXAMPLE_WORKFLOW_DIR: Path = EXAMPLE_DATA_DIR / "example_five_event_subset"


def ensure_dir(path: Path) -> Path:
    """Create one directory path when it does not already exist.

    Parameters
    ----------
    path
        Directory path to create.

    Returns
    -------
    pathlib.Path
        The same path after ensuring it exists.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_events_csv(name: str = "salvus_events_m3above.csv") -> Path:
    """Return the default event catalog path.

    Parameters
    ----------
    name
        Preferred event-catalog filename under ``inputs/metadata``.

    Returns
    -------
    pathlib.Path
        Existing event catalog path, falling back to ``all_events.csv``.

    Raises
    ------
    FileNotFoundError
        If neither the preferred catalog nor the fallback exists.
    """
    candidate = METADATA_DIR / name
    if candidate.exists():
        return candidate
    for fallback_name in ("master_event_list.csv", "all_events.csv"):
        fallback = METADATA_DIR / fallback_name
        if fallback.exists():
            return fallback
    for example in (
        EXAMPLE_WORKFLOW_DIR / "metadata" / "events.csv",
        EXAMPLE_FORMATS_DIR / "example_events.csv",
    ):
        if example.exists():
            return example
    raise FileNotFoundError(
        f"Neither '{candidate}', '{METADATA_DIR / 'master_event_list.csv'}', "
        f"nor '{METADATA_DIR / 'all_events.csv'}' exists, and no public example "
        "event catalog was found under data/examples."
    )


def default_geology_csv() -> Optional[Path]:
    """Return the default station geology metadata CSV when present.

    Returns
    -------
    pathlib.Path or None
        Existing geology CSV path or ``None``.
    """
    candidate = METADATA_DIR / "geologic_metadata.csv"
    if candidate.exists():
        return candidate
    example = EXAMPLE_FORMATS_DIR / "example_site_metadata.csv"
    return example if example.exists() else None


def default_regions_geojson() -> Optional[Path]:
    """Return the regional polygons GeoJSON when present.

    Returns
    -------
    pathlib.Path or None
        Existing regions GeoJSON path or ``None``.
    """
    for name in ("regions_updated.geojson", "regions.geojson"):
        candidate = GEOSPATIAL_DIR / name
        if candidate.exists():
            return candidate
    for example in (
        EXAMPLE_WORKFLOW_DIR / "metadata" / "example_path_regions.geojson",
        EXAMPLE_FORMATS_DIR / "example_path_regions.geojson",
    ):
        if example.exists():
            return example
    return None


def default_subbasins_geojson() -> Optional[Path]:
    """Return the subbasin polygons path when available.

    Returns
    -------
    pathlib.Path or None
        Existing subbasins GeoJSON path or ``None``.
    """
    candidate = GEOSPATIAL_DIR / "subbasins.geojson"
    if candidate.exists():
        return candidate
    return None


def default_event_patch_csv() -> Optional[Path]:
    """Return the optional event-region patch CSV when present.

    Returns
    -------
    pathlib.Path or None
        Existing patch CSV path or ``None``.
    """
    candidate = METADATA_DIR / "events_without_regions_patch.csv"
    return candidate if candidate.exists() else None
