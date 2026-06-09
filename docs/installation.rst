Installation
============

This page walks you through setting up Spatial-VTK in a conda environment,
installing the package, and running a few quick checks before you start a
workflow.

You will need Python 3.10 or newer and conda. If you are new to conda, the
`conda getting started guide <https://docs.conda.io/projects/conda/en/latest/user-guide/getting-started.html>`__
is a good place to start.

Create the Conda Environment
----------------------------

The public repository includes an environment file named
``svtk_environment.yaml`` at the repository root. Download that file from the
`Spatial-VTK GitHub repository <https://github.com/bcbirkel/spatial-vtk>`__, or
use the copy that is already present if you cloned the repository.

From the directory that contains ``svtk_environment.yaml``, run:

.. code-block:: bash

   conda env create -f svtk_environment.yaml
   conda activate spatial-vtk

If you already created the environment and want to refresh it after the
environment file changes, run:

.. code-block:: bash

   conda env update -f svtk_environment.yaml --prune
   conda activate spatial-vtk

Install from PyPI
-----------------

This is the simplest route. It installs the base package, the public Python
source modules, the ``svtk`` command, and the dashboard dependencies.

.. code-block:: bash

   python -m pip install spatial-vtk

The tutorial notebooks and example data are repository/docs-site assets, not
part of the PyPI wheel.

.. raw:: html

   <details>
   <summary><strong>Advanced: install development extras</strong></summary>
   <p>
   Use this only if you want to run the public test suite, build the docs, or
   validate a release from a source checkout.
   </p>
   <pre><code>python -m pip install "spatial-vtk[dashboard,docs,validation,waveforms]"</code></pre>
   <p>
   From a source checkout, use the editable form:
   </p>
   <pre><code>python -m pip install -e ".[dashboard,docs,validation,waveforms]"</code></pre>
   <p>
   After installing the validation extras, you can run:
   </p>
   <pre><code>python -m pytest</code></pre>
   </details>
   <div style="height: 1.25rem;"></div>

Install from Source
-------------------

Use this route when you want the repository files too, including docs, tutorial
notebooks, example data, tests, and editable source code.

.. code-block:: bash

   git clone https://github.com/bcbirkel/spatial-vtk.git
   cd spatial-vtk
   conda env create -f svtk_environment.yaml
   conda activate spatial-vtk
   python -m pip install -e .

The editable install means changes in the source checkout are picked up by the
environment immediately. That is the most convenient setup while you are
working through the tutorial notebooks or developing new analysis code.

Check the Install
-----------------

Run these checks from the same activated environment:

.. code-block:: bash

   python -c "import spatial_vtk; print(spatial_vtk.__version__)"
   svtk --help

If you installed from a source checkout and installed the advanced validation
extras, you can also run the public test suite:

.. code-block:: bash

   python -m pytest

You are ready to continue once the import prints a version, ``svtk --help``
shows the command groups, and the tests pass if you chose to run them.

Common Setup Notes
------------------

If conda cannot solve the environment, make sure you are using the
``conda-forge`` channel from ``svtk_environment.yaml``. Creating a fresh
environment is usually cleaner than trying to reuse an older research
environment with many unrelated packages.

If map figures render without a basemap, check your network connection.
Spatial-VTK uses ``contextily`` for basemap tiles, so basemap-backed maps need
network access unless you already have the required tiles cached locally.
