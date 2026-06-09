"""Table helpers for manual QC review queues.

Purpose
-------
This module owns small public table operations for manual quality-control
review: queue creation, decision CSV loading/writing, and applying manual
decisions to automated inventory rows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

DECISION_COLUMNS: tuple[str, ...] = (
    "event_id",
    "station",
    "component",
    "scope_kind",
    "scope_label",
    "decision",
    "reason_code",
    "notes",
    "reviewed_at",
)


def filter_trace_summary(
    df: pd.DataFrame,
    *,
    event_id: str | None = None,
    station: str | None = None,
    component: str | None = None,
    accepted: bool | None = None,
    reject_reason_contains: str | None = None,
) -> pd.DataFrame:
    """Filter a trace-summary table using common review fields."""

    out = df.copy()
    if event_id is not None and "event_id" in out.columns:
        out = out[out["event_id"].astype(str) == str(event_id)]
    if station is not None and "station" in out.columns:
        out = out[out["station"].astype(str).str.upper() == str(station).upper()]
    if component is not None and "component" in out.columns:
        out = out[out["component"].astype(str).str.upper() == str(component).upper()]
    if accepted is not None:
        if "accepted" in out.columns:
            out = out[out["accepted"].astype(bool) == bool(accepted)]
        elif "reject" in out.columns:
            out = out[out["reject"].astype(bool) != bool(accepted)]
    if reject_reason_contains and "reject_reason" in out.columns:
        out = out[out["reject_reason"].astype(str).str.contains(str(reject_reason_contains), case=False, na=False)]
    return out.reset_index(drop=True)


def queue_rows_from_filtered_trace_df(
    df: pd.DataFrame,
    *,
    key_columns: tuple[str, ...] = ("event_id", "station", "component"),
    status: str = "pending",
) -> list[dict[str, object]]:
    """Convert a filtered trace table into manual-review queue rows."""

    missing = [column for column in key_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing queue key columns: {missing}")
    rows: list[dict[str, object]] = []
    for _, row in df.drop_duplicates(list(key_columns)).iterrows():
        entry = {column: row[column] for column in key_columns}
        entry["status"] = status
        rows.append(entry)
    return rows


def decision_key(
    event_id: object,
    station: object,
    component: object,
    scope_kind: object,
    scope_label: object,
) -> tuple[str, str, str, str, str]:
    """Build the normalized key for one manual QC decision."""

    return (
        str(event_id or "").strip(),
        str(station or "").strip().upper(),
        str(component or "").strip().upper(),
        str(scope_kind or "").strip().lower(),
        str(scope_label or "").strip().lower(),
    )


def normalize_manual_qc_decisions(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize a manual QC decision table.

    Parameters
    ----------
    df
        Raw decision table.

    Returns
    -------
    pandas.DataFrame
        Decision table with public columns.
    """

    out = df.copy()
    for column in DECISION_COLUMNS:
        if column not in out.columns:
            out[column] = ""
    out["event_id"] = out["event_id"].astype(str).str.strip()
    out["station"] = out["station"].astype(str).str.strip().str.upper()
    out["component"] = out["component"].astype(str).str.strip().str.upper()
    out["scope_kind"] = out["scope_kind"].replace("", "full").astype(str).str.strip().str.lower()
    out["scope_label"] = out["scope_label"].replace("", "full").astype(str).str.strip().str.lower()
    out["decision"] = out["decision"].astype(str).str.strip().str.lower()
    return out.loc[:, list(DECISION_COLUMNS)]


def load_manual_qc_decisions(path: str | Path | None) -> pd.DataFrame:
    """Load manual QC decisions from CSV.

    Parameters
    ----------
    path
        Decision CSV path. Missing or ``None`` returns an empty table.

    Returns
    -------
    pandas.DataFrame
        Normalized decision table.
    """

    if path is None:
        return pd.DataFrame(columns=DECISION_COLUMNS)
    source = Path(path).expanduser()
    if not source.exists():
        return pd.DataFrame(columns=DECISION_COLUMNS)
    return normalize_manual_qc_decisions(pd.read_csv(source))


def write_manual_qc_decisions(df: pd.DataFrame, path: str | Path, *, overwrite: bool = True) -> Path:
    """Write manual QC decisions to CSV.

    Parameters
    ----------
    df
        Decision rows.
    path
        Output CSV path.
    overwrite
        Whether to replace an existing file.

    Returns
    -------
    pathlib.Path
        Written path.
    """

    output = Path(path).expanduser()
    if output.exists() and not overwrite:
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    normalize_manual_qc_decisions(df).to_csv(output, index=False)
    return output


def apply_manual_qc_decisions(
    inventory_df: pd.DataFrame,
    decisions: pd.DataFrame | str | Path | None,
    *,
    band_columns: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Apply manual accept/reject decisions to an automated inventory table.

    Parameters
    ----------
    inventory_df
        Automated QC inventory.
    decisions
        Decision table or CSV path.
    band_columns
        Optional reject-column suffixes. When omitted, columns named
        ``reject_*`` are inferred.

    Returns
    -------
    pandas.DataFrame
        Inventory copy with manual decision columns applied.
    """

    out = inventory_df.copy()
    decision_df = load_manual_qc_decisions(decisions) if not isinstance(decisions, pd.DataFrame) else normalize_manual_qc_decisions(decisions)
    out["manual_qc_decision"] = ""
    out["manual_qc_reason"] = ""
    out["manual_qc_notes"] = ""
    if decision_df.empty or out.empty:
        return out
    suffixes = list(band_columns or [column.removeprefix("reject_") for column in out.columns if column.startswith("reject_")])
    lookup = _decision_lookup(decision_df)
    for idx, row in out.iterrows():
        event_id = row.get("event_id", "")
        station = row.get("station", "")
        component = row.get("component", "")
        full = _lookup_decision(lookup, event_id, station, component, "full", "full")
        if full:
            _apply_decision_to_row(out, idx, suffixes, full)
        for suffix in suffixes:
            label = suffix.replace("_", "-").replace("p", ".")
            band = _lookup_decision(lookup, event_id, station, component, "band", label)
            if band:
                _apply_decision_to_row(out, idx, [suffix], band)
    return out


def _decision_lookup(decisions: pd.DataFrame) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    """Build a manual decision lookup."""

    lookup: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for _, row in decisions.iterrows():
        key = decision_key(row.get("event_id"), row.get("station"), row.get("component"), row.get("scope_kind"), row.get("scope_label"))
        lookup[key] = row.to_dict()
    return lookup


def _lookup_decision(
    lookup: dict[tuple[str, str, str, str, str], dict[str, Any]],
    event_id: object,
    station: object,
    component: object,
    scope_kind: str,
    scope_label: str,
) -> dict[str, Any] | None:
    """Find a component-specific or component-agnostic decision."""

    component_text = str(component or "").strip().upper()
    for candidate_component in (component_text, "", "ALL"):
        decision = lookup.get(decision_key(event_id, station, candidate_component, scope_kind, scope_label))
        if decision:
            return decision
    return None


def _apply_decision_to_row(out: pd.DataFrame, idx: Any, suffixes: list[str], decision: dict[str, Any]) -> None:
    """Apply one decision row to inventory reject columns."""

    value = str(decision.get("decision", "")).strip().lower()
    if value not in {"accept", "accepted", "reject", "rejected"}:
        return
    reject = value.startswith("reject")
    reason = str(decision.get("reason_code", "") or "manual_qc").strip()
    for suffix in suffixes:
        reject_col = f"reject_{suffix}"
        reason_col = f"reject_reason_{suffix}"
        if reject_col in out.columns:
            out.at[idx, reject_col] = reject
        if reason_col in out.columns:
            out.at[idx, reason_col] = reason if reject else ""
    out.at[idx, "manual_qc_decision"] = value
    out.at[idx, "manual_qc_reason"] = reason
    out.at[idx, "manual_qc_notes"] = str(decision.get("notes", ""))
