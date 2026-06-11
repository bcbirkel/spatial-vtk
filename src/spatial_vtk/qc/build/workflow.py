"""High-level QC table builders for public workflows.

Purpose
-------
This module creates the standard QC tables used by notebooks, CLI commands,
figures, metric filtering, dashboards, and manual-review exports.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import re
import time

import numpy as np
import pandas as pd

from spatial_vtk.config.metric_catalog import metric_group_for
from spatial_vtk.config.metrics import metrics_settings_from_config
from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.config.runtime import SpatialVTKConfig, active_config
from spatial_vtk.io.inventory import build_file_inventory
from spatial_vtk.io.tables import write_table
from spatial_vtk.io.waveforms import WaveformPreprocessing, read_waveform_file, select_waveform_trace
from spatial_vtk.qc.build.inventory import build_waveform_trace_qc_summary
from spatial_vtk.visualize.dashboard import write_manual_review_queue

_COMPARISON_METADATA_COLUMNS = (
    "event_title",
    "event_lat",
    "event_lon",
    "station_lat",
    "station_lon",
    "network",
    "magnitude",
    "distance_km",
    "azimuth_deg",
    "backazimuth_deg",
    "depth_km",
    "event_depth_km",
    "lat",
    "lon",
    "sta_lat",
    "sta_lon",
)


def _progress(verbose: bool, message: str) -> None:
    """Print one flushed progress message when verbose mode is enabled."""

    if verbose:
        print(message, flush=True)


def _format_duration(seconds: float) -> str:
    """Format elapsed seconds for progress messages."""

    seconds = max(float(seconds), 0.0)
    if seconds < 60.0:
        return f"{seconds:.1f}s"
    minutes, remaining = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m{remaining:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m{remaining:02d}s"


def _progress_status(prefix: str, current: int, total: int, start_time: float) -> str:
    """Return a progress message with elapsed time, rate, and ETA."""

    elapsed = max(time.monotonic() - float(start_time), 0.0)
    rate = float(current) / elapsed if elapsed > 0 else 0.0
    remaining = max(int(total) - int(current), 0)
    eta = remaining / rate if rate > 0 else 0.0
    return (
        f"{prefix}: record {current}/{total} "
        f"(elapsed {_format_duration(elapsed)}, {rate:.2f} records/s, ETA {_format_duration(eta)})"
    )


def _plural(count: int, singular: str, plural: str | None = None) -> str:
    """Return the singular or plural form for a count."""

    return singular if int(count) == 1 else (plural or f"{singular}s")


def _load_qc_checkpoint(path: str | Path | None) -> pd.DataFrame:
    """Load an existing QC checkpoint table if present."""

    if path is None:
        return pd.DataFrame()
    checkpoint = Path(path).expanduser()
    if not checkpoint.exists():
        return pd.DataFrame()
    try:
        return _read_table(checkpoint)
    except Exception:
        return pd.DataFrame()


def _write_qc_checkpoint(df: pd.DataFrame, path: str | Path | None) -> None:
    """Write one QC checkpoint table when a path is configured."""

    if path is None:
        return
    checkpoint = Path(path).expanduser()
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    write_table(df, checkpoint)


def _source_checkpoint_path(path: str | Path | None, source: str) -> Path | None:
    """Return a source-specific checkpoint path next to the combined table."""

    if path is None:
        return None
    checkpoint = Path(path).expanduser()
    suffix = checkpoint.suffix or ".csv"
    stem = checkpoint.name[: -len(checkpoint.suffix)] if checkpoint.suffix else checkpoint.name
    return checkpoint.with_name(f"{stem}.{str(source).strip().lower()}.checkpoint{suffix}")


def _combine_csv_checkpoints(paths: Sequence[Path], output_path: str | Path) -> Path:
    """Combine source CSV checkpoints without loading them all into memory."""

    target = Path(output_path).expanduser()
    suffix = target.suffix.lower()
    if suffix not in {"", ".csv"}:
        raise ValueError("Disk-backed QC checkpoint combining currently requires a CSV output path.")
    if not suffix:
        target = target.with_suffix(".csv")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_name(f".{target.name}.tmp")
    wrote_header = False
    with tmp_path.open("w", encoding="utf-8") as output:
        for path in paths:
            checkpoint = Path(path).expanduser()
            if not checkpoint.exists() or checkpoint.stat().st_size == 0:
                continue
            with checkpoint.open("r", encoding="utf-8") as handle:
                header = handle.readline()
                if not header:
                    continue
                if not wrote_header:
                    output.write(header)
                    wrote_header = True
                for line in handle:
                    output.write(line)
    if not wrote_header:
        pd.DataFrame().to_csv(tmp_path, index=False)
    tmp_path.replace(target)
    return target


def _metric_qc_completed_records(df: pd.DataFrame) -> set[tuple[str, str]]:
    """Return completed event/station records from a metric-QC checkpoint."""

    required = {"event_id", "station"}
    if df.empty or not required <= set(df.columns):
        return set()
    return {
        (str(row["event_id"]).strip(), str(row["station"]).strip().upper())
        for _, row in df.loc[:, ["event_id", "station"]].drop_duplicates().iterrows()
    }


def build_metric_qc_summary(
    event_station_records: pd.DataFrame | str | Path,
    *,
    metrics: Sequence[str],
    components: Sequence[str],
    passbands: Sequence[str | Sequence[float]],
    spectral_periods_s: Sequence[float] = (),
    sources: Sequence[str] = ("observed", "synthetic"),
    synthetic_max_frequency_hz: float | None = None,
    observed_available: bool = True,
    synthetic_available: bool = True,
    trace_qc_summary: pd.DataFrame | str | Path | None = None,
    verbose: bool = False,
    progress_interval: int = 25,
    checkpoint_path: str | Path | None = None,
    resume: bool = True,
    checkpoint_interval: int = 25,
) -> pd.DataFrame:
    """Build a side-specific metric QC summary from event-station records.

    Parameters
    ----------
    event_station_records
        Event-station table with at least ``event_id`` and ``station`` columns.
    metrics, components, passbands
        Requested metrics, components, and period bands.
    spectral_periods_s
        Periods to check for spectral metrics.
    sources
        Sources to include, usually ``observed`` and ``synthetic``.
    synthetic_max_frequency_hz
        Maximum valid synthetic frequency. Synthetic spectral periods shorter
        than ``1 / synthetic_max_frequency_hz`` fail QC.
    observed_available, synthetic_available
        Default availability values when the input table does not include
        source-specific availability columns.
    trace_qc_summary
        Optional side-specific waveform QC table. When provided, failed
        source/event/station/component/passband rows fail matching metric rows.
    verbose
        Print progress messages while building QC rows.
    progress_interval
        Number of event-station records between progress messages.
    checkpoint_path
        Optional table path where intermediate QC rows are written.
    resume
        When true and ``checkpoint_path`` exists, skip event/station records
        already present in that checkpoint.
    checkpoint_interval
        Number of event-station records between checkpoint writes.

    Returns
    -------
    pandas.DataFrame
        Standard metric QC rows.
    """

    records = _read_table(event_station_records).drop_duplicates(["event_id", "station"])
    trace_qc = _trace_qc_lookup(trace_qc_summary)
    source_defaults = {
        "observed": bool(observed_available),
        "synthetic": bool(synthetic_available),
    }
    checkpoint = _load_qc_checkpoint(checkpoint_path) if resume else pd.DataFrame()
    rows: list[dict[str, object]] = checkpoint.to_dict(orient="records") if not checkpoint.empty else []
    completed_records = _metric_qc_completed_records(checkpoint)
    total_records = len(records)
    interval = max(int(progress_interval), 1)
    checkpoint_every = max(int(checkpoint_interval), 1)
    progress_start = time.monotonic()
    _progress(
        verbose,
        "Metric QC: "
        f"{total_records} event-station record(s), {len(tuple(sources))} source(s), "
        f"{len(tuple(components))} component(s), {len(tuple(metrics))} metric(s)",
    )
    if checkpoint_path is None:
        _progress(verbose, "Metric QC: checkpointing disabled; starting from scratch")
    else:
        _progress(verbose, f"Metric QC: checkpoint path {Path(checkpoint_path).expanduser()}")
    if completed_records:
        completed_count = min(len(completed_records), total_records)
        remaining_count = max(total_records - completed_count, 0)
        _progress(
            verbose,
            f"Metric QC: resuming with {completed_count} completed "
            f"{_plural(completed_count, 'event-station record')} "
            f"({completed_count}/{total_records} complete; {remaining_count} "
            f"new {_plural(remaining_count, 'record')} remaining)",
        )
    elif checkpoint_path is not None:
        _progress(verbose, "Metric QC: no completed event-station records found; all work is new")
    for record_index, (_, record) in enumerate(records.iterrows(), start=1):
        if record_index == 1 or record_index % interval == 0 or record_index == total_records:
            _progress(verbose, _progress_status("Metric QC", record_index, total_records, progress_start))
        record_key = (str(record.get("event_id", "")).strip(), str(record.get("station", "")).strip().upper())
        if record_key in completed_records:
            continue
        for source in sources:
            source_key = str(source).strip().lower()
            is_available = _source_available(record, source_key, default=source_defaults.get(source_key, True))
            for component in components:
                for metric in metrics:
                    group = metric_group_for(metric) or ""
                    periods = tuple(float(period) for period in spectral_periods_s) if group == "spectral" else (np.nan,)
                    for passband in passbands:
                        band_label = _period_band_label(passband)
                        for period_s in periods:
                            status, reason = _qc_status(
                                source=source_key,
                                available=is_available,
                                metric_group=group,
                                period_s=period_s,
                                synthetic_max_frequency_hz=synthetic_max_frequency_hz,
                            )
                            trace_payload = _trace_qc_payload(
                                trace_qc,
                                source=source_key,
                                event_id=record.get("event_id", ""),
                                station=record.get("station", ""),
                                component=component,
                                passband=band_label,
                            )
                            if status == "pass":
                                status, reason = _apply_trace_qc(
                                    trace_payload,
                                    current_status=status,
                                    current_reason=reason,
                                )
                            rows.append(
                                {
                                    "source": source_key,
                                    "event_id": record.get("event_id", ""),
                                    "station": str(record.get("station", "")).strip().upper(),
                                    "event_title": record.get("event_title", ""),
                                    "event_lat": _first_present(record, "event_lat", "source_lat"),
                                    "event_lon": _first_present(record, "event_lon", "source_lon"),
                                    "station_lat": _first_present(record, "station_lat", "lat", "sta_lat"),
                                    "station_lon": _first_present(record, "station_lon", "lon", "sta_lon"),
                                    "network": _first_present(record, "network", "network_x", "network_y"),
                                    "magnitude": _first_present(record, "magnitude", "event_magnitude", "Mw"),
                                    "distance_km": _first_present(record, "distance_km", "hypocentral_distance_km"),
                                    "component": str(component).strip().upper(),
                                    "passband": band_label,
                                    "metric_group": group,
                                    "metric": str(metric),
                                    "period_s": period_s,
                                    "qc_status": status,
                                    "qc_reason": reason,
                                    "trace_start_s": trace_payload.get("trace_start_s", np.nan),
                                    "sample_interval_s": trace_payload.get("sample_interval_s", np.nan),
                                    "valid_start_rel_s": trace_payload.get("valid_start_rel_s", np.nan),
                                    "valid_end_rel_s": trace_payload.get("valid_end_rel_s", np.nan),
                                    "valid_start_sample": trace_payload.get("valid_start_sample", np.nan),
                                    "valid_end_sample": trace_payload.get("valid_end_sample", np.nan),
                                }
                            )
        completed_records.add(record_key)
        if checkpoint_path is not None and (record_index % checkpoint_every == 0 or record_index == total_records):
            _write_qc_checkpoint(pd.DataFrame(rows), checkpoint_path)
    _progress(verbose, f"Metric QC: built {len(rows)} row(s) in {_format_duration(time.monotonic() - progress_start)}")
    result = pd.DataFrame(rows)
    _write_qc_checkpoint(result, checkpoint_path)
    return result


def build_waveform_qc_summary(
    event_station_records: pd.DataFrame | str | Path,
    *,
    sources: Sequence[str] = ("observed", "synthetic"),
    waveform_path_columns: dict[str, str] | None = None,
    components: Sequence[str] | None = None,
    passbands: Sequence[str | Sequence[float]] | None = None,
    preprocessing: WaveformPreprocessing | None = None,
    apply_config_preprocessing_to_processed_files: bool = False,
    cfg: SpatialVTKConfig | None = None,
    min_record_length_s: float | None = None,
    min_end_after_origin_s: float | None = None,
    snr_threshold: float | None = None,
    arrival_pick_catalog: pd.DataFrame | str | Path | None = None,
    onset_phase: str = "P",
    min_onset_pick_probability: float = 0.0,
    verbose: bool = False,
    progress_interval: int = 25,
    checkpoint_path: str | Path | None = None,
    resume: bool = True,
    checkpoint_interval: int = 25,
    return_result: bool = True,
) -> pd.DataFrame:
    """Build observed/synthetic waveform QC rows from event-station records.

    Parameters
    ----------
    event_station_records
        Event-station table with waveform path columns.
    sources
        Source labels to inspect.
    waveform_path_columns
        Optional mapping from source label to waveform path column.
    components, passbands
        Optional component and period-band selections. When omitted, the active
        metric settings are used.
    preprocessing
        Optional preprocessing applied before QC. When omitted and a processed
        waveform column is used, no extra filtering is applied.
    apply_config_preprocessing_to_processed_files
        Whether processed waveform columns should still use config
        preprocessing during QC.
    cfg
        Optional config object. When omitted, the active config is used.
    min_record_length_s, min_end_after_origin_s, snr_threshold
        Optional QC threshold overrides. Missing values are read from
        ``qc.automatic`` in the config.
    arrival_pick_catalog
        Optional PhaseNet-style pick catalog used to anchor QC windows.
    onset_phase
        Pick phase used as the QC onset when available.
    min_onset_pick_probability
        Minimum picker probability accepted for the QC onset pick.
    verbose
        Print progress messages while loading waveforms and building QC rows.
    progress_interval
        Number of event-station records between progress messages.
    checkpoint_path
        Optional table path where the combined waveform QC summary is written.
        Per-source intermediate checkpoints are written next to this path.
    resume
        When true, existing per-source checkpoints are used to skip completed
        event/station/component groups.
    checkpoint_interval
        Number of event-station records between checkpoint writes.
    return_result
        When false, write per-source checkpoints and combine them on disk into
        ``checkpoint_path`` instead of keeping all source QC rows in memory.
        This is intended for Slurm workers on large inventories.

    Returns
    -------
    pandas.DataFrame
        Side-specific waveform QC rows that can be passed to
        ``build_metric_qc_summary(trace_qc_summary=...)``.
    """

    records = _read_table(event_station_records)
    try:
        config = cfg or active_config()
    except Exception:
        config = None
    metric_settings = metrics_settings_from_config(config) if config is not None and (components is None or passbands is None) else None
    if components is not None:
        resolved_components = tuple(components)
    elif metric_settings is not None:
        resolved_components = tuple(metric_settings.components)
    else:
        resolved_components = ("Z",)
    if passbands is not None:
        resolved_passbands = tuple(passbands)
    elif metric_settings is not None:
        resolved_passbands = tuple(metric_settings.passbands)
    else:
        resolved_passbands = ()
    qc_settings = dict(config.section("qc.automatic", {}) or {}) if config is not None else {}
    resolved_min_record_length_s = float(min_record_length_s if min_record_length_s is not None else qc_settings.get("min_record_length_s", 60.0))
    resolved_min_end_after_origin_s = float(
        min_end_after_origin_s if min_end_after_origin_s is not None else qc_settings.get("min_end_after_origin_s", 60.0)
    )
    resolved_snr_threshold = float(snr_threshold if snr_threshold is not None else qc_settings.get("snr_threshold", 3.0))

    rows: list[pd.DataFrame] = []
    source_checkpoint_paths: list[Path] = []
    source_columns = waveform_path_columns or {}
    _progress(
        verbose,
        "Waveform QC: "
        f"{len(records)} event-station row(s), {len(tuple(sources))} source(s), "
        f"{len(tuple(resolved_components))} component(s), {len(tuple(resolved_passbands))} passband(s)",
    )
    for source in sources:
        source_start = time.monotonic()
        source_key = str(source).strip().lower()
        explicit_column = source_columns.get(source_key)
        source_records, path_column = _waveform_path_records_and_column(
            records,
            source_key,
            explicit_column=explicit_column,
        )
        source_preprocessing = preprocessing
        if source_preprocessing is None and path_column.endswith("_processed_waveform") and not apply_config_preprocessing_to_processed_files:
            source_preprocessing = WaveformPreprocessing()
        _progress(verbose, f"Waveform QC: source {source_key!r} using column {path_column!r}")
        source_checkpoint = _source_checkpoint_path(checkpoint_path, source_key)
        if source_checkpoint is not None:
            source_checkpoint_paths.append(source_checkpoint)
            _progress(verbose, f"Waveform QC: source {source_key!r} checkpoint path {source_checkpoint}")
        else:
            _progress(verbose, f"Waveform QC: source {source_key!r} checkpointing disabled")
        source_result = build_waveform_trace_qc_summary(
            source_records,
            source=source_key,
            waveform_path_col=path_column,
            components=resolved_components,
            passbands=resolved_passbands,
            preprocessing=source_preprocessing,
            min_record_length_s=resolved_min_record_length_s,
            min_end_after_origin_s=resolved_min_end_after_origin_s,
            snr_threshold=resolved_snr_threshold,
            arrival_pick_catalog=arrival_pick_catalog,
            onset_phase=onset_phase,
            min_onset_pick_probability=min_onset_pick_probability,
            verbose=verbose,
            progress_interval=progress_interval,
            checkpoint_path=source_checkpoint,
            resume=resume,
            checkpoint_interval=checkpoint_interval,
        )
        _progress(
            verbose,
            f"Waveform QC: source {source_key!r} complete "
            f"({len(source_result)} row(s), elapsed {_format_duration(time.monotonic() - source_start)})",
        )
        if return_result:
            rows.append(source_result)
        del source_result
    if return_result:
        result = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
        _write_qc_checkpoint(result, checkpoint_path)
        _progress(verbose, f"Waveform QC: built {len(result)} row(s)")
        return result
    if checkpoint_path is not None:
        _combine_csv_checkpoints(source_checkpoint_paths, checkpoint_path)
        _progress(verbose, f"Waveform QC: wrote combined checkpoint {checkpoint_path}")
    return pd.DataFrame()


def build_comparison_eligibility(qc_summary: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Return rows where observed and synthetic QC both pass.

    Parameters
    ----------
    qc_summary
        Side-specific QC summary table.

    Returns
    -------
    pandas.DataFrame
        Comparison-eligible event/station/component/passband/metric rows.
    """

    qc = _read_table(qc_summary).copy()
    key_columns = ["event_id", "station", "component", "passband", "metric_group", "metric", "period_s"]
    for column in key_columns + ["source", "qc_status"]:
        if column not in qc.columns:
            raise KeyError(f"QC summary is missing required column: {column}")
    observed = qc.loc[qc["source"].astype(str).str.lower().eq("observed")].copy()
    synthetic = qc.loc[qc["source"].astype(str).str.lower().eq("synthetic")].copy()
    eligible = observed.merge(synthetic, on=key_columns, suffixes=("_observed", "_synthetic"))
    eligible = eligible.loc[
        eligible["qc_status_observed"].astype(str).str.lower().eq("pass")
        & eligible["qc_status_synthetic"].astype(str).str.lower().eq("pass")
    ].copy()
    eligible = _coalesce_common_columns(eligible, _COMPARISON_METADATA_COLUMNS)
    return eligible.reset_index(drop=True)


def build_qc_availability_table(
    event_station_records: pd.DataFrame | str | Path,
    *,
    qc_summary: pd.DataFrame | str | Path | None = None,
    qc_aggregate: str = "all_pass",
    observed_root: str | Path | None = None,
    synthetic_root: str | Path | None = None,
    observed_inventory: pd.DataFrame | str | Path | None = None,
    synthetic_inventory: pd.DataFrame | str | Path | None = None,
    cfg: SpatialVTKConfig | None = None,
) -> pd.DataFrame:
    """Build observed/synthetic availability rows for QC figures.

    Parameters
    ----------
    event_station_records
        Event-station table.
    qc_summary
        Optional side-specific QC summary. When provided, availability is based
        on post-QC retained rows instead of file presence.
    qc_aggregate
        ``"all_pass"`` marks a side available only if all matching QC rows pass.
        ``"any_pass"`` marks a side available when at least one matching row
        passes.
    observed_root, synthetic_root
        Optional roots used to inventory files when inventory tables are not
        already available. When omitted, the active config's
        ``paths.observed_root`` and ``paths.synthetic_root`` are used when
        present.
    observed_inventory, synthetic_inventory
        Optional file inventory tables.
    cfg
        Optional config object used to resolve default roots.

    Returns
    -------
    pandas.DataFrame
        Availability table with one row per event/station.
    """

    records = _read_table(event_station_records).drop_duplicates(["event_id", "station"]).copy()
    out = records[["event_id", "station"]].copy()
    if qc_summary is not None:
        return _qc_availability_from_summary(out, qc_summary, aggregate=qc_aggregate)

    config = cfg or active_config()
    resolved_observed_root = observed_root or config.path("paths.observed_root")
    resolved_synthetic_root = synthetic_root or config.path("paths.synthetic_root")
    observed_events = _event_ids_from_inventory(observed_inventory, resolved_observed_root, dataset="observed")
    synthetic_events = _event_ids_from_inventory(synthetic_inventory, resolved_synthetic_root, dataset="synthetic")
    out["observed_available"] = out["event_id"].astype(str).isin(observed_events) if observed_events else True
    out["synthetic_available"] = out["event_id"].astype(str).isin(synthetic_events) if synthetic_events else True
    return out


def build_post_qc_record_table(
    event_station_records: pd.DataFrame | str | Path,
    *,
    events: pd.DataFrame | str | Path | None = None,
    qc_summary: pd.DataFrame | str | Path | None = None,
) -> pd.DataFrame:
    """Build station-event records for post-QC map figures.

    Parameters
    ----------
    event_station_records
        Event-station table with station coordinates.
    events
        Optional event metadata with event coordinates.
    qc_summary
        Optional QC summary used to assign pass/fail status per event/station.

    Returns
    -------
    pandas.DataFrame
        Records with ``sta_lat``, ``sta_lon``, event coordinates, and
        ``qc_status``.
    """

    records = _read_table(event_station_records).copy()
    out = records.rename(columns={"station_lat": "sta_lat", "station_lon": "sta_lon"})
    if events is not None:
        event_df = _read_table(events)
        keep = [column for column in ("event_id", "event_lat", "event_lon", "magnitude") if column in event_df.columns]
        out = out.merge(event_df[keep].drop_duplicates("event_id"), on="event_id", how="left")
    out = _coalesce_common_columns(out, ["event_lat", "event_lon", "magnitude"])
    out["qc_status"] = "pass"
    if qc_summary is not None:
        qc = _read_table(qc_summary).copy()
        status = (
            qc.assign(is_pass=qc["qc_status"].astype(str).str.lower().eq("pass"))
            .groupby(["event_id", "station"], as_index=False)["is_pass"]
            .any()
        )
        status["qc_status"] = np.where(status["is_pass"], "pass", "fail")
        out = out.merge(status[["event_id", "station", "qc_status"]], on=["event_id", "station"], how="left", suffixes=("", "_from_qc"))
        out["qc_status"] = out["qc_status_from_qc"].fillna(out["qc_status"])
        out.drop(columns=["qc_status_from_qc"], inplace=True)
    return out


def _coalesce_common_columns(df: pd.DataFrame, base_columns: Sequence[str]) -> pd.DataFrame:
    """Coalesce merge-suffixed columns back to public column names."""

    out = df.copy()
    for base in base_columns:
        candidates = [base, f"{base}_observed", f"{base}_synthetic", f"{base}_x", f"{base}_y", f"{base}_event"]
        existing = [column for column in candidates if column in out.columns]
        if not existing:
            continue
        values = out[existing[0]].replace("", pd.NA)
        for column in existing[1:]:
            values = values.combine_first(out[column].replace("", pd.NA))
        out[base] = values
        drop_cols = [column for column in existing if column != base]
        if drop_cols:
            out = out.drop(columns=drop_cols)
    return out


def build_retention_figure_table(qc_summary: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Prepare QC rows for retention summary figures.

    Parameters
    ----------
    qc_summary
        Metric QC summary table.

    Returns
    -------
    pandas.DataFrame
        Copy with ``stage`` set to passband labels.
    """

    qc = _read_table(qc_summary).copy()
    qc["stage"] = qc["passband"] if "passband" in qc.columns else "qc"
    return qc


def build_metric_pair_retention_table(
    qc_summary: pd.DataFrame | str | Path,
    *,
    group_cols: Sequence[str] = ("metric", "passband"),
) -> pd.DataFrame:
    """Summarize post-QC observed/synthetic pair retention.

    Parameters
    ----------
    qc_summary
        Side-specific metric QC table with observed and synthetic rows.
    group_cols
        Columns used to group retention percentages, usually metric and
        passband.

    Returns
    -------
    pandas.DataFrame
        Pair-retention rows with total pairs before QC, retained pairs after
        QC, and retained percentage.
    """

    pairs = _comparison_pair_table(qc_summary)
    if pairs.empty:
        return pd.DataFrame(columns=[*group_cols, "total_pairs", "retained_pairs", "retention_percent"])
    groups = [column for column in group_cols if column in pairs.columns]
    if not groups:
        groups = ["metric"]
    out = (
        pairs.groupby(groups, dropna=False)
        .agg(total_pairs=("is_retained_pair", "size"), retained_pairs=("is_retained_pair", "sum"))
        .reset_index()
    )
    out["retention_percent"] = np.where(out["total_pairs"] > 0, 100.0 * out["retained_pairs"] / out["total_pairs"], np.nan)
    return out.sort_values(groups, kind="stable").reset_index(drop=True)


def build_event_station_pair_retention_table(qc_summary: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Summarize comparison-pair retention for each event-station pair.

    Parameters
    ----------
    qc_summary
        Side-specific metric QC table with observed and synthetic rows.

    Returns
    -------
    pandas.DataFrame
        One row per event/station with total comparison pairs, retained pairs,
        and retained percentage across all components, passbands, and metrics.
    """

    pairs = _comparison_pair_table(qc_summary)
    columns = ["event_id", "station", "total_pairs", "retained_pairs", "retention_percent"]
    if pairs.empty:
        return pd.DataFrame(columns=columns)
    out = (
        pairs.groupby(["event_id", "station"], dropna=False)
        .agg(total_pairs=("is_retained_pair", "size"), retained_pairs=("is_retained_pair", "sum"))
        .reset_index()
    )
    out["retention_percent"] = np.where(out["total_pairs"] > 0, 100.0 * out["retained_pairs"] / out["total_pairs"], np.nan)
    return out.sort_values(["event_id", "station"], kind="stable").reset_index(drop=True)


def _comparison_pair_table(qc_summary: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Return observed/synthetic QC rows merged at comparison-pair grain."""

    qc = _read_table(qc_summary).copy()
    key_columns = ["event_id", "station", "component", "passband", "metric_group", "metric", "period_s"]
    for column in key_columns + ["source", "qc_status"]:
        if column not in qc.columns:
            raise KeyError(f"QC summary is missing required column: {column}")
    observed = qc.loc[qc["source"].astype(str).str.lower().eq("observed"), key_columns + ["qc_status"]].copy()
    synthetic = qc.loc[qc["source"].astype(str).str.lower().eq("synthetic"), key_columns + ["qc_status"]].copy()
    pairs = observed.merge(synthetic, on=key_columns, how="inner", suffixes=("_observed", "_synthetic"))
    pairs["is_retained_pair"] = (
        pairs["qc_status_observed"].astype(str).str.lower().eq("pass")
        & pairs["qc_status_synthetic"].astype(str).str.lower().eq("pass")
    )
    return pairs


def build_qc_waveform_comparison_records(
    event_station_records: pd.DataFrame | str | Path,
    qc_summary: pd.DataFrame | str | Path | None = None,
    *,
    comparison_eligible: pd.DataFrame | str | Path | None = None,
    component: str = "Z",
    passband: str | None = None,
    event_id: str | list[str] | tuple[str, ...] | None = None,
    max_distance_km: float | None = 50.0,
    max_records: int | None = 12,
    observed_waveform_col: str = "observed_processed_waveform",
    synthetic_waveform_col: str = "synthetic_processed_waveform",
) -> pd.DataFrame:
    """Build post-QC waveform rows for observed/synthetic visual inspection.

    Parameters
    ----------
    event_station_records
        Prepared event-station table with waveform paths.
    qc_summary
        Side-specific QC table. Used to build comparison-eligible rows when
        ``comparison_eligible`` is not supplied.
    comparison_eligible
        Optional precomputed output from :func:`build_comparison_eligibility`.
    component
        Component to load for the visual comparison.
    passband
        Optional retained passband to select.
    event_id
        Optional event ID or IDs to select before loading waveforms.
    max_distance_km
        Optional distance limit in kilometers.
    max_records
        Optional maximum retained event-station rows to load.
    observed_waveform_col, synthetic_waveform_col
        Waveform path columns in ``event_station_records``.

    Returns
    -------
    pandas.DataFrame
        Rows with observed and synthetic trace objects, sample intervals,
        event-origin offsets, and distance metadata.
    """

    if comparison_eligible is None:
        if qc_summary is None:
            raise ValueError("Provide qc_summary or comparison_eligible.")
        eligible = build_comparison_eligibility(qc_summary)
    else:
        eligible = _read_table(comparison_eligible)
    records = _read_table(event_station_records).copy()
    if observed_waveform_col not in records.columns or synthetic_waveform_col not in records.columns:
        raise KeyError(f"event_station_records must include {observed_waveform_col!r} and {synthetic_waveform_col!r}.")
    component_key = str(component).strip().upper()
    if "component" not in eligible.columns:
        raise KeyError("comparison_eligible must include a 'component' column.")
    eligible = eligible.loc[eligible["component"].astype(str).str.upper().eq(component_key)].copy()
    if passband is not None and "passband" in eligible.columns:
        eligible = eligible.loc[eligible["passband"].astype(str).eq(str(passband))].copy()
    if event_id is not None:
        event_ids = {str(value) for value in ([event_id] if isinstance(event_id, str) else event_id)}
        eligible = eligible.loc[eligible["event_id"].astype(str).isin(event_ids)].copy()
    key = ["event_id", "station"]
    for column in key:
        if column not in eligible.columns or column not in records.columns:
            raise KeyError(f"comparison_eligible and event_station_records must include {column!r}.")
    if eligible.empty:
        return pd.DataFrame(
            columns=[
                "event_id",
                "event_name",
                "station",
                "component",
                "passband",
                "distance_km",
                "sta_lat",
                "sta_lon",
                "event_lat",
                "event_lon",
                "observed",
                "synthetic",
                "dt",
                "synthetic_dt",
                "observed_time_offset_s",
                "synthetic_time_offset_s",
            ]
        )
    selected = eligible[key + [column for column in ("component", "passband", "distance_km") if column in eligible.columns]].drop_duplicates(key)
    merged = selected.merge(records, on=key, how="left", suffixes=("", "_record"))
    merged = _coalesce_common_columns(merged, ["distance_km"])
    if max_distance_km is not None and "distance_km" in merged.columns:
        merged["distance_km"] = pd.to_numeric(merged["distance_km"], errors="coerce")
        merged = merged.loc[merged["distance_km"].le(float(max_distance_km))].copy()
    if "distance_km" in merged.columns:
        merged = merged.sort_values(["distance_km", "event_id", "station"], kind="stable")
    if max_records is not None:
        merged = merged.head(int(max_records))
    rows: list[dict[str, object]] = []
    waveform_cache: dict[str, object] = {}
    for _, row in merged.iterrows():
        observed_path = str(row.get(observed_waveform_col, "") or "").strip()
        synthetic_path = str(row.get(synthetic_waveform_col, "") or "").strip()
        if not observed_path or not synthetic_path:
            continue
        try:
            observed_trace = select_waveform_trace(_cached_loaded_waveform(observed_path, waveform_cache), station=row.get("station"), component=component_key)
            synthetic_trace = select_waveform_trace(_cached_loaded_waveform(synthetic_path, waveform_cache), station=row.get("station"), component=component_key)
        except Exception:
            continue
        origin = _event_origin_time(row)
        rows.append(
            {
                "event_id": row.get("event_id", ""),
                "event_name": row.get("event_name", row.get("event_title", "")),
                "station": row.get("station", ""),
                "component": component_key,
                "passband": row.get("passband", passband or ""),
                "distance_km": row.get("distance_km", np.nan),
                "sta_lat": _first_present(row, "sta_lat", "station_lat", "lat", "lat_x", "lat_y"),
                "sta_lon": _first_present(row, "sta_lon", "station_lon", "lon", "lon_x", "lon_y"),
                "event_lat": _first_present(row, "event_lat", "event_lat_event", "source_lat"),
                "event_lon": _first_present(row, "event_lon", "event_lon_event", "source_lon"),
                "observed": observed_trace,
                "synthetic": synthetic_trace,
                "dt": _trace_dt(observed_trace),
                "synthetic_dt": _trace_dt(synthetic_trace),
                "observed_time_offset_s": _trace_offset_s(observed_trace, origin),
                "synthetic_time_offset_s": _trace_offset_s(synthetic_trace, origin),
            }
        )
    return pd.DataFrame(rows)


def export_manual_review_queue(
    qc_summary: pd.DataFrame | str | Path,
    output_path: str | Path | None = None,
    *,
    cfg: SpatialVTKConfig | None = None,
) -> Path:
    """Write a manual-review queue from QC summary rows.

    Parameters
    ----------
    qc_summary
        Metric QC summary table.
    output_path
        CSV or JSON output path. When omitted, the standard
        ``manual_review_queue`` output path is resolved from the active config.
    cfg
        Optional config object used when resolving the default output path.

    Returns
    -------
    pathlib.Path
        Written queue path.
    """

    resolved_path = output_path or resolve_output_path("manual_review_queue", kind="table", cfg=cfg, create_parent=True)
    return write_manual_review_queue(_read_table(qc_summary), resolved_path)


def _read_table(value: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Read a dataframe, CSV, or Parquet table."""

    if isinstance(value, pd.DataFrame):
        return value.copy()
    path = Path(value).expanduser()
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _waveform_path_records_and_column(
    records: pd.DataFrame,
    source: str,
    *,
    explicit_column: str | None = None,
) -> tuple[pd.DataFrame, str]:
    """Return records and a source path column, coalescing default candidates."""

    if explicit_column:
        if explicit_column not in records.columns:
            raise KeyError(f"Configured waveform path column {explicit_column!r} is missing for source {source!r}.")
        return records, explicit_column

    candidates = _waveform_path_column_candidates(source)
    existing = [column for column in candidates if column in records.columns]
    usable = [column for column in existing if _column_has_path_values(records[column])]
    if not usable:
        tried = ", ".join(candidates)
        raise KeyError(f"Could not find a waveform path column with paths for source {source!r}. Tried: {tried}")
    if len(usable) == 1:
        return records, usable[0]

    coalesced = records.copy()
    column = f"__svtk_{source}_waveform_path"
    values: list[str] = []
    for _, row in records.iterrows():
        text = ""
        for candidate in usable:
            text = _path_cell_text(row.get(candidate, ""))
            if text:
                break
        values.append(text)
    coalesced[column] = values
    return coalesced, column


def _waveform_path_column_candidates(source: str) -> tuple[str, ...]:
    """Return preferred waveform path columns for one source."""

    return (
        f"{source}_processed_waveform",
        f"{source}_waveform",
        f"{source}_mseed",
        f"{source}_pickle",
        f"{source}_raw_waveform",
    )


def _column_has_path_values(series: pd.Series) -> bool:
    """Return whether a path column has at least one non-empty path value."""

    return any(_path_cell_text(value) for value in series)


def _path_cell_text(value: object) -> str:
    """Return one waveform path cell as text, treating missing values as blank."""

    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    return "" if text.lower() in {"", "nan", "none", "null"} else text


def _period_band_label(passband: str | Sequence[float]) -> str:
    """Return a public period-band label."""

    if isinstance(passband, str):
        numbers = re.findall(r"\d*\.?\d+(?:[eE][-+]?\d+)?", passband)
        if len(numbers) >= 2:
            return f"{float(numbers[0]):g}-{float(numbers[1]):g} sec"
        return passband
    if len(passband) != 2:
        raise ValueError(f"Passband entries must be strings or two-value period ranges; got {passband!r}.")
    return f"{float(passband[0]):g}-{float(passband[1]):g} sec"


def _source_available(record: pd.Series, source: str, *, default: bool) -> bool:
    """Return source availability for one event-station record."""

    candidates = [f"{source}_available", f"{source}_exists", f"has_{source}"]
    for column in candidates:
        if column in record.index:
            value = record.get(column)
            if pd.isna(value):
                return default
            return str(value).strip().lower() not in {"0", "false", "no", "n", "missing", "nan", ""}
    return default


def _first_present(record: pd.Series, *columns: str) -> object:
    """Return the first present, non-empty value from a row."""

    for column in columns:
        if column not in record.index:
            continue
        value = record.get(column)
        if pd.isna(value) or str(value).strip() == "":
            continue
        return value
    return ""


def _event_origin_time(record: pd.Series) -> pd.Timestamp | None:
    """Resolve event origin time from common event-station columns.

    Parameters
    ----------
    record
        Event-station row.

    Returns
    -------
    pandas.Timestamp | None
        Parsed UTC event origin time, when available.
    """

    for column in ("start", "origin_time", "event_time", "time"):
        if column not in record.index:
            continue
        value = record.get(column)
        if pd.isna(value) or str(value).strip() == "":
            continue
        timestamp = pd.to_datetime(value, errors="coerce", utc=True)
        if not pd.isna(timestamp):
            return timestamp
    return None


def _qc_status(
    *,
    source: str,
    available: bool,
    metric_group: str,
    period_s: float,
    synthetic_max_frequency_hz: float | None,
) -> tuple[str, str]:
    """Return QC status and reason for one side/metric/period row."""

    if not available:
        return "fail", f"missing_{source}_waveform"
    if source == "synthetic" and metric_group == "spectral" and synthetic_max_frequency_hz:
        min_period_s = 1.0 / float(synthetic_max_frequency_hz)
        if np.isfinite(period_s) and float(period_s) < min_period_s:
            return "fail", "period_below_synthetic_min_period"
    return "pass", ""


def _trace_qc_lookup(trace_qc_summary: pd.DataFrame | str | Path | None) -> dict[tuple[str, str, str, str, str], dict[str, object]]:
    """Build a lookup for side-specific waveform QC rows."""

    if trace_qc_summary is None:
        return {}
    qc = _read_table(trace_qc_summary).copy()
    required = ["source", "event_id", "station", "component", "passband", "qc_status", "qc_reason"]
    missing = [column for column in required if column not in qc.columns]
    if missing:
        raise KeyError(f"Trace QC summary is missing required columns: {missing}")
    lookup: dict[tuple[str, str, str, str, str], dict[str, object]] = {}
    for _, row in qc.iterrows():
        key = (
            str(row.get("source", "")).strip().lower(),
            str(row.get("event_id", "")).strip(),
            str(row.get("station", "")).strip().upper(),
            str(row.get("component", "")).strip().upper(),
            _period_band_label(str(row.get("passband", ""))),
        )
        status = str(row.get("qc_status", "")).strip().lower() or "pass"
        reason = str(row.get("qc_reason", "") if not pd.isna(row.get("qc_reason", "")) else "").strip()
        if key not in lookup or status == "fail":
            payload = row.to_dict()
            payload["qc_status"] = status
            payload["qc_reason"] = reason
            lookup[key] = payload
    return lookup


def _trace_qc_payload(
    trace_qc: dict[tuple[str, str, str, str, str], dict[str, object]],
    *,
    source: str,
    event_id: object,
    station: object,
    component: object,
    passband: str,
) -> dict[str, object]:
    """Return waveform-level QC payload for one metric-QC row."""

    if not trace_qc:
        return {}
    key = (
        str(source).strip().lower(),
        str(event_id).strip(),
        str(station).strip().upper(),
        str(component).strip().upper(),
        _period_band_label(passband),
    )
    return trace_qc.get(key, {})


def _apply_trace_qc(
    trace_payload: dict[str, object],
    *,
    current_status: str,
    current_reason: str,
) -> tuple[str, str]:
    """Apply waveform-level QC to one metric-QC row."""

    if not trace_payload:
        return current_status, current_reason
    trace_status = str(trace_payload.get("qc_status", "")).strip().lower() or "pass"
    trace_reason = str(trace_payload.get("qc_reason", "") if not pd.isna(trace_payload.get("qc_reason", "")) else "").strip()
    if str(trace_status).strip().lower() == "fail":
        return "fail", trace_reason or "trace_qc_failed"
    return current_status, current_reason


def _event_ids_from_inventory(
    inventory: pd.DataFrame | str | Path | None,
    root: str | Path | None,
    *,
    dataset: str,
) -> set[str]:
    """Infer event IDs from an inventory table or waveform root."""

    if inventory is None and root is not None:
        inventory = build_file_inventory(root, dataset=dataset, include_sha256=False)
    if inventory is None:
        return set()
    table = _read_table(inventory)
    event_ids: set[str] = set()
    for column in ("event_id", "filename", "path"):
        if column not in table.columns:
            continue
        for value in table[column].dropna().astype(str):
            match = re.search(r"(ci\\d+)", value)
            event_ids.add(match.group(1) if match else Path(value).stem)
    return event_ids


def _cached_loaded_waveform(path: str | Path, cache: dict[str, object]) -> object:
    """Load one waveform file with a small local cache.

    Parameters
    ----------
    path
        Waveform file path.
    cache
        Mutable cache keyed by expanded path string.

    Returns
    -------
    object
        Loaded waveform object.
    """

    key = str(Path(path).expanduser())
    if key not in cache:
        cache[key] = read_waveform_file(key)
    return cache[key]


def _trace_dt(trace: object) -> float:
    """Return the sample interval from one trace-like object.

    Parameters
    ----------
    trace
        ObsPy-like or mapping trace.

    Returns
    -------
    float
        Sample interval in seconds.
    """

    stats = _trace_stats(trace)
    value = _stat_value(stats, "delta", None)
    if value in (None, ""):
        sampling_rate = _stat_value(stats, "sampling_rate", None)
        value = 1.0 / float(sampling_rate) if sampling_rate not in (None, "", 0) else np.nan
    try:
        out = float(value)
    except Exception:
        out = np.nan
    return out if np.isfinite(out) and out > 0.0 else np.nan


def _trace_offset_s(trace: object, origin: pd.Timestamp | None) -> float:
    """Return trace start time relative to event origin.

    Parameters
    ----------
    trace
        ObsPy-like or mapping trace.
    origin
        Event origin time.

    Returns
    -------
    float
        Seconds from event origin to trace start, or zero when unavailable.
    """

    if origin is None:
        return 0.0
    start = _stat_value(_trace_stats(trace), "starttime", None)
    timestamp = pd.to_datetime(str(start), errors="coerce", utc=True) if start not in (None, "") else pd.NaT
    if pd.isna(timestamp):
        return 0.0
    return float((timestamp - origin).total_seconds())


def _trace_stats(trace: object) -> object:
    """Return stats metadata from trace-like objects."""

    if isinstance(trace, dict):
        return trace.get("stats", trace)
    return getattr(trace, "stats", None)


def _stat_value(stats: object, key: str, default: object = None) -> object:
    """Read one trace metadata value from mapping or attribute stats."""

    if stats is None:
        return default
    if isinstance(stats, dict):
        return stats.get(key, default)
    return getattr(stats, key, default)


def _qc_availability_from_summary(
    event_station_rows: pd.DataFrame,
    qc_summary: pd.DataFrame | str | Path,
    *,
    aggregate: str,
) -> pd.DataFrame:
    """Build post-QC event/station availability from side-specific QC rows."""

    qc = _read_table(qc_summary).copy()
    required = {"source", "event_id", "station", "qc_status"}
    missing = sorted(required - set(qc.columns))
    if missing:
        raise KeyError(f"QC summary is missing required columns: {missing}")
    aggregate_key = str(aggregate).strip().lower()
    if aggregate_key not in {"all_pass", "any_pass"}:
        raise ValueError("qc_aggregate must be 'all_pass' or 'any_pass'.")
    qc["_is_pass"] = qc["qc_status"].astype(str).str.lower().eq("pass")
    reducer = "all" if aggregate_key == "all_pass" else "any"
    side_status = (
        qc.assign(
            source=qc["source"].astype(str).str.lower(),
            station=qc["station"].astype(str).str.upper(),
            event_id=qc["event_id"].astype(str),
        )
        .groupby(["event_id", "station", "source"], as_index=False)["_is_pass"]
        .agg(reducer)
    )
    observed = side_status.loc[side_status["source"].eq("observed"), ["event_id", "station", "_is_pass"]].rename(columns={"_is_pass": "observed_available"})
    synthetic = side_status.loc[side_status["source"].eq("synthetic"), ["event_id", "station", "_is_pass"]].rename(columns={"_is_pass": "synthetic_available"})
    out = event_station_rows.copy()
    out["event_id"] = out["event_id"].astype(str)
    out["station"] = out["station"].astype(str).str.upper()
    out = out.merge(observed, on=["event_id", "station"], how="left")
    out = out.merge(synthetic, on=["event_id", "station"], how="left")
    out["observed_available"] = out["observed_available"].fillna(False).astype(bool)
    out["synthetic_available"] = out["synthetic_available"].fillna(False).astype(bool)
    return out


__all__ = [
    "build_comparison_eligibility",
    "build_metric_pair_retention_table",
    "build_metric_qc_summary",
    "build_post_qc_record_table",
    "build_qc_waveform_comparison_records",
    "build_qc_availability_table",
    "build_retention_figure_table",
    "build_waveform_qc_summary",
    "export_manual_review_queue",
]
