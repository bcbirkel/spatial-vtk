"""General GeoJSON metadata, path relation, and polygon-summary helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
import time
from typing import Literal

import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

from spatial_vtk.spatial.calculate.polygon_edges import PolygonFeature, load_polygon_features, safe_name_token
from spatial_vtk.spatial.calculate.settings import spatial_statistics_settings_from_config

GeoJSONRelation = Literal["crosses_boundary", "begins_in", "ends_in", "station_inside", "event_inside"]
GeoJSONDirection = Literal["either", "inside_to_outside", "outside_to_inside"]

GEOJSON_SUMMARY_INPUT_COLUMNS: tuple[str, ...] = (
    "event_id",
    "event_title",
    "station",
    "station_id",
    "station_name",
    "sta_lon",
    "station_longitude",
    "station_lon",
    "longitude",
    "lon",
    "sta_lat",
    "station_latitude",
    "station_lat",
    "latitude",
    "lat",
    "event_lon",
    "event_longitude",
    "source_lon",
    "source_longitude",
    "event_lat",
    "event_latitude",
    "source_lat",
    "source_latitude",
)


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


@dataclass(frozen=True)
class GeoJSONRegionSummaryWorkflowResult:
    """Result metadata for the table-backed GeoJSON region summary workflow."""

    path: Path
    rows: int
    source_rows: int
    elapsed_s: float


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


def geojson_polygon_preview_table(
    geojson_path_or_features: str | Path | Sequence[PolygonFeature],
    *,
    selector: object = "all",
) -> pd.DataFrame:
    """Return a compact table describing selected GeoJSON polygon features.

    Parameters
    ----------
    geojson_path_or_features
        Path to a GeoJSON file or already-loaded polygon features.
    selector
        Polygon selector accepted by :func:`select_geojson_polygons`.

    Returns
    -------
    pandas.DataFrame
        One row per selected polygon with display labels, geometry type,
        longitude/latitude bounds, and original feature properties.
    """

    features = (
        load_geojson_polygons(geojson_path_or_features)
        if isinstance(geojson_path_or_features, (str, Path))
        else list(geojson_path_or_features)
    )
    selected = select_geojson_polygons(features, selector=selector)
    rows: list[dict[str, object]] = []
    for feature in selected:
        geom = feature.geometry
        min_lon, min_lat, max_lon, max_lat = geom.bounds
        rows.append(
            {
                "region": feature.name.replace("_", " "),
                "feature_name": feature.name,
                "geometry_type": geom.geom_type,
                "min_lon": float(min_lon),
                "min_lat": float(min_lat),
                "max_lon": float(max_lon),
                "max_lat": float(max_lat),
                "property_count": len(feature.properties),
                "properties": dict(feature.properties),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "region",
            "feature_name",
            "geometry_type",
            "min_lon",
            "min_lat",
            "max_lon",
            "max_lat",
            "property_count",
            "properties",
        ],
    )


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


def build_geojson_region_summary(
    df: pd.DataFrame,
    geojson_path: str | Path,
    *,
    selector: object = "all",
    verbose: bool = False,
    source_rows: int | None = None,
) -> pd.DataFrame:
    """Summarize station, event, and path GeoJSON membership efficiently.

    The summary is computed on unique station, event, and event-station
    geometry records instead of every metric row. This keeps large metric
    tables from repeating the same GeoJSON point-in-polygon and path-crossing
    checks for each metric, component, passband, and model row.
    """

    source_rows = len(df) if source_rows is None else int(source_rows)
    rows: list[pd.DataFrame] = []
    for point in ("station", "event"):
        relation = f"{point}_inside"
        try:
            point_records = _unique_point_records(df, point=point)
            _progress(verbose, f"GeoJSON summary: {relation} on {len(point_records)} unique record(s) from {source_rows} row(s)")
            annotated = annotate_points_with_geojson(
                point_records,
                geojson_path,
                point=point,  # type: ignore[arg-type]
                selector=selector,
                include_per_polygon=False,
                require_overlap=False,
            )
            rows.append(
                _geojson_label_count_table(
                    annotated[f"{point}_geojson_labels"],
                    relation=relation,
                    source_rows=source_rows,
                    unique_records=len(point_records),
                )
            )
        except Exception as exc:  # pragma: no cover - exercised through Slurm workflows
            rows.append(_geojson_error_row(relation, source_rows=source_rows, message=str(exc)))
            _progress(verbose, f"GeoJSON summary: {relation} failed: {exc}")

    relation = "crosses_boundary"
    try:
        path_records = _unique_path_records(df)
        _progress(verbose, f"GeoJSON summary: {relation} on {len(path_records)} unique path(s) from {source_rows} row(s)")
        paths = classify_paths_with_geojson(
            path_records,
            geojson_path,
            relation=relation,
            selector=selector,
            include_per_polygon=False,
            require_overlap=False,
        )
        rows.append(
            _geojson_label_count_table(
                paths["path_geojson_labels"],
                relation=relation,
                source_rows=source_rows,
                unique_records=len(path_records),
            )
        )
    except Exception as exc:  # pragma: no cover - exercised through Slurm workflows
        rows.append(_geojson_error_row(relation, source_rows=source_rows, message=str(exc)))
        _progress(verbose, f"GeoJSON summary: {relation} failed: {exc}")

    summary = pd.concat(rows, ignore_index=True, sort=False) if rows else pd.DataFrame(columns=["relation", "region", "count"])
    _progress(verbose, f"GeoJSON summary: complete with {len(summary)} row(s)")
    return summary


def build_geojson_region_summary_from_table(
    table: pd.DataFrame | str | Path,
    geojson_path: str | Path,
    *,
    selector: object = "all",
    chunksize: int | None = 1_000_000,
    verbose: bool = False,
) -> pd.DataFrame:
    """Build a GeoJSON region summary from a metrics table path or dataframe.

    Only event/station identifiers and coordinate columns are read from table
    paths. Repeated metric rows are de-duplicated before geometry operations,
    while the returned summary still reports the original table row count in
    ``source_rows``.
    """

    frame, source_rows = _geojson_summary_input(table, chunksize=chunksize, verbose=verbose)
    return build_geojson_region_summary(
        frame,
        geojson_path,
        selector=selector,
        verbose=verbose,
        source_rows=source_rows,
    )


def run_geojson_region_summary_workflow(
    metrics_table: pd.DataFrame | str | Path | None = None,
    geojson_path: str | Path | None = None,
    *,
    output_key: str = "geojson_region_summaries",
    cfg: object | None = None,
    selector: object = "all",
    chunksize: int | None = 1_000_000,
    verbose: bool = False,
) -> GeoJSONRegionSummaryWorkflowResult:
    """Build and write the configured GeoJSON region summary table.

    Parameters
    ----------
    metrics_table
        Metrics table path or dataframe. When omitted, the active config output
        registry entry for ``"metrics_long"`` is used.
    geojson_path
        GeoJSON feature path. When omitted, ``paths.region_geojson`` is read
        from the active/configured project.
    output_key
        Output table registry key used for the written summary.
    cfg
        Optional :class:`~spatial_vtk.config.runtime.SpatialVTKConfig`.
    selector, chunksize, verbose
        Passed through to :func:`build_geojson_region_summary_from_table`.

    Returns
    -------
    GeoJSONRegionSummaryWorkflowResult
        Written path, output row count, source row count, and elapsed seconds.
    """

    from spatial_vtk.config.outputs import resolve_output_path
    from spatial_vtk.config.runtime import active_config
    from spatial_vtk.io import write_output_table

    started = time.perf_counter()
    config = cfg or active_config()
    resolved_metrics = metrics_table
    if resolved_metrics is None:
        resolved_metrics = resolve_output_path("metrics_long", kind="table", cfg=config)
    resolved_geojson = Path(geojson_path).expanduser() if geojson_path is not None else config.path("paths.region_geojson", must_exist=False)
    if resolved_geojson is None:
        summary = pd.DataFrame(columns=["relation", "region", "count", "unique_records", "source_rows"])
        source_rows = 0
        _progress(verbose, "GeoJSON summary: no paths.region_geojson configured; writing empty summary")
    else:
        frame, source_rows = _geojson_summary_input(resolved_metrics, chunksize=chunksize, verbose=verbose)
        summary = build_geojson_region_summary(
            frame,
            resolved_geojson,
            selector=selector,
            verbose=verbose,
            source_rows=source_rows,
        )
    output_path = write_output_table(output_key, summary, cfg=config)
    elapsed = time.perf_counter() - started
    _progress(verbose, f"GeoJSON summary: wrote {len(summary)} row(s) to {output_path} in {elapsed:.1f}s")
    return GeoJSONRegionSummaryWorkflowResult(
        path=output_path,
        rows=len(summary),
        source_rows=int(source_rows),
        elapsed_s=float(elapsed),
    )


def run_geojson_region_summary_workflow_from_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
    metrics_table: pd.DataFrame | str | Path | None = None,
    geojson_path: str | Path | None = None,
    output_key: str = "geojson_region_summaries",
    selector: object = "all",
    chunksize: int | None = 1_000_000,
    verbose: bool = False,
) -> dict[str, object]:
    """Run the configured GeoJSON region summary workflow.

    This wrapper is intended for notebooks and generated Slurm workers. It
    activates the requested config, delegates all heavy work to
    :func:`run_geojson_region_summary_workflow`, and returns a JSON-ready
    summary for notebook output and Slurm logs.
    """

    config = _geojson_workflow_config(config_path=config_path, run_scenario=run_scenario)
    result = run_geojson_region_summary_workflow(
        metrics_table,
        geojson_path=geojson_path,
        output_key=output_key,
        cfg=config,
        selector=selector,
        chunksize=chunksize,
        verbose=verbose,
    )
    return {
        "path": str(result.path),
        "rows": int(result.rows),
        "source_rows": int(result.source_rows),
        "elapsed_s": float(result.elapsed_s),
    }


def _geojson_workflow_config(
    *,
    config_path: str | Path | None = None,
    run_scenario: str | None = None,
):
    """Resolve and activate config for GeoJSON notebook/Slurm helpers."""

    from spatial_vtk.config.runtime import SpatialVTKConfig, active_config

    if config_path is not None:
        return SpatialVTKConfig.from_file(config_path, run_scenario=run_scenario).activate()
    config = active_config()
    if run_scenario is not None and config.config_path is not None:
        return SpatialVTKConfig.from_file(config.config_path, run_scenario=run_scenario).activate()
    return config.activate()


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


def _geojson_summary_input(
    table: pd.DataFrame | str | Path,
    *,
    chunksize: int | None,
    verbose: bool,
) -> tuple[pd.DataFrame, int]:
    """Return de-duplicated GeoJSON summary columns and original row count."""

    if isinstance(table, pd.DataFrame):
        return _dedupe_geojson_summary_frame(table), len(table)

    path = Path(table).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Metrics table does not exist: {path}")

    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        available, row_count = _parquet_columns_and_rows(path)
        columns = _available_geojson_summary_columns(available)
        if not columns:
            raise KeyError(f"No GeoJSON summary coordinate columns were found in {path}")
        _progress(verbose, f"GeoJSON summary: reading {len(columns)} column(s) from {path}")
        frame = pd.read_parquet(path, columns=columns)
        return _dedupe_geojson_summary_frame(frame), row_count if row_count is not None else len(frame)

    if suffix in {".csv", ".txt"}:
        available = list(pd.read_csv(path, nrows=0).columns)
        columns = _available_geojson_summary_columns(available)
        if not columns:
            raise KeyError(f"No GeoJSON summary coordinate columns were found in {path}")
        if chunksize:
            source_rows = 0
            chunks: list[pd.DataFrame] = []
            for index, chunk in enumerate(pd.read_csv(path, usecols=columns, chunksize=chunksize), start=1):
                source_rows += len(chunk)
                chunks.append(_dedupe_geojson_summary_frame(chunk))
                _progress(verbose, f"GeoJSON summary: read CSV chunk {index} ({source_rows} row(s) total)")
            frame = pd.concat(chunks, ignore_index=True, sort=False) if chunks else pd.DataFrame(columns=columns)
            return _dedupe_geojson_summary_frame(frame), source_rows
        frame = pd.read_csv(path, usecols=columns)
        return _dedupe_geojson_summary_frame(frame), len(frame)

    from spatial_vtk.io import read_table

    frame = read_table(path)
    return _dedupe_geojson_summary_frame(frame), len(frame)


def _parquet_columns_and_rows(path: Path) -> tuple[list[str], int | None]:
    """Return parquet column names and row count without reading row groups."""

    try:
        import pyarrow.parquet as pq
    except Exception:
        frame = pd.read_parquet(path)
        return list(frame.columns), len(frame)
    metadata = pq.ParquetFile(path)
    return list(metadata.schema.names), int(metadata.metadata.num_rows)


def _available_geojson_summary_columns(columns: Sequence[str]) -> list[str]:
    """Return GeoJSON summary columns available in a table schema."""

    available = set(columns)
    return [column for column in GEOJSON_SUMMARY_INPUT_COLUMNS if column in available]


def _dedupe_geojson_summary_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize aliases and remove repeated geometry rows."""

    columns = _available_geojson_summary_columns(df.columns)
    work = df.loc[:, columns].copy()
    _copy_alias_column(work, target="event_id", aliases=("event_title",))
    _copy_alias_column(work, target="station", aliases=("station_id", "station_name"))
    return work.drop_duplicates().reset_index(drop=True)


def _copy_alias_column(df: pd.DataFrame, *, target: str, aliases: Sequence[str]) -> None:
    """Copy the first available alias into a canonical column when absent."""

    if target in df.columns:
        return
    for alias in aliases:
        if alias in df.columns:
            df[target] = df[alias]
            return


def _unique_point_records(df: pd.DataFrame, *, point: str) -> pd.DataFrame:
    """Return unique point geometry records for one point role."""

    lon_col, lat_col = _resolve_point_columns(df, point=point, lon_col=None, lat_col=None)
    id_col = "station" if point == "station" else "event_id"
    columns = [column for column in (id_col, lon_col, lat_col) if column in df.columns]
    return df.loc[:, columns].dropna(subset=[lon_col, lat_col]).drop_duplicates().reset_index(drop=True)


def _unique_path_records(df: pd.DataFrame) -> pd.DataFrame:
    """Return unique event-station geometry records for path classification."""

    event_lon, event_lat = _resolve_point_columns(df, point="event", lon_col=None, lat_col=None)
    station_lon, station_lat = _resolve_point_columns(df, point="station", lon_col=None, lat_col=None)
    columns = [column for column in ("event_id", "station", event_lon, event_lat, station_lon, station_lat) if column in df.columns]
    return df.loc[:, columns].dropna(subset=[event_lon, event_lat, station_lon, station_lat]).drop_duplicates().reset_index(drop=True)


def _geojson_label_count_table(
    labels: pd.Series,
    *,
    relation: str,
    source_rows: int,
    unique_records: int,
) -> pd.DataFrame:
    """Count GeoJSON labels with an explicit outside bin."""

    clean = labels.fillna("").astype(str).str.strip()
    outside_count = int(clean.eq("").sum())
    inside = clean.loc[clean.ne("")].str.split(";").explode().astype(str).str.strip()
    inside = inside.loc[inside.ne("")]
    counts = inside.value_counts().rename_axis("region").reset_index(name="count")
    if outside_count:
        counts = pd.concat([counts, pd.DataFrame([{"region": "outside", "count": outside_count}])], ignore_index=True)
    if counts.empty:
        counts = pd.DataFrame([{"region": "outside", "count": 0}])
    counts["relation"] = relation
    counts["source_rows"] = int(source_rows)
    counts["unique_records"] = int(unique_records)
    return counts.loc[:, ["relation", "region", "count", "unique_records", "source_rows"]]


def _geojson_error_row(relation: str, *, source_rows: int, message: str) -> pd.DataFrame:
    """Return one GeoJSON summary error row."""

    return pd.DataFrame(
        [
            {
                "relation": relation,
                "region": "error",
                "count": 0,
                "unique_records": 0,
                "source_rows": int(source_rows),
                "message": message,
            }
        ]
    )


def _progress(enabled: bool, message: str) -> None:
    """Print one flushed progress line when enabled."""

    if enabled:
        print(message, flush=True)


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
