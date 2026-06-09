"""Map polygon-boundary corridors with station and event context."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import math

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
from spatial_vtk.visualize.figure_context import apply_figure_context
from spatial_vtk.visualize.figure_io import finish_figure


def plot_corridor_map(
    corridors_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    stations_df: pd.DataFrame | None = None,
    events_df: pd.DataFrame | None = None,
    records_df: pd.DataFrame | None = None,
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    highlight_anchor: bool = False,
    title: str | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot corridor footprints with optional station, event, and path context.

    Parameters
    ----------
    corridors_df
        Corridor table with a ``corridor_geometry`` Shapely polygon column.
    output_path
        Figure path.
    stations_df, events_df
        Optional station/event context tables.
    records_df
        Optional event-station path table.
    add_basemap
        Whether to draw a contextily basemap. Defaults to ``True`` for public
        map outputs; tests may disable it for offline rendering.
    basemap_source, basemap_kwargs
        Basemap provider settings.
    highlight_anchor
        Whether to highlight station/event anchor rows used to place the
        corridor. Falls back to the boundary anchor point if the source point
        table is not available.
    title
        Optional figure title.

    Returns
    -------
    matplotlib.figure.Figure
        Figure object.
    """

    if corridors_df.empty:
        raise ValueError("corridors_df is empty.")
    fig, ax = plt.subplots(figsize=(7.2, 6.2), dpi=180)

    for idx, corridor in enumerate(corridors_df.itertuples(index=False)):
        geom = getattr(corridor, "corridor_geometry", None)
        if geom is None or geom.is_empty:
            continue
        x, y = geom.exterior.xy
        ax.fill(x, y, facecolor="#ffb000", edgecolor="#202020", linewidth=1.1, alpha=0.32, zorder=3)
        if idx == 0 and hasattr(corridor, "polygon_geometry"):
            polygon = getattr(corridor, "polygon_geometry")
            if polygon is not None and not polygon.is_empty:
                _plot_geometry_outline(ax, polygon)

    if records_df is not None and not records_df.empty:
        _plot_paths(ax, records_df)
    if stations_df is not None and not stations_df.empty:
        lon_col, lat_col = _resolve_xy(stations_df, lon_candidates=["station_lon", "station_longitude", "sta_lon", "lon", "longitude"], lat_candidates=["station_lat", "station_latitude", "sta_lat", "lat", "latitude"], label="station")
        ax.scatter(stations_df[lon_col], stations_df[lat_col], s=30, marker="^", facecolor="#2b83ba", edgecolor="white", linewidth=0.45, zorder=6, label="Stations")
    if events_df is not None and not events_df.empty:
        lon_col, lat_col = _resolve_xy(events_df, lon_candidates=["event_lon", "event_longitude", "source_lon", "source_longitude", "lon", "longitude"], lat_candidates=["event_lat", "event_latitude", "source_lat", "source_latitude", "lat", "latitude"], label="event")
        ax.scatter(events_df[lon_col], events_df[lat_col], s=34, marker="*", facecolor="#d7191c", edgecolor="white", linewidth=0.45, zorder=7, label="Events")
    if highlight_anchor:
        _plot_corridor_anchors(ax, corridors_df, stations_df=stations_df, events_df=events_df)

    _set_bounds_from_layers(ax, corridors_df, stations_df=stations_df, events_df=events_df, records_df=records_df)
    if add_basemap:
        kwargs = dict(basemap_kwargs or {})
        add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **kwargs)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    extra = [
        f"Corridors: {len(corridors_df):,}",
        f"Stations: {len(stations_df):,}" if stations_df is not None and not stations_df.empty else "",
        f"Events: {len(events_df):,}" if events_df is not None and not events_df.empty else "",
        f"Inside-corridor paths: {len(records_df):,}" if records_df is not None and not records_df.empty else "",
    ]
    apply_figure_context(ax, None, title=title or "Corridor Map", max_values=3, max_line_chars=72, extra=extra)
    ax.grid(True, alpha=0.18, zorder=1)
    if stations_df is not None or events_df is not None:
        ax.legend(loc="best", frameon=True)

    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _plot_corridor_anchors(
    ax: plt.Axes,
    corridors_df: pd.DataFrame,
    *,
    stations_df: pd.DataFrame | None,
    events_df: pd.DataFrame | None,
) -> None:
    """Highlight station, event, or boundary anchors used for corridors.

    Parameters
    ----------
    ax
        Matplotlib axes.
    corridors_df
        Corridor table with ``anchor_source`` and ``anchor_label`` metadata.
    stations_df, events_df
        Optional source point tables used to highlight the actual station or
        event anchor. If unavailable, the corridor boundary anchor point is
        highlighted instead.

    Returns
    -------
    None
        Mutates ``ax``.
    """

    if corridors_df.empty or "anchor_source" not in corridors_df.columns or "anchor_label" not in corridors_df.columns:
        return
    plotted_labels: set[str] = set()
    for row in corridors_df.itertuples(index=False):
        source = str(getattr(row, "anchor_source", "")).strip().lower()
        label = str(getattr(row, "anchor_label", "")).strip()
        point = _source_anchor_point(source, label, stations_df=stations_df, events_df=events_df)
        marker = "o"
        color = "#ff00a8"
        if point is None and hasattr(row, "anchor_lon") and hasattr(row, "anchor_lat"):
            point = (float(getattr(row, "anchor_lon")), float(getattr(row, "anchor_lat")))
            marker = "X"
            color = "#111111"
        if point is None:
            continue
        legend_label = "Corridor anchor" if "Corridor anchor" not in plotted_labels else None
        ax.scatter(
            [point[0]],
            [point[1]],
            s=120,
            marker=marker,
            facecolor=color,
            edgecolor="white",
            linewidth=1.2,
            zorder=8,
            label=legend_label,
        )
        plotted_labels.add("Corridor anchor")
        ax.text(
            point[0],
            point[1],
            f"  {label}",
            fontsize=7.0,
            fontweight="bold",
            color="black",
            va="center",
            ha="left",
            zorder=9,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.68, "pad": 0.8},
        )


def _source_anchor_point(
    source: str,
    label: str,
    *,
    stations_df: pd.DataFrame | None,
    events_df: pd.DataFrame | None,
) -> tuple[float, float] | None:
    """Return the source station/event coordinates for an anchor label.

    Parameters
    ----------
    source
        Anchor source type.
    label
        Anchor station or event identifier.
    stations_df, events_df
        Optional metadata tables.

    Returns
    -------
    tuple[float, float] or None
        Longitude and latitude for the source anchor.
    """

    if source == "station" and stations_df is not None and not stations_df.empty:
        id_col = next((column for column in ("station", "station_code", "sta") if column in stations_df.columns), None)
        if id_col is not None:
            matches = stations_df.loc[stations_df[id_col].astype(str).eq(label)]
            if not matches.empty:
                lon, lat = _resolve_xy(matches, lon_candidates=["station_lon", "station_longitude", "sta_lon", "lon", "longitude"], lat_candidates=["station_lat", "station_latitude", "sta_lat", "lat", "latitude"], label="station")
                return float(matches.iloc[0][lon]), float(matches.iloc[0][lat])
    if source == "event" and events_df is not None and not events_df.empty:
        id_col = next((column for column in ("event_id", "event", "id") if column in events_df.columns), None)
        if id_col is not None:
            matches = events_df.loc[events_df[id_col].astype(str).eq(label)]
            if not matches.empty:
                lon, lat = _resolve_xy(matches, lon_candidates=["event_lon", "event_longitude", "source_lon", "source_longitude", "lon", "longitude"], lat_candidates=["event_lat", "event_latitude", "source_lat", "source_latitude", "lat", "latitude"], label="event")
                return float(matches.iloc[0][lon]), float(matches.iloc[0][lat])
    return None


def _plot_geometry_outline(ax: plt.Axes, geometry: object) -> None:
    """Plot one Polygon or MultiPolygon outline.

    Parameters
    ----------
    ax
        Matplotlib axes.
    geometry
        Shapely Polygon-like geometry.

    Returns
    -------
    None
        Mutates ``ax``.
    """

    geoms = geometry.geoms if hasattr(geometry, "geoms") else [geometry]
    for geom in geoms:
        if hasattr(geom, "exterior"):
            x, y = geom.exterior.xy
            ax.plot(x, y, color="#202020", linewidth=1.0, alpha=0.85, zorder=4)


def _plot_paths(ax: plt.Axes, records_df: pd.DataFrame) -> None:
    """Plot event-station paths from a record table.

    Parameters
    ----------
    ax
        Matplotlib axes.
    records_df
        Event-station records with event and station coordinates.

    Returns
    -------
    None
        Mutates ``ax``.
    """

    sta_lon, sta_lat = _resolve_xy(records_df, lon_candidates=["station_lon", "station_longitude", "sta_lon"], lat_candidates=["station_lat", "station_latitude", "sta_lat"], label="station")
    ev_lon, ev_lat = _resolve_xy(records_df, lon_candidates=["event_lon", "event_longitude", "source_lon", "source_longitude"], lat_candidates=["event_lat", "event_latitude", "source_lat", "source_latitude"], label="event")
    for row in records_df.itertuples(index=False):
        ax.plot([getattr(row, ev_lon), getattr(row, sta_lon)], [getattr(row, ev_lat), getattr(row, sta_lat)], color="#202020", alpha=0.58, linewidth=1.15, zorder=5)


def _resolve_xy(df: pd.DataFrame, *, lon_candidates: list[str], lat_candidates: list[str], label: str) -> tuple[str, str]:
    """Resolve longitude/latitude columns from candidate names.

    Parameters
    ----------
    df
        Input dataframe.
    lon_candidates, lat_candidates
        Candidate coordinate columns.
    label
        Point label used in errors.

    Returns
    -------
    tuple[str, str]
        Longitude and latitude column names.
    """

    lon = next((column for column in lon_candidates if column in df.columns), None)
    lat = next((column for column in lat_candidates if column in df.columns), None)
    if lon is None or lat is None:
        raise KeyError(f"Could not resolve {label} longitude/latitude columns.")
    return lon, lat


def _set_bounds_from_layers(
    ax: plt.Axes,
    corridors_df: pd.DataFrame,
    *,
    stations_df: pd.DataFrame | None,
    events_df: pd.DataFrame | None,
    records_df: pd.DataFrame | None,
) -> None:
    """Set padded map bounds from all plotted layers.

    Parameters
    ----------
    ax
        Matplotlib axes.
    corridors_df
        Corridor table.
    stations_df, events_df, records_df
        Optional context layers.

    Returns
    -------
    None
        Mutates ``ax``.
    """

    xs: list[float] = []
    ys: list[float] = []
    for geom in corridors_df.get("corridor_geometry", []):
        if geom is not None and not geom.is_empty:
            x, y = geom.exterior.xy
            xs.extend(list(x))
            ys.extend(list(y))
    for frame, lon_candidates, lat_candidates, label in [
        (stations_df, ["station_lon", "station_longitude", "sta_lon", "lon", "longitude"], ["station_lat", "station_latitude", "sta_lat", "lat", "latitude"], "station"),
        (events_df, ["event_lon", "event_longitude", "source_lon", "source_longitude", "lon", "longitude"], ["event_lat", "event_latitude", "source_lat", "source_latitude", "lat", "latitude"], "event"),
        (records_df, ["station_lon", "station_longitude", "sta_lon"], ["station_lat", "station_latitude", "sta_lat"], "station"),
        (records_df, ["event_lon", "event_longitude", "source_lon", "source_longitude"], ["event_lat", "event_latitude", "source_lat", "source_latitude"], "event"),
    ]:
        if frame is None or frame.empty:
            continue
        lon, lat = _resolve_xy(frame, lon_candidates=lon_candidates, lat_candidates=lat_candidates, label=label)
        xs.extend(pd.to_numeric(frame[lon], errors="coerce").dropna().tolist())
        ys.extend(pd.to_numeric(frame[lat], errors="coerce").dropna().tolist())
    x_arr = np.asarray(xs, dtype=float)
    y_arr = np.asarray(ys, dtype=float)
    finite = np.isfinite(x_arr) & np.isfinite(y_arr)
    if not finite.any():
        return
    west, east = float(np.nanmin(x_arr[finite])), float(np.nanmax(x_arr[finite]))
    south, north = float(np.nanmin(y_arr[finite])), float(np.nanmax(y_arr[finite]))
    pad_x = max(0.03, 0.08 * max(east - west, 0.01))
    pad_y = max(0.03, 0.08 * max(north - south, 0.01))
    ax.set_xlim(west - pad_x, east + pad_x)
    ax.set_ylim(south - pad_y, north + pad_y)
    _set_geographic_aspect(ax)


def _set_geographic_aspect(ax: plt.Axes) -> None:
    """Preserve lon/lat proportions on corridor map axes."""

    lat_min, lat_max = ax.get_ylim()
    lat_mid = 0.5 * (float(lat_min) + float(lat_max))
    cos_lat = math.cos(math.radians(lat_mid))
    if math.isfinite(cos_lat) and abs(cos_lat) > 1.0e-6:
        ax.set_aspect(1.0 / cos_lat, adjustable="box")
