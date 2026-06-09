"""Public runtime configuration loading and path resolution.

Purpose
-------
This module gives Spatial-VTK one generic configuration surface for user
projects. Config files are explicit YAML/JSON files; they define paths,
run-defaults, named bounds, and workflow settings without relying on private
repository defaults.

Usage examples
--------------
Load a user config and resolve a configured path:
  ``cfg = SpatialVTKConfig.from_file("spatial-vtk.yaml")``
  ``metrics_dir = cfg.path("outputs.metrics", create_parent=True)``
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping
import json
import os
import re

import yaml

from spatial_vtk.config.bounds import load_bounds_presets
from spatial_vtk.config.paths import ROOT_DIR


SVTK_CONFIG_ENV = "SVTK_CONFIG_FILE"
DEFAULT_CONFIG_FILENAMES = (
    "spatial-vtk.yaml",
    "spatial-vtk.yml",
    "svtk_config.yaml",
    "svtk_config.yml",
    "svtk.yaml",
    "svtk.yml",
)

_ACTIVE_CONFIG: "SpatialVTKConfig | None" = None


def active_config() -> "SpatialVTKConfig":
    """Return the active Spatial-VTK config or discover one.

    Parameters
    ----------
    None
        This function reads the in-process active config, the
        ``SVTK_CONFIG_FILE`` environment variable, or a standard config file
        in the current directory tree.

    Returns
    -------
    SpatialVTKConfig
        Active or discovered config object.
    """

    if _ACTIVE_CONFIG is not None:
        return _ACTIVE_CONFIG
    return SpatialVTKConfig.from_file()


def clear_active_config() -> None:
    """Clear the in-process active Spatial-VTK config."""

    global _ACTIVE_CONFIG
    _ACTIVE_CONFIG = None


def find_config_file(explicit_path: str | Path | None = None, *, start_dir: str | Path | None = None) -> Path | None:
    """Find the active Spatial-VTK configuration file.

    Parameters
    ----------
    explicit_path
        Direct config path. This has highest precedence.
    start_dir
        Directory to search for standard config filenames. Defaults to the
        current working directory.

    Returns
    -------
    pathlib.Path or None
        Resolved config path, or ``None`` when no config file is available.
    """

    if explicit_path is not None:
        return Path(explicit_path).expanduser().resolve()
    env_value = os.environ.get(SVTK_CONFIG_ENV)
    if env_value:
        return Path(env_value).expanduser().resolve()
    base = Path(start_dir or Path.cwd()).expanduser().resolve()
    for directory in (base, *base.parents):
        for name in DEFAULT_CONFIG_FILENAMES:
            candidate = directory / name
            if candidate.exists():
                return candidate.resolve()
    return None


def load_config(config_path: str | Path | None = None, *, start_dir: str | Path | None = None) -> dict[str, Any]:
    """Load one public Spatial-VTK config file.

    Parameters
    ----------
    config_path
        Optional explicit config path.
    start_dir
        Optional search directory used when ``config_path`` is omitted.

    Returns
    -------
    dict
        Parsed config dictionary, or an empty dictionary when no config file is
        found.
    """

    path = find_config_file(config_path, start_dir=start_dir)
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Spatial-VTK config file does not exist: {path}")
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        payload = json.loads(text)
    elif suffix in {".yaml", ".yml", ""}:
        payload = yaml.safe_load(text) or {}
    else:
        raise ValueError(f"Unsupported Spatial-VTK config file extension: {path.suffix}")
    if not isinstance(payload, dict):
        raise ValueError("Spatial-VTK config must parse to a mapping/dictionary.")
    return dict(payload)


def deep_merge(base: Mapping[str, Any] | None, updates: Mapping[str, Any] | None) -> dict[str, Any]:
    """Recursively merge two dictionaries.

    Parameters
    ----------
    base
        Base mapping.
    updates
        Values that should override ``base``.

    Returns
    -------
    dict
        Merged dictionary.
    """

    merged = dict(base or {})
    for key, value in dict(updates or {}).items():
        if isinstance(merged.get(key), dict) and isinstance(value, Mapping):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def get_dotted(mapping: Mapping[str, Any], dotted_key: str | None, default: Any = None) -> Any:
    """Read one dotted key from a nested mapping.

    Parameters
    ----------
    mapping
        Source mapping.
    dotted_key
        Key such as ``"outputs.metrics"``.
    default
        Returned when any key part is missing.

    Returns
    -------
    object
        Found value or ``default``.
    """

    if not dotted_key:
        return mapping
    current: Any = mapping
    for part in str(dotted_key).split("."):
        if not isinstance(current, Mapping) or part not in current:
            return default
        current = current[part]
    return current


def resolve_path(
    value: str | Path | None,
    *,
    base_dir: str | Path | None = None,
    root_dir: str | Path | None = None,
    must_exist: bool = False,
    create_parent: bool = False,
) -> Path | None:
    """Resolve a user-configured path or path template.

    Parameters
    ----------
    value
        Raw path string. ``None`` and empty strings return ``None``.
    base_dir
        Directory used for relative paths and ``{config_dir}`` formatting.
    root_dir
        Project root used for ``{root_dir}`` formatting.
    must_exist
        Raise ``FileNotFoundError`` when the resolved path does not exist.
    create_parent
        Create the path's parent directory.

    Returns
    -------
    pathlib.Path or None
        Resolved path.
    """

    if value in (None, ""):
        return None
    base = Path(base_dir or Path.cwd()).expanduser().resolve()
    root = Path(root_dir or base).expanduser().resolve()
    rendered = str(value).format_map(_SafePathFormat(root_dir=str(root), config_dir=str(base)))
    path = Path(rendered).expanduser()
    if not path.is_absolute():
        path = (base / path).resolve()
    if must_exist and not path.exists():
        raise FileNotFoundError(f"Configured path does not exist: {path}")
    if create_parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def format_template(template: str, *, root_dir: str | Path, config_dir: str | Path, **values: object) -> str:
    """Format one config template with standard Spatial-VTK variables.

    Parameters
    ----------
    template
        Template string.
    root_dir, config_dir
        Standard project and config directories.
    values
        Additional formatting values.

    Returns
    -------
    str
        Formatted template.
    """

    context = {"root_dir": str(root_dir), "config_dir": str(config_dir), **values}
    return str(template).format(**context)


def command_chain(command: str | None) -> list[str]:
    """Return dotted command prefixes from broad to specific.

    Parameters
    ----------
    command
        Command key such as ``"metrics.calculate.batch"``.

    Returns
    -------
    list[str]
        ``["metrics", "metrics.calculate", "metrics.calculate.batch"]``.
    """

    if not command:
        return []
    parts = [part for part in str(command).split(".") if part]
    return [".".join(parts[: index + 1]) for index in range(len(parts))]


def resolve_run_defaults(config: Mapping[str, Any], command: str | None = None) -> dict[str, Any]:
    """Resolve defaults for one dotted workflow command.

    Parameters
    ----------
    config
        Parsed Spatial-VTK config mapping.
    command
        Dotted command key.

    Returns
    -------
    dict
        Merged defaults. Later command-specific blocks override broader
        defaults.
    """

    run_defaults = dict(config.get("run_defaults") or {})
    defaults = dict(run_defaults.get("common") or {})
    groups = dict(run_defaults.get("groups") or {})
    commands = dict(run_defaults.get("commands") or {})
    for key in command_chain(command):
        defaults = deep_merge(defaults, groups.get(key) or {})
        defaults = deep_merge(defaults, commands.get(key) or {})
    return defaults


def apply_run_scenario(config: Mapping[str, Any], scenario_name: str | None) -> dict[str, Any]:
    """Apply one named run scenario as a top-level config overlay.

    Parameters
    ----------
    config
        Parsed Spatial-VTK config mapping.
    scenario_name
        Key from the top-level ``run_scenarios`` section. ``None`` returns a
        shallow copy of ``config``.

    Returns
    -------
    dict
        Config mapping with the selected scenario deep-merged over the base
        config.
    """

    if not scenario_name:
        return dict(config or {})
    scenarios = dict(config.get("run_scenarios") or {})
    if scenario_name not in scenarios:
        available = ", ".join(sorted(str(key) for key in scenarios)) or "none"
        raise KeyError(f"Unknown Spatial-VTK run scenario {scenario_name!r}. Available scenarios: {available}")
    scenario = scenarios[scenario_name]
    if not isinstance(scenario, Mapping):
        raise ValueError(f"run_scenarios.{scenario_name} must be a mapping/dictionary.")
    base = _drop_exclusive_metric_selector(config, scenario)
    merged = deep_merge(base, scenario)
    merged.setdefault("project", {})
    if isinstance(merged["project"], Mapping):
        merged["project"] = dict(merged["project"])
        merged["project"]["active_run_scenario"] = scenario_name
    return merged


def _drop_exclusive_metric_selector(config: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    """Drop inherited metric selectors that a scenario replaces."""

    base = dict(config or {})
    overlay_metrics = overlay.get("metrics")
    base_metrics = base.get("metrics")
    if not isinstance(overlay_metrics, Mapping) or not isinstance(base_metrics, Mapping):
        return base
    replacement = set(overlay_metrics)
    if replacement.intersection({"metrics", "metric"}):
        updated = dict(base_metrics)
        updated.pop("groups", None)
        updated.pop("metric_groups", None)
        base["metrics"] = updated
    elif replacement.intersection({"groups", "metric_groups"}):
        updated = dict(base_metrics)
        updated.pop("metrics", None)
        updated.pop("metric", None)
        base["metrics"] = updated
    return base


@dataclass(frozen=True)
class SpatialVTKConfig:
    """Resolved public Spatial-VTK configuration object.

    Parameters
    ----------
    config_path
        Config file path, or ``None`` for an empty config.
    root_dir
        Project root used when resolving paths.
    data
        Parsed config mapping.

    Returns
    -------
    SpatialVTKConfig
        Immutable config object.
    """

    config_path: Path | None
    root_dir: Path
    data: dict[str, Any]
    run_scenario: str | None = None

    @classmethod
    def from_file(
        cls,
        config_path: str | Path | None = None,
        *,
        start_dir: str | Path | None = None,
        run_scenario: str | None = None,
    ) -> "SpatialVTKConfig":
        """Load a config object from YAML/JSON or the public search path."""

        path = find_config_file(config_path, start_dir=start_dir)
        payload = load_config(path) if path is not None else {}
        payload = apply_run_scenario(payload, run_scenario)
        config_dir = path.parent if path is not None else Path(start_dir or Path.cwd()).expanduser().resolve()
        root_value = get_dotted(payload, "project.root_dir", None)
        root = resolve_path(root_value, base_dir=config_dir, root_dir=config_dir) if root_value else config_dir
        return cls(config_path=path, root_dir=Path(root).resolve(), data=payload, run_scenario=run_scenario)

    @classmethod
    def empty(cls, *, root_dir: str | Path | None = None) -> "SpatialVTKConfig":
        """Return an empty config object rooted at ``root_dir`` or the repo."""

        return cls(config_path=None, root_dir=Path(root_dir or ROOT_DIR).expanduser().resolve(), data={})

    def with_run_scenario(self, scenario_name: str) -> "SpatialVTKConfig":
        """Return a new config with one named run scenario applied."""

        payload = apply_run_scenario(self.data, scenario_name)
        root_value = get_dotted(payload, "project.root_dir", None)
        root = resolve_path(root_value, base_dir=self.config_dir, root_dir=self.config_dir) if root_value else self.root_dir
        return SpatialVTKConfig(
            config_path=self.config_path,
            root_dir=Path(root).resolve(),
            data=payload,
            run_scenario=scenario_name,
        )

    def run_scenario_names(self) -> tuple[str, ...]:
        """Return available top-level run scenario names."""

        scenarios = self.section("run_scenarios", {}) or {}
        if not isinstance(scenarios, Mapping):
            raise ValueError("run_scenarios must be a mapping from scenario name to config overrides.")
        return tuple(sorted(str(key) for key in scenarios))

    @property
    def config_dir(self) -> Path:
        """Return the directory containing the config file."""

        return self.config_path.parent if self.config_path is not None else self.root_dir

    def section(self, dotted_key: str | None, default: Any = None) -> Any:
        """Return a config section by dotted key."""

        return get_dotted(self.data, dotted_key, default)

    def path(self, dotted_key: str, *, must_exist: bool = False, create_parent: bool = False) -> Path | None:
        """Resolve one configured path by dotted key."""

        value = self.section(dotted_key)
        return resolve_path(
            value,
            base_dir=self.config_dir,
            root_dir=self.root_dir,
            must_exist=must_exist,
            create_parent=create_parent,
        )

    def path_namespace(self, dotted_key: str = "paths", *, suffix: str = "_path", must_exist: bool = False) -> SimpleNamespace:
        """Return configured paths as readable namespace attributes.

        Parameters
        ----------
        dotted_key
            Config section containing path values, commonly ``"paths"``.
        suffix
            Suffix added to each normalized config key. With the default,
            ``paths.observed_root`` becomes ``observed_root_path``.
        must_exist
            Raise ``FileNotFoundError`` when any resolved path does not exist.

        Returns
        -------
        types.SimpleNamespace
            Namespace whose attributes are resolved ``Path`` objects or
            ``None`` for empty path values.
        """

        values = self.section(dotted_key, {}) or {}
        if not isinstance(values, Mapping):
            raise ValueError(f"{dotted_key} must be a mapping of path names to paths.")
        resolved: dict[str, Path | None] = {}
        for key, value in values.items():
            attr = _path_attr_name(str(key), suffix=suffix)
            resolved[attr] = resolve_path(value, base_dir=self.config_dir, root_dir=self.root_dir, must_exist=must_exist)
        return SimpleNamespace(**resolved)

    def paths(self, dotted_key: str, *, must_exist: bool = False) -> list[Path]:
        """Resolve one configured scalar or list of paths by dotted key."""

        value = self.section(dotted_key, [])
        values = value if isinstance(value, (list, tuple)) else [value]
        out = []
        for item in values:
            resolved = resolve_path(item, base_dir=self.config_dir, root_dir=self.root_dir, must_exist=must_exist)
            if resolved is not None:
                out.append(resolved)
        return out

    def path_from_value(self, value: str | Path | None, *, must_exist: bool = False, create_parent: bool = False) -> Path | None:
        """Resolve one raw path value using this config's directories."""

        return resolve_path(
            value,
            base_dir=self.config_dir,
            root_dir=self.root_dir,
            must_exist=must_exist,
            create_parent=create_parent,
        )

    def run_defaults(self, command: str | None = None) -> dict[str, Any]:
        """Return merged run defaults for one workflow command."""

        return resolve_run_defaults(self.data, command)

    def bounds_presets(self) -> dict[str, tuple[float, float, float, float]]:
        """Return user-defined named bounds from inline config and optional CSV."""

        presets: dict[str, tuple[float, float, float, float]] = {}
        csv_path = self.path("bounds.presets_csv")
        if csv_path is not None:
            presets.update(load_bounds_presets(csv_path))
        inline = self.section("bounds.presets", {}) or {}
        if not isinstance(inline, Mapping):
            raise ValueError("bounds.presets must be a mapping from keyword to extent.")
        for key, value in inline.items():
            presets[str(key).strip().lower()] = _coerce_bounds(value, label=str(key))
        return presets

    def resolve_bounds(self, keyword_or_extent: str | list[float] | tuple[float, ...] | None) -> tuple[float, float, float, float] | None:
        """Resolve a named bounds keyword or explicit lon/lat extent."""

        if keyword_or_extent in (None, "", "none"):
            return None
        if isinstance(keyword_or_extent, str):
            token = keyword_or_extent.strip().lower()
            presets = self.bounds_presets()
            if token not in presets:
                raise KeyError(f"Unknown Spatial-VTK bounds keyword: {keyword_or_extent}")
            return presets[token]
        return _coerce_bounds(keyword_or_extent, label="bounds")

    def format_template(self, template: str, **values: object) -> str:
        """Format a config template with this config's directories."""

        return format_template(template, root_dir=self.root_dir, config_dir=self.config_dir, **values)

    def activate(self) -> "SpatialVTKConfig":
        """Make this config the in-process default for output resolution.

        Parameters
        ----------
        None
            The config object itself supplies all values.

        Returns
        -------
        SpatialVTKConfig
            This config object, so calls can be chained.
        """

        global _ACTIVE_CONFIG
        _ACTIVE_CONFIG = self
        return self

    @classmethod
    def active(cls) -> "SpatialVTKConfig":
        """Return the active or discoverable config object."""

        return active_config()


def _coerce_bounds(value: object, *, label: str) -> tuple[float, float, float, float]:
    """Convert one bounds value to ``(lon_min, lon_max, lat_min, lat_max)``.

    Parameters
    ----------
    value
        Sequence or mapping with four bounds values.
    label
        Label used in errors.

    Returns
    -------
    tuple[float, float, float, float]
        Coerced bounds tuple.
    """

    if isinstance(value, Mapping):
        raw = [value.get("lon_min"), value.get("lon_max"), value.get("lat_min"), value.get("lat_max")]
    else:
        raw = list(value) if isinstance(value, (list, tuple)) else []
    if len(raw) != 4:
        raise ValueError(f"Bounds preset {label!r} must provide lon_min, lon_max, lat_min, lat_max.")
    return tuple(float(item) for item in raw)  # type: ignore[return-value]


def _path_attr_name(key: str, *, suffix: str) -> str:
    """Return a safe namespace attribute name for a configured path key."""

    attr = re.sub(r"[^0-9a-zA-Z_]+", "_", key.strip()).strip("_").lower()
    if suffix and not attr.endswith(suffix):
        attr = f"{attr}{suffix}"
    return attr


class _SafePathFormat(dict[str, str]):
    """Format known path variables while preserving workflow placeholders."""

    def __missing__(self, key: str) -> str:
        return "{" + str(key) + "}"
