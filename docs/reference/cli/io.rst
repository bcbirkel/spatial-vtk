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

   svtk io inventory [-h] [--observed-root PATH] [--synthetic-root PATH]
                         [--output PATH] [--config PATH]
                         [--run-scenario RUN_SCENARIO] [--suffix SUFFIX]
                         [--relative-to DIR] [--no-sha256]

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
     - Filesystem path. Observed waveform directory or path template. Defaults to paths.observed_root or paths.observed_template from config.
   * - ``--synthetic-root``
     - No
     -
     - Filesystem path. Synthetic waveform directory or path template. Defaults to paths.synthetic_root or paths.synthetic_template from config.
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
     - Apply one named run_scenarios overlay.
   * - ``--suffix``
     - No
     - Repeatable
     - Waveform suffix to include. May be repeated.
   * - ``--relative-to``
     - No
     -
     - Directory path. Base path used for relative inventory paths.
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

   svtk io prepare-event-stations [-h] [--event-station-table PATH]
                                      [--station-table PATH]
                                      [--event-table PATH]
                                      [--event-station-records-output PATH]
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
   * - ``--event-station-table``, ``--input``
     - No
     -
     - Filesystem path. Event-station CSV/parquet table. Defaults to config paths.event_station_table when that file exists; otherwise all station/event pairs are built. Prefer --event-station-table; --input is a legacy alias.
   * - ``--station-table``, ``--stations``
     - No
     -
     - Filesystem path. Station metadata table. Defaults to prepared_stations, then config paths.station_metadata. Prefer --station-table; --stations is a legacy alias.
   * - ``--event-table``, ``--events``
     - No
     -
     - Filesystem path. Event metadata table. Defaults to prepared_events, then config paths.event_metadata. Prefer --event-table; --events is a legacy alias.
   * - ``--event-station-records-output``, ``--output``
     - No
     -
     - Filesystem path. Event-station records output CSV/parquet table. Defaults to configured output table 'event_station_records'. Prefer --event-station-records-output; --output is a legacy alias.
   * - ``--config``
     - No
     -
     - Filesystem path. Spatial-VTK config file used to resolve default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.

.. _cli-svtk-io-prepare-events:

svtk io prepare-events
^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk io prepare-events [-h] [--event-metadata-table PATH]
                              [--prepared-events-output PATH] [--config PATH]
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
   * - ``--event-metadata-table``, ``--input``
     - No
     -
     - Filesystem path. Event metadata CSV/parquet table. Defaults to config paths.event_metadata. Prefer --event-metadata-table; --input is a legacy alias.
   * - ``--prepared-events-output``, ``--output``
     - No
     -
     - Filesystem path. Prepared event metadata output CSV/parquet table. Defaults to configured output table 'prepared_events'. Prefer --prepared-events-output; --output is a legacy alias.
   * - ``--config``
     - No
     -
     - Filesystem path. Spatial-VTK config file used to resolve default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.

.. _cli-svtk-io-prepare-stations:

svtk io prepare-stations
^^^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk io prepare-stations [-h] [--station-metadata-table PATH]
                                [--prepared-stations-output PATH]
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
   * - ``--station-metadata-table``, ``--input``
     - No
     -
     - Filesystem path. Station metadata CSV/parquet table. Defaults to config paths.station_metadata. Prefer --station-metadata-table; --input is a legacy alias.
   * - ``--prepared-stations-output``, ``--output``
     - No
     -
     - Filesystem path. Prepared station metadata output CSV/parquet table. Defaults to configured output table 'prepared_stations'. Prefer --prepared-stations-output; --output is a legacy alias.
   * - ``--config``
     - No
     -
     - Filesystem path. Spatial-VTK config file used to resolve default input/output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay.

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
     - Apply one named run_scenarios overlay.
   * - ``--observed-column``
     - No
     -
     - Observed waveform path column. Auto-detected when omitted.
   * - ``--synthetic-column``
     - No
     -
     - Synthetic waveform path column. Auto-detected when omitted.
   * - ``--event-id-col``
     - No
     - Default: ``event_id``
     - Event ID column in --records.
   * - ``--lowpass-hz``
     - No
     -
     - Optional lowpass cutoff in Hz.
   * - ``--highpass-hz``
     - No
     -
     - Optional highpass cutoff in Hz.
   * - ``--bandpass-low-hz``
     - No
     -
     - Optional bandpass low corner in Hz.
   * - ``--bandpass-high-hz``
     - No
     -
     - Optional bandpass high corner in Hz.
   * - ``--resample-hz``
     - No
     -
     - Optional target sampling rate in Hz.
   * - ``--filter-order``
     - No
     -
     - Butterworth filter order.
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
