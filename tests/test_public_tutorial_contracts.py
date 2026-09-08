from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
import pytest

from spatial_vtk.tutorials import tutorial_root
from spatial_vtk.metrics.calculate.arrival_picks import find_phasenet_command, PhaseNetUnavailableError
from spatial_vtk.metrics.calculate.phasenet_adapter import (
    PhaseNetInputRecord, prepare_phasenet_numpy_inputs, normalize_phasenet_output, run_phasenet,
)


def test_root_discovery_and_explicit_override(tmp_path, monkeypatch):
    root = tmp_path / 'project'
    config = root / 'data/examples/configuration/example_spatial_vtk_config.yaml'
    config.parent.mkdir(parents=True)
    config.write_text('')
    notebooks = root / 'docs/examples'
    notebooks.mkdir(parents=True)
    monkeypatch.chdir(notebooks)
    monkeypatch.delenv('SVTK_PROJECT_ROOT', raising=False)
    assert tutorial_root() == root
    monkeypatch.setenv('SVTK_PROJECT_ROOT', str(tmp_path / 'missing'))
    with pytest.raises(FileNotFoundError, match='SVTK_PROJECT_ROOT'):
        tutorial_root()
    assert tutorial_root(root) == root


def test_en_z_channels_are_not_replaced_with_zeros(tmp_path):
    components = {key: {'data': np.full(20, i), 'sampling_rate': 100, 'starttime': '2020-01-01T00:00:00Z'} for i, key in enumerate(('E', 'N', 'Z'), 1)}
    records = prepare_phasenet_numpy_inputs([dict(event_id='e', station='s', components=components)], tmp_path)
    data = np.load(tmp_path / records[0].file_name)['data']
    np.testing.assert_array_equal(data[0], [1, 2, 3])
    assert records[0].components == ('E', 'N', 'Z')
    components['N']['starttime'] = '2020-01-01T00:00:01Z'
    with pytest.raises(ValueError, match='aligned start'):
        prepare_phasenet_numpy_inputs([dict(event_id='e', station='s', components=components)], tmp_path)


def test_sample_index_is_seconds_relative_to_event(tmp_path):
    record = PhaseNetInputRecord('input.npz', 'e', 's', 'observed', ('E', 'N', 'Z'), 100,
        '2020-01-01T00:00:10Z', '2020-01-01T00:00:00Z')
    path = tmp_path / 'picks.csv'
    pd.DataFrame([dict(file_name='input.npz', phase_type='P', phase_score=0.9, phase_index=250)]).to_csv(path, index=False)
    result = normalize_phasenet_output(path, [record])
    assert result.pick_time_rel_s.iloc[0] == 12.5
    pd.DataFrame([dict(file_name='unknown', phase_type='P', phase_score=0.9, phase_index=250)]).to_csv(path, index=False)
    with pytest.raises(ValueError, match='unknown input'):
        normalize_phasenet_output(path, [record])
    pd.DataFrame(columns=['wrong']).to_csv(path, index=False)
    with pytest.raises(ValueError, match='schema'):
        normalize_phasenet_output(path, [record])


def test_configured_backend_does_not_fall_back(monkeypatch):
    monkeypatch.setenv('SVTK_PHASENET_COMMAND', sys.executable)
    assert find_phasenet_command('/definitely/missing/picker') is None
    monkeypatch.delenv('SVTK_PHASENET_COMMAND')
    monkeypatch.delenv('VTK_PHASENET_COMMAND', raising=False)
    assert find_phasenet_command() is None


def test_external_process_contract(tmp_path):
    # This executable tests the subprocess protocol, not real neural inference.
    script = tmp_path / 'contract_backend.py'
    script.write_text('''import argparse
from pathlib import Path
p=argparse.ArgumentParser()
for name in ('data_dir','data_list','result_dir','result_fname','model_dir','min_p_prob','min_s_prob','format','sampling_rate','batch_size'):
    p.add_argument('--'+name)
a=p.parse_args()
assert a.format == 'numpy'
assert a.sampling_rate == '100.0'
Path(a.result_dir, a.result_fname+'.csv').write_text('file_name,phase_type,phase_score,phase_index\\n')
''')
    model = tmp_path / 'model'
    model.mkdir()
    (model / 'checkpoint').write_text('test fixture')
    result = run_phasenet(tmp_path, result_dir=tmp_path / 'results', model_dir=model,
        phasenet_command=f'{sys.executable} {script}', sampling_rate=100)
    assert result.name == 'picks.csv' and result.is_file()
    with pytest.raises(RuntimeError, match='Incompatible PhaseNet'):
        run_phasenet(tmp_path, result_dir=tmp_path / 'bad', model_dir=model,
            phasenet_command=sys.executable, sampling_rate=100)


def test_qc_map_accepts_prepared_coordinates():
    from spatial_vtk.qc import build_post_qc_record_table
    result = build_post_qc_record_table(pd.DataFrame([dict(event_id='e', station='s', lat=34., lon=-118.)]))
    assert result.sta_lat.iloc[0] == 34.
    assert result.sta_lon.iloc[0] == -118.


def test_basemap_opt_out_never_imports_tiles(monkeypatch):
    from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
    monkeypatch.setenv('SVTK_NO_BASEMAP', '1')
    assert add_contextily_basemap(None) == (False, 'disabled')


def test_single_period_execution_preserves_spectral_values():
    from spatial_vtk.metrics.workflow.run import _LoadedSide, _calculate_spectral_metric_rows
    from spatial_vtk.metrics.workflow.tasks import MetricWorkflowTask
    from spatial_vtk.metrics.calculate.gof import PSA, FAS
    # Deterministic unit-test waveform; the public tutorial uses real MiniSEED.
    samples = np.sin(np.arange(1000) * .031) + .1 * np.cos(np.arange(1000) * .11)
    periods = (1., 2., 3., 5.)
    task = MetricWorkflowTask('test', 'event', 'station', 'Z', spectral_periods_s=periods,
        transforms=('log2_residual',), use_qc=False)
    observed = _LoadedSide(samples, .01)
    synthetic = _LoadedSide(samples * .5, .01)
    for metric, calculate in [('PSA', PSA), ('FAS', FAS)]:
        rows = pd.DataFrame(_calculate_spectral_metric_rows(task, metric, observed, synthetic, {}, {}))
        expected = calculate(samples, .01, periods=periods)
        np.testing.assert_array_equal(rows.value_obs, expected)
        np.testing.assert_allclose(rows.value_syn, expected * .5)
        np.testing.assert_allclose(rows.log2_residual, 1.)


def test_corridor_map_accepts_prepared_coordinates():
    import matplotlib.pyplot as plt
    from shapely.geometry import box
    from spatial_vtk.spatial.map import plot_corridor_map
    corridors = pd.DataFrame({'corridor_geometry': [box(-118.2, 33.8, -117.8, 34.2)]})
    records = pd.DataFrame([dict(event_lon=-118., event_lat=34., lon=-117., lat=35.)])
    figure = plot_corridor_map(corridors, records_df=records, add_basemap=False,
        highlight_anchor=False, showfig=False, savefig=False)
    axis = figure.axes[0]
    np.testing.assert_array_equal(axis.lines[0].get_xdata(), [-118., -117.])
    assert axis.get_xlim()[1] >= -117.
    assert axis.get_ylim()[1] >= 35.
    plt.close(figure)
