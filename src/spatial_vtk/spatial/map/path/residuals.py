"""Map source-station residual patterns for one event or metric selection."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence
import math

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from spatial_vtk.config.labels import metric_display_name, value_column_display_name
from spatial_vtk.metrics.calculate.enrich import prepare_metric_residual_table
from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
from spatial_vtk.visualize.figure_context import apply_figure_context, value_color_settings
from spatial_vtk.visualize.figure_sidecars import finish_figure_with_sidecar


def plot_event_residual_map(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    event_id: str | None = None,
    metric: str | None = None,
    value_col: str = "residual",
    station_region_col: str | None = None,
    station_regions: Sequence[str] | str | None = None,
    event_region_col: str | None = None,
    event_regions: Sequence[str] | str | None = None,
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    title: str | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
) -> plt.Figure:
    """Plot station residuals for one event/metric selection.

    Map figures add a basemap by default, following the repository figure rule.
    Tests may pass ``add_basemap=False`` for fully offline rendering. Set
    ``station_regions`` or ``event_regions`` to restrict the mapped rows to
    region labels that were joined onto the residual table, and set
    ``write_sidecar=True`` to write the filtered event/metric/region rows and
    the unfiltered source rows next to the saved figure.
    """

    work = prepare_metric_residual_table(df)
    if event_id is not None:
        work = work.loc[work["event_id"].astype(str) == str(event_id)].copy()
    if metric is not None:
        work = work.loc[work["metric"].astype(str) == str(metric)].copy()
    work = _filter_region_rows(
        work,
        station_region_col=station_region_col,
        station_regions=station_regions,
        event_region_col=event_region_col,
        event_regions=event_regions,
    )
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

    return finish_figure_with_sidecar(
        fig,
        output_path,
        outpath=outpath,
        showfig=showfig,
        savefig=savefig,
        sidecar_df=work,
        source_rows=prepare_metric_residual_table(df),
        write_sidecar=write_sidecar,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
        metadata={
            "figure_type": "event_residual_map",
            "event_id": event_id,
            "metric": metric,
            "value_col": value_col,
            "station_region_col": station_region_col,
            "station_regions": _region_metadata_value(station_regions),
            "event_region_col": event_region_col,
            "event_regions": _region_metadata_value(event_regions),
        },
    )


def _filter_region_rows(
    df: pd.DataFrame,
    *,
    station_region_col: str | None,
    station_regions: Sequence[str] | str | None,
    event_region_col: str | None,
    event_regions: Sequence[str] | str | None,
) -> pd.DataFrame:
    """Filter station/event rows by optional region labels."""

    out = df
    if station_regions is not None:
        column = station_region_col or _first_existing_column(
            out,
            ("station_region", "station_geojson_region", "station_geojson_labels", "station_region_type"),
        )
        out = _filter_region_column(out, column, station_regions, label="station")
    if event_regions is not None:
        column = event_region_col or _first_existing_column(
            out,
            ("event_region", "event_geojson_region", "event_geojson_labels", "event_region_type"),
        )
        out = _filter_region_column(out, column, event_regions, label="event")
    return out


def _filter_region_column(df: pd.DataFrame, column: str | None, values: Sequence[str] | str, *, label: str) -> pd.DataFrame:
    """Return rows matching a station/event region column."""

    if column is None or column not in df.columns:
        raise KeyError(f"No {label} region column was found for filtering.")
    wanted = {str(value) for value in _as_list(values)}
    return df.loc[df[column].astype(str).isin(wanted)].copy()


def _first_existing_column(df: pd.DataFrame, candidates: Sequence[str]) -> str | None:
    """Return the first existing column from ``candidates``."""

    return next((column for column in candidates if column in df.columns), None)


def _as_list(values: Sequence[str] | str) -> list[str]:
    """Normalize a scalar or sequence of region labels."""

    if isinstance(values, str):
        return [values]
    return [str(value) for value in values]


def _region_metadata_value(values: Sequence[str] | str | None) -> str | list[str] | None:
    """Return JSON-friendly region metadata."""

    if values is None:
        return None
    out = _as_list(values)
    return out[0] if len(out) == 1 else out


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
