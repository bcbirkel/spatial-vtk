"""Command-line entry point for Spatial-VTK.

Purpose
-------
This module exposes the public ``svtk`` command. The curated subcommands cover
file-based workflows that users commonly run outside notebooks, while
``svtk call`` provides a generic CLI path to any importable public Python
function.

Usage examples
--------------
Show active config:
  ``svtk config show --config spatial-vtk.yaml``

Prepare downstream metric outputs:
  ``svtk metrics outputs --metrics metrics.csv --output-dir outputs/metrics``

Run any public function with JSON/YAML arguments:
  ``svtk call spatial_vtk.config.labels.metric_display_name --args C5``
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml


@dataclass(frozen=True)
class PlotCommand:
    """One file-backed plotting command definition.

    Parameters
    ----------
    function
        Importable plotting function path.
    primary_arg
        Function argument populated from ``--input``.
    help
        Short command help text.
    table_aliases
        Convenience table options mapped to function argument names.

    Returns
    -------
    PlotCommand
        Immutable plotting command metadata.
    """

    function: str
    primary_arg: str | None
    help: str
    table_aliases: dict[str, str] | None = None


METRICS_PLOT_COMMANDS: dict[str, PlotCommand] = {
    "example-metric-pairs": PlotCommand("spatial_vtk.metrics.plot.example_metric_plots.plot_example_metric_pairs", None, "Plot synthetic trace-pair examples that illustrate metric behavior."),
    "model-metric-heatmap": PlotCommand("spatial_vtk.metrics.plot.model_comparison.plot_model_metric_heatmap", "summary_df", "Plot a model-by-metric heatmap."),
    "winner-heatmap": PlotCommand("spatial_vtk.metrics.plot.model_comparison.plot_winner_heatmap", "summary_df", "Plot a winner/class heatmap."),
    "band-score-distribution": PlotCommand("spatial_vtk.metrics.plot.model_comparison.plot_band_score_distribution", "df", "Plot score distributions by passband."),
    "psa-period-curve": PlotCommand("spatial_vtk.metrics.plot.periods.plot_psa_period_curve", "df", "Plot PSA values by period."),
    "period-spectra": PlotCommand("spatial_vtk.metrics.plot.periods.plot_period_spectra", "spectra_df", "Plot period spectra."),
    "period-spectrogram": PlotCommand("spatial_vtk.metrics.plot.periods.plot_period_spectrogram", "spectrogram_df", "Plot a period spectrogram."),
    "vs30-scatter": PlotCommand("spatial_vtk.metrics.plot.site_terms.plot_vs30_scatter", "df", "Plot metric values against Vs30."),
    "geology-boxplot": PlotCommand("spatial_vtk.metrics.plot.site_terms.plot_geology_boxplot", "df", "Plot metric values by geologic class."),
    "metric-trend": PlotCommand("spatial_vtk.metrics.plot.trends.plot_metric_trend", "df", "Plot a general metric trend."),
    "residuals-vs-distance": PlotCommand("spatial_vtk.metrics.plot.trends.plot_residuals_vs_distance", "df", "Plot residuals against distance."),
    "residuals-vs-depth": PlotCommand("spatial_vtk.metrics.plot.trends.plot_residuals_vs_depth", "df", "Plot residuals against event depth."),
    "score-trends": PlotCommand("spatial_vtk.metrics.plot.trends.plot_score_trends", "df", "Plot score trends."),
    "phase-delay-vs-distance": PlotCommand("spatial_vtk.metrics.plot.trends.plot_phase_delay_vs_distance", "df", "Plot phase delay against distance."),
    "scatterplot": PlotCommand("spatial_vtk.spatial.plot.metrics.scatterplot", "data", "Plot any metric-table variable against another variable."),
    "boxplot": PlotCommand("spatial_vtk.spatial.plot.metrics.boxplot", "data", "Plot metric distributions by categorical variables."),
    "heatmap": PlotCommand("spatial_vtk.spatial.plot.metrics.heatmap", "data", "Plot categorical metric summaries as a heatmap."),
}


SPATIAL_PLOT_COMMANDS: dict[str, PlotCommand] = {
    "correlogram": PlotCommand("spatial_vtk.spatial.plot.correlation.plot_correlogram", "distance_df", "Plot a spatial correlogram."),
    "semivariogram": PlotCommand("spatial_vtk.spatial.plot.correlation.plot_semivariogram", "distance_df", "Plot a semivariogram."),
    "directional-correlogram": PlotCommand("spatial_vtk.spatial.plot.correlation.plot_directional_correlogram", "directional_df", "Plot directional spatial correlations.", table_aliases={"fit": "fit_df"}),
    "block-holdout-scatter": PlotCommand("spatial_vtk.spatial.plot.correlation.plot_block_holdout_scatter", "prediction_df", "Plot observed versus held-out predictions."),
    "cluster-solution-scores": PlotCommand("spatial_vtk.spatial.plot.correlation.plot_cluster_solution_scores", "score_df", "Plot clustering solution scores."),
    "cluster-feature-heatmap": PlotCommand("spatial_vtk.spatial.plot.correlation.plot_cluster_feature_heatmap", "feature_summary_df", "Plot cluster feature summaries."),
    "pattern-similarity": PlotCommand("spatial_vtk.spatial.plot.correlation.plot_pattern_similarity", "stations", "Plot observed/synthetic pattern similarity."),
    "azimuthal-residuals": PlotCommand("spatial_vtk.spatial.plot.metrics.plot_azimuthal_residuals", "df", "Plot residuals by azimuth."),
    "path-bin-summary": PlotCommand("spatial_vtk.spatial.plot.metrics.plot_path_bin_summary", "path_summary_df", "Plot path-bin summary values."),
    "residual-correlation": PlotCommand("spatial_vtk.spatial.plot.metrics.plot_residual_correlation", "correlation_df", "Plot residual correlation values."),
    "polar-residuals": PlotCommand("spatial_vtk.spatial.plot.metrics.plot_polar_residuals", "df", "Plot residuals in polar coordinates."),
    "pca-explained-variance": PlotCommand("spatial_vtk.spatial.plot.pca.plot_pca_explained_variance", "explained_variance_df", "Plot PCA explained variance."),
    "pca-feature-loadings": PlotCommand("spatial_vtk.spatial.plot.pca.plot_pca_feature_loadings", "feature_loadings_df", "Plot PCA feature loadings."),
}


SPATIAL_MAP_COMMANDS: dict[str, PlotCommand] = {
    "station-bias": PlotCommand("spatial_vtk.spatial.map.correlation.plot_station_bias_map", "station_df", "Map station bias values."),
    "cluster": PlotCommand("spatial_vtk.spatial.map.correlation.plot_cluster_map", "assignments_df", "Map cluster assignments."),
    "redcap-cluster": PlotCommand("spatial_vtk.spatial.map.correlation.plot_redcap_cluster_map", "redcap_df", "Map REDCAP cluster values."),
    "block-holdout-error": PlotCommand("spatial_vtk.spatial.map.correlation.plot_block_holdout_error_map", "prediction_df", "Map block-holdout prediction errors."),
    "pca-mode": PlotCommand("spatial_vtk.spatial.map.pca.plot_pca_mode_map", "station_scores_df", "Map one PCA spatial mode."),
    "station-metric": PlotCommand("spatial_vtk.spatial.map.metrics.plot_station_metric_map", "df", "Map station metric values."),
    "score": PlotCommand("spatial_vtk.spatial.map.metrics.plot_score_map", "df", "Map score values."),
    "residual-grid": PlotCommand("spatial_vtk.spatial.map.metrics.plot_residual_grid", "grid_df", "Map residual grid values."),
    "metric-by-model": PlotCommand("spatial_vtk.spatial.map.metrics.plot_metric_map_by_model", "df", "Map metric values by model."),
    "model-improvement": PlotCommand("spatial_vtk.spatial.map.metrics.plot_model_improvement_map", "df", "Map model improvement values."),
    "event-residual": PlotCommand("spatial_vtk.spatial.map.path.plot_event_residual_map", "df", "Map event residual paths."),
    "corridor": PlotCommand("spatial_vtk.spatial.map.path.plot_corridor_map", "corridors_df", "Map corridor selections.", table_aliases={"stations": "stations_df", "events": "events_df", "records": "records_df"}),
}


CONTEXT_VISUALIZE_COMMANDS: dict[str, PlotCommand] = {
    "station-event-context": PlotCommand("spatial_vtk.visualize.context.plot_station_event_context", "stations_df", "Plot station and event context.", table_aliases={"events": "events_df"}),
    "study-domain": PlotCommand("spatial_vtk.visualize.context.plot_study_domain_map", "stations_df", "Plot the study domain map.", table_aliases={"events": "events_df"}),
    "station-coverage": PlotCommand("spatial_vtk.visualize.context.plot_station_coverage", "event_station_df", "Plot station record coverage."),
    "event-coverage": PlotCommand("spatial_vtk.visualize.context.plot_event_coverage", "event_station_df", "Plot event record coverage."),
    "record-coverage": PlotCommand("spatial_vtk.visualize.context.plot_record_coverage", "records_df", "Plot record-window coverage."),
    "event-trace-comparison": PlotCommand("spatial_vtk.visualize.context.plot_event_trace_comparison", "records_df", "Plot event trace comparisons."),
    "distance-amplitude-diagnostics": PlotCommand("spatial_vtk.visualize.context.plot_distance_amplitude_diagnostics", "records_df", "Plot distance/amplitude diagnostics."),
    "event-magnitude-map": PlotCommand("spatial_vtk.visualize.context.plot_event_magnitude_map", "events_df", "Map events by magnitude."),
    "station-event-network": PlotCommand("spatial_vtk.visualize.context.plot_station_event_network_map", "stations_df", "Map station/event network geometry.", table_aliases={"events": "events_df"}),
    "station-event-beachball": PlotCommand("spatial_vtk.visualize.context.plot_station_event_beachball_map", "events_df", "Map station/event context with beachballs.", table_aliases={"stations": "stations_df"}),
}


QC_VISUALIZE_COMMANDS: dict[str, PlotCommand] = {
    "trace-inventory-samples": PlotCommand("spatial_vtk.visualize.qc.plot_trace_inventory_samples", "sample_df", "Plot sample QC traces."),
    "retention-summary": PlotCommand("spatial_vtk.visualize.qc.plot_retention_summary", "qc_df", "Plot QC retention summary."),
    "data-synthetic-availability": PlotCommand("spatial_vtk.visualize.qc.plot_data_synthetic_availability", "availability_df", "Plot observed/synthetic availability."),
    "event-station-retention": PlotCommand("spatial_vtk.visualize.qc.plot_event_station_retention_heatmap", "retention_df", "Plot retained comparison-pair percentages by station and event."),
    "post-qc-station-event-map": PlotCommand("spatial_vtk.visualize.qc.plot_post_qc_station_event_map", "records_df", "Map retained station/event records after QC."),
    "drop-cause-diagnostics": PlotCommand("spatial_vtk.visualize.qc.plot_qc_drop_cause_diagnostics", "qc_df", "Plot QC drop-cause diagnostics."),
}


WAVEFORM_VISUALIZE_COMMANDS: dict[str, PlotCommand] = {
    "record-section": PlotCommand("spatial_vtk.visualize.waveforms.plot_record_section", "records", "Plot a waveform record section."),
    "observed-synthetic-record-section": PlotCommand("spatial_vtk.visualize.waveforms.plot_observed_synthetic_record_section", "records_df", "Plot observed/synthetic record sections."),
    "waveform-overlay-matrix": PlotCommand("spatial_vtk.visualize.waveforms.plot_waveform_overlay_matrix", "records_df", "Plot waveform overlay matrix."),
    "event-radial-trace-section": PlotCommand("spatial_vtk.visualize.waveforms.plot_event_radial_trace_section", "records_df", "Plot event radial trace section."),
    "station-event-waveform-map": PlotCommand("spatial_vtk.visualize.waveforms.plot_station_event_waveform_map", "records_df", "Map station/event waveforms."),
}


PLOT_COMMAND_GROUPS: dict[str, dict[str, PlotCommand]] = {
    "metrics": METRICS_PLOT_COMMANDS,
    "spatial": SPATIAL_PLOT_COMMANDS,
}


MAP_COMMAND_GROUPS: dict[str, dict[str, PlotCommand]] = {
    "spatial": SPATIAL_MAP_COMMANDS,
}


VISUALIZE_COMMAND_GROUPS: dict[str, dict[str, PlotCommand]] = {
    "context": CONTEXT_VISUALIZE_COMMANDS,
    "qc": QC_VISUALIZE_COMMANDS,
    "waveforms": WAVEFORM_VISUALIZE_COMMANDS,
}


AUTO_PLOT_OPTION_KEYS = frozenset({"add_basemap", "basemap_source", "bounds"})


def main(argv: list[str] | None = None) -> int:
    """Run the public ``svtk`` command.

    Parameters
    ----------
    argv
        Optional command-line arguments without the program name.

    Returns
    -------
    int
        Process-style exit code.
    """

    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "version", False):
        from spatial_vtk import __version__

        print(__version__)
        return 0
    if not hasattr(args, "handler"):
        parser.print_help()
        return 0
    return int(args.handler(args) or 0)


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level command parser.

    Parameters
    ----------
    None

    Returns
    -------
    argparse.ArgumentParser
        Configured CLI parser.
    """

    parser = argparse.ArgumentParser(
        prog="svtk",
        description="Spatial validation tools for ground-motion simulations.",
    )
    parser.add_argument("--version", action="store_true", help="Print the package version and exit.")
    subparsers = parser.add_subparsers(dest="command")
    _add_config_commands(subparsers)
    _add_io_commands(subparsers)
    _add_qc_commands(subparsers)
    _add_metrics_commands(subparsers)
    _add_plot_commands(subparsers)
    _add_map_commands(subparsers)
    _add_visualize_commands(subparsers)
    _add_dashboard_commands(subparsers)
    _add_call_command(subparsers)
    return parser


def _add_config_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register configuration CLI commands.

    Parameters
    ----------
    subparsers
        Top-level argparse subparser collection.

    Returns
    -------
    None
    """

    config = subparsers.add_parser("config", help="Inspect Spatial-VTK configuration.")
    config_sub = config.add_subparsers(dest="config_command", required=True)

    find = config_sub.add_parser("find", help="Print the resolved config path.")
    find.add_argument("--config", default=None, help="Explicit config file.")
    find.add_argument("--start-dir", default=None, help="Directory used for config discovery.")
    find.set_defaults(handler=_cmd_config_find)

    show = config_sub.add_parser("show", help="Print the active config or one section.")
    show.add_argument("--config", default=None, help="Explicit config file.")
    show.add_argument("--run-scenario", default=None, help="Apply one named run_scenarios overlay before printing.")
    show.add_argument("--section", default=None, help="Optional dotted section key.")
    show.add_argument("--json", action="store_true", help="Write JSON instead of YAML.")
    show.set_defaults(handler=_cmd_config_show)

    bounds = config_sub.add_parser("bounds", help="List configured named bounds presets.")
    bounds.add_argument("--config", default=None, help="Explicit config file.")
    bounds.add_argument("--run-scenario", default=None, help="Apply one named run_scenarios overlay before listing bounds.")
    bounds.add_argument("--json", action="store_true", help="Write JSON instead of YAML.")
    bounds.set_defaults(handler=_cmd_config_bounds)


def _add_io_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register input/output CLI commands."""

    io = subparsers.add_parser("io", help="Prepare metadata and input inventories.")
    io_sub = io.add_subparsers(dest="io_command", required=True)

    stations = io_sub.add_parser("prepare-stations", help="Normalize station metadata column names.")
    stations.add_argument("--input", required=True, help="Station CSV/parquet path.")
    stations.add_argument("--output", required=True, help="Output CSV/parquet path.")
    stations.set_defaults(handler=_cmd_io_prepare_stations)

    events = io_sub.add_parser("prepare-events", help="Normalize event metadata column names.")
    events.add_argument("--input", required=True, help="Event CSV/parquet path.")
    events.add_argument("--output", required=True, help="Output CSV/parquet path.")
    events.set_defaults(handler=_cmd_io_prepare_events)

    master_stations = io_sub.add_parser("master-stations", help="Build a master station list from one or more tables.")
    master_stations.add_argument("--input", nargs="+", required=True, help="Station CSV/parquet paths.")
    master_stations.add_argument("--output", required=True, help="Output CSV path.")
    master_stations.set_defaults(handler=_cmd_io_master_stations)

    master_events = io_sub.add_parser("master-events", help="Build a master event list from one or more tables.")
    master_events.add_argument("--input", nargs="+", required=True, help="Event CSV/parquet paths.")
    master_events.add_argument("--output", required=True, help="Output CSV path.")
    master_events.set_defaults(handler=_cmd_io_master_events)

    inventory = io_sub.add_parser("inventory", help="Build a lightweight observed/synthetic file inventory.")
    inventory.add_argument("--observed-root", required=True, help="Observed waveform root directory.")
    inventory.add_argument("--synthetic-root", required=True, help="Synthetic waveform root directory.")
    inventory.add_argument("--output", required=True, help="Output CSV/parquet path.")
    inventory.add_argument("--suffix", action="append", default=None, help="Waveform suffix to include. May be repeated.")
    inventory.add_argument("--relative-to", default=None, help="Base path used for relative inventory paths.")
    inventory.add_argument("--no-sha256", action="store_true", help="Skip SHA-256 hashing.")
    inventory.set_defaults(handler=_cmd_io_inventory)

    preprocess = io_sub.add_parser("preprocess-waveforms", help="Filter/resample waveform files and write reusable processed copies.")
    preprocess.add_argument("--records", required=True, help="Event-station CSV/parquet with waveform path columns.")
    preprocess.add_argument(
        "--output-root",
        default=None,
        help="Folder where processed waveforms and metadata tables are written. Defaults to outputs.preprocessed_waveforms from config.",
    )
    preprocess.add_argument("--config", default=None, help="Spatial-VTK config file.")
    preprocess.add_argument("--run-scenario", default=None, help="Apply one named run_scenarios overlay.")
    preprocess.add_argument("--observed-column", default=None, help="Observed waveform path column. Auto-detected when omitted.")
    preprocess.add_argument("--synthetic-column", default=None, help="Synthetic waveform path column. Auto-detected when omitted.")
    preprocess.add_argument("--event-id-col", default="event_id", help="Event ID column in --records.")
    preprocess.add_argument("--lowpass-hz", type=float, default=None, help="Optional lowpass cutoff in Hz.")
    preprocess.add_argument("--highpass-hz", type=float, default=None, help="Optional highpass cutoff in Hz.")
    preprocess.add_argument("--bandpass-low-hz", type=float, default=None, help="Optional bandpass low corner in Hz.")
    preprocess.add_argument("--bandpass-high-hz", type=float, default=None, help="Optional bandpass high corner in Hz.")
    preprocess.add_argument("--resample-hz", type=float, default=None, help="Optional target sampling rate in Hz.")
    preprocess.add_argument("--filter-order", type=int, default=None, help="Butterworth filter order.")
    preprocess.add_argument("--overwrite", action="store_true", help="Rewrite processed files even if they already exist.")
    preprocess.add_argument("--continue-on-error", action="store_true", help="Record failed files in the manifest instead of stopping.")
    preprocess.add_argument("--keep-input-columns", action="store_true", help="Keep original waveform path columns pointed at raw files.")
    preprocess.set_defaults(handler=_cmd_io_preprocess_waveforms)


def _add_qc_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register quality-control CLI commands."""

    qc = subparsers.add_parser("qc", help="Prepare QC review outputs.")
    qc_sub = qc.add_subparsers(dest="qc_command", required=True)

    queue = qc_sub.add_parser("manual-queue", help="Export a manual-QC review queue from trace summary rows.")
    queue.add_argument("--trace-summary", required=True, help="Trace-summary CSV/parquet path.")
    queue.add_argument("--output", required=True, help="Output manual-review queue CSV.")
    queue.add_argument("--event-id", default="", help="Optional event id filter.")
    queue.add_argument("--station-family", default="all", help="Optional station-family filter.")
    queue.add_argument("--component", default="all", help="Optional component filter.")
    queue.add_argument("--station-contains", default="", help="Optional station substring filter.")
    queue.add_argument("--band", default=None, help="Optional passband filter.")
    queue.set_defaults(handler=_cmd_qc_manual_queue)

    slurm = qc_sub.add_parser("slurm", help="Write a SLURM script for QC inventory generation.")
    slurm.add_argument("--event-stations", required=True, help="Prepared event-station table.")
    slurm.add_argument("--output", required=True, help="Output SLURM script path.")
    slurm.add_argument("--config", required=True, help="Config file containing compute.slurm or qc.slurm settings.")
    slurm.add_argument("--run-scenario", default=None, help="Apply one named run_scenarios overlay.")
    slurm.add_argument("--trace-output", default=None, help="Output waveform QC table path.")
    slurm.add_argument("--inventory-output", default=None, help="Output metric QC inventory path.")
    slurm.add_argument("--overlap-inventory-output", default=None, help="Output overlap-only metric QC inventory path.")
    slurm.add_argument("--submit", action="store_true", help="Submit the script with sbatch after writing it.")
    slurm.set_defaults(handler=_cmd_qc_slurm)


def _add_metrics_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register metric workflow CLI commands."""

    metrics = subparsers.add_parser("metrics", help="Plan, run, and post-process metric calculations.")
    metrics_sub = metrics.add_subparsers(dest="metrics_command", required=True)

    plan = metrics_sub.add_parser("plan", help="Plan metric tasks from inventories and config.")
    plan.add_argument("--observed-inventory", default=None, help="Observed metric waveform inventory.")
    plan.add_argument("--synthetic-inventory", default=None, help="Synthetic metric waveform inventory.")
    plan.add_argument("--config", default=None, help="Spatial-VTK config file.")
    plan.add_argument("--run-scenario", default=None, help="Apply one named run_scenarios overlay.")
    plan.add_argument("--metric", action="append", dest="metrics", default=None, help="Metric override. Repeat or use 'all'.")
    plan.add_argument("--metric-group", action="append", dest="metric_groups", default=None, help="Metric-group override. Repeat or use 'all'.")
    plan.add_argument("--component", action="append", dest="components", default=None, help="Component override. Repeat for multiple components.")
    plan.add_argument("--passband", action="append", dest="passbands", default=None, help="Period passband override, such as 1-2. Repeat for multiple bands.")
    plan.add_argument("--model", action="append", dest="models", default=None, help="Synthetic model override. Repeat for multiple models.")
    plan.add_argument("--transform", action="append", dest="transforms", default=None, help="Metric transform override. Repeat for multiple transforms.")
    plan.add_argument("--output-mode", default=None, help="Metric output mode override.")
    plan.add_argument("--require-source-overlap", action="store_true", help="Only plan metric tasks for events or event-station rows with both observed and synthetic data.")
    plan.add_argument("--source-overlap-scope", choices=("event", "event_station"), default=None, help="Overlap scope for --require-source-overlap.")
    plan.add_argument("--output", required=True, help="Output task table or manifest path.")
    plan.add_argument("--manifest", action="store_true", help="Write a JSON manifest instead of a task table.")
    plan.add_argument("--batch-output-dir", default=None, help="Batch output directory when writing a manifest.")
    plan.add_argument("--batch-size", type=int, default=100, help="Tasks per batch when writing a manifest.")
    plan.add_argument("--qc-table", default=None, help="Optional QC inventory recorded in a manifest.")
    plan.add_argument("--no-qc", action="store_true", help="Do not mark planned tasks as QC-filtered by default.")
    plan.set_defaults(handler=_cmd_metrics_plan)

    run = metrics_sub.add_parser("run", help="Run a task table locally.")
    run.add_argument("--tasks", required=True, help="Task CSV/parquet path.")
    run.add_argument("--output", required=True, help="Output metric CSV/parquet path.")
    run.add_argument("--qc-table", default=None, help="Optional QC inventory.")
    run.set_defaults(handler=_cmd_metrics_run)

    batch = metrics_sub.add_parser("run-batch", help="Run one batch from a metric manifest.")
    batch.add_argument("--manifest", required=True, help="Metric workflow manifest JSON.")
    batch.add_argument("--batch-index", type=int, required=True, help="Batch index to run.")
    batch.add_argument("--overwrite", action="store_true", help="Replace an existing batch output.")
    batch.set_defaults(handler=_cmd_metrics_run_batch)

    merge = metrics_sub.add_parser("merge-batches", help="Merge metric manifest batch outputs.")
    merge.add_argument("--manifest", required=True, help="Metric workflow manifest JSON.")
    merge.add_argument("--output", required=True, help="Merged output CSV/parquet path.")
    merge.add_argument("--allow-missing", action="store_true", help="Allow missing batch outputs.")
    merge.set_defaults(handler=_cmd_metrics_merge_batches)

    outputs = metrics_sub.add_parser("outputs", help="Write standard downstream metric outputs.")
    outputs.add_argument("--metrics", required=True, help="Metric workflow rows CSV/parquet path.")
    outputs.add_argument("--output-dir", required=True, help="Output directory.")
    outputs.add_argument("--events", default=None, help="Optional event metadata CSV/parquet path.")
    outputs.add_argument("--stations", default=None, help="Optional station metadata CSV/parquet path.")
    outputs.add_argument("--residual-column", default=None, help="Column exposed as canonical residual.")
    outputs.add_argument("--score-column", default=None, help="Column exposed as canonical score.")
    outputs.add_argument("--format", choices=("parquet", "csv"), default="parquet", help="Table output format.")
    outputs.add_argument("--dashboard-partitioned", action="store_true", help="Partition dashboard metric rows.")
    outputs.set_defaults(handler=_cmd_metrics_outputs)

    slurm = metrics_sub.add_parser("slurm", help="Write a SLURM array script for a metric manifest.")
    slurm.add_argument("--manifest", required=True, help="Metric workflow manifest JSON.")
    slurm.add_argument("--output", required=True, help="Output SLURM script path.")
    slurm.add_argument("--config", required=True, help="Config file containing metrics.slurm settings.")
    slurm.add_argument("--run-scenario", default=None, help="Apply one named run_scenarios overlay.")
    slurm.add_argument("--submit", action="store_true", help="Submit the script with sbatch after writing it.")
    slurm.set_defaults(handler=_cmd_metrics_slurm)


def _add_dashboard_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register dashboard CLI commands."""

    dashboard = subparsers.add_parser("dashboard", help="Prepare and launch Streamlit dashboards.")
    dashboard_sub = dashboard.add_subparsers(dest="dashboard_command", required=True)

    metrics = dashboard_sub.add_parser("metrics", help="Launch the metrics Streamlit dashboard.")
    metrics.add_argument("--metrics-root", required=True, help="Dashboard metric dataset root.")
    metrics.add_argument("--summary-root", required=True, help="Dashboard summary dataset root.")
    metrics.add_argument("--port", type=int, default=8501, help="Streamlit server port.")
    metrics.add_argument("--address", default="127.0.0.1", help="Streamlit server address.")
    metrics.add_argument("--show", action="store_true", help="Open Streamlit in a browser when supported.")
    metrics.set_defaults(handler=_cmd_dashboard_metrics)

    qc = dashboard_sub.add_parser("qc", help="Launch the QC Streamlit dashboard.")
    qc.add_argument("--trace-summary", required=True, help="Trace-summary CSV/parquet path.")
    qc.add_argument("--port", type=int, default=8502, help="Streamlit server port.")
    qc.add_argument("--address", default="127.0.0.1", help="Streamlit server address.")
    qc.add_argument("--show", action="store_true", help="Open Streamlit in a browser when supported.")
    qc.set_defaults(handler=_cmd_dashboard_qc)


def _add_plot_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register non-map plotting CLI commands."""

    plot = subparsers.add_parser("plot", help="Create static metric and spatial plots.")
    plot_sub = plot.add_subparsers(dest="plot_group", required=True)
    _add_registered_command_group(plot_sub, "metrics", METRICS_PLOT_COMMANDS, "Metric plots.")
    _add_registered_command_group(plot_sub, "spatial", SPATIAL_PLOT_COMMANDS, "Spatial-statistics plots.")


def _add_map_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register map-producing CLI commands."""

    map_parser = subparsers.add_parser("map", help="Create static map figures.")
    map_sub = map_parser.add_subparsers(dest="map_group", required=True)
    _add_registered_command_group(map_sub, "spatial", SPATIAL_MAP_COMMANDS, "Spatial map figures.", include_map_options=True)


def _add_visualize_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register higher-level visualization CLI commands."""

    visualize = subparsers.add_parser("visualize", help="Create context, QC, and waveform figures.")
    visualize_sub = visualize.add_subparsers(dest="visualize_group", required=True)
    _add_registered_command_group(visualize_sub, "context", CONTEXT_VISUALIZE_COMMANDS, "Context figures and maps.", include_map_options=True)
    _add_registered_command_group(visualize_sub, "qc", QC_VISUALIZE_COMMANDS, "QC and retention figures.", include_map_options=True)
    _add_registered_command_group(visualize_sub, "waveforms", WAVEFORM_VISUALIZE_COMMANDS, "Waveform figures and maps.", include_map_options=True)


def _add_registered_command_group(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    group_name: str,
    commands: dict[str, PlotCommand],
    help_text: str,
    *,
    include_map_options: bool = False,
) -> None:
    """Register one group of registry-backed figure commands."""

    group = subparsers.add_parser(group_name, help=help_text)
    group_sub = group.add_subparsers(dest=f"{group_name}_figure", required=True)
    list_cmd = group_sub.add_parser("list", help="List available figure commands in this group.")
    list_cmd.set_defaults(handler=_cmd_list_registered_plots, registry=commands)
    for command_name, spec in sorted(commands.items()):
        command = group_sub.add_parser(command_name, help=spec.help)
        _add_figure_io_arguments(command, spec, include_map_options=include_map_options)
        command.set_defaults(handler=_cmd_registered_plot, plot_spec=spec)


def _add_figure_io_arguments(parser: argparse.ArgumentParser, spec: PlotCommand, *, include_map_options: bool) -> None:
    """Add shared file-backed plotting arguments."""

    if spec.primary_arg is not None:
        parser.add_argument("--input", required=True, help=f"Input CSV/parquet table for the {spec.primary_arg} argument.")
    parser.add_argument("--output", required=True, help="Output figure path.")
    parser.add_argument("--table", action="append", default=(), help="Extra table as argument_name=path. May be repeated.")
    parser.add_argument("--kwargs", nargs="*", default=(), help="Extra function keyword arguments as key=value.")
    parser.add_argument("--kwargs-json", default=None, help="Extra function keyword arguments as a JSON/YAML mapping.")
    for option in sorted((spec.table_aliases or {}).keys()):
        parser.add_argument(f"--{option.replace('_', '-')}", default=None, help=f"Convenience table path for the {spec.table_aliases[option]} argument.")
    if include_map_options:
        parser.add_argument("--config", default=None, help="Optional Spatial-VTK config for named bounds.")
        parser.add_argument("--run-scenario", default=None, help="Apply one named run_scenarios overlay.")
        parser.add_argument("--bounds", default=None, help="Named bounds from config or comma-separated lon_min,lon_max,lat_min,lat_max.")
        parser.add_argument("--no-basemap", action="store_true", help="Disable basemap rendering for map figures.")
        parser.add_argument("--basemap-source", default=None, help="Optional contextily basemap source.")


def _add_call_command(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the generic Python-call CLI command."""

    call = subparsers.add_parser("call", help="Call any importable Spatial-VTK Python function.")
    call.add_argument("function", help="Import path, for example spatial_vtk.config.labels.metric_display_name.")
    call.add_argument("--args", nargs="*", default=(), help="Positional arguments parsed as YAML scalars/sequences.")
    call.add_argument("--args-json", default=None, help="JSON/YAML list of positional arguments.")
    call.add_argument("--kwargs", nargs="*", default=(), help="Keyword arguments as key=value, parsed as YAML values.")
    call.add_argument("--kwargs-json", default=None, help="JSON/YAML mapping of keyword arguments.")
    call.add_argument("--output", default=None, help="Optional output path for DataFrame/dict/list results.")
    call.set_defaults(handler=_cmd_call)


def _cmd_config_find(args: argparse.Namespace) -> int:
    """Run ``svtk config find``."""

    from spatial_vtk.config import find_config_file

    path = find_config_file(args.config, start_dir=args.start_dir)
    print(path or "")
    return 0 if path is not None else 1


def _cmd_config_show(args: argparse.Namespace) -> int:
    """Run ``svtk config show``."""

    from spatial_vtk.config import SpatialVTKConfig

    config = SpatialVTKConfig.from_file(args.config, run_scenario=args.run_scenario)
    payload = config.section(args.section) if args.section else config.data
    _print_payload(payload, as_json=args.json)
    return 0


def _cmd_config_bounds(args: argparse.Namespace) -> int:
    """Run ``svtk config bounds``."""

    from spatial_vtk.config import SpatialVTKConfig

    config = SpatialVTKConfig.from_file(args.config, run_scenario=args.run_scenario)
    _print_payload(config.bounds_presets(), as_json=args.json)
    return 0


def _cmd_io_prepare_stations(args: argparse.Namespace) -> int:
    """Run ``svtk io prepare-stations``."""

    from spatial_vtk.io import prepare_station_metadata

    _write_table(prepare_station_metadata(_read_table(args.input)), args.output)
    return 0


def _cmd_io_prepare_events(args: argparse.Namespace) -> int:
    """Run ``svtk io prepare-events``."""

    from spatial_vtk.io import prepare_event_metadata

    _write_table(prepare_event_metadata(_read_table(args.input)), args.output)
    return 0


def _cmd_io_master_stations(args: argparse.Namespace) -> int:
    """Run ``svtk io master-stations``."""

    from spatial_vtk.io import build_master_station_list, write_master_station_list

    write_master_station_list(build_master_station_list(station_tables=args.input), args.output)
    return 0


def _cmd_io_master_events(args: argparse.Namespace) -> int:
    """Run ``svtk io master-events``."""

    from spatial_vtk.io import build_master_event_list, write_master_event_list

    write_master_event_list(build_master_event_list(event_tables=args.input), args.output)
    return 0


def _cmd_io_inventory(args: argparse.Namespace) -> int:
    """Run ``svtk io inventory``."""

    from spatial_vtk.io import DEFAULT_WAVEFORM_SUFFIXES, build_observed_synthetic_inventory

    suffixes = args.suffix or sorted(DEFAULT_WAVEFORM_SUFFIXES)
    df = build_observed_synthetic_inventory(
        args.observed_root,
        args.synthetic_root,
        suffixes=suffixes,
        relative_to=args.relative_to,
        include_sha256=not args.no_sha256,
    )
    _write_table(df, args.output)
    return 0


def _cmd_io_preprocess_waveforms(args: argparse.Namespace) -> int:
    """Run ``svtk io preprocess-waveforms``."""

    from spatial_vtk.config import SpatialVTKConfig
    from spatial_vtk.io import preprocess_waveform_files, waveform_preprocessing_from_config

    config = SpatialVTKConfig.from_file(args.config, run_scenario=args.run_scenario) if args.config or args.run_scenario else None
    settings = waveform_preprocessing_from_config(config)
    overrides = {
        "lowpass_hz": args.lowpass_hz,
        "highpass_hz": args.highpass_hz,
        "bandpass_low_hz": args.bandpass_low_hz,
        "bandpass_high_hz": args.bandpass_high_hz,
        "resample_hz": args.resample_hz,
        "filter_order": args.filter_order,
    }
    explicit = {key: value for key, value in overrides.items() if value is not None}
    if explicit:
        settings = replace(settings, **explicit)
    source_columns: dict[str, str] = {}
    if args.observed_column:
        source_columns["observed"] = args.observed_column
    if args.synthetic_column:
        source_columns["synthetic"] = args.synthetic_column
    result = preprocess_waveform_files(
        args.records,
        args.output_root,
        source_columns=source_columns or None,
        preprocessing=settings,
        config=config,
        event_id_col=args.event_id_col,
        overwrite=args.overwrite,
        continue_on_error=args.continue_on_error,
        replace_input_columns=not args.keep_input_columns,
    )
    _print_payload(
        {
            "event_station_records": str(result.event_station_path),
            "manifest": str(result.manifest_path),
            "trace_metadata": str(result.trace_metadata_path),
            "files": int(len(result.manifest)),
        },
        as_json=False,
    )
    return 0


def _cmd_qc_manual_queue(args: argparse.Namespace) -> int:
    """Run ``svtk qc manual-queue``."""

    from spatial_vtk.visualize.dashboard import filter_qc_dashboard_rows, write_manual_review_queue
    from spatial_vtk.visualize.qc import load_trace_qc_summary

    df = load_trace_qc_summary(args.trace_summary)
    filtered = filter_qc_dashboard_rows(
        df,
        event_filter=args.event_id,
        station_family=args.station_family,
        component_filter=args.component,
        station_query=args.station_contains,
        band=args.band,
    )
    write_manual_review_queue(filtered, args.output)
    return 0


def _cmd_qc_slurm(args: argparse.Namespace) -> int:
    """Run ``svtk qc slurm``."""

    from spatial_vtk.config import SpatialVTKConfig
    from spatial_vtk.qc.build.slurm import (
        slurm_settings_from_config,
        submit_qc_slurm_job,
        write_qc_slurm_script,
    )

    config = SpatialVTKConfig.from_file(args.config, run_scenario=args.run_scenario)
    settings = slurm_settings_from_config(config)
    if args.submit:
        submission = submit_qc_slurm_job(
            args.event_stations,
            args.output,
            settings,
            config_path=args.config,
            run_scenario=args.run_scenario,
            trace_qc_output=args.trace_output,
            qc_inventory_output=args.inventory_output,
            qc_inventory_overlap_output=args.overlap_inventory_output,
        )
        print(submission.stdout or f"submitted {submission.script_path}")
        return int(submission.returncode)
    path = write_qc_slurm_script(
        args.event_stations,
        args.output,
        settings,
        config_path=args.config,
        run_scenario=args.run_scenario,
        trace_qc_output=args.trace_output,
        qc_inventory_output=args.inventory_output,
        qc_inventory_overlap_output=args.overlap_inventory_output,
    )
    print(path)
    return 0


def _cmd_metrics_plan(args: argparse.Namespace) -> int:
    """Run ``svtk metrics plan``."""

    from spatial_vtk.config import SpatialVTKConfig
    from spatial_vtk.io import metric_plan_from_config
    from spatial_vtk.metrics.workflow import plan_metric_tasks, tasks_to_frame, write_task_manifest

    config = SpatialVTKConfig.from_file(args.config, run_scenario=args.run_scenario)
    plan = metric_plan_from_config(config, command="metrics.calculate", overrides=_metric_plan_overrides(args))
    tasks = plan_metric_tasks(args.observed_inventory, args.synthetic_inventory, plan=plan, use_qc=not args.no_qc)
    if args.manifest:
        batch_dir = args.batch_output_dir or str(Path(args.output).with_suffix("")) + "_batches"
        write_task_manifest(tasks, args.output, output_dir=batch_dir, batch_size=args.batch_size, qc_table=args.qc_table)
    else:
        _write_table(tasks_to_frame(tasks), args.output)
    print(f"Planned {len(tasks)} metric tasks.")
    return 0


def _metric_plan_overrides(args: argparse.Namespace) -> dict[str, Any]:
    """Build explicit metric-plan config overrides from CLI flags."""

    overrides: dict[str, Any] = {}
    if getattr(args, "metrics", None):
        overrides["metrics"] = args.metrics
    if getattr(args, "metric_groups", None):
        overrides["groups"] = args.metric_groups
    if getattr(args, "components", None):
        overrides["components"] = args.components
    if getattr(args, "passbands", None):
        overrides["passbands"] = args.passbands
    if getattr(args, "models", None):
        overrides["models"] = args.models
    if getattr(args, "transforms", None):
        overrides["transforms"] = args.transforms
    if getattr(args, "output_mode", None):
        overrides["output_mode"] = args.output_mode
    if getattr(args, "require_source_overlap", False):
        overrides["require_source_overlap"] = True
    if getattr(args, "source_overlap_scope", None):
        overrides["source_overlap_scope"] = args.source_overlap_scope
    return overrides


def _cmd_metrics_run(args: argparse.Namespace) -> int:
    """Run ``svtk metrics run``."""

    from spatial_vtk.metrics.workflow import run_metric_tasks, tasks_from_frame, write_metric_rows

    tasks = tasks_from_frame(args.tasks)
    rows = run_metric_tasks(tasks, qc_table=args.qc_table)
    write_metric_rows(rows, args.output)
    print(f"Wrote {len(rows)} metric rows.")
    return 0


def _cmd_metrics_run_batch(args: argparse.Namespace) -> int:
    """Run ``svtk metrics run-batch``."""

    from spatial_vtk.metrics.workflow import run_manifest_batch

    path = run_manifest_batch(args.manifest, batch_index=args.batch_index, overwrite=args.overwrite)
    print(path)
    return 0


def _cmd_metrics_merge_batches(args: argparse.Namespace) -> int:
    """Run ``svtk metrics merge-batches``."""

    from spatial_vtk.metrics.workflow import merge_batch_outputs

    path = merge_batch_outputs(args.manifest, args.output, require_all=not args.allow_missing)
    print(path)
    return 0


def _cmd_metrics_outputs(args: argparse.Namespace) -> int:
    """Run ``svtk metrics outputs``."""

    from spatial_vtk.metrics.workflow import write_metric_outputs

    written = write_metric_outputs(
        args.metrics,
        args.output_dir,
        events=args.events,
        stations=args.stations,
        residual_column=args.residual_column,
        score_column=args.score_column,
        table_format=args.format,
        dashboard_partitioned=args.dashboard_partitioned,
    )
    _print_payload({key: str(path) for key, path in written.items()}, as_json=False)
    return 0


def _cmd_metrics_slurm(args: argparse.Namespace) -> int:
    """Run ``svtk metrics slurm``."""

    from spatial_vtk.config import SpatialVTKConfig
    from spatial_vtk.metrics.workflow import (
        slurm_settings_from_config,
        submit_metrics_slurm_job,
        write_metrics_slurm_script,
    )

    settings = slurm_settings_from_config(SpatialVTKConfig.from_file(args.config, run_scenario=args.run_scenario))
    if args.submit:
        submission = submit_metrics_slurm_job(args.manifest, args.output, settings)
        print(submission.stdout or f"submitted {submission.script_path}")
        return int(submission.returncode)
    path = write_metrics_slurm_script(args.manifest, args.output, settings)
    print(path)
    return 0


def _cmd_dashboard_metrics(args: argparse.Namespace) -> int:
    """Run ``svtk dashboard metrics``."""

    from spatial_vtk.visualize.dashboard import launch_metrics_dashboard

    process = launch_metrics_dashboard(metrics_root=args.metrics_root, summary_root=args.summary_root, server_address=args.address, server_port=args.port, show=args.show)
    print(f"Metrics dashboard running at http://{args.address}:{args.port} (pid {process.pid})")
    return 0


def _cmd_dashboard_qc(args: argparse.Namespace) -> int:
    """Run ``svtk dashboard qc``."""

    from spatial_vtk.visualize.dashboard import launch_qc_dashboard

    process = launch_qc_dashboard(trace_summary=args.trace_summary, server_address=args.address, server_port=args.port, show=args.show)
    print(f"QC dashboard running at http://{args.address}:{args.port} (pid {process.pid})")
    return 0


def _cmd_list_registered_plots(args: argparse.Namespace) -> int:
    """List available registered plotting commands."""

    for name, spec in sorted(args.registry.items()):
        input_note = f" --input <table>" if spec.primary_arg is not None else ""
        print(f"{name}{input_note} --output <path>  # {spec.help}")
    return 0


def _cmd_registered_plot(args: argparse.Namespace) -> int:
    """Run one registry-backed plotting command."""

    spec: PlotCommand = args.plot_spec
    function = _resolve_function(spec.function)
    kwargs = _registered_plot_kwargs(args, spec)
    _drop_unsupported_auto_plot_kwargs(function, kwargs)
    result = function(**kwargs)
    if result is not None and str(result) != str(kwargs["output_path"]):
        print(result)
    else:
        print(kwargs["output_path"])
    return 0


def _cmd_call(args: argparse.Namespace) -> int:
    """Run ``svtk call``."""

    function = _resolve_function(args.function)
    positional = list(_parse_sequence(args.args_json)) if args.args_json else [_parse_value(item) for item in args.args]
    kwargs = dict(_parse_mapping(args.kwargs_json)) if args.kwargs_json else {}
    kwargs.update(_parse_key_values(args.kwargs))
    result = function(*positional, **kwargs)
    if args.output:
        _write_result(result, args.output)
    else:
        _print_result(result)
    return 0


def _registered_plot_kwargs(args: argparse.Namespace, spec: PlotCommand) -> dict[str, Any]:
    """Build plotting keyword arguments from CLI table and scalar options."""

    kwargs: dict[str, Any] = {"output_path": args.output}
    if spec.primary_arg is not None:
        kwargs[spec.primary_arg] = _read_table(args.input)
    for table_arg, table_path in _parse_table_arguments(getattr(args, "table", ())):
        kwargs[table_arg] = _read_table(table_path)
    for option, table_arg in (spec.table_aliases or {}).items():
        value = getattr(args, option.replace("-", "_"), None)
        if value:
            kwargs[table_arg] = _read_table(value)
    if getattr(args, "kwargs_json", None):
        kwargs.update(_parse_mapping(args.kwargs_json))
    kwargs.update(_parse_key_values(getattr(args, "kwargs", ())))
    if hasattr(args, "no_basemap") and args.no_basemap:
        kwargs["add_basemap"] = False
    if getattr(args, "basemap_source", None):
        kwargs["basemap_source"] = args.basemap_source
    bounds = _resolve_cli_bounds(
        getattr(args, "bounds", None),
        getattr(args, "config", None),
        getattr(args, "run_scenario", None),
    )
    if bounds is not None:
        kwargs["bounds"] = bounds
    return kwargs


def _parse_table_arguments(items: Iterable[str]) -> list[tuple[str, str]]:
    """Parse repeated ``argument=path`` table options."""

    parsed: list[tuple[str, str]] = []
    for item in items:
        key, separator, value = str(item).partition("=")
        if not separator or not key or not value:
            raise ValueError(f"Expected --table argument_name=path, got: {item!r}")
        parsed.append((key, value))
    return parsed


def _resolve_cli_bounds(
    value: str | None,
    config_path: str | None,
    run_scenario: str | None = None,
) -> tuple[float, float, float, float] | None:
    """Resolve CLI bounds from a config keyword or explicit extent."""

    if not value:
        return None
    raw = str(value).strip()
    parts = [part.strip() for part in raw.split(",")]
    if len(parts) == 4:
        try:
            return tuple(float(part) for part in parts)  # type: ignore[return-value]
        except ValueError:
            pass
    from spatial_vtk.config import SpatialVTKConfig

    config = (
        SpatialVTKConfig.from_file(config_path, run_scenario=run_scenario)
        if config_path
        else SpatialVTKConfig.empty(root_dir=".")
    )
    bounds = config.resolve_bounds(raw)
    if bounds is None:
        raise ValueError(f"Could not resolve bounds: {value!r}")
    return bounds


def _drop_unsupported_auto_plot_kwargs(function: Any, kwargs: dict[str, Any]) -> None:
    """Remove automatic map options from functions that do not accept them."""

    signature = inspect.signature(function)
    if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()):
        return
    accepted = set(signature.parameters)
    for key in list(AUTO_PLOT_OPTION_KEYS):
        if key in kwargs and key not in accepted:
            kwargs.pop(key)


def _resolve_function(path: str):
    """Resolve an importable function path.

    Parameters
    ----------
    path
        Dotted function path.

    Returns
    -------
    callable
        Imported function or class.
    """

    if not path.startswith("spatial_vtk."):
        raise ValueError("svtk call only accepts import paths under spatial_vtk.")
    module_name, _, attr_name = path.rpartition(".")
    if not module_name or not attr_name:
        raise ValueError("Function path must include a module and attribute name.")
    module = importlib.import_module(module_name)
    target = getattr(module, attr_name)
    if not callable(target):
        raise TypeError(f"Import path is not callable: {path}")
    return target


def _read_table(path: str | Path) -> pd.DataFrame:
    """Read one CSV or Parquet table."""

    table_path = Path(path).expanduser()
    if table_path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(table_path)
    return pd.read_csv(table_path)


def _write_table(df: pd.DataFrame, path: str | Path) -> Path:
    """Write one CSV or Parquet table."""

    output = Path(path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() in {".parquet", ".pq"}:
        df.to_parquet(output, index=False)
    else:
        df.to_csv(output, index=False)
    print(output)
    return output


def _write_result(result: Any, output: str | Path) -> None:
    """Write a generic command result to disk."""

    path = Path(output).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(result, pd.DataFrame):
        _write_table(result, path)
    elif isinstance(result, (dict, list, tuple)):
        if path.suffix.lower() in {".yaml", ".yml"}:
            path.write_text(yaml.safe_dump(_jsonable(result), sort_keys=False), encoding="utf-8")
        else:
            path.write_text(json.dumps(_jsonable(result), indent=2), encoding="utf-8")
        print(path)
    elif hasattr(result, "savefig"):
        result.savefig(path, bbox_inches="tight")
        print(path)
    elif hasattr(result, "write_html"):
        result.write_html(path)
        print(path)
    else:
        path.write_text(str(result), encoding="utf-8")
        print(path)


def _print_result(result: Any) -> None:
    """Print a generic command result."""

    if isinstance(result, pd.DataFrame):
        print(result.to_csv(index=False))
    elif isinstance(result, (dict, list, tuple)):
        print(json.dumps(_jsonable(result), indent=2))
    else:
        print(result)


def _print_payload(payload: Any, *, as_json: bool) -> None:
    """Print a mapping/list payload as YAML or JSON."""

    if as_json:
        print(json.dumps(_jsonable(payload), indent=2))
    else:
        print(yaml.safe_dump(_jsonable(payload), sort_keys=False).strip())


def _parse_sequence(value: str) -> list[Any]:
    """Parse a JSON/YAML CLI sequence."""

    parsed = yaml.safe_load(value)
    if parsed is None:
        return []
    if not isinstance(parsed, list):
        raise ValueError("--args-json must parse to a list.")
    return parsed


def _parse_mapping(value: str) -> dict[str, Any]:
    """Parse a JSON/YAML CLI mapping."""

    parsed = yaml.safe_load(value)
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise ValueError("--kwargs-json must parse to a mapping.")
    return dict(parsed)


def _parse_key_values(items: Iterable[str]) -> dict[str, Any]:
    """Parse key=value CLI arguments."""

    parsed: dict[str, Any] = {}
    for item in items:
        key, separator, value = str(item).partition("=")
        if not separator or not key:
            raise ValueError(f"Expected key=value argument, got: {item!r}")
        parsed[key] = _parse_value(value)
    return parsed


def _parse_value(value: str) -> Any:
    """Parse one YAML scalar/list/dict value from CLI text."""

    try:
        return yaml.safe_load(value)
    except yaml.YAMLError:
        return value


def _jsonable(value: Any) -> Any:
    """Convert common Python objects into JSON/YAML-safe values."""

    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, pd.Series):
        return value.to_dict()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if inspect.isclass(value) or inspect.isfunction(value):
        return f"{value.__module__}.{value.__name__}"
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


__all__ = ["build_parser", "main"]
