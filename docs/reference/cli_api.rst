CLI API
=======

The public command is ``svtk``. It gives you file-based access to the same major Spatial-VTK workflows used from Python: configuration inspection, metadata and waveform preparation, QC queue export, metric planning and execution, plotting, mapping, dashboards, and advanced one-off public-function calls outside the named command groups.

Run ``svtk --help`` to see the command tree from your installed environment.

.. code-block:: bash

   svtk --help
   svtk --version

Config Defaults And Explicit Paths
----------------------------------

Most workflow commands can read default input and output paths from a config file passed with ``--config`` or saved with ``svtk config set``. Use that mode for routine project runs where tables, figures, dashboards, and Slurm scripts should land in the configured output registry.

When a command accepts complete explicit input and output paths, those paths take precedence and the command does not load the saved config unless you also pass ``--config`` or ``--run-scenario``. This keeps one-off status checks, table preparation, metric estimates, batch merges, and manual queue exports usable from minimal terminal environments without requiring project config dependencies.

Commands that need project-level settings, such as waveform templates, preprocessing defaults, Slurm settings, or registered output names, still require a config when those values are not supplied explicitly. If a command reports that no Spatial-VTK config was found, either pass the missing explicit paths or set the project config first:

.. code-block:: bash

   svtk config set spatial-vtk.yaml
   svtk config show
   svtk metrics batch-status --metric-manifest runs/outputs/tables/metric_manifest.json

Command Groups
--------------

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Command
     - What it does
   * - :doc:`svtk config <cli/config>`
     - Inspect Spatial-VTK configuration.
   * - :doc:`svtk io <cli/io>`
     - Prepare metadata and input inventories.
   * - :doc:`svtk qc <cli/qc>`
     - Prepare QC review outputs.
   * - :doc:`svtk metrics <cli/metrics>`
     - Plan, run, and post-process metric calculations.
   * - :doc:`svtk spatial <cli/spatial>`
     - Run spatial-statistics table workflows.
   * - :doc:`svtk plot <cli/plot>`
     - Create static metric and spatial plots.
   * - :doc:`svtk map <cli/map>`
     - Create static map figures.
   * - :doc:`svtk visualize <cli/visualize>`
     - Create context, QC, waveform figures, and inspect figure sidecars.
   * - :doc:`svtk dashboard <cli/dashboard>`
     - Prepare and launch Streamlit dashboards.
   * - :doc:`svtk call <cli/call>`
     - Advanced one-off public-function calls outside the named command groups.

Detailed Command Reference
--------------------------

.. toctree::
   :maxdepth: 2

   cli/config
   cli/io
   cli/qc
   cli/metrics
   cli/spatial
   cli/plot
   cli/map
   cli/visualize
   cli/dashboard
   cli/call

Plotting and Mapping Notes
--------------------------

Most plotting, mapping, and visualization commands can resolve their standard input tables and figure paths from the active config, so ``--input-table``/``--input`` and ``--figure-output``/``--output`` are optional for the usual tutorial/workflow outputs. Registered table defaults may be CSV or Parquet depending on the configured output key; commands that say they accept CSV or Parquet read either suffix through the package table helpers. Use ``svtk plot metrics list``, ``svtk plot spatial list``, ``svtk map spatial list``, ``svtk visualize qc list``, ``svtk visualize context list``, or ``svtk visualize waveforms list`` to see which commands use ``config:<key>`` defaults and which intentionally require explicit input tables, shown as ``required:<role> (--input-table PATH)`` entries. Add ``--resolve-paths --config PATH`` to any of those list commands when you want to see the concrete configured paths that will be used. A ``required:<role> (--input-table PATH)`` entry means that command works on a caller-supplied table outside the standard output registry, so pass ``--input-table``/``--input`` or a named table flag for that invocation.

Common figure controls such as ``--metric``, ``--passband``, ``--bin-label``, ``--component``, ``--components``, ``--model``, ``--mode``, ``--dep``, ``--indep``, ``--colorby``, ``--compare-to``, ``--value-col``, ``--score-col``, ``--scale``, ``--time-limit-s``, ``--max-records``, ``--max-traces``, ``--title``, ``--station-region``, ``--event-region``, ``--no-connect-points``, and sidecar options are first-class flags where they apply. Use ``--kwargs key=value`` only for advanced function-specific options that are not exposed as named flags. Prefer configured default tables and named table flags such as ``--event-table``, ``--station-table``, ``--events``, ``--stations``, or ``--records`` when a command lists them; use advanced ``--table function_argument=path`` only for extra function tables that are not exposed as named table flags.

Map commands also accept ``--config`` and ``--bounds`` so you can reuse named bounds from your project config. Basemaps are enabled by default for map figures; use ``--no-basemap`` only when you explicitly want a data-only map.

Advanced Python Calls
---------------------

``svtk call`` is an advanced one-off escape hatch for importable public functions outside the named workflow commands. Prefer the named ``config``, ``io``, ``qc``, ``metrics``, ``spatial``, ``plot``, ``map``, ``visualize``, and ``dashboard`` commands for standard workflows. ``svtk call`` only accepts import paths under ``spatial_vtk``.
