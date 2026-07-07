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
from spatial_vtk.visualize.figure_sidecars import normalize_figure_status_rows


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

        return normalize_figure_status_rows(
            [
                {
                    "name": "waveform_comparison_figure",
                    "artifact_label": "Waveform comparison figure",
                    "artifact_role": "figure",
                    "status": self.status,
                    "message": self.message,
                    "figure_path": str(self.figure_path),
                    "figure_exists": self.figure_path.exists(),
                    "event_station_path": str(self.event_station_path),
                    "event_station_exists": self.event_station_path.exists(),
                    "comparison_eligible_path": str(self.comparison_eligible_path),
                    "comparison_eligible_exists": self.comparison_eligible_path.exists(),
                    "record_count": len(self.records),
                },
                {
                    "name": "event_station_records",
                    "artifact_label": "Event-station record table",
                    "artifact_role": "input_table",
                    "status": "ready" if self.event_station_path.exists() else "missing",
                    "message": (
                        "Event-station record table is ready."
                        if self.event_station_path.exists()
                        else "Event-station record table is missing."
                    ),
                    "path": str(self.event_station_path),
                    "record_count": "",
                },
                {
                    "name": "comparison_eligible_records",
                    "artifact_label": "Comparison-eligible record table",
                    "artifact_role": "input_table",
                    "status": "ready" if self.comparison_eligible_path.exists() else "missing",
                    "message": (
                        "Comparison-eligible record table is ready."
                        if self.comparison_eligible_path.exists()
                        else "Comparison-eligible record table is missing."
                    ),
                    "path": str(self.comparison_eligible_path),
                    "record_count": "",
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
    fallback_to_available: bool = False,
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
    fallback_to_available
        When true, retry with available components and all passbands if the
        requested component/passband selection has no plottable records.
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

    def _build_records(selection_component: str, selection_passband: str | None) -> pd.DataFrame:
        eligible_sample = _load_comparison_eligible_records(
            comparison_eligible,
            component=selection_component,
            passband=selection_passband,
            event_id=event_id,
            max_records=max_records,
            chunksize=chunksize,
        )
        return _build_qc_waveform_comparison_records(
            event_station,
            comparison_eligible=eligible_sample,
            component=selection_component,
            passband=selection_passband,
            event_id=event_id,
            max_distance_km=max_distance_km,
            max_records=max_records,
        )

    records = _build_records(selected_component, passband)
    fallback_note = ""
    if records.empty and fallback_to_available:
        unfiltered_sample = _load_comparison_eligible_records(
            comparison_eligible,
            component=None,
            passband=None,
            event_id=event_id,
            max_records=max_records,
            chunksize=chunksize,
        )
        if "component" in unfiltered_sample.columns:
            fallback_components = [
                str(value).strip().upper()
                for value in unfiltered_sample["component"].dropna().drop_duplicates().tolist()
                if str(value).strip()
            ]
        else:
            fallback_components = []
        for fallback_component in fallback_components:
            candidate_records = _build_qc_waveform_comparison_records(
                event_station,
                comparison_eligible=unfiltered_sample,
                component=fallback_component,
                passband=None,
                event_id=event_id,
                max_distance_km=max_distance_km,
                max_records=max_records,
            )
            if not candidate_records.empty:
                records = candidate_records
                fallback_note = (
                    f" Used available waveform selection instead: component {fallback_component}, all passbands."
                )
                break
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
        message=f"Wrote waveform comparison figure: {figure_path}.{fallback_note}",
    )


def write_waveform_comparison_from_notebook_settings(
    step_outputs: Any,
    settings: Any,
    *,
    max_records: int | None = 12,
    max_distance_km: float | None = 50.0,
    chunksize: int = 1_000_000,
    overwrite: bool = False,
    event_id: str | list[str] | tuple[str, ...] | None = None,
    component: str | None = None,
    passband: str | None = None,
    fallback_to_available: bool = False,
    plot_options: dict[str, Any] | None = None,
) -> WaveformComparisonFigureResult:
    """Write a bounded waveform comparison figure using notebook settings.

    This wrapper owns the notebook-facing render gate and settings-to-keyword
    translation so tutorial cells do not need to repeat input checks or
    environment-backed figure options. Use ``plot_options`` for
    figure-specific labels or trace-display options that should be forwarded to
    :func:`plot_event_trace_comparison`.
    """

    output_group = getattr(step_outputs, "outputs", step_outputs)
    event_station = Path(getattr(output_group, "event_station_path"))
    comparison_eligible = Path(getattr(output_group, "comparison_eligible_path"))
    figure_path = Path(getattr(output_group, "event_trace_comparison_path"))
    gate = settings.render_gate(
        [comparison_eligible, event_station],
        missing_message="Comparison-eligible records or event-station records are not ready yet.",
    )
    if not gate.ready:
        status = "disabled" if not gate.figures_enabled else "missing_inputs"
        return WaveformComparisonFigureResult(
            figure_path=figure_path,
            event_station_path=event_station,
            comparison_eligible_path=comparison_eligible,
            records=pd.DataFrame(),
            status=status,
            message=gate.message,
        )
    plot_kwargs = settings.plot_kwargs()
    if plot_options:
        plot_kwargs.update(plot_options)
    return write_waveform_comparison_from_outputs(
        output_group,
        component=component if component is not None else (settings.component or "Z"),
        passband=passband if passband is not None else settings.passband,
        event_id=event_id,
        max_records=max_records,
        max_distance_km=max_distance_km,
        chunksize=chunksize,
        overwrite=overwrite,
        fallback_to_available=fallback_to_available,
        **plot_kwargs,
    )


def write_large_run_waveform_comparison_from_outputs(
    step_outputs: Any,
    **kwargs: Any,
) -> WaveformComparisonFigureResult:
    """Compatibility wrapper for large-run notebooks.

    Prefer :func:`write_waveform_comparison_from_notebook_settings` in
    notebook cells so package code owns render gates and environment-backed
    figure options. Use :func:`write_waveform_comparison_from_outputs` from
    scripts when explicit plotting keyword arguments are already resolved. The
    older large-run name remains public so existing notebooks do not break.
    """

    return write_waveform_comparison_from_outputs(step_outputs, **kwargs)


__all__ = [
    "WaveformComparisonFigureResult",
    "plot_event_trace_comparison",
    "write_large_run_waveform_comparison_from_outputs",
    "write_waveform_comparison_from_notebook_settings",
    "write_waveform_comparison_from_outputs",
]
