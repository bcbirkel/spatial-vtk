Input and Output API
====================

The I/O modules prepare station and event metadata, discover waveform files,
write standard output artifacts, and handle preprocessing products used by the
rest of the workflow.

.. contents:: On this page
   :local:
   :depth: 2

Package Entry Point
-------------------

Start with ``spatial_vtk.io`` in notebooks and scripts. These helpers cover the
routine workflow surface: metadata normalization, event-station table creation,
preprocessing products, table I/O, output groups, readiness checks, and bounded
table previews. Prefer these imports before reaching into implementation
modules.

.. code-block:: python

   from spatial_vtk.io import (
       load_configured_input_paths,
       load_configured_input_tables,
       output_group,
       prepare_event_metadata,
       prepare_event_station_table,
       prepare_station_metadata,
       preprocessed_waveform_output_group,
       preprocess_waveform_files,
       record_coverage_readiness_from_config,
       read_config_table,
       write_output_table,
   )

.. automodule:: spatial_vtk.io
   :members:

Public helpers exposed by ``spatial_vtk.io``:

.. list-table::
   :header-rows: 1

   * - Helper
     - Use
   * - ``output_group``
     - Resolve a named workflow output group once and use attributes,
       ``status_frame()``, ``readiness()``, ``load_table()``,
       ``preview_table()``, ``load_tables()``, ``preview_tables()``, and
       ``display_table_previews()`` instead of repeating output-path variables
       or preview loops in notebooks. Use
       ``display_first_existing_table_preview()`` when a notebook should prefer
       a derived table, such as ``metrics_enriched``, but fall back to an
       earlier table, such as ``metrics_long``. Use ``figure_path()`` when a
       notebook needs a metric-specific figure filename beside a registered
       configured figure path. ``status_frame()`` and
       ``output_group_status_frame()`` include ``output_key``, ``kind``, and
       ``required`` columns for registered artifacts, so notebooks can display
       which configured table, figure, or dashboard output each path row
       represents. For path-backed artifacts outside the registered output
       table registry, such as preprocessing manifests, use
       ``display_path_table_previews()`` so notebooks still print the owning
       path and display bounded rows through the output group.
   * - ``preprocessed_waveform_output_group``
     - Resolve preprocessing metadata outputs that live under the configured
       preprocessed-waveform metadata directory.
   * - ``output_readiness`` and ``OutputReadiness``
     - Gate local or Slurm-backed work on missing, stale, blocked, or reusable
       outputs. Required input mappings may use ``None`` for an optional
       config path that is not set; readiness reports the input as
       ``<not configured>`` and blocks dependent work with the
       ``missing_inputs`` reason instead of fabricating a filesystem path.
   * - ``load_configured_input_tables``
     - Load optional input tables from dotted config path keys such as
       ``paths.metric_figure_snapshot`` or ``paths.site_metadata``.
   * - ``load_configured_input_paths``
     - Resolve optional non-table inputs from dotted config path keys, such as
       ``paths.region_geojson``, without putting direct ``cfg.path`` calls in
       notebook cells.
   * - ``event_display_label``
     - Return a human-readable event label for notebook titles and displays,
       falling back to the event id instead of raising when a label is missing.
   * - ``event_ids_from_records``, ``event_rows_for_records``, and
       ``event_label_preview_frame``
     - Extract event IDs, select matching event metadata rows, and build
       compact event-label preview tables without notebook-local dataframe
       filtering or fragile ``iloc`` lookups.
   * - ``first_nonempty_table_value``
     - Return a safe first non-empty value from an optional table column for
       notebook titles, labels, and summaries, with a fallback when the column
       is missing or empty.
   * - ``prepare_metadata_tables_from_config``
     - Normalize station, event, and event-station metadata and write the
       standard Step 1 tables.
   * - ``preprocess_waveforms_from_config``
     - Read configured waveform sources, reuse existing preprocessed files when
       possible, and write preprocessing metadata.
   * - ``record_coverage_readiness_from_config``
     - Check whether record coverage should be rebuilt from preprocessed trace
       metadata.
   * - ``build_record_coverage_from_config``
     - Build and write the configured record-coverage table.
   * - ``read_bounded_table`` and ``preview_table``
     - Inspect large CSV or Parquet tables without loading all rows.
   * - ``write_output_table`` and ``load_output_table``
     - Read and write registered output tables when lower-level table access is
       required.

Metadata and Inventories
------------------------

.. automodule:: spatial_vtk.io.metadata
   :members:

.. automodule:: spatial_vtk.io.inventory
   :members:

.. automodule:: spatial_vtk.io.master_lists
   :members:

.. automodule:: spatial_vtk.io.metric_inputs
   :members:

Waveforms and Preprocessing
---------------------------

.. automodule:: spatial_vtk.io.waveforms
   :members:

.. automodule:: spatial_vtk.io.preprocessing
   :members:

Notebook Workflow Helpers
-------------------------

Use these config-backed helpers from notebooks or scripts when a workflow step
should use the same Python package function locally and inside Slurm workers.

.. automodule:: spatial_vtk.io.workflows
   :members:

Tables and Artifacts
--------------------

.. automodule:: spatial_vtk.io.tables
   :members:

.. automodule:: spatial_vtk.io.output_paths
   :members:

.. automodule:: spatial_vtk.io.artifacts
   :members:

.. automodule:: spatial_vtk.io.compute_manifest
   :members:

.. automodule:: spatial_vtk.io.plans
   :members:

Catalogs and File Formats
-------------------------

.. automodule:: spatial_vtk.io.catalogs
   :members:

.. automodule:: spatial_vtk.io.synthetic_formats
   :members:

.. automodule:: spatial_vtk.io.model_aliases
   :members:

Geospatial and Layout Exports
-----------------------------

.. automodule:: spatial_vtk.io.kml
   :members:

.. automodule:: spatial_vtk.io.layouts
   :members:
