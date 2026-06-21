"""Metric-ready waveform cache helpers.

Purpose
-------
This module materializes the station/component traces referenced by a metric
manifest into lightweight ``.npz`` files and writes a new manifest that points
at those cached traces. The metric runner can then use the same batch logic
while avoiding repeated reads of larger pickle or ASDF waveform containers.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
import time
from typing import Any

import numpy as np

from spatial_vtk.io.compute_manifest import write_json
from spatial_vtk.metrics.workflow.execution import MANIFEST_VERSION, MetricWorkflowManifest, read_task_manifest
from spatial_vtk.metrics.workflow.run import _load_component_samples
from spatial_vtk.metrics.workflow.tasks import MetricWorkflowTask


@dataclass(frozen=True)
class MetricWaveformCacheResult:
    """Summary of a cached metric manifest write."""

    manifest: MetricWorkflowManifest
    cache_root: Path
    materialized_files: int
    reused_files: int
    in_memory_reuses: int
    source_references: int

    @property
    def metric_manifest_cached_path(self) -> Path:
        """Path to the cached metric workflow manifest."""

        return self.manifest.manifest_path

    @property
    def metric_ready_waveform_cache_root(self) -> Path:
        """Directory containing cached metric-ready waveform arrays."""

        return self.cache_root

    @property
    def metric_batches_cached_dir(self) -> Path | None:
        """Directory containing cached-manifest batch output files, if present."""

        if not self.manifest.batches:
            return None
        output_path = self.manifest.batches[0].get("output_path")
        return Path(str(output_path)).expanduser().parent if output_path else None

    def status_frame(self) -> Any:
        """Return a compact summary of cached metric workflow outputs."""

        import pandas as pd

        rows = [
            {
                "name": "metric_manifest_cached_path",
                "artifact_label": "cached metric manifest",
                "resolved_path": str(self.metric_manifest_cached_path),
                "path": str(self.metric_manifest_cached_path),
                "exists": self.metric_manifest_cached_path.exists(),
                "rows": len(self.manifest.tasks),
                "materialized_files": self.materialized_files,
                "reused_files": self.reused_files,
                "in_memory_reuses": self.in_memory_reuses,
                "source_references": self.source_references,
            },
            {
                "name": "metric_ready_waveform_cache_root",
                "artifact_label": "metric-ready waveform cache",
                "resolved_path": str(self.metric_ready_waveform_cache_root),
                "path": str(self.metric_ready_waveform_cache_root),
                "exists": self.metric_ready_waveform_cache_root.exists(),
                "rows": self.source_references,
                "materialized_files": self.materialized_files,
                "reused_files": self.reused_files,
                "in_memory_reuses": self.in_memory_reuses,
                "source_references": self.source_references,
            },
        ]
        batch_dir = self.metric_batches_cached_dir
        if batch_dir is not None:
            rows.append(
                {
                    "name": "metric_batches_cached_dir",
                    "artifact_label": "cached metric batch output directory",
                    "resolved_path": str(batch_dir),
                    "path": str(batch_dir),
                    "exists": batch_dir.exists(),
                    "rows": len(self.manifest.batches),
                    "materialized_files": self.materialized_files,
                    "reused_files": self.reused_files,
                    "in_memory_reuses": self.in_memory_reuses,
                    "source_references": self.source_references,
                }
            )
        return pd.DataFrame(rows)


def cache_metric_manifest_waveforms(
    manifest: MetricWorkflowManifest | str | Path,
    output_manifest: str | Path,
    *,
    cache_root: str | Path,
    batch_output_dir: str | Path | None = None,
    overwrite: bool = False,
    compressed: bool = False,
    progress_label: str | None = None,
    progress_interval: int = 100,
) -> MetricWaveformCacheResult:
    """Write a cached copy of a metric manifest.

    Parameters
    ----------
    manifest
        Source metric workflow manifest.
    output_manifest
        Destination manifest whose tasks will point at cached ``.npz`` traces.
    cache_root
        Directory where metric-ready traces are written.
    batch_output_dir
        Optional output directory for the cached manifest's batch files. When
        omitted, a sibling ``*_batches`` directory is derived from
        ``output_manifest``.
    overwrite
        Whether to rewrite existing cached trace files.
    compressed
        Whether to write compressed ``.npz`` files. Uncompressed files are
        larger but usually faster to read.
    progress_label
        Optional label for flushed progress messages.
    progress_interval
        Print progress after this many tasks when ``progress_label`` is set.

    Returns
    -------
    MetricWaveformCacheResult
        New manifest object and cache statistics.
    """

    parsed = read_task_manifest(manifest) if not isinstance(manifest, MetricWorkflowManifest) else manifest
    output_path = Path(output_manifest).expanduser()
    cache_dir = Path(cache_root).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    batch_dir = Path(batch_output_dir).expanduser() if batch_output_dir else output_path.with_suffix("").parent / f"{output_path.stem}_batches"
    batch_dir.mkdir(parents=True, exist_ok=True)

    stats = _CacheStats()
    cache_index: dict[tuple[str, str, str, str, str], str] = {}
    start = time.monotonic()
    cached_tasks: list[MetricWorkflowTask] = []
    total = len(parsed.tasks)
    interval = max(1, int(progress_interval))
    for index, task in enumerate(parsed.tasks, start=1):
        cached_tasks.append(
            _cache_task_waveforms(
                task,
                cache_root=cache_dir,
                overwrite=overwrite,
                compressed=compressed,
                cache_index=cache_index,
                stats=stats,
            )
        )
        if progress_label and (index == 1 or index == total or index % interval == 0):
            elapsed = time.monotonic() - start
            rate = index / elapsed if elapsed > 0 else 0.0
            eta = (total - index) / rate if rate > 0 else 0.0
            print(
                f"{progress_label}: task {index}/{total} "
                f"(elapsed {_format_duration(elapsed)}, {rate:.2f} tasks/s, ETA {_format_duration(eta)})",
                flush=True,
            )

    batches = _cached_batches(parsed.batches, batch_dir=batch_dir)
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "qc_table": parsed.qc_table,
        "tasks": [task.to_dict() for task in cached_tasks],
        "batches": batches,
    }
    write_json(output_path, payload)
    new_manifest = read_task_manifest(output_path)
    return MetricWaveformCacheResult(
        manifest=new_manifest,
        cache_root=cache_dir,
        materialized_files=stats.materialized_files,
        reused_files=stats.reused_files,
        in_memory_reuses=stats.in_memory_reuses,
        source_references=stats.source_references,
    )


@dataclass
class _CacheStats:
    """Mutable cache-write counters."""

    materialized_files: int = 0
    reused_files: int = 0
    in_memory_reuses: int = 0
    source_references: int = 0


def _cache_task_waveforms(
    task: MetricWorkflowTask,
    *,
    cache_root: Path,
    overwrite: bool,
    compressed: bool,
    cache_index: dict[tuple[str, str, str, str, str], str],
    stats: _CacheStats,
) -> MetricWorkflowTask:
    """Return one task with waveform paths replaced by cache paths."""

    obs_path = (
        _cache_one_waveform(
            "observed",
            task.obs_waveform_path,
            task.event_id,
            task.station,
            task.component,
            cache_root=cache_root,
            overwrite=overwrite,
            compressed=compressed,
            cache_index=cache_index,
            stats=stats,
        )
        if task.obs_waveform_path
        else ""
    )
    syn_path = (
        _cache_one_waveform(
            "synthetic",
            task.syn_waveform_path,
            task.event_id,
            task.station,
            task.component,
            cache_root=cache_root,
            overwrite=overwrite,
            compressed=compressed,
            cache_index=cache_index,
            stats=stats,
        )
        if task.syn_waveform_path
        else ""
    )
    return replace(task, obs_waveform_path=obs_path, syn_waveform_path=syn_path)


def _cache_one_waveform(
    source: str,
    path: str,
    event_id: str,
    station: str,
    component: str,
    *,
    cache_root: Path,
    overwrite: bool,
    compressed: bool,
    cache_index: dict[tuple[str, str, str, str, str], str],
    stats: _CacheStats,
) -> str:
    """Materialize one source/station/component waveform and return its path."""

    stats.source_references += 1
    key = (source, str(path), str(event_id), str(station), str(component))
    if key in cache_index:
        stats.in_memory_reuses += 1
        return cache_index[key]

    output_path = _cache_path(cache_root, source, path, event_id, station, component)
    if output_path.exists() and not overwrite:
        stats.reused_files += 1
        cache_index[key] = str(output_path)
        return str(output_path)

    side = _load_component_samples(path, station, component)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "data": np.asarray(side.data, dtype=np.float32),
        "channels": np.asarray([f"HN{component}"]),
        "station": np.asarray(str(station)),
        "sampling_rate": np.asarray(1.0 / float(side.dt), dtype=float),
        "starttime": np.asarray(""),
    }
    if compressed:
        np.savez_compressed(output_path, **payload)
    else:
        np.savez(output_path, **payload)
    stats.materialized_files += 1
    cache_index[key] = str(output_path)
    return str(output_path)


def _cache_path(cache_root: Path, source: str, path: str, event_id: str, station: str, component: str) -> Path:
    """Return a collision-resistant cache path for one waveform trace."""

    fingerprint = hashlib.sha1(f"{source}|{path}|{station}|{component}".encode("utf-8")).hexdigest()[:12]
    filename = f"{_safe_token(station)}_{_safe_token(component)}_{fingerprint}.npz"
    return cache_root / _safe_token(source) / _safe_token(event_id) / filename


def _cached_batches(batches: tuple[dict[str, Any], ...], *, batch_dir: Path) -> list[dict[str, Any]]:
    """Return batch metadata with output paths redirected to ``batch_dir``."""

    suffix = ".csv"
    if batches:
        suffix = Path(str(batches[0].get("output_path", ""))).suffix or suffix
    cached: list[dict[str, Any]] = []
    for batch_index, batch in enumerate(batches):
        updated = dict(batch)
        index = int(updated.get("batch_index", batch_index))
        updated["batch_index"] = index
        updated["output_path"] = str(batch_dir / f"metrics_batch_{index:04d}{suffix}")
        updated["status"] = "planned"
        cached.append(updated)
    return cached


def _safe_token(value: object) -> str:
    """Return a filesystem-safe path token."""

    text = str(value).strip() or "blank"
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text)[:120]


def _format_duration(seconds: float) -> str:
    """Return compact elapsed or ETA text."""

    total = max(0, int(round(seconds)))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{secs:02d}s"
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


__all__ = [
    "MetricWaveformCacheResult",
    "cache_metric_manifest_waveforms",
]
