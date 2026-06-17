Changelog
=========

2026-06-16
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
   Added a shared large-run notebook helper for ``svtk`` CLI commands that
   prints the exact command, runs it through the Python CLI entrypoint when
   ``SVTK_RUN_LOCAL=1``, or writes/submits a config-backed SLURM wrapper
   otherwise. The large-run QC, metrics, spatial, and dashboard notebooks now
   use this helper for repeated command-driver cells.
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
   Replaced the Step 5 tutorial GeoJSON regions with real LA Basin, East LA,
   and Santa Monica Mountains polygons from the private geospatial inputs,
   regenerated the Step 5 notebook output, and updated corridor maps so they
   draw the selected event-station paths for each corridor definition. The
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
