.. _cli-svtk-metrics:

svtk metrics
============

Command Tree
------------

- :ref:`svtk metrics <cli-svtk-metrics>`
   - :ref:`svtk metrics batch-status <cli-svtk-metrics-batch-status>`
   - :ref:`svtk metrics cache-waveforms <cli-svtk-metrics-cache-waveforms>`
   - :ref:`svtk metrics estimate <cli-svtk-metrics-estimate>`
   - :ref:`svtk metrics inventories <cli-svtk-metrics-inventories>`
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

   svtk metrics [-h]
                    {inventories,plan,estimate,run,run-batch,batch-status,cache-waveforms,merge-batches,outputs,slurm}
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

.. _cli-svtk-metrics-batch-status:

svtk metrics batch-status
^^^^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk metrics batch-status [-h] [--manifest PATH] [--config CONFIG]
                                 [--run-scenario RUN_SCENARIO]
                                 [--missing-limit MISSING_LIMIT] [--json]

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
     - No
     -
     - Filesystem path. Metric workflow manifest JSON. Defaults to metric_manifest_cached when it exists, otherwise metric_manifest.
   * - ``--config``
     - No
     -
     - Value: ``config``. Spatial-VTK config used to resolve the default manifest path.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--missing-limit``
     - No
     - Default: ``20``
     - Value: ``missing_limit``. Maximum missing batch outputs to list. Use -1 for all.
   * - ``--json``
     - No
     - Flag
     - Print JSON instead of YAML.

.. _cli-svtk-metrics-cache-waveforms:

svtk metrics cache-waveforms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk metrics cache-waveforms [-h] [--manifest PATH] [--output PATH]
                                    [--cache-root DIR]
                                    [--batch-output-dir DIR] [--config CONFIG]
                                    [--run-scenario RUN_SCENARIO]
                                    [--overwrite] [--compressed] [--verbose]
                                    [--progress-interval PROGRESS_INTERVAL]

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
     - No
     -
     - Filesystem path. Source metric workflow manifest JSON. Defaults to configured output table 'metric_manifest'.
   * - ``--output``
     - No
     -
     - Filesystem path. Cached metric workflow manifest JSON. Defaults to configured output table 'metric_manifest_cached'.
   * - ``--cache-root``
     - No
     -
     - Directory path. Directory for cached metric-ready waveform .npz files. Defaults to outputs/metric_ready_waveform_cache.
   * - ``--batch-output-dir``
     - No
     -
     - Directory path. Batch output directory for the cached manifest. Defaults to outputs/metric_batches_cached.
   * - ``--config``
     - No
     -
     - Value: ``config``. Spatial-VTK config used to resolve default paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--overwrite``
     - No
     - Flag
     - Rewrite existing cached waveform files.
   * - ``--compressed``
     - No
     - Flag
     - Write compressed .npz files instead of faster uncompressed .npz files.
   * - ``--verbose``
     - No
     - Flag
     - Print progress while materializing waveform traces.
   * - ``--progress-interval``
     - No
     - Default: ``100``
     - Value: ``progress_interval``. Task interval for verbose progress messages.

.. _cli-svtk-metrics-estimate:

svtk metrics estimate
^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk metrics estimate [-h] [--tasks PATH] [--manifest PATH]
                             [--config CONFIG] [--run-scenario RUN_SCENARIO]
                             [--output PATH]
                             [--seconds-per-task SECONDS_PER_TASK]
                             [--memory-gb-per-task MEMORY_GB_PER_TASK]
                             [--cpus-per-task CPUS_PER_TASK]
                             [--parallel-tasks PARALLEL_TASKS]

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
     - No
     -
     - Filesystem path. Metric task CSV/parquet path. Overrides --manifest.
   * - ``--manifest``
     - No
     -
     - Filesystem path. Metric workflow manifest JSON. Defaults to configured output table 'metric_manifest'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Spatial-VTK config used to resolve default manifest and output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--output``
     - No
     -
     - Filesystem path. Optional output CSV/parquet path for the estimate table. Defaults to configured output table 'metric_task_estimate' when a config is available.
   * - ``--seconds-per-task``
     - No
     - Default: ``60.0``
     - Value: ``seconds_per_task``. Approximate runtime for one task in seconds.
   * - ``--memory-gb-per-task``
     - No
     - Default: ``2.0``
     - Value: ``memory_gb_per_task``. Approximate memory needed by one task.
   * - ``--cpus-per-task``
     - No
     - Default: ``1``
     - Value: ``cpus_per_task``. CPU cores requested per task.
   * - ``--parallel-tasks``
     - No
     -
     - Value: ``parallel_tasks``. Optional concurrent task count for wall-time estimates.

.. _cli-svtk-metrics-inventories:

svtk metrics inventories
^^^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk metrics inventories [-h] [--trace-metadata PATH]
                                [--observed-output PATH]
                                [--synthetic-output PATH] [--config CONFIG]
                                [--run-scenario RUN_SCENARIO]
                                [--synthetic-model SYNTHETIC_MODEL]
                                [--observed-path-column OBSERVED_PATH_COLUMN]
                                [--synthetic-path-column SYNTHETIC_PATH_COLUMN]
                                [--overwrite] [--verbose]

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
   * - ``--trace-metadata``
     - No
     -
     - Filesystem path. Preprocessed trace metadata CSV/parquet path. Defaults to the configured preprocessing trace_metadata output.
   * - ``--observed-output``, ``--observed-inventory-output``
     - No
     -
     - Filesystem path. Observed metric waveform inventory output CSV/parquet path. Defaults to configured output table 'observed_metric_inventory'.
   * - ``--synthetic-output``, ``--synthetic-inventory-output``
     - No
     -
     - Filesystem path. Synthetic metric waveform inventory output CSV/parquet path. Defaults to configured output table 'synthetic_metric_inventory'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Optional Spatial-VTK config used to infer a single synthetic model.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--synthetic-model``
     - No
     -
     - Value: ``synthetic_model``. Synthetic model label override.
   * - ``--observed-path-column``
     - No
     - Default: ``output_file``
     - Value: ``observed_path_column``. Trace metadata column used for observed waveform_path.
   * - ``--synthetic-path-column``
     - No
     - Default: ``input_file``
     - Value: ``synthetic_path_column``. Trace metadata column used for synthetic waveform_path.
   * - ``--overwrite``
     - No
     - Flag
     - Replace existing inventory outputs.
   * - ``--verbose``
     - No
     - Flag
     - Print row counts and output paths.

.. _cli-svtk-metrics-merge-batches:

svtk metrics merge-batches
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk metrics merge-batches [-h] [--manifest PATH] [--output PATH]
                                  [--config CONFIG]
                                  [--run-scenario RUN_SCENARIO]
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
     - No
     -
     - Filesystem path. Metric workflow manifest JSON. Defaults to metric_manifest_cached when it exists, otherwise metric_manifest.
   * - ``--output``
     - No
     -
     - Filesystem path. Merged output CSV/parquet path. If an existing directory or directory-style path is passed, writes metric_rows.parquet inside it. Defaults to configured output table 'metric_rows'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Spatial-VTK config used to resolve default paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--allow-missing``
     - No
     - Flag
     - Allow missing batch outputs.

.. _cli-svtk-metrics-outputs:

svtk metrics outputs
^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk metrics outputs [-h] [--metrics PATH] [--output-dir DIR]
                            [--config CONFIG] [--run-scenario RUN_SCENARIO]
                            [--events PATH] [--stations PATH]
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
   * - ``--metrics``, ``--metric-rows``
     - No
     -
     - Filesystem path. Raw metric workflow rows CSV/parquet path. Defaults to configured output table 'metric_rows'.
   * - ``--output-dir``, ``--metrics-output-dir``
     - No
     -
     - Directory path. Ad hoc downstream metric output directory. When omitted, configured output paths are used.
   * - ``--config``
     - No
     -
     - Value: ``config``. Config file used to resolve standard output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--events``, ``--event-table``
     - No
     -
     - Filesystem path. Optional prepared event metadata CSV/parquet path. Defaults to configured output table 'prepared_events' when it exists.
   * - ``--stations``, ``--station-table``
     - No
     -
     - Filesystem path. Optional prepared station metadata CSV/parquet path. Defaults to configured output table 'prepared_stations' when it exists.
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

   svtk metrics plan [-h] [--observed-inventory PATH]
                         [--synthetic-inventory PATH] [--config CONFIG]
                         [--run-scenario RUN_SCENARIO] [--metric METRICS]
                         [--metric-group METRIC_GROUPS]
                         [--component COMPONENTS] [--passband PASSBANDS]
                         [--model MODELS] [--transform TRANSFORMS]
                         [--output-mode OUTPUT_MODE]
                         [--require-source-overlap]
                         [--source-overlap-scope {event,event_station}]
                         [--output PATH] [--manifest] [--batch-output-dir DIR]
                         [--batch-size BATCH_SIZE] [--batch-count BATCH_COUNT]
                         [--qc-table PATH] [--no-qc]
                         [--include-qc-failed-tasks]

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
   * - ``--observed-inventory``, ``--observed-metric-inventory``
     - No
     -
     - Filesystem path. Observed metric waveform inventory CSV/parquet path. Defaults to configured output table 'observed_metric_inventory'.
   * - ``--synthetic-inventory``, ``--synthetic-metric-inventory``
     - No
     -
     - Filesystem path. Synthetic metric waveform inventory CSV/parquet path. Defaults to configured output table 'synthetic_metric_inventory'.
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
   * - ``--require-source-overlap``
     - No
     - Flag
     - Only plan metric tasks for events or event-station rows with both observed and synthetic data.
   * - ``--source-overlap-scope``
     - No
     - Choices: ``event``, ``event_station``
     - Value: ``source_overlap_scope``. Overlap scope for --require-source-overlap.
   * - ``--output``
     - No
     -
     - Filesystem path. Output task table or manifest path. Defaults to configured output table 'metric_manifest' with --manifest, otherwise 'metric_tasks'.
   * - ``--manifest``
     - No
     - Flag
     - Write a JSON manifest instead of a task table.
   * - ``--batch-output-dir``
     - No
     -
     - Directory path. Batch output directory when writing a manifest. Defaults to outputs/metric_batches.
   * - ``--batch-size``
     - No
     - Default: ``100``
     - Value: ``batch_size``. Tasks per batch when writing a manifest.
   * - ``--batch-count``
     - No
     -
     - Value: ``batch_count``. Target number of batches when writing a manifest. Overrides --batch-size.
   * - ``--qc-table``
     - No
     -
     - Filesystem path. Optional QC inventory recorded in a manifest. Defaults to configured output table 'qc_inventory_overlap' when QC is enabled.
   * - ``--no-qc``
     - No
     - Flag
     - Do not mark planned tasks as QC-filtered by default.
   * - ``--include-qc-failed-tasks``
     - No
     - Flag
     - When --qc-table is supplied, keep task keys even if no observed/synthetic metric pair passed QC.

.. _cli-svtk-metrics-run:

svtk metrics run
^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk metrics run [-h] [--tasks PATH] [--output PATH] [--config CONFIG]
                        [--run-scenario RUN_SCENARIO] [--qc-table PATH]

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
   * - ``--tasks``, ``--task-table``
     - No
     -
     - Filesystem path. Metric task table CSV/parquet path. Defaults to configured output table 'metric_tasks'.
   * - ``--output``, ``--metric-rows``
     - No
     -
     - Filesystem path. Metric row output CSV/parquet path. Defaults to configured output table 'metric_rows'.
   * - ``--config``
     - No
     -
     - Value: ``config``. Spatial-VTK config used to resolve default task/output paths.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
   * - ``--qc-table``
     - No
     -
     - Filesystem path. Optional QC inventory.

.. _cli-svtk-metrics-run-batch:

svtk metrics run-batch
^^^^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk metrics run-batch [-h] [--manifest PATH] [--config CONFIG]
                              [--run-scenario RUN_SCENARIO] --batch-index
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
     - No
     -
     - Filesystem path. Metric workflow manifest JSON. Defaults to metric_manifest_cached when it exists, otherwise metric_manifest.
   * - ``--config``
     - No
     -
     - Value: ``config``. Spatial-VTK config used to resolve the default manifest path.
   * - ``--run-scenario``
     - No
     -
     - Value: ``run_scenario``. Apply one named run_scenarios overlay.
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

   svtk metrics slurm [-h] [--manifest PATH] [--output PATH]
                          [--config CONFIG] [--run-scenario RUN_SCENARIO]
                          [--submit] [--incomplete-only] [--overwrite-batches]

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
     - No
     -
     - Filesystem path. Metric workflow manifest JSON. Defaults to metric_manifest_cached when it exists, otherwise metric_manifest.
   * - ``--output``
     - No
     -
     - Filesystem path. Output SLURM script path. Defaults to outputs/slurm/step03_run_metrics.slurm.
   * - ``--config``
     - No
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
   * - ``--incomplete-only``
     - No
     - Flag
     - Only include manifest batches whose output files are missing.
   * - ``--overwrite-batches``
     - No
     - Flag
     - Pass --overwrite to each metric batch task in the Slurm array.
