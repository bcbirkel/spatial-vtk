"""File-layout inspection helpers for station/event datasets."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def inspect_station_event_layouts(
    root: str | Path,
    *,
    suffixes: tuple[str, ...] = (".csv", ".json", ".geojson", ".mseed", ".h5", ".hdf5", ".asdf"),
    max_files: int | None = None,
) -> pd.DataFrame:
    """Inventory station/event files below a root directory.

    Parameters
    ----------
    root
        Directory to inspect.
    suffixes
        File suffixes to include.
    max_files
        Optional cap on the number of files returned.

    Returns
    -------
    pandas.DataFrame
        File inventory with relative path, suffix, size, and light metadata.
    """

    root_path = Path(root).expanduser()
    if not root_path.is_dir():
        raise NotADirectoryError(f"root is not a directory: {root_path}")
    rows: list[dict[str, object]] = []
    normalized_suffixes = tuple(suffix.lower() for suffix in suffixes)
    for path in sorted(root_path.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in normalized_suffixes:
            continue
        rows.append(_describe_file(path, root_path))
        if max_files is not None and len(rows) >= max_files:
            break
    return pd.DataFrame(rows)


def _describe_file(path: Path, root: Path) -> dict[str, object]:
    """Describe one file for layout inspection."""

    stat = path.stat()
    row: dict[str, object] = {
        "path": str(path),
        "relative_path": str(path.relative_to(root)),
        "suffix": path.suffix.lower(),
        "size_bytes": int(stat.st_size),
        "parent": str(path.parent.relative_to(root)),
    }
    if path.suffix.lower() in {".json", ".geojson"}:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                row["json_keys"] = ",".join(sorted(str(key) for key in payload.keys())[:12])
                row["json_type"] = str(payload.get("type", "object"))
        except Exception as exc:  # pragma: no cover - informational only
            row["read_error"] = str(exc)
    return row
