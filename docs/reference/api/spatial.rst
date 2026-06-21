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
       load_standard_spatial_workflow_output_status,
       load_standard_spatial_workflow_outputs,
       load_standard_geojson_workflow_output_status,
       load_standard_geojson_plotting_inputs,
       load_standard_additional_plotting_output_status,
       load_standard_additional_plotting_inputs,
   )

Direct config-backed spatial helpers remain public for scripts, generated
workers, and custom orchestration that already owns execution control:

.. code-block:: python

   from spatial_vtk.spatial import (
       run_geojson_region_summary_workflow_from_config,
       run_boundary_corridor_workflow_from_config,
       build_path_table,
       summarize_residuals_by_path_bin,
   )

Routine notebooks should render standard spatial figures through the result
objects so readiness checks, output paths, sidecars, and figure-family
iteration stay in package code:

.. code-block:: python

   spatial_outputs = load_standard_spatial_workflow_output_status(cfg=cfg)
   spatial_figure_suite = spatial_outputs.write_figure_suite(settings)

Individual plot and map functions are available for focused scripts that
already own filtered spatial tables or resolved map inputs:

.. code-block:: python

   from spatial_vtk.spatial.plot import (
       plot_correlogram,
       plot_distance_correlation_by_metric,
   )
   from spatial_vtk.spatial.map import plot_station_metric_map

.. automodule:: spatial_vtk.spatial
   :members:

Public helpers exposed by ``spatial_vtk.spatial``:

.. list-table::
   :header-rows: 1

   * - Helper
     - Use
   * - ``load_standard_spatial_workflow_output_status``
     - Load lightweight Step 4 output status, readiness gates, Slurm/local
       runner methods, bounded previews, and quick summary figures without
       loading large spatial tables in notebook driver cells.
   * - ``load_standard_spatial_workflow_outputs``
     - Load the standard Step 4 output-table bundle and build per-metric
       product summaries without notebook-local path/table plumbing.
       The returned result also writes the standard Step 4 map and diagnostic
       figure suites through ``write_map_figures()`` and
       ``write_diagnostic_figures()``. Pass ``cfg=`` as either a config object
       or a config file path; the loader resolves all Step 4 paths from that
       config without requiring active global config state.
   * - ``load_standard_geojson_workflow_output_status``
     - Load lightweight Step 5 output status, region/corridor runner methods,
       bounded previews, and large-run region figures without loading full
       GeoJSON or metric tables in notebook driver cells.
   * - ``load_standard_geojson_plotting_inputs``
     - Load standard Step 5 plotting inputs and configured output groups for
       region and corridor figure suites without notebook-local path/table
       plumbing. The Step 3 metric table is read with a spatial event-row
       column projection.
   * - ``load_standard_additional_plotting_output_status``
     - Load lightweight Step 6 output status, bounded metric-source previews,
       waveform comparison writing, and region-boxplot writing for large-run
       notebooks.
   * - ``load_standard_additional_plotting_inputs``
     - Load standard Step 6 plotting inputs and configured output groups for
       waveform, pattern, scatterplot, boxplot, and heatmap figures without
       notebook-local path/table plumbing.
   * - ``run_spatial_statistics_workflow_from_config``
     - Build the configured metric-field, event-centered residual,
       station-bias, Moran's I, distance-correlation, clustering, PCA, and
       geology tables from scripts or generated workers. Routine notebooks
       should usually call this through the standard status result above.
   * - ``run_spatial_derived_outputs_workflow_from_config``
     - Rebuild downstream spatial outputs that depend on existing metric and
       spatial-statistics tables. Pattern-similarity derived outputs read only
       the metric columns they need from path-backed CSV or Parquet inputs.
   * - ``spatial_workflow_failure_frame``
     - Convert non-fatal spatial workflow failures into a stable notebook
       display table without constructing dataframes in tutorial cells.
   * - ``spatial_correlation_preview_frame``
     - Display Moran's I rows plus a bounded number of distance-bin
       correlation rows for one metric without notebook-local filtering.
   * - ``spatial_metric_product_summary_frame``
     - Summarize per-metric Step 4 products such as metric-field,
       event-centered residual, and station-bias rows with row, event, and
       station counts.
   * - ``summarize_standard_spatial_products``
     - Build the per-metric Step 4 product-frame mapping and compact
       summary/preview display tables from configured spatial workflow
       outputs, keeping metric-specific dataframe loops out of notebooks.
   * - ``spatial_metric_table_frame``, ``spatial_metric_product_frames``, and
       ``spatial_pca_product_frames``
     - Select metric-specific rows from Step 4 output tables without repeating
       dataframe filters in notebooks.
   * - ``station_bias_preview_frame``
     - Display bounded station-bias rows for one metric without notebook-local
       ``head()`` calls or repeated preview-column selection.
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
   * - ``geojson_metric_region_frame`` and ``geojson_metric_subset_frame``
     - Annotate and filter metric rows for GeoJSON region plotting without
       repeating label-column and metric-dimension filters in notebooks.
   * - ``build_station_edge_corridors`` and ``select_records_by_corridors``
     - Prepare corridor records for path-focused diagnostics.
   * - ``corridor_record_pair_frame``
     - Return one row per selected corridor event-station pair for maps,
       waveform joins, and downstream subset tables.
   * - ``event_station_records_matching_pairs`` and
       ``geojson_matched_record_frame``
     - Filter record tables by selected event-station pairs or GeoJSON match
       flags without notebook-local merges or boolean masks.
   * - ``corridor_record_preview_frame``
     - Display bounded selected corridor event-station rows without repeating
       preview-column and duplicate-removal logic in notebooks.

Calculate
---------

Notebook and CLI workflows should import spatial statistics, GeoJSON, corridor,
and geometry helpers from the stable ``spatial_vtk.spatial`` package entry
point. ``spatial_vtk.spatial.calculate`` remains a public module for advanced
calculation scripts, while the calculate implementation modules are
implementation organization and are intentionally not listed as notebook-facing
import paths.

.. automodule:: spatial_vtk.spatial.calculate
   :members:

.. autofunction:: spatial_vtk.spatial.spatial_summary_readiness_from_config

.. autofunction:: spatial_vtk.spatial.spatial_derived_outputs_readiness_from_config

.. autofunction:: spatial_vtk.spatial.geojson_region_summary_readiness_from_config

.. autofunction:: spatial_vtk.spatial.boundary_corridor_readiness_from_config

.. autofunction:: spatial_vtk.spatial.spatial_workflow_failure_frame

.. autofunction:: spatial_vtk.spatial.spatial_correlation_preview_frame

.. autofunction:: spatial_vtk.spatial.spatial_metric_product_summary_frame

.. autoclass:: spatial_vtk.spatial.StandardSpatialProductSummaryResult
   :members:

.. autofunction:: spatial_vtk.spatial.summarize_standard_spatial_products

.. autoclass:: spatial_vtk.spatial.StandardSpatialWorkflowOutputResult
   :members:

.. autofunction:: spatial_vtk.spatial.load_standard_spatial_workflow_outputs

.. autoclass:: spatial_vtk.spatial.StandardSpatialWorkflowOutputStatusResult
   :members:

The Step 4 status result remembers the config used to create it, so large-run
notebooks can call ``run_summary_step_if_needed(...)``,
``run_derived_outputs_step_if_needed(...)``,
``display_table_previews(nrows=...)``, ``write_summary_figures(...)``, and
``write_figure_suite(...)``
without repeating readiness checks, Slurm submission plumbing, ``cfg``, or
direct writer imports in each cell. Display the run/skip/submission payload
from the ``run_*_step_if_needed(...)`` methods with
``spatial_vtk.config.display_notebook_step_result`` rather than printing the
raw result object. Display
``StandardSpatialWorkflowOutputStatusResult.status_frame()`` for the compact
configured-output readiness table and
``StandardSpatialWorkflowOutputStatusResult.display_table_previews(...)`` for
bounded summaries of existing spatial outputs.

``StandardSpatialWorkflowOutputResult`` is the standard Step 4 output bundle
for already-loaded notebook workflows. Use its ``status_frame()`` and
``summary_frame()`` methods for configured output status and product row-count
summaries, and use its figure-writing helpers instead of repeating output-path
variables or figure-function imports in notebook cells. The loaded-output
``status_frame()`` preserves ``table`` and ``rows`` while adding normalized
``name``, ``artifact``, ``artifact_label``, ``artifact_role``, ``status``,
``exists``, ``resolved_path``, and ``path`` columns. Rows backed by configured
output paths report ``ready`` or ``missing`` from the filesystem; in-memory
rows without a configured path report ``loaded`` with blank paths.

.. autofunction:: spatial_vtk.spatial.load_standard_spatial_workflow_output_status

.. autofunction:: spatial_vtk.spatial.spatial_metric_table_frame

.. autofunction:: spatial_vtk.spatial.spatial_metric_product_frames

.. autofunction:: spatial_vtk.spatial.spatial_pca_product_frames

.. autofunction:: spatial_vtk.spatial.station_bias_preview_frame

.. autofunction:: spatial_vtk.spatial.corridor_record_preview_frame

.. autofunction:: spatial_vtk.spatial.corridor_record_pair_frame

.. autofunction:: spatial_vtk.spatial.event_station_records_matching_pairs

.. autofunction:: spatial_vtk.spatial.geojson_matched_record_frame

.. autofunction:: spatial_vtk.spatial.geojson_metric_region_frame

.. autofunction:: spatial_vtk.spatial.geojson_metric_subset_frame

Plots
-----

Routine notebooks should render the standard Step 4 figure suite through the
spatial workflow result object:

.. code-block:: python

   from spatial_vtk.spatial import load_standard_spatial_workflow_output_status

   spatial_outputs = load_standard_spatial_workflow_output_status(cfg=cfg)
   spatial_figure_suite = spatial_outputs.write_figure_suite(settings)

Use ``spatial_vtk.spatial.plot`` for public non-map plotting imports in
focused scripts and custom extensions. The implementation submodules are not
part of the tutorial-facing API.

.. code-block:: python

   from spatial_vtk.spatial.plot import (
       plot_correlogram,
       plot_distance_correlation_by_metric,
       plot_semivariogram,
   )

.. automodule:: spatial_vtk.spatial.plot
   :members:

Public plotting helpers and notebook workflow loaders:

.. list-table::
   :header-rows: 1

   * - Helper
     - Use
   * - ``load_standard_spatial_workflow_output_status``
     - Resolve Step 4 output status and retain config-backed methods for
       ``run_summary_step_if_needed(...)``,
       ``run_derived_outputs_step_if_needed(...)``,
       ``display_table_previews(nrows=...)``, ``write_summary_figures(...)``,
       and ``write_figure_suite(...)``. Routine Step 4 notebooks should start
       here so Slurm/local gates, bounded previews, sidecars, and configured
       figure paths stay on the result object.
   * - ``load_standard_spatial_workflow_outputs``
     - Load the standard Step 4 output-table bundle for tutorial-sized runs
       and already-prepared workflows. The returned result writes standard
       Step 4 map and diagnostic figures through ``write_map_figures()`` and
       ``write_diagnostic_figures()`` without notebook-local output-group
       mapping or plot-function imports.
   * - ``load_standard_geojson_workflow_output_status``
     - Resolve Step 5 output status and bounded table previews for large-run
       driver notebooks without loading the full metrics or GeoJSON input
       tables. The status result retains its config for
       ``run_geojson_summary_step_if_needed(...)``,
       ``run_corridor_step_if_needed(...)``,
       ``display_table_previews(nrows=...)`` calls and writes the Step 5
       large-run region/corridor figure family through
       ``write_region_figures()``. ``cfg=`` may be either a config object or a
       config file path, so worker scripts can resolve outputs without active
       global config state.
   * - ``load_standard_geojson_plotting_inputs``
     - Load the standard Step 5 metrics, prepared metadata, comparison-eligible
       records, configured GeoJSON path, and configured output group without
       notebook-local output-group, config-path, or table-loading plumbing;
       the Step 3 metric table is read with only the columns needed by
       spatial event-row GeoJSON figures;
       the returned result can write the standard region and corridor figure
       suites through ``write_region_figures()`` and
       ``write_corridor_figures()``.
   * - ``load_standard_additional_plotting_output_status``
     - Resolve Step 6 output status and the first available metric-source
       preview for large-run driver notebooks without loading the plotting
       inputs. The status result retains its config for
       ``display_metric_source_preview(nrows=...)`` calls and writes bounded
       waveform comparisons plus region boxplots through
       ``write_waveform_comparison()`` and ``write_region_boxplot()``.
       ``cfg=`` may be either a config object or a config file path, so worker
       scripts can resolve outputs without active global config state.
   * - ``load_standard_additional_plotting_inputs``
     - Load the standard Step 6 metric snapshot, event metadata,
       event-station records, comparison-eligible pairs, and configured output
       group without notebook-local output-group or config-table path
       plumbing.
       The returned result writes the standard Step 6 waveform, pattern,
       scatterplot, boxplot, and heatmap figure suite through
       ``write_figures()``.
   * - ``write_large_run_spatial_figure_suite_from_notebook_settings``
     - Lower-level Step 4 figure-suite writer for scripts or compatibility
       paths that already own notebook figure settings. New notebooks should
       usually call
       ``load_standard_spatial_workflow_output_status(...).write_figure_suite(...)``
       so readiness, config, and output bookkeeping stay on the Step 4 result
       object.
   * - ``write_large_run_spatial_summary_figures_from_outputs``
     - Lower-level script helper that writes compact Step 4 spatial summary
       figures from an ``OutputGroup`` after the caller has already resolved
       the configured outputs and plotting keyword arguments.
   * - ``write_standard_spatial_map_figures``
     - Script-facing writer for the standard Step 4 station-bias and
       residual-grid maps when a prepared ``SpatialFigureContext`` and
       settings object are already available.
   * - ``write_standard_spatial_diagnostic_figures``
     - Script-facing writer for the standard Step 4 spatial-correlation,
       PCA-summary, and geology-contrast diagnostic figures when the caller
       already owns the figure context and settings.
   * - ``write_standard_geojson_region_figures``
     - Write the standard Step 5 GeoJSON overview, regional PGA boxplot, and
       regional station residual map while keeping GeoJSON annotation, summary
       table generation, configured figure paths, and sidecar options in
       package code. The returned ``StandardGeoJSONFigureResult`` exposes
       ``summary_frame()`` and ``status_frame()`` for written region figures
       and source-row sidecars. Its status frame includes normalized
       ``name``, ``artifact_label``, ``artifact_role``, ``status``,
       ``resolved_path``, ``path``, and ``exists`` columns while preserving
       ``figure_path`` and
       ``figure_exists``.
   * - ``write_standard_geojson_corridor_figures``
     - Write the standard Step 5 boundary-corridor maps, boundary-crossing
       waveform record section, and outward-corridor PGV station map while
       keeping corridor construction, selected-record joins, waveform
       selection, metric filtering, figure paths, and preview tables in
       package code. The returned ``StandardGeoJSONCorridorFigureResult``
       exposes ``status_frame()`` for corridor figure paths, statuses,
       messages, and sidecars. Its status frame uses the same normalized
       figure path columns as the standard region figure result.
   * - ``write_standard_additional_plotting_figures``
     - Write the standard Step 6 waveform map, pattern-similarity figure,
       residual scatterplot, region boxplot, and region heatmap while keeping
       waveform selection, GeoJSON metric annotation, figure paths, sidecars,
       and preview tables in package code. The returned
       ``StandardAdditionalPlottingFigureResult`` exposes
       ``metric_summary_frame()`` for selected metric coverage and
       ``status_frame()`` for figure outputs with normalized figure path
       columns, including ``artifact_role`` and ``status``.
   * - ``write_large_run_geojson_region_figures_from_outputs``
     - Lower-level Step 5 script helper that writes the GeoJSON overview map,
       corridor map, and region boxplot from configured output groups after
       the caller has decided to bypass the standard plotting input/result
       object.
   * - ``write_large_run_geojson_region_figures_from_notebook_settings``
     - Compatibility helper for scripts that need the Step 5 GeoJSON/corridor
       figure family directly from ``notebook_figure_settings(...)``. New
       notebooks should usually call
       ``load_standard_geojson_workflow_output_status(...).write_region_figures(...)``
       or ``load_standard_geojson_plotting_inputs(...).write_region_figures(...)``.
   * - ``write_large_run_region_boxplot_from_outputs``
     - Lower-level Step 5/6 script helper that writes one region boxplot from
       an ``OutputGroup``, preferring an enriched metric table when available
       and falling back to the long metric table.
   * - ``write_large_run_region_boxplot_from_notebook_settings``
     - Compatibility helper for scripts that need the Step 6 region boxplot
       directly from ``notebook_figure_settings(...)``. New notebooks should
       usually call
       ``load_standard_additional_plotting_output_status(...).write_region_boxplot(...)``.
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
     - Plot custom spatial metric distributions from prepared tables.
   * - ``plot_geology_contrast`` and ``plot_path_bin_summary``
     - Plot geologic-class and path-bin diagnostic tables.
   * - ``plot_pca_explained_variance`` and ``plot_pca_feature_loadings``
     - Plot PCA spatial-mode diagnostics.

Large-Run Spatial Figure Suite
------------------------------

Notebook-facing spatial plotting should use the result-object and suite helpers
below. These helpers keep table readiness checks, spatial filtering, PSA
period-sheet handling, station aggregation, sidecar metadata, render gates, and
registered output paths in package code instead of notebook cells.

Use ``SpatialFigureContext`` for Step 4-style spatial diagnostics that should
reuse the same filtering, PSA period-sheet handling, station aggregation, and
sidecar metadata conventions as the metric figure workflow. The context
delegates metric-field and event-centered residual tables to the appropriate
metric figure context, so station maps, residual grids, and model maps use the
same row factories and aggregation audit metadata across Step 3 and Step 4.
Metric-field and event-centered figure items carry an internal owner tag so
writer methods do not have to infer ownership from overlapping dataframe
schemas.

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
   represented. ``status_frame`` uses ``resolved_path`` as the clear path
   column while preserving ``path`` for compatibility.

``SpatialFigureSuiteResult.context_status_frames`` and
``SpatialFigureSuiteResult.display_context_status(...)``
   Return or display the context status, dimension summary, and PSA/FAS
   spectral-contract audit tables used by large-run Step 4 notebooks. Use
   these result-owned methods instead of branching in notebook cells to decide
   which readiness tables are safe to display.

``SpatialFigureSuiteResult.status_frame``
   Returns one row per spatial figure family with exact ``figure_paths``,
   ``first_figure_path``, ``figure_paths_preview``, and normalized ``name``,
   ``artifact_label``, ``artifact_role``, ``status``, ``resolved_path``,
   ``path``, and ``exists`` columns keyed to the first figure in each family.

``spectral_metric_contract_status``
   Return a compact PSA/FAS audit table for both ``metric_field`` and
   ``event_centered_residuals``. Use it before spatial figure rendering to
   catch legacy passband-scoped spectral rows that should be rebuilt as
   broadband PSA/FAS rows split by ``period_s``.

GeoJSON and region plotting status tables use ``resolved_path`` as the clear
notebook-facing path column while preserving ``path`` as a compatibility alias.
Figure-specific result tables that already expose ``figure_path`` keep that
descriptive column. Standard Step 4 map/diagnostic/summary result tables,
Step 5 GeoJSON/corridor result tables, Step 6 additional-plotting result
tables, and region-specific result tables share the same normalized
``artifact_label``, ``artifact_role``, ``status``, ``resolved_path``, ``path``,
and ``exists`` vocabulary.

Advanced Spatial Figure Extension Helpers
-----------------------------------------

The context builders in this section are public for custom scripts and
extension code, but they are not the preferred tutorial or notebook entry
points. New notebooks should call
``load_standard_spatial_workflow_output_status(...).write_figure_suite(...)``
or the standard workflow result-object figure methods so the package owns
readiness checks, output bookkeeping, sidecars, and figure-family iteration.

``prepare_spatial_figure_context``
   Build a reusable ``SpatialFigureContext`` for scripts that need to control
   large-run spatial filtering, station aggregation, PSA-period handling, and
   sidecar metadata before rendering selected figure families.

``prepare_spatial_figure_context_from_notebook_settings``
   Compatibility helper for scripts that need a ``SpatialFigureContext`` built
   from ``notebook_figure_settings(...)``.

``RegionFigureResult`` and ``RegionBoxplotResult``
   Return normalized ``status_frame()`` tables with ``name``,
   ``artifact_label``, ``artifact_role``, ``status``, ``resolved_path``,
   ``path``, and ``exists`` columns while preserving sidecar path fields for
   figure provenance.

.. autoclass:: spatial_vtk.spatial.plot.SpatialFigureContext
   :members:

.. autoclass:: spatial_vtk.spatial.plot.RegionFigureResult
   :members:

.. autofunction:: spatial_vtk.spatial.plot.prepare_spatial_figure_context

.. autofunction:: spatial_vtk.spatial.plot.prepare_spatial_figure_context_from_notebook_settings

.. autoclass:: spatial_vtk.spatial.plot.SpatialFigureSuiteResult
   :members:

.. autofunction:: spatial_vtk.spatial.plot.write_large_run_spatial_figure_suite_from_notebook_settings

.. autoclass:: spatial_vtk.spatial.plot.SpatialSummaryFigureResult
   :members:

.. autofunction:: spatial_vtk.spatial.plot.write_large_run_spatial_summary_figures_from_outputs

.. autofunction:: spatial_vtk.spatial.plot.write_standard_spatial_map_figures

.. autofunction:: spatial_vtk.spatial.plot.write_standard_spatial_diagnostic_figures

.. autoclass:: spatial_vtk.spatial.plot.StandardGeoJSONFigureResult
   :members:

.. autofunction:: spatial_vtk.spatial.plot.write_standard_geojson_region_figures

.. autoclass:: spatial_vtk.spatial.plot.StandardGeoJSONCorridorFigureResult
   :members:

.. autofunction:: spatial_vtk.spatial.plot.write_standard_geojson_corridor_figures

.. autoclass:: spatial_vtk.spatial.plot.StandardGeoJSONPlottingInputResult
   :members:

``StandardGeoJSONPlottingInputResult.status_frame()`` reports loaded Step 5
inputs with normalized ``name``, ``table``, ``artifact_label``,
``artifact_role``, ``status``, ``exists``, ``resolved_path``, and ``path``
columns. The GeoJSON row is path-backed; in-memory dataframes report
``status="loaded"`` and preserve row counts without requiring notebooks to
resolve paths.

.. autofunction:: spatial_vtk.spatial.load_standard_geojson_plotting_inputs

.. autoclass:: spatial_vtk.spatial.plot.StandardGeoJSONWorkflowOutputStatusResult
   :members:

.. autofunction:: spatial_vtk.spatial.load_standard_geojson_workflow_output_status

.. autoclass:: spatial_vtk.spatial.plot.StandardAdditionalPlottingInputResult
   :members:

``StandardAdditionalPlottingInputResult.status_frame()`` uses the same
normalized input-status schema for Step 6 metric, event-station, event, and
comparison-eligible inputs while preserving the simple ``table`` and ``rows``
columns used by existing notebooks.

.. autofunction:: spatial_vtk.spatial.load_standard_additional_plotting_inputs

.. autoclass:: spatial_vtk.spatial.plot.StandardAdditionalPlottingOutputStatusResult
   :members:

.. autofunction:: spatial_vtk.spatial.load_standard_additional_plotting_output_status

.. autoclass:: spatial_vtk.spatial.plot.StandardAdditionalPlottingFigureResult
   :members:

.. autofunction:: spatial_vtk.spatial.plot.write_standard_additional_plotting_figures

.. autofunction:: spatial_vtk.spatial.plot.write_large_run_geojson_region_figures_from_outputs

.. autofunction:: spatial_vtk.spatial.plot.write_large_run_geojson_region_figures_from_notebook_settings

.. autofunction:: spatial_vtk.spatial.plot.write_large_run_region_boxplot_from_outputs

.. autofunction:: spatial_vtk.spatial.plot.write_large_run_region_boxplot_from_notebook_settings

Maps
----

Routine notebooks should use the standard spatial and plotting result helpers
first so the package owns output paths, figure families, render gates, and
sidecars. Use ``spatial_vtk.spatial.map`` for public map imports in focused
scripts and custom extensions that already own filtered metric tables or
resolved map inputs.

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
