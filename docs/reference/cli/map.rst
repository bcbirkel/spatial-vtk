.. _cli-svtk-map:

svtk map
========

Config-Backed Mapping
----------------------

If a config is active with ``svtk config set`` or passed with ``--config``, registered map commands resolve their standard input tables, figure outputs, and named map bounds automatically. For routine workflow maps, prefer the curated flags shown below instead of passing legacy ``--input`` and ``--output`` paths.

.. code-block:: bash

   svtk config set data/examples/configuration/example_spatial_vtk_config.yaml
   svtk map spatial station-metric --value-col log2_residual --metric PGA --passband "2-3 sec"
   svtk map spatial event-residual --value-col log2_residual --metric PGA --bounds study_area

These commands use configured outputs such as ``metrics_long`` and ``path_table`` plus the registered figure keys for the selected map unless you supply ``--input-table``/``--input`` or ``--figure-output``/``--output`` explicitly. Run ``svtk map spatial list`` to print a table showing each map command's input and output source, including ``config:<key>`` defaults and ``required:<role>`` entries. Add ``--resolve-paths --config PATH`` to show the concrete configured files.

Basemaps are enabled by default for map figures; use ``--no-basemap`` only when you explicitly want a data-only map.

Command Tree
------------

- :ref:`svtk map <cli-svtk-map>`
   - :ref:`svtk map spatial <cli-svtk-map-spatial>`
      - :ref:`svtk map spatial block-holdout-error <cli-svtk-map-spatial-block-holdout-error>` - Map block-holdout prediction errors.
      - :ref:`svtk map spatial cluster <cli-svtk-map-spatial-cluster>` - Map cluster assignments.
      - :ref:`svtk map spatial corridor <cli-svtk-map-spatial-corridor>` - Map corridor selections.
      - :ref:`svtk map spatial event-residual <cli-svtk-map-spatial-event-residual>` - Map event residual paths.
      - :ref:`svtk map spatial list <cli-svtk-map-spatial-list>`
      - :ref:`svtk map spatial metric-by-model <cli-svtk-map-spatial-metric-by-model>` - Map metric values by model.
      - :ref:`svtk map spatial model-improvement <cli-svtk-map-spatial-model-improvement>` - Map model improvement values.
      - :ref:`svtk map spatial pca-mode <cli-svtk-map-spatial-pca-mode>` - Map one PCA spatial mode.
      - :ref:`svtk map spatial redcap-cluster <cli-svtk-map-spatial-redcap-cluster>` - Map REDCAP cluster values.
      - :ref:`svtk map spatial residual-grid <cli-svtk-map-spatial-residual-grid>` - Map residual grid values.
      - :ref:`svtk map spatial score <cli-svtk-map-spatial-score>` - Map score values.
      - :ref:`svtk map spatial station-bias <cli-svtk-map-spatial-station-bias>` - Map station bias values.
      - :ref:`svtk map spatial station-metric <cli-svtk-map-spatial-station-metric>` - Map station metric values.

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

Map block-holdout prediction errors.

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial block-holdout-error [-h] [--input-table PATH]
                                            [--figure-output PATH]
                                            [--config PATH]
                                            [--run-scenario RUN_SCENARIO]
                                            [--table [ARG=PATH]] [--no-table]
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
                                            [--sidecar-dir DIR]
                                            [--bounds BOUNDS] [--no-basemap]
                                            [--basemap-source BASEMAP_SOURCE]

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:block_holdout_predictions``
     - Uses configured output table ``block_holdout_predictions`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:block_holdout_error``
     - Uses configured figure output ``block_holdout_error`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
   * - ``--input-table``, ``--input``
     - No
     -
     - Filesystem path. Primary figure input table (block holdout predictions); accepts CSV or parquet. Defaults to configured output table 'block_holdout_predictions' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'block_holdout_error' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --event-table, --station-table, --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Passband filter/value. Repeat for multiple passbands.
   * - ``--bin-label``
     - No
     -
     - Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Component list for waveform plots that use a components argument. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Column containing the numeric value for distribution or score-style plots, such as log2_residual or a GOF score.
   * - ``--x-col``
     - No
     -
     - Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Mode selector for figures that support named modes, such as PCA maps.
   * - ``--dep``
     - No
     - Repeatable
     - Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Maximum number of traces for waveform map figures.
   * - ``--title``
     - No
     -
     - Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Optional contextily basemap source.

.. _cli-svtk-map-spatial-cluster:

svtk map spatial cluster
""""""""""""""""""""""""

Map cluster assignments.

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial cluster [-h] [--input-table PATH]
                                [--figure-output PATH] [--config PATH]
                                [--run-scenario RUN_SCENARIO]
                                [--table [ARG=PATH]] [--no-table]
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
                                [--sidecar-dir DIR] [--bounds BOUNDS]
                                [--no-basemap]
                                [--basemap-source BASEMAP_SOURCE]

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:clusters``
     - Uses configured output table ``clusters`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:cluster``
     - Uses configured figure output ``cluster`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
   * - ``--input-table``, ``--input``
     - No
     -
     - Filesystem path. Primary figure input table (clusters); accepts CSV or parquet. Defaults to configured output table 'clusters' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'cluster' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --event-table, --station-table, --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Passband filter/value. Repeat for multiple passbands.
   * - ``--bin-label``
     - No
     -
     - Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Component list for waveform plots that use a components argument. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Column containing the numeric value for distribution or score-style plots, such as log2_residual or a GOF score.
   * - ``--x-col``
     - No
     -
     - Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Mode selector for figures that support named modes, such as PCA maps.
   * - ``--dep``
     - No
     - Repeatable
     - Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Maximum number of traces for waveform map figures.
   * - ``--title``
     - No
     -
     - Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Optional contextily basemap source.

.. _cli-svtk-map-spatial-corridor:

svtk map spatial corridor
"""""""""""""""""""""""""

Map corridor selections.

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial corridor [-h] [--input-table PATH]
                                 [--figure-output PATH] [--config PATH]
                                 [--run-scenario RUN_SCENARIO]
                                 [--table [ARG=PATH]] [--no-table]
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
                                 [--sidecar-dir DIR] [--events PATH]
                                 [--records PATH] [--stations PATH]
                                 [--bounds BOUNDS] [--no-basemap]
                                 [--basemap-source BASEMAP_SOURCE]

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:corridors``
     - Uses configured output table ``corridors`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:corridor_map``
     - Uses configured figure output ``corridor_map`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.
   * - Extra tables
     - ``--events(events_df)=config:prepared_events, --records(records_df)=config:event_station_records, --stations(stations_df)=config:prepared_stations``
     - Uses configured table defaults for ``--events``, ``--records``, ``--stations`` when a config is active; override with the same named flags.

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
   * - ``--input-table``, ``--input``
     - No
     -
     - Filesystem path. Primary figure input table (corridors); accepts CSV or parquet. Defaults to configured output table 'corridors' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'corridor_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --event-table, --station-table, --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Passband filter/value. Repeat for multiple passbands.
   * - ``--bin-label``
     - No
     -
     - Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Component list for waveform plots that use a components argument. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Column containing the numeric value for distribution or score-style plots, such as log2_residual or a GOF score.
   * - ``--x-col``
     - No
     -
     - Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Mode selector for figures that support named modes, such as PCA maps.
   * - ``--dep``
     - No
     - Repeatable
     - Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Maximum number of traces for waveform map figures.
   * - ``--title``
     - No
     -
     - Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Maximum rows to write to each sidecar. Omit to write all rows.
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
     - Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Optional contextily basemap source.

.. _cli-svtk-map-spatial-event-residual:

svtk map spatial event-residual
"""""""""""""""""""""""""""""""

Map event residual paths.

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial event-residual [-h] [--input-table PATH]
                                       [--figure-output PATH] [--config PATH]
                                       [--run-scenario RUN_SCENARIO]
                                       [--table [ARG=PATH]] [--no-table]
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
                                       [--sidecar-dir DIR] [--bounds BOUNDS]
                                       [--no-basemap]
                                       [--basemap-source BASEMAP_SOURCE]

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:path_table``
     - Uses configured output table ``path_table`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:event_residual_map``
     - Uses configured figure output ``event_residual_map`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
   * - ``--input-table``, ``--input``
     - No
     -
     - Filesystem path. Primary figure input table (path); accepts CSV or parquet. Defaults to configured output table 'path_table' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'event_residual_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --event-table, --station-table, --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Passband filter/value. Repeat for multiple passbands.
   * - ``--bin-label``
     - No
     -
     - Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Component list for waveform plots that use a components argument. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Column containing the numeric value for distribution or score-style plots, such as log2_residual or a GOF score.
   * - ``--x-col``
     - No
     -
     - Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Mode selector for figures that support named modes, such as PCA maps.
   * - ``--dep``
     - No
     - Repeatable
     - Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Maximum number of traces for waveform map figures.
   * - ``--title``
     - No
     -
     - Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Optional contextily basemap source.

.. _cli-svtk-map-spatial-list:

svtk map spatial list
"""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial list [-h] [--config PATH]
                             [--run-scenario RUN_SCENARIO] [--resolve-paths]

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
     - Filesystem path. Optional Spatial-VTK config used with --resolve-paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay when resolving paths.
   * - ``--resolve-paths``
     - No
     - Flag
     - Resolve config-backed input, output, and extra-table keys to concrete paths.

.. _cli-svtk-map-spatial-metric-by-model:

svtk map spatial metric-by-model
""""""""""""""""""""""""""""""""

Map metric values by model.

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial metric-by-model [-h] [--input-table PATH]
                                        [--figure-output PATH] [--config PATH]
                                        [--run-scenario RUN_SCENARIO]
                                        [--table [ARG=PATH]] [--no-table]
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
                                        [--sidecar-dir DIR] [--bounds BOUNDS]
                                        [--no-basemap]
                                        [--basemap-source BASEMAP_SOURCE]

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:metrics_long``
     - Uses configured output table ``metrics_long`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:metric_map_by_model``
     - Uses configured figure output ``metric_map_by_model`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
   * - ``--input-table``, ``--input``
     - No
     -
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'metric_map_by_model' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --event-table, --station-table, --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Passband filter/value. Repeat for multiple passbands.
   * - ``--bin-label``
     - No
     -
     - Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Component list for waveform plots that use a components argument. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Column containing the numeric value for distribution or score-style plots, such as log2_residual or a GOF score.
   * - ``--x-col``
     - No
     -
     - Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Mode selector for figures that support named modes, such as PCA maps.
   * - ``--dep``
     - No
     - Repeatable
     - Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Maximum number of traces for waveform map figures.
   * - ``--title``
     - No
     -
     - Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Optional contextily basemap source.

.. _cli-svtk-map-spatial-model-improvement:

svtk map spatial model-improvement
""""""""""""""""""""""""""""""""""

Map model improvement values.

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial model-improvement [-h] [--input-table PATH]
                                          [--figure-output PATH]
                                          [--config PATH]
                                          [--run-scenario RUN_SCENARIO]
                                          [--table [ARG=PATH]] [--no-table]
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
                                          [--sidecar-dir DIR]
                                          [--bounds BOUNDS] [--no-basemap]
                                          [--basemap-source BASEMAP_SOURCE]

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:metrics_long``
     - Uses configured output table ``metrics_long`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:model_improvement``
     - Uses configured figure output ``model_improvement`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
   * - ``--input-table``, ``--input``
     - No
     -
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'model_improvement' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --event-table, --station-table, --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Passband filter/value. Repeat for multiple passbands.
   * - ``--bin-label``
     - No
     -
     - Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Component list for waveform plots that use a components argument. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Column containing the numeric value for distribution or score-style plots, such as log2_residual or a GOF score.
   * - ``--x-col``
     - No
     -
     - Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Mode selector for figures that support named modes, such as PCA maps.
   * - ``--dep``
     - No
     - Repeatable
     - Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Maximum number of traces for waveform map figures.
   * - ``--title``
     - No
     -
     - Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Optional contextily basemap source.

.. _cli-svtk-map-spatial-pca-mode:

svtk map spatial pca-mode
"""""""""""""""""""""""""

Map one PCA spatial mode.

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial pca-mode [-h] [--input-table PATH]
                                 [--figure-output PATH] [--config PATH]
                                 [--run-scenario RUN_SCENARIO]
                                 [--table [ARG=PATH]] [--no-table]
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
                                 [--sidecar-dir DIR] [--bounds BOUNDS]
                                 [--no-basemap]
                                 [--basemap-source BASEMAP_SOURCE]

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:pca_station_scores``
     - Uses configured output table ``pca_station_scores`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:pca_mode_map``
     - Uses configured figure output ``pca_mode_map`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
   * - ``--input-table``, ``--input``
     - No
     -
     - Filesystem path. Primary figure input table (pca station scores); accepts CSV or parquet. Defaults to configured output table 'pca_station_scores' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'pca_mode_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --event-table, --station-table, --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Passband filter/value. Repeat for multiple passbands.
   * - ``--bin-label``
     - No
     -
     - Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Component list for waveform plots that use a components argument. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Column containing the numeric value for distribution or score-style plots, such as log2_residual or a GOF score.
   * - ``--x-col``
     - No
     -
     - Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Mode selector for figures that support named modes, such as PCA maps.
   * - ``--dep``
     - No
     - Repeatable
     - Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Maximum number of traces for waveform map figures.
   * - ``--title``
     - No
     -
     - Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Optional contextily basemap source.

.. _cli-svtk-map-spatial-redcap-cluster:

svtk map spatial redcap-cluster
"""""""""""""""""""""""""""""""

Map REDCAP cluster values.

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial redcap-cluster [-h] [--input-table PATH]
                                       [--figure-output PATH] [--config PATH]
                                       [--run-scenario RUN_SCENARIO]
                                       [--table [ARG=PATH]] [--no-table]
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
                                       [--sidecar-dir DIR] [--bounds BOUNDS]
                                       [--no-basemap]
                                       [--basemap-source BASEMAP_SOURCE]

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:redcap_clusters``
     - Uses configured output table ``redcap_clusters`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:redcap_cluster_map``
     - Uses configured figure output ``redcap_cluster_map`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
   * - ``--input-table``, ``--input``
     - No
     -
     - Filesystem path. Primary figure input table (redcap clusters); accepts CSV or parquet. Defaults to configured output table 'redcap_clusters' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'redcap_cluster_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --event-table, --station-table, --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Passband filter/value. Repeat for multiple passbands.
   * - ``--bin-label``
     - No
     -
     - Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Component list for waveform plots that use a components argument. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Column containing the numeric value for distribution or score-style plots, such as log2_residual or a GOF score.
   * - ``--x-col``
     - No
     -
     - Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Mode selector for figures that support named modes, such as PCA maps.
   * - ``--dep``
     - No
     - Repeatable
     - Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Maximum number of traces for waveform map figures.
   * - ``--title``
     - No
     -
     - Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Optional contextily basemap source.

.. _cli-svtk-map-spatial-residual-grid:

svtk map spatial residual-grid
""""""""""""""""""""""""""""""

Map residual grid values.

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial residual-grid [-h] [--input-table PATH]
                                      [--figure-output PATH] [--config PATH]
                                      [--run-scenario RUN_SCENARIO]
                                      [--table [ARG=PATH]] [--no-table]
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
                                      [--sidecar-dir DIR] [--bounds BOUNDS]
                                      [--no-basemap]
                                      [--basemap-source BASEMAP_SOURCE]

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:metric_field``
     - Uses configured output table ``metric_field`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:residual_grid``
     - Uses configured figure output ``residual_grid`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
   * - ``--input-table``, ``--input``
     - No
     -
     - Filesystem path. Primary figure input table (metric field); accepts CSV or parquet. Defaults to configured output table 'metric_field' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'residual_grid' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --event-table, --station-table, --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Passband filter/value. Repeat for multiple passbands.
   * - ``--bin-label``
     - No
     -
     - Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Component list for waveform plots that use a components argument. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Column containing the numeric value for distribution or score-style plots, such as log2_residual or a GOF score.
   * - ``--x-col``
     - No
     -
     - Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Mode selector for figures that support named modes, such as PCA maps.
   * - ``--dep``
     - No
     - Repeatable
     - Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Maximum number of traces for waveform map figures.
   * - ``--title``
     - No
     -
     - Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Optional contextily basemap source.

.. _cli-svtk-map-spatial-score:

svtk map spatial score
""""""""""""""""""""""

Map score values.

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial score [-h] [--input-table PATH] [--figure-output PATH]
                              [--config PATH] [--run-scenario RUN_SCENARIO]
                              [--table [ARG=PATH]] [--no-table]
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
                              [--sidecar-dir DIR] [--bounds BOUNDS]
                              [--no-basemap] [--basemap-source BASEMAP_SOURCE]

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:metrics_long``
     - Uses configured output table ``metrics_long`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:score``
     - Uses configured figure output ``score`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
   * - ``--input-table``, ``--input``
     - No
     -
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'score' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --event-table, --station-table, --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Passband filter/value. Repeat for multiple passbands.
   * - ``--bin-label``
     - No
     -
     - Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Component list for waveform plots that use a components argument. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Column containing the numeric value for distribution or score-style plots, such as log2_residual or a GOF score.
   * - ``--x-col``
     - No
     -
     - Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Mode selector for figures that support named modes, such as PCA maps.
   * - ``--dep``
     - No
     - Repeatable
     - Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Maximum number of traces for waveform map figures.
   * - ``--title``
     - No
     -
     - Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Optional contextily basemap source.

.. _cli-svtk-map-spatial-station-bias:

svtk map spatial station-bias
"""""""""""""""""""""""""""""

Map station bias values.

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial station-bias [-h] [--input-table PATH]
                                     [--figure-output PATH] [--config PATH]
                                     [--run-scenario RUN_SCENARIO]
                                     [--table [ARG=PATH]] [--no-table]
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
                                     [--sidecar-dir DIR] [--bounds BOUNDS]
                                     [--no-basemap]
                                     [--basemap-source BASEMAP_SOURCE]

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:station_bias``
     - Uses configured output table ``station_bias`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:station_residual_map``
     - Uses configured figure output ``station_residual_map`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
   * - ``--input-table``, ``--input``
     - No
     -
     - Filesystem path. Primary figure input table (station bias); accepts CSV or parquet. Defaults to configured output table 'station_bias' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'station_residual_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --event-table, --station-table, --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Passband filter/value. Repeat for multiple passbands.
   * - ``--bin-label``
     - No
     -
     - Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Component list for waveform plots that use a components argument. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Column containing the numeric value for distribution or score-style plots, such as log2_residual or a GOF score.
   * - ``--x-col``
     - No
     -
     - Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Mode selector for figures that support named modes, such as PCA maps.
   * - ``--dep``
     - No
     - Repeatable
     - Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Maximum number of traces for waveform map figures.
   * - ``--title``
     - No
     -
     - Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Optional contextily basemap source.

.. _cli-svtk-map-spatial-station-metric:

svtk map spatial station-metric
"""""""""""""""""""""""""""""""

Map station metric values.

.. rubric:: Usage

.. code-block:: bash

   svtk map spatial station-metric [-h] [--input-table PATH]
                                       [--figure-output PATH] [--config PATH]
                                       [--run-scenario RUN_SCENARIO]
                                       [--table [ARG=PATH]] [--no-table]
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
                                       [--sidecar-dir DIR] [--bounds BOUNDS]
                                       [--no-basemap]
                                       [--basemap-source BASEMAP_SOURCE]

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:metrics_long``
     - Uses configured output table ``metrics_long`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:station_metric_map``
     - Uses configured figure output ``station_metric_map`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
   * - ``--input-table``, ``--input``
     - No
     -
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'station_metric_map' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--config``
     - No
     -
     - Filesystem path. Optional Spatial-VTK config for default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.
   * - ``--table``
     - No
     - Nargs: ``?``; Repeatable
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --event-table, --station-table, --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
   * - ``--no-table``
     - No
     -
     - Disable a function-specific comparison/statistical table when supported.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Extra function keyword arguments as key=value.
   * - ``--kwargs-json``
     - No
     -
     - Extra function keyword arguments as a JSON/YAML mapping.
   * - ``--metric``
     - No
     -
     - Metric name passed to plotting functions that support metric filtering.
   * - ``--passband``
     - No
     - Repeatable
     - Passband filter/value. Repeat for multiple passbands.
   * - ``--bin-label``
     - No
     -
     - Pattern or period-bin label passed to plotting functions that require one.
   * - ``--component``
     - No
     - Repeatable
     - Component filter/value. Repeat for multiple components.
   * - ``--components``
     - No
     - Repeatable
     - Component list for waveform plots that use a components argument. Repeat for multiple components.
   * - ``--model``
     - No
     - Repeatable
     - Model filter/value. Repeat for multiple models.
   * - ``--value-col``
     - No
     -
     - Column containing the plotted value.
   * - ``--score-col``
     - No
     -
     - Column containing the numeric value for distribution or score-style plots, such as log2_residual or a GOF score.
   * - ``--x-col``
     - No
     -
     - Column used on the x axis.
   * - ``--y-col``
     - No
     -
     - Column used on the y axis.
   * - ``--group-col``
     - No
     -
     - Column used for grouping, coloring, or trend groups.
   * - ``--color-col``
     - No
     -
     - Column used to color plot groups.
   * - ``--fit``
     - No
     -
     - Optional fit/trend method, such as 'linear' or 'lowess'.
   * - ``--connect-points``, ``--no-connect-points``
     - No
     -
     - Connect sorted points for trend plots that support line-style rendering. Use --no-connect-points for scatter-only rendering.
   * - ``--mode``
     - No
     -
     - Mode selector for figures that support named modes, such as PCA maps.
   * - ``--dep``
     - No
     - Repeatable
     - Dependent metric or column for flexible spatial plots. Repeat for multiple metrics.
   * - ``--indep``
     - No
     -
     - Independent column for flexible spatial plots.
   * - ``--colorby``
     - No
     -
     - Column or alias used for flexible spatial plot color grouping.
   * - ``--compare-to``
     - No
     - Repeatable
     - Baseline category for categorical comparison plots. Repeat for multiple categories.
   * - ``--station-region``
     - No
     - Repeatable
     - Station region filter. Repeat for multiple regions.
   * - ``--event-region``
     - No
     - Repeatable
     - Event region filter. Repeat for multiple regions.
   * - ``--scale``
     - No
     -
     - Waveform plotting scale for record-section style figures.
   * - ``--time-limit-s``
     - No
     -
     - Upper time limit in seconds for waveform figures that support time_limit_s.
   * - ``--max-records``
     - No
     -
     - Maximum number of records for record-section style waveform figures.
   * - ``--max-traces``
     - No
     -
     - Maximum number of traces for waveform map figures.
   * - ``--title``
     - No
     -
     - Figure title.
   * - ``--write-sidecar``
     - No
     - Flag
     - Write CSV/JSON sidecars with rows used by the figure.
   * - ``--sidecar-rows``
     - No
     -
     - Maximum rows to write to each sidecar. Omit to write all rows.
   * - ``--sidecar-dir``
     - No
     -
     - Directory path. Directory for figure sidecars. Defaults next to the output figure.
   * - ``--bounds``
     - No
     -
     - Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.
   * - ``--no-basemap``
     - No
     - Flag
     - Disable basemap rendering for map figures.
   * - ``--basemap-source``
     - No
     -
     - Optional contextily basemap source.
