"""Lightweight input file inventory helpers.

Purpose
-------
This module records what observed and synthetic input files are present before
metric calculation. It is intentionally lightweight and does not read waveform
samples.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
import hashlib

import pandas as pd


DEFAULT_WAVEFORM_SUFFIXES = frozenset({".mseed", ".ms", ".sac", ".h5", ".hdf5", ".asdf", ".json", ".pkl"})


def compute_sha256(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Compute the SHA-256 digest for one file.

    Parameters
    ----------
    path
        File to hash.
    chunk_size
        Number of bytes read per chunk.

    Returns
    -------
    str
        Hexadecimal SHA-256 digest.
    """

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(int(chunk_size)), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_file_inventory(
    root: str | Path,
    *,
    dataset: str,
    suffixes: Iterable[str] = DEFAULT_WAVEFORM_SUFFIXES,
    relative_to: str | Path | None = None,
    include_sha256: bool = True,
) -> pd.DataFrame:
    """Build a lightweight inventory of files under one input folder.

    Parameters
    ----------
    root
        Folder to scan recursively.
    dataset
        Dataset label recorded in the output, such as ``"observed"`` or
        ``"synthetic"``.
    suffixes
        File suffixes to include.
    relative_to
        Optional base path used to store relative paths.
    include_sha256
        Whether to compute file hashes.

    Returns
    -------
    pandas.DataFrame
        Inventory table with dataset, path, filename, suffix, size, and
        optional SHA-256 columns.
    """

    root_path = Path(root).expanduser().resolve()
    base = Path(relative_to).expanduser().resolve() if relative_to is not None else root_path
    suffix_set = {str(suffix).lower() for suffix in suffixes}
    rows: list[dict[str, object]] = []
    if not root_path.exists():
        return pd.DataFrame(columns=["dataset", "path", "filename", "suffix", "size_bytes", "sha256"])
    for path in sorted(root_path.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in suffix_set:
            continue
        try:
            recorded_path = path.relative_to(base)
        except ValueError:
            recorded_path = path
        row: dict[str, object] = {
            "dataset": str(dataset),
            "path": str(recorded_path),
            "filename": path.name,
            "suffix": path.suffix.lower(),
            "size_bytes": int(path.stat().st_size),
        }
        if include_sha256:
            row["sha256"] = compute_sha256(path)
        rows.append(row)
    columns = ["dataset", "path", "filename", "suffix", "size_bytes"]
    if include_sha256:
        columns.append("sha256")
    return pd.DataFrame(rows, columns=columns)


def build_observed_synthetic_inventory(
    observed_root: str | Path,
    synthetic_root: str | Path,
    *,
    suffixes: Iterable[str] = DEFAULT_WAVEFORM_SUFFIXES,
    relative_to: str | Path | None = None,
    include_sha256: bool = True,
) -> pd.DataFrame:
    """Build one combined inventory for observed and synthetic inputs.

    Parameters
    ----------
    observed_root
        Observed input folder.
    synthetic_root
        Synthetic input folder.
    suffixes
        File suffixes to include.
    relative_to
        Optional base path used to store relative paths.
    include_sha256
        Whether to compute file hashes.

    Returns
    -------
    pandas.DataFrame
        Combined observed/synthetic file inventory.
    """

    observed = build_file_inventory(observed_root, dataset="observed", suffixes=suffixes, relative_to=relative_to, include_sha256=include_sha256)
    synthetic = build_file_inventory(synthetic_root, dataset="synthetic", suffixes=suffixes, relative_to=relative_to, include_sha256=include_sha256)
    return pd.concat([observed, synthetic], ignore_index=True)
