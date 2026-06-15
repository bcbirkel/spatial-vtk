"""Generic SLURM support for metric workflow batches.

Purpose
-------
This module writes portable SLURM array scripts for metric workflow manifests.
It does not submit jobs unless a caller explicitly runs ``sbatch`` outside this
module.

Usage examples
--------------
Write a script from config settings:
  ``write_metrics_slurm_script("manifest.json", "run_metrics.slurm", settings)``
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from spatial_vtk.config.compute import (
    SlurmSettings,
    slurm_header,
    slurm_settings_from_config as _shared_slurm_settings_from_config,
    submit_slurm_script,
)
from spatial_vtk.config.runtime import SpatialVTKConfig
from spatial_vtk.metrics.workflow.execution import read_task_manifest


def slurm_settings_from_config(config: SpatialVTKConfig, *, section: str = "metrics.slurm") -> SlurmSettings:
    """Read SLURM settings from a public config object.

    Parameters
    ----------
    config
        Loaded Spatial-VTK config.
    section
        Dotted section key. ``metrics.slurm`` is checked first, then
        top-level ``slurm`` as a fallback.

    Returns
    -------
    SlurmSettings
        Normalized SLURM settings.
    """

    settings = _shared_slurm_settings_from_config(config, section=section)
    if settings.job_name == "svtk-job":
        return replace(settings, job_name="svtk-metrics")
    return settings


def write_metrics_slurm_script(
    manifest_path: str | Path,
    script_path: str | Path,
    settings: SlurmSettings,
) -> Path:
    """Write a SLURM array script for a metric workflow manifest.

    Parameters
    ----------
    manifest_path
        Metric workflow manifest JSON.
    script_path
        Destination shell script.
    settings
        User-provided SLURM settings.

    Returns
    -------
    pathlib.Path
        Written script path.
    """

    manifest = read_task_manifest(manifest_path)
    if not manifest.batches:
        raise ValueError("Cannot write a SLURM script for a manifest with no batches.")
    target = Path(script_path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest_abs = Path(manifest_path).expanduser().resolve()
    last_index = len(manifest.batches) - 1
    lines = slurm_header(settings, array=f"0-{last_index}%{max(1, int(settings.max_concurrent))}")
    lines.extend(
        [
            f'echo "Metric Slurm array: task $SLURM_ARRAY_TASK_ID of {len(manifest.batches)} batch(es)"',
            f'echo "Metric manifest: {manifest_abs}"',
            f'echo "Metric max concurrent batches: {max(1, int(settings.max_concurrent))}"',
            f"{settings.python_command} -m spatial_vtk.metrics.workflow.execution --manifest {manifest_abs} --batch-index $SLURM_ARRAY_TASK_ID",
            "",
        ]
    )
    target.write_text("\n".join(lines), encoding="utf-8")
    target.chmod(0o755)
    return target


def submit_metrics_slurm_job(
    manifest_path: str | Path,
    script_path: str | Path,
    settings: SlurmSettings,
):
    """Write and submit a SLURM array script for a metric workflow manifest."""

    script = write_metrics_slurm_script(manifest_path, script_path, settings)
    return submit_slurm_script(script, settings)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the SLURM script CLI parser.

    Parameters
    ----------
    None

    Returns
    -------
    argparse.ArgumentParser
        Parser for script-writing arguments.
    """

    parser = argparse.ArgumentParser(description="Write a generic SLURM script for Spatial-VTK metric batches.")
    parser.add_argument("--manifest", required=True, help="Metric workflow manifest JSON.")
    parser.add_argument("--output", required=True, help="Output SLURM script path.")
    parser.add_argument("--config", default=None, help="Spatial-VTK config with metrics.slurm settings.")
    parser.add_argument("--run-scenario", default=None, help="Apply one named run_scenarios overlay.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Write a SLURM script from CLI arguments.

    Parameters
    ----------
    argv
        Optional argument list.

    Returns
    -------
    int
        Process exit code.
    """

    args = build_arg_parser().parse_args(argv)
    config = (
        SpatialVTKConfig.from_file(args.config, run_scenario=args.run_scenario)
        if args.config
        else SpatialVTKConfig.empty(root_dir=".")
    )
    settings = slurm_settings_from_config(config)
    write_metrics_slurm_script(args.manifest, args.output, settings)
    return 0


__all__ = [
    "SlurmSettings",
    "build_arg_parser",
    "main",
    "slurm_settings_from_config",
    "submit_metrics_slurm_job",
    "write_metrics_slurm_script",
]


if __name__ == "__main__":
    raise SystemExit(main())
