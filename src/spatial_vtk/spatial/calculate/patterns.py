"""Observed/synthetic spatial pattern comparison helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from spatial_vtk.spatial.calculate._common import metric_label, normalize_passband


def normalize_metrics_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize a synthetic-overlap metrics table for pattern comparisons.

    Parameters
    ----------
    df
        Metrics table with observed/synthetic columns and coordinates.

    Returns
    -------
    pandas.DataFrame
        Copy with normalized event id, passband, and numeric coordinates.
    """

    out = df.copy()
    if "event_id" not in out.columns:
        out["event_id"] = out["event_title"].astype(str)
    out["event_id"] = out["event_id"].astype(str)
    out["station_name"] = out["station_name"].astype(str)
    out["passband_norm"] = out["simulation_band"].map(normalize_passband)
    for column in ["station_longitude", "station_latitude", "event_longitude", "event_latitude", "event_depth_km"]:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    return out.dropna(subset=["station_longitude", "station_latitude", "event_longitude", "event_latitude"]).copy()


def pattern_similarity(stations: pd.DataFrame) -> pd.DataFrame:
    """Compare observed and synthetic station-anomaly patterns.

    Parameters
    ----------
    stations
        Station-level anomaly table containing ``dataset`` values
        ``observed`` and ``synthetic``.

    Returns
    -------
    pandas.DataFrame
        Similarity statistics by metric and bin.
    """

    rows = []
    for (metric, bin_label), group in stations.groupby(["metric", "bin"], dropna=False):
        pivot = group.pivot_table(index="station_name", columns="dataset", values="value", aggfunc="mean")
        if "observed" not in pivot.columns or "synthetic" not in pivot.columns:
            continue
        matched = pivot[["observed", "synthetic"]].replace([np.inf, -np.inf], np.nan).dropna()
        if len(matched) < 5:
            continue
        diff = matched["observed"] - matched["synthetic"]
        rows.append(
            {
                "metric": metric,
                "bin": bin_label,
                "metric_label": metric_label(metric),
                "n_stations": int(len(matched)),
                "pearson_r": float(matched["observed"].corr(matched["synthetic"])),
                "spearman_r": float(spearmanr(matched["observed"], matched["synthetic"]).correlation),
                "median_observed_minus_synthetic": float(np.median(diff)),
                "mad_observed_minus_synthetic": float(np.median(np.abs(diff - np.median(diff)))),
            }
        )
    return pd.DataFrame(rows)


def build_pattern_similarity_station_anomalies(
    metrics: pd.DataFrame,
    *,
    metric: str,
    passband: str,
    component: str | None = None,
    model: str | None = None,
    station_col: str = "station",
    observed_col: str = "value_obs",
    synthetic_col: str = "value_syn",
) -> pd.DataFrame:
    """Build observed/synthetic station-anomaly rows for pattern plots.

    Parameters
    ----------
    metrics
        Long metric table with observed and synthetic metric-value columns.
    metric, passband
        Metric name and period band to select.
    component, model
        Optional component and model filters.
    station_col
        Station identifier column in ``metrics``.
    observed_col, synthetic_col
        Columns containing observed and synthetic metric values.

    Returns
    -------
    pandas.DataFrame
        Long table with ``station_name``, ``dataset``, ``metric``, ``bin``, and
        mean-centered ``value`` columns for plotting and similarity statistics.
    """

    required = {station_col, "metric", "band", observed_col, synthetic_col}
    missing = sorted(required.difference(metrics.columns))
    if missing:
        raise KeyError(f"Missing required metric columns for pattern similarity: {missing}")

    work = metrics.copy()
    mask = work["metric"].astype(str).str.upper().eq(str(metric).upper()) & work["band"].astype(str).eq(str(passband))
    if component is not None and "component" in work.columns:
        mask &= work["component"].astype(str).str.upper().eq(str(component).upper())
    if model is not None and "model" in work.columns:
        mask &= work["model"].astype(str).eq(str(model))
    subset = work.loc[mask, [station_col, observed_col, synthetic_col]].copy()
    if subset.empty:
        return pd.DataFrame(columns=["station_name", "dataset", "metric", "bin", "value"])

    rows: list[pd.DataFrame] = []
    for dataset, value_col in (("observed", observed_col), ("synthetic", synthetic_col)):
        station_values = (
            subset.assign(_value=pd.to_numeric(subset[value_col], errors="coerce"))
            .dropna(subset=["_value"])
            .groupby(station_col, dropna=False)["_value"]
            .mean()
            .reset_index()
        )
        if station_values.empty:
            continue
        station_values["value"] = station_values["_value"] - float(station_values["_value"].mean())
        station_values["station_name"] = station_values[station_col].astype(str)
        station_values["dataset"] = dataset
        station_values["metric"] = str(metric).upper()
        station_values["bin"] = str(passband)
        rows.append(station_values[["station_name", "dataset", "metric", "bin", "value"]])
    if not rows:
        return pd.DataFrame(columns=["station_name", "dataset", "metric", "bin", "value"])
    return pd.concat(rows, ignore_index=True)
