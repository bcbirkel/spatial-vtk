"""Large-run metric plotting orchestration helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import inspect
import re
from tempfile import TemporaryDirectory
from typing import Any, Callable, Iterable, Sequence

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from spatial_vtk.visualize.figure_context import value_requires_model
from spatial_vtk.visualize.figure_sidecars import write_figure_row_sidecar


TARGET_METRIC_SPECS = (
    {"key": "arias_duration", "label": "Arias duration", "aliases": ("Arias duration", "Arias duration (5-95%)", "arias_duration", "AD")},
    {"key": "pga", "label": "PGA", "aliases": ("PGA", "Peak acceleration", "Peak ground acceleration")},
    {"key": "pgv", "label": "PGV", "aliases": ("PGV", "Peak velocity", "Peak ground velocity")},
    {"key": "psa", "label": "PSA", "aliases": ("PSA", "Pseudo-spectral acceleration", "Pseudo spectral acceleration")},
    {"key": "traveltime_delay", "label": "Traveltime delay", "aliases": ("traveltime delay", "travel time delay", "travel-time delay", "TT delay", "traveltime")},
    {"key": "cav", "label": "CAV", "aliases": ("CAV", "Cumulative absolute velocity")},
)
DEFAULT_SCORE_TREND_COLUMNS = ("anderson_2004_gof", "olsen_mayhew_gof", "score")
BROADBAND_PASSBAND_LABELS = frozenset({"", "all", "broadband", "none", "nan"})
SPECTRAL_CONTRACT_METRICS = (
    ("PSA", ("PSA", "Pseudo-spectral acceleration", "Pseudo spectral acceleration")),
    ("FAS", ("FAS", "Fourier amplitude spectrum", "Fourier amplitude spectra")),
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

    def status_frame(self) -> pd.DataFrame:
        """Return a compact status table for this metric figure context.

        The table is designed for notebooks: it records the configured input and
        output paths, filter defaults, loaded row/column counts, and sidecar
        settings without reading any additional large files.
        """

        rows = [
            ("ready", self.ready),
            ("make_figures", self.make_figures),
            (
                "metrics_long_path",
                None if str(self.metrics_long_path) == "." else str(self.metrics_long_path),
            ),
            ("figure_dir", str(self.figure_dir)),
            ("selected_metric_rows", int(len(self.metrics_for_figures))),
            ("available_column_count", int(len(self.available_columns))),
            ("loaded_column_count", int(len(self.loaded_columns))),
            ("value_col", self.value_col),
            ("default_passband", self.default_passband),
            ("default_components", _preview_values(self.default_components)),
            ("default_model", self.default_model),
            ("sample_rows_per_figure", None if self.sample_rows <= 0 else int(self.sample_rows)),
            ("station_aggregation", self.station_aggregation),
            ("write_sidecars", self.write_sidecars),
            ("sidecar_dir", str(self.sidecar_output_dir) if self.write_sidecars else None),
            ("sidecar_rows", "all" if self.sidecar_rows is None or self.sidecar_rows <= 0 else int(self.sidecar_rows)),
        ]
        spectral_status = self.spectral_metric_contract_status()
        if not spectral_status.empty:
            aggregate = _aggregate_spectral_contract_status(spectral_status)
            rows.extend(
                [
                    ("spectral_contract_status", aggregate["status"]),
                    ("spectral_contract_message", aggregate["message"]),
                ]
            )
            for _, spectral_row in spectral_status.iterrows():
                metric_key = slug(str(spectral_row["metric"]))
                rows.extend(
                    [
                        (f"{metric_key}_metric_rows", int(spectral_row["row_count"])),
                        (f"{metric_key}_broadband_rows", int(spectral_row["broadband_row_count"])),
                        (f"{metric_key}_legacy_passband_rows", int(spectral_row["legacy_passband_row_count"])),
                        (f"{metric_key}_period_count", int(spectral_row["period_count"])),
                    ]
                )
        return pd.DataFrame(rows, columns=["name", "value"])

    def spectral_metric_contract_status(self) -> pd.DataFrame:
        """Return PSA/FAS broadband-passband contract status for notebook audits.

        Spectral metrics should be calculated once per event/station/component
        and model with a blank passband, then split by oscillator period in
        ``period_s``. This status frame lets notebooks surface legacy
        passband-scoped PSA/FAS rows before plotting silently skips them.
        """

        df = self.metrics_for_figures
        columns = [
            "metric",
            "row_count",
            "broadband_row_count",
            "legacy_passband_row_count",
            "period_count",
            "status",
            "message",
        ]
        if df.empty or self.metric_col is None or self.metric_col not in df.columns:
            return pd.DataFrame(columns=columns)
        rows: list[dict[str, Any]] = []
        for metric, aliases in SPECTRAL_CONTRACT_METRICS:
            metric_rows = df.loc[self.metric_mask(df, aliases)].copy()
            row_count = int(len(metric_rows))
            if row_count == 0:
                rows.append(
                    {
                        "metric": metric,
                        "row_count": 0,
                        "broadband_row_count": 0,
                        "legacy_passband_row_count": 0,
                        "period_count": 0,
                        "status": "not_present",
                        "message": f"{metric} rows are not present in the selected metric figure rows.",
                    }
                )
                continue
            period_count = (
                int(pd.to_numeric(metric_rows[self.period_col], errors="coerce").dropna().nunique())
                if self.period_col is not None and self.period_col in metric_rows.columns
                else 0
            )
            if self.band_col is None or self.band_col not in metric_rows.columns:
                rows.append(
                    {
                        "metric": metric,
                        "row_count": row_count,
                        "broadband_row_count": 0,
                        "legacy_passband_row_count": 0,
                        "period_count": period_count,
                        "status": "missing_passband_column",
                        "message": f"{metric} rows cannot be checked because no passband/band column is loaded.",
                    }
                )
                continue
            broadband = _broadband_passband_mask(metric_rows[self.band_col])
            broadband_count = int(broadband.sum())
            legacy_count = int(row_count - broadband_count)
            if legacy_count == 0:
                status = "ok"
                message = f"{metric} rows use blank/broadband passbands and oscillator periods in period_s."
            elif broadband_count == 0:
                status = "legacy_passband_rows"
                message = (
                    f"{metric} rows are passband-scoped. Rebuild the metric manifest and metric rows so "
                    f"{metric} is calculated once with a blank passband and split by period_s."
                )
            else:
                status = "mixed_passband_rows"
                message = (
                    f"{metric} rows mix broadband and passband-scoped records. Rebuild metric rows before "
                    "using large-run spectral plots."
                )
            rows.append(
                {
                    "metric": metric,
                    "row_count": row_count,
                    "broadband_row_count": broadband_count,
                    "legacy_passband_row_count": legacy_count,
                    "period_count": period_count,
                    "status": status,
                    "message": message,
                }
            )
        return pd.DataFrame(rows, columns=columns)

    def dimension_summary_frame(self, *, value_col: str | None = None) -> pd.DataFrame:
        """Summarize selected metric rows by common plotting dimensions.

        This is a lightweight audit table for large-run plotting cells. It helps
        users verify that the figure context is using the expected metrics,
        passbands, components, models, events, and stations before rendering many
        figures.
        """

        df = self.metrics_for_figures
        resolved_value_col = self.value_col if value_col is None else value_col
        dimension_specs = [
            ("metric", self.metric_col),
            ("passband", self.band_col),
            ("component", self.component_col),
            ("model", self.model_col),
            ("psa_period_s", self.period_col),
            ("event", first_existing(df, ["event_id", "event", "event_title"])),
            ("station", first_existing(df, ["station", "station_id", "station_code"])),
        ]
        rows: list[dict[str, Any]] = []
        for label, column in dimension_specs:
            if column is None or column not in df.columns:
                rows.append(
                    {
                        "dimension": label,
                        "column": column,
                        "unique_count": None,
                        "non_null_rows": 0,
                        "finite_value_rows": 0,
                        "values_preview": None,
                    }
                )
                continue
            values = df[column]
            finite_value_rows = 0
            if resolved_value_col in df.columns:
                value_rows = pd.to_numeric(df.loc[values.notna(), resolved_value_col], errors="coerce")
                finite_value_rows = int(np.isfinite(value_rows).sum())
            rows.append(
                {
                    "dimension": label,
                    "column": column,
                    "unique_count": int(values.nunique(dropna=True)),
                    "non_null_rows": int(values.notna().sum()),
                    "finite_value_rows": finite_value_rows,
                    "values_preview": _preview_values(values.dropna().unique()),
                }
            )
        return pd.DataFrame(rows)

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

    def metric_item(
        self,
        metric: str,
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        split_psa_period: bool = False,
    ) -> dict[str, Any]:
        """Return one configured metric item by key, label, or alias.

        This is intended for tutorial cells that need one named figure without
        hand-building the metric subset in notebook code.
        """

        wanted = norm_text(metric)
        matches: list[dict[str, Any]] = []
        for item in self.iter_metric_frames(
            passband=passband,
            components=components,
            model=model,
            split_psa_period=split_psa_period,
        ):
            spec = _target_metric_spec(item["key"])
            names = {item["key"], item["label"], item["metric"], *(spec.get("aliases", ()) if spec else ())}
            if wanted in {norm_text(name) for name in names}:
                matches.append(item)
        if not matches:
            raise ValueError(f"No metric rows matched {metric!r}.")
        if len(matches) > 1:
            raise ValueError(
                f"Metric {metric!r} matched {len(matches)} figure items. "
                "Pass more specific filters or set split_psa_period=False."
            )
        return matches[0]

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
                collapsed_cols=context_cols,
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
                collapsed_cols=context_cols,
                source_rows=df,
                finite_rows=finite_df,
            )
        )
        return summary

    def item_source_rows(self, item: dict[str, Any]) -> pd.DataFrame:
        """Return the metric rows represented by one figure item."""

        return item["df"]

    def station_summary_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate one figure item's rows to one plotted value per station."""

        return self.station_summary_for_map(
            self.item_source_rows(item),
            value_col=value_col,
            extra_group_cols=extra_group_cols,
        )

    def station_summary_for_metric(
        self,
        metric: str,
        value_col: str | None = None,
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
    ) -> pd.DataFrame:
        """Aggregate one named metric to station rows for notebook previews."""

        item = self.metric_item(metric, passband=passband, components=components, model=model)
        if item["key"] == "psa" and self.period_col in item["df"].columns:
            return self.station_period_summary_for_item(item, value_col=value_col)
        return self.station_summary_for_item(item, value_col=value_col)

    def station_summary_preview_for_metric(
        self,
        metric: str,
        value_col: str | None = None,
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        nrows: int = 5,
        columns: Iterable[str] | None = None,
    ) -> pd.DataFrame:
        """Return a bounded station-summary preview for one named metric.

        This is intended for notebook displays after station aggregation. It
        uses the same metric selection, PSA handling, and aggregation path as
        :meth:`station_summary_for_metric`, then returns only available preview
        columns and a bounded number of rows.
        """

        summary = self.station_summary_for_metric(
            metric,
            value_col=value_col,
            passband=passband,
            components=components,
            model=model,
        )
        requested = list(
            columns
            or (
                "station",
                "period_s",
                value_col or self.value_col,
                "source_row_count",
                "source_event_count",
                "aggregation",
            )
        )
        available = [column for column in requested if column and column in summary.columns]
        if not available:
            return summary.head(max(int(nrows), 0)).reset_index(drop=True)
        return summary.loc[:, available].head(max(int(nrows), 0)).reset_index(drop=True)

    def station_period_summary_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate one PSA figure item's rows to one plotted value per station and period."""

        return self.station_period_summary_for_map(
            self.item_source_rows(item),
            value_col=value_col,
            extra_group_cols=extra_group_cols,
        )

    def station_grid_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate one figure item and expose station coordinates as lon/lat."""

        return _station_summary_grid_columns(
            self.station_summary_for_item(
                item,
                value_col=value_col,
                extra_group_cols=extra_group_cols,
            )
        )

    def station_period_grid_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
        *,
        extra_group_cols: Iterable[str | None] | None = None,
    ) -> pd.DataFrame:
        """Aggregate one PSA figure item by station/period and expose lon/lat columns."""

        return _station_summary_grid_columns(
            self.station_period_summary_for_item(
                item,
                value_col=value_col,
                extra_group_cols=extra_group_cols,
            )
        )

    def station_model_summary_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
    ) -> pd.DataFrame:
        """Aggregate one figure item by station and model."""

        return self.station_summary_for_item(item, value_col=value_col, extra_group_cols=[self.model_col])

    def station_model_grid_for_item(
        self,
        item: dict[str, Any],
        value_col: str | None = None,
    ) -> pd.DataFrame:
        """Aggregate one figure item by station/model and expose lon/lat columns."""

        return self.station_grid_for_item(item, value_col=value_col, extra_group_cols=[self.model_col])

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
                df=_call_item_dataframe_factory(df_factory, item, value_col=resolved_value_col) if df_factory else None,
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
            sidecar_df, source_sidecar_df = self.psa_period_sheet_sidecar_rows(
                item,
                df_factory=df_factory,
                source_df_factory=source_df_factory,
                value_col=resolved_value_col,
            )
            self.write_figure_sidecar(
                output,
                sidecar_df,
                source_df=source_sidecar_df,
            )
            return output
        ncols = min(3, max(1, len(period_items)))
        nrows = int(np.ceil(len(period_items) / ncols))
        fig, axes = plt.subplots(nrows, ncols, figsize=(5.8 * ncols, 4.7 * nrows), dpi=160, squeeze=False)
        axes_flat = axes.ravel()
        with TemporaryDirectory() as tmpdir_raw:
            tmpdir = Path(tmpdir_raw)
            for ax, period_item in zip(axes_flat, period_items):
                plot_df = self.plot_rows(
                    _call_item_dataframe_factory(df_factory, period_item, value_col=resolved_value_col)
                    if df_factory
                    else period_item["df"]
                )
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
        sidecar_df, source_sidecar_df = self.psa_period_sheet_sidecar_rows(
            item,
            df_factory=df_factory,
            source_df_factory=source_df_factory,
            value_col=resolved_value_col,
        )
        self.write_figure_sidecar(output, sidecar_df, source_df=source_sidecar_df)
        if showfig:
            plt.show()
        plt.close(fig)
        print(f"wrote {output}")
        return output

    def write_residuals_vs_distance_plots(
        self,
        residuals_vs_distance_func: Callable[..., Any],
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        value_col: str | None = None,
        showfig: bool | None = None,
        robust_axis_percentile: float | None = None,
    ) -> list[Path]:
        """Write residual-vs-distance figures for all configured target metrics."""

        resolved_value_col = self.value_col if value_col is None else value_col
        outputs: list[Path] = []
        if not self._can_render_metric_figures("residuals_vs_distance", resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            writer = self.write_psa_period_sheet if item["key"] == "psa" else self.write_metric_plot
            output = writer(
                "residuals_vs_distance",
                item,
                residuals_vs_distance_func,
                required=[self.distance_col, resolved_value_col],
                y_col=resolved_value_col,
                group_col=self.component_col,
                fit="lowess",
                connect_points=False,
                robust_axis_percentile=self._resolved_robust_axis_percentile(robust_axis_percentile),
                showfig=self._resolved_showfig(showfig),
            )
            if output is not None:
                outputs.append(output)
        return outputs

    def write_residuals_vs_depth_plots(
        self,
        residuals_vs_depth_func: Callable[..., Any],
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        value_col: str | None = None,
        showfig: bool | None = None,
        robust_axis_percentile: float | None = None,
    ) -> list[Path]:
        """Write residual-vs-depth figures for all configured target metrics."""

        resolved_value_col = self.value_col if value_col is None else value_col
        outputs: list[Path] = []
        if not self._can_render_metric_figures("residuals_vs_depth", resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            writer = self.write_psa_period_sheet if item["key"] == "psa" else self.write_metric_plot
            output = writer(
                "residuals_vs_depth",
                item,
                residuals_vs_depth_func,
                required=[self.depth_col, resolved_value_col],
                y_col=resolved_value_col,
                group_col=self.component_col,
                fit="lowess",
                connect_points=False,
                robust_axis_percentile=self._resolved_robust_axis_percentile(robust_axis_percentile),
                showfig=self._resolved_showfig(showfig),
            )
            if output is not None:
                outputs.append(output)
        return outputs

    def write_vs30_scatter_plots(
        self,
        vs30_scatter_func: Callable[..., Any],
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        value_col: str | None = None,
        showfig: bool | None = None,
        robust_axis_percentile: float | None = None,
    ) -> list[Path]:
        """Write Vs30 scatter figures for all configured target metrics."""

        resolved_value_col = self.value_col if value_col is None else value_col
        outputs: list[Path] = []
        if not self._can_render_metric_figures("vs30_scatter", resolved_value_col):
            return outputs
        if self.vs30_col is None:
            print("Skipping Vs30 figures: no Vs30 column found.")
            return outputs
        for item in self.iter_metric_frames(
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            writer = self.write_psa_period_sheet if item["key"] == "psa" else self.write_metric_plot
            output = writer(
                "vs30_scatter",
                item,
                vs30_scatter_func,
                required=[self.vs30_col, resolved_value_col],
                vs30_col=self.vs30_col,
                value_col=resolved_value_col,
                forward_value_col=True,
                group_col=self.component_col,
                fit="lowess",
                connect_points=False,
                robust_axis_percentile=self._resolved_robust_axis_percentile(robust_axis_percentile),
                showfig=self._resolved_showfig(showfig),
            )
            if output is not None:
                outputs.append(output)
        return outputs

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
        """Write station-level metric maps for all configured target metrics."""

        resolved_value_col = self.value_col if value_col is None else value_col
        outputs: list[Path] = []
        if not self._can_render_metric_figures("station_metric_map", resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            if item["key"] == "psa" and self.period_col in item["df"].columns:
                station_df = self.station_period_summary_for_item(item, resolved_value_col)
                output = self.write_metric_plot(
                    "station_metric_map",
                    item,
                    station_metric_map_by_period_func,
                    df=station_df,
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
                output = self.write_metric_plot(
                    "station_metric_map",
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

    def write_station_metric_map_for_metric(
        self,
        station_metric_map_func: Callable[..., Any],
        station_metric_map_by_period_func: Callable[..., Any],
        *,
        metric: str,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        value_col: str | None = None,
        add_basemap: bool | None = None,
        showfig: bool | None = None,
        title: str | None = None,
    ) -> Path | None:
        """Write one station-level map for a named metric.

        The plotted station rows are aggregated with
        :meth:`station_summary_for_metric`; the source-row sidecar contains the
        underlying event-station metric rows. Use this for focused tutorial
        figures that should not render the full target-metric figure suite.
        """

        resolved_value_col = self.value_col if value_col is None else value_col
        if not self._can_render_metric_figures("station_metric_map", resolved_value_col):
            return None
        item = self.metric_item(metric, passband=passband, components=components, model=model)
        plot_kwargs: dict[str, Any] = {}
        if title is not None:
            plot_kwargs["title"] = title
        if item["key"] == "psa" and self.period_col in item["df"].columns:
            station_df = self.station_period_summary_for_item(item, resolved_value_col)
            return self.write_metric_plot(
                "station_metric_map",
                item,
                station_metric_map_by_period_func,
                df=station_df,
                source_df=self.item_source_rows(item),
                required=["sta_lon", "sta_lat", self.period_col, resolved_value_col],
                value_col=resolved_value_col,
                forward_value_col=True,
                period_col=self.period_col,
                add_basemap=self._resolved_add_basemap(add_basemap),
                showfig=self._resolved_showfig(showfig),
                **plot_kwargs,
            )
        station_df = self.station_summary_for_item(item, resolved_value_col)
        return self.write_metric_plot(
            "station_metric_map",
            item,
            station_metric_map_func,
            df=station_df,
            source_df=self.item_source_rows(item),
            required=["sta_lon", "sta_lat", resolved_value_col],
            value_col=resolved_value_col,
            forward_value_col=True,
            add_basemap=self._resolved_add_basemap(add_basemap),
            showfig=self._resolved_showfig(showfig),
            **plot_kwargs,
        )

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

        resolved_value_col = self.value_col if value_col is None else value_col
        outputs: list[Path] = []
        if not self._can_render_metric_figures("residual_grid", resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            if item["key"] == "psa":
                output = self.write_psa_period_sheet(
                    "residual_grid",
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
                station_df = self.station_grid_for_item(item, resolved_value_col)
                output = self.write_metric_plot(
                    "residual_grid",
                    item,
                    residual_grid_func,
                    df=station_df,
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
        """Write faceted station metric maps split by model."""

        resolved_value_col = self.value_col if value_col is None else value_col
        outputs: list[Path] = []
        if not self._can_render_metric_figures("metric_by_model_map", resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            if item["key"] == "psa":
                output = self.write_psa_period_sheet(
                    "metric_by_model_map",
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
                output = self.write_metric_plot(
                    "metric_by_model_map",
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
        """Write event residual maps for all configured target metrics."""

        resolved_value_col = self.value_col if value_col is None else value_col
        outputs: list[Path] = []
        if not self._can_render_metric_figures("event_residual_map", resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            writer = self.write_psa_period_sheet if item["key"] == "psa" else self.write_metric_plot
            output = writer(
                "event_residual_map",
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

    def write_log2_residual_distribution_plots(
        self,
        band_score_distribution_func: Callable[..., Any],
        period_score_distribution_func: Callable[..., Any],
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        value_col: str | None = None,
        showfig: bool | None = None,
        robust_axis_percentile: float | None = None,
    ) -> list[Path]:
        """Write passband or PSA-period residual distribution figures."""

        resolved_value_col = self.value_col if value_col is None else value_col
        outputs: list[Path] = []
        if not self._can_render_metric_figures("log2_residual_distribution", resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            if item["key"] == "psa":
                output = self.write_metric_plot(
                    "period_log2_residual_distribution",
                    item,
                    period_score_distribution_func,
                    required=[self.period_col, resolved_value_col],
                    period_col=self.period_col,
                    score_col=resolved_value_col,
                    color_col=self.component_col,
                    robust_axis_percentile=self._resolved_robust_axis_percentile(robust_axis_percentile),
                    showfig=self._resolved_showfig(showfig),
                )
            else:
                output = self.write_metric_plot(
                    "band_log2_residual_distribution",
                    item,
                    band_score_distribution_func,
                    required=[self.band_col, resolved_value_col],
                    band_col=self.band_col,
                    score_col=resolved_value_col,
                    color_col=self.component_col,
                    robust_axis_percentile=self._resolved_robust_axis_percentile(robust_axis_percentile),
                    showfig=self._resolved_showfig(showfig),
                )
            if output is not None:
                outputs.append(output)
        return outputs

    def write_psa_period_curve_plots(
        self,
        psa_period_curve_func: Callable[..., Any],
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        value_col: str | None = None,
        showfig: bool | None = None,
        robust_axis_percentile: float | None = None,
    ) -> list[Path]:
        """Write PSA period-curve figures for selected PSA rows."""

        resolved_value_col = self.value_col if value_col is None else value_col
        outputs: list[Path] = []
        if not self._can_render_metric_figures("psa_period_curve", resolved_value_col):
            return outputs
        for item in self.iter_metric_frames(
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            if item["key"] != "psa":
                continue
            output = self.write_metric_plot(
                "psa_period_curve",
                item,
                psa_period_curve_func,
                required=[self.period_col, resolved_value_col],
                metric=None,
                period_col=self.period_col,
                value_col=resolved_value_col,
                forward_value_col=True,
                group_col=self.component_col,
                robust_axis_percentile=self._resolved_robust_axis_percentile(robust_axis_percentile),
                showfig=self._resolved_showfig(showfig),
            )
            if output is not None:
                outputs.append(output)
        return outputs

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
        compare_to: str | Sequence[str] | None = None,
        table: bool = False,
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
        for base_item in self.iter_metric_frames(
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            for item, item_model in self.diagnostic_model_items(base_item, value_col=resolved_value_col, model=model):
                outputs.extend(
                    self._write_generic_metric_diagnostic_item(
                        item,
                        scatterplot_func,
                        boxplot_func,
                        heatmap_func,
                        period_distribution_func,
                        passband=passband,
                        model=item_model,
                        value_col=resolved_value_col,
                        showfig=showfig,
                        compare_to=compare_to,
                        table=table,
                    )
                )
        return outputs

    def diagnostic_model_items(
        self,
        item: dict[str, Any],
        *,
        value_col: str | None,
        model: str | Sequence[str] | None = None,
    ) -> list[tuple[dict[str, Any], str | None]]:
        """Return model-specific items when a plotted value needs model context."""

        if model is not None or self.model_col is None or self.model_col not in item["df"].columns:
            return [(item, model if isinstance(model, str) else None)]
        if not value_requires_model(value_col, item["df"]):
            return [(item, None)]
        values = [str(value) for value in pd.unique(item["df"][self.model_col].dropna()) if str(value).strip()]
        if len(values) <= 1:
            return [(item, values[0] if values else None)]
        out: list[tuple[dict[str, Any], str | None]] = []
        for value in values:
            subset = item["df"].loc[item["df"][self.model_col].astype(str).eq(value)].copy()
            if subset.empty:
                continue
            split_item = dict(item)
            split_item["df"] = subset
            out.append((split_item, value))
        return out or [(item, None)]

    def _write_generic_metric_diagnostic_item(
        self,
        item: dict[str, Any],
        scatterplot_func: Callable[..., Any],
        boxplot_func: Callable[..., Any],
        heatmap_func: Callable[..., Any],
        period_distribution_func: Callable[..., Any],
        *,
        passband: str | None,
        model: str | None,
        value_col: str,
        showfig: bool,
        compare_to: str | Sequence[str] | None,
        table: bool,
    ) -> list[Path]:
        """Write generic diagnostic figures for one already filtered metric item."""

        outputs: list[Path] = []
        metric_name = self.first_value(item["df"], self.metric_col) or item.get("metric", item["label"])
        if item["key"] == "psa":
            output = self.write_psa_period_sheet(
                "scatterplot",
                item,
                scatterplot_func,
                required=[self.distance_col, value_col],
                indep=self.distance_col,
                dep=metric_name,
                value_col=value_col,
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
                required=[self.period_col, value_col],
                period_col=self.period_col,
                score_col=value_col,
                color_col=self.component_col,
                robust_axis_percentile=self.robust_axis_percentile,
                showfig=showfig,
            )
            if output is not None:
                outputs.append(output)
            print("skip heatmap for PSA: use the PSA period curve and period distribution figures instead of passband heatmaps")
            return outputs
        output = self.write_metric_plot(
            "scatterplot",
            item,
            scatterplot_func,
            required=[self.distance_col, value_col],
            indep=self.distance_col,
            dep=metric_name,
            value_col=value_col,
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
            required=[self.component_col, value_col] if self.component_col else [value_col],
            dep=metric_name,
            indep=self.component_col or self.model_col,
            value_col=value_col,
            forward_value_col=True,
            passband=passband,
            model=model,
            colorby=self.model_col if self.model_col in item["df"].columns else None,
            robust_axis_percentile=self.robust_axis_percentile,
            compare_to=compare_to,
            table=table,
            showfig=showfig,
        )
        if output is not None:
            outputs.append(output)
        output = self.write_metric_plot(
            "heatmap",
            item,
            heatmap_func,
            required=[value_col],
            dep=metric_name,
            indep=self.component_col or self.model_col,
            column=self.model_col if self.model_col in item["df"].columns else None,
            value_col=value_col,
            forward_value_col=True,
            passband=passband,
            model=model,
            showfig=showfig,
        )
        if output is not None:
            outputs.append(output)
        return outputs

    def write_score_trend_plots(
        self,
        score_trend_func: Callable[..., Any],
        *,
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        score_columns: Iterable[str] | None = None,
        showfig: bool = False,
    ) -> list[Path]:
        """Write GOF/score trend figures for each target metric.

        This mirrors the standard tutorial's score-trend figure while keeping
        large-run notebooks on the same context-managed path as other metric
        figures and sidecars.
        """

        if not self.ready:
            print("Skipping score trend figures: metric figure context is not ready.")
            return []
        candidates = tuple(score_columns or DEFAULT_SCORE_TREND_COLUMNS)
        available = [
            column
            for column in candidates
            if column in self.metrics_for_figures.columns
            and pd.to_numeric(self.metrics_for_figures[column], errors="coerce").notna().any()
        ]
        if not available:
            print(f"Skipping score trend figures: no finite score column found from {list(candidates)}")
            return []
        outputs: list[Path] = []
        for item in self.iter_metric_frames(
            passband=passband,
            components=components,
            model=model,
            split_psa_period=False,
        ):
            writer = self.write_psa_period_sheet if item["key"] == "psa" else self.write_metric_plot
            for score_col in available:
                output = writer(
                    "score_trends",
                    item,
                    score_trend_func,
                    required=[self.distance_col, score_col],
                    score_col=score_col,
                    group_col=self.component_col,
                    fit="lowess",
                    connect_points=False,
                    robust_axis_percentile=self.robust_axis_percentile,
                    value_col=score_col,
                    showfig=showfig,
                )
                if output is not None:
                    outputs.append(output)
        return outputs

    def _resolved_add_basemap(self, add_basemap: bool | None) -> bool:
        """Resolve an optional per-call basemap override."""

        return self.add_basemap if add_basemap is None else bool(add_basemap)

    def _resolved_showfig(self, showfig: bool | None) -> bool:
        """Resolve an optional per-call showfig override."""

        return self.default_showfig if showfig is None else bool(showfig)

    def _resolved_robust_axis_percentile(self, robust_axis_percentile: float | None) -> float:
        """Resolve an optional per-call robust-axis percentile override."""

        return self.robust_axis_percentile if robust_axis_percentile is None else float(robust_axis_percentile)

    def _can_render_metric_figures(self, label: str, value_col: str | None) -> bool:
        """Return whether a metric figure family can be rendered."""

        if not self.ready:
            print(f"Skipping {label}: metric figure context is not ready.")
            return False
        if value_col is None or value_col not in self.metrics_for_figures.columns:
            print(f"Skipping {label}: value column {value_col!r} is not present.")
            return False
        return True

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

    def psa_period_sheet_sidecar_rows(
        self,
        item: dict[str, Any],
        *,
        df_factory: Callable[[dict[str, Any]], pd.DataFrame] | None = None,
        source_df_factory: Callable[[dict[str, Any]], pd.DataFrame | None] | None = None,
        value_col: str | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame | None]:
        """Return plotted/source rows represented by a PSA period sheet."""

        resolved_value_col = self.value_col if value_col is None else value_col
        period_items = self.psa_period_items(item)
        if not period_items:
            plot_df = self.plot_rows(
                _call_item_dataframe_factory(df_factory, item, value_col=resolved_value_col)
                if df_factory
                else item["df"]
            )
            source_df = source_df_factory(item) if source_df_factory else None
            return plot_df, source_df
        sidecar_frames: list[pd.DataFrame] = []
        source_sidecar_frames: list[pd.DataFrame] = []
        for period_item in period_items:
            plot_df = self.plot_rows(
                _call_item_dataframe_factory(df_factory, period_item, value_col=resolved_value_col)
                if df_factory
                else period_item["df"]
            )
            panel_df = plot_df.assign(__svtk_panel_period_s=period_item.get("period_s"))
            panel_df.attrs.update(getattr(plot_df, "attrs", {}))
            sidecar_frames.append(panel_df)
            if source_df_factory is not None:
                source_rows = source_df_factory(period_item)
                if source_rows is not None:
                    source_sidecar_frames.append(source_rows.copy().assign(__svtk_panel_period_s=period_item.get("period_s")))
        sidecar_df = pd.concat(sidecar_frames, ignore_index=True, sort=False) if sidecar_frames else item["df"].iloc[0:0].copy()
        source_sidecar_df = pd.concat(source_sidecar_frames, ignore_index=True, sort=False) if source_sidecar_frames else None
        if any(getattr(frame, "attrs", {}).get("svtk_aggregation_kind") for frame in sidecar_frames):
            aggregation_frames = [frame for frame in sidecar_frames if getattr(frame, "attrs", {}).get("svtk_aggregation_kind")]
            first_attrs = getattr(aggregation_frames[0], "attrs", {}) if aggregation_frames else {}
            sidecar_df.attrs["svtk_aggregation_kind"] = "station_event_rows_to_station_summary_by_panel"
            sidecar_df.attrs["svtk_aggregation_panel_count"] = int(len(period_items))
            sidecar_df.attrs["svtk_aggregation_value_col"] = resolved_value_col
            sidecar_df.attrs["svtk_aggregation_method"] = self.station_aggregation
            sidecar_df.attrs["svtk_aggregation_group_columns"] = list(first_attrs.get("svtk_aggregation_group_columns", []))
            sidecar_df.attrs["svtk_aggregation_coordinate_columns"] = list(first_attrs.get("svtk_aggregation_coordinate_columns", []))
            sidecar_df.attrs["svtk_aggregation_collapsed_columns"] = list(first_attrs.get("svtk_aggregation_collapsed_columns", []))
            sidecar_df.attrs["svtk_aggregation_finite_row_count"] = int(
                sum(int(getattr(frame, "attrs", {}).get("svtk_aggregation_finite_row_count") or 0) for frame in aggregation_frames)
            )
            sidecar_df.attrs["svtk_aggregation_dropped_nonfinite_row_count"] = int(
                sum(int(getattr(frame, "attrs", {}).get("svtk_aggregation_dropped_nonfinite_row_count") or 0) for frame in aggregation_frames)
            )
            if source_sidecar_df is not None:
                sidecar_df.attrs["svtk_aggregation_input_row_count"] = int(len(source_sidecar_df))
                sidecar_df.attrs["svtk_aggregation_input_station_count"] = _unique_count(source_sidecar_df, ("station", "station_id", "station_code"))
                sidecar_df.attrs["svtk_aggregation_input_event_count"] = _unique_count(source_sidecar_df, ("event_id", "event", "event_title"))
                collapsed = list(first_attrs.get("svtk_aggregation_collapsed_columns", []) or [])
                sidecar_df.attrs["svtk_aggregation_collapsed_unique_counts"] = {
                    str(column): int(source_sidecar_df[column].nunique(dropna=True))
                    for column in collapsed
                    if column in source_sidecar_df.columns
                }
        return sidecar_df, source_sidecar_df

    def plot_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return the exact rows that will be handed to a plotting function."""

        if self.sample_rows <= 0 or len(df) <= self.sample_rows:
            out = df.copy()
        else:
            out = _sample_rows(df, n=self.sample_rows)
        out.attrs.update(getattr(df, "attrs", {}))
        return out

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
        source_for_plotted_rows = _source_rows_for_plotted_groups(df, source_df)
        result = write_figure_row_sidecar(
            figure,
            df,
            enabled=True,
            sidecar_rows=self.sidecar_rows,
            sidecar_dir=self.sidecar_output_dir,
            source_rows=source_for_plotted_rows,
            metadata=self.figure_sidecar_metadata(df, source_df=source_for_plotted_rows),
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
            metadata["aggregation_kind"] = aggregation_attrs.get("svtk_aggregation_kind")
            metadata["aggregation_value_col"] = aggregation_attrs.get("svtk_aggregation_value_col")
            metadata["aggregation_method"] = aggregation_attrs.get("svtk_aggregation_method")
            metadata["aggregation_group_columns"] = aggregation_attrs.get("svtk_aggregation_group_columns")
            metadata["aggregation_coordinate_columns"] = aggregation_attrs.get("svtk_aggregation_coordinate_columns")
            metadata["aggregation_input_row_count"] = aggregation_attrs.get("svtk_aggregation_input_row_count")
            metadata["aggregation_finite_row_count"] = aggregation_attrs.get("svtk_aggregation_finite_row_count")
            metadata["aggregation_dropped_nonfinite_row_count"] = aggregation_attrs.get("svtk_aggregation_dropped_nonfinite_row_count")
            metadata["aggregation_audit"] = (
                "Main sidecar rows are the station-level values handed to the plotting function; "
                "source sidecar rows are the metric rows aggregated into those station values."
            )
        if source_df is not None:
            metadata["source_rows_role"] = "pre_aggregation_metric_rows" if aggregation_attrs else "figure_source_rows"
            if aggregation_attrs:
                metadata["source_rows_filter"] = "aggregation_groups_present_in_plot_rows"
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
        broadband = _broadband_passband_mask(df[self.band_col])
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


@dataclass(frozen=True)
class StationMetricMapResult:
    """Result from a focused station metric map notebook helper."""

    output_path: Path | None
    context: MetricFigureContext
    preview: pd.DataFrame

    def status_frame(self) -> pd.DataFrame:
        """Return a compact notebook status table for the rendered station map."""

        rows = [
            ("output_path", None if self.output_path is None else str(self.output_path)),
            ("ready", bool(self.context.ready)),
            ("selected_metric_rows", int(len(self.context.metrics_for_figures))),
            ("preview_rows", int(len(self.preview))),
            ("station_aggregation", self.context.station_aggregation),
            ("write_sidecars", bool(self.context.write_sidecars)),
            ("sidecar_dir", str(self.context.sidecar_output_dir) if self.context.write_sidecars else None),
        ]
        return pd.DataFrame(rows, columns=["name", "value"])


def write_station_metric_map_from_notebook_settings(
    metrics: pd.DataFrame,
    settings: Any,
    *,
    metric: str,
    value_col: str = "log2_residual",
    passband: str | None = None,
    components: list[str] | str | None = None,
    model: str | None = None,
    title: str | None = None,
    preview_rows: int = 5,
    make_figures: bool = True,
    overwrite: bool = True,
) -> StationMetricMapResult:
    """Write one station metric map using notebook figure settings.

    This helper keeps tutorial notebooks from constructing
    :class:`MetricFigureContext` directly for a single focused figure while
    preserving the same station aggregation and source-row sidecar contract.
    """

    from spatial_vtk.spatial.map import plot_station_metric_map, plot_station_metric_map_by_period

    context_kwargs = dict(settings.context_kwargs(include_station_aggregation=True))
    context_kwargs["make_figures"] = bool(make_figures)
    context = MetricFigureContext.from_frame(
        metrics,
        settings.figure_dir,
        overwrite=bool(overwrite),
        value_col=value_col,
        **context_kwargs,
    )
    resolved_passband = passband if passband is not None else settings.passband
    resolved_components = components if components is not None else settings.components
    resolved_model = model if model is not None else settings.model
    output = context.write_station_metric_map_for_metric(
        plot_station_metric_map,
        plot_station_metric_map_by_period,
        metric=metric,
        passband=resolved_passband,
        components=resolved_components,
        model=resolved_model,
        value_col=value_col,
        add_basemap=settings.add_basemap,
        title=title,
        showfig=settings.showfig,
    )
    preview = context.station_summary_preview_for_metric(
        metric,
        value_col,
        passband=resolved_passband,
        components=resolved_components,
        model=resolved_model,
        nrows=preview_rows,
    )
    return StationMetricMapResult(output, context, preview)


def metric_plot_input_summary_frame(
    metrics: pd.DataFrame,
    *,
    comparison_eligible: pd.DataFrame | None = None,
    metric_col: str | None = None,
    event_col: str | None = None,
    station_col: str | None = None,
    max_metric_names: int = 12,
) -> pd.DataFrame:
    """Return a compact notebook summary for metric plotting inputs.

    Parameters
    ----------
    metrics
        Metric rows used by a plotting notebook.
    comparison_eligible
        Optional observed/synthetic waveform-pair table used by waveform
        preview plots.
    metric_col, event_col, station_col
        Optional column overrides. When omitted, common Spatial-VTK aliases are
        resolved from ``metrics``.
    max_metric_names
        Maximum number of metric names to show before appending an overflow
        count.

    Returns
    -------
    pandas.DataFrame
        Two-column summary with ``Input`` and ``Value`` columns.
    """

    metric_column = metric_col if metric_col in metrics.columns else first_existing(metrics, ["metric", "metric_name"])
    event_column = event_col if event_col in metrics.columns else first_existing(metrics, ["event_id", "event", "event_title"])
    station_column = station_col if station_col in metrics.columns else first_existing(metrics, ["station", "station_id", "station_code"])
    rows: list[dict[str, Any]] = [
        {"Input": "Metric rows", "Value": int(len(metrics))},
        {"Input": "Events", "Value": _summary_unique_count(metrics, event_column)},
        {"Input": "Stations", "Value": _summary_unique_count(metrics, station_column)},
        {"Input": "Metrics", "Value": _summary_metric_names(metrics, metric_column, max_names=max_metric_names)},
    ]
    if comparison_eligible is not None:
        rows.append({"Input": "Waveform preview pairs", "Value": int(len(comparison_eligible))})
    return pd.DataFrame(rows, columns=["Input", "Value"])


def metric_rows_for_metrics(
    metrics: pd.DataFrame | None,
    metric_names: Sequence[object],
    *,
    metric_col: str | None = None,
) -> pd.DataFrame:
    """Return metric rows matching one or more metric names or aliases.

    Parameters
    ----------
    metrics
        Metric table to filter.
    metric_names
        Metric names, display labels, keys, or aliases to keep. Values such as
        ``"pga"`` and ``"Peak acceleration"`` match the same target metric.
    metric_col
        Optional metric column override. When omitted, common metric column
        names are resolved from ``metrics``.

    Returns
    -------
    pandas.DataFrame
        Filtered metric rows in their original order. Missing inputs or metric
        columns return an empty frame with the same columns where possible.
    """

    if metrics is None:
        return pd.DataFrame()
    if metrics.empty:
        return metrics.copy()
    column = metric_col if metric_col in metrics.columns else first_existing(metrics, ["metric", "metric_name"])
    if column is None:
        return metrics.iloc[0:0].copy()
    wanted = _metric_name_match_tokens(metric_names)
    if not wanted:
        return metrics.iloc[0:0].copy()
    mask = metrics[column].map(lambda value: bool(_metric_name_alias_tokens(value) & wanted))
    return metrics.loc[mask].copy()


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


def _target_metric_spec(key: object) -> dict[str, object] | None:
    """Return one target metric spec by key, label, or alias."""

    wanted = norm_text(key)
    for spec in TARGET_METRIC_SPECS:
        names = {spec["key"], spec["label"], *spec.get("aliases", ())}
        if wanted in {norm_text(name) for name in names}:
            return dict(spec)
    return None


def _metric_name_match_tokens(metric_names: Sequence[object]) -> set[str]:
    """Return normalized metric names and known aliases for filtering."""

    tokens: set[str] = set()
    for name in metric_names:
        name_tokens = _metric_name_alias_tokens(name)
        if not name_tokens:
            continue
        tokens.update(name_tokens)
        spec = _target_metric_spec(name)
        if spec is None:
            continue
        names = {spec["key"], spec["label"], *spec.get("aliases", ())}
        for value in names:
            tokens.update(_metric_name_alias_tokens(value))
    return tokens


def _metric_name_alias_tokens(value: object) -> set[str]:
    """Return normalized tokens for a metric display value."""

    text = str(value).strip()
    if not text:
        return set()
    tokens = {norm_text(text)}
    without_parenthetical = re.sub(r"\([^)]*\)", "", text).strip()
    if without_parenthetical:
        tokens.add(norm_text(without_parenthetical))
    for match in re.findall(r"\(([^)]*)\)", text):
        if match.strip():
            tokens.add(norm_text(match))
    return {token for token in tokens if token}


def slug(value: object) -> str:
    """Return a filename-safe short slug."""

    text = str(value).strip()
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    return text[:80] or "unknown"


def psa_period_label(period: float) -> str:
    """Format one PSA oscillator period label."""

    period = float(period)
    return f"T={period:g} s (f={1.0 / period:g} Hz)" if np.isfinite(period) and period > 0 else "PSA period unknown"


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
        "anderson_2004_gof",
        "olsen_mayhew_gof",
        "score",
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


def _station_summary_grid_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a station summary with generic lon/lat columns for grid plot helpers."""

    return df.rename(columns={"sta_lon": "lon", "sta_lat": "lat"})


def _call_item_dataframe_factory(
    factory: Callable[[dict[str, Any]], pd.DataFrame],
    item: dict[str, Any],
    *,
    value_col: str | None,
) -> pd.DataFrame:
    """Call an item dataframe factory, passing value_col when the factory supports it."""

    try:
        signature = inspect.signature(factory)
    except (TypeError, ValueError):
        return factory(item)
    parameters = signature.parameters.values()
    accepts_value_col = "value_col" in signature.parameters or any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters
    )
    if accepts_value_col:
        return factory(item, value_col=value_col)  # type: ignore[call-arg]
    return factory(item)


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


def _broadband_passband_mask(values: pd.Series) -> pd.Series:
    """Return rows whose passband label represents a broadband spectral row."""

    labels = values.fillna("").astype(str).str.strip().str.lower()
    return labels.isin(BROADBAND_PASSBAND_LABELS)


def _aggregate_spectral_contract_status(status: pd.DataFrame) -> dict[str, str]:
    """Return one compact status/message for PSA/FAS contract rows."""

    if status.empty:
        return {"status": "not_checked", "message": "No spectral metric rows were available to check."}
    work = status.loc[~status["status"].eq("not_present")]
    if work.empty:
        return {"status": "not_present", "message": "No PSA/FAS rows are present in the selected metric figure rows."}
    problem = work.loc[work["status"].isin(["legacy_passband_rows", "mixed_passband_rows"])]
    if not problem.empty:
        metrics = ", ".join(problem["metric"].astype(str).tolist())
        return {
            "status": "needs_rebuild",
            "message": f"{metrics} rows include passband-scoped spectral records; rebuild metric manifest and metric rows.",
        }
    unchecked = work.loc[work["status"].eq("missing_passband_column")]
    if not unchecked.empty:
        metrics = ", ".join(unchecked["metric"].astype(str).tolist())
        return {"status": "not_checked", "message": f"{metrics} rows could not be checked because no passband column is loaded."}
    return {"status": "ok", "message": "Spectral metric rows use blank/broadband passbands with oscillator periods in period_s."}


def _station_aggregation_attrs(
    *,
    value_col: str,
    method: str,
    group_cols: list[str],
    coordinate_cols: tuple[str, str],
    collapsed_cols: Iterable[str | None] | None,
    source_rows: pd.DataFrame,
    finite_rows: pd.DataFrame,
) -> dict[str, Any]:
    """Return dataframe metadata describing a station-summary aggregation."""

    lon_col, lat_col = coordinate_cols
    collapsed = _ordered_existing_columns(source_rows, collapsed_cols or [])
    input_stations = _unique_count(source_rows, ("station", "station_id", "station_code"))
    finite_stations = _unique_count(finite_rows, ("station", "station_id", "station_code"))
    input_events = _unique_count(source_rows, ("event_id", "event", "event_title"))
    finite_events = _unique_count(finite_rows, ("event_id", "event", "event_title"))
    collapsed_counts = {
        str(column): int(source_rows[column].nunique(dropna=True))
        for column in collapsed
        if column in source_rows.columns
    }
    return {
        "svtk_aggregation_kind": "station_event_rows_to_station_summary",
        "svtk_aggregation_value_col": value_col,
        "svtk_aggregation_method": str(method or "median").lower(),
        "svtk_aggregation_group_columns": list(group_cols),
        "svtk_aggregation_coordinate_columns": [lon_col, lat_col],
        "svtk_aggregation_collapsed_columns": collapsed,
        "svtk_aggregation_collapsed_unique_counts": collapsed_counts,
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


def _summary_unique_count(df: pd.DataFrame, column: str | None) -> int | None:
    """Return a nullable unique count for a notebook summary row."""

    if column is None or column not in df.columns:
        return None
    return int(df[column].nunique(dropna=True))


def _summary_metric_names(df: pd.DataFrame, column: str | None, *, max_names: int) -> str | None:
    """Return a compact metric-name preview for a notebook summary row."""

    if column is None or column not in df.columns:
        return None
    names = sorted({str(value) for value in df[column].dropna().unique() if str(value).strip()})
    if not names:
        return None
    limit = max(1, int(max_names))
    shown = names[:limit]
    suffix = f", ... (+{len(names) - limit} more)" if len(names) > limit else ""
    return ", ".join(shown) + suffix


def _preview_values(values: Iterable[Any] | Any, *, limit: int = 6) -> str | None:
    """Return a compact deterministic preview for settings or dimension values."""

    if values is None:
        return None
    if isinstance(values, (str, bytes)):
        items = [values]
    else:
        try:
            items = list(values)
        except TypeError:
            items = [values]
    cleaned = [item for item in items if not pd.isna(item)]
    if not cleaned:
        return None
    ordered = sorted({str(item) for item in cleaned})
    preview = ordered[:limit]
    suffix = f", ... (+{len(ordered) - limit} more)" if len(ordered) > limit else ""
    return ", ".join(preview) + suffix


def _source_rows_for_plotted_groups(plot_rows: pd.DataFrame, source_rows: pd.DataFrame | None) -> pd.DataFrame | None:
    """Return source rows for the aggregation groups present in plotted rows."""

    if source_rows is None:
        return None
    attrs = getattr(plot_rows, "attrs", {})
    group_cols = [str(column) for column in attrs.get("svtk_aggregation_group_columns", [])]
    if not group_cols or plot_rows.empty:
        return source_rows.iloc[0:0].copy() if plot_rows.empty else source_rows
    pairs = _source_plot_group_column_pairs(plot_rows, source_rows, group_cols, attrs)
    if not pairs:
        return source_rows
    plot_keys = {
        tuple(_group_key_value(row[plot_col]) for _, plot_col in pairs)
        for _, row in plot_rows.iterrows()
    }
    if not plot_keys:
        return source_rows.iloc[0:0].copy()
    source_keys = source_rows.apply(
        lambda row: tuple(_group_key_value(row[source_col]) for source_col, _ in pairs),
        axis=1,
    )
    return source_rows.loc[source_keys.isin(plot_keys)].copy()


def _source_plot_group_column_pairs(
    plot_rows: pd.DataFrame,
    source_rows: pd.DataFrame,
    group_cols: Iterable[str],
    attrs: dict[str, Any],
) -> list[tuple[str, str]]:
    """Return source/plot column pairs for aggregation group matching."""

    pairs: list[tuple[str, str]] = []
    coordinate_cols = list(attrs.get("svtk_aggregation_coordinate_columns", []) or [])
    coordinate_map: dict[str, str] = {}
    if len(coordinate_cols) >= 2:
        coordinate_map[str(coordinate_cols[0])] = "sta_lon"
        coordinate_map[str(coordinate_cols[1])] = "sta_lat"
    for group_col in group_cols:
        source_col = _resolve_group_column(source_rows, group_col)
        plot_col = _resolve_group_column(plot_rows, group_col)
        if plot_col is None and group_col in coordinate_map:
            plot_col = _resolve_group_column(plot_rows, coordinate_map[group_col])
        if source_col is not None and plot_col is not None:
            pairs.append((source_col, plot_col))
    return pairs


def _resolve_group_column(df: pd.DataFrame, column: str) -> str | None:
    """Resolve one aggregation group column against canonical aliases."""

    if column in df.columns:
        return column
    aliases = {
        "station": ("station", "station_id", "station_code"),
        "station_id": ("station_id", "station", "station_code"),
        "station_code": ("station_code", "station", "station_id"),
        "sta_lon": ("sta_lon", "lon", "station_lon", "station_longitude"),
        "lon": ("lon", "sta_lon", "station_lon", "station_longitude"),
        "station_lon": ("station_lon", "sta_lon", "lon", "station_longitude"),
        "station_longitude": ("station_longitude", "station_lon", "sta_lon", "lon"),
        "sta_lat": ("sta_lat", "lat", "station_lat", "station_latitude"),
        "lat": ("lat", "sta_lat", "station_lat", "station_latitude"),
        "station_lat": ("station_lat", "sta_lat", "lat", "station_latitude"),
        "station_latitude": ("station_latitude", "station_lat", "sta_lat", "lat"),
    }
    return next((candidate for candidate in aliases.get(column, ()) if candidate in df.columns), None)


def _group_key_value(value: object) -> object:
    """Normalize group key values so source and plot rows can be matched."""

    if pd.isna(value):
        return "<NA>"
    if isinstance(value, (float, np.floating)):
        return round(float(value), 12)
    return str(value)


__all__ = [
    "MetricFigureContext",
    "StationMetricMapResult",
    "TARGET_METRIC_SPECS",
    "dimension_value",
    "filter_optional",
    "first_existing",
    "first_value",
    "metric_plot_input_summary_frame",
    "metric_rows_for_metrics",
    "norm_text",
    "prepare_large_run_metric_figure_context",
    "psa_period_label",
    "slug",
    "write_station_metric_map_from_notebook_settings",
]
