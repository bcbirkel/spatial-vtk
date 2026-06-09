"""Naming helpers for public-facing model and dataset labels."""

from __future__ import annotations


def abbreviate_model(name: str) -> str:
    """Create a compact label from a synthetic model folder or alias.

    Parameters
    ----------
    name
        Model folder name or user-facing model alias.

    Returns
    -------
    str
        Compact model label when known tokens are found; otherwise the input
        name is returned unchanged.
    """

    raw = str(name)
    parts = raw.lower().replace("-", "_").split("_")
    abbrev: list[str] = []

    has_lab = any(part.startswith("cvmhlabn") for part in parts)
    has_all_basins = any(
        part.startswith(("cvmhlabn", "cvmhsgbn", "cvmhsbbn", "cvmhvbn"))
        for part in parts
    )
    if has_lab and not any(part.startswith("cvmhsgbn") for part in parts):
        abbrev.append("LABonly")
    if has_all_basins:
        abbrev.append("allBasins")

    if "cvmh" in parts or "cvm-h" in raw.lower():
        abbrev.append("H")
    elif "cvmsi" in parts or "cvm-si" in raw.lower():
        abbrev.append("SI")
    elif "cvms5" in parts or "cvms-5" in raw.lower():
        abbrev.append("S5")
    elif "cvms4" in parts or "cvms-4" in raw.lower():
        abbrev.append("S4")
    elif "bbp1d" in parts or "bbp-1d" in raw.lower():
        abbrev.append("BBP1D")

    if "elygtl" in parts or "ely" in parts or "ely" in raw.lower().split("-"):
        abbrev.append("Ely")

    return "+".join(abbrev) if abbrev else raw
