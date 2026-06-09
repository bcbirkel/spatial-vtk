"""Run metric workflow tasks.

Purpose
-------
This module executes file-based metric tasks and writes standardized long
metric tables. It keeps calculation logic separate from manifest chunking and
SLURM script generation.

Usage examples
--------------
Run planned tasks:
  ``rows = run_metric_tasks(tasks, qc_table=qc_inventory)``
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from spatial_vtk.io.metric_inputs import metric_qc_lookup, metric_qc_passed
from spatial_vtk.io.waveforms import WaveformPreprocessing, apply_waveform_preprocessing_with_metadata, read_waveform_file
from spatial_vtk.metrics.calculate import (
    CAV,
    FAS,
    PGA,
    PGD,
    PGV,
    PSA,
    arias_duration,
    arias_intensity,
    bandpass_with_metadata,
    build_metric_value_row,
    build_spectral_metric_rows,
    delay_corrected_cc,
    energy_duration,
    energy_intensity,
    original_cc,
    traveltime_delay,
)
from spatial_vtk.metrics.workflow.tasks import MetricWorkflowTask, metric_group_for, tasks_from_frame
from spatial_vtk.qc.build.spectral import qc_fas_periods, qc_psa_periods


PAIR_ONLY_METRICS = {"traveltime_delay", "original_cc", "delay_corrected_cc"}
TRACE_VALUE_METRICS = {
    "arias_duration",
    "energy_duration",
    "PGA",
    "PGV",
    "PGD",
    "arias_intensity",
    "energy_intensity",
    "CAV",
}
SPECTRAL_METRICS = {"PSA", "FAS"}


@dataclass(frozen=True)
class _LoadedSide:
    """One loaded waveform side and its actual sample interval."""

    data: np.ndarray
    dt: float
    valid_mask: np.ndarray | None = None


def run_metric_tasks(
    tasks: list[MetricWorkflowTask],
    *,
    qc_table: pd.DataFrame | str | Path | None = None,
) -> pd.DataFrame:
    """Run metric workflow tasks and return a long metric table.

    Parameters
    ----------
    tasks
        Metric workflow tasks.
    qc_table
        Optional side-specific QC inventory.

    Returns
    -------
    pandas.DataFrame
        Long metric table.
    """

    lookup = metric_qc_lookup(qc_table)
    rows: list[dict[str, Any]] = []
    waveform_cache: dict[str, Any] = {}
    for task in tasks:
        rows.extend(calculate_task_rows(task, qc_lookup=lookup, waveform_cache=waveform_cache))
    return pd.DataFrame(rows)


def calculate_task_rows(
    task: MetricWorkflowTask,
    *,
    qc_lookup: dict[tuple[str, str, str, str, str, str, str], dict[str, Any]] | None = None,
    waveform_cache: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Calculate all metric rows for one workflow task.

    Parameters
    ----------
    task
        Workflow task.
    qc_lookup
        Optional normalized QC lookup.
    waveform_cache
        Optional cache of loaded waveform files reused across tasks.

    Returns
    -------
    list[dict[str, object]]
        Long metric rows.
    """

    lookup = qc_lookup or {}
    observed = _load_and_prepare_side(
        task.obs_waveform_path,
        task.station,
        task.component,
        task.period_min_s,
        task.period_max_s,
        task.waveform_lowpass_hz,
        task.waveform_resample_hz,
        task.waveform_filter_order,
        waveform_cache=waveform_cache,
    ) if task.obs_waveform_path else None
    synthetic = _load_and_prepare_side(
        task.syn_waveform_path,
        task.station,
        task.component,
        task.period_min_s,
        task.period_max_s,
        task.waveform_lowpass_hz,
        task.waveform_resample_hz,
        task.waveform_filter_order,
        waveform_cache=waveform_cache,
    ) if task.syn_waveform_path else None
    if task.output_mode in {"residual", "gof", "full"} and (observed is None or synthetic is None):
        raise ValueError(f"Task {task.task_id} requires both observed and synthetic waveforms for output_mode={task.output_mode!r}.")
    rows: list[dict[str, Any]] = []
    spectral_qc = _build_spectral_qc(task, observed, synthetic)
    for metric in task.metrics:
        group = metric_group_for(metric)
        if metric in TRACE_VALUE_METRICS:
            rows.append(_calculate_trace_metric_row(task, metric, group, observed, synthetic, lookup))
        elif metric in SPECTRAL_METRICS:
            rows.extend(_calculate_spectral_metric_rows(task, metric, observed, synthetic, lookup, spectral_qc))
        elif metric in PAIR_ONLY_METRICS:
            rows.append(_calculate_pair_metric_row(task, metric, group, observed, synthetic, lookup))
        else:
            raise ValueError(f"Unsupported metric in workflow task: {metric!r}")
    return rows


def write_metric_rows(df: pd.DataFrame, path: str | Path) -> Path:
    """Write metric rows to CSV or Parquet based on file suffix.

    Parameters
    ----------
    df
        Metric dataframe.
    path
        Output path. ``.parquet`` and ``.pq`` use Parquet; all other suffixes
        use CSV.

    Returns
    -------
    pathlib.Path
        Written output path.
    """

    output = Path(path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() in {".parquet", ".pq"}:
        df.to_parquet(output, index=False)
    else:
        df.to_csv(output, index=False)
    return output


def _calculate_trace_metric_row(
    task: MetricWorkflowTask,
    metric: str,
    group: str,
    observed: _LoadedSide | None,
    synthetic: _LoadedSide | None,
    lookup: dict[tuple[str, str, str, str, str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Calculate one scalar trace-value metric row."""

    obs_qc = _lookup_qc(task, lookup, "observed", group, metric, None)
    syn_qc = _lookup_qc(task, lookup, "synthetic", group, metric, None)
    observed = _apply_qc_valid_window(observed, obs_qc) if task.use_qc else observed
    synthetic = _apply_qc_valid_window(synthetic, syn_qc) if task.use_qc else synthetic
    obs_ok, syn_ok = _side_ok(task, obs_qc, _side_available(observed)), _side_ok(task, syn_qc, _side_available(synthetic))
    obs_data = _valid_data(observed) if observed is not None else None
    syn_data = _valid_data(synthetic) if synthetic is not None else None
    obs_value = _calculate_trace_metric(metric, obs_data, observed.dt, task.period_min_s, obs_ok) if observed is not None else np.nan
    syn_value = _calculate_trace_metric(metric, syn_data, synthetic.dt, task.period_min_s, syn_ok) if synthetic is not None else np.nan
    comparison_ok = _comparison_ok(task, obs_ok, syn_ok)
    return build_metric_value_row(
        metric_group=group,
        metric=metric,
        value_obs=obs_value if task.output_mode != "synthetic" else np.nan,
        value_syn=syn_value if task.output_mode != "observed" else np.nan,
        transforms=task.transforms if comparison_ok else (),
        **_context(task),
        **_qc_payload(task, obs_qc, syn_qc, obs_ok, syn_ok, comparison_ok),
    )


def _calculate_spectral_metric_rows(
    task: MetricWorkflowTask,
    metric: str,
    observed: _LoadedSide | None,
    synthetic: _LoadedSide | None,
    lookup: dict[tuple[str, str, str, str, str, str, str], dict[str, Any]],
    spectral_qc: dict[tuple[str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    """Calculate one row per requested spectral period."""

    periods = task.spectral_periods_s
    if not periods:
        return []
    rows: list[dict[str, Any]] = []
    for idx, period_s in enumerate(periods):
        obs_qc = _combine_qc_rows(
            _lookup_qc(task, lookup, "observed", "spectral", metric, period_s),
            spectral_qc.get(("observed", metric, _period_key(period_s))),
        )
        syn_qc = _combine_qc_rows(
            _lookup_qc(task, lookup, "synthetic", "spectral", metric, period_s),
            spectral_qc.get(("synthetic", metric, _period_key(period_s))),
        )
        observed_for_period = _apply_qc_valid_window(observed, obs_qc) if task.use_qc else observed
        synthetic_for_period = _apply_qc_valid_window(synthetic, syn_qc) if task.use_qc else synthetic
        obs_ok = _side_ok(task, obs_qc, _side_available(observed_for_period))
        syn_ok = _side_ok(task, syn_qc, _side_available(synthetic_for_period))
        obs_values = _calculate_spectral_values(metric, _valid_data(observed_for_period), observed_for_period.dt, periods) if observed_for_period is not None else np.full(len(periods), np.nan)
        syn_values = _calculate_spectral_values(metric, _valid_data(synthetic_for_period), synthetic_for_period.dt, periods) if synthetic_for_period is not None else np.full(len(periods), np.nan)
        comparison_ok = _comparison_ok(task, obs_ok, syn_ok)
        rows.extend(
            build_spectral_metric_rows(
                metric=metric,
                periods_s=[period_s],
                values_obs=[obs_values[idx] if obs_ok and task.output_mode != "synthetic" else np.nan],
                values_syn=[syn_values[idx] if syn_ok and task.output_mode != "observed" else np.nan],
                transforms=task.transforms if comparison_ok else (),
                **_context(task),
                **_qc_payload(task, obs_qc, syn_qc, obs_ok, syn_ok, comparison_ok),
            )
        )
    return rows


def _calculate_pair_metric_row(
    task: MetricWorkflowTask,
    metric: str,
    group: str,
    observed: _LoadedSide | None,
    synthetic: _LoadedSide | None,
    lookup: dict[tuple[str, str, str, str, str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Calculate one pair-only metric row."""

    obs_qc = _lookup_qc(task, lookup, "observed", group, metric, None)
    syn_qc = _lookup_qc(task, lookup, "synthetic", group, metric, None)
    observed = _apply_qc_valid_window(observed, obs_qc) if task.use_qc else observed
    synthetic = _apply_qc_valid_window(synthetic, syn_qc) if task.use_qc else synthetic
    obs_ok = _side_ok(task, obs_qc, _side_available(observed))
    syn_ok = _side_ok(task, syn_qc, _side_available(synthetic))
    comparison_ok = _comparison_ok(task, obs_ok, syn_ok)
    observed_pair, synthetic_pair = _trim_pair_to_common_valid(observed, synthetic) if comparison_ok and observed is not None and synthetic is not None else (None, None)
    pair_value = _calculate_pair_metric(metric, observed_pair, synthetic_pair, _pair_dt(observed, synthetic)) if comparison_ok else np.nan
    row = build_metric_value_row(
        metric_group=group,
        metric=metric,
        transforms=(),
        **_context(task),
        **_qc_payload(task, obs_qc, syn_qc, obs_ok, syn_ok, comparison_ok),
    )
    row["value"] = pair_value
    return row


def _calculate_trace_metric(metric: str, data: np.ndarray | None, dt: float, period_min_s: float | None, ok: bool) -> float:
    """Calculate one scalar trace metric or NaN when unavailable."""

    if data is None or not ok:
        return np.nan
    if metric == "arias_duration":
        return arias_duration(data, dt)
    if metric == "energy_duration":
        return energy_duration(data, dt, fmin=_fmin_from_period(period_min_s))
    if metric == "PGA":
        return PGA(data)
    if metric == "PGV":
        return PGV(data, dt, fmin=_fmin_from_period(period_min_s))
    if metric == "PGD":
        return PGD(data, dt, fmin=_fmin_from_period(period_min_s))
    if metric == "arias_intensity":
        return arias_intensity(data, dt)
    if metric == "energy_intensity":
        return energy_intensity(data, dt, fmin=_fmin_from_period(period_min_s))
    if metric == "CAV":
        return CAV(data, dt)
    raise ValueError(f"Unsupported scalar trace metric: {metric}")


def _calculate_spectral_values(metric: str, data: np.ndarray | None, dt: float, periods: tuple[float, ...]) -> np.ndarray:
    """Calculate spectral values for one side."""

    if data is None:
        return np.full(len(periods), np.nan)
    if metric == "PSA":
        return PSA(data, dt, periods)
    if metric == "FAS":
        return FAS(data, dt, periods=periods)
    raise ValueError(f"Unsupported spectral metric: {metric}")


def _calculate_pair_metric(metric: str, observed: np.ndarray | None, synthetic: np.ndarray | None, dt: float) -> float:
    """Calculate one pair-only metric."""

    if observed is None or synthetic is None:
        return np.nan
    if metric == "traveltime_delay":
        return traveltime_delay(observed, synthetic, dt)
    if metric == "original_cc":
        return original_cc(observed, synthetic)
    if metric == "delay_corrected_cc":
        return delay_corrected_cc(observed, synthetic, dt)
    raise ValueError(f"Unsupported pair-only metric: {metric}")


def _load_and_prepare_side(
    path: str,
    station: str,
    component: str,
    period_min_s: float | None,
    period_max_s: float | None,
    lowpass_hz: float | None = None,
    resample_hz: float | None = None,
    filter_order: int | None = None,
    waveform_cache: dict[str, Any] | None = None,
) -> _LoadedSide:
    """Load one waveform side and apply configured preprocessing and bandpass."""

    side = _load_component_samples(path, station, component, waveform_cache=waveform_cache)
    if lowpass_hz is not None or resample_hz is not None:
        processed = apply_waveform_preprocessing_with_metadata(
            side.data,
            side.dt,
            WaveformPreprocessing(
                lowpass_hz=lowpass_hz,
                resample_hz=resample_hz,
                filter_order=filter_order or 4,
            ),
        )
        side = _LoadedSide(processed.data, processed.dt, _processing_valid_mask(processed.data.size, lowpass_hz=lowpass_hz, resample_hz=resample_hz))
    if period_min_s is None or period_max_s is None:
        return side
    low_hz = 1.0 / float(period_max_s)
    high_hz = 1.0 / float(period_min_s)
    bandpassed = bandpass_with_metadata(side.data, side.dt, low_hz, high_hz)
    valid_mask = _combine_valid_masks(side.valid_mask, bandpassed.valid_mask)
    return _LoadedSide(bandpassed.data, side.dt, valid_mask)


def _load_component_samples(path: str, station: str, component: str, *, waveform_cache: dict[str, Any] | None = None) -> _LoadedSide:
    """Load samples and sample interval for one station/component."""

    source = str(path)
    source_path = Path(source).expanduser()
    cache_key = f"{source}::{station}::{component}" if source_path.suffix.lower() == ".asdf" else source
    if waveform_cache is not None and cache_key in waveform_cache:
        stream = waveform_cache[cache_key]
    else:
        if source_path.suffix.lower() == ".asdf":
            from spatial_vtk.io.synthetic_formats import (
                SyntheticFormatInfo,
                SyntheticReadRequest,
                synthetic_reader_for,
            )

            info = SyntheticFormatInfo(str(source_path), "asdf", True, False)
            stream = synthetic_reader_for(info).read(
                SyntheticReadRequest(station=station, component=component)
            )
        else:
            stream = read_waveform_file(source)
        if waveform_cache is not None:
            waveform_cache[cache_key] = stream
    traces = list(stream if isinstance(stream, list) else stream) if _is_iterable_stream(stream) else [stream]
    station_token = str(station).strip().upper()
    component_token = str(component).strip().upper()
    selected = None
    for trace in traces:
        trace_station = _trace_station(trace)
        trace_component = _trace_component(trace)
        if trace_station == station_token and trace_component == component_token:
            selected = trace
            break
    if selected is None:
        available = sorted({_trace_station(trace) + "." + _trace_component(trace) for trace in traces})
        raise ValueError(
            f"Waveform file does not contain station/component {station_token}.{component_token}: {path}. "
            f"Available station/components include: {available[:12]}"
        )
    samples = _trace_data(selected)
    if samples.size == 0:
        raise ValueError(f"Waveform file contains no samples: {path}")
    return _LoadedSide(samples, _trace_dt(selected), np.ones(samples.size, dtype=bool))


def _processing_valid_mask(sample_count: int, *, lowpass_hz: float | None = None, resample_hz: float | None = None) -> np.ndarray:
    """Return samples considered valid after workflow preprocessing."""

    count = int(sample_count)
    if count <= 0:
        return np.zeros(0, dtype=bool)
    mask = np.ones(count, dtype=bool)
    if lowpass_hz is None and resample_hz is None:
        return mask
    edge = int(round(count * 0.05))
    if edge > 0 and edge * 2 < count:
        mask[:edge] = False
        mask[-edge:] = False
    return mask


def _combine_valid_masks(*masks: np.ndarray | None) -> np.ndarray | None:
    """Return the intersection of available validity masks."""

    present = [np.asarray(mask, dtype=bool) for mask in masks if mask is not None]
    if not present:
        return None
    out = present[0].copy()
    for mask in present[1:]:
        if mask.shape != out.shape:
            raise ValueError("Cannot combine waveform validity masks with different shapes.")
        out &= mask
    return out


def _apply_qc_valid_window(side: _LoadedSide | None, qc_row: dict[str, Any] | None) -> _LoadedSide | None:
    """Intersect one loaded side with a QC-provided valid sample window."""

    if side is None or qc_row is None:
        return side
    start, end = _qc_valid_sample_bounds(qc_row, side.data.size, side.dt)
    if start is None or end is None:
        return side
    mask = np.zeros(side.data.size, dtype=bool)
    mask[start:end] = True
    return _LoadedSide(side.data, side.dt, _combine_valid_masks(side.valid_mask, mask))


def _qc_valid_sample_bounds(qc_row: dict[str, Any], sample_count: int, dt: float) -> tuple[int | None, int | None]:
    """Return inclusive/exclusive valid sample bounds from one QC row."""

    start_sample = _optional_int(qc_row.get("valid_start_sample"))
    end_sample = _optional_int(qc_row.get("valid_end_sample"))
    count = int(sample_count)
    if start_sample is not None and end_sample is not None:
        start = max(0, min(count, start_sample))
        end = max(start, min(count, end_sample))
        return (start, end) if end > start else (None, None)
    start_s = _optional_float(qc_row.get("valid_start_rel_s"))
    end_s = _optional_float(qc_row.get("valid_end_rel_s"))
    if start_s is None or end_s is None or end_s <= start_s:
        return None, None
    reference_start_s = _optional_float(qc_row.get("trace_start_s"))
    sample_dt = _optional_float(qc_row.get("sample_interval_s")) or float(dt)
    if not np.isfinite(sample_dt) or sample_dt <= 0.0:
        return None, None
    origin = reference_start_s if reference_start_s is not None else 0.0
    start = max(0, int(np.ceil((start_s - origin) / sample_dt)))
    end = min(count, int(np.floor((end_s - origin) / sample_dt)))
    return (start, end) if end > start else (None, None)


def _valid_data(side: _LoadedSide | None) -> np.ndarray | None:
    """Return samples inside a loaded side's valid mask."""

    if side is None:
        return None
    data = np.asarray(side.data, dtype=float)
    if side.valid_mask is None:
        return data
    mask = np.asarray(side.valid_mask, dtype=bool)
    if mask.shape != data.shape:
        raise ValueError("Waveform data and validity mask must have matching shapes.")
    return data[mask]


def _side_available(side: _LoadedSide | None) -> bool:
    """Return whether a side has enough valid samples for metrics."""

    data = _valid_data(side)
    return data is not None and data.size >= 2


def _trim_pair_to_common_valid(observed: _LoadedSide, synthetic: _LoadedSide) -> tuple[np.ndarray, np.ndarray]:
    """Return observed/synthetic valid samples trimmed to a common length."""

    obs = _valid_data(observed)
    syn = _valid_data(synthetic)
    if obs is None or syn is None:
        return np.asarray([], dtype=float), np.asarray([], dtype=float)
    count = min(obs.size, syn.size)
    if count <= 0:
        return obs[:0], syn[:0]
    return obs[:count], syn[:count]


def _optional_float(value: object) -> float | None:
    """Return a finite float or None."""

    try:
        numeric = float(value)
    except Exception:
        return None
    return numeric if np.isfinite(numeric) else None


def _optional_int(value: object) -> int | None:
    """Return an integer when the input is finite."""

    numeric = _optional_float(value)
    return int(round(numeric)) if numeric is not None else None


def _build_spectral_qc(
    task: MetricWorkflowTask,
    observed: _LoadedSide | None,
    synthetic: _LoadedSide | None,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Build side-specific spectral QC lookup for one task."""

    out: dict[tuple[str, str, str], dict[str, Any]] = {}
    if not task.spectral_periods_s:
        return out
    for source, side in (("observed", observed), ("synthetic", synthetic)):
        if side is None:
            continue
        side_data = _valid_data(side)
        if side_data is None or side_data.size < 2:
            continue
        for metric in ("PSA", "FAS"):
            qc = (
                qc_psa_periods(
                    side_data,
                    dt=side.dt,
                    periods_s=task.spectral_periods_s,
                    threshold=task.spectral_relative_amplitude_threshold,
                    min_cycles_in_record=task.spectral_min_cycles_in_record,
                    synthetic_max_frequency_hz=task.synthetic_max_frequency_hz,
                    source=source,
                    disable_relative_amplitude_qc=task.disable_spectral_relative_amplitude_qc,
                )
                if metric == "PSA"
                else qc_fas_periods(
                    side_data,
                    dt=side.dt,
                    periods_s=task.spectral_periods_s,
                    threshold=task.spectral_relative_amplitude_threshold,
                    min_cycles_in_record=task.spectral_min_cycles_in_record,
                    synthetic_max_frequency_hz=task.synthetic_max_frequency_hz,
                    source=source,
                    disable_relative_amplitude_qc=task.disable_spectral_relative_amplitude_qc,
                )
            )
            for _, row in qc.iterrows():
                out[(source, metric, _period_key(row["period_s"]))] = row.to_dict()
    return out


def _lookup_qc(
    task: MetricWorkflowTask,
    lookup: dict[tuple[str, str, str, str, str, str, str], dict[str, Any]],
    source: str,
    group: str,
    metric: str,
    period_s: float | None,
) -> dict[str, Any] | None:
    """Look up one side-specific QC row."""

    period = _period_key(period_s)
    keys = [
        (source, task.event_id, task.station, task.component, group, metric, period),
        (source, task.event_id, task.station, task.component, "", metric, period),
        (source, task.event_id, task.station, task.component, group, "", period),
        (source, task.event_id, task.station, task.component, "", "", ""),
    ]
    for key in keys:
        if key in lookup:
            return lookup[key]
    return None


def _combine_qc_rows(*rows: dict[str, Any] | None) -> dict[str, Any] | None:
    """Combine QC rows, failing when any source row fails."""

    present = [row for row in rows if row is not None]
    if not present:
        return None
    combined: dict[str, Any] = {}
    for row in present:
        combined.update({key: value for key, value in row.items() if key not in {"qc_status", "qc_reason"}})
    failed = [row for row in present if not metric_qc_passed(row)]
    if failed:
        reasons = [str(row.get("qc_reason", "")) for row in failed if str(row.get("qc_reason", ""))]
        combined.update({"qc_status": "fail", "qc_reason": ";".join(reasons) or "qc_failed"})
        return combined
    combined.update({"qc_status": "pass", "qc_reason": ""})
    return combined


def _side_ok(task: MetricWorkflowTask, qc_row: dict[str, Any] | None, side_available: bool) -> bool:
    """Return whether one side is usable."""

    if not side_available:
        return False
    return metric_qc_passed(qc_row) if task.use_qc else True


def _comparison_ok(task: MetricWorkflowTask, obs_ok: bool, syn_ok: bool) -> bool:
    """Return whether observed/synthetic comparison is allowed."""

    return task.output_mode in {"residual", "gof", "full"} and obs_ok and syn_ok


def _qc_payload(
    task: MetricWorkflowTask,
    obs_qc: dict[str, Any] | None,
    syn_qc: dict[str, Any] | None,
    obs_ok: bool,
    syn_ok: bool,
    comparison_ok: bool,
) -> dict[str, str]:
    """Return standardized QC output fields."""

    obs_status = "pass" if obs_ok else "fail"
    syn_status = "pass" if syn_ok else "fail"
    if task.output_mode == "observed":
        syn_status = ""
    if task.output_mode == "synthetic":
        obs_status = ""
    return {
        "obs_qc_status": obs_status,
        "obs_qc_reason": "" if obs_ok else str((obs_qc or {}).get("qc_reason", "observed_unavailable_or_failed_qc")),
        "syn_qc_status": syn_status,
        "syn_qc_reason": "" if syn_ok else str((syn_qc or {}).get("qc_reason", "synthetic_unavailable_or_failed_qc")),
        "comparison_qc_status": "pass" if comparison_ok else ("not_applicable" if task.output_mode in {"observed", "synthetic"} else "fail"),
        "comparison_qc_reason": "" if comparison_ok else ("single_side_output_mode" if task.output_mode in {"observed", "synthetic"} else "observed_or_synthetic_failed_qc"),
    }


def _context(task: MetricWorkflowTask) -> dict[str, Any]:
    """Return standard row context for one task."""

    return {
        "task_id": task.task_id,
        "event_id": task.event_id,
        "station": task.station,
        "component": task.component,
        "model": task.model,
        "passband": task.passband,
        "obs_waveform_path": task.obs_waveform_path,
        "syn_waveform_path": task.syn_waveform_path,
    }


def _trace_data(trace: Any) -> np.ndarray:
    """Return trace samples."""

    data = trace.get("data") if isinstance(trace, dict) else getattr(trace, "data", trace)
    return np.asarray(data, dtype=float).reshape(-1)


def _trace_dt(trace: Any) -> float:
    """Return trace sample interval."""

    stats = trace.get("stats", {}) if isinstance(trace, dict) else getattr(trace, "stats", {})
    delta = _stat_value(stats, "delta", None)
    if delta not in (None, ""):
        try:
            value = float(delta)
        except Exception:
            value = np.nan
        if np.isfinite(value) and value > 0.0:
            return value
    sampling_rate = _stat_value(stats, "sampling_rate", None)
    if sampling_rate not in (None, ""):
        try:
            value = float(sampling_rate)
        except Exception:
            value = np.nan
        if np.isfinite(value) and value > 0.0:
            return 1.0 / value
    raise ValueError("Loaded trace is missing a positive delta or sampling_rate.")


def _trace_component(trace: Any) -> str:
    """Return trace component token."""

    stats = trace.get("stats", {}) if isinstance(trace, dict) else getattr(trace, "stats", {})
    channel = _stat_value(stats, "channel", "")
    component = _stat_value(stats, "component", "")
    token = str(component or channel[-1:] or "").strip().upper()
    return token


def _trace_station(trace: Any) -> str:
    """Return trace station token."""

    stats = trace.get("stats", {}) if isinstance(trace, dict) else getattr(trace, "stats", {})
    station = _stat_value(stats, "station", "")
    return str(station or "").strip().upper()


def _stat_value(stats: Any, key: str, default: Any = None) -> Any:
    """Read stats value from mapping or object."""

    if isinstance(stats, dict):
        return stats.get(key, default)
    return getattr(stats, key, default)


def _is_iterable_stream(value: Any) -> bool:
    """Return whether a loaded waveform should be iterated as traces."""

    return hasattr(value, "__iter__") and not isinstance(value, (dict, str, bytes, np.ndarray))


def _pair_dt(observed: _LoadedSide, synthetic: _LoadedSide) -> float:
    """Return pair dt when two sides use a compatible sample interval."""

    if not np.isclose(observed.dt, synthetic.dt):
        raise ValueError(
            "Pair-only metrics require observed and synthetic traces with matching sample intervals. "
            "Resample the waveforms before requesting traveltime or cross-correlation metrics."
        )
    return observed.dt


def _fmin_from_period(period_min_s: float | None) -> float | None:
    """Return minimum integration frequency from a period minimum."""

    if period_min_s is None or period_min_s <= 0.0:
        return None
    return 1.0 / float(period_min_s)


def _period_key(value: object) -> str:
    """Return stable period key."""

    try:
        number = float(value)
    except Exception:
        return ""
    return f"{number:g}" if np.isfinite(number) else ""


def build_arg_parser() -> argparse.ArgumentParser:
    """Build a CLI parser for direct task-table execution."""

    parser = argparse.ArgumentParser(description="Run Spatial-VTK metric tasks from a task table.")
    parser.add_argument("--tasks-csv", required=True, help="CSV or parquet file created by metric task planning.")
    parser.add_argument("--qc-table", default=None, help="Optional side-specific QC table.")
    parser.add_argument("--output", required=True, help="Metric rows output CSV or parquet.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run metric tasks from a task table."""

    args = build_arg_parser().parse_args(argv)
    rows = run_metric_tasks(tasks_from_frame(args.tasks_csv), qc_table=args.qc_table)
    write_metric_rows(rows, args.output)
    return 0


__all__ = [
    "calculate_task_rows",
    "run_metric_tasks",
    "write_metric_rows",
    "build_arg_parser",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
