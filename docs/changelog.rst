Changelog
=========

2026-06-19
----------

- **Config-path workflow stabilization** *(Changed)*

  - Standard output resolvers, output groups, table IO helpers, preprocessing
    helpers, metric result objects, Step 4 spatial workflow helpers, and
    dashboard contract helpers now accept either config objects or config file
    paths through ``cfg=``.
  - Step 5 GeoJSON plotting/status helpers and Step 6 additional plotting
    helpers now preserve path-valued ``cfg=`` inputs for output previews,
    figure writers, and result-owned workflow runner methods.
  - Tutorial notebook source preflight now rejects hard-coded
    ``Path('../')`` repo-root setup cells so public notebooks keep using the
    shared source-checkout bootstrap and config-context helpers.
  - ``svtk dashboard qc`` now presents ``--qc-trace-summary`` as the canonical
    override flag in help and generated CLI docs while preserving
    ``--trace-summary`` as a legacy alias.
  - QC build/Slurm and metric-row workflow commands now present artifact-named
    output flags first in help and generated CLI docs while preserving generic
    aliases for existing scripts.
  - Metric inventory and downstream metric-output commands now present
    inventory/table-specific flags first in help and generated CLI docs while
    preserving shorter legacy aliases for existing scripts.
  - Spatial summary, derived-output, GeoJSON, and corridor commands now present
    table/path-specific flags first in help and generated CLI docs while
    preserving older generic aliases for existing scripts.
  - Registered plot, map, and visualization commands now present
    ``--input-table`` and ``--figure-output`` as their canonical explicit path
    overrides while preserving ``--input`` and ``--output`` for existing
    scripts.
  - Human-readable spatial and dashboard status commands now label resolved
    filesystem targets as ``resolved_path`` so terminal output matches the
    notebook readiness tables.
  - Dashboard readiness attachments and stale-output checks now resolve
    summary-table, metric-dataset, and QC-trace paths from ``resolved_path``
    first, while retaining compatibility with the legacy ``path`` alias.
  - Metrics and QC dashboard status tables now display ``resolved_path`` rather
    than the legacy ``path`` alias, while keeping large-table status displays
    bounded to the readiness columns users need.
  - Metrics dashboard Data Status now carries row-level metric dataset
    readiness messages into the Distributions row, so missing or stale
    dashboard metric datasets explain why distribution plots are unavailable.
  - QC dashboard startup now emits a single readiness warning that includes the
    specific trace-summary blocker, such as missing required columns, instead
    of showing a generic warning plus a second detailed warning.
  - Metrics dashboard startup now emits a single summary-readiness warning that
    includes the specific primary summary-table blocker before full dashboard
    summaries are loaded.
  - Compact dashboard readiness summaries now preserve dashboard-table labels,
    required columns, missing columns, missing map-coordinate columns, and
    non-empty value columns so notebooks can show the exact blocker for each
    dashboard artifact.
  - Metrics dashboard Data Status now displays required schema columns and
    recognized value columns alongside missing-column and non-empty-value
    checks, so dashboard readiness gaps are visible without loading large
    metric tables.
  - ``svtk dashboard status`` now prints the same bounded schema, missing
    column, map-coordinate, and value-column readiness fields for terminal and
    Slurm-log diagnostics.
  - This lets notebooks, generated workers, Slurm scripts, and lightweight
    Python drivers resolve registered outputs from one explicit config file
    without first activating global config state.
  - Added regression coverage for config-path resolution across preprocessing,
    Step 3 metric outputs, Step 4 spatial outputs, dashboard readiness and
    preview helpers, large-run readiness helpers, and later plotting-status
    helpers.

- **Step 1 workflow helpers** *(Added)*

  - Added a standard Step 1 ingest output loader for combined ingest and
    preprocessing output status.
  - Added typed Step 1 metadata, preprocessing, and record-coverage result
    objects with mapping-compatible access plus ``summary_message()`` and
    ``summary_frame()`` methods for notebooks.
  - Added bounded station, event, and preprocessing manifest previews for the
    standard Step 1 ingest output loader.
  - Added config-backed Step 1 metadata and preprocessing readiness helpers so
    notebook cells no longer repeat prepared-table or preprocessed-metadata
    path contracts.

- **Step 2 workflow helpers** *(Added)*

  - Added a lightweight standard Step 2 QC output loader for large-run setup
    cells that need QC output status without loading prepared metadata tables.
  - Added standard Step 2 QC input-result helpers for skipped-step fallback
    payloads, compact output summaries, and bounded QC inventory/summary
    previews.
  - Added config-backed Step 2 QC readiness helpers for full QC inventory,
    observed/synthetic overlap inventory, and compact QC summary workflows.
  - Added ``overwrite`` and readiness-message pass-throughs to Step 2 QC
    readiness helpers so notebooks keep rerun controls without local readiness
    contracts.
  - Added large-run Step 2 QC output result methods for full-QC inventory
    building, overlap-sidecar writing, and compact-summary table writing so
    the large-run QC notebook no longer imports or passes the lower-level
    configured QC writer/readiness functions directly.
  - Rewired the standard Step 2 QC notebook to use the same QC output result
    methods, including package-owned skipped-step payloads when configured
    outputs are already current.

- **Step 3 workflow helpers** *(Added)*

  - Extended the standard Step 3 metric output loader with the preprocessed
    trace metadata dependency and status-frame helper used by large-run
    metric readiness cells.
  - Added a standard Step 3 metric output loader for task-estimate,
    task-preview, and ``metrics_long`` notebook previews.
  - Added standard Step 3 metric output result methods for task-estimate
    loading and diagnostic figure writing so notebooks no longer load
    ``metrics_long`` or pass output groups into figure writers directly.
  - Rewired the standard Step 3 notebook to call
    ``metric_outputs.write_configured_outputs()`` and
    ``metric_outputs.write_station_metric_map()`` instead of importing
    lower-level metric-output and station-map writer functions.
  - Added large-run Step 3 result methods for metric inventory building,
    manifest planning, Slurm script writing/submission, batch merging,
    downstream output writing, and metric figure-suite rendering so the
    large-run notebook no longer imports or passes the lower-level configured
    writer functions directly.
  - Added config-backed Step 3 metric inventory and manifest readiness helpers
    so metric notebooks no longer repeat trace-metadata or QC-overlap
    dependency contracts.

- **Later-step workflow helpers** *(Added)*

  - Added lightweight Step 4, Step 5, and Step 6 output-status loaders for
    large-run driver notebooks that need configured status tables and bounded
    previews without loading large plotting inputs.
  - Added standard notebook input/output loaders for QC summaries.
  - Added standard notebook input/output loaders for spatial summaries.
  - Added standard Step 4 spatial output result methods for map and diagnostic
    figure writing so notebooks no longer unpack spatial product tables or
    output groups before plotting.
  - Added large-run Step 4 spatial status result methods for spatial-summary
    and derived-output runner gates so notebooks no longer import
    lower-level readiness or workflow functions directly.
  - Added standard notebook input/output loaders for GeoJSON plotting.
  - Added large-run Step 5 GeoJSON status result methods for region-summary
    and corridor runner gates so notebooks no longer import lower-level
    readiness or workflow functions directly.
  - Added standard Step 6 additional-plotting input result methods for figure
    writing so notebooks no longer unpack metric, event, comparison, or output
    aliases before plotting.
  - Added standard notebook input/output loaders for Step 5 readiness checks.

- **Notebook preview helpers** *(Added)*

  - Added output-registry preview helpers for notebook display cells.
  - Added path-backed table preview helpers for notebook display cells.
  - Added workflow-step status helpers for notebook display cells.
  - Added bounded pattern-similarity preview helpers for notebook display
    cells.
  - Added artifact labels, readiness messages, and suggested rebuild actions
    to output-group status frames used by notebook status cells.

- **Metrics API helpers** *(Added)*

  - Added public Metrics API reference tables for inventory and manifest
    helpers exposed through stable package entry points.
  - Added public Metrics API reference tables for Slurm, batch, merge, and
    output helpers exposed through stable package entry points.
  - Added ``SVTK_DASHBOARD_CHUNKSIZE`` to notebook run contexts so dashboard
    preparation chunking is configured once with the rest of the large-run
    controls.

- **Large-run notebook readiness** *(Rewired)*

  - Rewired the large-run Step 3 notebook to resolve metric outputs and trace
    metadata dependencies through the standard metric output helper.
  - Rewired the large-run Step 3 metric figure cell to use
    ``metric_outputs.metrics_long_path`` directly instead of exposing a
    lower-level ``step_outputs`` object and trace-metadata path variables in
    the notebook.
  - Rewired the large-run Step 2 notebook to resolve QC output status through
    the lightweight QC workflow output helper.
  - Rewired standard and large-run Step 2 notebooks to use package-owned QC
    readiness helpers for full inventory, overlap sidecar, and compact summary
    gates.
  - Rewired the large-run Step 3 notebook to use package-owned readiness
    helpers for metric waveform inventories and metric manifest planning.
  - Rewired the large-run Step 1 notebook to resolve ingest and preprocessing
    outputs through the same package helper as the standard tutorial.
  - Rewired the large-run Step 1 notebook to use package-owned metadata and
    preprocessing readiness helpers before local or Slurm execution.
  - Added result-object driver methods for large-run Step 1 metadata,
    waveform preprocessing, and record-coverage stages so notebooks call
    ``ingest_outputs.run_*_step_if_needed(...)`` instead of assembling
    readiness checks and build functions inline.

- **Notebook-owned display cleanup** *(Rewired)*

  - Rewired large-run Step 4, Step 5, and Step 6 status/preview cells to call
    package-owned output-status helpers instead of direct ``output_group(...)``
    methods.
  - Rewired large-run Step 4, Step 5, and Step 6 figure cells to call
    result-object methods for quick spatial summaries, GeoJSON region figures,
    waveform comparisons, and region boxplots instead of importing direct
    writer functions in notebooks.
  - Rewired the large-run Step 7 dashboard build cell to call
    ``DashboardDatasetPreparationResult.run_if_needed()`` instead of importing
    the configured dashboard writer and manually passing it to
    ``run_notebook_step_if_needed``.
  - Rewired the standard Step 5 GeoJSON notebook to call configured input
    result methods for region and corridor figure suites instead of unpacking
    GeoJSON paths, loaded tables, and output groups into notebook variables.
  - Rewired standard Step 1 and Step 2 notebooks to call package helpers for
    table previews, readiness messages, and configured output loading.
  - Rewired standard Step 2 and Step 3 notebooks to import metric settings
    helpers from the stable ``spatial_vtk.config`` package surface, matching
    the large-run notebooks.
  - Rewired the standard Step 2 notebook to use named QC skipped-step result
    methods for full inventory, overlap inventory, and compact summary
    fallbacks instead of passing individual QC output paths in notebook cells.
  - Rewired the standard Step 2 waveform comparison cell to call
    ``qc_inputs.write_waveform_comparison()`` instead of importing the
    waveform writer and passing the Step 2 output group through the notebook.
  - Rewired standard Step 4, Step 5, and Step 6 notebooks to call package
    helpers for table previews, readiness messages, and configured output
    loading.
  - Rewired Step 1 context figures and Step 2 QC figures to call result-object
    methods instead of unpacking output groups into notebook-local variables.
  - Kept reusable skip/rebuild decisions in package code rather than in
    notebook-local dictionaries.
  - Kept ``reused`` flags and path string conversion in package code rather
    than in notebook-local dictionaries.

- **Public API documentation** *(Changed)*

  - Updated Metrics API pages to document stable package entry points instead
    of lower-level implementation modules.
  - Split notebook-facing metric figure-suite guidance from advanced metric
    row-selection/context helpers so tutorial authors have one clear plotting
    path while custom scripts can still find the extension APIs.
  - Updated Python workflow guidance so the stable notebook import surface for
    metric plotting points to figure suites and result objects, while keeping
    row-selection helpers documented only as advanced script APIs.
  - Split notebook-facing spatial figure-suite guidance from advanced spatial
    figure-context builders so Step 4 tutorials point at result-object figure
    methods instead of context construction.
  - Updated QC, Spatial, Visualization, I/O, and Configuration API pages to
    document stable package entry points instead of lower-level implementation
    modules.
  - Added a stable workflow import-surface table that maps notebook and
    large-run helper families to public package namespaces and directs new
    helpers to be re-exported before notebooks use them.
  - Reworded the large-run notebook guidance to name stable public import
    packages without showing obsolete implementation-submodule examples.
  - Updated the Metrics API workflow result docs to reference the
    ``spatial_vtk.metrics`` package re-exports instead of lower-level
    workflow-module paths.
  - Updated configuration examples to use standard workflow output helpers
    instead of notebook-facing ``output_group(...).load_tables(...)`` blocks.
  - Updated workflow examples to prefer ``output_group()`` and configured
    output-registry helpers over raw ``resolve_output_path()`` snippets for
    normal notebook workflows.
  - Updated Python workflow docs so Step 2 QC and Step 3 metrics list
    result-object ``run_*_step_if_needed()`` methods as the notebook-facing
    entry points, with lower-level configured functions reserved for scripts
    and custom orchestration.
  - Updated Spatial API docs so Step 4 spatial status and Step 5 GeoJSON
    status result objects list their result-owned heavy-step runner methods.
  - Updated large-run README, package overview, and Python workflow guidance
    so common notebook examples point to result-object loaders and Step 4/5
    runner methods instead of lower-level readiness/build helper pairs.
  - Updated I/O reference docs and the output-registry module docstring so
    standard workflow result loaders are presented before ``output_group()``
    for routine notebooks, with ``output_group()`` and ``resolve_output_path()``
    framed as grouped-artifact and single-artifact script helpers.
  - Updated metric workflow package docstrings so Step 3 examples start with
    ``load_standard_metric_workflow_outputs(...)`` and result-owned
    manifest/Slurm methods before documenting lower-level task manifest and
    batch execution primitives for advanced scripts.
  - Updated the waveform preprocessing docstring so Step 1 examples start
    with ``load_standard_ingest_workflow_outputs(...)`` and the
    result-owned preprocessing runner before documenting direct
    ``preprocess_waveform_files(...)`` calls for advanced scripts.
  - Updated master station/event list docstrings so Step 1 metadata examples
    start with the standard ingest workflow output helper and
    ``run_metadata_step_if_needed(...)`` before documenting dataframe-level
    master-list builders.
  - Updated the spatial workflow docstring so Step 4 examples start with
    ``load_standard_spatial_workflow_output_status(...)`` and the
    result-owned summary runner before documenting custom output-directory
    helpers.
  - Updated metric and spatial plotting package docstrings so examples start
    with large-run figure-suite writers before documenting individual
    low-level plot functions, and aligned the Spatial API entry-point example
    with the same suite-first guidance.
  - Updated context map docstrings so Step 1 context figure examples use the
    standard ingest workflow output result instead of literal ``*.png`` output
    filenames.
  - Updated shared figure I/O docstrings so saving examples use configured
    figure output keys through ``finish_figure(...)`` before mentioning
    explicit ``outpath=`` overrides.
  - Updated QC retention figure docstrings so Step 2 QC figure examples use
    ``load_standard_qc_workflow_outputs(...)`` and the result-owned figure
    writer before documenting individual dataframe-driven plot functions.
  - Updated spatial map package docstrings so notebook examples start with
    the standard map figure writer before documenting individual map functions
    for focused scripts.
  - Updated the configuration guide so figure-output override guidance points
    routine notebooks at result-owned figure writers instead of a literal
    ``outpath="figures/..."`` example.

- **CLI examples and defaults** *(Changed)*

  - Updated CLI workflow examples so routine GeoJSON commands resolve
    standard inputs from the active config.
  - Updated CLI workflow examples so routine metric plotting, mapping,
    visualization, and dashboard commands resolve standard inputs from the
    active config.
  - Updated ``svtk ... list`` discovery output for plot, map, and visualization
    commands so required explicit inputs name the table role, such as
    ``required:spectrogram table``, instead of only naming a generic flag.
  - Added ``--resolve-paths`` to plot, map, and visualization ``list``
    commands so config-backed input, output, and extra-table keys can be
    expanded to concrete configured paths before running a figure command.
  - Added command-specific ``Configured defaults`` sections to generated plot,
    map, and visualization CLI reference pages so each command shows its
    config-backed input table, output figure key, and required-table roles
    before the long argument list.
  - Added first-class ``svtk dashboard metrics`` runtime-limit flags for
    row-level loading, summary-table display, and CSV downloads.

- **CLI validation and help text** *(Changed)*

  - Made registered plot/map/visualization commands validate missing required
    input and output paths before importing plotting modules or loading config,
    so missing-table errors are not masked by optional dependency messages.
  - Normalized generated CLI help text for config, input, output, and manifest
    arguments so usage strings show ``PATH`` or ``DIR`` where appropriate.
  - Normalized generated CLI help text for dashboard, inventory, and waveform
    path arguments so usage strings show ``PATH`` or ``DIR`` where
    appropriate.
  - Normalized spatial workflow CLI help for summary, derived-output,
    GeoJSON, and corridor commands so table/path options use ``PATH``/``DIR``
    and output registry options use ``KEY``.
  - Added a top-level CLI missing-dependency message so source-checkout
    commands report the missing package and install command instead of a raw
    traceback.
  - Made config-required workflow commands report missing config before
    importing optional runtime modules.
  - Made IO, QC, spatial, and dashboard commands validate missing configured
    defaults before importing optional workflow modules.
  - Normalized registered figure command help so advanced ``--table`` mappings,
    named table aliases, and sidecar directories use path-oriented metavars.

- **CLI guidance output** *(Changed)*

  - Clarified CLI plotting notes so visualization list commands are included
    with plot/map list commands, and ``required:<role>`` entries explain when
    explicit input tables are still required.
  - Clarified registered figure missing-path messages so input and figure
    output errors name both legacy and clearer path aliases before suggesting
    config-backed defaults.
  - Made ``svtk dashboard status`` print artifact labels, dashboard-tab
    readiness, and suggested rebuild actions in its human-readable output
    instead of the lower-level configured path table.
  - Clarified dashboard launch errors so missing config/path messages name the
    metrics-dashboard row dataset, dashboard summary-table directory, and QC
    trace-summary table instead of generic roots or paths.
  - Clarified ``svtk visualize sidecars status`` output so missing sidecar
    directories are reported separately from existing directories with no JSON
    sidecars.
  - Documented the sidecar status JSON ``sidecar_dir_exists`` field so notebook
    and script audits can tell missing sidecar directories from empty ones.
  - Made ``svtk spatial status`` print artifact labels, output keys, and
    Step 3/Step 4 rebuild guidance in its human-readable output instead of
    the lower-level path-key readiness table.

- **Dashboard large-run resilience** *(Hardened)*

  - Streamed partitioned dashboard metric dataset writes from path-backed CSV
    or Parquet metric tables, using chunked partition files instead of
    materializing the full ``metrics_long`` table before writing dashboard
    partitions.
  - Built dashboard summary tables from partitioned dashboard metric datasets
    one partition directory at a time, preserving exact summary statistics
    without loading all dashboard metric partitions at once.
  - Made metrics-dashboard summary readiness checks scan value and
    map-coordinate columns in projected chunks instead of materializing full
    summary tables during startup.
  - Made metrics-dashboard station, event, and path summary tabs load
    filtered summary rows lazily in chunks instead of loading every optional
    summary table at startup.
  - Made remaining full-table dashboard CSV reads use stable dtype inference
    so mixed station/event identifiers do not emit pandas ``DtypeWarning``
    messages or vary by chunk.
  - Added a separate metrics-dashboard summary-table display row cap so large
    station, event, path, or model-summary tables are not fully serialized to
    the browser by default.
  - Added a separate metrics-dashboard download row cap so filtered row-level
    CSV downloads do not serialize every loaded distribution row by default.
  - Added clear Streamlit dashboard query aliases
    ``metrics_dataset_dir``, ``dashboard_summary_table_dir``, and
    ``qc_trace_summary`` while preserving legacy dashboard links.
  - Added clear Python launch keywords ``metrics_dataset_dir`` and
    ``dashboard_summary_table_dir`` for ``launch_metrics_dashboard`` while
    preserving ``metrics_root`` and ``summary_root``.
  - Added ``qc_trace_summary_table`` to notebook dashboard launch status
    frames while preserving ``trace_summary_table`` for existing code.
  - Added ``resolved_path`` to dashboard output status, readiness summary, and
    written-output frames while preserving ``path`` for existing notebooks.
  - Added dashboard value-family readiness metadata so status tables show
    whether row-level and summary datasets contain residuals, GOF scores,
    observed values, synthetic values, or only generic metric values.
  - Promoted dashboard tab empty-state, missing-column, chart-readiness, and
    value-selector messages into public package helpers so notebooks and CLI
    status output can share the same contracts as Streamlit tabs.
  - Made ``svtk dashboard status`` include dashboard value-family and
    map-readiness messages in its bounded human-readable status table, matching
    the notebook and Streamlit Data Status displays.
  - Made ``svtk dashboard status`` show the clearer ``resolved_path`` column in
    human-readable output while preserving ``path`` in machine-readable status
    frames.
  - Hardened Streamlit dashboard launch checks so occupied ports are detected
    before launch and delayed startup failures are reported before the CLI
    prints a running-dashboard URL.
  - Kept dashboard launch helper imports config-lazy so lightweight dashboard
    command builders and launch function objects remain importable without
    loading YAML/config machinery.
  - Deferred dashboard status, contract, filter, label, and dataset-preparation
    function implementations until call time so public helper objects remain
    importable without eager pandas or YAML imports while result classes still
    resolve to real classes when explicitly imported.
  - Made ``spatial_vtk.spatial`` and ``spatial_vtk.spatial.calculate`` resolve
    public calculation helpers lazily so importing spatial package surfaces no
    longer imports every spatial calculation backend up front.
  - Made ``spatial_vtk.io`` resolve public I/O helpers lazily so importing the
    standard notebook I/O surface no longer imports table, waveform,
    preprocessing, or workflow implementations up front.
  - Kept lightweight output-status helpers importable without loading
    YAML/config machinery; configured output-group path resolution still loads
    config support only when a resolver is called.
  - Made ``spatial_vtk.visualize.context`` and
    ``spatial_vtk.visualize.waveforms`` resolve public figure helpers lazily so
    importing the stable visualization subpackages no longer requires NumPy,
    pandas, or plotting modules before a figure helper is used.
  - Made ``spatial_vtk.config`` resolve public config helpers lazily and
    decoupled display-label helpers from runtime config imports so lightweight
    label utilities remain importable without YAML or pandas.
  - Added a no-write ``tools/generate_cli_reference.py --check`` mode and
    rewired CI/release validation to use it for generated CLI-reference
    freshness checks.
  - Updated ``svtk call`` help and generated CLI docs to use a stable public
    import-path example instead of a lower-level implementation module.
  - Clarified generated API parameter descriptions for dashboard row datasets,
    summary-table directories, and QC trace-summary tables.
  - Clarified generated API parameter descriptions so ``metrics_root`` and
    ``summary_root`` are documented as legacy aliases rather than the primary
    Python dashboard launch parameters.
  - Added ``qc_trace_summary_table`` as the primary Python keyword for
    ``launch_qc_dashboard(...)`` while preserving ``trace_summary`` as a
    legacy alias.
  - Updated ``svtk dashboard qc`` to call the QC dashboard launcher through
    the primary ``qc_trace_summary_table`` keyword.

- **Workflow large-run resilience** *(Hardened)*

  - Added ``artifact_label`` and clear ``resolved_path`` columns to configured
    output-registry frames while preserving the existing ``path`` alias.
  - Added ``resolved_path`` to output status and readiness frames while keeping
    ``path`` as a compatibility alias.
  - Added ``resolved_path`` to Step 5 GeoJSON plotting input and region-figure
    status tables while preserving ``path`` for existing notebooks.
  - Added ``resolved_path`` to Step 4 spatial figure-context status frames
    while preserving ``path`` for existing notebooks.
  - Added ``resolved_path`` to focused station metric-map status frames while
    preserving ``output_path`` for existing notebooks.
  - Added exact ``figure_paths`` lists to Step 3 large-run metric figure-suite
    status frames while preserving preview-oriented figure path fields.
  - Added exact ``figure_paths`` lists to Step 4 large-run spatial
    figure-suite status frames while preserving preview-oriented figure path
    fields.
  - Updated the large-run dashboard notebook to use the package-owned
    dashboard preparation/display helper for preflight and postflight status,
    while letting the preparation result own the Slurm-aware dashboard dataset
    write call.
  - Added a Step 1 ingest metadata summary helper and updated the large-run
    ingest notebook to use it instead of loading prepared metadata tables only
    to print row counts.
  - Added a Step 2 QC compact-summary preview helper and updated the large-run
    QC notebook to preview summary products without touching full QC
    inventories.
  - Updated the large-run metric notebook to preview ``metrics_long`` through
    the package-owned metric workflow result helper instead of direct
    output-group calls.
  - Let Step 4 spatial and Step 5 GeoJSON status helpers retain their config
    for bounded preview calls, removing repeated config plumbing from the
    large-run notebooks.
  - Let Step 6 additional-plotting status helpers retain their config for
    metric-source preview calls, keeping the large-run plotting notebook
    focused on workflow steps instead of preview plumbing.
  - Added dashboard output previews to the Step 7 preparation result so
    large-run dashboard notebooks inspect bounded dashboard products without
    lower-level config/path preview calls.
  - Added broad notebook regression coverage and workflow docs requiring
    standard result-object preview methods instead of lower-level preview
    functions with repeated config arguments.
  - Reused the standard ingest output helper inside record-coverage
    readiness/build workflows so script and notebook path fallback behavior
    stays aligned.
  - Added warnings when large-run QC or metric checkpoint reuse falls back to
    slower paths because an existing checkpoint cannot be read.
  - Updated readiness-aware notebook cells so they print why a package workflow
    step is running before local execution or Slurm script generation.

- **Fresh checkout and docs checks** *(Fixed)*

  - Added regression coverage for public API import examples.
  - Added regression coverage for committed tutorial data.
  - Added regression coverage for CLI workflow examples.
  - Added regression coverage for changelog formatting.
  - Tightened changelog formatting checks so dated entries must keep their
    details as nested bullets instead of indented paragraph blocks.
  - Added release guardrails so local agent notes and execplans stay ignored.
  - Added release guardrails so machine-specific instructions are called out
    before public publishing.
  - Clarified tutorial runtime checks so missing importable modules are
    reported directly before the install command.
  - Aligned README and installation docs around the same notebook and
    large-run preflight commands.
  - Aligned source-checkout validation and CI tutorial gates around the same
    notebook and large-run preflight commands.
  - Added README quick-start verification commands for standard and large-run
    tutorial notebook preflight, runtime checks, and clean execution.

- **Config and plotting behavior** *(Fixed)*

  - Made ``svtk plot metrics period-spectra`` use the configured
    ``metrics_long`` table by default.
  - Taught ``plot_period_spectra()`` to accept standard metric-table
    residual/value columns through ``value_col``.
  - Clarified ``output_group_namespace()`` as a legacy path-only compatibility
    wrapper.

- **Workflow guidance** *(Documented)*

  - Clarified Python workflow guidance around public helper signatures, return
    contracts, and bounded previews.
  - Clarified output-registry guidance around public helper signatures, return
    contracts, and bounded previews.
  - Updated Python workflow guidance so the leading notebook example uses the
    standard QC output helper, with direct ``output_group(...)`` documented as
    a lower-level fallback when no standard helper exists yet.
  - Updated Python workflow guidance so large-run metric plotting points to the
    package-owned figure-suite wrapper rather than lower-level metric
    figure-context and row-selection helpers.
  - Updated Python workflow guidance so large-run spatial plotting points to
    the package-owned figure-suite wrapper rather than lower-level spatial
    figure-context helpers.
  - Clarified dashboard API guidance so notebooks display user-facing artifact
    labels instead of internal dashboard output-registry names.
  - Updated Spatial API examples so large-run plotting starts from the
    package-owned spatial figure-suite wrapper, with context builders described
    as advanced helpers.
  - Updated Metrics API examples so plotting starts from package-owned figure
    wrappers, with row-selection helpers described as advanced script APIs.
  - Updated Visualization API examples so notebook-facing waveform and
    dashboard wrappers appear before lower-level script helpers.
  - Documented notebook-facing and script-facing waveform-comparison and
    region-boxplot helpers.
  - Updated generated CLI reference examples to use the committed example
    config.
  - Updated generated CLI reference examples to use the tutorial run scenario.

- **Notebook hygiene** *(Cleaned)*

  - Removed one-off preview variables and repeated path construction from
    standard notebook cells where package helpers now own the task.
  - Added a global tutorial-notebook import-boundary guard so notebooks cannot
    reintroduce implementation modules for config, I/O, QC, metrics, spatial,
    visualization, or dashboard workflows.
  - Extended the tutorial notebook source-contract preflight so
    ``tools/execute_tutorial_notebooks.py --preflight-only`` enforces the same
    public import boundary before runtime dependencies, output cleanup, or
    notebook execution.
  - Made large-run README guidance explicit about public plotting entry
    points.
  - Made large-run README guidance explicit about public mapping and
    visualization entry points.
  - Replaced large-run README single-figure import examples with package-owned
    workflow helper examples for metrics, QC, spatial figures, dashboards, and
    bounded notebook context setup.
  - Clarified that large-run notebooks may import stable public plotting and
    dashboard packages, while deeper implementation submodule imports remain
    blocked by preflight.

2026-06-18
----------

- **Package-owned figure suites** *(Added)*

  - Added standard and large-run figure-suite helpers for metric diagnostics
    and spatial diagnostics.
  - Added standard and large-run figure-suite helpers for GeoJSON regions and
    corridors.
  - Added standard and large-run figure-suite helpers for waveform comparison,
    context figures, and QC figures.
  - Added standard and large-run figure-suite helpers for region boxplots and
    dashboard preparation.
  - Added focused station-map preview helpers.
  - Added focused spatial-product and PCA-product preview helpers.
  - Added focused corridor-record preview helpers.
  - Added focused waveform-order and pattern-similarity preview helpers.

- **Figure provenance and sidecars** *(Added)*

  - Expanded figure sidecar metadata and status frames with source-row roles.
  - Expanded figure sidecar metadata and status frames with plot/source
    dimension counts.
  - Expanded figure sidecar metadata and status frames with aggregation
    contracts and exactness flags.
  - Expanded figure sidecar metadata and status frames with station/event
    counts and PSA/multi-panel counts.
  - Added sampled station-map sidecar regression coverage so plotted station
    groups and source rows stay aligned.

- **Release and API maintenance** *(Added)*

  - Added a public ``RELEASE_CHECKLIST.md`` for validation, docs, and build
    gates.
  - Added a public ``RELEASE_CHECKLIST.md`` for wheel inspection and publish
    gates.
  - Added public helpers for metric row selection and event/station matching.
  - Added public helpers for GeoJSON metric frames and event labels.
  - Added public helpers for spatial metric products and first non-empty table
    values.
  - Clarified API and workflow docs so stable public subpackages are not
    described as lower-level implementation modules.
  - Updated the example tutorial scenario and CLI workflow to use
    event-station observed/synthetic overlap for metric planning.
  - Made the large-run Step 2 notebook print and pass the configured QC
    overlap scope when writing the observed/synthetic overlap inventory.
  - Made the large-run Step 3 notebook display the resolved metric settings
    and batch count before metric manifest planning.
  - Clarified large-run Step 4 spatial status tables and event-centered plot
    titles so users can tell when event means have been removed.
  - Updated the configuration guide so notebook examples use standard workflow
    output helpers instead of registered table-write calls.
  - Updated the dashboard export module docs so the configured dashboard
    preparation helper appears before lower-level dataset writers.

- **Notebook simplification** *(Rewired)*

  - Rewired standard and large-run plotting notebooks so cells call package
    helpers instead of importing individual plotting functions.
  - Rewired standard and large-run plotting notebooks so cells no longer
    construct figure paths or repeat sidecar/showfig/savefig plumbing.
  - Rewired standard Step 3 and Step 4 notebooks to use package-owned context
    setup, table previews, dashboard displays, and diagnostic figure writers.
  - Rewired standard Step 5, Step 6, and Step 7 notebooks to use package-owned
    context setup, table previews, dashboard displays, and diagnostic figure
    writers.

- **Large-run metric and spatial plotting** *(Rewired)*

  - Moved metric target iteration into package code.
  - Moved PSA period-sheet branching and station aggregation into package
    code.
  - Moved robust-axis selection into package code.
  - Moved model/component/passband defaults and raw source-row sidecars into
    package code.
  - Added spectral contract status checks for PSA/FAS rows so notebooks can
    flag legacy passband-scoped spectral metrics before rendering figures.

- **Tutorial/runtime checks** *(Hardened)*

  - Strengthened runtime checks to verify the source checkout before notebook
    outputs are cleaned or executed.
  - Strengthened runtime checks to verify required scientific, mapping,
    dashboard, waveform, Jupyter, and IPython modules before notebook outputs
    are cleaned or executed.
  - Tightened notebook preflight to reject notebook-local function and class
    definitions.

- **Dashboard and plotting stability** *(Hardened)*

  - Improved metrics-dashboard Data Status messages for skipped optional
    summary tables.
  - Improved metrics-dashboard Data Status messages for filtered-empty views.
  - Routed Step 4 spatial figure items by explicit owner tags instead of
    dataframe column-subset inference.
  - Improved generated API-reference fallback text for common parameter names.

- **Public entry points** *(Documented)*

  - Updated configuration and workflow docs to use stable public imports from
    ``spatial_vtk.config`` and other package surfaces.
  - Documented the broadband spectral-metric contract: PSA and FAS are planned
    as blank-passband spectral tasks with oscillator periods in ``period_s``.

- **Development-only reload hooks** *(Removed)*

  - Removed ``reload_metric_plot_modules()`` and the large-run notebook
    ``globals().update(...)`` reload pattern.

2026-06-17
----------

- **Large-run workflow drivers** *(Added)*

  - Added config-backed QC and metrics helpers for large-run notebooks.
  - Added config-backed spatial, GeoJSON, and dashboard helpers for large-run
    notebooks.
  - Added config-backed preprocessing, record-coverage, and waveform-inventory
    helpers for large-run notebooks.
  - Added config-backed Slurm, batch-merge, and output-writing helpers for
    large-run notebooks.
  - Added ``run_notebook_step_if_needed()`` and structured readiness/status
    frames so notebooks can skip current outputs and explain stale or missing
    prerequisites.

- **Output groups and previews** *(Added)*

  - Added ``OutputGroup`` helpers for grouped table loading and fallback
    previews.
  - Added ``OutputGroup`` helpers for path-backed preprocessing metadata.
  - Added ``OutputGroup`` helpers for first-existing outputs and figure paths.
  - Added ``OutputGroup`` helpers for readiness checks and status frames.
  - Added notebook settings helpers for run scenarios and metric batch counts.
  - Added notebook settings helpers for preprocessing error policy.
  - Added notebook settings helpers for figure controls, sidecar settings, and
    PCA mode.
  - Added notebook settings helpers for dashboard launch commands and optional
    score trends.

- **Dashboard and figure diagnostics** *(Added)*

  - Added metrics/QC dashboard launch helpers and dashboard dataset writers.
  - Added dashboard readiness summaries and bounded dashboard startup checks.
  - Added current-filter diagnostics for dashboard workflows.
  - Added metric and spatial figure contexts with status frames and dimension
    summaries.
  - Added metric and spatial figure contexts with sidecar status.
  - Added metric and spatial figure contexts with PSA/FAS contract checks,
    station aggregation metadata, and source-row provenance.

- **Config-backed CLI and notebooks** *(Rewired)*

  - Updated standard and large-run notebooks to load tables through output
    groups and package helpers instead of repeated ``load_output_table`` or
    raw path checks.
  - Made routine ``svtk io`` and ``svtk metrics`` commands use configured
    defaults or clearer artifact-named aliases.
  - Made routine ``svtk plot`` and ``svtk map`` commands use configured
    defaults or clearer artifact-named aliases.
  - Made routine ``svtk visualize``, ``svtk spatial``, and ``svtk qc``
    commands use configured defaults or clearer artifact-named aliases.
  - Made dashboard commands use configured defaults or clearer artifact-named
    aliases.

- **Metric and spatial execution** *(Changed)*

  - Added incomplete-only metric Slurm arrays and metric batch-status
    reporting.
  - Added output-directory-aware batch merging and config-backed metric task
    planning/running/merging.
  - Preserved PSA oscillator periods, path geometry, and public value columns
    in compact spatial outputs for downstream Step 4 figures.

- **Large-run performance and robustness** *(Hardened)*

  - Reduced dashboard summary memory use.
  - Made dashboard dataset rewrites replace stale artifacts safely.
  - Hardened dashboard startup for partial or large outputs.
  - Added dashboard startup diagnostics for missing map coordinates and value
    columns.
  - Hardened station aggregation and map coordinates.
  - Hardened figure sidecars.
  - Hardened PSA sheets and older pandas/Matplotlib compatibility.
  - Hardened directory-style metric batch merge outputs.

- **User-facing clarity** *(Clarified)*

  - Clarified public API start points.
  - Clarified dashboard path names.
  - Clarified metric, spatial, and QC CLI aliases.
  - Clarified large-run plotting defaults and helper return-value guidance.
  - Updated tests to guard outlier handling and sidecar provenance.
  - Updated tests to guard config-backed CLI defaults.
  - Updated tests to guard notebook imports and tutorial freshness checks.

- **Notebook and workflow docs** *(Documented)*

  - Updated tutorial notebooks to use public package helpers, grouped output
    loading, and direct output-group attributes.
  - Updated Python workflow docs to use public package helpers, grouped output
    loading, and direct output-group attributes.
  - Documented the committed NPZ tutorial waveform subset, source-checkout
    install extras, package-level plotting/map entry points, and dashboard
    output contracts.

2026-06-16
----------

- **CLI and plotting controls** *(Added)*

  - Added first-class plotting, mapping, waveform, and table flags.
  - Added first-class sidecar flags.
  - Added first-class mode, component, metric, and passband flags.
  - Added first-class value-column, fit, title, and comparison flags so
    routine figure configuration no longer depends on generic ``--kwargs``.
  - Registered plotting and mapping commands through stable public import
    surfaces and expanded config-backed command defaults.

- **Tutorial execution and CI** *(Added)*

  - Added ``tools/execute_tutorial_notebooks.py`` for clean source-checkout
    notebook execution and warning-like output detection.
  - Added tutorial data preflight and runtime dependency preflight.
  - Added CI notebook execution coverage and regression checks against
    private/local notebook paths.

- **Dashboard and sidecar contracts** *(Added)*

  - Added dashboard output helpers, readiness diagnostics, and artifact roles.
  - Added dashboard summary contribution-count tests, map-coordinate
    requirements, and optional row-provenance sidecars for saved figures.

- **Notebook path ownership** *(Rewired)*

  - Replaced notebook-local output-path dictionaries and repeated
    ``resolve_output_path`` calls with output namespaces, output groups, and
    dashboard output helpers.
  - Updated large-run notebooks to keep configured paths attached to
    package-owned output groups.

- **Public workflow docs** *(Changed)*

  - Updated generated CLI reference and shell workflow examples to prefer
    first-class flags and stable package entry points.
  - Updated Python workflow docs and configuration examples to prefer
    first-class flags and stable package entry points.

- **Dashboard and figure behavior** *(Hardened)*

  - Hardened metrics and QC dashboards against missing, empty, schema-invalid,
    filtered-empty, and value-less optional tables.
  - Hardened station-map aggregation and station coordinate handling.
  - Hardened sidecar metadata.
  - Hardened warning scans and notebook output labels.
  - Hardened output-readiness messages.

- **Fresh checkout reliability** *(Fixed)*

  - Made tutorial basemap fetching opt-in, kept Jupyter runtime files under
    ignored tutorial outputs, and added missing notebook runtime dependencies
    to source-install extras and the conda environment.

2026-06-09
----------

- **0.1.3** *(Released)*

  - Published a PyPI README workflow-image fix after external Sigstore/Rekor
    ``502`` errors blocked the ``0.1.2`` publish.

- **0.1.2** *(Released)*

  - Refreshed PyPI project metadata so the README workflow image uses an
    absolute GitHub-hosted URL that renders on PyPI.

- **0.1.1** *(Released)*

  - Refreshed PyPI project metadata so the package page points readers to the
    public GitHub Pages documentation.

2026-06-08
----------

- **QC-to-metrics valid-window contract** *(Added)*

  - Preserved waveform source labels in PhaseNet arrival-pick catalogs.
  - Allowed waveform QC to anchor noise and signal windows to source-specific
    PhaseNet P picks when available, with envelope-onset fallback.
  - Added a plausibility gate so PhaseNet picks are used only when their signal
    windows have enough finite samples inside the metric-valid interval.

- **Waveform QC windows** *(Fixed)*

  - Reduced the automatic waveform-QC default noise-window minimum from
    10 seconds to 1 second.
  - Allowed QC noise windows to sample finite preprocessed data outside the
    metric-valid interval while keeping signal metrics constrained to the valid
    interval.

- **Metric trimming** *(Notes)*

  - Waveform QC records processing-valid trace intervals, metric QC preserves
    those intervals, and metric execution trims scalar, pair, and spectral
    calculations to valid samples so filter/resampling edge transients do not
    control metric values.
  - The actual noise window remains at least as long as the requested period
    band.

2026-06-03
----------

- **Public docs and examples** *(Added)*

  - Added data formats and configuration guidance.
  - Added package overview and installation guidance.
  - Added Python API and CLI API guidance.
  - Added CLI workflow, tutorial, and downloadable notebook guidance.
  - Added lightweight LA Basin metadata, public example manifests, GeoJSON
    regions, and site metadata previews.
  - Added basemap-backed output previews and tutorial waveform/data snippets.

- **Tutorial workflow helpers** *(Added)*

  - Added config-default metadata preparation and output table
    readers/writers.
  - Added shared metric catalog/run scenarios.
  - Added dashboard/table display helpers.
  - Added concise tutorial comments before main package calls.
  - Added Step 6 plotting examples for waveform maps, pattern similarity,
    scatterplot, boxplot, and heatmap outputs.

- **CLI and spatial examples** *(Added)*

  - Expanded generated CLI reference pages.
  - Added a shell workflow tutorial covering config, preprocessing, QC,
    metrics, and spatial figures.
  - Added a shell workflow tutorial covering GeoJSON, corridors, flexible
    plots, and dashboards.
  - Added spatial-correlation-by-distance and geology-contrast examples.

- **Installation and workflow docs** *(Changed)*

  - Restored conda-environment-first installation guidance.
  - Kept ``python -m pip install spatial-vtk`` as the main PyPI command.
  - Reworked package overview into a workflow-oriented guide.
  - Renamed tutorial-facing loaders/writers to ``load_output_table`` and
    ``write_metric_outputs``.

- **Tutorial outputs** *(Changed)*

  - Replaced notebook timing magics with shared timing registration.
  - Updated signed residual map figures to use a zero-centered divergent
    colorscale.
  - Updated log-ratio and mean-centered map figures to use a zero-centered
    divergent colorscale.
  - Regenerated Step 5 regions and corridor maps with public LA Basin examples.

- **Tutorial reliability** *(Fixed)*

  - Cleaned tutorial notebooks so they use the activated tutorial config and
    shared output registry.
  - Cleaned tutorial notebooks so they use standard table writes/reads and
    headless figure display support.
  - Simplified Step 4 so spatial-statistics functions resolve metric/value
    selection and event-centering from the active config.
  - Simplified Step 4 so spatial-statistics functions resolve Moran,
    clustering, PCA, GeoJSON, and geology options from the active config.
  - Clarified spectral QC reason labels, regenerated QC previews, and cleaned
    internal trace-offset displays from waveform-map tutorials.

- **Workflow simplification** *(Notes)*

  - Standard outputs are written where they are created and later notebooks
    read those products by key.
  - ``summarize_station_bias`` accepts raw and event-centered metric fields.
  - The dashboard tutorial is Step 7.

2026-06-02
----------

- **Initial public migration** *(Added)*

  - Started the public Spatial-VTK package skeleton.
  - Added runtime configuration and output planning.
  - Added the metric catalog.
  - Added YAML/JSON config loading and named bounds.
  - Added output manifests and config-backed metric plans.

- **Core workflow modules** *(Added)*

  - Added metadata preparation and waveform inventories.
  - Added context figures and QC helpers.
  - Added metric batch calculations and arrival-pick normalization.
  - Added long residual-table preparation and metadata enrichment.
  - Added deterministic example metric plots.
  - Added public metric, transform, and passband labels/helpers.
  - Added public dashboard labels/helpers.
  - Added public plotting and mapping labels/helpers.
  - Added public figure-selection labels/helpers.

- **Spatial analysis and visualization** *(Added)*

  - Added spatial-statistics modules for metric preparation and station bias.
  - Added spatial-statistics modules for Moran's I and distance-bin
    correlations.
  - Added spatial-statistics modules for spatial holdout, clustering, REDCAP,
    and PCA.
  - Added spatial-statistics modules for bootstrap contrasts, permutation
    tests, pattern similarity, and observed/synthetic geometry.
  - Added plot/map wrappers for correlograms, semivariograms, and directional
    correlation.
  - Added plot/map wrappers for holdout maps, clusters, PCA, station bias, and
    REDCAP.
  - Added plot/map wrappers for pattern similarity, path maps, and event
    residual maps.
  - Added plot/map wrappers for GeoJSON polygons and boundary corridors.

- **Dashboards** *(Added)*

  - Added optional Streamlit dashboard support with Folium maps and Plotly
    charts.
  - Added dashboard schema validation.
  - Added filtered exports and manual-review exports.
  - Added selectable observed/synthetic/residual/GOF value columns.

- **Metric naming** *(Changed)*

  - Updated metric plots and spatial plots to support the renamed metric
    scheme and selectable value columns.
  - Updated maps and dashboard summaries to support the renamed metric scheme
    and selectable value columns.
  - Updated QC dashboard controls and waveform figures to support the renamed
    metric scheme and selectable value columns.
  - Updated record sections and context figures to support the renamed metric
    scheme and selectable value columns.

Future Work
-----------

- Planned additions are tracked in :doc:`future_features`.

.. toctree::
 :maxdepth: 1
 :hidden:

 future_features
