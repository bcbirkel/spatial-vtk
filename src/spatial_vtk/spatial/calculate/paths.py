"""Path-oriented summaries for source-station metric rows."""

from __future__ import annotations

import numpy as np
import pandas as pd

from spatial_vtk.metrics.calculate.enrich import prepare_metric_residual_table


def build_path_table(df: pd.DataFrame, *, residual_mode: str = "logratio") -> pd.DataFrame:
    """Prepare metric rows for source-station path analysis."""

    out = prepare_metric_residual_table(df, residual_mode=residual_mode)
    required = ["event_id", "station", "metric", "residual", "distance_km", "azimuth_deg"]
    missing = [column for column in required if column not in out.columns]
    if missing:
        raise KeyError(f"Missing required path-analysis columns: {missing}")
    return out.dropna(subset=["residual", "distance_km", "azimuth_deg"]).copy()


def summarize_residuals_by_path_bin(
    path_df: pd.DataFrame,
    *,
    distance_bin_km: float = 10.0,
    azimuth_bin_deg: float = 30.0,
) -> pd.DataFrame:
    """Summarize residuals by distance and azimuth bins."""

    work = build_path_table(path_df) if "distance_km" not in path_df.columns or "residual" not in path_df.columns else path_df.copy()
    work["distance_bin_km"] = np.floor(pd.to_numeric(work["distance_km"], errors="coerce") / float(distance_bin_km)) * float(distance_bin_km)
    work["azimuth_bin_deg"] = np.floor((pd.to_numeric(work["azimuth_deg"], errors="coerce") % 360.0) / float(azimuth_bin_deg)) * float(azimuth_bin_deg)
    return (
        work.groupby(["model", "metric", "band", "distance_bin_km", "azimuth_bin_deg"], dropna=False)
        .agg(mean_residual=("residual", "mean"), median_residual=("residual", "median"), n=("residual", "count"))
        .reset_index()
    )
