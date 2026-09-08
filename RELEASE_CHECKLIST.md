# Release checklist

This checklist applies to the public package, Python 3.10–3.12. Keep the
statistics-module proposal out of this release.

1. Check the staged public diff and version agreement in pyproject.toml,
   src/spatial_vtk/__init__.py and CITATION.cff. Keep generated outputs, private
   plans, caches and local paths out of the commit. Record the final commit.
2. Install the validation, docs, dashboard, notebooks and waveforms extras.
   Run from the checkout:
   ```sh
   PYTHONPATH=src MPLCONFIGDIR=/tmp/mplconfig_svtk python -m pytest -q
   PYTHONPYCACHEPREFIX=/tmp/svtk-pycache python -m compileall -q src tests tools
   PYTHONPATH=src MPLCONFIGDIR=/tmp/mplconfig_svtk python -m sphinx -W -b html docs docs/_build/html
   node tools/check_documentation_search.mjs docs/_build/html
   python -m build --sdist --wheel
   python -m twine check dist/*
   python tools/check_release_artifacts.py
   ```
3. Install the built wheel with dependencies in a new virtual environment.
   Confirm imports resolve to that environment's site-packages, not src.
   Test CLI help/version and all seven tutorials in a clean copy of the
   example data/docs/tools, with no PYTHONPATH override:
   ```sh
   unset SVTK_NO_BASEMAP
   export MPLBACKEND=Agg
   python tools/execute_tutorial_notebooks.py
   ```
   Final reviewed figures require successful Esri imagery. Only computation CI
   may use SVTK_NO_BASEMAP=1 and --allow-missing-basemaps.
4. Use tools/smoke_tutorial_dashboards.py on the resulting dashboard tables
   and QC trace summary. Check empty and restored model/passband selections,
   filters, application exceptions and localhost health. Inspect browser
   behavior separately; application tests do not certify a clean browser console.
5. Run tools/prepare_documentation_preview.py --execution-root <validated-project>
   and build Sphinx from outputs/documentation_preview/docs for output-bearing
   tutorial pages. The Pages workflow executes all seven tutorials with required
   cached Esri imagery before preparing these pages. Verify the docs reference sidebar, search results and result links.
   Sphinx rendering does not execute notebook cells. Keep hosted-browser
   evidence separate from local-file JavaScript tests.
6. Review unit/data statements in DATA_PROVENANCE.md. The owner confirmed both
   example waveform populations are acceleration in cm/s² on 2026-09-08.
   External PhaseNet inference remains separately unverified and optional.
7. Push a review branch and obtain passing CI on its exact commit, including
   Python 3.10, 3.11 and 3.12, tutorials, docs and distribution checks. Confirm
   GitHub Pages and the testpypi/pypi Trusted Publisher environments.
8. Keep 0.1.4rc1 for the candidate unless deliberately changing the version.
   Rebuild and revalidate if the code or version changes. Do not overwrite a
   previously published version. Publishing a GitHub Release triggers PyPI,
   including prereleases; manual Release dispatch defaults to TestPyPI.
9. After final publication authorization, merge/deploy docs, publish the exact
   matching tag, verify a fresh public clone and PyPI install, and check Pages
   search, links and README badges. Preserve final artifact hashes and logs.
