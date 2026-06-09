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

Main areas:

- ``io.metadata`` and ``io.inventory`` for prepared station, event, and waveform tables
- ``io.waveforms``, ``io.preprocessing``, and ``io.synthetic_formats`` for waveform preprocessing and synthetic file helpers
- ``io.artifacts`` and ``io.plans`` for reproducible output paths and metric plans

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

Main areas:

- ``qc.build`` for QC inventory and filtering logic
- ``qc.review`` for manual-review tables
- ``qc.summary`` for retention summaries and reject-rule helpers

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

Main areas:

- ``metrics.calculate`` for metric math and table preparation
- ``metrics.workflow`` for file-based task planning, batching, merging, and SLURM scripts
- ``metrics.plot`` for metric-specific diagnostic figures

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
