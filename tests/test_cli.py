from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from spatial_vtk.cli import main
from spatial_vtk.cli import _dashboard_cli_readiness_columns


def test_cli_help(capsys):
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "Spatial validation tools" in captured.out


def test_cli_main_reports_missing_runtime_dependency(monkeypatch, capsys):
    """Missing runtime dependencies should produce install guidance, not a traceback."""

    import argparse
    import spatial_vtk.cli as cli

    parser = argparse.ArgumentParser(prog="svtk")

    def missing_dependency_handler(_args):
        raise ModuleNotFoundError("No module named 'pandas'", name="pandas")

    parser.set_defaults(handler=missing_dependency_handler)
    monkeypatch.setattr(cli, "build_parser", lambda: parser)

    assert cli.main([]) == 2
    captured = capsys.readouterr()
    assert "Missing Python dependency 'pandas' required by this command." in captured.err
    assert "python -m pip install -e" in captured.err
    assert "Traceback" not in captured.err


def test_cli_missing_config_reports_config_before_optional_dependencies(tmp_path, monkeypatch, capsys):
    """Config-required workflow commands should report missing config before optional imports."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SVTK_CONFIG_FILE", raising=False)
    monkeypatch.setenv("SVTK_CLI_CONFIG_FILE", str(tmp_path / "missing-settings.json"))

    assert main(["metrics", "run"]) == 2

    captured = capsys.readouterr()
    assert "No Spatial-VTK config was found" in captured.err
    assert "Pass --config or run 'svtk config set PATH'" in captured.err
    assert "Missing Python dependency" not in captured.err
    assert "No module named" not in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    "command",
    [
        ["io", "prepare-stations"],
        ["io", "prepare-events"],
        ["io", "prepare-event-stations"],
        ["io", "inventory"],
        ["io", "preprocess-waveforms"],
        ["qc", "build"],
        ["qc", "manual-queue"],
        ["qc", "slurm"],
        ["qc", "summaries"],
        ["spatial", "status"],
        ["spatial", "summaries"],
        ["spatial", "derived-outputs"],
        ["spatial", "geojson-summaries"],
        ["spatial", "corridors"],
        ["dashboard", "status"],
        ["dashboard", "metrics"],
        ["dashboard", "qc"],
    ],
)
def test_config_backed_cli_commands_validate_config_before_optional_imports(
    command, tmp_path, monkeypatch, capsys
):
    """Config-backed workflow commands should fail on missing config before heavy imports."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SVTK_CONFIG_FILE", raising=False)
    monkeypatch.setenv("SVTK_CLI_CONFIG_FILE", str(tmp_path / "missing-settings.json"))

    assert main(command) == 2

    captured = capsys.readouterr()
    assert "Spatial-VTK config was found" in captured.err
    assert "Missing Python dependency" not in captured.err
    assert "No module named" not in captured.err
    assert "Traceback" not in captured.err


def test_cli_version(capsys):
    assert main(["--version"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip()


def test_dashboard_status_cli_keeps_rich_readiness_columns():
    """Human dashboard status output should expose the same core readiness fields as notebooks."""

    status = pd.DataFrame(
        {
            "item_type": ["summary_table"],
            "item": ["station_rollup"],
            "artifact_label": ["station_rollup dashboard summary table"],
            "dashboard_tabs": ["Stations"],
            "required_columns": ["station, model, metric"],
            "ready": [False],
            "readiness": ["no_value_data"],
            "row_count": [12],
            "file_count": [""],
            "map_ready": [True],
            "missing_columns": [""],
            "missing_map_columns": [""],
            "value_columns": ["med_log2_residual, med_gof_score"],
            "nonempty_value_columns": ["med_log2_residual"],
            "value_families": ["residual, score/gof"],
            "nonempty_value_families": ["residual"],
            "message": ["station_rollup summary has rows but no finite dashboard value columns."],
            "map_message": ["station_rollup map coordinates are ready."],
            "suggested_action": ["Run write_configured_dashboard_datasets."],
            "path": ["/tmp/station_rollup.parquet"],
            "extra_private_column": ["not shown"],
        }
    )

    shown = _dashboard_cli_readiness_columns(status)

    assert "required_columns" in shown.columns
    assert "missing_columns" in shown.columns
    assert "missing_map_columns" in shown.columns
    assert "value_columns" in shown.columns
    assert "nonempty_value_columns" in shown.columns
    assert "value_families" in shown.columns
    assert "nonempty_value_families" in shown.columns
    assert "map_message" in shown.columns
    assert "extra_private_column" not in shown.columns
    assert shown.loc[0, "value_columns"] == "med_log2_residual, med_gof_score"
    assert shown.loc[0, "nonempty_value_columns"] == "med_log2_residual"
    assert shown.loc[0, "nonempty_value_families"] == "residual"


def test_cli_config_outputs_lists_registry_with_resolved_paths(tmp_path, capsys):
    """CLI users should be able to discover registered output keys."""

    config = tmp_path / "spatial-vtk.yaml"
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
  figures: outputs/figures
  dashboards: outputs/dashboards
""",
        encoding="utf-8",
    )

    assert main(["config", "outputs", "--config", str(config), "--kind", "table"]) == 0
    text = capsys.readouterr().out
    assert "metrics_long" in text
    assert "metrics_long.parquet" in text
    assert str(tmp_path / "outputs" / "tables" / "metrics_long.parquet") in text
    assert "station_metric_map" not in text

    assert main(["config", "outputs", "--kind", "dashboard", "--no-paths", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    keys = {row["key"] for row in payload["outputs"]}
    assert {"metrics_dashboard", "dashboard_summaries"} <= keys
    assert "path" not in payload["outputs"][0]


def test_cli_spatial_summaries_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["spatial", "summaries", "--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    help_text = " ".join(captured.out.split())
    assert "Build standard spatial-statistics summary tables" in captured.out
    assert "--station-metadata" in captured.out
    assert "--station-metadata-table" in captured.out
    assert "--metrics-table" in captured.out
    assert "--checkpoint-dir" in captured.out
    assert "--no-resume" in captured.out
    assert "svtk spatial summaries [-h] [--metrics-table PATH] [--config PATH]" in captured.out
    assert "[--station-metadata-table PATH] [--checkpoint-dir DIR]" in captured.out
    assert "default config is set with 'svtk config set'" in help_text
    assert "Prefer --metrics-table; --metrics is a legacy alias" in help_text
    assert "Prefer --station-metadata-table; --station-metadata is a legacy alias" in help_text


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
    monkeypatch.setattr("spatial_vtk.spatial.run_spatial_statistics_workflow", fake_run_spatial_statistics_workflow)

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


def test_cli_spatial_summaries_accepts_clear_table_aliases(tmp_path, monkeypatch):
    """Spatial summaries should accept explicit table-named input aliases."""

    from types import SimpleNamespace

    config = tmp_path / "spatial-vtk.yaml"
    metrics = tmp_path / "metrics_long.parquet"
    stations = tmp_path / "prepared_stations.csv"
    metrics.write_bytes(b"metrics")
    stations.write_text("station,lon,lat\nSTA,-118,34\n", encoding="utf-8")
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

    def fake_run_spatial_statistics_workflow(metrics=None, **kwargs):
        seen["metrics"] = metrics
        seen.update(kwargs)
        return SimpleNamespace(metrics=("PGA",), elapsed_s=0.5, paths={}, failures=())

    monkeypatch.setattr("spatial_vtk.spatial.run_spatial_statistics_workflow", fake_run_spatial_statistics_workflow)

    assert (
        main(
            [
                "spatial",
                "summaries",
                "--config",
                str(config),
                "--metrics-table",
                str(metrics),
                "--station-metadata-table",
                str(stations),
                "--no-resume",
            ]
        )
        == 0
    )

    assert seen["metrics"] == str(metrics)
    assert seen["station_metadata"] == str(stations)
    assert seen["resume"] is False


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
    monkeypatch.setattr("spatial_vtk.spatial.run_spatial_derived_outputs_workflow", fake_run_spatial_derived_outputs_workflow)

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


def test_cli_spatial_derived_outputs_accepts_clear_table_aliases(tmp_path, monkeypatch):
    """Spatial derived outputs should accept explicit table-named input aliases."""

    from types import SimpleNamespace

    config = tmp_path / "spatial-vtk.yaml"
    metrics = tmp_path / "metrics_long.parquet"
    metric_field = tmp_path / "metric_field.parquet"
    station_bias = tmp_path / "station_bias.parquet"
    for path in (metrics, metric_field, station_bias):
        path.write_bytes(b"table")
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

    def fake_run_spatial_derived_outputs_workflow(metrics=None, **kwargs):
        seen["metrics"] = metrics
        seen.update(kwargs)
        return SimpleNamespace(elapsed_s=0.75, paths={}, rows={}, reused=(), failures=())

    monkeypatch.setattr("spatial_vtk.spatial.run_spatial_derived_outputs_workflow", fake_run_spatial_derived_outputs_workflow)

    assert (
        main(
            [
                "spatial",
                "derived-outputs",
                "--config",
                str(config),
                "--metrics-table",
                str(metrics),
                "--metric-field-table",
                str(metric_field),
                "--station-bias-table",
                str(station_bias),
            ]
        )
        == 0
    )

    assert seen["metrics"] == str(metrics)
    assert seen["metric_field"] == str(metric_field)
    assert seen["station_bias"] == str(station_bias)


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
    assert "Spatial readiness summary:" in captured.out
    assert "metric field table" in captured.out
    assert "redcap clusters table" in captured.out
    assert "resolved_path" in captured.out
    assert "Step 4 spatial summaries should be rebuilt" in captured.out
    assert "Run svtk spatial summaries with the active config" in captured.out
    assert "metric_field_path" not in captured.out


def test_cli_spatial_geojson_and_corridor_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["spatial", "geojson-summaries", "--help"])
    assert excinfo.value.code == 0
    geojson_help = capsys.readouterr().out
    assert "Metric rows table" in geojson_help
    assert "--metrics-table" in geojson_help
    assert "--region-geojson" in geojson_help
    assert "--output-table-key" in geojson_help
    assert "svtk spatial geojson-summaries [-h] [--metrics-table PATH]" in geojson_help
    assert "[--region-geojson PATH]" in geojson_help
    assert "[--chunksize N]" in geojson_help
    assert "[--output-table-key KEY]" in geojson_help
    assert "not a filesystem path" in geojson_help
    assert "--chunksize" in geojson_help
    assert "--selector" in geojson_help

    with pytest.raises(SystemExit) as excinfo:
        main(["spatial", "corridors", "--help"])
    assert excinfo.value.code == 0
    corridor_help = capsys.readouterr().out
    assert "Region GeoJSON path" in corridor_help
    assert "--region-geojson" in corridor_help
    assert "--records" in corridor_help
    assert "--records-table" in corridor_help
    assert "--stations" in corridor_help
    assert "--station-table" in corridor_help
    assert "--event-table" in corridor_help
    assert "--output-table-key" in corridor_help
    assert "svtk spatial corridors [-h] [--region-geojson PATH]" in corridor_help
    assert "[--station-table PATH]" in corridor_help
    assert "[--event-table PATH] [--records-table PATH] [--config PATH]" in corridor_help
    assert "[--output-table-key KEY]" in corridor_help


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

    monkeypatch.setattr("spatial_vtk.spatial.run_geojson_region_summary_workflow", fake_geojson)
    monkeypatch.setattr("spatial_vtk.spatial.run_boundary_corridor_workflow", fake_corridors)

    assert (
        main(
            [
                "spatial",
                "geojson-summaries",
                "--config",
                str(config),
                "--metrics-table",
                "metrics.parquet",
                "--region-geojson",
                "regions.geojson",
                "--selector",
                "basin",
                "--chunksize",
                "123",
                "--output-table-key",
                "custom_geojson_summary",
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
                "--region-geojson",
                "regions.geojson",
                "--station-table",
                "stations.csv",
                "--event-table",
                "events.csv",
                "--records-table",
                "records.csv",
                "--output-table-key",
                "custom_corridors",
                "--verbose",
            ]
        )
        == 0
    )

    assert seen["geojson"]["metrics_table"] == "metrics.parquet"
    assert seen["geojson"]["geojson_path"] == "regions.geojson"
    assert seen["geojson"]["output_key"] == "custom_geojson_summary"
    assert seen["geojson"]["selector"] == "basin"
    assert seen["geojson"]["chunksize"] == 123
    assert seen["geojson"]["verbose"] is True
    assert seen["corridors"]["station_table"] == "stations.csv"
    assert seen["corridors"]["event_table"] == "events.csv"
    assert seen["corridors"]["records_table"] == "records.csv"
    assert seen["corridors"]["output_key"] == "custom_corridors"
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
    assert "--qc-trace-summary-output" in captured.out
    assert "--qc-inventory-output" in captured.out
    assert "--qc-overlap-inventory-output" in captured.out
    assert "[--qc-trace-summary-output QC_TRACE_SUMMARY_OUTPUT]" in captured.out
    assert "Prefer --qc-trace-summary-output" in captured.out
    assert "--trace-output is a legacy alias" in captured.out
    assert "qc_trace_summary" in captured.out
    assert "qc_inventory_overlap" in captured.out


def test_cli_qc_build_accepts_clear_output_aliases(tmp_path, monkeypatch, capsys):
    """QC build should dispatch clearer artifact-named output aliases."""

    config = tmp_path / "spatial-vtk.yaml"
    records = tmp_path / "event_station_records.csv"
    trace = tmp_path / "qc_trace.parquet"
    inventory = tmp_path / "qc_inventory.parquet"
    overlap = tmp_path / "qc_overlap.parquet"
    records.write_text("event_id,station\nE1,STA1\n", encoding="utf-8")
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

    import spatial_vtk.qc.build.slurm as qc_slurm

    def fake_run_qc_inventory_job(event_stations, **kwargs):
        seen["event_stations"] = Path(event_stations)
        seen.update(kwargs)
        for path in (trace, inventory, overlap):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("qc", encoding="utf-8")
        return {"qc_trace_summary": trace, "qc_inventory": inventory, "qc_inventory_overlap": overlap}

    monkeypatch.setattr(qc_slurm, "run_qc_inventory_job", fake_run_qc_inventory_job)

    assert main(
        [
            "qc",
            "build",
            "--config",
            str(config),
            "--event-stations",
            str(records),
            "--qc-trace-summary-output",
            str(trace),
            "--qc-inventory-output",
            str(inventory),
            "--qc-overlap-inventory-output",
            str(overlap),
            "--verbose",
        ]
    ) == 0

    captured = capsys.readouterr()
    assert seen["event_stations"] == records
    assert seen["trace_qc_output"] == str(trace)
    assert seen["qc_inventory_output"] == str(inventory)
    assert seen["qc_inventory_overlap_output"] == str(overlap)
    assert seen["verbose"] is True
    assert str(trace) in captured.out


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
                "--metric-task-estimate-output",
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

    from spatial_vtk.metrics import MetricWorkflowTask, write_task_manifest

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
                "--metric-manifest",
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

    from spatial_vtk.metrics import MetricWorkflowTask, write_task_manifest

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
    assert "--input-table" in captured.out
    assert "--figure-output" in captured.out
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


def test_cli_visualize_sidecars_status_reports_metadata_without_csv_loads(tmp_path, capsys):
    """The sidecar status command should summarize JSON metadata for notebook audits."""

    from spatial_vtk.visualize.figure_sidecars import write_figure_row_sidecar

    rows = pd.DataFrame(
        {
            "event_id": ["E1", "E2", "E3"],
            "station": ["STA", "STA", "STB"],
            "metric": ["PGA", "PGA", "PGA"],
            "log2_residual": [0.1, 0.2, -0.4],
        }
    )
    result = write_figure_row_sidecar(
        tmp_path / "figures" / "station_metric_map.png",
        rows,
        sidecar_rows=2,
        sidecar_dir=tmp_path / "sidecars",
        metadata={"svtk_aggregation_kind": "station_summary"},
    )
    assert result is not None

    assert main(["visualize", "sidecars", "status", "--sidecar-dir", str(result.sidecar_path.parent)]) == 0
    text_output = capsys.readouterr().out
    assert "Figure sidecars found: 1" in text_output
    assert "station_metric_map.png" in text_output
    assert "deterministic_sample" in text_output

    assert main(["visualize", "sidecars", "status", "--sidecar-dir", str(result.sidecar_path.parent), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["sidecar_count"] == 1
    assert payload["status"][0]["figure"] == "station_metric_map.png"
    assert payload["status"][0]["plot_row_count"] == 3
    assert payload["status"][0]["plot_sidecar_exact"] is False


def test_cli_visualize_sidecars_status_distinguishes_missing_and_empty_directories(tmp_path, capsys):
    """Sidecar status should distinguish missing sidecar dirs from empty dirs."""

    missing_dir = tmp_path / "missing_sidecars"
    assert main(["visualize", "sidecars", "status", "--sidecar-dir", str(missing_dir)]) == 0
    missing_text = capsys.readouterr().out
    assert "Figure sidecar directory exists: False" in missing_text
    assert "Figure sidecar directory does not exist" in missing_text

    assert main(["visualize", "sidecars", "status", "--sidecar-dir", str(missing_dir), "--json"]) == 0
    missing_payload = json.loads(capsys.readouterr().out)
    assert missing_payload["sidecar_dir_exists"] is False
    assert missing_payload["sidecar_count"] == 0

    empty_dir = tmp_path / "empty_sidecars"
    empty_dir.mkdir()
    assert main(["visualize", "sidecars", "status", "--sidecar-dir", str(empty_dir)]) == 0
    empty_text = capsys.readouterr().out
    assert "Figure sidecar directory exists: True" in empty_text
    assert "No figure sidecar JSON files found in the existing directory." in empty_text


def test_cli_registered_plot_help_names_config_defaults(capsys):
    """Registered figure help should explain config-backed table and figure defaults."""

    with pytest.raises(SystemExit) as excinfo:
        main(["plot", "metrics", "band-score-distribution", "--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    help_text = " ".join(captured.out.split())
    assert "Primary figure input table (metrics long); accepts CSV or parquet" in help_text
    assert "function argument 'df'" not in help_text
    assert "Advanced extra table mapping as function_argument=path" in help_text
    assert "--input-table" in help_text
    assert "--figure-output" in help_text
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
    assert "Primary figure input table (station bias); accepts CSV or parquet" in help_text
    assert "function argument 'station_df'" not in help_text
    assert "Advanced extra table mapping as function_argument=path" in help_text
    assert "--input-table" in help_text
    assert "--figure-output" in help_text
    assert "configured output table 'station_bias'" in help_text
    assert "configured figure output 'station_residual_map'" in help_text


def test_cli_reference_describes_config_defaults_before_kwargs():
    """CLI docs should not present kwargs as the primary plotting interface."""

    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "reference" / "cli_api.rst").read_text(encoding="utf-8")
    generator_text = (root / "tools" / "generate_cli_reference.py").read_text(encoding="utf-8")
    assert "resolve their standard input tables and figure paths from the active config" in text
    assert "first-class flags where they apply" in text
    assert "``--mode``" in text
    assert "``--dep``" in text
    assert "``--indep``" in text
    assert "``--colorby``" in text
    assert "``--compare-to``" in text
    assert "``--bin-label``" in text
    assert "``--input-table``" in text
    assert "``--figure-output``" in text
    assert "``--station-region``" in text
    assert "``--event-region``" in text
    assert "``--components``" in text
    assert "``--time-limit-s``" in text
    assert "``--max-records``" in text
    assert "``--max-traces``" in text
    assert "``--no-connect-points``" in text
    assert "Registered table defaults may be CSV or Parquet" in text
    assert "commands that say they accept CSV or parquet read either suffix through the package table helpers" in text
    assert "``svtk visualize qc list``" in text
    assert "``svtk visualize context list``" in text
    assert "``svtk visualize waveforms list``" in text
    assert "A ``required:<role>`` entry means that command has no registered default table" in text
    assert "Use ``--kwargs key=value`` only for advanced function-specific options" in text
    assert "Prefer configured default tables and named table aliases such as ``--events`` or ``--stations``" in text
    assert "advanced ``--table function_argument=path``" in text
    assert "``svtk visualize qc list``" in generator_text
    assert "A ``required:<role>`` entry means that command has no registered default table" in generator_text
    assert "Prefer configured default tables and named table aliases such as ``--events`` or ``--stations``" in generator_text
    assert "advanced ``--table function_argument=path``" in generator_text
    assert "Registered table defaults may be CSV or Parquet" in generator_text
    assert "argument_name=path" not in generator_text


def test_generated_cli_reference_includes_config_backed_examples():
    """Top-level CLI pages should show config-backed commands users can run directly."""

    root = Path(__file__).resolve().parents[1]
    plot_text = (root / "docs" / "reference" / "cli" / "plot.rst").read_text(encoding="utf-8")
    map_text = (root / "docs" / "reference" / "cli" / "map.rst").read_text(encoding="utf-8")
    visualize_text = (root / "docs" / "reference" / "cli" / "visualize.rst").read_text(encoding="utf-8")
    dashboard_text = (root / "docs" / "reference" / "cli" / "dashboard.rst").read_text(encoding="utf-8")
    generator_text = (root / "tools" / "generate_cli_reference.py").read_text(encoding="utf-8")

    assert "Config-Backed Plotting" in plot_text
    assert "svtk plot metrics band-score-distribution --score-col log2_residual" in plot_text
    assert "registered figure keys for the selected plot" in plot_text
    assert "svtk plot metrics list" in plot_text
    assert "config:<key>" in plot_text
    assert "required:<role>" in plot_text
    assert "Config-Backed Mapping" in map_text
    assert "svtk map spatial station-metric --value-col log2_residual --metric PGA" in map_text
    assert "svtk map spatial list" in map_text
    assert "named map bounds" in map_text
    assert "Basemaps are enabled by default" in map_text
    assert "Config-Backed Visualization" in visualize_text
    assert "svtk visualize qc retention-summary" in visualize_text
    assert "svtk visualize context station-event-context --bounds study_area" in visualize_text
    assert "svtk visualize waveforms observed-synthetic-record-section --components R --max-records 80" in visualize_text
    assert "svtk visualize waveforms list" in visualize_text
    assert "svtk visualize sidecars status" in visualize_text
    assert "event_station_records" in visualize_text
    assert "Config-Backed Dashboards" in dashboard_text
    example_config = "data/examples/configuration/example_spatial_vtk_config.yaml"
    assert f"svtk config set {example_config}" in plot_text
    assert f"svtk config set {example_config}" in map_text
    assert f"svtk config set {example_config}" in visualize_text
    assert f"svtk dashboard status --config {example_config} --run-scenario tutorial" in dashboard_text
    assert (
        f"svtk dashboard metrics --config {example_config} --run-scenario tutorial --auto-port --proxy-mode"
        in dashboard_text
    )
    assert (
        f"svtk dashboard qc --config {example_config} --run-scenario tutorial --auto-port --proxy-mode"
        in dashboard_text
    )
    cli_reference_preambles = [
        plot_text.split("Command Tree", 1)[0],
        map_text.split("Command Tree", 1)[0],
        visualize_text.split("Command Tree", 1)[0],
        dashboard_text.split("Command Tree", 1)[0],
    ]
    assert "runs/spatial_vtk_config.yaml" not in "\n".join(
        cli_reference_preambles
    )
    assert "--metrics-dataset-dir" in dashboard_text
    assert "--dashboard-summary-table-dir" in dashboard_text
    assert "row-level data used by metric filters" in dashboard_text
    assert "dashboard overview tabs" in dashboard_text
    assert "Only pass explicit paths when you want to override those configured outputs" in dashboard_text
    assert "Run ``svtk dashboard status`` before launching dashboards" in dashboard_text
    assert "without loading large metric or QC inventories" in dashboard_text
    assert "Prefer ``--metrics-dataset-dir`` and ``--dashboard-summary-table-dir``" in dashboard_text
    assert "are legacy aliases" in dashboard_text
    assert "metrics_dataset_dir" in dashboard_text
    assert "dashboard_summary_table_dir" in dashboard_text
    assert "qc_trace_summary" in dashboard_text
    assert "[--qc-trace-summary PATH]" in dashboard_text
    assert "``--qc-trace-summary``, ``--trace-summary``" in dashboard_text
    assert "Prefer --qc-trace-summary; --trace-summary is a legacy alias." in dashboard_text
    assert "Older ``metrics_root``, ``summary_root``, and ``trace_summary`` query parameters still work" in dashboard_text
    assert "Config-Backed Plotting" in generator_text
    assert "Config-Backed Mapping" in generator_text
    assert "Config-Backed Visualization" in generator_text
    assert "Config-Backed Dashboards" in generator_text
    assert "``--input-table``/``--input`` and ``--figure-output``/``--output``" in generator_text
    assert "Configured defaults" in generator_text
    assert "_render_configured_defaults(parser)" in generator_text


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
    cli_pages_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((root / "docs" / "reference" / "cli").glob("*.rst"))
    )

    assert "Primary figure input table (metrics long); accepts CSV or parquet" in plot_text
    assert "function argument 'df'" not in plot_text
    assert "``--input-table``, ``--input``" in plot_text
    assert "``--figure-output``, ``--output``" in plot_text
    assert ".. rubric:: Configured defaults" in plot_text
    assert "``config:metrics_long``" in plot_text
    assert "Uses configured output table ``metrics_long`` when ``--config`` is passed" in plot_text
    assert "Uses configured figure output ``band_score_distribution`` when ``--config`` is passed" in plot_text
    assert "Override with ``--input-table`` or ``--input``." in plot_text
    assert "Override with ``--figure-output`` or ``--output``." in plot_text
    assert "``--resolve-paths``" in plot_text
    assert "Add ``--resolve-paths --config PATH``" in plot_text
    assert "Filesystem path. Primary figure input table (metrics long); accepts CSV or parquet" in plot_text
    assert "Filesystem path. Output figure path." in plot_text
    assert "Value: ``PATH``. Primary figure input table" not in plot_text
    assert "Value: ``PATH``. Output figure path" not in plot_text
    assert "configured output table 'metrics_long' when --config is passed" in plot_text
    assert "svtk plot metrics winner-heatmap [-h] [--input-table PATH]" in plot_text
    assert "[--figure-output PATH]" in plot_text
    assert "Defaults to configured output table 'metrics_long'" in plot_text
    assert "svtk plot spatial residual-correlation [-h] [--input-table PATH]" in plot_text
    assert "svtk plot spatial directional-correlogram [-h] [--input-table PATH]" in plot_text
    assert "svtk plot metrics list [-h] [--config PATH]" in plot_text
    assert "``--resolve-paths``" in plot_text
    assert "Add ``--resolve-paths --config PATH`` to show the concrete configured files." in plot_text
    assert "Defaults to configured output table 'distance_bin_correlations'" in plot_text
    assert "configured figure output 'band_score_distribution' when --config is passed" in plot_text
    assert "default config is set with 'svtk config set'" in plot_text
    assert "Advanced extra table mapping as function_argument=path" in plot_text
    assert "Prefer config-backed defaults and named table flags" in plot_text
    assert "Extra table as argument_name=path" not in plot_text
    assert "Filesystem path. Advanced extra table mapping" not in plot_text
    assert "Primary figure input table (station bias); accepts CSV or parquet" in map_text
    assert "function argument 'station_df'" not in map_text
    assert "``--input-table``, ``--input``" in map_text
    assert "``--figure-output``, ``--output``" in map_text
    assert ".. rubric:: Configured defaults" in map_text
    assert "``config:station_bias``" in map_text
    assert "Uses configured output table ``station_bias`` when ``--config`` is passed" in map_text
    assert "Uses configured figure output ``station_residual_map`` when ``--config`` is passed" in map_text
    assert "``--resolve-paths``" in map_text
    assert "Filesystem path. Primary figure input table (station bias); accepts CSV or parquet" in map_text
    assert "Filesystem path. Output figure path." in map_text
    assert "Value: ``PATH``. Primary figure input table" not in map_text
    assert "Value: ``PATH``. Output figure path" not in map_text
    assert "configured output table 'station_bias' when --config is passed" in map_text
    assert "svtk map spatial model-improvement [-h] [--input-table PATH]" in map_text
    assert "svtk map spatial list [-h] [--config PATH]" in map_text
    assert "``--resolve-paths``" in map_text
    assert "Defaults to configured output table 'metrics_long'" in map_text
    assert "configured figure output 'station_residual_map' when --config is passed" in map_text
    assert "``--input-table``, ``--input``" in visualize_text
    assert "``--figure-output``, ``--output``" in visualize_text
    assert "Override with ``--input-table`` or ``--input``." in visualize_text
    assert "Override with ``--figure-output`` or ``--output``." in visualize_text
    assert "``--mode``" in map_text
    assert "``--dep``" in map_text
    assert "``--compare-to``" in map_text
    assert "``--station-region``" in map_text
    assert "``--event-region``" in map_text
    assert "Filesystem path. Convenience prepared events table path" in map_text
    assert "Filesystem path. Convenience event station records table path" in map_text
    assert "Filesystem path. Convenience prepared stations table path" in map_text
    assert "Value: ``events``. Convenience prepared events table path" not in map_text
    assert "Value: ``records``. Convenience event station records table path" not in map_text
    assert "Value: ``stations``. Convenience prepared stations table path" not in map_text
    assert "Value: ``" not in cli_pages_text
    assert "Input table\n     - ``config:qc_metric_pair_retention``" in cli_pages_text
    assert "Input table\n     - ``required:sample table``" in cli_pages_text
    assert (
        "No registered default table is available yet. Pass ``--input-table`` or ``--input`` "
        "with a precomputed period-spectrogram table."
    ) in cli_pages_text
    assert "Plot a precomputed period-spectrogram table. This advanced figure does not" in cli_pages_text
    assert "have a standard config-backed input table; pass --input-table or" in cli_pages_text
    assert (
        "No registered default table is available yet. Pass ``--input-table`` or ``--input`` "
        "with a prepared trace-sample table."
    ) in cli_pages_text
    assert '"spectrogram_df": "a precomputed period-spectrogram table"' in generator_text
    assert '"sample_df": "a prepared trace-sample table"' in generator_text
    assert "No registered config default is available; pass --input-table or --input." in cli_pages_text


def test_config_cli_help_marks_config_values_as_paths(capsys):
    """Config-file arguments should render as path values in help and docs."""

    with pytest.raises(SystemExit) as excinfo:
        main(["config", "show", "--help"])
    assert excinfo.value.code == 0
    show_help = capsys.readouterr().out
    assert "[--config PATH]" in show_help
    assert "[--config CONFIG]" not in show_help

    with pytest.raises(SystemExit) as excinfo:
        main(["config", "set", "--help"])
    assert excinfo.value.code == 0
    set_help = capsys.readouterr().out
    assert "svtk config set [-h] PATH" in set_help
    assert "svtk config set [-h] config_path" not in set_help

    root = Path(__file__).resolve().parents[1]
    config_reference = (root / "docs" / "reference" / "cli" / "config.rst").read_text(encoding="utf-8")
    assert "svtk config show [-h] [--config PATH]" in config_reference
    assert "svtk config set [-h] PATH" in config_reference
    assert "   * - ``PATH``" in config_reference
    assert "Filesystem path. Explicit config file." in config_reference
    assert "Filesystem path. Spatial-VTK config file to use by default." in config_reference
    assert "[--config CONFIG]" not in config_reference
    assert "   * - ``config_path``" not in config_reference
    assert "Value: ``config``. Explicit config file." not in config_reference


def test_cli_config_error_messages_use_path_metavar():
    """Runtime guidance should match ``svtk config set`` help."""

    source = (Path(__file__).resolve().parents[1] / "src" / "spatial_vtk" / "cli" / "__init__.py").read_text(
        encoding="utf-8"
    )
    assert "svtk config set PATH" in source
    assert "svtk config set CONFIG_PATH" not in source


def test_generated_cli_reference_uses_role_based_table_help():
    """Generated plotting docs should present table roles, not raw Python argument names."""

    root = Path(__file__).resolve().parents[1]
    pages = [
        root / "docs" / "reference" / "cli" / "plot.rst",
        root / "docs" / "reference" / "cli" / "map.rst",
        root / "docs" / "reference" / "cli" / "visualize.rst",
    ]
    for path in pages:
        text = path.read_text(encoding="utf-8")
        assert "function argument '" not in text, path.name
        assert "Extra table as argument_name=path" not in text, path.name
        assert "Advanced extra table mapping as function_argument=path" in text, path.name
        assert "Prefer config-backed defaults and named table flags" in text, path.name
        assert "[--table [TABLE]]" not in text, path.name
        assert "[--table [ARG=PATH]]" in text, path.name
        assert "SIDECAR_DIR" not in text, path.name
        assert "[--sidecar-dir DIR]" in text, path.name


def test_registered_table_alias_help_uses_path_metavars(capsys):
    """Named table aliases should look like file paths in CLI help."""

    with pytest.raises(SystemExit) as excinfo:
        main(["map", "spatial", "corridor", "--help"])
    assert excinfo.value.code == 0
    help_text = capsys.readouterr().out
    assert "[--events PATH]" in help_text
    assert "[--records PATH]" in help_text
    assert "[--stations PATH]" in help_text
    assert "[--events EVENTS]" not in help_text
    assert "[--records RECORDS]" not in help_text
    assert "[--stations STATIONS]" not in help_text


def test_generated_cli_reference_names_metrics_run_defaults():
    """Generated metric CLI docs should keep local run paths config-backed."""

    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "reference" / "cli" / "metrics.rst").read_text(encoding="utf-8")
    section = text.split(".. _cli-svtk-metrics-run:", maxsplit=1)[1].split(".. _cli-svtk-metrics-run-batch:", maxsplit=1)[0]
    assert "[--tasks PATH]" in section
    assert "[--output PATH]" in section
    assert "--tasks TASKS --output OUTPUT" not in section
    assert "Filesystem path. Metric task table CSV/parquet path" in section
    assert "Filesystem path. Metric row output CSV/parquet path" in section
    assert "Defaults to configured output table 'metric_tasks'" in section
    assert "Defaults to configured output table 'metric_rows'" in section
    assert "Spatial-VTK config used to resolve default task/output paths" in section


def test_generated_cli_reference_names_io_inventory_defaults():
    """Generated IO CLI docs should describe config-backed inventory defaults."""

    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "reference" / "cli" / "io.rst").read_text(encoding="utf-8")
    section = text.split(".. _cli-svtk-io-inventory:", maxsplit=1)[1].split(
        ".. _cli-svtk-io-master-events:", maxsplit=1
    )[0]
    assert "[--observed-root PATH]" in section
    assert "[--synthetic-root PATH]" in section
    assert "[--relative-to DIR]" in section
    assert "OBSERVED_ROOT" not in section
    assert "SYNTHETIC_ROOT" not in section
    assert "[--waveform-inventory-output PATH]" in section
    assert "``--waveform-inventory-output``, ``--output``" in section
    assert "Filesystem path. Waveform inventory output CSV/parquet table" in section
    assert "Prefer --waveform-inventory-output; --output is a legacy alias." in section
    assert "Defaults to paths.observed_root or paths.observed_template from config" in section
    assert "Defaults to paths.synthetic_root or paths.synthetic_template from config" in section
    assert "Defaults to configured output table 'waveform_inventory'" in section
    assert "``--config``" in section
    assert "``--run-scenario``" in section


def test_generated_cli_reference_names_io_prepare_aliases():
    """Generated IO CLI docs should expose artifact-named metadata prep flags."""

    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "reference" / "cli" / "io.rst").read_text(encoding="utf-8")
    master_events = text.split(".. _cli-svtk-io-master-events:", maxsplit=1)[1].split(
        ".. _cli-svtk-io-master-stations:", maxsplit=1
    )[0]
    master_stations = text.split(".. _cli-svtk-io-master-stations:", maxsplit=1)[1].split(
        ".. _cli-svtk-io-prepare-event-stations:", maxsplit=1
    )[0]
    stations = text.split(".. _cli-svtk-io-prepare-stations:", maxsplit=1)[1]
    stations = stations.split(".. _cli-svtk-io-preprocess-waveforms:", maxsplit=1)[0]
    events = text.split(".. _cli-svtk-io-prepare-events:", maxsplit=1)[1].split(
        ".. _cli-svtk-io-prepare-stations:", maxsplit=1
    )[0]
    event_stations = text.split(".. _cli-svtk-io-prepare-event-stations:", maxsplit=1)[1].split(
        ".. _cli-svtk-io-prepare-events:", maxsplit=1
    )[0]

    assert "[--station-metadata-table PATH]" in stations
    assert "[--prepared-stations-output PATH]" in stations
    assert "``--station-metadata-table``, ``--input``" in stations
    assert "``--prepared-stations-output``, ``--output``" in stations
    assert "Prefer --station-metadata-table; --input is a legacy alias." in stations
    assert "Prefer --prepared-stations-output; --output is a legacy alias." in stations

    assert "[--event-metadata-table PATH]" in events
    assert "[--prepared-events-output PATH]" in events
    assert "``--event-metadata-table``, ``--input``" in events
    assert "``--prepared-events-output``, ``--output``" in events
    assert "Prefer --event-metadata-table; --input is a legacy alias." in events
    assert "Prefer --prepared-events-output; --output is a legacy alias." in events

    assert "[--event-station-table PATH]" in event_stations
    assert "[--station-table PATH]" in event_stations
    assert "[--event-table PATH]" in event_stations
    assert "[--event-station-records-output PATH]" in event_stations
    assert "``--event-station-table``, ``--input``" in event_stations
    assert "``--station-table``, ``--stations``" in event_stations
    assert "``--event-table``, ``--events``" in event_stations
    assert "``--event-station-records-output``, ``--output``" in event_stations
    assert "Prefer --event-station-records-output; --output is a legacy alias." in event_stations

    assert "``--station-tables``, ``--input``" in master_stations
    assert "``--master-station-output``, ``--output``" in master_stations
    assert "Prefer --station-tables; --input is a legacy alias." in master_stations
    assert "Prefer --master-station-output; --output is a legacy alias." in master_stations
    assert "``--event-tables``, ``--input``" in master_events
    assert "``--master-event-output``, ``--output``" in master_events
    assert "Prefer --event-tables; --input is a legacy alias." in master_events
    assert "Prefer --master-event-output; --output is a legacy alias." in master_events


def test_config_find_help_uses_directory_metavar(capsys):
    """Config discovery help should label the start directory as a directory."""

    with pytest.raises(SystemExit) as excinfo:
        main(["config", "find", "--help"])
    assert excinfo.value.code == 0
    help_text = capsys.readouterr().out
    assert "[--start-dir DIR]" in help_text
    assert "START_DIR" not in help_text


def test_cli_metrics_workflow_help_exposes_artifact_aliases(capsys):
    """Metric workflow path flags should name the artifacts they read/write."""

    with pytest.raises(SystemExit) as excinfo:
        main(["metrics", "inventories", "--help"])
    assert excinfo.value.code == 0
    inventory_help = " ".join(capsys.readouterr().out.split())
    assert "[--observed-inventory-output PATH]" in inventory_help
    assert "[--synthetic-inventory-output PATH]" in inventory_help
    assert "--observed-inventory-output" in inventory_help
    assert "--synthetic-inventory-output" in inventory_help
    assert "Prefer --observed-inventory-output; --observed-output is a legacy alias." in inventory_help
    assert "Prefer --synthetic-inventory-output; --synthetic-output is a legacy alias." in inventory_help
    assert "Preprocessed trace metadata" in inventory_help
    assert "observed_metric_inventory" in inventory_help
    assert "synthetic_metric_inventory" in inventory_help

    with pytest.raises(SystemExit) as excinfo:
        main(["metrics", "plan", "--help"])
    assert excinfo.value.code == 0
    plan_help = " ".join(capsys.readouterr().out.split())
    assert "--observed-metric-inventory" in plan_help
    assert "--synthetic-metric-inventory" in plan_help
    assert "--metric-plan-output" in plan_help
    assert "Defaults to configured output table 'observed_metric_inventory'" in plan_help
    assert "Defaults to configured output table 'synthetic_metric_inventory'" in plan_help

    with pytest.raises(SystemExit) as excinfo:
        main(["metrics", "estimate", "--help"])
    assert excinfo.value.code == 0
    estimate_help = " ".join(capsys.readouterr().out.split())
    assert "--metric-manifest" in estimate_help
    assert "--metric-task-estimate-output" in estimate_help

    with pytest.raises(SystemExit) as excinfo:
        main(["metrics", "run", "--help"])
    assert excinfo.value.code == 0
    run_help = " ".join(capsys.readouterr().out.split())
    assert "--task-table" in run_help
    assert "--metric-rows" in run_help
    assert "Metric task table CSV/parquet path" in run_help
    assert "Metric row output CSV/parquet path" in run_help

    with pytest.raises(SystemExit) as excinfo:
        main(["metrics", "batch-status", "--help"])
    assert excinfo.value.code == 0
    batch_status_help = " ".join(capsys.readouterr().out.split())
    assert "--metric-manifest" in batch_status_help
    assert "Metric workflow manifest JSON" in batch_status_help
    assert "--missing-limit" in batch_status_help

    with pytest.raises(SystemExit) as excinfo:
        main(["metrics", "merge-batches", "--help"])
    assert excinfo.value.code == 0
    merge_help = " ".join(capsys.readouterr().out.split())
    assert "--metric-manifest" in merge_help
    assert "--metric-rows-output" in merge_help

    with pytest.raises(SystemExit) as excinfo:
        main(["metrics", "cache-waveforms", "--help"])
    assert excinfo.value.code == 0
    cache_help = " ".join(capsys.readouterr().out.split())
    assert "--metric-manifest" in cache_help
    assert "--cached-metric-manifest-output" in cache_help

    with pytest.raises(SystemExit) as excinfo:
        main(["metrics", "slurm", "--help"])
    assert excinfo.value.code == 0
    slurm_help = " ".join(capsys.readouterr().out.split())
    assert "--metric-manifest" in slurm_help
    assert "--metrics-slurm-script-output" in slurm_help
    assert "--incomplete-only" in slurm_help
    assert "--overwrite-batches" in slurm_help


def test_generated_cli_reference_names_metrics_workflow_artifact_aliases():
    """Generated metric CLI docs should preserve artifact-named workflow aliases."""

    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "reference" / "cli" / "metrics.rst").read_text(encoding="utf-8")
    inventories_section = text.split(".. _cli-svtk-metrics-inventories:", maxsplit=1)[1].split(
        ".. _cli-svtk-metrics-merge-batches:", maxsplit=1
    )[0]
    plan_section = text.split(".. _cli-svtk-metrics-plan:", maxsplit=1)[1].split(
        ".. _cli-svtk-metrics-run:", maxsplit=1
    )[0]
    run_section = text.split(".. _cli-svtk-metrics-run:", maxsplit=1)[1].split(
        ".. _cli-svtk-metrics-run-batch:", maxsplit=1
    )[0]
    run_batch_section = text.split(".. _cli-svtk-metrics-run-batch:", maxsplit=1)[1].split(
        ".. _cli-svtk-metrics-slurm:", maxsplit=1
    )[0]
    batch_status_section = text.split(".. _cli-svtk-metrics-batch-status:", maxsplit=1)[1].split(
        ".. _cli-svtk-metrics-cache-waveforms:", maxsplit=1
    )[0]
    cache_section = text.split(".. _cli-svtk-metrics-cache-waveforms:", maxsplit=1)[1].split(
        ".. _cli-svtk-metrics-estimate:", maxsplit=1
    )[0]
    estimate_section = text.split(".. _cli-svtk-metrics-estimate:", maxsplit=1)[1].split(
        ".. _cli-svtk-metrics-inventories:", maxsplit=1
    )[0]
    merge_section = text.split(".. _cli-svtk-metrics-merge-batches:", maxsplit=1)[1].split(
        ".. _cli-svtk-metrics-outputs:", maxsplit=1
    )[0]
    slurm_section = text.split(".. _cli-svtk-metrics-slurm:", maxsplit=1)[1]

    assert "``--observed-inventory-output``, ``--observed-output``" in inventories_section
    assert "``--synthetic-inventory-output``, ``--synthetic-output``" in inventories_section
    assert "Prefer --observed-inventory-output; --observed-output is a legacy alias." in inventories_section
    assert "Prefer --synthetic-inventory-output; --synthetic-output is a legacy alias." in inventories_section
    assert "Preprocessed trace metadata CSV/parquet path" in inventories_section
    assert "``--observed-inventory``, ``--observed-metric-inventory``" in plan_section
    assert "``--synthetic-inventory``, ``--synthetic-metric-inventory``" in plan_section
    assert "``--metric-plan-output``, ``--output``" in plan_section
    assert "Defaults to configured output table 'observed_metric_inventory'" in plan_section
    assert "Defaults to configured output table 'synthetic_metric_inventory'" in plan_section
    assert "Prefer --metric-plan-output; --output is a legacy alias." in plan_section
    assert "``--tasks``, ``--task-table``" in run_section
    assert "``--metric-rows``, ``--output``" in run_section
    assert "Metric task table CSV/parquet path" in run_section
    assert "Metric row output CSV/parquet path" in run_section
    assert "Prefer --metric-rows; --output is a legacy alias." in run_section
    assert "``--missing-limit``" in batch_status_section
    assert "``--metric-manifest``, ``--manifest``" in batch_status_section
    assert "Metric workflow manifest JSON" in batch_status_section
    assert "Prefer --metric-manifest; --manifest is a legacy alias." in batch_status_section
    assert "``--metric-manifest``, ``--manifest``" in cache_section
    assert "``--cached-metric-manifest-output``, ``--output``" in cache_section
    assert "Prefer --metric-manifest; --manifest is a legacy alias." in cache_section
    assert "Prefer --cached-metric-manifest-output; --output is a legacy alias." in cache_section
    assert "``--metric-manifest``, ``--manifest``" in estimate_section
    assert "``--metric-task-estimate-output``, ``--output``" in estimate_section
    assert "Metric task CSV/parquet path. Overrides --metric-manifest." in estimate_section
    assert "Prefer --metric-manifest; --manifest is a legacy alias." in estimate_section
    assert "Prefer --metric-task-estimate-output; --output is a legacy alias." in estimate_section
    assert "``--metric-manifest``, ``--manifest``" in merge_section
    assert "``--metric-rows-output``, ``--output``" in merge_section
    assert "Prefer --metric-manifest; --manifest is a legacy alias." in merge_section
    assert "Prefer --metric-rows-output; --output is a legacy alias." in merge_section
    assert "``--metric-manifest``, ``--manifest``" in run_batch_section
    assert "Prefer --metric-manifest; --manifest is a legacy alias." in run_batch_section
    assert "``--metric-manifest``, ``--manifest``" in slurm_section
    assert "``--metrics-slurm-script-output``, ``--output``" in slurm_section
    assert "Prefer --metric-manifest; --manifest is a legacy alias." in slurm_section
    assert "Prefer --metrics-slurm-script-output; --output is a legacy alias." in slurm_section
    assert "``--incomplete-only``" in slurm_section
    assert "``--overwrite-batches``" in slurm_section


def test_generated_cli_reference_names_metrics_outputs_aliases():
    """Generated metric CLI docs should expose clear downstream output aliases."""

    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "reference" / "cli" / "metrics.rst").read_text(encoding="utf-8")
    section = text.split(".. _cli-svtk-metrics-outputs:", maxsplit=1)[1].split(
        ".. _cli-svtk-metrics-plan:", maxsplit=1
    )[0]
    assert "``--metric-rows``, ``--metrics``" in section
    assert "Raw metric workflow rows CSV/parquet path" in section
    assert "Prefer --metric-rows; --metrics is a legacy alias." in section
    assert "``--metrics-output-dir``, ``--output-dir``" in section
    assert "configured output paths are used" in section
    assert "Prefer --metrics-output-dir; --output-dir is a legacy alias." in section
    assert "``--event-table``, ``--events``" in section
    assert "``--station-table``, ``--stations``" in section
    assert "Prefer --event-table; --events is a legacy alias." in section
    assert "Prefer --station-table; --stations is a legacy alias." in section
    assert "prepared_events" in section
    assert "prepared_stations" in section


def test_generated_cli_reference_names_qc_output_aliases():
    """Generated QC CLI docs should expose artifact-named output aliases."""

    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "reference" / "cli" / "qc.rst").read_text(encoding="utf-8")
    build_section = text.split(".. _cli-svtk-qc-build:", maxsplit=1)[1].split(
        ".. _cli-svtk-qc-manual-queue:", maxsplit=1
    )[0]
    slurm_section = text.split(".. _cli-svtk-qc-slurm:", maxsplit=1)[1].split(
        ".. _cli-svtk-qc-summaries:", maxsplit=1
    )[0]
    manual_queue_section = text.split(".. _cli-svtk-qc-manual-queue:", maxsplit=1)[1].split(
        ".. _cli-svtk-qc-slurm:", maxsplit=1
    )[0]
    assert "[--qc-trace-summary PATH]" in manual_queue_section
    assert "[--manual-review-queue-output PATH]" in manual_queue_section
    assert "``--qc-trace-summary``, ``--trace-summary``" in manual_queue_section
    assert "``--manual-review-queue-output``, ``--output``" in manual_queue_section
    assert "Prefer --qc-trace-summary; --trace-summary is a legacy alias." in manual_queue_section
    assert "Prefer --manual-review-queue-output; --output is a legacy alias." in manual_queue_section
    assert "manual_review_queue" in manual_queue_section
    assert "[--event-station-records PATH]" in slurm_section
    assert "[--qc-slurm-script-output PATH]" in slurm_section
    assert "``--event-station-records``, ``--event-stations``" in slurm_section
    assert "``--qc-slurm-script-output``, ``--output``" in slurm_section
    assert "Prefer --event-station-records; --event-stations is a legacy alias." in slurm_section
    assert "Prefer --qc-slurm-script-output; --output is a legacy alias." in slurm_section
    for section in (build_section, slurm_section):
        assert "``--qc-trace-summary-output``, ``--trace-output``" in section
        assert "``--qc-inventory-output``, ``--inventory-output``" in section
        assert "``--qc-overlap-inventory-output``, ``--overlap-inventory-output``" in section
        assert "Prefer --qc-trace-summary-output; --trace-output is a legacy alias." in section
        assert "Prefer --qc-inventory-output; --inventory-output is a legacy alias." in section
        assert "Prefer --qc-overlap-inventory-output; --overlap-inventory-output is a legacy alias." in section
        assert "qc_trace_summary" in section
        assert "qc_inventory" in section
        assert "qc_inventory_overlap" in section


def test_generated_cli_reference_names_spatial_geojson_aliases():
    """Generated spatial CLI docs should expose table/path role aliases."""

    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "reference" / "cli" / "spatial.rst").read_text(encoding="utf-8")
    geojson_section = text.split(".. _cli-svtk-spatial-geojson-summaries:", maxsplit=1)[1].split(
        ".. _cli-svtk-spatial-status:", maxsplit=1
    )[0]
    corridor_section = text.split(".. _cli-svtk-spatial-corridors:", maxsplit=1)[1].split(
        ".. _cli-svtk-spatial-derived-outputs:", maxsplit=1
    )[0]
    assert "``--metrics-table``, ``--metrics``" in geojson_section
    assert "``--region-geojson``, ``--geojson``" in geojson_section
    assert "``--output-table-key``, ``--output-key``" in geojson_section
    assert "Prefer --metrics-table; --metrics is a legacy alias." in geojson_section
    assert "Prefer --region-geojson; --geojson is a legacy alias." in geojson_section
    assert "Prefer --output-table-key; --output-key is a legacy alias." in geojson_section
    assert "Registered output table key, not a filesystem path" in geojson_section
    assert "``--region-geojson``, ``--geojson``" in corridor_section
    assert "``--station-table``, ``--stations``" in corridor_section
    assert "``--event-table``, ``--events``" in corridor_section
    assert "``--records-table``, ``--records``" in corridor_section
    assert "``--output-table-key``, ``--output-key``" in corridor_section
    assert "Prefer --region-geojson; --geojson is a legacy alias." in corridor_section
    assert "Prefer --station-table; --stations is a legacy alias." in corridor_section
    assert "Prefer --event-table; --events is a legacy alias." in corridor_section
    assert "Prefer --records-table; --records is a legacy alias." in corridor_section
    assert "Prefer --output-table-key; --output-key is a legacy alias." in corridor_section
    assert "prepared_stations" in corridor_section
    assert "prepared_events" in corridor_section


def test_generated_cli_reference_names_spatial_summary_aliases():
    """Generated spatial CLI docs should expose table-named summary aliases."""

    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "reference" / "cli" / "spatial.rst").read_text(encoding="utf-8")
    derived_section = text.split(".. _cli-svtk-spatial-derived-outputs:", maxsplit=1)[1].split(
        ".. _cli-svtk-spatial-geojson-summaries:", maxsplit=1
    )[0]
    summaries_section = text.split(".. _cli-svtk-spatial-summaries:", maxsplit=1)[1]

    assert "``--metrics-table``, ``--metrics``" in derived_section
    assert "``--metric-field-table``, ``--metric-field``" in derived_section
    assert "``--station-bias-table``, ``--station-bias``" in derived_section
    assert "Prefer --metrics-table; --metrics is a legacy alias." in derived_section
    assert "Prefer --metric-field-table; --metric-field is a legacy alias." in derived_section
    assert "Prefer --station-bias-table; --station-bias is a legacy alias." in derived_section
    assert "svtk spatial derived-outputs [-h] [--metrics-table PATH]" in derived_section
    assert "[--metric-field-table PATH]" in derived_section
    assert "[--station-bias-table PATH] [--config PATH]" in derived_section
    assert "[--outputs KEYS]" in derived_section
    assert "``--metrics-table``, ``--metrics``" in summaries_section
    assert "``--station-metadata-table``, ``--station-metadata``" in summaries_section
    assert "Prefer --metrics-table; --metrics is a legacy alias." in summaries_section
    assert "Prefer --station-metadata-table; --station-metadata is a legacy alias." in summaries_section
    assert "svtk spatial summaries [-h] [--metrics-table PATH] [--config PATH]" in summaries_section
    assert "[--station-metadata-table PATH] [--checkpoint-dir DIR]" in summaries_section
    assert "metrics_long" in summaries_section
    assert "prepared_stations" in summaries_section


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
    assert "--require-source-overlap" in text
    assert "--source-overlap-scope event_station" in text
    assert "SVTK_METRICS_DASHBOARD_ROW_LIMIT" in text
    assert "SVTK_QC_DASHBOARD_MAX_ROWS" in text
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
    assert '--metrics "$TABLES/metrics_long.parquet"' not in text
    assert '--input "$TABLES/metrics_long.parquet"' not in text
    assert "svtk plot metrics scatterplot \\\n     --config \"$CONFIG\"" in text
    assert "svtk plot metrics heatmap \\\n     --config \"$CONFIG\"" in text


def test_cli_workflow_configured_commands_use_tutorial_scenario():
    """The shell tutorial should keep commands on the committed tutorial inputs."""

    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "examples" / "cli_workflow.rst").read_text(encoding="utf-8")
    assert "export SCENARIO=tutorial" in text
    command_blocks = [
        block
        for block in text.split("\n\n")
        if block.lstrip().startswith("svtk ") or block.lstrip().startswith("   svtk ")
    ]
    configured_commands = [
        block
        for block in command_blocks
        if '--config "$CONFIG"' in block
    ]
    assert configured_commands
    missing_scenario = [
        block.splitlines()[0].strip()
        for block in configured_commands
        if '--run-scenario "$SCENARIO"' not in block
    ]
    assert not missing_scenario


def test_cli_reference_frames_svtk_call_as_advanced_escape_hatch():
    """The CLI reference should not present svtk call as a standard workflow path."""

    root = Path(__file__).resolve().parents[1]
    index_text = (root / "docs" / "reference" / "cli_api.rst").read_text(encoding="utf-8")
    call_text = (root / "docs" / "reference" / "cli" / "call.rst").read_text(encoding="utf-8")

    assert "Advanced escape hatch" in index_text
    assert "Advanced Escape Hatch" in call_text
    assert "Prefer the named ``config``, ``io``, ``qc``, ``metrics``" in index_text
    assert "spatial_vtk.config.metric_display_name" in call_text
    assert "spatial_vtk.config.labels.metric_display_name" not in call_text
    assert "Call any importable Spatial-VTK Python function." not in index_text
    assert "Call any importable Spatial-VTK Python function." not in call_text


def test_metric_cli_commands_use_public_metrics_surface():
    """Curated metric CLI commands should use the top-level metrics API surface."""

    import spatial_vtk.cli as cli_module

    source = inspect.getsource(cli_module)
    assert "from spatial_vtk.metrics.workflow import" not in source
    assert "from spatial_vtk.metrics import run_manifest_batch" in source
    assert "from spatial_vtk.metrics import metric_manifest_batch_status" in source
    assert "from spatial_vtk.metrics import (\n        metric_manifest_batch_status," in source
    assert "from spatial_vtk.metrics import plan_metric_tasks, tasks_to_frame, write_task_manifest" in source
    assert "from spatial_vtk.metrics import cache_metric_manifest_waveforms" in source
    assert "from spatial_vtk.metrics import write_metric_outputs" in source


def test_spatial_cli_commands_use_public_spatial_surface():
    """Curated spatial CLI commands should use the top-level spatial API surface."""

    import spatial_vtk.cli as cli_module

    source = inspect.getsource(cli_module)
    forbidden_import = "from spatial_vtk.spatial.calculate import " + "run_"
    assert forbidden_import not in source
    assert "from spatial_vtk.spatial import run_spatial_statistics_workflow" in source
    assert "from spatial_vtk.spatial import run_spatial_derived_outputs_workflow" in source
    assert "from spatial_vtk.spatial import run_geojson_region_summary_workflow" in source
    assert "from spatial_vtk.spatial import run_boundary_corridor_workflow" in source


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


def test_cli_period_spectra_uses_metrics_long_config_default(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    table_dir = tmp_path / "outputs" / "tables"
    table_dir.mkdir(parents=True)
    metrics = table_dir / "metrics_long.csv"
    metrics.write_text(
        "metric,period_s,model,log2_residual\n"
        "PSA,1.0,m1,0.5\n"
        "PSA,2.0,m1,0.2\n",
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

    def fake_plot_period_spectra(spectra_df, output_path=None, **kwargs):
        seen["rows"] = len(spectra_df)
        seen["columns"] = list(spectra_df.columns)
        seen["output_path"] = Path(output_path)
        seen["kwargs"] = kwargs
        seen["output_path"].parent.mkdir(parents=True, exist_ok=True)
        seen["output_path"].write_text("figure", encoding="utf-8")
        return seen["output_path"]

    monkeypatch.setattr(metrics_plot, "plot_period_spectra", fake_plot_period_spectra)

    assert (
        main(
            [
                "plot",
                "metrics",
                "period-spectra",
                "--config",
                str(config),
                "--value-col",
                "log2_residual",
                "--group-col",
                "model",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    expected_output = tmp_path / "outputs" / "figures" / "period_spectra.png"
    assert seen["rows"] == 2
    assert "log2_residual" in seen["columns"]
    assert seen["output_path"] == expected_output
    assert seen["kwargs"]["value_col"] == "log2_residual"
    assert seen["kwargs"]["group_col"] == "model"
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


def test_cli_bounds_reports_malformed_numeric_extent():
    """Comma-separated bounds should fail with a numeric-extent message."""

    from spatial_vtk.cli import _resolve_cli_bounds

    assert _resolve_cli_bounds("1,2,3,4", None) == (1.0, 2.0, 3.0, 4.0)
    with pytest.raises(ValueError, match="four comma-separated values must be numeric"):
        _resolve_cli_bounds("1,2,bad,4", None)


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


def test_cli_prepare_station_metadata_accepts_artifact_flags(tmp_path):
    src = tmp_path / "stations.csv"
    out = tmp_path / "prepared.csv"
    pd.DataFrame({"stationcode": ["sta2"], "station_latitude": [35.0], "station_longitude": [-119.0]}).to_csv(src, index=False)

    assert (
        main(
            [
                "io",
                "prepare-stations",
                "--station-metadata-table",
                str(src),
                "--prepared-stations-output",
                str(out),
            ]
        )
        == 0
    )

    prepared = pd.read_csv(out)
    assert set(["station", "lat", "lon"]) <= set(prepared.columns)
    assert prepared.loc[0, "station"] == "STA2"


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


def test_cli_inventory_uses_configured_template_roots_and_output(tmp_path):
    observed = tmp_path / "raw" / "observed"
    synthetic = tmp_path / "raw" / "synthetic" / "model_a"
    observed.mkdir(parents=True)
    synthetic.mkdir(parents=True)
    (observed / "ev1.pkl").write_bytes(b"observed")
    (synthetic / "ev1.mseed").write_bytes(b"synthetic")
    config = tmp_path / "spatial-vtk.yaml"
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
paths:
  observed_root: raw/observed/{{event_id}}.pkl
  synthetic_template: raw/synthetic/{{model}}/{{event_id}}.mseed
outputs:
  tables: outputs/tables
""",
        encoding="utf-8",
    )

    assert main(["io", "inventory", "--config", str(config), "--no-sha256"]) == 0

    inventory = pd.read_csv(tmp_path / "outputs" / "tables" / "waveform_inventory.csv")
    assert set(inventory["dataset"]) == {"observed", "synthetic"}
    assert set(inventory["filename"]) == {"ev1.pkl", "ev1.mseed"}
    assert "sha256" not in inventory.columns


def test_cli_inventory_accepts_waveform_inventory_output_flag(tmp_path):
    observed = tmp_path / "observed"
    synthetic = tmp_path / "synthetic"
    observed.mkdir()
    synthetic.mkdir()
    (observed / "ev1.pkl").write_bytes(b"observed")
    (synthetic / "ev1.mseed").write_bytes(b"synthetic")
    output = tmp_path / "waveform_inventory.csv"

    assert (
        main(
            [
                "io",
                "inventory",
                "--observed-root",
                str(observed),
                "--synthetic-root",
                str(synthetic),
                "--waveform-inventory-output",
                str(output),
                "--no-sha256",
            ]
        )
        == 0
    )

    inventory = pd.read_csv(output)
    assert set(inventory["dataset"]) == {"observed", "synthetic"}
    assert set(inventory["filename"]) == {"ev1.pkl", "ev1.mseed"}
    assert "sha256" not in inventory.columns


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


def test_cli_metrics_outputs_help_exposes_clear_aliases(capsys):
    """Metric output help should name raw metric rows and prepared metadata roles."""

    with pytest.raises(SystemExit) as excinfo:
        main(["metrics", "outputs", "--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "--metric-rows" in captured.out
    assert "--metrics-output-dir" in captured.out
    assert "--event-table" in captured.out
    assert "--station-table" in captured.out
    assert "Raw metric workflow rows" in captured.out
    assert "Prefer --metrics-output-dir" in captured.out
    assert "Prefer --event-table" in captured.out
    assert "Prefer --station-table" in captured.out
    assert "prepared_events" in captured.out
    assert "prepared_stations" in captured.out


def test_cli_metrics_outputs_uses_aliases_and_configured_metadata(tmp_path, monkeypatch):
    """Metric outputs should use clearer aliases and prepared metadata defaults."""

    config = tmp_path / "spatial-vtk.yaml"
    tables = tmp_path / "outputs" / "tables"
    output_dir = tmp_path / "downstream"
    tables.mkdir(parents=True)
    metric_rows = tables / "metric_rows.parquet"
    prepared_events = tables / "prepared_events.csv"
    prepared_stations = tables / "prepared_stations.csv"
    pd.DataFrame({"event_id": ["ev1"], "station": ["STA1"], "metric": ["PGA"]}).to_parquet(metric_rows, index=False)
    pd.DataFrame({"event_id": ["ev1"], "event_lat": [34.0], "event_lon": [-118.0]}).to_csv(prepared_events, index=False)
    pd.DataFrame({"station": ["STA1"], "station_lat": [34.1], "station_lon": [-118.2]}).to_csv(prepared_stations, index=False)
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

    import spatial_vtk.metrics.workflow as workflow

    def fake_write_metric_outputs(metric_rows_arg, output_dir_arg=None, **kwargs):
        seen["metric_rows"] = Path(metric_rows_arg)
        seen["output_dir"] = Path(output_dir_arg)
        seen["kwargs"] = kwargs
        seen["output_dir"].mkdir(parents=True, exist_ok=True)
        path = seen["output_dir"] / "metrics_long.parquet"
        path.write_text("metric rows", encoding="utf-8")
        return {"metrics_long": path}

    monkeypatch.setattr(workflow, "write_metric_outputs", fake_write_metric_outputs)

    assert main(
        [
            "metrics",
            "outputs",
            "--config",
            str(config),
            "--metric-rows",
            str(metric_rows),
            "--metrics-output-dir",
            str(output_dir),
        ]
    ) == 0

    assert seen["metric_rows"] == metric_rows
    assert seen["output_dir"] == output_dir
    assert seen["kwargs"]["events"] == prepared_events
    assert seen["kwargs"]["stations"] == prepared_stations
    assert seen["kwargs"]["cfg"].root_dir == tmp_path


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
                "--metric-plan-output",
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
                "--metric-plan-output",
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
                "--metric-manifest",
                str(manifest_path),
                "--cached-metric-manifest-output",
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


def test_cli_metrics_run_uses_configured_defaults(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    tables = tmp_path / "outputs" / "tables"
    tables.mkdir(parents=True)
    tasks_path = tables / "metric_tasks.csv"
    tasks_path.write_text("task_id,event_id,station,component,model,passband,metrics\n", encoding="utf-8")
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

    import spatial_vtk.metrics.workflow as workflow

    def fake_tasks_from_frame(path):
        seen["tasks_path"] = Path(path)
        return ["task-1"]

    def fake_run_metric_tasks(tasks, qc_table=None):
        seen["tasks"] = tasks
        seen["qc_table"] = qc_table
        return pd.DataFrame({"metric": ["PGA"], "value": [1.0]})

    def fake_write_metric_rows(rows, path):
        seen["rows"] = rows
        seen["output"] = Path(path)
        seen["output"].parent.mkdir(parents=True, exist_ok=True)
        rows.to_parquet(seen["output"], index=False)
        return seen["output"]

    monkeypatch.setattr(workflow, "tasks_from_frame", fake_tasks_from_frame)
    monkeypatch.setattr(workflow, "run_metric_tasks", fake_run_metric_tasks)
    monkeypatch.setattr(workflow, "write_metric_rows", fake_write_metric_rows)

    assert main(["metrics", "run", "--config", str(config)]) == 0

    captured = capsys.readouterr()
    assert seen["tasks_path"] == tasks_path
    assert seen["output"] == tables / "metric_rows.parquet"
    assert seen["tasks"] == ["task-1"]
    assert seen["qc_table"] is None
    assert "Wrote 1 metric rows." in captured.out
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

    assert (
        main(
            [
                "metrics",
                "slurm",
                "--metric-manifest",
                str(manifest),
                "--metrics-slurm-script-output",
                str(script),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert "Wrote metric Slurm script" in captured.out
    assert "No job was submitted" in captured.out
    assert script.exists()


def test_cli_metrics_batch_status_and_incomplete_slurm(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spatial-vtk.yaml"
    manifest = tmp_path / "manifest.json"
    script = tmp_path / "run_metrics.slurm"
    settings = tmp_path / "svtk-cli-config.json"
    completed = tmp_path / "batch_0.csv"
    completed.write_text("metric\nPGA\n", encoding="utf-8")
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
                "batches": [
                    {"batch_index": 0, "task_indices": [], "output_path": str(completed)},
                    {"batch_index": 1, "task_indices": [], "output_path": str(tmp_path / "batch_1.csv")},
                    {"batch_index": 2, "task_indices": [], "output_path": str(tmp_path / "batch_2.csv")},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SVTK_CLI_CONFIG_FILE", str(settings))
    assert main(["config", "set", str(config)]) == 0

    assert main(["metrics", "batch-status", "--metric-manifest", str(manifest), "--missing-limit", "1"]) == 0

    status_output = capsys.readouterr().out
    assert "total_batches: 3" in status_output
    assert "completed_batches: 1" in status_output
    assert "missing_batches: 2" in status_output
    assert "missing_outputs_truncated: true" in status_output

    assert main(["metrics", "slurm", "--manifest", str(manifest), "--output", str(script), "--incomplete-only", "--overwrite-batches"]) == 0

    slurm_output = capsys.readouterr().out
    assert "Wrote metric Slurm script" in slurm_output
    text = script.read_text(encoding="utf-8")
    assert "#SBATCH --array=1-2%2" in text
    assert "Metric selected batches: 2 of 3" in text
    assert "--batch-index $SLURM_ARRAY_TASK_ID --overwrite" in text


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
    trace_output = tables / "qc_trace_summary.parquet"
    inventory_output = tables / "qc_inventory.parquet"
    overlap_output = tables / "qc_inventory_overlap.parquet"
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

    assert main(
        [
            "qc",
            "slurm",
            "--config",
            str(config),
            "--qc-trace-summary-output",
            str(trace_output),
            "--qc-inventory-output",
            str(inventory_output),
            "--qc-overlap-inventory-output",
            str(overlap_output),
        ]
    ) == 0

    captured = capsys.readouterr()
    script = tmp_path / "outputs" / "slurm" / "build_qc_inventory.slurm"
    assert str(script) in captured.out
    text = script.read_text(encoding="utf-8")
    assert "--event-stations" in text
    assert "--qc-trace-summary-output" in text
    assert "--qc-inventory-output" in text
    assert "--qc-overlap-inventory-output" in text
    assert str(event_stations.resolve()) in text
    assert str(trace_output.resolve()) in text
    assert str(inventory_output.resolve()) in text
    assert str(overlap_output.resolve()) in text
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

    assert (
        main(
            [
                "dashboard",
                "metrics",
                "--config",
                str(config),
                "--port",
                "8555",
                "--proxy-mode",
                "--row-limit",
                "250000",
                "--summary-display-rows",
                "7500",
                "--download-rows",
                "all",
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert "Metrics dashboard row dataset:" in captured.out
    assert "Metrics dashboard summary tables:" in captured.out
    assert Path(launched["metrics_dataset_dir"]) == tmp_path / "outputs" / "dashboards" / "metrics_dashboard"
    assert Path(launched["dashboard_summary_table_dir"]) == tmp_path / "outputs" / "dashboards" / "dashboard_summaries"
    assert Path(launched["config_path"]) == config.resolve()
    assert launched["server_port"] == 8555
    assert launched["auto_port"] is False
    assert launched["proxy_mode"] is True
    assert launched["row_limit"] == "250000"
    assert launched["summary_display_rows"] == "7500"
    assert launched["download_rows"] == "all"
    assert "Metrics dashboard row-level record limit: 250000" in captured.out
    assert "Metrics dashboard summary display rows: 7500" in captured.out
    assert "Metrics dashboard download rows: all" in captured.out


def test_cli_dashboard_help_exposes_clear_path_aliases(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["dashboard", "metrics", "--help"])
    assert excinfo.value.code == 0
    metrics_help = capsys.readouterr().out
    assert "--metrics-dataset-dir" in metrics_help
    assert "--metrics-dataset" in metrics_help
    assert "--metrics-root" in metrics_help
    assert "--dashboard-summary-table-dir" in metrics_help
    assert "--dashboard-summary-dir" in metrics_help
    assert "--summary-root" in metrics_help
    assert "Metrics dashboard row dataset directory" in metrics_help
    assert "row-level data used by metric filters" in metrics_help
    assert "Dashboard summary-table directory" in metrics_help
    assert "--row-limit" in metrics_help
    assert "--summary-display-rows" in metrics_help
    assert "--download-rows" in metrics_help
    assert "model_metric_band" in metrics_help
    assert "station_rollup" in metrics_help
    assert "metrics_dashboard" in metrics_help
    assert "dashboard_summaries" in metrics_help
    assert "when --config is passed or a default config is set with 'svtk config set'" in metrics_help
    assert "Prefer --metrics-dataset-dir" in metrics_help
    assert "--metrics-root and --metrics-dataset are legacy aliases" in metrics_help
    assert "Prefer --dashboard-summary-table-dir" in metrics_help
    assert "--summary-root and --dashboard-summary-dir are legacy aliases" in metrics_help

    with pytest.raises(SystemExit) as excinfo:
        main(["dashboard", "qc", "--help"])
    assert excinfo.value.code == 0
    qc_help = capsys.readouterr().out
    assert "--qc-trace-summary" in qc_help
    assert "[--qc-trace-summary PATH]" in qc_help
    assert "qc_trace_summary" in qc_help
    assert "Prefer --qc-trace-summary" in qc_help
    assert "--trace-summary is a legacy alias" in qc_help


def test_cli_dashboard_missing_config_errors_name_dashboard_artifacts(tmp_path, monkeypatch, capsys):
    """Dashboard launch errors should name concrete artifact roles, not generic roots."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SVTK_CONFIG_FILE", raising=False)
    monkeypatch.setenv("SVTK_CLI_CONFIG_FILE", str(tmp_path / "missing-settings.json"))

    assert main(["dashboard", "metrics"]) == 2
    metrics_error = capsys.readouterr().err
    assert "metrics dashboard row dataset" in metrics_error
    assert "dashboard summary-table directory" in metrics_error
    assert "metrics_dashboard row dataset" in metrics_error
    assert "dashboard_summaries table directory" in metrics_error
    assert "dashboard roots" not in metrics_error

    assert main(["dashboard", "qc"]) == 2
    qc_error = capsys.readouterr().err
    assert "QC trace-summary table" in qc_error
    assert "qc_trace_summary table" in qc_error
    assert "trace-summary path" not in qc_error


def test_cli_dashboard_metrics_accepts_clear_path_aliases(tmp_path, monkeypatch, capsys):
    metrics_path = tmp_path / "dashboard_metrics"
    summary_path = tmp_path / "dashboard_summaries"
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

    assert (
        main(
            [
                "dashboard",
                "metrics",
                "--metrics-dataset-dir",
                str(metrics_path),
                "--dashboard-summary-table-dir",
                str(summary_path),
                "--port",
                "8555",
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert "Metrics dashboard row dataset:" in captured.out
    assert "Metrics dashboard summary tables:" in captured.out
    assert Path(launched["metrics_dataset_dir"]) == metrics_path
    assert Path(launched["dashboard_summary_table_dir"]) == summary_path
    assert launched["config_path"] is None
    assert launched["server_port"] == 8555


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
    assert Path(launched["qc_trace_summary_table"]) == tmp_path / "outputs" / "tables" / "qc_trace_summary.csv"
    assert "trace_summary" not in launched
    assert Path(launched["config_path"]) == config.resolve()
    assert launched["server_port"] == 8556


def test_cli_dashboard_qc_accepts_clear_trace_summary_alias(tmp_path, monkeypatch, capsys):
    trace_summary = tmp_path / "qc_trace_summary.parquet"
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

    assert main(["dashboard", "qc", "--qc-trace-summary", str(trace_summary), "--port", "8556"]) == 0

    captured = capsys.readouterr()
    assert "QC dashboard trace summary:" in captured.out
    assert Path(launched["qc_trace_summary_table"]) == trace_summary
    assert "trace_summary" not in launched
    assert launched["config_path"] is None
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
    qc_row = next(row for row in payload["status"] if row["name"] == "qc_trace_summary_path")
    assert qc_row["dashboard_table"] == "qc_trace_summary"
    assert qc_row["ready"] is False
    assert qc_row["readiness"] == "missing"
    assert "QC trace-summary table is missing" in qc_row["message"]
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
    assert "Dashboard readiness summary:" in captured.out
    assert "metrics_long source table" in captured.out
    assert "QC trace-summary table" in captured.out
    assert "Run the Step 2 QC workflow" in captured.out
    assert "Finish the metric workflow outputs" in captured.out
    assert "QC Overview, Charts, Review Queue" in captured.out
    assert "resolved_path" in captured.out
    assert "metrics_long_path" not in captured.out
    assert " path " not in captured.out
    assert "QC trace-summary table is missing" in captured.out
    assert "model_metric_band dashboard summary table" in captured.out


def test_cli_call_importable_function(capsys):
    assert main(["call", "spatial_vtk.config.metric_display_name", "--args", "C5"]) == 0
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
    assert main(["plot", "metrics", "residuals-vs-distance", "--input-table", str(src), "--figure-output", str(out)]) == 0
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
    assert main(["map", "spatial", "station-metric", "--input-table", str(src), "--figure-output", str(out), "--no-basemap"]) == 0
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
    assert main(["visualize", "context", "station-coverage", "--input-table", str(src), "--figure-output", str(out)]) == 0
    assert out.exists()


def test_cli_plot_list(capsys):
    assert main(["plot", "metrics", "list"]) == 0
    captured = capsys.readouterr()
    assert "Command" in captured.out
    assert "Input" in captured.out
    assert "Output" in captured.out
    assert "residuals-vs-distance" in captured.out
    assert "config:metrics_long" in captured.out
    assert "period-spectra" in captured.out
    period_line = next(line for line in captured.out.splitlines() if line.startswith("period-spectra"))
    assert "config:metrics_long" in period_line
    assert "required:" not in period_line
    assert "period-spectrogram" in captured.out
    assert "required:spectrogram table" in captured.out
    assert "precomputed period-spectrogram table" in captured.out
    assert "model-metric-heatmap" in captured.out
    assert "config:band_score_distribution" in captured.out
    assert "config:model_metric_heatmap" in captured.out
    assert "from config from config" not in captured.out


def test_cli_plot_list_can_resolve_config_backed_paths(tmp_path, capsys):
    """Figure list commands should show concrete configured paths on request."""

    config = tmp_path / "spatial-vtk.yaml"
    config.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
  figures: outputs/figures
""",
        encoding="utf-8",
    )

    assert main(["plot", "metrics", "list", "--config", str(config), "--resolve-paths"]) == 0
    text = capsys.readouterr().out
    assert "config:metrics_long ->" in text
    assert str(tmp_path / "outputs" / "tables" / "metrics_long.parquet") in text
    assert "config:band_score_distribution ->" in text
    assert str(tmp_path / "outputs" / "figures" / "band_score_distribution.png") in text
    assert "required:spectrogram table" in text

    assert main(["map", "spatial", "list", "--config", str(config), "--resolve-paths"]) == 0
    map_text = capsys.readouterr().out
    assert "config:station_bias ->" in map_text
    assert str(tmp_path / "outputs" / "tables" / "station_bias.parquet") in map_text
    assert "--events(events_df)=config:prepared_events ->" in map_text
    assert str(tmp_path / "outputs" / "tables" / "prepared_events.csv") in map_text
    assert "config:corridor_map ->" in map_text


def test_cli_plot_list_resolve_paths_requires_config(tmp_path, monkeypatch, capsys):
    """Resolved list output should fail with standard config guidance."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SVTK_CONFIG_FILE", raising=False)
    monkeypatch.setenv("SVTK_CLI_CONFIG_FILE", str(tmp_path / "missing-settings.json"))

    assert main(["plot", "metrics", "list", "--resolve-paths"]) == 2
    captured = capsys.readouterr()
    assert "No Spatial-VTK config was found" in captured.err
    assert "svtk config set PATH" in captured.err
    assert "Traceback" not in captured.err


def test_cli_registered_plot_missing_input_names_required_table_role(capsys):
    """Missing registered plot inputs should name the table role before importing plot modules."""

    with pytest.raises(SystemExit) as excinfo:
        main(["plot", "metrics", "period-spectrogram"])
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "No spectrogram table was provided" in captured.err
    assert "Pass --input-table/--input PATH" in captured.err
    assert "required table roles" in captured.err
    assert "Missing Python dependency" not in captured.err
    assert "the following arguments are required" not in captured.err


def test_cli_registered_plot_help_names_required_input_without_config_default(capsys):
    """Advanced registered plots should say when no config-backed input exists."""

    with pytest.raises(SystemExit) as excinfo:
        main(["plot", "metrics", "period-spectrogram", "--help"])
    assert excinfo.value.code == 0
    text = capsys.readouterr().out
    assert "precomputed period-spectrogram table" in text
    assert "No registered config default is available; pass --input-table or --input." in text


def test_cli_registered_plot_missing_output_names_figure_role():
    """Shared registered-figure resolver should explain missing figure outputs clearly."""

    import argparse
    import spatial_vtk.cli as cli

    args = argparse.Namespace(output=None)
    spec = cli.PlotCommand("spatial_vtk.metrics.plot.plot_band_score_distribution", "df", "Plot.", output_key=None)

    with pytest.raises(ValueError) as excinfo:
        cli._registered_plot_output_path(args, spec, None)

    message = str(excinfo.value)
    assert "No figure output path was provided" in message
    assert "Pass --figure-output/--output PATH" in message
    assert "required output roles" in message


def test_cli_registered_plot_missing_config_messages_name_clear_aliases():
    """Config-backed registered figure errors should mention both path aliases."""

    import argparse
    import spatial_vtk.cli as cli

    args = argparse.Namespace(input=None, output=None)
    spec = cli.PlotCommand(
        "spatial_vtk.metrics.plot.plot_band_score_distribution",
        "df",
        "Plot.",
        input_key="metrics_long",
        output_key="band_score_distribution",
    )

    with pytest.raises(ValueError) as input_exc:
        cli._registered_plot_input_path(args, spec, None)
    with pytest.raises(ValueError) as output_exc:
        cli._registered_plot_output_path(args, spec, None)

    assert "Pass --input-table/--input PATH" in str(input_exc.value)
    assert "Pass --figure-output/--output PATH" in str(output_exc.value)
    assert "svtk config set PATH" in str(input_exc.value)
    assert "svtk config set PATH" in str(output_exc.value)


def test_cli_spatial_plot_list_includes_pattern_similarity_defaults(capsys):
    assert main(["plot", "spatial", "list"]) == 0
    captured = capsys.readouterr()
    assert "pattern-similarity" in captured.out
    assert "config:pattern_similarity_station_anomalies" in captured.out
    assert "config:pattern_similarity" in captured.out
    assert "directional-correlogram" in captured.out
    assert "config:distance_bin_correlations" in captured.out
    assert "--fit(fit_df)=optional" in captured.out
