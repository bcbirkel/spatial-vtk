.. _cli-svtk-spatial:

svtk spatial
============

Run spatial-statistics table workflows.

Command Tree
------------

- :ref:`svtk spatial <cli-svtk-spatial>`
   - :ref:`svtk spatial corridors <cli-svtk-spatial-corridors>` - Build configured boundary corridor tables from region GeoJSON and prepared metadata.
   - :ref:`svtk spatial derived-outputs <cli-svtk-spatial-derived-outputs>` - Build optional Step 4 spatial tables used by overview plots: block_holdout_predictions, redcap_clusters, and pattern_similarity_station_anomalies.
   - :ref:`svtk spatial geojson-summaries <cli-svtk-spatial-geojson-summaries>` - Build configured GeoJSON region summary tables from metric outputs.
   - :ref:`svtk spatial status <cli-svtk-spatial-status>` - Inspect configured spatial-statistics inputs and outputs without running calculations.
   - :ref:`svtk spatial summaries <cli-svtk-spatial-summaries>` - Build standard spatial-statistics summary tables.

Command Details
---------------

.. rubric:: Usage

.. code-block:: bash

   svtk spatial [-h]
                    {status,summaries,derived-outputs,geojson-summaries,corridors}
                    ...

.. rubric:: Parameters

.. list-table::
   :header-rows: 1
   :widths: 26 13 14 47

   * - Name
     - Required
     - Default / choices
     - Description
   * - ``-h``, ``--help``
     - No
     -
     - show this help message and exit

.. _cli-svtk-spatial-corridors:

svtk spatial corridors
^^^^^^^^^^^^^^^^^^^^^^

Build configured boundary corridor tables from region GeoJSON and prepared metadata.

.. rubric:: Usage

.. code-block:: bash

   svtk spatial corridors [-h] [--geojson GEOJSON] [--stations STATIONS]
                              [--events EVENTS] [--records RECORDS]
                              [--config CONFIG] [--run-scenario RUN_SCENARIO]
                              [--output-key OUTPUT_KEY] [--verbose]

.. rubric:: Parameters

.. list-table::
   :header-rows: 1
   :widths: 26 13 14 47

   * - Name
     - Required
     - Default / choices
     - Description
   * - ``-h``, ``--help``
     - No
     -
     - show this help message and exit
   * - ``--geojson``, ``--region-geojson``
     - No
     -
     - Value: ``geojson``. Region GeoJSON path. Defaults to paths.region_geojson.
   * - ``--stations``, ``--station-table``
     - No
     -
     - Value: ``stations``. Prepared station metadata table. Defaults to configured output table 'prepared_stations'.
   * - ``--events``, ``--event-table``
     - No
     -
     - Value: ``events``. Prepared event metadata table. Defaults to configured output table 'prepared_events'.
   * - ``--records``, ``--records-table``
     - No
     -
     - Value: ``records``. Event-station records used by max-records anchor strategies. Defaults to comparison_eligible_records when needed.
   * - ``--config``
     - No
     -
     - Value: ``config``. Spatial-VTK config file.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--output-key``, ``--output-table-key``
     - No
     - Default: ``corridors``
     - Value: ``output_key``. Registered output table key, not a filesystem path.
   * - ``--verbose``
     - No
     - Flag
     - Print elapsed-time progress for Slurm logs.

.. _cli-svtk-spatial-derived-outputs:

svtk spatial derived-outputs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Build optional Step 4 spatial tables used by overview plots: block_holdout_predictions, redcap_clusters, and pattern_similarity_station_anomalies.

.. rubric:: Usage

.. code-block:: bash

   svtk spatial derived-outputs [-h] [--metrics METRICS]
                                    [--metric-field METRIC_FIELD]
                                    [--station-bias STATION_BIAS]
                                    [--config CONFIG]
                                    [--run-scenario RUN_SCENARIO]
                                    [--metric METRIC]
                                    [--pattern-passband PATTERN_PASSBAND]
                                    [--pattern-component PATTERN_COMPONENT]
                                    [--pattern-model PATTERN_MODEL]
                                    [--outputs OUTPUTS] [--overwrite]
                                    [--verbose]

.. rubric:: Parameters

.. list-table::
   :header-rows: 1
   :widths: 26 13 14 47

   * - Name
     - Required
     - Default / choices
     - Description
   * - ``-h``, ``--help``
     - No
     -
     - show this help message and exit
   * - ``--metrics``
     - No
     -
     - Value: ``metrics``. Long metric rows table. Defaults to configured output table 'metrics_long'.
   * - ``--metric-field``
     - No
     -
     - Value: ``metric_field``. Metric-field table. Defaults to configured output table 'metric_field'.
   * - ``--station-bias``
     - No
     -
     - Value: ``station_bias``. Station-bias table. Defaults to configured output table 'station_bias'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Spatial-VTK config file.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--metric``
     - No
     -
     - Value: ``metric``. Metric filter. Defaults to spatial.pattern_metric/spatial.metric; use 'all' for all available metrics.
   * - ``--pattern-passband``
     - No
     -
     - Value: ``pattern_passband``. Pattern-similarity passband filter. Defaults to spatial.pattern_passband; use 'all' for all passbands.
   * - ``--pattern-component``
     - No
     -
     - Value: ``pattern_component``. Pattern-similarity component filter. Defaults to spatial.pattern_component; use 'all' for all components.
   * - ``--pattern-model``
     - No
     -
     - Value: ``pattern_model``. Pattern-similarity model filter. Defaults to spatial.pattern_model; use 'all' for all models.
   * - ``--outputs``
     - No
     - Default: ``all``
     - Value: ``outputs``. Comma-separated derived output keys to build. Defaults to all optional spatial derived outputs.
   * - ``--overwrite``
     - No
     - Flag
     - Overwrite existing derived output tables.
   * - ``--verbose``
     - No
     - Flag
     - Print elapsed-time progress for Slurm logs.

.. _cli-svtk-spatial-geojson-summaries:

svtk spatial geojson-summaries
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Build configured GeoJSON region summary tables from metric outputs.

.. rubric:: Usage

.. code-block:: bash

   svtk spatial geojson-summaries [-h] [--metrics METRICS]
                                      [--geojson GEOJSON] [--config CONFIG]
                                      [--run-scenario RUN_SCENARIO]
                                      [--selector SELECTOR]
                                      [--chunksize CHUNKSIZE]
                                      [--output-key OUTPUT_KEY] [--verbose]

.. rubric:: Parameters

.. list-table::
   :header-rows: 1
   :widths: 26 13 14 47

   * - Name
     - Required
     - Default / choices
     - Description
   * - ``-h``, ``--help``
     - No
     -
     - show this help message and exit
   * - ``--metrics``, ``--metrics-table``
     - No
     -
     - Value: ``metrics``. Metric rows table. Defaults to configured output table 'metrics_long'.
   * - ``--geojson``, ``--region-geojson``
     - No
     -
     - Value: ``geojson``. Region GeoJSON path. Defaults to paths.region_geojson.
   * - ``--config``
     - No
     -
     - Value: ``config``. Spatial-VTK config file.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--selector``
     - No
     - Default: ``all``
     - Value: ``selector``. GeoJSON polygon selector. Defaults to all polygons.
   * - ``--chunksize``
     - No
     - Default: ``1000000``
     - Value: ``chunksize``. Rows per metric-table chunk.
   * - ``--output-key``, ``--output-table-key``
     - No
     - Default: ``geojson_region_summaries``
     - Value: ``output_key``. Registered output table key, not a filesystem path.
   * - ``--verbose``
     - No
     - Flag
     - Print elapsed-time progress for Slurm logs.

.. _cli-svtk-spatial-status:

svtk spatial status
^^^^^^^^^^^^^^^^^^^

Inspect configured spatial-statistics inputs and outputs without running calculations.

.. rubric:: Usage

.. code-block:: bash

   svtk spatial status [-h] [--config CONFIG]
                           [--run-scenario RUN_SCENARIO] [--include-optional]
                           [--json]

.. rubric:: Parameters

.. list-table::
   :header-rows: 1
   :widths: 26 13 14 47

   * - Name
     - Required
     - Default / choices
     - Description
   * - ``-h``, ``--help``
     - No
     -
     - show this help message and exit
   * - ``--config``
     - No
     -
     - Value: ``config``. Spatial-VTK config file.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--include-optional``
     - No
     - Flag
     - Include optional spatial output artifacts in the status table.
   * - ``--json``
     - No
     - Flag
     - Print machine-readable JSON.

.. _cli-svtk-spatial-summaries:

svtk spatial summaries
^^^^^^^^^^^^^^^^^^^^^^

Build standard spatial-statistics summary tables.

.. rubric:: Usage

.. code-block:: bash

   svtk spatial summaries [-h] [--metrics METRICS] [--config CONFIG]
                              [--run-scenario RUN_SCENARIO] [--metric METRIC]
                              [--station-metadata STATION_METADATA]
                              [--checkpoint-dir CHECKPOINT_DIR] [--no-resume]
                              [--verbose]

.. rubric:: Parameters

.. list-table::
   :header-rows: 1
   :widths: 26 13 14 47

   * - Name
     - Required
     - Default / choices
     - Description
   * - ``-h``, ``--help``
     - No
     -
     - show this help message and exit
   * - ``--metrics``
     - No
     -
     - Value: ``metrics``. Metric rows table. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Spatial-VTK config file.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--metric``
     - No
     -
     - Value: ``metric``. Metric override. Use 'all' to process each metric in the input table.
   * - ``--station-metadata``
     - No
     -
     - Value: ``station_metadata``. Prepared station metadata table for geology contrasts. Defaults to configured output table 'prepared_stations'.
   * - ``--checkpoint-dir``
     - No
     -
     - Value: ``checkpoint_dir``. Base directory for resumable per-metric checkpoints. Defaults to a hidden directory next to the configured spatial output tables.
   * - ``--no-resume``
     - No
     - Flag
     - Do not reuse existing per-metric spatial summary checkpoints.
   * - ``--verbose``
     - No
     - Flag
     - Print elapsed-time progress for Slurm logs.
