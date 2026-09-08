"""Scientific contracts for the separate lowpass spectral branch."""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from obspy import Trace, UTCDateTime
from scipy.signal import butter, sosfiltfilt

from spatial_vtk.io.plans import MetricPlan
from spatial_vtk.metrics.workflow.tasks import plan_metric_tasks, tasks_from_frame, tasks_to_frame
from spatial_vtk.metrics.workflow.run import _prepare_spectral_sides, calculate_task_rows


def inventories(tmp_path):
    rows = []
    for name, rate, start, scale in [('observed', 100, 0, 2), ('synthetic', 80, 0.13, 1)]:
        t = np.arange(0, 60, 1 / rate)
        trace = Trace(scale * (np.sin(2 * np.pi * .25 * (t + start)) + .01 * np.sin(2 * np.pi * .6 * t)),
                      header=dict(station='ABC', channel='HNT', sampling_rate=rate, starttime=UTCDateTime(start)))
        trace.data = trace.data.astype(np.float32)  # Real MiniSEED inputs preserve this precision through tapering.
        path = tmp_path / (name + '.mseed')
        trace.write(str(path), format='MSEED')
        rows.append(pd.DataFrame([dict(event_id='e1', station='ABC', component='T', model='m', sampling_rate=rate,
                     waveform_path=str(tmp_path / 'processed-do-not-read.mseed'), raw_waveform_path=str(path))]))
    return rows


def plan():
    return MetricPlan(metrics=('PGA', 'PSA', 'FAS'), passbands=((1, 2), (2, 3)),
                      components=('T',), models=('m',), synthetic_max_frequency_hz=1,
                      spectral_periods_s=(1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5), transforms=('log2_residual',))


def test_spectral_tasks_are_unique_raw_and_strictly_inside_simulation_limit(tmp_path):
    tasks = plan_metric_tasks(*inventories(tmp_path), plan=plan())
    assert len(tasks) == 3
    assert [t.metrics for t in tasks] == [('PGA',), ('PGA',), ('PSA', 'FAS')]
    spec = tasks[-1]
    assert spec.spectral_periods_s == tuple(np.arange(1.5, 5.1, .5))
    assert spec.period_min_s is None and spec.period_max_s is None
    assert spec.disable_spectral_relative_amplitude_qc
    assert tasks_from_frame(tasks_to_frame(tasks))[-1] == spec
    rows = calculate_task_rows(spec)
    assert len(rows) == 16
    assert all(row['comparison_qc_status'] == 'pass' for row in rows)
    assert all(np.isfinite(row['log2_residual']) for row in rows)
    for metric in ('PSA', 'FAS'):
        with pytest.raises(ValueError, match='strictly above'):
            calculate_task_rows(replace(spec, metrics=(metric,), spectral_periods_s=(1.0,), use_qc=False))
    with pytest.raises(ValueError, match='Replan'):
        calculate_task_rows(replace(spec, period_min_s=1, period_max_s=2))
    with pytest.raises(ValueError, match='No PSA/FAS periods'):
        plan_metric_tasks(*inventories(tmp_path), plan=replace(plan(), spectral_periods_s=(.5, 1)))


def test_lowpass_common_grid_matches_research_sequence_and_retains_long_period_energy(tmp_path):
    from obspy import read
    task = plan_metric_tasks(*inventories(tmp_path), plan=plan())[-1]
    obs, syn, audit = _prepare_spectral_sides(task, {})
    assert obs.dt == syn.dt == .04
    assert obs.start_s == syn.start_s == .16
    assert obs.data.shape == syn.data.shape
    for path, actual in [(task.obs_waveform_path, obs), (task.syn_waveform_path, syn)]:
        raw = read(path)[0]
        reference = raw.copy().detrend('demean').taper(max_percentage=.05, type='cosine')
        filtered = sosfiltfilt(butter(4, 1., btype='lowpass', fs=raw.stats.sampling_rate, output='sos'), reference.data.astype(float))
        expected = np.interp(actual.start_s + np.arange(actual.data.size) / 25,
                             float(raw.stats.starttime) + np.arange(raw.stats.npts) * raw.stats.delta, filtered)
        np.testing.assert_allclose(actual.data, expected, rtol=1e-12, atol=1e-12)
    assert np.std(obs.data) > 1  # 4-second energy would be removed by a 1–2 s bandpass.
    assert audit['spectral_lowpass_obs_hz'] == audit['spectral_lowpass_syn_hz'] == 1
