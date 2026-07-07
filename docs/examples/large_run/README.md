# Large-Run Notebook Set

These notebooks are action-oriented drivers for full large-dataset runs. They
skip existing outputs by default and either submit heavy work to Slurm or print
the generated submission script/command. The same notebooks also run against
the committed example data from a fresh source checkout; they must not require
private paths, pre-existing outputs, or user-specific shell state.

Notebook cells call importable `spatial_vtk` package functions directly,
specifically public `spatial_vtk.large_run` actions. The
package owns config activation, path resolution, skip/rebuild checks, chunking,
Slurm script generation, figure settings, dashboard launch details, and
bounded diagnostics. They do not shell out to `svtk` CLI commands for workflow work.
The notebooks should read as the scientific workflow, not as implementation
plumbing.

To verify the public notebooks from a clean checkout, install the tutorial
extras and run:

```bash
python -m pip install -e ".[validation,docs,dashboard,notebooks,waveforms]"
python tools/check_validation_environment.py --groups tutorial
MPLCONFIGDIR=/tmp/mplconfig_svtk python tools/execute_tutorial_notebooks.py --clean --include-large-run
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
The action-oriented large-run notebooks avoid notebook-local dataframe filtering
and joins entirely.
Notebook driver cells should use action helpers such as:

```python
from spatial_vtk.large_run import (
    activate_large_run,
    run_quality_control,
    launch_qc_dashboard,
    calculate_metrics,
    launch_metrics_dashboard,
)
```

Lower-level workflow, plotting, dashboard, and sidecar helpers remain available
for scripts and package extensions, but the large-run notebooks should not
hand-wire individual plot calls, figure paths, status frames, dataframe joins,
or dashboard contracts.

Run `python tools/check_validation_environment.py --groups tutorial` first to
report missing Jupyter, mapping, dashboard, or waveform modules before the
heavier notebook checks start. If dependencies are missing, the checker prints
both the generic source-checkout install command and the active-Python install
command so the package extras are installed into the same environment that will
run the notebooks.
Run `python tools/execute_tutorial_notebooks.py --preflight-only --include-large-run`
for the same source-contract and example-data checks without notebook runtime
dependencies.
Run `MPLCONFIGDIR=/tmp/mplconfig_svtk python tools/execute_tutorial_notebooks.py --runtime-check-only --include-large-run`
to also verify that the current environment can import the Jupyter,
`spatial_vtk`, scientific Python, mapping, dashboard, and waveform modules used
by the notebooks, without cleaning outputs or starting execution.

Environment switches:

- `SVTK_SUBMIT_SLURM=1`: submit generated Slurm scripts through package helpers from notebook cells. Otherwise cells write the script and show a structured result with the script path and the submission command to run from a terminal.
- `SVTK_RUN_SCENARIO=tutorial`: choose a configured run scenario. Large-run notebooks let `notebook_run_context()` read this once and reuse `context.run_scenario`.
- `SVTK_RUN_LOCAL=1`: run lightweight package helper calls directly from the notebook. Otherwise heavy cells write Slurm scripts and print or submit them.
- `SVTK_OVERWRITE=1`: rebuild outputs even when they already exist.
- `SVTK_MAKE_FIGURES=1`: environment-backed default for figure rendering. The
  large-run notebooks also expose `make_figures=` in their setup cell so the
  choice is visible and editable in the notebook.
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
2. `step_02_large_run_quality_control.ipynb` and review the QC dashboard
3. `step_03_large_run_calculate_metrics.ipynb` and review the metrics dashboard
4. `step_04_large_run_spatial_statistics.ipynb`
5. `step_05_large_run_geojson_corridors.ipynb`
6. `step_06_large_run_additional_plotting.ipynb`

Dashboards are not a separate final step in the large-run workflow. The QC
dashboard belongs in Step 2 because it supports QC review before metrics. The
metrics dashboard belongs in Step 3 because it supports metric review before
spatial analysis. In short: QC dashboard belongs in Step 2; metrics dashboard
belongs in Step 3.

Each notebook is a driver: it should expose one setup cell and action cells,
skip completed outputs, submit or print heavy package jobs, and keep
troubleshooting details inside package helpers rather than notebook-local
helper functions.
