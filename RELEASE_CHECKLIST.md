# Spatial-VTK Release Checklist

Use this checklist before publishing a new `spatial-vtk` release. Run the
commands from the repository root in a clean environment.

## 1. Start From A Clean Tree

```bash
git status --short
git fetch origin
git rebase origin/main
```

Do not publish with generated files staged. Keep `dist/`, `build/`,
`src/spatial_vtk.egg-info/`, `docs/_build/`, `outputs/`, caches, and bytecode
out of git.

## 2. Install Release Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[validation,docs,dashboard,notebooks,waveforms]"
```

Use Python 3.10, 3.11, or 3.12. The package currently declares
`>=3.10,<3.14`.

## 3. Run Local Validation

```bash
MPLCONFIGDIR=/tmp/mplconfig_svtk python -m pytest -q
python -m compileall -q src tests
MPLCONFIGDIR=/tmp/mplconfig_svtk python tools/execute_tutorial_notebooks.py --preflight-only --include-large-run
MPLCONFIGDIR=/tmp/mplconfig_svtk python -m sphinx -W -b html docs docs/_build/html
```

For a release candidate, also run the public tutorial notebooks end to end:

```bash
MPLCONFIGDIR=/tmp/mplconfig_svtk python tools/execute_tutorial_notebooks.py --clean --include-large-run
```

The notebook run should finish without errors or warning-like output. If it
fails, fix the package, docs, or example data rather than weakening the
notebook source contract.

## 4. Check CLI And Dashboard Entry Points

```bash
svtk --help
svtk --version
svtk config --help
svtk plot metrics list
svtk map spatial list
svtk visualize context list
svtk dashboard status --help
```

Confirm user-facing command help favors config-backed defaults and clear aliases
such as `--input-table`, `--figure-output`, `--metrics-dataset-dir`, and
`--dashboard-summary-table-dir`.

## 5. Build And Inspect Distributions

```bash
rm -rf dist build src/spatial_vtk.egg-info
python -m build --sdist --wheel
python -m twine check dist/*
```

Inspect the wheel before publishing:

```bash
python - <<'PY'
import pathlib
import zipfile

wheels = sorted(pathlib.Path("dist").glob("*.whl"))
if not wheels:
    raise SystemExit("No wheel was built.")
with zipfile.ZipFile(wheels[0]) as zf:
    names = zf.namelist()

required = ["spatial_vtk/config/default_outputs.yaml"]
for name in required:
    if name not in names:
        raise SystemExit(f"Wheel is missing required file: {name}")

forbidden_prefixes = ("data/", "docs/", "tests/", "tools/", "outputs/")
if any(name.startswith(forbidden_prefixes) for name in names):
    raise SystemExit("Wheel contains repository-only content.")
if any("__pycache__" in name or name.endswith((".pyc", ".DS_Store", ".ipynb")) for name in names):
    raise SystemExit("Wheel contains generated files or notebooks.")
print(f"checked {wheels[0].name}: {len(names)} files")
PY
```

## 6. Smoke-Test The Wheel

```bash
rm -rf /tmp/spatial_vtk_wheel_smoke
python -m pip install --no-deps --target /tmp/spatial_vtk_wheel_smoke dist/spatial_vtk-*.whl
PYTHONPATH=/tmp/spatial_vtk_wheel_smoke python -c "import spatial_vtk; print(spatial_vtk.__version__)"
```

For a full install smoke test, create a fresh virtual environment and install
the built wheel with dependencies:

```bash
python -m venv /tmp/spatial-vtk-release-smoke
. /tmp/spatial-vtk-release-smoke/bin/activate
python -m pip install --upgrade pip
python -m pip install dist/spatial_vtk-*.whl
python -c "import spatial_vtk; print(spatial_vtk.__version__)"
svtk --help
deactivate
```

## 7. Verify GitHub Checks

Push the release branch and wait for:

- `.github/workflows/ci.yml`
- `.github/workflows/docs.yml`

Both workflows should pass before tagging or publishing. Fix any failure in the
branch and rerun the checks.

## 8. Publish

1. Confirm the version in `pyproject.toml` is the intended release version.
2. Confirm the changelog describes the release.
3. Create a GitHub release tagged `vX.Y.Z` for the exact package version.
4. Let `.github/workflows/release.yml` build and publish through trusted
   publishing.
5. Confirm the package installs from PyPI:

   ```bash
   python -m venv /tmp/spatial-vtk-pypi
   . /tmp/spatial-vtk-pypi/bin/activate
   python -m pip install --upgrade pip
   python -m pip install spatial-vtk==X.Y.Z
   python -c "import spatial_vtk; print(spatial_vtk.__version__)"
   svtk --help
   deactivate
   ```

6. Confirm the docs site resolves and README badges render.
