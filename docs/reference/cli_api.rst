CLI API
=======

The public command is ``svtk``. It gives you file-based access to the same major Spatial-VTK workflows used from Python: configuration inspection, metadata and waveform preparation, QC queue export, metric planning and execution, plotting, mapping, dashboards, and advanced calls to importable public functions.

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
   * - :doc:`svtk plot <cli/plot>`
     - Create static metric and spatial plots.
   * - :doc:`svtk map <cli/map>`
     - Create static map figures.
   * - :doc:`svtk visualize <cli/visualize>`
     - Create context, QC, and waveform figures.
   * - :doc:`svtk dashboard <cli/dashboard>`
     - Prepare and launch Streamlit dashboards.
   * - :doc:`svtk call <cli/call>`
     - Call any importable Spatial-VTK Python function.

Detailed Command Reference
--------------------------

.. toctree::
   :maxdepth: 2

   cli/config
   cli/io
   cli/qc
   cli/metrics
   cli/plot
   cli/map
   cli/visualize
   cli/dashboard
   cli/call

Plotting and Mapping Notes
--------------------------

Most plotting and mapping commands accept ``--input`` for the main table, ``--output`` for the figure path, and ``--kwargs key=value`` for function-specific settings such as ``value_col=log2_residual`` or ``title='Residuals by distance'``. Commands that need additional tables accept ``--table argument_name=path`` and, where available, convenience aliases such as ``--events`` or ``--stations``.

Map commands also accept ``--config`` and ``--bounds`` so you can reuse named bounds from your project config. Basemaps are enabled by default for map figures; use ``--no-basemap`` only when you explicitly want a data-only map.

Advanced Python Calls
---------------------

``svtk call`` is available when you need to run an importable public function that does not yet have a curated workflow command. It only accepts import paths under ``spatial_vtk``.
