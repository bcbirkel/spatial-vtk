Python Workflow Entry Points
============================

Use these helpers when a notebook or Python script needs to run a configured
Spatial-VTK workflow step. They resolve paths from the active config or from a
``config_path`` argument, write the standard output tables, and return compact
metadata dictionaries that are safe to print in notebooks.

For large datasets, keep notebook cells as lightweight drivers:

Notebooks should use package functions for workflow work; reserve CLI commands
for terminal-oriented workflows and generated batch scripts.

1. Build or load small metadata tables locally.
2. Use ``output_readiness`` or a dashboard readiness helper to decide whether a
   heavy step is missing or stale.
3. Call ``run_notebook_step_if_needed`` with one of the package workflow
   functions below. The helper either runs locally or writes/submits a Slurm
   script using the same Python function.
4. Preview bounded tables after outputs exist; do not load full QC or metric
   inventories into the notebook just to check progress.

Workflow functions return JSON-ready dictionaries that are safe to display in
notebooks or Slurm logs. New notebook code should prefer explicit keys such as
``metric_manifest_path``, ``observed_metric_inventory_path``,
``record_coverage_path``, and ``geojson_region_summaries_path``. These
descriptive keys are the public notebook contract: they make status tables,
logs, and downstream cells readable without checking each helper's
implementation. A few helpers may still return older short aliases internally
for backward compatibility, but notebooks and docs should not depend on generic
names such as ``path``, ``output``, or ``manifest``.

Every dotted helper listed on this page is an importable public entry point.
Tutorial notebooks should import these package functions directly rather than
calling CLI commands from cells.

Config-backed spatial, GeoJSON, and corridor helpers also accept dotted path
keys such as ``"paths.metric_figure_snapshot"``, ``"paths.site_metadata"``,
``"paths.region_geojson"``, or ``"paths.event_station_table"`` for optional
inputs, so notebooks can select configured inputs without resolving filesystem
paths in cells.

.. code-block:: python

   from spatial_vtk.config import SpatialVTKConfig
   from spatial_vtk.config import configured_output_registry_frame
   from spatial_vtk.config.notebook import notebook_figure_settings, notebook_run_context, run_notebook_step_if_needed
   from spatial_vtk.io import load_configured_input_tables, output_group
   from spatial_vtk.qc import run_qc_inventory_from_config

   cfg = SpatialVTKConfig.from_file("runs/spatial_vtk_config.yaml").activate()
   context = notebook_run_context()
   step_outputs = output_group("step_02_qc", cfg=cfg)
   step_outputs.bind(globals(), names=("trace_qc_path", "event_station_path"))
   display(configured_output_registry_frame(cfg=cfg, kinds=("table",)).head())
   display(step_outputs.status_frame())
   readiness = step_outputs.readiness(
       "trace_qc_path",
       inputs=("event_station_path",),
       sources=("event_station_path",),
   )

   run_notebook_step_if_needed(
       context,
       readiness,
       run_qc_inventory_from_config,
       kwargs={"config_path": str(cfg.config_path), "overwrite": False, "verbose": True},
       script_name="build_qc_inventory.slurm",
       job_name="svtk-qc",
       walltime="24:00:00",
       memory="64G",
       cpus=1,
   )

   metric_figure_settings = notebook_figure_settings("metric", figure_dir=context.figures_dir / "metrics")
   # Pass metric_figure_settings.context_kwargs(...) into package plotting
   # contexts instead of parsing SVTK_FIGURE_* variables in notebook cells.
   configured_inputs = load_configured_input_tables({"metrics": "paths.metric_figure_snapshot"}, cfg=cfg)

Core Driver Helpers
-------------------

These helpers are the notebook control plane. They keep config loading,
readiness checks, local execution, and Slurm script generation consistent across
the large-run notebooks.

.. list-table::
   :header-rows: 1

   * - Helper
     - Use
   * - ``spatial_vtk.config.notebook_run_context``
     - Resolve config, run scenario, output directories, and run/submit flags
       once near the top of a notebook.
   * - ``spatial_vtk.io.output_readiness``
     - Report whether configured outputs are missing, stale relative to inputs,
       blocked by missing inputs, or ready to reuse.
   * - ``spatial_vtk.io.output_group``
     - Resolve a named workflow output group once, then use attribute access,
       ``bind()``, ``status_frame()``, ``completion()``, and ``readiness()``
       instead of cluttering notebooks with repeated path variables.
       ``bind(globals())`` exposes conventional names such as
       ``metrics_long_path`` in a notebook setup cell. ``readiness()`` can
       receive registered output, input, and source path names such as
       ``"metrics_long_path"`` and resolves them to configured paths before
       building the status table. ``load_tables()`` and ``preview_tables()``
       read selected table artifacts by group path name, output key, or a
       display-label mapping, which keeps notebook cells focused on workflow
       tasks rather than repeated ``load_output_table`` calls.
   * - ``spatial_vtk.io.load_configured_input_tables``
     - Load non-output input tables from dotted config path keys such as
       ``"paths.metric_figure_snapshot"`` or ``"paths.site_metadata"`` into a
       labeled dictionary. Use this for tutorial figure inputs and optional
       spatial metadata instead of repeating direct ``read_config_table`` calls
       in notebook cells.
   * - ``spatial_vtk.config.run_notebook_step_if_needed``
     - Display the readiness table, then run or submit a Python package
       workflow function only when work is needed. Pass the imported package
       function directly in notebooks; fully qualified import-path strings are
       retained only for compatibility and generated Slurm workers.
   * - ``spatial_vtk.config.display_output_table_previews``
     - Print configured output-table paths and display bounded row previews
       without repeating ``resolve_output_path`` or ``preview_output_table``
       loops in notebook cells.
   * - ``spatial_vtk.config.notebook_figure_sidecar_settings``
     - Read the notebook-side figure sidecar settings and return keyword
       arguments accepted by supported plotting helpers. The returned settings
       object also has ``status_frame()``, which reads only the small sidecar
       JSON files and shows which figures were written, whether row sidecars
       are exact or sampled, and which aggregated figures include source-row
       provenance.
   * - ``spatial_vtk.config.notebook_figure_settings``
     - Read common notebook figure controls such as ``SVTK_MAKE_FIGURES``,
       ``SVTK_MAKE_METRIC_FIGURES``, ``SVTK_ADD_BASEMAP``,
       ``SVTK_FIGURE_PASSBAND``, ``SVTK_FIGURE_COMPONENTS``,
       ``SVTK_FIGURE_SHOWFIG``, ``SVTK_FIGURE_ROBUST_PERCENTILE``, and sidecar
       settings once. Use ``context_kwargs()`` for large-run plotting contexts
       and ``plot_kwargs()`` for single plotting calls so notebook cells stay
       focused on the figure being rendered. Region/corridor notebooks also
       retain the existing ``SVTK_REGION_*`` controls through this helper, and
       optional GOF score-trend diagnostics use
       ``notebook_figure_settings("score_trend")`` so
       ``SVTK_MAKE_SCORE_TRENDS`` and ``SVTK_SCORE_TREND_COLUMNS`` are parsed
       by package code rather than notebook cells.
   * - ``spatial_vtk.config.notebook_dashboard_launch_commands``
     - Return config-backed dashboard launch settings. Use
       ``metrics_launch_kwargs()`` and ``qc_launch_kwargs()`` with the package
       dashboard launch helpers; the shell-safe command strings are retained as
       a terminal fallback for long-lived dashboard sessions. The returned
       settings also parse ``SVTK_LAUNCH_METRICS_DASHBOARD`` and
       ``SVTK_LAUNCH_QC_DASHBOARD`` so notebooks do not repeat dashboard
       launch environment parsing in cells.

Step 1: Metadata, Waveforms, and Record Coverage
------------------------------------------------

.. list-table::
   :header-rows: 1

   * - Task
     - Python entry point
     - Standard outputs
   * - Prepare stations, events, and event-station rows
     - ``spatial_vtk.io.prepare_metadata_tables_from_config``
     - ``prepared_stations``, ``prepared_events``,
       ``event_station_records``
   * - Preprocess observed/synthetic waveforms
     - ``spatial_vtk.io.preprocess_waveforms_from_config``
     - preprocessed waveform files, preprocessing manifest,
       trace metadata, preprocessed event-station records
   * - Build record coverage from trace metadata
     - ``spatial_vtk.io.build_record_coverage_from_config``
     - ``record_coverage``

Step 2: Quality Control
-----------------------

.. list-table::
   :header-rows: 1

   * - Task
     - Python entry point
     - Standard outputs
   * - Build full waveform and metric QC inventories
     - ``spatial_vtk.qc.run_qc_inventory_from_config``
     - ``qc_trace_summary`` and ``qc_inventory``
   * - Write the observed/synthetic event-station overlap inventory
     - ``spatial_vtk.qc.write_qc_inventory_overlap_from_config``
     - ``qc_inventory_overlap``
   * - Build compact QC summary tables for figures and dashboards
     - ``spatial_vtk.qc.run_qc_summary_workflow_from_config``
     - retention, availability, post-QC record, and drop-cause tables

The full QC inventory can be useful for observed-only or synthetic-only
analysis, but metric calculations should normally use the overlap inventory so
they only plan observed/synthetic pairs that can be compared.

Step 3: Metric Calculation and Metric Figures
---------------------------------------------

.. list-table::
   :header-rows: 1

   * - Task
     - Python entry point
     - Standard outputs
   * - Build metric-ready observed/synthetic waveform inventories
     - ``spatial_vtk.metrics.build_metric_waveform_inventories_from_config``
     - ``observed_metric_inventory`` and ``synthetic_metric_inventory``
   * - Plan metric tasks and write a manifest
     - ``spatial_vtk.metrics.plan_metric_tasks_from_config``
     - ``metric_manifest`` plus per-batch output paths
   * - Preview task counts from a configured metric snapshot
     - ``spatial_vtk.metrics.summarize_metric_snapshot_tasks_from_config``
     - ``metric_tasks`` and ``metric_task_estimate``
   * - Write or submit a metric Slurm array script
     - ``spatial_vtk.metrics.metric_slurm_submission_readiness`` plus
       ``spatial_vtk.metrics.write_metrics_slurm_script_from_config``
     - metric Slurm script; optionally submitted job metadata
   * - Merge completed metric batches
     - ``spatial_vtk.metrics.merge_metric_batches_from_config``
     - ``metric_rows``
   * - Write downstream long, enriched, summary, and dashboard metric tables
     - ``spatial_vtk.metrics.write_metric_outputs_from_config``
     - ``metrics_long``, ``metrics_enriched``, path tables, dashboard metric
       datasets, dashboard summary tables
   * - Render many large-run metric figures with auditable row sidecars
     - ``spatial_vtk.metrics.plot.prepare_large_run_metric_figure_context``
     - saved metric figures and optional ``*.csv``/``*.source.csv``/``*.json``
       sidecars

Step 4: Spatial Statistics
--------------------------

.. list-table::
   :header-rows: 1

   * - Task
     - Python entry point
     - Standard outputs
   * - Build spatial-statistics summary tables
     - ``spatial_vtk.spatial.run_spatial_statistics_workflow_from_config``
     - metric field, event-centered residuals, station bias, Moran's I,
       distance correlation, cluster, PCA, and geology tables
   * - Build optional derived spatial outputs
     - ``spatial_vtk.spatial.run_spatial_derived_outputs_workflow_from_config``
     - block holdout, REDCAP, and pattern-similarity tables
   * - Render large-run spatial figures
     - ``spatial_vtk.spatial.plot.prepare_spatial_figure_context``
     - saved spatial figures and optional row-provenance sidecars

Step 5: GeoJSON Regions and Corridors
-------------------------------------

.. list-table::
   :header-rows: 1

   * - Task
     - Python entry point
     - Standard outputs
   * - Summarize configured GeoJSON regions
     - ``spatial_vtk.spatial.run_geojson_region_summary_workflow_from_config``
     - GeoJSON region summary tables
   * - Build configured boundary corridors
     - ``spatial_vtk.spatial.run_boundary_corridor_workflow_from_config``
     - corridor definitions and corridor-selected records

Both Step 5 helpers can receive configured path keys for optional inputs. For
example, pass ``metrics_table="paths.metric_figure_snapshot"`` or
``geojson_path="paths.region_geojson"`` when a notebook needs to select a
configured non-default input without adding path-resolution cells.

Step 7: Dashboard Datasets
--------------------------

.. list-table::
   :header-rows: 1

   * - Task
     - Python entry point
     - Standard outputs
   * - Check dashboard dataset readiness without loading full inventories
     - ``spatial_vtk.visualize.dashboard.dashboard_readiness_summary_frame``,
       ``spatial_vtk.visualize.dashboard.dashboard_output_status_frame``, and
       ``spatial_vtk.visualize.dashboard.dashboard_output_readiness``
     - compact tab-level readiness plus detailed status frames
   * - Write dashboard-ready row and summary datasets
     - ``spatial_vtk.visualize.dashboard.write_configured_dashboard_datasets``
     - dashboard metric dataset root and dashboard summary table root; standard
       dashboard artifacts are replaced so stale partitions or stale
       CSV/Parquet summary files do not mix with the current run
   * - Launch dashboards from Python
     - ``spatial_vtk.config.notebook_dashboard_launch_commands``,
       ``spatial_vtk.visualize.dashboard.launch_configured_metrics_dashboard``,
       ``spatial_vtk.visualize.dashboard.launch_configured_qc_dashboard``,
       ``spatial_vtk.visualize.dashboard.launch_metrics_dashboard``, and
       ``spatial_vtk.visualize.dashboard.launch_qc_dashboard``
     - local Streamlit processes configured from the same output registry,
       optional terminal fallback commands, and a bounded
       ``dashboard_launch.status_frame()`` preview showing ports, commands, and
       configured dashboard inputs

Related API Pages
-----------------

The workflow helpers above are stable entry points. Use the module pages for
exact signatures and lower-level utilities:

- :doc:`api/config`
- :doc:`api/io`
- :doc:`api/qc`
- :doc:`api/metrics`
- :doc:`api/spatial`
- :doc:`api/visualize`
