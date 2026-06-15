# Large-Run Notebook Set

These notebooks mirror the seven tutorial steps, but they are designed for full CARC-scale runs. They default to skipping existing outputs and submitting heavy work to Slurm or printing the exact command to run.

Environment switches:

- `SVTK_SUBMIT_SLURM=1`: submit generated Slurm scripts from notebook cells. Otherwise cells print `sbatch ...` commands.
- `SVTK_RUN_LOCAL=1`: run lightweight CLI commands directly from the notebook. Otherwise cells print commands.
- `SVTK_OVERWRITE=1`: rebuild outputs even when they already exist.
- `SVTK_MAKE_FIGURES=1`: render figure cells after compact input tables exist.
- `SVTK_QC_CHUNKSIZE=1000000`: chunk size for disk-backed QC readers.

Run order:

1. `step_01_large_run_ingest_and_prepare_data.ipynb`
2. `step_02_large_run_quality_control.ipynb`
3. `step_03_large_run_calculate_metrics.ipynb`
4. `step_04_large_run_spatial_statistics.ipynb`
5. `step_05_large_run_geojson_corridors.ipynb`
6. `step_06_large_run_additional_plotting.ipynb`
7. `step_07_large_run_dashboards.ipynb`

Each notebook is a driver: it should show paths, skip completed outputs, submit or print heavy commands, and preview only small bounded tables.
