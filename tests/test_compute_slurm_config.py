from __future__ import annotations

from pathlib import Path

import pytest

from spatial_vtk.config import SpatialVTKConfig
from spatial_vtk.config.compute import (
    SlurmSettings,
    slurm_header,
    slurm_settings_from_config,
    submit_slurm_script,
)


def test_shared_slurm_settings_support_task_overrides() -> None:
    """Task-specific SLURM sections should override shared compute defaults."""

    cfg = SpatialVTKConfig(
        None,
        Path(".").resolve(),
        {
            "compute": {
                "slurm": {
                    "python_command": "python",
                    "partition": "shared",
                    "memory": "16G",
                    "cpus": 2,
                    "environment_setup": ["mamba activate spatial-vtk"],
                }
            },
            "qc": {"slurm": {"memory": "32G", "job_name": "svtk-qc"}},
        },
    )

    settings = slurm_settings_from_config(cfg, section="qc.slurm")

    assert settings.python_command == "python"
    assert settings.partition == "shared"
    assert settings.memory == "32G"
    assert settings.cpus_per_task == 2
    assert settings.job_name == "svtk-qc"
    assert settings.environment_setup == ("mamba activate spatial-vtk",)


def test_slurm_settings_normalize_yaml_sexagesimal_walltime() -> None:
    """Unquoted YAML times may parse as seconds and still need Slurm syntax."""

    cfg = SpatialVTKConfig(
        None,
        Path(".").resolve(),
        {
            "compute": {
                "slurm": {
                    "python_command": "python",
                    "walltime": 86400,
                }
            },
        },
    )

    settings = slurm_settings_from_config(cfg, section="qc.slurm")

    assert settings.walltime == "24:00:00"


def test_slurm_settings_require_python_command() -> None:
    """SLURM settings should fail early when no Python command is configured."""

    cfg = SpatialVTKConfig.empty(root_dir=".")

    with pytest.raises(ValueError, match="python_command"):
        slurm_settings_from_config(cfg, section="qc.slurm")


def test_slurm_header_supports_array_logs_and_environment_setup() -> None:
    """Shared SLURM headers should support array jobs and setup commands."""

    settings = SlurmSettings(
        python_command="python",
        environment_setup=("source ~/.bashrc", "conda activate spatial-vtk"),
        job_name="svtk-metrics",
        log_dir="outputs/logs",
        max_concurrent=4,
        working_directory="/project/spatial-vtk",
    )

    header = "\n".join(slurm_header(settings, array="0-9%4"))

    assert "#SBATCH --array=0-9%4" in header
    assert "#SBATCH --output=outputs/logs/%x_%A_%a.out" in header
    assert "cd /project/spatial-vtk" in header
    assert "conda activate spatial-vtk" in header


def test_submit_slurm_script_splits_submit_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Submit commands may include extra arguments such as ``--parsable``."""

    script = tmp_path / "job.slurm"
    script.write_text("#!/bin/bash\n", encoding="utf-8")
    captured: dict[str, object] = {}

    class Result:
        stdout = "Submitted batch job 12345\n"
        stderr = ""
        returncode = 0

    def fake_run(command: tuple[str, ...], **kwargs: object) -> Result:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return Result()

    monkeypatch.setattr("spatial_vtk.config.compute.subprocess.run", fake_run)
    settings = SlurmSettings(python_command="python", submit_command="sbatch --parsable")

    submission = submit_slurm_script(script, settings)

    assert captured["command"] == ("sbatch", "--parsable", str(script))
    assert submission.job_id == "12345"
