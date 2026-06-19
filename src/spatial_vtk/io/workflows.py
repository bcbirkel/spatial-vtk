"""Config-backed IO workflow helpers for notebooks and batch scripts.

Purpose
-------
This module groups small, reusable workflow entry points that combine existing
IO primitives with the configured output registry. Public notebooks can call
these helpers directly, and Slurm wrappers can import the same helpers instead
of embedding task-specific Python in notebook cells.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from spatial_vtk.config import SpatialVTKConfig, active_config, resolve_output_path
from spatial_vtk.io.output_paths import OutputReadiness, output_group
from spatial_vtk.io.preprocessing import (
    preprocessed_waveform_output_group,
    preprocess_waveform_files,
)
from spatial_vtk.io.tables import load_output_table, read_config_table, write_output_table
from spatial_vtk.io.metadata import (
    prepare_event_metadata,
    prepare_event_station_table,
    prepare_station_metadata,
)


@dataclass(frozen=True)
class StandardIngestWorkflowOutputResult:
    """Configured Step 1 output groups and preview helpers."""

    outputs: Any
    preprocessed_outputs: Any
    cfg: SpatialVTKConfig | None = None

    def status_frame(self) -> Any:
        """Return combined Step 1 ingest and preprocessing output status."""

        return self.outputs.status_frame(extra_paths=self.preprocessed_outputs.as_dict())

    def display_station_preview(
        self,
        *,
        nrows: int = 5,
        display_fn: Any | None = None,
    ) -> dict[str, object]:
        """Display a bounded preview of the prepared station table."""

        return self.outputs.display_table_previews(
            {"stations": "prepared_stations_path"},
            cfg=self.cfg,
            nrows=nrows,
            display_fn=display_fn,
        )

    def display_event_preview(
        self,
        *,
        nrows: int = 5,
        display_fn: Any | None = None,
    ) -> dict[str, object]:
        """Display a bounded preview of the prepared event table."""

        return self.outputs.display_table_previews(
            {"events": "prepared_events_path"},
            cfg=self.cfg,
            nrows=nrows,
            display_fn=display_fn,
        )

    def metadata_summary_frame(self, *, missing: Literal["raise", "skip"] = "skip") -> pd.DataFrame:
        """Return row counts for the prepared Step 1 metadata tables.

        This helper keeps tutorial notebooks from loading the prepared station,
        event, and event-station tables only to print basic counts. The current
        implementation still reads available tables through the configured
        output group, so future row-count optimizations can happen here without
        changing notebook cells.
        """

        rows: list[dict[str, object]] = []
        table_specs = [
            ("stations", "prepared_stations", "prepared_stations_path"),
            ("events", "prepared_events", "prepared_events_path"),
            ("event_stations", "event_station_records", "event_station_path"),
        ]
        for label, output_key, path_name in table_specs:
            path = getattr(self.outputs, path_name, None)
            path_text = None if path is None else str(path)
            status = "missing"
            row_count: int | None = None
            table = self.outputs.load_table(path_name, cfg=self.cfg, missing=missing)
            if table is not None:
                row_count = int(len(table))
                status = "ready"
            rows.append(
                {
                    "table": label,
                    "output_key": output_key,
                    "output_path": path_text,
                    "resolved_path": path_text,
                    "path": path_text,
                    "status": status,
                    "row_count": row_count,
                }
            )
        return pd.DataFrame(
            rows,
            columns=["table", "output_key", "resolved_path", "path", "output_path", "status", "row_count"],
        )

    def display_preprocessing_manifest_preview(
        self,
        *,
        nrows: int = 5,
        columns: Sequence[str] | None = ("source", "event_id", "status", "processing", "trace_count"),
        display_fn: Any | None = None,
    ) -> dict[str, object]:
        """Display a bounded preview of the waveform preprocessing manifest."""

        return self.preprocessed_outputs.display_path_table_previews(
            {"preprocessing_manifest": "preprocessed_manifest_path"},
            nrows=nrows,
            columns=columns,
            display_fn=display_fn,
        )


def load_standard_ingest_workflow_outputs(
    *,
    cfg: SpatialVTKConfig | None = None,
    ingest_group_name: str = "step_01_ingest",
) -> StandardIngestWorkflowOutputResult:
    """Load standard Step 1 ingest and preprocessing output handles.

    Parameters
    ----------
    cfg
        Active Spatial-VTK config. When omitted, the active config is used by
        the underlying output-group helpers.
    ingest_group_name
        Configured output group that owns prepared metadata and context figure
        outputs.

    Returns
    -------
    StandardIngestWorkflowOutputResult
        Configured Step 1 output group, preprocessed-waveform output group,
        combined status frame, and common preview helpers.
    """

    return StandardIngestWorkflowOutputResult(
        outputs=output_group(ingest_group_name, cfg=cfg),
        preprocessed_outputs=preprocessed_waveform_output_group(config=cfg),
        cfg=cfg,
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


def metadata_tables_readiness_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    ingest_group_name: str = "step_01_ingest",
    overwrite: bool = False,
    current_message: str | None = "Prepared metadata tables are current; skipping.",
    rebuild_message: str | None = None,
) -> OutputReadiness:
    """Return readiness for configured prepared station/event metadata tables.

    This helper owns the Step 1 metadata output contract used before calling
    :func:`prepare_metadata_tables_from_config`. It checks configured output
    paths and freshness only; it does not load the potentially large prepared
    tables.
    """

    cfg = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    outputs = output_group(ingest_group_name, cfg=cfg)
    return outputs.readiness(
        ("prepared_stations_path", "prepared_events_path", "event_station_path"),
        overwrite=overwrite,
        current_message=current_message,
        rebuild_message=rebuild_message,
    )


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
        "preprocessed_manifest_path": str(result.manifest_path),
        "preprocessing_manifest_path": str(result.manifest_path),
        "preprocessed_trace_metadata_path": str(result.trace_metadata_path),
        "event_station_records": str(result.event_station_path),
        "manifest": str(result.manifest_path),
        "trace_metadata": str(result.trace_metadata_path),
        "manifest_rows": int(len(result.manifest)),
        "trace_metadata_rows": int(len(result.trace_metadata)),
        "event_station_rows": int(len(result.event_station_records)),
    }


def preprocessing_readiness_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    overwrite: bool = False,
    missing_input_message: str | None = "Event-station records are not ready yet.",
    current_message: str | None = "Preprocessed waveform metadata is current; skipping preprocessing submission.",
    rebuild_message: str | None = None,
) -> OutputReadiness:
    """Return readiness for configured waveform preprocessing metadata outputs.

    Waveform preprocessing writes metadata under the preprocessed waveform root
    instead of the standard output-table directory. This helper keeps that
    location and the required ``event_station_records`` dependency in package
    code so notebooks can stay focused on the workflow step.
    """

    cfg = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    ingest_outputs = load_standard_ingest_workflow_outputs(cfg=cfg)
    step_outputs = ingest_outputs.outputs
    preprocessed_outputs = ingest_outputs.preprocessed_outputs
    return preprocessed_outputs.readiness(
        ("preprocessed_event_station_path", "preprocessed_trace_metadata_path", "preprocessed_manifest_path"),
        inputs={"event_station_path": step_outputs.event_station_path},
        sources={"event_station_path": step_outputs.event_station_path},
        overwrite=overwrite,
        missing_input_message=missing_input_message,
        current_message=current_message,
        rebuild_message=rebuild_message,
    )


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
    from spatial_vtk.visualize.context import build_record_coverage_table_from_trace_metadata

    ingest_outputs = load_standard_ingest_workflow_outputs(cfg=cfg)
    step_outputs = ingest_outputs.outputs
    preprocessed_outputs = ingest_outputs.preprocessed_outputs
    event_station_records = (
        preprocessed_outputs.preprocessed_event_station_path
        if preprocessed_outputs.preprocessed_event_station_path.exists()
        else step_outputs.event_station_path
    )
    record_coverage = build_record_coverage_table_from_trace_metadata(
        preprocessed_outputs.preprocessed_trace_metadata_path,
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
        "preprocessed_trace_metadata_path": str(preprocessed_outputs.preprocessed_trace_metadata_path),
        "event_station_records_path": str(event_station_records),
        "record_coverage": str(output_path),
        "trace_metadata": str(preprocessed_outputs.preprocessed_trace_metadata_path),
        "event_stations": str(event_station_records),
        "rows": int(len(record_coverage)),
    }


def record_coverage_readiness_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    overwrite: bool = False,
    missing_input_message: str = "Trace metadata or event-station records are not ready yet.",
    current_message: str = "Record coverage table is current; skipping.",
    rebuild_message: str | None = None,
) -> OutputReadiness:
    """Return the configured record-coverage rebuild decision.

    The record-coverage workflow prefers the preprocessed event-station table
    when preprocessing has written it, and falls back to the base
    ``event_station_records`` output otherwise. This helper exposes that same
    fallback as an :class:`~spatial_vtk.io.OutputReadiness` object so notebooks
    do not have to duplicate path-selection logic before calling
    :func:`build_record_coverage_from_config`.
    """

    cfg = _workflow_config(config_path=config_path, run_scenario=run_scenario)
    ingest_outputs = load_standard_ingest_workflow_outputs(cfg=cfg)
    step_outputs = ingest_outputs.outputs
    preprocessed_outputs = ingest_outputs.preprocessed_outputs
    event_station_records = (
        preprocessed_outputs.preprocessed_event_station_path
        if preprocessed_outputs.preprocessed_event_station_path.exists()
        else step_outputs.event_station_path
    )
    dependencies = {
        "preprocessed_trace_metadata_path": preprocessed_outputs.preprocessed_trace_metadata_path,
        "event_station_records_path": event_station_records,
    }
    return step_outputs.readiness(
        "record_coverage_path",
        inputs=dependencies,
        sources=dependencies,
        overwrite=overwrite,
        missing_input_message=missing_input_message,
        current_message=current_message,
        rebuild_message=rebuild_message,
    )


def load_configured_input_tables(
    tables: Mapping[str, str] | Sequence[str],
    *,
    cfg: SpatialVTKConfig | None = None,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    **read_kwargs: Any,
) -> dict[str, Any]:
    """Load named input tables from configured dotted path keys.

    This helper is intended for notebooks that need configured input tables
    that are not standard workflow outputs, such as ``paths.metric_figure_snapshot``
    or ``paths.site_metadata``. It keeps cells focused on the task by replacing
    repeated direct ``read_config_table("paths...")`` calls with a small,
    labeled table bundle.

    Parameters
    ----------
    tables
        Mapping of user-facing table labels to dotted config path keys, or a
        sequence of dotted config path keys. For sequences, labels are derived
        from the final dotted-key segment.
    cfg
        Optional active config object. When omitted, ``config_path`` or the
        active config is used.
    config_path, run_scenario
        Optional config file and run scenario used when ``cfg`` is omitted.
    **read_kwargs
        Additional keyword arguments passed through to :func:`read_config_table`.

    Returns
    -------
    dict
        Mapping of labels to loaded pandas dataframes.
    """

    if cfg is not None and (config_path is not None or run_scenario is not None):
        raise ValueError("Pass either cfg or config_path/run_scenario, not both.")
    config = (
        cfg
        if cfg is not None
        else _workflow_config(config_path=config_path, run_scenario=run_scenario)
    )
    table_map = _configured_input_table_map(tables)
    return {label: read_config_table(dotted_key, cfg=config, **read_kwargs) for label, dotted_key in table_map.items()}


def load_configured_input_paths(
    paths: Mapping[str, str] | Sequence[str],
    *,
    cfg: SpatialVTKConfig | None = None,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    must_exist: bool = True,
    create_parent: bool = False,
) -> dict[str, Path | None]:
    """Resolve named input paths from configured dotted path keys.

    This helper is intended for notebooks that need configured non-table inputs
    such as ``paths.region_geojson``. It keeps cells from calling ``cfg.path``
    directly while still returning explicit, descriptive ``label -> Path``
    mappings that plotting and spatial helper calls can use.

    Parameters
    ----------
    paths
        Mapping of user-facing labels to dotted config path keys, or a sequence
        of dotted config path keys. For sequences, labels are derived from the
        final dotted-key segment.
    cfg
        Optional active config object. When omitted, ``config_path`` or the
        active config is used.
    config_path, run_scenario
        Optional config file and run scenario used when ``cfg`` is omitted.
    must_exist
        Whether each configured path must exist. Set ``False`` for optional
        inputs that should be reported by a later render/readiness gate.
    create_parent
        Whether to create each path's parent directory while resolving it.

    Returns
    -------
    dict
        Mapping of labels to resolved paths, or ``None`` for empty optional
        config values when ``must_exist`` is ``False``.
    """

    if cfg is not None and (config_path is not None or run_scenario is not None):
        raise ValueError("Pass either cfg or config_path/run_scenario, not both.")
    config = cfg if cfg is not None else _workflow_config(config_path=config_path, run_scenario=run_scenario)
    path_map = _configured_input_key_map(paths, kind="path")
    return {
        label: config.path(dotted_key, must_exist=must_exist, create_parent=create_parent)
        for label, dotted_key in path_map.items()
    }


def _workflow_config(*, config_path: str | Path | None, run_scenario: str | None) -> SpatialVTKConfig:
    """Return an activated config for a package workflow helper."""

    if config_path is not None:
        return SpatialVTKConfig.from_file(config_path, run_scenario=run_scenario).activate()
    cfg = active_config()
    if run_scenario:
        return SpatialVTKConfig.from_file(cfg.config_path, run_scenario=run_scenario).activate()
    return cfg


def _configured_input_table_map(tables: Mapping[str, str] | Sequence[str]) -> dict[str, str]:
    """Normalize configured input table labels and dotted keys."""

    return _configured_input_key_map(tables, kind="table")


def _configured_input_key_map(
    values: Mapping[str, str] | Sequence[str],
    *,
    kind: str,
) -> dict[str, str]:
    """Normalize configured input labels and dotted keys."""

    if isinstance(values, Mapping):
        value_map = {str(label): str(dotted_key) for label, dotted_key in values.items()}
    else:
        if isinstance(values, (str, bytes)):
            raise TypeError(
                f"{kind}s must be a mapping or a sequence of dotted config keys, not a string."
            )
        value_map = {str(dotted_key).rsplit(".", 1)[-1]: str(dotted_key) for dotted_key in values}
    if not value_map:
        raise ValueError(f"At least one configured input {kind} must be requested.")
    for label, dotted_key in value_map.items():
        if not label:
            raise ValueError(f"Configured input {kind} labels must be non-empty.")
        if "." not in dotted_key:
            raise ValueError(f"Configured input {kind} key {dotted_key!r} must be a dotted config path key.")
    return value_map


__all__ = [
    "build_record_coverage_from_config",
    "load_configured_input_paths",
    "load_configured_input_tables",
    "load_standard_ingest_workflow_outputs",
    "metadata_tables_readiness_from_config",
    "prepare_metadata_tables_from_config",
    "preprocessing_readiness_from_config",
    "preprocess_waveforms_from_config",
    "record_coverage_readiness_from_config",
    "StandardIngestWorkflowOutputResult",
]
