from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from spatial_vtk.qc.build import inventory as qc_inventory_module
from spatial_vtk.qc.build.inventory import build_waveform_trace_qc_summary
from spatial_vtk.qc.build.workflow import build_metric_qc_summary


def test_waveform_trace_qc_resumes_from_checkpoint_without_reloading_waveforms(tmp_path: Path, monkeypatch, capsys) -> None:
    """Waveform QC checkpoints should skip completed source/event/station/component groups."""

    checkpoint_path = tmp_path / "qc_trace_summary.observed.checkpoint.csv"
    pd.DataFrame(
        {
            "source": ["observed"],
            "event_id": ["ci123"],
            "station": ["ABC"],
            "component": ["Z"],
            "passband": ["1-2 sec"],
            "metric_group": [""],
            "metric": [""],
            "period_s": [np.nan],
            "qc_status": ["pass"],
            "qc_reason": [""],
        }
    ).to_csv(checkpoint_path, index=False)
    event_stations = pd.DataFrame(
        {
            "event_id": ["ci123"],
            "station": ["ABC"],
            "start": ["2020-01-01T00:00:00Z"],
            "observed_processed_waveform": [tmp_path / "missing.pkl"],
        }
    )

    def fail_read(path):
        raise AssertionError(f"waveform should not be reloaded when checkpoint can resume: {path}")

    monkeypatch.setattr(qc_inventory_module, "read_waveform_file", fail_read)

    resumed = build_waveform_trace_qc_summary(
        event_stations,
        source="observed",
        waveform_path_col="observed_processed_waveform",
        components=("Z",),
        passbands=[(1.0, 2.0)],
        checkpoint_path=checkpoint_path,
        verbose=True,
        progress_interval=1,
        checkpoint_interval=1,
    )
    output = capsys.readouterr().out

    assert len(resumed) == 1
    assert "resuming with 1 completed component group" in output


def test_metric_qc_summary_resumes_from_checkpoint(tmp_path: Path) -> None:
    """Metric QC checkpoints should skip completed event-station records."""

    checkpoint_path = tmp_path / "qc_inventory.csv"
    pd.DataFrame(
        {
            "source": ["observed"],
            "event_id": ["E1"],
            "station": ["S1"],
            "component": ["Z"],
            "passband": ["1-2 sec"],
            "metric_group": ["amplitude"],
            "metric": ["PGA"],
            "period_s": [np.nan],
            "qc_status": ["pass"],
            "qc_reason": [""],
        }
    ).to_csv(checkpoint_path, index=False)
    event_stations = pd.DataFrame({"event_id": ["E1", "E2"], "station": ["S1", "S2"]})

    qc = build_metric_qc_summary(
        event_stations,
        metrics=("PGA",),
        components=("Z",),
        passbands=[(1.0, 2.0)],
        sources=("observed",),
        checkpoint_path=checkpoint_path,
        checkpoint_interval=1,
    )

    assert qc["event_id"].tolist() == ["E1", "E2"]
    assert qc["station"].tolist() == ["S1", "S2"]
