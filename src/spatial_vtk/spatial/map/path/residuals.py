"""Map source-station residual patterns for one event or metric selection."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import math

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from spatial_vtk.config.labels import metric_display_name, value_column_display_name
from spatial_vtk.metrics.calculate.enrich import prepare_metric_residual_table
from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
from spatial_vtk.visualize.figure_context import apply_figure_context, value_color_settings
from spatial_vtk.visualize.figure_io import finish_figure


def plot_event_residual_map(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    event_id: str | None = None,
    metric: str | None = None,
    value_col: str = "residual",
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    title: str | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot station residuals for one event/metric selection.

    Map figures add a basemap by default, following the repository figure rule.
    Tests may pass ``add_basemap=False`` for fully offline rendering.
    """

    work = prepare_metric_residual_table(df)
    if event_id is not None:
        work = work.loc[work["event_id"].astype(str) == str(event_id)].copy()
    if metric is not None:
        work = work.loc[work["metric"].astype(str) == str(metric)].copy()
    if work.empty:
        raise ValueError("No rows remain after event/metric filtering.")
    lon_col, lat_col = _xy_columns(work)
    values = pd.to_numeric(work[value_col], errors="coerce")
    cmap, vmin, vmax = value_color_settings(values.to_numpy(dtype=float), value_col, work)

    fig, ax = plt.subplots(figsize=(7.0, 6.0), dpi=180, constrained_layout=True)
    _set_bounds(ax, work, lon_col, lat_col)
    if add_basemap:
        kwargs = dict(basemap_kwargs or {})
        add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **kwargs)
    scatter = ax.scatter(
        pd.to_numeric(work[lon_col], errors="coerce"),
        pd.to_numeric(work[lat_col], errors="coerce"),
        c=values,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        s=42,
        edgecolor="black",
        linewidth=0.35,
        zorder=3,
    )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    apply_figure_context(
        ax,
        work,
        value_col=value_col,
        title=title or _default_title(event_id=event_id, metric=metric),
        max_values=3,
        include_counts=False,
        include_value=False,
        max_line_chars=72,
    )
    ax.grid(True, alpha=0.18, zorder=1)
    cbar = fig.colorbar(scatter, ax=ax, pad=0.045)
    cbar.set_label(value_column_display_name(value_col))

    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _xy_columns(df: pd.DataFrame) -> tuple[str, str]:
    """Resolve longitude and latitude columns from supported schemas."""

    lon = next((column for column in ["sta_lon", "lon", "station_longitude", "longitude"] if column in df.columns), None)
    lat = next((column for column in ["sta_lat", "lat", "station_latitude", "latitude"] if column in df.columns), None)
    if lon is None or lat is None:
        raise KeyError("Could not resolve station longitude/latitude columns.")
    return lon, lat


def _set_bounds(ax: plt.Axes, df: pd.DataFrame, lon_col: str, lat_col: str) -> None:
    """Set padded map bounds from station coordinates."""

    lon = pd.to_numeric(df[lon_col], errors="coerce").to_numpy(dtype=float)
    lat = pd.to_numeric(df[lat_col], errors="coerce").to_numpy(dtype=float)
    finite = np.isfinite(lon) & np.isfinite(lat)
    west, east = float(np.nanmin(lon[finite])), float(np.nanmax(lon[finite]))
    south, north = float(np.nanmin(lat[finite])), float(np.nanmax(lat[finite]))
    pad_x = max(0.03, 0.08 * max(east - west, 0.01))
    pad_y = max(0.03, 0.08 * max(north - south, 0.01))
    ax.set_xlim(west - pad_x, east + pad_x)
    ax.set_ylim(south - pad_y, north + pad_y)
    _set_geographic_aspect(ax)


def _set_geographic_aspect(ax: plt.Axes) -> None:
    """Preserve lon/lat proportions on map axes."""

    lat_min, lat_max = ax.get_ylim()
    lat_mid = 0.5 * (float(lat_min) + float(lat_max))
    cos_lat = math.cos(math.radians(lat_mid))
    if math.isfinite(cos_lat) and abs(cos_lat) > 1.0e-6:
        ax.set_aspect(1.0 / cos_lat, adjustable="box")


def _default_title(*, event_id: str | None, metric: str | None) -> str:
    """Build a compact event residual map title."""

    parts = ["Event Residual Map"]
    if event_id:
        parts.append(str(event_id))
    if metric:
        parts.append(metric_display_name(metric))
    return " - ".join(parts)
