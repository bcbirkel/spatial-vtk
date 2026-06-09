"""Configuration helpers for spatial-statistics workflows.

Purpose
-------
This module resolves spatial-analysis settings from the active Spatial-VTK
configuration so notebooks and scripts do not need repeated config plumbing.

Usage examples
--------------
Read active spatial settings:
  ``settings = spatial_statistics_settings_from_config()``
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from spatial_vtk.config.runtime import SpatialVTKConfig, active_config


@dataclass(frozen=True)
class SpatialStatisticsSettings:
    """Resolved settings for spatial-statistics calculations.

    Parameters
    ----------
    metric
        Metric name or ``"all"`` used when building a spatial field.
    value_column
        Metric value, residual, or score column used as the spatial field.
    remove_event_mean
        Whether event means should be removed when centering a field.
    min_stations_per_event, min_events_per_station
        Minimum support thresholds for event centering and station summaries.
    moran_neighbors, moran_permutations
        Moran's I nearest-neighbor and permutation-test settings.
    distance_bin_width_km
        Distance-bin width for correlation summaries.
    cluster_min_k, cluster_max_k
        Cluster-count search range.
    pca_components
        Requested number of PCA spatial modes.
    geology_group_column, geology_left_values, geology_right_values
        Geology contrast classes.
    geology_min_stations_per_group
        Minimum station count required on each side of a geology contrast.
    geology_bootstrap_samples
        Bootstrap draws used for geology contrasts.
    geology_statistic
        Station-summary statistic used for geology contrasts.
    random_seed
        Reproducibility seed for stochastic spatial calculations.
    region_geojson_path
        Optional configured GeoJSON polygon path.
    """

    metric: str = "all"
    value_column: str = "log2_residual"
    remove_event_mean: bool = True
    min_stations_per_event: int = 2
    min_events_per_station: int = 1
    moran_neighbors: int = 2
    moran_permutations: int = 99
    distance_bin_width_km: float = 20.0
    cluster_min_k: int = 2
    cluster_max_k: int = 4
    pca_components: int = 2
    geology_group_column: str = "mapped_region_type"
    geology_left_values: tuple[str, ...] = ("Basin",)
    geology_right_values: tuple[str, ...] = ("Mountains",)
    geology_min_stations_per_group: int = 3
    geology_bootstrap_samples: int = 100
    geology_statistic: str = "mean"
    random_seed: int = 42
    region_geojson_path: Path | None = None


def spatial_statistics_settings_from_config(cfg: SpatialVTKConfig | None = None) -> SpatialStatisticsSettings:
    """Resolve spatial-statistics settings from a config.

    Parameters
    ----------
    cfg
        Optional config. When omitted, the active/discoverable config is used.

    Returns
    -------
    SpatialStatisticsSettings
        Resolved spatial settings with package defaults filled in.
    """

    config = cfg or active_config()
    section = config.section("spatial", {})
    region_path = config.path("paths.region_geojson", must_exist=False)
    return SpatialStatisticsSettings(
        metric=str(section.get("metric", "all")),
        value_column=str(section.get("value_column", section.get("field_mode", "log2_residual"))),
        remove_event_mean=_as_bool(section.get("remove_event_mean", True)),
        min_stations_per_event=int(section.get("min_stations_per_event", 2)),
        min_events_per_station=int(section.get("min_events_per_station", 1)),
        moran_neighbors=int(section.get("moran_neighbors", 2)),
        moran_permutations=int(section.get("moran_permutations", 99)),
        distance_bin_width_km=float(section.get("distance_bin_width_km", 20.0)),
        cluster_min_k=int(section.get("cluster_min_k", 2)),
        cluster_max_k=int(section.get("cluster_max_k", 4)),
        pca_components=int(section.get("pca_components", 2)),
        geology_group_column=str(section.get("geology_group_column", "mapped_region_type")),
        geology_left_values=_as_tuple(section.get("geology_left_values", ("Basin",))),
        geology_right_values=_as_tuple(section.get("geology_right_values", ("Mountains",))),
        geology_min_stations_per_group=int(section.get("geology_min_stations_per_group", 3)),
        geology_bootstrap_samples=int(section.get("geology_bootstrap_samples", 100)),
        geology_statistic=str(section.get("geology_statistic", "mean")),
        random_seed=int(section.get("random_seed", 42)),
        region_geojson_path=region_path,
    )


def _as_tuple(value: Any) -> tuple[str, ...]:
    """Convert a config value into a tuple of strings."""

    if isinstance(value, str):
        return (value,)
    if value is None:
        return tuple()
    return tuple(str(item) for item in value)


def _as_bool(value: Any) -> bool:
    """Convert common config truthy/falsy values into a boolean."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off"}
    return bool(value)


__all__ = [
    "SpatialStatisticsSettings",
    "spatial_statistics_settings_from_config",
]
