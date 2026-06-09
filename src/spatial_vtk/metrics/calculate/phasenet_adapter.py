"""PhaseNet adapter for broadband arrival picking.

Purpose
-------
This module prepares station-level broadband waveform inputs for PhaseNet,
runs a configured PhaseNet command, and converts PhaseNet picks into the public
Spatial-VTK arrival-pick catalog schema.

Usage examples
--------------
Build a pick catalog from preloaded waveform groups:
  ``build_phasenet_arrival_pick_catalog(groups, phasenet_command="python -m phasenet.predict", output_catalog="picks.csv", work_dir="phasenet_work")``
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from spatial_vtk.metrics.calculate.arrival_picks import REQUIRED_PICK_COLUMNS, require_phasenet, write_arrival_pick_catalog


STATION_LEVEL_COMPONENT = "ALL"


@dataclass(frozen=True)
class PhaseNetInputRecord:
    """Describe one generated PhaseNet input file.

    Parameters
    ----------
    file_name
        File name relative to the PhaseNet data directory.
    event_id, station, waveform_source
        Catalog identifiers for the input waveform.
    components
        Components present in the generated three-channel input.
    sampling_rate
        Sampling rate resolved from trace metadata.
    time_anchor
        Absolute waveform start time when available.
    relative_time_origin
        Absolute origin used to compute catalog-relative pick seconds.
    broadband
        Whether the input came from broadband traces.

    Returns
    -------
    PhaseNetInputRecord
        Immutable metadata record used to normalize PhaseNet picks.
    """

    file_name: str
    event_id: str
    station: str
    waveform_source: str
    components: tuple[str, ...]
    sampling_rate: float
    time_anchor: str = ""
    relative_time_origin: str = ""
    broadband: bool = True


def prepare_phasenet_numpy_inputs(
    groups: Iterable[Mapping[str, object]],
    data_dir: str | Path,
    *,
    overwrite: bool = False,
) -> list[PhaseNetInputRecord]:
    """Prepare full-broadband NumPy inputs for PhaseNet."""

    output_dir = Path(data_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[PhaseNetInputRecord] = []
    for group in groups:
        event_id = str(group.get("event_id", "")).strip()
        station = str(group.get("station", "")).strip()
        source = str(group.get("waveform_source", group.get("source", ""))).strip().lower()
        components = group.get("components")
        if not isinstance(components, Mapping):
            raise ValueError("Each PhaseNet group requires a components mapping.")
        data, present, sampling_rate, start = _stack_components(components, station=station)
        relative_origin = _origin_time_text(group.get("relative_time_origin"), start)
        file_name = f"{_safe_token(event_id)}_{_safe_token(station)}_{_safe_token(source)}_broadband.npz"
        path = output_dir / file_name
        if overwrite or not path.exists():
            np.savez(
                path,
                data=data,
                station_id=np.array(_safe_token(station)),
                t0=np.array(_phasenet_time_anchor(start)),
                sampling_rate=np.array(float(sampling_rate)),
                broadband=np.array(True),
            )
        records.append(
            PhaseNetInputRecord(
                file_name=file_name,
                event_id=event_id,
                station=station,
                waveform_source=source,
                components=present,
                sampling_rate=float(sampling_rate),
                time_anchor=start,
                relative_time_origin=relative_origin,
                broadband=True,
            )
        )
    return records


def write_phasenet_data_list(records: Sequence[PhaseNetInputRecord], data_dir: str | Path) -> Path:
    """Write PhaseNet ``data_list.csv`` for generated inputs."""

    output_dir = Path(data_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "data_list.csv"
    path.write_text("fname\n" + "\n".join(record.file_name for record in records) + "\n", encoding="utf-8")
    return path


def run_phasenet(
    data_dir: str | Path,
    *,
    result_dir: str | Path,
    phasenet_command: str | None = None,
    model_dir: str | Path | None = None,
    sampling_rate: float,
    min_p_prob: float = 0.0,
    min_s_prob: float = 0.0,
) -> Path:
    """Run PhaseNet for one sampling-rate group.

    Parameters
    ----------
    data_dir, result_dir
        PhaseNet input and output directories.
    phasenet_command
        Explicit command. Defaults to the configured PhaseNet command.
    model_dir
        Optional PhaseNet model directory.
    sampling_rate
        Trace sampling rate in Hz.
    min_p_prob, min_s_prob
        PhaseNet probability thresholds.

    Returns
    -------
    pathlib.Path
        Path to PhaseNet's pick CSV.
    """

    resolved_command = phasenet_command or require_phasenet()
    data_path = Path(data_dir).resolve()
    result_path = Path(result_dir).resolve()
    result_path.mkdir(parents=True, exist_ok=True)
    args = [
        "--data_dir",
        str(data_path),
        "--data_list",
        str(data_path / "data_list.csv"),
        "--format",
        "numpy",
        "--result_dir",
        str(result_path),
        "--result_fname",
        "picks.csv",
        "--batch_size",
        "1",
        "--sampling_rate",
        str(float(sampling_rate)),
        "--min_p_prob",
        str(float(min_p_prob)),
        "--min_s_prob",
        str(float(min_s_prob)),
    ]
    if model_dir:
        args = ["--model_dir", str(model_dir), *args]
    cmd, use_shell = _phase_command(resolved_command, args)
    subprocess.run(cmd, cwd=str(data_path), check=True, shell=use_shell)
    for candidate in (result_path / "picks.csv", result_path / "picks.csv.csv"):
        if candidate.exists():
            return candidate
    return result_path / "picks.csv"


def normalize_phasenet_output(
    phasenet_csv: str | Path,
    records: Iterable[PhaseNetInputRecord],
    *,
    model_version: str = "",
    min_p_prob: float = 0.0,
    min_s_prob: float = 0.0,
) -> pd.DataFrame:
    """Convert PhaseNet picks into station-level Spatial-VTK catalog rows."""

    picks = pd.read_csv(phasenet_csv)
    by_file = {record.file_name: record for record in records}
    rows: list[dict[str, object]] = []
    if picks.empty:
        return pd.DataFrame(columns=REQUIRED_PICK_COLUMNS)
    picks["phase_score"] = pd.to_numeric(picks.get("phase_score", np.nan), errors="coerce")
    picks["phase_type_norm"] = picks.get("phase_type", "").astype(str).str.upper()
    for file_name, file_df in picks.groupby("file_name", dropna=False):
        record = by_file.get(str(file_name))
        if record is None:
            continue
        for phase, threshold in (("P", float(min_p_prob)), ("S", float(min_s_prob))):
            phase_df = file_df[file_df["phase_type_norm"].eq(phase)].copy()
            phase_df = phase_df[phase_df["phase_score"].fillna(-np.inf) >= threshold]
            if phase_df.empty:
                continue
            best = phase_df.loc[phase_df["phase_score"].fillna(-np.inf).idxmax()]
            abs_time, rel_s = _phase_time_rel_s(best, record)
            if not np.isfinite(rel_s):
                continue
            rows.append(
                {
                    "event_id": record.event_id,
                    "station": record.station,
                    "component": STATION_LEVEL_COMPONENT,
                    "phase": phase,
                    "pick_time_abs": abs_time,
                    "pick_time_rel_s": rel_s,
                    "probability": float(best.get("phase_score", np.nan)),
                    "method": "phasenet",
                    "source": record.waveform_source,
                }
            )
    return pd.DataFrame(rows, columns=[*REQUIRED_PICK_COLUMNS, "source"])


def build_phasenet_arrival_pick_catalog(
    groups: Iterable[Mapping[str, object]],
    *,
    phasenet_command: str | None = None,
    output_catalog: str | Path,
    work_dir: str | Path,
    model_dir: str | Path | None = None,
    model_version: str = "",
    min_p_prob: float = 0.0,
    min_s_prob: float = 0.0,
    overwrite: bool = False,
) -> Path:
    """Prepare inputs, run PhaseNet, and write a pick catalog."""

    work_path = Path(work_dir)
    data_dir = work_path / "numpy"
    records = prepare_phasenet_numpy_inputs(groups, data_dir, overwrite=overwrite)
    by_rate: dict[float, list[PhaseNetInputRecord]] = {}
    for record in records:
        by_rate.setdefault(float(record.sampling_rate), []).append(record)
    catalogs: list[pd.DataFrame] = []
    for idx, (sampling_rate, rate_records) in enumerate(sorted(by_rate.items())):
        rate_dir = data_dir / f"rate_{idx}_{_safe_token(sampling_rate)}"
        rate_dir.mkdir(parents=True, exist_ok=True)
        for record in rate_records:
            source = data_dir / record.file_name
            target = rate_dir / record.file_name
            if overwrite or not target.exists():
                target.write_bytes(source.read_bytes())
        write_phasenet_data_list(rate_records, rate_dir)
        phasenet_csv = run_phasenet(
            rate_dir,
            result_dir=work_path / "phasenet_results" / f"rate_{idx}_{_safe_token(sampling_rate)}",
            phasenet_command=phasenet_command,
            model_dir=model_dir,
            sampling_rate=sampling_rate,
            min_p_prob=min_p_prob,
            min_s_prob=min_s_prob,
        )
        catalogs.append(
            normalize_phasenet_output(
                phasenet_csv,
                rate_records,
                model_version=model_version,
                min_p_prob=min_p_prob,
                min_s_prob=min_s_prob,
            )
        )
    catalog = pd.concat(catalogs, ignore_index=True) if catalogs else pd.DataFrame(columns=REQUIRED_PICK_COLUMNS)
    return write_arrival_pick_catalog(catalog, output_catalog, overwrite=overwrite)


def _trace_array_and_rate(value: object) -> tuple[np.ndarray, float, str]:
    """Return data, sampling rate, and start-time text for one trace."""

    if hasattr(value, "data") and hasattr(value, "stats"):
        data = np.asarray(getattr(value, "data"), dtype=np.float32)
        stats = getattr(value, "stats")
        if hasattr(stats, "sampling_rate"):
            sampling_rate = float(getattr(stats, "sampling_rate"))
        elif hasattr(stats, "delta"):
            sampling_rate = 1.0 / float(getattr(stats, "delta"))
        else:
            raise ValueError("Trace is missing stats.sampling_rate or stats.delta.")
        return data, sampling_rate, str(getattr(stats, "starttime", "") or "")
    if isinstance(value, Mapping):
        data = np.asarray(value.get("data", []), dtype=np.float32)
        if "sampling_rate" in value:
            sampling_rate = float(value["sampling_rate"])
        elif "delta" in value:
            sampling_rate = 1.0 / float(value["delta"])
        else:
            raise ValueError("Trace mapping is missing sampling_rate or delta.")
        return data, sampling_rate, str(value.get("starttime", "") or "")
    raise TypeError("PhaseNet traces must be ObsPy-like traces or mappings.")


def _stack_components(components: Mapping[str, object], *, station: str) -> tuple[np.ndarray, tuple[str, ...], float, str]:
    """Stack component traces into a PhaseNet ``(samples, 3)`` array."""

    normalized = {str(key).upper(): value for key, value in components.items()}
    if not normalized:
        raise ValueError(f"No broadband components available for station {station}.")
    arrays: dict[str, np.ndarray] = {}
    rates: list[float] = []
    starts: list[str] = []
    for component, trace in normalized.items():
        data, rate, start = _trace_array_and_rate(trace)
        if data.size == 0:
            continue
        arrays[component] = data
        rates.append(rate)
        if start:
            starts.append(start)
    if not arrays:
        raise ValueError(f"No non-empty broadband components available for station {station}.")
    median_rate = float(np.median(rates))
    if any(abs(rate - median_rate) > 1e-3 for rate in rates):
        raise ValueError(f"Broadband components for station {station} have incompatible sampling rates: {rates}")
    npts = min(array.size for array in arrays.values())
    if npts < 2:
        raise ValueError(f"Need at least two samples for station {station}.")
    order = _component_priority(arrays)
    stacked = []
    present = []
    for component in order:
        if component in arrays:
            stacked.append(arrays[component][:npts])
            present.append(component)
        else:
            stacked.append(np.zeros(npts, dtype=np.float32))
    return np.stack(stacked, axis=-1).astype(np.float32), tuple(present), median_rate, (starts[0] if starts else "")


def _component_priority(components: Mapping[str, object]) -> tuple[str, str, str]:
    """Return preferred component order for PhaseNet input."""

    keys = {str(key).upper() for key in components}
    if {"R", "T", "Z"} & keys:
        return ("R", "T", "Z")
    return ("E", "N", "Z")


def _phase_time_rel_s(row: pd.Series, record: PhaseNetInputRecord | None = None) -> tuple[str, float]:
    """Return absolute pick time and seconds relative to catalog origin."""

    begin = pd.to_datetime(row.get("begin_time"), utc=True, errors="coerce")
    phase_time = pd.to_datetime(row.get("phase_time"), utc=True, errors="coerce")
    if not pd.isna(begin) and not pd.isna(phase_time):
        origin = pd.NaT
        if record is not None and record.relative_time_origin:
            origin = pd.to_datetime(record.relative_time_origin, utc=True, errors="coerce")
        if pd.isna(origin):
            origin = begin
        return phase_time.isoformat(), float((phase_time - origin).total_seconds())
    rel = pd.to_numeric(row.get("phase_index", row.get("phase_time")), errors="coerce")
    if np.isfinite(rel):
        return "", float(rel)
    return "", np.nan


def _phase_command(command: str, args: Sequence[str]) -> tuple[object, bool]:
    """Return a subprocess command and whether to run through a shell."""

    text = str(command).strip()
    if not text:
        raise ValueError("PhaseNet command is empty.")
    if any(part in text for part in ("=", " ", "\t")):
        return " ".join([text, *(shlex.quote(str(arg)) for arg in args)]), True
    return [text, *map(str, args)], False


def _phasenet_time_anchor(value: str) -> str:
    """Return a PhaseNet-compatible start-time string."""

    text = str(value or "").strip()
    if not text:
        return "1970-01-01T00:00:00.000"
    if text.endswith("Z"):
        text = text[:-1]
    if "+" in text:
        text = text.split("+", 1)[0]
    return text


def _origin_time_text(value: object, fallback: str = "") -> str:
    """Return the absolute origin used for relative pick seconds."""

    text = str(value or "").strip()
    return text or str(fallback or "").strip()


def _safe_token(value: object) -> str:
    """Return a filesystem-safe token."""

    text = str(value or "").strip()
    out = [char if char.isalnum() or char in {"-", "_", "."} else "_" for char in text]
    return "".join(out).strip("_") or "unknown"


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the module-level CLI parser."""

    parser = argparse.ArgumentParser(description="Normalize PhaseNet picks into a Spatial-VTK arrival-pick catalog.")
    parser.add_argument("--phasenet-csv", required=True, help="PhaseNet picks CSV to normalize.")
    parser.add_argument("--records-csv", required=True, help="CSV containing PhaseNet input records.")
    parser.add_argument("--output", required=True, help="Output pick catalog CSV/parquet.")
    parser.add_argument("--min-p-prob", type=float, default=0.0)
    parser.add_argument("--min-s-prob", type=float, default=0.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the PhaseNet normalization CLI wrapper."""

    args = build_arg_parser().parse_args(argv)
    records_df = pd.read_csv(args.records_csv)
    records = [
        PhaseNetInputRecord(
            file_name=str(row.get("file_name", "")),
            event_id=str(row.get("event_id", "")),
            station=str(row.get("station", "")),
            waveform_source=str(row.get("waveform_source", "")),
            components=tuple(str(row.get("components", "")).split(",")) if str(row.get("components", "")) else (),
            sampling_rate=float(row.get("sampling_rate", 0.0)),
            time_anchor=str(row.get("time_anchor", "")),
            relative_time_origin=str(row.get("relative_time_origin", "")),
        )
        for _, row in records_df.iterrows()
    ]
    catalog = normalize_phasenet_output(args.phasenet_csv, records, min_p_prob=args.min_p_prob, min_s_prob=args.min_s_prob)
    write_arrival_pick_catalog(catalog, args.output, overwrite=True)
    return 0


__all__ = [
    "STATION_LEVEL_COMPONENT",
    "PhaseNetInputRecord",
    "prepare_phasenet_numpy_inputs",
    "write_phasenet_data_list",
    "run_phasenet",
    "normalize_phasenet_output",
    "build_phasenet_arrival_pick_catalog",
    "build_arg_parser",
    "main",
]
