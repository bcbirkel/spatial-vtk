"""Verify a non-editable base install without waveform or neural packages."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import spatial_vtk
from spatial_vtk.spatial.calculate import build_metric_field, center_field_by_event

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--snapshot', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
assert 'site-packages' in spatial_vtk.__file__, spatial_vtk.__file__
for package in ('torch', 'phasenet', 'tensorflow', 'obspy'):
    assert importlib.util.find_spec(package) is None, f'{package} installed in base environment'
metrics = pd.read_parquet(args.snapshot)
field = build_metric_field(metrics, metric='PGA', value_column='log2_residual')
centered = center_field_by_event(field, min_stations_per_event=2)
assert len(centered) > 100
np.testing.assert_allclose(centered.groupby('event_id').field_centered.mean(), 0, atol=1e-12)
result = {'python': sys.version, 'version': spatial_vtk.__version__, 'package': spatial_vtk.__file__, 'rows': len(centered), 'no_optional_backends': True, 'event_centering': 'passed'}
Path(args.output).write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
