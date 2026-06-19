"""Streamlit QC Explorer entrypoint."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from spatial_vtk.config.runtime import SpatialVTKConfig
from spatial_vtk.visualize.dashboard.charts import build_qc_bar_figure, build_qc_histogram_figure
from spatial_vtk.visualize.dashboard.contracts import dashboard_qc_trace_readiness_frame, dashboard_ready_value
from spatial_vtk.visualize.dashboard.exports import normalize_manual_review_queue, queue_to_csv_bytes
from spatial_vtk.visualize.dashboard.filters import filter_qc_dashboard_rows
from spatial_vtk.config.labels import band_display_label, display_table
from spatial_vtk.visualize.qc.overview import load_trace_qc_summary, queue_rows_from_filtered_trace_df
from spatial_vtk.visualize.selection import FigureSelection, configured_band_options


QC_READINESS_DISPLAY_COLUMNS = (
    "artifact_label",
    "dashboard_table",
    "ready",
    "readiness",
    "row_count",
    "missing_columns",
    "message",
    "suggested_action",
    "path",
)
DEFAULT_QC_DASHBOARD_MAX_ROWS = 250_000
DEFAULT_QC_DASHBOARD_DOWNLOAD_ROWS = 100_000


def main() -> None:
    """Run the Streamlit QC Explorer."""

    st.set_page_config(page_title="Spatial-VTK QC Explorer", layout="wide")
    st.title("Spatial-VTK QC Explorer")
    trace_summary = _path_setting("trace_summary", "SVTK_TRACE_SUMMARY")
    config_path = _path_setting("config", "SVTK_CONFIG_FILE")
    if not trace_summary:
        trace_summary = st.text_input("Trace-summary table", value="")
        if not trace_summary:
            st.info("Choose a trace-summary Parquet or CSV file to begin.")
            return
    readiness = _qc_trace_readiness(trace_summary)
    _render_qc_readiness(readiness)
    blocker = _qc_dashboard_startup_blocker(readiness)
    if blocker:
        st.warning(blocker)
        return
    try:
        row_limit = _qc_dashboard_row_limit()
        df = _load_trace_summary_cached(trace_summary, max_rows=row_limit)
    except Exception as exc:
        st.error(str(exc))
        return
    config = _load_optional_config(config_path)
    _render_qc_dashboard(df, config, readiness=readiness, row_limit=row_limit)


def _render_qc_dashboard(
    df: pd.DataFrame,
    config: SpatialVTKConfig | None = None,
    *,
    readiness: pd.DataFrame | None = None,
    row_limit: int | None = None,
) -> None:
    """Render the QC dashboard body."""

    with st.sidebar:
        st.header("Filters")
        event_filter = st.text_input("Event ID", value="")
        family_options = _options(df, "station_family", include_all=True)
        station_family = st.selectbox("Station Family", family_options)
        component_options = _configured_component_options(config, df)
        component = st.selectbox("Component", component_options)
        station_query = st.text_input("Station Contains", value="")
        magnitude_range = _range_slider("Magnitude", df, "magnitude")
        distance_range = _range_slider("Distance (km)", df, "distance_km")
        date_range = _date_range(df)
        metadata_warning = st.text_input("Metadata Warning Contains", value="") if "metadata_warning" in df.columns else ""
        reject_reason = st.text_input("Reject Reason Contains", value="") if any("reject" in column.lower() and "reason" in column.lower() for column in df.columns) else ""
        band_options = configured_band_options(config, command="qc.dashboard", fallback_df=df)
        band_options = ["all", *band_options] if band_options else []
        selected_band = st.selectbox("Band", band_options, format_func=lambda value: "All bands" if value == "all" else band_display_label(value)) if band_options else "all"
        clip_iqr = st.checkbox("Hide histogram outliers with 1.5 x IQR", value=False)
        if row_limit is not None:
            configured_row_limit = int(row_limit)
            row_limit = int(
                st.number_input(
                    "Maximum trace-summary rows",
                    min_value=1_000,
                    max_value=max(2_000_000, configured_row_limit),
                    value=configured_row_limit,
                    step=10_000,
                )
            )
            st.caption("Set SVTK_QC_DASHBOARD_MAX_ROWS=all before launch to load the full trace-summary table.")
        else:
            st.caption("Loading the full trace-summary table because SVTK_QC_DASHBOARD_MAX_ROWS is set to all.")

    filtered = filter_qc_dashboard_rows(
        df,
        event_filter=event_filter,
        station_family=station_family,
        component_filter=component,
        station_query=station_query,
        magnitude_range=magnitude_range,
        distance_range_km=distance_range,
        date_range=date_range,
        metadata_warning=metadata_warning,
        reject_reason=reject_reason,
        band=None if selected_band == "all" else selected_band,
    )
    limit_message = _qc_row_limit_message(readiness, df, row_limit)
    if limit_message:
        st.info(limit_message)
    download_limit = _qc_dashboard_download_limit()
    overview_tab, amp_tab, timing_tab, band_tab, table_tab, queue_tab, status_tab = st.tabs(
        ["Overview", "Amplitudes", "Timing", "Band Content", "Trace Table", "Manual Review Queue", "Data Status"]
    )
    with overview_tab:
        if filtered.empty:
            st.info(_empty_rows_message("trace QC"))
        cols = st.columns(5)
        cols[0].metric("Traces", f"{len(filtered):,}")
        cols[1].metric("Event/Station Pairs", f"{len(queue_rows_from_filtered_trace_df(filtered)):,}")
        cols[2].metric("Events", f"{filtered['event_id'].nunique() if 'event_id' in filtered else 0:,}")
        cols[3].metric("Stations", f"{filtered['station'].nunique() if 'station' in filtered else 0:,}")
        cols[4].metric("Components", f"{filtered['component'].nunique() if 'component' in filtered else 0:,}")
        if not filtered.empty and "dominant_band_label" in filtered.columns:
            st.plotly_chart(build_qc_bar_figure(filtered, column="dominant_band_label", title="Dominant Band Counts"), width="stretch", key="overview_dominant_band_counts")
    with amp_tab:
        columns, message = _qc_chart_columns_or_message(filtered, _amplitude_columns(filtered), "amplitude")
        if message:
            st.info(message)
        else:
            for column in columns:
                st.plotly_chart(build_qc_histogram_figure(filtered, value_col=column, title=_qc_column_label(column), clip_iqr=clip_iqr), width="stretch", key=f"amp_{column}")
    with timing_tab:
        columns, message = _qc_chart_columns_or_message(
            filtered,
            [item for item in ("start_rel_s", "end_rel_s", "duration_s") if item in filtered.columns],
            "timing",
        )
        if message:
            st.info(message)
        else:
            for column in columns:
                st.plotly_chart(build_qc_histogram_figure(filtered, value_col=column, title=_qc_column_label(column), clip_iqr=clip_iqr), width="stretch", key=f"timing_{column}")
    with band_tab:
        content_columns = _band_content_columns(filtered)
        columns, message = _qc_chart_columns_or_message(
            filtered,
            (["dominant_band_label"] if "dominant_band_label" in filtered.columns else []) + content_columns,
            "band-content",
        )
        if message:
            st.info(message)
        else:
            if "dominant_band_label" in filtered.columns:
                st.plotly_chart(build_qc_bar_figure(filtered, column="dominant_band_label", title="Dominant Band Counts"), width="stretch", key="band_dominant_band_counts")
            for column in content_columns:
                st.plotly_chart(build_qc_histogram_figure(filtered, value_col=column, title=_qc_column_label(column), clip_iqr=clip_iqr), width="stretch", key=f"band_{column}")
    with table_tab:
        if filtered.empty:
            st.info(_empty_rows_message("trace QC"))
        st.dataframe(display_table(filtered, max_rows=5000), width="stretch")
        download_rows, download_message = _bounded_download_frame(filtered, download_limit)
        if download_message:
            st.caption(download_message)
        st.download_button(
            "Download filtered trace rows",
            download_rows.to_csv(index=False).encode("utf-8"),
            file_name="filtered_trace_qc_rows.csv",
        )
    with queue_tab:
        queue_rows = normalize_manual_review_queue(queue_rows_from_filtered_trace_df(filtered))
        st.metric("Event/Station Pairs in Queue", f"{len(queue_rows):,}")
        if not queue_rows:
            st.info(_empty_rows_message("manual review queue"))
        st.dataframe(display_table(pd.DataFrame(queue_rows)), width="stretch")
        queue_download_rows, queue_download_message = _bounded_queue_rows(queue_rows, download_limit)
        if queue_download_message:
            st.caption(queue_download_message)
        st.download_button(
            "Download manual-review queue CSV",
            queue_to_csv_bytes(queue_download_rows),
            file_name="manual_review_queue.csv",
        )
        st.caption("The exported queue is formatted for the manual QC picker and can be passed to the manual waveform-review workflow.")
    with status_tab:
        _render_qc_data_status_tab(readiness, df, filtered, row_limit=row_limit, download_limit=download_limit)


@st.cache_data(show_spinner=False)
def _load_trace_summary_cached(path: str, *, max_rows: int | None = DEFAULT_QC_DASHBOARD_MAX_ROWS) -> pd.DataFrame:
    """Load trace summary with Streamlit caching."""

    return load_trace_qc_summary(path, max_rows=max_rows)


def _qc_trace_readiness(trace_summary: str) -> pd.DataFrame:
    """Return bounded readiness for one configured QC trace summary."""

    return dashboard_qc_trace_readiness_frame(trace_summary, create_parent=False)


def _render_qc_readiness(readiness: pd.DataFrame) -> None:
    """Render QC trace-summary readiness when the dashboard cannot start."""

    if readiness.empty or "ready" not in readiness.columns:
        return
    ready = readiness["ready"].map(lambda value: dashboard_ready_value(value, default=False))
    if bool(ready.all()):
        return
    st.warning("The QC trace-summary table is not ready. Rebuild QC outputs before using the QC dashboard.")
    shown = _select_qc_readiness_columns(readiness)
    st.dataframe(display_table(shown), width="stretch")


def _render_qc_data_status_tab(
    readiness: pd.DataFrame | None,
    loaded: pd.DataFrame,
    filtered: pd.DataFrame,
    *,
    row_limit: int | None = None,
    download_limit: int | None = DEFAULT_QC_DASHBOARD_DOWNLOAD_ROWS,
) -> None:
    """Render QC input/readiness details in a persistent dashboard tab."""

    st.subheader("Trace Summary Input")
    status = _select_qc_readiness_columns(readiness)
    if status.empty:
        st.info("No QC trace-summary readiness row is available.")
    else:
        st.dataframe(display_table(status), width="stretch")

    st.subheader("Loaded Rows")
    loaded_summary = _qc_loaded_row_summary(
        loaded,
        filtered,
        readiness=readiness,
        row_limit=row_limit,
    )
    st.dataframe(display_table(loaded_summary), width="stretch")
    limit_message = _qc_row_limit_message(readiness, loaded, row_limit)
    if limit_message:
        st.info(limit_message)
    st.caption(_qc_download_limit_message(download_limit))


def _select_qc_readiness_columns(readiness: pd.DataFrame | None) -> pd.DataFrame:
    """Return bounded QC readiness columns for dashboard display."""

    if readiness is None or readiness.empty:
        return pd.DataFrame()
    shown = [column for column in QC_READINESS_DISPLAY_COLUMNS if column in readiness.columns]
    return readiness.loc[:, shown].copy() if shown else pd.DataFrame()


def _qc_loaded_row_summary(
    loaded: pd.DataFrame,
    filtered: pd.DataFrame,
    *,
    readiness: pd.DataFrame | None = None,
    row_limit: int | None = None,
) -> pd.DataFrame:
    """Return compact counts for loaded and currently filtered QC rows."""

    table_rows = _qc_readiness_row_count(readiness)
    row_limit_text = "all" if row_limit is None else int(row_limit)
    loaded_subset = bool(table_rows is not None and len(loaded) < table_rows)
    subset_message = _qc_row_limit_message(readiness, loaded, row_limit)
    rows = [
        {
            "scope": "loaded",
            "table_rows": table_rows if table_rows is not None else len(loaded),
            "row_limit": row_limit_text,
            "loaded_subset": loaded_subset,
            "trace_rows": len(loaded),
            "event_station_pairs": len(queue_rows_from_filtered_trace_df(loaded)),
            "events": _nunique_if_present(loaded, "event_id"),
            "stations": _nunique_if_present(loaded, "station"),
            "components": _nunique_if_present(loaded, "component"),
            "message": subset_message or "All available trace-summary rows are loaded.",
        },
        {
            "scope": "filtered",
            "table_rows": table_rows if table_rows is not None else len(loaded),
            "row_limit": row_limit_text,
            "loaded_subset": loaded_subset,
            "trace_rows": len(filtered),
            "event_station_pairs": len(queue_rows_from_filtered_trace_df(filtered)),
            "events": _nunique_if_present(filtered, "event_id"),
            "stations": _nunique_if_present(filtered, "station"),
            "components": _nunique_if_present(filtered, "component"),
            "message": _empty_rows_message("trace QC") if filtered.empty else "Ready for current filters.",
        },
    ]
    return pd.DataFrame(rows)


def _qc_dashboard_row_limit() -> int | None:
    """Return the maximum QC rows loaded into the Streamlit process."""

    return _env_optional_positive_int(
        ("SVTK_QC_DASHBOARD_MAX_ROWS", "SVTK_DASHBOARD_MAX_ROWS"),
        default=DEFAULT_QC_DASHBOARD_MAX_ROWS,
    )


def _qc_dashboard_download_limit() -> int | None:
    """Return the maximum rows serialized by dashboard download buttons."""

    return _env_optional_positive_int(
        ("SVTK_QC_DASHBOARD_DOWNLOAD_ROWS", "SVTK_DASHBOARD_DOWNLOAD_ROWS"),
        default=DEFAULT_QC_DASHBOARD_DOWNLOAD_ROWS,
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
        return parsed if parsed > 0 else None
    return default


def _qc_readiness_row_count(readiness: pd.DataFrame | None) -> int | None:
    """Return the row count reported by QC readiness, when available."""

    if readiness is None or readiness.empty or "row_count" not in readiness.columns:
        return None
    value = pd.to_numeric(pd.Series([readiness.iloc[0].get("row_count")]), errors="coerce").iloc[0]
    return None if pd.isna(value) else int(value)


def _qc_row_limit_message(readiness: pd.DataFrame | None, loaded: pd.DataFrame, row_limit: int | None) -> str | None:
    """Return a dashboard message when only a bounded table prefix is loaded."""

    table_rows = _qc_readiness_row_count(readiness)
    if table_rows is None or row_limit is None or len(loaded) >= table_rows:
        return None
    return (
        f"Loaded {len(loaded):,} of {table_rows:,} trace-summary row(s). "
        "Filters, charts, manual-review queues, and downloads apply to the loaded subset. "
        "Set SVTK_QC_DASHBOARD_MAX_ROWS=all to load the full table."
    )


def _qc_download_limit_message(download_limit: int | None) -> str:
    """Return a concise explanation of dashboard download row limits."""

    if download_limit is None:
        return "Download buttons include all currently filtered loaded rows."
    return f"Download buttons include at most {download_limit:,} currently filtered loaded row(s)."


def _bounded_download_frame(df: pd.DataFrame, limit: int | None) -> tuple[pd.DataFrame, str | None]:
    """Return bounded dataframe rows and a caption when rows are truncated."""

    if limit is None or len(df) <= limit:
        return df, None
    message = f"Download is limited to the first {int(limit):,} of {len(df):,} filtered loaded row(s)."
    return df.head(int(limit)).copy(), message


def _bounded_queue_rows(queue_rows: list[dict[str, str]], limit: int | None) -> tuple[list[dict[str, str]], str | None]:
    """Return bounded queue rows and a caption when rows are truncated."""

    if limit is None or len(queue_rows) <= limit:
        return queue_rows, None
    message = (
        f"Manual-review queue download is limited to the first {int(limit):,} "
        f"of {len(queue_rows):,} queue row(s)."
    )
    return queue_rows[: int(limit)], message


def _qc_dashboard_startup_blocker(readiness: pd.DataFrame) -> str | None:
    """Return a startup-blocking message when the QC trace summary is not ready."""

    if readiness.empty:
        return "The QC trace-summary readiness check did not return a status row."
    row = readiness.iloc[0]
    if dashboard_ready_value(row.get("ready"), default=False):
        return None
    message = str(row.get("message") or "").strip()
    return message or "The QC trace-summary table is not ready."


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


def _configured_component_options(config: SpatialVTKConfig | None, df: pd.DataFrame) -> list[str]:
    """Return component options from config with dataframe fallback."""

    configured = list(FigureSelection.from_config(config, command="qc.dashboard").components) if config is not None else []
    detected = _options(df, "component", include_all=False)
    merged = []
    for item in [*configured, *detected]:
        token = str(item).upper()
        if token not in merged:
            merged.append(token)
    return ["all", *merged]


def _options(df: pd.DataFrame, column: str, *, include_all: bool) -> list[str]:
    """Return sorted option labels."""

    values = sorted([str(value) for value in df[column].dropna().unique()]) if column in df.columns else []
    return ["all", *values] if include_all else values


def _range_slider(label: str, df: pd.DataFrame, column: str) -> tuple[float | None, float | None] | None:
    """Create a numeric range slider when possible."""

    if column not in df.columns:
        return None
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return None
    lower, upper = float(values.min()), float(values.max())
    if lower == upper:
        return (lower, upper)
    return st.slider(label, min_value=lower, max_value=upper, value=(lower, upper))


def _date_range(df: pd.DataFrame) -> tuple[pd.Timestamp | None, pd.Timestamp | None] | None:
    """Create a date range input when event dates are available."""

    if "event_date" not in df.columns:
        return None
    dates = pd.to_datetime(df["event_date"], errors="coerce").dropna()
    if dates.empty:
        return None
    start, end = st.date_input("Event Date Range", value=(dates.min().date(), dates.max().date()))
    return (pd.Timestamp(start), pd.Timestamp(end))


def _band_options(df: pd.DataFrame) -> list[str]:
    """Return configured/detected band options."""

    for column in ("band", "passband", "dominant_band_label"):
        if column in df.columns:
            return ["all", *sorted(df[column].dropna().astype(str).unique().tolist(), key=band_display_label)]
    return []


def _amplitude_columns(df: pd.DataFrame) -> list[str]:
    """Return configured band-specific amplitude columns."""

    return [column for column in df.columns if column == "raw_peak_abs" or column.startswith("band_peak_abs")]


def _band_content_columns(df: pd.DataFrame) -> list[str]:
    """Return configured band-specific content columns."""

    return [column for column in df.columns if column == "dominant_period_s" or column.startswith("energy_frac")]


def _qc_chart_columns_or_message(
    df: pd.DataFrame,
    columns: list[str],
    column_label: str,
) -> tuple[list[str], str | None]:
    """Return chart columns or the explicit empty-state message for one QC tab."""

    if df.empty:
        return [], _empty_rows_message("trace QC")
    if not columns:
        return [], _missing_columns_message(column_label)
    return columns, None


def _qc_column_label(column: str) -> str:
    """Return a readable QC column label."""

    return column.replace("band_peak_abs_", "Peak amplitude ").replace("energy_frac_", "Energy fraction ").replace("_", " ").replace(" s", " sec").title()


def _empty_rows_message(row_label: str) -> str:
    """Return a consistent filtered-empty dashboard message."""

    return f"No {row_label} rows match the selected filters."


def _missing_columns_message(column_label: str) -> str:
    """Return a consistent missing-column dashboard message."""

    return f"No {column_label} columns are available in the loaded trace-summary table."


def _nunique_if_present(df: pd.DataFrame, column: str) -> int:
    """Return unique non-null values when a column exists."""

    return int(df[column].nunique(dropna=True)) if column in df.columns else 0


if __name__ == "__main__":
    main()
