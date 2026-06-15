from __future__ import annotations

import os
import types

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from spatial_vtk.config import (
    SVTK_CONFIG_ENV,
    SpatialVTKConfig,
    active_config,
    clear_active_config,
    find_config_file,
    format_run_time,
    load_config,
    notebook_timing_enabled,
    register_svtk_cell_timer,
    resolve_output_path,
    resolve_run_defaults,
)
from spatial_vtk.io import (
    ArtifactSpec,
    apply_waveform_preprocessing_with_metadata,
    apply_waveform_preprocessing,
    artifact_path_for_spec,
    default_output_paths,
    read_artifact_manifest,
    metric_plan_from_config,
    stable_hash,
    waveform_preprocessing_from_config,
    waveform_preprocessing_label,
    write_artifact_manifest,
    write_output_table,
)
import spatial_vtk.visualize.figure_io as figure_io
from spatial_vtk.visualize.figure_io import finish_figure
from spatial_vtk.visualize import default_figure_paths


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


def test_default_output_and_figure_paths_are_named(tmp_path):
    """Default path helpers should avoid repeated filename declarations."""

    tables = default_output_paths(
        tmp_path / "tables",
        ["qc_inventory", "manual_review_queue", "qc_metric_pair_retention", "post_qc_records"],
    )
    figures = default_figure_paths(tmp_path / "figures")

    assert tables.qc_inventory == tmp_path / "tables" / "qc_inventory.csv"
    assert tables.manual_review_queue == tmp_path / "tables" / "manual_review_queue.csv"
    assert tables.qc_metric_pair_retention == tmp_path / "tables" / "qc_metric_pair_retention.csv"
    assert tables.post_qc_records == tmp_path / "tables" / "post_qc_records.csv"
    assert figures.retention_summary == tmp_path / "figures" / "retention_summary.png"
    assert figures.station_event_context == tmp_path / "figures" / "station_event_context.png"


def test_notebook_timing_config_and_formatter(tmp_path):
    """Notebook timing should be configurable and display only wall time."""

    enabled = SpatialVTKConfig(tmp_path / "config.yaml", tmp_path, {"notebooks": {"show_cell_timing": True}})
    disabled = SpatialVTKConfig(tmp_path / "config.yaml", tmp_path, {"notebooks": {"show_cell_timing": False}})

    assert notebook_timing_enabled(enabled)
    assert not notebook_timing_enabled(disabled)
    assert format_run_time(0.0192) == "Run time: 19.2 ms"
    assert format_run_time(2.5) == "Run time: 2.50 s"


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
