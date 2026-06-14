from __future__ import annotations

from pathlib import Path
import pickle

import numpy as np
import pandas as pd
import pytest

from spatial_vtk.io.tables import write_table
from spatial_vtk.qc.build import inventory as qc_inventory_module
from spatial_vtk.qc.build import workflow as qc_workflow_module
from spatial_vtk.qc.build.inventory import build_waveform_trace_qc_summary
from spatial_vtk.qc.build.workflow import build_metric_qc_summary, build_waveform_qc_summary


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
    assert "checkpoint already complete; returning cached rows" in output
    assert "record 1/1" not in output


def test_waveform_trace_qc_reports_only_pending_resume_records(tmp_path: Path, capsys) -> None:
    """Partial waveform QC resumes should iterate pending records, not all records."""

    checkpoint_path = tmp_path / "qc_trace_summary.observed.checkpoint.csv"
    pd.DataFrame(
        {
            "source": ["observed"],
            "event_id": ["E1"],
            "station": ["S1"],
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
            "event_id": ["E1", "E2"],
            "station": ["S1", "S2"],
            "start": ["2020-01-01T00:00:00Z", "2020-01-01T00:01:00Z"],
            "observed_processed_waveform": ["", ""],
        }
    )

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

    assert len(resumed) == 2
    assert "resuming with 1 completed component group (1/2 complete; 1 new group remaining)" in output
    assert "processing 1 new component group across 1 event-station record" in output
    assert "record 1/1" in output
    assert "record 1/2" not in output


def test_metric_qc_summary_resumes_from_checkpoint(tmp_path: Path, capsys) -> None:
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

    complete_checkpoint_path = tmp_path / "qc_inventory_complete.csv"
    pd.DataFrame(
        {
            "source": ["observed", "observed"],
            "event_id": ["E1", "E2"],
            "station": ["S1", "S2"],
            "component": ["Z", "Z"],
            "passband": ["1-2 sec", "1-2 sec"],
            "metric_group": ["amplitude", "amplitude"],
            "metric": ["PGA", "PGA"],
            "period_s": [np.nan, np.nan],
            "qc_status": ["pass", "pass"],
            "qc_reason": ["", ""],
        }
    ).to_csv(complete_checkpoint_path, index=False)

    complete_qc = build_metric_qc_summary(
        event_stations,
        metrics=("PGA",),
        components=("Z",),
        passbands=[(1.0, 2.0)],
        sources=("observed",),
        checkpoint_path=complete_checkpoint_path,
        checkpoint_interval=1,
        verbose=True,
        progress_interval=1,
    )
    output = capsys.readouterr().out

    assert len(complete_qc) == 2
    assert "checkpoint already complete; returning cached rows" in output
    assert "record 1/2" not in output


def test_metric_qc_summary_disk_resume_appends_without_loading_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disk-backed metric QC resumes should scan keys instead of loading full rows."""

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

    def fail_full_checkpoint_load(path):
        raise AssertionError(f"checkpoint should not be fully loaded: {path}")

    monkeypatch.setattr(qc_workflow_module, "_load_qc_checkpoint", fail_full_checkpoint_load)

    result = build_metric_qc_summary(
        event_stations,
        metrics=("PGA",),
        components=("Z",),
        passbands=[(1.0, 2.0)],
        sources=("observed",),
        checkpoint_path=checkpoint_path,
        checkpoint_interval=1,
        return_result=False,
    )

    checkpoint = pd.read_csv(checkpoint_path)
    assert result.empty
    assert checkpoint["event_id"].tolist() == ["E1", "E2"]
    assert checkpoint["station"].tolist() == ["S1", "S2"]


def test_waveform_qc_summary_combines_source_checkpoints_without_returning_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Slurm trace QC should combine source checkpoints without retaining both sources."""

    event_stations = pd.DataFrame(
        {
            "event_id": ["E1"],
            "station": ["S1"],
            "observed_processed_waveform": [tmp_path / "obs.pkl"],
            "synthetic_processed_waveform": [tmp_path / "syn.pkl"],
        }
    )
    checkpoint_path = tmp_path / "qc_trace_summary.csv"

    def fake_build_waveform_trace_qc_summary(records, *, source, checkpoint_path=None, **kwargs):
        rows = pd.DataFrame(
            {
                "source": [source],
                "event_id": ["E1"],
                "station": ["S1"],
                "component": ["Z"],
                "passband": ["1-2 sec"],
                "qc_status": ["pass"],
            }
        )
        rows.to_csv(checkpoint_path, index=False)
        return rows

    monkeypatch.setattr(qc_workflow_module, "build_waveform_trace_qc_summary", fake_build_waveform_trace_qc_summary)

    result = build_waveform_qc_summary(
        event_stations,
        sources=("observed", "synthetic"),
        components=("Z",),
        passbands=[(1.0, 2.0)],
        checkpoint_path=checkpoint_path,
        return_result=False,
    )

    combined = pd.read_csv(checkpoint_path)
    assert result.empty
    assert combined["source"].tolist() == ["observed", "synthetic"]
    assert (tmp_path / "qc_trace_summary.observed.checkpoint.csv").exists()
    assert (tmp_path / "qc_trace_summary.synthetic.checkpoint.csv").exists()


def test_waveform_trace_qc_reports_missing_component_without_window_failures(
    tmp_path: Path,
) -> None:
    """Selection failures should not masquerade as signal/noise QC failures."""

    waveform_path = tmp_path / "observed.pkl"
    with waveform_path.open("wb") as handle:
        pickle.dump(
            [
                {
                    "data": np.ones(100, dtype=float),
                    "stats": {
                        "network": "CI",
                        "station": "ABC",
                        "channel": "HNZ",
                        "sampling_rate": 1.0,
                        "starttime": "2020-01-01T00:00:00Z",
                    },
                }
            ],
            handle,
        )
    event_stations = pd.DataFrame(
        {
            "event_id": ["ci123"],
            "station": ["ABC"],
            "start": ["2020-01-01T00:00:00Z"],
            "observed_processed_waveform": [waveform_path],
        }
    )

    qc = build_waveform_trace_qc_summary(
        event_stations,
        source="observed",
        waveform_path_col="observed_processed_waveform",
        components=("R",),
        passbands=[(1.0, 2.0)],
    )

    assert qc.loc[0, "qc_status"] == "fail"
    assert qc.loc[0, "qc_reason"] == "missing_component"
    assert "Available traces include" in qc.loc[0, "load_message"]


def test_waveform_trace_qc_reuses_one_asdf_station_read_for_components(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ASDF QC should read one station stream once and reuse it for components."""

    import spatial_vtk.io.synthetic_formats as synthetic_formats

    calls = []

    class FakeSyntheticReader:
        def __init__(self, info):
            self.info = info

        def read(self, request):
            calls.append((self.info.root, request.station, request.component))
            return [
                {
                    "data": np.ones(120, dtype=float),
                    "stats": {
                        "station": "ABC",
                        "channel": f"BH{component}",
                        "sampling_rate": 1.0,
                        "starttime": "2020-01-01T00:00:00Z",
                    },
                }
                for component in ("R", "T", "Z")
            ]

    monkeypatch.setattr(synthetic_formats, "synthetic_reader_for", FakeSyntheticReader)
    event_stations = pd.DataFrame(
        {
            "event_id": ["ci123"],
            "station": ["ABC"],
            "start": ["2020-01-01T00:00:00Z"],
            "synthetic_processed_waveform": [tmp_path / "ci123.asdf"],
        }
    )

    qc = build_waveform_trace_qc_summary(
        event_stations,
        source="synthetic",
        waveform_path_col="synthetic_processed_waveform",
        components=("R", "T", "Z"),
        passbands=[(1.0, 2.0)],
        preprocessing=qc_inventory_module.WaveformPreprocessing(),
    )

    assert qc["component"].tolist() == ["R", "T", "Z"]
    assert calls == [(str(tmp_path / "ci123.asdf"), "ABC", None)]


def test_write_table_keeps_existing_csv_when_replacement_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Atomic table writes should not leave checkpoints empty on failure."""

    path = tmp_path / "checkpoint.csv"
    write_table(pd.DataFrame({"event_id": ["E1"]}), path)
    original = path.read_text(encoding="utf-8")

    def fail_to_csv(
        self: pd.DataFrame,
        output_path: str | Path,
        *args: object,
        **kwargs: object,
    ) -> None:
        Path(output_path).write_text("partial\n", encoding="utf-8")
        raise RuntimeError("simulated write failure")

    monkeypatch.setattr(pd.DataFrame, "to_csv", fail_to_csv)

    with pytest.raises(RuntimeError, match="simulated write failure"):
        write_table(pd.DataFrame({"event_id": ["E2"]}), path)

    assert path.read_text(encoding="utf-8") == original
    assert not list(tmp_path.glob(".checkpoint.csv.*.tmp"))
