"""SLURM helpers for QC inventory workflows."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import shlex

from spatial_vtk.config.compute import (
    SlurmSettings,
    slurm_header,
    slurm_settings_from_config as _shared_slurm_settings_from_config,
    submit_slurm_script,
)
from spatial_vtk.config.metrics import metrics_settings_from_config
from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.config.runtime import SpatialVTKConfig
from spatial_vtk.io.tables import read_table
from spatial_vtk.qc.build.workflow import build_metric_qc_summary, build_waveform_qc_summary


def slurm_settings_from_config(config: SpatialVTKConfig, *, section: str = "qc.slurm") -> SlurmSettings:
    """Read QC SLURM settings from ``compute.slurm`` plus ``qc.slurm`` overrides."""

    settings = _shared_slurm_settings_from_config(config, section=section)
    if settings.job_name == "svtk-job":
        return replace(settings, job_name="svtk-qc")
    return settings


def run_qc_inventory_job(
    event_station_records: str | Path,
    *,
    config: SpatialVTKConfig,
    trace_qc_output: str | Path | None = None,
    qc_inventory_output: str | Path | None = None,
    verbose: bool = True,
) -> dict[str, Path]:
    """Run the standard waveform and metric QC inventory workflow."""

    config.activate()
    event_stations = read_table(event_station_records)
    metric_settings = metrics_settings_from_config(config)
    trace_path = (
        Path(trace_qc_output).expanduser()
        if trace_qc_output
        else resolve_output_path("qc_trace_summary", kind="table", cfg=config, create_parent=True)
    )
    inventory_path = (
        Path(qc_inventory_output).expanduser()
        if qc_inventory_output
        else resolve_output_path("qc_inventory", kind="table", cfg=config, create_parent=True)
    )
    build_waveform_qc_summary(
        event_stations,
        components=metric_settings.components,
        passbands=metric_settings.passbands,
        verbose=verbose,
        checkpoint_path=trace_path,
        return_result=False,
    )
    build_metric_qc_summary(
        event_stations,
        metrics=metric_settings.metrics,
        components=metric_settings.components,
        passbands=metric_settings.passbands,
        spectral_periods_s=metric_settings.spectral.periods_s,
        synthetic_max_frequency_hz=metric_settings.synthetic_max_frequency_hz,
        require_source_overlap=metric_settings.require_source_overlap,
        source_overlap_scope=metric_settings.source_overlap_scope,
        trace_qc_summary=trace_path,
        verbose=verbose,
        checkpoint_path=inventory_path,
        return_result=False,
    )
    return {"qc_trace_summary": trace_path, "qc_inventory": inventory_path}


def write_qc_slurm_script(
    event_station_records: str | Path,
    script_path: str | Path,
    settings: SlurmSettings,
    *,
    config_path: str | Path,
    run_scenario: str | None = None,
    trace_qc_output: str | Path | None = None,
    qc_inventory_output: str | Path | None = None,
) -> Path:
    """Write a SLURM script that builds QC trace and inventory tables."""

    target = Path(script_path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    args = [
        f"--event-stations {shlex.quote(str(Path(event_station_records).expanduser().resolve()))}",
        f"--config {shlex.quote(str(Path(config_path).expanduser().resolve()))}",
    ]
    if run_scenario:
        args.append(f"--run-scenario {shlex.quote(str(run_scenario))}")
    if trace_qc_output:
        args.append(
            f"--trace-output {shlex.quote(str(Path(trace_qc_output).expanduser().resolve()))}"
        )
    if qc_inventory_output:
        args.append(
            f"--inventory-output {shlex.quote(str(Path(qc_inventory_output).expanduser().resolve()))}"
        )
    lines = slurm_header(settings)
    lines.extend(
        [
            f"{settings.python_command} -m spatial_vtk.qc.build.slurm {' '.join(args)}",
            "",
        ]
    )
    target.write_text("\n".join(lines), encoding="utf-8")
    target.chmod(0o755)
    return target


def submit_qc_slurm_job(
    event_station_records: str | Path,
    script_path: str | Path,
    settings: SlurmSettings,
    *,
    config_path: str | Path,
    run_scenario: str | None = None,
    trace_qc_output: str | Path | None = None,
    qc_inventory_output: str | Path | None = None,
):
    """Write and submit a SLURM job for the QC inventory workflow."""

    script = write_qc_slurm_script(
        event_station_records,
        script_path,
        settings,
        config_path=config_path,
        run_scenario=run_scenario,
        trace_qc_output=trace_qc_output,
        qc_inventory_output=qc_inventory_output,
    )
    return submit_slurm_script(script, settings)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the QC SLURM worker parser."""

    parser = argparse.ArgumentParser(description="Run or script Spatial-VTK QC inventory jobs.")
    parser.add_argument("--event-stations", required=True, help="Prepared event-station table.")
    parser.add_argument("--config", required=True, help="Spatial-VTK config YAML/JSON.")
    parser.add_argument("--run-scenario", default=None, help="Apply one named run_scenarios overlay.")
    parser.add_argument("--trace-output", default=None, help="Output waveform QC table path.")
    parser.add_argument("--inventory-output", default=None, help="Output metric QC inventory path.")
    parser.add_argument("--quiet", action="store_true", help="Disable progress messages.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the QC inventory worker from CLI arguments."""

    args = build_arg_parser().parse_args(argv)
    config = SpatialVTKConfig.from_file(args.config, run_scenario=args.run_scenario)
    written = run_qc_inventory_job(
        args.event_stations,
        config=config,
        trace_qc_output=args.trace_output,
        qc_inventory_output=args.inventory_output,
        verbose=not args.quiet,
    )
    for key, path in written.items():
        print(f"{key}: {path}")
    return 0


__all__ = [
    "build_arg_parser",
    "main",
    "run_qc_inventory_job",
    "slurm_settings_from_config",
    "submit_qc_slurm_job",
    "write_qc_slurm_script",
]


if __name__ == "__main__":
    raise SystemExit(main())
