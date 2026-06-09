.. _cli-svtk-config:

svtk config
===========

Command Tree
------------

- :ref:`svtk config <cli-svtk-config>`
   - :ref:`svtk config bounds <cli-svtk-config-bounds>`
   - :ref:`svtk config find <cli-svtk-config-find>`
   - :ref:`svtk config show <cli-svtk-config-show>`

Command Details
---------------

.. rubric:: Usage

.. code-block:: bash

   svtk config [-h] {find,show,bounds} ...

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

.. _cli-svtk-config-bounds:

svtk config bounds
^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk config bounds [-h] [--config CONFIG] [--run-scenario RUN_SCENARIO]
                          [--json]

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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Explicit config file.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay before listing bounds.
   * - ``--json``
     - No
     - Flag
     - Write JSON instead of YAML.

.. _cli-svtk-config-find:

svtk config find
^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk config find [-h] [--config CONFIG] [--start-dir START_DIR]

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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Explicit config file.
   * - ``--start-dir``
     - No
     - 
     - Value: ``start_dir``. Directory used for config discovery.

.. _cli-svtk-config-show:

svtk config show
^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk config show [-h] [--config CONFIG] [--run-scenario RUN_SCENARIO]
                        [--section SECTION] [--json]

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
   * - ``--config``
     - No
     - 
     - Value: ``config``. Explicit config file.
   * - ``--run-scenario``
     - No
     - 
     - Value: ``run_scenario``. Apply one named run_scenarios overlay before printing.
   * - ``--section``
     - No
     - 
     - Value: ``section``. Optional dotted section key.
   * - ``--json``
     - No
     - Flag
     - Write JSON instead of YAML.
