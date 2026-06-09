"""Dashboard dataset export helpers.

Purpose
-------
This module converts wide or long metric tables into dashboard-ready Parquet
datasets and reloads those datasets for summary generation.

Usage examples
--------------
Write one dashboard dataset:
  ``path = write_dashboard_metric_dataset(metrics_df, "dashboard_data")``
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.visualize.dashboard.tables import build_dashboard_summaries, prepare_dashboard_metric_table, write_dashboard_summaries


def write_dashboard_metric_dataset(
    tables: pd.DataFrame | str | Path | Sequence[pd.DataFrame | str | Path],
    output_root: str | Path | None = None,
    *,
    residual_mode: str = "logratio",
    partitioned: bool = False,
) -> Path:
    """Write dashboard-ready long metric data as Parquet.

    Parameters
    ----------
    tables
        One table, path, or sequence of tables/paths.
    output_root
        Output directory for ``metrics_long.parquet`` or partitioned files.
        When omitted, the standard ``metrics_dashboard`` path is resolved from
        the active config.
    residual_mode
        Residual mode used when converting wide tables.
    partitioned
        Whether to partition by ``model``, ``band``, and ``metric``.

    Returns
    -------
    pathlib.Path
        Dataset root directory.
    """

    frames = [_read_metric_table(item) for item in _as_sequence(tables)]
    if not frames:
        raise ValueError("At least one metric table is required.")
    long_frames = [prepare_dashboard_metric_table(frame, residual_mode=residual_mode) for frame in frames]
    long_df = pd.concat(long_frames, ignore_index=True)
    long_df = add_dashboard_path_geometry(long_df)
    root = Path(output_root).expanduser() if output_root is not None else resolve_output_path("metrics_dashboard", kind="dashboard", create_parent=True)
    root.mkdir(parents=True, exist_ok=True)
    if not partitioned:
        long_df.to_parquet(root / "metrics_long.parquet", index=False)
        return root
    required = ["model", "band", "metric"]
    for column in required:
        if column not in long_df.columns:
            long_df[column] = "unknown"
    for keys, group in long_df.groupby(required, dropna=False):
        model, band, metric = [safe_path_token(value) for value in keys]
        out_path = root / f"model={model}" / f"band={band}" / f"metric={metric}" / "part.parquet"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        group.to_parquet(out_path, index=False)
    return root


def load_dashboard_metric_dataset(input_root: str | Path) -> pd.DataFrame:
    """Load a dashboard metric Parquet dataset.

    Parameters
    ----------
    input_root
        Directory containing ``metrics_long.parquet`` or partitioned parquet
        files.

    Returns
    -------
    pandas.DataFrame
        Combined long metric table.
    """

    root = Path(input_root).expanduser()
    direct = root / "metrics_long.parquet"
    paths = [direct] if direct.exists() else sorted(root.rglob("*.parquet"))
    if not paths:
        raise FileNotFoundError(f"No dashboard parquet files found under {root}.")
    return pd.concat([pd.read_parquet(path) for path in paths], ignore_index=True)


def write_dashboard_summary_dataset(
    input_root: str | Path | None = None,
    output_root: str | Path | None = None,
    *,
    hex_dist: float = 10.0,
    hex_az: float = 10.0,
    format: str = "parquet",
) -> dict[str, Path]:
    """Build and write dashboard summary tables from a metric dataset.

    Parameters
    ----------
    input_root
        Dashboard metric dataset root. When omitted, the standard
        ``metrics_dashboard`` path is resolved from the active config.
    output_root
        Output directory for summary tables. When omitted, the standard
        ``dashboard_summaries`` path is resolved from the active config.
    hex_dist
        Distance-bin size in kilometers.
    hex_az
        Azimuth-bin size in degrees.
    format
        Output format, ``"parquet"`` or ``"csv"``.

    Returns
    -------
    dict[str, pathlib.Path]
        Written summary paths by table name.
    """

    resolved_input_root = input_root or resolve_output_path("metrics_dashboard", kind="dashboard")
    resolved_output_root = output_root or resolve_output_path("dashboard_summaries", kind="dashboard", create_parent=True)
    metrics = load_dashboard_metric_dataset(resolved_input_root)
    summaries = build_dashboard_summaries(metrics, hex_dist=hex_dist, hex_az=hex_az)
    return write_dashboard_summaries(summaries, resolved_output_root, format=format)


def add_dashboard_path_geometry(df: pd.DataFrame) -> pd.DataFrame:
    """Add distance, azimuth, and backazimuth columns when coordinates exist.

    Parameters
    ----------
    df
        Long metric table with event and station coordinates.

    Returns
    -------
    pandas.DataFrame
        Copy with ``distance_km``, ``azimuth_deg``, and ``backazimuth_deg``
        when enough coordinate columns are present.
    """

    out = df.copy()
    coordinate_sets = [
        ("event_lat", "event_lon", "sta_lat", "sta_lon"),
        ("event_lat", "event_lon", "station_lat", "station_lon"),
        ("event_lat", "event_lon", "lat", "lon"),
    ]
    selected = next((cols for cols in coordinate_sets if set(cols) <= set(out.columns)), None)
    if selected is None:
        return out
    event_lat, event_lon, station_lat, station_lon = selected
    lat1 = pd.to_numeric(out[event_lat], errors="coerce")
    lon1 = pd.to_numeric(out[event_lon], errors="coerce")
    lat2 = pd.to_numeric(out[station_lat], errors="coerce")
    lon2 = pd.to_numeric(out[station_lon], errors="coerce")
    out["distance_km"] = haversine_km(lat1, lon1, lat2, lon2)
    azimuth = forward_azimuth_deg(lat1, lon1, lat2, lon2)
    out["azimuth_deg"] = azimuth
    out["backazimuth_deg"] = (azimuth + 180.0) % 360.0
    return out


def haversine_km(lat1: Any, lon1: Any, lat2: Any, lon2: Any) -> np.ndarray:
    """Calculate great-circle distance in kilometers.

    Parameters
    ----------
    lat1, lon1, lat2, lon2
        Scalar or array-like coordinates in degrees.

    Returns
    -------
    numpy.ndarray
        Distance values in kilometers.
    """

    radius_km = 6371.0088
    lat1_arr = np.asarray(lat1, dtype=float)
    lon1_arr = np.asarray(lon1, dtype=float)
    lat2_arr = np.asarray(lat2, dtype=float)
    lon2_arr = np.asarray(lon2, dtype=float)
    dlat = np.radians(lat2_arr - lat1_arr)
    dlon = np.radians(lon2_arr - lon1_arr)
    a = np.sin(dlat / 2.0) ** 2 + np.cos(np.radians(lat1_arr)) * np.cos(np.radians(lat2_arr)) * np.sin(dlon / 2.0) ** 2
    return 2.0 * radius_km * np.arcsin(np.sqrt(a))


def forward_azimuth_deg(lat1: Any, lon1: Any, lat2: Any, lon2: Any) -> np.ndarray:
    """Calculate forward azimuth from event to station.

    Parameters
    ----------
    lat1, lon1
        Source coordinates in degrees.
    lat2, lon2
        Target coordinates in degrees.

    Returns
    -------
    numpy.ndarray
        Azimuth values in degrees clockwise from north.
    """

    lat1_rad = np.radians(np.asarray(lat1, dtype=float))
    lat2_rad = np.radians(np.asarray(lat2, dtype=float))
    dlon = np.radians(np.asarray(lon2, dtype=float) - np.asarray(lon1, dtype=float))
    x = np.sin(dlon) * np.cos(lat2_rad)
    y = np.cos(lat1_rad) * np.sin(lat2_rad) - np.sin(lat1_rad) * np.cos(lat2_rad) * np.cos(dlon)
    return (np.degrees(np.arctan2(x, y)) + 360.0) % 360.0


def safe_path_token(value: object) -> str:
    """Return a conservative token for partition paths.

    Parameters
    ----------
    value
        Value to include in a path component.

    Returns
    -------
    str
        Sanitized path token.
    """

    text = "unknown" if value is None or pd.isna(value) else str(value)
    return "".join(char if char.isalnum() or char in "._=-" else "_" for char in text).strip("_") or "unknown"


def _read_metric_table(table: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Read one metric table from dataframe, CSV, or parquet."""

    if isinstance(table, pd.DataFrame):
        return table.copy()
    path = Path(table).expanduser()
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _as_sequence(value: pd.DataFrame | str | Path | Sequence[pd.DataFrame | str | Path]) -> list[pd.DataFrame | str | Path]:
    """Normalize a scalar or sequence of metric-table inputs."""

    if isinstance(value, (pd.DataFrame, str, Path)):
        return [value]
    return list(value)


__all__ = [
    "add_dashboard_path_geometry",
    "forward_azimuth_deg",
    "haversine_km",
    "load_dashboard_metric_dataset",
    "safe_path_token",
    "write_dashboard_metric_dataset",
    "write_dashboard_summary_dataset",
]
