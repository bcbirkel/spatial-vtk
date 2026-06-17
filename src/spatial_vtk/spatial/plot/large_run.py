"""Large-run spatial plotting orchestration helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

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
    "morans_i",
    "geology_contrasts",
)

SPATIAL_EVENT_ROW_TABLE_KEYS: frozenset[str] = frozenset(
    {"metric_field", "event_centered_residuals"}
)

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
    "field_centered",
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
            key: _read_if_exists(path, columns=_columns_for_spatial_table(key))
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
        yield from context.iter_metric_frames(
            passband=passband,
            components=components,
            model=model,
            split_psa_period=split_psa_period,
        )

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

        context = self._context_for(item.get("df")) or self.metric_context
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

        context = self._context_for(item.get("df")) or self.metric_context
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

        context = self._context_for(item.get("df")) or self.metric_context
        return context.item_source_rows(item)

    def station_summary_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate one figure item's rows to one plotted value per station."""

        context = self._context_for(item.get("df")) or self.metric_context
        return context.station_summary_for_item(item, value_col=value_col, extra_group_cols=extra_group_cols)

    def station_period_summary_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate one PSA figure item's rows to one plotted value per station and period."""

        context = self._context_for(item.get("df")) or self.metric_context
        return context.station_period_summary_for_item(item, value_col=value_col, extra_group_cols=extra_group_cols)

    def station_grid_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate one figure item and expose station coordinates as lon/lat."""

        context = self._context_for(item.get("df")) or self.metric_context
        return context.station_grid_for_item(item, value_col=value_col, extra_group_cols=extra_group_cols)

    def station_period_grid_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate one PSA figure item by station/period and expose lon/lat columns."""

        context = self._context_for(item.get("df")) or self.metric_context
        return context.station_period_grid_for_item(item, value_col=value_col, extra_group_cols=extra_group_cols)

    def station_model_summary_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
    ) -> pd.DataFrame:
        """Aggregate one figure item by station and model."""

        context = self._context_for(item.get("df")) or self.metric_context
        return context.station_model_summary_for_item(item, value_col=value_col)

    def station_model_grid_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
    ) -> pd.DataFrame:
        """Aggregate one figure item by station/model and expose lon/lat columns."""

        context = self._context_for(item.get("df")) or self.metric_context
        return context.station_model_grid_for_item(item, value_col=value_col)

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

    def _context_for(self, df: pd.DataFrame | None) -> MetricFigureContext | None:
        """Return the metric or event context that owns one dataframe."""

        if df is None or df.empty:
            return None
        event = self.event_centered
        if event is not None and set(df.columns).issubset(set(event.columns)):
            return self.event_context
        return self.metric_context


@dataclass(frozen=True)
class RegionBoxplotResult:
    """Result from writing a large-run GeoJSON region boxplot."""

    figure_path: Path | None
    sidecar_path: Path | None
    rows: int
    status: str
    message: str


def prepare_spatial_figure_context(**kwargs: Any) -> SpatialFigureContext:
    """Return a reusable spatial figure context for large-run notebooks."""

    return SpatialFigureContext.from_config(**kwargs)


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


def _columns_for_spatial_table(key: str) -> tuple[str, ...] | None:
    """Return column projection for large spatial event-row tables."""

    if key in SPATIAL_EVENT_ROW_TABLE_KEYS:
        return SPATIAL_EVENT_ROW_COLUMNS
    return None


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


__all__ = [
    "RegionBoxplotResult",
    "SPATIAL_FIGURE_TABLE_KEYS",
    "SpatialFigureContext",
    "prepare_spatial_figure_context",
    "write_large_run_region_boxplot",
]
