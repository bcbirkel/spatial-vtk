"""Non-map spatial metric plots."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

from spatial_vtk.config.labels import band_display_label, display_label, metric_display_name, model_display_name, normalize_metric_name, value_column_display_name
from spatial_vtk.spatial.calculate.geology import bootstrap_contrast_table
from spatial_vtk.spatial.calculate.settings import spatial_statistics_settings_from_config
from spatial_vtk.visualize.figure_context import (
    add_below_axes_table,
    apply_figure_context,
    context_value_label,
    figure_context_text,
    value_color_settings,
    value_requires_model,
    value_uses_zero_reference,
)
from spatial_vtk.visualize.figure_io import finish_figure
from spatial_vtk.visualize.fit import draw_scatter_fit
from spatial_vtk.visualize.selection import FigureSpatialSelection, apply_figure_spatial_selection


def scatterplot(
    data: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    indep: str,
    dep: str | Sequence[str],
    value_col: str | None = None,
    passband: str | Sequence[str] | None = None,
    band: str | Sequence[str] | None = None,
    model: str | Sequence[str] | None = None,
    component: str | Sequence[str] | None = None,
    station: str | Sequence[str] | None = None,
    event_id: str | Sequence[str] | None = None,
    filters: dict[str, object] | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    station_region_col: str | None = None,
    station_regions: Sequence[str] | str | None = None,
    station_region_relation: str = "inside",
    event_region_col: str | None = None,
    event_regions: Sequence[str] | str | None = None,
    event_region_relation: str = "inside",
    station_bounds: tuple[float, float, float, float] | None = None,
    station_bounds_relation: str = "inside",
    event_bounds: tuple[float, float, float, float] | None = None,
    event_bounds_relation: str = "inside",
    station_corridor_col: str | None = None,
    station_corridors: Sequence[str] | str | None = None,
    station_corridor_relation: str = "inside",
    event_corridor_col: str | None = None,
    event_corridors: Sequence[str] | str | None = None,
    event_corridor_relation: str = "inside",
    colorby: str | None = None,
    groupby: str | None = None,
    fit: str | Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray] | pd.DataFrame] | None = None,
    lowess_frac: float = 0.65,
    cmap: str | Sequence[object] | None = None,
    title: str | None = None,
    data_label: str | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot any metric table variable against another variable.

    Parameters
    ----------
    data
        Input dataframe. Wide tables can pass real column names as ``dep``.
        Long metric tables can pass metric names, such as ``"PGA"`` or
        ``["PGA", "PGV"]``, and use ``value_col`` to choose the plotted value.
    output_path, outpath
        Optional destination for saving the figure.
    indep, dep
        Independent-variable column and dependent variable or variables.
        Friendly aliases such as ``"distance"``, ``"vs30"``, and lowercase
        metric names are resolved when possible.
    value_col
        Value column for long metric tables. Aliases include ``"observed"``,
        ``"synthetic"``, ``"log2_residual"``, and other public transform names.
    passband, band, model, component, station, event_id, filters
        Optional filters applied before plotting.
    colorby, groupby
        Optional column used for color and fit grouping. ``"dep"`` groups by
        dependent variable when multiple dependent variables are plotted.
    fit
        Optional line-fitting mode: ``"point-to-point"``, ``"best"``, ``"linear"``,
        ``"inverse"``, ``"inverse-square"``, ``"quadratic"``,
        ``"exponential-decay"``, ``"lowess"``, a callable, or ``None``.
    lowess_frac
        Fraction of points used by LOWESS when ``fit="lowess"``.
    cmap
        Matplotlib colormap name or explicit color sequence for grouped points.
    title, data_label
        Optional visible title controls. ``data_label`` prefixes the default
        title, for example ``"Observed"``.
    showfig, savefig
        Standard Spatial-VTK display/save controls.

    Returns
    -------
    matplotlib.figure.Figure
        Scatterplot figure.
    """

    if data.empty:
        fig, ax = plt.subplots(figsize=(7.0, 5.0), dpi=180)
        ax.text(0.5, 0.5, "No rows matched the scatterplot request", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return finish_figure(fig, output_path, outpath=outpath, output_key="scatterplot", showfig=showfig, savefig=savefig)

    work = _filter_scatter_data(
        data,
        passband=passband if passband is not None else band,
        model=model,
        component=component,
        station=station,
        event_id=event_id,
        filters=filters,
    )
    work, subset_label = apply_figure_spatial_selection(
        work,
        spatial_selection,
        station_region_col=station_region_col,
        station_regions=station_regions,
        station_region_relation=station_region_relation,
        event_region_col=event_region_col,
        event_regions=event_regions,
        event_region_relation=event_region_relation,
        station_bounds=station_bounds,
        station_bounds_relation=station_bounds_relation,
        event_bounds=event_bounds,
        event_bounds_relation=event_bounds_relation,
        station_corridor_col=station_corridor_col,
        station_corridors=station_corridors,
        station_corridor_relation=station_corridor_relation,
        event_corridor_col=event_corridor_col,
        event_corridors=event_corridors,
        event_corridor_relation=event_corridor_relation,
    )
    if work.empty:
        fig, ax = plt.subplots(figsize=(7.0, 5.0), dpi=180)
        ax.text(0.5, 0.5, "No rows matched the scatterplot filters", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return finish_figure(fig, output_path, outpath=outpath, output_key="scatterplot", showfig=showfig, savefig=savefig)
    plot_df, x_col, y_col, dep_labels, resolved_value_col = _scatter_long_form(work, indep=indep, dep=dep, value_col=value_col)
    fig, ax = plt.subplots(figsize=(7.2, 5.0), dpi=180)
    if plot_df.empty:
        ax.text(0.5, 0.5, "No rows matched the scatterplot request", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return finish_figure(fig, output_path, outpath=outpath, output_key="scatterplot", showfig=showfig, savefig=savefig)

    group_col = groupby or colorby
    if group_col is None and len(dep_labels) > 1:
        group_col = "dep"
    if group_col == "passband":
        group_col = _first_existing_column(plot_df, ["band", "passband", "simulation_band"]) or group_col
    if group_col is not None:
        group_col = _resolve_scatter_column(plot_df, group_col, required=False) or group_col
    x_axis = _scatter_axis_encoder(plot_df[x_col])
    y_axis = _scatter_axis_encoder(plot_df[y_col])
    groups = [(None, plot_df)] if group_col is None or group_col not in plot_df.columns else list(plot_df.groupby(group_col, dropna=False))
    colors = _scatter_colors(cmap, len(groups))
    for group_index, (label, subset) in enumerate(groups):
        x = x_axis["encode"](subset[x_col])
        y = y_axis["encode"](subset[y_col])
        finite = x.notna() & y.notna()
        if not finite.any():
            continue
        legend_label = _group_display_label(label, group_col) if label is not None else None
        color = colors[group_index]
        ax.scatter(x[finite], y[finite], s=30, alpha=0.76, color=color, label=legend_label)
        if not x_axis["categorical"] and not y_axis["categorical"]:
            draw_scatter_fit(ax, x[finite].to_numpy(dtype=float), y[finite].to_numpy(dtype=float), fit_method=fit, lowess_frac=lowess_frac, color=color, label=legend_label)
    _apply_categorical_axis(ax, x_axis, axis="x")
    _apply_categorical_axis(ax, y_axis, axis="y")
    if not y_axis["categorical"] and (_uses_zero_reference(y_col) or str(resolved_value_col or "").endswith("residual")):
        ax.axhline(0.0, color="black", linewidth=0.8, linestyle=":")
    ax.set_xlabel(_feature_axis_label(x_col))
    ax.set_ylabel(_scatter_y_label(dep_labels, resolved_value_col, y_col, data_label=data_label))
    plot_title = title or _scatter_default_title(dep_labels, x_col, resolved_value_col, data_label=data_label)
    ax.set_title(f"{plot_title}\n{subset_label}" if subset_label else plot_title)
    ax.grid(True, alpha=0.25)
    _draw_scatter_legend(ax, group_col)
    return finish_figure(fig, output_path, outpath=outpath, output_key="scatterplot", showfig=showfig, savefig=savefig)


def boxplot(
    data: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    dep: str | Sequence[str],
    indep: str,
    value_col: str,
    passband: str | Sequence[str],
    model: str | Sequence[str] | None = None,
    component: str | Sequence[str] | None = None,
    station: str | Sequence[str] | None = None,
    event_id: str | Sequence[str] | None = None,
    filters: dict[str, object] | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    station_region_col: str | None = None,
    station_regions: Sequence[str] | str | None = None,
    station_region_relation: str = "inside",
    event_region_col: str | None = None,
    event_regions: Sequence[str] | str | None = None,
    event_region_relation: str = "inside",
    station_bounds: tuple[float, float, float, float] | None = None,
    station_bounds_relation: str = "inside",
    event_bounds: tuple[float, float, float, float] | None = None,
    event_bounds_relation: str = "inside",
    station_corridor_col: str | None = None,
    station_corridors: Sequence[str] | str | None = None,
    station_corridor_relation: str = "inside",
    event_corridor_col: str | None = None,
    event_corridors: Sequence[str] | str | None = None,
    event_corridor_relation: str = "inside",
    colorby: str | None = None,
    compare_to: str | Sequence[str] | None = None,
    table: bool = False,
    statistic: str = "median",
    n_bootstrap: int = 1000,
    random_seed: int = 42,
    title: str | None = None,
    cmap: str | Sequence[object] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot metric distributions grouped by a categorical variable.

    Parameters
    ----------
    data
        Input dataframe. Long metric tables should contain a ``metric`` column;
        wide tables can pass real numeric dependent-variable columns.
    output_path, outpath
        Optional destination for saving the figure.
    dep, indep, value_col, passband
        Required plotting controls. ``dep`` is one or more metrics or columns,
        ``indep`` is the categorical grouping column, ``value_col`` is the
        plotted value, and ``passband`` filters the period band.
    model
        Required when the requested value column depends on synthetics,
        residuals, or scores and the table contains model information.
    component, station, event_id, filters
        Optional filters applied before plotting.
    colorby
        Optional box-color grouping. When omitted and multiple ``dep`` values
        are requested, boxes are colored by dependent variable.
    compare_to, table
        Optional baseline category and below-plot comparison table.
    statistic, n_bootstrap, random_seed
        Summary statistic and bootstrap settings for the comparison table.
    title, cmap, showfig, savefig
        Standard display controls.

    Returns
    -------
    matplotlib.figure.Figure
        Boxplot figure.
    """

    plot_df, category_col, value_column, dep_labels, resolved_value_col, subset_label = _categorical_metric_plot_data(
        data,
        dep=dep,
        indep=indep,
        value_col=value_col,
        passband=passband,
        model=model,
        component=component,
        station=station,
        event_id=event_id,
        filters=filters,
        spatial_selection=spatial_selection,
        station_region_col=station_region_col,
        station_regions=station_regions,
        station_region_relation=station_region_relation,
        event_region_col=event_region_col,
        event_regions=event_regions,
        event_region_relation=event_region_relation,
        station_bounds=station_bounds,
        station_bounds_relation=station_bounds_relation,
        event_bounds=event_bounds,
        event_bounds_relation=event_bounds_relation,
        station_corridor_col=station_corridor_col,
        station_corridors=station_corridors,
        station_corridor_relation=station_corridor_relation,
        event_corridor_col=event_corridor_col,
        event_corridors=event_corridors,
        event_corridor_relation=event_corridor_relation,
    )
    fig_width = max(7.6, 1.45 * max(2, plot_df[category_col].nunique()) + 1.6 * max(1, len(dep_labels)))
    fig_height = 6.6 if table and compare_to is not None else 5.4
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=180)
    if plot_df.empty:
        ax.text(0.5, 0.5, "No rows matched the boxplot request", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return finish_figure(fig, output_path, outpath=outpath, output_key="boxplot", showfig=showfig, savefig=savefig)

    categories = _ordered_categories(plot_df[category_col])
    if compare_to is not None:
        categories = _move_baseline_categories_first(categories, compare_to)
    color_col = colorby or ("dep" if len(dep_labels) > 1 else None)
    if color_col is not None:
        color_col = _resolve_scatter_column(plot_df, color_col, required=False) or color_col
    if color_col is None or color_col not in plot_df.columns:
        color_values = ["Distribution"]
        plot_df["_box_color_group"] = "Distribution"
        color_col = "_box_color_group"
    else:
        color_values = _ordered_categories(plot_df[color_col])
    colors = _scatter_colors(cmap, len(color_values))
    color_lookup = dict(zip(color_values, colors))
    _draw_grouped_boxplot(ax, plot_df, category_col=category_col, color_col=color_col, value_col=value_column, categories=categories, color_values=color_values, color_lookup=color_lookup)
    if _uses_zero_reference(str(resolved_value_col)) or str(resolved_value_col).endswith("residual"):
        ax.axhline(0.0, color="black", linewidth=0.8, linestyle=":")
    ax.set_xlabel(display_label(category_col))
    ax.set_ylabel(context_value_label(str(resolved_value_col), plot_df))
    apply_figure_context(
        ax,
        plot_df,
        value_col=str(resolved_value_col),
        title=title or _categorical_plot_title(dep_labels, category_col, resolved_value_col, plot_type="Boxplot"),
        max_values=3,
        include_metric=False,
        include_model=_context_should_include_model(resolved_value_col),
        include_value=False,
        extra=[subset_label] if subset_label else None,
    )
    ax.grid(True, axis="y", alpha=0.25)
    if color_col != "_box_color_group":
        _draw_boxplot_legend(ax, color_values, color_lookup, color_col)
    if table and compare_to is not None:
        rows = _categorical_comparison_rows(
            plot_df,
            category_col=category_col,
            color_col="dep",
            value_col=value_column,
            compare_to=compare_to,
            statistic=statistic,
            n_bootstrap=n_bootstrap,
            random_seed=random_seed,
        )
        if rows:
            ax.set_xlabel("")
            add_below_axes_table(ax, rows=rows, columns=["Comparison", "Effect", "95% CI", "p", "n"], col_widths=[0.42, 0.12, 0.24, 0.10, 0.08], font_size=7.0, max_visible_rows=6)
    return finish_figure(fig, output_path, outpath=outpath, output_key="boxplot", showfig=showfig, savefig=savefig)


def heatmap(
    data: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    dep: str | Sequence[str],
    indep: str,
    value_col: str,
    passband: str | Sequence[str],
    model: str | Sequence[str] | None = None,
    column: str | None = None,
    component: str | Sequence[str] | None = None,
    station: str | Sequence[str] | None = None,
    event_id: str | Sequence[str] | None = None,
    filters: dict[str, object] | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    station_region_col: str | None = None,
    station_regions: Sequence[str] | str | None = None,
    station_region_relation: str = "inside",
    event_region_col: str | None = None,
    event_regions: Sequence[str] | str | None = None,
    event_region_relation: str = "inside",
    station_bounds: tuple[float, float, float, float] | None = None,
    station_bounds_relation: str = "inside",
    event_bounds: tuple[float, float, float, float] | None = None,
    event_bounds_relation: str = "inside",
    station_corridor_col: str | None = None,
    station_corridors: Sequence[str] | str | None = None,
    station_corridor_relation: str = "inside",
    event_corridor_col: str | None = None,
    event_corridors: Sequence[str] | str | None = None,
    event_corridor_relation: str = "inside",
    aggfunc: str = "mean",
    title: str | None = None,
    cmap: str = "coolwarm",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot categorical metric summaries as a heatmap.

    Parameters are the same as ``boxplot``. When ``column`` is omitted, heatmap
    columns are the selected dependent variables. When ``column`` is provided,
    columns are that categorical field and ``dep`` filters the metric rows.
    """

    plot_df, row_col, value_column, dep_labels, resolved_value_col, subset_label = _categorical_metric_plot_data(
        data,
        dep=dep,
        indep=indep,
        value_col=value_col,
        passband=passband,
        model=model,
        component=component,
        station=station,
        event_id=event_id,
        filters=filters,
        spatial_selection=spatial_selection,
        station_region_col=station_region_col,
        station_regions=station_regions,
        station_region_relation=station_region_relation,
        event_region_col=event_region_col,
        event_regions=event_regions,
        event_region_relation=event_region_relation,
        station_bounds=station_bounds,
        station_bounds_relation=station_bounds_relation,
        event_bounds=event_bounds,
        event_bounds_relation=event_bounds_relation,
        station_corridor_col=station_corridor_col,
        station_corridors=station_corridors,
        station_corridor_relation=station_corridor_relation,
        event_corridor_col=event_corridor_col,
        event_corridors=event_corridors,
        event_corridor_relation=event_corridor_relation,
    )
    if column is None:
        col_col = "dep"
    else:
        col_col = _resolve_scatter_column(plot_df, column, required=True)
    pivot = plot_df.pivot_table(index=row_col, columns=col_col, values=value_column, aggfunc=aggfunc)
    if not pivot.empty:
        pivot = pivot.reindex(index=_ordered_categories(plot_df[row_col]))
        if col_col == "dep":
            pivot = pivot.reindex(columns=dep_labels)
    return _heatmap(
        pivot,
        output_path,
        title=title or _categorical_plot_title(dep_labels, row_col, resolved_value_col, plot_type="Heatmap"),
        cbar_label=context_value_label(str(resolved_value_col), plot_df),
        x_label=_scatter_group_title(col_col) or display_label(col_col),
        y_label=display_label(row_col),
        context_df=plot_df,
        value_col=str(resolved_value_col),
        include_model=_context_should_include_model(resolved_value_col),
        extra=[subset_label] if subset_label else None,
        showfig=showfig,
        savefig=savefig,
        outpath=outpath,
        cmap=cmap,
    )


def _draw_scatter_legend(ax: plt.Axes, group_col: str | None) -> None:
    """Draw a scatterplot legend only when labeled artists are present."""

    handles, labels = ax.get_legend_handles_labels()
    if handles and labels:
        ax.legend(frameon=True, fontsize=8, title=_scatter_group_title(group_col))


def plot_azimuthal_residuals(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    azimuth_col: str = "azimuth_deg",
    value_col: str = "residual",
    group_col: str | None = "model",
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    station_region_col: str | None = None,
    station_regions: Sequence[str] | str | None = None,
    station_region_relation: str = "inside",
    event_region_col: str | None = None,
    event_regions: Sequence[str] | str | None = None,
    event_region_relation: str = "inside",
    station_bounds: tuple[float, float, float, float] | None = None,
    station_bounds_relation: str = "inside",
    event_bounds: tuple[float, float, float, float] | None = None,
    event_bounds_relation: str = "inside",
    station_corridor_col: str | None = None,
    station_corridors: Sequence[str] | str | None = None,
    station_corridor_relation: str = "inside",
    event_corridor_col: str | None = None,
    event_corridors: Sequence[str] | str | None = None,
    event_corridor_relation: str = "inside",
    station_subset_label: str | None = None,
    event_subset_label: str | None = None,
    title: str = "Azimuthal Residuals",
    fit_method: str | Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray] | pd.DataFrame] | None = None,
    fit: str | Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray] | pd.DataFrame] | None = None,
    lowess_frac: float = 0.65,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot residuals against source-station azimuth.

    Inputs are metric rows with azimuth and residual columns. When
    ``fit_method`` is supplied, points are shown with a shared fitted curve
    such as ``"lowess"`` instead of connecting every point directly. The
    output is a Matplotlib figure.
    """

    plot_df, subset_label = apply_figure_spatial_selection(
        df,
        spatial_selection,
        station_region_col=station_region_col,
        station_regions=station_regions,
        station_region_relation=station_region_relation,
        event_region_col=event_region_col,
        event_regions=event_regions,
        event_region_relation=event_region_relation,
        station_bounds=station_bounds,
        station_bounds_relation=station_bounds_relation,
        event_bounds=event_bounds,
        event_bounds_relation=event_bounds_relation,
        station_corridor_col=station_corridor_col,
        station_corridors=station_corridors,
        station_corridor_relation=station_corridor_relation,
        event_corridor_col=event_corridor_col,
        event_corridors=event_corridors,
        event_corridor_relation=event_corridor_relation,
    )
    extra_labels = [label for label in (station_subset_label, event_subset_label) if label]
    if extra_labels:
        subset_label = "; ".join(extra_labels + ([subset_label] if subset_label else []))
    _require(plot_df, [azimuth_col, value_col])
    fig, ax = plt.subplots(figsize=(8.0, 5.6), dpi=180)
    groups = [(None, plot_df)] if group_col is None or group_col not in plot_df.columns else list(plot_df.groupby(group_col, dropna=False))
    selected_fit = fit_method if fit_method is not None else fit
    palette = plt.get_cmap("tab10")
    for group_index, (label, subset) in enumerate(groups):
        x = pd.to_numeric(subset[azimuth_col], errors="coerce") % 360.0
        y = pd.to_numeric(subset[value_col], errors="coerce")
        trend = pd.DataFrame({"x": x, "y": y}).dropna().sort_values("x")
        if trend.empty:
            continue
        legend_label = display_label(label) if label is not None else None
        color = palette(group_index % 10)
        if selected_fit is None:
            ax.plot(trend["x"], trend["y"], marker="o", markersize=4.0, linewidth=1.1, alpha=0.78, color=color, label=legend_label)
        else:
            ax.scatter(trend["x"], trend["y"], s=24, alpha=0.70, color=color, label=legend_label)
            draw_scatter_fit(ax, trend["x"].to_numpy(dtype=float), trend["y"].to_numpy(dtype=float), fit_method=selected_fit, lowess_frac=lowess_frac, color=color, label=legend_label)
    if _uses_zero_reference(value_col):
        ax.axhline(0.0, color="black", linewidth=0.8, linestyle=":")
    ax.set_xlim(0.0, 360.0)
    ax.set_xlabel("Azimuth (deg)")
    ax.set_ylabel(value_column_display_name(value_col))
    apply_figure_context(
        ax,
        plot_df,
        value_col=value_col,
        title=title,
        max_values=3,
        include_metric=not (group_col == "metric"),
        include_model=not (group_col == "model"),
        include_value=False,
        extra=[subset_label] if subset_label else None,
    )
    ax.grid(True, alpha=0.25)
    if group_col and group_col in df.columns:
        handles, labels = ax.get_legend_handles_labels()
        if handles and labels:
            fig.subplots_adjust(bottom=0.28, top=0.84)
            fig.legend(handles, labels, frameon=True, fontsize=8, loc="lower center", bbox_to_anchor=(0.5, 0.02), ncol=2)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_path_bin_summary(
    path_summary_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    distance_col: str = "distance_bin_km",
    azimuth_col: str = "azimuth_bin_deg",
    value_col: str = "mean_residual",
    title: str = "Path-Bin Residual Summary",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot distance/azimuth binned residual values as a heatmap."""

    _require(path_summary_df, [distance_col, azimuth_col, value_col])
    work = path_summary_df.copy()
    work[azimuth_col] = pd.to_numeric(work[azimuth_col], errors="coerce") % 360.0
    pivot = work.pivot_table(index=azimuth_col, columns=distance_col, values=value_col, aggfunc="mean").sort_index()
    count_pivot = _path_count_pivot(path_summary_df, index_col=azimuth_col, column_col=distance_col)
    return _heatmap(
        pivot,
        output_path,
        title=title,
        cbar_label=value_column_display_name(value_col),
        x_label="Distance bin (km)",
        y_label="Azimuth bin (deg)",
        context_df=work,
        value_col=value_col,
        annotation_pivot=count_pivot,
        showfig=showfig,
        savefig=savefig,
        outpath=outpath,
    )


def plot_residual_correlation(
    correlation_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    x_col: str = "feature_value",
    y_col: str = "residual",
    group_col: str | None = None,
    fit_method: str | Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray] | pd.DataFrame] | None = None,
    lowess_frac: float = 0.65,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    station_region_col: str | None = None,
    station_regions: Sequence[str] | str | None = None,
    station_region_relation: str = "inside",
    event_region_col: str | None = None,
    event_regions: Sequence[str] | str | None = None,
    event_region_relation: str = "inside",
    station_bounds: tuple[float, float, float, float] | None = None,
    station_bounds_relation: str = "inside",
    event_bounds: tuple[float, float, float, float] | None = None,
    event_bounds_relation: str = "inside",
    station_corridor_col: str | None = None,
    station_corridors: Sequence[str] | str | None = None,
    station_corridor_relation: str = "inside",
    event_corridor_col: str | None = None,
    event_corridors: Sequence[str] | str | None = None,
    event_corridor_relation: str = "inside",
    title: str = "Residual Correlation",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot residuals against a spatial or geologic feature.

    Parameters
    ----------
    correlation_df
        Input table containing x and y columns.
    output_path, outpath
        Optional destination for saving the figure.
    x_col, y_col
        Columns plotted on the x and y axes.
    group_col
        Optional column used to color points and fit one line per group.
    fit_method
        Optional line-fitting mode. Supported strings are ``"point-to-point"``,
        ``"best"``, ``"linear"``, ``"inverse"``, ``"inverse-square"``, ``"quadratic"``,
        ``"exponential-decay"``, and ``"lowess"``. A callable can also be
        supplied; it receives finite ``x`` and ``y`` arrays and should return
        either ``(x_fit, y_fit)`` or a dataframe with ``x`` and ``y`` columns.
    lowess_frac
        Fraction of points used by LOWESS when ``fit_method="lowess"``.

    Returns
    -------
    matplotlib.figure.Figure
        The finished figure.
    """

    plot_df, subset_label = apply_figure_spatial_selection(
        correlation_df,
        spatial_selection,
        station_region_col=station_region_col,
        station_regions=station_regions,
        station_region_relation=station_region_relation,
        event_region_col=event_region_col,
        event_regions=event_regions,
        event_region_relation=event_region_relation,
        station_bounds=station_bounds,
        station_bounds_relation=station_bounds_relation,
        event_bounds=event_bounds,
        event_bounds_relation=event_bounds_relation,
        station_corridor_col=station_corridor_col,
        station_corridors=station_corridors,
        station_corridor_relation=station_corridor_relation,
        event_corridor_col=event_corridor_col,
        event_corridors=event_corridors,
        event_corridor_relation=event_corridor_relation,
    )
    _require(plot_df, [x_col, y_col])
    fig, ax = plt.subplots(figsize=(7.0, 5.0), dpi=180)
    groups = [(None, plot_df)] if group_col is None or group_col not in plot_df.columns else list(plot_df.groupby(group_col, dropna=False))
    palette = plt.get_cmap("tab10")
    for group_index, (label, subset) in enumerate(groups):
        x = pd.to_numeric(subset[x_col], errors="coerce")
        y = pd.to_numeric(subset[y_col], errors="coerce")
        finite = x.notna() & y.notna()
        color = palette(group_index % 10)
        legend_label = _group_display_label(label, group_col) if label is not None else None
        ax.scatter(x[finite], y[finite], s=28, alpha=0.74, color=color, label=legend_label)
        draw_scatter_fit(ax, x[finite].to_numpy(dtype=float), y[finite].to_numpy(dtype=float), fit_method=fit_method, lowess_frac=lowess_frac, color=color, label=legend_label)
    if _uses_zero_reference(y_col):
        ax.axhline(0.0, color="black", linewidth=0.8, linestyle=":")
    ax.set_xlabel(_feature_axis_label(x_col))
    ax.set_ylabel(value_column_display_name(y_col))
    apply_figure_context(ax, plot_df, value_col=y_col, title=title, max_values=3, include_value=False, include_period=not (group_col in {"band", "passband"}), extra=[subset_label] if subset_label else None)
    ax.grid(True, alpha=0.25)
    if group_col and group_col in correlation_df.columns:
        ax.legend(frameon=True, fontsize=8, title=display_label(group_col))
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_polar_residuals(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    azimuth_col: str = "azimuth_deg",
    radius_col: str = "distance_km",
    value_col: str = "residual",
    facet_col: str | None = None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    station_region_col: str | None = None,
    station_regions: Sequence[str] | str | None = None,
    station_region_relation: str = "inside",
    event_region_col: str | None = None,
    event_regions: Sequence[str] | str | None = None,
    event_region_relation: str = "inside",
    station_bounds: tuple[float, float, float, float] | None = None,
    station_bounds_relation: str = "inside",
    event_bounds: tuple[float, float, float, float] | None = None,
    event_bounds_relation: str = "inside",
    station_corridor_col: str | None = None,
    station_corridors: Sequence[str] | str | None = None,
    station_corridor_relation: str = "inside",
    event_corridor_col: str | None = None,
    event_corridors: Sequence[str] | str | None = None,
    event_corridor_relation: str = "inside",
    station_subset_label: str | None = None,
    event_subset_label: str | None = None,
    title: str = "Polar Residuals",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot residuals on polar azimuth/distance axes."""

    plot_df, subset_label = apply_figure_spatial_selection(
        df,
        spatial_selection,
        station_region_col=station_region_col,
        station_regions=station_regions,
        station_region_relation=station_region_relation,
        event_region_col=event_region_col,
        event_regions=event_regions,
        event_region_relation=event_region_relation,
        station_bounds=station_bounds,
        station_bounds_relation=station_bounds_relation,
        event_bounds=event_bounds,
        event_bounds_relation=event_bounds_relation,
        station_corridor_col=station_corridor_col,
        station_corridors=station_corridors,
        station_corridor_relation=station_corridor_relation,
        event_corridor_col=event_corridor_col,
        event_corridors=event_corridors,
        event_corridor_relation=event_corridor_relation,
    )
    extra_labels = [label for label in (station_subset_label, event_subset_label) if label]
    if extra_labels:
        subset_label = "; ".join(extra_labels + ([subset_label] if subset_label else []))
    _require(plot_df, [azimuth_col, radius_col, value_col])
    values = pd.to_numeric(plot_df[value_col], errors="coerce")
    cmap, vmin, vmax = value_color_settings(values.to_numpy(dtype=float), value_col, plot_df)
    radius_max = float(pd.to_numeric(plot_df[radius_col], errors="coerce").max())
    if not np.isfinite(radius_max) or radius_max <= 0.0:
        radius_max = 1.0
    if facet_col and facet_col in plot_df.columns:
        groups = [(label, subset.copy()) for label, subset in plot_df.groupby(facet_col, dropna=False)]
        n_groups = len(groups)
        ncols = 2 if n_groups > 1 else 1
        nrows = int(np.ceil(n_groups / ncols))
        fig, axes = plt.subplots(nrows, ncols, figsize=(5.4 * ncols, 4.9 * nrows), dpi=180, subplot_kw={"projection": "polar"}, squeeze=False)
        scatter = None
        for ax, (label, subset) in zip(axes.ravel(), groups):
            scatter = _draw_polar_residual_axis(ax, subset, azimuth_col=azimuth_col, radius_col=radius_col, value_col=value_col, cmap=cmap, vmin=vmin, vmax=vmax, radius_max=radius_max)
            ax.set_title(_polar_facet_label(label, facet_col), fontsize=10)
        for ax in axes.ravel()[n_groups:]:
            ax.set_axis_off()
        context = figure_context_text(
            plot_df,
            value_col=value_col,
            max_values=3,
            include_value=False,
            include_metric=False,
            extra=[subset_label] if subset_label else None,
        )
        fig.suptitle(f"{title}\n{context}" if context else title)
        fig.subplots_adjust(left=0.06, right=0.82, bottom=0.06, top=0.86, wspace=0.48, hspace=0.48)
        if scatter is not None:
            fig.colorbar(scatter, ax=axes.ravel().tolist(), pad=0.08, label=value_column_display_name(value_col))
    else:
        fig, ax = plt.subplots(figsize=(6.4, 6.0), dpi=180, subplot_kw={"projection": "polar"})
        scatter = _draw_polar_residual_axis(ax, plot_df, azimuth_col=azimuth_col, radius_col=radius_col, value_col=value_col, cmap=cmap, vmin=vmin, vmax=vmax, radius_max=radius_max)
        apply_figure_context(ax, plot_df, value_col=value_col, title=title, max_values=3, include_value=False, extra=[subset_label] if subset_label else None)
        fig.colorbar(scatter, ax=ax, pad=0.12, label=value_column_display_name(value_col))
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_geology_contrast(
    events: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    station_metadata: pd.DataFrame | None = None,
    contrast_df: pd.DataFrame | None = None,
    station_col: str = "station",
    value_col: str = "field_centered",
    group_col: str | None = None,
    left_values: tuple[str, ...] | None = None,
    right_values: tuple[str, ...] | None = None,
    baseline_values: tuple[str, ...] | None = None,
    compare_values: tuple[str, ...] | list[str] | list[tuple[str, ...]] | None = None,
    class_values: tuple[str, ...] | list[str] | None = None,
    statistic: str | None = None,
    title: str | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot two-sided or baseline-relative geology residual contrasts.

    Parameters
    ----------
    events
        Event-station residual table.
    output_path
        Optional figure path for older positional usage.
    station_metadata
        Optional station metadata table containing the grouping column.
    contrast_df
        Optional output from ``bootstrap_contrast_table`` used to annotate the
        effect, confidence interval, and p-value.
    station_col, value_col
        Station and residual-value columns.
    group_col
        Metadata class column. When omitted, the active config value is used.
    left_values, right_values
        Class labels compared as ``mean(left) - mean(right)``. These names are
        comparison sides, not map directions.
    baseline_values, compare_values, class_values
        Optional baseline mode. When ``baseline_values`` is set, the plot shows
        the baseline class and each comparison class. The contrast table and
        annotation report ``comparison - baseline`` for each comparison.
    statistic
        Station-summary statistic used for bootstrap contrasts. Choose
        ``"mean"`` or ``"median"``.
    title
        Optional figure title.
    showfig, savefig, outpath
        Standard Spatial-VTK display and save controls.

    Returns
    -------
    matplotlib.figure.Figure
        Figure showing the residual distributions for configured classes.
    """

    settings = spatial_statistics_settings_from_config()
    selected_group_col = group_col or settings.geology_group_column
    selected_left_values = left_values or settings.geology_left_values
    selected_right_values = right_values or settings.geology_right_values
    selected_statistic = statistic or settings.geology_statistic
    work = events.copy()
    if station_metadata is not None and selected_group_col not in work.columns:
        metadata_cols = [station_col, selected_group_col]
        missing_metadata = [column for column in metadata_cols if column not in station_metadata.columns]
        if missing_metadata:
            raise KeyError(f"Missing station metadata columns for geology contrast plot: {missing_metadata}")
        work = work.merge(station_metadata[metadata_cols].drop_duplicates(subset=[station_col]), on=station_col, how="left")
    _require(work, [station_col, value_col, selected_group_col])

    if contrast_df is None:
        contrast_df = bootstrap_contrast_table(
            work,
            station_col=station_col,
            value_col=value_col,
            group_col=selected_group_col,
            left_values=selected_left_values,
            right_values=selected_right_values,
            baseline_values=baseline_values,
            compare_values=compare_values,
            class_values=class_values,
            statistic=selected_statistic,
        )
    group_specs = _plot_group_specs(
        work,
        group_col=selected_group_col,
        left_values=selected_left_values,
        right_values=selected_right_values,
        baseline_values=baseline_values,
        compare_values=compare_values,
        class_values=class_values,
        contrast_df=contrast_df,
    )
    values = [
        pd.to_numeric(work.loc[work[selected_group_col].astype(str).isin(values_tuple), value_col], errors="coerce")
        .dropna()
        .to_numpy(dtype=float)
        for _label, values_tuple in group_specs
    ]
    labels = [label for label, _values_tuple in group_specs]

    fig_width = max(7.2, 1.25 * max(2, len(labels)) + 4.2)
    fig, ax = plt.subplots(figsize=(fig_width, 6.4), dpi=180)
    if any(len(item) for item in values):
        try:
            boxplot = ax.boxplot(values, tick_labels=labels, patch_artist=True, widths=0.55, showfliers=False)
        except TypeError:
            boxplot = ax.boxplot(values, labels=labels, patch_artist=True, widths=0.55, showfliers=False)
        colors = _class_colors(len(labels))
        for patch, color in zip(boxplot["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.35)
        rng = np.random.default_rng(42)
        for index, data in enumerate(values, start=1):
            if len(data) == 0:
                continue
            jitter = rng.normal(0.0, 0.035, size=len(data))
            ax.scatter(np.full(len(data), index) + jitter, data, s=18, alpha=0.58, color=colors[index - 1], edgecolors="black", linewidths=0.2)
    else:
        ax.text(0.5, 0.5, "No rows matched the configured geology classes.", ha="center", va="center", transform=ax.transAxes)
        ax.set_xticks(np.arange(1, len(labels) + 1))
        ax.set_xticklabels(labels)
    if _uses_zero_reference(value_col):
        ax.axhline(0.0, color="black", linewidth=0.8, linestyle=":")
    ax.set_xlabel(display_label(selected_group_col))
    ax.set_ylabel(context_value_label(value_col, work))
    plot_title = title or _geology_title(contrast_df, labels)
    apply_figure_context(ax, work, value_col=value_col, title=plot_title, max_values=3, include_value=False)
    ax.grid(True, axis="y", alpha=0.25)
    _annotate_contrast(ax, contrast_df)
    if contrast_df is not None and not contrast_df.empty:
        fig.subplots_adjust(bottom=0.34)
    return finish_figure(fig, output_path, outpath=outpath, output_key="geology_contrast", showfig=showfig, savefig=savefig)


def _heatmap(
    pivot: pd.DataFrame,
    output_path: str | Path | None,
    *,
    title: str,
    cbar_label: str,
    x_label: str,
    y_label: str,
    context_df: pd.DataFrame | None = None,
    value_col: str | None = None,
    annotation_pivot: pd.DataFrame | None = None,
    cmap: str = "coolwarm",
    include_model: bool = True,
    extra: Sequence[str] | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Draw numeric heatmap."""

    if pivot.empty:
        fig, ax = plt.subplots(figsize=(7.5, 5.2), dpi=180)
        ax.text(0.5, 0.5, "No rows matched the heatmap request", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)
    values = pivot.to_numpy(dtype=float)
    cmap, vmin, vmax = value_color_settings(values, value_col, context_df, diverging_cmap=cmap, sequential_cmap="viridis")
    fig, ax = plt.subplots(figsize=(7.5, 5.2), dpi=180)
    image = ax.imshow(values, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xticks(np.arange(pivot.shape[1]))
    ax.set_xticklabels(pivot.columns.astype(str), rotation=35, ha="right")
    ax.set_yticks(np.arange(pivot.shape[0]))
    ax.set_yticklabels(pivot.index.astype(str))
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if annotation_pivot is not None and not annotation_pivot.empty:
        aligned = annotation_pivot.reindex(index=pivot.index, columns=pivot.columns)
        for row_index, index_value in enumerate(pivot.index):
            for col_index, column_value in enumerate(pivot.columns):
                annotation = aligned.loc[index_value, column_value]
                if pd.notna(annotation) and str(annotation).strip():
                    ax.text(col_index, row_index, str(annotation), ha="center", va="center", fontsize=7.0, color="black")
    apply_figure_context(
        ax,
        context_df,
        value_col=value_col,
        title=title,
        max_values=3,
        include_counts=False,
        include_metric=False,
        include_model=include_model,
        include_value=False,
        max_line_chars=72,
        extra=extra,
    )
    fig.colorbar(image, ax=ax, pad=0.04, label=cbar_label)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _categorical_metric_plot_data(
    data: pd.DataFrame,
    *,
    dep: str | Sequence[str],
    indep: str,
    value_col: str,
    passband: str | Sequence[str],
    model: str | Sequence[str] | None,
    component: str | Sequence[str] | None,
    station: str | Sequence[str] | None,
    event_id: str | Sequence[str] | None,
    filters: dict[str, object] | None,
    spatial_selection: FigureSpatialSelection | dict[str, object] | None = None,
    station_region_col: str | None = None,
    station_regions: Sequence[str] | str | None = None,
    station_region_relation: str = "inside",
    event_region_col: str | None = None,
    event_regions: Sequence[str] | str | None = None,
    event_region_relation: str = "inside",
    station_bounds: tuple[float, float, float, float] | None = None,
    station_bounds_relation: str = "inside",
    event_bounds: tuple[float, float, float, float] | None = None,
    event_bounds_relation: str = "inside",
    station_corridor_col: str | None = None,
    station_corridors: Sequence[str] | str | None = None,
    station_corridor_relation: str = "inside",
    event_corridor_col: str | None = None,
    event_corridors: Sequence[str] | str | None = None,
    event_corridor_relation: str = "inside",
) -> tuple[pd.DataFrame, str, str, list[str], str, str | None]:
    """Return normalized categorical metric rows for boxplots and heatmaps.

    Inputs are a metric table and required plotting controls. The output table
    contains a resolved categorical column, a numeric ``_plot_value`` column,
    and a readable ``dep`` column for metric grouping.
    """

    if value_col is None or str(value_col).strip() == "":
        raise ValueError("value_col is required.")
    if passband is None:
        raise ValueError("passband is required.")
    _validate_model_requirement(data, value_col=value_col, model=model)
    work = _filter_scatter_data(
        data,
        passband=None if _is_all_filter(passband) else passband,
        model=model,
        component=component,
        station=station,
        event_id=event_id,
        filters=filters,
    )
    work, subset_label = apply_figure_spatial_selection(
        work,
        spatial_selection,
        station_region_col=station_region_col,
        station_regions=station_regions,
        station_region_relation=station_region_relation,
        event_region_col=event_region_col,
        event_regions=event_regions,
        event_region_relation=event_region_relation,
        station_bounds=station_bounds,
        station_bounds_relation=station_bounds_relation,
        event_bounds=event_bounds,
        event_bounds_relation=event_bounds_relation,
        station_corridor_col=station_corridor_col,
        station_corridors=station_corridors,
        station_corridor_relation=station_corridor_relation,
        event_corridor_col=event_corridor_col,
        event_corridors=event_corridors,
        event_corridor_relation=event_corridor_relation,
    )
    plot_df, category_col, value_column, dep_labels, resolved_value_col = _scatter_long_form(work, indep=indep, dep=dep, value_col=value_col)
    if "dep" not in plot_df.columns:
        plot_df["dep"] = _short_join(dep_labels)
    plot_df["_plot_value"] = pd.to_numeric(plot_df[value_column], errors="coerce")
    plot_df = plot_df.dropna(subset=[category_col, "_plot_value"]).copy()
    plot_df[category_col] = plot_df[category_col].map(_category_display_label)
    return plot_df, category_col, "_plot_value", dep_labels, resolved_value_col or value_column, subset_label


def _context_should_include_model(value_col: str | None) -> bool:
    """Return whether figure context should include the synthetic model."""

    return value_requires_model(value_col)


def _is_all_filter(values: object) -> bool:
    """Return whether a filter explicitly requests all available values."""

    items = _as_list(values)
    return len(items) == 1 and str(items[0]).strip().lower() == "all"


def _validate_model_requirement(data: pd.DataFrame, *, value_col: str, model: str | Sequence[str] | None) -> None:
    """Require model selection for model-dependent values when needed."""

    if model is not None or not _value_col_requires_model(value_col):
        return
    model_col = _first_existing_column(data, ["model", "simulation_model", "synthetic_model"])
    if model_col is None:
        return
    available = [value for value in pd.unique(data[model_col].dropna()) if str(value).strip()]
    if len(available) > 1:
        raise ValueError(f"model is required for value_col={value_col!r}. Available models: {', '.join(map(str, available))}")


def _value_col_requires_model(value_col: str | None) -> bool:
    """Return whether a plotted value depends on synthetic/model outputs."""

    return value_requires_model(value_col)


def _ordered_categories(series: pd.Series) -> list[str]:
    """Return stable categorical labels in dataframe order."""

    return [str(value) for value in pd.unique(series.dropna())]


def _category_display_label(value: object) -> str:
    """Return a readable category label."""

    text = str(value)
    if ":" in text:
        return text.split(":", 1)[-1]
    return display_label(text)


def _move_baseline_categories_first(categories: list[str], compare_to: str | Sequence[str]) -> list[str]:
    """Move comparison baseline categories to the front of an x-axis."""

    baselines = [_category_display_label(value) for value in _as_list(compare_to)]
    front = [category for category in categories if category in baselines]
    rest = [category for category in categories if category not in set(front)]
    return front + rest


def _draw_grouped_boxplot(
    ax: plt.Axes,
    plot_df: pd.DataFrame,
    *,
    category_col: str,
    color_col: str,
    value_col: str,
    categories: list[str],
    color_values: list[str],
    color_lookup: dict[str, object],
) -> None:
    """Draw category-grouped boxplots with jittered sample points."""

    n_colors = max(1, len(color_values))
    total_width = 0.72
    box_width = min(0.28, total_width / n_colors * 0.82)
    offsets = np.linspace(-total_width / 2.0 + box_width / 2.0, total_width / 2.0 - box_width / 2.0, n_colors)
    rng = np.random.default_rng(42)
    plotted_positions: list[float] = []
    plotted_values: list[np.ndarray] = []
    plotted_colors: list[object] = []
    for category_index, category in enumerate(categories):
        for color_index, color_value in enumerate(color_values):
            subset = plot_df.loc[(plot_df[category_col].astype(str) == category) & (plot_df[color_col].astype(str) == color_value), value_col]
            values = pd.to_numeric(subset, errors="coerce").dropna().to_numpy(dtype=float)
            if len(values) == 0:
                continue
            position = category_index + 1 + float(offsets[color_index])
            plotted_positions.append(position)
            plotted_values.append(values)
            plotted_colors.append(color_lookup[color_value])
    if plotted_values:
        try:
            result = ax.boxplot(plotted_values, positions=plotted_positions, widths=box_width, patch_artist=True, showfliers=False, manage_ticks=False)
        except TypeError:
            result = ax.boxplot(plotted_values, positions=plotted_positions, widths=box_width, patch_artist=True, showfliers=False)
        for patch, color in zip(result["boxes"], plotted_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.35)
            patch.set_edgecolor(color)
        for median in result["medians"]:
            median.set_color("0.18")
            median.set_linewidth(1.2)
        for position, values, color in zip(plotted_positions, plotted_values, plotted_colors):
            jitter = rng.normal(0.0, box_width * 0.09, size=len(values))
            ax.scatter(np.full(len(values), position) + jitter, values, s=18, alpha=0.58, color=color, edgecolors="black", linewidths=0.2)
    ax.set_xlim(0.4, len(categories) + 0.6)
    ax.set_xticks(np.arange(1, len(categories) + 1))
    ax.set_xticklabels(categories, rotation=20, ha="right")


def _draw_boxplot_legend(ax: plt.Axes, color_values: list[str], color_lookup: dict[str, object], color_col: str) -> None:
    """Draw a readable legend for grouped boxplots."""

    handles = [Patch(facecolor=color_lookup[value], edgecolor=color_lookup[value], alpha=0.35, label=_group_display_label(value, color_col)) for value in color_values]
    ax.legend(handles=handles, frameon=True, fontsize=8, title=_scatter_group_title(color_col))


def _categorical_comparison_rows(
    plot_df: pd.DataFrame,
    *,
    category_col: str,
    color_col: str,
    value_col: str,
    compare_to: str | Sequence[str],
    statistic: str,
    n_bootstrap: int,
    random_seed: int,
) -> list[list[str]]:
    """Return baseline-comparison rows for an optional boxplot table."""

    baseline_labels = {_category_display_label(value) for value in _as_list(compare_to)}
    available = set(plot_df[category_col].astype(str).dropna())
    matched_baseline = baseline_labels & available
    if not matched_baseline:
        raise ValueError(f"compare_to={compare_to!r} did not match available categories: {', '.join(sorted(available))}")
    baseline = sorted(matched_baseline)[0]
    rows: list[list[str]] = []
    group_values = _ordered_categories(plot_df[color_col]) if color_col in plot_df.columns else ["Distribution"]
    for group_value in group_values:
        group_df = plot_df.loc[plot_df[color_col].astype(str).eq(str(group_value))] if color_col in plot_df.columns else plot_df
        baseline_values = pd.to_numeric(group_df.loc[group_df[category_col].astype(str).eq(baseline), value_col], errors="coerce").dropna().to_numpy(dtype=float)
        if len(baseline_values) == 0:
            continue
        for category in _ordered_categories(group_df[category_col]):
            if str(category) == baseline:
                continue
            compare_values = pd.to_numeric(group_df.loc[group_df[category_col].astype(str).eq(str(category)), value_col], errors="coerce").dropna().to_numpy(dtype=float)
            if len(compare_values) == 0:
                continue
            effect, low, high = _bootstrap_difference(compare_values, baseline_values, statistic=statistic, n_bootstrap=n_bootstrap, random_seed=random_seed)
            pvalue = _two_sample_pvalue(compare_values, baseline_values)
            comparison = f"{_compact_group_label(group_value, color_col)}: {category} - {baseline}" if color_col == "dep" else f"{category} - {baseline}"
            rows.append([comparison, f"{effect:+.3g}", f"{low:+.3g} to {high:+.3g}", _format_pvalue(pvalue), f"{len(compare_values)}/{len(baseline_values)}"])
    return rows


def _bootstrap_difference(
    values: np.ndarray,
    baseline: np.ndarray,
    *,
    statistic: str,
    n_bootstrap: int,
    random_seed: int,
) -> tuple[float, float, float]:
    """Return statistic(values) - statistic(baseline) and bootstrap CI."""

    reducer = np.nanmean if str(statistic).lower() == "mean" else np.nanmedian
    effect = float(reducer(values) - reducer(baseline))
    if len(values) < 1 or len(baseline) < 1 or n_bootstrap <= 0:
        return effect, np.nan, np.nan
    rng = np.random.default_rng(random_seed)
    diffs = np.empty(int(n_bootstrap), dtype=float)
    for index in range(int(n_bootstrap)):
        sampled = rng.choice(values, size=len(values), replace=True)
        sampled_baseline = rng.choice(baseline, size=len(baseline), replace=True)
        diffs[index] = float(reducer(sampled) - reducer(sampled_baseline))
    low, high = np.nanpercentile(diffs, [2.5, 97.5])
    return effect, float(low), float(high)


def _two_sample_pvalue(values: np.ndarray, baseline: np.ndarray) -> float:
    """Return a robust two-sample p-value for category comparisons."""

    if len(values) < 1 or len(baseline) < 1:
        return np.nan
    try:
        from scipy.stats import mannwhitneyu

        result = mannwhitneyu(values, baseline, alternative="two-sided")
        return float(result.pvalue)
    except Exception:
        return np.nan


def _categorical_plot_title(dep_labels: list[str], category_col: str, value_col: str | None, *, plot_type: str) -> str:
    """Return a readable title for categorical metric plots."""

    return f"{_readable_label_join(dep_labels)} by {display_label(category_col)} {plot_type}"


def _readable_label_join(labels: Sequence[str]) -> str:
    """Return a readable title join without hiding metric names."""

    clean = [str(label) for label in labels if str(label).strip()]
    if not clean:
        return "Metric"
    if len(clean) == 1:
        return clean[0]
    if len(clean) == 2:
        return f"{clean[0]} and {clean[1]}"
    return f"{', '.join(clean[:-1])}, and {clean[-1]}"


def _compact_group_label(value: object, group_col: str | None) -> str:
    """Return a compact table label for grouped categorical comparisons."""

    label = _group_display_label(value, group_col)
    if "(" in label and ")" in label:
        return label.rsplit("(", 1)[-1].split(")", 1)[0]
    return label


def _draw_polar_residual_axis(
    ax: plt.Axes,
    df: pd.DataFrame,
    *,
    azimuth_col: str,
    radius_col: str,
    value_col: str,
    cmap: str,
    vmin: float,
    vmax: float,
    radius_max: float,
) -> plt.Collection:
    """Draw residual points on one polar axis.

    Inputs are a dataframe with azimuth, radius, and value columns plus a
    symmetric color limit. The output is the scatter artist used for colorbars.
    """

    theta = np.radians(pd.to_numeric(df[azimuth_col], errors="coerce") % 360.0)
    radius = pd.to_numeric(df[radius_col], errors="coerce")
    values = pd.to_numeric(df[value_col], errors="coerce")
    scatter = ax.scatter(theta, radius, c=values, cmap=cmap, vmin=vmin, vmax=vmax, s=30, edgecolors="black", linewidths=0.25)
    ax.set_ylim(0.0, radius_max * 1.05)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    return scatter


def _draw_scatter_fit(
    ax: plt.Axes,
    x: np.ndarray,
    y: np.ndarray,
    *,
    fit_method: str | Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray] | pd.DataFrame] | None,
    lowess_frac: float,
    color: object,
    label: str | None,
) -> None:
    """Draw an optional fitted line for one scatter group.

    Inputs are finite x/y arrays, a configured fitting method, and display
    styling. The output is a line added to the axis when enough points are
    available for the requested method.
    """

    if fit_method is None or len(x) < 2:
        return
    order = np.argsort(x)
    x_sorted = x[order]
    y_sorted = y[order]
    method = fit_method
    method_name = "custom"
    if callable(method):
        fit_x, fit_y = _call_user_fit(method, x_sorted, y_sorted)
    else:
        method_name = str(method).strip().lower().replace("_", "-")
        if method_name in {"point-to-point", "points", "connect"}:
            fit_x, fit_y = x_sorted, y_sorted
        elif method_name == "linear":
            fit_x, fit_y = _polynomial_fit(x_sorted, y_sorted, degree=1)
        elif method_name in {"inverse", "1/x", "reciprocal"}:
            fit_x, fit_y = _inverse_fit(x_sorted, y_sorted, power=1)
        elif method_name in {"inverse-square", "inverse-squared", "1/x2", "1/x^2", "reciprocal-square"}:
            fit_x, fit_y = _inverse_fit(x_sorted, y_sorted, power=2)
        elif method_name in {"quadratic", "x2", "x^2", "second-order"}:
            fit_x, fit_y = _polynomial_fit(x_sorted, y_sorted, degree=2)
        elif method_name in {"exponential-decay", "exponential", "exp-decay"}:
            fit_x, fit_y = _exponential_decay_fit(x_sorted, y_sorted)
        elif method_name == "lowess":
            fit_x, fit_y = _lowess_fit(x_sorted, y_sorted, frac=lowess_frac)
        elif method_name == "best":
            method_name, fit_x, fit_y = _best_fit(x_sorted, y_sorted, lowess_frac=lowess_frac)
        else:
            raise ValueError("fit_method must be one of 'point-to-point', 'best', 'linear', 'inverse', 'inverse-square', 'quadratic', 'exponential-decay', 'lowess', a callable, or None.")
    if len(fit_x) == 0:
        return
    fit_label = _scatter_fit_label(method_name, x_sorted, y_sorted, fit_x, fit_y, label=label)
    ax.plot(fit_x, fit_y, color=color, linewidth=1.3, alpha=0.88, label=fit_label)


def _fit_method_has_legend(fit_method: str | Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray] | pd.DataFrame] | None) -> bool:
    """Return whether a scatter fit mode should force a visible legend."""

    if fit_method is None:
        return False
    if callable(fit_method):
        return True
    method_name = str(fit_method).strip().lower().replace("_", "-")
    return method_name not in {"point-to-point", "points", "connect"}


def _scatter_fit_label(method_name: str, x: np.ndarray, y: np.ndarray, fit_x: np.ndarray, fit_y: np.ndarray, *, label: str | None) -> str:
    """Return a readable legend label for a scatter fit line."""

    if method_name in {"point-to-point", "points", "connect"}:
        return "_nolegend_"
    prefix = f"{label} " if label else ""
    slope, fit_r = _fit_line_stats(x, y, fit_x, fit_y)
    if method_name.startswith("best:"):
        fit_name = _scatter_fit_display_name(method_name.split(":", 1)[1])
        return f"{prefix}best fit: {fit_name} (slope={_format_fit_number(slope)}, r={_format_fit_number(fit_r)})"
    fit_name = _scatter_fit_display_name(method_name)
    return f"{prefix}{fit_name} best fit (slope={_format_fit_number(slope)}, r={_format_fit_number(fit_r)})"


def _scatter_fit_display_name(method_name: str) -> str:
    """Return a readable fit method name for legends."""

    if method_name == "linear":
        return "linear"
    if method_name in {"inverse", "1/x", "reciprocal"}:
        return "inverse"
    if method_name in {"inverse-square", "inverse-squared", "1/x2", "1/x^2", "reciprocal-square"}:
        return "inverse-square"
    if method_name in {"quadratic", "x2", "x^2", "second-order"}:
        return "quadratic"
    if method_name in {"exponential-decay", "exponential", "exp-decay"}:
        return "exponential-decay"
    if method_name == "lowess":
        return "LOWESS"
    return "custom"


def _best_fit(x: np.ndarray, y: np.ndarray, *, lowess_frac: float) -> tuple[str, np.ndarray, np.ndarray]:
    """Return the highest-R-squared supported fit for sorted x/y data."""

    candidates: list[tuple[str, np.ndarray, np.ndarray]] = [
        ("linear", *_polynomial_fit(x, y, degree=1)),
        ("inverse", *_inverse_fit(x, y, power=1)),
        ("inverse-square", *_inverse_fit(x, y, power=2)),
        ("quadratic", *_polynomial_fit(x, y, degree=2)),
        ("exponential-decay", *_exponential_decay_fit(x, y)),
        ("lowess", *_lowess_fit(x, y, frac=lowess_frac)),
    ]
    scored: list[tuple[float, str, np.ndarray, np.ndarray]] = []
    for method_name, fit_x, fit_y in candidates:
        score = _fit_r_squared(x, y, fit_x, fit_y)
        if np.isfinite(score):
            scored.append((score, method_name, fit_x, fit_y))
    if not scored:
        return "best", np.array([]), np.array([])
    score, method_name, fit_x, fit_y = max(scored, key=lambda item: item[0])
    return f"best:{method_name}", fit_x, fit_y


def _fit_r_squared(x: np.ndarray, y: np.ndarray, fit_x: np.ndarray, fit_y: np.ndarray) -> float:
    """Return R-squared between observed values and a fitted curve."""

    if len(x) < 2 or len(fit_x) < 2 or len(fit_y) < 2:
        return np.nan
    order = np.argsort(fit_x)
    unique_fit_x, unique_indices = np.unique(fit_x[order], return_index=True)
    unique_fit_y = fit_y[order][unique_indices]
    if len(unique_fit_x) < 2:
        return np.nan
    predicted = np.interp(x, unique_fit_x, unique_fit_y)
    finite = np.isfinite(predicted) & np.isfinite(y)
    if int(np.sum(finite)) < 2:
        return np.nan
    residual = y[finite] - predicted[finite]
    total = y[finite] - float(np.nanmean(y[finite]))
    ss_total = float(np.nansum(total**2))
    if ss_total <= 0.0:
        return np.nan
    return float(1.0 - np.nansum(residual**2) / ss_total)


def _fit_line_stats(x: np.ndarray, y: np.ndarray, fit_x: np.ndarray, fit_y: np.ndarray) -> tuple[float, float]:
    """Return overall fit-line slope and observed-vs-fit Pearson r."""

    if len(x) < 2 or len(fit_x) < 2 or len(fit_y) < 2:
        return np.nan, np.nan
    slope = _overall_fit_slope(fit_x, fit_y)
    order = np.argsort(fit_x)
    unique_fit_x, unique_indices = np.unique(fit_x[order], return_index=True)
    unique_fit_y = fit_y[order][unique_indices]
    if len(unique_fit_x) < 2:
        return slope, np.nan
    predicted = np.interp(x, unique_fit_x, unique_fit_y)
    if np.nanstd(predicted) == 0.0 or np.nanstd(y) == 0.0:
        fit_r = np.nan
    else:
        fit_r = float(np.corrcoef(y, predicted)[0, 1])
    return slope, fit_r


def _overall_fit_slope(fit_x: np.ndarray, fit_y: np.ndarray) -> float:
    """Return endpoint slope for a fitted curve."""

    delta_x = float(fit_x[-1] - fit_x[0])
    if not np.isfinite(delta_x) or abs(delta_x) < 1.0e-12:
        return np.nan
    return float((fit_y[-1] - fit_y[0]) / delta_x)


def _format_fit_number(value: float) -> str:
    """Format a compact fit diagnostic for legends."""

    if not np.isfinite(value):
        return "n/a"
    return f"{value:.3g}"


def _call_user_fit(
    fit_function: Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray] | pd.DataFrame],
    x: np.ndarray,
    y: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Call a user-defined fit function and normalize its output.

    Inputs are finite sorted x/y arrays. The output is a pair of arrays suitable
    for Matplotlib line plotting.
    """

    result = fit_function(x, y)
    if isinstance(result, pd.DataFrame):
        if "x" not in result.columns or "y" not in result.columns:
            raise ValueError("User fit dataframe must contain 'x' and 'y' columns.")
        return result["x"].to_numpy(dtype=float), result["y"].to_numpy(dtype=float)
    fit_x, fit_y = result
    return np.asarray(fit_x, dtype=float), np.asarray(fit_y, dtype=float)


def _polynomial_fit(x: np.ndarray, y: np.ndarray, *, degree: int) -> tuple[np.ndarray, np.ndarray]:
    """Return a least-squares polynomial fit line for sorted x/y values."""

    if len(x) < degree + 1:
        return np.array([]), np.array([])
    coefficients = np.polyfit(x, y, deg=degree)
    fit_x = np.linspace(float(np.nanmin(x)), float(np.nanmax(x)), 100)
    return fit_x, np.polyval(coefficients, fit_x)


def _inverse_fit(x: np.ndarray, y: np.ndarray, *, power: int) -> tuple[np.ndarray, np.ndarray]:
    """Return a least-squares inverse-distance fit line.

    The fitted form is ``intercept + coefficient / x`` for ``power=1`` and
    ``intercept + coefficient / x**2`` for ``power=2``.
    """

    if len(x) < 2:
        return np.array([]), np.array([])
    finite = np.isfinite(x) & np.isfinite(y) & (np.abs(x) > 1.0e-12)
    if int(np.sum(finite)) < 2:
        return np.array([]), np.array([])
    x_valid = x[finite]
    y_valid = y[finite]
    predictor = 1.0 / np.power(x_valid, int(power))
    coefficient, intercept = np.polyfit(predictor, y_valid, deg=1)
    fit_x = np.linspace(float(np.nanmin(x_valid)), float(np.nanmax(x_valid)), 100)
    fit_y = intercept + coefficient / np.power(fit_x, int(power))
    return fit_x, fit_y


def _exponential_decay_fit(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return a simple exponential-decay fit for sorted x/y values.

    The fitted form is ``offset + amplitude * exp(-x / scale)``. If the fit is
    not stable for the supplied points, empty arrays are returned.
    """

    if len(x) < 3:
        return np.array([]), np.array([])
    try:
        from scipy.optimize import curve_fit

        def model(values: np.ndarray, offset: float, amplitude: float, scale: float) -> np.ndarray:
            return offset + amplitude * np.exp(-values / max(scale, 1.0e-6))

        initial = (float(np.nanmedian(y)), float(y[0] - np.nanmedian(y)), max(float(np.nanmax(x) - np.nanmin(x)), 1.0))
        params, _cov = curve_fit(model, x, y, p0=initial, maxfev=5000)
        fit_x = np.linspace(float(np.nanmin(x)), float(np.nanmax(x)), 100)
        return fit_x, model(fit_x, *params)
    except Exception:
        return np.array([]), np.array([])


def _lowess_fit(x: np.ndarray, y: np.ndarray, *, frac: float) -> tuple[np.ndarray, np.ndarray]:
    """Return a LOWESS smooth for sorted x/y values.

    Inputs are finite sorted x/y arrays and the LOWESS fraction. The output is
    the LOWESS x/y line. ``statsmodels`` is a package dependency so this method
    should work in normal Spatial-VTK installs.
    """

    if len(x) < 3:
        return x, y
    from statsmodels.nonparametric.smoothers_lowess import lowess

    smoothed = lowess(y, x, frac=float(np.clip(frac, 0.05, 1.0)), return_sorted=True)
    return smoothed[:, 0], smoothed[:, 1]


def _filter_scatter_data(
    data: pd.DataFrame,
    *,
    passband: str | Sequence[str] | None,
    model: str | Sequence[str] | None,
    component: str | Sequence[str] | None,
    station: str | Sequence[str] | None,
    event_id: str | Sequence[str] | None,
    filters: dict[str, object] | None,
) -> pd.DataFrame:
    """Apply user-friendly scatterplot filters to a dataframe."""

    work = data.copy()
    work = _apply_scatter_filter(work, ["band", "passband", "simulation_band"], passband, normalizer=band_display_label)
    work = _apply_scatter_filter(work, ["model", "simulation_model"], model, normalizer=_normalize_filter_text)
    work = _apply_scatter_filter(work, ["component", "station_component"], component, normalizer=_normalize_filter_text)
    work = _apply_scatter_filter(work, ["station", "station_name"], station, normalizer=_normalize_filter_text)
    work = _apply_scatter_filter(work, ["event_id", "event", "event_title"], event_id, normalizer=_normalize_filter_text)
    for key, value in dict(filters or {}).items():
        column = _resolve_scatter_column(work, key, required=True)
        work = _filter_column_values(work, column, value, normalizer=_normalize_filter_text)
    return work


def _apply_scatter_filter(
    data: pd.DataFrame,
    candidates: Sequence[str],
    values: object,
    *,
    normalizer: Callable[[object], str],
) -> pd.DataFrame:
    """Filter one optional scatterplot field by candidate column names."""

    if values is None:
        return data
    column = _first_existing_column(data, candidates)
    if column is None:
        raise KeyError(f"Cannot apply filter; none of these columns exist: {list(candidates)}")
    return _filter_column_values(data, column, values, normalizer=normalizer)


def _filter_column_values(
    data: pd.DataFrame,
    column: str,
    values: object,
    *,
    normalizer: Callable[[object], str],
) -> pd.DataFrame:
    """Return rows where one column matches one or more normalized values."""

    requested = {normalizer(value) for value in _as_list(values)}
    available = data[column].map(normalizer)
    return data.loc[available.isin(requested)].copy()


def _scatter_long_form(
    data: pd.DataFrame,
    *,
    indep: str,
    dep: str | Sequence[str],
    value_col: str | None,
) -> tuple[pd.DataFrame, str, str, list[str], str | None]:
    """Normalize wide or long metric tables into x/y scatter rows."""

    x_col = _resolve_scatter_column(data, indep, required=True)
    dep_items = [str(item) for item in _as_list(dep)]
    if not dep_items:
        raise ValueError("dep must contain at least one dependent variable.")
    wide_columns = [_resolve_scatter_column(data, item, required=False) for item in dep_items]
    if all(column is not None for column in wide_columns):
        id_columns = [column for column in data.columns if column not in set(wide_columns)]
        melted = data.melt(id_vars=id_columns, value_vars=[str(column) for column in wide_columns], var_name="dep", value_name="_scatter_y")
        melted["dep"] = melted["dep"].map(_dependent_display_label)
        return melted, x_col, "_scatter_y", [_dependent_display_label(item) for item in dep_items], value_col

    metric_col = _first_existing_column(data, ["metric", "metric_name"])
    if metric_col is None:
        missing = [item for item, column in zip(dep_items, wide_columns) if column is None]
        raise KeyError(f"Could not resolve dependent variable columns and no metric column is available for: {missing}")
    metric_map = {_metric_key(value): value for value in data[metric_col].dropna().unique()}
    requested_metrics = []
    for item in dep_items:
        key = _metric_key(item)
        if key not in metric_map:
            print(f"Unknown metric keyword: {item!r}")
            print("Available metric keywords include:")
            print(", ".join(sorted(str(value) for value in data[metric_col].dropna().unique())))
            raise KeyError(f"Metric {item!r} was not found in column {metric_col!r}.")
        requested_metrics.append(metric_map[key])
    resolved_value_col = _resolve_value_col(data, value_col)
    subset = data.loc[data[metric_col].isin(requested_metrics)].copy()
    subset["dep"] = subset[metric_col].map(metric_display_name)
    return subset, x_col, resolved_value_col, [metric_display_name(item) for item in requested_metrics], resolved_value_col


def _resolve_value_col(data: pd.DataFrame, value_col: str | None) -> str:
    """Resolve the y-value column for a long metric table."""

    aliases = {
        "observed": "value_obs",
        "obs": "value_obs",
        "synthetic": "value_syn",
        "syn": "value_syn",
        "sim": "value_syn",
        "log2residualcentered": "log2_residual_centered",
        "log2residualscentered": "log2_residual_centered",
        "centeredlog2residual": "log2_residual_centered",
        "centeredlog2residuals": "log2_residual_centered",
    }
    if value_col is not None:
        requested = aliases.get(_column_key(value_col), aliases.get(str(value_col).strip().lower(), str(value_col)))
        if requested == "log2_residual_centered":
            return _resolve_or_create_centered_value(data, source_col="log2_residual", output_col="log2_residual_centered")
        return _resolve_scatter_column(data, requested, required=True)
    for candidate in ("log2_residual", "residual", "score", "value_obs", "value_syn", "value"):
        column = _resolve_scatter_column(data, candidate, required=False)
        if column is not None:
            return column
    raise KeyError("Could not infer a metric value column. Pass value_col='observed', 'synthetic', 'log2_residual', or another numeric value column.")


def _resolve_or_create_centered_value(data: pd.DataFrame, *, source_col: str, output_col: str) -> str:
    """Resolve or create an event-centered value column for plotting."""

    existing = _resolve_scatter_column(data, output_col, required=False)
    if existing is not None:
        return existing
    source = _resolve_scatter_column(data, source_col, required=True)
    event_col = _first_existing_column(data, ["event_id", "event", "event_title"])
    if event_col is None:
        data[output_col] = pd.to_numeric(data[source], errors="coerce") - float(pd.to_numeric(data[source], errors="coerce").mean())
        return output_col
    group_cols = [event_col]
    for candidate in ("metric", "band", "passband", "component", "model", "simulation_model"):
        if candidate in data.columns:
            group_cols.append(candidate)
    values = pd.to_numeric(data[source], errors="coerce")
    data[output_col] = values - values.groupby([data[column] for column in group_cols]).transform("mean")
    return output_col


def _resolve_scatter_column(data: pd.DataFrame, name: str, *, required: bool) -> str | None:
    """Resolve a user-facing scatterplot name to a dataframe column."""

    aliases = {
        "distance": ("distance_km", "dist_km", "distance", "dist"),
        "dist": ("distance_km", "dist_km", "distance", "dist"),
        "distancekm": ("distance_km", "dist_km", "distance"),
        "distkm": ("distance_km", "dist_km", "distance"),
        "depth": ("depth_km", "event_depth_km", "source_depth_km", "depth"),
        "depthkm": ("depth_km", "event_depth_km", "source_depth_km", "depth"),
        "vs30": ("Vs30", "vs30", "site_vs30", "station_vs30"),
        "latitude": ("lat", "latitude", "station_lat", "sta_lat", "event_lat", "event_latitude"),
        "lat": ("lat", "latitude", "station_lat", "sta_lat", "event_lat", "event_latitude"),
        "longitude": ("lon", "longitude", "station_lon", "sta_lon", "event_lon", "event_longitude"),
        "lon": ("lon", "longitude", "station_lon", "sta_lon", "event_lon", "event_longitude"),
        "passband": ("band", "passband", "period_band", "simulation_band"),
        "periodband": ("band", "passband", "period_band", "simulation_band"),
        "period": ("period_s", "period", "period_sec", "period_seconds"),
        "frequency": ("frequency_hz", "freq_hz", "frequency", "freq"),
        "event": ("event_id", "event", "event_title"),
        "eventid": ("event_id", "event", "event_title"),
        "station": ("station", "station_name", "station_code"),
        "component": ("component", "station_component", "channel_component"),
        "model": ("model", "simulation_model", "synthetic_model"),
        "geology": ("geology", "geologic_description", "geology_class"),
        "geomorphology": ("geomorphology", "geomorphology_class", "geomorphic_class"),
        "geomorphicregion": ("mapped_region_type", "geomorphic_region", "geomorphic_province", "geomorphic province", "region_name"),
        "geomorphicprovince": ("mapped_region_type", "geomorphic_province", "geomorphic_region", "geomorphic province", "region_name"),
        "geomorphic": ("mapped_region_type", "geomorphic_region", "geomorphic_province", "geomorphic province", "region_name"),
        "mappedregion": ("mapped_region", "mapped_region_type", "region_name"),
        "mappedregiontype": ("mapped_region_type", "mapped_region", "region_name"),
        "azimuth": ("azimuth_deg", "azimuth", "azimuth_degrees"),
        "azimuthdeg": ("azimuth_deg", "azimuth", "azimuth_degrees"),
        "magnitude": ("magnitude", "event_magnitude", "mag"),
    }
    text = str(name)
    candidates = [text]
    key = _column_key(text)
    candidates.extend(aliases.get(key, ()))
    lower_lookup = {str(column).lower(): str(column) for column in data.columns}
    normalized_lookup = {_column_key(column): str(column) for column in data.columns}
    for candidate in candidates:
        if candidate in data.columns:
            return str(candidate)
        if str(candidate).lower() in lower_lookup:
            return lower_lookup[str(candidate).lower()]
        candidate_key = _column_key(candidate)
        if candidate_key in normalized_lookup:
            return normalized_lookup[candidate_key]
    if required:
        _print_unknown_scatter_keyword(name, data, aliases)
        raise KeyError(f"Could not resolve scatterplot keyword {name!r}. See printed available keywords.")
    return None


def _column_key(value: object) -> str:
    """Normalize a user-facing column token for permissive matching."""

    return "".join(char for char in str(value).strip().lower() if char.isalnum())


def _print_unknown_scatter_keyword(name: object, data: pd.DataFrame, aliases: dict[str, Sequence[str]]) -> None:
    """Print available scatterplot keywords after an unknown variable request."""

    available = _available_scatter_keywords(data, aliases)
    print(f"Unknown scatterplot keyword: {name!r}")
    print("Available scatterplot keywords include:")
    print(", ".join(available))


def _available_scatter_keywords(data: pd.DataFrame, aliases: dict[str, Sequence[str]]) -> list[str]:
    """Return dataframe columns and active aliases that can be used as keywords."""

    keywords = {str(column) for column in data.columns}
    normalized_columns = {_column_key(column) for column in data.columns}
    for alias, candidates in aliases.items():
        if any(_column_key(candidate) in normalized_columns for candidate in candidates):
            keywords.add(alias)
    return sorted(keywords, key=lambda item: item.lower())


def _scatter_colors(cmap: str | Sequence[object] | None, n_groups: int) -> list[object]:
    """Return colors for grouped scatterplot series."""

    if n_groups <= 0:
        return []
    if cmap is None:
        palette = plt.get_cmap("tab10")
        return [palette(index % 10) for index in range(n_groups)]
    if isinstance(cmap, str):
        palette = plt.get_cmap(cmap)
        if n_groups == 1:
            return [palette(0.0)]
        return [palette(index / max(n_groups - 1, 1)) for index in range(n_groups)]
    colors = list(cmap)
    if not colors:
        return _scatter_colors(None, n_groups)
    return [colors[index % len(colors)] for index in range(n_groups)]


def _scatter_axis_encoder(series: pd.Series) -> dict[str, object]:
    """Return an encoder for numeric or categorical scatterplot axes."""

    numeric = pd.to_numeric(series, errors="coerce")
    nonmissing = series.notna()
    if int(numeric.notna().sum()) == int(nonmissing.sum()):
        return {"categorical": False, "encode": lambda values: pd.to_numeric(values, errors="coerce"), "ticks": None, "labels": None}
    labels = [str(value) for value in pd.unique(series.dropna())]
    label_to_index = {label: index for index, label in enumerate(labels)}

    def encode(values: pd.Series) -> pd.Series:
        return values.map(lambda value: label_to_index.get(str(value), np.nan)).astype(float)

    return {"categorical": True, "encode": encode, "ticks": list(range(len(labels))), "labels": labels}


def _apply_categorical_axis(ax: plt.Axes, axis_info: dict[str, object], *, axis: str) -> None:
    """Apply category ticks to one scatterplot axis when needed."""

    if not axis_info.get("categorical"):
        return
    ticks = axis_info.get("ticks") or []
    labels = axis_info.get("labels") or []
    if axis == "x":
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels, rotation=25, ha="right")
    else:
        ax.set_yticks(ticks)
        ax.set_yticklabels(labels)


def _scatter_y_label(dep_labels: list[str], value_col: str | None, y_col: str, *, data_label: str | None) -> str:
    """Return a readable scatterplot y-axis label."""

    if len(dep_labels) == 1:
        prefix = _value_prefix(value_col, data_label=data_label)
        return f"{prefix} {dep_labels[0]}".strip()
    if value_col:
        return value_column_display_name(value_col)
    return value_column_display_name(y_col)


def _scatter_group_title(group_col: str | None) -> str | None:
    """Return a readable legend title for scatterplot grouping."""

    if group_col is None:
        return None
    if group_col == "dep":
        return "Metric"
    return display_label(group_col)


def _scatter_default_title(dep_labels: list[str], x_col: str, value_col: str | None, *, data_label: str | None) -> str:
    """Return a readable default scatterplot title."""

    dep_text = _short_join(dep_labels)
    prefix = _value_prefix(value_col, data_label=data_label)
    y_text = f"{prefix} {dep_text}".strip()
    return f"{y_text} vs. {_feature_axis_label(x_col)}"


def _value_prefix(value_col: str | None, *, data_label: str | None) -> str:
    """Return a compact prefix describing a scatterplot value source."""

    if data_label:
        return str(data_label)
    if value_col == "value_obs":
        return "Observed"
    if value_col == "value_syn":
        return "Synthetic"
    if value_col == "log2_residual":
        return "Log2 residual"
    if value_col == "ln_residual":
        return "Ln residual"
    if value_col in {"anderson_2004_gof", "olsen_mayhew_gof", "score"}:
        return value_column_display_name(value_col)
    return ""


def _short_join(values: Sequence[str]) -> str:
    """Join a few display labels without overwhelming titles."""

    if len(values) <= 2:
        return " and ".join(values)
    return ", ".join(values[:2]) + f", and {len(values) - 2} more"


def _metric_key(value: object) -> str:
    """Return a case-insensitive key for metric lookup."""

    return normalize_metric_name(value).strip().lower()


def _dependent_display_label(value: object) -> str:
    """Return a readable dependent-variable label."""

    text = str(value).strip()
    upper = text.upper()
    if upper in {"PGA", "PGV", "PGD", "PSA", "FAS", "CAV"}:
        return metric_display_name(upper)
    if upper in {"C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "C13"}:
        return metric_display_name(upper)
    return display_label(text)


def _normalize_filter_text(value: object) -> str:
    """Normalize generic filter values for case-insensitive matching."""

    return str(value).strip().lower()


def _as_list(value: object) -> list[object]:
    """Normalize scalar or sequence values to a list."""

    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return list(value)
    return [value]


def _first_existing_column(df: pd.DataFrame, candidates: Sequence[str]) -> str | None:
    """Return the first available candidate column from a dataframe."""

    for column in candidates:
        if column in df.columns:
            return column
    return None


def _group_display_label(value: object, group_col: str | None) -> str:
    """Return a readable legend label for a grouped scatter series."""

    if group_col in {"band", "passband"}:
        return band_display_label(value)
    if group_col == "metric":
        return metric_display_name(value)
    if group_col == "dep":
        return str(value)
    if group_col in {"model", "simulation_model"}:
        return model_display_name(value)
    return display_label(value)


def _polar_facet_label(value: object, facet_col: str) -> str:
    """Return a readable panel title for polar residual facets.

    Inputs are one facet value and the facet column name. The output is a short
    label suitable for a subplot title.
    """

    if str(facet_col) == "metric":
        return metric_display_name(value)
    return display_label(value)


def _require(df: pd.DataFrame, columns: list[str]) -> None:
    """Raise a clear error for missing columns."""

    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")


def _uses_zero_reference(value_col: str) -> bool:
    """Return whether a metric value should show a zero reference line."""

    return value_uses_zero_reference(value_col)


def _feature_axis_label(column: str) -> str:
    """Return a readable x-axis label for residual-feature scatter plots."""

    if str(column) == "distance_km":
        return "Distance (km)"
    if str(column) in {"depth_km", "event_depth_km"}:
        return "Depth (km)"
    return display_label(column)


def _path_count_pivot(path_summary_df: pd.DataFrame, *, index_col: str, column_col: str) -> pd.DataFrame | None:
    """Return a cell annotation table with event/station counts when present."""

    event_col = _first_existing(path_summary_df, ("n_events", "event_count", "events"))
    station_col = _first_existing(path_summary_df, ("n_stations", "station_count", "stations"))
    if not event_col and not station_col:
        return None
    work = path_summary_df[[index_col, column_col] + [column for column in (event_col, station_col) if column]].copy()
    labels: list[str] = []
    for row in work.itertuples(index=False):
        row_dict = row._asdict()
        parts = []
        if event_col:
            parts.append(f"E={int(float(row_dict[event_col]))}")
        if station_col:
            parts.append(f"S={int(float(row_dict[station_col]))}")
        labels.append("\n".join(parts))
    work["_count_label"] = labels
    return work.pivot_table(index=index_col, columns=column_col, values="_count_label", aggfunc=lambda values: str(values.iloc[0]))


def _first_existing(df: pd.DataFrame, candidates: Sequence[str]) -> str | None:
    """Return the first available candidate column."""

    for column in candidates:
        if column in df.columns:
            return column
    return None


def _apply_station_event_subset(
    df: pd.DataFrame,
    *,
    station_region_col: str | None,
    station_regions: Sequence[str] | str | None,
    event_region_col: str | None,
    event_regions: Sequence[str] | str | None,
    station_bounds: tuple[float, float, float, float] | None,
    event_bounds: tuple[float, float, float, float] | None,
    station_subset_label: str | None,
    event_subset_label: str | None,
) -> tuple[pd.DataFrame, str]:
    """Filter a dataframe to optional station/event regions or bounding boxes."""

    out = df.copy()
    station_label = "All Stations"
    event_label = "All Events"
    if station_region_col and station_regions is not None:
        _require(out, [station_region_col])
        values = _as_set(station_regions)
        out = out.loc[out[station_region_col].astype(str).isin(values)].copy()
        station_label = station_subset_label or _subset_values_label("Stations in", values)
    elif station_bounds is not None:
        out = _filter_bounds(out, station_bounds, lon_candidates=("sta_lon", "station_lon", "station_longitude", "lon"), lat_candidates=("sta_lat", "station_lat", "station_latitude", "lat"))
        station_label = station_subset_label or "Stations in bounding box"
    elif station_subset_label:
        station_label = station_subset_label

    if event_region_col and event_regions is not None:
        _require(out, [event_region_col])
        values = _as_set(event_regions)
        out = out.loc[out[event_region_col].astype(str).isin(values)].copy()
        event_label = event_subset_label or _subset_values_label("Events in", values)
    elif event_bounds is not None:
        out = _filter_bounds(out, event_bounds, lon_candidates=("event_lon", "event_longitude", "source_lon"), lat_candidates=("event_lat", "event_latitude", "source_lat"))
        event_label = event_subset_label or "Events in bounding box"
    elif event_subset_label:
        event_label = event_subset_label

    if out.empty and (station_label != "All Stations" or event_label != "All Events"):
        raise ValueError(f"No rows matched the selected spatial subset: {station_label}; {event_label}.")
    if station_label == "All Stations" and event_label == "All Events":
        return out, ""
    return out, f"{station_label}; {event_label}"


def _as_set(values: Sequence[str] | str) -> set[str]:
    """Return a set of string labels from one or many requested values."""

    if isinstance(values, str):
        return {values}
    return {str(value) for value in values}


def _subset_values_label(prefix: str, values: set[str]) -> str:
    """Return a readable station/event subset label."""

    return f"{prefix} {', '.join(sorted(values))}"


def _filter_bounds(df: pd.DataFrame, bounds: tuple[float, float, float, float], *, lon_candidates: Sequence[str], lat_candidates: Sequence[str]) -> pd.DataFrame:
    """Filter rows to lon/lat bounds using the first matching coordinate columns."""

    lon_col = _first_existing(df, lon_candidates)
    lat_col = _first_existing(df, lat_candidates)
    if lon_col is None or lat_col is None:
        raise KeyError("Could not apply bounds because longitude/latitude columns were not found.")
    west, east, south, north = [float(value) for value in bounds]
    lon = pd.to_numeric(df[lon_col], errors="coerce")
    lat = pd.to_numeric(df[lat_col], errors="coerce")
    return df.loc[lon.between(west, east) & lat.between(south, north)].copy()


def _as_string_tuple(values: tuple[str, ...] | list[str] | str) -> tuple[str, ...]:
    """Return a tuple of string class labels."""

    if isinstance(values, str):
        return (values,)
    return tuple(str(value) for value in values)


def _values_label(values: tuple[str, ...] | list[str] | str) -> str:
    """Return a readable label for one comparison side."""

    clean = [value for value in _as_string_tuple(values) if value]
    return " / ".join(clean) if clean else "unconfigured"


def _plot_group_specs(
    work: pd.DataFrame,
    *,
    group_col: str,
    left_values: tuple[str, ...] | list[str] | str,
    right_values: tuple[str, ...] | list[str] | str,
    baseline_values: tuple[str, ...] | list[str] | str | None,
    compare_values: tuple[str, ...] | list[str] | list[tuple[str, ...]] | None,
    class_values: tuple[str, ...] | list[str] | None,
    contrast_df: pd.DataFrame | None,
) -> list[tuple[str, tuple[str, ...]]]:
    """Resolve plotted geology class groups."""

    specs: list[tuple[str, tuple[str, ...]]] = []
    selected_baseline = _as_string_tuple(baseline_values) if baseline_values is not None else tuple()
    if selected_baseline:
        specs.append((_values_label(selected_baseline), selected_baseline))
        for group in _comparison_groups_for_plot(compare_values, class_values=class_values, baseline_values=selected_baseline, available_values=_available_values(work[group_col])):
            specs.append((_values_label(group), group))
    else:
        specs = [(_values_label(left_values), _as_string_tuple(left_values)), (_values_label(right_values), _as_string_tuple(right_values))]
    deduped: list[tuple[str, tuple[str, ...]]] = []
    seen: set[tuple[str, ...]] = set()
    for label, values in specs:
        key = tuple(values)
        if key and key not in seen:
            deduped.append((label, key))
            seen.add(key)
    return deduped or [("unconfigured", tuple())]


def _comparison_groups_for_plot(
    compare_values: tuple[str, ...] | list[str] | list[tuple[str, ...]] | None,
    *,
    class_values: tuple[str, ...] | list[str] | None,
    baseline_values: tuple[str, ...],
    available_values: tuple[str, ...],
) -> list[tuple[str, ...]]:
    """Resolve plotted baseline comparison groups."""

    if compare_values is None:
        candidates = _as_string_tuple(class_values) if class_values is not None else available_values
        return [(value,) for value in candidates if value not in set(baseline_values)]
    values = list(compare_values)
    if all(isinstance(value, (list, tuple, set)) for value in values):
        return [tuple(str(item) for item in value if str(item)) for value in values]
    return [(str(value),) for value in values if str(value)]


def _available_values(series: pd.Series) -> tuple[str, ...]:
    """Return available geology classes in stable sorted order."""

    values = [str(value) for value in pd.unique(series.dropna()) if str(value).strip()]
    return tuple(sorted(values))


def _class_colors(count: int) -> list[str]:
    """Return visually distinct class colors."""

    palette = plt.get_cmap("tab10")
    return [palette(index % 10) for index in range(max(count, 1))]


def _geology_title(contrast_df: pd.DataFrame | None, labels: list[str]) -> str:
    """Return a concise geology contrast title."""

    if len(labels) == 2:
        return f"Geology Contrast: {labels[0]} minus {labels[1]}"
    if contrast_df is not None and not contrast_df.empty and "baseline_values" in contrast_df.columns and contrast_df["baseline_values"].notna().any():
        baseline = str(contrast_df["baseline_values"].dropna().iloc[0])
        return f"Geology Contrast: classes relative to {baseline}"
    if len(labels) >= 2:
        return f"Geology Contrast: {labels[0]} minus {labels[1]}"
    return "Geology Contrast"


def _annotate_contrast(ax: plt.Axes, contrast_df: pd.DataFrame | None) -> None:
    """Add bootstrap summary statistics below a geology contrast plot."""

    if contrast_df is None or contrast_df.empty:
        return
    rows = _contrast_annotation_rows(contrast_df)
    if not rows:
        return
    add_below_axes_table(
        ax,
        rows=rows,
        columns=["Contrast", "Effect", "95% CI", "p", "Result", "Events"],
        col_widths=[0.34, 0.10, 0.22, 0.08, 0.18, 0.08],
        font_size=7.5,
        max_visible_rows=5,
    )


def _contrast_annotation_rows(contrast_df: pd.DataFrame) -> list[list[str]]:
    """Return compact bootstrap summary rows for the below-plot table."""

    rows = []
    for _index, row in contrast_df.head(5).iterrows():
        label = str(row.get("contrast_label", "") or row.get("effect_direction", "") or "Contrast")
        effect, interval = _effect_and_interval_labels(row)
        if not effect:
            continue
        pvalue = pd.to_numeric(pd.Series([row.get("bootstrap_p")]), errors="coerce").iloc[0]
        p_label = _format_pvalue(float(pvalue)) if np.isfinite(pvalue) else ""
        n_events = row.get("n_events", "")
        rows.append([label, effect, interval, p_label, _significance_label(row), str(n_events) if n_events != "" else ""])
    if len(contrast_df) > 5:
        rows.append([f"{len(contrast_df) - 5} additional contrasts omitted", "", "", "", "", ""])
    return rows


def _effect_and_interval_labels(row: pd.Series) -> tuple[str, str]:
    """Return effect and confidence-interval labels for one contrast row."""

    percent = pd.to_numeric(pd.Series([row.get("percent_effect")]), errors="coerce").iloc[0]
    percent_low = pd.to_numeric(pd.Series([row.get("percent_ci_low")]), errors="coerce").iloc[0]
    percent_high = pd.to_numeric(pd.Series([row.get("percent_ci_high")]), errors="coerce").iloc[0]
    effect = pd.to_numeric(pd.Series([row.get("effect")]), errors="coerce").iloc[0]
    ci_low = pd.to_numeric(pd.Series([row.get("ci_low")]), errors="coerce").iloc[0]
    ci_high = pd.to_numeric(pd.Series([row.get("ci_high")]), errors="coerce").iloc[0]
    if np.isfinite(percent):
        interval = f"{percent_low:+.1f} to {percent_high:+.1f}%" if np.isfinite(percent_low) and np.isfinite(percent_high) else ""
        return f"{percent:+.1f}%", interval
    if np.isfinite(effect):
        interval = f"{ci_low:+.3g} to {ci_high:+.3g}" if np.isfinite(ci_low) and np.isfinite(ci_high) else ""
        return f"{effect:+.3g}", interval
    return "", ""


def _significance_label(row: pd.Series) -> str:
    """Return a compact statistical-significance label."""

    ci_flag = bool(row.get("significant_95", False))
    p_flag = bool(row.get("significant_p05", False))
    if ci_flag and p_flag:
        return "significant"
    if ci_flag:
        return "CI excludes 0"
    if p_flag:
        return "p < 0.05"
    return "not significant"


def _format_pvalue(value: float) -> str:
    """Format a p-value for plot annotations."""

    if value < 0.001:
        return "<0.001"
    return f"{value:.3f}"


__all__ = [
    "plot_azimuthal_residuals",
    "plot_geology_contrast",
    "plot_path_bin_summary",
    "plot_polar_residuals",
    "plot_residual_correlation",
]
