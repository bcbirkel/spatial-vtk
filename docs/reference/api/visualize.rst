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

``dashboard_output_status_frame`` returns a notebook-friendly preflight table
for the configured dashboard artifacts. It includes the row-level metric
dataset root used by distribution/download tabs, the four metrics-dashboard
summary tables used by the overview, station, event, path, and model-comparison
tabs, and the trace-QC table used by the QC dashboard. ``ready`` and
``readiness`` values are intentionally bounded checks: they inspect paths,
schemas, row counts, map-coordinate availability, and recognized dashboard
value columns without loading the full large-run metric inventory.

``dashboard_summary_table_contracts`` documents which summary table feeds each
dashboard tab and the required columns for that table. Use it in notebooks next
to ``dashboard_output_status_frame`` when a tab is empty, because the status
table reports whether the issue is a missing file, missing required columns,
missing map coordinates, or value columns that exist but contain no finite
data.

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
