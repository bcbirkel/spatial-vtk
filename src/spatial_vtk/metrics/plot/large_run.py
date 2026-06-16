"""Large-run metric plotting orchestration helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import importlib
import re
from tempfile import TemporaryDirectory
from typing import Any, Callable

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


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
        metrics = pd.read_parquet(path)
        context.metrics_for_figures = metrics
        context.metric_col = first_existing(metrics, ["metric"])
        context.band_col = first_existing(metrics, ["band", "passband"])
        context.model_col = first_existing(metrics, ["model"])
        context.component_col = first_existing(metrics, ["component"])
        context.period_col = first_existing(metrics, ["period_s"])
        context.distance_col = first_existing(metrics, ["distance_km"])
        context.depth_col = first_existing(metrics, ["depth_km"])
        context.vs30_col = first_existing(metrics, ["Vs30", "vs30", "VS30", "site_vs30", "station_vs30", "vs30_mps", "Vs30_mps"])
        if context.value_col not in metrics.columns:
            print(f"Cannot render metric figures: {context.value_col!r} is not present in metrics_long.")
            return context
        context.ready = True
        limit_text = "no per-figure row limit" if context.sample_rows <= 0 else f"up to {context.sample_rows:,} raw row(s) per figure"
        print(f"Rendering metric figures from {len(metrics):,} metric row(s) into {output_dir}; {limit_text}")
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
            print(f"Figure sidecars enabled: {sidecar_dir} ({rows_text})")
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
        context.depth_col = first_existing(metrics, ["depth_km"])
        context.vs30_col = first_existing(
            metrics,
            ["Vs30", "vs30", "VS30", "site_vs30", "station_vs30", "vs30_mps", "Vs30_mps"],
        )
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

    def station_summary_for_map(self, df: pd.DataFrame, value_col: str | None = None) -> pd.DataFrame:
        """Aggregate all selected metric rows to one plotted value per station."""

        resolved_value_col = self.value_col if value_col is None else value_col
        if not all(column in df.columns for column in ["station", "sta_lon", "sta_lat", resolved_value_col]):
            return df
        group_cols = ["station", "sta_lon", "sta_lat"]
        context_cols = [column for column in [self.metric_col, self.band_col, self.model_col, self.component_col, self.period_col] if column and column in df.columns]
        grouped = df.groupby(group_cols, dropna=False)
        values = _aggregate_grouped_values(grouped[resolved_value_col], self.station_aggregation).reset_index(name=resolved_value_col)
        counts = grouped.size().reset_index(name="source_row_count")
        summary = values.merge(counts, on=group_cols, how="left")
        if "event_id" in df.columns:
            event_counts = grouped["event_id"].nunique(dropna=True).reset_index(name="source_event_count")
            summary = summary.merge(event_counts, on=group_cols, how="left")
        for column in context_cols:
            summary[column] = dimension_value(df, column, self.context_multi_label(column))
        summary["aggregation"] = self.station_aggregation
        return summary

    def station_period_summary_for_map(self, df: pd.DataFrame, value_col: str | None = None) -> pd.DataFrame:
        """Aggregate all selected PSA rows to one plotted value per station and period."""

        resolved_value_col = self.value_col if value_col is None else value_col
        if self.period_col is None or self.period_col not in df.columns:
            return self.station_summary_for_map(df, value_col=resolved_value_col)
        if not all(column in df.columns for column in ["station", "sta_lon", "sta_lat", self.period_col, resolved_value_col]):
            return df
        group_cols = ["station", "sta_lon", "sta_lat", self.period_col]
        context_cols = [column for column in [self.metric_col, self.band_col, self.model_col, self.component_col] if column and column in df.columns]
        grouped = df.groupby(group_cols, dropna=False)
        values = _aggregate_grouped_values(grouped[resolved_value_col], self.station_aggregation).reset_index(name=resolved_value_col)
        counts = grouped.size().reset_index(name="source_row_count")
        summary = values.merge(counts, on=group_cols, how="left")
        if "event_id" in df.columns:
            event_counts = grouped["event_id"].nunique(dropna=True).reset_index(name="source_event_count")
            summary = summary.merge(event_counts, on=group_cols, how="left")
        for column in context_cols:
            summary[column] = dimension_value(df, column, self.context_multi_label(column))
        summary["aggregation"] = self.station_aggregation
        return summary

    def write_metric_plot(
        self,
        base: str,
        item: dict[str, Any],
        func: Callable[..., Any],
        df: pd.DataFrame | None = None,
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
            self.write_figure_sidecar(output, plot_df)
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
            self.write_figure_sidecar(output, plot_df)
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
                required=required,
                value_col=resolved_value_col,
                forward_value_col=forward_value_col,
                showfig=showfig,
                **kwargs,
            )
        output = self.figure_dir / f"{self.figure_name(base, item, resolved_value_col)}.png"
        if output.exists() and not self.overwrite:
            print(f"skip {output.name}: exists")
            self.write_figure_sidecar(output, self.plot_rows(df_factory(item) if df_factory else item["df"]))
            return output
        ncols = min(3, max(1, len(period_items)))
        nrows = int(np.ceil(len(period_items) / ncols))
        fig, axes = plt.subplots(nrows, ncols, figsize=(5.8 * ncols, 4.7 * nrows), dpi=160, squeeze=False)
        axes_flat = axes.ravel()
        sidecar_frames: list[pd.DataFrame] = []
        with TemporaryDirectory() as tmpdir_raw:
            tmpdir = Path(tmpdir_raw)
            for ax, period_item in zip(axes_flat, period_items):
                plot_df = self.plot_rows(df_factory(period_item) if df_factory else period_item["df"])
                sidecar_frames.append(plot_df.assign(__svtk_panel_period_s=period_item.get("period_s")))
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
            self.write_figure_sidecar(output, pd.concat(sidecar_frames, ignore_index=True, sort=False))
        if showfig:
            plt.show()
        plt.close(fig)
        print(f"wrote {output}")
        return output

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

    def write_figure_sidecar(self, figure_path: str | Path, df: pd.DataFrame) -> Path | None:
        """Optionally write a CSV and metadata file for rows used by one figure."""

        if not self.write_sidecars:
            return None
        sidecar_dir = self.sidecar_output_dir
        sidecar_dir.mkdir(parents=True, exist_ok=True)
        figure = Path(figure_path)
        sidecar_path = sidecar_dir / f"{figure.stem}.csv"
        rows = df
        sampled = False
        if self.sidecar_rows is not None and self.sidecar_rows > 0 and len(rows) > self.sidecar_rows:
            rows = _sample_rows(rows, n=self.sidecar_rows)
            sampled = True
        rows.to_csv(sidecar_path, index=False)
        metadata = {
            "figure": str(figure),
            "sidecar": str(sidecar_path),
            "source_row_count": int(len(df)),
            "written_row_count": int(len(rows)),
            "sampled": bool(sampled),
            "value_col": self.value_col,
            "station_aggregation": self.station_aggregation,
        }
        sidecar_path.with_suffix(".json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        return sidecar_path

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


def _sample_rows(df: pd.DataFrame, *, n: int) -> pd.DataFrame:
    """Return all rows or a deterministic sample."""

    if len(df) <= n:
        return df.copy()
    return df.sample(n=n, random_state=42).copy()


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
