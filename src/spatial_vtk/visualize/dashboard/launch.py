"""Launch helpers for Streamlit dashboards."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any, Iterable


@dataclass(frozen=True)
class DashboardLaunchResult:
    """Result returned by notebook dashboard launch orchestration helpers."""

    metrics_process: subprocess.Popen[Any] | None
    qc_process: subprocess.Popen[Any] | None
    rows: tuple[dict[str, Any], ...]

    def status_frame(self) -> Any:
        """Return a compact notebook-friendly dashboard launch table."""

        import pandas as pd

        return pd.DataFrame(list(self.rows))


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
    metrics_dataset_dir: str | Path | None = None,
    dashboard_summary_table_dir: str | Path | None = None,
    metrics_root: str | Path | None = None,
    summary_root: str | Path | None = None,
    config_path: str | Path | None = None,
    server_address: str = "127.0.0.1",
    server_port: int = 8501,
    auto_port: bool = False,
    show: bool = True,
    proxy_mode: bool = False,
    row_limit: int | str | None = None,
    summary_display_rows: int | str | None = None,
    download_rows: int | str | None = None,
    extra_args: list[str] | None = None,
    startup_timeout_s: float = 2.5,
) -> subprocess.Popen[Any]:
    """Launch the Streamlit Metrics Explorer.

    Parameters
    ----------
    metrics_dataset_dir, dashboard_summary_table_dir
        Metrics dashboard row dataset and dashboard summary-table directory.
        These names match the CLI flags and Streamlit query parameters.
    metrics_root, summary_root
        Backward-compatible aliases for ``metrics_dataset_dir`` and
        ``dashboard_summary_table_dir``.
    """

    resolved_metrics_dataset = _coalesce_dashboard_launch_path(
        metrics_dataset_dir,
        metrics_root,
        preferred_name="metrics_dataset_dir",
        legacy_name="metrics_root",
        artifact_label="metrics dashboard row dataset",
    )
    resolved_summary_tables = _coalesce_dashboard_launch_path(
        dashboard_summary_table_dir,
        summary_root,
        preferred_name="dashboard_summary_table_dir",
        legacy_name="summary_root",
        artifact_label="dashboard summary-table directory",
    )

    env = os.environ.copy()
    env["SVTK_METRICS_ROOT"] = str(Path(resolved_metrics_dataset).expanduser())
    env["SVTK_SUMMARY_ROOT"] = str(Path(resolved_summary_tables).expanduser())
    _set_optional_env(env, "SVTK_METRICS_DASHBOARD_ROW_LIMIT", row_limit)
    _set_optional_env(env, "SVTK_METRICS_DASHBOARD_SUMMARY_DISPLAY_ROWS", summary_display_rows)
    _set_optional_env(env, "SVTK_METRICS_DASHBOARD_DOWNLOAD_ROWS", download_rows)
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
        startup_timeout_s=startup_timeout_s,
    )


def launch_configured_metrics_dashboard(
    *,
    cfg: Any | None = None,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    server_address: str = "127.0.0.1",
    server_port: int = 8501,
    auto_port: bool = False,
    show: bool = True,
    proxy_mode: bool = False,
    row_limit: int | str | None = None,
    summary_display_rows: int | str | None = None,
    download_rows: int | str | None = None,
    extra_args: list[str] | None = None,
    startup_timeout_s: float = 2.5,
) -> subprocess.Popen[Any]:
    """Launch the Metrics Explorer from configured dashboard output paths.

    Parameters
    ----------
    cfg, config_path, run_scenario
        Configuration object or config file used to resolve the
        ``metrics_dashboard`` and ``dashboard_summaries`` output registry keys.
        When omitted, the active Spatial-VTK config is used.
    server_address, server_port, auto_port, show, proxy_mode, extra_args
        Passed through to :func:`launch_metrics_dashboard`.
    """

    from spatial_vtk.visualize.dashboard.contracts import dashboard_output_paths

    config = _resolve_dashboard_config(cfg=cfg, config_path=config_path, run_scenario=run_scenario)
    paths = dashboard_output_paths(cfg=config, include_summary_tables=False)
    return launch_metrics_dashboard(
        metrics_dataset_dir=paths["metrics_dashboard_root"],
        dashboard_summary_table_dir=paths["dashboard_summary_root"],
        config_path=config.config_path,
        server_address=server_address,
        server_port=server_port,
        auto_port=auto_port,
        show=show,
        proxy_mode=proxy_mode,
        row_limit=row_limit,
        summary_display_rows=summary_display_rows,
        download_rows=download_rows,
        extra_args=extra_args,
        startup_timeout_s=startup_timeout_s,
    )


def _coalesce_dashboard_launch_path(
    preferred: str | Path | None,
    legacy: str | Path | None,
    *,
    preferred_name: str,
    legacy_name: str,
    artifact_label: str,
) -> str | Path:
    """Return one dashboard launch path from a clear keyword or legacy alias."""

    if preferred is None and legacy is None:
        raise ValueError(f"{preferred_name} is required for the {artifact_label}.")
    if (
        preferred is not None
        and legacy is not None
        and str(Path(preferred).expanduser()) != str(Path(legacy).expanduser())
    ):
        raise ValueError(
            f"Pass either {preferred_name} or {legacy_name} for the {artifact_label}, "
            "not two different paths."
        )
    return preferred if preferred is not None else legacy


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
    startup_timeout_s: float = 2.5,
) -> subprocess.Popen[Any]:
    """Launch the Streamlit QC Explorer."""

    config = None
    if trace_summary is None or config_path is None:
        try:
            config = _resolve_dashboard_config(config_path=config_path)
        except Exception:
            config = None
    if trace_summary is None:
        if config is None:
            raise ValueError("trace_summary is required when no active Spatial-VTK config is available.")
        from spatial_vtk.config import resolve_output_path

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
        startup_timeout_s=startup_timeout_s,
    )


def launch_configured_qc_dashboard(
    *,
    cfg: Any | None = None,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    server_address: str = "127.0.0.1",
    server_port: int = 8502,
    auto_port: bool = False,
    show: bool = True,
    proxy_mode: bool = False,
    extra_args: list[str] | None = None,
    startup_timeout_s: float = 2.5,
) -> subprocess.Popen[Any]:
    """Launch the QC Explorer from the configured ``qc_trace_summary`` output."""

    config = _resolve_dashboard_config(cfg=cfg, config_path=config_path, run_scenario=run_scenario)
    from spatial_vtk.config import resolve_output_path

    return launch_qc_dashboard(
        trace_summary=resolve_output_path("qc_trace_summary", kind="table", cfg=config),
        config_path=config.config_path,
        server_address=server_address,
        server_port=server_port,
        auto_port=auto_port,
        show=show,
        proxy_mode=proxy_mode,
        extra_args=extra_args,
        startup_timeout_s=startup_timeout_s,
    )


def launch_configured_dashboards_from_notebook_settings(
    dashboard_launch: Any,
    *,
    dashboards: Iterable[str] = ("metrics", "qc"),
    show: bool = True,
    catch_errors: bool = True,
) -> DashboardLaunchResult:
    """Launch or report configured Metrics and QC dashboards for notebooks.

    Parameters
    ----------
    dashboard_launch
        Result from :func:`spatial_vtk.config.notebook_dashboard_launch_commands`.
        The object supplies launch flags, requested ports, terminal fallback
        commands, and config-backed keyword arguments for each dashboard.
    dashboards
        Dashboard names to include. Use ``("qc",)`` for QC-only tutorial cells
        and the default ``("metrics", "qc")`` for Step 7 dashboard launch
        cells.
    show
        Passed through to configured dashboard launch helpers.
    catch_errors
        When true, launch failures are returned as ``"error"`` rows in the
        status frame instead of raising immediately. This keeps tutorial
        notebooks readable when optional dashboard dependencies are not
        installed or a requested port is busy.

    Returns
    -------
    DashboardLaunchResult
        Process handles for dashboards that launched, plus a bounded status
        frame describing running dashboards, fallback terminal commands, or
        launch errors.
    """

    requested_dashboards = tuple(str(name).strip().lower() for name in dashboards)
    unknown = sorted({name for name in requested_dashboards if name not in {"metrics", "qc"}})
    if unknown:
        raise ValueError(f"Unknown dashboard name(s): {unknown}. Expected 'metrics' and/or 'qc'.")
    rows: list[dict[str, Any]] = []
    metrics_process = None
    qc_process = None
    if "metrics" in requested_dashboards:
        metrics_process = _launch_one_dashboard_from_notebook_settings(
            dashboard_name="metrics",
            launch_requested=bool(getattr(dashboard_launch, "launch_metrics_dashboard", False)),
            requested_port=int(getattr(dashboard_launch, "metrics_port", 8501)),
            terminal_command=str(getattr(dashboard_launch, "metrics_command", "")),
            launch_callable=launch_configured_metrics_dashboard,
            launch_kwargs=dashboard_launch.metrics_launch_kwargs(show=show),
            rows=rows,
            catch_errors=catch_errors,
        )
    if "qc" in requested_dashboards:
        qc_process = _launch_one_dashboard_from_notebook_settings(
            dashboard_name="qc",
            launch_requested=bool(getattr(dashboard_launch, "launch_qc_dashboard", False)),
            requested_port=int(getattr(dashboard_launch, "qc_port", 8502)),
            terminal_command=str(getattr(dashboard_launch, "qc_command", "")),
            launch_callable=launch_configured_qc_dashboard,
            launch_kwargs=dashboard_launch.qc_launch_kwargs(show=show),
            rows=rows,
            catch_errors=catch_errors,
        )
    return DashboardLaunchResult(
        metrics_process=metrics_process,
        qc_process=qc_process,
        rows=tuple(rows),
    )


def _launch_one_dashboard_from_notebook_settings(
    *,
    dashboard_name: str,
    launch_requested: bool,
    requested_port: int,
    terminal_command: str,
    launch_callable: Any,
    launch_kwargs: dict[str, Any],
    rows: list[dict[str, Any]],
    catch_errors: bool,
) -> subprocess.Popen[Any] | None:
    """Append one dashboard launch status row and return the process if any."""

    common = {
        "dashboard": dashboard_name,
        "launch_requested": launch_requested,
        "requested_port": requested_port,
        "terminal_command": terminal_command,
    }
    if not launch_requested:
        rows.append(
            {
                **common,
                "status": "command",
                "pid": "",
                "resolved_port": "",
                "url": "",
                "message": "Launch disabled; run the terminal command in a separate session when needed.",
            }
        )
        return None
    try:
        process = launch_callable(**launch_kwargs)
    except Exception as exc:
        if not catch_errors:
            raise
        rows.append(
            {
                **common,
                "status": "error",
                "pid": "",
                "resolved_port": "",
                "url": "",
                "message": f"Failed to launch {dashboard_name} dashboard: {exc}",
            }
        )
        return None
    resolved_port = int(getattr(process, "spatial_vtk_server_port", requested_port))
    rows.append(
        {
            **common,
            "status": "running",
            "pid": getattr(process, "pid", ""),
            "resolved_port": resolved_port,
            "url": f"http://127.0.0.1:{resolved_port}",
            "message": f"{dashboard_name.capitalize()} dashboard running.",
        }
    )
    return process


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
    startup_timeout_s: float = 2.5,
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
    _raise_if_streamlit_exited_early(process, server_port=resolved_port, startup_timeout_s=startup_timeout_s)
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
        with socket.create_connection((host, int(server_port)), timeout=0.2):
            return False
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, int(server_port)))
    except OSError:
        return False
    return True


def _raise_if_streamlit_exited_early(
    process: subprocess.Popen[Any],
    *,
    server_port: int,
    startup_timeout_s: float,
) -> None:
    """Raise if Streamlit reports a startup failure after process creation."""

    deadline = time.monotonic() + max(float(startup_timeout_s), 0.0)
    while True:
        if process.poll() is not None:
            raise RuntimeError(
                f"Streamlit dashboard exited during startup with status {process.returncode}. "
                f"Check the Streamlit output above, or try another port with --port {int(server_port) + 1} "
                "or --auto-port."
            )
        if time.monotonic() >= deadline:
            return
        time.sleep(0.1)


def _entrypoint(name: str) -> Path:
    """Return the path to one Streamlit entrypoint."""

    return Path(__file__).resolve().parent / name


def _require_streamlit() -> None:
    """Raise a clear error when Streamlit is not installed."""

    if importlib.util.find_spec("streamlit") is None:
        raise ImportError("Streamlit dashboards require the optional dashboard dependencies. Install spatial-vtk[dashboard] or use svtk_environment.yaml.")


def _set_optional_env(env: dict[str, str], name: str, value: int | str | None) -> None:
    """Set one dashboard runtime environment variable when a value is explicit."""

    if value is None:
        return
    text = str(value).strip()
    if not text:
        return
    env[name] = text


def _resolve_dashboard_config(
    *,
    cfg: Any | None = None,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
) -> Any:
    """Resolve a dashboard config from an object, config path, or active config."""

    from spatial_vtk.config import SpatialVTKConfig, active_config

    if cfg is not None:
        return cfg.with_run_scenario(run_scenario) if run_scenario and hasattr(cfg, "with_run_scenario") else cfg
    if config_path is not None:
        return SpatialVTKConfig.from_file(config_path, run_scenario=run_scenario)
    config = active_config()
    return config.with_run_scenario(run_scenario) if run_scenario and hasattr(config, "with_run_scenario") else config


__all__ = [
    "DashboardLaunchResult",
    "build_streamlit_command",
    "find_available_port",
    "launch_configured_dashboards_from_notebook_settings",
    "launch_configured_metrics_dashboard",
    "launch_configured_qc_dashboard",
    "launch_metrics_dashboard",
    "launch_qc_dashboard",
    "launch_streamlit_dashboard",
]
