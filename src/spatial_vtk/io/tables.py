"""Generic table loading and reshaping helpers."""

from __future__ import annotations

import csv
import glob
from collections.abc import Callable, Sequence
from pathlib import Path
import tempfile
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd

from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.config.outputs import output_description
from spatial_vtk.config.runtime import SpatialVTKConfig, active_config

ConfigInput = SpatialVTKConfig | str | Path


RENAME_MAP = {
    "simulation_model": "model",
    "simulation_band": "band",
    "simulation_freq_min": "freq_min",
    "simulation_freq_max": "freq_max",
    "event_title": "event_id",
    "event_latitude": "event_lat",
    "event_longitude": "event_lon",
    "event_depth_km": "event_depth_km",
    "event_magnitude": "Mw",
    "station_name": "station",
    "station_latitude": "sta_lat",
    "station_longitude": "sta_lon",
    "station_component": "component",
    "station_Vs30": "Vs30",
    "station_geology": "geologic_description",
    "SourceFile": "source_file",
}

CONTEXT_COLS = [
    "model",
    "band",
    "freq_min",
    "freq_max",
    "event_id",
    "event_lat",
    "event_lon",
    "event_depth_km",
    "Mw",
    "station",
    "sta_lat",
    "sta_lon",
    "component",
    "Vs30",
    "geologic_description",
    "source_file",
]


def load_csv_bundle(
    sources: str | Path | Sequence[str | Path] | dict[str, Any],
    *,
    base_dir: str | Path | None = None,
    source_column: str = "__source_csv__",
) -> pd.DataFrame:
    """Load one or more CSV files into a single table.

    Parameters
    ----------
    sources
        CSV path, glob pattern, sequence of paths, or config dictionary with one
        of ``input_csv``, ``csv_dir``, or ``csv_files``.
    base_dir
        Directory used to resolve relative paths.
    source_column
        Name of the column recording the source CSV path.

    Returns
    -------
    pandas.DataFrame
        Concatenated CSV table.
    """

    paths = _resolve_csv_sources(sources, Path(base_dir or "."))
    frames: list[pd.DataFrame] = []
    for path in paths:
        df = pd.read_csv(path, low_memory=False)
        if source_column:
            df[source_column] = str(path)
        frames.append(df)
    if not frames:
        raise ValueError("No CSV files were loaded.")
    return pd.concat(frames, ignore_index=True)


def read_bounded_table(path: str | Path, max_rows: int) -> pd.DataFrame:
    """Read at most ``max_rows`` from a CSV or Parquet table.

    This is intended for notebook previews and lightweight plotting cells that
    need representative rows from a large output table without loading the full
    table into memory. Parquet files are streamed by row batch when PyArrow is
    available.

    Parameters
    ----------
    path
        CSV or Parquet table path.
    max_rows
        Maximum number of rows to return. Values less than one return an empty
        dataframe.

    Returns
    -------
    pandas.DataFrame
        Bounded table prefix.
    """

    input_path = Path(path).expanduser()
    limit = int(max_rows)
    if limit < 1:
        return pd.DataFrame()
    suffix = input_path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return _read_parquet_prefix(input_path, max_rows=limit)
    return pd.read_csv(input_path, nrows=limit, low_memory=False)


def _read_parquet_prefix(
    path: Path,
    *,
    max_rows: int,
    columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Read a bounded prefix from a Parquet table without full materialization."""

    try:
        import pyarrow.parquet as pq
    except Exception as exc:
        raise RuntimeError(
            f"Could not read bounded parquet preview for {path}: pyarrow is required. "
            "Install the package dependencies or write the table as CSV before previewing it."
        ) from exc
    try:
        parquet_file = pq.ParquetFile(path)
    except Exception as exc:
        raise RuntimeError(
            f"Could not inspect parquet metadata for bounded preview {path}. "
            "Repair or rewrite the table before using notebook preview helpers."
        ) from exc
    selected_columns = None if columns is None else list(dict.fromkeys(str(column) for column in columns))
    frames: list[pd.DataFrame] = []
    remaining = max(0, int(max_rows))
    try:
        for batch in parquet_file.iter_batches(batch_size=min(max(remaining, 1), 100_000), columns=selected_columns):
            frame = batch.to_pandas()
            bounded = frame.head(remaining)
            if not bounded.empty:
                frames.append(bounded)
            remaining -= len(bounded)
            if remaining <= 0:
                break
    except Exception as exc:
        raise RuntimeError(
            f"Could not stream bounded parquet preview rows from {path}. "
            "Repair or rewrite the table before using notebook preview helpers."
        ) from exc
    if frames:
        return pd.concat(frames, ignore_index=True)
    output_columns = selected_columns if selected_columns is not None else list(parquet_file.schema.names)
    return pd.DataFrame(columns=output_columns)


def parquet_table_columns(path: str | Path) -> list[str]:
    """Return parquet column names without reading row data."""

    input_path = Path(path).expanduser()
    try:
        import pyarrow.parquet as pq
    except Exception as exc:
        raise RuntimeError(
            f"Could not inspect parquet columns for {input_path}: pyarrow is required. "
            "Install the package dependencies or write the table as CSV before using this workflow."
        ) from exc
    try:
        return list(pq.ParquetFile(input_path).schema.names)
    except Exception as exc:
        raise RuntimeError(
            f"Could not inspect parquet metadata for {input_path}. "
            "Repair or rewrite the table before using this workflow."
        ) from exc


def table_columns(path: str | Path) -> list[str]:
    """Return CSV or Parquet column names without reading row data."""

    input_path = Path(path).expanduser()
    suffix = input_path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return parquet_table_columns(input_path)
    if suffix in {"", ".csv"}:
        return list(pd.read_csv(input_path, nrows=0, low_memory=False).columns)
    raise ValueError(f"Unsupported table format for {input_path}. Use Parquet or CSV.")


def parquet_table_row_count(path: str | Path) -> int:
    """Return a parquet row count without materializing table columns."""

    input_path = Path(path).expanduser()
    try:
        import pyarrow.parquet as pq
    except Exception as exc:
        raise RuntimeError(
            f"Could not inspect parquet row count for {input_path}: pyarrow is required. "
            "Install the package dependencies or write the table as CSV before using this workflow."
        ) from exc
    try:
        metadata = pq.ParquetFile(input_path).metadata
    except Exception as exc:
        raise RuntimeError(
            f"Could not inspect parquet metadata for {input_path}. "
            "Repair or rewrite the table before using this workflow."
        ) from exc
    return int(metadata.num_rows)


def table_row_count(path: str | Path) -> int:
    """Return a CSV or Parquet row count without materializing the table.

    Parquet counts are read from file metadata. CSV counts are streamed with
    Python's CSV parser so quoted newlines are handled without loading rows
    into memory. Empty CSV files return zero rows.
    """

    input_path = Path(path).expanduser()
    suffix = input_path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return parquet_table_row_count(input_path)
    try:
        with input_path.open("r", newline="", encoding="utf-8") as handle:
            rows = sum(1 for _ in csv.reader(handle))
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            f"Could not count CSV rows for {input_path}: the file is not valid UTF-8. "
            "Rewrite the table with UTF-8 encoding or use Parquet for large-run status checks."
        ) from exc
    return max(int(rows) - 1, 0)


def first_nonempty_table_value(
    table: pd.DataFrame | None,
    column: str,
    *,
    fallback: str | None = None,
) -> str | None:
    """Return the first non-empty value from a table column.

    This is intended for notebook titles, labels, and compact summaries where a
    missing optional column should use a stable fallback instead of relying on a
    brittle ``.iloc[0]`` lookup.

    Parameters
    ----------
    table
        Source dataframe.
    column
        Column to scan.
    fallback
        Value returned when the table is missing, the column is absent, or all
        values are empty/null.

    Returns
    -------
    str or None
        First non-empty string value, or ``fallback``.
    """

    if table is None or column not in table.columns:
        return fallback
    for value in table[column].dropna():
        text = str(value).strip()
        if text:
            return text
    return fallback


def normalize_metric_table(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize common legacy metric-table column names.

    Parameters
    ----------
    df
        Metric table with either public or legacy column names.

    Returns
    -------
    pandas.DataFrame
        Copy of the table with public column names where possible.
    """

    out = df.rename(columns=RENAME_MAP).copy()
    out = _coalesce_duplicate_columns(out)
    for column in CONTEXT_COLS:
        if column not in out.columns:
            out[column] = np.nan
    return out


def wide_to_long_metrics(
    df: pd.DataFrame,
    residual_mode: str = "logratio",
    *,
    context_cols: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Convert wide ``*_obs``/``*_syn`` metric columns into tidy long form.

    Parameters
    ----------
    df
        Metric table with observed and synthetic metric columns.
    residual_mode
        ``"logratio"`` for ``log10(synthetic / observed)`` or ``"diff"`` for
        ``synthetic - observed``.
    context_cols
        Metadata columns to preserve in each long-form row.

    Returns
    -------
    pandas.DataFrame
        Long-form metric table with ``metric``, ``value_obs``, ``value_syn``,
        ``residual``, and optional ``score`` columns.
    """

    if residual_mode not in {"logratio", "diff"}:
        raise ValueError("residual_mode must be 'logratio' or 'diff'.")
    work = normalize_metric_table(df)
    contexts = [col for col in (context_cols or CONTEXT_COLS) if col in work.columns]
    bases = sorted(
        column[:-4]
        for column in work.columns
        if column.endswith("_obs") and f"{column[:-4]}_syn" in work.columns
    )
    if not bases:
        raise ValueError("No metric pairs with *_obs and *_syn columns were found.")

    long_frames: list[pd.DataFrame] = []
    for base in bases:
        obs = pd.to_numeric(work[f"{base}_obs"], errors="coerce")
        syn = pd.to_numeric(work[f"{base}_syn"], errors="coerce")
        if residual_mode == "logratio":
            with np.errstate(divide="ignore", invalid="ignore"):
                residual = np.log10(syn / obs)
        else:
            residual = syn - obs
        part = work[contexts].copy()
        part["metric"] = base
        part["value_obs"] = obs
        part["value_syn"] = syn
        part["residual"] = residual
        part["score"] = work[f"{base}_score"] if f"{base}_score" in work.columns else np.nan
        long_frames.append(part)
    return pd.concat(long_frames, ignore_index=True)


def aggregate_metric_by_station_over_events(
    df: pd.DataFrame,
    *,
    metric_col: str,
    model_col: str = "model",
    station_col: str = "station",
    latitude_col: str = "sta_lat",
    longitude_col: str = "sta_lon",
    event_col: str = "event_id",
) -> pd.DataFrame:
    """Average a metric by station after first averaging within each event.

    Parameters
    ----------
    df
        Metric table.
    metric_col
        Numeric column to aggregate.
    model_col, station_col, latitude_col, longitude_col, event_col
        Column names defining model, station, coordinates, and event.

    Returns
    -------
    pandas.DataFrame
        Station-level metric table with ``n_events`` when event information is
        available.
    """

    work = normalize_metric_table(df)
    required = [metric_col, model_col, station_col, latitude_col, longitude_col]
    missing = [column for column in required if column not in work.columns]
    if missing:
        raise ValueError(f"Missing required columns for station aggregation: {missing}")

    columns = required + ([event_col] if event_col in work.columns else [])
    work = work[columns].copy()
    work[metric_col] = pd.to_numeric(work[metric_col], errors="coerce")
    work = work.dropna(subset=[metric_col, latitude_col, longitude_col])
    if work.empty:
        return pd.DataFrame(columns=[model_col, station_col, latitude_col, longitude_col, metric_col])

    group_cols = [model_col, station_col, latitude_col, longitude_col]
    if event_col in work.columns:
        event_level = (
            work.groupby(group_cols + [event_col], dropna=False)[metric_col]
            .mean()
            .reset_index(name="event_metric_mean")
        )
        station_level = (
            event_level.groupby(group_cols, dropna=False)["event_metric_mean"]
            .mean()
            .reset_index(name=metric_col)
        )
        event_counts = (
            event_level.groupby(group_cols, dropna=False)[event_col]
            .nunique()
            .reset_index(name="n_events")
        )
        return station_level.merge(event_counts, on=group_cols, how="left")
    return work.groupby(group_cols, dropna=False)[metric_col].mean().reset_index()


def write_table(df: pd.DataFrame, path: str | Path, *, index: bool = False) -> Path:
    """Write one table based on the destination file extension.

    Parameters
    ----------
    df
        Table to write.
    path
        Output path ending in ``.csv`` or ``.parquet``. Paths without an
        extension are written as CSV.
    index
        Whether to include the dataframe index.

    Returns
    -------
    pathlib.Path
        Written path.
    """

    output_path = Path(path).expanduser()
    suffix = output_path.suffix.lower()
    if suffix in {"", ".csv"}:
        if not suffix:
            output_path = output_path.with_suffix(".csv")
        _atomic_write_table(df, output_path, index=index, format="csv")
    elif suffix in {".parquet", ".pq"}:
        _atomic_write_table(df, output_path, index=index, format="parquet")
    else:
        raise ValueError(f"Unsupported table output extension: {output_path.suffix}")
    return output_path


def _atomic_write_table(df: pd.DataFrame, output_path: Path, *, index: bool, format: str) -> None:
    """Write one table through a same-directory temporary file."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        delete=False,
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
    )
    tmp_path = Path(handle.name)
    handle.close()
    try:
        if format == "csv":
            df.to_csv(tmp_path, index=index)
        elif format == "parquet":
            df.to_parquet(tmp_path, index=index)
        else:
            raise ValueError(f"Unsupported table output format: {format}")
        tmp_path.replace(output_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def read_table(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Read one CSV or Parquet table from disk.

    Parameters
    ----------
    path
        Input table path ending in ``.csv``, ``.parquet``, or ``.pq``.
    **kwargs
        Additional keyword arguments forwarded to ``pandas.read_csv`` for CSV
        files or ``pandas.read_parquet`` for Parquet files.

    Returns
    -------
    pandas.DataFrame
        Loaded table.
    """

    input_path = Path(path).expanduser()
    suffix = input_path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(input_path, **kwargs)
    csv_kwargs = {"low_memory": False, **kwargs}
    return pd.read_csv(input_path, **csv_kwargs)


def load_output_table(
    key: str,
    *,
    cfg: ConfigInput | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Load a standard output table by artifact key.

    Parameters
    ----------
    key
        Registered output key such as ``"prepared_stations"``.
    cfg
        Optional config object or config file path. When omitted, the
        active/discoverable config is used.
    **kwargs
        Additional read options forwarded to ``read_table``.

    Returns
    -------
    pandas.DataFrame
        Loaded table.
    """

    path = resolve_output_path(key, kind="table", cfg=cfg)
    return read_table(path, **kwargs)


def preview_table(
    path: str | Path,
    *,
    nrows: int = 5,
    columns: Sequence[str] | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Load only the first rows of a table for notebook previews.

    This avoids loading large workflow outputs such as ``qc_inventory.csv`` just
    to inspect their schema or first few rows.
    """

    input_path = Path(path).expanduser()
    row_count = max(int(nrows), 0)
    suffix = input_path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        if kwargs:
            extra = ", ".join(sorted(str(key) for key in kwargs))
            raise ValueError(
                "Parquet preview_table uses bounded PyArrow streaming and does not accept "
                f"extra pandas read_parquet options: {extra}."
            )
        return _read_parquet_prefix(input_path, max_rows=row_count, columns=columns)
    csv_kwargs = {"low_memory": False, **kwargs}
    csv_kwargs["nrows"] = row_count
    if columns is not None:
        requested = set(columns)
        csv_kwargs["usecols"] = lambda column: column in requested
    return pd.read_csv(input_path, **csv_kwargs)


def preview_output_table(
    key: str,
    *,
    cfg: ConfigInput | None = None,
    nrows: int = 5,
    columns: Sequence[str] | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Preview a standard output table without loading the full file."""

    path = resolve_output_path(key, kind="table", cfg=cfg)
    return preview_table(path, nrows=nrows, columns=columns, **kwargs)


def load_or_build_output_table(
    key: str,
    builder: Callable[[], pd.DataFrame],
    *,
    source_path: str | Path | Sequence[str | Path] | None = None,
    cfg: ConfigInput | None = None,
    overwrite: bool = False,
    verbose: bool = True,
    index: bool = False,
) -> pd.DataFrame:
    """Load a registered output table or rebuild it when stale.

    This helper is intended for compact derived tables used by notebooks and
    dashboards. It keeps workflow cells focused on the table being produced
    while centralizing the common "reuse unless source changed" behavior.

    Parameters
    ----------
    key
        Registered table output key.
    builder
        Zero-argument callable that returns the table when it needs to be
        created or refreshed.
    source_path
        Optional source file path or paths. If any existing source is newer
        than the output, the table is rebuilt.
    cfg
        Optional config object or config file path. When omitted, the
        active/discoverable config is used.
    overwrite
        Force a rebuild even if the existing table is current.
    verbose
        Print reuse/rebuild messages.
    index
        Whether to include dataframe indexes when writing the rebuilt table.

    Returns
    -------
    pandas.DataFrame
        Existing or rebuilt output table.
    """

    output_path = resolve_output_path(key, kind="table", cfg=cfg, create_parent=True)
    sources = _table_source_paths(source_path)
    output_exists = output_path.exists()
    stale_sources = [
        path
        for path in sources
        if path.exists() and output_exists and path.stat().st_mtime > output_path.stat().st_mtime
    ]

    if output_exists and not overwrite and not stale_sources:
        if verbose:
            print(f"Reusing {key}: {output_path}")
        return load_output_table(key, cfg=cfg)

    if verbose and output_exists and stale_sources:
        changed = ", ".join(str(path) for path in stale_sources[:3])
        suffix = "" if len(stale_sources) <= 3 else f", +{len(stale_sources) - 3} more"
        print(f"Rebuilding {key}: source is newer than {output_path} ({changed}{suffix})")
    elif verbose and overwrite:
        print(f"Rebuilding {key}: overwrite=True")
    elif verbose:
        print(f"Building {key}: {output_path}")

    table = builder()
    written = write_output_table(key, table, cfg=cfg, index=index)
    if verbose:
        print(f"Wrote {key}: {written}")
    return table


def read_config_table(
    dotted_key: str,
    *,
    cfg: ConfigInput | None = None,
    must_exist: bool = True,
    **kwargs: Any,
) -> pd.DataFrame:
    """Read a table path from the active config.

    Parameters
    ----------
    dotted_key
        Config key that points to a table, such as ``"paths.station_metadata"``.
    cfg
        Optional config object or config file path. When omitted, the
        active/discoverable config is used.
    must_exist
        Whether to raise an error if the configured path is missing.
    **kwargs
        Additional read options forwarded to ``read_table``.

    Returns
    -------
    pandas.DataFrame
        Loaded table.
    """

    config = _coerce_table_config(cfg)
    path = config.path(dotted_key, must_exist=must_exist)
    if path is None:
        raise ValueError(f"No path is configured for {dotted_key!r}.")
    table = read_table(path, **kwargs)
    if dotted_key == "paths.station_metadata":
        from spatial_vtk.io.metadata import prepare_station_metadata

        return prepare_station_metadata(table, required_columns=("station",))
    if dotted_key == "paths.event_metadata":
        from spatial_vtk.io.metadata import prepare_event_metadata

        return prepare_event_metadata(table, required_columns=("event_id",))
    return table


def write_output_table(
    key: str,
    df: pd.DataFrame,
    *,
    outpath: str | Path | None = None,
    cfg: ConfigInput | None = None,
    index: bool = False,
) -> Path:
    """Write a standard table using the output registry and config.

    Parameters
    ----------
    key
        Registered table key such as ``"prepared_stations"``.
    df
        Table to write.
    outpath
        Optional explicit output path. This always wins.
    cfg
        Optional config object or config file path. When omitted, the
        active/discoverable config is used.
    index
        Whether to include the dataframe index.

    Returns
    -------
    pathlib.Path
        Written table path.
    """

    path = resolve_output_path(key, kind="table", outpath=outpath, cfg=cfg, create_parent=True)
    return write_table(df, path, index=index)


def write_output_tables(
    tables: dict[str, pd.DataFrame] | None = None,
    *,
    cfg: ConfigInput | None = None,
    index: bool = False,
    **named_tables: pd.DataFrame,
) -> dict[str, Path]:
    """Write one or more standard output tables by artifact key.

    Parameters
    ----------
    tables
        Optional mapping from registered output keys to dataframes.
    cfg
        Optional config object or config file path. When omitted, the
        active/discoverable config is used.
    index
        Whether to include dataframe indexes.
    **named_tables
        Additional registered output keys passed as keyword arguments.

    Returns
    -------
    dict[str, pathlib.Path]
        Written table paths keyed by artifact name.
    """

    combined: dict[str, pd.DataFrame] = {}
    if tables:
        combined.update(tables)
    combined.update(named_tables)
    return {key: write_output_table(key, table, cfg=cfg, index=index) for key, table in combined.items()}


def _coerce_table_config(cfg: ConfigInput | None) -> SpatialVTKConfig:
    """Return a config object for table path resolution."""

    if cfg is None:
        return active_config()
    if isinstance(cfg, SpatialVTKConfig):
        return cfg
    return SpatialVTKConfig.from_file(cfg)


def write_named_tables(
    tables: dict[str, pd.DataFrame],
    paths: SimpleNamespace | dict[str, str | Path],
    *,
    index: bool = False,
) -> dict[str, Path]:
    """Write a set of named tables to matching named paths.

    Parameters
    ----------
    tables
        Mapping from logical table name to dataframe.
    paths
        Namespace or mapping with one path per table name.
    index
        Whether to include dataframe indexes.

    Returns
    -------
    dict[str, pathlib.Path]
        Written paths keyed by table name.
    """

    written: dict[str, Path] = {}
    for name, table in tables.items():
        path = paths[name] if isinstance(paths, dict) else getattr(paths, name)
        written[name] = write_table(table, path, index=index)
    return written


def written_files_table(
    written: dict[str, str | Path],
    *,
    descriptions: dict[str, str] | None = None,
    relative_to: str | Path | None = None,
) -> pd.DataFrame:
    """Build a readable table of written files.

    Parameters
    ----------
    written
        Mapping from logical output name to written file path.
    descriptions
        Optional mapping from logical output name to display description.
    relative_to
        Optional root used to display relative paths.

    Returns
    -------
    pandas.DataFrame
        Two-column manifest with ``File`` and ``Description``.
    """

    root = Path(relative_to).expanduser().resolve() if relative_to is not None else None
    rows: list[dict[str, str]] = []
    for name, raw_path in written.items():
        path = Path(raw_path)
        display_path = path
        if root is not None:
            try:
                display_path = path.resolve().relative_to(root)
            except ValueError:
                display_path = path
        description = (descriptions or {}).get(name) or output_description(name) or _title_from_name(name)
        rows.append({"File": str(display_path), "Description": description})
    return pd.DataFrame(rows, columns=["File", "Description"])


def _table_source_paths(source_path: str | Path | Sequence[str | Path] | None) -> list[Path]:
    """Normalize optional table source paths."""

    if source_path is None:
        return []
    if isinstance(source_path, (str, Path)):
        return [Path(source_path).expanduser()]
    return [Path(path).expanduser() for path in source_path]


def _resolve_csv_sources(
    sources: str | Path | Sequence[str | Path] | dict[str, Any],
    base_dir: Path,
) -> list[Path]:
    """Resolve CSV input sources into existing paths."""

    if isinstance(sources, dict):
        input_csv = sources.get("input_csv")
        csv_dir = sources.get("csv_dir")
        csv_files = sources.get("csv_files")
        selected = sum(value is not None for value in (input_csv, csv_dir, csv_files))
        if selected != 1:
            raise ValueError("Set exactly one of input_csv, csv_dir, or csv_files.")
        if input_csv is not None:
            raw_sources: Sequence[str | Path] = [input_csv]
        elif csv_dir is not None:
            directory = _resolve_path(csv_dir, base_dir)
            pattern = str(sources.get("csv_glob", "*.csv"))
            raw_sources = sorted(directory.glob(pattern))
        else:
            raw_sources = csv_files if isinstance(csv_files, Sequence) and not isinstance(csv_files, str) else [csv_files]
    elif isinstance(sources, Sequence) and not isinstance(sources, (str, bytes, Path)):
        raw_sources = sources
    else:
        raw = str(sources)
        if any(char in raw for char in "*?[]"):
            raw_sources = sorted(Path(path) for path in glob.glob(raw))
        else:
            raw_sources = [sources]

    paths = [_resolve_path(path, base_dir) for path in raw_sources]
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"CSV file does not exist: {missing[0]}")
    return sorted(paths)


def _resolve_path(path: str | Path, base_dir: Path) -> Path:
    """Resolve a path against a base directory."""

    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    return (base_dir / candidate).resolve()


def _coalesce_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse duplicate column labels by first non-null value."""

    if df.columns.is_unique:
        return df
    output_columns: dict[str, pd.Series] = {}
    for column in dict.fromkeys(df.columns):
        selected = df.loc[:, df.columns == column]
        merged = selected.iloc[:, 0].copy()
        for idx in range(1, selected.shape[1]):
            merged = merged.combine_first(selected.iloc[:, idx])
        output_columns[column] = merged
    return pd.DataFrame(output_columns, index=df.index)


def _title_from_name(name: str) -> str:
    """Convert an output key into a readable title."""

    return str(name).replace("_", " ").strip().capitalize()
