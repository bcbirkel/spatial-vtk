Examples and Tutorials
======================

These notebooks walk you through the public Spatial-VTK workflow with the LA Basin example subset. Each page is rendered from the downloadable notebook shown in the docs.

Install from the source checkout with ``python -m pip install ".[notebooks,waveforms]"``.
Launch notebooks from the checkout root or ``docs/examples``. For downloaded
notebooks, set ``SVTK_PROJECT_ROOT`` to a complete example checkout before
starting the kernel. Setup changes the working directory to that root so paths
inside metadata tables resolve consistently; it loads its own tutorial config.

Run Steps 1 → 2 → 3 before Steps 4–7. Step 3 calculates metrics and natural-log
residuals directly from the waveform inputs. All subsequent metric figures and
spatial analyses load those generated results. The plotting notebooks do not
use the legacy metric snapshots.

Final tutorial runs require basemaps. For computation-only checks without tile
downloads, set ``SVTK_NO_BASEMAP=1`` and pass ``--allow-missing-basemaps`` to the
runner. Those outputs must not be used for final visual review.
The default remains Esri World Imagery. This only disables optional static map
backgrounds; all scientific analysis cells still execute. Use
``python tools/execute_tutorial_notebooks.py`` to execute all seven notebooks.
The full spectral run can take tens of minutes. The runner allows 3600 seconds
per cell by default; use ``--timeout`` to adjust this on slower machines.
The runner saves executed copies and a manifest in ``outputs/tutorial_execution``.
Sphinx uses stored outputs (``nbsphinx_execute = "never"``); a documentation
build is not a notebook-execution test.

.. toctree::
   :maxdepth: 1

   step_01_ingest_and_prepare_data
   step_02_quality_control
   step_03_calculate_metrics
   step_04_spatial_statistics
   step_05_maps_and_figures
   step_06_additional_plotting_options
   step_07_dashboards
   cli_workflow


Residual convention
-------------------

The default residual is now ``ln(observed / synthetic)``. It is dimensionless:
zero indicates equal amplitudes, positive values indicate larger observed
amplitudes, and negative values indicate larger synthetic amplitudes.
Explicit ``log2_residual`` requests remain supported.

Step 3 calculates natural-log residuals directly from observed and synthetic
metric values. Steps 4–7 load those generated results; plotting cells do not
convert legacy log2 snapshots. Run the notebooks in order.
Percentage effects use ``100 * (exp(effect) - 1)``.
