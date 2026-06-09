"""Public metric catalog used by config parsing and workflow planning.

Purpose
-------
This module defines the public metric groups, metric names, and legacy C-code
aliases that Spatial-VTK accepts in configuration files.

Usage examples
--------------
Resolve all amplitude metrics:
  ``resolve_metric_names(metrics=None, groups=("amplitude",))``
"""

from __future__ import annotations


DEFAULT_METRICS_BY_GROUP: dict[str, tuple[str, ...]] = {
    "duration": ("arias_duration", "energy_duration"),
    "amplitude": ("PGA", "PGV", "PGD"),
    "spectral": ("PSA", "FAS"),
    "intensity": ("arias_intensity", "energy_intensity", "CAV"),
    "delay": ("traveltime_delay",),
    "cross_correlation": ("original_cc", "delay_corrected_cc"),
}

LEGACY_METRIC_ALIASES: dict[str, str] = {
    "C1": "arias_duration",
    "C2": "energy_duration",
    "C3": "arias_intensity",
    "C4": "energy_intensity",
    "C5": "PGA",
    "C6": "PGV",
    "C7": "PGD",
    "C8": "PSA",
    "C9": "FAS",
    "C10": "original_cc",
    "C11": "traveltime_delay",
    "C12": "delay_corrected_cc",
    "C13": "CAV",
}

ALL_METRIC_GROUPS: tuple[str, ...] = tuple(DEFAULT_METRICS_BY_GROUP)
ALL_METRICS: tuple[str, ...] = tuple(
    metric for metrics in DEFAULT_METRICS_BY_GROUP.values() for metric in metrics
)


def normalize_metric_groups(groups: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    """Normalize metric-group selections, including the ``all`` keyword.

    Parameters
    ----------
    groups
        Metric group names or ``all``.

    Returns
    -------
    tuple[str, ...]
        Valid public metric group names.
    """

    requested = tuple(str(item).strip().lower() for item in (groups or ()) if str(item).strip())
    if not requested or any(item == "all" for item in requested):
        return ALL_METRIC_GROUPS
    unknown = [item for item in requested if item not in DEFAULT_METRICS_BY_GROUP]
    if unknown:
        raise ValueError(
            f"Unknown metric groups {unknown}. Expected any of {ALL_METRIC_GROUPS} or 'all'."
        )
    return tuple(dict.fromkeys(requested))


def normalize_metric_name(metric: str) -> str:
    """Return the public name for one metric or legacy C-code.

    Parameters
    ----------
    metric
        Public metric name or legacy C-code.

    Returns
    -------
    str
        Public metric name.
    """

    text = str(metric).strip()
    return LEGACY_METRIC_ALIASES.get(text.upper(), text)


def resolve_metric_names(
    metrics: tuple[str, ...] | list[str] | None,
    groups: tuple[str, ...] | list[str] | None = None,
) -> tuple[str, ...]:
    """Resolve public metric names from metric or group selections.

    Parameters
    ----------
    metrics
        Explicit metric names, legacy C-codes, or ``all``.
    groups
        Metric groups used when explicit metrics are omitted.

    Returns
    -------
    tuple[str, ...]
        Public metric names.
    """

    requested = tuple(str(item).strip() for item in (metrics or ()) if str(item).strip())
    if requested:
        if any(item.lower() == "all" for item in requested):
            return ALL_METRICS
        resolved = tuple(normalize_metric_name(item) for item in requested)
        unknown = [item for item in resolved if item not in ALL_METRICS]
        if unknown:
            raise ValueError(
                f"Unknown metrics {unknown}. Expected any public metric, legacy C-code, or 'all'."
            )
        return tuple(dict.fromkeys(resolved))

    selected_groups = normalize_metric_groups(groups)
    out: list[str] = []
    for group in selected_groups:
        out.extend(DEFAULT_METRICS_BY_GROUP[group])
    return tuple(dict.fromkeys(out))


def metric_group_for(metric: str) -> str:
    """Return the public metric group for one metric name.

    Parameters
    ----------
    metric
        Public metric name or legacy C-code.

    Returns
    -------
    str
        Metric group name.
    """

    public_name = normalize_metric_name(metric)
    for group, names in DEFAULT_METRICS_BY_GROUP.items():
        if public_name in names:
            return group
    return ""


__all__ = [
    "ALL_METRIC_GROUPS",
    "ALL_METRICS",
    "DEFAULT_METRICS_BY_GROUP",
    "LEGACY_METRIC_ALIASES",
    "metric_group_for",
    "normalize_metric_groups",
    "normalize_metric_name",
    "resolve_metric_names",
]
