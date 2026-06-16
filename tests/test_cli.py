from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from spatial_vtk.cli import main


def test_cli_help(capsys):
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "Spatial validation tools" in captured.out


def test_cli_version(capsys):
    assert main(["--version"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip()


def test_cli_spatial_summaries_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["spatial", "summaries", "--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "Build standard spatial-statistics summary tables" in captured.out
    assert "--station-metadata" in captured.out


def test_cli_qc_summaries_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["qc", "summaries", "--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "Build compact QC summary tables" in captured.out
    assert "--chunksize" in captured.out


def test_cli_config_show_section(tmp_path, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    config.write_text(
        """
project:
  root_dir: .
metrics:
  passbands: ["2-4"]
""",
        encoding="utf-8",
    )
    assert main(["config", "show", "--config", str(config), "--section", "metrics"]) == 0
    captured = capsys.readouterr()
    assert "passbands" in captured.out


def test_cli_config_set_supplies_default_config(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    settings = tmp_path / "svtk-cli-config.json"
    config.write_text(
        """
project:
  root_dir: .
metrics:
  passbands: ["1-2"]
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("SVTK_CLI_CONFIG_FILE", str(settings))

    assert main(["config", "set", str(config)]) == 0
    assert main(["config", "find"]) == 0
    assert main(["config", "show", "--section", "metrics"]) == 0

    captured = capsys.readouterr()
    assert "Saved default Spatial-VTK config" in captured.out
    assert str(config.resolve()) in captured.out
    assert "passbands" in captured.out

    assert main(["config", "unset"]) == 0
    assert not settings.exists()


def test_cli_plot_band_score_distribution_uses_config_defaults(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    table_dir = tmp_path / "outputs" / "tables"
    table_dir.mkdir(parents=True)
    metrics = table_dir / "metrics_long.csv"
    metrics.write_text("band,score,metric\n1-2 sec,0.5,PGA\n", encoding="utf-8")
    config.write_text(
        """
project:
  root_dir: .
outputs:
  tables: outputs/tables
  figures: outputs/figures
  artifacts:
    metrics_long:
      filename: metrics_long.csv
""",
        encoding="utf-8",
    )
    seen = {}

    from spatial_vtk.metrics.plot import model_comparison

    def fake_plot_band_score_distribution(df, output_path=None, **kwargs):
        seen["rows"] = len(df)
        seen["output_path"] = Path(output_path)
        seen["kwargs"] = kwargs
        seen["output_path"].parent.mkdir(parents=True, exist_ok=True)
        seen["output_path"].write_text("figure", encoding="utf-8")
        return seen["output_path"]

    monkeypatch.setattr(model_comparison, "plot_band_score_distribution", fake_plot_band_score_distribution)

    assert (
        main(
            [
                "plot",
                "metrics",
                "band-score-distribution",
                "--config",
                str(config),
                "--kwargs",
                "score_col=score",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    expected_output = tmp_path / "outputs" / "figures" / "band_score_distribution.png"
    assert seen["rows"] == 1
    assert seen["output_path"] == expected_output
    assert seen["kwargs"]["score_col"] == "score"
    assert captured.out.strip() == str(expected_output)


def test_cli_prepare_station_metadata(tmp_path):
    src = tmp_path / "stations.csv"
    out = tmp_path / "prepared.csv"
    pd.DataFrame({"stationcode": ["sta1"], "station_latitude": [34.0], "station_longitude": [-118.0]}).to_csv(src, index=False)
    assert main(["io", "prepare-stations", "--input", str(src), "--output", str(out)]) == 0
    prepared = pd.read_csv(out)
    assert set(["station", "lat", "lon"]) <= set(prepared.columns)
    assert prepared.loc[0, "station"] == "STA1"


def test_cli_qc_manual_queue(tmp_path):
    src = tmp_path / "trace_summary.csv"
    out = tmp_path / "queue.csv"
    pd.DataFrame(
        {
            "event_id": ["ev1", "ev1"],
            "station": ["STA1", "STA2"],
            "component": ["R", "T"],
            "dominant_band_label": ["2-4", "4-8"],
            "event_lat": [34.0, 34.0],
            "event_lon": [-118.0, -118.0],
            "station_lat": [34.1, 34.2],
            "station_lon": [-118.1, -118.2],
        }
    ).to_csv(src, index=False)
    assert main(["qc", "manual-queue", "--trace-summary", str(src), "--output", str(out), "--band", "2-4 sec"]) == 0
    queue = pd.read_csv(out)
    assert len(queue) == 1
    assert queue.loc[0, "station"] == "STA1"


def test_cli_metrics_outputs(tmp_path):
    metrics = tmp_path / "metrics.csv"
    events = tmp_path / "events.csv"
    stations = tmp_path / "stations.csv"
    output_dir = tmp_path / "outputs"
    pd.DataFrame(
        {
            "event_id": ["ev1"],
            "station": ["STA1"],
            "component": ["R"],
            "model": ["m1"],
            "metric_group": ["cross_correlation"],
            "metric": ["original_cc"],
            "passband": ["2-4s"],
            "value": [0.9],
        }
    ).to_csv(metrics, index=False)
    pd.DataFrame({"event_id": ["ev1"], "event_lat": [34.0], "event_lon": [-118.0], "magnitude": [4.5]}).to_csv(events, index=False)
    pd.DataFrame({"station": ["STA1"], "station_lat": [34.1], "station_lon": [-118.2], "Vs30": [400.0]}).to_csv(stations, index=False)
    assert main(["metrics", "outputs", "--metrics", str(metrics), "--events", str(events), "--stations", str(stations), "--output-dir", str(output_dir), "--format", "csv"]) == 0
    assert (output_dir / "metrics_long.csv").exists()
    assert (output_dir / "dashboard_summaries" / "model_metric_band.csv").exists()


def test_cli_metrics_plan_applies_scenario_and_overrides(tmp_path):
    config = tmp_path / "spatial-vtk.yaml"
    obs = tmp_path / "obs.csv"
    syn = tmp_path / "syn.csv"
    out = tmp_path / "tasks.csv"
    config.write_text(
        """
project:
  root_dir: .
metrics:
  groups: [amplitude]
  components: [R, T]
  passbands: [[1, 2]]
  models: [m1]
run_scenarios:
  spectral:
    metrics:
      metrics: [PSA]
      spectral:
        periods_s: [1.0, 2.0]
""",
        encoding="utf-8",
    )
    pd.DataFrame({"event_id": ["ev1"], "station": ["STA1"], "component": ["Z"], "model": ["m1"], "path": ["obs.npz"], "dt": [0.01]}).to_csv(obs, index=False)
    pd.DataFrame({"event_id": ["ev1"], "station": ["STA1"], "component": ["Z"], "model": ["m1"], "path": ["syn.npz"], "dt": [0.01]}).to_csv(syn, index=False)

    assert (
        main(
            [
                "metrics",
                "plan",
                "--config",
                str(config),
                "--run-scenario",
                "spectral",
                "--metric",
                "PGA",
                "--component",
                "Z",
                "--observed-inventory",
                str(obs),
                "--synthetic-inventory",
                str(syn),
                "--output",
                str(out),
            ]
        )
        == 0
    )
    tasks = pd.read_csv(out)
    assert tasks["metrics"].unique().tolist() == ["PGA"]
    assert tasks["component"].unique().tolist() == ["Z"]


def test_cli_metrics_plan_manifest_accepts_batch_count(tmp_path):
    config = tmp_path / "spatial-vtk.yaml"
    obs = tmp_path / "obs.csv"
    syn = tmp_path / "syn.csv"
    out = tmp_path / "manifest.json"
    config.write_text(
        """
project:
  root_dir: .
metrics:
  metrics: [PGA]
  components: [Z]
  passbands: [[1, 2]]
  models: [m1]
""",
        encoding="utf-8",
    )
    rows = {
        "event_id": ["ev1", "ev1", "ev1"],
        "station": ["STA1", "STA2", "STA3"],
        "component": ["Z", "Z", "Z"],
        "path": ["one.npz", "two.npz", "three.npz"],
        "dt": [0.01, 0.01, 0.01],
    }
    pd.DataFrame(rows).to_csv(obs, index=False)
    synthetic_rows = {**rows, "model": ["m1", "m1", "m1"]}
    pd.DataFrame(synthetic_rows).to_csv(syn, index=False)

    assert (
        main(
            [
                "metrics",
                "plan",
                "--config",
                str(config),
                "--observed-inventory",
                str(obs),
                "--synthetic-inventory",
                str(syn),
                "--manifest",
                "--batch-count",
                "2",
                "--batch-output-dir",
                str(tmp_path / "metric_batches"),
                "--output",
                str(out),
            ]
        )
        == 0
    )

    manifest = json.loads(out.read_text(encoding="utf-8"))
    assert len(manifest["tasks"]) == 3
    assert [len(batch["task_indices"]) for batch in manifest["batches"]] == [2, 1]


def test_cli_metrics_inventories_builds_from_trace_metadata(tmp_path):
    trace_metadata = tmp_path / "trace_metadata.csv"
    observed = tmp_path / "observed_inventory.parquet"
    synthetic = tmp_path / "synthetic_inventory.parquet"
    config = tmp_path / "spatial-vtk.yaml"
    config.write_text(
        """
project:
  root_dir: .
metrics:
  models: [model_a]
""",
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "source_type": ["observed", "synthetic"],
            "event_id": ["e1", "e1"],
            "station": ["abc", "abc"],
            "component": ["z", "z"],
            "input_file": ["raw_obs.mseed", "synthetic_source.mseed"],
            "output_file": ["processed_obs.npz", "processed_syn.npz"],
            "delta": [0.01, 0.02],
        }
    ).to_csv(trace_metadata, index=False)

    assert (
        main(
            [
                "metrics",
                "inventories",
                "--config",
                str(config),
                "--trace-metadata",
                str(trace_metadata),
                "--observed-output",
                str(observed),
                "--synthetic-output",
                str(synthetic),
                "--overwrite",
            ]
        )
        == 0
    )

    observed_rows = pd.read_parquet(observed)
    synthetic_rows = pd.read_parquet(synthetic)
    assert observed_rows.loc[0, "waveform_path"] == "processed_obs.npz"
    assert synthetic_rows.loc[0, "waveform_path"] == "synthetic_source.mseed"
    assert synthetic_rows.loc[0, "model"] == "model_a"


def test_cli_metrics_cache_waveforms_writes_cached_manifest(tmp_path):
    obs = tmp_path / "obs.npz"
    syn = tmp_path / "syn.npz"
    manifest_path = tmp_path / "manifest.json"
    output_path = tmp_path / "cached_manifest.json"
    batch_dir = tmp_path / "cached_batches"
    cache_root = tmp_path / "cache"
    _write_cli_npz(obs, [0.0, 1.0, 0.0], station="ABC", channel="HNZ")
    _write_cli_npz(syn, [0.0, 0.5, 0.0], station="ABC", channel="HNZ")
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "qc_table": "",
                "tasks": [
                    {
                        "task_id": "task-1",
                        "event_id": "e1",
                        "station": "ABC",
                        "component": "Z",
                        "model": "m1",
                        "passband": "",
                        "obs_waveform_path": str(obs),
                        "syn_waveform_path": str(syn),
                        "dt": 0.01,
                        "metrics": "PGA",
                        "transforms": "log2_residual",
                        "output_mode": "full",
                    }
                ],
                "batches": [{"batch_index": 0, "task_indices": [0], "output_path": str(tmp_path / "old_batch.csv")}],
            }
        ),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "metrics",
                "cache-waveforms",
                "--manifest",
                str(manifest_path),
                "--output",
                str(output_path),
                "--cache-root",
                str(cache_root),
                "--batch-output-dir",
                str(batch_dir),
            ]
        )
        == 0
    )

    cached = json.loads(output_path.read_text(encoding="utf-8"))
    assert cached["tasks"][0]["obs_waveform_path"] != str(obs)
    assert cached["tasks"][0]["syn_waveform_path"] != str(syn)
    assert cached["tasks"][0]["obs_waveform_path"].endswith(".npz")
    assert cached["batches"][0]["output_path"] == str(batch_dir / "metrics_batch_0000.csv")
    assert len(list(cache_root.rglob("*.npz"))) == 2


def test_cli_metrics_slurm_reports_script_without_submit(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    manifest = tmp_path / "manifest.json"
    script = tmp_path / "run_metrics.slurm"
    settings = tmp_path / "svtk-cli-config.json"
    config.write_text(
        """
project:
  root_dir: .
metrics:
  slurm:
    python_command: python
    max_concurrent: 2
""",
        encoding="utf-8",
    )
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "qc_table": "",
                "tasks": [],
                "batches": [{"batch_index": 0, "task_indices": [], "output_path": str(tmp_path / "batch.csv")}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SVTK_CLI_CONFIG_FILE", str(settings))
    assert main(["config", "set", str(config)]) == 0

    assert main(["metrics", "slurm", "--manifest", str(manifest), "--output", str(script)]) == 0

    captured = capsys.readouterr()
    assert "Wrote metric Slurm script" in captured.out
    assert "No job was submitted" in captured.out
    assert script.exists()


def test_cli_dashboard_metrics_uses_configured_output_roots(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  tables: outputs/tables
""",
        encoding="utf-8",
    )
    launched = {}

    class FakeProcess:
        pid = 12345

    def fake_launch_metrics_dashboard(**kwargs):
        launched.update(kwargs)
        return FakeProcess()

    monkeypatch.setattr(
        "spatial_vtk.visualize.dashboard.launch_metrics_dashboard",
        fake_launch_metrics_dashboard,
    )

    assert main(["dashboard", "metrics", "--config", str(config), "--port", "8555", "--proxy-mode"]) == 0

    captured = capsys.readouterr()
    assert "Metrics dashboard data:" in captured.out
    assert Path(launched["metrics_root"]) == tmp_path / "outputs" / "tables" / "dashboard_metrics"
    assert Path(launched["summary_root"]) == tmp_path / "outputs" / "tables" / "dashboard_summaries"
    assert Path(launched["config_path"]) == config.resolve()
    assert launched["server_port"] == 8555
    assert launched["proxy_mode"] is True


def test_cli_dashboard_qc_uses_configured_trace_summary(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  tables: outputs/tables
""",
        encoding="utf-8",
    )
    launched = {}

    class FakeProcess:
        pid = 12346

    def fake_launch_qc_dashboard(**kwargs):
        launched.update(kwargs)
        return FakeProcess()

    monkeypatch.setattr(
        "spatial_vtk.visualize.dashboard.launch_qc_dashboard",
        fake_launch_qc_dashboard,
    )

    assert main(["dashboard", "qc", "--config", str(config), "--port", "8556"]) == 0

    captured = capsys.readouterr()
    assert "QC dashboard trace summary:" in captured.out
    assert Path(launched["trace_summary"]) == tmp_path / "outputs" / "tables" / "qc_trace_summary.csv"
    assert Path(launched["config_path"]) == config.resolve()
    assert launched["server_port"] == 8556


def test_cli_call_importable_function(capsys):
    assert main(["call", "spatial_vtk.config.labels.metric_display_name", "--args", "C5"]) == 0
    captured = capsys.readouterr()
    assert "Peak acceleration" in captured.out


def _write_cli_npz(path, samples, *, station: str, channel: str) -> None:
    np.savez(
        path,
        data=np.asarray(samples, dtype=float),
        channels=np.asarray([channel]),
        station=np.asarray(station),
        sampling_rate=np.asarray(100.0, dtype=float),
    )


def test_cli_plot_metrics_wrapper(tmp_path):
    src = tmp_path / "metrics.csv"
    out = tmp_path / "residuals_vs_distance.png"
    pd.DataFrame(
        {
            "distance_km": [10.0, 20.0, 30.0],
            "residual": [-0.2, 0.1, 0.3],
            "metric": ["PGA", "PGA", "PGA"],
            "model": ["m1", "m1", "m1"],
        }
    ).to_csv(src, index=False)
    assert main(["plot", "metrics", "residuals-vs-distance", "--input", str(src), "--output", str(out)]) == 0
    assert out.exists()


def test_cli_map_spatial_wrapper(tmp_path):
    src = tmp_path / "station_metrics.csv"
    out = tmp_path / "station_metric_map.png"
    pd.DataFrame(
        {
            "sta_lon": [-118.2, -118.1, -118.0],
            "sta_lat": [34.0, 34.1, 34.2],
            "residual": [-0.1, 0.2, 0.0],
        }
    ).to_csv(src, index=False)
    assert main(["map", "spatial", "station-metric", "--input", str(src), "--output", str(out), "--no-basemap"]) == 0
    assert out.exists()


def test_cli_visualize_context_wrapper(tmp_path):
    src = tmp_path / "event_station.csv"
    out = tmp_path / "station_coverage.png"
    pd.DataFrame(
        {
            "event_id": ["ev1", "ev1", "ev2"],
            "station": ["STA1", "STA2", "STA1"],
        }
    ).to_csv(src, index=False)
    assert main(["visualize", "context", "station-coverage", "--input", str(src), "--output", str(out)]) == 0
    assert out.exists()


def test_cli_plot_list(capsys):
    assert main(["plot", "metrics", "list"]) == 0
    captured = capsys.readouterr()
    assert "residuals-vs-distance" in captured.out
