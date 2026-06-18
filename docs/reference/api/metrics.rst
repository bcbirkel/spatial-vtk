Metrics API
===========

Metrics modules calculate observed and synthetic waveform values, transform
those values into residuals and scores, plan file-based metric runs, and plot
metric diagnostics.

.. contents:: On this page
   :local:
   :depth: 2

Package Entry Point
-------------------

Start with ``spatial_vtk.metrics`` for metric workflow helpers and calculation
utilities that are used by notebooks, scripts, and generated Slurm workers.
These imports keep large-run planning, waveform inventory creation, metric
batch execution, merge steps, dashboard exports, and metric-output writes on one
stable package surface.

.. code-block:: python

   from spatial_vtk.metrics import (
       build_metric_waveform_inventories_from_config,
       cache_metric_manifest_waveforms,
       merge_metric_batches_from_config,
       metric_manifest_batch_status,
       metric_slurm_submission_readiness,
       metric_slurm_submission_readiness_from_config,
       plan_metric_tasks_from_config,
       submit_metrics_slurm_job,
       write_metric_outputs_from_config,
   )

.. automodule:: spatial_vtk.metrics
   :members:

Calculate
---------

.. automodule:: spatial_vtk.metrics.calculate.amplitudes
   :members:

.. automodule:: spatial_vtk.metrics.calculate.arrival_picks
   :members:

.. automodule:: spatial_vtk.metrics.calculate.bands
   :members:

.. automodule:: spatial_vtk.metrics.calculate.batch
   :members:

.. automodule:: spatial_vtk.metrics.calculate.enrich
   :members:

.. automodule:: spatial_vtk.metrics.calculate.gof
   :members:

.. automodule:: spatial_vtk.metrics.calculate.phasenet_adapter
   :members:

.. automodule:: spatial_vtk.metrics.calculate.records
   :members:

.. automodule:: spatial_vtk.metrics.calculate.spectra
   :members:

.. automodule:: spatial_vtk.metrics.calculate.summaries
   :members:

.. automodule:: spatial_vtk.metrics.calculate.transforms
   :members:

.. automodule:: spatial_vtk.metrics.calculate.waveforms
   :members:

Workflow
--------

Notebook and CLI workflows should import metric planning, execution, summary,
and output helpers from the stable ``spatial_vtk.metrics`` package entry
point. The implementation modules below document the lower-level organization
for users who need narrower module references.

.. automodule:: spatial_vtk.metrics.workflow
   :members:
   :exclude-members: MetricWorkflowTask, SlurmSettings

.. automodule:: spatial_vtk.metrics.workflow.configured
   :members:

.. automodule:: spatial_vtk.metrics.workflow.inventory
   :members:

.. automodule:: spatial_vtk.metrics.workflow.cache
   :members:

.. automodule:: spatial_vtk.metrics.workflow.execution
   :members:

.. automodule:: spatial_vtk.metrics.workflow.outputs
   :members:

.. automodule:: spatial_vtk.metrics.workflow.run
   :members:

.. automodule:: spatial_vtk.metrics.workflow.slurm
   :members:
   :exclude-members: SlurmSettings

.. automodule:: spatial_vtk.metrics.workflow.tasks
   :members:

Plotting
--------

Import plotting helpers from the stable ``spatial_vtk.metrics.plot`` package
entry point in notebooks and scripts. The implementation submodules are not
part of the tutorial-facing API.

.. code-block:: python

   from spatial_vtk.metrics.plot import (
       plot_band_score_distribution,
       plot_period_spectra,
       plot_residuals_vs_distance,
   )

.. automodule:: spatial_vtk.metrics.plot
   :members:

Large-Run Figure Context
------------------------

Use ``MetricFigureContext`` when a notebook or script needs to render many
metric figures from a large ``metrics_long`` table without loading unnecessary
columns or truncating station-map aggregation inputs. The context owns the
standard row factories used by the large-run notebooks:

``item_source_rows``
   Return the selected metric rows for a figure item. These rows are written to
   ``*.source.csv`` sidecars for aggregated station figures.

``station_summary_for_item`` and ``station_period_summary_for_item``
   Collapse all selected event-station metric rows to station summaries before
   plotting. PSA period sheets use the period-aware variant.

``station_grid_for_item`` and ``station_model_summary_for_item``
   Prepare station summaries for grid and model-map plotting while preserving
   aggregation metadata for sidecar JSON files.

.. autoclass:: spatial_vtk.metrics.plot.MetricFigureContext
   :members:

.. autofunction:: spatial_vtk.metrics.plot.prepare_large_run_metric_figure_context
