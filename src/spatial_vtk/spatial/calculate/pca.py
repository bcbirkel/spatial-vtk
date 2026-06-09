"""PCA spatial-mode calculations for station residual fingerprints.

Purpose
-------
This module extracts orthogonal station-level spatial modes from event,
metric, or residual-feature matrices. Rows represent stations and columns
represent residual features such as event-centered metric values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from spatial_vtk.spatial.calculate.settings import spatial_statistics_settings_from_config


@dataclass(frozen=True)
class PCASpatialModeResult:
    """Container for PCA spatial-mode outputs."""

    station_scores: pd.DataFrame
    feature_loadings: pd.DataFrame
    explained_variance: pd.DataFrame
    feature_columns: list[str]


def _resolve_feature_columns(
    df: pd.DataFrame,
    *,
    feature_columns: Sequence[str] | None,
    metadata_columns: Sequence[str],
) -> list[str]:
    """Return numeric feature columns available for PCA."""

    if feature_columns is not None:
        missing = [column for column in feature_columns if column not in df.columns]
        if missing:
            raise KeyError(f"Missing PCA feature columns: {missing}")
        candidates = [str(column) for column in feature_columns]
    else:
        metadata = set(metadata_columns)
        reserved = {
            "events_present",
            "metrics_present",
            "station_bias_events",
            "metric_events",
            "features_present",
            "feature_nonmissing_count",
        }
        candidates = [column for column in df.columns if column not in metadata and column not in reserved]

    valid: list[str] = []
    for column in candidates:
        values = pd.to_numeric(df[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
        if int(values.notna().sum()) >= 2 and float(values.std(ddof=1)) > 0.0:
            valid.append(column)
    return valid


def compute_pca_spatial_modes(
    feature_df: pd.DataFrame,
    *,
    feature_columns: Sequence[str] | None = None,
    metadata_columns: Sequence[str] = ("station", "lat", "lon"),
    n_components: int | None = None,
    min_nonmissing_per_station: int = 1,
    standardize: bool = True,
    component_prefix: str = "PC",
) -> PCASpatialModeResult:
    """Compute PCA spatial modes from a station-feature table.

    Parameters
    ----------
    feature_df
        Table with one row per station and residual-feature columns.
    feature_columns
        Optional explicit feature columns. When omitted, numeric non-metadata
        columns are used.
    metadata_columns
        Columns copied into the station-score output.
    n_components
        Requested number of principal components.
    min_nonmissing_per_station
        Minimum number of finite feature values required to keep a station.
    standardize
        Whether to z-score features before PCA.
    component_prefix
        Prefix used for component labels, such as ``"PC"``.

    Returns
    -------
    PCASpatialModeResult
        Station score table, feature loading table, explained-variance table,
        and the feature columns used in the model.
    """

    score_columns = [column for column in metadata_columns if column in feature_df.columns]
    empty_scores = pd.DataFrame(columns=[*score_columns, "feature_nonmissing_count"])
    empty_loadings = pd.DataFrame(columns=["mode", "mode_index", "feature", "loading", "absolute_loading"])
    empty_variance = pd.DataFrame(
        columns=[
            "mode",
            "mode_index",
            "explained_variance",
            "explained_variance_ratio",
            "cumulative_explained_variance_ratio",
            "singular_value",
            "n_stations",
            "n_features",
            "standardized",
        ]
    )
    settings = spatial_statistics_settings_from_config()
    requested_components = settings.pca_components if n_components is None else int(n_components)
    if feature_df.empty:
        return PCASpatialModeResult(empty_scores, empty_loadings, empty_variance, [])

    features = _resolve_feature_columns(feature_df, feature_columns=feature_columns, metadata_columns=metadata_columns)
    if not features:
        return PCASpatialModeResult(empty_scores, empty_loadings, empty_variance, [])

    work = feature_df.copy()
    for column in features:
        work[column] = pd.to_numeric(work[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
    work["feature_nonmissing_count"] = work[features].notna().sum(axis=1)
    work = work.loc[work["feature_nonmissing_count"] >= int(min_nonmissing_per_station)].copy()
    if len(work) < 2:
        return PCASpatialModeResult(empty_scores, empty_loadings, empty_variance, features)

    matrix = work[features].to_numpy(dtype=float)
    column_means = np.nanmean(matrix, axis=0)
    column_means = np.where(np.isfinite(column_means), column_means, 0.0)
    imputed = np.where(np.isfinite(matrix), matrix, column_means[None, :])
    if standardize:
        model_input = StandardScaler().fit_transform(imputed)
    else:
        model_input = imputed - np.nanmean(imputed, axis=0, keepdims=True)

    component_count = max(1, min(int(requested_components), model_input.shape[0], model_input.shape[1]))
    pca = PCA(n_components=component_count)
    scores = pca.fit_transform(model_input)
    loadings = pca.components_.T.copy()

    # Stabilize signs by making the strongest loading in each mode positive.
    for component_index in range(component_count):
        strongest = int(np.nanargmax(np.abs(loadings[:, component_index])))
        if loadings[strongest, component_index] < 0.0:
            loadings[:, component_index] *= -1.0
            scores[:, component_index] *= -1.0

    station_scores = work[score_columns].copy()
    station_scores["feature_nonmissing_count"] = work["feature_nonmissing_count"].to_numpy(dtype=int)
    for component_index in range(component_count):
        station_scores[f"{component_prefix}{component_index + 1}_score"] = scores[:, component_index]

    loading_rows: list[dict[str, object]] = []
    for component_index in range(component_count):
        mode = f"{component_prefix}{component_index + 1}"
        for feature_index, feature in enumerate(features):
            value = float(loadings[feature_index, component_index])
            loading_rows.append(
                {
                    "mode": mode,
                    "mode_index": int(component_index + 1),
                    "feature": str(feature),
                    "loading": value,
                    "absolute_loading": abs(value),
                }
            )
    feature_loadings = pd.DataFrame(loading_rows).sort_values(["mode_index", "absolute_loading"], ascending=[True, False])

    cumulative = np.cumsum(pca.explained_variance_ratio_)
    explained_variance = pd.DataFrame(
        {
            "mode": [f"{component_prefix}{index + 1}" for index in range(component_count)],
            "mode_index": np.arange(1, component_count + 1, dtype=int),
            "explained_variance": pca.explained_variance_.astype(float),
            "explained_variance_ratio": pca.explained_variance_ratio_.astype(float),
            "cumulative_explained_variance_ratio": cumulative.astype(float),
            "singular_value": pca.singular_values_.astype(float),
            "n_stations": int(model_input.shape[0]),
            "n_features": int(model_input.shape[1]),
            "standardized": bool(standardize),
        }
    )
    return PCASpatialModeResult(station_scores, feature_loadings, explained_variance, features)
