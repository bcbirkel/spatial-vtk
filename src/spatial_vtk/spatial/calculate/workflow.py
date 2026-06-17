"""Workflow helpers for spatial-statistics tutorial and CLI outputs.

Purpose
-------
This module names the standard spatial-statistics output tables so notebooks,
scripts, and CLI wrappers can share the same file layout.

Usage examples
--------------
Create standard paths for spatial outputs:
  ``paths = spatial_statistics_output_paths("outputs/tutorials/step_04")``
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import time
from types import SimpleNamespace

import pandas as pd

from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.config.runtime import SpatialVTKConfig, active_config
from spatial_vtk.io import default_output_paths, load_output_table, read_table, write_output_table, write_table
from spatial_vtk.spatial.calculate.clustering import run_residual_feature_clustering
from spatial_vtk.spatial.calculate.correlation import (
    build_distance_bin_summary,
    compute_global_morans_i,
    moran_result_to_frame,
)
from spatial_vtk.spatial.calculate.geology import bootstrap_contrast_table
from spatial_vtk.spatial.calculate.pca import compute_pca_spatial_modes
from spatial_vtk.spatial.calculate.prepare_stats import (
    build_metric_field,
    build_station_feature_table,
    center_field_by_event,
    summarize_station_bias,
)
from spatial_vtk.spatial.calculate.settings import SpatialStatisticsSettings, spatial_statistics_settings_from_config


SPATIAL_STATISTICS_OUTPUT_NAMES: tuple[str, ...] = (
    "metric_field.parquet",
    "event_centered_residuals.parquet",
    "station_bias.parquet",
    "morans_i",
    "permutation_moran",
    "distance_bin_correlations",
    "clusters.parquet",
    "cluster_scores",
    "cluster_summary",
    "pca_station_scores.parquet",
    "pca_feature_loadings",
    "pca_explained_variance",
    "geology_contrasts",
    "geojson_region_summaries",
)

SPATIAL_STATISTICS_OUTPUT_DESCRIPTIONS: dict[str, str] = {
    "metric_field": "Metric field table",
    "event_centered_residuals": "Event-centered residuals",
    "station_bias": "Station-bias summary",
    "morans_i": "Moran's I summary",
    "permutation_moran": "Permutation Moran test summary",
    "distance_bin_correlations": "Distance-bin correlations",
    "clusters": "Cluster assignments",
    "cluster_scores": "Cluster solution scores",
    "cluster_summary": "Cluster summary",
    "pca_station_scores": "PCA station scores",
    "pca_feature_loadings": "PCA feature loadings",
    "pca_explained_variance": "PCA explained variance",
    "geology_contrasts": "Geology contrast summary",
    "geojson_region_summaries": "GeoJSON region summaries",
}

SPATIAL_SUMMARY_OUTPUT_KEYS: tuple[str, ...] = (
    "metric_field",
    "event_centered_residuals",
    "station_bias",
    "morans_i",
    "distance_bin_correlations",
    "clusters",
    "cluster_scores",
    "cluster_feature_summary",
    "cluster_summary",
    "pca_station_scores",
    "pca_feature_loadings",
    "pca_explained_variance",
    "geology_contrasts",
)

SPATIAL_WORKFLOW_TABLE_KEYS: tuple[str, ...] = (
    "metric_field",
    "event_centered_residuals",
    "station_bias",
    "morans_i",
    "permutation_moran",
    "distance_bin_correlations",
    "clusters",
    "cluster_scores",
    "cluster_feature_summary",
    "cluster_summary",
    "pca_station_scores",
    "pca_feature_loadings",
    "pca_explained_variance",
    "geology_contrasts",
)

SPATIAL_SUMMARY_COLUMNS: dict[str, tuple[str, ...]] = {
    "station_bias": (
        "station",
        "lat",
        "lon",
        "n_events",
        "mean_centered",
        "median_centered",
        "std_centered",
        "sem_centered",
        "abs_mean_centered",
        "bias_zscore",
        "metric",
    ),
    "morans_i": ("n", "k", "moran_i", "p_two_sided", "permutations", "metric"),
    "distance_bin_correlations": (
        "distance_start_km",
        "distance_end_km",
        "distance_center_km",
        "pair_count",
        "mean_pair_correlation",
        "semivariance",
        "metric",
    ),
    "clusters": (
        "station",
        "lat",
        "lon",
        "feature_nonmissing_count",
        "cluster_id",
        "cluster_name",
        "cluster_k",
        "best_silhouette",
        "cluster_feature_count",
        "metric",
    ),
    "cluster_scores": ("n_clusters", "silhouette", "inertia", "n_samples", "n_features", "metric"),
    "cluster_feature_summary": (
        "cluster_id",
        "cluster_name",
        "feature",
        "feature_mean",
        "feature_median",
        "feature_std",
        "feature_nonmissing_count",
        "station_count",
        "metric",
    ),
    "cluster_summary": ("cluster_id", "cluster_name", "station_count", "lat_mean", "lon_mean", "metric"),
    "pca_station_scores": ("station", "lat", "lon", "feature_nonmissing_count", "metric"),
    "pca_feature_loadings": ("mode", "mode_index", "feature", "loading", "absolute_loading", "metric"),
    "pca_explained_variance": (
        "mode",
        "mode_index",
        "explained_variance",
        "explained_variance_ratio",
        "cumulative_explained_variance_ratio",
        "singular_value",
        "n_stations",
        "n_features",
        "standardized",
        "metric",
    ),
    "geology_contrasts": (
        "group_col",
        "left_values",
        "right_values",
        "contrast_label",
        "effect_direction",
        "value_col",
        "statistic",
        "effect",
        "ci_low",
        "ci_high",
        "bootstrap_p",
        "n_left_stations",
        "n_right_stations",
        "n_events",
        "metric",
    ),
}


@dataclass(frozen=True)
class SpatialStatisticsWorkflowResult:
    """Result returned by :func:`run_spatial_statistics_workflow`.

    Parameters
    ----------
    metrics
        Metric names processed.
    tables
        Output table dataframes keyed by registered output name.
    paths
        Written output paths keyed by registered output name.
    failures
        Non-fatal per-metric step failures. Expensive large runs should still
        write all successful tables instead of discarding work after one
        optional diagnostic fails.
    elapsed_s
        Total workflow wall time in seconds.
    """

    metrics: tuple[str, ...]
    tables: dict[str, pd.DataFrame]
    paths: dict[str, Path]
    failures: tuple[dict[str, str], ...]
    elapsed_s: float


@dataclass(frozen=True)
class _SpatialMetricCheckpoint:
    """Loaded checkpoint tables for one spatial metric."""

    tables: dict[str, pd.DataFrame]
    failures: tuple[dict[str, str], ...]


def spatial_statistics_output_paths(output_dir: str | Path) -> SimpleNamespace:
    """Return standard Step 4 spatial-statistics output paths.

    Parameters
    ----------
    output_dir
        Directory where spatial-statistics tables should be written.

    Returns
    -------
    types.SimpleNamespace
        Namespace with one attribute per standard output table.
    """

    return default_output_paths(output_dir, SPATIAL_STATISTICS_OUTPUT_NAMES)


def run_spatial_statistics_workflow(
    metrics: pd.DataFrame | str | Path | None = None,
    *,
    cfg: SpatialVTKConfig | None = None,
    metric: str | Sequence[str] | None = None,
    station_metadata: pd.DataFrame | str | Path | None = None,
    resume: bool = True,
    checkpoint_dir: str | Path | None = None,
    verbose: bool = False,
) -> SpatialStatisticsWorkflowResult:
    """Build and write the standard spatial-statistics tables.

    Parameters
    ----------
    metrics
        Long metric table or path. When omitted, the configured
        ``metrics_long`` output table is used.
    cfg
        Optional Spatial-VTK config. The config is activated during execution
        because lower-level spatial helpers read active spatial settings.
    metric
        Optional metric override. Use ``"all"`` to process each available
        metric in the input table, or pass a sequence such as
        ``("PGA", "FAS")`` to process a curated subset.
    station_metadata
        Optional prepared station metadata table or path for geology contrasts.
        When omitted, the configured ``prepared_stations`` output is used if it
        exists.
    resume
        Reuse per-metric checkpoints for path-backed runs. In-memory dataframe
        inputs only use checkpoints when ``checkpoint_dir`` is explicitly set.
    checkpoint_dir
        Optional base directory for internal per-metric checkpoints. The
        workflow creates a hashed run subdirectory so checkpoints are reused
        only when the metric input path and spatial settings match.
    verbose
        Print elapsed-time status updates suitable for Slurm logs.

    Returns
    -------
    SpatialStatisticsWorkflowResult
        Written tables, output paths, non-fatal failures, and elapsed time.
    """

    config = cfg or active_config()
    config.activate()
    settings = spatial_statistics_settings_from_config(config)
    start = time.monotonic()

    def progress(message: str) -> None:
        if verbose:
            elapsed = time.monotonic() - start
            print(f"Spatial statistics: {message} (elapsed {elapsed:.1f}s)", flush=True)

    metrics_path = None
    if metrics is None:
        metrics_path = resolve_output_path("metrics_long", kind="table", cfg=config, create_parent=True)
        progress(f"reading {metrics_path}")
        metrics_df = read_table(metrics_path)
    elif isinstance(metrics, pd.DataFrame):
        metrics_df = metrics.copy()
    else:
        metrics_path = Path(metrics).expanduser()
        progress(f"reading {metrics_path}")
        metrics_df = read_table(metrics_path)

    metrics_to_run = _spatial_metric_list(metrics_df, metric or settings.metric)
    progress(f"running {len(metrics_to_run)} metric(s): {', '.join(metrics_to_run)}")
    station_df = _load_station_metadata(station_metadata, cfg=config, progress=progress)
    failures: list[dict[str, str]] = []

    checkpoint_run_dir: Path | None = None
    if resume and (metrics_path is not None or checkpoint_dir is not None):
        checkpoint_run_dir = _spatial_checkpoint_run_dir(
            config,
            checkpoint_dir=checkpoint_dir,
            metrics_path=metrics_path,
            metrics_df=metrics_df,
            metrics_to_run=metrics_to_run,
            settings=settings,
        )
        _write_checkpoint_manifest(
            checkpoint_run_dir,
            _spatial_checkpoint_signature(
                metrics_path=metrics_path,
                metrics_df=metrics_df,
                metrics_to_run=metrics_to_run,
                settings=settings,
            ),
        )
        progress(f"checkpoint directory {checkpoint_run_dir}")
    elif resume:
        progress("checkpoint resume disabled for in-memory metrics; pass checkpoint_dir to enable it")
    else:
        progress("checkpoint resume disabled")

    field_tables: list[pd.DataFrame] = []
    centered_tables: list[pd.DataFrame] = []
    station_bias_tables: list[pd.DataFrame] = []
    moran_tables: list[pd.DataFrame] = []
    distance_tables: list[pd.DataFrame] = []
    cluster_tables: list[pd.DataFrame] = []
    cluster_score_tables: list[pd.DataFrame] = []
    cluster_feature_tables: list[pd.DataFrame] = []
    cluster_summary_tables: list[pd.DataFrame] = []
    pca_score_tables: list[pd.DataFrame] = []
    pca_loading_tables: list[pd.DataFrame] = []
    pca_variance_tables: list[pd.DataFrame] = []
    geology_tables: list[pd.DataFrame] = []
    table_lists = {
        "metric_field": field_tables,
        "event_centered_residuals": centered_tables,
        "station_bias": station_bias_tables,
        "morans_i": moran_tables,
        "distance_bin_correlations": distance_tables,
        "clusters": cluster_tables,
        "cluster_scores": cluster_score_tables,
        "cluster_feature_summary": cluster_feature_tables,
        "cluster_summary": cluster_summary_tables,
        "pca_station_scores": pca_score_tables,
        "pca_feature_loadings": pca_loading_tables,
        "pca_explained_variance": pca_variance_tables,
        "geology_contrasts": geology_tables,
    }

    for metric_index, metric_name in enumerate(metrics_to_run, start=1):
        prefix = f"metric {metric_index}/{len(metrics_to_run)} {metric_name}"
        if checkpoint_run_dir is not None:
            checkpoint = _load_metric_checkpoint(checkpoint_run_dir, metric_name)
            if checkpoint is not None:
                _append_checkpoint_tables(checkpoint.tables, table_lists)
                failures.extend(checkpoint.failures)
                progress(f"{prefix}: reusing checkpoint")
                continue

        table_start_indices = {key: len(frames) for key, frames in table_lists.items()}
        failure_start = len(failures)

        progress(f"{prefix}: building metric field")
        try:
            field_value_column = _spatial_field_value_column(metrics_df, settings)
            metric_field = build_metric_field(metrics_df, metric=metric_name, value_column=field_value_column)
        except Exception as exc:
            _record_failure(failures, metric_name, "metric_field", exc, progress)
            continue
        metric_field = _with_metric(metric_field, metric_name)
        field_tables.append(metric_field)

        progress(f"{prefix}: centering by event")
        try:
            centered = center_field_by_event(
                metric_field,
                min_stations_per_event=settings.min_stations_per_event,
                remove_event_mean=settings.remove_event_mean,
            )
        except Exception as exc:
            _record_failure(failures, metric_name, "event_centering", exc, progress)
            centered = metric_field.iloc[0:0].copy()
        centered = _with_metric(centered, metric_name)
        centered_tables.append(centered)

        progress(f"{prefix}: summarizing station bias")
        try:
            station_bias = summarize_station_bias(centered, min_events_per_station=settings.min_events_per_station) if "station" in centered.columns else pd.DataFrame()
        except Exception as exc:
            _record_failure(failures, metric_name, "station_bias", exc, progress)
            station_bias = pd.DataFrame()
        station_bias = _with_metric(station_bias, metric_name)
        station_bias_tables.append(station_bias)

        progress(f"{prefix}: computing Moran's I")
        try:
            morans_i = moran_result_to_frame(
                compute_global_morans_i(
                    station_bias,
                    k=settings.moran_neighbors,
                    permutations=settings.moran_permutations,
                    random_seed=settings.random_seed,
                )
            )
            moran_tables.append(_with_metric(morans_i, metric_name))
        except Exception as exc:
            _record_failure(failures, metric_name, "morans_i", exc, progress)

        progress(f"{prefix}: building distance-bin correlations")
        try:
            distance_corr = build_distance_bin_summary(
                centered,
                bin_width_km=settings.distance_bin_width_km,
                random_seed=settings.random_seed,
            )
            distance_tables.append(_with_metric(distance_corr, metric_name))
        except Exception as exc:
            _record_failure(failures, metric_name, "distance_bin_correlations", exc, progress)

        progress(f"{prefix}: building station feature table")
        try:
            features = build_station_feature_table(centered)
        except Exception as exc:
            _record_failure(failures, metric_name, "station_features", exc, progress)
            features = pd.DataFrame(columns=["station", "lat", "lon"])

        progress(f"{prefix}: running residual-feature clustering")
        try:
            clusters, cluster_scores, cluster_features, cluster_summary, _best, _feature_cols = run_residual_feature_clustering(
                features,
                cluster_min_k=settings.cluster_min_k,
                cluster_max_k=settings.cluster_max_k,
                random_seed=settings.random_seed,
            )
            cluster_tables.append(_with_metric(clusters, metric_name))
            cluster_score_tables.append(_with_metric(cluster_scores, metric_name))
            cluster_feature_tables.append(_with_metric(cluster_features, metric_name))
            cluster_summary_tables.append(_with_metric(cluster_summary, metric_name))
        except Exception as exc:
            _record_failure(failures, metric_name, "clustering", exc, progress)

        progress(f"{prefix}: running PCA spatial modes")
        try:
            pca_result = compute_pca_spatial_modes(features, n_components=settings.pca_components)
            pca_score_tables.append(_with_metric(pca_result.station_scores, metric_name))
            pca_loading_tables.append(_with_metric(pca_result.feature_loadings, metric_name))
            pca_variance_tables.append(_with_metric(pca_result.explained_variance, metric_name))
        except Exception as exc:
            _record_failure(failures, metric_name, "pca", exc, progress)

        progress(f"{prefix}: building geology contrasts")
        if station_df is None:
            _record_failure(failures, metric_name, "geology_contrasts", RuntimeError("prepared station metadata is unavailable"), progress)
        else:
            try:
                geology = bootstrap_contrast_table(
                    centered,
                    station_metadata=station_df,
                    group_col=settings.geology_group_column,
                    left_values=settings.geology_left_values,
                    right_values=settings.geology_right_values,
                    min_stations_per_group=settings.geology_min_stations_per_group,
                    n_bootstrap=settings.geology_bootstrap_samples,
                    random_seed=settings.random_seed,
                    statistic=settings.geology_statistic,
                )
                geology_tables.append(_with_metric(geology, metric_name))
            except Exception as exc:
                _record_failure(failures, metric_name, "geology_contrasts", exc, progress)

        if checkpoint_run_dir is not None:
            metric_tables = _metric_checkpoint_tables(
                table_lists,
                table_start_indices,
                metrics_columns=tuple(metrics_df.columns),
            )
            _write_metric_checkpoint(
                checkpoint_run_dir,
                metric_name,
                tables=metric_tables,
                failures=tuple(failures[failure_start:]),
            )
            progress(f"{prefix}: wrote checkpoint")

    progress("writing combined spatial tables")
    tables = {
        "metric_field": _concat_or_empty(field_tables, tuple(metrics_df.columns)),
        "event_centered_residuals": _concat_or_empty(centered_tables, ("model", "band", "component", "event_id", "station", "field_value", "field_centered", "metric")),
        "station_bias": _concat_or_empty(station_bias_tables, SPATIAL_SUMMARY_COLUMNS["station_bias"]),
        "morans_i": _concat_or_empty(moran_tables, SPATIAL_SUMMARY_COLUMNS["morans_i"]),
        "permutation_moran": _concat_or_empty(moran_tables, SPATIAL_SUMMARY_COLUMNS["morans_i"]),
        "distance_bin_correlations": _concat_or_empty(distance_tables, SPATIAL_SUMMARY_COLUMNS["distance_bin_correlations"]),
        "clusters": _concat_or_empty(cluster_tables, SPATIAL_SUMMARY_COLUMNS["clusters"]),
        "cluster_scores": _concat_or_empty(cluster_score_tables, SPATIAL_SUMMARY_COLUMNS["cluster_scores"]),
        "cluster_feature_summary": _concat_or_empty(cluster_feature_tables, SPATIAL_SUMMARY_COLUMNS["cluster_feature_summary"]),
        "cluster_summary": _concat_or_empty(cluster_summary_tables, SPATIAL_SUMMARY_COLUMNS["cluster_summary"]),
        "pca_station_scores": _concat_or_empty(pca_score_tables, SPATIAL_SUMMARY_COLUMNS["pca_station_scores"]),
        "pca_feature_loadings": _concat_or_empty(pca_loading_tables, SPATIAL_SUMMARY_COLUMNS["pca_feature_loadings"]),
        "pca_explained_variance": _concat_or_empty(pca_variance_tables, SPATIAL_SUMMARY_COLUMNS["pca_explained_variance"]),
        "geology_contrasts": _concat_or_empty(geology_tables, SPATIAL_SUMMARY_COLUMNS["geology_contrasts"]),
    }
    paths = {key: write_output_table(key, table, cfg=config) for key, table in tables.items()}
    elapsed = time.monotonic() - start
    progress(
        "complete: "
        f"metric_field={len(tables['metric_field'])}, "
        f"centered={len(tables['event_centered_residuals'])}, "
        f"station_bias={len(tables['station_bias'])}"
    )
    return SpatialStatisticsWorkflowResult(
        metrics=tuple(metrics_to_run),
        tables=tables,
        paths=paths,
        failures=tuple(failures),
        elapsed_s=float(elapsed),
    )


def _spatial_checkpoint_run_dir(
    cfg: SpatialVTKConfig,
    *,
    checkpoint_dir: str | Path | None,
    metrics_path: Path | None,
    metrics_df: pd.DataFrame,
    metrics_to_run: Sequence[str],
    settings: SpatialStatisticsSettings,
) -> Path:
    """Return the hashed checkpoint directory for one spatial workflow run."""

    if checkpoint_dir is None:
        output_dir = resolve_output_path("metric_field", kind="table", cfg=cfg, create_parent=True).parent
        base_dir = output_dir / ".spatial_statistics_checkpoints"
    else:
        base_dir = Path(checkpoint_dir).expanduser()
    signature = _spatial_checkpoint_signature(
        metrics_path=metrics_path,
        metrics_df=metrics_df,
        metrics_to_run=metrics_to_run,
        settings=settings,
    )
    token = hashlib.sha256(json.dumps(signature, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return base_dir / token


def _spatial_checkpoint_signature(
    *,
    metrics_path: Path | None,
    metrics_df: pd.DataFrame,
    metrics_to_run: Sequence[str],
    settings: SpatialStatisticsSettings,
) -> dict[str, object]:
    """Return a JSON-stable signature for spatial checkpoint reuse."""

    if metrics_path is not None:
        resolved = Path(metrics_path).expanduser().resolve()
        stat = resolved.stat()
        input_signature: dict[str, object] = {
            "path": str(resolved),
            "mtime_ns": int(stat.st_mtime_ns),
            "size": int(stat.st_size),
        }
    else:
        input_signature = {
            "dataframe_rows": int(len(metrics_df)),
            "columns": [str(column) for column in metrics_df.columns],
            "metrics": sorted(metrics_df["metric"].dropna().astype(str).unique().tolist()) if "metric" in metrics_df.columns else [],
        }
    return {
        "version": 1,
        "metrics_input": input_signature,
        "metrics_to_run": [str(item) for item in metrics_to_run],
        "settings": _json_ready(asdict(settings)),
    }


def _write_checkpoint_manifest(run_dir: Path, signature: dict[str, object]) -> None:
    """Write one checkpoint manifest for auditability."""

    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(run_dir / "manifest.json", signature)


def _load_metric_checkpoint(run_dir: Path, metric_name: str) -> _SpatialMetricCheckpoint | None:
    """Load one completed per-metric checkpoint if every table is present."""

    metric_dir = _metric_checkpoint_dir(run_dir, metric_name)
    failures_path = metric_dir / "failures.json"
    if not failures_path.exists():
        return None
    table_paths = {key: metric_dir / f"{key}.parquet" for key in SPATIAL_WORKFLOW_TABLE_KEYS}
    if any(not path.exists() for path in table_paths.values()):
        return None
    tables = {key: read_table(path) for key, path in table_paths.items()}
    try:
        failures_payload = json.loads(failures_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    failures = tuple(dict(item) for item in failures_payload if isinstance(item, dict))
    return _SpatialMetricCheckpoint(tables=tables, failures=failures)


def _write_metric_checkpoint(
    run_dir: Path,
    metric_name: str,
    *,
    tables: dict[str, pd.DataFrame],
    failures: tuple[dict[str, str], ...],
) -> None:
    """Write one complete per-metric checkpoint atomically table-by-table."""

    metric_dir = _metric_checkpoint_dir(run_dir, metric_name)
    metric_dir.mkdir(parents=True, exist_ok=True)
    for key in SPATIAL_WORKFLOW_TABLE_KEYS:
        write_table(tables[key], metric_dir / f"{key}.parquet")
    _write_json_atomic(metric_dir / "failures.json", list(failures))


def _metric_checkpoint_tables(
    table_lists: dict[str, list[pd.DataFrame]],
    start_indices: dict[str, int],
    *,
    metrics_columns: tuple[str, ...],
) -> dict[str, pd.DataFrame]:
    """Extract tables produced for one metric from the workflow accumulators."""

    tables: dict[str, pd.DataFrame] = {}
    for key in SPATIAL_WORKFLOW_TABLE_KEYS:
        if key == "permutation_moran":
            frames = table_lists["morans_i"][start_indices["morans_i"] :]
        else:
            frames = table_lists.get(key, [])[start_indices.get(key, 0) :]
        tables[key] = _concat_or_empty(frames, _spatial_columns_for_key(key, metrics_columns))
    return tables


def _append_checkpoint_tables(tables: dict[str, pd.DataFrame], table_lists: dict[str, list[pd.DataFrame]]) -> None:
    """Append loaded per-metric checkpoint tables to workflow accumulators."""

    for key, frames in table_lists.items():
        frame = tables.get(key)
        if frame is not None and not frame.empty:
            frames.append(frame)


def _spatial_columns_for_key(key: str, metrics_columns: tuple[str, ...]) -> tuple[str, ...]:
    """Return known output columns for one spatial workflow table key."""

    if key == "metric_field":
        return tuple(metrics_columns)
    if key == "event_centered_residuals":
        return ("model", "band", "component", "event_id", "station", "field_value", "field_centered", "metric")
    if key == "permutation_moran":
        return SPATIAL_SUMMARY_COLUMNS["morans_i"]
    return SPATIAL_SUMMARY_COLUMNS.get(key, ())


def _metric_checkpoint_dir(run_dir: Path, metric_name: str) -> Path:
    """Return a collision-resistant directory for one metric name."""

    text = str(metric_name)
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._") or "metric"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return run_dir / f"{slug}-{digest}"


def _write_json_atomic(path: Path, payload: object) -> None:
    """Write a JSON file through a same-directory temporary path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(json.dumps(_json_ready(payload), indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def _json_ready(value: object) -> object:
    """Coerce dataclass payload values to JSON-safe objects."""

    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def _spatial_metric_list(metrics: pd.DataFrame, configured: str | Sequence[str]) -> list[str]:
    """Return metric names to process for a spatial workflow."""

    available = sorted(metrics["metric"].dropna().astype(str).unique().tolist()) if "metric" in metrics.columns else []
    if not isinstance(configured, str) and isinstance(configured, Sequence):
        selected = [str(item).strip() for item in configured if str(item).strip()]
        if not selected:
            return available
        missing = [item for item in selected if available and item not in available]
        if missing:
            raise KeyError(f"Configured spatial metrics {missing!r} are not present in metrics_long. Choices: {available}")
        return selected
    token = str(configured).strip()
    if token.lower() in {"all", "*", ""}:
        return available or [token or "all"]
    if available and token not in available:
        raise KeyError(f"Configured spatial metric {token!r} is not present in metrics_long. Choices: {available}")
    return [token]


def _spatial_field_value_column(metrics: pd.DataFrame, settings: SpatialStatisticsSettings) -> str:
    """Return a value selector compatible with long and wide metric tables."""

    configured = str(settings.value_column or "auto")
    if "metric" in metrics.columns:
        return configured
    if configured in {"auto", "log2_ratio", "score"} or configured in metrics.columns:
        return configured
    return "auto"


def _concat_or_empty(frames: list[pd.DataFrame], columns: tuple[str, ...]) -> pd.DataFrame:
    """Concatenate non-empty frames or return an empty frame with known columns."""

    usable = [frame for frame in frames if frame is not None and not frame.empty]
    if usable:
        return pd.concat(usable, ignore_index=True, sort=False)
    return pd.DataFrame(columns=list(columns))


def _with_metric(frame: pd.DataFrame, metric_name: str) -> pd.DataFrame:
    """Ensure one output frame contains a metric column."""

    out = frame.copy()
    if "metric" not in out.columns:
        out["metric"] = metric_name
    return out


def _load_station_metadata(
    station_metadata: pd.DataFrame | str | Path | None,
    *,
    cfg: SpatialVTKConfig,
    progress,
) -> pd.DataFrame | None:
    """Load optional station metadata for geology summaries."""

    if isinstance(station_metadata, pd.DataFrame):
        return station_metadata.copy()
    if station_metadata is not None:
        path = Path(station_metadata).expanduser()
        progress(f"reading station metadata {path}")
        return read_table(path)
    try:
        return load_output_table("prepared_stations", cfg=cfg)
    except Exception as exc:
        progress(f"prepared station metadata unavailable for geology contrasts: {exc}")
        return None


def _record_failure(failures: list[dict[str, str]], metric: str, step: str, exc: Exception, progress) -> None:
    """Record and print one non-fatal workflow failure."""

    message = str(exc)
    failures.append({"metric": str(metric), "step": str(step), "error": type(exc).__name__, "message": message})
    progress(f"metric {metric} {step} failed: {message}")


__all__ = [
    "SPATIAL_STATISTICS_OUTPUT_DESCRIPTIONS",
    "SPATIAL_STATISTICS_OUTPUT_NAMES",
    "SPATIAL_SUMMARY_OUTPUT_KEYS",
    "SpatialStatisticsWorkflowResult",
    "run_spatial_statistics_workflow",
    "spatial_statistics_output_paths",
]
