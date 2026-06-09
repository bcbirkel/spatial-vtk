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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from spatial_vtk.config.runtime import SpatialVTKConfig
from spatial_vtk.metrics.workflow.execution import read_task_manifest


@dataclass(frozen=True)
class SlurmSettings:
    """User-provided SLURM resource settings.

    Parameters
    ----------
    python_command
        Command that can run Python modules in the user's environment, for
        example ``python`` after activation or an absolute interpreter path.
    environment_setup
        Optional shell lines that load modules or activate an environment.
    partition, account, walltime, memory, cpus_per_task, max_concurrent
        Standard SLURM resource settings.
    job_name
        SLURM job name.
    log_dir
        Directory for SLURM stdout/stderr logs.

    Returns
    -------
    SlurmSettings
        Immutable settings object.
    """

    python_command: str
    environment_setup: tuple[str, ...] = ()
    partition: str = ""
    account: str = ""
    walltime: str = "12:00:00"
    memory: str = "8G"
    cpus_per_task: int = 1
    max_concurrent: int = 10
    job_name: str = "svtk-metrics"
    log_dir: str = "logs"


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

    payload = dict(config.section(section, {}) or {})
    if not payload:
        payload = dict(config.section("slurm", {}) or {})
    python_command = str(payload.get("python_command", "")).strip()
    if not python_command:
        raise ValueError("SLURM config requires metrics.slurm.python_command, such as 'python' or an absolute interpreter path.")
    setup = payload.get("environment_setup") or payload.get("setup") or ()
    if isinstance(setup, str):
        setup_lines = tuple(line for line in setup.splitlines() if line.strip())
    else:
        setup_lines = tuple(str(line) for line in setup if str(line).strip())
    return SlurmSettings(
        python_command=python_command,
        environment_setup=setup_lines,
        partition=str(payload.get("partition", "") or ""),
        account=str(payload.get("account", "") or ""),
        walltime=str(payload.get("walltime", payload.get("time", "12:00:00"))),
        memory=str(payload.get("memory", payload.get("mem", "8G"))),
        cpus_per_task=int(payload.get("cpus_per_task", payload.get("cpus", 1))),
        max_concurrent=int(payload.get("max_concurrent", 10)),
        job_name=str(payload.get("job_name", "svtk-metrics")),
        log_dir=str(payload.get("log_dir", "logs")),
    )


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
    log_dir = Path(settings.log_dir)
    last_index = len(manifest.batches) - 1
    lines = [
        "#!/bin/bash",
        f"#SBATCH --job-name={settings.job_name}",
        f"#SBATCH --array=0-{last_index}%{max(1, int(settings.max_concurrent))}",
        f"#SBATCH --time={settings.walltime}",
        f"#SBATCH --cpus-per-task={int(settings.cpus_per_task)}",
        f"#SBATCH --mem={settings.memory}",
        f"#SBATCH --output={log_dir}/%x_%A_%a.out",
        f"#SBATCH --error={log_dir}/%x_%A_%a.err",
    ]
    if settings.partition:
        lines.append(f"#SBATCH --partition={settings.partition}")
    if settings.account:
        lines.append(f"#SBATCH --account={settings.account}")
    lines.extend(
        [
            "",
            "set -euo pipefail",
            f"mkdir -p {log_dir}",
            "export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}",
            "export MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}",
            "export OPENBLAS_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}",
            "",
        ]
    )
    lines.extend(settings.environment_setup)
    if settings.environment_setup:
        lines.append("")
    lines.extend(
        [
            f"{settings.python_command} -m spatial_vtk.metrics.workflow.execution --manifest {manifest_abs} --batch-index $SLURM_ARRAY_TASK_ID",
            "",
        ]
    )
    target.write_text("\n".join(lines), encoding="utf-8")
    target.chmod(0o755)
    return target


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
    "write_metrics_slurm_script",
]


if __name__ == "__main__":
    raise SystemExit(main())
