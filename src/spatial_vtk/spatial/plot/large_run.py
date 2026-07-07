"""Large-run spatial plotting orchestration helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import pandas as pd

from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.config.runtime import SpatialVTKConfig
from spatial_vtk.io import load_output_table, read_bounded_table, read_table, slugify, table_columns
from spatial_vtk.metrics.plot.large_run import (
    MetricFigureContext,
    SIDECAR_EVENT_CENTERED_ATTR,
    SIDECAR_PLOT_ROWS_ROLE_ATTR,
    SIDECAR_SOURCE_ROWS_ROLE_ATTR,
    SIDECAR_TABLE_ROLE_ATTR,
    dimension_value,
    first_existing,
)
from spatial_vtk.visualize.figure_sidecars import (
    add_figure_family_sidecar_status,
    normalize_figure_status_rows,
    write_figure_row_sidecar,
)


ConfigInput = SpatialVTKConfig | str | Path
STEP06_METRIC_COMPARISON_VALUE_COL = "metric_comparison_value"
STEP06_METRIC_COMPARISON_METRICS: tuple[tuple[str, frozenset[str]], ...] = (
    ("PGA", frozenset({"pga", "peak_acceleration", "peak_acceleration_pga"})),
    ("arias_duration", frozenset({"arias_duration", "arias_duration_5_95", "arias_duration_5_95_percent"})),
    ("FAS", frozenset({"fas", "fourier_amplitude_spectrum"})),
    ("traveltime_delay", frozenset({"traveltime_delay", "phase_delay", "delay_time", "phase_delay_time"})),
    (
        "delay_corrected_cc",
        frozenset({"delay_corrected_cc", "delay_corrected_cross_correlation", "corrected_cc"}),
    ),
)
STEP06_METRIC_COMPARISON_RAW_VALUE_KEYS = frozenset({"traveltime_delay", "delay_corrected_cc"})
STEP06_MODEL_DELTA_HEATMAP_SPECS: tuple[dict[str, object], ...] = (
    {
        "token": "log2_residual_metrics",
        "title": "Log2 residual metrics",
        "quantity_label": "Difference in mean log2(observed / synthetic)",
        "metric_keys": frozenset({"pga", "arias_duration", "fas"}),
    },
    {
        "token": "phase_delay_fraction",
        "title": "Phase delay",
        "quantity_label": "Difference in delay / dominant period",
        "metric_keys": frozenset({"traveltime_delay"}),
    },
    {
        "token": "delay_corrected_cc",
        "title": "Delay-corrected cross correlation",
        "quantity_label": "Difference in correlation coefficient",
        "metric_keys": frozenset({"delay_corrected_cc"}),
    },
)


def _site_metadata_with_geology(
    station_df: pd.DataFrame | None,
    *,
    cfg: ConfigInput | None,
    progress: Callable[[str], None],
) -> pd.DataFrame | None:
    """Add configured GeoJSON geology classes when plotting needs them."""

    if station_df is None or station_df.empty:
        return station_df
    try:
        settings = _spatial_statistics_settings(cfg)
    except Exception as exc:
        progress(f"Station metadata geology labels unavailable: could not read spatial settings: {exc}")
        return _site_metadata_with_geomorphology(station_df)

    group_col = str(settings.geology_group_column)
    if group_col in station_df.columns:
        return _site_metadata_with_geomorphology(station_df)
    geology_cols = {"target_region_zone", "target_region_edge_distance_km", "mapped_region", "mapped_region_type"}
    if group_col not in geology_cols:
        return _site_metadata_with_geomorphology(station_df)
    if settings.region_geojson_path is None:
        progress(f"Station metadata is missing {group_col!r}; paths.region_geojson is not configured.")
        return _site_metadata_with_geomorphology(station_df)

    coord_cols = _site_metadata_coordinate_columns(station_df)
    if coord_cols is None:
        progress(
            f"Station metadata is missing {group_col!r} and does not include longitude/latitude columns "
            "for GeoJSON classification."
        )
        return _site_metadata_with_geomorphology(station_df)

    lon_col, lat_col = coord_cols
    try:
        from spatial_vtk.spatial.calculate.geology import add_station_geology_classes, load_region_geometries

        records, target_geom = load_region_geometries(settings.region_geojson_path)
        classified = add_station_geology_classes(
            station_df,
            region_records=records,
            target_region_geom=target_geom,
            edge_buffer_km=5.0,
            lon_col=lon_col,
            lat_col=lat_col,
        )
    except Exception as exc:
        progress(f"Could not add GeoJSON geology classes to station metadata: {exc}")
        return _site_metadata_with_geomorphology(station_df)

    added = [column for column in geology_cols if column in classified.columns and column not in station_df.columns]
    if added:
        progress(f"Added station geology columns from paths.region_geojson: {', '.join(sorted(added))}.")
    return _site_metadata_with_geomorphology(classified)


def _site_metadata_with_geomorphology(station_df: pd.DataFrame | None) -> pd.DataFrame | None:
    """Add a broad geomorphology class used for scientific review boxplots."""

    if station_df is None or station_df.empty or "geomorphology" in station_df.columns:
        return station_df
    if "mapped_region_type" not in station_df.columns and "target_region_zone" not in station_df.columns:
        return station_df
    out = station_df.copy()
    out["geomorphology"] = [_geomorphology_label(row) for _index, row in out.iterrows()]
    return out


def _geomorphology_label(row: pd.Series) -> object:
    """Return Basin, Basin edge, Mountain/hills, or Valley for one station row."""

    zone = str(row.get("target_region_zone", "")).strip().casefold()
    mapped = str(row.get("mapped_region_type", "")).strip().casefold()
    if zone in {"target_region_edge_inside", "target_region_edge_outside"}:
        return "Basin edge"
    if mapped == "basin" or zone == "target_region_interior":
        return "Basin"
    if mapped in {"mountain", "mountains", "hill", "hills"}:
        return "Mountain/hills"
    if mapped in {"valley", "valleys"}:
        return "Valley"
    return pd.NA


def _geology_group_column(cfg: ConfigInput | None) -> str:
    """Return the configured station geology grouping column."""

    try:
        return str(_spatial_statistics_settings(cfg).geology_group_column)
    except Exception:
        return "mapped_region_type"


def _spatial_statistics_settings(cfg: ConfigInput | None) -> Any:
    """Load spatial-statistics settings without importing calculation code at module import time."""

    from spatial_vtk.spatial.calculate.settings import spatial_statistics_settings_from_config

    return spatial_statistics_settings_from_config(cfg)


def _site_metadata_coordinate_columns(station_df: pd.DataFrame) -> tuple[str, str] | None:
    """Return longitude/latitude columns usable for station GeoJSON classification."""

    candidates = (
        ("station_longitude", "station_latitude"),
        ("lon", "lat"),
        ("sta_lon", "sta_lat"),
        ("longitude", "latitude"),
    )
    for lon_col, lat_col in candidates:
        if lon_col in station_df.columns and lat_col in station_df.columns:
            return lon_col, lat_col
    return None


def _is_defined_geology_class(value: object) -> bool:
    """Return True for usable mapped geology class labels."""

    text = str(value).strip()
    if not text:
        return False
    return text.casefold() not in {
        "unknown",
        "unmapped",
        "undefined",
        "unclassified",
        "none",
        "null",
        "nan",
    }


def _close_matplotlib_figures(target: Any = "all") -> None:
    """Close Matplotlib figures when Matplotlib is installed."""

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    plt.close(target)


SPATIAL_FIGURE_TABLE_KEYS: tuple[str, ...] = (
    "metric_field",
    "event_centered_residuals",
    "station_bias",
    "distance_bin_correlations",
    "clusters",
    "pca_station_scores",
    "path_summary",
    "pca_explained_variance",
    "pca_feature_loadings",
    "cluster_solution_scores",
    "cluster_feature_summary",
    "block_holdout_predictions",
    "corridors",
    "redcap_clusters",
    "pattern_similarity_station_anomalies",
    "morans_i",
    "geology_contrasts",
)

SPATIAL_EVENT_ROW_TABLE_KEYS: frozenset[str] = frozenset(
    {"metric_field", "event_centered_residuals"}
)

SPATIAL_TABLE_KEY_ATTR = "svtk_spatial_table_key"
SPATIAL_CONTEXT_ATTR = "svtk_spatial_context"

SPATIAL_EVENT_ROW_COLUMNS: tuple[str, ...] = (
    "metric",
    "metric_name",
    "band",
    "passband",
    "period_band",
    "model",
    "model_name",
    "component",
    "channel_component",
    "period_s",
    "distance_km",
    "azimuth_deg",
    "backazimuth_deg",
    "depth_km",
    "event_depth_km",
    "event_id",
    "event",
    "event_title",
    "station",
    "station_id",
    "station_code",
    "sta_lon",
    "sta_lat",
    "lon",
    "lat",
    "station_lon",
    "station_lat",
    "station_longitude",
    "station_latitude",
    "event_lon",
    "event_lat",
    "event_longitude",
    "event_latitude",
    "field_value",
    "field_source",
    "field_centered",
    "field_z",
    "mean_centered",
    "event_centered_residual",
    "residual",
    "log2_residual",
    "ln_residual",
    "value",
    "score",
    "station_region",
    "station_geojson_region",
    "station_geojson_labels",
    "event_region",
    "event_geojson_region",
    "event_geojson_labels",
)


@dataclass
class SpatialFigureContext:
    """Reusable state for large-run spatial figure notebooks.

    The context loads only compact Step 4 spatial summary outputs and delegates
    metric filtering, PSA period sheets, figure naming, robust row sampling, and
    optional sidecar CSV writing to :class:`MetricFigureContext`.
    """

    figure_dir: Path
    make_figures: bool
    overwrite: bool = False
    add_basemap: bool = False
    default_passband: str | None = None
    default_components: list[str] | None = None
    default_showfig: bool = False
    default_model: str | None = None
    robust_axis_percentile: float = 95.0
    metric_context: MetricFigureContext = field(
        default_factory=lambda: MetricFigureContext.from_frame(None, Path("."), make_figures=False)
    )
    event_context: MetricFigureContext = field(
        default_factory=lambda: MetricFigureContext.from_frame(None, Path("."), make_figures=False)
    )
    tables: dict[str, pd.DataFrame | None] = field(default_factory=dict)
    paths: dict[str, Path] = field(default_factory=dict)
    site_metadata: pd.DataFrame | None = None
    geology_group_col: str = "mapped_region_type"
    verbose: bool = True

    @classmethod
    def from_config(
        cls,
        *,
        figure_dir: str | Path,
        make_figures: bool,
        cfg: ConfigInput | None = None,
        overwrite: bool = False,
        add_basemap: bool = False,
        default_passband: str | None = None,
        default_components: list[str] | None = None,
        default_showfig: bool = False,
        default_model: str | None = None,
        robust_axis_percentile: float = 95.0,
        sample_rows: int = 200_000,
        write_sidecars: bool = False,
        sidecar_rows: int | None = None,
        sidecar_dir: str | Path | None = None,
        station_aggregation: str = "median",
        load_filters: dict[str, object] | None = None,
        verbose: bool = True,
    ) -> "SpatialFigureContext":
        """Load compact spatial output tables and return a plotting context."""

        output_dir = Path(figure_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        sidecar_output_dir = None if sidecar_dir is None else Path(sidecar_dir).expanduser()
        paths = {
            key: resolve_output_path(key, kind="table", cfg=cfg, create_parent=True)
            for key in SPATIAL_FIGURE_TABLE_KEYS
        }
        tables = {
            key: _tag_spatial_table(
                _read_if_exists(path, columns=_columns_for_spatial_table(key)),
                key=key,
            )
            for key, path in paths.items()
        }
        metric_value_col = _first_existing(
            tables["metric_field"],
            ["log2_residual", "field_value", "mean_centered", "field_centered", "residual"],
        )
        event_value_col = _first_existing(
            tables["event_centered_residuals"],
            ["mean_centered", "field_centered", "event_centered_residual", "residual", "log2_residual"],
        )
        metric_context = MetricFigureContext.from_frame(
            tables["metric_field"],
            output_dir,
            make_figures=make_figures,
            overwrite=overwrite,
            sample_rows=sample_rows,
            value_col=metric_value_col or "log2_residual",
            default_passband=default_passband,
            default_components=default_components,
            default_showfig=default_showfig,
            default_model=default_model,
            add_basemap=add_basemap,
            robust_axis_percentile=robust_axis_percentile,
            write_sidecars=write_sidecars,
            sidecar_rows=sidecar_rows,
            sidecar_dir=sidecar_output_dir,
            station_aggregation=station_aggregation,
            load_filters=load_filters,
            verbose=verbose,
        )
        event_context = MetricFigureContext.from_frame(
            tables["event_centered_residuals"],
            output_dir,
            make_figures=make_figures,
            overwrite=overwrite,
            sample_rows=sample_rows,
            value_col=event_value_col or metric_value_col or "log2_residual",
            default_passband=default_passband,
            default_components=default_components,
            default_showfig=default_showfig,
            default_model=default_model,
            add_basemap=add_basemap,
            robust_axis_percentile=robust_axis_percentile,
            write_sidecars=write_sidecars,
            sidecar_rows=sidecar_rows,
            sidecar_dir=sidecar_output_dir,
            station_aggregation=station_aggregation,
            load_filters=load_filters,
            verbose=verbose,
        )
        station_metadata_messages: list[str] = []
        try:
            site_metadata = load_output_table("prepared_stations", cfg=cfg)
            site_metadata = _site_metadata_with_geology(
                site_metadata,
                cfg=cfg,
                progress=station_metadata_messages.append,
            )
        except Exception as exc:
            site_metadata = None
            station_metadata_messages.append(f"Station metadata unavailable for geology contrast plots: {exc}")
        geology_group_col = _geology_group_column(cfg)
        context = cls(
            figure_dir=output_dir,
            make_figures=bool(make_figures),
            overwrite=bool(overwrite),
            add_basemap=bool(add_basemap),
            default_passband=default_passband,
            default_components=default_components,
            default_showfig=bool(default_showfig),
            default_model=default_model,
            robust_axis_percentile=float(robust_axis_percentile),
            metric_context=metric_context,
            event_context=event_context,
            tables=tables,
            paths=paths,
            site_metadata=site_metadata,
            geology_group_col=geology_group_col,
            verbose=bool(verbose),
        )
        if make_figures:
            for station_metadata_message in station_metadata_messages:
                context._progress(station_metadata_message)
        if make_figures:
            context._progress(f"Rendering spatial figures into {output_dir}")
            context._progress(
                f"metric_value_col={context.metric_value_col} "
                f"event_value_col={context.event_value_col} "
                f"default_passband={default_passband} "
                f"default_components={default_components} "
                f"default_model={default_model}"
            )
        return context

    def _progress(self, message: str) -> None:
        """Print one progress message when verbose output is enabled."""

        if self.verbose:
            print(message)

    def status_frame(self) -> pd.DataFrame:
        """Return loaded table status for this spatial figure context.

        The frame reports the configured Step 4 table paths, whether each table
        exists and was loaded, normalized artifact labels/roles/status values,
        and the loaded row/column counts. It is safe to display in notebooks
        because it summarizes tables already loaded by the context and does not
        read additional large files.
        """

        rows: list[dict[str, Any]] = []
        for key in SPATIAL_FIGURE_TABLE_KEYS:
            path = self.paths.get(key)
            resolved_path = None if path is None else str(path)
            table = self.tables.get(key)
            loaded = table is not None
            exists = bool(path.exists()) if path is not None else None
            rows.append(
                {
                    "name": key,
                    "artifact": key,
                    "artifact_label": key.replace("_", " ").title(),
                    "artifact_role": "spatial_figure_input",
                    "status": _spatial_context_table_status(loaded=loaded, exists=exists),
                    "role": _spatial_table_role(key),
                    "resolved_path": resolved_path,
                    "path": resolved_path,
                    "exists": exists,
                    "loaded": loaded,
                    "row_count": int(len(table)) if loaded else 0,
                    "column_count": int(len(table.columns)) if loaded else 0,
                    "value_col": _spatial_table_value_col(key, table, self),
                    "value_role": _spatial_table_value_role(key),
                }
            )
        station_table = self.site_metadata
        rows.append(
            {
                "name": "prepared_stations",
                "artifact": "prepared_stations",
                "artifact_label": "Prepared Stations",
                "artifact_role": "site_metadata",
                "status": "ready" if station_table is not None else "not_loaded",
                "role": "site metadata for geology and station diagnostics",
                "resolved_path": None,
                "path": None,
                "exists": None,
                "loaded": station_table is not None,
                "row_count": int(len(station_table)) if station_table is not None else 0,
                "column_count": int(len(station_table.columns)) if station_table is not None else 0,
                "value_col": None,
                "value_role": None,
            }
        )
        return pd.DataFrame(rows)

    def dimension_summary_frame(self) -> pd.DataFrame:
        """Return metric/event-centered dimension coverage for spatial figures."""

        frames = [
            self.metric_context.dimension_summary_frame().assign(table="metric_field"),
            self.event_context.dimension_summary_frame().assign(table="event_centered_residuals"),
        ]
        out = pd.concat(frames, ignore_index=True, sort=False)
        columns = ["table", *[column for column in out.columns if column != "table"]]
        return out.loc[:, columns]

    def spectral_metric_contract_status(self) -> pd.DataFrame:
        """Return PSA/FAS broadband-passband contract status for spatial rows.

        Step 4 spatial figures use ``metric_field`` and
        ``event_centered_residuals`` tables produced from metric rows. This
        helper audits both tables with the same broadband spectral contract used
        by :class:`MetricFigureContext`, while adding a ``table`` column so
        notebooks can tell which spatial input needs to be rebuilt.
        """

        frames = [
            self.metric_context.spectral_metric_contract_status().assign(table="metric_field"),
            self.event_context.spectral_metric_contract_status().assign(table="event_centered_residuals"),
        ]
        out = pd.concat(frames, ignore_index=True, sort=False)
        columns = ["table", *[column for column in out.columns if column != "table"]]
        return out.loc[:, columns]

    @property
    def metric_field(self) -> pd.DataFrame | None:
        """Loaded metric-field table."""

        return self.tables.get("metric_field")

    @property
    def event_centered(self) -> pd.DataFrame | None:
        """Loaded event-centered residual table."""

        return self.tables.get("event_centered_residuals")

    @property
    def metric_col(self) -> str | None:
        """Metric column selected from the metric-field table."""

        return self.metric_context.metric_col

    @property
    def band_col(self) -> str | None:
        """Passband column selected from the metric-field table."""

        return self.metric_context.band_col

    @property
    def model_col(self) -> str | None:
        """Model column selected from the metric-field table."""

        return self.metric_context.model_col

    @property
    def component_col(self) -> str | None:
        """Component column selected from the metric-field table."""

        return self.metric_context.component_col

    @property
    def period_col(self) -> str | None:
        """PSA period column selected from the metric-field table."""

        return self.metric_context.period_col or self.event_context.period_col

    @property
    def metric_value_col(self) -> str | None:
        """Value column selected from the metric-field table."""

        return self.metric_context.value_col if self.metric_context.ready else None

    @property
    def event_value_col(self) -> str | None:
        """Value column selected from the event-centered table."""

        return self.event_context.value_col if self.event_context.ready else None

    def table(self, key: str) -> pd.DataFrame | None:
        """Return one loaded spatial output table by key."""

        return self.tables.get(key)

    def iter_metric_frames(
        self,
        df: pd.DataFrame | None,
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        split_psa_period: bool = True,
    ):
        """Yield target metric frames for one loaded spatial table."""

        context = self._context_for(df)
        if context is None:
            return
        context_name = "event" if context is self.event_context else "metric"
        for item in context.iter_metric_frames(
            passband=passband,
            components=components,
            model=model,
            split_psa_period=split_psa_period,
        ):
            tagged = dict(item)
            tagged[SPATIAL_CONTEXT_ATTR] = context_name
            frame = tagged.get("df")
            if isinstance(frame, pd.DataFrame):
                frame.attrs[SPATIAL_CONTEXT_ATTR] = context_name
                _tag_spatial_sidecar_roles(frame, context=context, aggregated=False)
            yield tagged

    def write_spatial_plot(
        self,
        base: str,
        item: dict[str, Any],
        func: Callable[..., Any],
        df: pd.DataFrame | None = None,
        source_df: pd.DataFrame | None = None,
        required: tuple[str, ...] | list[str | None] = (),
        finite_columns: tuple[str | None, ...] | list[str | None] = (),
        value_col: str | None = None,
        forward_value_col: bool = False,
        showfig: bool = False,
        **kwargs: Any,
    ) -> Path | None:
        """Write one spatial plot using the matching figure context."""

        context = self._context_for_item(item) or self.metric_context
        self._apply_event_centered_plot_defaults(base, context, kwargs)
        return context.write_metric_plot(
            base,
            item,
            func,
            df=df,
            source_df=source_df,
            required=[column for column in required if column],
            finite_columns=[column for column in finite_columns if column],
            value_col=value_col,
            forward_value_col=forward_value_col,
            showfig=showfig,
            **kwargs,
        )

    def _apply_event_centered_plot_defaults(
        self,
        base: str,
        context: MetricFigureContext,
        kwargs: dict[str, Any],
    ) -> None:
        """Set clearer default labels for plots drawn from event-centered rows."""

        if context is not self.event_context or "title" in kwargs:
            return
        title = {
            "spatial_azimuthal_residuals": "Event-Centered Azimuthal Residuals (Event Mean Removed)",
            "spatial_polar_residuals": "Event-Centered Polar Residuals (Event Mean Removed)",
        }.get(base)
        if title:
            kwargs["title"] = title

    def write_spatial_period_sheet(
        self,
        base: str,
        item: dict[str, Any],
        func: Callable[..., Any],
        df_factory: Callable[[dict[str, Any]], pd.DataFrame] | None = None,
        source_df_factory: Callable[[dict[str, Any]], pd.DataFrame | None] | None = None,
        required: tuple[str, ...] | list[str | None] = (),
        value_col: str | None = None,
        forward_value_col: bool = False,
        showfig: bool = False,
        **kwargs: Any,
    ) -> Path | None:
        """Write a PSA period contact sheet using the matching context."""

        context = self._context_for_item(item) or self.metric_context
        self._apply_event_centered_plot_defaults(base, context, kwargs)
        return context.write_psa_period_sheet(
            base,
            item,
            func,
            df_factory=df_factory,
            source_df_factory=source_df_factory,
            required=[column for column in required if column],
            value_col=value_col,
            forward_value_col=forward_value_col,
            showfig=showfig,
            **kwargs,
        )

    def write_station_metric_maps(
        self,
        station_metric_map_func: Callable[..., Any],
        station_metric_map_by_period_func: Callable[..., Any],
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        value_col: str | None = None,
        add_basemap: bool | None = None,
        showfig: bool | None = None,
        event_centered: bool = False,
    ) -> list[Path]:
        """Write station-level spatial metric maps for configured target metrics."""

        source = self.event_centered if event_centered else self.metric_field
        base_name = "spatial_station_metric_map_event_centered" if event_centered else "spatial_station_metric_map"
        resolved_value_col = value_col or (self.event_value_col if event_centered else self.metric_value_col)
        outputs: list[Path] = []
        can_render = self._can_render_event_figures if event_centered else self._can_render_metric_figures
        if not can_render(base_name, resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            source,
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            if item["key"] == "psa" and self.period_col in item["df"].columns:
                station_period_df = self.station_period_summary_for_item(item, resolved_value_col)
                output = self.write_spatial_plot(
                    base_name,
                    item,
                    station_metric_map_by_period_func,
                    df=station_period_df,
                    source_df=self.item_source_rows(item),
                    required=["sta_lon", "sta_lat", self.period_col, resolved_value_col],
                    value_col=resolved_value_col,
                    forward_value_col=True,
                    period_col=self.period_col,
                    add_basemap=self._resolved_add_basemap(add_basemap),
                    showfig=self._resolved_showfig(showfig),
                )
            else:
                station_df = self.station_summary_for_item(item, resolved_value_col)
                output = self.write_spatial_plot(
                    base_name,
                    item,
                    station_metric_map_func,
                    df=station_df,
                    source_df=self.item_source_rows(item),
                    required=["sta_lon", "sta_lat", resolved_value_col],
                    value_col=resolved_value_col,
                    forward_value_col=True,
                    add_basemap=self._resolved_add_basemap(add_basemap),
                    showfig=self._resolved_showfig(showfig),
                )
            if output is not None:
                outputs.append(output)
        return outputs

    def write_station_bias_maps(
        self,
        station_bias_map_func: Callable[..., Any],
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        value_col: str | None = None,
        add_basemap: bool | None = None,
        showfig: bool | None = None,
        event_centered: bool = True,
    ) -> list[Path]:
        """Write station-bias summary maps for target metrics."""

        outputs: list[Path] = []
        if event_centered:
            resolved_value_col = value_col or "mean_centered"
            station_bias = self.table("station_bias")
            if station_bias is None or station_bias.empty:
                self._progress("skip spatial_station_bias_map: station_bias table missing or empty")
                return outputs
            if resolved_value_col not in station_bias.columns:
                self._progress(f"skip spatial_station_bias_map: value column unavailable ({resolved_value_col!r})")
                return outputs
            if self.metric_field is None or self.metric_field.empty:
                self._progress("skip spatial_station_bias_map: metric_field table missing or empty")
                return outputs
            items = self.iter_metric_frames(
                self.metric_field,
                passband=passband,
                components=components,
                model=model,
                split_psa_period=False,
            )
            base_name = "spatial_station_bias_map"
            value_label = "Mean event-centered log2(observed / synthetic)"
            title = "Station Bias (Event Mean Removed)"
            for item in items:
                bias_for_item = self.filter_like_item(station_bias, item, include_period=False)
                if bias_for_item is None or bias_for_item.empty:
                    self._progress(f"skip {base_name} {item['label']}: no station-bias rows")
                    continue
                output = self.write_spatial_plot(
                    base_name,
                    item,
                    station_bias_map_func,
                    df=bias_for_item,
                    required=[resolved_value_col],
                    finite_columns=[resolved_value_col],
                    value_col=resolved_value_col,
                    forward_value_col=True,
                    value_label=value_label,
                    title=title,
                    add_basemap=self._resolved_add_basemap(add_basemap),
                    showfig=self._resolved_showfig(showfig),
                )
                if output is not None:
                    outputs.append(output)
            return outputs

        resolved_value_col = value_col or self.metric_value_col
        if not self._can_render_metric_figures("spatial_station_bias_map_raw", resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            self.metric_field,
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            bias_for_item = self.station_summary_for_item(item, resolved_value_col)
            output = self.write_spatial_plot(
                "spatial_station_bias_map_raw",
                item,
                station_bias_map_func,
                df=bias_for_item,
                source_df=self.item_source_rows(item),
                required=[resolved_value_col],
                finite_columns=[resolved_value_col],
                value_col=resolved_value_col,
                forward_value_col=True,
                value_label="Mean raw log2(observed / synthetic)",
                title="Station Mean Residual (Event Mean Not Removed)",
                add_basemap=self._resolved_add_basemap(add_basemap),
                showfig=self._resolved_showfig(showfig),
            )
            if output is not None:
                outputs.append(output)
        return outputs

    def write_residual_grid_maps(
        self,
        residual_grid_func: Callable[..., Any],
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        value_col: str | None = None,
        add_basemap: bool | None = None,
        showfig: bool | None = None,
        event_centered: bool = False,
    ) -> list[Path]:
        """Write station-interpolated residual grid maps for target metrics."""

        source = self.event_centered if event_centered else self.metric_field
        base_name = "spatial_residual_grid_event_centered" if event_centered else "spatial_residual_grid"
        resolved_value_col = value_col or (self.event_value_col if event_centered else self.metric_value_col)
        outputs: list[Path] = []
        can_render = self._can_render_event_figures if event_centered else self._can_render_metric_figures
        if not can_render(base_name, resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            source,
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            if item["key"] == "psa":
                output = self.write_spatial_period_sheet(
                    base_name,
                    item,
                    residual_grid_func,
                    df_factory=self.station_grid_for_item,
                    source_df_factory=self.item_source_rows,
                    required=["lon", "lat", resolved_value_col],
                    value_col=resolved_value_col,
                    forward_value_col=True,
                    add_basemap=self._resolved_add_basemap(add_basemap),
                    showfig=self._resolved_showfig(showfig),
                )
            else:
                grid_df = self.station_grid_for_item(item, resolved_value_col)
                output = self.write_spatial_plot(
                    base_name,
                    item,
                    residual_grid_func,
                    df=grid_df,
                    source_df=self.item_source_rows(item),
                    required=["lon", "lat", resolved_value_col],
                    value_col=resolved_value_col,
                    forward_value_col=True,
                    add_basemap=self._resolved_add_basemap(add_basemap),
                    showfig=self._resolved_showfig(showfig),
                )
            if output is not None:
                outputs.append(output)
        return outputs

    def write_metric_by_model_maps(
        self,
        metric_by_model_map_func: Callable[..., Any],
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        value_col: str | None = None,
        add_basemap: bool | None = None,
        showfig: bool | None = None,
        event_centered: bool = False,
    ) -> list[Path]:
        """Write faceted station maps split by model for target metrics."""

        source = self.event_centered if event_centered else self.metric_field
        base_name = "spatial_metric_by_model_map_event_centered" if event_centered else "spatial_metric_by_model_map"
        resolved_value_col = value_col or (self.event_value_col if event_centered else self.metric_value_col)
        outputs: list[Path] = []
        can_render = self._can_render_event_figures if event_centered else self._can_render_metric_figures
        if not can_render(base_name, resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            source,
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            if item["key"] == "psa":
                output = self.write_spatial_period_sheet(
                    base_name,
                    item,
                    metric_by_model_map_func,
                    df_factory=self.station_model_summary_for_item,
                    source_df_factory=self.item_source_rows,
                    required=[self.model_col, "sta_lon", "sta_lat", resolved_value_col],
                    value_col=resolved_value_col,
                    forward_value_col=True,
                    add_basemap=self._resolved_add_basemap(add_basemap),
                    showfig=self._resolved_showfig(showfig),
                )
            else:
                station_model_df = self.station_model_summary_for_item(item, resolved_value_col)
                output = self.write_spatial_plot(
                    base_name,
                    item,
                    metric_by_model_map_func,
                    df=station_model_df,
                    source_df=self.item_source_rows(item),
                    required=[self.model_col, "sta_lon", "sta_lat", resolved_value_col],
                    value_col=resolved_value_col,
                    forward_value_col=True,
                    add_basemap=self._resolved_add_basemap(add_basemap),
                    showfig=self._resolved_showfig(showfig),
                )
            if output is not None:
                outputs.append(output)
        return outputs

    def write_event_residual_maps(
        self,
        event_residual_map_func: Callable[..., Any],
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        value_col: str | None = None,
        add_basemap: bool | None = None,
        showfig: bool | None = None,
        event_centered: bool = False,
    ) -> list[Path]:
        """Write event residual maps for target metric rows."""

        source = self.event_centered if event_centered else self.metric_field
        base_name = "spatial_event_residual_map_event_centered" if event_centered else "spatial_event_residual_map"
        resolved_value_col = value_col or (self.event_value_col if event_centered else self.metric_value_col)
        outputs: list[Path] = []
        can_render = self._can_render_event_figures if event_centered else self._can_render_metric_figures
        if not can_render(base_name, resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            source,
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            writer = self.write_spatial_period_sheet if item["key"] == "psa" else self.write_spatial_plot
            output = writer(
                base_name,
                item,
                event_residual_map_func,
                required=["event_id", "sta_lon", "sta_lat", resolved_value_col],
                value_col=resolved_value_col,
                forward_value_col=True,
                metric=None,
                add_basemap=self._resolved_add_basemap(add_basemap),
                showfig=self._resolved_showfig(showfig),
            )
            if output is not None:
                outputs.append(output)
        return outputs

    def write_event_centered_azimuthal_plots(
        self,
        azimuthal_residuals_func: Callable[..., Any],
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        value_col: str | None = None,
        showfig: bool | None = None,
        robust_axis_percentile: float | None = None,
    ) -> list[Path]:
        """Write event-centered azimuthal residual plots for target metrics."""

        resolved_value_col = value_col or self.event_value_col
        outputs: list[Path] = []
        if not self._can_render_event_figures("spatial_azimuthal_residuals", resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            self.event_centered,
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            writer = self.write_spatial_period_sheet if item["key"] == "psa" else self.write_spatial_plot
            output = writer(
                "spatial_azimuthal_residuals",
                item,
                azimuthal_residuals_func,
                required=["azimuth_deg", resolved_value_col],
                value_col=resolved_value_col,
                forward_value_col=True,
                group_col=self.component_col,
                fit="lowess",
                robust_axis_percentile=self.robust_axis_percentile if robust_axis_percentile is None else robust_axis_percentile,
                showfig=self._resolved_showfig(showfig),
            )
            if output is not None:
                outputs.append(output)
        return outputs

    def write_event_centered_polar_plots(
        self,
        polar_residuals_func: Callable[..., Any],
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        value_col: str | None = None,
        showfig: bool | None = None,
    ) -> list[Path]:
        """Write event-centered polar residual plots for target metrics."""

        resolved_value_col = value_col or self.event_value_col
        outputs: list[Path] = []
        if not self._can_render_event_figures("spatial_polar_residuals", resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            self.event_centered,
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            writer = self.write_spatial_period_sheet if item["key"] == "psa" else self.write_spatial_plot
            output = writer(
                "spatial_polar_residuals",
                item,
                polar_residuals_func,
                required=["azimuth_deg", "distance_km", resolved_value_col],
                value_col=resolved_value_col,
                forward_value_col=True,
                showfig=self._resolved_showfig(showfig),
            )
            if output is not None:
                outputs.append(output)
        return outputs

    def _resolved_add_basemap(self, add_basemap: bool | None) -> bool:
        """Return explicit or context-level basemap setting."""

        return self.add_basemap if add_basemap is None else bool(add_basemap)

    def _resolved_showfig(self, showfig: bool | None) -> bool:
        """Return explicit or context-level notebook display setting."""

        return self.default_showfig if showfig is None else bool(showfig)

    def _can_render_metric_figures(self, label: str, value_col: str | None) -> bool:
        """Return whether metric-field figures can render, printing a bounded reason."""

        if not self.make_figures:
            self._progress(f"Skipping {label}. Enable spatial figures to render it.")
            return False
        if self.metric_field is None or self.metric_field.empty:
            self._progress(f"Skipping {label}: metric_field table missing or empty.")
            return False
        if not value_col:
            self._progress(f"Skipping {label}: no metric value column is available.")
            return False
        return True

    def _can_render_event_figures(self, label: str, value_col: str | None) -> bool:
        """Return whether event-centered figures can render, printing a bounded reason."""

        if not self.make_figures:
            self._progress(f"Skipping {label}. Enable spatial figures to render it.")
            return False
        if self.event_centered is None or self.event_centered.empty:
            self._progress(f"Skipping {label}: event_centered_residuals table missing or empty.")
            return False
        if not value_col:
            self._progress(f"Skipping {label}: no event-centered value column is available.")
            return False
        return True

    def station_summary_for_map(
        self,
        df: pd.DataFrame,
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate event-station spatial rows to one plotted value per station."""

        context = self._context_for(df) or self.metric_context
        out = context.station_summary_for_map(df, value_col=value_col, extra_group_cols=extra_group_cols)
        _tag_spatial_sidecar_roles(out, context_name=self._context_name(context), aggregated=True)
        return out

    def station_period_summary_for_map(
        self,
        df: pd.DataFrame,
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate PSA spatial rows to one plotted value per station and oscillator period."""

        context = self._context_for(df) or self.metric_context
        out = context.station_period_summary_for_map(df, value_col=value_col, extra_group_cols=extra_group_cols)
        _tag_spatial_sidecar_roles(out, context_name=self._context_name(context), aggregated=True)
        return out

    def item_source_rows(self, item: dict[str, Any]) -> pd.DataFrame:
        """Return the spatial rows represented by one figure item."""

        context = self._context_for_item(item) or self.metric_context
        out = context.item_source_rows(item)
        _tag_spatial_sidecar_roles(out, context_name=self._context_name(context), aggregated=False)
        return out

    def station_summary_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate one figure item's rows to one plotted value per station."""

        context = self._context_for_item(item) or self.metric_context
        out = context.station_summary_for_item(item, value_col=value_col, extra_group_cols=extra_group_cols)
        _tag_spatial_sidecar_roles(out, context_name=self._context_name(context), aggregated=True)
        return out

    def station_period_summary_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate one PSA figure item's rows to one plotted value per station and period."""

        context = self._context_for_item(item) or self.metric_context
        out = context.station_period_summary_for_item(item, value_col=value_col, extra_group_cols=extra_group_cols)
        _tag_spatial_sidecar_roles(out, context_name=self._context_name(context), aggregated=True)
        return out

    def station_grid_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate one figure item and expose station coordinates as lon/lat."""

        context = self._context_for_item(item) or self.metric_context
        out = context.station_grid_for_item(item, value_col=value_col, extra_group_cols=extra_group_cols)
        _tag_spatial_sidecar_roles(out, context_name=self._context_name(context), aggregated=True)
        return out

    def station_period_grid_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate one PSA figure item by station/period and expose lon/lat columns."""

        context = self._context_for_item(item) or self.metric_context
        out = context.station_period_grid_for_item(item, value_col=value_col, extra_group_cols=extra_group_cols)
        _tag_spatial_sidecar_roles(out, context_name=self._context_name(context), aggregated=True)
        return out

    def station_model_summary_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
    ) -> pd.DataFrame:
        """Aggregate one figure item by station and model."""

        context = self._context_for_item(item) or self.metric_context
        out = context.station_model_summary_for_item(item, value_col=value_col)
        _tag_spatial_sidecar_roles(out, context_name=self._context_name(context), aggregated=True)
        return out

    def station_model_grid_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
    ) -> pd.DataFrame:
        """Aggregate one figure item by station/model and expose lon/lat columns."""

        context = self._context_for_item(item) or self.metric_context
        out = context.station_model_grid_for_item(item, value_col=value_col)
        _tag_spatial_sidecar_roles(out, context_name=self._context_name(context), aggregated=True)
        return out

    def write_overview_plots(
        self,
        *,
        value_col: str | None = None,
        event_value_col: str | None = None,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        showfig: bool = False,
        robust_axis_percentile: float | None = None,
        plot_functions: Mapping[str, Callable[..., Any]] | None = None,
    ) -> list[Path]:
        """Write compact Step 4 overview figures from loaded spatial summary tables.

        Missing optional tables are represented as empty frames so overview
        figures skip with normal required-column messages instead of falling
        back to unrelated metric-field rows.
        """

        functions = dict(_spatial_overview_plot_functions() if plot_functions is None else plot_functions)
        overview_item = {
            "key": "overview",
            "label": "Overview",
            "period_s": None,
            "df": self.metric_field if self.metric_field is not None else pd.DataFrame(),
        }
        resolved_value_col = self.metric_value_col if value_col is None else value_col
        resolved_event_value_col = self.event_value_col if event_value_col is None else event_value_col
        resolved_robust = self.robust_axis_percentile if robust_axis_percentile is None else float(robust_axis_percentile)
        outputs: list[Path] = []

        specs: list[dict[str, Any]] = [
            {
                "base": "spatial_correlogram",
                "table": "distance_bin_correlations",
                "func": "plot_correlogram",
                "required": ["distance_center_km", "mean_pair_correlation"],
                "value_col": "mean_pair_correlation",
            },
            {
                "base": "spatial_correlation_distance_by_metric",
                "table": "distance_bin_correlations",
                "func": "plot_distance_correlation_by_metric",
                "required": ["distance_center_km", "mean_pair_correlation"],
                "value_col": "mean_pair_correlation",
                "kwargs": {"significance_df": self.table("morans_i"), "title": "Spatial Correlation by Distance"},
            },
            {
                "base": "spatial_semivariogram",
                "table": "distance_bin_correlations",
                "func": "plot_semivariogram",
                "required": ["distance_end_km", "semivariance"],
                "value_col": "semivariance",
            },
            {
                "base": "spatial_directional_correlogram",
                "table": "distance_bin_correlations",
                "func": "plot_directional_correlogram",
                "required": ["direction_center_deg", "distance_center_km", "mean_pair_correlation"],
                "value_col": "mean_pair_correlation",
            },
            {
                "base": "spatial_block_holdout_scatter",
                "table": "block_holdout_predictions",
                "func": "plot_block_holdout_scatter",
                "required": ["observed_mean_centered", "predicted_mean_centered"],
                "value_col": "prediction_error",
            },
            {
                "base": "spatial_cluster_solution_scores",
                "table": "cluster_solution_scores",
                "func": "plot_cluster_solution_scores",
                "required": ["k", "score"],
                "value_col": "score",
            },
            {
                "base": "spatial_cluster_feature_heatmap",
                "table": "cluster_feature_summary",
                "func": "plot_cluster_feature_heatmap",
                "value_col": resolved_value_col,
            },
            {
                "base": "spatial_path_bin_summary",
                "table": "path_summary",
                "func": "plot_path_bin_summary",
                "required": ["path_bin", "median_residual"],
                "value_col": "median_residual",
                "forward_value_col": True,
            },
            {
                "base": "spatial_residual_correlation",
                "table": "distance_bin_correlations",
                "func": "plot_residual_correlation",
                "value_col": resolved_value_col,
            },
            {
                "base": "spatial_pca_explained_variance",
                "table": "pca_explained_variance",
                "func": "plot_pca_explained_variance",
                "required": ["mode_index", "explained_variance_ratio"],
                "value_col": "explained_variance_ratio",
            },
            {
                "base": "spatial_pca_feature_loadings",
                "table": "pca_feature_loadings",
                "func": "plot_pca_feature_loadings",
                "value_col": resolved_value_col,
            },
        ]
        for spec in specs:
            output = self.write_spatial_plot(
                spec["base"],
                overview_item,
                functions[spec["func"]],
                df=self._table_or_empty(spec["table"]),
                required=spec.get("required", []),
                value_col=spec.get("value_col"),
                forward_value_col=bool(spec.get("forward_value_col", False)),
                showfig=showfig,
                **spec.get("kwargs", {}),
            )
            if output is not None:
                outputs.append(output)

        outputs.extend(
            self._write_pattern_similarity_overview_plots(
                functions["plot_pattern_similarity"],
                passband=passband,
                components=components,
                model=model,
                showfig=showfig,
            )
        )
        outputs.extend(
            self._write_geology_contrast_overview_plots(
                functions["plot_geology_contrast"],
                value_col=resolved_value_col,
                event_value_col=resolved_event_value_col,
                passband=passband,
                components=components,
                model=model,
                showfig=showfig,
                robust_axis_percentile=resolved_robust,
            )
        )
        return outputs

    def write_pca_summary_plots(
        self,
        pca_summary_func: Callable[..., Any],
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        mode: str = "PC1",
        score_col: str | None = None,
        showfig: bool = False,
        **kwargs: Any,
    ) -> list[Path]:
        """Write combined PCA mode summaries for each target metric.

        The summary combines the station-score map, explained variance, and
        feature-loading panel used by the standard tutorial while keeping the
        large-run notebook on compact Step 4 summary tables.
        """

        metric_field = self.metric_field
        station_scores = self.table("pca_station_scores")
        explained_variance = self.table("pca_explained_variance")
        feature_loadings = self.table("pca_feature_loadings")
        if metric_field is None or metric_field.empty:
            self._progress("skip spatial_pca_summary: metric_field table missing or empty")
            return []
        if station_scores is None or station_scores.empty:
            self._progress("skip spatial_pca_summary: pca_station_scores table missing or empty")
            return []
        if explained_variance is None or explained_variance.empty:
            self._progress("skip spatial_pca_summary: pca_explained_variance table missing or empty")
            return []
        if feature_loadings is None or feature_loadings.empty:
            self._progress("skip spatial_pca_summary: pca_feature_loadings table missing or empty")
            return []

        resolved_score_col = score_col or f"{mode}_score"
        outputs: list[Path] = []
        for item in self.iter_metric_frames(
            metric_field,
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            score_rows = self.filter_like_item(station_scores, item, include_period=False)
            explained_rows = self.filter_like_item(explained_variance, item, include_period=False)
            loading_rows = self.filter_like_item(feature_loadings, item, include_period=False)
            if score_rows is None or score_rows.empty:
                self._progress(f"skip spatial_pca_summary {item['label']}: no PCA station score rows")
                continue
            if explained_rows is None or explained_rows.empty:
                self._progress(f"skip spatial_pca_summary {item['label']}: no PCA explained-variance rows")
                continue
            if loading_rows is None or loading_rows.empty:
                self._progress(f"skip spatial_pca_summary {item['label']}: no PCA feature-loading rows")
                continue
            if resolved_score_col not in score_rows.columns:
                self._progress(f"skip spatial_pca_summary {item['label']}: missing score column {resolved_score_col!r}")
                continue

            output = self.figure_dir / f"{self.metric_context.figure_name('spatial_pca_summary', item, resolved_score_col)}.png"
            if output.exists() and not self.overwrite:
                self._progress(f"skip {output.name}: exists")
                self._write_pca_summary_sidecar(
                    output,
                    station_scores=score_rows,
                    explained_variance=explained_rows,
                    feature_loadings=loading_rows,
                    mode=mode,
                    score_col=resolved_score_col,
                )
                outputs.append(output)
                continue

            try:
                pca_summary_func(
                    score_rows,
                    explained_rows,
                    loading_rows,
                    output_path=output,
                    mode=mode,
                    score_col=resolved_score_col,
                    add_basemap=self.add_basemap,
                    showfig=showfig,
                    savefig=True,
                    write_sidecar=self.metric_context.write_sidecars,
                    sidecar_rows=self.metric_context.sidecar_rows,
                    sidecar_dir=self.metric_context.sidecar_output_dir,
                    title=f"{item['label']} PCA Spatial Mode Summary",
                    **kwargs,
                )
                _close_matplotlib_figures()
                self._progress(f"wrote {output}")
                outputs.append(output)
            except Exception as exc:
                _close_matplotlib_figures()
                self._progress(f"skip {output.name}: {type(exc).__name__}: {exc}")
        return outputs

    def _write_pca_summary_sidecar(
        self,
        output: Path,
        *,
        station_scores: pd.DataFrame,
        explained_variance: pd.DataFrame,
        feature_loadings: pd.DataFrame,
        mode: str,
        score_col: str,
    ) -> Path | None:
        """Write a PCA summary sidecar when the figure already exists."""

        if not self.metric_context.write_sidecars:
            return None
        sidecar_rows = _layer_pca_summary_rows(
            station_scores=station_scores,
            explained_variance=explained_variance,
            feature_loadings=feature_loadings,
            mode=mode,
            score_col=score_col,
        )
        result = write_figure_row_sidecar(
            output,
            sidecar_rows,
            sidecar_rows=self.metric_context.sidecar_rows,
            sidecar_dir=self.metric_context.sidecar_output_dir,
            metadata={"figure_type": "pca_summary", "mode": mode, "score_col": score_col},
        )
        return None if result is None else result.sidecar_path

    def _write_pattern_similarity_overview_plots(
        self,
        func: Callable[..., Any],
        *,
        passband: str | None,
        components: list[str] | str | None,
        model: str | None,
        showfig: bool,
    ) -> list[Path]:
        """Write observed/synthetic station-pattern similarity overview plots."""

        outputs: list[Path] = []
        pattern_rows = self.table("pattern_similarity_station_anomalies")
        if pattern_rows is None or pattern_rows.empty:
            self._progress("skip spatial_pattern_similarity: pattern_similarity_station_anomalies table missing or empty")
            return outputs
        work = pattern_rows.copy()
        if passband is not None and "bin" in work.columns:
            work = work.loc[work["bin"].astype(str).eq(str(passband))].copy()
        component_values = _as_selection_list(components)
        if component_values and "component" in work.columns:
            work = work.loc[work["component"].astype(str).isin(component_values)].copy()
        if model is not None and "model" in work.columns:
            work = work.loc[work["model"].astype(str).eq(str(model))].copy()
        if work.empty:
            self._progress("skip spatial_pattern_similarity: no rows match the requested passband/component/model filters")
            return outputs
        for (metric_name, bin_label), subset in work.groupby(["metric", "bin"], dropna=False):
            if subset.empty:
                continue
            item = {
                "key": "pattern_similarity",
                "label": f"{metric_name} {bin_label}",
                "metric": str(metric_name),
                "period_s": None,
                "df": subset,
            }
            output = self.write_spatial_plot(
                "spatial_pattern_similarity",
                item,
                func,
                df=subset,
                source_df=subset,
                required=["station_name", "dataset", "metric", "bin", "value"],
                value_col="value",
                metric=str(metric_name),
                bin_label=str(bin_label),
                showfig=showfig,
            )
            if output is not None:
                outputs.append(output)
        return outputs

    def filter_like_item(
        self,
        df: pd.DataFrame | None,
        item: dict[str, Any],
        *,
        include_period: bool = True,
    ) -> pd.DataFrame | None:
        """Filter one summary table to the metric dimensions of a plot item."""

        if df is None or df.empty:
            return df
        out = df.copy()
        item_df = item.get("df")
        if item_df is None or item_df.empty:
            return out
        for column in [self.metric_col, self.band_col, self.component_col, self.model_col]:
            if column and column in out.columns and column in item_df.columns:
                values = [str(value) for value in pd.unique(item_df[column].dropna()) if str(value).strip()]
                if values:
                    out = out.loc[out[column].astype(str).isin(values)].copy()
        period_col = self.period_col
        if include_period and period_col and period_col in out.columns and period_col in item_df.columns:
            wanted = pd.to_numeric(item_df[period_col], errors="coerce").dropna().unique()
            if len(wanted):
                out = out.loc[pd.to_numeric(out[period_col], errors="coerce").isin(wanted)].copy()
        return out

    def _table_or_empty(self, key: str) -> pd.DataFrame:
        """Return one loaded table or an explicit empty frame for optional outputs."""

        table = self.table(key)
        return table if table is not None else pd.DataFrame()

    def _write_geology_contrast_overview_plots(
        self,
        func: Callable[..., Any],
        *,
        value_col: str | None,
        event_value_col: str | None,
        passband: str | None,
        components: list[str] | str | None,
        model: str | None,
        showfig: bool,
        robust_axis_percentile: float,
    ) -> list[Path]:
        """Write geology-contrast overview plots for each event-centered metric item."""

        outputs: list[Path] = []
        geology_value_col = event_value_col or value_col
        event_centered = self.event_centered
        if event_centered is None or event_centered.empty:
            self._progress("skip spatial_geology_contrast: event-centered residual table missing or empty")
            return outputs
        if geology_value_col is None or geology_value_col not in event_centered.columns:
            self._progress(f"skip spatial_geology_contrast: value column unavailable ({geology_value_col!r})")
            return outputs
        geology_group_col = self.geology_group_col
        event_has_geology = geology_group_col in event_centered.columns
        metadata_has_geology = self.site_metadata is not None and geology_group_col in self.site_metadata.columns
        if not event_has_geology and not metadata_has_geology:
            self._progress("skip spatial_geology_contrast: station geology metadata missing")
            return outputs
        geomorphology_col = "geomorphology"
        has_geomorphology = self.site_metadata is not None and geomorphology_col in self.site_metadata.columns
        for item in self._iter_geology_contrast_items(
            event_centered,
            passband=passband,
            components=components,
            model=model,
        ):
            class_values = self._defined_geology_class_values(item.get("df"))
            baseline_values = ("Basin",) if class_values and "Basin" in class_values else None
            compare_values = tuple(value for value in class_values or () if value != "Basin") if baseline_values else None
            output = self.write_spatial_plot(
                "spatial_geology_contrast",
                item,
                func,
                required=["station", geology_value_col],
                value_col=geology_value_col,
                forward_value_col=True,
                showfig=showfig,
                station_metadata=self.site_metadata,
                contrast_df=None,
                group_col=geology_group_col,
                baseline_values=baseline_values,
                compare_values=compare_values,
                class_values=class_values,
                title=f"{item['label']} Residuals by Geology Class",
                robust_axis_percentile=robust_axis_percentile,
            )
            if output is not None:
                outputs.append(output)
            if not has_geomorphology:
                continue
            geomorphology_values = self._defined_geology_class_values(item.get("df"), group_col=geomorphology_col)
            if not geomorphology_values or len(geomorphology_values) < 2:
                continue
            geomorphology_output = self.write_spatial_plot(
                "spatial_geomorphology_contrast",
                item,
                func,
                required=["station", geology_value_col],
                value_col=geology_value_col,
                forward_value_col=True,
                showfig=showfig,
                station_metadata=self.site_metadata,
                contrast_df=None,
                group_col=geomorphology_col,
                class_values=geomorphology_values,
                pairwise_contrasts=True,
                title=f"{item['label']} Residuals by Geomorphology",
                robust_axis_percentile=robust_axis_percentile,
            )
            if geomorphology_output is not None:
                outputs.append(geomorphology_output)
        return outputs

    def _iter_geology_contrast_items(
        self,
        event_centered: pd.DataFrame,
        *,
        passband: str | None,
        components: list[str] | str | None,
        model: str | None,
    ):
        """Yield combined geology items plus per-passband items when useful."""

        seen: set[tuple[str, str]] = set()
        for item in self.iter_metric_frames(
            event_centered,
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            key = (str(item.get("key")), str(dimension_value(item.get("df"), self.band_col, "all-passbands")))
            seen.add(key)
            yield item

        if passband is not None or self.band_col is None or self.band_col not in event_centered.columns:
            return
        band_values = [
            str(value)
            for value in sorted(pd.unique(event_centered[self.band_col].dropna()), key=lambda value: str(value))
            if str(value).strip()
        ]
        if len(band_values) <= 1:
            return
        for band_value in band_values:
            for item in self.iter_metric_frames(
                event_centered,
                passband=band_value,
                components=components,
                model=model,
                split_psa_period=False,
            ):
                key = (str(item.get("key")), str(dimension_value(item.get("df"), self.band_col, "all-passbands")))
                if key in seen:
                    continue
                seen.add(key)
                yield item

    def _defined_geology_class_values(self, rows: pd.DataFrame | None, *, group_col: str | None = None) -> tuple[str, ...] | None:
        """Return defined geology classes represented by a selected event-row frame."""

        if rows is None or rows.empty:
            return None
        selected_group_col = group_col or self.geology_group_col
        if selected_group_col in rows.columns:
            values = rows[selected_group_col]
        elif self.site_metadata is not None and "station" in rows.columns and selected_group_col in self.site_metadata.columns:
            station_metadata = self.site_metadata[["station", selected_group_col]].drop_duplicates(subset=["station"])
            values = rows[["station"]].merge(station_metadata, on="station", how="left")[selected_group_col]
        else:
            return None
        classes = sorted({str(value).strip() for value in values.dropna() if _is_defined_geology_class(value)})
        return tuple(classes) if classes else None

    def _context_for(self, df: pd.DataFrame | None) -> MetricFigureContext | None:
        """Return the metric or event context that owns one dataframe."""

        if df is None or df.empty:
            return None
        owner = getattr(df, "attrs", {}).get(SPATIAL_CONTEXT_ATTR)
        if owner == "event":
            return self.event_context
        if owner == "metric":
            return self.metric_context
        table_key = getattr(df, "attrs", {}).get(SPATIAL_TABLE_KEY_ATTR)
        if table_key == "event_centered_residuals":
            return self.event_context
        if table_key == "metric_field":
            return self.metric_context
        if df is self.event_centered:
            return self.event_context
        if df is self.metric_field:
            return self.metric_context
        event = self.event_centered
        if event is not None and set(df.columns).issubset(set(event.columns)):
            return self.event_context
        return self.metric_context

    def _context_for_item(self, item: dict[str, Any]) -> MetricFigureContext | None:
        """Return the context explicitly assigned to a spatial figure item."""

        owner = item.get(SPATIAL_CONTEXT_ATTR)
        if owner == "event":
            return self.event_context
        if owner == "metric":
            return self.metric_context
        return self._context_for(item.get("df"))

    def _context_name(self, context: MetricFigureContext | None) -> str:
        """Return the sidecar context name for one metric figure context."""

        return "event" if context is self.event_context else "metric"


@dataclass(frozen=True)
class RegionBoxplotResult:
    """Result from writing a large-run GeoJSON region boxplot."""

    figure_path: Path | None
    sidecar_path: Path | None
    rows: int
    status: str
    message: str
    comparison_table: pd.DataFrame = field(default_factory=pd.DataFrame)

    def status_frame(self) -> pd.DataFrame:
        """Return a compact notebook status table for the region boxplot."""

        figure_path = None if self.figure_path is None else str(self.figure_path)
        sidecar_path = None if self.sidecar_path is None else str(self.sidecar_path)
        frame = normalize_figure_status_rows(
            [
                {
                    "artifact": "region_boxplot",
                    "status": self.status,
                    "row_count": self.rows,
                    "figure_path": figure_path,
                    "figure_exists": bool(self.figure_path is not None and self.figure_path.exists()),
                    "sidecar_path": sidecar_path,
                    "sidecar_exists": bool(self.sidecar_path is not None and self.sidecar_path.exists()),
                    "message": self.message,
                }
            ]
        )
        return frame.reindex(
            columns=[
                "name",
                "artifact_label",
                "artifact_role",
                "resolved_path",
                "path",
                "exists",
                "artifact",
                "status",
                "status_reason",
                "row_count",
                "figure_path",
                "figure_exists",
                "sidecar_path",
                "sidecar_exists",
                "message",
            ]
        )

    def comparison_frame(self) -> pd.DataFrame:
        """Return the statistical comparison table drawn below the boxplot."""

        return self.comparison_table.copy()


@dataclass(frozen=True)
class RegionFigureResult:
    """Result from writing the large-run GeoJSON/corridor figure family."""

    geojson_overview_path: Path | None
    corridor_map_path: Path | None
    boxplot_result: RegionBoxplotResult
    geojson_status: str
    corridor_status: str
    messages: tuple[str, ...]

    def status_frame(self) -> pd.DataFrame:
        """Return a compact notebook status table for region figure outputs."""

        geojson_path = None if self.geojson_overview_path is None else str(self.geojson_overview_path)
        corridor_path = None if self.corridor_map_path is None else str(self.corridor_map_path)
        boxplot_path = None if self.boxplot_result.figure_path is None else str(self.boxplot_result.figure_path)
        boxplot_sidecar_path = None if self.boxplot_result.sidecar_path is None else str(self.boxplot_result.sidecar_path)
        rows = [
            {
                "artifact": "geojson_overview",
                "status": self.geojson_status,
                "resolved_path": geojson_path,
                "path": geojson_path,
                "exists": bool(self.geojson_overview_path is not None and self.geojson_overview_path.exists()),
                "sidecar_path": None,
                "sidecar_exists": None,
                "message": self._message_for("geojson_overview"),
            },
            {
                "artifact": "corridor_map",
                "status": self.corridor_status,
                "resolved_path": corridor_path,
                "path": corridor_path,
                "exists": bool(self.corridor_map_path is not None and self.corridor_map_path.exists()),
                "sidecar_path": None,
                "sidecar_exists": None,
                "message": self._message_for("corridor_map"),
            },
            {
                "artifact": "region_boxplot",
                "status": self.boxplot_result.status,
                "resolved_path": boxplot_path,
                "path": boxplot_path,
                "exists": bool(
                    self.boxplot_result.figure_path is not None and self.boxplot_result.figure_path.exists()
                ),
                "sidecar_path": boxplot_sidecar_path,
                "sidecar_exists": bool(
                    self.boxplot_result.sidecar_path is not None and self.boxplot_result.sidecar_path.exists()
                ),
                "message": self.boxplot_result.message,
            },
        ]
        frame = normalize_figure_status_rows(rows)
        return frame.reindex(
            columns=[
                "name",
                "artifact_label",
                "artifact_role",
                "resolved_path",
                "path",
                "exists",
                "artifact",
                "status",
                "status_reason",
                "sidecar_path",
                "sidecar_exists",
                "message",
            ]
        )

    def _message_for(self, artifact: str) -> str | None:
        """Return the first message tagged for one artifact."""

        prefix = f"{artifact}: "
        for message in self.messages:
            if message.startswith(prefix):
                return message[len(prefix):]
        return None

    def comparison_frame(self) -> pd.DataFrame:
        """Return the region-boxplot statistical comparison table."""

        return self.boxplot_result.comparison_frame()


@dataclass(frozen=True)
class StandardGeoJSONFigureResult:
    """Result from writing standard Step 5 GeoJSON region figures."""

    rows: tuple[dict[str, Any], ...]
    region_preview: pd.DataFrame
    metrics_by_regions: pd.DataFrame
    model_name: str
    summary: Mapping[str, Any] | None = None

    def status_frame(self) -> pd.DataFrame:
        """Return one row per Step 5 region figure written or skipped."""

        frame = normalize_figure_status_rows(self.rows)
        return frame.reindex(
            columns=[
                "name",
                "artifact_label",
                "artifact_role",
                "resolved_path",
                "path",
                "exists",
                "artifact",
                "status",
                "status_reason",
                "row_count",
                "figure_path",
                "figure_exists",
                "message",
            ]
        )

    def preview_frame(self) -> pd.DataFrame:
        """Return a compact table of configured GeoJSON regions."""

        return self.region_preview.copy()

    def summary_frame(self) -> pd.DataFrame:
        """Return the configured GeoJSON summary workflow status as a table."""

        if not self.summary:
            return pd.DataFrame()
        return pd.DataFrame([dict(self.summary)])


@dataclass(frozen=True)
class StandardGeoJSONCorridorFigureResult:
    """Result from writing standard Step 5 corridor and record-section figures."""

    rows: tuple[dict[str, Any], ...]
    boundary_crossing_preview: pd.DataFrame
    outward_event_preview: pd.DataFrame
    metrics_by_regions: pd.DataFrame

    def status_frame(self) -> pd.DataFrame:
        """Return one row per Step 5 corridor figure written or skipped."""

        frame = normalize_figure_status_rows(self.rows)
        return frame.reindex(
            columns=[
                "name",
                "artifact_label",
                "artifact_role",
                "resolved_path",
                "path",
                "exists",
                "artifact",
                "status",
                "status_reason",
                "row_count",
                "figure_path",
                "figure_exists",
                "message",
            ]
        )

    def boundary_crossing_frame(self) -> pd.DataFrame:
        """Return a bounded preview of paths used by the record section."""

        return self.boundary_crossing_preview.copy()

    def outward_event_frame(self) -> pd.DataFrame:
        """Return events selected by the outward corridor."""

        return self.outward_event_preview.copy()


def _loaded_spatial_input_status_frame(
    items: Sequence[tuple[str, pd.DataFrame | None, str | Path | None]],
) -> pd.DataFrame:
    """Return normalized notebook status rows for loaded spatial inputs."""

    rows: list[dict[str, Any]] = []
    for name, frame, path_value in items:
        path = Path(path_value).expanduser() if path_value is not None else None
        has_path = path is not None
        exists = path.exists() if path is not None else True
        status = ("ready" if exists else "missing") if has_path else "loaded"
        rows.append(
            {
                "name": name,
                "table": name,
                "artifact": name,
                "artifact_label": str(name).replace("_", " ") + (" file" if has_path else " table"),
                "artifact_role": "input_file" if has_path else "input_table",
                "status": status,
                "exists": exists,
                "rows": None if frame is None else len(frame),
                "resolved_path": "" if path is None else str(path),
                "path": "" if path is None else str(path),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "name",
            "table",
            "artifact",
            "artifact_label",
            "artifact_role",
            "status",
            "exists",
            "rows",
            "resolved_path",
            "path",
        ],
    )


@dataclass(frozen=True)
class StandardGeoJSONPlottingInputResult:
    """Configured input tables and output group for the standard Step 5 notebook."""

    metrics: pd.DataFrame
    stations: pd.DataFrame
    events: pd.DataFrame
    event_stations: pd.DataFrame
    comparison_eligible: pd.DataFrame
    geojson_path: Path
    outputs: Any

    def status_frame(self) -> pd.DataFrame:
        """Return a compact row-count/path table for loaded Step 5 inputs."""

        return _loaded_spatial_input_status_frame(
            [
                ("region_geojson", None, self.geojson_path),
                ("metrics", self.metrics, None),
                ("stations", self.stations, None),
                ("events", self.events, None),
                ("event_stations", self.event_stations, None),
                ("comparison_eligible", self.comparison_eligible, None),
            ]
        )

    def write_region_figures(
        self,
        *,
        settings: Any,
        value_col: str = "log2_residual",
        passbands: Sequence[str] | str | None = ("1-2 sec", "2-3 sec"),
        component: str | Sequence[str] | None = "Z",
        station_region: str = "LA Basin",
        event_region: str = "Glendale",
        metric: str = "PGA",
        compare_to: str = "LA Basin",
        model: str | None = None,
        summary_metrics_table: pd.DataFrame | str | Path | None = "paths.metric_figure_snapshot",
        summary_geojson_path: str | Path | None = "paths.region_geojson",
        summary_chunksize: int | None = 100_000,
        summary_func: Callable[..., Mapping[str, Any]] | None = None,
    ) -> "StandardGeoJSONFigureResult":
        """Write standard Step 5 region figures from configured inputs."""

        return write_standard_geojson_region_figures(
            metrics=self.metrics,
            stations=self.stations,
            events=self.events,
            outputs=self.outputs,
            settings=settings,
            geojson_path=self.geojson_path,
            value_col=value_col,
            passbands=passbands,
            component=component,
            station_region=station_region,
            event_region=event_region,
            metric=metric,
            compare_to=compare_to,
            model=model,
            summary_metrics_table=summary_metrics_table,
            summary_geojson_path=summary_geojson_path,
            summary_chunksize=summary_chunksize,
            summary_func=summary_func,
        )

    def write_corridor_figures(
        self,
        *,
        metrics_by_regions: pd.DataFrame,
        spatial_settings: Any,
        waveform_settings: Any,
        value_col: str = "log2_residual",
        passbands: Sequence[str] | str | None = ("1-2 sec", "2-3 sec"),
        component: str | None = "Z",
        boundary_region: str = "LA Basin",
        through_anchor_station: str = "OLI",
        outward_event_id: str = "ci38695658",
        corridor_station_region: str = "LA Basin",
        record_component: str = "R",
        record_passband: str = "1-2 sec",
        display_func: Callable[[Any], Any] | None = None,
    ) -> "StandardGeoJSONCorridorFigureResult":
        """Write standard Step 5 corridor figures from configured inputs."""

        return write_standard_geojson_corridor_figures(
            metrics_by_regions=metrics_by_regions,
            stations=self.stations,
            event_stations=self.event_stations,
            events=self.events,
            comparison_eligible=self.comparison_eligible,
            outputs=self.outputs,
            spatial_settings=spatial_settings,
            waveform_settings=waveform_settings,
            geojson_path=self.geojson_path,
            value_col=value_col,
            passbands=passbands,
            component=component,
            boundary_region=boundary_region,
            through_anchor_station=through_anchor_station,
            outward_event_id=outward_event_id,
            corridor_station_region=corridor_station_region,
            record_component=record_component,
            record_passband=record_passband,
            display_func=display_func,
        )


@dataclass(frozen=True)
class StandardGeoJSONWorkflowOutputStatusResult:
    """Configured Step 5 output status and bounded preview helpers."""

    outputs: Any
    cfg: Any | None = None

    def status_frame(self) -> pd.DataFrame:
        """Return configured Step 5 output path status."""

        return self.outputs.status_frame()

    def step_result(self, readiness: Any, **values: Any) -> dict[str, Any]:
        """Return a standard fallback payload for a skipped Step 5 gate."""

        from spatial_vtk.config import notebook_step_result

        return notebook_step_result(readiness, **values)

    def geojson_summary_step_result(self, readiness: Any) -> dict[str, Any]:
        """Return the fallback payload for the GeoJSON summary gate."""

        return self.step_result(
            readiness,
            geojson_summaries_path=self.outputs.geojson_summaries_path,
        )

    def corridor_step_result(self, readiness: Any) -> dict[str, Any]:
        """Return the fallback payload for the corridor-table gate."""

        return self.step_result(
            readiness,
            corridors_path=self.outputs.corridors_path,
        )

    def run_geojson_summary_step_if_needed(
        self,
        context: Any,
        *,
        overwrite: bool = False,
        chunksize: int = 1_000_000,
        verbose: bool = True,
        current_message: str | None = "GeoJSON summary table is current; skipping.",
        script_name: str = "step05_geojson_summaries.slurm",
        job_name: str = "svtk-step05-geojson",
        walltime: str = "08:00:00",
        memory: str = "32G",
        cpus: int = 1,
        run_local: bool | None = None,
        section: str | None = "compute.slurm",
        display_fn: Any | None = None,
    ) -> object:
        """Run or submit configured Step 5 GeoJSON region summaries when stale."""

        from spatial_vtk.config import run_notebook_step_if_needed
        from spatial_vtk.spatial.calculate.geojson import run_geojson_region_summary_workflow_from_config
        from spatial_vtk.spatial.calculate.workflow import geojson_region_summary_readiness_from_config

        config_path = _geojson_result_config_path(self.cfg, context)
        run_scenario = _geojson_result_run_scenario(self.cfg, context)
        readiness = geojson_region_summary_readiness_from_config(
            config_path=config_path,
            run_scenario=run_scenario,
            overwrite=overwrite,
        )
        if current_message is not None and getattr(readiness, "reason", None) == "current":
            readiness = replace(readiness, message=current_message)
        result = run_notebook_step_if_needed(
            context,
            readiness,
            run_geojson_region_summary_workflow_from_config,
            kwargs={
                "config_path": str(config_path) if config_path is not None else None,
                "run_scenario": run_scenario,
                "chunksize": chunksize,
                "verbose": verbose,
            },
            script_name=script_name,
            job_name=job_name,
            walltime=walltime,
            memory=memory,
            cpus=cpus,
            run_local=run_local,
            section=section,
            display_fn=display_fn,
        )
        return result or self.geojson_summary_step_result(readiness)

    def run_corridor_step_if_needed(
        self,
        context: Any,
        *,
        overwrite: bool = False,
        verbose: bool = True,
        current_message: str | None = "Corridor table is current; skipping.",
        script_name: str = "step05_corridors.slurm",
        job_name: str = "svtk-step05-corridors",
        walltime: str = "02:00:00",
        memory: str = "8G",
        cpus: int = 1,
        run_local: bool | None = None,
        section: str | None = "compute.slurm",
        display_fn: Any | None = None,
    ) -> object:
        """Run or submit configured Step 5 corridor tables when stale."""

        from spatial_vtk.config import run_notebook_step_if_needed
        from spatial_vtk.spatial.calculate.corridors import run_boundary_corridor_workflow_from_config
        from spatial_vtk.spatial.calculate.workflow import boundary_corridor_readiness_from_config

        config_path = _geojson_result_config_path(self.cfg, context)
        run_scenario = _geojson_result_run_scenario(self.cfg, context)
        readiness = boundary_corridor_readiness_from_config(
            config_path=config_path,
            run_scenario=run_scenario,
            overwrite=overwrite,
        )
        if current_message is not None and getattr(readiness, "reason", None) == "current":
            readiness = replace(readiness, message=current_message)
        result = run_notebook_step_if_needed(
            context,
            readiness,
            run_boundary_corridor_workflow_from_config,
            kwargs={
                "config_path": str(config_path) if config_path is not None else None,
                "run_scenario": run_scenario,
                "verbose": verbose,
            },
            script_name=script_name,
            job_name=job_name,
            walltime=walltime,
            memory=memory,
            cpus=cpus,
            run_local=run_local,
            section=section,
            display_fn=display_fn,
        )
        return result or self.corridor_step_result(readiness)

    def display_table_previews(
        self,
        *,
        cfg: Any | None = None,
        nrows: int = 5,
        display_fn: Any | None = None,
    ) -> dict[str, object]:
        """Display bounded previews of the core Step 5 GeoJSON output tables."""

        return self.outputs.display_table_previews(
            {
                "geojson_region_summaries": "geojson_region_summaries",
                "corridors": "corridors",
            },
            cfg=cfg or self.cfg,
            nrows=nrows,
            display_fn=display_fn,
        )

    def write_region_figures(
        self,
        ingest_outputs: Any,
        settings: Any | None = None,
        *,
        geojson_path: str | Path | None = None,
        cfg: Any | None = None,
        overwrite: bool = False,
    ) -> "RegionFigureResult":
        """Write Step 5 GeoJSON/corridor figures from this output bundle."""

        resolved_cfg = cfg or self.cfg
        if settings is None:
            settings = ingest_outputs
            from spatial_vtk.io import load_configured_input_paths, load_standard_ingest_workflow_outputs

            ingest_outputs = load_standard_ingest_workflow_outputs(cfg=resolved_cfg).outputs
            geojson_path = load_configured_input_paths({"region_geojson": "paths.region_geojson"}, cfg=resolved_cfg)[
                "region_geojson"
            ]
        elif geojson_path is None:
            raise ValueError(
                "geojson_path is required when passing explicit ingest outputs. "
                "Pass only settings to resolve standard Step 5 inputs from the active config."
            )

        return write_large_run_geojson_region_figures_from_notebook_settings(
            self,
            ingest_outputs,
            settings,
            geojson_path=geojson_path,
            cfg=resolved_cfg,
            overwrite=overwrite,
        )


@dataclass(frozen=True)
class StandardAdditionalPlottingFigureResult:
    """Result from writing standard Step 6 additional plotting figures."""

    rows: tuple[dict[str, Any], ...]
    metric_summary: pd.DataFrame
    waveform_order: pd.DataFrame
    region_metrics: pd.DataFrame
    pattern_rows: pd.DataFrame

    def status_frame(self) -> pd.DataFrame:
        """Return one row per Step 6 figure written or skipped."""

        frame = normalize_figure_status_rows(self.rows)
        return frame.reindex(
            columns=[
                "name",
                "artifact_label",
                "artifact_role",
                "resolved_path",
                "path",
                "exists",
                "artifact",
                "status",
                "status_reason",
                "row_count",
                "figure_path",
                "figure_exists",
                "message",
            ]
        )

    def metric_summary_frame(self) -> pd.DataFrame:
        """Return a compact summary of the metric and comparison inputs."""

        return self.metric_summary.copy()

    def waveform_order_frame(self) -> pd.DataFrame:
        """Return the plotted waveform station order preview."""

        return self.waveform_order.copy()

    def pattern_frame(self) -> pd.DataFrame:
        """Return the pattern-similarity rows used by the figure."""

        return self.pattern_rows.copy()

    def pattern_preview_frame(self, nrows: int = 5) -> pd.DataFrame:
        """Return a bounded preview of pattern-similarity rows."""

        return self.pattern_rows.head(nrows).copy()


@dataclass(frozen=True)
class StandardAdditionalPlottingInputResult:
    """Configured input tables and output group for the standard Step 6 notebook."""

    metrics: pd.DataFrame
    event_stations: pd.DataFrame
    events: pd.DataFrame
    comparison_eligible: pd.DataFrame
    outputs: Any

    def status_frame(self) -> pd.DataFrame:
        """Return a compact row-count table for loaded Step 6 inputs."""

        return _loaded_spatial_input_status_frame(
            [
                ("metrics", self.metrics, None),
                ("event_stations", self.event_stations, None),
                ("events", self.events, None),
                ("comparison_eligible", self.comparison_eligible, None),
            ]
        )

    def write_figures(
        self,
        *,
        waveform_settings: Any,
        metric_settings: Any,
        **kwargs: Any,
    ) -> "StandardAdditionalPlottingFigureResult":
        """Write standard Step 6 figures from configured input tables.

        The standard additional-plotting notebook uses this method so the
        loaded input bundle owns metric rows, prepared event metadata,
        comparison-eligible rows, and the Step 6 output group. Additional
        keyword arguments are forwarded to
        :func:`write_standard_additional_plotting_figures`.
        """

        return write_standard_additional_plotting_figures(
            metrics=self.metrics,
            event_stations=self.event_stations,
            events=self.events,
            comparison_eligible=self.comparison_eligible,
            outputs=self.outputs,
            waveform_settings=waveform_settings,
            metric_settings=metric_settings,
            **kwargs,
        )


@dataclass(frozen=True)
class StandardAdditionalPlottingOutputStatusResult:
    """Configured Step 6 output status and bounded preview helpers."""

    outputs: Any
    cfg: Any | None = None

    def status_frame(self) -> pd.DataFrame:
        """Return configured Step 6 output path status."""

        return self.outputs.status_frame()

    def display_metric_source_preview(
        self,
        *,
        cfg: Any | None = None,
        nrows: int = 5,
        display_fn: Any | None = None,
        missing_message: str = "Metric plotting source is not ready yet.",
    ) -> dict[str, object]:
        """Display a bounded preview of the first available metric source table."""

        return self.outputs.display_first_existing_table_preview(
            ("metrics_enriched_path", "metrics_long_path"),
            cfg=cfg or self.cfg,
            nrows=nrows,
            display_fn=display_fn,
            missing_message=missing_message,
        )

    def write_waveform_comparison(
        self,
        settings: Any,
        *,
        max_records: int | None = 12,
        max_distance_km: float | None = 50.0,
        chunksize: int = 1_000_000,
        overwrite: bool = False,
        event_id: str | list[str] | tuple[str, ...] | None = None,
        component: str | None = None,
        passband: str | None = None,
        fallback_to_available: bool = False,
        plot_options: dict[str, Any] | None = None,
    ) -> object:
        """Write a bounded Step 6 waveform comparison from this output bundle."""

        from spatial_vtk.visualize.waveforms import write_waveform_comparison_from_notebook_settings

        return write_waveform_comparison_from_notebook_settings(
            self,
            settings,
            max_records=max_records,
            max_distance_km=max_distance_km,
            chunksize=chunksize,
            overwrite=overwrite,
            event_id=event_id,
            component=component,
            passband=passband,
            fallback_to_available=fallback_to_available,
            plot_options=plot_options,
        )

    def write_region_boxplot(
        self,
        settings: Any,
        *,
        output_prefix: str = "additional_region_boxplot",
        geojson_path: str | Path | None = None,
        annotate_if_missing: bool = False,
        overwrite: bool = False,
    ) -> "RegionBoxplotResult":
        """Write the Step 6 region boxplot from this output bundle."""

        return write_large_run_region_boxplot_from_notebook_settings(
            self,
            settings,
            output_prefix=output_prefix,
            geojson_path=geojson_path,
            cfg=self.cfg,
            annotate_if_missing=annotate_if_missing,
            overwrite=overwrite,
        )


@dataclass(frozen=True)
class SpatialSummaryFigureResult:
    """Result from writing compact large-run spatial summary figures."""

    station_bias_path: Path | None
    station_bias_figure_path: Path | None
    status: str
    row_count: int = 0
    message: str = ""

    def status_frame(self) -> pd.DataFrame:
        """Return a compact notebook status table for summary figures."""

        frame = normalize_figure_status_rows(
            [
                {
                    "artifact": "station_bias_map",
                    "status": self.status,
                    "row_count": self.row_count,
                    "input_path": None if self.station_bias_path is None else str(self.station_bias_path),
                    "figure_path": None if self.station_bias_figure_path is None else str(self.station_bias_figure_path),
                    "figure_exists": bool(
                        self.station_bias_figure_path is not None and self.station_bias_figure_path.exists()
                    ),
                    "message": self.message,
                }
            ]
        )
        return frame.reindex(
            columns=[
                "name",
                "artifact_label",
                "artifact_role",
                "resolved_path",
                "path",
                "exists",
                "artifact",
                "status",
                "status_reason",
                "row_count",
                "input_path",
                "figure_path",
                "figure_exists",
                "message",
            ]
        )


@dataclass(frozen=True)
class StandardSpatialMapFigureResult:
    """Result from writing standard Step 4 spatial map figures."""

    rows: tuple[dict[str, Any], ...]

    def status_frame(self) -> pd.DataFrame:
        """Return a compact notebook status table for written spatial figures."""

        frame = normalize_figure_status_rows(self.rows)
        return frame.reindex(
            columns=[
                "name",
                "artifact_label",
                "artifact_role",
                "resolved_path",
                "path",
                "exists",
                "artifact",
                "metric",
                "status",
                "status_reason",
                "row_count",
                "figure_path",
                "figure_exists",
                "message",
            ],
        )


@dataclass(frozen=True)
class StandardSpatialDiagnosticFigureResult:
    """Result from writing standard Step 4 diagnostic figures."""

    rows: tuple[dict[str, Any], ...]
    preview_rows: tuple[pd.DataFrame, ...] = ()

    def status_frame(self) -> pd.DataFrame:
        """Return one row per diagnostic figure written or skipped."""

        frame = normalize_figure_status_rows(self.rows)
        return frame.reindex(
            columns=[
                "name",
                "artifact_label",
                "artifact_role",
                "resolved_path",
                "path",
                "exists",
                "artifact",
                "metric",
                "status",
                "status_reason",
                "row_count",
                "figure_path",
                "figure_exists",
                "message",
            ],
        )

    def preview_frame(self) -> pd.DataFrame:
        """Return compact diagnostic tables used by the plotted figures."""

        frames = [frame for frame in self.preview_rows if frame is not None and not frame.empty]
        if not frames:
            return pd.DataFrame(columns=["artifact", "metric"])
        return pd.concat(frames, ignore_index=True, sort=False)


@dataclass(frozen=True)
class SpatialFigureSuiteResult:
    """Result from rendering the full large-run Step 4 spatial figure suite."""

    context: SpatialFigureContext
    rows: tuple[dict[str, Any], ...]

    def context_status_frames(self) -> dict[str, pd.DataFrame]:
        """Return compact spatial figure context audit frames for notebooks."""

        return {
            "context_status": self.context.status_frame(),
            "dimension_summary": self.context.dimension_summary_frame(),
            "spectral_metric_contract": self.context.spectral_metric_contract_status(),
        }

    def display_context_status(
        self,
        *,
        display: Callable[[pd.DataFrame], Any] | None = None,
    ) -> dict[str, pd.DataFrame]:
        """Display and return the standard spatial figure context audit frames."""

        frames = self.context_status_frames()
        if display is not None:
            for frame in frames.values():
                display(frame)
        return frames

    def status_frame(self) -> pd.DataFrame:
        """Return one row per spatial figure family rendered or skipped."""

        frame = normalize_figure_status_rows(self.rows)
        frame = add_figure_family_sidecar_status(
            frame,
            sidecar_dir=getattr(self.context, "sidecar_output_dir", None),
            enabled=bool(getattr(self.context, "write_sidecars", False)),
        )
        return frame.reindex(
            columns=[
                "name",
                "artifact_label",
                "artifact_role",
                "resolved_path",
                "path",
                "exists",
                "artifact",
                "status",
                "status_reason",
                "figure_count",
                "existing_figure_count",
                "figure_paths",
                "first_figure_path",
                "figure_paths_preview",
                "sidecar_dir",
                "sidecar_metadata_count",
                "sidecar_count",
                "sidecar_missing_count",
                "source_sidecar_count",
                "source_sidecar_missing_count",
                "plot_row_count_total",
                "written_row_count_total",
                "plot_sidecar_all_exact",
                "source_row_count_total",
                "source_written_row_count_total",
                "source_sidecar_all_exact",
                "sidecar_sampled_count",
                "source_sidecar_sampled_count",
                "message",
            ]
        )

    def diagnostic_preview_frame(self, nrows: int = 5) -> pd.DataFrame:
        """Return bounded previews of statistical tables used by spatial figures."""

        frames: list[pd.DataFrame] = []
        for artifact, key in (
            ("morans_i", "morans_i"),
            ("distance_bin_correlations", "distance_bin_correlations"),
            ("pca_explained_variance", "pca_explained_variance"),
            ("pca_feature_loadings", "pca_feature_loadings"),
            ("cluster_solution_scores", "cluster_solution_scores"),
            ("cluster_feature_summary", "cluster_feature_summary"),
            ("geology_contrasts", "geology_contrasts"),
        ):
            table = self.context.table(key)
            if table is None or table.empty:
                continue
            preview = table.head(max(int(nrows), 0)).copy()
            preview.insert(0, "artifact", artifact)
            frames.append(preview)
        if not frames:
            return pd.DataFrame(columns=["artifact"])
        return pd.concat(frames, ignore_index=True, sort=False)


def prepare_spatial_figure_context(**kwargs: Any) -> SpatialFigureContext:
    """Return a reusable spatial figure context for large-run notebooks."""

    return SpatialFigureContext.from_config(**kwargs)


def prepare_spatial_figure_context_from_notebook_settings(
    settings: Any,
    *,
    overwrite: bool = False,
    include_station_aggregation: bool = False,
    **overrides: Any,
) -> SpatialFigureContext:
    """Return a spatial figure context from notebook figure settings.

    Public notebooks use :func:`spatial_vtk.config.notebook_figure_settings`
    for figure switches. This adapter keeps those notebooks from repeating the
    individual context keyword names while preserving the lower-level
    ``prepare_spatial_figure_context`` API for scripts.
    """

    context_kwargs = dict(settings.context_kwargs(include_station_aggregation=include_station_aggregation))
    context_kwargs.setdefault("verbose", False)
    context_kwargs.update(overrides)
    return prepare_spatial_figure_context(
        figure_dir=settings.figure_dir,
        overwrite=overwrite,
        **context_kwargs,
    )


def _spatial_suite_status_row(
    artifact: str,
    outputs: Sequence[Path],
    *,
    message: str = "",
    status_reason: str | None = None,
) -> dict[str, Any]:
    """Return one notebook status row for a spatial figure family."""

    paths = [Path(path) for path in outputs]
    preview = ", ".join(str(path) for path in paths[:3])
    if len(paths) > 3:
        preview += f", ... (+{len(paths) - 3} more)"
    resolved_status_reason = status_reason or ("written" if paths else "no_figures_written")
    return {
        "artifact": artifact,
        "status": "written" if paths else "skipped",
        "status_reason": resolved_status_reason,
        "figure_count": int(len(paths)),
        "existing_figure_count": int(sum(path.exists() for path in paths)),
        "figure_paths": [str(path) for path in paths],
        "first_figure_path": None if not paths else str(paths[0]),
        "figure_paths_preview": preview,
        "message": message if message else ("" if paths else "No figures were written; check context status and missing-table messages above."),
    }


def write_large_run_spatial_figure_suite_from_notebook_settings(
    settings: Any,
    *,
    cfg: ConfigInput | None = None,
    overwrite: bool = False,
    station_metric_map_func: Callable[..., Any] | None = None,
    station_metric_map_by_period_func: Callable[..., Any] | None = None,
    station_bias_map_func: Callable[..., Any] | None = None,
    residual_grid_func: Callable[..., Any] | None = None,
    metric_by_model_map_func: Callable[..., Any] | None = None,
    event_residual_map_func: Callable[..., Any] | None = None,
    azimuthal_residuals_func: Callable[..., Any] | None = None,
    polar_residuals_func: Callable[..., Any] | None = None,
    pca_summary_func: Callable[..., Any] | None = None,
) -> SpatialFigureSuiteResult:
    """Render the full large-run Step 4 spatial figure suite.

    This helper keeps the large-run spatial notebook as a lightweight driver:
    it owns the public plotting-function imports, repeated selection keyword
    expansion, PSA period-sheet handling, and station-aggregation source-row
    sidecars while still returning the reusable context for status displays.
    """

    if any(
        func is None
        for func in (
            station_metric_map_func,
            station_metric_map_by_period_func,
            station_bias_map_func,
            residual_grid_func,
            metric_by_model_map_func,
            event_residual_map_func,
            pca_summary_func,
        )
    ):
        from spatial_vtk.spatial.map import (
            plot_event_residual_map,
            plot_metric_map_by_model,
            plot_pca_summary,
            plot_residual_grid,
            plot_station_bias_map,
            plot_station_metric_map,
            plot_station_metric_map_by_period,
        )

        station_metric_map_func = station_metric_map_func or plot_station_metric_map
        station_metric_map_by_period_func = station_metric_map_by_period_func or plot_station_metric_map_by_period
        station_bias_map_func = station_bias_map_func or plot_station_bias_map
        residual_grid_func = residual_grid_func or plot_residual_grid
        metric_by_model_map_func = metric_by_model_map_func or plot_metric_map_by_model
        event_residual_map_func = event_residual_map_func or plot_event_residual_map
        pca_summary_func = pca_summary_func or plot_pca_summary
    if azimuthal_residuals_func is None or polar_residuals_func is None:
        from spatial_vtk.spatial.plot import plot_azimuthal_residuals, plot_polar_residuals

        azimuthal_residuals_func = azimuthal_residuals_func or plot_azimuthal_residuals
        polar_residuals_func = polar_residuals_func or plot_polar_residuals

    context = prepare_spatial_figure_context_from_notebook_settings(
        settings,
        cfg=cfg,
        overwrite=overwrite,
        include_station_aggregation=True,
    )
    rows: list[dict[str, Any]] = []
    if not settings.make_figures:
        rows.append(
            {
                "artifact": "spatial_figure_suite",
                "status": "skipped",
                "status_reason": "disabled",
                "figure_count": 0,
                "existing_figure_count": 0,
                "figure_paths": [],
                "first_figure_path": None,
                "figure_paths_preview": "",
                "message": "Set SVTK_MAKE_SPATIAL_FIGURES=1 or SVTK_MAKE_FIGURES=1 to render spatial figures.",
            }
        )
        return SpatialFigureSuiteResult(context=context, rows=tuple(rows))

    metric_value_col = context.metric_value_col
    event_value_col = context.event_value_col

    metric_kwargs = settings.plot_selection_kwargs(value_col=metric_value_col)
    event_metric_kwargs = settings.plot_selection_kwargs(value_col=event_value_col)
    rows.append(
        _spatial_suite_status_row(
            "station_metric_maps",
            context.write_station_metric_maps(
                station_metric_map_func,
                station_metric_map_by_period_func,
                **metric_kwargs,
            ),
        )
    )
    rows.append(
        _spatial_suite_status_row(
            "station_metric_maps_event_centered",
            context.write_station_metric_maps(
                station_metric_map_func,
                station_metric_map_by_period_func,
                event_centered=True,
                **event_metric_kwargs,
            ),
        )
    )
    rows.append(
        _spatial_suite_status_row(
            "station_bias_maps_raw",
            context.write_station_bias_maps(
                station_bias_map_func,
                event_centered=False,
                **metric_kwargs,
            ),
        )
    )
    rows.append(
        _spatial_suite_status_row(
            "station_bias_maps",
            context.write_station_bias_maps(
                station_bias_map_func,
                **settings.plot_selection_kwargs(value_col="mean_centered"),
            ),
        )
    )
    rows.append(
        _spatial_suite_status_row(
            "residual_grid_maps",
            context.write_residual_grid_maps(
                residual_grid_func,
                **metric_kwargs,
            ),
        )
    )
    rows.append(
        _spatial_suite_status_row(
            "residual_grid_maps_event_centered",
            context.write_residual_grid_maps(
                residual_grid_func,
                event_centered=True,
                **event_metric_kwargs,
            ),
        )
    )
    rows.append(
        _spatial_suite_status_row(
            "metric_by_model_maps",
            context.write_metric_by_model_maps(
                metric_by_model_map_func,
                **settings.plot_selection_kwargs(value_col=metric_value_col, model=None),
            ),
        )
    )
    rows.append(
        _spatial_suite_status_row(
            "metric_by_model_maps_event_centered",
            context.write_metric_by_model_maps(
                metric_by_model_map_func,
                event_centered=True,
                **settings.plot_selection_kwargs(value_col=event_value_col, model=None),
            ),
        )
    )
    rows.append(
        _spatial_suite_status_row(
            "event_residual_maps",
            context.write_event_residual_maps(
                event_residual_map_func,
                **metric_kwargs,
            ),
        )
    )
    rows.append(
        _spatial_suite_status_row(
            "event_residual_maps_event_centered",
            context.write_event_residual_maps(
                event_residual_map_func,
                event_centered=True,
                **event_metric_kwargs,
            ),
        )
    )
    rows.append(
        _spatial_suite_status_row(
            "event_centered_azimuthal_plots",
            context.write_event_centered_azimuthal_plots(
                azimuthal_residuals_func,
                **settings.plot_selection_kwargs(value_col=event_value_col, include_robust_axis_percentile=True),
            ),
        )
    )
    rows.append(
        _spatial_suite_status_row(
            "event_centered_polar_plots",
            context.write_event_centered_polar_plots(
                polar_residuals_func,
                **settings.plot_selection_kwargs(value_col=event_value_col),
            ),
        )
    )
    rows.append(
        _spatial_suite_status_row(
            "pca_summary_plots",
            context.write_pca_summary_plots(
                pca_summary_func,
                mode=settings.pca_mode,
                **settings.plot_selection_kwargs(),
            ),
        )
    )
    rows.append(
        _spatial_suite_status_row(
            "overview_plots",
            context.write_overview_plots(
                event_value_col=event_value_col,
                **settings.plot_selection_kwargs(value_col=metric_value_col, include_robust_axis_percentile=True),
            ),
        )
    )
    return SpatialFigureSuiteResult(context=context, rows=tuple(rows))


def write_large_run_spatial_summary_figures_from_outputs(
    outputs: Any,
    settings: Any,
    *,
    cfg: ConfigInput | None = None,
    overwrite: bool = False,
    plot_station_bias_map_func: Callable[..., Any] | None = None,
) -> SpatialSummaryFigureResult:
    """Write compact Step 4 spatial figures from configured output groups.

    The helper keeps large-run notebooks from repeating readiness checks,
    table loading, output-path lookup, and figure keyword plumbing for summary
    figures that are backed by compact Step 4 outputs.
    """

    station_bias_path = _group_path(outputs, "station_bias_path")
    figure_path = _group_path(outputs, "station_bias_figure_path")
    gate = settings.render_gate(
        [station_bias_path],
        missing_message="station_bias table is not ready yet.",
    )
    if not gate.ready:
        return SpatialSummaryFigureResult(
            station_bias_path,
            figure_path,
            "missing_input" if gate.figures_enabled else "disabled",
            message=gate.message,
        )
    if figure_path is None:
        return SpatialSummaryFigureResult(
            station_bias_path,
            None,
            "missing_output",
            message="skip station bias map: station_bias_figure_path is not configured",
        )
    if figure_path.exists() and not overwrite:
        return SpatialSummaryFigureResult(
            station_bias_path,
            figure_path,
            "exists",
            message=f"skip {figure_path.name}: exists",
        )

    plot_func = plot_station_bias_map_func
    if plot_func is None:
        from spatial_vtk.spatial.map import plot_station_bias_map as plot_func

    try:
        station_bias = outputs.load_table("station_bias", cfg=cfg)
    except Exception as exc:
        return SpatialSummaryFigureResult(
            station_bias_path,
            figure_path,
            "load_failed",
            message=f"skip station bias map: {type(exc).__name__}: {exc}",
        )
    row_count = len(station_bias)
    try:
        plot_func(
            station_bias,
            outpath=figure_path,
            savefig=True,
            **settings.plot_kwargs(),
        )
        _close_matplotlib_figures()
    except Exception as exc:
        _close_matplotlib_figures()
        return SpatialSummaryFigureResult(
            station_bias_path,
            figure_path,
            "plot_failed",
            row_count=row_count,
            message=f"skip station bias map: {type(exc).__name__}: {exc}",
        )
    return SpatialSummaryFigureResult(
        station_bias_path,
        figure_path,
        "wrote",
        row_count=row_count,
        message=f"wrote {figure_path}" if figure_path is not None else "wrote station bias map",
    )


def write_standard_spatial_map_figures(
    spatial_products: Mapping[str, Mapping[str, pd.DataFrame]],
    outputs: Any,
    settings: Any,
    *,
    station_bias_value_col: str = "mean_centered",
    station_bias_value_label: str = "Mean event-centered log2(obs/syn)",
    residual_grid_value_col: str = "field_centered",
    grid_cell_size_deg: float = 0.05,
    station_bias_path_name: str = "station_bias_figure_path",
    residual_grid_path_name: str = "residual_grid_figure_path",
    station_bias_plot_func: Callable[..., Any] | None = None,
    residual_grid_plot_func: Callable[..., Any] | None = None,
) -> StandardSpatialMapFigureResult:
    """Write standard Step 4 station-bias and residual-grid maps.

    The helper owns the repeated per-metric plot calls, output-path naming,
    sidecar keyword expansion, basemap settings, and status reporting used by
    the standard spatial-statistics tutorial.
    """

    from spatial_vtk.config.labels import metric_display_name

    if station_bias_plot_func is None:
        from spatial_vtk.spatial.map import plot_station_bias_map as station_bias_plot_func
    if residual_grid_plot_func is None:
        from spatial_vtk.spatial.map import plot_residual_grid as residual_grid_plot_func

    rows: list[dict[str, Any]] = []
    sidecar_kwargs = dict(settings.sidecars.kwargs())
    plot_kwargs = {
        "add_basemap": bool(settings.add_basemap),
        "showfig": bool(settings.showfig),
        "savefig": True,
        **sidecar_kwargs,
    }

    for metric_name, products in spatial_products.items():
        label = metric_display_name(metric_name)
        station_df = products.get("station_bias", pd.DataFrame())
        station_path = outputs.figure_path(
            station_bias_path_name,
            stem_parts=("step_04", metric_name, "station_bias"),
        )
        try:
            station_bias_plot_func(
                station_df,
                title=f"{label} Station Bias",
                value_col=station_bias_value_col,
                value_label=station_bias_value_label,
                outpath=station_path,
                **plot_kwargs,
            )
            _close_matplotlib_figures()
            rows.append(
                {
                    "artifact": "station_bias_map",
                    "metric": metric_name,
                    "status": "wrote",
                    "row_count": len(station_df),
                    "figure_path": str(station_path),
                    "figure_exists": station_path.exists(),
                    "message": f"wrote {station_path}",
                }
            )
        except Exception as exc:
            _close_matplotlib_figures()
            rows.append(
                {
                    "artifact": "station_bias_map",
                    "metric": metric_name,
                    "status": "plot_failed",
                    "row_count": len(station_df),
                    "figure_path": str(station_path),
                    "figure_exists": station_path.exists(),
                    "message": f"{type(exc).__name__}: {exc}",
                }
            )

        centered_df = products.get("centered", pd.DataFrame())
        grid_path = outputs.figure_path(
            residual_grid_path_name,
            stem_parts=("step_04", metric_name, "residual_grid"),
        )
        try:
            residual_grid_plot_func(
                centered_df,
                lon_col="lon",
                lat_col="lat",
                value_col=residual_grid_value_col,
                cell_size_deg=grid_cell_size_deg,
                title=f"{label} Residual Grid",
                outpath=grid_path,
                **plot_kwargs,
            )
            _close_matplotlib_figures()
            rows.append(
                {
                    "artifact": "residual_grid_map",
                    "metric": metric_name,
                    "status": "wrote",
                    "row_count": len(centered_df),
                    "figure_path": str(grid_path),
                    "figure_exists": grid_path.exists(),
                    "message": f"wrote {grid_path}",
                }
            )
        except Exception as exc:
            _close_matplotlib_figures()
            rows.append(
                {
                    "artifact": "residual_grid_map",
                    "metric": metric_name,
                    "status": "plot_failed",
                    "row_count": len(centered_df),
                    "figure_path": str(grid_path),
                    "figure_exists": grid_path.exists(),
                    "message": f"{type(exc).__name__}: {exc}",
                }
            )

    return StandardSpatialMapFigureResult(tuple(rows))


def write_standard_spatial_diagnostic_figures(
    spatial_products: Mapping[str, Mapping[str, pd.DataFrame]],
    spatial_tables: Mapping[str, pd.DataFrame],
    outputs: Any,
    settings: Any,
    *,
    cfg: ConfigInput | None = None,
    site_metadata: pd.DataFrame | None = None,
    metrics: Sequence[str] | None = None,
    pca_mode: str | None = None,
    distance_bin_rows: int = 5,
    distance_correlation_path_name: str = "spatial_correlation_distance_figure_path",
    pca_summary_path_name: str = "pca_summary_figure_path",
    geology_contrast_path_name: str = "geology_contrast_figure_path",
    distance_plot_func: Callable[..., Any] | None = None,
    pca_plot_func: Callable[..., Any] | None = None,
    geology_plot_func: Callable[..., Any] | None = None,
) -> StandardSpatialDiagnosticFigureResult:
    """Write standard Step 4 correlation, PCA, and geology diagnostic figures.

    This helper owns the repeated per-metric table selection, figure naming,
    sidecar keyword expansion, basemap settings, and compact preview tables
    used by the standard spatial-statistics tutorial.
    """

    from spatial_vtk.config.labels import metric_display_name
    from spatial_vtk.io import load_configured_input_tables
    from spatial_vtk.spatial import (
        spatial_correlation_preview_frame,
        spatial_metric_table_frame,
        spatial_pca_product_frames,
    )

    if distance_plot_func is None:
        from spatial_vtk.spatial.plot import plot_distance_correlation_by_metric as distance_plot_func
    if pca_plot_func is None:
        from spatial_vtk.spatial.map import plot_pca_summary as pca_plot_func
    if geology_plot_func is None:
        from spatial_vtk.spatial.plot import plot_geology_contrast as geology_plot_func

    metric_names = tuple(metrics or spatial_products.keys())
    morans_i = spatial_tables.get("morans_i", pd.DataFrame())
    distance_bins = spatial_tables.get("distance_bins", pd.DataFrame())
    geology_contrasts = spatial_tables.get("geology_contrasts", pd.DataFrame())
    pca_station_scores = spatial_tables.get("pca_station_scores", pd.DataFrame())
    pca_feature_loadings = spatial_tables.get("pca_feature_loadings", pd.DataFrame())
    pca_explained_variance = spatial_tables.get("pca_explained_variance", pd.DataFrame())
    if site_metadata is None and cfg is not None:
        try:
            site_metadata = load_configured_input_tables({"site_metadata": "paths.site_metadata"}, cfg=cfg)["site_metadata"]
        except Exception:
            site_metadata = None

    rows: list[dict[str, Any]] = []
    previews: list[pd.DataFrame] = []
    sidecar_kwargs = dict(settings.sidecars.kwargs())
    showfig = bool(getattr(settings, "showfig", False))
    add_basemap = bool(getattr(settings, "add_basemap", False))
    resolved_pca_mode = pca_mode or getattr(settings, "pca_mode", "PC1")

    for metric_name in metric_names:
        preview = spatial_correlation_preview_frame(
            morans_i=morans_i,
            distance_bins=distance_bins,
            metric=metric_name,
            distance_bin_rows=distance_bin_rows,
        )
        if not preview.empty:
            previews.append(_standard_spatial_preview_frame(preview, artifact="spatial_correlation", metric=metric_name))

    distance_path = outputs.figure_path(
        distance_correlation_path_name,
        stem_parts=("step_04", "spatial_correlation_distance"),
    )
    rows.append(
        _write_standard_spatial_diagnostic_figure(
            "spatial_correlation_distance",
            "all",
            distance_bins,
            distance_path,
            distance_plot_func,
            title="Spatial Correlation by Distance",
            significance_df=morans_i,
            showfig=showfig,
            savefig=True,
            **sidecar_kwargs,
        )
    )

    for metric_name in metric_names:
        label = metric_display_name(metric_name)
        pca_products = spatial_pca_product_frames(
            metric_name,
            station_scores=pca_station_scores,
            explained_variance=pca_explained_variance,
            feature_loadings=pca_feature_loadings,
        )
        explained = pca_products["explained_variance"]
        if not explained.empty:
            previews.append(_standard_spatial_preview_frame(explained, artifact="pca_explained_variance", metric=metric_name))
        pca_path = outputs.figure_path(
            pca_summary_path_name,
            stem_parts=("step_04", metric_name, "pca_summary"),
        )
        rows.append(
            _write_standard_spatial_diagnostic_figure(
                "pca_summary",
                metric_name,
                pca_products["station_scores"],
                pca_path,
                pca_plot_func,
                explained,
                pca_products["feature_loadings"],
                mode=resolved_pca_mode,
                title=f"{label} PCA Spatial Mode Summary",
                add_basemap=add_basemap,
                showfig=showfig,
                savefig=True,
                **sidecar_kwargs,
            )
        )

        geology_contrast = spatial_metric_table_frame(geology_contrasts, metric_name)
        if not geology_contrast.empty:
            previews.append(_standard_spatial_preview_frame(geology_contrast, artifact="geology_contrast", metric=metric_name))
        centered = spatial_products.get(metric_name, {}).get("centered", pd.DataFrame())
        geology_path = outputs.figure_path(
            geology_contrast_path_name,
            stem_parts=("step_04", metric_name, "geology_contrast"),
        )
        rows.append(
            _write_standard_spatial_diagnostic_figure(
                "geology_contrast",
                metric_name,
                centered,
                geology_path,
                geology_plot_func,
                station_metadata=site_metadata,
                contrast_df=geology_contrast,
                title=f"{label} Residuals by Geology Class",
                showfig=showfig,
                savefig=True,
                **sidecar_kwargs,
            )
        )

    return StandardSpatialDiagnosticFigureResult(tuple(rows), tuple(previews))


def _standard_spatial_preview_frame(frame: pd.DataFrame, *, artifact: str, metric: str) -> pd.DataFrame:
    """Tag a compact diagnostic preview with artifact and metric labels."""

    preview = frame.copy()
    preview["artifact"] = artifact
    preview["metric"] = metric
    leading = ["artifact", "metric"]
    return preview.loc[:, leading + [column for column in preview.columns if column not in leading]]


def _write_standard_spatial_diagnostic_figure(
    artifact: str,
    metric: str,
    frame: pd.DataFrame,
    figure_path: Path,
    plot_func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """Call one standard Step 4 diagnostic plot and return a status row."""

    try:
        plot_func(frame, *args, outpath=figure_path, **kwargs)
        _close_matplotlib_figures()
        status = "wrote"
        message = f"wrote {figure_path}"
    except Exception as exc:
        _close_matplotlib_figures()
        status = "plot_failed"
        message = f"{type(exc).__name__}: {exc}"
    return {
        "artifact": artifact,
        "metric": metric,
        "status": status,
        "row_count": len(frame),
        "figure_path": str(figure_path),
        "figure_exists": figure_path.exists(),
        "message": message,
    }


def write_standard_geojson_region_figures(
    *,
    metrics: pd.DataFrame,
    stations: pd.DataFrame,
    events: pd.DataFrame,
    outputs: Any,
    settings: Any,
    geojson_path: str | Path,
    value_col: str = "log2_residual",
    passbands: Sequence[str] | str | None = ("1-2 sec", "2-3 sec"),
    component: str | Sequence[str] | None = "Z",
    station_region: str = "LA Basin",
    event_region: str = "Glendale",
    metric: str = "PGA",
    compare_to: str = "LA Basin",
    model: str | None = None,
    summary_metrics_table: pd.DataFrame | str | Path | None = None,
    summary_geojson_path: str | Path | None = None,
    summary_chunksize: int | None = 100_000,
    geojson_plot_func: Callable[..., Any] | None = None,
    boxplot_func: Callable[..., Any] | None = None,
    station_map_func: Callable[..., Any] | None = None,
    summary_func: Callable[..., Mapping[str, Any]] | None = None,
) -> StandardGeoJSONFigureResult:
    """Write standard Step 5 GeoJSON overview, boxplot, and region map figures.

    The helper owns the GeoJSON annotation, regional metric filtering, station
    residual summary, configured figure naming, sidecar kwargs, and status
    reporting used by the standard maps-and-figures tutorial.
    """

    from spatial_vtk.io import event_rows_for_records
    from spatial_vtk.spatial import (
        build_metric_field,
        geojson_metric_region_frame,
        geojson_metric_subset_frame,
        geojson_polygon_preview_table,
        run_geojson_region_summary_workflow_from_config,
        summarize_station_bias,
    )

    if geojson_plot_func is None:
        from spatial_vtk.spatial.map import plot_geojson_polygons_map as geojson_plot_func
    if boxplot_func is None:
        from spatial_vtk.spatial.plot import boxplot as boxplot_func
    if station_map_func is None:
        from spatial_vtk.spatial.map import plot_station_metric_map as station_map_func
    if summary_func is None:
        summary_func = run_geojson_region_summary_workflow_from_config

    sidecar_kwargs = dict(settings.sidecars.kwargs())
    showfig = bool(getattr(settings, "showfig", False))
    add_basemap = bool(getattr(settings, "add_basemap", False))
    model_name = model or _first_nonempty_metric_value(metrics, "model", fallback="model")
    region_preview = geojson_polygon_preview_table(geojson_path)
    rows: list[dict[str, Any]] = []
    summary = summary_func(
        metrics_table=summary_metrics_table,
        geojson_path=summary_geojson_path,
        chunksize=summary_chunksize,
        verbose=False,
    )

    metrics_by_station_region = geojson_metric_region_frame(
        metrics,
        geojson_path,
        target="station",
        selector="all",
        region_col="station_region",
    )
    metrics_by_station_region = _merge_geojson_region_class_metadata(
        metrics_by_station_region,
        Path(geojson_path),
        region_col="station_region",
    )
    region_color_col = _region_boxplot_color_column(metrics_by_station_region)
    metrics_by_regions = geojson_metric_region_frame(
        metrics_by_station_region,
        geojson_path,
        target="event",
        selector="all",
        require_inside=False,
        region_col="event_region",
    )

    geojson_path_out = outputs.figure_path(
        "geojson_polygons_map_path",
        stem_parts=("step_05", "geojson_regions"),
    )
    rows.append(
        _write_standard_geojson_figure(
            "geojson_regions",
            pd.concat(
                [stations.assign(_figure_layer="station"), events.assign(_figure_layer="event")],
                ignore_index=True,
                sort=False,
            ),
            geojson_path_out,
            geojson_plot_func,
            geojson_path,
            stations_df=stations,
            events_df=events,
            title="Example GeoJSON Regions",
            add_basemap=add_basemap,
            showfig=showfig,
            savefig=True,
            **sidecar_kwargs,
        )
    )

    boxplot_path = outputs.figure_path(
        "region_boxplot_figure_path",
        stem_parts=("step_05", "pga", "region_boxplot"),
    )
    rows.append(
        _write_standard_geojson_figure(
            "pga_region_boxplot",
            metrics_by_station_region,
            boxplot_path,
            boxplot_func,
            data=metrics_by_station_region,
            dep=metric,
            indep="station_region",
            value_col=value_col,
            passband=passbands,
            model=model_name,
            component=component,
            colorby=region_color_col,
            compare_to=compare_to,
            table=True,
            title="PGA Residuals by Station Region",
            showfig=showfig,
            savefig=True,
            **sidecar_kwargs,
        )
    )

    regional_metric = geojson_metric_subset_frame(
        metrics_by_regions,
        metric=metric,
        passband=passbands,
        component=component,
        event_region=event_region,
        station_region=station_region,
    )
    regional_field = build_metric_field(regional_metric, metric, value_column=value_col)
    regional_bias = summarize_station_bias(
        regional_field,
        value_col="field_value",
        center_by_event=False,
        min_events_per_station=1,
    )
    regional_event_points = event_rows_for_records(events, regional_metric)
    station_map_path = outputs.figure_path(
        "station_metric_map_path",
        stem_parts=("step_05", "pga", "glendale_events", "la_basin_stations"),
    )
    rows.append(
        _write_standard_geojson_figure(
            "regional_pga_station_map",
            regional_bias,
            station_map_path,
            station_map_func,
            regional_bias,
            value_col="mean_centered",
            lon_col="lon",
            lat_col="lat",
            events_df=regional_event_points,
            geojson_path=geojson_path,
            polygon_selector=[event_region, station_region],
            polygon_alpha=0.12,
            label_polygons=True,
            event_alpha=0.76,
            title="Mean PGA log2(obs/syn) Residual\nEvents in Glendale; Stations in LA Basin",
            add_basemap=add_basemap,
            showfig=showfig,
            savefig=True,
            **sidecar_kwargs,
        )
    )
    return StandardGeoJSONFigureResult(
        rows=tuple(rows),
        region_preview=region_preview,
        metrics_by_regions=metrics_by_regions,
        model_name=str(model_name),
        summary=dict(summary),
    )


def _write_standard_geojson_figure(
    artifact: str,
    frame: pd.DataFrame,
    figure_path: Path,
    plot_func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """Call one standard Step 5 GeoJSON plot and return a status row."""

    try:
        plot_func(*args, outpath=figure_path, **kwargs)
        _close_matplotlib_figures()
        status = "wrote"
        message = f"wrote {figure_path}"
    except Exception as exc:
        _close_matplotlib_figures()
        status = "plot_failed"
        message = f"{type(exc).__name__}: {exc}"
    return {
        "artifact": artifact,
        "status": status,
        "row_count": len(frame),
        "figure_path": str(figure_path),
        "figure_exists": figure_path.exists(),
        "message": message,
    }


def _first_nonempty_metric_value(df: pd.DataFrame, column: str, *, fallback: str) -> str:
    """Return the first non-empty dataframe value for a column."""

    if column not in df.columns:
        return str(fallback)
    values = df[column].dropna().astype(str)
    values = values.loc[values.str.strip().ne("")]
    return str(values.iloc[0]) if not values.empty else str(fallback)


def load_standard_geojson_plotting_inputs(
    *,
    cfg: Any | None = None,
    geojson_config_key: str = "paths.region_geojson",
    ingest_group_name: str = "step_01_ingest",
    metrics_group_name: str = "step_03_metrics",
    geojson_group_name: str = "step_05_geojson",
) -> StandardGeoJSONPlottingInputResult:
    """Load standard Step 5 GeoJSON tutorial inputs through configured registries.

    The Step 3 ``metrics_long`` table is loaded with a spatial event-row column
    projection so large path-backed metric tables do not have to materialize
    unrelated metric output columns before Step 5 figures are rendered.

    Parameters
    ----------
    cfg
        Spatial-VTK config object or config file path. When omitted, the
        active config is used by the underlying IO helpers.
    geojson_config_key
        Dotted config key for the region GeoJSON file.
    ingest_group_name, metrics_group_name, geojson_group_name
        Output-group names for prepared Step 1 metadata, Step 3 metrics, and
        Step 5 GeoJSON figure/table outputs.

    Returns
    -------
    StandardGeoJSONPlottingInputResult
        Loaded metrics, station/event metadata, event-station records,
        comparison-eligible pairs, configured GeoJSON path, and the configured
        Step 5 output group.
    """

    from spatial_vtk.io import load_configured_input_paths, output_group

    ingest_outputs = output_group(ingest_group_name, cfg=cfg)
    metrics_outputs = output_group(metrics_group_name, cfg=cfg)
    geojson_outputs = output_group(geojson_group_name, cfg=cfg)
    configured_paths = load_configured_input_paths({"region_geojson": geojson_config_key}, cfg=cfg)
    ingest_tables = ingest_outputs.load_tables(
        {
            "stations": "prepared_stations_path",
            "events": "prepared_events_path",
            "event_stations": "event_station_path",
        },
        cfg=cfg,
    )
    geojson_tables = geojson_outputs.load_tables(
        {"comparison_eligible": "comparison_eligible_path"},
        cfg=cfg,
    )
    metrics_path = getattr(metrics_outputs, "metrics_long_path", None)
    metrics = _read_if_exists(metrics_path, columns=SPATIAL_EVENT_ROW_COLUMNS)
    if metrics is None:
        raise FileNotFoundError("Configured Step 3 metrics_long table is missing.")

    return StandardGeoJSONPlottingInputResult(
        metrics=metrics,
        stations=ingest_tables["stations"],
        events=ingest_tables["events"],
        event_stations=ingest_tables["event_stations"],
        comparison_eligible=geojson_tables["comparison_eligible"],
        geojson_path=configured_paths["region_geojson"],
        outputs=geojson_outputs,
    )


def load_standard_geojson_workflow_output_status(
    *,
    cfg: Any | None = None,
    geojson_group_name: str = "step_05_geojson",
) -> StandardGeoJSONWorkflowOutputStatusResult:
    """Return configured Step 5 output status without loading large tables."""

    from spatial_vtk.io import output_group

    return StandardGeoJSONWorkflowOutputStatusResult(outputs=output_group(geojson_group_name, cfg=cfg), cfg=cfg)


def _geojson_result_config_path(cfg: Any | None, context: Any | None) -> object | None:
    """Return the configured path for result-owned Step 5 notebook runners."""

    if isinstance(cfg, (str, Path)):
        return cfg
    value = getattr(cfg, "config_path", None)
    return value if value is not None else getattr(context, "config_path", None)


def _geojson_result_run_scenario(cfg: Any | None, context: Any | None) -> str | None:
    """Return the run scenario for result-owned Step 5 notebook runners."""

    value = getattr(cfg, "run_scenario", None)
    return value if value is not None else getattr(context, "run_scenario", None)


def write_standard_geojson_corridor_figures(
    *,
    metrics_by_regions: pd.DataFrame,
    stations: pd.DataFrame,
    event_stations: pd.DataFrame,
    events: pd.DataFrame,
    comparison_eligible: pd.DataFrame,
    outputs: Any,
    spatial_settings: Any,
    waveform_settings: Any,
    geojson_path: str | Path,
    value_col: str = "log2_residual",
    passbands: Sequence[str] | str | None = None,
    component: str | None = None,
    boundary_region: str = "LA Basin",
    through_anchor_station: str = "OLI",
    outward_event_id: str = "ci38695658",
    corridor_station_region: str = "LA Basin",
    record_component: str = "R",
    record_passband: str = "1-2 sec",
    display_func: Callable[[Any], Any] | None = None,
    build_corridors_func: Callable[..., pd.DataFrame] | None = None,
    select_records_func: Callable[..., pd.DataFrame] | None = None,
    classify_paths_func: Callable[..., pd.DataFrame] | None = None,
    matched_records_func: Callable[..., pd.DataFrame] | None = None,
    comparison_records_func: Callable[..., pd.DataFrame] | None = None,
    waveform_records_func: Callable[..., pd.DataFrame] | None = None,
    event_ids_func: Callable[..., list[str]] | None = None,
    event_rows_func: Callable[..., pd.DataFrame] | None = None,
    event_preview_func: Callable[..., pd.DataFrame] | None = None,
    metric_subset_func: Callable[..., pd.DataFrame] | None = None,
    metric_field_func: Callable[..., pd.DataFrame] | None = None,
    station_bias_func: Callable[..., pd.DataFrame] | None = None,
    corridor_pair_func: Callable[..., pd.DataFrame] | None = None,
    corridor_preview_func: Callable[..., pd.DataFrame] | None = None,
    corridor_map_func: Callable[..., Any] | None = None,
    record_section_func: Callable[..., Any] | None = None,
    station_map_func: Callable[..., Any] | None = None,
) -> StandardGeoJSONCorridorFigureResult:
    """Write standard Step 5 corridor maps, record section, and corridor PGV map.

    The helper keeps corridor geometry construction, selected-record joins,
    waveform comparison selection, metric filtering, configured figure paths,
    and notebook preview tables in package code.
    """

    from spatial_vtk.config import render_notebook_figure
    from spatial_vtk.io import event_ids_from_records, event_label_preview_frame, event_rows_for_records
    from spatial_vtk.qc import build_qc_waveform_comparison_records
    from spatial_vtk.spatial import (
        BoundaryCorridorConfig,
        CorridorAnchorConfig,
        CorridorSelectionConfig,
        build_boundary_corridors,
        build_metric_field,
        classify_paths_with_geojson,
        corridor_record_pair_frame,
        corridor_record_preview_frame,
        event_station_records_matching_pairs,
        geojson_matched_record_frame,
        geojson_metric_subset_frame,
        select_records_by_corridors,
        summarize_station_bias,
    )
    from spatial_vtk.spatial.map import plot_corridor_map, plot_station_metric_map
    from spatial_vtk.visualize.waveforms import plot_observed_synthetic_record_section

    build_corridors_func = build_corridors_func or build_boundary_corridors
    select_records_func = select_records_func or select_records_by_corridors
    classify_paths_func = classify_paths_func or classify_paths_with_geojson
    matched_records_func = matched_records_func or geojson_matched_record_frame
    comparison_records_func = comparison_records_func or event_station_records_matching_pairs
    waveform_records_func = waveform_records_func or build_qc_waveform_comparison_records
    event_ids_func = event_ids_func or event_ids_from_records
    event_rows_func = event_rows_func or event_rows_for_records
    event_preview_func = event_preview_func or event_label_preview_frame
    metric_subset_func = metric_subset_func or geojson_metric_subset_frame
    metric_field_func = metric_field_func or build_metric_field
    station_bias_func = station_bias_func or summarize_station_bias
    corridor_pair_func = corridor_pair_func or corridor_record_pair_frame
    corridor_preview_func = corridor_preview_func or corridor_record_preview_frame
    corridor_map_func = corridor_map_func or plot_corridor_map
    record_section_func = record_section_func or plot_observed_synthetic_record_section
    station_map_func = station_map_func or plot_station_metric_map

    through_corridors = build_corridors_func(
        geojson_path,
        config=BoundaryCorridorConfig(
            selector=boundary_region,
            mode="through_boundary",
            along_boundary_width_km=10,
            inside_length_km=15,
            outside_length_km=20,
            anchor=CorridorAnchorConfig(source="station", strategy="id", id_value=through_anchor_station),
        ),
        station_df=stations,
        event_df=events,
    )
    outward_corridors = build_corridors_func(
        geojson_path,
        config=BoundaryCorridorConfig(
            selector=boundary_region,
            mode="outward",
            along_boundary_width_km=10,
            inside_length_km=15,
            outside_length_km=20,
            anchor=CorridorAnchorConfig(source="event", strategy="id", id_value=outward_event_id),
        ),
        station_df=stations,
        event_df=events,
    )

    through_corridor_paths = select_records_func(
        event_stations,
        through_corridors,
        config=CorridorSelectionConfig(path_filter="passes_through_corridor", min_path_length_km=0.1),
    )
    outward_corridor_paths = select_records_func(
        event_stations,
        outward_corridors,
        config=CorridorSelectionConfig(path_filter="passes_through_corridor", min_path_length_km=0.1),
    )

    rows: list[dict[str, Any]] = []
    rows.append(
        _write_standard_notebook_figure(
            "through_boundary_corridor_map",
            through_corridors,
            render_notebook_figure,
            corridor_map_func,
            outputs,
            "corridor_map_path",
            spatial_settings,
            through_corridors,
            stem_parts=("step_05", "corridor", "through_boundary"),
            include_basemap=True,
            display_func=display_func,
            stations_df=stations,
            events_df=events,
            records_df=corridor_pair_func(through_corridor_paths),
            highlight_anchor=True,
            title="Through-Boundary Corridor at the LA Basin Edge\nAnchor: station OLI",
        )
    )
    rows.append(
        _write_standard_notebook_figure(
            "outward_corridor_map",
            outward_corridors,
            render_notebook_figure,
            corridor_map_func,
            outputs,
            "corridor_map_path",
            spatial_settings,
            outward_corridors,
            stem_parts=("step_05", "corridor", "outward"),
            include_basemap=True,
            display_func=display_func,
            stations_df=stations,
            events_df=events,
            records_df=corridor_pair_func(outward_corridor_paths),
            highlight_anchor=True,
            title="Outward Corridor from the LA Basin Boundary\nAnchor: event ci38695658",
        )
    )

    central_boundary_paths = classify_paths_func(
        event_stations,
        geojson_path,
        relation="crosses_boundary",
        selector=boundary_region,
        direction="either",
    )
    boundary_crossing_paths = select_records_func(
        matched_records_func(central_boundary_paths),
        through_corridors,
        config=CorridorSelectionConfig(path_filter="passes_through_corridor", min_path_length_km=0.1),
    )
    selected_eligible = comparison_records_func(comparison_eligible, boundary_crossing_paths)
    boundary_waveforms = waveform_records_func(
        event_stations,
        comparison_eligible=selected_eligible,
        component=record_component,
        passband=record_passband,
        max_distance_km=None,
        max_records=12,
    )
    rows.append(
        _write_standard_notebook_figure(
            "boundary_crossing_record_section",
            boundary_waveforms,
            render_notebook_figure,
            record_section_func,
            outputs,
            "record_section_figure_path",
            waveform_settings,
            boundary_waveforms,
            stem_parts=("step_05", "boundary_crossing_record_section"),
            display_func=display_func,
            components=[record_component],
            normalize=True,
            scale=2.5,
            title="Observed vs Synthetic Records for LA Basin Boundary-Crossing Paths",
            filter_label=f"lowpass 1 Hz; {record_component} component; {record_passband} QC passband",
            time_limit_s=60,
        )
    )

    outward_event_paths = select_records_func(
        event_stations,
        outward_corridors,
        config=CorridorSelectionConfig(event_filter="inside_corridor"),
    )
    outward_event_ids = event_ids_func(outward_event_paths)
    events_in_outward_corridor = event_rows_func(events, event_ids=outward_event_ids)
    selected_event_names = event_preview_func(events_in_outward_corridor)
    pgv_corridor_rows = metric_subset_func(
        metrics_by_regions,
        metric="PGV",
        passband=passbands,
        component=component,
        event_ids=outward_event_ids,
        station_region=corridor_station_region,
    )
    pgv_corridor_field = metric_field_func(pgv_corridor_rows, "PGV", value_column=value_col)
    pgv_corridor_bias = station_bias_func(
        pgv_corridor_field,
        value_col="field_value",
        center_by_event=False,
        min_events_per_station=1,
    )
    pgv_corridor_paths = comparison_records_func(outward_event_paths, pgv_corridor_rows)
    rows.append(
        _write_standard_notebook_figure(
            "pgv_outward_corridor_station_map",
            pgv_corridor_bias,
            render_notebook_figure,
            station_map_func,
            outputs,
            "station_metric_map_path",
            spatial_settings,
            pgv_corridor_bias,
            stem_parts=("step_05", "pgv", "outward_corridor", "la_basin_stations"),
            include_basemap=True,
            display_func=display_func,
            value_col="mean_centered",
            lon_col="lon",
            lat_col="lat",
            geojson_path=geojson_path,
            polygon_selector="all",
            polygon_alpha=0.10,
            label_polygons=True,
            corridors_df=outward_corridors,
            events_df=events_in_outward_corridor,
            records_df=corridor_pair_func(pgv_corridor_paths),
            title="Mean PGV log2(obs/syn) Residual\nEvents in Outward Corridor; Stations in LA Basin",
        )
    )
    return StandardGeoJSONCorridorFigureResult(
        rows=tuple(rows),
        boundary_crossing_preview=corridor_preview_func(boundary_crossing_paths),
        outward_event_preview=selected_event_names,
        metrics_by_regions=metrics_by_regions,
    )


def load_standard_additional_plotting_inputs(
    *,
    cfg: Any | None = None,
    metrics_config_key: str = "paths.metric_figure_snapshot",
    ingest_group_name: str = "step_01_ingest",
    plotting_group_name: str = "step_06_plotting",
) -> StandardAdditionalPlottingInputResult:
    """Load the standard Step 6 tutorial inputs through configured registries.

    Parameters
    ----------
    cfg
        Spatial-VTK config object or config file path. When omitted, the
        active config is used by the underlying IO helpers.
    metrics_config_key
        Config key for the compact QC-passed metric snapshot used by the
        standard plotting tutorial.
    ingest_group_name, plotting_group_name
        Output-group names for Step 1 prepared metadata and Step 6 plotting
        inputs/figures.

    Returns
    -------
    StandardAdditionalPlottingInputResult
        Loaded metrics, event/station records, events, comparison-eligible
        pairs, and the configured Step 6 output group.
    """

    from spatial_vtk.io import load_configured_input_tables, output_group

    ingest_outputs = output_group(ingest_group_name, cfg=cfg)
    plotting_outputs = output_group(plotting_group_name, cfg=cfg)
    ingest_tables = ingest_outputs.load_tables(
        {
            "events": "prepared_events_path",
            "event_stations": "event_station_path",
        },
        cfg=cfg,
    )
    plotting_tables = plotting_outputs.load_tables(
        {"comparison_eligible": "comparison_eligible_path"},
        cfg=cfg,
    )
    configured_inputs = load_configured_input_tables({"metrics": metrics_config_key}, cfg=cfg)
    return StandardAdditionalPlottingInputResult(
        metrics=configured_inputs["metrics"],
        event_stations=ingest_tables["event_stations"],
        events=ingest_tables["events"],
        comparison_eligible=plotting_tables["comparison_eligible"],
        outputs=plotting_outputs,
    )


def load_standard_additional_plotting_output_status(
    *,
    cfg: Any | None = None,
    plotting_group_name: str = "step_06_plotting",
) -> StandardAdditionalPlottingOutputStatusResult:
    """Return configured Step 6 output status without loading large tables."""

    from spatial_vtk.io import output_group

    return StandardAdditionalPlottingOutputStatusResult(outputs=output_group(plotting_group_name, cfg=cfg), cfg=cfg)


def write_standard_additional_plotting_figures(
    *,
    metrics: pd.DataFrame,
    event_stations: pd.DataFrame,
    events: pd.DataFrame,
    comparison_eligible: pd.DataFrame,
    outputs: Any,
    waveform_settings: Any,
    metric_settings: Any,
    waveform_event_id: str = "ci38038071",
    waveform_component: str = "R",
    waveform_passband: str = "1-2 sec",
    waveform_time_limit_s: float = 90.0,
    model: str = "cvmsi",
    value_col: str = "log2_residual",
    passbands: Sequence[str] | str | None = None,
    component: str | None = None,
    pattern_metric: str = "PGA",
    pattern_passband: str = "1-2 sec",
    pattern_title: str = "PGA Observed/Synthetic Station Pattern Similarity",
    station_region_col: str = "station_geojson_region",
    display_func: Callable[[Any], Any] | None = None,
    waveform_records_func: Callable[..., pd.DataFrame] | None = None,
    event_label_func: Callable[..., str] | None = None,
    metric_summary_func: Callable[..., pd.DataFrame] | None = None,
    geojson_region_func: Callable[..., pd.DataFrame] | None = None,
    pattern_rows_func: Callable[..., pd.DataFrame] | None = None,
    waveform_order_func: Callable[..., pd.DataFrame] | None = None,
    waveform_map_func: Callable[..., Any] | None = None,
    pattern_plot_func: Callable[..., Any] | None = None,
    scatterplot_func: Callable[..., Any] | None = None,
    boxplot_func: Callable[..., Any] | None = None,
    heatmap_func: Callable[..., Any] | None = None,
) -> StandardAdditionalPlottingFigureResult:
    """Write standard Step 6 waveform, pattern, scatter, boxplot, and heatmap figures.

    The helper owns the figure-path lookup, sidecar/default plotting kwargs,
    waveform-record selection, GeoJSON region annotation, pattern-similarity
    table construction, and notebook preview tables used by the standard
    additional-plotting tutorial.
    """

    from spatial_vtk.config import render_notebook_figure
    from spatial_vtk.io import event_display_label
    from spatial_vtk.metrics.plot import metric_plot_input_summary_frame
    from spatial_vtk.qc import build_qc_waveform_comparison_records
    from spatial_vtk.spatial import build_pattern_similarity_station_anomalies, geojson_metric_region_frame
    from spatial_vtk.spatial.plot import boxplot, heatmap, plot_pattern_similarity, scatterplot
    from spatial_vtk.visualize.waveforms import (
        plot_station_event_waveform_map,
        station_event_waveform_order_frame,
    )

    waveform_records_func = waveform_records_func or build_qc_waveform_comparison_records
    event_label_func = event_label_func or event_display_label
    metric_summary_func = metric_summary_func or metric_plot_input_summary_frame
    geojson_region_func = geojson_region_func or geojson_metric_region_frame
    pattern_rows_func = pattern_rows_func or build_pattern_similarity_station_anomalies
    waveform_order_func = waveform_order_func or station_event_waveform_order_frame
    waveform_map_func = waveform_map_func or plot_station_event_waveform_map
    pattern_plot_func = pattern_plot_func or plot_pattern_similarity
    scatterplot_func = scatterplot_func or scatterplot
    boxplot_func = boxplot_func or boxplot
    heatmap_func = heatmap_func or heatmap

    metrics = _with_step06_delay_fraction(metrics)
    if model is None:
        raise ValueError("Step 6 standard diagnostics require a single model. Use write_step06_model_comparison_figures for two-model comparison figures.")
    selected_model = str(model)
    model_filter = selected_model
    model_metrics = _filter_step06_rows(metrics, model=selected_model)
    if model_metrics.empty:
        model_metrics = metrics
    waveform_event_id = _select_step06_waveform_event_id(
        event_stations,
        comparison_eligible=comparison_eligible,
        requested_event_id=waveform_event_id,
        component=waveform_component,
        passband=waveform_passband,
    )
    waveform_records = waveform_records_func(
        event_stations,
        comparison_eligible=comparison_eligible,
        component=waveform_component,
        passband=waveform_passband,
        event_id=waveform_event_id,
        max_distance_km=None,
        max_records=12,
    )
    waveform_event_name = event_label_func(events, waveform_event_id)
    metric_summary = metric_summary_func(model_metrics, comparison_eligible=comparison_eligible)
    region_metrics = geojson_region_func(
        model_metrics,
        target="station",
        selector="all",
        region_col=station_region_col,
    )
    comparison_region_metrics = _with_step06_metric_comparison_values(region_metrics, default_value_col=value_col)
    waveform_order = waveform_order_func(waveform_records, max_traces=12)

    rows: list[dict[str, Any]] = []
    if not waveform_records.empty:
        rows.append(
            _write_standard_notebook_figure(
                "station_event_waveform_map",
                waveform_records,
                render_notebook_figure,
                waveform_map_func,
                outputs,
                "station_event_waveform_map_path",
                waveform_settings,
                waveform_records,
                stem_parts=("step_06", "station_event_waveform_map", selected_model, waveform_event_id, waveform_passband, waveform_component),
                include_basemap=True,
                display_func=display_func,
                waveform_col="observed",
                time_limit_s=waveform_time_limit_s,
                normalize=True,
                title=f"Observed Station-Event Waveform Map\n{waveform_event_name}",
                filter_label=f"lowpass 1 Hz; {waveform_component} component; {waveform_passband} QC passband",
            )
        )
    else:
        rows.append(_step06_skipped_row("station_event_waveform_map", waveform_records, outputs, "station_event_waveform_map_path", ("step_06", "station_event_waveform_map", selected_model, waveform_event_id, waveform_passband, waveform_component), "no waveform records matched the selected event/component/passband"))

    selected_passbands = _step06_available_values(model_metrics, "passband") or _step06_available_values(model_metrics, "band")
    if passbands is not None:
        selected_passbands = [value for value in _as_step06_list(passbands) if value in set(selected_passbands)] or selected_passbands
    metric_names = _step06_available_values(model_metrics, "metric")
    comparison_metrics = _step06_metric_comparison_metrics(metric_names)
    all_pattern_rows: list[pd.DataFrame] = []

    for metric_name in metric_names:
        metric_value_col = _step06_metric_value_col(metric_name, model_metrics, value_col)
        if not _has_step06_finite_rows(model_metrics, metric_name, model_filter, None, component, metric_value_col, require_distance=True):
            rows.append(_step06_skipped_row("metric_scatterplot", model_metrics.iloc[0:0], outputs, "scatterplot_figure_path", ("step_06", "metric_scatterplot", selected_model, metric_name, "all-passbands", component or "all-components", metric_value_col), "no finite metric/distance rows"))
            continue
        scatter_passbands = None if _step06_is_spectral_metric(metric_name) else selected_passbands or None
        rows.append(
            _write_standard_notebook_figure(
                "metric_scatterplot",
                model_metrics,
                render_notebook_figure,
                scatterplot_func,
                outputs,
                "scatterplot_figure_path",
                metric_settings,
                data=model_metrics,
                indep="distance",
                dep=metric_name,
                value_col=metric_value_col,
                passband=scatter_passbands,
                model=model_filter,
                component=component,
                colorby="passband" if scatter_passbands is not None and len(selected_passbands) > 1 else None,
                fit="lowess",
                title=f"{metric_name} vs Distance",
                stem_parts=("step_06", "metric_scatterplot", selected_model, metric_name, "all-passbands", component or "all-components", metric_value_col),
                display_func=display_func,
            )
        )

        for passband_name in [None, *selected_passbands]:
            passband_label = passband_name or "all-passbands"
            if not _has_step06_region_rows(region_metrics, metric_name, model_filter, passband_name, component, metric_value_col, station_region_col):
                rows.append(_step06_skipped_row("metric_boxplot", region_metrics.iloc[0:0], outputs, "boxplot_figure_path", ("step_06", "metric_boxplot", selected_model, metric_name, passband_label, component or "all-components", metric_value_col), "no finite region rows"))
                continue
            rows.append(
                _write_standard_notebook_figure(
                    "metric_boxplot",
                    region_metrics,
                    render_notebook_figure,
                    boxplot_func,
                    outputs,
                    "boxplot_figure_path",
                    metric_settings,
                    data=region_metrics,
                    dep=metric_name,
                    indep=station_region_col,
                    value_col=metric_value_col,
                    passband=passband_name,
                    model=model_filter,
                    component=component,
                    compare_to="LA Basin",
                    table=True,
                    title=f"{metric_name} by GeoJSON Region",
                    stem_parts=("step_06", "metric_boxplot", selected_model, metric_name, passband_label, component or "all-components", metric_value_col),
                    display_func=display_func,
                )
            )

        for passband_name in selected_passbands:
            try:
                pattern_rows = pattern_rows_func(
                    model_metrics,
                    metric=metric_name,
                    passband=passband_name,
                    component=component,
                    model=model_filter,
                )
            except Exception:
                pattern_rows = pd.DataFrame()
            all_pattern_rows.append(pattern_rows)
            if pattern_rows.empty:
                rows.append(_step06_skipped_row("pattern_similarity", pattern_rows, outputs, "pattern_similarity_figure_path", ("step_06", "pattern_similarity", selected_model, metric_name, passband_name, component or "all-components"), "no matched observed/synthetic station anomalies"))
                continue
            rows.append(
                _write_standard_notebook_figure(
                    "pattern_similarity",
                    pattern_rows,
                    render_notebook_figure,
                    pattern_plot_func,
                    outputs,
                    "pattern_similarity_figure_path",
                    metric_settings,
                    pattern_rows,
                    stem_parts=("step_06", "pattern_similarity", selected_model, metric_name, passband_name, component or "all-components"),
                    display_func=display_func,
                    metric=metric_name,
                    bin_label=passband_name,
                    title=f"{metric_name} Observed/Synthetic Station Pattern Similarity",
                    fit="linear",
                )
            )

    for passband_name in [None, *selected_passbands]:
        passband_label = passband_name or "all-passbands"
        heatmap_metrics = [
            name
            for name in comparison_metrics
            if _has_step06_region_rows(
                comparison_region_metrics,
                name,
                model_filter,
                passband_name,
                component,
                STEP06_METRIC_COMPARISON_VALUE_COL,
                station_region_col,
            )
        ]
        if not heatmap_metrics:
            rows.append(
                _step06_skipped_row(
                    "metric_heatmap",
                    comparison_region_metrics.iloc[0:0],
                    outputs,
                    "heatmap_figure_path",
                    (
                        "step_06",
                        "metric_heatmap",
                        selected_model,
                        "requested-metric-comparison",
                        passband_label,
                        component or "all-components",
                        STEP06_METRIC_COMPARISON_VALUE_COL,
                    ),
                    "no finite requested metric comparison region rows",
                )
            )
            continue
        rows.append(
            _write_standard_notebook_figure(
                "metric_heatmap",
                comparison_region_metrics,
                render_notebook_figure,
                heatmap_func,
                outputs,
                "heatmap_figure_path",
                metric_settings,
                data=comparison_region_metrics,
                dep=heatmap_metrics,
                indep=station_region_col,
                value_col=STEP06_METRIC_COMPARISON_VALUE_COL,
                passband=passband_name,
                model=model_filter,
                component=component,
                aggfunc="mean",
                title="Mean Metric Comparison Value by GeoJSON Region",
                stem_parts=(
                    "step_06",
                    "metric_heatmap",
                    selected_model,
                    "requested-metric-comparison",
                    passband_label,
                    component or "all-components",
                    STEP06_METRIC_COMPARISON_VALUE_COL,
                ),
                display_func=display_func,
            )
        )
    pattern_rows = pd.concat([frame for frame in all_pattern_rows if not frame.empty], ignore_index=True) if any(not frame.empty for frame in all_pattern_rows) else pd.DataFrame()
    return StandardAdditionalPlottingFigureResult(
        rows=tuple(rows),
        metric_summary=metric_summary,
        waveform_order=waveform_order,
        region_metrics=region_metrics,
        pattern_rows=pattern_rows,
    )


def write_step06_model_comparison_figures(
    *,
    metrics: pd.DataFrame,
    figure_dir: str | Path,
    metric_settings: Any,
    cfg: ConfigInput | None = None,
    models: Sequence[str] | None = None,
    value_col: str = "log2_residual",
    station_region_col: str = "station_geojson_region",
    component: str | None = None,
    geojson_region_func: Callable[..., pd.DataFrame] | None = None,
    boxplot_func: Callable[..., Any] | None = None,
    heatmap_delta_func: Callable[..., Any] | None = None,
    metric_map_func: Callable[..., Any] | None = None,
) -> StandardAdditionalPlottingFigureResult:
    """Write Step 6 model-comparison figures without pooling model rows."""

    if geojson_region_func is None:
        from spatial_vtk.spatial import geojson_metric_region_frame

        geojson_region_func = geojson_metric_region_frame
    if boxplot_func is None:
        from spatial_vtk.spatial.plot import boxplot

        boxplot_func = boxplot
    heatmap_delta_func = heatmap_delta_func or _plot_step06_model_delta_heatmap
    if metric_map_func is None:
        from spatial_vtk.spatial.map import plot_metric_map_by_model

        metric_map_func = plot_metric_map_by_model

    root = Path(figure_dir)
    root.mkdir(parents=True, exist_ok=True)
    metrics = _with_step06_delay_fraction(metrics)
    metrics = _with_step06_station_region_classes(metrics, cfg=cfg)
    model_pair = _step06_comparison_model_pair(metrics, models=models)
    if len(model_pair) < 2:
        return StandardAdditionalPlottingFigureResult(
            rows=(
                _step06_comparison_status_row(
                    "model_comparison",
                    "skipped",
                    root / "model_comparison_unavailable.png",
                    "fewer than two models are available for comparison",
                    row_count=len(metrics),
                ),
            ),
            metric_summary=pd.DataFrame(),
            waveform_order=pd.DataFrame(),
            region_metrics=pd.DataFrame(),
            pattern_rows=pd.DataFrame(),
        )

    comparison_metrics = _step06_metric_comparison_metrics(_step06_available_values(metrics, "metric"))
    selected_passbands = _step06_available_values(metrics, "passband") or _step06_available_values(metrics, "band")
    passband_values: list[str | None] = [None, *selected_passbands]
    try:
        region_metrics = geojson_region_func(
            metrics,
            target="station",
            selector="all",
            region_col=station_region_col,
        )
    except Exception:
        region_metrics = metrics.copy()
    region_metrics = _with_step06_delay_fraction(region_metrics)
    comparison_region_metrics = _with_step06_metric_comparison_values(region_metrics, default_value_col=value_col)
    category_cols = [
        column
        for column in (station_region_col, "mapped_region_type", "geomorphology")
        if column in comparison_region_metrics.columns
    ]
    rows: list[dict[str, Any]] = []

    for passband_name in passband_values:
        passband_label = _step06_label_token(passband_name or "all-passbands")
        for heatmap_spec in _step06_model_delta_heatmap_specs(comparison_metrics):
            heatmap_token = str(heatmap_spec["token"])
            heatmap_path = root / "region_heatmaps" / f"step_06_model_delta_heatmap__{heatmap_token}__{passband_label}.png"
            heatmap_path.parent.mkdir(parents=True, exist_ok=True)
            heatmap_rows = _step06_model_delta_region_frame(
                comparison_region_metrics,
                metrics=heatmap_spec["metrics"],
                models=model_pair,
                passband=passband_name,
                component=component,
                value_col=STEP06_METRIC_COMPARISON_VALUE_COL,
                region_col=station_region_col,
            )
            if heatmap_rows.empty:
                rows.append(
                    _step06_comparison_status_row(
                        "model_delta_heatmap",
                        "skipped",
                        heatmap_path,
                        f"no paired model region means are available for {heatmap_spec['title']}",
                        row_count=0,
                    )
                )
            else:
                rows.append(
                    _write_step06_comparison_plot(
                        "model_delta_heatmap",
                        heatmap_rows,
                        heatmap_path,
                        heatmap_delta_func,
                        heatmap_rows,
                        region_col=station_region_col,
                        metric_col="metric",
                        value_col="model_delta",
                        model_labels=model_pair,
                        passband=passband_name,
                        quantity_title=str(heatmap_spec["title"]),
                        quantity_label=str(heatmap_spec["quantity_label"]),
                        value_kind=heatmap_token,
                        settings=metric_settings,
                    )
                )

        for category_col in category_cols:
            for metric_name in comparison_metrics:
                metric_value_col = _step06_metric_value_col(metric_name, comparison_region_metrics, value_col)
                plot_rows = _filter_step06_rows(
                    comparison_region_metrics,
                    metric=metric_name,
                    model=None,
                    passband=passband_name,
                    component=component,
                )
                if "model" in plot_rows.columns:
                    plot_rows = plot_rows.loc[plot_rows["model"].astype(str).isin([str(item) for item in model_pair])]
                if plot_rows.empty or category_col not in plot_rows.columns or metric_value_col not in plot_rows.columns:
                    continue
                finite = pd.to_numeric(plot_rows[metric_value_col], errors="coerce").notna()
                plot_rows = plot_rows.loc[finite & plot_rows[category_col].notna()].copy()
                if plot_rows.empty or plot_rows["model"].astype(str).nunique() < 2:
                    continue
                boxplot_path = (
                    root
                    / "model_boxplots"
                    / _step06_label_token(category_col)
                    / f"step_06_model_boxplot__{_step06_label_token(metric_name)}__{passband_label}__{_step06_label_token(category_col)}.png"
                )
                boxplot_path.parent.mkdir(parents=True, exist_ok=True)
                rows.append(
                    _write_step06_comparison_plot(
                        "model_boxplot",
                        plot_rows,
                        boxplot_path,
                        boxplot_func,
                        plot_rows,
                        dep=metric_name,
                        indep=category_col,
                        value_col=metric_value_col,
                        passband=passband_name,
                        model=model_pair,
                        component=component,
                        colorby="model",
                        title=f"{metric_name} by {category_col}: model comparison",
                        settings=metric_settings,
                    )
                )

        for metric_name in comparison_metrics:
            metric_value_col = _step06_metric_value_col(metric_name, metrics, value_col)
            station_rows = _step06_station_model_map_frame(
                metrics,
                metric=metric_name,
                models=model_pair,
                passband=passband_name,
                component=component,
                value_col=metric_value_col,
            )
            map_path = root / "model_maps" / f"step_06_model_map__{_step06_label_token(metric_name)}__{passband_label}.png"
            map_path.parent.mkdir(parents=True, exist_ok=True)
            if station_rows.empty:
                rows.append(
                    _step06_comparison_status_row(
                        "model_metric_map",
                        "skipped",
                        map_path,
                        "no finite station rows are available for both models",
                        row_count=0,
                    )
                )
                continue
            rows.append(
                _write_step06_comparison_plot(
                    "model_metric_map",
                    station_rows,
                    map_path,
                    metric_map_func,
                    station_rows,
                    model_col="model",
                    value_col=metric_value_col,
                    lon_col="sta_lon",
                    lat_col="sta_lat",
                    title=f"{metric_name} spatial comparison by model",
                    add_basemap=True,
                    basemap_kwargs={"cache_download": False},
                    settings=metric_settings,
                )
            )

    return StandardAdditionalPlottingFigureResult(
        rows=tuple(rows),
        metric_summary=pd.DataFrame(
            {
                "Input": ["Models", "Comparison metrics", "Figure rows"],
                "Value": [", ".join(model_pair), ", ".join(comparison_metrics), len(rows)],
            }
        ),
        waveform_order=pd.DataFrame(),
        region_metrics=region_metrics,
        pattern_rows=pd.DataFrame(),
    )


def _step06_comparison_model_pair(frame: pd.DataFrame, *, models: Sequence[str] | None = None) -> list[str]:
    """Return the two models to compare, preferring CVM-S then CVM-H labels."""

    available = [str(value) for value in (models or _step06_available_values(frame, "model")) if str(value).strip()]
    if not available:
        return []
    unique = list(dict.fromkeys(available))
    preferred: list[str] = []
    for needle in ("cvms", "cvm-s", "cvmh", "cvm-h"):
        match = next((model for model in unique if needle in model.casefold().replace("_", "-")), None)
        if match is not None and match not in preferred:
            preferred.append(match)
    for model in unique:
        if model not in preferred:
            preferred.append(model)
    return preferred[:2]


def _with_step06_station_region_classes(frame: pd.DataFrame, *, cfg: ConfigInput | None) -> pd.DataFrame:
    """Attach GeoJSON-derived station class columns for Step 6 comparisons."""

    if frame.empty or cfg is None:
        return frame
    if {"mapped_region_type", "geomorphology"}.issubset(frame.columns):
        return frame
    lon_col = _first_existing(frame, ["sta_lon", "station_lon", "lon", "longitude"])
    lat_col = _first_existing(frame, ["sta_lat", "station_lat", "lat", "latitude"])
    station_col = _first_existing(frame, ["station", "station_name", "station_id", "station_code"])
    if lon_col is None or lat_col is None or station_col is None:
        return frame
    station_rows = (
        frame[[station_col, lon_col, lat_col]]
        .dropna(subset=[station_col, lon_col, lat_col])
        .drop_duplicates(subset=[station_col])
        .rename(columns={lon_col: "sta_lon", lat_col: "sta_lat"})
    )
    if station_rows.empty:
        return frame
    classified = _site_metadata_with_geology(
        station_rows,
        cfg=cfg,
        progress=lambda _message: None,
    )
    return _merge_station_region_class_metadata(frame, classified)


def _step06_label_token(value: object) -> str:
    """Return a short filename token for Step 6 comparison outputs."""

    return slugify(str(value).replace(" ", "_").replace("/", "_")).lower()


def _step06_model_delta_region_frame(
    frame: pd.DataFrame,
    *,
    metrics: Sequence[str],
    models: Sequence[str],
    passband: str | None,
    component: str | None,
    value_col: str,
    region_col: str,
) -> pd.DataFrame:
    """Return per-region model deltas after separate model aggregation."""

    if len(models) < 2 or frame.empty or region_col not in frame.columns or "model" not in frame.columns:
        return pd.DataFrame()
    parts: list[pd.DataFrame] = []
    for metric_name in metrics:
        subset = _filter_step06_rows(frame, metric=metric_name, model=None, passband=passband, component=component)
        if subset.empty or value_col not in subset.columns:
            continue
        subset = subset.loc[subset["model"].astype(str).isin([str(item) for item in models])].copy()
        subset[value_col] = pd.to_numeric(subset[value_col], errors="coerce")
        subset = subset.loc[subset[value_col].notna() & subset[region_col].notna()].copy()
        if subset.empty:
            continue
        grouped = subset.groupby([region_col, "model"], dropna=False)[value_col].mean().reset_index()
        pivot = grouped.pivot(index=region_col, columns="model", values=value_col)
        missing = [model for model in models if model not in pivot.columns]
        if missing:
            continue
        delta = pivot[str(models[1])] - pivot[str(models[0])]
        part = delta.rename("model_delta").reset_index()
        part["metric"] = metric_name
        part["model_a"] = str(models[0])
        part["model_b"] = str(models[1])
        part["comparison"] = f"{models[1]} minus {models[0]}"
        parts.append(part)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def _step06_station_model_map_frame(
    frame: pd.DataFrame,
    *,
    metric: str,
    models: Sequence[str],
    passband: str | None,
    component: str | None,
    value_col: str,
) -> pd.DataFrame:
    """Return station-mean rows for model-faceted comparison maps."""

    if len(models) < 2 or frame.empty or "model" not in frame.columns or value_col not in frame.columns:
        return pd.DataFrame()
    lon_col = _first_existing(frame, ["sta_lon", "station_lon", "lon", "longitude"])
    lat_col = _first_existing(frame, ["sta_lat", "station_lat", "lat", "latitude"])
    if lon_col is None or lat_col is None:
        return pd.DataFrame()
    subset = _filter_step06_rows(frame, metric=metric, model=None, passband=passband, component=component)
    subset = subset.loc[subset["model"].astype(str).isin([str(item) for item in models])].copy()
    if subset.empty:
        return pd.DataFrame()
    subset[value_col] = pd.to_numeric(subset[value_col], errors="coerce")
    subset = subset.loc[subset[value_col].notna()].copy()
    if subset.empty or subset["model"].astype(str).nunique() < 2:
        return pd.DataFrame()
    group_cols = [column for column in ("model", "station", "metric", "passband", "component") if column in subset.columns]
    out = (
        subset.groupby(group_cols, dropna=False)
        .agg(
            sta_lon=(lon_col, "first"),
            sta_lat=(lat_col, "first"),
            **{
                value_col: (value_col, "mean"),
                "event_count": ("event_id", "nunique") if "event_id" in subset.columns else (value_col, "size"),
            },
        )
        .reset_index()
    )
    return out.loc[pd.to_numeric(out[value_col], errors="coerce").notna()].copy()


def _plot_step06_model_delta_heatmap(
    data: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    region_col: str,
    metric_col: str,
    value_col: str,
    model_labels: Sequence[str],
    passband: str | None = None,
    quantity_title: str = "Metric values",
    quantity_label: str = "Difference",
    value_kind: str = "model_delta",
    showfig: bool | None = None,
    savefig: bool | None = None,
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
) -> Any:
    """Plot a model-delta heatmap with rows kept separate until differencing."""

    import matplotlib.pyplot as plt
    import numpy as np

    from spatial_vtk.config.labels import display_label, metric_display_name, model_display_name
    from spatial_vtk.spatial.plot.metrics import _heatmap

    pivot = data.pivot_table(index=region_col, columns=metric_col, values=value_col, aggfunc="mean")
    if not pivot.empty:
        pivot = pivot.reindex(columns=[metric for metric in data[metric_col].dropna().astype(str).unique() if metric in pivot.columns])
    label_a = model_display_name(str(model_labels[0])) if model_labels else "model A"
    label_b = model_display_name(str(model_labels[1])) if len(model_labels) > 1 else "model B"
    metric_labels = {column: metric_display_name(str(column)) for column in pivot.columns}
    pivot = pivot.rename(columns=metric_labels)
    values = pivot.to_numpy(dtype=float) if not pivot.empty else np.array([])
    limit = np.nanpercentile(np.abs(values), 95) if values.size and np.isfinite(values).any() else 1.0
    limit = float(limit) if np.isfinite(limit) and limit > 0 else 1.0
    title = f"Model Difference by GeoJSON Region\n{label_b} minus {label_a}: {quantity_title}"
    if passband is not None:
        title += f" | Period: {passband}"
    return _heatmap(
        pivot,
        output_path,
        title=title,
        cbar_label=f"{label_b} minus {label_a}\n{quantity_label}",
        x_label="Metric",
        y_label=display_label(region_col),
        showfig=showfig,
        savefig=savefig,
        cmap="coolwarm",
        vmin=-limit,
        vmax=limit,
        sidecar_df=data,
        source_rows=data,
        write_sidecar=write_sidecar,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
        metadata={"figure_type": "model_delta_heatmap", "value_col": value_col, "value_kind": value_kind},
    )


def _write_step06_comparison_plot(
    artifact: str,
    frame: pd.DataFrame,
    path: Path,
    plot_func: Callable[..., Any],
    *args: Any,
    settings: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """Write one Step 6 comparison figure and return a status row."""

    try:
        plot_kwargs = _step06_direct_plot_kwargs(settings)
        plot_func(*args, output_path=path, **kwargs, **plot_kwargs)
        status = "wrote"
        message = f"wrote {path}"
    except Exception as exc:
        _close_matplotlib_figures()
        status = "plot_failed"
        message = f"{type(exc).__name__}: {exc}"
    return _step06_comparison_status_row(artifact, status, path, message, row_count=len(frame))


def _step06_direct_plot_kwargs(settings: Any) -> dict[str, Any]:
    """Return plotting kwargs safe for direct Step 6 comparison plot calls."""

    return {
        "showfig": False,
        "savefig": True,
        "write_sidecar": bool(getattr(settings, "write_sidecar", False)),
        "sidecar_rows": getattr(settings, "sidecar_rows", None),
    }


def _step06_comparison_status_row(
    artifact: str,
    status: str,
    path: Path,
    message: str,
    *,
    row_count: int,
) -> dict[str, Any]:
    """Return a normalized status row for a Step 6 comparison figure."""

    return {
        "artifact": artifact,
        "status": status,
        "row_count": row_count,
        "figure_path": str(path),
        "figure_exists": path.exists(),
        "message": message,
    }


def _first_available_value(frame: pd.DataFrame, column: str, *, fallback: str) -> str:
    """Return the first non-empty string value in a dataframe column."""

    if column not in frame.columns:
        return fallback
    values = frame[column].dropna().astype(str)
    values = values[values.str.strip().ne("")]
    return str(values.iloc[0]) if not values.empty else fallback


def _step06_available_values(frame: pd.DataFrame, column: str) -> list[str]:
    """Return sorted non-empty values for a Step 6 metric dimension."""

    if column not in frame.columns:
        return []
    values = frame[column].dropna().astype(str)
    values = values[values.str.strip().ne("")]
    return sorted(values.unique().tolist())


def _as_step06_list(values: Sequence[str] | str) -> list[str]:
    """Normalize a scalar or sequence plotting option into a list."""

    if isinstance(values, str):
        return [values]
    return [str(value) for value in values]


def _step06_metric_key(metric: object) -> str:
    """Return a tolerant key for matching configured Step 6 metric names."""

    return re.sub(r"[^a-z0-9]+", "_", str(metric).strip().casefold()).strip("_")


def _step06_metric_comparison_metrics(metric_names: Sequence[str]) -> list[str]:
    """Return available metrics in the fixed Step 6 comparison-figure order."""

    available_by_key = {_step06_metric_key(name): str(name) for name in metric_names}
    ordered: list[str] = []
    for canonical, aliases in STEP06_METRIC_COMPARISON_METRICS:
        keys = {_step06_metric_key(canonical), *aliases}
        for key in keys:
            if key in available_by_key:
                ordered.append(available_by_key[key])
                break
    return ordered


def _step06_model_delta_heatmap_specs(metric_names: Sequence[str]) -> list[dict[str, object]]:
    """Return model-delta heatmap specs with only available metrics included."""

    available = {str(metric): _step06_metric_key(metric) for metric in metric_names}
    specs: list[dict[str, object]] = []
    for spec in STEP06_MODEL_DELTA_HEATMAP_SPECS:
        keys = spec["metric_keys"]
        selected = [metric for metric, key in available.items() if key in keys]
        if not selected:
            continue
        out = dict(spec)
        out["metrics"] = selected
        specs.append(out)
    return specs


def _with_step06_metric_comparison_values(frame: pd.DataFrame, *, default_value_col: str) -> pd.DataFrame:
    """Add the value column used by Step 6 metric comparison figures."""

    if frame.empty or "metric" not in frame.columns:
        out = frame.copy()
        out[STEP06_METRIC_COMPARISON_VALUE_COL] = pd.Series(dtype="float64")
        return out
    out = frame.copy()
    metric_keys = out["metric"].map(_step06_metric_key)
    out[STEP06_METRIC_COMPARISON_VALUE_COL] = pd.Series(float("nan"), index=out.index, dtype="float64")
    delay_mask = metric_keys.eq("traveltime_delay")
    cc_mask = metric_keys.eq("delay_corrected_cc")
    raw_mask = metric_keys.isin(STEP06_METRIC_COMPARISON_RAW_VALUE_KEYS)
    if delay_mask.any() and "delay_fraction_dominant_period" in out.columns:
        out.loc[delay_mask, STEP06_METRIC_COMPARISON_VALUE_COL] = pd.to_numeric(
            out.loc[delay_mask, "delay_fraction_dominant_period"],
            errors="coerce",
        )
    if "value" in out.columns:
        value_mask = cc_mask | (delay_mask & out[STEP06_METRIC_COMPARISON_VALUE_COL].isna())
        out.loc[value_mask, STEP06_METRIC_COMPARISON_VALUE_COL] = pd.to_numeric(
            out.loc[value_mask, "value"],
            errors="coerce",
        )
    if default_value_col in out.columns:
        residual_mask = ~raw_mask
        out.loc[residual_mask, STEP06_METRIC_COMPARISON_VALUE_COL] = pd.to_numeric(
            out.loc[residual_mask, default_value_col],
            errors="coerce",
        )
    return out


def _with_step06_delay_fraction(frame: pd.DataFrame) -> pd.DataFrame:
    """Add delay time as a fraction of dominant period when delay rows exist."""

    if "metric" not in frame.columns or "delay_fraction_dominant_period" in frame.columns:
        return frame
    delay_mask = frame["metric"].astype(str).str.lower().eq("traveltime_delay")
    if not delay_mask.any():
        return frame
    out = frame.copy()
    source_col = "value" if "value" in out.columns else "residual"
    delay_s = pd.to_numeric(out[source_col], errors="coerce") if source_col in out.columns else pd.Series(float("nan"), index=out.index)
    if "dominant_period_s" in out.columns:
        denominator = pd.to_numeric(out["dominant_period_s"], errors="coerce")
    elif "period_s" in out.columns:
        denominator = pd.to_numeric(out["period_s"], errors="coerce")
    else:
        band_col = "passband" if "passband" in out.columns else "band" if "band" in out.columns else None
        denominator = out[band_col].map(_step06_passband_midpoint_s) if band_col else pd.Series(float("nan"), index=out.index)
    denominator = denominator.where(denominator > 0)
    out["delay_fraction_dominant_period"] = delay_s / denominator
    return out


def _step06_passband_midpoint_s(value: object) -> float:
    """Return a simple period midpoint parsed from labels such as ``1-2 sec``."""

    import re

    numbers = [float(match) for match in re.findall(r"\d+(?:\.\d+)?", str(value))]
    if len(numbers) >= 2:
        return sum(numbers[:2]) / 2.0
    if numbers:
        return numbers[0]
    return float("nan")


def _step06_metric_value_col(metric: str, frame: pd.DataFrame, default: str) -> str:
    """Choose the plotted value column appropriate for one metric."""

    key = str(metric).lower()
    if key in {"original_cc", "delay_corrected_cc"} and "value" in frame.columns:
        return "value"
    if key == "traveltime_delay" and "delay_fraction_dominant_period" in frame.columns:
        return "delay_fraction_dominant_period"
    return default


def _filter_step06_rows(
    frame: pd.DataFrame,
    *,
    metric: str | None = None,
    model: str | None = None,
    passband: str | None = None,
    component: str | None = None,
) -> pd.DataFrame:
    """Apply exact Step 6 metric dimension filters that are present."""

    out = frame
    if metric is not None and "metric" in out.columns:
        out = out.loc[out["metric"].astype(str).eq(str(metric))]
    if model is not None and "model" in out.columns:
        out = out.loc[out["model"].astype(str).eq(str(model))]
    band_col = "passband" if "passband" in out.columns else "band" if "band" in out.columns else None
    if passband is not None and band_col is not None:
        out = out.loc[out[band_col].astype(str).eq(str(passband))]
    if component is not None and "component" in out.columns:
        out = out.loc[out["component"].astype(str).eq(str(component))]
    return out


def _step06_is_spectral_metric(metric: object) -> bool:
    """Return whether Step 6 should treat a metric as period-scoped spectral data."""

    text = str(metric).strip()
    return text.upper() in {"FAS", "PSA"} or text.casefold() in {"fas", "psa"}


def _has_step06_finite_rows(
    frame: pd.DataFrame,
    metric: str,
    model: str | None,
    passband: str | None,
    component: str | None,
    value_col: str,
    *,
    require_distance: bool = False,
) -> bool:
    """Return whether a requested Step 6 metric subset has finite values."""

    subset = _filter_step06_rows(frame, metric=metric, model=model, passband=passband, component=component)
    if subset.empty or value_col not in subset.columns:
        return False
    finite = pd.to_numeric(subset[value_col], errors="coerce").replace([float("inf"), float("-inf")], pd.NA).notna()
    if require_distance:
        distance_col = "distance_km" if "distance_km" in subset.columns else "distance" if "distance" in subset.columns else None
        if distance_col is None:
            return False
        finite &= pd.to_numeric(subset[distance_col], errors="coerce").replace([float("inf"), float("-inf")], pd.NA).notna()
    return bool(finite.any())


def _has_step06_region_rows(
    frame: pd.DataFrame,
    metric: str,
    model: str | None,
    passband: str | None,
    component: str | None,
    value_col: str,
    region_col: str,
) -> bool:
    """Return whether a Step 6 region plot has real categories and values."""

    subset = _filter_step06_rows(frame, metric=metric, model=model, passband=passband, component=component)
    if subset.empty or region_col not in subset.columns or value_col not in subset.columns:
        return False
    categories = subset[region_col].dropna().astype(str).str.strip()
    finite = pd.to_numeric(subset[value_col], errors="coerce").replace([float("inf"), float("-inf")], pd.NA).notna()
    return bool(categories.ne("").any() and finite.any())


def _select_step06_waveform_event_id(
    event_stations: pd.DataFrame,
    *,
    comparison_eligible: pd.DataFrame,
    requested_event_id: str,
    component: str,
    passband: str,
) -> str:
    """Use the requested event when possible, otherwise choose the first available one."""

    for frame in (comparison_eligible, event_stations):
        if frame.empty or "event_id" not in frame.columns:
            continue
        subset = frame
        if "component" in subset.columns:
            subset = subset.loc[subset["component"].astype(str).eq(str(component))]
        band_col = "passband" if "passband" in subset.columns else "band" if "band" in subset.columns else None
        if band_col is not None:
            subset = subset.loc[subset[band_col].astype(str).eq(str(passband))]
        requested = subset.loc[subset["event_id"].astype(str).eq(str(requested_event_id))]
        if not requested.empty:
            return requested_event_id
        values = subset["event_id"].dropna().astype(str)
        values = values[values.str.strip().ne("")]
        if not values.empty:
            return str(values.iloc[0])
    return requested_event_id


def _step06_skipped_row(
    artifact: str,
    frame: pd.DataFrame,
    outputs: Any,
    figure_path_name: str,
    stem_parts: Sequence[object],
    reason: str,
) -> dict[str, Any]:
    """Return a status row for a Step 6 figure intentionally not written."""

    path = outputs.figure_path(figure_path_name, stem_parts=stem_parts)
    return {
        "artifact": artifact,
        "status": "skipped",
        "row_count": len(frame),
        "figure_path": str(path),
        "figure_exists": path.exists(),
        "message": reason,
    }


def _write_standard_notebook_figure(
    artifact: str,
    frame: pd.DataFrame,
    render_func: Callable[..., Any],
    plot_func: Callable[..., Any],
    outputs: Any,
    figure_path_name: str,
    settings: Any,
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """Render one standard tutorial figure and return a status row."""

    try:
        render_func(plot_func, outputs, figure_path_name, settings, *args, **kwargs)
        path = outputs.figure_path(
            figure_path_name,
            stem=kwargs.get("stem"),
            stem_parts=kwargs.get("stem_parts"),
        )
        status = "wrote"
        message = f"wrote {path}"
    except Exception as exc:
        path = outputs.figure_path(
            figure_path_name,
            stem=kwargs.get("stem"),
            stem_parts=kwargs.get("stem_parts"),
        )
        _close_matplotlib_figures()
        status = "plot_failed"
        message = f"{type(exc).__name__}: {exc}"
    return {
        "artifact": artifact,
        "status": status,
        "row_count": len(frame),
        "figure_path": str(path),
        "figure_exists": path.exists(),
        "message": message,
    }


def write_large_run_geojson_region_figures_from_outputs(
    outputs: Any,
    ingest_outputs: Any,
    *,
    geojson_path: str | Path,
    figure_dir: str | Path,
    cfg: ConfigInput | None = None,
    metric: str = "PGA",
    passband: str | Sequence[str] = "2-3 sec",
    component: str | Sequence[str] | None = None,
    model: str | Sequence[str] | None = None,
    value_col: str = "log2_residual",
    compare_to: str | Sequence[str] | None = "LA Basin",
    max_rows: int = 200_000,
    region_boxplot_prefix: str = "geojson_region_boxplot",
    overview_add_basemap: bool = True,
    corridor_add_basemap: bool = True,
    corridor_filters: Mapping[str, object] | None = None,
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
    annotate_if_missing: bool = True,
    overwrite: bool = False,
    showfig: bool = False,
) -> RegionFigureResult:
    """Write the standard large-run Step 5 region and corridor figures.

    The helper keeps large-run notebooks focused on figure settings: package
    code loads prepared station/event context, renders the GeoJSON overview,
    renders the corridor map when the corridor table is ready, and delegates the
    bounded metric read for the region boxplot to
    :func:`write_large_run_region_boxplot_from_outputs`.
    """

    from spatial_vtk.spatial.map import plot_corridor_map, plot_geojson_polygons_map

    output_group = getattr(outputs, "outputs", outputs)
    output_dir = Path(figure_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []
    geojson_status = "skipped"
    corridor_status = "skipped"
    geojson_overview_path = _resolve_region_figure_output(
        output_group,
        "geojson_polygons_map_path",
        "geojson_polygons_map",
        cfg=cfg,
        fallback_dir=output_dir,
        prefer_fallback_dir=True,
    )
    corridor_map_path = _resolve_region_figure_output(
        output_group,
        "corridor_map_path",
        "corridor_map",
        cfg=cfg,
        fallback_dir=output_dir,
        prefer_fallback_dir=True,
    )

    try:
        stations = _load_group_table_by_path(
            ingest_outputs,
            "prepared_stations_path",
            "prepared_stations",
            cfg=cfg,
        )
        events = _load_group_table_by_path(
            ingest_outputs,
            "prepared_events_path",
            "prepared_events",
            cfg=cfg,
        )
    except Exception as exc:
        boxplot_result = RegionBoxplotResult(
            None,
            None,
            0,
            "missing_context",
            f"skip region boxplot: could not load station/event context: {exc}",
        )
        messages.append(f"geojson_overview: skip GeoJSON overview: could not load station/event context: {exc}")
        messages.append(f"corridor_map: skip corridor map: could not load station/event context: {exc}")
        return RegionFigureResult(
            geojson_overview_path=None,
            corridor_map_path=None,
            boxplot_result=boxplot_result,
            geojson_status="missing_context",
            corridor_status="missing_context",
            messages=tuple(messages),
        )

    if geojson_overview_path.exists() and not overwrite:
        geojson_status = "exists"
        messages.append(f"geojson_overview: skip {geojson_overview_path.name}: exists")
    else:
        try:
            plot_geojson_polygons_map(
                geojson_path,
                output_path=geojson_overview_path,
                stations_df=None,
                events_df=None,
                label_polygons=False,
                legend_polygons=True,
                add_basemap=overview_add_basemap,
                savefig=True,
                showfig=showfig,
                write_sidecar=write_sidecar,
                sidecar_rows=sidecar_rows,
                sidecar_dir=sidecar_dir,
            )
            _close_matplotlib_figures()
            geojson_status = "wrote"
            messages.append(f"geojson_overview: wrote {geojson_overview_path}")
        except Exception as exc:
            _close_matplotlib_figures()
            geojson_status = "plot_failed"
            messages.append(f"geojson_overview: skip {geojson_overview_path.name}: {type(exc).__name__}: {exc}")

    corridor_table_path = getattr(output_group, "paths", {}).get("corridors_path")
    if corridor_table_path is not None and Path(corridor_table_path).exists():
        corridors = read_table(corridor_table_path)
    elif hasattr(output_group, "load_table"):
        corridors = output_group.load_table("corridors", cfg=cfg, missing="skip")
    else:
        corridors = None
    if corridors is not None:
        corridors = _filter_table_by_values(corridors, corridor_filters)
    if corridors is None:
        corridor_status = "missing_input"
        messages.append("corridor_map: corridor table is not ready yet; skipping corridor map")
    elif corridors.empty:
        corridor_status = "no_data"
        messages.append("corridor_map: no corridors match the requested filters; skipping corridor map")
    elif corridor_map_path.exists() and not overwrite:
        corridor_status = "exists"
        messages.append(f"corridor_map: skip {corridor_map_path.name}: exists")
    else:
        try:
            plot_corridor_map(
                corridors,
                output_path=corridor_map_path,
                stations_df=None,
                events_df=None,
                add_basemap=corridor_add_basemap,
                savefig=True,
                showfig=showfig,
                write_sidecar=write_sidecar,
                sidecar_rows=sidecar_rows,
                sidecar_dir=sidecar_dir,
            )
            _close_matplotlib_figures()
            corridor_status = "wrote"
            messages.append(f"corridor_map: wrote {corridor_map_path}")
        except Exception as exc:
            _close_matplotlib_figures()
            corridor_status = "plot_failed"
            messages.append(f"corridor_map: skip {corridor_map_path.name}: {type(exc).__name__}: {exc}")

    boxplot_result = write_large_run_region_boxplot_from_outputs(
        output_group,
        figure_dir=output_dir,
        geojson_path=geojson_path,
        station_metadata=stations,
        metric=metric,
        passband=passband,
        component=component,
        model=model,
        value_col=value_col,
        compare_to=compare_to,
        max_rows=max_rows,
        output_prefix=region_boxplot_prefix,
        write_sidecar=write_sidecar,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
        annotate_if_missing=annotate_if_missing,
        overwrite=overwrite,
        showfig=showfig,
    )
    messages.append(f"region_boxplot: {boxplot_result.message}")

    return RegionFigureResult(
        geojson_overview_path=geojson_overview_path,
        corridor_map_path=corridor_map_path if corridors is not None else None,
        boxplot_result=boxplot_result,
        geojson_status=geojson_status,
        corridor_status=corridor_status,
        messages=tuple(messages),
    )


def _filter_table_by_values(df: pd.DataFrame, filters: Mapping[str, object] | None) -> pd.DataFrame:
    """Return rows matching scalar/list filters for columns present in a table."""

    if not filters or df is None or df.empty:
        return df
    filtered = df
    for column, value in filters.items():
        if column not in filtered.columns or value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            values = [str(item) for item in value]
        else:
            values = [str(value)]
        filtered = filtered[filtered[column].astype(str).isin(values)]
    return filtered


def write_large_run_geojson_region_figures_from_notebook_settings(
    outputs: Any,
    ingest_outputs: Any,
    settings: Any,
    *,
    geojson_path: str | Path,
    cfg: ConfigInput | None = None,
    overwrite: bool = False,
) -> RegionFigureResult:
    """Write Step 5 GeoJSON/corridor figures using notebook figure settings.

    This wrapper owns the notebook-facing render gate and settings-to-keyword
    translation for the standard Step 5 figure family.
    """

    prepared_stations_path = getattr(ingest_outputs, "prepared_stations_path", None)
    prepared_events_path = getattr(ingest_outputs, "prepared_events_path", None)
    gate = settings.render_gate(
        [prepared_stations_path, prepared_events_path, geojson_path],
        missing_message="Skipping figures until stations, events, and region GeoJSON are ready.",
    )
    if not gate.ready:
        status = "disabled" if not gate.figures_enabled else "missing_input"
        boxplot_result = RegionBoxplotResult(
            None,
            None,
            0,
            status,
            gate.message,
        )
        return RegionFigureResult(
            geojson_overview_path=None,
            corridor_map_path=None,
            boxplot_result=boxplot_result,
            geojson_status=status,
            corridor_status=status,
            messages=(
                f"geojson_overview: {gate.message}",
                f"corridor_map: {gate.message}",
                f"region_boxplot: {gate.message}",
            ),
        )
    return write_large_run_geojson_region_figures_from_outputs(
        outputs,
        ingest_outputs,
        geojson_path=geojson_path,
        figure_dir=settings.figure_dir,
        cfg=cfg,
        metric=settings.metric,
        passband=settings.passband,
        component=settings.component,
        model=settings.model,
        value_col=settings.value_col,
        compare_to=settings.compare_to,
        max_rows=settings.sample_rows,
        corridor_add_basemap=settings.add_basemap,
        corridor_filters=getattr(settings, "corridor_filters", None),
        **settings.sidecars.kwargs(),
        annotate_if_missing=True,
        overwrite=overwrite,
        showfig=settings.showfig,
    )


def write_large_run_region_boxplot(
    metric_source: str | Path,
    *,
    figure_dir: str | Path,
    geojson_path: str | Path | None = None,
    metric: str = "PGA",
    passband: str | Sequence[str] = "2-3 sec",
    component: str | Sequence[str] | None = None,
    model: str | Sequence[str] | None = None,
    value_col: str = "log2_residual",
    compare_to: str | Sequence[str] | None = "LA Basin",
    max_rows: int = 200_000,
    output_prefix: str = "geojson_region_boxplot",
    annotate_if_missing: bool = True,
    station_metadata: pd.DataFrame | str | Path | None = None,
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
    overwrite: bool = False,
    showfig: bool = False,
) -> RegionBoxplotResult:
    """Write a station-region metric boxplot from a bounded metric table read.

    This helper keeps large-run notebooks lightweight: it reads at most
    ``max_rows`` metric rows, reuses existing station-region columns when
    present, can annotate station regions from a GeoJSON file, and writes one
    reproducibly named figure under ``figure_dir``.
    """

    source_path = Path(metric_source).expanduser()
    output_dir = Path(figure_dir).expanduser()
    if not source_path.exists():
        return RegionBoxplotResult(None, None, 0, "missing_input", "skip region boxplot: metrics table is not ready yet")

    metric_rows = read_bounded_table(source_path, int(max_rows))
    if metric_rows.empty:
        return RegionBoxplotResult(None, None, 0, "empty_input", "skip region boxplot: metrics table has no rows")

    region_col = first_existing(metric_rows, ["station_region", "station_geojson_region", "station_geojson_labels"])
    geojson_file = None if geojson_path is None else Path(geojson_path).expanduser()
    if region_col is None and annotate_if_missing and geojson_file is not None and geojson_file.exists():
        try:
            from spatial_vtk.spatial.calculate import add_geojson_metadata_to_metrics

            metric_rows = add_geojson_metadata_to_metrics(metric_rows, geojson_file, target="station", selector="all")
            region_col = first_existing(metric_rows, ["station_region", "station_geojson_region", "station_geojson_labels"])
        except Exception as exc:
            return RegionBoxplotResult(
                None,
                None,
                len(metric_rows),
                "annotation_failed",
                f"skip region boxplot: could not annotate metric rows with GeoJSON regions: {exc}",
            )
    if region_col is None:
        suffix = "; run Step 5 enrichment first" if not annotate_if_missing else ""
        return RegionBoxplotResult(
            None,
            None,
            len(metric_rows),
            "missing_region_column",
            f"skip region boxplot: no station GeoJSON region column is available{suffix}",
        )
    if value_col not in metric_rows.columns:
        return RegionBoxplotResult(
            None,
            None,
            len(metric_rows),
            "missing_value_column",
            f"skip region boxplot: {value_col!r} is not present",
        )

    metric_rows = _merge_station_region_class_metadata(metric_rows, station_metadata)
    plot_rows = metric_rows.copy()
    plot_rows["station_region"] = plot_rows[region_col].fillna("").astype(str).str.replace("_", " ", regex=False)
    plot_rows = plot_rows.loc[plot_rows["station_region"].str.len() > 0].copy()
    plot_rows = _merge_geojson_region_class_metadata(plot_rows, geojson_file, region_col="station_region")
    if plot_rows.empty:
        return RegionBoxplotResult(
            None,
            None,
            len(metric_rows),
            "empty_region_labels",
            "skip region boxplot: no rows have station-region labels",
        )
    comparison_table = _region_boxplot_comparison_table(
        plot_rows,
        metric=metric,
        passband=passband,
        component=component,
        model=model,
        value_col=value_col,
        compare_to=compare_to,
    )

    output = output_dir / _region_boxplot_name(
        output_prefix,
        metric=metric,
        passband=passband,
        component=component,
        model=model,
        value_col=value_col,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not overwrite:
        sidecar_path = _write_region_boxplot_sidecar(
            output,
            plot_rows,
            write_sidecar=write_sidecar,
            sidecar_rows=sidecar_rows,
            sidecar_dir=sidecar_dir,
            metric=metric,
            passband=passband,
            component=component,
            model=model,
            value_col=value_col,
            compare_to=compare_to,
        )
        message = f"skip {output.name}: exists"
        if sidecar_path is not None:
            message += f"; wrote {sidecar_path}"
        return RegionBoxplotResult(output, sidecar_path, len(plot_rows), "exists", message, comparison_table)

    try:
        from spatial_vtk.spatial.plot.metrics import boxplot

        color_col = _region_boxplot_color_column(plot_rows)
        boxplot(
            data=plot_rows,
            output_path=output,
            dep=metric,
            indep="station_region",
            value_col=value_col,
            passband=passband,
            model=model,
            component=component,
            colorby=color_col,
            compare_to=compare_to,
            table=True,
            title=f"{metric} Residuals by Station Region",
            showfig=showfig,
            savefig=True,
        )
        _close_matplotlib_figures()
        sidecar_path = _write_region_boxplot_sidecar(
            output,
            plot_rows,
            write_sidecar=write_sidecar,
            sidecar_rows=sidecar_rows,
            sidecar_dir=sidecar_dir,
            metric=metric,
            passband=passband,
            component=component,
            model=model,
            value_col=value_col,
            compare_to=compare_to,
        )
    except Exception as exc:
        _close_matplotlib_figures()
        return RegionBoxplotResult(
            output,
            None,
            len(plot_rows),
            "plot_failed",
            f"skip {output.name}: {type(exc).__name__}: {exc}",
        )
    message = f"wrote {output}"
    if sidecar_path is not None:
        message += f" and {sidecar_path}"
    return RegionBoxplotResult(output, sidecar_path, len(plot_rows), "wrote", message, comparison_table)


def write_large_run_region_boxplot_from_outputs(
    outputs: Any,
    *,
    figure_dir: str | Path,
    metric_candidates: Sequence[str] = ("metrics_enriched_path", "metrics_long_path"),
    default_metric_source: str | Path | None = "metrics_long_path",
    cfg: ConfigInput | None = None,
    station_metadata: pd.DataFrame | str | Path | None = None,
    **kwargs: Any,
) -> RegionBoxplotResult:
    """Write a region boxplot using a fallback metric table from an output group.

    Large-run notebooks usually prefer ``metrics_enriched`` because it carries
    spatial metadata, but can fall back to ``metrics_long`` when enrichment has
    not been written yet. This helper keeps that fallback selection in package
    code and delegates the bounded table read and plotting behavior to
    :func:`write_large_run_region_boxplot`.
    """

    output_group = getattr(outputs, "outputs", outputs)
    metric_source = output_group.first_existing_path(
        tuple(metric_candidates),
        default=default_metric_source,
    )
    if metric_source is None:
        return RegionBoxplotResult(
            None,
            None,
            0,
            "missing_input",
            "skip region boxplot: no configured metric table candidate is available",
        )
    if station_metadata is None:
        try:
            from spatial_vtk.io import load_output_table

            station_metadata = load_output_table("prepared_stations", cfg=cfg)
        except Exception:
            station_metadata = None
    return write_large_run_region_boxplot(
        metric_source,
        figure_dir=figure_dir,
        station_metadata=station_metadata,
        **kwargs,
    )


def write_large_run_region_boxplot_from_notebook_settings(
    outputs: Any,
    settings: Any,
    *,
    output_prefix: str = "additional_region_boxplot",
    geojson_path: str | Path | None = None,
    cfg: ConfigInput | None = None,
    annotate_if_missing: bool = False,
    overwrite: bool = False,
) -> RegionBoxplotResult:
    """Write a Step 6 region boxplot using notebook figure settings.

    Public notebooks use :func:`spatial_vtk.config.notebook_figure_settings`
    for figure switches and row-provenance controls. This wrapper owns the
    notebook-facing render gate and settings-to-keyword translation so the
    notebook only states which figure family it wants.
    """

    gate = settings.render_gate(
        [],
        disabled_message="Skipping region boxplot. Set SVTK_MAKE_FIGURES=1 to render it.",
    )
    if not gate.ready:
        status = "disabled" if not gate.figures_enabled else "missing_input"
        return RegionBoxplotResult(
            None,
            None,
            0,
            status,
            gate.message,
        )
    return write_large_run_region_boxplot_from_outputs(
        outputs,
        figure_dir=settings.figure_dir,
        geojson_path=geojson_path,
        cfg=cfg,
        metric=settings.metric,
        passband=settings.passband,
        component=settings.component,
        model=settings.model,
        value_col=settings.value_col,
        compare_to=settings.compare_to,
        max_rows=settings.sample_rows,
        output_prefix=output_prefix,
        **settings.sidecars.kwargs(),
        annotate_if_missing=annotate_if_missing,
        overwrite=overwrite,
        showfig=settings.showfig,
    )


_REGION_BOXPLOT_COLOR_COLUMNS = (
    "mapped_region_type",
    "geomorphology",
    "target_region_zone",
    "mapped_region",
    "station_region_class",
    "region_class",
    "geomorphic_region",
    "geomorphic_province",
)


def _merge_station_region_class_metadata(
    metric_rows: pd.DataFrame,
    station_metadata: pd.DataFrame | str | Path | None,
) -> pd.DataFrame:
    """Attach station-level region class columns used to color region boxplots."""

    if station_metadata is None or metric_rows.empty:
        return metric_rows
    try:
        stations = read_table(station_metadata) if isinstance(station_metadata, (str, Path)) else station_metadata.copy()
    except Exception:
        return metric_rows
    if stations is None or stations.empty:
        return metric_rows
    stations = _site_metadata_with_geomorphology(stations)
    class_cols = [column for column in _REGION_BOXPLOT_COLOR_COLUMNS if column in stations.columns]
    if not class_cols:
        return metric_rows
    key_pair = _station_metadata_key_pair(metric_rows, stations)
    if key_pair is None:
        return metric_rows
    left_key, right_key = key_pair
    out = metric_rows.copy()
    left_tmp = "__svtk_region_boxplot_station_key"
    out[left_tmp] = out[left_key].astype(str).str.strip()
    station_subset = stations[[right_key, *class_cols]].copy()
    station_subset[left_tmp] = station_subset[right_key].astype(str).str.strip()
    station_subset = station_subset.loc[station_subset[left_tmp].str.len() > 0].drop_duplicates(left_tmp)
    station_subset = station_subset.drop(columns=[right_key])
    rename = {column: f"__svtk_station_meta_{column}" for column in class_cols}
    station_subset = station_subset.rename(columns=rename)
    out = out.merge(station_subset, on=left_tmp, how="left")
    for column in class_cols:
        meta_col = rename[column]
        if meta_col not in out.columns:
            continue
        if column in out.columns:
            existing_text = out[column].astype(str).str.strip()
            missing = out[column].isna() | existing_text.eq("") | existing_text.str.casefold().isin(
                {"unknown", "unmapped", "undefined", "unclassified", "none", "null", "nan"}
            )
            out.loc[missing, column] = out.loc[missing, meta_col]
        else:
            out[column] = out[meta_col]
    return out.drop(columns=[left_tmp, *rename.values()], errors="ignore")


def _merge_geojson_region_class_metadata(
    plot_rows: pd.DataFrame,
    geojson_path: Path | None,
    *,
    region_col: str,
) -> pd.DataFrame:
    """Attach GeoJSON region classes by matching plotted region labels."""

    if geojson_path is None or not geojson_path.exists() or region_col not in plot_rows.columns:
        return plot_rows
    try:
        lookup = _geojson_region_type_lookup(geojson_path)
    except Exception:
        return plot_rows
    if not lookup:
        return plot_rows
    mapped = plot_rows[region_col].map(lambda value: lookup.get(_region_label_key(value), pd.NA))
    if "mapped_region_type" in plot_rows.columns:
        out = plot_rows.copy()
        existing_text = out["mapped_region_type"].astype(str).str.strip()
        missing = out["mapped_region_type"].isna() | existing_text.eq("") | existing_text.str.casefold().isin(
            {"unknown", "unmapped", "undefined", "unclassified", "none", "null", "nan"}
        )
        out.loc[missing, "mapped_region_type"] = mapped.loc[missing]
        return out
    out = plot_rows.copy()
    out["mapped_region_type"] = mapped
    return out


def _geojson_region_type_lookup(geojson_path: Path) -> dict[str, object]:
    """Return normalized GeoJSON region label to region-class mapping."""

    data = json.loads(geojson_path.read_text(encoding="utf-8"))
    features = data.get("features", []) if isinstance(data, Mapping) else []
    lookup: dict[str, object] = {}
    label_props = ("long_name", "short_name", "name", "region_name", "label", "mapped_region")
    class_props = ("region_type", "mapped_region_type", "geomorphology", "region_class", "class")
    for feature in features:
        properties = feature.get("properties", {}) if isinstance(feature, Mapping) else {}
        if not isinstance(properties, Mapping):
            continue
        class_value = next((properties[prop] for prop in class_props if prop in properties and _is_defined_geology_class(properties[prop])), None)
        if class_value is None:
            continue
        for prop in label_props:
            if prop in properties:
                key = _region_label_key(properties[prop])
                if key:
                    lookup[key] = class_value
    return lookup


def _region_label_key(value: object) -> str:
    """Normalize region labels from figures and GeoJSON properties for matching."""

    return " ".join(str(value).replace("_", " ").strip().casefold().split())


def _station_metadata_key_pair(metric_rows: pd.DataFrame, stations: pd.DataFrame) -> tuple[str, str] | None:
    """Return metric/station metadata columns that identify the same station."""

    candidates = (
        ("station", "station"),
        ("station", "station_name"),
        ("station", "name"),
        ("station_name", "station"),
        ("station_name", "station_name"),
        ("station_id", "station"),
        ("station_code", "station"),
    )
    for left_key, right_key in candidates:
        if left_key in metric_rows.columns and right_key in stations.columns:
            return left_key, right_key
    return None


def _region_boxplot_color_column(plot_rows: pd.DataFrame) -> str | None:
    """Choose the best station region-class column for coloring the region boxplot."""

    for column in _REGION_BOXPLOT_COLOR_COLUMNS:
        if column not in plot_rows.columns:
            continue
        values = plot_rows[column].dropna().astype(str).str.strip()
        if values.map(_is_defined_geology_class).any():
            return column
    return None


def _group_path(outputs: Any, name: str) -> Path | None:
    """Return one path from an output group-like object."""

    if hasattr(outputs, name):
        value = getattr(outputs, name)
        return None if value is None else Path(value)
    paths = getattr(outputs, "paths", None)
    if isinstance(paths, Mapping) and name in paths:
        value = paths[name]
        return None if value is None else Path(value)
    return None


def _resolve_region_figure_output(
    outputs: Any,
    path_name: str,
    output_key: str,
    *,
    cfg: ConfigInput | None,
    fallback_dir: Path,
    prefer_fallback_dir: bool = False,
) -> Path:
    """Resolve one region figure path from an output group or config."""

    if prefer_fallback_dir:
        return fallback_dir / f"{output_key}.png"
    group_paths = getattr(outputs, "paths", {})
    if isinstance(group_paths, Mapping) and path_name in group_paths:
        return Path(group_paths[path_name]).expanduser()
    try:
        return resolve_output_path(output_key, kind="figure", cfg=cfg, create_parent=True)
    except Exception:
        return fallback_dir / f"{output_key}.png"


def _load_group_table_by_path(
    outputs: Any,
    path_name: str,
    output_key: str,
    *,
    cfg: ConfigInput | None,
) -> pd.DataFrame:
    """Load a table from an output group's explicit path before key fallback."""

    table_path = getattr(outputs, "paths", {}).get(path_name)
    if table_path is not None and Path(table_path).exists():
        return read_table(table_path)
    return outputs.load_table(output_key, cfg=cfg)


def _read_if_exists(
    path: str | Path | None,
    *,
    columns: Sequence[str] | None = None,
) -> pd.DataFrame | None:
    """Read one table path if it exists."""

    if path is None:
        return None
    input_path = Path(path)
    if not input_path.exists():
        return None
    selected = _existing_columns(input_path, columns)
    if selected is None:
        return read_table(input_path)
    if input_path.suffix.lower() in {".parquet", ".pq"}:
        return read_table(input_path, columns=selected)
    wanted = set(selected)
    return read_table(input_path, usecols=lambda column: column in wanted)


def _tag_spatial_table(df: pd.DataFrame | None, *, key: str) -> pd.DataFrame | None:
    """Attach a stable table-owner hint to a loaded Step 4 dataframe."""

    if df is not None:
        df.attrs[SPATIAL_TABLE_KEY_ATTR] = str(key)
        if key == "event_centered_residuals":
            df.attrs[SPATIAL_CONTEXT_ATTR] = "event"
            _tag_spatial_sidecar_roles(df, context_name="event", aggregated=False)
        elif key == "metric_field":
            df.attrs[SPATIAL_CONTEXT_ATTR] = "metric"
            _tag_spatial_sidecar_roles(df, context_name="metric", aggregated=False)
    return df


def _tag_spatial_sidecar_roles(
    df: pd.DataFrame | None,
    *,
    context: MetricFigureContext | None = None,
    context_name: str | None = None,
    aggregated: bool,
) -> pd.DataFrame | None:
    """Attach sidecar role metadata for Step 4 spatial figure rows."""

    if df is None:
        return None
    resolved_context = str(context_name or "").strip().lower()
    if not resolved_context and context is not None:
        table_key = getattr(df, "attrs", {}).get(SPATIAL_TABLE_KEY_ATTR)
        existing_context = getattr(df, "attrs", {}).get(SPATIAL_CONTEXT_ATTR)
        if existing_context:
            resolved_context = str(existing_context).strip().lower()
        elif table_key == "event_centered_residuals":
            resolved_context = "event"
        elif table_key == "metric_field":
            resolved_context = "metric"
    if resolved_context == "event":
        df.attrs[SIDECAR_TABLE_ROLE_ATTR] = "event-centered residuals; event means removed"
        df.attrs[SIDECAR_EVENT_CENTERED_ATTR] = True
        if aggregated:
            df.attrs[SIDECAR_PLOT_ROWS_ROLE_ATTR] = "post_aggregation_station_summary_from_event_centered_residuals"
            df.attrs[SIDECAR_SOURCE_ROWS_ROLE_ATTR] = "pre_aggregation_event_centered_residual_rows"
        else:
            df.attrs[SIDECAR_PLOT_ROWS_ROLE_ATTR] = "event_centered_residual_rows"
            df.attrs[SIDECAR_SOURCE_ROWS_ROLE_ATTR] = "event_centered_residual_rows"
    elif resolved_context == "metric":
        df.attrs[SIDECAR_TABLE_ROLE_ATTR] = "metric field rows; event means retained"
        df.attrs[SIDECAR_EVENT_CENTERED_ATTR] = False
        if aggregated:
            df.attrs[SIDECAR_PLOT_ROWS_ROLE_ATTR] = "post_aggregation_station_summary_from_metric_field"
            df.attrs[SIDECAR_SOURCE_ROWS_ROLE_ATTR] = "pre_aggregation_metric_field_rows"
        else:
            df.attrs[SIDECAR_PLOT_ROWS_ROLE_ATTR] = "metric_field_rows"
            df.attrs[SIDECAR_SOURCE_ROWS_ROLE_ATTR] = "metric_field_rows"
    return df


def _columns_for_spatial_table(key: str) -> tuple[str, ...] | None:
    """Return column projection for large spatial event-row tables."""

    if key in SPATIAL_EVENT_ROW_TABLE_KEYS:
        return SPATIAL_EVENT_ROW_COLUMNS
    return None


def _spatial_table_role(key: str) -> str:
    """Return a notebook-facing role label for one spatial output table."""

    roles = {
        "metric_field": "event-station metric field used for station/path spatial figures",
        "event_centered_residuals": "event-centered residuals used for event-normalized figures",
        "station_bias": "station bias summary table",
        "distance_bin_correlations": "distance-bin correlation summary table",
        "clusters": "cluster assignments",
        "pca_station_scores": "station PCA scores",
        "path_summary": "path-level residual summary table",
        "pca_explained_variance": "PCA explained variance",
        "pca_feature_loadings": "PCA feature loadings",
        "cluster_solution_scores": "cluster solution scores",
        "cluster_feature_summary": "cluster feature summary",
        "block_holdout_predictions": "spatial block-holdout predictions",
        "corridors": "boundary corridor records",
        "redcap_clusters": "REDCAP spatial clusters",
        "pattern_similarity_station_anomalies": "pattern-similarity station anomalies",
        "morans_i": "Moran's I spatial autocorrelation",
        "geology_contrasts": "geology contrast summary table",
    }
    return roles.get(key, key.replace("_", " "))


def _spatial_table_value_col(
    key: str,
    table: pd.DataFrame | None,
    context: SpatialFigureContext,
) -> str | None:
    """Return the primary plotted value column for one loaded spatial table."""

    if key == "metric_field":
        return context.metric_value_col
    if key == "event_centered_residuals":
        return context.event_value_col
    return _first_existing(
        table,
        [
            "log2_residual",
            "field_value",
            "field_centered",
            "mean_centered",
            "event_centered_residual",
            "residual",
            "median_residual",
            "mean_pair_correlation",
            "semivariance",
            "prediction_error",
            "score",
            "explained_variance_ratio",
        ],
    )


def _spatial_table_value_role(key: str) -> str | None:
    """Return a notebook-facing label for what one table value represents."""

    roles = {
        "metric_field": "raw event-station residuals; event means retained",
        "event_centered_residuals": "event-centered residuals; event means removed",
        "station_bias": "station summaries of event-centered residuals",
        "path_summary": "path-binned residual summary",
        "distance_bin_correlations": "distance-binned residual correlation summary",
        "morans_i": "spatial autocorrelation statistic",
        "geology_contrasts": "event-centered residual contrast by geologic group",
    }
    return roles.get(key)


def _spatial_context_table_status(*, loaded: bool, exists: bool | None) -> str:
    """Return a compact status for one spatial figure input table."""

    if loaded:
        return "ready"
    if exists is True:
        return "available_not_loaded"
    if exists is False:
        return "missing"
    return "not_configured"


def _existing_columns(path: Path, columns: Sequence[str] | None) -> list[str] | None:
    """Return requested columns present in one table."""

    if columns is None:
        return None
    requested = list(dict.fromkeys(str(column) for column in columns if str(column).strip()))
    if not requested:
        return []
    available = set(_table_columns(path))
    return [column for column in requested if column in available]


def _table_columns(path: Path) -> list[str]:
    """Return table columns without loading row data."""

    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq", ".csv"}:
        return table_columns(path)
    raise ValueError(f"Unsupported table format for {path}. Use Parquet or CSV.")


def _first_existing(df: pd.DataFrame | None, candidates: list[str]) -> str | None:
    """Return the first candidate column present in a dataframe."""

    return first_existing(df, candidates) if df is not None else None


def _region_boxplot_name(
    prefix: str,
    *,
    metric: str,
    passband: str | Sequence[str],
    component: str | Sequence[str] | None,
    model: str | Sequence[str] | None,
    value_col: str,
) -> str:
    """Return a stable filename for a region boxplot."""

    parts = [
        prefix,
        slugify(metric),
        slugify(_label_for_slug(passband) or "all-passbands"),
        slugify(_label_for_slug(component) or "all-components"),
        slugify(_label_for_slug(model) or "all-models"),
        slugify(value_col),
    ]
    return "__".join(parts) + ".png"


def _write_region_boxplot_sidecar(
    figure_path: Path,
    data: pd.DataFrame,
    *,
    write_sidecar: bool,
    sidecar_rows: int | None,
    sidecar_dir: str | Path | None,
    metric: str,
    passband: str | Sequence[str],
    component: str | Sequence[str] | None,
    model: str | Sequence[str] | None,
    value_col: str,
    compare_to: str | Sequence[str] | None,
) -> Path | None:
    """Write the normalized rows used by one region boxplot."""

    if not write_sidecar:
        return None
    from spatial_vtk.spatial.plot.metrics import _categorical_metric_plot_data

    plot_df, category_col, plot_value_col, dep_labels, resolved_value_col, _subset_label = _categorical_metric_plot_data(
        data,
        dep=metric,
        indep="station_region",
        value_col=value_col,
        passband=passband,
        model=model,
        component=component,
        station=None,
        event_id=None,
        filters=None,
    )
    color_col = _region_boxplot_color_column(plot_df)
    result = write_figure_row_sidecar(
        figure_path,
        plot_df,
        enabled=True,
        sidecar_rows=sidecar_rows,
        sidecar_dir=sidecar_dir,
        metadata={
            "metric": metric,
            "metric_labels": dep_labels,
            "passband": _label_for_slug(passband),
            "component": _label_for_slug(component),
            "model": _label_for_slug(model),
            "category_col": category_col,
            "value_col": value_col,
            "resolved_value_col": resolved_value_col,
            "plot_value_col": plot_value_col,
            "color_col": color_col,
            "compare_to": compare_to,
        },
    )
    return None if result is None else result.sidecar_path


def _region_boxplot_comparison_table(
    data: pd.DataFrame,
    *,
    metric: str,
    passband: str | Sequence[str],
    component: str | Sequence[str] | None,
    model: str | Sequence[str] | None,
    value_col: str,
    compare_to: str | Sequence[str] | None,
) -> pd.DataFrame:
    """Return the statistical comparison table for one large-run region boxplot."""

    try:
        from spatial_vtk.spatial.plot.metrics import build_categorical_comparison_table

        return build_categorical_comparison_table(
            data,
            dep=metric,
            indep="station_region",
            value_col=value_col,
            passband=passband,
            model=model,
            component=component,
            compare_to=compare_to,
        )
    except Exception:
        return pd.DataFrame(columns=["comparison", "effect", "ci95", "p", "n"])


def _label_for_slug(value: object) -> str | None:
    """Return a compact text label for filename dimensions."""

    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, Sequence):
        labels = [str(item) for item in value if str(item).strip()]
        return "_".join(labels) if labels else None
    return str(value)


def _as_selection_list(value: object) -> list[str]:
    """Normalize one optional scalar/list selection to strings."""

    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, Sequence):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _layer_pca_summary_rows(
    *,
    station_scores: pd.DataFrame,
    explained_variance: pd.DataFrame,
    feature_loadings: pd.DataFrame,
    mode: str,
    score_col: str,
    top_loadings: int = 10,
) -> pd.DataFrame:
    """Return layered source rows for an existing PCA summary figure."""

    frames: list[pd.DataFrame] = []
    if not station_scores.empty:
        score_rows = station_scores.copy()
        if score_col in score_rows.columns:
            score_rows = score_rows.loc[pd.to_numeric(score_rows[score_col], errors="coerce").notna()].copy()
        lon_col = _first_existing(score_rows, ["lon", "sta_lon", "station_lon", "station_longitude"])
        lat_col = _first_existing(score_rows, ["lat", "sta_lat", "station_lat", "station_latitude"])
        if lon_col and lat_col:
            score_rows = score_rows.dropna(subset=[lon_col, lat_col])
        if not score_rows.empty:
            frames.append(score_rows.assign(_figure_layer="station_score"))
    if not explained_variance.empty:
        if "mode_index" in explained_variance.columns:
            explained_rows = explained_variance.sort_values("mode_index").copy()
        else:
            explained_rows = explained_variance.copy()
        frames.append(explained_rows.assign(_figure_layer="explained_variance"))
    if not feature_loadings.empty:
        loading_rows = feature_loadings.copy()
        if "mode" in loading_rows.columns:
            loading_rows = loading_rows.loc[loading_rows["mode"].astype(str).eq(str(mode))].copy()
        if "absolute_loading" in loading_rows.columns:
            loading_rows = loading_rows.sort_values("absolute_loading", ascending=False).head(int(top_loadings)).copy()
        if "loading" in loading_rows.columns:
            loading_rows = loading_rows.sort_values("loading", ascending=True).copy()
        if not loading_rows.empty:
            frames.append(loading_rows.assign(_figure_layer="feature_loading"))
    if frames:
        return pd.concat(frames, ignore_index=True, sort=False)
    return station_scores.iloc[0:0].copy().assign(_figure_layer=pd.Series(dtype="object"))


def _spatial_overview_plot_functions() -> dict[str, Callable[..., Any]]:
    """Load plotting functions used by the large-run spatial overview helper."""

    from spatial_vtk.spatial.plot.correlation import (
        plot_block_holdout_scatter,
        plot_cluster_feature_heatmap,
        plot_cluster_solution_scores,
        plot_correlogram,
        plot_distance_correlation_by_metric,
        plot_directional_correlogram,
        plot_pattern_similarity,
        plot_semivariogram,
    )
    from spatial_vtk.spatial.plot.metrics import (
        plot_geology_contrast,
        plot_path_bin_summary,
        plot_residual_correlation,
    )
    from spatial_vtk.spatial.plot.pca import plot_pca_explained_variance, plot_pca_feature_loadings

    return {
        "plot_block_holdout_scatter": plot_block_holdout_scatter,
        "plot_cluster_feature_heatmap": plot_cluster_feature_heatmap,
        "plot_cluster_solution_scores": plot_cluster_solution_scores,
        "plot_correlogram": plot_correlogram,
        "plot_distance_correlation_by_metric": plot_distance_correlation_by_metric,
        "plot_directional_correlogram": plot_directional_correlogram,
        "plot_geology_contrast": plot_geology_contrast,
        "plot_path_bin_summary": plot_path_bin_summary,
        "plot_pattern_similarity": plot_pattern_similarity,
        "plot_pca_explained_variance": plot_pca_explained_variance,
        "plot_pca_feature_loadings": plot_pca_feature_loadings,
        "plot_residual_correlation": plot_residual_correlation,
        "plot_semivariogram": plot_semivariogram,
    }


__all__ = [
    "RegionBoxplotResult",
    "RegionFigureResult",
    "SPATIAL_FIGURE_TABLE_KEYS",
    "StandardAdditionalPlottingFigureResult",
    "StandardAdditionalPlottingInputResult",
    "StandardAdditionalPlottingOutputStatusResult",
    "StandardGeoJSONCorridorFigureResult",
    "StandardGeoJSONFigureResult",
    "StandardGeoJSONPlottingInputResult",
    "StandardGeoJSONWorkflowOutputStatusResult",
    "SpatialSummaryFigureResult",
    "SpatialFigureSuiteResult",
    "SpatialFigureContext",
    "StandardSpatialDiagnosticFigureResult",
    "StandardSpatialMapFigureResult",
    "load_standard_additional_plotting_output_status",
    "load_standard_additional_plotting_inputs",
    "load_standard_geojson_workflow_output_status",
    "load_standard_geojson_plotting_inputs",
    "prepare_spatial_figure_context",
    "prepare_spatial_figure_context_from_notebook_settings",
    "write_standard_additional_plotting_figures",
    "write_step06_model_comparison_figures",
    "write_standard_geojson_corridor_figures",
    "write_standard_spatial_diagnostic_figures",
    "write_standard_geojson_region_figures",
    "write_standard_spatial_map_figures",
    "write_large_run_geojson_region_figures_from_outputs",
    "write_large_run_geojson_region_figures_from_notebook_settings",
    "write_large_run_region_boxplot",
    "write_large_run_region_boxplot_from_outputs",
    "write_large_run_region_boxplot_from_notebook_settings",
    "write_large_run_spatial_summary_figures_from_outputs",
    "write_large_run_spatial_figure_suite_from_notebook_settings",
]
