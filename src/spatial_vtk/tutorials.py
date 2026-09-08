"""Portable setup and verified input handoffs for the public tutorials."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

CONFIG = Path('data/examples/configuration/example_spatial_vtk_config.yaml')


def tutorial_root(project_root=None):
    """Find the example checkout, or use explicit root / SVTK_PROJECT_ROOT."""
    explicit = project_root or os.environ.get('SVTK_PROJECT_ROOT')
    candidates = [Path(explicit).expanduser()] if explicit else [Path.cwd(), *Path.cwd().parents]
    for candidate in candidates:
        if (candidate / CONFIG).is_file():
            return candidate.resolve()
    raise FileNotFoundError('Tutorial data/config not found. Clone spatial-vtk and set SVTK_PROJECT_ROOT to that checkout (not the notebook directory).')


def verify_waveforms(project_root=None):
    """Check every required file and checksum before expensive preprocessing."""
    root = tutorial_root(project_root)
    bundle = root / 'data/examples/example_five_event_subset'
    manifest = json.loads((bundle / 'metadata/waveform_manifest.json').read_text())
    errors = []
    for item in manifest['files']:
        path = bundle / item['path']
        if not path.is_file():
            errors.append(f"Missing {item['path']}")
        elif path.stat().st_size != item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            errors.append(f"Checksum mismatch: {item['path']}")
    if errors:
        raise FileNotFoundError('\n'.join(errors) + '\nObtain the complete example data from the matching source checkout; the PyPI wheel excludes examples. See data/examples/README.md.')
    return manifest


def build_metric_inventories(event_stations, *, config):
    """Inventory the Step 1 processed traces, preserving actual sample metadata."""
    import pandas as pd
    from obspy import read
    from spatial_vtk.io.metric_inputs import normalize_metric_waveform_inventory
    outputs = []
    for source in ('observed', 'synthetic'):
        column = f'{source}_processed_waveform'
        rows = []
        for (_, path), records in event_stations.groupby(['event_id', column]):
            if not Path(path).is_file():
                raise FileNotFoundError(f'{path}: run Step 1 first.')
            allowed = set(records['station'].astype(str))
            for trace in read(str(path)):
                if trace.stats.station not in allowed:
                    continue
                rows.append(dict(source=source, event_id=str(records.iloc[0]['event_id']),
                    station=trace.stats.station, component=trace.stats.channel[-1],
                    model=config.section('metrics.models')[0] if source == 'synthetic' else '',
                    raw_waveform_path=str((config.root_dir / Path(records.iloc[0][f'{source}_raw_waveform'])).resolve()),
                    waveform_path=str(path), dt=trace.stats.delta, sampling_rate=trace.stats.sampling_rate,
                    starttime=str(trace.stats.starttime), endtime=str(trace.stats.endtime)))
        if not rows:
            raise ValueError(f'No {source} traces found. Run Step 1 with the complete example bundle.')
        outputs.append(normalize_metric_waveform_inventory(pd.DataFrame(rows), source=source,
            synthetic_max_frequency_hz=config.section('synthetics.max_frequency_hz')))
    return tuple(outputs)


def with_natural_log_residual(table):
    """Derive ln residuals from a legacy tutorial snapshot without editing it.

    Multiplication by ln(2) preserves existing QC exclusions and missing values.
    Named log2 columns remain available for explicit legacy comparisons.
    """
    import numpy as np
    import pandas as pd
    result = table.copy()
    if "ln_residual" not in result.columns or (result["ln_residual"].isna().all() and "log2_residual" in result.columns and result["log2_residual"].notna().any()):
        if "log2_residual" not in result.columns:
            raise ValueError("Tutorial snapshot requires ln_residual or log2_residual.")
        result["ln_residual"] = pd.to_numeric(result["log2_residual"], errors="coerce") * np.log(2.0)
    return result
