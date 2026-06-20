"""Stable configuration helpers for Spatial-VTK notebooks and scripts.

``spatial_vtk.config`` is the public import surface for runtime config
objects, notebook run contexts, output-registry previews, Slurm settings,
metric settings, labels, and figure controls. Routine notebooks should import
from this package rather than reaching into runtime, output, or notebook
implementation modules directly.

The package keeps its broad public surface lazy: importing ``spatial_vtk.config``
does not import runtime YAML parsing, compute helpers, notebook utilities, or
output registries until the requested helper is accessed.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MODULES = {
    "ROOT_DIR": "spatial_vtk.config.paths",
    "DEFAULT_METRIC_GROUPS": "spatial_vtk.config.metrics",
    "DEFAULT_METRICS": "spatial_vtk.config.metrics",
    "DEFAULT_OUTPUT_MODE": "spatial_vtk.config.metrics",
    "DEFAULT_TRANSFORMS": "spatial_vtk.config.metrics",
    "VALID_OUTPUT_MODES": "spatial_vtk.config.metrics",
    "VALID_TRANSFORMS": "spatial_vtk.config.metrics",
    "ALL_METRIC_GROUPS": "spatial_vtk.config.metric_catalog",
    "ALL_METRICS": "spatial_vtk.config.metric_catalog",
    "DEFAULT_METRICS_BY_GROUP": "spatial_vtk.config.metric_catalog",
    "LEGACY_METRIC_ALIASES": "spatial_vtk.config.metric_catalog",
    "MetricSettings": "spatial_vtk.config.metrics",
    "OutputSpec": "spatial_vtk.config.outputs",
    "SpectralSettings": "spatial_vtk.config.metrics",
    "NotebookFigureSidecarSettings": "spatial_vtk.config.notebook",
    "NotebookFigureSettings": "spatial_vtk.config.notebook",
    "NotebookFigureRenderGate": "spatial_vtk.config.notebook",
    "NotebookDashboardCommands": "spatial_vtk.config.notebook",
    "NotebookRunContext": "spatial_vtk.config.notebook",
    "SVTK_CLI_CONFIG_ENV": "spatial_vtk.config.runtime",
    "SVTK_CONFIG_ENV": "spatial_vtk.config.runtime",
    "SlurmSettings": "spatial_vtk.config.compute",
    "SlurmSubmission": "spatial_vtk.config.compute",
    "SpatialVTKConfig": "spatial_vtk.config.runtime",
    "METRIC_DISPLAY_NAMES": "spatial_vtk.config.labels",
    "VALUE_COLUMN_LABELS": "spatial_vtk.config.labels",
    "COLUMN_DISPLAY_LABELS": "spatial_vtk.config.labels",
    "abbreviate_model": "spatial_vtk.config.naming",
    "active_config": "spatial_vtk.config.runtime",
    "apply_run_scenario": "spatial_vtk.config.runtime",
    "clear_saved_config_path": "spatial_vtk.config.runtime",
    "clear_active_config": "spatial_vtk.config.runtime",
    "available_dashboard_value_columns": "spatial_vtk.config.labels",
    "band_display_label": "spatial_vtk.config.labels",
    "band_display_options": "spatial_vtk.config.labels",
    "column_display_lookup": "spatial_vtk.config.labels",
    "column_display_name": "spatial_vtk.config.labels",
    "configured_output_registry_frame": "spatial_vtk.config.outputs",
    "configured_output_registry_preview_frame": "spatial_vtk.config.outputs",
    "deep_merge": "spatial_vtk.config.runtime",
    "default_output_registry": "spatial_vtk.config.outputs",
    "display_label": "spatial_vtk.config.labels",
    "display_table": "spatial_vtk.config.labels",
    "display_output_table_previews": "spatial_vtk.config.notebook",
    "ensure_dir": "spatial_vtk.config.paths",
    "find_repo_root": "spatial_vtk.config.notebook",
    "find_config_file": "spatial_vtk.config.runtime",
    "format_run_time": "spatial_vtk.config.notebook",
    "get_saved_config_path": "spatial_vtk.config.runtime",
    "load_bounds_presets": "spatial_vtk.config.bounds",
    "load_config": "spatial_vtk.config.runtime",
    "infer_output_key": "spatial_vtk.config.outputs",
    "metric_display_name": "spatial_vtk.config.labels",
    "metric_group_for": "spatial_vtk.config.metric_catalog",
    "metric_settings_summary": "spatial_vtk.config.metrics",
    "metrics_settings_from_config": "spatial_vtk.config.metrics",
    "notebook_timer": "spatial_vtk.config.notebook",
    "notebook_dashboard_launch_commands": "spatial_vtk.config.notebook",
    "notebook_figure_settings": "spatial_vtk.config.notebook",
    "notebook_figure_sidecar_settings": "spatial_vtk.config.notebook",
    "notebook_timing_enabled": "spatial_vtk.config.notebook",
    "notebook_run_context": "spatial_vtk.config.notebook",
    "notebook_step_result": "spatial_vtk.config.notebook",
    "prepare_notebook_geospatial_environment": "spatial_vtk.config.notebook",
    "normalize_metric_groups": "spatial_vtk.config.metric_catalog",
    "normalize_metric_name": "spatial_vtk.config.labels",
    "output_description": "spatial_vtk.config.outputs",
    "output_spec": "spatial_vtk.config.outputs",
    "preset_keywords": "spatial_vtk.config.bounds",
    "print_notebook_context": "spatial_vtk.config.notebook",
    "print_run_time": "spatial_vtk.config.notebook",
    "register_svtk_cell_timer": "spatial_vtk.config.notebook",
    "register_svtk_time_magic": "spatial_vtk.config.notebook",
    "render_notebook_figure": "spatial_vtk.config.notebook",
    "run_notebook_step_if_needed": "spatial_vtk.config.notebook",
    "run_or_submit_notebook_function": "spatial_vtk.config.notebook",
    "resolve_output_path": "spatial_vtk.config.outputs",
    "resolve_path": "spatial_vtk.config.runtime",
    "resolve_named_bounds": "spatial_vtk.config.bounds",
    "slurm_header": "spatial_vtk.config.compute",
    "slurm_settings_from_config": "spatial_vtk.config.compute",
    "slurm_settings_with_overrides": "spatial_vtk.config.compute",
    "submit_or_print_slurm_script": "spatial_vtk.config.compute",
    "submit_notebook_slurm_script": "spatial_vtk.config.notebook",
    "submit_slurm_script": "spatial_vtk.config.compute",
    "write_inline_python_slurm_script": "spatial_vtk.config.compute",
    "write_notebook_python_slurm_script": "spatial_vtk.config.notebook",
    "set_saved_config_path": "spatial_vtk.config.runtime",
    "resolve_metric_names": "spatial_vtk.config.metric_catalog",
    "resolve_run_defaults": "spatial_vtk.config.runtime",
    "transform_display_options": "spatial_vtk.config.labels",
    "transform_columns": "spatial_vtk.config.metrics",
    "value_column_display_name": "spatial_vtk.config.labels",
}

__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    """Load one public configuration helper lazily."""

    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module 'spatial_vtk.config' has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
