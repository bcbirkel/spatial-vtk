Spatial Analysis API
====================

Spatial modules prepare metric fields, calculate spatial statistics, work with
GeoJSON regions and corridors, and create maps and spatial diagnostic plots.

.. contents:: On this page
   :local:
   :depth: 2

Package Entry Point
-------------------

Start with ``spatial_vtk.spatial`` for spatial-statistics, GeoJSON, corridor,
geometry, PCA, clustering, path, and pattern helpers. Use
``spatial_vtk.spatial.plot`` for non-map diagnostic figures and
``spatial_vtk.spatial.map`` for geographic maps; those plotting subpackages are
stable public entry points and avoid exposing notebook users to implementation
module names.

.. code-block:: python

   from spatial_vtk.spatial import (
       run_spatial_statistics_workflow_from_config,
       run_geojson_region_summary_workflow_from_config,
       run_boundary_corridor_workflow_from_config,
       build_path_table,
       summarize_residuals_by_path_bin,
   )

   from spatial_vtk.spatial.plot import plot_correlogram
   from spatial_vtk.spatial.map import plot_station_metric_map

.. automodule:: spatial_vtk.spatial
   :members:

Public helpers exposed by ``spatial_vtk.spatial``:

.. list-table::
   :header-rows: 1

   * - Helper
     - Use
   * - ``run_spatial_statistics_workflow_from_config``
     - Build the configured metric-field, event-centered residual,
       station-bias, Moran's I, distance-correlation, clustering, PCA, and
       geology tables.
   * - ``run_spatial_derived_outputs_workflow_from_config``
     - Rebuild downstream spatial outputs that depend on existing metric and
       spatial-statistics tables.
   * - ``run_geojson_region_summary_workflow_from_config``
     - Summarize configured metric rows by GeoJSON regions using config-backed
       metric and region paths.
   * - ``run_boundary_corridor_workflow_from_config``
     - Build configured boundary-corridor selections and summaries.
   * - ``spatial_statistics_settings_from_config``
     - Resolve metric, component, passband, distance-bin, clustering, PCA, and
       geologic-contrast settings from the active config.
   * - ``build_path_table`` and ``summarize_residuals_by_path_bin``
     - Build path-level residual summaries for maps, corridors, and dashboard
       exports.
   * - ``annotate_points_with_geojson`` and ``classify_paths_with_geojson``
     - Add region and path-control metadata from configured GeoJSON polygons.
   * - ``build_station_edge_corridors`` and ``select_records_by_corridors``
     - Prepare corridor records for path-focused diagnostics.

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

Public helpers exposed by ``spatial_vtk.spatial.plot``:

.. list-table::
   :header-rows: 1

   * - Helper
     - Use
   * - ``prepare_spatial_figure_context`` and ``SpatialFigureContext``
     - Render large-run spatial figures with the same filtering, station
       aggregation, PSA-period handling, and sidecar metadata conventions used
       by the metric figure context.
   * - ``write_large_run_geojson_region_figures_from_outputs``
     - Write the Step 5 GeoJSON overview map, corridor map, and region boxplot
       from configured output groups without notebook-local table loading or
       figure-path plumbing.
   * - ``write_large_run_region_boxplot_from_outputs``
     - Write a Step 5/6 region boxplot from an ``OutputGroup``, preferring an
       enriched metric table when available and falling back to the long metric
       table without adding notebook-local path-selection logic.
   * - ``plot_correlogram``, ``plot_semivariogram``, and
       ``plot_directional_correlogram``
     - Plot spatial correlation diagnostics by distance or direction.
   * - ``plot_distance_correlation_by_metric`` and
       ``plot_residual_correlation``
     - Plot metric-level spatial correlation summaries.
   * - ``plot_block_holdout_scatter``
     - Plot spatial block-holdout predictions against observed values.
   * - ``plot_cluster_solution_scores`` and ``plot_cluster_feature_heatmap``
     - Plot clustering diagnostics and feature summaries.
   * - ``boxplot``, ``scatterplot``, and ``heatmap``
     - Plot generic spatial metric distributions from prepared tables.
   * - ``plot_geology_contrast`` and ``plot_path_bin_summary``
     - Plot geologic-class and path-bin diagnostic tables.
   * - ``plot_pca_explained_variance`` and ``plot_pca_feature_loadings``
     - Plot PCA spatial-mode diagnostics.

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

``status_frame`` and ``dimension_summary_frame``
   Return small notebook tables for loaded Step 4 output-table status and
   metric/event-centered dimension coverage. Use them before rendering figures
   to confirm which spatial outputs exist, which value columns will be plotted,
   and how many metric/passband/component/model/event/station values are
   represented.

.. autoclass:: spatial_vtk.spatial.plot.SpatialFigureContext
   :members:

.. autoclass:: spatial_vtk.spatial.plot.RegionFigureResult
   :members:

.. autofunction:: spatial_vtk.spatial.plot.prepare_spatial_figure_context

.. autofunction:: spatial_vtk.spatial.plot.write_large_run_geojson_region_figures_from_outputs

.. autofunction:: spatial_vtk.spatial.plot.write_large_run_region_boxplot_from_outputs

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

Public helpers exposed by ``spatial_vtk.spatial.map``:

.. list-table::
   :header-rows: 1

   * - Helper
     - Use
   * - ``plot_station_metric_map`` and ``plot_station_metric_map_by_period``
     - Map station-level metric residuals, including PSA-period sheets.
   * - ``plot_metric_map_by_model`` and ``plot_model_improvement_map``
     - Map model-level residual and model-improvement summaries.
   * - ``plot_residual_grid`` and ``plot_score_map``
     - Map gridded residuals or score summaries from prepared spatial tables.
   * - ``plot_event_residual_map``
     - Map event-level path residuals after event/station filtering.
   * - ``plot_corridor_map``
     - Map selected station-event corridors and boundary-crossing paths.
   * - ``plot_geojson_polygons_map``
     - Map configured GeoJSON regions and preview polygon selections.
   * - ``plot_station_bias_map`` and ``plot_cluster_map``
     - Map station bias and spatial cluster assignments.
   * - ``plot_pca_mode_map`` and ``plot_pca_summary``
     - Map spatial PCA mode scores and summary diagnostics.
