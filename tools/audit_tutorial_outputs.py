"""Validate the real tutorial's metric keys, numerical relationships and provenance."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project-root', type=Path, default=Path.cwd())
parser.add_argument('--baseline-metrics', type=Path)
args = parser.parse_args()
root = args.project_root.resolve()
tables = root / 'outputs/tutorials/tables'
metrics = pd.read_parquet(tables / 'metric_rows.parquet')
keys = ['event_id', 'station', 'component', 'model', 'passband', 'metric', 'period_s']
assert not metrics.duplicated(keys).any(), 'Duplicate metric keys'
assert set(metrics.component) == {'Z', 'R', 'T'}
assert metrics.event_id.nunique() == 5
assert set(metrics.metric) == {'PGA', 'PGV', 'PGD', 'PSA', 'FAS'}
spectral = metrics[metrics.metric.isin(['PSA', 'FAS'])]
assert set(spectral.period_s) == set(np.arange(1.5, 5.1, 0.5))
assert set(spectral.passband) == {'lowpass 1 Hz'}
assert not spectral.duplicated(['event_id', 'station', 'component', 'model', 'metric', 'period_s']).any()
assert spectral.spectral_sample_rate_hz.eq(25).all()
assert spectral.spectral_lowpass_obs_hz.eq(1).all() and spectral.spectral_lowpass_syn_hz.eq(1).all()
valid = metrics.dropna(subset=['value_obs', 'value_syn', 'ln_residual'])
assert len(valid) > 100
np.testing.assert_allclose(valid.ln_residual, np.log(valid.value_obs / valid.value_syn), atol=1e-10, rtol=1e-10)
manifest_path = root / 'data/examples/example_five_event_subset/metadata/waveform_manifest.json'
result = {'metric_rows': len(metrics), 'finite_comparisons': len(valid), 'events': metrics.event_id.nunique(), 'stations': metrics.station.nunique(), 'components': sorted(metrics.component.unique()), 'metrics': sorted(metrics.metric.unique()), 'duplicate_keys': 0, 'residual_identity': 'passed', 'input_waveform_manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(), 'outputs': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(tables.glob('*')) if p.suffix in ('.csv', '.parquet')}}
output = root / 'outputs/tutorial_execution/validation.json'
output.parent.mkdir(parents=True, exist_ok=True)
coverage = spectral.assign(finite_comparison=np.isfinite(spectral.ln_residual)).groupby(
    ['metric', 'component', 'period_s'], dropna=False).agg(rows=('metric', 'size'), finite_comparisons=('finite_comparison', 'sum')).reset_index()
coverage.to_csv(output.parent / 'spectral_coverage.csv', index=False)
result['spectral_coverage'] = coverage.to_dict(orient='records')
if args.baseline_metrics:
    from spatial_vtk.tutorials import with_natural_log_residual
    old = with_natural_log_residual(pd.read_parquet(args.baseline_metrics))
    ordinary = ['PGA', 'PGV', 'PGD']
    cols = keys + ['value_obs', 'value_syn', 'ln_residual', 'obs_qc_status', 'syn_qc_status', 'comparison_qc_status']
    before = old[old.metric.isin(ordinary)][cols].sort_values(keys).reset_index(drop=True)
    after = metrics[metrics.metric.isin(ordinary)][cols].sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(before, after, check_exact=False, atol=1e-12, rtol=1e-12)
    result['amplitude_baseline_comparison'] = dict(rows=len(after), status='unchanged after conversion to natural log',
        baseline_sha256=hashlib.sha256(args.baseline_metrics.read_bytes()).hexdigest())
output.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='outputs'}))
