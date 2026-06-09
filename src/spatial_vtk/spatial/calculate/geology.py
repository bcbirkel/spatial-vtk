"""Geology-class joins and station-level spatial/geology tests."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
import json
import re
import warnings

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.stats import kruskal
from shapely.geometry import Point, shape
from shapely.ops import transform

from spatial_vtk.spatial.calculate._common import haversine_km, metric_label, metric_sort_key, normalize_passband
from spatial_vtk.spatial.calculate.correlation import compute_global_morans_i
from spatial_vtk.spatial.calculate.prepare_stats import collapse_and_event_demean, collapse_and_reference_demean
from spatial_vtk.spatial.calculate.settings import spatial_statistics_settings_from_config

DEFAULT_C_PASSBANDS = ["1-2 sec", "2-3 sec", "3-5 sec", "5-8 sec"]
DEFAULT_GEOLOGY_CONTRASTS = [
    (
        "target_region_inside_minus_outside",
        ("target_region_interior", "target_region_edge_inside"),
        ("target_region_edge_outside", "outside_target_region"),
        "target_region_zone",
    ),
    (
        "target_region_edge_inside_minus_outside",
        ("target_region_edge_inside",),
        ("target_region_edge_outside", "outside_target_region"),
        "target_region_zone",
    ),
    ("Basin_minus_Mountains", ("Basin",), ("Mountains",), "mapped_region_type"),
]


def discover_metric_stems(columns: Iterable[str], *, require_syn: bool) -> tuple[list[str], list[str]]:
    """Discover C-metric and PSA metric stems in a metrics table."""

    column_set = {str(column) for column in columns}
    stems = []
    for column in column_set:
        if not column.endswith("_obs"):
            continue
        stem = column[:-4]
        if require_syn and f"{stem}_syn" not in column_set:
            continue
        if re.fullmatch(r"C(?:[1-9]|1[0-3])", stem) or re.fullmatch(r"PSA_T[0-9]+(?:\.[0-9]+)?", stem):
            stems.append(stem)
    stems = sorted(set(stems), key=metric_sort_key)
    return [stem for stem in stems if stem.startswith("C")], [stem for stem in stems if stem.startswith("PSA_T")]


def load_region_geometries(geojson_path: str | Path, *, region_name: str | None = None) -> tuple[list[dict[str, object]], object]:
    """Load mapped-region records and a target-region geometry from GeoJSON."""

    path = Path(geojson_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = []
    selected_geom = None
    target = region_name.lower() if region_name is not None else None
    for feature in payload.get("features", []):
        props = feature.get("properties", {})
        geom = shape(feature.get("geometry"))
        record = {
            "geom": geom,
            "short_name": props.get("short_name") or props.get("name") or props.get("long_name") or "unknown",
            "long_name": props.get("long_name") or props.get("name") or props.get("short_name") or "unknown",
            "region_type": props.get("region_type") or "unmapped",
        }
        records.append(record)
        names = [str(record["short_name"]).lower(), str(record["long_name"]).lower()]
        if target is None and selected_geom is None:
            selected_geom = geom
        elif target in names:
            selected_geom = geom
    if selected_geom is None:
        if region_name is None:
            raise ValueError(f"No polygon features found in {path}")
        raise ValueError(f"No feature named {region_name!r} found in {path}")
    return records, selected_geom


def add_station_geology_classes(
    df: pd.DataFrame,
    *,
    region_records: list[dict[str, object]],
    target_region_geom: object,
    edge_buffer_km: float,
    lon_col: str = "station_longitude",
    lat_col: str = "station_latitude",
) -> pd.DataFrame:
    """Add target-region edge-zone and mapped-region labels to station rows."""

    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3310", always_xy=True)

    def project(x, y, z=None):
        return transformer.transform(x, y)

    target_projected = transform(project, target_region_geom)
    station_coords = df[[lon_col, lat_col]].drop_duplicates().copy()
    classes: dict[tuple[float, float], tuple[str, float, str, str]] = {}
    for row in station_coords.itertuples(index=False):
        lon = float(getattr(row, lon_col))
        lat = float(getattr(row, lat_col))
        point_ll = Point(lon, lat)
        point_projected = transform(project, point_ll)
        inside_target = bool(target_region_geom.contains(point_ll) or target_region_geom.touches(point_ll))
        distance_km = float(target_projected.boundary.distance(point_projected) / 1000.0)
        if inside_target and distance_km >= edge_buffer_km:
            target_region_zone = "target_region_interior"
        elif inside_target:
            target_region_zone = "target_region_edge_inside"
        elif distance_km < edge_buffer_km:
            target_region_zone = "target_region_edge_outside"
        else:
            target_region_zone = "outside_target_region"
        hits = []
        for record in region_records:
            geom = record["geom"]
            if geom.contains(point_ll) or geom.touches(point_ll):
                hits.append(record)
        if hits:
            hits.sort(key=lambda item: item["geom"].area)
            hit = hits[0]
            mapped_region = f"{hit['short_name']}:{hit['region_type']}"
            mapped_region_type = str(hit["region_type"])
        else:
            mapped_region = "unmapped"
            mapped_region_type = "unmapped"
        classes[(lon, lat)] = (target_region_zone, distance_km, mapped_region, mapped_region_type)
    out = df.copy()
    values = [classes[(float(lon), float(lat))] for lon, lat in zip(out[lon_col], out[lat_col])]
    out["target_region_zone"] = [value[0] for value in values]
    out["target_region_edge_distance_km"] = [value[1] for value in values]
    out["mapped_region"] = [value[2] for value in values]
    out["mapped_region_type"] = [value[3] for value in values]
    return out


def hypocentral_distance(df: pd.DataFrame) -> np.ndarray:
    """Compute hypocentral event-station distances in kilometers."""

    horizontal = haversine_km(df["event_latitude"], df["event_longitude"], df["station_latitude"], df["station_longitude"])
    depth = pd.to_numeric(df.get("event_depth_km", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
    return np.sqrt(horizontal**2 + depth**2).clip(min=0.001)


def build_observed_c_events(df: pd.DataFrame, c_metrics: list[str], passbands: list[str]) -> pd.DataFrame:
    """Build event-demeaned observed anomaly rows for C metrics."""

    work = df.copy()
    work["event_id"] = work["event_id"].astype(str)
    work["passband_norm"] = work["simulation_band"].map(normalize_passband)
    work = work[work["passband_norm"].isin(passbands)].copy()
    work["hypocentral_distance_km"] = hypocentral_distance(work)
    pieces = []
    base_cols = ["event_id", "station_name", "station_longitude", "station_latitude", "target_region_zone", "target_region_edge_distance_km", "mapped_region", "mapped_region_type", "passband_norm"]
    for metric in c_metrics:
        column = f"{metric}_obs"
        if column not in work.columns:
            continue
        subset = work[base_cols + [column, "hypocentral_distance_km"]].copy()
        subset[column] = pd.to_numeric(subset[column], errors="coerce")
        subset = subset.replace([np.inf, -np.inf], np.nan).dropna(subset=[column])
        subset = subset[subset[column] > 0.0].copy()
        if subset.empty:
            continue
        subset["dataset"] = "observed"
        subset["metric"] = metric
        subset["bin"] = subset["passband_norm"]
        subset["value_raw"] = np.log(subset[column].astype(float) * subset["hypocentral_distance_km"].astype(float))
        pieces.append(subset.drop(columns=[column, "hypocentral_distance_km", "passband_norm"]))
    return collapse_and_event_demean(pd.concat(pieces, ignore_index=True)) if pieces else pd.DataFrame()


def build_observed_psa_events(df: pd.DataFrame, psa_metrics: list[str]) -> pd.DataFrame:
    """Build event-demeaned observed anomaly rows for raw PSA periods."""

    work = df.copy()
    work["event_id"] = work["event_id"].astype(str)
    work["passband_norm"] = work["simulation_band"].map(normalize_passband)
    work = work[work["passband_norm"].str.lower().eq("raw")].copy()
    work["hypocentral_distance_km"] = hypocentral_distance(work)
    pieces = []
    base_cols = ["event_id", "station_name", "station_longitude", "station_latitude", "target_region_zone", "target_region_edge_distance_km", "mapped_region", "mapped_region_type"]
    for metric in psa_metrics:
        column = f"{metric}_obs"
        if column not in work.columns:
            continue
        subset = work[base_cols + [column, "hypocentral_distance_km"]].copy()
        subset[column] = pd.to_numeric(subset[column], errors="coerce")
        subset = subset.replace([np.inf, -np.inf], np.nan).dropna(subset=[column])
        subset = subset[subset[column] > 0.0].copy()
        if subset.empty:
            continue
        subset["dataset"] = "observed"
        subset["metric"] = metric
        subset["bin"] = metric.replace("PSA_T", "T=") + " s"
        subset["value_raw"] = np.log(subset[column].astype(float) * subset["hypocentral_distance_km"].astype(float))
        pieces.append(subset.drop(columns=[column, "hypocentral_distance_km"]))
    return collapse_and_event_demean(pd.concat(pieces, ignore_index=True)) if pieces else pd.DataFrame()


def normalize_residual_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize event and coordinate columns in a residual metrics table."""

    out = df.copy()
    if "event_id" not in out.columns:
        out["event_id"] = out["event_title"].astype(str)
    if "magnitude" not in out.columns and "event_magnitude" in out.columns:
        out["magnitude"] = out["event_magnitude"]
    out["event_id"] = out["event_id"].astype(str)
    out["passband_norm"] = out["simulation_band"].map(normalize_passband)
    for column in ["station_longitude", "station_latitude", "event_longitude", "event_latitude", "event_depth_km"]:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    return out


def build_residual_c_events(df: pd.DataFrame, c_metrics: list[str], passbands: list[str]) -> pd.DataFrame:
    """Build event-demeaned log2 observed/synthetic residual rows for C metrics."""

    work = df[df["passband_norm"].isin(passbands)].copy()
    pieces = []
    base_cols = ["event_id", "station_name", "station_longitude", "station_latitude", "target_region_zone", "target_region_edge_distance_km", "mapped_region", "mapped_region_type", "passband_norm"]
    for metric in c_metrics:
        obs_col = f"{metric}_obs"
        syn_col = f"{metric}_syn"
        if obs_col not in work.columns or syn_col not in work.columns:
            continue
        subset = work[base_cols + [obs_col, syn_col]].copy()
        subset[obs_col] = pd.to_numeric(subset[obs_col], errors="coerce")
        subset[syn_col] = pd.to_numeric(subset[syn_col], errors="coerce")
        subset = subset.replace([np.inf, -np.inf], np.nan).dropna(subset=[obs_col, syn_col])
        subset = subset[(subset[obs_col] > 0.0) & (subset[syn_col] > 0.0)].copy()
        if subset.empty:
            continue
        subset["dataset"] = "residual"
        subset["metric"] = metric
        subset["bin"] = subset["passband_norm"]
        subset["value_raw"] = np.log2(subset[obs_col].astype(float) / subset[syn_col].astype(float))
        pieces.append(subset.drop(columns=[obs_col, syn_col, "passband_norm"]))
    return collapse_and_event_demean(pd.concat(pieces, ignore_index=True)) if pieces else pd.DataFrame()


def build_residual_psa_events(df: pd.DataFrame, psa_metrics: list[str]) -> pd.DataFrame:
    """Build event-demeaned log2 observed/synthetic residual rows for PSA periods."""

    pieces = []
    base_cols = ["event_id", "station_name", "station_longitude", "station_latitude", "target_region_zone", "target_region_edge_distance_km", "mapped_region", "mapped_region_type"]
    for metric in psa_metrics:
        obs_col = f"{metric}_obs"
        syn_col = f"{metric}_syn"
        if obs_col not in df.columns or syn_col not in df.columns:
            continue
        subset = df[base_cols + [obs_col, syn_col]].copy()
        subset[obs_col] = pd.to_numeric(subset[obs_col], errors="coerce")
        subset[syn_col] = pd.to_numeric(subset[syn_col], errors="coerce")
        subset = subset.replace([np.inf, -np.inf], np.nan).dropna(subset=[obs_col, syn_col])
        subset = subset[(subset[obs_col] > 0.0) & (subset[syn_col] > 0.0)].copy()
        if subset.empty:
            continue
        subset = subset.drop_duplicates(base_cols + [obs_col, syn_col])
        subset["dataset"] = "residual"
        subset["metric"] = metric
        subset["bin"] = metric.replace("PSA_T", "T=") + " s"
        subset["value_raw"] = np.log2(subset[obs_col].astype(float) / subset[syn_col].astype(float))
        pieces.append(subset.drop(columns=[obs_col, syn_col]))
    return collapse_and_event_demean(pd.concat(pieces, ignore_index=True)) if pieces else pd.DataFrame()


def matched_piece(subset: pd.DataFrame, *, metric: str, suffix: str, bin_label: str) -> pd.DataFrame:
    """Convert matched observed/synthetic rows into one dataset's anomaly rows."""

    column = f"{metric}_{suffix}"
    piece = subset[["event_id", "station_name", "station_longitude", "station_latitude", "target_region_zone", "target_region_edge_distance_km", "mapped_region", "mapped_region_type", column, "hypocentral_distance_km"]].copy()
    piece["dataset"] = "observed" if suffix == "obs" else "synthetic"
    piece["metric"] = metric
    piece["bin"] = bin_label
    piece["value_raw"] = np.log(piece[column].astype(float) * piece["hypocentral_distance_km"].astype(float))
    return piece.drop(columns=[column, "hypocentral_distance_km"])


def build_c_events(df: pd.DataFrame, c_metrics: list[str], passbands: list[str], *, anomaly_reference: str = "pooled") -> pd.DataFrame:
    """Build matched observed and synthetic event-station rows for C metrics."""

    work = df[df["passband_norm"].isin(passbands)].copy()
    work["hypocentral_distance_km"] = hypocentral_distance(work)
    pieces = []
    base_cols = ["event_id", "station_name", "station_longitude", "station_latitude", "target_region_zone", "target_region_edge_distance_km", "mapped_region", "mapped_region_type", "passband_norm", "hypocentral_distance_km"]
    for metric in c_metrics:
        obs_col = f"{metric}_obs"
        syn_col = f"{metric}_syn"
        if obs_col not in work.columns or syn_col not in work.columns:
            continue
        subset = work[base_cols + [obs_col, syn_col]].copy()
        subset[obs_col] = pd.to_numeric(subset[obs_col], errors="coerce")
        subset[syn_col] = pd.to_numeric(subset[syn_col], errors="coerce")
        subset = subset.replace([np.inf, -np.inf], np.nan).dropna(subset=[obs_col, syn_col])
        subset = subset[(subset[obs_col] > 0.0) & (subset[syn_col] > 0.0)].copy()
        for bin_label, bin_subset in subset.groupby("passband_norm", dropna=False):
            pieces.append(matched_piece(bin_subset, metric=metric, suffix="obs", bin_label=str(bin_label)))
            pieces.append(matched_piece(bin_subset, metric=metric, suffix="syn", bin_label=str(bin_label)))
    return collapse_and_reference_demean(pd.concat(pieces, ignore_index=True), reference=anomaly_reference) if pieces else pd.DataFrame()


def build_psa_events(df: pd.DataFrame, psa_metrics: list[str], *, anomaly_reference: str = "pooled") -> pd.DataFrame:
    """Build matched observed and synthetic event-station rows for PSA periods."""

    work = df.copy()
    work["hypocentral_distance_km"] = hypocentral_distance(work)
    pieces = []
    base_cols = ["event_id", "station_name", "station_longitude", "station_latitude", "station_component", "target_region_zone", "target_region_edge_distance_km", "mapped_region", "mapped_region_type", "hypocentral_distance_km"]
    for metric in psa_metrics:
        obs_col = f"{metric}_obs"
        syn_col = f"{metric}_syn"
        if obs_col not in work.columns or syn_col not in work.columns:
            continue
        subset = work[base_cols + [obs_col, syn_col]].copy()
        subset[obs_col] = pd.to_numeric(subset[obs_col], errors="coerce")
        subset[syn_col] = pd.to_numeric(subset[syn_col], errors="coerce")
        subset = subset.replace([np.inf, -np.inf], np.nan).dropna(subset=[obs_col, syn_col])
        subset = subset[(subset[obs_col] > 0.0) & (subset[syn_col] > 0.0)].copy()
        subset = subset.drop_duplicates(base_cols + [obs_col, syn_col]).drop(columns=["station_component"])
        if subset.empty:
            continue
        bin_label = metric.replace("PSA_T", "T=") + " s"
        pieces.append(matched_piece(subset, metric=metric, suffix="obs", bin_label=bin_label))
        pieces.append(matched_piece(subset, metric=metric, suffix="syn", bin_label=bin_label))
    return collapse_and_reference_demean(pd.concat(pieces, ignore_index=True), reference=anomaly_reference) if pieces else pd.DataFrame()


def station_summary(events: pd.DataFrame, *, min_events: int) -> pd.DataFrame:
    """Average event-station anomalies to station-level summaries."""

    keys = ["dataset", "metric", "bin", "station_name", "station_longitude", "station_latitude", "target_region_zone", "target_region_edge_distance_km", "mapped_region", "mapped_region_type"]
    summary = (
        events.groupby(keys, dropna=False)
        .agg(value=("value", "mean"), value_raw=("value_raw", "mean"), n_events=("event_id", "nunique"), n_records=("event_id", "size"))
        .reset_index()
    )
    return summary[summary["n_events"] >= int(min_events)].copy()


def bootstrap_contrast(
    events: pd.DataFrame,
    *,
    group_col: str,
    left_values: tuple[str, ...],
    right_values: tuple[str, ...],
    n_bootstrap: int,
    rng: np.random.Generator,
    min_stations_per_group: int = 3,
    statistic: str = "mean",
) -> dict[str, float | int | str]:
    """Calculate a station-level contrast with event bootstrap uncertainty.

    Parameters
    ----------
    events
        Event-station table with ``station_name``, ``event_id``, ``value``, and
        the configured geology class column.
    group_col
        Geology or metadata class column.
    left_values, right_values
        Class labels compared as left minus right.
    n_bootstrap
        Number of event-bootstrap draws.
    rng
        NumPy random generator used for reproducible resampling.
    min_stations_per_group
        Minimum finite station means required on each side.
    statistic
        Station-summary statistic for each side. Choose ``"mean"`` or
        ``"median"``.

    Returns
    -------
    dict
        Effect, confidence interval, p-value, and support counts.
    """

    work = events[events[group_col].isin(left_values + right_values)].copy()
    if work.empty:
        return {}
    pivot = work.pivot_table(index="station_name", columns="event_id", values="value", aggfunc="mean")
    if pivot.shape[1] < 2:
        return {}
    station_classes = work.groupby("station_name", dropna=False)[group_col].first().reindex(pivot.index)
    left_mask = station_classes.isin(left_values).to_numpy()
    right_mask = station_classes.isin(right_values).to_numpy()
    matrix = pivot.to_numpy(dtype=float)
    event_count = matrix.shape[1]
    selected_statistic = str(statistic or "mean").strip().lower()
    if selected_statistic not in {"mean", "median"}:
        raise ValueError("statistic must be 'mean' or 'median'.")

    def calculate(sample: np.ndarray | None = None) -> float:
        values = matrix if sample is None else matrix[:, sample]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            station_values = np.nanmean(values, axis=1)
        left = station_values[left_mask]
        right = station_values[right_mask]
        left = left[np.isfinite(left)]
        right = right[np.isfinite(right)]
        if len(left) < int(min_stations_per_group) or len(right) < int(min_stations_per_group):
            return np.nan
        if selected_statistic == "median":
            return float(np.nanmedian(left) - np.nanmedian(right))
        return float(np.nanmean(left) - np.nanmean(right))

    observed = calculate()
    if not np.isfinite(observed):
        return {}
    boot = []
    for _ in range(int(n_bootstrap)):
        value = calculate(rng.integers(0, event_count, size=event_count))
        if np.isfinite(value):
            boot.append(value)
    boot_arr = np.asarray(boot, dtype=float)
    if boot_arr.size:
        ci_low, ci_high = np.nanpercentile(boot_arr, [2.5, 97.5])
        pvalue = min(1.0, 2.0 * min(float(np.mean(boot_arr <= 0.0)), float(np.mean(boot_arr >= 0.0))))
    else:
        ci_low = np.nan
        ci_high = np.nan
        pvalue = np.nan
    return {
        "effect": observed,
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "bootstrap_p": float(pvalue),
        "n_left_stations": int(np.sum(left_mask)),
        "n_right_stations": int(np.sum(right_mask)),
        "n_events": int(event_count),
        "bootstrap_samples_used": int(boot_arr.size),
        "statistic": selected_statistic,
    }


def bootstrap_contrast_table(
    events: pd.DataFrame,
    *,
    station_metadata: pd.DataFrame | None = None,
    station_col: str = "station",
    event_col: str = "event_id",
    value_col: str = "field_centered",
    group_col: str | None = None,
    left_values: tuple[str, ...] | None = None,
    right_values: tuple[str, ...] | None = None,
    baseline_values: tuple[str, ...] | None = None,
    compare_values: tuple[str, ...] | list[str] | list[tuple[str, ...]] | None = None,
    class_values: tuple[str, ...] | list[str] | None = None,
    min_stations_per_group: int | None = None,
    n_bootstrap: int | None = None,
    random_seed: int | None = None,
    statistic: str | None = None,
    outpath: str | Path | None = None,
) -> pd.DataFrame:
    """Calculate geology contrasts and return a table.

    Parameters
    ----------
    events
        Event-station residual table.
    station_metadata
        Optional station metadata table containing the grouping column.
    station_col, event_col, value_col
        Columns identifying station, event, and residual value.
    group_col
        Metadata class column used for the contrast. When omitted,
        ``spatial.geology_group_column`` from the active config is used.
    left_values, right_values
        Class labels compared as left minus right. These names describe the
        two class sets being compared; they are not map directions. The
        reported effect is ``statistic(left_values) - statistic(right_values)``.
        When omitted, configured geology contrast classes are used.
    baseline_values, compare_values, class_values
        Optional baseline mode. When ``baseline_values`` is provided, one
        contrast row is generated for each comparison class or class group:
        ``comparison - baseline``. ``compare_values`` can be a list of class
        names for separate comparisons or a list of tuples for grouped
        comparisons. ``class_values`` can limit or order the plotted/classes
        considered when ``compare_values`` is omitted.
    min_stations_per_group
        Minimum station count required on each side of the contrast. When
        omitted, the active config value is used.
    n_bootstrap
        Number of event-bootstrap draws. When omitted, the active config value
        is used.
    random_seed
        Seed for reproducible bootstrap sampling. When omitted, the active
        config value is used.
    statistic
        Station-summary statistic for each contrast. Choose ``"mean"`` or
        ``"median"``.
    outpath
        Optional CSV output path.

    Returns
    -------
    pandas.DataFrame
        Contrast table with one row per comparison. The table includes class
        sets, contrast labels, effect direction, percent effects when the field
        is a log2 observed/synthetic ratio, and significance flags.
    """

    settings = spatial_statistics_settings_from_config()
    selected_group_col = group_col or settings.geology_group_column
    selected_left_values = left_values or settings.geology_left_values
    selected_right_values = right_values or settings.geology_right_values
    minimum_group_size = settings.geology_min_stations_per_group if min_stations_per_group is None else int(min_stations_per_group)
    bootstrap_count = settings.geology_bootstrap_samples if n_bootstrap is None else int(n_bootstrap)
    seed = settings.random_seed if random_seed is None else int(random_seed)
    selected_statistic = str(statistic or settings.geology_statistic or "mean").strip().lower()
    if selected_statistic not in {"mean", "median"}:
        raise ValueError("statistic must be 'mean' or 'median'.")
    columns = [
        "group_col",
        "left_values",
        "right_values",
        "comparison_values",
        "baseline_values",
        "contrast_label",
        "effect_direction",
        "value_col",
        "statistic",
        "min_stations_per_group",
        "effect",
        "ci_low",
        "ci_high",
        "percent_effect",
        "percent_ci_low",
        "percent_ci_high",
        "bootstrap_p",
        "significant_95",
        "significant_p05",
        "n_left_stations",
        "n_right_stations",
        "n_comparison_stations",
        "n_baseline_stations",
        "n_events",
        "bootstrap_samples_used",
    ]
    work = events.copy()
    if station_metadata is not None:
        metadata_cols = [station_col, selected_group_col]
        missing_metadata = [column for column in metadata_cols if column not in station_metadata.columns]
        if missing_metadata:
            raise KeyError(f"Missing station metadata columns for bootstrap contrast: {missing_metadata}")
        work = work.merge(station_metadata[metadata_cols].drop_duplicates(subset=[station_col]), on=station_col, how="left")
    required = [station_col, event_col, value_col, selected_group_col]
    missing = [column for column in required if column not in work.columns]
    if missing:
        raise KeyError(f"Missing columns for bootstrap contrast: {missing}")
    rename_map = {station_col: "station_name", event_col: "event_id", value_col: "value"}
    for source_col, target_col in rename_map.items():
        if source_col != target_col and target_col in work.columns:
            work = work.drop(columns=[target_col])
    contrast_events = work.rename(columns=rename_map)
    available_values = _available_group_values(contrast_events[selected_group_col])
    contrast_specs = _contrast_specs(
        selected_left_values=selected_left_values,
        selected_right_values=selected_right_values,
        baseline_values=baseline_values,
        compare_values=compare_values,
        class_values=class_values,
        available_values=available_values,
    )
    rng = np.random.default_rng(seed)
    log2_context = _is_log2_ratio_field(value_col, work)
    rows = []
    for comparison_side, baseline_side in contrast_specs:
        comparison_label = _contrast_values_label(comparison_side)
        baseline_label = _contrast_values_label(baseline_side)
        metadata = {
            "group_col": selected_group_col,
            "left_values": comparison_label,
            "right_values": baseline_label,
            "comparison_values": comparison_label,
            "baseline_values": baseline_label,
            "contrast_label": f"{comparison_label} minus {baseline_label}",
            "effect_direction": f"{selected_statistic}({comparison_label}) - {selected_statistic}({baseline_label})",
            "value_col": value_col,
            "statistic": selected_statistic,
            "min_stations_per_group": int(minimum_group_size),
        }
        result = bootstrap_contrast(
            contrast_events,
            group_col=selected_group_col,
            left_values=comparison_side,
            right_values=baseline_side,
            n_bootstrap=int(bootstrap_count),
            min_stations_per_group=int(minimum_group_size),
            rng=rng,
            statistic=selected_statistic,
        )
        if not result:
            continue
        row = {**metadata, **result}
        row["n_comparison_stations"] = row.get("n_left_stations")
        row["n_baseline_stations"] = row.get("n_right_stations")
        row.update(_effect_interpretation(row, log2_context=log2_context))
        rows.append(row)
    out = pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(columns=columns)
    if outpath is not None:
        path = Path(outpath).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(path, index=False)
    return out


def _contrast_values_label(values: tuple[str, ...] | list[str] | str) -> str:
    """Return a readable label for one side of a geology contrast."""

    if isinstance(values, str):
        return values
    clean = [str(value) for value in values if str(value)]
    return " / ".join(clean) if clean else "unconfigured"


def _as_values_tuple(values: tuple[str, ...] | list[str] | str | None) -> tuple[str, ...]:
    """Return class labels as a tuple of strings."""

    if values is None:
        return tuple()
    if isinstance(values, str):
        return (values,)
    return tuple(str(value) for value in values if str(value))


def _available_group_values(series: pd.Series) -> tuple[str, ...]:
    """Return available class values in stable sorted order."""

    values = [str(value) for value in pd.unique(series.dropna()) if str(value).strip()]
    return tuple(sorted(values))


def _comparison_groups(
    compare_values: tuple[str, ...] | list[str] | list[tuple[str, ...]] | None,
    *,
    baseline_values: tuple[str, ...],
    class_values: tuple[str, ...],
    available_values: tuple[str, ...],
) -> list[tuple[str, ...]]:
    """Resolve baseline-mode comparison groups."""

    if compare_values is None:
        candidates = class_values or available_values
        return [(value,) for value in candidates if value not in set(baseline_values)]
    if isinstance(compare_values, str):
        return [(compare_values,)]
    values = list(compare_values)
    if not values:
        return []
    if all(isinstance(value, (list, tuple, set)) for value in values):
        return [tuple(str(item) for item in value if str(item)) for value in values]
    return [(str(value),) for value in values if str(value)]


def _contrast_specs(
    *,
    selected_left_values: tuple[str, ...],
    selected_right_values: tuple[str, ...],
    baseline_values: tuple[str, ...] | None,
    compare_values: tuple[str, ...] | list[str] | list[tuple[str, ...]] | None,
    class_values: tuple[str, ...] | list[str] | None,
    available_values: tuple[str, ...],
) -> list[tuple[tuple[str, ...], tuple[str, ...]]]:
    """Resolve contrast specifications while preserving two-sided behavior."""

    selected_baseline = _as_values_tuple(baseline_values)
    if not selected_baseline:
        return [(selected_left_values, selected_right_values)]
    selected_classes = _as_values_tuple(class_values)
    comparison_groups = _comparison_groups(
        compare_values,
        baseline_values=selected_baseline,
        class_values=selected_classes,
        available_values=available_values,
    )
    return [(group, selected_baseline) for group in comparison_groups if group]


def _effect_interpretation(row: dict[str, object], *, log2_context: bool) -> dict[str, object]:
    """Build percent and significance columns for one contrast row."""

    effect = _finite_float(row.get("effect"))
    ci_low = _finite_float(row.get("ci_low"))
    ci_high = _finite_float(row.get("ci_high"))
    pvalue = _finite_float(row.get("bootstrap_p"))
    significant_95 = bool(np.isfinite(ci_low) and np.isfinite(ci_high) and ((ci_low > 0.0 and ci_high > 0.0) or (ci_low < 0.0 and ci_high < 0.0)))
    significant_p05 = bool(np.isfinite(pvalue) and pvalue < 0.05)
    out: dict[str, object] = {
        "percent_effect": np.nan,
        "percent_ci_low": np.nan,
        "percent_ci_high": np.nan,
        "significant_95": significant_95,
        "significant_p05": significant_p05,
    }
    if log2_context:
        if np.isfinite(effect):
            out["percent_effect"] = _log2_effect_to_percent(effect)
        if np.isfinite(ci_low):
            out["percent_ci_low"] = _log2_effect_to_percent(ci_low)
        if np.isfinite(ci_high):
            out["percent_ci_high"] = _log2_effect_to_percent(ci_high)
    return out


def _finite_float(value: object) -> float:
    """Return a finite float or NaN."""

    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(numeric) if np.isfinite(numeric) else float("nan")


def _is_log2_ratio_field(value_col: str | None, df: pd.DataFrame) -> bool:
    """Return whether percent conversion is meaningful for a value column."""

    text = str(value_col or "").lower()
    if "log2" in text or "log2_ratio" in text:
        return True
    if text in {"field_value", "field_centered", "mean_centered", "station_mean_centered"} and "field_source" in df.columns:
        source_text = " ".join(str(value).lower() for value in pd.unique(df["field_source"].dropna()))
        return "log2" in source_text
    return False


def _log2_effect_to_percent(effect: float | int | np.floating) -> float:
    """Convert a log2 ratio effect to percent observed/synthetic change."""

    return float((2.0 ** float(effect) - 1.0) * 100.0)


def moran_permutation_test(
    station_values: pd.DataFrame,
    *,
    k: int,
    permutations: int,
    rng: np.random.Generator,
) -> dict[str, float | int]:
    """Compute Moran's I and a permutation p-value from station values."""

    result = compute_global_morans_i(
        station_values.rename(columns={"station_longitude": "lon", "station_latitude": "lat"}),
        value_column="value",
        k=k,
        permutations=permutations,
        random_seed=int(rng.integers(0, 2**31 - 1)),
    )
    if result is None:
        n = int(station_values.dropna(subset=["station_longitude", "station_latitude", "value"]).shape[0])
        return {"moran_i": np.nan, "moran_p": np.nan, "n_stations": n, "neighbors": int(k)}
    return {"moran_i": result.moran_i, "moran_p": result.p_two_sided, "n_stations": result.n, "neighbors": result.k}


def run_geology_spatial_tests(
    events: pd.DataFrame,
    stations: pd.DataFrame,
    *,
    contrasts: list[tuple[str, tuple[str, ...], tuple[str, ...], str]] | None = None,
    bootstrap_samples: int = 500,
    permutation_samples: int = 999,
    moran_neighbors: int = 8,
    seed: int = 20260529,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run contrast and Moran tests for each dataset, metric, and bin."""

    rng = np.random.default_rng(int(seed))
    contrast_rows = []
    moran_rows = []
    contrast_specs = contrasts or DEFAULT_GEOLOGY_CONTRASTS
    grouped_stations = {(dataset, metric, bin_label): frame for (dataset, metric, bin_label), frame in stations.groupby(["dataset", "metric", "bin"], dropna=False)}
    for (dataset, metric, bin_label), event_group in events.groupby(["dataset", "metric", "bin"], dropna=False):
        station_group = grouped_stations.get((dataset, metric, bin_label), pd.DataFrame())
        if station_group.empty:
            continue
        try:
            zone_groups = [frame["value"].dropna().to_numpy() for _zone, frame in station_group.groupby("target_region_zone") if len(frame) >= 5]
            kruskal_p = float(kruskal(*zone_groups).pvalue) if len(zone_groups) >= 2 else np.nan
        except Exception:
            kruskal_p = np.nan
        moran = moran_permutation_test(station_group, k=moran_neighbors, permutations=permutation_samples, rng=rng)
        moran_rows.append({"dataset": dataset, "metric": metric, "bin": bin_label, "metric_label": metric_label(metric), "kruskal_target_region_zone_p": kruskal_p, **moran})
        for contrast_name, left, right, group_col in contrast_specs:
            result = bootstrap_contrast(event_group, group_col=group_col, left_values=left, right_values=right, n_bootstrap=bootstrap_samples, rng=rng)
            if result:
                contrast_rows.append({"dataset": dataset, "metric": metric, "bin": bin_label, "metric_label": metric_label(metric), "contrast": contrast_name, "group_col": group_col, "left_values": ",".join(left), "right_values": ",".join(right), **result})
    return pd.DataFrame(contrast_rows), pd.DataFrame(moran_rows)
