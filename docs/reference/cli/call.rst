.. _cli-svtk-call:

svtk call
=========

Advanced escape hatch for importable public Spatial-VTK Python functions that do not yet have curated workflow commands.

Advanced Escape Hatch
---------------------

Use ``svtk call`` only for public Spatial-VTK functions that do not yet have a curated workflow command. Standard project workflows should use the named command groups because they resolve config-backed paths, expose stable flags, and document expected inputs directly.

Command Tree
------------

- :ref:`svtk call <cli-svtk-call>`

Command Details
---------------

.. rubric:: Usage

.. code-block:: bash

   svtk call [-h] [--args [ARGS ...]] [--args-json ARGS_JSON]
                 [--kwargs [KWARGS ...]] [--kwargs-json KWARGS_JSON]
                 [--output PATH]
                 function

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
   * - ``function``
     - Yes
     -
     - Import path, for example spatial_vtk.config.metric_display_name.
   * - ``--args``
     - No
     - Nargs: ``*``
     - Positional arguments parsed as YAML scalars/sequences.
   * - ``--args-json``
     - No
     -
     - JSON/YAML list of positional arguments.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Keyword arguments as key=value, parsed as YAML values.
   * - ``--kwargs-json``
     - No
     -
     - JSON/YAML mapping of keyword arguments.
   * - ``--output``
     - No
     -
     - Filesystem path. Optional output path for DataFrame/dict/list results.
