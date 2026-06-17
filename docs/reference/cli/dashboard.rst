.. _cli-svtk-dashboard:

svtk dashboard
==============

Command Tree
------------

- :ref:`svtk dashboard <cli-svtk-dashboard>`
   - :ref:`svtk dashboard qc <cli-svtk-dashboard-qc>`
   - :ref:`svtk dashboard metrics <cli-svtk-dashboard-metrics>`
   - :ref:`svtk dashboard status <cli-svtk-dashboard-status>`

Command Details
---------------

.. rubric:: Usage

.. code-block:: bash

   svtk dashboard [-h] {status,metrics,qc} ...

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
                         [--trace-summary PATH] [--port PORT]
                         [--address ADDRESS] [--auto-port] [--proxy-mode]
                         [--show]

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
   * - ``--trace-summary``, ``--qc-trace-summary``
     - No
     -
     - Value: ``PATH``. QC trace-summary CSV/parquet table. Defaults to the configured output table 'qc_trace_summary'.
   * - ``--port``
     - No
     - Default: ``8502``
     - Value: ``port``. Streamlit server port.
   * - ``--address``
     - No
     - Default: ``127.0.0.1``
     - Value: ``address``. Streamlit server address.
   * - ``--auto-port``
     - No
     - Flag
     - Use the first available port at or above --port.
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
                              [--metrics-root PATH] [--summary-root DIR]
                              [--port PORT] [--address ADDRESS] [--auto-port]
                              [--proxy-mode] [--show]

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
   * - ``--metrics-root``, ``--metrics-dataset``
     - No
     -
     - Value: ``PATH``. Dashboard-ready metric dataset directory or direct CSV/parquet table. Defaults to the configured dashboard output key 'metrics_dashboard'.
   * - ``--summary-root``, ``--dashboard-summary-dir``
     - No
     -
     - Value: ``DIR``. Directory containing dashboard summary tables (model_metric_band, station_rollup, event_rollup, path_hex). Defaults to the configured dashboard output key 'dashboard_summaries'.
   * - ``--port``
     - No
     - Default: ``8501``
     - Value: ``port``. Streamlit server port.
   * - ``--address``
     - No
     - Default: ``127.0.0.1``
     - Value: ``address``. Streamlit server address.
   * - ``--auto-port``
     - No
     - Flag
     - Use the first available port at or above --port.
   * - ``--proxy-mode``
     - No
     - Flag
     - Allow access through reverse proxies.
   * - ``--show``
     - No
     - Flag
     - Open Streamlit in a browser when supported.

.. _cli-svtk-dashboard-status:

svtk dashboard status
^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk dashboard status [-h] [--config CONFIG]
                             [--run-scenario RUN_SCENARIO]
                             [--summary-format {parquet,csv}] [--json]

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
     - Value: ``config``. Spatial-VTK config used to resolve dashboard inputs.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--summary-format``
     - No
     - Default: ``parquet``; Choices: ``parquet``, ``csv``
     - Value: ``summary_format``. Expected dashboard summary table format for missing files.
   * - ``--json``
     - No
     - Flag
     - Print machine-readable JSON.
