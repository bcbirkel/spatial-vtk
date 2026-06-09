"""Shared helpers for chunked compute workflows.

Purpose
-------
This module provides small, dependency-light utilities for commands that split
large work into resumable chunks. It handles JSON manifests, atomic CSV writes,
run-directory creation, and SLURM array script generation.

Usage examples
--------------
Create a run directory:
  ``run_dir = ensure_run_dir("metrics", "abcdef")``

Write a SLURM array script:
  ``write_slurm_array_script(path, chunks_path="chunks.json", worker_command="python worker.py")``
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


def utc_run_id() -> str:
    """Return a compact UTC timestamp suitable for run-directory names.

    Parameters
    ----------
    None

    Returns
    -------
    str
        Timestamp such as ``20260512T024500Z``.
    """

    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_run_dir(
    output_root: str | os.PathLike[str],
    workflow: str,
    config_hash: str,
    *,
    run_id: str | None = None,
    work_root: str | os.PathLike[str] | None = None,
) -> Path:
    """Create and return a compute-workflow run directory.

    Parameters
    ----------
    output_root
        Metrics or figure output root used when ``work_root`` is not supplied.
    workflow
        Workflow name, for example ``"metrics_export"``.
    config_hash
        Hash identifying the effective run configuration.
    run_id
        Optional human-readable run identifier.
    work_root
        Optional explicit parent work directory.

    Returns
    -------
    pathlib.Path
        Created run directory.
    """

    base = Path(work_root).expanduser() if work_root else Path(output_root).expanduser() / "_work"
    run_dir = base / workflow / str(config_hash) / (run_id or utc_run_id())
    run_dir.mkdir(parents=True, exist_ok=True)
    for child in ("chunks", "logs"):
        (run_dir / child).mkdir(exist_ok=True)
    return run_dir


def write_json(path: str | os.PathLike[str], payload: Mapping[str, Any] | list[Any]) -> Path:
    """Atomically write one JSON payload.

    Parameters
    ----------
    path
        Destination JSON path.
    payload
        JSON-serializable mapping or list.

    Returns
    -------
    pathlib.Path
        Written path.
    """

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return target


def read_json(path: str | os.PathLike[str]) -> Any:
    """Read one JSON file.

    Parameters
    ----------
    path
        JSON path.

    Returns
    -------
    object
        Decoded JSON payload.
    """

    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_write_csv(df: pd.DataFrame, path: str | os.PathLike[str]) -> Path:
    """Atomically write a dataframe to CSV.

    Parameters
    ----------
    df
        Dataframe to write.
    path
        Destination CSV path.

    Returns
    -------
    pathlib.Path
        Written CSV path.
    """

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    os.replace(tmp, target)
    return target


def write_slurm_array_script(
    path: str | os.PathLike[str],
    *,
    chunks_path: str | os.PathLike[str],
    worker_command: str,
    num_chunks: int,
    max_concurrent: int,
    job_name: str = "svtk-metrics-export",
    time_limit: str = "12:00:00",
    cpus_per_task: int = 1,
    memory: str = "8G",
) -> Path:
    """Write a conservative SLURM array script for chunk workers.

    Parameters
    ----------
    path
        Script destination path.
    chunks_path
        JSON file containing chunk specs.
    worker_command
        Command prefix that accepts ``--chunks-json`` and ``--chunk-index``.
    num_chunks
        Number of chunks in the array.
    max_concurrent
        Maximum concurrent array tasks.
    job_name, time_limit, cpus_per_task, memory
        SLURM resource settings.

    Returns
    -------
    pathlib.Path
        Written script path.
    """

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    last_index = max(0, int(num_chunks) - 1)
    throttle = max(1, int(max_concurrent))
    text = "\n".join(
        [
            "#!/bin/bash",
            f"#SBATCH --job-name={job_name}",
            f"#SBATCH --array=0-{last_index}%{throttle}",
            f"#SBATCH --time={time_limit}",
            f"#SBATCH --cpus-per-task={int(cpus_per_task)}",
            f"#SBATCH --mem={memory}",
            "#SBATCH --output=logs/%x_%A_%a.out",
            "#SBATCH --error=logs/%x_%A_%a.err",
            "",
            "set -euo pipefail",
            "cd \"$(dirname \"$0\")\"",
            "export OMP_NUM_THREADS=1",
            "export MKL_NUM_THREADS=1",
            "export OPENBLAS_NUM_THREADS=1",
            "",
            f"{worker_command} --chunks-json {Path(chunks_path)} --chunk-index $SLURM_ARRAY_TASK_ID",
            "",
        ]
    )
    target.write_text(text, encoding="utf-8")
    target.chmod(0o755)
    return target
