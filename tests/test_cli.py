from __future__ import annotations

import inspect
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
    help_text = " ".join(captured.out.split())
    assert "Build standard spatial-statistics summary tables" in captured.out
    assert "--station-metadata" in captured.out
    assert "--checkpoint-dir" in captured.out
    assert "--no-resume" in captured.out
    assert "default config is set with 'svtk config set'" in help_text


def test_cli_spatial_summaries_use_saved_config_defaults(tmp_path, monkeypatch, capsys):
    """After svtk config set, spatial summaries should use configured table paths."""

    from types import SimpleNamespace

    settings = tmp_path / "settings" / "svtk-config.json"
    config = tmp_path / "spatial-vtk.yaml"
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
spatial_statistics:
  metric: PGA
""",
        encoding="utf-8",
    )
    seen = {}

    def fake_run_spatial_statistics_workflow(
        metrics=None,
        *,
        cfg=None,
        metric=None,
        station_metadata=None,
        resume=True,
        checkpoint_dir=None,
        verbose=False,
    ):
        seen["metrics"] = metrics
        seen["cfg_root"] = cfg.root_dir
        seen["metric"] = metric
        seen["station_metadata"] = station_metadata
        seen["resume"] = resume
        seen["checkpoint_dir"] = checkpoint_dir
        seen["verbose"] = verbose
        return SimpleNamespace(
            metrics=("PGA",),
            elapsed_s=1.25,
            paths={"metric_field": tmp_path / "outputs" / "tables" / "metric_field.parquet"},
            failures=(),
        )

    monkeypatch.setenv("SVTK_CLI_CONFIG_FILE", str(settings))
    monkeypatch.setattr("spatial_vtk.spatial.calculate.run_spatial_statistics_workflow", fake_run_spatial_statistics_workflow)

    assert main(["config", "set", str(config)]) == 0
    assert main(["spatial", "summaries", "--verbose"]) == 0

    captured = capsys.readouterr()
    assert seen["metrics"] is None
    assert seen["cfg_root"] == tmp_path
    assert seen["metric"] is None
    assert seen["station_metadata"] is None
    assert seen["resume"] is True
    assert seen["checkpoint_dir"] is None
    assert seen["verbose"] is True
    assert "Spatial statistics metrics: PGA" in captured.out
    assert "metric_field:" in captured.out


def test_cli_spatial_derived_outputs_use_saved_config_defaults(tmp_path, monkeypatch, capsys):
    """After svtk config set, spatial derived outputs should use configured paths."""

    from types import SimpleNamespace

    settings = tmp_path / "settings" / "svtk-config.json"
    config = tmp_path / "spatial-vtk.yaml"
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
""",
        encoding="utf-8",
    )
    seen = {}

    def fake_run_spatial_derived_outputs_workflow(
        metrics=None,
        *,
        metric_field=None,
        station_bias=None,
        cfg=None,
        metric=None,
        pattern_passband=None,
        pattern_component=None,
        pattern_model=None,
        outputs="all",
        overwrite=False,
        verbose=False,
    ):
        seen["metrics"] = metrics
        seen["metric_field"] = metric_field
        seen["station_bias"] = station_bias
        seen["cfg_root"] = cfg.root_dir
        seen["metric"] = metric
        seen["pattern_passband"] = pattern_passband
        seen["pattern_component"] = pattern_component
        seen["pattern_model"] = pattern_model
        seen["outputs"] = outputs
        seen["overwrite"] = overwrite
        seen["verbose"] = verbose
        return SimpleNamespace(
            elapsed_s=2.5,
            paths={"redcap_clusters": tmp_path / "outputs" / "tables" / "redcap_clusters.parquet"},
            rows={"redcap_clusters": 4},
            reused=(),
            failures=(),
        )

    monkeypatch.setenv("SVTK_CLI_CONFIG_FILE", str(settings))
    monkeypatch.setattr("spatial_vtk.spatial.calculate.run_spatial_derived_outputs_workflow", fake_run_spatial_derived_outputs_workflow)

    assert main(["config", "set", str(config)]) == 0
    assert main(["spatial", "derived-outputs", "--outputs", "redcap_clusters", "--overwrite", "--verbose"]) == 0

    captured = capsys.readouterr()
    assert seen["metrics"] is None
    assert seen["metric_field"] is None
    assert seen["station_bias"] is None
    assert seen["cfg_root"] == tmp_path
    assert seen["metric"] is None
    assert seen["pattern_passband"] is None
    assert seen["pattern_component"] is None
    assert seen["pattern_model"] is None
    assert seen["outputs"] == "redcap_clusters"
    assert seen["overwrite"] is True
    assert seen["verbose"] is True
    assert "Spatial derived outputs elapsed: 2.5s" in captured.out
    assert "redcap_clusters_rows: 4" in captured.out


def test_cli_spatial_status_reports_named_missing_input(tmp_path, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
""",
        encoding="utf-8",
    )

    assert main(["spatial", "status", "--config", str(config), "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    rows = payload["status"]
    by_name = {row["name"]: row for row in rows}
    assert payload["reason"] == "missing_inputs"
    assert payload["should_run_spatial_summaries"] is False
    assert by_name["metrics_long_path"]["role"] == "input"
    assert by_name["metrics_long_path"]["state"] == "missing"
    assert by_name["metric_field_path"]["role"] == "output"
    assert by_name["morans_i_path"]["role"] == "output"
    assert "metrics_long_path=" in payload["message"]
    assert not (tmp_path / "outputs").exists()


def test_cli_spatial_status_reports_missing_outputs_with_existing_metrics(tmp_path, capsys):
    tables = tmp_path / "outputs" / "tables"
    tables.mkdir(parents=True)
    (tables / "metrics_long.parquet").write_bytes(b"placeholder")
    config = tmp_path / "spatial-vtk.yaml"
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
""",
        encoding="utf-8",
    )

    assert main(["spatial", "status", "--config", str(config), "--include-optional"]) == 0

    captured = capsys.readouterr()
    assert "Spatial outputs current: False" in captured.out
    assert "Spatial summaries run recommended: True" in captured.out
    assert "Reason: missing_outputs" in captured.out
    assert "metric_field_path" in captured.out
    assert "redcap_clusters_path" in captured.out


def test_cli_spatial_geojson_and_corridor_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["spatial", "geojson-summaries", "--help"])
    assert excinfo.value.code == 0
    geojson_help = capsys.readouterr().out
    assert "Metric rows table" in geojson_help
    assert "--chunksize" in geojson_help
    assert "--selector" in geojson_help

    with pytest.raises(SystemExit) as excinfo:
        main(["spatial", "corridors", "--help"])
    assert excinfo.value.code == 0
    corridor_help = capsys.readouterr().out
    assert "Region GeoJSON path" in corridor_help
    assert "--records" in corridor_help
    assert "--stations" in corridor_help


def test_cli_spatial_geojson_and_corridors_dispatch_configured_workflows(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace

    config = tmp_path / "spatial-vtk.yaml"
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
paths:
  region_geojson: regions.geojson
""",
        encoding="utf-8",
    )
    seen = {}

    def fake_geojson(metrics_table=None, geojson_path=None, *, output_key=None, cfg=None, selector=None, chunksize=None, verbose=False):
        seen["geojson"] = {
            "metrics_table": metrics_table,
            "geojson_path": geojson_path,
            "output_key": output_key,
            "cfg_root": cfg.root_dir,
            "selector": selector,
            "chunksize": chunksize,
            "verbose": verbose,
        }
        return SimpleNamespace(path=tmp_path / "geojson_region_summaries.csv", rows=3, source_rows=100, elapsed_s=2.5)

    def fake_corridors(geojson_path=None, *, station_table=None, event_table=None, records_table=None, output_key=None, cfg=None, verbose=False):
        seen["corridors"] = {
            "geojson_path": geojson_path,
            "station_table": station_table,
            "event_table": event_table,
            "records_table": records_table,
            "output_key": output_key,
            "cfg_root": cfg.root_dir,
            "verbose": verbose,
        }
        return SimpleNamespace(path=tmp_path / "corridors.parquet", rows=2, elapsed_s=1.5)

    monkeypatch.setattr("spatial_vtk.spatial.calculate.run_geojson_region_summary_workflow", fake_geojson)
    monkeypatch.setattr("spatial_vtk.spatial.calculate.run_boundary_corridor_workflow", fake_corridors)

    assert (
        main(
            [
                "spatial",
                "geojson-summaries",
                "--config",
                str(config),
                "--metrics",
                "metrics.parquet",
                "--geojson",
                "regions.geojson",
                "--selector",
                "basin",
                "--chunksize",
                "123",
                "--verbose",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "spatial",
                "corridors",
                "--config",
                str(config),
                "--geojson",
                "regions.geojson",
                "--stations",
                "stations.csv",
                "--events",
                "events.csv",
                "--records",
                "records.csv",
                "--verbose",
            ]
        )
        == 0
    )

    assert seen["geojson"]["metrics_table"] == "metrics.parquet"
    assert seen["geojson"]["geojson_path"] == "regions.geojson"
    assert seen["geojson"]["output_key"] == "geojson_region_summaries"
    assert seen["geojson"]["selector"] == "basin"
    assert seen["geojson"]["chunksize"] == 123
    assert seen["geojson"]["verbose"] is True
    assert seen["corridors"]["station_table"] == "stations.csv"
    assert seen["corridors"]["event_table"] == "events.csv"
    assert seen["corridors"]["records_table"] == "records.csv"
    assert seen["corridors"]["output_key"] == "corridors"
    assert seen["corridors"]["verbose"] is True
    captured = capsys.readouterr()
    assert "GeoJSON region summaries:" in captured.out
    assert "Corridors:" in captured.out


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


def test_cli_metrics_estimate_reads_manifest(tmp_path, capsys):
    """Metric estimates should work directly from resumable manifests."""

    from spatial_vtk.metrics.workflow import MetricWorkflowTask, write_task_manifest

    manifest = tmp_path / "metric_manifest.json"
    write_task_manifest(
        [
            MetricWorkflowTask(
                task_id="task-1",
                event_id="e1",
                station="S1",
                component="R",
                model="m1",
                passband="1-2 sec",
                metrics=("PGA", "PGV"),
            )
        ],
        manifest,
        output_dir=tmp_path / "batches",
    )

    assert (
        main(
            [
                "metrics",
                "estimate",
                "--manifest",
                str(manifest),
                "--seconds-per-task",
                "30",
                "--parallel-tasks",
                "2",
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert "Metric tasks" in captured.out
    assert "Approximate metric evaluations" in captured.out
    assert "Wall time at 2 parallel tasks" in captured.out


def test_cli_metrics_estimate_uses_saved_config_defaults(tmp_path, monkeypatch, capsys):
    """After svtk config set, metric estimate should not need repeated path flags."""

    from spatial_vtk.metrics.workflow import MetricWorkflowTask, write_task_manifest

    settings = tmp_path / "settings" / "svtk-config.json"
    config = tmp_path / "spatial-vtk.yaml"
    tables = tmp_path / "outputs" / "tables"
    tables.mkdir(parents=True)
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
""",
        encoding="utf-8",
    )
    write_task_manifest(
        [
            MetricWorkflowTask(
                task_id="task-1",
                event_id="e1",
                station="S1",
                component="R",
                model="m1",
                passband="1-2 sec",
                metrics=("PGA",),
            )
        ],
        tables / "metric_manifest.json",
        output_dir=tmp_path / "outputs" / "metric_batches",
    )
    monkeypatch.setenv("SVTK_CLI_CONFIG_FILE", str(settings))

    assert main(["config", "set", str(config)]) == 0
    assert main(["metrics", "estimate", "--seconds-per-task", "30"]) == 0

    captured = capsys.readouterr()
    output = tables / "metric_task_estimate.csv"
    assert str(output) in captured.out
    assert "Saved default Spatial-VTK config" in captured.out
    assert output.exists()


def test_cli_registered_plot_help_shows_common_options(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["plot", "metrics", "residuals-vs-distance", "--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "--metric" in captured.out
    assert "--passband" in captured.out
    assert "--value-col" in captured.out
    assert "--y-col" in captured.out
    assert "--no-connect-points" in captured.out
    assert "--mode" in captured.out
    assert "--dep" in captured.out
    assert "--indep" in captured.out
    assert "--colorby" in captured.out
    assert "--compare-to" in captured.out
    assert "--table" in captured.out
    assert "--station-region" in captured.out
    assert "--event-region" in captured.out
    assert "--components" in captured.out
    assert "--time-limit-s" in captured.out
    assert "--max-records" in captured.out
    assert "--max-traces" in captured.out
    assert "--write-sidecar" in captured.out


@pytest.mark.parametrize(
    ("command_prefix", "group_name"),
    [
        (("plot", "metrics"), "PLOT_COMMAND_GROUPS"),
        (("plot", "spatial"), "PLOT_COMMAND_GROUPS"),
        (("map", "spatial"), "MAP_COMMAND_GROUPS"),
        (("visualize", "context"), "VISUALIZE_COMMAND_GROUPS"),
        (("visualize", "qc"), "VISUALIZE_COMMAND_GROUPS"),
        (("visualize", "waveforms"), "VISUALIZE_COMMAND_GROUPS"),
    ],
)
def test_cli_registered_figure_commands_expose_sidecar_controls(command_prefix, group_name, capsys):
    """Every registry-backed figure command should expose row-provenance sidecars."""

    import spatial_vtk.cli as cli

    registry = getattr(cli, group_name)[command_prefix[-1]]
    for command_name, spec in sorted(registry.items()):
        function = cli._resolve_registered_plot_function(spec.function)
        parameters = set(inspect.signature(function).parameters)
        assert {"write_sidecar", "sidecar_rows", "sidecar_dir"} <= parameters, spec.function

        with pytest.raises(SystemExit) as excinfo:
            main([*command_prefix, command_name, "--help"])
        assert excinfo.value.code == 0
        help_text = capsys.readouterr().out
        assert "--write-sidecar" in help_text, command_name
        assert "--sidecar-rows" in help_text, command_name
        assert "--sidecar-dir" in help_text, command_name


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
    assert "``--mode``" in text
    assert "``--dep``" in text
    assert "``--indep``" in text
    assert "``--colorby``" in text
    assert "``--compare-to``" in text
    assert "``--bin-label``" in text
    assert "``--table``" in text
    assert "``--station-region``" in text
    assert "``--event-region``" in text
    assert "``--components``" in text
    assert "``--time-limit-s``" in text
    assert "``--max-records``" in text
    assert "``--max-traces``" in text
    assert "``--no-connect-points``" in text
    assert "Use ``--kwargs key=value`` only for advanced function-specific options" in text


def test_configuration_map_override_example_uses_first_class_flags():
    """Configuration docs should not teach routine plot controls through kwargs."""

    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "configuration.rst").read_text(encoding="utf-8")
    assert "svtk map spatial station-metric --config spatial-vtk.yaml" in text
    assert "--value-col log2_residual --metric PGA" in text
    assert "--kwargs value_col=log2_residual metric=PGA" not in text


def test_generated_cli_reference_names_plot_defaults():
    """Generated CLI pages should match live parser help for config defaults."""

    root = Path(__file__).resolve().parents[1]
    plot_text = (root / "docs" / "reference" / "cli" / "plot.rst").read_text(encoding="utf-8")
    map_text = (root / "docs" / "reference" / "cli" / "map.rst").read_text(encoding="utf-8")

    assert "Input CSV/parquet table for function argument 'df'" in plot_text
    assert "configured output table 'metrics_long' when --config is passed" in plot_text
    assert "configured figure output 'band_score_distribution' when --config is passed" in plot_text
    assert "default config is set with 'svtk config set'" in plot_text
    assert "Input CSV/parquet table for function argument 'station_df'" in map_text
    assert "configured output table 'station_bias' when --config is passed" in map_text
    assert "configured figure output 'station_residual_map' when --config is passed" in map_text
    assert "``--mode``" in map_text
    assert "``--dep``" in map_text
    assert "``--compare-to``" in map_text
    assert "``--station-region``" in map_text
    assert "``--event-region``" in map_text


def test_cli_workflow_uses_curated_commands_for_standard_steps():
    """The shell workflow should not route routine tutorial steps through svtk call."""

    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "examples" / "cli_workflow.rst").read_text(encoding="utf-8")
    assert "svtk call" not in text
    assert "--no-connect-points" in text
    assert "--kwargs connect_points=false" not in text
    assert "--mode PC1" in text
    assert "--kwargs mode=PC1" not in text
    assert "--dep PGA" in text
    assert "--indep distance" in text
    assert "--colorby dep" in text
    assert '--compare-to "LA Basin"' in text
    assert "--table" in text
    assert '--station-region "LA Basin"' in text
    assert '--event-region "Santa Monica Mountains"' in text
    assert "--components R" in text
    assert "--time-limit-s 60" in text
    assert "--max-records 80" in text
    assert "--max-traces 12" in text
    assert "--auto-port" in text
    assert "--kwargs dep=" not in text
    assert " indep=" not in text
    assert " colorby=" not in text
    assert " compare_to=" not in text
    assert "--kwargs" not in text
    assert "station_region=" not in text
    assert "event_region=" not in text
    assert "table=true" not in text
    assert "gain=2.0" not in text
    assert "xlim_s=" not in text
    assert "max_time_s=" not in text
    assert "lowpass_hz=" not in text


def test_cli_workflow_explanatory_text_is_not_in_bash_blocks():
    """Prose near shell examples should not be indented into bash literal blocks."""

    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "examples" / "cli_workflow.rst").read_text(encoding="utf-8")
    prose_starts = (
        "The band-score plot defaults",
        "Add ``--write-sidecar``",
        "metadata records ``plot_rows_role``",
    )
    for line in text.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(prefix) for prefix in prose_starts):
            assert not line.startswith("   "), line


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


def test_cli_plot_uses_saved_config_defaults_without_path_flags(tmp_path, monkeypatch, capsys):
    """Registered plot commands should honor a saved default config."""

    settings = tmp_path / "settings" / "svtk-config.json"
    config = tmp_path / "spatial-vtk.yaml"
    table_dir = tmp_path / "outputs" / "tables"
    table_dir.mkdir(parents=True)
    metrics = table_dir / "metrics_long.csv"
    metrics.write_text("band,log2_residual,metric\n1-2 sec,0.5,PGA\n", encoding="utf-8")
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
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
    monkeypatch.setenv("SVTK_CLI_CONFIG_FILE", str(settings))

    assert main(["config", "set", str(config)]) == 0
    assert main(["plot", "metrics", "band-score-distribution", "--score-col", "log2_residual"]) == 0

    captured = capsys.readouterr()
    expected_output = tmp_path / "outputs" / "figures" / "band_score_distribution.png"
    assert seen["rows"] == 1
    assert seen["output_path"] == expected_output
    assert seen["kwargs"]["score_col"] == "log2_residual"
    assert str(expected_output) in captured.out


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
                "--no-connect-points",
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
    assert seen["kwargs"]["connect_points"] is False
    assert captured.out.strip() == str(expected_output)


def test_cli_model_metric_heatmap_uses_metrics_long_config_default(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    table_dir = tmp_path / "outputs" / "tables"
    table_dir.mkdir(parents=True)
    metrics = table_dir / "metrics_long.csv"
    metrics.write_text(
        "metric,band,model,component,log2_residual\n"
        "PGA,1-2 sec,m1,Z,0.5\n"
        "PGA,1-2 sec,m2,Z,-0.2\n",
        encoding="utf-8",
    )
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

    import spatial_vtk.metrics.plot as metrics_plot

    def fake_plot_model_metric_heatmap(summary_df, output_path=None, **kwargs):
        seen["columns"] = list(summary_df.columns)
        seen["rows"] = len(summary_df)
        seen["output_path"] = Path(output_path)
        seen["kwargs"] = kwargs
        seen["output_path"].parent.mkdir(parents=True, exist_ok=True)
        seen["output_path"].write_text("figure", encoding="utf-8")
        return seen["output_path"]

    monkeypatch.setattr(metrics_plot, "plot_model_metric_heatmap", fake_plot_model_metric_heatmap)

    assert main(["plot", "metrics", "model-metric-heatmap", "--config", str(config)]) == 0
    captured = capsys.readouterr()
    expected_output = tmp_path / "outputs" / "figures" / "model_metric_heatmap.png"
    assert seen["rows"] == 2
    assert "log2_residual" in seen["columns"]
    assert seen["output_path"] == expected_output
    assert "value_col" not in seen["kwargs"]
    assert captured.out.strip() == str(expected_output)


def test_cli_pattern_similarity_uses_registered_table_and_bin_label(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    table_dir = tmp_path / "outputs" / "tables"
    table_dir.mkdir(parents=True)
    pattern_rows = table_dir / "pattern_similarity_station_anomalies.csv"
    pattern_rows.write_text(
        "station_name,dataset,metric,bin,value\n"
        "S1,observed,PGA,1-2 sec,0.2\n"
        "S1,synthetic,PGA,1-2 sec,0.1\n",
        encoding="utf-8",
    )
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

    def fake_plot_pattern_similarity(stations, output_path=None, **kwargs):
        seen["rows"] = len(stations)
        seen["output_path"] = Path(output_path)
        seen["kwargs"] = kwargs
        seen["output_path"].parent.mkdir(parents=True, exist_ok=True)
        seen["output_path"].write_text("figure", encoding="utf-8")
        return seen["output_path"]

    monkeypatch.setattr(spatial_plot, "plot_pattern_similarity", fake_plot_pattern_similarity)

    assert (
        main(
            [
                "plot",
                "spatial",
                "pattern-similarity",
                "--config",
                str(config),
                "--metric",
                "PGA",
                "--bin-label",
                "1-2 sec",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    expected_output = tmp_path / "outputs" / "figures" / "pattern_similarity.png"
    assert seen["rows"] == 2
    assert seen["output_path"] == expected_output
    assert seen["kwargs"]["metric"] == "PGA"
    assert seen["kwargs"]["bin_label"] == "1-2 sec"
    assert captured.out.strip() == str(expected_output)


def test_cli_data_synthetic_availability_uses_qc_availability_default(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    table_dir = tmp_path / "outputs" / "tables"
    table_dir.mkdir(parents=True)
    availability = table_dir / "qc_availability.csv"
    availability.write_text(
        "event_id,station,observed_available,synthetic_available\n"
        "e1,S1,True,True\n",
        encoding="utf-8",
    )
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

    import spatial_vtk.visualize.qc as qc_plot

    def fake_plot_data_synthetic_availability(availability_df, output_path=None, **kwargs):
        seen["rows"] = len(availability_df)
        seen["output_path"] = Path(output_path)
        seen["columns"] = list(availability_df.columns)
        seen["kwargs"] = kwargs
        seen["output_path"].parent.mkdir(parents=True, exist_ok=True)
        seen["output_path"].write_text("figure", encoding="utf-8")
        return seen["output_path"]

    monkeypatch.setattr(qc_plot, "plot_data_synthetic_availability", fake_plot_data_synthetic_availability)

    assert main(["visualize", "qc", "data-synthetic-availability", "--config", str(config)]) == 0
    captured = capsys.readouterr()
    expected_output = tmp_path / "outputs" / "figures" / "data_synthetic_availability.png"
    assert seen["rows"] == 1
    assert seen["output_path"] == expected_output
    assert "observed_available" in seen["columns"]
    assert "synthetic_available" in seen["columns"]
    assert captured.out.strip() == str(expected_output)


def test_cli_flexible_metric_plot_uses_first_class_dep_indep_flags(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    table_dir = tmp_path / "outputs" / "tables"
    table_dir.mkdir(parents=True)
    metrics = table_dir / "metrics_long.csv"
    metrics.write_text(
        "metric,band,model,component,distance,log2_residual\nPGA,1-2 sec,m1,Z,10,0.5\n",
        encoding="utf-8",
    )
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

    import spatial_vtk.spatial.plot as spatial_plot

    def fake_scatterplot(data, output_path=None, **kwargs):
        seen["rows"] = len(data)
        seen["output_path"] = Path(output_path)
        seen["kwargs"] = kwargs
        seen["output_path"].parent.mkdir(parents=True, exist_ok=True)
        seen["output_path"].write_text("figure", encoding="utf-8")
        return seen["output_path"]

    monkeypatch.setattr(spatial_plot, "scatterplot", fake_scatterplot)

    assert (
        main(
            [
                "plot",
                "metrics",
                "scatterplot",
                "--config",
                str(config),
                "--dep",
                "PGA",
                "--dep",
                "PGV",
                "--indep",
                "distance",
                "--colorby",
                "dep",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    expected_output = tmp_path / "outputs" / "figures" / "scatterplot.png"
    assert seen["rows"] == 1
    assert seen["output_path"] == expected_output
    assert seen["kwargs"]["dep"] == ["PGA", "PGV"]
    assert seen["kwargs"]["indep"] == "distance"
    assert seen["kwargs"]["colorby"] == "dep"
    assert captured.out.strip() == str(expected_output)


def test_cli_metric_boxplot_uses_first_class_table_flag(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    table_dir = tmp_path / "outputs" / "tables"
    table_dir.mkdir(parents=True)
    metrics = table_dir / "metrics_long.csv"
    metrics.write_text(
        "metric,band,model,station_geojson_labels,log2_residual\nPGA,1-2 sec,m1,LA Basin,0.5\n",
        encoding="utf-8",
    )
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

    import spatial_vtk.spatial.plot as spatial_plot

    def fake_boxplot(data, output_path=None, **kwargs):
        seen["rows"] = len(data)
        seen["output_path"] = Path(output_path)
        seen["kwargs"] = kwargs
        seen["output_path"].parent.mkdir(parents=True, exist_ok=True)
        seen["output_path"].write_text("figure", encoding="utf-8")
        return seen["output_path"]

    monkeypatch.setattr(spatial_plot, "boxplot", fake_boxplot)

    assert (
        main(
            [
                "plot",
                "metrics",
                "boxplot",
                "--config",
                str(config),
                "--dep",
                "PGA",
                "--indep",
                "station_geojson_labels",
                "--compare-to",
                "LA Basin",
                "--table",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    expected_output = tmp_path / "outputs" / "figures" / "boxplot.png"
    assert seen["rows"] == 1
    assert seen["output_path"] == expected_output
    assert seen["kwargs"]["compare_to"] == "LA Basin"
    assert seen["kwargs"]["table"] is True
    assert captured.out.strip() == str(expected_output)


def test_cli_waveform_record_section_uses_first_class_waveform_flags(tmp_path, monkeypatch, capsys):
    records = tmp_path / "records.csv"
    records.write_text(
        "station,distance_km,component,observed,synthetic\n"
        "STA,10,R,\"[0,1,0]\",\"[0,0.5,0]\"\n",
        encoding="utf-8",
    )
    output = tmp_path / "figures" / "record_section.png"
    seen = {}

    import spatial_vtk.visualize.waveforms as waveforms

    def fake_plot_observed_synthetic_record_section(records_df, output_path=None, **kwargs):
        seen["rows"] = len(records_df)
        seen["output_path"] = Path(output_path)
        seen["kwargs"] = kwargs
        seen["output_path"].parent.mkdir(parents=True, exist_ok=True)
        seen["output_path"].write_text("figure", encoding="utf-8")
        return seen["output_path"]

    monkeypatch.setattr(waveforms, "plot_observed_synthetic_record_section", fake_plot_observed_synthetic_record_section)

    assert (
        main(
            [
                "visualize",
                "waveforms",
                "observed-synthetic-record-section",
                "--input",
                str(records),
                "--output",
                str(output),
                "--components",
                "R",
                "--scale",
                "2.0",
                "--time-limit-s",
                "60",
                "--max-records",
                "80",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert seen["rows"] == 1
    assert seen["output_path"] == output
    assert seen["kwargs"]["components"] == "R"
    assert seen["kwargs"]["scale"] == 2.0
    assert seen["kwargs"]["time_limit_s"] == 60.0
    assert seen["kwargs"]["max_records"] == 80
    assert captured.out.strip() == str(output)


def test_cli_waveform_plot_uses_configured_event_station_records(tmp_path, monkeypatch, capsys):
    tables = tmp_path / "outputs" / "tables"
    tables.mkdir(parents=True)
    records = tables / "event_station_records.csv"
    records.write_text(
        "event_id,station,distance_km,component,observed,synthetic\n"
        "ev1,STA,10,R,\"[0,1,0]\",\"[0,0.5,0]\"\n",
        encoding="utf-8",
    )
    config = tmp_path / "spatial-vtk.yaml"
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  tables: outputs/tables
  figures: outputs/figures
""",
        encoding="utf-8",
    )
    seen = {}

    import spatial_vtk.visualize.waveforms as waveforms

    def fake_plot_observed_synthetic_record_section(records_df, output_path=None, **kwargs):
        seen["rows"] = len(records_df)
        seen["output_path"] = Path(output_path)
        seen["kwargs"] = kwargs
        seen["output_path"].parent.mkdir(parents=True, exist_ok=True)
        seen["output_path"].write_text("figure", encoding="utf-8")
        return seen["output_path"]

    monkeypatch.setattr(waveforms, "plot_observed_synthetic_record_section", fake_plot_observed_synthetic_record_section)

    assert (
        main(
            [
                "visualize",
                "waveforms",
                "observed-synthetic-record-section",
                "--config",
                str(config),
                "--components",
                "R",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    expected_output = tmp_path / "outputs" / "figures" / "observed_synthetic_record_section.png"
    assert seen["rows"] == 1
    assert seen["output_path"] == expected_output
    assert seen["kwargs"]["components"] == "R"
    assert captured.out.strip() == str(expected_output)


def test_cli_context_trace_comparison_uses_configured_event_station_records(tmp_path, monkeypatch, capsys):
    tables = tmp_path / "outputs" / "tables"
    tables.mkdir(parents=True)
    records = tables / "event_station_records.csv"
    records.write_text(
        "event_id,station,distance_km,component\n"
        "ev1,STA,10,R\n",
        encoding="utf-8",
    )
    config = tmp_path / "spatial-vtk.yaml"
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  tables: outputs/tables
  figures: outputs/figures
""",
        encoding="utf-8",
    )
    seen = {}

    import spatial_vtk.visualize.context as context

    def fake_plot_event_trace_comparison(records_df, output_path=None, **kwargs):
        seen["rows"] = len(records_df)
        seen["output_path"] = Path(output_path)
        seen["output_path"].parent.mkdir(parents=True, exist_ok=True)
        seen["output_path"].write_text("figure", encoding="utf-8")
        return seen["output_path"]

    monkeypatch.setattr(context, "plot_event_trace_comparison", fake_plot_event_trace_comparison)

    assert main(["visualize", "context", "event-trace-comparison", "--config", str(config)]) == 0
    captured = capsys.readouterr()
    expected_output = tmp_path / "outputs" / "figures" / "event_trace_comparison.png"
    assert seen["rows"] == 1
    assert seen["output_path"] == expected_output
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


def test_cli_event_residual_map_uses_first_class_region_flags(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    table_dir = tmp_path / "outputs" / "tables"
    table_dir.mkdir(parents=True)
    path_table = table_dir / "path_table.csv"
    path_table.write_text(
        "event_id,station,sta_lon,sta_lat,metric,residual,station_geojson_labels,event_geojson_labels\n"
        "EV,STA,-118,34,PGA,0.2,LA Basin,Santa Monica Mountains\n",
        encoding="utf-8",
    )
    config.write_text(
        """
project:
  root_dir: .
outputs:
  tables: outputs/tables
  figures: outputs/figures
  artifacts:
    path_table:
      filename: path_table.csv
""",
        encoding="utf-8",
    )
    seen = {}

    import spatial_vtk.spatial.map as spatial_map
    import spatial_vtk.spatial.map.path.residuals as residual_maps

    def fake_plot_event_residual_map(df, output_path=None, **kwargs):
        seen["rows"] = len(df)
        seen["output_path"] = Path(output_path)
        seen["kwargs"] = kwargs
        seen["output_path"].parent.mkdir(parents=True, exist_ok=True)
        seen["output_path"].write_text("figure", encoding="utf-8")
        return seen["output_path"]

    monkeypatch.setattr(residual_maps, "plot_event_residual_map", fake_plot_event_residual_map)
    monkeypatch.setattr(spatial_map, "plot_event_residual_map", fake_plot_event_residual_map)

    assert (
        main(
            [
                "map",
                "spatial",
                "event-residual",
                "--config",
                str(config),
                "--metric",
                "PGA",
                "--value-col",
                "residual",
                "--station-region",
                "LA Basin",
                "--event-region",
                "Santa Monica Mountains",
                "--no-basemap",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    expected_output = tmp_path / "outputs" / "figures" / "event_residual_map.png"
    assert seen["rows"] == 1
    assert seen["output_path"] == expected_output
    assert seen["kwargs"]["metric"] == "PGA"
    assert seen["kwargs"]["value_col"] == "residual"
    assert seen["kwargs"]["station_regions"] == "LA Basin"
    assert seen["kwargs"]["event_regions"] == "Santa Monica Mountains"
    assert seen["kwargs"]["add_basemap"] is False
    assert captured.out.strip() == str(expected_output)


def test_cli_pca_mode_map_uses_first_class_mode_flag(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    table_dir = tmp_path / "outputs" / "tables"
    table_dir.mkdir(parents=True)
    pca_scores = table_dir / "pca_station_scores.csv"
    pca_scores.write_text("station,lon,lat,PC1_score\nSTA,-118,34,0.2\n", encoding="utf-8")
    config.write_text(
        """
project:
  root_dir: .
outputs:
  tables: outputs/tables
  figures: outputs/figures
  artifacts:
    pca_station_scores:
      filename: pca_station_scores.csv
""",
        encoding="utf-8",
    )
    seen = {}

    import spatial_vtk.spatial.map as spatial_map
    import spatial_vtk.spatial.map.pca as pca_maps

    def fake_plot_pca_mode_map(station_scores_df, output_path=None, **kwargs):
        seen["rows"] = len(station_scores_df)
        seen["output_path"] = Path(output_path)
        seen["kwargs"] = kwargs
        seen["output_path"].parent.mkdir(parents=True, exist_ok=True)
        seen["output_path"].write_text("figure", encoding="utf-8")
        return seen["output_path"]

    monkeypatch.setattr(pca_maps, "plot_pca_mode_map", fake_plot_pca_mode_map)
    monkeypatch.setattr(spatial_map, "plot_pca_mode_map", fake_plot_pca_mode_map)

    assert main(["map", "spatial", "pca-mode", "--config", str(config), "--mode", "PC1", "--no-basemap"]) == 0
    captured = capsys.readouterr()
    expected_output = tmp_path / "outputs" / "figures" / "pca_mode_map.png"
    assert seen["rows"] == 1
    assert seen["output_path"] == expected_output
    assert seen["kwargs"]["mode"] == "PC1"
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


def test_cli_prepare_metadata_uses_configured_defaults(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    tables = tmp_path / "outputs" / "tables"
    stations = inputs / "stations.csv"
    events = inputs / "events.csv"
    config = tmp_path / "spatial-vtk.yaml"
    pd.DataFrame({"stationcode": ["sta1"], "station_latitude": [34.0], "station_longitude": [-118.0]}).to_csv(stations, index=False)
    pd.DataFrame({"event_title": ["ev1"], "event_latitude": [33.9], "event_longitude": [-118.2]}).to_csv(events, index=False)
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
paths:
  station_metadata: inputs/stations.csv
  event_metadata: inputs/events.csv
outputs:
  tables: outputs/tables
""",
        encoding="utf-8",
    )

    assert main(["io", "prepare-stations", "--config", str(config)]) == 0
    assert main(["io", "prepare-events", "--config", str(config)]) == 0

    prepared_stations = pd.read_csv(tables / "prepared_stations.csv")
    prepared_events = pd.read_csv(tables / "prepared_events.csv")
    assert prepared_stations.loc[0, "station"] == "STA1"
    assert prepared_events.loc[0, "event_id"] == "ev1"


def test_cli_prepare_event_stations_uses_configured_defaults(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    tables = tmp_path / "outputs" / "tables"
    stations = inputs / "stations.csv"
    events = inputs / "events.csv"
    pairs = inputs / "event_stations.csv"
    config = tmp_path / "spatial-vtk.yaml"
    pd.DataFrame({"stationcode": ["sta1"], "station_latitude": [34.0], "station_longitude": [-118.0]}).to_csv(stations, index=False)
    pd.DataFrame({"event_title": ["ev1"], "event_latitude": [33.9], "event_longitude": [-118.2]}).to_csv(events, index=False)
    pd.DataFrame({"event": ["ev1"], "site": ["sta1"]}).to_csv(pairs, index=False)
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
paths:
  station_metadata: inputs/stations.csv
  event_metadata: inputs/events.csv
  event_station_table: inputs/event_stations.csv
outputs:
  tables: outputs/tables
""",
        encoding="utf-8",
    )

    assert main(["io", "prepare-event-stations", "--config", str(config)]) == 0

    prepared = pd.read_csv(tables / "event_station_records.csv")
    assert len(prepared) == 1
    assert prepared.loc[0, "event_id"] == "ev1"
    assert prepared.loc[0, "station"] == "STA1"
    assert {"lat", "lon", "event_lat", "event_lon"} <= set(prepared.columns)


def test_cli_prepare_event_stations_builds_all_pairs_without_input_table(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    tables = tmp_path / "outputs" / "tables"
    stations = inputs / "stations.csv"
    events = inputs / "events.csv"
    config = tmp_path / "spatial-vtk.yaml"
    pd.DataFrame({"station": ["STA1", "STA2"], "lat": [34.0, 34.1], "lon": [-118.0, -118.1]}).to_csv(stations, index=False)
    pd.DataFrame({"event_id": ["ev1", "ev2"], "event_lat": [33.9, 34.2], "event_lon": [-118.2, -118.3]}).to_csv(events, index=False)
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
paths:
  station_metadata: inputs/stations.csv
  event_metadata: inputs/events.csv
outputs:
  tables: outputs/tables
""",
        encoding="utf-8",
    )

    assert main(["io", "prepare-event-stations", "--config", str(config)]) == 0

    prepared = pd.read_csv(tables / "event_station_records.csv")
    assert len(prepared) == 4
    assert set(prepared["event_id"]) == {"ev1", "ev2"}
    assert set(prepared["station"]) == {"STA1", "STA2"}


def test_cli_preprocess_waveforms_uses_configured_records_default(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace

    tables = tmp_path / "outputs" / "tables"
    tables.mkdir(parents=True)
    records = tables / "event_station_records.csv"
    records.write_text("event_id,station,observed_waveform\nE1,STA1,obs.mseed\n", encoding="utf-8")
    config = tmp_path / "spatial-vtk.yaml"
    config.write_text(
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

    import spatial_vtk.io as io

    def fake_preprocess_waveform_files(event_station_records, output_root=None, **kwargs):
        seen["records"] = Path(event_station_records)
        seen["output_root"] = output_root
        seen["config_root"] = kwargs["config"].root_dir
        seen["continue_on_error"] = kwargs["continue_on_error"]
        return SimpleNamespace(
            event_station_path=tmp_path / "outputs" / "preprocessed_waveforms" / "metadata" / "event_station_records_preprocessed.csv",
            manifest_path=tmp_path / "outputs" / "preprocessed_waveforms" / "metadata" / "preprocessing_manifest.csv",
            trace_metadata_path=tmp_path / "outputs" / "preprocessed_waveforms" / "metadata" / "trace_metadata_preprocessed.csv",
            manifest=pd.DataFrame({"event_id": ["E1"]}),
        )

    monkeypatch.setattr(io, "preprocess_waveform_files", fake_preprocess_waveform_files)

    assert main(["io", "preprocess-waveforms", "--config", str(config), "--continue-on-error"]) == 0
    captured = capsys.readouterr()
    assert seen["records"] == records
    assert seen["output_root"] is None
    assert seen["config_root"] == tmp_path
    assert seen["continue_on_error"] is True
    assert "event_station_records:" in captured.out
    assert "files: 1" in captured.out


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


def test_cli_qc_manual_queue_uses_saved_config_defaults(tmp_path, monkeypatch):
    """Manual QC queue export should use configured trace and output tables."""

    settings = tmp_path / "settings" / "svtk-config.json"
    config = tmp_path / "spatial-vtk.yaml"
    tables = tmp_path / "outputs" / "tables"
    tables.mkdir(parents=True)
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
""",
        encoding="utf-8",
    )
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
    ).to_csv(tables / "qc_trace_summary.csv", index=False)
    monkeypatch.setenv("SVTK_CLI_CONFIG_FILE", str(settings))

    assert main(["config", "set", str(config)]) == 0
    assert main(["qc", "manual-queue", "--component", "R"]) == 0

    queue = pd.read_csv(tables / "manual_review_queue.csv")
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
                "--no-qc",
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
                "--no-qc",
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


def test_cli_metrics_plan_uses_configured_workflow_defaults(tmp_path):
    config = tmp_path / "spatial-vtk.yaml"
    tables = tmp_path / "outputs" / "tables"
    tables.mkdir(parents=True)
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
metrics:
  metrics: [PGA]
  components: [Z]
  passbands: [[1, 2]]
  models: [m1]
""",
        encoding="utf-8",
    )
    inventory = {
        "event_id": ["ev1", "ev2"],
        "station": ["STA1", "STA2"],
        "component": ["Z", "Z"],
        "waveform_path": ["obs1.npz", "obs2.npz"],
        "dt": [0.01, 0.01],
    }
    pd.DataFrame(inventory).to_parquet(tables / "observed_metric_inventory.parquet", index=False)
    pd.DataFrame({**inventory, "model": ["m1", "m1"], "waveform_path": ["syn1.npz", "syn2.npz"]}).to_parquet(
        tables / "synthetic_metric_inventory.parquet",
        index=False,
    )
    pd.DataFrame(
        [
            {
                "source": source,
                "event_id": "ev1",
                "station": "STA1",
                "component": "Z",
                "passband": "1-2 sec",
                "metric_group": "amplitude",
                "metric": "PGA",
                "period_s": np.nan,
                "qc_status": "pass",
            }
            for source in ("observed", "synthetic")
        ]
    ).to_parquet(tables / "qc_inventory_overlap.parquet", index=False)

    assert main(["metrics", "plan", "--config", str(config), "--manifest", "--batch-count", "1"]) == 0

    manifest_path = tables / "metric_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["tasks"]) == 1
    assert manifest["qc_table"].endswith("qc_inventory_overlap.parquet")
    assert manifest["batches"][0]["output_path"].endswith("outputs/metric_batches/metrics_batch_0000.csv")


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


def test_cli_metrics_inventories_use_configured_defaults(tmp_path):
    config = tmp_path / "spatial-vtk.yaml"
    trace_dir = tmp_path / "outputs" / "preprocessed_waveforms" / "metadata"
    trace_dir.mkdir(parents=True)
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
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
    ).to_csv(trace_dir / "trace_metadata_preprocessed.csv", index=False)

    assert main(["metrics", "inventories", "--config", str(config), "--overwrite"]) == 0

    observed = pd.read_parquet(tmp_path / "outputs" / "tables" / "observed_metric_inventory.parquet")
    synthetic = pd.read_parquet(tmp_path / "outputs" / "tables" / "synthetic_metric_inventory.parquet")
    assert observed.loc[0, "waveform_path"] == "processed_obs.npz"
    assert synthetic.loc[0, "waveform_path"] == "synthetic_source.mseed"


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


def test_cli_metrics_cache_and_merge_use_configured_defaults(tmp_path):
    obs = tmp_path / "obs.npz"
    syn = tmp_path / "syn.npz"
    tables = tmp_path / "outputs" / "tables"
    tables.mkdir(parents=True)
    config = tmp_path / "spatial-vtk.yaml"
    _write_cli_npz(obs, [0.0, 1.0, 0.0], station="ABC", channel="HNZ")
    _write_cli_npz(syn, [0.0, 0.5, 0.0], station="ABC", channel="HNZ")
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
metrics:
  slurm:
    python_command: python
""",
        encoding="utf-8",
    )
    (tables / "metric_manifest.json").write_text(
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

    assert main(["metrics", "cache-waveforms", "--config", str(config)]) == 0
    assert (tables / "metric_manifest_cached.json").exists()
    assert main(["metrics", "run-batch", "--config", str(config), "--batch-index", "0"]) == 0

    assert main(["metrics", "merge-batches", "--config", str(config)]) == 0
    assert (tables / "metric_rows.parquet").exists()


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


def test_cli_metrics_slurm_uses_configured_defaults(tmp_path, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    tables = tmp_path / "outputs" / "tables"
    tables.mkdir(parents=True)
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
metrics:
  slurm:
    python_command: python
    max_concurrent: 2
""",
        encoding="utf-8",
    )
    (tables / "metric_manifest_cached.json").write_text(
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

    assert main(["metrics", "slurm", "--config", str(config)]) == 0

    captured = capsys.readouterr()
    assert "Wrote metric Slurm script" in captured.out
    assert (tmp_path / "outputs" / "slurm" / "step03_run_metrics.slurm").exists()


def test_cli_qc_slurm_uses_configured_defaults(tmp_path, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    tables = tmp_path / "outputs" / "tables"
    tables.mkdir(parents=True)
    event_stations = tables / "event_station_records.csv"
    event_stations.write_text("event_id,station\nE1,STA1\n", encoding="utf-8")
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
compute:
  slurm:
    python_command: python
qc:
  slurm:
    max_concurrent: 1
""",
        encoding="utf-8",
    )

    assert main(["qc", "slurm", "--config", str(config)]) == 0

    captured = capsys.readouterr()
    script = tmp_path / "outputs" / "slurm" / "build_qc_inventory.slurm"
    assert str(script) in captured.out
    text = script.read_text(encoding="utf-8")
    assert "--event-stations" in text
    assert str(event_stations.resolve()) in text
    assert "-m spatial_vtk.qc.build.slurm" in text


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
    assert launched["auto_port"] is False
    assert launched["proxy_mode"] is True


def test_cli_dashboard_metrics_reports_auto_selected_port(tmp_path, monkeypatch, capsys):
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
        spatial_vtk_server_port = 8556

    def fake_launch_metrics_dashboard(**kwargs):
        launched.update(kwargs)
        return FakeProcess()

    monkeypatch.setattr(
        "spatial_vtk.visualize.dashboard.launch_metrics_dashboard",
        fake_launch_metrics_dashboard,
    )

    assert main(["dashboard", "metrics", "--config", str(config), "--port", "8555", "--auto-port"]) == 0

    captured = capsys.readouterr()
    assert launched["server_port"] == 8555
    assert launched["auto_port"] is True
    assert "Metrics dashboard auto-port: requested 8555, using 8556" in captured.out
    assert "http://127.0.0.1:8556" in captured.out


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


def test_cli_dashboard_status_reports_configured_paths_without_launching(tmp_path, capsys):
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

    assert main(["dashboard", "status", "--config", str(config), "--json"]) == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    names = {row["name"] for row in payload["status"]}
    assert payload["reason"] == "missing_inputs"
    assert payload["should_build_dashboard_outputs"] is False
    assert "metrics_long.parquet is not ready yet" in payload["message"]
    assert "metrics_long_path" in names
    assert "qc_trace_summary_path" in names
    assert "qc_inventory_overlap_path" in names
    assert "model_metric_band_summary_path" in names
    assert not (tmp_path / "outputs" / "dashboards").exists()


def test_cli_dashboard_status_human_output_includes_readiness(tmp_path, capsys):
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

    assert main(["dashboard", "status", "--config", str(config)]) == 0

    captured = capsys.readouterr()
    assert "Dashboard outputs current: False" in captured.out
    assert "metrics_long_path" in captured.out
    assert "model_metric_band_summary_path" in captured.out


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
    assert "default input from config: metrics_long" in captured.out
    assert "model-metric-heatmap" in captured.out
    assert "default output from config: band_score_distribution" in captured.out
    assert "default output from config: model_metric_heatmap" in captured.out
    assert "from config from config" not in captured.out


def test_cli_spatial_plot_list_includes_pattern_similarity_defaults(capsys):
    assert main(["plot", "spatial", "list"]) == 0
    captured = capsys.readouterr()
    assert "pattern-similarity" in captured.out
    assert "default input from config: pattern_similarity_station_anomalies" in captured.out
    assert "default output from config: pattern_similarity" in captured.out
