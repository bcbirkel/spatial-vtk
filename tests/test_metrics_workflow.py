from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spatial_vtk.config.runtime import SpatialVTKConfig
from spatial_vtk.io.plans import MetricPlan
from spatial_vtk.metrics.workflow import (
    SlurmSettings,
    merge_batch_outputs,
    plan_metric_tasks,
    prepare_metric_workflow_outputs,
    read_task_manifest,
    run_manifest_batch,
    run_metric_tasks,
    slurm_settings_from_config,
    summarize_metric_tasks,
    write_metric_outputs,
    write_metrics_slurm_script,
    write_task_manifest,
    MetricWorkflowTask,
)
from spatial_vtk.spatial.map.path import plot_event_residual_map
from spatial_vtk.visualize.dashboard import available_dashboard_value_columns, build_dashboard_summaries, load_dashboard_metric_dataset


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
    assert len(tasks) == 1
    assert tasks[0].metrics == ("PGA", "PSA", "original_cc")

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

    batch_output = run_manifest_batch(parsed, batch_index=0)
    assert batch_output.exists()
    merged_output = merge_batch_outputs(parsed, tmp_path / "merged.csv")
    merged = pd.read_csv(merged_output)
    assert merged.loc[0, "metric"] == "PGA"

    script = write_metrics_slurm_script(
        parsed.manifest_path,
        tmp_path / "run_metrics.slurm",
        SlurmSettings(python_command="python", environment_setup=("source activate spatial-vtk",), max_concurrent=2),
    )
    text = script.read_text(encoding="utf-8")
    assert "#SBATCH --array=0-0%2" in text
    assert "python -m spatial_vtk.metrics.workflow.execution" in text
    assert "source activate spatial-vtk" in text


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
