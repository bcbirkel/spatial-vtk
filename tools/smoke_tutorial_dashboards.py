"""Exercise Streamlit dashboard rendering, one filter change, and HTTP health."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen

from streamlit.testing.v1 import AppTest
import spatial_vtk.visualize.dashboard as dashboard

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--metrics-root', required=True)
parser.add_argument('--summary-root', required=True)
parser.add_argument('--trace-summary', required=True)
parser.add_argument('--output', default='outputs/dashboard_smoke.json')
args = parser.parse_args()
os.environ.update(SVTK_METRICS_ROOT=str(Path(args.metrics_root).resolve()), SVTK_SUMMARY_ROOT=str(Path(args.summary_root).resolve()), SVTK_TRACE_SUMMARY=str(Path(args.trace_summary).resolve()))
root = Path(dashboard.__file__).parent
results = {}
for name in ('metrics', 'qc'):
    app = AppTest.from_file(str(root / f'streamlit_{name}.py'), default_timeout=60).run()
    assert not app.exception, str(app.exception)
    assert not app.error, str(app.error)
    assert len(app.dataframe), 'No displayed data'
    if name == 'metrics':
        selector = next(x for x in app.selectbox if x.label == 'Component')
        selector.select('Z').run()
        models = next(x for x in app.multiselect if x.label == 'Models')
        saved_models = list(models.value)
        models.set_value([]).run()
        assert not app.exception and not app.error
        assert any(x.label == 'Rows' and x.value == '0' for x in app.metric)
        assert len(app.dataframe) == 0
        next(x for x in app.multiselect if x.label == 'Models').set_value(saved_models).run()
        bands = next(x for x in app.multiselect if x.label == 'Passbands')
        saved_bands = list(bands.value)
        bands.set_value([]).run()
        assert not app.exception and not app.error
        assert any(x.label == 'Rows' and x.value == '0' for x in app.metric)
        next(x for x in app.multiselect if x.label == 'Passbands').set_value(saved_bands).run()
    else:
        next(x for x in app.text_input if x.label == 'Station Contains').input('BFS').run()
    assert not app.exception and not app.error
    results[name] = {'render': 'passed', 'filter_change': 'passed', 'displayed_tables': len(app.dataframe)}
    # Bind only localhost, check the server, and always terminate our own process.
    import socket
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    process = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', str(root / f'streamlit_{name}.py'), '--server.address=127.0.0.1', f'--server.port={port}', '--server.headless=true'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                with urlopen(f'http://127.0.0.1:{port}/_stcore/health', timeout=1) as response:
                    assert response.read() == b'ok'
                results[name]['http_health'] = 'passed'
                break
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError('Streamlit exited early')
                time.sleep(.2)
        else:
            raise RuntimeError('Streamlit health timeout')
    finally:
        process.terminate()
        process.wait(timeout=10)
path = Path(args.output)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(results, indent=2)+'\n')
print(json.dumps(results))
