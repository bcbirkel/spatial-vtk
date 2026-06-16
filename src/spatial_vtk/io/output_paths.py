"""Reusable output-path and output-group helpers.

Purpose
-------
This module gives notebooks, scripts, and CLI wrappers a small common way to
name output files without repeatedly spelling out filenames in each workflow.

Usage examples
--------------
Create explicit CSV paths:
  ``tables = default_output_paths(output_root, ["prepared_stations", "prepared_events"])``
  ``stations.to_csv(tables.prepared_stations, index=False)``
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable, Literal

from spatial_vtk.config.outputs import OutputKind, resolve_output_path
from spatial_vtk.config.runtime import SpatialVTKConfig


OutputGroupName = Literal[
    "step_01_ingest",
    "step_02_qc",
    "step_03_metrics",
    "step_04_spatial",
    "step_05_geojson",
    "step_06_plotting",
    "step_07_dashboards",
    "large_run_core",
]

DEFAULT_OUTPUT_SUFFIXES: dict[str, str] = {
    "qc_inventory_overlap": ".parquet",
}


@dataclass(frozen=True)
class OutputArtifact:
    """One named output artifact in a workflow group.

    Parameters
    ----------
    name
        Human-readable variable-style name, such as ``"metrics_long_path"``.
    key
        Output registry key resolved with :func:`resolve_output_path`.
    kind
        Artifact kind: ``"table"``, ``"figure"``, or ``"dashboard"``.
    required
        Whether the artifact is required for the workflow stage to be complete.
    """

    name: str
    key: str
    kind: OutputKind = "table"
    required: bool = True


OUTPUT_GROUPS: dict[str, tuple[OutputArtifact, ...]] = {
    "step_01_ingest": (
        OutputArtifact("prepared_stations_path", "prepared_stations"),
        OutputArtifact("prepared_events_path", "prepared_events"),
        OutputArtifact("event_station_path", "event_station_records"),
        OutputArtifact("record_coverage_path", "record_coverage"),
    ),
    "step_02_qc": (
        OutputArtifact("event_station_path", "event_station_records"),
        OutputArtifact("trace_qc_path", "qc_trace_summary"),
        OutputArtifact("qc_inventory_path", "qc_inventory"),
        OutputArtifact("qc_inventory_overlap_path", "qc_inventory_overlap"),
        OutputArtifact("comparison_eligible_path", "comparison_eligible_records"),
        OutputArtifact("manual_queue_path", "manual_review_queue", required=False),
        OutputArtifact("retention_path", "qc_metric_pair_retention"),
        OutputArtifact("event_station_retention_path", "qc_event_station_pair_retention"),
        OutputArtifact("post_qc_records_path", "post_qc_records"),
        OutputArtifact("drop_causes_path", "qc_drop_causes"),
        OutputArtifact("drop_causes_overlap_path", "qc_drop_causes_overlap"),
    ),
    "step_03_metrics": (
        OutputArtifact("qc_inventory_overlap_path", "qc_inventory_overlap"),
        OutputArtifact("metrics_long_path", "metrics_long"),
        OutputArtifact("metrics_enriched_path", "metrics_enriched"),
        OutputArtifact("path_table_path", "path_table"),
        OutputArtifact("path_summary_path", "path_summary"),
    ),
    "step_04_spatial": (
        OutputArtifact("metrics_long_path", "metrics_long"),
        OutputArtifact("metric_field_path", "metric_field"),
        OutputArtifact("event_centered_path", "event_centered_residuals"),
        OutputArtifact("station_bias_path", "station_bias"),
        OutputArtifact("morans_i_path", "morans_i"),
        OutputArtifact("distance_corr_path", "distance_bin_correlations"),
        OutputArtifact("clusters_path", "clusters"),
        OutputArtifact("cluster_scores_path", "cluster_scores"),
        OutputArtifact("cluster_summary_path", "cluster_summary"),
        OutputArtifact("cluster_features_path", "cluster_feature_summary"),
        OutputArtifact("pca_scores_path", "pca_station_scores"),
        OutputArtifact("pca_loadings_path", "pca_feature_loadings"),
        OutputArtifact("pca_explained_path", "pca_explained_variance"),
        OutputArtifact("geology_path", "geology_contrasts"),
    ),
    "step_05_geojson": (
        OutputArtifact("geojson_summaries_path", "geojson_region_summaries"),
        OutputArtifact("metrics_long_path", "metrics_long"),
        OutputArtifact("path_table_path", "path_table"),
        OutputArtifact("metrics_enriched_path", "metrics_enriched"),
        OutputArtifact("comparison_eligible_path", "comparison_eligible_records"),
    ),
    "step_06_plotting": (
        OutputArtifact("comparison_eligible_path", "comparison_eligible_records"),
        OutputArtifact("event_station_path", "event_station_records"),
        OutputArtifact("metrics_long_path", "metrics_long"),
        OutputArtifact("metrics_enriched_path", "metrics_enriched"),
        OutputArtifact("event_trace_comparison_path", "event_trace_comparison", kind="figure", required=False),
    ),
    "step_07_dashboards": (
        OutputArtifact("metrics_long_path", "metrics_long"),
        OutputArtifact("qc_trace_summary_path", "qc_trace_summary"),
        OutputArtifact("qc_inventory_path", "qc_inventory"),
        OutputArtifact("qc_inventory_overlap_path", "qc_inventory_overlap"),
        OutputArtifact("metrics_dashboard_root", "metrics_dashboard", kind="dashboard"),
        OutputArtifact("dashboard_summary_root", "dashboard_summaries", kind="dashboard"),
    ),
}

def default_output_paths(
    output_dir: str | Path,
    names: Iterable[str],
    *,
    suffix: str = ".csv",
    create_dir: bool = True,
) -> SimpleNamespace:
    """Return a namespace of standard output paths.

    Parameters
    ----------
    output_dir
        Directory where output files should be written.
    names
        Basenames without extension, such as ``"qc_inventory"``.
    suffix
        File extension to append when a name has no extension.
    create_dir
        Whether to create ``output_dir``.

    Returns
    -------
    types.SimpleNamespace
        Namespace with one attribute per normalized name.
    """

    root = Path(output_dir).expanduser()
    if create_dir:
        root.mkdir(parents=True, exist_ok=True)
    paths = {}
    for raw_name in names:
        name = str(raw_name).strip()
        if not name:
            continue
        path = Path(name)
        attr = path.stem.replace("-", "_").replace(" ", "_")
        resolved_suffix = DEFAULT_OUTPUT_SUFFIXES.get(path.name, suffix)
        filename = path.name if path.suffix else f"{path.name}{resolved_suffix}"
        paths[attr] = root / filename
    return SimpleNamespace(**paths)


def output_group_artifacts(group: str) -> tuple[OutputArtifact, ...]:
    """Return artifact definitions for one named workflow output group.

    Parameters
    ----------
    group
        Group name such as ``"step_02_qc"`` or ``"step_04_spatial"``.

    Returns
    -------
    tuple of OutputArtifact
        Artifact definitions in display order.
    """

    key = str(group).strip().lower().replace("-", "_").replace(" ", "_")
    try:
        return OUTPUT_GROUPS[key]
    except KeyError as exc:
        choices = ", ".join(sorted(OUTPUT_GROUPS))
        raise KeyError(f"Unknown output group {group!r}. Choices: {choices}") from exc


def output_group_paths(
    group: str,
    *,
    cfg: SpatialVTKConfig | None = None,
    create_parent: bool = True,
    include_optional: bool = True,
) -> dict[str, Path]:
    """Resolve paths for one workflow output group.

    Parameters
    ----------
    group
        Group name such as ``"step_03_metrics"``.
    cfg
        Optional config object. When omitted, the active config is used.
    create_parent
        Whether to create output parent directories.
    include_optional
        Whether to include optional artifacts.

    Returns
    -------
    dict
        Mapping from variable-style artifact names to resolved paths.
    """

    paths: dict[str, Path] = {}
    for artifact in output_group_artifacts(group):
        if not include_optional and not artifact.required:
            continue
        paths[artifact.name] = resolve_output_path(
            artifact.key,
            kind=artifact.kind,
            cfg=cfg,
            create_parent=create_parent,
        )
    return paths


def output_group_namespace(
    group: str,
    *,
    cfg: SpatialVTKConfig | None = None,
    create_parent: bool = True,
    include_optional: bool = True,
) -> SimpleNamespace:
    """Resolve one output group as an attribute namespace."""

    return SimpleNamespace(**output_group_paths(group, cfg=cfg, create_parent=create_parent, include_optional=include_optional))


def output_status_rows(paths: dict[str, str | Path]) -> list[dict[str, object]]:
    """Return display-ready file status rows for named paths.

    Parameters
    ----------
    paths
        Mapping from names to paths.

    Returns
    -------
    list of dict
        Rows with ``name``, ``path``, ``exists``, ``size_gb``, and
        ``modified`` fields.
    """

    rows: list[dict[str, object]] = []
    for name, raw_path in paths.items():
        path = Path(raw_path)
        row: dict[str, object] = {
            "name": str(name),
            "path": str(path),
            "exists": path.exists(),
            "size_gb": None,
            "modified": None,
        }
        if path.exists():
            stat = path.stat()
            row["size_gb"] = round(stat.st_size / 1024**3, 3)
            row["modified"] = _format_mtime(stat.st_mtime)
        rows.append(row)
    return rows


def output_status_frame(paths):
    """Return file status for a path collection as a pandas dataframe.

    Parameters
    ----------
    paths
        Mapping from display names to paths, a sequence of paths, or a sequence
        of ``(name, path)`` pairs.

    Returns
    -------
    pandas.DataFrame
        Display-ready status table.
    """

    import pandas as pd

    return pd.DataFrame(output_status_rows(_coerce_named_paths(paths)))


def output_group_status(
    group: str,
    *,
    cfg: SpatialVTKConfig | None = None,
    create_parent: bool = True,
    include_optional: bool = True,
) -> list[dict[str, object]]:
    """Return status rows for one named output group."""

    return output_status_rows(
        output_group_paths(group, cfg=cfg, create_parent=create_parent, include_optional=include_optional)
    )


def output_group_status_frame(
    group: str,
    *,
    cfg: SpatialVTKConfig | None = None,
    create_parent: bool = True,
    include_optional: bool = True,
):
    """Return output-group status as a pandas dataframe.

    This helper imports pandas lazily so non-notebook callers can use the path
    helpers without importing pandas.
    """

    import pandas as pd

    return pd.DataFrame(
        output_group_status(
            group,
            cfg=cfg,
            create_parent=create_parent,
            include_optional=include_optional,
        )
    )


def required_outputs_exist(paths: dict[str, str | Path]) -> bool:
    """Return whether all named output paths exist."""

    return all(Path(path).exists() for path in paths.values())


def should_rebuild_outputs(
    paths: dict[str, str | Path],
    *,
    overwrite: bool = False,
    sources: Iterable[str | Path] = (),
) -> bool:
    """Return whether a workflow step should run for the target outputs.

    A step should run when overwrite is requested, one or more outputs are
    missing, or any existing source is newer than any output.
    """

    output_paths = [Path(path) for path in paths.values()]
    if bool(overwrite) or not all(path.exists() for path in output_paths):
        return True
    source_paths = [Path(path) for path in sources if Path(path).exists()]
    if not source_paths:
        return False
    return any(
        source.stat().st_mtime > output.stat().st_mtime
        for source in source_paths
        for output in output_paths
    )


def should_rebuild_paths(
    *paths: str | Path,
    overwrite: bool = False,
    sources: Iterable[str | Path] = (),
) -> bool:
    """Return whether unnamed output paths should be rebuilt."""

    return should_rebuild_outputs(
        {f"path_{index}": path for index, path in enumerate(paths)},
        overwrite=overwrite,
        sources=sources,
    )


def output_group_completion(
    group: str,
    *,
    cfg: SpatialVTKConfig | None = None,
    include_optional: bool = False,
) -> dict[str, object]:
    """Summarize completion for one output group."""

    artifacts = output_group_artifacts(group)
    rows = output_group_status(
        group,
        cfg=cfg,
        include_optional=include_optional,
    )
    required_names = {
        artifact.name
        for artifact in artifacts
        if artifact.required or include_optional
    }
    required_rows = [row for row in rows if row["name"] in required_names]
    existing = sum(1 for row in required_rows if row["exists"])
    total = len(required_rows)
    return {
        "group": str(group),
        "complete": existing == total,
        "existing": existing,
        "total": total,
        "missing": [row["name"] for row in required_rows if not row["exists"]],
    }


def _dedupe_artifacts(artifacts: Iterable[OutputArtifact]) -> list[OutputArtifact]:
    """Return artifacts with duplicate names removed while preserving order."""

    seen: set[str] = set()
    out: list[OutputArtifact] = []
    for artifact in artifacts:
        if artifact.name in seen:
            continue
        seen.add(artifact.name)
        out.append(artifact)
    return out


def _coerce_named_paths(paths) -> dict[str, str | Path]:
    """Coerce common path collections into a named mapping."""

    if isinstance(paths, dict):
        return {str(name): path for name, path in paths.items()}
    items = []
    for index, item in enumerate(paths):
        if isinstance(item, tuple) and len(item) == 2:
            items.append((str(item[0]), item[1]))
        else:
            items.append((f"path_{index}", item))
    return dict(items)


OUTPUT_GROUPS["large_run_core"] = tuple(
    _dedupe_artifacts(
        [
            *OUTPUT_GROUPS["step_01_ingest"],
            *OUTPUT_GROUPS["step_02_qc"],
            *OUTPUT_GROUPS["step_03_metrics"],
            *OUTPUT_GROUPS["step_04_spatial"],
            *OUTPUT_GROUPS["step_05_geojson"],
            *OUTPUT_GROUPS["step_07_dashboards"],
        ]
    )
)


def _format_mtime(timestamp: float) -> str:
    """Format a filesystem modification timestamp for notebook display."""

    import time

    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


__all__ = [
    "OUTPUT_GROUPS",
    "OutputArtifact",
    "OutputGroupName",
    "default_output_paths",
    "output_group_artifacts",
    "output_group_completion",
    "output_group_namespace",
    "output_group_paths",
    "output_group_status",
    "output_group_status_frame",
    "output_status_frame",
    "output_status_rows",
    "required_outputs_exist",
    "should_rebuild_paths",
    "should_rebuild_outputs",
]
