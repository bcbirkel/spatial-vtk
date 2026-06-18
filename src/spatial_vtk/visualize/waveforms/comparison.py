"""Observed/synthetic trace comparison figures.

Purpose
-------
This module hosts waveform-oriented trace comparison APIs. The implementation
currently reuses the tested public context helper while making the preferred
module path `spatial_vtk.visualize.waveforms`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from spatial_vtk.visualize.context.figures import plot_event_trace_comparison


def _load_comparison_eligible_records(*args: Any, **kwargs: Any) -> pd.DataFrame:
    """Lazy import wrapper for QC comparison-eligible loading."""

    from spatial_vtk.qc import load_comparison_eligible_records

    return load_comparison_eligible_records(*args, **kwargs)


def _build_qc_waveform_comparison_records(*args: Any, **kwargs: Any) -> pd.DataFrame:
    """Lazy import wrapper for QC waveform comparison row construction."""

    from spatial_vtk.qc import build_qc_waveform_comparison_records

    return build_qc_waveform_comparison_records(*args, **kwargs)


@dataclass(frozen=True)
class WaveformComparisonFigureResult:
    """Result returned by waveform comparison figure helpers."""

    figure_path: Path
    event_station_path: Path
    comparison_eligible_path: Path
    records: pd.DataFrame
    status: str
    message: str

    def status_frame(self) -> pd.DataFrame:
        """Return a notebook-friendly status table."""

        return pd.DataFrame(
            [
                {
                    "status": self.status,
                    "message": self.message,
                    "figure_path": str(self.figure_path),
                    "figure_exists": self.figure_path.exists(),
                    "event_station_path": str(self.event_station_path),
                    "event_station_exists": self.event_station_path.exists(),
                    "comparison_eligible_path": str(self.comparison_eligible_path),
                    "comparison_eligible_exists": self.comparison_eligible_path.exists(),
                    "record_count": len(self.records),
                }
            ]
        )


def write_waveform_comparison_from_outputs(
    step_outputs: Any,
    *,
    event_station_path: str | Path | None = None,
    comparison_eligible_path: str | Path | None = None,
    output_path: str | Path | None = None,
    component: str | None = "Z",
    passband: str | None = None,
    event_id: str | list[str] | tuple[str, ...] | None = None,
    max_records: int | None = 12,
    max_distance_km: float | None = 50.0,
    chunksize: int = 1_000_000,
    overwrite: bool = False,
    savefig: bool = True,
    **plot_kwargs: Any,
) -> WaveformComparisonFigureResult:
    """Write a waveform trace comparison figure from configured outputs.

    Parameters
    ----------
    step_outputs
        Output group for ``"step_02_qc"``, ``"step_06_plotting"``, or any
        object with matching
        ``event_station_path``, ``comparison_eligible_path``, and
        ``event_trace_comparison_path`` attributes.
    event_station_path, comparison_eligible_path, output_path
        Optional explicit paths. When omitted, paths are read from
        ``step_outputs``.
    component, passband, event_id
        Bounded selection passed to the comparison-eligible loader and waveform
        record builder.
    max_records
        Maximum event-station rows to load and render.
    max_distance_km
        Optional distance limit in kilometers.
    chunksize
        Rows per chunk when reading comparison-eligible records from disk.
    overwrite
        When false, reuse an existing output figure without reloading
        waveforms.
    savefig
        Whether to save the figure. This defaults to true because the helper is
        intended for notebook workflow outputs.
    **plot_kwargs
        Additional keyword arguments forwarded to
        :func:`plot_event_trace_comparison`, including ``showfig`` and
        sidecar controls.

    Returns
    -------
    WaveformComparisonFigureResult
        Figure path, plotted records, and a compact status message.
    """

    event_station = Path(event_station_path or getattr(step_outputs, "event_station_path"))
    comparison_eligible = Path(comparison_eligible_path or getattr(step_outputs, "comparison_eligible_path"))
    figure_path = Path(output_path or getattr(step_outputs, "event_trace_comparison_path"))
    if figure_path.exists() and not overwrite:
        return WaveformComparisonFigureResult(
            figure_path=figure_path,
            event_station_path=event_station,
            comparison_eligible_path=comparison_eligible,
            records=pd.DataFrame(),
            status="reused",
            message=f"Reused existing waveform comparison figure: {figure_path}",
        )
    missing = [path for path in (event_station, comparison_eligible) if not path.exists()]
    if missing:
        return WaveformComparisonFigureResult(
            figure_path=figure_path,
            event_station_path=event_station,
            comparison_eligible_path=comparison_eligible,
            records=pd.DataFrame(),
            status="missing_inputs",
            message=f"Missing waveform comparison input path(s): {', '.join(str(path) for path in missing)}",
        )

    selected_component = str(component or "Z").strip().upper()
    eligible_sample = _load_comparison_eligible_records(
        comparison_eligible,
        component=selected_component,
        passband=passband,
        event_id=event_id,
        max_records=max_records,
        chunksize=chunksize,
    )
    records = _build_qc_waveform_comparison_records(
        event_station,
        comparison_eligible=eligible_sample,
        component=selected_component,
        passband=passband,
        event_id=event_id,
        max_distance_km=max_distance_km,
        max_records=max_records,
    )
    if records.empty:
        return WaveformComparisonFigureResult(
            figure_path=figure_path,
            event_station_path=event_station,
            comparison_eligible_path=comparison_eligible,
            records=records,
            status="empty",
            message="No observed/synthetic waveform comparison records matched the requested filters.",
        )

    figure_path.parent.mkdir(parents=True, exist_ok=True)
    plot_event_trace_comparison(
        records,
        output_path=figure_path,
        max_records=max_records,
        savefig=savefig,
        **plot_kwargs,
    )
    return WaveformComparisonFigureResult(
        figure_path=figure_path,
        event_station_path=event_station,
        comparison_eligible_path=comparison_eligible,
        records=records,
        status="written",
        message=f"Wrote waveform comparison figure: {figure_path}",
    )


def write_large_run_waveform_comparison_from_outputs(
    step_outputs: Any,
    **kwargs: Any,
) -> WaveformComparisonFigureResult:
    """Compatibility wrapper for large-run notebooks.

    Prefer :func:`write_waveform_comparison_from_outputs` in new notebooks and
    docs. The older name remains public so existing large-run notebooks do not
    break.
    """

    return write_waveform_comparison_from_outputs(step_outputs, **kwargs)


__all__ = [
    "WaveformComparisonFigureResult",
    "plot_event_trace_comparison",
    "write_large_run_waveform_comparison_from_outputs",
    "write_waveform_comparison_from_outputs",
]
