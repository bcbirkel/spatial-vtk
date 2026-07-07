from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
import pytest

from spatial_vtk.io.artifacts import ArtifactRegistry, ArtifactSpec
from spatial_vtk.config import SpatialVTKConfig, clear_active_config
from spatial_vtk.io.master_lists import (
    build_arg_parser as build_master_list_arg_parser,
    build_master_event_list,
    build_master_station_list,
    write_master_station_list,
)
from spatial_vtk.io.metadata import prepare_event_station_table
from spatial_vtk.io.plans import (
    MetricPlan,
    build_arg_parser as build_metric_plan_arg_parser,
    compare_metric_plan_to_table,
    expected_metric_rows_from_inventory,
)
from spatial_vtk.io.waveforms import (
    WaveformPreprocessing,
    build_arg_parser as build_waveform_arg_parser,
    read_waveform_file,
    trace_metadata_table,
    write_trace_metadata_table,
)
from spatial_vtk.io.preprocessing import preprocess_waveform_files
from spatial_vtk.metrics.calculate.arrival_picks import load_arrival_pick_catalog, write_arrival_pick_catalog
from spatial_vtk.metrics.calculate.phasenet_adapter import (
    PhaseNetInputRecord,
    build_arg_parser as build_phasenet_arg_parser,
    normalize_phasenet_output,
    prepare_phasenet_numpy_inputs,
)
from spatial_vtk.qc.build.inventory import (
    _passband_quality_summary,
    build_trace_inventory,
    build_waveform_trace_qc_summary,
    companion_rows_from_master,
)
from spatial_vtk.qc.build.workflow import (
    build_comparison_eligibility,
    build_event_station_pair_retention_table,
    build_event_station_pair_retention_table_from_qc_inventory,
    build_metric_pair_retention_table,
    build_metric_pair_retention_table_from_qc_inventory,
    build_metric_qc_summary,
    build_post_qc_record_table_from_qc_inventory,
    build_qc_availability_table,
    build_qc_drop_cause_table_from_qc_inventory,
    build_qc_waveform_comparison_records,
    build_waveform_qc_summary,
    export_manual_review_queue_from_qc_inventory,
    filter_event_station_records_for_source_overlap,
    load_comparison_eligible_records,
    run_qc_summary_workflow,
    run_qc_summary_workflow_from_config,
    write_comparison_eligibility_from_qc_inventory,
    write_qc_inventory_overlap_from_config,
    write_qc_inventory_overlap_from_full,
)
from spatial_vtk.qc.review.tables import apply_manual_qc_decisions, load_manual_qc_decisions, write_manual_qc_decisions
from spatial_vtk.visualize.dashboard import write_manual_review_queue


@dataclass
class Coordinates:
    latitude: float
    longitude: float
    elevation: float


@dataclass
class Stats:
    network: str
    station: str
    channel: str
    sampling_rate: float
    starttime: str
    endtime: str
    coordinates: Coordinates

    @property
    def npts(self) -> int:
        return 100


@dataclass
class Trace:
    data: np.ndarray
    stats: Stats


def _trace(station: str = "ABC", channel: str = "HNZ") -> Trace:
    return Trace(
        data=np.ones(100, dtype=float),
        stats=Stats(
            network="CI",
            station=station,
            channel=channel,
            sampling_rate=1.0,
            starttime="2020-01-01T00:00:00Z",
            endtime="2020-01-01T00:01:40Z",
            coordinates=Coordinates(latitude=34.1, longitude=-118.2, elevation=10.0),
        ),
    )


def test_waveform_metadata_feeds_master_station_list() -> None:
    stream = [_trace(channel="HNE"), _trace(channel="HNN")]
    meta = trace_metadata_table(stream, event_id="ci123", source="observed")

    assert list(meta["component"]) == ["E", "N"]
    assert meta.loc[0, "station"] == "ABC"

    stations = build_master_station_list(station_tables=[meta])
    assert stations.to_dict(orient="records") == [
        {"network": "CI", "station": "ABC", "lat": 34.1, "lon": -118.2, "elev": 10.0}
    ]


def test_waveform_metadata_computes_missing_endtime_from_numpy_trace_fields() -> None:
    trace = {
        "data": np.ones(5, dtype=float),
        "stats": {
            "network": "CI",
            "station": "ABC",
            "channel": "HNZ",
            "sampling_rate": 2.0,
            "starttime": "2020-01-01T00:00:00Z",
        },
    }

    meta = trace_metadata_table([trace], event_id="ci123", source="observed")

    assert meta.loc[0, "delta"] == pytest.approx(0.5)
    assert meta.loc[0, "npts"] == 5
    assert meta.loc[0, "endtime"] == "2020-01-01T00:00:02+00:00"


def test_master_event_list_uses_common_aliases() -> None:
    raw = pd.DataFrame(
        {
            "id": ["ci123"],
            "time": ["2020-01-01T00:00:00Z"],
            "event_latitude": [34.0],
            "event_longitude": [-118.0],
            "depth": [8.5],
            "mag": [4.2],
        }
    )

    events = build_master_event_list(event_tables=[raw])
    assert events.loc[0, "event_id"] == "ci123"
    assert events.loc[0, "lat"] == 34.0
    assert events.loc[0, "magnitude"] == 4.2


def test_master_list_module_cli_uses_artifact_named_aliases(capsys) -> None:
    """The direct module CLI should not expose only generic input/output names."""

    parser = build_master_list_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["stations", "--help"])
    stations_help_text = capsys.readouterr().out
    with pytest.raises(SystemExit):
        parser.parse_args(["events", "--help"])
    events_help_text = capsys.readouterr().out
    stations_help = parser.parse_args(
        [
            "stations",
            "--station-tables",
            "stations_a.parquet",
            "stations_b.csv",
            "--master-station-output",
            "prepared_stations.parquet",
        ]
    )
    legacy_stations = parser.parse_args(
        [
            "stations",
            "--input",
            "stations.csv",
            "--output",
            "prepared_stations.csv",
        ]
    )
    events_help = parser.parse_args(
        [
            "events",
            "--event-tables",
            "events.parquet",
            "--master-event-output",
            "prepared_events.parquet",
        ]
    )
    legacy_events = parser.parse_args(
        [
            "events",
            "--input",
            "events.csv",
            "--output",
            "prepared_events.csv",
        ]
    )

    assert "--station-tables" in stations_help_text
    assert "--master-station-output" in stations_help_text
    assert "legacy alias" in stations_help_text
    assert "--event-tables" in events_help_text
    assert "--master-event-output" in events_help_text
    assert "legacy alias" in events_help_text
    assert stations_help.station_tables == ["stations_a.parquet", "stations_b.csv"]
    assert stations_help.master_station_output == "prepared_stations.parquet"
    assert legacy_stations.station_tables == ["stations.csv"]
    assert legacy_stations.master_station_output == "prepared_stations.csv"
    assert events_help.event_tables == ["events.parquet"]
    assert events_help.master_event_output == "prepared_events.parquet"
    assert legacy_events.event_tables == ["events.csv"]
    assert legacy_events.master_event_output == "prepared_events.csv"
    assert not hasattr(stations_help, "input")
    assert not hasattr(stations_help, "output")
    assert not hasattr(events_help, "input")
    assert not hasattr(events_help, "output")


def test_waveform_module_cli_uses_trace_metadata_output_alias(capsys) -> None:
    """The direct waveform metadata parser should name its output artifact."""

    parser = build_waveform_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--help"])
    help_text = capsys.readouterr().out
    args = parser.parse_args(
        [
            "observed.mseed",
            "--trace-metadata-output",
            "trace_metadata.parquet",
            "--event-id",
            "ci123",
        ]
    )
    legacy_args = parser.parse_args(
        [
            "observed.mseed",
            "--output",
            "trace_metadata.csv",
        ]
    )

    assert "--trace-metadata-output" in help_text
    assert "--output" in help_text
    assert "legacy alias" in help_text
    assert args.paths == ["observed.mseed"]
    assert args.trace_metadata_output == "trace_metadata.parquet"
    assert args.event_id == "ci123"
    assert legacy_args.trace_metadata_output == "trace_metadata.csv"
    assert not hasattr(args, "output")


def test_metric_plan_module_cli_uses_artifact_named_table_aliases() -> None:
    """The direct metric completeness parser should expose clear table roles."""

    parser = build_metric_plan_arg_parser()
    help_text = parser.format_help()
    args = parser.parse_args(
        [
            "--qc-inventory",
            "qc_inventory.parquet",
            "--metrics-table",
            "metrics_long.parquet",
            "--missing-metrics-output",
            "missing_metrics.parquet",
        ]
    )
    legacy_args = parser.parse_args(
        [
            "--inventory",
            "qc_inventory.csv",
            "--metrics",
            "metrics_long.csv",
            "--missing-output",
            "missing_metrics.csv",
        ]
    )

    assert "--qc-inventory" in help_text
    assert "--metrics-table" in help_text
    assert "--missing-metrics-output" in help_text
    assert "legacy alias" in help_text
    assert args.qc_inventory == "qc_inventory.parquet"
    assert args.metrics_table == "metrics_long.parquet"
    assert args.missing_metrics_output == "missing_metrics.parquet"
    assert legacy_args.qc_inventory == "qc_inventory.csv"
    assert legacy_args.metrics_table == "metrics_long.csv"
    assert legacy_args.missing_metrics_output == "missing_metrics.csv"
    assert not hasattr(args, "inventory")
    assert not hasattr(args, "metrics")
    assert not hasattr(args, "missing_output")


def test_small_public_table_writers_use_suffixless_csv_targets(tmp_path) -> None:
    station_path = tmp_path / "stations"
    station_rows = pd.DataFrame({"station": ["STA"], "network": ["XX"], "lat": [34.1], "lon": [-118.2]})
    written_station_path = write_master_station_list(station_rows, station_path)

    assert written_station_path == station_path.with_suffix(".csv")
    assert pd.read_csv(written_station_path).loc[0, "station"] == "STA"
    skipped_station_path = write_master_station_list(
        pd.DataFrame({"station": ["NEW"], "network": ["XX"], "lat": [34.2], "lon": [-118.3]}),
        station_path,
        overwrite=False,
    )
    assert skipped_station_path == written_station_path
    assert pd.read_csv(written_station_path).loc[0, "station"] == "STA"

    pick_path = tmp_path / "picks"
    pick_rows = pd.DataFrame(
        {
            "event_id": ["ci123"],
            "station": ["STA"],
            "component": ["Z"],
            "phase": ["p"],
            "pick_time_abs": ["2020-01-01T00:00:00Z"],
            "pick_time_rel_s": [1.5],
            "probability": [0.9],
            "method": ["catalog"],
        }
    )
    written_pick_path = write_arrival_pick_catalog(pick_rows, pick_path)

    assert written_pick_path == pick_path.with_suffix(".csv")
    assert load_arrival_pick_catalog(written_pick_path).loc[0, "phase"] == "P"
    skipped_pick_path = write_arrival_pick_catalog(pick_rows.assign(phase=["S"]), pick_path, overwrite=False)
    assert skipped_pick_path == written_pick_path
    assert load_arrival_pick_catalog(written_pick_path).loc[0, "phase"] == "P"

    metadata_path = write_trace_metadata_table([_trace()], tmp_path / "trace_metadata", event_id="ci123")
    assert metadata_path == tmp_path / "trace_metadata.csv"
    assert pd.read_csv(metadata_path).loc[0, "event_id"] == "ci123"

    queue_path = write_manual_review_queue([{"event_id": "ci123", "station": "abc"}], tmp_path / "manual_queue")
    assert queue_path == tmp_path / "manual_queue.csv"
    assert pd.read_csv(queue_path).loc[0, "station"] == "ABC"


def test_event_station_table_computes_path_geometry() -> None:
    station_metadata = pd.DataFrame({"station": ["ABC"], "lat": [34.1], "lon": [-118.2]})
    event_metadata = pd.DataFrame({"event_id": ["ci123"], "event_lat": [34.0], "event_lon": [-118.0]})
    event_station_metadata = pd.DataFrame({"event_id": ["ci123"], "station": ["ABC"]})

    event_stations = prepare_event_station_table(
        event_station_metadata=event_station_metadata,
        station_metadata=station_metadata,
        event_metadata=event_metadata,
    )

    assert event_stations.loc[0, "distance_km"] == pytest.approx(21.44, abs=0.1)
    assert 0.0 <= event_stations.loc[0, "azimuth_deg"] <= 360.0
    assert 0.0 <= event_stations.loc[0, "backazimuth_deg"] <= 360.0


def test_qc_inventory_companion_and_manual_decisions(tmp_path) -> None:
    inventory = build_trace_inventory({"ci123": [_trace()]}, observed_variant="rotated")
    assert inventory.loc[0, "available"]
    assert not bool(inventory.loc[0, "reject_1_3s"])

    companion = companion_rows_from_master(inventory)
    assert companion
    assert companion[0]["event_id"] == "ci123"

    decisions = pd.DataFrame(
        [
            {
                "event_id": "ci123",
                "station": "ABC",
                "component": "Z",
                "scope_kind": "band",
                "scope_label": "1-3s",
                "decision": "reject",
                "reason_code": "manual_bad_trace",
                "notes": "test decision",
            }
        ]
    )
    decision_path = write_manual_qc_decisions(decisions, tmp_path / "manual_qc")
    assert decision_path == tmp_path / "manual_qc.csv"
    loaded = load_manual_qc_decisions(decision_path)
    skipped_decision_path = write_manual_qc_decisions(decisions.assign(decision=["accept"]), tmp_path / "manual_qc", overwrite=False)
    assert skipped_decision_path == decision_path
    assert load_manual_qc_decisions(decision_path).loc[0, "decision"] == "reject"
    updated = apply_manual_qc_decisions(inventory, loaded)
    assert bool(updated.loc[0, "reject_1_3s"])
    assert updated.loc[0, "reject_reason_1_3s"] == "manual_bad_trace"


def test_waveform_trace_qc_propagates_to_metric_qc(tmp_path) -> None:
    trace = _trace()
    trace.data = np.zeros(100, dtype=float)
    waveform_path = tmp_path / "ci123.pkl"
    with waveform_path.open("wb") as handle:
        pickle.dump([trace], handle)
    event_stations = pd.DataFrame(
        {
            "event_id": ["ci123"],
            "station": ["ABC"],
            "start": ["2020-01-01T00:00:00Z"],
            "observed_pickle": [waveform_path],
        }
    )

    trace_qc = build_waveform_trace_qc_summary(
        event_stations,
        source="observed",
        waveform_path_col="observed_pickle",
        components=("Z",),
        passbands=[(1.0, 2.0)],
        min_record_length_s=60.0,
        min_end_after_origin_s=60.0,
    )
    assert trace_qc.loc[0, "qc_status"] == "fail"
    assert "flat_trace" in trace_qc.loc[0, "qc_reason"]
    assert {
        "trace_start_s",
        "trace_end_s",
        "trace_duration_s",
        "valid_start_rel_s",
        "valid_end_rel_s",
        "valid_start_sample",
        "valid_end_sample",
        "sample_interval_s",
        "sample_count",
        "raw_peak_abs",
        "raw_rms_amplitude",
        "dominant_period_s",
        "band_peak_abs",
        "energy_frac",
        "band_peak_abs_1_2s",
        "energy_frac_1_2s",
    } <= set(trace_qc.columns)
    assert trace_qc.loc[0, "trace_start_s"] == 0.0
    assert trace_qc.loc[0, "trace_duration_s"] == 100.0
    assert trace_qc.loc[0, "valid_start_rel_s"] == 0.0
    assert trace_qc.loc[0, "valid_end_rel_s"] == 100.0
    assert trace_qc.loc[0, "valid_start_sample"] == 0
    assert trace_qc.loc[0, "valid_end_sample"] == 100
    assert trace_qc.loc[0, "sample_count"] == 100

    metric_qc = build_metric_qc_summary(
        event_stations,
        metrics=("PGA",),
        components=("Z",),
        passbands=[(1.0, 2.0)],
        sources=("observed",),
        trace_qc_summary=trace_qc,
    )
    assert metric_qc.loc[0, "qc_status"] == "fail"
    assert "flat_trace" in metric_qc.loc[0, "qc_reason"]
    assert metric_qc.loc[0, "valid_start_rel_s"] == 0.0
    assert metric_qc.loc[0, "valid_end_rel_s"] == 100.0
    assert metric_qc.loc[0, "valid_start_sample"] == 0
    assert metric_qc.loc[0, "valid_end_sample"] == 100


def test_waveform_qc_summary_builds_both_sources_from_processed_columns(tmp_path) -> None:
    trace = _trace()
    trace.data = np.zeros(100, dtype=float)
    observed_path = tmp_path / "observed.pkl"
    synthetic_path = tmp_path / "synthetic.pkl"
    for path in (observed_path, synthetic_path):
        with path.open("wb") as handle:
            pickle.dump([trace], handle)
    event_stations = pd.DataFrame(
        {
            "event_id": ["ci123"],
            "station": ["ABC"],
            "start": ["2020-01-01T00:00:00Z"],
            "observed_processed_waveform": [observed_path],
            "synthetic_processed_waveform": [synthetic_path],
        }
    )

    trace_qc = build_waveform_qc_summary(
        event_stations,
        components=("Z",),
        passbands=[(1.0, 2.0)],
        min_record_length_s=60.0,
        min_end_after_origin_s=60.0,
        snr_threshold=3.0,
    )

    assert set(trace_qc["source"]) == {"observed", "synthetic"}
    assert len(trace_qc) == 2
    assert set(trace_qc["qc_status"]) == {"fail"}
    assert trace_qc["qc_reason"].str.contains("flat_trace").all()


def test_waveform_trace_qc_uses_source_specific_arrival_pick_for_onset(tmp_path) -> None:
    trace = _trace()
    samples = 0.02 * np.ones(100, dtype=float)
    samples[20:40] = 1.0
    trace.data = samples
    waveform_path = tmp_path / "ci123.pkl"
    with waveform_path.open("wb") as handle:
        pickle.dump([trace], handle)
    event_stations = pd.DataFrame(
        {
            "event_id": ["ci123"],
            "station": ["ABC"],
            "start": ["2020-01-01T00:00:00Z"],
            "observed_pickle": [waveform_path],
        }
    )
    picks = pd.DataFrame(
        [
            {
                "source": "observed",
                "event_id": "ci123",
                "station": "ABC",
                "component": "ALL",
                "phase": "P",
                "pick_time_abs": "",
                "pick_time_rel_s": 20.0,
                "probability": 0.9,
                "method": "phasenet",
            },
            {
                "source": "synthetic",
                "event_id": "ci123",
                "station": "ABC",
                "component": "ALL",
                "phase": "P",
                "pick_time_abs": "",
                "pick_time_rel_s": 5.0,
                "probability": 0.95,
                "method": "phasenet",
            },
        ]
    )

    trace_qc = build_waveform_trace_qc_summary(
        event_stations,
        source="observed",
        waveform_path_col="observed_pickle",
        components=("Z",),
        passbands=[(1.0, 2.0)],
        min_record_length_s=1.0,
        min_end_after_origin_s=1.0,
        arrival_pick_catalog=picks,
        onset_phase="P",
        min_onset_pick_probability=0.5,
    )

    assert trace_qc.loc[0, "onset_rel_s"] == pytest.approx(20.0)


def test_waveform_trace_qc_allows_noise_window_outside_valid_interval() -> None:
    samples = np.zeros(30, dtype=float)
    samples[2:5] = 0.1
    samples[6:17] = 1.0
    trace_summary = {
        "samples": samples,
        "times_s": np.arange(samples.size, dtype=float),
        "dt": 1.0,
        "valid_start_rel_s": 5.0,
        "valid_end_rel_s": 25.0,
    }

    summary = _passband_quality_summary(
        trace_summary,
        period_min_s=1.0,
        period_max_s=3.0,
        snr_threshold=3.0,
        noise_window_min_s=1.0,
        signal_window_min_s=10.0,
        noise_gap_s=0.5,
        signal_gap_s=0.5,
        origin_tolerance_s=0.5,
        pre_origin_signal_ratio_threshold=0.5,
        global_reasons=[],
        pick_onset_rel_s=5.0,
    )

    assert summary["noise_window_valid"] is True
    assert summary["signal_window_valid"] is True
    assert summary["noise_rms"] == pytest.approx(0.1)
    assert summary["signal_rms"] == pytest.approx(1.0)


def test_waveform_trace_qc_rejects_pick_without_valid_signal_window() -> None:
    samples = np.zeros(130, dtype=float)
    samples[30:46] = 1.0
    trace_summary = {
        "samples": samples,
        "times_s": np.arange(samples.size, dtype=float),
        "dt": 1.0,
        "valid_start_rel_s": 6.0,
        "valid_end_rel_s": 114.0,
    }

    summary = _passband_quality_summary(
        trace_summary,
        period_min_s=1.0,
        period_max_s=2.0,
        snr_threshold=3.0,
        noise_window_min_s=1.0,
        signal_window_min_s=10.0,
        noise_gap_s=0.5,
        signal_gap_s=0.5,
        origin_tolerance_s=0.5,
        pre_origin_signal_ratio_threshold=0.5,
        global_reasons=[],
        pick_onset_rel_s=115.0,
    )

    assert summary["onset_rel_s"] < 50.0
    assert summary["onset_rel_s"] != pytest.approx(115.0)
    assert summary["signal_window_valid"] is True


def test_comparison_eligibility_coalesces_shared_metadata() -> None:
    qc_summary = pd.DataFrame(
        [
            {
                "source": "observed",
                "event_id": "ci123",
                "station": "ABC",
                "component": "Z",
                "passband": "1-2 sec",
                "metric_group": "amplitude",
                "metric": "PGA",
                "period_s": 0.0,
                "qc_status": "pass",
                "qc_reason": "",
                "event_title": "Test earthquake",
                "magnitude": 4.2,
                "distance_km": 12.5,
                "station_lat": 34.1,
                "station_lon": -118.2,
            },
            {
                "source": "synthetic",
                "event_id": "ci123",
                "station": "ABC",
                "component": "Z",
                "passband": "1-2 sec",
                "metric_group": "amplitude",
                "metric": "PGA",
                "period_s": 0.0,
                "qc_status": "pass",
                "qc_reason": "",
                "event_title": "",
                "magnitude": np.nan,
                "distance_km": np.nan,
                "station_lat": np.nan,
                "station_lon": np.nan,
            },
        ]
    )

    eligible = build_comparison_eligibility(qc_summary)

    assert len(eligible) == 1
    assert eligible.loc[0, "distance_km"] == pytest.approx(12.5)
    assert eligible.loc[0, "magnitude"] == pytest.approx(4.2)
    assert eligible.loc[0, "station_lat"] == pytest.approx(34.1)
    assert "distance_km_observed" not in eligible.columns
    assert "distance_km_synthetic" not in eligible.columns
    assert {"qc_status_observed", "qc_status_synthetic"} <= set(eligible.columns)


def test_metric_pair_retention_table_counts_both_sides() -> None:
    qc_summary = pd.DataFrame(
        [
            {"source": "observed", "event_id": "e1", "station": "S1", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass"},
            {"source": "synthetic", "event_id": "e1", "station": "S1", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass"},
            {"source": "observed", "event_id": "e1", "station": "S2", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "fail"},
            {"source": "synthetic", "event_id": "e1", "station": "S2", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass"},
        ]
    )

    retention = build_metric_pair_retention_table(qc_summary)

    assert len(retention) == 1
    assert retention.loc[0, "total_pairs"] == 2
    assert retention.loc[0, "retained_pairs"] == 1
    assert retention.loc[0, "retention_percent"] == pytest.approx(50.0)


def test_event_station_pair_retention_table_counts_across_metrics() -> None:
    qc_summary = pd.DataFrame(
        [
            {"source": "observed", "event_id": "e1", "station": "S1", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass"},
            {"source": "synthetic", "event_id": "e1", "station": "S1", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass"},
            {"source": "observed", "event_id": "e1", "station": "S1", "component": "R", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGV", "period_s": 0.0, "qc_status": "fail"},
            {"source": "synthetic", "event_id": "e1", "station": "S1", "component": "R", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGV", "period_s": 0.0, "qc_status": "pass"},
            {"source": "observed", "event_id": "e2", "station": "S1", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass"},
            {"source": "synthetic", "event_id": "e2", "station": "S1", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass"},
        ]
    )

    retention = build_event_station_pair_retention_table(qc_summary)

    e1_s1 = retention.loc[retention["event_id"].eq("e1") & retention["station"].eq("S1")].iloc[0]
    assert e1_s1["total_pairs"] == 2
    assert e1_s1["retained_pairs"] == 1
    assert e1_s1["retention_percent"] == pytest.approx(50.0)
    e2_s1 = retention.loc[retention["event_id"].eq("e2") & retention["station"].eq("S1")].iloc[0]
    assert e2_s1["retention_percent"] == pytest.approx(100.0)


def test_source_overlap_filter_supports_event_and_event_station_scopes() -> None:
    records = pd.DataFrame(
        {
            "event_id": ["e1", "e1", "e2", "e3"],
            "station": ["S1", "S2", "S1", "S1"],
            "observed_processed_waveform": ["obs-e1-s1.pkl", "obs-e1-s2.pkl", "obs-e2-s1.pkl", ""],
            "synthetic_processed_waveform": ["syn-e1-s1.pkl", "", "", "syn-e3-s1.pkl"],
        }
    )

    event_scope = filter_event_station_records_for_source_overlap(records, scope="event")
    event_station_scope = filter_event_station_records_for_source_overlap(records, scope="event_station")

    assert event_scope[["event_id", "station"]].to_dict("records") == [
        {"event_id": "e1", "station": "S1"},
        {"event_id": "e1", "station": "S2"},
    ]
    assert event_station_scope[["event_id", "station"]].to_dict("records") == [
        {"event_id": "e1", "station": "S1"}
    ]


def test_metric_qc_can_restrict_to_source_overlap() -> None:
    records = pd.DataFrame(
        {
            "event_id": ["e1", "e1", "e2"],
            "station": ["S1", "S2", "S1"],
            "observed_processed_waveform": ["obs-e1-s1.pkl", "obs-e1-s2.pkl", "obs-e2-s1.pkl"],
            "synthetic_processed_waveform": ["syn-e1-s1.pkl", "", ""],
        }
    )

    event_qc = build_metric_qc_summary(
        records,
        metrics=["PGA"],
        components=["Z"],
        passbands=[[1.0, 2.0]],
        require_source_overlap=True,
        source_overlap_scope="event",
    )
    event_station_qc = build_metric_qc_summary(
        records,
        metrics=["PGA"],
        components=["Z"],
        passbands=[[1.0, 2.0]],
        require_source_overlap=True,
        source_overlap_scope="event_station",
    )

    assert set(event_qc["event_id"]) == {"e1"}
    assert set(event_qc["station"]) == {"S1", "S2"}
    assert set(event_station_qc["event_id"]) == {"e1"}
    assert set(event_station_qc["station"]) == {"S1"}


def test_qc_inventory_overlap_sidecar_streams_filtered_rows(tmp_path: Path) -> None:
    records = pd.DataFrame(
        {
            "event_id": ["e1", "e1", "e2"],
            "station": ["S1", "S2", "S1"],
            "observed_processed_waveform": ["obs-e1-s1.pkl", "obs-e1-s2.pkl", "obs-e2-s1.pkl"],
            "synthetic_processed_waveform": ["syn-e1-s1.pkl", "syn-e1-s2.pkl", ""],
        }
    )
    qc_summary = pd.DataFrame(
        [
            {"source": "observed", "event_id": "e1", "station": "S1", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass", "qc_reason": ""},
            {"source": "synthetic", "event_id": "e1", "station": "S1", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass", "qc_reason": ""},
            {"source": "observed", "event_id": "e1", "station": "S2", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "fail", "qc_reason": "missing_waveform_path"},
            {"source": "synthetic", "event_id": "e1", "station": "S2", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "fail", "qc_reason": "missing_station"},
            {"source": "observed", "event_id": "e2", "station": "S1", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass", "qc_reason": ""},
        ]
    )
    qc_path = tmp_path / "qc_inventory.csv"
    qc_summary.to_csv(qc_path, index=False)

    event_sidecar = tmp_path / "qc_inventory_overlap_event.csv"
    write_qc_inventory_overlap_from_full(
        qc_path,
        records,
        event_sidecar,
        scope="event",
        chunksize=2,
        require_trace_overlap=False,
    )
    event_overlap = pd.read_csv(event_sidecar)
    assert event_overlap[["event_id", "station"]].drop_duplicates().to_dict("records") == [
        {"event_id": "e1", "station": "S1"},
        {"event_id": "e1", "station": "S2"},
    ]

    event_station_sidecar = tmp_path / "qc_inventory_overlap_event_station.csv"
    write_qc_inventory_overlap_from_full(
        qc_path,
        records,
        event_station_sidecar,
        scope="event_station",
        chunksize=2,
        require_trace_overlap=False,
    )
    event_station_overlap = pd.read_csv(event_station_sidecar)
    assert event_station_overlap[["event_id", "station"]].drop_duplicates().to_dict("records") == [
        {"event_id": "e1", "station": "S1"},
        {"event_id": "e1", "station": "S2"},
    ]

    default_sidecar = tmp_path / "qc_inventory_overlap_default.csv"
    write_qc_inventory_overlap_from_full(qc_path, records, default_sidecar, chunksize=2)
    default_overlap = pd.read_csv(default_sidecar)
    assert default_overlap[["event_id", "station"]].drop_duplicates().to_dict("records") == [
        {"event_id": "e1", "station": "S1"}
    ]
    assert "missing_station" not in set(default_overlap.get("qc_reason", pd.Series(dtype=object)).astype(str))

    parquet_sidecar = tmp_path / "qc_inventory_overlap.parquet"
    write_qc_inventory_overlap_from_full(qc_path, records, parquet_sidecar, scope="event", chunksize=2)
    parquet_overlap = build_metric_pair_retention_table_from_qc_inventory(parquet_sidecar, chunksize=2)
    assert parquet_sidecar.exists()
    assert parquet_overlap["total_pairs"].sum() == 1


def test_qc_inventory_overlap_from_config_resolves_standard_paths(tmp_path: Path) -> None:
    clear_active_config()
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  tables: outputs/tables
""",
        encoding="utf-8",
    )
    output_root = tmp_path / "outputs" / "tables"
    output_root.mkdir(parents=True)
    pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "station": ["S1", "S2"],
            "observed_processed_waveform": ["obs-e1-s1.pkl", "obs-e2-s2.pkl"],
            "synthetic_processed_waveform": ["syn-e1-s1.pkl", ""],
        }
    ).to_csv(output_root / "event_station_records.csv", index=False)
    pd.DataFrame(
        [
            {"source": "observed", "event_id": "e1", "station": "S1", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass", "qc_reason": ""},
            {"source": "synthetic", "event_id": "e1", "station": "S1", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass", "qc_reason": ""},
            {"source": "observed", "event_id": "e2", "station": "S2", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass", "qc_reason": ""},
        ]
    ).to_csv(output_root / "qc_inventory.csv", index=False)

    result = write_qc_inventory_overlap_from_config(config_path=config_path, chunksize=2, overwrite=True)

    overlap_path = Path(str(result["qc_inventory_overlap"]))
    overlap = pd.read_parquet(overlap_path) if overlap_path.suffix == ".parquet" else pd.read_csv(overlap_path)
    assert result["scope"] == "event_station"
    assert overlap[["event_id", "station"]].drop_duplicates().to_dict("records") == [
        {"event_id": "e1", "station": "S1"}
    ]


def test_large_qc_inventory_helpers_stream_event_station_chunks(tmp_path: Path) -> None:
    qc_summary = pd.DataFrame(
        [
            {"source": "observed", "event_id": "e1", "station": "S1", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass", "qc_reason": "", "event_lat": 1.0, "event_lon": 2.0, "station_lat": 3.0, "station_lon": 4.0},
            {"source": "synthetic", "event_id": "e1", "station": "S1", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass", "qc_reason": "", "event_lat": 1.0, "event_lon": 2.0, "station_lat": 3.0, "station_lon": 4.0},
            {"source": "observed", "event_id": "e1", "station": "S1", "component": "R", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGV", "period_s": 0.0, "qc_status": "fail", "qc_reason": "low_snr", "event_lat": 1.0, "event_lon": 2.0, "station_lat": 3.0, "station_lon": 4.0},
            {"source": "synthetic", "event_id": "e1", "station": "S1", "component": "R", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGV", "period_s": 0.0, "qc_status": "pass", "qc_reason": "", "event_lat": 1.0, "event_lon": 2.0, "station_lat": 3.0, "station_lon": 4.0},
            {"source": "observed", "event_id": "e2", "station": "S2", "component": "Z", "passband": "2-3 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass", "qc_reason": "", "event_lat": 5.0, "event_lon": 6.0, "station_lat": 7.0, "station_lon": 8.0},
            {"source": "synthetic", "event_id": "e2", "station": "S2", "component": "Z", "passband": "2-3 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "fail", "qc_reason": "missing_waveform_file", "event_lat": 5.0, "event_lon": 6.0, "station_lat": 7.0, "station_lon": 8.0},
        ]
    )
    qc_path = tmp_path / "qc_inventory.csv"
    qc_summary.to_csv(qc_path, index=False)

    eligible_path = tmp_path / "comparison_eligible.csv"
    write_comparison_eligibility_from_qc_inventory(qc_path, eligible_path, chunksize=3)
    eligible = pd.read_csv(eligible_path)
    expected_eligible = build_comparison_eligibility(qc_summary)
    assert eligible[["event_id", "station", "component", "metric"]].to_dict("records") == expected_eligible[["event_id", "station", "component", "metric"]].to_dict("records")
    mtime = eligible_path.stat().st_mtime_ns
    write_comparison_eligibility_from_qc_inventory(qc_path, eligible_path, chunksize=3, overwrite=False)
    assert eligible_path.stat().st_mtime_ns == mtime

    eligible_sample = load_comparison_eligible_records(
        eligible_path,
        component="Z",
        max_records=1,
        chunksize=1,
    )
    assert eligible_sample[["event_id", "station", "component", "metric"]].to_dict("records") == [
        {"event_id": "e1", "station": "S1", "component": "Z", "metric": "PGA"}
    ]

    metric_retention = build_metric_pair_retention_table_from_qc_inventory(qc_path, chunksize=3)
    expected_metric_retention = build_metric_pair_retention_table(qc_summary)
    pd.testing.assert_frame_equal(metric_retention.reset_index(drop=True), expected_metric_retention.reset_index(drop=True))

    event_station_retention = build_event_station_pair_retention_table_from_qc_inventory(qc_path, chunksize=3)
    expected_event_station_retention = build_event_station_pair_retention_table(qc_summary)
    pd.testing.assert_frame_equal(event_station_retention.reset_index(drop=True), expected_event_station_retention.reset_index(drop=True))

    event_stations = pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "station": ["S1", "S2"],
            "lat": [3.0, 7.0],
            "lon": [4.0, 8.0],
        }
    )
    post_qc = build_post_qc_record_table_from_qc_inventory(
        event_stations,
        qc_summary=qc_path,
        chunksize=3,
    )
    assert post_qc.set_index(["event_id", "station"])["qc_status"].to_dict() == {
        ("e1", "S1"): "pass",
        ("e2", "S2"): "fail",
    }
    assert post_qc.set_index(["event_id", "station"])["sta_lat"].to_dict() == {
        ("e1", "S1"): 3.0,
        ("e2", "S2"): 7.0,
    }
    assert post_qc.set_index(["event_id", "station"])["sta_lon"].to_dict() == {
        ("e1", "S1"): 4.0,
        ("e2", "S2"): 8.0,
    }

    drop_causes = build_qc_drop_cause_table_from_qc_inventory(qc_path, chunksize=3)
    assert drop_causes.set_index("_reason")["count"].to_dict() == {
        "Low SNR": 1,
        "Missing waveform file": 1,
    }
    overlap_drop_causes = build_qc_drop_cause_table_from_qc_inventory(qc_path, event_ids=["e1"], chunksize=3)
    assert overlap_drop_causes.set_index("_reason")["count"].to_dict() == {"Low SNR": 1}

    queue_path = tmp_path / "manual_queue.csv"
    export_manual_review_queue_from_qc_inventory(qc_path, queue_path, chunksize=3)
    queue = pd.read_csv(queue_path)
    assert queue[["event_id", "station"]].to_dict("records") == [
        {"event_id": "e1", "station": "S1"},
        {"event_id": "e2", "station": "S2"},
    ]
    queue_path.write_text("event_id,station\ncached,row\n", encoding="utf-8")
    export_manual_review_queue_from_qc_inventory(qc_path, queue_path, chunksize=3, overwrite=False)
    assert pd.read_csv(queue_path).to_dict("records") == [{"event_id": "cached", "station": "row"}]


def test_qc_summary_workflow_writes_standard_outputs(tmp_path: Path) -> None:
    clear_active_config()
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  tables: outputs/tables
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    records = pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "station": ["S1", "S2"],
            "lat": [3.0, 7.0],
            "lon": [4.0, 8.0],
            "observed_processed_waveform": ["obs1.pkl", "obs2.pkl"],
            "synthetic_processed_waveform": ["syn1.pkl", "syn2.pkl"],
        }
    )
    events = pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "event_lat": [1.0, 5.0],
            "event_lon": [2.0, 6.0],
        }
    )
    qc_summary = pd.DataFrame(
        [
            {"source": "observed", "event_id": "e1", "station": "S1", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass", "qc_reason": ""},
            {"source": "synthetic", "event_id": "e1", "station": "S1", "component": "Z", "passband": "1-2 sec", "metric_group": "amplitude", "metric": "PGA", "period_s": 0.0, "qc_status": "pass", "qc_reason": ""},
            {"source": "observed", "event_id": "e2", "station": "S2", "component": "Z", "passband": "2-3 sec", "metric_group": "amplitude", "metric": "PGV", "period_s": 0.0, "qc_status": "fail", "qc_reason": "low_snr"},
            {"source": "synthetic", "event_id": "e2", "station": "S2", "component": "Z", "passband": "2-3 sec", "metric_group": "amplitude", "metric": "PGV", "period_s": 0.0, "qc_status": "pass", "qc_reason": ""},
        ]
    )
    output_root = tmp_path / "outputs" / "tables"
    output_root.mkdir(parents=True)
    records.to_csv(output_root / "event_station_records.csv", index=False)
    events.to_csv(output_root / "prepared_events.csv", index=False)
    qc_summary.to_csv(output_root / "qc_inventory.csv", index=False)
    qc_summary.to_parquet(output_root / "qc_inventory_overlap.parquet", index=False)

    result = run_qc_summary_workflow(cfg=cfg, chunksize=2, overwrite=True, verbose=True)

    assert result.paths["comparison_eligible_records"].exists()
    assert result.paths["qc_metric_pair_retention"].exists()
    assert result.paths["qc_event_station_pair_retention"].exists()
    assert result.paths["qc_availability"].exists()
    assert result.paths["post_qc_records"].exists()
    assert result.paths["qc_drop_causes"].exists()
    assert result.paths["qc_drop_causes_overlap"].exists()
    assert result.paths["manual_review_queue"].exists()
    status = result.status_frame().set_index("artifact")
    assert {"name", "artifact_label", "artifact_role", "exists", "resolved_path", "path"} <= set(status.columns)
    assert status.loc["comparison_eligible_records", "status"] == "ready"
    assert status.loc["comparison_eligible_records", "name"] == "comparison_eligible_records"
    assert status.loc["comparison_eligible_records", "artifact_label"] == "comparison eligible records table"
    assert status.loc["comparison_eligible_records", "artifact_role"] == "output_table"
    assert bool(status.loc["comparison_eligible_records", "exists"]) is True
    assert status.loc["comparison_eligible_records", "resolved_path"] == status.loc["comparison_eligible_records", "path"]
    assert status.loc["post_qc_records", "rows"] == 2
    eligible = pd.read_csv(result.paths["comparison_eligible_records"])
    assert eligible[["event_id", "station", "metric"]].to_dict("records") == [
        {"event_id": "e1", "station": "S1", "metric": "PGA"}
    ]
    post_qc = pd.read_csv(result.paths["post_qc_records"])
    assert post_qc.set_index(["event_id", "station"])["qc_status"].to_dict() == {
        ("e1", "S1"): "pass",
        ("e2", "S2"): "fail",
    }
    availability = pd.read_csv(result.paths["qc_availability"])
    assert availability.set_index(["event_id", "station"])[["observed_available", "synthetic_available"]].to_dict("index") == {
        ("e1", "S1"): {"observed_available": True, "synthetic_available": True},
        ("e2", "S2"): {"observed_available": False, "synthetic_available": True},
    }

    wrapper_result = run_qc_summary_workflow_from_config(
        config_path=config_path,
        chunksize=2,
        overwrite=True,
        verbose=False,
    )
    assert Path(wrapper_result["paths"]["qc_availability"]).exists()
    assert wrapper_result["output_paths"]["qc_availability"] == wrapper_result["paths"]["qc_availability"]
    assert wrapper_result["rows"]["post_qc_records"] == 2


def test_qc_waveform_comparison_records_loads_retained_pairs(tmp_path) -> None:
    observed = _trace()
    observed.data = np.linspace(0.0, 1.0, 100)
    synthetic = _trace()
    synthetic.data = np.linspace(0.0, 0.5, 100)
    observed_path = tmp_path / "observed.pkl"
    synthetic_path = tmp_path / "synthetic.pkl"
    with observed_path.open("wb") as handle:
        pickle.dump([observed], handle)
    with synthetic_path.open("wb") as handle:
        pickle.dump([synthetic], handle)
    event_stations = pd.DataFrame(
        {
            "event_id": ["e1"],
            "station": ["ABC"],
            "start": ["2020-01-01T00:00:00Z"],
            "distance_km": [12.0],
            "observed_processed_waveform": [observed_path],
            "synthetic_processed_waveform": [synthetic_path],
        }
    )
    comparison_eligible = pd.DataFrame(
        {
            "event_id": ["e1"],
            "station": ["ABC"],
            "component": ["Z"],
            "passband": ["1-2 sec"],
            "distance_km": [12.0],
        }
    )

    records = build_qc_waveform_comparison_records(event_stations, comparison_eligible=comparison_eligible, component="Z", max_distance_km=50)

    assert len(records) == 1
    assert records.loc[0, "distance_km"] == pytest.approx(12.0)
    assert records.loc[0, "dt"] == pytest.approx(1.0)
    assert np.asarray(records.loc[0, "observed"].data)[-1] == pytest.approx(1.0)


def test_qc_availability_table_can_reflect_post_qc_failures() -> None:
    event_stations = pd.DataFrame({"event_id": ["ci123"], "station": ["ABC"]})
    qc_summary = pd.DataFrame(
        [
            {"source": "observed", "event_id": "ci123", "station": "ABC", "qc_status": "pass"},
            {"source": "observed", "event_id": "ci123", "station": "ABC", "qc_status": "fail"},
            {"source": "synthetic", "event_id": "ci123", "station": "ABC", "qc_status": "pass"},
        ]
    )

    strict = build_qc_availability_table(event_stations, qc_summary=qc_summary)
    permissive = build_qc_availability_table(event_stations, qc_summary=qc_summary, qc_aggregate="any_pass")

    assert not bool(strict.loc[0, "observed_available"])
    assert bool(strict.loc[0, "synthetic_available"])
    assert bool(permissive.loc[0, "observed_available"])
    assert bool(permissive.loc[0, "synthetic_available"])


def test_waveform_preprocessing_workflow_writes_processed_files(tmp_path) -> None:
    clear_active_config()
    samples = np.sin(2.0 * np.pi * 1.0 * np.arange(0.0, 2.0, 0.01))
    trace = _trace()
    trace.data = samples
    trace.stats.sampling_rate = 100.0
    waveform_path = tmp_path / "raw" / "ci123.pkl"
    waveform_path.parent.mkdir()
    with waveform_path.open("wb") as handle:
        pickle.dump([trace], handle)
    records = pd.DataFrame(
        {
            "event_id": ["ci123"],
            "station": ["ABC"],
            "observed_waveform": [waveform_path],
        }
    )

    result = preprocess_waveform_files(
        records,
        tmp_path / "processed",
        source_columns={"observed": "observed_waveform"},
        preprocessing=WaveformPreprocessing(lowpass_hz=4.0, resample_hz=20.0),
    )

    processed_path = result.event_station_records.loc[0, "observed_processed_waveform"]
    assert result.event_station_path.exists()
    assert result.manifest_path.exists()
    assert result.trace_metadata_path.exists()
    assert result.preprocessed_event_station_path == result.event_station_path
    assert result.preprocessed_manifest_path == result.manifest_path
    assert result.preprocessed_trace_metadata_path == result.trace_metadata_path
    status = result.status_frame()
    assert status["name"].tolist() == [
        "preprocessed_event_station_path",
        "preprocessed_manifest_path",
        "preprocessed_trace_metadata_path",
    ]
    assert status["artifact"].tolist() == [
        "preprocessed_event_station",
        "preprocessed_manifest",
        "preprocessed_trace_metadata",
    ]
    assert status["artifact_role"].tolist() == [
        "preprocessing_output",
        "preprocessing_output",
        "preprocessing_output",
    ]
    assert status["status"].tolist() == ["ready", "ready", "ready"]
    assert status["artifact_label"].tolist() == [
        "preprocessed event-station records",
        "waveform preprocessing manifest",
        "preprocessed trace metadata",
    ]
    assert status["resolved_path"].tolist() == status["path"].tolist()
    assert status["exists"].tolist() == [True, True, True]
    assert status["rows"].tolist() == [1, 1, 1]
    assert result.event_station_records.loc[0, "observed_raw_waveform"] == waveform_path
    assert result.event_station_records.loc[0, "observed_waveform"] == processed_path
    assert result.manifest.loc[0, "status"] == "written"
    assert result.trace_metadata.loc[0, "source_type"] == "observed"
    assert result.trace_metadata.loc[0, "input_file"] == str(waveform_path)
    assert result.trace_metadata.loc[0, "output_file"] == processed_path

    processed = read_waveform_file(processed_path)
    metadata = trace_metadata_table(processed)
    assert metadata.loc[0, "sampling_rate"] == pytest.approx(20.0)
    assert metadata.loc[0, "npts"] == pytest.approx(40)


def test_waveform_preprocessing_workflow_uses_configured_output_root(tmp_path) -> None:
    trace = _trace()
    trace.data = np.arange(20, dtype=float)
    trace.stats.sampling_rate = 20.0
    waveform_path = tmp_path / "raw" / "ci123.pkl"
    waveform_path.parent.mkdir()
    with waveform_path.open("wb") as handle:
        pickle.dump([trace], handle)
    records = pd.DataFrame(
        {
            "event_id": ["ci123"],
            "station": ["ABC"],
            "observed_waveform": [waveform_path],
        }
    )
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        "\n".join(
            [
                "project:",
                "  root_dir: .",
                "outputs:",
                "  preprocessed_waveforms: processed_from_config",
            ]
        ),
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)

    result = preprocess_waveform_files(
        records,
        source_columns={"observed": "observed_waveform"},
        preprocessing=WaveformPreprocessing(lowpass_hz=4.0),
        config=cfg,
    )

    assert result.event_station_path.parent == tmp_path / "processed_from_config" / "metadata"
    assert Path(result.event_station_records.loc[0, "observed_processed_waveform"]).is_file()


def test_trace_qc_uses_resampled_timing(tmp_path) -> None:
    trace = _trace()
    trace.data = np.sin(2.0 * np.pi * 0.1 * np.arange(100, dtype=float))
    waveform_path = tmp_path / "ci123.pkl"
    with waveform_path.open("wb") as handle:
        pickle.dump([trace], handle)
    event_stations = pd.DataFrame(
        {
            "event_id": ["ci123"],
            "station": ["ABC"],
            "start": ["2020-01-01T00:00:00Z"],
            "observed_pickle": [waveform_path],
        }
    )

    trace_qc = build_waveform_trace_qc_summary(
        event_stations,
        source="observed",
        waveform_path_col="observed_pickle",
        components=("Z",),
        passbands=[(1.0, 2.0)],
        preprocessing=WaveformPreprocessing(resample_hz=2.0),
        min_record_length_s=1.0,
        min_end_after_origin_s=1.0,
    )

    assert trace_qc.loc[0, "sample_interval_s"] == pytest.approx(0.5)
    assert trace_qc.loc[0, "sample_count"] == 200


def test_artifact_registry_records_missing_outputs(tmp_path) -> None:
    registry = ArtifactRegistry(tmp_path / "artifacts.jsonl")
    spec = ArtifactSpec(kind="metrics", name="long_table", extension=".csv")
    existing = tmp_path / "metrics.csv"
    existing.write_text("a,b\n1,2\n", encoding="utf-8")

    registry.record(existing, kind="metrics", name="long_table", spec=spec)
    registry.record(tmp_path / "missing.csv", kind="metrics", name="missing", status="planned")

    assert len(registry.records()) == 2
    assert [record.name for record in registry.missing()] == ["missing"]


def test_phasenet_adapter_parser_prefers_artifact_named_aliases() -> None:
    """PhaseNet normalization parser should expose concrete artifact roles."""

    parser = build_phasenet_arg_parser()
    help_text = " ".join(parser.format_help().split())
    assert "--phasenet-picks" in help_text
    assert "--phasenet-csv" in help_text
    assert "--phasenet-input-records" in help_text
    assert "--records-csv" in help_text
    assert "--arrival-pick-catalog-output" in help_text
    assert "--output" in help_text
    assert help_text.count("legacy alias") >= 3
    assert "PhaseNet picks CSV to normalize." in help_text
    assert "CSV containing PhaseNet input records." in help_text
    assert "Output arrival-pick catalog CSV or Parquet table." in help_text

    args = parser.parse_args(
        [
            "--phasenet-picks",
            "phasenet_picks.csv",
            "--phasenet-input-records",
            "phasenet_input_records.csv",
            "--arrival-pick-catalog-output",
            "arrival_pick_catalog.parquet",
        ]
    )
    legacy_args = parser.parse_args(
        [
            "--phasenet-csv",
            "legacy_picks.csv",
            "--records-csv",
            "legacy_records.csv",
            "--output",
            "legacy_catalog.csv",
        ]
    )

    assert args.phasenet_picks == "phasenet_picks.csv"
    assert args.phasenet_input_records == "phasenet_input_records.csv"
    assert args.arrival_pick_catalog_output == "arrival_pick_catalog.parquet"
    assert legacy_args.phasenet_picks == "legacy_picks.csv"
    assert legacy_args.phasenet_input_records == "legacy_records.csv"
    assert legacy_args.arrival_pick_catalog_output == "legacy_catalog.csv"
    assert not hasattr(args, "phasenet_csv")
    assert not hasattr(args, "records_csv")
    assert not hasattr(args, "output")


def test_phasenet_prepare_and_normalize(tmp_path) -> None:
    groups = [
        {
            "event_id": "ci123",
            "station": "ABC",
            "waveform_source": "observed",
            "relative_time_origin": "2020-01-01T00:00:00Z",
            "components": {
                "E": {"data": np.arange(10), "sampling_rate": 1.0, "starttime": "2020-01-01T00:00:00Z"},
                "N": {"data": np.arange(10), "sampling_rate": 1.0, "starttime": "2020-01-01T00:00:00Z"},
                "Z": {"data": np.arange(10), "sampling_rate": 1.0, "starttime": "2020-01-01T00:00:00Z"},
            },
        }
    ]
    records = prepare_phasenet_numpy_inputs(groups, tmp_path / "numpy")
    assert (tmp_path / "numpy" / records[0].file_name).exists()

    picks = pd.DataFrame(
        [
            {
                "file_name": records[0].file_name,
                "phase_type": "P",
                "phase_score": 0.9,
                "begin_time": "2020-01-01T00:00:00Z",
                "phase_time": "2020-01-01T00:00:12Z",
            },
            {
                "file_name": records[0].file_name,
                "phase_type": "S",
                "phase_score": 0.8,
                "begin_time": "2020-01-01T00:00:00Z",
                "phase_time": "2020-01-01T00:00:24Z",
            },
        ]
    )
    picks_path = tmp_path / "picks.csv"
    picks.to_csv(picks_path, index=False)
    catalog = normalize_phasenet_output(picks_path, records)

    assert list(catalog["phase"]) == ["P", "S"]
    assert list(catalog["pick_time_rel_s"]) == [12.0, 24.0]
    assert all(catalog["method"] == "phasenet")
    assert set(catalog["source"]) == {"observed"}


def test_metric_plan_completeness_from_inventory() -> None:
    inventory = pd.DataFrame({"event_id": ["ci123"], "station": ["ABC"], "component": ["Z"]})
    plan = MetricPlan(metrics=("C5", "C6"), passbands=((1.0, 3.0),), components=("Z",), models=("model_a",))
    expected = expected_metric_rows_from_inventory(inventory, plan)
    existing = expected.iloc[[0]].copy()

    missing, summary = compare_metric_plan_to_table(expected, existing)

    assert summary.expected == 2
    assert summary.present == 1
    assert summary.missing == 1
    assert missing.loc[0, "metric"] == "C6"
