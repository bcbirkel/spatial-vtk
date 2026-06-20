Package Overview
================

Spatial-VTK is organized around the order you will usually move through a
project: prepare your inputs, set project defaults, review data quality,
calculate metrics, analyze spatial patterns, and make figures or dashboards.

This page is a map of the package. Use it to decide where to start, then go to
the examples or API reference when you want runnable code or exact function
signatures.

Workflow At A Glance
--------------------

.. list-table::
   :header-rows: 1
   :widths: 12 18 45

   * - Step
     - Module
     - What You Use It For
   * - 1
     - ``io``
     - Read waveform inputs, prepare metadata, and build inventories.
   * - 2
     - ``config``
     - Set paths, bounds, metric choices, synthetic limits, and run scenarios.
   * - 3
     - ``qc``
     - Build QC tables, summarize retained records, and prepare manual-review queues.
   * - 4
     - ``metrics``
     - Calculate observed/synthetic metric values, residuals, and GOF scores.
   * - 5
     - ``spatial``
     - Find station, event, path, geology, polygon, and corridor patterns.
   * - 6
     - ``visualize``
     - Make context figures, QC figures, waveform figures, maps, and dashboards.
   * - 7
     - ``cli``
     - Run the same workflows from the terminal with ``svtk``.

``io``
------

Use ``io`` when you are turning your own files into tables Spatial-VTK can use.

Common tasks:

- prepare station and event metadata with consistent column names
- build observed/synthetic waveform inventories
- preprocess waveform files once with configured filters or resampling
- read catalog tables and synthetic model aliases
- write artifact manifests for generated outputs
- reshape metric tables for downstream workflows

Start with public helpers from ``spatial_vtk.io``:

- ``prepare_station_metadata``, ``prepare_event_metadata``, and
  ``prepare_event_station_table`` for prepared station/event tables
- ``preprocess_waveforms_from_config`` and ``build_record_coverage_from_config``
  for config-backed waveform preprocessing and record coverage; their result
  objects provide ``summary_message()`` and ``summary_frame()`` so notebooks do
  not need to unpack path dictionaries just to report progress
- ``output_group`` and ``output_readiness`` for notebook-friendly output status
  checks without hand-written path cells

``config``
----------

Use ``config`` when you want one place to define the project settings you reuse.

Common tasks:

- resolve project paths and output folders
- define named map bounds such as ``study_area``
- choose metric groups, transforms, passbands, components, and models
- set synthetic maximum frequency limits
- apply optional ``run_scenarios`` for repeatable variations

Start with :doc:`configuration` if you are setting up a project config file.

``qc``
------

Use ``qc`` when you need to decide which records are reliable enough to keep.

Common tasks:

- build trace and record inventories
- apply reject rules and passband-specific checks
- summarize retained and rejected records
- export manual-review queues for the QC picker

Start with public helpers from ``spatial_vtk.qc``:

- ``load_standard_qc_inputs`` for standard Step 2 prepared metadata, QC
  output-group loading, named skipped-step results, bounded preview display,
  standard QC figure rendering, and bounded waveform comparison rendering
- ``load_standard_qc_workflow_outputs`` for large-run Step 2 QC output status
  without eager prepared-table reads, plus compact QC summary previews and
  figure rendering
- ``run_qc_inventory_from_config`` for full waveform and metric QC inventories
- ``write_qc_inventory_overlap_from_config`` for comparison-ready overlap rows
- ``run_qc_summary_workflow_from_config`` for compact retention, availability,
  post-QC record, and drop-cause tables
- ``filter_trace_summary`` and ``queue_rows_from_filtered_trace_df`` for
  manual-review queues

``metrics``
-----------

Use ``metrics`` when you are ready to calculate waveform metrics and compare
observed and synthetic records.

Common tasks:

- calculate amplitude, duration, spectral, intensity, delay, and correlation metrics
- compute residuals, log residuals, Anderson GOF scores, and Olsen-Mayhew GOF scores
- run metric calculations locally, in batches, or with SLURM
- enrich metric tables with station, event, path, and geologic metadata
- prepare standard outputs for spatial analysis, plotting, and dashboards

Start with public helpers from ``spatial_vtk.metrics``:

- ``build_metric_waveform_inventories_from_config`` and
  ``plan_metric_tasks_from_config`` for large-run planning
- ``summarize_metric_snapshot_tasks_from_config`` for tutorial and review
  task previews from already-calculated metric snapshots
- ``load_standard_metric_workflow_outputs`` for Step 3 output status, bounded
  metric previews, task-estimate loading, and standard diagnostic figures
- ``metric_manifest_batch_status`` and ``metric_slurm_submission_readiness`` for
  resumable large-run metric arrays
- ``write_metrics_slurm_script_from_config`` and
  ``merge_metric_batches_from_config`` for batch execution handoffs
- ``write_metric_outputs_from_config`` for downstream metric, dashboard, and
  spatial-statistics tables
- ``spatial_vtk.metrics.plot`` for metric-specific diagnostic figures

``spatial``
-----------

Use ``spatial`` when you want to understand where model performance changes
across stations, events, paths, regions, or geologic settings.

Calculation tools:

- station bias and event-centered residual fields
- Moran's I, permutation Moran tests, and distance-bin correlations
- spatial holdout tests and residual-feature clustering
- REDCAP spatial clustering
- PCA spatial modes
- bootstrap contrasts and geology-class joins
- observed/synthetic spatial-pattern comparisons

Path, polygon, and corridor tools:

- source-station geometry and distance/azimuth path summaries
- GeoJSON station, event, and path classifications
- polygon crossing, begins-in-polygon, and ends-in-polygon selections
- boundary corridors built from keyword parameters
- corridor path classification by membership, side, and path length

Plot and map tools:

- correlograms, semivariograms, holdout diagnostics, and cluster summaries
- PCA variance/loadings plots and PCA mode maps
- station-bias maps, score maps, residual grids, and event residual maps
- corridor and polygon-path maps

Start with public helpers from ``spatial_vtk.spatial``:

- ``run_spatial_statistics_workflow_from_config`` for standard spatial
  statistics tables
- ``load_standard_spatial_workflow_output_status`` for Step 4 large-run output
  status, bounded table previews, and quick summary figures without loading
  large tables
- ``load_standard_spatial_workflow_outputs`` for standard Step 4 output-table
  loading, per-metric product summaries, and standard Step 4 figure suites
- ``run_spatial_derived_outputs_workflow_from_config`` for optional REDCAP,
  block holdout, and pattern-similarity tables
- ``geojson_region_summary_readiness_from_config`` and
  ``boundary_corridor_readiness_from_config`` for Step 5 readiness checks that
  resolve configured region and upstream table paths
- ``run_geojson_region_summary_workflow_from_config`` and
  ``run_boundary_corridor_workflow_from_config`` for GeoJSON and corridor
  tables
- ``load_standard_geojson_workflow_output_status`` and
  ``load_standard_geojson_plotting_inputs`` for Step 5 output status and
  standard notebook inputs without notebook-local GeoJSON path or output-table
  plumbing; the standard plotting input result writes region and corridor
  figure suites from configured inputs, the lightweight status result writes
  large-run region/corridor figures, and status tables include
  ``resolved_path`` with ``path`` retained as a compatibility alias
- ``load_standard_additional_plotting_output_status`` and
  ``load_standard_additional_plotting_inputs`` for Step 6 output status,
  metric-source previews, bounded waveform comparisons, region boxplots,
  standard plotting inputs, and standard Step 6 figure suite writing
- ``add_geojson_metadata_to_metrics``, ``build_boundary_corridors``, and
  ``build_pattern_similarity_station_anomalies`` for focused spatial
  calculations
- ``spatial_vtk.spatial.plot`` and ``spatial_vtk.spatial.map`` for spatial
  figures and maps

``visualize``
-------------

Use ``visualize`` when you want figures or interactive outputs rather than new
tables.

Common tasks:

- make basic station/event context maps and coverage figures
- make QC and retention figures
- make waveform record sections and trace-comparison figures
- prepare dashboard datasets from long metric tables
- launch Streamlit/Folium dashboards for metrics and QC review

Main areas:

- ``visualize.context`` for project overview figures
- ``visualize.qc`` for QC and retention figures
- ``visualize.waveforms`` for record sections and waveform comparisons
- ``visualize.dashboard`` for dashboard tables and Streamlit apps, including
  result-owned ``run_if_needed(...)`` helpers for large-run dashboard dataset
  preparation

``cli``
-------

Use ``cli`` when you want to run package workflows from a terminal. The public
command is ``svtk``.

Common command groups:

- ``svtk config`` for config discovery and inspection
- ``svtk io`` for metadata and inventory preparation
- ``svtk qc`` for QC review-queue exports
- ``svtk metrics`` for metric task planning, execution, merging, and outputs
- ``svtk plot``, ``svtk map``, and ``svtk visualize`` for file-backed figures
- ``svtk dashboard`` for Streamlit dashboard launchers

See :doc:`reference/cli_api` for command examples.

Where To Go Next
----------------

- If you are checking what files you need, go to :doc:`data_formats`.
- If you are setting up paths and defaults, go to :doc:`configuration`.
- If you want a guided workflow, go to :doc:`examples/index`.
- If you need function signatures, go to :doc:`reference/python_api`.
- If you need terminal commands, go to :doc:`reference/cli_api`.
