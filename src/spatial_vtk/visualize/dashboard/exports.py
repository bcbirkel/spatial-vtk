"""Export helpers for Streamlit dashboard selections."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

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


def write_dashboard_filtered_export(df: pd.DataFrame, output_path: str | Path) -> Path:
    """Write filtered dashboard rows to CSV, Parquet, or JSON."""

    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        df.to_parquet(path, index=False)
    elif suffix == ".json":
        path.write_text(df.to_json(orient="records", indent=2), encoding="utf-8")
    else:
        df.to_csv(path, index=False)
    return path


def write_manual_review_queue(filtered_trace_df: pd.DataFrame | list[dict[str, object]], output_path: str | Path) -> Path:
    """Write a manual QC picker queue from filtered dashboard rows.

    The output CSV uses the event/station queue columns consumed by the manual
    QC picker. Additional missing columns are filled with blank strings.
    """

    rows = filtered_trace_df if isinstance(filtered_trace_df, list) else _queue_rows_from_filtered_trace_df(filtered_trace_df)
    normalized = normalize_manual_review_queue(rows)
    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    else:
        pd.DataFrame(normalized, columns=list(QUEUE_COLUMNS)).to_csv(path, index=False)
    return path


def normalize_manual_review_queue(rows: list[dict[str, object]]) -> list[dict[str, str]]:
    """Normalize queue rows for the manual QC picker."""

    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        event_id = str(row.get("event_id", "")).strip()
        station = str(row.get("station", "")).strip().upper()
        if not event_id or not station:
            continue
        key = (event_id, station)
        if key in seen:
            continue
        seen.add(key)
        payload: dict[str, str] = {}
        for column in QUEUE_COLUMNS:
            value = row.get(column, "")
            payload[column] = "" if pd.isna(value) else str(value).strip()
        payload["event_id"] = event_id
        payload["station"] = station
        normalized.append(payload)
    return normalized


def queue_to_csv_bytes(rows: list[dict[str, object]]) -> bytes:
    """Return normalized manual-review queue rows as CSV bytes."""

    normalized = normalize_manual_review_queue(rows)
    return pd.DataFrame(normalized, columns=list(QUEUE_COLUMNS)).to_csv(index=False).encode("utf-8")


def _queue_rows_from_filtered_trace_df(filtered_trace_df: pd.DataFrame) -> list[dict[str, object]]:
    """Convert filtered trace rows into manual-review queue rows."""

    if filtered_trace_df.empty:
        return []
    work = filtered_trace_df.copy()
    for column in QUEUE_COLUMNS:
        if column not in work.columns:
            work[column] = ""
    return work.loc[:, list(QUEUE_COLUMNS)].drop_duplicates(subset=["event_id", "station"]).sort_values(["event_id", "station"]).to_dict(orient="records")


__all__ = [
    "normalize_manual_review_queue",
    "queue_to_csv_bytes",
    "write_dashboard_filtered_export",
    "write_manual_review_queue",
]
