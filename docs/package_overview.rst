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
  for config-backed waveform preprocessing and record coverage
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
- ``run_spatial_derived_outputs_workflow_from_config`` for optional REDCAP,
  block holdout, and pattern-similarity tables
- ``run_geojson_region_summary_workflow_from_config`` and
  ``run_boundary_corridor_workflow_from_config`` for GeoJSON and corridor
  tables
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
- ``visualize.dashboard`` for dashboard tables and Streamlit apps

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
