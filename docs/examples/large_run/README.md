# Large-Run Notebook Set

These notebooks mirror the seven tutorial steps, but they are designed for full
large-dataset runs. They default to skipping existing outputs and submitting
heavy package-helper work to Slurm or printing the generated submission script.
The same notebooks
also run against the committed example data from a fresh source checkout; they
must not require private paths, pre-existing outputs, or user-specific shell
state.

Notebook cells call importable `spatial_vtk` package functions directly. They
do not shell out to `svtk` CLI commands for workflow work; the CLI remains a
terminal-oriented interface and an implementation detail of generated batch
scripts.

To verify the public notebooks from a clean checkout, install the tutorial
extras and run:

```bash
python -m pip install -e ".[validation,docs,dashboard,notebooks,waveforms]"
python tools/execute_tutorial_notebooks.py --clean --include-large-run
```

If pip has trouble solving compiled geospatial or waveform packages in an
existing environment, create the full source-checkout environment first:

```bash
conda env create -f svtk_environment.yaml
conda activate spatial-vtk
python -m pip install -e ".[validation,docs,dashboard,notebooks,waveforms]"
```

The checker executes the standard notebooks first, then these large-run
drivers, using only committed example data. It fails if any notebook raises an
error or emits warning-like output. Before execution or output cleanup, it also
checks that tutorial notebooks have no saved execution state, private absolute
paths, shell/CLI workflow cells, implementation plotting/workflow imports,
fixed run layout paths, raw output-path/table reads, or notebook-local
dataframe filtering and joins that should live in package helpers.
Notebook driver cells should use package workflow helpers that own path
resolution, skip/rebuild checks, chunking, Slurm script generation, figure
sidecars, and bounded previews. Common large-run entry points include:

```python
from spatial_vtk.config import notebook_run_context, notebook_figure_settings
from spatial_vtk.io import load_standard_ingest_workflow_outputs
from spatial_vtk.metrics import load_standard_metric_workflow_outputs
from spatial_vtk.metrics.plot import write_large_run_metric_figure_suite_from_notebook_settings
from spatial_vtk.qc import load_standard_qc_workflow_outputs
from spatial_vtk.spatial import (
    load_standard_geojson_workflow_output_status,
    load_standard_spatial_workflow_output_status,
)
from spatial_vtk.visualize import prepare_configured_dashboard_datasets_from_notebook_settings
```

Step 4 large-run spatial figures should be rendered through the standard
spatial output result:

```python
spatial_outputs = load_standard_spatial_workflow_output_status(cfg=context.cfg)
spatial_figure_suite = spatial_outputs.write_figure_suite(spatial_figure_settings)
```

Single-figure helpers remain available for custom Python scripts, but the
large-run notebooks should not hand-wire individual plot calls, figure paths, or
dataframe joins. Import from stable public packages such as
`spatial_vtk.metrics.plot`, `spatial_vtk.spatial.plot`,
`spatial_vtk.spatial.map`, and `spatial_vtk.visualize`. Do not import from
deeper implementation modules below those packages in notebooks; preflight
rejects those paths because they are internal organization, not the tutorial
contract.

Run `python tools/execute_tutorial_notebooks.py --preflight-only --include-large-run`
for the same source-contract and example-data checks without notebook runtime
dependencies.
Run `python tools/execute_tutorial_notebooks.py --runtime-check-only --include-large-run`
to also verify that the current environment can import the Jupyter,
`spatial_vtk`, scientific Python, mapping, dashboard, and waveform modules used
by the notebooks, without cleaning outputs or starting execution.

Environment switches:

- `SVTK_SUBMIT_SLURM=1`: submit generated Slurm scripts from notebook cells. Otherwise cells print `sbatch ...` commands.
- `SVTK_RUN_SCENARIO=tutorial`: choose a configured run scenario. Large-run notebooks let `notebook_run_context()` read this once and reuse `context.run_scenario`.
- `SVTK_RUN_LOCAL=1`: run lightweight package helper calls directly from the notebook. Otherwise heavy cells write Slurm scripts and print or submit them.
- `SVTK_OVERWRITE=1`: rebuild outputs even when they already exist.
- `SVTK_MAKE_FIGURES=1`: render figure cells after compact input tables exist.
- `SVTK_MAKE_SCORE_TRENDS=1`: render optional GOF score-trend diagnostics in Step 3. The main metric figure suite uses log2 residuals and does not render GOF score figures unless this is set.
- `SVTK_SCORE_TREND_COLUMNS=anderson_2004_gof`: choose the score columns for optional Step 3 GOF trend diagnostics.
- `SVTK_QC_CHUNKSIZE=1000000`: chunk size for disk-backed QC readers.
- `SVTK_PREPROCESS_CONTINUE_ON_ERROR=1`: allow Step 1 preprocessing to write partial metadata when configured waveform inputs are intentionally incomplete.
- `SVTK_METRIC_BATCH_COUNT=100`: choose how many metric manifest batches Step 3 writes before Slurm submission.
- `SVTK_FIGURE_SIDECARS=1`: write CSV/JSON row-provenance sidecars for saved figures.
- `SVTK_FIGURE_SIDECAR_ROWS=all`: write every plotted/source row to each sidecar. Use a positive integer to write a deterministic sample of that many rows. The matching JSON metadata records whether each CSV is exact or sampled.
- `SVTK_STATION_AGGREGATION=mean`: choose how metric rows are collapsed to station summaries for station-level maps. Supported values include `mean`, `median`, `min`, and `max`.
- `SVTK_PCA_MODE=PC1`: choose which PCA mode the Step 4 spatial PCA summary figures render.

Figure sidecars:

- Saved figure helpers can write a main `*.csv` sidecar containing the exact rows handed to the plotting function.
- Aggregated station figures also write a `*.source.csv` sidecar with the pre-aggregation metric rows used to build station summaries.
- If a station figure samples aggregated plot rows, the source sidecar is filtered to the raw metric rows behind those plotted station groups.
- The matching `*.json` sidecar records row counts, event/station/component/model/metric/passband/PSA-period counts, the value column, the station aggregation method, the dimensions collapsed into each station summary, and exactness flags such as `plot_sidecar_exact` and `source_sidecar_exact`. This is the audit trail for checking that plots average or summarize all selected event-station rows rather than only preview rows.

Dashboard summaries:

- Dashboard rollup tables expose `n` for contributing row counts and, when the source data includes the needed identifiers, `event_count` and `station_count` for unique event/station coverage behind each displayed aggregate.
- PSA summaries preserve `period_s`, so dashboard filters and rollups can separate oscillator periods even when PSA rows are not tied to one waveform passband.

Spectral metrics:

- `PSA` and `FAS` are broadband spectral metrics. Metric planning writes one broadband task per event/station/component/model for these metrics, with a blank passband, and then writes one output row per requested oscillator period in `period_s`.
- Passband filters in figure cells apply to passband-dependent metrics such as `PGA`, `PGV`, `CAV`, durations, delays, and correlations. PSA figures use oscillator periods instead; PSA period sheets and period curves should be compared by `period_s` or oscillator frequency, not by waveform passband.
- If an older run has PSA rows repeated under passband labels such as `1-2 sec`, rebuild the metric manifest and metric rows before using the large-run plotting notebooks. The package plotting helpers treat blank-passband PSA rows as the current contract.

Run order:

1. `step_01_large_run_ingest_and_prepare_data.ipynb`
2. `step_02_large_run_quality_control.ipynb`
3. `step_03_large_run_calculate_metrics.ipynb`
4. `step_04_large_run_spatial_statistics.ipynb`
5. `step_05_large_run_geojson_corridors.ipynb`
6. `step_06_large_run_additional_plotting.ipynb`
7. `step_07_large_run_dashboards.ipynb`

Each notebook is a driver: it should show paths, skip completed outputs, submit
or print heavy package-helper jobs, and preview only small bounded tables.
Reusable logic belongs in the package, not in notebook-local helper functions.
