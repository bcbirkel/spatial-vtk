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

   svtk qc build [-h] [--event-stations EVENT_STATIONS] [--config CONFIG]
                     [--run-scenario RUN_SCENARIO]
                     [--trace-output TRACE_OUTPUT]
                     [--inventory-output INVENTORY_OUTPUT]
                     [--overlap-inventory-output OVERLAP_INVENTORY_OUTPUT]
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
     - Value: ``event_stations``. Prepared event-station table. Defaults to configured output table 'event_station_records'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Spatial-VTK config file.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--trace-output``, ``--qc-trace-summary-output``
     - No
     -
     - Value: ``trace_output``. Output waveform QC table path. Defaults to configured output table 'qc_trace_summary'.
   * - ``--inventory-output``, ``--qc-inventory-output``
     - No
     -
     - Value: ``inventory_output``. Output metric QC inventory path. Defaults to configured output table 'qc_inventory'.
   * - ``--overlap-inventory-output``, ``--qc-overlap-inventory-output``
     - No
     -
     - Value: ``overlap_inventory_output``. Output observed/synthetic-overlap metric QC inventory path. Defaults to configured output table 'qc_inventory_overlap'.
   * - ``--verbose``
     - No
     - Flag
     - Print elapsed-time progress messages.

.. _cli-svtk-qc-manual-queue:

svtk qc manual-queue
^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk qc manual-queue [-h] [--trace-summary TRACE_SUMMARY]
                            [--output OUTPUT] [--config CONFIG]
                            [--run-scenario RUN_SCENARIO]
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
     - Value: ``trace_summary``. Trace-summary CSV/parquet path. Defaults to configured output table 'qc_trace_summary'.
   * - ``--output``
     - No
     -
     - Value: ``output``. Output manual-review queue CSV. Defaults to configured output table 'manual_review_queue'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Spatial-VTK config used to resolve default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

.. _cli-svtk-qc-slurm:

svtk qc slurm
^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk qc slurm [-h] [--event-stations EVENT_STATIONS] [--output OUTPUT]
                     [--config CONFIG] [--run-scenario RUN_SCENARIO]
                     [--trace-output TRACE_OUTPUT]
                     [--inventory-output INVENTORY_OUTPUT]
                     [--overlap-inventory-output OVERLAP_INVENTORY_OUTPUT]
                     [--submit]

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
     - Value: ``event_stations``. Prepared event-station table. Defaults to configured output table 'event_station_records'.
   * - ``--output``
     - No
     -
     - Value: ``output``. Output SLURM script path. Defaults to outputs/slurm/build_qc_inventory.slurm.
   * - ``--config``
     - No
     -
     - Value: ``config``. Config file containing compute.slurm or qc.slurm settings.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--trace-output``, ``--qc-trace-summary-output``
     - No
     -
     - Value: ``trace_output``. Output waveform QC table path. Defaults to configured output table 'qc_trace_summary'.
   * - ``--inventory-output``, ``--qc-inventory-output``
     - No
     -
     - Value: ``inventory_output``. Output metric QC inventory path. Defaults to configured output table 'qc_inventory'.
   * - ``--overlap-inventory-output``, ``--qc-overlap-inventory-output``
     - No
     -
     - Value: ``overlap_inventory_output``. Output observed/synthetic-overlap metric QC inventory path. Defaults to configured output table 'qc_inventory_overlap'.
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

   svtk qc summaries [-h] [--config CONFIG] [--run-scenario RUN_SCENARIO]
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
     - Value: ``config``. Spatial-VTK config file.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--chunksize``
     - No
     - Default: ``1000000``
     - Value: ``chunksize``. Rows per streamed QC chunk.
   * - ``--overwrite``
     - No
     - Flag
     - Replace existing disk-backed summary outputs.
   * - ``--verbose``
     - No
     - Flag
     - Print chunked progress messages.
