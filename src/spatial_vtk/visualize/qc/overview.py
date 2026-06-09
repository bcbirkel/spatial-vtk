"""QC overview filtering and lightweight HTML export helpers.

Purpose
-------
This module prepares QC summary tables for notebook/docs inspection and manual
review queues without launching a dashboard server.

Usage examples
--------------
Filter a QC summary and build queue rows:
  ``queue = queue_rows_from_filtered_trace_df(filter_trace_summary(summary, component_filter="Z"))``
"""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from spatial_vtk.config.labels import display_table


NUMERIC_COLUMNS: tuple[str, ...] = (
    "magnitude",
    "distance_km",
    "start_rel_s",
    "end_rel_s",
    "duration_s",
    "raw_peak_abs",
    "dominant_period_s",
)
TEXT_COLUMNS: tuple[str, ...] = (
    "event_id",
    "station",
    "component",
    "network",
    "station_family",
    "dominant_band_label",
    "metadata_warning",
)
QUEUE_COLUMNS: tuple[str, ...] = (
    "event_id",
    "station",
    "event_title",
    "event_lat",
    "event_lon",
    "station_lat",
    "station_lon",
    "network",
    "distance_km",
    "source_context_count",
    "source_contexts",
)


def load_trace_qc_summary(table: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Load a trace QC summary table.

    Parameters
    ----------
    table
        DataFrame, CSV path, or parquet path.

    Returns
    -------
    pandas.DataFrame
        Normalized summary table.
    """

    df = _read_table(table)
    return normalize_trace_qc_summary(df)


def normalize_trace_qc_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize trace QC summary columns used by overview helpers.

    Parameters
    ----------
    df
        Raw trace summary table.

    Returns
    -------
    pandas.DataFrame
        Normalized copy with typed date, numeric, and text columns.
    """

    out = df.copy()
    if "event_date" in out.columns:
        out["event_date"] = pd.to_datetime(out["event_date"], errors="coerce")
    for column in NUMERIC_COLUMNS:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    for column in TEXT_COLUMNS:
        if column in out.columns:
            out[column] = out[column].fillna("").astype(str)
    return out


def filter_trace_summary(
    trace_df: pd.DataFrame,
    *,
    event_filter: str = "",
    station_family: str = "all",
    component_filter: str = "all",
    station_query: str = "",
    magnitude_range: tuple[float | None, float | None] | None = None,
    distance_range_km: tuple[float | None, float | None] | None = None,
    date_range: tuple[pd.Timestamp | str | None, pd.Timestamp | str | None] | None = None,
) -> pd.DataFrame:
    """Filter one trace-QC summary table.

    Parameters
    ----------
    trace_df
        Normalized trace summary table.
    event_filter
        Optional exact event ID filter.
    station_family
        ``all`` or a station-family value.
    component_filter
        ``all`` or one component token.
    station_query
        Optional station substring.
    magnitude_range
        Optional inclusive magnitude range.
    distance_range_km
        Optional inclusive distance range.
    date_range
        Optional inclusive date range.

    Returns
    -------
    pandas.DataFrame
        Filtered table.
    """

    df = normalize_trace_qc_summary(trace_df)
    if str(event_filter).strip() and "event_id" in df.columns:
        event_key = str(event_filter).strip().lower()
        df = df[df["event_id"].str.lower() == event_key]
    family_key = str(station_family or "all").strip().lower()
    if family_key not in {"", "all"} and "station_family" in df.columns:
        df = df[df["station_family"].str.lower() == family_key]
    component_key = str(component_filter or "all").strip().upper()
    if component_key not in {"", "ALL"} and "component" in df.columns:
        df = df[df["component"].str.upper() == component_key]
    if str(station_query).strip() and "station" in df.columns:
        token = str(station_query).strip().upper()
        df = df[df["station"].str.upper().str.contains(token, na=False)]
    if magnitude_range is not None and "magnitude" in df.columns:
        df = _filter_range(df, "magnitude", magnitude_range)
    if distance_range_km is not None and "distance_km" in df.columns:
        df = _filter_range(df, "distance_km", distance_range_km)
    if date_range is not None and "event_date" in df.columns:
        start, end = date_range
        if start is not None:
            df = df[df["event_date"] >= pd.Timestamp(start)]
        if end is not None:
            df = df[df["event_date"] <= pd.Timestamp(end)]
    return df.reset_index(drop=True)


def queue_rows_from_filtered_trace_df(filtered_trace_df: pd.DataFrame) -> list[dict[str, str]]:
    """Convert filtered trace rows into manual-review queue records.

    Parameters
    ----------
    filtered_trace_df
        Filtered trace summary table.

    Returns
    -------
    list[dict[str, str]]
        Deduplicated queue rows keyed by event and station.
    """

    if filtered_trace_df.empty:
        return []
    work = filtered_trace_df.copy()
    for column in QUEUE_COLUMNS:
        if column not in work.columns:
            work[column] = ""
    deduped = work.loc[:, list(QUEUE_COLUMNS)].drop_duplicates(subset=["event_id", "station"]).sort_values(["event_id", "station"])
    rows: list[dict[str, str]] = []
    for _, row in deduped.iterrows():
        record: dict[str, str] = {}
        for column in QUEUE_COLUMNS:
            record[column] = _format_queue_value(row[column], column=column)
        rows.append(record)
    return rows


def trace_qc_records(trace_df: pd.DataFrame) -> list[dict[str, object]]:
    """Convert a trace-QC table to JSON-safe records.

    Parameters
    ----------
    trace_df
        Trace summary dataframe.

    Returns
    -------
    list[dict[str, object]]
        JSON-safe records.
    """

    out: list[dict[str, object]] = []
    for row in normalize_trace_qc_summary(trace_df).to_dict(orient="records"):
        payload: dict[str, object] = {}
        for key, value in row.items():
            payload[key] = _json_value(value)
        out.append(payload)
    return out


def build_trace_qc_overview_html(
    trace_summary: pd.DataFrame | str | Path,
    output_root: str | Path,
    *,
    title: str = "Trace QC Overview",
) -> str:
    """Build a standalone QC overview HTML document.

    Parameters
    ----------
    trace_summary
        Trace summary dataframe or table path.
    output_root
        Output root recorded in the page metadata.
    title
        Page title.

    Returns
    -------
    str
        HTML document string with embedded JSON records.
    """

    df = load_trace_qc_summary(trace_summary)
    records = trace_qc_records(df)
    summary = {
        "n_rows": int(len(df)),
        "n_events": int(df["event_id"].nunique()) if "event_id" in df.columns else 0,
        "n_stations": int(df["station"].nunique()) if "station" in df.columns else 0,
        "n_components": int(df["component"].nunique()) if "component" in df.columns else 0,
        "output_root": str(Path(output_root).expanduser()),
        "written_at": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
    }
    table_preview = display_table(df, columns=("event_id", "station", "component", "station_family", "magnitude", "distance_km", "metadata_warning"), max_rows=500)
    table_html = table_preview.to_html(index=False, escape=True) if not table_preview.empty else "<p>No preview columns are available.</p>"
    payload_json = html.escape(json.dumps({"summary": summary, "records": records}, separators=(",", ":")))
    title_text = html.escape(str(title))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title_text}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; color: #1f2933; }}
    header {{ margin-bottom: 18px; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 20px; }}
    .metric {{ border: 1px solid #d7dee8; border-radius: 8px; padding: 10px 12px; background: #f8fafc; }}
    .metric strong {{ display: block; font-size: 1.35rem; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
    th, td {{ border-bottom: 1px solid #d7dee8; padding: 6px 8px; text-align: left; }}
    th {{ background: #edf2f7; }}
    code {{ background: #edf2f7; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <header>
    <h1>{title_text}</h1>
    <p>Generated {html.escape(summary["written_at"])}. Output root: <code>{html.escape(summary["output_root"])}</code></p>
  </header>
  <section class="summary">
    <div class="metric"><span>Rows</span><strong>{summary["n_rows"]}</strong></div>
    <div class="metric"><span>Events</span><strong>{summary["n_events"]}</strong></div>
    <div class="metric"><span>Stations</span><strong>{summary["n_stations"]}</strong></div>
    <div class="metric"><span>Components</span><strong>{summary["n_components"]}</strong></div>
  </section>
  <section>
    <h2>Preview</h2>
    {table_html}
  </section>
  <script id="trace-qc-data" type="application/json">{payload_json}</script>
</body>
</html>
"""


def write_trace_qc_overview_html(
    trace_summary: pd.DataFrame | str | Path,
    output_path: str | Path,
    *,
    output_root: str | Path | None = None,
    title: str = "Trace QC Overview",
) -> Path:
    """Write a standalone QC overview HTML file.

    Parameters
    ----------
    trace_summary
        Trace summary dataframe or table path.
    output_path
        Destination HTML path.
    output_root
        Optional output root recorded in the HTML metadata.
    title
        Page title.

    Returns
    -------
    pathlib.Path
    Written HTML path.
    """

    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    html_text = build_trace_qc_overview_html(trace_summary, output_root or path.parent, title=title)
    path.write_text(html_text, encoding="utf-8")
    return path


def _filter_range(df: pd.DataFrame, column: str, bounds: tuple[float | None, float | None]) -> pd.DataFrame:
    """Apply one inclusive numeric filter range."""

    out = df
    minimum, maximum = bounds
    if minimum is not None:
        out = out[out[column] >= float(minimum)]
    if maximum is not None:
        out = out[out[column] <= float(maximum)]
    return out


def _format_queue_value(value: object, *, column: str) -> str:
    """Format one manual-review queue field."""

    if pd.isna(value):
        return ""
    if column in {"event_lat", "event_lon", "station_lat", "station_lon", "distance_km"}:
        try:
            return f"{float(value):.6f}"
        except Exception:
            return ""
    return str(value).strip()


def _json_value(value: object) -> object:
    """Convert one value to a JSON-safe scalar."""

    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if value is None or pd.isna(value):
        return None
    return value


def _read_table(table: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Read a dataframe, CSV, or parquet path."""

    if isinstance(table, pd.DataFrame):
        return table.copy()
    path = Path(table).expanduser()
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path)


__all__ = [
    "build_trace_qc_overview_html",
    "filter_trace_summary",
    "load_trace_qc_summary",
    "normalize_trace_qc_summary",
    "queue_rows_from_filtered_trace_df",
    "trace_qc_records",
    "write_trace_qc_overview_html",
]
