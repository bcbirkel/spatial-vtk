from __future__ import annotations

import pandas as pd

from spatial_vtk.qc.build import (
    companion_rows_from_master,
    load_trace_inventory_lookup,
    trace_passband_is_accepted,
)
from spatial_vtk.qc.review import filter_trace_summary, queue_rows_from_filtered_trace_df
from spatial_vtk.qc.summary import classify_station_family, global_trace_reject_reasons, reject_passband


def test_trace_inventory_lookup_and_filtering(tmp_path):
    csv_path = tmp_path / "trace_inventory.csv"
    pd.DataFrame(
        {
            "observed_variant": ["nonrotated", "nonrotated"],
            "event_id": ["e1", "e1"],
            "station": ["ABC", "1234"],
            "component": ["N", "N"],
            "reject_1_3s": ["false", "true"],
            "reject_reason_1_3s": ["", "low_snr"],
        }
    ).to_csv(csv_path, index=False)

    lookup = load_trace_inventory_lookup(csv_path)
    assert trace_passband_is_accepted(
        lookup,
        observed_variant="nonrotated",
        event_id="e1",
        station="ABC",
        component="N",
        passband_label="1-3s",
    )
    assert not trace_passband_is_accepted(
        lookup,
        observed_variant="nonrotated",
        event_id="e1",
        station="1234",
        component="N",
        passband_label="1-3s",
    )


def test_companion_rows_and_summary_rules():
    rows = [
        {
            "event_id": "e1",
            "observed_variant": "nonrotated",
            "station": "ABC",
            "component": "N",
            "distance_km": 5.0,
            "reject_1_3s": False,
            "mean_abs_1_3s": 2.0,
        },
        {
            "event_id": "e1",
            "observed_variant": "nonrotated",
            "station": "1234",
            "component": "N",
            "distance_km": 7.0,
            "reject_1_3s": True,
            "reject_reason_1_3s": "low_snr",
        },
    ]
    companion = companion_rows_from_master(rows, inventory_bands=[("1-3s", 1.0, 3.0)])
    assert companion[0]["accepted_trace_count"] == 1
    assert companion[0]["rejected_trace_count"] == 1

    assert classify_station_family("CE", "1234") == "strong_motion"
    rejected, reasons = global_trace_reject_reasons(
        record_length_s=20.0,
        end_rel_s=100.0,
        onset_reasons=[],
        min_end_after_origin_s=60.0,
        min_record_length_s=80.0,
    )
    assert rejected
    assert "record_too_short" in reasons

    rejected, reasons = reject_passband(
        global_reasons=[],
        snr_rms=1.0,
        snr_threshold=3.0,
        noise_window_valid=True,
        signal_window_valid=True,
        pre_origin_window_valid=False,
        pre_origin_signal_ratio=0.0,
        pre_origin_signal_ratio_threshold=0.5,
        origin_window_valid=False,
        origin_signal_ratio=0.0,
    )
    assert rejected
    assert reasons == ["low_snr"]


def test_review_queue_helpers():
    df = pd.DataFrame(
        {
            "event_id": ["e1", "e1", "e2"],
            "station": ["ABC", "ABC", "XYZ"],
            "component": ["N", "E", "N"],
            "reject_reason": ["low_snr", "", "low_snr"],
        }
    )
    filtered = filter_trace_summary(df, reject_reason_contains="low")
    assert len(filtered) == 2
    queue = queue_rows_from_filtered_trace_df(filtered)
    assert queue[0]["status"] == "pending"
    assert {row["event_id"] for row in queue} == {"e1", "e2"}
