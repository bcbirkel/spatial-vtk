"""Config-driven row selection helpers for public figures and dashboards.

Purpose
-------
This module applies the active Spatial-VTK configuration to dataframe-backed
figures without making every plotting function parse config files itself.

Usage examples
--------------
Resolve and apply defaults before plotting:
  ``selection = FigureSelection.from_config(config, command="visualize.context")``
  ``plot_df = selection.apply(records)``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal
import re

import pandas as pd

from spatial_vtk.config.labels import band_display_label
from spatial_vtk.config.runtime import SpatialVTKConfig


@dataclass(frozen=True)
class FigureSelection:
    """Resolved row-selection settings for figure inputs.

    Parameters
    ----------
    components
        Component tokens to keep, or an empty tuple to keep all components.
    passbands
        Passband tokens to keep, or an empty tuple to keep all passbands.
    events
        Event identifiers to keep, or an empty tuple to keep all events.
    stations
        Station identifiers to keep, or an empty tuple to keep all stations.
    bounds
        Optional ``(lon_min, lon_max, lat_min, lat_max)`` map bounds.
    band_labels
        Optional display labels keyed by raw passband tokens.

    Returns
    -------
    FigureSelection
        Immutable selection object.
    """

    components: tuple[str, ...] = ()
    passbands: tuple[str, ...] = ()
    events: tuple[str, ...] = ()
    stations: tuple[str, ...] = ()
    bounds: tuple[float, float, float, float] | None = None
    band_labels: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_config(
        cls,
        config: SpatialVTKConfig | str | Path | None = None,
        *,
        command: str = "visualize",
        components: Iterable[object] | None = None,
        passbands: Iterable[object] | None = None,
        events: Iterable[object] | None = None,
        stations: Iterable[object] | None = None,
        bounds: str | Iterable[float] | None = None,
    ) -> "FigureSelection":
        """Resolve figure-selection settings from config plus overrides.

        Parameters
        ----------
        config
            Config object, config path, or ``None`` for no config.
        command
            Dotted command used to merge run defaults.
        components, passbands, events, stations, bounds
            Explicit overrides. When omitted, matching config values are used.

        Returns
        -------
        FigureSelection
            Selection object ready to apply to a dataframe.
        """

        cfg = _coerce_config(config)
        defaults = cfg.run_defaults(command) if cfg is not None else {}
        figure_cfg = dict(cfg.section("visualize", {}) or {}) if cfg is not None else {}
        merged: dict[str, Any] = {**figure_cfg, **defaults}
        raw_components = components if components is not None else merged.get("components")
        raw_passbands = passbands if passbands is not None else (merged.get("passbands") or merged.get("bands"))
        raw_events = events if events is not None else (merged.get("events") or merged.get("event_ids") or merged.get("event_list"))
        raw_stations = stations if stations is not None else (merged.get("stations") or merged.get("station_ids") or merged.get("station_list"))
        raw_bounds = bounds if bounds is not None else merged.get("bounds")
        resolved_bounds = cfg.resolve_bounds(raw_bounds) if cfg is not None and raw_bounds not in (None, "") else _coerce_bounds(raw_bounds)
        bands = _passband_tokens(raw_passbands)
        return cls(
            components=tuple(str(item).upper() for item in _as_tuple(raw_components)),
            passbands=bands,
            events=_as_tuple(raw_events),
            stations=tuple(str(item).upper() for item in _as_tuple(raw_stations)),
            bounds=resolved_bounds,
            band_labels={band: band_display_label(band) for band in bands},
        )

    def apply(
        self,
        df: pd.DataFrame,
        *,
        component_col: str = "component",
        band_cols: tuple[str, ...] = ("band", "passband", "dominant_band_label"),
        event_col: str = "event_id",
        station_col: str = "station",
    ) -> pd.DataFrame:
        """Apply configured component, passband, event, and station filters.

        Parameters
        ----------
        df
            Input table.
        component_col, band_cols, event_col, station_col
            Column names used for filtering when present.

        Returns
        -------
        pandas.DataFrame
            Filtered copy with reset index.
        """

        out = df.copy()
        if self.components and component_col in out.columns:
            out = out[out[component_col].astype(str).str.upper().isin(set(self.components))]
        if self.events and event_col in out.columns:
            keep_events = {str(item) for item in self.events}
            out = out[out[event_col].astype(str).isin(keep_events)]
        if self.stations and station_col in out.columns:
            keep_stations = {str(item).upper() for item in self.stations}
            out = out[out[station_col].astype(str).str.upper().isin(keep_stations)]
        if self.passbands:
            out = filter_by_bands(out, self.passbands, band_cols=band_cols)
        return out.reset_index(drop=True)


SpatialRelation = Literal["inside", "outside", "both"]


@dataclass(frozen=True)
class FigureSpatialSelection:
    """Resolved station/event spatial subset settings for figure inputs.

    Parameters
    ----------
    station_region_col, event_region_col
        Columns containing region labels, usually added by GeoJSON joins.
    station_regions, event_regions
        Region labels to select. Empty values mean any non-empty region label.
    station_region_relation, event_region_relation
        Whether to keep rows inside, outside, or on both sides of the selected
        region labels.
    station_bounds, event_bounds
        Optional ``(west, east, south, north)`` boxes for station/event points.
    station_corridor_col, event_corridor_col
        Columns containing corridor labels or booleans.

    Returns
    -------
    FigureSpatialSelection
        Immutable spatial selection object.
    """

    station_region_col: str | None = None
    station_regions: tuple[str, ...] = ()
    station_region_relation: SpatialRelation = "inside"
    event_region_col: str | None = None
    event_regions: tuple[str, ...] = ()
    event_region_relation: SpatialRelation = "inside"
    station_bounds: tuple[float, float, float, float] | None = None
    station_bounds_relation: SpatialRelation = "inside"
    event_bounds: tuple[float, float, float, float] | None = None
    event_bounds_relation: SpatialRelation = "inside"
    station_corridor_col: str | None = None
    station_corridors: tuple[str, ...] = ()
    station_corridor_relation: SpatialRelation = "inside"
    event_corridor_col: str | None = None
    event_corridors: tuple[str, ...] = ()
    event_corridor_relation: SpatialRelation = "inside"
    label: str | None = None

    @classmethod
    def from_inputs(
        cls,
        spatial_selection: "FigureSpatialSelection | dict[str, Any] | None" = None,
        **overrides: Any,
    ) -> "FigureSpatialSelection | None":
        """Build a spatial selector from an object, mapping, and overrides.

        Parameters
        ----------
        spatial_selection
            Existing selector or dictionary of selector fields.
        **overrides
            Explicit keyword overrides from a plotting function.

        Returns
        -------
        FigureSpatialSelection or None
            A selector when any spatial control is configured.
        """

        values: dict[str, Any] = {}
        if isinstance(spatial_selection, FigureSpatialSelection):
            values.update(spatial_selection.__dict__)
        elif isinstance(spatial_selection, dict):
            values.update(spatial_selection)
        elif spatial_selection is not None:
            raise TypeError("spatial_selection must be a FigureSpatialSelection, a dictionary, or None.")
        values.update({key: value for key, value in overrides.items() if value is not None})
        for key in ("station_regions", "event_regions", "station_corridors", "event_corridors"):
            values[key] = _as_tuple(values.get(key))
        for key in ("station_region_relation", "event_region_relation", "station_bounds_relation", "event_bounds_relation", "station_corridor_relation", "event_corridor_relation"):
            values[key] = _normalize_spatial_relation(values.get(key, "inside"))
        for key in ("station_bounds", "event_bounds"):
            values[key] = _coerce_bounds(values.get(key))
        allowed = set(cls.__dataclass_fields__)
        clean = {key: value for key, value in values.items() if key in allowed}
        if not any(value not in (None, "", ()) for key, value in clean.items() if key != "label"):
            return None
        return cls(**clean)

    def apply(self, df: pd.DataFrame, *, require_match: bool = True) -> tuple[pd.DataFrame, str | None]:
        """Apply station/event spatial filters to a dataframe.

        Parameters
        ----------
        df
            Input table with station/event region, corridor, or coordinate
            columns.
        require_match
            Whether to raise if configured selectors remove every row.

        Returns
        -------
        tuple[pandas.DataFrame, str or None]
            Filtered table and readable subset label.
        """

        out = df.copy()
        labels: list[str] = []
        out, label = _apply_category_subset(
            out,
            column=self.station_region_col,
            values=self.station_regions,
            relation=self.station_region_relation,
            subject="Stations",
            kind="region",
        )
        if label:
            labels.append(label)
        out, label = _apply_category_subset(
            out,
            column=self.event_region_col,
            values=self.event_regions,
            relation=self.event_region_relation,
            subject="Events",
            kind="region",
        )
        if label:
            labels.append(label)
        out, label = _apply_bounds_subset(
            out,
            bounds=self.station_bounds,
            relation=self.station_bounds_relation,
            subject="Stations",
            lon_candidates=("station_lon", "station_longitude", "station_x", "lon", "longitude"),
            lat_candidates=("station_lat", "station_latitude", "station_y", "lat", "latitude"),
        )
        if label:
            labels.append(label)
        out, label = _apply_bounds_subset(
            out,
            bounds=self.event_bounds,
            relation=self.event_bounds_relation,
            subject="Events",
            lon_candidates=("event_lon", "event_longitude", "source_lon", "source_longitude", "evlo"),
            lat_candidates=("event_lat", "event_latitude", "source_lat", "source_latitude", "evla"),
        )
        if label:
            labels.append(label)
        out, label = _apply_category_subset(
            out,
            column=self.station_corridor_col,
            values=self.station_corridors,
            relation=self.station_corridor_relation,
            subject="Stations",
            kind="corridor",
        )
        if label:
            labels.append(label)
        out, label = _apply_category_subset(
            out,
            column=self.event_corridor_col,
            values=self.event_corridors,
            relation=self.event_corridor_relation,
            subject="Events",
            kind="corridor",
        )
        if label:
            labels.append(label)
        if require_match and not df.empty and out.empty:
            label_text = self.label or "; ".join(labels) or "configured spatial subset"
            raise ValueError(f"No rows matched {label_text}. Check that the selected regions/corridors/bounds overlap the input data.")
        return out.reset_index(drop=True), self.label or "; ".join(labels) or None


def apply_figure_spatial_selection(
    df: pd.DataFrame,
    spatial_selection: FigureSpatialSelection | dict[str, Any] | None = None,
    *,
    require_match: bool = True,
    **kwargs: Any,
) -> tuple[pd.DataFrame, str | None]:
    """Apply optional station/event region, bounds, or corridor filtering.

    Parameters
    ----------
    df
        Input table.
    spatial_selection
        Selector object or dictionary.
    require_match
        Whether an active selector should raise when it removes every row.
    **kwargs
        Selector fields accepted by :class:`FigureSpatialSelection`.

    Returns
    -------
    tuple[pandas.DataFrame, str or None]
        Filtered dataframe and readable subset label.
    """

    selector = FigureSpatialSelection.from_inputs(spatial_selection, **kwargs)
    if selector is None:
        return df.copy(), None
    return selector.apply(df, require_match=require_match)


def filter_by_bands(df: pd.DataFrame, bands: Iterable[object], *, band_cols: tuple[str, ...] = ("band", "passband", "dominant_band_label")) -> pd.DataFrame:
    """Filter a dataframe by any supported band/passband column.

    Parameters
    ----------
    df
        Input table.
    bands
        Raw band tokens or labels to keep.
    band_cols
        Candidate band columns.

    Returns
    -------
    pandas.DataFrame
        Filtered table when a band column exists; otherwise the original rows.
    """

    requested = {str(item) for item in bands}
    requested_labels = {band_display_label(item) for item in requested}
    if not requested:
        return df.copy()
    available = [column for column in band_cols if column in df.columns]
    if not available:
        return df.copy()
    mask = pd.Series(False, index=df.index)
    for column in available:
        values = df[column].astype(str)
        labels = values.map(band_display_label)
        mask = mask | values.isin(requested) | labels.isin(requested_labels)
    return df.loc[mask].copy()


def configured_band_options(
    config: SpatialVTKConfig | str | Path | None = None,
    *,
    command: str = "visualize",
    fallback_df: pd.DataFrame | None = None,
) -> list[str]:
    """Return configured passband tokens with dataframe-detected fallback.

    Parameters
    ----------
    config
        Config object, config path, or ``None``.
    command
        Dotted command used to merge run defaults.
    fallback_df
        Optional table used when no passbands are configured.

    Returns
    -------
    list[str]
        Raw passband tokens sorted by display label.
    """

    selection = FigureSelection.from_config(config, command=command)
    if selection.passbands:
        return sorted(selection.passbands, key=band_display_label)
    if fallback_df is None:
        return []
    for column in ("band", "passband", "dominant_band_label"):
        if column in fallback_df.columns:
            return sorted(fallback_df[column].dropna().astype(str).unique().tolist(), key=band_display_label)
    return []


def _coerce_config(config: SpatialVTKConfig | str | Path | None) -> SpatialVTKConfig | None:
    """Return a config object or ``None`` from an optional config input."""

    if config is None:
        return None
    if isinstance(config, SpatialVTKConfig):
        return config
    return SpatialVTKConfig.from_file(config)


def _as_tuple(value: object) -> tuple[str, ...]:
    """Normalize a scalar or sequence into a string tuple."""

    if value in (None, ""):
        return ()
    if isinstance(value, str):
        return tuple(part for part in re.split(r"[\s,]+", value.strip()) if part)
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value if item not in (None, ""))
    return (str(value),)


def _passband_tokens(value: object) -> tuple[str, ...]:
    """Normalize config passband values into displayable raw tokens."""

    tokens: list[str] = []
    for item in _as_tuple_or_items(value):
        if isinstance(item, (list, tuple)) and len(item) == 2:
            tokens.append(f"{_format_period(item[0])}-{_format_period(item[1])}s")
        else:
            tokens.append(str(item))
    return tuple(dict.fromkeys(token for token in tokens if token.strip()))


def _as_tuple_or_items(value: object) -> tuple[object, ...]:
    """Normalize passband config while preserving nested numeric pairs."""

    if value in (None, ""):
        return ()
    if isinstance(value, str):
        return tuple(part for part in re.split(r"[\s,]+", value.strip()) if part)
    if isinstance(value, (list, tuple, set)):
        return tuple(item for item in value if item not in (None, ""))
    return (value,)


def _format_period(value: object) -> str:
    """Format one period value for a compact passband token."""

    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:g}"


def _coerce_bounds(value: object) -> tuple[float, float, float, float] | None:
    """Coerce explicit bounds when no config object is available."""

    if value in (None, "", "none"):
        return None
    if isinstance(value, str):
        return None
    raw = list(value) if isinstance(value, (list, tuple)) else []
    if len(raw) != 4:
        return None
    return tuple(float(item) for item in raw)  # type: ignore[return-value]


def _normalize_spatial_relation(value: object) -> SpatialRelation:
    """Normalize a spatial relation token."""

    text = str(value or "inside").strip().lower().replace("_", "-")
    if text in {"inside", "in", "within", "include"}:
        return "inside"
    if text in {"outside", "out", "without", "exclude"}:
        return "outside"
    if text in {"both", "all", "either", "any"}:
        return "both"
    raise ValueError("Spatial relation must be 'inside', 'outside', or 'both'.")


def _apply_category_subset(
    df: pd.DataFrame,
    *,
    column: str | None,
    values: tuple[str, ...],
    relation: SpatialRelation,
    subject: str,
    kind: str,
) -> tuple[pd.DataFrame, str | None]:
    """Apply a categorical region/corridor subset and return a label."""

    if not column:
        return df, None
    if column not in df.columns:
        raise KeyError(f"Missing {kind} selection column {column!r}. Available columns: {', '.join(map(str, df.columns))}")
    mask = _category_membership_mask(df[column], values)
    label = _category_subset_label(subject, kind, values, relation)
    if relation == "both":
        return df.copy(), label
    if relation == "outside":
        mask = ~mask
    return df.loc[mask].copy(), label


def _category_membership_mask(series: pd.Series, values: tuple[str, ...] | Iterable[object] | object) -> pd.Series:
    """Return rows with matching labels or truthy labels when no values given."""

    text = series.astype(str).str.strip()
    invalid = {"", "nan", "none", "false", "0", "[]", "{}"}
    if values is None or (isinstance(values, str) and values == ""):
        normalized_values: tuple[str, ...] = ()
    elif isinstance(values, pd.Series):
        normalized_values = tuple(str(value) for value in values.dropna().tolist() if str(value).strip())
    elif isinstance(values, (list, tuple, set)):
        normalized_values = tuple(str(value) for value in values if value not in (None, "") and str(value).strip())
    else:
        normalized_values = (str(values),)
    if not normalized_values:
        return ~text.str.lower().isin(invalid)
    requested = {str(value).strip().lower() for value in normalized_values}

    def contains_requested(value: object) -> bool:
        parts = re.split(r"[;,|]", str(value))
        normalized = {part.strip().lower() for part in parts if part.strip()}
        return bool(normalized & requested)

    return series.map(contains_requested)


def _category_subset_label(subject: str, kind: str, values: tuple[str, ...], relation: SpatialRelation) -> str:
    """Return a readable category subset label."""

    target = _join_labels(values) if values else f"selected {kind}s"
    if relation == "inside":
        return f"{subject} in {target}"
    if relation == "outside":
        return f"{subject} outside {target}"
    return f"{subject} in or outside {target}"


def _apply_bounds_subset(
    df: pd.DataFrame,
    *,
    bounds: tuple[float, float, float, float] | None,
    relation: SpatialRelation,
    subject: str,
    lon_candidates: tuple[str, ...],
    lat_candidates: tuple[str, ...],
) -> tuple[pd.DataFrame, str | None]:
    """Apply a coordinate bounds subset and return a label."""

    if bounds is None:
        return df, None
    lon_col = next((column for column in lon_candidates if column in df.columns), None)
    lat_col = next((column for column in lat_candidates if column in df.columns), None)
    if lon_col is None or lat_col is None:
        raise KeyError(f"Could not apply {subject.lower()} bounds; missing coordinate columns from {lon_candidates} / {lat_candidates}.")
    west, east, south, north = bounds
    lon = pd.to_numeric(df[lon_col], errors="coerce")
    lat = pd.to_numeric(df[lat_col], errors="coerce")
    mask = lon.between(float(west), float(east), inclusive="both") & lat.between(float(south), float(north), inclusive="both")
    label = _bounds_subset_label(subject, relation)
    if relation == "both":
        return df.copy(), label
    if relation == "outside":
        mask = ~mask
    return df.loc[mask].copy(), label


def _bounds_subset_label(subject: str, relation: SpatialRelation) -> str:
    """Return a compact bounds subset label."""

    if relation == "inside":
        return f"{subject} inside configured bounds"
    if relation == "outside":
        return f"{subject} outside configured bounds"
    return f"{subject} inside or outside configured bounds"


def _join_labels(values: tuple[str, ...]) -> str:
    """Join labels for a short figure-context phrase."""

    labels = [str(value) for value in values if str(value).strip()]
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


__all__ = [
    "FigureSelection",
    "FigureSpatialSelection",
    "SpatialRelation",
    "apply_figure_spatial_selection",
    "configured_band_options",
    "filter_by_bands",
]
