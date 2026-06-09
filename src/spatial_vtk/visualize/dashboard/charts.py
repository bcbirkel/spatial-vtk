"""Plotly chart builders for Streamlit dashboards."""

from __future__ import annotations

import numpy as np
import pandas as pd

from spatial_vtk.config.labels import band_display_label, metric_display_name, model_display_name, value_column_display_name
from spatial_vtk.visualize.figure_context import value_color_settings, value_uses_zero_reference


def build_metric_heatmap_figure(df: pd.DataFrame, *, value_col: str, title: str = "Model-Metric Summary"):
    """Build a model-by-metric heatmap."""

    px = _plotly_express()
    work = df.copy()
    if value_col not in work.columns:
        raise ValueError(f"Heatmap value column is not available: {value_col}")
    work["Metric"] = work["metric"].map(metric_display_name) if "metric" in work.columns else ""
    work["Band"] = work["band"].map(band_display_label) if "band" in work.columns else "All periods"
    work["Model"] = work["model"].map(model_display_name) if "model" in work.columns else ""
    pivot = work.pivot_table(index="Model", columns="Metric", values=value_col, aggfunc="median")
    cmin, cmax = _color_bounds(pivot.to_numpy(dtype=float), value_col)
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale=_color_scale(value_col),
        zmin=cmin,
        zmax=cmax,
        title=title,
        labels={"color": value_column_display_name(value_col), "x": "Metric", "y": "Model"},
    )
    fig.update_layout(xaxis_tickangle=-35)
    return fig


def build_path_heatmap_figure(df: pd.DataFrame, *, value_col: str, title: str = "Path Summary"):
    """Build a distance-by-azimuth heatmap."""

    px = _plotly_express()
    if value_col not in df.columns:
        raise ValueError(f"Path heatmap value column is not available: {value_col}")
    pivot = df.pivot_table(index="az_bin_deg", columns="dist_bin_km", values=value_col, aggfunc="median")
    cmin, cmax = _color_bounds(pivot.to_numpy(dtype=float), value_col)
    return px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale=_color_scale(value_col),
        zmin=cmin,
        zmax=cmax,
        title=title,
        labels={"color": value_column_display_name(value_col), "x": "Distance bin (km)", "y": "Azimuth bin (deg)"},
    )


def build_value_histogram_figure(df: pd.DataFrame, *, value_col: str, title: str | None = None):
    """Build a histogram for one metric value column."""

    px = _plotly_express()
    if value_col not in df.columns:
        raise ValueError(f"Histogram value column is not available: {value_col}")
    label = value_column_display_name(value_col)
    return px.histogram(df, x=value_col, nbins=40, title=title or label, labels={value_col: label})


def build_value_vs_distance_figure(df: pd.DataFrame, *, value_col: str, distance_col: str = "distance_km", title: str | None = None):
    """Build a value-versus-distance scatter plot."""

    px = _plotly_express()
    if value_col not in df.columns:
        raise ValueError(f"Scatter value column is not available: {value_col}")
    if distance_col not in df.columns and "med_dist_km" in df.columns:
        distance_col = "med_dist_km"
    if distance_col not in df.columns:
        raise ValueError("Distance plot requires distance_km or med_dist_km.")
    label = value_column_display_name(value_col)
    return px.scatter(df, x=distance_col, y=value_col, color="model" if "model" in df.columns else None, title=title or f"{label} vs Distance", labels={value_col: label, distance_col: "Distance (km)"})


def build_qc_histogram_figure(df: pd.DataFrame, *, value_col: str, title: str | None = None, clip_iqr: bool = False, bounds: tuple[float | None, float | None] | None = None):
    """Build a QC histogram with optional display clipping."""

    px = _plotly_express()
    if value_col not in df.columns:
        raise ValueError(f"QC histogram column is not available: {value_col}")
    values = pd.to_numeric(df[value_col], errors="coerce").dropna()
    if clip_iqr and len(values) >= 4:
        q1, q3 = values.quantile(0.25), values.quantile(0.75)
        iqr = q3 - q1
        values = values[(values >= q1 - 1.5 * iqr) & (values <= q3 + 1.5 * iqr)]
    if bounds is not None:
        lower, upper = bounds
        if lower is not None:
            values = values[values >= float(lower)]
        if upper is not None:
            values = values[values <= float(upper)]
    label = value_col.replace("_", " ").title()
    return px.histogram(pd.DataFrame({value_col: values}), x=value_col, nbins=40, title=title or label, labels={value_col: label})


def build_qc_bar_figure(df: pd.DataFrame, *, column: str, title: str | None = None):
    """Build a count bar chart for one QC categorical column."""

    px = _plotly_express()
    if column not in df.columns:
        raise ValueError(f"QC bar column is not available: {column}")
    counts = df[column].fillna("unknown").astype(str).value_counts().rename_axis(column).reset_index(name="count")
    return px.bar(counts, x=column, y="count", title=title or column.replace("_", " ").title())


def _plotly_express():
    """Import Plotly Express with a clear optional dependency error."""

    try:
        import plotly.express as px
    except Exception as exc:  # pragma: no cover - depends on optional install
        raise ImportError("Dashboard charts require plotly. Install spatial-vtk[dashboard].") from exc
    return px


def _color_scale(value_col: str) -> str:
    """Return a color scale for a value column."""

    return "RdBu_r" if value_uses_zero_reference(value_col) else "Viridis"


def _color_bounds(values: object, value_col: str) -> tuple[float | None, float | None]:
    """Return Plotly color bounds using the shared Spatial-VTK value rules."""

    _cmap, vmin, vmax = value_color_settings(np.asarray(values, dtype=float), value_col)
    return vmin, vmax


__all__ = [
    "build_metric_heatmap_figure",
    "build_path_heatmap_figure",
    "build_qc_bar_figure",
    "build_qc_histogram_figure",
    "build_value_histogram_figure",
    "build_value_vs_distance_figure",
]
