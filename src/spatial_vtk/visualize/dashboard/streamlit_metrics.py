"""Streamlit Metrics Explorer entrypoint.

Purpose
-------
This module is executed by Streamlit to explore dashboard-ready metric tables.
Filtering, plotting, and map construction are delegated to normal package
helpers so the app stays thin and testable.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from spatial_vtk.config.runtime import SpatialVTKConfig
from spatial_vtk.visualize.dashboard.charts import (
    build_metric_heatmap_figure,
    build_path_heatmap_figure,
    build_value_histogram_figure,
    build_value_vs_distance_figure,
)
from spatial_vtk.visualize.dashboard.contracts import load_dashboard_summary_tables, load_metric_long_table, validate_dashboard_tables
from spatial_vtk.visualize.dashboard.filters import filter_dashboard_metrics
from spatial_vtk.config.labels import (
    available_dashboard_value_columns,
    band_display_label,
    display_table,
    metric_display_name,
    normalize_metric_name,
    value_column_display_name,
)
from spatial_vtk.visualize.dashboard.maps import BASEMAPS, build_event_folium_map, build_station_folium_map, render_folium_html
from spatial_vtk.visualize.selection import FigureSelection, configured_band_options


def main() -> None:
    """Run the Streamlit Metrics Explorer."""

    st.set_page_config(page_title="Spatial-VTK Metrics Explorer", layout="wide")
    st.title("Spatial-VTK Metrics Explorer")
    metrics_root = _path_setting("metrics_root", "SVTK_METRICS_ROOT")
    summary_root = _path_setting("summary_root", "SVTK_SUMMARY_ROOT")
    config_path = _path_setting("config", "SVTK_CONFIG_FILE")
    if not summary_root:
        st.info("Choose a dashboard summary directory to begin.")
        summary_root = st.text_input("Dashboard summary directory", value="")
        if not summary_root:
            return
    try:
        summaries = validate_dashboard_tables(load_dashboard_summary_tables(summary_root))
    except Exception as exc:
        st.error(str(exc))
        return
    long_metrics = _try_load_long_metrics(metrics_root)
    config = _load_optional_config(config_path)
    _render_metrics_dashboard(summaries, long_metrics, config)


def _render_metrics_dashboard(summaries: dict[str, pd.DataFrame], long_metrics: pd.DataFrame | None, config: SpatialVTKConfig | None = None) -> None:
    """Render the metrics dashboard body."""

    all_metrics = sorted({normalize_metric_name(value) for value in summaries["model_metric_band"]["metric"].dropna().astype(str)}, key=metric_display_name)
    all_models = sorted(summaries["model_metric_band"]["model"].dropna().astype(str).unique().tolist())
    data_bands = sorted(summaries["model_metric_band"]["band"].dropna().astype(str).unique().tolist(), key=band_display_label)
    configured_bands = configured_band_options(config, command="metrics.dashboard", fallback_df=summaries["model_metric_band"])
    all_bands = _merged_options(configured_bands, data_bands, key=band_display_label)
    component_options = _component_options(config, summaries, long_metrics)

    with st.sidebar:
        st.header("Filters")
        selected_models = st.multiselect("Models", options=all_models, default=all_models)
        selected_metric = st.selectbox("Metric", options=all_metrics, format_func=metric_display_name)
        selected_bands = st.multiselect("Passbands", options=all_bands, default=data_bands or all_bands, format_func=band_display_label)
        selected_component = st.selectbox("Component", options=component_options) if component_options else "all"
        value_source = filter_dashboard_metrics(
            summaries["model_metric_band"],
            models=selected_models,
            metric=selected_metric,
            bands=selected_bands,
            component=None if selected_component in {"", "all"} else selected_component,
        )
        value_columns = _available_nonempty_value_columns(value_source)
        if not value_columns:
            st.error("No observed, synthetic, residual, or score value columns are available for the selected filters.")
            return
        value_col = st.selectbox("Displayed Value", options=value_columns, format_func=value_column_display_name)
        distance_range = _range_slider_from_columns("Distance (km)", summaries["station_rollup"], ("med_dist_km", "distance_km"))
        vs30_range = _range_slider_from_columns("Vs30", summaries["station_rollup"], ("Vs30", "vs30"))
        basemap = st.selectbox("Basemap", options=list(BASEMAPS), index=list(BASEMAPS).index("Carto Light"))
        marker_cluster = st.checkbox("Cluster map markers", value=True)
        max_markers = st.number_input("Maximum map markers", min_value=100, max_value=50000, value=3000, step=100)

    component_filter = None if selected_component in {"", "all"} else selected_component
    heat = filter_dashboard_metrics(summaries["model_metric_band"], models=selected_models, metric=selected_metric, bands=selected_bands, value_column=value_col, component=component_filter)
    stations = filter_dashboard_metrics(summaries["station_rollup"], models=selected_models, metric=selected_metric, bands=selected_bands, value_column=value_col, distance_range_km=distance_range, vs30_range=vs30_range, component=component_filter)
    events = filter_dashboard_metrics(summaries["event_rollup"], models=selected_models, metric=selected_metric, bands=selected_bands, value_column=value_col, distance_range_km=distance_range, component=component_filter)
    paths = filter_dashboard_metrics(summaries["path_hex"], models=selected_models, metric=selected_metric, bands=selected_bands, value_column=value_col, component=component_filter)
    rows = None
    if long_metrics is not None:
        row_value = _row_value_column(value_col, long_metrics)
        rows = filter_dashboard_metrics(long_metrics, models=selected_models, metric=selected_metric, bands=selected_bands, value_column=row_value if row_value else None, distance_range_km=distance_range, vs30_range=vs30_range, component=component_filter)

    overview_tab, station_tab, event_tab, path_tab, distribution_tab, compare_tab = st.tabs(["Overview", "Stations", "Events", "Paths", "Distributions", "Compare Models"])
    with overview_tab:
        cols = st.columns(4)
        cols[0].metric("Rows", f"{len(rows) if rows is not None else len(heat):,}")
        cols[1].metric("Models", f"{len(selected_models):,}")
        cols[2].metric("Metrics", f"{heat['metric'].nunique() if 'metric' in heat else 0:,}")
        cols[3].metric("Passbands", f"{len(selected_bands):,}")
        st.plotly_chart(build_metric_heatmap_figure(heat, value_col=value_col), width="stretch")
        st.dataframe(_display_table(heat), width="stretch")
    with station_tab:
        st_folium(build_station_folium_map(stations, value_col=value_col, basemap=basemap, marker_cluster=marker_cluster, max_markers=int(max_markers)), use_container_width=True, height=620)
        st.download_button("Download station map HTML", render_folium_html(build_station_folium_map(stations, value_col=value_col, basemap=basemap, marker_cluster=marker_cluster, max_markers=int(max_markers))), file_name="station_metric_map.html")
        st.dataframe(_display_table(stations), width="stretch")
    with event_tab:
        st_folium(build_event_folium_map(events, value_col=value_col, basemap=basemap, marker_cluster=marker_cluster, max_markers=int(max_markers)), use_container_width=True, height=560)
        st.dataframe(_display_table(events), width="stretch")
    with path_tab:
        st.plotly_chart(build_path_heatmap_figure(paths, value_col=value_col), width="stretch")
        st.dataframe(_display_table(paths), width="stretch")
    with distribution_tab:
        if rows is None or rows.empty:
            st.info("Load the long metrics dataset to view row-level distributions.")
        else:
            row_value = _row_value_column(value_col, rows) or value_col
            st.plotly_chart(build_value_histogram_figure(rows, value_col=row_value), width="stretch")
            if {"distance_km", "med_dist_km"} & set(rows.columns):
                st.plotly_chart(build_value_vs_distance_figure(rows, value_col=row_value), width="stretch")
            st.download_button("Download filtered metric rows", rows.to_csv(index=False).encode("utf-8"), file_name="filtered_metrics.csv")
    with compare_tab:
        st.plotly_chart(build_metric_heatmap_figure(heat, value_col=value_col, title="Model Comparison"), width="stretch")
        st.dataframe(_display_table(heat), width="stretch")


@st.cache_data(show_spinner=False)
def _load_summary_tables_cached(summary_root: str) -> dict[str, pd.DataFrame]:
    """Load summary tables with Streamlit caching."""

    return validate_dashboard_tables(load_dashboard_summary_tables(summary_root))


@st.cache_data(show_spinner=False)
def _load_long_metrics_cached(metrics_root: str) -> pd.DataFrame:
    """Load long metrics with Streamlit caching."""

    return load_metric_long_table(metrics_root)


def _try_load_long_metrics(metrics_root: str) -> pd.DataFrame | None:
    """Load long metrics when a root is configured."""

    if not metrics_root:
        return None
    try:
        return _load_long_metrics_cached(metrics_root)
    except Exception as exc:
        st.warning(f"Long metric table was not loaded: {exc}")
        return None


def _path_setting(query_key: str, env_key: str) -> str:
    """Read one app path setting."""

    value = st.query_params.get(query_key, "")
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or os.environ.get(env_key, "")).strip()


def _load_optional_config(config_path: str) -> SpatialVTKConfig | None:
    """Load a dashboard config when one is explicitly configured."""

    if not config_path:
        return None
    try:
        return SpatialVTKConfig.from_file(config_path)
    except Exception as exc:
        st.warning(f"Spatial-VTK config was not loaded: {exc}")
        return None


def _merged_options(primary: list[str], secondary: list[str], *, key) -> list[str]:
    """Merge option lists while preserving unique string values."""

    seen: set[str] = set()
    out: list[str] = []
    for item in [*primary, *secondary]:
        token = str(item)
        if token not in seen:
            seen.add(token)
            out.append(token)
    return sorted(out, key=key)


def _component_options(config: SpatialVTKConfig | None, summaries: dict[str, pd.DataFrame], long_metrics: pd.DataFrame | None) -> list[str]:
    """Return configured and detected component options."""

    configured = list(FigureSelection.from_config(config, command="metrics.dashboard").components) if config is not None else []
    detected: list[str] = []
    for frame in [*summaries.values(), long_metrics]:
        if frame is None or "component" not in frame.columns:
            continue
        detected.extend(frame["component"].dropna().astype(str).str.upper().unique().tolist())
    options = _merged_options(configured, detected, key=str)
    return ["all", *options] if options else []


def _range_slider_from_columns(label: str, df: pd.DataFrame, columns: tuple[str, ...]) -> tuple[float | None, float | None] | None:
    """Build a range slider for the first available numeric column."""

    column = next((item for item in columns if item in df.columns), None)
    if column is None:
        return None
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return None
    lower, upper = float(values.min()), float(values.max())
    if lower == upper:
        return (lower, upper)
    return st.slider(label, min_value=lower, max_value=upper, value=(lower, upper))


def _row_value_column(summary_value_col: str, rows: pd.DataFrame) -> str | None:
    """Map a summary value column back to a row-level value column."""

    candidates = [summary_value_col]
    if summary_value_col == "med_resid":
        candidates.append("residual")
    elif summary_value_col.startswith("med_"):
        candidates.append(summary_value_col.removeprefix("med_"))
    for candidate in candidates:
        if candidate in rows.columns:
            return candidate
    return None


def _available_nonempty_value_columns(df: pd.DataFrame) -> list[str]:
    """Return selectable value columns that have finite data for current filters."""

    columns = available_dashboard_value_columns(df)
    nonempty = [
        column
        for column in columns
        if column in df.columns and pd.to_numeric(df[column], errors="coerce").notna().any()
    ]
    return nonempty or columns


def _display_table(df: pd.DataFrame) -> pd.DataFrame:
    """Return a dashboard table with human-readable values and headers."""

    return display_table(df)


if __name__ == "__main__":
    main()
