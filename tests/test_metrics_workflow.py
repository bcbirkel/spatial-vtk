from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from spatial_vtk.config.runtime import SpatialVTKConfig, clear_active_config
from spatial_vtk.io.plans import MetricPlan
from spatial_vtk.metrics.workflow import (
    SlurmSettings,
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
from spatial_vtk.metrics.plot import MetricFigureContext, plot_period_score_distribution
from spatial_vtk.spatial.map import plot_event_residual_map
from spatial_vtk.spatial.plot import boxplot, heatmap, scatterplot
from spatial_vtk.visualize.dashboard import available_dashboard_value_columns, build_dashboard_summaries, load_dashboard_metric_dataset


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
    pga_item = next(context.iter_metric_frames(passband="1-2 sec", components=["Z"], model="m1", split_psa_period=False))
    station_summary = context.station_summary_for_map(pga_item["df"])
    item_station_summary = context.station_summary_for_item(pga_item)
    item_station_grid = context.station_grid_for_item(pga_item)
    assert item_station_summary[["station", "log2_residual"]].to_dict("records") == station_summary[
        ["station", "log2_residual"]
    ].to_dict("records")
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

    generic_outputs = context.write_generic_metric_diagnostic_plots(
        _dummy_png_plot,
        _dummy_png_plot,
        _dummy_png_plot,
        _dummy_png_plot,
        passband="1-2 sec",
        components=["Z"],
        model="m1",
    )
    stems = {path.stem for path in generic_outputs}
    assert any(stem.startswith("scatterplot__pga") for stem in stems)
    assert any(stem.startswith("boxplot__pga") for stem in stems)
    assert any(stem.startswith("heatmap__pga") for stem in stems)
    assert any(stem.startswith("scatterplot__psa") for stem in stems)
    assert any(stem.startswith("boxplot__psa") for stem in stems)
    for path in generic_outputs:
        generic_sidecar = context.sidecar_output_dir / f"{path.stem}.csv"
        generic_metadata = context.sidecar_output_dir / f"{path.stem}.json"
        assert generic_sidecar.exists(), path.name
        assert generic_metadata.exists(), path.name
        metadata = json.loads(generic_metadata.read_text(encoding="utf-8"))
        assert metadata["plot_row_count"] >= metadata["written_row_count"] > 0
        assert metadata["source_row_count"] >= metadata["written_row_count"]


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
    assert any(
        call["base"] == "metric_by_model_map"
        and getattr(call["source_factory"], "__self__", None) is context
        and getattr(call["source_factory"], "__func__", None) is item_source_func
        for call in sheet_calls
    )
    assert any("log2_residual" in call["required"] for call in calls)


def test_generic_metric_diagnostics_split_residuals_by_model(tmp_path) -> None:
    """Generic residual diagnostics should not require notebook-local model loops."""

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

    outputs = context.write_generic_metric_diagnostic_plots(
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


def test_generic_metric_diagnostics_forward_boxplot_comparison_options(tmp_path) -> None:
    """Large-run generic diagnostics should expose tutorial comparison tables."""

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

    outputs = context.write_generic_metric_diagnostic_plots(
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

    manifest = write_task_manifest(tasks, tmp_path / "manifest.json", output_dir=tmp_path / "batches", batch_size=1)
    parsed = read_task_manifest(manifest.manifest_path)
    assert len(parsed.batches) == 1
    initial_status = metric_manifest_batch_status(parsed)
    assert initial_status.total_batches == 1
    assert initial_status.completed_count == 0
    assert initial_status.missing_batches == (0,)
    assert bool(initial_status.status_frame().loc[0, "all_complete"]) is False
    initial_readiness = metric_slurm_submission_readiness(initial_status)
    assert initial_readiness.should_run is True
    assert initial_readiness.reason == "incomplete_batches"
    assert "1 missing batch output" in initial_readiness.message
    assert bool(initial_readiness.status_frame().loc[0, "should_submit"]) is True

    batch_output = run_manifest_batch(parsed, batch_index=0)
    assert batch_output.exists()
    completed_status = metric_manifest_batch_status(parsed)
    assert completed_status.completed_batches == (0,)
    assert completed_status.missing_count == 0
    assert completed_status.all_complete
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
    assert plan_result["planned_output_path"] == str(manifest_path)
    assert plan_result["observed_metric_inventory_path"] == str(tables / "observed_metric_inventory.parquet")
    assert plan_result["synthetic_metric_inventory_path"] == str(tables / "synthetic_metric_inventory.parquet")
    assert plan_result["metric_qc_table_path"] == str(tables / "qc_inventory_overlap.parquet")
    assert len(manifest.tasks) == 1
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

    manifest = write_task_manifest(tasks, tmp_path / "manifest.json", output_dir=tmp_path / "batches", batch_size=2)
    parsed = read_task_manifest(manifest.manifest_path)

    assert [task.task_id for task in parsed.tasks] == ["task-a1", "task-a2", "task-b"]
    assert parsed.batches[0]["task_indices"] == [0, 1]


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
    manifest = write_task_manifest(tasks, tmp_path / "manifest.json", output_dir=tmp_path / "batches", batch_size=2)

    result = cache_metric_manifest_waveforms(
        manifest.manifest_path,
        tmp_path / "cached_manifest.json",
        cache_root=tmp_path / "cache",
        batch_output_dir=tmp_path / "cached_batches",
    )

    assert result.materialized_files == 2
    assert result.in_memory_reuses == 2
    cached_manifest = read_task_manifest(result.manifest.manifest_path)
    assert len(cached_manifest.tasks) == 2
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
    assert rows["Approximate metric evaluations"] == "4"
    assert rows["Unique events"] == "1"
    assert rows["Unique stations"] == "2"
    assert rows["Components"] == "R, Z"
    assert rows["Models"] == "m1"
    assert rows["Passbands"] == "1-2 sec"
    assert rows["Approximate CPU-hours"] == "0.033"
    assert rows["Memory per task"] == "1.5 GB"
    assert rows["Wall time at 2 parallel tasks"] == "30 sec"
    assert rows["Peak memory at 2 parallel tasks"] == "3 GB"


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


def test_write_metric_outputs_uses_registered_dashboard_paths_when_configured(tmp_path) -> None:
    """Config-backed metric output writing should not put dashboards under tables."""

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
    cfg = SpatialVTKConfig.from_file(config_path).activate()
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
        written = write_metric_outputs(metric_rows)
    finally:
        clear_active_config()

    assert written["metrics_long"] == tmp_path / "outputs" / "tables" / "metrics_long.parquet"
    assert written["metrics_enriched"] == tmp_path / "outputs" / "tables" / "metrics_enriched.parquet"
    assert written["dashboard_metrics"] == tmp_path / "outputs" / "dashboards" / "metrics_dashboard"
    assert (tmp_path / "outputs" / "tables" / "metrics_enriched.parquet").exists()
    assert (tmp_path / "outputs" / "dashboards" / "metrics_dashboard" / "metrics_long.parquet").exists()
    assert (tmp_path / "outputs" / "dashboards" / "dashboard_summaries" / "model_metric_band.parquet").exists()
    assert not (tmp_path / "outputs" / "tables" / "dashboard_metrics").exists()
    assert cfg.root_dir == tmp_path


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
