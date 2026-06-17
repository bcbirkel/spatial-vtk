from __future__ import annotations

import os
import types

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from spatial_vtk.config import (
    SVTK_CLI_CONFIG_ENV,
    SVTK_CONFIG_ENV,
    SpatialVTKConfig,
    active_config,
    clear_saved_config_path,
    clear_active_config,
    find_config_file,
    format_run_time,
    notebook_figure_sidecar_settings,
    notebook_run_context,
    get_saved_config_path,
    load_config,
    notebook_timing_enabled,
    prepare_notebook_geospatial_environment,
    register_svtk_cell_timer,
    resolve_output_path,
    resolve_run_defaults,
    run_or_submit_notebook_cli_command,
    set_saved_config_path,
    submit_notebook_slurm_script,
    write_notebook_python_slurm_script,
)
from spatial_vtk.io import (
    ArtifactSpec,
    apply_waveform_preprocessing_with_metadata,
    apply_waveform_preprocessing,
    artifact_path_for_spec,
    default_output_paths,
    read_artifact_manifest,
    metric_plan_from_config,
    output_group_completion,
    output_group_namespace,
    output_group_paths,
    output_group_status,
    output_readiness,
    output_status_frame,
    should_rebuild_paths,
    should_rebuild_outputs,
    stable_hash,
    waveform_preprocessing_from_config,
    waveform_preprocessing_label,
    write_artifact_manifest,
    write_output_table,
)
import spatial_vtk.visualize.figure_io as figure_io
import spatial_vtk.config.notebook as notebook_helpers
from spatial_vtk.visualize.figure_io import finish_figure
from spatial_vtk.visualize import default_figure_paths
from spatial_vtk.visualize.figure_sidecars import FigureSidecarResult, write_figure_row_sidecar
from spatial_vtk.visualize.dashboard import (
    dashboard_map_readiness,
    dashboard_output_namespace,
    dashboard_summary_readiness_frame,
    filter_optional_dashboard_summary,
    row_value_column_for_summary,
)
from spatial_vtk.visualize.dashboard.export import load_dashboard_metric_dataset


def test_runtime_config_loads_paths_defaults_and_bounds(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    config_path = project / "spatial-vtk.yaml"
    bounds_csv = project / "config" / "bounds.csv"
    bounds_csv.parent.mkdir()
    bounds_csv.write_text(
        "keyword,lon_min,lon_max,lat_min,lat_max\n"
        "csv_region,-121,-120,35,36\n",
        encoding="utf-8",
    )
    config_path.write_text(
        """
project:
  name: example
  root_dir: .
paths:
  observed_root: data/observed
  synthetic_template: data/synthetic/{model}/{event_id}/*.mseed
outputs:
  metrics: outputs/metrics/metrics.csv
  figures: outputs/figures
bounds:
  presets_csv: config/bounds.csv
  presets:
    inline_region:
      lon_min: -119.0
      lon_max: -118.0
      lat_min: 33.0
      lat_max: 34.0
run_defaults:
  common:
    components: [Z]
    filter_order: 4
  groups:
    metrics:
      metrics: [C5]
      passbands: ["1-2"]
    metrics.calculate:
      components: [R, T]
  commands:
    metrics.calculate.batch:
      metrics: [C5, C10]
      filter_order: 6
metrics:
  models: [model_a]
  output_path: outputs/metrics/metrics.csv
""",
        encoding="utf-8",
    )

    cfg = SpatialVTKConfig.from_file(config_path)
    assert cfg.root_dir == project.resolve()
    assert cfg.path("paths.observed_root") == project / "data" / "observed"
    path_vars = cfg.path_namespace("paths")
    assert path_vars.observed_root_path == project / "data" / "observed"
    assert path_vars.synthetic_template_path == project / "data" / "synthetic" / "{model}" / "{event_id}" / "*.mseed"
    assert cfg.format_template("run/{model}/{event_id}", model="m1", event_id="e1") == "run/m1/e1"
    assert cfg.resolve_bounds("inline_region") == (-119.0, -118.0, 33.0, 34.0)
    assert cfg.resolve_bounds("csv_region") == (-121.0, -120.0, 35.0, 36.0)
    assert cfg.resolve_bounds([-1, 1, 2, 3]) == (-1.0, 1.0, 2.0, 3.0)
    with pytest.raises(KeyError, match="Unknown Spatial-VTK bounds keyword"):
        cfg.resolve_bounds("missing_region")

    defaults = cfg.run_defaults("metrics.calculate.batch")
    assert defaults["components"] == ["R", "T"]
    assert defaults["metrics"] == ["C5", "C10"]
    assert defaults["filter_order"] == 6

    monkeypatch.setenv(SVTK_CONFIG_ENV, str(config_path))
    assert find_config_file() == config_path.resolve()
    assert load_config()["project"]["name"] == "example"


def test_public_dashboard_and_sidecar_helpers_import_without_streamlit():
    """Pure dashboard and sidecar helpers should be usable without app imports."""

    import sys

    import spatial_vtk.visualize.dashboard as dashboard_helpers
    import spatial_vtk.visualize as visualize_helpers

    assert dashboard_helpers.dashboard_summary_readiness_frame is dashboard_summary_readiness_frame
    assert dashboard_helpers.filter_optional_dashboard_summary is filter_optional_dashboard_summary
    assert dashboard_helpers.row_value_column_for_summary is row_value_column_for_summary
    assert visualize_helpers.write_figure_row_sidecar is write_figure_row_sidecar
    assert visualize_helpers.FigureSidecarResult is FigureSidecarResult
    assert "spatial_vtk.visualize.dashboard.streamlit_metrics" not in sys.modules
    assert "spatial_vtk.visualize.dashboard.streamlit_qc" not in sys.modules


def test_saved_cli_config_path_is_used_after_env(tmp_path, monkeypatch):
    """A saved CLI config should be used when no explicit path/env config is set."""

    config_path = tmp_path / "spatial-vtk.yaml"
    settings_path = tmp_path / "cli-config.json"
    config_path.write_text(
        """
project:
  name: saved
  root_dir: .
""",
        encoding="utf-8",
    )
    monkeypatch.setenv(SVTK_CLI_CONFIG_ENV, str(settings_path))

    saved = set_saved_config_path(config_path)

    assert saved == config_path.resolve()
    assert get_saved_config_path() == config_path.resolve()
    assert find_config_file() == config_path.resolve()
    assert load_config()["project"]["name"] == "saved"
    assert clear_saved_config_path() == settings_path.resolve()
    assert get_saved_config_path() is None


def test_default_output_and_figure_paths_are_named(tmp_path):
    """Default path helpers should avoid repeated filename declarations."""

    tables = default_output_paths(
        tmp_path / "tables",
        [
            "qc_inventory",
            "qc_inventory_overlap",
            "manual_review_queue",
            "qc_metric_pair_retention",
            "post_qc_records",
            "qc_drop_causes_overlap",
        ],
    )
    figures = default_figure_paths(tmp_path / "figures")

    assert tables.qc_inventory == tmp_path / "tables" / "qc_inventory.csv"
    assert tables.qc_inventory_overlap == tmp_path / "tables" / "qc_inventory_overlap.parquet"
    assert tables.manual_review_queue == tmp_path / "tables" / "manual_review_queue.csv"
    assert tables.qc_metric_pair_retention == tmp_path / "tables" / "qc_metric_pair_retention.csv"
    assert tables.post_qc_records == tmp_path / "tables" / "post_qc_records.csv"
    assert tables.qc_drop_causes_overlap == tmp_path / "tables" / "qc_drop_causes_overlap.csv"
    assert figures.retention_summary == tmp_path / "figures" / "retention_summary.png"
    assert figures.qc_drop_cause_diagnostics_overlap == tmp_path / "figures" / "qc_drop_cause_diagnostics_overlap.png"
    assert figures.station_event_context == tmp_path / "figures" / "station_event_context.png"


def test_notebook_timing_config_and_formatter(tmp_path):
    """Notebook timing should be configurable and display only wall time."""

    enabled = SpatialVTKConfig(tmp_path / "config.yaml", tmp_path, {"notebooks": {"show_cell_timing": True}})
    disabled = SpatialVTKConfig(tmp_path / "config.yaml", tmp_path, {"notebooks": {"show_cell_timing": False}})

    assert notebook_timing_enabled(enabled)
    assert not notebook_timing_enabled(disabled)
    assert format_run_time(0.0192) == "Run time: 19.2 ms"
    assert format_run_time(2.5) == "Run time: 2.50 s"


def test_prepare_notebook_geospatial_environment_clears_proj_overrides(monkeypatch):
    """Tutorial notebook bootstrap should ignore inherited external PROJ paths."""

    monkeypatch.setenv("PROJ_LIB", "/external/proj")
    monkeypatch.setenv("PROJ_DATA", "/external/proj-data")

    removed = prepare_notebook_geospatial_environment()

    assert removed == {"PROJ_LIB": "/external/proj", "PROJ_DATA": "/external/proj-data"}
    assert "PROJ_LIB" not in os.environ
    assert "PROJ_DATA" not in os.environ


def test_prepare_notebook_geospatial_environment_can_keep_proj_overrides(monkeypatch):
    """Users can keep custom PROJ paths when they intentionally need them."""

    monkeypatch.setenv("PROJ_LIB", "/external/proj")
    monkeypatch.setenv("SVTK_KEEP_PROJ_ENV", "1")

    removed = prepare_notebook_geospatial_environment()

    assert removed == {}
    assert os.environ["PROJ_LIB"] == "/external/proj"


def test_notebook_run_context_resolves_config_dirs_and_flags(tmp_path, monkeypatch):
    """Notebook setup should be reusable instead of redefined in each notebook."""

    repo = tmp_path / "project"
    (repo / "src" / "spatial_vtk").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='spatial-vtk'\n", encoding="utf-8")
    config_path = repo / "runs" / "spatial_vtk_config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(
        """
project:
  root_dir: ..
outputs:
  root: run_outputs
  tables: run_outputs/tables
  figures: run_outputs/figures
  dashboards: run_outputs/dashboards
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("SVTK_SUBMIT_SLURM", "1")
    monkeypatch.setenv("SVTK_OVERWRITE", "true")
    monkeypatch.setenv("SVTK_PREVIEW_ROWS", "12")

    context = notebook_run_context(start=repo / "docs", create_dirs=True)

    assert context.repo_root == repo.resolve()
    assert context.config_path == config_path.resolve()
    expected_outputs = config_path.parent / "run_outputs"
    assert context.outputs_root == expected_outputs
    assert context.tables_dir == expected_outputs / "tables"
    assert context.figures_dir == expected_outputs / "figures"
    assert context.dashboards_dir == expected_outputs / "dashboards"
    assert context.slurm_dir == expected_outputs / "slurm"
    assert context.submit_slurm is True
    assert context.overwrite is True
    assert context.preview_rows == 12
    assert context.tables_dir.exists()

    clear_active_config()


def test_notebook_figure_sidecar_settings_parse_env(tmp_path, monkeypatch):
    """Notebook sidecar controls should use one parser across tutorials."""

    monkeypatch.setenv("SVTK_FIGURE_SIDECARS", "1")
    monkeypatch.setenv("SVTK_FIGURE_SIDECAR_ROWS", "all")
    generic = notebook_figure_sidecar_settings("metric", figure_dir=tmp_path / "figures")
    assert generic.enabled is True
    assert generic.rows is None
    assert generic.directory == tmp_path / "figures" / "sidecars"
    assert generic.kwargs() == {
        "write_sidecar": True,
        "sidecar_rows": None,
        "sidecar_dir": tmp_path / "figures" / "sidecars",
    }

    monkeypatch.setenv("SVTK_METRIC_FIGURE_SIDECARS", "0")
    monkeypatch.setenv("SVTK_METRIC_FIGURE_SIDECAR_ROWS", "25")
    metric = notebook_figure_sidecar_settings("metric", figure_dir=tmp_path / "figures")
    assert metric.enabled is False
    assert metric.rows == 25

    for name in (
        "SVTK_FIGURE_SIDECARS",
        "SVTK_FIGURE_SIDECAR_ROWS",
        "SVTK_METRIC_FIGURE_SIDECARS",
        "SVTK_METRIC_FIGURE_SIDECAR_ROWS",
    ):
        monkeypatch.delenv(name, raising=False)
    explicit = notebook_figure_sidecar_settings(
        "qc",
        sidecar_dir=tmp_path / "custom_sidecars",
        default_enabled=True,
        default_rows=10,
    )
    assert explicit.enabled is True
    assert explicit.rows == 10
    assert explicit.directory == tmp_path / "custom_sidecars"


def test_notebook_slurm_script_uses_configured_environment(tmp_path, capsys):
    """Notebook SLURM scripts should inherit setup from config, not notebooks."""

    repo = tmp_path / "project"
    (repo / "src" / "spatial_vtk").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='spatial-vtk'\n", encoding="utf-8")
    config_path = repo / "runs" / "spatial_vtk_config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(
        """
project:
  root_dir: ..
outputs:
  root: run_outputs
  tables: run_outputs/tables
  figures: run_outputs/figures
  dashboards: run_outputs/dashboards
compute:
  slurm:
    python_command: python
    submit_command: sbatch --parsable
    partition: shared
    environment_setup:
      - module load python
""",
        encoding="utf-8",
    )

    context = notebook_run_context(start=repo / "docs", create_dirs=True)
    script = write_notebook_python_slurm_script(
        context,
        "example.slurm",
        'print("ready")',
        job_name="svtk-example",
        walltime="01:00:00",
        memory="4G",
        cpus=2,
    )

    text = script.read_text(encoding="utf-8")
    assert script == context.slurm_dir / "example.slurm"
    assert "#SBATCH --job-name=svtk-example" in text
    assert "#SBATCH --partition=shared" in text
    assert "#SBATCH --time=01:00:00" in text
    assert "#SBATCH --mem=4G" in text
    assert "#SBATCH --cpus-per-task=2" in text
    assert "module load python" in text
    assert f"cd {context.repo_root}" in text
    assert 'print("ready")' in text

    result = submit_notebook_slurm_script(context, script)

    captured = capsys.readouterr().out
    assert result is None
    assert f"script: {script}" in captured
    assert f"sbatch --parsable {script}" in captured
    clear_active_config()


def test_notebook_cli_helper_runs_or_writes_slurm_wrapper(tmp_path, monkeypatch, capsys):
    """Large-run notebooks should share one CLI run/submit helper."""

    repo = tmp_path / "project"
    (repo / "src" / "spatial_vtk").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='spatial-vtk'\n", encoding="utf-8")
    config_path = repo / "runs" / "spatial_vtk_config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(
        """
project:
  root_dir: ..
outputs:
  root: run_outputs
compute:
  slurm:
    python_command: python
    submit_command: sbatch --parsable
""",
        encoding="utf-8",
    )
    context = notebook_run_context(start=repo / "docs", create_dirs=True)
    captured_args = {}

    def fake_cli(args):
        captured_args["args"] = list(args)
        return 0

    monkeypatch.setattr(notebook_helpers, "_run_spatial_vtk_cli", fake_cli)
    result = run_or_submit_notebook_cli_command(
        context,
        ["svtk", "metrics", "outputs", "--config", str(config_path)],
        script_name="metrics_outputs.slurm",
        job_name="svtk-metrics-outputs",
        run_local=True,
    )

    assert result is None
    assert captured_args["args"] == ["metrics", "outputs", "--config", str(config_path)]

    result = run_or_submit_notebook_cli_command(
        context,
        ["svtk", "qc", "summaries", "--verbose"],
        script_name="qc_summaries.slurm",
        job_name="svtk-qc-summaries",
        walltime="02:00:00",
        memory="8G",
        cpus=2,
        run_local=False,
    )

    script = context.slurm_dir / "qc_summaries.slurm"
    text = script.read_text(encoding="utf-8")
    printed = capsys.readouterr().out
    assert result is None
    assert "svtk qc summaries --verbose" in printed
    assert "#SBATCH --job-name=svtk-qc-summaries" in text
    assert "#SBATCH --time=02:00:00" in text
    assert "#SBATCH --mem=8G" in text
    assert "#SBATCH --cpus-per-task=2" in text
    assert "main(['qc', 'summaries', '--verbose'])" in text
    assert f"sbatch --parsable {script}" in printed
    clear_active_config()


def test_register_svtk_cell_timer_prints_for_successful_cells(tmp_path, monkeypatch, capsys):
    """Automatic notebook timing should register one reusable IPython hook."""

    class FakeEvents:
        """Minimal IPython event registry used by the automatic timer test."""

        def __init__(self):
            self.callbacks = {}

        def register(self, event_name, callback):
            self.callbacks[event_name] = callback

        def unregister(self, event_name, callback):
            if self.callbacks.get(event_name) is callback:
                del self.callbacks[event_name]

    class FakeShell:
        """Minimal shell object exposing the event API used by notebooks."""

        def __init__(self):
            self.events = FakeEvents()

    shell = FakeShell()
    fake_ipython = types.SimpleNamespace(get_ipython=lambda: shell)
    monkeypatch.setitem(__import__("sys").modules, "IPython", fake_ipython)
    cfg = SpatialVTKConfig(tmp_path / "config.yaml", tmp_path, {"notebooks": {"show_cell_timing": True}})

    register_svtk_cell_timer(config=cfg)
    assert "pre_run_cell" in shell.events.callbacks
    assert "post_run_cell" in shell.events.callbacks

    shell.events.callbacks["pre_run_cell"](types.SimpleNamespace(raw_cell="x = 1"))
    shell.events.callbacks["post_run_cell"](types.SimpleNamespace(error_before_exec=None, error_in_exec=None))
    assert "Run time:" in capsys.readouterr().out


def test_active_config_resolves_registry_outputs(tmp_path, monkeypatch):
    """Active config should provide default table and figure output paths."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  root: run_outputs
  tables: run_outputs/custom_tables
  figures: run_outputs/custom_figures
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()

    assert active_config() is cfg
    assert resolve_output_path("prepared_stations", kind="table") == tmp_path / "run_outputs" / "custom_tables" / "prepared_stations.csv"
    assert resolve_output_path("record_coverage", kind="figure") == tmp_path / "run_outputs" / "custom_figures" / "record_coverage.png"

    table_path = write_output_table("prepared_stations", pd.DataFrame({"station": ["ABC"]}))
    assert table_path == tmp_path / "run_outputs" / "custom_tables" / "prepared_stations.csv"
    assert table_path.exists()

    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    finished = finish_figure(fig, output_key="record_coverage", savefig=True, showfig=False)
    figure_path = tmp_path / "run_outputs" / "custom_figures" / "record_coverage.png"
    assert finished.spatial_vtk_saved_path == figure_path
    assert figure_path.exists()

    explicit = resolve_output_path("record_coverage", kind="figure", outpath="override/custom.png")
    assert explicit == tmp_path / "override" / "custom.png"
    clear_active_config()


def test_output_groups_resolve_configured_paths(tmp_path, monkeypatch):
    """Workflow output groups should avoid repeated notebook path plumbing."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  root: run_outputs
  tables: run_outputs/tables
  figures: run_outputs/figures
  dashboards: run_outputs/dashboards
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()

    qc_paths = output_group_paths("step_02_qc", cfg=cfg)
    assert qc_paths["trace_qc_path"] == tmp_path / "run_outputs" / "tables" / "qc_trace_summary.csv"
    assert qc_paths["qc_inventory_path"] == tmp_path / "run_outputs" / "tables" / "qc_inventory.csv"
    assert qc_paths["qc_inventory_overlap_path"] == tmp_path / "run_outputs" / "tables" / "qc_inventory_overlap.parquet"
    assert qc_paths["comparison_eligible_path"] == tmp_path / "run_outputs" / "tables" / "comparison_eligible_records.csv"
    assert qc_paths["drop_causes_overlap_figure_path"] == tmp_path / "run_outputs" / "figures" / "drop_cause_diagnostics_overlap.png"
    assert qc_paths["event_trace_comparison_path"] == tmp_path / "run_outputs" / "figures" / "event_trace_comparison.png"

    paths = output_group_paths("step_04_spatial", cfg=cfg)

    assert paths["metrics_long_path"] == tmp_path / "run_outputs" / "tables" / "metrics_long.parquet"
    assert paths["cluster_features_path"] == tmp_path / "run_outputs" / "tables" / "cluster_feature_summary.csv"
    assert paths["pca_scores_path"] == tmp_path / "run_outputs" / "tables" / "pca_station_scores.parquet"

    metric_paths = output_group_paths("step_03_metrics", cfg=cfg)
    assert metric_paths["prepared_events_path"] == tmp_path / "run_outputs" / "tables" / "prepared_events.csv"
    assert metric_paths["prepared_stations_path"] == tmp_path / "run_outputs" / "tables" / "prepared_stations.csv"

    namespace = output_group_namespace("step_07_dashboards", cfg=cfg)
    assert namespace.qc_trace_summary_path == tmp_path / "run_outputs" / "tables" / "qc_trace_summary.csv"
    assert namespace.metrics_dashboard_root == tmp_path / "run_outputs" / "dashboards" / "metrics_dashboard"
    assert namespace.dashboard_summary_root == tmp_path / "run_outputs" / "dashboards" / "dashboard_summaries"
    dashboard_namespace = dashboard_output_namespace(cfg=cfg)
    assert dashboard_namespace.qc_trace_summary_path == namespace.qc_trace_summary_path
    assert dashboard_namespace.metrics_dashboard_root == namespace.metrics_dashboard_root
    assert dashboard_namespace.dashboard_summary_root == namespace.dashboard_summary_root

    status = output_group_status("step_04_spatial", cfg=cfg)
    assert status[0]["name"] == "metrics_long_path"
    assert status[0]["exists"] is False

    write_output_table("metrics_long", pd.DataFrame({"metric": ["PGA"]}), cfg=cfg)
    completion = output_group_completion("step_03_metrics", cfg=cfg)
    assert completion["complete"] is False
    assert completion["existing"] == 1
    assert "metrics_enriched_path" in completion["missing"]

    assert should_rebuild_outputs({"metrics_long_path": paths["metrics_long_path"]}) is False
    assert should_rebuild_paths(paths["metrics_long_path"]) is False
    source = tmp_path / "newer_source.csv"
    source.write_text("x\n1\n", encoding="utf-8")
    assert should_rebuild_outputs({"metrics_long_path": paths["metrics_long_path"]}, sources=[source]) is True
    assert should_rebuild_paths(paths["metrics_long_path"], sources=[source]) is True
    status_frame = output_status_frame({"metrics_long_path": paths["metrics_long_path"]})
    assert list(status_frame["name"]) == ["metrics_long_path"]

    clear_active_config()


def test_dashboard_summary_readiness_reports_missing_empty_and_value_states(tmp_path):
    """Dashboard preflight should explain why tabs will be blank."""

    summary_root = tmp_path / "dashboard_summaries"
    summary_root.mkdir()
    (summary_root / "model_metric_band.csv").write_text(
        "model,metric,band,n,med_log2_residual\nm1,PGA,1-2 sec,1,0.25\n",
        encoding="utf-8",
    )
    (summary_root / "station_rollup.csv").write_text(
        "station,model,metric,band,n\nSTA,m1,PGA,1-2 sec,1\n",
        encoding="utf-8",
    )
    (summary_root / "event_rollup.csv").write_text(
        "event_id,model,metric,band,n,med_log2_residual\n",
        encoding="utf-8",
    )

    readiness = dashboard_summary_readiness_frame(summary_root, create_parent=False)
    by_table = readiness.set_index("dashboard_table")

    assert by_table.loc["model_metric_band", "readiness"] == "ready"
    assert by_table.loc["model_metric_band", "ready"] is True
    assert by_table.loc["station_rollup", "readiness"] == "no_value_data"
    assert "finite dashboard value" in by_table.loc["station_rollup", "message"]
    assert by_table.loc["station_rollup", "map_ready"] is False
    assert "longitude" in by_table.loc["station_rollup", "missing_map_columns"]
    assert by_table.loc["event_rollup", "readiness"] == "empty"
    assert by_table.loc["event_rollup", "map_ready"] is False
    assert "coordinate columns" in by_table.loc["event_rollup", "map_message"]
    assert by_table.loc["path_hex", "readiness"] == "missing"
    assert "dist_bin_km" in by_table.loc["path_hex", "missing_columns"]

    ready_map = dashboard_map_readiness(
        pd.DataFrame({"station": ["STA"], "sta_lon": [-118.1], "sta_lat": [34.2]}),
        "station_rollup",
    )
    assert ready_map["ready"] is True


def test_optional_dashboard_summary_filter_reports_missing_value_columns():
    """Optional dashboard tabs should not crash when a selected value is absent."""

    station_summary = pd.DataFrame(
        {
            "station": ["STA"],
            "model": ["m1"],
            "metric": ["PGA"],
            "band": ["1-2 sec"],
            "n": [1],
        }
    )

    filtered, message = filter_optional_dashboard_summary(
        station_summary,
        table_label="station",
        value_column="med_log2_residual",
        models=["m1"],
        metric="PGA",
        bands=["1-2 sec"],
    )

    assert filtered.empty
    assert list(filtered.columns) == list(station_summary.columns)
    assert message is not None
    assert "station summary" in message
    assert "log2(observed / synthetic)" in message


def test_dashboard_metric_dataset_loader_accepts_direct_table_files(tmp_path):
    """Dashboard metric loading should accept a table file or dataset directory."""

    direct_csv = tmp_path / "metrics_long.csv"
    direct_csv.write_text(
        "model,metric,band,station,event_id,log2_residual\n"
        "m1,PGA,1-2 sec,STA,EV,0.25\n",
        encoding="utf-8",
    )
    loaded_csv = load_dashboard_metric_dataset(direct_csv)
    assert len(loaded_csv) == 1
    assert loaded_csv["log2_residual"].iloc[0] == pytest.approx(0.25)

    dataset_root = tmp_path / "dashboard_dataset"
    dataset_root.mkdir()
    loaded_csv.to_parquet(dataset_root / "metrics_long.parquet", index=False)
    loaded_dataset = load_dashboard_metric_dataset(dataset_root)
    assert loaded_dataset[["model", "metric", "band"]].to_dict("records") == [
        {"model": "m1", "metric": "PGA", "band": "1-2 sec"}
    ]

    bad_file = tmp_path / "metrics_long.txt"
    bad_file.write_text("not,a,table\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Use Parquet or CSV"):
        load_dashboard_metric_dataset(bad_file)


def test_dashboard_summary_values_map_to_row_level_columns():
    """Summary median/mean columns should map back to raw row value columns."""

    rows = pd.DataFrame(
        {
            "log2_residual": [0.25],
            "residual": [1.5],
            "value_obs": [3.0],
            "score": [0.8],
        }
    )

    assert row_value_column_for_summary("med_log2_residual", rows) == "log2_residual"
    assert row_value_column_for_summary("mean_log2_residual", rows) == "log2_residual"
    assert row_value_column_for_summary("med_resid", rows) == "residual"
    assert row_value_column_for_summary("med_residual", rows) == "residual"
    assert row_value_column_for_summary("med_value_obs", rows) == "value_obs"
    assert row_value_column_for_summary("score", rows) == "score"
    assert row_value_column_for_summary("med_missing_value", rows) is None


def test_output_readiness_reports_notebook_step_decisions(tmp_path):
    """Output readiness should explain missing, stale, current, and overwrite states."""

    required_input = tmp_path / "inputs" / "metrics.parquet"
    output = tmp_path / "outputs" / "summary.csv"

    missing_input = output_readiness(output, inputs=[required_input])
    assert missing_input.should_run is False
    assert missing_input.reason == "missing_inputs"
    assert missing_input.missing_inputs == (required_input,)

    required_input.parent.mkdir()
    required_input.write_text("source\n", encoding="utf-8")

    missing_output = output_readiness(output, inputs=[required_input], sources=[required_input])
    assert missing_output.should_run is True
    assert missing_output.reason == "missing_outputs"
    assert missing_output.missing_outputs == (output,)

    output.parent.mkdir()
    output.write_text("old\n", encoding="utf-8")
    assert output_readiness(output, inputs=[required_input], sources=[required_input]).reason == "current"

    newer_time = output.stat().st_mtime + 10
    os.utime(required_input, (newer_time, newer_time))
    stale = output_readiness(output, inputs=[required_input], sources=[required_input])
    assert stale.should_run is True
    assert stale.reason == "stale_sources"
    assert stale.stale_outputs == (output,)

    forced = output_readiness({"summary": output}, inputs={"metrics": required_input}, overwrite=True)
    assert forced.should_run is True
    assert forced.reason == "overwrite"


def test_finish_figure_uses_rich_display_in_notebooks(monkeypatch):
    """Notebook display should embed figures even when assigned to variables."""

    displayed = []

    def fake_display(fig):
        displayed.append(fig)

    monkeypatch.setattr(figure_io, "_in_notebook", lambda: True)
    monkeypatch.setattr("IPython.display.display", fake_display)

    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    finished = finish_figure(fig, showfig=True, savefig=False)

    assert finished is fig
    assert len(displayed) == 1
    assert displayed[0].data
    assert not plt.fignum_exists(fig.number)


def test_finish_figure_can_keep_displayed_notebook_figures_open(monkeypatch):
    """Callers can opt out of notebook auto-close when they need the figure open."""

    monkeypatch.setattr(figure_io, "_in_notebook", lambda: True)
    monkeypatch.setattr("IPython.display.display", lambda fig: None)

    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    finished = finish_figure(fig, showfig=True, savefig=False, close=False)

    assert finished is fig
    assert plt.fignum_exists(fig.number)
    plt.close(fig)


def test_metric_plan_and_artifact_manifest_are_deterministic(tmp_path):
    config_path = tmp_path / "svtk_config.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  metrics: outputs/metrics/default.csv
run_defaults:
  common:
    components: [Z]
  commands:
    metrics.calculate:
      metrics: [C5, C12]
      passbands:
        - [1, 2]
        - "2-4"
      models: [model_a, model_b]
      output_metrics: outputs/metrics/command.csv
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    plan = metric_plan_from_config(cfg, command="metrics.calculate")
    assert plan.metrics == ("PGA", "delay_corrected_cc")
    assert plan.passbands == ((1.0, 2.0), (2.0, 4.0))
    assert plan.components == ("Z",)
    assert plan.models == ("model_a", "model_b")
    assert plan.output_path == tmp_path / "outputs" / "metrics" / "command.csv"

    spec = ArtifactSpec(
        kind="figure",
        name="Station Bias Map",
        scope={"metric": "C5", "band": "1-2 sec"},
        config={"components": plan.components, "models": plan.models},
        extension=".png",
        subdir="maps",
    )
    first_path = artifact_path_for_spec(tmp_path / "artifacts", spec)
    second_path = artifact_path_for_spec(tmp_path / "artifacts", spec)
    assert first_path == second_path
    assert first_path.name.startswith("station_bias_map__")
    assert first_path.suffix == ".png"
    assert stable_hash(spec.payload()) == stable_hash(spec.payload())

    manifest = write_artifact_manifest(first_path, spec, extra={"created_by": "test"})
    payload = read_artifact_manifest(manifest)
    assert payload["artifact_path"] == str(first_path)
    assert payload["spec"]["name"] == "Station Bias Map"
    assert payload["extra"]["created_by"] == "test"


def test_run_scenario_overlays_config_and_cli_plans(tmp_path):
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
metrics:
  groups: [amplitude]
  components: [R, T]
  passbands: [[1, 2]]
  transforms: [log2_residual]
outputs:
  metrics: outputs/metrics/default.parquet
run_scenarios:
  spectral_review:
    metrics:
      metrics: [PSA]
      components: [Z]
      spectral:
        periods_s: [1.0, 2.0]
    waveforms:
      preprocessing:
        lowpass_hz: 1.0
        filter_order: 4
    outputs:
      metrics: outputs/metrics/spectral.parquet
""",
        encoding="utf-8",
    )

    cfg = SpatialVTKConfig.from_file(config_path, run_scenario="spectral_review")
    assert cfg.run_scenario == "spectral_review"
    assert cfg.run_scenario_names() == ("spectral_review",)
    plan = metric_plan_from_config(cfg, command="metrics.calculate")
    assert plan.metrics == ("PSA",)
    assert plan.components == ("Z",)
    assert plan.spectral_periods_s == (1.0, 2.0)
    assert plan.waveform_lowpass_hz == 1.0
    assert plan.waveform_filter_order == 4
    assert plan.output_path == tmp_path / "outputs" / "metrics" / "spectral.parquet"

    override_plan = metric_plan_from_config(cfg, command="metrics.calculate", overrides={"metrics": ["PGA"], "components": ["R"]})
    assert override_plan.metrics == ("PGA",)
    assert override_plan.components == ("R",)


def test_waveform_preprocessing_uses_active_config(tmp_path):
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
waveforms:
  preprocessing:
    lowpass_hz:
    filter_order: 4
run_scenarios:
  tutorial:
    waveforms:
      preprocessing:
        lowpass_hz: 1.0
        filter_order: 4
""",
        encoding="utf-8",
    )
    try:
        SpatialVTKConfig.from_file(config_path, run_scenario="tutorial").activate()
        settings = waveform_preprocessing_from_config()
        assert settings.lowpass_hz == 1.0
        assert settings.filter_order == 4
        assert waveform_preprocessing_label() == "Filter: lowpass 1 Hz"

        dt = 0.01
        time = np.arange(0.0, 2.0, dt)
        signal = np.sin(2.0 * np.pi * 0.5 * time)
        high_frequency = 5.0 * np.sin(2.0 * np.pi * 20.0 * time)
        filtered = apply_waveform_preprocessing(signal + high_frequency, dt)
        assert np.max(np.abs(filtered - signal)) < np.max(np.abs(high_frequency))
    finally:
        clear_active_config()


def test_waveform_preprocessing_supports_bandpass_and_resampling(tmp_path):
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
waveforms:
  preprocessing:
    bandpass_hz: [0.5, 4.0]
    resample_hz: 20.0
    filter_order: 3
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    settings = waveform_preprocessing_from_config(cfg)

    assert settings.bandpass_low_hz == 0.5
    assert settings.bandpass_high_hz == 4.0
    assert settings.resample_hz == 20.0
    assert settings.filter_order == 3
    assert waveform_preprocessing_label(settings) == "Filter: bandpass 0.5-4 Hz; resample 20 Hz"

    dt = 0.01
    time = np.arange(0.0, 2.0, dt)
    signal = np.sin(2.0 * np.pi * 1.0 * time) + 0.1 * np.sin(2.0 * np.pi * 20.0 * time)
    result = apply_waveform_preprocessing_with_metadata(signal, dt, settings)

    assert result.sampling_rate_hz == pytest.approx(20.0)
    assert result.dt == pytest.approx(0.05)
    assert 35 <= result.data.size <= 45


def test_empty_config_has_no_private_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    monkeypatch.setenv(SVTK_CLI_CONFIG_ENV, str(tmp_path / "missing-cli-config.json"))
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        cfg = SpatialVTKConfig.from_file()
    finally:
        os.chdir(cwd)
    assert cfg.data == {}
    assert cfg.run_defaults("metrics.calculate") == {}
    assert cfg.bounds_presets() == {}
    assert cfg.path("paths.observed_root") is None
    assert resolve_run_defaults({}, "metrics.calculate") == {}
