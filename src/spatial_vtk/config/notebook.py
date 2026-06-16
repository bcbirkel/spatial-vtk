"""Notebook display helpers.

Purpose
-------
This module registers lightweight IPython helpers used by the public tutorial
notebooks. The timing helpers print only wall-clock run time and can be
toggled from the active Spatial-VTK configuration.

Usage examples
--------------
Register automatic timing for later notebook cells:
  ``from spatial_vtk.config.notebook import register_svtk_cell_timer``
  ``register_svtk_cell_timer()``
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator

from spatial_vtk.config.runtime import SpatialVTKConfig, active_config
from spatial_vtk.config.compute import (
    SlurmSubmission,
    slurm_settings_from_config,
    slurm_settings_with_overrides,
    submit_or_print_slurm_script,
    write_inline_python_slurm_script,
)


@dataclass(frozen=True)
class NotebookRunContext:
    """Resolved paths and flags for a workflow notebook.

    Parameters
    ----------
    repo_root
        Repository or project root used by the notebook.
    config_path
        Config file loaded for the run.
    cfg
        Activated Spatial-VTK config.
    outputs_root, tables_dir, figures_dir, dashboards_dir, slurm_dir, logs_dir
        Standard output directories resolved from the config.
    run_local, submit_slurm, overwrite
        Common notebook execution flags read from environment variables.
    preview_rows, qc_chunksize
        Common notebook row/chunk controls read from environment variables.
    """

    repo_root: Path
    config_path: Path
    cfg: SpatialVTKConfig
    outputs_root: Path
    tables_dir: Path
    figures_dir: Path
    dashboards_dir: Path
    slurm_dir: Path
    logs_dir: Path
    run_local: bool
    submit_slurm: bool
    overwrite: bool
    preview_rows: int
    qc_chunksize: int


def find_repo_root(start: str | Path | None = None) -> Path:
    """Find the nearest Spatial-VTK repository root.

    Parameters
    ----------
    start
        Directory to search from. When omitted, the current working directory
        is used.

    Returns
    -------
    pathlib.Path
        First parent containing ``pyproject.toml`` and ``src/spatial_vtk``.
        If none is found, the resolved start directory is returned.
    """

    current = Path(start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "src" / "spatial_vtk").exists():
            return candidate
    return current


def notebook_run_context(
    config_path: str | Path | None = None,
    *,
    start: str | Path | None = None,
    activate: bool = True,
    create_dirs: bool = True,
) -> NotebookRunContext:
    """Resolve the standard context for Spatial-VTK workflow notebooks.

    Parameters
    ----------
    config_path
        Explicit config path. When omitted, common project-relative locations
        and ``SVTK_CONFIG`` discovery are used.
    start
        Directory used to find the repository root.
    activate
        Whether to activate the loaded config.
    create_dirs
        Whether to create standard output directories.

    Returns
    -------
    NotebookRunContext
        Resolved config, output directories, and execution flags.
    """

    repo_root = find_repo_root(start)
    resolved_config = _resolve_notebook_config_path(repo_root, config_path)
    cfg = SpatialVTKConfig.from_file(resolved_config)
    if activate:
        cfg.activate()

    outputs_root = Path(cfg.path("outputs.root", create_parent=create_dirs) or (cfg.root_dir / "outputs"))
    tables_dir = Path(cfg.path("outputs.tables", create_parent=create_dirs) or (outputs_root / "tables"))
    figures_dir = Path(cfg.path("outputs.figures", create_parent=create_dirs) or (outputs_root / "figures"))
    dashboards_dir = Path(cfg.path("outputs.dashboards", create_parent=create_dirs) or (outputs_root / "dashboards"))
    slurm_dir = outputs_root / "slurm"
    logs_dir = outputs_root / "logs"
    if create_dirs:
        for directory in (outputs_root, tables_dir, figures_dir, dashboards_dir, slurm_dir, logs_dir):
            directory.mkdir(parents=True, exist_ok=True)

    return NotebookRunContext(
        repo_root=repo_root,
        config_path=resolved_config,
        cfg=cfg,
        outputs_root=outputs_root,
        tables_dir=tables_dir,
        figures_dir=figures_dir,
        dashboards_dir=dashboards_dir,
        slurm_dir=slurm_dir,
        logs_dir=logs_dir,
        run_local=_env_bool("SVTK_RUN_LOCAL", default=False),
        submit_slurm=_env_bool("SVTK_SUBMIT_SLURM", default=False),
        overwrite=_env_bool("SVTK_OVERWRITE", default=False),
        preview_rows=_env_int("SVTK_PREVIEW_ROWS", default=5),
        qc_chunksize=_env_int("SVTK_QC_CHUNKSIZE", default=1_000_000),
    )


def print_notebook_context(context: NotebookRunContext) -> None:
    """Print a compact run-context summary for a notebook setup cell."""

    print(f"repo_root: {context.repo_root}")
    print(f"config_path: {context.config_path}")
    print(f"outputs_root: {context.outputs_root}")
    print(f"tables_dir: {context.tables_dir}")
    print(f"figures_dir: {context.figures_dir}")
    print(
        "SUBMIT_SLURM="
        f"{context.submit_slurm} RUN_LOCAL={context.run_local} OVERWRITE={context.overwrite}"
    )


def write_notebook_python_slurm_script(
    context: NotebookRunContext,
    script_name: str,
    python_body: str,
    *,
    job_name: str,
    walltime: str = "24:00:00",
    memory: str = "32G",
    cpus: int = 1,
    section: str | None = "compute.slurm",
) -> Path:
    """Write an inline-Python SLURM script for a workflow notebook.

    The job inherits Python command and environment setup from the active config
    and only overrides resources supplied by the notebook cell.
    """

    settings = slurm_settings_with_overrides(
        context.cfg,
        section=section,
        job_name=job_name,
        walltime=walltime,
        memory=memory,
        cpus_per_task=cpus,
        working_directory=context.repo_root,
        log_dir=context.logs_dir,
    )
    return write_inline_python_slurm_script(
        context.slurm_dir / script_name,
        python_body,
        settings,
    )


def submit_notebook_slurm_script(
    context: NotebookRunContext,
    script_path: str | Path,
    *,
    section: str | None = "compute.slurm",
) -> SlurmSubmission | None:
    """Submit or print one notebook-generated SLURM script."""

    settings = slurm_settings_from_config(context.cfg, section=section)
    return submit_or_print_slurm_script(
        script_path,
        settings=settings,
        submit=context.submit_slurm,
    )


def notebook_timing_enabled(config: SpatialVTKConfig | None = None, *, default: bool = True) -> bool:
    """Return whether notebook cell timing should be printed.

    Parameters
    ----------
    config
        Optional config object. When omitted, the active config is used if one
        is available.
    default
        Value returned when no config or setting is available.

    Returns
    -------
    bool
        ``True`` when timing output should be displayed.
    """

    cfg = config
    if cfg is None:
        try:
            cfg = active_config()
        except Exception:
            return bool(default)
    value = cfg.section("notebooks.show_cell_timing", default)
    return _as_bool(value, default=default)


def format_run_time(seconds: float) -> str:
    """Format elapsed wall-clock seconds as a compact run-time label.

    Parameters
    ----------
    seconds
        Elapsed wall-clock seconds.

    Returns
    -------
    str
        Text such as ``"Run time: 19.2 ms"``.
    """

    seconds = max(float(seconds), 0.0)
    if seconds < 1.0:
        return f"Run time: {seconds * 1000.0:.1f} ms"
    if seconds < 60.0:
        return f"Run time: {seconds:.2f} s"
    minutes, remainder = divmod(seconds, 60.0)
    if minutes < 60.0:
        return f"Run time: {int(minutes)} min {remainder:.1f} s"
    hours, minutes = divmod(minutes, 60.0)
    return f"Run time: {int(hours)} hr {int(minutes)} min {remainder:.1f} s"


def print_run_time(start_time: float, *, config: SpatialVTKConfig | None = None, default: bool = True) -> None:
    """Print elapsed wall-clock time when notebook timing is enabled.

    Parameters
    ----------
    start_time
        Value returned by ``time.perf_counter()`` before work started.
    config
        Optional config object used to check ``notebooks.show_cell_timing``.
    default
        Fallback timing behavior when no config is available.

    Returns
    -------
    None
        Prints a compact run-time line when enabled.
    """

    if notebook_timing_enabled(config, default=default):
        print(format_run_time(perf_counter() - float(start_time)))


@contextmanager
def notebook_timer(*, config: SpatialVTKConfig | None = None, default: bool = True) -> Iterator[None]:
    """Context manager that prints compact notebook run time.

    Parameters
    ----------
    config
        Optional config object used to check ``notebooks.show_cell_timing``.
    default
        Fallback timing behavior when no config is available.

    Returns
    -------
    contextlib.AbstractContextManager
        Context manager for timing setup/bootstrap cells.
    """

    start_time = perf_counter()
    try:
        yield
    finally:
        print_run_time(start_time, config=config, default=default)


def register_svtk_time_magic() -> None:
    """Register the ``%%svtk_time`` IPython cell magic.

    Parameters
    ----------
    None
        The active IPython shell is discovered automatically.

    Returns
    -------
    None
        Registers the magic when IPython is available.
    """

    try:
        from IPython import get_ipython
    except Exception:
        return
    shell = get_ipython()
    if shell is None:
        return

    def svtk_time(line: str, cell: str) -> Any:
        """Run one cell and print compact wall-clock timing."""

        start_time = perf_counter()
        result = shell.run_cell(cell, store_history=False)
        if getattr(result, "error_before_exec", None) is not None or getattr(result, "error_in_exec", None) is not None:
            result.raise_error()
        print_run_time(start_time)
        return None

    shell.register_magic_function(svtk_time, magic_kind="cell", magic_name="svtk_time")


def register_svtk_cell_timer(*, config: SpatialVTKConfig | None = None, default: bool = True) -> None:
    """Register automatic compact timing for later IPython code cells.

    Parameters
    ----------
    config
        Optional config object used to check ``notebooks.show_cell_timing``.
        When omitted, the active config is checked at the end of each cell.
    default
        Fallback timing behavior when no config is available.

    Returns
    -------
    None
        Registers IPython pre/post cell hooks when IPython is available.
    """

    try:
        from IPython import get_ipython
    except Exception:
        return
    shell = get_ipython()
    if shell is None or not hasattr(shell, "events"):
        return

    existing = getattr(shell, "_spatial_vtk_cell_timer_callbacks", None)
    if existing is not None:
        for event_name, callback in existing:
            try:
                shell.events.unregister(event_name, callback)
            except Exception:
                pass

    state: dict[str, float | str] = {}

    def pre_run_cell(info: Any) -> None:
        """Store the start time for one IPython code cell."""

        raw_cell = str(getattr(info, "raw_cell", "") or "")
        if raw_cell.strip():
            state["raw_cell"] = raw_cell
            state["start_time"] = perf_counter()

    def post_run_cell(result: Any) -> None:
        """Print compact run time after a successful IPython code cell."""

        start_time = state.pop("start_time", None)
        state.pop("raw_cell", None)
        if start_time is None:
            return
        if getattr(result, "error_before_exec", None) is not None or getattr(result, "error_in_exec", None) is not None:
            return
        print_run_time(float(start_time), config=config, default=default)

    shell.events.register("pre_run_cell", pre_run_cell)
    shell.events.register("post_run_cell", post_run_cell)
    shell._spatial_vtk_cell_timer_callbacks = (
        ("pre_run_cell", pre_run_cell),
        ("post_run_cell", post_run_cell),
    )


def _as_bool(value: object, *, default: bool) -> bool:
    """Interpret common boolean config values."""

    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _resolve_notebook_config_path(repo_root: Path, config_path: str | Path | None) -> Path:
    """Resolve the config path used by workflow notebooks."""

    if config_path is not None:
        return Path(config_path).expanduser().resolve()
    env_path = os.environ.get("SVTK_CONFIG")
    if env_path:
        return Path(env_path).expanduser().resolve()
    candidates = [
        repo_root / "runs" / "spatial_vtk_config.yaml",
        Path.cwd() / "spatial_vtk_config.yaml",
        Path.cwd() / "runs" / "spatial_vtk_config.yaml",
    ]
    return next((path.resolve() for path in candidates if path.exists()), candidates[0].resolve())


def _env_bool(name: str, *, default: bool) -> bool:
    """Read one boolean environment variable."""

    value = os.environ.get(name)
    if value is None:
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, *, default: int) -> int:
    """Read one integer environment variable."""

    value = os.environ.get(name)
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


__all__ = [
    "NotebookRunContext",
    "find_repo_root",
    "format_run_time",
    "notebook_timer",
    "notebook_timing_enabled",
    "notebook_run_context",
    "print_run_time",
    "print_notebook_context",
    "register_svtk_cell_timer",
    "register_svtk_time_magic",
    "submit_notebook_slurm_script",
    "write_notebook_python_slurm_script",
]
