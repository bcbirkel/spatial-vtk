"""Station residual-feature clustering and REDCAP regionalization."""

from __future__ import annotations

from dataclasses import dataclass
import heapq
import math

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from spatial_vtk.spatial.calculate._common import (
    DEFAULT_CLUSTER_MAX_K,
    DEFAULT_CLUSTER_MIN_K,
    DEFAULT_CLUSTER_MIN_METRICS_PER_STATION,
    haversine_km,
    metric_sort_key,
    safe_token,
)
from spatial_vtk.spatial.calculate.settings import spatial_statistics_settings_from_config


@dataclass(frozen=True)
class ClusterSolutionSummary:
    """Container for one residual-clustering solution."""

    n_clusters: int
    silhouette: float
    inertia: float
    n_samples: int
    n_features: int


def build_station_event_fingerprint(
    centered_df: pd.DataFrame,
    station_df: pd.DataFrame,
    *,
    min_events_per_station: int = 3,
) -> pd.DataFrame:
    """Build a station-by-event feature matrix for one metric.

    Parameters
    ----------
    centered_df
        Event-centered residual field.
    station_df
        Station-bias table.
    min_events_per_station
        Minimum event support per station.

    Returns
    -------
    pandas.DataFrame
        Station metadata plus event feature columns.
    """

    if centered_df.empty or station_df.empty:
        return pd.DataFrame(columns=["station", "lat", "lon", "events_present"])
    pivot = centered_df.pivot_table(index="station", columns="event_id", values="field_centered", aggfunc="mean")
    if pivot.empty:
        return pd.DataFrame(columns=["station", "lat", "lon", "events_present"])
    event_order = sorted([str(col) for col in pivot.columns], key=lambda token: token.lower())
    pivot = pivot[event_order].rename(columns={name: f"event::{safe_token(name)}" for name in event_order})
    pivot["events_present"] = pivot.notna().sum(axis=1)
    pivot = pivot.loc[pivot["events_present"] >= int(min_events_per_station)].copy()
    if pivot.empty:
        return pd.DataFrame(columns=["station", "lat", "lon", "events_present"])
    meta = station_df[["station", "lat", "lon", "mean_centered", "n_events"]].rename(
        columns={"mean_centered": "station_mean_centered", "n_events": "station_bias_events"}
    )
    out = meta.merge(pivot.reset_index(), on="station", how="inner")
    out["events_present"] = pd.to_numeric(out["events_present"], errors="coerce").fillna(0).astype(int)
    return out


def build_joint_metric_fingerprint(
    station_bias_lookup: dict[str, pd.DataFrame],
    *,
    min_metrics_per_station: int = DEFAULT_CLUSTER_MIN_METRICS_PER_STATION,
) -> pd.DataFrame:
    """Build a station-by-metric feature matrix from station-bias summaries."""

    rows = []
    for metric_name, station_df in station_bias_lookup.items():
        if station_df.empty:
            continue
        sub = station_df[["station", "lat", "lon", "mean_centered", "n_events"]].copy()
        sub["metric"] = str(metric_name)
        sub.rename(columns={"mean_centered": "metric_mean_centered", "n_events": "metric_events"}, inplace=True)
        rows.append(sub)
    if not rows:
        return pd.DataFrame(columns=["station", "lat", "lon", "metrics_present"])
    long_df = pd.concat(rows, ignore_index=True)
    metric_order = sorted(long_df["metric"].dropna().astype(str).unique().tolist(), key=metric_sort_key)
    wide = long_df.pivot_table(index="station", columns="metric", values="metric_mean_centered", aggfunc="mean").reindex(columns=metric_order)
    if wide.empty:
        return pd.DataFrame(columns=["station", "lat", "lon", "metrics_present"])
    wide["metrics_present"] = wide.notna().sum(axis=1)
    wide = wide.loc[wide["metrics_present"] >= int(min_metrics_per_station)].copy()
    if wide.empty:
        return pd.DataFrame(columns=["station", "lat", "lon", "metrics_present"])
    meta = long_df.groupby("station", as_index=False).agg(lat=("lat", "mean"), lon=("lon", "mean"))
    out = meta.merge(wide.reset_index(), on="station", how="inner")
    out["metrics_present"] = pd.to_numeric(out["metrics_present"], errors="coerce").fillna(0).astype(int)
    return out


def summarize_joint_station_bias(joint_fingerprint_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize one cross-metric station-bias value for each station."""

    columns = ["station", "lat", "lon", "n_events", "mean_centered", "median_centered", "std_centered", "sem_centered", "abs_mean_centered", "bias_zscore", "metrics_present"]
    if joint_fingerprint_df.empty:
        return pd.DataFrame(columns=columns)
    metadata_cols = {"station", "lat", "lon", "metrics_present"}
    feature_cols = [col for col in joint_fingerprint_df.columns if col not in metadata_cols]
    if not feature_cols:
        return pd.DataFrame(columns=columns)
    values = joint_fingerprint_df[feature_cols].apply(pd.to_numeric, errors="coerce")
    out = joint_fingerprint_df[["station", "lat", "lon", "metrics_present"]].copy()
    out["n_events"] = pd.to_numeric(out["metrics_present"], errors="coerce").fillna(0).astype(int)
    out["mean_centered"] = values.mean(axis=1, skipna=True)
    out["median_centered"] = values.median(axis=1, skipna=True)
    out["std_centered"] = values.std(axis=1, skipna=True)
    out["sem_centered"] = out["std_centered"] / np.sqrt(out["n_events"].clip(lower=1))
    out["abs_mean_centered"] = np.abs(out["mean_centered"])
    out["bias_zscore"] = out["mean_centered"] / out["sem_centered"]
    out.replace([np.inf, -np.inf], np.nan, inplace=True)
    out.dropna(subset=["mean_centered"], inplace=True)
    return out.sort_values(["abs_mean_centered", "station"], ascending=[False, True])[columns]


def _prepare_clustering_inputs(
    feature_df: pd.DataFrame,
    *,
    metadata_columns: tuple[str, ...] = ("station", "lat", "lon"),
    min_nonmissing_per_row: int = 1,
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, list[str]]:
    """Filter, impute, and standardize a station feature matrix."""

    if feature_df.empty:
        return pd.DataFrame(), pd.DataFrame(), np.empty((0, 0)), []
    metadata_cols = [col for col in metadata_columns if col in feature_df.columns]
    reserved = {"events_present", "metrics_present", "station_bias_events", "metric_events"}
    feature_columns = [col for col in feature_df.columns if col not in metadata_cols and col not in reserved]
    if not feature_columns:
        return pd.DataFrame(), pd.DataFrame(), np.empty((0, 0)), []
    work = feature_df.copy()
    for col in feature_columns:
        work[col] = pd.to_numeric(work[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
    valid_features = []
    for col in feature_columns:
        values = work[col].to_numpy(dtype=float)
        finite_count = int(np.isfinite(values).sum())
        if finite_count >= 2 and float(np.nanstd(values, ddof=1)) > 0.0:
            valid_features.append(col)
    if not valid_features:
        return pd.DataFrame(), pd.DataFrame(), np.empty((0, 0)), []
    work["features_present"] = work[valid_features].notna().sum(axis=1)
    work = work.loc[work["features_present"] >= int(min_nonmissing_per_row)].copy()
    if work.empty:
        return pd.DataFrame(), pd.DataFrame(), np.empty((0, 0)), []
    raw_features = work[valid_features].copy()
    matrix = raw_features.to_numpy(dtype=float)
    col_means = np.nanmean(matrix, axis=0)
    col_means = np.where(np.isfinite(col_means), col_means, 0.0)
    imputed = np.where(np.isfinite(matrix), matrix, col_means[None, :])
    standardized = StandardScaler().fit_transform(imputed)
    return work, raw_features, standardized, valid_features


def _relabel_clusters_by_spatial_centroid(labels: np.ndarray, metadata_df: pd.DataFrame) -> np.ndarray:
    """Relabel clusters by centroid location for stable public output."""

    if len(labels) == 0:
        return labels.astype(int)
    if metadata_df.empty or "lat" not in metadata_df.columns or "lon" not in metadata_df.columns:
        unique = sorted(np.unique(labels).tolist())
        mapping = {int(old): int(new) for new, old in enumerate(unique)}
        return np.asarray([mapping[int(value)] for value in labels], dtype=int)
    tmp = pd.DataFrame({"cluster_id": np.asarray(labels, dtype=int), "lat": pd.to_numeric(metadata_df["lat"], errors="coerce"), "lon": pd.to_numeric(metadata_df["lon"], errors="coerce")})
    order = tmp.groupby("cluster_id", as_index=False).agg(lat=("lat", "mean"), lon=("lon", "mean")).sort_values(["lat", "lon", "cluster_id"])
    mapping = {int(old): int(new) for new, old in enumerate(order["cluster_id"].tolist())}
    return np.asarray([mapping[int(value)] for value in labels], dtype=int)


def summarize_cluster_assignments(assignments_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize station counts and spatial spread for cluster assignments."""

    columns = ["cluster_id", "cluster_name", "station_count", "mean_lat", "mean_lon", "mean_distance_to_centroid_km", "max_distance_to_centroid_km", "mean_features_present"]
    if assignments_df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for cluster_id, sub in assignments_df.groupby("cluster_id", sort=True):
        mean_lat = float(pd.to_numeric(sub["lat"], errors="coerce").mean())
        mean_lon = float(pd.to_numeric(sub["lon"], errors="coerce").mean())
        dist = haversine_km(pd.to_numeric(sub["lat"], errors="coerce"), pd.to_numeric(sub["lon"], errors="coerce"), mean_lat, mean_lon)
        rows.append(
            {
                "cluster_id": int(cluster_id),
                "cluster_name": str(sub["cluster_name"].iloc[0]) if "cluster_name" in sub.columns else f"cluster_{int(cluster_id):02d}",
                "station_count": int(len(sub)),
                "mean_lat": mean_lat,
                "mean_lon": mean_lon,
                "mean_distance_to_centroid_km": float(np.nanmean(dist)) if len(dist) else np.nan,
                "max_distance_to_centroid_km": float(np.nanmax(dist)) if len(dist) else np.nan,
                "mean_features_present": float(pd.to_numeric(sub.get("feature_nonmissing_count"), errors="coerce").mean()) if "feature_nonmissing_count" in sub.columns else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values("cluster_id")[columns]


def summarize_cluster_feature_values(assignments_df: pd.DataFrame, raw_feature_df: pd.DataFrame, *, feature_columns: list[str]) -> pd.DataFrame:
    """Summarize raw feature values within each cluster."""

    columns = ["cluster_id", "cluster_name", "feature", "feature_mean", "feature_median", "feature_std", "feature_nonmissing_count", "station_count"]
    if assignments_df.empty or raw_feature_df.empty or not feature_columns:
        return pd.DataFrame(columns=columns)
    rows = []
    for cluster_id, sub in assignments_df.groupby("cluster_id", sort=True):
        feature_subset = raw_feature_df.loc[sub.index, feature_columns]
        for feature in feature_columns:
            values = pd.to_numeric(feature_subset[feature], errors="coerce")
            rows.append(
                {
                    "cluster_id": int(cluster_id),
                    "cluster_name": str(sub["cluster_name"].iloc[0]),
                    "feature": str(feature),
                    "feature_mean": float(values.mean()) if values.notna().any() else np.nan,
                    "feature_median": float(values.median()) if values.notna().any() else np.nan,
                    "feature_std": float(values.std(ddof=1)) if values.notna().sum() > 1 else np.nan,
                    "feature_nonmissing_count": int(values.notna().sum()),
                    "station_count": int(len(sub)),
                }
            )
    return pd.DataFrame(rows).sort_values(["cluster_id", "feature"])[columns]


def run_residual_feature_clustering(
    feature_df: pd.DataFrame,
    *,
    cluster_min_k: int | None = None,
    cluster_max_k: int | None = None,
    min_nonmissing_per_row: int = 1,
    random_seed: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, ClusterSolutionSummary | None, list[str]]:
    """Cluster station residual fingerprints with K-means and silhouette selection."""

    settings = spatial_statistics_settings_from_config()
    min_k_setting = DEFAULT_CLUSTER_MIN_K if cluster_min_k is None else cluster_min_k
    max_k_setting = DEFAULT_CLUSTER_MAX_K if cluster_max_k is None else cluster_max_k
    if cluster_min_k is None:
        min_k_setting = settings.cluster_min_k
    if cluster_max_k is None:
        max_k_setting = settings.cluster_max_k
    seed = settings.random_seed if random_seed is None else int(random_seed)
    prepared_df, raw_feature_df, standardized, valid_features = _prepare_clustering_inputs(feature_df, min_nonmissing_per_row=min_nonmissing_per_row)
    empty_scores = pd.DataFrame(columns=["n_clusters", "silhouette", "inertia", "n_samples", "n_features"])
    if prepared_df.empty or standardized.size == 0 or not valid_features:
        return pd.DataFrame(), empty_scores, pd.DataFrame(), pd.DataFrame(), None, []
    n_samples = len(prepared_df)
    min_k = max(2, int(min_k_setting))
    max_k = min(int(max_k_setting), n_samples - 1)
    if max_k < min_k:
        return pd.DataFrame(), empty_scores, pd.DataFrame(), pd.DataFrame(), None, valid_features
    score_rows = []
    best_summary: ClusterSolutionSummary | None = None
    best_labels: np.ndarray | None = None
    for n_clusters in range(min_k, max_k + 1):
        model = KMeans(n_clusters=n_clusters, random_state=int(seed) + n_clusters * 17, n_init=20)
        labels = model.fit_predict(standardized)
        labels = _relabel_clusters_by_spatial_centroid(labels, prepared_df[["lat", "lon"]])
        score = float(silhouette_score(standardized, labels)) if len(set(labels)) > 1 else 0.0
        summary = ClusterSolutionSummary(n_clusters=n_clusters, silhouette=score, inertia=float(model.inertia_), n_samples=n_samples, n_features=len(valid_features))
        score_rows.append(summary.__dict__)
        if best_summary is None or score > best_summary.silhouette + 1e-12 or (abs(score - best_summary.silhouette) <= 1e-12 and n_clusters < best_summary.n_clusters):
            best_summary = summary
            best_labels = labels.copy()
    score_df = pd.DataFrame(score_rows)
    if best_summary is None or best_labels is None:
        return pd.DataFrame(), score_df, pd.DataFrame(), pd.DataFrame(), None, valid_features
    assignments = prepared_df[["station", "lat", "lon"]].copy()
    assignments["feature_nonmissing_count"] = pd.to_numeric(prepared_df["features_present"], errors="coerce").fillna(0).astype(int)
    assignments["cluster_id"] = best_labels.astype(int)
    assignments["cluster_name"] = [f"cluster_{int(value):02d}" for value in assignments["cluster_id"]]
    assignments["cluster_k"] = int(best_summary.n_clusters)
    assignments["best_silhouette"] = float(best_summary.silhouette)
    assignments["cluster_feature_count"] = int(best_summary.n_features)
    feature_summary_df = summarize_cluster_feature_values(assignments, raw_feature_df, feature_columns=valid_features)
    cluster_summary_df = summarize_cluster_assignments(assignments)
    return assignments, score_df, feature_summary_df, cluster_summary_df, best_summary, valid_features


def connected_components(adjacency: dict[int, set[int]]) -> list[list[int]]:
    """Return connected components from an undirected adjacency dictionary."""

    unseen = set(adjacency)
    components = []
    while unseen:
        root = unseen.pop()
        stack = [root]
        component = {root}
        while stack:
            node = stack.pop()
            for neighbor in adjacency[node]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    component.add(neighbor)
                    stack.append(neighbor)
        components.append(sorted(component))
    return components


def build_spatial_neighbor_graph(coords: np.ndarray, *, n_neighbors: int) -> dict[int, set[int]]:
    """Build a connected nearest-neighbor graph for REDCAP constraints."""

    coords = np.asarray(coords, dtype=float)
    n_stations = int(coords.shape[0])
    if n_stations < 2:
        raise ValueError("Need at least two stations to build a REDCAP graph.")
    n_query = min(n_stations, max(2, int(n_neighbors) + 1))
    nn = NearestNeighbors(n_neighbors=n_query).fit(coords)
    _dist, indices = nn.kneighbors(coords)
    adjacency = {idx: set() for idx in range(n_stations)}
    for idx, row in enumerate(indices):
        for neighbor in row:
            neighbor = int(neighbor)
            if neighbor != idx:
                adjacency[idx].add(neighbor)
                adjacency[neighbor].add(idx)
    components = connected_components(adjacency)
    while len(components) > 1:
        best_pair = None
        best_distance = float("inf")
        for left_index, left_component in enumerate(components[:-1]):
            for right_component in components[left_index + 1 :]:
                distances = np.sum((coords[left_component][:, None, :] - coords[right_component][None, :, :]) ** 2, axis=2)
                flat_index = int(np.argmin(distances))
                left_pos, right_pos = np.unravel_index(flat_index, distances.shape)
                distance = float(distances[left_pos, right_pos])
                if distance < best_distance:
                    best_distance = distance
                    best_pair = (left_component[left_pos], right_component[right_pos])
        if best_pair is None:
            break
        left, right = best_pair
        adjacency[left].add(right)
        adjacency[right].add(left)
        components = connected_components(adjacency)
    return adjacency


def redcap_merge_cost(left: dict[str, object], right: dict[str, object]) -> float:
    """Return Ward-style merge cost for two candidate REDCAP regions."""

    n_left = int(left["n"])
    n_right = int(right["n"])
    mean_left = np.asarray(left["mean"], dtype=float)
    mean_right = np.asarray(right["mean"], dtype=float)
    return float((n_left * n_right / (n_left + n_right)) * np.sum((mean_left - mean_right) ** 2))


def redcap_labels(regions: dict[int, dict[str, object]], n_stations: int) -> np.ndarray:
    """Convert active REDCAP regions into a station-label vector."""

    labels = np.zeros(n_stations, dtype=int)
    for label, region_id in enumerate(sorted(regions), start=1):
        for member in regions[region_id]["members"]:
            labels[int(member)] = label
    return labels


def assign_redcap_clusters(
    station_summary: pd.DataFrame,
    *,
    value_col: str = "avg_observed_metric_distance_scaled_event_demeaned",
    min_k: int = 2,
    max_k: int = 8,
    n_neighbors: int = 2,
    location_weight: float = 0.1,
    residual_weight: float = 2.0,
    lon_col: str = "station_longitude",
    lat_col: str = "station_latitude",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Assign spatially constrained REDCAP clusters to station residuals.

    Parameters
    ----------
    station_summary
        Station-level table with coordinate and residual columns.
    value_col
        Residual or metric-anomaly value used in the regionalization.
    min_k, max_k
        Candidate regional cluster-count range.
    n_neighbors
        Spatial neighbors used to build the constraint graph.
    location_weight, residual_weight
        Weights applied to standardized coordinate and residual features.
    lon_col, lat_col
        Coordinate column names.

    Returns
    -------
    tuple of pandas.DataFrame
        Clustered station table and candidate-score table.
    """

    needed = [lon_col, lat_col, value_col]
    work = station_summary.replace([np.inf, -np.inf], np.nan).dropna(subset=needed).copy()
    if len(work) < max(3, int(min_k) + 1):
        raise ValueError(f"Need at least {max(3, int(min_k) + 1)} stations for REDCAP; found {len(work)}.")
    coords = work[[lon_col, lat_col]].to_numpy(dtype=float)
    raw_features = work[[lon_col, lat_col, value_col]].to_numpy(dtype=float)
    features = StandardScaler().fit_transform(raw_features)
    features[:, :2] *= max(0.0, float(location_weight))
    features[:, 2] *= max(0.0, float(residual_weight))
    if not np.any(np.std(features, axis=0) > 0.0):
        raise ValueError("REDCAP features have no variance after scaling.")
    n_stations = len(work)
    candidate_max = min(int(max_k), n_stations - 1)
    candidate_min = max(2, int(min_k))
    if candidate_min > candidate_max:
        candidate_min = 2
        candidate_max = max(2, min(3, n_stations - 1))
    station_graph = build_spatial_neighbor_graph(coords, n_neighbors=int(n_neighbors))
    regions: dict[int, dict[str, object]] = {idx: {"members": {idx}, "n": 1, "mean": features[idx].copy()} for idx in range(n_stations)}
    region_graph: dict[int, set[int]] = {idx: set(neighbors) for idx, neighbors in station_graph.items()}
    heap: list[tuple[float, int, int, int]] = []
    sequence = 0
    for left, neighbors in region_graph.items():
        for right in neighbors:
            if left < right:
                heapq.heappush(heap, (redcap_merge_cost(regions[left], regions[right]), sequence, left, right))
                sequence += 1
    snapshots: dict[int, np.ndarray] = {}
    active_count = n_stations
    if active_count <= candidate_max:
        snapshots[active_count] = redcap_labels(regions, n_stations)
    next_region_id = n_stations
    while active_count > candidate_min and heap:
        _cost, _seq, left, right = heapq.heappop(heap)
        if left not in regions or right not in regions or right not in region_graph.get(left, set()):
            continue
        left_region = regions.pop(left)
        right_region = regions.pop(right)
        left_neighbors = region_graph.pop(left)
        right_neighbors = region_graph.pop(right)
        merged_neighbors = (left_neighbors | right_neighbors) - {left, right}
        for neighbor in left_neighbors | right_neighbors:
            if neighbor in region_graph:
                region_graph[neighbor].discard(left)
                region_graph[neighbor].discard(right)
        merged_n = int(left_region["n"]) + int(right_region["n"])
        merged_mean = (int(left_region["n"]) * np.asarray(left_region["mean"], dtype=float) + int(right_region["n"]) * np.asarray(right_region["mean"], dtype=float)) / merged_n
        new_id = next_region_id
        next_region_id += 1
        regions[new_id] = {"members": set(left_region["members"]) | set(right_region["members"]), "n": merged_n, "mean": merged_mean}
        region_graph[new_id] = set()
        for neighbor in merged_neighbors:
            if neighbor not in regions:
                continue
            region_graph[new_id].add(neighbor)
            region_graph[neighbor].add(new_id)
            heapq.heappush(heap, (redcap_merge_cost(regions[new_id], regions[neighbor]), sequence, new_id, neighbor))
            sequence += 1
        active_count -= 1
        if candidate_min <= active_count <= candidate_max:
            snapshots[active_count] = redcap_labels(regions, n_stations)
    records = []
    best_k = None
    best_score = -np.inf
    best_labels = None
    for k in range(candidate_min, candidate_max + 1):
        labels = snapshots.get(k)
        score = float("nan") if labels is None or len(set(labels)) < 2 else float(silhouette_score(features, labels))
        records.append({"k": int(k), "silhouette_score": score, "n_neighbors": int(n_neighbors), "location_weight": float(location_weight), "residual_weight": float(residual_weight)})
        if math.isfinite(score) and score > best_score:
            best_k = int(k)
            best_score = score
            best_labels = labels
    if best_labels is None:
        best_k = min(snapshots) if snapshots else len(regions)
        best_labels = snapshots.get(best_k, redcap_labels(regions, n_stations))
        best_score = float("nan")
    work["cluster"] = np.asarray(best_labels, dtype=int)
    centers = work.groupby("cluster", dropna=False)[value_col].mean().sort_values().reset_index().reset_index()
    order = {int(row["cluster"]): int(row["index"]) + 1 for _, row in centers.iterrows()}
    work["cluster"] = work["cluster"].map(order).astype(int)
    work["selected_k"] = int(best_k)
    work["selected_silhouette_score"] = best_score
    work["redcap_neighbors"] = int(n_neighbors)
    work["redcap_location_weight"] = float(location_weight)
    work["redcap_residual_weight"] = float(residual_weight)
    scores = pd.DataFrame.from_records(records)
    scores["selected"] = scores["k"] == int(best_k)
    return work, scores
