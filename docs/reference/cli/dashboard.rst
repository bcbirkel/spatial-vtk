.. _cli-svtk-dashboard:

svtk dashboard
==============

Config-Backed Dashboards
------------------------

Dashboard commands can resolve their standard datasets from the active config. The metrics dashboard uses configured dashboard outputs such as ``metrics_dashboard`` and ``dashboard_summaries`` when you pass ``--config`` or set a default config with ``svtk config set``. Only pass explicit paths when you want to override those configured outputs. Prefer ``--metrics-dataset-dir`` and ``--dashboard-summary-table-dir`` for those overrides; ``--metrics-root``, ``--metrics-dataset``, ``--summary-root``, and ``--dashboard-summary-dir`` are legacy aliases.

.. code-block:: bash

   svtk dashboard status --config runs/spatial_vtk_config.yaml
   svtk dashboard metrics --config runs/spatial_vtk_config.yaml --auto-port --proxy-mode

Use ``--auto-port`` when another Streamlit server may already be running and ``--proxy-mode`` when launching through a proxied notebook or remote desktop service.

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

   svtk dashboard qc [-h] [--config PATH] [--run-scenario RUN_SCENARIO]
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
     - Filesystem path. Spatial-VTK config used to find the default trace-summary output.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--trace-summary``, ``--qc-trace-summary``
     - No
     -
     - Filesystem path. QC trace-summary CSV/parquet table. Defaults to the configured output table 'qc_trace_summary'.
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

   svtk dashboard metrics [-h] [--config PATH]
                              [--run-scenario RUN_SCENARIO]
                              [--metrics-dataset-dir PATH]
                              [--dashboard-summary-table-dir DIR]
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
     - Filesystem path. Spatial-VTK config used to find default dashboard outputs.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--metrics-dataset-dir``, ``--metrics-root``, ``--metrics-dataset``
     - No
     -
     - Filesystem path. Metrics dashboard row dataset directory or direct metrics_long CSV/parquet table (the row-level data used by metric filters, station/event maps, and detail tables). Defaults to configured dashboard output key 'metrics_dashboard' when --config is passed or a default config is set with 'svtk config set'. Prefer --metrics-dataset-dir; --metrics-root and --metrics-dataset are legacy aliases.
   * - ``--dashboard-summary-table-dir``, ``--summary-root``, ``--dashboard-summary-dir``
     - No
     -
     - Directory path. Dashboard summary-table directory containing model_metric_band, station_rollup, event_rollup, and path_hex CSV/parquet tables for dashboard overview tabs. Defaults to configured dashboard output key 'dashboard_summaries' when --config is passed or a default config is set with 'svtk config set'. Prefer --dashboard-summary-table-dir; --summary-root and --dashboard-summary-dir are legacy aliases.
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

   svtk dashboard status [-h] [--config PATH]
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
     - Filesystem path. Spatial-VTK config used to resolve dashboard inputs.
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
