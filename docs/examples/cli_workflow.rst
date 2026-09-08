CLI Workflow Tutorial
=====================

Run these commands from the source checkout root in an environment installed
with ``.[notebooks,waveforms]``. Example data are in the source checkout, not
the wheel. The notebook runner executes every analysis cell and stores executed
copies and an output manifest under ``outputs/tutorial_execution``.

Complete terminal workflow
--------------------------

.. code-block:: bash

   unset SVTK_NO_BASEMAP
   export MPLBACKEND=Agg
   python -c 'from spatial_vtk.tutorials import verify_waveforms; verify_waveforms()'
   python tools/execute_tutorial_notebooks.py --steps 1 2 3 4 5 6 7

Final runs require the requested imagery and stop if it cannot be loaded.
For computation-only CI checks, use ``SVTK_NO_BASEMAP=1`` with
``--allow-missing-basemaps``; these outputs are not eligible for visual review.
Run Steps 1–3 before Steps 4–7. These produce the waveform, QC, and native ln
metric handoffs used by every subsequent notebook.

Metric CLI handoffs
-------------------

This representative CLI run calculates amplitude metrics for Z and 1–2 seconds;
the full notebook sequence above also calculates the other components and spectral metrics.
After Steps 1 and 2, create the metric inventories explicitly before planning.
These contain actual processed trace paths, components, and sample intervals.
Use the CLI plan's preprocessing override below because Step 1 already applied
the 1 Hz lowpass.

.. code-block:: bash

   export CONFIG=data/examples/configuration/example_spatial_vtk_config.yaml
   export TABLES=outputs/tutorials/tables
   python tools/tutorial_metric_inventories.py
   svtk metrics plan --config "$CONFIG" --run-scenario tutorial \
     --observed-inventory "$TABLES/observed_metric_inventory.csv" \
     --synthetic-inventory "$TABLES/synthetic_metric_inventory.csv" \
     --qc-table "$TABLES/qc_inventory.csv" \
     --metric-group amplitude --component Z --passband 1-2 \
     --waveforms-preprocessed --output "$TABLES/cli_metric_tasks.csv"

Execute the planned tasks and create standard outputs:

.. code-block:: bash

   svtk metrics run --tasks "$TABLES/cli_metric_tasks.csv" \
     --qc-table "$TABLES/qc_inventory.csv" --output "$TABLES/cli_metric_rows.parquet"
   svtk metrics outputs --metrics "$TABLES/cli_metric_rows.parquet" \
     --events "$TABLES/prepared_events.csv" --stations "$TABLES/prepared_stations.csv" \
     --output-dir outputs/tutorials/cli_tables --residual-column ln_residual \
     --score-column anderson_2004_gof --format parquet

Dashboard launch
----------------

Step 7 prints launch commands containing explicit dataset paths. Start the
servers explicitly in separate terminals; notebook execution does not launch
background servers or open a browser.

.. code-block:: bash

   svtk dashboard metrics --metrics-root outputs/tutorials/dashboards/metrics_dashboard \
     --summary-root outputs/tutorials/dashboards/dashboard_summaries --port 8501
   svtk dashboard qc --trace-summary "$TABLES/qc_trace_summary.csv" --port 8502

The spatial, corridor, and pattern-similarity operations are demonstrated by
the full Python cells in Steps 4–6. Run those with the notebook runner above;
they are not prerequisites silently supplied by a prior research environment.
