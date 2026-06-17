"""Notebook bootstrap helpers for running examples from a source checkout."""

from __future__ import annotations

from pathlib import Path
import sys


def use_source_checkout(start: str | Path | None = None) -> Path:
    """Make the nearest Spatial-VTK source checkout importable.

    Tutorial notebooks are often run directly from a freshly cloned repository,
    before the package has been installed. This helper finds the checkout root
    and prepends its ``src`` directory to ``sys.path`` when needed.
    """

    repo_root = find_source_checkout(start)
    src_path = repo_root / "src"
    src_text = str(src_path)
    if src_text not in sys.path:
        sys.path.insert(0, src_text)
    return repo_root


def find_source_checkout(start: str | Path | None = None) -> Path:
    """Return the nearest Spatial-VTK source checkout at or above ``start``."""

    current = Path.cwd() if start is None else Path(start)
    current = current.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "src" / "spatial_vtk").exists():
            return candidate
    raise RuntimeError(
        "Could not find a Spatial-VTK source checkout. Start Jupyter from the "
        "repository root or install the package before running the tutorial notebooks."
    )
