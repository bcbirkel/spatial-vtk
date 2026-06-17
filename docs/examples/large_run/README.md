# Large-Run Notebook Set

These notebooks mirror the seven tutorial steps, but they are designed for full
large-dataset runs. They default to skipping existing outputs and submitting
heavy work to Slurm or printing the exact command to run. The same notebooks
also run against the committed example data from a fresh source checkout; they
must not require private paths, pre-existing outputs, or user-specific shell
state.

To verify the public notebooks from a clean checkout, install the tutorial
extras and run:

```bash
python tools/execute_tutorial_notebooks.py --clean --include-large-run
```

The checker executes the standard notebooks first, then these large-run
drivers, using only committed example data. It fails if any notebook raises an
error or emits warning-like output.

Environment switches:

- `SVTK_SUBMIT_SLURM=1`: submit generated Slurm scripts from notebook cells. Otherwise cells print `sbatch ...` commands.
- `SVTK_RUN_LOCAL=1`: run lightweight CLI commands directly from the notebook. Otherwise cells print commands.
- `SVTK_OVERWRITE=1`: rebuild outputs even when they already exist.
- `SVTK_MAKE_FIGURES=1`: render figure cells after compact input tables exist.
- `SVTK_QC_CHUNKSIZE=1000000`: chunk size for disk-backed QC readers.
- `SVTK_FIGURE_SIDECARS=1`: write CSV/JSON row-provenance sidecars for saved figures.
- `SVTK_FIGURE_SIDECAR_ROWS=all`: write every plotted/source row to each sidecar. Use a positive integer to write a deterministic sample of that many rows.
- `SVTK_STATION_AGGREGATION=median`: choose how metric rows are collapsed to station summaries for station-level maps. Supported values include `median`, `mean`, `min`, and `max`.

Figure sidecars:

- Saved figure helpers can write a main `*.csv` sidecar containing the exact rows handed to the plotting function.
- Aggregated station figures also write a `*.source.csv` sidecar with the pre-aggregation metric rows used to build station summaries.
- The matching `*.json` sidecar records row counts, event/station/component/model/metric/passband/PSA-period counts, the value column, and the station aggregation method. This is the audit trail for checking that plots average or summarize all selected event-station rows rather than only preview rows.

Run order:

1. `step_01_large_run_ingest_and_prepare_data.ipynb`
2. `step_02_large_run_quality_control.ipynb`
3. `step_03_large_run_calculate_metrics.ipynb`
4. `step_04_large_run_spatial_statistics.ipynb`
5. `step_05_large_run_geojson_corridors.ipynb`
6. `step_06_large_run_additional_plotting.ipynb`
7. `step_07_large_run_dashboards.ipynb`

Each notebook is a driver: it should show paths, skip completed outputs, submit
or print heavy commands, and preview only small bounded tables. Reusable logic
belongs in the package, not in notebook-local helper functions.
