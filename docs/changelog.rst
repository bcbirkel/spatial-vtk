Changelog
=========

2026-06-18
   Added ``write_standard_geojson_region_figures()`` and rewired the standard
   Step 5 GeoJSON notebook to use it for the GeoJSON overview, regional PGA
   contrast, and regional station residual map. The notebook no longer owns
   GeoJSON region annotation, summary-table generation, configured figure-path
   lookup, or sidecar keyword plumbing for those figures.
   Added ``write_standard_additional_plotting_figures()`` and rewired the
   standard Step 6 additional-plotting notebook to use it for the waveform
   map, pattern-similarity figure, scatterplot, boxplot, and heatmap. The
   notebook no longer imports individual plotting functions, calls
   ``render_notebook_figure()`` directly, or owns waveform selection, GeoJSON
   metric annotation, figure-path lookup, and preview-table construction.
   Added ``display_dashboard_preparation_result()`` and rewired the standard
   Step 7 dashboard notebook to use it for readiness, artifact-status,
   written-output, and dashboard-summary contract displays. The notebook no
   longer imports dashboard table-formatting helpers or formats each
   preparation dataframe by hand.
   Added ``write_standard_metric_diagnostic_figures()`` and rewired the
   standard Step 3 metric notebook to use it for residual-distance,
   GOF-distance, and band-distribution diagnostics. The notebook no longer
   imports individual metric plotting functions, calls
   ``render_notebook_figure()`` directly, or filters the tutorial metric set in
   notebook code for those figures.
   Added ``write_standard_spatial_diagnostic_figures()`` and rewired the
   standard Step 4 spatial notebook to use it for spatial-correlation,
   PCA-summary, and geology-contrast diagnostic figures. The notebook no
   longer imports those plot functions directly or owns per-metric diagnostic
   table filters; package code handles configured figure paths, sidecar
   options, compact preview tables, and status reporting.
   Added ``NotebookFigureSidecarSettings.readiness_frame()`` and updated the
   metric/spatial provenance cells in the standard and large-run notebooks to
   display sidecar readiness before the per-figure sidecar metadata table. The
   readiness table tells users whether row-provenance sidecars are enabled,
   which directory is being inspected, how many JSON metadata files exist, and
   whether sidecar CSV rows are complete or deterministically sampled.
   Added
   ``write_large_run_metric_figure_suite_from_notebook_settings()`` and
   rewired the large-run Step 3 metric notebook to call it for the full metric
   figure suite. The notebook no longer imports or references individual
   metric/spatial plotting functions or repeats per-family plotting cells;
   package code owns metric context construction, selection kwargs, optional
   score-trend gates, PSA period sheets, station aggregation, and source-row
   sidecars.
   Added
   ``write_large_run_spatial_figure_suite_from_notebook_settings()`` and
   rewired the large-run Step 4 spatial notebook to call it for the full
   spatial figure suite. The notebook no longer imports individual map/plot
   functions or repeats per-family plotting cells; package code owns the
   figure-function imports, selection kwargs, PSA period sheets, station
   aggregation, and source-row sidecars.
   Expanded ``StationMetricMapResult.status_frame()`` so focused tutorial
   station-map cells surface sidecar JSON audit fields directly, including the
   aggregation contract, source-row role/filter, input and finite row/event
   counts, and sidecar exactness flags.
   Strengthened ``tools/execute_tutorial_notebooks.py --runtime-check-only`` so
   it makes the source checkout importable and verifies the tutorial execution
   environment beyond Jupyter packages, including ``spatial_vtk``, scientific
   Python, mapping, dashboard, and waveform modules before any notebook
   outputs are cleaned or cells are executed.
   Added explicit QC dashboard Data Status messages for loaded and filtered
   trace-summary scopes, including bounded-prefix loads and filters that remove
   all currently loaded rows.
   Updated the metrics dashboard Data Status current-filter summary so skipped
   optional summary tables report their readiness cause, such as a missing
   station or path summary, instead of a generic "no rows match" message.
   Added regression coverage for sampled station-map sidecars so source-row
   sidecars stay tied to the station groups actually plotted while aggregation
   metadata still reports the full selected event-station input.
   Added a public ``RELEASE_CHECKLIST.md`` matching the current validation,
   notebook execution, docs, build, wheel-inspection, and publish gates. The
   checklist keeps release steps in the repository instead of only in agent
   instructions and avoids private machine- or cluster-specific paths.
   Tightened the tutorial notebook preflight so notebook-local function and
   class definitions are rejected. Reusable logic now has an executable guard
   that keeps it in importable package helpers instead of public notebook
   cells.
   Added
   ``spatial_vtk.metrics.plot.write_station_metric_map_from_notebook_settings()``
   and rewired the standard Step 3 metrics notebook to use it for the focused
   station residual map. The notebook no longer imports
   ``MetricFigureContext`` or spatial map plotting functions just to render
   one station summary; package code now owns the context setup, station
   aggregation, source-row sidecar contract, status table, and preview rows.
   Added ``spatial_vtk.visualize.qc.write_qc_figures_from_outputs()`` as the
   generic QC figure-suite writer and rewired the standard Step 2 QC notebook
   to use it. The notebook no longer imports individual QC plotting functions,
   loads compact QC figure tables manually, or repeats basemap,
   ``showfig``/``savefig``, and sidecar kwargs for each QC figure. Extended
   ``write_waveform_comparison_from_notebook_settings()`` with
   ``plot_options`` and rewired the same notebook to use it for the bounded
   waveform comparison preview.
   Rewired large-run Step 4 spatial plotting cells to use
   ``NotebookFigureSettings.plot_selection_kwargs()`` for shared passband,
   component, model, ``showfig``, value-column, and robust-axis selections.
   The notebook no longer repeats ``PLOT_PASSBAND``, ``PLOT_COMPONENTS``,
   ``PLOT_MODEL``, ``PLOT_SHOWFIG``, ``PCA_MODE``, or robust-percentile
   assignments around each spatial figure family.
   Added ``spatial_vtk.visualize.context.write_context_figures_from_outputs()``
   as the generic Step 1 context figure writer and rewired the standard Step 1
   ingest notebook to use it. The notebook no longer imports individual
   context plotting functions or repeats basemap, ``showfig``/``savefig``,
   close, and sidecar kwargs for each context figure.
   Added ``NotebookFigureSettings.plot_selection_kwargs()`` for
   context-managed notebook plotting calls and rewired the large-run Step 3
   metric plotting notebook to use it. The notebook no longer defines separate
   default passband, component, model, basemap, robust-axis, comparison-table,
   or sidecar variables around each metric figure family.
   Added optional standard Step 3 figure artifacts for residual-distance,
   score-trend, station metric map, and band score distribution outputs. The
   standard Step 3 metrics notebook now uses
   ``spatial_vtk.config.render_notebook_figure()`` for individual metric
   figures and no longer repeats sidecar, ``showfig``, or ``savefig`` kwargs
   in those plot cells.
   Rewired the remaining standard Step 4 spatial plotting cells to use
   ``spatial_vtk.config.render_notebook_figure()`` for distance-correlation,
   PCA summary, and geology-contrast figures. The notebook no longer repeats
   configured figure-path resolution, ``showfig``/``savefig``, sidecar kwargs,
   or basemap kwargs in those cells.
   Rewired the standard Step 6 additional plotting notebook to use
   ``spatial_vtk.config.render_notebook_figure()`` for waveform maps, pattern
   similarity, scatterplot, boxplot, and heatmap figures. The notebook no
   longer repeats configured figure-path resolution, ``showfig``/``savefig``,
   sidecar kwargs, or basemap kwargs in each plot cell.
   Added ``spatial_vtk.config.render_notebook_figure()`` and rewired the
   standard Step 5 maps notebook to use it for configured plot rendering. The
   notebook keeps the GeoJSON, corridor, waveform, and metric-selection logic
   visible while no longer repeating ``outpath``, ``savefig``, ``showfig``,
   sidecar kwargs, display, or ``plt.close`` plumbing around each plot call.
   Added ``spatial_vtk.spatial.plot.write_standard_spatial_map_figures()`` and
   rewired the standard Step 4 spatial notebook to use it for station-bias and
   residual-grid maps. The notebook no longer repeats per-metric map loops,
   output-path construction, sidecar keyword expansion, or basemap/showfig
   keyword plumbing for those figure families.
   Added
   ``spatial_vtk.visualize.dashboard.prepare_configured_dashboard_datasets_from_notebook_settings()``
   and rewired the standard Step 7 dashboard notebook to use it. The notebook
   no longer performs dashboard readiness branching, local-write decisions, or
   written-output loop printing inline.
   Added
   ``spatial_vtk.spatial.plot.write_large_run_region_boxplot_from_notebook_settings()``
   and rewired the large-run Step 6 region boxplot cell to use it. The
   notebook no longer performs the region-boxplot render gate or
   settings-to-plot-keyword translation inline.
   Added
   ``spatial_vtk.spatial.plot.write_large_run_geojson_region_figures_from_notebook_settings()``
   and rewired the large-run Step 5 GeoJSON/corridor figure cell to use it.
   The notebook no longer performs the region figure render gate or
   settings-to-figure-keyword translation inline.
   Added
   ``spatial_vtk.visualize.waveforms.write_waveform_comparison_from_notebook_settings()``
   and rewired the large-run Step 6 waveform comparison cell to use it. The
   notebook no longer performs the waveform figure render gate or
   settings-to-plot-keyword translation inline.
   Added
   ``spatial_vtk.visualize.context.write_large_run_context_figures_from_outputs()``
   and rewired the large-run Step 1 context figure cell to use it. The
   notebook no longer performs context-table readiness checks, table loading,
   basemap keyword selection, figure-path selection, or context plotting calls
   inline.
   Added
   ``spatial_vtk.visualize.qc.write_large_run_qc_figures_from_outputs()``
   and rewired the large-run Step 2 QC figure cell to use it. The notebook no
   longer performs compact-QC input gating, table loading, figure-path
   selection, or plotting calls inline.
   Added
   ``spatial_vtk.spatial.plot.write_large_run_spatial_summary_figures_from_outputs()``
   and rewired the large-run Step 4 quick spatial-figure cell to use it. The
   notebook no longer performs station-bias input gating, table loading, or
   map-path plumbing inline.
   Added
   ``spatial_vtk.spatial.plot.prepare_spatial_figure_context_from_notebook_settings()``
   and rewired the large-run Step 4 spatial notebook to use it. The notebook
   now keeps figure controls visible without repeating the context keyword,
   figure-directory, sidecar, basemap, and sampling plumbing.
   Simplified the large-run Step 2 QC notebook so
   ``run_qc_inventory_from_config`` resolves configured event-station and QC
   output paths itself, rather than passing registry paths back through
   notebook-local keyword arguments.
   Made ``SpatialFigureContext`` route Step 4 metric-field and event-centered
   figure items by explicit owner tags instead of dataframe column-subset
   inference. This prevents large-run spatial figures from using the wrong
   plotting context when compact Step 4 tables share similar schemas.
   Expanded ``figure_sidecar_status_frame()`` so notebook sidecar audits expose
   source-row filters, plot/source dimension counts, station/event aggregation
   counts, and PSA/multi-panel counts without loading large CSV sidecars.
   Added ``metric_rows_for_metrics()`` to the public
   ``spatial_vtk.metrics.plot`` API. Rewired the standard Step 3 metric
   notebook to use it for focused plotting examples instead of notebook-local
   ``figure_metrics.loc[...isin(...)]`` filtering.
   Added ``event_station_records_matching_pairs()`` and
   ``geojson_matched_record_frame()`` to the public ``spatial_vtk.spatial``
   API. Rewired the standard Step 5 corridor notebook to use them instead of
   notebook-local GeoJSON boolean masks and event-station pair merges.
   Added ``event_ids_from_records()``, ``event_rows_for_records()``, and
   ``event_label_preview_frame()`` to the public ``spatial_vtk.io`` API.
   Rewired the standard Step 5 maps notebook to use these helpers for regional
   and corridor event subsets instead of notebook-local
   ``events.loc[...isin(...)]`` filtering and event-name ``drop_duplicates()``
   previews.
   Added ``geojson_metric_region_frame()`` and
   ``geojson_metric_subset_frame()`` to the public spatial API. Rewired
   standard Step 5 and Step 6 GeoJSON metric plots to use these helpers instead
   of notebook-local GeoJSON label and metric-dimension filtering.
   Added ``corridor_record_pair_frame()`` to the public spatial API and rewired
   standard Step 5 corridor maps, waveform joins, and selected-path maps to use
   it instead of repeated event-station ``drop_duplicates`` snippets in the
   notebook.
   Added ``spatial_metric_table_frame()``,
   ``spatial_metric_product_frames()``, and ``spatial_pca_product_frames()`` to
   the public spatial API. The standard Step 4 notebook now uses these helpers
   for metric-specific spatial, PCA, and geology tables instead of repeating
   dataframe metric filters in cells.
   Added ``station_bias_preview_frame()`` and
   ``corridor_record_preview_frame()`` to the public spatial API. Rewired the
   standard Step 4 and Step 5 notebooks to use those package helpers instead of
   direct ``head()``/``drop_duplicates().head()`` preview snippets.
   Added ``MetricFigureContext.station_summary_preview_for_metric()`` and
   rewired the standard Step 3 metric notebook to use it for station-summary
   audit previews instead of slicing station-summary dataframes in the
   notebook.
   Added ``station_event_waveform_order_frame()`` to the public waveform
   visualization API and rewired the standard Step 6 plotting notebook to use
   it for station-order previews instead of inline sort/head dataframe code.
   Added ``spatial_correlation_preview_frame()`` to the public spatial API and
   rewired the standard Step 4 spatial notebook to use it for Moran's I and
   distance-bin diagnostic previews instead of notebook-local filtered
   ``.head()`` displays.
   Rewired the standard Step 1 ingest notebook station/event preview cells to
   use ``OutputGroup.display_table_previews()`` instead of direct dataframe
   ``.head()`` displays.
   Rewired the standard Step 3 metric notebook to preview the metric task table
   and ``metrics_long`` output through ``OutputGroup.display_table_previews()``
   instead of loading full tables only to display ``.head()`` rows.
   Added ``first_nonempty_table_value()`` to the public ``spatial_vtk.io`` API
   and rewired the standard Step 5 maps notebook to use it for model labels.
   Missing or empty model columns now use a stable fallback instead of raising
   from a notebook-local ``.iloc[0]`` lookup.
   Added ``event_display_label()`` to the public ``spatial_vtk.io`` API and
   rewired the standard Step 6 plotting notebook to use it for waveform figure
   titles. Missing event-name rows now fall back to the event id instead of
   raising from a notebook-local ``iloc[0]`` lookup.
   Added ``spatial_workflow_failure_frame()`` and
   ``spatial_metric_product_summary_frame()`` to the public spatial API. The
   standard Step 4 spatial notebook now uses these helpers for workflow
   diagnostics and per-metric product summaries instead of constructing local
   ``pd.DataFrame`` displays.
   Added ``metric_plot_input_summary_frame()`` to the public metric plotting API
   and rewired the standard Step 6 plotting notebook to use it instead of
   constructing a local ``pd.DataFrame`` summary. This keeps the notebook
   focused on plotting tasks while package code owns the reusable input-summary
   contract.
   Updated standard Step 5 and Step 6 notebooks to name their Step 1
   ``OutputGroup`` before loading tables, keeping output-group access
   consistent across tutorial cells.
   Rewired Step 2 QC and large-run Step 3 metric preview cells to use
   ``OutputGroup.display_table_previews()`` instead of notebook-local
   ``preview_table()`` branches.
   Added ``display_dashboard_output_previews()`` to the public dashboard API
   and rewired Step 7 notebooks to use it for bounded dashboard summary and
   ``metrics_long`` previews instead of notebook-local path checks.
   Added ``figure_subdir`` support to ``notebook_figure_settings()`` and
   rewired the large-run notebooks to use ``figure_subdir="metrics"`` for
   metric, spatial, and region figure suites. The large-run notebooks no
   longer bind ``figures_dir = context.figures_dir``, build
   ``figures_dir / "metrics"`` paths, or maintain separate
   ``METRICS_FIGURE_DIR`` aliases.
   Updated ``notebook_figure_settings()`` so it resolves and creates the
   active config's ``outputs.figures`` directory when no explicit
   ``figure_dir`` is supplied. Standard tutorial notebooks now rely on that
   package helper instead of assigning ``figure_dir = context.figures_dir`` and
   creating the directory in setup cells.
   Registered missing waveform visualization figure defaults for record
   sections, observed/synthetic record sections, waveform overlay matrices,
   and event radial trace sections. Rewired the standard Step 5 GeoJSON and
   corridor notebook to use ``OutputGroup.figure_path()`` for GeoJSON maps,
   regional boxplots, station residual maps, corridor maps, and boundary
   record-section outputs instead of hand-joining ``figure_dir`` paths.
   Registered the standard Step 6 plotting figures on the ``step_06_plotting``
   output group and rewired the Step 6 additional plotting notebook to use
   ``OutputGroup.figure_path()`` for waveform maps, pattern similarity,
   scatterplot, boxplot, and heatmap outputs instead of hand-joining
   ``figure_dir`` paths in notebook cells.
   Added ``OutputGroup.figure_path()`` and registered optional Step 4 spatial
   figure artifacts so notebooks can derive metric-specific figure filenames
   from configured output keys instead of hand-joining ``figure_dir`` paths.
   Rewired the standard Step 4 spatial notebook to use the helper for station
   bias maps, residual grids, spatial-correlation plots, PCA summaries, and
   geology contrasts.
   Added the generic
   ``spatial_vtk.visualize.waveforms.write_waveform_comparison_from_outputs``
   helper and rewired the standard Step 2 QC notebook to use it for the
   observed/synthetic waveform preview. The notebook no longer repeats the
   comparison-eligible loading, waveform-record construction, and trace plotting
   pipeline inline.
   Added config-backed ``svtk visualize`` guidance to the generated CLI
   reference so context, QC, waveform, and sidecar commands show the same
   configured-default path pattern as ``svtk plot``, ``svtk map``, and
   dashboards.
   Removed the remaining development-only ``reload_metric_plot_modules()``
   helper from the metric plotting package surface. Large-run notebooks now use
   normal imports from ``spatial_vtk.metrics.plot`` and tests guard against the
   reload hook returning.
   Updated the configuration API reference so notebook helpers are documented
   through the stable ``spatial_vtk.config`` package surface instead of the
   implementation module ``spatial_vtk.config.notebook``. Added a regression so
   the implementation-module autodoc block does not return.
   Added ``OutputGroup.load_path_table()`` and ``preview_path_table()`` for
   output groups that own table paths outside the standard registry, such as
   preprocessed waveform metadata. Standard Step 1 now previews the waveform
   preprocessing manifest through the preprocessed output group instead of
   calling ``read_table(...).head()`` in the notebook.
   Removed the development-only ``reload_metric_plot_modules()``/
   ``globals().update(...)`` hook from the large-run Step 3 notebook. Metric
   figure cells now rely only on the package ``MetricFigureContext`` methods,
   and notebook source-contract coverage prevents hidden global namespace
   mutation from returning to the tutorial.
   Rewired the standard Step 1 ingest notebook to use config-backed
   ``spatial_vtk.io`` workflow helpers for metadata preparation, waveform
   preprocessing, and record-coverage writing. The notebook now reads the
   resulting station/event/context tables through ``OutputGroup`` and has a
   regression that prevents returning to inline table construction.
   Added focused metric figure helpers
   ``MetricFigureContext.metric_item()``,
   ``station_summary_for_metric()``, and
   ``write_station_metric_map_for_metric()``. The standard Step 3 notebook now
   uses these package helpers for the PGA station map instead of hand-filtering
   rows and passing ``source_df`` from notebook code, while retaining the same
   station aggregation and source-row sidecar audit trail.
   Added ``SpatialFigureContext.spectral_metric_contract_status()`` and wired
   the large-run Step 4 notebook to display it beside the spatial status and
   dimension summaries. Spatial figure cells now surface whether
   ``metric_field`` or ``event_centered_residuals`` still contain legacy
   passband-scoped PSA/FAS rows before Step 4 maps and grids are rendered.
   Added PSA/FAS spectral-contract status to ``MetricFigureContext``.
   ``status_frame()`` now reports aggregate spectral contract status and
   PSA/FAS broadband versus legacy passband row counts, while
   ``spectral_metric_contract_status()`` returns a detailed audit table for
   notebook diagnostics before large-run PSA figures are rendered.
   Documented the broadband spectral-metric contract for large runs. The
   large-run README, Python workflow reference, and metrics API now state that
   ``PSA`` and ``FAS`` are planned as blank-passband spectral tasks with
   oscillator-period outputs in ``period_s``, and that legacy passband-scoped
   PSA metric rows should be rebuilt before using current plotting notebooks.
   Improved generated API-reference fallback parameter text. When a public
   function lacks hand-written parameter docs, Sphinx now emits name-aware
   descriptions for common workflow values such as ``input_path``, ``output``,
   ``summary``, ``config_path``, and figure sidecar settings instead of generic
   placeholder text.
   Added ``tools/execute_tutorial_notebooks.py --runtime-check-only`` so users
   can verify tutorial source contracts, committed example data, and notebook
   execution runtime dependencies without cleaning outputs or starting notebook
   kernels.
   Aligned notebook runtime dependencies across the pip ``notebooks`` extra and
   ``svtk_environment.yaml``. Both install paths now name the modules required
   by the tutorial notebook executor, including ``IPython``.
   Added ``write_large_run_geojson_region_figures_from_outputs()`` and
   ``RegionFigureResult`` so large-run Step 5 renders the GeoJSON overview,
   corridor map, and region boxplot through one package helper. The Step 5
   notebook now exposes figure settings and a status table while package code
   owns prepared station/event loading, corridor-table reuse, configured figure
   paths, overwrite handling, and bounded metric reads.
   Added package-level ``MetricFigureContext`` helpers for large-run Step 3
   metric figure families, including residual distance/depth trends, Vs30
   scatter plots, station maps, residual grids, model-faceted maps, event
   residual maps, log2 residual distributions, and PSA period curves. The
   large-run metric notebook now keeps only per-cell plotting overrides and
   calls those package helpers, while target-metric iteration, PSA period-sheet
   branching, station aggregation, and raw source-row sidecars stay in package
   code.
   Added package-level ``SpatialFigureContext`` helpers for large-run Step 4
   spatial figure families, including station metric maps, residual grids,
   model-faceted maps, event residual maps, and event-centered azimuthal/polar
   plots. The large-run spatial notebook now keeps only the per-cell plotting
   overrides and calls those package helpers, while source-row sidecar
   provenance and PSA period-sheet branching stay in package code.

2026-06-17
   Standard tutorial notebooks now use ``notebook_run_context()`` for config
   loading, activation, and output-directory discovery, matching the large-run
   notebooks and avoiding repeated direct ``SpatialVTKConfig.from_file`` setup
   cells.
   ``OutputReadiness`` and output status tables now handle unconfigured
   optional input paths explicitly. Passing a named input value of ``None``
   reports ``<not configured>`` in notebook status tables, blocks dependent
   work with ``missing_inputs``, and avoids fake placeholder paths in public
   large-run examples.
   Added ``MetricFigureContext.status_frame()`` and
   ``MetricFigureContext.dimension_summary_frame()`` so large-run metric
   plotting notebooks can display the selected row count, loaded column count,
   filter defaults, sidecar settings, and metric/passband/component/model/event
   station coverage before rendering figures. Large-run Step 3 now displays
   those package-generated audit tables next to the plotting context setup.
   Added matching ``SpatialFigureContext.status_frame()`` and
   ``SpatialFigureContext.dimension_summary_frame()`` helpers for Step 4
   large-run spatial figures. The Step 4 notebook now displays loaded spatial
   output-table status, plotted value-column choices, and metric/event-centered
   dimension coverage before rendering figure batches.
   Added ``OutputGroup.display_table_previews()`` so notebooks can print
   configured output paths and bounded previews from the group object that owns
   those paths. Large-run Steps 4 and 5 now use this method instead of importing
   a separate preview helper and repeating output-key preview mappings.
   Added ``OutputGroup.display_first_existing_table_preview()`` for fallback
   table previews such as ``metrics_enriched`` with ``metrics_long`` fallback.
   Large-run Step 6 now uses this helper instead of separately selecting and
   previewing the same fallback table list in notebook code.
   Added ``write_large_run_region_boxplot_from_outputs()`` so large-run Steps 5
   and 6 can render region boxplots through a package-owned
   ``metrics_enriched``/``metrics_long`` fallback instead of selecting metric
   source paths in notebook cells.
   Added
   ``spatial_vtk.visualize.waveforms.write_large_run_waveform_comparison_from_outputs()``
   so large-run Step 6 can render the observed/synthetic trace comparison from
   configured Step 6 outputs without inline QC sample loading or waveform-record
   construction in the notebook.
   Added
   ``spatial_vtk.visualize.dashboard.launch_configured_dashboards_from_notebook_settings()``
   so Step 7 notebooks can launch requested Metrics/QC dashboards or display
   terminal fallback commands through one package helper instead of duplicating
   per-dashboard launch branches. The helper also supports QC-only launch
   status rows, and the Step 2 QC tutorial now uses that package helper instead
   of branching around ``launch_configured_qc_dashboard()`` in notebook code.
   Added ``spatial_vtk.io.load_configured_input_paths()`` for configured
   non-table inputs such as ``paths.region_geojson``. Standard and large-run
   Step 5 now use this helper instead of resolving GeoJSON paths with direct
   ``cfg.path`` calls in notebook cells.
   Added config-backed metric readiness helpers for Slurm submission, batch
   merging, and downstream metric output tables. Large-run Step 3 now uses
   those Python package helpers directly instead of notebook-local manifest and
   metric-row path checks, keeping the notebook focused on workflow steps while
   package code owns the large-run readiness logic.
   Large-run Step 3 metric figure cells now gate plotting through
   ``metric_plot_context.ready`` instead of repeating metric-table existence,
   figure-enable, and value-column checks in every cell.
   Large-run Step 2 compact QC summaries now rely on
   ``OutputGroup.readiness()`` to report a missing overlap inventory, and
   large-run Step 5 optional corridor-map rendering now uses
   ``OutputGroup.load_tables(..., missing="skip")`` instead of direct
   ``Path.exists()`` checks in notebook cells.
   Standard Step 7 now checks ``dashboard_output_readiness`` before preparing
   dashboard datasets locally, displays the same readiness summary/status used
   by the large-run dashboard driver, and skips dataset writes when dashboard
   outputs are current.
   Added ``OutputGroup.first_existing_path()`` and
   ``OutputGroup.preview_first_existing_table()`` for ordered fallback table
   previews. Large-run Steps 3, 6, and 7 now preview metric tables through
   output groups instead of direct ``preview_table`` or ``preview_output_table``
   calls in notebook cells.
   Large-run Steps 1 and 5 now also avoid stale direct preview imports and
   direct metric-source fallback expressions in favor of output-group helpers.
   Standard tutorial Steps 2 and 7 now preview configured QC and dashboard
   tables through ``OutputGroup.preview_tables()`` instead of raw table-preview
   helpers.
   Standard Step 2 now lets the QC inventory helper resolve configured output
   paths directly and reuses the manual-review queue written by the compact QC
   summary workflow, avoiding a redundant notebook-local export call.
   Standard Step 2 now also uses ``OutputGroup.readiness()`` with
   ``run_notebook_step_if_needed(..., run_local=True)`` for the full QC,
   overlap sidecar, and compact summary table steps, matching the large-run
   package-runner pattern while keeping the small tutorial local.
   Standard Step 7 now uses ``dashboard_outputs`` attributes directly in
   dashboard status and preview cells instead of assigning throwaway local path
   aliases.
   Added a tutorial notebook hygiene regression requiring committed examples to
   stay unexecuted, with no saved cell outputs or execution counts, so
   fresh-checkout users do not inherit stale runtime state.
   Updated the configuration guide to use ``output_group`` for self-contained
   Python path resolution examples, matching the notebook workflow and avoiding
   raw ``resolve_output_path`` snippets in user-facing tutorial docs.
   Updated standard tutorial notebooks and Python workflow examples to import
   notebook helpers from the stable ``spatial_vtk.config`` package surface
   instead of the implementation module ``spatial_vtk.config.notebook``.
   Extended ``prepare_notebook_geospatial_environment()`` with optional
   ``LOKY_MAX_CPU_COUNT`` setup and moved the Step 4 tutorial notebook's direct
   environment write into that shared helper.
   Added ``NotebookFigureSettings.render_gate()`` so notebook figure blocks can
   report disabled rendering, missing input paths, and unconfigured optional
   paths consistently without loading large tables. Large-run Steps 1, 2, 4, 5,
   and 6 now use the gate for context, QC, spatial, region, and waveform figure
   prerequisites.
   Added ``spatial_vtk.io.record_coverage_readiness_from_config`` so Step 1
   notebooks can display the record-coverage rebuild decision without
   duplicating the preprocessed/base event-station fallback used by the build
   helper.
   Metrics dashboards now show an explicit row-level dataset notice in the
   dashboard body when summary tabs can render but distribution/download tabs
   cannot load filtered metric rows.
   QC dashboards now show explicit empty-state messages in the Trace Table and
   Manual Review Queue tabs when active filters remove all loaded trace rows.
   ``svtk dashboard metrics`` now labels launch output as the metrics
   dashboard row dataset and dashboard summary tables, matching the clearer
   ``--metrics-dataset-dir`` and ``--dashboard-summary-table-dir`` option
   names.
   ``dashboard_output_status_frame()`` now includes ``artifact_role`` and
   ``artifact_label`` columns so notebook status tables can show human-readable
   dashboard artifact names alongside configured path keys.
   Tutorial docs now show the editable source-checkout install command with
   ``notebooks`` and ``waveforms`` extras immediately before the clean
   notebook execution commands, so fresh-checkout verification does not depend
   on an implicit runtime setup step.
   Added ``spatial_vtk.io.preprocessed_waveform_output_group`` so Step 1 can
   use ``OutputGroup``-style ``bind()``, ``status_frame()``, and
   ``readiness()`` for preprocessing metadata under
   ``outputs.preprocessed_waveforms/metadata``. The large-run Step 1 notebook
   now uses this helper instead of direct ``output_readiness`` calls.
   Added ``metric_batch_count`` and ``preprocess_continue_on_error`` to
   ``NotebookRunContext``. Large-run Step 1 and Step 3 now use those context
   fields instead of parsing ``SVTK_PREPROCESS_CONTINUE_ON_ERROR`` and
   ``SVTK_METRIC_BATCH_COUNT`` directly in notebook cells.
   Added ``pca_mode`` to ``NotebookFigureSettings`` and updated large-run Step
   4 to use ``notebook_figure_settings("spatial")`` for ``SVTK_PCA_MODE``
   instead of parsing it in the notebook.
   Added ``run_scenario`` to ``NotebookRunContext`` and updated the large-run
   notebooks to call ``notebook_run_context()`` directly instead of parsing
   ``SVTK_RUN_SCENARIO`` in setup cells. Downstream helpers that need the
   scenario now use ``context.run_scenario``.
   Extended ``notebook_dashboard_launch_commands()`` to expose dashboard launch
   request flags from ``SVTK_LAUNCH_METRICS_DASHBOARD`` and
   ``SVTK_LAUNCH_QC_DASHBOARD``. Standard Step 2 now uses the config-backed
   launch helper instead of parsing QC dashboard port and launch variables in
   the notebook, and large-run Step 7 now uses the same helper-owned launch
   flags for metrics and QC dashboards.
   Extended ``notebook_figure_settings()`` to cover optional score-trend
   diagnostics through ``notebook_figure_settings("score_trend")``. Large-run
   Step 3 now keeps ``SVTK_MAKE_SCORE_TRENDS`` and
   ``SVTK_SCORE_TREND_COLUMNS`` as supported user controls while moving their
   parsing out of notebook cells.
   Added ``spatial_vtk.io.load_configured_input_tables`` so notebooks can load
   labeled non-output input tables from dotted config keys such as
   ``paths.metric_figure_snapshot`` and ``paths.site_metadata`` without
   repeating direct ``read_config_table`` calls in workflow cells.
   Clarified Python workflow helper return-value guidance so notebooks treat
   descriptive keys such as ``metric_manifest_path`` and
   ``geojson_region_summaries_path`` as the public contract, while generic
   aliases such as ``path``, ``output``, and ``manifest`` are documented only
   as backward-compatible internals that notebooks should not depend on.
   Clarified the API reference start points for ``spatial_vtk.io``,
   ``spatial_vtk.qc``, ``spatial_vtk.metrics``, and ``spatial_vtk.spatial`` so
   workflow users see package-level imports before lower-level implementation
   modules. The spatial package docstring now also states that plotting helpers
   live under ``spatial_vtk.spatial.plot`` and maps under
   ``spatial_vtk.spatial.map``.
   Added ``notebook_figure_settings()`` for package-native notebook figure
   controls and updated the large-run plotting notebooks to use it instead of
   parsing repeated ``SVTK_FIGURE_*`` environment variables in cells. The helper
   also preserves existing region/corridor controls such as
   ``SVTK_REGION_BOX_METRIC`` and ``SVTK_REGION_FIGURE_ROWS``.
   Updated the standard tutorial notebooks to use ``notebook_figure_settings()``
   for basemap and figure sidecar controls, matching the large-run notebooks and
   keeping figure behavior in package code rather than notebook-local
   environment parsing.
   Documented that the Python workflow page lists importable public entry
   points and added a regression that resolves every dotted helper listed there
   against the package modules.
   Clarified ``svtk dashboard metrics`` help and generated CLI reference text
   so ``--metrics-dataset-dir`` is described as the row-level
   ``metrics_dashboard`` dataset and ``--dashboard-summary-table-dir`` is
   described as the ``dashboard_summaries`` table directory used by overview
   tabs.
   Made ``svtk plot spatial directional-correlogram`` use the configured
   ``distance_bin_correlations`` table by default, matching the large-run
   spatial figure context and avoiding an unnecessary raw ``--input`` path for
   standard spatial outputs.
   Reworked ``svtk plot ... list``, ``svtk map ... list``, and
   ``svtk visualize ... list`` output as compact tables that show whether each
   command uses a ``config:<key>`` input/output, requires ``--input`` or
   ``--output``, or has optional extra table arguments.
   Made ``svtk plot metrics winner-heatmap``, ``svtk plot spatial
   residual-correlation``, and ``svtk map spatial model-improvement`` use
   config-backed input table defaults, and updated the generated CLI reference
   accordingly.
   Updated configuration documentation to show grouped output table loading
   with ``OutputGroup.load_tables()`` instead of direct ``load_output_table``
   examples.
   Added ``metric_tasks_path`` to the Step 3 output group and updated the
   standard Step 3 metrics notebook to read metric task, estimate, and long
   metric tables through ``OutputGroup.load_tables()``.
   Updated the standard and large-run Step 5/6 plotting notebooks to read
   workflow output tables through ``OutputGroup.load_tables()`` instead of
   direct ``load_output_table`` calls.
   Updated the large-run Step 1 notebook to read prepared metadata and context
   figure tables through ``OutputGroup.load_tables()`` after package workflow
   execution.
   Updated the standard and large-run Step 2 QC notebooks to read Step 1
   metadata tables and compact QC plotting summaries through
   ``OutputGroup.load_tables()`` instead of repeated ``load_output_table``
   calls.
   Added ``OutputGroup.load_tables()`` and ``OutputGroup.preview_tables()``
   for config-backed table reads from named workflow output groups. The
   standard and large-run Step 4 notebooks now use grouped table loading for
   spatial outputs instead of repeating individual ``load_output_table`` calls.
   Added ``NotebookFigureSidecarSettings.status_frame()`` and updated the
   metric and spatial notebooks to show package-native figure provenance
   review tables after plotting. The status frame reads only the small JSON
   sidecar files, reports exact/sampled row status plus source-row availability,
   and keeps notebook cells free of sidecar path plumbing.
   Added ``NotebookDashboardCommands.status_frame()`` and updated Step 7
   notebooks to display the package-generated dashboard launch plan. The launch
   preview now shows requested ports, terminal fallback commands, config path,
   and the configured metrics dataset, summary-table, and QC trace-summary
   inputs without notebook-local path plumbing.
   Made dashboard dataset writes replace recognized dashboard artifacts before
   writing new outputs. Rerunning dashboard preparation now removes stale metric
   partitions and stale cross-format summary files without deleting unrelated
   files in the dashboard output directories.
   Added a current-filter row-count summary to the metrics dashboard Data Status
   tab so blank Overview, Stations, Events, Paths, or Distributions tabs can be
   diagnosed from the running dashboard without loading full large-run tables in
   a notebook.
   Added config-backed examples to the generated ``svtk plot`` and
   ``svtk dashboard`` reference pages so users can see path-light commands for
   common plotting and dashboard workflows without guessing ``--input``,
   ``--output``, metrics dataset, or summary-table paths.
   Clarified event-centered residual figures in the large-run spatial plotting
   flow. Azimuthal, polar, and path-bin plot labels now use dataframe-aware
   value labels, and the large-run spatial context gives event-centered path
   plots explicit event-centered titles.
   Exposed tutorial-style comparison tables in the large-run generic metric
   diagnostic helper. Step 3 now forwards ``SVTK_FIGURE_COMPARE_TO`` and
   ``SVTK_FIGURE_COMPARISON_TABLE=1`` through the package plotting context
   instead of requiring notebook-local plotting logic.
   Added ``metric_slurm_submission_readiness()`` so the large-run Step 3 metric
   array submission cell uses the same ``run_notebook_step_if_needed()``
   readiness pattern as the other package-backed heavy workflow steps instead
   of calling the lower-level notebook submission helper directly.
   Added config-backed Python dashboard launch helpers,
   ``launch_configured_metrics_dashboard()`` and
   ``launch_configured_qc_dashboard()``, so notebooks can launch Streamlit
   dashboards through package functions that resolve output registry paths
   directly. The Step 7 notebooks now use those helpers when launch flags are
   enabled and keep CLI commands only as optional terminal handoff text.
   Updated the standard Step 7 dashboard notebook so dashboard dataset
   preparation stays package-helper based for tutorial data and points full runs
   to the large-run package-helper Slurm driver instead of printing a
   ``svtk metrics outputs`` command from the notebook.
   Added config-backed GeoJSON and boundary-corridor workflow helpers for
   large-run Step 5. The notebook now calls importable ``spatial_vtk.spatial``
   functions through readiness-driven package helpers and uses structured
   freshness checks that include GeoJSON and upstream tables.
   Added config-backed spatial workflow helpers for Step 4 spatial summaries
   and optional spatial plot-input tables. The large-run Step 4 notebook now
   calls importable ``spatial_vtk.spatial`` functions through readiness-driven
   package helpers instead of constructing spatial CLI commands in notebook
   cells.
   Added config-backed metric workflow helpers for waveform-inventory
   generation, task-manifest planning, metric Slurm script writing, batch
   merging, and downstream metric/dashboard output writing. The large-run Step
   3 notebook now calls importable ``spatial_vtk.metrics`` functions through
   readiness-driven package helpers instead of constructing metric CLI commands
   in notebook cells.
   Added config-backed QC notebook workflow helpers for full QC inventory
   builds, overlap sidecar creation, and compact QC summaries. The large-run
   Step 2 notebook now calls importable ``spatial_vtk.qc`` functions through
   readiness-driven package helpers instead of constructing CLI commands or
   inline Slurm worker code.
   Added package-backed notebook task execution with
   ``run_notebook_step_if_needed()`` and moved large-run Step 1
   preprocessing/record-coverage execution behind importable
   ``spatial_vtk.io`` workflow helpers. The notebook now calls Python package
   functions directly while the helper handles local execution or Slurm
   submission.
   Added metric manifest batch-status reporting and incomplete-only Slurm array
   generation, then updated large-run Step 3 to skip complete metric arrays and
   block batch merging until every expected batch output exists.
   Updated the large-run Step 2 full-QC driver to use structured readiness
   checks with ``event_station_records`` as both a required input and freshness
   source, preventing stale QC reuse after metadata regeneration.
   Preserved PSA oscillator periods, path geometry, and public value columns in
   compact spatial ``metric_field`` and ``event_centered_residuals`` outputs so
   large-run Step 4 can split PSA figures by ``period_s`` and render
   azimuth/distance plots from bounded table reads.
   Made large-run Step 3 GOF score trend figures explicitly opt-in with
   ``SVTK_MAKE_SCORE_TRENDS=1`` so the default metric plotting flow stays on
   ``log2_residual`` figures while preserving optional score diagnostics.
   Made ``svtk io inventory`` config-backed. Observed and synthetic roots now
   default from ``paths.observed_root``/``paths.observed_template`` and
   ``paths.synthetic_root``/``paths.synthetic_template``, output defaults to
   the registered ``waveform_inventory`` table, and template/glob paths are
   reduced to their static scan directory.
   Fixed CLI reference generation so ``tools/generate_cli_reference.py`` keeps
   the current plotting/mapping table guidance when regenerating
   ``docs/reference/cli_api.rst`` instead of restoring stale
   ``argument_name=path`` wording.
   Clarified metric workflow CLI path aliases. ``svtk metrics inventories``
   now exposes ``--observed-inventory-output`` and
   ``--synthetic-inventory-output``, ``svtk metrics plan`` exposes
   ``--observed-metric-inventory`` and ``--synthetic-metric-inventory``, and
   ``svtk metrics run`` exposes ``--task-table`` and ``--metric-rows`` while
   preserving the older flags.
   Clarified registered plotting CLI table help. Generated ``svtk plot``,
   ``svtk map``, and ``svtk visualize`` pages now describe primary and
   convenience tables by table role/config key instead of raw Python function
   argument names, and ``--table`` is documented as an advanced escape hatch
   with named table flags preferred when available.
   Strengthened metric figure regression coverage for large-run provenance and
   outlier handling. Tests now assert exact source event/station/period rows
   behind aggregated station and PSA sidecars, and verify that robust axis and
   color limits keep extreme outliers from dominating direct trend,
   distribution, and station-map figures.
   Hardened direct spectral metric plots. ``plot_period_spectra`` no longer
   filters generic spectra tables as PSA, direct PSA/FAS period plots now
   prefer broadband rows and reject passband-duplicated oscillator-period rows
   with a clear error, and direct metric trend/distribution plots label
   event-centered log2 residuals consistently when event-centering metadata is
   present.
   Cleaned up public docs and API entry points. The README workflow image now
   points at the committed public asset, the configuration example loads
   ``record_coverage`` before plotting it, QC Slurm settings are exposed from
   the public ``spatial_vtk.qc`` entry point, tutorial notebooks use that
   public import, and the API reference documents notebook-facing workflow,
   spatial, and visualization package entry points.
   Clarified spatial summary and derived-output table flags. ``svtk spatial
   summaries`` and ``svtk spatial derived-outputs`` now accept aliases such as
   ``--metrics-table``, ``--station-metadata-table``,
   ``--metric-field-table``, and ``--station-bias-table`` while preserving the
   older flags.
   Clarified spatial GeoJSON/corridor CLI path roles. ``svtk spatial
   geojson-summaries`` and ``svtk spatial corridors`` now accept aliases such
   as ``--metrics-table``, ``--region-geojson``, ``--records-table``, and
   ``--output-table-key`` so table keys are not confused with filesystem
   paths.
   Clarified QC output path flags. ``svtk qc build`` and ``svtk qc slurm``
   now accept ``--qc-trace-summary-output``, ``--qc-inventory-output``, and
   ``--qc-overlap-inventory-output`` aliases, and generated QC Slurm scripts
   use those artifact-named flags while preserving the older output flags.
   Clarified ``svtk metrics outputs`` path roles. The command now accepts
   ``--metric-rows``, ``--metrics-output-dir``, ``--event-table``, and
   ``--station-table`` aliases, and config-backed runs automatically use
   existing ``prepared_events`` and ``prepared_stations`` tables when the user
   does not pass metadata paths explicitly.
   Cleaned up public tutorial documentation and large-run notebook setup.
   The docs now describe the committed NPZ tutorial waveform subset, the
   workflow diagram lives under ``docs/_static/``, large-run Step 1 and Step 2
   define ``SVTK_ADD_BASEMAP`` before optional figure rendering, and the Step 2
   full-QC submission no longer reruns just because the overlap sidecar is
   missing.
   Made metric batch merging tolerate output directories. ``svtk metrics
   merge-batches --output`` and ``merge_batch_outputs()`` now write
   ``metric_rows.parquet`` inside an existing or directory-style output path,
   while explicit file paths keep their existing behavior.
   Clarified registry-backed figure CLI path flags. ``svtk plot``,
   ``svtk map``, and ``svtk visualize`` commands now accept
   ``--input-table`` and ``--figure-output`` as clearer aliases for
   ``--input`` and ``--output``, with help text that identifies the primary
   input table while preserving existing command forms.
   Clarified dashboard CLI path options. ``svtk dashboard metrics`` now accepts
   ``--metrics-dataset`` and ``--dashboard-summary-dir`` aliases, and
   ``svtk dashboard qc`` accepts ``--qc-trace-summary``, while preserving the
   older root/path flags for compatibility.
   Hardened metrics-dashboard startup for large or partial dashboard outputs.
   The Streamlit app now runs bounded summary readiness before loading full
   summary tables and skips not-ready optional summaries with schema-correct
   empty frames so available tabs can still render.
   Added large-run Step 4 PCA-summary parity with the standard tutorial. The
   spatial figure context now exposes ``write_pca_summary_plots()``, and the
   large-run spatial notebook renders combined PCA station-score, explained
   variance, and feature-loading sheets with layered row sidecars.
   Added large-run Step 3 score-trend parity with the standard tutorial. The
   metric figure context now projects GOF score columns, exposes a
   ``write_score_trend_plots()`` helper, and the large-run metric notebook
   renders configurable score trend figures through that helper.
   Added a bounded startup preflight to the QC Streamlit dashboard. The app now
   checks the configured QC trace-summary table headers and row count before
   loading the full table, showing a readiness message for missing, empty, or
   schema-bad inputs.
   Added collapsed-dimension metadata to large-run station metric figure
   sidecars. Station-summary JSON now records which metric dimensions were
   averaged or otherwise collapsed into each plotted station value, plus unique
   counts for those dimensions in the source rows.
   Simplified the large-run Step 7 dashboard driver so the notebook uses
   config-backed dashboard status, submits
   ``write_configured_dashboard_datasets()`` through the package-function
   notebook helper, and previews ``metrics_long`` through
   ``preview_output_table("metrics_long")`` instead of expanding configured
   dashboard paths or building metric-output CLI commands in task cells.
   Added ``write_configured_dashboard_datasets()`` as a config-backed helper
   for writing the metrics dashboard dataset and dashboard summary tables in
   one call. The Step 7 dashboard notebooks now use this helper instead of
   spelling out dashboard dataset roots or metric-output command arguments in
   notebook cells.
   Made ``svtk metrics run`` config-backed for small local metric runs. The
   command now defaults ``--tasks`` to the configured ``metric_tasks`` table and
   ``--output`` to ``metric_rows`` when a config is passed or set with
   ``svtk config set``, matching the rest of the metric workflow commands.
   Added bounded QC dashboard trace-summary readiness diagnostics to
   ``dashboard_output_status_frame()``, ``dashboard_output_readiness()``, and
   ``svtk dashboard status``. Status output now reports whether the configured
   QC trace table exists, has the required ``event_id``/``station`` columns,
   and contains rows without loading the full table.
   Tightened large-run metric figure provenance for sampled station maps.
   When a station-level map samples aggregated station rows before plotting,
   the optional ``*.source.csv`` sidecar is now filtered to the raw metric rows
   behind those plotted station groups rather than the full unsampled metric
   selection. Step 3 notebook text now describes the configurable station
   aggregation method instead of saying station maps always use medians.
   Wired the large-run Step 2 QC notebook to the standard
   ``qc_availability`` table and availability figure so observed/synthetic
   post-QC overlap can be rendered without loading the full inventory. The
   availability heatmap now uses sparse labels and capped figure dimensions
   for large datasets, and the event-station retention heatmap now writes to
   the distinct ``event_station_retention`` figure output instead of sharing
   the availability filename.
   Hardened metric plotting compatibility for older pandas and Matplotlib
   environments by avoiding pandas 2-only ``DataFrame.map`` calls and falling
   back to Matplotlib's legacy boxplot label keyword when needed.
   Added a public ``preprocessed_waveform_metadata_paths()`` helper so
   notebooks and scripts use the same config-backed preprocessing metadata
   paths as ``preprocess_waveform_files()``. Large-run Step 1 and Step 3 now
   use that helper instead of rebuilding ``preprocessed_waveforms/metadata``
   paths by hand, and the Step 1 readiness table now checks the actual
   ``waveform_preprocessing_manifest.csv`` filename written by preprocessing.
   Aligned the large-run Step 3 station-map default with the standard tutorial:
   station-level metric maps now average selected event rows by default via
   ``SVTK_STATION_AGGREGATION=mean`` while keeping the environment override for
   median or percentile summaries. Notebook regression coverage now also
   requires source-row sidecar wiring for station, residual-grid, and
   metric-by-model map cells.
   Expanded figure sidecar JSON metadata with plot/source column lists and
   counts, sidecar row limits, sampling seed, source-row availability, and
   source-sidecar write status. This makes it easier to audit whether a figure
   sidecar contains raw rows, transformed plot rows, or a sampled subset.
   Made ``svtk plot metrics model-metric-heatmap`` config-backed for standard
   metric workflows. The command now defaults its input to ``metrics_long`` and
   the plotting function falls back from summary-only ``med_resid`` to common
   long-table value columns such as ``log2_residual`` when needed.
   Registered the standard ``pattern_similarity_station_anomalies`` table and
   made ``svtk plot spatial pattern-similarity`` resolve that input and the
   ``pattern_similarity`` figure path from config. The plot CLI also exposes
   ``--bin-label`` as a first-class option for helpers that require a named
   period/bin selection.
   Added a standard ``qc_availability`` table to the QC summary workflow and
   made ``svtk visualize qc data-synthetic-availability`` resolve it from the
   active config. The availability table records post-QC observed/synthetic
   availability by overlapping event-station pair.
   Added named status rows and pandas status frames to ``OutputReadiness`` so
   large-run notebook driver cells can display exactly which inputs, outputs,
   and source dependencies are missing, stale, current, or intentionally
   ignored without rebuilding path tables by hand.
   Hardened PSA contact-sheet figure sidecars in large-run metric notebooks.
   Re-running a PSA sheet cell now refreshes sidecars from the same per-period
   panel rows used during rendering, including raw source-row sidecars for
   station-aggregated sheets. Fresh PSA-sheet renders now also write sidecars
   for empty plotted-row selections so audit files can distinguish no data from
   no sidecar request.
   Made zero-column figure sidecars CSV-readable by writing a marker column for
   otherwise unrepresentable empty sidecar tables while keeping true row counts
   in the JSON metadata.
   Reduced dashboard summary generation memory use for large metric datasets.
   Summary builds now project only the columns required for grouping, values,
   and path geometry instead of reading every metrics-long payload column.

2026-06-16
   Hardened metrics dashboard optional tabs so missing, empty, or value-less
   station/event/path summary tables show their dashboard-readiness message in
   the affected tab instead of a generic filtered-empty message.
   Hardened QC dashboard chart tabs so filtered-empty trace tables show an
   explicit empty-state message and do not attempt to render blank histogram or
   band-content charts.
   Simplified tutorial and large-run notebook sidecar plumbing. Figure cells
   now pass ``**sidecar_settings.kwargs()`` or
   ``**sidecar_settings.kwargs(plural=True)`` instead of expanding sidecar
   settings into repeated ``write_sidecar``/``sidecar_rows``/``sidecar_dir``
   variables, keeping notebooks task-focused while preserving optional plotted
   row and source-row provenance files.
   Added ``notebook_dashboard_launch_commands()`` so tutorial and large-run
   dashboard notebooks print the same config-backed launch commands as the CLI
   defaults. Notebook dashboard commands now include ``--auto-port`` by default
   and expose port/proxy options through environment variables instead of
   notebook-local command assembly.
   Added ``--auto-port`` to metrics and QC dashboard launch commands. The
   dashboard launcher can now select the first available Streamlit port at or
   above the requested ``--port`` and prints the actual URL, which makes
   dashboard startup less brittle on shared systems where default ports are
   already occupied. Dashboard proxy-mode examples now recommend using
   ``--auto-port`` together with ``--proxy-mode``.
   Hardened large-run station aggregation for metric and spatial maps against
   non-canonical table schemas. Station-level map summaries now recognize
   ``station_id`` and ``station_code`` as station identifiers, ``station_lon`` /
   ``station_lat`` and ``station_longitude`` / ``station_latitude`` as station
   coordinates, and ``event`` / ``event_title`` as event identifiers for audit
   counts. Aggregated map rows are still normalized back to ``station``,
   ``sta_lon``, and ``sta_lat`` for plotting, while sidecar metadata records
   the original grouping and coordinate columns used for provenance.
   Hardened clean standard tutorial execution for source checkouts. The
   preprocessing workflow now prefers canonical config-generated waveform
   columns over legacy format-specific metadata columns when both exist, so
   ignored local MiniSEED files cannot mask the committed NPZ tutorial subset.
   Standard metric and map tutorials now make external basemap fetching opt-in
   with ``SVTK_ADD_BASEMAP=1``, avoiding warning output in fresh checkouts
   without ``contextily`` or tile access. The tutorial notebook executor now
   keeps Jupyter/IPython runtime files under ignored tutorial outputs and
   starts kernels with quieter logging so clean runs do not emit TCP-kernel
   warnings.
   Made large-run metric plotting context column-aware: Step 3 metric figures
   now load only columns required by the registered diagnostic plots and apply
   default component/model filters at context load time, reducing memory
   pressure without truncating selected rows used for station-map aggregation.
   Hardened large-run station metric map aggregation so representative station
   coordinates are computed from all selected source rows, not only finite
   metric-value rows. Station-map sidecar metadata now also records input and
   finite station/event counts for aggregation audits.
   Added first-class ``--table`` / ``--no-table``, ``--station-region``,
   and ``--event-region`` controls for registered plotting and mapping
   commands. The CLI workflow now uses named flags instead of routine
   ``--kwargs`` plumbing, while ``--table argument_name=path`` remains
   available for extra input tables.
   Added ``tools/execute_tutorial_notebooks.py`` so source checkouts and CI can
   execute the standard tutorial notebooks from a clean
   ``outputs/tutorials`` directory and fail on notebook errors or warning-like
   cell output. The source-install notebook extra and conda environment now
   list ``nbclient`` and ``nbformat`` explicitly.
   Added config-backed dashboard output helpers that report the metrics
   dashboard root, dashboard summary root, QC trace table, and per-tab summary
   files in one status table. The dashboard CLI now uses the configured
   ``outputs.dashboards`` roots by default, and Step 7 notebooks use the shared
   helper instead of spelling out each dashboard path.
   Added user-facing artifact roles and labels to compact dashboard readiness
   summaries and Streamlit Data Status tables so large-run notebook preflight
   output can explain dashboard artifacts without exposing only internal path
   keys.
   Added sample-data coverage for dashboard summary contribution counts,
   asserting that ``n``, ``event_count``, and ``station_count`` describe the
   metric rows, events, and stations behind each aggregate.
   Added shared large-run notebook helpers for package-backed heavy work. The
   older CLI-wrapper helper is now a deprecated compatibility fallback, and the
   large-run QC, metrics, spatial, GeoJSON, and dashboard drivers use
   importable package-function tasks for their repeated heavy-work cells.
   Extended large-run metric figure sidecars with event, station, component,
   model, metric, passband, and PSA-period counts for both plotted rows and
   source rows. Metric-by-model maps now aggregate rows by station and model
   before plotting, with raw metric rows preserved in the optional source
   sidecar.
   Extended the same station-level aggregation and source-row sidecar pattern
   to large-run spatial metric maps. Spatial ``metric_field`` outputs with
   ``lon``/``lat`` coordinates are now normalized to the canonical
   ``sta_lon``/``sta_lat`` plotting schema before station maps, residual
   grids, and model-faceted maps are rendered.
   Tightened large-run notebook sidecar plumbing so optional figure row
   sidecars use the shared ``notebook_figure_sidecar_settings`` directory
   instead of hardcoded ``figures/sidecars`` paths.
   Replaced tutorial notebook output-path dictionary indexing with
   namespace-style helpers for grouped workflow outputs and dashboard outputs,
   keeping path resolution config-backed while reducing setup-cell plumbing.
   Updated the Python workflow docs and ``OutputGroup.bind`` docstring so new
   notebook examples prefer direct output-group attributes over injecting
   resolved paths into ``globals()``.
   Updated the large-run notebooks to use direct ``OutputGroup`` attributes for
   configured paths instead of binding output paths into notebook globals, and
   added notebook regression coverage to keep grouped path ownership explicit.
   Clarified the metrics and spatial API reference so notebooks and scripts
   import plotting helpers from stable public package entry points such as
   ``spatial_vtk.metrics.plot`` and ``spatial_vtk.spatial.map``. Updated the
   metrics-dashboard CLI help to describe config-backed dashboard output roots
   rather than stale table-directory examples.
   Trimmed the metrics API plotting reference to the stable
   ``spatial_vtk.metrics.plot`` entry point so docs no longer direct notebook
   users to plotting implementation modules.
   Trimmed the spatial API plotting and map references to the stable
   ``spatial_vtk.spatial.plot`` and ``spatial_vtk.spatial.map`` entry points,
   including path-map helpers, so public docs no longer point users at
   implementation modules.
   Updated the large-run spatial statistics notebook to import
   ``prepare_spatial_figure_context`` from the public
   ``spatial_vtk.spatial.plot`` entry point and expanded notebook regression
   coverage to reject internal plotting module imports.
   Updated the configuration guide's station-metric map override example to
   use first-class ``--value-col`` and ``--metric`` flags instead of routing
   routine plotting controls through ``--kwargs``.
   Added first-class ``--connect-points`` / ``--no-connect-points`` plotting
   flags and updated the shell workflow residual-distance example to use the
   named flag instead of ``--kwargs connect_points=false``.
   Added a first-class ``--mode`` plotting flag and updated the shell workflow
   PCA map example to use ``--mode PC1`` instead of ``--kwargs mode=PC1``.
   Added first-class ``--dep``, ``--indep``, ``--colorby``, and
   ``--compare-to`` plotting flags for flexible spatial plots, and updated
   shell workflow scatterplot, boxplot, and heatmap examples to use them.
   Added first-class waveform figure flags for ``--components``, ``--scale``,
   ``--time-limit-s``, ``--max-records``, and ``--max-traces``. The CLI
   workflow examples now use these supported controls instead of stale
   ``--kwargs`` aliases such as ``gain``, ``xlim_s``, ``max_time_s``, and
   ``lowpass_hz``.
   Added explicit aggregation provenance to large-run station metric figure
   sidecars. Station summary dataframes now record the source value column,
   aggregation method, grouping columns, coordinate columns, input row count,
   and finite row count; the JSON sidecar persists that contract alongside the
   sampled plotted/source rows.
   Hardened the tutorial notebook executor's warning scan so clean diagnostic
   text such as ``warnings=0`` does not fail fresh-checkout notebook runs,
   while real warning signatures such as ``RuntimeWarning:`` and
   ``WARNING:`` still fail unless explicitly allowed.
   Added map-coordinate readiness checks for metrics dashboard station/event
   summaries. Dashboard status tables now report missing map coordinate
   columns separately from value-table readiness, and the Streamlit station and
   event tabs show an explanatory message instead of attempting to render a map
   from tables without usable longitude/latitude pairs.
   Extended the dashboard summary-table contract with map-coordinate
   requirements, so Step 7 notebooks show which station/event longitude and
   latitude columns feed the dashboard map tabs before launch.
   Added per-station finite-value drop counts to large-run metric figure
   aggregation outputs. Optional station-map sidecars now show, for each
   plotted station summary, how many selected metric rows and events were
   excluded because the plotted value was non-finite.
   Improved notebook output-status tables so grouped output namespaces keep
   their artifact names and bare path lists use filename-derived labels instead
   of opaque ``path_0`` entries.
   Improved ``output_readiness()`` messages so mapping and grouped-output
   inputs retain names such as ``metrics_long`` or ``qc_inventory_overlap``
   when notebooks explain missing, stale, current, or overwrite decisions.
   Added a dashboard summary-table contract helper that maps each metrics
   dashboard tab to its required summary file and columns. Dashboard output
   status tables and Step 7 notebooks now show this contract alongside file
   readiness so missing dashboard tabs are easier to diagnose.
   Expanded config-backed defaults for registered ``svtk plot``, ``svtk map``,
   and ``svtk visualize`` commands. Standard context, QC, waveform, metric,
   and spatial-statistics figures now resolve their usual input tables and
   figure paths from the active config when ``--input`` or ``--output`` is
   omitted, and multi-table context maps can also resolve their standard
   station/event alias tables from the config.
   Rewired the standard Step 2 QC notebook to use the shared
   ``output_group_paths("step_02_qc")`` helper for QC, overlap, and
   comparison-eligible outputs instead of resolving those paths one by one.
   Added ``notebook_figure_sidecar_settings()`` so standard and large-run
   notebooks use one parser for optional figure row-provenance sidecars instead
   of duplicating environment-variable handling in setup cells.
   Tightened large-run station metric map aggregation so event-level rows are
   grouped by station, period, and model rather than by station-coordinate
   pairs. Station coordinates are now summarized separately and optional
   figure sidecars record coordinate multiplicity, source row counts, and
   source event counts for auditing.
   Figure row-provenance sidecar metadata now records ``plot_rows_role`` and
   ``source_rows_role`` consistently, so users can tell whether each CSV
   contains plotted rows, post-aggregation station summaries, or raw
   pre-aggregation metric rows.
   Hardened ``tools/execute_tutorial_notebooks.py`` with an upfront notebook
   runtime dependency preflight. The tutorial execution gate now reports
   missing ``nbformat``, ``nbclient``, ``ipykernel``, or ``IPython`` modules
   before cleaning ``outputs/tutorials`` or attempting notebook execution.
   Added a CI contract test requiring the source-checkout workflow to install
   notebook extras and execute the standard tutorial notebooks from a clean
   tutorial output directory.
   Added optional row-provenance sidecars to GeoJSON region maps and corridor
   maps, and wired the standard and large-run tutorial notebooks so every
   saved direct plotting call can emit the plotted rows when sidecars are
   enabled.
   Added first-class ``--write-sidecar``, ``--sidecar-rows``, and
   ``--sidecar-dir`` flags to registered ``svtk plot``, ``svtk map``, and
   ``svtk visualize`` figure commands. Trace sample and distance/amplitude
   diagnostic figures now support the same row-provenance sidecar interface.
   Added first-class common plotting flags such as ``--metric``,
   ``--passband``, ``--component``, ``--model``, ``--value-col``,
   ``--score-col``, ``--x-col``, ``--y-col``, ``--group-col``,
   ``--color-col``, ``--fit``, and ``--title`` to registered figure
   commands so routine figure configuration does not need to be hidden inside
   ``--kwargs``.
   Added dashboard summary readiness diagnostics. Dashboard status tables now
   report whether each summary table is missing, empty, schema-invalid,
   missing finite value data, or ready, so notebooks can explain blank
   dashboard tabs before Streamlit is launched.
   The metrics Streamlit dashboard now displays those readiness diagnostics
   and stops before building sidebar filters when the primary
   ``model_metric_band`` summary is not usable.
   Optional metrics-dashboard station, event, and path tabs now handle summary
   tables that lack the selected value column by showing a clear empty-state
   message instead of raising during dashboard rendering.
   Dashboard long-metric loading now accepts either a dashboard dataset
   directory or a direct CSV/Parquet metrics table, and the dashboard CLI help
   documents both accepted forms.
   Metrics-dashboard row-level distribution plots now use a shared
   summary-to-row value-column resolver for median/mean summary columns, and
   show a clear message when the loaded long metric table lacks the requested
   row-level value.
   Documented the public figure-sidecar contract in the visualization API
   reference and added an import regression test so dashboard readiness/filter
   helpers and figure sidecar helpers remain available without importing the
   optional Streamlit app modules.
   Figure sidecar metadata now counts common event, station, passband, metric,
   model, component, and PSA-period column aliases so JSON provenance remains
   informative for both ``band``/``passband`` and canonicalized station/event
   table variants.
   ``plot_event_residual_map()`` now supports the shared
   ``write_sidecar``/``sidecar_rows``/``sidecar_dir`` plotting options so
   event-map provenance works consistently for direct Python calls, CLI-routed
   plotting, and large-run notebook wrappers.
   GitHub CI and docs workflows now install the ``notebooks`` extra wherever
   tutorial execution or notebook-backed docs checks are part of the public
   source-checkout validation path.
   Registered ``svtk plot`` and ``svtk map`` commands now resolve plotting
   functions through the stable public ``spatial_vtk.metrics.plot``,
   ``spatial_vtk.spatial.plot``, and ``spatial_vtk.spatial.map`` import
   surfaces instead of implementation submodules.
   Public metric trend, Vs30, score-map, and model-improvement plotting
   wrappers now expose ``write_sidecar``, ``sidecar_rows``, and
   ``sidecar_dir`` directly in their signatures so generated docs and
   interactive help show the row-provenance controls.
   Updated the generated CLI reference introduction so standard plotting
   workflows are documented as config-backed commands with first-class
   plotting flags, while ``--kwargs`` is described as an advanced escape hatch
   rather than the normal interface.
   Added first-class ``svtk qc build`` and ``svtk metrics estimate`` commands
   so the shell workflow tutorial no longer needs generic ``svtk call`` for
   routine QC inventory generation or metric task resource summaries.
   Tightened Step 1 tutorial and large-run notebook figure sidecar calls so
   every figure that enables row-provenance sidecars also passes the configured
   sidecar directory. Added a notebook regression to keep sidecar directory
   controls from being dropped.
   Added a tutorial example-data preflight to
   ``tools/execute_tutorial_notebooks.py``. The clean tutorial execution gate
   now checks the committed five-event metadata, metric snapshots, and
   observed/synthetic NPZ waveform subset before deleting ``outputs/tutorials``
   or starting notebook execution.
   Added a tutorial-notebook regression that rejects committed notebook cells
   containing private/local cluster paths or host names, keeping public
   notebooks runnable from a fresh source checkout.
   Cleaned the large-run notebooks so remaining Step 2/3/4/5 path lookups use
   grouped config-backed output paths instead of notebook-local
   ``resolve_output_path`` calls, including the metric-output station/event
   inputs and the overlap drop-cause figure path.
   Cleaned the standard tutorial notebooks the same way: Step 2 now gets the
   overlap drop-cause and waveform comparison figure paths from the Step 2
   output group, and a notebook regression prevents inline
   ``resolve_output_path`` calls from returning.

2026-06-09
   Released ``0.1.3`` to publish the PyPI README workflow-image fix after
   external Sigstore/Rekor ``502`` errors blocked the ``0.1.2`` publish.

2026-06-09
   Released ``0.1.2`` to refresh PyPI project metadata so the README workflow
   image uses an absolute GitHub-hosted URL that renders on PyPI.

2026-06-09
   Released ``0.1.1`` to refresh PyPI project metadata so the package page
   points readers to the public GitHub Pages documentation.

2026-06-08
   Added a QC-to-metrics valid-window contract. Waveform QC now records
   processing-valid trace intervals, metric QC preserves those intervals, and
   metric execution trims scalar, pair, and spectral calculations to valid
   samples so edge transients from filtering or resampling do not control
   metric values.
   Reduced the automatic waveform-QC default noise-window minimum from
   10 seconds to 1 second. The actual noise window is still at least as long as
   the requested period band.
   Preserved waveform source labels in PhaseNet arrival-pick catalogs and
   allowed waveform QC to anchor noise and signal windows to a source-specific
   PhaseNet P pick when a pick catalog is supplied, falling back to the
   envelope onset when no pick is available.
   Allowed waveform-QC noise windows to sample finite preprocessed data outside
   the metric-valid interval while keeping signal metrics constrained to the
   valid interval. This lets SNR reject traces with noisy or artifact-dominated
   pre-signal windows without failing them solely for ``insufficient_noise_window``.
   Added a PhaseNet-pick plausibility gate in waveform QC: a picker onset is
   used only when its signal window has enough finite samples inside the
   metric-valid interval; otherwise QC falls back to the envelope onset.

2026-06-03
   Added a public Data Formats page with minimal input requirements, optional
   metadata and GeoJSON guidance, example downloadable input/output snippets,
   and basemap-backed preview images for common Spatial-VTK outputs. Added
   lightweight LA Basin example metadata plus a public dataset manifest under
   ``data/examples/`` for source checkout and tutorial setup. Scrubbed the
   public example manifest so it uses source-checkout paths and public
   provenance labels, and expanded the example residual-distance plot so each
   metric has multiple distance samples.
   Clarified spectral QC reason labels so requested periods are not described
   as frequencies, regenerated the example QC preview, replaced the site
   metadata preview with rows derived from actual LA Basin metadata products,
   and simplified the dashboard output section to show the dashboard screenshot
   without a mismatched CSV preview.
   Rebuilt the Installation page from the public-release checklist, separating
   conda environment creation from source/PyPI package installation, and made
   ``svtk_environment.yaml`` dependency-only so it can be downloaded and used
   before installing the package.
   Revised the Installation page so the primary install path is
   ``python -m pip install spatial-vtk``, moved PyPI installation before source
   installation, moved development extras into a collapsible advanced section,
   and made dashboard dependencies part of the default package install.
   Restored the conda-environment-first installation layout while keeping the
   main PyPI command as ``python -m pip install spatial-vtk`` and placing the
   development extras disclosure at the bottom of the PyPI section.
   Added the Configuration page with a commented downloadable YAML example,
   config discovery instructions, config precedence rules, and concise checks
   for active config sections and named bounds.
   Revised configuration handling and docs so metric selection is explicit:
   choose either metric groups or specific metrics, with ``all`` accepted for
   either mode. Added a shared public metric catalog, normalized legacy C-code
   config selections to public metric names, added reusable ``run_scenarios``
   config overlays, and exposed scenario/one-run overrides through Python and
   relevant ``svtk`` commands.
   Reworked the Package Overview page from a dense module inventory into a
   workflow-oriented guide with a step table, short module sections, grouped
   task lists, and clear links to data formats, configuration, examples, and
   reference pages.
   Cleaned the six tutorial notebooks so they use the activated tutorial
   config, shared default output registry, standard ``write_output_table``
   table writes, and ``load_output_table`` reads instead of notebook-local
   output path manifests. Added zipped notebook downloads to the rendered docs
   pages, hardened lazy import surfaces for metric plotting and spatial maps,
   and fixed post-QC event-coordinate handling for the QC map workflow.
   Further simplified tutorial notebook setup by adding ``read_config_table``
   and ``load_output_table``, letting metric settings resolve from the active
   config, and giving QC, metric-workflow, and dashboard helpers active-config
   defaults for common paths.
   Let metadata preparation helpers read station, event, and event-station
   tables from the active config when no dataframe is passed, so tutorials can
   use concise calls like ``prepare_station_metadata()``.
   Removed final written-file manifest blocks from the tutorial notebooks.
   Standard outputs are now written where they are created with
   ``write_output_table`` or ``write_output_tables``, and later notebooks read
   those products by key with ``load_output_table``.
   Added concise comments before the main package function calls in each
   tutorial notebook so readers can follow what each workflow call does without
   extra prose between cells.
   Renamed the tutorial-facing output loader to ``load_output_table`` and the
   metric workflow writer to ``write_metric_outputs``. Simplified Step 4 so
   spatial-statistics functions resolve metric/value selection, event-centering
   settings, Moran settings, clustering, PCA, GeoJSON, and geology-contrast
   options from the active config. ``summarize_station_bias`` now accepts both
   raw metric fields and event-centered fields, with event-mean removal kept as
   an explicit optional step.
   Clarified Step 4 geology-contrast handling: contrast tables now record the
   grouping column, compared class sets, contrast label, effect direction, and
   value column, and the tutorial now creates a geology-contrast figure that
   visualizes the two residual distributions and bootstrap uncertainty.
   Added shared dashboard/table display helpers so notebook previews, Streamlit
   tables, figures, and future CLI previews use one human-readable label lookup
   instead of notebook-local column rename dictionaries.
   Added a new Step 6 tutorial for additional plotting options, including a
   QC-passed station-event waveform map, observed/synthetic pattern similarity,
   and flexible scatterplot, boxplot, and heatmap examples. The dashboard
   tutorial is now Step 7. Waveform-map helpers now support event-origin time
   alignment, distance sorting, and explicit time windows, and the spatial
   pattern helper can build station-anomaly rows directly from long metrics
   tables.
   Replaced per-cell tutorial timing magics with one-time automatic notebook
   timing registration. Tutorial notebooks now call
   ``register_svtk_cell_timer()`` once and still show compact ``Run time: ...``
   output after each code cell.
   Updated signed residual/log-ratio/mean-centered map figures to use a
   zero-centered ``seismic`` divergent colorscale by default. Added a Step 4
   spatial-correlation-by-distance figure that compares PGA and FAS
   distance-bin correlations and marks metrics with significant Moran
   permutation-test results.
   Replaced the Step 5 tutorial GeoJSON regions with public example polygons
   for LA Basin, East LA, and Santa Monica Mountains, regenerated the Step 5
   notebook output, and updated corridor maps so they draw the selected
   event-station paths for each corridor definition. The
   outward-corridor residual map now overlays the highlighted corridor,
   selected events, selected paths, and station residuals together.
   Cleaned the Step 6 waveform-map tutorial so it no longer displays internal
   trace-start offset columns. Station-event waveform maps now use observed or
   synthetic event-origin offsets automatically when those columns are present,
   keeping tutorial code focused on the fact that ``t=0`` is the event origin.
   Updated the Step 6 flexible boxplot and heatmap examples so they use the
   real tutorial GeoJSON regions: LA Basin, East LA, and Santa Monica
   Mountains. Generic display labels now preserve common acronyms such as
   LA, GeoJSON, QC, and Vs30, and bottom comparison tables leave more room for
   long region names.
   Fixed notebook figure display during headless docs execution. Plot helpers
   now emit explicit PNG payloads when ``showfig=True`` is used in a notebook
   kernel, and the Step 5 and Step 6 tutorial pages now render their saved
   map and figure outputs in the Sphinx HTML.
   Reorganized the Python API reference into grouped module/submodule pages
   for configuration, I/O, quality control, metrics, spatial analysis, and
   visualization so the reference section can be browsed by workflow area
   instead of as one long function list.
   Expanded the CLI API reference into generated command-group pages derived
   from the live ``svtk`` parser, including all available subcommands,
   required arguments, repeatable options, defaults, and choices. Added a CLI
   Workflow Tutorial page that mirrors the seven notebook tutorials as shell
   commands for config, preprocessing, QC, metrics, spatial figures, GeoJSON
   and corridor figures, flexible plots, and dashboards.

2026-06-02
   Started the public Spatial-VTK migration skeleton.
   Added public spatial-statistics calculation modules for metric preparation,
   station bias, Moran's I, distance-bin correlations, spatial holdout,
   residual-feature clustering, REDCAP clustering, geology-class joins,
   PCA spatial modes, bootstrap contrasts, permutation Moran tests, and
   observed/synthetic pattern similarity.
   Added companion plot and map wrappers for correlograms, semivariograms,
   directional correlation, holdout scatter/error maps, cluster summaries,
   PCA variance/loadings diagnostics, PCA mode maps, station-bias maps, REDCAP
   maps, and pattern-similarity plots.
   Added public metadata preparation, observed/synthetic file inventory, and
   basic context-figure helpers to support the first example notebook scaffold.
   Added public foundation helpers for model naming, frequency bands, waveform
   spectra/filtering, KML export, layout inspection, metric-table reshaping,
   catalog readers, and synthetic model alias resolution.
   Added public QC helpers for trace-inventory lookup/filtering, event
   inventory discovery, companion QC summary rows, station-family
   classification, reject-rule evaluation, and manual-review queue table
   construction.
   Added public metric batch calculation, arrival-pick catalog normalization,
   long residual-table preparation, metadata enrichment, and deterministic
   metric example plots.
   Added dashboard preparation tables that consume metric residual outputs and
   build model/metric/band, station, event, and path-bin summaries.
   Added path-oriented spatial helpers for source-station geometry, residual
   distance/azimuth binning, NE/RT rotation, and event residual maps.
   Added general GeoJSON polygon controls for station/event membership,
   path boundary crossings with direction, path start/end membership,
   polygon-based metric summaries, and cleaned-up station-edge corridor/event
   selection wrappers.
   Added parameterized boundary-corridor helpers for inward, outward, and
   through-boundary corridors, anchor selection from boundary segments or
   station/event metadata, station/event/path corridor filters, and static
   corridor maps with station, event, and path context.
   Added a public runtime configuration layer for loading YAML/JSON project
   configs, resolving paths and named bounds, merging run defaults, planning
   deterministic output artifacts, writing artifact manifests, and reading
   metric calculation plans from config.
   Added optional Streamlit dashboard app support with Folium maps, Plotly
   charts, dashboard schema validation, human-readable public metric and
   transform labels, selectable observed/synthetic/residual/GOF value columns,
   filtered export helpers, and manual-review queue exports compatible with
   the manual QC picker.
   Added shared public metric, transform, and passband labels for dashboard,
   plotting, mapping, and future CLI output.
   Added reusable figure-selection helpers so plots can consistently apply
   configured passbands, components, events, stations, and bounds.
   Updated metric plots, spatial plots, maps, dashboard summaries, QC
   dashboard controls, waveform figures, record sections, and context figures
   to support the renamed metric scheme and selectable observed/synthetic,
   residual, log-residual, and GOF value columns.

Future Work
-----------

Planned additions are tracked in :doc:`future_features`.

.. toctree::
   :maxdepth: 1
   :hidden:

   future_features
