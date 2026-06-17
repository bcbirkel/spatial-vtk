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
from spatial_vtk.visualize.dashboard.contracts import (
    dashboard_map_readiness,
    dashboard_summary_readiness_frame,
    load_dashboard_summary_tables,
    load_metric_long_table,
    validate_dashboard_tables,
)
from spatial_vtk.visualize.dashboard.filters import (
    filter_dashboard_metrics,
    filter_optional_dashboard_summary,
    row_value_column_for_summary,
)
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
        readiness = dashboard_summary_readiness_frame(summary_root, create_parent=False)
    except Exception as exc:
        st.error(str(exc))
        return
    _render_dashboard_readiness(readiness)
    blocker = _metrics_dashboard_startup_blocker(readiness)
    if blocker:
        st.warning(blocker)
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
    if not all_metrics or not all_models or not all_bands:
        st.info("The model/metric/passband summary is empty, so dashboard filters cannot be built yet.")
        st.dataframe(_display_table(summaries["model_metric_band"]), width="stretch")
        return

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
    stations, station_value_message = filter_optional_dashboard_summary(
        summaries["station_rollup"],
        table_label="station",
        value_column=value_col,
        models=selected_models,
        metric=selected_metric,
        bands=selected_bands,
        distance_range_km=distance_range,
        vs30_range=vs30_range,
        component=component_filter,
    )
    events, event_value_message = filter_optional_dashboard_summary(
        summaries["event_rollup"],
        table_label="event",
        value_column=value_col,
        models=selected_models,
        metric=selected_metric,
        bands=selected_bands,
        distance_range_km=distance_range,
        component=component_filter,
    )
    paths, path_value_message = filter_optional_dashboard_summary(
        summaries["path_hex"],
        table_label="path",
        value_column=value_col,
        models=selected_models,
        metric=selected_metric,
        bands=selected_bands,
        component=component_filter,
    )
    rows = None
    row_value = None
    row_value_message = None
    if long_metrics is not None:
        row_value = row_value_column_for_summary(value_col, long_metrics)
        if row_value is None:
            row_value_message = _missing_row_value_message(value_col)
        else:
            rows = filter_dashboard_metrics(long_metrics, models=selected_models, metric=selected_metric, bands=selected_bands, value_column=row_value, distance_range_km=distance_range, vs30_range=vs30_range, component=component_filter)

    overview_tab, station_tab, event_tab, path_tab, distribution_tab, compare_tab = st.tabs(["Overview", "Stations", "Events", "Paths", "Distributions", "Compare Models"])
    with overview_tab:
        cols = st.columns(4)
        cols[0].metric("Rows", f"{len(rows) if rows is not None else len(heat):,}")
        cols[1].metric("Models", f"{len(selected_models):,}")
        cols[2].metric("Metrics", f"{heat['metric'].nunique() if 'metric' in heat else 0:,}")
        cols[3].metric("Passbands", f"{len(selected_bands):,}")
        if heat.empty:
            st.info(_empty_rows_message("model/metric/passband"))
        else:
            st.plotly_chart(build_metric_heatmap_figure(heat, value_col=value_col), width="stretch")
        st.dataframe(_display_table(heat), width="stretch")
    with station_tab:
        station_map_status = dashboard_map_readiness(stations, "station_rollup")
        if station_value_message:
            st.info(station_value_message)
        elif stations.empty:
            st.info(_empty_rows_message("station"))
        elif station_map_status["ready"] is False:
            st.info(str(station_map_status["message"]))
        else:
            station_map = build_station_folium_map(stations, value_col=value_col, basemap=basemap, marker_cluster=marker_cluster, max_markers=int(max_markers))
            st_folium(station_map, use_container_width=True, height=620)
            st.download_button("Download station map HTML", render_folium_html(station_map), file_name="station_metric_map.html")
        st.dataframe(_display_table(stations), width="stretch")
    with event_tab:
        event_map_status = dashboard_map_readiness(events, "event_rollup")
        if event_value_message:
            st.info(event_value_message)
        elif events.empty:
            st.info(_empty_rows_message("event"))
        elif event_map_status["ready"] is False:
            st.info(str(event_map_status["message"]))
        else:
            st_folium(build_event_folium_map(events, value_col=value_col, basemap=basemap, marker_cluster=marker_cluster, max_markers=int(max_markers)), use_container_width=True, height=560)
        st.dataframe(_display_table(events), width="stretch")
    with path_tab:
        if path_value_message:
            st.info(path_value_message)
        elif paths.empty:
            st.info(_empty_rows_message("path"))
        else:
            st.plotly_chart(build_path_heatmap_figure(paths, value_col=value_col), width="stretch")
        st.dataframe(_display_table(paths), width="stretch")
    with distribution_tab:
        if rows is None:
            st.info(row_value_message or "Load the long metrics dataset to view row-level distributions.")
        elif rows.empty:
            st.info(_empty_rows_message("row-level metric"))
        else:
            st.plotly_chart(build_value_histogram_figure(rows, value_col=row_value), width="stretch")
            if {"distance_km", "med_dist_km"} & set(rows.columns):
                st.plotly_chart(build_value_vs_distance_figure(rows, value_col=row_value), width="stretch")
            st.download_button("Download filtered metric rows", rows.to_csv(index=False).encode("utf-8"), file_name="filtered_metrics.csv")
    with compare_tab:
        if heat.empty:
            st.info(_empty_rows_message("model comparison"))
        else:
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


def _render_dashboard_readiness(readiness: pd.DataFrame) -> None:
    """Render summary-table readiness when any dashboard input is incomplete."""

    if readiness.empty or "ready" not in readiness.columns:
        return
    ready = readiness["ready"].map(lambda value: bool(value) if pd.notna(value) else True)
    if bool(ready.all()):
        return
    st.warning("Some dashboard summary tables are not ready. Affected tabs may be empty until those files are rebuilt.")
    columns = [
        "dashboard_table",
        "dashboard_tabs",
        "ready",
        "readiness",
        "row_count",
        "missing_columns",
        "map_ready",
        "missing_map_columns",
        "nonempty_value_columns",
        "message",
        "map_message",
    ]
    shown = [column for column in columns if column in readiness.columns]
    st.dataframe(_display_table(readiness[shown]), width="stretch")


def _metrics_dashboard_startup_blocker(readiness: pd.DataFrame) -> str | None:
    """Return a startup-blocking message for missing primary dashboard input."""

    if readiness.empty or "dashboard_table" not in readiness.columns:
        return None
    primary = readiness.loc[readiness["dashboard_table"].astype(str).eq("model_metric_band")]
    if primary.empty:
        return "The model_metric_band dashboard summary is missing from the readiness table."
    row = primary.iloc[0]
    ready = row.get("ready")
    is_ready = bool(ready) if pd.notna(ready) else False
    if is_ready:
        return None
    message = str(row.get("message") or "").strip()
    return message or "The model_metric_band dashboard summary is not ready."


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


def _missing_row_value_message(summary_value_col: str) -> str:
    """Return a clear message when a summary value has no row-level column."""

    return (
        f"The loaded long metrics dataset does not include a row-level column for "
        f"{value_column_display_name(summary_value_col)}. Rebuild the dashboard metric dataset "
        "from metric rows that contain this value to view row-level distributions."
    )


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


def _empty_rows_message(row_label: str) -> str:
    """Return a consistent filtered-empty dashboard message."""

    return f"No {row_label} rows match the selected filters."


if __name__ == "__main__":
    main()
