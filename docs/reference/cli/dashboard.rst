.. _cli-svtk-dashboard:

svtk dashboard
==============

Command Tree
------------

- :ref:`svtk dashboard <cli-svtk-dashboard>`
   - :ref:`svtk dashboard qc <cli-svtk-dashboard-qc>`
   - :ref:`svtk dashboard metrics <cli-svtk-dashboard-metrics>`

Command Details
---------------

.. rubric:: Usage

.. code-block:: bash

   svtk dashboard [-h] {metrics,qc} ...

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

.. _cli-svtk-dashboard-qc:

svtk dashboard qc
^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk dashboard qc [-h] [--config CONFIG] [--run-scenario RUN_SCENARIO]
                         [--trace-summary TRACE_SUMMARY] [--port PORT]
                         [--address ADDRESS] [--proxy-mode] [--show]

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
     - Value: ``config``. Spatial-VTK config used to find the default trace-summary output.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--trace-summary``
     - No
     -
     - Value: ``trace_summary``. Trace-summary CSV/parquet path. Defaults from config.
   * - ``--port``
     - No
     - Default: ``8502``
     - Value: ``port``. Streamlit server port.
   * - ``--address``
     - No
     - Default: ``127.0.0.1``
     - Value: ``address``. Streamlit server address.
   * - ``--proxy-mode``
     - No
     - Flag
     - Allow access through reverse proxies.
   * - ``--show``
     - No
     - Flag
     - Open Streamlit in a browser when supported.

.. _cli-svtk-dashboard-metrics:

svtk dashboard metrics
^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk dashboard metrics [-h] [--config CONFIG]
                              [--run-scenario RUN_SCENARIO]
                              [--metrics-root METRICS_ROOT]
                              [--summary-root SUMMARY_ROOT] [--port PORT]
                              [--address ADDRESS] [--proxy-mode] [--show]

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
     - Value: ``config``. Spatial-VTK config used to find default dashboard outputs.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--metrics-root``
     - No
     -
     - Value: ``metrics_root``. Dashboard-ready long metric dataset directory or direct CSV/parquet table. Defaults to the configured metrics_dashboard_root output.
   * - ``--summary-root``
     - No
     -
     - Value: ``summary_root``. Dashboard summary table directory. Defaults to the configured dashboard_summary_root output.
   * - ``--port``
     - No
     - Default: ``8501``
     - Value: ``port``. Streamlit server port.
   * - ``--address``
     - No
     - Default: ``127.0.0.1``
     - Value: ``address``. Streamlit server address.
   * - ``--proxy-mode``
     - No
     - Flag
     - Allow access through reverse proxies.
   * - ``--show``
     - No
     - Flag
     - Open Streamlit in a browser when supported.
