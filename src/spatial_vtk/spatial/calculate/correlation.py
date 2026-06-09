"""Spatial autocorrelation, distance-bin summaries, and holdout diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from sklearn.neighbors import NearestNeighbors

from spatial_vtk.spatial.calculate._common import (
    DEFAULT_BIN_WIDTH_KM,
    DEFAULT_BLOCK_DISTANCE_POWER,
    DEFAULT_BLOCK_PREDICTION_K,
    DEFAULT_BLOCK_SIZE_KM,
    DEFAULT_DIRECTION_BIN_WIDTH_DEG,
    DEFAULT_MAX_DISTANCE_KM,
    DEFAULT_MAX_PAIRS_PER_EVENT,
    haversine_km,
    lonlat_to_xy_km,
)
from spatial_vtk.spatial.calculate.prepare_stats import center_field_by_reference_mask, summarize_station_bias
from spatial_vtk.spatial.calculate.settings import spatial_statistics_settings_from_config


@dataclass(frozen=True)
class MoranResult:
    """Container for global Moran's I output."""

    n: int
    k: int
    moran_i: float
    p_two_sided: float
    permutations: int


@dataclass(frozen=True)
class CorrelationLengthFit:
    """Container for exponential correlation-length estimates."""

    correlation_length_km: float
    effective_range_km: float
    method: str
    n_bins_used: int


def _compute_moran_i_from_weights(values: np.ndarray, neighbors: np.ndarray, weights: np.ndarray) -> float:
    """Compute global Moran's I from a fixed neighbor graph.

    Parameters
    ----------
    values
        Station values.
    neighbors
        Integer neighbor index array.
    weights
        Neighbor weights with the same shape as ``neighbors``.

    Returns
    -------
    float
        Moran's I statistic.
    """

    x = np.asarray(values, dtype=float)
    x = x - np.nanmean(x)
    denom = float(np.dot(x, x))
    if not np.isfinite(denom) or denom <= 0.0:
        return float("nan")
    weighted = np.sum(weights * x[:, None] * x[neighbors])
    weight_sum = float(np.sum(weights))
    n = float(len(x))
    if weight_sum <= 0.0 or n <= 1.0:
        return float("nan")
    return (n / weight_sum) * (weighted / denom)


def compute_global_morans_i(
    station_df: pd.DataFrame,
    *,
    value_column: str = "mean_centered",
    lat_column: str = "lat",
    lon_column: str = "lon",
    k: int | None = None,
    permutations: int | None = None,
    random_seed: int | None = None,
) -> MoranResult | None:
    """Compute global Moran's I for station-level values.

    Parameters
    ----------
    station_df
        Station table with coordinates and a value column.
    value_column, lat_column, lon_column
        Column names used for values and coordinates.
    k
        Number of nearest spatial neighbors.
    permutations
        Number of random permutations for a two-sided p-value.
    random_seed
        Seed for reproducible permutation tests.

    Returns
    -------
    MoranResult or None
        Moran's I result, or None when too few valid stations exist.
    """

    settings = spatial_statistics_settings_from_config()
    k_value = settings.moran_neighbors if k is None else int(k)
    permutation_count = settings.moran_permutations if permutations is None else int(permutations)
    seed = settings.random_seed if random_seed is None else int(random_seed)
    if station_df.empty:
        return None
    work = station_df.dropna(subset=[lat_column, lon_column, value_column]).copy()
    n = len(work)
    if n < 4:
        return None
    k_use = max(1, min(int(k_value), n - 1))
    x_km, y_km = lonlat_to_xy_km(work[lat_column].to_numpy(dtype=float), work[lon_column].to_numpy(dtype=float))
    coords = np.column_stack([x_km, y_km])
    nn = NearestNeighbors(n_neighbors=k_use + 1).fit(coords)
    _dist, indices = nn.kneighbors(coords)
    neighbors = np.asarray(indices[:, 1:], dtype=int)
    weights = np.full((n, k_use), 1.0 / float(k_use), dtype=float)
    values = work[value_column].to_numpy(dtype=float)
    observed = _compute_moran_i_from_weights(values, neighbors, weights)
    if not np.isfinite(observed):
        return None
    rng = np.random.default_rng(seed)
    null = np.asarray([_compute_moran_i_from_weights(rng.permutation(values), neighbors, weights) for _ in range(int(permutation_count))], dtype=float)
    null = null[np.isfinite(null)]
    p_two_sided = float((1.0 + np.sum(np.abs(null) >= abs(observed))) / (1.0 + len(null))) if len(null) else float("nan")
    return MoranResult(n=n, k=k_use, moran_i=float(observed), p_two_sided=p_two_sided, permutations=int(permutation_count))


def moran_result_to_frame(result: MoranResult | None) -> pd.DataFrame:
    """Convert one Moran's I result into a dataframe.

    Parameters
    ----------
    result
        Output from ``compute_global_morans_i``.

    Returns
    -------
    pandas.DataFrame
        One-row Moran summary, or an empty table with the expected columns.
    """

    columns = ["n", "k", "moran_i", "p_two_sided", "permutations"]
    if result is None:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(
        [
            {
                "n": int(result.n),
                "k": int(result.k),
                "moran_i": float(result.moran_i),
                "p_two_sided": float(result.p_two_sided),
                "permutations": int(result.permutations),
            }
        ],
        columns=columns,
    )


def _sample_pair_indices(n_points: int, max_pairs: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Return a manageable set of unique point-pair indices."""

    total_pairs = n_points * (n_points - 1) // 2
    if total_pairs <= 0:
        return np.empty(0, dtype=int), np.empty(0, dtype=int)
    if total_pairs <= int(max_pairs):
        return np.triu_indices(n_points, k=1)
    target = int(max_pairs)
    collected: set[tuple[int, int]] = set()
    while len(collected) < target:
        need = max(target - len(collected), 1)
        i = rng.integers(0, n_points, size=need * 3)
        j = rng.integers(0, n_points, size=need * 3)
        keep = i != j
        lo = np.minimum(i[keep], j[keep])
        hi = np.maximum(i[keep], j[keep])
        for left, right in zip(lo.tolist(), hi.tolist()):
            collected.add((left, right))
            if len(collected) >= target:
                break
    pairs = np.asarray(sorted(collected), dtype=int)
    return pairs[:, 0], pairs[:, 1]


def _orientation_pairs_deg(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Return undirected pair orientation in degrees over ``[0, 180)``."""

    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    dlon_rad = np.radians(lon2 - lon1)
    y = np.sin(dlon_rad) * np.cos(lat2_rad)
    x = np.cos(lat1_rad) * np.sin(lat2_rad) - np.sin(lat1_rad) * np.cos(lat2_rad) * np.cos(dlon_rad)
    bearing = (np.degrees(np.arctan2(y, x)) + 360.0) % 360.0
    return np.mod(bearing, 180.0)


def _direction_bin_centers(direction_bin_width_deg: float) -> np.ndarray:
    """Return direction-sector centers over the undirected domain."""

    width = float(direction_bin_width_deg)
    if not np.isfinite(width) or width <= 0.0 or width >= 180.0:
        raise ValueError("direction_bin_width_deg must lie in (0, 180).")
    centers = np.arange(0.0, 180.0, width, dtype=float)
    if centers.size < 2:
        raise ValueError("direction_bin_width_deg produced fewer than two sectors.")
    return centers


def _assign_direction_bins(orientation_deg: np.ndarray, direction_bin_width_deg: float) -> np.ndarray:
    """Assign undirected orientations to centered sectors."""

    width = float(direction_bin_width_deg)
    shifted = np.mod(np.asarray(orientation_deg, dtype=float) + 0.5 * width, 180.0)
    return np.floor(shifted / width).astype(int)


def _direction_label(center_deg: float, width_deg: float) -> str:
    """Build one human-readable direction-sector label."""

    center = float(center_deg) % 180.0
    width = float(width_deg)
    if math.isclose(width, 45.0, abs_tol=1e-6):
        labels = {0.0: "N-S", 45.0: "NE-SW", 90.0: "E-W", 135.0: "NW-SE"}
        for key, label in labels.items():
            if math.isclose(center, key, abs_tol=1e-6):
                return label
    if math.isclose(width, 90.0, abs_tol=1e-6):
        return "N-S" if math.isclose(center, 0.0, abs_tol=1e-6) else "E-W"
    return f"{center:g} deg"


def build_pair_summaries(
    centered_df: pd.DataFrame,
    *,
    bin_width_km: float = DEFAULT_BIN_WIDTH_KM,
    max_distance_km: float = DEFAULT_MAX_DISTANCE_KM,
    max_pairs_per_event: int = DEFAULT_MAX_PAIRS_PER_EVENT,
    direction_bin_width_deg: float = DEFAULT_DIRECTION_BIN_WIDTH_DEG,
    random_seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build isotropic and direction-resolved pair summaries.

    Parameters
    ----------
    centered_df
        Event-centered field table with ``field_centered`` and ``field_z``.
    bin_width_km, max_distance_km
        Distance-bin configuration.
    max_pairs_per_event
        Maximum station pairs sampled for each event.
    direction_bin_width_deg
        Direction-sector width for anisotropy summaries.
    random_seed
        Seed for pair sampling.

    Returns
    -------
    tuple of pandas.DataFrame
        Isotropic distance-bin summary and directional distance-bin summary.
    """

    bin_width = float(bin_width_km)
    max_distance = float(max_distance_km)
    if bin_width <= 0.0 or max_distance <= 0.0:
        raise ValueError("bin_width_km and max_distance_km must be positive.")
    n_bins = int(math.ceil(max_distance / bin_width))
    direction_centers = _direction_bin_centers(direction_bin_width_deg)
    n_dirs = len(direction_centers)
    sum_corr = np.zeros(n_bins)
    sum_semivar = np.zeros(n_bins)
    count_pairs = np.zeros(n_bins, dtype=int)
    count_events = np.zeros(n_bins, dtype=int)
    sum_corr_dir = np.zeros((n_dirs, n_bins))
    sum_semivar_dir = np.zeros((n_dirs, n_bins))
    count_pairs_dir = np.zeros((n_dirs, n_bins), dtype=int)
    count_events_dir = np.zeros((n_dirs, n_bins), dtype=int)
    rng = np.random.default_rng(random_seed)

    for _event_id, sub in centered_df.groupby("event_id"):
        event_df = sub.drop_duplicates(subset=["station"]).copy()
        event_df.dropna(subset=["field_centered", "field_z", "lat", "lon"], inplace=True)
        if len(event_df) < 3:
            continue
        if float(np.nanstd(event_df["field_centered"].to_numpy(dtype=float), ddof=1)) <= 0.0:
            continue
        i_idx, j_idx = _sample_pair_indices(len(event_df), int(max_pairs_per_event), rng)
        if i_idx.size == 0:
            continue
        lat = event_df["lat"].to_numpy(dtype=float)
        lon = event_df["lon"].to_numpy(dtype=float)
        z = event_df["field_z"].to_numpy(dtype=float)
        centered = event_df["field_centered"].to_numpy(dtype=float)
        distances = haversine_km(lat[i_idx], lon[i_idx], lat[j_idx], lon[j_idx])
        orientations = _orientation_pairs_deg(lat[i_idx], lon[i_idx], lat[j_idx], lon[j_idx])
        valid = np.isfinite(distances) & np.isfinite(orientations) & (distances <= max_distance)
        if not np.any(valid):
            continue
        distances = distances[valid]
        orientations = orientations[valid]
        i_idx = i_idx[valid]
        j_idx = j_idx[valid]
        pair_corr = z[i_idx] * z[j_idx]
        pair_semivar = 0.5 * (centered[i_idx] - centered[j_idx]) ** 2
        finite = np.isfinite(pair_corr) & np.isfinite(pair_semivar)
        if not np.any(finite):
            continue
        distances = distances[finite]
        orientations = orientations[finite]
        pair_corr = pair_corr[finite]
        pair_semivar = pair_semivar[finite]
        bin_index = np.floor(distances / bin_width).astype(int)
        keep = (bin_index >= 0) & (bin_index < n_bins)
        if not np.any(keep):
            continue
        bin_index = bin_index[keep]
        orientations = orientations[keep]
        pair_corr = pair_corr[keep]
        pair_semivar = pair_semivar[keep]
        counts = np.bincount(bin_index, minlength=n_bins)
        sum_corr += np.bincount(bin_index, weights=pair_corr, minlength=n_bins)
        sum_semivar += np.bincount(bin_index, weights=pair_semivar, minlength=n_bins)
        count_pairs += counts.astype(int)
        count_events[np.unique(bin_index)] += 1
        dir_index = _assign_direction_bins(orientations, direction_bin_width_deg)
        dir_keep = (dir_index >= 0) & (dir_index < n_dirs)
        if not np.any(dir_keep):
            continue
        flat = dir_index[dir_keep] * n_bins + bin_index[dir_keep]
        flat_size = n_dirs * n_bins
        count_pairs_dir += np.bincount(flat, minlength=flat_size).reshape(n_dirs, n_bins).astype(int)
        sum_corr_dir += np.bincount(flat, weights=pair_corr[dir_keep], minlength=flat_size).reshape(n_dirs, n_bins)
        sum_semivar_dir += np.bincount(flat, weights=pair_semivar[dir_keep], minlength=flat_size).reshape(n_dirs, n_bins)
        unique_flat = np.unique(flat)
        count_events_dir[unique_flat // n_bins, unique_flat % n_bins] += 1

    starts = np.arange(0.0, n_bins * bin_width, bin_width)
    centers = starts + 0.5 * bin_width
    with np.errstate(divide="ignore", invalid="ignore"):
        distance_df = pd.DataFrame(
            {
                "distance_start_km": starts,
                "distance_end_km": starts + bin_width,
                "distance_center_km": centers,
                "pair_count": count_pairs,
                "event_count": count_events,
                "mean_pair_correlation": sum_corr / count_pairs,
                "mean_semivariance": sum_semivar / count_pairs,
            }
        )
    rows: list[dict[str, object]] = []
    for dir_idx, center_deg in enumerate(direction_centers.tolist()):
        label = _direction_label(center_deg, direction_bin_width_deg)
        with np.errstate(divide="ignore", invalid="ignore"):
            corr = sum_corr_dir[dir_idx] / count_pairs_dir[dir_idx]
            semivar = sum_semivar_dir[dir_idx] / count_pairs_dir[dir_idx]
        for bin_idx in range(n_bins):
            rows.append(
                {
                    "direction_center_deg": float(center_deg),
                    "direction_label": label,
                    "direction_bin_width_deg": float(direction_bin_width_deg),
                    "distance_start_km": float(starts[bin_idx]),
                    "distance_end_km": float(starts[bin_idx] + bin_width),
                    "distance_center_km": float(centers[bin_idx]),
                    "pair_count": int(count_pairs_dir[dir_idx, bin_idx]),
                    "event_count": int(count_events_dir[dir_idx, bin_idx]),
                    "mean_pair_correlation": float(corr[bin_idx]) if np.isfinite(corr[bin_idx]) else np.nan,
                    "mean_semivariance": float(semivar[bin_idx]) if np.isfinite(semivar[bin_idx]) else np.nan,
                }
            )
    return distance_df.replace([np.inf, -np.inf], np.nan), pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan)


def build_distance_bin_summary(centered_df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """Build an isotropic correlogram and semivariogram summary."""

    settings = spatial_statistics_settings_from_config()
    kwargs.setdefault("bin_width_km", settings.distance_bin_width_km)
    kwargs.setdefault("random_seed", settings.random_seed)
    distance_df, _directional_df = build_pair_summaries(centered_df, **kwargs)
    return distance_df


def build_directional_distance_bin_summary(centered_df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """Build a direction-resolved correlogram and semivariogram summary."""

    _distance_df, directional_df = build_pair_summaries(centered_df, **kwargs)
    return directional_df


def fit_exponential_correlation_length(distance_df: pd.DataFrame, *, min_pairs_per_bin: int = 20) -> CorrelationLengthFit | None:
    """Fit an exponential correlation length to a binned correlogram."""

    if distance_df.empty:
        return None
    valid = distance_df.loc[
        (distance_df["pair_count"] >= int(min_pairs_per_bin))
        & np.isfinite(distance_df["distance_center_km"])
        & np.isfinite(distance_df["mean_pair_correlation"])
        & (distance_df["mean_pair_correlation"] > 0.0)
    ].copy()
    if len(valid) < 2:
        return None
    x = valid["distance_center_km"].to_numpy(dtype=float)
    y = valid["mean_pair_correlation"].clip(lower=1e-6, upper=1.0).to_numpy(dtype=float)
    weights = np.sqrt(valid["pair_count"].to_numpy(dtype=float).clip(min=1.0))

    def exp_model(distance_km: np.ndarray, corr_len_km: float) -> np.ndarray:
        return np.exp(-distance_km / np.maximum(corr_len_km, 1e-6))

    guess = max(float(np.nanmedian(x[x > 0.0])) if np.any(x > 0.0) else 20.0, 1.0)
    try:
        popt, _ = curve_fit(exp_model, x, y, p0=[guess], bounds=(1e-6, 1e6), sigma=1.0 / weights, absolute_sigma=False, maxfev=10000)
        corr_len = float(popt[0])
        method = "curve_fit"
    except Exception:
        coeffs = np.polyfit(x, np.log(y), deg=1, w=weights)
        slope = float(coeffs[0])
        if not np.isfinite(slope) or slope >= 0.0:
            return None
        corr_len = float(-1.0 / slope)
        method = "log_linear"
    if not np.isfinite(corr_len) or corr_len <= 0.0:
        return None
    return CorrelationLengthFit(
        correlation_length_km=corr_len,
        effective_range_km=float(-corr_len * math.log(0.05)),
        method=method,
        n_bins_used=int(len(valid)),
    )


def summarize_directional_fits(directional_df: pd.DataFrame, *, min_pairs_per_bin: int = 20) -> pd.DataFrame:
    """Fit one exponential correlation length per directional sector."""

    columns = [
        "direction_label",
        "direction_center_deg",
        "direction_bin_width_deg",
        "correlation_length_km",
        "effective_range_km",
        "fit_method",
        "fit_bins_used",
        "total_pair_count",
    ]
    if directional_df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for direction_center_deg, sub in directional_df.groupby("direction_center_deg", sort=True):
        fit = fit_exponential_correlation_length(sub, min_pairs_per_bin=min_pairs_per_bin)
        rows.append(
            {
                "direction_label": sub["direction_label"].iloc[0],
                "direction_center_deg": float(direction_center_deg),
                "direction_bin_width_deg": float(sub["direction_bin_width_deg"].iloc[0]),
                "correlation_length_km": fit.correlation_length_km if fit else np.nan,
                "effective_range_km": fit.effective_range_km if fit else np.nan,
                "fit_method": fit.method if fit else np.nan,
                "fit_bins_used": fit.n_bins_used if fit else np.nan,
                "total_pair_count": int(pd.to_numeric(sub["pair_count"], errors="coerce").fillna(0).sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("direction_center_deg")


def build_station_catalog(field_df: pd.DataFrame) -> pd.DataFrame:
    """Build a unique station catalog from an event-station field."""

    if field_df.empty:
        return pd.DataFrame(columns=["station", "lat", "lon", "n_rows", "n_events"])
    return field_df.groupby("station", as_index=False).agg(lat=("lat", "mean"), lon=("lon", "mean"), n_rows=("event_id", "size"), n_events=("event_id", pd.Series.nunique))


def assign_spatial_blocks(station_df: pd.DataFrame, *, block_size_km: float = DEFAULT_BLOCK_SIZE_KM) -> pd.DataFrame:
    """Assign stations to simple Cartesian spatial blocks."""

    if station_df.empty:
        return station_df.copy()
    block_size = float(block_size_km)
    if block_size <= 0.0:
        raise ValueError("block_size_km must be positive.")
    out = station_df.copy()
    x_km, y_km = lonlat_to_xy_km(out["lat"].to_numpy(dtype=float), out["lon"].to_numpy(dtype=float))
    x0 = float(np.nanmin(x_km))
    y0 = float(np.nanmin(y_km))
    out["x_km"] = x_km
    out["y_km"] = y_km
    out["block_ix"] = np.floor((x_km - x0) / block_size).astype(int)
    out["block_iy"] = np.floor((y_km - y0) / block_size).astype(int)
    out["block_id"] = [f"bx{ix:03d}_by{iy:03d}" for ix, iy in zip(out["block_ix"].tolist(), out["block_iy"].tolist())]
    out["block_station_count"] = out.groupby("block_id")["station"].transform("size").astype(int)
    return out


def predict_station_bias_idw(
    train_station_df: pd.DataFrame,
    test_station_df: pd.DataFrame,
    *,
    knn: int = DEFAULT_BLOCK_PREDICTION_K,
    distance_power: float = DEFAULT_BLOCK_DISTANCE_POWER,
) -> pd.DataFrame:
    """Predict held-out station bias from nearby training stations using IDW."""

    if train_station_df.empty or test_station_df.empty:
        return pd.DataFrame()
    train = train_station_df.dropna(subset=["lat", "lon", "mean_centered"]).copy()
    test = test_station_df.dropna(subset=["lat", "lon", "mean_centered"]).copy()
    if train.empty or test.empty:
        return pd.DataFrame()
    all_lat = np.concatenate([train["lat"].to_numpy(dtype=float), test["lat"].to_numpy(dtype=float)])
    all_lon = np.concatenate([train["lon"].to_numpy(dtype=float), test["lon"].to_numpy(dtype=float)])
    x_all, y_all = lonlat_to_xy_km(all_lat, all_lon)
    train_count = len(train)
    train_coords = np.column_stack([x_all[:train_count], y_all[:train_count]])
    test_coords = np.column_stack([x_all[train_count:], y_all[train_count:]])
    k_use = max(1, min(int(knn), len(train)))
    nn = NearestNeighbors(n_neighbors=k_use).fit(train_coords)
    distances, indices = nn.kneighbors(test_coords)
    weights = 1.0 / np.power(np.maximum(distances, 1e-6), float(distance_power))
    train_values = train["mean_centered"].to_numpy(dtype=float)
    predicted = np.sum(weights * train_values[indices], axis=1) / np.sum(weights, axis=1)
    baseline = float(np.nanmean(train_values)) if np.isfinite(train_values).any() else 0.0
    out = test[["station", "lat", "lon", "n_events", "mean_centered"]].copy()
    out.rename(columns={"mean_centered": "observed_mean_centered", "n_events": "holdout_n_events"}, inplace=True)
    out["predicted_mean_centered"] = predicted
    out["baseline_prediction"] = baseline
    out["prediction_error"] = out["predicted_mean_centered"] - out["observed_mean_centered"]
    out["absolute_error"] = np.abs(out["prediction_error"])
    out["neighbor_count"] = k_use
    out["mean_neighbor_distance_km"] = np.nanmean(distances, axis=1)
    out["max_neighbor_distance_km"] = np.nanmax(distances, axis=1)
    return out


def evaluate_spatial_block_holdouts(
    field_df: pd.DataFrame,
    *,
    block_size_km: float = DEFAULT_BLOCK_SIZE_KM,
    min_block_stations: int = 3,
    min_stations_per_event: int = 3,
    min_events_per_station: int = 3,
    prediction_k: int = DEFAULT_BLOCK_PREDICTION_K,
    prediction_distance_power: float = DEFAULT_BLOCK_DISTANCE_POWER,
    max_folds: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Evaluate station-bias generalization with leave-one-spatial-block-out folds."""

    block_assignments = assign_spatial_blocks(build_station_catalog(field_df), block_size_km=block_size_km)
    if block_assignments.empty:
        return block_assignments, pd.DataFrame(), pd.DataFrame()
    block_order = (
        block_assignments.groupby("block_id")
        .agg(block_station_count=("station", "size"), block_lat=("lat", "mean"), block_lon=("lon", "mean"))
        .reset_index()
        .sort_values(["block_station_count", "block_id"], ascending=[False, True])
    )
    block_order = block_order.loc[block_order["block_station_count"] >= int(min_block_stations)].copy()
    if max_folds is not None and int(max_folds) > 0:
        block_order = block_order.head(int(max_folds)).copy()
    if block_order.empty:
        return block_assignments, pd.DataFrame(), pd.DataFrame()
    field_with_blocks = field_df.merge(block_assignments[["station", "block_id"]], on="station", how="left")
    prediction_rows = []
    summary_rows = []
    for block_id in block_order["block_id"].tolist():
        holdout_stations = set(block_assignments.loc[block_assignments["block_id"] == block_id, "station"])
        reference_mask = ~field_with_blocks["station"].isin(holdout_stations)
        centered_fold = center_field_by_reference_mask(field_with_blocks, reference_mask, min_stations_per_event=min_stations_per_event)
        if centered_fold.empty:
            continue
        train_centered = centered_fold.loc[~centered_fold["station"].isin(holdout_stations)].copy()
        holdout_centered = centered_fold.loc[centered_fold["station"].isin(holdout_stations)].copy()
        train_station_df = summarize_station_bias(train_centered, min_events_per_station=min_events_per_station)
        holdout_station_df = summarize_station_bias(holdout_centered, min_events_per_station=min_events_per_station)
        if len(train_station_df) < 3 or holdout_station_df.empty:
            continue
        predictions = predict_station_bias_idw(train_station_df, holdout_station_df, knn=prediction_k, distance_power=prediction_distance_power)
        if predictions.empty:
            continue
        predictions["block_id"] = block_id
        predictions["block_station_count"] = int(len(holdout_station_df))
        predictions["train_station_count"] = int(len(train_station_df))
        predictions["block_size_km"] = float(block_size_km)
        prediction_rows.append(predictions)
        observed = predictions["observed_mean_centered"].to_numpy(dtype=float)
        pred = predictions["predicted_mean_centered"].to_numpy(dtype=float)
        baseline = predictions["baseline_prediction"].to_numpy(dtype=float)
        rmse = float(np.sqrt(np.nanmean((pred - observed) ** 2)))
        baseline_rmse = float(np.sqrt(np.nanmean((baseline - observed) ** 2)))
        summary_rows.append(
            {
                "block_id": block_id,
                "holdout_station_count": int(len(predictions)),
                "train_station_count": int(len(train_station_df)),
                "rmse": rmse,
                "baseline_rmse": baseline_rmse,
                "skill_vs_baseline": float(1.0 - rmse / baseline_rmse) if baseline_rmse > 0.0 else np.nan,
                "mean_absolute_error": float(np.nanmean(np.abs(pred - observed))),
            }
        )
    prediction_df = pd.concat(prediction_rows, ignore_index=True) if prediction_rows else pd.DataFrame()
    summary_df = pd.DataFrame(summary_rows)
    if not summary_df.empty:
        summary_df.sort_values(["rmse", "block_id"], inplace=True)
    return block_assignments, prediction_df, summary_df
