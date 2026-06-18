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
from dataclasses import dataclass, field
import importlib
import json
import os
from pathlib import Path
import shlex
from time import perf_counter
from typing import Any, Callable, Iterator
import warnings

from spatial_vtk.config.runtime import SpatialVTKConfig, active_config, get_saved_config_path
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
    run_scenario
        Resolved run scenario applied to the config, or ``None`` when no
        scenario overlay is active.
    outputs_root, tables_dir, figures_dir, dashboards_dir, slurm_dir, logs_dir
        Standard output directories resolved from the config.
    run_local, submit_slurm, overwrite
        Common notebook execution flags read from environment variables.
    preview_rows, qc_chunksize, metric_batch_count
        Common notebook row/chunk controls read from environment variables.
    preprocess_continue_on_error
        Whether preprocessing should allow a partial event-station table when
        configured input waveform files are missing.
    """

    repo_root: Path
    config_path: Path
    cfg: SpatialVTKConfig
    run_scenario: str | None
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
    metric_batch_count: int
    preprocess_continue_on_error: bool


@dataclass(frozen=True)
class NotebookFigureSidecarSettings:
    """Environment-backed figure sidecar controls for notebooks.

    Parameters
    ----------
    enabled
        Whether figures should write row-provenance sidecars.
    rows
        Maximum sidecar rows to write. ``None`` means write all rows.
    directory
        Optional sidecar directory. Plotting functions default to a
        ``sidecars`` folder next to the figure when omitted.
    """

    enabled: bool = False
    rows: int | None = None
    directory: Path | None = None

    def kwargs(self, *, plural: bool = False) -> dict[str, object]:
        """Return keyword arguments accepted by Spatial-VTK plotting helpers.

        Parameters
        ----------
        plural
            Return ``write_sidecars`` instead of ``write_sidecar`` for helper
            contexts that manage several figure calls.
        """

        write_key = "write_sidecars" if plural else "write_sidecar"
        return {
            write_key: self.enabled,
            "sidecar_rows": self.rows,
            "sidecar_dir": self.directory,
        }

    def status_frame(self) -> Any:
        """Return a compact status table for sidecars written by these settings.

        The helper reads only the small JSON metadata files, not the plotted-row
        CSV sidecars. It is intended for notebook review cells after a figure
        block has run.
        """

        from spatial_vtk.visualize.figure_sidecars import figure_sidecar_status_frame

        return figure_sidecar_status_frame(self.directory)


@dataclass(frozen=True)
class NotebookFigureSettings:
    """Environment-backed figure controls for workflow notebooks.

    The settings object keeps notebook cells from repeating ``os.environ``
    parsing for common figure switches. Family-specific variables such as
    ``SVTK_METRIC_FIGURE_PASSBAND`` are checked before generic variables such
    as ``SVTK_FIGURE_PASSBAND``.
    """

    figure_kind: str | None = None
    make_figures: bool = False
    add_basemap: bool = False
    showfig: bool = False
    metric: str | None = None
    passband: str | None = None
    component: str | None = None
    components: list[str] | None = None
    model: str | None = None
    value_col: str = "log2_residual"
    sample_rows: int = 200_000
    robust_axis_percentile: float = 95.0
    station_aggregation: str = "mean"
    compare_to: str | None = None
    comparison_table: bool = False
    score_columns: list[str] | None = None
    pca_mode: str = "PC1"
    sidecars: NotebookFigureSidecarSettings = field(default_factory=NotebookFigureSidecarSettings)

    def context_kwargs(self, *, include_station_aggregation: bool = False) -> dict[str, object]:
        """Return keyword arguments accepted by large-run figure contexts."""

        kwargs: dict[str, object] = {
            "make_figures": self.make_figures,
            "sample_rows": self.sample_rows,
            "default_passband": self.passband,
            "default_components": self.components,
            "default_showfig": self.showfig,
            "default_model": self.model,
            "add_basemap": self.add_basemap,
            "robust_axis_percentile": self.robust_axis_percentile,
            **self.sidecars.kwargs(plural=True),
        }
        if include_station_aggregation:
            kwargs["station_aggregation"] = self.station_aggregation
        return kwargs

    def plot_kwargs(self, *, include_basemap: bool = False, plural_sidecars: bool = False) -> dict[str, object]:
        """Return keyword arguments accepted by individual plotting helpers."""

        kwargs: dict[str, object] = {
            "showfig": self.showfig,
            **self.sidecars.kwargs(plural=plural_sidecars),
        }
        if include_basemap:
            kwargs["add_basemap"] = self.add_basemap
        return kwargs

    def status_frame(self) -> Any:
        """Return a compact sidecar status table for this figure family."""

        return self.sidecars.status_frame()


@dataclass(frozen=True)
class NotebookDashboardCommands:
    """Config-backed dashboard launch plan for workflow notebooks.

    Parameters
    ----------
    metrics_command, qc_command
        Shell-safe fallback commands for launching the metrics and QC
        dashboards from a terminal.
    metrics_port, qc_port
        Requested ports before any ``auto_port`` fallback.
    launch_metrics_dashboard, launch_qc_dashboard
        Whether notebooks should launch dashboards from the kernel. When false,
        notebooks can display or print the terminal command instead.
    auto_port
        Whether dashboard launch helpers may move to the next available port.
    proxy_mode
        Whether launch helpers use reverse-proxy settings for notebook
        environments.
    config_path
        Resolved config path passed to package dashboard launch helpers.
    run_scenario
        Optional run scenario passed to dashboard launch helpers.
    """

    metrics_command: str
    qc_command: str
    metrics_port: int
    qc_port: int
    launch_metrics_dashboard: bool
    launch_qc_dashboard: bool
    auto_port: bool
    proxy_mode: bool
    config_path: Path
    run_scenario: str | None = None

    def metrics_launch_kwargs(self, *, show: bool = True) -> dict[str, object]:
        """Return keyword arguments for ``launch_configured_metrics_dashboard``."""

        kwargs: dict[str, object] = {
            "config_path": self.config_path,
            "server_port": self.metrics_port,
            "auto_port": self.auto_port,
            "proxy_mode": self.proxy_mode,
            "show": bool(show),
        }
        if self.run_scenario is not None:
            kwargs["run_scenario"] = self.run_scenario
        return kwargs

    def qc_launch_kwargs(self, *, show: bool = True) -> dict[str, object]:
        """Return keyword arguments for ``launch_configured_qc_dashboard``."""

        kwargs: dict[str, object] = {
            "config_path": self.config_path,
            "server_port": self.qc_port,
            "auto_port": self.auto_port,
            "proxy_mode": self.proxy_mode,
            "show": bool(show),
        }
        if self.run_scenario is not None:
            kwargs["run_scenario"] = self.run_scenario
        return kwargs

    def status_frame(self) -> Any:
        """Return a display-ready dashboard launch plan.

        The frame shows both the Python-launch settings and the terminal command
        fallback, plus the configured dashboard paths that each dashboard will
        read. It is intended for notebooks, where users need to verify launch
        inputs without resolving paths manually.
        """

        import pandas as pd

        from spatial_vtk.visualize.dashboard.contracts import dashboard_output_paths

        cfg = SpatialVTKConfig.from_file(self.config_path, run_scenario=self.run_scenario)
        paths = dashboard_output_paths(cfg=cfg, create_parent=False, include_summary_tables=False)
        common = {
            "config_path": str(self.config_path),
            "run_scenario": self.run_scenario or "",
            "auto_port": self.auto_port,
            "proxy_mode": self.proxy_mode,
        }
        rows = [
            {
                "dashboard": "metrics",
                "requested_port": self.metrics_port,
                "launch_requested": self.launch_metrics_dashboard,
                "metrics_dataset_dir": str(paths["metrics_dashboard_root"]),
                "dashboard_summary_table_dir": str(paths["dashboard_summary_root"]),
                "trace_summary_table": "",
                "terminal_command": self.metrics_command,
                **common,
            },
            {
                "dashboard": "qc",
                "requested_port": self.qc_port,
                "launch_requested": self.launch_qc_dashboard,
                "metrics_dataset_dir": "",
                "dashboard_summary_table_dir": "",
                "trace_summary_table": str(paths["qc_trace_summary_path"]),
                "terminal_command": self.qc_command,
                **common,
            },
        ]
        return pd.DataFrame(rows)


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


def prepare_notebook_geospatial_environment(
    *,
    clear_proj_env: bool | None = None,
) -> dict[str, str]:
    """Clear inherited PROJ overrides that can break tutorial geospatial plots.

    Some shell environments export ``PROJ_LIB`` or ``PROJ_DATA`` for a separate
    GIS installation. Rasterio, pyproj, and contextily may then read an
    incompatible ``proj.db`` before they can use the package environment's
    database. Tutorial notebooks call this during bootstrap so a fresh checkout
    can run without relying on the user's shell-specific GIS settings.

    Parameters
    ----------
    clear_proj_env
        Whether to remove ``PROJ_LIB`` and ``PROJ_DATA`` from ``os.environ``.
        When omitted, the default is ``True`` unless
        ``SVTK_KEEP_PROJ_ENV=1`` is set.

    Returns
    -------
    dict
        Mapping of environment variables that were removed to their previous
        values. The return value is intended for debugging; notebooks do not
        print it by default.
    """

    if clear_proj_env is None:
        clear_proj_env = not _env_bool("SVTK_KEEP_PROJ_ENV", default=False)
    if not clear_proj_env:
        return {}

    removed: dict[str, str] = {}
    for name in ("PROJ_LIB", "PROJ_DATA"):
        value = os.environ.pop(name, None)
        if value:
            removed[name] = value
    return removed


def notebook_run_context(
    config_path: str | Path | None = None,
    *,
    run_scenario: str | None = None,
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
    run_scenario
        Optional ``run_scenarios`` overlay to apply before activating the
        config. When omitted, ``SVTK_RUN_SCENARIO`` is honored if set.
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
    scenario = run_scenario if run_scenario is not None else os.environ.get("SVTK_RUN_SCENARIO")
    cfg = SpatialVTKConfig.from_file(resolved_config, run_scenario=scenario)
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
        run_scenario=scenario,
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
        metric_batch_count=_env_int("SVTK_METRIC_BATCH_COUNT", default=100),
        preprocess_continue_on_error=_env_bool("SVTK_PREPROCESS_CONTINUE_ON_ERROR", default=True),
    )


def print_notebook_context(context: NotebookRunContext) -> None:
    """Print a compact run-context summary for a notebook setup cell."""

    print(f"repo_root: {context.repo_root}")
    print(f"config_path: {context.config_path}")
    print(f"run_scenario: {context.run_scenario or ''}")
    print(f"outputs_root: {context.outputs_root}")
    print(f"tables_dir: {context.tables_dir}")
    print(f"figures_dir: {context.figures_dir}")
    print(
        "SUBMIT_SLURM="
        f"{context.submit_slurm} RUN_LOCAL={context.run_local} OVERWRITE={context.overwrite}"
    )
    print(
        "PREVIEW_ROWS="
        f"{context.preview_rows} QC_CHUNKSIZE={context.qc_chunksize} "
        f"METRIC_BATCH_COUNT={context.metric_batch_count}"
    )
    print(f"PREPROCESS_CONTINUE_ON_ERROR={context.preprocess_continue_on_error}")


def display_output_table_previews(
    keys: Iterable[str | tuple[str, str]] | dict[str, str],
    *,
    cfg: SpatialVTKConfig | None = None,
    nrows: int = 5,
    display_fn: Callable[[Any], Any] | None = None,
) -> dict[str, Path]:
    """Print paths and display bounded previews for configured output tables.

    Parameters
    ----------
    keys
        Output table keys, ``(label, key)`` pairs, or a ``label -> key``
        mapping. Labels are printed before each preview; keys are resolved
        through the configured output registry.
    cfg
        Optional Spatial-VTK config. When omitted, the active config is used by
        the underlying output resolver.
    nrows
        Number of rows to preview from each existing table.
    display_fn
        Optional display function. When omitted, IPython's ``display`` is used
        if available, otherwise dataframes are printed as plain text.

    Returns
    -------
    dict
        Mapping from display labels to resolved output paths.
    """

    from spatial_vtk.config.outputs import resolve_output_path
    from spatial_vtk.io.tables import preview_output_table

    display = _notebook_display(display_fn)
    resolved: dict[str, Path] = {}
    for label, key in _preview_key_items(keys):
        path = resolve_output_path(key, kind="table", cfg=cfg)
        resolved[label] = path
        print(f"\n{label}: {path}")
        if not path.exists():
            print(f"{label} is not ready yet.")
            continue
        preview = preview_output_table(key, cfg=cfg, nrows=nrows)
        if display is not None:
            display(preview)
        elif hasattr(preview, "to_string"):
            print(preview.to_string(index=False))
        else:
            print(preview)
    return resolved


def _preview_key_items(keys: Iterable[str | tuple[str, str]] | dict[str, str]) -> list[tuple[str, str]]:
    """Return ``(label, output_key)`` pairs for preview requests."""

    items = keys.items() if isinstance(keys, dict) else keys
    normalized: list[tuple[str, str]] = []
    for item in items:
        if isinstance(item, str):
            normalized.append((item, item))
        else:
            label, key = item
            normalized.append((str(label), str(key)))
    return normalized


def _notebook_display(display_fn: Callable[[Any], Any] | None = None) -> Callable[[Any], Any] | None:
    """Return a notebook display function when available."""

    if display_fn is not None:
        return display_fn
    try:
        from IPython.display import display as ipython_display

        return ipython_display
    except Exception:
        return None


def notebook_figure_sidecar_settings(
    figure_kind: str | None = None,
    *,
    figure_dir: str | Path | None = None,
    sidecar_dir: str | Path | None = None,
    default_enabled: bool = False,
    default_rows: int | None = None,
) -> NotebookFigureSidecarSettings:
    """Return standard notebook figure sidecar settings from the environment.

    Parameters
    ----------
    figure_kind
        Optional figure family token such as ``"metric"``, ``"spatial"``,
        ``"context"``, ``"qc"``, or ``"waveform"``. Family-specific
        variables such as ``SVTK_METRIC_FIGURE_SIDECARS`` and
        ``SVTK_METRIC_FIGURE_SIDECAR_ROWS`` are checked before generic
        ``SVTK_FIGURE_SIDECARS`` and ``SVTK_FIGURE_SIDECAR_ROWS``.
    figure_dir
        Figure output directory. When provided and ``sidecar_dir`` is omitted,
        the returned directory is ``figure_dir / "sidecars"``.
    sidecar_dir
        Explicit sidecar directory override.
    default_enabled
        Fallback enabled value when no environment variable is set.
    default_rows
        Fallback row limit. ``None`` writes all rows.

    Returns
    -------
    NotebookFigureSidecarSettings
        Parsed settings suitable for ``plot(..., **settings.kwargs())``.
    """

    prefix = _figure_env_prefix(figure_kind)
    enabled_names = []
    row_names = []
    if prefix:
        enabled_names.append(f"SVTK_{prefix}_FIGURE_SIDECARS")
        row_names.append(f"SVTK_{prefix}_FIGURE_SIDECAR_ROWS")
    enabled_names.extend(("SVTK_FIGURE_SIDECARS", "SVTK_WRITE_FIGURE_SIDECARS", "SVTK_WRITE_SIDECARS"))
    row_names.append("SVTK_FIGURE_SIDECAR_ROWS")

    enabled = _env_bool_first(enabled_names, default=default_enabled)
    rows = _env_optional_int_first(row_names, default=default_rows)
    directory = Path(sidecar_dir).expanduser() if sidecar_dir is not None else None
    if directory is None and figure_dir is not None:
        directory = Path(figure_dir).expanduser() / "sidecars"
    return NotebookFigureSidecarSettings(enabled=enabled, rows=rows, directory=directory)


def notebook_figure_settings(
    figure_kind: str | None = None,
    *,
    figure_dir: str | Path | None = None,
    sidecar_dir: str | Path | None = None,
    default_make_figures: bool = False,
    default_add_basemap: bool = False,
    default_showfig: bool = False,
    default_metric: str | None = None,
    default_passband: str | None = None,
    default_component: str | None = None,
    default_model: str | None = None,
    default_value_col: str = "log2_residual",
    default_sample_rows: int = 200_000,
    default_robust_axis_percentile: float = 95.0,
    default_station_aggregation: str = "mean",
    default_score_columns: list[str] | tuple[str, ...] | None = None,
    default_pca_mode: str = "PC1",
    default_sidecar_rows: int | None = None,
) -> NotebookFigureSettings:
    """Return standard notebook figure settings from environment variables.

    Parameters
    ----------
    figure_kind
        Optional figure family token such as ``"metric"``, ``"spatial"``,
        ``"context"``, ``"qc"``, ``"region"``, or ``"waveform"``.
        Family-specific variables are checked before generic variables. For
        example, ``figure_kind="metric"`` checks
        ``SVTK_MAKE_METRIC_FIGURES`` before ``SVTK_MAKE_FIGURES`` and
        ``SVTK_METRIC_FIGURE_PASSBAND`` before ``SVTK_FIGURE_PASSBAND``.
    figure_dir, sidecar_dir
        Figure and sidecar directories passed through to
        :func:`notebook_figure_sidecar_settings`.
    default_make_figures, default_add_basemap, default_showfig
        Fallback booleans when no corresponding environment variable is set.
    default_metric, default_passband, default_component, default_model,
    default_value_col
        Fallback single-figure filters and value column.
    default_sample_rows, default_robust_axis_percentile
        Fallback dense-plot controls.
    default_station_aggregation
        Fallback station aggregation method for station-summary figures.
    default_score_columns
        Fallback score columns for optional GOF/score trend diagnostics.
    default_pca_mode
        Fallback PCA mode name for spatial PCA summary figures.
    default_sidecar_rows
        Fallback sidecar row count.

    Returns
    -------
    NotebookFigureSettings
        Parsed settings suitable for large-run figure contexts and individual
        plotting helpers.
    """

    prefix = _figure_env_prefix(figure_kind)

    make_names: list[str] = []
    if prefix:
        make_names.append(f"SVTK_MAKE_{prefix}_FIGURES")
    make_names.append("SVTK_MAKE_FIGURES")

    passband_names = _figure_setting_names(prefix, "PASSBAND")
    metric_names = _figure_setting_names(prefix, "METRIC")
    component_names = _figure_setting_names(prefix, "COMPONENTS")
    component_names.extend(_figure_setting_names(prefix, "COMPONENT"))
    model_names = _figure_setting_names(prefix, "MODEL")
    value_col_names = _figure_setting_names(prefix, "VALUE_COL")
    showfig_names = _figure_setting_names(prefix, "SHOWFIG")
    sample_row_names = _figure_setting_names(prefix, "SAMPLE_ROWS")
    robust_names = _figure_setting_names(prefix, "ROBUST_PERCENTILE")
    compare_to_names = _figure_setting_names(prefix, "COMPARE_TO")
    comparison_table_names = _figure_setting_names(prefix, "COMPARISON_TABLE")
    score_column_names = _figure_setting_names(prefix, "SCORE_COLUMNS")
    pca_mode_names = _figure_setting_names(prefix, "PCA_MODE")

    aggregation_names = []
    if prefix:
        aggregation_names.append(f"SVTK_{prefix}_STATION_AGGREGATION")
    aggregation_names.append("SVTK_STATION_AGGREGATION")
    if prefix == "SCORE_TREND":
        make_names = ["SVTK_MAKE_SCORE_TRENDS", "SVTK_MAKE_SCORE_TREND_FIGURES"]
        score_column_names.insert(0, "SVTK_SCORE_TREND_COLUMNS")
    if prefix == "REGION":
        metric_names.insert(0, "SVTK_REGION_BOX_METRIC")
        passband_names.insert(0, "SVTK_REGION_BOX_PASSBAND")
        component_names.insert(0, "SVTK_REGION_BOX_COMPONENT")
        model_names.insert(0, "SVTK_REGION_BOX_MODEL")
        value_col_names.insert(0, "SVTK_REGION_VALUE_COL")
        compare_to_names.insert(0, "SVTK_REGION_COMPARE_TO")
        sample_row_names.insert(0, "SVTK_REGION_FIGURE_ROWS")
    if prefix == "SPATIAL":
        pca_mode_names.insert(0, "SVTK_PCA_MODE")

    component = _env_text_first(component_names, default=default_component)
    components = _env_list_first(component_names)
    if components is None and component:
        components = [component]
    default_scores = list(default_score_columns) if default_score_columns is not None else None

    return NotebookFigureSettings(
        figure_kind=figure_kind,
        make_figures=_env_bool_first(make_names, default=default_make_figures),
        add_basemap=_env_bool("SVTK_ADD_BASEMAP", default=default_add_basemap),
        showfig=_env_bool_first(showfig_names, default=default_showfig),
        metric=_env_text_first(metric_names, default=default_metric),
        passband=_env_text_first(passband_names, default=default_passband),
        component=component,
        components=components,
        model=_env_text_first(model_names, default=default_model),
        value_col=_env_text_first(value_col_names, default=default_value_col) or default_value_col,
        sample_rows=_env_int_first(sample_row_names, default=default_sample_rows),
        robust_axis_percentile=_env_float_first(robust_names, default=default_robust_axis_percentile),
        station_aggregation=_env_text_first(aggregation_names, default=default_station_aggregation)
        or default_station_aggregation,
        compare_to=_env_text_first(compare_to_names),
        comparison_table=_env_bool_first(comparison_table_names, default=False),
        score_columns=_env_list_first(score_column_names) or default_scores,
        pca_mode=_env_text_first(pca_mode_names, default=default_pca_mode) or default_pca_mode,
        sidecars=notebook_figure_sidecar_settings(
            figure_kind,
            figure_dir=figure_dir,
            sidecar_dir=sidecar_dir,
            default_rows=default_sidecar_rows,
        ),
    )


def notebook_dashboard_launch_commands(
    config_path: str | Path | None = None,
    *,
    metrics_port: int | None = None,
    qc_port: int | None = None,
    launch_metrics_dashboard: bool | None = None,
    launch_qc_dashboard: bool | None = None,
    auto_port: bool | None = None,
    proxy_mode: bool | None = None,
    run_scenario: str | None = None,
) -> NotebookDashboardCommands:
    """Return config-backed dashboard launch settings for notebooks.

    Parameters
    ----------
    config_path
        Config file passed to dashboard launch helpers. When omitted, the
        active config path or ``SVTK_CONFIG`` is used when available.
    metrics_port, qc_port
        Optional dashboard ports. Defaults come from
        ``SVTK_METRICS_DASHBOARD_PORT`` and ``SVTK_QC_DASHBOARD_PORT``.
    launch_metrics_dashboard, launch_qc_dashboard
        Optional launch flags. Defaults come from
        ``SVTK_LAUNCH_METRICS_DASHBOARD`` and ``SVTK_LAUNCH_QC_DASHBOARD``.
    auto_port
        Whether to include ``--auto-port``. The notebook default is ``True`` so
        a stale dashboard does not make the cell fail.
    proxy_mode
        Whether to include ``--proxy-mode`` for reverse-proxy notebook
        sessions. Defaults to ``SVTK_DASHBOARD_PROXY_MODE``.
    run_scenario
        Optional run scenario forwarded to dashboard commands.

    Returns
    -------
    NotebookDashboardCommands
        Resolved package-launch settings plus terminal command fallbacks for
        notebook users who prefer to start long-lived dashboard servers outside
        the notebook kernel.
    """

    resolved_config_path = _resolve_dashboard_config_path(config_path)
    resolved_metrics_port = int(
        metrics_port if metrics_port is not None else _env_int("SVTK_METRICS_DASHBOARD_PORT", default=8501)
    )
    resolved_qc_port = int(
        qc_port if qc_port is not None else _env_int("SVTK_QC_DASHBOARD_PORT", default=8502)
    )
    resolved_launch_metrics = (
        _env_bool("SVTK_LAUNCH_METRICS_DASHBOARD", default=False)
        if launch_metrics_dashboard is None
        else bool(launch_metrics_dashboard)
    )
    resolved_launch_qc = (
        _env_bool("SVTK_LAUNCH_QC_DASHBOARD", default=False)
        if launch_qc_dashboard is None
        else bool(launch_qc_dashboard)
    )
    resolved_auto_port = _env_bool("SVTK_DASHBOARD_AUTO_PORT", default=True) if auto_port is None else bool(auto_port)
    resolved_proxy_mode = _env_bool("SVTK_DASHBOARD_PROXY_MODE", default=False) if proxy_mode is None else bool(proxy_mode)

    def command(kind: str, port: int) -> str:
        parts = ["svtk", "dashboard", kind, "--config", str(resolved_config_path), "--port", str(port)]
        if run_scenario:
            parts.extend(["--run-scenario", str(run_scenario)])
        if resolved_auto_port:
            parts.append("--auto-port")
        if resolved_proxy_mode:
            parts.append("--proxy-mode")
        return shlex.join(parts)

    return NotebookDashboardCommands(
        metrics_command=command("metrics", resolved_metrics_port),
        qc_command=command("qc", resolved_qc_port),
        metrics_port=resolved_metrics_port,
        qc_port=resolved_qc_port,
        launch_metrics_dashboard=resolved_launch_metrics,
        launch_qc_dashboard=resolved_launch_qc,
        auto_port=resolved_auto_port,
        proxy_mode=resolved_proxy_mode,
        config_path=resolved_config_path,
        run_scenario=run_scenario,
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


def run_or_submit_notebook_cli_command(
    context: NotebookRunContext,
    command: list[str] | tuple[str, ...],
    *,
    script_name: str,
    job_name: str,
    walltime: str = "12:00:00",
    memory: str = "32G",
    cpus: int = 1,
    run_local: bool | None = None,
    section: str | None = "compute.slurm",
) -> SlurmSubmission | None:
    """Run a Spatial-VTK CLI command locally or wrap it in a SLURM script.

    Deprecated compatibility helper for older notebooks. New notebooks should
    use :func:`run_notebook_step_if_needed` with an importable package function
    so workflow work stays on the public Python API surface. When running
    locally, the command is dispatched through
    :func:`spatial_vtk.cli.main` so callers do not depend on a shell ``svtk``
    executable. When not running locally, an inline-Python SLURM script is
    written and then submitted or printed according to ``context.submit_slurm``.
    """

    warnings.warn(
        "run_or_submit_notebook_cli_command is deprecated for notebooks; use "
        "run_notebook_step_if_needed with an importable package function instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    cmd = [str(part) for part in command]
    print(shlex.join(cmd))
    should_run_local = context.run_local if run_local is None else bool(run_local)
    cli_args = _spatial_vtk_cli_args(cmd)
    if should_run_local:
        return_code = _run_spatial_vtk_cli(cli_args)
        if int(return_code or 0) != 0:
            raise RuntimeError(f"Spatial-VTK CLI command failed with return code {return_code}: {shlex.join(cmd)}")
        return None
    script = write_notebook_python_slurm_script(
        context,
        script_name,
        f"""
        from spatial_vtk.cli import main
        raise SystemExit(main({cli_args!r}))
        """,
        job_name=job_name,
        walltime=walltime,
        memory=memory,
        cpus=cpus,
        section=section,
    )
    return submit_notebook_slurm_script(context, script, section=section)


def run_or_submit_notebook_function(
    context: NotebookRunContext,
    function: str | Callable[..., Any],
    *,
    args: list[Any] | tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
    script_name: str,
    job_name: str,
    walltime: str = "12:00:00",
    memory: str = "32G",
    cpus: int = 1,
    run_local: bool | None = None,
    section: str | None = "compute.slurm",
) -> Any | SlurmSubmission | None:
    """Run an importable package function locally or through Slurm.

    This lower-level helper powers :func:`run_notebook_step_if_needed`. New
    notebooks should usually call that readiness-aware wrapper so each heavy
    step displays its status table, skips current outputs, and then calls the
    package function only when work is needed. Use this helper directly only
    when a caller has already handled readiness and skip logic. Local execution
    calls the Python function directly. Slurm execution writes a small worker
    script that imports the same function and calls it with JSON-serializable
    arguments.

    Parameters
    ----------
    context
        Active notebook run context.
    function
        Top-level package callable, or an import path such as
        ``"spatial_vtk.io.preprocess_waveforms_from_config"`` for compatibility.
        New notebooks should pass the callable itself so cells stay tied to the
        public Python API rather than string paths.
    args, kwargs
        JSON-serializable arguments passed to ``function``.
    script_name, job_name, walltime, memory, cpus, run_local, section
        Slurm/local execution controls matching the lower-level notebook Slurm
        helpers.

    Returns
    -------
    object or SlurmSubmission or None
        Function result when run locally, Slurm submission record when
        submitted, or ``None`` when a script is only printed.
    """

    function_path = _notebook_function_import_path(function)
    payload_args = _notebook_json_payload(list(args))
    payload_kwargs = _notebook_json_payload(dict(kwargs or {}))
    print(_notebook_function_display(function_path, payload_args, payload_kwargs))
    should_run_local = context.run_local if run_local is None else bool(run_local)
    if should_run_local:
        resolved = _resolve_notebook_function(function)
        result = resolved(*payload_args, **payload_kwargs)
        _print_notebook_function_result(result)
        return result
    script = write_notebook_python_slurm_script(
        context,
        script_name,
        f"""
        from spatial_vtk.config.notebook import _run_notebook_function_worker
        raise SystemExit(_run_notebook_function_worker({function_path!r}, {json.dumps(payload_args)!r}, {json.dumps(payload_kwargs)!r}))
        """,
        job_name=job_name,
        walltime=walltime,
        memory=memory,
        cpus=cpus,
        section=section,
    )
    return submit_notebook_slurm_script(context, script, section=section)


def run_notebook_step_if_needed(
    context: NotebookRunContext,
    readiness: Any,
    function: str | Callable[..., Any],
    *,
    args: list[Any] | tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
    script_name: str,
    job_name: str,
    walltime: str = "12:00:00",
    memory: str = "32G",
    cpus: int = 1,
    run_local: bool | None = None,
    section: str | None = "compute.slurm",
    display_fn: Callable[[Any], Any] | None = None,
) -> Any | SlurmSubmission | None:
    """Display readiness status and run a package workflow step when needed.

    Large-run notebooks frequently need the same pattern: show a readiness
    table, submit or run a package helper when outputs are missing/stale, and
    otherwise print the skip message while still showing the status table. This
    helper keeps that control flow in the package while preserving explicit
    function names and resource settings in notebook cells.

    Parameters
    ----------
    context
        Active notebook run context.
    readiness
        Object with ``should_run``, ``message``, and ``status_frame()``
        attributes, such as ``OutputReadiness`` or dashboard readiness objects.
    function
        Top-level package callable, or a compatibility import path passed to
        :func:`run_or_submit_notebook_function` when
        ``readiness.should_run`` is true.
    args, kwargs
        Positional and keyword arguments passed to ``function``.
    script_name, job_name, walltime, memory, cpus, run_local, section
        Passed through to :func:`run_or_submit_notebook_function` when
        ``readiness.should_run`` is true.
    display_fn
        Optional display function used for status frames. When omitted,
        ``IPython.display.display`` is used if available, otherwise the status
        frame is printed.

    Returns
    -------
    object or SlurmSubmission or None
        The underlying run/submission result when work runs, otherwise ``None``.
    """

    _display_notebook_readiness_status(readiness, display_fn=display_fn)
    if bool(getattr(readiness, "should_run", False)):
        return run_or_submit_notebook_function(
            context,
            function,
            args=args,
            kwargs=kwargs,
            script_name=script_name,
            job_name=job_name,
            walltime=walltime,
            memory=memory,
            cpus=cpus,
            run_local=run_local,
            section=section,
        )
    message = getattr(readiness, "message", None)
    if message:
        print(message)
    return None


def _display_notebook_readiness_status(readiness: Any, *, display_fn: Callable[[Any], Any] | None = None) -> None:
    """Display one readiness status frame in notebooks or plain Python."""

    status_frame = readiness.status_frame() if hasattr(readiness, "status_frame") else readiness
    display = display_fn
    if display is None:
        try:
            from IPython.display import display as ipython_display

            display = ipython_display
        except Exception:
            display = None
    if display is not None:
        display(status_frame)
    elif hasattr(status_frame, "to_string"):
        print(status_frame.to_string(index=False))
    else:
        print(status_frame)


def _run_notebook_function_worker(function_path: str, args_json: str, kwargs_json: str) -> int:
    """Run one notebook function payload from a generated Slurm worker."""

    function = _resolve_notebook_function(function_path)
    args = json.loads(args_json)
    kwargs = json.loads(kwargs_json)
    result = function(*args, **kwargs)
    _print_notebook_function_result(result)
    return 0


def _spatial_vtk_cli_args(command: list[str]) -> list[str]:
    """Return arguments suitable for ``spatial_vtk.cli.main``."""

    if not command:
        raise ValueError("CLI command cannot be empty.")
    executable = Path(command[0]).name
    args = command[1:] if executable == "svtk" else command
    if not args:
        raise ValueError("Spatial-VTK CLI command must include a subcommand, for example: svtk qc summaries.")
    if args[0] == "--version":
        return args
    commands = {"config", "io", "qc", "metrics", "spatial", "plot", "map", "visualize", "dashboard", "call"}
    if args[0] not in commands:
        displayed = shlex.join(command)
        raise ValueError(
            "Notebook CLI helpers only run Spatial-VTK CLI commands. "
            f"Pass a command beginning with 'svtk' or a Spatial-VTK subcommand; got: {displayed}"
        )
    return args


def _run_spatial_vtk_cli(args: list[str]) -> int:
    """Run ``spatial_vtk.cli.main`` for a notebook helper."""

    from spatial_vtk.cli import main

    return int(main(args) or 0)


def _notebook_function_import_path(function: str | Callable[..., Any]) -> str:
    """Return an import path for a notebook workflow function."""

    if isinstance(function, str):
        if "." not in function:
            raise ValueError(f"Notebook function must be an import path, got {function!r}.")
        return function
    module = getattr(function, "__module__", "")
    qualname = getattr(function, "__qualname__", "")
    if not module or not qualname or "<locals>" in qualname:
        raise ValueError("Notebook function must be a top-level importable callable.")
    return f"{module}.{qualname}"


def _resolve_notebook_function(function: str | Callable[..., Any]) -> Callable[..., Any]:
    """Resolve one importable notebook workflow function."""

    if callable(function) and not isinstance(function, str):
        return function
    path = _notebook_function_import_path(str(function))
    module_name, _, attr_path = path.rpartition(".")
    if not module_name or not attr_path:
        raise ValueError(f"Notebook function must be a fully qualified import path, got {path!r}.")
    value: Any = importlib.import_module(module_name)
    for part in attr_path.split("."):
        value = getattr(value, part)
    if not callable(value):
        raise TypeError(f"Notebook function import path is not callable: {path}")
    return value


def _notebook_json_payload(value: Any) -> Any:
    """Return a JSON-compatible payload, normalizing Paths to strings."""

    def default(item: Any) -> Any:
        if isinstance(item, Path):
            return str(item)
        raise TypeError(f"Object of type {type(item).__name__} is not JSON serializable.")

    return json.loads(json.dumps(value, default=default))


def _notebook_function_display(function_path: str, args: list[Any], kwargs: dict[str, Any]) -> str:
    """Return one concise notebook task display line."""

    if kwargs:
        return f"{function_path}(**{json.dumps(kwargs, sort_keys=True)})"
    if args:
        return f"{function_path}(*{json.dumps(args)})"
    return f"{function_path}()"


def _print_notebook_function_result(result: Any) -> None:
    """Print a compact, stable result summary for notebook/Slurm output."""

    if result is None:
        return
    try:
        print(json.dumps(result, indent=2, sort_keys=True, default=str))
    except TypeError:
        print(repr(result))


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
    saved = get_saved_config_path()
    if saved:
        return Path(saved).expanduser().resolve()
    candidates = [
        repo_root / "runs" / "spatial_vtk_config.yaml",
        Path.cwd() / "spatial_vtk_config.yaml",
        Path.cwd() / "runs" / "spatial_vtk_config.yaml",
        repo_root / "data" / "examples" / "configuration" / "example_spatial_vtk_config.yaml",
    ]
    return next((path.resolve() for path in candidates if path.exists()), candidates[0].resolve())


def _resolve_dashboard_config_path(config_path: str | Path | None) -> Path:
    """Resolve a config path for dashboard commands without loading tables."""

    if config_path is not None:
        return Path(config_path).expanduser().resolve()
    try:
        active = active_config()
        active_path = getattr(active, "config_path", None)
        if active_path:
            return Path(active_path).expanduser().resolve()
    except Exception:
        pass
    saved = get_saved_config_path()
    if saved:
        return Path(saved).expanduser().resolve()
    env_path = os.environ.get("SVTK_CONFIG")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return _resolve_notebook_config_path(find_repo_root(), None)


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


def _env_bool_first(names: list[str] | tuple[str, ...], *, default: bool) -> bool:
    """Read the first set boolean environment variable from ``names``."""

    for name in names:
        if name in os.environ:
            return _env_bool(name, default=default)
    return bool(default)


def _env_optional_int_first(names: list[str] | tuple[str, ...], *, default: int | None) -> int | None:
    """Read the first set optional integer environment variable from ``names``."""

    for name in names:
        if name not in os.environ:
            continue
        value = os.environ.get(name)
        if value is None:
            continue
        text = str(value).strip().lower()
        if text in {"", "0", "all", "none", "null"}:
            return None
        try:
            return int(text)
        except ValueError:
            return default
    return default


def _env_int_first(names: list[str] | tuple[str, ...], *, default: int) -> int:
    """Read the first set integer environment variable from ``names``."""

    for name in names:
        if name in os.environ:
            return _env_int(name, default=default)
    return int(default)


def _env_float_first(names: list[str] | tuple[str, ...], *, default: float) -> float:
    """Read the first set float environment variable from ``names``."""

    for name in names:
        if name not in os.environ:
            continue
        try:
            return float(os.environ.get(name, default))
        except (TypeError, ValueError):
            return float(default)
    return float(default)


def _env_text_first(names: list[str] | tuple[str, ...], *, default: str | None = None) -> str | None:
    """Read the first non-empty text environment variable from ``names``."""

    for name in names:
        if name not in os.environ:
            continue
        value = os.environ.get(name)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _env_list_first(names: list[str] | tuple[str, ...]) -> list[str] | None:
    """Read the first comma-separated list environment variable from ``names``."""

    text = _env_text_first(names)
    if text is None:
        return None
    items = [item.strip() for item in text.split(",") if item.strip()]
    return items or None


def _figure_setting_names(prefix: str, setting: str) -> list[str]:
    """Return family-specific and generic environment names for a figure setting."""

    names: list[str] = []
    if prefix:
        names.append(f"SVTK_{prefix}_FIGURE_{setting}")
    names.append(f"SVTK_FIGURE_{setting}")
    return names


def _figure_env_prefix(figure_kind: str | None) -> str:
    """Return the environment-variable prefix for one figure family."""

    if not figure_kind:
        return ""
    return str(figure_kind).strip().upper().replace("-", "_").replace(" ", "_")


__all__ = [
    "NotebookDashboardCommands",
    "NotebookFigureSettings",
    "NotebookFigureSidecarSettings",
    "NotebookRunContext",
    "display_output_table_previews",
    "find_repo_root",
    "format_run_time",
    "notebook_dashboard_launch_commands",
    "notebook_figure_settings",
    "notebook_figure_sidecar_settings",
    "notebook_timer",
    "notebook_timing_enabled",
    "notebook_run_context",
    "prepare_notebook_geospatial_environment",
    "print_run_time",
    "print_notebook_context",
    "register_svtk_cell_timer",
    "register_svtk_time_magic",
    "run_notebook_step_if_needed",
    "run_or_submit_notebook_function",
    "submit_notebook_slurm_script",
    "write_notebook_python_slurm_script",
]
