"""Compare the spectral preprocessing against a read-only research function.

Only the inspected preprocess_common function is compiled; the research module
is never imported and its pipeline/main routine is never executed.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from obspy import read, UTCDateTime
from scipy.signal import butter, sosfiltfilt
from spatial_vtk.metrics.workflow.tasks import tasks_from_frame
from spatial_vtk.metrics.workflow.run import _prepare_spectral_sides

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--reference', required=True, type=Path)
p.add_argument('--tasks', required=True, type=Path)
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
source = a.reference.read_text()
function = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'preprocess_common')
namespace = dict(np=np, UTCDateTime=UTCDateTime, butter=butter, sosfiltfilt=sosfiltfilt)
exec(compile(ast.Module(body=[function], type_ignores=[]), str(a.reference), 'exec'), namespace)
tasks = [t for t in tasks_from_frame(a.tasks) if t.spectral_preprocessing]
results = []
# First real pair in each component; this verifies actual heterogeneous rates.
for component in sorted({t.component for t in tasks}):
    task = next(t for t in tasks if t.component == component)
    traces = [read(path).select(station=task.station, component=component)[0] for path in (task.obs_waveform_path, task.syn_waveform_path)]
    reference, _ = namespace['preprocess_common'](traces, 0, task.synthetic_max_frequency_hz)
    observed, synthetic, audit = _prepare_spectral_sides(task, {})
    errors = []
    for expected, actual in zip(reference, (observed, synthetic)):
        np.testing.assert_allclose(actual.data, expected.data, rtol=1e-12, atol=1e-12)
        assert actual.start_s == float(expected.stats.starttime)
        errors.append(float(np.max(np.abs(actual.data - expected.data))))
    results.append(dict(event_id=task.event_id, station=task.station, component=component,
                        maximum_absolute_sample_errors=errors, processing=audit,
                        source_sha256={path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                                       for path in (task.obs_waveform_path, task.syn_waveform_path)}))
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(dict(reference_path=str(a.reference),
    reference_sha256=hashlib.sha256(source.encode()).hexdigest(),
    builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    tasks_sha256=hashlib.sha256(a.tasks.read_bytes()).hexdigest(),
    scope='Preprocessing parity only; no independent validation of PSA/FAS formulas or physical units.',
    results=results), indent=2) + '\n')
print(json.dumps(results, indent=2))
