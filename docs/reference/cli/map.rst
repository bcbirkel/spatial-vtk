.. _cli-svtk-map:

svtk map
========

Config-Backed Mapping
----------------------

If a config is active with ``svtk config set`` or passed with ``--config``, registered map commands resolve their standard input tables, figure outputs, and named map bounds automatically. For routine workflow maps, prefer the curated flags shown below instead of passing raw ``--input`` and ``--output`` paths.

.. code-block:: bash

   svtk config set runs/spatial_vtk_config.yaml
   svtk map spatial station-metric --value-col log2_residual --metric PGA --passband "2-3 sec"
   svtk map spatial event-residual --value-col log2_residual --metric PGA --bounds study_area

These commands use configured outputs such as ``metrics_long`` and ``path_table`` plus the registered figure keys for the selected map unless you supply ``--input``/``--input-table`` or ``--output``/``--figure-output`` explicitly. Run ``svtk map spatial list`` to print a table showing each map command's input and output source, including ``config:<key>`` defaults and ``required:--input`` entries.

Basemaps are enabled by default for map figures; use ``--no-basemap`` only when you explicitly want a data-only map.

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

   svtk map spatial block-holdout-error [-h] [--input PATH]
                                            [--output PATH] [--config CONFIG]
                                            [--run-scenario RUN_SCENARIO]
                                            [--table [TABLE]] [--no-table]
                                            [--kwargs [KWARGS ...]]
                                            [--kwargs-json KWARGS_JSON]
                                            [--metric METRIC]
                                            [--passband PASSBAND]
                                            [--bin-label BIN_LABEL]
                                            [--component COMPONENT]
                                            [--components COMPONENTS]
                                            [--model MODEL]
                                            [--value-col VALUE_COL]
                                            [--score-col SCORE_COL]
                                            [--x-col X_COL] [--y-col Y_COL]
                                            [--group-col GROUP_COL]
                                            [--color-col COLOR_COL]
                                            [--fit FIT]
                                            [--connect-points | --no-connect-points]
                                            [--mode MODE] [--dep DEP]
                                            [--indep INDEP]
                                            [--colorby COLORBY]
                                            [--compare-to COMPARE_TO]
                                            [--station-region STATION_REGIONS]
                                            [--event-region EVENT_REGIONS]
                                            [--scale SCALE]
                                            [--time-limit-s TIME_LIMIT_S]
                                            [--max-records MAX_RECORDS]
                                            [--max-traces MAX_TRACES]
                                            [--title TITLE] [--write-sidecar]
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
   * - ``--input``, ``--input-table``
     - No
     -
     - Filesystem path. Primary figure input table (block holdout predictions); accepts CSV or parquet. Defaults to configured output table 'block_holdout_predictions' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'block_holdout_error' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Value: ``table``. Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
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
   * - ``--bin-label``
     - No
     -
     - Value: ``bin_label``. Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Value: ``components``. Component list for waveform plots that use a components argument. Repeat for multiple components.
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
   * - ``--dep``
     - No
     - Repeatable
     - Value: ``dep``. Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Value: ``indep``. Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Value: ``colorby``. Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Value: ``compare_to``. Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Value: ``station_regions``. Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Value: ``event_regions``. Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Value: ``scale``. Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Value: ``time_limit_s``. Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Value: ``max_records``. Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Value: ``max_traces``. Maximum number of traces for waveform map figures.
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
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
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

   svtk map spatial cluster [-h] [--input PATH] [--output PATH]
                                [--config CONFIG]
                                [--run-scenario RUN_SCENARIO]
                                [--table [TABLE]] [--no-table]
                                [--kwargs [KWARGS ...]]
                                [--kwargs-json KWARGS_JSON] [--metric METRIC]
                                [--passband PASSBAND] [--bin-label BIN_LABEL]
                                [--component COMPONENT]
                                [--components COMPONENTS] [--model MODEL]
                                [--value-col VALUE_COL]
                                [--score-col SCORE_COL] [--x-col X_COL]
                                [--y-col Y_COL] [--group-col GROUP_COL]
                                [--color-col COLOR_COL] [--fit FIT]
                                [--connect-points | --no-connect-points]
                                [--mode MODE] [--dep DEP] [--indep INDEP]
                                [--colorby COLORBY] [--compare-to COMPARE_TO]
                                [--station-region STATION_REGIONS]
                                [--event-region EVENT_REGIONS] [--scale SCALE]
                                [--time-limit-s TIME_LIMIT_S]
                                [--max-records MAX_RECORDS]
                                [--max-traces MAX_TRACES] [--title TITLE]
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
   * - ``--input``, ``--input-table``
     - No
     -
     - Filesystem path. Primary figure input table (clusters); accepts CSV or parquet. Defaults to configured output table 'clusters' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'cluster' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Value: ``table``. Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
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
   * - ``--bin-label``
     - No
     -
     - Value: ``bin_label``. Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Value: ``components``. Component list for waveform plots that use a components argument. Repeat for multiple components.
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
   * - ``--dep``
     - No
     - Repeatable
     - Value: ``dep``. Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Value: ``indep``. Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Value: ``colorby``. Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Value: ``compare_to``. Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Value: ``station_regions``. Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Value: ``event_regions``. Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Value: ``scale``. Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Value: ``time_limit_s``. Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Value: ``max_records``. Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Value: ``max_traces``. Maximum number of traces for waveform map figures.
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
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
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

   svtk map spatial corridor [-h] [--input PATH] [--output PATH]
                                 [--config CONFIG]
                                 [--run-scenario RUN_SCENARIO]
                                 [--table [TABLE]] [--no-table]
                                 [--kwargs [KWARGS ...]]
                                 [--kwargs-json KWARGS_JSON] [--metric METRIC]
                                 [--passband PASSBAND] [--bin-label BIN_LABEL]
                                 [--component COMPONENT]
                                 [--components COMPONENTS] [--model MODEL]
                                 [--value-col VALUE_COL]
                                 [--score-col SCORE_COL] [--x-col X_COL]
                                 [--y-col Y_COL] [--group-col GROUP_COL]
                                 [--color-col COLOR_COL] [--fit FIT]
                                 [--connect-points | --no-connect-points]
                                 [--mode MODE] [--dep DEP] [--indep INDEP]
                                 [--colorby COLORBY] [--compare-to COMPARE_TO]
                                 [--station-region STATION_REGIONS]
                                 [--event-region EVENT_REGIONS]
                                 [--scale SCALE] [--time-limit-s TIME_LIMIT_S]
                                 [--max-records MAX_RECORDS]
                                 [--max-traces MAX_TRACES] [--title TITLE]
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
   * - ``--input``, ``--input-table``
     - No
     -
     - Filesystem path. Primary figure input table (corridors); accepts CSV or parquet. Defaults to configured output table 'corridors' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'corridor_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Value: ``table``. Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
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
   * - ``--bin-label``
     - No
     -
     - Value: ``bin_label``. Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Value: ``components``. Component list for waveform plots that use a components argument. Repeat for multiple components.
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
   * - ``--dep``
     - No
     - Repeatable
     - Value: ``dep``. Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Value: ``indep``. Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Value: ``colorby``. Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Value: ``compare_to``. Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Value: ``station_regions``. Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Value: ``event_regions``. Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Value: ``scale``. Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Value: ``time_limit_s``. Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Value: ``max_records``. Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Value: ``max_traces``. Maximum number of traces for waveform map figures.
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
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--events``
     - No
     -
     - Filesystem path. Convenience prepared events table path; accepts CSV or parquet. Defaults to configured output table 'prepared_events' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--records``
     - No
     -
     - Filesystem path. Convenience event station records table path; accepts CSV or parquet. Defaults to configured output table 'event_station_records' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--stations``
     - No
     -
     - Filesystem path. Convenience prepared stations table path; accepts CSV or parquet. Defaults to configured output table 'prepared_stations' when --config is passed or a default config is set with 'svtk config set'.
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

   svtk map spatial event-residual [-h] [--input PATH] [--output PATH]
                                       [--config CONFIG]
                                       [--run-scenario RUN_SCENARIO]
                                       [--table [TABLE]] [--no-table]
                                       [--kwargs [KWARGS ...]]
                                       [--kwargs-json KWARGS_JSON]
                                       [--metric METRIC] [--passband PASSBAND]
                                       [--bin-label BIN_LABEL]
                                       [--component COMPONENT]
                                       [--components COMPONENTS]
                                       [--model MODEL] [--value-col VALUE_COL]
                                       [--score-col SCORE_COL] [--x-col X_COL]
                                       [--y-col Y_COL] [--group-col GROUP_COL]
                                       [--color-col COLOR_COL] [--fit FIT]
                                       [--connect-points | --no-connect-points]
                                       [--mode MODE] [--dep DEP]
                                       [--indep INDEP] [--colorby COLORBY]
                                       [--compare-to COMPARE_TO]
                                       [--station-region STATION_REGIONS]
                                       [--event-region EVENT_REGIONS]
                                       [--scale SCALE]
                                       [--time-limit-s TIME_LIMIT_S]
                                       [--max-records MAX_RECORDS]
                                       [--max-traces MAX_TRACES]
                                       [--title TITLE] [--write-sidecar]
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
   * - ``--input``, ``--input-table``
     - No
     -
     - Filesystem path. Primary figure input table (path); accepts CSV or parquet. Defaults to configured output table 'path_table' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'event_residual_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Value: ``table``. Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
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
   * - ``--bin-label``
     - No
     -
     - Value: ``bin_label``. Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Value: ``components``. Component list for waveform plots that use a components argument. Repeat for multiple components.
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
   * - ``--dep``
     - No
     - Repeatable
     - Value: ``dep``. Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Value: ``indep``. Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Value: ``colorby``. Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Value: ``compare_to``. Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Value: ``station_regions``. Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Value: ``event_regions``. Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Value: ``scale``. Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Value: ``time_limit_s``. Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Value: ``max_records``. Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Value: ``max_traces``. Maximum number of traces for waveform map figures.
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
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
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

   svtk map spatial metric-by-model [-h] [--input PATH] [--output PATH]
                                        [--config CONFIG]
                                        [--run-scenario RUN_SCENARIO]
                                        [--table [TABLE]] [--no-table]
                                        [--kwargs [KWARGS ...]]
                                        [--kwargs-json KWARGS_JSON]
                                        [--metric METRIC]
                                        [--passband PASSBAND]
                                        [--bin-label BIN_LABEL]
                                        [--component COMPONENT]
                                        [--components COMPONENTS]
                                        [--model MODEL]
                                        [--value-col VALUE_COL]
                                        [--score-col SCORE_COL]
                                        [--x-col X_COL] [--y-col Y_COL]
                                        [--group-col GROUP_COL]
                                        [--color-col COLOR_COL] [--fit FIT]
                                        [--connect-points | --no-connect-points]
                                        [--mode MODE] [--dep DEP]
                                        [--indep INDEP] [--colorby COLORBY]
                                        [--compare-to COMPARE_TO]
                                        [--station-region STATION_REGIONS]
                                        [--event-region EVENT_REGIONS]
                                        [--scale SCALE]
                                        [--time-limit-s TIME_LIMIT_S]
                                        [--max-records MAX_RECORDS]
                                        [--max-traces MAX_TRACES]
                                        [--title TITLE] [--write-sidecar]
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
   * - ``--input``, ``--input-table``
     - No
     -
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'metric_map_by_model' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Value: ``table``. Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
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
   * - ``--bin-label``
     - No
     -
     - Value: ``bin_label``. Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Value: ``components``. Component list for waveform plots that use a components argument. Repeat for multiple components.
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
   * - ``--dep``
     - No
     - Repeatable
     - Value: ``dep``. Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Value: ``indep``. Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Value: ``colorby``. Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Value: ``compare_to``. Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Value: ``station_regions``. Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Value: ``event_regions``. Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Value: ``scale``. Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Value: ``time_limit_s``. Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Value: ``max_records``. Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Value: ``max_traces``. Maximum number of traces for waveform map figures.
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
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
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

   svtk map spatial model-improvement [-h] [--input PATH] [--output PATH]
                                          [--config CONFIG]
                                          [--run-scenario RUN_SCENARIO]
                                          [--table [TABLE]] [--no-table]
                                          [--kwargs [KWARGS ...]]
                                          [--kwargs-json KWARGS_JSON]
                                          [--metric METRIC]
                                          [--passband PASSBAND]
                                          [--bin-label BIN_LABEL]
                                          [--component COMPONENT]
                                          [--components COMPONENTS]
                                          [--model MODEL]
                                          [--value-col VALUE_COL]
                                          [--score-col SCORE_COL]
                                          [--x-col X_COL] [--y-col Y_COL]
                                          [--group-col GROUP_COL]
                                          [--color-col COLOR_COL] [--fit FIT]
                                          [--connect-points | --no-connect-points]
                                          [--mode MODE] [--dep DEP]
                                          [--indep INDEP] [--colorby COLORBY]
                                          [--compare-to COMPARE_TO]
                                          [--station-region STATION_REGIONS]
                                          [--event-region EVENT_REGIONS]
                                          [--scale SCALE]
                                          [--time-limit-s TIME_LIMIT_S]
                                          [--max-records MAX_RECORDS]
                                          [--max-traces MAX_TRACES]
                                          [--title TITLE] [--write-sidecar]
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
   * - ``--input``, ``--input-table``
     - No
     -
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'model_improvement' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Value: ``table``. Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
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
   * - ``--bin-label``
     - No
     -
     - Value: ``bin_label``. Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Value: ``components``. Component list for waveform plots that use a components argument. Repeat for multiple components.
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
   * - ``--dep``
     - No
     - Repeatable
     - Value: ``dep``. Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Value: ``indep``. Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Value: ``colorby``. Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Value: ``compare_to``. Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Value: ``station_regions``. Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Value: ``event_regions``. Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Value: ``scale``. Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Value: ``time_limit_s``. Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Value: ``max_records``. Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Value: ``max_traces``. Maximum number of traces for waveform map figures.
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
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
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

   svtk map spatial pca-mode [-h] [--input PATH] [--output PATH]
                                 [--config CONFIG]
                                 [--run-scenario RUN_SCENARIO]
                                 [--table [TABLE]] [--no-table]
                                 [--kwargs [KWARGS ...]]
                                 [--kwargs-json KWARGS_JSON] [--metric METRIC]
                                 [--passband PASSBAND] [--bin-label BIN_LABEL]
                                 [--component COMPONENT]
                                 [--components COMPONENTS] [--model MODEL]
                                 [--value-col VALUE_COL]
                                 [--score-col SCORE_COL] [--x-col X_COL]
                                 [--y-col Y_COL] [--group-col GROUP_COL]
                                 [--color-col COLOR_COL] [--fit FIT]
                                 [--connect-points | --no-connect-points]
                                 [--mode MODE] [--dep DEP] [--indep INDEP]
                                 [--colorby COLORBY] [--compare-to COMPARE_TO]
                                 [--station-region STATION_REGIONS]
                                 [--event-region EVENT_REGIONS]
                                 [--scale SCALE] [--time-limit-s TIME_LIMIT_S]
                                 [--max-records MAX_RECORDS]
                                 [--max-traces MAX_TRACES] [--title TITLE]
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
   * - ``--input``, ``--input-table``
     - No
     -
     - Filesystem path. Primary figure input table (pca station scores); accepts CSV or parquet. Defaults to configured output table 'pca_station_scores' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'pca_mode_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Value: ``table``. Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
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
   * - ``--bin-label``
     - No
     -
     - Value: ``bin_label``. Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Value: ``components``. Component list for waveform plots that use a components argument. Repeat for multiple components.
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
   * - ``--dep``
     - No
     - Repeatable
     - Value: ``dep``. Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Value: ``indep``. Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Value: ``colorby``. Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Value: ``compare_to``. Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Value: ``station_regions``. Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Value: ``event_regions``. Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Value: ``scale``. Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Value: ``time_limit_s``. Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Value: ``max_records``. Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Value: ``max_traces``. Maximum number of traces for waveform map figures.
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
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
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

   svtk map spatial redcap-cluster [-h] [--input PATH] [--output PATH]
                                       [--config CONFIG]
                                       [--run-scenario RUN_SCENARIO]
                                       [--table [TABLE]] [--no-table]
                                       [--kwargs [KWARGS ...]]
                                       [--kwargs-json KWARGS_JSON]
                                       [--metric METRIC] [--passband PASSBAND]
                                       [--bin-label BIN_LABEL]
                                       [--component COMPONENT]
                                       [--components COMPONENTS]
                                       [--model MODEL] [--value-col VALUE_COL]
                                       [--score-col SCORE_COL] [--x-col X_COL]
                                       [--y-col Y_COL] [--group-col GROUP_COL]
                                       [--color-col COLOR_COL] [--fit FIT]
                                       [--connect-points | --no-connect-points]
                                       [--mode MODE] [--dep DEP]
                                       [--indep INDEP] [--colorby COLORBY]
                                       [--compare-to COMPARE_TO]
                                       [--station-region STATION_REGIONS]
                                       [--event-region EVENT_REGIONS]
                                       [--scale SCALE]
                                       [--time-limit-s TIME_LIMIT_S]
                                       [--max-records MAX_RECORDS]
                                       [--max-traces MAX_TRACES]
                                       [--title TITLE] [--write-sidecar]
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
   * - ``--input``, ``--input-table``
     - No
     -
     - Filesystem path. Primary figure input table (redcap clusters); accepts CSV or parquet. Defaults to configured output table 'redcap_clusters' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'redcap_cluster_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Value: ``table``. Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
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
   * - ``--bin-label``
     - No
     -
     - Value: ``bin_label``. Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Value: ``components``. Component list for waveform plots that use a components argument. Repeat for multiple components.
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
   * - ``--dep``
     - No
     - Repeatable
     - Value: ``dep``. Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Value: ``indep``. Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Value: ``colorby``. Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Value: ``compare_to``. Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Value: ``station_regions``. Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Value: ``event_regions``. Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Value: ``scale``. Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Value: ``time_limit_s``. Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Value: ``max_records``. Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Value: ``max_traces``. Maximum number of traces for waveform map figures.
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
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
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

   svtk map spatial residual-grid [-h] [--input PATH] [--output PATH]
                                      [--config CONFIG]
                                      [--run-scenario RUN_SCENARIO]
                                      [--table [TABLE]] [--no-table]
                                      [--kwargs [KWARGS ...]]
                                      [--kwargs-json KWARGS_JSON]
                                      [--metric METRIC] [--passband PASSBAND]
                                      [--bin-label BIN_LABEL]
                                      [--component COMPONENT]
                                      [--components COMPONENTS]
                                      [--model MODEL] [--value-col VALUE_COL]
                                      [--score-col SCORE_COL] [--x-col X_COL]
                                      [--y-col Y_COL] [--group-col GROUP_COL]
                                      [--color-col COLOR_COL] [--fit FIT]
                                      [--connect-points | --no-connect-points]
                                      [--mode MODE] [--dep DEP]
                                      [--indep INDEP] [--colorby COLORBY]
                                      [--compare-to COMPARE_TO]
                                      [--station-region STATION_REGIONS]
                                      [--event-region EVENT_REGIONS]
                                      [--scale SCALE]
                                      [--time-limit-s TIME_LIMIT_S]
                                      [--max-records MAX_RECORDS]
                                      [--max-traces MAX_TRACES]
                                      [--title TITLE] [--write-sidecar]
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
   * - ``--input``, ``--input-table``
     - No
     -
     - Filesystem path. Primary figure input table (metric field); accepts CSV or parquet. Defaults to configured output table 'metric_field' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'residual_grid' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Value: ``table``. Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
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
   * - ``--bin-label``
     - No
     -
     - Value: ``bin_label``. Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Value: ``components``. Component list for waveform plots that use a components argument. Repeat for multiple components.
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
   * - ``--dep``
     - No
     - Repeatable
     - Value: ``dep``. Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Value: ``indep``. Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Value: ``colorby``. Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Value: ``compare_to``. Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Value: ``station_regions``. Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Value: ``event_regions``. Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Value: ``scale``. Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Value: ``time_limit_s``. Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Value: ``max_records``. Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Value: ``max_traces``. Maximum number of traces for waveform map figures.
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
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
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

   svtk map spatial score [-h] [--input PATH] [--output PATH]
                              [--config CONFIG] [--run-scenario RUN_SCENARIO]
                              [--table [TABLE]] [--no-table]
                              [--kwargs [KWARGS ...]]
                              [--kwargs-json KWARGS_JSON] [--metric METRIC]
                              [--passband PASSBAND] [--bin-label BIN_LABEL]
                              [--component COMPONENT]
                              [--components COMPONENTS] [--model MODEL]
                              [--value-col VALUE_COL] [--score-col SCORE_COL]
                              [--x-col X_COL] [--y-col Y_COL]
                              [--group-col GROUP_COL] [--color-col COLOR_COL]
                              [--fit FIT]
                              [--connect-points | --no-connect-points]
                              [--mode MODE] [--dep DEP] [--indep INDEP]
                              [--colorby COLORBY] [--compare-to COMPARE_TO]
                              [--station-region STATION_REGIONS]
                              [--event-region EVENT_REGIONS] [--scale SCALE]
                              [--time-limit-s TIME_LIMIT_S]
                              [--max-records MAX_RECORDS]
                              [--max-traces MAX_TRACES] [--title TITLE]
                              [--write-sidecar] [--sidecar-rows SIDECAR_ROWS]
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
   * - ``--input``, ``--input-table``
     - No
     -
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'score' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Value: ``table``. Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
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
   * - ``--bin-label``
     - No
     -
     - Value: ``bin_label``. Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Value: ``components``. Component list for waveform plots that use a components argument. Repeat for multiple components.
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
   * - ``--dep``
     - No
     - Repeatable
     - Value: ``dep``. Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Value: ``indep``. Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Value: ``colorby``. Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Value: ``compare_to``. Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Value: ``station_regions``. Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Value: ``event_regions``. Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Value: ``scale``. Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Value: ``time_limit_s``. Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Value: ``max_records``. Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Value: ``max_traces``. Maximum number of traces for waveform map figures.
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
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
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

   svtk map spatial station-bias [-h] [--input PATH] [--output PATH]
                                     [--config CONFIG]
                                     [--run-scenario RUN_SCENARIO]
                                     [--table [TABLE]] [--no-table]
                                     [--kwargs [KWARGS ...]]
                                     [--kwargs-json KWARGS_JSON]
                                     [--metric METRIC] [--passband PASSBAND]
                                     [--bin-label BIN_LABEL]
                                     [--component COMPONENT]
                                     [--components COMPONENTS] [--model MODEL]
                                     [--value-col VALUE_COL]
                                     [--score-col SCORE_COL] [--x-col X_COL]
                                     [--y-col Y_COL] [--group-col GROUP_COL]
                                     [--color-col COLOR_COL] [--fit FIT]
                                     [--connect-points | --no-connect-points]
                                     [--mode MODE] [--dep DEP] [--indep INDEP]
                                     [--colorby COLORBY]
                                     [--compare-to COMPARE_TO]
                                     [--station-region STATION_REGIONS]
                                     [--event-region EVENT_REGIONS]
                                     [--scale SCALE]
                                     [--time-limit-s TIME_LIMIT_S]
                                     [--max-records MAX_RECORDS]
                                     [--max-traces MAX_TRACES] [--title TITLE]
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
   * - ``--input``, ``--input-table``
     - No
     -
     - Filesystem path. Primary figure input table (station bias); accepts CSV or parquet. Defaults to configured output table 'station_bias' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'station_residual_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Value: ``table``. Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
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
   * - ``--bin-label``
     - No
     -
     - Value: ``bin_label``. Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Value: ``components``. Component list for waveform plots that use a components argument. Repeat for multiple components.
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
   * - ``--dep``
     - No
     - Repeatable
     - Value: ``dep``. Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Value: ``indep``. Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Value: ``colorby``. Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Value: ``compare_to``. Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Value: ``station_regions``. Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Value: ``event_regions``. Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Value: ``scale``. Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Value: ``time_limit_s``. Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Value: ``max_records``. Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Value: ``max_traces``. Maximum number of traces for waveform map figures.
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
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
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

   svtk map spatial station-metric [-h] [--input PATH] [--output PATH]
                                       [--config CONFIG]
                                       [--run-scenario RUN_SCENARIO]
                                       [--table [TABLE]] [--no-table]
                                       [--kwargs [KWARGS ...]]
                                       [--kwargs-json KWARGS_JSON]
                                       [--metric METRIC] [--passband PASSBAND]
                                       [--bin-label BIN_LABEL]
                                       [--component COMPONENT]
                                       [--components COMPONENTS]
                                       [--model MODEL] [--value-col VALUE_COL]
                                       [--score-col SCORE_COL] [--x-col X_COL]
                                       [--y-col Y_COL] [--group-col GROUP_COL]
                                       [--color-col COLOR_COL] [--fit FIT]
                                       [--connect-points | --no-connect-points]
                                       [--mode MODE] [--dep DEP]
                                       [--indep INDEP] [--colorby COLORBY]
                                       [--compare-to COMPARE_TO]
                                       [--station-region STATION_REGIONS]
                                       [--event-region EVENT_REGIONS]
                                       [--scale SCALE]
                                       [--time-limit-s TIME_LIMIT_S]
                                       [--max-records MAX_RECORDS]
                                       [--max-traces MAX_TRACES]
                                       [--title TITLE] [--write-sidecar]
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
   * - ``--input``, ``--input-table``
     - No
     -
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'station_metric_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Value: ``table``. Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
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
   * - ``--bin-label``
     - No
     -
     - Value: ``bin_label``. Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``component``. Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Value: ``components``. Component list for waveform plots that use a components argument. Repeat for multiple components.
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
   * - ``--dep``
     - No
     - Repeatable
     - Value: ``dep``. Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Value: ``indep``. Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Value: ``colorby``. Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Value: ``compare_to``. Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Value: ``station_regions``. Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Value: ``event_regions``. Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Value: ``scale``. Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Value: ``time_limit_s``. Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Value: ``max_records``. Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Value: ``max_traces``. Maximum number of traces for waveform map figures.
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
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
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
