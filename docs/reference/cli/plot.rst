.. _cli-svtk-plot:

svtk plot
=========

Config-Backed Plotting
-----------------------

If a config is active with ``svtk config set`` or passed with ``--config``, registered plotting commands resolve their standard input tables and figure outputs automatically. For routine workflow figures, prefer the curated flags shown below instead of passing raw ``--input`` and ``--output`` paths.

.. code-block:: bash

   svtk config set data/examples/configuration/example_spatial_vtk_config.yaml
   svtk plot metrics band-score-distribution --score-col log2_residual
   svtk plot metrics residuals-vs-distance --metric PGA --passband "2-3 sec" --score-col log2_residual

These commands use configured outputs such as ``metrics_long`` plus the registered figure keys for the selected plot unless you supply ``--input``/``--input-table`` or ``--output``/``--figure-output`` explicitly. Run ``svtk plot metrics list`` or ``svtk plot spatial list`` to print a table showing each command's input and output source, including ``config:<key>`` defaults and ``required:--input`` entries.

Command Tree
------------

- :ref:`svtk plot <cli-svtk-plot>`
   - :ref:`svtk plot metrics <cli-svtk-plot-metrics>`
      - :ref:`svtk plot metrics band-score-distribution <cli-svtk-plot-metrics-band-score-distribution>`
      - :ref:`svtk plot metrics boxplot <cli-svtk-plot-metrics-boxplot>`
      - :ref:`svtk plot metrics example-metric-pairs <cli-svtk-plot-metrics-example-metric-pairs>`
      - :ref:`svtk plot metrics geology-boxplot <cli-svtk-plot-metrics-geology-boxplot>`
      - :ref:`svtk plot metrics heatmap <cli-svtk-plot-metrics-heatmap>`
      - :ref:`svtk plot metrics list <cli-svtk-plot-metrics-list>`
      - :ref:`svtk plot metrics metric-trend <cli-svtk-plot-metrics-metric-trend>`
      - :ref:`svtk plot metrics model-metric-heatmap <cli-svtk-plot-metrics-model-metric-heatmap>`
      - :ref:`svtk plot metrics period-spectra <cli-svtk-plot-metrics-period-spectra>`
      - :ref:`svtk plot metrics period-spectrogram <cli-svtk-plot-metrics-period-spectrogram>`
      - :ref:`svtk plot metrics phase-delay-vs-distance <cli-svtk-plot-metrics-phase-delay-vs-distance>`
      - :ref:`svtk plot metrics psa-period-curve <cli-svtk-plot-metrics-psa-period-curve>`
      - :ref:`svtk plot metrics residuals-vs-depth <cli-svtk-plot-metrics-residuals-vs-depth>`
      - :ref:`svtk plot metrics residuals-vs-distance <cli-svtk-plot-metrics-residuals-vs-distance>`
      - :ref:`svtk plot metrics scatterplot <cli-svtk-plot-metrics-scatterplot>`
      - :ref:`svtk plot metrics score-trends <cli-svtk-plot-metrics-score-trends>`
      - :ref:`svtk plot metrics vs30-scatter <cli-svtk-plot-metrics-vs30-scatter>`
      - :ref:`svtk plot metrics winner-heatmap <cli-svtk-plot-metrics-winner-heatmap>`
   - :ref:`svtk plot spatial <cli-svtk-plot-spatial>`
      - :ref:`svtk plot spatial azimuthal-residuals <cli-svtk-plot-spatial-azimuthal-residuals>`
      - :ref:`svtk plot spatial block-holdout-scatter <cli-svtk-plot-spatial-block-holdout-scatter>`
      - :ref:`svtk plot spatial cluster-feature-heatmap <cli-svtk-plot-spatial-cluster-feature-heatmap>`
      - :ref:`svtk plot spatial cluster-solution-scores <cli-svtk-plot-spatial-cluster-solution-scores>`
      - :ref:`svtk plot spatial correlogram <cli-svtk-plot-spatial-correlogram>`
      - :ref:`svtk plot spatial directional-correlogram <cli-svtk-plot-spatial-directional-correlogram>`
      - :ref:`svtk plot spatial list <cli-svtk-plot-spatial-list>`
      - :ref:`svtk plot spatial path-bin-summary <cli-svtk-plot-spatial-path-bin-summary>`
      - :ref:`svtk plot spatial pattern-similarity <cli-svtk-plot-spatial-pattern-similarity>`
      - :ref:`svtk plot spatial pca-explained-variance <cli-svtk-plot-spatial-pca-explained-variance>`
      - :ref:`svtk plot spatial pca-feature-loadings <cli-svtk-plot-spatial-pca-feature-loadings>`
      - :ref:`svtk plot spatial polar-residuals <cli-svtk-plot-spatial-polar-residuals>`
      - :ref:`svtk plot spatial residual-correlation <cli-svtk-plot-spatial-residual-correlation>`
      - :ref:`svtk plot spatial semivariogram <cli-svtk-plot-spatial-semivariogram>`

Command Details
---------------

.. rubric:: Usage

.. code-block:: bash

   svtk plot [-h] {metrics,spatial} ...

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

.. _cli-svtk-plot-metrics:

svtk plot metrics
^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics [-h]
                         {list,band-score-distribution,boxplot,example-metric-pairs,geology-boxplot,heatmap,metric-trend,model-metric-heatmap,period-spectra,period-spectrogram,phase-delay-vs-distance,psa-period-curve,residuals-vs-depth,residuals-vs-distance,scatterplot,score-trends,vs30-scatter,winner-heatmap}
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

.. _cli-svtk-plot-metrics-band-score-distribution:

svtk plot metrics band-score-distribution
"""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics band-score-distribution [-h] [--input PATH]
                                                 [--output PATH]
                                                 [--config PATH]
                                                 [--run-scenario RUN_SCENARIO]
                                                 [--table [TABLE]]
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
                                                 [--sidecar-dir SIDECAR_DIR]

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
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'band_score_distribution' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-boxplot:

svtk plot metrics boxplot
"""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics boxplot [-h] [--input PATH] [--output PATH]
                                 [--config PATH] [--run-scenario RUN_SCENARIO]
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
                                 [--sidecar-dir SIDECAR_DIR]

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
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'boxplot' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-example-metric-pairs:

svtk plot metrics example-metric-pairs
""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics example-metric-pairs [-h] [--output PATH]
                                              [--config PATH]
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
                                              [--title TITLE]
                                              [--write-sidecar]
                                              [--sidecar-rows SIDECAR_ROWS]
                                              [--sidecar-dir SIDECAR_DIR]

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
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'example_metric_pairs' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-geology-boxplot:

svtk plot metrics geology-boxplot
"""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics geology-boxplot [-h] [--input PATH] [--output PATH]
                                         [--config PATH]
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
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'geology_boxplot' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-heatmap:

svtk plot metrics heatmap
"""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics heatmap [-h] [--input PATH] [--output PATH]
                                 [--config PATH] [--run-scenario RUN_SCENARIO]
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
                                 [--sidecar-dir SIDECAR_DIR]

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
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'heatmap' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-list:

svtk plot metrics list
""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics list [-h]

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

.. _cli-svtk-plot-metrics-metric-trend:

svtk plot metrics metric-trend
""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics metric-trend [-h] [--input PATH] [--output PATH]
                                      [--config PATH]
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
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'metric_trend' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-model-metric-heatmap:

svtk plot metrics model-metric-heatmap
""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics model-metric-heatmap [-h] [--input PATH]
                                              [--output PATH] [--config PATH]
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
                                              [--title TITLE]
                                              [--write-sidecar]
                                              [--sidecar-rows SIDECAR_ROWS]
                                              [--sidecar-dir SIDECAR_DIR]

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
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'model_metric_heatmap' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-period-spectra:

svtk plot metrics period-spectra
""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics period-spectra [-h] [--input PATH] [--output PATH]
                                        [--config PATH]
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
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'period_spectra' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-period-spectrogram:

svtk plot metrics period-spectrogram
""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics period-spectrogram [-h] --input PATH [--output PATH]
                                            [--config PATH]
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
     - Yes
     -
     - Filesystem path. Primary figure input table (spectrogram); accepts CSV or parquet.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'period_spectrogram' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-phase-delay-vs-distance:

svtk plot metrics phase-delay-vs-distance
"""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics phase-delay-vs-distance [-h] [--input PATH]
                                                 [--output PATH]
                                                 [--config PATH]
                                                 [--run-scenario RUN_SCENARIO]
                                                 [--table [TABLE]]
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
                                                 [--sidecar-dir SIDECAR_DIR]

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
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'phase_delay_vs_distance' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-psa-period-curve:

svtk plot metrics psa-period-curve
""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics psa-period-curve [-h] [--input PATH] [--output PATH]
                                          [--config PATH]
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
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'psa_period_curve' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-residuals-vs-depth:

svtk plot metrics residuals-vs-depth
""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics residuals-vs-depth [-h] [--input PATH]
                                            [--output PATH] [--config PATH]
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
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'residuals_vs_depth' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-residuals-vs-distance:

svtk plot metrics residuals-vs-distance
"""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics residuals-vs-distance [-h] [--input PATH]
                                               [--output PATH] [--config PATH]
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
                                               [--title TITLE]
                                               [--write-sidecar]
                                               [--sidecar-rows SIDECAR_ROWS]
                                               [--sidecar-dir SIDECAR_DIR]

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
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'residuals_vs_distance' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-scatterplot:

svtk plot metrics scatterplot
"""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics scatterplot [-h] [--input PATH] [--output PATH]
                                     [--config PATH]
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
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'scatterplot' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-score-trends:

svtk plot metrics score-trends
""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics score-trends [-h] [--input PATH] [--output PATH]
                                      [--config PATH]
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
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'score_trends' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-vs30-scatter:

svtk plot metrics vs30-scatter
""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics vs30-scatter [-h] [--input PATH] [--output PATH]
                                      [--config PATH]
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
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'vs30_scatter' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-winner-heatmap:

svtk plot metrics winner-heatmap
""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics winner-heatmap [-h] [--input PATH] [--output PATH]
                                        [--config PATH]
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
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'winner_heatmap' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial:

svtk plot spatial
^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial [-h]
                         {list,azimuthal-residuals,block-holdout-scatter,cluster-feature-heatmap,cluster-solution-scores,correlogram,directional-correlogram,path-bin-summary,pattern-similarity,pca-explained-variance,pca-feature-loadings,polar-residuals,residual-correlation,semivariogram}
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

.. _cli-svtk-plot-spatial-azimuthal-residuals:

svtk plot spatial azimuthal-residuals
"""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial azimuthal-residuals [-h] [--input PATH]
                                             [--output PATH] [--config PATH]
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
     - Filesystem path. Primary figure input table (event centered residuals); accepts CSV or parquet. Defaults to configured output table 'event_centered_residuals' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'azimuthal_residuals' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-block-holdout-scatter:

svtk plot spatial block-holdout-scatter
"""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial block-holdout-scatter [-h] [--input PATH]
                                               [--output PATH] [--config PATH]
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
                                               [--title TITLE]
                                               [--write-sidecar]
                                               [--sidecar-rows SIDECAR_ROWS]
                                               [--sidecar-dir SIDECAR_DIR]

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
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'block_holdout_scatter' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-cluster-feature-heatmap:

svtk plot spatial cluster-feature-heatmap
"""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial cluster-feature-heatmap [-h] [--input PATH]
                                                 [--output PATH]
                                                 [--config PATH]
                                                 [--run-scenario RUN_SCENARIO]
                                                 [--table [TABLE]]
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
                                                 [--sidecar-dir SIDECAR_DIR]

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
     - Filesystem path. Primary figure input table (cluster feature summary); accepts CSV or parquet. Defaults to configured output table 'cluster_feature_summary' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'cluster_feature_heatmap' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-cluster-solution-scores:

svtk plot spatial cluster-solution-scores
"""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial cluster-solution-scores [-h] [--input PATH]
                                                 [--output PATH]
                                                 [--config PATH]
                                                 [--run-scenario RUN_SCENARIO]
                                                 [--table [TABLE]]
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
                                                 [--sidecar-dir SIDECAR_DIR]

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
     - Filesystem path. Primary figure input table (cluster solution scores); accepts CSV or parquet. Defaults to configured output table 'cluster_solution_scores' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'cluster_solution_scores_plot' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-correlogram:

svtk plot spatial correlogram
"""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial correlogram [-h] [--input PATH] [--output PATH]
                                     [--config PATH]
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
     - Filesystem path. Primary figure input table (distance bin correlations); accepts CSV or parquet. Defaults to configured output table 'distance_bin_correlations' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'correlogram' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-directional-correlogram:

svtk plot spatial directional-correlogram
"""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial directional-correlogram [-h] [--input PATH]
                                                 [--output PATH]
                                                 [--config PATH]
                                                 [--run-scenario RUN_SCENARIO]
                                                 [--table [TABLE]]
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
                                                 [--sidecar-dir SIDECAR_DIR]
                                                 [--fit FIT]

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
     - Filesystem path. Primary figure input table (distance bin correlations); accepts CSV or parquet. Defaults to configured output table 'distance_bin_correlations' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'directional_correlogram' when --config is passed or a default config is set with 'svtk config set'.
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
   * - ``--fit``
     - No
     -
     - Filesystem path. Convenience fit table path; accepts CSV or parquet.

.. _cli-svtk-plot-spatial-list:

svtk plot spatial list
""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial list [-h]

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

.. _cli-svtk-plot-spatial-path-bin-summary:

svtk plot spatial path-bin-summary
""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial path-bin-summary [-h] [--input PATH] [--output PATH]
                                          [--config PATH]
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
     - Filesystem path. Primary figure input table (path summary); accepts CSV or parquet. Defaults to configured output table 'path_summary' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'path_bin_summary' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-pattern-similarity:

svtk plot spatial pattern-similarity
""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial pattern-similarity [-h] [--input PATH]
                                            [--output PATH] [--config PATH]
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
     - Filesystem path. Primary figure input table (pattern similarity station anomalies); accepts CSV or parquet. Defaults to configured output table 'pattern_similarity_station_anomalies' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'pattern_similarity' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-pca-explained-variance:

svtk plot spatial pca-explained-variance
""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial pca-explained-variance [-h] [--input PATH]
                                                [--output PATH]
                                                [--config PATH]
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
                                                [--sidecar-dir SIDECAR_DIR]

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
     - Filesystem path. Primary figure input table (pca explained variance); accepts CSV or parquet. Defaults to configured output table 'pca_explained_variance' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'pca_explained_variance' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-pca-feature-loadings:

svtk plot spatial pca-feature-loadings
""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial pca-feature-loadings [-h] [--input PATH]
                                              [--output PATH] [--config PATH]
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
                                              [--title TITLE]
                                              [--write-sidecar]
                                              [--sidecar-rows SIDECAR_ROWS]
                                              [--sidecar-dir SIDECAR_DIR]

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
     - Filesystem path. Primary figure input table (pca feature loadings); accepts CSV or parquet. Defaults to configured output table 'pca_feature_loadings' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'pca_feature_loadings' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-polar-residuals:

svtk plot spatial polar-residuals
"""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial polar-residuals [-h] [--input PATH] [--output PATH]
                                         [--config PATH]
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
     - Filesystem path. Primary figure input table (event centered residuals); accepts CSV or parquet. Defaults to configured output table 'event_centered_residuals' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'polar_residuals' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-residual-correlation:

svtk plot spatial residual-correlation
""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial residual-correlation [-h] [--input PATH]
                                              [--output PATH] [--config PATH]
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
                                              [--title TITLE]
                                              [--write-sidecar]
                                              [--sidecar-rows SIDECAR_ROWS]
                                              [--sidecar-dir SIDECAR_DIR]

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
     - Filesystem path. Primary figure input table (distance bin correlations); accepts CSV or parquet. Defaults to configured output table 'distance_bin_correlations' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'residual_correlation' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-semivariogram:

svtk plot spatial semivariogram
"""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial semivariogram [-h] [--input PATH] [--output PATH]
                                       [--config PATH]
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
     - Filesystem path. Primary figure input table (distance bin correlations); accepts CSV or parquet. Defaults to configured output table 'distance_bin_correlations' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--output``, ``--figure-output``
     - No
     -
     - Filesystem path. Output figure path. The clearer alias --figure-output is equivalent to --output. Defaults to configured figure output 'semivariogram' when --config is passed or a default config is set with 'svtk config set'.
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
