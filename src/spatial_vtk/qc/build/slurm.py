"""SLURM helpers for QC inventory workflows."""

from __future__ import annotations

import argparse
from pathlib import Path
import shlex
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from spatial_vtk.config.compute import SlurmSettings
    from spatial_vtk.config.runtime import SpatialVTKConfig


def slurm_settings_from_config(config: SpatialVTKConfig, *, section: str = "qc.slurm") -> SlurmSettings:
    """Read QC SLURM settings from ``compute.slurm`` plus ``qc.slurm`` overrides."""

    from dataclasses import replace

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
    qc_inventory_overlap_output: str | Path | None = None,
    verbose: bool = True,
) -> dict[str, Path]:
    """Run the standard waveform and metric QC inventory workflow."""

    from spatial_vtk.qc.build.workflow import (
        build_metric_qc_summary,
        build_waveform_qc_summary,
        write_qc_inventory_overlap_from_full,
    )

    config.activate()
    event_stations = _read_table(event_station_records)
    metric_settings = _metrics_settings_from_config(config)
    trace_path = (
        Path(trace_qc_output).expanduser()
        if trace_qc_output
        else _resolve_output_path("qc_trace_summary", kind="table", cfg=config, create_parent=True)
    )
    inventory_path = (
        Path(qc_inventory_output).expanduser()
        if qc_inventory_output
        else _resolve_output_path("qc_inventory", kind="table", cfg=config, create_parent=True)
    )
    overlap_inventory_path = (
        Path(qc_inventory_overlap_output).expanduser()
        if qc_inventory_overlap_output
        else _resolve_output_path("qc_inventory_overlap", kind="table", cfg=config, create_parent=True)
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
        trace_qc_summary=trace_path,
        verbose=verbose,
        checkpoint_path=inventory_path,
        return_result=False,
    )
    overlap_stale = (
        not overlap_inventory_path.exists()
        or (inventory_path.exists() and inventory_path.stat().st_mtime > overlap_inventory_path.stat().st_mtime)
    )
    write_qc_inventory_overlap_from_full(
        inventory_path,
        event_stations,
        overlap_inventory_path,
        scope=metric_settings.source_overlap_scope,
        overwrite=overlap_stale,
        verbose=verbose,
    )
    return {
        "qc_trace_summary": trace_path,
        "qc_inventory": inventory_path,
        "qc_inventory_overlap": overlap_inventory_path,
    }


def run_qc_inventory_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    event_station_records: str | Path | None = None,
    trace_qc_output: str | Path | None = None,
    qc_inventory_output: str | Path | None = None,
    qc_inventory_overlap_output: str | Path | None = None,
    verbose: bool = True,
) -> dict[str, str]:
    """Run the configured QC inventory workflow and return written paths.

    This wrapper gives notebooks and generated workers a JSON-serializable entry
    point. All paths default to the active config/output registry, so notebooks
    do not need to duplicate QC path plumbing.
    """

    SpatialVTKConfig = _spatial_vtk_config_type()
    config = (
        SpatialVTKConfig.from_file(config_path, run_scenario=run_scenario).activate()
        if config_path is not None
        else _active_config()
    )
    if config_path is None and run_scenario:
        config = SpatialVTKConfig.from_file(config.config_path, run_scenario=run_scenario).activate()
    event_station_path = (
        Path(event_station_records).expanduser()
        if event_station_records is not None
        else _resolve_output_path("event_station_records", kind="table", cfg=config, create_parent=True)
    )
    written = run_qc_inventory_job(
        event_station_path,
        config=config,
        trace_qc_output=trace_qc_output,
        qc_inventory_output=qc_inventory_output,
        qc_inventory_overlap_output=qc_inventory_overlap_output,
        verbose=verbose,
    )
    payload = {f"{key}_path": str(path) for key, path in written.items()}
    payload.update({key: str(path) for key, path in written.items()})
    return payload


def write_qc_slurm_script(
    event_station_records: str | Path,
    script_path: str | Path,
    settings: SlurmSettings,
    *,
    config_path: str | Path,
    run_scenario: str | None = None,
    trace_qc_output: str | Path | None = None,
    qc_inventory_output: str | Path | None = None,
    qc_inventory_overlap_output: str | Path | None = None,
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
            f"--qc-trace-summary-output {shlex.quote(str(Path(trace_qc_output).expanduser().resolve()))}"
        )
    if qc_inventory_output:
        args.append(
            f"--qc-inventory-output {shlex.quote(str(Path(qc_inventory_output).expanduser().resolve()))}"
        )
    if qc_inventory_overlap_output:
        args.append(
            f"--qc-overlap-inventory-output {shlex.quote(str(Path(qc_inventory_overlap_output).expanduser().resolve()))}"
        )
    lines = _slurm_header(settings)
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
    qc_inventory_overlap_output: str | Path | None = None,
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
        qc_inventory_overlap_output=qc_inventory_overlap_output,
    )
    return _submit_slurm_script(script, settings)


def _shared_slurm_settings_from_config(*args: Any, **kwargs: Any) -> Any:
    """Load shared Slurm settings only when QC Slurm settings are requested."""

    from spatial_vtk.config.compute import slurm_settings_from_config

    return slurm_settings_from_config(*args, **kwargs)


def _slurm_header(*args: Any, **kwargs: Any) -> list[str]:
    """Load shared Slurm header rendering only when writing a script."""

    from spatial_vtk.config.compute import slurm_header

    return slurm_header(*args, **kwargs)


def _submit_slurm_script(*args: Any, **kwargs: Any) -> Any:
    """Load shared Slurm submission only when submitting a script."""

    from spatial_vtk.config.compute import submit_slurm_script

    return submit_slurm_script(*args, **kwargs)


def _metrics_settings_from_config(*args: Any, **kwargs: Any) -> Any:
    """Load metric config parsing only when a QC job runs."""

    from spatial_vtk.config.metrics import metrics_settings_from_config

    return metrics_settings_from_config(*args, **kwargs)


def _resolve_output_path(*args: Any, **kwargs: Any) -> Path:
    """Load output-registry resolution only when configured outputs are needed."""

    from spatial_vtk.config.outputs import resolve_output_path

    return resolve_output_path(*args, **kwargs)


def _active_config() -> Any:
    """Load the active-config runtime only when a configured QC job runs."""

    from spatial_vtk.config.runtime import active_config

    return active_config()


def _spatial_vtk_config_type() -> Any:
    """Load the config class only when parsing a config path."""

    from spatial_vtk.config.runtime import SpatialVTKConfig

    return SpatialVTKConfig


def _read_table(*args: Any, **kwargs: Any) -> Any:
    """Load shared table reading only when the QC worker reads inputs."""

    from spatial_vtk.io.tables import read_table

    return read_table(*args, **kwargs)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the QC SLURM worker parser."""

    parser = argparse.ArgumentParser(description="Run or script Spatial-VTK QC inventory jobs.")
    parser.add_argument(
        "--event-station-records",
        "--event-stations",
        dest="event_stations",
        required=True,
        help="Prepared event-station records table. Prefer --event-station-records; --event-stations is a legacy alias.",
    )
    parser.add_argument("--config", required=True, help="Spatial-VTK config YAML/JSON.")
    parser.add_argument("--run-scenario", default=None, help="Apply one named run_scenarios overlay.")
    parser.add_argument(
        "--qc-trace-summary-output",
        "--trace-output",
        dest="trace_output",
        default=None,
        help="Output QC trace-summary table path. Prefer --qc-trace-summary-output; --trace-output is a legacy alias.",
    )
    parser.add_argument(
        "--qc-inventory-output",
        "--inventory-output",
        dest="inventory_output",
        default=None,
        help="Output metric QC inventory table path. Prefer --qc-inventory-output; --inventory-output is a legacy alias.",
    )
    parser.add_argument(
        "--qc-overlap-inventory-output",
        "--overlap-inventory-output",
        dest="overlap_inventory_output",
        default=None,
        help=(
            "Output observed/synthetic-overlap metric QC inventory path. "
            "Prefer --qc-overlap-inventory-output; --overlap-inventory-output is a legacy alias."
        ),
    )
    parser.add_argument("--quiet", action="store_true", help="Disable progress messages.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the QC inventory worker from CLI arguments."""

    args = build_arg_parser().parse_args(argv)
    SpatialVTKConfig = _spatial_vtk_config_type()
    config = SpatialVTKConfig.from_file(args.config, run_scenario=args.run_scenario)
    written = run_qc_inventory_job(
        args.event_stations,
        config=config,
        trace_qc_output=args.trace_output,
        qc_inventory_output=args.inventory_output,
        qc_inventory_overlap_output=args.overlap_inventory_output,
        verbose=not args.quiet,
    )
    for key, path in written.items():
        print(f"{key}: {path}")
    return 0


__all__ = [
    "build_arg_parser",
    "main",
    "run_qc_inventory_from_config",
    "run_qc_inventory_job",
    "slurm_settings_from_config",
    "submit_qc_slurm_job",
    "write_qc_slurm_script",
]


if __name__ == "__main__":
    raise SystemExit(main())
