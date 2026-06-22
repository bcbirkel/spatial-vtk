Changelog
=========

2026-06-22
----------

- **Metric figure readiness** *(Fixed)*

  - Updated large-run metric figure context readiness so a present value column
    with no finite selected values is not reported as ready to render.
  - Added finite and non-finite selected-value row counts to the metric figure
    context status frame for easier notebook diagnostics on large datasets.
  - Documented the finite-value render gate in the metric plotting API
    reference and added source-contract coverage for the status fields.

- **Standard notebook setup imports** *(Changed)*

  - Moved ``notebook_run_context`` imports for standard Steps 1, 4, 5, 6, and
    7 into each notebook's setup import cell.
  - Removed repeated context-helper imports from task/configuration cells so
    those cells stay focused on workflow settings and package helper calls.

- **Step 3 metric preview context** *(Fixed)*

  - Updated ``summarize_metric_snapshot_tasks_from_config`` to accept the
    shared notebook context object and inherit its config path and run
    scenario.
  - Updated the standard Step 3 notebook to call the helper with
    ``context=context`` instead of referencing an undefined ``config_path``
    variable.

- **Standard dashboard launch context** *(Changed)*

  - Updated the standard Step 2 and Step 7 notebooks to pass the resolved
    ``NotebookRunContext`` directly to ``notebook_dashboard_launch_commands``.
  - Removed local config-path and run-scenario plumbing from dashboard launch
    cells so standard and large-run notebook drivers use the same package
    helper pattern.

- **Large-run dashboard launch context** *(Changed)*

  - Updated ``notebook_dashboard_launch_commands`` to accept a resolved
    ``NotebookRunContext`` directly and inherit its run scenario when one is
    not passed explicitly.
  - Removed unused ``config_path = context.config_path`` assignments from the
    large-run Step 1, Step 2, Step 3, and Step 7 notebooks so driver cells stay
    focused on workflow settings instead of path plumbing.

- **Dashboard CLI argument names** *(Changed)*

  - Renamed the internal argparse destinations for metrics-dashboard overrides
    to ``metrics_dataset_dir`` and ``dashboard_summary_table_dir`` so command
    handlers use the same vocabulary as the public flags and docs.
  - Kept ``--metrics-root``, ``--metrics-dataset``, ``--summary-root``, and
    ``--dashboard-summary-dir`` working as legacy aliases.

- **Dashboard readiness summary status** *(Changed)*

  - Added the stable ``artifact`` identifier to compact dashboard readiness
    summaries, matching the detailed dashboard status frame.
  - Kept input, metrics-dashboard dataset, dashboard summary-table, and
    trace-QC rows aligned so notebooks can filter readiness displays without
    relying on path keys or labels.

- **Spatial figure context status** *(Changed)*

  - Added normalized ``artifact``, ``artifact_label``, ``artifact_role``, and
    compact ``status`` fields to Step 4 spatial figure context status frames.
  - Kept the status frame lightweight by reporting only already-loaded tables
    and configured paths, without reading additional large spatial outputs.

- **Notebook figure sidecar status** *(Changed)*

  - Updated notebook-facing figure sidecar status frames so disabled,
    not-configured, missing-directory, and empty-directory states display an
    explanatory row instead of a blank table.
  - Kept the low-level figure-sidecar scanner focused on per-figure metadata
    rows, so script and CLI callers can still distinguish no metadata from
    written sidecars directly.

- **API reference export guard** *(Added)*

  - Added source-contract coverage for public API ``autofunction`` and
    ``autoclass`` targets so docs cannot point at helpers missing from the
    documented package namespace ``__all__`` exports.
  - Kept the check source-based and lazy so it validates public documentation
    targets without importing heavy plotting or workflow implementation
    objects.

- **Large-run Step 5/6 sidecar visibility** *(Changed)*

  - Added package-owned sidecar readiness and status displays to the large-run
    GeoJSON/corridor and additional-plotting notebooks.
  - Kept provenance review visible for Step 5 region figures plus Step 6
    waveform and region-boxplot figures without notebook-local sidecar path
    plumbing.
  - Added notebook source-contract coverage so these large-run figure families
    continue to expose sidecar readiness before rendering and sidecar status
    after rendering.

- **Step 3 output writer context** *(Fixed)*

  - Added optional ``context=`` support to
    ``StandardMetricWorkflowOutputResult.write_configured_outputs()`` so the
    documented notebook call can derive config path and run scenario from the
    same notebook context used by the Step 3 driver methods.
  - Preserved existing ``cfg=`` behavior for scripts and notebooks that already
    load the Step 3 result with a config object or config path.
  - Added regression coverage for context-derived downstream metric output
    writing.

- **Metric waveform cache imports** *(Changed)*

  - Deferred the metric runner import inside
    ``cache_metric_manifest_waveforms`` until a missing cache file actually
    needs waveform samples materialized.
  - Kept metric cache status frames and existing-cache reuse paths lightweight
    for large-run notebooks that only need readiness/output inspection.
  - Added source-contract coverage so the cache helper does not reintroduce
    eager metric-runner or waveform-reader imports.

- **Step 4 spatial status imports** *(Changed)*

  - Moved clustering, PCA, autocorrelation, geology, and pattern-similarity
    calculator imports out of the Step 4 workflow module import path and into
    the compute functions that use them.
  - Kept spatial workflow status/result helpers importable for lightweight
    notebook readiness checks without importing expensive spatial-analysis
    backends first.
  - Kept per-metric checkpoint reuse from front-loading those calculators, and
    left each optional spatial diagnostic import inside the same non-fatal
    failure boundary as its computation.
  - Added source-contract coverage so Step 4 status helpers keep those
    optional calculators lazy.

- **Step 5/6 spatial plotting status imports** *(Changed)*

  - Moved Matplotlib-backed region-boxplot imports and Shapely-backed GeoJSON
    annotation imports out of the large-run spatial plotting module import
    path.
  - Kept Step 5/6 output-status result classes importable for lightweight
    notebook readiness checks before figure rendering or GeoJSON annotation
    is requested.
  - Added source-contract coverage so the large-run spatial plotting module
    does not reintroduce eager plotting or GeoJSON calculator imports.

- **Step 4 spatial output status** *(Fixed)*

  - Updated ``StandardSpatialWorkflowOutputResult.status_frame()`` to start
    from the configured Step 4 table artifacts instead of only reporting
    tables that were already loaded into memory.
  - Added a ``loaded`` column and preserved row counts for loaded tables, so
    large-run notebooks can distinguish missing configured outputs from
    outputs that exist but were not materialized in the current process.
  - Added regression coverage for a configured but unloaded
    ``permutation_moran`` table so spatial status cells keep exposing missing
    Moran/PCA/cluster/geology products.

- **Package overview dashboard guidance** *(Changed)*

  - Updated the top-level package overview to point routine notebooks to
    ``spatial_vtk.visualize`` dashboard readiness, preparation, preview, and
    launch helpers instead of a vague dashboard subpackage description.
  - Named the configured ``metrics_dashboard``, ``dashboard_summaries``, and
    ``qc_trace_summary`` dashboard outputs in the overview so users see the
    same vocabulary across docs, CLI, notebooks, and API reference pages.

- **Large-run notebook import guidance** *(Changed)*

  - Clarified that large-run notebooks should use workflow result objects for
    plotting and output bookkeeping instead of hand-wiring individual plotting
    calls.
  - Kept ``spatial_vtk.metrics.plot``, ``spatial_vtk.spatial.plot``,
    ``spatial_vtk.spatial.map``, and ``spatial_vtk.visualize`` documented as
    stable public imports for custom scripts and package extensions.

- **Dashboard documentation vocabulary** *(Changed)*

  - Replaced remaining dashboard ``root`` wording in the visualize API and
    Python workflow references with the configured ``metrics_dashboard`` row
    dataset directory and ``dashboard_summaries`` summary-table directory
    terminology.
  - Added source-contract coverage so dashboard docs keep using explicit
    dataset, summary-table, and output-directory labels instead of ambiguous
    root vocabulary.

- **CLI PSA plotting workflow** *(Fixed)*

  - Removed ``PSA`` from the passband heatmap command in the CLI workflow
    tutorial so the example no longer mixes broadband spectral rows with
    passband-dependent metrics.
  - Added a ``svtk plot metrics psa-period-curve`` example for PSA
    ``log2_residual`` diagnostics by oscillator period.
  - Added source-contract coverage so the CLI workflow keeps passband heatmaps
    focused on passband-dependent metrics and routes PSA through period-based
    plotting.

- **Dashboard workflow path vocabulary** *(Changed)*

  - Replaced ambiguous dashboard ``root`` wording in the Python workflow guide
    with the configured ``metrics_dashboard`` row dataset directory and
    ``dashboard_summaries`` summary-table directory names.
  - Added source-contract coverage so dashboard workflow docs stay aligned with
    the config, CLI, and dashboard launcher vocabulary.

- **Visualize API public helper surface** *(Changed)*

  - Replaced the lower-level shared visualize utility automodule block with
    public ``spatial_vtk.visualize`` autosummary entries for figure sidecars,
    figure context labels, figure saving, and record-section helpers.
  - Kept the family-specific public modules documented for context, QC,
    waveform, and dashboard workflows while steering reusable helpers through
    stable package re-exports.
  - Added source-contract coverage so internal visualize utility modules are
    not reintroduced as notebook-facing API reference sections.

- **Step 1 notebook workflow ownership** *(Changed)*

  - Switched the standard Step 1 notebook to
    ``load_standard_ingest_workflow_outputs(...).run_*_step_if_needed(...)``
    methods for metadata, waveform preprocessing, and record coverage.
  - Added a ``component`` pass-through to
    ``StandardIngestWorkflowOutputResult.run_record_coverage_step_if_needed()``
    so the notebook can keep its configured record-coverage component without
    direct path-wrapper calls.
  - Added notebook contract coverage so Step 1 no longer depends on local
    ``config_path=str(config_path)`` boilerplate in workflow cells.

- **Metric figure suite sidecar status** *(Added)*

  - Added suite-level sidecar coverage fields to
    ``MetricFigureSuiteResult.status_frame()`` so Step 3 notebooks show
    provenance sidecar counts, source-sidecar counts, total plot/source row
    counts, and exact-versus-sampled flags for each figure family.
  - Added the same sidecar coverage fields to
    ``SpatialFigureSuiteResult.status_frame()`` so Step 4 spatial figures expose
    the same provenance contract.
  - Promoted the JSON-only suite summarizer to
    ``spatial_vtk.visualize.figure_family_sidecar_summary`` and
    ``spatial_vtk.visualize.add_figure_family_sidecar_status`` for reuse by
    figure-suite result objects.
  - Kept the suite status lightweight by reading only small sidecar JSON
    metadata files and checking file existence, not the potentially large CSV
    sidecars.
  - Added regression coverage for mixed exact/sampled sidecars and missing
    source sidecars.

- **Large-run spatial plotting import boundary** *(Changed)*

  - Deferred Matplotlib imports in large-run spatial plotting helpers until a
    figure is actually rendered or cleaned up.
  - Kept ``SpatialFigureSuiteResult`` and spatial figure status helpers usable
    in lightweight table/status environments without plotting dependencies
    installed.
  - Added source-contract coverage that rejects top-level Matplotlib imports in
    the large-run spatial plotting module.

- **Step 2 notebook checkpoint visibility** *(Fixed)*

  - Bound the standard Step 2 dashboard launch cell to
    ``context.config_path`` so the notebook can run cleanly from a fresh kernel.
  - Displayed ``qc_outputs.checkpoint_status_frame()`` after Step 2 QC
    inventory work in both standard and large-run notebooks.
  - Added notebook contract coverage so checkpoint progress stays visible in
    future Step 2 edits.

- **QC checkpoint status frames** *(Added)*

  - Added ``qc_checkpoint_status_frame()`` for lightweight inspection of trace
    QC and metric QC checkpoint paths, row counts, completed event-station
    records, and completed waveform component groups.
  - Added ``StandardQCWorkflowOutputResult.checkpoint_status_frame()`` so
    notebooks can display resume progress through the configured Step 2 result
    object instead of reconstructing checkpoint filenames.
  - Documented the status frame in the QC API and Python workflow references.

- **Metric Slurm progress timing** *(Fixed)*

  - Made generated metric Slurm scripts create a shared workflow start-time
    stamp next to the script when the array starts.
  - Taught metric batch progress output to prefer that Slurm start time over
    the manifest modification time, avoiding misleading elapsed times when a
    manifest was planned well before the job was submitted.
  - Added regression coverage for the generated start-time export and elapsed
    time fallback.

- **Metric manifest planning metadata** *(Changed)*

  - Added optional planning metadata to metric workflow manifests so status
    frames can show whether tasks were filtered to passing observed/synthetic
    QC pairs.
  - Recorded configured planning policy, QC filtering mode, output mode, and
    observed/synthetic overlap settings when manifests are created from the
    active config.
  - Preserved planning metadata when rewriting manifests to use metric-ready
    waveform caches.
  - Clarified the metrics API reference and large-run Step 3 notebook so users
    can see that default metric manifests are planned from
    ``qc_inventory_overlap`` and passing observed/synthetic event-station QC
    pairs, not from every row in the full QC inventory.

- **Large-run metric plotting import boundary** *(Changed)*

  - Deferred matplotlib imports in large-run metric plotting helpers until a
    figure is actually rendered.
  - Kept ``MetricFigureContext`` importable in lightweight table-only
    environments so status checks, station aggregation, and sidecar planning
    can run without plotting dependencies installed.
  - Added a source-contract regression test that rejects top-level matplotlib
    imports in the large-run metric plotting module.
  - Expanded focused station metric-map status frames with station aggregation
    coordinate columns, collapsed dimensions, collapsed-dimension unique counts,
    and input/finite station counts from the sidecar metadata so notebooks can
    audit aggregation without opening JSON sidecars.

- **Large-run figure table parity** *(Changed)*

  - Added a public ``build_categorical_comparison_table()`` helper that returns
    the same baseline comparison rows drawn under categorical boxplots.
  - Added comparison-table accessors to large-run region figure results so
    Step 5 and Step 6 notebooks can display the statistical table without
    rebuilding it locally.
  - Added compact diagnostic previews to the large-run Step 4 spatial figure
    suite for Moran's I, distance-correlation, PCA, clustering, and geology
    tables used by the figures.
  - Updated large-run plotting notebooks to display the package-owned
    comparison and diagnostic tables alongside figure status frames.

- **Spatial figure sidecar provenance** *(Changed)*

  - Labeled spatial figure sidecars with explicit plot/source table roles so
    users can distinguish metric-field rows from event-centered residual rows.
  - Preserved sidecar role metadata through PSA period-sheet concatenation and
    source-row filtering for aggregated station plots.
  - Added event-centered flags to sidecar JSON metadata and sidecar status
    frames, including an ``event_mean_removed`` marker for event-centered
    residual figures.
  - Added regression coverage for overlapping metric-field and event-centered
    schemas so routing and sidecar labels do not depend on ambiguous columns.

- **PSA map sheet layout** *(Fixed)*

  - Reworked PSA period station maps to reserve a dedicated GridSpec column for
    the shared colorbar instead of placing it with fixed figure coordinates.
  - Reworked metric-by-model maps to use the same explicit colorbar-column
    layout so model facets and colorbars cannot overlap.
  - Wrapped long metric/context subtitles before positioning map panels, which
    keeps PSA oscillator-period summaries readable without covering the maps.
  - Added direct regression coverage for multi-period PSA maps and model-facet
    maps so figure layout is tested at the plotting-function level.

- **Notebook config resolution cleanup** *(Changed)*

  - Updated standard tutorial notebooks to let ``notebook_run_context()``
    resolve the committed example config instead of hard-coding the example
    config path in each notebook.
  - Kept dashboard launch helpers using ``context.config_path`` so generated
    commands still point at the active config.
  - Added source-contract coverage so tutorial notebooks keep config discovery
    centralized in the notebook context helper.

2026-06-21
----------

- **Slurm and QC workflow import boundary** *(Changed)*

  - Deferred config-runtime, output-registry, Slurm-compute, and shared table
    imports in metric Slurm, QC Slurm, and QC workflow helpers until scripts
    are written, jobs are submitted, or config-backed QC tables are built.
  - Kept public QC result classes, readiness helpers, Slurm script writers,
    and QC summary helpers importable before optional config parsing
    dependencies are installed.
  - Added source-contract coverage so Slurm and QC workflow helpers do not
    reintroduce top-level config-bound imports.
  - Added a no-site-packages import regression check for the metric and QC
    Slurm entry modules.

- **Metric workflow import boundary** *(Changed)*

  - Deferred config-output, active-config, metric-enrichment, and metric-runner
    imports in metric workflow orchestration helpers until configured planning
    or downstream output writing actually runs.
  - Kept lightweight metric workflow output contracts, input-column helpers,
    and configured workflow entry points importable before PyYAML or SciPy are
    available.
  - Added source-contract coverage for metric workflow import boundaries.

- **Step 1 workflow import boundary** *(Changed)*

  - Deferred config-runtime imports in waveform preprocessing and configured
    ingest workflow helpers so Step 1 result classes, readiness helpers, and
    explicit-path preprocessing utilities can import without PyYAML.
  - Kept active-config and output-registry resolution available at call time
    for config-backed metadata, preprocessing, and record-coverage workflows.
  - Added source-contract coverage for the Step 1 workflow import boundary.

- **Generic table I/O import boundary** *(Changed)*

  - Deferred config-output and active-config imports in ``spatial_vtk.io.tables``
    so generic CSV/Parquet helpers such as ``read_table()``, ``write_table()``,
    ``table_columns()``, and ``table_row_count()`` can run without PyYAML.
  - Kept config-backed output table helpers resolving paths through the same
    output registry at call time.
  - Made metric waveform inventory builders import and write explicit
    CSV/Parquet outputs without importing config dependencies.

- **Lightweight dashboard data imports** *(Changed)*

  - Deferred config-output resolution and shared table I/O imports in
    dashboard contract and export helpers until configured dashboard paths or
    table rows are actually requested.
  - Kept dashboard dataclasses, table contracts, summary loaders, and dataset
    writer helpers importable in minimal environments before PyYAML-backed
    config dependencies are available.
  - Added source-contract coverage so dashboard data helpers do not
    reintroduce top-level config-bound imports.

- **Lightweight metric plan imports** *(Changed)*

  - Deferred config-runtime, config-metric, and shared table I/O imports in
    ``spatial_vtk.io.plans`` until config-backed planning or the metric-plan
    CLI is actually invoked.
  - Kept ``MetricPlan`` and dataframe-only expected-row helpers importable in
    minimal environments before PyYAML-backed config dependencies are
    available.
  - Added source-contract coverage so metric planning helpers do not
    reintroduce top-level config-bound imports.

- **Lightweight metric batch status** *(Changed)*

  - Made metric manifest batch-status checks read only manifest batch
    metadata, so status does not deserialize metric tasks or import the metric
    runner.
  - Kept explicit-manifest ``svtk metrics batch-status`` independent of saved
    config loading, which makes the command usable as a cheap progress check
    even in minimal terminal environments.
  - Added regression coverage for invalid task payloads in status-only
    manifests and for explicit CLI manifest checks that must not load config.

- **Explicit-path metric CLI defaults** *(Changed)*

  - Routed metric inventory, estimate, local-run, waveform-cache,
    batch-merge, and output-writing commands through the shared config-default
    helper.
  - Prevented those commands from loading a saved ``svtk config set`` path when
    all required file paths are provided explicitly.
  - Added source-contract coverage so explicit-path metric commands stay
    independent of ambient config unless ``--config`` or ``--run-scenario`` is
    passed.

- **Explicit-path IO and QC CLI defaults** *(Changed)*

  - Routed event-station preparation, waveform inventory scanning, and manual
    QC queue export commands through the shared config-default helper.
  - Kept those commands independent of saved ``svtk config set`` state when
    users provide all required input and output paths explicitly.
  - Deferred config-bound metadata table imports so explicit dataframe/table
    preparation does not require config parsing dependencies.
  - Added source-contract coverage so these lightweight file commands keep the
    same explicit-path behavior as metric workflow commands.

- **CLI config behavior documentation** *(Changed)*

  - Added a CLI API section that distinguishes config-backed default paths from
    complete explicit input and output paths.
  - Documented that explicit-path commands do not load saved ``svtk config
    set`` state unless ``--config`` or ``--run-scenario`` is passed.
  - Updated source-contract coverage for lightweight CLI CSV/Parquet table
    writes while keeping the shared table-writer fallback for nonstandard
    suffixes.

- **Lightweight table helper imports** *(Changed)*

  - Deferred config-bound table reader and writer imports in metric input,
    master-list, catalog, manual-QC review, and dashboard summary helpers.
  - Kept dataframe-only normalization and summary helper imports usable in
    minimal environments before a Spatial-VTK config or PyYAML is available.
  - Added source-contract coverage that prevents those helper modules from
    reintroducing top-level config-bound table imports.

- **Config-backed sidecar status CLI** *(Changed)*

  - Made ``svtk visualize sidecars status`` resolve the notebook-standard
    sidecar directory from ``--config`` when ``--sidecar-dir`` is omitted.
  - Added ``--figure-kind`` and ``--figure-subdir`` so large-run figure
    families such as metric and spatial plots can be inspected without
    repeating full sidecar paths.
  - Kept explicit ``--sidecar-dir`` behavior and added regression coverage for
    config-backed and missing-config cases.

- **CLI and notebook public import surfaces** *(Changed)*

  - Routed curated ``svtk`` helpers for dashboard paths, preprocessing metadata
    paths, and generic table I/O through the stable ``spatial_vtk.io`` and
    ``spatial_vtk.visualize.dashboard`` package surfaces.
  - Routed notebook dashboard-status and bounded-output-preview helpers through
    the same public package surfaces.
  - Added regression coverage so notebook-facing CLI workflows do not drift
    back to importing directly from lower-level implementation modules.

- **Public documentation import boundary** *(Changed)*

  - Expanded public docs and tutorial-notebook regression coverage so examples
    keep importing from stable workflow surfaces such as
    ``spatial_vtk.metrics``, ``spatial_vtk.metrics.plot``,
    ``spatial_vtk.spatial``, ``spatial_vtk.spatial.plot``,
    ``spatial_vtk.spatial.map``, and ``spatial_vtk.visualize``.
  - Added guards against reintroducing notebook-facing imports from deeper
    implementation modules for metric workflow workers, calculation adapters,
    QC build workers, visualization context/QC/waveform internals, dashboard
    Streamlit entry modules, and spatial path-map internals.

- **Notebook readiness path guard** *(Changed)*

  - Added tutorial-notebook regression coverage that allows source-checkout
    bootstrap path discovery but prevents workflow cells from reintroducing
    direct ``Path.exists()``, ``Path.is_file()``, or ``Path.is_dir()`` checks.
  - Keeps notebook readiness and skip decisions routed through package
    output/status helpers instead of ad hoc path probing in cells.

- **Metric station-map aggregation documentation** *(Changed)*

  - Clarified the Metrics API reference that large-run station maps aggregate
    all selected event-station rows by station identifier rather than exact
    station coordinates, so coordinate jitter does not split one station into
    multiple plotted values.
  - Documented that station-summary rows and source-row sidecars carry input,
    finite, dropped, coordinate, event-count, and aggregation metadata for
    auditing plotted station values and PSA oscillator-period panels.

- **Dashboard optional-tab loading** *(Fixed)*

  - Split metrics-dashboard optional summary loading from map/tab readiness so
    station or event summaries with usable table data are still lazily loaded
    when their maps are blocked by missing coordinate columns.
  - Kept startup warnings and Data Status rows on ``tab_ready`` so map-specific
    blockers remain visible without making the rest of the tab look empty.

- **Dependency metadata consistency** *(Changed)*

  - Removed the stale ``nbsphinx`` entry from the source-checkout conda
    environment because public docs now render notebooks as downloadable
    source assets rather than through a Sphinx notebook renderer.
  - Added regression coverage that keeps
    ``tools/check_validation_environment.py`` module checks aligned with
    declared ``pyproject.toml`` dependencies.

- **Config-first CLI workflow docs** *(Changed)*

  - Simplified the CLI workflow tutorial so ``svtk metrics outputs`` relies on
    the saved config and registered ``prepared_events``/``prepared_stations``
    tables instead of repeating explicit table paths.
  - Updated regression coverage so future CLI tutorial edits do not re-add
    those unnecessary prepared-table flags.

- **Large-run notebook result displays** *(Changed)*

  - Updated the first three large-run driver notebooks so metadata,
    preprocessing, QC, metric-planning, Slurm-script, merge, and downstream
    output steps assign their package result objects and render them through
    ``display_notebook_step_result``.
  - Extended notebook source-contract coverage so heavy cells keep showing
    normalized skipped/submitted/local-run status frames instead of relying on
    implicit cell output or raw dataclass/dictionary displays.

- **CLI config path metavar** *(Changed)*

  - Standardized live ``svtk`` help so optional config-file arguments render as
    ``--config PATH`` across config, I/O, QC, metrics, dashboard, plotting,
    mapping, and visualization commands.
  - Added regression coverage that prevents terminal help from falling back to
    argparse's generic ``--config CONFIG`` placeholder.

- **CLI path placeholder guard** *(Changed)*

  - Added regression coverage that keeps registered plot, map, and visualization
    command help on ``--input-table PATH`` and ``--figure-output PATH`` instead
    of reverting to generic ``--input INPUT`` or ``--output OUTPUT`` usage.
  - Added dashboard help/reference coverage that prevents the old
    ``METRICS_ROOT`` and ``SUMMARY_ROOT`` placeholders from returning to the
    metrics-dashboard command docs.

- **Tutorial setup documentation** *(Changed)*

  - Added the validation-environment preflight to the examples overview and
    large-run notebook README so all tutorial entry points start with the same
    lightweight dependency check.
  - Extended tutorial documentation coverage so the examples index and large-run
    README keep that dependency-check command alongside the README and
    installation guide.

- **Validation-environment preflight** *(Added)*

  - Added a stdlib-only ``tools/check_validation_environment.py`` helper that
    checks the active Python version and importable modules for release,
    tutorial, dashboard, docs, notebook, validation, waveform, or core
    dependency groups.
  - Documented the checker in the release checklist, README, and installation
    guide so missing dependencies are reported before expensive pytest,
    Sphinx, dashboard, or notebook checks start.
  - Added regression coverage for dependency-group expansion and missing-module
    messages.

- **Tutorial notebook helper guard** *(Changed)*

  - Added regression coverage that scans committed tutorial notebooks for
    top-level functions and classes, keeping reusable workflow logic in
    importable package helpers instead of notebook cells.
  - Verified the current tutorial and large-run notebooks pass that
    package-boundary contract.

- **Metrics dashboard tab readiness** *(Fixed)*

  - Made Streamlit metrics-dashboard optional-tab skip decisions honor
    ``tab_ready`` when dashboard summary data exists but the tab cannot render
    correctly, such as station/event map tabs missing coordinate columns.
  - Extended dashboard startup coverage so map-blocked optional tabs are
    reported consistently instead of being treated as fully ready.
  - Clarified the Step 7 Python workflow docs so notebook users can distinguish
    data-level ``ready`` from dashboard-tab-level ``tab_ready``.

- **Direct QC Slurm parser aliases** *(Changed)*

  - Added artifact-named ``--event-station-records``,
    ``--qc-trace-summary-output``, ``--qc-inventory-output``, and
    ``--qc-overlap-inventory-output`` aliases to the direct
    ``spatial_vtk.qc.build.slurm`` worker parser.
  - Kept legacy ``--event-stations``, ``--trace-output``,
    ``--inventory-output``, and ``--overlap-inventory-output`` support and
    added parser coverage for both preferred and legacy forms.

- **Direct PhaseNet parser aliases** *(Changed)*

  - Added artifact-named ``--phasenet-picks``,
    ``--phasenet-input-records``, and ``--arrival-pick-catalog-output``
    aliases to the direct ``spatial_vtk.metrics.calculate.phasenet_adapter``
    parser.
  - Kept legacy ``--phasenet-csv``, ``--records-csv``, and ``--output``
    support and added parser coverage for both preferred and legacy forms.

- **Direct metric batch parser alias** *(Changed)*

  - Added artifact-named ``--metric-manifest`` to the direct
    ``spatial_vtk.metrics.workflow.execution`` batch runner parser.
  - Kept legacy ``--manifest`` support and added parser coverage for both
    preferred and legacy forms.

- **Direct metric task-runner input flag** *(Changed)*

  - Added ``--tasks-table`` as the preferred input flag for the direct metric
    task-runner module so CSV and Parquet task tables are not described with a
    CSV-only option name.
  - Kept ``--tasks-csv`` as a legacy alias and added parser regression
    coverage for both spellings.

- **Direct master-list parser aliases** *(Changed)*

  - Added artifact-named ``--station-tables``, ``--master-station-output``,
    ``--event-tables``, and ``--master-event-output`` aliases to the direct
    ``spatial_vtk.io.master_lists`` module parser.
  - Kept legacy ``--input`` and ``--output`` spellings for existing scripts
    and added parser coverage for both preferred and legacy forms.

- **Direct waveform parser output alias** *(Changed)*

  - Added artifact-named ``--trace-metadata-output`` to the direct
    ``spatial_vtk.io.waveforms`` metadata parser so the output role is clear
    in scripts.
  - Kept legacy ``--output`` support and added parser coverage for both
    spellings.

- **Direct metric Slurm parser aliases** *(Changed)*

  - Added artifact-named ``--metric-manifest`` and
    ``--metrics-slurm-script-output`` aliases to the direct
    ``spatial_vtk.metrics.workflow.slurm`` parser.
  - Kept legacy ``--manifest`` and ``--output`` support and added parser
    coverage for both preferred and legacy forms.

- **CI wheel-content gate** *(Changed)*

  - Aligned the CI wheel-inspection step with the public release checklist so
    CI also requires packaged config data and rejects repository-only content
    prefixes.
  - Added regression coverage that keeps the workflow and release checklist
    wheel-content guardrails in sync.

- **Direct metric-plan parser aliases** *(Changed)*

  - Added artifact-named ``--qc-inventory``, ``--metrics-table``, and
    ``--missing-metrics-output`` aliases to the direct
    ``spatial_vtk.io.plans`` metric-completeness parser.
  - Kept legacy ``--inventory``, ``--metrics``, and ``--missing-output``
    support and added parser coverage for both preferred and legacy forms.

- **Direct metric task-runner output alias** *(Changed)*

  - Added artifact-named ``--metric-rows-output`` to the direct
    ``spatial_vtk.metrics.workflow.run`` task-runner parser.
  - Kept legacy ``--output`` support and extended parser coverage for both
    preferred and legacy output spellings.

- **Master-list CLI defaults** *(Changed)*

  - Made ``svtk io master-stations`` and ``svtk io master-events`` resolve
    their standard inputs and outputs from the active config, matching the
    other Step 1 I/O commands when explicit table paths are omitted.
  - Updated generated CLI reference coverage so those commands advertise
    artifact-named flags, config-backed defaults, and legacy ``--input`` /
    ``--output`` aliases consistently.

- **Table-format wording** *(Changed)*

  - Standardized current CLI help, API docs, generated CLI reference pages,
    and table-helper docstrings on ``CSV or Parquet`` wording so public table
    format support is described consistently.
  - Added regression coverage that rejects mixed ``CSV/parquet`` and
    ``CSV/Parquet`` phrasing in current user-facing help and docs sources.

- **Workflow import guidance** *(Fixed)*

  - Cleaned the configuration guide's Python examples so metric settings are
    imported from the public ``spatial_vtk.config`` namespace and active-config
    guidance points notebooks toward standard workflow result helpers instead
    of direct table read/write patterns.
  - Reworded Config API figure-helper guidance so routine notebooks are
    directed to workflow result-object figure methods, while figure settings
    and ``render_notebook_figure`` are framed as package/custom-helper
    building blocks.
  - Cleaned the I/O API entry-point import example so it starts with
    task-level ingest/preprocessing/record-coverage helpers instead of
    lower-level output-group and table-read/write utilities.
  - Reworded Metrics API figure-context guidance so ``MetricFigureContext`` is
    presented as a script/custom-extension tool, while notebooks stay on the
    Step 3 result object's figure methods.
  - Reworded the Step 4 spatial map workflow guide and spatial-map package
    docstring so notebooks start from the standard spatial workflow result
    object's ``write_map_figures(...)`` method instead of direct plot-helper
    imports.
  - Reworded Step 2/6 waveform-comparison workflow guidance so notebooks use
    QC or additional-plotting result-object methods, with direct waveform
    writers framed as script/custom-orchestration helpers.
  - Aligned the Visualize API waveform guidance with the same result-object
    contract so direct waveform writers are no longer described as the primary
    notebook path.
  - Removed the direct waveform-comparison writer from the Visualize API
    notebook-facing import example and relabelled it as a lower-level
    result-object delegate or script helper.
  - Updated regression coverage so workflow docs keep result-object methods
    as the notebook-facing path for spatial maps and waveform comparisons.
  - Cleaned the Spatial API focused-script plotting example so it shows
    individual plot functions instead of mixing direct suite writers into the
    first import block.

- **API import-boundary wording** *(Changed)*

  - Tightened the I/O API entry-point guidance so notebooks are told to use
    stable ``spatial_vtk.io`` re-exports instead of reaching into
    implementation modules, with regression coverage for that public wording.
  - Aligned the ``spatial_vtk.config`` package docstring with the same
    re-export-first rule for notebook-facing config helpers.
  - Reworded the Spatial API map section so public map imports are framed for
    focused scripts and custom extensions, while routine notebooks are kept on
    standard result-object figure helpers.
  - Reworded the Visualize API context, QC, and waveform family sections so
    routine notebooks use top-level re-exports or result-object figure methods,
    while family subpackage imports are framed for scripts and extensions.
  - Reworded the Metrics API calculation section so routine notebooks start
    from Step 3 workflow/result-object helpers, while calculation-level imports
    are framed for scripts and custom extensions.

- **Tutorial runtime and preview checks** *(Fixed)*

  - Improved tutorial runtime-check failures so missing-dependency messages
    include both the generic source-checkout commands and exact install/check
    commands for the Python executable that failed the runtime check.
  - Added a tutorial runtime Python-version guard so source-checkout users see
    the supported ``>=3.10,<3.14`` requirement before missing-dependency
    diagnostics from an unsupported interpreter.
  - Hardened QC overview bounded reads so DataFrame previews clamp negative
    row limits to zero and path-backed previews keep using the bounded table
    reader instead of falling through to full-table parquet reads.
  - Fixed output status tables so user-home paths such as ``~/outputs`` are
    expanded before existence checks and displayed through the ``resolved_path``
    column.
  - Aligned public tutorial-check commands in the README, installation guide,
    examples index, large-run README, and CI preflight so runtime notebook
    checks use a writable ``MPLCONFIGDIR`` instead of relying on user-level
    matplotlib cache locations.
  - Updated tutorial missing-dependency diagnostics so the suggested rerun
    commands use the same writable ``MPLCONFIGDIR`` prefix as the public
    tutorial docs and release checks.
  - Aligned README and release-checklist Python-version guidance with the
    declared ``>=3.10,<3.14`` package range and the tutorial waveform stack.
  - Added Python 3.13 to package classifiers and CI coverage so public package
    metadata and validation match the declared supported range.
  - Added PhaseNet to the tutorial runtime preflight so arrival-pick workflow
    dependencies are reported before notebooks or generated workers run.
  - Routed large-run checkpoint and metric-batch CSV header probes through the
    shared table-column helper so schema-only reads use consistent table
    defaults and avoid warning-prone ad hoc ``read_csv`` calls.

- **Notebook source-contract checks** *(Fixed)*

  - Tightened tutorial notebook contract checks so brittle parent-directory
    bootstrap cells using ``Path("..")`` are rejected alongside
    ``Path("../")`` variants.
  - Reworked the parent-directory notebook bootstrap check to use AST call
    detection, so equivalent forms such as ``pathlib.Path("../docs")`` are
    caught by the same source-contract preflight.
  - Hardened tutorial example-data preflight so malformed
    ``selected_event_stations.csv`` files report missing ``event_id`` or
    ``station`` columns before notebook execution.
  - Hardened the same tutorial preflight to report row numbers when
    ``selected_event_stations.csv`` has blank ``event_id`` or ``station``
    values instead of silently skipping waveform-file checks for those rows.
  - Tightened tutorial notebook public-import checks so lower-level
    ``spatial_vtk.config.metrics`` imports are rejected in favor of the public
    ``spatial_vtk.config`` namespace already used by the notebooks.
  - Extended the same notebook preflight guardrail to
    ``spatial_vtk.config.notebook`` imports so tutorial cells keep using the
    public ``spatial_vtk.config`` namespace for notebook helpers.
  - Extended the same public-import guardrail to
    ``spatial_vtk.config.paths`` so notebook path helpers also come through
    the stable ``spatial_vtk.config`` namespace.
  - Extended tutorial notebook CLI-regression coverage to reject
    ``get_ipython().system(...)`` shell calls in addition to direct subprocess
    and ``!svtk`` patterns.
  - Made tutorial notebook source-contract diagnostics actionable by naming
    the package workflow, result-object, table-loader, or figure-helper pattern
    that should replace each forbidden shell, path, table, or DataFrame idiom.
  - Extended tutorial notebook source-contract checks to reject additional
    notebook-local DataFrame filtering, joining, aggregation, reshaping,
    ordering, and de-duplication idioms that should live in package helpers.

- **Workflow readiness and dashboard parsing** *(Fixed)*

  - Tightened QC and metrics dashboard row-limit, download-limit,
    display-limit, and summary-chunksize parsing so explicit
    ``all``/``none``/``unlimited`` values remain the only full-table opt-in
    where supported, while invalid numeric limits now raise clear
    configuration errors instead of silently changing load behavior.
  - Hardened notebook output-readiness checks so an empty output collection
    raises a clear error instead of reporting the step as current and skipped.
  - Applied the same empty-output guard to lower-level output-existence and
    rebuild helpers so path-based workflow checks cannot silently no-op when
    no targets are configured.
  - Added the compact dashboard readiness summary to
    ``svtk dashboard status --json`` so machine-readable status output includes
    the same tab/input readiness view shown in human output.
  - Clarified metrics dashboard startup warnings so map-only tab blockers,
    missing summary tables, and missing row-level datasets are reported as
    dashboard input or tab readiness issues rather than only summary-table
    failures.
  - Added workflow-doc regression coverage so notebook guidance keeps using
    stable package import surfaces and does not reintroduce metrics plotting
    implementation-module paths.
  - Routed QC helper-local table loading through the shared I/O table reader so
    CSV dtype handling and Parquet dispatch stay centralized for large-run
    checkpoints and derived QC tables.
  - Routed metric task-planning path reads through the same shared table reader
    so task manifests, summaries, and fallback table inputs use consistent
    CSV/Parquet behavior.
  - Routed metric downstream-output table reads through the shared reader while
    preserving existing column projection for large metric tables.
  - Routed unscoped metric input table normalization through the shared reader
    while preserving specialized scoped QC chunking and Parquet predicate
    pushdown for large inventories.
  - Routed metric enrichment metadata and master station/event list input
    readers through the shared table loader so metadata-side CSV/Parquet
    handling matches the rest of the workflow.
  - Routed notebook-facing QC overview and context-figure full-table reads
    through the shared loader while preserving bounded preview behavior.

- **CLI submission feedback** *(Fixed)*

  - Made ``svtk metrics slurm --submit`` print normalized submission details,
    including the written script path and parsed job id, even when ``sbatch``
    stdout is empty or scheduler-specific.

- **Table reader consistency** *(Changed)*

  - Routed manual QC decision and arrival-pick catalog loading through the
    shared table reader so these small public helper paths use the same
    CSV/Parquet behavior as larger workflow artifacts, and aligned manual QC
    decision docstrings with that shared table support.
  - Routed public station, event, and event-station metadata loaders through
    the shared table reader and updated their docstrings so they are no longer
    described as CSV-only helpers, including master-list table inputs.
  - Routed dashboard summary and dashboard metric export readers through the
    shared table reader while preserving supported-format validation and
    selected-column loading.
  - Routed optional event patch/context table loading through the shared table
    reader and updated catalog wrapper docstrings so public context helpers no
    longer imply CSV-only inputs.
  - Routed generic CLI input-table loading through the shared table reader so
    ``svtk`` metadata, plot, map, visualization, and metric-plan completeness
    commands use the same CSV/Parquet behavior as package APIs.
  - Routed generic CLI table-output writing through the shared table writer so
    ``svtk`` commands get the same atomic write and suffix handling as package
    APIs.
  - Routed dashboard summary-table and metric dataset writes through the
    shared table writer so dashboard exports keep atomic-write behavior while
    preserving stale cross-format cleanup and partitioned dataset layouts.
  - Routed manual QC decision, manual-review queue, trace-metadata,
    arrival-pick catalog, geology-contrast, GeoJSON summary, and master-list
    helper writes through the shared table writer while preserving explicit
    ``overwrite=False`` behavior and matching CLI help text.
  - Added a shared ``table_columns()`` helper for schema-only CSV/Parquet
    inspection and routed dashboard, metric workflow, metric batch merge, and
    large-run plotting column probes through it.
  - Routed QC lookup and spatial/GeoJSON schema probes through the same helper
    so selected-column reads avoid duplicating CSV header and Parquet metadata
    logic.

- **Tutorial notebook hygiene** *(Fixed)*

  - Hardened tutorial notebook source-contract checks so saved widget/UI
    metadata state is rejected alongside execution counts and saved cell
    outputs.
  - Extended the same notebook source-contract checks to reject saved per-cell
    runtime metadata such as execution timestamps, and stripped those stale
    metadata blocks from checked-in tutorial notebooks.
  - Extended the tutorial notebook source-contract checks to reject
    ``get_ipython().system(...)`` shell calls, closing the same CLI-workflow
    escape path already blocked for ``!svtk`` and ``subprocess.run(...)``.
  - Added Purpose/Outputs notes to every standard tutorial notebook section so
    the lightweight examples document each task and produced artifact as
    clearly as the large-run notebooks.
  - Extended tutorial notebook source-contract checks to reject
    under-documented section headings that omit Purpose/Outputs notes.
  - Improved CLI missing-dependency diagnostics so import aliases such as
    ``yaml`` name their installable package, for example ``PyYAML``.

- **Notebook status-frame vocabulary** *(Changed)*

  - Normalized ``SlurmSubmission.status_frame()`` so notebook-displayed Slurm
    submissions include ``name``, ``artifact_label``, ``resolved_path``,
    ``path``, and ``exists`` columns while preserving ``script_path``.
  - Expanded ``StandardQCInputResult.status_frame()`` so Step 2 notebooks show
    loaded input row counts and configured QC output paths in one normalized
    status table.
  - Normalized figure result status tables so context, QC, waveform, and
    sidecar helpers expose ``artifact_role`` and a derived ``status`` alongside
    ``artifact_label``, ``resolved_path``, ``path``, and ``exists``.
  - Kept the same normalized figure status vocabulary in Step 3 metric plotting
    result objects, including focused station metric maps and standard metric
    diagnostic/suite status frames.
  - Applied the same normalized figure status vocabulary to Step 4 spatial,
    Step 5 GeoJSON/corridor, Step 6 additional-plotting, and compact spatial
    summary figure result objects.
  - Normalized dashboard preparation and launch status frames so notebook
    dashboard cells expose the same ``resolved_path``, ``path``, and ``exists``
    columns as dashboard readiness and output status tables.
  - Normalized generic output path rows, output-group status rows, output
    readiness rows, and compact I/O workflow summary frames with
    ``artifact_label``, ``artifact_role``, and ``status`` columns.

- **Dashboard launch and release checks** *(Fixed)*

  - Added dashboard launch port validation so invalid ports or impossible
    auto-port search ranges raise clear configuration errors before Streamlit
    startup.
  - Made dashboard CLI launch messages print browser-friendly URLs for
    wildcard bind addresses such as ``0.0.0.0`` while still passing the
    requested bind address to Streamlit.
  - Hardened those dashboard CLI launch URLs for IPv6 literals by printing
    bracketed hosts such as ``[::1]`` while preserving the actual server bind
    address.
  - Broadened public-release privacy regression coverage so private run paths
    and cluster-specific tokens are rejected across public docs, notebooks,
    package source, tooling, workflow files, and package metadata.
  - Added ``git diff --check`` as an explicit CI and release-checklist gate so
    whitespace regressions are caught before release validation continues.
  - Expanded the CI and release-checklist compile gate to include ``tools`` so
    notebook execution and CLI reference scripts are syntax-checked with the
    package and tests.
  - Tightened release-checklist regression coverage so the documented notebook
    runtime dependency check remains part of the required validation sequence.
  - Added exact-set regression coverage for tutorial runtime module checks so
    notebook-critical dependency additions or removals require an intentional
    test update.
  - Added regression coverage that every tutorial runtime module check maps to
    a declared base or tutorial-extra dependency in ``pyproject.toml``.

2026-06-19
----------

- **Config-path workflow stabilization** *(Changed)*

  - Expanded config-path support across output resolvers, workflow helpers,
    plotting/status helpers, dashboard contracts, and result objects so
    notebooks and scripts can pass explicit config files without activating
    global config state first.
  - Standardized user-facing path/status tables around ``resolved_path`` while
    preserving legacy ``path`` aliases for existing notebooks and scripts.
  - Promoted artifact-named CLI flags for QC, metrics, spatial, GeoJSON,
    dashboard, IO, plot, map, and visualization commands while preserving
    legacy generic aliases for compatibility.

- **Notebook and dashboard workflow contracts** *(Changed)*

  - Moved notebook display, readiness, summary, and result-status formatting
    into package helpers so tutorial cells show labelled tables instead of
    raw dictionaries, dataclasses, or repeated path variables.
  - Hardened dashboard and figure readiness diagnostics so notebooks,
    Streamlit tabs, CLI status output, and Slurm logs expose missing schema,
    missing map coordinates, empty value columns, stale datasets, and rebuild
    guidance without loading full large-run tables.
  - Promoted notebook-safe dashboard readiness, contract, filtering, preview,
    and bounded loading helpers to ``spatial_vtk.visualize`` while preserving
    the ``spatial_vtk.visualize.dashboard`` family import path for dashboard
    scripts.
  - Updated workflow-guide and large-run README dashboard examples to import
    routine dashboard helpers from ``spatial_vtk.visualize``.
  - Scoped path-backed long metric-table reads during dashboard metric dataset
    export so large-run dashboard preparation streams only the columns needed
    by dashboard summaries while preserving full reads for wide legacy metric
    matrices.
  - Added preprocessed-specific path aliases and a compact status frame to
    waveform preprocessing result objects while preserving generic legacy path
    fields.
  - Added ``SlurmSubmission.status_frame()`` so submitted notebook and workflow
    jobs expose job id, script path, command, stdout, stderr, and return code
    without printing raw dataclass representations.
  - Standardized context, QC, and waveform-comparison figure result
    ``status_frame()`` outputs so notebook tables expose ``name``,
    ``artifact_label``, ``resolved_path``, ``path``, and ``exists`` while
    preserving legacy figure/table path columns.

- **Figure status-frame contracts** *(Changed)*

  - Added normalized path columns to ``MetricFigureContext.status_frame()`` for
    metric input, figure directory, and sidecar directory rows while preserving
    the existing scalar ``name``/``value`` notebook display.
  - Standardized ``StandardMetricDiagnosticFigureResult.status_frame()`` so
    Step 3 diagnostic figure rows include normalized figure path columns while
    preserving ``figure_path`` and ``figure_exists``.
  - Standardized standard Step 5 GeoJSON region and corridor figure
    ``status_frame()`` outputs so notebook tables expose normalized figure
    path columns while preserving legacy figure path fields.
  - Standardized Step 6 additional plotting, region figure, and region boxplot
    ``status_frame()`` outputs around normalized figure path columns and
    preserved sidecar provenance fields.
  - Added normalized first-figure path columns to metric and spatial
    multi-figure suite ``status_frame()`` outputs while preserving exact
    ``figure_paths`` lists and preview fields.
  - Added normalized sidecar-directory path columns to
    ``NotebookFigureSidecarSettings.readiness_frame()`` so notebooks show
    whether figure provenance metadata can be inspected.
  - Added config and dashboard-output existence flags to
    ``NotebookDashboardCommands.status_frame()`` so dashboard launch cells show
    missing metrics, summary, or QC inputs before starting Streamlit.

- **Dashboard and workflow status-frame contracts** *(Changed)*

  - Standardized ``MetricWaveformCacheResult.status_frame()`` so metric cache
    notebook status tables expose artifact names, roles, readiness status,
    normalized paths, row counts, and cache reuse counters.
  - Standardized ``DashboardLaunchResult.status_frame()`` so dashboard launch
    cells expose artifact names, labels, roles, launch status, ports, fallback
    commands, URLs, process ids, and error messages in the same status-table
    vocabulary used by other notebook workflow helpers.
  - Standardized ``DashboardDatasetPreparationResult.preparation_frame()`` and
    ``written_frame()`` so dashboard preparation cells expose artifact names,
    labels, roles, status, normalized paths, and existence checks without
    notebook-local formatting.
  - Added explicit ``artifact`` ids to ``DashboardOutputReadiness.status_frame()``
    rows so dashboard readiness displays line up with the artifact vocabulary
    used by workflow output, preparation, launch, and figure status tables.
  - Standardized ``MetricWaveformInventoryResult.status_frame()`` so observed
    and synthetic metric inventory rows expose artifact ids, labels, roles,
    readiness status, normalized paths, row counts, and reuse flags.
  - Standardized ``WaveformPreprocessingWorkflowResult.status_frame()`` so
    direct preprocessing calls expose preprocessed event-station, manifest, and
    trace-metadata artifacts with ids, labels, roles, readiness status,
    normalized paths, and row counts.
  - Standardized metric manifest and batch-status frames so large-run Step 3
    planning, Slurm submission, and merge-readiness displays expose artifact
    ids, labels, roles, ready/missing or complete/incomplete status, normalized
    manifest paths, and completion counts.
  - Standardized ``NotebookDashboardCommands.status_frame()`` so dashboard
    launch-plan cells expose dashboard artifact ids, labels, roles,
    command/requested-launch status, configured input paths, and existence
    checks without notebook-local path handling.
  - Standardized ``NotebookFigureSidecarSettings.readiness_frame()`` so figure
    provenance readiness cells expose sidecar artifact ids, labels, roles,
    compact status, configured directory paths, and existence checks while
    preserving the existing ``name``/``value`` display.
  - Standardized ``NotebookFigureRenderGate.status_frame()`` so figure
    prerequisite cells expose artifact ids, labels, roles, compact
    ``ready``/``disabled``/``missing_inputs`` status, messages, and exact
    missing input paths.

- **CLI help and generated-reference wording** *(Changed)*

  - Clarified metrics CLI help for manifest batch output directories,
    ``--batch-size``, and ``--batch-count`` so Slurm array sizing is explicit.
  - Reworded metric workflow Slurm/task docs to describe metric manifest
    arrays instead of generic Slurm scripts.
  - Corrected the generated config-backed plotting example for
    ``svtk plot metrics residuals-vs-distance`` to use ``--y-col
    log2_residual`` instead of the score-distribution ``--score-col`` flag.
  - Reworded the ``svtk metrics outputs`` override-directory help from vague
    ``ad hoc`` wording to a clear custom downstream metric output directory
    description.
  - Reworded the generated ``band-score-distribution`` CLI summary to describe
    residual or score distributions, matching the default ``log2_residual``
    example instead of implying the plot is GOF-score only.
  - Aligned band and period distribution plot docstrings and default titles
    with residual-or-score usage so Python API docs match the stabilized
    large-run metric plotting workflow.
  - Clarified ``--score-col`` CLI help and examples so distribution plots are
    described as taking a numeric residual or score value column rather than a
    score-only input.
  - Tightened generated API fallback parameter descriptions for generic path
    and table names so explicit overrides are distinguished from standard
    config-resolved workflow artifacts.

- **Workflow result-object wording** *(Changed)*

  - Clarified public workflow docs so lower-level notebook step helpers and
    custom plot helpers are described as explicit/custom-script tools, while
    standard notebooks are steered toward result-object methods.
  - Reworded notebook execution-helper docstrings so the readiness-aware
    wrapper remains the documented default for heavy notebook steps, while
    direct function execution is described as an explicit primitive for callers
    that already own readiness and skip logic.
  - Reworded skipped-step result helper guidance so standard workflow result
    objects remain the default owner of skipped ``run_*_step_if_needed()``
    payloads, while ``notebook_step_result`` is framed as a custom-workflow
    fallback helper instead of notebook-local dictionary construction.
  - Reworded workflow-guide output-group guidance so standard result objects
    remain the default notebook object and reusable output groups are described
    as artifact-named helpers for custom or compatibility paths.
  - Reworded Python workflow display-helper guidance to use skipped/current
    step payload terminology consistently with the config API docs.
  - Reworded the Python workflow guide introduction so notebook-facing package
    outputs are described as status payloads, result objects, or labelled
    frames rather than generic metadata dictionaries.
  - Reworded package overview and output-group table-loader docs from path
    dictionaries and dictionary keys to path mappings and mapping keys.
  - Reworded Metrics API result-object guidance to describe avoiding
    manifest, metric-row, and output-table path plumbing in notebook cells.
  - Reworded Python workflow output-group guidance so notebook cells avoid
    repeated path plumbing rather than repeated path variables.
  - Reworded Spatial API Step 4-6 helper descriptions so result loaders avoid
    notebook-local path/table plumbing instead of output-group table mappings.

- **Metric plotting and dashboard wording** *(Changed)*

  - Renamed the standard Step 3 diagnostic wording from ``GOF-distance`` and
    generic band-distribution language to explicit residual-distance,
    score-trend, and band residual-distribution diagnostics so tutorial text
    matches the figure artifacts the package writes.
  - Aligned band and period distribution plot docstrings and default titles
    with residual-or-score usage so Python API docs match the stabilized
    large-run metric plotting workflow.
  - Clarified dashboard readiness value-family wording so Visualize API docs
    describe residual, GOF score, observed, synthetic, and other configured
    metric-value coverage without vague generic terminology.
  - Renamed the standard large-run scatter, box, and heatmap diagnostic suite
    artifact from generic metric diagnostics to standard metric diagnostics,
    while preserving the old method name as a compatibility wrapper.
  - Updated metric API and notebook-setting docs so standard diagnostic figure
    controls use standard diagnostic wording instead of generic diagnostic
    terminology.

- **Workflow API contract wording** *(Changed)*

  - Reworded remaining notebook-facing workflow/API docs from raw dictionary
    phrasing to labeled mappings, status payloads, and product-frame mappings
    where the package returns structured display data.
  - Aligned notebook-step result docstrings and config API docs around status
    payload terminology so skipped/current workflow gates are not described as
    raw dictionaries.
  - Aligned internal CLI call/result helper docstrings with the public
    ``svtk call`` guidance so direct public-function calls are consistently
    framed as advanced one-off usage rather than generic workflow commands.
  - Reworded QC API standard-input guidance so Step 2 notebooks avoid Step 1
    path/table plumbing rather than output-group table mapping.
  - Reworded configuration output-registry guidance so notebooks and scripts
    avoid hard-coded path plumbing rather than path variables.
  - Made Step 1 summary-result mapping compatibility declare an explicit
    abstract ``as_dict()`` contract with a descriptive implementation error.
  - Replaced synthetic-format ``NotImplementedError`` cases with user-facing
    runtime or schema errors for unsupported HDF5 adapters and malformed
    Salvus receiver files.
  - Added a warning when unreadable preprocessing trace-metadata caches force
    fast-resume waveform reuse without cached trace metadata.
  - Standardized package-local full-table CSV readers on stable dtype
    inference to avoid mixed-type warnings in large-run QC, metric, metadata,
    visualization, and CLI workflows.

- **Public surface guardrails** *(Fixed)*

  - Aligned API docs, generated CLI reference, workflow guides, README
    install guidance, and tutorial notebooks with the stabilized public import
    surfaces and result-object workflow.
  - Added regression coverage for config-path resolution, public API exports,
    notebook import boundaries, dashboard readiness fields, runtime install
    guidance, and changelog formatting.

- **Config and I/O API example guardrails** *(Fixed)*

  - Reworded the runtime configuration module example so scripts see the
    explicit ``SpatialVTKConfig`` load path while notebooks are steered toward
    ``notebook_run_context()`` instead of individual path resolution.
  - Aligned Configuration API regression coverage with the current
    ``load_standard_*`` result-object guidance so stale output-group-first
    wording is not accepted as the notebook path contract.
  - Reworded low-level metric Slurm readiness docstrings so routine notebooks
    are directed to the standard metric workflow result object's
    ``run_slurm_step_if_needed(...)`` method, while direct readiness objects
    remain documented for custom orchestration that already owns manifest
    status.
  - Reworded the I/O output-path module example so notebooks start from the
    standard ingest workflow result and direct ``output_group()`` or
    ``default_output_paths()`` usage is framed as custom-script/package-helper
    access.
  - Reordered the I/O API helper table so the standard Step 1 ingest workflow
    result loader appears before lower-level output-group helpers, and removed
    the duplicate ingest-loader entry.
  - Reworded metric downstream-output module examples so Step 3 notebooks use
    the standard metric workflow result object and direct metric row writers
    are framed as custom-script helpers.

- **Plotting API example guardrails** *(Fixed)*

  - Reworded metric plotting package and API examples so Step 3 notebooks use
    the standard metric workflow result object's figure-suite method instead
    of passing ``metrics_long_path`` into direct plotting helpers.
  - Reworded the Metrics API plotting import example so focused scripts start
    with individual plotting functions, while direct Step 3 suite writers are
    framed as lower-level script or compatibility helpers.
  - Reworded the large-run README and workflow-guide metric-figure examples
    so notebook users start from the standard metric output result instead of
    importing direct plotting-suite helpers.
  - Reworded Spatial API plotting examples so Step 4 notebooks start from the
    standard spatial workflow result object, while direct spatial plotting
    imports are framed as focused-script helpers.
  - Reordered Spatial API plotting helper guidance so Step 4/5/6 result
    loaders and result-object methods appear before direct large-run writer
    helpers.
  - Reworded Step 6 region-boxplot workflow guidance so notebooks use the
    standard additional-plotting output result method, with direct region
    boxplot helpers framed as script APIs.

- **Dashboard and workflow API example guardrails** *(Fixed)*

  - Reworded Step 7 dashboard-preparation workflow guidance so notebooks use
    the dashboard preparation result object, with direct dashboard dataset
    writers framed as script APIs.
  - Reworded dashboard launch workflow guidance so notebooks use the
    notebook dashboard launch settings plus the configured launch wrapper,
    with one-dashboard launch helpers framed as script APIs.
  - Reordered Visualize API dashboard-helper guidance so the notebook-facing
    dashboard preparation and launch wrappers appear before lower-level script
    helpers in both public helper tables.
  - Reworded the preprocessing direct-call example so advanced scripts prefer
    config-backed output resolution instead of a literal preprocessed-output
    directory.
  - Reworded dashboard export examples so notebooks start from configured
    dashboard dataset preparation and raw dataset writers are framed as
    custom-script APIs.
  - Reworded metric manifest execution examples so advanced snippets use
    caller-owned manifest and batch-output variables instead of hard-coded
    filenames.

- **Workflow documentation guardrails** *(Fixed)*

  - Reworded public workflow docs from ad-hoc/manual phrasing toward
    custom-script and notebook-local-gate wording.
  - Removed stale lower-level workflow and plotting implementation import
    paths from public workflow docs while preserving public namespace guidance.
  - Made tutorial notebook runtime-check failures name the active Python
    executable and the exact runtime-check command to rerun after installing
    notebook extras.
  - Reworded the public release checklist so it refers to private planning
    files generically while ``.gitignore`` retains the concrete ignored
    patterns.
  - Expanded notebook dashboard launch status frames with server address,
    auto-port, proxy-mode, show/headless, and browser URL provenance so remote
    dashboard launch cells are easier to debug.
  - Normalized ``MetricWorkflowManifest.status_frame()`` with ``name``,
    ``artifact_label``, ``resolved_path``, ``path``, and ``exists`` columns
    while preserving legacy manifest-path aliases.
  - Reworded lazy I/O package loader docs so public API references describe
    resolved public helpers instead of implementation-module plumbing.

- **Result-owned workflow runner guidance** *(Fixed)*

  - Reworded config-backed metric workflow module docs so large-run notebooks
    are steered to the standard metric result object instead of direct helper
    calls wrapped in notebook readiness plumbing.
  - Reworded Step 4 spatial readiness docs so large-run notebooks are steered
    to the standard spatial result object's summary runner instead of direct
    readiness-helper wiring.
  - Reworded metric Slurm readiness docs so Step 3 notebooks are steered to
    the standard metric result object's Slurm runner instead of direct
    readiness-helper wiring.
  - Expanded top-level Step 5/6 spatial workflow loader docs so API references
    show the result-owned runner, preview, waveform, and region-boxplot methods
    that keep large-run notebooks lightweight.
  - Reworded Step 2 QC readiness docs so notebooks are steered to the standard
    QC result object's inventory, overlap, and summary runners instead of
    direct readiness-helper wiring.

- **Large-run artifact guardrails** *(Fixed)*

  - Streamed metric batch merges directly into the merged CSV/Parquet output so
    large metric runs no longer need to materialize every batch table before
    writing ``metric_rows``.
  - Hardened figure sidecar JSON metadata writing so numpy/pandas scalar
    values, missing values, timestamps, non-finite floats, and sets from
    aggregation audits serialize reliably for large-run figure provenance.

- **Step 1 workflow helpers** *(Added)*

  - Added a standard Step 1 ingest output loader for combined ingest and
    preprocessing output status.
  - Added typed Step 1 metadata, preprocessing, and record-coverage result
    objects with mapping-compatible access, ``summary_frame()`` methods for
    notebook display helpers, and ``summary_message()`` strings for scripts and
    logs.
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
  - Added ``MetricWorkflowManifest.status_frame()`` so metric planning exposes
    task count, batch count, batch output directory, per-batch task range, and
    first/last batch outputs before Slurm submission.
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
  - Added artifact-specific path aliases and compact status frames to direct
    GeoJSON region-summary and boundary-corridor workflow result objects.
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
  - Added artifact-specific path aliases and a compact status frame to metric
    waveform inventory result objects, and included those aliases in CLI JSON
    output.
  - Added artifact-specific path aliases and a compact status frame to
    metric-ready waveform cache result objects.

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
  - Removed remaining one-off setup-cell prints for preprocessing error
    policy, QC overlap scope, and metric batch count so large-run notebooks
    rely on the shared context and metric-settings displays.

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

- **Standard notebook display cleanup** *(Rewired)*

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
  - Split the QC API import example into notebook-facing result loaders and
    direct config-backed helpers for scripts, generated workers, and custom
    orchestration.

- **Metrics API import guidance** *(Changed)*

  - Split the Metrics API import example into notebook-facing workflow result
    loaders and direct config-backed metric helpers for scripts, generated
    workers, and custom orchestration.

- **Spatial and workflow API documentation** *(Changed)*

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

- **Spatial API import guidance** *(Changed)*

  - Split the Spatial API import examples into notebook-facing result loaders,
    direct config-backed helpers for scripts/workers/custom orchestration, and
    individual plot/map functions for focused scripts.

- **Step 5 workflow guidance** *(Changed)*

  - Clarified Python workflow guidance so Step 5 notebooks use the GeoJSON
    output-status result for heavy summary/corridor gates and the plotting
    input result for region/corridor figure suites.
  - Framed direct configured GeoJSON workflow functions and configured path
    keys as script/custom-orchestration APIs rather than routine notebook
    cell patterns.

- **Output-registry and workflow docstrings** *(Changed)*

  - Updated I/O reference docs and the output-registry module docstring so
    standard workflow result loaders are presented before ``output_group()``
    for routine notebooks, with ``output_group()`` and ``resolve_output_path()``
    framed as grouped-artifact and single-artifact script helpers.
  - Updated Configuration API output-path guidance so routine notebooks start
    from standard workflow result loaders, while output groups and
    ``resolve_output_path()`` are framed as custom-helper and script APIs.
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

- **Figure and map docstrings** *(Changed)*

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
  - Updated the shell workflow tutorial to rely on ``svtk config set`` instead
    of repeating ``--config "$CONFIG"`` on every command, while keeping the
    tutorial run scenario explicit.
  - Updated ``svtk ... list`` discovery output for plot, map, and visualization
    commands so required explicit inputs name the table role, such as
    ``required:spectrogram table (--input-table PATH)``, instead of only
    naming a generic flag.
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
    with plot/map list commands, and
    ``required:<role> (--input-table PATH)`` entries explain when explicit
    input tables are still required.
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
  - Clarified ``required:<role> (--input-table PATH)`` CLI figure guidance so
    commands that need caller-supplied tables are documented as intentional
    advanced inputs rather than missing registered defaults.

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
  - Made bounded dashboard parquet readers fail with an actionable metadata or
    batch-iteration error instead of falling back to full-table materialization
    when streaming reads fail.
  - Made remaining full-table dashboard CSV reads use stable dtype inference
    so mixed station/event identifiers do not emit pandas ``DtypeWarning``
    messages or vary by chunk.
  - Added a separate metrics-dashboard summary-table display row cap so large
    station, event, path, or model-summary tables are not fully serialized to
    the browser by default.
  - Added a separate metrics-dashboard download row cap so filtered row-level
    CSV downloads do not serialize every loaded distribution row by default.
  - Made config-backed dashboard dataset writes partitioned by default so
    standard workflow helpers use the large-run-safe dashboard layout unless a
    caller explicitly requests a single output table.

- **Dashboard path and value contracts** *(Hardened)*

  - Added clear Streamlit dashboard query aliases
    ``metrics_dataset_dir``, ``dashboard_summary_table_dir``, and
    ``qc_trace_summary`` while preserving legacy dashboard links.
  - Added clear Python launch keywords ``metrics_dataset_dir`` and
    ``dashboard_summary_table_dir`` for ``launch_metrics_dashboard`` while
    preserving ``metrics_root`` and ``summary_root``.
  - Added ``qc_trace_summary_table`` to notebook dashboard launch status
    frames while preserving the ``trace_summary`` runtime alias for existing
    code.
  - Added primary-name properties to dashboard path contract objects so
    ``metrics_dataset_dir``, ``dashboard_summary_table_dir``, and
    ``qc_trace_summary_table`` are available alongside legacy field names.
  - Re-exported dashboard path/readiness contract classes from the stable
    ``spatial_vtk.visualize.dashboard`` and ``spatial_vtk.visualize`` package
    surfaces.
  - Added ``resolved_path`` to dashboard output status, readiness summary, and
    written-output frames while preserving ``path`` for existing notebooks.
  - Added dashboard value-family readiness metadata so status tables show
    whether row-level and summary datasets contain residuals, GOF scores,
    observed values, synthetic values, or only generic metric values.

- **Dashboard readiness and startup checks** *(Hardened)*

  - Promoted dashboard tab empty-state, missing-column, chart-readiness, and
    value-selector messages into public package helpers so notebooks and CLI
    status output can share the same contracts as Streamlit tabs.
  - Made ``svtk dashboard status`` include dashboard value-family and
    map-readiness messages in its bounded human-readable status table, matching
    the notebook and Streamlit Data Status displays.
  - Added tab-level dashboard readiness fields so station/event summaries that
    have finite values but lack map coordinates are reported as data-ready but
    tab-blocked.
  - Made metrics-dashboard startup warnings and optional-tab messages honor
    ``tab_ready`` / ``tab_message`` so map-blocked station or event tabs are
    not treated as fully ready.
  - Made ``svtk dashboard status`` show the clearer ``resolved_path`` column in
    human-readable output while preserving ``path`` in machine-readable status
    frames.
  - Made metrics-dashboard readiness warnings include specific tab blocker
    messages, such as missing map-coordinate columns, while bounding long
    warning banners and pointing users to the Data Status tab for the full
    table.
  - Hardened Streamlit dashboard launch checks so occupied ports are detected
    before launch and delayed startup failures are reported before the CLI
    prints a running-dashboard URL.
  - Made partial metrics-dashboard path overrides without a config name the
    supplied flag and the missing companion dashboard artifact instead of
    reporting that both dashboard paths were omitted.

- **Lazy dashboard and workflow imports** *(Hardened)*

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

- **Dashboard CLI and API reference wording** *(Changed)*

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
  - Made QC dashboard startup warnings render even when the bounded readiness
    check itself returns an empty or malformed status frame, so failed
    preflight checks do not silently leave a blank dashboard page.

- **Workflow status-frame contracts** *(Hardened)*

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

- **Large-table read and merge paths** *(Hardened)*

  - Made scoped metric-QC parquet reads fail with actionable PyArrow metadata
    or streaming errors instead of falling back to full-table materialization
    during metric manifest planning.
  - Made metric batch parquet merges fail with actionable PyArrow dependency
    errors instead of falling back to full-table pandas reads when inspecting
    schemas or bounded previews.
  - Changed metric batch merges to stream each CSV or Parquet batch in row
    chunks instead of full-reading one batch file at a time before writing the
    merged metric-row table.
  - Changed metric task summary estimates to stream projected task columns
    from path-backed task tables instead of full-reading serialized waveform
    path and execution-parameter columns that are not needed for planning
    counts.
  - Made shared parquet preview helpers stream bounded rows with PyArrow and
    report actionable metadata/dependency errors instead of full-reading large
    tables before taking ``head()``.
  - Reused shared parquet metadata helpers across metric figures, spatial
    figures, dashboard readiness checks, QC lookup loading, and GeoJSON
    summaries so schema/row-count probes do not fall back to full-table reads.
  - Reused the same shared parquet schema helper inside dashboard metric
    dataset exports so filtered dashboard readers and writers use one
    large-table-safe schema path.
  - Added a shared CSV/Parquet ``table_row_count`` helper and used it when
    reusing existing spatial derived-output tables, avoiding full-table reads
    just to report skip row counts.
  - Reused the shared row-count helper in dashboard readiness checks so CSV
    dashboard datasets with quoted newlines report correct row counts without
    materializing the table.

- **Bounded workflow previews and outputs** *(Hardened)*

  - Scoped path-backed long metric-row reads during downstream metric output
    preparation so enrichment, path summaries, and dashboard outputs do not
    carry unused payload columns from large merged metric files.
  - Changed the Step 1 ingest metadata summary result to count prepared
    station, event, and event-station rows through lightweight table counters
    instead of loading full metadata tables.
  - Made Step 3 metric workflow outputs skip eager ``metric_task_estimate``
    loading by default and simplified tutorial calls to use
    ``load_standard_metric_workflow_outputs(cfg=cfg)``.
  - Clarified Python workflow guidance so notebook preview cells use bounded
    result-object display helpers and reserve full ``load_table()`` calls for
    explicit analysis or package helpers.
  - Clarified output-group API guidance so custom helpers use bounded
    ``preview_table()`` / ``preview_tables()`` calls by default and reserve
    full ``load_table()`` / ``load_tables()`` calls for explicit full-table
    reads.
  - Scoped pattern-similarity derived-output metric reads to the required
    columns for path-backed CSV and Parquet inputs so optional Step 4 derived
    products do not materialize wide metric tables unnecessarily.
  - Scoped Step 5 GeoJSON plotting input metric reads to spatial event-row
    columns so region and corridor figure helpers do not materialize unused
    ``metrics_long`` columns.
  - Made configured metric-output and dashboard-output helpers write
    partitioned dashboard metric datasets by default, and changed
    ``svtk metrics outputs`` to default to that large-run-safe layout while
    keeping ``--no-dashboard-partitioned`` as an explicit opt-out.

- **Large-run notebook result objects** *(Hardened)*

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

- **Large-run workflow checks and logging** *(Hardened)*

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
  - Added release guardrails so local agent notes and private planning files
    stay ignored.
  - Added release guardrails so machine-specific instructions are called out
    before public publishing.

- **Tutorial install and runtime checks** *(Fixed)*

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
    the result-owned ``write_figure_suite(...)`` method rather than
    lower-level spatial figure-context helpers.

- **Dashboard and spatial API guidance** *(Documented)*

  - Clarified dashboard API guidance so notebooks display user-facing artifact
    labels instead of internal dashboard output-registry names.
  - Updated Spatial API examples so large-run plotting starts from the
    package-owned spatial workflow result, with context builders described as
    advanced helpers.
  - Promoted Step 5 GeoJSON and Step 6 additional-plotting input/status
    loaders to the top-level ``spatial_vtk.spatial`` import surface so
    notebooks use one workflow namespace for Steps 4-6.
  - Updated Metrics API examples so plotting starts from package-owned figure
    wrappers, with row-selection helpers described as advanced script APIs.
  - Updated Visualization API examples so notebook-facing waveform and
    dashboard wrappers appear before lower-level script helpers.
  - Documented notebook-facing and script-facing waveform-comparison and
    region-boxplot helpers.

- **Generated CLI example guidance** *(Documented)*

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
  - Clarified the large-run dashboard notebook review step so blank or sparse
    dashboard tabs point readers to package-owned readiness/Data Status
    messages and dashboard table contracts instead of manual path inspection.

- **Notebook figure provenance displays** *(Cleaned)*

  - Added explicit purpose/output notes to the remaining large-run figure and
    provenance cells so notebook section headers keep the same task-focused
    contract as the code cells they introduce.
  - Aligned standard and large-run figure provenance review cells to call
    ``settings.sidecars.status_frame()`` directly so the displayed table is
    clearly the per-figure sidecar inventory rather than a generic render
    settings table.
  - Added explicit existence fields to large-run Step 5 region figure status
    tables so notebooks show whether GeoJSON, corridor, boxplot, and sidecar
    artifacts were actually written without requiring manual path checks.
  - Added ``figure_exists`` fields to standard Step 3 metric diagnostics,
    Step 4 spatial maps/diagnostics, Step 5 GeoJSON/corridor figures, and
    Step 6 additional plotting status tables.
  - Added ``existing_figure_count`` fields to large-run metric and spatial
    figure-suite status tables so notebooks distinguish planned figure paths
    from artifacts that are already present on disk.
  - Added ``table_exists`` and ``figure_exists`` fields to Step 1 context and
    Step 2 QC figure-suite status tables so notebooks show missing inputs and
    written artifacts without requiring manual path checks.
  - Added source-input readiness fields to
    ``DashboardOutputReadiness.status_frame()`` so dashboard rebuild decisions
    show ``metrics_long`` readiness, messages, and suggested actions directly.
  - Changed compact dashboard readiness summaries to use user-facing input
    labels such as ``metrics_long source table`` as displayed items instead of
    internal path keys such as ``metrics_long_path``.
  - Removed the legacy ``trace_summary_table`` alias column from notebook
    dashboard launch status frames; launch helpers still accept the legacy
    ``trace_summary`` keyword for existing Python callers.
  - Aligned dashboard preparation display tests and API docs with the package
    helper contract that includes a preparation-decision frame alongside
    readiness, status, written-output, and summary-contract frames.

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
  - Added ``FigureSidecarResult.status_frame()`` so direct sidecar writes return
    the same notebook-friendly path and exactness summary as directory-level
    sidecar audits.
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

- **Release and workflow documentation** *(Added)*

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
