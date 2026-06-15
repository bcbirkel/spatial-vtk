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

   svtk config show \
     --config "$CONFIG" \
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
     --input "$TABLES/prepared_stations.csv" \
     --events "$TABLES/prepared_events.csv" \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area \
     --output "$FIGURES/station_event_context.png"

   svtk visualize context station-event-beachball \
     --input "$TABLES/prepared_events.csv" \
     --stations "$TABLES/prepared_stations.csv" \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area \
     --output "$FIGURES/event_beachball_map.png"


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

   svtk call spatial_vtk.qc.build_waveform_qc_summary \
     --kwargs event_station_records="$EVENT_STATIONS" components='[Z, R, T]' passbands='[[1, 2], [2, 3]]' \
     --output "$TRACE_QC"

   svtk call spatial_vtk.qc.build_metric_qc_summary \
     --kwargs event_station_records="$EVENT_STATIONS" metrics='[PGA, PGV, PGD, PSA, FAS]' components='[Z, R, T]' passbands='[[1, 2], [2, 3]]' spectral_periods_s='[1.0, 2.0, 3.0, 5.0]' synthetic_max_frequency_hz=1.0 trace_qc_summary="$TRACE_QC" \
     --output "$QC_INVENTORY"

   svtk call spatial_vtk.qc.write_qc_inventory_overlap_from_full \
     --kwargs qc_inventory="$QC_INVENTORY" event_station_records="$EVENT_STATIONS" output_path="$QC_INVENTORY_OVERLAP" scope=event chunksize=1000000 verbose=true

   svtk call spatial_vtk.qc.write_comparison_eligibility_from_qc_inventory \
     --kwargs qc_summary="$QC_INVENTORY_OVERLAP" output_path="$TABLES/comparison_eligible_records.csv" chunksize=1000000 verbose=true

   svtk call spatial_vtk.qc.build_metric_pair_retention_table_from_qc_inventory \
     --args "$QC_INVENTORY_OVERLAP" \
     --output "$TABLES/metric_pair_retention.csv"

   svtk call spatial_vtk.qc.build_event_station_pair_retention_table_from_qc_inventory \
     --args "$QC_INVENTORY_OVERLAP" \
     --output "$TABLES/event_station_pair_retention.csv"

   svtk qc manual-queue \
     --trace-summary "$TRACE_QC" \
     --output "$TABLES/manual_review_queue.csv" \
     --component R

   svtk visualize qc retention-summary \
     --input "$QC_INVENTORY_OVERLAP" \
     --output "$FIGURES/retention_summary.png"

   svtk visualize qc event-station-retention \
     --input "$TABLES/event_station_pair_retention.csv" \
     --output "$FIGURES/data_synthetic_availability.png"

   svtk visualize waveforms observed-synthetic-record-section \
     --input "$EVENT_STATIONS" \
     --output "$FIGURES/event_trace_comparison.png" \
     --kwargs component=R gain=2.0 max_distance_km=50.0 xlim_s='[0, 60]'

   svtk dashboard qc \
     --trace-summary "$TRACE_QC" \
     --port 8502


Step 3: Calculate Metrics
-------------------------

Plan a metric calculation, run it locally or in batches, and write the standard long metric outputs used by later figures and dashboards.

.. code-block:: bash

   export METRIC_TASKS="$TABLES/metric_tasks.csv"
   export METRIC_ROWS="$TABLES/metric_rows.parquet"

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

   svtk call spatial_vtk.metrics.workflow.summarize_metric_tasks \
     --args "$METRIC_TASKS" \
     --kwargs seconds_per_task=60 memory_gb_per_task=2 parallel_tasks=4 \
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
     --input "$TABLES/metrics_long.parquet" \
     --output "$FIGURES/residuals_vs_distance.png" \
     --kwargs y_col=log2_residual group_col=metric fit=lowess connect_points=false

   svtk map spatial station-metric \
     --input "$TABLES/metrics_long.parquet" \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area \
     --output "$FIGURES/station_residual_map.png" \
     --kwargs value_col=log2_residual metric=PGA

   svtk plot metrics band-score-distribution \
     --input "$TABLES/metrics_long.parquet" \
     --output "$FIGURES/band_score_distribution.png" \
     --kwargs score_col=log2_residual color_col=metric


Step 4: Spatial Statistics
--------------------------

Use the metric outputs to make spatial diagnostic maps and plots. The notebook version also walks through the intermediate spatial-statistics tables in Python, which is easier for exploratory analysis.

.. code-block:: bash

   export SPATIAL=outputs/tutorials/spatial
   mkdir -p "$SPATIAL"

   svtk map spatial station-bias \
     --input "$TABLES/station_bias.parquet" \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area \
     --output "$FIGURES/station_bias_map.png" \
     --kwargs value_col=mean_centered title="Mean PGA Station Bias"

   svtk map spatial residual-grid \
     --input "$TABLES/residual_grid.parquet" \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area \
     --output "$FIGURES/residual_grid.png" \
     --kwargs value_col=log2_residual

   svtk plot spatial correlogram \
     --input "$SPATIAL/distance_bin_correlations.csv" \
     --output "$FIGURES/correlogram.png"

   svtk plot spatial cluster-solution-scores \
     --input "$TABLES/cluster_scores.csv" \
     --output "$FIGURES/cluster_solution_scores.png"

   svtk map spatial pca-mode \
     --input "$TABLES/pca_station_scores.parquet" \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area \
     --output "$FIGURES/pca_mode_map.png" \
     --kwargs mode=PC1


Step 5: GeoJSON Regions and Corridors
-------------------------------------

Work with region polygons and corridor selections, then make maps and waveform sections for the selected station-event paths.

.. code-block:: bash

   export REGIONS=data/examples/example_five_event_subset/metadata/example_path_regions.geojson

   svtk plot metrics boxplot \
     --input "$TABLES/metrics_long.parquet" \
     --output "$FIGURES/geojson_region_boxplot.png" \
     --kwargs value_col=log2_residual dep=PGA indep=station_geojson_labels compare_to="LA Basin" table=true passband="1-2 sec" model=cvmsi_20260506_material_0p6x1p2_asdf

   svtk map spatial event-residual \
     --input "$TABLES/path_table.parquet" \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area \
     --output "$FIGURES/event_residual_map.png" \
     --kwargs value_col=log2_residual metric=PGA station_region="LA Basin" event_region="Santa Monica Mountains"

   svtk map spatial corridor \
     --input "$TABLES/corridors.parquet" \
     --records "$TABLES/path_table.parquet" \
     --stations "$TABLES/prepared_stations.csv" \
     --events "$TABLES/prepared_events.csv" \
     --config "$CONFIG" \
     --run-scenario "$SCENARIO" \
     --bounds study_area \
     --output "$FIGURES/corridor_map.png"

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
     --kwargs value_col=log2_residual dep='[PGA, PGV]' indep=distance passband="1-2 sec" model=cvmsi_20260506_material_0p6x1p2_asdf fit=lowess colorby=dep title="PGA and PGV Residuals vs Distance"

   svtk plot metrics boxplot \
     --input "$TABLES/metrics_long.parquet" \
     --output "$FIGURES/boxplot_by_region.png" \
     --kwargs value_col=log2_residual dep='[PGA, PGV]' indep=station_geojson_labels compare_to="LA Basin" table=true passband="1-2 sec" model=cvmsi_20260506_material_0p6x1p2_asdf

   svtk plot metrics heatmap \
     --input "$TABLES/metrics_long.parquet" \
     --output "$FIGURES/heatmap_by_region.png" \
     --kwargs value_col=log2_residual dep='[PGA, PGV, PSA]' indep=station_geojson_labels passband='[1-2 sec, 2-3 sec]' model=cvmsi_20260506_material_0p6x1p2_asdf


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
     --metrics-root "$TABLES/dashboard_metrics" \
     --summary-root "$TABLES/dashboard_summaries" \
     --port 8501

   svtk dashboard qc \
     --trace-summary "$TRACE_QC" \
     --port 8502
