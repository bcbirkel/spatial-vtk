"""Metric Slurm array support for manifest batches.

Purpose
-------
This module writes portable Slurm array scripts for metric workflow manifests.
Each array task runs one manifest batch and writes the batch's configured
metric row output file. ``write_metrics_slurm_script`` only writes a script;
``submit_metrics_slurm_job`` is the explicit submission helper.

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
    *,
    batch_indices: list[int] | tuple[int, ...] | None = None,
    overwrite_batches: bool = False,
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
    batch_indices
        Optional manifest batch indices to include in the array. When omitted,
        the script includes every planned batch.
    overwrite_batches
        Whether array tasks should replace existing batch outputs.

    Returns
    -------
    pathlib.Path
        Written script path.
    """

    from spatial_vtk.metrics.workflow.execution import read_task_manifest

    manifest = read_task_manifest(manifest_path)
    if not manifest.batches:
        raise ValueError("Cannot write a SLURM script for a manifest with no batches.")
    selected_indices = _selected_batch_indices(manifest, batch_indices=batch_indices)
    if not selected_indices:
        raise ValueError("Cannot write a SLURM script because no metric batches were selected.")
    target = Path(script_path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest_abs = Path(manifest_path).expanduser().resolve()
    array_spec = _slurm_array_spec(selected_indices, max_concurrent=max(1, int(settings.max_concurrent)))
    overwrite_flag = " --overwrite" if overwrite_batches else ""
    lines = slurm_header(settings, array=array_spec)
    lines.extend(
        [
            f'echo "Metric Slurm array: task $SLURM_ARRAY_TASK_ID of {len(manifest.batches)} batch(es)"',
            f'echo "Metric selected batches: {len(selected_indices)} of {len(manifest.batches)}"',
            f'echo "Metric manifest: {manifest_abs}"',
            f'echo "Metric max concurrent batches: {max(1, int(settings.max_concurrent))}"',
            f"{settings.python_command} -m spatial_vtk.metrics.workflow.execution --manifest {manifest_abs} --batch-index $SLURM_ARRAY_TASK_ID{overwrite_flag}",
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
    *,
    batch_indices: list[int] | tuple[int, ...] | None = None,
    overwrite_batches: bool = False,
):
    """Write and submit a SLURM array script for a metric workflow manifest."""

    script = write_metrics_slurm_script(
        manifest_path,
        script_path,
        settings,
        batch_indices=batch_indices,
        overwrite_batches=overwrite_batches,
    )
    return submit_slurm_script(script, settings)


def _selected_batch_indices(manifest, *, batch_indices: list[int] | tuple[int, ...] | None) -> tuple[int, ...]:
    """Return validated batch indices for one Slurm array."""

    available = {int(batch["batch_index"]) for batch in manifest.batches}
    if batch_indices is None:
        return tuple(sorted(available))
    selected = tuple(dict.fromkeys(int(index) for index in batch_indices))
    missing = [index for index in selected if index not in available]
    if missing:
        raise ValueError(f"Metric manifest does not contain batch indices: {missing}")
    return tuple(sorted(selected))


def _slurm_array_spec(indices: tuple[int, ...], *, max_concurrent: int) -> str:
    """Return a compact Slurm array expression for selected indices."""

    if not indices:
        raise ValueError("At least one batch index is required.")
    ranges: list[str] = []
    start = previous = int(indices[0])
    for raw_index in indices[1:]:
        index = int(raw_index)
        if index == previous + 1:
            previous = index
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = index
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return f"{','.join(ranges)}%{max(1, int(max_concurrent))}"


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the metric Slurm array script CLI parser.

    Parameters
    ----------
    None

    Returns
    -------
    argparse.ArgumentParser
        Parser for script-writing arguments.
    """

    parser = argparse.ArgumentParser(description="Write a metric Slurm array script from a Spatial-VTK manifest.")
    parser.add_argument("--manifest", required=True, help="Metric workflow manifest JSON with batch output paths.")
    parser.add_argument("--output", required=True, help="Output metric Slurm array script path.")
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
    path = write_metrics_slurm_script(args.manifest, args.output, settings)
    print(f"Wrote metric Slurm script: {path}")
    print("No job was submitted. Submit the script with sbatch.")
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
