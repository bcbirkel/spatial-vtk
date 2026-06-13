"""Inventory helpers for quality-control dataset construction."""

from __future__ import annotations

import math
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from spatial_vtk.io.tables import write_table
from spatial_vtk.io.waveforms import (
    WaveformPreprocessing,
    apply_waveform_preprocessing_with_metadata,
    read_waveform_file,
    select_waveform_trace,
    trace_metadata_table,
    waveform_preprocessing_from_config,
)
from spatial_vtk.metrics.calculate.arrival_picks import load_arrival_pick_catalog, normalize_pick_catalog
from spatial_vtk.qc.build.filtering import band_key_from_label
from spatial_vtk.qc.summary.rules import (
    INVENTORY_REJECT_REASON_CODES,
    INVENTORY_STANDARD_BANDS,
    classify_station_family,
    global_trace_reject_reasons,
    reject_passband,
)

PROCESSING_EDGE_FRACTION = 0.05
TRACE_UNAVAILABLE_REASONS = {
    "missing_waveform_path",
    "missing_waveform_file",
    "waveform_read_error",
    "missing_station",
    "missing_component",
    "missing_trace",
}


def discover_event_ids(*roots: str | Path) -> list[str]:
    """Discover candidate event IDs from one or more observed-data roots.

    Parameters
    ----------
    *roots
        Directories containing event files or event subdirectories.

    Returns
    -------
    list of str
        Sorted unique event identifiers.
    """

    event_ids: set[str] = set()
    for root in roots:
        root_path = Path(root).expanduser()
        if not root_path.exists():
            continue
        for path in root_path.iterdir():
            if path.name.startswith("."):
                continue
            if path.is_dir():
                event_ids.add(path.name)
            elif path.suffix.lower() in {".json", ".csv", ".pkl", ".mseed", ".h5", ".hdf5", ".asdf"}:
                event_ids.add(path.stem)
    return sorted(event_ids)


def determine_available_components(stream: Any, station: str, components: tuple[str, ...] = ("N", "E", "Z", "R", "T")) -> list[str]:
    """Determine which requested components are available for one station.

    Parameters
    ----------
    stream
        ObsPy stream-like iterable with trace ``stats.station`` and
        ``stats.channel`` attributes.
    station
        Station code to inspect.
    components
        Component suffixes to search for.

    Returns
    -------
    list of str
        Components present in the stream for the station.
    """

    wanted = {str(component).upper() for component in components}
    station_key = str(station).strip().upper()
    found: set[str] = set()
    for trace in stream or []:
        stats = getattr(trace, "stats", None)
        if str(getattr(stats, "station", "")).strip().upper() != station_key:
            continue
        channel = str(getattr(stats, "channel", "")).strip().upper()
        component = channel[-1:] if channel else ""
        if component in wanted:
            found.add(component)
    return [component for component in components if str(component).upper() in found]


def companion_rows_from_master(
    master_rows: list[dict[str, object]] | pd.DataFrame,
    inventory_bands: list[tuple[str, float, float]] | None = None,
) -> list[dict[str, object]]:
    """Build per-event QC companion rows from master inventory rows.

    Parameters
    ----------
    master_rows
        Full master inventory rows.
    inventory_bands
        Inventory passbands as ``(label, period_min, period_max)`` tuples.

    Returns
    -------
    list of dict
        Per-event, per-variant, per-band summaries with distance-bin counts.
    """

    rows = master_rows.to_dict(orient="records") if isinstance(master_rows, pd.DataFrame) else list(master_rows)
    bands = inventory_bands or list(INVENTORY_STANDARD_BANDS)
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        for label, _period_min, _period_max in bands:
            grouped[(str(row.get("event_id", "")), str(row.get("observed_variant", "")), str(label))].append(row)

    out: list[dict[str, object]] = []
    for (event_id, observed_variant, passband_label), group_rows in sorted(grouped.items()):
        if not group_rows:
            continue
        band_key = band_key_from_label(passband_label)
        rejected_rows = [row for row in group_rows if _truthy(row.get(f"reject_{band_key}", False))]
        accepted_rows = [row for row in group_rows if not _truthy(row.get(f"reject_{band_key}", False))]
        total = len(group_rows)
        rejected = len(rejected_rows)
        reason_counts: Counter[str] = Counter()
        for row in rejected_rows:
            reasons = [text.strip() for text in str(row.get(f"reject_reason_{band_key}", "")).split(";") if text.strip()]
            reason_counts.update(reasons)

        finite_distances = [_safe_float(row.get("distance_km")) for row in group_rows]
        max_distance = max([value for value in finite_distances if value is not None], default=0.0)
        n_bins = int(math.ceil(max_distance / 10.0)) if max_distance > 0.0 else 1
        for bin_idx in range(n_bins):
            bin_start = float(bin_idx * 10.0)
            bin_end = float(bin_start + 10.0)
            in_bin = [
                row
                for row in group_rows
                if (distance := _safe_float(row.get("distance_km"))) is not None
                and distance >= bin_start
                and (distance < bin_end or (bin_idx == n_bins - 1 and distance <= bin_end))
            ]
            accepted_in_bin = [row for row in in_bin if not _truthy(row.get(f"reject_{band_key}", False))]
            mean_abs_values = [
                value
                for row in accepted_in_bin
                if (value := _safe_float(row.get(f"mean_abs_{band_key}"))) is not None
            ]
            companion = {
                "event_id": event_id,
                "event_title": str(group_rows[0].get("event_title", "")),
                "magnitude": group_rows[0].get("magnitude", ""),
                "observed_variant": observed_variant,
                "orientation_set": str(group_rows[0].get("orientation_set", "")),
                "passband": passband_label,
                "total_trace_count": total,
                "accepted_trace_count": len(accepted_rows),
                "accepted_trace_pct": (100.0 * len(accepted_rows) / total) if total else "",
                "rejected_trace_count": rejected,
                "distance_bin_start_km": bin_start,
                "distance_bin_end_km": bin_end,
                "distance_bin_label": f"{int(bin_start)}-{int(bin_end)}",
                "distance_bin_trace_count": len(in_bin),
                "distance_bin_accepted_trace_count": len(accepted_in_bin),
                "distance_bin_avg_mean_abs": float(np.mean(mean_abs_values)) if mean_abs_values else "",
            }
            for reason_code in INVENTORY_REJECT_REASON_CODES:
                companion[f"reject_reason_pct_{reason_code}"] = (100.0 * reason_counts.get(reason_code, 0) / rejected) if rejected else ""
            out.append(companion)
    return out


def build_trace_inventory(
    event_streams: dict[str, Any] | list[dict[str, Any]] | pd.DataFrame,
    *,
    observed_variant: str = "nonrotated",
    inventory_bands: list[tuple[str, float, float]] | None = None,
    min_record_length_s: float = 80.0,
    min_end_after_origin_s: float = 60.0,
    station_metadata: pd.DataFrame | None = None,
    event_metadata: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build a QC trace inventory from waveform streams or trace metadata.

    Parameters
    ----------
    event_streams
        Mapping from event ID to stream-like objects, list of records with
        ``event_id`` and ``stream`` fields, or precomputed trace metadata.
    observed_variant
        Label for the observed-data variant.
    inventory_bands
        Inventory passbands as ``(label, period_min, period_max)`` tuples.
    min_record_length_s
        Minimum accepted trace length in seconds.
    min_end_after_origin_s
        Minimum accepted trace end time relative to origin.
    station_metadata, event_metadata
        Optional metadata tables joined into the inventory.

    Returns
    -------
    pandas.DataFrame
        One row per trace with passband reject flags and reject reasons.
    """

    bands = inventory_bands or list(INVENTORY_STANDARD_BANDS)
    trace_df = _coerce_trace_metadata(event_streams, observed_variant=observed_variant)
    station_lookup = _metadata_lookup(station_metadata, key="station") if station_metadata is not None else {}
    event_lookup = _metadata_lookup(event_metadata, key="event_id") if event_metadata is not None else {}
    rows: list[dict[str, Any]] = []
    for _, row in trace_df.iterrows():
        station = str(row.get("station", "")).strip().upper()
        event_id = str(row.get("event_id", "")).strip()
        record_length_s = _record_length_s(row)
        end_rel_s = _end_relative_to_origin_s(row, event_lookup.get(event_id, {}))
        reject_global, reasons = global_trace_reject_reasons(
            record_length_s=record_length_s,
            end_rel_s=end_rel_s,
            onset_reasons=[],
            min_end_after_origin_s=min_end_after_origin_s,
            min_record_length_s=min_record_length_s,
        )
        out = {
            "event_id": event_id,
            "observed_variant": observed_variant,
            "network": row.get("network", ""),
            "station": station,
            "component": row.get("component", ""),
            "channel": row.get("channel", ""),
            "station_family": classify_station_family(row.get("network", ""), station),
            "record_length_s": record_length_s,
            "starttime": row.get("starttime", ""),
            "endtime": row.get("endtime", ""),
            "sampling_rate": row.get("sampling_rate", ""),
            "npts": row.get("npts", ""),
            "lat": row.get("lat", ""),
            "lon": row.get("lon", ""),
            "elev": row.get("elev", ""),
            "source": row.get("source", ""),
            "available": bool(station and event_id),
            "global_reject": reject_global,
            "global_reject_reason": ";".join(reasons),
        }
        out.update(_prefixed_metadata(station_lookup.get(station, {}), "station_meta"))
        out.update(_prefixed_metadata(event_lookup.get(event_id, {}), "event_meta"))
        for label, _period_min, _period_max in bands:
            suffix = band_key_from_label(label)
            out[f"reject_{suffix}"] = bool(reject_global)
            out[f"reject_reason_{suffix}"] = ";".join(reasons)
            out[f"mean_abs_{suffix}"] = ""
        rows.append(out)
    return pd.DataFrame(rows)


def build_waveform_trace_qc_summary(
    event_station_records: pd.DataFrame | str | Path,
    *,
    source: str = "observed",
    waveform_path_col: str = "observed_pickle",
    components: tuple[str, ...] | list[str] = ("Z",),
    passbands: tuple[str | tuple[float, float], ...] | list[str | tuple[float, float]] | None = None,
    preprocessing: WaveformPreprocessing | None = None,
    min_record_length_s: float = 60.0,
    min_end_after_origin_s: float = 60.0,
    snr_threshold: float = 3.0,
    noise_window_min_s: float = 1.0,
    signal_window_min_s: float = 10.0,
    noise_gap_s: float = 0.5,
    signal_gap_s: float = 0.5,
    origin_tolerance_s: float = 0.5,
    pre_origin_signal_ratio_threshold: float = 0.5,
    arrival_pick_catalog: pd.DataFrame | str | Path | None = None,
    onset_phase: str = "P",
    min_onset_pick_probability: float = 0.0,
    verbose: bool = False,
    progress_interval: int = 25,
    checkpoint_path: str | Path | None = None,
    resume: bool = True,
    checkpoint_interval: int = 25,
) -> pd.DataFrame:
    """Build side-specific trace QC rows from waveform files.

    Parameters
    ----------
    event_station_records
        Event-station records with event IDs, station codes, event origin
        times, and waveform paths.
    source
        Source label copied to the output, usually ``"observed"`` or
        ``"synthetic"``.
    waveform_path_col
        Column containing waveform files for this source.
    components
        Components to inspect.
    passbands
        Period bands to report. When omitted, the public inventory standard
        bands are used.
    preprocessing
        Optional waveform preprocessing applied before QC calculations.
    min_record_length_s
        Minimum trace duration in seconds.
    min_end_after_origin_s
        Minimum required trace end time relative to event origin.
    snr_threshold
        Minimum RMS signal-to-noise ratio.
    noise_window_min_s
        Minimum noise-window length in seconds.
    signal_window_min_s
        Minimum signal-window length in seconds.
    noise_gap_s
        Gap between detected onset and the noise window.
    signal_gap_s
        Gap between detected onset and the signal window.
    origin_tolerance_s
        Half-width of the origin energy check window.
    pre_origin_signal_ratio_threshold
        Maximum origin/pre-origin to signal RMS ratio.
    arrival_pick_catalog
        Optional PhaseNet-style pick catalog. When a finite pick exists for the
        requested onset phase, QC uses it as the signal onset; otherwise QC
        falls back to the waveform-envelope onset.
    onset_phase
        Pick phase used to anchor QC noise and signal windows.
    min_onset_pick_probability
        Minimum picker probability accepted for the QC onset pick.
    verbose
        Print progress messages while loading waveform files and building rows.
    progress_interval
        Number of event-station records between progress messages.
    checkpoint_path
        Optional table path where intermediate QC rows are written.
    resume
        When true and ``checkpoint_path`` exists, skip event/station/component
        groups already present in that checkpoint.
    checkpoint_interval
        Number of event-station records between checkpoint writes.

    Returns
    -------
    pandas.DataFrame
        Metric-QC-compatible rows with one row per
        source/event/station/component/passband.
    """

    records = _read_table(event_station_records).drop_duplicates(["event_id", "station"]).copy()
    bands = _normalize_qc_passbands(passbands)
    preprocessing = preprocessing if preprocessing is not None else waveform_preprocessing_from_config()
    pick_lookup = _arrival_pick_lookup(
        arrival_pick_catalog,
        phase=onset_phase,
        min_probability=min_onset_pick_probability,
    )
    checkpoint = _load_qc_checkpoint(checkpoint_path) if resume else pd.DataFrame()
    if checkpoint_path is not None and not resume:
        _reset_qc_checkpoint(checkpoint_path)
    rows: list[dict[str, object]] = checkpoint.to_dict(orient="records") if not checkpoint.empty else []
    checkpoint_buffer: list[dict[str, object]] = []
    completed = _waveform_qc_completed_keys(checkpoint)
    stream_cache: dict[str, Any] = {}
    source_key = str(source).strip().lower()
    components_text = tuple(str(component).strip().upper() for component in components)
    total_records = len(records)
    progress_every = max(int(progress_interval), 1)
    checkpoint_every = max(int(checkpoint_interval), 1)
    progress_start = time.monotonic()
    progress_prefix = f"Trace QC {source_key}"
    _progress(
        verbose,
        f"{progress_prefix}: "
        f"{total_records} event-station record(s), {len(components_text)} component(s), {len(bands)} passband(s)",
    )
    pending_work: list[tuple[pd.Series, tuple[str, ...]]] = []
    for _, record in records.iterrows():
        event_id = str(record.get("event_id", "")).strip()
        station = str(record.get("station", "")).strip().upper()
        pending_components = tuple(
            component_text
            for component_text in components_text
            if (source_key, event_id, station, component_text) not in completed
        )
        if pending_components:
            pending_work.append((record, pending_components))
    pending_component_groups = sum(len(pending_components) for _, pending_components in pending_work)
    total_component_groups = total_records * len(components_text)
    if checkpoint_path is None:
        _progress(verbose, f"{progress_prefix}: checkpointing disabled; starting from scratch")
    else:
        _progress(verbose, f"{progress_prefix}: checkpoint path {Path(checkpoint_path).expanduser()}")
    if completed:
        completed_count = max(total_component_groups - pending_component_groups, 0)
        remaining_count = pending_component_groups
        _progress(
            verbose,
            f"{progress_prefix}: resuming with {completed_count} completed "
            f"{_plural(completed_count, 'component group')} "
            f"({completed_count}/{total_component_groups} complete; {remaining_count} "
            f"new {_plural(remaining_count, 'group')} remaining)",
        )
        if remaining_count == 0:
            _progress(verbose, f"{progress_prefix}: checkpoint already complete; returning cached rows")
            return pd.DataFrame(rows)
        _progress(
            verbose,
            f"{progress_prefix}: processing {remaining_count} new {_plural(remaining_count, 'component group')} "
            f"across {len(pending_work)} event-station {_plural(len(pending_work), 'record')}",
        )
    elif checkpoint_path is not None:
        _progress(verbose, f"{progress_prefix}: no completed component groups found; all work is new")
    total_pending_records = len(pending_work)
    for record_index, (record, pending_components) in enumerate(pending_work, start=1):
        if record_index == 1 or record_index % progress_every == 0 or record_index == total_pending_records:
            _progress(verbose, _progress_status(progress_prefix, record_index, total_pending_records, progress_start))
        event_id = str(record.get("event_id", "")).strip()
        station = str(record.get("station", "")).strip().upper()
        origin = _event_origin_time(record)
        path_text = _path_cell_text(record.get(waveform_path_col, ""))
        for component_text in pending_components:
            completed_key = (str(source).strip().lower(), event_id, station, component_text)
            trace = None
            load_reason = ""
            load_message = ""
            if not path_text:
                load_reason = "missing_waveform_path"
            else:
                try:
                    stream = _cached_waveform(
                        path_text,
                        stream_cache,
                        station=station,
                        component=component_text,
                    )
                except FileNotFoundError as exc:
                    load_reason = "missing_waveform_file"
                    load_message = str(exc)
                except Exception as exc:
                    load_reason = "waveform_read_error"
                    load_message = str(exc)
                else:
                    try:
                        trace = _select_trace(stream, station=station, component=component_text)
                    except Exception as exc:
                        load_reason = _trace_selection_failure_reason(stream, station=station, component=component_text)
                        load_message = str(exc)
            trace_summary = _trace_quality_summary(
                trace,
                origin=origin,
                preprocessing=preprocessing,
                min_record_length_s=min_record_length_s,
                min_end_after_origin_s=min_end_after_origin_s,
            )
            global_reasons = list(trace_summary.pop("global_reasons"))
            if load_reason:
                global_reasons = [load_reason]
            pick_onset_rel_s = _lookup_onset_pick(
                pick_lookup,
                source=source,
                event_id=event_id,
                station=station,
                component=component_text,
                phase=onset_phase,
            )
            for label, period_min_s, period_max_s in bands:
                band_summary = _passband_quality_summary(
                    trace_summary,
                    period_min_s=period_min_s,
                    period_max_s=period_max_s,
                    snr_threshold=snr_threshold,
                    noise_window_min_s=noise_window_min_s,
                    signal_window_min_s=signal_window_min_s,
                    noise_gap_s=noise_gap_s,
                    signal_gap_s=signal_gap_s,
                    origin_tolerance_s=origin_tolerance_s,
                    pre_origin_signal_ratio_threshold=pre_origin_signal_ratio_threshold,
                    global_reasons=global_reasons,
                    pick_onset_rel_s=pick_onset_rel_s,
                )
                if _trace_unavailable(global_reasons):
                    reject_flag, reasons = True, list(global_reasons)
                else:
                    reject_flag, reasons = reject_passband(
                        global_reasons=global_reasons,
                        snr_rms=float(band_summary["snr_rms"]),
                        snr_threshold=snr_threshold,
                        noise_window_valid=bool(band_summary["noise_window_valid"]),
                        signal_window_valid=bool(band_summary["signal_window_valid"]),
                        pre_origin_window_valid=bool(band_summary["pre_origin_window_valid"]),
                        pre_origin_signal_ratio=float(band_summary["pre_origin_signal_ratio"]),
                        pre_origin_signal_ratio_threshold=pre_origin_signal_ratio_threshold,
                        origin_window_valid=bool(band_summary["origin_window_valid"]),
                        origin_signal_ratio=float(band_summary["origin_signal_ratio"]),
                    )
                row = {
                    "source": str(source).strip().lower(),
                    "event_id": event_id,
                    "station": station,
                    "component": component_text,
                    "passband": _display_passband_label(label),
                    "metric_group": "",
                    "metric": "",
                    "period_s": np.nan,
                    "qc_status": "fail" if reject_flag else "pass",
                    "qc_reason": ";".join(reasons),
                    "record_length_s": trace_summary["record_length_s"],
                    "start_rel_s": trace_summary["start_rel_s"],
                    "end_rel_s": trace_summary["end_rel_s"],
                    "trace_start_s": trace_summary["start_rel_s"],
                    "trace_end_s": trace_summary["end_rel_s"],
                    "trace_duration_s": trace_summary["record_length_s"],
                    "valid_start_rel_s": trace_summary["valid_start_rel_s"],
                    "valid_end_rel_s": trace_summary["valid_end_rel_s"],
                    "valid_start_sample": trace_summary["valid_start_sample"],
                    "valid_end_sample": trace_summary["valid_end_sample"],
                    "sample_interval_s": trace_summary["dt"],
                    "sample_count": int(np.asarray(trace_summary.get("samples", [])).size),
                    "load_message": load_message,
                    "onset_rel_s": band_summary["onset_rel_s"],
                    "snr_rms": band_summary["snr_rms"],
                    "noise_rms": band_summary["noise_rms"],
                    "signal_rms": band_summary["signal_rms"],
                    "pre_origin_signal_ratio": band_summary["pre_origin_signal_ratio"],
                    "origin_signal_ratio": band_summary["origin_signal_ratio"],
                }
                rows.append(row)
                checkpoint_buffer.append(row)
            completed.add(completed_key)
        if checkpoint_path is not None and (record_index % checkpoint_every == 0 or record_index == total_pending_records):
            _append_qc_checkpoint_rows(checkpoint_buffer, checkpoint_path)
            checkpoint_buffer.clear()
    result = pd.DataFrame(rows)
    if checkpoint_buffer:
        _append_qc_checkpoint_rows(checkpoint_buffer, checkpoint_path)
    _progress(verbose, f"{progress_prefix}: built {len(result)} row(s) in {_format_duration(time.monotonic() - progress_start)}")
    return result


def _read_table(value: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Read a dataframe, CSV, or Parquet table.

    Parameters
    ----------
    value
        DataFrame or path to a CSV/Parquet table.

    Returns
    -------
    pandas.DataFrame
        Loaded table copy.
    """

    if isinstance(value, pd.DataFrame):
        return value.copy()
    path = Path(value).expanduser()
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path)


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


def _reset_qc_checkpoint(path: str | Path | None) -> None:
    """Remove one checkpoint table when a non-resume run should start fresh."""

    if path is None:
        return
    checkpoint = Path(path).expanduser()
    checkpoint.unlink(missing_ok=True)


def _append_qc_checkpoint_rows(rows: list[dict[str, object]], path: str | Path | None) -> None:
    """Append newly generated rows to one CSV checkpoint table."""

    if path is None or not rows:
        return
    checkpoint = Path(path).expanduser()
    suffix = checkpoint.suffix.lower()
    if suffix not in {"", ".csv"}:
        existing = _load_qc_checkpoint(checkpoint)
        combined = pd.concat([existing, pd.DataFrame(rows)], ignore_index=True) if not existing.empty else pd.DataFrame(rows)
        _write_qc_checkpoint(combined, checkpoint)
        return
    if not suffix:
        checkpoint = checkpoint.with_suffix(".csv")
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    write_header = not checkpoint.exists() or checkpoint.stat().st_size == 0
    pd.DataFrame(rows).to_csv(checkpoint, mode="a", header=write_header, index=False)


def _waveform_qc_completed_keys(df: pd.DataFrame) -> set[tuple[str, str, str, str]]:
    """Return completed source/event/station/component groups from a checkpoint."""

    required = {"source", "event_id", "station", "component"}
    if df.empty or not required <= set(df.columns):
        return set()
    return {
        (
            str(row["source"]).strip().lower(),
            str(row["event_id"]).strip(),
            str(row["station"]).strip().upper(),
            str(row["component"]).strip().upper(),
        )
        for _, row in df.loc[:, list(required)].drop_duplicates().iterrows()
    }


def _normalize_qc_passbands(passbands: tuple[str | tuple[float, float], ...] | list[str | tuple[float, float]] | None) -> list[tuple[str, float, float]]:
    """Normalize period-band settings to labels and period bounds.

    Parameters
    ----------
    passbands
        Period-band labels such as ``"1-2 sec"`` or two-value ranges.

    Returns
    -------
    list of tuple
        ``(label, period_min_s, period_max_s)`` tuples.
    """

    if passbands is None:
        return [(_display_passband_label(label), float(period_min), float(period_max)) for label, period_min, period_max in INVENTORY_STANDARD_BANDS]
    out: list[tuple[str, float, float]] = []
    for item in passbands:
        if isinstance(item, str):
            numbers = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", item)
            if len(numbers) < 2:
                raise ValueError(f"Passband label must contain two period bounds; got {item!r}.")
            period_min, period_max = float(numbers[0]), float(numbers[1])
            out.append((_display_passband_label(item), period_min, period_max))
        else:
            if len(item) != 2:
                raise ValueError(f"Passband entries must be strings or two-value ranges; got {item!r}.")
            period_min, period_max = float(item[0]), float(item[1])
            out.append((f"{period_min:g}-{period_max:g} sec", period_min, period_max))
    return out


def _display_passband_label(label: object) -> str:
    """Return a consistent public period-band label.

    Parameters
    ----------
    label
        Raw passband label.

    Returns
    -------
    str
        Label using ``sec`` units.
    """

    text = str(label).strip()
    numbers = re.findall(r"\d*\.?\d+(?:[eE][-+]?\d+)?", text)
    if len(numbers) >= 2:
        return f"{float(numbers[0]):g}-{float(numbers[1]):g} sec"
    if text.lower().endswith("s") and not text.lower().endswith("sec"):
        text = f"{text[:-1].strip()} sec"
    return text


def _event_origin_time(record: pd.Series) -> pd.Timestamp | None:
    """Resolve event origin time from common event-station columns.

    Parameters
    ----------
    record
        Event-station row.

    Returns
    -------
    pandas.Timestamp or None
        UTC origin timestamp when available.
    """

    for column in ("origin_time", "event_origin_time", "event_time", "time", "start", "event_start"):
        if column not in record.index:
            continue
        value = record.get(column)
        if pd.isna(value) or str(value).strip() == "":
            continue
        parsed = pd.to_datetime(value, utc=True, errors="coerce")
        if not pd.isna(parsed):
            return parsed
    return None


def _cached_waveform(path: str | Path, cache: dict[str, Any], *, station: str | None = None, component: str | None = None) -> Any:
    """Read one waveform file with a small path cache.

    Parameters
    ----------
    path
        Waveform path.
    cache
        Mutable cache keyed by resolved path text.

    Returns
    -------
    object
        Loaded waveform stream.
    """

    source = Path(path).expanduser()
    key = str(source)
    if source.suffix.lower() == ".asdf":
        key = f"{key}::{station or ''}"
    if key not in cache:
        if source.suffix.lower() == ".asdf":
            from spatial_vtk.io.synthetic_formats import (
                SyntheticFormatInfo,
                SyntheticReadRequest,
                synthetic_reader_for,
            )

            info = SyntheticFormatInfo(str(source), "asdf", True, False)
            cache[key] = synthetic_reader_for(info).read(
                SyntheticReadRequest(station=station)
            )
        else:
            cache[key] = read_waveform_file(source)
    return cache[key]


def _select_trace(stream: Any, *, station: str, component: str) -> Any:
    """Select one station/component trace from a stream.

    Parameters
    ----------
    stream
        Stream-like waveform object.
    station, component
        Trace selector values.

    Returns
    -------
    object
        Selected trace-like object.
    """

    return select_waveform_trace(stream, station=station, component=component)


def _trace_selection_failure_reason(stream: Any, *, station: str, component: str) -> str:
    """Classify why trace selection failed for a loaded waveform stream."""

    try:
        metadata = trace_metadata_table(stream)
    except Exception:
        return "missing_trace"
    if metadata.empty:
        return "missing_trace"
    station_key = str(station).strip().upper()
    component_key = str(component).strip().upper()
    stations = {
        str(value).strip().upper()
        for value in metadata.get("station", pd.Series(dtype=object)).dropna()
    }
    if station_key and station_key not in stations:
        return "missing_station"
    station_rows = metadata
    if station_key and "station" in metadata.columns:
        station_mask = metadata["station"].astype(str).str.strip().str.upper().eq(station_key)
        station_rows = metadata.loc[station_mask]
    components = {
        str(value).strip().upper()
        for value in station_rows.get("component", pd.Series(dtype=object)).dropna()
    }
    if component_key and component_key not in components:
        return "missing_component"
    return "missing_trace"


def _trace_unavailable(reasons: list[str]) -> bool:
    """Return whether passband window checks should be skipped."""

    return bool({str(reason).strip() for reason in reasons} & TRACE_UNAVAILABLE_REASONS)


def _trace_quality_summary(
    trace: Any,
    *,
    origin: pd.Timestamp | None,
    preprocessing: WaveformPreprocessing,
    min_record_length_s: float,
    min_end_after_origin_s: float,
) -> dict[str, Any]:
    """Compute global trace-quality values before passband checks.

    Parameters
    ----------
    trace
        Trace-like object or ``None``.
    origin
        Event origin time, when known.
    preprocessing
        Configured waveform preprocessing.
    min_record_length_s, min_end_after_origin_s
        Global duration thresholds.

    Returns
    -------
    dict
        Samples, relative times, duration values, and global reject reasons.
    """

    if trace is None:
        reasons, record_length_s, start_rel_s, end_rel_s = ["missing_trace"], float("nan"), float("nan"), float("nan")
        return {
            "samples": np.asarray([], dtype=float),
            "times_s": np.asarray([], dtype=float),
            "dt": float("nan"),
            "record_length_s": record_length_s,
            "start_rel_s": start_rel_s,
            "end_rel_s": end_rel_s,
            "valid_start_rel_s": float("nan"),
            "valid_end_rel_s": float("nan"),
            "valid_start_sample": float("nan"),
            "valid_end_sample": float("nan"),
            "global_reasons": reasons,
        }
    samples, dt, start_time = _trace_array_dt_start(trace)
    record_length_s = float(samples.size * dt) if np.isfinite(dt) and dt > 0.0 else float("nan")
    start_rel_s = _relative_seconds(start_time, origin)
    if not np.isfinite(start_rel_s):
        start_rel_s = 0.0
    times_s = start_rel_s + np.arange(samples.size, dtype=float) * dt if samples.size and np.isfinite(dt) else np.asarray([], dtype=float)
    end_rel_s = float(start_rel_s + record_length_s) if np.isfinite(record_length_s) else float("nan")
    reasons: list[str] = []
    if not samples.size or not np.any(np.isfinite(samples)):
        reasons.append("invalid_samples")
    else:
        finite = np.asarray(samples, dtype=float)
        finite = finite[np.isfinite(finite)]
        if finite.size and float(np.nanmax(np.abs(finite))) <= 0.0:
            reasons.append("flat_trace")
    reject_global, global_reasons = global_trace_reject_reasons(
        record_length_s=record_length_s,
        end_rel_s=end_rel_s,
        onset_reasons=reasons,
        min_end_after_origin_s=min_end_after_origin_s,
        min_record_length_s=min_record_length_s,
    )
    processed = samples
    processed_dt = dt
    if samples.size and np.isfinite(dt) and dt > 0.0:
        result = apply_waveform_preprocessing_with_metadata(samples, dt, preprocessing)
        processed = result.data
        processed_dt = result.dt
        record_length_s = float(processed.size * processed_dt) if np.isfinite(processed_dt) and processed_dt > 0.0 else record_length_s
        times_s = start_rel_s + np.arange(processed.size, dtype=float) * processed_dt if processed.size else np.asarray([], dtype=float)
        end_rel_s = float(start_rel_s + record_length_s) if np.isfinite(record_length_s) else float("nan")
    valid_mask = _processing_valid_mask(np.asarray(processed).size, preprocessing)
    valid_start_sample, valid_end_sample = _valid_sample_bounds(valid_mask)
    if (
        valid_start_sample is not None
        and valid_end_sample is not None
        and times_s.size == np.asarray(processed).size
        and np.isfinite(processed_dt)
        and processed_dt > 0.0
        and valid_end_sample > valid_start_sample
    ):
        valid_start_rel_s = float(times_s[valid_start_sample])
        valid_end_rel_s = float(times_s[valid_end_sample - 1] + processed_dt)
    else:
        valid_start_rel_s = float("nan")
        valid_end_rel_s = float("nan")
    return {
        "samples": np.asarray(processed, dtype=float),
        "times_s": times_s,
        "dt": processed_dt,
        "record_length_s": record_length_s,
        "start_rel_s": start_rel_s,
        "end_rel_s": end_rel_s,
        "valid_start_rel_s": valid_start_rel_s,
        "valid_end_rel_s": valid_end_rel_s,
        "valid_start_sample": valid_start_sample if valid_start_sample is not None else np.nan,
        "valid_end_sample": valid_end_sample if valid_end_sample is not None else np.nan,
        "global_reasons": global_reasons if reject_global else [],
    }


def _passband_quality_summary(
    trace_summary: dict[str, Any],
    *,
    period_min_s: float,
    period_max_s: float,
    snr_threshold: float,
    noise_window_min_s: float,
    signal_window_min_s: float,
    noise_gap_s: float,
    signal_gap_s: float,
    origin_tolerance_s: float,
    pre_origin_signal_ratio_threshold: float,
    global_reasons: list[str],
    pick_onset_rel_s: float | None = None,
) -> dict[str, float | bool]:
    """Compute passband-level signal/noise diagnostics.

    Parameters
    ----------
    trace_summary
        Output from :func:`_trace_quality_summary`.
    period_min_s, period_max_s
        Period bounds used to size QC windows.
    snr_threshold, noise_window_min_s, signal_window_min_s, noise_gap_s,
    signal_gap_s, origin_tolerance_s, pre_origin_signal_ratio_threshold
        QC thresholds.
    global_reasons
        Global trace reject reasons already assigned.

    Returns
    -------
    dict
        Passband diagnostic values consumed by :func:`reject_passband`.
    """

    _ = snr_threshold, pre_origin_signal_ratio_threshold, global_reasons
    samples = np.asarray(trace_summary.get("samples", []), dtype=float)
    times_s = np.asarray(trace_summary.get("times_s", []), dtype=float)
    if samples.size == 0 or times_s.size != samples.size:
        return _empty_passband_summary()
    finite = np.isfinite(samples) & np.isfinite(times_s)
    full_samples = samples[finite]
    full_times_s = times_s[finite]
    if full_samples.size == 0:
        return _empty_passband_summary()
    valid_start = _optional_float(trace_summary.get("valid_start_rel_s"))
    valid_end = _optional_float(trace_summary.get("valid_end_rel_s"))
    valid_finite = finite.copy()
    if valid_start is not None and valid_end is not None and valid_end > valid_start:
        valid_finite &= (times_s >= valid_start) & (times_s < valid_end)
    valid_samples = samples[valid_finite]
    valid_times_s = times_s[valid_finite]
    onset_samples = valid_samples if valid_samples.size else full_samples
    onset_times_s = valid_times_s if valid_times_s.size else full_times_s
    envelope = _smooth_abs(onset_samples, float(trace_summary.get("dt", np.nan)))
    post_mask = onset_times_s >= 0.0
    if not np.any(post_mask):
        return _empty_passband_summary()
    post_env = envelope[post_mask]
    post_times = onset_times_s[post_mask]
    threshold = _onset_threshold(envelope, onset_times_s)
    above = np.flatnonzero(post_env >= threshold)
    envelope_onset = float(post_times[above[0]]) if above.size else float("nan")
    min_window_s = max(float(period_max_s), float(period_min_s), 0.0)
    noise_length_s = max(float(noise_window_min_s), min_window_s)
    signal_length_s = max(float(signal_window_min_s), min_window_s)
    pick_onset = _optional_float(pick_onset_rel_s)
    signal_gap = float(signal_gap_s)
    pick_plausible = (
        pick_onset is not None
        and _window_has_min_samples(
            valid_samples,
            valid_times_s,
            pick_onset + signal_gap,
            pick_onset + signal_gap + signal_length_s,
        )
    )
    onset_rel_s = pick_onset if pick_plausible else envelope_onset
    if not np.isfinite(onset_rel_s):
        return _empty_passband_summary(onset_rel_s=onset_rel_s)
    noise_start = onset_rel_s - float(noise_gap_s) - noise_length_s
    noise_end = onset_rel_s - float(noise_gap_s)
    signal_start = onset_rel_s + signal_gap
    signal_end = signal_start + signal_length_s
    pre_origin_start = -float(origin_tolerance_s) - max(10.0, min_window_s)
    pre_origin_end = -float(origin_tolerance_s)
    origin_start = -float(origin_tolerance_s)
    origin_end = float(origin_tolerance_s)
    noise_rms, noise_valid = _window_rms(full_samples, full_times_s, noise_start, noise_end)
    signal_rms, signal_valid = _window_rms(valid_samples, valid_times_s, signal_start, signal_end)
    pre_rms, pre_valid = _window_rms(valid_samples, valid_times_s, pre_origin_start, pre_origin_end)
    origin_rms, origin_valid = _window_rms(valid_samples, valid_times_s, origin_start, origin_end)
    snr_rms = float(signal_rms / noise_rms) if noise_valid and signal_valid and noise_rms > 0.0 else float("nan")
    pre_ratio = float(pre_rms / signal_rms) if pre_valid and signal_valid and signal_rms > 0.0 else float("nan")
    origin_ratio = float(origin_rms / signal_rms) if origin_valid and signal_valid and signal_rms > 0.0 else float("nan")
    return {
        "onset_rel_s": onset_rel_s,
        "noise_rms": noise_rms,
        "signal_rms": signal_rms,
        "snr_rms": snr_rms,
        "noise_window_valid": bool(noise_valid),
        "signal_window_valid": bool(signal_valid),
        "pre_origin_window_valid": bool(pre_valid),
        "origin_window_valid": bool(origin_valid),
        "pre_origin_signal_ratio": pre_ratio,
        "origin_signal_ratio": origin_ratio,
    }


def _trace_array_dt_start(trace: Any) -> tuple[np.ndarray, float, pd.Timestamp | None]:
    """Extract samples, sample interval, and start time from one trace.

    Parameters
    ----------
    trace
        Trace-like object.

    Returns
    -------
    tuple
        ``(samples, dt_s, start_time)``.
    """

    data = trace.get("data") if isinstance(trace, dict) else getattr(trace, "data", [])
    stats = trace.get("stats", trace) if isinstance(trace, dict) else getattr(trace, "stats", None)
    samples = np.asarray(data, dtype=float).reshape(-1)
    sampling_rate = _safe_float(_stat_value(stats, "sampling_rate", None))
    delta = _safe_float(_stat_value(stats, "delta", None))
    dt = float(delta) if delta not in (None, 0.0) else (1.0 / float(sampling_rate) if sampling_rate not in (None, 0.0) else float("nan"))
    start_value = _stat_value(stats, "starttime", None)
    start_time = _to_utc_timestamp(start_value)
    return samples, dt, None if pd.isna(start_time) else start_time


def _to_utc_timestamp(value: Any) -> pd.Timestamp:
    """Parse common trace timestamp values as UTC pandas timestamps."""

    if value is None or (isinstance(value, float) and np.isnan(value)):
        return pd.NaT
    if hasattr(value, "datetime"):
        value = value.datetime
    elif not isinstance(value, (str, bytes)) and hasattr(value, "isoformat"):
        value = value.isoformat()
    return pd.to_datetime(value, utc=True, errors="coerce")


def _stat_value(stats: Any, key: str, default: Any = None) -> Any:
    """Read one stats value from a mapping or attribute object."""

    if stats is None:
        return default
    if isinstance(stats, dict):
        return stats.get(key, default)
    return getattr(stats, key, default)


def _relative_seconds(time_value: pd.Timestamp | None, origin: pd.Timestamp | None) -> float:
    """Return seconds from origin to a timestamp when both are available."""

    if time_value is None or origin is None:
        return float("nan")
    return float((time_value - origin).total_seconds())


def _smooth_abs(samples: np.ndarray, dt: float) -> np.ndarray:
    """Return a short moving-average absolute envelope."""

    values = np.abs(np.asarray(samples, dtype=float))
    if not np.isfinite(dt) or dt <= 0.0 or values.size < 3:
        return values
    window = max(3, int(round(0.5 / dt)))
    window = min(window, values.size)
    kernel = np.ones(window, dtype=float) / float(window)
    return np.convolve(values, kernel, mode="same")


def _onset_threshold(envelope: np.ndarray, times_s: np.ndarray) -> float:
    """Estimate a conservative onset threshold from pre- and post-origin data."""

    finite = np.isfinite(envelope)
    if not np.any(finite):
        return float("inf")
    post = envelope[finite & (times_s >= 0.0)]
    pre = envelope[finite & (times_s < -0.5)]
    if post.size == 0:
        return float("inf")
    post_peak = float(np.nanmax(post))
    if pre.size:
        median = float(np.nanmedian(pre))
        mad = float(np.nanmedian(np.abs(pre - median)))
        return max(0.05 * post_peak, median + 5.0 * mad)
    return 0.05 * post_peak


def _arrival_pick_lookup(
    arrival_pick_catalog: pd.DataFrame | str | Path | None,
    *,
    phase: str,
    min_probability: float,
) -> dict[tuple[str, str, str, str, str], float]:
    """Build a source/event/station/component/phase lookup for onset picks."""

    if arrival_pick_catalog is None:
        return {}
    picks = load_arrival_pick_catalog(arrival_pick_catalog) if not isinstance(arrival_pick_catalog, pd.DataFrame) else normalize_pick_catalog(arrival_pick_catalog)
    if picks.empty:
        return {}
    if "source" not in picks.columns:
        picks["source"] = ""
    picks = picks.copy()
    picks["phase"] = picks["phase"].astype(str).str.upper()
    picks["source"] = picks["source"].astype(str).str.strip().str.lower()
    picks["event_id"] = picks["event_id"].astype(str).str.strip()
    picks["station"] = picks["station"].astype(str).str.strip().str.upper()
    picks["component"] = picks["component"].astype(str).str.strip().str.upper()
    picks["pick_time_rel_s"] = pd.to_numeric(picks["pick_time_rel_s"], errors="coerce")
    picks["probability"] = pd.to_numeric(picks["probability"], errors="coerce")
    phase_text = str(phase or "P").strip().upper()
    picks = picks.loc[
        picks["phase"].eq(phase_text)
        & picks["pick_time_rel_s"].notna()
        & (picks["probability"].fillna(0.0) >= float(min_probability))
    ].copy()
    lookup: dict[tuple[str, str, str, str, str], float] = {}
    if picks.empty:
        return lookup
    picks = picks.sort_values("probability", ascending=False, na_position="last")
    for _, row in picks.iterrows():
        key = (
            str(row["source"]).strip().lower(),
            str(row["event_id"]).strip(),
            str(row["station"]).strip().upper(),
            str(row["component"]).strip().upper(),
            phase_text,
        )
        lookup.setdefault(key, float(row["pick_time_rel_s"]))
    return lookup


def _lookup_onset_pick(
    lookup: dict[tuple[str, str, str, str, str], float],
    *,
    source: object,
    event_id: object,
    station: object,
    component: object,
    phase: str = "P",
) -> float | None:
    """Return the best source/component-specific onset pick when available."""

    if not lookup:
        return None
    source_text = str(source).strip().lower()
    event_text = str(event_id).strip()
    station_text = str(station).strip().upper()
    component_text = str(component).strip().upper()
    phase_text = str(phase or "P").strip().upper()
    for key in (
        (source_text, event_text, station_text, component_text, phase_text),
        (source_text, event_text, station_text, "ALL", phase_text),
        ("", event_text, station_text, component_text, phase_text),
        ("", event_text, station_text, "ALL", phase_text),
    ):
        pick = _optional_float(lookup.get(key))
        if pick is not None:
            return pick
    return None


def _processing_valid_mask(sample_count: int, preprocessing: WaveformPreprocessing | None) -> np.ndarray:
    """Return samples considered valid after configured preprocessing."""

    count = int(sample_count)
    if count <= 0:
        return np.zeros(0, dtype=bool)
    mask = np.ones(count, dtype=bool)
    settings = preprocessing or WaveformPreprocessing()
    has_preprocessing = any(
        value is not None
        for value in (
            settings.lowpass_hz,
            settings.highpass_hz,
            settings.bandpass_low_hz,
            settings.bandpass_high_hz,
            settings.resample_hz,
        )
    )
    if not has_preprocessing:
        return mask
    edge = int(round(count * PROCESSING_EDGE_FRACTION))
    if edge > 0 and edge * 2 < count:
        mask[:edge] = False
        mask[-edge:] = False
    return mask


def _valid_sample_bounds(mask: np.ndarray) -> tuple[int | None, int | None]:
    """Return inclusive/exclusive sample bounds from one validity mask."""

    indices = np.flatnonzero(np.asarray(mask, dtype=bool))
    if indices.size == 0:
        return None, None
    return int(indices[0]), int(indices[-1]) + 1


def _optional_float(value: object) -> float | None:
    """Return a finite float when conversion is possible."""

    try:
        numeric = float(value)
    except Exception:
        return None
    return numeric if np.isfinite(numeric) else None


def _window_has_min_samples(
    samples: np.ndarray,
    times_s: np.ndarray,
    start_s: float,
    end_s: float,
    *,
    min_samples: int = 3,
) -> bool:
    """Return whether one time window contains enough finite samples."""

    values = np.asarray(samples, dtype=float)
    times = np.asarray(times_s, dtype=float)
    if values.size == 0 or values.size != times.size:
        return False
    mask = (times >= float(start_s)) & (times <= float(end_s)) & np.isfinite(values)
    return bool(np.count_nonzero(mask) >= int(min_samples))


def _window_rms(samples: np.ndarray, times_s: np.ndarray, start_s: float, end_s: float) -> tuple[float, bool]:
    """Compute RMS for one time window."""

    mask = (times_s >= float(start_s)) & (times_s <= float(end_s)) & np.isfinite(samples)
    if not np.any(mask):
        return float("nan"), False
    values = samples[mask]
    return float(np.sqrt(np.mean(np.square(values)))), bool(values.size >= 3)


def _empty_passband_summary(*, onset_rel_s: float = float("nan")) -> dict[str, float | bool]:
    """Return a failed passband diagnostic mapping."""

    return {
        "onset_rel_s": onset_rel_s,
        "noise_rms": float("nan"),
        "signal_rms": float("nan"),
        "snr_rms": float("nan"),
        "noise_window_valid": False,
        "signal_window_valid": False,
        "pre_origin_window_valid": False,
        "origin_window_valid": False,
        "pre_origin_signal_ratio": float("nan"),
        "origin_signal_ratio": float("nan"),
    }


def _safe_float(value: object) -> float | None:
    """Convert a scalar to a finite float when possible."""

    try:
        out = float(value)
    except Exception:
        return None
    return float(out) if np.isfinite(out) else None


def _coerce_trace_metadata(event_streams: dict[str, Any] | list[dict[str, Any]] | pd.DataFrame, *, observed_variant: str) -> pd.DataFrame:
    """Normalize stream inputs to trace metadata rows."""

    if isinstance(event_streams, pd.DataFrame):
        out = event_streams.copy()
        if "observed_variant" not in out.columns:
            out["observed_variant"] = observed_variant
        return out
    frames: list[pd.DataFrame] = []
    if isinstance(event_streams, dict):
        for event_id, stream in event_streams.items():
            frames.append(trace_metadata_table(stream, event_id=str(event_id)))
    else:
        for item in event_streams:
            event_id = str(item.get("event_id", ""))
            source = item.get("source")
            stream = item.get("stream", item.get("traces"))
            frames.append(trace_metadata_table(stream, event_id=event_id, source=source))
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["observed_variant"] = observed_variant
    return out


def _metadata_lookup(df: pd.DataFrame, *, key: str) -> dict[str, dict[str, Any]]:
    """Build a case-normalized metadata lookup."""

    if df is None or df.empty or key not in df.columns:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        token = str(row.get(key, "")).strip()
        if key == "station":
            token = token.upper()
        if token:
            out[token] = row.to_dict()
    return out


def _record_length_s(row: pd.Series) -> float:
    """Compute trace record length in seconds."""

    npts = _safe_float(row.get("npts"))
    sampling_rate = _safe_float(row.get("sampling_rate"))
    if npts is not None and sampling_rate not in (None, 0.0):
        return float(npts) / float(sampling_rate)
    start = pd.to_datetime(row.get("starttime"), utc=True, errors="coerce")
    end = pd.to_datetime(row.get("endtime"), utc=True, errors="coerce")
    if not pd.isna(start) and not pd.isna(end):
        return float((end - start).total_seconds())
    return float("nan")


def _end_relative_to_origin_s(row: pd.Series, event_meta: dict[str, Any]) -> float:
    """Compute trace end time relative to event origin when available."""

    end = pd.to_datetime(row.get("endtime"), utc=True, errors="coerce")
    origin_value = ""
    for column in ("origin_time", "event_origin_time", "event_time", "time", "start", "event_start"):
        if column in event_meta and str(event_meta.get(column, "")).strip():
            origin_value = event_meta.get(column)
            break
    origin = pd.to_datetime(origin_value, utc=True, errors="coerce")
    if not pd.isna(end) and not pd.isna(origin):
        return float((end - origin).total_seconds())
    return _record_length_s(row)


def _prefixed_metadata(row: dict[str, Any], prefix: str) -> dict[str, Any]:
    """Return one metadata mapping with prefixed keys."""

    return {f"{prefix}_{key}": value for key, value in row.items() if key not in {"event_id", "station"}}


def _truthy(value: object) -> bool:
    """Interpret common CSV truth values."""

    return str(value).strip().lower() in {"1", "true", "yes", "y", "reject", "rejected"}
