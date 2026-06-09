"""Metric workflow manifests and batch execution.

Purpose
-------
This module writes resumable metric task manifests, runs individual batches,
and merges batch outputs.

Usage examples
--------------
Write a manifest and run the first batch:
  ``manifest = write_task_manifest(tasks, "metrics_manifest.json", output_dir="metric_batches")``
  ``run_manifest_batch(manifest, batch_index=0)``
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from spatial_vtk.io.compute_manifest import read_json, write_json
from spatial_vtk.metrics.workflow.run import run_metric_tasks, write_metric_rows
from spatial_vtk.metrics.workflow.tasks import MetricWorkflowTask


MANIFEST_VERSION = 1


@dataclass(frozen=True)
class MetricWorkflowManifest:
    """Metric workflow manifest payload.

    Parameters
    ----------
    manifest_path
        Path to the JSON manifest.
    tasks
        Planned metric tasks.
    batches
        Batch dictionaries with task indices and output paths.
    qc_table
        Optional QC table path.

    Returns
    -------
    MetricWorkflowManifest
        Immutable manifest object.
    """

    manifest_path: Path
    tasks: tuple[MetricWorkflowTask, ...]
    batches: tuple[dict[str, Any], ...]
    qc_table: str = ""


def chunk_tasks(tasks: list[MetricWorkflowTask], *, chunk_size: int) -> list[list[MetricWorkflowTask]]:
    """Split tasks into fixed-size chunks.

    Parameters
    ----------
    tasks
        Workflow tasks.
    chunk_size
        Maximum tasks per chunk.

    Returns
    -------
    list[list[MetricWorkflowTask]]
        Chunked tasks.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    return [tasks[start:start + int(chunk_size)] for start in range(0, len(tasks), int(chunk_size))]


def write_task_manifest(
    tasks: list[MetricWorkflowTask],
    manifest_path: str | Path,
    *,
    output_dir: str | Path,
    batch_size: int = 100,
    qc_table: str | Path | None = None,
    output_suffix: str = ".csv",
) -> MetricWorkflowManifest:
    """Write a metric task manifest.

    Parameters
    ----------
    tasks
        Planned metric tasks.
    manifest_path
        Destination JSON manifest.
    output_dir
        Directory for per-batch metric outputs.
    batch_size
        Maximum tasks per batch.
    qc_table
        Optional QC table path copied into the manifest.
    output_suffix
        Output suffix for batch tables, usually ``.csv`` or ``.parquet``.

    Returns
    -------
    MetricWorkflowManifest
        Written manifest object.
    """

    manifest = Path(manifest_path).expanduser()
    batch_dir = Path(output_dir).expanduser()
    batch_dir.mkdir(parents=True, exist_ok=True)
    chunks = chunk_tasks(tasks, chunk_size=batch_size)
    batches: list[dict[str, Any]] = []
    cursor = 0
    suffix = output_suffix if str(output_suffix).startswith(".") else f".{output_suffix}"
    for batch_index, chunk in enumerate(chunks):
        indices = list(range(cursor, cursor + len(chunk)))
        cursor += len(chunk)
        batches.append(
            {
                "batch_index": batch_index,
                "task_indices": indices,
                "output_path": str(batch_dir / f"metrics_batch_{batch_index:04d}{suffix}"),
                "status": "planned",
            }
        )
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "qc_table": str(qc_table or ""),
        "tasks": [task.to_dict() for task in tasks],
        "batches": batches,
    }
    write_json(manifest, payload)
    return MetricWorkflowManifest(manifest_path=manifest, tasks=tuple(tasks), batches=tuple(batches), qc_table=str(qc_table or ""))


def read_task_manifest(path: str | Path) -> MetricWorkflowManifest:
    """Read a metric task manifest.

    Parameters
    ----------
    path
        Manifest JSON path.

    Returns
    -------
    MetricWorkflowManifest
        Parsed manifest object.
    """

    manifest_path = Path(path).expanduser()
    payload = read_json(manifest_path)
    tasks = tuple(MetricWorkflowTask.from_dict(item) for item in payload.get("tasks", []))
    batches = tuple(dict(item) for item in payload.get("batches", []))
    return MetricWorkflowManifest(
        manifest_path=manifest_path,
        tasks=tasks,
        batches=batches,
        qc_table=str(payload.get("qc_table", "")),
    )


def run_manifest_batch(
    manifest: MetricWorkflowManifest | str | Path,
    *,
    batch_index: int,
    overwrite: bool = False,
) -> Path:
    """Run one batch from a metric task manifest.

    Parameters
    ----------
    manifest
        Manifest object or path.
    batch_index
        Batch index to run.
    overwrite
        Whether to replace an existing batch output.

    Returns
    -------
    pathlib.Path
        Batch output path.
    """

    parsed = read_task_manifest(manifest) if not isinstance(manifest, MetricWorkflowManifest) else manifest
    batch = _batch_by_index(parsed, batch_index)
    output_path = Path(batch["output_path"]).expanduser()
    if output_path.exists() and not overwrite:
        return output_path
    selected_tasks = [parsed.tasks[int(index)] for index in batch["task_indices"]]
    rows = run_metric_tasks(selected_tasks, qc_table=parsed.qc_table or None)
    return write_metric_rows(rows, output_path)


def merge_batch_outputs(
    manifest: MetricWorkflowManifest | str | Path,
    output_path: str | Path,
    *,
    require_all: bool = True,
) -> Path:
    """Merge batch outputs from a manifest into one metric table.

    Parameters
    ----------
    manifest
        Manifest object or path.
    output_path
        Destination merged table.
    require_all
        Whether every planned batch output must exist.

    Returns
    -------
    pathlib.Path
        Written merged output path.
    """

    parsed = read_task_manifest(manifest) if not isinstance(manifest, MetricWorkflowManifest) else manifest
    frames: list[pd.DataFrame] = []
    missing: list[str] = []
    for batch in parsed.batches:
        path = Path(batch["output_path"]).expanduser()
        if not path.exists():
            missing.append(str(path))
            continue
        frames.append(_read_table(path))
    if missing and require_all:
        raise FileNotFoundError(f"Missing metric batch outputs: {missing}")
    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return write_metric_rows(merged, output_path)


def _batch_by_index(manifest: MetricWorkflowManifest, batch_index: int) -> dict[str, Any]:
    """Return one batch dictionary by index."""

    for batch in manifest.batches:
        if int(batch["batch_index"]) == int(batch_index):
            return batch
    raise IndexError(f"Batch index {batch_index} is not present in manifest {manifest.manifest_path}.")


def _read_table(path: str | Path) -> pd.DataFrame:
    """Read one CSV or parquet table."""

    table_path = Path(path).expanduser()
    if table_path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(table_path)
    return pd.read_csv(table_path)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the batch-execution CLI parser."""

    parser = argparse.ArgumentParser(description="Run one Spatial-VTK metric manifest batch.")
    parser.add_argument("--manifest", required=True, help="Metric workflow manifest JSON.")
    parser.add_argument("--batch-index", type=int, required=True, help="Batch index to run.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing batch output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one manifest batch from CLI arguments."""

    args = build_arg_parser().parse_args(argv)
    run_manifest_batch(args.manifest, batch_index=args.batch_index, overwrite=args.overwrite)
    return 0


__all__ = [
    "MANIFEST_VERSION",
    "MetricWorkflowManifest",
    "chunk_tasks",
    "merge_batch_outputs",
    "read_task_manifest",
    "run_manifest_batch",
    "write_task_manifest",
    "build_arg_parser",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
