Configuration
=============

Spatial-VTK can read one project configuration file so your notebooks,
scripts, and CLI commands do not need long path lists or repeated settings.
Use it for project paths, output folders, named map bounds, metric choices,
synthetic frequency limits, waveform preprocessing, and defaults you want to
reuse across workflows.
The top-level sections are the defaults for your project. Optional
``run_scenarios`` let you reuse a focused set of overrides for a particular
analysis without editing the main config.

Start With This Example
-----------------------

Save a config file such as ``spatial-vtk.yaml`` in your project folder, then
edit the paths and settings for your data. The comments in this example are
meant to show what each section is for.

The downloadable example includes a ``tutorial`` run scenario that points at
the lightweight LA Basin metadata committed in ``data/examples/``. That
scenario still expects you to download or generate the companion waveform
bundle before you run the full notebooks.

:download:`Download example_spatial_vtk_config.yaml <../data/examples/configuration/example_spatial_vtk_config.yaml>`

.. literalinclude:: ../data/examples/configuration/example_spatial_vtk_config.yaml
   :language: yaml

Choose Metric Groups Or Metrics
-------------------------------

In the ``metrics`` section, choose either ``groups`` or ``metrics``. Do not set
both for the same run.

``groups: all`` calculates every available metric. You can also choose from
``duration`` (``arias_duration``, ``energy_duration``), ``amplitude`` (``PGA``,
``PGV``, ``PGD``), ``spectral`` (``PSA``, ``FAS``), ``intensity``
(``arias_intensity``, ``energy_intensity``, ``CAV``), ``delay``
(``traveltime_delay``), and ``cross_correlation`` (``original_cc``,
``delay_corrected_cc``).

``metrics: all`` also calculates every available metric. Use ``metrics`` when
you want a short custom list, such as ``[PGA, PSA, original_cc]``.

Set Waveform Preprocessing
--------------------------

If your observed data and synthetics need the same preprocessing before they
are comparable, put that in ``waveforms.preprocessing``. For example, the
tutorial LA Basin scenario lowpasses both observed and synthetic waveforms at
1 Hz:

.. code-block:: yaml

   waveforms:
     preprocessing:
       lowpass_hz: 1.0
       highpass_hz:
       bandpass_low_hz:
       bandpass_high_hz:
       resample_hz:
       filter_order: 4

Leave the cutoff and resampling values empty when your input waveforms are
already filtered and sampled the way you want. Use either
``bandpass_low_hz``/``bandpass_high_hz`` or separate ``highpass_hz`` and
``lowpass_hz`` settings. ``resample_hz`` writes traces at a new sampling rate
after filtering.

For a full run, preprocess the waveform files once and point later QC, metric,
dashboard, and figure steps at the saved processed files:

.. code-block:: bash

   svtk io preprocess-waveforms \
     --config spatial-vtk.yaml \
     --run-scenario tutorial \
     --records data/metadata/event_station_records.csv

The command writes processed waveforms, a preprocessing manifest, trace
metadata, and an updated event-station table under
``outputs.preprocessed_waveforms``. You can pass ``--output-root`` when you
want to write one run somewhere else. Spatial-VTK only filters or resamples
waveforms when your config, run scenario, Python call, or CLI override asks it
to.

Set Automatic QC Thresholds
---------------------------

Automatic waveform QC can use project-specific thresholds from ``qc.automatic``.
These settings are used when you ask Spatial-VTK to inspect waveform files
before metric calculations:

.. code-block:: yaml

   qc:
     automatic:
       min_record_length_s: 60.0
       min_end_after_origin_s: 60.0
       snr_threshold: 3.0

Use these as starting values, then tune them for the record lengths, noise
windows, and signal levels in your project.

Submit Heavy Work To Slurm
--------------------------

Long-running QC and metric workflows can run locally from notebooks, or you
can write a Slurm batch script from the same config. Put shared cluster
defaults in ``compute.slurm``:

.. code-block:: yaml

   compute:
     slurm:
       python_command: python
       environment_setup:
         - module load mamba
         - mamba activate spatial-vtk-py312
       partition: main
       account: my_account
       walltime: 12:00:00
       memory: 16G
       cpus_per_task: 1
       max_concurrent: 10
       log_dir: outputs/logs

Task-specific sections such as ``qc.slurm`` and ``metrics.slurm`` override
only the values you set there. For example, use more memory for QC inventory
generation without changing metric task arrays:

.. code-block:: yaml

   qc:
     slurm:
       job_name: svtk-qc
       walltime: 24:00:00
       memory: 32G

   metrics:
     slurm:
       job_name: svtk-metrics
       walltime: 24:00:00
       memory: 32G

Write a QC inventory Slurm script:

.. code-block:: bash

   svtk qc slurm \
     --config spatial-vtk.yaml \
     --event-stations outputs/tables/event_station_records.csv \
     --output outputs/slurm/build_qc.slurm

Submit it in the same command when your login node can run ``sbatch``:

.. code-block:: bash

   svtk qc slurm \
     --config spatial-vtk.yaml \
     --event-stations outputs/tables/event_station_records.csv \
     --output outputs/slurm/build_qc.slurm \
     --submit

QC Slurm jobs call the same checkpointed builders used in Python, so rerunning
the job resumes from the saved ``qc_trace_summary`` and ``qc_inventory`` tables
when those checkpoint paths already exist.

Metric Slurm jobs run as task arrays from a manifest produced by the metric
workflow. After creating the manifest, write or submit the array script:

.. code-block:: bash

   svtk metrics slurm \
     --config spatial-vtk.yaml \
     --manifest outputs/metrics/metric_manifest.json \
     --output outputs/slurm/run_metrics.slurm \
     --submit

Show Or Hide Notebook Run Times
-------------------------------

The tutorial notebooks register a Spatial-VTK cell timer once near the top of
the notebook. After that, each code cell prints one compact line, such as
``Run time: 19.2 ms``. You can turn those lines off in the config:

.. code-block:: yaml

   notebooks:
     show_cell_timing: false

Leave this set to ``true`` when you want the notebooks to show how long each
step took on your machine.

Point Spatial-VTK At Your Config
--------------------------------

Spatial-VTK looks for a config file in this order:

1. A path you pass directly, such as ``--config spatial-vtk.yaml``.
2. The ``SVTK_CONFIG_FILE`` environment variable.
3. A standard filename in your current folder or one of its parent folders:
   ``spatial-vtk.yaml``, ``spatial-vtk.yml``, ``svtk_config.yaml``,
   ``svtk_config.yml``, ``svtk.yaml``, or ``svtk.yml``.

For a one-time command, pass the file directly:

.. code-block:: bash

   svtk config show --config spatial-vtk.yaml
   svtk metrics plan --config spatial-vtk.yaml --observed-inventory observed.parquet --synthetic-inventory synthetic.parquet --output outputs/tasks.csv

For a whole terminal session, set the environment variable:

.. code-block:: bash

   export SVTK_CONFIG_FILE=/path/to/spatial-vtk.yaml
   svtk config find

In a notebook or script, load the same file with Python:

.. code-block:: python

   from spatial_vtk.config import SpatialVTKConfig

   cfg = SpatialVTKConfig.from_file("spatial-vtk.yaml")
   metrics_path = cfg.path("outputs.metrics")

Use Configs In Python
---------------------

Spatial-VTK supports three Python patterns. Use the one that best matches how
you are working.

If you want short notebook cells, activate the config once near the top of the
notebook. Plotting, table-reading, table-writing, and metric-setting helpers
will use that active config when you do not pass paths or config objects.

.. code-block:: python

   from spatial_vtk.config import SpatialVTKConfig
   from spatial_vtk.config.metrics import metrics_settings_from_config
   from spatial_vtk.io import load_output_table
   from spatial_vtk.io import prepare_station_metadata
   from spatial_vtk.visualize.context import plot_record_coverage

   cfg = SpatialVTKConfig.from_file("spatial-vtk.yaml", run_scenario="tutorial").activate()

   stations = prepare_station_metadata()
   metrics = load_output_table("metrics_enriched")
   metric_settings = metrics_settings_from_config()
   plot_record_coverage(record_coverage, showfig=True, savefig=True)

If you prefer each call to be self-contained, pass the config directly.

.. code-block:: python

   from spatial_vtk.config import SpatialVTKConfig
   from spatial_vtk.config import resolve_output_path

   cfg = SpatialVTKConfig.from_file("spatial-vtk.yaml", run_scenario="tutorial")
   path = resolve_output_path("record_coverage", kind="figure", cfg=cfg)

For CLI workflows, set ``SVTK_CONFIG_FILE`` in your shell and let commands
discover it.

.. code-block:: bash

   export SVTK_CONFIG_FILE=/path/to/spatial-vtk.yaml
   svtk config find

Default Output Names
--------------------

Keep your main config focused on folders:

.. code-block:: yaml

   outputs:
     root: outputs
     tables: outputs/tables
     figures: outputs/figures
     dashboards: outputs/dashboards

Spatial-VTK keeps default table and figure filenames in its package defaults,
so notebooks do not need long filename lists. For example,
``plot_record_coverage(..., savefig=True)`` writes
``outputs/figures/record_coverage.png`` when that key is not overridden.
Likewise, ``write_output_table("prepared_stations", stations)`` writes
``outputs/tables/prepared_stations.csv``.

When a workflow step creates several standard tables, write them by output key
and let the next step read them the same way:

.. code-block:: python

   from spatial_vtk.io import load_output_table, write_output_tables

   write_output_tables(
       prepared_stations=stations,
       prepared_events=events,
       event_station_records=event_stations,
   )

   stations = load_output_table("prepared_stations")

You can still override a single output directly:

.. code-block:: python

   plot_record_coverage(record_coverage, savefig=True, outpath="figures/custom_record_coverage.png")

The explicit ``outpath`` wins over the active config and package defaults.

Use A Run Scenario
------------------

The main config file should hold the defaults you normally want. If you need a
repeatable variation, add it under ``run_scenarios``. A scenario is a small
overlay: any section inside the scenario replaces or extends the same section
from the main config.

Use a scenario from the CLI:

.. code-block:: bash

   svtk config show --config spatial-vtk.yaml --run-scenario quick_amplitude_check --section metrics
   svtk metrics plan --config spatial-vtk.yaml --run-scenario quick_amplitude_check --observed-inventory observed.parquet --synthetic-inventory synthetic.parquet --output outputs/quick_tasks.csv

Use the same scenario in Python:

.. code-block:: python

   from spatial_vtk.config import SpatialVTKConfig
   from spatial_vtk.io import metric_plan_from_config

   cfg = SpatialVTKConfig.from_file("spatial-vtk.yaml", run_scenario="quick_amplitude_check")
   plan = metric_plan_from_config(cfg)

Override One Run
----------------

You can also override one setting for a single CLI or notebook run. This is
useful when you want to try something quickly without changing your config
file.

For example, this CLI command uses the config file but calculates only PGA on
the Z component for this run:

.. code-block:: bash

   svtk metrics plan --config spatial-vtk.yaml --metric PGA --component Z --observed-inventory observed.parquet --synthetic-inventory synthetic.parquet --output outputs/pga_z_tasks.csv

And this map command uses a named bounds override from the config:

.. code-block:: bash

   svtk map spatial station-metric --config spatial-vtk.yaml --bounds specific_area_of_interest --input metrics.parquet --output figures/station_metric_map.png

In a notebook, pass an override dictionary to the metric-plan helper:

.. code-block:: python

   cfg = SpatialVTKConfig.from_file("spatial-vtk.yaml")
   plan = metric_plan_from_config(
       cfg,
       overrides={
           "metrics": ["PGA"],
           "components": ["Z"],
       },
   )

How Values Are Chosen
---------------------

Most workflows use this precedence:

1. Explicit CLI arguments, notebook variables, or function arguments for the
   current run.
2. The selected ``run_scenarios`` overlay, if you selected one.
3. Top-level sections such as ``paths``, ``outputs``, ``metrics``, and
   ``synthetics``.
4. Package defaults.

If you pass a specific CLI argument such as ``--metric`` or set an override in
a notebook, that explicit value wins for that run. If you select
``--run-scenario quick_amplitude_check``, that scenario overrides the main
config defaults before the command runs.

Check The Current Settings
--------------------------

Use these quick checks when you are not sure which file or values are active:

.. code-block:: bash

   # Show which config file Spatial-VTK found.
   svtk config find

   # Print the full config file after YAML parsing.
   svtk config show

   # Print one section.
   svtk config show --section metrics
   svtk config show --run-scenario quick_amplitude_check --section metrics

   # List named map/station bounds from inline config and bounds CSV files.
   svtk config bounds

For metric workflows, you can also inspect the resolved plan in Python:

.. code-block:: python

   from spatial_vtk.config import SpatialVTKConfig
   from spatial_vtk.io import metric_plan_from_config

   cfg = SpatialVTKConfig.from_file("spatial-vtk.yaml")
   plan = metric_plan_from_config(cfg, command="metrics.calculate")
   print(plan)

If a value appears in ``svtk config show``, it came from your config file. If a
value appears only after you add ``--run-scenario``, it came from that selected
scenario. If a value only appears in a command you typed or an override
dictionary you passed in a notebook, it is an override for that run. If none of
those places set it, Spatial-VTK falls back to its package defaults.
