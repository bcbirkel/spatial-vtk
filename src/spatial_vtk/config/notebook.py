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
from time import perf_counter
from typing import Any, Iterator

from spatial_vtk.config.runtime import SpatialVTKConfig, active_config


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


__all__ = [
    "format_run_time",
    "notebook_timer",
    "notebook_timing_enabled",
    "print_run_time",
    "register_svtk_cell_timer",
    "register_svtk_time_magic",
]
