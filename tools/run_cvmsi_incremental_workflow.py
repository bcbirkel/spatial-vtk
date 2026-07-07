#!/usr/bin/env python3
"""Run repeatable incremental Salvus synthetic event processing.

This project-specific workflow discovers new Salvus CVM-SI or CVM-H events,
converts their raw ``receivers.h5`` files to rotated synthetics, builds
overlap/QC tables, plans metric batches, writes Slurm scripts, merges completed
metrics into the active inventory tables, and validates the result.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import pickle
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_ROOT = Path("/project2/jvidale_1700/spatial-vtk")
DEFAULT_OBS = Path("/project2/jvidale_1700/data/all_merged_gmprocess")
DEFAULT_PYTHON = Path("/project2/jvidale_1700/miniforge3/envs/gmprocess/bin/python")
MODEL_PRESETS = {
    "cvmsi": {
        "raw": "/project2/jvidale_1700/Salvus_HPC/codebase/slurm_material_meshes/cvmsi_0.6x1.2_slurm_meshing/20260506_material_0.6x1.2/EVENTS",
        "synthetic": "/project2/jvidale_1700/ValidationToolkit/_synthetic_inventory/converted/cvmsi_20260506_material_0p6x1p2_asdf",
        "model": "cvmsi_20260506_material_0p6x1p2_asdf",
        "format": "asdf",
        "batch_prefix": "cvmsi_incremental",
    },
    "cvmh": {
        "raw": "/project2/jvidale_1700/Salvus_HPC/codebase/slurm_material_meshes/cvmh_0.6x1.2_slurm_meshing/20260506_material_0.6x1.2/EVENTS",
        "synthetic": "/project2/jvidale_1700/ValidationToolkit/_synthetic_inventory/converted/cvmh_20260506_material_0p6x1p2_mseed",
        "model": "cvmh_20260506_material_0p6x1p2_mseed",
        "format": "asdf",
        "batch_prefix": "cvmh_incremental",
    },
}
COMPONENTS = ("R", "T", "Z")
PASSBANDS = ((1, 2), (2, 3), (3, 5), (1, 5))
PASSBAND_LABELS = ("1-2 sec", "2-3 sec", "3-5 sec", "1-5 sec")
METRICS = (
    "arias_duration",
    "energy_duration",
    "PGA",
    "PGV",
    "PGD",
    "PSA",
    "FAS",
    "arias_intensity",
    "energy_intensity",
    "CAV",
    "traveltime_delay",
    "original_cc",
    "delay_corrected_cc",
)
SPECTRAL_PERIODS = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "discover",
            "convert",
            "prepare-qc",
            "pick-arrivals",
            "write-config",
            "plan-metrics",
            "write-prep-slurm",
            "submit-prep",
            "write-slurm",
            "submit-metrics",
            "combine",
            "validate",
            "prep-all",
        ),
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--model-preset", choices=tuple(MODEL_PRESETS), default="cvmsi")
    parser.add_argument("--raw-events-root", type=Path, default=None)
    parser.add_argument("--synthetic-root", type=Path, default=None)
    parser.add_argument("--model-name", default="")
    parser.add_argument("--output-format", choices=("asdf", "mseed"), default="")
    parser.add_argument("--observed-root", type=Path, default=DEFAULT_OBS)
    parser.add_argument("--python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--batch-name", default="")
    parser.add_argument("--batch-count", type=int, default=220)
    parser.add_argument("--chunk-size", type=int, default=int(os.environ.get("CVMSI_CONVERT_CHUNK_SIZE", "96")))
    parser.add_argument("--slurm-account", default="scec_608")
    parser.add_argument("--slurm-partition", default="main")
    parser.add_argument("--metric-array-concurrency", type=int, default=20)
    parser.add_argument("--convert-time", default="18:00:00")
    parser.add_argument("--convert-mem", default="24G")
    parser.add_argument("--metrics-time", default="04:00:00")
    parser.add_argument("--metrics-mem", default="8G")
    parser.add_argument("--combine-time", default="02:00:00")
    parser.add_argument("--combine-mem", default="32G")
    parser.add_argument("--submit-combine", action="store_true")
    parser.add_argument("--arrival-pick-catalog", type=Path, default=None)
    parser.add_argument("--phasenet-command", default=os.environ.get("SVTK_PHASENET_COMMAND", "python -m phasenet.predict"))
    parser.add_argument("--phasenet-model-dir", type=Path, default=None)
    parser.add_argument("--phasenet-min-p-prob", type=float, default=0.1)
    args = parser.parse_args()
    apply_model_preset(args)
    return args


def batch_name(value: str) -> str:
    return value or f"incremental_{time.strftime('%Y%m%dT%H%M%S')}"


def apply_model_preset(args: argparse.Namespace) -> None:
    preset = MODEL_PRESETS[args.model_preset]
    if args.raw_events_root is None:
        args.raw_events_root = Path(str(preset["raw"]))
    if args.synthetic_root is None:
        args.synthetic_root = Path(str(preset["synthetic"]))
    if not args.model_name:
        args.model_name = str(preset["model"])
    if not args.output_format:
        args.output_format = str(preset["format"])


def paths(args: argparse.Namespace) -> dict[str, Path]:
    name = batch_name(args.batch_name)
    out = args.root / "runs/outputs" / name
    return {
        "out": out,
        "logs": args.root / "runs/outputs/logs",
        "tables": args.root / "runs/outputs/tables",
        "event_list": out / "converted_events.txt",
        "manifest": out / "metric_manifest_incremental.json",
        "metric_batches": out / "metric_batches",
        "metric_rows": out / "metric_rows_incremental.parquet",
        "arrival_pick_catalog": out / "arrival_pick_catalog.parquet",
        "phasenet_work": out / "phasenet_work",
        "config": out / "spatial_vtk_config_incremental.yaml",
        "metric_outputs": out / "metric_outputs",
    }


def event_csv(args: argparse.Namespace) -> Path:
    return args.root / "runs/inputs/metadata/master_event_list.csv"


def station_csv(args: argparse.Namespace) -> Path:
    return args.root / "runs/inputs/metadata/master_station_list.csv"


def log_json(path: Path, **row: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps(row, sort_keys=True), flush=True)


def receiver_file(event_dir: Path) -> Path | None:
    files = sorted(event_dir.rglob("receivers.h5"), key=lambda p: (p.stat().st_size, p.stat().st_mtime), reverse=True)
    return files[0] if files else None


def raw_events_with_receivers(raw_root: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for event_dir in sorted(p for p in raw_root.iterdir() if p.is_dir() and p.name.startswith("ci")):
        h5_path = receiver_file(event_dir)
        if h5_path is not None:
            out[event_dir.name] = h5_path
    return out


def cvmh_mseed_name(event_id: str) -> str:
    return f"salvus_{event_id}_20260506_material_0.6x1.2_cvmh_0.6x1.2_material_CSrules_forward.mseed"


def synthetic_path_for_event(args: argparse.Namespace, event_id: str) -> Path:
    if args.output_format == "asdf":
        return args.synthetic_root / f"{event_id}.asdf"
    if args.output_format == "mseed":
        return args.synthetic_root / cvmh_mseed_name(event_id)
    raise ValueError(f"Unsupported output format: {args.output_format}")


def converted_event_ids(args: argparse.Namespace) -> set[str]:
    converted: set[str] = set()
    for path in args.synthetic_root.glob("*.asdf"):
        if ".partial" not in path.name:
            converted.add(path.stem)
    for path in args.synthetic_root.glob("*.mseed"):
        match = re.search(r"(ci\d+)", path.name)
        if match and ".partial" not in path.name:
            converted.add(match.group(1))
    return converted


def processed_event_ids(args: argparse.Namespace) -> set[str]:
    processed: set[str] = set()
    path = args.root / "runs/outputs/tables/metric_rows.parquet"
    if path.exists():
        try:
            rows = pd.read_parquet(path, columns=["event_id", "model"])
        except Exception:
            rows = pd.read_parquet(path)
        if "model" in rows.columns:
            rows = rows[rows["model"].astype(str).eq(args.model_name)]
        processed.update(rows["event_id"].astype(str))
    outputs = args.root / "runs/outputs"
    for validation_path in outputs.glob(f"{args.model_preset}*/validation_summary.json"):
        try:
            payload = json.loads(validation_path.read_text())
        except Exception:
            continue
        processed.update(str(event_id) for event_id in payload.get("events", []))
    return processed


def discover_missing(args: argparse.Namespace) -> list[str]:
    raw = raw_events_with_receivers(args.raw_events_root)
    converted = converted_event_ids(args)
    processed = processed_event_ids(args)
    missing = sorted(set(raw) - processed)
    print(json.dumps({"model": args.model_name, "raw_with_receivers_h5": len(raw), "converted": len(converted), "processed_metric_events": len(processed), "missing": len(missing)}, indent=2))
    for event_id in missing:
        print(event_id)
    return missing


def station_coordinates(args: argparse.Namespace) -> dict[str, dict[str, float]]:
    stations = pd.read_csv(station_csv(args))
    out: dict[str, dict[str, float]] = {}
    for row in stations.to_dict("records"):
        station = str(row["station"]).strip().upper()
        network = str(row.get("network", "") or "").strip()
        location = str(row.get("location", "") or "").strip()
        coords = {"latitude": float(row["lat"]), "longitude": float(row["lon"])}
        for key in (station, f"{network}.{station}", f"{network}.{station}.{location}"):
            if key and not key.startswith("."):
                out[key] = coords
    return out


def receiver_count(path: Path) -> int:
    import h5py

    with h5py.File(path, "r") as handle:
        return int(len(handle["names_ELASTIC_point"]))


def convert(args: argparse.Namespace) -> None:
    from spatial_vtk.io.synthetic_formats import SalvusConversionRequest, read_salvus_receivers_h5

    p = paths(args)
    out = p["out"]
    out.mkdir(parents=True, exist_ok=True)
    log = out / "convert.jsonl"
    events = pd.read_csv(event_csv(args)).set_index("event_id")
    coords = station_coordinates(args)
    raw = raw_events_with_receivers(args.raw_events_root)
    converted = converted_event_ids(args)
    processed = processed_event_ids(args)
    missing = sorted(set(raw) - processed)
    p["event_list"].write_text("")
    log_json(log, stage="inventory", model=args.model_name, output_format=args.output_format, raw_with_receivers=len(raw), converted=len(converted), processed_metric_events=len(processed), missing=len(missing), chunk_size=args.chunk_size)
    for event_id in missing:
        if event_id not in events.index:
            log_json(log, stage="skip", event_id=event_id, reason="missing_event_metadata")
            continue
        h5_path = raw[event_id]
        out_path = synthetic_path_for_event(args, event_id)
        partial_path = out_path.with_name(out_path.name.replace(out_path.suffix, f".partial{out_path.suffix}"))
        if out_path.exists():
            with p["event_list"].open("a") as handle:
                handle.write(event_id + "\n")
            log_json(log, stage="skip_conversion", event_id=event_id, reason="already_converted", output=str(out_path))
            continue
        if partial_path.exists():
            partial_path.unlink()
        event = events.loc[event_id]
        request = SalvusConversionRequest(
            components=("E", "N", "R", "T", "Z"),
            event_latitude=float(event["event_lat"]),
            event_longitude=float(event["event_lon"]),
            station_coordinates=coords,
            acceleration_scale=100.0,
            input_acceleration_units="m/s^2",
            output_acceleration_units="cm/s^2",
        )
        n_receivers = receiver_count(h5_path)
        log_json(log, stage="start_event", event_id=event_id, receivers=n_receivers, receivers_h5=str(h5_path), output=str(out_path))
        if args.output_format == "asdf":
            import pyasdf

            with pyasdf.ASDFDataSet(str(partial_path), mode="w") as ds:
                for start in range(0, n_receivers, args.chunk_size):
                    stop = min(start + args.chunk_size, n_receivers)
                    stream = read_salvus_receivers_h5(
                        h5_path,
                        origin_time=str(event["start"]),
                        request=request,
                        receiver_start=start,
                        receiver_stop=stop,
                    )
                    ds.add_waveforms(stream, tag="synthetic")
                    log_json(log, stage="chunk", event_id=event_id, start=start, stop=stop, traces=len(stream))
        elif args.output_format == "mseed":
            with partial_path.open("ab") as handle:
                for start in range(0, n_receivers, args.chunk_size):
                    stop = min(start + args.chunk_size, n_receivers)
                    stream = read_salvus_receivers_h5(
                        h5_path,
                        origin_time=str(event["start"]),
                        request=request,
                        receiver_start=start,
                        receiver_stop=stop,
                    )
                    stream.write(handle, format="MSEED")
                    log_json(log, stage="chunk", event_id=event_id, start=start, stop=stop, traces=len(stream))
        else:
            raise ValueError(f"Unsupported output format: {args.output_format}")
        partial_path.replace(out_path)
        with p["event_list"].open("a") as handle:
            handle.write(event_id + "\n")
        log_json(log, stage="done_event", event_id=event_id, output=str(out_path))
    raw_after = raw_events_with_receivers(args.raw_events_root)
    converted_after = converted_event_ids(args)
    processed_after = processed_event_ids(args)
    remaining = sorted(set(raw_after) - processed_after)
    log_json(log, stage="complete", raw_with_receivers=len(raw_after), converted=len(converted_after), processed_metric_events=len(processed_after), remaining_unprocessed=len(remaining), remaining_events=remaining)


def trace_component(trace: Any) -> str:
    return str(getattr(trace.stats, "channel", "") or "")[-1:].upper()


def trace_station(trace: Any) -> str:
    return str(getattr(trace.stats, "station", "") or "").strip().upper()


def load_stream(path: Path):
    from obspy import Stream, Trace

    with path.open("rb") as handle:
        obj = pickle.load(handle)
    if isinstance(obj, Stream):
        return obj
    if isinstance(obj, (list, tuple)):
        stream = Stream()
        for item in obj:
            if isinstance(item, Trace):
                stream.append(item)
            elif isinstance(item, Stream):
                stream += item
        return stream
    raise TypeError(f"Unsupported observed pickle payload: {path}: {type(obj)!r}")


def rotate_observed_stream(stream: Any, *, event_lat: float, event_lon: float, station_meta: pd.DataFrame):
    from obspy import Stream
    from obspy.geodetics import gps2dist_azimuth
    from obspy.signal.rotate import rotate_ne_rt

    station_lookup = station_meta.set_index("station")
    out = Stream()
    grouped: dict[str, list[Any]] = {}
    for tr in stream:
        sta = trace_station(tr)
        if sta:
            grouped.setdefault(sta, []).append(tr)
    for sta, traces in grouped.items():
        by_comp: dict[str, Any] = {}
        for tr in traces:
            comp = trace_component(tr)
            if comp and comp not in by_comp:
                by_comp[comp] = tr
        for comp in ("N", "E", "Z"):
            if comp in by_comp:
                out.append(by_comp[comp].copy())
        if "N" not in by_comp or "E" not in by_comp or sta not in station_lookup.index:
            continue
        sta_row = station_lookup.loc[sta]
        _, _, baz = gps2dist_azimuth(event_lat, event_lon, float(sta_row["lat"]), float(sta_row["lon"]))
        north = by_comp["N"]
        east = by_comp["E"]
        n_data = np.asarray(north.data, dtype=np.float64)
        e_data = np.asarray(east.data, dtype=np.float64)
        npts = min(n_data.size, e_data.size)
        if npts <= 0:
            continue
        radial, transverse = rotate_ne_rt(n_data[:npts], e_data[:npts], baz)
        r_trace = north.copy()
        t_trace = east.copy()
        r_trace.data = np.asarray(radial, dtype=np.float32)
        t_trace.data = np.asarray(transverse, dtype=np.float32)
        r_trace.stats.channel = str(getattr(r_trace.stats, "channel", "BHN"))[:-1] + "R"
        t_trace.stats.channel = str(getattr(t_trace.stats, "channel", "BHE"))[:-1] + "T"
        out.append(r_trace)
        out.append(t_trace)
    return out


def station_components(stream: Any) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for tr in stream:
        sta = trace_station(tr)
        comp = trace_component(tr)
        if sta and comp:
            out.setdefault(sta, set()).add(comp)
    return out


def synthetic_stations(path: Path) -> set[str]:
    if path.suffix.lower() == ".asdf":
        import pyasdf

        with pyasdf.ASDFDataSet(str(path), mode="r") as ds:
            stations = set()
            for name in ds.waveforms.list():
                parts = str(name).split(".")
                stations.add(parts[1].upper() if len(parts) > 1 else parts[0].upper())
            return stations
    from obspy import read

    return {trace_station(tr) for tr in read(str(path), headonly=True) if trace_station(tr)}


def first_trace_meta(stream: Any, sta: str, comp: str) -> dict[str, object] | None:
    for tr in stream:
        if trace_station(tr) == sta and trace_component(tr) == comp:
            return {
                "dt": float(tr.stats.delta),
                "sampling_rate": float(tr.stats.sampling_rate),
                "starttime": str(tr.stats.starttime),
                "endtime": str(tr.stats.endtime),
            }
    return None


def prepare_qc(args: argparse.Namespace) -> None:
    import pyasdf  # noqa: F401
    from obspy.geodetics import gps2dist_azimuth

    from spatial_vtk.io.waveforms import WaveformPreprocessing
    from spatial_vtk.qc.build.inventory import build_waveform_trace_qc_summary
    from spatial_vtk.qc.build.workflow import build_metric_qc_summary

    p = paths(args)
    out = p["out"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "observed_rotated").mkdir(parents=True, exist_ok=True)
    event_ids = [line.strip() for line in p["event_list"].read_text().splitlines() if line.strip()]
    events = pd.read_csv(event_csv(args)).set_index("event_id")
    stations = pd.read_csv(station_csv(args))
    station_meta = stations.copy()
    station_meta["station"] = station_meta["station"].astype(str).str.upper()
    station_lookup = station_meta.set_index("station")

    observed_rows: list[dict[str, object]] = []
    synthetic_rows: list[dict[str, object]] = []
    event_station_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for event_id in event_ids:
        if event_id not in events.index:
            raise KeyError(f"{event_id} missing from event metadata")
        event = events.loc[event_id]
        syn_path = synthetic_path_for_event(args, event_id)
        obs_source = args.observed_root / f"{event_id}_proc.pkl"
        syn_stations = synthetic_stations(syn_path) if syn_path.exists() else set()
        rotated_path = out / "observed_rotated" / event_id / f"{event_id}_proc.pkl"
        if not obs_source.exists():
            summary_rows.append({"event_id": event_id, "observed_path": "", "observed_stations": 0, "synthetic_stations": len(syn_stations), "overlap_stations": 0})
            continue
        stream = load_stream(obs_source)
        rotated = rotate_observed_stream(stream, event_lat=float(event["event_lat"]), event_lon=float(event["event_lon"]), station_meta=station_meta)
        rotated_path.parent.mkdir(parents=True, exist_ok=True)
        with rotated_path.open("wb") as handle:
            pickle.dump(rotated, handle, protocol=pickle.HIGHEST_PROTOCOL)
        obs_components = station_components(rotated)
        obs_stations = {sta for sta, comps in obs_components.items() if comps & set(COMPONENTS)}
        overlap = sorted(obs_stations & syn_stations & set(station_lookup.index))
        for sta in overlap:
            sta_row = station_lookup.loc[sta]
            distance_m, az, baz = gps2dist_azimuth(float(event["event_lat"]), float(event["event_lon"]), float(sta_row["lat"]), float(sta_row["lon"]))
            event_station_rows.append(
                {
                    "event_id": event_id,
                    "station": sta,
                    "model": args.model_name,
                    "start": event["start"],
                    "event_lat": float(event["event_lat"]),
                    "event_lon": float(event["event_lon"]),
                    "magnitude": float(event["magnitude"]),
                    "station_lat": float(sta_row["lat"]),
                    "station_lon": float(sta_row["lon"]),
                    "network": str(sta_row.get("network", "")),
                    "observed_available": True,
                    "synthetic_available": True,
                    "observed_waveform_path": str(rotated_path),
                    "synthetic_waveform_path": str(syn_path),
                    "distance_km": float(distance_m / 1000.0),
                    "azimuth_deg": float(az),
                    "backazimuth_deg": float(baz),
                }
            )
            for comp in COMPONENTS:
                meta = first_trace_meta(rotated, sta, comp)
                if meta is not None:
                    observed_rows.append({"source": "observed", "event_id": event_id, "station": sta, "component": comp, "model": "", "waveform_path": str(rotated_path), **meta})
                synthetic_rows.append(
                    {
                        "source": "synthetic",
                        "event_id": event_id,
                        "station": sta,
                        "component": comp,
                        "model": args.model_name,
                        "waveform_path": str(syn_path),
                        "dt": 1.0 / 725.6333333333333,
                        "sampling_rate": 725.6333333333333,
                        "starttime": str(event["start"]),
                        "endtime": "",
                    }
                )
        summary_rows.append({"event_id": event_id, "observed_path": str(rotated_path), "observed_stations": len(obs_stations), "synthetic_stations": len(syn_stations), "overlap_stations": len(overlap)})
        print(json.dumps(summary_rows[-1]), flush=True)

    pd.DataFrame(summary_rows).to_csv(out / "incremental_overlap_summary.csv", index=False)
    pd.DataFrame(observed_rows).to_parquet(out / "observed_metric_inventory_rtz.parquet", index=False)
    pd.DataFrame(synthetic_rows).to_parquet(out / "synthetic_metric_inventory_rtz.parquet", index=False)
    records = pd.DataFrame(event_station_rows)
    records.to_parquet(out / "event_station_overlap_rtz.parquet", index=False)
    print(json.dumps({"event_station_rows": len(records), "observed_rows": len(observed_rows), "synthetic_rows": len(synthetic_rows)}), flush=True)
    if records.empty:
        empty_metric_qc_columns = [
            "source",
            "event_id",
            "station",
            "event_title",
            "event_lat",
            "event_lon",
            "station_lat",
            "station_lon",
            "network",
            "magnitude",
            "distance_km",
            "component",
            "passband",
            "metric_group",
            "metric",
            "period_s",
            "qc_status",
            "qc_reason",
            "trace_start_s",
            "sample_interval_s",
            "valid_start_rel_s",
            "valid_end_rel_s",
            "valid_start_sample",
            "valid_end_sample",
        ]
        pd.DataFrame(columns=empty_metric_qc_columns).to_parquet(out / "trace_qc_overlap_rtz.parquet", index=False)
        pd.DataFrame(columns=empty_metric_qc_columns).to_parquet(out / "metric_qc_overlap.parquet", index=False)
        pd.DataFrame(columns=["source", "metric_group", "metric", "qc_status", "rows"]).to_csv(out / "metric_qc_overlap_summary.csv", index=False)
        print(json.dumps({"trace_qc_rows": 0}), flush=True)
        print(json.dumps({"metric_qc_rows": 0, "events": 0}), flush=True)
        return
    trace_parts = []
    for source, path_col in (("observed", "observed_waveform_path"), ("synthetic", "synthetic_waveform_path")):
        rows = build_waveform_trace_qc_summary(
            records,
            source=source,
            waveform_path_col=path_col,
            components=COMPONENTS,
            passbands=PASSBAND_LABELS,
            preprocessing=WaveformPreprocessing(lowpass_hz=1.0, filter_order=4),
            min_record_length_s=60.0,
            min_end_after_origin_s=60.0,
            snr_threshold=3.0,
            verbose=True,
            progress_interval=250,
            checkpoint_path=out / f"{source}_trace_qc_checkpoint.parquet",
            resume=True,
            checkpoint_interval=250,
        )
        trace_parts.append(rows)
    trace_qc = pd.concat(trace_parts, ignore_index=True) if trace_parts else pd.DataFrame()
    trace_qc.to_parquet(out / "trace_qc_overlap_rtz.parquet", index=False)
    print(json.dumps({"trace_qc_rows": len(trace_qc)}), flush=True)
    metric_qc = build_metric_qc_summary(
        records,
        metrics=METRICS,
        components=COMPONENTS,
        passbands=PASSBAND_LABELS,
        spectral_periods_s=SPECTRAL_PERIODS,
        sources=("observed", "synthetic"),
        synthetic_max_frequency_hz=1.0,
        observed_available=True,
        synthetic_available=True,
        trace_qc_summary=trace_qc,
        verbose=True,
        progress_interval=250,
        checkpoint_path=out / "metric_qc_overlap_checkpoint.parquet",
        resume=True,
        checkpoint_interval=250,
    )
    metric_qc.to_parquet(out / "metric_qc_overlap.parquet", index=False)
    print(json.dumps({"metric_qc_rows": len(metric_qc), "events": int(metric_qc["event_id"].nunique())}), flush=True)
    metric_qc.groupby(["source", "metric_group", "metric", "qc_status"], dropna=False).size().reset_index(name="rows").to_csv(out / "metric_qc_overlap_summary.csv", index=False)


def write_config(args: argparse.Namespace) -> None:
    import yaml

    p = paths(args)
    p["out"].mkdir(parents=True, exist_ok=True)
    base = args.root / "runs/large_run/spatial_vtk_config.yaml"
    with base.open() as handle:
        config = yaml.safe_load(handle)
    metrics = config.setdefault("metrics", {})
    metrics["models"] = [args.model_name]
    metrics["passbands"] = [list(passband) for passband in PASSBANDS]
    metrics.setdefault("spectral", {})["periods_s"] = list(SPECTRAL_PERIODS)

    def update_nested_models(node: object) -> None:
        if isinstance(node, dict):
            if "models" in node:
                node["models"] = [args.model_name]
            for value in node.values():
                update_nested_models(value)
        elif isinstance(node, list):
            for value in node:
                update_nested_models(value)

    update_nested_models(config.get("run_scenarios", {}))
    with p["config"].open("w") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)
    print(p["config"])


def run_subprocess(cmd: list[str], *, cwd: Path) -> dict[str, object]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=True)
    return {"command": " ".join(cmd), "stdout": proc.stdout, "stderr": proc.stderr}


def plan_metrics(args: argparse.Namespace) -> None:
    p = paths(args)
    pick_catalog = args.arrival_pick_catalog or p["arrival_pick_catalog"]
    delay_method = "phasenet_cycle" if pick_catalog.exists() else "bounded"
    cmd = [
        str(args.python),
        "-m",
        "spatial_vtk.cli",
        "metrics",
        "plan",
        "--config",
        str(p["config"]),
        "--observed-inventory",
        str(p["out"] / "observed_metric_inventory_rtz.parquet"),
        "--synthetic-inventory",
        str(p["out"] / "synthetic_metric_inventory_rtz.parquet"),
        "--qc-table",
        str(p["out"] / "metric_qc_overlap.parquet"),
        "--require-source-overlap",
        "--source-overlap-scope",
        "event_station",
        "--metric-plan-output",
        str(p["manifest"]),
        "--manifest",
        "--batch-output-dir",
        str(p["metric_batches"]),
        "--batch-count",
        str(args.batch_count),
        "--delay-method",
        delay_method,
    ]
    if pick_catalog.exists():
        cmd.extend(["--arrival-pick-catalog", str(pick_catalog)])
    env = os.environ.copy()
    env.update({"PYTHONPATH": "src", "PYTHONNOUSERSITE": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"})
    proc = subprocess.run(cmd, cwd=args.root, text=True, env=env, check=True)
    print(json.dumps({"manifest": str(p["manifest"]), "returncode": proc.returncode, "delay_method": delay_method}))


def pick_arrivals(args: argparse.Namespace) -> None:
    """Run lowpass PhaseNet picking for the incremental observed/synthetic overlap."""

    from spatial_vtk.io.waveforms import WaveformPreprocessing, apply_waveform_preprocessing_with_metadata
    from spatial_vtk.metrics.calculate.phasenet_adapter import build_phasenet_arrival_pick_catalog
    from spatial_vtk.metrics.workflow.run import _load_component_samples

    p = paths(args)
    output = args.arrival_pick_catalog or p["arrival_pick_catalog"]
    obs_path = p["out"] / "observed_metric_inventory_rtz.parquet"
    syn_path = p["out"] / "synthetic_metric_inventory_rtz.parquet"
    if not obs_path.exists() or not syn_path.exists():
        raise FileNotFoundError("Observed and synthetic metric inventories must exist before PhaseNet picking.")
    inventories = [
        ("observed", pd.read_parquet(obs_path)),
        ("synthetic", pd.read_parquet(syn_path)),
    ]
    groups: list[dict[str, object]] = []
    waveform_cache: dict[str, object] = {}
    preprocessing = WaveformPreprocessing(lowpass_hz=1.0, filter_order=4)
    for source, inv in inventories:
        if inv.empty:
            continue
        inv = inv.copy()
        inv["station"] = inv["station"].astype(str).str.upper()
        inv["component"] = inv["component"].astype(str).str.upper()
        for (event_id, station), group_df in inv.groupby(["event_id", "station"], dropna=False):
            components: dict[str, object] = {}
            relative_origin = ""
            for _, row in group_df.sort_values("component").iterrows():
                component = str(row.get("component", "")).strip().upper()
                if component not in COMPONENTS:
                    continue
                path = str(row.get("waveform_path", "") or "")
                if not path:
                    continue
                try:
                    loaded = _load_component_samples(path, str(station), component, waveform_cache=waveform_cache)
                    processed = apply_waveform_preprocessing_with_metadata(loaded.data, loaded.dt, preprocessing)
                except Exception as exc:
                    print(json.dumps({"stage": "pick-arrivals", "status": "skip_component", "source": source, "event_id": str(event_id), "station": str(station), "component": component, "reason": str(exc)}), flush=True)
                    continue
                starttime = str(row.get("starttime", "") or row.get("trace_start_time", "") or "")
                if not relative_origin and starttime:
                    relative_origin = starttime
                components[component] = {
                    "data": processed.data.astype(np.float32),
                    "sampling_rate": 1.0 / float(processed.dt),
                    "starttime": starttime,
                }
            if components:
                groups.append(
                    {
                        "event_id": str(event_id),
                        "station": str(station).upper(),
                        "source": source,
                        "waveform_source": source,
                        "relative_time_origin": relative_origin,
                        "components": components,
                    }
                )
    output.parent.mkdir(parents=True, exist_ok=True)
    if not groups:
        pd.DataFrame(
            columns=["event_id", "station", "component", "phase", "pick_time_abs", "pick_time_rel_s", "probability", "method", "source"]
        ).to_parquet(output, index=False)
        print(json.dumps({"stage": "pick-arrivals", "groups": 0, "output": str(output)}))
        return
    result = build_phasenet_arrival_pick_catalog(
        groups,
        phasenet_command=args.phasenet_command,
        output_catalog=output,
        work_dir=p["phasenet_work"],
        model_dir=args.phasenet_model_dir,
        min_p_prob=args.phasenet_min_p_prob,
        min_s_prob=1.0,
        overwrite=True,
    )
    picks = pd.read_parquet(result) if Path(result).suffix.lower() in {".parquet", ".pq"} else pd.read_csv(result)
    print(json.dumps({"stage": "pick-arrivals", "groups": len(groups), "picks": int(len(picks)), "output": str(result)}))


def manifest_batch_count(path: Path) -> int:
    with path.open() as handle:
        manifest = json.load(handle)
    return int(len(manifest.get("batches", [])))


def forwarded_model_args(args: argparse.Namespace) -> str:
    return (
        f"--model-preset {args.model_preset} "
        f"--raw-events-root {args.raw_events_root} "
        f"--synthetic-root {args.synthetic_root} "
        f"--model-name {args.model_name} "
        f"--output-format {args.output_format}"
    )


def forwarded_picker_args(args: argparse.Namespace) -> str:
    parts = [f"--phasenet-command {json.dumps(str(args.phasenet_command))}"]
    if args.phasenet_model_dir is not None:
        parts.append(f"--phasenet-model-dir {args.phasenet_model_dir}")
    parts.append(f"--phasenet-min-p-prob {args.phasenet_min_p_prob:g}")
    if args.arrival_pick_catalog is not None:
        parts.append(f"--arrival-pick-catalog {args.arrival_pick_catalog}")
    return " ".join(parts)


def write_slurm(args: argparse.Namespace) -> None:
    p = paths(args)
    batch_count = manifest_batch_count(p["manifest"])
    if batch_count <= 0:
        raise RuntimeError(f"No metric batches in {p['manifest']}")
    logs = p["logs"]
    logs.mkdir(parents=True, exist_ok=True)
    metric_slurm = p["out"] / "run_metric_batches.slurm"
    combine_slurm = p["out"] / "combine_incremental.slurm"
    metric_slurm.write_text(
        f"""#!/bin/bash
#SBATCH --job-name=svtk-{args.model_preset}-inc-metrics
#SBATCH --partition={args.slurm_partition}
#SBATCH --account={args.slurm_account}
#SBATCH --time={args.metrics_time}
#SBATCH --mem={args.metrics_mem}
#SBATCH --cpus-per-task=1
#SBATCH --array=0-{batch_count - 1}%{args.metric_array_concurrency}
#SBATCH --output={logs}/svtk-{args.model_preset}-inc-metrics_%A_%a.out
#SBATCH --error={logs}/svtk-{args.model_preset}-inc-metrics_%A_%a.err

set -euo pipefail
cd {args.root}
export PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH=src
{args.python} -m spatial_vtk.cli metrics run-batch \\
  --metric-manifest {p["manifest"]} \\
  --batch-index "${{SLURM_ARRAY_TASK_ID}}" \\
  --overwrite
"""
    )
    combine_slurm.write_text(
        f"""#!/bin/bash
#SBATCH --job-name=svtk-{args.model_preset}-inc-combine
#SBATCH --partition={args.slurm_partition}
#SBATCH --account={args.slurm_account}
#SBATCH --time={args.combine_time}
#SBATCH --mem={args.combine_mem}
#SBATCH --cpus-per-task=1
#SBATCH --output={logs}/svtk-{args.model_preset}-inc-combine_%j.out
#SBATCH --error={logs}/svtk-{args.model_preset}-inc-combine_%j.err

set -euo pipefail
cd {args.root}
export PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH=src
{args.python} tools/run_cvmsi_incremental_workflow.py combine --batch-name {batch_name(args.batch_name)} {forwarded_model_args(args)}
{args.python} tools/run_cvmsi_incremental_workflow.py validate --batch-name {batch_name(args.batch_name)} {forwarded_model_args(args)}
"""
    )
    print(json.dumps({"metric_slurm": str(metric_slurm), "combine_slurm": str(combine_slurm), "batches": batch_count}, indent=2))


def write_prep_slurm(args: argparse.Namespace) -> None:
    p = paths(args)
    p["out"].mkdir(parents=True, exist_ok=True)
    p["logs"].mkdir(parents=True, exist_ok=True)
    prep_slurm = p["out"] / "prep_incremental.slurm"
    prep_slurm.write_text(
        f"""#!/bin/bash
#SBATCH --job-name=svtk-{args.model_preset}-inc-prep
#SBATCH --partition={args.slurm_partition}
#SBATCH --account={args.slurm_account}
#SBATCH --time={args.convert_time}
#SBATCH --mem={args.convert_mem}
#SBATCH --cpus-per-task=1
#SBATCH --output={p["logs"]}/svtk-{args.model_preset}-inc-prep_%j.out
#SBATCH --error={p["logs"]}/svtk-{args.model_preset}-inc-prep_%j.err

set -euo pipefail
cd {args.root}
export PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH=src
{args.python} tools/run_cvmsi_incremental_workflow.py prep-all \\
  --batch-name {batch_name(args.batch_name)} \\
  {forwarded_model_args(args)} \\
  --batch-count {args.batch_count} \\
  --chunk-size {args.chunk_size} \\
  --slurm-account {args.slurm_account} \\
  --slurm-partition {args.slurm_partition} \\
  --metric-array-concurrency {args.metric_array_concurrency} \\
  {forwarded_picker_args(args)}
"""
    )
    print(json.dumps({"prep_slurm": str(prep_slurm)}, indent=2))


def submit_prep(args: argparse.Namespace) -> None:
    p = paths(args)
    write_prep_slurm(args)
    proc = subprocess.run(["sbatch", str(p["out"] / "prep_incremental.slurm")], cwd=args.root, text=True, capture_output=True, check=True)
    result = {"prep_job": proc.stdout.strip().split()[-1], "prep_submit_stdout": proc.stdout.strip()}
    (p["out"] / "submitted_prep_job.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


def submit_metrics(args: argparse.Namespace) -> None:
    p = paths(args)
    write_slurm(args)
    metric_proc = subprocess.run(["sbatch", str(p["out"] / "run_metric_batches.slurm")], cwd=args.root, text=True, capture_output=True, check=True)
    metric_job = metric_proc.stdout.strip().split()[-1]
    result: dict[str, object] = {"metric_job": metric_job, "metric_submit_stdout": metric_proc.stdout.strip()}
    if args.submit_combine:
        combine_proc = subprocess.run(["sbatch", f"--dependency=afterok:{metric_job}", str(p["out"] / "combine_incremental.slurm")], cwd=args.root, text=True, capture_output=True, check=True)
        result["combine_job"] = combine_proc.stdout.strip().split()[-1]
        result["combine_submit_stdout"] = combine_proc.stdout.strip()
    (p["out"] / "submitted_jobs.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


def normalize_for_parquet(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if out[col].dtype != "object":
            continue
        series = out[col]
        has_bytes = series.map(lambda value: isinstance(value, (bytes, bytearray))).any()
        if has_bytes:
            series = series.map(lambda value: value.decode("utf-8", errors="replace") if isinstance(value, (bytes, bytearray)) else value)
        numeric = pd.to_numeric(series, errors="coerce")
        non_null = series.notna()
        if bool(non_null.any()) and int(numeric.notna().sum()) == int(non_null.sum()):
            out[col] = numeric
        else:
            out[col] = series.map(lambda value: "" if pd.isna(value) else str(value))
    return out


def read_table(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.suffix.lower() in {".parquet", ".pq"} else pd.read_csv(path)


def write_table(df: pd.DataFrame, path: Path) -> None:
    if path.suffix.lower() in {".parquet", ".pq"}:
        normalize_for_parquet(df).to_parquet(path, index=False)
    else:
        df.to_csv(path, index=False)


def event_ids_for_batch(args: argparse.Namespace) -> set[str]:
    event_list = paths(args)["event_list"]
    return {line.strip() for line in event_list.read_text().splitlines() if line.strip()}


def replace_event_rows(args: argparse.Namespace, target: Path, incoming: Path, backup: Path, *, label: str) -> dict[str, object]:
    events = event_ids_for_batch(args)
    old = read_table(target)
    new = read_table(incoming)
    backup.mkdir(parents=True, exist_ok=True)
    backup_path = backup / target.name
    shutil.copy2(target, backup_path)
    old_mask = old["event_id"].astype(str).isin(events)
    new_mask = new["event_id"].astype(str).isin(events)
    if "model" in old.columns and "model" in new.columns and label != "observed_metric_inventory":
        old_mask &= old["model"].astype(str).eq(args.model_name)
        new_mask &= new["model"].astype(str).eq(args.model_name)
    kept = old.loc[~old_mask].copy()
    add = new.loc[new_mask].copy()
    if label == "observed_metric_inventory":
        key_cols = [col for col in ("event_id", "station", "component", "waveform_path") if col in kept.columns and col in add.columns]
        if key_cols:
            kept_key = kept[key_cols].astype(str).agg("\x1f".join, axis=1)
            add_key = set(add[key_cols].astype(str).agg("\x1f".join, axis=1))
            kept = kept.loc[~kept_key.isin(add_key)].copy()
    columns = list(dict.fromkeys([*kept.columns.tolist(), *add.columns.tolist()]))
    combined = pd.concat([kept.reindex(columns=columns), add.reindex(columns=columns)], ignore_index=True)
    write_table(combined, target)
    return {"label": label, "target": str(target), "incoming": str(incoming), "backup": str(backup_path), "old_rows": int(len(old)), "removed_existing_event_rows": int(old_mask.sum()), "incoming_rows": int(len(add)), "final_rows": int(len(combined))}


def append_metric_qc_csv(args: argparse.Namespace) -> dict[str, object]:
    p = paths(args)
    target = p["tables"] / "qc_inventory.csv"
    incoming = p["out"] / "metric_qc_overlap.parquet"
    marker = p["tables"] / f".{batch_name(args.batch_name)}_metric_qc_csv_appended.json"
    if marker.exists():
        return {"label": "qc_inventory.csv", "status": "skipped_marker_exists", "marker": str(marker)}
    with target.open("r", newline="") as handle:
        header = next(csv.reader(handle))
    new_df = pd.read_parquet(incoming)
    for col in header:
        if col not in new_df.columns:
            new_df[col] = pd.NA
    append_df = new_df.reindex(columns=header)
    before_size = target.stat().st_size
    append_df.to_csv(target, mode="a", header=False, index=False)
    payload = {"label": "qc_inventory.csv", "incoming": str(incoming), "appended_rows": int(len(append_df)), "before_size": int(before_size), "after_size": int(target.stat().st_size), "marker": str(marker)}
    marker.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def combine(args: argparse.Namespace) -> None:
    p = paths(args)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    backup = p["tables"] / f"backup_before_{batch_name(args.batch_name)}_{stamp}"
    results: list[dict[str, object]] = []
    results.append(
        run_subprocess(
            [
                str(args.python),
                "-m",
                "spatial_vtk.cli",
                "metrics",
                "merge-batches",
                "--metric-manifest",
                str(p["manifest"]),
                "--metric-rows-output",
                str(p["metric_rows"]),
            ],
            cwd=args.root,
        )
    )
    results.append(
        run_subprocess(
            [
                str(args.python),
                "-m",
                "spatial_vtk.cli",
                "metrics",
                "outputs",
                "--config",
                str(p["config"]),
                "--metric-rows",
                str(p["metric_rows"]),
                "--metrics-output-dir",
                str(p["metric_outputs"]),
                "--event-table",
                str(event_csv(args)),
                "--station-table",
                str(station_csv(args)),
                "--format",
                "parquet",
            ],
            cwd=args.root,
        )
    )
    results.append(replace_event_rows(args, p["tables"] / "observed_metric_inventory.parquet", p["out"] / "observed_metric_inventory_rtz.parquet", backup, label="observed_metric_inventory"))
    results.append(replace_event_rows(args, p["tables"] / "synthetic_metric_inventory.parquet", p["out"] / "synthetic_metric_inventory_rtz.parquet", backup, label="synthetic_metric_inventory"))
    results.append(replace_event_rows(args, p["tables"] / "qc_inventory_overlap.parquet", p["out"] / "metric_qc_overlap.parquet", backup, label="qc_inventory_overlap"))
    results.append(append_metric_qc_csv(args))
    results.append(replace_event_rows(args, p["tables"] / "metric_rows.parquet", p["metric_rows"], backup, label="metric_rows"))
    results.append(
        run_subprocess(
            [
                str(args.python),
                "-m",
                "spatial_vtk.cli",
                "metrics",
                "outputs",
                "--config",
                str(p["config"]),
                "--metric-rows",
                str(p["tables"] / "metric_rows.parquet"),
                "--event-table",
                str(event_csv(args)),
                "--station-table",
                str(station_csv(args)),
                "--format",
                "parquet",
            ],
            cwd=args.root,
        )
    )
    results.append(
        run_subprocess(
            [
                str(args.python),
                "-m",
                "spatial_vtk.metrics.finalize",
                "--metrics-input",
                str(p["tables"] / "metrics_enriched.parquet"),
                "--output",
                str(p["tables"] / "metrics_final_enriched.parquet"),
            ],
            cwd=args.root,
        )
    )
    summary = {"summary_path": str(p["out"] / f"combine_{stamp}.json"), "backup_dir": str(backup), "results": results}
    Path(summary["summary_path"]).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def metric_counts(df: pd.DataFrame) -> dict[str, int]:
    if "metric" not in df.columns:
        return {}
    return {str(k): int(v) for k, v in df["metric"].value_counts().sort_index().items()}


def validate(args: argparse.Namespace) -> None:
    p = paths(args)
    events = sorted(event_ids_for_batch(args))
    overlap = pd.read_csv(p["out"] / "incremental_overlap_summary.csv")
    validation: dict[str, object] = {
        "batch_name": batch_name(args.batch_name),
        "converted_events": len(events),
        "events": events,
        "overlap_summary_events": int(overlap["event_id"].nunique()) if len(overlap) else 0,
        "events_with_overlap": int((overlap["overlap_stations"] > 0).sum()) if len(overlap) else 0,
        "events_without_observed_overlap": overlap.loc[overlap["overlap_stations"] <= 0, "event_id"].astype(str).tolist() if len(overlap) else [],
        "overlap_stations_total": int(overlap["overlap_stations"].sum()) if len(overlap) else 0,
    }
    for table_name in ("metric_rows", "metrics_long", "metrics_enriched", "metrics_final_enriched"):
        path = p["tables"] / f"{table_name}.parquet"
        df = pd.read_parquet(path)
        sub = df[df["event_id"].astype(str).isin(events)]
        if "model" in sub.columns:
            sub = sub[sub["model"].astype(str).eq(args.model_name)]
        validation[table_name] = {"total_rows": int(len(df)), "batch_rows": int(len(sub)), "batch_events": int(sub["event_id"].nunique()) if len(sub) else 0, "metric_counts": metric_counts(sub)}
        if "period" in sub.columns:
            periods = sorted(float(x) for x in sub["period"].dropna().unique())
            validation[table_name]["spectral_periods"] = periods
    qc = pd.read_parquet(p["tables"] / "qc_inventory_overlap.parquet")
    qc_sub = qc[qc["event_id"].astype(str).isin(events)]
    validation["qc_inventory_overlap"] = {"total_rows": int(len(qc)), "batch_rows": int(len(qc_sub)), "batch_events": int(qc_sub["event_id"].nunique()) if len(qc_sub) else 0}
    marker = p["tables"] / f".{batch_name(args.batch_name)}_metric_qc_csv_appended.json"
    validation["qc_csv_marker_exists"] = marker.exists()
    out_path = p["out"] / "validation_summary.json"
    out_path.write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps(validation, indent=2))


def prep_all(args: argparse.Namespace) -> None:
    convert(args)
    if not event_ids_for_batch(args):
        print(json.dumps({"stage": "prep-all", "status": "no_new_events", "model": args.model_name}))
        return
    write_config(args)
    prepare_qc(args)
    metric_qc = pd.read_parquet(paths(args)["out"] / "metric_qc_overlap.parquet")
    if metric_qc.empty:
        validate(args)
        print(json.dumps({"stage": "prep-all", "status": "no_metric_tasks", "model": args.model_name}))
        return
    pick_catalog = args.arrival_pick_catalog or paths(args)["arrival_pick_catalog"]
    if pick_catalog.exists():
        print(json.dumps({"stage": "pick-arrivals", "status": "using_existing_catalog", "output": str(pick_catalog)}))
    else:
        from spatial_vtk.metrics.calculate.arrival_picks import find_phasenet_command

        if find_phasenet_command(args.phasenet_command):
            pick_arrivals(args)
        else:
            print(
                json.dumps(
                    {
                        "stage": "pick-arrivals",
                        "status": "skipped_no_package_phasenet_cli",
                        "message": "Incremental metrics will use bounded delay; run direct PhaseNet/cycle enrichment after combine.",
                    }
                )
            )
    plan_metrics(args)
    write_slurm(args)


def main() -> None:
    args = parse_args()
    os.environ.setdefault("PYTHONNOUSERSITE", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
    if args.command == "discover":
        discover_missing(args)
    elif args.command == "convert":
        convert(args)
    elif args.command == "prepare-qc":
        prepare_qc(args)
    elif args.command == "pick-arrivals":
        pick_arrivals(args)
    elif args.command == "write-config":
        write_config(args)
    elif args.command == "plan-metrics":
        plan_metrics(args)
    elif args.command == "write-prep-slurm":
        write_prep_slurm(args)
    elif args.command == "submit-prep":
        submit_prep(args)
    elif args.command == "write-slurm":
        write_slurm(args)
    elif args.command == "submit-metrics":
        submit_metrics(args)
    elif args.command == "combine":
        combine(args)
    elif args.command == "validate":
        validate(args)
    elif args.command == "prep-all":
        prep_all(args)
    else:
        raise ValueError(args.command)


if __name__ == "__main__":
    main()
