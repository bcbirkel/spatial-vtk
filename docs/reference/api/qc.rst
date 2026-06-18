Quality Control API
===================

Quality-control modules build trace inventories, evaluate waveform and metric
QC rules, create summaries, and prepare manual-review queues.

.. contents:: On this page
   :local:
   :depth: 2

Package Entry Point
-------------------

Start with ``spatial_vtk.qc`` for notebook and Slurm QC workflow helpers. The
top-level package exposes the full QC inventory build, observed/synthetic
overlap sidecar creation, compact summary-table generation, and review-table
helpers without requiring notebooks to import lower-level builder modules.

.. code-block:: python

   from spatial_vtk.qc import (
       build_metric_pair_retention_table_from_qc_inventory,
       build_qc_drop_cause_table_from_qc_inventory,
       run_qc_inventory_from_config,
       run_qc_summary_workflow_from_config,
       write_qc_inventory_overlap_from_config,
   )

.. automodule:: spatial_vtk.qc
   :members:

Build
-----

.. automodule:: spatial_vtk.qc.build.filtering
   :members:

.. automodule:: spatial_vtk.qc.build.inventory
   :members:

.. automodule:: spatial_vtk.qc.build.spectral
   :members:

.. automodule:: spatial_vtk.qc.build.workflow
   :members:

Review
------

.. automodule:: spatial_vtk.qc.review.tables
   :members:

Summary
-------

.. automodule:: spatial_vtk.qc.summary.rules
   :members:
