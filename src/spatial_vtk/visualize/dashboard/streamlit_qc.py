"""Streamlit QC Explorer entrypoint."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from spatial_vtk.config.runtime import SpatialVTKConfig
from spatial_vtk.visualize.dashboard.charts import build_qc_bar_figure, build_qc_histogram_figure
from spatial_vtk.visualize.dashboard.exports import normalize_manual_review_queue, queue_to_csv_bytes
from spatial_vtk.visualize.dashboard.filters import filter_qc_dashboard_rows
from spatial_vtk.config.labels import band_display_label, display_table
from spatial_vtk.visualize.qc.overview import load_trace_qc_summary, queue_rows_from_filtered_trace_df
from spatial_vtk.visualize.selection import FigureSelection, configured_band_options


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
    try:
        df = _load_trace_summary_cached(trace_summary)
    except Exception as exc:
        st.error(str(exc))
        return
    config = _load_optional_config(config_path)
    _render_qc_dashboard(df, config)


def _render_qc_dashboard(df: pd.DataFrame, config: SpatialVTKConfig | None = None) -> None:
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
    overview_tab, amp_tab, timing_tab, band_tab, table_tab, queue_tab = st.tabs(["Overview", "Amplitudes", "Timing", "Band Content", "Trace Table", "Manual Review Queue"])
    with overview_tab:
        cols = st.columns(5)
        cols[0].metric("Traces", f"{len(filtered):,}")
        cols[1].metric("Event/Station Pairs", f"{len(queue_rows_from_filtered_trace_df(filtered)):,}")
        cols[2].metric("Events", f"{filtered['event_id'].nunique() if 'event_id' in filtered else 0:,}")
        cols[3].metric("Stations", f"{filtered['station'].nunique() if 'station' in filtered else 0:,}")
        cols[4].metric("Components", f"{filtered['component'].nunique() if 'component' in filtered else 0:,}")
        if "dominant_band_label" in filtered.columns:
            st.plotly_chart(build_qc_bar_figure(filtered, column="dominant_band_label", title="Dominant Band Counts"), width="stretch", key="overview_dominant_band_counts")
    with amp_tab:
        for column in _amplitude_columns(filtered):
            st.plotly_chart(build_qc_histogram_figure(filtered, value_col=column, title=_qc_column_label(column), clip_iqr=clip_iqr), width="stretch", key=f"amp_{column}")
    with timing_tab:
        for column in [item for item in ("start_rel_s", "end_rel_s", "duration_s") if item in filtered.columns]:
            st.plotly_chart(build_qc_histogram_figure(filtered, value_col=column, title=_qc_column_label(column), clip_iqr=clip_iqr), width="stretch", key=f"timing_{column}")
    with band_tab:
        if "dominant_band_label" in filtered.columns:
            st.plotly_chart(build_qc_bar_figure(filtered, column="dominant_band_label", title="Dominant Band Counts"), width="stretch", key="band_dominant_band_counts")
        for column in _band_content_columns(filtered):
            st.plotly_chart(build_qc_histogram_figure(filtered, value_col=column, title=_qc_column_label(column), clip_iqr=clip_iqr), width="stretch", key=f"band_{column}")
    with table_tab:
        st.dataframe(display_table(filtered, max_rows=5000), width="stretch")
        st.download_button("Download filtered trace rows", filtered.to_csv(index=False).encode("utf-8"), file_name="filtered_trace_qc_rows.csv")
    with queue_tab:
        queue_rows = normalize_manual_review_queue(queue_rows_from_filtered_trace_df(filtered))
        st.metric("Event/Station Pairs in Queue", f"{len(queue_rows):,}")
        st.dataframe(display_table(pd.DataFrame(queue_rows)), width="stretch")
        st.download_button("Download manual-review queue CSV", queue_to_csv_bytes(queue_rows), file_name="manual_review_queue.csv")
        st.caption("The exported queue is formatted for the manual QC picker and can be passed to the manual waveform-review workflow.")


@st.cache_data(show_spinner=False)
def _load_trace_summary_cached(path: str) -> pd.DataFrame:
    """Load trace summary with Streamlit caching."""

    return load_trace_qc_summary(path)


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


def _qc_column_label(column: str) -> str:
    """Return a readable QC column label."""

    return column.replace("band_peak_abs_", "Peak amplitude ").replace("energy_frac_", "Energy fraction ").replace("_", " ").replace(" s", " sec").title()


if __name__ == "__main__":
    main()
