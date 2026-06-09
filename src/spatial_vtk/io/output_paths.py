"""Reusable output-path namespace helpers.

Purpose
-------
This module gives notebooks, scripts, and CLI wrappers a small common way to
name output files without repeatedly spelling out filenames in each workflow.

Usage examples
--------------
Create explicit CSV paths:
  ``tables = default_output_paths(output_root, ["prepared_stations", "prepared_events"])``
  ``stations.to_csv(tables.prepared_stations, index=False)``
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Iterable


def default_output_paths(
    output_dir: str | Path,
    names: Iterable[str],
    *,
    suffix: str = ".csv",
    create_dir: bool = True,
) -> SimpleNamespace:
    """Return a namespace of standard output paths.

    Parameters
    ----------
    output_dir
        Directory where output files should be written.
    names
        Basenames without extension, such as ``"qc_inventory"``.
    suffix
        File extension to append when a name has no extension.
    create_dir
        Whether to create ``output_dir``.

    Returns
    -------
    types.SimpleNamespace
        Namespace with one attribute per normalized name.
    """

    root = Path(output_dir).expanduser()
    if create_dir:
        root.mkdir(parents=True, exist_ok=True)
    paths = {}
    for raw_name in names:
        name = str(raw_name).strip()
        if not name:
            continue
        path = Path(name)
        attr = path.stem.replace("-", "_").replace(" ", "_")
        filename = path.name if path.suffix else f"{path.name}{suffix}"
        paths[attr] = root / filename
    return SimpleNamespace(**paths)


__all__ = ["default_output_paths"]
