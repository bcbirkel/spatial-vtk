Configuration API
=================

Configuration helpers load project YAML files, resolve paths and bounds, manage
default outputs, normalize labels, and keep metric settings consistent.

.. contents:: On this page
   :local:
   :depth: 2

Package Entry Point
-------------------

.. automodule:: spatial_vtk.config
   :members:

Runtime Configuration
---------------------

Start routine notebooks, scripts, and Slurm workers from
``spatial_vtk.config`` helpers such as ``notebook_run_context()``,
``SpatialVTKConfig``, ``active_config()``, ``load_config()``,
``find_config_file()``, and ``resolve_run_defaults()``. These runtime helpers
are re-exported by the package entry point so public code does not need to
reach into implementation modules directly.

.. autosummary::
   :nosignatures:

   spatial_vtk.config.SpatialVTKConfig
   spatial_vtk.config.active_config
   spatial_vtk.config.clear_active_config
   spatial_vtk.config.find_config_file
   spatial_vtk.config.get_saved_config_path
   spatial_vtk.config.load_config
   spatial_vtk.config.resolve_path
   spatial_vtk.config.resolve_run_defaults
   spatial_vtk.config.set_saved_config_path

Paths and Outputs
-----------------

Routine notebooks should start with the standard ``load_standard_*`` workflow
result loaders from ``spatial_vtk.io``, ``spatial_vtk.qc``,
``spatial_vtk.metrics``, and ``spatial_vtk.spatial``; those result objects own
configured paths, status tables, bounded previews, and notebook
skip/rebuild helpers. Use ``output_group()`` only for custom helpers that need
a reusable group of configured artifacts before a standard result object
exists. The path and output modules below document lower-level registry and
resolver APIs for scripts, CLIs, generated workers, and package extension
code. ``resolve_output_path()`` accepts either a ``SpatialVTKConfig`` object or
a config file path through ``cfg=`` so those scripts can resolve registered
table, figure, and dashboard outputs without activating global config state.

.. automodule:: spatial_vtk.config.paths
   :members:

.. automodule:: spatial_vtk.config.outputs
   :members:

Bounds
------

.. automodule:: spatial_vtk.config.bounds
   :members:

Metrics
-------

.. automodule:: spatial_vtk.config.metrics
   :members:

.. automodule:: spatial_vtk.config.metric_catalog
   :members:

Compute and Slurm
-----------------

.. automodule:: spatial_vtk.config.compute
   :members:

Labels and Naming
-----------------

.. automodule:: spatial_vtk.config.labels
   :members:

.. automodule:: spatial_vtk.config.naming
   :members:

Notebook Helpers
----------------

Import notebook helpers from ``spatial_vtk.config``. The implementation lives
in an internal submodule, but tutorial notebooks and public scripts should use
the stable package surface below.

.. list-table::
   :header-rows: 1

   * - Helper
     - Use
   * - ``NotebookRunContext`` and ``notebook_run_context``
     - Resolve config, run scenario, output directories, overwrite flags,
       Slurm/local execution flags, and notebook runtime settings once.
   * - ``run_notebook_step_if_needed``
     - Display readiness, skip current outputs, run a Python package function
       locally, or write/submit a Slurm script for the same function.
   * - ``notebook_step_result`` and ``notebook_step_result_frame``
     - Build compact current/skipped status payloads and labelled display
       frames for one-off custom steps outside the standard workflow result
       objects. Prefer the standard result object's ``run_*_step_if_needed()``
       methods when they exist; use these helpers instead of hand-written
       dictionaries with generic ``path`` keys in notebook cells.
   * - ``display_notebook_step_result``
     - Display a compact table for skipped/current step payloads, Slurm
       submission results, and result objects with ``status_frame()`` or
       ``summary_frame()`` so notebooks do not print raw dictionaries,
       summary strings, or dataclass representations. ``SlurmSubmission`` owns
       ``status_frame()`` with normalized ``name``, ``artifact_label``,
       ``resolved_path``, ``path``, and ``exists`` columns plus the job id,
       legacy ``script_path``, submit command, stdout, stderr, and return code.
   * - ``NotebookFigureSettings`` and ``notebook_figure_settings``
     - Parse figure controls, robust-axis settings, sidecar settings, and
       render gates from environment variables in one package-owned helper.
       Standard notebooks should receive these settings through workflow
       result-object figure methods. Custom package helpers and focused
       scripts can use ``context_kwargs()`` for large-run figure contexts,
       ``plot_kwargs()`` for individual plotting functions, and
       ``plot_selection_kwargs()`` for context-managed plotting calls that
       need passband, component, model, value-column, basemap, or robust-axis
       selections. ``render_gate(...).status_frame()`` reports artifact ids,
       labels, roles, compact ``ready``/``disabled``/``missing_inputs``
       status, the user-facing message, and exact missing input paths.
   * - ``render_notebook_figure``
     - Lower-level rendering delegate for package figure wrappers or custom
       helpers that already own the configured output path, ``showfig``,
       basemap, sidecar, save, display, and close behavior. Routine notebooks
       should call workflow result-object figure methods instead.
   * - ``NotebookFigureSidecarSettings`` and
       ``notebook_figure_sidecar_settings``
     - Configure optional plotted-row and source-row CSV/JSON sidecars.
       ``readiness_frame()`` reports whether sidecars are enabled, where JSON
       metadata will be read, how row sampling is configured, and normalized
       ``artifact``, ``artifact_role``, ``status``, ``resolved_path``,
       ``path``, and ``exists`` columns for the sidecar directory;
       ``status_frame()`` reports disabled/not-configured/missing-directory
       states when no metadata exists yet and per-figure provenance from saved
       JSON sidecars after rendering, without loading large CSV row files.
       Normalized figure status rows include ``status_reason`` for structured
       notebook filtering.
   * - ``NotebookDashboardCommands`` and
       ``notebook_dashboard_launch_commands``
     - Resolve dashboard launch settings from config-backed dashboard outputs;
       ``status_frame()`` reports ``name``, ``artifact``, ``artifact_label``,
       ``artifact_role``, launch-plan ``status``, ``metrics_dataset_dir``,
       ``dashboard_summary_table_dir``, and ``qc_trace_summary_table`` with
       existence flags, without notebooks resolving paths themselves.
   * - ``display_output_table_previews``
     - Print configured output-table paths and display bounded previews without
       repeating path-resolution code in notebooks.
   * - ``configured_output_registry_frame`` and
       ``configured_output_registry_preview_frame``
     - Inspect the configured table, figure, and dashboard output registry with
       ``artifact_label`` and ``resolved_path`` columns. Use the preview helper
       in notebooks when only a bounded path listing is needed.
   * - ``prepare_notebook_geospatial_environment``
     - Set conservative geospatial/threading defaults for notebook and docs
       execution.
