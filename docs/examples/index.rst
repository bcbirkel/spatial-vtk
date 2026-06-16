Examples and Tutorials
======================

The standard tutorial notebooks run end to end against the example data that
ships with the repository. The large-run notebooks use the same workflow shape
but keep heavy work in chunked helpers or SLURM-driven cells.

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

Large-Run Driver Notebooks
--------------------------

These notebooks are lightweight drivers for larger datasets. They print or
submit batch commands for compute-heavy work rather than loading full
inventories into notebook memory.

1. :download:`Large Step 1: ingest and prepare data <large_run/step_01_large_run_ingest_and_prepare_data.ipynb>`
2. :download:`Large Step 2: quality control <large_run/step_02_large_run_quality_control.ipynb>`
3. :download:`Large Step 3: calculate metrics <large_run/step_03_large_run_calculate_metrics.ipynb>`
4. :download:`Large Step 4: spatial statistics <large_run/step_04_large_run_spatial_statistics.ipynb>`
5. :download:`Large Step 5: GeoJSON corridors <large_run/step_05_large_run_geojson_corridors.ipynb>`
6. :download:`Large Step 6: additional plotting <large_run/step_06_large_run_additional_plotting.ipynb>`
7. :download:`Large Step 7: dashboards <large_run/step_07_large_run_dashboards.ipynb>`

Command-Line Workflow
---------------------

.. toctree::
   :maxdepth: 1

   cli_workflow
