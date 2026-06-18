"""Dashboard dataset export helpers.

Purpose
-------
This module converts wide or long metric tables into dashboard-ready Parquet
datasets and reloads those datasets for summary generation.

Usage examples
--------------
Write one dashboard dataset:
  ``path = write_dashboard_metric_dataset(metrics_df, "dashboard_data")``
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from spatial_vtk.config.labels import normalize_metric_name
from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.config.runtime import SpatialVTKConfig
from spatial_vtk.visualize.dashboard.tables import (
    build_dashboard_summaries,
    dashboard_summary_input_columns,
    prepare_dashboard_metric_table,
    write_dashboard_summaries,
)


def write_dashboard_metric_dataset(
    tables: pd.DataFrame | str | Path | Sequence[pd.DataFrame | str | Path],
    output_root: str | Path | None = None,
    *,
    residual_mode: str = "logratio",
    partitioned: bool = False,
    replace_existing: bool = True,
) -> Path:
    """Write dashboard-ready long metric data as Parquet.

    Parameters
    ----------
    tables
        One table, path, or sequence of tables/paths.
    output_root
        Output directory for ``metrics_long.parquet`` or partitioned files.
        When omitted, the standard ``metrics_dashboard`` path is resolved from
        the active config.
    residual_mode
        Residual mode used when converting wide tables.
    partitioned
        Whether to partition by ``model``, ``band``, and ``metric``.
    replace_existing
        Remove previously written dashboard metric files under ``output_root``
        before writing new files. Only recognized dashboard files are removed,
        so unrelated files in the output directory are preserved.

    Returns
    -------
    pathlib.Path
        Dataset root directory.
    """

    frames = [_read_metric_table(item) for item in _as_sequence(tables)]
    if not frames:
        raise ValueError("At least one metric table is required.")
    long_frames = [prepare_dashboard_metric_table(frame, residual_mode=residual_mode) for frame in frames]
    long_df = pd.concat(long_frames, ignore_index=True)
    long_df = add_dashboard_path_geometry(long_df)
    root = Path(output_root).expanduser() if output_root is not None else resolve_output_path("metrics_dashboard", kind="dashboard", create_parent=True)
    root.mkdir(parents=True, exist_ok=True)
    if replace_existing:
        _clear_dashboard_metric_dataset(root)
    if not partitioned:
        long_df.to_parquet(root / "metrics_long.parquet", index=False)
        return root
    required = ["model", "band", "metric"]
    for column in required:
        if column not in long_df.columns:
            long_df[column] = "unknown"
    for keys, group in long_df.groupby(required, dropna=False):
        model, band, metric = [safe_path_token(value) for value in keys]
        out_path = root / f"model={model}" / f"band={band}" / f"metric={metric}" / "part.parquet"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        group.to_parquet(out_path, index=False)
    return root


def load_dashboard_metric_dataset(
    input_root: str | Path,
    *,
    columns: Sequence[str] | None = None,
    models: Sequence[str] | str | None = None,
    bands: Sequence[str] | str | None = None,
    metrics: Sequence[str] | str | None = None,
    periods_s: Sequence[float | str] | float | str | None = None,
    component: str | None = None,
    distance_range_km: tuple[float | None, float | None] | None = None,
    vs30_range: tuple[float | None, float | None] | None = None,
    preserve_unbanded_bands: bool = True,
    max_rows: int | None = None,
    chunksize: int = 50_000,
) -> pd.DataFrame:
    """Load dashboard metric rows from a dataset directory or table file.

    Parameters
    ----------
    input_root
        Directory containing ``metrics_long.parquet`` or partitioned parquet
        files, or a direct ``.parquet``/``.csv`` long metric table path.
    columns
        Optional column subset to load. Missing requested columns are ignored
        so dashboard previews can run against older metric datasets.
    models, bands, metrics
        Optional row filters. Partitioned dashboard datasets prune matching
        ``model=*/band=*/metric=*/part.parquet`` files before reading and then
        apply the same filters after loading. Single-file datasets apply the
        filters after loading.
    periods_s, component, distance_range_km, vs30_range
        Additional row filters applied while reading bounded datasets, before
        ``max_rows`` is enforced. This keeps dashboard distribution tabs from
        filling their row cap with rows outside the current component,
        oscillator-period, distance, or site-condition selection.
    preserve_unbanded_bands
        Preserve blank/broadband rows when a passband filter is supplied.
        Spectral metrics such as PSA and FAS are broadband rows, so this keeps
        row-level dashboard loading consistent with summary-table filtering.
    max_rows
        Optional maximum rows to return after filtering. When provided, files
        are read in bounded chunks where possible so dashboards can show
        row-level distributions without materializing a full large-run metric
        dataset.
    chunksize
        Row batch size used when ``max_rows`` is provided.

    Returns
    -------
    pandas.DataFrame
        Combined long metric table.
    """

    root = Path(input_root).expanduser()
    filter_columns = _dashboard_metric_filter_columns(
        models=models,
        bands=bands,
        metrics=metrics,
        periods_s=periods_s,
        component=component,
        distance_range_km=distance_range_km,
        vs30_range=vs30_range,
    )
    read_columns = _merged_columns(columns, filter_columns)
    row_limit = _normalize_max_rows(max_rows)
    if row_limit == 0:
        return pd.DataFrame(columns=list(columns or ()))
    if root.is_file():
        if row_limit is not None:
            return _load_dashboard_metric_dataset_bounded(
                [root],
                columns=read_columns,
                models=models,
                bands=bands,
                metrics=metrics,
                periods_s=periods_s,
                component=component,
                distance_range_km=distance_range_km,
                vs30_range=vs30_range,
                preserve_unbanded_bands=preserve_unbanded_bands,
                output_columns=columns,
                max_rows=row_limit,
                chunksize=chunksize,
            )
        return _filter_dashboard_metric_rows(
            _read_dashboard_metric_table(root, columns=read_columns),
            models=models,
            bands=bands,
            metrics=metrics,
            periods_s=periods_s,
            component=component,
            distance_range_km=distance_range_km,
            vs30_range=vs30_range,
            preserve_unbanded_bands=preserve_unbanded_bands,
            output_columns=columns,
        )
    if not root.exists():
        raise FileNotFoundError(f"Dashboard metric dataset path does not exist: {root}")
    paths = _dashboard_metric_parquet_paths(root)
    if not paths:
        raise FileNotFoundError(
            f"No dashboard metric parquet files found under {root}. "
            "Expected metrics_long.parquet or model=*/band=*/metric=*/part.parquet."
        )
    paths = _filter_dashboard_metric_paths(
        paths,
        models=models,
        bands=bands,
        metrics=metrics,
        preserve_unbanded_bands=preserve_unbanded_bands,
    )
    if not paths:
        return pd.DataFrame(columns=list(columns or ()))
    if row_limit is not None:
        return _load_dashboard_metric_dataset_bounded(
            paths,
            columns=read_columns,
            models=models,
            bands=bands,
            metrics=metrics,
            periods_s=periods_s,
            component=component,
            distance_range_km=distance_range_km,
            vs30_range=vs30_range,
            preserve_unbanded_bands=preserve_unbanded_bands,
            output_columns=columns,
            max_rows=row_limit,
            chunksize=chunksize,
        )
    loaded = pd.concat(
        [_read_dashboard_metric_table(path, columns=read_columns) for path in paths],
        ignore_index=True,
        sort=False,
    )
    return _filter_dashboard_metric_rows(
        loaded,
        models=models,
        bands=bands,
        metrics=metrics,
        periods_s=periods_s,
        component=component,
        distance_range_km=distance_range_km,
        vs30_range=vs30_range,
        preserve_unbanded_bands=preserve_unbanded_bands,
        output_columns=columns,
    )


def _load_dashboard_metric_dataset_bounded(
    paths: Sequence[Path],
    *,
    columns: Sequence[str] | None,
    models: Sequence[str] | str | None,
    bands: Sequence[str] | str | None,
    metrics: Sequence[str] | str | None,
    periods_s: Sequence[float | str] | float | str | None,
    component: str | None,
    distance_range_km: tuple[float | None, float | None] | None,
    vs30_range: tuple[float | None, float | None] | None,
    preserve_unbanded_bands: bool,
    output_columns: Sequence[str] | None,
    max_rows: int,
    chunksize: int,
) -> pd.DataFrame:
    """Load filtered dashboard metric rows up to ``max_rows``."""

    if max_rows <= 0:
        return pd.DataFrame(columns=list(output_columns or columns or ()))
    frames: list[pd.DataFrame] = []
    remaining = int(max_rows)
    for path in paths:
        for chunk in _iter_dashboard_metric_table_chunks(path, columns=columns, chunksize=chunksize):
            filtered = _filter_dashboard_metric_rows(
                chunk,
                models=models,
                bands=bands,
                metrics=metrics,
                periods_s=periods_s,
                component=component,
                distance_range_km=distance_range_km,
                vs30_range=vs30_range,
                preserve_unbanded_bands=preserve_unbanded_bands,
                output_columns=output_columns,
            )
            if filtered.empty:
                continue
            if len(filtered) > remaining:
                filtered = filtered.head(remaining)
            frames.append(filtered)
            remaining -= len(filtered)
            if remaining <= 0:
                break
        if remaining <= 0:
            break
    if not frames:
        return pd.DataFrame(columns=list(output_columns or columns or ()))
    return pd.concat(frames, ignore_index=True, sort=False)


def dashboard_metric_dataset_paths(input_root: str | Path) -> list[Path]:
    """Return recognized dashboard metric files without reading row data.

    Parameters
    ----------
    input_root
        Dashboard dataset directory or direct dashboard metric table path.

    Returns
    -------
    list[pathlib.Path]
        Existing direct or partitioned metric table files. The list is empty
        when the root is missing or contains no recognized dashboard files.
    """

    root = Path(input_root).expanduser()
    if root.is_file():
        return [root] if root.suffix.lower() in {".parquet", ".pq", ".csv"} else []
    if not root.exists():
        return []
    return _dashboard_metric_parquet_paths(root)


def _dashboard_metric_parquet_paths(root: Path) -> list[Path]:
    """Return recognized dashboard metric parquet files under ``root``."""

    direct = root / "metrics_long.parquet"
    if direct.exists():
        return [direct]
    return sorted(path for path in root.glob("model=*/band=*/metric=*/part.parquet") if path.is_file())


def _dashboard_metric_filter_columns(
    *,
    models: Sequence[str] | str | None = None,
    bands: Sequence[str] | str | None = None,
    metrics: Sequence[str] | str | None = None,
    periods_s: Sequence[float | str] | float | str | None = None,
    component: str | None = None,
    distance_range_km: tuple[float | None, float | None] | None = None,
    vs30_range: tuple[float | None, float | None] | None = None,
) -> tuple[str, ...]:
    """Return row columns needed to apply dashboard metric filters."""

    columns: list[str] = []
    if models:
        columns.append("model")
    if bands:
        columns.append("band")
    if metrics:
        columns.append("metric")
    if periods_s:
        columns.append("period_s")
    if component:
        columns.append("component")
    if distance_range_km is not None:
        columns.extend(["distance_km", "med_dist_km", "dist_km"])
    if vs30_range is not None:
        columns.extend(["Vs30", "vs30"])
    return tuple(dict.fromkeys(columns))


def _merged_columns(columns: Sequence[str] | None, extras: Sequence[str]) -> list[str] | None:
    """Return a stable column projection that includes filter columns."""

    if columns is None:
        return None
    return list(dict.fromkeys([*(str(column) for column in columns), *(str(column) for column in extras)]))


def _filter_dashboard_metric_paths(
    paths: Sequence[Path],
    *,
    models: Sequence[str] | str | None = None,
    bands: Sequence[str] | str | None = None,
    metrics: Sequence[str] | str | None = None,
    preserve_unbanded_bands: bool = True,
) -> list[Path]:
    """Prune partitioned dashboard metric paths using model/band/metric filters."""

    model_tokens = _filter_tokens(models)
    band_tokens = _filter_tokens(bands)
    metric_tokens = _metric_filter_tokens(metrics)
    if not model_tokens and not band_tokens and not metric_tokens:
        return list(paths)
    selected: list[Path] = []
    for path in paths:
        partition = _dashboard_metric_partition_values(path)
        if not partition:
            selected.append(path)
            continue
        if model_tokens and partition.get("model") not in model_tokens:
            continue
        if band_tokens and partition.get("band") not in band_tokens:
            if not (preserve_unbanded_bands and _is_unbanded_dashboard_value(partition.get("band"))):
                continue
        if metric_tokens and partition.get("metric") not in metric_tokens:
            continue
        selected.append(path)
    return selected


def _dashboard_metric_partition_values(path: Path) -> dict[str, str]:
    """Return sanitized partition values from one metric dataset path."""

    values: dict[str, str] = {}
    for part in path.parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key in {"model", "band", "metric"}:
            values[key] = value
    return values if {"model", "band", "metric"} <= set(values) else {}


def _filter_dashboard_metric_rows(
    df: pd.DataFrame,
    *,
    models: Sequence[str] | str | None = None,
    bands: Sequence[str] | str | None = None,
    metrics: Sequence[str] | str | None = None,
    periods_s: Sequence[float | str] | float | str | None = None,
    component: str | None = None,
    distance_range_km: tuple[float | None, float | None] | None = None,
    vs30_range: tuple[float | None, float | None] | None = None,
    preserve_unbanded_bands: bool = True,
    output_columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Apply dashboard metric row filters and restore requested column order."""

    out = df.copy()
    model_values = _filter_values(models)
    if model_values and "model" in out.columns:
        out = out[out["model"].astype(str).isin(model_values)]
    band_values = _filter_values(bands)
    if band_values and "band" in out.columns:
        band_mask = out["band"].astype(str).isin(band_values)
        if preserve_unbanded_bands:
            band_mask = band_mask | out["band"].map(_is_unbanded_dashboard_value)
        out = out[band_mask]
    metric_values = {normalize_metric_name(value) for value in _filter_values(metrics)}
    if metric_values and "metric" in out.columns:
        out = out[out["metric"].map(normalize_metric_name).isin(metric_values)]
    period_values = _numeric_filter_values(periods_s)
    if period_values and "period_s" in out.columns:
        periods = pd.to_numeric(out["period_s"], errors="coerce")
        rounded = periods.round(9)
        out = out[periods.isna() | rounded.isin(period_values)]
    if component and "component" in out.columns:
        out = out[out["component"].astype(str).str.upper() == str(component).upper()]
    out = _filter_numeric_range_any(out, ("med_dist_km", "distance_km", "dist_km"), distance_range_km)
    out = _filter_numeric_range_any(out, ("Vs30", "vs30"), vs30_range)
    if output_columns is not None:
        selected = [column for column in dict.fromkeys(str(column) for column in output_columns) if column in out.columns]
        out = out.loc[:, selected]
    return out.reset_index(drop=True)


def _normalize_max_rows(max_rows: int | None) -> int | None:
    """Return a non-negative row limit or ``None``."""

    if max_rows is None:
        return None
    value = int(max_rows)
    return max(value, 0)


def _filter_values(values: Sequence[str] | str | None) -> set[str]:
    """Normalize scalar or sequence dashboard filter values."""

    if values is None:
        return set()
    if isinstance(values, str):
        items = [values]
    else:
        items = list(values)
    return {str(item) for item in items if str(item).strip()}


def _numeric_filter_values(values: Sequence[float | str] | float | str | None) -> set[float]:
    """Return rounded numeric filter values from a scalar or sequence."""

    if values is None:
        return set()
    if isinstance(values, (str, int, float)):
        items = [values]
    else:
        items = list(values)
    out: set[float] = set()
    for item in items:
        value = pd.to_numeric(pd.Series([item]), errors="coerce").iloc[0]
        if pd.notna(value):
            out.add(round(float(value), 9))
    return out


def _filter_numeric_range_any(
    df: pd.DataFrame,
    columns: tuple[str, ...],
    bounds: tuple[float | None, float | None] | None,
) -> pd.DataFrame:
    """Apply a numeric range to the first available column."""

    if bounds is None:
        return df
    column = next((item for item in columns if item in df.columns), None)
    if column is None:
        return df
    lower, upper = bounds
    values = pd.to_numeric(df[column], errors="coerce")
    out = df
    if lower is not None:
        out = out[values >= float(lower)]
        values = values.loc[out.index]
    if upper is not None:
        out = out[values <= float(upper)]
    return out


def _is_unbanded_dashboard_value(value: object) -> bool:
    """Return whether one band or partition token represents broadband rows."""

    return str(value).strip().lower() in {"", "nan", "none", "all", "broadband", "unknown"}


def _filter_tokens(values: Sequence[str] | str | None) -> set[str]:
    """Return sanitized partition tokens for raw dashboard filter values."""

    return {safe_path_token(value) for value in _filter_values(values)}


def _metric_filter_tokens(values: Sequence[str] | str | None) -> set[str]:
    """Return sanitized partition tokens for metric names and their aliases."""

    tokens: set[str] = set()
    for value in _filter_values(values):
        tokens.add(safe_path_token(value))
        tokens.add(safe_path_token(normalize_metric_name(value)))
    return tokens


def _read_dashboard_metric_table(path: Path, *, columns: Sequence[str] | None = None) -> pd.DataFrame:
    """Read one dashboard metric table with optional column projection."""

    suffix = path.suffix.lower()
    selected = _selected_existing_columns(path, columns)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path, columns=selected)
    if suffix == ".csv":
        if selected is None:
            return pd.read_csv(path)
        wanted = set(selected)
        return pd.read_csv(path, usecols=lambda column: column in wanted, low_memory=False)
    raise ValueError(f"Unsupported dashboard metric table format for {path}. Use Parquet or CSV.")


def _iter_dashboard_metric_table_chunks(
    path: Path,
    *,
    columns: Sequence[str] | None = None,
    chunksize: int = 50_000,
):
    """Yield projected metric table chunks without requiring full materialization."""

    suffix = path.suffix.lower()
    selected = _selected_existing_columns(path, columns)
    size = max(int(chunksize), 1)
    if suffix in {".parquet", ".pq"}:
        try:
            import pyarrow.parquet as pq

            parquet = pq.ParquetFile(path)
            for batch in parquet.iter_batches(batch_size=size, columns=selected):
                yield batch.to_pandas()
            return
        except Exception:
            table = pd.read_parquet(path, columns=selected)
            for start in range(0, len(table), size):
                yield table.iloc[start : start + size].copy()
            return
    if suffix == ".csv":
        if selected is None:
            reader = pd.read_csv(path, chunksize=size, low_memory=False)
        else:
            wanted = set(selected)
            reader = pd.read_csv(path, usecols=lambda column: column in wanted, chunksize=size, low_memory=False)
        yield from reader
        return
    raise ValueError(f"Unsupported dashboard metric table format for {path}. Use Parquet or CSV.")


def _selected_existing_columns(path: Path, columns: Sequence[str] | None) -> list[str] | None:
    """Return requested columns that exist in one table."""

    if columns is None:
        return None
    requested = list(dict.fromkeys(str(column) for column in columns if str(column).strip()))
    if not requested:
        return []
    available = set(_dashboard_metric_table_columns(path))
    return [column for column in requested if column in available]


def _dashboard_metric_table_columns(path: Path) -> list[str]:
    """Return dashboard metric table columns without materializing row data."""

    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        try:
            import pyarrow.parquet as pq

            return list(pq.ParquetFile(path).schema.names)
        except Exception:
            return list(pd.read_parquet(path).head(0).columns)
    if suffix == ".csv":
        return list(pd.read_csv(path, nrows=0).columns)
    raise ValueError(f"Unsupported dashboard metric table format for {path}. Use Parquet or CSV.")


def write_dashboard_summary_dataset(
    input_root: str | Path | None = None,
    output_root: str | Path | None = None,
    *,
    hex_dist: float = 10.0,
    hex_az: float = 10.0,
    format: str = "parquet",
    replace_existing: bool = True,
) -> dict[str, Path]:
    """Build and write dashboard summary tables from a metric dataset.

    Parameters
    ----------
    input_root
        Dashboard metric dataset root. When omitted, the standard
        ``metrics_dashboard`` path is resolved from the active config.
    output_root
        Output directory for summary tables. When omitted, the standard
        ``dashboard_summaries`` path is resolved from the active config.
    hex_dist
        Distance-bin size in kilometers.
    hex_az
        Azimuth-bin size in degrees.
    format
        Output format, ``"parquet"`` or ``"csv"``.
    replace_existing
        Remove old dashboard summary files with the same table names before
        writing new summaries. This prevents stale ``.parquet`` files from
        shadowing newly written ``.csv`` summaries and vice versa.

    Returns
    -------
    dict[str, pathlib.Path]
        Written summary paths by table name.
    """

    resolved_input_root = input_root or resolve_output_path("metrics_dashboard", kind="dashboard")
    resolved_output_root = output_root or resolve_output_path("dashboard_summaries", kind="dashboard", create_parent=True)
    metrics = load_dashboard_metric_dataset(
        resolved_input_root,
        columns=dashboard_summary_input_columns(),
    )
    summaries = build_dashboard_summaries(metrics, hex_dist=hex_dist, hex_az=hex_az)
    return write_dashboard_summaries(summaries, resolved_output_root, format=format, replace_existing=replace_existing)


def write_configured_dashboard_datasets(
    tables: pd.DataFrame | str | Path | Sequence[pd.DataFrame | str | Path] | None = None,
    *,
    cfg: SpatialVTKConfig | str | Path | None = None,
    residual_mode: str = "logratio",
    partitioned: bool = False,
    hex_dist: float = 10.0,
    hex_az: float = 10.0,
    format: str = "parquet",
    replace_existing: bool = True,
) -> dict[str, Path]:
    """Write standard dashboard metric and summary datasets from config.

    Parameters
    ----------
    tables
        Metric rows to export. When omitted, the configured ``metrics_long``
        output table is used.
    cfg
        Optional Spatial-VTK config or config file path used to resolve
        ``metrics_long``, ``metrics_dashboard``, and ``dashboard_summaries``.
        When omitted, the active config is used.
    residual_mode
        Residual mode used when converting wide metric tables.
    partitioned
        Whether to partition the dashboard metric dataset by model, passband,
        and metric.
    hex_dist, hex_az
        Dashboard path-summary bin sizes.
    format
        Dashboard summary table format, ``"parquet"`` or ``"csv"``.
    replace_existing
        Replace previously written dashboard metric and summary artifacts before
        writing this run's outputs.

    Returns
    -------
    dict[str, pathlib.Path]
        Written dashboard roots and summary table paths.
    """

    config = _coerce_dashboard_config(cfg)
    metric_tables = tables if tables is not None else resolve_output_path("metrics_long", kind="table", cfg=config)
    dashboard_root = resolve_output_path("metrics_dashboard", kind="dashboard", cfg=config, create_parent=True)
    summary_root = resolve_output_path("dashboard_summaries", kind="dashboard", cfg=config, create_parent=True)
    metric_root = write_dashboard_metric_dataset(
        metric_tables,
        dashboard_root,
        residual_mode=residual_mode,
        partitioned=partitioned,
        replace_existing=replace_existing,
    )
    summary_paths = write_dashboard_summary_dataset(
        metric_root,
        summary_root,
        hex_dist=hex_dist,
        hex_az=hex_az,
        format=format,
        replace_existing=replace_existing,
    )
    return {
        "metrics_dashboard_root": metric_root,
        "dashboard_summary_root": Path(summary_root),
        **{f"dashboard_summary_{name}": path for name, path in summary_paths.items()},
    }


def _coerce_dashboard_config(cfg: SpatialVTKConfig | str | Path | None) -> SpatialVTKConfig | None:
    """Return a config object for dashboard output resolution."""

    if cfg is None or isinstance(cfg, SpatialVTKConfig):
        return cfg
    return SpatialVTKConfig.from_file(cfg)


def _clear_dashboard_metric_dataset(root: Path) -> None:
    """Remove recognized dashboard metric files from one output root."""

    for direct_name in ("metrics_long.parquet", "metrics_long.csv"):
        direct = root / direct_name
        if direct.exists():
            direct.unlink()
    for part_path in sorted(root.glob("model=*/band=*/metric=*/part.parquet"), key=lambda path: len(path.parts), reverse=True):
        part_path.unlink()
        for parent in (part_path.parent, part_path.parent.parent, part_path.parent.parent.parent):
            if parent == root or root not in parent.parents:
                continue
            try:
                parent.rmdir()
            except OSError:
                break


def add_dashboard_path_geometry(df: pd.DataFrame) -> pd.DataFrame:
    """Add distance, azimuth, and backazimuth columns when coordinates exist.

    Parameters
    ----------
    df
        Long metric table with event and station coordinates.

    Returns
    -------
    pandas.DataFrame
        Copy with ``distance_km``, ``azimuth_deg``, and ``backazimuth_deg``
        when enough coordinate columns are present.
    """

    out = df.copy()
    coordinate_sets = [
        ("event_lat", "event_lon", "sta_lat", "sta_lon"),
        ("event_lat", "event_lon", "station_lat", "station_lon"),
        ("event_lat", "event_lon", "lat", "lon"),
    ]
    selected = next((cols for cols in coordinate_sets if set(cols) <= set(out.columns)), None)
    if selected is None:
        return out
    event_lat, event_lon, station_lat, station_lon = selected
    lat1 = pd.to_numeric(out[event_lat], errors="coerce")
    lon1 = pd.to_numeric(out[event_lon], errors="coerce")
    lat2 = pd.to_numeric(out[station_lat], errors="coerce")
    lon2 = pd.to_numeric(out[station_lon], errors="coerce")
    out["distance_km"] = haversine_km(lat1, lon1, lat2, lon2)
    azimuth = forward_azimuth_deg(lat1, lon1, lat2, lon2)
    out["azimuth_deg"] = azimuth
    out["backazimuth_deg"] = (azimuth + 180.0) % 360.0
    return out


def haversine_km(lat1: Any, lon1: Any, lat2: Any, lon2: Any) -> np.ndarray:
    """Calculate great-circle distance in kilometers.

    Parameters
    ----------
    lat1, lon1, lat2, lon2
        Scalar or array-like coordinates in degrees.

    Returns
    -------
    numpy.ndarray
        Distance values in kilometers.
    """

    radius_km = 6371.0088
    lat1_arr = np.asarray(lat1, dtype=float)
    lon1_arr = np.asarray(lon1, dtype=float)
    lat2_arr = np.asarray(lat2, dtype=float)
    lon2_arr = np.asarray(lon2, dtype=float)
    dlat = np.radians(lat2_arr - lat1_arr)
    dlon = np.radians(lon2_arr - lon1_arr)
    a = np.sin(dlat / 2.0) ** 2 + np.cos(np.radians(lat1_arr)) * np.cos(np.radians(lat2_arr)) * np.sin(dlon / 2.0) ** 2
    return 2.0 * radius_km * np.arcsin(np.sqrt(a))


def forward_azimuth_deg(lat1: Any, lon1: Any, lat2: Any, lon2: Any) -> np.ndarray:
    """Calculate forward azimuth from event to station.

    Parameters
    ----------
    lat1, lon1
        Source coordinates in degrees.
    lat2, lon2
        Target coordinates in degrees.

    Returns
    -------
    numpy.ndarray
        Azimuth values in degrees clockwise from north.
    """

    lat1_rad = np.radians(np.asarray(lat1, dtype=float))
    lat2_rad = np.radians(np.asarray(lat2, dtype=float))
    dlon = np.radians(np.asarray(lon2, dtype=float) - np.asarray(lon1, dtype=float))
    x = np.sin(dlon) * np.cos(lat2_rad)
    y = np.cos(lat1_rad) * np.sin(lat2_rad) - np.sin(lat1_rad) * np.cos(lat2_rad) * np.cos(dlon)
    return (np.degrees(np.arctan2(x, y)) + 360.0) % 360.0


def safe_path_token(value: object) -> str:
    """Return a conservative token for partition paths.

    Parameters
    ----------
    value
        Value to include in a path component.

    Returns
    -------
    str
        Sanitized path token.
    """

    text = "unknown" if value is None or pd.isna(value) else str(value)
    return "".join(char if char.isalnum() or char in "._=-" else "_" for char in text).strip("_") or "unknown"


def _read_metric_table(table: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Read one metric table from dataframe, CSV, or parquet."""

    if isinstance(table, pd.DataFrame):
        return table.copy()
    path = Path(table).expanduser()
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _as_sequence(value: pd.DataFrame | str | Path | Sequence[pd.DataFrame | str | Path]) -> list[pd.DataFrame | str | Path]:
    """Normalize a scalar or sequence of metric-table inputs."""

    if isinstance(value, (pd.DataFrame, str, Path)):
        return [value]
    return list(value)


__all__ = [
    "add_dashboard_path_geometry",
    "dashboard_metric_dataset_paths",
    "forward_azimuth_deg",
    "haversine_km",
    "load_dashboard_metric_dataset",
    "safe_path_token",
    "write_dashboard_metric_dataset",
    "write_dashboard_summary_dataset",
    "write_configured_dashboard_datasets",
]
