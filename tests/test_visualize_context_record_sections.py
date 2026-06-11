"""Tests for migrated context and record-section figure helpers."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pytest
from matplotlib import pyplot as plt

matplotlib.use("Agg", force=True)

from spatial_vtk.visualize.context import (
    build_record_coverage_table,
    build_record_coverage_table_from_qc,
    build_record_coverage_table_from_trace_metadata,
    plot_distance_amplitude_diagnostics,
    plot_event_trace_comparison,
    plot_record_coverage,
    plot_study_domain_map,
)
from spatial_vtk.visualize.record_sections import (
    build_record_section_rows,
    plot_observed_synthetic_record_section,
    plot_record_section,
)
from spatial_vtk.visualize.selection import FigureSelection
from spatial_vtk.visualize.waveforms import plot_station_event_waveform_map


def _assert_png(path: Path) -> None:
    """Assert that a plotted PNG exists and is non-empty."""

    assert path.exists()
    assert path.stat().st_size > 0


def _records() -> pd.DataFrame:
    """Build a tiny observed/synthetic waveform table for plotting tests."""

    time = np.linspace(0.0, 20.0, 401)
    rows = []
    for index, station in enumerate(["S1", "S2", "S3"]):
        for component in ["Z", "R"]:
            phase = index * 0.35 + (0.2 if component == "R" else 0.0)
            observed = np.sin(time * 0.7 + phase) * np.exp(-time / 35.0)
            synthetic = 0.85 * np.sin(time * 0.7 + phase + 0.18) * np.exp(-time / 35.0)
            rows.append(
                {
                    "event_id": "E1",
                    "station": station,
                    "component": component,
                    "distance_km": 20.0 + index * 18.0,
                    "trace": observed,
                    "observed": observed,
                    "synthetic": synthetic,
                    "observed_peak_abs": float(np.max(np.abs(observed))),
                    "synthetic_peak_abs": float(np.max(np.abs(synthetic))),
                    "observed_start_s": 0.0,
                    "observed_end_s": 20.0,
                    "synthetic_start_s": 0.0,
                    "synthetic_end_s": 18.0 + index,
                }
            )
    return pd.DataFrame(rows)


def test_basic_context_figures_write_outputs(tmp_path: Path) -> None:
    """Migrated basic-context figures should render from public DataFrames."""

    stations = pd.DataFrame(
        {
            "station": ["S1", "S2", "S3"],
            "network": ["AA", "AA", "BB"],
            "lat": [34.0, 34.15, 34.25],
            "lon": [-118.45, -118.25, -118.15],
        }
    )
    events = pd.DataFrame(
        {
            "event_id": ["E1", "E2"],
            "event_lat": [34.08, 34.32],
            "event_lon": [-118.38, -118.08],
            "magnitude": [4.2, 4.8],
        }
    )
    records = _records()
    outputs = [
        plot_study_domain_map(stations, events, tmp_path / "study_domain.png", add_basemap=False),
        plot_record_coverage(records, tmp_path / "record_coverage.png"),
        plot_event_trace_comparison(records, tmp_path / "trace_comparison.png", max_records=4),
        plot_distance_amplitude_diagnostics(records, tmp_path / "distance_amplitude.png"),
    ]
    for output in outputs:
        _assert_png(output)


def test_record_coverage_table_from_waveform_qc(tmp_path: Path) -> None:
    """Waveform QC rows should provide measured coverage intervals."""

    trace_qc = pd.DataFrame(
        {
            "source": ["observed", "synthetic"],
            "event_id": ["E1", "E1"],
            "station": ["S1", "S1"],
            "component": ["Z", "Z"],
            "passband": ["1-2 sec", "1-2 sec"],
            "trace_start_s": [-2.0, 0.0],
            "trace_end_s": [62.0, 60.0],
            "trace_duration_s": [64.0, 60.0],
        }
    )
    event_stations = pd.DataFrame({"event_id": ["E1"], "station": ["S1"], "distance_km": [12.5]})
    coverage = build_record_coverage_table_from_qc(trace_qc, event_station_df=event_stations, component="Z", passband="1-2 sec")
    assert coverage.loc[0, "observed_start_s"] == -2.0
    assert coverage.loc[0, "observed_end_s"] == 62.0
    assert coverage.loc[0, "synthetic_start_s"] == 0.0
    assert coverage.loc[0, "synthetic_end_s"] == 60.0
    assert coverage.loc[0, "distance_km"] == 12.5
    output = plot_record_coverage(coverage, tmp_path / "record_coverage_from_qc.png")
    _assert_png(output)


def test_record_coverage_requires_measured_timing() -> None:
    """Record coverage should not silently invent default record lengths."""

    basic_records = pd.DataFrame({"event_id": ["E1"], "station": ["S1"]})
    with pytest.raises(KeyError, match="measured timing"):
        build_record_coverage_table(basic_records)
    with pytest.raises(KeyError, match="measured timing"):
        plot_record_coverage(basic_records)


def test_record_coverage_table_from_trace_metadata(tmp_path: Path) -> None:
    """Preprocessing trace metadata should build measured record coverage."""

    trace_metadata = pd.DataFrame(
        {
            "source_type": ["observed", "synthetic"],
            "event_id": ["E1", "E1"],
            "station": ["S1", "S1"],
            "component": ["Z", "Z"],
            "starttime": ["2020-01-01T00:00:05Z", "2020-01-01T00:00:10Z"],
            "endtime": ["2020-01-01T00:01:05Z", "2020-01-01T00:01:15Z"],
        }
    )
    event_stations = pd.DataFrame(
        {
            "event_id": ["E1"],
            "station": ["S1"],
            "start": ["2020-01-01T00:00:10Z"],
            "event_name": ["M 4.0 test event"],
            "distance_km": [12.5],
        }
    )

    coverage = build_record_coverage_table_from_trace_metadata(trace_metadata, event_station_df=event_stations, component="Z")
    assert coverage.loc[0, "observed_start_s"] == -5.0
    assert coverage.loc[0, "observed_end_s"] == 55.0
    assert coverage.loc[0, "synthetic_start_s"] == 0.0
    assert coverage.loc[0, "synthetic_end_s"] == 65.0
    assert coverage.loc[0, "event_name"] == "M 4.0 test event"
    output = plot_record_coverage(coverage, tmp_path / "record_coverage_from_metadata.png")
    _assert_png(output)


def test_record_coverage_trace_metadata_matches_numeric_station_alias() -> None:
    """Trace station codes with leading zeros should match numeric metadata IDs."""

    trace_metadata = pd.DataFrame(
        {
            "source_type": ["observed", "synthetic"],
            "event_id": ["ci15481673", "ci15481673"],
            "station": ["0637", "0637"],
            "component": ["Z", "Z"],
            "starttime": ["2020-01-01T00:00:05Z", "2020-01-01T00:00:10Z"],
            "endtime": ["2020-01-01T00:01:05Z", "2020-01-01T00:01:15Z"],
        }
    )
    event_stations = pd.DataFrame(
        {
            "event_id": ["ci15481673"],
            "station": [637],
            "start": ["2020-01-01T00:00:10Z"],
            "distance_km": [4.2],
        }
    )

    coverage = build_record_coverage_table_from_trace_metadata(trace_metadata, event_station_df=event_stations)

    assert coverage.loc[0, "station"] == "0637"
    assert coverage.loc[0, "distance_km"] == 4.2
    assert coverage.loc[0, "observed_start_s"] == -5.0


def test_record_coverage_drops_trace_metadata_without_event_station_match() -> None:
    """Extra placeholder trace stations should not stop coverage table creation."""

    trace_metadata = pd.DataFrame(
        {
            "source_type": ["observed", "synthetic", "observed", "synthetic"],
            "event_id": ["E1", "E1", "E1", "E1"],
            "station": ["S1", "S1", "00000", "00000"],
            "starttime": [
                "2020-01-01T00:00:05Z",
                "2020-01-01T00:00:10Z",
                "2020-01-01T00:00:00Z",
                "2020-01-01T00:00:00Z",
            ],
            "endtime": [
                "2020-01-01T00:01:05Z",
                "2020-01-01T00:01:15Z",
                "2020-01-01T00:01:00Z",
                "2020-01-01T00:01:00Z",
            ],
        }
    )
    event_stations = pd.DataFrame({"event_id": ["E1"], "station": ["S1"], "start": ["2020-01-01T00:00:10Z"]})

    coverage = build_record_coverage_table_from_trace_metadata(trace_metadata, event_station_df=event_stations)

    assert coverage["station"].tolist() == ["S1"]
    assert coverage.attrs["dropped_missing_metadata"] == 1


def test_record_coverage_can_raise_on_missing_event_station_match() -> None:
    """Strict mode should still flag trace stations absent from event-station metadata."""

    trace_metadata = pd.DataFrame(
        {
            "source_type": ["observed"],
            "event_id": ["E1"],
            "station": ["00000"],
            "starttime": ["2020-01-01T00:00:00Z"],
            "endtime": ["2020-01-01T00:01:00Z"],
        }
    )
    event_stations = pd.DataFrame({"event_id": ["E1"], "station": ["S1"], "start": ["2020-01-01T00:00:10Z"]})

    with pytest.raises(ValueError, match="No event-station metadata"):
        build_record_coverage_table_from_trace_metadata(
            trace_metadata,
            event_station_df=event_stations,
            on_missing_metadata="raise",
        )


def test_record_section_figures_write_outputs(tmp_path: Path) -> None:
    """Generic record-section helpers should render single and obs/syn sections."""

    records = _records()
    rows = build_record_section_rows(records, trace_col="trace")
    assert {"trace", "dt", "station", "component", "distance_km"} <= set(rows.columns)

    outputs = [
        plot_record_section(records, tmp_path / "record_section.png", components=["Z", "R"], max_records=4),
        plot_observed_synthetic_record_section(records, tmp_path / "obs_syn_record_section.png", components=["Z", "R"], max_records=4),
    ]
    for output in outputs:
        _assert_png(output)


def test_record_sections_apply_selection_before_truncation(tmp_path: Path) -> None:
    """Selection filters should run before max-record truncation."""

    records = _records()
    selection = FigureSelection(components=("R",), stations=("S3",), events=("E1",))
    filtered = selection.apply(records)
    assert len(filtered) == 1
    assert filtered.iloc[0]["component"] == "R"
    output = plot_observed_synthetic_record_section(records, tmp_path / "selected.png", selection=selection, max_records=1)
    _assert_png(output)


def test_trace_comparison_uses_event_origin_offsets() -> None:
    """Observed/synthetic overlays should use event-origin-relative offsets."""

    records = pd.DataFrame(
        {
            "event_id": ["E1"],
            "station": ["S1"],
            "component": ["Z"],
            "distance_km": [20.0],
            "observed": [np.arange(20, dtype=float)],
            "synthetic": [np.arange(10, dtype=float)],
            "dt": [1.0],
            "synthetic_dt": [1.0],
            "observed_time_offset_s": [-5.0],
            "synthetic_time_offset_s": [0.0],
        }
    )
    fig = plot_event_trace_comparison(records, max_records=1, time_limit_s=8.0, showfig=False)
    ax = fig.axes[0]
    assert ax.get_xlabel() == "Seconds since event origin"
    observed_x = ax.lines[0].get_xdata()
    synthetic_x = ax.lines[1].get_xdata()
    assert float(observed_x[0]) == 0.0
    assert float(observed_x[-1]) == 8.0
    assert float(synthetic_x[0]) == 0.0
    assert float(synthetic_x[-1]) == 8.0


def test_station_event_waveform_map_aligns_to_event_time_and_sorts_distance() -> None:
    """Station-event waveform maps should align traces and sort nearest at bottom."""

    records = pd.DataFrame(
        {
            "event_id": ["E1", "E1"],
            "station": ["FAR", "NEAR"],
            "component": ["R", "R"],
            "sta_lon": [-118.3, -118.2],
            "sta_lat": [34.2, 34.1],
            "event_lon": [-118.0, -118.0],
            "event_lat": [34.0, 34.0],
            "distance_km": [50.0, 10.0],
            "observed": [np.arange(20, dtype=float), np.arange(20, dtype=float)],
            "synthetic": [0.5 * np.arange(20, dtype=float), 0.5 * np.arange(20, dtype=float)],
            "dt": [1.0, 1.0],
            "synthetic_dt": [1.0, 1.0],
            "observed_time_offset_s": [-3.0, 2.0],
            "synthetic_time_offset_s": [0.0, 0.0],
        }
    )
    fig = plot_station_event_waveform_map(
        records,
        waveform_col="observed",
        time_limit_s=8.0,
        add_basemap=False,
        showfig=False,
    )
    trace_ax = fig.axes[1]
    assert trace_ax.get_xlim() == (0.0, 8.0)
    labels = [text.get_text() for text in trace_ax.texts]
    assert labels[0].startswith("NEAR")
    plt.close(fig)

    low_gain = plot_event_trace_comparison(
        records,
        max_records=1,
        time_limit_s=8.0,
        normalize=False,
        amplitude_gain="auto",
        amplitude_gain_multiplier=1.0,
        showfig=False,
    )
    high_gain = plot_event_trace_comparison(
        records,
        max_records=1,
        time_limit_s=8.0,
        normalize=False,
        amplitude_gain="auto",
        amplitude_gain_multiplier=2.0,
        showfig=False,
    )
    low_y = low_gain.axes[0].lines[0].get_ydata()
    high_y = high_gain.axes[0].lines[0].get_ydata()
    assert np.nanmax(high_y) - np.nanmin(high_y) > 1.5 * (np.nanmax(low_y) - np.nanmin(low_y))
    plt.close(low_gain)
    plt.close(high_gain)


def test_observed_synthetic_record_section_uses_event_origin_offsets() -> None:
    """Record-section overlays should trim pre-origin observed samples."""

    records = pd.DataFrame(
        {
            "event_id": ["E1"],
            "station": ["S1"],
            "component": ["Z"],
            "distance_km": [20.0],
            "observed": [np.arange(20, dtype=float)],
            "synthetic": [np.arange(10, dtype=float)],
            "dt": [1.0],
            "synthetic_dt": [1.0],
            "observed_time_offset_s": [-5.0],
            "synthetic_time_offset_s": [0.0],
        }
    )
    fig = plot_observed_synthetic_record_section(records, components=["Z"], max_records=1, time_limit_s=8.0, showfig=False)
    ax = fig.axes[0]
    assert ax.get_xlabel() == "Seconds since event origin"
    observed_x = ax.lines[0].get_xdata()
    synthetic_x = ax.lines[1].get_xdata()
    assert float(observed_x[0]) == 0.0
    assert float(observed_x[-1]) == 8.0
    assert float(synthetic_x[0]) == 0.0
    assert float(synthetic_x[-1]) == 8.0
    plt.close(fig)
