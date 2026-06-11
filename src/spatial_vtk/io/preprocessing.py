"""File-based waveform preprocessing workflow.

Purpose
-------
This module makes waveform preprocessing a first-class Spatial-VTK workflow
step. It filters and/or resamples observed and synthetic waveform files once,
writes processed copies, and returns an updated event-station table that later
QC, metric, and figure steps can consume directly.

Usage examples
--------------
Preprocess observed and synthetic paths listed in an event-station table:
  ``preprocess_waveform_files("event_stations.csv", "outputs/preprocessed", config=cfg)``

Use explicit preprocessing settings:
  ``preprocess_waveform_files(records, "outputs/preprocessed", preprocessing=WaveformPreprocessing(lowpass_hz=1.0, resample_hz=20.0))``
"""

from __future__ import annotations

from dataclasses import dataclass
import glob
from pathlib import Path
from typing import Any, Mapping
import pickle
import warnings

import pandas as pd

from spatial_vtk.io.tables import read_table, write_table
from spatial_vtk.io.waveforms import (
    WaveformPreprocessing,
    preprocess_stream,
    read_waveform_file,
    trace_metadata_table,
    waveform_preprocessing_from_config,
    waveform_preprocessing_label,
)


DEFAULT_SOURCE_COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "observed": ("observed_mseed", "observed_waveform", "observed_pickle", "obs_waveform_path", "obs_path"),
    "synthetic": ("synthetic_mseed", "synthetic_waveform", "synthetic_pickle", "syn_waveform_path", "syn_path"),
}
CONFIG_TEMPLATE_KEYS: dict[str, tuple[str, ...]] = {
    "observed": ("paths.observed_template", "paths.observed_root"),
    "synthetic": ("paths.synthetic_template", "paths.synthetic_root"),
}
CONFIG_ROOT_KEYS: dict[str, tuple[str, ...]] = {
    "observed": ("paths.observed_root",),
    "synthetic": ("paths.synthetic_root",),
}
EVENT_ID_COLUMN_CANDIDATES = (
    "event_id",
    "eventid",
    "event",
    "event_name",
    "eventname",
    "event_title",
    "eventtitle",
    "id",
    "source_id",
    "origin_id",
)
PREPROCESSING_WAVEFORM_SUFFIX_PRIORITY: dict[str, int] = {
    ".asdf": 0,
    ".mseed": 1,
    ".msd": 1,
    ".ms": 1,
    ".sac": 2,
    ".pkl": 3,
    ".pickle": 3,
    ".npz": 4,
    ".npy": 4,
    ".h5": 5,
    ".hdf5": 5,
}


@dataclass(frozen=True)
class WaveformPreprocessingWorkflowResult:
    """Outputs written by :func:`preprocess_waveform_files`.

    Parameters
    ----------
    event_station_records
        Updated event-station table.
    event_station_path
        Path where the updated event-station table was written.
    manifest
        One row per source waveform file.
    manifest_path
        Path where the preprocessing manifest was written.
    trace_metadata
        One row per processed trace.
    trace_metadata_path
        Path where trace metadata was written.

    Returns
    -------
    WaveformPreprocessingWorkflowResult
        Immutable workflow result with dataframes and written paths.
    """

    event_station_records: pd.DataFrame
    event_station_path: Path
    manifest: pd.DataFrame
    manifest_path: Path
    trace_metadata: pd.DataFrame
    trace_metadata_path: Path


def preprocess_waveform_files(
    event_station_records: pd.DataFrame | str | Path,
    output_root: str | Path | None = None,
    *,
    source_columns: Mapping[str, str] | None = None,
    preprocessing: WaveformPreprocessing | None = None,
    config: Any | None = None,
    event_id_col: str = "event_id",
    overwrite: bool = False,
    continue_on_error: bool = False,
    replace_input_columns: bool = True,
    drop_unprocessed_rows: bool = True,
    verbose: bool = False,
    event_station_name: str = "event_station_records_preprocessed.csv",
    manifest_name: str = "waveform_preprocessing_manifest.csv",
    trace_metadata_name: str = "trace_metadata_preprocessed.csv",
) -> WaveformPreprocessingWorkflowResult:
    """Preprocess waveform files and write reusable processed copies.

    Parameters
    ----------
    event_station_records
        DataFrame or CSV/Parquet path with event IDs and waveform paths.
    output_root
        Folder where processed waveforms and metadata tables will be written.
        When omitted, ``outputs.preprocessed_waveforms`` is read from
        ``config`` or the active Spatial-VTK config.
    source_columns
        Optional mapping such as ``{"observed": "observed_mseed"}``. When
        omitted, common observed/synthetic waveform column names are detected.
    preprocessing
        Explicit preprocessing settings. When omitted, settings are read from
        ``config`` or from the active Spatial-VTK config.
    config
        Optional Spatial-VTK config used only when ``preprocessing`` is omitted.
    event_id_col
        Column containing event IDs.
    overwrite
        Replace existing processed waveform files when true.
    continue_on_error
        Record failed files in the manifest and continue when true. The default
        is to raise a clear error so downstream steps do not use missing files.
    replace_input_columns
        When true, the original waveform path columns are replaced with
        processed paths while raw paths are preserved in ``*_raw_waveform``.
    drop_unprocessed_rows
        When true, rows that did not resolve to any processed waveform path
        are removed from the returned/written event-station table. Disable this
        only when you need to audit the full input table, including unavailable
        waveform records.
    verbose
        Print progress messages while resolving and preprocessing waveform
        files. This is useful in notebooks for long-running ASDF/MiniSEED
        preprocessing.
    event_station_name, manifest_name, trace_metadata_name
        Output filenames written under ``output_root/metadata``.

    Returns
    -------
    WaveformPreprocessingWorkflowResult
        Updated table, manifest, trace metadata, and their written paths.
    """

    records = read_table(event_station_records) if not isinstance(event_station_records, pd.DataFrame) else event_station_records.copy()
    records = _ensure_event_id_column(records, event_id_col=event_id_col)
    if event_id_col not in records.columns:
        raise ValueError(f"Event-station records must include an {event_id_col!r} column.")
    settings = preprocessing or waveform_preprocessing_from_config(config)
    records = _add_configured_waveform_paths(records, config=config, event_id_col=event_id_col)
    columns = _resolve_source_columns(records, source_columns)
    if not columns:
        expected = sorted({candidate for values in DEFAULT_SOURCE_COLUMN_CANDIDATES.values() for candidate in values})
        raise ValueError(f"No waveform path columns were found. Provide source_columns or add one of: {expected}")
    _validate_source_columns(
        records,
        columns=columns,
        config=config,
        event_id_col=event_id_col,
        allow_missing_paths=continue_on_error,
    )

    root = _resolve_output_root(output_root, config)
    _progress(verbose, f"Preprocessing waveforms into {root}")
    _progress(verbose, f"Resolved waveform sources: {', '.join(sorted(columns))}")
    metadata_dir = root / "metadata"
    event_station_path = metadata_dir / event_station_name
    manifest_path = metadata_dir / manifest_name
    trace_metadata_path = metadata_dir / trace_metadata_name
    metadata_dir.mkdir(parents=True, exist_ok=True)
    cached_trace_metadata = _index_cached_trace_metadata(trace_metadata_path)
    updated = records.copy()
    manifest_rows: list[dict[str, Any]] = []
    trace_frames: list[pd.DataFrame] = []
    processed_lookup: dict[tuple[str, str, str], Path] = {}
    processed_columns: list[str] = []

    for source, column in columns.items():
        raw_column = f"{source}_raw_waveform"
        processed_column = f"{source}_processed_waveform"
        preprocessing_column = f"{source}_waveform_preprocessing"
        processed_columns.append(processed_column)
        if raw_column not in updated.columns:
            updated[raw_column] = updated[column]
        else:
            raw_missing = updated[raw_column].map(_path_cell_text).eq("")
            source_present = updated[column].map(_path_cell_text).ne("")
            updated.loc[raw_missing & source_present, raw_column] = updated.loc[raw_missing & source_present, column]
        updated[processed_column] = ""
        updated[preprocessing_column] = ""
        source_records = records.loc[records[column].map(_path_cell_text).ne("")]
        source_groups = list(source_records.groupby([event_id_col, column], sort=False))
        _progress(verbose, f"{source}: {len(source_groups)} unique event waveform file(s) from column {column!r}")
        for item_index, (key, group) in enumerate(source_groups, start=1):
            event_id, input_value = key
            input_path = Path(_path_cell_text(input_value)).expanduser()
            lookup_key = (source, str(event_id), str(input_path))
            output_path = processed_lookup.get(lookup_key)
            if output_path is None:
                output_path = _processed_output_path(root, source, str(event_id), input_path)
                processed_lookup[lookup_key] = output_path
                action = "Reusing" if output_path.exists() and not overwrite else "Writing"
                _progress(
                    verbose,
                    f"{source} {item_index}/{len(source_groups)} event {event_id}: "
                    f"{action.lower()} {output_path.name}",
                )
                manifest_row, trace_frame = _preprocess_one_file(
                    input_path,
                    output_path,
                    source=source,
                    event_id=str(event_id),
                    settings=settings,
                    overwrite=overwrite,
                    cached_metadata=_cached_trace_metadata_for_output(cached_trace_metadata, output_path) if not overwrite else None,
                )
                manifest_rows.append(manifest_row)
                status = str(manifest_row.get("status", "unknown"))
                trace_count = int(manifest_row.get("trace_count", 0) or 0)
                _progress(verbose, f"{source} event {event_id}: {status} ({trace_count} trace(s))")
                if manifest_row.get("status") == "error" and not continue_on_error:
                    raise RuntimeError(
                        f"Failed to preprocess {source} waveform for event {event_id}: "
                        f"{manifest_row.get('message', '')}"
                    )
                if trace_frame is not None and not trace_frame.empty:
                    trace_frames.append(trace_frame)
            row_index = group.index
            updated.loc[row_index, processed_column] = str(output_path)
            updated.loc[row_index, preprocessing_column] = waveform_preprocessing_label(settings)
            if replace_input_columns:
                updated.loc[row_index, column] = str(output_path)

    if drop_unprocessed_rows and processed_columns:
        keep_mask = pd.Series(False, index=updated.index)
        for processed_column in processed_columns:
            if processed_column in updated.columns:
                keep_mask |= updated[processed_column].map(_path_cell_text).ne("")
        dropped = int((~keep_mask).sum())
        if dropped:
            _progress(verbose, f"Dropped {dropped} event-station row(s) without processed waveform paths")
        updated = updated.loc[keep_mask].reset_index(drop=True)

    manifest = pd.DataFrame(manifest_rows)
    trace_metadata = pd.concat(trace_frames, ignore_index=True) if trace_frames else pd.DataFrame()
    write_table(updated, event_station_path)
    write_table(manifest, manifest_path)
    write_table(trace_metadata, trace_metadata_path)
    _progress(verbose, f"Wrote event-station records: {event_station_path}")
    _progress(verbose, f"Wrote preprocessing manifest: {manifest_path}")
    _progress(verbose, f"Wrote trace metadata: {trace_metadata_path}")
    return WaveformPreprocessingWorkflowResult(
        event_station_records=updated,
        event_station_path=event_station_path,
        manifest=manifest,
        manifest_path=manifest_path,
        trace_metadata=trace_metadata,
        trace_metadata_path=trace_metadata_path,
    )


def _progress(verbose: bool, message: str) -> None:
    """Print one flushed progress message when verbose mode is enabled."""

    if verbose:
        print(message, flush=True)


def _resolve_source_columns(records: pd.DataFrame, source_columns: Mapping[str, str] | None) -> dict[str, str]:
    """Find observed/synthetic waveform path columns in an event-station table."""

    if source_columns:
        missing = {source: column for source, column in source_columns.items() if column not in records.columns}
        if missing:
            raise ValueError(f"Configured waveform source columns are missing from the event-station table: {missing}")
        return {str(source).strip().lower(): column for source, column in source_columns.items()}
    resolved: dict[str, str] = {}
    for source, candidates in DEFAULT_SOURCE_COLUMN_CANDIDATES.items():
        for candidate in candidates:
            if candidate in records.columns and _column_has_path_values(records[candidate]):
                resolved[source] = candidate
                break
    return resolved


def _validate_source_columns(
    records: pd.DataFrame,
    *,
    columns: Mapping[str, str],
    config: Any | None,
    event_id_col: str,
    allow_missing_paths: bool = False,
) -> None:
    """Raise when configured waveform sources did not resolve usable paths."""

    configured_sources = _configured_sources(config)
    for source in configured_sources:
        if source not in columns:
            raise ValueError(
                f"{source.capitalize()} waveform input is configured, but no {source} waveform path column was resolved. "
                f"Check {', '.join((*CONFIG_TEMPLATE_KEYS[source], *CONFIG_ROOT_KEYS[source]))}."
            )
    for source, column in columns.items():
        has_path = records[column].map(_path_cell_text).ne("")
        if has_path.all() or source not in configured_sources or allow_missing_paths:
            continue
        missing = records.loc[~has_path, event_id_col].dropna().astype(str)
        event_preview = missing.drop_duplicates().head(10).tolist()
        resolved_count = int(has_path.sum())
        total_count = int(len(records))
        if resolved_count == 0:
            detail = "no files matched the configured paths"
        else:
            detail = f"{total_count - resolved_count} of {total_count} row(s) did not match a configured file"
        raise ValueError(
            f"{source.capitalize()} waveform input is configured, but {detail}. "
            f"Check {', '.join((*CONFIG_TEMPLATE_KEYS[source], *CONFIG_ROOT_KEYS[source]))}. "
            f"Example unmatched event IDs: {event_preview}. "
            "Pass continue_on_error=True only if you intentionally want a partial event-station table."
        )


def _configured_sources(config: Any | None) -> set[str]:
    """Return waveform sources with config template/root settings."""

    cfg = config
    if cfg is None:
        try:
            from spatial_vtk.config import SpatialVTKConfig

            cfg = SpatialVTKConfig.active()
        except Exception:
            cfg = None
    if cfg is None or not hasattr(cfg, "section"):
        return set()
    configured: set[str] = set()
    for source in DEFAULT_SOURCE_COLUMN_CANDIDATES:
        keys = (*CONFIG_TEMPLATE_KEYS[source], *CONFIG_ROOT_KEYS[source])
        if any(cfg.section(key) for key in keys):
            configured.add(source)
    return configured


def _ensure_event_id_column(records: pd.DataFrame, *, event_id_col: str) -> pd.DataFrame:
    """Rename a common event identifier alias to the requested event ID column."""

    if event_id_col in records.columns:
        return records
    lookup = {_normalize_column_name(column): str(column) for column in records.columns}
    for candidate in EVENT_ID_COLUMN_CANDIDATES:
        source = lookup.get(_normalize_column_name(candidate))
        if source is not None:
            return records.rename(columns={source: event_id_col})
    return records


def _normalize_column_name(name: object) -> str:
    """Normalize one column name for permissive alias matching."""

    return "".join(character for character in str(name).strip().lower() if character.isalnum())


def _add_configured_waveform_paths(records: pd.DataFrame, *, config: Any | None, event_id_col: str) -> pd.DataFrame:
    """Fill standard waveform path columns from config roots/templates."""

    cfg = config
    if cfg is None:
        try:
            from spatial_vtk.config import SpatialVTKConfig

            cfg = SpatialVTKConfig.active()
        except Exception:
            cfg = None
    if cfg is None:
        return records

    out = records.copy()
    if not _has_usable_source_column(out, "observed"):
        observed_paths = _waveform_paths_from_templates(out, cfg=cfg, template_keys=CONFIG_TEMPLATE_KEYS["observed"])
        if observed_paths is None:
            observed_paths = _waveform_paths_from_roots(out[event_id_col], cfg=cfg, root_keys=CONFIG_ROOT_KEYS["observed"])
        if observed_paths is not None:
            out["observed_waveform"] = observed_paths
    if not _has_usable_source_column(out, "synthetic"):
        synthetic_paths = _waveform_paths_from_templates(out, cfg=cfg, template_keys=CONFIG_TEMPLATE_KEYS["synthetic"])
        if synthetic_paths is None:
            synthetic_paths = _waveform_paths_from_roots(out[event_id_col], cfg=cfg, root_keys=CONFIG_ROOT_KEYS["synthetic"])
        if synthetic_paths is not None:
            out["synthetic_waveform"] = synthetic_paths
    return out


def _has_usable_source_column(records: pd.DataFrame, source: str) -> bool:
    """Return whether records include one recognized source column with paths."""

    return any(
        column in records.columns and _column_has_path_values(records[column])
        for column in DEFAULT_SOURCE_COLUMN_CANDIDATES[source]
    )


def _column_has_path_values(series: pd.Series) -> bool:
    """Return whether a path column has at least one non-empty path value."""

    return any(_path_cell_text(value) for value in series)


def _path_cell_text(value: object) -> str:
    """Return one waveform path cell as text, treating missing values as blank."""

    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    return "" if text.lower() in {"", "nan", "none", "null"} else text


def _waveform_paths_from_templates(records: pd.DataFrame, *, cfg: Any, template_keys: tuple[str, ...]) -> pd.Series | None:
    """Resolve waveform paths from the first configured template that matches."""

    for template_key in template_keys:
        paths = _waveform_paths_from_template(records, cfg=cfg, template_key=template_key)
        if paths is not None:
            return paths
    return None


def _waveform_paths_from_roots(event_ids: pd.Series, *, cfg: Any, root_keys: tuple[str, ...]) -> pd.Series | None:
    """Resolve waveform paths from the first configured root that matches."""

    for root_key in root_keys:
        paths = _waveform_paths_from_root(event_ids, cfg=cfg, root_key=root_key)
        if paths is not None:
            return paths
    return None


def _waveform_paths_from_root(event_ids: pd.Series, *, cfg: Any, root_key: str) -> pd.Series | None:
    """Resolve one event-level waveform path per event from a configured root."""

    root = _config_path(cfg, root_key)
    if root is None:
        return None
    path_by_event = _index_waveform_root(root)
    paths = event_ids.astype(str).str.strip().map(path_by_event).fillna("")
    return paths if paths.astype(bool).any() else None


def _waveform_paths_from_template(records: pd.DataFrame, *, cfg: Any, template_key: str) -> pd.Series | None:
    """Resolve one event-level waveform path per row from a configured template."""

    template = cfg.section(template_key) if hasattr(cfg, "section") else None
    if not template:
        return None
    if "{" not in str(template):
        return None
    paths = records.apply(lambda row: _resolve_template_row(row, cfg=cfg, template=str(template)), axis=1)
    return paths if paths.astype(bool).any() else None


def _config_path(cfg: Any, dotted_key: str) -> Path | None:
    """Resolve one config path when the config object supports the runtime API."""

    if not hasattr(cfg, "path"):
        return None
    try:
        return cfg.path(dotted_key)
    except Exception:
        return None


def _index_waveform_root(root: Path) -> dict[str, str]:
    """Map event IDs to waveform files found directly or recursively under root."""

    if not root.exists():
        return {}
    suffixes = set(PREPROCESSING_WAVEFORM_SUFFIX_PRIORITY)
    paths = [path for path in sorted(root.rglob("*")) if path.is_file() and path.suffix.lower() in suffixes]
    by_event: dict[str, Path] = {}
    for path in paths:
        for key in (path.name, path.stem):
            current = by_event.get(key)
            if current is None or _waveform_suffix_rank(path) < _waveform_suffix_rank(current):
                by_event[key] = path
    return {key: str(path) for key, path in by_event.items()}


def _waveform_suffix_rank(path: Path) -> int:
    """Return the preprocessing preference rank for one waveform suffix."""

    return PREPROCESSING_WAVEFORM_SUFFIX_PRIORITY.get(path.suffix.lower(), 999)


def _resolve_template_row(row: pd.Series, *, cfg: Any, template: str) -> str:
    """Resolve a configured waveform template for one event-station row."""

    values = {key: value for key, value in row.items() if pd.notna(value)}
    if "model" not in values:
        models = cfg.section("metrics.models", []) if hasattr(cfg, "section") else []
        if isinstance(models, (list, tuple)) and len(models) == 1:
            values["model"] = models[0]
    try:
        formatted = cfg.format_template(template, **values) if hasattr(cfg, "format_template") else template.format(**values)
    except KeyError:
        return ""
    resolved = cfg.path_from_value(formatted) if hasattr(cfg, "path_from_value") else Path(formatted).expanduser()
    if resolved is None:
        return ""
    matches = sorted(glob.glob(str(resolved)))
    if matches:
        return matches[0]
    return str(resolved) if resolved.exists() else ""


def _resolve_output_root(output_root: str | Path | None, config: Any | None) -> Path:
    """Resolve the preprocessing output folder from an argument or config."""

    if output_root is not None:
        return Path(output_root).expanduser()
    cfg = config
    if cfg is None:
        try:
            from spatial_vtk.config import SpatialVTKConfig

            cfg = SpatialVTKConfig.active()
        except Exception:
            cfg = None
    if cfg is not None:
        value = cfg.section("outputs.preprocessed_waveforms")
        if value:
            return cfg.path_from_value(value)
        root_value = cfg.section("outputs.root")
        if root_value:
            return cfg.path_from_value(root_value) / "preprocessed_waveforms"
    return Path("outputs") / "preprocessed_waveforms"


def _preprocess_one_file(
    input_path: Path,
    output_path: Path,
    *,
    source: str,
    event_id: str,
    settings: WaveformPreprocessing,
    overwrite: bool,
    cached_metadata: pd.DataFrame | None = None,
) -> tuple[dict[str, Any], pd.DataFrame | None]:
    """Preprocess one waveform file and return manifest metadata."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    label = waveform_preprocessing_label(settings)
    if output_path.exists() and not overwrite:
        if cached_metadata is not None and not cached_metadata.empty:
            metadata = cached_metadata.copy()
            return _manifest_row(input_path, output_path, source, event_id, settings, label, "cached", "", metadata), metadata
        message = (
            "Processed waveform exists; trace metadata was not available. "
            "Skipping waveform read for fast resume. Rerun with overwrite=True "
            "to regenerate trace metadata."
        )
        return _manifest_row(
            input_path,
            output_path,
            source,
            event_id,
            settings,
            label,
            "cached_missing_metadata",
            message,
            pd.DataFrame(),
        ), None
    try:
        stream = read_waveform_file(input_path)
        processed = preprocess_stream(stream, settings)
        _write_waveform_file(processed, output_path, input_path=input_path)
        metadata = trace_metadata_table(processed, source=output_path, event_id=event_id)
        metadata = _tag_trace_metadata(metadata, source=source, input_path=input_path, output_path=output_path)
        return _manifest_row(input_path, output_path, source, event_id, settings, label, "written", "", metadata), metadata
    except Exception as exc:
        row = _manifest_row(input_path, output_path, source, event_id, settings, label, "error", str(exc), pd.DataFrame())
        return row, None


def _write_waveform_file(stream: Any, output_path: Path, *, input_path: Path) -> None:
    """Write a processed waveform file using ObsPy when possible."""

    suffix = output_path.suffix.lower()
    if hasattr(stream, "write") and suffix in {".mseed", ".msd", ".sac"}:
        fmt = "MSEED" if suffix in {".mseed", ".msd"} else "SAC"
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"The encoding specified in trace\.stats\.mseed\.encoding does not match the dtype of the data\..*",
                category=UserWarning,
            )
            stream.write(str(output_path), format=fmt)
        return
    with output_path.open("wb") as handle:
        pickle.dump(stream, handle)


def _index_cached_trace_metadata(trace_metadata_path: Path) -> dict[str, pd.DataFrame]:
    """Load prior trace metadata by processed output file path."""

    if not trace_metadata_path.exists():
        return {}
    try:
        metadata = read_table(trace_metadata_path)
    except Exception:
        return {}
    if metadata.empty or "output_file" not in metadata.columns:
        return {}
    out: dict[str, pd.DataFrame] = {}
    for output_file, group in metadata.groupby("output_file", dropna=True, sort=False):
        for key in _path_cache_keys(output_file):
            out.setdefault(key, group.copy())
    return out


def _cached_trace_metadata_for_output(cache: Mapping[str, pd.DataFrame], output_path: Path) -> pd.DataFrame | None:
    """Return cached trace metadata for one processed output path."""

    for key in _path_cache_keys(output_path):
        metadata = cache.get(key)
        if metadata is not None:
            return metadata.copy()
    return None


def _path_cache_keys(value: object) -> tuple[str, ...]:
    """Return stable path keys without forcing filesystem resolution."""

    text = str(value).strip()
    if not text:
        return ()
    expanded = str(Path(text).expanduser())
    keys = [text]
    if expanded not in keys:
        keys.append(expanded)
    return tuple(keys)


def _tag_trace_metadata(metadata: pd.DataFrame, *, source: str, input_path: Path, output_path: Path) -> pd.DataFrame:
    """Add source and file provenance columns to processed trace metadata."""

    out = metadata.copy()
    if out.empty:
        return out
    out["source_type"] = str(source).strip().lower()
    out["input_file"] = str(input_path)
    out["output_file"] = str(output_path)
    return out


def _processed_output_path(root: Path, source: str, event_id: str, input_path: Path) -> Path:
    """Build the processed waveform path for one input file."""

    suffix = input_path.suffix if input_path.suffix.lower() in {".mseed", ".msd", ".sac", ".pkl", ".pickle"} else ".pkl"
    name = input_path.name if input_path.suffix.lower() in {".mseed", ".msd", ".sac", ".pkl", ".pickle"} else f"{input_path.stem}.pkl"
    if suffix in {".pkl", ".pickle"} and input_path.suffix.lower() not in {".pkl", ".pickle"}:
        name = f"{input_path.stem}.pkl"
    return root / str(source).strip().lower() / _safe_token(event_id) / name


def _manifest_row(
    input_path: Path,
    output_path: Path,
    source: str,
    event_id: str,
    settings: WaveformPreprocessing,
    label: str,
    status: str,
    message: str,
    metadata: pd.DataFrame,
) -> dict[str, Any]:
    """Build one preprocessing manifest row."""

    return {
        "event_id": event_id,
        "source": source,
        "input_file": str(input_path),
        "output_file": str(output_path),
        "status": status,
        "message": message,
        "processing": label,
        "lowpass_hz": settings.lowpass_hz,
        "highpass_hz": settings.highpass_hz,
        "bandpass_low_hz": settings.bandpass_low_hz,
        "bandpass_high_hz": settings.bandpass_high_hz,
        "resample_hz": settings.resample_hz,
        "filter_order": settings.filter_order,
        "trace_count": int(len(metadata)) if metadata is not None else 0,
    }


def _safe_token(value: Any) -> str:
    """Return a filesystem-safe token for event/source labels."""

    text = str(value or "unknown").strip()
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in text) or "unknown"


__all__ = [
    "DEFAULT_SOURCE_COLUMN_CANDIDATES",
    "WaveformPreprocessingWorkflowResult",
    "preprocess_waveform_files",
]
