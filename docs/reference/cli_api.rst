CLI API
=======

The public command is ``svtk``. It gives you file-based access to the same major Spatial-VTK workflows used from Python: configuration inspection, metadata and waveform preparation, QC queue export, metric planning and execution, plotting, mapping, dashboards, and advanced calls to public functions that do not yet have curated commands.

Run ``svtk --help`` to see the command tree from your installed environment.

.. code-block:: bash

   svtk --help
   svtk --version

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
     - Advanced escape hatch for public Spatial-VTK Python functions without curated commands.

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

Most plotting and mapping commands can resolve their standard input tables and figure paths from the active config, so ``--input``/``--input-table`` and ``--output``/``--figure-output`` are optional for the usual tutorial/workflow outputs. Registered table defaults may be CSV or Parquet depending on the configured output key; commands that say they accept CSV or parquet read either suffix through the package table helpers. Use ``svtk plot metrics list``, ``svtk plot spatial list``, or ``svtk map spatial list`` to see which commands use ``config:<key>`` defaults and which still require explicit input tables.

Common figure controls such as ``--metric``, ``--passband``, ``--bin-label``, ``--component``, ``--components``, ``--model``, ``--mode``, ``--dep``, ``--indep``, ``--colorby``, ``--compare-to``, ``--value-col``, ``--score-col``, ``--scale``, ``--time-limit-s``, ``--max-records``, ``--max-traces``, ``--title``, ``--station-region``, ``--event-region``, ``--no-connect-points``, and sidecar options are first-class flags where they apply. Use ``--kwargs key=value`` only for advanced function-specific options that do not yet have curated flags. Prefer configured default tables and named table aliases such as ``--events`` or ``--stations`` when a command lists them; use advanced ``--table function_argument=path`` only for extra function tables that do not yet have named flags.

Map commands also accept ``--config`` and ``--bounds`` so you can reuse named bounds from your project config. Basemaps are enabled by default for map figures; use ``--no-basemap`` only when you explicitly want a data-only map.

Advanced Python Calls
---------------------

``svtk call`` is an advanced escape hatch for importable public functions that do not yet have curated workflow commands. Prefer the named ``config``, ``io``, ``qc``, ``metrics``, ``spatial``, ``plot``, ``map``, ``visualize``, and ``dashboard`` commands for standard workflows. ``svtk call`` only accepts import paths under ``spatial_vtk``.
