#!/usr/bin/env python3
"""User-defined named station-bounds presets.

Spatial-VTK does not ship project-specific map-bound keywords. If you want
short names such as ``"my_region"`` for map windows or station filters, define
them in a CSV file and point the configuration at that file.

Examples
--------
>>> from spatial_vtk.config.bounds import preset_keywords
>>> isinstance(preset_keywords(), tuple)
True
"""

from __future__ import annotations

import csv
from pathlib import Path

from spatial_vtk.config.paths import ROOT_DIR


DEFAULT_PRESET_CSV = ROOT_DIR / "configs" / "station_bounds_presets.csv"


def load_bounds_presets(csv_path: Path | None = None) -> dict[str, tuple[float, float, float, float]]:
    """Load named station-bounds presets from CSV.

    Parameters
    ----------
    csv_path
        Optional override for the preset CSV path.

    Returns
    -------
    dict[str, tuple[float, float, float, float]]
        Mapping from lowercase keywords to
        ``(lon_min, lon_max, lat_min, lat_max)``.
    """

    path = Path(csv_path) if csv_path is not None else DEFAULT_PRESET_CSV
    presets: dict[str, tuple[float, float, float, float]] = {}
    if not path.exists():
        return presets
    with path.open("r", newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            key = str(row.get("keyword", "")).strip().lower()
            if not key:
                continue
            presets[key] = (
                float(row["lon_min"]),
                float(row["lon_max"]),
                float(row["lat_min"]),
                float(row["lat_max"]),
            )
    return presets


def preset_keywords(include_none: bool = False) -> tuple[str, ...]:
    """Return the available named station-bounds keywords.

    Parameters
    ----------
    include_none
        Whether to append the special ``"none"`` token.

    Returns
    -------
    tuple[str, ...]
        Accepted keyword strings.
    """

    keys = tuple(sorted(load_bounds_presets().keys()))
    if include_none:
        return keys + ("none",)
    return keys


def resolve_named_bounds(keyword: str | None) -> tuple[float, float, float, float] | None:
    """Resolve one named station-bounds preset.

    Parameters
    ----------
    keyword
        Preset keyword, or ``"none"`` / ``None``.

    Returns
    -------
    tuple[float, float, float, float] or None
        ``(lon_min, lon_max, lat_min, lat_max)``, or ``None`` for ``"none"``.

    Raises
    ------
    KeyError
        If the requested preset keyword is unknown.
    """

    token = str(keyword or "").strip().lower()
    if token in {"", "none"}:
        return None
    presets = load_bounds_presets()
    if token not in presets:
        raise KeyError(f"Unknown station-bounds preset: {keyword}")
    return presets[token]
