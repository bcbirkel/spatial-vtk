"""Trace inventory sample figure helpers.

Purpose
-------
This module draws compact sample waveform figures from explicit trace rows so
users can visually inspect retained and rejected records during QC.

Usage examples
--------------
Plot sample traces:
  ``plot_trace_inventory_samples(sample_df, "qc_samples.png")``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from spatial_vtk.visualize.figure_context import title_with_subtitle
from spatial_vtk.visualize.selection import FigureSelection
from spatial_vtk.visualize.figure_io import finish_figure


def plot_trace_inventory_samples(
    sample_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    trace_col: str = "trace",
    station_col: str = "station",
    event_col: str = "event_id",
    component_col: str = "component",
    status_col: str = "qc_status",
    dt_col: str = "dt",
    selection: FigureSelection | None = None,
    max_traces: int = 12,
    title: str = "Trace Inventory Samples",
    filter_label: str | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot sample traces from a QC inventory.

    Parameters
    ----------
    sample_df
        Table with trace arrays or trace-like objects.
    output_path
        Destination figure path.
    trace_col
        Trace column.
    station_col, event_col, component_col, status_col
        Label columns.
    dt_col
        Sample interval column.
    max_traces
        Maximum traces to display.
    title
        Figure title.
    filter_label
        Optional second title line describing any bandpass or lowpass filter.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    work = selection.apply(sample_df, component_col=component_col) if selection is not None else sample_df.copy()
    if trace_col not in work.columns:
        raise KeyError(f"sample_df must include a '{trace_col}' column.")
    df = work.head(int(max_traces)).copy()
    fig, axes = plt.subplots(len(df), 1, figsize=(9.0, max(2.2, 1.05 * max(len(df), 1))), dpi=180, sharex=False)
    axes = np.atleast_1d(axes)
    if df.empty:
        axes[0].text(0.5, 0.5, "No trace samples", ha="center", va="center", transform=axes[0].transAxes)
        axes[0].set_axis_off()
    for ax, (_, row) in zip(axes, df.iterrows()):
        data, dt = _trace_data_and_dt(row[trace_col], row.get(dt_col, 1.0))
        time = np.arange(len(data), dtype=float) * dt
        color = "#1b9e77" if str(row.get(status_col, "")).lower() in {"pass", "passed", "keep", "kept"} else "#d95f02"
        ax.plot(time, data, color=color, linewidth=0.8)
        label = " / ".join(str(row.get(column, "")).strip() for column in (event_col, station_col, component_col) if column in df.columns)
        status = str(row.get(status_col, "")).strip()
        ax.set_ylabel(status or "trace", fontsize=8)
        ax.set_title(label, fontsize=8, loc="left")
        ax.grid(True, alpha=0.18)
    axes[-1].set_xlabel("Time (s)")
    fig.suptitle(title_with_subtitle(title, filter_label), y=0.995)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.96))
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def _trace_data_and_dt(value: Any, default_dt: object) -> tuple[np.ndarray, float]:
    """Return waveform samples and sample spacing from array or trace-like data."""

    if hasattr(value, "data"):
        data = np.asarray(value.data, dtype=float).reshape(-1)
        stats = getattr(value, "stats", None)
        dt = getattr(stats, "delta", None)
        if dt is None:
            sampling_rate = getattr(stats, "sampling_rate", None)
            dt = 1.0 / float(sampling_rate) if sampling_rate else default_dt
    else:
        data = np.asarray(value, dtype=float).reshape(-1)
        dt = default_dt
    try:
        dt_out = float(dt)
    except Exception:
        dt_out = 1.0
    return data, dt_out


__all__ = ["plot_trace_inventory_samples"]
