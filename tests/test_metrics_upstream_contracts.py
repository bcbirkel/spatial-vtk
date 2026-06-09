from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spatial_vtk.config.metrics import metric_settings_summary, metrics_settings_from_config
from spatial_vtk.config.runtime import SpatialVTKConfig
from spatial_vtk.io.metric_inputs import (
    comparison_qc_passed,
    metric_qc_lookup,
    normalize_metric_qc_table,
    normalize_metric_waveform_inventory,
)
from spatial_vtk.io.plans import expected_metric_rows_from_inventory, metric_plan_from_config
from spatial_vtk.qc.build.spectral import (
    qc_fas_periods,
    spectral_relative_amplitude_mask,
    spectral_valid_period_bounds,
)
from spatial_vtk.qc.build.workflow import build_metric_qc_summary


def test_metric_config_supports_multiple_transforms_and_spectral_settings() -> None:
    config = SpatialVTKConfig.empty(
        root_dir=".",
    )
    data = {
        "metrics": {
            "metrics": ["PSA", "PGA"],
            "components": ["z", "r"],
            "passbands": [[1, 2], "2-4 sec"],
            "transforms": ["residual", "log2_residual", "anderson", "olsen_mayhew"],
            "output_mode": "full",
            "synthetic_max_frequency_hz": 1.0,
            "spectral": {
                "periods_s": [1.0, 2.0, 10.0],
                "relative_amplitude_threshold": 0.2,
                "min_cycles_in_record": 4,
            },
        }
    }
    config = SpatialVTKConfig(config.config_path, config.root_dir, data)

    settings = metrics_settings_from_config(config)

    assert settings.groups == ("spectral", "amplitude")
    assert settings.metrics == ("PSA", "PGA")
    assert settings.components == ("Z", "R")
    assert settings.passbands == ((1.0, 2.0), "2-4 sec")
    assert settings.transforms == ("residual", "log2_residual", "anderson_2004_gof", "olsen_mayhew_gof")
    assert settings.synthetic_max_frequency_hz == 1.0
    assert settings.spectral.periods_s == (1.0, 2.0, 10.0)
    assert settings.spectral.relative_amplitude_threshold == 0.2
    assert settings.spectral.min_cycles_in_record == 4.0
    summary = metric_settings_summary(settings)
    assert list(summary.columns) == ["Setting", "Value"]
    assert "Spectral periods" in set(summary["Setting"])
    assert "1 s, 2 s, 10 s" in set(summary["Value"])


def test_metric_config_uses_either_groups_or_metrics() -> None:
    config = SpatialVTKConfig.empty(root_dir=".")
    group_config = SpatialVTKConfig(
        config.config_path,
        config.root_dir,
        {"metrics": {"groups": ["amplitude", "cross_correlation"]}},
    )
    settings = metrics_settings_from_config(group_config)
    assert settings.groups == ("amplitude", "cross_correlation")
    assert settings.metrics == ("PGA", "PGV", "PGD", "original_cc", "delay_corrected_cc")

    all_config = SpatialVTKConfig(config.config_path, config.root_dir, {"metrics": {"metrics": ["all"]}})
    all_settings = metrics_settings_from_config(all_config)
    assert "PGA" in all_settings.metrics
    assert "delay_corrected_cc" in all_settings.metrics

    invalid_config = SpatialVTKConfig(
        config.config_path,
        config.root_dir,
        {"metrics": {"groups": ["amplitude"], "metrics": ["PGA"]}},
    )
    with pytest.raises(ValueError, match="either metrics.groups or metrics.metrics"):
        metrics_settings_from_config(invalid_config)


def test_metric_plan_keeps_requested_transform_columns_and_period_rows() -> None:
    config = SpatialVTKConfig.empty(root_dir=".")
    data = {
        "metrics": {
            "metrics": ["PSA"],
            "models": ["m1"],
            "components": ["Z"],
            "transforms": ["residual", "ln_residual", "anderson_2004_gof"],
            "spectral": {"periods_s": [1.0, 2.0]},
        }
    }
    config = SpatialVTKConfig(config.config_path, config.root_dir, data)
    plan = metric_plan_from_config(config)
    inventory = pd.DataFrame({"event_id": ["e1"], "station": ["abc"], "component": ["z"]})

    rows = expected_metric_rows_from_inventory(inventory, plan)

    assert len(rows) == 2
    assert set(rows["period_s"]) == {1.0, 2.0}
    assert rows["requested_transforms"].iloc[0] == "residual,ln_residual,anderson_2004_gof"
    for column in ("residual", "ln_residual", "anderson_2004_gof"):
        assert column in rows.columns


def test_metric_input_and_qc_tables_are_side_specific() -> None:
    raw_inventory = pd.DataFrame(
        {
            "role": ["synthetic"],
            "event": ["e1"],
            "Station": ["abc"],
            "component": ["z"],
            "model_alias": ["m1"],
            "path": ["syn.npz"],
        }
    )
    inventory = normalize_metric_waveform_inventory(raw_inventory, synthetic_max_frequency_hz=1.25)
    assert inventory.loc[0, "source"] == "synthetic"
    assert inventory.loc[0, "synthetic_max_frequency_hz"] == 1.25

    qc = normalize_metric_qc_table(
        pd.DataFrame(
            {
                "source": ["observed", "synthetic"],
                "event_id": ["e1", "e1"],
                "station": ["abc", "abc"],
                "component": ["z", "z"],
                "metric": ["PGA", "PGA"],
                "qc_status": ["pass", "fail"],
                "qc_reason": ["", "above_max_frequency"],
            }
        )
    )
    lookup = metric_qc_lookup(qc)
    obs = lookup[("observed", "e1", "ABC", "Z", "", "PGA", "")]
    syn = lookup[("synthetic", "e1", "ABC", "Z", "", "PGA", "")]
    assert not comparison_qc_passed(obs, syn)


def test_spectral_qc_uses_relative_support_and_synthetic_max_frequency() -> None:
    periods = np.array([0.25, 1.0, 10.0])
    amplitudes = np.array([1.0, 10.0, 2.0])
    mask = spectral_relative_amplitude_mask(periods, amplitudes, threshold=0.25)
    assert mask.tolist() == [False, True, False]
    assert spectral_valid_period_bounds(periods, mask) == (1.0, 1.0)

    trace = np.sin(np.linspace(0.0, 20.0 * np.pi, 400))
    qc = qc_fas_periods(
        trace,
        dt=0.1,
        periods_s=periods,
        threshold=0.0,
        min_cycles_in_record=3.0,
        synthetic_max_frequency_hz=0.5,
        source="synthetic",
        disable_relative_amplitude_qc=True,
    )
    status_by_period = dict(zip(qc["period_s"], qc["qc_status"], strict=False))
    assert status_by_period[0.25] == "fail"
    assert status_by_period[10.0] == "pass"


def test_metric_qc_synthetic_max_frequency_boundary_is_inclusive() -> None:
    records = pd.DataFrame({"event_id": ["e1"], "station": ["abc"]})

    qc = build_metric_qc_summary(
        records,
        metrics=["PSA"],
        components=["Z"],
        passbands=[[1.0, 2.0]],
        spectral_periods_s=[0.5, 1.0, 2.0],
        sources=["synthetic"],
        synthetic_max_frequency_hz=1.0,
    )
    status_by_period = {
        float(row.period_s): (row.qc_status, row.qc_reason)
        for row in qc.itertuples(index=False)
    }

    assert status_by_period[0.5] == ("fail", "period_below_synthetic_min_period")
    assert status_by_period[1.0] == ("pass", "")
    assert status_by_period[2.0] == ("pass", "")
