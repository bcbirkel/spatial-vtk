.. _cli-svtk-call:

svtk call
=========

Command Tree
------------

- :ref:`svtk call <cli-svtk-call>`

Command Details
---------------

.. rubric:: Usage

.. code-block:: bash

   svtk call [-h] [--args [ARGS ...]] [--args-json ARGS_JSON]
                 [--kwargs [KWARGS ...]] [--kwargs-json KWARGS_JSON]
                 [--output OUTPUT]
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
     - Import path, for example spatial_vtk.config.labels.metric_display_name.
   * - ``--args``
     - No
     - Nargs: ``*``
     - Value: ``args``. Positional arguments parsed as YAML scalars/sequences.
   * - ``--args-json``
     - No
     - 
     - Value: ``args_json``. JSON/YAML list of positional arguments.
   * - ``--kwargs``
     - No
     - Nargs: ``*``
     - Value: ``kwargs``. Keyword arguments as key=value, parsed as YAML values.
   * - ``--kwargs-json``
     - No
     - 
     - Value: ``kwargs_json``. JSON/YAML mapping of keyword arguments.
   * - ``--output``
     - No
     - 
     - Value: ``output``. Optional output path for DataFrame/dict/list results.
