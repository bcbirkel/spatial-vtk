"""Tests for config-derived waveform preprocessing inputs."""

from __future__ import annotations

from pathlib import Path
import pickle
from types import SimpleNamespace

import pandas as pd
import pytest

from spatial_vtk.config import SpatialVTKConfig, clear_active_config
from spatial_vtk.config.runtime import SVTK_CLI_CONFIG_ENV, SVTK_CONFIG_ENV
from spatial_vtk.io import workflows as io_workflows
from spatial_vtk.io import preprocessing as preprocessing_module
from spatial_vtk.io.workflows import (
    build_record_coverage_from_config,
    load_configured_input_paths,
    load_configured_input_tables,
    prepare_metadata_tables_from_config,
    preprocess_waveforms_from_config,
)
from spatial_vtk.io.preprocessing import preprocessed_waveform_metadata_paths, preprocess_waveform_files


@pytest.fixture(autouse=True)
def _isolate_config_discovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Keep preprocessing tests independent of user-level config state."""

    clear_active_config()
    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    monkeypatch.setenv(SVTK_CLI_CONFIG_ENV, str(tmp_path / "missing-cli-config.json"))
    yield
    clear_active_config()


def test_preprocessed_waveform_metadata_paths_match_preprocessing_defaults(tmp_path: Path) -> None:
    """Notebook readiness checks should use the same metadata paths as preprocessing."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        "\n".join(
            [
                "project:",
                "  root_dir: .",
                "outputs:",
                "  preprocessed_waveforms: processed",
            ]
        ),
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)

    paths = preprocessed_waveform_metadata_paths(config=cfg, create_parent=True)

    assert paths.root == tmp_path / "processed"
    assert paths.metadata_dir == tmp_path / "processed" / "metadata"
    assert paths.metadata_dir.is_dir()
    assert paths.event_station_path == paths.metadata_dir / "event_station_records_preprocessed.csv"
    assert paths.manifest_path == paths.metadata_dir / "waveform_preprocessing_manifest.csv"
    assert paths.trace_metadata_path == paths.metadata_dir / "trace_metadata_preprocessed.csv"
    assert paths.as_dict()["preprocessed_manifest_path"] == paths.manifest_path


def test_preprocess_waveforms_from_config_uses_registered_event_station_table(tmp_path: Path, monkeypatch) -> None:
    """Notebook/package workflow should resolve preprocessing inputs from config."""

    tables = tmp_path / "outputs" / "tables"
    tables.mkdir(parents=True)
    records = tables / "event_station_records.csv"
    records.write_text("event_id,station,observed_waveform\nE1,STA1,obs.mseed\n", encoding="utf-8")
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
  preprocessed_waveforms: outputs/preprocessed_waveforms
""",
        encoding="utf-8",
    )
    seen = {}

    def fake_preprocess_waveform_files(event_station_records, output_root=None, **kwargs):
        seen["event_station_records"] = Path(event_station_records)
        seen["output_root"] = output_root
        seen["overwrite"] = kwargs["overwrite"]
        seen["continue_on_error"] = kwargs["continue_on_error"]
        seen["verbose"] = kwargs["verbose"]
        return SimpleNamespace(
            event_station_path=tmp_path / "outputs" / "preprocessed_waveforms" / "metadata" / "event_station_records_preprocessed.csv",
            manifest_path=tmp_path / "outputs" / "preprocessed_waveforms" / "metadata" / "waveform_preprocessing_manifest.csv",
            trace_metadata_path=tmp_path / "outputs" / "preprocessed_waveforms" / "metadata" / "trace_metadata_preprocessed.csv",
            manifest=pd.DataFrame({"event_id": ["E1"]}),
            trace_metadata=pd.DataFrame({"event_id": ["E1", "E1"]}),
            event_station_records=pd.DataFrame({"event_id": ["E1"]}),
        )

    monkeypatch.setattr(io_workflows, "preprocess_waveform_files", fake_preprocess_waveform_files)

    result = preprocess_waveforms_from_config(
        config_path=config_path,
        overwrite=True,
        continue_on_error=True,
        verbose=False,
    )

    assert seen == {
        "event_station_records": records,
        "output_root": None,
        "overwrite": True,
        "continue_on_error": True,
        "verbose": False,
    }
    assert result["manifest_rows"] == 1
    assert result["trace_metadata_rows"] == 2
    assert result["event_station_rows"] == 1
    assert result["preprocessed_event_station_records_path"] == result["event_station_records"]
    assert result["preprocessed_manifest_path"] == result["manifest"]
    assert result["preprocessing_manifest_path"] == result["manifest"]
    assert result["preprocessed_trace_metadata_path"] == result["trace_metadata"]


def test_prepare_metadata_tables_from_config_writes_registered_outputs(tmp_path: Path, monkeypatch) -> None:
    """Step 1 metadata workflow should write the standard configured outputs."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
""",
        encoding="utf-8",
    )
    stations = pd.DataFrame({"station": ["STA1"], "lat": [34.0], "lon": [-118.0]})
    events = pd.DataFrame({"event_id": ["E1"], "start": ["2020-01-01T00:00:00Z"]})
    event_stations = pd.DataFrame({"event_id": ["E1"], "station": ["STA1"]})
    seen: dict[str, object] = {}

    def fake_prepare_event_station_table(*, station_metadata=None, event_metadata=None, **kwargs):
        seen["station_rows"] = len(station_metadata)
        seen["event_rows"] = len(event_metadata)
        return event_stations

    monkeypatch.setattr(io_workflows, "prepare_station_metadata", lambda: stations)
    monkeypatch.setattr(io_workflows, "prepare_event_metadata", lambda: events)
    monkeypatch.setattr(io_workflows, "prepare_event_station_table", fake_prepare_event_station_table)

    result = prepare_metadata_tables_from_config(config_path=config_path, overwrite=True)

    assert seen == {"station_rows": 1, "event_rows": 1}
    assert result["station_rows"] == 1
    assert result["event_rows"] == 1
    assert result["event_station_rows"] == 1
    assert result["reused"] is False
    assert Path(result["prepared_stations_path"]).exists()
    assert Path(result["prepared_events_path"]).exists()
    assert Path(result["event_station_records_path"]).exists()


def test_load_configured_input_tables_reads_named_config_paths(tmp_path: Path) -> None:
    """Notebook helpers should load configured input tables with descriptive labels."""

    inputs = tmp_path / "inputs"
    inputs.mkdir()
    metric_snapshot = inputs / "metric_snapshot.csv"
    site_metadata = inputs / "site_metadata.csv"
    pd.DataFrame({"metric": ["PGA"], "station": ["STA1"]}).to_csv(metric_snapshot, index=False)
    pd.DataFrame({"station": ["STA1"], "Vs30": [760.0]}).to_csv(site_metadata, index=False)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
paths:
  metric_figure_snapshot: inputs/metric_snapshot.csv
  site_metadata: inputs/site_metadata.csv
""",
        encoding="utf-8",
    )

    tables = load_configured_input_tables(
        {
            "metrics": "paths.metric_figure_snapshot",
            "site_metadata": "paths.site_metadata",
        },
        config_path=config_path,
    )

    assert list(tables) == ["metrics", "site_metadata"]
    assert tables["metrics"]["metric"].tolist() == ["PGA"]
    assert tables["site_metadata"]["Vs30"].tolist() == [760.0]


def test_load_configured_input_paths_resolves_named_config_paths(tmp_path: Path) -> None:
    """Notebook helpers should resolve configured non-table inputs with labels."""

    inputs = tmp_path / "inputs"
    inputs.mkdir()
    geojson = inputs / "regions.geojson"
    geojson.write_text('{"type": "FeatureCollection", "features": []}', encoding="utf-8")
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
paths:
  region_geojson: inputs/regions.geojson
  optional_geojson:
""",
        encoding="utf-8",
    )

    paths = load_configured_input_paths(
        {"region_geojson": "paths.region_geojson"},
        config_path=config_path,
    )
    optional = load_configured_input_paths(
        ["paths.optional_geojson"],
        config_path=config_path,
        must_exist=False,
    )

    assert paths == {"region_geojson": geojson.resolve()}
    assert optional == {"optional_geojson": None}


def test_load_configured_input_tables_rejects_ambiguous_arguments(tmp_path: Path) -> None:
    """Callers should not mix active config objects with config file arguments."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text("project:\n  root_dir: .\n", encoding="utf-8")
    cfg = SpatialVTKConfig.from_file(config_path)

    with pytest.raises(ValueError, match="either cfg or config_path"):
        load_configured_input_tables({"demo": "paths.demo"}, cfg=cfg, config_path=config_path)
    with pytest.raises(TypeError, match="not a string"):
        load_configured_input_tables("paths.demo", cfg=cfg)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="dotted config path"):
        load_configured_input_tables({"demo": "demo"}, cfg=cfg)

    with pytest.raises(ValueError, match="either cfg or config_path"):
        load_configured_input_paths({"demo": "paths.demo"}, cfg=cfg, config_path=config_path)
    with pytest.raises(TypeError, match="not a string"):
        load_configured_input_paths("paths.demo", cfg=cfg)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="dotted config path"):
        load_configured_input_paths({"demo": "demo"}, cfg=cfg)


def test_build_record_coverage_from_config_uses_preprocessed_metadata(tmp_path: Path) -> None:
    """Record coverage workflow should read preprocessed metadata and write the registered output."""

    preprocessing_metadata = tmp_path / "outputs" / "preprocessed_waveforms" / "metadata"
    preprocessing_metadata.mkdir(parents=True)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
  preprocessed_waveforms: outputs/preprocessed_waveforms
""",
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "event_id": ["E1"],
            "station": ["STA1"],
            "start": ["2020-01-01T00:00:00Z"],
            "distance_km": [12.5],
        }
    ).to_csv(preprocessing_metadata / "event_station_records_preprocessed.csv", index=False)
    pd.DataFrame(
        {
            "event_id": ["E1", "E1"],
            "station": ["STA1", "STA1"],
            "source_type": ["observed", "synthetic"],
            "starttime": ["2019-12-31T23:59:55Z", "2020-01-01T00:00:00Z"],
            "endtime": ["2020-01-01T00:01:05Z", "2020-01-01T00:01:00Z"],
        }
    ).to_csv(preprocessing_metadata / "trace_metadata_preprocessed.csv", index=False)

    result = build_record_coverage_from_config(config_path=config_path)

    output = tmp_path / "outputs" / "tables" / "record_coverage.csv"
    records = pd.read_csv(output)
    assert result["record_coverage"] == str(output)
    assert result["record_coverage_path"] == str(output)
    assert result["preprocessed_trace_metadata_path"].endswith("trace_metadata_preprocessed.csv")
    assert result["event_station_records_path"].endswith("event_station_records_preprocessed.csv")
    assert result["rows"] == 1
    assert records.loc[0, "event_id"] == "E1"
    assert records.loc[0, "station"] == "STA1"
    assert records.loc[0, "observed_start_s"] == -5.0


def test_preprocess_waveform_files_uses_configured_waveform_paths(tmp_path: Path, monkeypatch, capsys) -> None:
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

    def fake_preprocess_one_file(input_path, output_path, *, source, event_id, settings, overwrite, cached_metadata=None):
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

    result = preprocess_waveform_files(records, config=cfg, verbose=True)
    output = capsys.readouterr().out

    assert set(result.manifest["source"]) == {"observed", "synthetic"}
    assert "Resolved waveform sources: observed, synthetic" in output
    assert "observed 1/1 event E01" in output
    assert "synthetic 1/1 event E01" in output
    assert "Wrote preprocessing manifest:" in output
    assert set(result.manifest["input_file"]) == {str(observed_path), str(synthetic_path)}
    assert result.event_station_records.loc[0, "event_id"] == "E01"
    assert "event_title" not in result.event_station_records.columns
    assert result.event_station_records.loc[0, "observed_raw_waveform"] == str(observed_path)
    assert result.event_station_records.loc[0, "synthetic_raw_waveform"] == str(synthetic_path)
    assert Path(result.event_station_records.loc[0, "observed_processed_waveform"]).is_file()
    assert Path(result.event_station_records.loc[0, "synthetic_processed_waveform"]).is_file()


def test_preprocess_waveform_files_backfills_blank_existing_waveform_columns(tmp_path: Path, monkeypatch) -> None:
    """Blank waveform columns should not prevent config-derived path resolution."""

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
                "waveforms:",
                "  preprocessing:",
                "    lowpass_hz: 1.0",
            ]
        ),
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    records = pd.DataFrame(
        {
            "event_id": ["E01"],
            "station": ["STA01"],
            "observed_waveform": [""],
            "synthetic_waveform": [pd.NA],
            "observed_raw_waveform": [""],
            "synthetic_raw_waveform": [""],
            "observed_processed_waveform": [""],
            "synthetic_processed_waveform": [""],
        }
    )

    def fake_preprocess_one_file(input_path, output_path, *, source, event_id, settings, overwrite, cached_metadata=None):
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
                "processing": "Filter: lowpass 1 Hz",
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
    out = result.event_station_records.loc[0]

    assert set(result.manifest["input_file"]) == {str(observed_path), str(synthetic_path)}
    assert out["observed_raw_waveform"] == str(observed_path)
    assert out["synthetic_raw_waveform"] == str(synthetic_path)
    assert Path(out["observed_processed_waveform"]).is_file()
    assert Path(out["synthetic_processed_waveform"]).is_file()
    assert out["observed_waveform_preprocessing"] == "Filter: lowpass 1 Hz"
    assert out["synthetic_waveform_preprocessing"] == "Filter: lowpass 1 Hz"


def test_preprocess_waveform_files_does_not_label_rows_without_paths(tmp_path: Path) -> None:
    """Preprocessing labels should not imply that blank source rows were processed."""

    records = pd.DataFrame({"event_id": ["E01"], "station": ["STA01"], "observed_waveform": [""]})

    result = preprocess_waveform_files(records, output_root=tmp_path / "processed", source_columns={"observed": "observed_waveform"})

    assert result.manifest.empty
    assert result.event_station_records.empty

    audit = preprocess_waveform_files(
        records,
        output_root=tmp_path / "processed-audit",
        source_columns={"observed": "observed_waveform"},
        drop_unprocessed_rows=False,
    )
    assert audit.event_station_records.loc[0, "observed_processed_waveform"] == ""
    assert audit.event_station_records.loc[0, "observed_waveform_preprocessing"] == ""


def test_preprocess_waveform_files_drops_rows_without_processed_paths(tmp_path: Path, monkeypatch) -> None:
    """The preprocessed handoff table should only include usable waveform rows."""

    raw_path = tmp_path / "raw" / "E01.pkl"
    raw_path.parent.mkdir()
    raw_path.write_bytes(b"raw")
    records = pd.DataFrame(
        {
            "event_id": ["E01", "E02"],
            "station": ["STA01", "STA02"],
            "observed_waveform": [raw_path, ""],
        }
    )

    def fake_preprocess_one_file(input_path, output_path, *, source, event_id, settings, overwrite, cached_metadata=None):
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

    result = preprocess_waveform_files(records, output_root=tmp_path / "processed", source_columns={"observed": "observed_waveform"})

    assert result.event_station_records["event_id"].tolist() == ["E01"]
    assert result.event_station_records.loc[0, "observed_processed_waveform"]


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

    def fake_preprocess_one_file(input_path, output_path, *, source, event_id, settings, overwrite, cached_metadata=None):
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


def test_configured_templates_override_stale_nonexistent_metadata_paths(tmp_path: Path, monkeypatch) -> None:
    """Valid configured templates should not be masked by stale path columns."""

    fixture_root = tmp_path / "fixtures"
    observed_path = fixture_root / "observed" / "E01" / "STA01.pkl"
    synthetic_path = fixture_root / "synthetic" / "model_a" / "E01" / "STA01.pkl"
    observed_path.parent.mkdir(parents=True)
    synthetic_path.parent.mkdir(parents=True)
    observed_path.write_bytes(b"observed")
    synthetic_path.write_bytes(b"synthetic")
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        "\n".join(
            [
                "project:",
                "  root_dir: .",
                "paths:",
                "  observed_template: fixtures/observed/{event_id}/{station}.pkl",
                "  synthetic_template: fixtures/synthetic/{model}/{event_id}/{station}.pkl",
                "outputs:",
                "  preprocessed_waveforms: processed",
                "metrics:",
                "  models: [model_a]",
            ]
        ),
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    records = pd.DataFrame(
        {
            "event_id": ["E01"],
            "station": ["STA01"],
            "observed_mseed": ["old/missing/E01.mseed"],
            "synthetic_mseed": ["old/missing/model_a/E01.mseed"],
        }
    )

    def fake_preprocess_one_file(input_path, output_path, *, source, event_id, settings, overwrite, cached_metadata=None):
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

    assert set(result.manifest["input_file"]) == {str(observed_path), str(synthetic_path)}
    row = result.event_station_records.loc[0]
    assert row["observed_raw_waveform"] == str(observed_path)
    assert row["synthetic_raw_waveform"] == str(synthetic_path)


def test_configured_templates_override_existing_legacy_metadata_paths(tmp_path: Path, monkeypatch) -> None:
    """Configured canonical waveform columns should win over legacy mseed columns."""

    fixture_root = tmp_path / "fixtures"
    observed_path = fixture_root / "observed" / "E01" / "STA01.pkl"
    synthetic_path = fixture_root / "synthetic" / "model_a" / "E01" / "STA01.pkl"
    legacy_observed_path = fixture_root / "legacy" / "observed" / "E01.mseed"
    legacy_synthetic_path = fixture_root / "legacy" / "synthetic" / "model_a" / "E01.mseed"
    for path in (observed_path, synthetic_path, legacy_observed_path, legacy_synthetic_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(path.name.encode("utf-8"))
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        "\n".join(
            [
                "project:",
                "  root_dir: .",
                "paths:",
                "  observed_template: fixtures/observed/{event_id}/{station}.pkl",
                "  synthetic_template: fixtures/synthetic/{model}/{event_id}/{station}.pkl",
                "outputs:",
                "  preprocessed_waveforms: processed",
                "metrics:",
                "  models: [model_a]",
            ]
        ),
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    records = pd.DataFrame(
        {
            "event_id": ["E01"],
            "station": ["STA01"],
            "observed_mseed": [str(legacy_observed_path)],
            "synthetic_mseed": [str(legacy_synthetic_path)],
        }
    )

    def fake_preprocess_one_file(input_path, output_path, *, source, event_id, settings, overwrite, cached_metadata=None):
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

    assert set(result.manifest["input_file"]) == {str(observed_path), str(synthetic_path)}
    row = result.event_station_records.loc[0]
    assert row["observed_raw_waveform"] == str(observed_path)
    assert row["synthetic_raw_waveform"] == str(synthetic_path)


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


def test_configured_partial_waveform_matches_stop_before_writing_blank_rows(tmp_path: Path, monkeypatch) -> None:
    """Configured waveform templates should not silently write blank unmatched rows."""

    observed_root = tmp_path / "raw" / "observed"
    observed_root.mkdir(parents=True)
    (observed_root / "E01.pkl").write_bytes(b"observed")
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        "\n".join(
            [
                "project:",
                "  root_dir: .",
                "paths:",
                "  observed_template: raw/observed/{event_id}.pkl",
                "outputs:",
                "  preprocessed_waveforms: processed",
            ]
        ),
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    records = pd.DataFrame(
        {
            "event_id": ["E01", "E02"],
            "station": ["STA01", "STA02"],
            "observed_waveform": ["", ""],
            "observed_processed_waveform": ["", ""],
        }
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("preprocessing should not run when configured paths are incomplete")

    monkeypatch.setattr(preprocessing_module, "_preprocess_one_file", fail_if_called)

    with pytest.raises(ValueError, match="Example unmatched event IDs: \\['E02'\\]"):
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

    assert result.manifest.loc[0, "status"] == "cached_missing_metadata"
    assert "trace metadata was not available" in result.manifest.loc[0, "message"]
    assert result.manifest.loc[0, "trace_count"] == 0
    assert result.event_station_records.loc[0, "observed_processed_waveform"] == str(cached_path)

    writes: list[Path] = []
    monkeypatch.setattr(preprocessing_module, "preprocess_stream", lambda stream, settings: stream)
    monkeypatch.setattr(preprocessing_module, "_write_waveform_file", lambda stream, output_path, input_path: writes.append(output_path))

    overwritten = preprocess_waveform_files(records, output_root=output_root, overwrite=True)

    assert overwritten.manifest.loc[0, "status"] == "written"
    assert writes == [cached_path]


def test_cached_waveforms_without_metadata_do_not_read_processed_files(tmp_path: Path, monkeypatch) -> None:
    """Fast resume should not open cached waveform files just to check existence."""

    raw_path = tmp_path / "raw" / "E01.pkl"
    raw_path.parent.mkdir()
    raw_path.write_bytes(b"raw")
    output_root = tmp_path / "processed"
    cached_path = output_root / "observed" / "E01" / "E01.pkl"
    cached_path.parent.mkdir(parents=True)
    cached_path.write_bytes(b"cached waveform placeholder")
    records = pd.DataFrame({"event_id": ["E01"], "station": ["STA01"], "observed_waveform": [raw_path]})

    def fail_read(path):
        raise AssertionError(f"cached waveform should not be opened during fast resume: {path}")

    monkeypatch.setattr(preprocessing_module, "read_waveform_file", fail_read)

    result = preprocess_waveform_files(records, output_root=output_root)

    assert result.manifest.loc[0, "status"] == "cached_missing_metadata"
    assert result.manifest.loc[0, "trace_count"] == 0
    assert "Skipping waveform read for fast resume" in result.manifest.loc[0, "message"]
    assert result.trace_metadata.empty


def test_cached_waveforms_reuse_existing_trace_metadata_without_reading_files(tmp_path: Path, monkeypatch) -> None:
    """Existing trace metadata should avoid reopening cached waveform files."""

    raw_path = tmp_path / "raw" / "E01.pkl"
    raw_path.parent.mkdir()
    raw_path.write_bytes(b"raw")
    output_root = tmp_path / "processed"
    cached_path = output_root / "observed" / "E01" / "E01.pkl"
    metadata_dir = output_root / "metadata"
    cached_path.parent.mkdir(parents=True)
    metadata_dir.mkdir(parents=True)
    cached_path.write_bytes(b"cached waveform placeholder")
    pd.DataFrame(
        {
            "event_id": ["E01"],
            "station": ["STA01"],
            "starttime": ["2020-01-01T00:00:00Z"],
            "endtime": ["2020-01-01T00:01:00Z"],
            "source_type": ["observed"],
            "input_file": [str(raw_path)],
            "output_file": [str(cached_path)],
        }
    ).to_csv(metadata_dir / "trace_metadata_preprocessed.csv", index=False)
    records = pd.DataFrame({"event_id": ["E01"], "station": ["STA01"], "observed_waveform": [raw_path]})

    def fail_read(path):
        raise AssertionError(f"cached waveform should not be opened: {path}")

    monkeypatch.setattr(preprocessing_module, "read_waveform_file", fail_read)

    result = preprocess_waveform_files(records, output_root=output_root)

    assert result.manifest.loc[0, "status"] == "cached"
    assert result.manifest.loc[0, "trace_count"] == 1
    assert result.trace_metadata.loc[0, "station"] == "STA01"
