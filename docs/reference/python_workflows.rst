Python Workflow Entry Points
============================

Use these helpers when a notebook or Python script needs to run a configured
Spatial-VTK workflow step. They resolve paths from the active config or from a
``config_path`` argument, write the standard output tables, and return compact
status payloads or result frames that are safe to display in notebooks.

For large datasets, keep notebook cells as lightweight drivers:

Notebooks should use package functions for workflow work; reserve CLI commands
for terminal-oriented workflows and generated batch scripts.

1. Build or load small metadata tables locally.
2. Load the standard result object for the current step, such as
   ``load_standard_ingest_workflow_outputs()``,
   ``load_standard_qc_workflow_outputs()``, or
   ``load_standard_metric_workflow_outputs()``.
3. Call that result object's ``run_*_step_if_needed()`` methods. Those methods
   own the readiness check plus the local/Slurm execution branch while the
   notebook cell keeps resource controls visible.
4. Use ``run_notebook_step_if_needed`` directly only for one-off custom
   orchestration outside the standard result-object methods.
5. Preview bounded tables after outputs exist; do not load full QC or metric
   inventories into the notebook just to check progress.

Workflow functions return JSON-ready status payloads, result objects, or
labelled frames that are safe to display in notebooks or write to Slurm logs.
New notebook code should prefer explicit
keys such as
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

Stable Import Surfaces
----------------------

Use these package namespaces as the public workflow import surface. If a
notebook needs a helper that is only available from an implementation module, add a
stable re-export first, then update the notebook to use the package-level
namespace.

.. list-table::
   :header-rows: 1

   * - Namespace
     - Use
   * - ``spatial_vtk.config``
     - Notebook run contexts, readiness-driven local/Slurm execution,
       configured figure settings, output-registry previews, dashboard launch
       settings, and shared figure rendering helpers.
   * - ``spatial_vtk.io``
     - Step 1 ingest workflow helpers, output groups, configured input-table
       loaders, preprocessing outputs, bounded table previews, event-label
       helpers, and table read/write helpers.
   * - ``spatial_vtk.qc``
     - Step 2 QC inventory builders, overlap inventory writers, compact QC
       summary builders, manual-review helpers, and standard QC input/output
       result objects.
   * - ``spatial_vtk.metrics``
     - Step 3 metric inventories, manifest planning, Slurm/batch readiness,
       batch execution/merge helpers, metric-output writers, and standard
       metric workflow result objects.
   * - ``spatial_vtk.metrics.plot``
     - Metric diagnostic plots, large-run metric figure suites, station metric
       maps, and metric figure result objects. Advanced row-selection helpers
       are documented in the Metrics API reference for custom scripts, but
       tutorials should use the result-object figure-suite methods instead.
   * - ``spatial_vtk.spatial``
     - Step 4 spatial-statistics workflows, Step 5 GeoJSON/corridor
       workflows, spatial readiness checks, configured spatial settings,
       region/corridor joins, and spatial product preview helpers.
   * - ``spatial_vtk.spatial.plot``
     - Spatial diagnostic plots, large-run spatial figure suites, GeoJSON and
       additional-plotting figure suites, and spatial figure result objects.
   * - ``spatial_vtk.spatial.map``
     - Geographic map helpers and basemap utilities.
   * - ``spatial_vtk.visualize``
     - Notebook-facing dashboard dataset preparation,
       dashboard readiness/status previews, dashboard launch helpers, figure
       sidecars, and standard context/QC/waveform visualization helpers.
       Focused dashboard scripts can import the same dashboard helpers from
       ``spatial_vtk.visualize.dashboard``.
   * - ``spatial_vtk.visualize.waveforms``
     - Waveform comparison helpers and waveform figure result objects.

Avoid importing tutorial workflow helpers from lower-level workflow, builder,
calculation, or plotting implementation modules in notebooks. Those modules
remain available for package internals and advanced scripts, but standard docs
and notebooks should depend on the stable namespaces above.

.. code-block:: python

   from spatial_vtk.config import configured_output_registry_preview_frame
   from spatial_vtk.config import (
       notebook_figure_settings,
       notebook_run_context,
   )
   from spatial_vtk.io import load_standard_ingest_workflow_outputs
   from spatial_vtk.metrics import load_standard_metric_workflow_outputs
   from spatial_vtk.qc import load_standard_qc_workflow_outputs

   context = notebook_run_context()
   cfg = context.cfg
   ingest_outputs = load_standard_ingest_workflow_outputs(cfg=cfg)
   qc_outputs = load_standard_qc_workflow_outputs(cfg=cfg)
   metric_outputs = load_standard_metric_workflow_outputs(cfg=cfg)
   display(context.status_frame())
   display(configured_output_registry_preview_frame(cfg=cfg, kinds=("table",)))
   display(ingest_outputs.status_frame())
   display(qc_outputs.status_frame())
   display(metric_outputs.status_frame())
   qc_outputs.run_inventory_step_if_needed(
       context,
       overwrite=False,
       verbose=True,
       script_name="build_qc_inventory.slurm",
       job_name="svtk-qc",
       walltime="24:00:00",
       memory="64G",
       cpus=1,
   )

   metric_figure_settings = notebook_figure_settings("metric", figure_subdir="metrics")
   # Pass metric_figure_settings to result-object figure methods instead of
   # parsing SVTK_FIGURE_* variables or constructing figure paths in cells.

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
       ``SVTK_DASHBOARD_CHUNKSIZE``, ``SVTK_METRIC_BATCH_COUNT``, and
       ``SVTK_PREPROCESS_CONTINUE_ON_ERROR`` so cells can pass
       ``context.<field>`` values into package workflow functions. Standard
       and large-run tutorial setup cells should display
       ``context.status_frame()`` to show the active config, output
       directories, run scenario, and execution flags with the same labelled
       path/status columns used by later workflow status tables.
   * - ``spatial_vtk.io.output_readiness``
     - Report whether configured outputs are missing, stale relative to inputs,
       blocked by missing inputs, or ready to reuse.
   * - ``spatial_vtk.io.output_group``
     - Resolve a named workflow output group once, then use attribute access,
       ``bind()``, ``status_frame()``, ``completion()``, and ``readiness()``
       instead of cluttering notebooks with repeated path plumbing.
       Prefer direct attributes when a cell needs a resolved path; standard
       result objects expose common paths directly, such as
       ``metric_outputs.metrics_long_path`` for Step 3 metric figures, while
       reusable output groups expose the same artifact-named paths, such as
       ``step_outputs.metrics_long_path``. ``bind()`` remains available for
       older notebooks but should not be the default pattern for new tutorial
       cells.
       ``readiness()`` can receive registered output, input, and source path
       names such as ``"metrics_long_path"`` and resolves them to configured
       paths before building the status table. Use ``preview_table()`` or
       ``display_table_previews()`` for bounded notebook previews, and reserve
       ``load_table()`` / ``load_tables()`` for package helpers or explicit
       analysis steps that genuinely need full in-memory tables. Pass
       ``missing="skip"`` when a figure can use an optional output if present
       but should continue without it.
       Standard public result-object names such as
       ``event_station_records_path`` are accepted where older output groups
       still expose the legacy ``event_station_path`` name, so scripts can use
       the clearer public spelling while older notebooks continue to run.
       These aliases work consistently for direct access, ``bind()``, table
       preview/loading helpers, ``first_existing_path()``, and
       ``readiness()`` output/input/source checks.
       Output-group helpers accept ``cfg=`` as either a config object or a
       config file path, so generated workers and scripts can resolve the same
       paths as notebooks without relying on active global config.
       Legacy helpers such as ``output_group_namespace()`` return only path
       attributes. New workflow notebooks should prefer the standard
       ``load_standard_*`` helpers listed below; use ``output_group()`` directly
       only when a new reusable standard helper does not exist yet, so
       readiness, previews, completion checks, and figure-path helpers stay
       attached to the same object.
       For output groups that own table paths outside the configured output
       registry, such as preprocessing metadata, use ``load_path_table()`` or
       ``preview_path_table()`` with the group path name for one table, or
       ``display_path_table_previews()`` for display-label mappings and bounded
       notebook previews. This keeps path-backed artifacts on the shared
       bounded-preview path instead of ad hoc table reads in notebook cells.
       Use ``figure_path()`` for figure artifacts that need configured
       directories but metric-specific filenames; pass ``stem_parts`` instead
       of constructing ``figure_dir / "name.png"`` in notebook cells.
       When a required input comes from an optional config value, pass the
       named mapping value as ``None``. The readiness/status table displays
       ``<not configured>`` and blocks the step cleanly instead of using a
       manufactured fallback path.
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
       labeled mapping. Use this for tutorial figure inputs and optional
       spatial metadata instead of repeating direct ``read_config_table`` calls
       in notebook cells.
   * - ``spatial_vtk.io.load_configured_input_paths``
     - Resolve non-table configured inputs such as ``"paths.region_geojson"``
       into a labeled path mapping. Use this when plotting or spatial helper
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
   * - ``spatial_vtk.io.metric_plan_from_config`` and
       ``spatial_vtk.io.MetricPlan``
     - Resolve metric calculation settings from a config, run scenario, and
       optional overrides. Display ``MetricPlan.summary_frame()`` in notebooks
       when checking the active metrics, passbands, components, models,
       spectral periods, overlap settings, and metric output path.
   * - ``spatial_vtk.config.run_notebook_step_if_needed``
     - Advanced helper for one-off custom workflow steps outside the standard
       result-object ``run_*_step_if_needed()`` methods. Prefer the standard
       result object for tutorial workflows; use this helper when a custom
       script still needs the same readiness table plus local/Slurm execution
       branch. Pass the imported package function directly; fully qualified
       import-path strings are retained only for compatibility and generated
       Slurm workers.
   * - ``spatial_vtk.config.notebook_step_result``
     - Return a compact JSON-friendly status payload for current/skipped
       notebook workflow steps. Standard result objects call this internally
       for skipped ``run_*_step_if_needed()`` payloads; custom workflow cells
       can call it directly when they already own the readiness object and
       fallback values. Use it instead of writing inline dictionaries that
       repeat ``str(path)`` conversion, ``reused`` flags, or generic ``path``
       keys in notebook cells.
   * - ``spatial_vtk.config.display_notebook_step_result``
     - Display current/skipped step payloads, Slurm submissions, and
       result objects with ``status_frame()`` or ``summary_frame()`` as compact
       labelled tables. Use this in workflow cells instead of
       ``print(result)`` or ``print(result.summary_message())`` when a
       package helper returns a displayable workflow result.
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
       JSON files. Before any JSON metadata exists, it reports disabled,
       not-configured, missing-directory, and empty-directory states as an
       explanatory notebook row; after figures are written, it shows which
       figures were written, whether row sidecars are exact or sampled, and
       which aggregated figures include source-row provenance.
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
       For large-run metric figures, call
       ``spatial_vtk.metrics.load_standard_metric_workflow_outputs(...).write_large_run_figure_suite(...)``
       with ``notebook_figure_settings("metric", figure_subdir="metrics")``.
       The result object owns the notebook-facing render path and delegates the
       figure render gate, metric-table readiness checks, value-column checks,
       settings resolution, and sidecar options to package code, so notebook
       cells do not repeat metric-table existence checks or build figure
       contexts by hand.
       For large-run spatial figures, call
       ``spatial_vtk.spatial.load_standard_spatial_workflow_output_status(...).write_figure_suite(...)``
       with ``notebook_figure_settings("spatial", figure_subdir="metrics")``.
       The result object owns the notebook-facing render path and delegates
       table readiness checks, figure settings, configured output paths, and
       row-provenance sidecars to package code, so notebooks do not build
       spatial figure contexts or per-plot paths by hand.
   * - ``spatial_vtk.config.render_notebook_figure``
     - Building block for custom package helpers or focused scripts that need
       to call one plotting helper with a configured ``OutputGroup`` figure
       path, the relevant ``NotebookFigureSettings`` object, optional basemap
       settings, save/display/close behavior, and row-sidecar settings.
       Standard tutorial notebooks should prefer workflow result-object figure
       methods, which call these lower-level render helpers internally.
   * - ``spatial_vtk.config.notebook_dashboard_launch_commands``
     - Return config-backed dashboard launch settings. Use
       ``metrics_launch_kwargs()`` and ``qc_launch_kwargs()`` with the package
       dashboard launch helpers; the shell-safe command strings are retained as
       a terminal fallback for long-lived dashboard sessions. The returned
       settings also parse ``SVTK_LAUNCH_METRICS_DASHBOARD`` and
       ``SVTK_LAUNCH_QC_DASHBOARD`` so notebooks do not repeat dashboard
       launch environment parsing in cells. ``status_frame()`` also reports
       whether configured dashboard input paths exist.

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
       manifest preview, plus standard context figure rendering through
       ``write_context_figures()``.
   * - Step 2 QC
     - ``spatial_vtk.qc.load_standard_qc_inputs``
     - Prepared stations, events, event-station records, the Step 1 output
       group, the Step 2 QC output group, named skipped-step fallback payloads
       for full QC, overlap QC, and compact QC summaries,
       compact output summaries, bounded QC inventory/summary previews, and
       standard QC and waveform-comparison rendering through
       ``write_figures()`` and ``write_waveform_comparison()``.
   * - Step 2 large-run QC setup
     - ``spatial_vtk.qc.load_standard_qc_workflow_outputs``
     - The Step 2 QC output group and status frame without eager reads of the
       prepared station/event/event-station tables, plus compact QC summary
       previews, figure rendering through ``write_figures()``, and large-run
       full-QC, overlap-sidecar, and summary runner methods.
   * - Step 3 metric calculation
     - ``spatial_vtk.metrics.load_standard_metric_workflow_outputs``
     - The Step 3 output group, preprocessed trace metadata dependency, status
       frame, optional metric task estimate, task-preview display helper,
       ``metrics_long`` display helper, plotting-table loader, configured
       downstream output writer, large-run inventory/manifest/Slurm/merge
       step runners, standard diagnostic figure writer, focused station-map
       writer, large-run figure-suite writer, and task-estimate reload helper.
       The task estimate separates passband-dependent tasks from broadband
       spectral tasks and reports spectral periods so users can confirm PSA/FAS
       work is planned once per event/station/component/model, not once per
       waveform passband.
   * - Step 4 spatial statistics
     - ``spatial_vtk.spatial.load_standard_spatial_workflow_output_status``
       and ``spatial_vtk.spatial.load_standard_spatial_workflow_outputs``
     - Lightweight Step 4 output status/previews for large-run driver cells,
       result-owned spatial summary and derived-output runners through
       ``run_summary_step_if_needed()`` and
       ``run_derived_outputs_step_if_needed()``, quick summary-figure writing
       through ``write_summary_figures()``, plus loaded spatial workflow
       tables, per-metric product summaries, station-bias previews, standard
       map/diagnostic figure methods, and failure/status frames when the
       standard tutorial needs in-memory products.
   * - Step 5 GeoJSON regions and corridors
     - ``spatial_vtk.spatial.load_standard_geojson_workflow_output_status``
       and ``spatial_vtk.spatial.load_standard_geojson_plotting_inputs``
     - Lightweight Step 5 output status/previews for large-run driver cells,
       result-owned GeoJSON and corridor runners through
       ``run_geojson_summary_step_if_needed()`` and
       ``run_corridor_step_if_needed()``, large-run region/corridor figure
       writing through ``write_region_figures()``, plus prepared
       station/event/event-station metadata, metric tables, configured
       GeoJSON paths, Step 5 outputs, compact plotting input summaries, and
       result methods that write the standard region and corridor figure
       suites without notebook-local path unpacking. Both helpers accept
       ``cfg=`` as a config object or config file path.
   * - Step 6 additional plotting
     - ``spatial_vtk.spatial.load_standard_additional_plotting_output_status``
       and ``spatial_vtk.spatial.load_standard_additional_plotting_inputs``
     - Lightweight Step 6 output status and metric-source preview helpers for
       large-run driver cells, bounded waveform and region-boxplot writers
       through ``write_waveform_comparison()`` and ``write_region_boxplot()``,
       plus metric snapshot rows, event metadata,
       event-station records, comparison-eligible records, and the Step 6
       plotting output group when figures need loaded inputs; the loaded input
       result writes the standard Step 6 figure suite without notebook-local
       table or output-group aliases. Both helpers accept ``cfg=`` as a
       config object or config file path.

These helpers should replace notebook-local blocks that create several
``output_group(...)`` objects, call table loaders manually, or keep fallback
path choices in the cell. If a workflow step needs a new reusable input bundle,
add the bundle as a package helper first, then keep the notebook cell focused
on the analysis task.

The same rule applies to status and preview cells. Standard notebook result
objects expose bounded display helpers such as ``display_summary_previews()``,
``display_metrics_preview()``, ``display_metric_source_preview()``, and
``display_output_previews()``. Notebook cells should call those methods instead
of passing ``cfg`` into standalone preview helpers, because the result object
already owns the configured paths, missing-output policy, and display fallback.

Step 1: Metadata, Waveforms, and Record Coverage
------------------------------------------------

.. list-table::
   :header-rows: 1

   * - Task
     - Python entry point
     - Standard outputs
   * - Prepare stations, events, and event-station rows
     - ``spatial_vtk.io.load_standard_ingest_workflow_outputs(...).run_metadata_step_if_needed(...)``
     - ``prepared_stations``, ``prepared_events``,
       ``event_station_records``; returns ``MetadataPreparationResult`` with
       notebook summary helpers
   * - Check prepared metadata readiness
     - ``spatial_vtk.io.metadata_tables_readiness_from_config``
     - Readiness/status for ``prepared_stations``, ``prepared_events``, and
       ``event_station_records`` without loading large prepared tables
   * - Preprocess observed/synthetic waveforms
     - ``spatial_vtk.io.load_standard_ingest_workflow_outputs(...).run_preprocessing_step_if_needed(...)``
     - preprocessed waveform files, preprocessing manifest,
       trace metadata, preprocessed event-station records; returns
       ``WaveformPreprocessingSummaryResult``
   * - Check preprocessing readiness
     - ``spatial_vtk.io.preprocessing_readiness_from_config``
     - Readiness/status for preprocessing metadata and its
       ``event_station_records`` dependency without repeating path names
   * - Build record coverage from trace metadata
     - ``spatial_vtk.io.load_standard_ingest_workflow_outputs(...).run_record_coverage_step_if_needed(...)``
     - ``record_coverage``; returns ``RecordCoverageWorkflowResult`` with the
       exact trace metadata and event-station inputs used

The ``run_*_step_if_needed`` methods wrap
``spatial_vtk.config.run_notebook_step_if_needed`` with the correct readiness
helper and build function for each Step 1 stage. Use the direct
``metadata_tables_readiness_from_config``,
``preprocessing_readiness_from_config``,
``record_coverage_readiness_from_config``,
``prepare_metadata_tables_from_config``, ``preprocess_waveforms_from_config``,
and ``build_record_coverage_from_config`` functions in tests, scripts, or
custom orchestration that needs that extra control. Tutorial notebooks should
prefer the result-object methods so they do not duplicate path-selection logic.
Step 1 status and summary frames include ``status_reason`` alongside
``status`` so notebooks can filter ready and missing output artifacts without
parsing display messages.

Step 2: Quality Control
-----------------------

.. list-table::
   :header-rows: 1

   * - Task
     - Python entry point
     - Standard outputs
   * - Build full waveform and metric QC inventories
     - ``spatial_vtk.qc.load_standard_qc_workflow_outputs(...).run_inventory_step_if_needed(...)``
     - ``qc_trace_summary`` and ``qc_inventory``
   * - Write the observed/synthetic event-station overlap inventory
     - ``spatial_vtk.qc.load_standard_qc_workflow_outputs(...).run_overlap_step_if_needed(...)``
     - ``qc_inventory_overlap``
   * - Build compact QC summary tables for figures and dashboards
     - ``spatial_vtk.qc.load_standard_qc_workflow_outputs(...).run_summary_step_if_needed(...)``
     - retention, availability, post-QC record, and drop-cause tables

The full QC inventory can be useful for observed-only or synthetic-only
analysis, but metric calculations should normally use the overlap inventory so
they only plan observed/synthetic pairs that can be compared.

Use
``spatial_vtk.qc.load_standard_qc_workflow_outputs(...).checkpoint_status_frame()``
to inspect QC resume progress before rerunning a large job. That frame reports
the combined waveform QC table, source-specific waveform checkpoints, and the
metric QC inventory checkpoint with row counts and completed key counts while
streaming only identifier columns from CSV checkpoints. It also includes
``status_reason`` so driver notebooks can filter ready, missing, and
unconfigured checkpoints without parsing messages.

The direct ``spatial_vtk.qc.run_qc_inventory_from_config``,
``spatial_vtk.qc.write_qc_inventory_overlap_from_config``, and
``spatial_vtk.qc.run_qc_summary_workflow_from_config`` functions remain public
for scripts or custom orchestration that needs direct control.

Step 3: Metric Calculation and Metric Figures
---------------------------------------------

.. list-table::
   :header-rows: 1

   * - Task
     - Python entry point
     - Standard outputs
   * - Build metric-ready observed/synthetic waveform inventories
     - ``spatial_vtk.metrics.load_standard_metric_workflow_outputs(...).run_inventory_step_if_needed(...)``
     - ``observed_metric_inventory`` and ``synthetic_metric_inventory``
   * - Check metric inventory readiness
     - ``spatial_vtk.metrics.metric_inventories_readiness_from_config``
     - Readiness/status for observed and synthetic metric inventories and the
       preprocessed trace-metadata dependency
   * - Plan metric tasks and write a manifest
     - ``spatial_vtk.metrics.load_standard_metric_workflow_outputs(...).run_manifest_step_if_needed(...)``
     - ``metric_manifest`` plus per-batch output paths
   * - Check metric manifest readiness
     - ``spatial_vtk.metrics.metric_manifest_readiness_from_config``
     - Readiness/status for the metric manifest, metric inventories, and
       observed/synthetic overlap QC inventory
   * - Preview task counts from a configured metric snapshot
     - ``spatial_vtk.metrics.summarize_metric_snapshot_tasks_from_config``
     - ``metric_tasks`` and ``metric_task_estimate``
   * - Write or submit a metric Slurm array script
     - ``spatial_vtk.metrics.load_standard_metric_workflow_outputs(...).run_slurm_step_if_needed(...)``
     - metric Slurm script; optionally submitted job metadata
   * - Merge completed metric batches
     - ``spatial_vtk.metrics.load_standard_metric_workflow_outputs(...).run_merge_step_if_needed(...)``
     - ``metric_rows``
   * - Write downstream long, enriched, summary, and dashboard metric tables
     - ``spatial_vtk.metrics.load_standard_metric_workflow_outputs(...).run_downstream_outputs_step_if_needed(...)``
     - ``metrics_long``, ``metrics_enriched``, path tables, dashboard metric
       datasets, dashboard summary tables
   * - Render many large-run metric figures with auditable row sidecars
     - ``spatial_vtk.metrics.load_standard_metric_workflow_outputs(...).write_large_run_figure_suite(...)``
     - saved metric figures, package-generated context status and dimension
       summary tables, target-metric selection status, spectral-contract
       status, and optional ``*.csv``/``*.source.csv``/``*.json`` sidecars.
       The context status table uses labelled ``artifact_role``, ``status``,
       ``resolved_path``, ``path``, and ``exists`` columns so notebooks can
       show metric-table readiness, render gates, selected-value checks, and
       sidecar settings without notebook-local row filtering,
       figure-context construction, or per-plot path plumbing

Use direct metric helpers such as
``spatial_vtk.metrics.build_metric_waveform_inventories_from_config``,
``spatial_vtk.metrics.plan_metric_tasks_from_config``,
``spatial_vtk.metrics.write_metrics_slurm_script_from_config``,
``spatial_vtk.metrics.merge_metric_batches_from_config``,
``spatial_vtk.metrics.write_metric_outputs_from_config``, and
``write_large_run_metric_figure_suite_from_notebook_settings`` imported from
``spatial_vtk.metrics.plot`` from scripts or custom orchestration that needs
direct control. Tutorial notebooks should prefer the standard metric
result-object methods above. If a script calls the direct
``spatial_vtk.metrics.write_metric_outputs``
writer directly, pass ``cfg=cfg`` or ``cfg=config_path`` when writing to
registered output paths; this keeps the script independent of global
active-config state. The standard metric result object also accepts either
form, so ``load_standard_metric_workflow_outputs(cfg=config_path)`` resolves
the Step 3 tables and preprocessing trace metadata from the same config.
Passing an explicit ``output_dir`` remains available for custom exports outside
the configured output registry.

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

Standard Step 4 helpers accept ``cfg=`` as either a config object or a config
file path. Use ``cfg=config_path`` in generated workers and lightweight driver
scripts when you want the spatial output bundle, readiness gates, and settings
to resolve from one config file without activating global state first.
Put non-default Step 4 inputs in the config under ``spatial.metrics_table`` and
``spatial.station_metadata_table``. Those settings can point to dotted path keys
such as ``paths.metric_figure_snapshot`` and ``paths.site_metadata``, which
keeps notebooks from passing one-off table paths into workflow calls. Set
``spatial.metric`` to ``all``, one metric name, or a metric list when a run
should build only a curated subset.

.. list-table::
   :header-rows: 1

   * - Task
     - Python entry point
     - Standard outputs
   * - Build spatial-statistics summary tables
     - ``spatial_vtk.spatial.load_standard_spatial_workflow_output_status(...).run_summary_step_if_needed(...)``
     - metric field, event-centered residuals, station bias, Moran's I,
       distance correlation, cluster, PCA, and geology tables
   * - Build optional derived spatial outputs
     - ``spatial_vtk.spatial.load_standard_spatial_workflow_output_status(...).run_derived_outputs_step_if_needed(...)``
     - block holdout, REDCAP, and pattern-similarity tables
   * - Render standard spatial station and grid maps
     - ``spatial_vtk.spatial.load_standard_spatial_workflow_outputs(...).write_map_figures(...)``
     - per-metric station-bias and residual-grid figures, compact write status
       table, and optional row-provenance sidecars
   * - Render large-run spatial figures
     - ``spatial_vtk.spatial.load_standard_spatial_workflow_output_status(...).write_figure_suite(...)``
     - saved spatial figures, package-generated spatial table/dimension status
       summaries, compact diagnostic preview tables for statistics used by
       the figures, and optional row-provenance sidecars

The large-run Step 4 figure suite returns a result object, not just paths.
Use ``spatial_figure_suite.display_context_status(display=display)`` to show
the loaded-table, dimension, and spectral-contract audit frames, display
``spatial_figure_suite.diagnostic_preview_frame(nrows=...)`` under the figure
cell to keep Moran, distance-correlation, clustering, PCA, and geology
diagnostic rows visible, and display ``spatial_figure_suite.status_frame()``
for the figure/sidecar write status. This mirrors the smaller tutorial's
"figure plus table" layout while avoiding notebook-local table joins or full
metric-table reads.

Display results returned by the Step 4 ``run_*_step_if_needed(...)`` methods
with ``spatial_vtk.config.display_notebook_step_result``. That keeps submitted,
skipped, and local-run states visible as labelled notebook tables instead of
raw dictionaries or Slurm dataclass output.

Step 5: GeoJSON Regions and Corridors
-------------------------------------

.. list-table::
   :header-rows: 1

   * - Task
     - Python entry point
     - Standard outputs
   * - Summarize configured GeoJSON regions
     - ``spatial_vtk.spatial.load_standard_geojson_workflow_output_status(...).run_geojson_summary_step_if_needed(...)``
     - GeoJSON region summary tables
   * - Build configured boundary corridors
     - ``spatial_vtk.spatial.load_standard_geojson_workflow_output_status(...).run_corridor_step_if_needed(...)``
     - corridor definitions and corridor-selected records

Step 5 notebooks should keep heavy gates on the lightweight output-status
result and keep loaded plotting inputs on the plotting-input result. Use
``load_standard_geojson_workflow_output_status(...).run_geojson_summary_step_if_needed(...)``
and ``run_corridor_step_if_needed(...)`` for the region-summary and corridor
tables, then use ``load_standard_geojson_plotting_inputs(...).write_region_figures(...)``
and ``write_corridor_figures(...)`` for the standard figure suites. These
result methods own the configured output bundle, skip/rebuild decisions,
bounded previews, and figure paths, so notebook cells do not need to pass
resolved table paths around.
The output-status result imports remain lightweight: Matplotlib-backed figure
helpers and Shapely-backed GeoJSON annotation helpers are loaded only when a
figure or annotation step is actually requested.

Direct configured workflow functions can still receive configured path keys
for optional inputs in scripts or custom orchestration. For example, pass
``metrics_table="paths.metric_figure_snapshot"`` or
``geojson_path="paths.region_geojson"`` when a script needs to select a
configured non-default input without activating global config state first.
Use ``spatial_vtk.spatial.geojson_matched_record_frame`` and
``spatial_vtk.spatial.event_station_records_matching_pairs`` for corridor
record filtering and event-station pair joins instead of notebook-local boolean
masks or dataframe merges.
Region boxplot cells should use
``spatial_vtk.spatial.load_standard_additional_plotting_output_status(...).write_region_boxplot(...)``.
The result object owns the figure render gate, notebook figure settings,
sidecar options, and the ``metrics_enriched`` to ``metrics_long`` fallback.
Use ``write_large_run_region_boxplot_from_notebook_settings`` or
``write_large_run_region_boxplot_from_outputs`` imported from
``spatial_vtk.spatial.plot`` from scripts when explicit figure settings or
output bundles are already resolved.

Step 2 and Step 6 waveform-comparison cells should use
``spatial_vtk.qc.load_standard_qc_inputs(...).write_waveform_comparison(...)``
or
``spatial_vtk.spatial.load_standard_additional_plotting_inputs(...).write_waveform_comparison(...)``.
Those result methods own the figure render gate and notebook figure settings,
then read only a bounded comparison-eligible sample, build the plotted
observed/synthetic trace records, write the configured
``event_trace_comparison`` figure, and return a small status frame with the
figure row plus event-station and comparison-eligible input-table rows. For
scripts, use ``write_waveform_comparison_from_notebook_settings`` or
``write_waveform_comparison_from_outputs`` imported from
``spatial_vtk.visualize`` when notebook settings should still control rendering
or explicit plotting keyword arguments are already resolved.
Notebooks should not repeat the QC sample loading, figure-setting expansion,
and waveform-record construction pipeline inline.

Step 7: Dashboard Datasets
--------------------------

Dashboard readiness, status, and preview helpers accept ``cfg=`` as either a
config object or a config file path. This keeps Step 7 notebook cells and
worker scripts on the same configured dashboard dataset and summary-table
paths without requiring global config activation.

.. list-table::
   :header-rows: 1

   * - Task
     - Python entry point
     - Standard outputs
   * - Check dashboard dataset readiness without loading full inventories
     - ``spatial_vtk.visualize.dashboard_readiness_summary_frame``,
       ``spatial_vtk.visualize.dashboard_output_status_frame``, and
       ``spatial_vtk.visualize.dashboard_output_readiness``
     - compact tab-level readiness plus detailed status frames. Standard
       tutorial notebooks should prefer the preparation helper below so they do
       not repeat ``should_run`` branches inline; large-run
       notebooks call ``DashboardDatasetPreparationResult.run_if_needed()`` so
       the result owns the Slurm/local execution branch.
   * - Preview dashboard outputs without loading full tab inputs
     - ``DashboardDatasetPreparationResult.display_output_previews()``,
       ``spatial_vtk.visualize.display_dashboard_output_previews``, and
       ``spatial_vtk.visualize.preview_dashboard_summary_tables``
     - bounded samples from the configured ``dashboard_summaries`` directory
       and ``metrics_long`` table after readiness checks pass, so notebooks can
       inspect dashboard inputs without resolving paths or repeating preview
       conditionals in cells
   * - Write dashboard-ready row and summary datasets
     - ``spatial_vtk.visualize.prepare_configured_dashboard_datasets_from_notebook_settings``
     - configured ``metrics_dashboard`` row dataset directory and
       ``dashboard_summaries`` summary-table directory; standard dashboard
       artifacts are replaced so stale partitions or stale CSV or Parquet
       summary files do not mix with the current run. The notebook preparation
       helper owns local-skip/current/rebuild decisions and returns readiness,
       status, and written-output frames for display. The returned
       ``DashboardDatasetPreparationResult`` also owns the Slurm-aware
       ``run_if_needed(...)`` call used by large-run notebooks, including the
       configured writer function, serializable config path, and standard
       dashboard resource defaults. Partitioned path-backed metric inputs are
       streamed in ``SVTK_DASHBOARD_CHUNKSIZE`` row batches so large-run
       dashboard preparation does not have to materialize the full
       ``metrics_long`` table before writing dashboard partitions. Summary
       tables are then built one dashboard partition at a time so exact
       medians, IQRs, and unique counts do not require loading the full
       dashboard metric dataset. Dashboard startup/readiness checks inspect
       summary value and map-coordinate columns with projected chunk scans, so
       they can report schema/value/map readiness without materializing complete
       summary tables. ``ready`` reports whether the underlying summary data is
       usable, while ``tab_ready`` reports whether the dashboard tab can render
       correctly after map-coordinate requirements are considered. Startup
       warnings use ``tab_ready`` so value-ready but map-blocked station/event
       tabs are reported clearly, while optional summary-table loading skips
       only tables whose underlying data ``ready`` value is false. This lets a
       map-blocked station or event tab still show its filtered table and Data
       Status rows. Display the result from
       ``DashboardDatasetPreparationResult.run_if_needed(...)`` with
       ``spatial_vtk.config.display_notebook_step_result`` so submitted,
       skipped, and local-run states appear as labelled notebook tables.
       Scripts that intentionally own dashboard preparation control can call
       ``spatial_vtk.visualize.write_configured_dashboard_datasets`` directly
       with ``cfg=`` or explicit output directories. The
       metrics dashboard loads the primary
       ``model_metric_band`` summary at startup, then reads optional
       station/event/path summaries lazily in chunks after the active
       model/metric/passband/period/component filters are known. It caps
       summary-table dataframe displays through
       ``SVTK_METRICS_DASHBOARD_SUMMARY_DISPLAY_ROWS`` or the shared
       ``SVTK_DASHBOARD_DISPLAY_ROWS`` setting, and caps row-level CSV
       downloads separately through
       ``SVTK_METRICS_DASHBOARD_DOWNLOAD_ROWS`` or the shared
       ``SVTK_DASHBOARD_DOWNLOAD_ROWS`` setting so dashboard tabs and downloads
       do not serialize more rows than intended.
   * - Launch dashboards from Python
     - ``spatial_vtk.config.notebook_dashboard_launch_commands``,
       and ``spatial_vtk.visualize.launch_configured_dashboards_from_notebook_settings``
     - local Streamlit processes configured from the same output registry,
       optional terminal fallback commands, and a bounded
       launch-settings status frame plus launch-result status frame showing
       ports, process IDs, commands, launch errors, and configured dashboard
       inputs. Scripts that intentionally launch one dashboard can call
       ``spatial_vtk.visualize.launch_configured_metrics_dashboard``,
       ``spatial_vtk.visualize.launch_configured_qc_dashboard``,
       ``spatial_vtk.visualize.launch_metrics_dashboard``, or
       ``spatial_vtk.visualize.launch_qc_dashboard`` directly when they own
       the launch target and explicit options.

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
