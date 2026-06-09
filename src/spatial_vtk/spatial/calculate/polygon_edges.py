"""Geometry helpers for polygon-edge station corridor sections.

Purpose
-------
This module owns the pure geometry used by the polygon-edge station-section
workflow. It loads Polygon/MultiPolygon GeoJSON features, associates stations
with the nearest *outer* shell edge, computes local shell width while ignoring
holes, builds station-specific normal corridors, and selects events inside
those corridors.

Usage examples
--------------
Load features and select near-edge stations without touching waveform files:
  ``features = load_polygon_features("inputs/geospatial/regions_updated.geojson")``
  ``matches = select_near_edge_stations(features[0], station_df)``
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
import json
import math
import warnings

import numpy as np
import pandas as pd
from pyproj import CRS, Transformer
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


FEATURE_NAME_KEYS: tuple[str, ...] = (
    "Subregion",
    "subregion",
    "Region",
    "region",
    "region_name",
    "name",
    "Name",
    "long_name",
    "region_type",
)


@dataclass(frozen=True)
class PolygonFeature:
    """One named GeoJSON polygon feature with shell components preserved.

    Parameters
    ----------
    name
        Deduplicated display name for the feature.
    geometry
        Original Shapely Polygon or MultiPolygon geometry in lon/lat.
    shells
        Individual Polygon shell components. For a Polygon this is one item;
        for a MultiPolygon this contains each component.
    properties
        Original GeoJSON feature properties.
    """

    name: str
    geometry: Polygon | MultiPolygon
    shells: tuple[Polygon, ...]
    properties: dict[str, object]


@dataclass(frozen=True)
class LocalShell:
    """Projected shell geometry and transformers for one polygon component.

    Parameters
    ----------
    feature_name
        Parent feature name.
    shell_index
        Zero-based shell component index within the feature.
    shell_lonlat
        Original shell polygon in longitude/latitude.
    shell_projected
        Projected shell polygon with holes preserved.
    shell_outer_projected
        Projected polygon made from only the exterior ring.
    exterior_line_projected
        Projected exterior ring LineString.
    to_projected
        Transformer from lon/lat to local meters.
    to_lonlat
        Transformer from local meters back to lon/lat.
    """

    feature_name: str
    shell_index: int
    shell_lonlat: Polygon
    shell_projected: Polygon
    shell_outer_projected: Polygon
    exterior_line_projected: LineString
    to_projected: Transformer
    to_lonlat: Transformer


@dataclass(frozen=True)
class StationEdgeSelection:
    """One station that qualifies as near a polygon's outer edge.

    Parameters
    ----------
    feature_name, station, network
        Identifiers for the polygon feature and station.
    shell_index
        Shell component used for nearest-edge association.
    station_lat, station_lon
        Station coordinates in decimal degrees.
    station_side
        ``"inside"`` when the station lies inside the actual polygon shell,
        otherwise ``"outside"``. A station in a hole is outside.
    anchor_lon, anchor_lat
        Nearest outer-boundary point in lon/lat.
    local_shell_width_km
        Distance from the anchor point to the opposite outer shell along the
        inward normal.
    near_edge_threshold_km
        Threshold used to accept this station.
    distance_to_edge_km
        Station-to-anchor distance.
    corridor_length_km, corridor_thickness_km
        Dimensions of the station-specific corridor. Triangle corridors use
        ``corridor_length_km`` as the side length and leave
        ``corridor_thickness_km`` as zero because they are angular wedges.
    edge_average_window_km
        Exterior-edge window used to average the tangent for normal corridors.
    corridor_shape
        Corridor footprint shape: ``"rectangle"`` or ``"triangle"``.
    corridor_half_angle_deg
        Half angle in degrees for triangle corridors.
    corridor_lonlat
        Corridor footprint polygon in lon/lat.
    tangent_xy, inward_normal_xy
        Unit vectors in local projected coordinates.
    """

    feature_name: str
    station: str
    network: str
    shell_index: int
    station_lat: float
    station_lon: float
    station_side: str
    anchor_lon: float
    anchor_lat: float
    local_shell_width_km: float
    near_edge_threshold_km: float
    distance_to_edge_km: float
    corridor_length_km: float
    corridor_thickness_km: float
    edge_average_window_km: float
    corridor_shape: str
    corridor_half_angle_deg: float
    corridor_lonlat: Polygon
    tangent_xy: tuple[float, float]
    inward_normal_xy: tuple[float, float]


def safe_name_token(value: object) -> str:
    """Return a deterministic filesystem-safe token for one label.

    Parameters
    ----------
    value
        Raw label such as a polygon or station name.

    Returns
    -------
    str
        Lowercase token containing letters, numbers, and underscores.
    """

    import re

    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unnamed"


def _feature_name(properties: dict[str, object], fallback: str) -> str:
    """Resolve one feature name from the repo-standard property priority.

    Parameters
    ----------
    properties
        GeoJSON feature properties.
    fallback
        Fallback label when no configured property is available.

    Returns
    -------
    str
        Human-readable feature name.
    """

    for key in FEATURE_NAME_KEYS:
        value = properties.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return fallback


def _dedupe_name(name: str, counts: dict[str, int]) -> str:
    """Return one deduplicated feature name with numeric suffixes as needed.

    Parameters
    ----------
    name
        Candidate feature name.
    counts
        Mutable count dictionary keyed by raw name.

    Returns
    -------
    str
        Original name or ``"<name> <N>"`` for repeated names.
    """

    key = str(name)
    count = counts.get(key, 0) + 1
    counts[key] = count
    if count == 1:
        return key
    return f"{key} {count}"


def load_polygon_features(geojson_path: str | Path) -> list[PolygonFeature]:
    """Load named Polygon/MultiPolygon features from a GeoJSON file.

    Parameters
    ----------
    geojson_path
        GeoJSON path containing Polygon or MultiPolygon features.

    Returns
    -------
    list of PolygonFeature
        Named features with individual shell components preserved.
    """

    path = Path(geojson_path).expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") == "FeatureCollection":
        raw_features = payload.get("features", [])
    elif payload.get("type") == "Feature":
        raw_features = [payload]
    else:
        raw_features = [{"type": "Feature", "properties": {}, "geometry": payload}]

    out: list[PolygonFeature] = []
    counts: dict[str, int] = {}
    for index, feature in enumerate(raw_features):
        geom_payload = feature.get("geometry") if isinstance(feature, dict) else None
        if not geom_payload:
            continue
        geom = shape(geom_payload)
        if geom.is_empty:
            continue
        if isinstance(geom, Polygon):
            shells = (geom,)
        elif isinstance(geom, MultiPolygon):
            shells = tuple(poly for poly in geom.geoms if not poly.is_empty)
        else:
            continue
        if not shells:
            continue
        properties = dict(feature.get("properties") or {}) if isinstance(feature, dict) else {}
        name = _dedupe_name(_feature_name(properties, f"polygon_{index + 1}"), counts)
        out.append(PolygonFeature(name=name, geometry=geom, shells=shells, properties=properties))
    return out


def _local_shell(feature: PolygonFeature, shell_index: int) -> LocalShell:
    """Build local projected geometry for one shell component.

    Parameters
    ----------
    feature
        Parent polygon feature.
    shell_index
        Component index.

    Returns
    -------
    LocalShell
        Projected shell and transformers.
    """

    shell = feature.shells[int(shell_index)]
    centroid = shell.centroid
    crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={float(centroid.y)} +lon_0={float(centroid.x)} +datum=WGS84 +units=m +no_defs"
    )
    to_projected = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    to_lonlat = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    shell_projected = transform(to_projected.transform, shell)
    shell_outer_projected = Polygon(shell_projected.exterior)
    exterior_line = LineString(shell_outer_projected.exterior.coords)
    return LocalShell(
        feature_name=feature.name,
        shell_index=int(shell_index),
        shell_lonlat=shell,
        shell_projected=shell_projected,
        shell_outer_projected=shell_outer_projected,
        exterior_line_projected=exterior_line,
        to_projected=to_projected,
        to_lonlat=to_lonlat,
    )


def project_point(local_shell: LocalShell, lon: float, lat: float) -> Point:
    """Project a lon/lat point into one shell's local metric CRS.

    Parameters
    ----------
    local_shell
        Local shell context.
    lon, lat
        Geographic coordinates.

    Returns
    -------
    shapely.geometry.Point
        Projected point in meters.
    """

    x, y = local_shell.to_projected.transform(float(lon), float(lat))
    return Point(float(x), float(y))


def inverse_project_point(local_shell: LocalShell, x: float, y: float) -> tuple[float, float]:
    """Convert one projected point back to lon/lat.

    Parameters
    ----------
    local_shell
        Local shell context.
    x, y
        Projected coordinates in meters.

    Returns
    -------
    tuple
        ``(lon, lat)``.
    """

    lon, lat = local_shell.to_lonlat.transform(float(x), float(y))
    return float(lon), float(lat)


def _unit_vector(dx: float, dy: float) -> tuple[float, float] | None:
    """Normalize one vector or return None when it is degenerate.

    Parameters
    ----------
    dx, dy
        Vector components.

    Returns
    -------
    tuple or None
        Unit vector components.
    """

    norm = math.hypot(float(dx), float(dy))
    if not math.isfinite(norm) or norm <= 1.0e-9:
        return None
    return float(dx) / norm, float(dy) / norm


def _nearest_segment_tangent(local_shell: LocalShell, point: Point) -> tuple[Point, tuple[float, float]] | None:
    """Find the nearest exterior-ring point and a stable tangent.

    Parameters
    ----------
    local_shell
        Local shell context.
    point
        Projected station point.

    Returns
    -------
    tuple or None
        ``(anchor_point, tangent_unit_vector)`` when a stable tangent exists.
    """

    coords = list(local_shell.exterior_line_projected.coords)
    if len(coords) < 2:
        return None
    best: tuple[float, int, Point, float] | None = None
    for index in range(len(coords) - 1):
        p0 = np.asarray(coords[index], dtype=float)
        p1 = np.asarray(coords[index + 1], dtype=float)
        seg = p1 - p0
        seg_len2 = float(np.dot(seg, seg))
        if seg_len2 <= 1.0e-12:
            continue
        raw_t = float(np.dot(np.asarray((point.x, point.y)) - p0, seg) / seg_len2)
        t = min(1.0, max(0.0, raw_t))
        nearest = p0 + t * seg
        dist = float(np.linalg.norm(np.asarray((point.x, point.y)) - nearest))
        if best is None or dist < best[0]:
            best = (dist, index, Point(float(nearest[0]), float(nearest[1])), t)
    if best is None:
        return None

    _dist, index, anchor, t = best
    p0 = np.asarray(coords[index], dtype=float)
    p1 = np.asarray(coords[index + 1], dtype=float)
    vectors: list[np.ndarray] = [p1 - p0]
    if t <= 1.0e-3 and index > 0:
        vectors.append(p0 - np.asarray(coords[index - 1], dtype=float))
    if t >= 1.0 - 1.0e-3 and index + 2 < len(coords):
        vectors.append(np.asarray(coords[index + 2], dtype=float) - p1)

    unit_vectors: list[np.ndarray] = []
    for vec in vectors:
        uv = _unit_vector(float(vec[0]), float(vec[1]))
        if uv is not None:
            unit_vectors.append(np.asarray(uv, dtype=float))
    if not unit_vectors:
        return None
    tangent = np.mean(unit_vectors, axis=0)
    tangent_unit = _unit_vector(float(tangent[0]), float(tangent[1]))
    if tangent_unit is None:
        first = unit_vectors[0]
        tangent_unit = (float(first[0]), float(first[1]))
    return anchor, tangent_unit


def _average_tangent_near_anchor(
    local_shell: LocalShell,
    anchor: Point,
    *,
    window_km: float = 10.0,
    fallback: tuple[float, float] | None = None,
) -> tuple[float, float] | None:
    """Average exterior-ring tangent over a metric window around an anchor.

    Parameters
    ----------
    local_shell
        Local shell context.
    anchor
        Projected exterior-boundary point.
    window_km
        Total exterior-ring distance window in kilometers.
    fallback
        Tangent used when the averaged window is degenerate.

    Returns
    -------
    tuple or None
        Unit tangent vector averaged across the requested boundary window.
    """

    coords = [np.asarray(coord, dtype=float) for coord in local_shell.exterior_line_projected.coords]
    if len(coords) < 2:
        return fallback
    segment_lengths = np.asarray([float(np.linalg.norm(coords[i + 1] - coords[i])) for i in range(len(coords) - 1)])
    total_length = float(np.nansum(segment_lengths))
    if not math.isfinite(total_length) or total_length <= 1.0e-6:
        return fallback
    anchor_distance = float(local_shell.exterior_line_projected.project(anchor))
    half_window_m = max(0.0, float(window_km) * 500.0)
    if half_window_m <= 0.0:
        return fallback

    weighted = np.zeros(2, dtype=float)
    cursor = 0.0
    intervals: list[tuple[float, float]]
    start = anchor_distance - half_window_m
    end = anchor_distance + half_window_m
    if start < 0.0:
        intervals = [(0.0, end), (total_length + start, total_length)]
    elif end > total_length:
        intervals = [(start, total_length), (0.0, end - total_length)]
    else:
        intervals = [(start, end)]

    for index, seg_len in enumerate(segment_lengths):
        if seg_len <= 1.0e-9:
            continue
        seg_start = cursor
        seg_end = cursor + float(seg_len)
        overlap = 0.0
        for interval_start, interval_end in intervals:
            overlap += max(0.0, min(seg_end, interval_end) - max(seg_start, interval_start))
        if overlap > 0.0:
            unit = (coords[index + 1] - coords[index]) / float(seg_len)
            weighted += unit * overlap
        cursor = seg_end

    tangent = _unit_vector(float(weighted[0]), float(weighted[1]))
    return tangent if tangent is not None else fallback


def _inward_normal(local_shell: LocalShell, anchor: Point, tangent: tuple[float, float]) -> tuple[float, float] | None:
    """Determine the inward normal for an exterior-boundary tangent.

    Parameters
    ----------
    local_shell
        Local shell context.
    anchor
        Projected exterior-boundary point.
    tangent
        Tangent unit vector.

    Returns
    -------
    tuple or None
        Inward normal unit vector.
    """

    tx, ty = tangent
    candidates = [(-ty, tx), (ty, -tx)]
    for distance_m in (1.0, 10.0, 50.0, 100.0, 250.0, 500.0):
        for nx, ny in candidates:
            probe = Point(anchor.x + nx * distance_m, anchor.y + ny * distance_m)
            if local_shell.shell_outer_projected.contains(probe):
                return float(nx), float(ny)
    target = local_shell.shell_outer_projected.representative_point()
    to_inside = np.asarray((target.x - anchor.x, target.y - anchor.y), dtype=float)
    if float(np.linalg.norm(to_inside)) > 1.0e-9:
        dots = [float(nx * to_inside[0] + ny * to_inside[1]) for nx, ny in candidates]
        if max(dots) > min(dots):
            nx, ny = candidates[int(np.argmax(dots))]
            return float(nx), float(ny)
    return None


def _collect_intersection_points(geometry: BaseGeometry) -> list[Point]:
    """Flatten intersection geometry into point samples.

    Parameters
    ----------
    geometry
        Shapely intersection result.

    Returns
    -------
    list of Point
        Candidate points.
    """

    if geometry.is_empty:
        return []
    if isinstance(geometry, Point):
        return [geometry]
    if isinstance(geometry, LineString):
        coords = list(geometry.coords)
        return [Point(coords[0]), Point(coords[-1])] if coords else []
    if hasattr(geometry, "geoms"):
        points: list[Point] = []
        for item in geometry.geoms:
            points.extend(_collect_intersection_points(item))
        return points
    return []


def local_shell_width_km(local_shell: LocalShell, anchor: Point, inward_normal: tuple[float, float]) -> float:
    """Measure shell width from an anchor to the opposite exterior shell.

    Parameters
    ----------
    local_shell
        Local shell context.
    anchor
        Projected exterior-boundary point.
    inward_normal
        Inward normal unit vector.

    Returns
    -------
    float
        Width in kilometers. Holes are ignored.
    """

    nx, ny = inward_normal
    minx, miny, maxx, maxy = local_shell.shell_outer_projected.bounds
    span = max(maxx - minx, maxy - miny, 1000.0)
    far = Point(anchor.x + nx * span * 4.0, anchor.y + ny * span * 4.0)
    ray = LineString([(anchor.x, anchor.y), (far.x, far.y)])
    intersections = _collect_intersection_points(ray.intersection(local_shell.exterior_line_projected))
    candidates: list[float] = []
    for point in intersections:
        dx = float(point.x - anchor.x)
        dy = float(point.y - anchor.y)
        along = dx * nx + dy * ny
        lateral = abs(dx * (-ny) + dy * nx)
        if along > 1.0 and lateral <= max(2.0, along * 1.0e-6):
            candidates.append(float(along))
    if not candidates:
        return float("nan")
    return min(candidates) / 1000.0


def build_station_corridor(
    local_shell: LocalShell,
    *,
    anchor: Point,
    station_point: Point,
    tangent: tuple[float, float],
    inward_normal: tuple[float, float],
    station_side: str,
    local_width_km: float,
    corridor_length_km: float = 30.0,
    corridor_thickness_km: float = 10.0,
) -> tuple[Polygon, float]:
    """Build a station-specific normal corridor in lon/lat.

    Parameters
    ----------
    local_shell
        Local shell context.
    anchor
        Projected exterior-boundary point.
    station_point
        Projected station point.
    tangent, inward_normal
        Unit vectors in projected coordinates.
    station_side
        ``"inside"`` or ``"outside"``.
    local_width_km
        Local shell width in kilometers.
    corridor_length_km, corridor_thickness_km
        Requested corridor dimensions.

    Returns
    -------
    tuple
        ``(corridor_lonlat, effective_length_km)``.
    """

    side_key = str(station_side).strip().lower()
    if side_key == "inside":
        length_km = min(float(corridor_length_km), float(local_width_km))
        normal = np.asarray(inward_normal, dtype=float)
    else:
        length_km = float(corridor_length_km)
        normal = -np.asarray(inward_normal, dtype=float)
    length_m = max(0.0, length_km * 1000.0)
    half_width_m = max(0.0, float(corridor_thickness_km) * 500.0)
    tangent_vec = np.asarray(tangent, dtype=float)
    anchor_vec = np.asarray((anchor.x, anchor.y), dtype=float)
    station_vec = np.asarray((station_point.x, station_point.y), dtype=float)
    lateral_offset = float(np.dot(station_vec - anchor_vec, tangent_vec))

    base_center = anchor_vec + lateral_offset * tangent_vec
    end_center = base_center + length_m * normal
    corners = [
        base_center - half_width_m * tangent_vec,
        base_center + half_width_m * tangent_vec,
        end_center + half_width_m * tangent_vec,
        end_center - half_width_m * tangent_vec,
        base_center - half_width_m * tangent_vec,
    ]
    lonlat = [inverse_project_point(local_shell, float(x), float(y)) for x, y in corners]
    return Polygon(lonlat), length_km


def _rotate_unit_vector(vector: np.ndarray, angle_rad: float) -> np.ndarray:
    """Rotate one 2-D unit vector by an angle in radians.

    Parameters
    ----------
    vector
        Unit vector in projected coordinates.
    angle_rad
        Rotation angle in radians, positive counterclockwise.

    Returns
    -------
    numpy.ndarray
        Rotated unit vector.
    """

    c = math.cos(float(angle_rad))
    s = math.sin(float(angle_rad))
    return np.asarray((c * vector[0] - s * vector[1], s * vector[0] + c * vector[1]), dtype=float)


def build_station_triangle_corridor(
    local_shell: LocalShell,
    *,
    anchor: Point,
    station_point: Point,
    inward_normal: tuple[float, float],
    station_side: str,
    corridor_length_km: float = 30.0,
    half_angle_deg: float = 30.0,
) -> tuple[Polygon, float]:
    """Build a triangular station-side event-selection wedge in lon/lat.

    Parameters
    ----------
    local_shell
        Local shell context.
    anchor
        Projected exterior-boundary point used as the triangle vertex.
    station_point
        Projected station point. The triangle centerline is chosen to pass
        through this point when possible.
    inward_normal
        Inward normal unit vector in projected coordinates.
    station_side
        ``"inside"`` or ``"outside"``.
    corridor_length_km
        Length of each triangle side in kilometers.
    half_angle_deg
        Half angle on either side of the centerline in degrees.

    Returns
    -------
    tuple
        ``(corridor_lonlat, effective_side_length_km)``.
    """

    side_key = str(station_side).strip().lower()
    station_side_normal = np.asarray(inward_normal, dtype=float)
    if side_key != "inside":
        station_side_normal = -station_side_normal
    anchor_vec = np.asarray((anchor.x, anchor.y), dtype=float)
    station_vec = np.asarray((station_point.x, station_point.y), dtype=float)
    to_station = station_vec - anchor_vec
    to_station_norm = float(np.linalg.norm(to_station))
    if to_station_norm > 1.0e-9 and float(np.dot(to_station, station_side_normal)) > 0.0:
        center = to_station / to_station_norm
    else:
        center = station_side_normal / float(np.linalg.norm(station_side_normal))
    side_length_m = max(0.0, float(corridor_length_km) * 1000.0)
    half_angle_rad = math.radians(max(0.0, float(half_angle_deg)))
    left = anchor_vec + side_length_m * _rotate_unit_vector(center, half_angle_rad)
    right = anchor_vec + side_length_m * _rotate_unit_vector(center, -half_angle_rad)
    corners = [anchor_vec, left, right, anchor_vec]
    lonlat = [inverse_project_point(local_shell, float(x), float(y)) for x, y in corners]
    return Polygon(lonlat), float(corridor_length_km)


def station_edge_selection_for_shell(
    feature: PolygonFeature,
    shell_index: int,
    *,
    station: str,
    network: str,
    station_lat: float,
    station_lon: float,
    near_edge_fraction: float = 0.10,
    near_edge_width_km: float | None = None,
    corridor_length_km: float = 30.0,
    corridor_thickness_km: float = 10.0,
    edge_average_window_km: float = 10.0,
    corridor_shape: str = "rectangle",
    corridor_half_angle_deg: float = 30.0,
) -> StationEdgeSelection | None:
    """Evaluate one station against one polygon shell.

    Parameters
    ----------
    feature, shell_index
        Polygon feature and component.
    station, network, station_lat, station_lon
        Station metadata.
    near_edge_fraction, near_edge_width_km
        Edge qualification rule.
    corridor_length_km, corridor_thickness_km
        Corridor dimensions. Triangle mode uses ``corridor_length_km`` as the
        side length and ignores thickness.
    edge_average_window_km
        Exterior-edge distance window used to average the boundary tangent.
    corridor_shape
        ``"rectangle"`` for the legacy station-centered rectangle or
        ``"triangle"`` for an angular wedge from the nearest boundary point.
    corridor_half_angle_deg
        Half angle in degrees for triangle corridors.

    Returns
    -------
    StationEdgeSelection or None
        Selection when the station qualifies, otherwise None.
    """

    local_shell = _local_shell(feature, shell_index)
    station_point = project_point(local_shell, float(station_lon), float(station_lat))
    nearest = _nearest_segment_tangent(local_shell, station_point)
    if nearest is None:
        warnings.warn(f"Skipping station {station}: could not determine a stable boundary tangent.", stacklevel=0)
        return None
    anchor, nearest_tangent = nearest
    tangent = _average_tangent_near_anchor(
        local_shell,
        anchor,
        window_km=edge_average_window_km,
        fallback=nearest_tangent,
    )
    if tangent is None:
        warnings.warn(f"Skipping station {station}: could not average the boundary tangent.", stacklevel=0)
        return None
    inward = _inward_normal(local_shell, anchor, tangent)
    if inward is None:
        warnings.warn(f"Skipping station {station}: could not determine inward normal.", stacklevel=0)
        return None
    width_km = local_shell_width_km(local_shell, anchor, inward)
    if not math.isfinite(width_km) or width_km <= 0.0:
        warnings.warn(f"Skipping station {station}: local shell width could not be measured.", stacklevel=0)
        return None

    station_inside = bool(local_shell.shell_projected.contains(station_point) or local_shell.shell_projected.touches(station_point))
    station_side = "inside" if station_inside else "outside"
    distance_km = float(station_point.distance(anchor) / 1000.0)
    threshold_km = float(near_edge_width_km) if near_edge_width_km is not None else float(near_edge_fraction) * width_km
    if distance_km > threshold_km:
        return None

    shape_key = str(corridor_shape or "rectangle").strip().lower()
    if shape_key == "triangle":
        corridor, effective_length = build_station_triangle_corridor(
            local_shell,
            anchor=anchor,
            station_point=station_point,
            inward_normal=inward,
            station_side=station_side,
            corridor_length_km=corridor_length_km,
            half_angle_deg=corridor_half_angle_deg,
        )
        effective_thickness = 0.0
    elif shape_key == "rectangle":
        corridor, effective_length = build_station_corridor(
            local_shell,
            anchor=anchor,
            station_point=station_point,
            tangent=tangent,
            inward_normal=inward,
            station_side=station_side,
            local_width_km=width_km,
            corridor_length_km=corridor_length_km,
            corridor_thickness_km=corridor_thickness_km,
        )
        effective_thickness = float(corridor_thickness_km)
    else:
        raise ValueError(f"Unsupported corridor_shape: {corridor_shape!r}")
    anchor_lon, anchor_lat = inverse_project_point(local_shell, anchor.x, anchor.y)
    return StationEdgeSelection(
        feature_name=feature.name,
        station=str(station),
        network=str(network or "UNKNOWN"),
        shell_index=int(shell_index),
        station_lat=float(station_lat),
        station_lon=float(station_lon),
        station_side=station_side,
        anchor_lon=anchor_lon,
        anchor_lat=anchor_lat,
        local_shell_width_km=float(width_km),
        near_edge_threshold_km=float(threshold_km),
        distance_to_edge_km=float(distance_km),
        corridor_length_km=float(effective_length),
        corridor_thickness_km=float(effective_thickness),
        edge_average_window_km=float(edge_average_window_km),
        corridor_shape=shape_key,
        corridor_half_angle_deg=float(corridor_half_angle_deg),
        corridor_lonlat=corridor,
        tangent_xy=(float(tangent[0]), float(tangent[1])),
        inward_normal_xy=(float(inward[0]), float(inward[1])),
    )


def select_near_edge_stations(
    feature: PolygonFeature,
    station_df: pd.DataFrame,
    *,
    near_edge_fraction: float = 0.10,
    near_edge_width_km: float | None = None,
    corridor_length_km: float = 30.0,
    corridor_thickness_km: float = 10.0,
    edge_average_window_km: float = 10.0,
    corridor_shape: str = "rectangle",
    corridor_half_angle_deg: float = 30.0,
) -> list[StationEdgeSelection]:
    """Select stations near the nearest exterior shell edge of a feature.

    Parameters
    ----------
    feature
        Polygon feature.
    station_df
        Station table with ``station``, ``station_lat``, ``station_lon``, and
        optional ``network``.
    near_edge_fraction, near_edge_width_km
        Edge qualification rule.
    corridor_length_km, corridor_thickness_km
        Corridor dimensions. Triangle mode uses ``corridor_length_km`` as the
        side length and ignores thickness.
    edge_average_window_km
        Exterior-edge distance window used to average the boundary tangent.
    corridor_shape
        Corridor footprint shape: ``"rectangle"`` or ``"triangle"``.
    corridor_half_angle_deg
        Half angle in degrees for triangle corridors.

    Returns
    -------
    list of StationEdgeSelection
        Qualified stations.
    """

    selections: list[StationEdgeSelection] = []
    for _, row in station_df.iterrows():
        station = str(row.get("station", "")).strip()
        if not station:
            continue
        try:
            station_lat = float(row.get("station_lat"))
            station_lon = float(row.get("station_lon"))
        except Exception:
            continue
        if not (math.isfinite(station_lat) and math.isfinite(station_lon)):
            continue
        shell_candidates: list[StationEdgeSelection] = []
        for shell_index in range(len(feature.shells)):
            selection = station_edge_selection_for_shell(
                feature,
                shell_index,
                station=station,
                network=str(row.get("network", "UNKNOWN")),
                station_lat=station_lat,
                station_lon=station_lon,
                near_edge_fraction=near_edge_fraction,
                near_edge_width_km=near_edge_width_km,
                corridor_length_km=corridor_length_km,
                corridor_thickness_km=corridor_thickness_km,
                edge_average_window_km=edge_average_window_km,
                corridor_shape=corridor_shape,
                corridor_half_angle_deg=corridor_half_angle_deg,
            )
            if selection is not None:
                shell_candidates.append(selection)
        if shell_candidates:
            shell_candidates.sort(key=lambda item: (item.distance_to_edge_km, item.shell_index))
            selections.append(shell_candidates[0])
    return selections


def event_rows_in_corridor(
    events_df: pd.DataFrame,
    corridor_lonlat: Polygon,
    *,
    min_depth_km: float | None = None,
    max_depth_km: float | None = None,
) -> pd.DataFrame:
    """Select event rows inside a corridor footprint and optional depth range.

    Parameters
    ----------
    events_df
        Runtime event catalog with event coordinates and depth.
    corridor_lonlat
        Corridor footprint polygon in lon/lat.
    min_depth_km, max_depth_km
        Optional inclusive depth limits.

    Returns
    -------
    pandas.DataFrame
        Matching rows preserving input columns.
    """

    rows: list[pd.Series] = []
    for _, row in events_df.iterrows():
        try:
            lon = float(row.get("event_lon"))
            lat = float(row.get("event_lat"))
        except Exception:
            continue
        if not (math.isfinite(lon) and math.isfinite(lat)):
            continue
        if min_depth_km is not None or max_depth_km is not None:
            try:
                depth = float(row.get("depth_km"))
            except Exception:
                continue
            if not math.isfinite(depth):
                continue
            if min_depth_km is not None and depth < float(min_depth_km):
                continue
            if max_depth_km is not None and depth > float(max_depth_km):
                continue
        point = Point(lon, lat)
        if corridor_lonlat.contains(point) or corridor_lonlat.touches(point):
            rows.append(row)
    if not rows:
        return events_df.iloc[0:0].copy()
    return pd.DataFrame(rows).reset_index(drop=True)
