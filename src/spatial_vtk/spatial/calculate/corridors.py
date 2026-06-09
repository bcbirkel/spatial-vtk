"""Clear public wrappers for GeoJSON polygon-edge corridor calculations."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import math

import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point, Polygon

from spatial_vtk.spatial.calculate.geojson import GeoJSONNoOverlapError, select_geojson_polygons
from spatial_vtk.spatial.calculate.polygon_edges import (
    PolygonFeature,
    StationEdgeSelection,
    _average_tangent_near_anchor,
    _inward_normal,
    _local_shell,
    _nearest_segment_tangent,
    event_rows_in_corridor,
    inverse_project_point,
    load_polygon_features,
    project_point,
    safe_name_token,
    select_near_edge_stations,
)


@dataclass(frozen=True)
class PolygonCorridorConfig:
    """Configuration for station-normal polygon-edge corridors.

    Parameters
    ----------
    selector
        Polygon selector: ``"all"``, one name/token, a set of names/tokens, or
        a property-filter mapping.
    near_edge_fraction, near_edge_width_km
        Station edge qualification. Use a fixed width in kilometers when
        supplied; otherwise a fraction of local polygon width is used.
    corridor_length_km, corridor_width_km
        Rectangle corridor dimensions. Triangle corridors use length only.
    edge_average_window_km
        Boundary window used to estimate tangent/normal direction.
    corridor_shape
        ``"rectangle"`` or ``"triangle"``.
    corridor_half_angle_deg
        Triangle half-angle in degrees.
    require_overlap
        Raise a clear error if selected polygons do not yield any corridor
        selections for the station table.
    """

    selector: object = "all"
    near_edge_fraction: float = 0.10
    near_edge_width_km: float | None = None
    corridor_length_km: float = 30.0
    corridor_width_km: float = 10.0
    edge_average_window_km: float = 10.0
    corridor_shape: str = "rectangle"
    corridor_half_angle_deg: float = 30.0
    require_overlap: bool = True


@dataclass(frozen=True)
class CorridorAnchorConfig:
    """Configuration for choosing where polygon-boundary corridors are placed.

    Parameters
    ----------
    source
        ``"all_boundary_segments"``, ``"station"``, ``"event"``, or
        ``"coordinate"``.
    strategy
        Anchor strategy for station/event sources. Supported values are
        ``"all"``, ``"id"``, ``"query"``, ``"max"``, ``"min"``,
        ``"max_records"``, and ``"largest_magnitude"``.
    id_value
        One ID or list of IDs for ``strategy="id"``.
    query
        Pandas query expression for ``strategy="query"``.
    sort_column
        Metadata column used for ``"max"`` and ``"min"``.
    top_n
        Number of station/event anchors to keep after ranking.
    lon, lat
        Coordinate anchor for ``source="coordinate"``.
    segment_spacing_km
        Boundary-center spacing for ``source="all_boundary_segments"``.

    Returns
    -------
    CorridorAnchorConfig
        Immutable anchor-selection settings.
    """

    source: str = "all_boundary_segments"
    strategy: str = "all"
    id_value: str | list[str] | tuple[str, ...] | None = None
    query: str | None = None
    sort_column: str | None = None
    top_n: int | None = None
    lon: float | None = None
    lat: float | None = None
    segment_spacing_km: float | None = None


@dataclass(frozen=True)
class BoundaryCorridorConfig:
    """Configuration for parameterized polygon-boundary corridors.

    Parameters
    ----------
    selector
        Polygon selector: ``"all"``, one name/token, a set of names/tokens, or
        a property-filter mapping.
    mode
        ``"inward"``, ``"outward"``, or ``"through_boundary"``.
    along_boundary_width_km
        Corridor width parallel to the polygon boundary.
    inside_length_km, outside_length_km
        Corridor lengths normal to the boundary. ``mode`` controls which side
        is used unless both are intentionally supplied.
    edge_average_window_km
        Boundary window used to estimate tangent/normal direction.
    anchor
        Boundary anchor-selection settings.
    require_overlap
        Raise when no corridors can be created for the requested polygons.

    Returns
    -------
    BoundaryCorridorConfig
        Immutable corridor-geometry settings.
    """

    selector: object = "all"
    mode: str = "through_boundary"
    along_boundary_width_km: float = 10.0
    inside_length_km: float = 15.0
    outside_length_km: float = 15.0
    edge_average_window_km: float = 10.0
    anchor: CorridorAnchorConfig = field(default_factory=CorridorAnchorConfig)
    require_overlap: bool = True


@dataclass(frozen=True)
class CorridorSelectionConfig:
    """Configuration for selecting station/event/path rows by corridors.

    Parameters
    ----------
    station_filter, event_filter
        ``"any"``, ``"inside_corridor"``, or ``"outside_corridor"``.
    side_filter
        ``"any"``, ``"opposite_polygon_sides"``, or
        ``"same_polygon_side"`` using station/event position relative to the
        source polygon.
    path_filter
        ``"any"`` or ``"passes_through_corridor"``.
    min_path_length_km
        Minimum path length through the corridor. Set to ``0`` to accept any
        intersection.
    min_path_fraction
        Minimum fraction of the corridor's longest approximate crossing.
        Set to ``0`` to accept any intersection.

    Returns
    -------
    CorridorSelectionConfig
        Immutable row-selection settings.
    """

    station_filter: str = "any"
    event_filter: str = "any"
    side_filter: str = "any"
    path_filter: str = "any"
    min_path_length_km: float = 0.0
    min_path_fraction: float = 0.0


def build_station_edge_corridors(
    station_df: pd.DataFrame,
    geojson_path: str | Path,
    *,
    config: PolygonCorridorConfig | None = None,
    station_col: str = "station",
    network_col: str = "network",
    lon_col: str | None = None,
    lat_col: str | None = None,
) -> pd.DataFrame:
    """Build station-specific corridors normal to selected polygon edges.

    Parameters
    ----------
    station_df
        Station table with station coordinates.
    geojson_path
        Polygon GeoJSON path.
    config
        Corridor configuration.
    station_col, network_col
        Station and network columns.
    lon_col, lat_col
        Optional coordinate columns. Common station coordinate names are
        inferred when omitted.

    Returns
    -------
    pandas.DataFrame
        Corridor table with station, polygon, edge, anchor, and geometry
        columns. The ``corridor_geometry`` column contains Shapely polygons.
    """

    cfg = config or PolygonCorridorConfig()
    features = select_geojson_polygons(load_polygon_features(geojson_path), cfg.selector)
    stations = _normalize_station_table(station_df, station_col=station_col, network_col=network_col, lon_col=lon_col, lat_col=lat_col)

    rows: list[dict[str, object]] = []
    for feature in features:
        selections = select_near_edge_stations(
            feature,
            stations,
            near_edge_fraction=cfg.near_edge_fraction,
            near_edge_width_km=cfg.near_edge_width_km,
            corridor_length_km=cfg.corridor_length_km,
            corridor_thickness_km=cfg.corridor_width_km,
            edge_average_window_km=cfg.edge_average_window_km,
            corridor_shape=cfg.corridor_shape,
            corridor_half_angle_deg=cfg.corridor_half_angle_deg,
        )
        rows.extend(_selection_to_row(selection) for selection in selections)

    if cfg.require_overlap and not rows:
        raise GeoJSONNoOverlapError(
            f"No stations qualified for polygon-edge corridors using GeoJSON {geojson_path}. "
            "Check station coordinates, selector, and near-edge thresholds."
        )
    return pd.DataFrame(rows)


def build_boundary_corridors(
    geojson_path: str | Path,
    *,
    config: BoundaryCorridorConfig | None = None,
    station_df: pd.DataFrame | None = None,
    event_df: pd.DataFrame | None = None,
    records_df: pd.DataFrame | None = None,
    station_col: str = "station",
    event_col: str = "event_id",
) -> pd.DataFrame:
    """Build parameterized corridors anchored to selected polygon boundaries.

    Parameters
    ----------
    geojson_path
        Polygon GeoJSON path.
    config
        Boundary-corridor configuration.
    station_df, event_df
        Optional station/event metadata used by station/event anchor strategies.
    records_df
        Optional event-station record table used for ``max_records`` anchors.
    station_col, event_col
        Station and event ID columns in the input tables.

    Returns
    -------
    pandas.DataFrame
        Corridor table with polygon, anchor, dimensions, and Shapely geometry
        columns. ``corridor_geometry`` is in lon/lat.
    """

    cfg = config or BoundaryCorridorConfig()
    _validate_boundary_corridor_config(cfg)
    features = select_geojson_polygons(load_polygon_features(geojson_path), cfg.selector)
    station_norm = None if station_df is None else _normalize_station_table(station_df, station_col=station_col, network_col="network", lon_col=None, lat_col=None)
    event_norm = None if event_df is None else _normalize_event_table(event_df, event_col=event_col, lon_col=None, lat_col=None)

    rows: list[dict[str, object]] = []
    for feature in features:
        for shell_index, _shell in enumerate(feature.shells):
            local_shell = _local_shell(feature, shell_index)
            anchors = _resolve_corridor_anchors(
                feature,
                local_shell,
                cfg,
                station_df=station_norm,
                event_df=event_norm,
                records_df=records_df,
                station_col="station",
                event_col="event_id",
            )
            for anchor_index, anchor in enumerate(anchors):
                corridor = _corridor_from_anchor(feature, local_shell, cfg, anchor=anchor, anchor_index=anchor_index)
                if corridor is not None:
                    rows.append(corridor)

    if cfg.require_overlap and not rows:
        raise GeoJSONNoOverlapError(
            f"No corridors could be built from GeoJSON {geojson_path}. "
            "Check polygon selector, anchor settings, and corridor dimensions."
        )
    return pd.DataFrame(rows)


def classify_records_by_corridors(
    records_df: pd.DataFrame,
    corridors_df: pd.DataFrame,
    *,
    config: CorridorSelectionConfig | None = None,
    station_lon_col: str | None = None,
    station_lat_col: str | None = None,
    event_lon_col: str | None = None,
    event_lat_col: str | None = None,
) -> pd.DataFrame:
    """Classify event-station path rows against corridor footprints.

    Parameters
    ----------
    records_df
        Event-station table with station and event coordinates.
    corridors_df
        Corridor table from :func:`build_boundary_corridors` or
        :func:`build_station_edge_corridors`.
    config
        Selection rules. Defaults keep any row/corridor pair.
    station_lon_col, station_lat_col, event_lon_col, event_lat_col
        Optional coordinate column overrides.

    Returns
    -------
    pandas.DataFrame
        One row per matching input row/corridor pair, with corridor metadata,
        point-membership flags, polygon-side flags, and path-through-corridor
        length.
    """

    cfg = config or CorridorSelectionConfig()
    if records_df.empty or corridors_df.empty:
        return pd.DataFrame()
    station_lon, station_lat = _resolve_pair_columns(
        records_df,
        station_lon_col,
        station_lat_col,
        lon_candidates=["station_lon", "station_longitude", "sta_lon", "lon", "longitude"],
        lat_candidates=["station_lat", "station_latitude", "sta_lat", "lat", "latitude"],
        label="station",
    )
    event_lon, event_lat = _resolve_pair_columns(
        records_df,
        event_lon_col,
        event_lat_col,
        lon_candidates=["event_lon", "event_longitude", "source_lon", "source_longitude"],
        lat_candidates=["event_lat", "event_latitude", "source_lat", "source_latitude"],
        label="event",
    )

    rows: list[dict[str, object]] = []
    for corridor in corridors_df.itertuples(index=False):
        corridor_geom = getattr(corridor, "corridor_geometry", None)
        polygon_geom = getattr(corridor, "polygon_geometry", None)
        if corridor_geom is None:
            continue
        for index, record in records_df.iterrows():
            station_point = Point(float(record[station_lon]), float(record[station_lat]))
            event_point = Point(float(record[event_lon]), float(record[event_lat]))
            station_in_corridor = bool(corridor_geom.contains(station_point) or corridor_geom.touches(station_point))
            event_in_corridor = bool(corridor_geom.contains(event_point) or corridor_geom.touches(event_point))
            station_inside_polygon = _point_inside_geometry(station_point, polygon_geom)
            event_inside_polygon = _point_inside_geometry(event_point, polygon_geom)
            path_line = LineString([(float(record[event_lon]), float(record[event_lat])), (float(record[station_lon]), float(record[station_lat]))])
            path_intersects = bool(path_line.intersects(corridor_geom))
            length_km = _geometry_length_km(path_line.intersection(corridor_geom))
            max_length = float(getattr(corridor, "corridor_max_path_length_km", np.nan))
            fraction = length_km / max_length if np.isfinite(max_length) and max_length > 0.0 else np.nan
            if not _record_matches_corridor_selection(
                cfg,
                station_in_corridor=station_in_corridor,
                event_in_corridor=event_in_corridor,
                station_inside_polygon=station_inside_polygon,
                event_inside_polygon=event_inside_polygon,
                path_intersects=path_intersects,
                path_length_km=length_km,
                path_fraction=fraction,
            ):
                continue
            out = record.to_dict()
            out.update(_corridor_metadata(corridor))
            out.update(
                {
                    "record_index": index,
                    "station_in_corridor": station_in_corridor,
                    "event_in_corridor": event_in_corridor,
                    "station_inside_polygon": station_inside_polygon,
                    "event_inside_polygon": event_inside_polygon,
                    "path_length_in_corridor_km": length_km,
                    "path_fraction_in_corridor": fraction,
                    "path_passes_through_corridor": path_intersects,
                }
            )
            rows.append(out)
    return pd.DataFrame(rows)


def select_records_by_corridors(
    records_df: pd.DataFrame,
    corridors_df: pd.DataFrame,
    *,
    config: CorridorSelectionConfig | None = None,
    station_lon_col: str | None = None,
    station_lat_col: str | None = None,
    event_lon_col: str | None = None,
    event_lat_col: str | None = None,
) -> pd.DataFrame:
    """Return event-station rows that match corridor selection rules.

    Parameters
    ----------
    records_df
        Event-station table.
    corridors_df
        Corridor table.
    config
        Corridor selection settings.
    station_lon_col, station_lat_col, event_lon_col, event_lat_col
        Optional coordinate column overrides.

    Returns
    -------
    pandas.DataFrame
        Matching row/corridor pairs.
    """

    return classify_records_by_corridors(
        records_df,
        corridors_df,
        config=config,
        station_lon_col=station_lon_col,
        station_lat_col=station_lat_col,
        event_lon_col=event_lon_col,
        event_lat_col=event_lat_col,
    )


def select_events_in_corridors(
    events_df: pd.DataFrame,
    corridors_df: pd.DataFrame,
    *,
    event_col: str = "event_id",
    lon_col: str | None = None,
    lat_col: str | None = None,
    min_depth_km: float | None = None,
    max_depth_km: float | None = None,
) -> pd.DataFrame:
    """Select event rows inside each corridor footprint.

    Parameters
    ----------
    events_df
        Event table.
    corridors_df
        Corridor table from :func:`build_station_edge_corridors`.
    event_col
        Event identifier column.
    lon_col, lat_col
        Optional event coordinate columns. Common event coordinate names are
        inferred when omitted.
    min_depth_km, max_depth_km
        Optional inclusive depth filters.

    Returns
    -------
    pandas.DataFrame
        Matching event-corridor rows.
    """

    if corridors_df.empty:
        return pd.DataFrame()
    events = _normalize_event_table(events_df, event_col=event_col, lon_col=lon_col, lat_col=lat_col)
    rows: list[dict[str, object]] = []
    for corridor in corridors_df.itertuples(index=False):
        geometry = getattr(corridor, "corridor_geometry", None)
        if geometry is None:
            continue
        matches = event_rows_in_corridor(events, geometry, min_depth_km=min_depth_km, max_depth_km=max_depth_km)
        for _, event_row in matches.iterrows():
            row = {
                "polygon_name": getattr(corridor, "polygon_name"),
                "polygon_safe_name": getattr(corridor, "polygon_safe_name"),
                "station": getattr(corridor, "station"),
                "network": getattr(corridor, "network"),
                "station_side": getattr(corridor, "station_side"),
                "corridor_shape": getattr(corridor, "corridor_shape"),
                "distance_to_edge_km": getattr(corridor, "distance_to_edge_km"),
                "corridor_length_km": getattr(corridor, "corridor_length_km"),
                "corridor_width_km": getattr(corridor, "corridor_width_km"),
            }
            row.update(event_row.to_dict())
            rows.append(row)
    return pd.DataFrame(rows)


def summarize_corridor_event_counts(corridor_events: pd.DataFrame) -> pd.DataFrame:
    """Summarize how many events fall in each station/polygon corridor."""

    if corridor_events.empty:
        return pd.DataFrame(columns=["polygon_name", "station", "event_count"])
    return (
        corridor_events.groupby(["polygon_name", "polygon_safe_name", "station", "network", "station_side"], dropna=False)
        .agg(event_count=("event_id", "nunique"))
        .reset_index()
        .sort_values(["polygon_name", "station"])
        .reset_index(drop=True)
    )


def _validate_boundary_corridor_config(config: BoundaryCorridorConfig) -> None:
    """Validate public boundary-corridor configuration values.

    Parameters
    ----------
    config
        Boundary-corridor settings.

    Returns
    -------
    None
        Raises ``ValueError`` if settings are inconsistent.
    """

    mode = str(config.mode).strip().lower()
    if mode not in {"inward", "outward", "through_boundary"}:
        raise ValueError("Boundary corridor mode must be 'inward', 'outward', or 'through_boundary'.")
    if float(config.along_boundary_width_km) <= 0.0:
        raise ValueError("along_boundary_width_km must be positive.")
    inside_km, outside_km = _effective_corridor_lengths(config)
    if inside_km + outside_km <= 0.0:
        raise ValueError("Corridor normal length must be positive on at least one side of the boundary.")


def _effective_corridor_lengths(config: BoundaryCorridorConfig) -> tuple[float, float]:
    """Return effective inward and outward corridor lengths in kilometers.

    Parameters
    ----------
    config
        Boundary-corridor settings.

    Returns
    -------
    tuple[float, float]
        ``(inside_length_km, outside_length_km)`` after applying mode.
    """

    mode = str(config.mode).strip().lower()
    inside = max(0.0, float(config.inside_length_km))
    outside = max(0.0, float(config.outside_length_km))
    if mode == "inward":
        return inside, 0.0
    if mode == "outward":
        return 0.0, outside
    return inside, outside


def _resolve_corridor_anchors(
    feature: PolygonFeature,
    local_shell: object,
    config: BoundaryCorridorConfig,
    *,
    station_df: pd.DataFrame | None,
    event_df: pd.DataFrame | None,
    records_df: pd.DataFrame | None,
    station_col: str,
    event_col: str,
) -> list[dict[str, object]]:
    """Resolve anchor points for one polygon shell.

    Parameters
    ----------
    feature, local_shell
        Polygon feature and projected shell context.
    config
        Boundary-corridor settings.
    station_df, event_df, records_df
        Optional input tables used for metadata-selected anchors.
    station_col, event_col
        Identifier columns for station/event inputs.

    Returns
    -------
    list[dict[str, object]]
        Anchor dictionaries with projected boundary points and labels.
    """

    source = str(config.anchor.source).strip().lower()
    if source == "all_boundary_segments":
        return _all_boundary_segment_anchors(feature, local_shell, config)
    if source == "coordinate":
        if config.anchor.lon is None or config.anchor.lat is None:
            raise ValueError("Coordinate anchors require anchor.lon and anchor.lat.")
        point = project_point(local_shell, float(config.anchor.lon), float(config.anchor.lat))
        return [_nearest_boundary_anchor(feature, local_shell, point, label="coordinate", source="coordinate")]
    if source == "station":
        if station_df is None:
            raise ValueError("Station anchors require station_df.")
        rows = _select_anchor_rows(station_df, config.anchor, id_col=station_col, records_df=records_df, records_id_col=station_col)
        return [
            _nearest_boundary_anchor(feature, local_shell, project_point(local_shell, row.station_lon, row.station_lat), label=str(row.station), source="station")
            for row in rows.itertuples(index=False)
        ]
    if source == "event":
        if event_df is None:
            raise ValueError("Event anchors require event_df.")
        rows = _select_anchor_rows(event_df, config.anchor, id_col=event_col, records_df=records_df, records_id_col=event_col)
        return [
            _nearest_boundary_anchor(feature, local_shell, project_point(local_shell, row.event_lon, row.event_lat), label=str(row.event_id), source="event")
            for row in rows.itertuples(index=False)
        ]
    raise ValueError("Corridor anchor source must be 'all_boundary_segments', 'station', 'event', or 'coordinate'.")


def _all_boundary_segment_anchors(feature: PolygonFeature, local_shell: object, config: BoundaryCorridorConfig) -> list[dict[str, object]]:
    """Create regularly spaced anchors around a polygon boundary.

    Parameters
    ----------
    feature, local_shell
        Polygon feature and projected shell context.
    config
        Boundary-corridor settings.

    Returns
    -------
    list[dict[str, object]]
        Anchor dictionaries centered on boundary segments.
    """

    line = local_shell.exterior_line_projected
    total_m = float(line.length)
    if not np.isfinite(total_m) or total_m <= 0.0:
        return []
    spacing_km = config.anchor.segment_spacing_km or config.along_boundary_width_km
    spacing_m = max(1.0, float(spacing_km) * 1000.0)
    count = max(1, int(math.ceil(total_m / spacing_m)))
    step_m = total_m / count
    anchors = []
    for index in range(count):
        distance_m = min(total_m, (index + 0.5) * step_m)
        point = line.interpolate(distance_m)
        anchors.append(_nearest_boundary_anchor(feature, local_shell, point, label=f"segment_{index + 1:03d}", source="all_boundary_segments"))
    return anchors


def _nearest_boundary_anchor(feature: PolygonFeature, local_shell: object, point: Point, *, label: str, source: str) -> dict[str, object]:
    """Build one nearest-boundary anchor from a projected point.

    Parameters
    ----------
    feature, local_shell
        Polygon feature and projected shell context.
    point
        Projected source point.
    label, source
        Anchor label and source type.

    Returns
    -------
    dict[str, object]
        Anchor metadata and projected boundary geometry.
    """

    nearest = _nearest_segment_tangent(local_shell, point)
    if nearest is None:
        raise ValueError(f"Could not determine boundary tangent for {feature.name!r}.")
    anchor_point, tangent = nearest
    return {"anchor_point": anchor_point, "tangent": tangent, "anchor_label": label, "anchor_source": source}


def _select_anchor_rows(
    df: pd.DataFrame,
    anchor: CorridorAnchorConfig,
    *,
    id_col: str,
    records_df: pd.DataFrame | None,
    records_id_col: str,
) -> pd.DataFrame:
    """Select station/event rows for metadata-driven anchors.

    Parameters
    ----------
    df
        Normalized station or event table.
    anchor
        Anchor-selection settings.
    id_col
        Identifier column in ``df``.
    records_df, records_id_col
        Optional record table and matching identifier column for
        ``max_records``.

    Returns
    -------
    pandas.DataFrame
        Selected anchor rows.
    """

    strategy = str(anchor.strategy).strip().lower()
    work = df.copy()
    if strategy == "all":
        selected = work
    elif strategy == "id":
        values = anchor.id_value if isinstance(anchor.id_value, (list, tuple, set)) else [anchor.id_value]
        selected = work[work[id_col].astype(str).isin({str(value) for value in values if value is not None})]
    elif strategy == "query":
        if not anchor.query:
            raise ValueError("Anchor strategy 'query' requires anchor.query.")
        selected = work.query(anchor.query).copy()
    elif strategy in {"max", "min"}:
        if not anchor.sort_column or anchor.sort_column not in work.columns:
            raise ValueError("Anchor strategy 'max'/'min' requires a valid anchor.sort_column.")
        selected = work.sort_values(anchor.sort_column, ascending=(strategy == "min"))
    elif strategy == "largest_magnitude":
        mag_col = anchor.sort_column or next((column for column in ["magnitude", "event_magnitude", "mag"] if column in work.columns), None)
        if mag_col is None:
            raise ValueError("largest_magnitude anchors require a magnitude column or anchor.sort_column.")
        selected = work.assign(_svtk_sort=pd.to_numeric(work[mag_col], errors="coerce")).sort_values("_svtk_sort", ascending=False)
    elif strategy == "max_records":
        if records_df is None or records_id_col not in records_df.columns:
            raise ValueError("max_records anchors require records_df with the requested ID column.")
        counts = records_df[records_id_col].astype(str).value_counts().rename("_svtk_record_count")
        selected = work.assign(_svtk_record_count=work[id_col].astype(str).map(counts).fillna(0)).sort_values("_svtk_record_count", ascending=False)
    else:
        raise ValueError("Unsupported anchor strategy. Use all, id, query, max, min, max_records, or largest_magnitude.")

    if anchor.top_n is not None:
        selected = selected.head(int(anchor.top_n))
    if selected.empty:
        raise GeoJSONNoOverlapError("No station/event rows matched the requested corridor anchor strategy.")
    return selected


def _corridor_from_anchor(
    feature: PolygonFeature,
    local_shell: object,
    config: BoundaryCorridorConfig,
    *,
    anchor: dict[str, object],
    anchor_index: int,
) -> dict[str, object] | None:
    """Build one corridor polygon from a boundary anchor.

    Parameters
    ----------
    feature, local_shell
        Polygon feature and projected shell context.
    config
        Boundary-corridor settings.
    anchor
        Anchor metadata.
    anchor_index
        Zero-based anchor index within the shell.

    Returns
    -------
    dict[str, object] or None
        Corridor row, or ``None`` when normal direction cannot be resolved.
    """

    anchor_point = anchor["anchor_point"]
    tangent = _average_tangent_near_anchor(
        local_shell,
        anchor_point,
        window_km=config.edge_average_window_km,
        fallback=anchor["tangent"],
    )
    if tangent is None:
        return None
    inward = _inward_normal(local_shell, anchor_point, tangent)
    if inward is None:
        return None
    inside_km, outside_km = _effective_corridor_lengths(config)
    polygon = _build_boundary_corridor_polygon(
        local_shell,
        anchor=anchor_point,
        tangent=tangent,
        inward_normal=inward,
        along_boundary_width_km=config.along_boundary_width_km,
        inside_length_km=inside_km,
        outside_length_km=outside_km,
    )
    anchor_lon, anchor_lat = inverse_project_point(local_shell, anchor_point.x, anchor_point.y)
    return {
        "polygon_name": feature.name,
        "polygon_safe_name": safe_name_token(feature.name),
        "polygon_geometry": feature.geometry,
        "shell_index": local_shell.shell_index,
        "anchor_source": anchor["anchor_source"],
        "anchor_label": anchor["anchor_label"],
        "anchor_index": int(anchor_index),
        "anchor_lon": anchor_lon,
        "anchor_lat": anchor_lat,
        "corridor_mode": str(config.mode).strip().lower(),
        "along_boundary_width_km": float(config.along_boundary_width_km),
        "inside_length_km": inside_km,
        "outside_length_km": outside_km,
        "corridor_max_path_length_km": math.hypot(float(config.along_boundary_width_km), inside_km + outside_km),
        "edge_average_window_km": float(config.edge_average_window_km),
        "corridor_geometry": polygon,
        "tangent_x": float(tangent[0]),
        "tangent_y": float(tangent[1]),
        "inward_normal_x": float(inward[0]),
        "inward_normal_y": float(inward[1]),
    }


def _build_boundary_corridor_polygon(
    local_shell: object,
    *,
    anchor: Point,
    tangent: tuple[float, float],
    inward_normal: tuple[float, float],
    along_boundary_width_km: float,
    inside_length_km: float,
    outside_length_km: float,
) -> Polygon:
    """Build a boundary-normal rectangular corridor polygon in lon/lat.

    Parameters
    ----------
    local_shell
        Projected shell context.
    anchor
        Projected boundary anchor point.
    tangent, inward_normal
        Unit tangent and inward-normal vectors.
    along_boundary_width_km
        Corridor width parallel to the boundary.
    inside_length_km, outside_length_km
        Corridor extents normal to the boundary.

    Returns
    -------
    shapely.geometry.Polygon
        Corridor footprint in longitude/latitude.
    """

    anchor_vec = np.asarray((anchor.x, anchor.y), dtype=float)
    tangent_vec = np.asarray(tangent, dtype=float)
    normal_vec = np.asarray(inward_normal, dtype=float)
    half_width_m = float(along_boundary_width_km) * 500.0
    inside_m = float(inside_length_km) * 1000.0
    outside_m = float(outside_length_km) * 1000.0
    start_center = anchor_vec - outside_m * normal_vec
    end_center = anchor_vec + inside_m * normal_vec
    corners = [
        start_center - half_width_m * tangent_vec,
        start_center + half_width_m * tangent_vec,
        end_center + half_width_m * tangent_vec,
        end_center - half_width_m * tangent_vec,
        start_center - half_width_m * tangent_vec,
    ]
    lonlat = [inverse_project_point(local_shell, float(x), float(y)) for x, y in corners]
    return Polygon(lonlat)


def _corridor_metadata(corridor: object) -> dict[str, object]:
    """Extract scalar corridor metadata from a dataframe row object.

    Parameters
    ----------
    corridor
        Row object from a corridor dataframe.

    Returns
    -------
    dict[str, object]
        Scalar corridor metadata safe to merge with record rows.
    """

    metadata = {}
    for key in [
        "polygon_name",
        "polygon_safe_name",
        "shell_index",
        "anchor_source",
        "anchor_label",
        "anchor_index",
        "anchor_lon",
        "anchor_lat",
        "corridor_mode",
        "along_boundary_width_km",
        "inside_length_km",
        "outside_length_km",
        "corridor_max_path_length_km",
        "station",
        "network",
        "station_side",
        "corridor_shape",
    ]:
        if hasattr(corridor, key):
            metadata[key] = getattr(corridor, key)
    return metadata


def _resolve_pair_columns(
    df: pd.DataFrame,
    lon_col: str | None,
    lat_col: str | None,
    *,
    lon_candidates: list[str],
    lat_candidates: list[str],
    label: str,
) -> tuple[str, str]:
    """Resolve longitude/latitude columns for station/event paths.

    Parameters
    ----------
    df
        Input dataframe.
    lon_col, lat_col
        Optional explicit coordinate columns.
    lon_candidates, lat_candidates
        Candidate column names.
    label
        Human-readable point label for errors.

    Returns
    -------
    tuple[str, str]
        Longitude and latitude column names.
    """

    lon = lon_col or next((column for column in lon_candidates if column in df.columns), None)
    lat = lat_col or next((column for column in lat_candidates if column in df.columns), None)
    if lon is None or lat is None:
        raise KeyError(f"Could not resolve {label} longitude/latitude columns.")
    return lon, lat


def _point_inside_geometry(point: Point, geometry: object | None) -> bool:
    """Return whether a point is inside/touching one geometry.

    Parameters
    ----------
    point
        Point geometry.
    geometry
        Polygon-like geometry or ``None``.

    Returns
    -------
    bool
        ``True`` when the geometry contains or touches the point.
    """

    if geometry is None:
        return False
    return bool(geometry.contains(point) or geometry.touches(point))


def _record_matches_corridor_selection(
    config: CorridorSelectionConfig,
    *,
    station_in_corridor: bool,
    event_in_corridor: bool,
    station_inside_polygon: bool,
    event_inside_polygon: bool,
    path_intersects: bool,
    path_length_km: float,
    path_fraction: float,
) -> bool:
    """Evaluate one event-station row against corridor selection rules.

    Parameters
    ----------
    config
        Corridor selection settings.
    station_in_corridor, event_in_corridor
        Point-in-corridor flags.
    station_inside_polygon, event_inside_polygon
        Point-in-source-polygon flags.
    path_intersects, path_length_km, path_fraction
        Path intersection metrics.

    Returns
    -------
    bool
        Whether the row matches all configured filters.
    """

    if not _point_filter_matches(config.station_filter, station_in_corridor):
        return False
    if not _point_filter_matches(config.event_filter, event_in_corridor):
        return False
    side_filter = str(config.side_filter).strip().lower()
    if side_filter == "opposite_polygon_sides" and station_inside_polygon == event_inside_polygon:
        return False
    if side_filter == "same_polygon_side" and station_inside_polygon != event_inside_polygon:
        return False
    if side_filter not in {"any", "opposite_polygon_sides", "same_polygon_side"}:
        raise ValueError("side_filter must be any, opposite_polygon_sides, or same_polygon_side.")
    path_filter = str(config.path_filter).strip().lower()
    if path_filter == "passes_through_corridor":
        if not path_intersects:
            return False
        if float(path_length_km) < max(0.0, float(config.min_path_length_km)):
            return False
        if np.isfinite(path_fraction) and float(path_fraction) < max(0.0, float(config.min_path_fraction)):
            return False
        if float(path_length_km) <= 0.0 and (float(config.min_path_length_km) > 0.0 or float(config.min_path_fraction) > 0.0):
            return False
    elif path_filter != "any":
        raise ValueError("path_filter must be any or passes_through_corridor.")
    return True


def _point_filter_matches(filter_name: str, inside: bool) -> bool:
    """Evaluate one point-in-corridor filter.

    Parameters
    ----------
    filter_name
        ``"any"``, ``"inside_corridor"``, or ``"outside_corridor"``.
    inside
        Whether the point is inside/touching the corridor.

    Returns
    -------
    bool
        Whether the point filter passes.
    """

    token = str(filter_name).strip().lower()
    if token == "any":
        return True
    if token == "inside_corridor":
        return bool(inside)
    if token == "outside_corridor":
        return not bool(inside)
    raise ValueError("Point filters must be any, inside_corridor, or outside_corridor.")


def _geometry_length_km(geometry: object) -> float:
    """Approximate lon/lat geometry length in kilometers.

    Parameters
    ----------
    geometry
        Shapely line-like intersection geometry.

    Returns
    -------
    float
        Approximate path length in kilometers.
    """

    if geometry is None or geometry.is_empty:
        return 0.0
    if isinstance(geometry, LineString):
        coords = list(geometry.coords)
        return sum(_haversine_km(coords[i][1], coords[i][0], coords[i + 1][1], coords[i + 1][0]) for i in range(len(coords) - 1))
    if hasattr(geometry, "geoms"):
        return float(sum(_geometry_length_km(part) for part in geometry.geoms))
    return 0.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two lon/lat points.

    Parameters
    ----------
    lat1, lon1, lat2, lon2
        Point coordinates in decimal degrees.

    Returns
    -------
    float
        Distance in kilometers.
    """

    radius_km = 6371.0088
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return float(2.0 * radius_km * math.asin(min(1.0, math.sqrt(a))))


def _selection_to_row(selection: StationEdgeSelection) -> dict[str, object]:
    """Convert one lower-level station-edge selection to a public table row."""

    return {
        "polygon_name": selection.feature_name,
        "polygon_safe_name": safe_name_token(selection.feature_name),
        "station": selection.station,
        "network": selection.network,
        "shell_index": selection.shell_index,
        "station_lat": selection.station_lat,
        "station_lon": selection.station_lon,
        "station_side": selection.station_side,
        "anchor_lon": selection.anchor_lon,
        "anchor_lat": selection.anchor_lat,
        "local_shell_width_km": selection.local_shell_width_km,
        "near_edge_threshold_km": selection.near_edge_threshold_km,
        "distance_to_edge_km": selection.distance_to_edge_km,
        "corridor_length_km": selection.corridor_length_km,
        "corridor_width_km": selection.corridor_thickness_km,
        "edge_average_window_km": selection.edge_average_window_km,
        "corridor_shape": selection.corridor_shape,
        "corridor_half_angle_deg": selection.corridor_half_angle_deg,
        "corridor_geometry": selection.corridor_lonlat,
        "tangent_x": selection.tangent_xy[0],
        "tangent_y": selection.tangent_xy[1],
        "inward_normal_x": selection.inward_normal_xy[0],
        "inward_normal_y": selection.inward_normal_xy[1],
    }


def _normalize_station_table(
    df: pd.DataFrame,
    *,
    station_col: str,
    network_col: str,
    lon_col: str | None,
    lat_col: str | None,
) -> pd.DataFrame:
    """Normalize station table columns for the corridor geometry kernel."""

    lon_name = lon_col or next((column for column in ["station_lon", "station_longitude", "sta_lon", "lon", "longitude"] if column in df.columns), None)
    lat_name = lat_col or next((column for column in ["station_lat", "station_latitude", "sta_lat", "lat", "latitude"] if column in df.columns), None)
    if lon_name is None or lat_name is None:
        raise KeyError("Could not resolve station longitude/latitude columns.")
    out = df.copy()
    out["station"] = df[station_col] if station_col in df.columns else df.index.astype(str)
    out["network"] = df[network_col] if network_col in df.columns else "UNKNOWN"
    out["station_lon"] = pd.to_numeric(df[lon_name], errors="coerce")
    out["station_lat"] = pd.to_numeric(df[lat_name], errors="coerce")
    return out.dropna(subset=["station_lon", "station_lat"])


def _normalize_event_table(
    df: pd.DataFrame,
    *,
    event_col: str,
    lon_col: str | None,
    lat_col: str | None,
) -> pd.DataFrame:
    """Normalize event table columns for corridor event selection."""

    lon_name = lon_col or next((column for column in ["event_lon", "event_longitude", "source_lon", "source_longitude", "lon", "longitude"] if column in df.columns), None)
    lat_name = lat_col or next((column for column in ["event_lat", "event_latitude", "source_lat", "source_latitude", "lat", "latitude"] if column in df.columns), None)
    if lon_name is None or lat_name is None:
        raise KeyError("Could not resolve event longitude/latitude columns.")
    out = df.copy()
    out["event_id"] = out[event_col] if event_col in out.columns else out.index.astype(str)
    out["event_lon"] = pd.to_numeric(out[lon_name], errors="coerce")
    out["event_lat"] = pd.to_numeric(out[lat_name], errors="coerce")
    if "event_depth_km" not in out.columns:
        out["event_depth_km"] = 0.0
    return out.dropna(subset=["event_lon", "event_lat"])
