"""Metric workflow manifests and batch execution.

Purpose
-------
This module writes resumable metric task manifests, runs individual batches,
and merges batch outputs.

Usage examples
--------------
Run configured metric work through the standard Step 3 output helper:
  ``from spatial_vtk.metrics import load_standard_metric_workflow_outputs``
  ``metric_outputs = load_standard_metric_workflow_outputs(cfg=cfg)``
  ``submission = metric_outputs.run_slurm_step_if_needed(context=context)``

Write a manifest and run the first batch only in advanced scripts that own
their task table directly:
  ``manifest = write_task_manifest(tasks, manifest_path, output_dir=batch_output_dir)``
  ``run_manifest_batch(manifest, batch_index=0)``
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Sequence

import pandas as pd

from spatial_vtk.io.compute_manifest import read_json, write_json


METRIC_TEXT_COLUMNS: tuple[str, ...] = (
    "task_id",
    "event_id",
    "station",
    "component",
    "model",
    "passband",
    "metric_group",
    "metric",
    "obs_qc_status",
    "obs_qc_reason",
    "syn_qc_status",
    "syn_qc_reason",
    "comparison_qc_status",
    "comparison_qc_reason",
    "obs_waveform_path",
    "syn_waveform_path",
)


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
    planning_metadata: dict[str, Any] | None = None

    def status_frame(self) -> pd.DataFrame:
        """Return a compact summary of manifest planning outputs."""

        output_paths = [Path(str(batch.get("output_path", ""))).expanduser() for batch in self.batches if batch.get("output_path")]
        output_dirs = sorted({str(path.parent) for path in output_paths})
        task_counts = [len(batch.get("task_indices", ())) for batch in self.batches]
        planning = dict(self.planning_metadata or {})
        return pd.DataFrame(
            [
                {
                    "name": "metric_manifest_path",
                    "artifact": "metric_manifest",
                    "artifact_label": "metric workflow manifest",
                    "artifact_role": "metric_manifest",
                    "status": "ready" if self.manifest_path.exists() else "missing",
                    "resolved_path": str(self.manifest_path),
                    "path": str(self.manifest_path),
                    "exists": self.manifest_path.exists(),
                    "manifest_path": str(self.manifest_path),
                    "manifest_exists": self.manifest_path.exists(),
                    "task_count": len(self.tasks),
                    "batch_count": len(self.batches),
                    "batch_output_dir": output_dirs[0] if len(output_dirs) == 1 else ("mixed" if output_dirs else ""),
                    "min_tasks_per_batch": min(task_counts) if task_counts else 0,
                    "max_tasks_per_batch": max(task_counts) if task_counts else 0,
                    "first_batch_output": str(output_paths[0]) if output_paths else "",
                    "last_batch_output": str(output_paths[-1]) if output_paths else "",
                    "qc_table": self.qc_table,
                    "planning_policy": planning.get("planning_policy", ""),
                    "use_qc": planning.get("use_qc", ""),
                    "require_passing_qc_pairs": planning.get("require_passing_qc_pairs", ""),
                    "include_qc_failed_tasks": planning.get("include_qc_failed_tasks", ""),
                    "require_source_overlap": planning.get("require_source_overlap", ""),
                    "source_overlap_scope": planning.get("source_overlap_scope", ""),
                    "output_mode": planning.get("output_mode", ""),
                }
            ]
        )


@dataclass(frozen=True)
class MetricManifestBatchStatus:
    """Completion status for the batch outputs listed in one metric manifest."""

    manifest_path: Path
    total_batches: int
    completed_batches: tuple[int, ...]
    missing_batches: tuple[int, ...]
    completed_outputs: tuple[Path, ...]
    missing_outputs: tuple[Path, ...]

    @property
    def completed_count(self) -> int:
        """Return the number of completed batch outputs."""

        return len(self.completed_batches)

    @property
    def missing_count(self) -> int:
        """Return the number of missing batch outputs."""

        return len(self.missing_batches)

    @property
    def all_complete(self) -> bool:
        """Return whether every manifest batch output exists."""

        return self.missing_count == 0

    @property
    def completion_fraction(self) -> float:
        """Return completed batch fraction in the closed interval [0, 1]."""

        if self.total_batches <= 0:
            return 1.0
        return float(self.completed_count) / float(self.total_batches)

    def status_frame(self) -> pd.DataFrame:
        """Return a one-row dataframe suitable for notebook display."""

        return pd.DataFrame(
            [
                {
                    "name": "metric_batch_outputs",
                    "artifact": "metric_batch_outputs",
                    "artifact_label": "metric batch outputs",
                    "artifact_role": "metric_batch_outputs",
                    "status": "complete" if self.all_complete else "incomplete",
                    "resolved_path": str(self.manifest_path),
                    "path": str(self.manifest_path),
                    "exists": self.manifest_path.exists(),
                    "manifest": str(self.manifest_path),
                    "total_batches": int(self.total_batches),
                    "completed_batches": int(self.completed_count),
                    "missing_batches": int(self.missing_count),
                    "completion_percent": round(100.0 * self.completion_fraction, 3),
                    "all_complete": bool(self.all_complete),
                }
            ]
        )

    def to_dict(self, *, missing_limit: int | None = 20) -> dict[str, Any]:
        """Return JSON/YAML-friendly status details."""

        limit = None if missing_limit is None or int(missing_limit) < 0 else int(missing_limit)
        missing_outputs = [str(path) for path in self.missing_outputs]
        if limit is not None:
            missing_outputs = missing_outputs[:limit]
        missing_batch_indices = list(self.missing_batches)
        if limit is not None:
            missing_batch_indices = missing_batch_indices[:limit]
        return {
            "manifest": str(self.manifest_path),
            "total_batches": int(self.total_batches),
            "completed_batches": int(self.completed_count),
            "missing_batches": int(self.missing_count),
            "completion_percent": round(100.0 * self.completion_fraction, 3),
            "all_complete": bool(self.all_complete),
            "missing_batch_indices": missing_batch_indices,
            "missing_outputs": missing_outputs,
            "missing_outputs_truncated": bool(limit is not None and len(self.missing_outputs) > limit),
        }


@dataclass(frozen=True)
class MetricSlurmSubmissionReadiness:
    """Readiness decision for metric Slurm array submission.

    Standard Step 3 notebooks normally get this status through
    ``load_standard_metric_workflow_outputs(...).run_slurm_step_if_needed(...)``.
    Custom orchestration can use this object directly when it already owns the
    manifest path, batch-status calculation, and notebook/slurm execution
    control. The object exposes the small readiness interface expected by the
    package notebook runner: ``should_run``, ``reason``, ``message``, and
    ``status_frame()``.
    """

    batch_status: MetricManifestBatchStatus
    should_run: bool
    reason: str
    message: str

    def status_frame(self) -> pd.DataFrame:
        """Return a one-row dataframe suitable for notebook display."""

        frame = self.batch_status.status_frame().copy()
        frame["should_submit"] = bool(self.should_run)
        frame["reason"] = self.reason
        frame["message"] = self.message
        return frame


def metric_slurm_submission_readiness(
    batch_status: MetricManifestBatchStatus | MetricWorkflowManifest | str | Path,
    *,
    overwrite: bool = False,
) -> MetricSlurmSubmissionReadiness:
    """Return whether the metric Slurm array should be written/submitted.

    Parameters
    ----------
    batch_status
        Batch completion status or a metric manifest path/object from which the
        status can be calculated.
    overwrite
        Whether existing batch outputs should be recalculated.

    Returns
    -------
    MetricSlurmSubmissionReadiness
        Readiness object for callers that directly manage manifest status.
        Routine notebooks should use the standard metric workflow result
        object's ``run_slurm_step_if_needed(...)`` method, which calls this
        helper internally.
    """

    status = (
        batch_status
        if isinstance(batch_status, MetricManifestBatchStatus)
        else metric_manifest_batch_status(batch_status)
    )
    if bool(overwrite):
        return MetricSlurmSubmissionReadiness(
            batch_status=status,
            should_run=True,
            reason="overwrite",
            message=(
                "Overwrite requested; writing/submitting metric Slurm script "
                f"for {status.total_batches} batch(es)."
            ),
        )
    if not status.all_complete:
        return MetricSlurmSubmissionReadiness(
            batch_status=status,
            should_run=True,
            reason="incomplete_batches",
            message=(
                "Metric batches are incomplete; writing/submitting metric Slurm "
                f"script for {status.missing_count} missing batch output(s)."
            ),
        )
    return MetricSlurmSubmissionReadiness(
        batch_status=status,
        should_run=False,
        reason="current",
        message="All metric batch outputs already exist; skipping metric Slurm submission.",
    )


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
    planning_metadata: dict[str, Any] | None = None,
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
    planning_metadata
        Optional JSON-serializable metadata describing the planning filters
        used to create the manifest, such as QC-passing-pair filtering and
        observed/synthetic overlap scope.
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
    ordered_tasks = _sort_tasks_for_cache(tasks)
    chunks = chunk_tasks(ordered_tasks, chunk_size=batch_size)
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
        "planning_metadata": dict(planning_metadata or {}),
        "tasks": [task.to_dict() for task in ordered_tasks],
        "batches": batches,
    }
    write_json(manifest, payload)
    return MetricWorkflowManifest(
        manifest_path=manifest,
        tasks=tuple(ordered_tasks),
        batches=tuple(batches),
        qc_table=str(qc_table or ""),
        planning_metadata=dict(planning_metadata or {}),
    )


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
    from spatial_vtk.metrics.workflow.tasks import MetricWorkflowTask

    tasks = tuple(MetricWorkflowTask.from_dict(item) for item in payload.get("tasks", []))
    batches = tuple(dict(item) for item in payload.get("batches", []))
    return MetricWorkflowManifest(
        manifest_path=manifest_path,
        tasks=tasks,
        batches=batches,
        qc_table=str(payload.get("qc_table", "")),
        planning_metadata=dict(payload.get("planning_metadata") or {}),
    )


def _read_manifest_batch_payload(path: str | Path) -> tuple[Path, tuple[dict[str, Any], ...]]:
    """Read only manifest batch metadata without deserializing metric tasks."""

    manifest_path = Path(path).expanduser()
    payload = read_json(manifest_path)
    return manifest_path, tuple(dict(item) for item in payload.get("batches", []))


def metric_manifest_batch_status(manifest: MetricWorkflowManifest | str | Path) -> MetricManifestBatchStatus:
    """Return completion status for all batch outputs listed in a manifest."""

    if isinstance(manifest, MetricWorkflowManifest):
        manifest_path = manifest.manifest_path
        batches = manifest.batches
    else:
        manifest_path, batches = _read_manifest_batch_payload(manifest)
    completed_batches: list[int] = []
    missing_batches: list[int] = []
    completed_outputs: list[Path] = []
    missing_outputs: list[Path] = []
    for batch in batches:
        batch_index = int(batch["batch_index"])
        output_path = Path(batch["output_path"]).expanduser()
        if output_path.exists():
            completed_batches.append(batch_index)
            completed_outputs.append(output_path)
        else:
            missing_batches.append(batch_index)
            missing_outputs.append(output_path)
    return MetricManifestBatchStatus(
        manifest_path=manifest_path,
        total_batches=len(batches),
        completed_batches=tuple(completed_batches),
        missing_batches=tuple(missing_batches),
        completed_outputs=tuple(completed_outputs),
        missing_outputs=tuple(missing_outputs),
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
    batch_number = int(batch["batch_index"]) + 1
    total_batches = len(parsed.batches)
    completed_before = _completed_batch_count(parsed)
    _print_batch_progress(
        parsed,
        batch_number=batch_number,
        total_batches=total_batches,
        completed_batches=completed_before,
        message=f"starting batch {batch_number}/{total_batches}",
    )
    if output_path.exists() and not overwrite:
        _print_batch_progress(
            parsed,
            batch_number=batch_number,
            total_batches=total_batches,
            completed_batches=completed_before,
            message=f"batch output already exists; skipping {output_path}",
        )
        return output_path
    selected_tasks = [parsed.tasks[int(index)] for index in batch["task_indices"]]
    start = time.monotonic()
    timing: dict[str, float] = {}
    print(
        f"Metric batch {batch_number}/{total_batches}: running {len(selected_tasks)} task(s) -> {output_path}",
        flush=True,
    )
    from spatial_vtk.metrics.workflow.run import run_metric_tasks, write_metric_rows

    rows = run_metric_tasks(
        selected_tasks,
        qc_table=parsed.qc_table or None,
        progress_label=f"Metric batch {batch_number}/{total_batches}",
        timing=timing,
    )
    write_start = time.monotonic()
    written = write_metric_rows(rows, output_path)
    timing["write_s"] = timing.get("write_s", 0.0) + (time.monotonic() - write_start)
    batch_elapsed = time.monotonic() - start
    print(_format_timing_summary(f"Metric batch {batch_number}/{total_batches}", timing), flush=True)
    completed_after = _completed_batch_count(parsed)
    _print_batch_progress(
        parsed,
        batch_number=batch_number,
        total_batches=total_batches,
        completed_batches=completed_after,
        message=(
            f"finished batch {batch_number}/{total_batches} "
            f"({len(rows)} metric row(s), batch elapsed {_format_duration(batch_elapsed)})"
        ),
    )
    return written


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
    resolved_output = _resolve_merge_output_path(output_path)
    paths: list[Path] = []
    missing: list[str] = []
    for batch in parsed.batches:
        path = Path(batch["output_path"]).expanduser()
        if not path.exists():
            missing.append(str(path))
            continue
        paths.append(path)
    if missing and require_all:
        raise FileNotFoundError(f"Missing metric batch outputs: {missing}")
    if not paths:
        from spatial_vtk.io.tables import write_table

        return write_table(pd.DataFrame(columns=METRIC_TEXT_COLUMNS), resolved_output, index=False)
    return _write_merged_batch_tables(paths, resolved_output)


def _resolve_merge_output_path(output_path: str | Path) -> Path:
    """Return a concrete metric merge output file path."""

    raw_path = os.fspath(output_path)
    path = Path(raw_path).expanduser()
    if path.exists() and path.is_dir():
        return path / "metric_rows.parquet"
    if raw_path.endswith(("/", os.sep)):
        return path / "metric_rows.parquet"
    return path


def _write_merged_batch_tables(paths: Sequence[Path], output_path: Path) -> Path:
    """Write existing metric batch tables to one output without holding all rows."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return _write_merged_batch_tables_parquet(paths, output_path)
    return _write_merged_batch_tables_csv(paths, output_path)


def _write_merged_batch_tables_csv(paths: Sequence[Path], output_path: Path) -> Path:
    """Stream existing batch tables into one CSV output."""

    columns = _merged_batch_columns(paths)
    tmp_path = _temporary_output_path(output_path)
    wrote_header = False
    try:
        for path in paths:
            for frame in _iter_table_frames(path):
                normalized = _normalize_merged_batch_frame(frame, columns)
                normalized.to_csv(tmp_path, mode="a", header=not wrote_header, index=False)
                wrote_header = True
        if not wrote_header:
            pd.DataFrame(columns=columns).to_csv(tmp_path, index=False)
        tmp_path.replace(output_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return output_path


def _write_merged_batch_tables_parquet(paths: Sequence[Path], output_path: Path) -> Path:
    """Stream existing batch tables into one Parquet output."""

    import pyarrow as pa
    import pyarrow.parquet as pq

    columns = _merged_batch_columns(paths)
    schema_frame = _merged_batch_schema_frame(paths, columns)
    tmp_path = _temporary_output_path(output_path)
    writer: pq.ParquetWriter | None = None
    try:
        if schema_frame.empty:
            pd.DataFrame(columns=columns).to_parquet(tmp_path, index=False)
            tmp_path.replace(output_path)
            return output_path
        schema = pa.Table.from_pandas(schema_frame, preserve_index=False).schema
        writer = pq.ParquetWriter(tmp_path, schema)
        for path in paths:
            for frame in _iter_table_frames(path):
                normalized = _normalize_merged_batch_frame(frame, columns)
                if normalized.empty:
                    continue
                table = pa.Table.from_pandas(normalized, schema=schema, preserve_index=False)
                writer.write_table(table)
        writer.close()
        writer = None
        tmp_path.replace(output_path)
    except Exception:
        if writer is not None:
            writer.close()
        tmp_path.unlink(missing_ok=True)
        raise
    return output_path


def _temporary_output_path(output_path: Path) -> Path:
    """Return a same-directory temporary path for one output file."""

    handle = tempfile.NamedTemporaryFile(
        delete=False,
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
    )
    tmp_path = Path(handle.name)
    handle.close()
    return tmp_path


def _merged_batch_columns(paths: Sequence[Path]) -> list[str]:
    """Return the union of metric batch columns without loading full tables."""

    columns: list[str] = []
    seen: set[str] = set()
    for path in paths:
        for column in _table_columns(path):
            if column not in seen:
                columns.append(column)
                seen.add(column)
    return columns


def _table_columns(path: Path) -> list[str]:
    """Return column names from one CSV or Parquet table."""

    from spatial_vtk.io.tables import table_columns

    return table_columns(path)


def _merged_batch_schema_frame(paths: Sequence[Path], columns: Sequence[str], *, max_rows_per_batch: int = 100) -> pd.DataFrame:
    """Return a bounded sample used to infer a stable merged Parquet schema."""

    records: list[dict[str, Any]] = []
    for path in paths:
        preview = _read_table_preview(path, max_rows=max_rows_per_batch)
        if preview.empty:
            continue
        normalized = _normalize_merged_batch_frame(preview, columns)
        records.extend(normalized.to_dict("records"))
    if not records:
        return pd.DataFrame(columns=list(columns))
    return pd.DataFrame.from_records(records, columns=list(columns))


def _read_table_preview(path: Path, *, max_rows: int) -> pd.DataFrame:
    """Read a bounded preview from one CSV or Parquet batch table."""

    if path.suffix.lower() in {".parquet", ".pq"}:
        try:
            import pyarrow.parquet as pq

            parquet_file = pq.ParquetFile(path)
            records: list[dict[str, Any]] = []
            remaining = max(0, int(max_rows))
            for batch in parquet_file.iter_batches(batch_size=min(max(remaining, 1), 100_000)):
                frame = batch.to_pandas()
                bounded = frame.head(remaining)
                if not bounded.empty:
                    records.extend(bounded.to_dict("records"))
                remaining -= len(bounded)
                if remaining <= 0:
                    break
            if not records:
                return pd.DataFrame(columns=parquet_file.schema.names)
            return pd.DataFrame.from_records(records, columns=parquet_file.schema.names)
        except ImportError as exc:
            raise RuntimeError(
                f"Could not read a bounded metric batch parquet preview for {path}: pyarrow is required. "
                "Install the package dependencies or rewrite metric batches as CSV before merging."
            ) from exc
    text_columns = _csv_text_columns(path)
    dtype = {column: str for column in text_columns}
    return pd.read_csv(path, dtype=dtype, nrows=max_rows, low_memory=False)


def _iter_table_frames(path: Path, *, chunksize: int = 100_000):
    """Yield table frames from one metric batch without full-file reads."""

    size = max(int(chunksize), 1)
    if path.suffix.lower() in {".parquet", ".pq"}:
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise RuntimeError(
                f"Could not stream metric batch parquet table for {path}: pyarrow is required. "
                "Install the package dependencies or rewrite metric batches as CSV before merging."
            ) from exc
        parquet_file = pq.ParquetFile(path)
        for batch in parquet_file.iter_batches(batch_size=size):
            yield batch.to_pandas()
        return
    text_columns = _csv_text_columns(path)
    dtype = {column: str for column in text_columns}
    yield from pd.read_csv(path, dtype=dtype, chunksize=size, low_memory=False)


def _normalize_merged_batch_frame(df: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    """Return one batch frame with stable text columns and merged-column order."""

    out = df.copy()
    for column in METRIC_TEXT_COLUMNS:
        if column in out.columns:
            out[column] = out[column].map(_metric_text_value)
    for column in columns:
        if column not in out.columns:
            out[column] = pd.NA
    return out.loc[:, list(columns)]


def _metric_text_value(value: Any) -> str:
    """Return one metric identifier/status/path value as text."""

    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value)


def _batch_by_index(manifest: MetricWorkflowManifest, batch_index: int) -> dict[str, Any]:
    """Return one batch dictionary by index."""

    for batch in manifest.batches:
        if int(batch["batch_index"]) == int(batch_index):
            return batch
    raise IndexError(f"Batch index {batch_index} is not present in manifest {manifest.manifest_path}.")


def _sort_tasks_for_cache(tasks: list[MetricWorkflowTask]) -> list[MetricWorkflowTask]:
    """Return tasks ordered to maximize per-process waveform cache reuse."""

    indexed = list(enumerate(tasks))
    indexed.sort(key=lambda item: (*_task_cache_sort_key(item[1]), item[0]))
    return [task for _, task in indexed]


def _task_cache_sort_key(task: MetricWorkflowTask) -> tuple[Any, ...]:
    """Return a stable key that keeps reusable waveform loads adjacent."""

    return (
        str(task.obs_waveform_path or ""),
        str(task.syn_waveform_path or ""),
        str(task.station or "").strip().upper(),
        str(task.component or "").strip().upper(),
        str(task.event_id or ""),
        str(task.model or ""),
        _none_last_float(task.period_min_s),
        _none_last_float(task.period_max_s),
        str(task.passband or ""),
    )


def _none_last_float(value: object) -> tuple[int, float]:
    """Sort finite numeric values before missing values."""

    try:
        number = float(value)
    except Exception:
        return (1, 0.0)
    return (0, number) if pd.notna(number) else (1, 0.0)


def _format_timing_summary(label: str, timing: dict[str, float]) -> str:
    """Format batch timing totals for Slurm stdout."""

    ordered = [
        ("qc_lookup_s", "qc_lookup"),
        ("task_total_s", "tasks"),
        ("load_s", "load"),
        ("spectral_qc_s", "spectral_qc"),
        ("trace_metric_s", "trace_metrics"),
        ("spectral_metric_s", "spectral_metrics"),
        ("pair_metric_s", "pair_metrics"),
        ("dataframe_s", "dataframe"),
        ("write_s", "write"),
    ]
    parts = [f"{name} {_format_duration(timing.get(key, 0.0))}" for key, name in ordered if timing.get(key, 0.0) > 0.0]
    return f"{label} timing: " + (", ".join(parts) if parts else "no timing recorded")


def _read_table(path: str | Path) -> pd.DataFrame:
    """Read one CSV or Parquet table."""

    table_path = Path(path).expanduser()
    if table_path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(table_path)
    text_columns = _csv_text_columns(table_path)
    dtype = {column: str for column in text_columns}
    return pd.read_csv(table_path, dtype=dtype, low_memory=False)


def _csv_text_columns(path: Path) -> list[str]:
    """Return known metric text columns present in a CSV header."""

    try:
        from spatial_vtk.io.tables import table_columns

        columns = table_columns(path)
    except pd.errors.EmptyDataError:
        return []
    present = set(columns)
    return [column for column in METRIC_TEXT_COLUMNS if column in present]


def _completed_batch_count(manifest: MetricWorkflowManifest) -> int:
    """Count manifest batch outputs that already exist."""

    return metric_manifest_batch_status(manifest).completed_count


def _workflow_elapsed_seconds(manifest: MetricWorkflowManifest) -> float:
    """Estimate workflow wall time from a Slurm start stamp or manifest mtime."""

    start_time = os.environ.get("SVTK_METRIC_WORKFLOW_START_TIME", "").strip()
    if start_time:
        try:
            return max(0.0, time.time() - float(start_time))
        except ValueError:
            pass

    try:
        return max(0.0, time.time() - manifest.manifest_path.expanduser().stat().st_mtime)
    except OSError:
        return 0.0


def _print_batch_progress(
    manifest: MetricWorkflowManifest,
    *,
    batch_number: int,
    total_batches: int,
    completed_batches: int,
    message: str,
) -> None:
    """Print one metric workflow progress line with elapsed time and ETA."""

    elapsed = _workflow_elapsed_seconds(manifest)
    remaining = max(total_batches - completed_batches, 0)
    eta = ""
    if completed_batches > 0 and elapsed > 0:
        seconds_per_batch = elapsed / completed_batches
        eta = f", ETA {_format_duration(seconds_per_batch * remaining)}"
    print(
        f"Metric workflow: {message}; {completed_batches}/{total_batches} batch(es) complete; "
        f"elapsed {_format_duration(elapsed)}{eta}",
        flush=True,
    )


def _format_duration(seconds: float) -> str:
    """Format elapsed seconds as compact human-readable time."""

    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{secs:02d}s"
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the batch-execution CLI parser."""

    parser = argparse.ArgumentParser(description="Run one Spatial-VTK metric manifest batch.")
    parser.add_argument(
        "--metric-manifest",
        "--manifest",
        dest="metric_manifest",
        required=True,
        help="Metric workflow manifest JSON. Prefer --metric-manifest; --manifest is a legacy alias.",
    )
    parser.add_argument("--batch-index", type=int, required=True, help="Batch index to run.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing batch output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one manifest batch from CLI arguments."""

    args = build_arg_parser().parse_args(argv)
    run_manifest_batch(args.metric_manifest, batch_index=args.batch_index, overwrite=args.overwrite)
    return 0


__all__ = [
    "MANIFEST_VERSION",
    "MetricManifestBatchStatus",
    "MetricSlurmSubmissionReadiness",
    "MetricWorkflowManifest",
    "chunk_tasks",
    "merge_batch_outputs",
    "metric_manifest_batch_status",
    "metric_slurm_submission_readiness",
    "read_task_manifest",
    "run_manifest_batch",
    "write_task_manifest",
    "build_arg_parser",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
