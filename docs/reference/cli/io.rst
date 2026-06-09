.. _cli-svtk-io:

svtk io
=======

Command Tree
------------

- :ref:`svtk io <cli-svtk-io>`
   - :ref:`svtk io inventory <cli-svtk-io-inventory>`
   - :ref:`svtk io master-events <cli-svtk-io-master-events>`
   - :ref:`svtk io master-stations <cli-svtk-io-master-stations>`
   - :ref:`svtk io prepare-events <cli-svtk-io-prepare-events>`
   - :ref:`svtk io prepare-stations <cli-svtk-io-prepare-stations>`
   - :ref:`svtk io preprocess-waveforms <cli-svtk-io-preprocess-waveforms>`

Command Details
---------------

.. rubric:: Usage

.. code-block:: bash

   svtk io [-h]
               {prepare-stations,prepare-events,master-stations,master-events,inventory,preprocess-waveforms}
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

.. _cli-svtk-io-inventory:

svtk io inventory
^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk io inventory [-h] --observed-root OBSERVED_ROOT --synthetic-root
                         SYNTHETIC_ROOT --output OUTPUT [--suffix SUFFIX]
                         [--relative-to RELATIVE_TO] [--no-sha256]

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
   * - ``--observed-root``
     - Yes
     - 
     - Value: ``observed_root``. Observed waveform root directory.
   * - ``--synthetic-root``
     - Yes
     - 
     - Value: ``synthetic_root``. Synthetic waveform root directory.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output CSV/parquet path.
   * - ``--suffix``
     - No
     - Repeatable
     - Value: ``suffix``. Waveform suffix to include. May be repeated.
   * - ``--relative-to``
     - No
     - 
     - Value: ``relative_to``. Base path used for relative inventory paths.
   * - ``--no-sha256``
     - No
     - Flag
     - Skip SHA-256 hashing.

.. _cli-svtk-io-master-events:

svtk io master-events
^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk io master-events [-h] --input INPUT [INPUT ...] --output OUTPUT

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
     - Nargs: ``+``
     - Value: ``input``. Event CSV/parquet paths.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output CSV path.

.. _cli-svtk-io-master-stations:

svtk io master-stations
^^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk io master-stations [-h] --input INPUT [INPUT ...] --output OUTPUT

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
     - Nargs: ``+``
     - Value: ``input``. Station CSV/parquet paths.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output CSV path.

.. _cli-svtk-io-prepare-events:

svtk io prepare-events
^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk io prepare-events [-h] --input INPUT --output OUTPUT

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
     - Value: ``input``. Event CSV/parquet path.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output CSV/parquet path.

.. _cli-svtk-io-prepare-stations:

svtk io prepare-stations
^^^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk io prepare-stations [-h] --input INPUT --output OUTPUT

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
     - Value: ``input``. Station CSV/parquet path.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output CSV/parquet path.

.. _cli-svtk-io-preprocess-waveforms:

svtk io preprocess-waveforms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk io preprocess-waveforms [-h] --records RECORDS
                                    [--output-root OUTPUT_ROOT]
                                    [--config CONFIG]
                                    [--run-scenario RUN_SCENARIO]
                                    [--observed-column OBSERVED_COLUMN]
                                    [--synthetic-column SYNTHETIC_COLUMN]
                                    [--event-id-col EVENT_ID_COL]
                                    [--lowpass-hz LOWPASS_HZ]
                                    [--highpass-hz HIGHPASS_HZ]
                                    [--bandpass-low-hz BANDPASS_LOW_HZ]
                                    [--bandpass-high-hz BANDPASS_HIGH_HZ]
                                    [--resample-hz RESAMPLE_HZ]
                                    [--filter-order FILTER_ORDER]
                                    [--overwrite] [--continue-on-error]
                                    [--keep-input-columns]

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
   * - ``--records``
     - Yes
     - 
     - Value: ``records``. Event-station CSV/parquet with waveform path columns.
   * - ``--output-root``
     - No
     - 
     - Value: ``output_root``. Folder where processed waveforms and metadata tables are written. Defaults to outputs.preprocessed_waveforms from config.
   * - ``--config``
     - No
     - 
     - Value: ``config``. Spatial-VTK config file.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--observed-column``
     - No
     - 
     - Value: ``observed_column``. Observed waveform path column. Auto-detected when omitted.
   * - ``--synthetic-column``
     - No
     - 
     - Value: ``synthetic_column``. Synthetic waveform path column. Auto-detected when omitted.
   * - ``--event-id-col``
     - No
     - Default: ``event_id``
     - Value: ``event_id_col``. Event ID column in --records.
   * - ``--lowpass-hz``
     - No
     - 
     - Value: ``lowpass_hz``. Optional lowpass cutoff in Hz.
   * - ``--highpass-hz``
     - No
     - 
     - Value: ``highpass_hz``. Optional highpass cutoff in Hz.
   * - ``--bandpass-low-hz``
     - No
     - 
     - Value: ``bandpass_low_hz``. Optional bandpass low corner in Hz.
   * - ``--bandpass-high-hz``
     - No
     - 
     - Value: ``bandpass_high_hz``. Optional bandpass high corner in Hz.
   * - ``--resample-hz``
     - No
     - 
     - Value: ``resample_hz``. Optional target sampling rate in Hz.
   * - ``--filter-order``
     - No
     - 
     - Value: ``filter_order``. Butterworth filter order.
   * - ``--overwrite``
     - No
     - Flag
     - Rewrite processed files even if they already exist.
   * - ``--continue-on-error``
     - No
     - Flag
     - Record failed files in the manifest instead of stopping.
   * - ``--keep-input-columns``
     - No
     - Flag
     - Keep original waveform path columns pointed at raw files.
