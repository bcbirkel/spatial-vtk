"""Geographic metric map figures."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from spatial_vtk.config.labels import model_display_name, value_column_display_name
from spatial_vtk.spatial.calculate.geojson import load_geojson_polygons, select_geojson_polygons
from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
from spatial_vtk.visualize.figure_context import apply_figure_context, value_color_settings
from spatial_vtk.visualize.figure_io import finish_figure
from spatial_vtk.visualize.selection import FigureSpatialSelection, apply_figure_spatial_selection


def plot_station_metric_map(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    value_col: str = "residual",
    lon_col: str = "sta_lon",
    lat_col: str = "sta_lat",
    corridors_df: pd.DataFrame | None = None,
    events_df: pd.DataFrame | None = None,
    records_df: pd.DataFrame | None = None,
    geojson_path: str | Path | None = None,
    polygon_selector: object = "all",
    polygon_alpha: float = 0.16,
    label_polygons: bool = False,
    event_alpha: float = 0.78,
    title: str = "Station Metric Map",
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Plot station-level metric values on a map."""

    return _point_metric_map(
        df,
        output_path,
        value_col=value_col,
        lon_col=lon_col,
        lat_col=lat_col,
        corridors_df=corridors_df,
        events_df=events_df,
        records_df=records_df,
        geojson_path=geojson_path,
        polygon_selector=polygon_selector,
        polygon_alpha=polygon_alpha,
        label_polygons=label_polygons,
        event_alpha=event_alpha,
        title=title,
        add_basemap=add_basemap,
        basemap_source=basemap_source,
        basemap_kwargs=basemap_kwargs,
        showfig=showfig,
        savefig=savefig,
        outpath=outpath,
        spatial_selection=spatial_selection,
        **spatial_kwargs,
    )


def plot_score_map(df: pd.DataFrame, output_path: str | Path | None = None, *, score_col: str = "score", **kwargs) -> plt.Figure:
    """Plot station or path scores on a map."""

    return _point_metric_map(df, output_path, value_col=score_col, title=kwargs.pop("title", "Score Map"), **kwargs)


def plot_residual_grid(
    grid_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    lon_col: str = "lon",
    lat_col: str = "lat",
    value_col: str = "residual",
    cell_size_deg: float | tuple[float, float] | None = None,
    title: str = "Residual Grid",
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot gridded residual values on geographic axes.

    Inputs are lon/lat/value rows where lon/lat are grid-cell centers. When
    ``cell_size_deg`` is set, rows are aggregated onto that lon/lat cell size
    before plotting so the map boxes have an explicit visual footprint.
    Returns a Matplotlib figure.
    """

    _require(grid_df, [lon_col, lat_col, value_col])
    plot_df = _coarsen_grid(grid_df, lon_col=lon_col, lat_col=lat_col, value_col=value_col, cell_size_deg=cell_size_deg)
    pivot = plot_df.pivot_table(index=lat_col, columns=lon_col, values=value_col, aggfunc="mean")
    values = pivot.to_numpy(dtype=float)
    cmap, vmin, vmax = _color_settings(values, value_col)
    fig, ax = plt.subplots(figsize=(8.0, 6.8), dpi=180, constrained_layout=True)
    dx, dy = _grid_cell_spacing(pivot, cell_size_deg=cell_size_deg)
    west = float(pivot.columns.min()) - 0.5 * dx
    east = float(pivot.columns.max()) + 0.5 * dx
    south = float(pivot.index.min()) - 0.5 * dy
    north = float(pivot.index.max()) + 0.5 * dy
    ax.set_xlim(west, east)
    ax.set_ylim(south, north)
    if add_basemap:
        add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **dict(basemap_kwargs or {}))
    image = ax.imshow(values, extent=(west, east, south, north), origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, alpha=0.72, zorder=3, aspect="auto")
    _set_geographic_aspect(ax)
    fig.colorbar(image, ax=ax, pad=0.045, label=value_column_display_name(value_col))
    _finish(ax, title, plot_df, value_col=value_col)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_metric_map_by_model(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    model_col: str = "model",
    value_col: str = "residual",
    lon_col: str = "sta_lon",
    lat_col: str = "sta_lat",
    max_models: int = 4,
    title: str = "Metric Map by Model",
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Plot station metric maps faceted by model."""

    plot_df, subset_label = apply_figure_spatial_selection(df, spatial_selection, **spatial_kwargs)
    _require(plot_df, [model_col, value_col, lon_col, lat_col])
    models = list(plot_df[model_col].dropna().astype(str).unique())[: int(max_models)]
    fig, axes = plt.subplots(1, max(len(models), 1), figsize=(5.8 * max(len(models), 1), 3.8), dpi=180, squeeze=False)
    axes_flat = axes.ravel()
    values_all = pd.to_numeric(plot_df[value_col], errors="coerce")
    cmap, vmin, vmax = _color_settings(values_all.to_numpy(dtype=float), value_col)
    for ax, model in zip(axes_flat, models or [""]):
        subset = plot_df.loc[plot_df[model_col].astype(str) == model] if models else plot_df
        _set_bounds(ax, subset, lon_col, lat_col)
        if add_basemap:
            add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **dict(basemap_kwargs or {}))
        scatter = ax.scatter(subset[lon_col], subset[lat_col], c=pd.to_numeric(subset[value_col], errors="coerce"), cmap=cmap, vmin=vmin, vmax=vmax, s=38, edgecolors="black", linewidths=0.3, zorder=4)
        _finish(ax, model_display_name(model) if model else title, subset, value_col=value_col, include_counts=False, include_model=False, include_metric=False, include_period=False)
    fig.subplots_adjust(left=0.055, right=0.86, bottom=0.16, top=0.74, wspace=0.20)
    cbar_ax = fig.add_axes([0.895, 0.20, 0.018, 0.48])
    fig.colorbar(scatter, cax=cbar_ax, label=value_column_display_name(value_col))
    fig.suptitle(f"{title}\n{subset_label}" if subset_label else title, y=0.96)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_model_improvement_map(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    improvement_col: str = "improvement",
    title: str = "Model Improvement Map",
    **kwargs,
) -> plt.Figure:
    """Plot model improvement values on a map."""

    return _point_metric_map(df, output_path, value_col=improvement_col, title=title, **kwargs)


def _point_metric_map(
    df: pd.DataFrame,
    output_path: str | Path | None,
    *,
    value_col: str,
    lon_col: str = "sta_lon",
    lat_col: str = "sta_lat",
    corridors_df: pd.DataFrame | None = None,
    events_df: pd.DataFrame | None = None,
    records_df: pd.DataFrame | None = None,
    geojson_path: str | Path | None = None,
    polygon_selector: object = "all",
    polygon_alpha: float = 0.16,
    label_polygons: bool = False,
    event_alpha: float = 0.78,
    title: str,
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    **spatial_kwargs: object,
) -> plt.Figure:
    """Draw a point metric map."""

    plot_df, subset_label = apply_figure_spatial_selection(df, spatial_selection, **spatial_kwargs)
    _require(plot_df, [value_col, lon_col, lat_col])
    values = pd.to_numeric(plot_df[value_col], errors="coerce")
    cmap, vmin, vmax = _color_settings(values.to_numpy(dtype=float), value_col)
    polygon_features = _selected_geojson_features(geojson_path, polygon_selector)
    fig, ax = plt.subplots(figsize=(8.0, 6.8), dpi=180, constrained_layout=True)
    _set_bounds_from_layers(
        ax,
        plot_df,
        lon_col,
        lat_col,
        corridors_df=corridors_df,
        events_df=events_df,
        records_df=records_df,
        polygon_features=polygon_features,
    )
    if add_basemap:
        add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **dict(basemap_kwargs or {}))
    _draw_geojson_overlays(ax, polygon_features, alpha=polygon_alpha, label_polygons=label_polygons)
    _draw_corridor_overlays(ax, corridors_df)
    _draw_path_overlays(ax, records_df)
    _draw_event_overlays(ax, events_df, alpha=event_alpha)
    point_label = "Stations" if corridors_df is not None or events_df is not None or records_df is not None else None
    scatter = ax.scatter(plot_df[lon_col], plot_df[lat_col], c=values, cmap=cmap, vmin=vmin, vmax=vmax, s=42, edgecolors="black", linewidths=0.3, zorder=4, label=point_label)
    fig.colorbar(scatter, ax=ax, pad=0.045, label=value_column_display_name(value_col))
    _finish(ax, title, plot_df, value_col=value_col, extra=[subset_label] if subset_label else None)
    if corridors_df is not None or events_df is not None or records_df is not None:
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(handles, labels, loc="best", frameon=True)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _require(df: pd.DataFrame, columns: list[str]) -> None:
    """Raise a clear error for missing columns."""

    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")


def _coarsen_grid(
    df: pd.DataFrame,
    *,
    lon_col: str,
    lat_col: str,
    value_col: str,
    cell_size_deg: float | tuple[float, float] | None,
) -> pd.DataFrame:
    """Aggregate residual-grid rows to an explicit lon/lat cell size.

    Inputs are a grid dataframe, coordinate/value column names, and an optional
    cell size in degrees. The output is a dataframe with rounded grid-center
    coordinates and mean values per cell, while preserving representative
    context columns for figure labeling.
    """

    out = df.copy()
    if cell_size_deg is None:
        return out
    dx, dy = _resolve_cell_size(cell_size_deg)
    lon = pd.to_numeric(out[lon_col], errors="coerce")
    lat = pd.to_numeric(out[lat_col], errors="coerce")
    out = out.loc[lon.notna() & lat.notna()].copy()
    if out.empty:
        return out
    lon = pd.to_numeric(out[lon_col], errors="coerce")
    lat = pd.to_numeric(out[lat_col], errors="coerce")
    lon_origin = float(np.floor(lon.min() / dx) * dx)
    lat_origin = float(np.floor(lat.min() / dy) * dy)
    out[lon_col] = lon_origin + (np.floor((lon - lon_origin) / dx) + 0.5) * dx
    out[lat_col] = lat_origin + (np.floor((lat - lat_origin) / dy) + 0.5) * dy
    context_cols = [column for column in ("metric", "model", "band", "component") if column in out.columns]
    grouped = out.groupby([lat_col, lon_col], as_index=False, dropna=False)
    values = grouped[value_col].mean()
    if context_cols:
        context = grouped[context_cols].first()
        values = values.merge(context, on=[lat_col, lon_col], how="left")
    return values


def _grid_cell_spacing(pivot: pd.DataFrame, *, cell_size_deg: float | tuple[float, float] | None) -> tuple[float, float]:
    """Return lon/lat cell spacing for residual-grid image extents.

    Inputs are the plotted pivot table and optional explicit cell size. The
    output is ``(dx, dy)`` in degrees, used to draw cells around their centers.
    """

    if cell_size_deg is not None:
        return _resolve_cell_size(cell_size_deg)
    lon_values = np.asarray(pivot.columns, dtype=float)
    lat_values = np.asarray(pivot.index, dtype=float)
    dx = _median_spacing(lon_values)
    dy = _median_spacing(lat_values)
    return dx, dy


def _resolve_cell_size(cell_size_deg: float | tuple[float, float]) -> tuple[float, float]:
    """Normalize scalar or ``(lon, lat)`` residual-grid cell sizes.

    Inputs are a scalar degree size or two-element tuple. The output is a
    positive ``(dx, dy)`` tuple in degrees.
    """

    if isinstance(cell_size_deg, tuple):
        if len(cell_size_deg) != 2:
            raise ValueError("cell_size_deg tuple must be (lon_size_deg, lat_size_deg).")
        dx, dy = float(cell_size_deg[0]), float(cell_size_deg[1])
    else:
        dx = dy = float(cell_size_deg)
    if dx <= 0 or dy <= 0:
        raise ValueError("cell_size_deg values must be positive.")
    return dx, dy


def _median_spacing(values: np.ndarray) -> float:
    """Infer a stable grid spacing from sorted coordinate values.

    Inputs are coordinate centers. The output is the median positive spacing,
    with a small fallback for degenerate one-cell grids.
    """

    unique = np.unique(values[np.isfinite(values)])
    if unique.size < 2:
        return 0.05
    diffs = np.diff(np.sort(unique))
    diffs = diffs[diffs > 0]
    if diffs.size == 0:
        return 0.05
    return float(np.median(diffs))


def _set_bounds(ax: plt.Axes, df: pd.DataFrame, lon_col: str, lat_col: str) -> None:
    """Set padded map bounds."""

    lon = pd.to_numeric(df[lon_col], errors="coerce").to_numpy(dtype=float)
    lat = pd.to_numeric(df[lat_col], errors="coerce").to_numpy(dtype=float)
    finite = np.isfinite(lon) & np.isfinite(lat)
    if not np.any(finite):
        ax.set_xlim(-180, 180)
        ax.set_ylim(-90, 90)
        return
    west, east = float(np.nanmin(lon[finite])), float(np.nanmax(lon[finite]))
    south, north = float(np.nanmin(lat[finite])), float(np.nanmax(lat[finite]))
    ax.set_xlim(west - max(0.03, 0.08 * max(east - west, 0.01)), east + max(0.03, 0.08 * max(east - west, 0.01)))
    ax.set_ylim(south - max(0.03, 0.08 * max(north - south, 0.01)), north + max(0.03, 0.08 * max(north - south, 0.01)))
    _set_geographic_aspect(ax)


def _set_geographic_aspect(ax: plt.Axes) -> None:
    """Preserve geographic lon/lat proportions on map axes."""

    lat_min, lat_max = ax.get_ylim()
    lat_mid = 0.5 * (float(lat_min) + float(lat_max))
    cos_lat = math.cos(math.radians(lat_mid))
    if math.isfinite(cos_lat) and abs(cos_lat) > 1.0e-6:
        ax.set_aspect(1.0 / cos_lat, adjustable="box")


def _set_bounds_from_layers(
    ax: plt.Axes,
    df: pd.DataFrame,
    lon_col: str,
    lat_col: str,
    *,
    corridors_df: pd.DataFrame | None,
    events_df: pd.DataFrame | None,
    records_df: pd.DataFrame | None,
    polygon_features: list[object] | None,
) -> None:
    """Set map bounds from station metrics and optional corridor overlays.

    Inputs are the plotted station table plus optional corridor, event, and
    event-station path layers. The output is applied to ``ax`` so basemaps,
    paths, corridors, and residual markers share the same map extent.
    """

    xs = pd.to_numeric(df[lon_col], errors="coerce").dropna().tolist()
    ys = pd.to_numeric(df[lat_col], errors="coerce").dropna().tolist()
    for geom in [] if corridors_df is None else corridors_df.get("corridor_geometry", []):
        if geom is not None and not geom.is_empty:
            x, y = geom.exterior.xy
            xs.extend(list(x))
            ys.extend(list(y))
    for feature in polygon_features or []:
        geom = getattr(feature, "geometry", None)
        if geom is None or geom.is_empty:
            continue
        minx, miny, maxx, maxy = geom.bounds
        xs.extend([float(minx), float(maxx)])
        ys.extend([float(miny), float(maxy)])
    for frame, lon_candidates, lat_candidates, label in [
        (events_df, ["event_lon", "event_longitude", "source_lon", "source_longitude", "lon", "longitude"], ["event_lat", "event_latitude", "source_lat", "source_latitude", "lat", "latitude"], "event"),
        (records_df, ["station_lon", "station_longitude", "sta_lon"], ["station_lat", "station_latitude", "sta_lat"], "station"),
        (records_df, ["event_lon", "event_longitude", "source_lon", "source_longitude"], ["event_lat", "event_latitude", "source_lat", "source_latitude"], "event"),
    ]:
        if frame is None or frame.empty:
            continue
        resolved_lon, resolved_lat = _resolve_xy(frame, lon_candidates=lon_candidates, lat_candidates=lat_candidates, label=label)
        xs.extend(pd.to_numeric(frame[resolved_lon], errors="coerce").dropna().tolist())
        ys.extend(pd.to_numeric(frame[resolved_lat], errors="coerce").dropna().tolist())
    x_arr = np.asarray(xs, dtype=float)
    y_arr = np.asarray(ys, dtype=float)
    finite = np.isfinite(x_arr) & np.isfinite(y_arr)
    if not finite.any():
        ax.set_xlim(-180, 180)
        ax.set_ylim(-90, 90)
        return
    west, east = float(np.nanmin(x_arr[finite])), float(np.nanmax(x_arr[finite]))
    south, north = float(np.nanmin(y_arr[finite])), float(np.nanmax(y_arr[finite]))
    pad_x = max(0.03, 0.08 * max(east - west, 0.01))
    pad_y = max(0.03, 0.08 * max(north - south, 0.01))
    ax.set_xlim(west - pad_x, east + pad_x)
    ax.set_ylim(south - pad_y, north + pad_y)
    _set_geographic_aspect(ax)


def _selected_geojson_features(geojson_path: str | Path | None, selector: object) -> list[object]:
    """Load selected GeoJSON polygons for optional map context.

    Inputs are an optional GeoJSON path and selector accepted by the Spatial-VTK
    GeoJSON calculation helpers. The output is a possibly empty feature list.
    """

    if geojson_path is None:
        return []
    return select_geojson_polygons(load_geojson_polygons(geojson_path), selector)


def _draw_geojson_overlays(
    ax: plt.Axes,
    features: list[object],
    *,
    alpha: float,
    label_polygons: bool,
) -> None:
    """Draw faint GeoJSON polygons underneath station metric markers.

    Inputs are selected polygon features plus display controls. The function
    mutates the Matplotlib axes and returns nothing.
    """

    if not features:
        return
    colors = plt.get_cmap("tab10")(np.linspace(0.0, 1.0, max(len(features), 1)))
    for idx, feature in enumerate(features):
        geom = getattr(feature, "geometry", None)
        if geom is None or geom.is_empty:
            continue
        geoms = geom.geoms if hasattr(geom, "geoms") else [geom]
        for part in geoms:
            if not hasattr(part, "exterior"):
                continue
            x, y = part.exterior.xy
            ax.fill(
                x,
                y,
                facecolor=colors[idx % len(colors)],
                edgecolor="#202020",
                linewidth=1.0,
                alpha=float(alpha),
                zorder=2.8,
                label="Regions" if idx == 0 else None,
            )
            ax.plot(x, y, color="#202020", linewidth=0.85, alpha=0.55, zorder=2.9)
        if label_polygons:
            point = geom.representative_point()
            ax.text(
                point.x,
                point.y,
                str(getattr(feature, "name", "")).replace("_", " "),
                ha="center",
                va="center",
                fontsize=8,
                color="black",
                bbox={"boxstyle": "round,pad=0.18", "facecolor": "white", "edgecolor": "none", "alpha": 0.62},
                zorder=3.1,
            )


def _draw_corridor_overlays(ax: plt.Axes, corridors_df: pd.DataFrame | None) -> None:
    """Draw corridor polygons on a station metric map.

    Inputs are corridor rows containing ``corridor_geometry`` polygons. The
    function mutates ``ax`` and returns nothing.
    """

    if corridors_df is None or corridors_df.empty:
        return
    for idx, geom in enumerate(corridors_df.get("corridor_geometry", [])):
        if geom is None or geom.is_empty:
            continue
        x, y = geom.exterior.xy
        ax.fill(
            x,
            y,
            facecolor="#ffb000",
            edgecolor="#202020",
            linewidth=1.1,
            alpha=0.28,
            zorder=3,
            label="Corridor" if idx == 0 else None,
        )


def _draw_path_overlays(ax: plt.Axes, records_df: pd.DataFrame | None) -> None:
    """Draw selected event-station paths on a station metric map.

    Inputs are event-station rows with event and station coordinates. The
    function mutates ``ax`` and returns nothing.
    """

    if records_df is None or records_df.empty:
        return
    sta_lon, sta_lat = _resolve_xy(records_df, lon_candidates=["station_lon", "station_longitude", "sta_lon"], lat_candidates=["station_lat", "station_latitude", "sta_lat"], label="station")
    ev_lon, ev_lat = _resolve_xy(records_df, lon_candidates=["event_lon", "event_longitude", "source_lon", "source_longitude"], lat_candidates=["event_lat", "event_latitude", "source_lat", "source_latitude"], label="event")
    for idx, row in enumerate(records_df.itertuples(index=False)):
        ax.plot(
            [getattr(row, ev_lon), getattr(row, sta_lon)],
            [getattr(row, ev_lat), getattr(row, sta_lat)],
            color="#202020",
            alpha=0.42,
            linewidth=0.9,
            zorder=3.5,
            label="Selected paths" if idx == 0 else None,
        )


def _draw_event_overlays(ax: plt.Axes, events_df: pd.DataFrame | None, *, alpha: float = 0.78) -> None:
    """Draw event points on a station metric map.

    Inputs are event rows with longitude and latitude columns. The function
    mutates ``ax`` and returns nothing.
    """

    if events_df is None or events_df.empty:
        return
    event_lon, event_lat = _resolve_xy(
        events_df,
        lon_candidates=["event_lon", "event_longitude", "source_lon", "source_longitude", "lon", "longitude"],
        lat_candidates=["event_lat", "event_latitude", "source_lat", "source_latitude", "lat", "latitude"],
        label="event",
    )
    ax.scatter(
        events_df[event_lon],
        events_df[event_lat],
        s=96,
        marker="*",
        facecolor="#ffd92f",
        edgecolor="black",
        linewidth=0.6,
        alpha=float(alpha),
        zorder=3.6,
        label="Events",
    )


def _resolve_xy(df: pd.DataFrame, *, lon_candidates: list[str], lat_candidates: list[str], label: str) -> tuple[str, str]:
    """Resolve longitude and latitude columns from common Spatial-VTK names."""

    lon = next((column for column in lon_candidates if column in df.columns), None)
    lat = next((column for column in lat_candidates if column in df.columns), None)
    if lon is None or lat is None:
        raise KeyError(f"Could not resolve {label} longitude/latitude columns.")
    return lon, lat


def _finish(
    ax: plt.Axes,
    title: str,
    df: pd.DataFrame | None = None,
    *,
    value_col: str | None = None,
    include_counts: bool = False,
    include_model: bool = True,
    include_metric: bool = True,
    include_period: bool = True,
    extra: list[str] | None = None,
) -> None:
    """Apply common map labels."""

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    apply_figure_context(
        ax,
        df,
        value_col=value_col,
        title=title,
        max_values=3,
        include_counts=include_counts,
        include_model=include_model,
        include_metric=include_metric,
        include_period=include_period,
        include_value=False,
        max_line_chars=72,
        extra=extra,
    )
    ax.grid(True, alpha=0.18)


def _color_settings(values: np.ndarray, value_col: str) -> tuple[str, float, float]:
    """Return colormap and color limits for a metric value column."""

    return value_color_settings(values, value_col)


__all__ = [
    "plot_metric_map_by_model",
    "plot_model_improvement_map",
    "plot_residual_grid",
    "plot_score_map",
    "plot_station_metric_map",
]
