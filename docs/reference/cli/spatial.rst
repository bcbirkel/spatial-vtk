.. _cli-svtk-spatial:

svtk spatial
============

Run spatial-statistics table workflows.

Command Tree
------------

- :ref:`svtk spatial <cli-svtk-spatial>`
   - :ref:`svtk spatial status <cli-svtk-spatial-status>` - Inspect configured spatial-statistics inputs and outputs without running calculations.
   - :ref:`svtk spatial summaries <cli-svtk-spatial-summaries>` - Build standard spatial-statistics summary tables.

Command Details
---------------

.. rubric:: Usage

.. code-block:: bash

   svtk spatial [-h] {status,summaries} ...

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
   * - ``--verbose``
     - No
     - Flag
     - Print elapsed-time progress for Slurm logs.
