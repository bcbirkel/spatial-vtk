Changelog
=========

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
