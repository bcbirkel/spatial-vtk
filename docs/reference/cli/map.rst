.. _cli-svtk-map:

svtk map
========

Command Tree
------------

- :ref:`svtk map <cli-svtk-map>`
   - :ref:`svtk map spatial <cli-svtk-map-spatial>`
      - :ref:`svtk map spatial block-holdout-error <cli-svtk-map-spatial-block-holdout-error>`
      - :ref:`svtk map spatial cluster <cli-svtk-map-spatial-cluster>`
      - :ref:`svtk map spatial corridor <cli-svtk-map-spatial-corridor>`
      - :ref:`svtk map spatial event-residual <cli-svtk-map-spatial-event-residual>`
      - :ref:`svtk map spatial list <cli-svtk-map-spatial-list>`
      - :ref:`svtk map spatial metric-by-model <cli-svtk-map-spatial-metric-by-model>`
      - :ref:`svtk map spatial model-improvement <cli-svtk-map-spatial-model-improvement>`
      - :ref:`svtk map spatial pca-mode <cli-svtk-map-spatial-pca-mode>`
      - :ref:`svtk map spatial redcap-cluster <cli-svtk-map-spatial-redcap-cluster>`
      - :ref:`svtk map spatial residual-grid <cli-svtk-map-spatial-residual-grid>`
      - :ref:`svtk map spatial score <cli-svtk-map-spatial-score>`
      - :ref:`svtk map spatial station-bias <cli-svtk-map-spatial-station-bias>`
      - :ref:`svtk map spatial station-metric <cli-svtk-map-spatial-station-metric>`

Command Details
---------------

.. rubric:: Usage

.. code-block:: bash

   svtk map [-h] {spatial} ...

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

.. _cli-svtk-map-spatial:

svtk map spatial
^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial [-h]
                        {list,block-holdout-error,cluster,corridor,event-residual,metric-by-model,model-improvement,pca-mode,redcap-cluster,residual-grid,score,station-bias,station-metric}
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

.. _cli-svtk-map-spatial-block-holdout-error:

svtk map spatial block-holdout-error
""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial block-holdout-error [-h] [--input INPUT]
                                            [--output OUTPUT]
                                            [--config CONFIG]
                                            [--run-scenario RUN_SCENARIO]
                                            [--table TABLE]
                                            [--kwargs [KWARGS ...]]
                                            [--kwargs-json KWARGS_JSON]
                                            [--metric METRIC]
                                            [--passband PASSBAND]
                                            [--component COMPONENT]
                                            [--model MODEL]
                                            [--value-col VALUE_COL]
                                            [--score-col SCORE_COL]
                                            [--x-col X_COL] [--y-col Y_COL]
                                            [--group-col GROUP_COL]
                                            [--color-col COLOR_COL]
                                            [--fit FIT]
                                            [--connect-points | --no-connect-points]
                                            [--mode MODE] [--title TITLE]
                                            [--write-sidecar]
                                            [--sidecar-rows SIDECAR_ROWS]
                                            [--sidecar-dir SIDECAR_DIR]
                                            [--bounds BOUNDS] [--no-basemap]
                                            [--basemap-source BASEMAP_SOURCE]

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
   * - ``--input``
     - No
     -
     - Value: ``input``. Input CSV/parquet table for function argument 'prediction_df'. Defaults to configured output table 'block_holdout_predictions' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``
     - No
     -
     - Value: ``output``. Output figure path. Defaults to configured figure output 'block_holdout_error' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Repeatable
     - Value: ``table``. Extra table as argument_name=path. May be repeated.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Value: ``kwargs``. Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Value: ``kwargs_json``. Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Value: ``metric``. Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Value: ``passband``. Passband filter/value. Repeat for multiple passbands.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Value: ``model``. Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Value: ``value_col``. Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Value: ``score_col``. Column containing scores or residual values for score-style plots.
   * - ``--x-col``
     - No
     -
     - Value: ``x_col``. Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Value: ``y_col``. Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Value: ``group_col``. Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Value: ``color_col``. Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Value: ``fit``. Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Value: ``connect_points``. Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Value: ``mode``. Mode selector for figures that support named modes, such as PCA maps.
   * - ``--title``
     - No
     -
     - Value: ``title``. Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Value: ``sidecar_rows``. Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Value: ``sidecar_dir``. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Value: ``bounds``. Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Value: ``basemap_source``. Optional contextily basemap source.

.. _cli-svtk-map-spatial-cluster:

svtk map spatial cluster
""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial cluster [-h] [--input INPUT] [--output OUTPUT]
                                [--config CONFIG]
                                [--run-scenario RUN_SCENARIO] [--table TABLE]
                                [--kwargs [KWARGS ...]]
                                [--kwargs-json KWARGS_JSON] [--metric METRIC]
                                [--passband PASSBAND] [--component COMPONENT]
                                [--model MODEL] [--value-col VALUE_COL]
                                [--score-col SCORE_COL] [--x-col X_COL]
                                [--y-col Y_COL] [--group-col GROUP_COL]
                                [--color-col COLOR_COL] [--fit FIT]
                                [--connect-points | --no-connect-points]
                                [--mode MODE] [--title TITLE]
                                [--write-sidecar]
                                [--sidecar-rows SIDECAR_ROWS]
                                [--sidecar-dir SIDECAR_DIR] [--bounds BOUNDS]
                                [--no-basemap]
                                [--basemap-source BASEMAP_SOURCE]

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
   * - ``--input``
     - No
     -
     - Value: ``input``. Input CSV/parquet table for function argument 'assignments_df'. Defaults to configured output table 'clusters' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``
     - No
     -
     - Value: ``output``. Output figure path. Defaults to configured figure output 'cluster' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Repeatable
     - Value: ``table``. Extra table as argument_name=path. May be repeated.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Value: ``kwargs``. Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Value: ``kwargs_json``. Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Value: ``metric``. Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Value: ``passband``. Passband filter/value. Repeat for multiple passbands.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Value: ``model``. Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Value: ``value_col``. Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Value: ``score_col``. Column containing scores or residual values for score-style plots.
   * - ``--x-col``
     - No
     -
     - Value: ``x_col``. Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Value: ``y_col``. Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Value: ``group_col``. Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Value: ``color_col``. Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Value: ``fit``. Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Value: ``connect_points``. Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Value: ``mode``. Mode selector for figures that support named modes, such as PCA maps.
   * - ``--title``
     - No
     -
     - Value: ``title``. Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Value: ``sidecar_rows``. Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Value: ``sidecar_dir``. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Value: ``bounds``. Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Value: ``basemap_source``. Optional contextily basemap source.

.. _cli-svtk-map-spatial-corridor:

svtk map spatial corridor
"""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial corridor [-h] [--input INPUT] [--output OUTPUT]
                                 [--config CONFIG]
                                 [--run-scenario RUN_SCENARIO] [--table TABLE]
                                 [--kwargs [KWARGS ...]]
                                 [--kwargs-json KWARGS_JSON] [--metric METRIC]
                                 [--passband PASSBAND] [--component COMPONENT]
                                 [--model MODEL] [--value-col VALUE_COL]
                                 [--score-col SCORE_COL] [--x-col X_COL]
                                 [--y-col Y_COL] [--group-col GROUP_COL]
                                 [--color-col COLOR_COL] [--fit FIT]
                                 [--connect-points | --no-connect-points]
                                 [--mode MODE] [--title TITLE]
                                 [--write-sidecar]
                                 [--sidecar-rows SIDECAR_ROWS]
                                 [--sidecar-dir SIDECAR_DIR] [--events EVENTS]
                                 [--records RECORDS] [--stations STATIONS]
                                 [--bounds BOUNDS] [--no-basemap]
                                 [--basemap-source BASEMAP_SOURCE]

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
   * - ``--input``
     - No
     -
     - Value: ``input``. Input CSV/parquet table for function argument 'corridors_df'. Defaults to configured output table 'corridors' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``
     - No
     -
     - Value: ``output``. Output figure path. Defaults to configured figure output 'corridor_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Repeatable
     - Value: ``table``. Extra table as argument_name=path. May be repeated.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Value: ``kwargs``. Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Value: ``kwargs_json``. Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Value: ``metric``. Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Value: ``passband``. Passband filter/value. Repeat for multiple passbands.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Value: ``model``. Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Value: ``value_col``. Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Value: ``score_col``. Column containing scores or residual values for score-style plots.
   * - ``--x-col``
     - No
     -
     - Value: ``x_col``. Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Value: ``y_col``. Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Value: ``group_col``. Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Value: ``color_col``. Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Value: ``fit``. Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Value: ``connect_points``. Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Value: ``mode``. Mode selector for figures that support named modes, such as PCA maps.
   * - ``--title``
     - No
     -
     - Value: ``title``. Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Value: ``sidecar_rows``. Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Value: ``sidecar_dir``. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--events``
     - No
     -
     - Value: ``events``. Convenience CSV/parquet table path for function argument 'events_df'. Defaults to configured output table 'prepared_events' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--records``
     - No
     -
     - Value: ``records``. Convenience CSV/parquet table path for function argument 'records_df'. Defaults to configured output table 'event_station_records' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--stations``
     - No
     -
     - Value: ``stations``. Convenience CSV/parquet table path for function argument 'stations_df'. Defaults to configured output table 'prepared_stations' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--bounds``
     - No
     -
     - Value: ``bounds``. Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Value: ``basemap_source``. Optional contextily basemap source.

.. _cli-svtk-map-spatial-event-residual:

svtk map spatial event-residual
"""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial event-residual [-h] [--input INPUT] [--output OUTPUT]
                                       [--config CONFIG]
                                       [--run-scenario RUN_SCENARIO]
                                       [--table TABLE] [--kwargs [KWARGS ...]]
                                       [--kwargs-json KWARGS_JSON]
                                       [--metric METRIC] [--passband PASSBAND]
                                       [--component COMPONENT] [--model MODEL]
                                       [--value-col VALUE_COL]
                                       [--score-col SCORE_COL] [--x-col X_COL]
                                       [--y-col Y_COL] [--group-col GROUP_COL]
                                       [--color-col COLOR_COL] [--fit FIT]
                                       [--connect-points | --no-connect-points]
                                       [--mode MODE] [--title TITLE]
                                       [--write-sidecar]
                                       [--sidecar-rows SIDECAR_ROWS]
                                       [--sidecar-dir SIDECAR_DIR]
                                       [--bounds BOUNDS] [--no-basemap]
                                       [--basemap-source BASEMAP_SOURCE]

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
   * - ``--input``
     - No
     -
     - Value: ``input``. Input CSV/parquet table for function argument 'df'. Defaults to configured output table 'path_table' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``
     - No
     -
     - Value: ``output``. Output figure path. Defaults to configured figure output 'event_residual_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Repeatable
     - Value: ``table``. Extra table as argument_name=path. May be repeated.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Value: ``kwargs``. Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Value: ``kwargs_json``. Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Value: ``metric``. Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Value: ``passband``. Passband filter/value. Repeat for multiple passbands.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Value: ``model``. Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Value: ``value_col``. Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Value: ``score_col``. Column containing scores or residual values for score-style plots.
   * - ``--x-col``
     - No
     -
     - Value: ``x_col``. Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Value: ``y_col``. Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Value: ``group_col``. Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Value: ``color_col``. Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Value: ``fit``. Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Value: ``connect_points``. Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Value: ``mode``. Mode selector for figures that support named modes, such as PCA maps.
   * - ``--title``
     - No
     -
     - Value: ``title``. Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Value: ``sidecar_rows``. Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Value: ``sidecar_dir``. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Value: ``bounds``. Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Value: ``basemap_source``. Optional contextily basemap source.

.. _cli-svtk-map-spatial-list:

svtk map spatial list
"""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial list [-h]

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

.. _cli-svtk-map-spatial-metric-by-model:

svtk map spatial metric-by-model
""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial metric-by-model [-h] [--input INPUT] [--output OUTPUT]
                                        [--config CONFIG]
                                        [--run-scenario RUN_SCENARIO]
                                        [--table TABLE]
                                        [--kwargs [KWARGS ...]]
                                        [--kwargs-json KWARGS_JSON]
                                        [--metric METRIC]
                                        [--passband PASSBAND]
                                        [--component COMPONENT]
                                        [--model MODEL]
                                        [--value-col VALUE_COL]
                                        [--score-col SCORE_COL]
                                        [--x-col X_COL] [--y-col Y_COL]
                                        [--group-col GROUP_COL]
                                        [--color-col COLOR_COL] [--fit FIT]
                                        [--connect-points | --no-connect-points]
                                        [--mode MODE] [--title TITLE]
                                        [--write-sidecar]
                                        [--sidecar-rows SIDECAR_ROWS]
                                        [--sidecar-dir SIDECAR_DIR]
                                        [--bounds BOUNDS] [--no-basemap]
                                        [--basemap-source BASEMAP_SOURCE]

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
   * - ``--input``
     - No
     -
     - Value: ``input``. Input CSV/parquet table for function argument 'df'. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``
     - No
     -
     - Value: ``output``. Output figure path. Defaults to configured figure output 'metric_map_by_model' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Repeatable
     - Value: ``table``. Extra table as argument_name=path. May be repeated.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Value: ``kwargs``. Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Value: ``kwargs_json``. Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Value: ``metric``. Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Value: ``passband``. Passband filter/value. Repeat for multiple passbands.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Value: ``model``. Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Value: ``value_col``. Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Value: ``score_col``. Column containing scores or residual values for score-style plots.
   * - ``--x-col``
     - No
     -
     - Value: ``x_col``. Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Value: ``y_col``. Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Value: ``group_col``. Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Value: ``color_col``. Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Value: ``fit``. Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Value: ``connect_points``. Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Value: ``mode``. Mode selector for figures that support named modes, such as PCA maps.
   * - ``--title``
     - No
     -
     - Value: ``title``. Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Value: ``sidecar_rows``. Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Value: ``sidecar_dir``. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Value: ``bounds``. Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Value: ``basemap_source``. Optional contextily basemap source.

.. _cli-svtk-map-spatial-model-improvement:

svtk map spatial model-improvement
""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial model-improvement [-h] --input INPUT [--output OUTPUT]
                                          [--config CONFIG]
                                          [--run-scenario RUN_SCENARIO]
                                          [--table TABLE]
                                          [--kwargs [KWARGS ...]]
                                          [--kwargs-json KWARGS_JSON]
                                          [--metric METRIC]
                                          [--passband PASSBAND]
                                          [--component COMPONENT]
                                          [--model MODEL]
                                          [--value-col VALUE_COL]
                                          [--score-col SCORE_COL]
                                          [--x-col X_COL] [--y-col Y_COL]
                                          [--group-col GROUP_COL]
                                          [--color-col COLOR_COL] [--fit FIT]
                                          [--connect-points | --no-connect-points]
                                          [--mode MODE] [--title TITLE]
                                          [--write-sidecar]
                                          [--sidecar-rows SIDECAR_ROWS]
                                          [--sidecar-dir SIDECAR_DIR]
                                          [--bounds BOUNDS] [--no-basemap]
                                          [--basemap-source BASEMAP_SOURCE]

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
   * - ``--input``
     - Yes
     -
     - Value: ``input``. Input CSV/parquet table for function argument 'df'.
   * - ``--output``
     - No
     -
     - Value: ``output``. Output figure path. Defaults to configured figure output 'model_improvement' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Repeatable
     - Value: ``table``. Extra table as argument_name=path. May be repeated.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Value: ``kwargs``. Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Value: ``kwargs_json``. Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Value: ``metric``. Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Value: ``passband``. Passband filter/value. Repeat for multiple passbands.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Value: ``model``. Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Value: ``value_col``. Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Value: ``score_col``. Column containing scores or residual values for score-style plots.
   * - ``--x-col``
     - No
     -
     - Value: ``x_col``. Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Value: ``y_col``. Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Value: ``group_col``. Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Value: ``color_col``. Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Value: ``fit``. Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Value: ``connect_points``. Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Value: ``mode``. Mode selector for figures that support named modes, such as PCA maps.
   * - ``--title``
     - No
     -
     - Value: ``title``. Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Value: ``sidecar_rows``. Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Value: ``sidecar_dir``. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Value: ``bounds``. Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Value: ``basemap_source``. Optional contextily basemap source.

.. _cli-svtk-map-spatial-pca-mode:

svtk map spatial pca-mode
"""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial pca-mode [-h] [--input INPUT] [--output OUTPUT]
                                 [--config CONFIG]
                                 [--run-scenario RUN_SCENARIO] [--table TABLE]
                                 [--kwargs [KWARGS ...]]
                                 [--kwargs-json KWARGS_JSON] [--metric METRIC]
                                 [--passband PASSBAND] [--component COMPONENT]
                                 [--model MODEL] [--value-col VALUE_COL]
                                 [--score-col SCORE_COL] [--x-col X_COL]
                                 [--y-col Y_COL] [--group-col GROUP_COL]
                                 [--color-col COLOR_COL] [--fit FIT]
                                 [--connect-points | --no-connect-points]
                                 [--mode MODE] [--title TITLE]
                                 [--write-sidecar]
                                 [--sidecar-rows SIDECAR_ROWS]
                                 [--sidecar-dir SIDECAR_DIR] [--bounds BOUNDS]
                                 [--no-basemap]
                                 [--basemap-source BASEMAP_SOURCE]

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
   * - ``--input``
     - No
     -
     - Value: ``input``. Input CSV/parquet table for function argument 'station_scores_df'. Defaults to configured output table 'pca_station_scores' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``
     - No
     -
     - Value: ``output``. Output figure path. Defaults to configured figure output 'pca_mode_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Repeatable
     - Value: ``table``. Extra table as argument_name=path. May be repeated.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Value: ``kwargs``. Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Value: ``kwargs_json``. Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Value: ``metric``. Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Value: ``passband``. Passband filter/value. Repeat for multiple passbands.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Value: ``model``. Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Value: ``value_col``. Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Value: ``score_col``. Column containing scores or residual values for score-style plots.
   * - ``--x-col``
     - No
     -
     - Value: ``x_col``. Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Value: ``y_col``. Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Value: ``group_col``. Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Value: ``color_col``. Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Value: ``fit``. Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Value: ``connect_points``. Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Value: ``mode``. Mode selector for figures that support named modes, such as PCA maps.
   * - ``--title``
     - No
     -
     - Value: ``title``. Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Value: ``sidecar_rows``. Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Value: ``sidecar_dir``. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Value: ``bounds``. Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Value: ``basemap_source``. Optional contextily basemap source.

.. _cli-svtk-map-spatial-redcap-cluster:

svtk map spatial redcap-cluster
"""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial redcap-cluster [-h] [--input INPUT] [--output OUTPUT]
                                       [--config CONFIG]
                                       [--run-scenario RUN_SCENARIO]
                                       [--table TABLE] [--kwargs [KWARGS ...]]
                                       [--kwargs-json KWARGS_JSON]
                                       [--metric METRIC] [--passband PASSBAND]
                                       [--component COMPONENT] [--model MODEL]
                                       [--value-col VALUE_COL]
                                       [--score-col SCORE_COL] [--x-col X_COL]
                                       [--y-col Y_COL] [--group-col GROUP_COL]
                                       [--color-col COLOR_COL] [--fit FIT]
                                       [--connect-points | --no-connect-points]
                                       [--mode MODE] [--title TITLE]
                                       [--write-sidecar]
                                       [--sidecar-rows SIDECAR_ROWS]
                                       [--sidecar-dir SIDECAR_DIR]
                                       [--bounds BOUNDS] [--no-basemap]
                                       [--basemap-source BASEMAP_SOURCE]

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
   * - ``--input``
     - No
     -
     - Value: ``input``. Input CSV/parquet table for function argument 'redcap_df'. Defaults to configured output table 'redcap_clusters' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``
     - No
     -
     - Value: ``output``. Output figure path. Defaults to configured figure output 'redcap_cluster_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Repeatable
     - Value: ``table``. Extra table as argument_name=path. May be repeated.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Value: ``kwargs``. Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Value: ``kwargs_json``. Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Value: ``metric``. Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Value: ``passband``. Passband filter/value. Repeat for multiple passbands.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Value: ``model``. Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Value: ``value_col``. Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Value: ``score_col``. Column containing scores or residual values for score-style plots.
   * - ``--x-col``
     - No
     -
     - Value: ``x_col``. Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Value: ``y_col``. Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Value: ``group_col``. Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Value: ``color_col``. Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Value: ``fit``. Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Value: ``connect_points``. Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Value: ``mode``. Mode selector for figures that support named modes, such as PCA maps.
   * - ``--title``
     - No
     -
     - Value: ``title``. Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Value: ``sidecar_rows``. Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Value: ``sidecar_dir``. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Value: ``bounds``. Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Value: ``basemap_source``. Optional contextily basemap source.

.. _cli-svtk-map-spatial-residual-grid:

svtk map spatial residual-grid
""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial residual-grid [-h] [--input INPUT] [--output OUTPUT]
                                      [--config CONFIG]
                                      [--run-scenario RUN_SCENARIO]
                                      [--table TABLE] [--kwargs [KWARGS ...]]
                                      [--kwargs-json KWARGS_JSON]
                                      [--metric METRIC] [--passband PASSBAND]
                                      [--component COMPONENT] [--model MODEL]
                                      [--value-col VALUE_COL]
                                      [--score-col SCORE_COL] [--x-col X_COL]
                                      [--y-col Y_COL] [--group-col GROUP_COL]
                                      [--color-col COLOR_COL] [--fit FIT]
                                      [--connect-points | --no-connect-points]
                                      [--mode MODE] [--title TITLE]
                                      [--write-sidecar]
                                      [--sidecar-rows SIDECAR_ROWS]
                                      [--sidecar-dir SIDECAR_DIR]
                                      [--bounds BOUNDS] [--no-basemap]
                                      [--basemap-source BASEMAP_SOURCE]

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
   * - ``--input``
     - No
     -
     - Value: ``input``. Input CSV/parquet table for function argument 'grid_df'. Defaults to configured output table 'metric_field' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``
     - No
     -
     - Value: ``output``. Output figure path. Defaults to configured figure output 'residual_grid' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Repeatable
     - Value: ``table``. Extra table as argument_name=path. May be repeated.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Value: ``kwargs``. Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Value: ``kwargs_json``. Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Value: ``metric``. Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Value: ``passband``. Passband filter/value. Repeat for multiple passbands.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Value: ``model``. Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Value: ``value_col``. Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Value: ``score_col``. Column containing scores or residual values for score-style plots.
   * - ``--x-col``
     - No
     -
     - Value: ``x_col``. Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Value: ``y_col``. Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Value: ``group_col``. Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Value: ``color_col``. Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Value: ``fit``. Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Value: ``connect_points``. Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Value: ``mode``. Mode selector for figures that support named modes, such as PCA maps.
   * - ``--title``
     - No
     -
     - Value: ``title``. Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Value: ``sidecar_rows``. Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Value: ``sidecar_dir``. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Value: ``bounds``. Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Value: ``basemap_source``. Optional contextily basemap source.

.. _cli-svtk-map-spatial-score:

svtk map spatial score
""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial score [-h] [--input INPUT] [--output OUTPUT]
                              [--config CONFIG] [--run-scenario RUN_SCENARIO]
                              [--table TABLE] [--kwargs [KWARGS ...]]
                              [--kwargs-json KWARGS_JSON] [--metric METRIC]
                              [--passband PASSBAND] [--component COMPONENT]
                              [--model MODEL] [--value-col VALUE_COL]
                              [--score-col SCORE_COL] [--x-col X_COL]
                              [--y-col Y_COL] [--group-col GROUP_COL]
                              [--color-col COLOR_COL] [--fit FIT]
                              [--connect-points | --no-connect-points]
                              [--mode MODE] [--title TITLE] [--write-sidecar]
                              [--sidecar-rows SIDECAR_ROWS]
                              [--sidecar-dir SIDECAR_DIR] [--bounds BOUNDS]
                              [--no-basemap] [--basemap-source BASEMAP_SOURCE]

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
   * - ``--input``
     - No
     -
     - Value: ``input``. Input CSV/parquet table for function argument 'df'. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``
     - No
     -
     - Value: ``output``. Output figure path. Defaults to configured figure output 'score' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Repeatable
     - Value: ``table``. Extra table as argument_name=path. May be repeated.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Value: ``kwargs``. Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Value: ``kwargs_json``. Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Value: ``metric``. Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Value: ``passband``. Passband filter/value. Repeat for multiple passbands.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Value: ``model``. Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Value: ``value_col``. Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Value: ``score_col``. Column containing scores or residual values for score-style plots.
   * - ``--x-col``
     - No
     -
     - Value: ``x_col``. Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Value: ``y_col``. Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Value: ``group_col``. Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Value: ``color_col``. Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Value: ``fit``. Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Value: ``connect_points``. Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Value: ``mode``. Mode selector for figures that support named modes, such as PCA maps.
   * - ``--title``
     - No
     -
     - Value: ``title``. Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Value: ``sidecar_rows``. Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Value: ``sidecar_dir``. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Value: ``bounds``. Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Value: ``basemap_source``. Optional contextily basemap source.

.. _cli-svtk-map-spatial-station-bias:

svtk map spatial station-bias
"""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial station-bias [-h] [--input INPUT] [--output OUTPUT]
                                     [--config CONFIG]
                                     [--run-scenario RUN_SCENARIO]
                                     [--table TABLE] [--kwargs [KWARGS ...]]
                                     [--kwargs-json KWARGS_JSON]
                                     [--metric METRIC] [--passband PASSBAND]
                                     [--component COMPONENT] [--model MODEL]
                                     [--value-col VALUE_COL]
                                     [--score-col SCORE_COL] [--x-col X_COL]
                                     [--y-col Y_COL] [--group-col GROUP_COL]
                                     [--color-col COLOR_COL] [--fit FIT]
                                     [--connect-points | --no-connect-points]
                                     [--mode MODE] [--title TITLE]
                                     [--write-sidecar]
                                     [--sidecar-rows SIDECAR_ROWS]
                                     [--sidecar-dir SIDECAR_DIR]
                                     [--bounds BOUNDS] [--no-basemap]
                                     [--basemap-source BASEMAP_SOURCE]

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
   * - ``--input``
     - No
     -
     - Value: ``input``. Input CSV/parquet table for function argument 'station_df'. Defaults to configured output table 'station_bias' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``
     - No
     -
     - Value: ``output``. Output figure path. Defaults to configured figure output 'station_residual_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Repeatable
     - Value: ``table``. Extra table as argument_name=path. May be repeated.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Value: ``kwargs``. Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Value: ``kwargs_json``. Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Value: ``metric``. Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Value: ``passband``. Passband filter/value. Repeat for multiple passbands.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Value: ``model``. Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Value: ``value_col``. Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Value: ``score_col``. Column containing scores or residual values for score-style plots.
   * - ``--x-col``
     - No
     -
     - Value: ``x_col``. Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Value: ``y_col``. Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Value: ``group_col``. Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Value: ``color_col``. Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Value: ``fit``. Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Value: ``connect_points``. Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Value: ``mode``. Mode selector for figures that support named modes, such as PCA maps.
   * - ``--title``
     - No
     -
     - Value: ``title``. Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Value: ``sidecar_rows``. Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Value: ``sidecar_dir``. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Value: ``bounds``. Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Value: ``basemap_source``. Optional contextily basemap source.

.. _cli-svtk-map-spatial-station-metric:

svtk map spatial station-metric
"""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial station-metric [-h] [--input INPUT] [--output OUTPUT]
                                       [--config CONFIG]
                                       [--run-scenario RUN_SCENARIO]
                                       [--table TABLE] [--kwargs [KWARGS ...]]
                                       [--kwargs-json KWARGS_JSON]
                                       [--metric METRIC] [--passband PASSBAND]
                                       [--component COMPONENT] [--model MODEL]
                                       [--value-col VALUE_COL]
                                       [--score-col SCORE_COL] [--x-col X_COL]
                                       [--y-col Y_COL] [--group-col GROUP_COL]
                                       [--color-col COLOR_COL] [--fit FIT]
                                       [--connect-points | --no-connect-points]
                                       [--mode MODE] [--title TITLE]
                                       [--write-sidecar]
                                       [--sidecar-rows SIDECAR_ROWS]
                                       [--sidecar-dir SIDECAR_DIR]
                                       [--bounds BOUNDS] [--no-basemap]
                                       [--basemap-source BASEMAP_SOURCE]

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
   * - ``--input``
     - No
     -
     - Value: ``input``. Input CSV/parquet table for function argument 'df'. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``
     - No
     -
     - Value: ``output``. Output figure path. Defaults to configured figure output 'station_metric_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Repeatable
     - Value: ``table``. Extra table as argument_name=path. May be repeated.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Value: ``kwargs``. Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Value: ``kwargs_json``. Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Value: ``metric``. Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Value: ``passband``. Passband filter/value. Repeat for multiple passbands.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Value: ``model``. Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Value: ``value_col``. Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Value: ``score_col``. Column containing scores or residual values for score-style plots.
   * - ``--x-col``
     - No
     -
     - Value: ``x_col``. Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Value: ``y_col``. Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Value: ``group_col``. Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Value: ``color_col``. Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Value: ``fit``. Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Value: ``connect_points``. Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Value: ``mode``. Mode selector for figures that support named modes, such as PCA maps.
   * - ``--title``
     - No
     -
     - Value: ``title``. Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Value: ``sidecar_rows``. Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Value: ``sidecar_dir``. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Value: ``bounds``. Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Value: ``basemap_source``. Optional contextily basemap source.
