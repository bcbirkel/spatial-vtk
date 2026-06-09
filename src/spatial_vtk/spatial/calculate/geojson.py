"""General GeoJSON metadata, path relation, and polygon-summary helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

from spatial_vtk.spatial.calculate.polygon_edges import PolygonFeature, load_polygon_features, safe_name_token
from spatial_vtk.spatial.calculate.settings import spatial_statistics_settings_from_config

GeoJSONRelation = Literal["crosses_boundary", "begins_in", "ends_in", "station_inside", "event_inside"]
GeoJSONDirection = Literal["either", "inside_to_outside", "outside_to_inside"]


class GeoJSONNoOverlapError(ValueError):
    """Raised when selected GeoJSON polygons do not overlap the supplied data."""


@dataclass(frozen=True)
class GeoJSONPathControl:
    """First-class configuration for GeoJSON path membership calculations.

    Parameters
    ----------
    relation
        Relation to evaluate: ``"crosses_boundary"``, ``"begins_in"``, or
        ``"ends_in"``.
    selector
        Polygon selector. Use ``"all"``, one polygon name/safe token, a set of
        names/tokens, or a mapping of property names to allowed values.
    direction
        Direction filter for boundary crossings. ``"inside_to_outside"`` means
        the event/start point is inside the polygon and the station/end point
        is outside; ``"outside_to_inside"`` is the reverse.
    start_role, end_role
        Data roles used for path start and end coordinates.
    """

    relation: GeoJSONRelation = "crosses_boundary"
    selector: object = "all"
    direction: GeoJSONDirection = "either"
    start_role: str = "event"
    end_role: str = "station"


def load_geojson_polygons(geojson_path: str | Path) -> list[PolygonFeature]:
    """Load Polygon and MultiPolygon features from a GeoJSON file.

    Parameters
    ----------
    geojson_path
        Path to a GeoJSON FeatureCollection, Feature, Polygon, or MultiPolygon.

    Returns
    -------
    list of PolygonFeature
        Named polygon features in longitude/latitude coordinates.
    """

    return load_polygon_features(geojson_path)


def select_geojson_polygons(
    features: Sequence[PolygonFeature],
    selector: object = "all",
) -> list[PolygonFeature]:
    """Select one, many, or all GeoJSON polygon features.

    Parameters
    ----------
    features
        Loaded polygon features.
    selector
        ``"all"``/``None`` for all features; a single name or safe token; an
        iterable of names/tokens; or a mapping from property name to allowed
        property values.

    Returns
    -------
    list of PolygonFeature
        Selected features.
    """

    if selector is None or str(selector).lower() == "all":
        return list(features)
    if isinstance(selector, Mapping):
        selected = [
            feature
            for feature in features
            if all(_property_matches(feature.properties.get(key), allowed) for key, allowed in selector.items())
        ]
    elif isinstance(selector, str):
        wanted = {selector, safe_name_token(selector)}
        selected = [feature for feature in features if _feature_matches(feature, wanted)]
    else:
        wanted = {str(item) for item in selector if str(item).strip()}
        wanted |= {safe_name_token(item) for item in wanted}
        selected = [feature for feature in features if _feature_matches(feature, wanted)]
    if not selected:
        available = ", ".join(feature.name for feature in features[:12])
        raise ValueError(f"No GeoJSON polygons matched selector {selector!r}. Available examples: {available}")
    return selected


def annotate_points_with_geojson(
    df: pd.DataFrame,
    geojson_path: str | Path,
    *,
    point: Literal["station", "event"],
    selector: object = "all",
    lon_col: str | None = None,
    lat_col: str | None = None,
    prefix: str | None = None,
    include_per_polygon: bool = True,
    require_overlap: bool = True,
) -> pd.DataFrame:
    """Add GeoJSON polygon membership columns for station or event points.

    Parameters
    ----------
    df
        Table containing point coordinates.
    geojson_path
        GeoJSON polygon file. It is only loaded by this GeoJSON-specific
        function; the basic workflow does not require this file.
    point
        Point role to annotate: ``"station"`` or ``"event"``.
    selector
        Polygon selector: all, one polygon, a set of polygons, or property
        filters.
    lon_col, lat_col
        Optional coordinate columns. When omitted, common station/event columns
        are inferred.
    prefix
        Output column prefix. Defaults to ``station_geojson`` or
        ``event_geojson``.
    include_per_polygon
        Whether to add one boolean column per selected polygon.
    require_overlap
        Raise ``GeoJSONNoOverlapError`` when no supplied points fall inside or
        touch the selected polygons.

    Returns
    -------
    pandas.DataFrame
        Copy of ``df`` with membership labels and boolean flags.
    """

    features = select_geojson_polygons(load_geojson_polygons(geojson_path), selector)
    out = df.copy()
    lon_name, lat_name = _resolve_point_columns(out, point=point, lon_col=lon_col, lat_col=lat_col)
    base = prefix or f"{point}_geojson"
    label_values: list[str] = []
    inside_any: list[bool] = []
    per_polygon: dict[str, list[bool]] = {feature.name: [] for feature in features}

    for row in out.itertuples(index=False):
        lon = _safe_float(getattr(row, lon_name))
        lat = _safe_float(getattr(row, lat_name))
        labels: list[str] = []
        if lon is not None and lat is not None:
            point_geom = Point(lon, lat)
            for feature in features:
                inside = _point_in_feature(point_geom, feature)
                per_polygon[feature.name].append(inside)
                if inside:
                    labels.append(feature.name)
        else:
            for feature in features:
                per_polygon[feature.name].append(False)
        label_values.append(";".join(labels))
        inside_any.append(bool(labels))

    if require_overlap and not any(inside_any):
        raise GeoJSONNoOverlapError(
            f"No {point} points overlap selected GeoJSON polygons from {geojson_path}. "
            "Check the GeoJSON CRS, coordinate columns, and polygon selector."
        )
    out[f"{base}_inside_any"] = inside_any
    out[f"{base}_labels"] = label_values
    if include_per_polygon:
        for feature in features:
            out[f"{base}_inside_{safe_name_token(feature.name)}"] = per_polygon[feature.name]
    return out


def classify_paths_with_geojson(
    df: pd.DataFrame,
    geojson_path: str | Path,
    *,
    relation: GeoJSONRelation = "crosses_boundary",
    selector: object = "all",
    direction: GeoJSONDirection = "either",
    start_role: str = "event",
    end_role: str = "station",
    start_lon_col: str | None = None,
    start_lat_col: str | None = None,
    end_lon_col: str | None = None,
    end_lat_col: str | None = None,
    prefix: str = "path_geojson",
    include_per_polygon: bool = True,
    require_overlap: bool = True,
) -> pd.DataFrame:
    """Classify source-station paths relative to selected GeoJSON polygons.

    Parameters
    ----------
    df
        Table containing event/start and station/end coordinates.
    geojson_path
        GeoJSON polygon file. It is optional for the basic workflow and only
        required by this function.
    relation
        ``"crosses_boundary"``, ``"begins_in"``, ``"ends_in"``,
        ``"station_inside"``, or ``"event_inside"``.
    selector
        One polygon, a set of polygons, all polygons, or property filters.
    direction
        Direction filter for crossing relation.
    start_role, end_role
        Coordinate roles used when explicit columns are not provided.
    start_lon_col, start_lat_col, end_lon_col, end_lat_col
        Optional coordinate columns for path start and end.
    prefix
        Output column prefix.
    include_per_polygon
        Whether to add one match column per selected polygon.
    require_overlap
        Raise ``GeoJSONNoOverlapError`` when the selected polygons have no
        qualifying relation to the paths.

    Returns
    -------
    pandas.DataFrame
        Copy of ``df`` with path relation flags, labels, and crossing direction.
    """

    _validate_relation_and_direction(relation, direction)
    features = select_geojson_polygons(load_geojson_polygons(geojson_path), selector)
    out = df.copy()
    start_lon, start_lat = _resolve_point_columns(out, point=start_role, lon_col=start_lon_col, lat_col=start_lat_col)
    end_lon, end_lat = _resolve_point_columns(out, point=end_role, lon_col=end_lon_col, lat_col=end_lat_col)

    match_any: list[bool] = []
    label_values: list[str] = []
    direction_values: list[str] = []
    starts_any: list[bool] = []
    ends_any: list[bool] = []
    crosses_any: list[bool] = []
    per_polygon: dict[str, list[bool]] = {feature.name: [] for feature in features}

    for row in out.itertuples(index=False):
        start = _point_from_row(row, start_lon, start_lat)
        end = _point_from_row(row, end_lon, end_lat)
        labels: list[str] = []
        directions: list[str] = []
        row_starts: list[bool] = []
        row_ends: list[bool] = []
        row_crosses: list[bool] = []
        for feature in features:
            starts_in = start is not None and _point_in_feature(start, feature)
            ends_in = end is not None and _point_in_feature(end, feature)
            crosses = False
            if start is not None and end is not None:
                line = LineString([start, end])
                crosses = _line_crosses_feature_boundary(line, feature)
            relation_direction = _relation_direction(starts_in, ends_in)
            relation_match = _relation_matches(
                relation=relation,
                starts_in=starts_in,
                ends_in=ends_in,
                crosses=crosses,
                direction=direction,
            )
            per_polygon[feature.name].append(relation_match)
            if relation_match:
                labels.append(feature.name)
                directions.append(relation_direction)
            row_starts.append(starts_in)
            row_ends.append(ends_in)
            row_crosses.append(crosses)
        match_any.append(bool(labels))
        label_values.append(";".join(labels))
        direction_values.append(";".join(_dedupe(directions)))
        starts_any.append(any(row_starts))
        ends_any.append(any(row_ends))
        crosses_any.append(any(row_crosses))

    if require_overlap and not any(match_any):
        raise GeoJSONNoOverlapError(
            f"No paths match relation={relation!r}, direction={direction!r}, selector={selector!r} "
            f"for GeoJSON {geojson_path}. Check coordinate columns, CRS, or selector."
        )
    out[f"{prefix}_matches"] = match_any
    out[f"{prefix}_labels"] = label_values
    out[f"{prefix}_cross_direction"] = direction_values
    out[f"{prefix}_begins_in_any"] = starts_any
    out[f"{prefix}_ends_in_any"] = ends_any
    out[f"{prefix}_crosses_boundary_any"] = crosses_any
    if include_per_polygon:
        for feature in features:
            out[f"{prefix}_matches_{safe_name_token(feature.name)}"] = per_polygon[feature.name]
    return out


def apply_geojson_path_control(
    df: pd.DataFrame,
    geojson_path: str | Path,
    control: GeoJSONPathControl,
    **kwargs,
) -> pd.DataFrame:
    """Apply a reusable GeoJSON path-control object to a table.

    Parameters
    ----------
    df
        Source-station table.
    geojson_path
        GeoJSON polygon file.
    control
        GeoJSON path relation configuration.
    **kwargs
        Additional keyword arguments forwarded to
        :func:`classify_paths_with_geojson`.

    Returns
    -------
    pandas.DataFrame
        Classified path table.
    """

    return classify_paths_with_geojson(
        df,
        geojson_path,
        relation=control.relation,
        selector=control.selector,
        direction=control.direction,
        start_role=control.start_role,
        end_role=control.end_role,
        **kwargs,
    )


def add_geojson_metadata_to_metrics(
    metrics_df: pd.DataFrame,
    geojson_path: str | Path | None = None,
    *,
    target: Literal["station", "event", "path"] = "station",
    selector: object = "all",
    relation: GeoJSONRelation = "crosses_boundary",
    direction: GeoJSONDirection = "either",
    require_overlap: bool = True,
) -> pd.DataFrame:
    """Add GeoJSON-derived metadata to metric rows.

    Parameters
    ----------
    metrics_df
        Metric, residual, or path table with station/event coordinates.
    geojson_path
        GeoJSON polygon file. When omitted, ``paths.region_geojson`` from the
        active config is used.
    target
        ``"station"`` or ``"event"`` for point membership; ``"path"`` for
        source-station relation classification.
    selector
        Polygon selector.
    relation, direction
        Path relation controls used when ``target="path"``.
    require_overlap
        Whether to raise a clear error if polygons do not overlap the data.

    Returns
    -------
    pandas.DataFrame
        Metric table with GeoJSON metadata columns.
    """

    settings = spatial_statistics_settings_from_config()
    path = geojson_path or settings.region_geojson_path
    if path is None:
        raise ValueError("No GeoJSON path was provided and paths.region_geojson is not configured.")
    if target in {"station", "event"}:
        return annotate_points_with_geojson(
            metrics_df,
            path,
            point=target,
            selector=selector,
            require_overlap=require_overlap,
        )
    if target == "path":
        return classify_paths_with_geojson(
            metrics_df,
            path,
            relation=relation,
            selector=selector,
            direction=direction,
            require_overlap=require_overlap,
        )
    raise ValueError("target must be 'station', 'event', or 'path'.")


def summarize_metrics_by_geojson(
    df: pd.DataFrame,
    *,
    label_col: str | None = None,
    value_col: str | None = None,
    group_cols: Sequence[str] = ("model", "metric", "band"),
    savecsv: bool = False,
    outpath: str | Path | None = None,
) -> pd.DataFrame:
    """Aggregate metric values by GeoJSON polygon labels.

    Parameters
    ----------
    df
        Table with a semicolon-delimited GeoJSON label column.
    label_col
        Label column produced by this module, such as
        ``station_geojson_labels`` or ``path_geojson_labels``. When omitted,
        the first available standard GeoJSON label column is used.
    value_col
        Numeric value to summarize. When omitted, ``spatial.value_column``
        from the active config is used.
    group_cols
        Additional grouping columns.
    savecsv
        Whether to write the summary as a CSV file.
    outpath
        Output path used when ``savecsv`` is true.

    Returns
    -------
    pandas.DataFrame
        Polygon-level count, mean, median, standard deviation, and IQR.
    """

    settings = spatial_statistics_settings_from_config()
    selected_label_col = label_col or _first_available_column(
        df,
        ("station_geojson_labels", "event_geojson_labels", "path_geojson_labels"),
    )
    selected_value_col = value_col or settings.value_column
    if selected_label_col is None:
        raise KeyError("Missing GeoJSON label column. Expected one of station_geojson_labels, event_geojson_labels, or path_geojson_labels.")
    if selected_label_col not in df.columns:
        raise KeyError(f"Missing GeoJSON label column: {selected_label_col}")
    if selected_value_col not in df.columns:
        raise KeyError(f"Missing GeoJSON summary value column: {selected_value_col}")
    work = df.copy()
    work["_geojson_label"] = work[selected_label_col].fillna("").astype(str).str.split(";")
    work = work.explode("_geojson_label")
    work["_geojson_label"] = work["_geojson_label"].astype(str).str.strip()
    work = work.loc[work["_geojson_label"].str.len() > 0].copy()
    if work.empty:
        out = pd.DataFrame(columns=[*group_cols, "geojson_label", "n", "mean", "median", "std", "iqr"])
        _maybe_write_csv(out, savecsv=savecsv, outpath=outpath)
        return out
    work[selected_value_col] = pd.to_numeric(work[selected_value_col], errors="coerce")
    groups = [column for column in group_cols if column in work.columns] + ["_geojson_label"]
    out = (
        work.groupby(groups, dropna=False)[selected_value_col]
        .agg(n="count", mean="mean", median="median", std="std", q25=lambda s: s.quantile(0.25), q75=lambda s: s.quantile(0.75))
        .reset_index()
    )
    out["iqr"] = out["q75"] - out["q25"]
    out = out.drop(columns=["q25", "q75"]).rename(columns={"_geojson_label": "geojson_label"})
    _maybe_write_csv(out, savecsv=savecsv, outpath=outpath)
    return out


def _maybe_write_csv(df: pd.DataFrame, *, savecsv: bool, outpath: str | Path | None) -> None:
    """Write a dataframe to CSV when requested."""

    if not savecsv:
        return
    if outpath is None:
        raise ValueError("outpath is required when savecsv=True.")
    path = Path(outpath).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _first_available_column(df: pd.DataFrame, candidates: Sequence[str]) -> str | None:
    """Return the first candidate column present in a dataframe."""

    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def _feature_matches(feature: PolygonFeature, wanted: set[str]) -> bool:
    """Return whether a feature matches a name/token selector."""

    names = {feature.name, safe_name_token(feature.name)}
    for key, value in feature.properties.items():
        names.add(str(value))
        names.add(safe_name_token(value))
        names.add(f"{key}={value}")
        names.add(safe_name_token(f"{key}_{value}"))
    return any(name in wanted for name in names)


def _property_matches(value: object, allowed: object) -> bool:
    """Return whether a property value matches a selector value or set."""

    if isinstance(allowed, str) or not isinstance(allowed, Iterable):
        allowed_values = {str(allowed), safe_name_token(allowed)}
    else:
        allowed_values = {str(item) for item in allowed}
        allowed_values |= {safe_name_token(item) for item in allowed_values}
    return str(value) in allowed_values or safe_name_token(value) in allowed_values


def _resolve_point_columns(
    df: pd.DataFrame,
    *,
    point: str,
    lon_col: str | None,
    lat_col: str | None,
) -> tuple[str, str]:
    """Resolve lon/lat columns for a point role."""

    if lon_col and lat_col:
        missing = [column for column in (lon_col, lat_col) if column not in df.columns]
        if missing:
            raise KeyError(f"Missing coordinate columns: {missing}")
        return lon_col, lat_col
    role = str(point).lower()
    if role == "station":
        lon_candidates = ["sta_lon", "station_longitude", "station_lon", "longitude", "lon"]
        lat_candidates = ["sta_lat", "station_latitude", "station_lat", "latitude", "lat"]
    elif role == "event":
        lon_candidates = ["event_lon", "event_longitude", "source_lon", "source_longitude"]
        lat_candidates = ["event_lat", "event_latitude", "source_lat", "source_latitude"]
    else:
        lon_candidates = [f"{role}_lon", f"{role}_longitude", "lon", "longitude"]
        lat_candidates = [f"{role}_lat", f"{role}_latitude", "lat", "latitude"]
    lon_name = next((column for column in lon_candidates if column in df.columns), None)
    lat_name = next((column for column in lat_candidates if column in df.columns), None)
    if lon_name is None or lat_name is None:
        raise KeyError(f"Could not resolve {point} longitude/latitude columns.")
    return lon_name, lat_name


def _point_from_row(row: object, lon_col: str, lat_col: str) -> Point | None:
    """Build a Shapely point from one dataframe row."""

    lon = _safe_float(getattr(row, lon_col))
    lat = _safe_float(getattr(row, lat_col))
    if lon is None or lat is None:
        return None
    return Point(lon, lat)


def _safe_float(value: object) -> float | None:
    """Convert one scalar to a finite float when possible."""

    try:
        out = float(value)
    except Exception:
        return None
    return float(out) if np.isfinite(out) else None


def _point_in_feature(point: Point, feature: PolygonFeature) -> bool:
    """Return whether a point lies inside or on a feature boundary."""

    return bool(feature.geometry.contains(point) or feature.geometry.touches(point))


def _line_crosses_feature_boundary(line: LineString, feature: PolygonFeature) -> bool:
    """Return whether a line intersects a polygon boundary."""

    if line.is_empty or line.length <= 0.0:
        return False
    return bool(line.intersects(feature.geometry.boundary))


def _relation_direction(starts_in: bool, ends_in: bool) -> str:
    """Return a path inside/outside direction label."""

    if starts_in and not ends_in:
        return "inside_to_outside"
    if not starts_in and ends_in:
        return "outside_to_inside"
    if starts_in and ends_in:
        return "inside_to_inside"
    return "outside_to_outside"


def _relation_matches(
    *,
    relation: GeoJSONRelation,
    starts_in: bool,
    ends_in: bool,
    crosses: bool,
    direction: GeoJSONDirection,
) -> bool:
    """Evaluate one relation/direction control for one polygon."""

    if relation == "begins_in":
        return starts_in
    if relation == "ends_in":
        return ends_in
    if relation == "station_inside":
        return ends_in
    if relation == "event_inside":
        return starts_in
    if relation == "crosses_boundary":
        if not crosses:
            return False
        if direction == "inside_to_outside":
            return starts_in and not ends_in
        if direction == "outside_to_inside":
            return (not starts_in) and ends_in
        return True
    raise ValueError(f"Unsupported GeoJSON relation: {relation!r}")


def _validate_relation_and_direction(relation: str, direction: str) -> None:
    """Validate relation and direction options."""

    valid_relations = {"crosses_boundary", "begins_in", "ends_in", "station_inside", "event_inside"}
    valid_directions = {"either", "inside_to_outside", "outside_to_inside"}
    if relation not in valid_relations:
        raise ValueError(f"relation must be one of {sorted(valid_relations)}")
    if direction not in valid_directions:
        raise ValueError(f"direction must be one of {sorted(valid_directions)}")


def _dedupe(values: Iterable[str]) -> list[str]:
    """Deduplicate text values while preserving order."""

    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out
