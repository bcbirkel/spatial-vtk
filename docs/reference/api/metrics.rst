Metrics API
===========

Metrics modules calculate observed and synthetic waveform values, transform
those values into residuals and scores, plan file-based metric runs, and plot
metric diagnostics.

.. contents:: On this page
   :local:
   :depth: 2

Package Entry Point
-------------------

Start with ``spatial_vtk.metrics`` for metric workflow helpers and calculation
utilities that are used by notebooks, scripts, and generated Slurm workers.
These imports keep large-run planning, waveform inventory creation, metric
batch execution, merge steps, dashboard exports, and metric-output writes on one
stable package surface.

.. code-block:: python

   from spatial_vtk.metrics import (
       load_standard_metric_workflow_outputs,
   )

Direct config-backed metric helpers remain public for scripts, generated
workers, and custom orchestration that already owns execution control:

.. code-block:: python

   from spatial_vtk.metrics import (
       MetricWorkflowTask,
       build_metric_waveform_inventories_from_config,
       cache_metric_manifest_waveforms,
       merge_batch_outputs,
       merge_metric_batches_from_config,
       metric_manifest_batch_status,
       metric_batch_merge_readiness_from_config,
       metric_inventories_readiness_from_config,
       metric_manifest_readiness_from_config,
       metric_slurm_submission_readiness,
       metric_slurm_submission_readiness_from_config,
       metric_workflow_output_input_columns,
       plan_metric_tasks_from_config,
       read_task_manifest,
       run_manifest_batch,
       submit_metrics_slurm_job,
       write_metric_outputs_from_config,
       write_metrics_slurm_script_from_config,
   )

.. automodule:: spatial_vtk.metrics
   :members:

Calculate
---------

Use ``spatial_vtk.metrics.calculate`` for metric calculation utilities,
waveform transforms, residual transforms, band helpers, and optional arrival
pick adapters. The lower-level calculation modules are implementation
organization. Routine notebooks should start from ``spatial_vtk.metrics``
workflow helpers and the Step 3 result-object methods above. Scripts and
custom extensions that intentionally work at calculation level can import
calculation helpers from ``spatial_vtk.metrics`` or
``spatial_vtk.metrics.calculate``.

.. automodule:: spatial_vtk.metrics.calculate
   :members:

Workflow
--------

Notebook and CLI workflows should import metric planning, execution, summary,
and output helpers from the stable ``spatial_vtk.metrics`` package entry
point. ``spatial_vtk.metrics.workflow`` remains a public module for advanced
workflow scripts, while lower-level workflow modules are implementation
organization.

Public workflow helpers exposed by ``spatial_vtk.metrics``:

.. list-table::
   :header-rows: 1

   * - Helper
     - Use
   * - ``load_standard_metric_workflow_outputs``
     - Load configured Step 3 output handles, the preprocessed trace metadata
       dependency, a status frame, and bounded preview helpers such as the
       ``metrics_long`` display helper ``display_metrics_preview()`` for
       standard metric notebooks. The returned result also owns task-estimate
       loading through ``with_task_estimate()``, configured downstream output
       writing through ``write_configured_outputs()``, standard diagnostic
       figure rendering through ``write_standard_diagnostic_figures()``,
       focused station-map rendering through ``write_station_metric_map()``,
       large-run Step 3 execution gates through the
       ``run_*_step_if_needed()`` methods, and large-run metric figure-suite
       rendering through ``write_large_run_figure_suite()``. Pass ``cfg=`` as
       either a config object or a config file path; the result resolves
       Step 3 outputs and preprocessing trace metadata from the same config.
       Display ``StandardMetricWorkflowOutputResult.status_frame()`` for
       configured output readiness and use its preview/figure methods instead
       of repeating manifest, metric-row, or output-table path plumbing in
       notebook cells.
   * - ``build_metric_waveform_inventories_from_config``
     - Build observed and synthetic metric-ready waveform inventories from the
       active config and preprocessed waveform metadata. The returned
       ``MetricWaveformInventoryResult.status_frame()`` reports observed and
       synthetic inventory artifacts with normalized names, roles, readiness
       status, paths, row counts, and reuse flags.
   * - ``metric_inventories_readiness_from_config``
     - Check whether metric-ready observed/synthetic waveform inventories are
       missing, stale, current, or forced by ``overwrite`` without repeating the
       preprocessed trace-metadata dependency in notebooks.
   * - ``plan_metric_tasks_from_config``
     - Plan metric tasks from configured inventories, the
       ``qc_inventory_overlap`` table, and metric settings. By default, paired
       observed/synthetic metric tasks are restricted to event-station records
       with at least one passing observed/synthetic QC pair, so the manifest
       avoids events or stations that cannot contribute comparison metrics. When
       writing a manifest, the returned payload includes task count, batch count,
       per-batch task range, batch output directory, first/last batch output
       paths, and planning-policy metadata for notebook display.
   * - ``metric_manifest_readiness_from_config``
     - Check whether configured metric inventories and the overlap QC table are
       ready before planning the metric manifest.
   * - ``cache_metric_manifest_waveforms``
     - Materialize metric-ready waveform cache files for repeated large-run
       batch execution. The returned ``MetricWaveformCacheResult`` exposes
       ``status_frame()`` with ``name``, ``artifact``, ``artifact_label``,
       ``artifact_role``, ``status``, ``resolved_path``, ``exists``, row
       counts, and cache reuse counts for notebook display.
   * - ``metric_slurm_submission_readiness_from_config``
     - Check whether a metric Slurm array should be submitted or skipped.
   * - ``write_metrics_slurm_script_from_config``
     - Write a config-backed metric Slurm array script without notebook-local
       path plumbing.
   * - ``read_task_manifest`` and ``run_manifest_batch``
     - Load a manifest and execute one planned batch from Python or a generated
       worker script. ``MetricWorkflowManifest.status_frame()`` reports
       ``name``, ``artifact``, ``artifact_label``, ``artifact_role``,
       ``status``, ``resolved_path``, ``exists``, task count, batch count,
       batch output directory, per-batch task range, first/last batch outputs,
       and QC table without loading waveform files. Legacy ``manifest_path``
       and ``manifest_exists`` aliases remain present.
   * - ``metric_manifest_batch_status`` and
       ``metric_batch_merge_readiness_from_config``
     - Report which metric batches are complete before merging outputs.
       Batch status frames expose the same artifact columns plus completion
       counts, percent complete, and ``complete``/``incomplete`` status.
   * - ``merge_batch_outputs`` and ``merge_metric_batches_from_config``
     - Merge completed metric batch files into the registered metric-row table.
   * - ``write_metric_outputs_from_config``
     - Write downstream long, enriched, dashboard, and summary metric outputs
       from registered config paths.
   * - ``metric_workflow_output_input_columns``
     - Return the long metric-row column projection used by downstream output
       writers before enrichment and dashboard/path summary generation.
``PSA`` and ``FAS`` are broadband spectral metrics in the file-based workflow.
Task planning separates them from passband-dependent metrics, writes blank
``passband`` values for spectral tasks, and stores oscillator-period outputs in
``period_s``. This keeps PSA/FAS values from being interpreted as values after
each waveform passband filter. Rebuild metric manifests and metric rows if an
older output table contains PSA rows repeated under passband labels.

.. automodule:: spatial_vtk.metrics.workflow
   :members:
   :exclude-members: MetricWorkflowTask, SlurmSettings

.. autoclass:: spatial_vtk.metrics.StandardMetricWorkflowOutputResult
   :members:

.. autofunction:: spatial_vtk.metrics.load_standard_metric_workflow_outputs

Import workflow helpers from ``spatial_vtk.metrics`` or
``spatial_vtk.metrics.workflow``. The configured, inventory, cache,
execution, output, run, Slurm, and task modules are implementation
organization and are intentionally not listed as notebook-facing import paths.

Plotting
--------

Routine notebooks should render the standard metric figure suite through the
Step 3 result object so the configured ``metrics_long`` table, output paths,
render gates, and sidecar settings stay in package code.

.. code-block:: python

   from spatial_vtk.metrics import load_standard_metric_workflow_outputs

   metric_outputs = load_standard_metric_workflow_outputs(cfg=cfg)
   metric_figure_suite = metric_outputs.write_large_run_figure_suite(settings)

Focused scripts and custom extensions can import plotting helpers from the
stable ``spatial_vtk.metrics.plot`` package entry point when they already own
the filtered metric rows or resolved table paths. The implementation submodules
are not part of the tutorial-facing API. Direct suite writers remain documented
below for scripts that intentionally bypass the standard Step 3 result object,
but they are not the focused-script import starting point.

.. code-block:: python

   from spatial_vtk.metrics.plot import (
       plot_band_score_distribution,
       plot_period_spectra,
       plot_residuals_vs_distance,
   )

.. automodule:: spatial_vtk.metrics.plot
   :members:

Public plotting helpers exposed by ``spatial_vtk.metrics.plot``:

.. list-table::
   :header-rows: 1

   * - Helper
     - Use
   * - ``plot_band_score_distribution``
     - Compare metric residual or score distributions by passband, component,
       model, or metric group.
   * - ``plot_period_score_distribution``
     - Compare PSA and period-indexed residual or score distributions by
       oscillator period.
   * - ``plot_period_spectra``
     - Plot period spectra from prepared spectral summary tables.
   * - ``plot_period_spectrogram``
     - Plot period-by-record spectral intensity summaries.
   * - ``plot_psa_period_curve``
     - Plot PSA values or residuals across oscillator periods.
   * - ``write_large_run_metric_figure_suite_from_notebook_settings``
     - Lower-level Step 3 suite writer for scripts or compatibility paths
       that already own notebook figure settings. New notebooks should
       usually call
       ``load_standard_metric_workflow_outputs(...).write_large_run_figure_suite(...)``
       so readiness, config, metric-row selection, and output bookkeeping stay
       on the Step 3 result object.
   * - ``plot_residuals_vs_distance``
     - Plot metric residuals against distance with optional trend overlays.
   * - ``plot_residuals_vs_depth``
     - Plot metric residuals against event depth.
   * - ``plot_phase_delay_vs_distance``
     - Plot traveltime or phase-delay residuals against distance.
   * - ``plot_metric_trend`` and ``plot_score_trends``
     - Plot custom metric trends and optional GOF score diagnostics.
   * - ``plot_vs30_scatter`` and ``plot_geology_boxplot``
     - Plot site-condition diagnostics against Vs30 or geologic classes.
   * - ``plot_model_metric_heatmap`` and ``plot_winner_heatmap``
     - Plot model-comparison summaries.
   * - ``plot_example_metric_pairs``
     - Plot synthetic trace-pair examples for documentation and sanity checks.

Large-Run Figure Suite
----------------------

Notebook-facing metric plotting should use
``load_standard_metric_workflow_outputs(...).write_large_run_figure_suite(...)``
for the full configured suite, or the result object's focused figure methods
for individual standard figures. The lower-level context and direct suite
helpers below remain public for scripts and custom extensions. These helpers
keep row filtering, robust plot scaling, sidecar writing, render gates, and
registered output paths in package code instead of notebook cells.

Use ``MetricFigureContext`` in scripts or custom extensions that need to render
many metric figures from a large ``metrics_long`` table without loading
unnecessary columns or truncating station-map aggregation inputs. Standard
notebooks should use the Step 3 result object's figure methods; those methods
build and own the context internally. The context owns the standard row
factories used by the large-run figure suite:

``item_source_rows``
   Return the selected metric rows for a figure item. These rows are written to
   ``*.source.csv`` sidecars for aggregated station figures.

``station_summary_for_item`` and ``station_period_summary_for_item``
   Collapse all selected event-station metric rows to station summaries before
   plotting. Station grouping is based on station identifiers, not exact
   coordinate values, so small coordinate jitter does not split one station
   into multiple plotted points. The summary rows retain input and finite
   source-row/event counts, finite-value drop counts, coordinate counts, and
   aggregation metadata so users can audit whether every selected event
   contributed to the plotted station value. PSA period sheets use the
   period-aware variant and preserve the same source-row sidecar contract for
   each oscillator-period panel.

``metric_item``, ``station_summary_for_metric``,
``station_summary_preview_for_metric``, and
``write_station_metric_map_for_metric``
   Select one named metric by key, display label, or alias, then build the
   station summary and focused station map with the same source-row sidecar
   contract used by the full large-run figure suite. Use these helpers for
   concise tutorial cells that should render or preview one metric without
   hand-filtering dataframes in the notebook.

``write_station_metric_map_from_notebook_settings``
   Build the focused station-map context, render one named metric, and return
   both a status table and station-summary preview using notebook figure
   settings. Standard tutorials use this helper instead of constructing a
   ``MetricFigureContext`` in the notebook. When figure sidecars are enabled,
   the returned ``StationMetricMapResult.status_frame()`` includes a clear
   ``resolved_path`` row for the rendered figure while preserving
   ``output_path`` for compatibility. The figure rows include normalized
   ``artifact_label``, ``artifact_role``, ``status``, ``exists``,
   ``resolved_path``, and ``path`` columns; audit rows preserve the same
   ``name`` / ``value`` pattern used by existing notebooks. The status frame
   also includes the station-aggregation contract, source-row role/filter,
   input/finite row and event counts, and sidecar exactness flags from the
   saved JSON metadata.

``write_standard_metric_diagnostic_figures``
   Render the standard Step 3 residual-distance, score-trend, and
   band residual-distribution diagnostics from one metric dataframe and an
   ``OutputGroup``. The helper owns the tutorial metric filtering, configured
   figure paths, sidecar keyword expansion, and per-figure status table so
   notebooks do not import individual plotting functions or call
   ``render_notebook_figure`` directly. The returned status frame includes
   normalized ``name``, ``artifact_label``, ``artifact_role``, ``status``,
   ``resolved_path``, ``path``, and ``exists`` columns while preserving the
   legacy ``figure_path`` and ``figure_exists`` fields.

``write_large_run_metric_figure_suite_from_notebook_settings``
   Build the large-run metric figure context, render the standard Step 3
   figure families, and return a per-family status table. The standard metric
   result object's ``write_large_run_figure_suite(...)`` method delegates to
   this helper so large-run notebooks do not import individual plotting
   functions, repeat selection kwargs, or add notebook-local gates for optional
   score trends. The
   status table includes exact ``figure_paths`` lists plus the existing
   ``first_figure_path`` and ``figure_paths_preview`` display fields so
   notebooks do not parse preview strings to inspect generated figures. It
   also includes normalized ``name``, ``artifact_label``, ``resolved_path``,
   ``path``, ``exists``, ``artifact_role``, and ``status`` columns keyed to
   the first figure in each family.
   The returned ``MetricFigureSuiteResult`` also owns
   ``context_status_frames()`` and ``display_context_status(...)`` so notebooks
   can display metric-table readiness, spectral-contract checks, and dimension
   summaries without branching on context readiness in notebook cells.

``station_grid_for_item`` and ``station_model_summary_for_item``
   Prepare station summaries for grid and model-map plotting while preserving
   aggregation metadata for sidecar JSON files.

``status_frame`` and ``dimension_summary_frame``
   Return small notebook tables that summarize the configured metric input,
   loaded columns, selected row count, default filters, sidecar settings, and
   metric/passband/component/model/event/station coverage before figures are
   rendered. These checks do not read additional large files. Path rows include
   normalized ``artifact_label``, ``resolved_path``, ``path``, and ``exists``
   columns while preserving the scalar ``name``/``value`` display used by
   notebooks. ``status_frame`` also includes ``spectral_contract_status`` plus
   PSA/FAS broadband and legacy passband row counts, so notebooks can warn
   users to rebuild metric rows before PSA plots are skipped because they came
   from older passband-scoped spectral outputs.

``spectral_metric_contract_status``
   Return a compact PSA/FAS audit table with row counts, broadband row counts,
   legacy passband-scoped row counts, period counts, and rebuild guidance.
   Display this next to ``status_frame`` when diagnosing old metric outputs.

``metric_plot_input_summary_frame``
   Return a small ``Input``/``Value`` table for plotting notebooks, including
   metric row count, event count, station count, metric names, and optional
   waveform-preview pair count. Use this instead of constructing summary
   dataframes in notebook cells.

``write_residuals_vs_distance_plots``, ``write_residuals_vs_depth_plots``,
``write_vs30_scatter_plots``, ``write_station_metric_maps``,
``write_residual_grid_maps``, ``write_metric_by_model_maps``,
``write_event_residual_maps``, ``write_log2_residual_distribution_plots``,
``write_psa_period_curve_plots``, and
``write_standard_metric_diagnostic_plots``
   Render the standard large-run metric figure families from one context. These
   methods keep target-metric iteration, PSA period sheets, robust axis
   settings, station aggregation, and raw source-row sidecars in package code
   instead of notebook-local loops.

For PSA, large-run figure helpers compare oscillator periods instead of
waveform passbands. Station maps, model maps, residual grids, event maps,
scatter plots, and distribution plots are written as PSA period sheets when the
input rows contain multiple ``period_s`` values; period curves use the same
``period_s`` values directly.

Advanced Figure Extension Helpers
---------------------------------

The functions in this section are public for custom scripts and extension
code, but they are not the preferred tutorial or notebook entry points. New
notebooks should call
``load_standard_metric_workflow_outputs(...).write_large_run_figure_suite(...)``,
``load_standard_metric_workflow_outputs(...).write_standard_diagnostic_figures(...)``,
or ``load_standard_metric_workflow_outputs(...).write_station_metric_map(...)``
so the package owns the data-selection contract and output bookkeeping.

``metric_rows_for_metrics``
   Select metric rows by metric names, display labels, keys, or aliases before
   calling lower-level plotting functions.

``prepare_large_run_metric_figure_context``
   Build a reusable ``MetricFigureContext`` for scripts that need to customize
   the standard large-run figure families programmatically.

.. autoclass:: spatial_vtk.metrics.plot.MetricFigureContext
   :members:

.. autoclass:: spatial_vtk.metrics.plot.MetricFigureSuiteResult
   :members:

.. autoclass:: spatial_vtk.metrics.plot.StandardMetricDiagnosticFigureResult
   :members:

.. autoclass:: spatial_vtk.metrics.plot.StationMetricMapResult
   :members:

.. autofunction:: spatial_vtk.metrics.plot.metric_plot_input_summary_frame

.. autofunction:: spatial_vtk.metrics.plot.metric_rows_for_metrics

.. autofunction:: spatial_vtk.metrics.plot.prepare_large_run_metric_figure_context

.. autofunction:: spatial_vtk.metrics.plot.write_large_run_metric_figure_suite_from_notebook_settings

.. autofunction:: spatial_vtk.metrics.plot.write_standard_metric_diagnostic_figures

.. autofunction:: spatial_vtk.metrics.plot.write_station_metric_map_from_notebook_settings
