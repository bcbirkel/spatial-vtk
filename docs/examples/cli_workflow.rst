CLI Workflow Tutorial
=====================

This page mirrors the notebook tutorial sequence as terminal commands. It is useful when you want to run the workflow from a shell, rerun one step after changing an input file, or copy the command shape into a batch script.

The commands assume you are working from the root of a Spatial-VTK source checkout and using the example configuration file. The Python notebooks are still the best place to learn the workflow interactively; this page gives you the same path in command form.


Step 1: Ingest and Prepare Data
-------------------------------

Prepare station and event metadata, preprocess the waveform files once, and make the first context figures.

.. code-block:: bash

   export CONFIG=data/examples/configuration/example_spatial_vtk_config.yaml
   export SCENARIO=tutorial
   export TABLES=outputs/tutorials/tables
   export FIGURES=outputs/tutorials/figures
   export PREPROCESSED=outputs/tutorials/preprocessed_waveforms

   mkdir -p "$TABLES" "$FIGURES" "$PREPROCESSED"
   svtk config set "$CONFIG"

   svtk config show \
     --run-scenario "$SCENARIO" \
     --section paths

   svtk io prepare-stations \
     --input data/examples/example_five_event_subset/metadata/selected_stations.csv \
     --output "$TABLES/prepared_stations.csv"

   svtk io prepare-events \
     --input data/examples/example_five_event_subset/metadata/events.csv \
     --output "$TABLES/prepared_events.csv"

   svtk io preprocess-waveforms \
     --records data/examples/example_five_event_subset/metadata/selected_event_stations.csv \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --output-root "$PREPROCESSED" \
     --overwrite

   svtk visualize context station-event-context \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area

   svtk visualize context station-event-beachball \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area


Step 2: Quality Control
-----------------------

Build waveform and metric QC tables, export comparison-ready rows, make QC figures, and launch the QC dashboard.
The full ``qc_inventory.csv`` is retained for observed-only and synthetic-only
diagnostics. Comparison metrics should use ``qc_inventory_overlap.parquet``, a
streamed sidecar restricted to events with both observed and synthetic data.

.. code-block:: bash

   export EVENT_STATIONS="$PREPROCESSED/metadata/event_station_records_preprocessed.csv"
   export TRACE_QC="$TABLES/qc_trace_summary.csv"
   export QC_INVENTORY="$TABLES/qc_inventory.csv"
   export QC_INVENTORY_OVERLAP="$TABLES/qc_inventory_overlap.parquet"

   svtk qc build \
     --event-stations "$EVENT_STATIONS" \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --trace-output "$TRACE_QC" \
     --inventory-output "$QC_INVENTORY" \
     --overlap-inventory-output "$QC_INVENTORY_OVERLAP" \
     --verbose

   svtk qc summaries \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --overwrite \
     --verbose

   svtk qc manual-queue \
     --trace-summary "$TRACE_QC" \
     --output "$TABLES/manual_review_queue.csv" \
     --component R

   svtk visualize qc retention-summary \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO"

   svtk visualize qc event-station-retention \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO"

   svtk visualize waveforms observed-synthetic-record-section \
     --input "$EVENT_STATIONS" \
     --output "$FIGURES/event_trace_comparison.png" \
     --kwargs component=R gain=2.0 max_distance_km=50.0 xlim_s='[0, 60]'

   svtk dashboard qc \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --port 8502


Step 3: Calculate Metrics
-------------------------

Plan a metric calculation, run it locally or in batches, and write the standard long metric outputs used by later figures and dashboards.

.. code-block:: bash

   export METRIC_TASKS="$TABLES/metric_tasks.csv"
   export METRIC_ROWS="$TABLES/metric_rows.parquet"
   export TRACE_METADATA="$PREPROCESSED/metadata/trace_metadata_preprocessed.csv"

   svtk metrics inventories \
     --trace-metadata "$TRACE_METADATA" \
     --observed-output "$TABLES/observed_metric_inventory.csv" \
     --synthetic-output "$TABLES/synthetic_metric_inventory.csv" \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --verbose

   svtk metrics plan \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --observed-inventory "$TABLES/observed_metric_inventory.csv" \
     --synthetic-inventory "$TABLES/synthetic_metric_inventory.csv" \
     --qc-table "$QC_INVENTORY_OVERLAP" \
     --metric-group amplitude \
     --metric-group spectral \
     --component Z \
     --component R \
     --component T \
     --passband 1-2 \
     --passband 2-3 \
     --output "$METRIC_TASKS"

   svtk metrics estimate \
     --tasks "$METRIC_TASKS" \
     --seconds-per-task 60 \
     --memory-gb-per-task 2 \
     --parallel-tasks 4 \
     --output "$TABLES/metric_task_estimate.csv"

   svtk metrics run \
     --tasks "$METRIC_TASKS" \
     --qc-table "$QC_INVENTORY_OVERLAP" \
     --output "$METRIC_ROWS"

   svtk metrics outputs \
     --metrics "$METRIC_ROWS" \
     --events "$TABLES/prepared_events.csv" \
     --stations "$TABLES/prepared_stations.csv" \
     --output-dir "$TABLES" \
     --residual-column log2_residual \
     --score-column anderson_2004_gof \
     --format parquet

   svtk plot metrics residuals-vs-distance \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --y-col log2_residual \
     --group-col metric \
     --fit lowess \
     --no-connect-points

   svtk map spatial station-metric \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area \
     --value-col log2_residual \
     --metric PGA

   svtk plot metrics band-score-distribution \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --score-col log2_residual \
     --color-col metric

   The band-score plot defaults to the configured ``metrics_long`` table and
   ``band_score_distribution`` figure path. Pass ``--input`` or ``--output``
   only when you want to override those paths.

   Add ``--write-sidecar`` to any ``svtk plot``, ``svtk map``, or
   ``svtk visualize`` figure command to write CSV/JSON provenance next to the
   figure. Use ``--sidecar-rows N`` to write a deterministic row sample or omit
   it to write every plotted row. Use ``--sidecar-dir`` when sidecars should go
   somewhere other than the figure directory's ``sidecars`` folder.


Step 4: Spatial Statistics
--------------------------

Use the metric outputs to make spatial diagnostic maps and plots. The notebook version also walks through the intermediate spatial-statistics tables in Python, which is easier for exploratory analysis.

.. code-block:: bash

   svtk spatial summaries \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --metrics "$TABLES/metrics_long.parquet" \
     --metric PGA

   svtk map spatial station-bias \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area \
     --value-col mean_centered \
     --title "Mean PGA Station Bias"

   svtk map spatial residual-grid \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area \
     --value-col log2_residual

   svtk plot spatial correlogram \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO"

   svtk plot spatial cluster-solution-scores \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO"

   svtk map spatial pca-mode \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area \
     --kwargs mode=PC1


Step 5: GeoJSON Regions and Corridors
-------------------------------------

Work with region polygons and corridor selections, then make maps and waveform sections for the selected station-event paths.

.. code-block:: bash

   export REGIONS=data/examples/example_five_event_subset/metadata/example_path_regions.geojson

   svtk plot metrics boxplot \
     --input "$TABLES/metrics_long.parquet" \
     --output "$FIGURES/geojson_region_boxplot.png" \
     --value-col log2_residual \
     --passband "1-2 sec" \
     --model cvmsi_20260506_material_0p6x1p2_asdf \
     --kwargs dep=PGA indep=station_geojson_labels compare_to="LA Basin" table=true

   svtk map spatial event-residual \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area \
     --value-col log2_residual \
     --metric PGA \
     --kwargs station_region="LA Basin" event_region="Santa Monica Mountains"

   svtk map spatial corridor \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area

   svtk visualize waveforms observed-synthetic-record-section \
     --input "$TABLES/corridor_waveform_records.csv" \
     --output "$FIGURES/corridor_record_section.png" \
     --kwargs component=R gain=2.0 xlim_s='[0, 60]' sort_by=distance_km


Step 6: Additional Plotting Options
-----------------------------------

Create waveform maps, pattern-similarity diagnostics, and flexible metric plots from the standard metric and waveform tables.

.. code-block:: bash

   svtk visualize waveforms station-event-waveform-map \
     --input "$EVENT_STATIONS" \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area \
     --output "$FIGURES/station_event_waveform_map.png" \
     --kwargs component=R sort_by=distance_km max_time_s=90 lowpass_hz=1.0

   svtk plot spatial pattern-similarity \
     --input "$TABLES/pattern_similarity_station_anomalies.csv" \
     --output "$FIGURES/pattern_similarity.png"

   svtk plot metrics scatterplot \
     --input "$TABLES/metrics_long.parquet" \
     --output "$FIGURES/scatterplot_distance.png" \
     --value-col log2_residual \
     --passband "1-2 sec" \
     --model cvmsi_20260506_material_0p6x1p2_asdf \
     --fit lowess \
     --title "PGA and PGV Residuals vs Distance" \
     --kwargs dep='[PGA, PGV]' indep=distance colorby=dep

   svtk plot metrics boxplot \
     --input "$TABLES/metrics_long.parquet" \
     --output "$FIGURES/boxplot_by_region.png" \
     --value-col log2_residual \
     --passband "1-2 sec" \
     --model cvmsi_20260506_material_0p6x1p2_asdf \
     --kwargs dep='[PGA, PGV]' indep=station_geojson_labels compare_to="LA Basin" table=true

   svtk plot metrics heatmap \
     --input "$TABLES/metrics_long.parquet" \
     --output "$FIGURES/heatmap_by_region.png" \
     --value-col log2_residual \
     --passband "1-2 sec" \
     --passband "2-3 sec" \
     --model cvmsi_20260506_material_0p6x1p2_asdf \
     --kwargs dep='[PGA, PGV, PSA]' indep=station_geojson_labels


Step 7: Dashboards
------------------

Write dashboard-ready Parquet datasets and launch the Streamlit dashboard apps.

.. code-block:: bash

   svtk metrics outputs \
     --metrics "$TABLES/metrics_long.parquet" \
     --events "$TABLES/prepared_events.csv" \
     --stations "$TABLES/prepared_stations.csv" \
     --output-dir "$TABLES" \
     --residual-column log2_residual \
     --score-column anderson_2004_gof \
     --format parquet \
     --dashboard-partitioned

   svtk dashboard metrics \
     --port 8501 \
     --proxy-mode

   svtk dashboard qc \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --port 8502 \
     --proxy-mode

Use ``--proxy-mode`` when opening dashboards through a reverse proxy. It
disables Streamlit's local origin checks for the dashboard process so the
proxied browser connection can attach to the app.
