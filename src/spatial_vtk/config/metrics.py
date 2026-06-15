"""Public metric configuration parsing helpers.

Purpose
-------
This module normalizes the metric-related portions of a Spatial-VTK config
file into explicit public settings used by metric planning, QC, and workflow
orchestration.

Usage examples
--------------
Load metric settings from a config object:
  ``settings = metrics_settings_from_config(config)``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re

import pandas as pd

from spatial_vtk.config.metric_catalog import (
    ALL_METRIC_GROUPS,
    ALL_METRICS,
    DEFAULT_METRICS_BY_GROUP,
    metric_group_for,
    normalize_metric_groups,
    resolve_metric_names,
)
from spatial_vtk.config.runtime import SpatialVTKConfig, active_config


DEFAULT_METRIC_GROUPS: tuple[str, ...] = ("amplitude",)
DEFAULT_METRICS: tuple[str, ...] = ("PGA",)
DEFAULT_TRANSFORMS: tuple[str, ...] = ("log2_residual",)
DEFAULT_OUTPUT_MODE = "full"

VALID_OUTPUT_MODES = ("observed", "synthetic", "residual", "gof", "full")
VALID_TRANSFORMS = (
    "residual",
    "log2_residual",
    "ln_residual",
    "anderson_2004_gof",
    "olsen_mayhew_gof",
)


@dataclass(frozen=True)
class SpectralSettings:
    """Settings that control PSA/FAS period selection and QC.

    Parameters
    ----------
    periods_s
        Requested spectral periods.
    relative_amplitude_threshold
        Minimum fraction of the maximum spectral amplitude required for a
        period to be usable.
    min_cycles_in_record
        Minimum usable cycles required to support a period.
    disable_relative_amplitude_qc
        Whether to disable relative spectral support checks.

    Returns
    -------
    SpectralSettings
               Normalized spectral settings.
    """

    periods_s: tuple[float, ...] = ()
    relative_amplitude_threshold: float = 0.25
    min_cycles_in_record: float = 3.0
    disable_relative_amplitude_qc: bool = False


@dataclass(frozen=True)
class MetricSettings:
    """Resolved public metric settings.

    Parameters
    ----------
    groups
        Metric groups to calculate.
    metrics
        Metric names to calculate.
    transforms
        Requested comparison transforms. The output schema has room for all
        requested transforms.
    components
        Waveform components or channels requested for QC and metric work.
    passbands
        Period bands requested for QC and metric work.
    output_mode
        One of observed, synthetic, residual, gof, or full.
    spectral
        Spectral settings for PSA/FAS.
    synthetic_max_frequency_hz
        Maximum valid synthetic frequency, if configured.
    require_source_overlap
        Whether metric-QC and metric planning should restrict work to records
        with both observed and synthetic data.
    source_overlap_scope
        Scope for overlap filtering: ``"event"`` or ``"event_station"``.

    Returns
    -------
    MetricSettings
               Normalized metric settings.
    """

    groups: tuple[str, ...] = DEFAULT_METRIC_GROUPS
    metrics: tuple[str, ...] = DEFAULT_METRICS
    transforms: tuple[str, ...] = DEFAULT_TRANSFORMS
    components: tuple[str, ...] = ("Z",)
    passbands: tuple[str | tuple[float, float], ...] = ()
    output_mode: str = DEFAULT_OUTPUT_MODE
    spectral: SpectralSettings = field(default_factory=SpectralSettings)
    synthetic_max_frequency_hz: float | None = None
    require_source_overlap: bool = False
    source_overlap_scope: str = "event"


def metrics_settings_from_config(
    config: SpatialVTKConfig | None = None,
    *,
    command: str = "metrics.calculate",
    overrides: dict[str, Any] | None = None,
) -> MetricSettings:
    """Build a metric settings object from a public config object.

    Parameters
    ----------
    config
        Loaded Spatial-VTK config. When omitted, the active or discoverable
        config is used.
    command
        Dotted command key used to merge run defaults.
    overrides
        Explicit values for this run. These override the config file and any
        selected run scenario.

    Returns
    -------
    MetricSettings
               Parsed public metric settings.
    """

    resolved_config = config or active_config()
    metric_cfg = dict(resolved_config.section("metrics", {}) or {})
    defaults = resolved_config.run_defaults(command)
    merged: dict[str, Any] = {**metric_cfg, **defaults}
    explicit_overrides = dict(overrides or {})
    if any(key in explicit_overrides for key in ("metrics", "metric")):
        merged.pop("groups", None)
        merged.pop("metric_groups", None)
    if any(key in explicit_overrides for key in ("groups", "metric_groups")):
        merged.pop("metrics", None)
        merged.pop("metric", None)
    merged = {**merged, **explicit_overrides}
    spectral_cfg = dict(merged.get("spectral") or {})
    synthetic_cfg = dict(resolved_config.section("synthetics", {}) or {})
    group_value = merged.get("groups", merged.get("metric_groups"))
    metric_value = merged.get("metrics", merged.get("metric"))
    has_groups = group_value not in (None, "", [])
    has_metrics = metric_value not in (None, "", [])
    if has_groups and has_metrics:
        raise ValueError("Set either metrics.groups or metrics.metrics, not both.")
    if has_groups:
        groups = normalize_metric_groups(_as_tuple(group_value))
        metrics = resolve_metric_names(None, groups)
    else:
        metrics = resolve_metric_names(_as_tuple(metric_value or DEFAULT_METRICS), None)
        groups = tuple(dict.fromkeys(metric_group_for(metric) for metric in metrics if metric_group_for(metric)))
    transforms = _normalize_transforms(merged.get("transforms") or merged.get("transform") or DEFAULT_TRANSFORMS)
    components = _normalize_components(merged.get("components") or merged.get("component") or ("Z",))
    passbands = _normalize_passbands(merged.get("passbands") or merged.get("passband") or ())
    output_mode = _normalize_output_mode(merged.get("output_mode") or merged.get("mode") or DEFAULT_OUTPUT_MODE)
    require_source_overlap = _as_bool(
        merged.get(
            "require_source_overlap",
            merged.get("require_observed_synthetic_overlap", merged.get("overlap_only", False)),
        )
    )
    source_overlap_scope = _normalize_source_overlap_scope(merged.get("source_overlap_scope", merged.get("overlap_scope", "event")))
    synthetic_max_frequency_hz = _optional_positive_float(
        merged.get("synthetic_max_frequency_hz", synthetic_cfg.get("max_frequency_hz"))
    )
    spectral = SpectralSettings(
        periods_s=_parse_float_tuple(spectral_cfg.get("periods_s") or spectral_cfg.get("periods") or merged.get("spectral_periods_s") or ()),
        relative_amplitude_threshold=float(
            spectral_cfg.get("relative_amplitude_threshold", merged.get("spectral_relative_amplitude_threshold", 0.25))
        ),
        min_cycles_in_record=float(spectral_cfg.get("min_cycles_in_record", 3.0)),
        disable_relative_amplitude_qc=_as_bool(spectral_cfg.get("disable_relative_amplitude_qc", False)),
    )
    return MetricSettings(
        groups=groups,
        metrics=metrics,
        transforms=transforms,
        components=components,
        passbands=passbands,
        output_mode=output_mode,
        spectral=spectral,
        synthetic_max_frequency_hz=synthetic_max_frequency_hz,
        require_source_overlap=require_source_overlap,
        source_overlap_scope=source_overlap_scope,
    )


def transform_columns(transforms: tuple[str, ...] | list[str] | None = None) -> tuple[str, ...]:
    """Return requested transform output columns."""

    selected = _normalize_transforms(transforms or VALID_TRANSFORMS)
    return tuple(transform for transform in selected)


def metric_settings_summary(settings: MetricSettings) -> pd.DataFrame:
    """Summarize resolved metric settings as a readable table.

    Parameters
    ----------
    settings
        Resolved metric settings from ``metrics_settings_from_config``.

    Returns
    -------
    pandas.DataFrame
        Two-column summary table with human-readable setting names and values.
    """

    rows = [
        ("Groups", ", ".join(settings.groups)),
        ("Metrics", ", ".join(settings.metrics)),
        ("Transforms", ", ".join(_format_transform(transform) for transform in settings.transforms)),
        ("Components", ", ".join(settings.components)),
        ("Passbands", ", ".join(_format_passband(item) for item in settings.passbands) or "none"),
        ("Output mode", settings.output_mode),
        ("Require source overlap", "yes" if settings.require_source_overlap else "no"),
        ("Source overlap scope", settings.source_overlap_scope),
        ("Spectral periods", ", ".join(f"{period:g} s" for period in settings.spectral.periods_s) or "none"),
    ]
    if settings.synthetic_max_frequency_hz is not None:
        rows.append(("Synthetic max frequency", f"{settings.synthetic_max_frequency_hz:g} Hz"))
    return pd.DataFrame(rows, columns=["Setting", "Value"])


def _as_tuple(value: object) -> tuple[str, ...]:
    """Normalize a scalar or sequence into a string tuple."""

    if value in (None, ""):
        return ()
    if isinstance(value, str):
        return tuple(part for part in re.split(r"[\s,]+", value.strip()) if part)
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value if item not in (None, ""))
    return (str(value),)


def _parse_float_tuple(value: object) -> tuple[float, ...]:
    """Normalize a scalar or sequence into a float tuple."""

    if value in (None, ""):
        return ()
    values = value if isinstance(value, (list, tuple, set)) else [value]
    return tuple(float(item) for item in values if item not in (None, ""))


def _normalize_components(value: object) -> tuple[str, ...]:
    """Normalize configured waveform components."""

    components = tuple(component.strip().upper() for component in _as_tuple(value) if component.strip())
    return components or ("Z",)


def _normalize_passbands(value: object) -> tuple[str | tuple[float, float], ...]:
    """Normalize configured period-band values while preserving public labels."""

    if value in (None, ""):
        return ()
    values = value if isinstance(value, (list, tuple)) else [value]
    out: list[str | tuple[float, float]] = []
    for item in values:
        if item in (None, ""):
            continue
        if isinstance(item, str):
            out.append(item)
            continue
        if isinstance(item, (list, tuple)) and len(item) == 2:
            out.append((float(item[0]), float(item[1])))
            continue
        raise ValueError(f"Passband entries must be strings or two-value period ranges; got {item!r}.")
    return tuple(out)


def _format_passband(value: str | tuple[float, float]) -> str:
    """Format a passband value for notebook and CLI display."""

    if isinstance(value, str):
        return value
    lo, hi = value
    return f"{lo:g}-{hi:g} sec"


def _format_transform(value: str) -> str:
    """Format a transform value for notebook and CLI display."""

    labels = {
        "residual": "Observed - synthetic",
        "log2_residual": "log2(observed / synthetic)",
        "ln_residual": "ln(observed / synthetic)",
        "anderson_2004_gof": "Anderson 2004 GOF",
        "olsen_mayhew_gof": "Olsen-Mayhew GOF",
    }
    return labels.get(str(value), str(value).replace("_", " ").title())


def _normalize_output_mode(value: object) -> str:
    """Normalize a requested metric output mode."""

    token = str(value or DEFAULT_OUTPUT_MODE).strip().lower().replace("-", "_")
    aliases = {"obs": "observed", "syn": "synthetic", "score": "gof", "scores": "gof"}
    token = aliases.get(token, token)
    if token not in VALID_OUTPUT_MODES:
        raise ValueError(f"Unknown metric output mode {value!r}. Expected one of {VALID_OUTPUT_MODES}.")
    return token


def _normalize_source_overlap_scope(value: object) -> str:
    """Normalize observed/synthetic overlap-filtering scope."""

    token = str(value or "event").strip().lower().replace("-", "_")
    aliases = {
        "events": "event",
        "event_id": "event",
        "event_station_pair": "event_station",
        "event_station_pairs": "event_station",
        "event_station_record": "event_station",
        "record": "event_station",
        "records": "event_station",
        "pair": "event_station",
        "pairs": "event_station",
    }
    token = aliases.get(token, token)
    if token not in {"event", "event_station"}:
        raise ValueError("metrics.source_overlap_scope must be 'event' or 'event_station'.")
    return token


def _normalize_transforms(value: object) -> tuple[str, ...]:
    """Normalize requested transform names and preserve arbitrary selections."""

    transforms = []
    aliases = {
        "log_residual": "ln_residual",
        "ln": "ln_residual",
        "log2": "log2_residual",
        "anderson": "anderson_2004_gof",
        "anderson_gof": "anderson_2004_gof",
        "olsen_mayhew": "olsen_mayhew_gof",
        "olsen_mayhew_2011": "olsen_mayhew_gof",
    }
    for item in _as_tuple(value):
        token = item.strip().lower().replace("-", "_")
        transforms.append(aliases.get(token, token))
    unknown = [item for item in transforms if item not in VALID_TRANSFORMS]
    if unknown:
        raise ValueError(f"Unknown metric transforms {unknown}. Expected a subset of {VALID_TRANSFORMS}.")
    return tuple(dict.fromkeys(transforms))


def _optional_positive_float(value: object) -> float | None:
    """Return a positive float or ``None``."""

    if value in (None, ""):
        return None
    out = float(value)
    if out <= 0.0:
        raise ValueError("synthetic maximum frequency must be positive.")
    return out


def _as_bool(value: object) -> bool:
    """Interpret common config truth values."""

    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


__all__ = [
    "ALL_METRIC_GROUPS",
    "ALL_METRICS",
    "DEFAULT_METRICS_BY_GROUP",
    "DEFAULT_METRIC_GROUPS",
    "DEFAULT_METRICS",
    "DEFAULT_TRANSFORMS",
    "DEFAULT_OUTPUT_MODE",
    "VALID_OUTPUT_MODES",
    "VALID_TRANSFORMS",
    "SpectralSettings",
    "MetricSettings",
    "metric_settings_summary",
    "metrics_settings_from_config",
    "transform_columns",
]
