"""Launch helpers for Streamlit dashboards."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from spatial_vtk.config import active_config, resolve_output_path


def build_streamlit_command(entrypoint: str | Path, *, server_address: str = "127.0.0.1", server_port: int = 8501, show: bool = True, extra_args: list[str] | None = None) -> list[str]:
    """Build the command used to run one Streamlit dashboard."""

    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(entrypoint),
        "--server.address",
        str(server_address),
        "--server.port",
        str(int(server_port)),
        "--server.headless",
        "false" if show else "true",
        *(extra_args or []),
    ]


def launch_metrics_dashboard(
    *,
    metrics_root: str | Path,
    summary_root: str | Path,
    server_address: str = "127.0.0.1",
    server_port: int = 8501,
    show: bool = True,
    extra_args: list[str] | None = None,
) -> subprocess.Popen[Any]:
    """Launch the Streamlit Metrics Explorer."""

    env = os.environ.copy()
    env["SVTK_METRICS_ROOT"] = str(Path(metrics_root).expanduser())
    env["SVTK_SUMMARY_ROOT"] = str(Path(summary_root).expanduser())
    return launch_streamlit_dashboard(_entrypoint("streamlit_metrics.py"), server_address=server_address, server_port=server_port, show=show, extra_args=extra_args, env=env)


def launch_qc_dashboard(
    *,
    trace_summary: str | Path | None = None,
    config_path: str | Path | None = None,
    server_address: str = "127.0.0.1",
    server_port: int = 8502,
    show: bool = True,
    extra_args: list[str] | None = None,
) -> subprocess.Popen[Any]:
    """Launch the Streamlit QC Explorer."""

    config = active_config()
    resolved_trace_summary = trace_summary or resolve_output_path("qc_inventory", kind="table", cfg=config)
    resolved_config_path = config_path or config.config_path
    env = os.environ.copy()
    env["SVTK_TRACE_SUMMARY"] = str(Path(resolved_trace_summary).expanduser())
    if resolved_config_path is not None:
        env["SVTK_CONFIG_FILE"] = str(Path(resolved_config_path).expanduser())
    return launch_streamlit_dashboard(_entrypoint("streamlit_qc.py"), server_address=server_address, server_port=server_port, show=show, extra_args=extra_args, env=env)


def launch_streamlit_dashboard(
    entrypoint: str | Path,
    *,
    server_address: str = "127.0.0.1",
    server_port: int = 8501,
    show: bool = True,
    extra_args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.Popen[Any]:
    """Start one Streamlit dashboard process."""

    _require_streamlit()
    command = build_streamlit_command(entrypoint, server_address=server_address, server_port=server_port, show=show, extra_args=extra_args)
    return subprocess.Popen(command, env=env or os.environ.copy())


def _entrypoint(name: str) -> Path:
    """Return the path to one Streamlit entrypoint."""

    return Path(__file__).resolve().parent / name


def _require_streamlit() -> None:
    """Raise a clear error when Streamlit is not installed."""

    if importlib.util.find_spec("streamlit") is None:
        raise ImportError("Streamlit dashboards require the optional dashboard dependencies. Install spatial-vtk[dashboard] or use svtk_environment.yaml.")


__all__ = ["build_streamlit_command", "launch_metrics_dashboard", "launch_qc_dashboard", "launch_streamlit_dashboard"]
