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

.. automodule:: spatial_vtk.config.runtime
   :members:

Paths and Outputs
-----------------

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
   * - ``NotebookFigureSettings`` and ``notebook_figure_settings``
     - Parse figure controls, robust-axis settings, sidecar settings, and
       render gates from environment variables in one package-owned helper.
   * - ``render_notebook_figure``
     - Call one plotting helper with configured output path, ``showfig``,
       basemap, sidecar, save, display, and close behavior.
   * - ``NotebookFigureSidecarSettings`` and
       ``notebook_figure_sidecar_settings``
     - Configure optional plotted-row and source-row CSV/JSON sidecars.
   * - ``NotebookDashboardCommands`` and
       ``notebook_dashboard_launch_commands``
     - Resolve dashboard launch settings from config-backed dashboard outputs.
   * - ``display_output_table_previews``
     - Print configured output-table paths and display bounded previews without
       repeating path-resolution code in notebooks.
   * - ``prepare_notebook_geospatial_environment``
     - Set conservative geospatial/threading defaults for notebook and docs
       execution.
