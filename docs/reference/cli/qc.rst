.. _cli-svtk-qc:

svtk qc
=======

Command Tree
------------

- :ref:`svtk qc <cli-svtk-qc>`
   - :ref:`svtk qc build <cli-svtk-qc-build>` - Build standard QC trace, inventory, and overlap tables from the active config.
   - :ref:`svtk qc manual-queue <cli-svtk-qc-manual-queue>`
   - :ref:`svtk qc slurm <cli-svtk-qc-slurm>`
   - :ref:`svtk qc summaries <cli-svtk-qc-summaries>` - Build compact QC summary tables from configured QC inventories.

Command Details
---------------

.. rubric:: Usage

.. code-block:: bash

   svtk qc [-h] {build,manual-queue,slurm,summaries} ...

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

.. _cli-svtk-qc-build:

svtk qc build
^^^^^^^^^^^^^

Build standard QC trace, inventory, and overlap tables from the active config.

.. rubric:: Usage

.. code-block:: bash

   svtk qc build [-h] [--event-stations PATH] [--config PATH]
                     [--run-scenario RUN_SCENARIO]
                     [--qc-trace-summary-output TRACE_OUTPUT]
                     [--qc-inventory-output INVENTORY_OUTPUT]
                     [--qc-overlap-inventory-output OVERLAP_INVENTORY_OUTPUT]
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
   * - ``--event-stations``
     - No
     -
     - Filesystem path. Prepared event-station table. Defaults to configured output table 'event_station_records'.
   * - ``--config``
     - No
     -
     - Filesystem path. Spatial-VTK config file.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.
   * - ``--qc-trace-summary-output``, ``--trace-output``
     - No
     -
     - Filesystem path. Output QC trace-summary table path. Defaults to configured output table 'qc_trace_summary'. Prefer --qc-trace-summary-output; --trace-output is a legacy alias.
   * - ``--qc-inventory-output``, ``--inventory-output``
     - No
     -
     - Output metric QC inventory path. Defaults to configured output table 'qc_inventory'. Prefer --qc-inventory-output; --inventory-output is a legacy alias.
   * - ``--qc-overlap-inventory-output``, ``--overlap-inventory-output``
     - No
     -
     - Output observed/synthetic-overlap metric QC inventory path. Defaults to configured output table 'qc_inventory_overlap'. Prefer --qc-overlap-inventory-output; --overlap-inventory-output is a legacy alias.
   * - ``--verbose``
     - No
     - Flag
     - Print elapsed-time progress messages.

.. _cli-svtk-qc-manual-queue:

svtk qc manual-queue
^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk qc manual-queue [-h] [--trace-summary PATH] [--output PATH]
                            [--config PATH] [--run-scenario RUN_SCENARIO]
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
     - No
     -
     - Filesystem path. Trace-summary CSV/parquet path. Defaults to configured output table 'qc_trace_summary'.
   * - ``--output``
     - No
     -
     - Filesystem path. Output manual-review queue CSV. Defaults to configured output table 'manual_review_queue'.
   * - ``--config``
     - No
     -
     - Filesystem path. Spatial-VTK config used to resolve default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.
   * - ``--event-id``
     - No
     - Default: empty string
     - Optional event id filter.
   * - ``--station-family``
     - No
     - Default: ``all``
     - Optional station-family filter.
   * - ``--component``
     - No
     - Default: ``all``
     - Optional component filter.
   * - ``--station-contains``
     - No
     - Default: empty string
     - Optional station substring filter.
   * - ``--band``
     - No
     -
     - Optional passband filter.

.. _cli-svtk-qc-slurm:

svtk qc slurm
^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk qc slurm [-h] [--event-stations PATH] [--output PATH]
                     [--config PATH] [--run-scenario RUN_SCENARIO]
                     [--qc-trace-summary-output PATH]
                     [--qc-inventory-output PATH]
                     [--qc-overlap-inventory-output PATH] [--submit]

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
   * - ``--event-stations``
     - No
     -
     - Filesystem path. Prepared event-station table. Defaults to configured output table 'event_station_records'.
   * - ``--output``
     - No
     -
     - Filesystem path. Output SLURM script path. Defaults to outputs/slurm/build_qc_inventory.slurm.
   * - ``--config``
     - No
     -
     - Filesystem path. Config file containing compute.slurm or qc.slurm settings.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.
   * - ``--qc-trace-summary-output``, ``--trace-output``
     - No
     -
     - Filesystem path. Output QC trace-summary table path. Defaults to configured output table 'qc_trace_summary'. Prefer --qc-trace-summary-output; --trace-output is a legacy alias.
   * - ``--qc-inventory-output``, ``--inventory-output``
     - No
     -
     - Filesystem path. Output metric QC inventory path. Defaults to configured output table 'qc_inventory'. Prefer --qc-inventory-output; --inventory-output is a legacy alias.
   * - ``--qc-overlap-inventory-output``, ``--overlap-inventory-output``
     - No
     -
     - Filesystem path. Output observed/synthetic-overlap metric QC inventory path. Defaults to configured output table 'qc_inventory_overlap'. Prefer --qc-overlap-inventory-output; --overlap-inventory-output is a legacy alias.
   * - ``--submit``
     - No
     - Flag
     - Submit the script with sbatch after writing it.

.. _cli-svtk-qc-summaries:

svtk qc summaries
^^^^^^^^^^^^^^^^^

Build compact QC summary tables from configured QC inventories.

.. rubric:: Usage

.. code-block:: bash

   svtk qc summaries [-h] [--config PATH] [--run-scenario RUN_SCENARIO]
                         [--chunksize CHUNKSIZE] [--overwrite] [--verbose]

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
     - Filesystem path. Spatial-VTK config file.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.
   * - ``--chunksize``
     - No
     - Default: ``1000000``
     - Rows per streamed QC chunk.
   * - ``--overwrite``
     - No
     - Flag
     - Replace existing disk-backed summary outputs.
   * - ``--verbose``
     - No
     - Flag
     - Print chunked progress messages.
