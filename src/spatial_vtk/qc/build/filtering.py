"""Inventory lookup and filtering helpers for QC workflows."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from spatial_vtk.qc.summary.rules import INVENTORY_STANDARD_BANDS


@dataclass(frozen=True)
class InventoryBandSpec:
    """Describe one passband present in a trace-inventory CSV."""

    label: str
    period_min: float
    period_max: float


class TraceInventoryLookup(dict):
    """Dictionary lookup with trace-inventory metadata."""

    def __init__(
        self,
        rows: dict[tuple[str, str, str, str, str], dict[str, str]] | None = None,
        *,
        csv_path: Path | None = None,
        available_bands: list[InventoryBandSpec] | None = None,
        disabled_requested_bands: set[str] | None = None,
    ) -> None:
        """Create a trace-inventory lookup object."""

        super().__init__(rows or {})
        self.csv_path = csv_path
        self.available_bands = list(available_bands or [])
        self.disabled_requested_bands = set(disabled_requested_bands or set())
        self.qc_disabled_for_requested_bands = bool(self.disabled_requested_bands)


def normalize_observed_variant(text: str | None) -> str:
    """Normalize one observed-variant label."""

    token = str(text or "").strip().lower()
    return token or "nonrotated"


def normalize_component(component: str | None) -> str:
    """Normalize one component code."""

    return str(component or "").strip().upper()


def normalize_band_label(label: str | None) -> str:
    """Normalize one inventory band label."""

    return str(label or "").strip().lower()


def normalize_event_id(event_id: object) -> str:
    """Normalize one event identifier for inventory lookup keys."""

    return str(event_id or "").strip()


def normalize_station_code(station: object) -> str:
    """Normalize one station code for inventory lookup keys."""

    return str(station or "").strip().upper()


def inventory_lookup_key(
    observed_variant: str,
    event_id: str,
    station: str,
    component: str,
    passband_label: str,
) -> tuple[str, str, str, str, str]:
    """Build one normalized inventory key tuple."""

    return (
        normalize_observed_variant(observed_variant),
        normalize_event_id(event_id),
        normalize_station_code(station),
        normalize_component(component),
        normalize_band_label(passband_label),
    )


def period_band_label(period_min: float | None, period_max: float | None) -> str | None:
    """Return the canonical period-band label for one requested band."""

    if period_min is None or period_max is None:
        return None
    try:
        pmin = float(period_min)
        pmax = float(period_max)
    except Exception:
        return None
    if pmin <= 0.0 or pmax <= pmin:
        return None
    return f"{_format_period_token(pmin)}-{_format_period_token(pmax)}s"


def band_key_from_label(label: str) -> str:
    """Convert a period-band label to a stable CSV column suffix."""

    text = str(label).strip().lower().replace(" ", "")
    if text.endswith("sec"):
        text = text[:-3] + "s"
    if not text.endswith("s"):
        text = f"{text}s"
    return text.replace(".", "p").replace("-", "_")


def band_label_from_key(key: str) -> str | None:
    """Convert one inventory CSV suffix to a period-band label."""

    text = str(key).strip().lower()
    if not text.endswith("s") or "_" not in text:
        return None
    left, right = text[:-1].split("_", 1)
    try:
        return period_band_label(float(left.replace("p", ".")), float(right.replace("p", ".")))
    except Exception:
        return None


def parse_period_band_label(label: str) -> tuple[float, float] | None:
    """Parse a period-band label into ``(period_min, period_max)``."""

    text = str(label).strip().lower().replace(" ", "")
    text = text.removesuffix("seconds").removesuffix("second").removesuffix("sec").removesuffix("s")
    if "-" not in text:
        return None
    left, right = text.split("-", 1)
    try:
        pmin = float(left)
        pmax = float(right)
    except Exception:
        return None
    if pmin <= 0.0 or pmax <= pmin:
        return None
    return pmin, pmax


def load_trace_inventory_lookup(csv_path: Path | str | None) -> TraceInventoryLookup:
    """Load one master inventory CSV into a normalized lookup dictionary."""

    if csv_path is None:
        return TraceInventoryLookup()
    path = Path(csv_path).expanduser().resolve()
    if not path.exists():
        return TraceInventoryLookup(csv_path=path)

    lookup: dict[tuple[str, str, str, str, str], dict[str, str]] = {}
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        available_bands = _band_specs_from_fieldnames(reader.fieldnames)
        for row in reader:
            observed_variant = normalize_observed_variant(row.get("observed_variant", "nonrotated"))
            for band in available_bands:
                band_key = band_key_from_label(band.label)
                key = inventory_lookup_key(
                    observed_variant,
                    row.get("event_id", ""),
                    row.get("station", ""),
                    row.get("component", ""),
                    band.label,
                )
                lookup[key] = {
                    "reject": str(row.get(f"reject_{band_key}", "")).strip().lower(),
                    "reject_reason": str(row.get(f"reject_reason_{band_key}", "")).strip(),
                    "observed_variant": observed_variant,
                    "event_id": str(row.get("event_id", "")),
                    "station": normalize_station_code(row.get("station", "")),
                    "component": normalize_component(row.get("component", "")),
                    "passband_label": band.label,
                }
    return TraceInventoryLookup(lookup, csv_path=path, available_bands=available_bands)


def relevant_inventory_bands(
    period_min: float | None,
    period_max: float | None,
    *,
    available_bands: list[InventoryBandSpec] | None = None,
) -> list[str]:
    """Resolve which inventory bands are relevant for one requested band."""

    requested_label = period_band_label(period_min, period_max)
    bands = available_bands or [InventoryBandSpec(*band) for band in INVENTORY_STANDARD_BANDS]
    if requested_label:
        for band in bands:
            if normalize_band_label(band.label) == normalize_band_label(requested_label):
                return [band.label]
    if period_min is None or period_max is None:
        return [band.label for band in bands]
    matches = []
    for band in bands:
        if max(float(period_min), band.period_min) < min(float(period_max), band.period_max):
            matches.append(band.label)
    return matches


def trace_passband_is_accepted(
    lookup: dict[tuple[str, str, str, str, str], dict[str, str]],
    *,
    observed_variant: str,
    event_id: str,
    station: str,
    component: str,
    passband_label: str | None = None,
    period_min: float | None = None,
    period_max: float | None = None,
) -> bool:
    """Return whether one trace is accepted for one passband request."""

    if not lookup:
        return True
    labels = [passband_label] if passband_label else relevant_inventory_bands(
        period_min,
        period_max,
        available_bands=getattr(lookup, "available_bands", None),
    )
    if not labels:
        return trace_has_any_accepted_passband(
            lookup,
            observed_variant=observed_variant,
            event_id=event_id,
            station=station,
            component=component,
        )
    return all(
        _row_is_accepted(
            lookup.get(inventory_lookup_key(observed_variant, event_id, station, component, str(label)))
        )
        for label in labels
    )


def trace_has_any_accepted_passband(
    lookup: dict[tuple[str, str, str, str, str], dict[str, str]],
    *,
    observed_variant: str,
    event_id: str,
    station: str,
    component: str,
) -> bool:
    """Return whether one trace has at least one accepted inventory passband."""

    if not lookup:
        return True
    labels = [band.label for band in getattr(lookup, "available_bands", [])] or [label for label, _, _ in INVENTORY_STANDARD_BANDS]
    return any(
        _row_is_accepted(
            lookup.get(inventory_lookup_key(observed_variant, event_id, station, component, label))
        )
        for label in labels
    )


def event_station_has_any_accepted_component(
    lookup: dict[tuple[str, str, str, str, str], dict[str, str]],
    *,
    observed_variant: str,
    event_id: str,
    station: str,
    components: tuple[str, ...] | list[str],
    period_min: float | None = None,
    period_max: float | None = None,
) -> bool:
    """Return whether any requested component survives inventory QC."""

    if not lookup:
        return True
    return any(
        trace_passband_is_accepted(
            lookup,
            observed_variant=observed_variant,
            event_id=event_id,
            station=station,
            component=str(component),
            period_min=period_min,
            period_max=period_max,
        )
        for component in components
    )


def filter_stream_by_inventory(
    stream: Any,
    lookup: dict[tuple[str, str, str, str, str], dict[str, str]],
    *,
    observed_variant: str,
    event_id: str,
) -> Any:
    """Filter a stream to traces with at least one accepted inventory band."""

    if not lookup or stream is None:
        return stream
    keep = []
    for trace in stream:
        stats = getattr(trace, "stats", None)
        station = getattr(stats, "station", "")
        channel = str(getattr(stats, "channel", "")).strip().upper()
        component = channel[-1] if channel else ""
        if trace_has_any_accepted_passband(
            lookup,
            observed_variant=observed_variant,
            event_id=event_id,
            station=station,
            component=component,
        ):
            keep.append(trace)
    try:
        return stream.__class__(keep)
    except Exception:
        return keep


def _format_period_token(value: float) -> str:
    """Format one period bound for labels and CSV columns."""

    number = float(value)
    return f"{int(number)}" if number.is_integer() else f"{number:g}"


def _band_specs_from_fieldnames(fieldnames: list[str] | None) -> list[InventoryBandSpec]:
    """Infer inventory passbands from CSV headers."""

    specs: dict[str, InventoryBandSpec] = {}
    for field in fieldnames or []:
        if not str(field).startswith("reject_") or str(field).startswith("reject_reason_"):
            continue
        label = band_label_from_key(str(field)[len("reject_") :])
        parsed = parse_period_band_label(label or "")
        if label is not None and parsed is not None:
            specs[normalize_band_label(label)] = InventoryBandSpec(label, parsed[0], parsed[1])
    if not specs:
        for label, period_min, period_max in INVENTORY_STANDARD_BANDS:
            specs[normalize_band_label(label)] = InventoryBandSpec(label, float(period_min), float(period_max))
    return sorted(specs.values(), key=lambda item: (item.period_min, item.period_max))


def _row_is_accepted(row: Mapping[str, Any] | None) -> bool:
    """Return whether one lookup row represents acceptance."""

    if row is None:
        return False
    if hasattr(row, "empty") and bool(getattr(row, "empty")):
        return False
    return str(row.get("reject", "")).strip().lower() not in {"1", "true", "yes", "y", "reject", "rejected"}
