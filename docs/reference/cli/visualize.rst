.. _cli-svtk-visualize:

svtk visualize
==============

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

   svtk visualize [-h] {context,qc,waveforms} ...

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

   svtk visualize qc data-synthetic-availability [-h] --input INPUT
                                                     --output OUTPUT
                                                     [--table TABLE]
                                                     [--kwargs [KWARGS ...]]
                                                     [--kwargs-json KWARGS_JSON]
                                                     [--config CONFIG]
                                                     [--run-scenario RUN_SCENARIO]
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
   * - ``--input``
     - Yes
     - 
     - Value: ``input``. Input CSV/parquet table for the availability_df argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

.. _cli-svtk-visualize-qc-drop-cause-diagnostics:

svtk visualize qc drop-cause-diagnostics
""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize qc drop-cause-diagnostics [-h] --input INPUT --output
                                                OUTPUT [--table TABLE]
                                                [--kwargs [KWARGS ...]]
                                                [--kwargs-json KWARGS_JSON]
                                                [--config CONFIG]
                                                [--run-scenario RUN_SCENARIO]
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
   * - ``--input``
     - Yes
     - 
     - Value: ``input``. Input CSV/parquet table for the qc_df argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

.. _cli-svtk-visualize-qc-event-station-retention:

svtk visualize qc event-station-retention
"""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize qc event-station-retention [-h] --input INPUT --output
                                                 OUTPUT [--table TABLE]
                                                 [--kwargs [KWARGS ...]]
                                                 [--kwargs-json KWARGS_JSON]
                                                 [--config CONFIG]
                                                 [--run-scenario RUN_SCENARIO]
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
   * - ``--input``
     - Yes
     - 
     - Value: ``input``. Input CSV/parquet table for the retention_df argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

   svtk visualize qc post-qc-station-event-map [-h] --input INPUT --output
                                                   OUTPUT [--table TABLE]
                                                   [--kwargs [KWARGS ...]]
                                                   [--kwargs-json KWARGS_JSON]
                                                   [--config CONFIG]
                                                   [--run-scenario RUN_SCENARIO]
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
   * - ``--input``
     - Yes
     - 
     - Value: ``input``. Input CSV/parquet table for the records_df argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

.. _cli-svtk-visualize-qc-retention-summary:

svtk visualize qc retention-summary
"""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize qc retention-summary [-h] --input INPUT --output OUTPUT
                                           [--table TABLE]
                                           [--kwargs [KWARGS ...]]
                                           [--kwargs-json KWARGS_JSON]
                                           [--config CONFIG]
                                           [--run-scenario RUN_SCENARIO]
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
     - Value: ``input``. Input CSV/parquet table for the qc_df argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

.. _cli-svtk-visualize-qc-trace-inventory-samples:

svtk visualize qc trace-inventory-samples
"""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize qc trace-inventory-samples [-h] --input INPUT --output
                                                 OUTPUT [--table TABLE]
                                                 [--kwargs [KWARGS ...]]
                                                 [--kwargs-json KWARGS_JSON]
                                                 [--config CONFIG]
                                                 [--run-scenario RUN_SCENARIO]
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
   * - ``--input``
     - Yes
     - 
     - Value: ``input``. Input CSV/parquet table for the sample_df argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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
       [-h] --input INPUT --output OUTPUT [--table TABLE]
       [--kwargs [KWARGS ...]] [--kwargs-json KWARGS_JSON] [--config CONFIG]
       [--run-scenario RUN_SCENARIO] [--bounds BOUNDS] [--no-basemap]
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
     - Value: ``input``. Input CSV/parquet table for the records_df argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

.. _cli-svtk-visualize-context-event-coverage:

svtk visualize context event-coverage
"""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context event-coverage [-h] --input INPUT --output
                                             OUTPUT [--table TABLE]
                                             [--kwargs [KWARGS ...]]
                                             [--kwargs-json KWARGS_JSON]
                                             [--config CONFIG]
                                             [--run-scenario RUN_SCENARIO]
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
     - Value: ``input``. Input CSV/parquet table for the event_station_df argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

.. _cli-svtk-visualize-context-event-magnitude-map:

svtk visualize context event-magnitude-map
""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context event-magnitude-map [-h] --input INPUT --output
                                                  OUTPUT [--table TABLE]
                                                  [--kwargs [KWARGS ...]]
                                                  [--kwargs-json KWARGS_JSON]
                                                  [--config CONFIG]
                                                  [--run-scenario RUN_SCENARIO]
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
   * - ``--input``
     - Yes
     - 
     - Value: ``input``. Input CSV/parquet table for the events_df argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

.. _cli-svtk-visualize-context-event-trace-comparison:

svtk visualize context event-trace-comparison
"""""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context event-trace-comparison [-h] --input INPUT
                                                     --output OUTPUT
                                                     [--table TABLE]
                                                     [--kwargs [KWARGS ...]]
                                                     [--kwargs-json KWARGS_JSON]
                                                     [--config CONFIG]
                                                     [--run-scenario RUN_SCENARIO]
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
   * - ``--input``
     - Yes
     - 
     - Value: ``input``. Input CSV/parquet table for the records_df argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

   svtk visualize context record-coverage [-h] --input INPUT --output
                                              OUTPUT [--table TABLE]
                                              [--kwargs [KWARGS ...]]
                                              [--kwargs-json KWARGS_JSON]
                                              [--config CONFIG]
                                              [--run-scenario RUN_SCENARIO]
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
     - Value: ``input``. Input CSV/parquet table for the records_df argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

.. _cli-svtk-visualize-context-station-coverage:

svtk visualize context station-coverage
"""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context station-coverage [-h] --input INPUT --output
                                               OUTPUT [--table TABLE]
                                               [--kwargs [KWARGS ...]]
                                               [--kwargs-json KWARGS_JSON]
                                               [--config CONFIG]
                                               [--run-scenario RUN_SCENARIO]
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
   * - ``--input``
     - Yes
     - 
     - Value: ``input``. Input CSV/parquet table for the event_station_df argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

.. _cli-svtk-visualize-context-station-event-beachball:

svtk visualize context station-event-beachball
""""""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context station-event-beachball [-h] --input INPUT
                                                      --output OUTPUT
                                                      [--table TABLE]
                                                      [--kwargs [KWARGS ...]]
                                                      [--kwargs-json KWARGS_JSON]
                                                      [--stations STATIONS]
                                                      [--config CONFIG]
                                                      [--run-scenario RUN_SCENARIO]
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
   * - ``--input``
     - Yes
     - 
     - Value: ``input``. Input CSV/parquet table for the events_df argument.
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
   * - ``--stations``
     - No
     - 
     - Value: ``stations``. Convenience table path for the stations_df argument.
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

.. _cli-svtk-visualize-context-station-event-context:

svtk visualize context station-event-context
""""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context station-event-context [-h] --input INPUT
                                                    --output OUTPUT
                                                    [--table TABLE]
                                                    [--kwargs [KWARGS ...]]
                                                    [--kwargs-json KWARGS_JSON]
                                                    [--events EVENTS]
                                                    [--config CONFIG]
                                                    [--run-scenario RUN_SCENARIO]
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
   * - ``--input``
     - Yes
     - 
     - Value: ``input``. Input CSV/parquet table for the stations_df argument.
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
   * - ``--events``
     - No
     - 
     - Value: ``events``. Convenience table path for the events_df argument.
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

.. _cli-svtk-visualize-context-station-event-network:

svtk visualize context station-event-network
""""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context station-event-network [-h] --input INPUT
                                                    --output OUTPUT
                                                    [--table TABLE]
                                                    [--kwargs [KWARGS ...]]
                                                    [--kwargs-json KWARGS_JSON]
                                                    [--events EVENTS]
                                                    [--config CONFIG]
                                                    [--run-scenario RUN_SCENARIO]
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
   * - ``--input``
     - Yes
     - 
     - Value: ``input``. Input CSV/parquet table for the stations_df argument.
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
   * - ``--events``
     - No
     - 
     - Value: ``events``. Convenience table path for the events_df argument.
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

.. _cli-svtk-visualize-context-study-domain:

svtk visualize context study-domain
"""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize context study-domain [-h] --input INPUT --output OUTPUT
                                           [--table TABLE]
                                           [--kwargs [KWARGS ...]]
                                           [--kwargs-json KWARGS_JSON]
                                           [--events EVENTS] [--config CONFIG]
                                           [--run-scenario RUN_SCENARIO]
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
     - Value: ``input``. Input CSV/parquet table for the stations_df argument.
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
   * - ``--events``
     - No
     - 
     - Value: ``events``. Convenience table path for the events_df argument.
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

   svtk visualize waveforms event-radial-trace-section [-h] --input INPUT
                                                           --output OUTPUT
                                                           [--table TABLE]
                                                           [--kwargs [KWARGS ...]]
                                                           [--kwargs-json KWARGS_JSON]
                                                           [--config CONFIG]
                                                           [--run-scenario RUN_SCENARIO]
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
   * - ``--input``
     - Yes
     - 
     - Value: ``input``. Input CSV/parquet table for the records_df argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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
       [-h] --input INPUT --output OUTPUT [--table TABLE]
       [--kwargs [KWARGS ...]] [--kwargs-json KWARGS_JSON] [--config CONFIG]
       [--run-scenario RUN_SCENARIO] [--bounds BOUNDS] [--no-basemap]
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
     - Value: ``input``. Input CSV/parquet table for the records_df argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

.. _cli-svtk-visualize-waveforms-record-section:

svtk visualize waveforms record-section
"""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize waveforms record-section [-h] --input INPUT --output
                                               OUTPUT [--table TABLE]
                                               [--kwargs [KWARGS ...]]
                                               [--kwargs-json KWARGS_JSON]
                                               [--config CONFIG]
                                               [--run-scenario RUN_SCENARIO]
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
   * - ``--input``
     - Yes
     - 
     - Value: ``input``. Input CSV/parquet table for the records argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

.. _cli-svtk-visualize-waveforms-station-event-waveform-map:

svtk visualize waveforms station-event-waveform-map
"""""""""""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize waveforms station-event-waveform-map [-h] --input INPUT
                                                           --output OUTPUT
                                                           [--table TABLE]
                                                           [--kwargs [KWARGS ...]]
                                                           [--kwargs-json KWARGS_JSON]
                                                           [--config CONFIG]
                                                           [--run-scenario RUN_SCENARIO]
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
   * - ``--input``
     - Yes
     - 
     - Value: ``input``. Input CSV/parquet table for the records_df argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

.. _cli-svtk-visualize-waveforms-waveform-overlay-matrix:

svtk visualize waveforms waveform-overlay-matrix
""""""""""""""""""""""""""""""""""""""""""""""""

.. rubric:: Usage

.. code-block:: bash

   svtk visualize waveforms waveform-overlay-matrix [-h] --input INPUT
                                                        --output OUTPUT
                                                        [--table TABLE]
                                                        [--kwargs [KWARGS ...]]
                                                        [--kwargs-json KWARGS_JSON]
                                                        [--config CONFIG]
                                                        [--run-scenario RUN_SCENARIO]
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
   * - ``--input``
     - Yes
     - 
     - Value: ``input``. Input CSV/parquet table for the records_df argument.
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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Optional Spatial-VTK config for named bounds.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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
