from __future__ import annotations

from pathlib import Path

import pytest

from spatial_vtk.config import SpatialVTKConfig
from spatial_vtk.config.compute import (
    SlurmSettings,
    SlurmSubmission,
    slurm_header,
    slurm_settings_from_config,
    slurm_settings_with_overrides,
    submit_or_print_slurm_script,
    submit_slurm_script,
    write_inline_python_slurm_script,
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


def test_slurm_settings_with_overrides_preserves_configured_environment() -> None:
    """Task overrides should not require notebooks to hard-code environment setup."""

    cfg = SpatialVTKConfig(
        None,
        Path(".").resolve(),
        {
            "compute": {
                "slurm": {
                    "python_command": "python",
                    "walltime": "01:00:00",
                    "memory": "8G",
                    "environment_setup": ["module load python"],
                    "log_dir": "logs",
                }
            },
        },
    )

    settings = slurm_settings_with_overrides(
        cfg,
        job_name="svtk-step",
        walltime="02:00:00",
        memory="24G",
        cpus_per_task=4,
        working_directory="/project",
    )

    assert settings.python_command == "python"
    assert settings.environment_setup == ("module load python",)
    assert settings.job_name == "svtk-step"
    assert settings.walltime == "02:00:00"
    assert settings.memory == "24G"
    assert settings.cpus_per_task == 4
    assert settings.working_directory == "/project"


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
    status = submission.status_frame()
    assert status.loc[0, "status"] == "submitted"
    assert status.loc[0, "job_id"] == "12345"
    assert status.loc[0, "script_path"] == str(script)
    assert status.loc[0, "returncode"] == 0
    assert status.loc[0, "command"] == f"sbatch --parsable {script}"
    assert status.loc[0, "stdout"] == "Submitted batch job 12345"
    assert status.loc[0, "stderr"] == ""


def test_slurm_submission_status_frame_reports_failed_submission(tmp_path: Path) -> None:
    """Submission results should display failed sbatch attempts without raw dataclass reprs."""

    submission = SlurmSubmission(
        script_path=tmp_path / "failed.slurm",
        command=("sbatch", str(tmp_path / "failed.slurm")),
        stdout="",
        stderr="invalid partition",
        returncode=1,
        job_id="",
    )

    status = submission.status_frame()

    assert status.loc[0, "status"] == "submission_failed"
    assert status.loc[0, "job_id"] == ""
    assert status.loc[0, "script_path"] == str(tmp_path / "failed.slurm")
    assert status.loc[0, "returncode"] == 1
    assert status.loc[0, "stderr"] == "invalid partition"


def test_write_inline_python_slurm_script_uses_shared_header(tmp_path: Path) -> None:
    """Notebook-style inline Python scripts should use shared SLURM settings."""

    script = tmp_path / "inline.slurm"
    settings = SlurmSettings(
        python_command="python",
        environment_setup=("conda activate spatial-vtk",),
        job_name="svtk-inline",
        log_dir=str(tmp_path / "logs"),
        working_directory="/project/spatial-vtk",
        memory="12G",
        cpus_per_task=3,
    )

    written = write_inline_python_slurm_script(
        script,
        """
        print("hello")
        """,
        settings,
    )

    text = written.read_text(encoding="utf-8")
    assert "#SBATCH --job-name=svtk-inline" in text
    assert "#SBATCH --mem=12G" in text
    assert "#SBATCH --cpus-per-task=3" in text
    assert "cd /project/spatial-vtk" in text
    assert "conda activate spatial-vtk" in text
    assert "python - <<'PYJOB'" in text
    assert 'print("hello")' in text


def test_submit_or_print_slurm_script_can_skip_submission(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Notebook drivers should be able to print a manual sbatch command."""

    script = tmp_path / "job.slurm"
    script.write_text("#!/bin/bash\n", encoding="utf-8")
    settings = SlurmSettings(python_command="python", submit_command="sbatch --parsable")

    result = submit_or_print_slurm_script(script, settings=settings, submit=False)

    captured = capsys.readouterr().out
    assert result is None
    assert f"script: {script}" in captured
    assert f"sbatch --parsable {script}" in captured
