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
notebooks and scripts:

.. code-block:: python

   from spatial_vtk.spatial.plot import (
       plot_correlogram,
       plot_distance_correlation_by_metric,
       prepare_spatial_figure_context,
   )

.. automodule:: spatial_vtk.spatial.plot
   :members:

.. automodule:: spatial_vtk.spatial.plot.correlation
   :members:

.. automodule:: spatial_vtk.spatial.plot.large_run
   :members:

.. automodule:: spatial_vtk.spatial.plot.metrics
   :members:

.. automodule:: spatial_vtk.spatial.plot.pca
   :members:

Maps
----

Use ``spatial_vtk.spatial.map`` for public map imports:

.. code-block:: python

   from spatial_vtk.spatial.map import (
       plot_metric_map_by_model,
       plot_residual_grid,
       plot_station_metric_map,
   )

.. automodule:: spatial_vtk.spatial.map
   :members:

.. automodule:: spatial_vtk.spatial.map.basemaps
   :members:

.. automodule:: spatial_vtk.spatial.map.correlation
   :members:

.. automodule:: spatial_vtk.spatial.map.geojson
   :members:

.. automodule:: spatial_vtk.spatial.map.metrics
   :members:

.. automodule:: spatial_vtk.spatial.map.pca
   :members:

Path Maps
---------

.. automodule:: spatial_vtk.spatial.map.path.corridors
   :members:

.. automodule:: spatial_vtk.spatial.map.path.residuals
   :members:
