.. _cli-svtk-plot:

svtk plot
=========

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

   svtk plot metrics band-score-distribution [-h] --input INPUT --output
                                                 OUTPUT [--table TABLE]
                                                 [--kwargs [KWARGS ...]]
                                                 [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-metrics-boxplot:

svtk plot metrics boxplot
"""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics boxplot [-h] --input INPUT --output OUTPUT
                                 [--table TABLE] [--kwargs [KWARGS ...]]
                                 [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the data argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-metrics-example-metric-pairs:

svtk plot metrics example-metric-pairs
""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics example-metric-pairs [-h] --output OUTPUT
                                              [--table TABLE]
                                              [--kwargs [KWARGS ...]]
                                              [--kwargs-json KWARGS_JSON]

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
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-metrics-geology-boxplot:

svtk plot metrics geology-boxplot
"""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics geology-boxplot [-h] --input INPUT --output OUTPUT
                                         [--table TABLE]
                                         [--kwargs [KWARGS ...]]
                                         [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-metrics-heatmap:

svtk plot metrics heatmap
"""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics heatmap [-h] --input INPUT --output OUTPUT
                                 [--table TABLE] [--kwargs [KWARGS ...]]
                                 [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the data argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

   svtk plot metrics metric-trend [-h] --input INPUT --output OUTPUT
                                      [--table TABLE] [--kwargs [KWARGS ...]]
                                      [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-metrics-model-metric-heatmap:

svtk plot metrics model-metric-heatmap
""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics model-metric-heatmap [-h] --input INPUT --output
                                              OUTPUT [--table TABLE]
                                              [--kwargs [KWARGS ...]]
                                              [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the summary_df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-metrics-period-spectra:

svtk plot metrics period-spectra
""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics period-spectra [-h] --input INPUT --output OUTPUT
                                        [--table TABLE]
                                        [--kwargs [KWARGS ...]]
                                        [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the spectra_df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-metrics-period-spectrogram:

svtk plot metrics period-spectrogram
""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics period-spectrogram [-h] --input INPUT --output OUTPUT
                                            [--table TABLE]
                                            [--kwargs [KWARGS ...]]
                                            [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the spectrogram_df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-metrics-phase-delay-vs-distance:

svtk plot metrics phase-delay-vs-distance
"""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics phase-delay-vs-distance [-h] --input INPUT --output
                                                 OUTPUT [--table TABLE]
                                                 [--kwargs [KWARGS ...]]
                                                 [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-metrics-psa-period-curve:

svtk plot metrics psa-period-curve
""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics psa-period-curve [-h] --input INPUT --output OUTPUT
                                          [--table TABLE]
                                          [--kwargs [KWARGS ...]]
                                          [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-metrics-residuals-vs-depth:

svtk plot metrics residuals-vs-depth
""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics residuals-vs-depth [-h] --input INPUT --output OUTPUT
                                            [--table TABLE]
                                            [--kwargs [KWARGS ...]]
                                            [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-metrics-residuals-vs-distance:

svtk plot metrics residuals-vs-distance
"""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics residuals-vs-distance [-h] --input INPUT --output
                                               OUTPUT [--table TABLE]
                                               [--kwargs [KWARGS ...]]
                                               [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-metrics-scatterplot:

svtk plot metrics scatterplot
"""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics scatterplot [-h] --input INPUT --output OUTPUT
                                     [--table TABLE] [--kwargs [KWARGS ...]]
                                     [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the data argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-metrics-score-trends:

svtk plot metrics score-trends
""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics score-trends [-h] --input INPUT --output OUTPUT
                                      [--table TABLE] [--kwargs [KWARGS ...]]
                                      [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-metrics-vs30-scatter:

svtk plot metrics vs30-scatter
""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics vs30-scatter [-h] --input INPUT --output OUTPUT
                                      [--table TABLE] [--kwargs [KWARGS ...]]
                                      [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-metrics-winner-heatmap:

svtk plot metrics winner-heatmap
""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot metrics winner-heatmap [-h] --input INPUT --output OUTPUT
                                        [--table TABLE]
                                        [--kwargs [KWARGS ...]]
                                        [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the summary_df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

   svtk plot spatial azimuthal-residuals [-h] --input INPUT --output
                                             OUTPUT [--table TABLE]
                                             [--kwargs [KWARGS ...]]
                                             [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-spatial-block-holdout-scatter:

svtk plot spatial block-holdout-scatter
"""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial block-holdout-scatter [-h] --input INPUT --output
                                               OUTPUT [--table TABLE]
                                               [--kwargs [KWARGS ...]]
                                               [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the prediction_df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-spatial-cluster-feature-heatmap:

svtk plot spatial cluster-feature-heatmap
"""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial cluster-feature-heatmap [-h] --input INPUT --output
                                                 OUTPUT [--table TABLE]
                                                 [--kwargs [KWARGS ...]]
                                                 [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the feature_summary_df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-spatial-cluster-solution-scores:

svtk plot spatial cluster-solution-scores
"""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial cluster-solution-scores [-h] --input INPUT --output
                                                 OUTPUT [--table TABLE]
                                                 [--kwargs [KWARGS ...]]
                                                 [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the score_df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-spatial-correlogram:

svtk plot spatial correlogram
"""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial correlogram [-h] --input INPUT --output OUTPUT
                                     [--table TABLE] [--kwargs [KWARGS ...]]
                                     [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the distance_df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-spatial-directional-correlogram:

svtk plot spatial directional-correlogram
"""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial directional-correlogram [-h] --input INPUT --output
                                                 OUTPUT [--table TABLE]
                                                 [--kwargs [KWARGS ...]]
                                                 [--kwargs-json KWARGS_JSON]
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
   * - ``--input``
     - Yes
     - 
     - Value: ``input``. Input CSV/parquet table for the directional_df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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
   * - ``--fit``
     - No
     - 
     - Value: ``fit``. Convenience table path for the fit_df argument.

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

   svtk plot spatial path-bin-summary [-h] --input INPUT --output OUTPUT
                                          [--table TABLE]
                                          [--kwargs [KWARGS ...]]
                                          [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the path_summary_df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-spatial-pattern-similarity:

svtk plot spatial pattern-similarity
""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial pattern-similarity [-h] --input INPUT --output OUTPUT
                                            [--table TABLE]
                                            [--kwargs [KWARGS ...]]
                                            [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the stations argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-spatial-pca-explained-variance:

svtk plot spatial pca-explained-variance
""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial pca-explained-variance [-h] --input INPUT --output
                                                OUTPUT [--table TABLE]
                                                [--kwargs [KWARGS ...]]
                                                [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the explained_variance_df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-spatial-pca-feature-loadings:

svtk plot spatial pca-feature-loadings
""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial pca-feature-loadings [-h] --input INPUT --output
                                              OUTPUT [--table TABLE]
                                              [--kwargs [KWARGS ...]]
                                              [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the feature_loadings_df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-spatial-polar-residuals:

svtk plot spatial polar-residuals
"""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial polar-residuals [-h] --input INPUT --output OUTPUT
                                         [--table TABLE]
                                         [--kwargs [KWARGS ...]]
                                         [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-spatial-residual-correlation:

svtk plot spatial residual-correlation
""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial residual-correlation [-h] --input INPUT --output
                                              OUTPUT [--table TABLE]
                                              [--kwargs [KWARGS ...]]
                                              [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the correlation_df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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

.. _cli-svtk-plot-spatial-semivariogram:

svtk plot spatial semivariogram
"""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk plot spatial semivariogram [-h] --input INPUT --output OUTPUT
                                       [--table TABLE] [--kwargs [KWARGS ...]]
                                       [--kwargs-json KWARGS_JSON]

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
     - Value: ``input``. Input CSV/parquet table for the distance_df argument.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output figure path.
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
