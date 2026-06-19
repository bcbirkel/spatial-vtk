.. _cli-svtk-config:

svtk config
===========

Command Tree
------------

- :ref:`svtk config <cli-svtk-config>`
   - :ref:`svtk config bounds <cli-svtk-config-bounds>`
   - :ref:`svtk config find <cli-svtk-config-find>`
   - :ref:`svtk config outputs <cli-svtk-config-outputs>`
   - :ref:`svtk config set <cli-svtk-config-set>`
   - :ref:`svtk config show <cli-svtk-config-show>`
   - :ref:`svtk config unset <cli-svtk-config-unset>`

Command Details
---------------

.. rubric:: Usage

.. code-block:: bash

   svtk config [-h] {find,set,unset,show,outputs,bounds} ...

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

   svtk config bounds [-h] [--config PATH] [--run-scenario RUN_SCENARIO]
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
     - Filesystem path. Explicit config file.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay before listing bounds.
   * - ``--json``
     - No
     - Flag
     - Write JSON instead of YAML.

.. _cli-svtk-config-find:

svtk config find
^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk config find [-h] [--config PATH] [--start-dir START_DIR]

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
     - Filesystem path. Explicit config file.
   * - ``--start-dir``
     - No
     -
     - Directory path. Directory used for config discovery.

.. _cli-svtk-config-outputs:

svtk config outputs
^^^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk config outputs [-h] [--config PATH] [--run-scenario RUN_SCENARIO]
                           [--kind {all,table,figure,dashboard}] [--no-paths]
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
     - Filesystem path. Explicit config file used to resolve output paths.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay before resolving paths.
   * - ``--kind``
     - No
     - Default: ``all``; Choices: ``all``, ``table``, ``figure``, ``dashboard``
     - Limit output registry rows by artifact kind.
   * - ``--no-paths``
     - No
     - Flag
     - List keys and filenames without resolving filesystem paths.
   * - ``--json``
     - No
     - Flag
     - Write JSON instead of a text table.

.. _cli-svtk-config-set:

svtk config set
^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk config set [-h] PATH

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
   * - ``PATH``
     - Yes
     -
     - Filesystem path. Spatial-VTK config file to use by default.

.. _cli-svtk-config-show:

svtk config show
^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk config show [-h] [--config PATH] [--run-scenario RUN_SCENARIO]
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
     - Filesystem path. Explicit config file.
   * - ``--run-scenario``
     - No
     -
     - Apply one named run_scenarios overlay before printing.
   * - ``--section``
     - No
     -
     - Optional dotted section key.
   * - ``--json``
     - No
     - Flag
     - Write JSON instead of YAML.

.. _cli-svtk-config-unset:

svtk config unset
^^^^^^^^^^^^^^^^^

.. rubric:: Usage

.. code-block:: bash

   svtk config unset [-h]

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
