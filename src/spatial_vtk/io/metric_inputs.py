"""Metric workflow input table normalization helpers.

Purpose
-------
This module defines the public table contracts used before metric calculation:
waveform inventories for observed/synthetic files and side-specific QC tables.

Usage examples
--------------
Normalize a waveform inventory:
  ``inventory = normalize_metric_waveform_inventory(raw_df, source="observed")``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


METRIC_WAVEFORM_COLUMNS: tuple[str, ...] = (
    "source",
    "event_id",
    "station",
    "component",
    "model",
    "waveform_path",
    "dt",
    "sampling_rate",
    "starttime",
    "endtime",
    "synthetic_max_frequency_hz",
)

METRIC_QC_COLUMNS: tuple[str, ...] = (
    "source",
    "event_id",
    "station",
    "component",
    "passband",
    "metric_group",
    "metric",
    "period_s",
    "qc_status",
    "qc_reason",
    "trace_start_s",
    "sample_interval_s",
    "valid_start_rel_s",
    "valid_end_rel_s",
    "valid_start_sample",
    "valid_end_sample",
)

WAVEFORM_ALIASES: dict[str, tuple[str, ...]] = {
    "source": ("source", "waveform_source", "waveform_role", "role"),
    "event_id": ("event_id", "event", "event_title", "id"),
    "station": ("station", "station_code", "station_name", "Station"),
    "component": ("component", "component_code", "channel_component"),
    "model": ("model", "model_alias", "simulation_model", "synthetic_model"),
    "waveform_path": ("waveform_path", "path", "file", "filename", "filepath"),
    "dt": ("dt", "delta", "sample_interval_s"),
    "sampling_rate": ("sampling_rate", "fs", "sampling_rate_hz"),
    "starttime": ("starttime", "start_time"),
    "endtime": ("endtime", "end_time"),
    "synthetic_max_frequency_hz": ("synthetic_max_frequency_hz", "max_frequency_hz", "fmax_hz"),
}

QC_ALIASES: dict[str, tuple[str, ...]] = {
    "source": ("source", "waveform_source", "waveform_role", "role"),
    "event_id": ("event_id", "event", "event_title", "id"),
    "station": ("station", "station_code", "station_name", "Station"),
    "component": ("component", "component_code", "channel_component"),
    "passband": ("passband", "passband_label", "band"),
    "metric_group": ("metric_group", "group"),
    "metric": ("metric", "metric_name"),
    "period_s": ("period_s", "period", "period_sec"),
    "qc_status": ("qc_status", "status", "accepted", "reject"),
    "qc_reason": ("qc_reason", "reason", "reject_reason"),
    "trace_start_s": ("trace_start_s", "start_rel_s", "valid_reference_start_s"),
    "sample_interval_s": ("sample_interval_s", "dt", "delta"),
    "valid_start_rel_s": ("valid_start_rel_s", "valid_start_s", "usable_start_rel_s"),
    "valid_end_rel_s": ("valid_end_rel_s", "valid_end_s", "usable_end_rel_s"),
    "valid_start_sample": ("valid_start_sample", "valid_start_index", "usable_start_sample"),
    "valid_end_sample": ("valid_end_sample", "valid_end_index", "usable_end_sample"),
}


def normalize_metric_waveform_inventory(
    table: pd.DataFrame | str | Path,
    *,
    source: str | None = None,
    synthetic_max_frequency_hz: float | None = None,
) -> pd.DataFrame:
    """Normalize an observed or synthetic waveform inventory.

    Parameters
    ----------
    table
        Raw inventory table or CSV/parquet path.
    source
        Optional source override, usually ``"observed"`` or ``"synthetic"``.
    synthetic_max_frequency_hz
        Optional synthetic max-frequency default for rows missing a value.

    Returns
    -------
    pandas.DataFrame
        Normalized inventory with public metric workflow columns.
    """

    df = _read_table(table)
    out = _normalize_columns(df, WAVEFORM_ALIASES, METRIC_WAVEFORM_COLUMNS)
    if source is not None:
        out["source"] = str(source)
    out["source"] = out["source"].replace("", "observed").astype(str).str.strip().str.lower()
    out["station"] = out["station"].astype(str).str.strip().str.upper()
    out["component"] = out["component"].astype(str).str.strip().str.upper()
    for column in ("dt", "sampling_rate", "synthetic_max_frequency_hz"):
        out[column] = pd.to_numeric(out[column], errors="coerce")
    if synthetic_max_frequency_hz is not None:
        mask = out["source"].eq("synthetic") & out["synthetic_max_frequency_hz"].isna()
        out.loc[mask, "synthetic_max_frequency_hz"] = float(synthetic_max_frequency_hz)
    _require_any(out, ["event_id", "station", "component", "waveform_path"], table_name="waveform inventory")
    return out.loc[:, list(METRIC_WAVEFORM_COLUMNS)]


def normalize_metric_qc_table(table: pd.DataFrame | str | Path, *, source: str | None = None) -> pd.DataFrame:
    """Normalize a side-specific metric QC table.

    Parameters
    ----------
    table
        Raw QC table or CSV/parquet path.
    source
        Optional source override.

    Returns
    -------
    pandas.DataFrame
        Normalized QC table.
    """

    df = _read_table(table)
    out = _normalize_columns(df, QC_ALIASES, METRIC_QC_COLUMNS)
    if source is not None:
        out["source"] = str(source)
    out["source"] = out["source"].replace("", "observed").astype(str).str.strip().str.lower()
    out["station"] = out["station"].astype(str).str.strip().str.upper()
    out["component"] = out["component"].astype(str).str.strip().str.upper()
    for column in ("period_s", "trace_start_s", "sample_interval_s", "valid_start_rel_s", "valid_end_rel_s", "valid_start_sample", "valid_end_sample"):
        out[column] = pd.to_numeric(out[column], errors="coerce")
    out["qc_status"] = out["qc_status"].map(_normalize_qc_status)
    _require_any(out, ["source", "event_id", "station", "component", "qc_status"], table_name="metric QC table")
    return out.loc[:, list(METRIC_QC_COLUMNS)]


def metric_qc_lookup(qc_table: pd.DataFrame | str | Path | None) -> dict[tuple[str, str, str, str, str, str, str], dict[str, Any]]:
    """Build a lookup for side-specific metric QC decisions.

    Parameters
    ----------
    qc_table
        QC table or path. ``None`` returns an empty lookup.

    Returns
    -------
    dict
        Normalized lookup keyed by source/event/station/component/group/metric/period.
    """

    if qc_table is None:
        return {}
    df = normalize_metric_qc_table(qc_table)
    lookup: dict[tuple[str, str, str, str, str, str, str], dict[str, Any]] = {}
    for _, row in df.iterrows():
        key = (
            str(row["source"]),
            str(row["event_id"]),
            str(row["station"]),
            str(row["component"]),
            str(row["metric_group"]).lower(),
            str(row["metric"]),
            _period_key(row["period_s"]),
        )
        lookup[key] = row.to_dict()
    return lookup


def metric_qc_passed(row: dict[str, Any] | pd.Series | None) -> bool:
    """Return whether a normalized QC row passed."""

    if row is None:
        return True
    return str(row.get("qc_status", "")).strip().lower() in {"pass", "passed", "accepted", "ok", "true", "1"}


def comparison_qc_passed(obs_row: dict[str, Any] | None, syn_row: dict[str, Any] | None) -> bool:
    """Return whether both observed and synthetic QC rows pass."""

    return metric_qc_passed(obs_row) and metric_qc_passed(syn_row)


def _read_table(table: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Read a dataframe or table path."""

    if isinstance(table, pd.DataFrame):
        return table.copy()
    path = Path(table).expanduser()
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _normalize_columns(df: pd.DataFrame, aliases: dict[str, tuple[str, ...]], columns: tuple[str, ...]) -> pd.DataFrame:
    """Normalize dataframe columns using alias mappings."""

    out = pd.DataFrame(index=df.index)
    for public_name, candidates in aliases.items():
        source = _find_column(df, candidates)
        out[public_name] = df[source] if source is not None else ""
    return out.reindex(columns=list(columns))


def _find_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    """Find a dataframe column by exact or compact case-insensitive name."""

    exact = {str(column): str(column) for column in df.columns}
    compact = {str(column).lower().replace("_", ""): str(column) for column in df.columns}
    for candidate in candidates:
        if candidate in exact:
            return exact[candidate]
        key = str(candidate).lower().replace("_", "")
        if key in compact:
            return compact[key]
    return None


def _normalize_qc_status(value: object) -> str:
    """Normalize common QC status values."""

    text = str(value).strip().lower()
    if text in {"", "nan", "none"}:
        return "pass"
    if text in {"false", "0", "reject", "rejected", "fail", "failed"}:
        return "fail"
    if text in {"true", "1", "accept", "accepted", "pass", "passed", "ok"}:
        return "pass"
    return text


def _require_any(df: pd.DataFrame, columns: list[str], *, table_name: str) -> None:
    """Raise when required columns are empty."""

    missing = [column for column in columns if column not in df.columns or not df[column].astype(str).str.strip().replace("nan", "").any()]
    if missing:
        raise ValueError(f"{table_name} is missing required fields or values: {missing}")


def _period_key(value: object) -> str:
    """Return a stable string key for a spectral period."""

    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return ""
    return f"{float(numeric):g}"


__all__ = [
    "METRIC_WAVEFORM_COLUMNS",
    "METRIC_QC_COLUMNS",
    "normalize_metric_waveform_inventory",
    "normalize_metric_qc_table",
    "metric_qc_lookup",
    "metric_qc_passed",
    "comparison_qc_passed",
]
