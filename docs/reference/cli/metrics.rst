.. _cli-svtk-metrics:

svtk metrics
============

Command Tree
------------

- :ref:`svtk metrics <cli-svtk-metrics>`
   - :ref:`svtk metrics merge-batches <cli-svtk-metrics-merge-batches>`
   - :ref:`svtk metrics outputs <cli-svtk-metrics-outputs>`
   - :ref:`svtk metrics plan <cli-svtk-metrics-plan>`
   - :ref:`svtk metrics run <cli-svtk-metrics-run>`
   - :ref:`svtk metrics run-batch <cli-svtk-metrics-run-batch>`
   - :ref:`svtk metrics slurm <cli-svtk-metrics-slurm>`

Command Details
---------------

.. rubric:: Usage

.. code-block:: bash

   svtk metrics [-h] {plan,run,run-batch,merge-batches,outputs,slurm} ...

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

.. _cli-svtk-metrics-merge-batches:

svtk metrics merge-batches
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk metrics merge-batches [-h] --manifest MANIFEST --output OUTPUT
                                  [--allow-missing]

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
   * - ``--manifest``
     - Yes
     - 
     - Value: ``manifest``. Metric workflow manifest JSON.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Merged output CSV/parquet path.
   * - ``--allow-missing``
     - No
     - Flag
     - Allow missing batch outputs.

.. _cli-svtk-metrics-outputs:

svtk metrics outputs
^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk metrics outputs [-h] --metrics METRICS --output-dir OUTPUT_DIR
                            [--events EVENTS] [--stations STATIONS]
                            [--residual-column RESIDUAL_COLUMN]
                            [--score-column SCORE_COLUMN]
                            [--format {parquet,csv}] [--dashboard-partitioned]

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
   * - ``--metrics``
     - Yes
     - 
     - Value: ``metrics``. Metric workflow rows CSV/parquet path.
   * - ``--output-dir``
     - Yes
     - 
     - Value: ``output_dir``. Output directory.
   * - ``--events``
     - No
     - 
     - Value: ``events``. Optional event metadata CSV/parquet path.
   * - ``--stations``
     - No
     - 
     - Value: ``stations``. Optional station metadata CSV/parquet path.
   * - ``--residual-column``
     - No
     - 
     - Value: ``residual_column``. Column exposed as canonical residual.
   * - ``--score-column``
     - No
     - 
     - Value: ``score_column``. Column exposed as canonical score.
   * - ``--format``
     - No
     - Default: ``parquet``; Choices: ``parquet``, ``csv``
     - Value: ``format``. Table output format.
   * - ``--dashboard-partitioned``
     - No
     - Flag
     - Partition dashboard metric rows.

.. _cli-svtk-metrics-plan:

svtk metrics plan
^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk metrics plan [-h] [--observed-inventory OBSERVED_INVENTORY]
                         [--waveforms-preprocessed]
                         [--synthetic-inventory SYNTHETIC_INVENTORY]
                         [--config CONFIG] [--run-scenario RUN_SCENARIO]
                         [--metric METRICS] [--metric-group METRIC_GROUPS]
                         [--component COMPONENTS] [--passband PASSBANDS]
                         [--model MODELS] [--transform TRANSFORMS]
                         [--output-mode OUTPUT_MODE] --output OUTPUT
                         [--manifest] [--batch-output-dir BATCH_OUTPUT_DIR]
                         [--batch-size BATCH_SIZE] [--qc-table QC_TABLE]
                         [--no-qc]

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
   * - ``--observed-inventory``
     - No
     - 
     - Value: ``observed_inventory``. Observed metric waveform inventory.
   * - ``--waveforms-preprocessed``
     - No
     - Flag
     - Inputs already have configured preprocessing; do not repeat lowpass/resampling.
   * - ``--synthetic-inventory``
     - No
     - 
     - Value: ``synthetic_inventory``. Synthetic metric waveform inventory.
   * - ``--config``
     - No
     - 
     - Value: ``config``. Spatial-VTK config file.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--metric``
     - No
     - Repeatable
     - Value: ``metrics``. Metric override. Repeat or use 'all'.
   * - ``--metric-group``
     - No
     - Repeatable
     - Value: ``metric_groups``. Metric-group override. Repeat or use 'all'.
   * - ``--component``
     - No
     - Repeatable
     - Value: ``components``. Component override. Repeat for multiple components.
   * - ``--passband``
     - No
     - Repeatable
     - Value: ``passbands``. Period passband override, such as 1-2. Repeat for multiple bands.
   * - ``--model``
     - No
     - Repeatable
     - Value: ``models``. Synthetic model override. Repeat for multiple models.
   * - ``--transform``
     - No
     - Repeatable
     - Value: ``transforms``. Metric transform override. Repeat for multiple transforms.
   * - ``--output-mode``
     - No
     - 
     - Value: ``output_mode``. Metric output mode override.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output task table or manifest path.
   * - ``--manifest``
     - No
     - Flag
     - Write a JSON manifest instead of a task table.
   * - ``--batch-output-dir``
     - No
     - 
     - Value: ``batch_output_dir``. Batch output directory when writing a manifest.
   * - ``--batch-size``
     - No
     - Default: ``100``
     - Value: ``batch_size``. Tasks per batch when writing a manifest.
   * - ``--qc-table``
     - No
     - 
     - Value: ``qc_table``. Optional QC inventory recorded in a manifest.
   * - ``--no-qc``
     - No
     - Flag
     - Do not mark planned tasks as QC-filtered by default.

.. _cli-svtk-metrics-run:

svtk metrics run
^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk metrics run [-h] --tasks TASKS --output OUTPUT
                        [--qc-table QC_TABLE]

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
   * - ``--tasks``
     - Yes
     - 
     - Value: ``tasks``. Task CSV/parquet path.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output metric CSV/parquet path.
   * - ``--qc-table``
     - No
     - 
     - Value: ``qc_table``. Optional QC inventory.

.. _cli-svtk-metrics-run-batch:

svtk metrics run-batch
^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk metrics run-batch [-h] --manifest MANIFEST --batch-index
                              BATCH_INDEX [--overwrite]

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
   * - ``--manifest``
     - Yes
     - 
     - Value: ``manifest``. Metric workflow manifest JSON.
   * - ``--batch-index``
     - Yes
     - 
     - Value: ``batch_index``. Batch index to run.
   * - ``--overwrite``
     - No
     - Flag
     - Replace an existing batch output.

.. _cli-svtk-metrics-slurm:

svtk metrics slurm
^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk metrics slurm [-h] --manifest MANIFEST --output OUTPUT --config
                          CONFIG [--run-scenario RUN_SCENARIO] [--submit]

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
   * - ``--manifest``
     - Yes
     - 
     - Value: ``manifest``. Metric workflow manifest JSON.
   * - ``--output``
     - Yes
     - 
     - Value: ``output``. Output SLURM script path.
   * - ``--config``
     - Yes
     - 
     - Value: ``config``. Config file containing metrics.slurm settings.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--submit``
     - No
     - Flag
     - Submit the script with sbatch after writing it.

Spectral waveform processing
----------------------------

PSA and FAS run once per waveform pair/component, independently of configured
passbands. Supply raw acceleration files in ``raw_waveform_path`` in each
inventory; when this optional column is absent, ``waveform_path`` must itself
contain raw records. ``--waveforms-preprocessed`` applies to ordinary metrics;
it does not bypass the spectral lowpass. Tutorial inventories retain both paths.

The spectral branch demeans and cosine-tapers each full raw record (5 percent),
applies one fourth-order zero-phase lowpass at ``synthetics.max_frequency_hz``,
and linearly interpolates the common time window onto a 25 Hz grid. The cutoff
is capped at 45 percent of the input sample rate and at 9.5 Hz when downsampling.
PSA uses 5 percent damping; FAS uses its Hann-windowed amplitude calculation.
The example period grid is 1.5, 2, 2.5, 3, 3.5, 4, 4.5, and 5 seconds.
Both metrics exclude periods less than or equal to the reciprocal simulation
frequency (1 second for a 1 Hz simulation). An entirely unsupported request
raises an error; partially unsupported grids are reduced in the task manifest.

Spectral tasks are labeled ``lowpass 1 Hz`` for this example. They do not inherit
passband QC windows or relative-amplitude rejection at 0.25. Record-length QC
still requires the configured minimum number of cycles, and nonfinite values
cannot yield usable comparisons. Lowpass settings, raw paths, and the actual
common grid are recorded on output rows. These processing records do not establish
physical acceleration units; those still require source calibration provenance.
Existing mixed or bandpassed spectral task manifests must be replanned.
