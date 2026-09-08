"""Execute public notebook cells without skipping analysis, and retain an audit."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
import subprocess
import time

import nbformat
from nbclient import NotebookClient

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--steps', nargs='+', type=int, choices=range(1, 8), default=list(range(1, 8)))
parser.add_argument('--timeout', type=int, default=3600, help='Maximum seconds per cell; spectral calculations can take tens of minutes.')
parser.add_argument('--cwd', choices=['root', 'notebooks'], default='root')
parser.add_argument('--allow-missing-basemaps', action='store_true', help='Computation-only run; outputs are not eligible for final visual review.')
args = parser.parse_args()
if not args.allow_missing_basemaps and os.environ.get('SVTK_NO_BASEMAP', '').lower() in {'1', 'true', 'yes'}:
    parser.error('Unset SVTK_NO_BASEMAP for final figures, or explicitly use --allow-missing-basemaps for computation-only validation.')
os.environ['SVTK_REQUIRE_BASEMAP'] = '0' if args.allow_missing_basemaps else '1'
root = Path(__file__).resolve().parents[1]
out = root / 'outputs/tutorial_execution'
out.mkdir(parents=True, exist_ok=True)
audit_path = out / 'basemaps.jsonl'
audit_path.write_text('')
os.environ['SVTK_BASEMAP_AUDIT'] = str(audit_path)
# Bind the kernel to the invoking environment (including a wheel-only environment).
kernel_root = out / 'jupyter'
kernel = kernel_root / 'kernels/python3'
kernel.mkdir(parents=True, exist_ok=True)
(kernel / 'kernel.json').write_text(json.dumps({'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'], 'display_name': 'Spatial-VTK validation', 'language': 'python'}))
os.environ['JUPYTER_PATH'] = str(kernel_root) + os.pathsep + os.environ.get('JUPYTER_PATH', '')
inputs = [root / 'data/examples/configuration/example_spatial_vtk_config.yaml', *sorted((root / 'data/examples').rglob('*.csv')), *sorted((root / 'data/examples').rglob('*.parquet')), *sorted((root / 'data/examples').rglob('*.geojson')), root / 'data/examples/example_five_event_subset/metadata/waveform_manifest.json']
manifest = {'inputs': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}, 'python_executable': sys.executable, 'python': sys.version, 'steps': [], 'basemaps_disabled': os.environ.get('SVTK_NO_BASEMAP', ''), 'basemaps_required': not args.allow_missing_basemaps, 'visual_review_eligible': not args.allow_missing_basemaps, 'basemap_audit': str(audit_path)}
for step in args.steps:
    path = next((root / 'docs/examples').glob(f'step_{step:02d}_*.ipynb'))
    notebook = nbformat.read(path, as_version=4)
    started = time.time()
    entry = {'notebook': str(path.relative_to(root)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest['steps'].append(entry)
    print(f'Executing {path.name}', flush=True)
    try:
        NotebookClient(notebook, timeout=args.timeout, kernel_name='python3', resources={'metadata': {'path': str(root if args.cwd == 'root' else path.parent)}}).execute()
        if step == 3:
            subprocess.run([sys.executable, str(root / 'tools/audit_tutorial_outputs.py'), '--project-root', str(root)], check=True)
        entry['status'] = 'passed'
    except Exception as exc:
        entry.update(status='failed', error=str(exc))
        raise
    finally:
        entry['seconds'] = time.time() - started
        nbformat.write(notebook, out / path.name)
        manifest['outputs'] = [str(p.relative_to(root)) for p in sorted((root / 'outputs/tutorials').rglob('*')) if p.is_file()]
        manifest['figure_sha256'] = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root / 'outputs/tutorials').rglob('*.png'))}
        (out / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'Passed Step {step} in {entry["seconds"]:.1f}s', flush=True)
