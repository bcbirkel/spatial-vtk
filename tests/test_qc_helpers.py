from __future__ import annotations

import pandas as pd

from spatial_vtk.qc.build import (
    G_CM_PER_S2,
    MetricResidualLimit,
    MetricSanityQCSettings,
    MetricValueLimit,
    SpatialResidualOutlierSettings,
    apply_metric_sanity_rejections_to_metric_table,
    apply_metric_sanity_rejections_to_qc_inventory,
    build_metric_sanity_rejection_table,
    companion_rows_from_master,
    load_trace_inventory_lookup,
    summarize_metric_sanity_removals,
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


def test_metric_sanity_qc_rejects_hard_residual_and_spatial_outliers():
    metrics = pd.DataFrame(
        [
            _metric_row("STA1", value_obs=100.0, value_syn=110.0, log2_residual=0.1, lon=-118.000),
            _metric_row("STA2", value_obs=120.0, value_syn=100.0, log2_residual=0.2, lon=-118.001),
            _metric_row("STA3", value_obs=90.0, value_syn=100.0, log2_residual=-0.1, lon=-118.002),
            _metric_row("BADPGA", value_obs=G_CM_PER_S2 * 1.5, value_syn=100.0, log2_residual=0.3, lon=-118.003),
            _metric_row("BADRES", value_obs=20.0, value_syn=100.0, log2_residual=9.5, lon=-118.004),
            _metric_row("BADSPAT", value_obs=50.0, value_syn=100.0, log2_residual=5.0, lon=-118.005),
        ]
    )
    settings = MetricSanityQCSettings(
        value_limits=(MetricValueLimit(metric="PGA", max_abs=G_CM_PER_S2, sources=("observed",), reason="pga_above_1g"),),
        residual_limit=MetricResidualLimit(column="log2_residual", max_abs=8.0, reason="log2_residual_extreme"),
        spatial_residual=SpatialResidualOutlierSettings(
            enabled=True,
            column="log2_residual",
            radius_km=10.0,
            min_neighbors=3,
            z_threshold=8.0,
            min_abs_difference=4.0,
            mad_floor=0.25,
            reason="spatial_neighbor_residual_outlier",
        ),
    )

    rejections = build_metric_sanity_rejection_table(metrics, settings=settings)

    reasons_by_station = rejections.groupby("station")["qc_reason"].apply(set).to_dict()
    assert reasons_by_station["BADPGA"] == {"pga_above_1g"}
    assert "log2_residual_extreme" in reasons_by_station["BADRES"]
    assert "spatial_neighbor_residual_outlier" in reasons_by_station["BADSPAT"]

    updated_metrics = apply_metric_sanity_rejections_to_metric_table(metrics, rejections)
    failed = updated_metrics.set_index("station")
    assert failed.loc["BADPGA", "obs_qc_status"] == "fail"
    assert failed.loc["BADPGA", "syn_qc_status"] == "pass"
    assert failed.loc["BADRES", "comparison_qc_status"] == "fail"
    assert failed.loc["BADSPAT", "comparison_qc_status"] == "fail"
    assert pd.isna(failed.loc["BADPGA", "value_obs"])
    assert pd.isna(failed.loc["BADRES", "log2_residual"])

    qc_before = pd.concat(
        [
            metrics.assign(source="observed", qc_status="pass", qc_reason=""),
            metrics.assign(source="synthetic", qc_status="pass", qc_reason=""),
        ],
        ignore_index=True,
    )[
        ["source", "event_id", "station", "component", "passband", "metric_group", "metric", "period_s", "qc_status", "qc_reason"]
    ]
    qc_after = apply_metric_sanity_rejections_to_qc_inventory(qc_before, rejections)
    summary = summarize_metric_sanity_removals(qc_before, qc_after)

    failed_qc = qc_after.loc[qc_after["qc_status"].eq("fail")]
    assert set(failed_qc["station"]) >= {"BADPGA", "BADRES", "BADSPAT"}
    assert summary["newly_failed_rows"].sum() == len(failed_qc)


def _metric_row(station: str, *, value_obs: float, value_syn: float, log2_residual: float, lon: float) -> dict[str, object]:
    return {
        "event_id": "e1",
        "station": station,
        "component": "R",
        "passband": "1-2 sec",
        "metric_group": "amplitude",
        "metric": "PGA",
        "period_s": float("nan"),
        "model": "model_a",
        "value_obs": value_obs,
        "value_syn": value_syn,
        "log2_residual": log2_residual,
        "obs_qc_status": "pass",
        "obs_qc_reason": "",
        "syn_qc_status": "pass",
        "syn_qc_reason": "",
        "comparison_qc_status": "pass",
        "comparison_qc_reason": "",
        "sta_lat": 34.0,
        "sta_lon": lon,
    }
