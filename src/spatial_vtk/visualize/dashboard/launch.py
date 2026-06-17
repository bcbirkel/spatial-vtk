"""Launch helpers for Streamlit dashboards."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any

from spatial_vtk.config import active_config, resolve_output_path


def build_streamlit_command(
    entrypoint: str | Path,
    *,
    server_address: str = "127.0.0.1",
    server_port: int = 8501,
    show: bool = True,
    proxy_mode: bool = False,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build the command used to run one Streamlit dashboard."""

    proxy_args = (
        [
            "--server.enableCORS=false",
            "--server.enableXsrfProtection=false",
            "--browser.gatherUsageStats=false",
        ]
        if proxy_mode
        else []
    )
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
        *proxy_args,
        *(extra_args or []),
    ]


def launch_metrics_dashboard(
    *,
    metrics_root: str | Path,
    summary_root: str | Path,
    config_path: str | Path | None = None,
    server_address: str = "127.0.0.1",
    server_port: int = 8501,
    auto_port: bool = False,
    show: bool = True,
    proxy_mode: bool = False,
    extra_args: list[str] | None = None,
) -> subprocess.Popen[Any]:
    """Launch the Streamlit Metrics Explorer."""

    env = os.environ.copy()
    env["SVTK_METRICS_ROOT"] = str(Path(metrics_root).expanduser())
    env["SVTK_SUMMARY_ROOT"] = str(Path(summary_root).expanduser())
    if config_path is not None:
        env["SVTK_CONFIG_FILE"] = str(Path(config_path).expanduser())
    return launch_streamlit_dashboard(
        _entrypoint("streamlit_metrics.py"),
        server_address=server_address,
        server_port=server_port,
        auto_port=auto_port,
        show=show,
        proxy_mode=proxy_mode,
        extra_args=extra_args,
        env=env,
    )


def launch_qc_dashboard(
    *,
    trace_summary: str | Path | None = None,
    config_path: str | Path | None = None,
    server_address: str = "127.0.0.1",
    server_port: int = 8502,
    auto_port: bool = False,
    show: bool = True,
    proxy_mode: bool = False,
    extra_args: list[str] | None = None,
) -> subprocess.Popen[Any]:
    """Launch the Streamlit QC Explorer."""

    config = None
    if trace_summary is None or config_path is None:
        try:
            config = active_config()
        except Exception:
            config = None
    if trace_summary is None:
        if config is None:
            raise ValueError("trace_summary is required when no active Spatial-VTK config is available.")
        resolved_trace_summary = resolve_output_path("qc_trace_summary", kind="table", cfg=config)
    else:
        resolved_trace_summary = trace_summary
    resolved_config_path = config_path or (config.config_path if config is not None else None)
    env = os.environ.copy()
    env["SVTK_TRACE_SUMMARY"] = str(Path(resolved_trace_summary).expanduser())
    if resolved_config_path is not None:
        env["SVTK_CONFIG_FILE"] = str(Path(resolved_config_path).expanduser())
    return launch_streamlit_dashboard(
        _entrypoint("streamlit_qc.py"),
        server_address=server_address,
        server_port=server_port,
        auto_port=auto_port,
        show=show,
        proxy_mode=proxy_mode,
        extra_args=extra_args,
        env=env,
    )


def launch_streamlit_dashboard(
    entrypoint: str | Path,
    *,
    server_address: str = "127.0.0.1",
    server_port: int = 8501,
    auto_port: bool = False,
    show: bool = True,
    proxy_mode: bool = False,
    extra_args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.Popen[Any]:
    """Start one Streamlit dashboard process."""

    _require_streamlit()
    resolved_port = find_available_port(server_address=server_address, start_port=server_port) if auto_port else int(server_port)
    _raise_if_port_in_use(server_address, resolved_port)
    command = build_streamlit_command(
        entrypoint,
        server_address=server_address,
        server_port=resolved_port,
        show=show,
        proxy_mode=proxy_mode,
        extra_args=extra_args,
    )
    process = subprocess.Popen(command, env=env or os.environ.copy())
    setattr(process, "spatial_vtk_server_port", resolved_port)
    time.sleep(0.75)
    if process.poll() is not None:
        raise RuntimeError(
            f"Streamlit dashboard exited immediately with status {process.returncode}. "
            f"Check the Streamlit output above, or try another port with --port {resolved_port + 1}."
        )
    return process


def find_available_port(*, server_address: str = "127.0.0.1", start_port: int = 8501, max_tries: int = 100) -> int:
    """Return the first available dashboard port at or above ``start_port``."""

    port = int(start_port)
    for candidate in range(port, port + int(max_tries)):
        if _port_is_available(server_address, candidate):
            return candidate
    raise RuntimeError(
        f"No available dashboard port found on {server_address} from {port} to {port + int(max_tries) - 1}."
    )


def _raise_if_port_in_use(server_address: str, server_port: int) -> None:
    """Raise a clear error when the requested dashboard port is occupied."""

    if _port_is_available(server_address, server_port):
        return
    raise RuntimeError(
        f"Port {server_port} is already in use on {server_address}. "
        "Stop the existing Streamlit dashboard, launch this one with a different --port, "
        "or pass --auto-port."
    )


def _port_is_available(server_address: str, server_port: int) -> bool:
    """Return whether a server can bind to one dashboard port."""

    host = "127.0.0.1" if str(server_address) in {"", "::"} else str(server_address)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, int(server_port)))
    except OSError:
        return False
    return True


def _entrypoint(name: str) -> Path:
    """Return the path to one Streamlit entrypoint."""

    return Path(__file__).resolve().parent / name


def _require_streamlit() -> None:
    """Raise a clear error when Streamlit is not installed."""

    if importlib.util.find_spec("streamlit") is None:
        raise ImportError("Streamlit dashboards require the optional dashboard dependencies. Install spatial-vtk[dashboard] or use svtk_environment.yaml.")


__all__ = [
    "build_streamlit_command",
    "find_available_port",
    "launch_metrics_dashboard",
    "launch_qc_dashboard",
    "launch_streamlit_dashboard",
]
