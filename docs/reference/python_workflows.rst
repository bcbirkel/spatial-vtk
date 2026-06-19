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
``metric_manifest_batch_output_dir``, ``preprocessed_manifest_path``,
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

   from spatial_vtk.config import configured_output_registry_preview_frame
   from spatial_vtk.config import (
       notebook_figure_settings,
       notebook_run_context,
       render_notebook_figure,
       run_notebook_step_if_needed,
   )
   from spatial_vtk.io import event_rows_for_records, load_configured_input_paths, load_configured_input_tables, output_group
   from spatial_vtk.qc import run_qc_inventory_from_config

   context = notebook_run_context()
   cfg = context.cfg
   step_outputs = output_group("step_02_qc", cfg=cfg)
   display(configured_output_registry_preview_frame(cfg=cfg, kinds=("table",)))
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
       kwargs={"config_path": str(context.config_path), "overwrite": False, "verbose": True},
       script_name="build_qc_inventory.slurm",
       job_name="svtk-qc",
       walltime="24:00:00",
       memory="64G",
       cpus=1,
   )

   metric_figure_settings = notebook_figure_settings("metric", figure_subdir="metrics")
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
       once near the top of a notebook. The helper honors ``SVTK_RUN_SCENARIO``
       when no scenario is passed and exposes the resolved value as
       ``context.run_scenario`` for downstream package helpers. It also owns
       common execution controls such as ``SVTK_QC_CHUNKSIZE``,
       ``SVTK_METRIC_BATCH_COUNT``, and
       ``SVTK_PREPROCESS_CONTINUE_ON_ERROR`` so cells can pass
       ``context.<field>`` values into package workflow functions.
   * - ``spatial_vtk.io.output_readiness``
     - Report whether configured outputs are missing, stale relative to inputs,
       blocked by missing inputs, or ready to reuse.
   * - ``spatial_vtk.io.output_group``
     - Resolve a named workflow output group once, then use attribute access,
       ``bind()``, ``status_frame()``, ``completion()``, and ``readiness()``
       instead of cluttering notebooks with repeated path variables.
       Prefer direct attributes such as ``step_outputs.metrics_long_path`` when
       a cell needs a resolved path; ``bind()`` remains available for older
       notebooks but should not be the default pattern for new tutorial cells.
       ``readiness()`` can receive registered output, input, and source path
       names such as ``"metrics_long_path"`` and resolves them to configured
       paths before building the status table. ``load_table()`` and
       ``preview_table()`` read one table artifact by group path name or output
       key; ``load_tables()``, ``preview_tables()``, and
       ``display_table_previews()`` handle multiple tables or display-label
       mappings. Pass ``missing="skip"`` when a figure can use an optional
       output if present but should continue without it.
       Legacy helpers such as ``output_group_namespace()`` return only path
       attributes; new notebooks should use ``output_group()`` so readiness,
       previews, completion checks, and figure-path helpers stay attached to
       the same object.
       For output groups that own table paths outside the configured output
       registry, such as preprocessing metadata, use ``load_path_table()`` or
       ``preview_path_table()`` with the group path name for one table, or
       ``display_path_table_previews()`` for display-label mappings and bounded
       notebook previews. This keeps path-backed artifacts out of direct
       ``read_table(...).head()`` calls.
       Use ``figure_path()`` for figure artifacts that need configured
       directories but metric-specific filenames; pass ``stem_parts`` instead
       of constructing ``figure_dir / "name.png"`` in notebook cells.
       When a required input comes from an optional config value, pass the
       named mapping value as ``None``. The readiness/status table displays
       ``<not configured>`` and blocks the step cleanly instead of using a
       fake placeholder path.
       ``first_existing_path()`` and ``preview_first_existing_table()`` cover
       common fallback cases such as
       preferring ``metrics_enriched`` when it exists and otherwise using
       ``metrics_long``; ``display_first_existing_table_preview()`` prints and
       displays that selected fallback in one package call. These helpers keep
       notebook cells focused on workflow tasks rather than repeated table-path
       and preview plumbing.
   * - ``spatial_vtk.io.preprocessed_waveform_output_group``
     - Resolve the preprocessing metadata directory as an ``OutputGroup``.
       Use this for Step 1 preprocessed event-station records, preprocessing
       manifests, and trace metadata because those artifacts live under
       ``outputs.preprocessed_waveforms/metadata`` rather than the standard
       table registry.
   * - ``spatial_vtk.io.load_configured_input_tables``
     - Load non-output input tables from dotted config path keys such as
       ``"paths.metric_figure_snapshot"`` or ``"paths.site_metadata"`` into a
       labeled dictionary. Use this for tutorial figure inputs and optional
       spatial metadata instead of repeating direct ``read_config_table`` calls
       in notebook cells.
   * - ``spatial_vtk.io.load_configured_input_paths``
     - Resolve non-table configured inputs such as ``"paths.region_geojson"``
       into a labeled path dictionary. Use this when plotting or spatial helper
       calls need a configured file path but should not own config path
       resolution in the notebook cell.
   * - ``spatial_vtk.io.event_ids_from_records``,
       ``spatial_vtk.io.event_rows_for_records``, and
       ``spatial_vtk.io.event_label_preview_frame``
     - Build event-id lists, matching event metadata subsets, and compact
       event label previews from record tables. Use these helpers in plotting
       and corridor notebooks instead of repeating
       ``events.loc[events["event_id"].isin(...)]`` or first-row label
       lookups in cells.
   * - ``spatial_vtk.config.run_notebook_step_if_needed``
     - Display the readiness table, then run or submit a Python package
       workflow function only when work is needed. Pass the imported package
       function directly in notebooks; fully qualified import-path strings are
       retained only for compatibility and generated Slurm workers. The
       tutorial notebook preflight fails cells that pass compatibility strings
       such as ``"spatial_vtk.qc.run_qc_inventory_from_config"`` instead of the
       imported callable ``run_qc_inventory_from_config``.
   * - ``spatial_vtk.config.notebook_step_result``
     - Return a compact JSON-friendly status dictionary for current/skipped
       notebook workflow steps. Use this with ``run_notebook_step_if_needed``
       fallbacks instead of writing inline dictionaries that repeat
       ``str(path)`` conversion, ``reused`` flags, or generic ``path`` keys in
       notebook cells.
   * - ``spatial_vtk.metrics.metric_slurm_submission_readiness_from_config``
     - Report whether the configured metric Slurm array should be written or
       submitted, including missing manifests and already-complete batch
       outputs, without notebook-local manifest path checks.
   * - ``spatial_vtk.metrics.metric_batch_merge_readiness_from_config``
     - Gate metric batch merging from the active config. The helper reports
       incomplete Slurm batches with a bounded display of missing batch paths,
       and uses all completed batch outputs as freshness dependencies before
       rebuilding the merged metric rows table.
   * - ``spatial_vtk.metrics.metric_outputs_readiness_from_config``
     - Gate downstream metric output tables such as ``metrics_long``,
       ``path_table``, and ``path_summary`` from the active config, so notebooks
       do not repeat direct ``metric_rows`` existence checks.
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
       focused on the figure being rendered. Use ``plot_selection_kwargs()``
       for context-managed figure families that share passband, component,
       model, value-column, basemap, or robust-axis selections across many
       calls. Region/corridor notebooks also
       retain the existing ``SVTK_REGION_*`` controls through this helper,
       spatial PCA figures use ``SVTK_PCA_MODE`` through
       ``notebook_figure_settings("spatial")``, and optional GOF score-trend
       diagnostics use
       ``notebook_figure_settings("score_trend")`` so
       ``SVTK_MAKE_SCORE_TRENDS`` and ``SVTK_SCORE_TREND_COLUMNS`` are parsed
       by package code rather than notebook cells. Use ``render_gate()`` before
       figure blocks that depend on generated tables; it reports disabled
       figures and missing input paths without loading large tables.
       When ``figure_dir`` is omitted, this helper resolves and creates the
       active config's ``outputs.figures`` directory and uses
       ``outputs.figures/sidecars`` for row-provenance sidecars, so standard
       notebooks do not need a separate ``figure_dir = context.figures_dir``
       setup line. Pass ``figure_subdir="metrics"`` for large-run metric and
       spatial figure suites that should write under
       ``outputs.figures/metrics`` without hard-coding
       ``context.figures_dir / "metrics"`` in notebook cells.
       For large-run metric figures, use
       ``spatial_vtk.metrics.plot.prepare_large_run_metric_figure_context`` and
       gate plotting cells on ``metric_plot_context.ready`` rather than
       repeating metric-table existence and value-column checks in each cell.
   * - ``spatial_vtk.config.render_notebook_figure``
     - Call one plotting helper with a configured ``OutputGroup`` figure path,
       the relevant ``NotebookFigureSettings`` object, optional basemap
       settings, save/display/close behavior, and row-sidecar settings. Use it
       in standard notebooks instead of repeating ``outpath``, ``savefig``,
       ``showfig``, sidecar kwargs, and ``plt.close`` around every plot call.
   * - ``spatial_vtk.config.notebook_dashboard_launch_commands``
     - Return config-backed dashboard launch settings. Use
       ``metrics_launch_kwargs()`` and ``qc_launch_kwargs()`` with the package
       dashboard launch helpers; the shell-safe command strings are retained as
       a terminal fallback for long-lived dashboard sessions. The returned
       settings also parse ``SVTK_LAUNCH_METRICS_DASHBOARD`` and
       ``SVTK_LAUNCH_QC_DASHBOARD`` so notebooks do not repeat dashboard
       launch environment parsing in cells.

Standard Notebook Input Helpers
-------------------------------

Use these helpers when a standard tutorial notebook needs the prepared inputs
for a later step. They return named result objects with the configured
``OutputGroup`` objects and loaded tables that the step actually needs. This is
the preferred pattern for standard notebooks because path resolution,
fallbacks, and bounded previews stay in package code.

.. list-table::
   :header-rows: 1

   * - Step
     - Helper
     - What it owns
   * - Step 1 ingest
     - ``spatial_vtk.io.load_standard_ingest_workflow_outputs``
     - The Step 1 output group, preprocessing metadata output group, combined
       status frame, prepared station/event previews, and preprocessing
       manifest preview.
   * - Step 2 QC
     - ``spatial_vtk.qc.load_standard_qc_inputs``
     - Prepared stations, events, event-station records, the Step 1 output
       group, and the Step 2 QC output group.
   * - Step 3 metric calculation
     - ``spatial_vtk.metrics.load_standard_metric_workflow_outputs``
     - The Step 3 output group, preprocessed trace metadata dependency, status
       frame, optional metric task estimate, task-preview display helper,
       ``metrics_long`` display helper, and plotting-table loader.
   * - Step 4 spatial statistics
     - ``spatial_vtk.spatial.load_standard_spatial_workflow_outputs``
     - The Step 4 output group, loaded spatial workflow tables, per-metric
       product summaries, station-bias previews, and failure/status frames.
   * - Step 5 GeoJSON regions and corridors
     - ``spatial_vtk.spatial.plot.load_standard_geojson_plotting_inputs``
     - Prepared station/event/event-station metadata, metric tables, configured
       GeoJSON paths, Step 5 outputs, and compact plotting input summaries.
   * - Step 6 additional plotting
     - ``spatial_vtk.spatial.plot.load_standard_additional_plotting_inputs``
     - Metric snapshot rows, event metadata, event-station records,
       comparison-eligible records, and the Step 6 plotting output group.

These helpers should replace notebook-local blocks that create several
``output_group(...)`` objects, call ``load_tables(...)`` manually, or keep
fallback path choices in the cell. If a workflow step needs a new reusable
input bundle, add the bundle as a package helper first, then keep the notebook
cell focused on the analysis task.

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

Use ``spatial_vtk.io.record_coverage_readiness_from_config`` before the record
coverage build step when a notebook needs a readiness table. It uses the same
preprocessed-event-station fallback as ``build_record_coverage_from_config``,
so notebooks do not need to duplicate that path-selection logic.

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
     - ``spatial_vtk.metrics.metric_slurm_submission_readiness_from_config`` plus
       ``spatial_vtk.metrics.write_metrics_slurm_script_from_config``
     - metric Slurm script; optionally submitted job metadata
   * - Merge completed metric batches
     - ``spatial_vtk.metrics.metric_batch_merge_readiness_from_config`` plus
       ``spatial_vtk.metrics.merge_metric_batches_from_config``
     - ``metric_rows``
   * - Write downstream long, enriched, summary, and dashboard metric tables
     - ``spatial_vtk.metrics.metric_outputs_readiness_from_config`` plus
       ``spatial_vtk.metrics.write_metric_outputs_from_config``
     - ``metrics_long``, ``metrics_enriched``, path tables, dashboard metric
       datasets, dashboard summary tables
   * - Render many large-run metric figures with auditable row sidecars
     - ``spatial_vtk.metrics.plot.prepare_large_run_metric_figure_context``
     - saved metric figures, package-generated context status and dimension
       summary tables, and optional ``*.csv``/``*.source.csv``/``*.json``
       sidecars
   * - Select metric rows for focused notebook plots
     - ``spatial_vtk.metrics.plot.metric_rows_for_metrics``
     - bounded plotting inputs filtered by metric name, display label, key, or
       alias without notebook-local ``.loc[...isin(...)]`` filtering

Spectral metrics are planned differently from passband metrics. ``PSA`` and
``FAS`` are broadband spectral calculations: the metric manifest should contain
one blank-passband spectral task per event/station/component/model and output
one row per requested oscillator period in ``period_s``. Passband filters in
metric figure cells apply to passband-dependent metrics such as ``PGA``,
``PGV``, ``CAV``, durations, delays, and correlations. PSA figures should use
oscillator-period sheets, period curves, and ``period_s`` filters instead of
passband comparisons. If a legacy metric table repeats PSA rows under waveform
passbands such as ``1-2 sec`` or ``2-3 sec``, rebuild the metric manifest and
metric rows before using the current large-run plotting helpers.

Step 4: Spatial Statistics
--------------------------

.. list-table::
   :header-rows: 1

   * - Task
     - Python entry point
     - Standard outputs
   * - Build spatial-statistics summary tables
     - ``spatial_vtk.spatial.spatial_summary_readiness_from_config`` and
       ``spatial_vtk.spatial.run_spatial_statistics_workflow_from_config``
     - metric field, event-centered residuals, station bias, Moran's I,
       distance correlation, cluster, PCA, and geology tables
   * - Build optional derived spatial outputs
     - ``spatial_vtk.spatial.spatial_derived_outputs_readiness_from_config``
       and
       ``spatial_vtk.spatial.run_spatial_derived_outputs_workflow_from_config``
     - block holdout, REDCAP, and pattern-similarity tables
   * - Render standard spatial station and grid maps
     - ``spatial_vtk.spatial.plot.write_standard_spatial_map_figures``
     - per-metric station-bias and residual-grid figures, compact write status
       table, and optional row-provenance sidecars
   * - Render large-run spatial figures
     - ``spatial_vtk.spatial.plot.prepare_spatial_figure_context_from_notebook_settings``
     - saved spatial figures, package-generated spatial table/dimension status
       summaries, and optional row-provenance sidecars

Step 5: GeoJSON Regions and Corridors
-------------------------------------

.. list-table::
   :header-rows: 1

   * - Task
     - Python entry point
     - Standard outputs
   * - Summarize configured GeoJSON regions
     - ``spatial_vtk.spatial.geojson_region_summary_readiness_from_config``
       and
       ``spatial_vtk.spatial.run_geojson_region_summary_workflow_from_config``
     - GeoJSON region summary tables
   * - Build configured boundary corridors
     - ``spatial_vtk.spatial.boundary_corridor_readiness_from_config`` and
       ``spatial_vtk.spatial.run_boundary_corridor_workflow_from_config``
     - corridor definitions and corridor-selected records

Both Step 5 helpers can receive configured path keys for optional inputs. For
example, pass ``metrics_table="paths.metric_figure_snapshot"`` or
``geojson_path="paths.region_geojson"`` when a notebook needs to select a
configured non-default input without adding path-resolution cells.
Use ``spatial_vtk.spatial.geojson_matched_record_frame`` and
``spatial_vtk.spatial.event_station_records_matching_pairs`` for corridor
record filtering and event-station pair joins instead of notebook-local boolean
masks or dataframe merges.
Region boxplot cells should use
``spatial_vtk.spatial.plot.write_large_run_region_boxplot_from_notebook_settings``.
That wrapper owns the figure render gate, notebook figure settings, sidecar
options, and the ``metrics_enriched`` to ``metrics_long`` fallback. Use
``spatial_vtk.spatial.plot.write_large_run_region_boxplot_from_outputs`` from
scripts when explicit figure settings are already resolved.

Step 2 and Step 6 waveform-comparison cells should use
``spatial_vtk.visualize.waveforms.write_waveform_comparison_from_notebook_settings``.
That helper owns the figure render gate and notebook figure settings, then
reads only a bounded comparison-eligible sample, builds the plotted
observed/synthetic trace records, writes the configured
``event_trace_comparison`` figure, and returns a small status frame. For
scripts, use
``spatial_vtk.visualize.waveforms.write_waveform_comparison_from_outputs`` when
explicit plotting keyword arguments are already resolved.
Notebooks should not repeat the QC sample loading, figure-setting expansion,
and waveform-record construction pipeline inline.

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
     - compact tab-level readiness plus detailed status frames. Standard
       tutorial notebooks should prefer the preparation helper below so they do
       not repeat ``should_run`` branches inline; large-run
       notebooks pass the same readiness object to
       ``run_notebook_step_if_needed`` for Slurm/local execution.
   * - Preview dashboard outputs without loading full tab inputs
     - ``spatial_vtk.visualize.dashboard.display_dashboard_output_previews``
       and ``spatial_vtk.visualize.dashboard.preview_dashboard_summary_tables``
     - bounded samples from the configured ``dashboard_summaries`` directory
       and ``metrics_long`` table after readiness checks pass, so notebooks can
       inspect dashboard inputs without resolving paths or repeating preview
       conditionals in cells
   * - Write dashboard-ready row and summary datasets
     - ``spatial_vtk.visualize.dashboard.prepare_configured_dashboard_datasets_from_notebook_settings``
       and ``spatial_vtk.visualize.dashboard.write_configured_dashboard_datasets``
     - dashboard metric dataset root and dashboard summary table root; standard
       dashboard artifacts are replaced so stale partitions or stale
       CSV/Parquet summary files do not mix with the current run. The notebook
       preparation helper owns local-skip/current/rebuild decisions and returns
       readiness, status, and written-output frames for display.
   * - Launch dashboards from Python
     - ``spatial_vtk.config.notebook_dashboard_launch_commands``,
       ``spatial_vtk.visualize.dashboard.launch_configured_dashboards_from_notebook_settings``,
       ``spatial_vtk.visualize.dashboard.launch_configured_metrics_dashboard``,
       ``spatial_vtk.visualize.dashboard.launch_configured_qc_dashboard``,
       ``spatial_vtk.visualize.dashboard.launch_metrics_dashboard``, and
       ``spatial_vtk.visualize.dashboard.launch_qc_dashboard``
     - local Streamlit processes configured from the same output registry,
       optional terminal fallback commands, and a bounded
       launch-settings status frame plus launch-result status frame showing
       ports, process IDs, commands, launch errors, and configured dashboard
       inputs

Related API Pages
-----------------

The workflow helpers above are stable entry points. Use the module pages for
exact signatures, return contracts, and supporting public helpers:

- :doc:`api/config`
- :doc:`api/io`
- :doc:`api/qc`
- :doc:`api/metrics`
- :doc:`api/spatial`
- :doc:`api/visualize`
