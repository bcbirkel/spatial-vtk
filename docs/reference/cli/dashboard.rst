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

   svtk dashboard qc [-h] --trace-summary TRACE_SUMMARY [--port PORT]
                         [--address ADDRESS] [--show]

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
   * - ``--trace-summary``
     - Yes
     - 
     - Value: ``trace_summary``. Trace-summary CSV/parquet path.
   * - ``--port``
     - No
     - Default: ``8502``
     - Value: ``port``. Streamlit server port.
   * - ``--address``
     - No
     - Default: ``127.0.0.1``
     - Value: ``address``. Streamlit server address.
   * - ``--show``
     - No
     - Flag
     - Open Streamlit in a browser when supported.

.. _cli-svtk-dashboard-metrics:

svtk dashboard metrics
^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk dashboard metrics [-h] --metrics-root METRICS_ROOT --summary-root
                              SUMMARY_ROOT [--port PORT] [--address ADDRESS]
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
   * - ``--metrics-root``
     - Yes
     - 
     - Value: ``metrics_root``. Dashboard metric dataset root.
   * - ``--summary-root``
     - Yes
     - 
     - Value: ``summary_root``. Dashboard summary dataset root.
   * - ``--port``
     - No
     - Default: ``8501``
     - Value: ``port``. Streamlit server port.
   * - ``--address``
     - No
     - Default: ``127.0.0.1``
     - Value: ``address``. Streamlit server address.
   * - ``--show``
     - No
     - Flag
     - Open Streamlit in a browser when supported.
