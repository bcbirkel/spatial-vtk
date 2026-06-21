"""Shared compute and SLURM configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import re
import shlex
import subprocess
import textwrap
from typing import Any

from spatial_vtk.config.runtime import SpatialVTKConfig, deep_merge


@dataclass(frozen=True)
class SlurmSettings:
    """User-provided SLURM resource settings."""

    python_command: str
    environment_setup: tuple[str, ...] = ()
    partition: str = ""
    account: str = ""
    walltime: str = "12:00:00"
    memory: str = "8G"
    cpus_per_task: int = 1
    max_concurrent: int = 10
    job_name: str = "svtk-job"
    log_dir: str = "logs"
    working_directory: str = ""
    submit_command: str = "sbatch"
    extra_directives: tuple[str, ...] = ()


@dataclass(frozen=True)
class SlurmSubmission:
    """Result returned after submitting a SLURM script."""

    script_path: Path
    command: tuple[str, ...]
    stdout: str
    stderr: str
    returncode: int
    job_id: str = ""

    def status_frame(self) -> Any:
        """Return a compact notebook status table for this submission."""

        import pandas as pd

        return pd.DataFrame(
            [
                {
                    "name": "slurm_script",
                    "artifact_label": "SLURM submission script",
                    "artifact_role": "script",
                    "status": "submitted" if self.returncode == 0 else "submission_failed",
                    "job_id": self.job_id,
                    "resolved_path": str(self.script_path),
                    "path": str(self.script_path),
                    "exists": self.script_path.exists(),
                    "script_path": str(self.script_path),
                    "returncode": int(self.returncode),
                    "command": " ".join(self.command),
                    "stdout": self.stdout.strip(),
                    "stderr": self.stderr.strip(),
                }
            ]
        )


def slurm_settings_from_config(config: SpatialVTKConfig, *, section: str | None = None) -> SlurmSettings:
    """Read shared SLURM settings from a Spatial-VTK config.

    ``compute.slurm`` is the shared base section. A task-specific section such
    as ``metrics.slurm`` or ``qc.slurm`` may override it. The older top-level
    ``slurm`` section remains a fallback for backward compatibility.
    """

    payload = dict(config.section("compute.slurm", {}) or {})
    if section:
        payload = deep_merge(payload, dict(config.section(section, {}) or {}))
    if not payload:
        payload = dict(config.section("slurm", {}) or {})
    python_command = str(payload.get("python_command", "")).strip()
    if not python_command:
        location = section or "compute.slurm"
        raise ValueError(f"SLURM config requires {location}.python_command, such as 'python' or an absolute interpreter path.")
    setup = payload.get("environment_setup") or payload.get("setup") or ()
    if isinstance(setup, str):
        setup_lines = tuple(line for line in setup.splitlines() if line.strip())
    else:
        setup_lines = tuple(str(line) for line in setup if str(line).strip())
    extra = payload.get("extra_directives") or ()
    if isinstance(extra, str):
        extra_directives = tuple(line for line in extra.splitlines() if line.strip())
    else:
        extra_directives = tuple(str(line) for line in extra if str(line).strip())
    return SlurmSettings(
        python_command=python_command,
        environment_setup=setup_lines,
        partition=str(payload.get("partition", "") or ""),
        account=str(payload.get("account", "") or ""),
        walltime=_slurm_walltime(payload.get("walltime", payload.get("time", "12:00:00"))),
        memory=str(payload.get("memory", payload.get("mem", "8G"))),
        cpus_per_task=int(payload.get("cpus_per_task", payload.get("cpus", 1))),
        max_concurrent=int(payload.get("max_concurrent", 10)),
        job_name=str(payload.get("job_name", "svtk-job")),
        log_dir=str(payload.get("log_dir", "logs")),
        working_directory=str(payload.get("working_directory", payload.get("workdir", "")) or ""),
        submit_command=str(payload.get("submit_command", "sbatch") or "sbatch"),
        extra_directives=extra_directives,
    )


def slurm_settings_with_overrides(
    config: SpatialVTKConfig,
    *,
    section: str | None = None,
    python_command: str | None = None,
    environment_setup: tuple[str, ...] | list[str] | str | None = None,
    partition: str | None = None,
    account: str | None = None,
    walltime: str | int | float | None = None,
    memory: str | None = None,
    cpus_per_task: int | None = None,
    max_concurrent: int | None = None,
    job_name: str | None = None,
    log_dir: str | Path | None = None,
    working_directory: str | Path | None = None,
    submit_command: str | None = None,
    extra_directives: tuple[str, ...] | list[str] | str | None = None,
) -> SlurmSettings:
    """Read SLURM settings and apply explicit overrides.

    This is useful for notebooks and workflow drivers that should inherit the
    configured environment setup while varying job name, memory, time, or CPU
    count for one task.
    """

    settings = slurm_settings_from_config(config, section=section)
    updates: dict[str, object] = {}
    if python_command is not None:
        updates["python_command"] = str(python_command)
    if environment_setup is not None:
        updates["environment_setup"] = _as_lines(environment_setup)
    if partition is not None:
        updates["partition"] = str(partition)
    if account is not None:
        updates["account"] = str(account)
    if walltime is not None:
        updates["walltime"] = _slurm_walltime(walltime)
    if memory is not None:
        updates["memory"] = str(memory)
    if cpus_per_task is not None:
        updates["cpus_per_task"] = int(cpus_per_task)
    if max_concurrent is not None:
        updates["max_concurrent"] = int(max_concurrent)
    if job_name is not None:
        updates["job_name"] = str(job_name)
    if log_dir is not None:
        updates["log_dir"] = str(log_dir)
    if working_directory is not None:
        updates["working_directory"] = str(working_directory)
    if submit_command is not None:
        updates["submit_command"] = str(submit_command)
    if extra_directives is not None:
        updates["extra_directives"] = _as_lines(extra_directives)
    return replace(settings, **updates)


def _slurm_walltime(value: Any) -> str:
    """Normalize YAML-parsed Slurm walltime values to ``HH:MM:SS``."""

    if value in (None, ""):
        return "12:00:00"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        total_seconds = int(value)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    text = str(value).strip()
    if text.isdigit():
        total_seconds = int(text)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return text


def _as_lines(value: tuple[str, ...] | list[str] | str) -> tuple[str, ...]:
    """Normalize a string or sequence into non-empty shell lines."""

    if isinstance(value, str):
        return tuple(line for line in value.splitlines() if line.strip())
    return tuple(str(line) for line in value if str(line).strip())


def slurm_header(settings: SlurmSettings, *, array: str | None = None) -> list[str]:
    """Build common SLURM header and environment lines."""

    lines = [
        "#!/bin/bash",
        f"#SBATCH --job-name={settings.job_name}",
        f"#SBATCH --time={settings.walltime}",
        f"#SBATCH --cpus-per-task={int(settings.cpus_per_task)}",
        f"#SBATCH --mem={settings.memory}",
        f"#SBATCH --output={settings.log_dir}/%x_%j.out",
        f"#SBATCH --error={settings.log_dir}/%x_%j.err",
    ]
    if array:
        lines.insert(2, f"#SBATCH --array={array}")
        lines[-2] = f"#SBATCH --output={settings.log_dir}/%x_%A_%a.out"
        lines[-1] = f"#SBATCH --error={settings.log_dir}/%x_%A_%a.err"
    if settings.partition:
        lines.append(f"#SBATCH --partition={settings.partition}")
    if settings.account:
        lines.append(f"#SBATCH --account={settings.account}")
    lines.extend(settings.extra_directives)
    lines.extend(
        [
            "",
            "set -euo pipefail",
            f"mkdir -p {settings.log_dir}",
            "export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}",
            "export MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}",
            "export OPENBLAS_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}",
            "",
        ]
    )
    if settings.working_directory:
        lines.extend([f"cd {settings.working_directory}", ""])
    lines.extend(settings.environment_setup)
    if settings.environment_setup:
        lines.append("")
    return lines


def submit_slurm_script(script_path: str | Path, settings: SlurmSettings | None = None) -> SlurmSubmission:
    """Submit a SLURM script with ``sbatch`` or ``settings.submit_command``."""

    script = Path(script_path).expanduser()
    submit_command = settings.submit_command if settings is not None else "sbatch"
    command = (*shlex.split(submit_command), str(script))
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    stdout = result.stdout.strip()
    match = re.search(r"\b(\d+)\b", stdout)
    return SlurmSubmission(
        script_path=script,
        command=command,
        stdout=stdout,
        stderr=result.stderr.strip(),
        returncode=int(result.returncode),
        job_id=match.group(1) if match else "",
    )


def write_inline_python_slurm_script(
    script_path: str | Path,
    python_body: str,
    settings: SlurmSettings,
    *,
    here_doc_token: str = "PYJOB",
) -> Path:
    """Write a SLURM script that runs an inline Python body.

    Parameters
    ----------
    script_path
        Destination shell script.
    python_body
        Python source code to execute inside the job.
    settings
        Normalized SLURM settings. The configured ``python_command``,
        environment setup, log directory, and working directory are used.
    here_doc_token
        Shell here-document marker. Override only if the Python body contains
        the default marker.

    Returns
    -------
    pathlib.Path
        Written executable script path.
    """

    target = Path(script_path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    body = textwrap.dedent(python_body).strip()
    token = str(here_doc_token).strip() or "PYJOB"
    lines = slurm_header(settings)
    lines.extend(
        [
            f"{settings.python_command} - <<'{token}'",
            body,
            token,
            "",
        ]
    )
    target.write_text("\n".join(lines), encoding="utf-8")
    target.chmod(0o755)
    return target


def submit_or_print_slurm_script(
    script_path: str | Path,
    *,
    settings: SlurmSettings | None = None,
    submit: bool = False,
) -> SlurmSubmission | None:
    """Submit a SLURM script or print the manual submission command.

    Parameters
    ----------
    script_path
        Script to submit.
    settings
        Optional settings that provide the submit command.
    submit
        When true, run ``sbatch`` or ``settings.submit_command``. When false,
        print a manual submission command and return ``None``.

    Returns
    -------
    SlurmSubmission or None
        Submission details when submitted; otherwise ``None``.
    """

    script = Path(script_path).expanduser()
    print(f"script: {script}")
    if not submit:
        submit_command = settings.submit_command if settings is not None else "sbatch"
        command = " ".join([*shlex.split(submit_command), shlex.quote(str(script))])
        print("Set submit=True, or submit manually:")
        print(command)
        return None
    result = submit_slurm_script(script, settings)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"SLURM submit failed with return code {result.returncode}")
    return result


__all__ = [
    "SlurmSettings",
    "SlurmSubmission",
    "slurm_header",
    "slurm_settings_from_config",
    "slurm_settings_with_overrides",
    "submit_or_print_slurm_script",
    "submit_slurm_script",
    "write_inline_python_slurm_script",
]
