"""Basic context figures for Spatial-VTK tutorials and workflows.

Purpose
-------
This module draws early workflow figures that help users understand station,
event, and record coverage before calculating validation metrics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import math

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from spatial_vtk.config.labels import display_label
from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
from spatial_vtk.visualize.figure_context import title_with_subtitle
from spatial_vtk.visualize.figure_io import finish_figure
from spatial_vtk.visualize.selection import FigureSelection


def _apply_bounds(ax: plt.Axes, bounds: tuple[float, float, float, float] | None) -> None:
    """Apply optional west/east/south/north bounds to an axes.

    Parameters
    ----------
    ax
        Matplotlib axes.
    bounds
        Optional ``(west, east, south, north)`` tuple.

    Returns
    -------
    None
        The axes are modified in place.
    """

    if bounds is not None:
        west, east, south, north = [float(value) for value in bounds]
        ax.set_xlim(west, east)
        ax.set_ylim(south, north)
        _set_geographic_aspect(ax)


def plot_station_event_context(
    stations_df: pd.DataFrame,
    events_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "Station and Event Coverage",
    bounds: tuple[float, float, float, float] | None = None,
    auto_bounds_buffer_fraction: float = 0.10,
    auto_bounds_min_buffer_deg: float = 0.03,
    annotate_stations: bool = False,
    annotate_events: bool = False,
    station_label_col: str = "station",
    event_label_col: str = "event_id",
    label_fontsize: float = 6.5,
    label_offset_fraction: float = 0.012,
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    close: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot station and event locations on one context map.

    Parameters
    ----------
    stations_df
        Prepared station metadata with ``lat`` and ``lon``.
    events_df
        Prepared event metadata with ``event_lat`` and ``event_lon``.
    output_path
        Destination figure path.
    title
        Figure title.
    bounds
        Optional ``(west, east, south, north)`` map bounds.
    auto_bounds_buffer_fraction
        Fractional padding around the station/event coordinate range when
        ``bounds`` is omitted.
    auto_bounds_min_buffer_deg
        Minimum longitude/latitude padding in degrees when ``bounds`` is
        omitted.
    annotate_stations, annotate_events
        Whether to draw station and event labels next to markers.
    station_label_col, event_label_col
        Metadata columns used for station and event labels.
    label_fontsize
        Text size for optional marker annotations.
    label_offset_fraction
        Label offset as a fraction of the current map width/height.
    add_basemap
        Whether to add a contextily basemap.
    basemap_source
        Contextily provider selector.
    basemap_kwargs
        Extra keyword arguments passed to the shared basemap helper.

    Returns
    -------
    matplotlib.figure.Figure
        Figure object.
    """

    if bounds is None:
        bounds = _bounds_from_coordinate_columns(
            [
                (stations_df, "lon", "lat"),
                (events_df, "event_lon", "event_lat"),
            ],
            buffer_fraction=auto_bounds_buffer_fraction,
            min_buffer_deg=auto_bounds_min_buffer_deg,
        )
    fig, ax = plt.subplots(figsize=(8.0, 6.8), dpi=180)
    _apply_bounds(ax, bounds)
    if add_basemap:
        kwargs = dict(basemap_kwargs or {})
        add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **kwargs)
    if not stations_df.empty:
        ax.scatter(stations_df["lon"], stations_df["lat"], s=32, label="Stations", alpha=0.9, edgecolors="black", linewidths=0.25, zorder=3)
        if annotate_stations:
            _annotate_points(
                ax,
                stations_df,
                x_col="lon",
                y_col="lat",
                label_col=station_label_col,
                fontsize=label_fontsize,
                offset_fraction=label_offset_fraction,
            )
    if not events_df.empty:
        ax.scatter(events_df["event_lon"], events_df["event_lat"], s=125, marker="*", label="Events", edgecolors="black", linewidths=0.5, zorder=4)
        if annotate_events:
            _annotate_points(
                ax,
                events_df,
                x_col="event_lon",
                y_col="event_lat",
                label_col=event_label_col,
                fontsize=label_fontsize,
                offset_fraction=label_offset_fraction,
                fontweight="bold",
            )
    _apply_bounds(ax, bounds)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(title)
    ax.grid(True, alpha=0.18)
    ax.legend(frameon=True)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig, close=close)


def _coordinate_columns(df: pd.DataFrame, *, kind: str) -> tuple[str, str]:
    """Return latitude and longitude columns for station or event tables.

    Parameters
    ----------
    df
        Input table.
    kind
        Either ``"station"`` or ``"event"``.

    Returns
    -------
    tuple of str
        ``(lat_column, lon_column)``.
    """

    if kind == "event":
        candidates = (("event_lat", "event_lon"), ("lat", "lon"), ("latitude", "longitude"))
    elif kind == "station":
        candidates = (("lat", "lon"), ("station_lat", "station_lon"), ("latitude", "longitude"))
    else:
        raise ValueError("kind must be 'station' or 'event'.")
    for lat_col, lon_col in candidates:
        if {lat_col, lon_col} <= set(df.columns):
            return lat_col, lon_col
    raise KeyError(f"{kind.title()} table must include one of these coordinate column pairs: {candidates}")


def _bounds_from_coordinate_columns(
    frames: Iterable[tuple[pd.DataFrame, str, str]],
    *,
    buffer_fraction: float = 0.10,
    min_buffer_deg: float = 0.03,
) -> tuple[float, float, float, float] | None:
    """Return padded bounds from a sequence of coordinate tables."""

    lon_values: list[float] = []
    lat_values: list[float] = []
    for frame, lon_col, lat_col in frames:
        if frame.empty or lon_col not in frame.columns or lat_col not in frame.columns:
            continue
        lon_values.extend(pd.to_numeric(frame[lon_col], errors="coerce").dropna().astype(float).tolist())
        lat_values.extend(pd.to_numeric(frame[lat_col], errors="coerce").dropna().astype(float).tolist())
    if not lon_values or not lat_values:
        return None
    west, east = min(lon_values), max(lon_values)
    south, north = min(lat_values), max(lat_values)
    pad_x = max((east - west) * float(buffer_fraction), float(min_buffer_deg))
    pad_y = max((north - south) * float(buffer_fraction), float(min_buffer_deg))
    return west - pad_x, east + pad_x, south - pad_y, north + pad_y


def _annotate_points(
    ax: plt.Axes,
    df: pd.DataFrame,
    *,
    x_col: str,
    y_col: str,
    label_col: str,
    fontsize: float,
    offset_fraction: float,
    fontweight: str = "normal",
) -> None:
    """Annotate point markers using a metadata column.

    Parameters
    ----------
    ax
        Matplotlib axes.
    df
        Table containing point coordinates and labels.
    x_col, y_col
        Coordinate columns.
    label_col
        Column to draw next to each marker.
    fontsize
        Annotation text size.
    offset_fraction
        Offset as a fraction of current axis width/height.
    fontweight
        Matplotlib font weight.

    Returns
    -------
    None
        The axes are modified in place.
    """

    if label_col not in df.columns:
        raise KeyError(f"Cannot annotate points because label column '{label_col}' is missing.")
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()
    dx = (float(x_max) - float(x_min)) * float(offset_fraction)
    dy = (float(y_max) - float(y_min)) * float(offset_fraction)
    for _, row in df.iterrows():
        x = pd.to_numeric(row.get(x_col), errors="coerce")
        y = pd.to_numeric(row.get(y_col), errors="coerce")
        if not np.isfinite(x) or not np.isfinite(y):
            continue
        label = str(row[label_col])
        ax.text(
            float(x) + dx,
            float(y) + dy,
            label,
            fontsize=fontsize,
            fontweight=fontweight,
            color="black",
            ha="left",
            va="bottom",
            zorder=6,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.55, "pad": 0.8},
        )


def _set_geographic_aspect(ax: plt.Axes) -> None:
    """Preserve lon/lat proportions on map axes."""

    lat_min, lat_max = ax.get_ylim()
    lat_mid = 0.5 * (float(lat_min) + float(lat_max))
    cos_lat = math.cos(math.radians(lat_mid))
    if math.isfinite(cos_lat) and abs(cos_lat) > 1.0e-6:
        ax.set_aspect(1.0 / cos_lat, adjustable="box")


def _label_column(df: pd.DataFrame, candidates: Iterable[str], *, fallback: str) -> str:
    """Return the first available label column from a table.

    Parameters
    ----------
    df
        Input table.
    candidates
        Column names to try in order.
    fallback
        Label used when none of the candidate columns exist.

    Returns
    -------
    str
        Column name or fallback text.
    """

    for column in candidates:
        if column in df.columns:
            return column
    return fallback


def plot_study_domain_map(
    stations_df: pd.DataFrame,
    events_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str | None = None,
    bounds: tuple[float, float, float, float] | None = None,
    color_by: str | None = "magnitude",
    annotate_events: bool = False,
    add_basemap: bool = True,
    basemap_source: str = "Esri.WorldImagery",
    basemap_kwargs: dict[str, Any] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot a station/event overview map for the study domain.

    Parameters
    ----------
    stations_df
        Station metadata with latitude/longitude columns.
    events_df
        Event metadata with event latitude/longitude columns.
    output_path
        Destination figure path.
    title
        Optional figure title.
    bounds
        Optional ``(west, east, south, north)`` map bounds.
    color_by
        Optional event column used for marker color.
    annotate_events
        Whether to label event markers by event id.
    add_basemap
        Whether to draw a contextily basemap.
    basemap_source
        Contextily provider selector.
    basemap_kwargs
        Extra keyword arguments passed to the shared basemap helper.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    station_lat, station_lon = _coordinate_columns(stations_df, kind="station") if not stations_df.empty else ("lat", "lon")
    event_lat, event_lon = _coordinate_columns(events_df, kind="event") if not events_df.empty else ("event_lat", "event_lon")
    fig, ax = plt.subplots(figsize=(9.0, 7.2), dpi=180)
    if bounds is None:
        lon_values: list[float] = []
        lat_values: list[float] = []
        if not stations_df.empty:
            lon_values.extend(pd.to_numeric(stations_df[station_lon], errors="coerce").dropna().astype(float).tolist())
            lat_values.extend(pd.to_numeric(stations_df[station_lat], errors="coerce").dropna().astype(float).tolist())
        if not events_df.empty:
            lon_values.extend(pd.to_numeric(events_df[event_lon], errors="coerce").dropna().astype(float).tolist())
            lat_values.extend(pd.to_numeric(events_df[event_lat], errors="coerce").dropna().astype(float).tolist())
        if lon_values and lat_values:
            lon_min, lon_max = min(lon_values), max(lon_values)
            lat_min, lat_max = min(lat_values), max(lat_values)
            lon_pad = max((lon_max - lon_min) * 0.12, 0.05)
            lat_pad = max((lat_max - lat_min) * 0.12, 0.05)
            bounds = (lon_min - lon_pad, lon_max + lon_pad, lat_min - lat_pad, lat_max + lat_pad)
    _apply_bounds(ax, bounds)
    if add_basemap:
        kwargs = dict(basemap_kwargs or {})
        add_contextily_basemap(ax, crs="EPSG:4326", primary_source=basemap_source, **kwargs)
    if not stations_df.empty:
        station_label_col = _label_column(stations_df, ("network",), fallback="")
        if station_label_col in stations_df.columns:
            for label, subset in stations_df.groupby(station_label_col, dropna=False):
                ax.scatter(
                    subset[station_lon],
                    subset[station_lat],
                    s=36,
                    marker="^",
                    alpha=0.92,
                    edgecolors="black",
                    linewidths=0.3,
                    label=f"Station {label}" if str(label).strip() else "Stations",
                    zorder=4,
                )
        else:
            ax.scatter(stations_df[station_lon], stations_df[station_lat], s=36, marker="^", alpha=0.92, edgecolors="black", linewidths=0.3, label="Stations", zorder=4)
    if not events_df.empty:
        event_color = events_df[color_by] if color_by and color_by in events_df.columns else "#f28e2b"
        events = ax.scatter(events_df[event_lon], events_df[event_lat], c=event_color, cmap="autumn_r" if color_by in events_df.columns else None, s=92, marker="*", edgecolors="black", linewidths=0.5, label="Events", zorder=5)
        if color_by and color_by in events_df.columns:
            fig.colorbar(events, ax=ax, label=display_label(color_by))
        if annotate_events:
            event_id_col = _label_column(events_df, ("event_id", "id", "name"), fallback="")
            if event_id_col in events_df.columns:
                for _, row in events_df.iterrows():
                    ax.text(float(row[event_lon]) + 0.01, float(row[event_lat]) + 0.01, str(row[event_id_col]), fontsize=7.0, zorder=6)
    _apply_bounds(ax, bounds)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(title or f"Study Domain ({len(stations_df)} stations, {len(events_df)} events)")
    ax.grid(True, alpha=0.18)
    ax.legend(frameon=True, fontsize=8, loc="best")
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_station_coverage(
    event_station_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "Station Coverage",
    max_stations: int = 40,
    showfig: bool | None = None,
    savefig: bool | None = None,
    close: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot event counts by station.

    Parameters
    ----------
    event_station_df
        Prepared event-station table.
    output_path
        Destination figure path.
    title
        Figure title.
    max_stations
        Maximum number of stations to show.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    fig, ax = plt.subplots(figsize=(8.0, 4.0), dpi=180)
    if event_station_df.empty:
        ax.text(0.5, 0.5, "No event-station rows", ha="center", va="center", transform=ax.transAxes)
    else:
        counts = event_station_df.groupby("station", as_index=False).agg(event_count=("event_id", "nunique"))
        counts = counts.sort_values(["event_count", "station"], ascending=[False, True]).head(int(max_stations))
        ax.bar(counts["station"], counts["event_count"], color="#4c78a8")
        ax.set_xlabel("Station")
        ax.set_ylabel("Event count")
        ax.tick_params(axis="x", rotation=75)
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.25)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig, close=close)


def plot_event_coverage(
    event_station_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "Event Coverage",
    showfig: bool | None = None,
    savefig: bool | None = None,
    close: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot station counts by event.

    Parameters
    ----------
    event_station_df
        Prepared event-station table.
    output_path
        Destination figure path.
    title
        Figure title.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    fig, ax = plt.subplots(figsize=(7.0, 4.0), dpi=180)
    if event_station_df.empty:
        ax.text(0.5, 0.5, "No event-station rows", ha="center", va="center", transform=ax.transAxes)
    else:
        counts = event_station_df.groupby("event_id", as_index=False).agg(station_count=("station", "nunique"))
        counts = counts.sort_values("event_id")
        ax.bar(counts["event_id"], counts["station_count"], color="#59a14f")
        ax.set_xlabel("Event")
        ax.set_ylabel("Station count")
        ax.tick_params(axis="x", rotation=45)
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.25)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig, close=close)


def build_record_coverage_table(
    event_station_df: pd.DataFrame,
    *,
    observed_start_col: str = "observed_start_s",
    observed_end_col: str = "observed_end_s",
    synthetic_start_col: str = "synthetic_start_s",
    synthetic_end_col: str = "synthetic_end_s",
) -> pd.DataFrame:
    """Validate and normalize a measured record-coverage table.

    Parameters
    ----------
    event_station_df
        Event-station records with measured observed/synthetic start and end
        columns in seconds relative to event origin.
    observed_start_col, observed_end_col
        Observed record start/end columns in seconds.
    synthetic_start_col, synthetic_end_col
        Synthetic record start/end columns in seconds.

    Returns
    -------
    pandas.DataFrame
        Validated record table with measured timing columns and durations.
    """

    records = event_station_df.copy()
    required = {"event_id", "station", observed_start_col, observed_end_col, synthetic_start_col, synthetic_end_col}
    missing = sorted(required - set(records.columns))
    if missing:
        raise KeyError(
            "Record coverage requires measured timing columns. "
            f"Missing columns: {missing}. Build this table with "
            "build_record_coverage_table_from_trace_metadata(...) or "
            "build_record_coverage_table_from_qc(...)."
        )
    out = pd.DataFrame()
    out["event_id"] = records["event_id"].astype(str)
    out["station"] = records["station"].astype(str).str.upper()
    if "distance_km" in records.columns:
        out["distance_km"] = pd.to_numeric(records["distance_km"], errors="coerce")
    for column in ("event_name", "event_title", "event_place"):
        if column in records.columns:
            out[column] = records[column]
    for source, start_col, end_col in (
        ("observed", observed_start_col, observed_end_col),
        ("synthetic", synthetic_start_col, synthetic_end_col),
    ):
        out[f"{source}_start_s"] = pd.to_numeric(records[start_col], errors="coerce")
        out[f"{source}_end_s"] = pd.to_numeric(records[end_col], errors="coerce")
        out[f"{source}_duration_s"] = out[f"{source}_end_s"] - out[f"{source}_start_s"]
    _validate_record_coverage_timing(out)
    sort_cols = [column for column in ("event_id", "distance_km", "station") if column in out.columns]
    return out.sort_values(sort_cols, na_position="last").reset_index(drop=True)


def build_record_coverage_table_from_trace_metadata(
    trace_metadata_df: pd.DataFrame | str | Path,
    *,
    event_station_df: pd.DataFrame | str | Path | None = None,
    component: str | None = None,
    observed_source: str = "observed",
    synthetic_source: str = "synthetic",
    source_type_col: str = "source_type",
    on_missing_source: str = "drop",
) -> pd.DataFrame:
    """Build paired record coverage from processed trace metadata.

    Parameters
    ----------
    trace_metadata_df
        Trace metadata table from preprocessing with event, station, source,
        start time, and end time columns.
    event_station_df
        Event-station metadata with event origin time in ``start`` plus
        optional distance and readable event-label columns.
    component
        Optional component to select before pairing observed/synthetic traces.
    observed_source, synthetic_source
        Source labels used for observed and synthetic rows.
    source_type_col
        Column naming the waveform source. If absent, the source is inferred
        from the trace metadata ``source`` or file path columns.
    on_missing_source
        ``"drop"`` keeps complete observed/synthetic pairs only. ``"raise"``
        raises when a selected event-station record is missing either source.

    Returns
    -------
    pandas.DataFrame
        Coverage table with measured observed/synthetic start, end, and
        duration columns in seconds relative to event origin.
    """

    traces = _read_table_like(trace_metadata_df).copy()
    if traces.empty:
        return pd.DataFrame()
    required = {"event_id", "station", "starttime", "endtime"}
    missing = sorted(required - set(traces.columns))
    if missing:
        raise KeyError(f"trace_metadata_df is missing required columns: {missing}")
    if event_station_df is None:
        raise ValueError("event_station_df is required so trace times can be measured relative to event origin.")
    if component is not None and "component" in traces.columns:
        traces = traces[traces["component"].astype(str).str.upper().eq(str(component).upper())].copy()
    if traces.empty:
        return pd.DataFrame()

    metadata = _coverage_metadata(event_station_df)
    rows: list[dict[str, object]] = []
    dropped_missing_source = 0
    observed_key = str(observed_source).strip().lower()
    synthetic_key = str(synthetic_source).strip().lower()
    missing_mode = str(on_missing_source).strip().lower()
    if missing_mode not in {"drop", "raise"}:
        raise ValueError("on_missing_source must be 'drop' or 'raise'.")
    for (event_id, station), group in traces.groupby(["event_id", "station"], dropna=False, sort=False):
        event_text = str(event_id)
        station_text = str(station).upper()
        meta = _coverage_metadata_lookup(metadata, event_text, station_text)
        if meta is None:
            raise ValueError(
                f"No event-station metadata found for event {event_text!r}, station {station_text!r}. "
                "Provide event_station_df with matching event_id/station rows and event origin times."
            )
        origin_value = _first_present(meta, ("start", "time", "origin_time"))
        origin = _coverage_timestamp(origin_value, f"event origin for {event_text}/{station_text}")
        row: dict[str, object] = {"event_id": event_text, "station": station_text}
        row.update({key: value for key, value in meta.items() if key != "start"})
        missing_pair_source = False
        for source_label, prefix in ((observed_key, "observed"), (synthetic_key, "synthetic")):
            source_rows = group[group.apply(lambda item: _coverage_source_type(item, source_type_col=source_type_col) == source_label, axis=1)]
            if source_rows.empty:
                if missing_mode == "raise":
                    raise ValueError(f"Missing {prefix} trace timing for event {event_text!r}, station {station_text!r}.")
                missing_pair_source = True
                break
            start_values = [
                _seconds_between(_coverage_timestamp(value, "trace starttime"), origin)
                for value in source_rows["starttime"].tolist()
            ]
            end_values = [
                _seconds_between(_coverage_timestamp(value, "trace endtime"), origin)
                for value in source_rows["endtime"].tolist()
            ]
            row[f"{prefix}_start_s"] = float(np.nanmin(start_values))
            row[f"{prefix}_end_s"] = float(np.nanmax(end_values))
            row[f"{prefix}_duration_s"] = row[f"{prefix}_end_s"] - row[f"{prefix}_start_s"]
        if missing_pair_source:
            dropped_missing_source += 1
            continue
        rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        out.attrs["dropped_missing_source"] = dropped_missing_source
        return out
    _validate_record_coverage_timing(out)
    sort_cols = [column for column in ("event_id", "distance_km", "station") if column in out.columns]
    out = out.sort_values(sort_cols, na_position="last").reset_index(drop=True)
    out.attrs["dropped_missing_source"] = dropped_missing_source
    return out


def build_record_coverage_table_from_qc(
    trace_qc_df: pd.DataFrame | str | Path,
    *,
    event_station_df: pd.DataFrame | str | Path | None = None,
    component: str | None = None,
    passband: str | None = None,
    observed_source: str = "observed",
    synthetic_source: str = "synthetic",
) -> pd.DataFrame:
    """Build a paired record-coverage table from waveform QC rows.

    Parameters
    ----------
    trace_qc_df
        Waveform QC table with one row per source/event/station/component/
        passband and timing columns such as ``trace_start_s`` and
        ``trace_end_s``.
    event_station_df
        Optional event-station metadata used to add distance and readable
        event labels.
    component
        Optional component to select before pairing source rows.
    passband
        Optional passband label to select before pairing source rows.
    observed_source, synthetic_source
        Source labels used for observed and synthetic rows.

    Returns
    -------
    pandas.DataFrame
        Coverage table with observed/synthetic start, end, and duration
        columns accepted by :func:`plot_record_coverage`.
    """

    qc = _read_table_like(trace_qc_df).copy()
    if qc.empty:
        return pd.DataFrame()
    required = {"source", "event_id", "station"}
    missing = sorted(required - set(qc.columns))
    if missing:
        raise KeyError(f"trace_qc_df is missing required columns: {missing}")
    if component is not None and "component" in qc.columns:
        qc = qc[qc["component"].astype(str).str.upper().eq(str(component).upper())].copy()
    if passband is not None and "passband" in qc.columns:
        target = _coverage_label_key(passband)
        qc = qc[qc["passband"].map(_coverage_label_key).eq(target)].copy()
    if qc.empty:
        return pd.DataFrame()

    metadata = _coverage_metadata(event_station_df)
    rows: list[dict[str, object]] = []
    for (event_id, station), group in qc.groupby(["event_id", "station"], dropna=False, sort=False):
        row: dict[str, object] = {"event_id": event_id, "station": str(station).upper()}
        meta = _coverage_metadata_lookup(metadata, str(event_id), str(station).upper()) or {}
        row.update(meta)
        for source_label, prefix in ((observed_source, "observed"), (synthetic_source, "synthetic")):
            source_rows = group[group["source"].astype(str).str.lower().eq(str(source_label).lower())]
            if source_rows.empty:
                continue
            source_row = source_rows.iloc[0]
            row[f"{prefix}_start_s"] = _first_numeric(source_row, ("trace_start_s", "start_rel_s"))
            row[f"{prefix}_end_s"] = _first_numeric(source_row, ("trace_end_s", "end_rel_s"))
            row[f"{prefix}_duration_s"] = _first_numeric(source_row, ("trace_duration_s", "record_length_s"))
        rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    _validate_record_coverage_timing(out)
    sort_cols = [column for column in ("event_id", "distance_km", "station") if column in out.columns]
    return out.sort_values(sort_cols, na_position="last").reset_index(drop=True)


def plot_record_coverage(
    records_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    event_col: str = "event_id",
    event_label_col: str = "event_name",
    station_col: str = "station",
    distance_col: str = "distance_km",
    observed_start_col: str = "observed_start_s",
    observed_end_col: str = "observed_end_s",
    synthetic_start_col: str = "synthetic_start_s",
    synthetic_end_col: str = "synthetic_end_s",
    include_event_in_label: bool = True,
    max_records: int | None = 40,
    title: str = "Record Coverage",
    showfig: bool | None = None,
    savefig: bool | None = None,
    close: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot observed and synthetic record time coverage by station.

    Parameters
    ----------
    records_df
        Table with one row per event-station record.
    output_path
        Destination figure path.
    event_col, event_label_col
        Event identifier and optional readable event label columns.
    station_col
        Station label column.
    distance_col
        Optional distance column used for sorting and labels.
    observed_start_col, observed_end_col
        Observed record start/end columns in seconds.
    synthetic_start_col, synthetic_end_col
        Synthetic record start/end columns in seconds.
    include_event_in_label
        Whether y-axis labels include event labels in addition to stations.
    max_records
        Maximum rows to draw.
    title
        Figure title.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    df = records_df.copy()
    if station_col not in df.columns:
        raise KeyError(f"records_df must include a '{station_col}' column.")
    required_timing = [observed_start_col, observed_end_col, synthetic_start_col, synthetic_end_col]
    missing_timing = [column for column in required_timing if column not in df.columns]
    if missing_timing:
        raise KeyError(
            "Record coverage plotting requires measured timing columns. "
            f"Missing columns: {missing_timing}. Build the table with "
            "build_record_coverage_table_from_trace_metadata(...) or "
            "build_record_coverage_table_from_qc(...)."
        )
    _validate_record_coverage_timing(
        df,
        observed_start_col=observed_start_col,
        observed_end_col=observed_end_col,
        synthetic_start_col=synthetic_start_col,
        synthetic_end_col=synthetic_end_col,
    )
    if distance_col in df.columns:
        df[distance_col] = pd.to_numeric(df[distance_col], errors="coerce")
        sort_cols = [column for column in (event_col, distance_col, station_col) if column in df.columns]
        df = df.sort_values(sort_cols, na_position="last")
    else:
        sort_cols = [column for column in (event_col, station_col) if column in df.columns]
        df = df.sort_values(sort_cols)
    if max_records is not None:
        df = df.head(int(max_records))
    height = max(4.2, 0.34 * max(len(df), 1) + 1.5)
    fig, ax = plt.subplots(figsize=(10.0, height), dpi=180)
    if df.empty:
        ax.text(0.5, 0.5, "No record rows", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        ax.set_title(title)
        return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig, close=close)

    y_positions = np.arange(len(df), dtype=float)
    y_labels: list[str] = []
    max_end = 0.0
    min_start = 0.0
    for idx, (_, row) in enumerate(df.iterrows()):
        y_labels.append(
            _coverage_row_label(
                row,
                station_col=station_col,
                event_col=event_col,
                event_label_col=event_label_col,
                distance_col=distance_col if distance_col in df.columns else None,
                include_event=include_event_in_label,
            )
        )
        coverage_specs = [
            ("Observed", observed_start_col, observed_end_col, -0.14, "black"),
            ("Synthetic", synthetic_start_col, synthetic_end_col, 0.14, "#d04a35"),
        ]
        for _name, start_col, end_col, offset, color in coverage_specs:
            start = float(row[start_col])
            end = float(row[end_col])
            min_start = min(min_start, start)
            max_end = max(max_end, end)
            ax.hlines(y_positions[idx] + offset, start, end, color=color, linewidth=2.3)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels, fontsize=8)
    ax.set_xlabel("Seconds since event origin")
    ax.set_title(title)
    span = max(max_end - min_start, 1.0)
    ax.set_xlim(left=min_start - 0.04 * span, right=max_end + 0.04 * span)
    ax.grid(True, axis="x", alpha=0.22)
    ax.invert_yaxis()
    ax.legend(
        handles=[
            Line2D([0], [0], color="black", linewidth=2.3, label="Observed"),
            Line2D([0], [0], color="#d04a35", linewidth=2.3, label="Synthetic"),
        ],
        loc="best",
    )
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig, close=close)


def _validate_record_coverage_timing(
    table: pd.DataFrame,
    *,
    observed_start_col: str = "observed_start_s",
    observed_end_col: str = "observed_end_s",
    synthetic_start_col: str = "synthetic_start_s",
    synthetic_end_col: str = "synthetic_end_s",
) -> None:
    """Raise a clear error when record coverage timing is absent or invalid."""

    required = [observed_start_col, observed_end_col, synthetic_start_col, synthetic_end_col]
    missing = [column for column in required if column not in table.columns]
    if missing:
        raise KeyError(
            "Record coverage requires measured observed and synthetic start/end columns. "
            f"Missing columns: {missing}."
        )
    numeric = table[required].apply(pd.to_numeric, errors="coerce")
    bad_columns = [column for column in required if numeric[column].isna().any()]
    if bad_columns:
        raise ValueError(f"Record coverage timing has non-finite values in columns: {bad_columns}")
    bad_observed = numeric[observed_end_col] < numeric[observed_start_col]
    bad_synthetic = numeric[synthetic_end_col] < numeric[synthetic_start_col]
    if bool((bad_observed | bad_synthetic).any()):
        raise ValueError("Record coverage timing has one or more rows where end time is before start time.")


def _coverage_row_label(
    row: pd.Series,
    *,
    station_col: str,
    event_col: str,
    event_label_col: str,
    distance_col: str | None,
    include_event: bool,
) -> str:
    """Build a compact y-axis label for one event-station record."""

    station = str(row.get(station_col, "")).upper()
    parts = [station]
    if include_event:
        event_value = row.get(event_label_col)
        if pd.isna(event_value) or str(event_value).strip() == "":
            event_value = row.get(event_col, "")
        if str(event_value).strip():
            parts.append(_short_label(event_value, max_chars=34))
    label = " | ".join(parts)
    if distance_col and distance_col in row.index and pd.notna(row.get(distance_col)):
        label = f"{label} ({float(row[distance_col]):.1f} km)"
    return label


def _short_label(value: object, *, max_chars: int = 34) -> str:
    """Return a readable label clipped to a maximum character count."""

    text = " ".join(str(value).strip().split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 1].rstrip()}..."


def _read_table_like(value: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Read a dataframe-like input into a dataframe copy."""

    if isinstance(value, pd.DataFrame):
        return value.copy()
    path = Path(value).expanduser()
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _coverage_label_key(value: object) -> str:
    """Normalize labels for lightweight passband matching."""

    text = str(value).strip().lower().replace("seconds", "sec")
    return " ".join(text.split())


def _coverage_metadata(event_station_df: pd.DataFrame | str | Path | None) -> dict[tuple[str, str], dict[str, object]]:
    """Return event-station metadata keyed by event and station."""

    if event_station_df is None:
        return {}
    table = _read_table_like(event_station_df)
    if table.empty or not {"event_id", "station"} <= set(table.columns):
        return {}
    keep = [
        column
        for column in (
            "event_id",
            "station",
            "distance_km",
            "event_name",
            "event_title",
            "event_place",
            "start",
            "time",
            "origin_time",
            "network",
            "lat",
            "lon",
            "station_lat",
            "station_lon",
        )
        if column in table.columns
    ]
    metadata: dict[tuple[str, str], dict[str, object]] = {}
    for _, row in table[keep].drop_duplicates(["event_id", "station"]).iterrows():
        event_key = _coverage_event_key(row["event_id"])
        values = {column: row[column] for column in keep if column not in {"event_id", "station"}}
        for station_key in _coverage_station_aliases(row["station"]):
            metadata.setdefault((event_key, station_key), values)
    return metadata


def _coverage_metadata_lookup(
    metadata: dict[tuple[str, str], dict[str, object]],
    event_id: object,
    station: object,
) -> dict[str, object] | None:
    """Return event-station metadata using tolerant station aliases."""

    event_key = _coverage_event_key(event_id)
    for station_key in _coverage_station_aliases(station):
        meta = metadata.get((event_key, station_key))
        if meta is not None:
            return meta
    return None


def _coverage_event_key(value: object) -> str:
    """Normalize event identifiers for record-coverage matching."""

    return str(value).strip()


def _coverage_station_aliases(value: object) -> tuple[str, ...]:
    """Return common station aliases for matching trace metadata to tables."""

    text = str(value).strip().upper()
    aliases: list[str] = []
    for candidate in (text, text.split(".")[-1]):
        candidate = candidate.strip()
        if candidate and candidate not in aliases:
            aliases.append(candidate)
        numeric = candidate.lstrip("0")
        if numeric and numeric.isdigit() and numeric not in aliases:
            aliases.append(numeric)
    return tuple(aliases)


def _coverage_source_type(row: pd.Series, *, source_type_col: str = "source_type") -> str:
    """Return the observed/synthetic source type for one trace metadata row."""

    if source_type_col in row.index and pd.notna(row.get(source_type_col)):
        text = str(row.get(source_type_col)).strip().lower()
        if text:
            return text
    for column in ("source", "output_file", "input_file"):
        if column not in row.index or pd.isna(row.get(column)):
            continue
        parts = str(row.get(column)).replace("\\", "/").lower().split("/")
        if "observed" in parts or any(part.startswith("observed") for part in parts):
            return "observed"
        if "synthetic" in parts or "synthetics" in parts or any(part.startswith("synthetic") for part in parts):
            return "synthetic"
    return ""


def _coverage_timestamp(value: object, label: str) -> pd.Timestamp:
    """Parse a timestamp value and raise a clear error if it is missing."""

    if value is None or pd.isna(value):
        raise ValueError(f"Missing {label}.")
    timestamp = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(timestamp):
        raise ValueError(f"Could not parse {label}: {value!r}")
    return timestamp


def _first_present(mapping: dict[str, object], columns: tuple[str, ...]) -> object:
    """Return the first non-empty value from a metadata mapping."""

    for column in columns:
        value = mapping.get(column)
        if value is not None and not pd.isna(value) and str(value).strip() != "":
            return value
    return None


def _seconds_between(value: pd.Timestamp, origin: pd.Timestamp) -> float:
    """Return seconds between two parsed timestamps."""

    return float((value - origin).total_seconds())


def _first_numeric(row: pd.Series, columns: tuple[str, ...]) -> float:
    """Return the first finite numeric value from a row."""

    for column in columns:
        if column in row.index and pd.notna(row.get(column)):
            value = pd.to_numeric(row.get(column), errors="coerce")
            if pd.notna(value):
                return float(value)
    return float("nan")


def _row_sample_interval(row: pd.Series, column: str | None, default: float = 1.0) -> float:
    """Return a finite positive sample interval from a dataframe row.

    Parameters
    ----------
    row
        Record row that may contain sample-interval metadata.
    column
        Column name containing the sample interval in seconds.
    default
        Fallback sample interval.

    Returns
    -------
    float
        Sample interval in seconds.
    """

    if column and column in row.index and pd.notna(row.get(column)):
        try:
            value = float(row.get(column))
        except (TypeError, ValueError):
            value = float(default)
        if np.isfinite(value) and value > 0.0:
            return value
    return float(default)


def _row_time_offset(row: pd.Series, column: str | None, default: float = 0.0) -> float:
    """Return a finite trace time offset from a dataframe row.

    Parameters
    ----------
    row
        Record row that may contain time-offset metadata.
    column
        Column containing seconds relative to the event origin.
    default
        Fallback offset in seconds.

    Returns
    -------
    float
        Time offset in seconds.
    """

    if column and column in row.index and pd.notna(row.get(column)):
        try:
            value = float(row.get(column))
        except (TypeError, ValueError):
            value = float(default)
        if np.isfinite(value):
            return value
    return float(default)


def _array_from_trace_like(value: Any, *, default_dt: float = 1.0) -> tuple[np.ndarray, float]:
    """Return data and sample interval from an array-like or ObsPy-like trace.

    Parameters
    ----------
    value
        Numeric array or trace object with ``data`` and optional ``stats``.
    default_dt
        Sample interval used when an array has no embedded metadata.

    Returns
    -------
    tuple
        ``(data, dt_seconds)``.
    """

    if hasattr(value, "data"):
        data = np.asarray(value.data, dtype=float)
        stats = getattr(value, "stats", None)
        dt = getattr(stats, "delta", None)
        if dt is None:
            sampling_rate = getattr(stats, "sampling_rate", None)
            dt = 1.0 / float(sampling_rate) if sampling_rate else default_dt
        return data, float(dt)
    return np.asarray(value, dtype=float), float(default_dt)


def _normalize_waveform(data: np.ndarray) -> np.ndarray:
    """Normalize one waveform by peak absolute amplitude.

    Parameters
    ----------
    data
        Input waveform.

    Returns
    -------
    numpy.ndarray
        Normalized waveform, or zeros when input is not usable.
    """

    out = np.asarray(data, dtype=float)
    peak = float(np.nanmax(np.abs(out))) if out.size else 0.0
    if not np.isfinite(peak) or peak <= 0.0:
        return np.zeros_like(out, dtype=float)
    return out / peak


def plot_event_trace_comparison(
    records_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    observed_col: str = "observed",
    synthetic_col: str = "synthetic",
    dt_col: str = "dt",
    synthetic_dt_col: str = "synthetic_dt",
    observed_time_offset_col: str = "observed_time_offset_s",
    synthetic_time_offset_col: str = "synthetic_time_offset_s",
    station_col: str = "station",
    component_col: str | None = "component",
    selection: FigureSelection | None = None,
    distance_col: str = "distance_km",
    distance_limit_km: float | None = None,
    max_records: int | None = 30,
    normalize: bool = True,
    amplitude_gain: float | str = 1.0,
    amplitude_gain_multiplier: float = 1.0,
    time_limit_s: float | None = 60.0,
    title: str = "Observed and Synthetic Trace Comparison",
    filter_label: str | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot observed and synthetic traces sorted by source distance.

    Parameters
    ----------
    records_df
        Table with observed and synthetic waveform arrays or ObsPy-like traces.
    output_path
        Destination figure path.
    observed_col, synthetic_col
        Waveform columns.
    dt_col, synthetic_dt_col
        Row-level sample interval columns for array-backed observed and
        synthetic waveforms.
    observed_time_offset_col, synthetic_time_offset_col
        Optional columns giving the trace start time in seconds relative to the
        event origin. When present, the x-axis is event-origin-relative.
    station_col
        Station label column.
    component_col
        Optional component grouping column.
    distance_col
        Optional distance column used for vertical position.
    distance_limit_km
        Optional maximum source-to-station distance to include.
    max_records
        Maximum rows per component.
    normalize
        Whether to normalize each waveform before plotting.
    amplitude_gain
        Single global gain applied to every plotted waveform after optional
        normalization. Use values greater than 1 to inspect unnormalized traces
        while preserving observed/synthetic relative amplitudes.
    amplitude_gain_multiplier
        Additional multiplier applied after resolving ``amplitude_gain``. This
        is useful with ``amplitude_gain="auto"`` when traces should be drawn
        larger while preserving relative amplitudes.
    time_limit_s
        Optional maximum seconds to display from each trace start.
    title
        Figure title.
    filter_label
        Optional second title line describing any bandpass or lowpass filter.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    required = {observed_col, synthetic_col, station_col}
    missing = required - set(records_df.columns)
    if missing:
        raise KeyError(f"records_df is missing required columns: {sorted(missing)}")
    df = selection.apply(records_df, component_col=component_col or "component") if selection is not None else records_df.copy()
    components = [None]
    if component_col and component_col in df.columns:
        components = sorted(df[component_col].dropna().astype(str).unique().tolist()) or [None]
    has_time_offsets = observed_time_offset_col in df.columns or synthetic_time_offset_col in df.columns
    fig, axes = plt.subplots(1, len(components), figsize=(max(6.0, 4.8 * len(components)), 6.4), dpi=180, sharey=True)
    axes = np.atleast_1d(axes)
    for ax, component in zip(axes, components):
        subset = df if component is None else df.loc[df[component_col].astype(str) == str(component)].copy()
        if distance_col in subset.columns:
            subset[distance_col] = pd.to_numeric(subset[distance_col], errors="coerce")
            if distance_limit_km is not None:
                subset = subset.loc[subset[distance_col].le(float(distance_limit_km))].copy()
            subset = subset.sort_values([distance_col, station_col], na_position="last")
        else:
            subset = subset.sort_values(station_col)
        if max_records is not None:
            subset = subset.head(int(max_records))
        if subset.empty:
            ax.text(0.5, 0.5, "No trace rows", ha="center", va="center", transform=ax.transAxes)
            continue
        y_values = subset[distance_col].to_numpy(dtype=float) if distance_col in subset.columns else np.arange(len(subset), dtype=float)
        if not np.isfinite(y_values).all():
            y_values = np.arange(len(subset), dtype=float)
        unique_y = np.unique(np.sort(y_values))
        diffs = np.diff(unique_y)
        diffs = diffs[diffs > 0]
        half_height = 0.38 * float(np.median(diffs)) if len(diffs) else 0.45
        half_height = max(half_height, 0.35)
        gain = _resolve_trace_comparison_gain(
            subset,
            observed_col,
            synthetic_col,
            normalize=normalize,
            amplitude_gain=amplitude_gain,
            amplitude_gain_multiplier=amplitude_gain_multiplier,
        )
        max_time = 0.0
        for row_idx, (_, row) in enumerate(subset.iterrows()):
            obs_default_dt = _row_sample_interval(row, dt_col, 1.0)
            syn_default_dt = _row_sample_interval(row, synthetic_dt_col, obs_default_dt)
            obs_data, obs_dt = _array_from_trace_like(row[observed_col], default_dt=obs_default_dt)
            syn_data, syn_dt = _array_from_trace_like(row[synthetic_col], default_dt=syn_default_dt)
            if len(obs_data) <= 1 or len(syn_data) <= 1:
                continue
            obs_offset = _row_time_offset(row, observed_time_offset_col, 0.0)
            syn_offset = _row_time_offset(row, synthetic_time_offset_col, 0.0)
            obs_time = obs_offset + np.arange(len(obs_data), dtype=float) * float(obs_dt)
            syn_time = syn_offset + np.arange(len(syn_data), dtype=float) * float(syn_dt)
            if time_limit_s is not None:
                limit = float(time_limit_s)
                obs_mask = (obs_time >= 0.0) & (obs_time <= limit)
                syn_mask = (syn_time >= 0.0) & (syn_time <= limit)
                obs_data = obs_data[obs_mask]
                syn_data = syn_data[syn_mask]
                obs_time = obs_time[obs_mask]
                syn_time = syn_time[syn_mask]
            if len(obs_data) <= 1 or len(syn_data) <= 1:
                continue
            if normalize:
                obs_data = _normalize_waveform(obs_data)
                syn_data = _normalize_waveform(syn_data)
            obs_data = obs_data * gain
            syn_data = syn_data * gain
            max_time = max(max_time, float(obs_time[-1]), float(syn_time[-1]))
            y0 = float(y_values[row_idx])
            ax.plot(obs_time, y0 + obs_data * half_height, color="black", linewidth=0.75, label="Observed" if row_idx == 0 else None)
            ax.plot(syn_time, y0 + syn_data * half_height, color="#d04a35", linewidth=0.75, alpha=0.9, label="Synthetic" if row_idx == 0 else None)
        ax.set_title(f"{component} component" if component is not None else "Traces")
        ax.set_xlabel("Seconds since event origin" if has_time_offsets else "Seconds since trace start")
        ax.set_xlim(0.0, max(max_time, 1.0))
        if distance_col in subset.columns and distance_limit_km is not None:
            ax.set_ylim(bottom=0.0, top=float(distance_limit_km))
        ax.grid(True, alpha=0.18)
        if distance_col not in subset.columns:
            ax.set_yticks(y_values)
            ax.set_yticklabels(subset[station_col].astype(str).tolist(), fontsize=7)
    axes[0].set_ylabel("Distance (km)" if distance_col in df.columns else "Station")
    axes[0].legend(loc="upper right")
    fig.suptitle(title_with_subtitle(title, filter_label), y=0.99)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _resolve_trace_comparison_gain(
    subset: pd.DataFrame,
    observed_col: str,
    synthetic_col: str,
    *,
    normalize: bool,
    amplitude_gain: float | str,
    amplitude_gain_multiplier: float = 1.0,
) -> float:
    """Return a global waveform gain for one trace comparison panel.

    Parameters
    ----------
    subset
        Rows being plotted in one panel.
    observed_col, synthetic_col
        Waveform columns.
    normalize
        Whether the caller will normalize each trace before plotting.
    amplitude_gain
        Numeric gain or ``"auto"`` for percentile-based scaling.
    amplitude_gain_multiplier
        Multiplier applied to the resolved gain.

    Returns
    -------
    float
        Gain applied to all observed and synthetic traces in the panel.
    """

    if isinstance(amplitude_gain, str) and amplitude_gain.strip().lower() == "auto":
        multiplier = _positive_float(amplitude_gain_multiplier, default=1.0)
        if normalize:
            return multiplier
        peaks: list[float] = []
        for _, row in subset.iterrows():
            for column in (observed_col, synthetic_col):
                try:
                    data, _dt = _array_from_trace_like(row[column], default_dt=1.0)
                except Exception:
                    continue
                if data.size:
                    peak = float(np.nanmax(np.abs(data)))
                    if np.isfinite(peak) and peak > 0.0:
                        peaks.append(peak)
        if not peaks:
            return 1.0
        reference = float(np.nanpercentile(peaks, 90.0))
        gain = 1.0 / reference if np.isfinite(reference) and reference > 0.0 else 1.0
        return gain * multiplier
    try:
        gain = float(amplitude_gain)
    except Exception:
        gain = 1.0
    gain = gain if np.isfinite(gain) and gain > 0.0 else 1.0
    return gain * _positive_float(amplitude_gain_multiplier, default=1.0)


def _positive_float(value: object, *, default: float) -> float:
    """Return a positive float or a default."""

    try:
        out = float(value)
    except Exception:
        return default
    return out if np.isfinite(out) and out > 0.0 else default


def _fit_inverse_distance(distance: np.ndarray, amplitude: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    """Fit a simple amplitude-versus-inverse-distance line.

    Parameters
    ----------
    distance
        Distance values in kilometers.
    amplitude
        Amplitude values.

    Returns
    -------
    tuple or None
        ``(distance_fit, amplitude_fit)`` when enough valid points exist.
    """

    x = np.asarray(distance, dtype=float)
    y = np.asarray(amplitude, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y) & (x > 0.0)
    if int(mask.sum()) < 3:
        return None
    x_valid = x[mask]
    y_valid = y[mask]
    inv = 1.0 / x_valid
    coeffs = np.polyfit(inv, y_valid, 1)
    x_fit = np.linspace(float(x_valid.min()), float(x_valid.max()), 200)
    y_fit = np.polyval(coeffs, 1.0 / x_fit)
    return x_fit, y_fit


def plot_distance_amplitude_diagnostics(
    records_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    distance_col: str = "distance_km",
    observed_col: str = "observed_peak_abs",
    synthetic_col: str = "synthetic_peak_abs",
    component_col: str | None = "component",
    selection: FigureSelection | None = None,
    event_col: str | None = "event_id",
    title: str = "Distance Versus Amplitude",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot amplitude decay diagnostics for observed and synthetic records.

    Parameters
    ----------
    records_df
        Table with distance and amplitude columns.
    output_path
        Destination figure path.
    distance_col
        Distance column in kilometers.
    observed_col, synthetic_col
        Observed and synthetic amplitude columns.
    component_col
        Optional component facet column.
    event_col
        Optional event color/grouping column.
    title
        Figure title.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    required = {distance_col, observed_col, synthetic_col}
    missing = required - set(records_df.columns)
    if missing:
        raise KeyError(f"records_df is missing required columns: {sorted(missing)}")
    df = selection.apply(records_df, component_col=component_col or "component") if selection is not None else records_df.copy()
    df[distance_col] = pd.to_numeric(df[distance_col], errors="coerce")
    df[observed_col] = pd.to_numeric(df[observed_col], errors="coerce")
    df[synthetic_col] = pd.to_numeric(df[synthetic_col], errors="coerce")
    components = [None]
    if component_col and component_col in df.columns:
        components = sorted(df[component_col].dropna().astype(str).unique().tolist()) or [None]
    fig, axes = plt.subplots(1, len(components), figsize=(max(6.0, 4.8 * len(components)), 5.2), dpi=180, sharex=True, sharey=True)
    axes = np.atleast_1d(axes)
    for ax, component in zip(axes, components):
        subset = df if component is None else df.loc[df[component_col].astype(str) == str(component)]
        groups = [(None, subset)]
        if event_col and event_col in subset.columns:
            groups = [(label, group) for label, group in subset.groupby(event_col, dropna=False)]
        for group_label, group in groups:
            label_suffix = f" {group_label}" if group_label is not None else ""
            ax.scatter(group[distance_col], group[observed_col], marker="o", color="black", alpha=0.72, s=24, label=f"Observed{label_suffix}")
            ax.scatter(group[distance_col], group[synthetic_col], marker="^", color="#d04a35", alpha=0.62, s=24, label=f"Synthetic{label_suffix}")
        obs_fit = _fit_inverse_distance(subset[distance_col].to_numpy(dtype=float), subset[observed_col].to_numpy(dtype=float))
        syn_fit = _fit_inverse_distance(subset[distance_col].to_numpy(dtype=float), subset[synthetic_col].to_numpy(dtype=float))
        if obs_fit is not None:
            ax.plot(obs_fit[0], obs_fit[1], color="black", linewidth=1.2, label="Observed 1/R fit")
        if syn_fit is not None:
            ax.plot(syn_fit[0], syn_fit[1], color="#d04a35", linewidth=1.2, linestyle="--", label="Synthetic 1/R fit")
        ax.set_title(f"{component} component" if component is not None else "All records")
        ax.set_xlabel("Source-to-station distance (km)")
        ax.grid(True, alpha=0.22)
    axes[0].set_ylabel("Peak absolute amplitude")
    axes[0].legend(loc="best", fontsize=7)
    fig.suptitle(title, y=0.99)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def summarize_coverage(event_station_df: pd.DataFrame) -> dict[str, int | None]:
    """Summarize event-station coverage for notebook manifests.

    Parameters
    ----------
    event_station_df
        Prepared event-station table.

    Returns
    -------
    dict
        Basic row, event, station, and missing-coordinate counts.
    """

    if event_station_df.empty:
        return {
            "event_station_rows": 0,
            "unique_events": 0,
            "unique_stations": 0,
            "rows_missing_station_coordinates": None,
            "rows_missing_event_coordinates": None,
        }
    station_missing = None
    event_missing = None
    if {"lat", "lon"} <= set(event_station_df.columns):
        station_missing = int(event_station_df[["lat", "lon"]].isna().any(axis=1).sum())
    if {"event_lat", "event_lon"} <= set(event_station_df.columns):
        event_missing = int(event_station_df[["event_lat", "event_lon"]].isna().any(axis=1).sum())
    return {
        "event_station_rows": int(len(event_station_df)),
        "unique_events": int(event_station_df["event_id"].nunique()) if "event_id" in event_station_df.columns else 0,
        "unique_stations": int(event_station_df["station"].nunique()) if "station" in event_station_df.columns else 0,
        "rows_missing_station_coordinates": station_missing,
        "rows_missing_event_coordinates": event_missing,
    }
