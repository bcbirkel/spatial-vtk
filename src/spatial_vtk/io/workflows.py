"""Config-backed IO workflow helpers for notebooks and batch scripts.

Purpose
-------
This module groups small, reusable workflow entry points that combine existing
IO primitives with the configured output registry. Public notebooks can call
these helpers directly, and Slurm wrappers can import the same helpers instead
of embedding task-specific Python in notebook cells.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from spatial_vtk.config import SpatialVTKConfig, active_config, resolve_output_path
from spatial_vtk.io.preprocessing import (
    preprocessed_waveform_metadata_paths,
    preprocess_waveform_files,
)
from spatial_vtk.io.tables import load_output_table, write_output_table
from spatial_vtk.io.metadata import (
    prepare_event_metadata,
    prepare_event_station_table,
    prepare_station_metadata,
)


def prepare_metadata_tables_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Prepare configured station, event, and event-station metadata tables.

    Parameters
    ----------
    config_path
        Spatial-VTK config file. When omitted, the active/discoverable config is
        used.
    run_scenario
        Optional named run scenario overlay.
    overwrite
        Whether to rebuild existing prepared metadata outputs.

    Returns
    -------
    dict
        Summary with written output paths and row counts.
    """

    cfg = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    station_path = resolve_output_path("prepared_stations", kind="table", cfg=cfg, create_parent=True)
    event_path = resolve_output_path("prepared_events", kind="table", cfg=cfg, create_parent=True)
    event_station_path = resolve_output_path("event_station_records", kind="table", cfg=cfg, create_parent=True)

    if not overwrite and station_path.exists() and event_path.exists() and event_station_path.exists():
        stations = load_output_table("prepared_stations", cfg=cfg)
        events = load_output_table("prepared_events", cfg=cfg)
        event_stations = load_output_table("event_station_records", cfg=cfg)
        return {
            "prepared_stations_path": str(station_path),
            "prepared_events_path": str(event_path),
            "event_station_records_path": str(event_station_path),
            "station_rows": int(len(stations)),
            "event_rows": int(len(events)),
            "event_station_rows": int(len(event_stations)),
            "reused": True,
        }

    stations = prepare_station_metadata()
    events = prepare_event_metadata()
    event_stations = prepare_event_station_table(station_metadata=stations, event_metadata=events)
    written_station_path = write_output_table("prepared_stations", stations, cfg=cfg)
    written_event_path = write_output_table("prepared_events", events, cfg=cfg)
    written_event_station_path = write_output_table("event_station_records", event_stations, cfg=cfg)
    return {
        "prepared_stations_path": str(written_station_path),
        "prepared_events_path": str(written_event_path),
        "event_station_records_path": str(written_event_station_path),
        "station_rows": int(len(stations)),
        "event_rows": int(len(events)),
        "event_station_rows": int(len(event_stations)),
        "reused": False,
    }


def preprocess_waveforms_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    overwrite: bool = False,
    continue_on_error: bool = True,
    verbose: bool = True,
) -> dict[str, Any]:
    """Preprocess configured event-station waveforms and return written paths.

    Parameters
    ----------
    config_path
        Spatial-VTK config file. When omitted, the active/discoverable config is
        used.
    run_scenario
        Optional named run scenario overlay.
    overwrite
        Whether to rewrite existing processed waveform files and metadata.
    continue_on_error
        Whether missing/unreadable waveform files should be recorded in the
        preprocessing manifest instead of stopping the workflow.
    verbose
        Print preprocessing progress messages.

    Returns
    -------
    dict
        Summary with event-station, manifest, trace-metadata paths and row
        counts.
    """

    cfg = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    event_station_records = resolve_output_path("event_station_records", kind="table", cfg=cfg)
    result = preprocess_waveform_files(
        event_station_records,
        config=cfg,
        overwrite=overwrite,
        continue_on_error=continue_on_error,
        verbose=verbose,
    )
    return {
        "preprocessed_event_station_records_path": str(result.event_station_path),
        "preprocessing_manifest_path": str(result.manifest_path),
        "preprocessed_trace_metadata_path": str(result.trace_metadata_path),
        "event_station_records": str(result.event_station_path),
        "manifest": str(result.manifest_path),
        "trace_metadata": str(result.trace_metadata_path),
        "manifest_rows": int(len(result.manifest)),
        "trace_metadata_rows": int(len(result.trace_metadata)),
        "event_station_rows": int(len(result.event_station_records)),
    }


def build_record_coverage_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    component: str | None = None,
    observed_source: str = "observed",
    synthetic_source: str = "synthetic",
    source_type_col: str = "source_type",
    on_missing_source: str = "drop",
    on_missing_metadata: str = "drop",
) -> dict[str, Any]:
    """Build configured record coverage from preprocessed trace metadata.

    Parameters
    ----------
    config_path
        Spatial-VTK config file. When omitted, the active/discoverable config is
        used.
    run_scenario
        Optional named run scenario overlay.
    component
        Optional component to select before pairing observed/synthetic traces.
    observed_source, synthetic_source, source_type_col
        Source labels and source-type column passed to
        :func:`build_record_coverage_table_from_trace_metadata`.
    on_missing_source, on_missing_metadata
        Missing-data behavior passed to the record-coverage builder.

    Returns
    -------
    dict
        Summary with input/output paths and row count.
    """

    cfg = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    from spatial_vtk.visualize.context.figures import build_record_coverage_table_from_trace_metadata

    preprocessing_paths = preprocessed_waveform_metadata_paths(config=cfg)
    event_station_records = (
        preprocessing_paths.event_station_path
        if preprocessing_paths.event_station_path.exists()
        else resolve_output_path("event_station_records", kind="table", cfg=cfg)
    )
    record_coverage = build_record_coverage_table_from_trace_metadata(
        preprocessing_paths.trace_metadata_path,
        event_station_df=event_station_records,
        component=component,
        observed_source=observed_source,
        synthetic_source=synthetic_source,
        source_type_col=source_type_col,
        on_missing_source=on_missing_source,
        on_missing_metadata=on_missing_metadata,
    )
    output_path = write_output_table("record_coverage", record_coverage, cfg=cfg)
    return {
        "record_coverage_path": str(output_path),
        "preprocessed_trace_metadata_path": str(preprocessing_paths.trace_metadata_path),
        "event_station_records_path": str(event_station_records),
        "record_coverage": str(output_path),
        "trace_metadata": str(preprocessing_paths.trace_metadata_path),
        "event_stations": str(event_station_records),
        "rows": int(len(record_coverage)),
    }


def _workflow_config(*, config_path: str | Path | None, run_scenario: str | None) -> SpatialVTKConfig:
    """Return an activated config for a package workflow helper."""

    if config_path is not None:
        return SpatialVTKConfig.from_file(config_path, run_scenario=run_scenario).activate()
    cfg = active_config()
    if run_scenario:
        return SpatialVTKConfig.from_file(cfg.config_path, run_scenario=run_scenario).activate()
    return cfg


__all__ = [
    "build_record_coverage_from_config",
    "prepare_metadata_tables_from_config",
    "preprocess_waveforms_from_config",
]
