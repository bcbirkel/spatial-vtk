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
    dashboard_empty_rows_message,
    dashboard_map_readiness,
    dashboard_metric_dataset_readiness_frame,
    dashboard_ready_value,
    dashboard_row_level_columns,
    dashboard_summary_readiness_frame,
    dashboard_summary_table_contracts,
    dashboard_value_columns_or_message,
    load_filtered_dashboard_summary_table,
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


SUMMARY_READINESS_DISPLAY_COLUMNS = (
    "artifact_label",
    "dashboard_table",
    "dashboard_tabs",
    "required_columns",
    "ready",
    "readiness",
    "tab_ready",
    "row_count",
    "missing_columns",
    "map_ready",
    "missing_map_columns",
    "value_columns",
    "value_families",
    "nonempty_value_families",
    "nonempty_value_columns",
    "message",
    "tab_message",
    "map_message",
    "suggested_action",
    "resolved_path",
)
METRIC_DATASET_READINESS_DISPLAY_COLUMNS = (
    "artifact_label",
    "name",
    "ready",
    "readiness",
    "file_count",
    "row_count",
    "value_families",
    "value_columns",
    "message",
    "suggested_action",
    "resolved_path",
)
DEFAULT_METRICS_DASHBOARD_MAX_ROWS = 200_000
DEFAULT_METRICS_DASHBOARD_DOWNLOAD_ROWS = 100_000
DEFAULT_METRICS_DASHBOARD_SUMMARY_DISPLAY_ROWS = 5_000
OPTIONAL_SUMMARY_TABLES = ("station_rollup", "event_rollup", "path_hex")


def main() -> None:
    """Run the Streamlit Metrics Explorer."""

    st.set_page_config(page_title="Spatial-VTK Metrics Explorer", layout="wide")
    st.title("Spatial-VTK Metrics Explorer")
    metrics_root = _path_setting(
        "metrics_dataset_dir",
        "SVTK_METRICS_ROOT",
        aliases=("metrics_root", "metrics_dataset"),
    )
    summary_root = _path_setting(
        "dashboard_summary_table_dir",
        "SVTK_SUMMARY_ROOT",
        aliases=("summary_root", "dashboard_summary_dir"),
    )
    config_path = _path_setting("config", "SVTK_CONFIG_FILE")
    if not summary_root:
        st.info("Choose a dashboard summary directory to begin.")
        summary_root = st.text_input("Dashboard summary directory", value="")
        if not summary_root:
            return
    try:
        readiness = dashboard_summary_readiness_frame(summary_root, create_parent=False)
    except Exception as exc:
        st.error(str(exc))
        return
    blocker = _metrics_dashboard_startup_blocker(readiness)
    _render_dashboard_readiness(readiness, message=blocker)
    if blocker:
        return
    metric_dataset_readiness = dashboard_metric_dataset_readiness_frame(metrics_root) if metrics_root else pd.DataFrame()
    skip_tables = _startup_skip_summary_tables(readiness)
    try:
        summaries = _load_summary_tables_cached(summary_root, tuple(skip_tables))
    except Exception as exc:
        st.error(str(exc))
        return
    config = _load_optional_config(config_path)
    _render_metrics_dashboard(
        summaries,
        metrics_root,
        config,
        summary_root=summary_root,
        optional_skip_tables=tuple(_not_ready_optional_summary_tables(readiness)),
        readiness=readiness,
        metric_dataset_readiness=metric_dataset_readiness,
    )


def _render_metrics_dashboard(
    summaries: dict[str, pd.DataFrame],
    metrics_root: str,
    config: SpatialVTKConfig | None = None,
    *,
    summary_root: str | None = None,
    optional_skip_tables: tuple[str, ...] = (),
    readiness: pd.DataFrame | None = None,
    metric_dataset_readiness: pd.DataFrame | None = None,
) -> None:
    """Render the metrics dashboard body."""

    all_metrics = sorted({normalize_metric_name(value) for value in summaries["model_metric_band"]["metric"].dropna().astype(str)}, key=metric_display_name)
    all_models = sorted(summaries["model_metric_band"]["model"].dropna().astype(str).unique().tolist())
    data_bands = _band_options(summaries["model_metric_band"])
    configured_bands = configured_band_options(config, command="metrics.dashboard", fallback_df=summaries["model_metric_band"])
    all_bands = _merged_options(configured_bands, data_bands, key=band_display_label)
    period_options = _period_options(summaries["model_metric_band"])
    component_options = _component_options(config, summaries, None)
    if not all_metrics or not all_models or (not all_bands and not period_options):
        st.info("The model/metric summary is empty, so dashboard filters cannot be built yet.")
        st.dataframe(_display_table(summaries["model_metric_band"]), width="stretch")
        return

    with st.sidebar:
        st.header("Filters")
        selected_models = st.multiselect("Models", options=all_models, default=all_models)
        selected_metric = st.selectbox("Metric", options=all_metrics, format_func=metric_display_name)
        selected_bands = (
            st.multiselect("Passbands", options=all_bands, default=data_bands or all_bands, format_func=band_display_label)
            if all_bands
            else []
        )
        selected_periods = (
            st.multiselect(
                "Oscillator Periods",
                options=period_options,
                default=period_options,
                format_func=_period_display_label,
            )
            if period_options
            else []
        )
        selected_component = st.selectbox("Component", options=component_options) if component_options else "all"
        value_source = filter_dashboard_metrics(
            summaries["model_metric_band"],
            models=selected_models,
            metric=selected_metric,
            bands=selected_bands,
            periods_s=selected_periods,
            component=None if selected_component in {"", "all"} else selected_component,
        )
        value_columns, value_message = _value_columns_or_message(value_source)
        if value_message:
            st.info(value_message)
        if not value_columns:
            return
        value_col = st.selectbox("Displayed Value", options=value_columns, format_func=value_column_display_name)
        component_filter = None if selected_component in {"", "all"} else selected_component
        summary_chunksize = _metrics_dashboard_summary_chunksize()
        station_source = _optional_summary_for_selection(
            summaries,
            summary_root,
            "station_rollup",
            skip_tables=optional_skip_tables,
            models=selected_models,
            metric=selected_metric,
            bands=selected_bands,
            periods_s=selected_periods,
            value_column=value_col,
            component=component_filter,
            chunksize=summary_chunksize,
        )
        distance_range = _range_slider_from_columns("Distance (km)", station_source, ("med_dist_km", "distance_km"))
        vs30_range = _range_slider_from_columns("Vs30", station_source, ("Vs30", "vs30"))
        basemap = st.selectbox("Basemap", options=list(BASEMAPS), index=list(BASEMAPS).index("Carto Light"))
        marker_cluster = st.checkbox("Cluster map markers", value=True)
        max_markers = st.number_input("Maximum map markers", min_value=100, max_value=50000, value=3000, step=100)
        configured_row_limit = _metrics_dashboard_row_limit()
        download_limit = _metrics_dashboard_download_limit()
        summary_display_limit = _metrics_dashboard_summary_display_limit()
        row_limit = st.number_input(
            "Maximum row-level records",
            min_value=1_000,
            max_value=max(2_000_000, configured_row_limit),
            value=configured_row_limit,
            step=10_000,
        )

    heat = filter_dashboard_metrics(
        summaries["model_metric_band"],
        models=selected_models,
        metric=selected_metric,
        bands=selected_bands,
        periods_s=selected_periods,
        value_column=value_col,
        component=component_filter,
    )
    stations, station_value_message = filter_optional_dashboard_summary(
        station_source,
        table_label="station",
        value_column=value_col,
        distance_range_km=distance_range,
        vs30_range=vs30_range,
    )
    event_source = _optional_summary_for_selection(
        summaries,
        summary_root,
        "event_rollup",
        skip_tables=optional_skip_tables,
        models=selected_models,
        metric=selected_metric,
        bands=selected_bands,
        periods_s=selected_periods,
        value_column=value_col,
        distance_range_km=distance_range,
        component=component_filter,
        chunksize=summary_chunksize,
    )
    events, event_value_message = filter_optional_dashboard_summary(
        event_source,
        table_label="event",
        value_column=value_col,
    )
    path_source = _optional_summary_for_selection(
        summaries,
        summary_root,
        "path_hex",
        skip_tables=optional_skip_tables,
        models=selected_models,
        metric=selected_metric,
        bands=selected_bands,
        periods_s=selected_periods,
        value_column=value_col,
        component=component_filter,
        chunksize=summary_chunksize,
    )
    paths, path_value_message = filter_optional_dashboard_summary(
        path_source,
        table_label="path",
        value_column=value_col,
    )
    rows = None
    row_value = None
    row_value_message = None
    metric_dataset_message = _metric_dataset_readiness_message(metric_dataset_readiness)
    if metric_dataset_message:
        row_value_message = metric_dataset_message
    elif metrics_root:
        row_value = row_value_column_for_summary(value_col, pd.DataFrame(columns=dashboard_row_level_columns()))
        if row_value is None:
            row_value_message = _missing_row_value_message(value_col)
        else:
            needed_columns = _row_level_columns_for_selection(row_value)
            try:
                loaded_rows = _try_load_filtered_long_metrics(
                    metrics_root,
                    columns=needed_columns,
                    models=selected_models,
                    metric=selected_metric,
                    bands=selected_bands,
                    periods_s=selected_periods,
                    component=component_filter,
                    distance_range_km=distance_range,
                    vs30_range=vs30_range,
                    max_rows=int(row_limit),
                )
            except Exception as exc:
                row_value_message = f"Long metric rows were not loaded: {exc}"
            else:
                if row_value not in loaded_rows.columns:
                    row_value_message = _missing_row_value_message(value_col)
                else:
                    rows = filter_dashboard_metrics(
                        loaded_rows,
                        periods_s=selected_periods,
                        value_column=row_value,
                        distance_range_km=distance_range,
                        vs30_range=vs30_range,
                        component=component_filter,
                    )
    else:
        row_value_message = "Configure the metrics dashboard dataset to view row-level distributions."

    row_level_notice = _row_level_dataset_notice_message(row_value_message, rows)
    if row_level_notice:
        st.warning(row_level_notice)
    elif rows is not None and int(row_limit) > 0 and len(rows) >= int(row_limit):
        st.info(
            f"Row-level dashboard data is capped at {int(row_limit):,} filtered records for responsiveness. "
            "Increase the sidebar limit if you need a larger distribution sample."
        )

    overview_tab, station_tab, event_tab, path_tab, distribution_tab, compare_tab, status_tab = st.tabs(
        ["Overview", "Stations", "Events", "Paths", "Distributions", "Compare Models", "Data Status"]
    )
    with overview_tab:
        cols = st.columns(4)
        cols[0].metric("Rows", f"{len(rows) if rows is not None else len(heat):,}")
        cols[1].metric("Models", f"{len(selected_models):,}")
        cols[2].metric("Metrics", f"{heat['metric'].nunique() if 'metric' in heat else 0:,}")
        cols[3].metric("Passbands / Periods", f"{len(selected_bands):,} / {len(selected_periods):,}")
        if period_options:
            st.caption(f"Oscillator periods selected: {len(selected_periods):,} of {len(period_options):,}")
        if heat.empty:
            st.info(_empty_rows_message("model/metric/passband-or-period"))
        else:
            st.plotly_chart(build_metric_heatmap_figure(heat, value_col=value_col), width="stretch")
        _render_summary_dataframe(heat, limit=summary_display_limit)
    with station_tab:
        station_ready_message = _summary_readiness_message(readiness, "station_rollup")
        station_map_status = dashboard_map_readiness(stations, "station_rollup")
        if station_ready_message:
            st.info(station_ready_message)
        elif station_value_message:
            st.info(station_value_message)
        elif stations.empty:
            st.info(_empty_rows_message("station"))
        elif station_map_status["ready"] is False:
            st.info(str(station_map_status["message"]))
        else:
            station_map = build_station_folium_map(stations, value_col=value_col, basemap=basemap, marker_cluster=marker_cluster, max_markers=int(max_markers))
            st_folium(station_map, use_container_width=True, height=620)
            st.download_button("Download station map HTML", render_folium_html(station_map), file_name="station_metric_map.html")
        _render_summary_dataframe(stations, limit=summary_display_limit)
    with event_tab:
        event_ready_message = _summary_readiness_message(readiness, "event_rollup")
        event_map_status = dashboard_map_readiness(events, "event_rollup")
        if event_ready_message:
            st.info(event_ready_message)
        elif event_value_message:
            st.info(event_value_message)
        elif events.empty:
            st.info(_empty_rows_message("event"))
        elif event_map_status["ready"] is False:
            st.info(str(event_map_status["message"]))
        else:
            st_folium(build_event_folium_map(events, value_col=value_col, basemap=basemap, marker_cluster=marker_cluster, max_markers=int(max_markers)), use_container_width=True, height=560)
        _render_summary_dataframe(events, limit=summary_display_limit)
    with path_tab:
        path_ready_message = _summary_readiness_message(readiness, "path_hex")
        if path_ready_message:
            st.info(path_ready_message)
        elif path_value_message:
            st.info(path_value_message)
        elif paths.empty:
            st.info(_empty_rows_message("path"))
        else:
            st.plotly_chart(build_path_heatmap_figure(paths, value_col=value_col), width="stretch")
        _render_summary_dataframe(paths, limit=summary_display_limit)
    with distribution_tab:
        if rows is None:
            st.info(row_value_message or "Load the long metrics dataset to view row-level distributions.")
        elif rows.empty:
            st.info(_empty_rows_message("row-level metric"))
        else:
            st.plotly_chart(build_value_histogram_figure(rows, value_col=row_value), width="stretch")
            if {"distance_km", "med_dist_km"} & set(rows.columns):
                st.plotly_chart(build_value_vs_distance_figure(rows, value_col=row_value), width="stretch")
            download_rows, download_message = _bounded_metric_download_frame(rows, download_limit)
            if download_message:
                st.caption(download_message)
            st.download_button("Download filtered metric rows", download_rows.to_csv(index=False).encode("utf-8"), file_name="filtered_metrics.csv")
    with compare_tab:
        if heat.empty:
            st.info(_empty_rows_message("model comparison"))
        else:
            st.plotly_chart(build_metric_heatmap_figure(heat, value_col=value_col, title="Model Comparison"), width="stretch")
        _render_summary_dataframe(heat, limit=summary_display_limit)
    with status_tab:
        _render_data_status_tab(
            readiness,
            metric_dataset_readiness,
            filtered_summary=_dashboard_filtered_row_summary(
                heat=heat,
                stations=stations,
                events=events,
                paths=paths,
                rows=rows,
                readiness=readiness,
                metric_dataset_readiness=metric_dataset_readiness,
            ),
        )


@st.cache_data(show_spinner=False)
def _load_summary_tables_cached(summary_root: str, skip_tables: tuple[str, ...] = ()) -> dict[str, pd.DataFrame]:
    """Load summary tables with Streamlit caching."""

    return validate_dashboard_tables(load_dashboard_summary_tables(summary_root, skip_tables=skip_tables))


@st.cache_data(show_spinner=False)
def _load_filtered_summary_table_cached(
    summary_root: str,
    table_name: str,
    models: tuple[str, ...],
    metric: str,
    bands: tuple[str, ...],
    periods_s: tuple[float, ...],
    value_column: str,
    component: str,
    distance_range_km: tuple[float | None, float | None] | None,
    vs30_range: tuple[float | None, float | None] | None,
    chunksize: int,
) -> pd.DataFrame:
    """Load one filtered optional summary table with Streamlit caching."""

    return load_filtered_dashboard_summary_table(
        summary_root,
        table_name,
        models=models,
        metric=metric or None,
        bands=bands,
        periods_s=periods_s,
        value_column=value_column or None,
        component=component or None,
        distance_range_km=distance_range_km,
        vs30_range=vs30_range,
        chunksize=chunksize,
    )


def _optional_summary_for_selection(
    summaries: dict[str, pd.DataFrame],
    summary_root: str | None,
    table_name: str,
    *,
    skip_tables: tuple[str, ...],
    models: list[str],
    metric: str,
    bands: list[str],
    periods_s: list[float] | None = None,
    value_column: str,
    component: str | None = None,
    distance_range_km: tuple[float | None, float | None] | None = None,
    vs30_range: tuple[float | None, float | None] | None = None,
    chunksize: int = 50_000,
) -> pd.DataFrame:
    """Return a lazily loaded optional summary table for current filters."""

    if table_name in set(skip_tables) or not summary_root:
        return summaries.get(table_name, pd.DataFrame()).copy()
    return _load_filtered_summary_table_cached(
        str(summary_root),
        str(table_name),
        tuple(str(model) for model in models),
        str(metric or ""),
        tuple(str(band) for band in bands),
        tuple(float(period) for period in periods_s or ()),
        str(value_column or ""),
        "" if component in {None, "", "all"} else str(component),
        distance_range_km,
        vs30_range,
        int(chunksize),
    )


@st.cache_data(show_spinner=False)
def _load_long_metrics_cached(
    metrics_root: str,
    columns: tuple[str, ...],
    models: tuple[str, ...],
    metric: str,
    bands: tuple[str, ...],
    periods_s: tuple[float, ...],
    component: str,
    distance_range_km: tuple[float | None, float | None] | None,
    vs30_range: tuple[float | None, float | None] | None,
    max_rows: int,
) -> pd.DataFrame:
    """Load long metrics with Streamlit caching."""

    return load_metric_long_table(
        metrics_root,
        columns=columns,
        models=models,
        metrics=[metric] if metric else None,
        bands=bands,
        periods_s=periods_s,
        component=component or None,
        distance_range_km=distance_range_km,
        vs30_range=vs30_range,
        max_rows=max_rows,
    )


def _try_load_filtered_long_metrics(
    metrics_root: str,
    *,
    columns: tuple[str, ...],
    models: list[str],
    metric: str,
    bands: list[str],
    periods_s: list[float] | None = None,
    component: str | None = None,
    distance_range_km: tuple[float | None, float | None] | None = None,
    vs30_range: tuple[float | None, float | None] | None = None,
    max_rows: int = 200_000,
) -> pd.DataFrame:
    """Load selected long metric rows when a root is configured."""

    return _load_long_metrics_cached(
        metrics_root,
        tuple(columns),
        tuple(str(model) for model in models),
        str(metric),
        tuple(str(band) for band in bands),
        tuple(float(period) for period in periods_s or ()),
        "" if component in {None, "", "all"} else str(component),
        distance_range_km,
        vs30_range,
        int(max_rows),
    )


def _render_metric_dataset_readiness(readiness: pd.DataFrame) -> None:
    """Render metric dataset readiness when row-level dashboard data is incomplete."""

    message = _metric_dataset_readiness_message(readiness)
    if not message:
        return
    st.warning(message)
    shown = _select_readiness_columns(readiness, METRIC_DATASET_READINESS_DISPLAY_COLUMNS)
    if not shown.empty:
        st.dataframe(_display_table(shown), width="stretch")


def _metric_dataset_readiness_message(readiness: pd.DataFrame | None) -> str | None:
    """Return a warning message for an unavailable row-level metric dataset."""

    if readiness is None or readiness.empty or "ready" not in readiness.columns:
        return None
    row = readiness.iloc[0]
    if dashboard_ready_value(row.get("ready"), default=False):
        return None
    message = str(row.get("message") or "").strip()
    return message or "The row-level metrics dashboard dataset is not ready."


def _row_level_dataset_notice_message(row_value_message: str | None, rows: pd.DataFrame | None) -> str | None:
    """Return the dashboard-level notice for unavailable row-level metric rows."""

    if rows is not None:
        return None
    message = str(row_value_message or "").strip()
    if message:
        return message
    return "Row-level metric rows are not loaded. Summary tabs can still render, but distributions and filtered row downloads need the metrics dashboard dataset."


def _render_dashboard_readiness(readiness: pd.DataFrame, *, message: str | None = None) -> None:
    """Render summary-table readiness when any dashboard input is incomplete."""

    if readiness.empty or "ready" not in readiness.columns:
        return
    ready_column = "tab_ready" if "tab_ready" in readiness.columns else "ready"
    ready = readiness[ready_column].map(lambda value: dashboard_ready_value(value, default=False))
    if bool(ready.all()):
        return
    detail = str(message or "").strip() or _dashboard_readiness_warning_detail(readiness, ready_column=ready_column)
    warning = "Some dashboard inputs or tabs are not ready."
    if detail and detail != warning:
        warning = f"{warning} {detail}"
    else:
        warning = f"{warning} Affected tabs may be empty until those files are rebuilt."
    st.warning(warning)
    shown = _select_readiness_columns(readiness, SUMMARY_READINESS_DISPLAY_COLUMNS)
    st.dataframe(_display_table(shown), width="stretch")


def _dashboard_readiness_warning_detail(readiness: pd.DataFrame, *, ready_column: str) -> str:
    """Return a concise detail string for not-ready dashboard summary rows."""

    if readiness.empty or ready_column not in readiness.columns:
        return ""
    not_ready = readiness.loc[~readiness[ready_column].map(lambda value: dashboard_ready_value(value, default=False))]
    details: list[str] = []
    for _, row in not_ready.iterrows():
        message = str(row.get("tab_message") or row.get("message") or "").strip()
        if message:
            details.append(message)
    unique = list(dict.fromkeys(details))
    if not unique:
        return ""
    shown = unique[:3]
    suffix = f" {len(unique) - len(shown)} more issue(s) are listed in Data Status." if len(unique) > len(shown) else ""
    return " ".join(shown) + suffix


def _render_data_status_tab(
    readiness: pd.DataFrame | None,
    metric_dataset_readiness: pd.DataFrame | None,
    *,
    filtered_summary: pd.DataFrame | None = None,
) -> None:
    """Render the data-readiness tab for already-started dashboards."""

    st.subheader("Current Filter Results")
    if filtered_summary is None or filtered_summary.empty:
        st.info("No current-filter summary is available yet.")
    else:
        st.dataframe(_display_table(filtered_summary), width="stretch")

    st.subheader("Dashboard Summary Tables")
    summary_status = _select_readiness_columns(readiness, SUMMARY_READINESS_DISPLAY_COLUMNS)
    if summary_status.empty:
        st.info("No dashboard summary readiness rows are available.")
    else:
        st.dataframe(_display_table(summary_status), width="stretch")

    st.subheader("Row-Level Metrics Dataset")
    metric_status = _select_readiness_columns(metric_dataset_readiness, METRIC_DATASET_READINESS_DISPLAY_COLUMNS)
    if metric_status.empty:
        st.info("No row-level metrics dataset was configured. Distribution tabs require the metrics dashboard dataset.")
    else:
        st.dataframe(_display_table(metric_status), width="stretch")

    st.subheader("Dashboard Table Contracts")
    st.dataframe(_display_table(dashboard_summary_table_contracts()), width="stretch")


def _select_readiness_columns(readiness: pd.DataFrame | None, columns: tuple[str, ...]) -> pd.DataFrame:
    """Return bounded readiness columns for dashboard display."""

    if readiness is None or readiness.empty:
        return pd.DataFrame()
    shown = [column for column in columns if column in readiness.columns]
    return readiness.loc[:, shown].copy() if shown else pd.DataFrame()


def _dashboard_filtered_row_summary(
    *,
    heat: pd.DataFrame,
    stations: pd.DataFrame,
    events: pd.DataFrame,
    paths: pd.DataFrame,
    rows: pd.DataFrame | None,
    readiness: pd.DataFrame | None = None,
    metric_dataset_readiness: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return tab-level row counts for the active dashboard filters."""

    specs = [
        ("Overview / Compare Models", "model_metric_band", heat),
        ("Stations", "station_rollup", stations),
        ("Events", "event_rollup", events),
        ("Paths", "path_hex", paths),
        ("Distributions", "metrics_dashboard_dataset", rows),
    ]
    result_rows: list[dict[str, object]] = []
    metric_dataset_message = _metric_dataset_readiness_message(metric_dataset_readiness)
    for tab, table, frame in specs:
        if frame is None:
            result_rows.append(
                {
                    "dashboard_tab": tab,
                    "dashboard_table": table,
                    "row_count": "",
                    "event_count": "",
                    "station_count": "",
                    "model_count": "",
                    "metric_count": "",
                    "message": metric_dataset_message
                    if table == "metrics_dashboard_dataset" and metric_dataset_message
                    else "Row-level metrics are not loaded for the current selection.",
                }
            )
            continue
        readiness_message = _summary_readiness_message(readiness, table)
        result_rows.append(
            {
                "dashboard_tab": tab,
                "dashboard_table": table,
                "row_count": int(len(frame)),
                "event_count": _unique_count(frame, "event_id"),
                "station_count": _unique_count(frame, "station"),
                "model_count": _unique_count(frame, "model"),
                "metric_count": _unique_count(frame, "metric"),
                "message": readiness_message or ("Ready for current filters." if not frame.empty else "No rows match the current filters."),
            }
        )
    return pd.DataFrame(result_rows)


def _unique_count(df: pd.DataFrame, column: str) -> int | str:
    """Return a display-safe unique count for one optional column."""

    if column not in df.columns:
        return ""
    return int(df[column].dropna().astype(str).nunique())


def _metrics_dashboard_startup_blocker(readiness: pd.DataFrame) -> str | None:
    """Return a startup-blocking message for missing primary dashboard input."""

    if readiness.empty or "dashboard_table" not in readiness.columns:
        return None
    primary = readiness.loc[readiness["dashboard_table"].astype(str).eq("model_metric_band")]
    if primary.empty:
        return "The model_metric_band dashboard summary is missing from the readiness table."
    row = primary.iloc[0]
    ready = row.get("ready")
    is_ready = dashboard_ready_value(ready, default=False)
    if is_ready:
        return None
    message = str(row.get("message") or "").strip()
    return message or "The model_metric_band dashboard summary is not ready."


def _not_ready_optional_summary_tables(readiness: pd.DataFrame) -> list[str]:
    """Return optional dashboard summary tables that should not be loaded."""

    if readiness.empty or "dashboard_table" not in readiness.columns or "ready" not in readiness.columns:
        return []
    skip: list[str] = []
    for _, row in readiness.iterrows():
        table = str(row.get("dashboard_table") or "").strip()
        if not table or table == "model_metric_band":
            continue
        if not dashboard_ready_value(row.get("ready"), default=False):
            skip.append(table)
    return sorted(dict.fromkeys(skip))


def _startup_skip_summary_tables(readiness: pd.DataFrame) -> list[str]:
    """Return dashboard summaries skipped during initial Streamlit startup."""

    skip = set(OPTIONAL_SUMMARY_TABLES)
    skip.update(_not_ready_optional_summary_tables(readiness))
    return sorted(skip)


def _summary_readiness_message(readiness: pd.DataFrame | None, table_name: str) -> str | None:
    """Return the tab-level readiness message for one optional summary table."""

    if readiness is None or readiness.empty or "dashboard_table" not in readiness.columns:
        return None
    rows = readiness.loc[readiness["dashboard_table"].astype(str).eq(str(table_name))]
    if rows.empty:
        return None
    row = rows.iloc[0]
    ready = row.get("tab_ready", row.get("ready"))
    if dashboard_ready_value(ready, default=False):
        return None
    message = str(row.get("tab_message") or row.get("message") or "").strip()
    if message:
        return message
    tabs = str(row.get("dashboard_tabs") or "").strip()
    tab_text = f" for {tabs}" if tabs else ""
    return f"{table_name} summary is not ready{tab_text}. Rebuild dashboard summaries for this run."


def _path_setting(query_key: str, env_key: str, *, aliases: tuple[str, ...] = ()) -> str:
    """Read one app path setting."""

    for key in (query_key, *aliases):
        value = st.query_params.get(key, "")
        if isinstance(value, list):
            value = value[0] if value else ""
        text = str(value or "").strip()
        if text:
            return text
    return str(os.environ.get(env_key, "")).strip()


def _metrics_dashboard_row_limit(default: int = DEFAULT_METRICS_DASHBOARD_MAX_ROWS) -> int:
    """Return the row-level metrics cap for responsive dashboard rendering."""

    return _env_minimum_positive_int(
        ("SVTK_METRICS_DASHBOARD_ROW_LIMIT",),
        default=default,
        minimum=1_000,
    )


def _metrics_dashboard_download_limit(default: int | None = DEFAULT_METRICS_DASHBOARD_DOWNLOAD_ROWS) -> int | None:
    """Return the maximum metric rows serialized by dashboard download buttons."""

    return _env_optional_positive_int(
        ("SVTK_METRICS_DASHBOARD_DOWNLOAD_ROWS", "SVTK_DASHBOARD_DOWNLOAD_ROWS"),
        default=default,
    )


def _metrics_dashboard_summary_chunksize(default: int = 50_000) -> int:
    """Return the chunk size for lazy optional summary-table loads."""

    return _env_minimum_positive_int(
        ("SVTK_METRICS_DASHBOARD_SUMMARY_CHUNKSIZE", "SVTK_DASHBOARD_CHUNKSIZE"),
        default=default,
        minimum=1_000,
    )


def _metrics_dashboard_summary_display_limit(default: int | None = DEFAULT_METRICS_DASHBOARD_SUMMARY_DISPLAY_ROWS) -> int | None:
    """Return the maximum summary rows displayed in dashboard dataframes."""

    return _env_optional_positive_int(
        ("SVTK_METRICS_DASHBOARD_SUMMARY_DISPLAY_ROWS", "SVTK_DASHBOARD_DISPLAY_ROWS"),
        default=default,
    )


def _env_optional_positive_int(names: tuple[str, ...], *, default: int | None) -> int | None:
    """Read the first configured positive integer, or ``None`` for all rows."""

    for name in names:
        raw = os.environ.get(name)
        if raw is None or str(raw).strip() == "":
            continue
        value = str(raw).strip().lower()
        if value in {"all", "none", "unlimited", "full"}:
            return None
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be a positive integer or 'all', got {raw!r}.") from exc
        if parsed <= 0:
            raise ValueError(f"{name} must be a positive integer or 'all', got {raw!r}.")
        return parsed
    return default


def _env_minimum_positive_int(names: tuple[str, ...], *, default: int, minimum: int) -> int:
    """Read the first configured positive integer and enforce a minimum value."""

    for name in names:
        raw = os.environ.get(name)
        if raw is None or str(raw).strip() == "":
            continue
        value = str(raw).strip()
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be a positive integer, got {raw!r}.") from exc
        if parsed <= 0:
            raise ValueError(f"{name} must be a positive integer, got {raw!r}.")
        return max(parsed, int(minimum))
    return int(default)


def _metrics_download_limit_message(download_limit: int | None) -> str:
    """Return a concise explanation of metrics dashboard download limits."""

    if download_limit is None:
        return "Download buttons include all currently filtered loaded rows."
    return f"Download buttons include at most {download_limit:,} currently filtered loaded row(s)."


def _bounded_metric_download_frame(df: pd.DataFrame, limit: int | None) -> tuple[pd.DataFrame, str | None]:
    """Return bounded metric rows and a caption when the download is truncated."""

    if limit is None or len(df) <= limit:
        return df, None
    message = f"Download is limited to the first {int(limit):,} of {len(df):,} filtered loaded row(s)."
    return df.head(int(limit)).copy(), message


def _render_summary_dataframe(df: pd.DataFrame, *, limit: int | None) -> None:
    """Render a bounded dashboard summary dataframe."""

    shown, message = _bounded_summary_display_frame(df, limit)
    if message:
        st.caption(message)
    st.dataframe(_display_table(shown), width="stretch")


def _bounded_summary_display_frame(df: pd.DataFrame, limit: int | None) -> tuple[pd.DataFrame, str | None]:
    """Return bounded summary rows and a caption when dashboard display is truncated."""

    if limit is None or len(df) <= limit:
        return df, None
    message = f"Table display is limited to the first {int(limit):,} of {len(df):,} filtered summary row(s)."
    return df.head(int(limit)).copy(), message


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


def _band_options(df: pd.DataFrame) -> list[str]:
    """Return non-empty passband options available in a dashboard summary."""

    if "band" not in df.columns:
        return []
    values = df["band"].dropna().astype(str).str.strip()
    values = values.loc[~values.str.lower().isin({"", "nan", "none", "all", "broadband"})]
    return sorted(values.unique().tolist(), key=band_display_label)


def _period_options(df: pd.DataFrame) -> list[float]:
    """Return finite oscillator periods available in a dashboard summary."""

    if "period_s" not in df.columns:
        return []
    values = pd.to_numeric(df["period_s"], errors="coerce").dropna()
    if values.empty:
        return []
    return sorted(float(value) for value in values.unique())


def _period_display_label(period_s: float | str) -> str:
    """Return a dashboard label for one oscillator period."""

    period = float(period_s)
    return f"T={period:g} s (f={1.0 / period:g} Hz)" if period > 0 else str(period_s)


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


def _row_level_columns_for_selection(value_col: str) -> tuple[str, ...]:
    """Return bounded row-level columns needed for selected distributions."""

    needed = {
        "model",
        "metric",
        "band",
        "period_s",
        "component",
        "station",
        "event_id",
        "distance_km",
        "med_dist_km",
        "Vs30",
        "vs30",
        value_col,
    }
    columns = [
        column
        for column in dashboard_row_level_columns()
        if column in needed
    ]
    if value_col not in columns:
        columns.append(value_col)
    return tuple(dict.fromkeys(columns))


def _available_nonempty_value_columns(df: pd.DataFrame) -> list[str]:
    """Return selectable value columns that have finite data for current filters."""

    columns = available_dashboard_value_columns(df)
    nonempty = [
        column
        for column in columns
        if column in df.columns and pd.to_numeric(df[column], errors="coerce").notna().any()
    ]
    return nonempty or columns


def _value_columns_or_message(df: pd.DataFrame) -> tuple[list[str], str | None]:
    """Return selectable value columns with a precise empty-state message."""

    return dashboard_value_columns_or_message(df)


def _display_table(df: pd.DataFrame) -> pd.DataFrame:
    """Return a dashboard table with human-readable values and headers."""

    return display_table(df)


def _empty_rows_message(row_label: str) -> str:
    """Return a consistent filtered-empty dashboard message."""

    return dashboard_empty_rows_message(row_label)


if __name__ == "__main__":
    main()
