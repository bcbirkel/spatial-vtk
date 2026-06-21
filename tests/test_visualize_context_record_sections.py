"""Tests for migrated context and record-section figure helpers."""

from __future__ import annotations

import json
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
from spatial_vtk.visualize.waveforms import (
    plot_event_radial_trace_section,
    plot_station_event_waveform_map,
    plot_waveform_overlay_matrix,
    station_event_waveform_order_frame,
    write_large_run_waveform_comparison_from_outputs,
    write_waveform_comparison_from_notebook_settings,
    write_waveform_comparison_from_outputs,
)


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


def test_waveform_comparison_helper_uses_configured_outputs(tmp_path: Path, monkeypatch) -> None:
    """Waveform comparison figures should be package-orchestrated."""

    import spatial_vtk.visualize.waveforms.comparison as comparison_helpers
    from spatial_vtk.io.output_paths import OutputGroup

    event_station_path = tmp_path / "event_station_records.csv"
    comparison_eligible_path = tmp_path / "comparison_eligible.csv"
    figure_path = tmp_path / "figures" / "event_trace_comparison.png"
    pd.DataFrame(
        {
            "event_id": ["E1"],
            "station": ["S1"],
            "observed_processed_waveform": ["observed.npz"],
            "synthetic_processed_waveform": ["synthetic.npz"],
        }
    ).to_csv(event_station_path, index=False)
    pd.DataFrame(
        {
            "event_id": ["E1", "E1"],
            "station": ["S1", "S2"],
            "component": ["Z", "R"],
            "passband": ["1-2 sec", "1-2 sec"],
            "metric_group": ["trace", "trace"],
            "metric": ["PGA", "PGA"],
            "period_s": [np.nan, np.nan],
        }
    ).to_csv(comparison_eligible_path, index=False)

    calls: dict[str, object] = {}

    def fake_load(comparison_eligible, *, component=None, **kwargs):
        frame = pd.read_csv(comparison_eligible)
        return frame.loc[frame["component"].astype(str).eq(str(component))].reset_index(drop=True)

    def fake_build(event_station_records, qc_summary=None, *, comparison_eligible=None, component="Z", **kwargs):
        calls["event_station_records"] = Path(event_station_records)
        calls["comparison_eligible"] = comparison_eligible.copy()
        calls["component"] = component
        return _records().head(1)

    def fake_plot(records_df, output_path=None, **kwargs):
        calls["plot_records"] = records_df.copy()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"png")
        return Path(output_path)

    monkeypatch.setattr(comparison_helpers, "_load_comparison_eligible_records", fake_load)
    monkeypatch.setattr(comparison_helpers, "_build_qc_waveform_comparison_records", fake_build)
    monkeypatch.setattr(comparison_helpers, "plot_event_trace_comparison", fake_plot)

    outputs = OutputGroup(
        "step_06_plotting",
        {
            "event_station_path": event_station_path,
            "comparison_eligible_path": comparison_eligible_path,
            "event_trace_comparison_path": figure_path,
        },
    )
    assert write_large_run_waveform_comparison_from_outputs is not None

    result = write_waveform_comparison_from_outputs(
        outputs,
        component="Z",
        max_records=12,
        overwrite=True,
        showfig=False,
    )

    assert result.status == "written"
    assert result.figure_path == figure_path
    assert result.status_frame().loc[0, "record_count"] == 1
    assert calls["event_station_records"] == event_station_path
    assert calls["component"] == "Z"
    assert calls["comparison_eligible"]["component"].tolist() == ["Z"]
    _assert_png(figure_path)


def test_waveform_comparison_notebook_settings_gate_disables_without_loading(tmp_path: Path, monkeypatch) -> None:
    """Notebook wrapper should return a status row when figure rendering is disabled."""

    import spatial_vtk.visualize.waveforms.comparison as comparison_helpers
    from spatial_vtk.io.output_paths import OutputGroup

    event_station_path = tmp_path / "event_station_records.csv"
    comparison_eligible_path = tmp_path / "comparison_eligible.csv"
    figure_path = tmp_path / "figures" / "event_trace_comparison.png"
    outputs = OutputGroup(
        "step_06_plotting",
        {
            "event_station_path": event_station_path,
            "comparison_eligible_path": comparison_eligible_path,
            "event_trace_comparison_path": figure_path,
        },
    )

    class Settings:
        component = "R"
        passband = "2-3 sec"

        def render_gate(self, paths, *, missing_message: str):  # noqa: ANN001, ANN202
            return type("Gate", (), {"ready": False, "figures_enabled": False, "message": "figures disabled"})()

        def plot_kwargs(self) -> dict[str, object]:
            return {"showfig": False}

    def fail_if_called(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise AssertionError("disabled figure block should not load waveform records")

    monkeypatch.setattr(comparison_helpers, "write_waveform_comparison_from_outputs", fail_if_called)

    result = write_waveform_comparison_from_notebook_settings(outputs, Settings())

    assert result.status == "disabled"
    assert result.message == "figures disabled"
    assert result.status_frame().loc[0, "record_count"] == 0


def test_waveform_comparison_notebook_settings_delegates_options(tmp_path: Path, monkeypatch) -> None:
    """Notebook wrapper should translate settings into the reusable waveform helper."""

    import spatial_vtk.visualize.waveforms.comparison as comparison_helpers
    from spatial_vtk.io.output_paths import OutputGroup

    event_station_path = tmp_path / "event_station_records.csv"
    comparison_eligible_path = tmp_path / "comparison_eligible.csv"
    figure_path = tmp_path / "figures" / "event_trace_comparison.png"
    event_station_path.write_text("ready", encoding="utf-8")
    comparison_eligible_path.write_text("ready", encoding="utf-8")
    outputs = OutputGroup(
        "step_06_plotting",
        {
            "event_station_path": event_station_path,
            "comparison_eligible_path": comparison_eligible_path,
            "event_trace_comparison_path": figure_path,
        },
    )
    calls: dict[str, object] = {}

    class Settings:
        component = "R"
        passband = "2-3 sec"

        def render_gate(self, paths, *, missing_message: str):  # noqa: ANN001, ANN202
            calls["gate_paths"] = list(paths)
            return type("Gate", (), {"ready": True, "figures_enabled": True, "message": "ready"})()

        def plot_kwargs(self) -> dict[str, object]:
            return {"showfig": False, "write_sidecar": True}

    def fake_write(step_outputs, **kwargs):  # noqa: ANN001, ANN202
        calls["kwargs"] = kwargs
        return comparison_helpers.WaveformComparisonFigureResult(
            figure_path=figure_path,
            event_station_path=event_station_path,
            comparison_eligible_path=comparison_eligible_path,
            records=_records().head(1),
            status="written",
            message="ok",
        )

    monkeypatch.setattr(comparison_helpers, "write_waveform_comparison_from_outputs", fake_write)

    result = write_waveform_comparison_from_notebook_settings(
        outputs,
        Settings(),
        chunksize=25,
        overwrite=True,
        component="T",
        plot_options={"title": "Custom title", "normalize": False},
    )

    assert result.status == "written"
    status = result.status_frame()
    assert status.loc[0, "name"] == "waveform_comparison_figure"
    assert status.loc[0, "path"] == str(figure_path)
    assert bool(status.loc[0, "exists"]) is False
    assert calls["gate_paths"] == [comparison_eligible_path, event_station_path]
    assert calls["kwargs"]["component"] == "T"
    assert calls["kwargs"]["passband"] == "2-3 sec"
    assert calls["kwargs"]["chunksize"] == 25
    assert calls["kwargs"]["overwrite"] is True
    assert calls["kwargs"]["write_sidecar"] is True
    assert calls["kwargs"]["title"] == "Custom title"
    assert calls["kwargs"]["normalize"] is False


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


def test_waveform_figures_write_optional_row_sidecars(tmp_path: Path) -> None:
    """Waveform figures should expose the plotted rows when requested."""

    records = _records().assign(
        dt=0.05,
        synthetic_dt=0.05,
        sta_lon=[-118.4, -118.4, -118.2, -118.2, -118.0, -118.0],
        sta_lat=[34.0, 34.0, 34.1, 34.1, 34.2, 34.2],
        event_lon=-118.3,
        event_lat=34.05,
        azimuth_deg=[20.0, 30.0, 120.0, 130.0, 240.0, 250.0],
        group=["A", "A", "A", "A", "B", "B"],
    )
    sidecar_dir = tmp_path / "sidecars"

    plot_event_trace_comparison(
        records,
        tmp_path / "trace_comparison.png",
        max_records=1,
        write_sidecar=True,
        sidecar_rows=2,
        sidecar_dir=sidecar_dir,
    )
    plot_record_section(
        records,
        tmp_path / "record_section.png",
        components=["Z", "R"],
        max_records=1,
        write_sidecar=True,
        sidecar_rows=2,
        sidecar_dir=sidecar_dir,
    )
    plot_observed_synthetic_record_section(
        records,
        tmp_path / "obs_syn_section.png",
        components=["Z", "R"],
        max_records=1,
        write_sidecar=True,
        sidecar_rows=2,
        sidecar_dir=sidecar_dir,
    )
    plot_station_event_waveform_map(
        records,
        tmp_path / "waveform_map.png",
        add_basemap=False,
        max_traces=2,
        write_sidecar=True,
        sidecar_rows=2,
        sidecar_dir=sidecar_dir,
    )
    plot_event_radial_trace_section(
        records,
        tmp_path / "radial_section.png",
        add_basemap=False,
        write_sidecar=True,
        sidecar_rows=2,
        sidecar_dir=sidecar_dir,
    )
    plot_waveform_overlay_matrix(
        records,
        tmp_path / "overlay_matrix.png",
        add_basemap=False,
        write_sidecar=True,
        sidecar_rows=2,
        sidecar_dir=sidecar_dir,
    )
    plot_distance_amplitude_diagnostics(
        records,
        tmp_path / "distance_amplitude.png",
        write_sidecar=True,
        sidecar_rows=2,
        sidecar_dir=sidecar_dir,
    )

    expected_counts = {
        "trace_comparison": 2,
        "record_section": 2,
        "obs_syn_section": 2,
        "waveform_map": 2,
        "radial_section": 6,
        "overlay_matrix": 6,
        "distance_amplitude": 6,
    }
    for stem, row_count in expected_counts.items():
        meta = json.loads((sidecar_dir / f"{stem}.json").read_text(encoding="utf-8"))
        assert meta["plot_row_count"] == row_count
        assert meta["written_row_count"] == min(2, row_count)
        assert (sidecar_dir / f"{stem}.csv").exists()
        if stem != "distance_amplitude":
            assert (sidecar_dir / f"{stem}.source.csv").exists()
    distance_metadata = json.loads((sidecar_dir / "distance_amplitude.json").read_text(encoding="utf-8"))
    assert distance_metadata["figure_type"] == "distance_amplitude_diagnostics"


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


def test_trace_comparison_accepts_numpy_trace_dictionaries() -> None:
    """Trace overlays should render the lightweight NumPy waveform fixture format."""

    records = pd.DataFrame(
        {
            "event_id": ["E1"],
            "station": ["S1"],
            "component": ["Z"],
            "distance_km": [20.0],
            "observed": [{"data": np.arange(20, dtype=float), "stats": {"sampling_rate": 2.0}}],
            "synthetic": [{"data": np.arange(20, dtype=float) * 0.5, "stats": {"delta": 0.5}}],
        }
    )

    fig = plot_event_trace_comparison(records, max_records=1, showfig=False)
    ax = fig.axes[0]
    assert len(ax.lines) >= 2
    assert float(ax.lines[0].get_xdata()[1]) == pytest.approx(0.5)
    assert float(ax.lines[1].get_xdata()[1]) == pytest.approx(0.5)
    plt.close(fig)


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

    order = station_event_waveform_order_frame(records, max_traces=1)
    assert order.loc[0, "station"] == "NEAR"
    assert order.loc[0, "distance_km"] == pytest.approx(10.0)
    assert list(order.columns) == ["station", "distance_km", "component"]

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


def test_observed_synthetic_record_section_accepts_numpy_trace_dictionaries() -> None:
    """Record-section overlays should render lightweight NumPy trace fixtures."""

    records = pd.DataFrame(
        {
            "event_id": ["E1"],
            "station": ["S1"],
            "component": ["R"],
            "distance_km": [20.0],
            "observed": [{"data": np.arange(20, dtype=float), "stats": {"sampling_rate": 2.0}}],
            "synthetic": [{"data": np.arange(20, dtype=float) * 0.5, "stats": {"delta": 0.5}}],
        }
    )

    fig = plot_observed_synthetic_record_section(records, components=["R"], max_records=1, showfig=False)
    ax = fig.axes[0]
    assert len(ax.lines) >= 2
    assert float(ax.lines[0].get_xdata()[1]) == pytest.approx(0.5)
    assert float(ax.lines[1].get_xdata()[1]) == pytest.approx(0.5)
    plt.close(fig)
