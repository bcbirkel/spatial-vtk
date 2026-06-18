Spatial Analysis API
====================

Spatial modules prepare metric fields, calculate spatial statistics, work with
GeoJSON regions and corridors, and create maps and spatial diagnostic plots.

.. contents:: On this page
   :local:
   :depth: 2

Package Entry Point
-------------------

.. automodule:: spatial_vtk.spatial
   :members:

Calculate
---------

Notebook and CLI workflows should import spatial statistics, GeoJSON, corridor,
and geometry helpers from the stable ``spatial_vtk.spatial`` package entry
point. The implementation modules below document the lower-level organization
for users who need narrower module references.

.. automodule:: spatial_vtk.spatial.calculate
   :members:

.. automodule:: spatial_vtk.spatial.calculate.prepare_stats
   :members:

.. automodule:: spatial_vtk.spatial.calculate.correlation
   :members:

.. automodule:: spatial_vtk.spatial.calculate.clustering
   :members:

.. automodule:: spatial_vtk.spatial.calculate.pca
   :members:

.. automodule:: spatial_vtk.spatial.calculate.geology
   :members:

.. automodule:: spatial_vtk.spatial.calculate.geojson
   :members:

.. automodule:: spatial_vtk.spatial.calculate.corridors
   :members:

.. automodule:: spatial_vtk.spatial.calculate.geometry
   :members:

.. automodule:: spatial_vtk.spatial.calculate.paths
   :members:

.. automodule:: spatial_vtk.spatial.calculate.patterns
   :members:

.. automodule:: spatial_vtk.spatial.calculate.polygon_edges
   :members:

.. automodule:: spatial_vtk.spatial.calculate.rotation
   :members:

.. automodule:: spatial_vtk.spatial.calculate.settings
   :members:

.. automodule:: spatial_vtk.spatial.calculate.workflow
   :members:

Plots
-----

Use ``spatial_vtk.spatial.plot`` for public non-map plotting imports in
notebooks and scripts. The implementation submodules are not part of the
tutorial-facing API.

.. code-block:: python

   from spatial_vtk.spatial.plot import (
       plot_correlogram,
       plot_distance_correlation_by_metric,
       prepare_spatial_figure_context,
   )

.. automodule:: spatial_vtk.spatial.plot
   :members:

Large-Run Spatial Figure Context
--------------------------------

Use ``SpatialFigureContext`` for Step 4-style spatial diagnostics that should
reuse the same filtering, PSA period-sheet handling, station aggregation, and
sidecar metadata conventions as the metric figure workflow. The context
delegates metric-field and event-centered residual tables to the appropriate
metric figure context, so station maps, residual grids, and model maps use the
same row factories and aggregation audit metadata across Step 3 and Step 4.

``item_source_rows``
   Return the spatial rows represented by a figure item for source sidecars.

``station_summary_for_item`` and ``station_period_summary_for_item``
   Collapse selected event-station rows to station summaries, including
   PSA-period summaries.

``station_grid_for_item`` and ``station_model_summary_for_item``
   Prepare station summaries for grid and model-map plotting without putting
   dataframe manipulation logic in notebooks.

.. autoclass:: spatial_vtk.spatial.plot.SpatialFigureContext
   :members:

.. autofunction:: spatial_vtk.spatial.plot.prepare_spatial_figure_context

Maps
----

Use ``spatial_vtk.spatial.map`` for public map imports. This entry point also
contains the path and corridor map helpers used by the tutorials.

.. code-block:: python

   from spatial_vtk.spatial.map import (
       plot_metric_map_by_model,
       plot_residual_grid,
       plot_corridor_map,
       plot_event_residual_map,
       plot_station_metric_map,
   )

.. automodule:: spatial_vtk.spatial.map
   :members:
