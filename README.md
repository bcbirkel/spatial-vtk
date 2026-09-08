# Spatial-VTK

[![CI](https://github.com/bcbirkel/spatial-vtk/actions/workflows/ci.yml/badge.svg)](https://github.com/bcbirkel/spatial-vtk/actions/workflows/ci.yml)
[![Docs](https://github.com/bcbirkel/spatial-vtk/actions/workflows/docs.yml/badge.svg)](https://github.com/bcbirkel/spatial-vtk/actions/workflows/docs.yml)
[![PyPI](https://img.shields.io/pypi/v/spatial-vtk.svg)](https://pypi.org/project/spatial-vtk/)
[![Python](https://img.shields.io/pypi/pyversions/spatial-vtk.svg)](https://pypi.org/project/spatial-vtk/)
[![License](https://img.shields.io/pypi/l/spatial-vtk.svg)](https://github.com/bcbirkel/spatial-vtk/blob/main/LICENSE)

`spatial-vtk` provides spatial validation tools for ground-motion simulations,
with data QC, residual and metric calculations, geologic metadata integration,
spatial statistics, mapping, and dashboard preparation for understanding model
performance patterns.

![Spatial-VTK workflow](https://raw.githubusercontent.com/bcbirkel/spatial-vtk/main/ValidationToolkit_Workflow.png)

## Install

Install from PyPI:

    python -m pip install spatial-vtk

Or create the conda environment and install from a source checkout:

    conda env create -f svtk_environment.yaml
    conda activate spatial-vtk
    python -m pip install -e .

The package imports as `spatial_vtk` and installs the `svtk` command:

    python -c "import spatial_vtk; print(spatial_vtk.__version__)"
    svtk --help

## Structure

- `spatial_vtk.io`: metadata preparation, input inventories, waveform
  preprocessing, manifests, and waveform format helpers.
- `spatial_vtk.config`: repository paths, bounds, and runtime settings.
- `spatial_vtk.qc`: quality-control build, review, and summary workflows.
- `spatial_vtk.metrics`: ground-motion metric and residual calculations.
- `spatial_vtk.spatial`: metric-field preparation, spatial correlation,
  PCA spatial modes, REDCAP and residual-feature clustering, geology joins,
  pattern tests, plots, and map helpers.
- `spatial_vtk.visualize`: context figures, QC views, and dashboard data.
- `spatial_vtk.cli`: command-line entry points.

See the [public documentation](https://bcbirkel.github.io/spatial-vtk/) for
installation, package overview, examples, API reference, support, and changelog
pages.

## Reproducible source tutorials (unreleased 0.1.4rc1)

This research/alpha package is under active validation. The existing PyPI 0.1.3
release does not contain these repairs. From this repaired source checkout:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install ".[notebooks,waveforms]"
export SVTK_NO_BASEMAP=1
python tools/execute_tutorial_notebooks.py
```

The source example bundle includes ten original MiniSEED inputs, five events,
and 30 selected stations, with checksums in `data/examples/`. Examples are not
included in the wheel. Step 1 generates processed waveforms; Step 2 performs QC;
Step 3 calculates metrics and native ln(observed / synthetic) residuals.
Steps 4–7 use those generated results; run Steps 1–3 first.
See the tutorial index and CLI workflow for launch commands.

Notebooks find the checkout from its root or `docs/examples`. For downloaded
notebooks set `SVTK_PROJECT_ROOT` to the complete example checkout. Unset
`SVTK_NO_BASEMAP` to request Esri World Imagery backgrounds.

Base metric/statistics workflows do not require an arrival picker. PhaseNet is
an optional external TensorFlow installation with an explicit command and model;
see [the integration contract](docs/phasenet.rst). The PyPI package named
`phasenet` has a different interface and is not installed by Spatial-VTK.

CI runs unit tests on Python 3.10–3.12 and executes the complete waveform-to-QC-
to-metrics tutorial on Python 3.12. Sphinx builds documentation without executing
notebooks; the notebook runner retains execution evidence separately.
