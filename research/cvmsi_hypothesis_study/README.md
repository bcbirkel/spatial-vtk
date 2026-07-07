# CVM-SI Hypothesis Study

Private, reproducible analysis code for exploring observed ground-motion
patterns, CVM-SI synthetic performance, and model-linked hypotheses. This
directory is intentionally separate from the public package API; generated
tables, figures, and reports should be written under ignored output
directories.

## Run on CARC

From the repository root on Discovery:

```bash
env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
python research/cvmsi_hypothesis_study/cvmsi_hypothesis_study.py
```

For the broader second-pass interaction scan, run after the first-pass output
exists:

```bash
env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
python research/cvmsi_hypothesis_study/cvmsi_extended_scan.py
```

For targeted waveform/model examples from high-residual path-azimuth bins, run
after the first two passes exist:

```bash
env MPLCONFIGDIR=/tmp/mplconfig_cvmsi_cases \
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
python research/cvmsi_hypothesis_study/cvmsi_targeted_case_studies.py
```

For the fuller mixed-effects deep dive, run after the first-pass `pairs.csv`
exists:

```bash
env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
python research/cvmsi_hypothesis_study/cvmsi_mixed_effects_deep_dive.py \
  --pairs-csv /project2/jvidale_1700/spatial-vtk/runs/outputs/analysis/cvmsi_hypothesis_study/tables/pairs.csv \
  --output-dir /project2/jvidale_1700/spatial-vtk/runs/outputs/analysis/cvmsi_hypothesis_study/mixed_effects
```

After copying or generating the reviewed outputs locally, build the PDF
companion to the integrated Markdown report:

```bash
/opt/anaconda3/envs/gmprocess/bin/python \
research/cvmsi_hypothesis_study/build_report_pdf.py
```

The default input paths point to:

- observed-derived metrics:
  `/project2/jvidale_1700/spatial-vtk/runs/outputs/tables/metrics_final_enriched.parquet`
- mapped regions:
  `/project2/jvidale_1700/spatial-vtk/runs/inputs/geospatial/regions_updated.geojson`
- CVM-SI material model:
  `/project2/jvidale_1700/Salvus_HPC/codebase/slurm_material_meshes/cvmsi_0.6x1.2_slurm_meshing/cvmsi_0.6x1.2_material_CSrules.h5`

Outputs default to:

`/project2/jvidale_1700/spatial-vtk/runs/outputs/analysis/cvmsi_hypothesis_study`

## What It Produces

- station/event/path analysis tables
- model samples at stations for several depths
- bootstrap and permutation statistical summaries
- mixed-effects fixed-effect summaries with station and event random effects
- maps, path/period figures, geology/site-mismatch figures, and model
  cross sections
- a Markdown report scaffold with figure/table references and statistical
  interpretation notes
- a self-contained PDF companion for the integrated report, including a figure
  appendix with the reviewed PNG exports

The extended scan adds source magnitude/depth/mechanism summaries,
distance/path attenuation regressions, within-pair band contrast regressions,
station/event support checks, azimuth and component summaries, station/event
geomorphology summaries, and mixed-effects interaction models using raw
log2(obs/syn) residuals with event and station random intercepts.

The targeted case-study pass selects event-station examples that have both
observed gmprocess waveforms and CVM-SI ASDF synthetics, then builds corridor
maps, CVM-SI Vs cross sections, and observed/synthetic 3-5 sec waveform panels.

The mixed-effects deep-dive pass fits nested crossed event/station mixed models
to raw residuals, compares source/distance/path/site/frequency explanations,
and exports variance-decomposition and fixed-effect interval figures.
