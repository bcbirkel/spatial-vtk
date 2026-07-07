#!/usr/bin/env python3
"""Convert missing CVM-H Salvus receiver files to normalized ASDF.

This is a project workflow helper for the private CARC validation run.  Missing
means an event has a Salvus ``receivers.h5`` under ``WAVEFORM_DATA`` but does not
yet have ``{event_id}.asdf`` in the converted CVM-H synthetic inventory.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from spatial_vtk.io.synthetic_formats import SalvusConversionRequest, read_salvus_receivers_h5


DEFAULT_RAW_ROOT = Path(
    "/project2/jvidale_1700/Salvus_HPC/codebase/slurm_material_meshes/"
    "cvmh_0.6x1.2_slurm_meshing/20260506_material_0.6x1.2/EVENTS"
)
DEFAULT_ASDF_ROOT = Path(
    "/project2/jvidale_1700/ValidationToolkit/_synthetic_inventory/converted/"
    "cvmh_20260506_material_0p6x1p2_mseed"
)
DEFAULT_METRICS_TABLE = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/tables/metrics_final_enriched.parquet")
DEFAULT_EVENT_CSV = Path("/project2/jvidale_1700/spatial-vtk/runs/inputs/metadata/master_event_list.csv")
DEFAULT_STATION_CSV = Path("/project2/jvidale_1700/spatial-vtk/runs/inputs/metadata/master_station_list.csv")
DEFAULT_RUN_ROOT = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/cvmh_missing_asdf_conversion")
DEFAULT_PYTHON = Path("/project2/jvidale_1700/miniforge3/envs/gmprocess/bin/python")

EVENT_ID_ALIASES = ("event_id", "event", "event_name")
EVENT_LAT_ALIASES = ("event_lat", "event_latitude", "source_lat", "source_latitude", "lat")
EVENT_LON_ALIASES = ("event_lon", "event_longitude", "source_lon", "source_longitude", "lon")
EVENT_TIME_ALIASES = ("start", "origin_time", "event_origin_time", "event_time", "time", "event_start")
STATION_ALIASES = ("station", "sta", "station_code")
NETWORK_ALIASES = ("network", "net")
LOCATION_ALIASES = ("location", "loc")
STATION_LAT_ALIASES = ("sta_lat", "station_lat", "station_latitude", "lat", "latitude")
STATION_LON_ALIASES = ("sta_lon", "station_lon", "station_longitude", "lon", "longitude")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "convert-index", "audit", "write-slurm"))
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--asdf-root", type=Path, default=DEFAULT_ASDF_ROOT)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--metrics-table", type=Path, default=DEFAULT_METRICS_TABLE)
    parser.add_argument("--event-csv", type=Path, default=DEFAULT_EVENT_CSV)
    parser.add_argument("--station-csv", type=Path, default=DEFAULT_STATION_CSV)
    parser.add_argument("--event-list", type=Path, default=None)
    parser.add_argument("--chunk-size", type=int, default=96)
    parser.add_argument("--array-index", type=int, default=None)
    parser.add_argument("--python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--slurm-account", default="scec_608")
    parser.add_argument("--slurm-partition", default="main")
    parser.add_argument("--slurm-time", default="18:00:00")
    parser.add_argument("--slurm-mem", default="24G")
    parser.add_argument("--array-concurrency", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.run_root.mkdir(parents=True, exist_ok=True)
    if args.command == "plan":
        plan(args)
    elif args.command == "convert-index":
        convert_index(args)
    elif args.command == "audit":
        print(json.dumps(audit(args), indent=2, sort_keys=True))
    elif args.command == "write-slurm":
        write_slurm(args)
    else:
        raise ValueError(args.command)


def audit(args: argparse.Namespace) -> dict[str, Any]:
    raw = raw_events_with_receivers(args.raw_root)
    asdf = converted_asdf_event_ids(args.asdf_root)
    selected = selected_event_ids(args.event_list)
    if selected is not None:
        raw = {event_id: path for event_id, path in raw.items() if event_id in selected}
    missing = sorted(set(raw) - asdf)
    return {
        "raw_root": str(args.raw_root),
        "asdf_root": str(args.asdf_root),
        "raw_with_receivers_h5": len(raw),
        "converted_asdf": len(asdf),
        "missing_asdf_with_receivers_h5": len(missing),
        "missing_asdf_events": missing,
    }


def plan(args: argparse.Namespace) -> None:
    raw = raw_events_with_receivers(args.raw_root)
    asdf = converted_asdf_event_ids(args.asdf_root)
    selected = selected_event_ids(args.event_list)
    if selected is not None:
        raw = {event_id: path for event_id, path in raw.items() if event_id in selected}
    missing = sorted(set(raw) - asdf)

    events = load_event_metadata(args)
    stations = load_station_coordinates(args)
    manifest_path = args.run_root / "missing_cvmh_asdf_manifest.jsonl"
    missing_path = args.run_root / "missing_cvmh_asdf_events.txt"
    skipped_path = args.run_root / "missing_cvmh_asdf_skipped_metadata.jsonl"

    rows = []
    skipped = []
    for event_id in missing:
        event = events.get(event_id)
        if event is None:
            skipped.append({"event_id": event_id, "reason": "missing_event_metadata", "receivers_h5": str(raw[event_id])})
            continue
        rows.append(
            {
                "event_id": event_id,
                "receivers_h5": str(raw[event_id]),
                "asdf_path": str(args.asdf_root / f"{event_id}.asdf"),
                "event_latitude": event["latitude"],
                "event_longitude": event["longitude"],
                "origin_time": event["origin_time"],
            }
        )

    write_jsonl(manifest_path, rows)
    missing_path.write_text("\n".join(row["event_id"] for row in rows) + ("\n" if rows else ""))
    write_jsonl(skipped_path, skipped)
    summary = {
        **audit(args),
        "planned_conversions": len(rows),
        "skipped_missing_metadata": len(skipped),
        "station_coordinate_keys": len(stations),
        "manifest": str(manifest_path),
        "event_list": str(missing_path),
        "metadata_skips": str(skipped_path),
    }
    (args.run_root / "plan_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


def convert_index(args: argparse.Namespace) -> None:
    manifest = read_jsonl(args.run_root / "missing_cvmh_asdf_manifest.jsonl")
    if args.array_index is None:
        raise ValueError("--array-index is required for convert-index")
    if args.array_index < 0 or args.array_index >= len(manifest):
        raise IndexError(f"array index {args.array_index} outside manifest length {len(manifest)}")
    row = manifest[args.array_index]
    stations = load_station_coordinates(args)
    log_path = args.run_root / "logs" / f"{row['event_id']}.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    convert_one_event(row, stations, args.chunk_size, args.overwrite, log_path)


def write_slurm(args: argparse.Namespace) -> None:
    manifest = read_jsonl(args.run_root / "missing_cvmh_asdf_manifest.jsonl")
    if not manifest:
        raise RuntimeError("Manifest is empty. Run plan first.")
    logs = args.run_root / "slurm_logs"
    logs.mkdir(parents=True, exist_ok=True)
    slurm = args.run_root / "convert_missing_cvmh_asdf.slurm"
    slurm.write_text(
        f"""#!/bin/bash
#SBATCH --job-name=svtk-cvmh-asdf
#SBATCH --partition={args.slurm_partition}
#SBATCH --account={args.slurm_account}
#SBATCH --time={args.slurm_time}
#SBATCH --mem={args.slurm_mem}
#SBATCH --cpus-per-task=1
#SBATCH --array=0-{len(manifest) - 1}%{args.array_concurrency}
#SBATCH --output={logs}/svtk-cvmh-asdf_%A_%a.out
#SBATCH --error={logs}/svtk-cvmh-asdf_%A_%a.err

set -euo pipefail
cd /project2/jvidale_1700/spatial-vtk
export PYTHONNOUSERSITE=1
export PYTHONPATH=src
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
{args.python} tools/convert_missing_cvmh_asdf.py convert-index \\
  --run-root {args.run_root} \\
  --raw-root {args.raw_root} \\
  --asdf-root {args.asdf_root} \\
  --event-csv {args.event_csv} \\
  --station-csv {args.station_csv} \\
  --metrics-table {args.metrics_table} \\
  --chunk-size {args.chunk_size} \\
  --array-index "${{SLURM_ARRAY_TASK_ID}}"
"""
    )
    print(json.dumps({"slurm": str(slurm), "array_size": len(manifest)}, indent=2, sort_keys=True))


def convert_one_event(row: dict[str, Any], stations: dict[str, dict[str, float]], chunk_size: int, overwrite: bool, log_path: Path) -> None:
    import h5py
    import pyasdf

    event_id = str(row["event_id"])
    h5_path = Path(row["receivers_h5"])
    out_path = Path(row["asdf_path"])
    partial_path = out_path.with_name(out_path.name.replace(out_path.suffix, f".partial{out_path.suffix}"))
    if out_path.exists() and not overwrite:
        log_json(log_path, stage="skip", event_id=event_id, reason="already_converted", output=str(out_path))
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if partial_path.exists():
        partial_path.unlink()

    with h5py.File(h5_path, "r") as handle:
        n_receivers = int(len(handle["names_ELASTIC_point"]))
    request = SalvusConversionRequest(
        components=("E", "N", "R", "T", "Z"),
        event_latitude=float(row["event_latitude"]),
        event_longitude=float(row["event_longitude"]),
        station_coordinates=stations,
        acceleration_scale=100.0,
        input_acceleration_units="m/s^2",
        output_acceleration_units="cm/s^2",
    )
    log_json(log_path, stage="start", event_id=event_id, receivers=n_receivers, receivers_h5=str(h5_path), output=str(out_path))
    with pyasdf.ASDFDataSet(str(partial_path), mode="w") as dataset:
        for start in range(0, n_receivers, chunk_size):
            stop = min(start + chunk_size, n_receivers)
            stream = read_salvus_receivers_h5(
                h5_path,
                origin_time=str(row["origin_time"]),
                request=request,
                receiver_start=start,
                receiver_stop=stop,
            )
            dataset.add_waveforms(stream, tag="synthetic")
            log_json(log_path, stage="chunk", event_id=event_id, start=start, stop=stop, traces=len(stream))
    partial_path.replace(out_path)
    log_json(log_path, stage="done", event_id=event_id, output=str(out_path))


def raw_events_with_receivers(raw_root: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for event_dir in sorted(path for path in raw_root.iterdir() if path.is_dir() and path.name.startswith("ci")):
        candidates = sorted(
            (event_dir / "WAVEFORM_DATA").glob("INTERNAL/*/*/*/receivers.h5"),
            key=lambda path: (path.stat().st_size, path.stat().st_mtime),
            reverse=True,
        )
        if candidates:
            out[event_dir.name] = candidates[0]
    return out


def converted_asdf_event_ids(asdf_root: Path) -> set[str]:
    return {path.stem for path in asdf_root.glob("*.asdf") if ".partial" not in path.name}


def selected_event_ids(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    return {line.strip() for line in path.read_text().splitlines() if line.strip()}


def load_event_metadata(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    paths = [args.event_csv] if args.event_csv else []
    if args.metrics_table:
        paths.append(args.metrics_table)
    out: dict[str, dict[str, Any]] = {}
    for path in paths:
        if path is None or not path.exists():
            continue
        frame = read_metadata_table(path, EVENT_ID_ALIASES + EVENT_LAT_ALIASES + EVENT_LON_ALIASES + EVENT_TIME_ALIASES)
        event_id_col = first_column(frame, EVENT_ID_ALIASES)
        lat_col = first_column(frame, EVENT_LAT_ALIASES)
        lon_col = first_column(frame, EVENT_LON_ALIASES)
        time_col = first_column(frame, EVENT_TIME_ALIASES)
        if not all((event_id_col, lat_col, lon_col, time_col)):
            continue
        subset = frame[[event_id_col, lat_col, lon_col, time_col]].dropna().drop_duplicates(subset=[event_id_col])
        for row in subset.to_dict("records"):
            event_id = str(row[event_id_col]).strip()
            if not event_id or event_id in out:
                continue
            out[event_id] = {
                "latitude": float(row[lat_col]),
                "longitude": float(row[lon_col]),
                "origin_time": str(row[time_col]),
            }
    return out


def load_station_coordinates(args: argparse.Namespace) -> dict[str, dict[str, float]]:
    paths = [args.station_csv] if args.station_csv else []
    if args.metrics_table:
        paths.append(args.metrics_table)
    out: dict[str, dict[str, float]] = {}
    for path in paths:
        if path is None or not path.exists():
            continue
        frame = read_metadata_table(path, STATION_ALIASES + NETWORK_ALIASES + LOCATION_ALIASES + STATION_LAT_ALIASES + STATION_LON_ALIASES)
        station_col = first_column(frame, STATION_ALIASES)
        lat_col = first_column(frame, STATION_LAT_ALIASES)
        lon_col = first_column(frame, STATION_LON_ALIASES)
        if not all((station_col, lat_col, lon_col)):
            continue
        network_col = first_column(frame, NETWORK_ALIASES)
        location_col = first_column(frame, LOCATION_ALIASES)
        keep = [col for col in (station_col, network_col, location_col, lat_col, lon_col) if col]
        subset = frame[keep].dropna(subset=[station_col, lat_col, lon_col]).drop_duplicates(subset=[station_col])
        for row in subset.to_dict("records"):
            station = str(row[station_col]).strip().upper()
            if not station:
                continue
            network = str(row.get(network_col, "") or "").strip().upper() if network_col else ""
            location = str(row.get(location_col, "") or "").strip().upper() if location_col else ""
            coords = {"latitude": float(row[lat_col]), "longitude": float(row[lon_col])}
            for key in (station, f"{network}.{station}", f"{network}.{station}.{location}"):
                if key and not key.startswith("."):
                    out.setdefault(key, coords)
    return out


def read_metadata_table(path: Path, candidate_columns: tuple[str, ...]) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        import pyarrow.parquet as pq

        schema_names = set(pq.read_schema(path).names)
        columns = [column for column in dict.fromkeys(candidate_columns) if column in schema_names]
        return pd.read_parquet(path, columns=columns)
    return pd.read_csv(path)


def first_column(frame: pd.DataFrame, aliases: tuple[str, ...]) -> str | None:
    columns = {column.lower(): column for column in frame.columns}
    for alias in aliases:
        if alias.lower() in columns:
            return columns[alias.lower()]
    return None


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def log_json(path: Path, **row: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps(row, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
