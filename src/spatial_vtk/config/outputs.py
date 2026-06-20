"""Default output registry and path resolution helpers.

Purpose
-------
This module resolves standard table and figure output paths from three places:
explicit function arguments, the active Spatial-VTK config, and package default
filenames stored in ``default_outputs.yaml``.

Usage examples
--------------
Resolve workflow outputs from the active config:
  ``from spatial_vtk.io import output_group``
  ``step_outputs = output_group("step_01_ingest")``
  ``path = step_outputs.record_coverage_figure``

Use ``resolve_output_path()`` directly for scripts or single-artifact helpers
that need one registered artifact path without the readiness and preview
methods attached to an output group.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
import inspect
from pathlib import Path
from typing import Any, Iterable, Literal

import yaml

from spatial_vtk.config.runtime import SpatialVTKConfig, active_config

OutputKind = Literal["table", "figure", "dashboard"]


@dataclass(frozen=True)
class OutputSpec:
    """One registered Spatial-VTK output artifact."""

    key: str
    kind: OutputKind
    filename: str
    description: str = ""


def default_output_registry() -> dict[str, dict[str, OutputSpec]]:
    """Load the package-wide default output registry.

    Parameters
    ----------
    None
        The registry is loaded from ``spatial_vtk.config.default_outputs.yaml``.

    Returns
    -------
    dict
        Registry grouped by ``tables`` and ``figures``.
    """

    text = resources.files("spatial_vtk.config").joinpath("default_outputs.yaml").read_text(encoding="utf-8")
    payload = yaml.safe_load(text) or {}
    registry: dict[str, dict[str, OutputSpec]] = {"tables": {}, "figures": {}, "dashboards": {}}
    for group_name, kind in (("tables", "table"), ("figures", "figure"), ("dashboards", "dashboard")):
        for key, value in dict(payload.get(group_name) or {}).items():
            item = dict(value or {})
            registry[group_name][str(key)] = OutputSpec(
                key=str(key),
                kind=kind,  # type: ignore[arg-type]
                filename=str(item.get("filename") or _fallback_filename(str(key), kind)),  # type: ignore[arg-type]
                description=str(item.get("description") or ""),
            )
    return registry


def configured_output_registry_frame(
    *,
    cfg: SpatialVTKConfig | str | Path | None = None,
    include_paths: bool = True,
    kinds: Iterable[OutputKind] | None = None,
    create_parent: bool = False,
):
    """Return registered output artifacts as a notebook-friendly dataframe.

    Parameters
    ----------
    cfg
        Optional config object or config file path used to resolve artifact
        paths. When omitted and ``include_paths`` is true, the
        active/discoverable config is used.
    include_paths
        Whether to include resolved path columns. ``resolved_path`` is the
        clear notebook-facing column; ``path`` is preserved as a compatibility
        alias for existing code.
    kinds
        Optional artifact kinds to include. When omitted, all registered tables,
        figures, and dashboard roots are returned.
    create_parent
        Whether path resolution should create parent directories.

    Returns
    -------
    pandas.DataFrame
        Columns include ``kind``, ``key``, ``artifact_label``, ``filename``,
        ``description``, and optionally ``resolved_path`` plus compatibility
        alias ``path``.
    """

    import pandas as pd

    requested = None if kinds is None else {str(kind).strip().lower() for kind in kinds}
    rows: list[dict[str, object]] = []
    registry = default_output_registry()
    for group_name, group_kind in (("tables", "table"), ("figures", "figure"), ("dashboards", "dashboard")):
        if requested is not None and group_kind not in requested:
            continue
        for spec in registry.get(group_name, {}).values():
            row: dict[str, object] = {
                "kind": spec.kind,
                "key": spec.key,
                "artifact_label": _artifact_label(spec),
                "filename": spec.filename,
                "description": spec.description,
            }
            if include_paths:
                resolved = str(
                    resolve_output_path(
                        spec.key,
                        kind=spec.kind,
                        cfg=cfg,
                        create_parent=create_parent,
                    )
                )
                row["resolved_path"] = resolved
                row["path"] = resolved
            rows.append(row)
    columns = (
        ["kind", "key", "artifact_label", "filename", "description", "resolved_path", "path"]
        if include_paths
        else ["kind", "key", "artifact_label", "filename", "description"]
    )
    return pd.DataFrame(rows, columns=columns)


def configured_output_registry_preview_frame(
    *,
    cfg: SpatialVTKConfig | str | Path | None = None,
    include_paths: bool = True,
    kinds: Iterable[OutputKind] | None = None,
    create_parent: bool = False,
    nrows: int = 10,
):
    """Return a bounded preview of registered output artifacts.

    This is a notebook-facing wrapper around
    :func:`configured_output_registry_frame` for examples that only need to show
    a few configured outputs without teaching direct dataframe slicing.
    """

    frame = configured_output_registry_frame(
        cfg=cfg,
        include_paths=include_paths,
        kinds=kinds,
        create_parent=create_parent,
    )
    return frame.head(max(int(nrows), 0)).reset_index(drop=True)


def output_spec(key: str, *, kind: OutputKind | None = None) -> OutputSpec:
    """Return one output spec, falling back to a generated filename.

    Parameters
    ----------
    key
        Artifact key such as ``"record_coverage"``.
    kind
        Artifact kind. When omitted, the registry is searched.

    Returns
    -------
    OutputSpec
        Registered or generated output spec.
    """

    clean_key = _clean_key(key)
    registry = default_output_registry()
    groups = [_group_name(kind)] if kind is not None else ("figures", "tables", "dashboards")
    for group in groups:
        spec = registry.get(group, {}).get(clean_key)
        if spec is not None:
            return spec
    resolved_kind = kind or "table"
    return OutputSpec(clean_key, resolved_kind, _fallback_filename(clean_key, resolved_kind))


def infer_output_key(function_name: str | None = None) -> str:
    """Infer an artifact key from a plotting or helper function name.

    Parameters
    ----------
    function_name
        Optional function name. When omitted, the caller stack is inspected.

    Returns
    -------
    str
        Normalized output key with prefixes such as ``plot_`` removed.
    """

    name = function_name
    if name is None:
        for frame in inspect.stack()[2:8]:
            candidate = frame.function
            if candidate.startswith(("plot_", "build_", "write_")):
                name = candidate
                break
    token = str(name or "output")
    for prefix in ("plot_", "build_", "write_"):
        if token.startswith(prefix):
            token = token[len(prefix) :]
            break
    for suffix in ("_figure", "_fig", "_table", "_output"):
        if token.endswith(suffix):
            token = token[: -len(suffix)]
    return _clean_key(token)


def resolve_output_path(
    key: str | None = None,
    *,
    kind: OutputKind | None = None,
    outpath: str | Path | None = None,
    cfg: SpatialVTKConfig | str | Path | None = None,
    create_parent: bool = False,
) -> Path:
    """Resolve an output path using explicit args, config, and defaults.

    Parameters
    ----------
    key
        Artifact key. When omitted, a key is inferred from the caller function.
    kind
        Output kind: ``"figure"``, ``"table"``, or ``"dashboard"``.
    outpath
        Explicit output path. This always wins.
    cfg
        Optional config object or config file path. When omitted, the
        active/discoverable config is used.
    create_parent
        Whether to create the resolved path parent directory.

    Returns
    -------
    pathlib.Path
        Resolved output path.
    """

    config = _coerce_output_config(cfg)
    if outpath is not None:
        path = config.path_from_value(outpath, create_parent=create_parent)
        if path is None:
            raise ValueError("outpath resolved to None.")
        return path
    output_key = _clean_key(key or infer_output_key())
    spec = output_spec(output_key, kind=kind)
    override = _artifact_override(config, output_key)
    override_path = override.get("path") if isinstance(override, dict) else None
    if override_path:
        path = config.path_from_value(override_path, create_parent=create_parent)
        if path is None:
            raise ValueError(f"outputs.artifacts.{output_key}.path resolved to None.")
        return path
    filename = str(override.get("filename") if isinstance(override, dict) and override.get("filename") else spec.filename)
    directory = _output_directory(config, spec.kind, create_parent=create_parent)
    path = directory / filename
    if create_parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _coerce_output_config(cfg: SpatialVTKConfig | str | Path | None) -> SpatialVTKConfig:
    """Return a config object for output path resolution."""

    if cfg is None:
        return active_config()
    if isinstance(cfg, SpatialVTKConfig):
        return cfg
    return SpatialVTKConfig.from_file(cfg)


def output_description(key: str, *, kind: OutputKind | None = None) -> str:
    """Return the registered description for one output key."""

    return output_spec(key, kind=kind).description


def _artifact_override(config: SpatialVTKConfig, key: str) -> dict[str, Any]:
    """Return per-artifact config overrides."""

    value = config.section(f"outputs.artifacts.{key}", {}) or {}
    return dict(value) if isinstance(value, dict) else {}


def _output_directory(config: SpatialVTKConfig, kind: OutputKind, *, create_parent: bool = False) -> Path:
    """Resolve the base output directory for one kind."""

    section_key = {"figure": "outputs.figures", "table": "outputs.tables", "dashboard": "outputs.dashboards"}[kind]
    directory = config.path(section_key)
    if directory is None:
        root = config.path("outputs.root") or (config.root_dir / "outputs")
        subdir = {"figure": "figures", "table": "tables", "dashboard": "dashboards"}[kind]
        directory = root / subdir
    if create_parent:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


def _group_name(kind: OutputKind | None) -> str:
    """Return the registry group name for one kind."""

    if kind == "figure":
        return "figures"
    if kind == "dashboard":
        return "dashboards"
    return "tables"


def _fallback_filename(key: str, kind: OutputKind) -> str:
    """Generate a default filename when a key is not registered."""

    suffix = ".png" if kind == "figure" else ".parquet" if kind == "dashboard" else ".csv"
    return f"{_clean_key(key)}{suffix}"


def _artifact_label(spec: OutputSpec) -> str:
    """Return a compact human-facing label for one registered artifact."""

    text = spec.key.replace("_", " ").strip()
    suffix = "figure" if spec.kind == "figure" else "dashboard directory" if spec.kind == "dashboard" else "table"
    return text if text.endswith(suffix) else f"{text} {suffix}"


def _clean_key(key: str) -> str:
    """Normalize one artifact key."""

    return str(key).strip().replace("-", "_").replace(" ", "_").lower()


__all__ = [
    "OutputKind",
    "OutputSpec",
    "configured_output_registry_frame",
    "configured_output_registry_preview_frame",
    "default_output_registry",
    "infer_output_key",
    "output_description",
    "output_spec",
    "resolve_output_path",
]
