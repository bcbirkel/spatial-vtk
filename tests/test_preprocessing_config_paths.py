"""Tests for config-derived waveform preprocessing inputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from spatial_vtk.config import SpatialVTKConfig
from spatial_vtk.io import preprocessing as preprocessing_module
from spatial_vtk.io.preprocessing import preprocess_waveform_files


def test_preprocess_waveform_files_uses_configured_waveform_paths(tmp_path: Path, monkeypatch) -> None:
    """Configured waveform roots/templates should populate missing path columns."""

    observed_root = tmp_path / "raw" / "observed"
    synthetic_root = tmp_path / "raw" / "synthetic" / "model_a"
    observed_root.mkdir(parents=True)
    synthetic_root.mkdir(parents=True)
    observed_path = observed_root / "E01.pkl"
    synthetic_path = synthetic_root / "E01.pkl"
    observed_path.write_bytes(b"observed")
    synthetic_path.write_bytes(b"synthetic")
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        "\n".join(
            [
                "project:",
                "  root_dir: .",
                "paths:",
                "  observed_root: raw/observed/{event_id}.pkl",
                "  synthetic_template: raw/synthetic/{model}/{event_id}.pkl",
                "outputs:",
                "  preprocessed_waveforms: processed",
                "metrics:",
                "  models: [model_a]",
            ]
        ),
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    records = pd.DataFrame({"event_title": ["E01"], "station": ["STA01"]})

    def fake_preprocess_one_file(input_path, output_path, *, source, event_id, settings, overwrite):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"processed")
        return (
            {
                "event_id": event_id,
                "source": source,
                "input_file": str(input_path),
                "output_file": str(output_path),
                "status": "written",
                "message": "",
                "processing": "none",
                "lowpass_hz": settings.lowpass_hz,
                "highpass_hz": settings.highpass_hz,
                "bandpass_low_hz": settings.bandpass_low_hz,
                "bandpass_high_hz": settings.bandpass_high_hz,
                "resample_hz": settings.resample_hz,
                "filter_order": settings.filter_order,
                "trace_count": 0,
            },
            pd.DataFrame(),
        )

    monkeypatch.setattr(preprocessing_module, "_preprocess_one_file", fake_preprocess_one_file)

    result = preprocess_waveform_files(records, config=cfg)

    assert set(result.manifest["source"]) == {"observed", "synthetic"}
    assert set(result.manifest["input_file"]) == {str(observed_path), str(synthetic_path)}
    assert result.event_station_records.loc[0, "event_id"] == "E01"
    assert "event_title" not in result.event_station_records.columns
    assert result.event_station_records.loc[0, "observed_raw_waveform"] == str(observed_path)
    assert result.event_station_records.loc[0, "synthetic_raw_waveform"] == str(synthetic_path)
    assert Path(result.event_station_records.loc[0, "observed_processed_waveform"]).is_file()
    assert Path(result.event_station_records.loc[0, "synthetic_processed_waveform"]).is_file()


def test_configured_observed_template_avoids_json_sidecars(tmp_path: Path, monkeypatch) -> None:
    """Explicit waveform templates should win over mixed-format root scans."""

    observed_root = tmp_path / "raw" / "observed"
    observed_root.mkdir(parents=True)
    observed_path = observed_root / "E01.pkl"
    sidecar_path = observed_root / "E01.json"
    observed_path.write_bytes(b"observed")
    sidecar_path.write_text('{"event_id": "E01"}', encoding="utf-8")
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        "\n".join(
            [
                "project:",
                "  root_dir: .",
                "paths:",
                "  observed_root: raw/observed",
                "  observed_template: raw/observed/{event_id}.pkl",
                "outputs:",
                "  preprocessed_waveforms: processed",
            ]
        ),
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    records = pd.DataFrame({"event_id": ["E01"], "station": ["STA01"]})

    def fake_preprocess_one_file(input_path, output_path, *, source, event_id, settings, overwrite):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"processed")
        return (
            {
                "event_id": event_id,
                "source": source,
                "input_file": str(input_path),
                "output_file": str(output_path),
                "status": "written",
                "message": "",
                "processing": "none",
                "lowpass_hz": settings.lowpass_hz,
                "highpass_hz": settings.highpass_hz,
                "bandpass_low_hz": settings.bandpass_low_hz,
                "bandpass_high_hz": settings.bandpass_high_hz,
                "resample_hz": settings.resample_hz,
                "filter_order": settings.filter_order,
                "trace_count": 0,
            },
            pd.DataFrame(),
        )

    monkeypatch.setattr(preprocessing_module, "_preprocess_one_file", fake_preprocess_one_file)

    result = preprocess_waveform_files(records, config=cfg)

    assert result.manifest["input_file"].tolist() == [str(observed_path)]
    assert result.event_station_records.loc[0, "observed_raw_waveform"] == str(observed_path)
