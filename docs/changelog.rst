Changelog
=========

2026-06-19
----------

- **Added**

  - **Public workflow helpers**

    - Added a standard Step 1 ingest output loader for combined ingest and
      preprocessing output status plus bounded station, event, and preprocessing
      manifest previews.
    - Added standard notebook input/output loaders for QC, spatial summaries,
      GeoJSON plotting, and Step 5 readiness checks so notebooks no longer
      duplicate config path plumbing.
    - Added a standard Step 3 metric output loader for task-estimate,
      task-preview, and ``metrics_long`` notebook previews.
    - Added output-registry preview helpers, path-backed table preview helpers,
      workflow-step status helpers, and bounded pattern-similarity preview
      helpers for notebook display cells.
    - Added public Metrics API reference tables for inventory, manifest, Slurm,
      batch, merge, and output helpers exposed through stable package entry
      points.

  - **Notebook-owned display cleanup**

    - Rewired standard Step 1, Step 2, Step 4, Step 5, and Step 6 notebooks to
      call package helpers for table previews, readiness messages, and configured
      output loading.
    - Kept reusable skip/rebuild decisions, ``reused`` flags, and path string
      conversion in package code rather than in notebook-local dictionaries.

- **Changed and Rewired**

  - **Public API documentation**

    - Updated Metrics, QC, Spatial, Visualization, I/O, and Configuration API
      pages to document stable package entry points instead of lower-level
      implementation modules.
    - Updated workflow examples to prefer ``output_group()`` and configured
      output-registry helpers over raw ``resolve_output_path()`` snippets for
      normal notebook workflows.

  - **CLI and workflow docs**

    - Updated CLI workflow examples so routine GeoJSON, metric plotting, mapping,
      visualization, and dashboard commands resolve standard inputs from the
      active config.
    - Normalized generated CLI help text for config, input, output, manifest,
      dashboard, inventory, and waveform path arguments so usage strings show
      ``PATH`` or ``DIR`` where appropriate.

  - **Large-run resilience**

    - Added warnings when large-run QC or metric checkpoint reuse falls back to
      slower paths because an existing checkpoint cannot be read.
    - Updated readiness-aware notebook cells so they print why a package workflow
      step is running before local execution or Slurm script generation.

- **Fixed and Hardened**

  - **Fresh checkout and docs checks**

    - Added regression coverage for public API import examples, committed
      tutorial data, CLI workflow examples, and changelog formatting.
    - Clarified tutorial runtime checks so missing importable modules are
      reported directly before the install command.
    - Aligned README, installation docs, source-checkout validation, and CI
      tutorial gates around the same notebook and large-run preflight commands.

  - **Config and plotting behavior**

    - Made ``svtk plot metrics period-spectra`` use the configured
      ``metrics_long`` table by default.
    - Taught ``plot_period_spectra()`` to accept standard metric-table
      residual/value columns through ``value_col``.
    - Clarified ``output_group_namespace()`` as a legacy path-only compatibility
      wrapper.

- **Documentation and Examples**

  - **Workflow guidance**

    - Clarified Python workflow and output-registry guidance around public helper
      signatures, return contracts, and bounded previews.
    - Documented notebook-facing and script-facing waveform-comparison and
      region-boxplot helpers.
    - Updated generated CLI reference examples to use the committed example
      config and tutorial run scenario.

  - **Notebook hygiene**

    - Removed one-off preview variables and repeated path construction from
      standard notebook cells where package helpers now own the task.
    - Made large-run README guidance explicit about public plotting, mapping, and
      visualization entry points.

2026-06-18
----------

- **Added**

  - **Package-owned figure suites**

    - Added standard and large-run figure-suite helpers for metric diagnostics,
      spatial diagnostics, GeoJSON regions/corridors, waveform comparison,
      context figures, QC figures, region boxplots, and dashboard preparation.
    - Added focused station-map, spatial-product, PCA-product, corridor-record,
      waveform-order, and pattern-similarity preview helpers.

  - **Figure provenance and sidecars**

    - Expanded figure sidecar metadata and status frames with source-row roles,
      plot/source dimension counts, aggregation contracts, exactness flags,
      station/event counts, and PSA/multi-panel counts.
    - Added sampled station-map sidecar regression coverage so plotted station
      groups and source rows stay aligned.

  - **Release and API maintenance**

    - Added a public ``RELEASE_CHECKLIST.md`` for validation, docs, build, wheel
      inspection, and publish gates.
    - Added public helpers for metric row selection, event/station matching,
      GeoJSON metric frames, event labels, spatial metric products, and first
      non-empty table values.

- **Changed and Rewired**

  - **Notebook simplification**

    - Rewired standard and large-run plotting notebooks so cells call package
      helpers instead of importing individual plotting functions, constructing
      figure paths, or repeating sidecar/showfig/savefig plumbing.
    - Rewired standard Step 3, Step 4, Step 5, Step 6, and Step 7 notebooks to
      use package-owned context setup, table previews, dashboard displays, and
      diagnostic figure writers.

  - **Large-run metric and spatial plotting**

    - Moved metric target iteration, PSA period-sheet branching, station
      aggregation, robust-axis selection, model/component/passband defaults, and
      raw source-row sidecars into package code.
    - Added spectral contract status checks for PSA/FAS rows so notebooks can
      flag legacy passband-scoped spectral metrics before rendering figures.

- **Fixed and Hardened**

  - **Tutorial/runtime checks**

    - Strengthened runtime checks to verify the source checkout and required
      scientific, mapping, dashboard, waveform, Jupyter, and IPython modules
      before notebook outputs are cleaned or executed.
    - Tightened notebook preflight to reject notebook-local function and class
      definitions.

  - **Dashboard and plotting stability**

    - Improved metrics-dashboard Data Status messages for skipped optional
      summary tables and filtered-empty views.
    - Routed Step 4 spatial figure items by explicit owner tags instead of
      dataframe column-subset inference.
    - Improved generated API-reference fallback text for common parameter names.

- **Documentation and Examples**

  - **Public entry points**

    - Updated configuration and workflow docs to use stable public imports from
      ``spatial_vtk.config`` and other package surfaces.
    - Documented the broadband spectral-metric contract: PSA and FAS are planned
      as blank-passband spectral tasks with oscillator periods in ``period_s``.

- **Removed**

  - **Development-only reload hooks**

    - Removed ``reload_metric_plot_modules()`` and the large-run notebook
      ``globals().update(...)`` reload pattern.

2026-06-17
----------

- **Added**

  - **Large-run workflow drivers**

    - Added config-backed QC, metrics, spatial, GeoJSON, dashboard, preprocessing,
      record-coverage, waveform-inventory, Slurm, batch-merge, and output-writing
      helpers for large-run notebooks.
    - Added ``run_notebook_step_if_needed()`` and structured readiness/status
      frames so notebooks can skip current outputs and explain stale or missing
      prerequisites.

  - **Output groups and previews**

    - Added ``OutputGroup`` helpers for grouped table loading, fallback previews,
      path-backed preprocessing metadata, first-existing outputs, figure paths,
      readiness checks, and status frames.
    - Added notebook settings helpers for run scenarios, metric batch counts,
      preprocessing error policy, figure controls, sidecar settings, PCA mode,
      dashboard launch commands, and optional score trends.

  - **Dashboard and figure diagnostics**

    - Added metrics/QC dashboard launch helpers, dashboard dataset writers,
      dashboard readiness summaries, bounded dashboard startup checks, and
      current-filter diagnostics.
    - Added metric and spatial figure contexts with status frames, dimension
      summaries, sidecar status, PSA/FAS contract checks, station aggregation
      metadata, and source-row provenance.

- **Changed and Rewired**

  - **Config-backed CLI and notebooks**

    - Updated standard and large-run notebooks to load tables through output
      groups and package helpers instead of repeated ``load_output_table`` or
      raw path checks.
    - Made routine ``svtk io``, ``svtk metrics``, ``svtk plot``, ``svtk map``,
      ``svtk visualize``, ``svtk spatial``, ``svtk qc``, and dashboard commands
      use configured defaults or clearer artifact-named aliases.

  - **Metric and spatial execution**

    - Added incomplete-only metric Slurm arrays, metric batch-status reporting,
      output-directory-aware batch merging, and config-backed metric task
      planning/running/merging.
    - Preserved PSA oscillator periods, path geometry, and public value columns
      in compact spatial outputs for downstream Step 4 figures.

- **Fixed and Hardened**

  - **Large-run performance and robustness**

    - Reduced dashboard summary memory use and made dashboard dataset rewrites
      replace stale artifacts safely.
    - Hardened dashboard startup for partial or large outputs, including missing
      map-coordinate and value-column diagnostics.
    - Hardened station aggregation, map coordinates, figure sidecars, PSA sheets,
      older pandas/Matplotlib compatibility, and directory-style metric batch
      merge outputs.

  - **User-facing clarity**

    - Clarified public API start points, dashboard path names, metric/spatial/QC
      CLI aliases, large-run plotting defaults, and helper return-value guidance.
    - Updated tests to guard outlier handling, sidecar provenance, config-backed
      CLI defaults, notebook imports, and tutorial freshness checks.

- **Documentation and Examples**

  - **Notebook and workflow docs**

    - Updated tutorial notebooks and Python workflow docs to use public package
      helpers, grouped output loading, and direct output-group attributes.
    - Documented the committed NPZ tutorial waveform subset, source-checkout
      install extras, package-level plotting/map entry points, and dashboard
      output contracts.

2026-06-16
----------

- **Added**

  - **CLI and plotting controls**

    - Added first-class plotting, mapping, waveform, table, sidecar, mode,
      component, metric, passband, value-column, fit, title, and comparison flags
      so routine figure configuration no longer depends on generic ``--kwargs``.
    - Registered plotting and mapping commands through stable public import
      surfaces and expanded config-backed command defaults.

  - **Tutorial execution and CI**

    - Added ``tools/execute_tutorial_notebooks.py`` for clean source-checkout
      notebook execution and warning-like output detection.
    - Added tutorial data preflight, runtime dependency preflight, CI notebook
      execution coverage, and regression checks against private/local notebook
      paths.

  - **Dashboard and sidecar contracts**

    - Added dashboard output helpers, readiness diagnostics, artifact roles,
      dashboard summary contribution-count tests, map-coordinate requirements,
      and optional row-provenance sidecars for saved figures.

- **Changed and Rewired**

  - **Notebook path ownership**

    - Replaced notebook-local output-path dictionaries and repeated
      ``resolve_output_path`` calls with output namespaces, output groups, and
      dashboard output helpers.
    - Updated large-run notebooks to keep configured paths attached to
      package-owned output groups.

  - **Public workflow docs**

    - Updated generated CLI reference, shell workflow examples, Python workflow
      docs, and configuration examples to prefer first-class flags and stable
      package entry points.

- **Fixed and Hardened**

  - **Dashboard and figure behavior**

    - Hardened metrics and QC dashboards against missing, empty, schema-invalid,
      filtered-empty, and value-less optional tables.
    - Hardened station-map aggregation, station coordinate handling, sidecar
      metadata, warning scans, notebook output labels, and output-readiness
      messages.

  - **Fresh checkout reliability**

    - Made tutorial basemap fetching opt-in, kept Jupyter runtime files under
      ignored tutorial outputs, and added missing notebook runtime dependencies
      to source-install extras and the conda environment.

2026-06-09
----------

- **Released**

  - **0.1.3**

    - Published a PyPI README workflow-image fix after external Sigstore/Rekor
      ``502`` errors blocked the ``0.1.2`` publish.

  - **0.1.2**

    - Refreshed PyPI project metadata so the README workflow image uses an
      absolute GitHub-hosted URL that renders on PyPI.

  - **0.1.1**

    - Refreshed PyPI project metadata so the package page points readers to the
      public GitHub Pages documentation.

2026-06-08
----------

- **Added**

  - **QC-to-metrics valid-window contract**

    - Preserved waveform source labels in PhaseNet arrival-pick catalogs.
    - Allowed waveform QC to anchor noise and signal windows to source-specific
      PhaseNet P picks when available, with envelope-onset fallback.
    - Added a plausibility gate so PhaseNet picks are used only when their signal
      windows have enough finite samples inside the metric-valid interval.

- **Fixed and Hardened**

  - **Waveform QC windows**

    - Reduced the automatic waveform-QC default noise-window minimum from
      10 seconds to 1 second.
    - Allowed QC noise windows to sample finite preprocessed data outside the
      metric-valid interval while keeping signal metrics constrained to the valid
      interval.

- **Other Notes**

  - **Metric trimming**

    - Waveform QC records processing-valid trace intervals, metric QC preserves
      those intervals, and metric execution trims scalar, pair, and spectral
      calculations to valid samples so filter/resampling edge transients do not
      control metric values.
    - The actual noise window remains at least as long as the requested period
      band.

2026-06-03
----------

- **Added**

  - **Public docs and examples**

    - Added data formats, configuration, package overview, installation, Python
      API, CLI API, CLI workflow, tutorial, and downloadable notebook guidance.
    - Added lightweight LA Basin metadata, public example manifests, GeoJSON
      regions, site metadata previews, basemap-backed output previews, and
      tutorial waveform/data snippets.

  - **Tutorial workflow helpers**

    - Added config-default metadata preparation, output table readers/writers,
      shared metric catalog/run scenarios, dashboard/table display helpers, and
      concise tutorial comments before main package calls.
    - Added Step 6 plotting examples for waveform maps, pattern similarity,
      scatterplot, boxplot, and heatmap outputs.

  - **CLI and spatial examples**

    - Expanded generated CLI reference pages and added a shell workflow tutorial
      covering config, preprocessing, QC, metrics, spatial figures, GeoJSON,
      corridors, flexible plots, and dashboards.
    - Added spatial-correlation-by-distance and geology-contrast examples.

- **Changed and Rewired**

  - **Installation and workflow docs**

    - Restored conda-environment-first installation guidance while keeping
      ``python -m pip install spatial-vtk`` as the main PyPI command.
    - Reworked package overview into a workflow-oriented guide.
    - Renamed tutorial-facing loaders/writers to ``load_output_table`` and
      ``write_metric_outputs``.

  - **Tutorial outputs**

    - Replaced notebook timing magics with shared timing registration.
    - Updated signed residual/log-ratio/mean-centered map figures to use a
      zero-centered divergent colorscale.
    - Regenerated Step 5 regions and corridor maps with public LA Basin examples.

- **Fixed and Hardened**

  - **Tutorial reliability**

    - Cleaned tutorial notebooks so they use the activated tutorial config,
      shared output registry, standard table writes/reads, and headless figure
      display support.
    - Simplified Step 4 so spatial-statistics functions resolve metric/value
      selection, event-centering, Moran, clustering, PCA, GeoJSON, and geology
      options from the active config.
    - Clarified spectral QC reason labels, regenerated QC previews, and cleaned
      internal trace-offset displays from waveform-map tutorials.

- **Other Notes**

  - **Workflow simplification**

    - Standard outputs are written where they are created and later notebooks
      read those products by key.
    - ``summarize_station_bias`` accepts raw and event-centered metric fields.
    - The dashboard tutorial is Step 7.

2026-06-02
----------

- **Added**

  - **Initial public migration**

    - Started the public Spatial-VTK package skeleton.
    - Added runtime configuration, output planning, metric catalog, YAML/JSON
      config loading, named bounds, output manifests, and config-backed metric
      plans.

  - **Core workflow modules**

    - Added metadata preparation, waveform inventories, context figures, QC
      helpers, metric batch calculations, arrival-pick normalization, long
      residual-table preparation, metadata enrichment, and deterministic example
      metric plots.
    - Added public metric, transform, passband, dashboard, plotting, mapping, and
      figure-selection labels/helpers.

  - **Spatial analysis and visualization**

    - Added spatial-statistics modules for metric preparation, station bias,
      Moran's I, distance-bin correlations, spatial holdout, clustering, REDCAP,
      PCA, bootstrap contrasts, permutation tests, pattern similarity, and
      observed/synthetic geometry.
    - Added plot/map wrappers for correlograms, semivariograms, directional
      correlation, holdout maps, clusters, PCA, station bias, REDCAP,
      pattern-similarity, path maps, event residual maps, GeoJSON polygons, and
      boundary corridors.

  - **Dashboards**

    - Added optional Streamlit dashboard support with Folium maps, Plotly charts,
      dashboard schema validation, filtered exports, manual-review exports, and
      selectable observed/synthetic/residual/GOF value columns.

- **Changed and Rewired**

  - **Metric naming**

    - Updated metric plots, spatial plots, maps, dashboard summaries, QC
      dashboard controls, waveform figures, record sections, and context figures
      to support the renamed metric scheme and selectable value columns.

Future Work
-----------

- Planned additions are tracked in :doc:`future_features`.

.. toctree::
 :maxdepth: 1
 :hidden:

 future_features
