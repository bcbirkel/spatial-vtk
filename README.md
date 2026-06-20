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

![Spatial-VTK workflow](https://raw.githubusercontent.com/bcbirkel/spatial-vtk/main/docs/_static/spatial_vtk_workflow.png)

## Install

Install from PyPI:

    python -m pip install spatial-vtk

Or create the conda environment and install from a source checkout:

    conda env create -f svtk_environment.yaml
    conda activate spatial-vtk
    python -m pip install -e ".[notebooks,waveforms]"

The notebook and waveform extras install the Jupyter runtime and waveform
reader modules needed by the committed tutorial notebooks.
If pip has trouble solving compiled geospatial or waveform packages in an
existing environment, prefer the source-checkout conda environment above; it
installs the same tutorial stack plus local validation tools from
`svtk_environment.yaml`.

The package imports as `spatial_vtk` and installs the `svtk` command:

    python -c "import spatial_vtk; print(spatial_vtk.__version__)"
    svtk --help

## Run the Tutorial Notebooks

From a source checkout, verify the committed example data and notebook imports
before running the notebooks:

    python tools/execute_tutorial_notebooks.py --preflight-only --include-large-run
    python tools/execute_tutorial_notebooks.py --runtime-check-only --include-large-run

The runtime check does not execute notebooks or clean outputs. To execute the
standard and large-run tutorial notebooks end to end from the committed example
data, run:

    python tools/execute_tutorial_notebooks.py --clean --include-large-run

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
