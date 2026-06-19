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

from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Literal, Sequence

from spatial_vtk.config.outputs import OutputKind, resolve_output_path
from spatial_vtk.config.runtime import SpatialVTKConfig
from spatial_vtk.io.artifacts import slugify


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


@dataclass(frozen=True)
class OutputGroup:
    """Resolved paths and status helpers for one workflow output group.

    Parameters
    ----------
    name
        Workflow group name, such as ``"step_03_metrics"``.
    paths
        Mapping from variable-style path names to resolved paths.

    Notes
    -----
    ``OutputGroup`` supports attribute access for existing notebook code
    (``outputs.metrics_long_path``), mapping-style access
    (``outputs["metrics_long_path"]``), and display helpers such as
    :meth:`status_frame` and :meth:`readiness`.
    """

    name: str
    paths: dict[str, Path]

    def __getattr__(self, name: str) -> Path:
        """Return one resolved path by attribute name."""

        try:
            return self.paths[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __getitem__(self, name: str) -> Path:
        """Return one resolved path by mapping key."""

        return self.paths[name]

    def __contains__(self, name: object) -> bool:
        """Return whether one path name is present."""

        return name in self.paths

    def keys(self):
        """Return path names in display order."""

        return self.paths.keys()

    def items(self):
        """Return ``(name, path)`` pairs in display order."""

        return self.paths.items()

    def values(self):
        """Return resolved paths in display order."""

        return self.paths.values()

    def as_dict(self) -> dict[str, Path]:
        """Return a shallow copy of the resolved path mapping."""

        return dict(self.paths)

    def bind(
        self,
        namespace: dict[str, object] | None = None,
        *,
        names: Iterable[str] | None = None,
    ) -> dict[str, Path]:
        """Bind resolved path names into a mutable namespace.

        Direct attribute access, such as ``step_outputs.metrics_long_path``, is
        preferred in new notebooks because it keeps path ownership visible. This
        helper remains available for older notebooks or compact interactive
        sessions that intentionally want conventional variables such as
        ``metrics_long_path`` in a mutable namespace. Pass ``names`` to bind
        only a subset.

        Parameters
        ----------
        namespace
            Mutable mapping to update, usually ``globals()`` in a notebook.
            When omitted, no external namespace is updated and the selected
            mapping is returned.
        names
            Optional path names to bind. Missing names raise ``KeyError`` so
            notebook setup cells fail close to the typo.

        Returns
        -------
        dict
            The selected path mapping.
        """

        selected = (
            self.as_dict()
            if names is None
            else {str(name): self.paths[str(name)] for name in names}
        )
        if namespace is not None:
            namespace.update(selected)
        return selected

    def load_tables(
        self,
        names: str | Iterable[str] | dict[str, str] | None = None,
        *,
        cfg: SpatialVTKConfig | None = None,
        missing: Literal["raise", "skip"] = "raise",
        **kwargs,
    ) -> dict[str, object]:
        """Load table artifacts from this output group.

        Parameters
        ----------
        names
            Artifact names, output keys, or a ``label -> artifact/key`` mapping.
            When omitted, every table artifact in the group is loaded. Mapping
            labels become the returned dictionary keys, which keeps notebook
            variables readable without repeating path-resolution code.
        cfg
            Optional config passed to :func:`spatial_vtk.io.load_output_table`.
        missing
            ``"raise"`` to fail on a missing table, or ``"skip"`` to omit
            missing tables.
        **kwargs
            Additional read options forwarded to ``load_output_table``.

        Returns
        -------
        dict
            Mapping from requested labels to loaded dataframes.
        """

        from spatial_vtk.io.tables import load_output_table

        _validate_missing_policy(missing)
        artifacts = _output_group_table_artifacts(self.name)
        selected = _selected_output_artifacts(artifacts, names)
        loaded: dict[str, object] = {}
        for label, artifact in selected:
            path = self.paths.get(artifact.name)
            if path is not None and not path.exists():
                if missing == "skip":
                    continue
            loaded[label] = load_output_table(artifact.key, cfg=cfg, **kwargs)
        return loaded

    def load_table(
        self,
        name: str,
        *,
        cfg: SpatialVTKConfig | None = None,
        missing: Literal["raise", "skip"] = "raise",
        **kwargs,
    ) -> object | None:
        """Load one table artifact from this output group.

        ``name`` can be either the output-group path name, such as
        ``"metrics_long_path"``, or the configured output key, such as
        ``"metrics_long"``. The helper keeps notebook cells focused when they
        need a single table instead of a ``label -> table`` mapping.
        """

        tables = self.load_tables(name, cfg=cfg, missing=missing, **kwargs)
        if not tables:
            return None
        return next(iter(tables.values()))

    def preview_tables(
        self,
        names: str | Iterable[str] | dict[str, str] | None = None,
        *,
        cfg: SpatialVTKConfig | None = None,
        nrows: int = 5,
        missing: Literal["raise", "skip"] = "skip",
        **kwargs,
    ) -> dict[str, object]:
        """Load bounded previews for table artifacts in this output group."""

        from spatial_vtk.io.tables import preview_output_table

        _validate_missing_policy(missing)
        artifacts = _output_group_table_artifacts(self.name)
        selected = _selected_output_artifacts(artifacts, names)
        previews: dict[str, object] = {}
        for label, artifact in selected:
            path = self.paths.get(artifact.name)
            if path is not None and not path.exists():
                if missing == "skip":
                    continue
            previews[label] = preview_output_table(artifact.key, cfg=cfg, nrows=nrows, **kwargs)
        return previews

    def preview_table(
        self,
        name: str,
        *,
        cfg: SpatialVTKConfig | None = None,
        nrows: int = 5,
        missing: Literal["raise", "skip"] = "skip",
        **kwargs,
    ) -> object | None:
        """Load a bounded preview for one table artifact in this output group."""

        previews = self.preview_tables(name, cfg=cfg, nrows=nrows, missing=missing, **kwargs)
        if not previews:
            return None
        return next(iter(previews.values()))

    def load_path_table(
        self,
        name: str,
        *,
        missing: Literal["raise", "skip"] = "raise",
        **kwargs,
    ) -> object | None:
        """Load a table from one resolved group path.

        Use this for output groups that own table paths outside the standard
        output registry, such as ``preprocessed_waveforms`` metadata files.
        Registry-backed workflow tables should continue to use
        :meth:`load_table` so reads go through configured output keys.
        """

        from spatial_vtk.io.tables import read_table

        _validate_missing_policy(missing)
        path = self._path_by_name(name)
        if not path.exists():
            if missing == "skip":
                return None
            raise FileNotFoundError(f"{name} is not ready yet: {path}")
        return read_table(path, **kwargs)

    def preview_path_table(
        self,
        name: str,
        *,
        nrows: int = 5,
        columns: Sequence[str] | None = None,
        missing: Literal["raise", "skip"] = "skip",
        **kwargs,
    ) -> object | None:
        """Load a bounded preview from one resolved group path.

        This mirrors :meth:`preview_table` for non-registry path groups. It
        keeps notebooks from calling ``read_table(...).head()`` for metadata
        tables that already have a named owner in the output group.
        """

        from spatial_vtk.io.tables import preview_table

        _validate_missing_policy(missing)
        path = self._path_by_name(name)
        if not path.exists():
            if missing == "skip":
                return None
            raise FileNotFoundError(f"{name} is not ready yet: {path}")
        return preview_table(path, nrows=nrows, columns=columns, **kwargs)

    def display_table_previews(
        self,
        names: str | Iterable[str] | dict[str, str] | None = None,
        *,
        cfg: SpatialVTKConfig | None = None,
        nrows: int = 5,
        missing: Literal["raise", "skip"] = "skip",
        display_fn: Callable[[Any], Any] | None = None,
        **kwargs,
    ) -> dict[str, object]:
        """Print paths and display bounded previews for group table artifacts.

        Parameters
        ----------
        names
            Artifact names, output keys, or a ``label -> artifact/key`` mapping.
            When omitted, every table artifact in the group is previewed.
        cfg
            Optional config passed to :func:`spatial_vtk.io.preview_output_table`.
        nrows
            Number of rows to preview from each existing table.
        missing
            ``"raise"`` to fail on a missing table, or ``"skip"`` to print a
            not-ready message and continue.
        display_fn
            Optional display function. When omitted, IPython's ``display`` is
            used when available, otherwise dataframes are printed as text.

        Returns
        -------
        dict
            Mapping from requested labels to preview dataframes for tables that
            were available.
        """

        from spatial_vtk.io.tables import preview_output_table

        _validate_missing_policy(missing)
        display = _notebook_display(display_fn)
        artifacts = _output_group_table_artifacts(self.name)
        selected = _selected_output_artifacts(artifacts, names)
        previews: dict[str, object] = {}
        for label, artifact in selected:
            path = self.paths.get(artifact.name)
            print(f"\n{label}: {path}")
            if path is not None and not path.exists():
                message = f"{label} is not ready yet."
                if missing == "raise":
                    raise FileNotFoundError(message)
                print(message)
                continue
            preview = preview_output_table(artifact.key, cfg=cfg, nrows=nrows, **kwargs)
            previews[label] = preview
            if display is not None:
                display(preview)
            elif hasattr(preview, "to_string"):
                print(preview.to_string(index=False))
            else:
                print(preview)
        return previews

    def display_path_table_previews(
        self,
        names: str | Iterable[str] | dict[str, str],
        *,
        nrows: int = 5,
        columns: Sequence[str] | None = None,
        missing: Literal["raise", "skip"] = "skip",
        display_fn: Callable[[Any], Any] | None = None,
        **kwargs,
    ) -> dict[str, object]:
        """Print paths and display bounded previews for resolved path tables.

        Use this for output groups that own table paths outside the configured
        output registry, such as preprocessed waveform metadata or compact
        path artifacts. Registry-backed workflow tables should continue to use
        :meth:`display_table_previews`.
        """

        from spatial_vtk.io.tables import preview_table

        _validate_missing_policy(missing)
        display = _notebook_display(display_fn)
        selected = _selected_path_names(self.paths, names)
        previews: dict[str, object] = {}
        for label, path in selected:
            print(f"\n{label}: {path}")
            if not path.exists():
                message = f"{label} is not ready yet."
                if missing == "raise":
                    raise FileNotFoundError(message)
                print(message)
                continue
            preview = preview_table(path, nrows=nrows, columns=columns, **kwargs)
            previews[label] = preview
            if display is not None:
                display(preview)
            elif hasattr(preview, "to_string"):
                print(preview.to_string(index=False))
            else:
                print(preview)
        return previews

    def first_existing_path(
        self,
        names: str | Iterable[str],
        *,
        default: str | Path | None = None,
    ) -> Path | None:
        """Return the first existing path from this group.

        Parameters
        ----------
        names
            Group path name or ordered group path names to check.
        default
            Optional fallback group path name or explicit path returned when no
            candidate exists. When omitted, ``None`` is returned.
        """

        candidates = (names,) if isinstance(names, str) else tuple(names)
        for name in candidates:
            path = self.paths[str(name)]
            if path.exists():
                return path
        if default is None:
            return None
        if isinstance(default, str) and default in self.paths:
            return self.paths[default]
        return Path(default)

    def figure_path(
        self,
        name: str,
        *,
        stem: str | None = None,
        stem_parts: Sequence[object] | None = None,
    ) -> Path:
        """Return a configured figure path, optionally with a variant stem.

        Parameters
        ----------
        name
            Figure artifact path name, such as ``"residual_grid_figure_path"``,
            or configured figure output key, such as ``"residual_grid"``.
        stem
            Optional exact replacement stem for the output filename.
        stem_parts
            Optional values slugified and joined with underscores to form the
            replacement stem. Use this for metric-specific figure variants that
            should live beside the configured base figure.

        Returns
        -------
        pathlib.Path
            Configured figure path or figure variant path.
        """

        if stem is not None and stem_parts is not None:
            raise ValueError("Pass either stem or stem_parts, not both.")
        artifact = self._artifact_by_name_or_key(name, kind="figure")
        base = self.paths.get(artifact.name)
        if base is None:
            raise KeyError(f"Figure artifact {name!r} is not resolved in output group {self.name!r}.")
        if stem is None and stem_parts is None:
            return base
        resolved_stem = str(stem) if stem is not None else "_".join(slugify(part) for part in (stem_parts or ()))
        resolved_stem = resolved_stem.strip()
        if not resolved_stem:
            raise ValueError("Figure stem cannot be empty.")
        return base.with_name(f"{resolved_stem}{base.suffix}")

    def preview_first_existing_table(
        self,
        names: str | Iterable[str],
        *,
        cfg: SpatialVTKConfig | None = None,
        nrows: int = 5,
        **kwargs,
    ) -> dict[str, object]:
        """Preview the first existing table from an ordered set of group paths.

        This is useful for notebooks that prefer a derived table when present
        but can fall back to an earlier table without repeating path checks.
        The returned dictionary has either one ``label -> preview`` entry or is
        empty when none of the candidate tables exists.
        """

        from spatial_vtk.io.tables import preview_output_table

        artifacts = _output_group_table_artifacts(self.name)
        candidates = _selected_output_artifacts(artifacts, names)
        for label, artifact in candidates:
            path = self.paths.get(artifact.name)
            if path is not None and path.exists():
                return {label: preview_output_table(artifact.key, cfg=cfg, nrows=nrows, **kwargs)}
        return {}

    def display_first_existing_table_preview(
        self,
        names: str | Iterable[str],
        *,
        cfg: SpatialVTKConfig | None = None,
        nrows: int = 5,
        display_fn: Callable[[Any], Any] | None = None,
        missing_message: str | None = None,
        **kwargs,
    ) -> dict[str, object]:
        """Print and display a bounded preview for the first available table.

        ``names`` follows :meth:`first_existing_path`: pass an ordered sequence
        of output-group path names such as ``("metrics_enriched_path",
        "metrics_long_path")``. The helper prints which candidate was selected
        and returns a one-entry ``label -> preview`` mapping, or an empty mapping
        when none of the candidates exists.
        """

        from spatial_vtk.io.tables import preview_output_table

        display = _notebook_display(display_fn)
        artifacts = _output_group_table_artifacts(self.name)
        candidates = _selected_output_artifacts(artifacts, names)
        for label, artifact in candidates:
            path = self.paths.get(artifact.name)
            if path is not None and path.exists():
                print(f"\nPreviewing {label}: {path}")
                preview = preview_output_table(artifact.key, cfg=cfg, nrows=nrows, **kwargs)
                if display is not None:
                    display(preview)
                elif hasattr(preview, "to_string"):
                    print(preview.to_string(index=False))
                else:
                    print(preview)
                return {label: preview}
        print(missing_message or "No candidate table is ready yet.")
        return {}

    def _path_by_name(self, name: str) -> Path:
        """Return a resolved group path by path-name with a clear error."""

        key = str(name)
        try:
            return self.paths[key]
        except KeyError as exc:
            choices = ", ".join(sorted(self.paths))
            raise KeyError(f"Unknown output-group path {key!r}. Choices: {choices}") from exc

    def _artifact_by_name_or_key(self, name: str, *, kind: OutputKind | None = None) -> OutputArtifact:
        """Return one group artifact by path-name or output key."""

        key = str(name)
        artifacts = output_group_artifacts(self.name)
        matches = [
            artifact
            for artifact in artifacts
            if artifact.name == key or artifact.key == key
        ]
        if kind is not None:
            matches = [artifact for artifact in matches if artifact.kind == kind]
        if matches:
            return matches[0]
        choices = sorted(
            {
                value
                for artifact in artifacts
                if kind is None or artifact.kind == kind
                for value in (artifact.name, artifact.key)
            }
        )
        label = f"{kind} artifact" if kind else "artifact"
        raise KeyError(f"Unknown output-group {label} {key!r}. Choices: {', '.join(choices)}")

    def status_frame(self, *, extra_paths=None):
        """Return a display-ready status frame for the group."""

        import pandas as pd

        rows = _output_group_status_rows_from_paths(self.name, self.paths)
        if extra_paths is not None:
            rows.extend(output_status_rows(_coerce_named_paths(extra_paths)))
        return pd.DataFrame(rows)

    def completion(self, *, include_optional: bool = False) -> dict[str, object]:
        """Return completion counts for this group's currently resolved paths."""

        artifacts = output_group_artifacts(self.name)
        required_names = {
            artifact.name
            for artifact in artifacts
            if artifact.required or include_optional
        }
        rows = output_status_rows(
            {
                name: path
                for name, path in self.paths.items()
                if include_optional or name in required_names
            }
        )
        existing = sum(1 for row in rows if row["exists"])
        total = len(rows)
        return {
            "group": self.name,
            "complete": existing == total,
            "existing": existing,
            "total": total,
            "missing": [row["name"] for row in rows if not row["exists"]],
        }

    def readiness(
        self,
        outputs: str | Iterable[str] | None = None,
        *,
        inputs=(),
        sources=(),
        overwrite: bool = False,
        missing_input_message: str | None = None,
        current_message: str | None = None,
        rebuild_message: str | None = None,
    ) -> "OutputReadiness":
        """Return a rebuild decision for selected group outputs.

        Parameters
        ----------
        outputs
            Optional path name or path names from this group. When omitted, all
            resolved group paths are considered outputs.
        inputs, sources
            Path collections passed through to :func:`output_readiness`.
            Strings that match path names in this group are resolved to those
            paths first, so notebooks can use
            ``inputs=("metrics_long_path",)`` instead of repeating local path
            variables.
        overwrite, missing_input_message, current_message, rebuild_message
            Passed through to :func:`output_readiness`.
        """

        if outputs is None:
            selected = self.paths
        elif isinstance(outputs, str):
            selected = {outputs: self.paths[outputs]}
        else:
            selected = {name: self.paths[name] for name in outputs}
        return output_readiness(
            selected,
            inputs=self._resolve_path_references(inputs),
            sources=self._resolve_path_references(sources),
            overwrite=overwrite,
            missing_input_message=missing_input_message,
            current_message=current_message,
            rebuild_message=rebuild_message,
        )

    def _resolve_path_references(self, paths):
        """Resolve path-name strings in an input/source path collection."""

        if paths is None:
            return None
        if _looks_like_path_value(paths):
            return self.paths.get(str(paths), paths)
        if isinstance(paths, dict):
            return {str(name): self._resolve_path_reference(path) for name, path in paths.items()}
        if isinstance(paths, SimpleNamespace) or (is_dataclass(paths) and not isinstance(paths, type)):
            return paths
        return [
            (str(item[0]), self._resolve_path_reference(item[1]))
            if isinstance(item, tuple) and len(item) == 2
            else self._resolve_path_reference(item)
            for item in paths
        ]

    def _resolve_path_reference(self, path):
        """Resolve one path-name string if it belongs to this group."""

        if isinstance(path, str) and path in self.paths:
            return self.paths[path]
        return path


@dataclass(frozen=True)
class OutputReadiness:
    """Decision record for one output-producing workflow step.

    Parameters
    ----------
    should_run
        Whether the step should run now.
    reason
        Stable reason code: ``"missing_inputs"``, ``"overwrite"``,
        ``"missing_outputs"``, ``"stale_sources"``, or ``"current"``.
    message
        Human-readable status message suitable for notebook output.
    outputs
        Target outputs checked by the decision.
    inputs
        Required input paths that must exist before the step can run.
    sources
        Dependency paths used for freshness checks.
    missing_inputs
        Required input paths that do not exist.
    unconfigured_inputs
        Required input names that are not configured.
    missing_outputs
        Target output paths that do not exist.
    stale_outputs
        Existing target outputs that are older than at least one existing
        source dependency.
    output_items, input_items, source_items
        Named path items used to build status tables for the decision.
    """

    should_run: bool
    reason: str
    message: str
    outputs: tuple[Path, ...]
    inputs: tuple[Path, ...] = ()
    sources: tuple[Path, ...] = ()
    missing_inputs: tuple[Path, ...] = ()
    unconfigured_inputs: tuple[str, ...] = ()
    missing_outputs: tuple[Path, ...] = ()
    stale_outputs: tuple[Path, ...] = ()
    output_items: tuple[tuple[str, Path], ...] = ()
    input_items: tuple[tuple[str, Path | None], ...] = ()
    source_items: tuple[tuple[str, Path | None], ...] = ()

    def status_rows(self) -> list[dict[str, object]]:
        """Return named input/output/source status rows for this decision."""

        rows: list[dict[str, object]] = []
        rows.extend(
            _readiness_status_rows(
                "output",
                self.output_items,
                missing=self.missing_outputs,
                stale=self.stale_outputs,
                reason=self.reason,
            )
        )
        rows.extend(
            _readiness_status_rows(
                "input",
                self.input_items,
                missing=self.missing_inputs,
                unconfigured=self.unconfigured_inputs,
                reason=self.reason,
            )
        )
        rows.extend(
            _readiness_status_rows(
                "source",
                self.source_items,
                reason=self.reason,
            )
        )
        return rows

    def status_frame(self):
        """Return named input/output/source status as a pandas dataframe."""

        import pandas as pd

        return pd.DataFrame(self.status_rows())


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
        OutputArtifact("availability_path", "qc_availability"),
        OutputArtifact("post_qc_records_path", "post_qc_records"),
        OutputArtifact("drop_causes_path", "qc_drop_causes"),
        OutputArtifact("drop_causes_overlap_path", "qc_drop_causes_overlap"),
        OutputArtifact("drop_causes_overlap_figure_path", "qc_drop_cause_diagnostics_overlap", kind="figure", required=False),
        OutputArtifact("event_trace_comparison_path", "event_trace_comparison", kind="figure", required=False),
    ),
    "step_03_metrics": (
        OutputArtifact("qc_inventory_overlap_path", "qc_inventory_overlap"),
        OutputArtifact("prepared_events_path", "prepared_events"),
        OutputArtifact("prepared_stations_path", "prepared_stations"),
        OutputArtifact("observed_inventory_path", "observed_metric_inventory"),
        OutputArtifact("synthetic_inventory_path", "synthetic_metric_inventory"),
        OutputArtifact("metric_tasks_path", "metric_tasks", required=False),
        OutputArtifact("metric_task_estimate_path", "metric_task_estimate", required=False),
        OutputArtifact("metric_manifest_path", "metric_manifest"),
        OutputArtifact("metric_manifest_cached_path", "metric_manifest_cached", required=False),
        OutputArtifact("metric_rows_path", "metric_rows"),
        OutputArtifact("metrics_long_path", "metrics_long"),
        OutputArtifact("metrics_enriched_path", "metrics_enriched"),
        OutputArtifact("path_table_path", "path_table"),
        OutputArtifact("path_summary_path", "path_summary"),
        OutputArtifact("residuals_vs_distance_figure_path", "residuals_vs_distance", kind="figure", required=False),
        OutputArtifact("score_trends_figure_path", "score_trends", kind="figure", required=False),
        OutputArtifact("station_metric_map_path", "station_metric_map", kind="figure", required=False),
        OutputArtifact("band_score_distribution_figure_path", "band_score_distribution", kind="figure", required=False),
    ),
    "step_04_spatial": (
        OutputArtifact("metrics_long_path", "metrics_long"),
        OutputArtifact("metric_field_path", "metric_field"),
        OutputArtifact("event_centered_path", "event_centered_residuals"),
        OutputArtifact("station_bias_path", "station_bias"),
        OutputArtifact("morans_i_path", "morans_i"),
        OutputArtifact("permutation_moran_path", "permutation_moran"),
        OutputArtifact("distance_corr_path", "distance_bin_correlations"),
        OutputArtifact("clusters_path", "clusters"),
        OutputArtifact("cluster_scores_path", "cluster_scores"),
        OutputArtifact("cluster_summary_path", "cluster_summary"),
        OutputArtifact("cluster_features_path", "cluster_feature_summary"),
        OutputArtifact("pca_scores_path", "pca_station_scores"),
        OutputArtifact("pca_loadings_path", "pca_feature_loadings"),
        OutputArtifact("pca_explained_path", "pca_explained_variance"),
        OutputArtifact("geology_path", "geology_contrasts"),
        OutputArtifact("station_bias_figure_path", "station_residual_map", kind="figure", required=False),
        OutputArtifact("residual_grid_figure_path", "residual_grid", kind="figure", required=False),
        OutputArtifact("spatial_correlation_distance_figure_path", "spatial_correlation_distance", kind="figure", required=False),
        OutputArtifact("pca_summary_figure_path", "pca_summary", kind="figure", required=False),
        OutputArtifact("geology_contrast_figure_path", "geology_contrast", kind="figure", required=False),
        OutputArtifact("path_summary_path", "path_summary", required=False),
        OutputArtifact("block_holdout_path", "block_holdout_predictions", required=False),
        OutputArtifact("corridors_path", "corridors", required=False),
        OutputArtifact("redcap_clusters_path", "redcap_clusters", required=False),
        OutputArtifact("pattern_similarity_path", "pattern_similarity_station_anomalies", required=False),
    ),
    "step_05_geojson": (
        OutputArtifact("geojson_summaries_path", "geojson_region_summaries"),
        OutputArtifact("corridors_path", "corridors"),
        OutputArtifact("geojson_polygons_map_path", "geojson_polygons_map", kind="figure", required=False),
        OutputArtifact("corridor_map_path", "corridor_map", kind="figure", required=False),
        OutputArtifact("region_boxplot_figure_path", "boxplot", kind="figure", required=False),
        OutputArtifact("station_metric_map_path", "station_metric_map", kind="figure", required=False),
        OutputArtifact("record_section_figure_path", "observed_synthetic_record_section", kind="figure", required=False),
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
        OutputArtifact("station_event_waveform_map_path", "station_event_waveform_map", kind="figure", required=False),
        OutputArtifact("pattern_similarity_figure_path", "pattern_similarity", kind="figure", required=False),
        OutputArtifact("scatterplot_figure_path", "scatterplot", kind="figure", required=False),
        OutputArtifact("boxplot_figure_path", "boxplot", kind="figure", required=False),
        OutputArtifact("heatmap_figure_path", "heatmap", kind="figure", required=False),
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
    """Resolve one output group as a legacy attribute namespace.

    This compatibility wrapper returns only resolved path attributes. New
    notebooks and workflow code should use :func:`output_group` so they also
    get readiness, completion, table-loading, preview, and figure-path helpers
    from the returned :class:`OutputGroup`.
    """

    return SimpleNamespace(**output_group_paths(group, cfg=cfg, create_parent=create_parent, include_optional=include_optional))


def output_group(
    group: str,
    *,
    cfg: SpatialVTKConfig | None = None,
    create_parent: bool = True,
    include_optional: bool = True,
) -> OutputGroup:
    """Resolve one workflow output group with path and status helpers."""

    normalized = str(group).strip().lower().replace("-", "_").replace(" ", "_")
    return OutputGroup(
        name=normalized,
        paths=output_group_paths(
            normalized,
            cfg=cfg,
            create_parent=create_parent,
            include_optional=include_optional,
        ),
    )


def _output_group_table_artifacts(group: str) -> tuple[OutputArtifact, ...]:
    """Return only table artifacts for one output group."""

    return tuple(artifact for artifact in output_group_artifacts(group) if artifact.kind == "table")


def _selected_output_artifacts(
    artifacts: tuple[OutputArtifact, ...],
    names: str | Iterable[str] | dict[str, str] | None,
) -> list[tuple[str, OutputArtifact]]:
    """Resolve artifact names or output keys to display labels and artifacts."""

    by_name = {artifact.name: artifact for artifact in artifacts}
    by_key = {artifact.key: artifact for artifact in artifacts}

    if names is None:
        return [(artifact.key, artifact) for artifact in artifacts]

    if isinstance(names, str):
        raw_items = ((None, names),)
    else:
        raw_items = names.items() if isinstance(names, dict) else ((None, name) for name in names)
    selected: list[tuple[str, OutputArtifact]] = []
    for raw_label, raw_name in raw_items:
        name = str(raw_name)
        artifact = by_name.get(name) or by_key.get(name)
        if artifact is None:
            choices = sorted({*by_name.keys(), *by_key.keys()})
            raise KeyError(f"Unknown table artifact {name!r}. Choices: {', '.join(choices)}")
        label = str(raw_label) if raw_label is not None else artifact.key
        selected.append((label, artifact))
    return selected


def _selected_path_names(
    paths: dict[str, Path],
    names: str | Iterable[str] | dict[str, str],
) -> list[tuple[str, Path]]:
    """Resolve output-group path names to display labels and paths."""

    if isinstance(names, str):
        raw_items = ((None, names),)
    elif isinstance(names, dict):
        raw_items = names.items()
    else:
        raw_items = ((None, name) for name in names)
    selected: list[tuple[str, Path]] = []
    for raw_label, raw_name in raw_items:
        name = str(raw_name)
        try:
            path = paths[name]
        except KeyError as exc:
            choices = ", ".join(sorted(paths))
            raise KeyError(f"Unknown output-group path {name!r}. Choices: {choices}") from exc
        label = str(raw_label) if raw_label is not None else name
        selected.append((label, path))
    return selected


def _validate_missing_policy(missing: str) -> None:
    """Validate a missing-table policy."""

    if missing not in {"raise", "skip"}:
        raise ValueError("missing must be 'raise' or 'skip'.")


UNCONFIGURED_PATH_LABEL = "<not configured>"


def _output_group_status_rows_from_paths(group: str, paths: dict[str, Path]) -> list[dict[str, object]]:
    """Return status rows for resolved output-group paths with artifact metadata."""

    artifacts = tuple(artifact for artifact in output_group_artifacts(group) if artifact.name in paths)
    return _output_group_status_rows_from_artifacts(artifacts, paths)


def _output_group_status_rows_from_artifacts(
    artifacts: Sequence[OutputArtifact],
    paths: dict[str, Path],
) -> list[dict[str, object]]:
    """Return display status rows annotated with output registry metadata."""

    status_paths = {
        artifact.name: paths[artifact.name]
        for artifact in artifacts
    }
    rows_by_name = {
        str(row["name"]): row
        for row in output_status_rows(status_paths)
    }
    rows: list[dict[str, object]] = []
    for artifact in artifacts:
        row = dict(rows_by_name[artifact.name])
        row["output_key"] = artifact.key
        row["kind"] = artifact.kind
        row["required"] = artifact.required
        rows.append(row)
    return rows


def output_status_rows(paths: dict[str, str | Path | None]) -> list[dict[str, object]]:
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
        if raw_path is None:
            rows.append(
                {
                    "name": str(name),
                    "path": UNCONFIGURED_PATH_LABEL,
                    "exists": False,
                    "size_gb": None,
                    "modified": None,
                }
            )
            continue
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
        Mapping from display names to paths, a namespace/dataclass with path
        attributes, a sequence of paths, or a sequence of ``(name, path)``
        pairs. Bare path sequences are labeled by path stem instead of opaque
        index names.

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
    extra_paths=None,
) -> list[dict[str, object]]:
    """Return status rows for one named output group.

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
    extra_paths
        Optional additional named paths to append to the status table. This is
        useful for step-specific inputs that are not registered workflow
        outputs, such as preprocessing metadata files.

    Returns
    -------
    list of dict
        Display-ready status rows.
    """

    artifacts = output_group_artifacts(group)
    if not include_optional:
        artifacts = tuple(artifact for artifact in artifacts if artifact.required)
    paths = {
        artifact.name: resolve_output_path(
            artifact.key,
            kind=artifact.kind,
            cfg=cfg,
            create_parent=create_parent,
        )
        for artifact in artifacts
    }
    rows = _output_group_status_rows_from_artifacts(artifacts, paths)
    if extra_paths is not None:
        rows.extend(output_status_rows(_coerce_named_paths(extra_paths)))
    return rows


def output_group_status_frame(
    group: str,
    *,
    cfg: SpatialVTKConfig | None = None,
    create_parent: bool = True,
    include_optional: bool = True,
    extra_paths=None,
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
            extra_paths=extra_paths,
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


def output_readiness(
    outputs,
    *,
    inputs=(),
    sources: Iterable[str | Path] = (),
    overwrite: bool = False,
    missing_input_message: str | None = None,
    current_message: str | None = None,
    rebuild_message: str | None = None,
) -> OutputReadiness:
    """Return a notebook-friendly rebuild decision for target outputs.

    This is a small structured wrapper around :func:`should_rebuild_paths`.
    It centralizes the common notebook pattern of checking required inputs,
    deciding whether outputs are missing or stale, and printing a clear
    skip/run message.

    Parameters
    ----------
    outputs
        Target output path, iterable of output paths, or mapping whose values
        are output paths.
    inputs
        Required input path, iterable of input paths, or mapping whose values
        are input paths. Missing inputs block the step.
    sources
        Existing dependency paths used for freshness checks. Missing sources
        are ignored here; pass required dependencies through ``inputs``.
    overwrite
        Whether to force the step to run.
    missing_input_message, current_message, rebuild_message
        Optional message overrides for notebook display.

    Returns
    -------
    OutputReadiness
        Structured decision with a stable reason and display message.
    """

    output_items = _coerce_named_path_mapping(outputs)
    input_items = _coerce_named_optional_path_mapping(inputs)
    source_items = _coerce_named_optional_path_mapping(sources)
    output_paths = tuple(output_items.values())
    input_paths = tuple(path for path in input_items.values() if path is not None)
    source_paths = tuple(path for path in source_items.values() if path is not None)
    named_outputs = tuple(output_items.items())
    named_inputs = tuple(input_items.items())
    named_sources = tuple(source_items.items())

    unconfigured_inputs = tuple(name for name, path in input_items.items() if path is None)
    missing_inputs = tuple(path for path in input_paths if not path.exists())
    missing_outputs = tuple(path for path in output_paths if not path.exists())
    existing_sources = tuple(path for path in source_paths if path.exists())
    stale_outputs = tuple(
        output
        for output in output_paths
        if output.exists() and any(source.stat().st_mtime > output.stat().st_mtime for source in existing_sources)
    )

    if unconfigured_inputs or missing_inputs:
        message = missing_input_message or _paths_message(
            "Required input is not ready yet",
            _filter_named_optional_paths(input_items, missing_inputs, unconfigured_inputs),
        )
        return OutputReadiness(
            should_run=False,
            reason="missing_inputs",
            message=message,
            outputs=output_paths,
            inputs=input_paths,
            sources=source_paths,
            missing_inputs=missing_inputs,
            unconfigured_inputs=unconfigured_inputs,
            missing_outputs=missing_outputs,
            stale_outputs=stale_outputs,
            output_items=named_outputs,
            input_items=named_inputs,
            source_items=named_sources,
        )

    if overwrite:
        message = rebuild_message or _paths_message("Overwrite requested; rebuilding", output_items)
        return OutputReadiness(
            should_run=True,
            reason="overwrite",
            message=message,
            outputs=output_paths,
            inputs=input_paths,
            sources=source_paths,
            unconfigured_inputs=unconfigured_inputs,
            missing_outputs=missing_outputs,
            stale_outputs=stale_outputs,
            output_items=named_outputs,
            input_items=named_inputs,
            source_items=named_sources,
        )

    if missing_outputs:
        message = rebuild_message or _paths_message(
            "Output is missing; building",
            _filter_named_paths(output_items, missing_outputs),
        )
        return OutputReadiness(
            should_run=True,
            reason="missing_outputs",
            message=message,
            outputs=output_paths,
            inputs=input_paths,
            sources=source_paths,
            unconfigured_inputs=unconfigured_inputs,
            missing_outputs=missing_outputs,
            stale_outputs=stale_outputs,
            output_items=named_outputs,
            input_items=named_inputs,
            source_items=named_sources,
        )

    if stale_outputs:
        message = rebuild_message or _paths_message(
            "Source dependency changed; rebuilding",
            _filter_named_paths(output_items, stale_outputs),
        )
        return OutputReadiness(
            should_run=True,
            reason="stale_sources",
            message=message,
            outputs=output_paths,
            inputs=input_paths,
            sources=source_paths,
            unconfigured_inputs=unconfigured_inputs,
            stale_outputs=stale_outputs,
            output_items=named_outputs,
            input_items=named_inputs,
            source_items=named_sources,
        )

    message = current_message or _paths_message("Outputs are current; skipping", output_items)
    return OutputReadiness(
        should_run=False,
        reason="current",
        message=message,
        outputs=output_paths,
        inputs=input_paths,
        sources=source_paths,
        unconfigured_inputs=unconfigured_inputs,
        output_items=named_outputs,
        input_items=named_inputs,
        source_items=named_sources,
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

    if paths is None:
        return {}
    if _looks_like_path_value(paths):
        return {_path_display_name(paths, fallback="path"): paths}
    if isinstance(paths, dict):
        return {str(name): path for name, path in paths.items()}
    if isinstance(paths, SimpleNamespace):
        return {
            str(name): path
            for name, path in vars(paths).items()
            if _looks_like_path_value(path)
        }
    if is_dataclass(paths) and not isinstance(paths, type):
        return {
            field.name: value
            for field in fields(paths)
            if _looks_like_path_value(value := getattr(paths, field.name))
        }
    items = []
    for index, item in enumerate(paths):
        if isinstance(item, tuple) and len(item) == 2:
            items.append((str(item[0]), item[1]))
        else:
            items.append((_path_display_name(item, fallback=f"path_{index}"), item))
    return dict(items)


def _looks_like_path_value(value: object) -> bool:
    """Return whether a value is a path-like object for status displays."""

    return isinstance(value, (str, Path))


def _path_display_name(path: object, *, fallback: str) -> str:
    """Return a readable display name for one path-like object."""

    if not _looks_like_path_value(path):
        return fallback
    candidate = Path(path)
    stem = candidate.stem if candidate.suffix else candidate.name
    name = stem.strip().replace("-", "_").replace(" ", "_")
    return name or fallback


def _coerce_path_tuple(paths) -> tuple[Path, ...]:
    """Coerce a path, mapping, or sequence into a tuple of paths."""

    return tuple(_coerce_named_path_mapping(paths).values())


def _coerce_named_path_mapping(paths) -> dict[str, Path]:
    """Coerce path inputs to a named mapping with resolved ``Path`` values."""

    return {
        name: Path(path)
        for name, path in _coerce_named_paths(paths).items()
        if path is not None
    }


def _coerce_named_optional_path_mapping(paths) -> dict[str, Path | None]:
    """Coerce path inputs to a named mapping while preserving unconfigured values."""

    return {
        name: None if path is None else Path(path)
        for name, path in _coerce_named_paths(paths).items()
    }


def _filter_named_paths(paths: dict[str, Path], selected: tuple[Path, ...]) -> dict[str, Path]:
    """Return named paths whose value is in ``selected``."""

    selected_set = set(selected)
    return {name: path for name, path in paths.items() if path in selected_set}


def _filter_named_optional_paths(
    paths: dict[str, Path | None],
    selected: tuple[Path, ...],
    unconfigured: tuple[str, ...],
) -> dict[str, Path | None]:
    """Return selected named paths, including paths not configured in the active config."""

    selected_set = set(selected)
    unconfigured_set = set(unconfigured)
    return {
        name: path
        for name, path in paths.items()
        if name in unconfigured_set or path in selected_set
    }


def _readiness_status_rows(
    role: str,
    items: tuple[tuple[str, Path | None], ...],
    *,
    missing: tuple[Path, ...] = (),
    stale: tuple[Path, ...] = (),
    unconfigured: tuple[str, ...] = (),
    reason: str,
) -> list[dict[str, object]]:
    """Return display rows for one role in an output-readiness decision."""

    rows: list[dict[str, object]] = []
    missing_paths = set(missing)
    stale_paths = set(stale)
    unconfigured_names = set(unconfigured)
    for name, path in items:
        row = output_status_rows({name: path})[0]
        row["role"] = role
        row["reason"] = reason
        if role == "output":
            if path is None:
                state = "unconfigured"
            elif path in missing_paths:
                state = "missing"
            elif path in stale_paths:
                state = "stale"
            elif reason == "overwrite":
                state = "overwrite"
            else:
                state = "current"
        elif role == "input":
            if path is None or name in unconfigured_names:
                state = "unconfigured"
            elif path in missing_paths:
                state = "missing"
            else:
                state = "ready"
        elif role == "source":
            if path is None:
                state = "unconfigured_ignored"
            else:
                state = "ready" if path.exists() else "missing_ignored"
        else:
            state = "unknown"
        row["state"] = state
        rows.append(row)
    return rows


def _paths_message(prefix: str, paths: tuple[Path, ...] | dict[str, Path | None]) -> str:
    """Return a compact status message that includes affected paths."""

    if not paths:
        return f"{prefix}."
    if isinstance(paths, dict):
        items = list(paths.items())
        value = UNCONFIGURED_PATH_LABEL if items[0][1] is None else items[0][1]
        first = f"{items[0][0]}={value}"
    else:
        items = [(None, path) for path in paths]
        first = str(items[0][1])
    if len(items) == 1:
        return f"{prefix}: {first}"
    return f"{prefix}: {len(items)} path(s); first is {first}"


def _notebook_display(display_fn: Callable[[Any], Any] | None = None) -> Callable[[Any], Any] | None:
    """Return a notebook display function when one is available."""

    if display_fn is not None:
        return display_fn
    try:
        from IPython.display import display  # type: ignore

        return display
    except Exception:
        return None


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
    "OutputGroup",
    "OutputGroupName",
    "OutputReadiness",
    "default_output_paths",
    "output_group",
    "output_group_artifacts",
    "output_group_completion",
    "output_group_namespace",
    "output_group_paths",
    "output_group_status",
    "output_group_status_frame",
    "output_readiness",
    "output_status_frame",
    "output_status_rows",
    "required_outputs_exist",
    "should_rebuild_paths",
    "should_rebuild_outputs",
]
