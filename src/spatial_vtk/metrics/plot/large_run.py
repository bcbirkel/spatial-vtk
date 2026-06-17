"""Large-run metric plotting orchestration helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import importlib
import re
from tempfile import TemporaryDirectory
from typing import Any, Callable, Iterable

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from spatial_vtk.visualize.figure_sidecars import write_figure_row_sidecar


TARGET_METRIC_SPECS = (
    {"key": "arias_duration", "label": "Arias duration", "aliases": ("Arias duration", "Arias duration (5-95%)", "arias_duration", "AD")},
    {"key": "pga", "label": "PGA", "aliases": ("PGA", "Peak acceleration", "Peak ground acceleration")},
    {"key": "pgv", "label": "PGV", "aliases": ("PGV", "Peak velocity", "Peak ground velocity")},
    {"key": "psa", "label": "PSA", "aliases": ("PSA", "Pseudo-spectral acceleration", "Pseudo spectral acceleration")},
    {"key": "traveltime_delay", "label": "Traveltime delay", "aliases": ("traveltime delay", "travel time delay", "travel-time delay", "TT delay", "traveltime")},
    {"key": "cav", "label": "CAV", "aliases": ("CAV", "Cumulative absolute velocity")},
)


@dataclass
class MetricFigureContext:
    """Reusable state and helpers for large-run metric figure notebooks."""

    metrics_long_path: Path
    figure_dir: Path
    make_figures: bool
    overwrite: bool = False
    sample_rows: int = 200_000
    value_col: str = "log2_residual"
    default_passband: str | None = None
    default_components: list[str] | None = None
    default_showfig: bool = False
    default_model: str | None = None
    add_basemap: bool = False
    robust_axis_percentile: float = 95.0
    write_sidecars: bool = False
    sidecar_rows: int | None = None
    sidecar_dir: Path | None = None
    station_aggregation: str = "median"
    metrics_for_figures: pd.DataFrame = field(default_factory=pd.DataFrame)
    loaded_columns: list[str] = field(default_factory=list)
    available_columns: list[str] = field(default_factory=list)
    metric_col: str | None = None
    band_col: str | None = None
    model_col: str | None = None
    component_col: str | None = None
    period_col: str | None = None
    distance_col: str | None = None
    depth_col: str | None = None
    vs30_col: str | None = None
    ready: bool = False

    @classmethod
    def from_metrics_long(
        cls,
        metrics_long_path: str | Path,
        figure_dir: str | Path,
        *,
        make_figures: bool,
        overwrite: bool = False,
        sample_rows: int = 200_000,
        value_col: str = "log2_residual",
        default_passband: str | None = None,
        default_components: list[str] | None = None,
        default_showfig: bool = False,
        default_model: str | None = None,
        add_basemap: bool = False,
        robust_axis_percentile: float = 95.0,
        write_sidecars: bool = False,
        sidecar_rows: int | None = None,
        sidecar_dir: str | Path | None = None,
        station_aggregation: str = "median",
    ) -> "MetricFigureContext":
        """Create a context from a metric table path and print readiness."""

        path = Path(metrics_long_path).expanduser()
        output_dir = Path(figure_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        context = cls(
            metrics_long_path=path,
            figure_dir=output_dir,
            make_figures=bool(make_figures),
            overwrite=bool(overwrite),
            sample_rows=int(sample_rows),
            value_col=str(value_col),
            default_passband=default_passband,
            default_components=default_components,
            default_showfig=bool(default_showfig),
            default_model=default_model,
            add_basemap=bool(add_basemap),
            robust_axis_percentile=float(robust_axis_percentile),
            write_sidecars=bool(write_sidecars),
            sidecar_rows=None if sidecar_rows is None else int(sidecar_rows),
            sidecar_dir=None if sidecar_dir is None else Path(sidecar_dir).expanduser(),
            station_aggregation=str(station_aggregation or "median").lower(),
        )
        if not context.make_figures:
            print("Skipping metric figures. Set SVTK_MAKE_METRIC_FIGURES=1 or SVTK_MAKE_FIGURES=1 to render them.")
            return context
        if not path.exists():
            print(f"metrics_long.parquet is not ready yet: {path}")
            return context
        available_columns = _table_columns(path)
        columns = _metric_figure_columns(available_columns, value_col=context.value_col)
        metrics = _read_metric_figure_table(path, columns=columns)
        context.available_columns = available_columns
        context.loaded_columns = list(metrics.columns)
        context.metrics_for_figures = metrics
        context.metric_col = first_existing(metrics, ["metric"])
        context.band_col = first_existing(metrics, ["band", "passband"])
        context.model_col = first_existing(metrics, ["model"])
        context.component_col = first_existing(metrics, ["component"])
        context.period_col = first_existing(metrics, ["period_s"])
        context.distance_col = first_existing(metrics, ["distance_km"])
        context.depth_col = first_existing(metrics, ["depth_km", "event_depth_km"])
        context.vs30_col = first_existing(metrics, ["Vs30", "vs30", "VS30", "site_vs30", "station_vs30", "vs30_mps", "Vs30_mps"])
        metrics = context._apply_load_filters(metrics)
        context.metrics_for_figures = metrics
        if context.value_col not in metrics.columns:
            print(f"Cannot render metric figures: {context.value_col!r} is not present in metrics_long.")
            return context
        context.ready = True
        limit_text = "no per-figure row limit" if context.sample_rows <= 0 else f"up to {context.sample_rows:,} raw row(s) per figure"
        column_text = (
            f"{len(context.loaded_columns)}/{len(context.available_columns)} column(s)"
            if context.available_columns
            else f"{len(context.loaded_columns)} column(s)"
        )
        print(f"Rendering metric figures from {len(metrics):,} selected metric row(s) and {column_text} into {output_dir}; {limit_text}")
        print(
            f"value_col={context.value_col} "
            f"default_passband={context.default_passband} "
            f"default_components={context.default_components} "
            f"default_model={context.default_model} "
            f"station_aggregation={context.station_aggregation}"
        )
        if context.write_sidecars:
            sidecar_dir = context.sidecar_output_dir
            rows_text = "all plotted rows" if context.sidecar_rows is None or context.sidecar_rows <= 0 else f"up to {context.sidecar_rows:,} plotted row(s)"
            print(f"Figure sidecars enabled: {sidecar_dir} ({rows_text}; source-row sidecars are written for aggregated figures)")
        return context

    @classmethod
    def from_frame(
        cls,
        metrics: pd.DataFrame | None,
        figure_dir: str | Path,
        *,
        make_figures: bool,
        overwrite: bool = False,
        sample_rows: int = 200_000,
        value_col: str = "log2_residual",
        default_passband: str | None = None,
        default_components: list[str] | None = None,
        default_showfig: bool = False,
        default_model: str | None = None,
        add_basemap: bool = False,
        robust_axis_percentile: float = 95.0,
        write_sidecars: bool = False,
        sidecar_rows: int | None = None,
        sidecar_dir: str | Path | None = None,
        station_aggregation: str = "median",
    ) -> "MetricFigureContext":
        """Create a context from an already loaded metrics dataframe."""

        output_dir = Path(figure_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        context = cls(
            metrics_long_path=Path(),
            figure_dir=output_dir,
            make_figures=bool(make_figures),
            overwrite=bool(overwrite),
            sample_rows=int(sample_rows),
            value_col=str(value_col),
            default_passband=default_passband,
            default_components=default_components,
            default_showfig=bool(default_showfig),
            default_model=default_model,
            add_basemap=bool(add_basemap),
            robust_axis_percentile=float(robust_axis_percentile),
            write_sidecars=bool(write_sidecars),
            sidecar_rows=None if sidecar_rows is None else int(sidecar_rows),
            sidecar_dir=None if sidecar_dir is None else Path(sidecar_dir).expanduser(),
            station_aggregation=str(station_aggregation or "median").lower(),
        )
        if metrics is None or metrics.empty:
            return context
        context.metrics_for_figures = metrics.copy()
        context.metric_col = first_existing(metrics, ["metric"])
        context.band_col = first_existing(metrics, ["band", "passband"])
        context.model_col = first_existing(metrics, ["model"])
        context.component_col = first_existing(metrics, ["component"])
        context.period_col = first_existing(metrics, ["period_s"])
        context.distance_col = first_existing(metrics, ["distance_km"])
        context.depth_col = first_existing(metrics, ["depth_km", "event_depth_km"])
        context.vs30_col = first_existing(
            metrics,
            ["Vs30", "vs30", "VS30", "site_vs30", "station_vs30", "vs30_mps", "Vs30_mps"],
        )
        context.available_columns = list(metrics.columns)
        context.loaded_columns = list(metrics.columns)
        context.metrics_for_figures = context._apply_load_filters(context.metrics_for_figures)
        context.ready = context.value_col in metrics.columns
        return context

    @property
    def sidecar_output_dir(self) -> Path:
        """Return the directory used for figure sidecar CSV files."""

        return self.sidecar_dir or (self.figure_dir / "sidecars")

    def metric_mask(self, df: pd.DataFrame, aliases: tuple[str, ...]) -> pd.Series:
        """Return rows whose metric text matches one alias."""

        if self.metric_col is None:
            return pd.Series(False, index=df.index)
        normalized_aliases = {norm_text(alias) for alias in aliases}
        metric_text = df[self.metric_col].astype(str)
        normalized_metric = metric_text.map(norm_text)
        exact = normalized_metric.isin(normalized_aliases)
        if exact.any():
            return exact
        return normalized_metric.map(lambda value: any(alias in value or value in alias for alias in normalized_aliases))

    def filtered_base(
        self,
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        include_passband: bool = True,
    ) -> pd.DataFrame:
        """Return sampled metric rows filtered by optional dimensions."""

        out = self.metrics_for_figures.copy()
        if include_passband and passband is not None:
            out = filter_optional(out, self.band_col, passband)
        if components is not None:
            out = filter_optional(out, self.component_col, components)
        if model is not None:
            out = filter_optional(out, self.model_col, model)
        return out

    def _apply_load_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply safe default filters immediately after loading metric rows."""

        out = df
        if self.component_col is not None and self.default_components is not None:
            out = filter_optional(out, self.component_col, self.default_components)
        if self.model_col is not None and self.default_model is not None:
            out = filter_optional(out, self.model_col, self.default_model)
        if self.metric_col is not None:
            mask = pd.Series(False, index=out.index)
            for spec in TARGET_METRIC_SPECS:
                mask = mask | self.metric_mask(out, tuple(spec["aliases"]))
            if mask.any():
                out = out.loc[mask].copy()
        return out

    def iter_metric_frames(
        self,
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        split_psa_period: bool = True,
    ):
        """Yield filtered frames for the configured target metrics."""

        for spec in TARGET_METRIC_SPECS:
            base = self.filtered_base(
                passband=passband,
                components=components,
                model=model,
                include_passband=spec["key"] != "psa",
            )
            subset = base.loc[self.metric_mask(base, tuple(spec["aliases"]))].copy()
            if spec["key"] == "psa":
                subset = self._broadband_spectral_rows(subset)
            if subset.empty:
                print(f"skip {spec['label']}: no matching rows")
                continue
            if spec["key"] == "psa" and split_psa_period and self.period_col in subset.columns:
                periods = sorted(pd.to_numeric(subset[self.period_col], errors="coerce").dropna().unique())
                for period in periods:
                    period_subset = subset.loc[pd.to_numeric(subset[self.period_col], errors="coerce").eq(period)].copy()
                    if not period_subset.empty:
                        yield {"key": spec["key"], "label": f"{spec['label']} {period:g}s", "metric": spec["label"], "period_s": period, "df": period_subset}
            else:
                yield {"key": spec["key"], "label": spec["label"], "metric": spec["label"], "period_s": None, "df": subset}

    def figure_name(self, base: str, item: dict[str, Any], value_col: str | None = None) -> str:
        """Build a stable figure filename stem from selected dimensions."""

        df = item["df"]
        resolved_value_col = self.value_col if value_col is None else value_col
        parts = [base, item["key"]]
        if item.get("key") == "psa" and item.get("period_s") is None and self.period_col in df.columns:
            parts.append("all-psa-periods")
        elif item.get("period_s") is not None:
            parts.append(f"period-{item['period_s']:g}s")
        dimension_columns: list[tuple[str | None, str]] = [] if item.get("key") == "psa" else [(self.band_col, "all-passbands")]
        dimension_columns.extend([(self.component_col, "all-components"), (self.model_col, "all-models")])
        for column, multi_label in dimension_columns:
            value = dimension_value(df, column, multi_label)
            if value:
                parts.append(slug(value))
        if resolved_value_col:
            parts.append(slug(resolved_value_col))
        return "__".join(dict.fromkeys(parts))

    def station_summary_for_map(
        self,
        df: pd.DataFrame,
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate all selected metric rows to one plotted value per station."""

        resolved_value_col = self.value_col if value_col is None else value_col
        lon_col, lat_col = _station_coordinate_columns(df)
        if lon_col is None or lat_col is None:
            return df
        if resolved_value_col not in df.columns:
            return df
        station_col = _station_identifier_column(df)
        finite_df = _finite_value_rows(df, resolved_value_col)
        if finite_df.empty:
            return finite_df
        group_cols = _station_group_columns(
            finite_df,
            station_col=station_col,
            lon_col=lon_col,
            lat_col=lat_col,
            extra_group_cols=extra_group_cols,
        )
        context_cols = [
            column
            for column in [self.metric_col, self.band_col, self.model_col, self.component_col, self.period_col]
            if column and column in finite_df.columns and column not in group_cols
        ]
        grouped = finite_df.groupby(group_cols, dropna=False)
        values = _aggregate_grouped_values(grouped[resolved_value_col], self.station_aggregation).reset_index(name=resolved_value_col)
        counts = grouped.size().reset_index(name="source_row_count")
        summary = values.merge(counts, on=group_cols, how="left")
        source_grouped = df.groupby(group_cols, dropna=False)
        coordinates = _station_coordinate_summary(source_grouped, lon_col=lon_col, lat_col=lat_col).reset_index()
        summary = summary.merge(coordinates, on=group_cols, how="left")
        event_col = _event_identifier_column(finite_df)
        if event_col is not None:
            event_counts = grouped[event_col].nunique(dropna=True).reset_index(name="source_event_count")
            summary = summary.merge(event_counts, on=group_cols, how="left")
        input_counts = _input_group_counts(df, group_cols, event_col=event_col)
        if not input_counts.empty:
            summary = summary.merge(input_counts, on=group_cols, how="left")
            summary = _add_station_aggregation_drop_counts(summary)
        for column in context_cols:
            summary[column] = dimension_value(df, column, self.context_multi_label(column))
        summary["aggregation"] = self.station_aggregation
        summary = _rename_station_identifier(summary, station_col=station_col)
        summary = _rename_station_coordinates(summary, lon_col=lon_col, lat_col=lat_col)
        summary.attrs.update(
            _station_aggregation_attrs(
                value_col=resolved_value_col,
                method=self.station_aggregation,
                group_cols=group_cols,
                coordinate_cols=(lon_col, lat_col),
                source_rows=df,
                finite_rows=finite_df,
            )
        )
        return summary

    def station_period_summary_for_map(
        self,
        df: pd.DataFrame,
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate all selected PSA rows to one plotted value per station and period."""

        resolved_value_col = self.value_col if value_col is None else value_col
        if self.period_col is None or self.period_col not in df.columns:
            return self.station_summary_for_map(df, value_col=resolved_value_col, extra_group_cols=extra_group_cols)
        lon_col, lat_col = _station_coordinate_columns(df)
        if lon_col is None or lat_col is None:
            return df
        if not all(column in df.columns for column in [self.period_col, resolved_value_col]):
            return df
        station_col = _station_identifier_column(df)
        finite_df = _finite_value_rows(df, resolved_value_col)
        if finite_df.empty:
            return finite_df
        group_cols = _station_group_columns(
            finite_df,
            station_col=station_col,
            lon_col=lon_col,
            lat_col=lat_col,
            extra_group_cols=[self.period_col, *(extra_group_cols or [])],
        )
        context_cols = [
            column
            for column in [self.metric_col, self.band_col, self.model_col, self.component_col]
            if column and column in finite_df.columns and column not in group_cols
        ]
        grouped = finite_df.groupby(group_cols, dropna=False)
        values = _aggregate_grouped_values(grouped[resolved_value_col], self.station_aggregation).reset_index(name=resolved_value_col)
        counts = grouped.size().reset_index(name="source_row_count")
        summary = values.merge(counts, on=group_cols, how="left")
        source_grouped = df.groupby(group_cols, dropna=False)
        coordinates = _station_coordinate_summary(source_grouped, lon_col=lon_col, lat_col=lat_col).reset_index()
        summary = summary.merge(coordinates, on=group_cols, how="left")
        event_col = _event_identifier_column(finite_df)
        if event_col is not None:
            event_counts = grouped[event_col].nunique(dropna=True).reset_index(name="source_event_count")
            summary = summary.merge(event_counts, on=group_cols, how="left")
        input_counts = _input_group_counts(df, group_cols, event_col=event_col)
        if not input_counts.empty:
            summary = summary.merge(input_counts, on=group_cols, how="left")
            summary = _add_station_aggregation_drop_counts(summary)
        for column in context_cols:
            summary[column] = dimension_value(df, column, self.context_multi_label(column))
        summary["aggregation"] = self.station_aggregation
        summary = _rename_station_identifier(summary, station_col=station_col)
        summary = _rename_station_coordinates(summary, lon_col=lon_col, lat_col=lat_col)
        summary.attrs.update(
            _station_aggregation_attrs(
                value_col=resolved_value_col,
                method=self.station_aggregation,
                group_cols=group_cols,
                coordinate_cols=(lon_col, lat_col),
                source_rows=df,
                finite_rows=finite_df,
            )
        )
        return summary

    def write_metric_plot(
        self,
        base: str,
        item: dict[str, Any],
        func: Callable[..., Any],
        df: pd.DataFrame | None = None,
        source_df: pd.DataFrame | None = None,
        required: tuple[str, ...] | list[str] = (),
        value_col: str | None = None,
        forward_value_col: bool = False,
        showfig: bool = False,
        **kwargs: Any,
    ) -> Path | None:
        """Write one figure or print a skip reason."""

        resolved_value_col = self.value_col if value_col is None else value_col
        plot_df = self.plot_rows(item["df"] if df is None else df)
        output = self.figure_dir / f"{self.figure_name(base, item, resolved_value_col)}.png"
        if output.exists() and not self.overwrite:
            print(f"skip {output.name}: exists")
            self.write_figure_sidecar(output, plot_df, source_df=source_df)
            return output
        missing = [column for column in required if column not in plot_df.columns]
        if missing:
            print(f"skip {output.name}: missing columns {missing}")
            return None
        if forward_value_col and resolved_value_col is not None and "value_col" not in kwargs:
            kwargs["value_col"] = resolved_value_col
        try:
            func(plot_df, output_path=output, showfig=showfig, savefig=True, **kwargs)
            plt.close("all")
            self.write_figure_sidecar(output, plot_df, source_df=source_df)
            print(f"wrote {output}")
            return output
        except Exception as exc:
            plt.close("all")
            print(f"skip {output.name}: {type(exc).__name__}: {exc}")
            return None

    def write_psa_period_sheet(
        self,
        base: str,
        item: dict[str, Any],
        func: Callable[..., Any],
        df_factory: Callable[[dict[str, Any]], pd.DataFrame] | None = None,
        source_df_factory: Callable[[dict[str, Any]], pd.DataFrame | None] | None = None,
        required: tuple[str, ...] | list[str] = (),
        value_col: str | None = None,
        forward_value_col: bool = False,
        showfig: bool = False,
        **kwargs: Any,
    ) -> Path | None:
        """Write a contact-sheet figure with one panel per PSA period."""

        resolved_value_col = self.value_col if value_col is None else value_col
        period_items = self.psa_period_items(item)
        if not period_items:
            return self.write_metric_plot(
                base,
                item,
                func,
                df=df_factory(item) if df_factory else None,
                source_df=source_df_factory(item) if source_df_factory else None,
                required=required,
                value_col=resolved_value_col,
                forward_value_col=forward_value_col,
                showfig=showfig,
                **kwargs,
            )
        output = self.figure_dir / f"{self.figure_name(base, item, resolved_value_col)}.png"
        if output.exists() and not self.overwrite:
            print(f"skip {output.name}: exists")
            self.write_figure_sidecar(
                output,
                self.plot_rows(df_factory(item) if df_factory else item["df"]),
                source_df=source_df_factory(item) if source_df_factory else None,
            )
            return output
        ncols = min(3, max(1, len(period_items)))
        nrows = int(np.ceil(len(period_items) / ncols))
        fig, axes = plt.subplots(nrows, ncols, figsize=(5.8 * ncols, 4.7 * nrows), dpi=160, squeeze=False)
        axes_flat = axes.ravel()
        sidecar_frames: list[pd.DataFrame] = []
        source_sidecar_frames: list[pd.DataFrame] = []
        with TemporaryDirectory() as tmpdir_raw:
            tmpdir = Path(tmpdir_raw)
            for ax, period_item in zip(axes_flat, period_items):
                plot_df = self.plot_rows(df_factory(period_item) if df_factory else period_item["df"])
                sidecar_frames.append(plot_df.assign(__svtk_panel_period_s=period_item.get("period_s")))
                if source_df_factory is not None:
                    source_rows = source_df_factory(period_item)
                    if source_rows is not None:
                        source_sidecar_frames.append(source_rows.copy().assign(__svtk_panel_period_s=period_item.get("period_s")))
                missing = [column for column in required if column not in plot_df.columns]
                if missing:
                    ax.text(0.5, 0.5, f"Missing columns: {missing}", ha="center", va="center", wrap=True)
                    ax.set_axis_off()
                    continue
                panel_path = tmpdir / f"panel_{period_item['period_s']:g}.png"
                call_kwargs = dict(kwargs)
                if forward_value_col and resolved_value_col is not None and "value_col" not in call_kwargs:
                    call_kwargs["value_col"] = resolved_value_col
                try:
                    func(plot_df, output_path=panel_path, showfig=False, savefig=True, **call_kwargs)
                    plt.close("all")
                    image = mpimg.imread(panel_path)
                    ax.imshow(image)
                    ax.set_title(psa_period_label(period_item["period_s"]), fontsize=9)
                    ax.set_axis_off()
                except Exception as exc:
                    plt.close("all")
                    ax.text(0.5, 0.5, f"{type(exc).__name__}: {exc}", ha="center", va="center", wrap=True)
                    ax.set_axis_off()
            for ax in axes_flat[len(period_items):]:
                ax.set_axis_off()
        fig.suptitle(f"{base.replace('_', ' ').title()} - PSA by oscillator period", fontsize=12, y=0.99)
        fig.tight_layout(rect=[0.01, 0.01, 0.99, 0.96])
        fig.savefig(output, bbox_inches="tight")
        if sidecar_frames:
            source_rows = pd.concat(source_sidecar_frames, ignore_index=True, sort=False) if source_sidecar_frames else None
            self.write_figure_sidecar(output, pd.concat(sidecar_frames, ignore_index=True, sort=False), source_df=source_rows)
        if showfig:
            plt.show()
        plt.close(fig)
        print(f"wrote {output}")
        return output

    def write_generic_metric_diagnostic_plots(
        self,
        scatterplot_func: Callable[..., Any],
        boxplot_func: Callable[..., Any],
        heatmap_func: Callable[..., Any],
        period_distribution_func: Callable[..., Any],
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        value_col: str | None = None,
        showfig: bool = False,
    ) -> list[Path]:
        """Write generic scatter, box, and heatmap diagnostics for target metrics.

        PSA rows are handled by oscillator period: scatter plots are written as
        period contact sheets, period distributions replace passband boxplots,
        and passband heatmaps are skipped because PSA is no longer calculated
        per band in the large-run workflow.
        """

        if not self.ready:
            print("Skipping generic metric diagnostics: metric figure context is not ready.")
            return []
        resolved_value_col = self.value_col if value_col is None else value_col
        outputs: list[Path] = []
        for item in self.iter_metric_frames(
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            metric_name = self.first_value(item["df"], self.metric_col) or item.get("metric", item["label"])
            if item["key"] == "psa":
                output = self.write_psa_period_sheet(
                    "scatterplot",
                    item,
                    scatterplot_func,
                    required=[self.distance_col, resolved_value_col],
                    indep=self.distance_col,
                    dep=metric_name,
                    value_col=resolved_value_col,
                    forward_value_col=True,
                    passband=None,
                    model=model,
                    colorby=self.component_col,
                    fit="lowess",
                    robust_axis_percentile=self.robust_axis_percentile,
                    showfig=showfig,
                )
                if output is not None:
                    outputs.append(output)
                output = self.write_metric_plot(
                    "boxplot",
                    item,
                    period_distribution_func,
                    required=[self.period_col, resolved_value_col],
                    period_col=self.period_col,
                    score_col=resolved_value_col,
                    color_col=self.component_col,
                    robust_axis_percentile=self.robust_axis_percentile,
                    showfig=showfig,
                )
                if output is not None:
                    outputs.append(output)
                print("skip heatmap for PSA: use the PSA period curve and period distribution figures instead of passband heatmaps")
                continue
            output = self.write_metric_plot(
                "scatterplot",
                item,
                scatterplot_func,
                required=[self.distance_col, resolved_value_col],
                indep=self.distance_col,
                dep=metric_name,
                value_col=resolved_value_col,
                forward_value_col=True,
                passband=passband,
                model=model,
                colorby=self.component_col,
                fit="lowess",
                robust_axis_percentile=self.robust_axis_percentile,
                showfig=showfig,
            )
            if output is not None:
                outputs.append(output)
            output = self.write_metric_plot(
                "boxplot",
                item,
                boxplot_func,
                required=[self.component_col, resolved_value_col] if self.component_col else [resolved_value_col],
                dep=metric_name,
                indep=self.component_col or self.model_col,
                value_col=resolved_value_col,
                forward_value_col=True,
                passband=passband,
                model=model,
                colorby=self.model_col if self.model_col in item["df"].columns else None,
                robust_axis_percentile=self.robust_axis_percentile,
                showfig=showfig,
            )
            if output is not None:
                outputs.append(output)
            output = self.write_metric_plot(
                "heatmap",
                item,
                heatmap_func,
                required=[resolved_value_col],
                dep=metric_name,
                indep=self.component_col or self.model_col,
                column=self.model_col if self.model_col in item["df"].columns else None,
                value_col=resolved_value_col,
                forward_value_col=True,
                passband=passband,
                model=model,
                showfig=showfig,
            )
            if output is not None:
                outputs.append(output)
        return outputs

    def psa_period_items(self, item: dict[str, Any]) -> list[dict[str, Any]]:
        """Return PSA item variants, one per oscillator period."""

        df = item["df"]
        if item.get("key") != "psa" or self.period_col is None or self.period_col not in df.columns:
            return []
        periods = sorted(pd.to_numeric(df[self.period_col], errors="coerce").dropna().unique())
        out = []
        period_values = pd.to_numeric(df[self.period_col], errors="coerce")
        for period in periods:
            subset = df.loc[period_values.eq(period)].copy()
            if not subset.empty:
                out.append({"key": item["key"], "label": f"{item['label']} {period:g}s", "metric": item.get("metric", item["label"]), "period_s": period, "df": subset})
        return out

    def plot_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return the exact rows that will be handed to a plotting function."""

        if self.sample_rows <= 0 or len(df) <= self.sample_rows:
            return df.copy()
        return _sample_rows(df, n=self.sample_rows)

    def write_figure_sidecar(
        self,
        figure_path: str | Path,
        df: pd.DataFrame,
        *,
        source_df: pd.DataFrame | None = None,
    ) -> Path | None:
        """Optionally write CSV and metadata files for rows used by one figure.

        The main sidecar contains the exact rows passed to the plotting
        function. When a figure is created from an aggregated table, callers can
        also pass ``source_df`` to write a ``*.source.csv`` sidecar containing
        the pre-aggregation rows that fed those plotted rows.
        """

        if not self.write_sidecars:
            return None
        figure = Path(figure_path)
        result = write_figure_row_sidecar(
            figure,
            df,
            enabled=True,
            sidecar_rows=self.sidecar_rows,
            sidecar_dir=self.sidecar_output_dir,
            source_rows=source_df,
            metadata=self.figure_sidecar_metadata(df, source_df=source_df),
        )
        return None if result is None else result.sidecar_path

    def figure_sidecar_metadata(self, df: pd.DataFrame, *, source_df: pd.DataFrame | None = None) -> dict[str, Any]:
        """Return provenance metadata for a metric figure sidecar."""

        metadata: dict[str, Any] = {
            "value_col": self.value_col,
            "station_aggregation": self.station_aggregation,
            "metrics_long_path": str(self.metrics_long_path) if str(self.metrics_long_path) != "." else None,
            "loaded_columns": list(self.loaded_columns),
        }
        aggregation_attrs = {
            str(key): value
            for key, value in getattr(df, "attrs", {}).items()
            if str(key).startswith("svtk_aggregation_")
        }
        metadata.update(aggregation_attrs)
        if aggregation_attrs:
            metadata["aggregation_contract"] = "station_event_rows_to_station_summary"
            metadata["plot_rows_role"] = "post_aggregation_station_summary"
        if source_df is not None:
            metadata["source_rows_role"] = "pre_aggregation_metric_rows" if aggregation_attrs else "figure_source_rows"
        return metadata

    def first_value(self, df: pd.DataFrame | None, column: str | None) -> str | None:
        """Return the first non-null value from one column."""

        return first_value(df, column)

    def context_multi_label(self, column: str) -> str:
        """Return a compact label for multi-valued plot dimensions."""

        if column == self.band_col:
            return "all-passbands"
        if column == self.component_col:
            return "all-components"
        if column == self.model_col:
            return "all-models"
        if column == self.period_col:
            return "all-psa-periods"
        return f"all-{slug(column)}"

    def _broadband_spectral_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep broadband spectral rows when present."""

        if self.band_col is None or self.band_col not in df.columns:
            return df
        labels = df[self.band_col].fillna("").astype(str).str.strip().str.lower()
        broadband = labels.isin(["", "all", "broadband", "none", "nan"])
        if broadband.any():
            return df.loc[broadband].copy()
        print("skip PSA: no broadband PSA rows found. Rebuild the metric manifest/metrics so spectral metrics are calculated once with blank passband instead of once per passband.")
        return df.iloc[0:0].copy()


def prepare_large_run_metric_figure_context(
    metrics_long_path: str | Path,
    figures_dir: str | Path,
    **kwargs: Any,
) -> MetricFigureContext:
    """Return a reusable metric figure context for large-run notebooks."""

    return MetricFigureContext.from_metrics_long(metrics_long_path, figures_dir, **kwargs)


def first_existing(df: pd.DataFrame, candidates: list[str | None]) -> str | None:
    """Return the first candidate column present in a dataframe."""

    return next((column for column in candidates if column and column in df.columns), None)


def first_value(df: pd.DataFrame | None, column: str | None) -> str | None:
    """Return the first non-null value from one column."""

    if df is None or column is None or column not in df.columns:
        return None
    values = df[column].dropna()
    return None if values.empty else str(values.iloc[0])


def dimension_value(df: pd.DataFrame | None, column: str | None, multi_label: str) -> str | None:
    """Return one dimension value or a multi-value label."""

    if df is None or column is None or column not in df.columns:
        return None
    values = [str(value) for value in pd.unique(df[column].dropna()) if str(value).strip()]
    if not values:
        return None
    return values[0] if len(values) == 1 else multi_label


def filter_optional(df: pd.DataFrame, column: str | None, values: list[str] | str | None) -> pd.DataFrame:
    """Filter a dataframe by one optional column/value set."""

    if df is None or column is None or column not in df.columns or values is None:
        return df
    if isinstance(values, str):
        values = [values]
    return df.loc[df[column].astype(str).isin([str(value) for value in values])].copy()


def norm_text(value: object) -> str:
    """Normalize text for metric alias matching."""

    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def slug(value: object) -> str:
    """Return a filename-safe short slug."""

    text = str(value).strip()
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    return text[:80] or "unknown"


def psa_period_label(period: float) -> str:
    """Format one PSA oscillator period label."""

    period = float(period)
    return f"T={period:g} s (f={1.0 / period:g} Hz)" if np.isfinite(period) and period > 0 else "PSA period unknown"


def reload_metric_plot_modules() -> dict[str, Callable[..., Any]]:
    """Reload and return plotting functions used by large-run notebooks."""

    import spatial_vtk.metrics.plot.model_comparison as model_plots
    import spatial_vtk.metrics.plot.periods as period_plots
    import spatial_vtk.metrics.plot.site_terms as site_plots
    import spatial_vtk.metrics.plot.trends as trend_plots
    import spatial_vtk.spatial.map.metrics as metric_maps
    import spatial_vtk.spatial.map.path.residuals as path_maps
    import spatial_vtk.spatial.plot.metrics as spatial_metric_plots

    for module in [model_plots, period_plots, site_plots, trend_plots, metric_maps, path_maps, spatial_metric_plots]:
        importlib.reload(module)
    return {
        "plot_band_score_distribution": model_plots.plot_band_score_distribution,
        "plot_period_spectra": period_plots.plot_period_spectra,
        "plot_period_score_distribution": period_plots.plot_period_score_distribution,
        "plot_psa_period_curve": period_plots.plot_psa_period_curve,
        "plot_geology_boxplot": site_plots.plot_geology_boxplot,
        "plot_vs30_scatter": site_plots.plot_vs30_scatter,
        "plot_metric_trend": trend_plots.plot_metric_trend,
        "plot_phase_delay_vs_distance": trend_plots.plot_phase_delay_vs_distance,
        "plot_residuals_vs_depth": trend_plots.plot_residuals_vs_depth,
        "plot_residuals_vs_distance": trend_plots.plot_residuals_vs_distance,
        "plot_score_trends": trend_plots.plot_score_trends,
        "plot_metric_map_by_model": metric_maps.plot_metric_map_by_model,
        "plot_residual_grid": metric_maps.plot_residual_grid,
        "plot_station_metric_map": metric_maps.plot_station_metric_map,
        "plot_station_metric_map_by_period": metric_maps.plot_station_metric_map_by_period,
        "plot_event_residual_map": path_maps.plot_event_residual_map,
        "boxplot": spatial_metric_plots.boxplot,
        "heatmap": spatial_metric_plots.heatmap,
        "scatterplot": spatial_metric_plots.scatterplot,
    }


def _table_columns(path: str | Path) -> list[str]:
    """Return table columns without reading full row data when possible."""

    input_path = Path(path).expanduser()
    suffix = input_path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        try:
            import pyarrow.parquet as pq

            return list(pq.ParquetFile(input_path).schema.names)
        except Exception:
            return list(pd.read_parquet(input_path).head(0).columns)
    return list(pd.read_csv(input_path, nrows=0).columns)


def _read_metric_figure_table(path: str | Path, *, columns: list[str]) -> pd.DataFrame:
    """Read only columns needed by large-run metric figures."""

    input_path = Path(path).expanduser()
    suffix = input_path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        try:
            return pd.read_parquet(input_path, columns=columns)
        except Exception:
            frame = pd.read_parquet(input_path)
            return frame.reindex(columns=[column for column in columns if column in frame.columns])
    wanted = set(columns)
    return pd.read_csv(input_path, usecols=lambda column: column in wanted, low_memory=False)


def _metric_figure_columns(available_columns: list[str], *, value_col: str) -> list[str]:
    """Return the metric columns needed by all large-run figure cells."""

    wanted = {
        value_col,
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
        "distance",
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
        "Vs30",
        "vs30",
        "VS30",
        "site_vs30",
        "station_vs30",
        "vs30_mps",
        "Vs30_mps",
        "station_region",
        "station_geojson_region",
        "station_geojson_labels",
        "event_region",
        "event_geojson_region",
        "event_geojson_labels",
    }
    return [column for column in available_columns if column in wanted]


def _sample_rows(df: pd.DataFrame, *, n: int) -> pd.DataFrame:
    """Return all rows or a deterministic sample."""

    if len(df) <= n:
        return df.copy()
    return df.sample(n=n, random_state=42).copy()


def _ordered_existing_columns(df: pd.DataFrame, columns: Iterable[str | None]) -> list[str]:
    """Return existing columns once, preserving caller order."""

    out: list[str] = []
    for column in columns:
        if column and column in df.columns and column not in out:
            out.append(column)
    return out


def _station_coordinate_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    """Resolve station longitude and latitude columns from supported schemas."""

    lon = next((column for column in ("sta_lon", "lon", "station_lon", "station_longitude") if column in df.columns), None)
    lat = next((column for column in ("sta_lat", "lat", "station_lat", "station_latitude") if column in df.columns), None)
    return lon, lat


def _station_identifier_column(df: pd.DataFrame) -> str | None:
    """Resolve the station identifier column from supported schemas."""

    return next((column for column in ("station", "station_id", "station_code") if column in df.columns), None)


def _event_identifier_column(df: pd.DataFrame) -> str | None:
    """Resolve the event identifier column from supported schemas."""

    return next((column for column in ("event_id", "event", "event_title") if column in df.columns), None)


def _station_group_columns(
    df: pd.DataFrame,
    *,
    station_col: str | None,
    lon_col: str,
    lat_col: str,
    extra_group_cols: Iterable[str | None] | None,
) -> list[str]:
    """Return station-summary grouping columns without splitting by coordinates."""

    base_columns = [station_col] if station_col is not None else [lon_col, lat_col]
    return _ordered_existing_columns(df, [*base_columns, *(extra_group_cols or [])])


def _station_coordinate_summary(grouped: Any, *, lon_col: str, lat_col: str) -> pd.DataFrame:
    """Summarize station coordinates for grouped event-level rows."""

    lon_summary = grouped[lon_col].agg(_representative_coordinate).rename(lon_col)
    lat_summary = grouped[lat_col].agg(_representative_coordinate).rename(lat_col)
    coordinate_counts = grouped[[lon_col, lat_col]].apply(_coordinate_pair_count).rename("source_coordinate_count")
    return pd.concat([lon_summary, lat_summary, coordinate_counts], axis=1)


def _representative_coordinate(values: pd.Series) -> float | object:
    """Return a stable representative coordinate for one station group."""

    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if not numeric.empty:
        return float(numeric.median())
    non_null = values.dropna()
    return np.nan if non_null.empty else non_null.iloc[0]


def _coordinate_pair_count(rows: pd.DataFrame) -> int:
    """Count distinct coordinate pairs in one station group."""

    if rows.empty:
        return 0
    return int(rows.dropna(how="all").drop_duplicates().shape[0])


def _rename_station_coordinates(df: pd.DataFrame, *, lon_col: str, lat_col: str) -> pd.DataFrame:
    """Return a copy with canonical station coordinate names for plotting."""

    rename: dict[str, str] = {}
    if lon_col != "sta_lon":
        rename[lon_col] = "sta_lon"
    if lat_col != "sta_lat":
        rename[lat_col] = "sta_lat"
    return df.rename(columns=rename) if rename else df


def _rename_station_identifier(df: pd.DataFrame, *, station_col: str | None) -> pd.DataFrame:
    """Return a copy with a canonical station identifier column for plotting."""

    if station_col is None or station_col == "station" or "station" in df.columns:
        return df
    return df.rename(columns={station_col: "station"})


def _finite_value_rows(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Return rows with finite numeric values in ``value_col``."""

    out = df.copy()
    values = pd.to_numeric(out[value_col], errors="coerce")
    out[value_col] = values
    return out.loc[np.isfinite(values)].copy()


def _input_group_counts(df: pd.DataFrame, group_cols: list[str], *, event_col: str | None) -> pd.DataFrame:
    """Count selected rows before finite-value filtering for aggregation audit."""

    if not group_cols or not set(group_cols) <= set(df.columns):
        return pd.DataFrame()
    grouped = df.groupby(group_cols, dropna=False)
    out = grouped.size().reset_index(name="input_row_count")
    if event_col is not None and event_col in df.columns:
        event_counts = grouped[event_col].nunique(dropna=True).reset_index(name="input_event_count")
        out = out.merge(event_counts, on=group_cols, how="left")
    return out


def _add_station_aggregation_drop_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Add per-group finite-value drop counts to station summary rows."""

    out = df.copy()
    if {"input_row_count", "source_row_count"} <= set(out.columns):
        out["dropped_nonfinite_row_count"] = (
            pd.to_numeric(out["input_row_count"], errors="coerce").fillna(0)
            - pd.to_numeric(out["source_row_count"], errors="coerce").fillna(0)
        ).clip(lower=0).astype(int)
    if {"input_event_count", "source_event_count"} <= set(out.columns):
        out["dropped_nonfinite_event_count"] = (
            pd.to_numeric(out["input_event_count"], errors="coerce").fillna(0)
            - pd.to_numeric(out["source_event_count"], errors="coerce").fillna(0)
        ).clip(lower=0).astype(int)
    return out


def _aggregate_grouped_values(grouped: Any, aggregation: str) -> pd.Series:
    """Aggregate one grouped numeric series using a supported statistic."""

    method = str(aggregation or "median").lower()
    if method in {"median", "mean", "min", "max", "sum"}:
        return getattr(grouped, method)()
    if method == "p05":
        return grouped.quantile(0.05)
    if method == "p10":
        return grouped.quantile(0.10)
    if method == "p90":
        return grouped.quantile(0.90)
    if method == "p95":
        return grouped.quantile(0.95)
    raise ValueError(
        "station_aggregation must be one of: median, mean, min, max, sum, p05, p10, p90, p95"
    )


def _station_aggregation_attrs(
    *,
    value_col: str,
    method: str,
    group_cols: list[str],
    coordinate_cols: tuple[str, str],
    source_rows: pd.DataFrame,
    finite_rows: pd.DataFrame,
) -> dict[str, Any]:
    """Return dataframe metadata describing a station-summary aggregation."""

    lon_col, lat_col = coordinate_cols
    input_stations = _unique_count(source_rows, ("station", "station_id", "station_code"))
    finite_stations = _unique_count(finite_rows, ("station", "station_id", "station_code"))
    input_events = _unique_count(source_rows, ("event_id", "event", "event_title"))
    finite_events = _unique_count(finite_rows, ("event_id", "event", "event_title"))
    return {
        "svtk_aggregation_kind": "station_event_rows_to_station_summary",
        "svtk_aggregation_value_col": value_col,
        "svtk_aggregation_method": str(method or "median").lower(),
        "svtk_aggregation_group_columns": list(group_cols),
        "svtk_aggregation_coordinate_columns": [lon_col, lat_col],
        "svtk_aggregation_input_row_count": int(len(source_rows)),
        "svtk_aggregation_finite_row_count": int(len(finite_rows)),
        "svtk_aggregation_dropped_nonfinite_row_count": int(len(source_rows) - len(finite_rows)),
        "svtk_aggregation_input_station_count": input_stations,
        "svtk_aggregation_finite_station_count": finite_stations,
        "svtk_aggregation_input_event_count": input_events,
        "svtk_aggregation_finite_event_count": finite_events,
    }


def _unique_count(df: pd.DataFrame, candidates: Iterable[str]) -> int | None:
    """Return the unique count for the first present candidate column."""

    column = next((candidate for candidate in candidates if candidate in df.columns), None)
    if column is None:
        return None
    return int(df[column].nunique(dropna=True))


__all__ = [
    "MetricFigureContext",
    "TARGET_METRIC_SPECS",
    "dimension_value",
    "filter_optional",
    "first_existing",
    "first_value",
    "norm_text",
    "prepare_large_run_metric_figure_context",
    "psa_period_label",
    "reload_metric_plot_modules",
    "slug",
]
