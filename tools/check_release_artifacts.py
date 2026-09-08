"""Verify release versions and distribution contents against current source."""
import hashlib
import json
import re
import tarfile
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
version = re.search(r'^version = "([^"]+)"', (root / 'pyproject.toml').read_text(), re.M)[1]
assert f'__version__ = "{version}"' in (root / 'src/spatial_vtk/__init__.py').read_text()
assert f'version: {version}' in (root / 'CITATION.cff').read_text()
wheel = root / f'dist/spatial_vtk-{version}-py3-none-any.whl'
sdist = root / f'dist/spatial_vtk-{version}.tar.gz'
with zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()
    assert 'spatial_vtk/config/default_outputs.yaml' in names
    assert not any(n.startswith(('data/', 'docs/', 'tests/', 'tools/', 'outputs/')) for n in names)
    assert not any('__pycache__' in n or n.endswith(('.pyc', '.ipynb', '.DS_Store')) for n in names)
    for source in (root / 'src/spatial_vtk').rglob('*.py'):
        assert archive.read(str(source.relative_to(root / 'src'))) == source.read_bytes(), source
with tarfile.open(sdist) as archive:
    for member in archive.getmembers():
        relative = member.name.partition('/')[2]
        assert not relative.startswith(('outputs/', 'data/', 'docs/', '.git/', '.cache/')), relative
report = {'version': version, 'source_matches_wheel': True, 'distributions': [
    {'file': p.name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    for p in (wheel, sdist)]}
out = root / 'outputs/release_validation'
out.mkdir(parents=True, exist_ok=True)
(out / 'distributions.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
