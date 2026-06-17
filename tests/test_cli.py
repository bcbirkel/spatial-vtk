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


def test_cli_qc_build_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["qc", "build", "--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "Build standard QC trace, inventory, and overlap tables" in captured.out
    assert "--event-stations" in captured.out
    assert "--overlap-inventory-output" in captured.out


def test_cli_metrics_estimate_writes_summary(tmp_path, capsys):
    tasks = tmp_path / "metric_tasks.csv"
    output = tmp_path / "metric_task_estimate.csv"
    tasks.write_text(
        "event_id,station,component,model,passband,metrics\n"
        "e1,S1,R,m1,1-2 sec,\"['PGA','PGV']\"\n",
        encoding="utf-8",
    )

    assert (
        main(
            [
                "metrics",
                "estimate",
                "--tasks",
                str(tasks),
                "--seconds-per-task",
                "30",
                "--memory-gb-per-task",
                "1.5",
                "--parallel-tasks",
                "2",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert captured.out.strip() == str(output)
    summary = pd.read_csv(output)
    assert "Metric tasks" in set(summary["Estimate"])
    assert "Wall time at 2 parallel tasks" in set(summary["Estimate"])


def test_cli_registered_plot_help_shows_common_options(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["plot", "metrics", "residuals-vs-distance", "--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "--metric" in captured.out
    assert "--passband" in captured.out
    assert "--value-col" in captured.out
    assert "--y-col" in captured.out
    assert "--write-sidecar" in captured.out


def test_cli_registered_plot_help_names_config_defaults(capsys):
    """Registered figure help should explain config-backed table and figure defaults."""

    with pytest.raises(SystemExit) as excinfo:
        main(["plot", "metrics", "band-score-distribution", "--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    help_text = " ".join(captured.out.split())
    assert "function argument 'df'" in help_text
    assert "configured output table 'metrics_long'" in help_text
    assert "configured figure output 'band_score_distribution'" in help_text
    assert "svtk config set" in help_text


def test_cli_registered_map_help_names_config_defaults(capsys):
    """Registered map help should make default figure artifacts discoverable."""

    with pytest.raises(SystemExit) as excinfo:
        main(["map", "spatial", "station-bias", "--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    help_text = " ".join(captured.out.split())
    assert "function argument 'station_df'" in help_text
    assert "configured output table 'station_bias'" in help_text
    assert "configured figure output 'station_residual_map'" in help_text


def test_cli_reference_describes_config_defaults_before_kwargs():
    """CLI docs should not present kwargs as the primary plotting interface."""

    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "reference" / "cli_api.rst").read_text(encoding="utf-8")
    assert "resolve their standard input tables and figure paths from the active config" in text
    assert "first-class flags where they apply" in text
    assert "Use ``--kwargs key=value`` only for advanced function-specific options" in text


def test_cli_workflow_uses_curated_commands_for_standard_steps():
    """The shell workflow should not route routine tutorial steps through svtk call."""

    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "examples" / "cli_workflow.rst").read_text(encoding="utf-8")
    assert "svtk call" not in text


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
                "--write-sidecar",
                "--sidecar-rows",
                "5",
                "--sidecar-dir",
                str(tmp_path / "sidecars"),
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
    assert seen["kwargs"]["write_sidecar"] is True
    assert seen["kwargs"]["sidecar_rows"] == 5
    assert seen["kwargs"]["sidecar_dir"] == tmp_path / "sidecars"
    assert captured.out.strip() == str(expected_output)


def test_cli_metric_long_plot_commands_use_config_defaults(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    table_dir = tmp_path / "outputs" / "tables"
    table_dir.mkdir(parents=True)
    metrics = table_dir / "metrics_long.csv"
    metrics.write_text("metric,band,model,component,distance_km,log2_residual\nPGA,1-2 sec,m1,Z,10,0.5\n", encoding="utf-8")
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

    from spatial_vtk.metrics.plot import trends

    def fake_plot_residuals_vs_distance(df, output_path=None, **kwargs):
        seen["rows"] = len(df)
        seen["output_path"] = Path(output_path)
        seen["kwargs"] = kwargs
        seen["output_path"].parent.mkdir(parents=True, exist_ok=True)
        seen["output_path"].write_text("figure", encoding="utf-8")
        return seen["output_path"]

    monkeypatch.setattr(trends, "plot_residuals_vs_distance", fake_plot_residuals_vs_distance)

    assert (
        main(
            [
                "plot",
                "metrics",
                "residuals-vs-distance",
                "--config",
                str(config),
                "--y-col",
                "log2_residual",
                "--group-col",
                "metric",
                "--fit",
                "lowess",
                "--metric",
                "PGA",
                "--passband",
                "1-2 sec",
                "--component",
                "Z",
                "--model",
                "m1",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    expected_output = tmp_path / "outputs" / "figures" / "residuals_vs_distance.png"
    assert seen["rows"] == 1
    assert seen["output_path"] == expected_output
    assert seen["kwargs"]["y_col"] == "log2_residual"
    assert seen["kwargs"]["group_col"] == "metric"
    assert seen["kwargs"]["fit"] == "lowess"
    assert seen["kwargs"]["metric"] == "PGA"
    assert seen["kwargs"]["passband"] == "1-2 sec"
    assert seen["kwargs"]["component"] == "Z"
    assert seen["kwargs"]["model"] == "m1"
    assert captured.out.strip() == str(expected_output)


def test_registered_plot_commands_use_public_import_surfaces():
    """Registered figure commands should point users at stable public imports."""

    from spatial_vtk.cli import METRICS_PLOT_COMMANDS, SPATIAL_MAP_COMMANDS, SPATIAL_PLOT_COMMANDS, _resolve_function

    for spec in METRICS_PLOT_COMMANDS.values():
        assert spec.function.startswith(("spatial_vtk.metrics.plot.", "spatial_vtk.spatial.plot."))
        assert ".model_comparison." not in spec.function
        assert ".periods." not in spec.function
        assert ".site_terms." not in spec.function
        assert ".trends." not in spec.function
        assert ".plot.metrics." not in spec.function
        assert callable(_resolve_function(spec.function))

    for spec in SPATIAL_PLOT_COMMANDS.values():
        assert spec.function.startswith("spatial_vtk.spatial.plot.")
        assert ".correlation." not in spec.function
        assert ".metrics." not in spec.function
        assert ".pca." not in spec.function
        assert callable(_resolve_function(spec.function))

    for spec in SPATIAL_MAP_COMMANDS.values():
        assert spec.function.startswith("spatial_vtk.spatial.map.")
        assert ".correlation." not in spec.function
        assert ".metrics." not in spec.function
        assert ".path." not in spec.function
        assert ".pca." not in spec.function
        assert callable(_resolve_function(spec.function))


def test_cli_spatial_plot_uses_configured_standard_table_default(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    table_dir = tmp_path / "outputs" / "tables"
    table_dir.mkdir(parents=True)
    distance_bins = table_dir / "distance_bin_correlations.csv"
    distance_bins.write_text("distance_center_km,mean_pair_correlation,pair_count\n10,0.4,5\n", encoding="utf-8")
    config.write_text(
        """
project:
  root_dir: .
outputs:
  tables: outputs/tables
  figures: outputs/figures
""",
        encoding="utf-8",
    )
    seen = {}

    import spatial_vtk.spatial.plot as spatial_plot
    from spatial_vtk.spatial.plot import correlation

    def fake_plot_correlogram(distance_df, output_path=None, **kwargs):
        seen["rows"] = len(distance_df)
        seen["output_path"] = Path(output_path)
        seen["kwargs"] = kwargs
        seen["output_path"].parent.mkdir(parents=True, exist_ok=True)
        seen["output_path"].write_text("figure", encoding="utf-8")
        return seen["output_path"]

    monkeypatch.setattr(correlation, "plot_correlogram", fake_plot_correlogram)
    monkeypatch.setattr(spatial_plot, "plot_correlogram", fake_plot_correlogram)

    assert main(["plot", "spatial", "correlogram", "--config", str(config)]) == 0
    captured = capsys.readouterr()
    expected_output = tmp_path / "outputs" / "figures" / "correlogram.png"
    assert seen["rows"] == 1
    assert seen["output_path"] == expected_output
    assert captured.out.strip() == str(expected_output)


def test_cli_spatial_map_uses_configured_standard_table_default(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    table_dir = tmp_path / "outputs" / "tables"
    table_dir.mkdir(parents=True)
    station_bias = table_dir / "station_bias.csv"
    station_bias.write_text("station,sta_lon,sta_lat,residual\nSTA,-118,34,0.2\n", encoding="utf-8")
    config.write_text(
        """
project:
  root_dir: .
outputs:
  tables: outputs/tables
  figures: outputs/figures
  artifacts:
    station_bias:
      filename: station_bias.csv
""",
        encoding="utf-8",
    )
    seen = {}

    import spatial_vtk.spatial.map as spatial_map
    from spatial_vtk.spatial.map import correlation

    def fake_plot_station_bias_map(station_df, output_path=None, **kwargs):
        seen["rows"] = len(station_df)
        seen["output_path"] = Path(output_path)
        seen["kwargs"] = kwargs
        seen["output_path"].parent.mkdir(parents=True, exist_ok=True)
        seen["output_path"].write_text("figure", encoding="utf-8")
        return seen["output_path"]

    monkeypatch.setattr(correlation, "plot_station_bias_map", fake_plot_station_bias_map)
    monkeypatch.setattr(spatial_map, "plot_station_bias_map", fake_plot_station_bias_map)

    assert main(["map", "spatial", "station-bias", "--config", str(config), "--no-basemap"]) == 0
    captured = capsys.readouterr()
    expected_output = tmp_path / "outputs" / "figures" / "station_residual_map.png"
    assert seen["rows"] == 1
    assert seen["output_path"] == expected_output
    assert seen["kwargs"]["add_basemap"] is False
    assert captured.out.strip() == str(expected_output)


def test_cli_context_figure_uses_configured_primary_and_alias_tables(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    table_dir = tmp_path / "outputs" / "tables"
    table_dir.mkdir(parents=True)
    (table_dir / "prepared_stations.csv").write_text("station,lon,lat\nSTA,-118,34\n", encoding="utf-8")
    (table_dir / "prepared_events.csv").write_text("event_id,event_lon,event_lat\nEV,-118.1,34.1\n", encoding="utf-8")
    config.write_text(
        """
project:
  root_dir: .
outputs:
  tables: outputs/tables
  figures: outputs/figures
""",
        encoding="utf-8",
    )
    seen = {}

    import spatial_vtk.visualize.context as context

    def fake_plot_station_event_context(stations_df, events_df, output_path=None, **kwargs):
        seen["station_rows"] = len(stations_df)
        seen["event_rows"] = len(events_df)
        seen["output_path"] = Path(output_path)
        seen["kwargs"] = kwargs
        seen["output_path"].parent.mkdir(parents=True, exist_ok=True)
        seen["output_path"].write_text("figure", encoding="utf-8")
        return seen["output_path"]

    monkeypatch.setattr(context, "plot_station_event_context", fake_plot_station_event_context)

    assert main(["visualize", "context", "station-event-context", "--config", str(config), "--no-basemap"]) == 0
    captured = capsys.readouterr()
    expected_output = tmp_path / "outputs" / "figures" / "station_event_context.png"
    assert seen["station_rows"] == 1
    assert seen["event_rows"] == 1
    assert seen["output_path"] == expected_output
    assert seen["kwargs"]["add_basemap"] is False
    assert captured.out.strip() == str(expected_output)


def test_cli_registered_plot_help_describes_alias_defaults(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["visualize", "context", "station-event-context", "--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    help_text = " ".join(captured.out.split())
    assert "Defaults to configured output table 'prepared_stations'" in help_text
    assert "Defaults to configured output table 'prepared_events'" in help_text


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
    assert Path(launched["metrics_root"]) == tmp_path / "outputs" / "dashboards" / "metrics_dashboard"
    assert Path(launched["summary_root"]) == tmp_path / "outputs" / "dashboards" / "dashboard_summaries"
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
