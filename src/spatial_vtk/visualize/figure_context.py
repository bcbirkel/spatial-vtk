"""Shared figure context labels for Spatial-VTK plots.

Purpose
-------
This module builds short, human-readable context strings for figures so saved
PNGs remain understandable outside the notebook, dashboard, or script that
created them.

Usage examples
--------------
Add a compact context line under a plot title:
  ``apply_figure_context(ax, metrics, value_col="log2_residual")``
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from spatial_vtk.config.labels import band_display_label, display_label, metric_display_name, model_display_name, value_column_display_name


def figure_context_lines(
    df: pd.DataFrame | None = None,
    *,
    value_col: str | None = None,
    max_values: int = 5,
    include_counts: bool = True,
    include_value: bool = True,
    include_metric: bool = True,
    include_model: bool = True,
    include_period: bool = True,
    include_component: bool = True,
    include_processing: bool = True,
    extra: Sequence[str] | None = None,
) -> list[str]:
    """Build concise context lines from common Spatial-VTK columns.

    Parameters
    ----------
    df
        Optional dataframe used to infer model, metric, period band, component,
        and row-count context.
    value_col
        Column or transform shown by the figure.
    max_values
        Maximum distinct values to show before summarizing as "N values".
    include_counts
        Whether to include rows/events/stations when available.
    extra
        Additional preformatted context strings.

    Returns
    -------
    list of str
        Context lines suitable for a subtitle or annotation box.
    """

    lines: list[str] = []
    if value_col and include_value:
        lines.append(f"Value: {context_value_label(value_col, df)}")
    if df is not None and not df.empty:
        for label, candidates, formatter, include in (
            ("Metric", ("metric", "metric_name"), metric_display_name, include_metric),
            ("Model", ("model", "simulation_model", "model_name"), model_display_name, include_model),
            ("Period", ("band", "passband", "simulation_band", "bin"), band_display_label, include_period),
            ("Component", ("component", "station_component"), str, include_component),
        ):
            column = _first_existing_column(df, candidates) if include else None
            if column:
                value_text = _summarize_values(df[column], max_values=max_values, formatter=formatter, summary_label=label)
                if value_text:
                    lines.append(f"{label}: {value_text}")
        if include_processing:
            processing = _processing_notes(df, value_col=value_col)
            if processing:
                lines.append(f"Processing: {processing}")
        if include_counts:
            count_text = _count_summary(df)
            if count_text:
                lines.append(count_text)
    if extra:
        lines.extend(str(item) for item in extra if str(item).strip())
    return lines


def figure_context_text(
    df: pd.DataFrame | None = None,
    *,
    value_col: str | None = None,
    separator: str = " | ",
    **kwargs: Any,
) -> str:
    """Return figure context as one compact string.

    Parameters
    ----------
    df
        Optional dataframe used to infer context.
    value_col
        Column or transform shown by the figure.
    separator
        Separator used between context fragments.
    **kwargs
        Additional options passed to :func:`figure_context_lines`.

    Returns
    -------
    str
        One-line context string.
    """

    return separator.join(figure_context_lines(df, value_col=value_col, **kwargs))


def title_with_subtitle(title: str, subtitle: str | None = None) -> str:
    """Return a figure title with an optional second subtitle line.

    Parameters
    ----------
    title
        Primary title line.
    subtitle
        Optional concise context line, such as a waveform filter description.

    Returns
    -------
    str
        ``title`` alone, or ``title`` followed by ``subtitle`` on the next line.
    """

    subtitle_text = str(subtitle or "").strip()
    return f"{title}\n{subtitle_text}" if subtitle_text else str(title)


def apply_figure_context(
    ax: plt.Axes,
    df: pd.DataFrame | None = None,
    *,
    value_col: str | None = None,
    title: str | None = None,
    max_values: int = 5,
    include_counts: bool = True,
    include_value: bool = True,
    include_metric: bool = True,
    include_model: bool = True,
    include_period: bool = True,
    include_component: bool = True,
    include_processing: bool = True,
    max_line_chars: int = 90,
    extra: Sequence[str] | None = None,
) -> None:
    """Apply a title plus concise context line to an axis.

    Parameters
    ----------
    ax
        Matplotlib axis to update.
    df
        Optional dataframe used to infer context.
    value_col
        Column or transform shown by the figure.
    title
        Primary title text.
    max_values
        Maximum distinct values to list in the context.
    include_counts
        Whether to include rows/events/stations.
    extra
        Additional preformatted context strings.

    Returns
    -------
    None
        The axis title is updated in place.
    """

    lines = figure_context_lines(
        df,
        value_col=value_col,
        max_values=max_values,
        include_counts=include_counts,
        include_value=include_value,
        include_metric=include_metric,
        include_model=include_model,
        include_period=include_period,
        include_component=include_component,
        include_processing=include_processing,
        extra=extra,
    )
    context = "\n".join(_pack_context_lines(lines, max_chars=int(max_line_chars)))
    if title and context:
        ax.set_title(f"{title}\n{context}", fontsize=11)
    elif title:
        ax.set_title(title)
    elif context:
        ax.set_title(context, fontsize=10)


def context_value_label(value_col: str, df: pd.DataFrame | None = None) -> str:
    """Return a value label with centering/ratio notes where detectable.

    Parameters
    ----------
    value_col
        Column or transform shown by the figure.
    df
        Optional dataframe used to inspect ``field_source`` and event-centering
        metadata.

    Returns
    -------
    str
        Human-readable value label.
    """

    label = value_column_display_name(value_col)
    if str(value_col) == "field_centered" and df is not None:
        source = _source_text(df)
        if "log2" in source:
            label = "Event-centered log2(observed / synthetic)"
        elif source:
            label = f"Event-centered {display_label(source)}"
    if str(value_col) in {"mean_centered", "station_mean_centered"} and df is not None and "log2" in _source_text(df):
        label = "Mean event-centered log2(observed / synthetic)"
    return label


def is_log2_ratio_field(value_col: str | None, df: pd.DataFrame | None = None) -> bool:
    """Return whether a field is interpretable as a log2 observed/synthetic ratio.

    Parameters
    ----------
    value_col
        Value column or transform name.
    df
        Optional dataframe used to inspect ``field_source``.

    Returns
    -------
    bool
        True when percent conversion with ``2 ** effect - 1`` is meaningful.
    """

    text = str(value_col or "").lower()
    if "log2" in text or "log2_ratio" in text:
        return True
    if text in {"field_value", "field_centered", "mean_centered", "station_mean_centered"} and df is not None:
        return "log2" in _source_text(df)
    return False


def log2_effect_to_percent(effect: float | int | np.floating[Any]) -> float:
    """Convert a log2 ratio difference to percent change.

    Parameters
    ----------
    effect
        Difference in log2 observed/synthetic ratio units.

    Returns
    -------
    float
        Percent change in observed/synthetic ratio.
    """

    return float((2.0 ** float(effect) - 1.0) * 100.0)


def value_requires_model(value_col: str | None, df: pd.DataFrame | None = None) -> bool:
    """Return whether a plotted value depends on synthetic model output.

    Parameters
    ----------
    value_col
        Value column or transform name.
    df
        Optional dataframe used to inspect ``field_source`` for generic spatial
        field columns.

    Returns
    -------
    bool
        True when model context should be shown or explicitly selected.
    """

    key = _value_key(value_col)
    if key in {"valueobs", "observed", "observedvalue", "medvalueobs", "medianobservedvalue"}:
        return False
    if key in {"valuesyn", "synthetic", "syntheticvalue", "medvaluesyn", "mediansyntheticvalue"}:
        return True
    if key in {"fieldvalue", "fieldcentered", "meancentered", "stationmeancentered"} and df is not None:
        source = _source_text(df)
        return any(token in source for token in ("syn", "synthetic", "residual", "score", "gof", "log2", "ln"))
    return any(token in key for token in ("syn", "synthetic", "residual", "score", "gof", "fieldcentered", "fieldvalue", "predictionerror", "heldoutbiaserror"))


def value_uses_zero_reference(value_col: str | None, df: pd.DataFrame | None = None) -> bool:
    """Return whether a value should use a zero reference/diverging scale.

    Parameters
    ----------
    value_col
        Value column or transform name.
    df
        Optional dataframe used to inspect ``field_source``.

    Returns
    -------
    bool
        True for residuals, centered fields, delays, errors, and signed
        improvements; false for observed/synthetic amplitudes and GOF scores.
    """

    key = _value_key(value_col)
    if any(token in key for token in ("score", "gof")) and not any(token in key for token in ("resid", "error", "bias")):
        return False
    if any(token in key for token in ("observed", "synthetic", "valueobs", "valuesyn")) and not any(token in key for token in ("resid", "ratio", "error", "bias")):
        return False
    if key in {"fieldcentered", "meancentered", "stationmeancentered"}:
        return True
    if key == "fieldvalue" and df is not None:
        source = _source_text(df)
        return any(token in source for token in ("resid", "log2", "ln", "center", "error", "bias"))
    return any(token in key for token in ("resid", "log2", "ln", "delay", "error", "center", "bias", "improvement", "anomaly"))


def value_color_settings(
    values: Sequence[float] | np.ndarray | pd.Series,
    value_col: str | None,
    df: pd.DataFrame | None = None,
    *,
    diverging_cmap: str = "seismic",
    sequential_cmap: str = "viridis",
) -> tuple[str, float, float]:
    """Return a consistent colormap and color limits for plotted values.

    Parameters
    ----------
    values
        Numeric values being plotted.
    value_col
        Value column or transform name.
    df
        Optional dataframe used to inspect generic spatial field metadata.
    diverging_cmap, sequential_cmap
        Colormaps used for signed residual-like/log/centered values and
        positive/score-like values.

    Returns
    -------
    tuple[str, float, float]
        Colormap name, lower color limit, and upper color limit.
    """

    array = np.asarray(values, dtype=float)
    finite = array[np.isfinite(array)]
    if finite.size == 0:
        return diverging_cmap if value_uses_zero_reference(value_col, df) else sequential_cmap, -1.0, 1.0
    if value_uses_zero_reference(value_col, df):
        vmax = max(float(np.nanmax(np.abs(finite))), 1.0e-12)
        return diverging_cmap, -vmax, vmax
    vmin = float(np.nanmin(finite))
    vmax = float(np.nanmax(finite))
    if np.isclose(vmin, vmax):
        pad = max(abs(vmax) * 0.05, 1.0e-6)
        vmin -= pad
        vmax += pad
    return sequential_cmap, vmin, vmax


def add_below_axes_table(
    ax: plt.Axes,
    *,
    rows: Sequence[Sequence[object]],
    columns: Sequence[str],
    col_widths: Sequence[float] | None = None,
    font_size: float = 7.5,
    max_visible_rows: int = 6,
) -> None:
    """Add a compact summary table below a Matplotlib axis.

    Parameters
    ----------
    ax
        Axis that owns the table.
    rows
        Body rows to display.
    columns
        Column headers.
    col_widths
        Optional relative column widths.
    font_size
        Table text size.
    max_visible_rows
        Maximum rows shown before an omitted-count row is appended.

    Returns
    -------
    None
        The figure layout and axis table are updated in place.
    """

    clean_rows = [[str(value) for value in row] for row in rows if any(str(value).strip() for value in row)]
    if not clean_rows:
        return
    if max_visible_rows > 0 and len(clean_rows) > max_visible_rows:
        omitted = len(clean_rows) - max_visible_rows
        clean_rows = clean_rows[:max_visible_rows] + [[f"{omitted} additional rows omitted"] + [""] * (len(columns) - 1)]
    row_count = len(clean_rows) + 1
    bottom_margin = min(0.58, 0.24 + 0.055 * row_count)
    table_height = min(0.40, 0.08 + 0.05 * row_count)
    if hasattr(ax.figure, "set_layout_engine"):
        try:
            ax.figure.set_layout_engine(None)
        except Exception:
            pass
    ax.figure.subplots_adjust(bottom=bottom_margin)
    table = ax.table(
        cellText=clean_rows,
        colLabels=list(columns),
        cellLoc="left",
        colLoc="left",
        colWidths=list(col_widths) if col_widths is not None else None,
        loc="bottom",
        bbox=[0.0, -0.34 - table_height, 1.0, table_height],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(font_size)
    for (row_index, _col_index), cell in table.get_celld().items():
        cell.set_edgecolor("0.82")
        if row_index == 0:
            cell.set_facecolor("0.94")
            cell.set_text_props(weight="bold")
        else:
            cell.set_facecolor("white")


def _first_existing_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    """Return the first candidate column present in a dataframe."""

    for column in candidates:
        if column in df.columns:
            return column
    return None


def _summarize_values(series: pd.Series, *, max_values: int, formatter: Any, summary_label: str) -> str:
    """Summarize distinct display values from a series."""

    values = [value for value in pd.unique(series.dropna()) if str(value).strip()]
    if summary_label == "Component":
        values = [value for value in values if str(value).strip().lower() not in {"all", "none", "nan"}]
    if summary_label == "Period":
        values = [value for value in values if str(value).strip().lower() not in {"all", "none", "nan"}]
    if not values:
        return ""
    if summary_label == "Period":
        return _summarize_periods(values, max_values=max_values)
    if len(values) <= max_values:
        return ", ".join(str(formatter(value)) for value in values)
    return f"{len(values)} {_plural_summary_label(summary_label)}"


def _summarize_periods(values: Sequence[object], *, max_values: int) -> str:
    """Summarize period bands without repeating units after every value."""

    labels = [band_display_label(value) for value in sorted(values, key=_period_sort_key)]
    if len(labels) > max_values:
        return f"{len(labels)} period bands"
    seconds_labels = [label for label in labels if label.endswith(" sec")]
    if len(seconds_labels) == len(labels):
        stripped = [label.removesuffix(" sec") for label in seconds_labels]
        return f"{', '.join(stripped)} sec"
    return ", ".join(labels)


def _period_sort_key(value: object) -> tuple[float, str]:
    """Return a stable numeric sort key for period labels."""

    label = band_display_label(value)
    text = label.removesuffix(" sec")
    first = text.split("-", 1)[0].strip()
    try:
        return (float(first), label)
    except ValueError:
        return (float("inf"), label)


def _plural_summary_label(label: str) -> str:
    """Return a readable plural noun for summarized context values."""

    lookup = {
        "Metric": "metrics",
        "Model": "models",
        "Period": "periods",
        "Component": "components",
    }
    return lookup.get(str(label), "values")


def _processing_notes(df: pd.DataFrame, *, value_col: str | None) -> str:
    """Infer short processing notes from common field columns."""

    notes: list[str] = []
    if str(value_col) == "field_centered" and "event_mean" in df.columns:
        notes.append("event mean removed")
    if _source_text(df).find("distance") >= 0:
        notes.append("distance scaled")
    return ", ".join(dict.fromkeys(notes))


def _count_summary(df: pd.DataFrame) -> str:
    """Return compact row/event/station counts for a dataframe."""

    parts = [f"Rows: {len(df):,}"]
    event_col = _first_existing_column(df, ("event_id", "event_title"))
    station_col = _first_existing_column(df, ("station", "station_name"))
    if event_col:
        parts.append(f"Events: {df[event_col].nunique(dropna=True):,}")
    if station_col:
        parts.append(f"Stations: {df[station_col].nunique(dropna=True):,}")
    return "; ".join(parts)


def _source_text(df: pd.DataFrame | None) -> str:
    """Return compact lower-case field-source text from a dataframe."""

    if df is None or "field_source" not in df.columns:
        return ""
    return " ".join(str(value).lower() for value in pd.unique(df["field_source"].dropna()) if str(value).strip())


def _value_key(value_col: str | None) -> str:
    """Return a compact comparison key for value-column tokens."""

    return "".join(char for char in str(value_col or "").lower() if char.isalnum())


def _pack_context_lines(lines: Sequence[str], *, max_chars: int = 115) -> list[str]:
    """Pack context fragments into readable title lines."""

    packed: list[str] = []
    current = ""
    for line in lines:
        fragment = str(line).strip()
        if not fragment:
            continue
        candidate = fragment if not current else f"{current} | {fragment}"
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            packed.append(current)
            current = fragment
    if current:
        packed.append(current)
    return packed


__all__ = [
    "add_below_axes_table",
    "apply_figure_context",
    "context_value_label",
    "figure_context_lines",
    "figure_context_text",
    "is_log2_ratio_field",
    "log2_effect_to_percent",
    "title_with_subtitle",
    "value_color_settings",
    "value_requires_model",
    "value_uses_zero_reference",
]
