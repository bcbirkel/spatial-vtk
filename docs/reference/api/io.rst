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
       load_standard_ingest_workflow_outputs,
       metadata_tables_readiness_from_config,
       metric_plan_from_config,
       prepare_event_metadata,
       prepare_event_station_table,
       prepare_station_metadata,
       prepare_metadata_tables_from_config,
       preprocessing_readiness_from_config,
       preprocess_waveforms_from_config,
       record_coverage_readiness_from_config,
       build_record_coverage_from_config,
   )

.. automodule:: spatial_vtk.io
   :members:

Public helpers exposed by ``spatial_vtk.io``:

.. list-table::
   :header-rows: 1

   * - Helper
     - Use
   * - ``load_standard_ingest_workflow_outputs``
     - Load the standard Step 1 ingest output group, preprocessing metadata
       output group, combined status frame, lightweight metadata row-count
       summary, and bounded station/event/manifest preview helpers for
       tutorial notebooks.
       The returned result also writes the standard Step 1 context figure
       suite through ``write_context_figures()`` and owns the notebook-facing
       large-run driver methods ``run_metadata_step_if_needed()``,
       ``run_preprocessing_step_if_needed()``, and
       ``run_record_coverage_step_if_needed()``.
   * - ``MetadataPreparationResult``
     - Report prepared metadata output paths and row counts with
       mapping-compatible access, ``summary_message()`` for scripts and logs,
       and ``summary_frame()`` for notebook display helpers.
   * - ``WaveformPreprocessingSummaryResult``
     - Report preprocessed event-station, manifest, and trace-metadata outputs
       with mapping-compatible access plus notebook summary helpers.
   * - ``WaveformPreprocessingWorkflowResult``
     - Return the full preprocessing dataframes and written path artifacts from
       direct preprocessing calls. ``status_frame()`` reports preprocessed
       event-station, manifest, and trace-metadata artifacts with normalized
       names, roles, readiness status, paths, and row counts.
   * - ``RecordCoverageWorkflowResult``
     - Report the record-coverage output and the exact trace metadata and
       event-station inputs used to build it.
   * - ``output_group``
     - Lower-level configured output-group helper for custom scripts or new
       reusable package helpers when no standard workflow result object exists
       yet. It resolves a named workflow output group once and exposes
       attributes, ``status_frame()``, ``readiness()``, ``load_table()``,
       ``preview_table()``, ``load_tables()``, ``preview_tables()``, and
       ``display_table_previews()``. Use ``preview_table()`` and
       ``preview_tables()`` for bounded table previews; reserve
       ``load_table()`` and ``load_tables()`` for explicit full-table reads in
       package helpers or analysis cells. Use
       ``display_first_existing_table_preview()`` when a custom helper should
       prefer a derived table, such as ``metrics_enriched``, but fall back to
       an earlier table, such as ``metrics_long``. Use ``figure_path()`` when
       a helper needs a metric-specific figure filename beside a registered
       configured figure path. ``status_frame()`` and
       ``output_group_status_frame()`` include clear ``resolved_path`` values
       plus ``output_key``, ``kind``, ``required``, ``artifact_label``,
       ``readiness``, ``message``, and ``suggested_action`` columns for
       registered artifacts. For path-backed artifacts outside the registered
       output table registry, such as preprocessing manifests, use
       ``display_path_table_previews()`` so custom helpers still print the
       owning path and display bounded rows through the output group. ``cfg=``
       may be a ``SpatialVTKConfig`` object or a config file path, which keeps
       worker scripts from activating global config before resolving output
       groups.
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
   * - ``load_output_table``, ``preview_output_table``,
       ``write_output_table``, ``write_output_tables``, and
       ``read_config_table``
     - Read and write registered output tables or configured input tables.
       Each helper accepts ``cfg=`` as either a ``SpatialVTKConfig`` object or
       a config file path, so worker scripts can resolve configured paths
       without activating global config state. Use ``preview_output_table`` for
       bounded notebook previews of large CSV/Parquet outputs.
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
   * - ``metric_plan_from_config`` and ``MetricPlan``
     - Resolve metric names, passbands, components, models, spectral periods,
       waveform preprocessing choices, overlap settings, and the configured
       metric output path from a config or run scenario.
       ``MetricPlan.summary_frame()`` returns a compact notebook display table,
       so configuration notebooks can inspect the active metric plan without
       printing a raw dataclass.
   * - ``prepare_metadata_tables_from_config``
     - Normalize station, event, and event-station metadata and write the
       standard Step 1 tables.
   * - ``metadata_tables_readiness_from_config``
     - Check whether configured prepared station, event, and event-station
       metadata tables are missing, stale, current, or forced by ``overwrite``
       without loading the tables in notebook cells.
   * - ``preprocess_waveforms_from_config``
     - Read configured waveform sources, reuse existing preprocessed files when
       possible, and write preprocessing metadata. Returns a
       ``WaveformPreprocessingSummaryResult`` with bounded display helpers.
   * - ``preprocessing_readiness_from_config``
     - Check whether preprocessing metadata outputs and their
       ``event_station_records`` dependency are ready without duplicating
       preprocessed metadata path names in notebook cells.
   * - ``record_coverage_readiness_from_config``
     - Check whether record coverage should be rebuilt from preprocessed trace
       metadata.
   * - ``build_record_coverage_from_config``
     - Build and write the configured record-coverage table. Returns a
       ``RecordCoverageWorkflowResult`` with input/output path provenance and
       row counts.
   * - ``read_bounded_table`` and ``preview_table``
     - Inspect large CSV or Parquet tables without loading all rows.
   * - ``table_row_count``
     - Count CSV or Parquet table rows without materializing the table. CSV
       inputs are streamed and Parquet inputs use metadata.
   * - ``parquet_table_columns`` and ``parquet_table_row_count``
     - Inspect Parquet schemas and row counts through metadata only. These
       helpers fail with actionable PyArrow/metadata errors instead of
       materializing large tables as a fallback.
   * - ``write_output_table`` and ``load_output_table``
     - Read and write registered output tables when lower-level table access is
       required.

Metadata and Inventories
------------------------

Routine notebooks should import metadata preparation, event/station matching,
and configured table helpers from ``spatial_vtk.io``. The modules below are
documented for API completeness and advanced scripts; they are implementation
organization for tutorial notebooks.

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

Routine notebooks should start with standard workflow result loaders and
bounded preview helpers from ``spatial_vtk.io``. Use ``output_group()`` only
when no standard workflow result helper exists for the step yet, or when an
advanced script needs direct access to a configured group of artifacts. The
lower-level table, output-path, artifact, manifest, and plan modules are
documented for scripts and package extension points, not as notebook
path-plumbing examples.

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
