Visualization API
=================

Visualization modules create context figures, QC and retention figures,
waveform plots, reusable figure utilities, and Streamlit dashboard inputs.

.. contents:: On this page
   :local:
   :depth: 2

Package Entry Point
-------------------

.. automodule:: spatial_vtk.visualize
   :members:

Public helpers exposed by ``spatial_vtk.visualize``:

.. list-table::
   :header-rows: 1

   * - Helper
     - Use
   * - ``plot_station_event_beachball_map`` and
       ``plot_station_event_network_map``
     - Render station/event context maps from prepared metadata.
   * - ``plot_retention_summary`` and
       ``plot_event_station_retention_heatmap``
     - Render compact QC retention figures from summary tables instead of full
       QC inventories.
   * - ``plot_post_qc_station_event_map`` and
       ``plot_qc_drop_cause_diagnostics``
     - Render post-QC maps and rejection-reason diagnostics.
   * - ``plot_observed_synthetic_record_section`` and ``plot_record_section``
     - Render record-section waveform figures from prepared waveform tables.
   * - ``finish_figure_with_sidecar`` and ``write_figure_row_sidecar``
     - Save figures with optional row-provenance CSV/JSON sidecars.
   * - ``figure_sidecar_status_frame`` and
       ``read_figure_sidecar_metadata``
     - Inspect saved figure provenance without loading large sidecar CSV files.
   * - ``write_configured_dashboard_datasets``
     - Write dashboard-ready row and summary datasets from configured metric
       outputs.
   * - ``dashboard_readiness_summary_frame`` and
       ``dashboard_output_status_frame``
     - Inspect dashboard readiness with bounded schema, row-count, and map-data
       checks.
   * - ``launch_configured_metrics_dashboard`` and
       ``launch_configured_qc_dashboard``
     - Launch dashboards from config-backed inputs.

Context Figures
---------------

Use ``spatial_vtk.visualize.context`` as the public entry point for station,
event, record-coverage, and study-domain context figures.

.. automodule:: spatial_vtk.visualize.context
   :members:

.. automodule:: spatial_vtk.visualize.context.figures
   :members:

.. automodule:: spatial_vtk.visualize.context.maps
   :members:

Quality Control Figures
-----------------------

Use ``spatial_vtk.visualize.qc`` as the public entry point for QC retention,
drop-cause, waveform-sample, and post-QC map figures.

.. automodule:: spatial_vtk.visualize.qc
   :members:

.. automodule:: spatial_vtk.visualize.qc.overview
   :members:

.. automodule:: spatial_vtk.visualize.qc.retention
   :members:

.. automodule:: spatial_vtk.visualize.qc.samples
   :members:

Waveform Figures
----------------

Use ``spatial_vtk.visualize.waveforms`` as the public entry point for waveform
comparison, overlay, record-section, and station-event waveform figures.

.. automodule:: spatial_vtk.visualize.waveforms
   :members:

.. automodule:: spatial_vtk.visualize.waveforms.comparison
   :members:

.. automodule:: spatial_vtk.visualize.waveforms.overlays
   :members:

.. automodule:: spatial_vtk.visualize.waveforms.radial_sections
   :members:

.. automodule:: spatial_vtk.visualize.waveforms.record_sections
   :members:

.. automodule:: spatial_vtk.visualize.waveforms.station_event
   :members:

Dashboard Helpers
-----------------

Dashboard helpers separate reusable data contracts from the Streamlit app
entry points. Scripts and notebooks should prefer the public functions exposed
by ``spatial_vtk.visualize.dashboard`` for readiness checks, summary filtering,
dashboard dataset export, and dashboard launch commands. These helpers are safe
to import without starting Streamlit.

``dashboard_readiness_summary_frame`` returns a compact preflight table for
notebooks, while ``dashboard_output_status_frame`` returns the detailed
artifact status. Together they cover the row-level metric dataset root used by
distribution/download tabs, the four metrics-dashboard summary tables used by
the overview, station, event, path, and model-comparison tabs, and the trace-QC
table used by the QC dashboard. ``ready`` and ``readiness`` values are
intentionally bounded checks: they inspect paths, schemas, row counts,
map-coordinate availability, and recognized dashboard value columns without
loading the full large-run metric inventory.
The detailed status table includes both the configured path key in ``name``
and user-facing ``artifact_role`` / ``artifact_label`` columns, so notebooks
can display "metrics dashboard row dataset" or "station_rollup dashboard
summary table" instead of relying on internal key names such as
``metrics_dashboard_root``.
The compact dashboard readiness summary carries the same
``artifact_role`` / ``artifact_label`` columns, and the metrics/QC dashboard
Data Status tabs show those labels while keeping readiness displays bounded to
small status metadata.

When a dashboard tab is blank or unexpectedly sparse, diagnose the configured
artifacts before loading full metric or QC inventories:

.. code-block:: python

   from spatial_vtk.visualize.dashboard import (
       dashboard_output_status_frame,
       dashboard_readiness_summary_frame,
       dashboard_summary_table_contracts,
   )

   readiness_summary = dashboard_readiness_summary_frame(cfg=cfg)
   dashboard_status = dashboard_output_status_frame(cfg=cfg)
   dashboard_contracts = dashboard_summary_table_contracts()

   display(readiness_summary)
   display(dashboard_status)
   display(dashboard_contracts)

The readiness and status frames are intentionally small. Use ``artifact_label``
to find the user-facing dataset, ``dashboard_tabs`` to see which dashboard tab
uses it, ``readiness`` / ``message`` to identify the failure, and
``suggested_action`` to see the next rebuild step. Use
``required_columns`` / ``missing_columns`` / ``map_message`` to decide whether
the dashboard inputs need to be rebuilt because of missing schema or map
coordinate data.

Public helpers exposed by ``spatial_vtk.visualize.dashboard``:

.. list-table::
   :header-rows: 1

   * - Helper
     - Use
   * - ``dashboard_readiness_summary_frame`` and
       ``dashboard_output_status_frame``
     - Build bounded dashboard-readiness tables for notebooks and Data Status
       tabs.
   * - ``dashboard_summary_table_contracts`` and
       ``dashboard_summary_table_paths``
     - Explain which summary tables feed dashboard tabs and which columns they
       require.
   * - ``preview_dashboard_summary_tables``
     - Read bounded previews of configured dashboard summary tables without
       loading full large-run dashboard inputs or resolving table paths in
       notebooks.
   * - ``dashboard_metric_dataset_readiness_frame`` and
       ``dashboard_qc_trace_readiness_frame``
     - Inspect row-level metric dataset and QC trace-summary readiness without
       loading full inventories.
   * - ``write_configured_dashboard_datasets``
     - Rebuild dashboard row datasets and summary tables from the active config.
   * - ``load_dashboard_metric_dataset`` and
       ``load_dashboard_summary_tables``
     - Load dashboard-ready datasets after readiness checks pass.
   * - ``launch_configured_metrics_dashboard`` and
       ``launch_configured_qc_dashboard``
     - Launch Streamlit dashboards from config-backed paths and launch options.
   * - ``filter_dashboard_metrics`` and ``filter_qc_dashboard_rows``
     - Apply dashboard filters consistently in apps, tests, and exported tables.

``write_configured_dashboard_datasets`` replaces the standard dashboard metric
dataset files and summary tables for the current run. It removes only
recognized dashboard artifacts, so reruns cannot accidentally mix old metric
partitions or stale summary files with newly written outputs.

``dashboard_summary_table_contracts`` documents which summary table feeds each
dashboard tab and the required columns for that table. Use it in notebooks next
to ``dashboard_output_status_frame`` when a tab is empty, because the status
table reports whether the issue is a missing file, missing required columns,
missing map coordinates, or value columns that exist but contain no finite
data. Use ``preview_dashboard_summary_tables`` for small, bounded samples of
the configured summary tables after readiness checks pass; it keeps large-run
notebooks from loading whole dashboard inputs just to inspect the first rows.
Dashboard summary tables use ``n`` for contributing metric row counts and
include ``event_count`` / ``station_count`` where those identifiers are
available, so notebook previews and dashboard tables can show how much data is
behind each aggregate. The metrics Streamlit dashboard also includes a Data
Status tab with the same bounded summary-table and row-level dataset readiness
tables, plus a current-filter row-count summary for the Overview, Stations,
Events, Paths, and Distributions tabs. The QC dashboard includes a Data Status tab for
trace-summary readiness plus loaded and filtered row counts. A running dashboard
can therefore explain blank tabs without requiring users to return to the
notebook.

.. automodule:: spatial_vtk.visualize.dashboard
   :members:

.. automodule:: spatial_vtk.visualize.dashboard.charts
   :members:

.. automodule:: spatial_vtk.visualize.dashboard.contracts
   :members:

.. automodule:: spatial_vtk.visualize.dashboard.export
   :members:

.. automodule:: spatial_vtk.visualize.dashboard.exports
   :members:

.. automodule:: spatial_vtk.visualize.dashboard.filters
   :members:

.. automodule:: spatial_vtk.visualize.dashboard.labels
   :members:

.. automodule:: spatial_vtk.visualize.dashboard.launch
   :members:

.. automodule:: spatial_vtk.visualize.dashboard.maps
   :members:

.. automodule:: spatial_vtk.visualize.dashboard.tables
   :members:

Shared Figure Utilities
-----------------------

Figure sidecars provide optional row-provenance files for saved figures. Pass
``write_sidecar=True`` to supported plotting functions to write a CSV with the
exact rows handed to the plot. Aggregated figures can also write a
``*.source.csv`` file containing the pre-aggregation rows, plus a JSON metadata
file with event, station, component, metric, passband, model, and PSA-period
counts. The JSON metadata includes ``plot_rows_role`` and
``source_rows_role`` so station summaries, event-level metric rows, and other
derived plotting tables can be audited without guessing what each CSV
represents. Use ``sidecar_rows=None`` or ``sidecar_rows=0`` to write all rows,
or a positive integer to write a deterministic sample. The metadata records
``sidecar_row_policy``, ``plot_sidecar_exact``, and ``source_sidecar_exact`` so
callers can tell whether a sidecar contains every row or a sampled audit table.
Use ``figure_sidecar_status_frame(sidecar_dir)`` to inspect a directory of
JSON sidecars without loading the CSV row files. The status table reports
exactness flags, plot/source row counts, source-sidecar availability, and
station-aggregation metadata when a figure was created from station summaries.
``read_figure_sidecar_metadata`` reads one JSON sidecar from a figure path,
main sidecar CSV path, source sidecar CSV path, or JSON metadata path.

Public sidecar helpers exposed by ``spatial_vtk.visualize``:

.. list-table::
   :header-rows: 1

   * - Helper
     - Use
   * - ``finish_figure_with_sidecar``
     - Save a Matplotlib figure and optional row-provenance sidecars through one
       helper.
   * - ``write_figure_row_sidecar``
     - Write the plotted rows, optional source rows, and JSON metadata next to a
       figure.
   * - ``layered_figure_rows`` and ``sidecar_rows_for_write``
     - Build deterministic row samples for large figures while preserving
       exactness metadata.
   * - ``figure_sidecar_status_frame``
     - Summarize a directory of JSON sidecars without opening large CSV row
       files.
   * - ``read_figure_sidecar_metadata``
     - Read one sidecar metadata JSON from any related figure or sidecar path.
   * - ``figure_sidecar_dimension_counts``
     - Record compact event, station, model, metric, passband, component, and
       PSA-period counts for figure audits.

.. automodule:: spatial_vtk.visualize.figure_context
   :members:

.. automodule:: spatial_vtk.visualize.figure_io
   :members:

.. automodule:: spatial_vtk.visualize.figure_sidecars
   :members:

.. automodule:: spatial_vtk.visualize.fit
   :members:

.. automodule:: spatial_vtk.visualize.record_sections
   :members:

.. automodule:: spatial_vtk.visualize.selection
   :members:
