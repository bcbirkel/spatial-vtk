Visualization API
=================

Visualization modules create context figures, QC and retention figures,
waveform plots, reusable figure utilities, and Streamlit dashboard inputs.

.. contents:: On this page
   :local:
   :depth: 2

Package Entry Point
-------------------

Start with ``spatial_vtk.visualize`` for notebook-facing context, QC, waveform,
dashboard, and sidecar helpers. Use lower-level ``context``, ``qc``,
``waveforms``, and ``dashboard`` packages when writing focused scripts that
need one visualization family.

.. code-block:: python

   from spatial_vtk.visualize import (
       prepare_configured_dashboard_datasets_from_notebook_settings,
       write_context_figures_from_outputs,
       write_qc_figures_from_outputs,
       write_waveform_comparison_from_notebook_settings,
   )

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
   * - ``write_context_figures_from_outputs`` and
       ``write_large_run_context_figures_from_outputs``
     - Render the standard Step 1 context figure suite from configured
       metadata and record-coverage outputs without notebook-local readiness
       checks, table loading, basemap kwargs, or sidecar kwargs.
   * - ``plot_retention_summary`` and
       ``plot_event_station_retention_heatmap``
     - Render compact QC retention figures from summary tables instead of full
       QC inventories.
   * - ``plot_post_qc_station_event_map`` and
       ``plot_qc_drop_cause_diagnostics``
     - Render post-QC maps and rejection-reason diagnostics.
   * - ``write_qc_figures_from_outputs`` and
       ``write_large_run_qc_figures_from_outputs``
     - Render the standard QC figure suite from compact configured QC outputs
       without notebook-local readiness checks, table loading, map kwargs, or
       sidecar kwargs.
   * - ``plot_observed_synthetic_record_section`` and ``plot_record_section``
     - Render record-section waveform figures from prepared waveform tables.
   * - ``station_event_waveform_order_frame``
     - Preview the bounded station/component order used by station-event
       waveform map panels without notebook-local sorting and slicing.
   * - ``write_waveform_comparison_from_notebook_settings``
     - Notebook-facing Step 2/6 waveform-comparison wrapper. It owns the
       ``notebook_figure_settings(...)`` render gate, sidecar controls,
       component, passband, and display settings before delegating to the
       lower-level output writer.
   * - ``write_waveform_comparison_from_outputs``
     - Lower-level script helper for observed/synthetic trace-comparison
       figures when output paths and plotting keyword arguments are already
       resolved. It reads bounded comparison-eligible rows from configured
       event-station and comparison-eligible outputs without loading full QC
       inventories.
   * - ``write_large_run_waveform_comparison_from_outputs``
     - Backward-compatible alias for older large-run notebooks that used the
       original helper name. New notebook cells should prefer
       ``write_waveform_comparison_from_notebook_settings``.
   * - ``finish_figure_with_sidecar`` and ``write_figure_row_sidecar``
     - Save figures with optional row-provenance CSV/JSON sidecars.
   * - ``figure_sidecar_status_frame`` and
       ``read_figure_sidecar_metadata``
     - Inspect saved figure provenance without loading large sidecar CSV files.
   * - ``prepare_configured_dashboard_datasets_from_notebook_settings``
     - Check dashboard readiness and optionally write configured dashboard
       datasets from one notebook-facing helper.
   * - ``write_configured_dashboard_datasets``
     - Lower-level script helper that writes dashboard-ready row and summary
       datasets from configured metric outputs after the caller has decided a
       local write is appropriate.
   * - ``display_dashboard_preparation_result``
     - Display the standard dashboard preparation readiness, status, written
       output, and summary-contract tables without notebook-local formatting
       code.
   * - ``dashboard_readiness_summary_frame`` and
       ``dashboard_output_status_frame``
     - Inspect dashboard readiness with bounded schema, row-count, and map-data
       checks.
   * - ``launch_configured_dashboards_from_notebook_settings``
     - Launch requested dashboards or show terminal fallback commands from
       config-backed notebook settings.
   * - ``launch_configured_metrics_dashboard`` and
       ``launch_configured_qc_dashboard``
     - Lower-level launch helpers for scripts that already know which
       dashboard should start and how launch options should be applied.

Context Figures
---------------

Use ``spatial_vtk.visualize.context`` as the public entry point for station,
event, record-coverage, and study-domain context figures.

.. automodule:: spatial_vtk.visualize.context
   :members:

The lower-level context figure and map modules are implementation
organization. Import context helpers from ``spatial_vtk.visualize.context`` in
notebooks and scripts.

Quality Control Figures
-----------------------

Use ``spatial_vtk.visualize.qc`` as the public entry point for QC retention,
drop-cause, waveform-sample, and post-QC map figures.

.. automodule:: spatial_vtk.visualize.qc
   :members:

The lower-level QC overview, retention, and sample modules are implementation
organization. Import QC visualization helpers from ``spatial_vtk.visualize.qc``
in notebooks and scripts.

Waveform Figures
----------------

Use ``spatial_vtk.visualize.waveforms`` as the public entry point for waveform
comparison, overlay, record-section, and station-event waveform figures.
Notebook cells should use
``write_waveform_comparison_from_notebook_settings`` when rendering the
standard or large-run comparison figure because that wrapper owns the render
gate, sidecar options, and notebook figure settings. Scripts can use
``write_waveform_comparison_from_outputs`` when they have already resolved the
output group, filters, and plotting keyword arguments.

.. automodule:: spatial_vtk.visualize.waveforms
   :members:

The lower-level waveform comparison, overlay, radial-section, record-section,
and station-event modules are implementation organization. Import waveform
figure helpers from ``spatial_vtk.visualize.waveforms`` in notebooks and
scripts.

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
and user-facing ``artifact_role`` / ``artifact_label`` columns, plus
``resolved_path`` as the clear path column. The legacy ``path`` column remains
available as an alias. Notebooks can display "metrics dashboard row dataset" or
"station_rollup dashboard summary table" instead of relying on lower-level
output registry names.
The compact dashboard readiness summary carries the same
``artifact_role`` / ``artifact_label`` and ``resolved_path`` columns, and the
metrics/QC dashboard Data Status tabs show those labels while keeping
readiness displays bounded to small status metadata.
The Streamlit apps also accept clear URL query keys for explicit path
overrides: ``metrics_dataset_dir`` and ``dashboard_summary_table_dir`` for the
metrics dashboard, and ``qc_trace_summary`` for the QC dashboard. The older
``metrics_root``, ``summary_root``, and ``trace_summary`` query keys remain
supported as compatibility aliases, but new links and docs should use the
clearer names.
For Python launch calls, pass ``metrics_dataset_dir`` and
``dashboard_summary_table_dir`` to ``launch_metrics_dashboard``; the older
``metrics_root`` and ``summary_root`` keyword arguments remain supported for
existing scripts.

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
   * - ``display_dashboard_output_previews``
     - Display bounded dashboard summary and ``metrics_long`` previews from
       configured paths in one notebook-safe package call.
   * - ``dashboard_metric_dataset_readiness_frame`` and
       ``dashboard_qc_trace_readiness_frame``
     - Inspect row-level metric dataset and QC trace-summary readiness without
       loading full inventories. For partitioned metric datasets, readiness
       checks row counts and the union of partition schemas, so one sparse
       partition does not hide value columns present in other partitions.
   * - ``write_configured_dashboard_datasets``
     - Rebuild dashboard row datasets and summary tables from the active config.
   * - ``prepare_configured_dashboard_datasets_from_notebook_settings``
     - Own the Step 7 notebook branch that checks readiness, optionally writes
       tutorial-sized dashboard datasets, and returns compact readiness,
       status, and written-output frames.
   * - ``display_dashboard_preparation_result``
     - Return and optionally display the standard dashboard preparation frames
       with bounded row counts and summary-table contracts.
   * - ``load_dashboard_metric_dataset``,
       ``load_dashboard_summary_tables``, and
       ``load_filtered_dashboard_summary_table``
     - Load dashboard-ready datasets after readiness checks pass.
       ``load_dashboard_metric_dataset`` applies model, metric, passband,
       PSA/FAS oscillator-period, component, distance, and Vs30 filters while
       reading bounded row-level datasets, so large-run dashboards cap the
       selected rows rather than a broader unfiltered prefix. Row-level
       loading treats ``band`` and ``passband`` as aliases so older
       ``metrics_long`` tables and current dashboard datasets filter the same
       way. ``load_filtered_dashboard_summary_table`` applies the same
       model/metric/passband/period/component filters while reading one summary
       table in chunks, which lets dashboard station, event, and path tabs load
       only the active selection instead of materializing every optional
       summary table at startup.
   * - ``launch_configured_metrics_dashboard`` and
       ``launch_configured_qc_dashboard``
     - Launch Streamlit dashboards from config-backed paths and launch options.
   * - ``launch_configured_dashboards_from_notebook_settings``
     - Use notebook launch settings to launch requested dashboards or return
       terminal fallback commands and launch errors in one compact status
       frame. Pass ``dashboards=("qc",)`` for QC-only notebook cells.
   * - ``filter_dashboard_metrics`` and ``filter_qc_dashboard_rows``
     - Apply dashboard filters consistently in apps, tests, and exported tables.

``write_configured_dashboard_datasets`` replaces the standard dashboard metric
dataset files and summary tables for the current run. It removes only
recognized dashboard artifacts, so reruns cannot accidentally mix old metric
partitions or stale summary files with newly written outputs.
``prepare_configured_dashboard_datasets_from_notebook_settings`` wraps that
writer for notebooks: it calls the bounded dashboard readiness checks, skips
local preparation when requested for large datasets, and reports the readiness,
current artifact status, and written paths without requiring notebooks to loop
over output dictionaries or repeat ``should_run`` branches. Large-run notebooks
set ``prepare_locally=False`` and pass the returned ``readiness`` object to the
Slurm-aware preparation cell, so preflight and postflight displays stay on the
same package helper path.

``dashboard_summary_table_contracts`` documents which summary table feeds each
dashboard tab and the required columns for that table. Use it in notebooks next
to ``dashboard_output_status_frame`` when a tab is empty, because the status
table reports whether the issue is a missing file, missing required columns,
missing map coordinates, or value columns that exist but contain no finite
data. Use ``preview_dashboard_summary_tables`` for small, bounded samples of
the configured summary tables after readiness checks pass; it keeps large-run
notebooks from loading whole dashboard inputs just to inspect the first rows.
The path summary is optional when the source ``metrics_long`` table has no
``distance_km`` and ``azimuth_deg`` columns. In that case the status table still
reports the missing or empty ``path_hex`` artifact for the Paths tab, but
``dashboard_output_readiness`` does not request a rebuild that cannot create
path-bin summaries from the available source columns.
Dashboard summary writing normalizes accepted station/event coordinate aliases
such as ``station_lat`` / ``station_lon`` and ``event_latitude`` /
``event_longitude`` into the canonical map columns used by station and event
dashboard tabs.
Dashboard summary tables use ``n`` for contributing metric row counts and
include ``event_count`` / ``station_count`` where those identifiers are
available, so notebook previews and dashboard tables can show how much data is
behind each aggregate. Residual summaries include both ``med_resid`` and the
canonical ``med_residual`` alias, while row-level downloads continue to use
``residual``. The metrics Streamlit dashboard also includes a Data Status tab
with the same bounded summary-table and row-level dataset readiness tables,
plus a current-filter row-count summary for the Overview, Stations, Events,
Paths, and Distributions tabs. The QC dashboard includes a Data Status tab for
trace-summary readiness plus loaded and filtered row counts. A running
dashboard can therefore explain blank tabs without requiring users to return to
the notebook.

For large runs, the metrics dashboard caps row-level records loaded for the
Distributions tab and filtered-row CSV download at ``200000`` rows by default.
Set ``SVTK_METRICS_DASHBOARD_ROW_LIMIT`` before launching the dashboard, or use
the "Maximum row-level records" sidebar control, when you need a larger or
smaller bounded sample. Summary, station, event, and path tabs continue to use
precomputed dashboard summary tables rather than loading the full metric
inventory.

The QC dashboard similarly caps loaded trace-summary rows at ``250000`` by
default. Set ``SVTK_QC_DASHBOARD_MAX_ROWS`` before launch, or use the "Maximum
trace-summary rows" sidebar control, to adjust the bounded subset. Set
``SVTK_QC_DASHBOARD_MAX_ROWS=all`` only when the full trace-summary table is
small enough for the dashboard process.

.. automodule:: spatial_vtk.visualize.dashboard
   :members:

The lower-level dashboard chart, contract, export, filter, label, launch, map,
and table modules are implementation organization. Import dashboard helpers
from ``spatial_vtk.visualize.dashboard`` in notebooks and scripts.

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

For station-level metric maps and other large-run station summaries, the main
sidecar rows are the post-aggregation station values handed to Matplotlib. The
matching source sidecar rows are the metric/event-station records aggregated
into those station values. The JSON sidecar records
``aggregation_contract``, ``aggregation_method``,
``aggregation_group_columns``, ``aggregation_coordinate_columns``,
``aggregation_input_row_count``, ``aggregation_finite_row_count``, and
``aggregation_dropped_nonfinite_row_count``. It also records input and finite
station/event counts, ``source_rows_filter`` when the source sidecar is limited
to plotted aggregation groups, and ``aggregation_panel_count`` for multi-panel
figures. For PSA period sheets and other multi-panel figures, panel identifiers
such as ``__svtk_panel_period_s`` are included so the raw source rows can be
matched back to the plotted panel. This is the public audit trail for verifying
that a station figure used all selected events and stations rather than a
preview or sampled dataframe.

Use ``figure_sidecar_status_frame(sidecar_dir)`` to inspect a directory of
JSON sidecars without loading the CSV row files. The status table reports
exactness flags, plot/source row counts, source-sidecar availability, and
station-aggregation metadata when a figure was created from station summaries,
including grouping columns, coordinate columns, collapsed dimensions, and
aggregation row, station, event, and panel counts.
Missing sidecar directories and existing empty sidecar directories both produce
an empty status table; use ``svtk visualize sidecars status --sidecar-dir DIR``
when a workflow needs the human-readable message or JSON
``sidecar_dir_exists`` field that distinguishes those cases.
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
