.. _cli-svtk-qc:

svtk qc
=======

Command Tree
------------

- :ref:`svtk qc <cli-svtk-qc>`
   - :ref:`svtk qc manual-queue <cli-svtk-qc-manual-queue>`

Command Details
---------------

.. rubric:: Usage

.. code-block:: bash

   svtk qc [-h] {manual-queue} ...

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

.. _cli-svtk-qc-manual-queue:

svtk qc manual-queue
^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk qc manual-queue [-h] --trace-summary TRACE_SUMMARY --output OUTPUT
                            [--event-id EVENT_ID]
                            [--station-family STATION_FAMILY]
                            [--component COMPONENT]
                            [--station-contains STATION_CONTAINS]
                            [--band BAND]

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
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output manual-review queue CSV.
   * - ``--event-id``
     - No
     - Default: empty string
     - Value: ``event_id``. Optional event id filter.
   * - ``--station-family``
     - No
     - Default: ``all``
     - Value: ``station_family``. Optional station-family filter.
   * - ``--component``
     - No
     - Default: ``all``
     - Value: ``component``. Optional component filter.
   * - ``--station-contains``
     - No
     - Default: empty string
     - Value: ``station_contains``. Optional station substring filter.
   * - ``--band``
     - No
     - 
     - Value: ``band``. Optional passband filter.
