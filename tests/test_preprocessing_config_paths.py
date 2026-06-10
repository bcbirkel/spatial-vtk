"""Tests for config-derived waveform preprocessing inputs."""

from __future__ import annotations

from pathlib import Path
import pickle

import pandas as pd
import pytest

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


def test_configured_missing_observed_paths_stop_before_partial_writes(tmp_path: Path, monkeypatch) -> None:
    """If observed is configured but unmatched, do not preprocess only synthetic."""

    synthetic_root = tmp_path / "raw" / "synthetic" / "model_a"
    synthetic_root.mkdir(parents=True)
    (synthetic_root / "E01.pkl").write_bytes(b"synthetic")
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        "\n".join(
            [
                "project:",
                "  root_dir: .",
                "paths:",
                "  observed_template: raw/observed/{event_id}.pkl",
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
    records = pd.DataFrame({"event_id": ["E01"], "station": ["STA01"]})

    def fail_if_called(*args, **kwargs):
        raise AssertionError("preprocessing should not run when a configured source is missing")

    monkeypatch.setattr(preprocessing_module, "_preprocess_one_file", fail_if_called)

    with pytest.raises(ValueError, match="Observed waveform input is configured"):
        preprocess_waveform_files(records, config=cfg)

    assert not (tmp_path / "processed").exists()


def test_existing_processed_waveforms_are_cached_unless_overwrite(tmp_path: Path, monkeypatch) -> None:
    """Existing processed waveform files should be reused by default."""

    raw_path = tmp_path / "raw" / "E01.pkl"
    raw_path.parent.mkdir()
    raw_path.write_bytes(b"raw")
    output_root = tmp_path / "processed"
    cached_path = output_root / "observed" / "E01" / "E01.pkl"
    cached_path.parent.mkdir(parents=True)
    with cached_path.open("wb") as handle:
        pickle.dump(["cached"], handle)
    records = pd.DataFrame({"event_id": ["E01"], "station": ["STA01"], "observed_waveform": [raw_path]})

    monkeypatch.setattr(preprocessing_module, "read_waveform_file", lambda path: ["cached"])
    monkeypatch.setattr(
        preprocessing_module,
        "trace_metadata_table",
        lambda stream, source=None, event_id=None: pd.DataFrame({"event_id": [event_id], "station": ["STA01"]}),
    )

    def fail_write(*args, **kwargs):
        raise AssertionError("cached waveform should not be overwritten")

    monkeypatch.setattr(preprocessing_module, "_write_waveform_file", fail_write)

    result = preprocess_waveform_files(records, output_root=output_root)

    assert result.manifest.loc[0, "status"] == "cached"
    assert result.event_station_records.loc[0, "observed_processed_waveform"] == str(cached_path)

    writes: list[Path] = []
    monkeypatch.setattr(preprocessing_module, "preprocess_stream", lambda stream, settings: stream)
    monkeypatch.setattr(preprocessing_module, "_write_waveform_file", lambda stream, output_path, input_path: writes.append(output_path))

    overwritten = preprocess_waveform_files(records, output_root=output_root, overwrite=True)

    assert overwritten.manifest.loc[0, "status"] == "written"
    assert writes == [cached_path]
