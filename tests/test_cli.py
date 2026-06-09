from __future__ import annotations

import pandas as pd

from spatial_vtk.cli import main


def test_cli_help(capsys):
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "Spatial validation tools" in captured.out


def test_cli_version(capsys):
    assert main(["--version"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip()


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


def test_cli_call_importable_function(capsys):
    assert main(["call", "spatial_vtk.config.labels.metric_display_name", "--args", "C5"]) == 0
    captured = capsys.readouterr()
    assert "Peak acceleration" in captured.out


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
