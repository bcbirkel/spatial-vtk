Input and Output API
====================

The I/O modules prepare station and event metadata, discover waveform files,
write standard output artifacts, and handle preprocessing products used by the
rest of the workflow.

.. contents:: On this page
   :local:
   :depth: 2

Package Entry Point
-------------------

Start with ``spatial_vtk.io`` in notebooks and scripts. These helpers cover the
routine workflow surface: metadata normalization, event-station table creation,
preprocessing products, table I/O, output groups, readiness checks, and bounded
table previews. Prefer these imports before reaching into implementation
modules.

.. code-block:: python

   from spatial_vtk.io import (
       output_group,
       prepare_event_metadata,
       prepare_event_station_table,
       prepare_station_metadata,
       preprocess_waveform_files,
       read_config_table,
       write_output_table,
   )

.. automodule:: spatial_vtk.io
   :members:

Metadata and Inventories
------------------------

.. automodule:: spatial_vtk.io.metadata
   :members:

.. automodule:: spatial_vtk.io.inventory
   :members:

.. automodule:: spatial_vtk.io.master_lists
   :members:

.. automodule:: spatial_vtk.io.metric_inputs
   :members:

Waveforms and Preprocessing
---------------------------

.. automodule:: spatial_vtk.io.waveforms
   :members:

.. automodule:: spatial_vtk.io.preprocessing
   :members:

Notebook Workflow Helpers
-------------------------

Use these config-backed helpers from notebooks or scripts when a workflow step
should use the same Python package function locally and inside Slurm workers.

.. automodule:: spatial_vtk.io.workflows
   :members:

Tables and Artifacts
--------------------

.. automodule:: spatial_vtk.io.tables
   :members:

.. automodule:: spatial_vtk.io.output_paths
   :members:

.. automodule:: spatial_vtk.io.artifacts
   :members:

.. automodule:: spatial_vtk.io.compute_manifest
   :members:

.. automodule:: spatial_vtk.io.plans
   :members:

Catalogs and File Formats
-------------------------

.. automodule:: spatial_vtk.io.catalogs
   :members:

.. automodule:: spatial_vtk.io.synthetic_formats
   :members:

.. automodule:: spatial_vtk.io.model_aliases
   :members:

Geospatial and Layout Exports
-----------------------------

.. automodule:: spatial_vtk.io.kml
   :members:

.. automodule:: spatial_vtk.io.layouts
   :members:
