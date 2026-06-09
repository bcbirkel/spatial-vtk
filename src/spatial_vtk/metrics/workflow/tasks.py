"""Metric workflow task planning.

Purpose
-------
This module converts normalized observed/synthetic waveform inventories into
explicit metric tasks that can be executed locally, in batches, or through a
generic SLURM array job.

Usage examples
--------------
Build tasks from inventories:
  ``tasks = plan_metric_tasks(obs_inventory, syn_inventory, plan=metric_plan)``
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import dataclasses
from pathlib import Path
from typing import Any
import hashlib

import numpy as np
import pandas as pd

from spatial_vtk.config.metric_catalog import DEFAULT_METRICS_BY_GROUP, LEGACY_METRIC_ALIASES, metric_group_for, resolve_metric_names
from spatial_vtk.io.metric_inputs import normalize_metric_waveform_inventory
from spatial_vtk.io.plans import MetricPlan


@dataclass(frozen=True)
class MetricWorkflowTask:
    """One file-based metric calculation task.

    Parameters
    ----------
    task_id
        Stable task identifier.
    event_id, station, component, model, passband
        Calculation identity fields.
    obs_waveform_path, syn_waveform_path
        Optional observed and synthetic waveform paths.
    dt
        Sample spacing in seconds.
    period_min_s, period_max_s
        Optional passband bounds in period seconds.
    metrics
        Metric names to calculate.
    transforms
        Requested observed/synthetic transforms.
    output_mode
        ``observed``, ``synthetic``, ``residual``, ``gof``, or ``full``.
    spectral_periods_s
        Requested PSA/FAS periods.
    synthetic_max_frequency_hz
        Optional maximum valid synthetic frequency.
    waveform_lowpass_hz
        Optional project-configured lowpass cutoff applied before passband
        filtering and metric calculations.
    waveform_resample_hz
        Optional target sample rate applied before passband filtering and
        metric calculations.
    use_qc
        Whether QC lookup rows should gate side values and comparisons.

    Returns
    -------
    MetricWorkflowTask
        Immutable workflow task.
    """

    task_id: str
    event_id: str
    station: str
    component: str
    model: str = ""
    passband: str = ""
    obs_waveform_path: str = ""
    syn_waveform_path: str = ""
    dt: float = np.nan
    period_min_s: float | None = None
    period_max_s: float | None = None
    metrics: tuple[str, ...] = ("PGA",)
    transforms: tuple[str, ...] = ("log2_residual",)
    output_mode: str = "full"
    spectral_periods_s: tuple[float, ...] = ()
    synthetic_max_frequency_hz: float | None = None
    waveform_lowpass_hz: float | None = None
    waveform_resample_hz: float | None = None
    waveform_filter_order: int | None = None
    spectral_relative_amplitude_threshold: float = 0.25
    spectral_min_cycles_in_record: float = 3.0
    disable_spectral_relative_amplitude_qc: bool = False
    use_qc: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Return this task as a JSON/CSV-safe dictionary.

        Parameters
        ----------
        self
            Workflow task.

        Returns
        -------
        dict[str, object]
            Serialized task payload.
        """

        payload = asdict(self)
        payload["metrics"] = ",".join(self.metrics)
        payload["transforms"] = ",".join(self.transforms)
        payload["spectral_periods_s"] = ",".join(f"{float(period):g}" for period in self.spectral_periods_s)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MetricWorkflowTask":
        """Build one task from a serialized dictionary.

        Parameters
        ----------
        payload
            Serialized task payload.

        Returns
        -------
        MetricWorkflowTask
            Reconstructed task.
        """

        allowed_fields = {field.name for field in dataclasses.fields(cls)}
        data = {key: value for key, value in dict(payload).items() if key in allowed_fields}
        data["metrics"] = _tuple_from_serialized(data.get("metrics"))
        data["transforms"] = _tuple_from_serialized(data.get("transforms"))
        data["spectral_periods_s"] = tuple(float(item) for item in _tuple_from_serialized(data.get("spectral_periods_s")))
        for column in ("dt", "period_min_s", "period_max_s", "synthetic_max_frequency_hz", "waveform_lowpass_hz", "waveform_resample_hz", "spectral_relative_amplitude_threshold", "spectral_min_cycles_in_record"):
            data[column] = _optional_float(data.get(column))
        data["waveform_filter_order"] = _optional_int(data.get("waveform_filter_order"))
        for column in ("disable_spectral_relative_amplitude_qc", "use_qc"):
            data[column] = _bool_value(data.get(column))
        return cls(**data)


def plan_metric_tasks(
    observed_inventory: pd.DataFrame | str | Path | None,
    synthetic_inventory: pd.DataFrame | str | Path | None = None,
    *,
    plan: MetricPlan,
    use_qc: bool = True,
    spectral_relative_amplitude_threshold: float = 0.25,
    spectral_min_cycles_in_record: float = 3.0,
    disable_spectral_relative_amplitude_qc: bool = False,
) -> list[MetricWorkflowTask]:
    """Plan metric workflow tasks from observed/synthetic inventories.

    Parameters
    ----------
    observed_inventory
        Observed waveform inventory or path. Required unless
        ``plan.output_mode == "synthetic"``.
    synthetic_inventory
        Synthetic waveform inventory or path. Required for pair modes and
        synthetic-only mode.
    plan
        Resolved metric plan.
    use_qc
        Whether tasks should honor QC tables during execution.
    spectral_relative_amplitude_threshold
        Relative amplitude threshold copied into each task for spectral QC.
    spectral_min_cycles_in_record
        Minimum usable cycles copied into each task for spectral QC.
    disable_spectral_relative_amplitude_qc
        Whether each task should skip relative-amplitude spectral QC.

    Returns
    -------
    list[MetricWorkflowTask]
        Planned workflow tasks.
    """

    output_mode = str(plan.output_mode or "full").lower()
    if output_mode not in {"observed", "synthetic", "residual", "gof", "full"}:
        raise ValueError("plan.output_mode must be observed, synthetic, residual, gof, or full.")
    obs = _normalize_inventory_or_empty(observed_inventory, source="observed") if observed_inventory is not None else pd.DataFrame()
    syn = _normalize_inventory_or_empty(
        synthetic_inventory,
        source="synthetic",
        synthetic_max_frequency_hz=plan.synthetic_max_frequency_hz,
    ) if synthetic_inventory is not None else pd.DataFrame()
    metrics = resolve_metric_names(plan.metrics, plan.metric_groups)
    passbands = plan.passbands or ((None, None),)
    tasks: list[MetricWorkflowTask] = []

    if output_mode == "observed":
        source_rows = _filter_inventory(obs, components=plan.components, models=())
        for _, obs_row in source_rows.iterrows():
            for period_min_s, period_max_s in passbands:
                tasks.append(_task_from_rows(obs_row, None, plan, metrics, period_min_s, period_max_s, use_qc, spectral_relative_amplitude_threshold, spectral_min_cycles_in_record, disable_spectral_relative_amplitude_qc))
        return tasks

    if output_mode == "synthetic":
        source_rows = _filter_inventory(syn, components=plan.components, models=plan.models)
        for _, syn_row in source_rows.iterrows():
            for period_min_s, period_max_s in passbands:
                tasks.append(_task_from_rows(None, syn_row, plan, metrics, period_min_s, period_max_s, use_qc, spectral_relative_amplitude_threshold, spectral_min_cycles_in_record, disable_spectral_relative_amplitude_qc))
        return tasks

    if obs.empty or syn.empty:
        raise ValueError("Observed and synthetic inventories are both required for residual, gof, and full metric modes.")
    obs_rows = _filter_inventory(obs, components=plan.components, models=())
    syn_rows = _filter_inventory(syn, components=plan.components, models=plan.models)
    syn_index = _synthetic_index(syn_rows)
    for _, obs_row in obs_rows.iterrows():
        candidates = syn_index.get((str(obs_row["event_id"]), str(obs_row["station"]), str(obs_row["component"])), [])
        for syn_row in candidates:
            for period_min_s, period_max_s in passbands:
                tasks.append(_task_from_rows(obs_row, syn_row, plan, metrics, period_min_s, period_max_s, use_qc, spectral_relative_amplitude_threshold, spectral_min_cycles_in_record, disable_spectral_relative_amplitude_qc))
    return tasks


def tasks_to_frame(tasks: list[MetricWorkflowTask]) -> pd.DataFrame:
    """Convert tasks to a dataframe.

    Parameters
    ----------
    tasks
        Workflow tasks.

    Returns
    -------
    pandas.DataFrame
        Serialized task table.
    """

    return pd.DataFrame([task.to_dict() for task in tasks])


def tasks_from_frame(table: pd.DataFrame | str | Path) -> list[MetricWorkflowTask]:
    """Read tasks from a dataframe or CSV/parquet path.

    Parameters
    ----------
    table
        Serialized task table.

    Returns
    -------
    list[MetricWorkflowTask]
        Reconstructed tasks.
    """

    df = _read_table(table)
    return [MetricWorkflowTask.from_dict(row.dropna().to_dict()) for _, row in df.iterrows()]


def summarize_metric_tasks(
    tasks: list[MetricWorkflowTask] | pd.DataFrame | str | Path,
    *,
    seconds_per_task: float = 60.0,
    memory_gb_per_task: float = 2.0,
    cpus_per_task: int = 1,
    parallel_tasks: int | None = None,
) -> pd.DataFrame:
    """Summarize metric task count and approximate resource needs.

    Parameters
    ----------
    tasks
        Metric task list, serialized task dataframe, or task table path.
    seconds_per_task
        Approximate runtime for one task in seconds.
    memory_gb_per_task
        Approximate memory required by one task in GB.
    cpus_per_task
        CPU cores requested per task.
    parallel_tasks
        Optional number of tasks expected to run at the same time.

    Returns
    -------
    pandas.DataFrame
        Compact estimate table with human-readable values and notes.
    """

    if isinstance(tasks, list):
        task_table = tasks_to_frame(tasks)
    else:
        task_table = _read_table(tasks)
    task_count = len(task_table)
    seconds_per_task = max(float(seconds_per_task), 0.0)
    memory_gb_per_task = max(float(memory_gb_per_task), 0.0)
    cpus_per_task = max(int(cpus_per_task), 1)
    parallel_count = max(int(parallel_tasks), 1) if parallel_tasks is not None else None
    metric_evaluations = _estimate_metric_evaluations(task_table)
    serial_cpu_hours = task_count * seconds_per_task * cpus_per_task / 3600.0

    rows = [
        {
            "Estimate": "Metric tasks",
            "Value": f"{task_count:,}",
            "Notes": "One task is one event-station-component-model-passband calculation unit.",
        },
        {
            "Estimate": "Approximate metric evaluations",
            "Value": f"{metric_evaluations:,}",
            "Notes": "Task count multiplied by the requested metrics per task.",
        },
        {
            "Estimate": "Unique events",
            "Value": _unique_count_text(task_table, "event_id"),
            "Notes": "",
        },
        {
            "Estimate": "Unique stations",
            "Value": _unique_count_text(task_table, "station"),
            "Notes": "",
        },
        {
            "Estimate": "Components",
            "Value": _unique_values_text(task_table, "component"),
            "Notes": "",
        },
        {
            "Estimate": "Models",
            "Value": _unique_values_text(task_table, "model"),
            "Notes": "",
        },
        {
            "Estimate": "Passbands",
            "Value": _unique_values_text(task_table, "passband", fallback_column="band"),
            "Notes": "Period-band labels, for example 1-2 sec.",
        },
        {
            "Estimate": "Approximate CPU-hours",
            "Value": _format_hours(serial_cpu_hours),
            "Notes": f"Uses {seconds_per_task:g} seconds/task and {cpus_per_task} CPU/task.",
        },
        {
            "Estimate": "Memory per task",
            "Value": f"{memory_gb_per_task:g} GB",
            "Notes": "Planning estimate; benchmark a small batch for final allocations.",
        },
    ]
    if parallel_count is not None:
        wall_seconds = task_count * seconds_per_task / parallel_count if parallel_count else 0.0
        rows.extend(
            [
                {
                    "Estimate": f"Wall time at {parallel_count} parallel tasks",
                    "Value": _format_duration(wall_seconds),
                    "Notes": "Approximate elapsed time if every task takes the same time.",
                },
                {
                    "Estimate": f"Peak memory at {parallel_count} parallel tasks",
                    "Value": f"{memory_gb_per_task * parallel_count:g} GB",
                    "Notes": "Memory per task multiplied by concurrent tasks.",
                },
            ]
        )
    return pd.DataFrame(rows)


def _task_from_rows(
    obs_row: pd.Series | None,
    syn_row: pd.Series | None,
    plan: MetricPlan,
    metrics: tuple[str, ...],
    period_min_s: float | None,
    period_max_s: float | None,
    use_qc: bool,
    spectral_relative_amplitude_threshold: float,
    spectral_min_cycles_in_record: float,
    disable_spectral_relative_amplitude_qc: bool,
) -> MetricWorkflowTask:
    """Build one workflow task from observed/synthetic inventory rows."""

    row = obs_row if obs_row is not None else syn_row
    if row is None:
        raise ValueError("At least one observed or synthetic row is required.")
    dt = _resolve_dt(obs_row, syn_row)
    model = str(syn_row.get("model", "") if syn_row is not None else row.get("model", ""))
    payload = {
        "event_id": str(row["event_id"]),
        "station": str(row["station"]).upper(),
        "component": str(row["component"]).upper(),
        "model": model,
        "passband": _passband_label(period_min_s, period_max_s),
        "obs_waveform_path": str(obs_row.get("waveform_path", "")) if obs_row is not None else "",
        "syn_waveform_path": str(syn_row.get("waveform_path", "")) if syn_row is not None else "",
        "dt": dt,
        "period_min_s": period_min_s,
        "period_max_s": period_max_s,
        "metrics": metrics,
        "transforms": plan.transforms,
        "output_mode": str(plan.output_mode or "full"),
        "spectral_periods_s": plan.spectral_periods_s,
        "synthetic_max_frequency_hz": _resolve_synthetic_max_frequency(syn_row, plan.synthetic_max_frequency_hz),
        "waveform_lowpass_hz": plan.waveform_lowpass_hz,
        "waveform_resample_hz": plan.waveform_resample_hz,
        "waveform_filter_order": plan.waveform_filter_order,
        "spectral_relative_amplitude_threshold": float(spectral_relative_amplitude_threshold),
        "spectral_min_cycles_in_record": float(spectral_min_cycles_in_record),
        "disable_spectral_relative_amplitude_qc": bool(disable_spectral_relative_amplitude_qc),
        "use_qc": bool(use_qc),
    }
    task_id = _task_id(payload)
    return MetricWorkflowTask(task_id=task_id, **payload)


def _filter_inventory(df: pd.DataFrame, *, components: tuple[str, ...], models: tuple[str, ...]) -> pd.DataFrame:
    """Filter inventory rows by component and model."""

    out = df.copy()
    if components:
        out = out[out["component"].isin([str(component).upper() for component in components])]
    if models and "model" in out.columns:
        out = out[out["model"].isin([str(model) for model in models])]
    return out.reset_index(drop=True)


def _synthetic_index(df: pd.DataFrame) -> dict[tuple[str, str, str], list[pd.Series]]:
    """Index synthetic rows by event, station, and component."""

    lookup: dict[tuple[str, str, str], list[pd.Series]] = {}
    for _, row in df.iterrows():
        key = (str(row["event_id"]), str(row["station"]).upper(), str(row["component"]).upper())
        lookup.setdefault(key, []).append(row)
    return lookup


def _normalize_inventory_or_empty(table: pd.DataFrame | str | Path, *, source: str, synthetic_max_frequency_hz: float | None = None) -> pd.DataFrame:
    """Normalize one inventory table."""

    return normalize_metric_waveform_inventory(table, source=source, synthetic_max_frequency_hz=synthetic_max_frequency_hz)


def _resolve_dt(obs_row: pd.Series | None, syn_row: pd.Series | None) -> float:
    """Resolve sample spacing from task inventory rows."""

    for row in (obs_row, syn_row):
        if row is None:
            continue
        dt = _optional_float(row.get("dt"))
        if dt is not None and dt > 0.0:
            return float(dt)
        sampling_rate = _optional_float(row.get("sampling_rate"))
        if sampling_rate is not None and sampling_rate > 0.0:
            return 1.0 / float(sampling_rate)
    raise ValueError("Task rows must provide dt or sampling_rate.")


def _resolve_synthetic_max_frequency(syn_row: pd.Series | None, plan_value: float | None) -> float | None:
    """Resolve synthetic maximum frequency from row or plan."""

    row_value = _optional_float(syn_row.get("synthetic_max_frequency_hz")) if syn_row is not None else None
    return row_value if row_value is not None else plan_value


def _passband_label(period_min_s: float | None, period_max_s: float | None) -> str:
    """Return a compact period passband label."""

    if period_min_s is None or period_max_s is None:
        return ""
    return f"{_period_token(period_min_s)}-{_period_token(period_max_s)} sec"


def _period_token(value: float) -> str:
    """Format one period token."""

    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:g}"


def _task_id(payload: dict[str, Any]) -> str:
    """Return a stable task ID."""

    parts = [
        payload.get("event_id", ""),
        payload.get("station", ""),
        payload.get("component", ""),
        payload.get("model", ""),
        payload.get("passband", ""),
        payload.get("output_mode", ""),
        ",".join(payload.get("metrics", ())),
    ]
    digest = hashlib.sha1("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:12]
    return f"metric-{digest}"


def _tuple_from_serialized(value: object) -> tuple[str, ...]:
    """Convert a serialized tuple value into strings."""

    if value in (None, "", np.nan):
        return ()
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip() != "")
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value if item not in (None, ""))
    return (str(value),)


def _optional_float(value: object) -> float | None:
    """Return a finite float or None."""

    try:
        out = float(value)
    except Exception:
        return None
    return out if np.isfinite(out) else None


def _optional_int(value: object) -> int | None:
    """Return a finite integer or None."""

    value_float = _optional_float(value)
    return int(value_float) if value_float is not None else None


def _bool_value(value: object) -> bool:
    """Interpret common serialized boolean values."""

    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _read_table(table: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Read a dataframe or table path."""

    if isinstance(table, pd.DataFrame):
        return table.copy()
    path = Path(table).expanduser()
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _estimate_metric_evaluations(task_table: pd.DataFrame) -> int:
    """Estimate the number of metric values requested by a task table."""

    if task_table.empty:
        return 0
    if "metrics" in task_table.columns:
        return int(task_table["metrics"].apply(lambda value: max(len(_tuple_from_serialized(value)), 1)).sum())
    if "metric" in task_table.columns:
        return int(task_table["metric"].notna().sum())
    return int(len(task_table))


def _unique_count_text(task_table: pd.DataFrame, column: str) -> str:
    """Return a formatted unique-count value for one task-table column."""

    if column not in task_table.columns:
        return "not available"
    return f"{task_table[column].dropna().astype(str).nunique():,}"


def _unique_values_text(task_table: pd.DataFrame, column: str, *, fallback_column: str | None = None, max_values: int = 6) -> str:
    """Return compact unique values for one task-table column."""

    active_column = column if column in task_table.columns else fallback_column
    if active_column is None or active_column not in task_table.columns:
        return "not available"
    values = [str(value) for value in task_table[active_column].dropna().unique() if str(value).strip()]
    if not values:
        return "not available"
    values = sorted(values)
    if len(values) <= max_values:
        return ", ".join(values)
    return f"{len(values):,} values"


def _format_hours(hours: float) -> str:
    """Format a CPU-hour estimate."""

    if hours == 0.0:
        return "0"
    return f"{hours:.3f}" if hours < 0.1 else f"{hours:.2f}"


def _format_duration(seconds: float) -> str:
    """Format a wall-clock duration estimate."""

    if seconds < 60.0:
        return f"{seconds:.0f} sec"
    minutes = seconds / 60.0
    if minutes < 90.0:
        return f"{minutes:.1f} min"
    return f"{minutes / 60.0:.2f} hr"


__all__ = [
    "DEFAULT_METRICS_BY_GROUP",
    "LEGACY_METRIC_ALIASES",
    "MetricWorkflowTask",
    "metric_group_for",
    "plan_metric_tasks",
    "resolve_metric_names",
    "summarize_metric_tasks",
    "tasks_from_frame",
    "tasks_to_frame",
]
