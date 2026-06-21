"""Stable input/output helpers for configured Spatial-VTK workflows.

``spatial_vtk.io`` is the public import surface for metadata preparation,
waveform preprocessing, output groups, registered table I/O, readiness checks,
and bounded table previews. Routine notebooks should start here instead of
reaching into lower-level metadata, preprocessing, table, output-path, or
manifest modules for path plumbing.

The package keeps this broad public surface lazy: importing ``spatial_vtk.io``
does not import table, waveform, preprocessing, or workflow implementations
until the requested helper is accessed.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MODULES = {
    "ArtifactRecord": "spatial_vtk.io.artifacts",
    "ArtifactRegistry": "spatial_vtk.io.artifacts",
    "ArtifactSpec": "spatial_vtk.io.artifacts",
    "DEFAULT_WAVEFORM_SUFFIXES": "spatial_vtk.io.inventory",
    "DEFAULT_SOURCE_COLUMN_CANDIDATES": "spatial_vtk.io.preprocessing",
    "MetricPlan": "spatial_vtk.io.plans",
    "MetricCompleteness": "spatial_vtk.io.plans",
    "ModelFolderCandidate": "spatial_vtk.io.model_aliases",
    "ModelResolution": "spatial_vtk.io.model_aliases",
    "METRIC_QC_COLUMNS": "spatial_vtk.io.metric_inputs",
    "METRIC_WAVEFORM_COLUMNS": "spatial_vtk.io.metric_inputs",
    "MetadataPreparationResult": "spatial_vtk.io.workflows",
    "OUTPUT_GROUPS": "spatial_vtk.io.output_paths",
    "OutputArtifact": "spatial_vtk.io.output_paths",
    "OutputGroup": "spatial_vtk.io.output_paths",
    "OutputReadiness": "spatial_vtk.io.output_paths",
    "PreprocessedWaveformMetadataPaths": "spatial_vtk.io.preprocessing",
    "PreprocessedWaveform": "spatial_vtk.io.waveforms",
    "RecordCoverageWorkflowResult": "spatial_vtk.io.workflows",
    "SyntheticFormatInfo": "spatial_vtk.io.synthetic_formats",
    "StandardIngestWorkflowOutputResult": "spatial_vtk.io.workflows",
    "WaveformPreprocessing": "spatial_vtk.io.waveforms",
    "WaveformPreprocessingSummaryResult": "spatial_vtk.io.workflows",
    "WaveformPreprocessingWorkflowResult": "spatial_vtk.io.preprocessing",
    "atomic_write_csv": "spatial_vtk.io.compute_manifest",
    "aggregate_metric_by_station_over_events": "spatial_vtk.io.tables",
    "apply_waveform_preprocessing": "spatial_vtk.io.waveforms",
    "apply_waveform_preprocessing_with_metadata": "spatial_vtk.io.waveforms",
    "artifact_manifest_path": "spatial_vtk.io.artifacts",
    "artifact_path_for_spec": "spatial_vtk.io.artifacts",
    "available_base_models": "spatial_vtk.io.model_aliases",
    "build_master_event_list": "spatial_vtk.io.master_lists",
    "build_master_station_list": "spatial_vtk.io.master_lists",
    "build_file_inventory": "spatial_vtk.io.inventory",
    "build_observed_synthetic_inventory": "spatial_vtk.io.inventory",
    "build_record_coverage_from_config": "spatial_vtk.io.workflows",
    "classify_model_folder": "spatial_vtk.io.model_aliases",
    "compare_metric_plan_to_table": "spatial_vtk.io.plans",
    "comparison_qc_passed": "spatial_vtk.io.metric_inputs",
    "compute_sha256": "spatial_vtk.io.inventory",
    "canonical_json": "spatial_vtk.io.artifacts",
    "context_dataset_paths": "spatial_vtk.io.catalogs",
    "default_output_paths": "spatial_vtk.io.output_paths",
    "ensure_run_dir": "spatial_vtk.io.compute_manifest",
    "event_display_label": "spatial_vtk.io.metadata",
    "event_ids_from_records": "spatial_vtk.io.metadata",
    "event_label_preview_frame": "spatial_vtk.io.metadata",
    "event_rows_for_records": "spatial_vtk.io.metadata",
    "expected_metric_rows_from_inventory": "spatial_vtk.io.plans",
    "first_nonempty_table_value": "spatial_vtk.io.tables",
    "inspect_synthetic_format": "spatial_vtk.io.synthetic_formats",
    "inspect_station_event_layouts": "spatial_vtk.io.layouts",
    "load_csv_bundle": "spatial_vtk.io.tables",
    "load_configured_input_paths": "spatial_vtk.io.workflows",
    "load_configured_input_tables": "spatial_vtk.io.workflows",
    "load_standard_ingest_workflow_outputs": "spatial_vtk.io.workflows",
    "metadata_tables_readiness_from_config": "spatial_vtk.io.workflows",
    "load_or_build_output_table": "spatial_vtk.io.tables",
    "load_output_table": "spatial_vtk.io.tables",
    "metric_plan_from_config": "spatial_vtk.io.plans",
    "metric_qc_lookup": "spatial_vtk.io.metric_inputs",
    "metric_qc_passed": "spatial_vtk.io.metric_inputs",
    "normalize_metric_table": "spatial_vtk.io.tables",
    "normalize_metric_qc_table": "spatial_vtk.io.metric_inputs",
    "normalize_metric_waveform_inventory": "spatial_vtk.io.metric_inputs",
    "normalize_event_table": "spatial_vtk.io.master_lists",
    "normalize_model_alias": "spatial_vtk.io.model_aliases",
    "normalize_station_table": "spatial_vtk.io.master_lists",
    "output_group_artifacts": "spatial_vtk.io.output_paths",
    "output_group": "spatial_vtk.io.output_paths",
    "output_group_completion": "spatial_vtk.io.output_paths",
    "output_group_namespace": "spatial_vtk.io.output_paths",
    "output_group_paths": "spatial_vtk.io.output_paths",
    "output_group_status": "spatial_vtk.io.output_paths",
    "output_group_status_frame": "spatial_vtk.io.output_paths",
    "output_readiness": "spatial_vtk.io.output_paths",
    "output_status_frame": "spatial_vtk.io.output_paths",
    "output_status_rows": "spatial_vtk.io.output_paths",
    "prepare_event_metadata": "spatial_vtk.io.metadata",
    "prepare_event_station_table": "spatial_vtk.io.metadata",
    "prepare_station_metadata": "spatial_vtk.io.metadata",
    "preview_output_table": "spatial_vtk.io.tables",
    "preview_table": "spatial_vtk.io.tables",
    "preprocessing_readiness_from_config": "spatial_vtk.io.workflows",
    "preprocessed_waveform_metadata_paths": "spatial_vtk.io.preprocessing",
    "preprocessed_waveform_output_group": "spatial_vtk.io.preprocessing",
    "prepare_metadata_tables_from_config": "spatial_vtk.io.workflows",
    "preprocess_waveforms_from_config": "spatial_vtk.io.workflows",
    "preprocess_stream": "spatial_vtk.io.waveforms",
    "preprocess_waveform_files": "spatial_vtk.io.preprocessing",
    "record_coverage_readiness_from_config": "spatial_vtk.io.workflows",
    "read_event_patch_table": "spatial_vtk.io.catalogs",
    "read_artifact_manifest": "spatial_vtk.io.artifacts",
    "read_bounded_table": "spatial_vtk.io.tables",
    "read_config_table": "spatial_vtk.io.tables",
    "read_event_metadata": "spatial_vtk.io.metadata",
    "read_events": "spatial_vtk.io.catalogs",
    "read_event_station_table": "spatial_vtk.io.metadata",
    "read_json": "spatial_vtk.io.compute_manifest",
    "read_stations": "spatial_vtk.io.catalogs",
    "read_station_metadata": "spatial_vtk.io.metadata",
    "read_table": "spatial_vtk.io.tables",
    "read_waveform_file": "spatial_vtk.io.waveforms",
    "resolve_model_aliases": "spatial_vtk.io.model_aliases",
    "required_outputs_exist": "spatial_vtk.io.output_paths",
    "scan_synthetic_model_folders": "spatial_vtk.io.model_aliases",
    "slugify": "spatial_vtk.io.artifacts",
    "stable_hash": "spatial_vtk.io.artifacts",
    "stream_station_table": "spatial_vtk.io.waveforms",
    "synthetic_reader_for": "spatial_vtk.io.synthetic_formats",
    "should_rebuild_paths": "spatial_vtk.io.output_paths",
    "should_rebuild_outputs": "spatial_vtk.io.output_paths",
    "trace_metadata_table": "spatial_vtk.io.waveforms",
    "utc_run_id": "spatial_vtk.io.compute_manifest",
    "waveform_preprocessing_from_config": "spatial_vtk.io.waveforms",
    "waveform_preprocessing_label": "spatial_vtk.io.waveforms",
    "wide_to_long_metrics": "spatial_vtk.io.tables",
    "write_artifact_manifest": "spatial_vtk.io.artifacts",
    "write_master_event_list": "spatial_vtk.io.master_lists",
    "write_master_station_list": "spatial_vtk.io.master_lists",
    "write_station_event_kml": "spatial_vtk.io.kml",
    "write_named_tables": "spatial_vtk.io.tables",
    "write_output_table": "spatial_vtk.io.tables",
    "write_output_tables": "spatial_vtk.io.tables",
    "write_table": "spatial_vtk.io.tables",
    "write_trace_metadata_csv": "spatial_vtk.io.waveforms",
    "written_files_table": "spatial_vtk.io.tables",
    "write_json": "spatial_vtk.io.compute_manifest",
    "load_waveform_collection": "spatial_vtk.io.waveforms",
}

__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    """Load one public I/O helper lazily.

    Parameters
    ----------
    name
        Public attribute requested from ``spatial_vtk.io``.

    Returns
    -------
    object
        The requested public helper.
    """

    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module 'spatial_vtk.io' has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
