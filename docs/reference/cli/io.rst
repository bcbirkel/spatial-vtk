.. _cli-svtk-io:

svtk io
=======

Command Tree
------------

- :ref:`svtk io <cli-svtk-io>`
   - :ref:`svtk io inventory <cli-svtk-io-inventory>`
   - :ref:`svtk io master-events <cli-svtk-io-master-events>`
   - :ref:`svtk io master-stations <cli-svtk-io-master-stations>`
   - :ref:`svtk io prepare-event-stations <cli-svtk-io-prepare-event-stations>`
   - :ref:`svtk io prepare-events <cli-svtk-io-prepare-events>`
   - :ref:`svtk io prepare-stations <cli-svtk-io-prepare-stations>`
   - :ref:`svtk io preprocess-waveforms <cli-svtk-io-preprocess-waveforms>`

Command Details
---------------

.. rubric:: Usage

.. code-block:: bash

   svtk io [-h]
               {prepare-stations,prepare-events,prepare-event-stations,master-stations,master-events,inventory,preprocess-waveforms}
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

   svtk io inventory [-h] [--observed-root OBSERVED_ROOT]
                         [--synthetic-root SYNTHETIC_ROOT] [--output PATH]
                         [--config PATH] [--run-scenario RUN_SCENARIO]
                         [--suffix SUFFIX] [--relative-to RELATIVE_TO]
                         [--no-sha256]

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
     - No
     -
     - Directory path. Observed waveform directory or path template. Defaults to paths.observed_root or paths.observed_template from config.
   * - ``--synthetic-root``
     - No
     -
     - Directory path. Synthetic waveform directory or path template. Defaults to paths.synthetic_root or paths.synthetic_template from config.
   * - ``--output``
     - No
     -
     - Filesystem path. Output CSV/parquet path. Defaults to configured output table 'waveform_inventory'.
   * - ``--config``
     - No
     -
     - Filesystem path. Spatial-VTK config file used to resolve default roots and output path.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

   svtk io master-events [-h] --input PATH [PATH ...] --output PATH

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
     - Filesystem path. Event CSV/parquet paths.
   * - ``--output``
     - Yes
     -
     - Filesystem path. Output CSV path.

.. _cli-svtk-io-master-stations:

svtk io master-stations
^^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk io master-stations [-h] --input PATH [PATH ...] --output PATH

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
     - Filesystem path. Station CSV/parquet paths.
   * - ``--output``
     - Yes
     -
     - Filesystem path. Output CSV path.

.. _cli-svtk-io-prepare-event-stations:

svtk io prepare-event-stations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk io prepare-event-stations [-h] [--input PATH] [--stations PATH]
                                      [--events PATH] [--output PATH]
                                      [--config PATH]
                                      [--run-scenario RUN_SCENARIO]

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
     - No
     -
     - Filesystem path. Event-station CSV/parquet path. Defaults to config paths.event_station_table when that file exists; otherwise all station/event pairs are built.
   * - ``--stations``
     - No
     -
     - Filesystem path. Station metadata table. Defaults to prepared_stations, then config paths.station_metadata.
   * - ``--events``
     - No
     -
     - Filesystem path. Event metadata table. Defaults to prepared_events, then config paths.event_metadata.
   * - ``--output``
     - No
     -
     - Filesystem path. Output CSV/parquet path. Defaults to configured output table 'event_station_records'.
   * - ``--config``
     - No
     -
     - Filesystem path. Spatial-VTK config file used to resolve default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.

.. _cli-svtk-io-prepare-events:

svtk io prepare-events
^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk io prepare-events [-h] [--input PATH] [--output PATH]
                              [--config PATH] [--run-scenario RUN_SCENARIO]

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
     - No
     -
     - Filesystem path. Event CSV/parquet path. Defaults to config paths.event_metadata.
   * - ``--output``
     - No
     -
     - Filesystem path. Output CSV/parquet path. Defaults to configured output table 'prepared_events'.
   * - ``--config``
     - No
     -
     - Filesystem path. Spatial-VTK config file used to resolve default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.

.. _cli-svtk-io-prepare-stations:

svtk io prepare-stations
^^^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk io prepare-stations [-h] [--input PATH] [--output PATH]
                                [--config PATH] [--run-scenario RUN_SCENARIO]

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
     - No
     -
     - Filesystem path. Station CSV/parquet path. Defaults to config paths.station_metadata.
   * - ``--output``
     - No
     -
     - Filesystem path. Output CSV/parquet path. Defaults to configured output table 'prepared_stations'.
   * - ``--config``
     - No
     -
     - Filesystem path. Spatial-VTK config file used to resolve default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.

.. _cli-svtk-io-preprocess-waveforms:

svtk io preprocess-waveforms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk io preprocess-waveforms [-h] [--records PATH] [--output-root DIR]
                                    [--config PATH]
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
     - No
     -
     - Filesystem path. Event-station CSV/parquet with waveform path columns. Defaults to configured output table 'event_station_records'.
   * - ``--output-root``
     - No
     -
     - Directory path. Folder where processed waveforms and metadata tables are written. Defaults to outputs.preprocessed_waveforms from config.
   * - ``--config``
     - No
     -
     - Filesystem path. Spatial-VTK config file.
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
