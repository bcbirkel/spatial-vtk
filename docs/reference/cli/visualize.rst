.. _cli-svtk-visualize:

svtk visualize
==============

Config-Backed Visualization
---------------------------

If a config is active with ``svtk config set`` or passed with ``--config``, registered visualization commands resolve their standard input tables and figure outputs automatically. For routine context, QC, and waveform figures, prefer the curated flags shown below instead of passing raw ``--input`` and ``--output`` paths.

.. code-block:: bash

   svtk config set data/examples/configuration/example_spatial_vtk_config.yaml
   svtk visualize qc retention-summary
   svtk visualize context station-event-context --bounds study_area
   svtk visualize waveforms observed-synthetic-record-section --components R --max-records 80

These commands use configured outputs such as ``qc_metric_pair_retention``, ``event_station_records``, and the registered figure keys for the selected visualization unless you supply ``--input``/``--input-table`` or ``--output``/``--figure-output`` explicitly. Run ``svtk visualize qc list``, ``svtk visualize context list``, or ``svtk visualize waveforms list`` to print a table showing each command's input and output source, including ``config:<key>`` defaults and ``required:<role>`` entries.

Use ``svtk visualize sidecars status`` to inspect figure provenance sidecars written by commands that support ``--write-sidecar``.

Command Tree
------------

- :ref:`svtk visualize <cli-svtk-visualize>`
   - :ref:`svtk visualize qc <cli-svtk-visualize-qc>`
      - :ref:`svtk visualize qc data-synthetic-availability <cli-svtk-visualize-qc-data-synthetic-availability>`
      - :ref:`svtk visualize qc drop-cause-diagnostics <cli-svtk-visualize-qc-drop-cause-diagnostics>`
      - :ref:`svtk visualize qc event-station-retention <cli-svtk-visualize-qc-event-station-retention>`
      - :ref:`svtk visualize qc list <cli-svtk-visualize-qc-list>`
      - :ref:`svtk visualize qc post-qc-station-event-map <cli-svtk-visualize-qc-post-qc-station-event-map>`
      - :ref:`svtk visualize qc retention-summary <cli-svtk-visualize-qc-retention-summary>`
      - :ref:`svtk visualize qc trace-inventory-samples <cli-svtk-visualize-qc-trace-inventory-samples>`
   - :ref:`svtk visualize context <cli-svtk-visualize-context>`
      - :ref:`svtk visualize context distance-amplitude-diagnostics <cli-svtk-visualize-context-distance-amplitude-diagnostics>`
      - :ref:`svtk visualize context event-coverage <cli-svtk-visualize-context-event-coverage>`
      - :ref:`svtk visualize context event-magnitude-map <cli-svtk-visualize-context-event-magnitude-map>`
      - :ref:`svtk visualize context event-trace-comparison <cli-svtk-visualize-context-event-trace-comparison>`
      - :ref:`svtk visualize context list <cli-svtk-visualize-context-list>`
      - :ref:`svtk visualize context record-coverage <cli-svtk-visualize-context-record-coverage>`
      - :ref:`svtk visualize context station-coverage <cli-svtk-visualize-context-station-coverage>`
      - :ref:`svtk visualize context station-event-beachball <cli-svtk-visualize-context-station-event-beachball>`
      - :ref:`svtk visualize context station-event-context <cli-svtk-visualize-context-station-event-context>`
      - :ref:`svtk visualize context station-event-network <cli-svtk-visualize-context-station-event-network>`
      - :ref:`svtk visualize context study-domain <cli-svtk-visualize-context-study-domain>`
   - :ref:`svtk visualize sidecars <cli-svtk-visualize-sidecars>`
      - :ref:`svtk visualize sidecars status <cli-svtk-visualize-sidecars-status>`
   - :ref:`svtk visualize waveforms <cli-svtk-visualize-waveforms>`
      - :ref:`svtk visualize waveforms event-radial-trace-section <cli-svtk-visualize-waveforms-event-radial-trace-section>`
      - :ref:`svtk visualize waveforms list <cli-svtk-visualize-waveforms-list>`
      - :ref:`svtk visualize waveforms observed-synthetic-record-section <cli-svtk-visualize-waveforms-observed-synthetic-record-section>`
      - :ref:`svtk visualize waveforms record-section <cli-svtk-visualize-waveforms-record-section>`
      - :ref:`svtk visualize waveforms station-event-waveform-map <cli-svtk-visualize-waveforms-station-event-waveform-map>`
      - :ref:`svtk visualize waveforms waveform-overlay-matrix <cli-svtk-visualize-waveforms-waveform-overlay-matrix>`

Command Details
---------------

.. rubric:: Usage

.. code-block:: bash

   svtk visualize [-h] {context,qc,waveforms,sidecars} ...

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

.. _cli-svtk-visualize-qc:

svtk visualize qc
^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk visualize qc [-h]
                         {list,data-synthetic-availability,drop-cause-diagnostics,event-station-retention,post-qc-station-event-map,retention-summary,trace-inventory-samples}
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

.. _cli-svtk-visualize-qc-data-synthetic-availability:

svtk visualize qc data-synthetic-availability
"""""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize qc data-synthetic-availability [-h] [--input PATH]
                                                     [--output PATH]
                                                     [--config PATH]
                                                     [--run-scenario RUN_SCENARIO]
                                                     [--table [ARG=PATH]]
                                                     [--no-table]
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
                                                     [--x-col X_COL]
                                                     [--y-col Y_COL]
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
                                                     [--title TITLE]
                                                     [--write-sidecar]
                                                     [--sidecar-rows SIDECAR_ROWS]
                                                     [--sidecar-dir DIR]
                                                     [--bounds BOUNDS]
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
     - Filesystem path. Primary figure input table (qc availability); accepts CSV or parquet. Defaults to configured output table 'qc_availability' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'data_synthetic_availability' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-qc-drop-cause-diagnostics:

svtk visualize qc drop-cause-diagnostics
""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize qc drop-cause-diagnostics [-h] [--input PATH]
                                                [--output PATH]
                                                [--config PATH]
                                                [--run-scenario RUN_SCENARIO]
                                                [--table [ARG=PATH]]
                                                [--no-table]
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
                                                [--x-col X_COL]
                                                [--y-col Y_COL]
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
                                                [--title TITLE]
                                                [--write-sidecar]
                                                [--sidecar-rows SIDECAR_ROWS]
                                                [--sidecar-dir DIR]
                                                [--bounds BOUNDS]
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
     - Filesystem path. Primary figure input table (qc drop causes); accepts CSV or parquet. Defaults to configured output table 'qc_drop_causes' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'drop_cause_diagnostics' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-qc-event-station-retention:

svtk visualize qc event-station-retention
"""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize qc event-station-retention [-h] [--input PATH]
                                                 [--output PATH]
                                                 [--config PATH]
                                                 [--run-scenario RUN_SCENARIO]
                                                 [--table [ARG=PATH]]
                                                 [--no-table]
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
                                                 [--x-col X_COL]
                                                 [--y-col Y_COL]
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
                                                 [--title TITLE]
                                                 [--write-sidecar]
                                                 [--sidecar-rows SIDECAR_ROWS]
                                                 [--sidecar-dir DIR]
                                                 [--bounds BOUNDS]
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
     - Filesystem path. Primary figure input table (qc event station pair retention); accepts CSV or parquet. Defaults to configured output table 'qc_event_station_pair_retention' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'event_station_retention' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-qc-list:

svtk visualize qc list
""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize qc list [-h]

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

.. _cli-svtk-visualize-qc-post-qc-station-event-map:

svtk visualize qc post-qc-station-event-map
"""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize qc post-qc-station-event-map [-h] [--input PATH]
                                                   [--output PATH]
                                                   [--config PATH]
                                                   [--run-scenario RUN_SCENARIO]
                                                   [--table [ARG=PATH]]
                                                   [--no-table]
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
                                                   [--x-col X_COL]
                                                   [--y-col Y_COL]
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
                                                   [--title TITLE]
                                                   [--write-sidecar]
                                                   [--sidecar-rows SIDECAR_ROWS]
                                                   [--sidecar-dir DIR]
                                                   [--bounds BOUNDS]
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
     - Filesystem path. Primary figure input table (post qc records); accepts CSV or parquet. Defaults to configured output table 'post_qc_records' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'post_qc_station_event_map' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-qc-retention-summary:

svtk visualize qc retention-summary
"""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize qc retention-summary [-h] [--input PATH] [--output PATH]
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
     - Filesystem path. Primary figure input table (qc metric pair retention); accepts CSV or parquet. Defaults to configured output table 'qc_metric_pair_retention' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'retention_summary' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-qc-trace-inventory-samples:

svtk visualize qc trace-inventory-samples
"""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize qc trace-inventory-samples [-h] [--input PATH]
                                                 [--output PATH]
                                                 [--config PATH]
                                                 [--run-scenario RUN_SCENARIO]
                                                 [--table [ARG=PATH]]
                                                 [--no-table]
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
                                                 [--x-col X_COL]
                                                 [--y-col Y_COL]
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
                                                 [--title TITLE]
                                                 [--write-sidecar]
                                                 [--sidecar-rows SIDECAR_ROWS]
                                                 [--sidecar-dir DIR]
                                                 [--bounds BOUNDS]
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
     - Filesystem path. Primary figure input table (sample); accepts CSV or parquet.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'trace_inventory_samples' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-context:

svtk visualize context
^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context [-h]
                              {list,distance-amplitude-diagnostics,event-coverage,event-magnitude-map,event-trace-comparison,record-coverage,station-coverage,station-event-beachball,station-event-context,station-event-network,study-domain}
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

.. _cli-svtk-visualize-context-distance-amplitude-diagnostics:

svtk visualize context distance-amplitude-diagnostics
"""""""""""""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context distance-amplitude-diagnostics
       [-h] [--input PATH] [--output PATH] [--config PATH]
       [--run-scenario RUN_SCENARIO] [--table [ARG=PATH]] [--no-table]
       [--kwargs [KWARGS ...]] [--kwargs-json KWARGS_JSON] [--metric METRIC]
       [--passband PASSBAND] [--bin-label BIN_LABEL] [--component COMPONENT]
       [--components COMPONENTS] [--model MODEL] [--value-col VALUE_COL]
       [--score-col SCORE_COL] [--x-col X_COL] [--y-col Y_COL]
       [--group-col GROUP_COL] [--color-col COLOR_COL] [--fit FIT]
       [--connect-points | --no-connect-points] [--mode MODE] [--dep DEP]
       [--indep INDEP] [--colorby COLORBY] [--compare-to COMPARE_TO]
       [--station-region STATION_REGIONS] [--event-region EVENT_REGIONS]
       [--scale SCALE] [--time-limit-s TIME_LIMIT_S]
       [--max-records MAX_RECORDS] [--max-traces MAX_TRACES] [--title TITLE]
       [--write-sidecar] [--sidecar-rows SIDECAR_ROWS] [--sidecar-dir DIR]
       [--bounds BOUNDS] [--no-basemap] [--basemap-source BASEMAP_SOURCE]

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
     - Filesystem path. Primary figure input table (event station records); accepts CSV or parquet. Defaults to configured output table 'event_station_records' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'distance_amplitude_diagnostics' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-context-event-coverage:

svtk visualize context event-coverage
"""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context event-coverage [-h] [--input PATH]
                                             [--output PATH] [--config PATH]
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
     - Filesystem path. Primary figure input table (event station records); accepts CSV or parquet. Defaults to configured output table 'event_station_records' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'event_coverage' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-context-event-magnitude-map:

svtk visualize context event-magnitude-map
""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context event-magnitude-map [-h] [--input PATH]
                                                  [--output PATH]
                                                  [--config PATH]
                                                  [--run-scenario RUN_SCENARIO]
                                                  [--table [ARG=PATH]]
                                                  [--no-table]
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
                                                  [--x-col X_COL]
                                                  [--y-col Y_COL]
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
                                                  [--title TITLE]
                                                  [--write-sidecar]
                                                  [--sidecar-rows SIDECAR_ROWS]
                                                  [--sidecar-dir DIR]
                                                  [--bounds BOUNDS]
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
     - Filesystem path. Primary figure input table (prepared events); accepts CSV or parquet. Defaults to configured output table 'prepared_events' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'event_magnitude_map' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-context-event-trace-comparison:

svtk visualize context event-trace-comparison
"""""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context event-trace-comparison [-h] [--input PATH]
                                                     [--output PATH]
                                                     [--config PATH]
                                                     [--run-scenario RUN_SCENARIO]
                                                     [--table [ARG=PATH]]
                                                     [--no-table]
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
                                                     [--x-col X_COL]
                                                     [--y-col Y_COL]
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
                                                     [--title TITLE]
                                                     [--write-sidecar]
                                                     [--sidecar-rows SIDECAR_ROWS]
                                                     [--sidecar-dir DIR]
                                                     [--bounds BOUNDS]
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
     - Filesystem path. Primary figure input table (event station records); accepts CSV or parquet. Defaults to configured output table 'event_station_records' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'event_trace_comparison' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-context-list:

svtk visualize context list
"""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context list [-h]

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

.. _cli-svtk-visualize-context-record-coverage:

svtk visualize context record-coverage
""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context record-coverage [-h] [--input PATH]
                                              [--output PATH] [--config PATH]
                                              [--run-scenario RUN_SCENARIO]
                                              [--table [ARG=PATH]]
                                              [--no-table]
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
                                              [--title TITLE]
                                              [--write-sidecar]
                                              [--sidecar-rows SIDECAR_ROWS]
                                              [--sidecar-dir DIR]
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
     - Filesystem path. Primary figure input table (record coverage); accepts CSV or parquet. Defaults to configured output table 'record_coverage' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'record_coverage' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-context-station-coverage:

svtk visualize context station-coverage
"""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context station-coverage [-h] [--input PATH]
                                               [--output PATH] [--config PATH]
                                               [--run-scenario RUN_SCENARIO]
                                               [--table [ARG=PATH]]
                                               [--no-table]
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
                                               [--title TITLE]
                                               [--write-sidecar]
                                               [--sidecar-rows SIDECAR_ROWS]
                                               [--sidecar-dir DIR]
                                               [--bounds BOUNDS]
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
     - Filesystem path. Primary figure input table (event station records); accepts CSV or parquet. Defaults to configured output table 'event_station_records' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'station_coverage' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-context-station-event-beachball:

svtk visualize context station-event-beachball
""""""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context station-event-beachball [-h] [--input PATH]
                                                      [--output PATH]
                                                      [--config PATH]
                                                      [--run-scenario RUN_SCENARIO]
                                                      [--table [ARG=PATH]]
                                                      [--no-table]
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
                                                      [--x-col X_COL]
                                                      [--y-col Y_COL]
                                                      [--group-col GROUP_COL]
                                                      [--color-col COLOR_COL]
                                                      [--fit FIT]
                                                      [--connect-points | --no-connect-points]
                                                      [--mode MODE]
                                                      [--dep DEP]
                                                      [--indep INDEP]
                                                      [--colorby COLORBY]
                                                      [--compare-to COMPARE_TO]
                                                      [--station-region STATION_REGIONS]
                                                      [--event-region EVENT_REGIONS]
                                                      [--scale SCALE]
                                                      [--time-limit-s TIME_LIMIT_S]
                                                      [--max-records MAX_RECORDS]
                                                      [--max-traces MAX_TRACES]
                                                      [--title TITLE]
                                                      [--write-sidecar]
                                                      [--sidecar-rows SIDECAR_ROWS]
                                                      [--sidecar-dir DIR]
                                                      [--stations PATH]
                                                      [--bounds BOUNDS]
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
     - Filesystem path. Primary figure input table (prepared events); accepts CSV or parquet. Defaults to configured output table 'prepared_events' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'station_event_beachball' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-context-station-event-context:

svtk visualize context station-event-context
""""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context station-event-context [-h] [--input PATH]
                                                    [--output PATH]
                                                    [--config PATH]
                                                    [--run-scenario RUN_SCENARIO]
                                                    [--table [ARG=PATH]]
                                                    [--no-table]
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
                                                    [--x-col X_COL]
                                                    [--y-col Y_COL]
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
                                                    [--title TITLE]
                                                    [--write-sidecar]
                                                    [--sidecar-rows SIDECAR_ROWS]
                                                    [--sidecar-dir DIR]
                                                    [--events PATH]
                                                    [--bounds BOUNDS]
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
     - Filesystem path. Primary figure input table (prepared stations); accepts CSV or parquet. Defaults to configured output table 'prepared_stations' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'station_event_context' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-context-station-event-network:

svtk visualize context station-event-network
""""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context station-event-network [-h] [--input PATH]
                                                    [--output PATH]
                                                    [--config PATH]
                                                    [--run-scenario RUN_SCENARIO]
                                                    [--table [ARG=PATH]]
                                                    [--no-table]
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
                                                    [--x-col X_COL]
                                                    [--y-col Y_COL]
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
                                                    [--title TITLE]
                                                    [--write-sidecar]
                                                    [--sidecar-rows SIDECAR_ROWS]
                                                    [--sidecar-dir DIR]
                                                    [--events PATH]
                                                    [--bounds BOUNDS]
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
     - Filesystem path. Primary figure input table (prepared stations); accepts CSV or parquet. Defaults to configured output table 'prepared_stations' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'station_event_network' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-context-study-domain:

svtk visualize context study-domain
"""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context study-domain [-h] [--input PATH] [--output PATH]
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
                                           [--sidecar-dir DIR] [--events PATH]
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
     - Filesystem path. Primary figure input table (prepared stations); accepts CSV or parquet. Defaults to configured output table 'prepared_stations' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'study_domain' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-sidecars:

svtk visualize sidecars
^^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk visualize sidecars [-h] {status} ...

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

.. _cli-svtk-visualize-sidecars-status:

svtk visualize sidecars status
""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize sidecars status [-h] --sidecar-dir DIR [--json]

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
   * - ``--sidecar-dir``, ``--sidecars-dir``
     - Yes
     -
     - Directory path. Directory containing figure sidecar JSON files.
   * - ``--json``
     - No
     - Flag
     - Print machine-readable JSON.

.. _cli-svtk-visualize-waveforms:

svtk visualize waveforms
^^^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk visualize waveforms [-h]
                                {list,event-radial-trace-section,observed-synthetic-record-section,record-section,station-event-waveform-map,waveform-overlay-matrix}
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

.. _cli-svtk-visualize-waveforms-event-radial-trace-section:

svtk visualize waveforms event-radial-trace-section
"""""""""""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize waveforms event-radial-trace-section [-h] [--input PATH]
                                                           [--output PATH]
                                                           [--config PATH]
                                                           [--run-scenario RUN_SCENARIO]
                                                           [--table [ARG=PATH]]
                                                           [--no-table]
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
                                                           [--x-col X_COL]
                                                           [--y-col Y_COL]
                                                           [--group-col GROUP_COL]
                                                           [--color-col COLOR_COL]
                                                           [--fit FIT]
                                                           [--connect-points | --no-connect-points]
                                                           [--mode MODE]
                                                           [--dep DEP]
                                                           [--indep INDEP]
                                                           [--colorby COLORBY]
                                                           [--compare-to COMPARE_TO]
                                                           [--station-region STATION_REGIONS]
                                                           [--event-region EVENT_REGIONS]
                                                           [--scale SCALE]
                                                           [--time-limit-s TIME_LIMIT_S]
                                                           [--max-records MAX_RECORDS]
                                                           [--max-traces MAX_TRACES]
                                                           [--title TITLE]
                                                           [--write-sidecar]
                                                           [--sidecar-rows SIDECAR_ROWS]
                                                           [--sidecar-dir DIR]
                                                           [--bounds BOUNDS]
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
     - Filesystem path. Primary figure input table (event station records); accepts CSV or parquet. Defaults to configured output table 'event_station_records' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'event_radial_trace_section' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-waveforms-list:

svtk visualize waveforms list
"""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize waveforms list [-h]

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

.. _cli-svtk-visualize-waveforms-observed-synthetic-record-section:

svtk visualize waveforms observed-synthetic-record-section
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize waveforms observed-synthetic-record-section
       [-h] [--input PATH] [--output PATH] [--config PATH]
       [--run-scenario RUN_SCENARIO] [--table [ARG=PATH]] [--no-table]
       [--kwargs [KWARGS ...]] [--kwargs-json KWARGS_JSON] [--metric METRIC]
       [--passband PASSBAND] [--bin-label BIN_LABEL] [--component COMPONENT]
       [--components COMPONENTS] [--model MODEL] [--value-col VALUE_COL]
       [--score-col SCORE_COL] [--x-col X_COL] [--y-col Y_COL]
       [--group-col GROUP_COL] [--color-col COLOR_COL] [--fit FIT]
       [--connect-points | --no-connect-points] [--mode MODE] [--dep DEP]
       [--indep INDEP] [--colorby COLORBY] [--compare-to COMPARE_TO]
       [--station-region STATION_REGIONS] [--event-region EVENT_REGIONS]
       [--scale SCALE] [--time-limit-s TIME_LIMIT_S]
       [--max-records MAX_RECORDS] [--max-traces MAX_TRACES] [--title TITLE]
       [--write-sidecar] [--sidecar-rows SIDECAR_ROWS] [--sidecar-dir DIR]
       [--bounds BOUNDS] [--no-basemap] [--basemap-source BASEMAP_SOURCE]

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
     - Filesystem path. Primary figure input table (event station records); accepts CSV or parquet. Defaults to configured output table 'event_station_records' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'observed_synthetic_record_section' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-waveforms-record-section:

svtk visualize waveforms record-section
"""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize waveforms record-section [-h] [--input PATH]
                                               [--output PATH] [--config PATH]
                                               [--run-scenario RUN_SCENARIO]
                                               [--table [ARG=PATH]]
                                               [--no-table]
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
                                               [--title TITLE]
                                               [--write-sidecar]
                                               [--sidecar-rows SIDECAR_ROWS]
                                               [--sidecar-dir DIR]
                                               [--bounds BOUNDS]
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
     - Filesystem path. Primary figure input table (event station records); accepts CSV or parquet. Defaults to configured output table 'event_station_records' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'record_section' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-waveforms-station-event-waveform-map:

svtk visualize waveforms station-event-waveform-map
"""""""""""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize waveforms station-event-waveform-map [-h] [--input PATH]
                                                           [--output PATH]
                                                           [--config PATH]
                                                           [--run-scenario RUN_SCENARIO]
                                                           [--table [ARG=PATH]]
                                                           [--no-table]
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
                                                           [--x-col X_COL]
                                                           [--y-col Y_COL]
                                                           [--group-col GROUP_COL]
                                                           [--color-col COLOR_COL]
                                                           [--fit FIT]
                                                           [--connect-points | --no-connect-points]
                                                           [--mode MODE]
                                                           [--dep DEP]
                                                           [--indep INDEP]
                                                           [--colorby COLORBY]
                                                           [--compare-to COMPARE_TO]
                                                           [--station-region STATION_REGIONS]
                                                           [--event-region EVENT_REGIONS]
                                                           [--scale SCALE]
                                                           [--time-limit-s TIME_LIMIT_S]
                                                           [--max-records MAX_RECORDS]
                                                           [--max-traces MAX_TRACES]
                                                           [--title TITLE]
                                                           [--write-sidecar]
                                                           [--sidecar-rows SIDECAR_ROWS]
                                                           [--sidecar-dir DIR]
                                                           [--bounds BOUNDS]
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
     - Filesystem path. Primary figure input table (event station records); accepts CSV or parquet. Defaults to configured output table 'event_station_records' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'station_event_waveform_map' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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

.. _cli-svtk-visualize-waveforms-waveform-overlay-matrix:

svtk visualize waveforms waveform-overlay-matrix
""""""""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize waveforms waveform-overlay-matrix [-h] [--input PATH]
                                                        [--output PATH]
                                                        [--config PATH]
                                                        [--run-scenario RUN_SCENARIO]
                                                        [--table [ARG=PATH]]
                                                        [--no-table]
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
                                                        [--x-col X_COL]
                                                        [--y-col Y_COL]
                                                        [--group-col GROUP_COL]
                                                        [--color-col COLOR_COL]
                                                        [--fit FIT]
                                                        [--connect-points | --no-connect-points]
                                                        [--mode MODE]
                                                        [--dep DEP]
                                                        [--indep INDEP]
                                                        [--colorby COLORBY]
                                                        [--compare-to COMPARE_TO]
                                                        [--station-region STATION_REGIONS]
                                                        [--event-region EVENT_REGIONS]
                                                        [--scale SCALE]
                                                        [--time-limit-s TIME_LIMIT_S]
                                                        [--max-records MAX_RECORDS]
                                                        [--max-traces MAX_TRACES]
                                                        [--title TITLE]
                                                        [--write-sidecar]
                                                        [--sidecar-rows SIDECAR_ROWS]
                                                        [--sidecar-dir DIR]
                                                        [--bounds BOUNDS]
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
     - Filesystem path. Primary figure input table (event station records); accepts CSV or parquet. Defaults to configured output table 'event_station_records' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'waveform_overlay_matrix' when --config is passed or a default config is set with 'svtk config set'.
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
     - Advanced extra table mapping as function_argument=path. May be repeated. Prefer config-backed defaults and named table flags such as --events, --stations, or --records when this command lists them. For plotting functions with a boolean table option, omit the value to show the table.
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
     - Column containing scores or residual values for score-style plots.
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
