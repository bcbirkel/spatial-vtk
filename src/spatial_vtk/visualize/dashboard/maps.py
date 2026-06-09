"""Folium map builders for Streamlit dashboards."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from spatial_vtk.config.labels import band_display_label, metric_display_name, model_display_name, value_column_display_name
from spatial_vtk.visualize.dashboard.contracts import validate_map_columns
from spatial_vtk.visualize.figure_context import value_color_settings


BASEMAPS: dict[str, dict[str, str]] = {
    "OpenStreetMap": {"tiles": "OpenStreetMap", "attr": ""},
    "Carto Light": {"tiles": "CartoDB positron", "attr": ""},
    "Esri Imagery": {
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attr": "Esri World Imagery",
    },
    "Esri Terrain": {
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}",
        "attr": "Esri World Terrain",
    },
}


def build_station_folium_map(
    df: pd.DataFrame,
    *,
    value_col: str,
    basemap: str = "Carto Light",
    geojson_paths: list[str | Path] | None = None,
    marker_cluster: bool = True,
    max_markers: int = 2000,
) -> Any:
    """Build a station metric map from a dashboard station table."""

    lon_col, lat_col = validate_map_columns(df, table_name="station map", lon_candidates=("sta_lon", "station_lon", "lon", "longitude"), lat_candidates=("sta_lat", "station_lat", "lat", "latitude"))
    return _point_map(
        df,
        value_col=value_col,
        lon_col=lon_col,
        lat_col=lat_col,
        label_cols=("station", "model", "metric", "band", "n", "Vs30", "med_dist_km"),
        basemap=basemap,
        geojson_paths=geojson_paths,
        marker_cluster=marker_cluster,
        max_markers=max_markers,
    )


def build_event_folium_map(
    df: pd.DataFrame,
    *,
    value_col: str,
    basemap: str = "Carto Light",
    geojson_paths: list[str | Path] | None = None,
    marker_cluster: bool = True,
    max_markers: int = 2000,
) -> Any:
    """Build an event metric map from a dashboard event table."""

    lon_col, lat_col = validate_map_columns(df, table_name="event map", lon_candidates=("event_lon", "lon", "longitude"), lat_candidates=("event_lat", "lat", "latitude"))
    return _point_map(
        df,
        value_col=value_col,
        lon_col=lon_col,
        lat_col=lat_col,
        label_cols=("event_id", "model", "metric", "band", "n", "med_dist_km"),
        basemap=basemap,
        geojson_paths=geojson_paths,
        marker_cluster=marker_cluster,
        max_markers=max_markers,
    )


def render_folium_html(map_obj: Any) -> str:
    """Render one Folium map to HTML."""

    return map_obj.get_root().render()


def _point_map(
    df: pd.DataFrame,
    *,
    value_col: str,
    lon_col: str,
    lat_col: str,
    label_cols: tuple[str, ...],
    basemap: str,
    geojson_paths: list[str | Path] | None,
    marker_cluster: bool,
    max_markers: int,
) -> Any:
    """Build a Folium point map."""

    folium, branca, MarkerCluster = _map_dependencies()
    if value_col not in df.columns:
        raise ValueError(f"Map value column is not available: {value_col}")
    work = df.copy()
    work[lon_col] = pd.to_numeric(work[lon_col], errors="coerce")
    work[lat_col] = pd.to_numeric(work[lat_col], errors="coerce")
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
    work = work.dropna(subset=[lon_col, lat_col])
    if max_markers and len(work) > int(max_markers):
        work = work.sort_values(value_col, key=lambda series: series.abs(), ascending=False, na_position="last").head(int(max_markers))
    center = _map_center(work, lat_col, lon_col)
    spec = BASEMAPS.get(basemap, BASEMAPS["Carto Light"])
    fmap = folium.Map(location=center, zoom_start=7, tiles=None, control_scale=True)
    folium.TileLayer(tiles=spec["tiles"], attr=spec.get("attr") or None, name=basemap, control=True).add_to(fmap)
    _add_geojson_overlays(fmap, geojson_paths)
    values = work[value_col].dropna()
    colormap = _color_map(branca, values, value_col)
    layer: Any = MarkerCluster(name="Dashboard points") if marker_cluster else folium.FeatureGroup(name="Dashboard points")
    for _, row in work.iterrows():
        value = row.get(value_col)
        color = colormap(float(value)) if pd.notna(value) else "#666666"
        folium.CircleMarker(
            location=[float(row[lat_col]), float(row[lon_col])],
            radius=5,
            color="#222222",
            weight=0.8,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            popup=folium.Popup(_popup_html(row, label_cols, value_col), max_width=340),
        ).add_to(layer)
    layer.add_to(fmap)
    colormap.caption = value_column_display_name(value_col)
    colormap.add_to(fmap)
    folium.LayerControl(collapsed=True).add_to(fmap)
    return fmap


def _map_dependencies() -> tuple[Any, Any, Any]:
    """Import optional Folium dependencies."""

    try:
        import branca
        import folium
        from folium.plugins import MarkerCluster
    except Exception as exc:  # pragma: no cover - depends on optional install
        raise ImportError("Dashboard maps require folium and branca. Install spatial-vtk[dashboard].") from exc
    return folium, branca, MarkerCluster


def _map_center(df: pd.DataFrame, lat_col: str, lon_col: str) -> list[float]:
    """Return a robust map center."""

    if df.empty:
        return [0.0, 0.0]
    return [float(df[lat_col].median()), float(df[lon_col].median())]


def _color_map(branca: Any, values: pd.Series, value_col: str) -> Any:
    """Return a Folium-compatible linear color map."""

    _cmap, vmin, vmax = value_color_settings(values.to_numpy(dtype=float), value_col)
    colors = ["#2166ac", "#f7f7f7", "#b2182b"] if vmin < 0.0 < vmax else ["#f7fbff", "#08306b"]
    return branca.colormap.LinearColormap(colors=colors, vmin=vmin, vmax=vmax)


def _popup_html(row: pd.Series, label_cols: tuple[str, ...], value_col: str) -> str:
    """Build compact popup HTML for one point."""

    pieces = [f"<b>{value_column_display_name(value_col)}</b>: {_format_value(row.get(value_col))}"]
    for column in label_cols:
        if column in row.index and pd.notna(row[column]):
            label = column.replace("_", " ").title()
            value = row[column]
            if column == "metric":
                value = metric_display_name(value)
            elif column == "band":
                value = band_display_label(value)
            elif column == "model":
                value = model_display_name(value)
            pieces.append(f"<b>{label}</b>: {_format_value(value)}")
    return "<br>".join(pieces)


def _format_value(value: object) -> str:
    """Format a popup value."""

    try:
        numeric = float(value)
    except Exception:
        return str(value)
    if np.isfinite(numeric):
        return f"{numeric:.4g}"
    return ""


def _add_geojson_overlays(fmap: Any, paths: list[str | Path] | None) -> None:
    """Add optional GeoJSON overlays to one map."""

    if not paths:
        return
    folium, _, _ = _map_dependencies()
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if path.exists():
            folium.GeoJson(str(path), name=path.stem, style_function=lambda _feature: {"fillOpacity": 0.05, "weight": 2}).add_to(fmap)


__all__ = ["BASEMAPS", "build_event_folium_map", "build_station_folium_map", "render_folium_html"]
