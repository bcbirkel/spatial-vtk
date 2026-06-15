#!/usr/bin/env python
"""Benchmark metric runtime with a temporary metric-ready waveform cache.

This utility is intended for large-run diagnostics. It selects a small subset
of tasks from a metric manifest, runs them against the original waveform files,
materializes just the needed station/component traces as lightweight ``.npz``
files, and reruns the same tasks against the cached files.
"""

from __future__ import annotations

import argparse
import shutil
import time
from dataclasses import replace
from pathlib import Path
from typing import Any


def build_arg_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Metric workflow manifest JSON.")
    parser.add_argument("--batch-index", type=int, default=0, help="Manifest batch index to sample.")
    parser.add_argument("--task-count", type=int, default=30, help="Number of tasks from the batch to benchmark.")
    parser.add_argument(
        "--cache-root",
        default="runs/outputs/metric_ready_waveform_cache_probe",
        help="Directory for temporary cached .npz traces.",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Remove the cache directory before materializing the subset.",
    )
    parser.add_argument(
        "--compressed",
        action="store_true",
        help="Use np.savez_compressed instead of uncompressed np.savez.",
    )
    parser.add_argument(
        "--progress-interval",
        type=int,
        default=10,
        help="Task interval for progress messages.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the subset benchmark."""

    args = build_arg_parser().parse_args(argv)

    from spatial_vtk.metrics.workflow.execution import read_task_manifest
    from spatial_vtk.metrics.workflow.run import run_metric_tasks

    manifest = read_task_manifest(args.manifest)
    if args.batch_index < 0 or args.batch_index >= len(manifest.batches):
        raise ValueError(f"Batch index {args.batch_index} is outside 0-{len(manifest.batches) - 1}.")

    task_indices = manifest.batches[args.batch_index]["task_indices"][: max(0, args.task_count)]
    tasks = [manifest.tasks[int(index)] for index in task_indices]
    if not tasks:
        raise ValueError("No tasks were selected for benchmarking.")

    cache_root = Path(args.cache_root).expanduser()
    if args.clear_cache and cache_root.exists():
        shutil.rmtree(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)

    print(f"subset_tasks: {len(tasks)}", flush=True)
    print(
        "subset_first_last: "
        f"{_task_label(tasks[0])} -> {_task_label(tasks[-1])}",
        flush=True,
    )

    warm_timing: dict[str, float] = {}
    run_metric_tasks(tasks[:1], qc_table=manifest.qc_table or None, timing=warm_timing)
    print(f"warmup_timing: {_rounded(warm_timing)}", flush=True)

    original_timing: dict[str, float] = {}
    original_start = time.monotonic()
    original_rows = run_metric_tasks(
        tasks,
        qc_table=manifest.qc_table or None,
        progress_label="original-subset",
        progress_interval=args.progress_interval,
        timing=original_timing,
    )
    original_elapsed = time.monotonic() - original_start
    print(f"original_elapsed_s: {original_elapsed:.3f}; rows: {len(original_rows)}", flush=True)
    print(f"original_timing: {_rounded(original_timing)}", flush=True)

    cache_index: dict[tuple[str, str, str, str, str], str] = {}
    cache_stats = {"materialized": 0, "reused": 0}
    materialize_start = time.monotonic()
    cached_tasks = [
        _task_with_cached_paths(
            task,
            cache_root=cache_root,
            compressed=args.compressed,
            cache_index=cache_index,
            cache_stats=cache_stats,
        )
        for task in tasks
    ]
    materialize_elapsed = time.monotonic() - materialize_start
    cache_files = sorted(cache_root.rglob("*.npz"))
    cache_bytes = sum(path.stat().st_size for path in cache_files)
    print(
        "cache_materialize_s: "
        f"{materialize_elapsed:.3f}; files: {len(cache_files)}; "
        f"materialized: {cache_stats['materialized']}; reused: {cache_stats['reused']}; "
        f"size_mb: {cache_bytes / 1024**2:.3f}",
        flush=True,
    )

    cached_timing: dict[str, float] = {}
    cached_start = time.monotonic()
    cached_rows = run_metric_tasks(
        cached_tasks,
        qc_table=manifest.qc_table or None,
        progress_label="cached-subset",
        progress_interval=args.progress_interval,
        timing=cached_timing,
    )
    cached_elapsed = time.monotonic() - cached_start
    print(f"cached_elapsed_s: {cached_elapsed:.3f}; rows: {len(cached_rows)}", flush=True)
    print(f"cached_timing: {_rounded(cached_timing)}", flush=True)

    total_cached_elapsed = cached_elapsed + materialize_elapsed
    print(f"row_count_match: {len(original_rows) == len(cached_rows)}", flush=True)
    print(f"speedup_metric_run_x: {_ratio(original_elapsed, cached_elapsed):.3f}", flush=True)
    print(f"speedup_including_materialize_x: {_ratio(original_elapsed, total_cached_elapsed):.3f}", flush=True)
    return 0


def _task_with_cached_paths(
    task: Any,
    *,
    cache_root: Path,
    compressed: bool,
    cache_index: dict[tuple[str, str, str, str, str], str],
    cache_stats: dict[str, int],
) -> Any:
    """Return a task with observed/synthetic paths replaced by cached traces."""

    obs_path = (
        _materialize_one(
            "observed",
            task.obs_waveform_path,
            task.event_id,
            task.station,
            task.component,
            cache_root=cache_root,
            compressed=compressed,
            cache_index=cache_index,
            cache_stats=cache_stats,
        )
        if task.obs_waveform_path
        else ""
    )
    syn_path = (
        _materialize_one(
            "synthetic",
            task.syn_waveform_path,
            task.event_id,
            task.station,
            task.component,
            cache_root=cache_root,
            compressed=compressed,
            cache_index=cache_index,
            cache_stats=cache_stats,
        )
        if task.syn_waveform_path
        else ""
    )
    return replace(task, obs_waveform_path=obs_path, syn_waveform_path=syn_path)


def _materialize_one(
    source: str,
    path: str,
    event_id: str,
    station: str,
    component: str,
    *,
    cache_root: Path,
    compressed: bool,
    cache_index: dict[tuple[str, str, str, str, str], str],
    cache_stats: dict[str, int],
) -> str:
    """Write one station/component trace as a metric-ready ``.npz`` file."""

    import numpy as np
    from spatial_vtk.metrics.workflow.run import _load_component_samples

    key = (source, path, event_id, station, component)
    if key in cache_index:
        return cache_index[key]

    out = cache_root / source / _safe_token(event_id) / f"{_safe_token(station)}_{_safe_token(component)}.npz"
    if out.exists():
        cache_stats["reused"] += 1
        cache_index[key] = str(out)
        return str(out)

    side = _load_component_samples(path, station, component)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "data": np.asarray(side.data, dtype=np.float32),
        "channels": np.asarray([f"HN{component}"]),
        "station": np.asarray(station),
        "sampling_rate": np.asarray(1.0 / float(side.dt), dtype=float),
        "starttime": np.asarray(""),
    }
    if compressed:
        np.savez_compressed(out, **payload)
    else:
        np.savez(out, **payload)
    cache_stats["materialized"] += 1
    cache_index[key] = str(out)
    return str(out)


def _safe_token(value: object) -> str:
    """Return a filesystem-safe path token."""

    text = str(value).strip() or "blank"
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text)[:120]


def _task_label(task: Any) -> tuple[str, str, str, str]:
    """Return a compact task label for logs."""

    return (str(task.event_id), str(task.station), str(task.component), str(task.passband))


def _rounded(values: dict[str, float]) -> dict[str, float]:
    """Round timing values for stable console output."""

    return {key: round(value, 3) for key, value in sorted(values.items())}


def _ratio(numerator: float, denominator: float) -> float:
    """Return a finite speedup ratio."""

    return numerator / denominator if denominator else float("inf")


if __name__ == "__main__":
    raise SystemExit(main())
