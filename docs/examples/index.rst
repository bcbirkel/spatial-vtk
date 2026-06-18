Examples and Tutorials
======================

The standard tutorial notebooks run end to end against the example data that
ships with the repository. The large-run notebooks use the same workflow shape
but keep heavy work in chunked helpers or SLURM-driven cells.

Notebook cells use importable ``spatial_vtk`` package functions rather than
shelling out to ``svtk``. The command-line workflow is documented separately for
terminal-first use.

Standard Tutorial Notebooks
---------------------------

Run these notebooks in order from a source checkout:

1. :download:`Step 1: ingest and prepare data <step_01_ingest_and_prepare_data.ipynb>`
2. :download:`Step 2: quality control <step_02_quality_control.ipynb>`
3. :download:`Step 3: calculate metrics <step_03_calculate_metrics.ipynb>`
4. :download:`Step 4: spatial statistics <step_04_spatial_statistics.ipynb>`
5. :download:`Step 5: maps and figures <step_05_maps_and_figures.ipynb>`
6. :download:`Step 6: additional plotting options <step_06_additional_plotting_options.ipynb>`
7. :download:`Step 7: dashboards <step_07_dashboards.ipynb>`

To verify the full standard tutorial from a clean output directory, run:

.. code-block:: bash

   python -m pip install -e ".[notebooks,waveforms]"
   python tools/execute_tutorial_notebooks.py --clean

The command executes the seven notebooks against the committed example data,
writes ``outputs/tutorials/notebook_execution_report.json``, and fails if a
notebook raises an error or emits warning-like cell output. It also checks the
notebook source contract, committed five-event metadata, snapshot tables, and
observed/synthetic NPZ waveform subset before cleaning ``outputs/tutorials``.
The source contract catches saved execution state, private absolute paths,
shell/CLI workflow cells, and raw output-path/table reads so public tutorials
stay package-first and source-checkout safe.

To verify the standard and large-run tutorial drivers together from a fresh
source checkout, run:

.. code-block:: bash

   python -m pip install -e ".[notebooks,waveforms]"
   python tools/execute_tutorial_notebooks.py --clean --include-large-run

The large-run notebooks still use the committed example data during this
check, but their cells are structured for larger datasets: expensive work is
chunked or submitted through package helpers, and notebook previews stay
bounded. The same source-contract preflight runs before execution.

Large-Run Driver Notebooks
--------------------------

These notebooks are lightweight drivers for larger datasets. They print or
submit package-backed batch tasks for compute-heavy work rather than loading
full inventories into notebook memory.

1. :download:`Large Step 1: ingest and prepare data <large_run/step_01_large_run_ingest_and_prepare_data.ipynb>`
2. :download:`Large Step 2: quality control <large_run/step_02_large_run_quality_control.ipynb>`
3. :download:`Large Step 3: calculate metrics <large_run/step_03_large_run_calculate_metrics.ipynb>`
4. :download:`Large Step 4: spatial statistics <large_run/step_04_large_run_spatial_statistics.ipynb>`
5. :download:`Large Step 5: GeoJSON corridors <large_run/step_05_large_run_geojson_corridors.ipynb>`
6. :download:`Large Step 6: additional plotting <large_run/step_06_large_run_additional_plotting.ipynb>`
7. :download:`Large Step 7: dashboards <large_run/step_07_large_run_dashboards.ipynb>`

Set ``SVTK_FIGURE_SIDECARS=1`` while rendering figures to write CSV/JSON
row-provenance sidecars. Main sidecars contain the exact rows passed to the
plotting function; aggregated station figures also write ``*.source.csv`` files
with the pre-aggregation event-station metric rows. If a station figure samples
aggregated plot rows, the source sidecar is filtered to the raw rows behind
those plotted station groups. Use
``SVTK_FIGURE_SIDECAR_ROWS=all`` to write all rows, or a positive integer to
write a deterministic sample. The JSON sidecar records ``sidecar_row_policy``,
``plot_sidecar_exact``, ``source_sidecar_exact``, and station-summary
``svtk_aggregation_collapsed_columns``/``svtk_aggregation_collapsed_unique_counts``
so sampled audits are distinguishable from complete row exports and users can
see which dimensions were collapsed into station-level values.

Command-Line Workflow
---------------------

.. toctree::
   :maxdepth: 1

   cli_workflow
