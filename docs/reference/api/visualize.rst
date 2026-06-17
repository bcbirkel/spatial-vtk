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

.. automodule:: spatial_vtk.visualize.context.figures
   :members:

.. automodule:: spatial_vtk.visualize.context.maps
   :members:

Quality Control Figures
-----------------------

.. automodule:: spatial_vtk.visualize.qc.overview
   :members:

.. automodule:: spatial_vtk.visualize.qc.retention
   :members:

.. automodule:: spatial_vtk.visualize.qc.samples
   :members:

Waveform Figures
----------------

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
represents. Use ``sidecar_rows=None`` to write all rows, or a positive integer
to write a deterministic sample.

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
