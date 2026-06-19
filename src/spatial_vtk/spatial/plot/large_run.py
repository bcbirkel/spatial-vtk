"""Large-run spatial plotting orchestration helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import matplotlib.pyplot as plt
import pandas as pd

from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.config.runtime import SpatialVTKConfig
from spatial_vtk.io import load_output_table, read_bounded_table, read_table, slugify
from spatial_vtk.metrics.plot.large_run import (
    MetricFigureContext,
    first_existing,
)
from spatial_vtk.spatial.calculate import add_geojson_metadata_to_metrics
from spatial_vtk.spatial.plot.metrics import _categorical_metric_plot_data, boxplot
from spatial_vtk.visualize.figure_sidecars import write_figure_row_sidecar


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

    @classmethod
    def from_config(
        cls,
        *,
        figure_dir: str | Path,
        make_figures: bool,
        cfg: SpatialVTKConfig | None = None,
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
            ["log2_residual", "mean_centered", "field_centered", "event_centered_residual", "residual"],
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
        )
        try:
            site_metadata = load_output_table("prepared_stations", cfg=cfg)
        except Exception as exc:
            site_metadata = None
            if make_figures:
                print(f"Station metadata unavailable for geology contrast plots: {exc}")
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
        )
        if make_figures:
            print(f"Rendering spatial figures into {output_dir}")
            print(
                f"metric_value_col={context.metric_value_col} "
                f"event_value_col={context.event_value_col} "
                f"default_passband={default_passband} "
                f"default_components={default_components} "
                f"default_model={default_model}"
            )
        return context

    def status_frame(self) -> pd.DataFrame:
        """Return loaded table status for this spatial figure context.

        The frame reports the configured Step 4 table paths, whether each table
        exists and was loaded, and the loaded row/column counts. It is safe to
        display in notebooks because it summarizes tables already loaded by the
        context and does not read additional large files.
        """

        rows: list[dict[str, Any]] = []
        for key in SPATIAL_FIGURE_TABLE_KEYS:
            path = self.paths.get(key)
            resolved_path = None if path is None else str(path)
            table = self.tables.get(key)
            loaded = table is not None
            rows.append(
                {
                    "name": key,
                    "role": _spatial_table_role(key),
                    "resolved_path": resolved_path,
                    "path": resolved_path,
                    "exists": bool(path.exists()) if path is not None else None,
                    "loaded": loaded,
                    "row_count": int(len(table)) if loaded else 0,
                    "column_count": int(len(table.columns)) if loaded else 0,
                    "value_col": _spatial_table_value_col(key, table, self),
                }
            )
        station_table = self.site_metadata
        rows.append(
            {
                "name": "prepared_stations",
                "role": "site metadata for geology and station diagnostics",
                "resolved_path": None,
                "path": None,
                "exists": None,
                "loaded": station_table is not None,
                "row_count": int(len(station_table)) if station_table is not None else 0,
                "column_count": int(len(station_table.columns)) if station_table is not None else 0,
                "value_col": None,
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
            yield tagged

    def write_spatial_plot(
        self,
        base: str,
        item: dict[str, Any],
        func: Callable[..., Any],
        df: pd.DataFrame | None = None,
        source_df: pd.DataFrame | None = None,
        required: tuple[str, ...] | list[str | None] = (),
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
            "spatial_azimuthal_residuals": "Event-Centered Azimuthal Residuals",
            "spatial_polar_residuals": "Event-Centered Polar Residuals",
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
    ) -> list[Path]:
        """Write station-level spatial metric maps for configured target metrics."""

        resolved_value_col = value_col or self.metric_value_col
        outputs: list[Path] = []
        if not self._can_render_metric_figures("spatial_station_metric_map", resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            self.metric_field,
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            if item["key"] == "psa" and self.period_col in item["df"].columns:
                station_period_df = self.station_period_summary_for_item(item, resolved_value_col)
                output = self.write_spatial_plot(
                    "spatial_station_metric_map",
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
                    "spatial_station_metric_map",
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
    ) -> list[Path]:
        """Write station-interpolated residual grid maps for target metrics."""

        resolved_value_col = value_col or self.metric_value_col
        outputs: list[Path] = []
        if not self._can_render_metric_figures("spatial_residual_grid", resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            self.metric_field,
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            if item["key"] == "psa":
                output = self.write_spatial_period_sheet(
                    "spatial_residual_grid",
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
                    "spatial_residual_grid",
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
    ) -> list[Path]:
        """Write faceted station maps split by model for target metrics."""

        resolved_value_col = value_col or self.metric_value_col
        outputs: list[Path] = []
        if not self._can_render_metric_figures("spatial_metric_by_model_map", resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            self.metric_field,
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            if item["key"] == "psa":
                output = self.write_spatial_period_sheet(
                    "spatial_metric_by_model_map",
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
                    "spatial_metric_by_model_map",
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
    ) -> list[Path]:
        """Write event residual maps for target metric rows."""

        resolved_value_col = value_col or self.metric_value_col
        outputs: list[Path] = []
        if not self._can_render_metric_figures("spatial_event_residual_map", resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            self.metric_field,
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            writer = self.write_spatial_period_sheet if item["key"] == "psa" else self.write_spatial_plot
            output = writer(
                "spatial_event_residual_map",
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
            print(f"Skipping {label}. Enable spatial figures to render it.")
            return False
        if self.metric_field is None or self.metric_field.empty:
            print(f"Skipping {label}: metric_field table missing or empty.")
            return False
        if not value_col:
            print(f"Skipping {label}: no metric value column is available.")
            return False
        return True

    def _can_render_event_figures(self, label: str, value_col: str | None) -> bool:
        """Return whether event-centered figures can render, printing a bounded reason."""

        if not self.make_figures:
            print(f"Skipping {label}. Enable spatial figures to render it.")
            return False
        if self.event_centered is None or self.event_centered.empty:
            print(f"Skipping {label}: event_centered_residuals table missing or empty.")
            return False
        if not value_col:
            print(f"Skipping {label}: no event-centered value column is available.")
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
        return context.station_summary_for_map(df, value_col=value_col, extra_group_cols=extra_group_cols)

    def station_period_summary_for_map(
        self,
        df: pd.DataFrame,
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate PSA spatial rows to one plotted value per station and oscillator period."""

        context = self._context_for(df) or self.metric_context
        return context.station_period_summary_for_map(df, value_col=value_col, extra_group_cols=extra_group_cols)

    def item_source_rows(self, item: dict[str, Any]) -> pd.DataFrame:
        """Return the spatial rows represented by one figure item."""

        context = self._context_for_item(item) or self.metric_context
        return context.item_source_rows(item)

    def station_summary_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate one figure item's rows to one plotted value per station."""

        context = self._context_for_item(item) or self.metric_context
        return context.station_summary_for_item(item, value_col=value_col, extra_group_cols=extra_group_cols)

    def station_period_summary_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate one PSA figure item's rows to one plotted value per station and period."""

        context = self._context_for_item(item) or self.metric_context
        return context.station_period_summary_for_item(item, value_col=value_col, extra_group_cols=extra_group_cols)

    def station_grid_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate one figure item and expose station coordinates as lon/lat."""

        context = self._context_for_item(item) or self.metric_context
        return context.station_grid_for_item(item, value_col=value_col, extra_group_cols=extra_group_cols)

    def station_period_grid_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate one PSA figure item by station/period and expose lon/lat columns."""

        context = self._context_for_item(item) or self.metric_context
        return context.station_period_grid_for_item(item, value_col=value_col, extra_group_cols=extra_group_cols)

    def station_model_summary_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
    ) -> pd.DataFrame:
        """Aggregate one figure item by station and model."""

        context = self._context_for_item(item) or self.metric_context
        return context.station_model_summary_for_item(item, value_col=value_col)

    def station_model_grid_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
    ) -> pd.DataFrame:
        """Aggregate one figure item by station/model and expose lon/lat columns."""

        context = self._context_for_item(item) or self.metric_context
        return context.station_model_grid_for_item(item, value_col=value_col)

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
            print("skip spatial_pca_summary: metric_field table missing or empty")
            return []
        if station_scores is None or station_scores.empty:
            print("skip spatial_pca_summary: pca_station_scores table missing or empty")
            return []
        if explained_variance is None or explained_variance.empty:
            print("skip spatial_pca_summary: pca_explained_variance table missing or empty")
            return []
        if feature_loadings is None or feature_loadings.empty:
            print("skip spatial_pca_summary: pca_feature_loadings table missing or empty")
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
                print(f"skip spatial_pca_summary {item['label']}: no PCA station score rows")
                continue
            if explained_rows is None or explained_rows.empty:
                print(f"skip spatial_pca_summary {item['label']}: no PCA explained-variance rows")
                continue
            if loading_rows is None or loading_rows.empty:
                print(f"skip spatial_pca_summary {item['label']}: no PCA feature-loading rows")
                continue
            if resolved_score_col not in score_rows.columns:
                print(f"skip spatial_pca_summary {item['label']}: missing score column {resolved_score_col!r}")
                continue

            output = self.figure_dir / f"{self.metric_context.figure_name('spatial_pca_summary', item, resolved_score_col)}.png"
            if output.exists() and not self.overwrite:
                print(f"skip {output.name}: exists")
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
                plt.close("all")
                print(f"wrote {output}")
                outputs.append(output)
            except Exception as exc:
                plt.close("all")
                print(f"skip {output.name}: {type(exc).__name__}: {exc}")
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
            print("skip spatial_pattern_similarity: pattern_similarity_station_anomalies table missing or empty")
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
            print("skip spatial_pattern_similarity: no rows match the requested passband/component/model filters")
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
        geology_contrasts = self.table("geology_contrasts")
        if event_centered is None or event_centered.empty:
            print("skip spatial_geology_contrast: event-centered residual table missing or empty")
            return outputs
        if geology_value_col is None or geology_value_col not in event_centered.columns:
            print(f"skip spatial_geology_contrast: value column unavailable ({geology_value_col!r})")
            return outputs
        if geology_contrasts is None or geology_contrasts.empty:
            print("skip spatial_geology_contrast: geology_contrasts table missing or empty")
            return outputs
        for item in self.iter_metric_frames(
            event_centered,
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            contrast_for_item = self.filter_like_item(geology_contrasts, item, include_period=False)
            output = self.write_spatial_plot(
                "spatial_geology_contrast",
                item,
                func,
                required=["station", geology_value_col],
                value_col=geology_value_col,
                forward_value_col=True,
                showfig=showfig,
                station_metadata=self.site_metadata,
                contrast_df=contrast_for_item,
                title=f"{item['label']} Residuals by Geology Class",
                robust_axis_percentile=robust_axis_percentile,
            )
            if output is not None:
                outputs.append(output)
        return outputs

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


@dataclass(frozen=True)
class RegionBoxplotResult:
    """Result from writing a large-run GeoJSON region boxplot."""

    figure_path: Path | None
    sidecar_path: Path | None
    rows: int
    status: str
    message: str


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
        rows = [
            {
                "artifact": "geojson_overview",
                "status": self.geojson_status,
                "resolved_path": geojson_path,
                "path": geojson_path,
                "message": self._message_for("geojson_overview"),
            },
            {
                "artifact": "corridor_map",
                "status": self.corridor_status,
                "resolved_path": corridor_path,
                "path": corridor_path,
                "message": self._message_for("corridor_map"),
            },
            {
                "artifact": "region_boxplot",
                "status": self.boxplot_result.status,
                "resolved_path": boxplot_path,
                "path": boxplot_path,
                "message": self.boxplot_result.message,
            },
        ]
        return pd.DataFrame(rows)

    def _message_for(self, artifact: str) -> str | None:
        """Return the first message tagged for one artifact."""

        prefix = f"{artifact}: "
        for message in self.messages:
            if message.startswith(prefix):
                return message[len(prefix):]
        return None


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

        return pd.DataFrame(
            self.rows,
            columns=[
                "artifact",
                "status",
                "row_count",
                "figure_path",
                "message",
            ],
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

        return pd.DataFrame(
            self.rows,
            columns=[
                "artifact",
                "status",
                "row_count",
                "figure_path",
                "message",
            ],
        )

    def boundary_crossing_frame(self) -> pd.DataFrame:
        """Return a bounded preview of paths used by the record section."""

        return self.boundary_crossing_preview.copy()

    def outward_event_frame(self) -> pd.DataFrame:
        """Return events selected by the outward corridor."""

        return self.outward_event_preview.copy()


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

        geojson_path = str(self.geojson_path)
        rows = [
            {
                "artifact": "region_geojson",
                "status": "ready" if self.geojson_path.exists() else "missing",
                "rows": None,
                "resolved_path": geojson_path,
                "path": geojson_path,
            },
            {"artifact": "metrics", "status": "loaded", "rows": len(self.metrics), "resolved_path": None, "path": None},
            {"artifact": "stations", "status": "loaded", "rows": len(self.stations), "resolved_path": None, "path": None},
            {"artifact": "events", "status": "loaded", "rows": len(self.events), "resolved_path": None, "path": None},
            {"artifact": "event_stations", "status": "loaded", "rows": len(self.event_stations), "resolved_path": None, "path": None},
            {
                "artifact": "comparison_eligible",
                "status": "loaded",
                "rows": len(self.comparison_eligible),
                "resolved_path": None,
                "path": None,
            },
        ]
        return pd.DataFrame(rows, columns=["artifact", "status", "rows", "resolved_path", "path"])


@dataclass(frozen=True)
class StandardGeoJSONWorkflowOutputStatusResult:
    """Configured Step 5 output status and bounded preview helpers."""

    outputs: Any
    cfg: Any | None = None

    def status_frame(self) -> pd.DataFrame:
        """Return configured Step 5 output path status."""

        return self.outputs.status_frame()

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

        return pd.DataFrame(
            self.rows,
            columns=[
                "artifact",
                "status",
                "row_count",
                "figure_path",
                "message",
            ],
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

        rows = [
            {"table": "metrics", "rows": len(self.metrics)},
            {"table": "event_stations", "rows": len(self.event_stations)},
            {"table": "events", "rows": len(self.events)},
            {"table": "comparison_eligible", "rows": len(self.comparison_eligible)},
        ]
        return pd.DataFrame(rows, columns=["table", "rows"])


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

        return pd.DataFrame(
            [
                {
                    "artifact": "station_bias_map",
                    "status": self.status,
                    "row_count": self.row_count,
                    "input_path": None if self.station_bias_path is None else str(self.station_bias_path),
                    "figure_path": None if self.station_bias_figure_path is None else str(self.station_bias_figure_path),
                    "message": self.message,
                }
            ]
        )


@dataclass(frozen=True)
class StandardSpatialMapFigureResult:
    """Result from writing standard Step 4 spatial map figures."""

    rows: tuple[dict[str, Any], ...]

    def status_frame(self) -> pd.DataFrame:
        """Return a compact notebook status table for written spatial figures."""

        return pd.DataFrame(
            self.rows,
            columns=[
                "artifact",
                "metric",
                "status",
                "row_count",
                "figure_path",
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

        return pd.DataFrame(
            self.rows,
            columns=[
                "artifact",
                "metric",
                "status",
                "row_count",
                "figure_path",
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

    def status_frame(self) -> pd.DataFrame:
        """Return one row per spatial figure family rendered or skipped."""

        return pd.DataFrame(
            self.rows,
            columns=[
                "artifact",
                "status",
                "figure_count",
                "figure_paths",
                "first_figure_path",
                "figure_paths_preview",
                "message",
            ],
        )


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
    context_kwargs.update(overrides)
    return prepare_spatial_figure_context(
        figure_dir=settings.figure_dir,
        overwrite=overwrite,
        **context_kwargs,
    )


def _spatial_suite_status_row(artifact: str, outputs: Sequence[Path]) -> dict[str, Any]:
    """Return one notebook status row for a spatial figure family."""

    paths = [Path(path) for path in outputs]
    preview = ", ".join(str(path) for path in paths[:3])
    if len(paths) > 3:
        preview += f", ... (+{len(paths) - 3} more)"
    return {
        "artifact": artifact,
        "status": "written" if paths else "skipped",
        "figure_count": int(len(paths)),
        "figure_paths": [str(path) for path in paths],
        "first_figure_path": None if not paths else str(paths[0]),
        "figure_paths_preview": preview,
        "message": "" if paths else "No figures were written; check context status and missing-table messages above.",
    }


def write_large_run_spatial_figure_suite_from_notebook_settings(
    settings: Any,
    *,
    overwrite: bool = False,
    station_metric_map_func: Callable[..., Any] | None = None,
    station_metric_map_by_period_func: Callable[..., Any] | None = None,
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
            plot_station_metric_map,
            plot_station_metric_map_by_period,
        )

        station_metric_map_func = station_metric_map_func or plot_station_metric_map
        station_metric_map_by_period_func = station_metric_map_by_period_func or plot_station_metric_map_by_period
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
        overwrite=overwrite,
        include_station_aggregation=True,
    )
    rows: list[dict[str, Any]] = []
    if not settings.make_figures:
        rows.append(
            {
                "artifact": "spatial_figure_suite",
                "status": "skipped",
                "figure_count": 0,
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
            "residual_grid_maps",
            context.write_residual_grid_maps(
                residual_grid_func,
                **metric_kwargs,
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
            "event_residual_maps",
            context.write_event_residual_maps(
                event_residual_map_func,
                **metric_kwargs,
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
    cfg: SpatialVTKConfig | None = None,
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
        plt.close("all")
    except Exception as exc:
        plt.close("all")
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
            plt.close("all")
            rows.append(
                {
                    "artifact": "station_bias_map",
                    "metric": metric_name,
                    "status": "wrote",
                    "row_count": len(station_df),
                    "figure_path": str(station_path),
                    "message": f"wrote {station_path}",
                }
            )
        except Exception as exc:
            plt.close("all")
            rows.append(
                {
                    "artifact": "station_bias_map",
                    "metric": metric_name,
                    "status": "plot_failed",
                    "row_count": len(station_df),
                    "figure_path": str(station_path),
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
            plt.close("all")
            rows.append(
                {
                    "artifact": "residual_grid_map",
                    "metric": metric_name,
                    "status": "wrote",
                    "row_count": len(centered_df),
                    "figure_path": str(grid_path),
                    "message": f"wrote {grid_path}",
                }
            )
        except Exception as exc:
            plt.close("all")
            rows.append(
                {
                    "artifact": "residual_grid_map",
                    "metric": metric_name,
                    "status": "plot_failed",
                    "row_count": len(centered_df),
                    "figure_path": str(grid_path),
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
    cfg: SpatialVTKConfig | None = None,
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
        plt.close("all")
        status = "wrote"
        message = f"wrote {figure_path}"
    except Exception as exc:
        plt.close("all")
        status = "plot_failed"
        message = f"{type(exc).__name__}: {exc}"
    return {
        "artifact": artifact,
        "metric": metric,
        "status": status,
        "row_count": len(frame),
        "figure_path": str(figure_path),
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
        plt.close("all")
        status = "wrote"
        message = f"wrote {figure_path}"
    except Exception as exc:
        plt.close("all")
        status = "plot_failed"
        message = f"{type(exc).__name__}: {exc}"
    return {
        "artifact": artifact,
        "status": status,
        "row_count": len(frame),
        "figure_path": str(figure_path),
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

    Parameters
    ----------
    cfg
        Active Spatial-VTK config. When omitted, the active config is used by
        the underlying IO helpers.
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
    metrics = metrics_outputs.load_table("metrics_long", cfg=cfg)
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
    passbands: Sequence[str] | str | None = ("1-2 sec", "2-3 sec"),
    component: str | None = "Z",
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
        Active Spatial-VTK config. When omitted, the active config is used by
        the underlying IO helpers.
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
    passbands: Sequence[str] | str | None = ("1-2 sec", "2-3 sec"),
    component: str | None = "Z",
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
    metric_summary = metric_summary_func(metrics, comparison_eligible=comparison_eligible)
    region_metrics = geojson_region_func(
        metrics,
        target="station",
        selector="all",
        region_col=station_region_col,
    )
    waveform_order = waveform_order_func(waveform_records, max_traces=12)
    pattern_rows = pattern_rows_func(
        metrics,
        metric=pattern_metric,
        passband=pattern_passband,
        component=component,
        model=model,
    )

    rows: list[dict[str, Any]] = []
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
            stem_parts=("step_06", "station_event_waveform_map"),
            include_basemap=True,
            display_func=display_func,
            waveform_col="observed",
            time_limit_s=waveform_time_limit_s,
            normalize=True,
            title=f"Observed Station-Event Waveform Map\n{waveform_event_name}",
            filter_label=f"lowpass 1 Hz; {waveform_component} component; {waveform_passband} QC passband",
        )
    )
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
            stem_parts=("step_06", "pattern_similarity"),
            display_func=display_func,
            metric=pattern_metric,
            bin_label=pattern_passband,
            title=pattern_title,
            fit="linear",
        )
    )
    rows.append(
        _write_standard_notebook_figure(
            "metric_scatterplot",
            metrics,
            render_notebook_figure,
            scatterplot_func,
            outputs,
            "scatterplot_figure_path",
            metric_settings,
            data=metrics,
            indep="distance",
            dep=["PGA", "PGV"],
            value_col=value_col,
            passband=passbands,
            model=model,
            component=component,
            colorby="dep",
            fit="lowess",
            title="PGA and PGV Residuals vs Distance",
            stem_parts=("step_06", "metric_scatterplot"),
            display_func=display_func,
        )
    )
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
            dep=["PGA", "PGV"],
            indep=station_region_col,
            value_col=value_col,
            passband=passbands,
            model=model,
            component=component,
            compare_to="LA Basin",
            table=True,
            title="PGA and PGV Residuals by GeoJSON Region",
            stem_parts=("step_06", "metric_boxplot"),
            display_func=display_func,
        )
    )
    rows.append(
        _write_standard_notebook_figure(
            "metric_heatmap",
            region_metrics,
            render_notebook_figure,
            heatmap_func,
            outputs,
            "heatmap_figure_path",
            metric_settings,
            data=region_metrics,
            dep=["PGA", "PGV", "PGD"],
            indep=station_region_col,
            value_col=value_col,
            passband=passbands,
            model=model,
            component=component,
            aggfunc="mean",
            title="Mean Residual by GeoJSON Region and Metric",
            stem_parts=("step_06", "metric_heatmap"),
            display_func=display_func,
        )
    )
    return StandardAdditionalPlottingFigureResult(
        rows=tuple(rows),
        metric_summary=metric_summary,
        waveform_order=waveform_order,
        region_metrics=region_metrics,
        pattern_rows=pattern_rows,
    )


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
        plt.close("all")
        status = "plot_failed"
        message = f"{type(exc).__name__}: {exc}"
    return {
        "artifact": artifact,
        "status": status,
        "row_count": len(frame),
        "figure_path": str(path),
        "message": message,
    }


def write_large_run_geojson_region_figures_from_outputs(
    outputs: Any,
    ingest_outputs: Any,
    *,
    geojson_path: str | Path,
    figure_dir: str | Path,
    cfg: SpatialVTKConfig | None = None,
    metric: str = "PGA",
    passband: str | Sequence[str] = "2-3 sec",
    component: str | Sequence[str] | None = None,
    model: str | Sequence[str] | None = None,
    value_col: str = "log2_residual",
    compare_to: str | Sequence[str] | None = "LA Basin",
    max_rows: int = 200_000,
    region_boxplot_prefix: str = "geojson_region_boxplot",
    overview_add_basemap: bool = True,
    corridor_add_basemap: bool = False,
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

    output_dir = Path(figure_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []
    geojson_status = "skipped"
    corridor_status = "skipped"
    geojson_overview_path = _resolve_region_figure_output(
        outputs,
        "geojson_polygons_map_path",
        "geojson_polygons_map",
        cfg=cfg,
        fallback_dir=output_dir,
    )
    corridor_map_path = _resolve_region_figure_output(
        outputs,
        "corridor_map_path",
        "corridor_map",
        cfg=cfg,
        fallback_dir=output_dir,
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
                stations_df=stations,
                events_df=events,
                add_basemap=overview_add_basemap,
                savefig=True,
                showfig=showfig,
                write_sidecar=write_sidecar,
                sidecar_rows=sidecar_rows,
                sidecar_dir=sidecar_dir,
            )
            plt.close("all")
            geojson_status = "wrote"
            messages.append(f"geojson_overview: wrote {geojson_overview_path}")
        except Exception as exc:
            plt.close("all")
            geojson_status = "plot_failed"
            messages.append(f"geojson_overview: skip {geojson_overview_path.name}: {type(exc).__name__}: {exc}")

    corridor_table_path = getattr(outputs, "paths", {}).get("corridors_path")
    if corridor_table_path is not None and Path(corridor_table_path).exists():
        corridors = read_table(corridor_table_path)
    elif hasattr(outputs, "load_table"):
        corridors = outputs.load_table("corridors", cfg=cfg, missing="skip")
    else:
        corridors = None
    if corridors is None:
        corridor_status = "missing_input"
        messages.append("corridor_map: corridor table is not ready yet; skipping corridor map")
    elif corridor_map_path.exists() and not overwrite:
        corridor_status = "exists"
        messages.append(f"corridor_map: skip {corridor_map_path.name}: exists")
    else:
        try:
            plot_corridor_map(
                corridors,
                output_path=corridor_map_path,
                stations_df=stations,
                events_df=events,
                add_basemap=corridor_add_basemap,
                savefig=True,
                showfig=showfig,
                write_sidecar=write_sidecar,
                sidecar_rows=sidecar_rows,
                sidecar_dir=sidecar_dir,
            )
            plt.close("all")
            corridor_status = "wrote"
            messages.append(f"corridor_map: wrote {corridor_map_path}")
        except Exception as exc:
            plt.close("all")
            corridor_status = "plot_failed"
            messages.append(f"corridor_map: skip {corridor_map_path.name}: {type(exc).__name__}: {exc}")

    boxplot_result = write_large_run_region_boxplot_from_outputs(
        outputs,
        figure_dir=output_dir,
        geojson_path=geojson_path,
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


def write_large_run_geojson_region_figures_from_notebook_settings(
    outputs: Any,
    ingest_outputs: Any,
    settings: Any,
    *,
    geojson_path: str | Path,
    cfg: SpatialVTKConfig | None = None,
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

    plot_rows = metric_rows.copy()
    plot_rows["station_region"] = plot_rows[region_col].fillna("").astype(str).str.replace("_", " ", regex=False)
    plot_rows = plot_rows.loc[plot_rows["station_region"].str.len() > 0].copy()
    if plot_rows.empty:
        return RegionBoxplotResult(
            None,
            None,
            len(metric_rows),
            "empty_region_labels",
            "skip region boxplot: no rows have station-region labels",
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
        return RegionBoxplotResult(output, sidecar_path, len(plot_rows), "exists", message)

    try:
        import matplotlib.pyplot as plt

        boxplot(
            data=plot_rows,
            output_path=output,
            dep=metric,
            indep="station_region",
            value_col=value_col,
            passband=passband,
            model=model,
            component=component,
            compare_to=compare_to,
            table=True,
            title=f"{metric} Residuals by Station Region",
            showfig=showfig,
            savefig=True,
        )
        plt.close("all")
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
        try:
            import matplotlib.pyplot as plt

            plt.close("all")
        except Exception:
            pass
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
    return RegionBoxplotResult(output, sidecar_path, len(plot_rows), "wrote", message)


def write_large_run_region_boxplot_from_outputs(
    outputs: Any,
    *,
    figure_dir: str | Path,
    metric_candidates: Sequence[str] = ("metrics_enriched_path", "metrics_long_path"),
    default_metric_source: str | Path | None = "metrics_long_path",
    **kwargs: Any,
) -> RegionBoxplotResult:
    """Write a region boxplot using a fallback metric table from an output group.

    Large-run notebooks usually prefer ``metrics_enriched`` because it carries
    spatial metadata, but can fall back to ``metrics_long`` when enrichment has
    not been written yet. This helper keeps that fallback selection in package
    code and delegates the bounded table read and plotting behavior to
    :func:`write_large_run_region_boxplot`.
    """

    metric_source = outputs.first_existing_path(
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
    return write_large_run_region_boxplot(
        metric_source,
        figure_dir=figure_dir,
        **kwargs,
    )


def write_large_run_region_boxplot_from_notebook_settings(
    outputs: Any,
    settings: Any,
    *,
    output_prefix: str = "additional_region_boxplot",
    geojson_path: str | Path | None = None,
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
    cfg: SpatialVTKConfig | None,
    fallback_dir: Path,
) -> Path:
    """Resolve one region figure path from an output group or config."""

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
    cfg: SpatialVTKConfig | None,
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
        elif key == "metric_field":
            df.attrs[SPATIAL_CONTEXT_ATTR] = "metric"
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
    if suffix in {".parquet", ".pq"}:
        try:
            import pyarrow.parquet as pq

            return list(pq.ParquetFile(path).schema.names)
        except Exception:
            return list(pd.read_parquet(path).head(0).columns)
    if suffix == ".csv":
        return list(pd.read_csv(path, nrows=0).columns)
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
            "compare_to": compare_to,
        },
    )
    return None if result is None else result.sidecar_path


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
