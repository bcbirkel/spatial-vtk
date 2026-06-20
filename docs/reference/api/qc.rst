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
       load_standard_qc_inputs,
       load_standard_qc_workflow_outputs,
       qc_inventory_readiness_from_config,
       qc_overlap_readiness_from_config,
       qc_summary_readiness_from_config,
       run_qc_inventory_from_config,
       run_qc_summary_workflow_from_config,
       write_qc_inventory_overlap_from_config,
   )

.. automodule:: spatial_vtk.qc
   :members:

Public helpers exposed by ``spatial_vtk.qc``:

.. list-table::
   :header-rows: 1

   * - Helper
     - Use
   * - ``run_qc_inventory_from_config``
     - Build or resume the configured waveform and metric QC inventory with
       checkpointed outputs for large datasets.
   * - ``qc_inventory_readiness_from_config``
     - Check whether configured event-station records, trace QC, and full QC
       inventory outputs are ready without loading large tables, with
       ``overwrite`` and message pass-throughs for notebook rerun controls.
   * - ``write_qc_inventory_overlap_from_config``
     - Write the observed/synthetic event-station overlap inventory used by
       pairwise metric planning.
   * - ``qc_overlap_readiness_from_config``
     - Check whether the configured full QC inventory and event-station table
       are ready before writing the overlap inventory sidecar, with
       ``overwrite`` and message pass-throughs for notebook rerun controls.
   * - ``run_qc_summary_workflow_from_config``
     - Build compact retention, drop-cause, post-QC record, and availability
       tables for figures and dashboards without loading the full inventory in a
       notebook.
   * - ``qc_summary_readiness_from_config``
     - Check whether compact QC summary/review outputs are missing or stale
       from configured QC inventories without loading the inventories, with
       ``overwrite`` and message pass-throughs for notebook rerun controls.
   * - ``load_standard_qc_inputs``
     - Load standard Step 2 prepared metadata tables and the configured QC
       output group without notebook-local Step 1 output-group table mapping.
       The returned result owns skipped-step fallback payloads through
       ``qc_inventory_step_result()``, ``qc_overlap_step_result()``, and
       ``qc_summary_step_result()``, plus compact output summaries, bounded QC
       inventory/summary previews, standard QC figure rendering through
       ``write_figures()``, and bounded post-QC waveform comparison rendering
       through ``write_waveform_comparison()``.
   * - ``load_standard_qc_workflow_outputs``
     - Load the configured Step 2 QC output group and status frame without
       notebook-local path mapping. The returned result owns the full-QC,
       overlap-sidecar, and compact-summary execution gates through
       ``run_inventory_step_if_needed()``, ``run_overlap_step_if_needed()``,
       and ``run_summary_step_if_needed()`` for both standard and large-run
       notebooks. These methods return displayable skipped-step payloads when
       configured outputs are already current, and provide bounded
       compact-summary previews plus compact QC figure rendering through
       ``write_figures()`` while leaving full trace/QC inventory inspection to
       explicit streaming tools.
   * - ``build_metric_pair_retention_table_from_qc_inventory``
     - Stream the QC inventory into metric/passband/component retention counts.
   * - ``build_event_station_pair_retention_table_from_qc_inventory``
     - Stream the QC inventory into event-station retained-pair summaries.
   * - ``build_post_qc_record_table_from_qc_inventory``
     - Join retained QC decisions back to event and station coordinates for
       post-QC maps.
   * - ``build_qc_drop_cause_table_from_qc_inventory``
     - Stream compact rejection-reason counts for diagnostics.
   * - ``export_manual_review_queue_from_qc_inventory``
     - Write a bounded manual-review queue from filtered QC rows.
   * - ``filter_event_station_records_for_source_overlap``
     - Keep only event-station rows with both observed and synthetic source
       records when planning paired metrics.
   * - ``load_trace_inventory_lookup``
     - Load trace-inventory lookup metadata for reusable QC filtering.

Build
-----

Use ``spatial_vtk.qc`` for notebook-facing QC build helpers, including the
config-backed inventory workflow, overlap inventory writer, streaming summary
builders, and trace-inventory lookup utilities. ``spatial_vtk.qc.build`` is
available for advanced scripts that need the narrower build subpackage, but
the filtering, inventory, spectral, workflow, and Slurm modules are
implementation organization and are intentionally not listed as public
notebook import paths.

Review
------

Use ``spatial_vtk.qc`` or ``spatial_vtk.qc.review`` for manual-review table
helpers. The lower-level review table module is implementation organization.

Summary
-------

Use ``spatial_vtk.qc`` or ``spatial_vtk.qc.summary`` for station-family and
rejection-rule helpers. The lower-level summary rules module is implementation
organization.
