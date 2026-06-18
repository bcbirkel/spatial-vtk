Changelog
=========

2026-06-17
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
   Added shared large-run notebook helpers for package-backed heavy work. The
   older helper can still wrap Spatial-VTK CLI calls when needed, but the
   large-run QC, metrics, spatial, GeoJSON, and dashboard drivers now use
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
   Clarified the metrics and spatial API reference so notebooks and scripts
   import plotting helpers from stable public package entry points such as
   ``spatial_vtk.metrics.plot`` and ``spatial_vtk.spatial.map``. Updated the
   metrics-dashboard CLI help to describe config-backed dashboard output roots
   rather than stale table-directory examples.
   Trimmed the metrics API plotting reference to the stable
   ``spatial_vtk.metrics.plot`` entry point so docs no longer direct notebook
   users to implementation modules such as
   ``spatial_vtk.metrics.plot.periods``.
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
