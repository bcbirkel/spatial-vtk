"""Public display labels for metrics, transforms, and passbands.

Purpose
-------
This module keeps user-facing figures, maps, dashboards, and future CLI output
from showing internal variable names. It maps public metric identifiers, legacy
metric aliases, value/transform columns, and passband tokens to readable labels.

Usage examples
--------------
Use the helpers wherever text will be shown to a user:
  ``metric_display_name("C5")``
  ``value_column_display_name("log2_residual")``
  ``band_display_label("1-3s")``
"""

from __future__ import annotations

from collections.abc import Iterable
import re

import pandas as pd

from spatial_vtk.config.metrics import VALID_TRANSFORMS


ACRONYM_LABELS: dict[str, str] = {
    "cc": "CC",
    "cav": "CAV",
    "fas": "FAS",
    "geojson": "GeoJSON",
    "gof": "GOF",
    "la": "LA",
    "pga": "PGA",
    "pgd": "PGD",
    "pgv": "PGV",
    "psa": "PSA",
    "qc": "QC",
    "vs30": "Vs30",
}


METRIC_DISPLAY_NAMES: dict[str, str] = {
    "arias_duration": "Arias duration (5-95%)",
    "energy_duration": "Energy duration (5-95%)",
    "arias_intensity": "Arias intensity",
    "energy_intensity": "Energy integral",
    "PGA": "Peak acceleration (PGA)",
    "PGV": "Peak velocity (PGV)",
    "PGD": "Peak displacement (PGD)",
    "PSA": "Pseudo-spectral acceleration (PSA)",
    "FAS": "Fourier amplitude spectrum (FAS)",
    "traveltime_delay": "Traveltime delay",
    "original_cc": "Original cross correlation",
    "delay_corrected_cc": "Delay-corrected cross correlation",
    "CAV": "Cumulative absolute velocity (CAV)",
}

LEGACY_METRIC_ALIASES: dict[str, str] = {
    "C1": "arias_duration",
    "C2": "energy_duration",
    "C3": "arias_intensity",
    "C4": "energy_intensity",
    "C5": "PGA",
    "C6": "PGV",
    "C7": "PGD",
    "C8": "PSA",
    "C9": "FAS",
    "C10": "original_cc",
    "C11": "traveltime_delay",
    "C12": "delay_corrected_cc",
    "C13": "CAV",
}

VALUE_COLUMN_LABELS: dict[str, str] = {
    "value": "Metric value",
    "value_obs": "Observed value",
    "value_syn": "Synthetic value",
    "residual": "Observed - synthetic",
    "log2_residual": "log2(observed / synthetic)",
    "ln_residual": "ln(observed / synthetic)",
    "anderson_2004_gof": "Anderson 2004 GOF",
    "olsen_mayhew_gof": "Olsen-Mayhew GOF",
    "score": "GOF score",
    "med_value": "Median metric value",
    "med_value_obs": "Median observed value",
    "med_value_syn": "Median synthetic value",
    "med_resid": "Median observed - synthetic",
    "med_residual": "Median observed - synthetic",
    "med_log2_residual": "Median log2(observed / synthetic)",
    "med_ln_residual": "Median ln(observed / synthetic)",
    "med_anderson_2004_gof": "Median Anderson 2004 GOF",
    "med_olsen_mayhew_gof": "Median Olsen-Mayhew GOF",
    "med_score": "Median GOF score",
    "mean_residual": "Mean observed - synthetic",
    "mean_log2_residual": "Mean log2(observed / synthetic)",
    "log2_residual_centered": "Event-centered log2(observed / synthetic)",
    "mean_ln_residual": "Mean ln(observed / synthetic)",
    "mean_anderson_2004_gof": "Mean Anderson 2004 GOF",
    "mean_olsen_mayhew_gof": "Mean Olsen-Mayhew GOF",
    "mean_score": "Mean GOF score",
    "improvement": "Model improvement",
    "improvement_percent": "Model improvement (%)",
    "prediction_error": "Prediction error",
    "heldout_bias_error": "Held-out station bias error",
    "mean_centered": "Mean residual",
    "station_mean_centered": "Station mean residual",
    "observed_mean_centered": "Observed station bias",
    "predicted_mean_centered": "Predicted station bias",
    "feature_mean": "Feature mean",
    "field_value": "Spatial field value",
    "field_centered": "Event-centered residual",
}

MODEL_DISPLAY_NAMES: dict[str, str] = {
    "cvmsi": "CVM-SI",
    "cvmsi_alt": "CVM-SI Alt",
    "cvm-si": "CVM-SI",
    "cvm_si": "CVM-SI",
    "cvmsi_20260506_material_0p6x1p2_asdf": "CVM-SI",
    "cvmsi_unstructuredmesh_qp2qs_abs2.5_minvs500_minvp1700": "CVM-SI",
}

COLUMN_DISPLAY_LABELS: dict[str, str] = {
    "event_id": "Event ID",
    "event_title": "Event ID",
    "event": "Event",
    "station": "Station",
    "station_name": "Station",
    "network": "Network",
    "component": "Component",
    "station_component": "Component",
    "model": "Model",
    "simulation_model": "Simulation Model",
    "metric": "Metric",
    "metric_group": "Metric Group",
    "transform": "Transform",
    "value_column": "Displayed Value",
    "band": "Period Band",
    "passband": "Period Band",
    "simulation_band": "Period Band",
    "dominant_band_label": "Dominant Period Band",
    "period_s": "Period (sec)",
    "frequency_hz": "Frequency (Hz)",
    "value": "Metric Value",
    "value_obs": "Observed Value",
    "value_syn": "Synthetic Value",
    "residual": "Observed - Synthetic",
    "log2_residual": "Log2 Residual",
    "ln_residual": "Ln Residual",
    "anderson_2004_gof": "Anderson 2004 GOF",
    "olsen_mayhew_gof": "Olsen-Mayhew GOF",
    "score": "GOF Score",
    "n": "Records",
    "n_records": "Records",
    "n_events": "Events",
    "n_stations": "Stations",
    "lat": "Latitude",
    "lon": "Longitude",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "station_lat": "Station Latitude",
    "station_lon": "Station Longitude",
    "sta_lat": "Station Latitude",
    "sta_lon": "Station Longitude",
    "station_latitude": "Station Latitude",
    "station_longitude": "Station Longitude",
    "event_lat": "Event Latitude",
    "event_lon": "Event Longitude",
    "event_latitude": "Event Latitude",
    "event_longitude": "Event Longitude",
    "magnitude": "Magnitude",
    "event_magnitude": "Magnitude",
    "depth_km": "Depth (km)",
    "event_depth_km": "Depth (km)",
    "distance_km": "Distance (km)",
    "med_dist_km": "Median Distance (km)",
    "azimuth_deg": "Azimuth (deg)",
    "az_bin_deg": "Azimuth Bin (deg)",
    "dist_bin_km": "Distance Bin (km)",
    "vs30": "Vs30",
    "Vs30": "Vs30",
    "geology": "Geology",
    "geologic_description": "Geologic Description",
    "geomorphology_class": "Geomorphology Class",
    "mapped_region": "Mapped Region",
    "mapped_region_long_name": "Mapped Region Name",
    "mapped_region_type": "Mapped Region Type",
    "target_region_zone": "Target Region Zone",
    "lab_zone": "LA Basin Zone",
    "metadata_warning": "Metadata Warning",
    "reject_reason": "Reject Reason",
    "qc_status": "QC Status",
    "start_rel_s": "Start Time (sec)",
    "end_rel_s": "End Time (sec)",
    "duration_s": "Duration (sec)",
}

VALUE_COLUMN_ORDER: tuple[str, ...] = (
    "med_log2_residual",
    "log2_residual",
    "med_ln_residual",
    "ln_residual",
    "med_resid",
    "med_residual",
    "residual",
    "med_anderson_2004_gof",
    "anderson_2004_gof",
    "med_olsen_mayhew_gof",
    "olsen_mayhew_gof",
    "med_score",
    "score",
    "med_value",
    "value",
    "med_value_obs",
    "value_obs",
    "med_value_syn",
    "value_syn",
)


def normalize_metric_name(metric: object) -> str:
    """Return the public metric name for a metric token.

    Parameters
    ----------
    metric
        Public metric name, legacy C-code, or raw table token.

    Returns
    -------
    str
        Public metric token when known.
    """

    text = str(metric or "").strip()
    return LEGACY_METRIC_ALIASES.get(text.upper(), text)


def metric_display_name(metric: object) -> str:
    """Return a human-readable metric label.

    Parameters
    ----------
    metric
        Public metric name, legacy C-code, or period-specific metric token.

    Returns
    -------
    str
        Label suitable for figure titles, legends, and dashboards.
    """

    public_name = normalize_metric_name(metric)
    if public_name in METRIC_DISPLAY_NAMES:
        return METRIC_DISPLAY_NAMES[public_name]
    period = _period_from_metric(public_name)
    if period is not None:
        if public_name.upper().startswith("PSA"):
            return f"Pseudo-spectral acceleration at {period:g} sec"
        if public_name.upper().startswith("FAS"):
            return f"Fourier amplitude at {period:g} sec"
    return _title_from_token(public_name)


def model_display_name(model: object) -> str:
    """Return a human-readable model label.

    Parameters
    ----------
    model
        Raw model token from a metric table or configuration file.

    Returns
    -------
    str
        Label suitable for legends, titles, dashboards, and tables.
    """

    text = str(model or "").strip()
    if not text:
        return "Unknown model"
    key = text.lower()
    return MODEL_DISPLAY_NAMES.get(key, _title_from_token(text))


def value_column_display_name(column: object) -> str:
    """Return a human-readable metric value or transform-column label.

    Parameters
    ----------
    column
        Raw dataframe column name.

    Returns
    -------
    str
        Label suitable for an axis, colorbar, selector, or popup.
    """

    text = str(column or "").strip()
    return VALUE_COLUMN_LABELS.get(text, _title_from_token(text))


def available_dashboard_value_columns(df: pd.DataFrame, *, prefer_medians: bool = True) -> list[str]:
    """Return value columns that can color or plot dashboard data.

    Parameters
    ----------
    df
        Dashboard data table.
    prefer_medians
        Whether median summary columns should appear before row-level columns.

    Returns
    -------
    list[str]
        Existing numeric value columns in display order.
    """

    columns = set(df.columns)
    ordered = list(VALUE_COLUMN_ORDER)
    if not prefer_medians:
        ordered = sorted(ordered, key=lambda item: (item.startswith("med_"), VALUE_COLUMN_ORDER.index(item)))
    out = [column for column in ordered if column in columns]
    extras = [column for column in df.columns if _looks_like_value_column(column) and column not in out]
    return out + extras


def transform_display_options(transforms: Iterable[str] = VALID_TRANSFORMS) -> dict[str, str]:
    """Return human-readable labels for transform names.

    Parameters
    ----------
    transforms
        Transform column names.

    Returns
    -------
    dict[str, str]
        Mapping from raw transform names to display labels.
    """

    return {str(transform): value_column_display_name(str(transform)) for transform in transforms}


def band_display_label(band: object, configured_labels: dict[str, str] | None = None) -> str:
    """Return a human-readable passband label.

    Parameters
    ----------
    band
        Raw band token such as ``"1-3s"``, ``"1-3 sec"``, or ``"all"``.
    configured_labels
        Optional labels keyed by raw band token.

    Returns
    -------
    str
        User-facing period-band label.
    """

    text = str(band or "").strip()
    if configured_labels and text in configured_labels:
        return str(configured_labels[text])
    if text.lower() in {"", "all", "none", "nan"}:
        return "All periods"
    match = re.fullmatch(r"([0-9.]+)\s*[-_]\s*([0-9.]+)\s*(?:s|sec|seconds)?", text, flags=re.IGNORECASE)
    if match:
        return f"{float(match.group(1)):g}-{float(match.group(2)):g} sec"
    match = re.fullmatch(r"T?([0-9.]+)\s*(?:s|sec|seconds)?", text, flags=re.IGNORECASE)
    if match:
        return f"{float(match.group(1)):g} sec"
    return _title_from_token(text).replace(" Sec", " sec")


def band_display_options(bands: Iterable[object], configured_labels: dict[str, str] | None = None) -> dict[str, str]:
    """Return display labels keyed by raw band token.

    Parameters
    ----------
    bands
        Raw band tokens.
    configured_labels
        Optional explicit labels.

    Returns
    -------
    dict[str, str]
        Labels keyed by the original string token.
    """

    return {str(band): band_display_label(band, configured_labels) for band in bands}


def display_label(value: object, label_map: dict[str, str] | None = None) -> str:
    """Return a readable label for a generic feature or metric token.

    Parameters
    ----------
    value
        Raw feature, metric, or value token.
    label_map
        Optional exact-match override labels.

    Returns
    -------
    str
        Human-readable label.
    """

    text = str(value or "").strip()
    if label_map and text in label_map:
        return str(label_map[text])
    if text in VALUE_COLUMN_LABELS:
        return value_column_display_name(text)
    if text.lower() in MODEL_DISPLAY_NAMES:
        return model_display_name(text)
    if text in METRIC_DISPLAY_NAMES or text.upper() in LEGACY_METRIC_ALIASES or _period_from_metric(text) is not None:
        return metric_display_name(text)
    if text.startswith("event::"):
        event_id = text.split("::", 1)[1].replace("_", " ").strip()
        return f"Event {event_id}" if event_id else "Event"
    return _title_from_token(text)


def column_display_name(column: object, label_map: dict[str, str] | None = None) -> str:
    """Return a human-readable dataframe column header.

    Parameters
    ----------
    column
        Raw dataframe column name.
    label_map
        Optional exact-match override labels.

    Returns
    -------
    str
        Column label suitable for table previews, dashboards, and exports.
    """

    text = str(column or "").strip()
    if label_map and text in label_map:
        return str(label_map[text])
    if text in COLUMN_DISPLAY_LABELS:
        return COLUMN_DISPLAY_LABELS[text]
    if text in VALUE_COLUMN_LABELS:
        return _title_from_token(VALUE_COLUMN_LABELS[text])
    return display_label(text)


def column_display_lookup(columns: Iterable[object], label_map: dict[str, str] | None = None) -> dict[str, str]:
    """Return human-readable labels for dataframe columns.

    Parameters
    ----------
    columns
        Raw dataframe column names.
    label_map
        Optional exact-match override labels.

    Returns
    -------
    dict
        Mapping from raw column names to display labels.
    """

    return {str(column): column_display_name(column, label_map) for column in columns}


def display_table(
    df: pd.DataFrame,
    *,
    columns: Iterable[str] | None = None,
    max_rows: int | None = None,
    label_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Return a copy of a dataframe with human-readable values and headers.

    Parameters
    ----------
    df
        Source dataframe.
    columns
        Optional preferred raw columns. Missing columns are ignored.
    max_rows
        Optional row limit.
    label_map
        Optional exact-match override labels for column headers.

    Returns
    -------
    pandas.DataFrame
        Display copy with metric names, period bands, value-column names, and
        column headers converted to user-facing labels.
    """

    selected = [column for column in columns or df.columns if column in df.columns]
    out = df.loc[:, selected].copy()
    if max_rows is not None:
        out = out.head(int(max_rows))
    for column in ("metric",):
        if column in out.columns:
            out[column] = out[column].map(metric_display_name)
    for column in ("model", "simulation_model", "model_name"):
        if column in out.columns:
            out[column] = out[column].map(model_display_name)
    for column in ("band", "passband", "simulation_band", "dominant_band_label"):
        if column in out.columns:
            out[column] = out[column].map(band_display_label)
    for column in ("value_column", "transform"):
        if column in out.columns:
            out[column] = out[column].map(value_column_display_name)
    display_lookup = column_display_lookup(out.columns, label_map)
    display_lookup = _deduplicate_display_lookup(display_lookup)
    return out.rename(columns=display_lookup)


def _deduplicate_display_lookup(label_lookup: dict[str, str]) -> dict[str, str]:
    """Return display labels with duplicates disambiguated by raw names.

    Parameters
    ----------
    label_lookup
        Mapping from raw dataframe column names to proposed display labels.

    Returns
    -------
    dict
        Mapping whose display labels are unique and safe for dashboard tables.
    """

    counts: dict[str, int] = {}
    for label in label_lookup.values():
        counts[label] = counts.get(label, 0) + 1
    out: dict[str, str] = {}
    seen: dict[str, int] = {}
    for raw, label in label_lookup.items():
        if counts[label] == 1:
            out[raw] = label
            continue
        seen[label] = seen.get(label, 0) + 1
        raw_hint = _title_from_token(raw)
        suffix = raw_hint if raw_hint and raw_hint != label else str(seen[label])
        out[raw] = f"{label} ({suffix})"
    return out


def _looks_like_value_column(column: str) -> bool:
    """Return whether a column name likely stores a displayable metric value."""

    lowered = str(column).lower()
    if lowered in VALUE_COLUMN_LABELS:
        return True
    return lowered.startswith(("med_", "mean_")) and any(token in lowered for token in ("resid", "score", "gof", "value", "obs", "syn"))


def _period_from_metric(metric: str) -> float | None:
    """Parse an embedded period from a PSA/FAS metric token when present."""

    match = re.search(r"(?:PSA|FAS)[_T]*([0-9]+(?:\.[0-9]+)?)", str(metric), flags=re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1))


def _title_from_token(value: object) -> str:
    """Convert a variable-like token into a readable title."""

    text = str(value or "").strip()
    if not text:
        return "Unknown"
    words = re.sub(r"\s+", " ", text.replace("_", " ").replace("-", " ")).strip().split(" ")
    titled: list[str] = []
    for word in words:
        key = word.lower()
        if key in ACRONYM_LABELS:
            titled.append(ACRONYM_LABELS[key])
        elif word.isupper() and len(word) <= 5:
            titled.append(word)
        elif any(char.isupper() for char in word[1:]):
            titled.append(word)
        else:
            titled.append(word[:1].upper() + word[1:].lower())
    return " ".join(titled)


__all__ = [
    "LEGACY_METRIC_ALIASES",
    "METRIC_DISPLAY_NAMES",
    "MODEL_DISPLAY_NAMES",
    "VALUE_COLUMN_LABELS",
    "COLUMN_DISPLAY_LABELS",
    "VALUE_COLUMN_ORDER",
    "available_dashboard_value_columns",
    "band_display_label",
    "band_display_options",
    "column_display_lookup",
    "column_display_name",
    "display_label",
    "display_table",
    "metric_display_name",
    "model_display_name",
    "normalize_metric_name",
    "transform_display_options",
    "value_column_display_name",
]
