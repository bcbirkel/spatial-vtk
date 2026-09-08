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

For more details, check out the the public documentation [here](https://bcbirkel.github.io/spatial-vtk/)!

![Spatial-VTK workflow](https://raw.githubusercontent.com/bcbirkel/spatial-vtk/main/ValidationToolkit_Workflow.png)

## Quick References:
### Install

The package can be installed from PyPI using:

    python -m pip install spatial-vtk

Or create the conda environment and install from a source checkout:

    conda env create -f svtk_environment.yaml
    conda activate spatial-vtk
    python -m pip install -e .

The package imports as `spatial_vtk` and installs the `svtk` command:

    python -c "import spatial_vtk; print(spatial_vtk.__version__)"
    svtk --help

### Package Structure Overview

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

### Issues/Questions/Troubleshooting

Review the [documentation](https://bcbirkel.github.io/spatial-vtk/index.html), particularly the [examples](https://bcbirkel.github.io/spatial-vtk/examples/index.html) and [troubleshooting](https://bcbirkel.github.io/spatial-vtk/support/troubleshooting.html) pages. Still having problems or have suggestions for useful additions to the package? Shoot me an email at birkel@usc.edu or open an issue on GitHub. 

Happy validating!
