"""Large-run spatial plotting orchestration helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.io import load_output_table, read_table
from spatial_vtk.metrics.plot.large_run import (
    MetricFigureContext,
    first_existing,
)


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
        station_aggregation: str = "median",
    ) -> "SpatialFigureContext":
        """Load compact spatial output tables and return a plotting context."""

        output_dir = Path(figure_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = {
            key: resolve_output_path(key, kind="table", create_parent=True)
            for key in SPATIAL_FIGURE_TABLE_KEYS
        }
        tables = {key: _read_if_exists(path) for key, path in paths.items()}
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
            station_aggregation=station_aggregation,
        )
        try:
            site_metadata = load_output_table("prepared_stations")
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
            required=[column for column in required if column],
            value_col=value_col,
            forward_value_col=forward_value_col,
            showfig=showfig,
            **kwargs,
        )

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


def prepare_spatial_figure_context(**kwargs: Any) -> SpatialFigureContext:
    """Return a reusable spatial figure context for large-run notebooks."""

    return SpatialFigureContext.from_config(**kwargs)


def _read_if_exists(path: str | Path | None) -> pd.DataFrame | None:
    """Read one table path if it exists."""

    if path is None:
        return None
    input_path = Path(path)
    if not input_path.exists():
        return None
    return read_table(input_path)


def _first_existing(df: pd.DataFrame | None, candidates: list[str]) -> str | None:
    """Return the first candidate column present in a dataframe."""

    return first_existing(df, candidates) if df is not None else None


__all__ = [
    "SPATIAL_FIGURE_TABLE_KEYS",
    "SpatialFigureContext",
    "prepare_spatial_figure_context",
]
