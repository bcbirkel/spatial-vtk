.. _cli-svtk-plot:

svtk plot
=========

Config-Backed Plotting
-----------------------

If a config is active with ``svtk config set`` or passed with ``--config``, registered plotting commands resolve their standard input tables and figure outputs automatically. For routine workflow figures, prefer the curated flags shown below instead of passing legacy ``--input`` and ``--output`` paths.

.. code-block:: bash

   svtk config set data/examples/configuration/example_spatial_vtk_config.yaml
   svtk plot metrics band-score-distribution --score-col log2_residual
   svtk plot metrics residuals-vs-distance --metric PGA --passband "2-3 sec" --y-col log2_residual

These commands use configured outputs such as ``metrics_long`` plus the registered figure keys for the selected plot unless you supply ``--input-table``/``--input`` or ``--figure-output``/``--output`` explicitly. Run ``svtk plot metrics list`` or ``svtk plot spatial list`` to print a table showing each command's input and output source, including ``config:<key>`` defaults and ``required:<role> (--input-table PATH)`` entries. Add ``--resolve-paths --config PATH`` to show the concrete configured files.

Command Tree
------------

- :ref:`svtk plot <cli-svtk-plot>`
   - :ref:`svtk plot metrics <cli-svtk-plot-metrics>`
      - :ref:`svtk plot metrics band-score-distribution <cli-svtk-plot-metrics-band-score-distribution>` - Plot residual or score distributions by passband.
      - :ref:`svtk plot metrics boxplot <cli-svtk-plot-metrics-boxplot>` - Plot metric distributions by categorical variables.
      - :ref:`svtk plot metrics example-metric-pairs <cli-svtk-plot-metrics-example-metric-pairs>` - Plot synthetic trace-pair examples that illustrate metric behavior.
      - :ref:`svtk plot metrics geology-boxplot <cli-svtk-plot-metrics-geology-boxplot>` - Plot metric values by geologic class.
      - :ref:`svtk plot metrics heatmap <cli-svtk-plot-metrics-heatmap>` - Plot categorical metric summaries as a heatmap.
      - :ref:`svtk plot metrics list <cli-svtk-plot-metrics-list>`
      - :ref:`svtk plot metrics metric-trend <cli-svtk-plot-metrics-metric-trend>` - Plot a general metric trend.
      - :ref:`svtk plot metrics model-metric-heatmap <cli-svtk-plot-metrics-model-metric-heatmap>` - Plot a model-by-metric heatmap.
      - :ref:`svtk plot metrics period-spectra <cli-svtk-plot-metrics-period-spectra>` - Plot period spectra.
      - :ref:`svtk plot metrics period-spectrogram <cli-svtk-plot-metrics-period-spectrogram>` - Plot a precomputed period-spectrogram table. This advanced figure does not have a standard config-backed input table; pass --input-table or --input explicitly.
      - :ref:`svtk plot metrics phase-delay-vs-distance <cli-svtk-plot-metrics-phase-delay-vs-distance>` - Plot phase delay against distance.
      - :ref:`svtk plot metrics psa-period-curve <cli-svtk-plot-metrics-psa-period-curve>` - Plot PSA values by period.
      - :ref:`svtk plot metrics residuals-vs-depth <cli-svtk-plot-metrics-residuals-vs-depth>` - Plot residuals against event depth.
      - :ref:`svtk plot metrics residuals-vs-distance <cli-svtk-plot-metrics-residuals-vs-distance>` - Plot residuals against distance.
      - :ref:`svtk plot metrics scatterplot <cli-svtk-plot-metrics-scatterplot>` - Plot any metric-table variable against another variable.
      - :ref:`svtk plot metrics score-trends <cli-svtk-plot-metrics-score-trends>` - Plot score trends.
      - :ref:`svtk plot metrics vs30-scatter <cli-svtk-plot-metrics-vs30-scatter>` - Plot metric values against Vs30.
      - :ref:`svtk plot metrics winner-heatmap <cli-svtk-plot-metrics-winner-heatmap>` - Plot a winner/class heatmap.
   - :ref:`svtk plot spatial <cli-svtk-plot-spatial>`
      - :ref:`svtk plot spatial azimuthal-residuals <cli-svtk-plot-spatial-azimuthal-residuals>` - Plot residuals by azimuth.
      - :ref:`svtk plot spatial block-holdout-scatter <cli-svtk-plot-spatial-block-holdout-scatter>` - Plot observed versus held-out predictions.
      - :ref:`svtk plot spatial cluster-feature-heatmap <cli-svtk-plot-spatial-cluster-feature-heatmap>` - Plot cluster feature summaries.
      - :ref:`svtk plot spatial cluster-solution-scores <cli-svtk-plot-spatial-cluster-solution-scores>` - Plot clustering solution scores.
      - :ref:`svtk plot spatial correlogram <cli-svtk-plot-spatial-correlogram>` - Plot a spatial correlogram.
      - :ref:`svtk plot spatial directional-correlogram <cli-svtk-plot-spatial-directional-correlogram>` - Plot directional spatial correlations.
      - :ref:`svtk plot spatial list <cli-svtk-plot-spatial-list>`
      - :ref:`svtk plot spatial path-bin-summary <cli-svtk-plot-spatial-path-bin-summary>` - Plot path-bin summary values.
      - :ref:`svtk plot spatial pattern-similarity <cli-svtk-plot-spatial-pattern-similarity>` - Plot observed/synthetic pattern similarity.
      - :ref:`svtk plot spatial pca-explained-variance <cli-svtk-plot-spatial-pca-explained-variance>` - Plot PCA explained variance.
      - :ref:`svtk plot spatial pca-feature-loadings <cli-svtk-plot-spatial-pca-feature-loadings>` - Plot PCA feature loadings.
      - :ref:`svtk plot spatial polar-residuals <cli-svtk-plot-spatial-polar-residuals>` - Plot residuals in polar coordinates.
      - :ref:`svtk plot spatial residual-correlation <cli-svtk-plot-spatial-residual-correlation>` - Plot residual correlation values.
      - :ref:`svtk plot spatial semivariogram <cli-svtk-plot-spatial-semivariogram>` - Plot a semivariogram.

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

Plot residual or score distributions by passband.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics band-score-distribution [-h] [--input-table PATH]
                                                 [--figure-output PATH]
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
     - ``config:band_score_distribution``
     - Uses configured figure output ``band_score_distribution`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or Parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'band_score_distribution' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-boxplot:

svtk plot metrics boxplot
"""""""""""""""""""""""""

Plot metric distributions by categorical variables.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics boxplot [-h] [--input-table PATH]
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
                                 [--sidecar-dir DIR]

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
     - ``config:boxplot``
     - Uses configured figure output ``boxplot`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or Parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'boxplot' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-example-metric-pairs:

svtk plot metrics example-metric-pairs
""""""""""""""""""""""""""""""""""""""

Plot synthetic trace-pair examples that illustrate metric behavior.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics example-metric-pairs [-h] [--figure-output PATH]
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

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``none``
     - This command does not read a primary input table.
   * - Output figure
     - ``config:example_metric_pairs``
     - Uses configured figure output ``example_metric_pairs`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'example_metric_pairs' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-geology-boxplot:

svtk plot metrics geology-boxplot
"""""""""""""""""""""""""""""""""

Plot metric values by geologic class.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics geology-boxplot [-h] [--input-table PATH]
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
     - ``config:geology_boxplot``
     - Uses configured figure output ``geology_boxplot`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or Parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'geology_boxplot' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-heatmap:

svtk plot metrics heatmap
"""""""""""""""""""""""""

Plot categorical metric summaries as a heatmap.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics heatmap [-h] [--input-table PATH]
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
                                 [--sidecar-dir DIR]

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
     - ``config:heatmap``
     - Uses configured figure output ``heatmap`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or Parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'heatmap' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-list:

svtk plot metrics list
""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics list [-h] [--config PATH]
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

.. _cli-svtk-plot-metrics-metric-trend:

svtk plot metrics metric-trend
""""""""""""""""""""""""""""""

Plot a general metric trend.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics metric-trend [-h] [--input-table PATH]
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
                                      [--sidecar-dir DIR]

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
     - ``config:metric_trend``
     - Uses configured figure output ``metric_trend`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or Parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'metric_trend' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-model-metric-heatmap:

svtk plot metrics model-metric-heatmap
""""""""""""""""""""""""""""""""""""""

Plot a model-by-metric heatmap.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics model-metric-heatmap [-h] [--input-table PATH]
                                              [--figure-output PATH]
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
     - ``config:model_metric_heatmap``
     - Uses configured figure output ``model_metric_heatmap`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or Parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'model_metric_heatmap' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-period-spectra:

svtk plot metrics period-spectra
""""""""""""""""""""""""""""""""

Plot period spectra.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics period-spectra [-h] [--input-table PATH]
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
                                        [--sidecar-dir DIR]

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
     - ``config:period_spectra``
     - Uses configured figure output ``period_spectra`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or Parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'period_spectra' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-period-spectrogram:

svtk plot metrics period-spectrogram
""""""""""""""""""""""""""""""""""""

Plot a precomputed period-spectrogram table. This advanced figure does not have a standard config-backed input table; pass --input-table or --input explicitly.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics period-spectrogram [-h] [--input-table PATH]
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

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``required:spectrogram table (--input-table PATH)``
     - This advanced figure requires an explicit table. Pass ``--input-table`` or ``--input`` with a precomputed period-spectrogram table.
   * - Output figure
     - ``config:period_spectrogram``
     - Uses configured figure output ``period_spectrogram`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (spectrogram); accepts CSV or Parquet. This advanced figure requires an explicit table; pass --input-table or --input.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'period_spectrogram' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-phase-delay-vs-distance:

svtk plot metrics phase-delay-vs-distance
"""""""""""""""""""""""""""""""""""""""""

Plot phase delay against distance.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics phase-delay-vs-distance [-h] [--input-table PATH]
                                                 [--figure-output PATH]
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
     - ``config:phase_delay_vs_distance``
     - Uses configured figure output ``phase_delay_vs_distance`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or Parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'phase_delay_vs_distance' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-psa-period-curve:

svtk plot metrics psa-period-curve
""""""""""""""""""""""""""""""""""

Plot PSA values by period.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics psa-period-curve [-h] [--input-table PATH]
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
     - ``config:psa_period_curve``
     - Uses configured figure output ``psa_period_curve`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or Parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'psa_period_curve' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-residuals-vs-depth:

svtk plot metrics residuals-vs-depth
""""""""""""""""""""""""""""""""""""

Plot residuals against event depth.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics residuals-vs-depth [-h] [--input-table PATH]
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
     - ``config:residuals_vs_depth``
     - Uses configured figure output ``residuals_vs_depth`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or Parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'residuals_vs_depth' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-residuals-vs-distance:

svtk plot metrics residuals-vs-distance
"""""""""""""""""""""""""""""""""""""""

Plot residuals against distance.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics residuals-vs-distance [-h] [--input-table PATH]
                                               [--figure-output PATH]
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
     - ``config:residuals_vs_distance``
     - Uses configured figure output ``residuals_vs_distance`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or Parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'residuals_vs_distance' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-scatterplot:

svtk plot metrics scatterplot
"""""""""""""""""""""""""""""

Plot any metric-table variable against another variable.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics scatterplot [-h] [--input-table PATH]
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
                                     [--sidecar-dir DIR]

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
     - ``config:scatterplot``
     - Uses configured figure output ``scatterplot`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or Parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'scatterplot' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-score-trends:

svtk plot metrics score-trends
""""""""""""""""""""""""""""""

Plot score trends.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics score-trends [-h] [--input-table PATH]
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
                                      [--sidecar-dir DIR]

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
     - ``config:score_trends``
     - Uses configured figure output ``score_trends`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or Parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'score_trends' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-vs30-scatter:

svtk plot metrics vs30-scatter
""""""""""""""""""""""""""""""

Plot metric values against Vs30.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics vs30-scatter [-h] [--input-table PATH]
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
                                      [--sidecar-dir DIR]

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
     - ``config:vs30_scatter``
     - Uses configured figure output ``vs30_scatter`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or Parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'vs30_scatter' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-metrics-winner-heatmap:

svtk plot metrics winner-heatmap
""""""""""""""""""""""""""""""""

Plot a winner/class heatmap.

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics winner-heatmap [-h] [--input-table PATH]
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
                                        [--sidecar-dir DIR]

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
     - ``config:winner_heatmap``
     - Uses configured figure output ``winner_heatmap`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (metrics long); accepts CSV or Parquet. Defaults to configured output table 'metrics_long' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'winner_heatmap' when --config is passed or a default config is set with 'svtk config set'.
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

Plot residuals by azimuth.

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial azimuthal-residuals [-h] [--input-table PATH]
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

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:event_centered_residuals``
     - Uses configured output table ``event_centered_residuals`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:azimuthal_residuals``
     - Uses configured figure output ``azimuthal_residuals`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (event centered residuals); accepts CSV or Parquet. Defaults to configured output table 'event_centered_residuals' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'azimuthal_residuals' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-block-holdout-scatter:

svtk plot spatial block-holdout-scatter
"""""""""""""""""""""""""""""""""""""""

Plot observed versus held-out predictions.

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial block-holdout-scatter [-h] [--input-table PATH]
                                               [--figure-output PATH]
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
     - ``config:block_holdout_scatter``
     - Uses configured figure output ``block_holdout_scatter`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (block holdout predictions); accepts CSV or Parquet. Defaults to configured output table 'block_holdout_predictions' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'block_holdout_scatter' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-cluster-feature-heatmap:

svtk plot spatial cluster-feature-heatmap
"""""""""""""""""""""""""""""""""""""""""

Plot cluster feature summaries.

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial cluster-feature-heatmap [-h] [--input-table PATH]
                                                 [--figure-output PATH]
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

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:cluster_feature_summary``
     - Uses configured output table ``cluster_feature_summary`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:cluster_feature_heatmap``
     - Uses configured figure output ``cluster_feature_heatmap`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (cluster feature summary); accepts CSV or Parquet. Defaults to configured output table 'cluster_feature_summary' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'cluster_feature_heatmap' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-cluster-solution-scores:

svtk plot spatial cluster-solution-scores
"""""""""""""""""""""""""""""""""""""""""

Plot clustering solution scores.

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial cluster-solution-scores [-h] [--input-table PATH]
                                                 [--figure-output PATH]
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

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:cluster_solution_scores``
     - Uses configured output table ``cluster_solution_scores`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:cluster_solution_scores_plot``
     - Uses configured figure output ``cluster_solution_scores_plot`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (cluster solution scores); accepts CSV or Parquet. Defaults to configured output table 'cluster_solution_scores' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'cluster_solution_scores_plot' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-correlogram:

svtk plot spatial correlogram
"""""""""""""""""""""""""""""

Plot a spatial correlogram.

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial correlogram [-h] [--input-table PATH]
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
                                     [--sidecar-dir DIR]

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:distance_bin_correlations``
     - Uses configured output table ``distance_bin_correlations`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:correlogram``
     - Uses configured figure output ``correlogram`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (distance bin correlations); accepts CSV or Parquet. Defaults to configured output table 'distance_bin_correlations' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'correlogram' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-directional-correlogram:

svtk plot spatial directional-correlogram
"""""""""""""""""""""""""""""""""""""""""

Plot directional spatial correlations.

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial directional-correlogram [-h] [--input-table PATH]
                                                 [--figure-output PATH]
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
                                                 [--fit PATH]

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:distance_bin_correlations``
     - Uses configured output table ``distance_bin_correlations`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:directional_correlogram``
     - Uses configured figure output ``directional_correlogram`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.
   * - Extra tables
     - ``--fit(fit_df)=optional``
     - Optional named table flags are available for this command.

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
     - Filesystem path. Primary figure input table (distance bin correlations); accepts CSV or Parquet. Defaults to configured output table 'distance_bin_correlations' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'directional_correlogram' when --config is passed or a default config is set with 'svtk config set'.
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
     - Filesystem path. Convenience fit table path; accepts CSV or Parquet.

.. _cli-svtk-plot-spatial-list:

svtk plot spatial list
""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial list [-h] [--config PATH]
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

.. _cli-svtk-plot-spatial-path-bin-summary:

svtk plot spatial path-bin-summary
""""""""""""""""""""""""""""""""""

Plot path-bin summary values.

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial path-bin-summary [-h] [--input-table PATH]
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

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:path_summary``
     - Uses configured output table ``path_summary`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:path_bin_summary``
     - Uses configured figure output ``path_bin_summary`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (path summary); accepts CSV or Parquet. Defaults to configured output table 'path_summary' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'path_bin_summary' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-pattern-similarity:

svtk plot spatial pattern-similarity
""""""""""""""""""""""""""""""""""""

Plot observed/synthetic pattern similarity.

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial pattern-similarity [-h] [--input-table PATH]
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

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:pattern_similarity_station_anomalies``
     - Uses configured output table ``pattern_similarity_station_anomalies`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:pattern_similarity``
     - Uses configured figure output ``pattern_similarity`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (pattern similarity station anomalies); accepts CSV or Parquet. Defaults to configured output table 'pattern_similarity_station_anomalies' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'pattern_similarity' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-pca-explained-variance:

svtk plot spatial pca-explained-variance
""""""""""""""""""""""""""""""""""""""""

Plot PCA explained variance.

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial pca-explained-variance [-h] [--input-table PATH]
                                                [--figure-output PATH]
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

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:pca_explained_variance``
     - Uses configured output table ``pca_explained_variance`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:pca_explained_variance``
     - Uses configured figure output ``pca_explained_variance`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (pca explained variance); accepts CSV or Parquet. Defaults to configured output table 'pca_explained_variance' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'pca_explained_variance' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-pca-feature-loadings:

svtk plot spatial pca-feature-loadings
""""""""""""""""""""""""""""""""""""""

Plot PCA feature loadings.

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial pca-feature-loadings [-h] [--input-table PATH]
                                              [--figure-output PATH]
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

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:pca_feature_loadings``
     - Uses configured output table ``pca_feature_loadings`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:pca_feature_loadings``
     - Uses configured figure output ``pca_feature_loadings`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (pca feature loadings); accepts CSV or Parquet. Defaults to configured output table 'pca_feature_loadings' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'pca_feature_loadings' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-polar-residuals:

svtk plot spatial polar-residuals
"""""""""""""""""""""""""""""""""

Plot residuals in polar coordinates.

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial polar-residuals [-h] [--input-table PATH]
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

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:event_centered_residuals``
     - Uses configured output table ``event_centered_residuals`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:polar_residuals``
     - Uses configured figure output ``polar_residuals`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (event centered residuals); accepts CSV or Parquet. Defaults to configured output table 'event_centered_residuals' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'polar_residuals' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-residual-correlation:

svtk plot spatial residual-correlation
""""""""""""""""""""""""""""""""""""""

Plot residual correlation values.

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial residual-correlation [-h] [--input-table PATH]
                                              [--figure-output PATH]
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

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:distance_bin_correlations``
     - Uses configured output table ``distance_bin_correlations`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:residual_correlation``
     - Uses configured figure output ``residual_correlation`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (distance bin correlations); accepts CSV or Parquet. Defaults to configured output table 'distance_bin_correlations' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'residual_correlation' when --config is passed or a default config is set with 'svtk config set'.
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

.. _cli-svtk-plot-spatial-semivariogram:

svtk plot spatial semivariogram
"""""""""""""""""""""""""""""""

Plot a semivariogram.

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial semivariogram [-h] [--input-table PATH]
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
                                       [--sidecar-dir DIR]

.. rubric:: Configured defaults

.. list-table::
   :header-rows: 1
   :widths: 20 26 54

   * - Role
     - Source
     - Meaning
   * - Input table
     - ``config:distance_bin_correlations``
     - Uses configured output table ``distance_bin_correlations`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--input-table`` or ``--input``.
   * - Output figure
     - ``config:semivariogram``
     - Uses configured figure output ``semivariogram`` when ``--config`` is passed or a default config is set with ``svtk config set``. Override with ``--figure-output`` or ``--output``.

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
     - Filesystem path. Primary figure input table (distance bin correlations); accepts CSV or Parquet. Defaults to configured output table 'distance_bin_correlations' when --config is passed or a default config is set with 'svtk config set'.
   * - ``--figure-output``, ``--output``
     - No
     -
     - Filesystem path. Output figure path. Prefer --figure-output; --output is a legacy alias. Defaults to configured figure output 'semivariogram' when --config is passed or a default config is set with 'svtk config set'.
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
