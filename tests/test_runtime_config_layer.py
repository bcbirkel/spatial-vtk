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
    SlurmSubmission,
    SpatialVTKConfig,
    active_config,
    clear_saved_config_path,
    clear_active_config,
    configured_output_registry_frame,
    configured_output_registry_preview_frame,
    display_notebook_step_result,
    find_config_file,
    format_run_time,
    metric_display_name,
    notebook_dashboard_launch_commands,
    notebook_figure_settings,
    notebook_figure_sidecar_settings,
    notebook_run_context,
    notebook_step_result,
    notebook_step_result_frame,
    display_output_table_previews,
    get_saved_config_path,
    load_config,
    notebook_timing_enabled,
    prepare_notebook_geospatial_environment,
    register_svtk_cell_timer,
    render_notebook_figure,
    resolve_output_path,
    resolve_run_defaults,
    run_notebook_step_if_needed,
    run_or_submit_notebook_function,
    set_saved_config_path,
    submit_notebook_slurm_script,
    write_notebook_python_slurm_script,
)
from spatial_vtk.config.notebook import run_or_submit_notebook_cli_command
from spatial_vtk.io import (
    ArtifactSpec,
    apply_waveform_preprocessing_with_metadata,
    apply_waveform_preprocessing,
    artifact_path_for_spec,
    default_output_paths,
    output_group,
    read_artifact_manifest,
    metric_plan_from_config,
    output_group_completion,
    output_group_namespace,
    output_group_paths,
    output_group_status,
    output_group_status_frame,
    output_readiness,
    output_status_frame,
    preprocessed_waveform_output_group,
    required_outputs_exist,
    load_standard_ingest_workflow_outputs,
    metadata_tables_readiness_from_config,
    preprocessing_readiness_from_config,
    record_coverage_readiness_from_config,
    should_rebuild_paths,
    should_rebuild_outputs,
    stable_hash,
    waveform_preprocessing_from_config,
    waveform_preprocessing_label,
    write_artifact_manifest,
    write_table,
    write_output_table,
)
import spatial_vtk.visualize.figure_io as figure_io
import spatial_vtk.config.notebook as notebook_helpers
from spatial_vtk.visualize.figure_io import finish_figure
from spatial_vtk.visualize import default_figure_paths
from spatial_vtk.visualize.figure_sidecars import (
    FigureSidecarResult,
    figure_sidecar_status_frame,
    read_figure_sidecar_metadata,
    write_figure_row_sidecar,
)
from spatial_vtk.visualize.dashboard import (
    dashboard_metric_dataset_readiness_frame,
    dashboard_map_readiness,
    dashboard_output_namespace,
    dashboard_output_readiness,
    dashboard_ready_value,
    dashboard_readiness_summary_frame,
    dashboard_summary_readiness_frame,
    dashboard_summary_table_contracts,
    display_dashboard_preparation_result,
    find_available_port,
    filter_optional_dashboard_summary,
    prepare_configured_dashboard_datasets_from_notebook_settings,
    row_value_column_for_summary,
)
from spatial_vtk.visualize.dashboard.export import load_dashboard_metric_dataset
from spatial_vtk.spatial import (
    boundary_corridor_readiness_from_config,
    geojson_region_summary_readiness_from_config,
    load_standard_spatial_workflow_output_status,
    spatial_statistics_settings_from_config,
    spatial_derived_outputs_readiness_from_config,
    spatial_summary_readiness_from_config,
)
from spatial_vtk.qc import (
    load_standard_qc_inputs,
    load_standard_qc_workflow_outputs,
    qc_inventory_readiness_from_config,
    qc_overlap_readiness_from_config,
    qc_summary_readiness_from_config,
)
from spatial_vtk.metrics import (
    load_standard_metric_workflow_outputs,
    metric_inventories_readiness_from_config,
    metric_manifest_readiness_from_config,
)
from spatial_vtk.spatial import (
    load_standard_additional_plotting_output_status,
    load_standard_geojson_plotting_inputs,
    load_standard_geojson_workflow_output_status,
)


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

    sys.modules.pop("spatial_vtk.visualize.dashboard.streamlit_metrics", None)
    sys.modules.pop("spatial_vtk.visualize.dashboard.streamlit_qc", None)

    import spatial_vtk.visualize.dashboard as dashboard_helpers
    import spatial_vtk.visualize as visualize_helpers

    assert dashboard_helpers.dashboard_summary_readiness_frame is dashboard_summary_readiness_frame
    assert dashboard_helpers.filter_optional_dashboard_summary is filter_optional_dashboard_summary
    assert callable(dashboard_helpers.launch_configured_metrics_dashboard)
    assert callable(dashboard_helpers.launch_configured_qc_dashboard)
    assert dashboard_helpers.row_value_column_for_summary is row_value_column_for_summary
    assert visualize_helpers.write_figure_row_sidecar is write_figure_row_sidecar
    assert visualize_helpers.figure_sidecar_status_frame is figure_sidecar_status_frame
    assert visualize_helpers.read_figure_sidecar_metadata is read_figure_sidecar_metadata
    assert visualize_helpers.FigureSidecarResult is FigureSidecarResult
    assert "spatial_vtk.visualize.dashboard.streamlit_metrics" not in sys.modules
    assert "spatial_vtk.visualize.dashboard.streamlit_qc" not in sys.modules


def test_dashboard_find_available_port_skips_occupied_port(monkeypatch):
    """Dashboard auto-port selection should avoid an occupied local port."""

    import spatial_vtk.visualize.dashboard.launch as dashboard_launch

    monkeypatch.setattr(dashboard_launch, "_port_is_available", lambda _address, port: int(port) >= 8503)

    assert find_available_port(server_address="127.0.0.1", start_port=8501, max_tries=3) == 8503


def test_dashboard_port_helpers_validate_search_bounds():
    """Dashboard launch helpers should report invalid port settings clearly."""

    import spatial_vtk.visualize.dashboard.launch as dashboard_launch

    with pytest.raises(ValueError, match="Dashboard port must be an integer from 1 to 65535"):
        dashboard_launch.find_available_port(start_port=0)
    with pytest.raises(ValueError, match="Dashboard port must be an integer from 1 to 65535"):
        dashboard_launch.find_available_port(start_port=65536)
    with pytest.raises(ValueError, match="max_tries must be a positive integer"):
        dashboard_launch.find_available_port(start_port=8501, max_tries=0)
    with pytest.raises(ValueError, match="exceeds port 65535"):
        dashboard_launch.find_available_port(start_port=65535, max_tries=2)


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
            "qc_availability",
            "post_qc_records",
            "qc_drop_causes_overlap",
        ],
    )
    figures = default_figure_paths(tmp_path / "figures")

    assert tables.qc_inventory == tmp_path / "tables" / "qc_inventory.csv"
    assert tables.qc_inventory_overlap == tmp_path / "tables" / "qc_inventory_overlap.parquet"
    assert tables.manual_review_queue == tmp_path / "tables" / "manual_review_queue.csv"
    assert tables.qc_metric_pair_retention == tmp_path / "tables" / "qc_metric_pair_retention.csv"
    assert tables.qc_availability == tmp_path / "tables" / "qc_availability.csv"
    assert tables.post_qc_records == tmp_path / "tables" / "post_qc_records.csv"
    assert tables.qc_drop_causes_overlap == tmp_path / "tables" / "qc_drop_causes_overlap.csv"
    assert figures.retention_summary == tmp_path / "figures" / "retention_summary.png"
    assert figures.qc_drop_cause_diagnostics_overlap == tmp_path / "figures" / "qc_drop_cause_diagnostics_overlap.png"
    assert figures.station_event_context == tmp_path / "figures" / "station_event_context.png"
    assert figures.observed_synthetic_record_section == tmp_path / "figures" / "observed_synthetic_record_section.png"
    assert figures.waveform_overlay_matrix == tmp_path / "figures" / "waveform_overlay_matrix.png"


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


def test_prepare_notebook_geospatial_environment_sets_loky_cpu_count(monkeypatch):
    """Notebook bootstrap should own optional loky CPU-count setup."""

    monkeypatch.delenv("LOKY_MAX_CPU_COUNT", raising=False)

    removed = prepare_notebook_geospatial_environment(clear_proj_env=False, loky_max_cpu_count=1)

    assert removed == {}
    assert os.environ["LOKY_MAX_CPU_COUNT"] == "1"
    monkeypatch.setenv("LOKY_MAX_CPU_COUNT", "4")

    prepare_notebook_geospatial_environment(clear_proj_env=False, loky_max_cpu_count=1)

    assert os.environ["LOKY_MAX_CPU_COUNT"] == "4"


def test_notebook_run_context_resolves_config_dirs_and_flags(tmp_path, monkeypatch):
    """Notebook setup should be reusable instead of redefined in each notebook."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    monkeypatch.setenv(SVTK_CLI_CONFIG_ENV, str(tmp_path / "cli-config.json"))
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
    monkeypatch.setenv("SVTK_QC_CHUNKSIZE", "250000")
    monkeypatch.setenv("SVTK_DASHBOARD_CHUNKSIZE", "75000")
    monkeypatch.setenv("SVTK_METRIC_BATCH_COUNT", "37")
    monkeypatch.setenv("SVTK_PREPROCESS_CONTINUE_ON_ERROR", "0")

    context = notebook_run_context(start=repo / "docs", create_dirs=True)

    assert context.repo_root == repo.resolve()
    assert context.config_path == config_path.resolve()
    assert context.run_scenario is None
    expected_outputs = config_path.parent / "run_outputs"
    assert context.outputs_root == expected_outputs
    assert context.tables_dir == expected_outputs / "tables"
    assert context.figures_dir == expected_outputs / "figures"
    assert context.dashboards_dir == expected_outputs / "dashboards"
    assert context.slurm_dir == expected_outputs / "slurm"
    assert context.submit_slurm is True
    assert context.overwrite is True
    assert context.preview_rows == 12
    assert context.qc_chunksize == 250000
    assert context.dashboard_chunksize == 75000
    assert context.metric_batch_count == 37
    assert context.preprocess_continue_on_error is False
    assert context.tables_dir.exists()

    clear_active_config()


def test_notebook_run_context_uses_committed_example_config_when_no_run_config_exists(tmp_path, monkeypatch):
    """Fresh-checkout large-run notebooks should fall back to the example config."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    monkeypatch.setenv(SVTK_CLI_CONFIG_ENV, str(tmp_path / "cli-config.json"))
    repo = tmp_path / "project"
    (repo / "src" / "spatial_vtk").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='spatial-vtk'\n", encoding="utf-8")
    config_path = repo / "data" / "examples" / "configuration" / "example_spatial_vtk_config.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        f"""
project:
  name: tutorial
  root_dir: {repo}
outputs:
  root: outputs/tutorials
""",
        encoding="utf-8",
    )

    context = notebook_run_context(start=repo / "docs" / "examples", create_dirs=False)

    assert context.config_path == config_path.resolve()
    assert context.cfg.root_dir == repo.resolve()
    clear_active_config()


def test_notebook_run_context_applies_requested_run_scenario(tmp_path, monkeypatch):
    """Large-run notebook setup should be able to apply the tutorial overlay."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    monkeypatch.setenv(SVTK_CLI_CONFIG_ENV, str(tmp_path / "cli-config.json"))
    repo = tmp_path / "project"
    (repo / "src" / "spatial_vtk").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='spatial-vtk'\n", encoding="utf-8")
    config_path = repo / "data" / "examples" / "configuration" / "example_spatial_vtk_config.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        f"""
project:
  name: base
  root_dir: {repo}
paths:
  station_metadata: data/metadata/stations.csv
outputs:
  root: outputs/base
run_scenarios:
  tutorial:
    paths:
      station_metadata: data/examples/example_five_event_subset/metadata/selected_stations.csv
    outputs:
      root: "{{root_dir}}/outputs/tutorials"
""",
        encoding="utf-8",
    )

    context = notebook_run_context(start=repo / "docs" / "examples", run_scenario="tutorial", create_dirs=False)

    assert context.run_scenario == "tutorial"
    assert context.cfg.run_scenario == "tutorial"
    assert context.outputs_root == repo / "outputs" / "tutorials"
    assert context.cfg.section("paths.station_metadata") == "data/examples/example_five_event_subset/metadata/selected_stations.csv"
    clear_active_config()


def test_notebook_run_context_applies_environment_run_scenario(tmp_path, monkeypatch):
    """Notebook cells should not need to parse SVTK_RUN_SCENARIO directly."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    monkeypatch.setenv(SVTK_CLI_CONFIG_ENV, str(tmp_path / "cli-config.json"))
    monkeypatch.setenv("SVTK_RUN_SCENARIO", "tutorial")
    repo = tmp_path / "project"
    (repo / "src" / "spatial_vtk").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='spatial-vtk'\n", encoding="utf-8")
    config_path = repo / "data" / "examples" / "configuration" / "example_spatial_vtk_config.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        f"""
project:
  name: base
  root_dir: {repo}
outputs:
  root: outputs/base
run_scenarios:
  tutorial:
    outputs:
      root: "{{root_dir}}/outputs/tutorials"
""",
        encoding="utf-8",
    )

    context = notebook_run_context(start=repo / "docs" / "examples", create_dirs=False)

    assert context.run_scenario == "tutorial"
    assert context.cfg.run_scenario == "tutorial"
    assert context.outputs_root == repo / "outputs" / "tutorials"
    clear_active_config()


def test_notebook_run_context_honors_saved_cli_config(tmp_path, monkeypatch):
    """Large-run notebooks should work after users run ``svtk config set``."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    monkeypatch.setenv(SVTK_CLI_CONFIG_ENV, str(tmp_path / "cli-config.json"))
    repo = tmp_path / "project"
    (repo / "src" / "spatial_vtk").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='spatial-vtk'\n", encoding="utf-8")
    example_config = repo / "data" / "examples" / "configuration" / "example_spatial_vtk_config.yaml"
    example_config.parent.mkdir(parents=True)
    example_config.write_text("project:\n  name: example\n  root_dir: .\n", encoding="utf-8")
    saved_config = tmp_path / "saved.yaml"
    saved_config.write_text(
        f"""
project:
  name: saved
  root_dir: {repo}
""",
        encoding="utf-8",
    )
    set_saved_config_path(saved_config)

    context = notebook_run_context(start=repo / "docs" / "examples", create_dirs=False)

    assert context.config_path == saved_config.resolve()
    assert context.cfg.section("project.name") == "saved"
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
    assert generic.kwargs(plural=True) == {
        "write_sidecars": True,
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

    empty_status = explicit.status_frame()
    assert list(figure_sidecar_status_frame(explicit.directory).columns) == [
        column for column in empty_status.columns if column in figure_sidecar_status_frame(explicit.directory).columns
    ]
    assert len(empty_status) == 1
    assert empty_status.loc[0, "figure"] == "figure_sidecar_status"
    assert empty_status.loc[0, "sidecar_status"] == "missing_directory"
    assert "has not been created" in empty_status.loc[0, "sidecar_message"]
    assert bool(empty_status.loc[0, "sidecars_enabled"]) is True
    assert bool(empty_status.loc[0, "sidecar_dir_exists"]) is False
    assert empty_status.loc[0, "sidecar_metadata_count"] == 0
    readiness = explicit.readiness_frame().set_index("name")
    assert {"artifact", "artifact_label", "artifact_role", "status", "resolved_path", "path", "exists"} <= set(
        readiness.columns
    )
    assert readiness.loc["enabled", "value"] is True
    assert readiness.loc["enabled", "artifact"] == "figure_sidecar_enabled"
    assert readiness.loc["enabled", "artifact_role"] == "figure_sidecar_setting"
    assert readiness.loc["enabled", "status"] == "missing_directory"
    assert readiness.loc["directory", "value"] == str(tmp_path / "custom_sidecars")
    assert readiness.loc["metadata_file_count", "value"] == 0
    assert readiness.loc["row_policy", "value"] == "deterministic_sample"
    assert readiness.loc["row_limit", "value"] == 10
    assert "has not been created" in readiness.loc["message", "value"]

    write_figure_row_sidecar(
        tmp_path / "figures" / "station_metric_map.png",
        pd.DataFrame(
            {
                "station": ["STA1", "STA2"],
                "event_id": ["ev1", "ev2"],
                "metric": ["PGA", "PGA"],
            }
        ),
        sidecar_dir=explicit.directory,
        metadata={"aggregation_contract": "station_event_rows_to_station_summary"},
    )
    status = explicit.status_frame().set_index("figure")
    assert "station_metric_map.png" in status.index
    assert status.loc["station_metric_map.png", "plot_row_count"] == 2
    assert status.loc["station_metric_map.png", "aggregation_contract"] == "station_event_rows_to_station_summary"
    ready_after_write = explicit.readiness_frame().set_index("name")
    assert ready_after_write.loc["enabled", "status"] == "ready"
    assert ready_after_write.loc["metadata_file_count", "value"] == 1
    assert "metadata is available" in ready_after_write.loc["message", "value"]

    no_directory = notebook_figure_sidecar_settings("metric")
    no_directory_status = no_directory.status_frame()
    assert len(no_directory_status) == 1
    assert no_directory_status.loc[0, "figure"] == "figure_sidecar_status"
    assert no_directory_status.loc[0, "sidecar_status"] == "disabled"
    assert "disabled" in no_directory_status.loc[0, "sidecar_message"]
    assert bool(no_directory_status.loc[0, "sidecars_enabled"]) is False
    assert bool(no_directory_status.loc[0, "sidecar_dir_exists"]) is False
    disabled = no_directory.readiness_frame().set_index("name")
    assert disabled.loc["enabled", "value"] is False
    assert disabled.loc["enabled", "status"] == "disabled"
    assert "disabled" in disabled.loc["message", "value"]


def test_notebook_figure_settings_parse_common_controls(tmp_path, monkeypatch):
    """Notebook figure controls should be centralized and family-aware."""

    monkeypatch.setenv("SVTK_MAKE_FIGURES", "1")
    monkeypatch.setenv("SVTK_MAKE_METRIC_FIGURES", "0")
    monkeypatch.setenv("SVTK_ADD_BASEMAP", "1")
    monkeypatch.setenv("SVTK_FIGURE_SHOWFIG", "1")
    monkeypatch.setenv("SVTK_METRIC_FIGURE_PASSBAND", "2-3 sec")
    monkeypatch.setenv("SVTK_FIGURE_COMPONENTS", "R, T, Z")
    monkeypatch.setenv("SVTK_FIGURE_MODEL", "cvmsi")
    monkeypatch.setenv("SVTK_METRIC_FIGURE_SAMPLE_ROWS", "1234")
    monkeypatch.setenv("SVTK_FIGURE_ROBUST_PERCENTILE", "97.5")
    monkeypatch.setenv("SVTK_STATION_AGGREGATION", "median")
    monkeypatch.setenv("SVTK_FIGURE_COMPARE_TO", "LA Basin")
    monkeypatch.setenv("SVTK_FIGURE_COMPARISON_TABLE", "1")
    monkeypatch.setenv("SVTK_METRIC_FIGURE_PCA_MODE", "PC2")
    monkeypatch.setenv("SVTK_FIGURE_SIDECARS", "1")
    monkeypatch.setenv("SVTK_FIGURE_SIDECAR_ROWS", "25")

    settings = notebook_figure_settings("metric", figure_dir=tmp_path / "figures")

    assert settings.figure_kind == "metric"
    assert settings.figure_dir == tmp_path / "figures"
    assert settings.figure_dir.exists()
    assert settings.make_figures is False
    assert settings.add_basemap is True
    assert settings.showfig is True
    assert settings.passband == "2-3 sec"
    assert settings.components == ["R", "T", "Z"]
    assert settings.model == "cvmsi"
    assert settings.sample_rows == 1234
    assert settings.robust_axis_percentile == 97.5
    assert settings.station_aggregation == "median"
    assert settings.compare_to == "LA Basin"
    assert settings.comparison_table is True
    assert settings.pca_mode == "PC2"
    assert settings.sidecars.enabled is True
    assert settings.sidecars.rows == 25
    sidecar_readiness = settings.sidecars.readiness_frame().set_index("name")
    assert {"artifact", "artifact_label", "artifact_role", "status", "resolved_path", "path", "exists"} <= set(
        sidecar_readiness.columns
    )
    assert sidecar_readiness.loc["directory", "artifact"] == "figure_sidecar_directory"
    assert sidecar_readiness.loc["directory", "artifact_role"] == "figure_sidecar_setting"
    assert sidecar_readiness.loc["directory", "status"] == "missing_directory"
    assert sidecar_readiness.loc["directory", "path"] == str(tmp_path / "figures" / "sidecars")
    assert bool(sidecar_readiness.loc["directory", "exists"]) is False

    context_kwargs = settings.context_kwargs(include_station_aggregation=True)
    assert context_kwargs["make_figures"] is False
    assert context_kwargs["sample_rows"] == 1234
    assert context_kwargs["default_passband"] == "2-3 sec"
    assert context_kwargs["default_components"] == ["R", "T", "Z"]
    assert context_kwargs["default_showfig"] is True
    assert context_kwargs["default_model"] == "cvmsi"
    assert context_kwargs["add_basemap"] is True
    assert context_kwargs["robust_axis_percentile"] == 97.5
    assert context_kwargs["station_aggregation"] == "median"
    assert context_kwargs["write_sidecars"] is True
    assert context_kwargs["sidecar_rows"] == 25
    assert context_kwargs["sidecar_dir"] == tmp_path / "figures" / "sidecars"

    assert settings.plot_kwargs(include_basemap=True) == {
        "showfig": True,
        "write_sidecar": True,
        "sidecar_rows": 25,
        "sidecar_dir": tmp_path / "figures" / "sidecars",
        "add_basemap": True,
    }

    assert settings.plot_selection_kwargs(
        value_col="log2_residual",
        include_basemap=True,
        include_robust_axis_percentile=True,
    ) == {
        "passband": "2-3 sec",
        "components": ["R", "T", "Z"],
        "model": "cvmsi",
        "showfig": True,
        "value_col": "log2_residual",
        "add_basemap": True,
        "robust_axis_percentile": 97.5,
    }
    all_selection_kwargs = settings.plot_selection_kwargs(passband=None, model=None)
    assert all_selection_kwargs["passband"] is None
    assert all_selection_kwargs["model"] is None


def test_render_notebook_figure_owns_output_sidecar_display_and_close(tmp_path, monkeypatch):
    """Notebook figure calls should not repeat path, sidecar, display, and close plumbing."""

    monkeypatch.setenv("SVTK_MAKE_FIGURES", "1")
    monkeypatch.setenv("SVTK_ADD_BASEMAP", "1")
    monkeypatch.setenv("SVTK_FIGURE_SIDECARS", "1")
    monkeypatch.setenv("SVTK_FIGURE_SIDECAR_ROWS", "5")
    settings = notebook_figure_settings("spatial", figure_dir=tmp_path / "figures")
    seen: dict[str, object] = {}
    displayed: list[object] = []
    closed: list[object] = []
    monkeypatch.setattr(plt, "close", lambda figure: closed.append(figure))

    class Outputs:
        def figure_path(self, name, *, stem=None, stem_parts=None):
            seen["path_name"] = name
            seen["stem"] = stem
            seen["stem_parts"] = tuple(stem_parts or ())
            return tmp_path / "figures" / "step_05_geojson_regions.png"

    def _plot_func(data, **kwargs):
        seen["data"] = data
        seen["kwargs"] = kwargs
        return "figure-object"

    result = render_notebook_figure(
        _plot_func,
        Outputs(),
        "geojson_polygons_map_path",
        settings,
        "regions.geojson",
        stem_parts=("step_05", "geojson_regions"),
        include_basemap=True,
        display_func=displayed.append,
        title="Regions",
    )

    assert result == "figure-object"
    assert displayed == ["figure-object"]
    assert closed == ["figure-object"]
    assert seen["path_name"] == "geojson_polygons_map_path"
    assert seen["stem_parts"] == ("step_05", "geojson_regions")
    assert seen["data"] == "regions.geojson"
    assert seen["kwargs"] == {
        "showfig": False,
        "write_sidecar": True,
        "sidecar_rows": 5,
        "sidecar_dir": tmp_path / "figures" / "sidecars",
        "add_basemap": True,
        "savefig": True,
        "outpath": tmp_path / "figures" / "step_05_geojson_regions.png",
        "title": "Regions",
    }

    displayed.clear()
    showing_settings = notebook_figure_settings("spatial", figure_dir=tmp_path / "figures")
    object.__setattr__(showing_settings, "showfig", True)
    render_notebook_figure(
        _plot_func,
        Outputs(),
        "geojson_polygons_map_path",
        showing_settings,
        "regions.geojson",
        stem_parts=("step_05", "geojson_regions"),
        include_basemap=True,
        display_func=displayed.append,
        close=False,
    )
    assert displayed == []


def test_notebook_figure_settings_default_to_configured_figure_dir(tmp_path, monkeypatch):
    """Notebook figure settings should own configured figure-directory resolution."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  root: run_outputs
  figures: run_outputs/custom_figures
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()

    settings = notebook_figure_settings("metric")

    assert active_config() is cfg
    assert settings.figure_dir == tmp_path / "run_outputs" / "custom_figures"
    assert settings.figure_dir.exists()
    assert settings.sidecars.directory == tmp_path / "run_outputs" / "custom_figures" / "sidecars"

    metric_settings = notebook_figure_settings("metric", figure_subdir="metrics")

    assert metric_settings.figure_dir == tmp_path / "run_outputs" / "custom_figures" / "metrics"
    assert metric_settings.figure_dir.exists()
    assert metric_settings.sidecars.directory == tmp_path / "run_outputs" / "custom_figures" / "metrics" / "sidecars"


def test_notebook_figure_settings_render_gate_reports_disabled_and_missing_inputs(tmp_path, monkeypatch):
    """Figure blocks should use package-owned gating instead of repeated path checks."""

    monkeypatch.delenv("SVTK_MAKE_FIGURES", raising=False)
    missing = tmp_path / "missing.csv"
    settings = notebook_figure_settings("qc", figure_dir=tmp_path / "figures")

    disabled_gate = settings.render_gate([missing])

    assert disabled_gate.ready is False
    assert disabled_gate.figures_enabled is False
    assert disabled_gate.missing_paths == ()
    assert "SVTK_MAKE_FIGURES=1" in disabled_gate.message
    disabled_status = disabled_gate.status_frame()
    assert disabled_status.loc[0, "name"] == "figure_render_gate"
    assert disabled_status.loc[0, "artifact"] == "figure_render_gate"
    assert disabled_status.loc[0, "artifact_label"] == "figure render gate"
    assert disabled_status.loc[0, "artifact_role"] == "notebook_render_gate"
    assert disabled_status.loc[0, "status"] == "disabled"

    monkeypatch.setenv("SVTK_MAKE_FIGURES", "1")
    enabled = notebook_figure_settings("qc", figure_dir=tmp_path / "figures")
    missing_gate = enabled.render_gate([missing], missing_message="QC inputs are missing.")

    assert missing_gate.ready is False
    assert missing_gate.figures_enabled is True
    assert missing_gate.missing_paths == (missing,)
    assert missing_gate.message == "QC inputs are missing."
    missing_status = missing_gate.status_frame()
    assert missing_status.loc[0, "artifact"] == "figure_render_gate"
    assert missing_status.loc[0, "artifact_role"] == "notebook_render_gate"
    assert missing_status.loc[0, "status"] == "missing_inputs"
    assert list(missing_status["missing_path"]) == [str(missing)]

    unconfigured_gate = enabled.render_gate([None])

    assert unconfigured_gate.ready is False
    assert unconfigured_gate.missing_paths == (Path("<not configured>"),)
    unconfigured_status = unconfigured_gate.status_frame()
    assert unconfigured_status.loc[0, "status"] == "missing_inputs"
    assert "<not configured>" in set(unconfigured_status["missing_path"])

    missing.write_text("ready\n", encoding="utf-8")
    ready_gate = enabled.render_gate([missing])

    assert ready_gate.ready is True
    assert ready_gate.message == "Figure inputs are ready."
    ready_status = ready_gate.status_frame()
    assert bool(ready_status.loc[0, "ready"]) is True
    assert ready_status.loc[0, "status"] == "ready"


def test_notebook_figure_settings_parse_region_legacy_controls(tmp_path, monkeypatch):
    """Region notebooks should keep their existing SVTK_REGION_* controls."""

    monkeypatch.setenv("SVTK_MAKE_FIGURES", "1")
    monkeypatch.setenv("SVTK_ADD_BASEMAP", "1")
    monkeypatch.setenv("SVTK_REGION_FIGURE_ROWS", "4321")
    monkeypatch.setenv("SVTK_REGION_BOX_METRIC", "PGV")
    monkeypatch.setenv("SVTK_REGION_BOX_PASSBAND", "3-5 sec")
    monkeypatch.setenv("SVTK_REGION_BOX_COMPONENT", "R")
    monkeypatch.setenv("SVTK_REGION_BOX_MODEL", "model-a")
    monkeypatch.setenv("SVTK_REGION_VALUE_COL", "log2_residual")
    monkeypatch.setenv("SVTK_REGION_COMPARE_TO", "basin")
    monkeypatch.setenv("SVTK_FIGURE_SHOWFIG", "1")

    settings = notebook_figure_settings(
        "region",
        figure_dir=tmp_path / "figures",
        default_metric="PGA",
        default_passband="2-3 sec",
        default_sidecar_rows=1000,
    )

    assert settings.make_figures is True
    assert settings.add_basemap is True
    assert settings.sample_rows == 4321
    assert settings.metric == "PGV"
    assert settings.passband == "3-5 sec"
    assert settings.component == "R"
    assert settings.components == ["R"]
    assert settings.model == "model-a"
    assert settings.value_col == "log2_residual"
    assert settings.compare_to == "basin"
    assert settings.showfig is True
    assert settings.sidecars.rows == 1000


def test_notebook_figure_settings_parse_spatial_pca_mode(monkeypatch):
    """Spatial PCA figure mode should be owned by package settings."""

    monkeypatch.setenv("SVTK_PCA_MODE", "PC3")

    settings = notebook_figure_settings("spatial")

    assert settings.pca_mode == "PC3"


def test_notebook_figure_settings_parse_score_trend_controls(tmp_path, monkeypatch):
    """Score-trend diagnostics should use package settings instead of notebook env parsing."""

    monkeypatch.setenv("SVTK_MAKE_SCORE_TRENDS", "1")
    monkeypatch.setenv("SVTK_SCORE_TREND_COLUMNS", "anderson_2004_gof, olsen_mayhew_gof")
    monkeypatch.setenv("SVTK_SCORE_TREND_FIGURE_SHOWFIG", "1")

    settings = notebook_figure_settings(
        "score_trend",
        figure_dir=tmp_path / "figures",
        default_score_columns=("score",),
    )

    assert settings.make_figures is True
    assert settings.score_columns == ["anderson_2004_gof", "olsen_mayhew_gof"]
    assert settings.showfig is True


def test_notebook_figure_settings_keeps_score_trends_opt_in(tmp_path, monkeypatch):
    """Generic figure rendering should not enable optional GOF score trends."""

    monkeypatch.setenv("SVTK_MAKE_FIGURES", "1")

    settings = notebook_figure_settings("score_trend", figure_dir=tmp_path / "figures")

    assert settings.make_figures is False


def test_notebook_dashboard_launch_commands_default_to_auto_port(tmp_path, monkeypatch):
    """Notebook dashboard commands should be config-backed and collision tolerant."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text("project:\n  root_dir: .\n", encoding="utf-8")
    monkeypatch.delenv("SVTK_METRICS_DASHBOARD_PORT", raising=False)
    monkeypatch.delenv("SVTK_QC_DASHBOARD_PORT", raising=False)
    monkeypatch.delenv("SVTK_LAUNCH_METRICS_DASHBOARD", raising=False)
    monkeypatch.delenv("SVTK_LAUNCH_QC_DASHBOARD", raising=False)
    monkeypatch.delenv("SVTK_DASHBOARD_AUTO_PORT", raising=False)
    monkeypatch.delenv("SVTK_DASHBOARD_PROXY_MODE", raising=False)
    monkeypatch.delenv("SVTK_METRICS_DASHBOARD_ROW_LIMIT", raising=False)
    monkeypatch.delenv("SVTK_METRICS_DASHBOARD_SUMMARY_DISPLAY_ROWS", raising=False)
    monkeypatch.delenv("SVTK_DASHBOARD_DISPLAY_ROWS", raising=False)
    monkeypatch.delenv("SVTK_METRICS_DASHBOARD_DOWNLOAD_ROWS", raising=False)
    monkeypatch.delenv("SVTK_DASHBOARD_DOWNLOAD_ROWS", raising=False)

    commands = notebook_dashboard_launch_commands(config_path)

    assert commands.metrics_port == 8501
    assert commands.qc_port == 8502
    assert commands.launch_metrics_dashboard is False
    assert commands.launch_qc_dashboard is False
    assert commands.auto_port is True
    assert commands.proxy_mode is False
    assert commands.config_path == config_path.resolve()
    assert commands.metrics_command == f"svtk dashboard metrics --config {config_path} --port 8501 --auto-port"
    assert commands.qc_command == f"svtk dashboard qc --config {config_path} --port 8502 --auto-port"
    assert commands.metrics_launch_kwargs(show=False) == {
        "config_path": config_path.resolve(),
        "server_port": 8501,
        "auto_port": True,
        "proxy_mode": False,
        "show": False,
    }
    assert commands.qc_launch_kwargs(show=False) == {
        "config_path": config_path.resolve(),
        "server_port": 8502,
        "auto_port": True,
        "proxy_mode": False,
        "show": False,
    }
    status = commands.status_frame().set_index("dashboard")
    assert status.loc["metrics", "name"] == "metrics_dashboard"
    assert status.loc["metrics", "artifact"] == "metrics_dashboard"
    assert status.loc["metrics", "artifact_label"] == "metrics dashboard launch plan"
    assert status.loc["metrics", "artifact_role"] == "dashboard_launch_plan"
    assert status.loc["metrics", "status"] == "command"
    assert status.loc["metrics", "requested_port"] == 8501
    assert bool(status.loc["metrics", "launch_requested"]) is False
    assert bool(status.loc["metrics", "config_exists"]) is True
    assert status.loc["metrics", "metrics_dataset_dir"] == str(
        tmp_path / "outputs" / "dashboards" / "metrics_dashboard"
    )
    assert bool(status.loc["metrics", "metrics_dataset_dir_exists"]) is False
    assert status.loc["metrics", "dashboard_summary_table_dir"] == str(
        tmp_path / "outputs" / "dashboards" / "dashboard_summaries"
    )
    assert bool(status.loc["metrics", "dashboard_summary_table_dir_exists"]) is False
    assert pd.isna(status.loc["metrics", "qc_trace_summary_table_exists"])
    assert status.loc["qc", "requested_port"] == 8502
    assert status.loc["qc", "name"] == "qc_dashboard"
    assert status.loc["qc", "artifact"] == "qc_dashboard"
    assert status.loc["qc", "artifact_label"] == "QC dashboard launch plan"
    assert status.loc["qc", "artifact_role"] == "dashboard_launch_plan"
    assert status.loc["qc", "status"] == "command"
    assert bool(status.loc["qc", "launch_requested"]) is False
    assert status.loc["qc", "qc_trace_summary_table"] == str(
        tmp_path / "outputs" / "tables" / "qc_trace_summary.csv"
    )
    assert bool(status.loc["qc", "qc_trace_summary_table_exists"]) is False
    assert "trace_summary_table" not in status.columns
    assert "svtk dashboard metrics" in status.loc["metrics", "terminal_command"]


def test_notebook_dashboard_launch_commands_parse_env_and_scenario(tmp_path, monkeypatch):
    """Notebook dashboard commands should expose proxy and scenario options clearly."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
run_scenarios:
  large-run: {}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("SVTK_METRICS_DASHBOARD_PORT", "8601")
    monkeypatch.setenv("SVTK_QC_DASHBOARD_PORT", "8602")
    monkeypatch.setenv("SVTK_LAUNCH_METRICS_DASHBOARD", "1")
    monkeypatch.setenv("SVTK_LAUNCH_QC_DASHBOARD", "1")
    monkeypatch.setenv("SVTK_DASHBOARD_AUTO_PORT", "0")
    monkeypatch.setenv("SVTK_DASHBOARD_PROXY_MODE", "1")
    monkeypatch.setenv("SVTK_METRICS_DASHBOARD_ROW_LIMIT", "250000")
    monkeypatch.setenv("SVTK_METRICS_DASHBOARD_SUMMARY_DISPLAY_ROWS", "7500")
    monkeypatch.setenv("SVTK_METRICS_DASHBOARD_DOWNLOAD_ROWS", "all")

    commands = notebook_dashboard_launch_commands(config_path, run_scenario="large-run")

    assert commands.metrics_port == 8601
    assert commands.qc_port == 8602
    assert commands.launch_metrics_dashboard is True
    assert commands.launch_qc_dashboard is True
    assert commands.auto_port is False
    assert commands.proxy_mode is True
    assert commands.metrics_row_limit == 250000
    assert commands.metrics_summary_display_rows == 7500
    assert commands.metrics_download_rows == "all"
    assert commands.run_scenario == "large-run"
    assert "--auto-port" not in commands.metrics_command
    assert "--proxy-mode" in commands.metrics_command
    assert "--run-scenario large-run" in commands.metrics_command
    assert "--row-limit 250000" in commands.metrics_command
    assert "--summary-display-rows 7500" in commands.metrics_command
    assert "--download-rows all" in commands.metrics_command
    assert "--proxy-mode" in commands.qc_command
    assert "--row-limit" not in commands.qc_command
    status = commands.status_frame().set_index("dashboard")
    assert status.loc["metrics", "run_scenario"] == "large-run"
    assert status.loc["metrics", "status"] == "launch_requested"
    assert status.loc["metrics", "metrics_row_limit"] == 250000
    assert status.loc["metrics", "metrics_summary_display_rows"] == 7500
    assert status.loc["metrics", "metrics_download_rows"] == "all"
    assert bool(status.loc["metrics", "launch_requested"]) is True
    assert bool(status.loc["metrics", "config_exists"]) is True
    assert bool(status.loc["qc", "launch_requested"]) is True
    assert status.loc["qc", "status"] == "launch_requested"
    assert "--run-scenario large-run" in status.loc["metrics", "terminal_command"]
    assert commands.metrics_launch_kwargs(show=False) == {
        "config_path": config_path.resolve(),
        "server_port": 8601,
        "auto_port": False,
        "proxy_mode": True,
        "show": False,
        "run_scenario": "large-run",
        "row_limit": 250000,
        "summary_display_rows": 7500,
        "download_rows": "all",
    }
    assert commands.qc_launch_kwargs(show=False) == {
        "config_path": config_path.resolve(),
        "server_port": 8602,
        "auto_port": False,
        "proxy_mode": True,
        "show": False,
        "run_scenario": "large-run",
    }


def test_notebook_slurm_script_uses_configured_environment(tmp_path, monkeypatch, capsys):
    """Notebook SLURM scripts should inherit setup from config, not notebooks."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    monkeypatch.setenv(SVTK_CLI_CONFIG_ENV, str(tmp_path / "cli-config.json"))
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

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    monkeypatch.setenv(SVTK_CLI_CONFIG_ENV, str(tmp_path / "cli-config.json"))
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
    with pytest.warns(DeprecationWarning, match="run_notebook_step_if_needed"):
        result = run_or_submit_notebook_cli_command(
            context,
            ["svtk", "metrics", "outputs", "--config", str(config_path)],
            script_name="metrics_outputs.slurm",
            job_name="svtk-metrics-outputs",
            run_local=True,
        )

    assert result is None
    assert captured_args["args"] == ["metrics", "outputs", "--config", str(config_path)]

    with pytest.warns(DeprecationWarning, match="run_notebook_step_if_needed"):
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


def test_notebook_cli_helper_rejects_non_svtk_commands(tmp_path, monkeypatch):
    """Notebook command helpers should fail before writing misleading scripts."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    monkeypatch.setenv(SVTK_CLI_CONFIG_ENV, str(tmp_path / "cli-config.json"))
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
""",
        encoding="utf-8",
    )
    context = notebook_run_context(start=repo / "docs", create_dirs=True)

    with pytest.warns(DeprecationWarning, match="run_notebook_step_if_needed"):
        with pytest.raises(ValueError, match="only run Spatial-VTK CLI commands"):
            run_or_submit_notebook_cli_command(
                context,
                ["python", "-m", "spatial_vtk.cli"],
                script_name="bad.slurm",
                job_name="bad",
                run_local=False,
            )

    assert not (context.slurm_dir / "bad.slurm").exists()
    clear_active_config()


def test_notebook_function_helper_runs_or_writes_slurm_wrapper(tmp_path, monkeypatch, capsys):
    """Large-run notebooks should submit package functions without CLI indirection."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    monkeypatch.setenv(SVTK_CLI_CONFIG_ENV, str(tmp_path / "cli-config.json"))
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

    result = run_or_submit_notebook_function(
        context,
        "spatial_vtk.config.metric_display_name",
        args=["PGA"],
        script_name="metric_label.slurm",
        job_name="svtk-metric-label",
        run_local=True,
    )

    assert result == "Peak acceleration (PGA)"

    result = run_or_submit_notebook_function(
        context,
        "spatial_vtk.config.metric_display_name",
        args=["PGV"],
        script_name="metric_label.slurm",
        job_name="svtk-metric-label",
        walltime="00:30:00",
        memory="2G",
        cpus=1,
        run_local=False,
    )

    script = context.slurm_dir / "metric_label.slurm"
    text = script.read_text(encoding="utf-8")
    printed = capsys.readouterr().out
    assert result is None
    assert "spatial_vtk.config.metric_display_name" in printed
    assert "#SBATCH --job-name=svtk-metric-label" in text
    assert "#SBATCH --time=00:30:00" in text
    assert "_run_notebook_function_worker" in text
    assert "spatial_vtk.config.metric_display_name" in text
    assert "PGV" in text
    assert f"sbatch --parsable {script}" in printed
    clear_active_config()


def test_notebook_function_helper_accepts_public_reexport_callables(tmp_path, monkeypatch, capsys):
    """Callable targets should run locally and keep worker imports executable."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    monkeypatch.setenv(SVTK_CLI_CONFIG_ENV, str(tmp_path / "cli-config.json"))
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

    local_result = run_or_submit_notebook_function(
        context,
        metric_display_name,
        args=["PGA"],
        script_name="callable_metric_label.slurm",
        job_name="svtk-callable-metric-label",
        run_local=True,
    )

    assert local_result == "Peak acceleration (PGA)"

    submission = run_or_submit_notebook_function(
        context,
        metric_display_name,
        args=["PGV"],
        script_name="callable_metric_label.slurm",
        job_name="svtk-callable-metric-label",
        run_local=False,
    )

    script = context.slurm_dir / "callable_metric_label.slurm"
    text = script.read_text(encoding="utf-8")
    printed = capsys.readouterr().out
    assert submission is None
    # Function objects keep their implementation module; string targets can use
    # the public ``spatial_vtk.config.metric_display_name`` import path.
    assert "spatial_vtk.config.labels.metric_display_name" in printed
    assert "spatial_vtk.config.labels.metric_display_name" in text
    assert "_run_notebook_function_worker" in text
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


def test_output_path_resolution_accepts_config_path_without_activation(tmp_path, monkeypatch):
    """Scripts and workers should resolve registered outputs from a config path."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    clear_active_config()
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  root: run_outputs
  tables: run_outputs/path_tables
  figures: run_outputs/path_figures
  dashboards: run_outputs/path_dashboards
""",
        encoding="utf-8",
    )

    assert resolve_output_path("prepared_events", kind="table", cfg=config_path) == (
        tmp_path / "run_outputs" / "path_tables" / "prepared_events.csv"
    )
    assert resolve_output_path("record_coverage", kind="figure", cfg=config_path) == (
        tmp_path / "run_outputs" / "path_figures" / "record_coverage.png"
    )
    assert resolve_output_path("metrics_dashboard", kind="dashboard", cfg=config_path) == (
        tmp_path / "run_outputs" / "path_dashboards" / "metrics_dashboard"
    )

    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    finished = finish_figure(
        fig,
        output_key="record_coverage",
        cfg=config_path,
        savefig=True,
        showfig=False,
    )
    figure_path = tmp_path / "run_outputs" / "path_figures" / "record_coverage.png"
    assert finished.spatial_vtk_saved_path == figure_path
    assert figure_path.exists()
    clear_active_config()


def test_configured_output_registry_frame_lists_keys_and_resolved_paths(tmp_path, monkeypatch):
    """Users should be able to discover output keys, filenames, and paths."""

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
    cfg = SpatialVTKConfig.from_file(config_path)

    table_registry = configured_output_registry_frame(cfg=cfg, kinds=("table",))
    by_key = table_registry.set_index("key")
    assert {"kind", "artifact_label", "filename", "description", "resolved_path", "path"} <= set(
        table_registry.columns
    )
    assert by_key.loc["metrics_long", "kind"] == "table"
    assert by_key.loc["metrics_long", "artifact_label"] == "metrics long table"
    assert by_key.loc["metrics_long", "filename"] == "metrics_long.parquet"
    assert by_key.loc["metrics_long", "resolved_path"] == str(
        tmp_path / "run_outputs" / "tables" / "metrics_long.parquet"
    )
    assert by_key.loc["metrics_long", "path"] == by_key.loc["metrics_long", "resolved_path"]
    assert "Long metrics table" in by_key.loc["metrics_long", "description"]

    figure_registry = configured_output_registry_frame(cfg=cfg, kinds=("figure",))
    assert "station_metric_map" in set(figure_registry["key"])
    assert "metrics_long" not in set(figure_registry["key"])

    path_config_registry = configured_output_registry_frame(cfg=config_path, kinds=("dashboard",))
    path_config_by_key = path_config_registry.set_index("key")
    assert path_config_by_key.loc["metrics_dashboard", "resolved_path"] == str(
        tmp_path / "run_outputs" / "dashboards" / "metrics_dashboard"
    )

    compact = configured_output_registry_frame(include_paths=False, kinds=("dashboard",))
    assert list(compact.columns) == ["kind", "key", "artifact_label", "filename", "description"]
    assert "dashboard_summaries" in set(compact["key"])

    preview = configured_output_registry_preview_frame(
        cfg=cfg,
        kinds=("table",),
        include_paths=False,
        nrows=2,
    )
    assert list(preview.columns) == ["kind", "key", "artifact_label", "filename", "description"]
    assert len(preview) == 2
    assert list(preview.index) == [0, 1]


def test_output_groups_accept_config_path_without_activation(tmp_path, monkeypatch):
    """Output-group helpers should work in scripts that pass a config path."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    clear_active_config()
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

    paths = output_group_paths("step_01_ingest", cfg=config_path)
    assert paths["prepared_events_path"] == tmp_path / "run_outputs" / "tables" / "prepared_events.csv"

    namespace = output_group_namespace("step_01_ingest", cfg=config_path)
    assert namespace.event_station_path == tmp_path / "run_outputs" / "tables" / "event_station_records.csv"

    group = output_group("step_01_ingest", cfg=config_path)
    assert group.event_station_records_path == tmp_path / "run_outputs" / "tables" / "event_station_records.csv"
    assert group.figure_path("record_coverage", stem_parts=("step 01", "record coverage")) == (
        tmp_path / "run_outputs" / "figures" / "step_01_record_coverage.png"
    )

    group.prepared_events_path.write_text("event_id\nE01\n", encoding="utf-8")
    loaded = group.load_table("prepared_events_path", cfg=config_path)
    preview = group.preview_table("prepared_events_path", cfg=config_path, nrows=1)
    assert loaded.to_dict("records") == [{"event_id": "E01"}]
    assert preview.to_dict("records") == [{"event_id": "E01"}]

    status = output_group_status("step_01_ingest", cfg=config_path)
    by_name = {row["name"]: row for row in status}
    assert by_name["prepared_events_path"]["exists"] is True
    assert by_name["event_station_path"]["resolved_path"] == str(group.event_station_path)
    status_frame = output_group_status_frame("step_01_ingest", cfg=config_path)
    assert "prepared_events_path" in set(status_frame["name"])

    completion = output_group_completion("step_01_ingest", cfg=config_path)
    assert completion["complete"] is False
    assert "prepared_stations_path" in completion["missing"]
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

    ingest_paths = output_group_paths("step_01_ingest", cfg=cfg)
    assert ingest_paths["event_station_path"] == tmp_path / "run_outputs" / "tables" / "event_station_records.csv"

    qc_paths = output_group_paths("step_02_qc", cfg=cfg)
    assert qc_paths["trace_qc_path"] == tmp_path / "run_outputs" / "tables" / "qc_trace_summary.csv"
    assert qc_paths["qc_inventory_path"] == tmp_path / "run_outputs" / "tables" / "qc_inventory.csv"
    assert qc_paths["qc_inventory_overlap_path"] == tmp_path / "run_outputs" / "tables" / "qc_inventory_overlap.parquet"
    assert qc_paths["comparison_eligible_path"] == tmp_path / "run_outputs" / "tables" / "comparison_eligible_records.csv"
    assert qc_paths["availability_path"] == tmp_path / "run_outputs" / "tables" / "qc_availability.csv"
    assert qc_paths["drop_causes_overlap_figure_path"] == tmp_path / "run_outputs" / "figures" / "drop_cause_diagnostics_overlap.png"
    assert qc_paths["event_trace_comparison_path"] == tmp_path / "run_outputs" / "figures" / "event_trace_comparison.png"

    paths = output_group_paths("step_04_spatial", cfg=cfg)

    assert paths["metrics_long_path"] == tmp_path / "run_outputs" / "tables" / "metrics_long.parquet"
    assert paths["permutation_moran_path"] == tmp_path / "run_outputs" / "tables" / "permutation_moran.csv"
    assert paths["cluster_features_path"] == tmp_path / "run_outputs" / "tables" / "cluster_feature_summary.csv"
    assert paths["pca_scores_path"] == tmp_path / "run_outputs" / "tables" / "pca_station_scores.parquet"
    assert paths["block_holdout_path"] == tmp_path / "run_outputs" / "tables" / "block_holdout_predictions.parquet"
    assert paths["corridors_path"] == tmp_path / "run_outputs" / "tables" / "corridors.parquet"
    assert paths["redcap_clusters_path"] == tmp_path / "run_outputs" / "tables" / "redcap_clusters.parquet"
    assert paths["pattern_similarity_path"] == tmp_path / "run_outputs" / "tables" / "pattern_similarity_station_anomalies.csv"
    assert paths["station_bias_figure_path"] == tmp_path / "run_outputs" / "figures" / "station_residual_map.png"
    assert paths["residual_grid_figure_path"] == tmp_path / "run_outputs" / "figures" / "residual_grid.png"
    assert paths["pca_summary_figure_path"] == tmp_path / "run_outputs" / "figures" / "pca_summary.png"

    spatial_group = output_group("step_04_spatial", cfg=cfg)
    assert spatial_group.figure_path("residual_grid") == tmp_path / "run_outputs" / "figures" / "residual_grid.png"
    assert spatial_group.figure_path(
        "residual_grid_figure_path",
        stem_parts=("step 04", "PGA", "residual grid"),
    ) == tmp_path / "run_outputs" / "figures" / "step_04_pga_residual_grid.png"

    geojson_paths = output_group_paths("step_05_geojson", cfg=cfg)
    assert geojson_paths["corridors_path"] == tmp_path / "run_outputs" / "tables" / "corridors.parquet"
    assert geojson_paths["geojson_polygons_map_path"] == tmp_path / "run_outputs" / "figures" / "geojson_polygons_map.png"
    assert geojson_paths["corridor_map_path"] == tmp_path / "run_outputs" / "figures" / "corridor_map.png"
    assert geojson_paths["region_boxplot_figure_path"] == tmp_path / "run_outputs" / "figures" / "boxplot.png"
    assert geojson_paths["station_metric_map_path"] == tmp_path / "run_outputs" / "figures" / "station_residual_map.png"
    assert geojson_paths["record_section_figure_path"] == tmp_path / "run_outputs" / "figures" / "observed_synthetic_record_section.png"

    geojson_group = output_group("step_05_geojson", cfg=cfg)
    assert geojson_group.figure_path(
        "corridor_map_path",
        stem_parts=("step 05", "corridor", "through boundary"),
    ) == tmp_path / "run_outputs" / "figures" / "step_05_corridor_through_boundary.png"

    plotting_paths = output_group_paths("step_06_plotting", cfg=cfg)
    assert plotting_paths["station_event_waveform_map_path"] == tmp_path / "run_outputs" / "figures" / "station_event_waveform_map.png"
    assert plotting_paths["pattern_similarity_figure_path"] == tmp_path / "run_outputs" / "figures" / "pattern_similarity.png"
    assert plotting_paths["scatterplot_figure_path"] == tmp_path / "run_outputs" / "figures" / "scatterplot.png"
    assert plotting_paths["boxplot_figure_path"] == tmp_path / "run_outputs" / "figures" / "boxplot.png"
    assert plotting_paths["heatmap_figure_path"] == tmp_path / "run_outputs" / "figures" / "heatmap.png"

    plotting_group = output_group("step_06_plotting", cfg=cfg)
    assert plotting_group.figure_path(
        "scatterplot_figure_path",
        stem_parts=("step 06", "metric scatterplot"),
    ) == tmp_path / "run_outputs" / "figures" / "step_06_metric_scatterplot.png"
    write_table(pd.DataFrame({"metric": ["PGA"], "log2_residual": [0.25]}), plotting_group.metrics_long_path)
    plotting_status = load_standard_additional_plotting_output_status(cfg=config_path)
    displayed_plotting: list[pd.DataFrame] = []
    plotting_previews = plotting_status.display_metric_source_preview(
        nrows=1,
        display_fn=displayed_plotting.append,
    )
    assert plotting_previews["metrics_long"].to_dict("records") == [{"metric": "PGA", "log2_residual": 0.25}]
    assert displayed_plotting[0].to_dict("records") == [{"metric": "PGA", "log2_residual": 0.25}]

    waveform_settings = types.SimpleNamespace(name="waveform")
    waveform_calls: list[dict[str, object]] = []

    def fake_write_waveform_comparison(outputs, settings, **kwargs):
        waveform_calls.append({"outputs": outputs, "settings": settings, "kwargs": kwargs})
        return "waveform-result"

    monkeypatch.setattr(
        "spatial_vtk.visualize.waveforms.write_waveform_comparison_from_notebook_settings",
        fake_write_waveform_comparison,
    )
    assert plotting_status.write_waveform_comparison(
        waveform_settings,
        max_records=3,
        max_distance_km=25.0,
        chunksize=500,
        overwrite=True,
        component="Z",
    ) == "waveform-result"
    assert waveform_calls == [
        {
            "outputs": plotting_status,
            "settings": waveform_settings,
            "kwargs": {
                "max_records": 3,
                "max_distance_km": 25.0,
                "chunksize": 500,
                "overwrite": True,
                "event_id": None,
                "component": "Z",
                "passband": None,
                "plot_options": None,
            },
        }
    ]

    import spatial_vtk.spatial.plot.large_run as large_run_plot

    region_settings = types.SimpleNamespace(name="region")
    region_calls: list[dict[str, object]] = []

    def fake_write_region_boxplot(
        outputs,
        settings,
        *,
        output_prefix,
        geojson_path=None,
        annotate_if_missing=False,
        overwrite=False,
    ):
        region_calls.append(
            {
                "outputs": outputs,
                "settings": settings,
                "output_prefix": output_prefix,
                "geojson_path": geojson_path,
                "annotate_if_missing": annotate_if_missing,
                "overwrite": overwrite,
            }
        )
        return "region-boxplot-result"

    monkeypatch.setattr(
        large_run_plot,
        "write_large_run_region_boxplot_from_notebook_settings",
        fake_write_region_boxplot,
    )
    assert plotting_status.write_region_boxplot(
        region_settings,
        output_prefix="additional_region_boxplot",
        annotate_if_missing=True,
        overwrite=True,
    ) == "region-boxplot-result"
    assert region_calls == [
        {
            "outputs": plotting_status,
            "settings": region_settings,
            "output_prefix": "additional_region_boxplot",
            "geojson_path": None,
            "annotate_if_missing": True,
            "overwrite": True,
        }
    ]

    metric_paths = output_group_paths("step_03_metrics", cfg=cfg)
    assert metric_paths["prepared_events_path"] == tmp_path / "run_outputs" / "tables" / "prepared_events.csv"
    assert metric_paths["prepared_stations_path"] == tmp_path / "run_outputs" / "tables" / "prepared_stations.csv"
    assert metric_paths["metric_tasks_path"] == tmp_path / "run_outputs" / "tables" / "metric_tasks.csv"
    assert metric_paths["residuals_vs_distance_figure_path"] == tmp_path / "run_outputs" / "figures" / "residuals_vs_distance.png"
    assert metric_paths["score_trends_figure_path"] == tmp_path / "run_outputs" / "figures" / "score_trends.png"
    assert metric_paths["station_metric_map_path"] == tmp_path / "run_outputs" / "figures" / "station_residual_map.png"
    assert (
        metric_paths["band_score_distribution_figure_path"]
        == tmp_path / "run_outputs" / "figures" / "band_score_distribution.png"
    )

    namespace = output_group_namespace("step_07_dashboards", cfg=cfg)
    assert namespace.qc_trace_summary_path == tmp_path / "run_outputs" / "tables" / "qc_trace_summary.csv"
    assert namespace.metrics_dashboard_root == tmp_path / "run_outputs" / "dashboards" / "metrics_dashboard"
    assert namespace.dashboard_summary_root == tmp_path / "run_outputs" / "dashboards" / "dashboard_summaries"
    assert "legacy attribute namespace" in (output_group_namespace.__doc__ or "")
    assert "New notebooks and workflow code should use :func:`output_group`" in (
        output_group_namespace.__doc__ or ""
    )

    preprocessed_group = preprocessed_waveform_output_group(config=cfg)
    assert preprocessed_group.name == "preprocessed_waveforms"
    assert (
        preprocessed_group.preprocessed_event_station_path
        == tmp_path / "run_outputs" / "preprocessed_waveforms" / "metadata" / "event_station_records_preprocessed.csv"
    )
    assert (
        preprocessed_group.preprocessed_manifest_path
        == tmp_path / "run_outputs" / "preprocessed_waveforms" / "metadata" / "waveform_preprocessing_manifest.csv"
    )
    assert (
        preprocessed_group.preprocessed_trace_metadata_path
        == tmp_path / "run_outputs" / "preprocessed_waveforms" / "metadata" / "trace_metadata_preprocessed.csv"
    )
    preprocessed_readiness = preprocessed_group.readiness(
        ("preprocessed_event_station_path", "preprocessed_trace_metadata_path", "preprocessed_manifest_path"),
        inputs={"event_station_path": ingest_paths["event_station_path"]},
        sources={"event_station_path": ingest_paths["event_station_path"]},
    )
    assert preprocessed_readiness.reason == "missing_inputs"
    assert {item.name for item in preprocessed_readiness.output_items} == {
        "preprocessed_event_station_path",
        "preprocessed_trace_metadata_path",
        "preprocessed_manifest_path",
    }
    preprocessed_group.preprocessed_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "source": ["observed", "synthetic"],
            "event_id": ["e1", "e1"],
            "trace_count": [3, 4],
        }
    ).to_csv(preprocessed_group.preprocessed_manifest_path, index=False)
    manifest = preprocessed_group.load_path_table("preprocessed_manifest_path")
    preview = preprocessed_group.preview_path_table("preprocessed_manifest_path", nrows=1)
    assert manifest["source"].tolist() == ["observed", "synthetic"]
    assert preview["source"].tolist() == ["observed"]
    displayed_path_previews: list[object] = []
    path_previews = preprocessed_group.display_path_table_previews(
        {"manifest": "preprocessed_manifest_path"},
        nrows=1,
        columns=("source", "event_id"),
        display_fn=displayed_path_previews.append,
    )
    assert path_previews["manifest"].to_dict("records") == [
        {"source": "observed", "event_id": "e1"}
    ]
    assert displayed_path_previews[0].to_dict("records") == [
        {"source": "observed", "event_id": "e1"}
    ]
    assert preprocessed_group.preview_path_table("preprocessed_trace_metadata_path", missing="skip") is None
    assert (
        preprocessed_group.display_path_table_previews(
            {"trace_metadata": "preprocessed_trace_metadata_path"},
            missing="skip",
        )
        == {}
    )
    with pytest.raises(FileNotFoundError, match="preprocessed_trace_metadata_path is not ready yet"):
        preprocessed_group.preview_path_table("preprocessed_trace_metadata_path", missing="raise")
    with pytest.raises(KeyError, match="Unknown output-group path"):
        preprocessed_group.preview_path_table("missing_manifest_path")
    with pytest.raises(KeyError, match="Unknown output-group path"):
        preprocessed_group.display_path_table_previews("missing_manifest_path")

    group = output_group("step_03_metrics", cfg=cfg)
    assert group.name == "step_03_metrics"
    assert group.metrics_long_path == paths["metrics_long_path"]
    assert group["metrics_long_path"] == paths["metrics_long_path"]
    assert "metrics_long_path" in group
    assert group.as_dict()["metric_rows_path"] == tmp_path / "run_outputs" / "tables" / "metric_rows.parquet"
    bound: dict[str, object] = {}
    returned = group.bind(bound, names=("metrics_long_path", "metric_rows_path"))
    assert returned == {
        "metrics_long_path": paths["metrics_long_path"],
        "metric_rows_path": tmp_path / "run_outputs" / "tables" / "metric_rows.parquet",
    }
    assert bound == returned
    with pytest.raises(KeyError):
        group.bind(names=("missing_path",))
    group_status = group.status_frame()
    assert "metrics_long_path" in set(group_status["name"])
    metrics_long_status = group_status.loc[group_status["name"].eq("metrics_long_path")].iloc[0]
    assert metrics_long_status["output_key"] == "metrics_long"
    assert metrics_long_status["kind"] == "table"
    assert bool(metrics_long_status["required"]) is True
    assert metrics_long_status["artifact_label"] == "metrics long table"
    assert metrics_long_status["readiness"] == "missing"
    assert metrics_long_status["message"] == "metrics long table is missing."
    assert "Step 3 metric outputs" in metrics_long_status["suggested_action"]
    group_completion = group.completion()
    assert group_completion["complete"] is False
    assert "metrics_enriched_path" in group_completion["missing"]

    readiness = group.readiness(
        ["metrics_long_path"],
        inputs={"prepared_events_path": metric_paths["prepared_events_path"]},
        sources={"prepared_events_path": metric_paths["prepared_events_path"]},
        current_message="Metric outputs are current.",
    )
    assert readiness.reason == "missing_inputs"
    prepared_events = metric_paths["prepared_events_path"]
    prepared_events.parent.mkdir(parents=True, exist_ok=True)
    prepared_events.write_text("event_id\nE1\n", encoding="utf-8")
    loaded_tables = group.load_tables({"events": "prepared_events_path"}, cfg=cfg)
    assert loaded_tables["events"].to_dict("records") == [{"event_id": "E1"}]
    loaded_by_key = group.load_tables("prepared_events", cfg=cfg)
    assert loaded_by_key["prepared_events"].to_dict("records") == [{"event_id": "E1"}]
    loaded_single = group.load_table("prepared_events", cfg=cfg)
    assert loaded_single.to_dict("records") == [{"event_id": "E1"}]
    previews = group.preview_tables({"events_preview": "prepared_events_path"}, cfg=cfg, nrows=1)
    assert previews["events_preview"].to_dict("records") == [{"event_id": "E1"}]
    preview_single = group.preview_table("prepared_events", cfg=cfg, nrows=1)
    assert preview_single.to_dict("records") == [{"event_id": "E1"}]
    displayed: list[object] = []
    displayed_previews = group.display_table_previews(
        {"events_preview": "prepared_events_path"},
        cfg=cfg,
        nrows=1,
        display_fn=displayed.append,
    )
    assert displayed_previews["events_preview"].to_dict("records") == [{"event_id": "E1"}]
    assert len(displayed) == 1
    assert displayed[0].to_dict("records") == [{"event_id": "E1"}]
    assert group.preview_table("metrics_enriched", cfg=cfg, nrows=1, missing="skip") is None
    assert group.first_existing_path(("prepared_stations_path", "prepared_events_path")) == prepared_events
    assert group.first_existing_path(("prepared_stations_path",), default="prepared_events_path") == prepared_events
    assert group.first_existing_path(("prepared_stations_path",)) is None
    first_preview = group.preview_first_existing_table(
        ("prepared_stations_path", "prepared_events_path"),
        cfg=cfg,
        nrows=1,
    )
    assert first_preview["prepared_events"].to_dict("records") == [{"event_id": "E1"}]
    displayed_first: list[object] = []
    first_display_preview = group.display_first_existing_table_preview(
        ("prepared_stations_path", "prepared_events_path"),
        cfg=cfg,
        nrows=1,
        display_fn=displayed_first.append,
    )
    assert first_display_preview["prepared_events"].to_dict("records") == [{"event_id": "E1"}]
    assert len(displayed_first) == 1
    assert displayed_first[0].to_dict("records") == [{"event_id": "E1"}]
    assert group.load_tables({"missing": "metrics_enriched_path"}, cfg=cfg, missing="skip") == {}
    with pytest.raises(KeyError, match="Unknown table artifact"):
        group.load_tables("missing_artifact", cfg=cfg)
    group.metrics_long_path.parent.mkdir(parents=True, exist_ok=True)
    group.metrics_long_path.write_text("metric\nPGA\n", encoding="utf-8")
    readiness = group.readiness(
        ["metrics_long_path"],
        inputs={"prepared_events_path": prepared_events},
        sources={"prepared_events_path": prepared_events},
        current_message="Metric outputs are current.",
    )
    assert readiness.reason == "current"
    assert readiness.message == "Metric outputs are current."
    named_readiness = group.readiness(
        "metrics_long_path",
        inputs=("prepared_events_path",),
        sources=("prepared_events_path",),
        current_message="Metric outputs are current.",
    )
    assert named_readiness.reason == "current"
    named_frame = named_readiness.status_frame()
    assert set(named_frame["name"]) == {"metrics_long_path", "prepared_events_path"}
    assert set(named_frame["role"]) == {"output", "input", "source"}

    unconfigured_readiness = group.readiness(
        "metrics_long_path",
        inputs={"region_geojson_path": None},
        sources={"region_geojson_path": None},
    )
    assert unconfigured_readiness.reason == "missing_inputs"
    assert unconfigured_readiness.should_run is False
    assert unconfigured_readiness.unconfigured_inputs == ("region_geojson_path",)
    assert "region_geojson_path=<not configured>" in unconfigured_readiness.message
    unconfigured_rows = unconfigured_readiness.status_frame()
    input_row = unconfigured_rows.loc[
        unconfigured_rows["name"].eq("region_geojson_path") & unconfigured_rows["role"].eq("input")
    ].iloc[0]
    assert input_row["resolved_path"] == "<not configured>"
    assert input_row["path"] == "<not configured>"
    assert input_row["state"] == "unconfigured"
    source_row = unconfigured_rows.loc[
        unconfigured_rows["name"].eq("region_geojson_path") & unconfigured_rows["role"].eq("source")
    ].iloc[0]
    assert source_row["state"] == "unconfigured_ignored"
    unconfigured_status = output_status_frame({"region_geojson_path": None})
    assert unconfigured_status.to_dict("records") == [
        {
            "name": "region_geojson_path",
            "artifact_label": "region geojson path",
            "artifact_role": "path",
            "status": "unconfigured",
            "resolved_path": "<not configured>",
            "path": "<not configured>",
            "exists": False,
            "size_gb": None,
            "modified": None,
        }
    ]

    dashboard_namespace = dashboard_output_namespace(cfg=cfg)
    assert dashboard_namespace.qc_trace_summary_path == namespace.qc_trace_summary_path
    assert dashboard_namespace.metrics_dashboard_root == namespace.metrics_dashboard_root
    assert dashboard_namespace.dashboard_summary_root == namespace.dashboard_summary_root

    status = output_group_status("step_04_spatial", cfg=cfg)
    assert status[0]["name"] == "metrics_long_path"
    assert status[0]["output_key"] == "metrics_long"
    assert status[0]["kind"] == "table"
    assert status[0]["required"] is True
    assert status[0]["exists"] is True
    assert status[0]["artifact_label"] == "metrics long table"
    assert status[0]["artifact_role"] == "output_table"
    assert status[0]["status"] == "ready"
    assert status[0]["readiness"] == "ready"
    assert status[0]["message"] == "metrics long table is ready."
    assert status[0]["suggested_action"] == ""
    extra_input = tmp_path / "run_outputs" / "preprocessed_waveforms" / "metadata" / "trace_metadata.parquet"
    extra_input.parent.mkdir(parents=True, exist_ok=True)
    extra_input.write_text("placeholder\n", encoding="utf-8")
    status_with_extra = output_group_status_frame(
        "step_03_metrics",
        cfg=cfg,
        extra_paths={"trace_metadata_path": extra_input},
    )
    extra_row = status_with_extra.loc[status_with_extra["name"].eq("trace_metadata_path")].iloc[0]
    assert extra_row["resolved_path"] == str(extra_input)
    assert extra_row["path"] == str(extra_input)
    assert bool(extra_row["exists"]) is True
    assert "output_key" in status_with_extra.columns
    assert pd.isna(extra_row["output_key"])
    assert "artifact_label" in status_with_extra.columns
    assert extra_row["artifact_label"] == "trace metadata path"
    assert extra_row["artifact_role"] == "path"
    assert extra_row["status"] == "ready"

    write_output_table("metrics_long", pd.DataFrame({"metric": ["PGA"]}), cfg=cfg)
    completion = output_group_completion("step_03_metrics", cfg=cfg)
    assert completion["complete"] is False
    assert completion["existing"] == 2
    assert "metrics_enriched_path" in completion["missing"]

    assert should_rebuild_outputs({"metrics_long_path": paths["metrics_long_path"]}) is False
    assert should_rebuild_paths(paths["metrics_long_path"]) is False
    with pytest.raises(ValueError, match="At least one output path is required"):
        required_outputs_exist({})
    with pytest.raises(ValueError, match="At least one output path is required"):
        should_rebuild_outputs({})
    with pytest.raises(ValueError, match="At least one output path is required"):
        should_rebuild_paths()
    source = tmp_path / "newer_source.csv"
    source.write_text("x\n1\n", encoding="utf-8")
    assert should_rebuild_outputs({"metrics_long_path": paths["metrics_long_path"]}, sources=[source]) is True
    assert should_rebuild_paths(paths["metrics_long_path"], sources=[source]) is True
    status_frame = output_status_frame({"metrics_long_path": paths["metrics_long_path"]})
    assert list(status_frame["name"]) == ["metrics_long_path"]
    assert status_frame.loc[0, "resolved_path"] == str(paths["metrics_long_path"])
    assert status_frame.loc[0, "path"] == status_frame.loc[0, "resolved_path"]
    assert "output_key" not in status_frame.columns
    namespace_status_frame = output_status_frame(
        types.SimpleNamespace(metrics_long_path=paths["metrics_long_path"], ignored=object())
    )
    assert list(namespace_status_frame["name"]) == ["metrics_long_path"]
    sequence_status_frame = output_status_frame([paths["metrics_long_path"]])
    assert list(sequence_status_frame["name"]) == ["metrics_long"]

    clear_active_config()


def test_output_status_frame_expands_user_home_paths(tmp_path, monkeypatch):
    """Status tables should report expanded home paths and truthful existence."""

    monkeypatch.setenv("HOME", str(tmp_path))
    home_table = tmp_path / "status_table.csv"
    home_table.write_text("x\n1\n", encoding="utf-8")

    status_frame = output_status_frame({"home_table_path": "~/status_table.csv"})

    assert status_frame.loc[0, "name"] == "home_table_path"
    assert status_frame.loc[0, "resolved_path"] == str(home_table)
    assert status_frame.loc[0, "path"] == str(home_table)
    assert bool(status_frame.loc[0, "exists"]) is True


def test_output_group_accepts_public_event_station_records_alias(tmp_path, monkeypatch):
    """Output-group helpers should accept public result-object path names."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  root: run_outputs
  tables: run_outputs/tables
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()
    group = output_group("step_01_ingest", cfg=cfg)

    assert group.event_station_records_path == group.event_station_path
    assert group["event_station_records_path"] == group.event_station_path
    assert "event_station_records_path" in group

    bound = group.bind(names=("event_station_records_path",))
    assert bound == {"event_station_records_path": group.event_station_path}

    group.event_station_path.parent.mkdir(parents=True, exist_ok=True)
    group.event_station_path.write_text("event_id,station\nE1,STA\n", encoding="utf-8")
    loaded = group.load_table("event_station_records_path", cfg=cfg)

    assert loaded.to_dict("records") == [{"event_id": "E1", "station": "STA"}]
    preview = group.preview_table("event_station_records_path", cfg=cfg, nrows=1)
    assert preview.to_dict("records") == [{"event_id": "E1", "station": "STA"}]
    assert group.load_path_table("event_station_records_path").to_dict("records") == [
        {"event_id": "E1", "station": "STA"}
    ]
    assert group.preview_path_table("event_station_records_path", nrows=1).to_dict("records") == [
        {"event_id": "E1", "station": "STA"}
    ]
    assert group.first_existing_path(("event_station_records_path",)) == group.event_station_path
    assert (
        group.first_existing_path(("prepared_stations_path",), default="event_station_records_path")
        == group.event_station_path
    )
    first_preview = group.preview_first_existing_table(("event_station_records_path",), cfg=cfg, nrows=1)
    assert first_preview["event_station_records"].to_dict("records") == [{"event_id": "E1", "station": "STA"}]
    readiness = group.readiness(
        "event_station_records_path",
        inputs=("event_station_records_path",),
        sources=("event_station_records_path",),
        current_message="Event-station records are current.",
    )
    assert readiness.reason == "current"
    assert dict(readiness.output_items)["event_station_records_path"] == group.event_station_path
    assert dict(readiness.input_items)["event_station_records_path"] == group.event_station_path
    assert dict(readiness.source_items)["event_station_records_path"] == group.event_station_path
    single_string_readiness = group.readiness(
        "event_station_records_path",
        inputs="event_station_records_path",
        sources="event_station_records_path",
        current_message="Event-station records are current.",
    )
    assert single_string_readiness.reason == "current"
    assert "event_station_records_path" not in set(group.status_frame()["name"])
    clear_active_config()


def test_spatial_readiness_helpers_own_step04_output_contract(tmp_path, monkeypatch):
    """Large-run Step 4 notebooks should not duplicate spatial path-name lists."""

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
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()
    step_outputs = output_group("step_04_spatial", cfg=cfg)
    write_table(pd.DataFrame({"metric": ["PGA"], "value": [0.1]}), step_outputs.metric_field_path)
    write_table(pd.DataFrame({"metric": ["PGA"], "moran_i": [0.2]}), step_outputs.morans_i_path)
    write_table(pd.DataFrame({"metric": ["PGA"], "contrast_label": ["basin-crust"]}), step_outputs.geology_path)
    spatial_status = load_standard_spatial_workflow_output_status(cfg=cfg)
    displayed_spatial: list[pd.DataFrame] = []
    spatial_previews = spatial_status.display_table_previews(nrows=1, display_fn=displayed_spatial.append)
    assert spatial_previews["metric_field"].to_dict("records") == [{"metric": "PGA", "value": 0.1}]
    assert spatial_previews["morans_i"].to_dict("records") == [{"metric": "PGA", "moran_i": 0.2}]
    assert spatial_previews["geology_contrasts"].to_dict("records") == [
        {"metric": "PGA", "contrast_label": "basin-crust"}
    ]
    assert [frame.to_dict("records")[0]["metric"] for frame in displayed_spatial] == ["PGA", "PGA", "PGA"]

    spatial_figure_settings = types.SimpleNamespace(name="spatial")
    spatial_figure_calls: list[dict[str, object]] = []

    def fake_write_spatial_summary_figures(outputs, settings, *, cfg=None, overwrite=False, **kwargs):
        spatial_figure_calls.append(
            {
                "outputs": outputs,
                "settings": settings,
                "cfg": cfg,
                "overwrite": overwrite,
                "kwargs": kwargs,
            }
        )
        return "spatial-summary-result"

    monkeypatch.setattr(
        "spatial_vtk.spatial.plot.write_large_run_spatial_summary_figures_from_outputs",
        fake_write_spatial_summary_figures,
    )
    assert spatial_status.write_summary_figures(
        spatial_figure_settings,
        overwrite=True,
        sidecar_rows=10,
    ) == "spatial-summary-result"
    assert spatial_figure_calls == [
        {
            "outputs": spatial_status,
            "settings": spatial_figure_settings,
            "cfg": cfg,
            "overwrite": True,
            "kwargs": {"sidecar_rows": 10},
        }
    ]

    spatial_figure_suite_calls: list[dict[str, object]] = []

    def fake_write_spatial_figure_suite(settings, *, overwrite=False, **kwargs):
        spatial_figure_suite_calls.append(
            {
                "settings": settings,
                "overwrite": overwrite,
                "kwargs": kwargs,
            }
        )
        return "spatial-suite-result"

    monkeypatch.setattr(
        "spatial_vtk.spatial.plot.write_large_run_spatial_figure_suite_from_notebook_settings",
        fake_write_spatial_figure_suite,
    )
    assert spatial_status.write_figure_suite(
        spatial_figure_settings,
        overwrite=True,
        pca_summary_func="custom-pca",
    ) == "spatial-suite-result"
    assert spatial_figure_suite_calls == [
        {
            "settings": spatial_figure_settings,
            "overwrite": True,
            "kwargs": {"pca_summary_func": "custom-pca"},
        }
    ]

    summary_missing = spatial_summary_readiness_from_config(config_path=config_path)

    assert summary_missing.reason == "missing_inputs"
    summary_rows = summary_missing.status_frame()
    output_names = set(summary_rows.loc[summary_rows["role"].eq("output"), "name"])
    assert "metric_field_path" in output_names
    assert "event_centered_path" in output_names
    assert "geology_path" in output_names
    assert "metrics_long_path" not in output_names
    assert set(summary_rows.loc[summary_rows["role"].eq("input"), "name"]) == {"metrics_long_path"}

    step_outputs.metrics_long_path.parent.mkdir(parents=True, exist_ok=True)
    step_outputs.metrics_long_path.write_text("metric\nPGA\n", encoding="utf-8")
    summary_ready_to_run = spatial_summary_readiness_from_config(config_path=config_path)
    assert summary_ready_to_run.reason == "missing_outputs"
    assert summary_ready_to_run.should_run is True

    derived_blocked = spatial_derived_outputs_readiness_from_config(config_path=config_path)
    assert derived_blocked.reason == "missing_inputs"
    assert "Core spatial summary tables are not ready yet" in derived_blocked.message

    for name in (
        "metric_field_path",
        "event_centered_path",
        "station_bias_path",
        "morans_i_path",
        "permutation_moran_path",
        "distance_corr_path",
        "clusters_path",
        "cluster_scores_path",
        "cluster_summary_path",
        "cluster_features_path",
        "pca_scores_path",
        "pca_loadings_path",
        "pca_explained_path",
        "geology_path",
    ):
        path = step_outputs[name]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ready\n", encoding="utf-8")

    derived_ready_to_run = spatial_derived_outputs_readiness_from_config(config_path=config_path)
    assert derived_ready_to_run.reason == "missing_outputs"
    derived_rows = derived_ready_to_run.status_frame()
    assert set(derived_rows.loc[derived_rows["role"].eq("output"), "name"]) == {
        "block_holdout_path",
        "redcap_clusters_path",
        "pattern_similarity_path",
    }
    assert "metrics_long_path" in set(derived_rows.loc[derived_rows["role"].eq("input"), "name"])
    clear_active_config()


def test_qc_readiness_helpers_own_step02_contracts(tmp_path, monkeypatch):
    """Step 2 notebooks should use package-owned QC readiness contracts."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  root: run_outputs
  tables: run_outputs/tables
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()
    step_outputs = output_group("step_02_qc", cfg=cfg)

    inventory_missing = qc_inventory_readiness_from_config(config_path=config_path)
    assert inventory_missing.reason == "missing_inputs"
    inventory_missing_rows = inventory_missing.status_frame()
    assert set(inventory_missing_rows.loc[inventory_missing_rows["role"].eq("input"), "name"]) == {
        "event_station_path",
    }

    step_outputs.event_station_path.parent.mkdir(parents=True, exist_ok=True)
    step_outputs.event_station_path.write_text("event_id,station\nE1,STA\n", encoding="utf-8")
    inventory_ready_to_run = qc_inventory_readiness_from_config(config_path=config_path)
    assert inventory_ready_to_run.reason == "missing_outputs"
    assert set(dict(inventory_ready_to_run.output_items)) == {"trace_qc_path", "qc_inventory_path"}

    overlap_missing = qc_overlap_readiness_from_config(config_path=config_path)
    assert overlap_missing.reason == "missing_inputs"
    overlap_missing_rows = overlap_missing.status_frame()
    assert set(overlap_missing_rows.loc[overlap_missing_rows["role"].eq("input"), "name"]) == {
        "qc_inventory_path",
        "event_station_path",
    }

    step_outputs.trace_qc_path.write_text("source,event_id,station,component,passband,qc_status\n", encoding="utf-8")
    step_outputs.qc_inventory_path.write_text("source,event_id,station,component,passband,qc_status\n", encoding="utf-8")
    inventory_current = qc_inventory_readiness_from_config(
        config_path=config_path,
        current_message="Full QC outputs are current.",
    )
    assert inventory_current.reason == "current"
    assert inventory_current.message == "Full QC outputs are current."
    inventory_forced = qc_inventory_readiness_from_config(config_path=config_path, overwrite=True)
    assert inventory_forced.reason == "overwrite"

    overlap_ready_to_run = qc_overlap_readiness_from_config(config_path=config_path)
    assert overlap_ready_to_run.reason == "missing_outputs"
    assert dict(overlap_ready_to_run.output_items)["qc_inventory_overlap_path"] == step_outputs.qc_inventory_overlap_path

    summary_missing = qc_summary_readiness_from_config(config_path=config_path)
    assert summary_missing.reason == "missing_inputs"
    summary_missing_rows = summary_missing.status_frame()
    assert set(summary_missing_rows.loc[summary_missing_rows["role"].eq("input"), "name"]) == {
        "qc_inventory_overlap_path",
    }

    step_outputs.qc_inventory_overlap_path.write_text(
        "source,event_id,station,component,passband,qc_status\n",
        encoding="utf-8",
    )
    summary_ready_to_run = qc_summary_readiness_from_config(config_path=config_path)
    assert summary_ready_to_run.reason == "missing_outputs"
    output_names = set(dict(summary_ready_to_run.output_items))
    assert "comparison_eligible_path" in output_names
    assert "manual_queue_path" in output_names
    assert dict(summary_ready_to_run.output_items)["drop_causes_overlap_path"] == step_outputs.drop_causes_overlap_path
    clear_active_config()


def test_metric_readiness_helpers_own_step03_inventory_and_manifest_contracts(tmp_path, monkeypatch):
    """Step 3 notebooks should use package-owned metric inventory and manifest readiness."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  root: run_outputs
  tables: run_outputs/tables
  preprocessed_waveforms: run_outputs/preprocessed_waveforms
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()
    metric_outputs = output_group("step_03_metrics", cfg=cfg)
    standard_metric_outputs = load_standard_metric_workflow_outputs(cfg=cfg)
    standard_metric_outputs_from_path = load_standard_metric_workflow_outputs(cfg=config_path)
    preprocessed_outputs = preprocessed_waveform_output_group(config=cfg, create_parent=True)

    assert standard_metric_outputs.metrics_long_path == metric_outputs.metrics_long_path
    assert standard_metric_outputs_from_path.metrics_long_path == metric_outputs.metrics_long_path
    assert standard_metric_outputs_from_path.trace_metadata_path == preprocessed_outputs.preprocessed_trace_metadata_path

    inventories_missing = metric_inventories_readiness_from_config(config_path=config_path)
    assert inventories_missing.reason == "missing_inputs"
    assert dict(inventories_missing.input_items)["trace_metadata_path"] == preprocessed_outputs.preprocessed_trace_metadata_path
    assert set(dict(inventories_missing.output_items)) == {"observed_inventory_path", "synthetic_inventory_path"}

    preprocessed_outputs.preprocessed_trace_metadata_path.write_text("event_id,station\nE1,STA\n", encoding="utf-8")
    inventories_ready_to_run = metric_inventories_readiness_from_config(config_path=config_path)
    assert inventories_ready_to_run.reason == "missing_outputs"

    for path in (metric_outputs.observed_inventory_path, metric_outputs.synthetic_inventory_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("event_id,station,component,path\nE1,STA,Z,file.npz\n", encoding="utf-8")
    inventories_current = metric_inventories_readiness_from_config(
        config_path=config_path,
        current_message="Metric inventories are current.",
    )
    assert inventories_current.reason == "current"
    assert inventories_current.message == "Metric inventories are current."
    assert metric_inventories_readiness_from_config(config_path=config_path, overwrite=True).reason == "overwrite"

    manifest_missing_overlap = metric_manifest_readiness_from_config(config_path=config_path)
    assert manifest_missing_overlap.reason == "missing_inputs"
    manifest_input_names = set(dict(manifest_missing_overlap.input_items))
    assert {"observed_inventory_path", "synthetic_inventory_path", "qc_inventory_overlap_path"} == manifest_input_names

    metric_outputs.qc_inventory_overlap_path.write_text(
        "source,event_id,station,component,passband,qc_status\n",
        encoding="utf-8",
    )
    manifest_ready_to_run = metric_manifest_readiness_from_config(config_path=config_path)
    assert manifest_ready_to_run.reason == "missing_outputs"
    assert dict(manifest_ready_to_run.output_items)["metric_manifest_path"] == metric_outputs.metric_manifest_path

    metric_outputs.metric_manifest_path.write_text('{"batches":[]}\n', encoding="utf-8")
    manifest_current = metric_manifest_readiness_from_config(
        config_path=config_path,
        current_message="Metric manifest is current.",
    )
    assert manifest_current.reason == "current"
    assert manifest_current.message == "Metric manifest is current."
    assert metric_manifest_readiness_from_config(config_path=config_path, overwrite=True).reason == "overwrite"
    clear_active_config()


def test_geojson_readiness_helpers_own_step05_input_contract(tmp_path, monkeypatch):
    """Large-run Step 5 notebooks should not resolve GeoJSON readiness paths."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
paths:
  region_geojson: inputs/regions.geojson
outputs:
  root: run_outputs
  tables: run_outputs/tables
  figures: run_outputs/figures
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()
    step_outputs = output_group("step_05_geojson", cfg=cfg)
    write_table(pd.DataFrame({"region": ["A"], "count": [1]}), step_outputs.geojson_summaries_path)
    geojson_output_status = load_standard_geojson_workflow_output_status(cfg=cfg)
    displayed_geojson: list[pd.DataFrame] = []
    geojson_previews = geojson_output_status.display_table_previews(
        nrows=1,
        display_fn=displayed_geojson.append,
    )
    assert geojson_previews["geojson_region_summaries"].to_dict("records") == [{"region": "A", "count": 1}]
    assert displayed_geojson[0].to_dict("records") == [{"region": "A", "count": 1}]
    import spatial_vtk.spatial.plot.large_run as large_run_plot

    geojson_figure_settings = types.SimpleNamespace(name="geojson")
    geojson_figure_calls: list[dict[str, object]] = []

    def fake_write_geojson_region_figures(
        outputs,
        ingest_outputs,
        settings,
        *,
        geojson_path,
        cfg=None,
        overwrite=False,
    ):
        geojson_figure_calls.append(
            {
                "outputs": outputs,
                "ingest_outputs": ingest_outputs,
                "settings": settings,
                "geojson_path": geojson_path,
                "cfg": cfg,
                "overwrite": overwrite,
            }
        )
        return "geojson-region-result"

    monkeypatch.setattr(
        large_run_plot,
        "write_large_run_geojson_region_figures_from_notebook_settings",
        fake_write_geojson_region_figures,
    )
    geojson_status = step_outputs.status_frame().set_index("name")
    assert geojson_status.loc["geojson_summaries_path", "artifact_label"] == "geojson region summaries table"
    assert geojson_status.loc["geojson_summaries_path", "readiness"] == "missing"
    assert "Step 5 GeoJSON" in geojson_status.loc["geojson_summaries_path", "suggested_action"]
    assert geojson_status.loc["corridor_map_path", "artifact_label"] == "corridor map figure"
    assert "plotting workflow" in geojson_status.loc["corridor_map_path", "suggested_action"]
    ingest_outputs = output_group("step_01_ingest", cfg=cfg)
    region_geojson = tmp_path / "inputs" / "regions.geojson"
    region_geojson.parent.mkdir(parents=True, exist_ok=True)

    def fake_load_ingest_outputs(*, cfg=None):  # noqa: ANN001
        assert cfg == config_path
        return types.SimpleNamespace(outputs=ingest_outputs)

    def fake_load_configured_paths(mapping, *, cfg=None):  # noqa: ANN001
        assert mapping == {"region_geojson": "paths.region_geojson"}
        assert cfg == config_path
        return {"region_geojson": region_geojson}

    monkeypatch.setattr("spatial_vtk.io.load_standard_ingest_workflow_outputs", fake_load_ingest_outputs)
    monkeypatch.setattr("spatial_vtk.io.load_configured_input_paths", fake_load_configured_paths)

    assert geojson_output_status.write_region_figures(
        geojson_figure_settings,
        overwrite=True,
    ) == "geojson-region-result"
    assert geojson_figure_calls == [
        {
            "outputs": geojson_output_status,
            "ingest_outputs": ingest_outputs,
            "settings": geojson_figure_settings,
            "geojson_path": region_geojson,
            "cfg": cfg,
            "overwrite": True,
        }
    ]

    geojson_missing = geojson_region_summary_readiness_from_config(config_path=config_path)

    assert geojson_missing.reason == "missing_inputs"
    geojson_rows = geojson_missing.status_frame()
    assert set(geojson_rows.loc[geojson_rows["role"].eq("input"), "name"]) == {
        "metrics_long_path",
        "region_geojson_path",
    }

    region_geojson.write_text('{"type":"FeatureCollection","features":[]}\n', encoding="utf-8")
    step_outputs.metrics_long_path.parent.mkdir(parents=True, exist_ok=True)
    step_outputs.metrics_long_path.write_text("metric\nPGA\n", encoding="utf-8")
    geojson_ready_to_run = geojson_region_summary_readiness_from_config(config_path=config_path)
    assert geojson_ready_to_run.reason == "missing_outputs"
    assert dict(geojson_ready_to_run.output_items)["geojson_summaries_path"] == step_outputs.geojson_summaries_path

    corridor_missing = boundary_corridor_readiness_from_config(config_path=config_path)
    assert corridor_missing.reason == "missing_inputs"
    corridor_rows = corridor_missing.status_frame()
    assert {"region_geojson_path", "prepared_stations_path", "prepared_events_path"}.issubset(
        set(corridor_rows.loc[corridor_rows["role"].eq("input"), "name"])
    )

    ingest_outputs.prepared_stations_path.parent.mkdir(parents=True, exist_ok=True)
    ingest_outputs.prepared_stations_path.write_text("station,lat,lon\nSTA,0,0\n", encoding="utf-8")
    ingest_outputs.prepared_events_path.write_text("event_id,lat,lon\nE1,0,0\n", encoding="utf-8")
    corridor_ready_to_run = boundary_corridor_readiness_from_config(config_path=config_path)
    assert corridor_ready_to_run.reason == "missing_outputs"
    assert dict(corridor_ready_to_run.output_items)["corridors_path"] == step_outputs.corridors_path
    assert "comparison_eligible_path" in dict(corridor_ready_to_run.source_items)
    clear_active_config()


def test_standard_geojson_plotting_input_loader_owns_path_and_table_loading(tmp_path, monkeypatch):
    """Standard Step 5 notebooks should load GeoJSON inputs through one helper."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
paths:
  region_geojson: inputs/regions.geojson
outputs:
  root: run_outputs
  tables: run_outputs/tables
  figures: run_outputs/figures
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()
    region_geojson = tmp_path / "inputs" / "regions.geojson"
    region_geojson.parent.mkdir(parents=True, exist_ok=True)
    region_geojson.write_text('{"type":"FeatureCollection","features":[]}\n', encoding="utf-8")

    ingest_outputs = output_group("step_01_ingest", cfg=cfg)
    metrics_outputs = output_group("step_03_metrics", cfg=cfg)
    geojson_outputs = output_group("step_05_geojson", cfg=cfg)
    for path, text in (
        (ingest_outputs.prepared_stations_path, "station,lat,lon\nSTA,0,0\n"),
        (ingest_outputs.prepared_events_path, "event_id,lat,lon\nE1,0,0\n"),
        (ingest_outputs.event_station_path, "event_id,station\nE1,STA\n"),
        (metrics_outputs.metrics_long_path, "event_id,station,metric,log2_residual\nE1,STA,PGA,0.1\n"),
        (geojson_outputs.comparison_eligible_path, "event_id,station\nE1,STA\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    inputs = load_standard_geojson_plotting_inputs(cfg=cfg)

    assert inputs.geojson_path == region_geojson
    assert inputs.outputs.name == "step_05_geojson"
    assert len(inputs.metrics) == 1
    assert len(inputs.stations) == 1
    assert len(inputs.events) == 1
    assert len(inputs.event_stations) == 1
    assert len(inputs.comparison_eligible) == 1
    status = inputs.status_frame()
    assert set(status["artifact"]) == {
        "region_geojson",
        "metrics",
        "stations",
        "events",
        "event_stations",
        "comparison_eligible",
    }
    assert status.loc[status["artifact"].eq("region_geojson"), "status"].iloc[0] == "ready"
    region_row = status.loc[status["artifact"].eq("region_geojson")].iloc[0]
    assert region_row["resolved_path"] == str(region_geojson)
    assert region_row["path"] == region_row["resolved_path"]
    clear_active_config()


def test_standard_qc_input_loader_owns_step01_table_loading(tmp_path, monkeypatch):
    """Standard Step 2 notebooks should load Step 1 metadata through one helper."""

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
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()
    ingest_outputs = output_group("step_01_ingest", cfg=cfg)
    qc_outputs = output_group("step_02_qc", cfg=cfg)
    for path, text in (
        (ingest_outputs.prepared_stations_path, "station,lat,lon\nSTA,0,0\n"),
        (ingest_outputs.prepared_events_path, "event_id,lat,lon\nE1,0,0\n"),
        (ingest_outputs.event_station_path, "event_id,station\nE1,STA\n"),
        (qc_outputs.qc_inventory_path, "event_id,station,qc_status\nE1,STA,pass\n"),
        (qc_outputs.comparison_eligible_path, "event_id,station\nE1,STA\n"),
        (qc_outputs.manual_queue_path, "event_id,station,reason\nE1,STA,review\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    inputs = load_standard_qc_inputs(cfg=cfg)

    assert inputs.outputs.name == "step_02_qc"
    assert len(inputs.stations) == 1
    assert len(inputs.events) == 1
    assert len(inputs.event_stations) == 1
    status = inputs.status_frame()
    input_status = status.loc[status["artifact_role"].eq("input_table")].set_index("table")
    assert set(input_status.index) == {"stations", "events", "event_stations"}
    assert input_status["rows"].tolist() == [1, 1, 1]
    assert input_status.loc["stations", "artifact_label"] == "prepared stations input table"
    output_status = status.loc[status["artifact_role"].ne("input_table")].set_index("name")
    assert "qc_inventory_path" in output_status.index
    assert output_status.loc["qc_inventory_path", "resolved_path"] == str(qc_outputs.qc_inventory_path)
    assert output_status.loc["qc_inventory_path", "path"] == str(qc_outputs.qc_inventory_path)
    displayed: list[pd.DataFrame] = []
    inventory_preview = inputs.display_inventory_preview(nrows=1, display_fn=displayed.append)
    assert inventory_preview["qc_inventory"].to_dict("records") == [
        {"event_id": "E1", "station": "STA", "qc_status": "pass"}
    ]
    summary_preview = inputs.display_summary_previews(nrows=1, display_fn=displayed.append)
    assert summary_preview["comparison_eligible"].to_dict("records") == [{"event_id": "E1", "station": "STA"}]
    compact = inputs.compact_output_summary_frame().set_index("artifact")
    assert bool(compact.loc["comparison_eligible", "exists"]) is True
    readiness = output_readiness((qc_outputs.qc_inventory_path,), current_message="current")
    fallback = inputs.step_result(readiness, qc_inventory_path=qc_outputs.qc_inventory_path)
    assert fallback["reused"] is True
    assert fallback["qc_inventory_path"] == str(qc_outputs.qc_inventory_path)
    inventory_fallback = inputs.qc_inventory_step_result(readiness)
    assert inventory_fallback["qc_trace_summary_path"] == str(qc_outputs.trace_qc_path)
    assert inventory_fallback["qc_inventory_path"] == str(qc_outputs.qc_inventory_path)
    assert inventory_fallback["qc_inventory_overlap_path"] == str(qc_outputs.qc_inventory_overlap_path)
    overlap_fallback = inputs.qc_overlap_step_result(readiness, scope="event_station")
    assert overlap_fallback["qc_inventory_overlap_path"] == str(qc_outputs.qc_inventory_overlap_path)
    assert overlap_fallback["scope"] == "event_station"
    summary_fallback = inputs.qc_summary_step_result(readiness)
    assert summary_fallback["comparison_eligible_path"] == str(qc_outputs.comparison_eligible_path)

    qc_figure_calls: list[dict[str, object]] = []

    def fake_write_qc_figures(outputs, settings, *, cfg=None, overwrite=False):  # noqa: ANN001, ANN202
        qc_figure_calls.append({"outputs": outputs, "settings": settings, "cfg": cfg, "overwrite": overwrite})
        return types.SimpleNamespace(status_frame=lambda: pd.DataFrame([{"status": "delegated"}]))

    monkeypatch.setattr("spatial_vtk.visualize.qc.write_qc_figures_from_outputs", fake_write_qc_figures)
    settings = object()
    figure_result = inputs.write_figures(settings, overwrite=True)
    assert figure_result.status_frame().to_dict("records") == [{"status": "delegated"}]
    assert qc_figure_calls == [{"outputs": inputs.outputs, "settings": settings, "cfg": cfg, "overwrite": True}]

    waveform_calls: list[dict[str, object]] = []

    def fake_write_waveform_comparison(outputs, **kwargs):  # noqa: ANN001, ANN202
        waveform_calls.append({"outputs": outputs, "kwargs": kwargs})
        return "waveform-result"

    monkeypatch.setattr(
        "spatial_vtk.visualize.waveforms.write_waveform_comparison_from_notebook_settings",
        fake_write_waveform_comparison,
    )
    assert inputs.write_waveform_comparison(
        component="Z",
        max_records=4,
        max_distance_km=25.0,
        chunksize=500,
        overwrite=True,
        passband="2-3 sec",
        plot_options={"normalize": False},
    ) == "waveform-result"
    assert waveform_calls == [
        {
            "outputs": inputs.outputs,
            "kwargs": {
                "component": "Z",
                "max_records": 4,
                "max_distance_km": 25.0,
                "chunksize": 500,
                "overwrite": True,
                "event_id": None,
                "passband": "2-3 sec",
                "plot_options": {"normalize": False},
            },
        }
    ]
    clear_active_config()


def test_standard_output_results_own_context_and_qc_figure_calls(tmp_path, monkeypatch):
    """Standard output result objects should wrap common figure writers."""

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
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()

    context_calls: list[dict[str, object]] = []
    qc_calls: list[dict[str, object]] = []

    def fake_write_context_figures(outputs, settings, *, cfg=None, overwrite=False):  # noqa: ANN001, ANN202
        context_calls.append({"outputs": outputs, "settings": settings, "cfg": cfg, "overwrite": overwrite})
        return types.SimpleNamespace(status_frame=lambda: pd.DataFrame([{"status": "context"}]))

    def fake_write_qc_figures(outputs, settings, *, cfg=None, overwrite=False):  # noqa: ANN001, ANN202
        qc_calls.append({"outputs": outputs, "settings": settings, "cfg": cfg, "overwrite": overwrite})
        return types.SimpleNamespace(status_frame=lambda: pd.DataFrame([{"status": "qc"}]))

    monkeypatch.setattr("spatial_vtk.visualize.context.write_context_figures_from_outputs", fake_write_context_figures)
    monkeypatch.setattr("spatial_vtk.visualize.qc.write_qc_figures_from_outputs", fake_write_qc_figures)

    ingest_outputs = load_standard_ingest_workflow_outputs(cfg=cfg)
    qc_outputs = load_standard_qc_workflow_outputs(cfg=cfg)
    context_settings = object()
    qc_settings = object()

    context_result = ingest_outputs.write_context_figures(context_settings, overwrite=True)
    qc_result = qc_outputs.write_figures(qc_settings, overwrite=True)

    assert context_result.status_frame().to_dict("records") == [{"status": "context"}]
    assert qc_result.status_frame().to_dict("records") == [{"status": "qc"}]
    assert context_calls == [
        {"outputs": ingest_outputs.outputs, "settings": context_settings, "cfg": cfg, "overwrite": True}
    ]
    assert qc_calls == [{"outputs": qc_outputs.outputs, "settings": qc_settings, "cfg": cfg, "overwrite": True}]
    clear_active_config()


def test_ingest_metadata_summary_uses_public_event_station_records_name(tmp_path, monkeypatch):
    """Step 1 summary previews should expose public result-object path names."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  root: run_outputs
  tables: run_outputs/tables
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()
    ingest_outputs = load_standard_ingest_workflow_outputs(cfg=cfg)

    ingest_outputs.outputs.prepared_stations_path.parent.mkdir(parents=True, exist_ok=True)
    ingest_outputs.outputs.prepared_stations_path.write_text("station,lat,lon\nSTA,0,0\n", encoding="utf-8")
    ingest_outputs.outputs.prepared_events_path.write_text("event_id,lat,lon\nE1,0,0\n", encoding="utf-8")
    ingest_outputs.outputs.event_station_path.write_text("event_id,station\nE1,STA\n", encoding="utf-8")

    summary = ingest_outputs.metadata_summary_frame()

    assert summary["table"].tolist() == ["stations", "events", "event_stations"]
    assert summary["name"].tolist() == [
        "prepared_stations_path",
        "prepared_events_path",
        "event_station_records_path",
    ]
    assert "event_station_path" not in set(summary["name"])
    assert summary.loc[summary["table"].eq("event_stations"), "row_count"].iloc[0] == 1
    clear_active_config()


def test_ingest_workflow_output_result_owns_large_run_step01_runners(tmp_path, monkeypatch):
    """Large-run Step 1 cells should delegate ingest orchestration through the result object."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  root: run_outputs
  tables: run_outputs/tables
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()

    class Context:
        config_path = tmp_path / "fallback.yaml"
        run_scenario = "fallback"

    run_calls: list[dict[str, object]] = []

    def fake_run_notebook_step_if_needed(context, readiness, function, **kwargs):  # noqa: ANN001, ANN202
        run_calls.append(
            {
                "context": context,
                "readiness": readiness,
                "function": function,
                "kwargs": kwargs,
            }
        )
        return {"readiness": readiness}

    monkeypatch.setattr("spatial_vtk.config.run_notebook_step_if_needed", fake_run_notebook_step_if_needed)

    readiness_calls: list[tuple[str, dict[str, object]]] = []

    def readiness_factory(name):
        def _inner(**kwargs):  # noqa: ANN202
            readiness_calls.append((name, kwargs))
            return f"{name}-readiness"

        return _inner

    monkeypatch.setattr("spatial_vtk.io.workflows.metadata_tables_readiness_from_config", readiness_factory("metadata"))
    monkeypatch.setattr("spatial_vtk.io.workflows.preprocessing_readiness_from_config", readiness_factory("preprocess"))
    monkeypatch.setattr("spatial_vtk.io.workflows.record_coverage_readiness_from_config", readiness_factory("coverage"))

    def fake_function(**_kwargs):  # noqa: ANN202
        return {"ok": True}

    monkeypatch.setattr("spatial_vtk.io.workflows.prepare_metadata_tables_from_config", fake_function)
    monkeypatch.setattr("spatial_vtk.io.workflows.preprocess_waveforms_from_config", fake_function)
    monkeypatch.setattr("spatial_vtk.io.workflows.build_record_coverage_from_config", fake_function)

    ingest_outputs = load_standard_ingest_workflow_outputs(cfg=cfg)
    context = Context()
    assert ingest_outputs.run_metadata_step_if_needed(context, overwrite=True, run_local=False) == {
        "readiness": "metadata-readiness"
    }
    assert ingest_outputs.run_preprocessing_step_if_needed(
        context,
        overwrite=True,
        continue_on_error=False,
        verbose=False,
    ) == {"readiness": "preprocess-readiness"}
    assert ingest_outputs.run_record_coverage_step_if_needed(context, overwrite=True, component="Z") == {
        "readiness": "coverage-readiness"
    }

    assert [name for name, _ in readiness_calls] == ["metadata", "preprocess", "coverage"]
    for _, kwargs in readiness_calls:
        assert kwargs["config_path"] == cfg.config_path
        assert kwargs["run_scenario"] == context.run_scenario
        assert kwargs["overwrite"] is True
    assert readiness_calls[0][1]["current_message"] == "Prepared metadata tables are current; skipping."
    assert readiness_calls[1][1]["current_message"] == (
        "Preprocessed waveform metadata is current; skipping preprocessing submission."
    )
    assert readiness_calls[2][1]["missing_input_message"] == (
        "Trace metadata or event-station records are not ready yet."
    )

    assert [call["readiness"] for call in run_calls] == [
        "metadata-readiness",
        "preprocess-readiness",
        "coverage-readiness",
    ]
    assert [call["kwargs"]["script_name"] for call in run_calls] == [
        "step01_prepare_metadata.slurm",
        "step01_preprocess_waveforms.slurm",
        "step01_record_coverage.slurm",
    ]
    assert [call["kwargs"]["job_name"] for call in run_calls] == [
        "svtk-step01-metadata",
        "svtk-step01-preprocess",
        "svtk-step01-coverage",
    ]
    assert run_calls[0]["kwargs"]["run_local"] is False
    assert run_calls[1]["kwargs"]["run_local"] is None
    assert run_calls[2]["kwargs"]["run_local"] is None
    assert run_calls[1]["kwargs"]["kwargs"]["continue_on_error"] is False
    assert run_calls[1]["kwargs"]["kwargs"]["verbose"] is False
    assert run_calls[2]["kwargs"]["kwargs"] == {
        "config_path": str(cfg.config_path),
        "run_scenario": cfg.run_scenario,
        "component": "Z",
    }
    clear_active_config()


def test_qc_workflow_output_result_owns_large_run_step02_runners(tmp_path, monkeypatch):
    """Large-run Step 2 cells should delegate QC orchestration through the result object."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  root: run_outputs
  tables: run_outputs/tables
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()

    class Context:
        config_path = tmp_path / "fallback.yaml"
        run_scenario = "fallback"

    run_calls: list[dict[str, object]] = []

    def fake_run_notebook_step_if_needed(context, readiness, function, **kwargs):  # noqa: ANN001, ANN202
        run_calls.append(
            {
                "context": context,
                "readiness": readiness,
                "function": function,
                "kwargs": kwargs,
            }
        )
        return {"readiness": readiness}

    monkeypatch.setattr("spatial_vtk.config.run_notebook_step_if_needed", fake_run_notebook_step_if_needed)

    readiness_calls: list[tuple[str, dict[str, object]]] = []

    def readiness_factory(name):
        def _inner(**kwargs):  # noqa: ANN202
            readiness_calls.append((name, kwargs))
            return f"{name}-readiness"

        return _inner

    import spatial_vtk.qc.build.workflow as qc_workflow

    monkeypatch.setattr(qc_workflow, "qc_inventory_readiness_from_config", readiness_factory("inventory"))
    monkeypatch.setattr(qc_workflow, "qc_overlap_readiness_from_config", readiness_factory("overlap"))
    monkeypatch.setattr(qc_workflow, "qc_summary_readiness_from_config", readiness_factory("summary"))

    def fake_function(**_kwargs):  # noqa: ANN202
        return {"ok": True}

    monkeypatch.setattr("spatial_vtk.qc.run_qc_inventory_from_config", fake_function)
    monkeypatch.setattr(qc_workflow, "write_qc_inventory_overlap_from_config", fake_function)
    monkeypatch.setattr(qc_workflow, "run_qc_summary_workflow_from_config", fake_function)

    qc_outputs = load_standard_qc_workflow_outputs(cfg=cfg)
    context = Context()
    assert qc_outputs.run_inventory_step_if_needed(context, overwrite=True, run_local=False) == {
        "readiness": "inventory-readiness"
    }
    assert qc_outputs.run_overlap_step_if_needed(
        context,
        overwrite=True,
        write_overwrite=False,
        chunksize=123,
        scope="event_station",
    ) == {"readiness": "overlap-readiness"}
    assert qc_outputs.run_summary_step_if_needed(
        context,
        overwrite=True,
        write_overwrite=False,
        chunksize=456,
    ) == {"readiness": "summary-readiness"}

    assert [name for name, _ in readiness_calls] == ["inventory", "overlap", "summary"]
    for _, kwargs in readiness_calls:
        assert kwargs["config_path"] == cfg.config_path
        assert kwargs["run_scenario"] == cfg.run_scenario
        assert kwargs["overwrite"] is True
    assert len(run_calls) == 3
    assert [call["readiness"] for call in run_calls] == [
        "inventory-readiness",
        "overlap-readiness",
        "summary-readiness",
    ]
    assert run_calls[0]["kwargs"]["script_name"] == "step02_build_qc_inventory.slurm"
    assert run_calls[0]["kwargs"]["memory"] == "64G"
    assert run_calls[0]["kwargs"]["run_local"] is False
    assert run_calls[0]["kwargs"]["kwargs"]["verbose"] is True
    assert run_calls[1]["kwargs"]["script_name"] == "step02_qc_overlap_sidecar.slurm"
    assert run_calls[1]["kwargs"]["kwargs"]["chunksize"] == 123
    assert run_calls[1]["kwargs"]["kwargs"]["overwrite"] is False
    assert run_calls[1]["kwargs"]["kwargs"]["scope"] == "event_station"
    assert run_calls[2]["kwargs"]["script_name"] == "step02_qc_summary_tables.slurm"
    assert run_calls[2]["kwargs"]["kwargs"]["chunksize"] == 456
    assert run_calls[2]["kwargs"]["kwargs"]["overwrite"] is False
    clear_active_config()


def test_qc_workflow_output_result_returns_skipped_step_payloads(tmp_path, monkeypatch):
    """Current Step 2 QC gates should still return displayable notebook payloads."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  root: run_outputs
  tables: run_outputs/tables
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()

    class Context:
        config_path = tmp_path / "fallback.yaml"
        run_scenario = "fallback"

    class Ready:
        should_run = False
        reason = "current"
        message = "Already current"

        def status_frame(self):  # noqa: ANN202
            return pd.DataFrame()

    def fake_run_notebook_step_if_needed(*_args, **_kwargs):  # noqa: ANN202
        return None

    monkeypatch.setattr("spatial_vtk.config.run_notebook_step_if_needed", fake_run_notebook_step_if_needed)

    import spatial_vtk.qc.build.workflow as qc_workflow

    monkeypatch.setattr(qc_workflow, "qc_inventory_readiness_from_config", lambda **_kwargs: Ready())
    monkeypatch.setattr(qc_workflow, "qc_overlap_readiness_from_config", lambda **_kwargs: Ready())
    monkeypatch.setattr(qc_workflow, "qc_summary_readiness_from_config", lambda **_kwargs: Ready())

    def fake_function(**_kwargs):  # noqa: ANN202
        return {"ok": True}

    monkeypatch.setattr("spatial_vtk.qc.run_qc_inventory_from_config", fake_function)
    monkeypatch.setattr(qc_workflow, "write_qc_inventory_overlap_from_config", fake_function)
    monkeypatch.setattr(qc_workflow, "run_qc_summary_workflow_from_config", fake_function)

    qc_outputs = load_standard_qc_workflow_outputs(cfg=cfg)
    context = Context()
    inventory = qc_outputs.run_inventory_step_if_needed(context)
    overlap = qc_outputs.run_overlap_step_if_needed(context, scope="event_station")
    summary = qc_outputs.run_summary_step_if_needed(context)

    assert inventory["reused"] is True
    assert inventory["reason"] == "current"
    assert inventory["message"] == "Already current"
    assert inventory["qc_trace_summary_path"] == str(qc_outputs.outputs.trace_qc_path)
    assert inventory["qc_inventory_path"] == str(qc_outputs.outputs.qc_inventory_path)
    assert inventory["qc_inventory_overlap_path"] == str(qc_outputs.outputs.qc_inventory_overlap_path)
    assert overlap == {
        "reused": True,
        "reason": "current",
        "message": "Already current",
        "qc_inventory_overlap_path": str(qc_outputs.outputs.qc_inventory_overlap_path),
        "scope": "event_station",
    }
    assert summary == {
        "reused": True,
        "reason": "current",
        "message": "Already current",
        "comparison_eligible_path": str(qc_outputs.outputs.comparison_eligible_path),
    }
    clear_active_config()


def test_standard_spatial_workflow_output_loader_owns_step04_table_mapping(tmp_path, monkeypatch):
    """Standard Step 4 notebooks should not map spatial output tables by hand."""

    from spatial_vtk.spatial import load_standard_spatial_workflow_outputs

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
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()
    outputs = output_group("step_04_spatial", cfg=cfg)
    metric_field = pd.DataFrame(
        {
            "metric": ["PGA"],
            "event_id": ["E1"],
            "station": ["STA"],
            "field_value": [0.2],
        }
    )
    event_centered = pd.DataFrame(
        {
            "metric": ["PGA"],
            "event_id": ["E1"],
            "station": ["STA"],
            "mean_centered": [0.0],
        }
    )
    station_bias = pd.DataFrame(
        {
            "metric": ["PGA"],
            "station": ["STA"],
            "mean_centered": [0.2],
            "n_events": [1],
        }
    )
    table_payloads = {
        "metric_field_path": metric_field,
        "event_centered_path": event_centered,
        "station_bias_path": station_bias,
        "morans_i_path": pd.DataFrame({"metric": ["PGA"], "I": [0.0]}),
        "distance_corr_path": pd.DataFrame({"metric": ["PGA"], "distance_bin": ["0-10"], "correlation": [0.0]}),
        "clusters_path": pd.DataFrame({"metric": ["PGA"], "station": ["STA"], "cluster": [0]}),
        "cluster_scores_path": pd.DataFrame({"metric": ["PGA"], "score": [1.0]}),
        "cluster_summary_path": pd.DataFrame({"metric": ["PGA"], "cluster": [0], "n": [1]}),
        "pca_scores_path": pd.DataFrame({"metric": ["PGA"], "station": ["STA"], "PC1": [0.0]}),
        "pca_loadings_path": pd.DataFrame({"metric": ["PGA"], "feature": ["mean_centered"], "loading": [1.0]}),
        "pca_explained_path": pd.DataFrame({"metric": ["PGA"], "mode": ["PC1"], "explained_variance_ratio": [1.0]}),
        "geology_path": pd.DataFrame({"metric": ["PGA"], "contrast": ["demo"], "effect": [0.0]}),
    }
    for path_name, frame in table_payloads.items():
        write_table(frame, getattr(outputs, path_name))

    loaded = load_standard_spatial_workflow_outputs({"metrics": ["PGA"]}, cfg=cfg)
    clear_active_config()
    loaded_from_path = load_standard_spatial_workflow_outputs({"metrics": ["PGA"]}, cfg=config_path)
    loaded_from_current_payload = load_standard_spatial_workflow_outputs({}, cfg=config_path)
    settings_from_path = spatial_statistics_settings_from_config(config_path)

    assert loaded.outputs.name == "step_04_spatial"
    assert loaded_from_path.outputs.name == "step_04_spatial"
    assert loaded_from_path.outputs.metric_field_path == outputs.metric_field_path
    assert settings_from_path.metrics_table == "paths.metric_figure_snapshot"
    assert settings_from_path.station_metadata_table == "paths.site_metadata"
    assert settings_from_path.metric == ("PGA", "FAS")
    assert all(not name.endswith("_path") for name in loaded.tables)
    assert {"metric_field", "event_centered_residuals", "station_bias", "morans_i"}.issubset(loaded.tables)
    assert {"metric_field", "event_centered_residuals", "station_bias", "morans_i"}.issubset(loaded_from_path.tables)
    assert loaded.metrics == ("PGA",)
    assert loaded_from_path.metrics == ("PGA",)
    assert loaded_from_current_payload.metrics == ("PGA",)
    assert len(loaded.metric_field) == 1
    assert len(loaded_from_path.metric_field) == 1
    assert len(loaded.event_centered_residuals) == 1
    assert len(loaded.station_bias) == 1
    assert "PGA" in loaded.spatial_products
    status = loaded.status_frame()
    assert status.loc[status["table"].eq("metric_field"), "rows"].iloc[0] == 1
    assert not loaded.summary_frame().empty
    assert not loaded.station_bias_preview_frame().empty


def test_spatial_workflow_output_status_owns_large_run_step04_runners(tmp_path, monkeypatch):
    """Large-run Step 4 cells should delegate heavy-step orchestration through the result object."""

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  root: run_outputs
  tables: run_outputs/tables
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    clear_active_config()

    class Context:
        config_path = tmp_path / "fallback.yaml"
        run_scenario = "fallback"

    class Ready:
        should_run = True
        reason = "missing_outputs"
        message = "run"

        def status_frame(self):  # noqa: ANN202
            return pd.DataFrame()

    run_calls: list[dict[str, object]] = []

    def fake_run_notebook_step_if_needed(context, readiness, function, **kwargs):  # noqa: ANN001, ANN202
        run_calls.append(
            {
                "context": context,
                "readiness": readiness,
                "function": function,
                "kwargs": kwargs,
            }
        )
        return {"readiness": readiness}

    monkeypatch.setattr("spatial_vtk.config.run_notebook_step_if_needed", fake_run_notebook_step_if_needed)

    import spatial_vtk.spatial.calculate.workflow as spatial_workflow

    readiness_calls: list[tuple[str, dict[str, object]]] = []

    def readiness_factory(name):
        def _inner(**kwargs):  # noqa: ANN202
            readiness_calls.append((name, kwargs))
            return Ready()

        return _inner

    def fake_function(**_kwargs):  # noqa: ANN202
        return {"ok": True}

    monkeypatch.setattr(spatial_workflow, "spatial_summary_readiness_from_config", readiness_factory("summary"))
    monkeypatch.setattr(spatial_workflow, "spatial_derived_outputs_readiness_from_config", readiness_factory("derived"))
    monkeypatch.setattr(spatial_workflow, "run_spatial_statistics_workflow_from_config", fake_function)
    monkeypatch.setattr(spatial_workflow, "run_spatial_derived_outputs_workflow_from_config", fake_function)

    outputs = load_standard_spatial_workflow_output_status(cfg=config_path)
    context = Context()
    assert outputs.run_summary_step_if_needed(context, overwrite=True, run_local=False) == {
        "readiness": run_calls[0]["readiness"]
    }
    assert outputs.run_derived_outputs_step_if_needed(context, overwrite=True, run_local=False) == {
        "readiness": run_calls[1]["readiness"]
    }

    assert [name for name, _ in readiness_calls] == ["summary", "derived"]
    for _, kwargs in readiness_calls:
        assert kwargs["config_path"] == cfg.config_path
        assert kwargs["run_scenario"] == context.run_scenario
        assert kwargs["overwrite"] is True
    assert [call["kwargs"]["script_name"] for call in run_calls] == [
        "step04_spatial_summaries.slurm",
        "step04_spatial_derived_outputs.slurm",
    ]
    assert run_calls[0]["kwargs"]["job_name"] == "svtk-step04-spatial"
    assert run_calls[0]["kwargs"]["cpus"] == 4
    assert run_calls[0]["kwargs"]["run_local"] is False
    assert run_calls[0]["kwargs"]["kwargs"]["run_scenario"] == context.run_scenario
    assert run_calls[0]["kwargs"]["kwargs"]["verbose"] is True
    assert run_calls[1]["kwargs"]["job_name"] == "svtk-step04-derived"
    assert run_calls[1]["kwargs"]["cpus"] == 2
    assert run_calls[1]["kwargs"]["kwargs"]["overwrite"] is True
    assert run_calls[1]["kwargs"]["kwargs"]["run_scenario"] == context.run_scenario
    clear_active_config()


def test_geojson_workflow_output_status_owns_large_run_step05_runners(tmp_path, monkeypatch):
    """Large-run Step 5 cells should delegate GeoJSON/corridor orchestration through the result object."""

    from spatial_vtk.spatial import load_standard_geojson_workflow_output_status

    monkeypatch.delenv(SVTK_CONFIG_ENV, raising=False)
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  root: run_outputs
  tables: run_outputs/tables
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()

    class Context:
        config_path = tmp_path / "fallback.yaml"
        run_scenario = "fallback"

    class Ready:
        should_run = True
        reason = "missing_outputs"
        message = "run"

        def status_frame(self):  # noqa: ANN202
            return pd.DataFrame()

    run_calls: list[dict[str, object]] = []

    def fake_run_notebook_step_if_needed(context, readiness, function, **kwargs):  # noqa: ANN001, ANN202
        run_calls.append(
            {
                "context": context,
                "readiness": readiness,
                "function": function,
                "kwargs": kwargs,
            }
        )
        return {"readiness": readiness}

    monkeypatch.setattr("spatial_vtk.config.run_notebook_step_if_needed", fake_run_notebook_step_if_needed)

    import spatial_vtk.spatial.calculate.workflow as spatial_workflow

    readiness_calls: list[tuple[str, dict[str, object]]] = []

    def readiness_factory(name):
        def _inner(**kwargs):  # noqa: ANN202
            readiness_calls.append((name, kwargs))
            return Ready()

        return _inner

    def fake_function(**_kwargs):  # noqa: ANN202
        return {"ok": True}

    monkeypatch.setattr(spatial_workflow, "geojson_region_summary_readiness_from_config", readiness_factory("geojson"))
    monkeypatch.setattr(spatial_workflow, "boundary_corridor_readiness_from_config", readiness_factory("corridor"))
    monkeypatch.setattr(spatial_workflow, "run_geojson_region_summary_workflow_from_config", fake_function)
    monkeypatch.setattr(spatial_workflow, "run_boundary_corridor_workflow_from_config", fake_function)

    outputs = load_standard_geojson_workflow_output_status(cfg=config_path)
    context = Context()
    assert outputs.run_geojson_summary_step_if_needed(context, overwrite=True, chunksize=123, run_local=False) == {
        "readiness": run_calls[0]["readiness"]
    }
    assert outputs.run_corridor_step_if_needed(context, overwrite=True, run_local=False) == {
        "readiness": run_calls[1]["readiness"]
    }

    assert [name for name, _ in readiness_calls] == ["geojson", "corridor"]
    for _, kwargs in readiness_calls:
        assert kwargs["config_path"] == config_path
        assert kwargs["run_scenario"] == context.run_scenario
        assert kwargs["overwrite"] is True
    assert [call["kwargs"]["script_name"] for call in run_calls] == [
        "step05_geojson_summaries.slurm",
        "step05_corridors.slurm",
    ]
    assert run_calls[0]["kwargs"]["job_name"] == "svtk-step05-geojson"
    assert run_calls[0]["kwargs"]["memory"] == "32G"
    assert run_calls[0]["kwargs"]["kwargs"]["chunksize"] == 123
    assert run_calls[0]["kwargs"]["kwargs"]["run_scenario"] == context.run_scenario
    assert run_calls[1]["kwargs"]["job_name"] == "svtk-step05-corridors"
    assert run_calls[1]["kwargs"]["memory"] == "8G"
    assert run_calls[1]["kwargs"]["kwargs"]["run_scenario"] == context.run_scenario
    clear_active_config()


def test_record_coverage_readiness_uses_preprocessed_event_station_fallback(tmp_path):
    """Record-coverage readiness should match the build helper's input fallback."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text("project:\n  root_dir: .\n", encoding="utf-8")
    cfg = SpatialVTKConfig.from_file(config_path).activate()
    ingest_outputs = output_group("step_01_ingest", cfg=cfg)
    preprocessed_outputs = preprocessed_waveform_output_group(config=cfg, create_parent=True)

    readiness = record_coverage_readiness_from_config(config_path=config_path)
    assert readiness.reason == "missing_inputs"
    assert dict(readiness.input_items)["event_station_records_path"] == ingest_outputs.event_station_path

    ingest_outputs.event_station_path.parent.mkdir(parents=True, exist_ok=True)
    ingest_outputs.event_station_path.write_text("event_id,station\nE1,STA\n", encoding="utf-8")
    preprocessed_outputs.preprocessed_trace_metadata_path.write_text("event_id,station\nE1,STA\n", encoding="utf-8")
    readiness = record_coverage_readiness_from_config(config_path=config_path)
    assert readiness.reason == "missing_outputs"
    assert dict(readiness.input_items)["event_station_records_path"] == ingest_outputs.event_station_path

    preprocessed_outputs.preprocessed_event_station_path.write_text("event_id,station\nE1,STA\n", encoding="utf-8")
    readiness = record_coverage_readiness_from_config(config_path=config_path)
    assert readiness.reason == "missing_outputs"
    assert (
        dict(readiness.input_items)["event_station_records_path"]
        == preprocessed_outputs.preprocessed_event_station_path
    )


def test_step01_readiness_helpers_own_metadata_and_preprocessing_contracts(tmp_path):
    """Step 1 notebooks should use package-owned metadata and preprocessing readiness."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text("project:\n  root_dir: .\n", encoding="utf-8")
    cfg = SpatialVTKConfig.from_file(config_path).activate()
    ingest_outputs = output_group("step_01_ingest", cfg=cfg)
    preprocessed_outputs = preprocessed_waveform_output_group(config=cfg, create_parent=True)

    metadata_missing = metadata_tables_readiness_from_config(config_path=config_path)
    assert metadata_missing.reason == "missing_outputs"
    assert set(dict(metadata_missing.output_items)) == {
        "prepared_stations_path",
        "prepared_events_path",
        "event_station_path",
    }

    for path in (
        ingest_outputs.prepared_stations_path,
        ingest_outputs.prepared_events_path,
        ingest_outputs.event_station_path,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("id\nx\n", encoding="utf-8")
    metadata_current = metadata_tables_readiness_from_config(
        config_path=config_path,
        current_message="Prepared metadata tables are current.",
    )
    assert metadata_current.reason == "current"
    assert metadata_current.message == "Prepared metadata tables are current."
    assert metadata_tables_readiness_from_config(config_path=config_path, overwrite=True).reason == "overwrite"

    preprocessing_missing = preprocessing_readiness_from_config(config_path=config_path)
    assert preprocessing_missing.reason == "missing_outputs"
    assert dict(preprocessing_missing.input_items)["event_station_path"] == ingest_outputs.event_station_path
    assert set(dict(preprocessing_missing.output_items)) == {
        "preprocessed_event_station_path",
        "preprocessed_trace_metadata_path",
        "preprocessed_manifest_path",
    }

    for path in (
        preprocessed_outputs.preprocessed_event_station_path,
        preprocessed_outputs.preprocessed_trace_metadata_path,
        preprocessed_outputs.preprocessed_manifest_path,
    ):
        path.write_text("event_id,station\nE1,STA\n", encoding="utf-8")
    preprocessing_current = preprocessing_readiness_from_config(
        config_path=config_path,
        current_message="Preprocessed waveform metadata is current.",
    )
    assert preprocessing_current.reason == "current"
    assert preprocessing_current.message == "Preprocessed waveform metadata is current."
    assert preprocessing_readiness_from_config(config_path=config_path, overwrite=True).reason == "overwrite"


def test_display_output_table_previews_resolves_and_labels_registered_tables(tmp_path, capsys):
    """Notebook previews should resolve configured paths without path boilerplate."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        """
project:
  root_dir: .
outputs:
  root: run_outputs
  tables: run_outputs/tables
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path).activate()
    write_output_table("metrics_long", pd.DataFrame({"metric": ["PGA", "PGV"]}), cfg=cfg)

    displayed: list[pd.DataFrame] = []
    paths = display_output_table_previews(
        {"Metric rows": "metrics_long", "Missing QC": "qc_inventory"},
        cfg=cfg,
        nrows=1,
        display_fn=displayed.append,
    )

    output = capsys.readouterr().out
    assert "Metric rows:" in output
    assert "Missing QC is not ready yet." in output
    assert paths["Metric rows"] == tmp_path / "run_outputs" / "tables" / "metrics_long.parquet"
    assert paths["Missing QC"] == tmp_path / "run_outputs" / "tables" / "qc_inventory.csv"
    assert len(displayed) == 1
    assert list(displayed[0]["metric"]) == ["PGA"]

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

    contracts = dashboard_summary_table_contracts().set_index("table")
    assert "sta_lon" in contracts.loc["station_rollup", "map_coordinate_columns"]
    assert "sta_lat" in contracts.loc["station_rollup", "map_coordinate_columns"]
    assert "event_lon" in contracts.loc["event_rollup", "map_coordinate_columns"]
    assert "event_lat" in contracts.loc["event_rollup", "map_coordinate_columns"]
    assert contracts.loc["model_metric_band", "map_coordinate_columns"] == ""


def test_dashboard_summary_readiness_distinguishes_data_ready_from_map_ready(tmp_path):
    """Map-tab blockers should be visible even when summary values are ready."""

    summary_root = tmp_path / "dashboard_summaries"
    summary_root.mkdir()
    (summary_root / "station_rollup.csv").write_text(
        "station,model,metric,band,n,med_log2_residual\nSTA,m1,PGA,1-2 sec,4,0.25\n",
        encoding="utf-8",
    )

    readiness = dashboard_summary_readiness_frame(summary_root, create_parent=False)
    station = readiness.set_index("dashboard_table").loc["station_rollup"]

    assert station["ready"] is True
    assert station["readiness"] == "ready"
    assert station["map_ready"] is False
    assert "coordinate columns" in station["map_message"]
    assert station["tab_ready"] is False
    assert station["tab_message"] == station["map_message"]


def test_dashboard_summary_readiness_uses_schema_and_selected_columns(tmp_path, monkeypatch):
    """Dashboard preflight should not materialize whole large summary tables."""

    import spatial_vtk.visualize.dashboard.contracts as contracts_module

    summary_root = tmp_path / "dashboard_summaries"
    summary_root.mkdir()
    pd.DataFrame(
        {
            "station": ["STA", "STB"],
            "model": ["m1", "m1"],
            "metric": ["PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec"],
            "n": [3, 4],
            "sta_lon": [-118.1, -118.2],
            "sta_lat": [34.1, 34.2],
            "med_log2_residual": [0.2, -0.1],
            "unused_payload": ["x" * 100, "y" * 100],
        }
    ).to_parquet(summary_root / "station_rollup.parquet", index=False)

    def _fail_full_reader(*args, **kwargs):
        raise AssertionError("readiness should not use the full dashboard table reader")

    monkeypatch.setattr(contracts_module, "read_dashboard_table", _fail_full_reader)

    readiness = dashboard_summary_readiness_frame(summary_root, create_parent=False)
    row = readiness.set_index("dashboard_table").loc["station_rollup"]

    assert row["readiness"] == "ready"
    assert row["ready"] is True
    assert row["row_count"] == 2
    assert row["map_ready"] is True
    assert row["nonempty_value_columns"] == "med_log2_residual"


def test_dashboard_output_readiness_requires_metric_dataset_files(tmp_path):
    """Dashboard preflight should not treat empty output directories as complete."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  tables: outputs/tables
  dashboards: outputs/dashboards
""",
        encoding="utf-8",
    )
    clear_active_config()
    paths = dashboard_output_namespace(cfg=config_path)
    paths.metrics_long_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"model": ["m1"], "metric": ["PGA"], "band": ["1-2 sec"], "value": [0.5]}).to_parquet(
        paths.metrics_long_path,
        index=False,
    )
    paths.metrics_dashboard_root.mkdir(parents=True, exist_ok=True)
    paths.dashboard_summary_root.mkdir(parents=True, exist_ok=True)

    metric_status = dashboard_metric_dataset_readiness_frame(paths.metrics_dashboard_root)
    readiness = dashboard_output_readiness(cfg=config_path)
    summary = dashboard_readiness_summary_frame(readiness=readiness)
    by_item = summary.set_index("item")

    assert metric_status["readiness"].iloc[0] == "missing_dataset_files"
    assert metric_status["resolved_path"].iloc[0] == metric_status["path"].iloc[0]
    assert readiness.should_run is True
    assert readiness.reason == "missing_outputs"
    assert "recognized files" in readiness.message
    readiness_status = readiness.status_frame()
    assert [
        "item_type",
        "name",
        "artifact",
        "artifact_role",
        "artifact_label",
        "ready",
        "readiness",
        "exists",
        "message",
        "suggested_action",
        "resolved_path",
        "path",
    ] == [
        column
        for column in readiness_status.columns
        if column
        in {
            "item_type",
            "name",
            "artifact",
            "artifact_role",
            "artifact_label",
            "ready",
            "readiness",
            "exists",
            "message",
            "suggested_action",
            "resolved_path",
            "path",
        }
    ]
    assert "metrics_dashboard_root" in set(readiness_status["name"])
    assert set(readiness_status["item_type"]) >= {"input", "dataset", "summary_table", "qc_table"}
    metrics_long_row = readiness_status.loc[readiness_status["name"].eq("metrics_long_path")].iloc[0]
    assert metrics_long_row["item_type"] == "input"
    assert metrics_long_row["artifact"] == "metrics_long"
    assert metrics_long_row["artifact_label"] == "metrics_long source table"
    assert bool(metrics_long_row["ready"]) is True
    assert metrics_long_row["readiness"] == "ready"
    assert bool(metrics_long_row["exists"]) is True
    assert metrics_long_row["resolved_path"] == metrics_long_row["path"]
    assert metrics_long_row["message"] == "metrics_long source table is ready."
    assert metrics_long_row["suggested_action"] == ""
    metric_root_row = readiness_status.loc[readiness_status["name"].eq("metrics_dashboard_root")].iloc[0]
    assert metric_root_row["item_type"] == "dataset"
    assert metric_root_row["artifact"] == "metrics_dashboard"
    assert metric_root_row["artifact_label"] == "metrics dashboard row dataset"
    assert metric_root_row["resolved_path"] == metric_root_row["path"]
    assert by_item.loc["metrics_dashboard_dataset", "readiness"] == "missing_dataset_files"
    assert by_item.loc["metrics_dashboard_dataset", "resolved_path"] == by_item.loc["metrics_dashboard_dataset", "path"]
    assert by_item.loc["model_metric_band", "readiness"] == "missing"
    assert by_item.loc["qc_trace_summary", "readiness"] == "missing"
    assert readiness.summary_frame().equals(summary)


def test_dashboard_readiness_attachments_prefer_resolved_path_without_path_alias(tmp_path):
    """Dashboard readiness attachments should not depend on the compatibility path column."""

    import spatial_vtk.visualize.dashboard.contracts as contracts_module

    summary_table = tmp_path / "model_metric_band.csv"
    pd.DataFrame(
        {
            "model": ["m1"],
            "metric": ["PGA"],
            "band": ["1-2 sec"],
            "n": [3],
            "med_log2_residual": [0.2],
        }
    ).to_csv(summary_table, index=False)
    metrics_root = tmp_path / "metrics_dashboard_dataset.csv"
    pd.DataFrame(
        {
            "model": ["m1"],
            "metric": ["PGA"],
            "band": ["1-2 sec"],
            "log2_residual": [0.25],
        }
    ).to_csv(metrics_root, index=False)
    qc_trace_summary = tmp_path / "qc_trace_summary.csv"
    pd.DataFrame(
        {
            "source": ["observed"],
            "event_id": ["ev1"],
            "station": ["STA"],
            "component": ["Z"],
            "passband": ["1-2 sec"],
            "qc_status": ["pass"],
            "qc_reason": [""],
        }
    ).to_csv(qc_trace_summary, index=False)

    summary_status = pd.DataFrame(
        [
            {
                "name": "model_metric_band_path",
                "dashboard_table": "model_metric_band",
                "resolved_path": str(summary_table),
                "exists": True,
            }
        ]
    )
    summary_attached = contracts_module._attach_dashboard_readiness(summary_status)
    assert "path" not in summary_attached.columns
    assert summary_attached.loc[0, "ready"] is True
    assert summary_attached.loc[0, "readiness"] == "ready"
    assert summary_attached.loc[0, "row_count"] == 1

    metric_source = tmp_path / "metrics_long.csv"
    metric_source.write_text("metric\nPGA\n", encoding="utf-8")
    os.utime(summary_table, (1_000, 1_000))
    os.utime(metric_source, (2_000, 2_000))
    assert contracts_module._dashboard_outputs_stale(metric_source, tmp_path / "missing_metrics_root", summary_status) is True

    metric_status = pd.DataFrame(
        [
            {
                "name": "metrics_dashboard_root",
                "resolved_path": str(metrics_root),
                "exists": True,
            }
        ]
    )
    metric_attached = contracts_module._attach_metric_dataset_readiness(metric_status)
    assert "path" not in metric_attached.columns
    assert metric_attached.loc[0, "ready"] is True
    assert metric_attached.loc[0, "readiness"] == "ready"
    assert metric_attached.loc[0, "file_count"] == 1

    qc_status = pd.DataFrame(
        [
            {
                "name": "qc_trace_summary_path",
                "resolved_path": str(qc_trace_summary),
                "exists": True,
            }
        ]
    )
    qc_attached = contracts_module._attach_qc_trace_readiness(qc_status)
    assert "path" not in qc_attached.columns
    assert qc_attached.loc[0, "ready"] is True
    assert qc_attached.loc[0, "readiness"] == "ready"
    assert qc_attached.loc[0, "row_count"] == 1


def test_notebook_dashboard_preparation_can_skip_local_writes(tmp_path, monkeypatch):
    """Standard notebooks should get readiness/status frames without writing large dashboards."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  tables: outputs/tables
  dashboards: outputs/dashboards
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)

    result = prepare_configured_dashboard_datasets_from_notebook_settings(
        cfg=cfg,
        prepare_locally=False,
    )

    assert result.status == "skipped"
    assert result.written_paths == {}
    assert "Slurm-aware dashboard preparation cell" in result.message
    assert not result.summary_frame().empty
    assert not result.status_frame().empty
    assert result.written_frame().empty
    preparation_frame = result.preparation_frame()
    assert preparation_frame.loc[0, "name"] == "dashboard_preparation"
    assert preparation_frame.loc[0, "artifact"] == "dashboard_preparation"
    assert preparation_frame.loc[0, "artifact_label"] == "dashboard preparation"
    assert preparation_frame.loc[0, "artifact_role"] == "workflow_step"
    assert preparation_frame.loc[0, "status"] == "skipped"
    assert {"resolved_path", "path", "exists"} <= set(preparation_frame.columns)
    assert preparation_frame.loc[0, "resolved_path"] == ""
    assert preparation_frame.loc[0, "path"] == ""
    assert preparation_frame.loc[0, "exists"] == ""
    assert bool(preparation_frame.loc[0, "should_run"]) is True
    assert "Slurm-aware dashboard preparation cell" in preparation_frame.loc[0, "message"]
    displayed_frames: list[pd.DataFrame] = []
    display_frames = display_dashboard_preparation_result(result, display=displayed_frames.append)
    assert "preparation" in display_frames
    assert displayed_frames[0].loc[0, "status"] == "skipped"

    calls: list[dict[str, object]] = []

    def fake_run_notebook_step_if_needed(
        context,
        readiness,
        function,
        *,
        kwargs,
        script_name,
        job_name,
        walltime,
        memory,
        cpus,
        run_local,
        section,
        display_fn,
    ):
        calls.append(
            {
                "context": context,
                "readiness": readiness,
                "function": function,
                "kwargs": kwargs,
                "script_name": script_name,
                "job_name": job_name,
                "walltime": walltime,
                "memory": memory,
                "cpus": cpus,
                "run_local": run_local,
                "section": section,
                "display_fn": display_fn,
            }
        )
        return "dashboard-run-result"

    monkeypatch.setattr("spatial_vtk.config.run_notebook_step_if_needed", fake_run_notebook_step_if_needed)
    context = types.SimpleNamespace(config_path=config_path)

    assert result.run_if_needed(
        context,
        partitioned=False,
        format="csv",
        chunksize=250,
        memory="16G",
    ) == "dashboard-run-result"

    assert len(calls) == 1
    call = calls[0]
    assert call["context"] is context
    assert call["readiness"] is result.readiness
    assert call["function"].__name__ == "write_configured_dashboard_datasets"
    assert call["kwargs"] == {
        "cfg": str(config_path),
        "residual_mode": "logratio",
        "partitioned": False,
        "hex_dist": 10.0,
        "hex_az": 10.0,
        "format": "csv",
        "replace_existing": True,
        "chunksize": 250,
    }
    assert call["script_name"] == "step07_dashboard_outputs.slurm"
    assert call["job_name"] == "svtk-step07-dashboards"
    assert call["walltime"] == "04:00:00"
    assert call["memory"] == "16G"
    assert call["cpus"] == 1
    assert call["run_local"] is None
    assert call["section"] == "compute.slurm"


def test_notebook_dashboard_preparation_delegates_configured_writer(tmp_path):
    """Tutorial dashboard preparation should use config-backed writer defaults."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  tables: outputs/tables
  dashboards: outputs/dashboards
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    paths = dashboard_output_namespace(cfg=cfg)
    paths.metrics_long_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"model": ["m1"], "metric": ["PGA"], "band": ["1-2 sec"], "value": [0.5]}).to_parquet(
        paths.metrics_long_path,
        index=False,
    )
    seen: dict[str, object] = {}

    def _fake_writer(**kwargs):
        seen.update(kwargs)
        return {
            "metrics_dashboard_root": tmp_path / "dashboards" / "metrics_dashboard",
            "dashboard_summary_root": tmp_path / "dashboards" / "dashboard_summaries",
        }

    result = prepare_configured_dashboard_datasets_from_notebook_settings(
        cfg=cfg,
        prepare_locally=True,
        partitioned=True,
        format="parquet",
        writer=_fake_writer,
    )

    assert result.status == "wrote"
    assert result.written_paths["metrics_dashboard_root"] == tmp_path / "dashboards" / "metrics_dashboard"
    assert seen["cfg"] is cfg
    assert seen["residual_mode"] == "logratio"
    assert seen["partitioned"] is True
    assert seen["format"] == "parquet"
    assert seen["replace_existing"] is True
    assert not result.summary_frame().empty
    written = result.written_frame().set_index("name")
    assert "dashboard_summary_root" in written.index
    assert written.loc["dashboard_summary_root", "artifact"] == "dashboard_summary"
    assert written.loc["dashboard_summary_root", "artifact_label"] == "dashboard summary root"
    assert written.loc["dashboard_summary_root", "artifact_role"] == "dashboard_output"
    assert written.loc["dashboard_summary_root", "status"] == "wrote"
    assert written.loc["dashboard_summary_root", "resolved_path"] == written.loc["dashboard_summary_root", "path"]
    assert bool(written.loc["dashboard_summary_root", "exists"]) is False


def test_display_dashboard_preparation_result_returns_named_frames(tmp_path):
    """Dashboard notebooks should display preparation frames through package code."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  tables: outputs/tables
  dashboards: outputs/dashboards
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    result = prepare_configured_dashboard_datasets_from_notebook_settings(
        cfg=cfg,
        prepare_locally=False,
    )
    displayed: list[pd.DataFrame] = []

    frames = display_dashboard_preparation_result(result, display=displayed.append)

    assert list(frames) == ["preparation", "readiness", "status", "written", "summary_contracts"]
    assert len(displayed) == 5
    assert frames["preparation"].loc[0, "status"] == "skipped"
    assert "Slurm-aware dashboard preparation cell" in frames["preparation"].loc[0, "message"]
    assert not frames["readiness"].empty
    assert not frames["status"].empty
    assert "value_families" in frames["readiness"].columns
    assert "nonempty_value_families" in frames["readiness"].columns
    assert "value_families" in frames["status"].columns
    assert frames["written"].empty
    assert not frames["summary_contracts"].empty


def test_dashboard_output_readiness_rebuilds_map_summaries_when_source_has_coordinates(tmp_path):
    """Dashboard preflight should rerun stale map summaries that dropped coordinates."""

    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  tables: outputs/tables
  dashboards: outputs/dashboards
""",
        encoding="utf-8",
    )
    cfg = SpatialVTKConfig.from_file(config_path)
    paths = dashboard_output_namespace(cfg=cfg)
    paths.metrics_long_path.parent.mkdir(parents=True, exist_ok=True)
    paths.metrics_dashboard_root.mkdir(parents=True, exist_ok=True)
    paths.dashboard_summary_root.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        {
            "model": ["m1"],
            "metric": ["PGA"],
            "band": ["1-2 sec"],
            "component": ["Z"],
            "station": ["STA"],
            "event_id": ["E1"],
            "log2_residual": [0.25],
            "sta_lon": [-118.1],
            "sta_lat": [34.2],
            "event_lon": [-118.0],
            "event_lat": [34.0],
        }
    ).to_parquet(paths.metrics_long_path, index=False)
    pd.DataFrame({"model": ["m1"], "metric": ["PGA"], "band": ["1-2 sec"], "log2_residual": [0.25]}).to_parquet(
        paths.metrics_dashboard_root / "metrics_long.parquet",
        index=False,
    )
    pd.DataFrame({"model": ["m1"], "metric": ["PGA"], "band": ["1-2 sec"], "n": [1], "med_log2_residual": [0.25]}).to_parquet(
        paths.dashboard_summary_root / "model_metric_band.parquet",
        index=False,
    )
    pd.DataFrame({"station": ["STA"], "model": ["m1"], "metric": ["PGA"], "band": ["1-2 sec"], "n": [1], "med_log2_residual": [0.25]}).to_parquet(
        paths.dashboard_summary_root / "station_rollup.parquet",
        index=False,
    )
    pd.DataFrame({"event_id": ["E1"], "model": ["m1"], "metric": ["PGA"], "band": ["1-2 sec"], "n": [1], "med_log2_residual": [0.25]}).to_parquet(
        paths.dashboard_summary_root / "event_rollup.parquet",
        index=False,
    )
    pd.DataFrame(
        {
            "model": ["m1"],
            "metric": ["PGA"],
            "band": ["1-2 sec"],
            "dist_bin_km": [0.0],
            "az_bin_deg": [0.0],
            "n": [1],
            "med_log2_residual": [0.25],
        }
    ).to_parquet(paths.dashboard_summary_root / "path_hex.parquet", index=False)

    readiness = dashboard_output_readiness(cfg=cfg)
    summary = dashboard_readiness_summary_frame(readiness=readiness).set_index("item")

    assert readiness.should_run is True
    assert readiness.reason == "map_incomplete"
    assert "station_rollup" in readiness.message
    assert "event_rollup" in readiness.message
    assert summary.loc["station_rollup", "readiness"] == "ready"
    assert summary.loc["station_rollup", "map_ready"] is False


def test_dashboard_ready_value_parses_status_table_values():
    """Dashboard readiness parsing should not treat string False as truthy."""

    assert dashboard_ready_value(True) is True
    assert dashboard_ready_value("true") is True
    assert dashboard_ready_value("ready") is True
    assert dashboard_ready_value(False) is False
    assert dashboard_ready_value("False") is False
    assert dashboard_ready_value("missing") is False
    assert dashboard_ready_value(pd.NA) is False
    assert dashboard_ready_value("", default=True) is True


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
    bounded_csv = load_dashboard_metric_dataset(direct_csv, max_rows=1, chunksize=1)
    assert len(bounded_csv) == 1

    many_rows = pd.DataFrame(
        {
            "model": ["m1", "m1", "m2", "m1"],
            "metric": ["PGA", "PGA", "PGA", "PGV"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec", "2-3 sec"],
            "station": ["A", "B", "C", "D"],
            "event_id": ["E1", "E2", "E3", "E4"],
            "log2_residual": [0.1, 0.2, 0.3, 0.4],
        }
    )
    bounded_csv_path = tmp_path / "many_metrics.csv"
    many_rows.to_csv(bounded_csv_path, index=False)
    bounded_filtered = load_dashboard_metric_dataset(
        bounded_csv_path,
        models=["m1"],
        metrics=["PGA"],
        bands=["1-2 sec"],
        max_rows=1,
        chunksize=1,
    )
    assert bounded_filtered[["model", "metric", "band", "station"]].to_dict("records") == [
        {"model": "m1", "metric": "PGA", "band": "1-2 sec", "station": "A"}
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

    with pytest.raises(ValueError, match="At least one output path is required"):
        output_readiness({})

    missing_input = output_readiness(output, inputs=[required_input])
    assert missing_input.should_run is False
    assert missing_input.reason == "missing_inputs"
    assert missing_input.missing_inputs == (required_input,)
    named_missing_input = output_readiness({"summary": output}, inputs={"metrics": required_input})
    assert "metrics=" in named_missing_input.message
    missing_rows = named_missing_input.status_rows()
    assert [(row["role"], row["name"], row["state"]) for row in missing_rows] == [
        ("output", "summary", "missing"),
        ("input", "metrics", "missing"),
    ]
    missing_frame = named_missing_input.status_frame()
    assert list(missing_frame["name"]) == ["summary", "metrics"]
    assert list(missing_frame["state"]) == ["missing", "missing"]

    required_input.parent.mkdir()
    required_input.write_text("source\n", encoding="utf-8")

    missing_output = output_readiness(output, inputs=[required_input], sources=[required_input])
    assert missing_output.should_run is True
    assert missing_output.reason == "missing_outputs"
    assert missing_output.missing_outputs == (output,)
    named_missing_output = output_readiness({"summary": output}, inputs={"metrics": required_input})
    assert named_missing_output.message.startswith("Output is missing; building: summary=")

    output.parent.mkdir()
    output.write_text("old\n", encoding="utf-8")
    current = output_readiness(
        {"summary": output},
        inputs={"metrics": required_input},
        sources={"metrics": required_input},
    )
    assert current.reason == "current"
    assert current.message.startswith("Outputs are current; skipping: summary=")

    newer_time = output.stat().st_mtime + 10
    os.utime(required_input, (newer_time, newer_time))
    stale = output_readiness(
        {"summary": output},
        inputs={"metrics": required_input},
        sources={"metrics": required_input},
    )
    assert stale.should_run is True
    assert stale.reason == "stale_sources"
    assert stale.stale_outputs == (output,)
    assert stale.message.startswith("Source dependency changed; rebuilding: summary=")
    assert [(row["role"], row["name"], row["state"]) for row in stale.status_rows()] == [
        ("output", "summary", "stale"),
        ("input", "metrics", "ready"),
        ("source", "metrics", "ready"),
    ]

    forced = output_readiness({"summary": output}, inputs={"metrics": required_input}, overwrite=True)
    assert forced.should_run is True
    assert forced.reason == "overwrite"
    assert forced.message.startswith("Overwrite requested; rebuilding: summary=")
    assert forced.status_rows()[0]["state"] == "overwrite"

    ignored_source = tmp_path / "inputs" / "optional.parquet"
    current_with_missing_source = output_readiness({"summary": output}, sources={"optional": ignored_source})
    source_rows = current_with_missing_source.status_rows()
    assert source_rows[-1]["role"] == "source"
    assert source_rows[-1]["name"] == "optional"
    assert source_rows[-1]["state"] == "missing_ignored"


def test_run_notebook_step_if_needed_displays_and_delegates(tmp_path, monkeypatch, capsys):
    """Notebook step helper should display readiness and run only when needed."""

    assert run_notebook_step_if_needed is notebook_helpers.run_notebook_step_if_needed
    context = types.SimpleNamespace(run_local=True)
    output = tmp_path / "outputs" / "summary.csv"
    missing_input = tmp_path / "inputs" / "metrics.parquet"
    displayed = []

    missing_input_readiness = output_readiness({"summary": output}, inputs={"metrics": missing_input})
    result = notebook_helpers.run_notebook_step_if_needed(
        context,
        missing_input_readiness,
        "spatial_vtk.fake.workflow",
        script_name="workflow.slurm",
        job_name="svtk-workflow",
        display_fn=displayed.append,
    )

    assert result is None
    assert "Required input is not ready yet" in capsys.readouterr().out
    assert list(displayed[0]["name"]) == ["summary", "metrics"]

    missing_input.parent.mkdir()
    missing_input.write_text("metric\n", encoding="utf-8")
    run_readiness = output_readiness({"summary": output}, inputs={"metrics": missing_input})
    calls = []

    def fake_run_or_submit(context_arg, function, **kwargs):
        calls.append((context_arg, function, kwargs))
        return "submitted"

    monkeypatch.setattr(notebook_helpers, "run_or_submit_notebook_function", fake_run_or_submit)
    displayed.clear()
    result = notebook_helpers.run_notebook_step_if_needed(
        context,
        run_readiness,
        metric_display_name,
        kwargs={"config_path": "run.yaml"},
        script_name="workflow.slurm",
        job_name="svtk-workflow",
        walltime="02:00:00",
        memory="8G",
        cpus=2,
        display_fn=displayed.append,
    )

    assert result == "submitted"
    printed = capsys.readouterr().out
    assert "Running notebook step:" in printed
    assert "Output is missing; building" in printed
    assert len(calls) == 1
    assert calls[0][0] is context
    assert calls[0][1] is metric_display_name
    assert calls[0][2]["kwargs"] == {"config_path": "run.yaml"}
    assert calls[0][2]["script_name"] == "workflow.slurm"
    assert calls[0][2]["walltime"] == "02:00:00"
    assert calls[0][2]["memory"] == "8G"
    assert calls[0][2]["cpus"] == 2
    assert list(displayed[0]["state"]) == ["missing", "ready"]


def test_notebook_step_result_reports_reuse_and_named_values(tmp_path):
    """Notebook skipped-step fallbacks should stay compact and JSON-friendly."""

    output = tmp_path / "outputs" / "summary.csv"
    output.parent.mkdir()
    output.write_text("value\n1\n", encoding="utf-8")
    readiness = output_readiness({"summary": output})

    result = notebook_step_result(
        readiness,
        summary_path=output,
        nested={"output": output},
        row_count=1,
    )

    assert result["reused"] is True
    assert result["reason"] == "current"
    assert result["message"].startswith("Outputs are current; skipping")
    assert result["summary_path"] == str(output)
    assert result["nested"] == {"output": str(output)}
    assert result["row_count"] == 1


def test_display_notebook_step_result_returns_labeled_display_frames(tmp_path):
    """Notebook step result display should avoid raw dict and Slurm repr output."""

    readiness = output_readiness({"summary": tmp_path / "summary.csv"})
    skipped = notebook_step_result(readiness, summary_path=tmp_path / "summary.csv")
    skipped_frame = notebook_step_result_frame(skipped, label="GeoJSON summaries")

    assert skipped_frame.loc[0, "step"] == "GeoJSON summaries"
    assert skipped_frame.loc[0, "status"] == "reused"
    assert skipped_frame.loc[0, "summary_path"] == str(tmp_path / "summary.csv")

    class SummaryResult:
        def summary_frame(self) -> pd.DataFrame:
            return pd.DataFrame([{"artifact": "metadata", "rows": 3}])

    summary_frame = notebook_step_result_frame(SummaryResult(), label="Metadata tables")
    assert summary_frame.loc[0, "step"] == "Metadata tables"
    assert summary_frame.loc[0, "artifact"] == "metadata"

    submission = SlurmSubmission(
        script_path=tmp_path / "step05.slurm",
        command=("sbatch", "step05.slurm"),
        stdout="Submitted batch job 123\n",
        stderr="",
        returncode=0,
        job_id="123",
    )
    displayed: list[pd.DataFrame] = []
    submission_frame = display_notebook_step_result(
        submission,
        label="Boundary corridors",
        display=displayed.append,
    )

    assert submission_frame.loc[0, "Step"] == "Boundary corridors"
    assert submission_frame.loc[0, "Status"] == "submitted"
    assert submission_frame.loc[0, "Job Id"] == "123"
    assert submission_frame.loc[0, "Command"] == "sbatch step05.slurm"
    assert len(displayed) == 1
    assert displayed[0] is submission_frame


def test_finish_figure_uses_rich_display_in_notebooks(monkeypatch):
    """Notebook display should embed figures even when assigned to variables."""

    pytest.importorskip("IPython")
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

    pytest.importorskip("IPython")
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
    plan_summary = plan.summary_frame().set_index("setting")["value"]
    assert plan_summary["metrics"] == "PGA, delay_corrected_cc"
    assert plan_summary["passbands"] == "1-2 s, 2-4 s"
    assert plan_summary["components"] == "Z"
    assert plan_summary["models"] == "model_a, model_b"
    assert plan_summary["output_path"] == str(tmp_path / "outputs" / "metrics" / "command.csv")

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
