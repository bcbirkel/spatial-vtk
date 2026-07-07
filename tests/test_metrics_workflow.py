from __future__ import annotations

import builtins
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from spatial_vtk.config.runtime import SpatialVTKConfig, clear_active_config
from spatial_vtk.io import OutputGroup
from spatial_vtk.io.plans import MetricPlan
from spatial_vtk.metrics.workflow import (
    SlurmSettings,
    StandardMetricWorkflowOutputResult,
    build_metric_waveform_inventories_from_config,
    build_metric_waveform_inventories_from_trace_metadata,
    cache_metric_manifest_waveforms,
    metric_batch_merge_readiness_from_config,
    merge_metric_batches_from_config,
    merge_batch_outputs,
    metric_manifest_batch_status,
    metric_outputs_readiness_from_config,
    metric_slurm_submission_readiness,
    metric_slurm_submission_readiness_from_config,
    metric_workflow_output_input_columns,
    load_standard_metric_workflow_outputs,
    plan_metric_tasks,
    plan_metric_tasks_from_config,
    prepare_metric_workflow_outputs,
    read_task_manifest,
    run_manifest_batch,
    run_metric_tasks,
    slurm_settings_from_config,
    summarize_metric_snapshot_tasks_from_config,
    summarize_metric_tasks,
    write_metric_outputs,
    write_metric_outputs_from_config,
    write_metric_rows,
    write_metrics_slurm_script_from_config,
    write_metrics_slurm_script,
    write_task_manifest,
    MetricWorkflowTask,
)
from spatial_vtk.metrics.plot import (
    MetricFigureContext,
    MetricFigureSuiteResult,
    StandardMetricDiagnosticFigureResult,
    plot_band_score_distribution,
    write_large_run_metric_figure_suite_from_notebook_settings,
    metric_plot_input_summary_frame,
    metric_rows_for_metrics,
    plot_period_score_distribution,
    write_standard_metric_diagnostic_figures,
    write_station_metric_map_from_notebook_settings,
)
from spatial_vtk.visualize import figure_sidecar_status_frame
from spatial_vtk.spatial.map import plot_event_residual_map
from spatial_vtk.spatial.plot import boxplot, heatmap, scatterplot
from spatial_vtk.visualize.dashboard import available_dashboard_value_columns, build_dashboard_summaries, load_dashboard_metric_dataset
import spatial_vtk.metrics.workflow.execution as metric_execution
import spatial_vtk.metrics.workflow.run as metric_run_module
import spatial_vtk.metrics.workflow.tasks as metric_tasks_module


def test_metric_inventories_from_trace_metadata_use_explicit_path_columns(tmp_path) -> None:
    """Trace metadata should become normalized observed/synthetic inventories."""

    trace_metadata = pd.DataFrame(
        {
            "source_type": ["observed", "synthetic"],
            "event_id": ["e1", "e1"],
            "station": ["abc", "abc"],
            "component": ["z", "z"],
            "input_file": ["raw_obs.mseed", "synthetic_source.mseed"],
            "output_file": ["processed_obs.npz", "processed_syn.npz"],
            "delta": [0.01, 0.02],
            "sampling_rate": [100.0, 50.0],
        }
    )
    config = SpatialVTKConfig(
        tmp_path / "config.yaml",
        tmp_path,
        {"metrics": {"models": ["model_a"]}},
    )
    observed_path = tmp_path / "observed_inventory.parquet"
    synthetic_path = tmp_path / "synthetic_inventory.parquet"

    result = build_metric_waveform_inventories_from_trace_metadata(
        trace_metadata,
        observed_path,
        synthetic_path,
        config=config,
        overwrite=True,
    )

    observed = pd.read_parquet(result.observed_path)
    synthetic = pd.read_parquet(result.synthetic_path)
    assert result.observed_rows == 1
    assert result.synthetic_rows == 1
    assert result.observed_metric_inventory_path == result.observed_path
    assert result.synthetic_metric_inventory_path == result.synthetic_path
    status = result.status_frame()
    assert status["name"].tolist() == [
        "observed_metric_inventory_path",
        "synthetic_metric_inventory_path",
    ]
    assert status["artifact"].tolist() == [
        "observed_metric_inventory",
        "synthetic_metric_inventory",
    ]
    assert status["artifact_role"].tolist() == ["metric_inventory", "metric_inventory"]
    assert status["status"].tolist() == ["ready", "ready"]
    assert status["artifact_label"].tolist() == [
        "observed metric waveform inventory",
        "synthetic metric waveform inventory",
    ]
    assert status["resolved_path"].tolist() == status["path"].tolist()
    assert status["exists"].tolist() == [True, True]
    assert status["rows"].tolist() == [1, 1]
    assert status["reused"].tolist() == [False, False]
    assert observed.loc[0, "station"] == "ABC"
    assert observed.loc[0, "component"] == "Z"
    assert observed.loc[0, "waveform_path"] == "processed_obs.npz"
    assert observed.loc[0, "dt"] == pytest.approx(0.01)
    assert synthetic.loc[0, "waveform_path"] == "synthetic_source.mseed"
    assert synthetic.loc[0, "model"] == "model_a"
    assert synthetic.loc[0, "dt"] == pytest.approx(0.02)

    reused = build_metric_waveform_inventories_from_trace_metadata(
        trace_metadata,
        observed_path,
        synthetic_path,
        overwrite=False,
    )
    assert reused.reused
    assert reused.observed_rows is None
    assert reused.synthetic_rows is None
    assert reused.status_frame()["reused"].tolist() == [True, True]


def test_direct_metric_task_runner_prefers_task_table_alias() -> None:
    """The direct task runner should describe CSV/Parquet inputs without CSV-only naming."""

    parser = metric_run_module.build_arg_parser()
    help_text = parser.format_help()

    assert "--tasks-table" in help_text
    assert "--tasks-csv" in help_text
    assert "--metric-rows-output" in help_text
    assert "--output" in help_text
    assert "legacy alias" in help_text
    assert "CSV or Parquet metric task table" in help_text

    args = parser.parse_args(
        ["--tasks-table", "tasks.parquet", "--metric-rows-output", "rows.parquet"]
    )
    legacy_args = parser.parse_args(["--tasks-csv", "tasks.csv", "--output", "rows.csv"])

    assert args.tasks_table == "tasks.parquet"
    assert args.metric_rows_output == "rows.parquet"
    assert legacy_args.tasks_table == "tasks.csv"
    assert legacy_args.metric_rows_output == "rows.csv"
    assert not hasattr(args, "tasks_csv")
    assert not hasattr(args, "output")


def test_direct_metric_batch_runner_prefers_metric_manifest_alias() -> None:
    """The direct batch runner should describe its manifest artifact explicitly."""

    parser = metric_execution.build_arg_parser()
    help_text = parser.format_help()

    assert "--metric-manifest" in help_text
    assert "--manifest" in help_text
    assert "Metric workflow manifest JSON." in help_text
    assert "legacy alias" in help_text

    args = parser.parse_args(["--metric-manifest", "metric_manifest.json", "--batch-index", "0"])
    legacy_args = parser.parse_args(["--manifest", "legacy_manifest.json", "--batch-index", "1"])

    assert args.metric_manifest == "metric_manifest.json"
    assert args.batch_index == 0
    assert legacy_args.metric_manifest == "legacy_manifest.json"
    assert legacy_args.batch_index == 1
    assert not hasattr(args, "manifest")


def test_metric_plot_input_summary_frame_reports_notebook_inputs() -> None:
    """Plotting notebooks should use package-owned metric input summaries."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e1", "e2"],
            "station": ["STA1", "STA2", "STA1"],
            "metric": ["PGA", "PGV", "PGA"],
        }
    )
    comparison_eligible = pd.DataFrame({"event_id": ["e1", "e2"]})

    summary = metric_plot_input_summary_frame(metrics, comparison_eligible=comparison_eligible).set_index("Input")["Value"]

    assert summary["Metric rows"] == 3
    assert summary["Events"] == 2
    assert summary["Stations"] == 2
    assert summary["Metrics"] == "PGA, PGV"
    assert summary["Waveform preview pairs"] == 2


def test_metric_plot_input_summary_frame_handles_missing_optional_columns() -> None:
    """The summary helper should not force every plotting table to share one schema."""

    summary = metric_plot_input_summary_frame(pd.DataFrame({"value": [1.0]})).set_index("Input")["Value"]

    assert summary["Metric rows"] == 1
    assert pd.isna(summary["Events"])
    assert pd.isna(summary["Stations"])
    assert pd.isna(summary["Metrics"])


def test_metric_rows_for_metrics_matches_aliases_and_preserves_order() -> None:
    """Plotting notebooks should use package-owned metric row filtering."""

    metrics = pd.DataFrame(
        {
            "metric": ["PGV", "Arias duration (5-95%)", "FAS", "Peak acceleration (PGA)", "PGD"],
            "value": [1, 2, 3, 4, 5],
        }
    )

    selected = metric_rows_for_metrics(metrics, ["pga", "Arias duration", "PGV"])

    assert selected["value"].tolist() == [1, 2, 4]


def test_metric_rows_for_metrics_handles_missing_inputs() -> None:
    """Metric row filtering should be safe for optional notebook branches."""

    metrics = pd.DataFrame({"value": [1.0]})

    assert metric_rows_for_metrics(None, ["PGA"]).empty
    assert metric_rows_for_metrics(metrics, ["PGA"]).empty
    assert list(metric_rows_for_metrics(metrics, ["PGA"]).columns) == ["value"]
    assert metric_rows_for_metrics(pd.DataFrame({"metric": ["PGV"]}), []).empty


def test_write_standard_metric_diagnostic_figures_owns_step03_plot_calls(tmp_path) -> None:
    """Standard Step 3 metric diagnostics should be package-owned."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e1", "e1", "e2"],
            "station": ["STA", "STB", "STC", "STD"],
            "metric": ["PGA", "PGV", "PGD", "FAS"],
            "band": ["1-2 sec", "2-3 sec", "3-5 sec", "1-2 sec"],
            "distance_km": [10.0, 20.0, 30.0, 40.0],
            "log2_residual": [0.1, -0.2, 0.3, 0.4],
            "anderson_2004_gof": [8.0, 7.0, 6.0, 5.0],
        }
    )
    outputs = OutputGroup(
        name="step_03_metrics",
        paths={
            "residuals_vs_distance_figure_path": tmp_path / "figures" / "residuals_vs_distance.png",
            "score_trends_figure_path": tmp_path / "figures" / "score_trends.png",
            "band_score_distribution_figure_path": tmp_path / "figures" / "band_distribution.png",
        },
    )
    seen: list[tuple[str, Path, list[str], dict[str, object]]] = []

    class Sidecars:
        @staticmethod
        def kwargs(**_kwargs) -> dict[str, object]:
            return {
                "write_sidecar": True,
                "sidecar_rows": 10,
                "sidecar_dir": tmp_path / "sidecars",
            }

    class Settings:
        showfig = False
        sidecars = Sidecars()

    def _fake_plot(name):
        def _inner(frame: pd.DataFrame, *, outpath, **kwargs):
            output = Path(outpath)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(name, encoding="utf-8")
            seen.append((name, output, frame["metric"].tolist(), kwargs))

        return _inner

    result = write_standard_metric_diagnostic_figures(
        metrics,
        outputs,
        Settings(),
        residuals_plot_func=_fake_plot("residuals"),
        score_trends_plot_func=_fake_plot("scores"),
        band_distribution_plot_func=_fake_plot("band"),
    )

    assert isinstance(result, StandardMetricDiagnosticFigureResult)
    assert [item[0] for item in seen] == ["residuals", "scores", "band"]
    assert seen[0][1].name == "step_03_residuals_vs_distance.png"
    assert seen[1][1].name == "step_03_score_trends.png"
    assert seen[2][1].name == "step_03_band_residual_distribution.png"
    for _, _, metric_names, kwargs in seen:
        assert metric_names == ["PGA", "PGV", "PGD"]
        assert kwargs["showfig"] is False
        assert kwargs["savefig"] is True
        assert kwargs["write_sidecar"] is True
        assert kwargs["sidecar_rows"] == 10
        assert kwargs["sidecar_dir"] == tmp_path / "sidecars"
    assert seen[0][3]["y_col"] == "log2_residual"
    assert seen[1][3]["score_col"] == "anderson_2004_gof"
    assert seen[2][3]["band_col"] == "band"
    status = result.status_frame()
    assert status["artifact"].tolist() == ["residuals_vs_distance", "score_trends", "band_score_distribution"]
    assert status["status"].tolist() == ["wrote", "wrote", "wrote"]
    assert status["figure_exists"].tolist() == [True, True, True]
    preview = result.preview_frame().set_index("Input")
    assert preview.loc["Metric rows", "Value"] == 3
    assert preview.loc["Metrics", "Value"] == "PGA, PGV, PGD"


def test_standard_metric_workflow_output_result_writes_diagnostic_figures(tmp_path) -> None:
    """The standard Step 3 result should own diagnostic table/output wiring."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e1", "e2"],
            "station": ["STA", "STB", "STC"],
            "metric": ["PGA", "PGV", "FAS"],
            "band": ["1-2 sec", "2-3 sec", ""],
            "distance_km": [10.0, 20.0, 30.0],
            "log2_residual": [0.1, -0.2, 0.3],
            "anderson_2004_gof": [8.0, 7.0, 6.0],
        }
    )
    task_estimate = pd.DataFrame({"item": ["tasks"], "value": [2]})
    seen: list[tuple[str, Path, list[str]]] = []

    class Outputs:
        def load_table(self, name, **_kwargs):
            if name == "metric_task_estimate_path":
                return task_estimate
            if name == "metrics_long":
                return metrics
            raise KeyError(name)

        def figure_path(self, _name, *, stem_parts):
            return tmp_path / "figures" / f"{'_'.join(stem_parts)}.png"

    class Sidecars:
        @staticmethod
        def kwargs(**_kwargs) -> dict[str, object]:
            return {}

    class Settings:
        showfig = False
        sidecars = Sidecars()

    def _fake_plot(name):
        def _inner(frame: pd.DataFrame, *, outpath, **_kwargs):
            output = Path(outpath)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(name, encoding="utf-8")
            seen.append((name, output, frame["metric"].tolist()))

        return _inner

    result = StandardMetricWorkflowOutputResult(outputs=Outputs()).with_task_estimate()
    assert result.task_estimate.equals(task_estimate)

    diagnostic_result = result.write_standard_diagnostic_figures(
        Settings(),
        metric_names=("PGA", "PGV"),
        residuals_plot_func=_fake_plot("residuals"),
        score_trends_plot_func=_fake_plot("scores"),
        band_distribution_plot_func=_fake_plot("band"),
    )

    assert isinstance(diagnostic_result, StandardMetricDiagnosticFigureResult)
    assert [item[0] for item in seen] == ["residuals", "scores", "band"]
    assert {metric for _, _, metrics_seen in seen for metric in metrics_seen} == {"PGA", "PGV"}
    diagnostic_status = diagnostic_result.status_frame()
    assert {"name", "artifact_label", "artifact_role", "resolved_path", "path", "exists"} <= set(
        diagnostic_status.columns
    )
    assert diagnostic_status["artifact_role"].tolist() == ["figure", "figure", "figure"]
    assert diagnostic_status["status"].tolist() == ["wrote", "wrote", "wrote"]
    assert diagnostic_status["figure_exists"].tolist() == [True, True, True]
    assert diagnostic_status["exists"].tolist() == [True, True, True]
    assert diagnostic_status["path"].tolist() == diagnostic_status["figure_path"].tolist()


def test_standard_metric_workflow_outputs_do_not_load_task_estimate_by_default(monkeypatch, tmp_path) -> None:
    """Step 3 output handles should not materialize task estimates unless requested."""

    class Outputs:
        metrics_long_path = tmp_path / "metrics_long.parquet"

        def load_table(self, name, **_kwargs):  # noqa: ANN001
            raise AssertionError(f"unexpected eager table load: {name}")

    class Preprocessed:
        trace_metadata_path = tmp_path / "trace_metadata.parquet"

    monkeypatch.setattr("spatial_vtk.io.output_group", lambda *args, **kwargs: Outputs())
    monkeypatch.setattr(
        "spatial_vtk.io.preprocessed_waveform_metadata_paths",
        lambda *args, **kwargs: Preprocessed(),
    )

    result = load_standard_metric_workflow_outputs(cfg=tmp_path / "config.yaml")

    assert result.task_estimate is None
    assert result.metrics_long_path == tmp_path / "metrics_long.parquet"
    assert result.trace_metadata_path == tmp_path / "trace_metadata.parquet"


def test_standard_metric_workflow_output_result_owns_outputs_and_station_map(monkeypatch, tmp_path) -> None:
    """The standard Step 3 result should own configured outputs and station-map wiring."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1"],
            "station": ["STA"],
            "metric": ["PGA"],
            "band": ["1-2 sec"],
            "distance_km": [10.0],
            "log2_residual": [0.1],
        }
    )

    class Config:
        config_path = tmp_path / "spatial-vtk.yaml"
        run_scenario = "tutorial"

    class Outputs:
        def load_table(self, name, **_kwargs):
            if name == "metrics_long":
                return metrics
            raise KeyError(name)

    output_calls: list[dict[str, object]] = []

    def fake_write_metric_outputs_from_config(**kwargs):
        output_calls.append(kwargs)
        return {"metrics_long": "metrics_long.parquet"}

    monkeypatch.setattr(
        "spatial_vtk.metrics.workflow.configured.write_metric_outputs_from_config",
        fake_write_metric_outputs_from_config,
    )

    map_calls: list[dict[str, object]] = []

    def fake_write_station_metric_map_from_notebook_settings(frame, settings, **kwargs):
        map_calls.append({"frame": frame, "settings": settings, "kwargs": kwargs})
        return "station-map"

    monkeypatch.setattr(
        "spatial_vtk.metrics.plot.write_station_metric_map_from_notebook_settings",
        fake_write_station_metric_map_from_notebook_settings,
    )

    result = StandardMetricWorkflowOutputResult(outputs=Outputs(), cfg=Config())
    assert result.write_configured_outputs(
        residual_column="log2_residual",
        score_column="anderson_2004_gof",
        table_format="parquet",
        dashboard_partitioned=False,
    ) == {"metrics_long": "metrics_long.parquet"}
    assert output_calls == [
        {
            "config_path": Config.config_path,
            "run_scenario": "tutorial",
            "metric_rows": None,
            "events": None,
            "stations": None,
            "residual_column": "log2_residual",
            "score_column": "anderson_2004_gof",
            "table_format": "parquet",
            "dashboard_partitioned": False,
        }
    ]
    output_calls.clear()

    path_result = StandardMetricWorkflowOutputResult(outputs=Outputs(), cfg=Config.config_path)
    assert path_result.write_configured_outputs(table_format="csv") == {"metrics_long": "metrics_long.parquet"}
    assert output_calls == [
        {
            "config_path": Config.config_path,
            "run_scenario": None,
            "metric_rows": None,
            "events": None,
            "stations": None,
            "residual_column": None,
            "score_column": None,
            "table_format": "csv",
            "dashboard_partitioned": True,
        }
    ]
    output_calls.clear()

    class Context:
        config_path = tmp_path / "context-config.yaml"
        run_scenario = "large-run"

    context_result = StandardMetricWorkflowOutputResult(outputs=Outputs())
    assert context_result.write_configured_outputs(context=Context(), table_format="csv") == {
        "metrics_long": "metrics_long.parquet"
    }
    assert output_calls == [
        {
            "config_path": Context.config_path,
            "run_scenario": "large-run",
            "metric_rows": None,
            "events": None,
            "stations": None,
            "residual_column": None,
            "score_column": None,
            "table_format": "csv",
            "dashboard_partitioned": True,
        }
    ]

    settings = object()
    assert result.write_station_metric_map(
        settings,
        metric="PGA",
        value_col="log2_residual",
        passband="1-2 sec",
        components=["R", "T"],
        model="model_a",
        title="Station PGA",
        preview_rows=3,
        make_figures=False,
        overwrite=False,
    ) == "station-map"
    assert len(map_calls) == 1
    assert map_calls[0]["frame"].equals(metrics)
    assert map_calls[0]["settings"] is settings
    assert map_calls[0]["kwargs"] == {
        "metric": "PGA",
        "value_col": "log2_residual",
        "passband": "1-2 sec",
        "components": ["R", "T"],
        "model": "model_a",
        "title": "Station PGA",
        "preview_rows": 3,
        "make_figures": False,
        "overwrite": False,
    }


def test_standard_metric_workflow_output_result_owns_large_run_steps(monkeypatch, tmp_path) -> None:
    """Large-run Step 3 cells should delegate orchestration through the result object."""

    class Config:
        config_path = tmp_path / "spatial-vtk.yaml"
        run_scenario = "large"

    class Context:
        config_path = tmp_path / "fallback.yaml"
        run_scenario = "fallback"

    class Outputs:
        metrics_long_path = tmp_path / "metrics_long.parquet"

    def fake_function(**_kwargs):
        return {"ok": True}

    run_calls: list[dict[str, object]] = []

    def fake_run_notebook_step_if_needed(context, readiness, function, **kwargs):
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
        def _inner(**kwargs):
            readiness_calls.append((name, kwargs))
            return f"{name}-readiness"

        return _inner

    for name in (
        "build_metric_waveform_inventories_from_config",
        "plan_metric_tasks_from_config",
        "write_metrics_slurm_script_from_config",
        "merge_metric_batches_from_config",
        "write_metric_outputs_from_config",
    ):
        monkeypatch.setattr(f"spatial_vtk.metrics.workflow.configured.{name}", fake_function)
    monkeypatch.setattr(
        "spatial_vtk.metrics.workflow.configured.metric_inventories_readiness_from_config",
        readiness_factory("inventory"),
    )
    monkeypatch.setattr(
        "spatial_vtk.metrics.workflow.configured.metric_manifest_readiness_from_config",
        readiness_factory("manifest"),
    )
    monkeypatch.setattr(
        "spatial_vtk.metrics.workflow.configured.metric_slurm_submission_readiness_from_config",
        readiness_factory("slurm"),
    )
    monkeypatch.setattr(
        "spatial_vtk.metrics.workflow.configured.metric_batch_merge_readiness_from_config",
        readiness_factory("merge"),
    )
    monkeypatch.setattr(
        "spatial_vtk.metrics.workflow.configured.metric_outputs_readiness_from_config",
        readiness_factory("outputs"),
    )

    result = StandardMetricWorkflowOutputResult(outputs=Outputs(), cfg=Config())
    context = Context()
    assert result.run_inventory_step_if_needed(context, overwrite=True, run_local=False) == {"readiness": "inventory-readiness"}
    assert result.run_manifest_step_if_needed(context, batch_count=17) == {"readiness": "manifest-readiness"}
    assert result.run_slurm_step_if_needed(context, overwrite=True, submit=True) == {"readiness": "slurm-readiness"}
    assert result.run_merge_step_if_needed(context) == {"readiness": "merge-readiness"}
    assert result.run_downstream_outputs_step_if_needed(context, table_format="csv") == {"readiness": "outputs-readiness"}

    assert [name for name, _ in readiness_calls] == ["inventory", "manifest", "slurm", "merge", "outputs"]
    for _, kwargs in readiness_calls:
        assert kwargs["config_path"] == Config.config_path
        assert kwargs["run_scenario"] == "large"
    assert readiness_calls[0][1]["overwrite"] is True
    assert readiness_calls[1][1]["current_message"] == "Metric manifest is current; skipping planning."
    assert readiness_calls[2][1]["overwrite"] is True

    assert len(run_calls) == 5
    assert [call["readiness"] for call in run_calls] == [
        "inventory-readiness",
        "manifest-readiness",
        "slurm-readiness",
        "merge-readiness",
        "outputs-readiness",
    ]
    assert run_calls[0]["kwargs"]["script_name"] == "step03_metric_inventories.slurm"
    assert run_calls[0]["kwargs"]["run_local"] is False
    assert run_calls[0]["kwargs"]["kwargs"]["overwrite"] is True
    assert run_calls[1]["kwargs"]["kwargs"]["batch_count"] == 17
    assert run_calls[1]["kwargs"]["run_local"] is True
    assert run_calls[2]["kwargs"]["kwargs"]["incomplete_only"] is False
    assert run_calls[2]["kwargs"]["kwargs"]["overwrite_batches"] is True
    assert run_calls[2]["kwargs"]["kwargs"]["submit"] is True
    assert run_calls[3]["kwargs"]["script_name"] == "step03_merge_metric_batches.slurm"
    assert run_calls[4]["kwargs"]["kwargs"]["table_format"] == "csv"
    assert run_calls[4]["kwargs"]["kwargs"]["dashboard_partitioned"] is True

    figure_calls: list[dict[str, object]] = []

    def fake_figure_suite(metrics_path, settings, **kwargs):
        figure_calls.append({"metrics_path": metrics_path, "settings": settings, "kwargs": kwargs})
        return "figures"

    monkeypatch.setattr(
        "spatial_vtk.metrics.plot.write_large_run_metric_figure_suite_from_notebook_settings",
        fake_figure_suite,
    )
    settings = object()
    assert result.write_large_run_figure_suite(settings, overwrite=True) == "figures"
    assert figure_calls == [
        {"metrics_path": Outputs.metrics_long_path, "settings": settings, "kwargs": {"overwrite": True}}
    ]


def test_metric_inventories_from_config_resolve_standard_paths(tmp_path) -> None:
    """Config-backed inventory helper should use preprocessing and output defaults."""

    clear_active_config()
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
  preprocessed_waveforms: outputs/preprocessed_waveforms
metrics:
  models: [model_a]
""",
        encoding="utf-8",
    )
    metadata_dir = tmp_path / "outputs" / "preprocessed_waveforms" / "metadata"
    metadata_dir.mkdir(parents=True)
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
    ).to_csv(metadata_dir / "trace_metadata_preprocessed.csv", index=False)

    result = build_metric_waveform_inventories_from_config(config_path=config_path, overwrite=True)

    observed = pd.read_parquet(result["observed_path"])
    synthetic = pd.read_parquet(result["synthetic_path"])
    assert Path(result["observed_path"]) == tmp_path / "outputs" / "tables" / "observed_metric_inventory.parquet"
    assert Path(result["synthetic_path"]) == tmp_path / "outputs" / "tables" / "synthetic_metric_inventory.parquet"
    assert result["observed_metric_inventory_path"] == result["observed_path"]
    assert result["synthetic_metric_inventory_path"] == result["synthetic_path"]
    assert observed.loc[0, "waveform_path"] == "processed_obs.npz"
    assert synthetic.loc[0, "model"] == "model_a"


def test_metric_figure_context_aggregates_full_station_rows_and_writes_sidecars(tmp_path) -> None:
    """Large-run figure helpers should aggregate full metric rows before plotting."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3", "e4", "e1", "e2"],
            "station": ["STA", "STA", "STB", "STA", "STA", "STA"],
            "sta_lon": [-118.00, -118.02, -117.5, -118.01, -118.0, -118.02],
            "sta_lat": [34.00, 34.02, 34.2, 34.01, 34.0, 34.02],
            "metric": ["PGA", "PGA", "PGA", "PGA", "PSA", "PSA"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec", "1-2 sec", "", ""],
            "model": ["m1", "m1", "m1", "m2", "m1", "m1"],
            "component": ["Z", "Z", "Z", "Z", "Z", "Z"],
            "period_s": [np.nan, np.nan, np.nan, np.nan, 1.0, 2.0],
            "distance_km": [10.0, 20.0, 30.0, 40.0, 10.0, 10.0],
            "log2_residual": [1.0, 3.0, 5.0, 7.0, 0.5, 0.75],
        }
    )
    metrics = pd.concat(
        [
            metrics,
            pd.DataFrame(
                {
                    "event_id": ["e5", "e3"],
                    "station": ["STA", "STA"],
                    "sta_lon": [-118.03, -118.02],
                    "sta_lat": [34.03, 34.02],
                    "metric": ["PGA", "PSA"],
                    "band": ["1-2 sec", ""],
                    "model": ["m1", "m1"],
                    "component": ["Z", "Z"],
                    "period_s": [np.nan, 2.0],
                    "distance_km": [50.0, 10.0],
                    "log2_residual": [np.nan, np.inf],
                }
            ),
        ],
        ignore_index=True,
    )
    metrics_path = tmp_path / "metrics_long.parquet"
    metrics.to_parquet(metrics_path, index=False)
    context = MetricFigureContext.from_metrics_long(
        metrics_path,
        tmp_path / "figures",
        make_figures=True,
        overwrite=True,
        sample_rows=2,
        write_sidecars=True,
        sidecar_rows=1,
        station_aggregation="mean",
    )

    assert context.ready
    assert len(context.metrics_for_figures) == len(metrics)
    context_status_frame = context.status_frame()
    assert {
        "name",
        "value",
        "artifact_role",
        "artifact_label",
        "status",
        "resolved_path",
        "path",
        "exists",
    } <= set(context_status_frame.columns)
    context_status = context_status_frame.set_index("name")
    assert bool(context_status.loc["value_col_present", "value"]) is True
    assert context_status.loc["value_col_present", "artifact_role"] == "schema_check"
    assert context_status.loc["value_col_present", "status"] == "ready"
    assert context_status.loc["finite_value_rows", "value"] == 6
    assert context_status.loc["finite_value_rows", "status"] == "ready"
    assert context_status.loc["nonfinite_value_rows", "value"] == 2
    assert context_status.loc["metrics_long_path", "artifact_label"] == "metrics long source table"
    assert context_status.loc["metrics_long_path", "artifact_role"] == "input_table"
    assert context_status.loc["metrics_long_path", "resolved_path"] == str(metrics_path)
    assert bool(context_status.loc["metrics_long_path", "exists"]) is True
    assert context_status.loc["metrics_long_path", "status"] == "ready"
    assert context_status.loc["figure_dir", "artifact_role"] == "figure_directory"
    selection_status = context.metric_selection_status_frame(components=["Z"], model="m1").set_index("metric_key")
    assert selection_status.loc["pga", "status_reason"] == "selected"
    assert selection_status.loc["pga", "selected_row_count"] == 4
    assert selection_status.loc["psa", "status_reason"] == "selected"
    assert selection_status.loc["psa", "selected_row_count"] == 3
    assert "traveltime_delay" not in selection_status.index
    pga_item = next(context.iter_metric_frames(passband="1-2 sec", components=["Z"], model="m1", split_psa_period=False))
    station_summary = context.station_summary_for_map(pga_item["df"])
    item_station_summary = context.station_summary_for_item(pga_item)
    item_station_grid = context.station_grid_for_item(pga_item)
    named_station_summary = context.station_summary_for_metric(
        "Peak ground acceleration",
        passband="1-2 sec",
        components=["Z"],
        model="m1",
    )
    named_station_preview = context.station_summary_preview_for_metric(
        "Peak ground acceleration",
        passband="1-2 sec",
        components=["Z"],
        model="m1",
        nrows=1,
    )
    assert item_station_summary[["station", "log2_residual"]].to_dict("records") == station_summary[
        ["station", "log2_residual"]
    ].to_dict("records")
    assert named_station_summary[["station", "log2_residual"]].to_dict("records") == station_summary[
        ["station", "log2_residual"]
    ].to_dict("records")
    assert list(named_station_preview.columns) == [
        "station",
        "log2_residual",
        "source_row_count",
        "source_event_count",
        "aggregation",
    ]
    assert len(named_station_preview) == 1
    assert named_station_preview.loc[0, "station"] == "STA"
    assert {"lon", "lat"}.issubset(item_station_grid.columns)
    assert {"sta_lon", "sta_lat"}.isdisjoint(item_station_grid.columns)
    sta = station_summary.loc[station_summary["station"].eq("STA")].iloc[0]
    assert sta["log2_residual"] == pytest.approx(2.0)
    assert sta["sta_lon"] == pytest.approx(-118.02)
    assert sta["sta_lat"] == pytest.approx(34.02)
    assert sta["source_row_count"] == 2
    assert sta["source_event_count"] == 2
    assert sta["input_row_count"] == 3
    assert sta["input_event_count"] == 3
    assert sta["dropped_nonfinite_row_count"] == 1
    assert sta["dropped_nonfinite_event_count"] == 1
    assert sta["source_coordinate_count"] == 3
    assert sta["aggregation"] == "mean"
    assert station_summary.attrs["svtk_aggregation_kind"] == "station_event_rows_to_station_summary"
    assert station_summary.attrs["svtk_aggregation_value_col"] == "log2_residual"
    assert station_summary.attrs["svtk_aggregation_method"] == "mean"
    assert station_summary.attrs["svtk_aggregation_group_columns"] == ["station"]
    assert station_summary.attrs["svtk_aggregation_coordinate_columns"] == ["sta_lon", "sta_lat"]
    assert station_summary.attrs["svtk_aggregation_input_row_count"] == 4
    assert station_summary.attrs["svtk_aggregation_finite_row_count"] == 3
    assert station_summary.attrs["svtk_aggregation_dropped_nonfinite_row_count"] == 1

    station_model_summary = context.station_summary_for_map(
        metrics.loc[metrics["metric"].eq("PGA")],
        extra_group_cols=["model"],
    )
    pga_all_models = next(context.iter_metric_frames(passband="1-2 sec", components=["Z"], split_psa_period=False))
    station_model_item_summary = context.station_model_summary_for_item(pga_all_models)
    station_model_item_grid = context.station_model_grid_for_item(pga_all_models)
    assert set(station_model_item_summary["model"]) == {"m1", "m2"}
    assert {"lon", "lat", "model"}.issubset(station_model_item_grid.columns)
    assert station_model_summary.attrs["svtk_aggregation_group_columns"] == ["station", "model"]

    assert set(station_model_summary["model"]) == {"m1", "m2"}
    sta_m1 = station_model_summary.loc[
        station_model_summary["station"].eq("STA") & station_model_summary["model"].eq("m1")
    ].iloc[0]
    sta_m2 = station_model_summary.loc[
        station_model_summary["station"].eq("STA") & station_model_summary["model"].eq("m2")
    ].iloc[0]
    assert sta_m1["log2_residual"] == pytest.approx(2.0)
    assert sta_m2["log2_residual"] == pytest.approx(7.0)
    assert sta_m1["source_event_count"] == 2
    assert sta_m1["input_event_count"] == 3
    assert sta_m1["dropped_nonfinite_row_count"] == 1
    assert sta_m1["dropped_nonfinite_event_count"] == 1
    assert sta_m2["source_event_count"] == 1
    assert sta_m2["dropped_nonfinite_row_count"] == 0
    assert sta_m2["dropped_nonfinite_event_count"] == 0
    assert sta_m1["source_coordinate_count"] == 3
    assert sta_m2["source_coordinate_count"] == 1

    psa_item = [item for item in context.iter_metric_frames(components=["Z"], model="m1", split_psa_period=False) if item["key"] == "psa"][0]
    assert "all-psa-periods" in context.figure_name("station_metric_map", psa_item)
    assert "1-2-sec" not in context.figure_name("station_metric_map", psa_item)
    station_period_summary = context.station_period_summary_for_map(psa_item["df"])
    item_period_summary = context.station_period_summary_for_item(psa_item)
    assert item_period_summary[["station", "period_s", "log2_residual"]].to_dict("records") == station_period_summary[
        ["station", "period_s", "log2_residual"]
    ].to_dict("records")
    assert station_period_summary.attrs["svtk_aggregation_group_columns"] == ["station", "period_s"]
    assert set(station_period_summary["period_s"]) == {1.0, 2.0}
    assert station_period_summary["source_row_count"].tolist() == [1, 1]
    assert station_period_summary["input_row_count"].tolist() == [1, 2]
    assert station_period_summary["dropped_nonfinite_row_count"].tolist() == [0, 1]
    assert station_period_summary["dropped_nonfinite_event_count"].tolist() == [0, 1]

    def _dummy_plot(frame: pd.DataFrame, *, output_path, **kwargs) -> None:
        Path(output_path).write_text(str(len(frame)), encoding="utf-8")

    output = context.write_metric_plot("debug_rows", pga_item, _dummy_plot, df=station_summary, source_df=pga_item["df"])
    assert output is not None
    sidecar = context.sidecar_output_dir / f"{output.stem}.csv"
    source_sidecar = context.sidecar_output_dir / f"{output.stem}.source.csv"
    metadata_path = sidecar.with_suffix(".json")
    assert sidecar.exists()
    assert source_sidecar.exists()
    assert metadata_path.exists()
    sidecar_rows = pd.read_csv(sidecar)
    source_sidecar_rows = pd.read_csv(source_sidecar)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert len(sidecar_rows) == 1
    assert len(source_sidecar_rows) == 1
    assert metadata["plot_row_count"] == 2
    assert metadata["source_row_count"] == 4
    assert metadata["source_written_row_count"] == 1
    assert metadata["source_sampled"] is True
    assert metadata["written_row_count"] == 1
    assert metadata["sampled"] is True
    assert metadata["plot_station_count"] == 2
    assert metadata["source_station_count"] == 2
    assert metadata["source_event_count"] == 4
    assert metadata["source_model_count"] == 1
    assert metadata["aggregation_contract"] == "station_event_rows_to_station_summary"
    assert metadata["aggregation_kind"] == "station_event_rows_to_station_summary"
    assert metadata["aggregation_value_col"] == "log2_residual"
    assert metadata["aggregation_method"] == "mean"
    assert metadata["aggregation_group_columns"] == ["station"]
    assert metadata["aggregation_coordinate_columns"] == ["sta_lon", "sta_lat"]
    assert metadata["aggregation_input_row_count"] == 4
    assert metadata["aggregation_finite_row_count"] == 3
    assert metadata["aggregation_dropped_nonfinite_row_count"] == 1
    assert "source sidecar rows are the metric rows aggregated" in metadata["aggregation_audit"]
    assert metadata["plot_rows_role"] == "post_aggregation_station_summary"
    assert metadata["source_rows_role"] == "pre_aggregation_metric_rows"
    assert metadata["svtk_aggregation_kind"] == "station_event_rows_to_station_summary"
    assert metadata["svtk_aggregation_value_col"] == "log2_residual"
    assert metadata["svtk_aggregation_method"] == "mean"
    assert metadata["svtk_aggregation_group_columns"] == ["station"]
    assert metadata["svtk_aggregation_coordinate_columns"] == ["sta_lon", "sta_lat"]
    assert metadata["svtk_aggregation_input_row_count"] == 4
    assert metadata["svtk_aggregation_finite_row_count"] == 3
    assert metadata["svtk_aggregation_dropped_nonfinite_row_count"] == 1
    status = figure_sidecar_status_frame(context.sidecar_output_dir).set_index("figure")
    status_row = status.loc[f"{output.stem}.png"]
    assert status_row["aggregation_group_columns"] == ["station"]
    assert status_row["aggregation_coordinate_columns"] == ["sta_lon", "sta_lat"]
    assert status_row["aggregation_input_row_count"] == 4
    assert status_row["aggregation_finite_row_count"] == 3
    assert status_row["aggregation_dropped_nonfinite_row_count"] == 1
    assert status_row["aggregation_input_station_count"] == 2
    assert status_row["aggregation_finite_station_count"] == 2
    assert status_row["aggregation_input_event_count"] == 4
    assert status_row["aggregation_finite_event_count"] == 3
    assert status_row["plot_station_count"] == 2
    assert status_row["source_station_count"] == 2
    assert status_row["source_event_count"] == 4
    assert status_row["source_model_count"] == 1

    context.sample_rows = 0
    context.sidecar_rows = None

    output_all = context.write_metric_plot("debug_all_rows", pga_item, _dummy_plot, df=station_summary, source_df=pga_item["df"])
    assert output_all is not None
    all_sidecar = pd.read_csv(context.sidecar_output_dir / f"{output_all.stem}.csv")
    all_source_sidecar = pd.read_csv(context.sidecar_output_dir / f"{output_all.stem}.source.csv")
    all_metadata = json.loads((context.sidecar_output_dir / f"{output_all.stem}.json").read_text(encoding="utf-8"))
    all_source_keys = set(zip(all_source_sidecar["event_id"].astype(str), all_source_sidecar["station"].astype(str)))
    assert len(all_sidecar) == 2
    assert len(all_source_sidecar) == 4
    assert all_source_keys == {("e1", "STA"), ("e2", "STA"), ("e3", "STB"), ("e5", "STA")}
    assert all_metadata["plot_row_count"] == 2
    assert all_metadata["source_row_count"] == 4
    assert all_metadata["source_written_row_count"] == 4
    assert all_metadata["source_sampled"] is False

    def _dummy_png_plot(frame: pd.DataFrame, *, output_path, **kwargs) -> None:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(2, 1.5))
        ax.text(0.5, 0.5, f"rows={len(frame)}", ha="center", va="center")
        ax.set_axis_off()
        fig.savefig(output_path)
        plt.close(fig)

    psa_output = context.write_psa_period_sheet(
        "station_metric_map",
        psa_item,
        _dummy_png_plot,
        df_factory=context.station_period_summary_for_item,
        source_df_factory=context.item_source_rows,
        required=("station", "sta_lon", "sta_lat", "period_s", "log2_residual"),
    )
    assert psa_output is not None
    psa_sidecar = context.sidecar_output_dir / f"{psa_output.stem}.csv"
    psa_source_sidecar = context.sidecar_output_dir / f"{psa_output.stem}.source.csv"
    psa_metadata = json.loads(psa_sidecar.with_suffix(".json").read_text(encoding="utf-8"))
    psa_rows = pd.read_csv(psa_sidecar)
    psa_source_rows = pd.read_csv(psa_source_sidecar)
    assert psa_sidecar.exists()
    assert psa_source_sidecar.exists()
    assert set(psa_rows["__svtk_panel_period_s"]) == {1.0, 2.0}
    assert set(psa_rows["period_s"]) == {1.0, 2.0}
    assert set(psa_source_rows["__svtk_panel_period_s"]) == {1.0, 2.0}
    assert set(zip(psa_source_rows["event_id"].astype(str), psa_source_rows["station"].astype(str), psa_source_rows["period_s"].astype(float))) == {
        ("e1", "STA", 1.0),
        ("e2", "STA", 2.0),
        ("e3", "STA", 2.0),
    }
    custom_psa_output = context.write_psa_period_sheet(
        "station_metric_map_custom",
        psa_item,
        _dummy_png_plot,
        df_factory=context.station_period_summary_for_item,
        source_df_factory=context.item_source_rows,
        required=("station", "sta_lon", "sta_lat", "period_s", "distance_km"),
        value_col="distance_km",
    )
    assert custom_psa_output is not None
    custom_psa_sidecar = context.sidecar_output_dir / f"{custom_psa_output.stem}.csv"
    custom_psa_metadata = json.loads(custom_psa_sidecar.with_suffix(".json").read_text(encoding="utf-8"))
    custom_psa_rows = pd.read_csv(custom_psa_sidecar)
    assert custom_psa_metadata["aggregation_value_col"] == "distance_km"
    assert custom_psa_metadata["svtk_aggregation_value_col"] == "distance_km"
    assert set(custom_psa_rows["distance_km"]) == {10.0}
    assert set(psa_source_rows["period_s"]) == {1.0, 2.0}
    assert psa_metadata["plot_row_count"] == 2
    assert psa_metadata["source_row_count"] == 3
    assert psa_metadata["source_written_row_count"] == 3
    assert psa_metadata["written_row_count"] == 2
    assert psa_metadata["sampled"] is False

    diagnostic_outputs = context.write_standard_metric_diagnostic_plots(
        _dummy_png_plot,
        _dummy_png_plot,
        _dummy_png_plot,
        _dummy_png_plot,
        passband="1-2 sec",
        components=["Z"],
        model="m1",
    )
    stems = {path.stem for path in diagnostic_outputs}
    assert any(stem.startswith("scatterplot__pga") for stem in stems)
    assert any(stem.startswith("boxplot__pga") for stem in stems)
    assert any(stem.startswith("heatmap__all_metrics") for stem in stems)
    assert any(stem.startswith("scatterplot__psa") for stem in stems)
    assert any(stem.startswith("boxplot__psa") for stem in stems)
    for path in diagnostic_outputs:
        diagnostic_sidecar = context.sidecar_output_dir / f"{path.stem}.csv"
        diagnostic_metadata = context.sidecar_output_dir / f"{path.stem}.json"
        assert diagnostic_sidecar.exists(), path.name
        assert diagnostic_metadata.exists(), path.name
        metadata = json.loads(diagnostic_metadata.read_text(encoding="utf-8"))
        assert metadata["plot_row_count"] >= metadata["written_row_count"] > 0
        assert metadata["source_row_count"] >= metadata["written_row_count"]


def test_metric_figure_context_reports_legacy_psa_selection_without_printing(tmp_path, capsys) -> None:
    """Passband-scoped legacy PSA rows should be skipped through status tables."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "station": ["STA", "STA"],
            "sta_lon": [-118.0, -118.0],
            "sta_lat": [34.0, 34.0],
            "metric": ["PSA", "PSA"],
            "band": ["1-2 sec", "2-3 sec"],
            "model": ["m1", "m1"],
            "component": ["Z", "Z"],
            "period_s": [1.0, 2.0],
            "log2_residual": [0.5, 0.75],
        }
    )
    metrics_path = tmp_path / "metrics_long.parquet"
    metrics.to_parquet(metrics_path, index=False)
    context = MetricFigureContext.from_metrics_long(metrics_path, tmp_path / "figures", make_figures=True)
    capsys.readouterr()

    assert list(context.iter_metric_frames(split_psa_period=False)) == []
    captured = capsys.readouterr()
    assert captured.out == ""
    selection = context.metric_selection_status_frame().set_index("metric_key")
    assert selection.loc["psa", "status"] == "skipped"
    assert selection.loc["psa", "row_count"] == 2
    assert selection.loc["psa", "selected_row_count"] == 0
    assert selection.loc["psa", "status_reason"] == "no_broadband_spectral_rows"
    assert "blank/broadband passbands" in selection.loc["psa", "message"]


def test_metric_figure_context_discovers_config_metric_names_for_figures(tmp_path) -> None:
    """Metric figures should render all metrics present after config/load filters."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e1", "e2", "e1", "e2"],
            "station": ["STA", "STB", "STA", "STB", "STA", "STB"],
            "sta_lon": [-118.0, -117.9, -118.0, -117.9, -118.0, -117.9],
            "sta_lat": [34.0, 34.1, 34.0, 34.1, 34.0, 34.1],
            "metric": ["PGA", "PGA", "RotD50 response", "RotD50 response", "FAS", "FAS"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec", "1-2 sec", "", ""],
            "model": ["m1"] * 6,
            "component": ["Z", "R", "Z", "R", "Z", "R"],
            "period_s": [np.nan, np.nan, np.nan, np.nan, 1.0, 2.0],
            "distance_km": [10.0, 20.0, 11.0, 21.0, 12.0, 22.0],
            "log2_residual": [0.2, -0.1, 0.4, -0.3, 0.1, 0.2],
        }
    )
    context = MetricFigureContext.from_frame(
        metrics,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=0,
        value_col="log2_residual",
    )
    calls: list[dict[str, object]] = []

    def _record_metric(base, item, func, df=None, source_df=None, required=(), **kwargs):
        calls.append({"writer": "metric", "base": base, "key": item["key"], "rows": len(item["df"])})
        return tmp_path / f"{base}_{item['key']}.png"

    def _record_sheet(base, item, func, df_factory=None, source_df_factory=None, required=(), **kwargs):
        calls.append({"writer": "sheet", "base": base, "key": item["key"], "rows": len(item["df"])})
        return tmp_path / f"{base}_{item['key']}_sheet.png"

    context.write_metric_plot = _record_metric  # type: ignore[method-assign]
    context.write_psa_period_sheet = _record_sheet  # type: ignore[method-assign]

    status = context.metric_selection_status_frame(components=["Z", "R"], model="m1").set_index("metric_key")
    assert {"pga", "rotd50_response", "fas"} <= set(status.index)
    assert status.loc["rotd50_response", "selected_row_count"] == 2
    assert status.loc["fas", "selected_row_count"] == 2

    outputs = context.write_residuals_vs_distance_plots(
        lambda _df, *, output_path, **_kwargs: Path(output_path).write_text("plot", encoding="utf-8"),
        passband="1-2 sec",
        components=["Z", "R"],
        model="m1",
    )

    assert outputs
    assert {"pga", "rotd50_response", "fas"} <= {str(call["key"]) for call in calls}
    assert any(call["writer"] == "sheet" and call["key"] == "fas" for call in calls)


def test_metric_figure_context_writes_single_named_station_map_with_source_sidecar(tmp_path) -> None:
    """Focused tutorial maps should use package aggregation and source-row sidecars."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3"],
            "station": ["STA", "STA", "STB"],
            "sta_lon": [-118.0, -118.1, -117.9],
            "sta_lat": [34.0, 34.1, 34.2],
            "metric": ["PGA", "PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec"],
            "model": ["m1", "m1", "m1"],
            "component": ["Z", "Z", "Z"],
            "log2_residual": [1.0, 3.0, 5.0],
        }
    )
    context = MetricFigureContext.from_frame(
        metrics,
        tmp_path / "figures",
        make_figures=True,
        overwrite=True,
        sample_rows=0,
        value_col="log2_residual",
        write_sidecars=True,
        sidecar_rows=None,
        station_aggregation="mean",
    )

    def _dummy_station_map(df: pd.DataFrame, *, output_path: Path, **_kwargs) -> None:
        assert "source_row_count" in df.columns
        Path(output_path).write_text("figure", encoding="utf-8")

    output = context.write_station_metric_map_for_metric(
        _dummy_station_map,
        _dummy_station_map,
        metric="PGA",
        passband="1-2 sec",
        components=["Z"],
        model="m1",
        value_col="log2_residual",
    )

    assert output is not None
    assert output.exists()
    sidecar = context.sidecar_output_dir / f"{output.stem}.csv"
    source_sidecar = context.sidecar_output_dir / f"{output.stem}.source.csv"
    metadata = json.loads(sidecar.with_suffix(".json").read_text(encoding="utf-8"))
    assert sidecar.exists()
    assert source_sidecar.exists()
    assert metadata["plot_rows_role"] == "post_aggregation_station_summary"
    assert metadata["source_row_count"] == 3
    assert pd.read_csv(source_sidecar)["event_id"].tolist() == ["e1", "e2", "e3"]


def test_station_metric_map_notebook_helper_writes_preview_and_sidecar(tmp_path, monkeypatch) -> None:
    """Notebook wrapper should own context setup for one station metric map."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3"],
            "station": ["STA", "STA", "STB"],
            "sta_lon": [-118.0, -118.1, -117.9],
            "sta_lat": [34.0, 34.1, 34.2],
            "metric": ["PGA", "PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec"],
            "model": ["m1", "m1", "m1"],
            "component": ["Z", "Z", "Z"],
            "log2_residual": [1.0, 3.0, 5.0],
        }
    )

    class Settings:
        figure_dir = tmp_path / "figures"
        passband = "1-2 sec"
        components = ["Z"]
        model = "m1"
        add_basemap = False
        showfig = False

        def context_kwargs(self, *, include_station_aggregation: bool = False) -> dict[str, object]:
            kwargs: dict[str, object] = {
                "sample_rows": 0,
                "default_passband": self.passband,
                "default_components": self.components,
                "default_showfig": self.showfig,
                "default_model": self.model,
                "add_basemap": self.add_basemap,
                "robust_axis_percentile": 95.0,
                "write_sidecars": True,
                "sidecar_rows": None,
                "sidecar_dir": self.figure_dir / "sidecars",
            }
            if include_station_aggregation:
                kwargs["station_aggregation"] = "mean"
            return kwargs

    def _dummy_station_map(df: pd.DataFrame, *, output_path: Path, **_kwargs) -> None:
        assert "source_row_count" in df.columns
        Path(output_path).write_text("figure", encoding="utf-8")

    import spatial_vtk.spatial.map as map_public
    import spatial_vtk.spatial.map.metrics as map_metrics

    monkeypatch.setattr(map_metrics, "plot_station_metric_map", _dummy_station_map)
    monkeypatch.setattr(map_metrics, "plot_station_metric_map_by_period", _dummy_station_map)
    monkeypatch.setattr(map_public, "plot_station_metric_map", _dummy_station_map, raising=False)
    monkeypatch.setattr(map_public, "plot_station_metric_map_by_period", _dummy_station_map, raising=False)

    result = write_station_metric_map_from_notebook_settings(
        metrics,
        Settings(),
        metric="PGA",
        value_col="log2_residual",
        title="Mean Station PGA Log2 Residual",
        preview_rows=1,
    )

    assert result.output_path is not None
    assert result.output_path.exists()
    assert result.preview["station"].tolist() == ["STA"]
    status = result.status_frame().set_index("name")
    assert {"artifact_label", "artifact_role", "status", "exists", "resolved_path", "path", "value"} <= set(
        status.columns
    )
    assert status.loc["resolved_path", "artifact_role"] == "figure"
    assert status.loc["resolved_path", "status"] == "ready"
    assert bool(status.loc["resolved_path", "exists"]) is True
    assert status.loc["resolved_path", "value"] == str(result.output_path)
    assert status.loc["output_path", "value"] == status.loc["resolved_path", "value"]
    assert bool(status.loc["ready", "value"]) is True
    assert status.loc["preview_rows", "value"] == 1
    assert status.loc["station_aggregation", "value"] == "mean"
    source_sidecar = result.context.sidecar_output_dir / f"{result.output_path.stem}.source.csv"
    metadata = json.loads((result.context.sidecar_output_dir / f"{result.output_path.stem}.json").read_text(encoding="utf-8"))
    assert source_sidecar.exists()
    assert metadata["aggregation_contract"] == "station_event_rows_to_station_summary"
    assert metadata["source_row_count"] == 3
    assert status.loc["aggregation_contract", "value"] == "station_event_rows_to_station_summary"
    assert status.loc["plot_rows_role", "value"] == "post_aggregation_station_summary"
    assert status.loc["source_rows_role", "value"] == "pre_aggregation_metric_rows"
    assert status.loc["source_rows_filter", "value"] == "aggregation_groups_present_in_plot_rows"
    assert status.loc["aggregation_group_columns", "value"] == ["station"]
    assert status.loc["aggregation_coordinate_columns", "value"] == ["sta_lon", "sta_lat"]
    assert status.loc["aggregation_collapsed_columns", "value"] == ["metric", "band", "model", "component"]
    assert status.loc["aggregation_collapsed_unique_counts", "value"] == {
        "metric": 1,
        "band": 1,
        "model": 1,
        "component": 1,
    }
    assert status.loc["aggregation_input_row_count", "value"] == 3
    assert status.loc["aggregation_finite_row_count", "value"] == 3
    assert status.loc["aggregation_input_station_count", "value"] == 1
    assert status.loc["aggregation_finite_station_count", "value"] == 1
    assert status.loc["aggregation_input_event_count", "value"] == 3
    assert status.loc["aggregation_finite_event_count", "value"] == 3
    assert status.loc["source_row_count", "value"] == 3
    assert status.loc["source_sidecar_written", "value"] is True


def test_metric_figure_context_orchestrates_large_run_plot_families(tmp_path) -> None:
    """Large-run metric plot families should be package helpers, not notebook loops."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e1", "e2"],
            "station": ["STA", "STB", "STA", "STB"],
            "sta_lon": [-118.0, -117.9, -118.0, -117.9],
            "sta_lat": [34.0, 34.1, 34.0, 34.1],
            "metric": ["PGA", "PGA", "PSA", "PSA"],
            "band": ["1-2 sec", "1-2 sec", "", ""],
            "model": ["m1", "m1", "m1", "m1"],
            "component": ["Z", "R", "Z", "R"],
            "period_s": [np.nan, np.nan, 1.0, 2.0],
            "distance_km": [10.0, 20.0, 10.0, 20.0],
            "depth_km": [5.0, 6.0, 5.0, 6.0],
            "vs30": [400.0, 500.0, 400.0, 500.0],
            "log2_residual": [0.2, -0.1, 0.1, 0.2],
        }
    )
    context = MetricFigureContext.from_frame(
        metrics,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=0,
        value_col="log2_residual",
    )
    calls: list[dict[str, object]] = []

    def _dummy_plot(_df: pd.DataFrame, *, output_path, **_kwargs) -> None:
        Path(output_path).write_text("plot", encoding="utf-8")

    def _record_metric(base, item, func, df=None, source_df=None, required=(), **kwargs):
        calls.append(
            {
                "writer": "metric",
                "base": base,
                "key": item["key"],
                "rows": None if df is None else len(df),
                "source_rows": None if source_df is None else len(source_df),
                "required": tuple(required),
                "kwargs": dict(kwargs),
            }
        )
        return tmp_path / f"{base}_{item['key']}.png"

    def _record_sheet(base, item, func, df_factory=None, source_df_factory=None, required=(), **kwargs):
        plot_df = df_factory(item) if df_factory is not None else item["df"]
        source_df = source_df_factory(item) if source_df_factory is not None else None
        calls.append(
            {
                "writer": "sheet",
                "base": base,
                "key": item["key"],
                "rows": len(plot_df),
                "source_rows": None if source_df is None else len(source_df),
                "required": tuple(required),
                "source_factory": source_df_factory,
                "kwargs": dict(kwargs),
            }
        )
        return tmp_path / f"{base}_{item['key']}_sheet.png"

    context.write_metric_plot = _record_metric  # type: ignore[method-assign]
    context.write_psa_period_sheet = _record_sheet  # type: ignore[method-assign]

    outputs = []
    outputs.extend(context.write_residuals_vs_distance_plots(_dummy_plot, passband="1-2 sec", components=["Z", "R"]))
    outputs.extend(context.write_residuals_vs_depth_plots(_dummy_plot, passband="1-2 sec", components=["Z", "R"]))
    outputs.extend(context.write_vs30_scatter_plots(_dummy_plot, passband="1-2 sec", components=["Z", "R"]))
    outputs.extend(context.write_station_metric_maps(_dummy_plot, _dummy_plot, passband="1-2 sec", components=["Z", "R"]))
    outputs.extend(context.write_residual_grid_maps(_dummy_plot, passband="1-2 sec", components=["Z", "R"]))
    outputs.extend(context.write_metric_by_model_maps(_dummy_plot, passband="1-2 sec", components=["Z", "R"]))
    outputs.extend(context.write_event_residual_maps(_dummy_plot, passband="1-2 sec", components=["Z", "R"]))
    outputs.extend(context.write_log2_residual_distribution_plots(_dummy_plot, _dummy_plot, components=["Z", "R"]))
    outputs.extend(context.write_psa_period_curve_plots(_dummy_plot, passband="1-2 sec", components=["Z", "R"]))

    assert outputs
    bases = {str(call["base"]) for call in calls}
    assert {
        "residuals_vs_distance",
        "residuals_vs_depth",
        "vs30_scatter",
        "station_metric_map",
        "residual_grid",
        "metric_by_model_map",
        "event_residual_map",
        "band_log2_residual_distribution",
        "period_log2_residual_distribution",
        "psa_period_curve",
    }.issubset(bases)
    station_calls = [call for call in calls if call["base"] == "station_metric_map"]
    assert any(call["key"] == "pga" and call["source_rows"] == 2 for call in station_calls)
    assert any(call["key"] == "psa" and call["source_rows"] == 2 for call in station_calls)
    sheet_calls = [call for call in calls if call["writer"] == "sheet"]
    item_source_func = context.item_source_rows.__func__
    assert any(
        call["base"] == "residual_grid"
        and getattr(call["source_factory"], "__self__", None) is context
        and getattr(call["source_factory"], "__func__", None) is item_source_func
        for call in sheet_calls
    )
    residual_grid_calls = [call for call in calls if call["base"] == "residual_grid"]
    assert residual_grid_calls
    assert all(call["kwargs"].get("basemap_kwargs") == {"cache_download": False} for call in residual_grid_calls)
    assert any(
        call["base"] == "metric_by_model_map"
        and getattr(call["source_factory"], "__self__", None) is context
        and getattr(call["source_factory"], "__func__", None) is item_source_func
        for call in sheet_calls
    )
    assert any("log2_residual" in call["required"] for call in calls)


def test_metric_figure_context_skips_vs30_when_no_finite_pairs(tmp_path) -> None:
    """Vs30 figures should be omitted when no finite Vs30/value pairs exist."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "station": ["STA", "STB"],
            "metric": ["PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec"],
            "model": ["m1", "m1"],
            "component": ["Z", "R"],
            "distance_km": [10.0, 20.0],
            "vs30": [np.nan, np.nan],
            "log2_residual": [0.2, -0.1],
        }
    )
    context = MetricFigureContext.from_frame(
        metrics,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=0,
        value_col="log2_residual",
    )

    def _unexpected_writer(*_args: object, **_kwargs: object) -> Path:
        raise AssertionError("Vs30 writer should not be called without finite Vs30/value pairs")

    context.write_metric_plot = _unexpected_writer  # type: ignore[method-assign]
    outputs = context.write_vs30_scatter_plots(
        _unexpected_writer,
        passband="1-2 sec",
        components=["Z", "R"],
    )

    assert outputs == []
    assert not list((tmp_path / "figures").glob("vs30_scatter*.png"))


def test_metric_figure_context_uses_pair_metric_values_for_trend_figures(tmp_path) -> None:
    """Pair-only metrics should not be plotted as log2 residuals."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3"],
            "station": ["STA", "STB", "STC"],
            "metric": ["PGA", "original_cc", "traveltime_delay"],
            "metric_group": ["amplitude", "cross_correlation", "delay"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec"],
            "model": ["m1", "m1", "m1"],
            "component": ["Z", "Z", "Z"],
            "distance_km": [10.0, 20.0, 30.0],
            "dominant_period_s": [np.nan, np.nan, 2.0],
            "log2_residual": [0.25, np.nan, np.nan],
            "value": [np.nan, 0.82, 0.5],
        }
    )
    context = MetricFigureContext.from_frame(
        metrics,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=0,
        value_col="log2_residual",
    )
    calls: list[dict[str, object]] = []

    def _record_metric(base, item, func, df=None, source_df=None, required=(), **kwargs):
        calls.append(
            {
                "key": item["key"],
                "y_col": kwargs.get("y_col"),
                "value_col": kwargs.get("value_col"),
                "required": tuple(required),
                "df": item["df"].copy(),
            }
        )
        return tmp_path / f"{base}_{item['key']}.png"

    context.write_metric_plot = _record_metric  # type: ignore[method-assign]

    outputs = context.write_residuals_vs_distance_plots(
        lambda _df, *, output_path, **_kwargs: Path(output_path).write_text("plot", encoding="utf-8"),
        passband="1-2 sec",
        components=["Z"],
        model="m1",
    )

    assert outputs
    by_key = {str(call["key"]): call for call in calls}
    assert by_key["pga"]["y_col"] == "log2_residual"
    assert by_key["original_cc"]["y_col"] == "value"
    assert by_key["traveltime_delay"]["y_col"] == "delay_fraction_dominant_period"
    delay_df = by_key["traveltime_delay"]["df"]
    assert delay_df["delay_fraction_dominant_period"].iloc[0] == pytest.approx(0.25)


def test_metric_figure_context_skips_trend_figures_without_finite_xy(tmp_path) -> None:
    """Trend figures should be omitted instead of writing empty placeholder PNGs."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "station": ["STA", "STB"],
            "metric": ["PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec"],
            "model": ["m1", "m1"],
            "component": ["Z", "R"],
            "distance_km": [np.nan, np.nan],
            "log2_residual": [0.2, -0.1],
        }
    )
    context = MetricFigureContext.from_frame(
        metrics,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=0,
        value_col="log2_residual",
    )

    def _unexpected_plot(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Plot function should not be called without finite x/y data")

    outputs = context.write_residuals_vs_distance_plots(
        _unexpected_plot,
        passband="1-2 sec",
        components=["Z", "R"],
        model="m1",
    )

    assert outputs == []
    assert not list((tmp_path / "figures").glob("residuals_vs_distance*.png"))


def test_write_large_run_metric_figure_suite_from_notebook_settings_delegates(tmp_path, monkeypatch) -> None:
    """Full Step 3 figure suite helper should keep plotting orchestration out of notebooks."""

    import spatial_vtk.metrics.plot.large_run as large_run_module

    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    class Settings:
        figure_dir = tmp_path / "figures"
        make_figures = True
        value_col = "log2_residual"
        compare_to = "reference"
        comparison_table = True

        def context_kwargs(self, *, include_station_aggregation: bool = False) -> dict[str, object]:
            assert include_station_aggregation is True
            return {
                "make_figures": True,
                "default_passband": "1-2 sec",
                "default_components": ["Z"],
                "default_model": "m1",
                "station_aggregation": "mean",
            }

        def plot_selection_kwargs(self, **kwargs: object) -> dict[str, object]:
            out: dict[str, object] = {
                "passband": "1-2 sec",
                "components": ["Z"],
                "model": "m1",
                "showfig": False,
            }
            if kwargs.pop("include_basemap", False):
                out["add_basemap"] = True
            if kwargs.pop("include_robust_axis_percentile", False):
                out["robust_axis_percentile"] = 95.0
            out.update(kwargs)
            return out

    class ScoreSettings:
        make_figures = True
        showfig = False
        score_columns = ["anderson_2004_gof"]

    class FakeContext:
        ready = True

        def _record(self, name: str, *args: object, **kwargs: object) -> list[Path]:
            calls.append((name, args, kwargs))
            return [tmp_path / "figures" / f"{name}.png"]

        def write_residuals_vs_distance_plots(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("residuals_vs_distance", *args, **kwargs)

        def write_score_trend_plots(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("score_trends", *args, **kwargs)

        def write_residuals_vs_depth_plots(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("residuals_vs_depth", *args, **kwargs)

        def write_vs30_scatter_plots(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("vs30_scatter", *args, **kwargs)

        def write_station_metric_maps(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("station_metric_maps", *args, **kwargs)

        def write_residual_grid_maps(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("residual_grid_maps", *args, **kwargs)

        def write_metric_by_model_maps(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("metric_by_model_maps", *args, **kwargs)

        def write_event_residual_maps(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("event_residual_maps", *args, **kwargs)

        def write_log2_residual_distribution_plots(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("log2_residual_distributions", *args, **kwargs)

        def write_psa_period_curve_plots(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("psa_period_curves", *args, **kwargs)

        def write_standard_metric_diagnostic_plots(self, *args: object, **kwargs: object) -> list[Path]:
            return self._record("standard_metric_diagnostics", *args, **kwargs)

    fake_context = FakeContext()
    prepare_kwargs: dict[str, object] = {}

    def _fake_prepare_metric_context(*args: object, **kwargs: object) -> FakeContext:
        prepare_kwargs.update(kwargs)
        return fake_context

    monkeypatch.setattr(
        large_run_module,
        "prepare_large_run_metric_figure_context",
        _fake_prepare_metric_context,
    )

    def _dummy_plot(*_args: object, **_kwargs: object) -> None:
        return None

    result = write_large_run_metric_figure_suite_from_notebook_settings(
        tmp_path / "metrics_long.parquet",
        Settings(),
        overwrite=True,
        score_settings=ScoreSettings(),
        residuals_vs_distance_func=_dummy_plot,
        score_trend_func=_dummy_plot,
        residuals_vs_depth_func=_dummy_plot,
        vs30_scatter_func=_dummy_plot,
        station_metric_map_func=_dummy_plot,
        station_metric_map_by_period_func=_dummy_plot,
        residual_grid_func=_dummy_plot,
        metric_by_model_map_func=_dummy_plot,
        event_residual_map_func=_dummy_plot,
        band_score_distribution_func=_dummy_plot,
        period_score_distribution_func=_dummy_plot,
        psa_period_curve_func=_dummy_plot,
        scatterplot_func=_dummy_plot,
        boxplot_func=_dummy_plot,
        heatmap_func=_dummy_plot,
    )

    expected = [
        "residuals_vs_distance",
        "score_trends",
        "residuals_vs_depth",
        "vs30_scatter",
        "station_metric_maps",
        "residual_grid_maps",
        "metric_by_model_maps",
        "event_residual_maps",
        "log2_residual_distributions",
        "psa_period_curves",
        "standard_metric_diagnostics",
    ]
    assert result.context is fake_context
    assert prepare_kwargs["verbose"] is False
    assert prepare_kwargs["station_aggregation"] == "mean"
    assert [call[0] for call in calls] == expected
    assert calls[0][2]["value_col"] == "log2_residual"
    assert calls[0][2]["robust_axis_percentile"] == 95.0
    assert calls[1][2]["score_columns"] == ["anderson_2004_gof"]
    assert calls[6][2]["model"] is None
    assert calls[8][2]["passband"] is None
    assert calls[10][2]["compare_to"] == "reference"
    assert calls[10][2]["table"] is True
    status = result.status_frame()
    assert {"name", "artifact_label", "resolved_path", "path", "exists"} <= set(status.columns)
    assert status["artifact"].tolist() == expected
    assert status["status"].tolist() == ["written"] * len(expected)
    assert status["status_reason"].tolist() == ["written"] * len(expected)
    assert status["figure_count"].tolist() == [1] * len(expected)
    assert status["existing_figure_count"].tolist() == [0] * len(expected)
    assert status["figure_paths"].tolist() == [[str(tmp_path / "figures" / f"{name}.png")] for name in expected]
    assert status["first_figure_path"].tolist() == [str(tmp_path / "figures" / f"{name}.png") for name in expected]
    assert status["path"].tolist() == status["first_figure_path"].tolist()
    assert status["exists"].tolist() == [False] * len(expected)


def test_large_run_metric_figures_enable_comparison_tables_by_default(tmp_path, monkeypatch) -> None:
    """The action-oriented Step 3 helper should restore component comparison tables."""

    import spatial_vtk.config as config_module
    import spatial_vtk.large_run as large_run_module
    import spatial_vtk.metrics as metrics_module
    from spatial_vtk.config import NotebookFigureSettings

    seen: dict[str, object] = {}
    settings_kwargs: dict[str, object] = {}

    class Outputs:
        def write_large_run_figure_suite(self, settings, *, overwrite: bool = False):  # noqa: ANN001, ANN202
            seen["settings"] = settings
            seen["overwrite"] = overwrite
            return {"status": "wrote"}

    def fake_figure_settings(*args: object, **kwargs: object) -> NotebookFigureSettings:
        settings_kwargs.update(kwargs)
        return NotebookFigureSettings(
            figure_dir=tmp_path / "figures" / "step_03_metrics" / "default",
            make_figures=True,
            add_basemap=bool(kwargs.get("default_add_basemap", False)),
        )

    monkeypatch.setattr(config_module, "notebook_figure_settings", fake_figure_settings)
    monkeypatch.setattr(metrics_module, "load_standard_metric_workflow_outputs", lambda *, cfg=None: Outputs())

    session = large_run_module.LargeRunSession(
        context=object(),
        cfg=object(),
        overwrite=True,
        submit_slurm=False,
        run_local=False,
        make_figures=True,
        preview_rows=5,
        qc_chunksize=100,
        dashboard_chunksize=100,
        metric_batch_count=1,
        preprocess_continue_on_error=False,
    )

    result = large_run_module.make_metric_figures(session)

    assert result.action == "Metric figures"
    settings = seen["settings"]
    assert settings.compare_to == "Z"
    assert settings.comparison_table is True
    assert settings.add_basemap is True
    assert settings_kwargs["default_add_basemap"] is True
    assert seen["overwrite"] is True


def test_large_run_filtered_metric_figures_translate_filters_and_folders(tmp_path, monkeypatch) -> None:
    """Filtered metric figure sets should write sibling folders with context load filters."""

    import spatial_vtk.config as config_module
    import spatial_vtk.large_run as large_run_module
    import spatial_vtk.metrics as metrics_module
    from spatial_vtk.config import NotebookFigureSettings

    settings_seen: list[object] = []
    settings_kwargs: dict[str, object] = {}

    class Outputs:
        def write_large_run_figure_suite(self, settings, *, overwrite: bool = False):  # noqa: ANN001, ANN202
            settings_seen.append(settings)
            return {"status": "wrote", "message": str(settings.figure_dir)}

    def fake_figure_settings(*args: object, **kwargs: object) -> NotebookFigureSettings:
        settings_kwargs.update(kwargs)
        return NotebookFigureSettings(
            figure_dir=tmp_path / "figures" / "step_03_metrics" / "default",
            make_figures=True,
            add_basemap=bool(kwargs.get("default_add_basemap", False)),
        )

    monkeypatch.setattr(config_module, "notebook_figure_settings", fake_figure_settings)
    monkeypatch.setattr(metrics_module, "load_standard_metric_workflow_outputs", lambda *, cfg=None: Outputs())

    session = large_run_module.LargeRunSession(
        context=object(),
        cfg=object(),
        overwrite=False,
        submit_slurm=False,
        run_local=False,
        make_figures=True,
        preview_rows=5,
        qc_chunksize=100,
        dashboard_chunksize=100,
        metric_batch_count=1,
        preprocess_continue_on_error=False,
    )

    result = large_run_module.make_filtered_metric_figures(
        session,
        [
            {"name": "1-2s_broadband_only", "passband": "1-2 sec", "station_family": "Broadband"},
            {"passband": "2-3 sec", "components": ["Z"], "compare_to": None},
        ],
    )

    assert result.action == "Filtered metric figures"
    assert settings_kwargs["default_add_basemap"] is True
    assert len(settings_seen) == 2
    assert settings_seen[0].figure_dir == tmp_path / "figures" / "step_03_metrics" / "metrics_figures_1-2s_broadband_only"
    assert settings_seen[0].context_kwargs(include_station_aggregation=True)["load_filters"] == {
        "band": "1-2 sec",
        "station_family": "broadband",
    }
    assert settings_seen[0].compare_to == "Z"
    assert settings_seen[0].comparison_table is True
    assert settings_seen[0].add_basemap is True
    assert settings_seen[1].figure_dir == tmp_path / "figures" / "step_03_metrics" / "metrics_figures_2-3s_component_Z"
    assert settings_seen[1].context_kwargs()["load_filters"] == {"band": "2-3 sec", "component": ["Z"]}
    assert settings_seen[1].compare_to is None
    assert settings_seen[1].comparison_table is False


def test_large_run_filtered_spatial_figures_translate_filters_and_folders(tmp_path, monkeypatch) -> None:
    """Filtered spatial figure sets should write Step 4 sibling folders with load filters."""

    import spatial_vtk.config as config_module
    import spatial_vtk.large_run as large_run_module
    import spatial_vtk.spatial as spatial_module
    from spatial_vtk.config import NotebookFigureSettings

    settings_seen: list[object] = []

    class Outputs:
        def write_figure_suite(self, settings, *, overwrite: bool = False):  # noqa: ANN001, ANN202
            settings_seen.append(settings)
            return {"status": "wrote", "message": str(settings.figure_dir), "overwrite": overwrite}

    def fake_figure_settings(*args: object, **kwargs: object) -> NotebookFigureSettings:
        return NotebookFigureSettings(
            figure_dir=tmp_path / "figures" / "step_04_spatial" / "default",
            make_figures=True,
            add_basemap=bool(kwargs.get("default_add_basemap", False)),
        )

    monkeypatch.setattr(config_module, "notebook_figure_settings", fake_figure_settings)
    monkeypatch.setattr(spatial_module, "load_standard_spatial_workflow_output_status", lambda *, cfg=None: Outputs())

    session = large_run_module.LargeRunSession(
        context=object(),
        cfg=object(),
        overwrite=True,
        submit_slurm=False,
        run_local=False,
        make_figures=True,
        preview_rows=5,
        qc_chunksize=100,
        dashboard_chunksize=100,
        metric_batch_count=1,
        preprocess_continue_on_error=False,
    )

    result = large_run_module.make_filtered_spatial_figures(
        session,
        [{"passband": "1-2 sec", "components": ["Z"], "station_family": "Broadband"}],
    )

    assert result.action == "Filtered spatial figures"
    assert len(settings_seen) == 1
    assert settings_seen[0].figure_dir == (
        tmp_path / "figures" / "step_04_spatial" / "spatial_figures_1-2s_component_Z_broadband_only"
    )
    assert settings_seen[0].context_kwargs(include_station_aggregation=True)["load_filters"] == {
        "band": "1-2 sec",
        "component": ["Z"],
        "station_family": "broadband",
    }
    assert settings_seen[0].add_basemap is True


def test_large_run_filtered_region_figures_translate_selection_and_corridor_filters(tmp_path, monkeypatch) -> None:
    """Filtered Step 5 figure sets should keep region and corridor options in one settings object."""

    import spatial_vtk.config as config_module
    import spatial_vtk.large_run as large_run_module
    import spatial_vtk.spatial as spatial_module
    from spatial_vtk.config import NotebookFigureSettings

    settings_seen: list[object] = []
    geojson_seen: list[object] = []

    class Outputs:
        def write_region_figures(  # noqa: ANN202
            self,
            settings,  # noqa: ANN001
            *,
            geojson_path=None,  # noqa: ANN001
            overwrite: bool = False,
        ):
            settings_seen.append(settings)
            geojson_seen.append(geojson_path)
            return {"status": "wrote", "message": str(settings.figure_dir), "overwrite": overwrite}

    def fake_figure_settings(*args: object, **kwargs: object) -> NotebookFigureSettings:
        return NotebookFigureSettings(
            figure_dir=tmp_path / "figures" / "step_05_regions" / "default",
            make_figures=True,
            add_basemap=bool(kwargs.get("default_add_basemap", False)),
            metric=str(kwargs.get("default_metric", "PGA")),
            passband=str(kwargs.get("default_passband", "2-3 sec")),
        )

    monkeypatch.setattr(config_module, "notebook_figure_settings", fake_figure_settings)
    monkeypatch.setattr(spatial_module, "load_standard_geojson_workflow_output_status", lambda *, cfg=None: Outputs())

    session = large_run_module.LargeRunSession(
        context=object(),
        cfg=object(),
        overwrite=False,
        submit_slurm=False,
        run_local=False,
        make_figures=True,
        preview_rows=5,
        qc_chunksize=100,
        dashboard_chunksize=100,
        metric_batch_count=1,
        preprocess_continue_on_error=False,
    )

    result = large_run_module.make_filtered_region_corridor_figures(
        session,
        [
            {
                "metric": "CAV",
                "passband": "3-5 sec",
                "components": ["R", "T"],
                "compare_to": None,
                "geojson_path": "/tmp/regions.geojson",
                "corridor_filters": {"selector": "LA Basin"},
            }
        ],
    )

    assert result.action == "Filtered region and corridor figures"
    assert len(settings_seen) == 1
    assert settings_seen[0].figure_dir == (
        tmp_path
        / "figures"
        / "step_05_regions"
        / "region_figures_metric_CAV_3-5s_components_R-T_custom_geojson_corridors_filtered"
    )
    assert settings_seen[0].metric == "CAV"
    assert settings_seen[0].passband == "3-5 sec"
    assert settings_seen[0].component == ["R", "T"]
    assert settings_seen[0].compare_to is None
    assert settings_seen[0].corridor_filters == {"selector": "LA Basin"}
    assert settings_seen[0].add_basemap is True
    assert geojson_seen == ["/tmp/regions.geojson"]


def test_large_run_additional_diagnostics_annotates_region_boxplot(tmp_path, monkeypatch) -> None:
    """Step 6 should add configured GeoJSON labels before writing the region boxplot."""

    import spatial_vtk.config as config_module
    import spatial_vtk.io as io_module
    import spatial_vtk.large_run as large_run_module
    import spatial_vtk.spatial as spatial_module
    from spatial_vtk.config import NotebookFigureSettings

    calls: dict[str, object] = {}
    region_geojson = tmp_path / "regions.geojson"

    class Outputs:
        def write_waveform_comparison(self, settings, **kwargs):  # noqa: ANN001, ANN202
            calls["waveform_kwargs"] = kwargs
            return {"status": "written"}

        def write_region_boxplot(self, settings, **kwargs):  # noqa: ANN001, ANN202
            calls["region_settings"] = settings
            calls["region_kwargs"] = kwargs
            return {"status": "written"}

    def fake_figure_settings(kind: str, *args: object, **kwargs: object) -> NotebookFigureSettings:
        return NotebookFigureSettings(
            figure_dir=tmp_path / "figures" / str(kind),
            make_figures=True,
            metric=str(kwargs.get("default_metric", "PGA")),
            passband=str(kwargs.get("default_passband", "2-3 sec")),
        )

    monkeypatch.setattr(config_module, "notebook_figure_settings", fake_figure_settings)
    monkeypatch.setattr(spatial_module, "load_standard_additional_plotting_output_status", lambda *, cfg=None: Outputs())
    monkeypatch.setattr(
        io_module,
        "load_configured_input_paths",
        lambda mapping, *, cfg=None: {"region_geojson": region_geojson},
    )

    session = large_run_module.LargeRunSession(
        context=object(),
        cfg=object(),
        overwrite=True,
        submit_slurm=False,
        run_local=False,
        make_figures=True,
        preview_rows=5,
        qc_chunksize=100,
        dashboard_chunksize=100,
        metric_batch_count=1,
        preprocess_continue_on_error=False,
    )

    result = large_run_module.make_additional_diagnostic_figures(session)

    assert result.action == "Additional diagnostics"
    assert calls["waveform_kwargs"]["fallback_to_available"] is True
    assert calls["waveform_kwargs"]["max_distance_km"] is None
    assert calls["region_kwargs"]["geojson_path"] == region_geojson
    assert calls["region_kwargs"]["annotate_if_missing"] is True
    assert calls["region_kwargs"]["overwrite"] is True


def test_metric_figure_suite_result_displays_context_status_frames() -> None:
    """Figure-suite results should own context readiness display branches."""

    class FakeContext:
        ready = False

        def status_frame(self) -> pd.DataFrame:
            return pd.DataFrame([{"frame": "status"}])

        def metric_selection_status_frame(self) -> pd.DataFrame:
            return pd.DataFrame([{"frame": "selection"}])

        def spectral_metric_contract_status(self) -> pd.DataFrame:
            return pd.DataFrame([{"frame": "spectral"}])

        def dimension_summary_frame(self) -> pd.DataFrame:
            raise AssertionError("dimension summary should not be read when context is not ready")

    result = MetricFigureSuiteResult(context=FakeContext(), rows=())
    displayed: list[pd.DataFrame] = []
    frames = result.display_context_status(display=displayed.append)

    assert list(frames) == ["context_status", "metric_selection", "spectral_metric_contract"]
    assert [frame["frame"].iloc[0] for frame in displayed] == ["status", "selection", "spectral"]

    class ReadyContext(FakeContext):
        ready = True

        def dimension_summary_frame(self) -> pd.DataFrame:
            return pd.DataFrame([{"frame": "dimension"}])

    ready_result = MetricFigureSuiteResult(context=ReadyContext(), rows=())
    ready_frames = ready_result.context_status_frames()
    assert list(ready_frames) == ["context_status", "metric_selection", "spectral_metric_contract", "dimension_summary"]


def test_metric_figure_suite_status_reports_skip_reasons() -> None:
    """Figure-suite status rows should expose structured skip reasons."""

    class FakeContext:
        write_sidecars = False
        sidecar_output_dir = None

    result = MetricFigureSuiteResult(
        context=FakeContext(),
        rows=(
            {
                "artifact": "score_trends",
                "status": "skipped",
                "status_reason": "disabled",
                "figure_count": 0,
                "existing_figure_count": 0,
                "figure_paths": [],
                "message": "Set SVTK_MAKE_SCORE_TRENDS=1 to render optional GOF score trends.",
            },
        ),
    )

    status = result.status_frame().set_index("artifact")
    assert status.loc["score_trends", "status"] == "skipped"
    assert status.loc["score_trends", "status_reason"] == "disabled"
    assert "SVTK_MAKE_SCORE_TRENDS" in status.loc["score_trends", "message"]


def test_metric_figure_context_not_ready_without_finite_values(tmp_path) -> None:
    """Metric figure readiness should distinguish present but unusable values."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "station": ["STA", "STB"],
            "metric": ["PGA", "PGV"],
            "band": ["1-2 sec", "1-2 sec"],
            "component": ["Z", "Z"],
            "model": ["m1", "m1"],
            "log2_residual": [np.nan, np.inf],
        }
    )

    context = MetricFigureContext.from_frame(
        metrics,
        tmp_path / "figures",
        make_figures=True,
        value_col="log2_residual",
    )

    assert context.ready is False
    status = context.status_frame().set_index("name")["value"]
    assert bool(status.loc["value_col_present"]) is True
    assert status.loc["selected_metric_rows"] == 2
    assert status.loc["finite_value_rows"] == 0
    assert status.loc["nonfinite_value_rows"] == 2


def test_metric_figure_suite_status_summarizes_sidecar_provenance(tmp_path) -> None:
    """Suite status should report sidecar coverage without reading large CSVs."""

    figure_dir = tmp_path / "figures"
    sidecar_dir = tmp_path / "sidecars"
    figure_dir.mkdir()
    sidecar_dir.mkdir()
    figure_a = figure_dir / "station_metric_map__pga.png"
    figure_b = figure_dir / "station_metric_map__pgv.png"
    figure_a.write_text("png-a", encoding="utf-8")
    figure_b.write_text("png-b", encoding="utf-8")
    (sidecar_dir / "station_metric_map__pga.csv").write_text("too,large,to,read\n", encoding="utf-8")
    (sidecar_dir / "station_metric_map__pgv.csv").write_text("too,large,to,read\n", encoding="utf-8")
    (sidecar_dir / "station_metric_map__pga.source.csv").write_text("too,large,to,read\n", encoding="utf-8")
    (sidecar_dir / "station_metric_map__pga.json").write_text(
        json.dumps(
            {
                "figure": str(figure_a),
                "sidecar": str(sidecar_dir / "station_metric_map__pga.csv"),
                "source_sidecar": str(sidecar_dir / "station_metric_map__pga.source.csv"),
                "plot_row_count": 10,
                "written_row_count": 5,
                "plot_sidecar_exact": False,
                "source_row_count": 100,
                "source_written_row_count": 25,
                "source_sidecar_exact": False,
                "sampled": True,
                "source_sampled": True,
            }
        ),
        encoding="utf-8",
    )
    (sidecar_dir / "station_metric_map__pgv.json").write_text(
        json.dumps(
            {
                "figure": str(figure_b),
                "sidecar": str(sidecar_dir / "station_metric_map__pgv.csv"),
                "plot_row_count": 20,
                "written_row_count": 20,
                "plot_sidecar_exact": True,
                "source_row_count": 200,
                "source_written_row_count": 200,
                "source_sidecar_exact": True,
                "sampled": False,
                "source_sampled": False,
            }
        ),
        encoding="utf-8",
    )

    class Context:
        write_sidecars = True
        sidecar_output_dir = sidecar_dir

    result = MetricFigureSuiteResult(
        context=Context(),
        rows=(
            {
                "artifact": "station_metric_maps",
                "status": "written",
                "figure_count": 2,
                "existing_figure_count": 2,
                "figure_paths": [str(figure_a), str(figure_b)],
                "first_figure_path": str(figure_a),
                "figure_paths_preview": f"{figure_a}, {figure_b}",
                "message": "",
            },
        ),
    )

    row = result.status_frame().set_index("artifact").loc["station_metric_maps"]
    assert row["sidecar_dir"] == str(sidecar_dir)
    assert row["sidecar_metadata_count"] == 2
    assert row["sidecar_count"] == 2
    assert row["sidecar_missing_count"] == 0
    assert row["source_sidecar_count"] == 1
    assert row["source_sidecar_missing_count"] == 0
    assert row["plot_row_count_total"] == 30
    assert row["written_row_count_total"] == 25
    assert bool(row["plot_sidecar_all_exact"]) is False
    assert row["source_row_count_total"] == 300
    assert row["source_written_row_count_total"] == 225
    assert bool(row["source_sidecar_all_exact"]) is False
    assert row["sidecar_sampled_count"] == 1
    assert row["source_sidecar_sampled_count"] == 1


def test_standard_metric_diagnostics_split_residuals_by_model(tmp_path) -> None:
    """Standard residual diagnostics should not require notebook-local model loops."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e1", "e2", "e1", "e2", "e1", "e2"],
            "station": ["STA", "STB", "STA", "STB", "STA", "STB", "STA", "STB"],
            "sta_lon": [-118.0, -117.9, -118.0, -117.9, -118.0, -117.9, -118.0, -117.9],
            "sta_lat": [34.0, 34.1, 34.0, 34.1, 34.0, 34.1, 34.0, 34.1],
            "metric": ["PGA", "PGA", "PGA", "PGA", "PSA", "PSA", "PSA", "PSA"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec", "1-2 sec", "", "", "", ""],
            "model": ["m1", "m1", "m2", "m2", "m1", "m1", "m2", "m2"],
            "component": ["Z", "R", "Z", "R", "Z", "R", "Z", "R"],
            "period_s": [np.nan, np.nan, np.nan, np.nan, 1.0, 2.0, 1.0, 2.0],
            "distance_km": [10.0, 20.0, 10.0, 20.0, 10.0, 20.0, 10.0, 20.0],
            "log2_residual": [0.2, -0.1, 0.4, -0.3, 0.1, 0.2, -0.2, -0.1],
        }
    )
    context = MetricFigureContext.from_frame(
        metrics,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=0,
        value_col="log2_residual",
    )

    outputs = context.write_standard_metric_diagnostic_plots(
        scatterplot,
        boxplot,
        heatmap,
        plot_period_score_distribution,
        passband="1-2 sec",
        components=["Z", "R"],
        model=None,
        value_col="log2_residual",
    )

    stems = {path.stem for path in outputs}
    assert any(stem.startswith("scatterplot__pga") and "__m1__" in stem for stem in stems)
    assert any(stem.startswith("scatterplot__pga") and "__m2__" in stem for stem in stems)
    assert any(stem.startswith("boxplot__pga") and "__m1__" in stem for stem in stems)
    assert any(stem.startswith("boxplot__psa") and "__m2__" in stem for stem in stems)
    assert all("__all-models__" not in stem for stem in stems)
    assert all(path.exists() for path in outputs)


def test_standard_metric_diagnostics_write_one_combined_metric_heatmap(tmp_path) -> None:
    """Component heatmaps should summarize all selected metrics in one figure."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e1", "e2", "e1", "e2", "e1", "e2"],
            "station": ["STA", "STB", "STA", "STB", "STA", "STB", "STA", "STB"],
            "metric": ["PGA", "PGA", "PGV", "PGV", "PGA", "PGA", "PGV", "PGV"],
            "band": ["1-2 sec"] * 8,
            "model": ["m1", "m1", "m1", "m1", "m2", "m2", "m2", "m2"],
            "component": ["Z", "R", "Z", "R", "Z", "R", "Z", "R"],
            "distance_km": [10.0, 20.0, 11.0, 21.0, 12.0, 22.0, 13.0, 23.0],
            "log2_residual": [0.2, -0.1, 0.4, -0.3, 0.1, -0.2, 0.5, -0.4],
        }
    )
    context = MetricFigureContext.from_frame(
        metrics,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=0,
        value_col="log2_residual",
    )
    heatmap_calls: list[dict[str, object]] = []

    def _spy_plot(_df, *, output_path, **kwargs):
        heatmap_calls.append({"df": _df.copy(), "kwargs": dict(kwargs)})
        Path(output_path).write_text("plot", encoding="utf-8")

    def _write_plot(_df, *, output_path, **_kwargs):
        Path(output_path).write_text("plot", encoding="utf-8")

    outputs = context.write_standard_metric_diagnostic_plots(
        _write_plot,
        _write_plot,
        _spy_plot,
        _write_plot,
        passband="1-2 sec",
        components=["Z", "R"],
        model=None,
        value_col="log2_residual",
    )

    heatmap_outputs = [path for path in outputs if path.stem.startswith("heatmap__")]
    assert len(heatmap_outputs) == 1
    assert heatmap_outputs[0].stem.startswith("heatmap__all_metrics")
    assert len(heatmap_calls) == 1
    kwargs = heatmap_calls[0]["kwargs"]
    assert kwargs["dep"] == ["PGA", "PGV"]
    assert kwargs["indep"] == "metric_component"
    assert kwargs["column"] == "model"
    assert set(heatmap_calls[0]["df"]["metric_component"]) == {
        "Peak acceleration (PGA) | Z",
        "Peak acceleration (PGA) | R",
        "Peak velocity (PGV) | Z",
        "Peak velocity (PGV) | R",
    }


def test_standard_metric_diagnostics_forward_boxplot_comparison_options(tmp_path) -> None:
    """Large-run standard diagnostics should expose tutorial comparison tables."""

    metrics = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3", "e4"],
            "station": ["STA", "STB", "STC", "STD"],
            "metric": ["PGA", "PGA", "PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec", "1-2 sec"],
            "model": ["m1", "m1", "m1", "m1"],
            "component": ["Z", "R", "Z", "R"],
            "distance_km": [10.0, 20.0, 30.0, 40.0],
            "log2_residual": [0.2, -0.1, 0.3, -0.2],
        }
    )
    context = MetricFigureContext.from_frame(
        metrics,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=0,
        value_col="log2_residual",
    )
    seen: dict[str, list[dict[str, object]]] = {"scatter": [], "box": [], "heat": [], "period": []}

    def _spy_plot(label: str):
        def _plot(_df, *, output_path, **kwargs):
            seen[label].append(dict(kwargs))
            Path(output_path).write_text("plot", encoding="utf-8")

        return _plot

    outputs = context.write_standard_metric_diagnostic_plots(
        _spy_plot("scatter"),
        _spy_plot("box"),
        _spy_plot("heat"),
        _spy_plot("period"),
        passband="1-2 sec",
        components=["Z", "R"],
        model="m1",
        value_col="log2_residual",
        compare_to="Z",
        table=True,
    )

    assert outputs
    assert seen["box"]
    assert any(call.get("compare_to") == "Z" and call.get("table") is True for call in seen["box"])
    assert all("compare_to" not in call and "table" not in call for call in seen["scatter"])
    assert all("compare_to" not in call and "table" not in call for call in seen["heat"])
    assert not seen["period"]


def test_band_score_distribution_limits_include_upper_whisker() -> None:
    """Robust scaling should not clip visible band-distribution boxplot whiskers."""

    rows = []
    for band in ["1-2 sec", "2-3 sec"]:
        for component in ["R", "T", "Z"]:
            for value in [-2.0, -1.0, 0.0, 1.0, 5.0, 9.5]:
                rows.append({"band": band, "component": component, "metric": "PGA", "log2_residual": value})
    fig = plot_band_score_distribution(
        pd.DataFrame(rows),
        band_col="band",
        score_col="log2_residual",
        color_col="component",
        robust_axis_percentile=80.0,
        showfig=False,
        savefig=False,
    )
    ymin, ymax = fig.axes[0].get_ylim()
    assert ymax > 9.5
    assert ymin < -2.0
    import matplotlib.pyplot as plt

    plt.close(fig)


def test_generic_metric_diagnostics_method_delegates_to_standard_name(tmp_path, monkeypatch) -> None:
    """The old diagnostic method name should remain a compatibility wrapper."""

    context = MetricFigureContext.from_frame(
        pd.DataFrame({"metric": ["PGA"], "band": ["1-2 sec"], "component": ["Z"], "log2_residual": [0.1]}),
        tmp_path / "figures",
        make_figures=False,
    )
    seen: dict[str, object] = {}

    def fake_standard(*args: object, **kwargs: object) -> list[Path]:
        seen["args"] = args
        seen["kwargs"] = kwargs
        return [tmp_path / "figures" / "standard.png"]

    monkeypatch.setattr(context, "write_standard_metric_diagnostic_plots", fake_standard)

    result = context.write_generic_metric_diagnostic_plots(
        _dummy_png_plot,
        _dummy_png_plot,
        _dummy_png_plot,
        _dummy_png_plot,
        passband="1-2 sec",
        components=["Z"],
        model="m1",
        value_col="log2_residual",
        compare_to="Z",
        table=True,
    )

    assert result == [tmp_path / "figures" / "standard.png"]
    assert len(seen["args"]) == 4
    assert seen["kwargs"] == {
        "passband": "1-2 sec",
        "components": ["Z"],
        "model": "m1",
        "value_col": "log2_residual",
        "showfig": False,
        "compare_to": "Z",
        "table": True,
    }


def test_metric_station_summary_uses_supported_station_and_event_aliases(tmp_path) -> None:
    """Station aggregation should not depend on already-canonical column names."""

    rows = pd.DataFrame(
        {
            "event_title": ["e1", "e2", "e3", "e4"],
            "station_id": ["STA", "STA", "STA", "STB"],
            "station_lon": [-118.0, -118.04, -118.02, -117.9],
            "station_lat": [34.0, 34.04, 34.02, 34.1],
            "metric": ["PGA", "PGA", "PGA", "PGA"],
            "band": ["1-2 sec", "1-2 sec", "1-2 sec", "1-2 sec"],
            "component": ["Z", "Z", "Z", "Z"],
            "model": ["m1", "m1", "m1", "m1"],
            "log2_residual": [1.0, 3.0, np.nan, -2.0],
        }
    )
    context = MetricFigureContext.from_frame(
        rows,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=0,
        value_col="log2_residual",
        station_aggregation="mean",
        write_sidecars=True,
        sidecar_rows=None,
    )

    summary = context.station_summary_for_map(rows)
    sta = summary.loc[summary["station"].eq("STA")].iloc[0]

    assert "station" in summary.columns
    assert "sta_lon" in summary.columns
    assert "sta_lat" in summary.columns
    assert sta["log2_residual"] == pytest.approx(2.0)
    assert sta["source_row_count"] == 2
    assert sta["source_event_count"] == 2
    assert sta["input_row_count"] == 3
    assert sta["input_event_count"] == 3
    assert sta["dropped_nonfinite_row_count"] == 1
    assert sta["dropped_nonfinite_event_count"] == 1
    assert sta["source_coordinate_count"] == 3
    assert sta["sta_lon"] == pytest.approx(-118.02)
    assert sta["sta_lat"] == pytest.approx(34.02)
    assert summary.attrs["svtk_aggregation_group_columns"] == ["station_id"]
    assert summary.attrs["svtk_aggregation_coordinate_columns"] == ["station_lon", "station_lat"]
    assert summary.attrs["svtk_aggregation_input_event_count"] == 4
    assert summary.attrs["svtk_aggregation_finite_event_count"] == 3

    def _dummy_plot(frame: pd.DataFrame, *, output_path, **kwargs) -> None:
        Path(output_path).write_text(str(len(frame)), encoding="utf-8")

    item = {"key": "pga", "label": "PGA", "metric": "PGA", "period_s": None, "df": rows}
    output = context.write_metric_plot("alias_station_map", item, _dummy_plot, df=summary, source_df=rows)
    assert output is not None
    metadata = json.loads((context.sidecar_output_dir / f"{output.stem}.json").read_text(encoding="utf-8"))
    assert metadata["plot_rows_role"] == "post_aggregation_station_summary"
    assert metadata["source_rows_role"] == "pre_aggregation_metric_rows"
    assert metadata["plot_station_count"] == 2
    assert metadata["source_station_count"] == 2
    assert metadata["source_event_count"] == 4


def test_sampled_station_map_source_sidecar_matches_plotted_station_groups(tmp_path) -> None:
    """Sampled station maps should keep source rows tied to plotted station groups."""

    rows = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3", "e4", "e5", "e6"],
            "station": ["STA", "STA", "STB", "STB", "STC", "STC"],
            "sta_lon": [-118.0, -118.02, -117.8, -117.82, -117.6, -117.62],
            "sta_lat": [34.0, 34.02, 34.1, 34.12, 34.2, 34.22],
            "metric": ["PGA"] * 6,
            "band": ["1-2 sec"] * 6,
            "component": ["Z"] * 6,
            "model": ["m1"] * 6,
            "log2_residual": [1.0, 3.0, 5.0, 7.0, 9.0, 11.0],
        }
    )
    context = MetricFigureContext.from_frame(
        rows,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=1,
        value_col="log2_residual",
        station_aggregation="mean",
        write_sidecars=True,
        sidecar_rows=None,
    )
    station_summary = context.station_summary_for_map(rows)

    def _dummy_plot(frame: pd.DataFrame, *, output_path, **kwargs) -> None:
        Path(output_path).write_text(",".join(frame["station"].astype(str)), encoding="utf-8")

    item = {"key": "pga", "label": "PGA", "metric": "PGA", "period_s": None, "df": rows}
    output = context.write_metric_plot("sampled_station_map", item, _dummy_plot, df=station_summary, source_df=rows)

    assert output is not None
    sidecar = pd.read_csv(context.sidecar_output_dir / f"{output.stem}.csv")
    source_sidecar = pd.read_csv(context.sidecar_output_dir / f"{output.stem}.source.csv")
    metadata = json.loads((context.sidecar_output_dir / f"{output.stem}.json").read_text(encoding="utf-8"))
    plotted_station = sidecar.loc[0, "station"]

    assert len(sidecar) == 1
    assert set(source_sidecar["station"]) == {plotted_station}
    assert len(source_sidecar) == 2
    assert metadata["plot_row_count"] == 1
    assert metadata["source_row_count"] == 2
    assert metadata["source_rows_filter"] == "aggregation_groups_present_in_plot_rows"
    assert metadata["aggregation_input_row_count"] == 6
    assert metadata["aggregation_finite_row_count"] == 6
    assert metadata["aggregation_input_station_count"] == 3
    assert metadata["aggregation_finite_station_count"] == 3


def test_psa_period_sheet_source_sidecar_tracks_plotted_station_period_groups(tmp_path) -> None:
    """PSA station sheets should filter source rows to the station/period groups plotted."""

    rows = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3", "e4"],
            "station": ["STA", "STB", "STA", "STB"],
            "sta_lon": [-118.0, -117.9, -118.0, -117.9],
            "sta_lat": [34.0, 34.1, 34.0, 34.1],
            "metric": ["PSA", "PSA", "PSA", "PSA"],
            "band": ["", "", "", ""],
            "model": ["m1", "m1", "m1", "m1"],
            "component": ["Z", "Z", "Z", "Z"],
            "period_s": [1.0, 1.0, 2.0, 2.0],
            "log2_residual": [0.5, 1.5, -0.25, 0.75],
        }
    )
    context = MetricFigureContext.from_frame(
        rows,
        tmp_path / "figures",
        make_figures=True,
        sample_rows=1,
        value_col="log2_residual",
        station_aggregation="mean",
        write_sidecars=True,
        sidecar_rows=None,
    )
    item = next(context.iter_metric_frames(components=["Z"], model="m1", split_psa_period=False))

    def _dummy_png_plot(frame: pd.DataFrame, *, output_path, **kwargs) -> None:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(2, 1.5))
        ax.text(0.5, 0.5, f"rows={len(frame)}", ha="center", va="center")
        ax.set_axis_off()
        fig.savefig(output_path)
        plt.close(fig)

    output = context.write_psa_period_sheet(
        "sampled_station_metric_map",
        item,
        _dummy_png_plot,
        df_factory=context.station_period_summary_for_item,
        source_df_factory=context.item_source_rows,
        required=("station", "sta_lon", "sta_lat", "period_s", "log2_residual"),
    )

    assert output is not None
    sidecar = pd.read_csv(context.sidecar_output_dir / f"{output.stem}.csv")
    source_sidecar = pd.read_csv(context.sidecar_output_dir / f"{output.stem}.source.csv")
    metadata = json.loads((context.sidecar_output_dir / f"{output.stem}.json").read_text(encoding="utf-8"))
    plotted_keys = set(zip(sidecar["station"].astype(str), sidecar["period_s"].astype(float)))
    source_keys = set(zip(source_sidecar["station"].astype(str), source_sidecar["period_s"].astype(float)))

    assert len(sidecar) == 2
    assert len(source_sidecar) == 2
    assert source_keys == plotted_keys
    assert metadata["aggregation_group_columns"] == ["station", "period_s"]
    assert metadata["source_rows_filter"] == "aggregation_groups_present_in_plot_rows"
    status = figure_sidecar_status_frame(context.sidecar_output_dir).set_index("figure")
    status_row = status.loc[f"{output.stem}.png"]
    assert status_row["source_rows_filter"] == "aggregation_groups_present_in_plot_rows"
    assert status_row["aggregation_group_columns"] == ["station", "period_s"]
    assert status_row["aggregation_panel_count"] == 2
    assert status_row["source_period_count"] == 2


def test_metric_workflow_runs_tasks_and_applies_side_specific_spectral_qc(tmp_path) -> None:
    """The workflow should plan pair tasks, run rows, and preserve QC provenance."""

    dt = 0.01
    time = np.arange(0.0, 5.0, dt)
    observed = 2.0 * np.sin(2.0 * np.pi * 1.0 * time)
    synthetic = np.sin(2.0 * np.pi * 1.0 * time)
    obs_path = tmp_path / "obs.npz"
    syn_path = tmp_path / "syn.npz"
    _write_npz_waveform(obs_path, observed, station="ABC", channel="HNZ", sampling_rate=1.0 / dt)
    _write_npz_waveform(syn_path, synthetic, station="ABC", channel="HNZ", sampling_rate=1.0 / dt)

    obs_inventory = pd.DataFrame(
        {
            "source": ["observed"],
            "event_id": ["e1"],
            "station": ["ABC"],
            "component": ["Z"],
            "waveform_path": [obs_path],
            "dt": [dt],
        }
    )
    syn_inventory = pd.DataFrame(
        {
            "source": ["synthetic"],
            "event_id": ["e1"],
            "station": ["ABC"],
            "component": ["Z"],
            "model": ["m1"],
            "waveform_path": [syn_path],
            "dt": [dt],
            "synthetic_max_frequency_hz": [0.5],
        }
    )
    plan = MetricPlan(
        metrics=("PGA", "PSA", "original_cc"),
        passbands=(),
        components=("Z",),
        models=("m1",),
        metric_groups=("amplitude", "spectral", "cross_correlation"),
        transforms=("log2_residual",),
        spectral_periods_s=(1.0, 2.0),
        output_mode="full",
        synthetic_max_frequency_hz=0.5,
    )

    tasks = plan_metric_tasks(
        obs_inventory,
        syn_inventory,
        plan=plan,
        spectral_min_cycles_in_record=1.0,
        disable_spectral_relative_amplitude_qc=True,
    )
    assert [(task.metrics, task.passband) for task in tasks] == [
        (("PGA", "original_cc"), ""),
        (("PSA",), ""),
    ]

    rows = run_metric_tasks(tasks)
    pga = rows.loc[rows["metric"].eq("PGA")].iloc[0]
    assert pga["value_obs"] == pytest.approx(2.0, rel=0.03)
    assert pga["value_syn"] == pytest.approx(1.0, rel=0.03)
    assert pga["log2_residual"] == pytest.approx(1.0, abs=0.05)

    cc = rows.loc[rows["metric"].eq("original_cc")].iloc[0]
    assert cc["value"] == pytest.approx(1.0, abs=1e-6)
    summaries = build_dashboard_summaries(rows)
    summary_columns = available_dashboard_value_columns(summaries["model_metric_band"])
    assert "med_value" in summary_columns
    cc_summary = summaries["model_metric_band"].loc[summaries["model_metric_band"]["metric"].eq("original_cc")].iloc[0]
    assert cc_summary["med_value"] == pytest.approx(1.0, abs=1e-6)
    assert cc_summary["n"] == 1

    psa_period_1 = rows.loc[rows["metric"].eq("PSA") & rows["period_s"].eq(1.0)].iloc[0]
    assert psa_period_1["syn_qc_status"] == "fail"
    assert psa_period_1["comparison_qc_status"] == "fail"
    assert "period_below_min_supported_period" in psa_period_1["syn_qc_reason"]

    psa_period_2 = rows.loc[rows["metric"].eq("PSA") & rows["period_s"].eq(2.0)].iloc[0]
    assert psa_period_2["comparison_qc_status"] == "pass"


def test_metric_planning_calculates_spectral_metrics_once_across_passbands(tmp_path) -> None:
    """PSA/FAS should be planned as broadband rows, not repeated per passband."""

    dt = 0.01
    time = np.arange(0.0, 5.0, dt)
    obs_path = tmp_path / "obs.npz"
    syn_path = tmp_path / "syn.npz"
    _write_npz_waveform(obs_path, 2.0 * np.sin(2.0 * np.pi * time), station="ABC", channel="HNZ", sampling_rate=1.0 / dt)
    _write_npz_waveform(syn_path, np.sin(2.0 * np.pi * time), station="ABC", channel="HNZ", sampling_rate=1.0 / dt)
    plan = MetricPlan(
        metrics=("PGA", "PSA"),
        passbands=((1.0, 2.0), (2.0, 3.0)),
        components=("Z",),
        models=("m1",),
        transforms=("log2_residual",),
        output_mode="full",
        spectral_periods_s=(1.0, 2.0),
        disable_spectral_relative_amplitude_qc=True,
    )
    obs_inventory = pd.DataFrame(
        {"event_id": ["e1"], "station": ["ABC"], "component": ["Z"], "waveform_path": [obs_path], "dt": [dt]}
    )
    syn_inventory = pd.DataFrame(
        {"event_id": ["e1"], "station": ["ABC"], "component": ["Z"], "model": ["m1"], "waveform_path": [syn_path], "dt": [dt]}
    )

    tasks = plan_metric_tasks(obs_inventory, syn_inventory, plan=plan, use_qc=False)
    rows = run_metric_tasks(tasks)

    assert [(task.metrics, task.passband) for task in tasks] == [
        (("PGA",), "1-2 sec"),
        (("PGA",), "2-3 sec"),
        (("PSA",), ""),
    ]
    pga_rows = rows.loc[rows["metric"].eq("PGA")]
    psa_rows = rows.loc[rows["metric"].eq("PSA")]
    assert sorted(pga_rows["passband"].unique()) == ["1-2 sec", "2-3 sec"]
    assert psa_rows["passband"].unique().tolist() == [""]
    assert sorted(psa_rows["period_s"].dropna().unique()) == [1.0, 2.0]
    assert len(psa_rows) == 2


def test_metric_task_planning_can_restrict_source_specific_modes_to_overlap(tmp_path) -> None:
    obs_inventory = pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "station": ["ABC", "ABC"],
            "component": ["Z", "Z"],
            "waveform_path": [tmp_path / "obs1.npz", tmp_path / "obs2.npz"],
            "dt": [0.01, 0.01],
        }
    )
    syn_inventory = pd.DataFrame(
        {
            "event_id": ["e1"],
            "station": ["ABC"],
            "component": ["Z"],
            "model": ["m1"],
            "waveform_path": [tmp_path / "syn1.npz"],
            "dt": [0.01],
        }
    )
    plan = MetricPlan(
        metrics=("PGA",),
        passbands=(),
        components=("Z",),
        models=("m1",),
        transforms=(),
        output_mode="observed",
        require_source_overlap=True,
        source_overlap_scope="event",
    )

    tasks = plan_metric_tasks(obs_inventory, syn_inventory, plan=plan)

    assert [task.event_id for task in tasks] == ["e1"]


def test_metric_task_planning_defaults_to_retained_qc_pairs(tmp_path) -> None:
    """Pair manifests should only include task keys with observed/synthetic QC pass pairs."""

    obs_inventory = pd.DataFrame(
        {
            "event_id": ["e1", "e1"],
            "station": ["S1", "S2"],
            "component": ["Z", "Z"],
            "waveform_path": [tmp_path / "obs_s1.npz", tmp_path / "obs_s2.npz"],
            "dt": [0.01, 0.01],
        }
    )
    syn_inventory = pd.DataFrame(
        {
            "event_id": ["e1", "e1"],
            "station": ["S1", "S2"],
            "component": ["Z", "Z"],
            "model": ["m1", "m1"],
            "waveform_path": [tmp_path / "syn_s1.npz", tmp_path / "syn_s2.npz"],
            "dt": [0.01, 0.01],
        }
    )
    plan = MetricPlan(
        metrics=("PGA",),
        passbands=(),
        components=("Z",),
        models=("m1",),
        transforms=("log2_residual",),
        output_mode="full",
    )
    qc_table = pd.DataFrame(
        [
            {
                "source": "observed",
                "event_id": "e1",
                "station": "S1",
                "component": "Z",
                "passband": "",
                "metric_group": "amplitude",
                "metric": "PGA",
                "period_s": np.nan,
                "qc_status": "pass",
            },
            {
                "source": "synthetic",
                "event_id": "e1",
                "station": "S1",
                "component": "Z",
                "passband": "",
                "metric_group": "amplitude",
                "metric": "PGA",
                "period_s": np.nan,
                "qc_status": "pass",
            },
            {
                "source": "observed",
                "event_id": "e1",
                "station": "S2",
                "component": "Z",
                "passband": "",
                "metric_group": "amplitude",
                "metric": "PGA",
                "period_s": np.nan,
                "qc_status": "pass",
            },
            {
                "source": "synthetic",
                "event_id": "e1",
                "station": "S2",
                "component": "Z",
                "passband": "",
                "metric_group": "amplitude",
                "metric": "PGA",
                "period_s": np.nan,
                "qc_status": "fail",
            },
        ]
    )

    retained_tasks = plan_metric_tasks(obs_inventory, syn_inventory, plan=plan, qc_table=qc_table)
    all_tasks = plan_metric_tasks(
        obs_inventory,
        syn_inventory,
        plan=plan,
        qc_table=qc_table,
        require_passing_qc_pairs=False,
    )

    assert [(task.event_id, task.station, task.component, task.passband) for task in retained_tasks] == [("e1", "S1", "Z", "")]
    assert [(task.event_id, task.station) for task in all_tasks] == [("e1", "S1"), ("e1", "S2")]


def test_metric_task_planning_retains_spectral_qc_as_broadband_task(tmp_path) -> None:
    """Spectral QC pass rows should retain one broadband spectral task."""

    obs_inventory = pd.DataFrame(
        {"event_id": ["e1"], "station": ["S1"], "component": ["Z"], "waveform_path": [tmp_path / "obs.npz"], "dt": [0.01]}
    )
    syn_inventory = pd.DataFrame(
        {"event_id": ["e1"], "station": ["S1"], "component": ["Z"], "model": ["m1"], "waveform_path": [tmp_path / "syn.npz"], "dt": [0.01]}
    )
    plan = MetricPlan(
        metrics=("PSA",),
        passbands=((1.0, 2.0), (2.0, 3.0)),
        components=("Z",),
        models=("m1",),
        transforms=("log2_residual",),
        output_mode="full",
        spectral_periods_s=(1.0,),
    )
    qc_table = pd.DataFrame(
        [
            {
                "source": "observed",
                "event_id": "e1",
                "station": "S1",
                "component": "Z",
                "passband": "1-2 sec",
                "metric_group": "spectral",
                "metric": "PSA",
                "period_s": 1.0,
                "qc_status": "pass",
            },
            {
                "source": "synthetic",
                "event_id": "e1",
                "station": "S1",
                "component": "Z",
                "passband": "1-2 sec",
                "metric_group": "spectral",
                "metric": "PSA",
                "period_s": 1.0,
                "qc_status": "pass",
            },
        ]
    )

    tasks = plan_metric_tasks(obs_inventory, syn_inventory, plan=plan, qc_table=qc_table)

    assert [(task.metrics, task.passband) for task in tasks] == [(("PSA",), "")]


def test_metric_workflow_manifest_batches_merge_and_slurm_script(tmp_path) -> None:
    """Manifest execution should run batches, merge outputs, and write SLURM scripts."""

    dt = 0.01
    time = np.arange(0.0, 3.0, dt)
    obs_path = tmp_path / "obs.npz"
    syn_path = tmp_path / "syn.npz"
    _write_npz_waveform(obs_path, 2.0 * np.sin(2.0 * np.pi * time), station="ABC", channel="HNZ", sampling_rate=1.0 / dt)
    _write_npz_waveform(syn_path, np.sin(2.0 * np.pi * time), station="ABC", channel="HNZ", sampling_rate=1.0 / dt)
    plan = MetricPlan(
        metrics=("PGA",),
        passbands=(),
        components=("Z",),
        models=("m1",),
        transforms=("log2_residual",),
        output_mode="full",
    )
    obs_inventory = pd.DataFrame({"event_id": ["e1"], "station": ["ABC"], "component": ["Z"], "waveform_path": [obs_path], "dt": [dt]})
    syn_inventory = pd.DataFrame({"event_id": ["e1"], "station": ["ABC"], "component": ["Z"], "model": ["m1"], "waveform_path": [syn_path], "dt": [dt]})
    tasks = plan_metric_tasks(obs_inventory, syn_inventory, plan=plan)

    planning_metadata = {
        "planning_policy": "passing_observed_synthetic_qc_pairs",
        "use_qc": True,
        "require_passing_qc_pairs": True,
        "include_qc_failed_tasks": False,
        "require_source_overlap": True,
        "source_overlap_scope": "event_station",
        "output_mode": "full",
    }
    manifest = write_task_manifest(
        tasks,
        tmp_path / "manifest.json",
        output_dir=tmp_path / "batches",
        batch_size=1,
        planning_metadata=planning_metadata,
    )
    manifest_status = manifest.status_frame()
    assert manifest_status.loc[0, "name"] == "metric_manifest_path"
    assert manifest_status.loc[0, "artifact"] == "metric_manifest"
    assert manifest_status.loc[0, "artifact_label"] == "metric workflow manifest"
    assert manifest_status.loc[0, "artifact_role"] == "metric_manifest"
    assert manifest_status.loc[0, "status"] == "ready"
    assert manifest_status.loc[0, "resolved_path"] == str(tmp_path / "manifest.json")
    assert manifest_status.loc[0, "path"] == str(tmp_path / "manifest.json")
    assert bool(manifest_status.loc[0, "exists"]) is True
    assert manifest_status.loc[0, "manifest_path"] == str(tmp_path / "manifest.json")
    assert bool(manifest_status.loc[0, "manifest_exists"]) is True
    assert manifest_status.loc[0, "task_count"] == len(tasks)
    assert manifest_status.loc[0, "batch_count"] == 1
    assert manifest_status.loc[0, "batch_output_dir"] == str(tmp_path / "batches")
    assert manifest_status.loc[0, "min_tasks_per_batch"] == 1
    assert manifest_status.loc[0, "max_tasks_per_batch"] == 1
    assert manifest_status.loc[0, "first_batch_output"] == str(tmp_path / "batches" / "metrics_batch_0000.csv")
    assert manifest_status.loc[0, "last_batch_output"] == str(tmp_path / "batches" / "metrics_batch_0000.csv")
    assert manifest_status.loc[0, "qc_table"] == ""
    assert manifest_status.loc[0, "planning_policy"] == "passing_observed_synthetic_qc_pairs"
    assert bool(manifest_status.loc[0, "use_qc"]) is True
    assert bool(manifest_status.loc[0, "require_passing_qc_pairs"]) is True
    assert bool(manifest_status.loc[0, "include_qc_failed_tasks"]) is False
    assert bool(manifest_status.loc[0, "require_source_overlap"]) is True
    assert manifest_status.loc[0, "source_overlap_scope"] == "event_station"
    assert manifest_status.loc[0, "output_mode"] == "full"
    parsed = read_task_manifest(manifest.manifest_path)
    parsed_status = parsed.status_frame()
    assert parsed_status.loc[0, "task_count"] == len(tasks)
    assert parsed_status.loc[0, "batch_count"] == 1
    assert parsed.planning_metadata == planning_metadata
    assert parsed_status.loc[0, "planning_policy"] == "passing_observed_synthetic_qc_pairs"
    assert len(parsed.batches) == 1
    initial_status = metric_manifest_batch_status(parsed)
    assert initial_status.total_batches == 1
    assert initial_status.completed_count == 0
    assert initial_status.missing_batches == (0,)
    initial_status_frame = initial_status.status_frame()
    assert initial_status_frame.loc[0, "name"] == "metric_batch_outputs"
    assert initial_status_frame.loc[0, "artifact"] == "metric_batch_outputs"
    assert initial_status_frame.loc[0, "artifact_label"] == "metric batch outputs"
    assert initial_status_frame.loc[0, "artifact_role"] == "metric_batch_outputs"
    assert initial_status_frame.loc[0, "status"] == "incomplete"
    assert initial_status_frame.loc[0, "resolved_path"] == str(tmp_path / "manifest.json")
    assert initial_status_frame.loc[0, "path"] == str(tmp_path / "manifest.json")
    assert bool(initial_status_frame.loc[0, "exists"]) is True
    assert bool(initial_status_frame.loc[0, "all_complete"]) is False
    initial_readiness = metric_slurm_submission_readiness(initial_status)
    assert initial_readiness.should_run is True
    assert initial_readiness.reason == "incomplete_batches"
    assert "1 missing batch output" in initial_readiness.message
    initial_readiness_frame = initial_readiness.status_frame()
    assert initial_readiness_frame.loc[0, "artifact"] == "metric_batch_outputs"
    assert initial_readiness_frame.loc[0, "status"] == "incomplete"
    assert bool(initial_readiness_frame.loc[0, "should_submit"]) is True

    batch_output = run_manifest_batch(parsed, batch_index=0)
    assert batch_output.exists()
    completed_status = metric_manifest_batch_status(parsed)
    assert completed_status.completed_batches == (0,)
    assert completed_status.missing_count == 0
    assert completed_status.all_complete
    assert completed_status.status_frame().loc[0, "status"] == "complete"
    completed_readiness = metric_slurm_submission_readiness(completed_status)
    assert completed_readiness.should_run is False
    assert completed_readiness.reason == "current"
    assert "skipping metric Slurm submission" in completed_readiness.message
    overwrite_readiness = metric_slurm_submission_readiness(completed_status, overwrite=True)
    assert overwrite_readiness.should_run is True
    assert overwrite_readiness.reason == "overwrite"
    merged_output = merge_batch_outputs(parsed, tmp_path / "merged.csv")
    merged = pd.read_csv(merged_output)
    assert merged.loc[0, "metric"] == "PGA"

    script = write_metrics_slurm_script(
        parsed.manifest_path,
        tmp_path / "run_metrics.slurm",
        SlurmSettings(python_command="python", environment_setup=("source activate spatial-vtk",), max_concurrent=2),
    )
    text = script.read_text(encoding="utf-8")
    assert "#SBATCH --array=0%2" in text
    assert "SVTK_METRIC_WORKFLOW_START_FILE" in text
    assert "run_metrics.slurm.start" in text
    assert 'echo "Metric workflow start: $SVTK_METRIC_WORKFLOW_START_TIME"' in text
    assert "python -m spatial_vtk.metrics.workflow.execution" in text
    assert "source activate spatial-vtk" in text

    partial_manifest = tmp_path / "partial_manifest.json"
    partial_manifest.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "qc_table": "",
                "tasks": [],
                "batches": [
                    {"batch_index": 0, "task_indices": [], "output_path": str(tmp_path / "done_0.csv")},
                    {"batch_index": 1, "task_indices": [], "output_path": str(tmp_path / "missing_1.csv")},
                    {"batch_index": 2, "task_indices": [], "output_path": str(tmp_path / "missing_2.csv")},
                    {"batch_index": 4, "task_indices": [], "output_path": str(tmp_path / "missing_4.csv")},
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "done_0.csv").write_text("metric\nPGA\n", encoding="utf-8")
    partial_status = metric_manifest_batch_status(partial_manifest)
    assert partial_status.completed_batches == (0,)
    assert partial_status.missing_batches == (1, 2, 4)

    status_only_manifest = tmp_path / "status_only_manifest.json"
    status_only_manifest.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "qc_table": "",
                "tasks": [{"this": "is intentionally not a metric task"}],
                "batches": [{"batch_index": 0, "task_indices": [0], "output_path": str(tmp_path / "status_only.csv")}],
            }
        ),
        encoding="utf-8",
    )
    status_only = metric_manifest_batch_status(status_only_manifest)
    assert status_only.total_batches == 1
    assert status_only.missing_batches == (0,)

    incomplete_script = write_metrics_slurm_script(
        partial_manifest,
        tmp_path / "run_incomplete_metrics.slurm",
        SlurmSettings(python_command="python", max_concurrent=3),
        batch_indices=partial_status.missing_batches,
        overwrite_batches=True,
    )
    incomplete_text = incomplete_script.read_text(encoding="utf-8")
    assert "#SBATCH --array=1-2,4%3" in incomplete_text
    assert "Metric selected batches: 3 of 4" in incomplete_text
    assert "--batch-index $SLURM_ARRAY_TASK_ID --overwrite" in incomplete_text


def test_metric_workflow_elapsed_prefers_slurm_start_time(tmp_path, monkeypatch) -> None:
    """Metric stdout elapsed time should use the Slurm run stamp before manifest mtime."""

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text('{"manifest_version": 1, "tasks": [], "batches": []}\n', encoding="utf-8")
    old_time = 1_600_000_000
    manifest_path.touch()
    import os
    import time

    os.utime(manifest_path, (old_time, old_time))
    manifest = read_task_manifest(manifest_path)
    monkeypatch.setenv("SVTK_METRIC_WORKFLOW_START_TIME", str(time.time() - 12.0))

    elapsed = metric_execution._workflow_elapsed_seconds(manifest)

    assert 0.0 <= elapsed < 60.0


def test_metric_slurm_module_docs_name_manifest_array_contract() -> None:
    """Metric Slurm help should describe manifest arrays, not a generic script."""

    import spatial_vtk.metrics.workflow as workflow_package
    import spatial_vtk.metrics.workflow.slurm as slurm_module
    import spatial_vtk.metrics.workflow.tasks as task_module

    assert "metric Slurm\narray scripts" in (workflow_package.__doc__ or "")
    assert "Metric Slurm array support for manifest batches" in (slurm_module.__doc__ or "")
    assert "metric Slurm array job" in (task_module.__doc__ or "")
    assert "generic SLURM" not in (workflow_package.__doc__ or "")
    assert "Generic SLURM" not in (slurm_module.__doc__ or "")
    assert "generic SLURM" not in (task_module.__doc__ or "")

    parser = slurm_module.build_arg_parser()
    help_text = parser.format_help()
    assert "Write a metric Slurm array script from a Spatial-VTK manifest." in help_text
    assert "Metric workflow manifest JSON with batch output paths." in help_text
    assert "Metric Slurm array script output path." in help_text
    assert "--metric-manifest" in help_text
    assert "--metrics-slurm-script-output" in help_text
    assert "legacy" in help_text
    assert "alias" in help_text

    args = parser.parse_args(
        [
            "--metric-manifest",
            "metric_manifest.json",
            "--metrics-slurm-script-output",
            "run_metrics.slurm",
        ]
    )
    legacy_args = parser.parse_args(["--manifest", "legacy_manifest.json", "--output", "legacy_metrics.slurm"])
    assert args.metric_manifest == "metric_manifest.json"
    assert args.metrics_slurm_script_output == "run_metrics.slurm"
    assert legacy_args.metric_manifest == "legacy_manifest.json"
    assert legacy_args.metrics_slurm_script_output == "legacy_metrics.slurm"
    assert not hasattr(args, "manifest")
    assert not hasattr(args, "output")


def test_configured_metric_plan_slurm_and_merge_helpers_use_registered_paths(tmp_path) -> None:
    """Config-backed metric helpers should mirror CLI workflow defaults."""

    clear_active_config()
    config_path = tmp_path / "spatial-vtk.yaml"
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
outputs:
  root: outputs
  tables: outputs/tables
compute:
  slurm:
    python_command: python
metrics:
  metrics: [PGA]
  components: [Z]
  passbands: [[1, 2]]
  models: [m1]
""",
        encoding="utf-8",
    )
    tables = tmp_path / "outputs" / "tables"
    tables.mkdir(parents=True)
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

    missing_manifest_slurm = metric_slurm_submission_readiness_from_config(config_path=config_path)
    assert missing_manifest_slurm.should_run is False
    assert missing_manifest_slurm.reason == "missing_inputs"
    assert "Metric manifest is not ready yet" in missing_manifest_slurm.message

    missing_manifest_merge = metric_batch_merge_readiness_from_config(config_path=config_path)
    assert missing_manifest_merge.should_run is False
    assert missing_manifest_merge.reason == "missing_inputs"
    assert "metric_manifest_path" in set(missing_manifest_merge.status_frame()["name"])

    missing_rows_outputs = metric_outputs_readiness_from_config(config_path=config_path)
    assert missing_rows_outputs.should_run is False
    assert missing_rows_outputs.reason == "missing_inputs"
    assert "Merged metric rows are not ready yet" in missing_rows_outputs.message

    plan_result = plan_metric_tasks_from_config(config_path=config_path, manifest=True, batch_count=1)

    manifest_path = Path(plan_result["manifest_path"])
    manifest = read_task_manifest(manifest_path)
    assert manifest_path == tables / "metric_manifest.json"
    assert plan_result["metric_manifest_path"] == str(manifest_path)
    assert plan_result["metric_manifest_path"] == plan_result["manifest_path"]
    assert plan_result["planned_output_path"] == str(manifest_path)
    assert plan_result["metric_manifest_batch_count"] == plan_result["batch_count"] == 1
    assert plan_result["metric_manifest_batch_size"] == plan_result["batch_size"] == 1
    assert plan_result["metric_manifest_batch_output_dir"] == plan_result["batch_output_dir"]
    assert plan_result["metric_manifest_min_tasks_per_batch"] == plan_result["min_tasks_per_batch"] == 1
    assert plan_result["metric_manifest_max_tasks_per_batch"] == plan_result["max_tasks_per_batch"] == 1
    assert plan_result["metric_manifest_first_batch_output"] == plan_result["first_batch_output"]
    assert plan_result["metric_manifest_last_batch_output"] == plan_result["last_batch_output"]
    assert plan_result["first_batch_output"].endswith("outputs/metric_batches/metrics_batch_0000.csv")
    assert plan_result["last_batch_output"].endswith("outputs/metric_batches/metrics_batch_0000.csv")
    assert plan_result["observed_metric_inventory_path"] == str(tables / "observed_metric_inventory.parquet")
    assert plan_result["synthetic_metric_inventory_path"] == str(tables / "synthetic_metric_inventory.parquet")
    assert plan_result["metric_qc_table_path"] == str(tables / "qc_inventory_overlap.parquet")
    assert plan_result["planning_policy"] == "passing_observed_synthetic_qc_pairs"
    assert bool(plan_result["use_qc"]) is True
    assert bool(plan_result["require_passing_qc_pairs"]) is True
    assert bool(plan_result["include_qc_failed_tasks"]) is False
    assert bool(plan_result["require_source_overlap"]) is False
    assert plan_result["source_overlap_scope"] == "event_station"
    assert plan_result["output_mode"] == "full"
    assert len(manifest.tasks) == 1
    assert manifest.planning_metadata["planning_policy"] == "passing_observed_synthetic_qc_pairs"
    assert manifest.status_frame().loc[0, "planning_policy"] == "passing_observed_synthetic_qc_pairs"
    assert manifest.batches[0]["output_path"].endswith("outputs/metric_batches/metrics_batch_0000.csv")

    incomplete_slurm = metric_slurm_submission_readiness_from_config(config_path=config_path)
    assert incomplete_slurm.should_run is True
    assert incomplete_slurm.reason == "incomplete_batches"

    incomplete_merge = metric_batch_merge_readiness_from_config(config_path=config_path)
    assert incomplete_merge.should_run is False
    assert incomplete_merge.reason == "missing_inputs"
    assert "Metric batches are incomplete" in incomplete_merge.message

    slurm_result = write_metrics_slurm_script_from_config(config_path=config_path, incomplete_only=True)
    script = Path(slurm_result["script_path"])
    assert script == tmp_path / "outputs" / "slurm" / "step03_run_metrics.slurm"
    assert slurm_result["metric_slurm_script_path"] == str(script)
    assert "#SBATCH --array=0" in script.read_text(encoding="utf-8")

    batch_output = Path(manifest.batches[0]["output_path"])
    batch_output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "event_id": ["ev1"],
            "station": ["STA1"],
            "component": ["Z"],
            "model": ["m1"],
            "band": ["1-2 sec"],
            "metric": ["PGA"],
            "value_obs": [2.0],
            "value_syn": [1.0],
            "log2_residual": [1.0],
        }
    ).to_csv(batch_output, index=False)

    ready_to_merge = metric_batch_merge_readiness_from_config(config_path=config_path)
    assert ready_to_merge.should_run is True
    assert ready_to_merge.reason == "missing_outputs"
    assert "metric_batch_0000_path" in set(ready_to_merge.status_frame()["name"])

    merge_result = merge_metric_batches_from_config(config_path=config_path)

    merged = pd.read_parquet(merge_result["metric_rows"])
    assert Path(merge_result["metric_rows"]) == tables / "metric_rows.parquet"
    assert merge_result["metric_rows_path"] == merge_result["metric_rows"]
    assert merge_result["metric_manifest_path"] == merge_result["manifest"]
    assert merged.loc[0, "station"] == "STA1"

    ready_for_outputs = metric_outputs_readiness_from_config(config_path=config_path)
    assert ready_for_outputs.should_run is True
    assert ready_for_outputs.reason == "missing_outputs"
    assert {"metrics_long_path", "path_table_path", "path_summary_path"}.issubset(
        set(ready_for_outputs.status_frame()["name"])
    )

    complete_slurm = write_metrics_slurm_script_from_config(config_path=config_path, incomplete_only=True)
    assert complete_slurm["all_complete"] is True
    assert complete_slurm["script_path"] == ""
    assert complete_slurm["metric_slurm_script_path"] == ""


def test_metric_merge_preserves_text_identifiers_for_parquet(tmp_path) -> None:
    """Merging CSV batches should keep station IDs textual for parquet output."""

    batch_a = tmp_path / "batch_a.csv"
    batch_b = tmp_path / "batch_b.csv"
    manifest_path = tmp_path / "manifest.json"
    pd.DataFrame(
        {
            "event_id": ["e1"],
            "station": ["00000"],
            "component": ["Z"],
            "metric_group": ["amplitude"],
            "metric": ["PGA"],
            "value_obs": [1.0],
        }
    ).to_csv(batch_a, index=False)
    pd.DataFrame(
        {
            "event_id": ["e2"],
            "station": [637],
            "component": ["Z"],
            "metric_group": ["amplitude"],
            "metric": ["PGA"],
            "value_obs": [2.0],
        }
    ).to_csv(batch_b, index=False)
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "qc_table": "",
                "tasks": [],
                "batches": [
                    {"batch_index": 0, "task_indices": [], "output_path": str(batch_a)},
                    {"batch_index": 1, "task_indices": [], "output_path": str(batch_b)},
                ],
            }
        ),
        encoding="utf-8",
    )

    merged_path = merge_batch_outputs(manifest_path, tmp_path / "merged.parquet")
    merged = pd.read_parquet(merged_path)

    assert merged["station"].tolist() == ["00000", "637"]


def test_metric_merge_accepts_output_directory(tmp_path) -> None:
    """Directory-style metric merge outputs should write the standard table."""

    batch = tmp_path / "batch.csv"
    output_dir = tmp_path / "tables"
    manifest_path = tmp_path / "manifest.json"
    output_dir.mkdir()
    pd.DataFrame(
        {
            "event_id": ["e1"],
            "station": ["ABC"],
            "component": ["Z"],
            "metric_group": ["amplitude"],
            "metric": ["PGA"],
            "value_obs": [1.0],
        }
    ).to_csv(batch, index=False)
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "qc_table": "",
                "tasks": [],
                "batches": [{"batch_index": 0, "task_indices": [], "output_path": str(batch)}],
            }
        ),
        encoding="utf-8",
    )

    merged_path = merge_batch_outputs(manifest_path, output_dir)
    merged = pd.read_parquet(merged_path)

    assert merged_path == output_dir / "metric_rows.parquet"
    assert merged["metric"].tolist() == ["PGA"]


def test_metric_batch_merge_streams_without_dataframe_concat(tmp_path, monkeypatch) -> None:
    """Large metric batch merges should not materialize all batches before writing."""

    batch_a = tmp_path / "batch_a.csv"
    batch_b = tmp_path / "batch_b.csv"
    manifest_path = tmp_path / "manifest.json"
    pd.DataFrame(
        {
            "event_id": ["e1"],
            "station": ["ABC"],
            "metric": ["PGA"],
            "value_obs": [1.0],
        }
    ).to_csv(batch_a, index=False)
    pd.DataFrame(
        {
            "event_id": ["e2"],
            "station": [637],
            "metric": ["PGV"],
            "value_obs": [2.0],
            "extra_note": ["later-column"],
        }
    ).to_csv(batch_b, index=False)
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "qc_table": "",
                "tasks": [],
                "batches": [
                    {"batch_index": 0, "task_indices": [], "output_path": str(batch_a)},
                    {"batch_index": 1, "task_indices": [], "output_path": str(batch_b)},
                ],
            }
        ),
        encoding="utf-8",
    )

    def fail_concat(*_args, **_kwargs):  # noqa: ANN202
        raise AssertionError("merge_batch_outputs should stream batch tables instead of concatenating them")

    def fail_full_batch_read(*_args, **_kwargs):  # noqa: ANN202
        raise AssertionError("merge_batch_outputs should stream chunks instead of full-reading each batch")

    monkeypatch.setattr(pd, "concat", fail_concat)
    monkeypatch.setattr(metric_execution, "_read_table", fail_full_batch_read)

    merged_path = merge_batch_outputs(manifest_path, tmp_path / "merged.parquet")
    monkeypatch.undo()
    merged = pd.read_parquet(merged_path)

    assert merged["event_id"].tolist() == ["e1", "e2"]
    assert merged["station"].tolist() == ["ABC", "637"]
    assert pd.isna(merged.loc[0, "extra_note"])
    assert merged.loc[1, "extra_note"] == "later-column"


def test_metric_batch_merge_requires_pyarrow_for_parquet_batches(tmp_path, monkeypatch) -> None:
    """Parquet metric batch merges should not fall back to full pandas reads."""

    batch = tmp_path / "batch.parquet"
    batch.write_bytes(b"not a real parquet file")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "qc_table": "",
                "tasks": [],
                "batches": [{"batch_index": 0, "task_indices": [], "output_path": str(batch)}],
            }
        ),
        encoding="utf-8",
    )
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: ANN001, ANN002
        if name == "pyarrow.parquet" or name == "pyarrow":
            raise ImportError("pyarrow unavailable for test")
        return real_import(name, globals, locals, fromlist, level)

    def fail_full_parquet_read(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise AssertionError("metric batch merges must not full-read parquet fallback data")

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(pd, "read_parquet", fail_full_parquet_read)

    with pytest.raises(RuntimeError, match="pyarrow is required"):
        merge_batch_outputs(manifest_path, tmp_path / "merged.csv")


def test_metric_row_parquet_write_normalizes_mixed_text_columns(tmp_path) -> None:
    """Metric parquet writes should not fail on mixed object identifier columns."""

    output = write_metric_rows(
        pd.DataFrame(
            {
                "event_id": ["e1", "e2"],
                "station": ["ABC", 637],
                "component": ["Z", "R"],
                "metric_group": ["amplitude", "amplitude"],
                "metric": ["PGA", "PGV"],
                "value_obs": [1.0, 2.0],
            }
        ),
        tmp_path / "metrics.parquet",
    )
    rows = pd.read_parquet(output)

    assert rows["station"].tolist() == ["ABC", "637"]


def test_metric_manifest_orders_tasks_for_waveform_cache_reuse(tmp_path) -> None:
    """Manifest writing should keep tasks with the same loaded waveforms adjacent."""

    tasks = [
        MetricWorkflowTask("task-b", "e1", "BBB", "Z", obs_waveform_path="obs_b.pkl", syn_waveform_path="syn_b.asdf", period_min_s=2.0, period_max_s=3.0),
        MetricWorkflowTask("task-a2", "e1", "AAA", "Z", obs_waveform_path="obs_a.pkl", syn_waveform_path="syn_a.asdf", period_min_s=3.0, period_max_s=5.0),
        MetricWorkflowTask("task-a1", "e1", "AAA", "Z", obs_waveform_path="obs_a.pkl", syn_waveform_path="syn_a.asdf", period_min_s=1.0, period_max_s=2.0),
    ]

    manifest = write_task_manifest(
        tasks,
        tmp_path / "manifest.json",
        output_dir=tmp_path / "batches",
        batch_size=2,
        planning_metadata={
            "planning_policy": "passing_observed_synthetic_qc_pairs",
            "require_passing_qc_pairs": True,
        },
    )
    parsed = read_task_manifest(manifest.manifest_path)

    assert [task.task_id for task in parsed.tasks] == ["task-a1", "task-a2", "task-b"]
    assert parsed.batches[0]["task_indices"] == [0, 1]


def test_metric_manifest_resolves_repo_relative_paths_from_slurm_workdir(tmp_path, monkeypatch) -> None:
    """Batch jobs should resolve repo-relative manifest paths outside the repo cwd."""

    repo = tmp_path / "repo"
    tables = repo / "runs" / "outputs" / "tables"
    batch_dir = repo / "runs" / "outputs" / "metric_batches"
    tables.mkdir(parents=True)
    batch_dir.mkdir(parents=True)
    qc_table = tables / "qc_inventory_overlap.parquet"
    qc_table.write_bytes(b"parquet placeholder")
    manifest_path = tables / "metric_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "qc_table": "runs/outputs/tables/qc_inventory_overlap.parquet",
                "tasks": [],
                "batches": [
                    {
                        "batch_index": 0,
                        "task_indices": [],
                        "output_path": "runs/outputs/metric_batches/metrics_batch_0000.csv",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    outside = tmp_path / "slurm-workdir"
    outside.mkdir()
    monkeypatch.chdir(outside)

    manifest = read_task_manifest(manifest_path)

    assert manifest.qc_table == str(qc_table)
    assert manifest.batches[0]["output_path"] == str(batch_dir / "metrics_batch_0000.csv")


def test_metric_manifest_waveform_cache_rewrites_paths_and_runs_batches(tmp_path) -> None:
    """Cached manifests should point at reusable .npz traces and run normally."""

    dt = 0.01
    time = np.arange(0.0, 3.0, dt)
    obs_path = tmp_path / "source_obs.npz"
    syn_path = tmp_path / "source_syn.npz"
    _write_npz_waveform(obs_path, 2.0 * np.sin(2.0 * np.pi * time), station="ABC", channel="HNZ", sampling_rate=1.0 / dt)
    _write_npz_waveform(syn_path, np.sin(2.0 * np.pi * time), station="ABC", channel="HNZ", sampling_rate=1.0 / dt)
    tasks = [
        MetricWorkflowTask(
            "cache-a",
            "e1",
            "ABC",
            "Z",
            obs_waveform_path=str(obs_path),
            syn_waveform_path=str(syn_path),
            metrics=("PGA",),
            transforms=("log2_residual",),
        ),
        MetricWorkflowTask(
            "cache-b",
            "e1",
            "ABC",
            "Z",
            obs_waveform_path=str(obs_path),
            syn_waveform_path=str(syn_path),
            metrics=("PGV",),
            transforms=("log2_residual",),
        ),
    ]
    manifest = write_task_manifest(
        tasks,
        tmp_path / "manifest.json",
        output_dir=tmp_path / "batches",
        batch_size=2,
        planning_metadata={
            "planning_policy": "passing_observed_synthetic_qc_pairs",
            "require_passing_qc_pairs": True,
        },
    )

    result = cache_metric_manifest_waveforms(
        manifest.manifest_path,
        tmp_path / "cached_manifest.json",
        cache_root=tmp_path / "cache",
        batch_output_dir=tmp_path / "cached_batches",
    )

    assert result.materialized_files == 2
    assert result.in_memory_reuses == 2
    assert result.metric_manifest_cached_path == tmp_path / "cached_manifest.json"
    assert result.metric_ready_waveform_cache_root == tmp_path / "cache"
    assert result.metric_batches_cached_dir == tmp_path / "cached_batches"
    status = result.status_frame()
    assert status["name"].tolist() == [
        "metric_manifest_cached_path",
        "metric_ready_waveform_cache_root",
        "metric_batches_cached_dir",
    ]
    assert status["artifact"].tolist() == [
        "metric_manifest_cached",
        "metric_ready_waveform_cache",
        "metric_batches_cached",
    ]
    assert status["artifact_role"].tolist() == ["manifest", "cache", "batch_output_dir"]
    assert status["status"].tolist() == ["ready", "ready", "ready"]
    assert status["artifact_label"].tolist() == [
        "cached metric manifest",
        "metric-ready waveform cache",
        "cached metric batch output directory",
    ]
    assert status["resolved_path"].tolist() == status["path"].tolist()
    assert status["exists"].tolist() == [True, True, True]
    assert status["rows"].tolist() == [2, 4, 1]
    cached_manifest = read_task_manifest(result.manifest.manifest_path)
    assert len(cached_manifest.tasks) == 2
    assert cached_manifest.planning_metadata["planning_policy"] == "passing_observed_synthetic_qc_pairs"
    assert bool(cached_manifest.status_frame().loc[0, "require_passing_qc_pairs"]) is True
    assert cached_manifest.tasks[0].obs_waveform_path.endswith(".npz")
    assert cached_manifest.tasks[0].obs_waveform_path != str(obs_path)
    assert cached_manifest.tasks[0].obs_waveform_path == cached_manifest.tasks[1].obs_waveform_path
    assert Path(cached_manifest.batches[0]["output_path"]).parent == tmp_path / "cached_batches"

    batch_output = run_manifest_batch(cached_manifest, batch_index=0)
    rows = pd.read_csv(batch_output)
    assert set(rows["metric"]) == {"PGA", "PGV"}

    resumed = cache_metric_manifest_waveforms(
        manifest.manifest_path,
        tmp_path / "cached_manifest_resumed.json",
        cache_root=tmp_path / "cache",
        batch_output_dir=tmp_path / "cached_batches_resumed",
    )
    assert resumed.materialized_files == 0
    assert resumed.reused_files == 2


def test_metric_workflow_applies_configured_lowpass_before_metrics(tmp_path) -> None:
    """Configured waveform lowpass should run before metric calculations."""

    dt = 0.005
    time = np.arange(0.0, 8.0, dt)
    comparable_signal = np.sin(2.0 * np.pi * 0.5 * time)
    high_frequency_observed = 10.0 * np.sin(2.0 * np.pi * 8.0 * time)
    observed = comparable_signal + high_frequency_observed
    synthetic = comparable_signal
    obs_path = tmp_path / "obs_noisy.npz"
    syn_path = tmp_path / "syn_clean.npz"
    _write_npz_waveform(obs_path, observed, station="ABC", channel="HNZ", sampling_rate=1.0 / dt)
    _write_npz_waveform(syn_path, synthetic, station="ABC", channel="HNZ", sampling_rate=1.0 / dt)
    task_kwargs = {
        "task_id": "lowpass-test",
        "event_id": "e1",
        "station": "ABC",
        "component": "Z",
        "model": "m1",
        "passband": "",
        "obs_waveform_path": str(obs_path),
        "syn_waveform_path": str(syn_path),
        "dt": dt,
        "metrics": ("PGA",),
        "transforms": ("log2_residual",),
        "output_mode": "full",
    }
    unfiltered_task = MetricWorkflowTask(**task_kwargs)
    filtered_task = MetricWorkflowTask(**task_kwargs, waveform_lowpass_hz=1.0, waveform_filter_order=4)

    assert filtered_task.waveform_lowpass_hz == 1.0
    serialized = filtered_task.to_dict()
    assert serialized["waveform_lowpass_hz"] == 1.0
    round_tripped = MetricWorkflowTask.from_dict(serialized)
    assert round_tripped.waveform_lowpass_hz == 1.0
    unfiltered_rows = run_metric_tasks([unfiltered_task])
    filtered_rows = run_metric_tasks([filtered_task])

    unfiltered_pga = float(unfiltered_rows.loc[unfiltered_rows["metric"].eq("PGA"), "value_obs"].iloc[0])
    filtered_pga = float(filtered_rows.loc[filtered_rows["metric"].eq("PGA"), "value_obs"].iloc[0])
    synthetic_pga = float(filtered_rows.loc[filtered_rows["metric"].eq("PGA"), "value_syn"].iloc[0])
    assert unfiltered_pga > 5.0
    assert filtered_pga == pytest.approx(synthetic_pga, rel=0.15)


def test_metric_workflow_uses_qc_valid_sample_window_for_peak_metrics(tmp_path) -> None:
    """QC valid windows should keep edge transients out of peak metrics."""

    samples = np.ones(200, dtype=float)
    observed = samples.copy()
    observed[:10] = 100.0
    synthetic = samples.copy()
    obs_path = tmp_path / "obs_spike.npz"
    syn_path = tmp_path / "syn_clean.npz"
    _write_npz_waveform(obs_path, observed, station="ABC", channel="HNZ", sampling_rate=20.0)
    _write_npz_waveform(syn_path, synthetic, station="ABC", channel="HNZ", sampling_rate=20.0)
    task = MetricWorkflowTask(
        task_id="valid-window-test",
        event_id="e1",
        station="ABC",
        component="Z",
        model="m1",
        passband="",
        obs_waveform_path=str(obs_path),
        syn_waveform_path=str(syn_path),
        dt=0.05,
        metrics=("PGA",),
        transforms=("log2_residual",),
        output_mode="full",
    )
    qc_table = pd.DataFrame(
        [
            {
                "source": "observed",
                "event_id": "e1",
                "station": "ABC",
                "component": "Z",
                "passband": "",
                "metric_group": "amplitude",
                "metric": "PGA",
                "period_s": np.nan,
                "qc_status": "pass",
                "qc_reason": "",
                "valid_start_sample": 20,
                "valid_end_sample": 200,
            },
            {
                "source": "synthetic",
                "event_id": "e1",
                "station": "ABC",
                "component": "Z",
                "passband": "",
                "metric_group": "amplitude",
                "metric": "PGA",
                "period_s": np.nan,
                "qc_status": "pass",
                "qc_reason": "",
                "valid_start_sample": 0,
                "valid_end_sample": 200,
            },
        ]
    )

    unmasked_rows = run_metric_tasks([task])
    masked_rows = run_metric_tasks([task], qc_table=qc_table)

    assert float(unmasked_rows.loc[0, "value_obs"]) == pytest.approx(100.0)
    assert float(masked_rows.loc[0, "value_obs"]) == pytest.approx(1.0)
    assert float(masked_rows.loc[0, "value_syn"]) == pytest.approx(1.0)
    assert float(masked_rows.loc[0, "log2_residual"]) == pytest.approx(0.0)


def test_pair_only_metrics_resample_when_sample_intervals_differ(tmp_path) -> None:
    """Pair-only metrics should resample mismatched pairs before calculation."""

    obs_path = tmp_path / "obs_dt_0p05.npz"
    syn_path = tmp_path / "syn_dt_0p1.npz"
    _write_npz_waveform(
        obs_path,
        np.sin(2.0 * np.pi * 1.0 * np.arange(0.0, 10.0, 0.05)),
        station="ABC",
        channel="HNZ",
        sampling_rate=20.0,
    )
    _write_npz_waveform(
        syn_path,
        np.sin(2.0 * np.pi * 1.0 * np.arange(0.0, 10.0, 0.1)),
        station="ABC",
        channel="HNZ",
        sampling_rate=10.0,
    )
    task = MetricWorkflowTask(
        task_id="dt-mismatch-test",
        event_id="e1",
        station="ABC",
        component="Z",
        model="m1",
        passband="",
        obs_waveform_path=str(obs_path),
        syn_waveform_path=str(syn_path),
        dt=0.05,
        metrics=("original_cc",),
        transforms=(),
        output_mode="full",
    )

    rows = run_metric_tasks([task])

    assert len(rows) == 1
    row = rows.iloc[0]
    assert row["metric"] == "original_cc"
    assert row["value"] == pytest.approx(1.0, abs=0.02)
    assert row["obs_qc_status"] == "pass"
    assert row["syn_qc_status"] == "pass"
    assert row["comparison_qc_status"] == "pass"
    assert row["comparison_qc_reason"] == ""


def test_metric_workflow_can_use_bounded_traveltime_delay_method(tmp_path) -> None:
    """Metric tasks should preserve and apply the bounded delay method option."""

    dt = 0.01
    time = np.arange(0.0, 20.0, dt)

    def packet(center_s: float, amplitude: float, width_s: float = 0.45) -> np.ndarray:
        envelope = np.exp(-0.5 * ((time - center_s) / width_s) ** 2)
        return amplitude * envelope * np.sin(2.0 * np.pi * 1.0 * (time - center_s))

    observed = packet(4.0, 0.6) + packet(10.0, 1.4)
    synthetic = packet(4.2, 0.6) + packet(9.05, 1.6)
    obs_path = tmp_path / "obs_packets.npz"
    syn_path = tmp_path / "syn_packets.npz"
    _write_npz_waveform(obs_path, observed, station="ABC", channel="HNZ", sampling_rate=1.0 / dt)
    _write_npz_waveform(syn_path, synthetic, station="ABC", channel="HNZ", sampling_rate=1.0 / dt)
    task_kwargs = {
        "task_id": "delay-method-test",
        "event_id": "e1",
        "station": "ABC",
        "component": "Z",
        "model": "m1",
        "passband": "1-2 sec",
        "obs_waveform_path": str(obs_path),
        "syn_waveform_path": str(syn_path),
        "dt": dt,
        "period_min_s": 1.0,
        "period_max_s": 2.0,
        "metrics": ("traveltime_delay",),
        "transforms": (),
        "output_mode": "full",
        "use_qc": False,
    }
    legacy_task = MetricWorkflowTask(**task_kwargs)
    bounded_task = MetricWorkflowTask(**task_kwargs, delay_method="bounded")

    assert MetricWorkflowTask.from_dict(bounded_task.to_dict()).delay_method == "bounded"
    rows = run_metric_tasks([legacy_task, bounded_task])

    values = rows["value"].to_numpy(dtype=float)
    assert values[0] < -0.5
    assert abs(values[1]) < abs(values[0])
    assert abs(values[1]) <= 0.5 + dt


def test_metric_workflow_uses_phasenet_cycle_corrected_delay(tmp_path) -> None:
    """PhaseNet-cycle delay should set pair metric values and retain pick metadata."""

    dt = 0.01
    time = np.arange(0.0, 8.0, dt)
    envelope = np.exp(-0.5 * ((time - 4.0) / 1.0) ** 2)
    observed = envelope * np.sin(2.0 * np.pi * 1.0 * time)
    synthetic = np.interp(time - 0.25, time, observed, left=0.0, right=0.0)
    obs_path = tmp_path / "obs_cycle.npz"
    syn_path = tmp_path / "syn_cycle.npz"
    _write_npz_waveform(obs_path, observed, station="ABC", channel="HNZ", sampling_rate=1.0 / dt)
    _write_npz_waveform(syn_path, synthetic, station="ABC", channel="HNZ", sampling_rate=1.0 / dt)
    task = MetricWorkflowTask(
        task_id="phasenet-cycle-test",
        event_id="e1",
        station="ABC",
        component="Z",
        model="m1",
        passband="1-2 sec",
        obs_waveform_path=str(obs_path),
        syn_waveform_path=str(syn_path),
        dt=dt,
        period_min_s=1.0,
        period_max_s=2.0,
        metrics=("traveltime_delay", "delay_corrected_cc"),
        transforms=(),
        output_mode="full",
        delay_method="phasenet_cycle",
        obs_p_pick_rel_s=2.0,
        syn_p_pick_rel_s=3.25,
        obs_p_pick_probability=0.4,
        syn_p_pick_probability=0.5,
        obs_p_pick_provenance="phasenet",
        syn_p_pick_provenance="phasenet",
        use_qc=False,
    )

    rows = run_metric_tasks([task])
    by_metric = rows.set_index("metric")

    assert by_metric.loc["traveltime_delay", "value"] == pytest.approx(0.25, abs=dt)
    assert by_metric.loc["traveltime_delay", "phasenet_traveltime_delay_s"] == pytest.approx(1.25)
    assert by_metric.loc["delay_corrected_cc", "value"] > 0.98
    assert by_metric.loc["delay_corrected_cc", "phasenet_cycle_corrected_cc"] > 0.98
    assert by_metric.loc["traveltime_delay", "obs_p_pick_provenance"] == "phasenet"


def test_metric_plan_attaches_arrival_pick_catalog_with_component_fallback(tmp_path) -> None:
    """Planning should attach exact picks or inherited station-component picks."""

    obs_inventory = pd.DataFrame(
        {
            "source": ["observed"],
            "event_id": ["e1"],
            "station": ["ABC"],
            "component": ["R"],
            "waveform_path": ["obs.npz"],
            "dt": [0.01],
        }
    )
    syn_inventory = pd.DataFrame(
        {
            "source": ["synthetic"],
            "event_id": ["e1"],
            "station": ["ABC"],
            "component": ["R"],
            "model": ["m1"],
            "waveform_path": ["syn.npz"],
            "dt": [0.01],
        }
    )
    picks = pd.DataFrame(
        [
            {
                "source": "observed",
                "event_id": "e1",
                "station": "ABC",
                "component": "Z",
                "phase": "P",
                "pick_time_abs": "2026-01-01T00:00:01",
                "pick_time_rel_s": 1.0,
                "probability": 0.3,
                "method": "phasenet",
            },
            {
                "source": "synthetic",
                "event_id": "e1",
                "station": "ABC",
                "component": "T",
                "phase": "P",
                "pick_time_abs": "2026-01-01T00:00:02",
                "pick_time_rel_s": 2.0,
                "probability": 0.7,
                "method": "phasenet",
            },
        ]
    )
    plan = MetricPlan(
        metrics=("traveltime_delay",),
        passbands=((1.0, 2.0),),
        components=("R",),
        models=("m1",),
        output_mode="full",
        delay_method="phasenet_cycle",
    )

    tasks = plan_metric_tasks(obs_inventory, syn_inventory, plan=plan, use_qc=False, arrival_pick_catalog=picks)

    assert len(tasks) == 1
    task = tasks[0]
    assert task.obs_p_pick_rel_s == pytest.approx(1.0)
    assert task.syn_p_pick_rel_s == pytest.approx(2.0)
    assert task.obs_p_pick_provenance == "phasenet:component:Z"
    assert task.syn_p_pick_provenance == "phasenet:component:T"


def test_slurm_settings_from_config_requires_python_command() -> None:
    """SLURM config parsing should fail clearly without a Python command."""

    empty = SpatialVTKConfig.empty(root_dir=".")
    with pytest.raises(ValueError, match="python_command"):
        slurm_settings_from_config(empty)

    config = SpatialVTKConfig(empty.config_path, empty.root_dir, {"metrics": {"slurm": {"python_command": "python", "cpus": 4}}})
    settings = slurm_settings_from_config(config)
    assert settings.python_command == "python"
    assert settings.cpus_per_task == 4


def test_summarize_metric_tasks_reports_task_and_resource_estimates() -> None:
    """Metric task summaries should report counts and planning estimates."""

    tasks = pd.DataFrame(
        {
            "event_id": ["e1", "e1"],
            "station": ["S1", "S2"],
            "component": ["Z", "R"],
            "model": ["m1", "m1"],
            "passband": ["1-2 sec", "1-2 sec"],
            "metrics": ["PGA,PGV", "PGA,PGV"],
        }
    )

    summary = summarize_metric_tasks(tasks, seconds_per_task=30.0, memory_gb_per_task=1.5, cpus_per_task=2, parallel_tasks=2)
    rows = dict(zip(summary["Estimate"], summary["Value"]))

    assert rows["Metric tasks"] == "2"
    assert rows["Passband metric tasks"] == "2"
    assert rows["Spectral metric tasks"] == "0"
    assert rows["Approximate metric evaluations"] == "4"
    assert rows["Unique events"] == "1"
    assert rows["Unique stations"] == "2"
    assert rows["Components"] == "R, Z"
    assert rows["Models"] == "m1"
    assert rows["Passbands"] == "1-2 sec"
    assert rows["Spectral periods"] == "none"
    assert rows["Approximate CPU-hours"] == "0.033"
    assert rows["Memory per task"] == "1.5 GB"
    assert rows["Wall time at 2 parallel tasks"] == "30 sec"
    assert rows["Peak memory at 2 parallel tasks"] == "3 GB"


def test_summarize_metric_tasks_streams_path_backed_task_tables(tmp_path, monkeypatch) -> None:
    """Path-backed metric task summaries should avoid full task-table reads."""

    task_table = tmp_path / "metric_tasks.csv"
    pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "station": ["STA1", "STA2"],
            "component": ["R", "T"],
            "model": ["m1", "m1"],
            "passband": ["1-2 sec", "2-3 sec"],
            "metrics": ["['PGA','PGV']", "['PSA']"],
            "spectral_periods_s": ["", "1,2,3"],
            "obs_waveform_path": ["unused-a", "unused-b"],
            "syn_waveform_path": ["unused-a", "unused-b"],
        }
    ).to_csv(task_table, index=False)

    def fail_full_task_read(*_args, **_kwargs):  # noqa: ANN202
        raise AssertionError("summarize_metric_tasks should stream projected task columns")

    monkeypatch.setattr(metric_tasks_module, "_read_table", fail_full_task_read)

    summary = summarize_metric_tasks(task_table, seconds_per_task=10.0)
    rows = dict(zip(summary["Estimate"], summary["Value"]))

    assert rows["Metric tasks"] == "2"
    assert rows["Passband metric tasks"] == "1"
    assert rows["Spectral metric tasks"] == "1"
    assert rows["Approximate metric evaluations"] == "3"
    assert rows["Unique events"] == "2"
    assert rows["Components"] == "R, T"
    assert rows["Passbands"] == "1-2 sec"
    assert rows["Spectral periods"] == "1, 2, 3"


def test_metric_workflow_outputs_feed_downstream_modules(tmp_path) -> None:
    """Workflow metric rows should feed enrichment, spatial summaries, dashboards, and maps."""

    dt = 0.01
    time = np.arange(0.0, 4.0, dt)
    obs_paths = []
    syn_paths = []
    stations = ["S1", "S2"]
    for index, station in enumerate(stations):
        obs_path = tmp_path / f"obs_{station}.npz"
        syn_path = tmp_path / f"syn_{station}.npz"
        observed = (1.0 + index) * np.sin(2.0 * np.pi * 1.0 * time)
        synthetic = (0.8 + index) * np.sin(2.0 * np.pi * 1.0 * time)
        _write_npz_waveform(obs_path, observed, station=station, channel="HNZ", sampling_rate=1.0 / dt)
        _write_npz_waveform(syn_path, synthetic, station=station, channel="HNZ", sampling_rate=1.0 / dt)
        obs_paths.append(obs_path)
        syn_paths.append(syn_path)

    obs_inventory = pd.DataFrame(
        {
            "event_id": ["e1", "e1"],
            "station": stations,
            "component": ["Z", "Z"],
            "waveform_path": obs_paths,
            "dt": [dt, dt],
        }
    )
    syn_inventory = pd.DataFrame(
        {
            "event_id": ["e1", "e1"],
            "station": stations,
            "component": ["Z", "Z"],
            "model": ["m1", "m1"],
            "waveform_path": syn_paths,
            "dt": [dt, dt],
        }
    )
    plan = MetricPlan(
        metrics=("PGA",),
        passbands=(),
        components=("Z",),
        models=("m1",),
        transforms=("log2_residual",),
        output_mode="full",
    )
    tasks = plan_metric_tasks(obs_inventory, syn_inventory, plan=plan)
    metric_rows = run_metric_tasks(tasks)
    assert {"metric", "value_obs", "value_syn", "log2_residual"} <= set(metric_rows.columns)

    events = pd.DataFrame({"event_id": ["e1"], "lat": [34.1], "lon": [-118.3], "magnitude": [4.2]})
    station_meta = pd.DataFrame(
        {
            "station": stations,
            "station_lat": [34.0, 34.2],
            "station_lon": [-118.5, -118.1],
            "network": ["AA", "AA"],
        }
    )
    prepared = prepare_metric_workflow_outputs(metric_rows, events=events, stations=station_meta)
    enriched = prepared["metrics_long"]
    assert {"residual", "distance_km", "azimuth_deg", "sta_lat", "sta_lon"} <= set(enriched.columns)
    assert enriched["residual"].notna().all()
    assert not prepared["path_table"].empty
    assert prepared["path_summary"]["n"].sum() == 2
    assert prepared["dashboard_summaries"]["model_metric_band"].loc[0, "n"] == 2

    written = write_metric_outputs(metric_rows, tmp_path / "downstream", events=events, stations=station_meta)
    assert written["metrics_long"].exists()
    assert written["path_table"].exists()
    assert written["path_summary"].exists()
    dashboard_metrics = load_dashboard_metric_dataset(written["dashboard_metrics"])
    assert len(dashboard_metrics) == 2

    figure = plot_event_residual_map(enriched, tmp_path / "workflow_residual_map.png", event_id="e1", metric="PGA", add_basemap=False)
    assert figure.exists()
    assert figure.stat().st_size > 0


def test_metric_workflow_outputs_project_path_backed_long_rows(tmp_path) -> None:
    """Downstream output prep should skip unused columns from long metric-row files."""

    metric_rows_path = tmp_path / "metric_rows.csv"
    pd.DataFrame(
        {
            "event_id": ["e1"],
            "station": ["STA"],
            "model": ["m1"],
            "component": ["Z"],
            "passband": ["1-2 sec"],
            "metric": ["PGA"],
            "value_obs": [4.0],
            "value_syn": [2.0],
            "log2_residual": [1.0],
            "event_lat": [34.1],
            "event_lon": [-118.3],
            "station_lat": [34.0],
            "station_lon": [-118.5],
            "unused_large_payload": ["x" * 1000],
        }
    ).to_csv(metric_rows_path, index=False)

    prepared = prepare_metric_workflow_outputs(metric_rows_path)
    metrics_long = prepared["metrics_long"]

    assert "unused_large_payload" not in metrics_long.columns
    assert {"distance_km", "azimuth_deg", "sta_lat", "sta_lon"} <= set(metrics_long.columns)
    assert "passband" in metric_workflow_output_input_columns()


def test_write_metric_outputs_uses_registered_dashboard_paths_when_configured(tmp_path) -> None:
    """Config-backed metric output writing should not put dashboards under tables."""

    clear_active_config()
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
    metric_rows = pd.DataFrame(
        {
            "event_id": ["e1"],
            "station": ["STA"],
            "model": ["m1"],
            "component": ["Z"],
            "band": ["1-2 sec"],
            "metric": ["PGA"],
            "value_obs": [4.0],
            "value_syn": [2.0],
            "log2_residual": [1.0],
            "residual": [1.0],
        }
    )
    try:
        written = write_metric_outputs(metric_rows, cfg=cfg)
    finally:
        clear_active_config()

    assert written["metrics_long"] == tmp_path / "outputs" / "tables" / "metrics_long.parquet"
    assert written["metrics_enriched"] == tmp_path / "outputs" / "tables" / "metrics_enriched.parquet"
    assert written["dashboard_metrics"] == tmp_path / "outputs" / "dashboards" / "metrics_dashboard"
    assert (tmp_path / "outputs" / "tables" / "metrics_enriched.parquet").exists()
    dashboard_metric_root = tmp_path / "outputs" / "dashboards" / "metrics_dashboard"
    assert not (dashboard_metric_root / "metrics_long.parquet").exists()
    assert list(dashboard_metric_root.glob("model=*/band=*/metric=*/part*.parquet"))
    assert (tmp_path / "outputs" / "dashboards" / "dashboard_summaries" / "model_metric_band.parquet").exists()
    assert not (tmp_path / "outputs" / "tables" / "dashboard_metrics").exists()
    assert cfg.root_dir == tmp_path

    clear_active_config()
    written_from_path = write_metric_outputs(metric_rows, cfg=config_path)
    assert written_from_path["metrics_long"] == tmp_path / "outputs" / "tables" / "metrics_long.parquet"
    assert written_from_path["dashboard_metrics"] == tmp_path / "outputs" / "dashboards" / "metrics_dashboard"


def test_write_metric_outputs_from_config_uses_registered_inputs_and_outputs(tmp_path) -> None:
    """Config-backed metric output helper should resolve standard tables."""

    clear_active_config()
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
    tables = tmp_path / "outputs" / "tables"
    tables.mkdir(parents=True)
    pd.DataFrame(
        {
            "event_id": ["e1"],
            "event_lat": [34.0],
            "event_lon": [-118.0],
        }
    ).to_csv(tables / "prepared_events.csv", index=False)
    pd.DataFrame(
        {
            "station": ["STA"],
            "lat": [34.1],
            "lon": [-118.1],
        }
    ).to_csv(tables / "prepared_stations.csv", index=False)
    pd.DataFrame(
        {
            "event_id": ["e1"],
            "station": ["STA"],
            "model": ["m1"],
            "component": ["Z"],
            "band": ["1-2 sec"],
            "metric": ["PGA"],
            "value_obs": [4.0],
            "value_syn": [2.0],
            "log2_residual": [1.0],
        }
    ).to_parquet(tables / "metric_rows.parquet", index=False)

    written = write_metric_outputs_from_config(config_path=config_path)

    assert Path(written["metrics_long"]) == tables / "metrics_long.parquet"
    assert Path(written["metrics_enriched"]) == tables / "metrics_enriched.parquet"
    assert Path(written["path_table"]) == tables / "path_table.parquet"
    assert Path(written["dashboard_metrics"]) == tmp_path / "outputs" / "dashboards" / "metrics_dashboard"
    assert (tables / "metrics_enriched.parquet").exists()
    assert (tmp_path / "outputs" / "dashboards" / "dashboard_summaries" / "model_metric_band.parquet").exists()


def test_summarize_metric_snapshot_tasks_from_config_writes_standard_tables(tmp_path) -> None:
    """Snapshot-backed tutorials should get task previews from a package helper."""

    clear_active_config()
    config_path = tmp_path / "spatial-vtk.yaml"
    snapshot_path = tmp_path / "inputs" / "metrics_snapshot.parquet"
    snapshot_path.parent.mkdir(parents=True)
    pd.DataFrame(
        {
            "event_id": ["e1", "e1", "e1"],
            "station": ["STA", "STA", "STB"],
            "component": ["Z", "Z", "R"],
            "model": ["m1", "m1", "m1"],
            "band": ["1-2 sec", "1-2 sec", "2-3 sec"],
            "metric": ["PGA", "PGV", "PGA"],
            "value_obs": [4.0, 3.0, 5.0],
            "value_syn": [2.0, 2.0, 2.5],
            "log2_residual": [1.0, 0.5, 1.0],
        }
    ).to_parquet(snapshot_path, index=False)
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
paths:
  metric_snapshot: {snapshot_path}
outputs:
  tables: outputs/tables
metrics:
  metrics: [PGA, PGV]
  transforms: [log2_residual]
  output_mode: full
""",
        encoding="utf-8",
    )

    result = summarize_metric_snapshot_tasks_from_config(config_path=config_path)

    tasks = pd.read_csv(result["metric_tasks_path"])
    estimate = pd.read_csv(result["metric_task_estimate_path"])
    assert result["task_count"] == 2
    assert set(tasks["station"]) == {"STA", "STB"}
    assert set(tasks["passband"]) == {"1-2 sec", "2-3 sec"}
    assert set(tasks["metrics"]) == {"PGA, PGV"}
    assert "Metric tasks" in set(estimate["Estimate"])


def test_summarize_metric_snapshot_tasks_from_config_accepts_notebook_context(tmp_path) -> None:
    """Notebook metric preview helpers should accept the shared run context."""

    clear_active_config()
    config_path = tmp_path / "spatial-vtk.yaml"
    snapshot_path = tmp_path / "inputs" / "metrics_snapshot.parquet"
    snapshot_path.parent.mkdir(parents=True)
    pd.DataFrame(
        {
            "event_id": ["e1", "e1"],
            "station": ["STA", "STA"],
            "component": ["Z", "Z"],
            "model": ["base", "base"],
            "band": ["1-2 sec", "1-2 sec"],
            "metric": ["PGA", "PGV"],
            "log2_residual": [1.0, 0.5],
        }
    ).to_parquet(snapshot_path, index=False)
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
paths:
  metric_snapshot: {snapshot_path}
outputs:
  tables: outputs/tables
metrics:
  metrics: [PGA, PGV]
  transforms: [log2_residual]
  output_mode: full
run_scenarios:
  tutorial:
    metrics:
      metrics: [PGA]
""",
        encoding="utf-8",
    )

    class Context:
        pass

    Context.config_path = config_path
    Context.run_scenario = "tutorial"

    result = summarize_metric_snapshot_tasks_from_config(context=Context())

    tasks = pd.read_csv(result["metric_tasks_path"])
    assert result["task_count"] == 1
    assert tasks["metrics"].tolist() == ["PGA"]


def test_write_metric_outputs_from_config_can_use_configured_snapshot(tmp_path) -> None:
    """Metric output helper should support tutorial snapshots without notebook path plumbing."""

    clear_active_config()
    config_path = tmp_path / "spatial-vtk.yaml"
    snapshot_path = tmp_path / "inputs" / "metrics_snapshot.parquet"
    snapshot_path.parent.mkdir(parents=True)
    pd.DataFrame(
        {
            "event_id": ["e1"],
            "station": ["STA"],
            "model": ["m1"],
            "component": ["Z"],
            "band": ["1-2 sec"],
            "metric": ["PGA"],
            "value_obs": [4.0],
            "value_syn": [2.0],
            "log2_residual": [1.0],
        }
    ).to_parquet(snapshot_path, index=False)
    config_path.write_text(
        f"""
project:
  root_dir: {tmp_path}
paths:
  metric_snapshot: {snapshot_path}
outputs:
  tables: outputs/tables
  dashboards: outputs/dashboards
""",
        encoding="utf-8",
    )
    tables = tmp_path / "outputs" / "tables"
    tables.mkdir(parents=True)
    pd.DataFrame(
        {
            "event_id": ["e1"],
            "event_lat": [34.0],
            "event_lon": [-118.0],
        }
    ).to_csv(tables / "prepared_events.csv", index=False)
    pd.DataFrame(
        {
            "station": ["STA"],
            "lat": [34.1],
            "lon": [-118.1],
        }
    ).to_csv(tables / "prepared_stations.csv", index=False)

    written = write_metric_outputs_from_config(config_path=config_path)

    assert Path(written["metrics_long"]) == tables / "metrics_long.parquet"
    assert Path(written["metrics_enriched"]) == tables / "metrics_enriched.parquet"
    assert Path(written["dashboard_metrics"]) == tmp_path / "outputs" / "dashboards" / "metrics_dashboard"
    assert (tables / "metrics_long.parquet").exists()
    assert (tables / "metrics_enriched.parquet").exists()


def _write_npz_waveform(path, samples, *, station: str, channel: str, sampling_rate: float) -> None:
    """Write one lightweight waveform fixture.

    Parameters
    ----------
    path
        Output ``.npz`` path.
    samples
        One-dimensional waveform samples.
    station, channel, sampling_rate
        Trace metadata.

    Returns
    -------
    None
        File is written in-place.
    """

    np.savez(
        path,
        data=np.asarray(samples, dtype=float)[:, np.newaxis],
        station=station,
        channels=np.array([channel]),
        sampling_rate=float(sampling_rate),
    )
