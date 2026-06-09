# Spatial-VTK Release Checklist

Use this checklist before publishing `spatial-vtk` to PyPI. Run commands from
the public repository root unless a step says otherwise.

## 1. Start Clean

Confirm the public repository contains only public files:

    git status --short
    find . \( -name '.DS_Store' -o -name '.cache' -o -name '.pytest_cache' -o -name '__pycache__' -o -name '*.pyc' -o -path './outputs' -o -path './docs/_build' -o -path './build' -o -path './src/spatial_vtk.egg-info' \) -print
    rg -n "/[p]roject2|ValidationToolkit-[r]estructured|private-[c]luster-name" .

The generated-artifact search should print nothing. The private-detail search
should print nothing except intentional public contact or documentation text.
Also scan any changed examples for local absolute paths, usernames, or private
model/output directories before publishing.

## 2. Validate Locally

Use the Spatial-VTK conda environment or another environment with the
validation, docs, dashboard, and waveform extras installed.

    python -m pip install -e ".[validation,docs,dashboard,waveforms]"
    MPLCONFIGDIR=/tmp/mplconfig_svtk python -m pytest -q
    python -m compileall -q src tests
    MPLCONFIGDIR=/tmp/mplconfig_svtk python -m sphinx -W -b html docs docs/_build/html

Expected result: tests pass, compileall prints no output, and Sphinx reports
`build succeeded`.

## 3. Build and Check Distributions

Remove any old distributions, then build fresh archives:

    rm -rf dist build src/spatial_vtk.egg-info
    python -m build --sdist --wheel
    python -m twine check dist/*

If you are building in an offline environment where isolated builds cannot
download `wheel`, use `python -m build --no-isolation` from an environment that
already has the validation extras installed.

Inspect the source archive and wheel to confirm only installable package files
are included. The PyPI archives should not include notebooks, example data,
documentation builds, review outputs, generated caches, private package names,
or repo-only tools:

    tar -tf dist/spatial_vtk-*.tar.gz | rg '(^spatial_vtk-[^/]+/(data|docs|tests|tools|outputs|\.github|\.cache|build|dist)/|\.ipynb$|__pycache__|\.pyc$|\.DS_Store)' && exit 1 || true

    python - <<'PY'
    import pathlib
    import zipfile
    wheels = sorted(pathlib.Path("dist").glob("*.whl"))
    if not wheels:
        raise SystemExit("No wheel was built.")
    with zipfile.ZipFile(wheels[0]) as zf:
        names = zf.namelist()
    assert any(name.startswith("spatial_vtk/") for name in names)
    assert "spatial_vtk/config/default_outputs.yaml" in names
    assert any(name.startswith("spatial_vtk/visualize/dashboard/") for name in names)
    legacy_namespace = "validation" + "_toolkit/"
    assert not any(name.startswith(legacy_namespace) for name in names)
    assert not any(name.startswith("data/") for name in names)
    assert not any(name.startswith("docs/") for name in names)
    assert not any(name.startswith("tests/") for name in names)
    assert not any(name.startswith("tools/") for name in names)
    assert not any(name.endswith(".ipynb") for name in names)
    assert not any("__pycache__" in name or name.endswith(".pyc") or name.endswith(".DS_Store") for name in names)
    print(f"checked {wheels[0].name}: {len(names)} files")
    PY

## 4. Clean Wheel Smoke Test

Install the wheel into a temporary target directory and run import/CLI checks:

    rm -rf /tmp/spatial_vtk_wheel_smoke
    python -m pip install --no-deps --target /tmp/spatial_vtk_wheel_smoke dist/spatial_vtk-*.whl
    PYTHONPATH=/tmp/spatial_vtk_wheel_smoke python -c "import spatial_vtk; print(spatial_vtk.__version__)"
    PYTHONPATH=/tmp/spatial_vtk_wheel_smoke python -m spatial_vtk.cli --help

This smoke test intentionally uses `--no-deps` and reuses the active
environment's dependencies. It verifies package contents and entry-point code
without creating a permanent install.

## 5. TestPyPI Dry Run

This step requires TestPyPI credentials or an API token.

    python -m twine upload --repository testpypi dist/*

Then create a fresh environment and install from TestPyPI:

    python -m venv /tmp/spatial-vtk-testpypi
    source /tmp/spatial-vtk-testpypi/bin/activate
    python -m pip install --upgrade pip
    python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ spatial-vtk
    python -c "import spatial_vtk; print(spatial_vtk.__version__)"
    svtk --help

If TestPyPI installation cannot resolve a dependency, fix package metadata
before publishing to the real PyPI.

## 6. Publish to PyPI

Only publish after TestPyPI succeeds.

    python -m twine upload dist/*

Then verify installation in a fresh environment:

    python -m venv /tmp/spatial-vtk-pypi
    source /tmp/spatial-vtk-pypi/bin/activate
    python -m pip install --upgrade pip
    python -m pip install spatial-vtk
    python -c "import spatial_vtk; print(spatial_vtk.__version__)"
    svtk --help

## 7. Tag and Announce

After PyPI succeeds, tag the release in GitHub:

    git tag -a v0.1.0 -m "spatial-vtk 0.1.0"
    git push origin v0.1.0

Create a GitHub release from the tag. Include the PyPI link, the documentation
link, a short feature summary, known limitations, and citation guidance.

## 8. Cleanup

Remove generated artifacts before the next development cycle:

    rm -rf build dist docs/_build src/spatial_vtk.egg-info .pytest_cache
    find . -name '__pycache__' -type d -prune -exec rm -rf {} +
    find . \( -name '*.pyc' -o -name '.DS_Store' \) -type f -delete
