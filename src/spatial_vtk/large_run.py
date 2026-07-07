"""Action-oriented helpers for large-run notebooks.

These helpers keep public large-run notebooks focused on scientific workflow
actions instead of setup/status plumbing. They delegate to the existing
workflow objects internally, suppress detailed readiness tables by default, and
print concise next-action messages for long-running or blocked steps.
"""

from __future__ import annotations

import os
import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

import pandas as pd


DisplayFn = Optional[Callable[[Any], Any]]


@dataclass
class LargeRunSession:
    """Resolved large-run config and notebook controls."""

    context: Any
    cfg: Any
    overwrite: bool
    submit_slurm: bool
    run_local: bool
    make_figures: bool
    preview_rows: int
    qc_chunksize: int
    dashboard_chunksize: int
    metric_batch_count: int
    preprocess_continue_on_error: bool


@dataclass
class LargeRunActionResult:
    """Compact user-facing result from one notebook action."""

    action: str
    message: str
    results: dict[str, Any] = field(default_factory=dict)
    details: pd.DataFrame | None = None

    def summary_frame(self) -> pd.DataFrame:
        """Return a compact summary suitable for optional display."""

        rows = [{"action": self.action, "message": self.message}]
        for name, result in self.results.items():
            rows.append({"action": name, "message": _result_message(result)})
        return pd.DataFrame(rows)


def activate_large_run(
    *,
    overwrite: bool | None = None,
    submit_slurm: bool | None = None,
    run_local: bool | None = None,
    make_figures: bool | None = None,
    preview_rows: int | None = None,
    qc_chunksize: int | None = None,
    dashboard_chunksize: int | None = None,
    metric_batch_count: int | None = None,
    preprocess_continue_on_error: bool | None = None,
) -> LargeRunSession:
    """Load the active large-run config and choose notebook controls.

    Pass explicit keyword values to override the environment-backed defaults
    for this notebook run. No workflow work is performed here.
    """

    from spatial_vtk.config import notebook_run_context, prepare_notebook_geospatial_environment

    prepare_notebook_geospatial_environment()
    context = notebook_run_context()
    updates: dict[str, Any] = {}
    for name, value in {
        "overwrite": overwrite,
        "submit_slurm": submit_slurm,
        "run_local": run_local,
        "preview_rows": preview_rows,
        "qc_chunksize": qc_chunksize,
        "dashboard_chunksize": dashboard_chunksize,
        "metric_batch_count": metric_batch_count,
        "preprocess_continue_on_error": preprocess_continue_on_error,
    }.items():
        if value is not None:
            updates[name] = value
    if updates:
        context = replace(context, **updates)
    session = LargeRunSession(
        context=context,
        cfg=context.cfg,
        overwrite=bool(context.overwrite),
        submit_slurm=bool(context.submit_slurm),
        run_local=bool(context.run_local),
        make_figures=bool(make_figures) if make_figures is not None else _env_bool("SVTK_MAKE_FIGURES"),
        preview_rows=int(context.preview_rows),
        qc_chunksize=int(context.qc_chunksize),
        dashboard_chunksize=int(context.dashboard_chunksize),
        metric_batch_count=int(context.metric_batch_count),
        preprocess_continue_on_error=bool(context.preprocess_continue_on_error),
    )
    _print_session(session)
    return session


def run_ingest(session: LargeRunSession) -> LargeRunActionResult:
    """Prepare metadata, preprocess waveforms, and build record coverage."""

    from spatial_vtk.io import load_standard_ingest_workflow_outputs

    _announce_long_step(
        "Ingest",
        "This prepares metadata and can submit waveform preprocessing for large runs.",
        session,
    )
    outputs = load_standard_ingest_workflow_outputs(cfg=session.cfg)
    results = {
        "metadata": outputs.run_metadata_step_if_needed(
            session.context,
            overwrite=session.overwrite,
            current_message="Prepared metadata tables are current; skipping.",
            script_name="step01_prepare_metadata.slurm",
            job_name="svtk-step01-metadata",
            run_local=True,
            display_fn=_ignore_display,
        ),
        "preprocessed_waveforms": outputs.run_preprocessing_step_if_needed(
            session.context,
            overwrite=session.overwrite,
            continue_on_error=session.preprocess_continue_on_error,
            verbose=True,
            current_message="Preprocessed waveform metadata is current; skipping preprocessing submission.",
            script_name="step01_preprocess_waveforms.slurm",
            job_name="svtk-step01-preprocess",
            walltime="24:00:00",
            memory="32G",
            cpus=1,
            display_fn=_ignore_display,
        ),
        "record_coverage": outputs.run_record_coverage_step_if_needed(
            session.context,
            overwrite=session.overwrite,
            missing_input_message="Trace metadata or event-station records are not ready yet.",
            current_message="Record coverage table is current; skipping.",
            script_name="step01_record_coverage.slurm",
            job_name="svtk-step01-coverage",
            walltime="12:00:00",
            memory="32G",
            cpus=1,
            display_fn=_ignore_display,
        ),
    }
    return _finish_action("Ingest", "Step 1 ingest outputs are ready for QC review.", results)


def make_context_figures(session: LargeRunSession, *, overwrite: bool | None = None) -> LargeRunActionResult:
    """Render Step 1 context figures when figure rendering is enabled."""

    if not session.make_figures:
        return _finish_action("Context figures", "Figure rendering is disabled for this run.", {})
    from spatial_vtk.config import notebook_figure_settings
    from spatial_vtk.io import load_standard_ingest_workflow_outputs

    outputs = load_standard_ingest_workflow_outputs(cfg=session.cfg)
    settings = notebook_figure_settings(
        "context",
        figure_subdir="step_01/default",
        default_make_figures=session.make_figures,
    )
    result = outputs.write_context_figures(settings, overwrite=session.overwrite if overwrite is None else bool(overwrite))
    return _finish_action("Context figures", "Context figures have been requested.", {"figures": result})


def run_quality_control(session: LargeRunSession) -> LargeRunActionResult:
    """Run full QC, overlap filtering, and compact QC summary outputs."""

    from spatial_vtk.config import metrics_settings_from_config
    from spatial_vtk.qc import load_standard_qc_workflow_outputs

    _announce_long_step(
        "Quality control",
        "This step can submit long-running QC work before compact review tables are written.",
        session,
    )
    outputs = load_standard_qc_workflow_outputs(cfg=session.cfg)
    metric_settings = metrics_settings_from_config(session.cfg)
    overlap_scope = metric_settings.source_overlap_scope
    results = {
        "qc_inventory": outputs.run_inventory_step_if_needed(
            session.context,
            overwrite=session.overwrite,
            current_message="Full QC outputs are current; skipping QC Slurm submission.",
            script_name="step02_build_qc_inventory.slurm",
            job_name="svtk-step02-qc",
            walltime="24:00:00",
            memory="64G",
            cpus=1,
            display_fn=_ignore_display,
        ),
        "overlap_qc": outputs.run_overlap_step_if_needed(
            session.context,
            overwrite=session.overwrite,
            chunksize=session.qc_chunksize,
            write_overwrite=True,
            verbose=True,
            scope=overlap_scope,
            current_message="Overlap QC sidecar is current; skipping.",
            script_name="step02_qc_overlap_sidecar.slurm",
            job_name="svtk-step02-overlap",
            walltime="12:00:00",
            memory="32G",
            cpus=1,
            display_fn=_ignore_display,
        ),
        "qc_summaries": outputs.run_summary_step_if_needed(
            session.context,
            overwrite=session.overwrite,
            chunksize=session.qc_chunksize,
            write_overwrite=True,
            verbose=True,
            current_message="Compact QC summary tables are current; skipping.",
            script_name="step02_qc_summary_tables.slurm",
            job_name="svtk-step02-summaries",
            walltime="12:00:00",
            memory="32G",
            cpus=1,
            display_fn=_ignore_display,
        ),
    }
    return _finish_action("Quality control", "QC review outputs are ready. Review the QC dashboard before metrics.", results)


def make_qc_figures(session: LargeRunSession) -> LargeRunActionResult:
    """Render compact QC figures when figure rendering is enabled."""

    if not session.make_figures:
        return _finish_action("QC figures", "Figure rendering is disabled for this run.", {})
    from spatial_vtk.config import notebook_figure_settings
    from spatial_vtk.qc import load_standard_qc_workflow_outputs

    outputs = load_standard_qc_workflow_outputs(cfg=session.cfg)
    settings = notebook_figure_settings(
        "qc",
        figure_subdir="step_02/default",
        default_make_figures=session.make_figures,
    )
    result = outputs.write_figures(settings, overwrite=session.overwrite)
    return _finish_action("QC figures", "QC figures have been requested.", {"figures": result})


def launch_qc_dashboard(session: LargeRunSession, *, show: bool = True) -> LargeRunActionResult:
    """Launch or print commands for the QC dashboard."""

    from spatial_vtk.config import notebook_dashboard_launch_commands
    from spatial_vtk.visualize import launch_configured_dashboards_from_notebook_settings

    dashboard_launch = notebook_dashboard_launch_commands(session.context)
    result = launch_configured_dashboards_from_notebook_settings(
        dashboard_launch,
        dashboards=("qc",),
        show=show,
    )
    return _finish_action("QC dashboard", "Use the QC dashboard to review retained/dropped records before metrics.", {"dashboard": result})


def calculate_metrics(session: LargeRunSession) -> LargeRunActionResult:
    """Build metric inventories, run metric batches, merge, and write outputs."""

    from spatial_vtk.metrics import load_standard_metric_workflow_outputs

    _announce_long_step(
        "Metrics",
        "This step can submit a metric Slurm array and may take hours on a full run.",
        session,
    )
    outputs = load_standard_metric_workflow_outputs(cfg=session.cfg)
    results = {
        "metric_inventories": outputs.run_inventory_step_if_needed(
            session.context,
            overwrite=session.overwrite,
            current_message="Metric waveform inventories are current; skipping.",
            script_name="step03_metric_inventories.slurm",
            job_name="svtk-step03-inventory",
            walltime="04:00:00",
            memory="32G",
            cpus=1,
            display_fn=_ignore_display,
        ),
        "metric_task_manifest": outputs.run_manifest_step_if_needed(
            session.context,
            overwrite=session.overwrite,
            batch_count=session.metric_batch_count,
            current_message="Metric manifest is current; skipping planning.",
            script_name="step03_metric_plan.slurm",
            job_name="svtk-step03-plan",
            run_local=True,
            display_fn=_ignore_display,
        ),
        "metric_batches": outputs.run_slurm_step_if_needed(
            session.context,
            overwrite=session.overwrite,
            submit=session.submit_slurm,
            incomplete_only=not session.overwrite,
            overwrite_batches=session.overwrite,
            script_name="step03_write_metric_slurm.slurm",
            job_name="svtk-step03-slurm",
            run_local=True,
            display_fn=_ignore_display,
        ),
        "metric_merge": outputs.run_merge_step_if_needed(
            session.context,
            overwrite=session.overwrite,
            script_name="step03_merge_metric_batches.slurm",
            job_name="svtk-step03-merge",
            walltime="02:00:00",
            memory="32G",
            cpus=1,
            display_fn=_ignore_display,
        ),
        "metric_outputs": outputs.run_downstream_outputs_step_if_needed(
            session.context,
            overwrite=session.overwrite,
            table_format="parquet",
            dashboard_partitioned=True,
            script_name="step03_metric_outputs.slurm",
            job_name="svtk-step03-outputs",
            walltime="08:00:00",
            memory="32G",
            cpus=1,
            display_fn=_ignore_display,
        ),
    }
    return _finish_action("Metrics", "Metric outputs are ready. Review the metrics dashboard before spatial analysis.", results)


def prepare_metrics_dashboard(session: LargeRunSession) -> LargeRunActionResult:
    """Prepare metrics dashboard datasets from metric outputs."""

    from spatial_vtk.visualize import prepare_configured_dashboard_datasets_from_notebook_settings

    _announce_long_step(
        "Metrics dashboard data",
        "This prepares dashboard-ready metric datasets for review before spatial analysis.",
        session,
    )
    preparation = prepare_configured_dashboard_datasets_from_notebook_settings(
        cfg=session.cfg,
        prepare_locally=False,
        overwrite=session.overwrite,
        partitioned=True,
        format="parquet",
        chunksize=session.dashboard_chunksize,
    )
    result = preparation.run_if_needed(
        session.context,
        partitioned=True,
        format="parquet",
        chunksize=session.dashboard_chunksize,
        display_fn=_ignore_display,
    )
    return _finish_action("Metrics dashboard data", "Metrics dashboard datasets are ready for review.", {"dashboard_data": result})


def launch_metrics_dashboard(session: LargeRunSession, *, show: bool = True) -> LargeRunActionResult:
    """Launch or print commands for the metrics dashboard."""

    from spatial_vtk.config import notebook_dashboard_launch_commands
    from spatial_vtk.visualize import launch_configured_dashboards_from_notebook_settings

    dashboard_launch = notebook_dashboard_launch_commands(session.context)
    result = launch_configured_dashboards_from_notebook_settings(
        dashboard_launch,
        dashboards=("metrics",),
        show=show,
    )
    return _finish_action("Metrics dashboard", "Use the metrics dashboard to review residuals and coverage before spatial analysis.", {"dashboard": result})


def make_metric_figures(session: LargeRunSession) -> LargeRunActionResult:
    """Render the main metric interpretation figures."""

    if not session.make_figures:
        return _finish_action("Metric figures", "Figure rendering is disabled for this run.", {})
    from spatial_vtk.config import notebook_figure_settings
    from spatial_vtk.metrics import load_standard_metric_workflow_outputs

    outputs = load_standard_metric_workflow_outputs(cfg=session.cfg)
    settings = notebook_figure_settings(
        "metric",
        figure_subdir="step_03_metrics/default",
        default_make_figures=session.make_figures,
        default_add_basemap=True,
    )
    if settings.compare_to is None:
        settings = replace(settings, compare_to="Z", comparison_table=True)
    elif not settings.comparison_table:
        settings = replace(settings, comparison_table=True)
    result = outputs.write_large_run_figure_suite(settings, overwrite=session.overwrite)
    return _finish_action("Metric figures", "Metric figures have been requested.", {"figures": result})


def make_filtered_metric_figures(
    session: LargeRunSession,
    figure_sets: Sequence[dict[str, Any]] | None = None,
) -> LargeRunActionResult:
    """Render additional metric figure suites for selected scientific subsets."""

    if not session.make_figures:
        return _finish_action("Filtered metric figures", "Figure rendering is disabled for this run.", {})
    if not figure_sets:
        return _finish_action("Filtered metric figures", "No filtered metric figure sets were requested.", {})
    from spatial_vtk.config import notebook_figure_settings
    from spatial_vtk.metrics import load_standard_metric_workflow_outputs

    outputs = load_standard_metric_workflow_outputs(cfg=session.cfg)
    base_settings = notebook_figure_settings(
        "metric",
        figure_subdir="step_03_metrics/default",
        default_make_figures=session.make_figures,
        default_add_basemap=True,
    )
    results: dict[str, Any] = {}
    for spec in figure_sets:
        settings = _filtered_metric_figure_settings(base_settings, spec)
        result = outputs.write_large_run_figure_suite(settings, overwrite=session.overwrite)
        results[_metric_figure_set_result_name(settings.figure_dir)] = result
    return _finish_action("Filtered metric figures", "Filtered metric figure sets have been requested.", results)


def run_spatial_statistics(session: LargeRunSession) -> LargeRunActionResult:
    """Build spatial statistics tables used for maps and interpretation."""

    from spatial_vtk.spatial import load_standard_spatial_workflow_output_status

    _announce_long_step(
        "Spatial statistics",
        "This builds spatial summary tables and optional plotting inputs from metric outputs.",
        session,
    )
    outputs = load_standard_spatial_workflow_output_status(cfg=session.cfg)
    results = {
        "spatial_summaries": outputs.run_summary_step_if_needed(
            session.context,
            overwrite=session.overwrite,
            verbose=True,
            script_name="step04_spatial_summaries.slurm",
            job_name="svtk-step04-spatial",
            walltime="12:00:00",
            memory="32G",
            cpus=4,
            display_fn=_ignore_display,
        ),
        "spatial_plot_inputs": outputs.run_derived_outputs_step_if_needed(
            session.context,
            overwrite=session.overwrite,
            verbose=True,
            script_name="step04_spatial_derived_outputs.slurm",
            job_name="svtk-step04-derived",
            walltime="04:00:00",
            memory="16G",
            cpus=2,
            display_fn=_ignore_display,
        ),
    }
    return _finish_action("Spatial statistics", "Spatial summary outputs are ready for figure interpretation.", results)


def make_spatial_figures(session: LargeRunSession) -> LargeRunActionResult:
    """Render spatial statistics figures when figure rendering is enabled."""

    if not session.make_figures:
        return _finish_action("Spatial figures", "Figure rendering is disabled for this run.", {})
    from spatial_vtk.config import notebook_figure_settings
    from spatial_vtk.spatial import load_standard_spatial_workflow_output_status

    outputs = load_standard_spatial_workflow_output_status(cfg=session.cfg)
    settings = notebook_figure_settings(
        "spatial",
        figure_subdir="step_04_spatial/default",
        default_make_figures=session.make_figures,
        default_add_basemap=True,
        default_sidecar_rows=1000,
    )
    result = outputs.write_figure_suite(settings, overwrite=session.overwrite)
    return _finish_action("Spatial figures", "Spatial figures have been requested.", {"figures": result})


def make_filtered_spatial_figures(
    session: LargeRunSession,
    figure_sets: Sequence[dict[str, Any]] | None = None,
) -> LargeRunActionResult:
    """Render additional spatial figure suites for selected scientific subsets."""

    if not session.make_figures:
        return _finish_action("Filtered spatial figures", "Figure rendering is disabled for this run.", {})
    if not figure_sets:
        return _finish_action("Filtered spatial figures", "No filtered spatial figure sets were requested.", {})
    from spatial_vtk.config import notebook_figure_settings
    from spatial_vtk.spatial import load_standard_spatial_workflow_output_status

    outputs = load_standard_spatial_workflow_output_status(cfg=session.cfg)
    base_settings = notebook_figure_settings(
        "spatial",
        figure_subdir="step_04_spatial/default",
        default_make_figures=session.make_figures,
        default_add_basemap=True,
        default_sidecar_rows=1000,
    )
    results: dict[str, Any] = {}
    for spec in figure_sets:
        settings = _filtered_spatial_figure_settings(base_settings, spec)
        result = outputs.write_figure_suite(settings, overwrite=session.overwrite)
        results[_figure_set_result_name(settings.figure_dir, "spatial_figures_")] = result
    return _finish_action("Filtered spatial figures", "Filtered spatial figure sets have been requested.", results)


def run_geojson_corridors(session: LargeRunSession) -> LargeRunActionResult:
    """Build GeoJSON region summaries and boundary corridor tables."""

    from spatial_vtk.spatial import load_standard_geojson_workflow_output_status

    _announce_long_step(
        "GeoJSON regions and corridors",
        "This builds region summaries and path/corridor tables from metric outputs.",
        session,
    )
    outputs = load_standard_geojson_workflow_output_status(cfg=session.cfg)
    results = {
        "region_summaries": outputs.run_geojson_summary_step_if_needed(
            session.context,
            overwrite=session.overwrite,
            chunksize=session.qc_chunksize,
            verbose=True,
            script_name="step05_geojson_summaries.slurm",
            job_name="svtk-step05-geojson",
            walltime="08:00:00",
            memory="32G",
            cpus=1,
            display_fn=_ignore_display,
        ),
        "corridors": outputs.run_corridor_step_if_needed(
            session.context,
            overwrite=session.overwrite,
            verbose=True,
            script_name="step05_corridors.slurm",
            job_name="svtk-step05-corridors",
            walltime="02:00:00",
            memory="8G",
            cpus=1,
            display_fn=_ignore_display,
        ),
    }
    return _finish_action("GeoJSON regions and corridors", "Region and corridor outputs are ready for figure interpretation.", results)


def make_region_corridor_figures(session: LargeRunSession) -> LargeRunActionResult:
    """Render GeoJSON region and corridor figures."""

    if not session.make_figures:
        return _finish_action("Region and corridor figures", "Figure rendering is disabled for this run.", {})
    from spatial_vtk.config import notebook_figure_settings
    from spatial_vtk.spatial import load_standard_geojson_plotting_inputs

    settings = notebook_figure_settings(
        "region",
        figure_subdir="step_05_regions/default",
        default_make_figures=session.make_figures,
        default_add_basemap=True,
        default_metric="PGA",
        default_passband="2-3 sec",
        default_sidecar_rows=1000,
    )
    waveform_settings = notebook_figure_settings(
        "waveform",
        figure_subdir="step_05_regions/default",
        default_make_figures=session.make_figures,
        default_add_basemap=True,
        default_sidecar_rows=1000,
    )
    inputs = load_standard_geojson_plotting_inputs(cfg=session.cfg)
    inputs = replace(
        inputs,
        outputs=_relocated_step_05_output_group(inputs.outputs, settings.figure_dir),
    )
    overview_result = _write_step_05_overview_map(inputs, settings=settings, overwrite=session.overwrite)
    metrics_by_regions = _step_05_metrics_with_station_event_regions(
        inputs.metrics,
        stations=inputs.stations,
        events=inputs.events,
        geojson_path=inputs.geojson_path,
    )
    boundary_region = _preferred_step_05_boundary_region(inputs.geojson_path)
    map_result = _write_step_05_station_metric_map(
        metrics_by_regions,
        inputs,
        settings=settings,
        overwrite=session.overwrite,
    )
    corridor_result = _write_step_05_corridor_maps(
        inputs,
        settings=settings,
        boundary_region=boundary_region,
        overwrite=session.overwrite,
    )
    waveform_result = _write_step_05_waveform_review(
        inputs,
        waveform_settings=waveform_settings,
        overwrite=session.overwrite,
    )
    boxplot_sweep = _write_step_05_region_boxplot_sweep(
        metrics_by_regions,
        settings=settings,
        output_dir=Path(settings.figure_dir) / "region_boxplots",
        overwrite=session.overwrite,
        compare_to=boundary_region,
    )
    return _finish_action(
        "Region and corridor figures",
        "Region, corridor, and all-metric station-region figures have been requested.",
        {
            "overview": overview_result,
            "maps": map_result,
            "corridor_figures": corridor_result,
            "waveforms": waveform_result,
            "region_boxplot_sweep": boxplot_sweep,
        },
    )


def make_filtered_region_corridor_figures(
    session: LargeRunSession,
    figure_sets: Sequence[dict[str, Any]] | None = None,
) -> LargeRunActionResult:
    """Render additional GeoJSON/corridor figure sets for selected scientific questions."""

    if not session.make_figures:
        return _finish_action("Filtered region and corridor figures", "Figure rendering is disabled for this run.", {})
    if not figure_sets:
        return _finish_action("Filtered region and corridor figures", "No filtered region/corridor figure sets were requested.", {})
    from spatial_vtk.config import notebook_figure_settings
    from spatial_vtk.spatial import load_standard_geojson_workflow_output_status

    outputs = load_standard_geojson_workflow_output_status(cfg=session.cfg)
    base_settings = notebook_figure_settings(
        "region",
        figure_subdir="step_05_regions/default",
        default_make_figures=session.make_figures,
        default_add_basemap=True,
        default_metric="PGA",
        default_passband="2-3 sec",
        default_sidecar_rows=1000,
    )
    results: dict[str, Any] = {}
    for spec in figure_sets:
        settings = _filtered_region_figure_settings(base_settings, spec)
        result = outputs.write_region_figures(
            settings,
            geojson_path=spec.get("geojson_path"),
            overwrite=session.overwrite,
        )
        results[_figure_set_result_name(settings.figure_dir, "region_figures_")] = result
    return _finish_action("Filtered region and corridor figures", "Filtered region/corridor figure sets have been requested.", results)


def make_additional_diagnostic_figures(session: LargeRunSession) -> LargeRunActionResult:
    """Render optional waveform and region diagnostic figures."""

    if not session.make_figures:
        return _finish_action("Additional diagnostics", "Figure rendering is disabled for this run.", {})
    from spatial_vtk.config import notebook_figure_settings
    from spatial_vtk.io import load_configured_input_paths, slugify
    from spatial_vtk.spatial import load_standard_additional_plotting_inputs, load_standard_additional_plotting_output_status

    outputs = load_standard_additional_plotting_output_status(cfg=session.cfg)
    waveform_settings = notebook_figure_settings("waveform", default_make_figures=session.make_figures)
    region_settings = notebook_figure_settings(
        "region",
        figure_subdir="step_06_additional_diagnostics/region",
        default_make_figures=session.make_figures,
        default_metric="PGA",
        default_passband="2-3 sec",
        default_sidecar_rows=1000,
    )
    try:
        region_geojson_path = load_configured_input_paths(
            {"region_geojson": "paths.region_geojson"},
            cfg=session.cfg,
        ).get("region_geojson")
    except (KeyError, TypeError, ValueError):
        region_geojson_path = None
    standard_settings = notebook_figure_settings(
        "metric",
        figure_subdir="step_06_additional_diagnostics/default",
        default_make_figures=session.make_figures,
        default_add_basemap=True,
        default_sidecar_rows=1000,
    )
    standard_waveform_settings = notebook_figure_settings(
        "waveform",
        figure_subdir="step_06_additional_diagnostics/default",
        default_make_figures=session.make_figures,
        default_add_basemap=True,
        default_sidecar_rows=1000,
    )
    try:
        try:
            standard_inputs = _load_step_06_additional_plotting_inputs_from_outputs(session.cfg)
        except (KeyError, TypeError, ValueError, FileNotFoundError):
            standard_inputs = load_standard_additional_plotting_inputs(cfg=session.cfg)
        requested_model = standard_settings.model
        models = [str(requested_model)] if requested_model is not None else _available_metric_values(standard_inputs.metrics, "model")
        if not models:
            models = [_first_nonempty_metric_value(standard_inputs.metrics, "model", fallback="model")]
        standard_figures = {}
        for model_name in models:
            model_figure_dir = Path(standard_settings.figure_dir) / slugify(model_name)
            model_inputs = replace(
                standard_inputs,
                outputs=_relocated_step_06_output_group(standard_inputs.outputs, model_figure_dir),
            )
            standard_figures[model_name] = model_inputs.write_figures(
                waveform_settings=standard_waveform_settings,
                metric_settings=standard_settings,
                model=model_name,
            )
        if requested_model is None and len(models) > 1:
            from spatial_vtk.spatial.plot.large_run import write_step06_model_comparison_figures

            standard_figures["model_comparison"] = write_step06_model_comparison_figures(
                metrics=standard_inputs.metrics,
                figure_dir=Path(standard_settings.figure_dir) / "model_comparison",
                metric_settings=standard_settings,
                cfg=session.cfg,
                models=models,
            )
    except Exception as exc:
        standard_figures = f"standard additional figures failed: {type(exc).__name__}: {exc}"
    results = {
        "standard_diagnostics": standard_figures,
        "waveform_comparison": outputs.write_waveform_comparison(
            waveform_settings,
            max_records=12,
            max_distance_km=None,
            chunksize=session.qc_chunksize,
            overwrite=session.overwrite,
            fallback_to_available=True,
        ),
        "region_boxplot": outputs.write_region_boxplot(
            region_settings,
            output_prefix="additional_region_boxplot",
            geojson_path=region_geojson_path,
            annotate_if_missing=True,
            overwrite=session.overwrite,
        ),
    }
    return _finish_action("Additional diagnostics", "Additional diagnostic figures have been requested.", results)


def _available_metric_values(frame: pd.DataFrame, column: str) -> list[str]:
    """Return stable non-empty metric dimension values from ``frame``."""

    if column not in frame.columns:
        return []
    values = frame[column].dropna().astype(str)
    values = values[values.str.strip().ne("")]
    return sorted(values.unique().tolist())


@dataclass(frozen=True)
class _FilteredMetricFigureSettings:
    """Notebook figure settings wrapper for one filtered metric figure suite."""

    base: Any
    figure_dir: Path
    load_filters: dict[str, object]
    compare_to: str | None
    comparison_table: bool

    def __getattr__(self, name: str) -> Any:
        return getattr(self.base, name)

    def context_kwargs(self, *, include_station_aggregation: bool = False) -> dict[str, object]:
        kwargs = dict(self.base.context_kwargs(include_station_aggregation=include_station_aggregation))
        existing = dict(kwargs.get("load_filters") or {})
        kwargs["load_filters"] = {**existing, **self.load_filters}
        if "band" in self.load_filters:
            kwargs["default_passband"] = _single_filter_value(self.load_filters["band"])
        if "component" in self.load_filters:
            value = self.load_filters["component"]
            kwargs["default_components"] = list(value) if isinstance(value, (list, tuple)) else [str(value)]
        if "model" in self.load_filters:
            kwargs["default_model"] = _single_filter_value(self.load_filters["model"])
        return kwargs

    def plot_selection_kwargs(self, **kwargs: object) -> dict[str, object]:
        return self.base.plot_selection_kwargs(**kwargs)


@dataclass(frozen=True)
class _FilteredRegionFigureSettings:
    """Notebook figure settings wrapper for one filtered region/corridor figure set."""

    base: Any
    figure_dir: Path
    metric: str | None
    passband: str | Sequence[str] | None
    component: str | Sequence[str] | None
    components: list[str] | None
    model: str | Sequence[str] | None
    value_col: str
    compare_to: str | None
    sample_rows: int
    corridor_filters: dict[str, object]

    def __getattr__(self, name: str) -> Any:
        return getattr(self.base, name)

    def plot_selection_kwargs(self, **kwargs: object) -> dict[str, object]:
        return self.base.plot_selection_kwargs(**kwargs)


def _filtered_metric_figure_settings(base_settings: Any, spec: dict[str, Any]) -> _FilteredMetricFigureSettings:
    """Return settings for one named filtered metric figure suite."""

    filters = _figure_set_filters(spec)
    label = str(spec.get("name") or _metric_figure_set_label(filters)).strip()
    figure_dir = _figure_set_dir(base_settings.figure_dir, label, prefix="metrics_figures_")
    compare_to = spec.get("compare_to", base_settings.compare_to if base_settings.compare_to is not None else "Z")
    comparison_table = bool(spec.get("comparison_table", compare_to is not None))
    if str(compare_to).strip().lower() in {"", "none", "null"}:
        compare_to = None
    return _FilteredMetricFigureSettings(
        base=base_settings,
        figure_dir=figure_dir,
        load_filters=filters,
        compare_to=compare_to,
        comparison_table=comparison_table,
    )


def _filtered_spatial_figure_settings(base_settings: Any, spec: dict[str, Any]) -> _FilteredMetricFigureSettings:
    """Return settings for one named filtered spatial figure suite."""

    filters = _figure_set_filters(spec)
    label = str(spec.get("name") or _metric_figure_set_label(filters)).strip()
    figure_dir = _figure_set_dir(base_settings.figure_dir, label, prefix="spatial_figures_")
    return _FilteredMetricFigureSettings(
        base=base_settings,
        figure_dir=figure_dir,
        load_filters=filters,
        compare_to=base_settings.compare_to,
        comparison_table=base_settings.comparison_table,
    )


def _filtered_region_figure_settings(base_settings: Any, spec: dict[str, Any]) -> _FilteredRegionFigureSettings:
    """Return settings for one named filtered Step 5 region/corridor figure set."""

    filters = _figure_set_filters(spec)
    label = str(spec.get("name") or _region_figure_set_label(spec, filters)).strip()
    figure_dir = _figure_set_dir(base_settings.figure_dir, label, prefix="region_figures_")
    compare_to = spec.get("compare_to", base_settings.compare_to)
    if str(compare_to).strip().lower() in {"", "none", "null"}:
        compare_to = None
    component = spec.get("component", spec.get("components", base_settings.component))
    components = spec.get("components", base_settings.components)
    if components is not None and not isinstance(components, list):
        components = list(components) if isinstance(components, tuple) else [str(components)]
    corridor_filters = dict(spec.get("corridor_filters") or {})
    return _FilteredRegionFigureSettings(
        base=base_settings,
        figure_dir=figure_dir,
        metric=spec.get("metric", base_settings.metric),
        passband=spec.get("passband", base_settings.passband),
        component=component,
        components=components,
        model=spec.get("model", base_settings.model),
        value_col=str(spec.get("value_col", base_settings.value_col)),
        compare_to=compare_to,
        sample_rows=int(spec.get("sample_rows", base_settings.sample_rows)),
        corridor_filters=corridor_filters,
    )


def _relocated_step_05_output_group(outputs: Any, figure_dir: str | Path) -> Any:
    """Return a Step 5 output group whose figure artifacts live under ``figure_dir``."""

    return _relocated_output_group_figures(
        outputs,
        figure_dir,
        {
            "geojson_polygons_map_path": "overview/geojson_polygons_map.png",
            "corridor_map_path": "corridors/corridor_map.png",
            "region_boxplot_figure_path": "region_boxplots/geojson_region_boxplot.png",
            "station_metric_map_path": "maps/station_metric_map.png",
            "record_section_figure_path": "waveforms/observed_synthetic_record_section.png",
        },
    )


def _write_step_05_overview_map(inputs: Any, *, settings: Any, overwrite: bool) -> pd.DataFrame:
    """Write the Step 5 GeoJSON overview map using polygon bounds only."""

    from spatial_vtk.spatial.map import plot_geojson_polygons_map

    path = Path(inputs.outputs.geojson_polygons_map_path)
    if path.exists() and not overwrite:
        return _figure_status_frame("geojson_polygons_map", "exists", path, "reused existing GeoJSON overview map")
    try:
        plot_geojson_polygons_map(
            inputs.geojson_path,
            output_path=path,
            stations_df=None,
            events_df=None,
            label_polygons=False,
            legend_polygons=True,
            add_basemap=bool(getattr(settings, "add_basemap", True)),
            savefig=True,
            showfig=False,
            write_sidecar=bool(getattr(settings, "write_sidecar", False)),
            sidecar_rows=getattr(settings, "sidecar_rows", None),
        )
        _close_all_figures()
        return _figure_status_frame(
            "geojson_polygons_map",
            "wrote",
            path,
            "bounded from the selected GeoJSON polygons, not the full station/event inventory",
        )
    except Exception as exc:
        _close_all_figures()
        return _figure_status_frame("geojson_polygons_map", "plot_failed", path, f"{type(exc).__name__}: {exc}")


def _write_step_05_corridor_maps(
    inputs: Any,
    *,
    settings: Any,
    boundary_region: str,
    overwrite: bool,
) -> pd.DataFrame:
    """Write Step 5 corridor maps with basemaps and corridor-focused extents."""

    from spatial_vtk.io import read_table, slugify
    from spatial_vtk.spatial import CorridorSelectionConfig

    rows: list[dict[str, Any]] = []
    path = Path(inputs.outputs.corridor_map_path)
    try:
        corridors = read_table(inputs.outputs.corridors_path)
    except Exception as exc:
        return _figure_status_frame("corridor_map", "missing_input", path, f"{type(exc).__name__}: {exc}")
    corridors = _step_05_restore_corridor_geometries(corridors)
    if corridors.empty:
        return _figure_status_frame("corridor_map", "no_data", path, "the configured corridor table is empty")
    corridors = _step_05_limit_corridors_for_sync(corridors, boundary_region=boundary_region)

    try:
        corridor_paths = _step_05_select_records_by_corridors_fast(
            inputs.event_stations,
            corridors,
            config=CorridorSelectionConfig(path_filter="passes_through_corridor", min_path_length_km=0.1),
        )
    except Exception as exc:
        return _figure_status_frame("corridor_map", "selection_failed", path, f"{type(exc).__name__}: {exc}")
    if {"station_in_corridor", "event_in_corridor"}.issubset(corridor_paths.columns):
        corridor_paths = corridor_paths.loc[
            corridor_paths["station_in_corridor"].astype(bool) | corridor_paths["event_in_corridor"].astype(bool)
        ].copy()
    if corridor_paths.empty:
        return _figure_status_frame("corridor_map", "no_data", path, "no event-station paths intersect the configured corridors")

    key_cols = _step_05_corridor_key_columns(corridors, corridor_paths)
    if not key_cols:
        return _figure_status_frame("corridor_map", "missing_columns", path, "could not identify corridor grouping columns")

    comparison_by_pair = inputs.comparison_eligible if {"event_id", "station"}.issubset(inputs.comparison_eligible.columns) else None
    grouped_paths = corridor_paths.groupby(key_cols, dropna=False, sort=False)
    for key_values, path_rows in grouped_paths:
        key_tuple = key_values if isinstance(key_values, tuple) else (key_values,)
        corridor_subset = _step_05_corridor_rows_for_key(corridors, key_cols, key_tuple)
        if corridor_subset.empty:
            continue
        first = corridor_subset.iloc[0]
        region = str(first.get("polygon_name", "region")).strip() or "region"
        mode = str(first.get("corridor_mode", "corridor")).strip() or "corridor"
        anchor = str(first.get("anchor_label", first.get("anchor_index", "segment"))).strip() or "segment"
        corridor_dir = (
            path.parent
            / _folder_token(region)
            / _folder_token(mode)
            / _folder_token(anchor)
        )
        corridor_path = corridor_dir / f"corridor_map__{slugify(region)}__{slugify(mode)}__{slugify(anchor)}.png"
        stations_df, events_df, records_df = _step_05_corridor_endpoint_frames(path_rows)
        map_row = _plot_step_05_corridor_map(
            corridor_subset,
            path=corridor_path,
            artifact=f"corridor_map:{region}:{mode}:{anchor}",
            settings=settings,
            overwrite=overwrite,
            title=f"{region} {mode.replace('_', ' ').title()} Corridor\nAnchor: {anchor}",
            stations_df=stations_df,
            events_df=events_df,
            records_df=records_df,
        )
        rows.append(map_row)
        waveform_dir = Path(settings.figure_dir) / "waveforms" / "corridors" / _folder_token(region) / _folder_token(mode) / _folder_token(anchor)
        scenario_rows = _write_step_05_corridor_waveform_scenarios(
            path_rows,
            inputs=inputs,
            comparison_by_pair=comparison_by_pair,
            output_dir=waveform_dir,
            title_prefix=f"{region} {mode.replace('_', ' ').title()} Corridor - {anchor}",
            overwrite=overwrite,
        )
        rows.extend(scenario_rows)
        rows.append(
            _write_step_05_corridor_review_composite(
                map_row,
                scenario_rows,
                output_path=waveform_dir / f"corridor_review__{slugify(region)}__{slugify(mode)}__{slugify(anchor)}.png",
                title=f"{region} {mode.replace('_', ' ').title()} Corridor - {anchor}",
                overwrite=overwrite,
            )
        )

    rows.append(
        _figure_status_row(
            "corridor_map_summary",
            "wrote" if rows else "no_data",
            path,
            f"created {len(rows):,} corridor-local maps with intersecting stations/events",
            row_count=len(corridor_paths),
        )
    )
    return pd.DataFrame(rows)


def _plot_step_05_corridor_map(
    corridors: pd.DataFrame,
    *,
    path: Path,
    artifact: str,
    settings: Any,
    overwrite: bool,
    title: str,
    stations_df: pd.DataFrame | None = None,
    events_df: pd.DataFrame | None = None,
    records_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Plot one corridor map status row."""

    from spatial_vtk.spatial.map import plot_corridor_map

    if corridors.empty:
        return _figure_status_row(artifact, "no_data", path, "no corridors matched this selection", row_count=0)
    if path.exists() and not overwrite:
        return _figure_status_row(artifact, "exists", path, "reused existing corridor map", row_count=len(corridors))
    try:
        plot_corridor_map(
            corridors,
            output_path=path,
            stations_df=stations_df,
            events_df=events_df,
            records_df=records_df,
            add_basemap=bool(getattr(settings, "add_basemap", True)),
            savefig=True,
            showfig=False,
            write_sidecar=bool(getattr(settings, "write_sidecar", False)),
            sidecar_rows=getattr(settings, "sidecar_rows", None),
            title=title,
        )
        _close_all_figures()
        return _figure_status_row(
            artifact,
            "wrote",
            path,
            "bounded from selected corridor geometry and rendered with a basemap",
            row_count=len(corridors),
        )
    except Exception as exc:
        _close_all_figures()
        return _figure_status_row(artifact, "plot_failed", path, f"{type(exc).__name__}: {exc}", row_count=len(corridors))


def _step_05_limit_corridors_for_sync(corridors: pd.DataFrame, *, boundary_region: str) -> pd.DataFrame:
    """Return an optional bounded corridor subset for synchronous notebook rendering."""

    raw = os.environ.get("SPATIAL_VTK_MAX_STEP5_CORRIDORS", "0")
    try:
        max_corridors = int(raw)
    except ValueError:
        max_corridors = 0
    if max_corridors <= 0 or len(corridors) <= max_corridors:
        return corridors.copy()
    work = corridors.copy()
    if "anchor_index" in work.columns:
        work = work.sort_values(["polygon_name", "corridor_mode", "anchor_index"], kind="stable")
    selected_parts: list[pd.DataFrame] = []
    region_col = "polygon_name" if "polygon_name" in work.columns else None
    mode_col = "corridor_mode" if "corridor_mode" in work.columns else None
    if region_col is not None:
        preferred_mask = work[region_col].astype(str).eq(str(boundary_region))
        if not preferred_mask.any() and str(boundary_region).casefold() == "la basin":
            preferred_mask = work[region_col].astype(str).str.casefold().str.contains("los angeles basin", regex=False)
        preferred = work.loc[preferred_mask]
        if not preferred.empty:
            selected_parts.append(_step_05_balanced_corridor_head(preferred, max(1, max_corridors // 3), mode_col=mode_col))
    remaining_slots = max_corridors - sum(len(part) for part in selected_parts)
    already = pd.concat(selected_parts).index if selected_parts else pd.Index([])
    remaining = work.loc[~work.index.isin(already)]
    if remaining_slots > 0 and not remaining.empty:
        selected_parts.append(_step_05_balanced_corridor_head(remaining, remaining_slots, mode_col=mode_col))
    if selected_parts:
        selected = pd.concat(selected_parts)
        selected = selected.loc[~selected.index.duplicated(keep="first")].head(max_corridors)
    else:
        selected = work.head(max_corridors)
    return selected.reset_index(drop=True)


def _step_05_balanced_corridor_head(corridors: pd.DataFrame, max_rows: int, *, mode_col: str | None) -> pd.DataFrame:
    """Take a balanced head across corridor modes."""

    if max_rows <= 0 or corridors.empty:
        return corridors.head(0)
    if mode_col is None or mode_col not in corridors.columns:
        return corridors.head(max_rows)
    pieces: list[pd.DataFrame] = []
    per_mode = max(1, int(max_rows // max(1, corridors[mode_col].nunique())))
    for _, group in corridors.groupby(mode_col, dropna=False, sort=False):
        pieces.append(group.head(per_mode))
    selected = pd.concat(pieces) if pieces else corridors.head(0)
    if len(selected) < max_rows:
        selected = pd.concat([selected, corridors.loc[~corridors.index.isin(selected.index)].head(max_rows - len(selected))])
    return selected.head(max_rows)


def _step_05_select_records_by_corridors_fast(
    records: pd.DataFrame,
    corridors: pd.DataFrame,
    *,
    config: Any,
) -> pd.DataFrame:
    """Select records whose station or event point falls inside each corridor."""

    from shapely.geometry import Point

    station_lon = _first_existing_column(records, ["station_lon", "station_longitude", "sta_lon", "lon", "longitude"])
    station_lat = _first_existing_column(records, ["station_lat", "station_latitude", "sta_lat", "lat", "latitude"])
    event_lon = _first_existing_column(records, ["event_lon", "event_longitude", "source_lon", "source_longitude"])
    event_lat = _first_existing_column(records, ["event_lat", "event_latitude", "source_lat", "source_latitude"])
    if station_lon is None or station_lat is None or event_lon is None or event_lat is None:
        return pd.DataFrame()
    work = records.copy()
    sx = pd.to_numeric(work[station_lon], errors="coerce")
    sy = pd.to_numeric(work[station_lat], errors="coerce")
    ex = pd.to_numeric(work[event_lon], errors="coerce")
    ey = pd.to_numeric(work[event_lat], errors="coerce")
    finite = sx.notna() & sy.notna() & ex.notna() & ey.notna()
    work = work.loc[finite].copy()
    sx = sx.loc[finite]
    sy = sy.loc[finite]
    ex = ex.loc[finite]
    ey = ey.loc[finite]
    selected: list[pd.DataFrame] = []
    for _, corridor in corridors.iterrows():
        geom = corridor.get("corridor_geometry")
        if geom is None or getattr(geom, "is_empty", True):
            continue
        minx, miny, maxx, maxy = geom.bounds
        pad = 0.02
        candidate_mask = (
            ((sx >= minx - pad) & (sx <= maxx + pad) & (sy >= miny - pad) & (sy <= maxy + pad))
            | ((ex >= minx - pad) & (ex <= maxx + pad) & (ey >= miny - pad) & (ey <= maxy + pad))
        )
        candidates = work.loc[candidate_mask].copy()
        if candidates.empty:
            continue
        candidate_sx = pd.to_numeric(candidates[station_lon], errors="coerce")
        candidate_sy = pd.to_numeric(candidates[station_lat], errors="coerce")
        candidate_ex = pd.to_numeric(candidates[event_lon], errors="coerce")
        candidate_ey = pd.to_numeric(candidates[event_lat], errors="coerce")
        station_in = [
            _point_in_geometry(Point(float(x), float(y)), geom)
            for x, y in zip(candidate_sx, candidate_sy)
        ]
        event_in = [
            _point_in_geometry(Point(float(x), float(y)), geom)
            for x, y in zip(candidate_ex, candidate_ey)
        ]
        keep = pd.Series(station_in, index=candidates.index) | pd.Series(event_in, index=candidates.index)
        if not keep.any():
            continue
        out = candidates.loc[keep].copy()
        for key, value in corridor.to_dict().items():
            if key not in out.columns:
                out[key] = value
        polygon_geom = corridor.get("polygon_geometry")
        out["station_in_corridor"] = pd.Series(station_in, index=candidates.index).loc[keep].to_numpy(dtype=bool)
        out["event_in_corridor"] = pd.Series(event_in, index=candidates.index).loc[keep].to_numpy(dtype=bool)
        out["station_inside_polygon"] = [
            _point_in_geometry(Point(float(x), float(y)), polygon_geom)
            for x, y in zip(pd.to_numeric(out[station_lon], errors="coerce"), pd.to_numeric(out[station_lat], errors="coerce"))
        ]
        out["event_inside_polygon"] = [
            _point_in_geometry(Point(float(x), float(y)), polygon_geom)
            for x, y in zip(pd.to_numeric(out[event_lon], errors="coerce"), pd.to_numeric(out[event_lat], errors="coerce"))
        ]
        selected.append(out)
    if not selected:
        return pd.DataFrame()
    return pd.concat(selected, ignore_index=True, sort=False)


def _point_in_geometry(point: Any, geometry: Any) -> bool:
    """Return whether a point is inside or touching a polygon-like geometry."""

    if geometry is None or getattr(geometry, "is_empty", True):
        return False
    try:
        return bool(geometry.contains(point) or geometry.touches(point))
    except Exception:
        return False


def _write_step_05_corridor_waveform_scenarios(
    path_rows: pd.DataFrame,
    *,
    inputs: Any,
    comparison_by_pair: pd.DataFrame | None,
    output_dir: Path,
    title_prefix: str,
    overwrite: bool,
) -> list[dict[str, Any]]:
    """Write bounded observed/synthetic waveform sections for corridor scenarios."""

    from spatial_vtk.qc import build_qc_waveform_comparison_records
    from spatial_vtk.visualize.waveforms import plot_observed_synthetic_record_section

    rows: list[dict[str, Any]] = []
    scenarios = [
        ("station_inside_event_inside", True, True, "Station and event inside boundary"),
        ("station_outside_event_outside", False, False, "Station and event outside boundary"),
        ("station_inside_event_outside", True, False, "Station inside / event outside boundary"),
        ("station_outside_event_inside", False, True, "Station outside / event inside boundary"),
    ]
    if "station_inside_polygon" not in path_rows.columns or "event_inside_polygon" not in path_rows.columns:
        return [
            _figure_status_row(
                "corridor_waveform_scenario",
                "missing_columns",
                output_dir / "missing_scenario_columns.png",
                "corridor records do not include station/event boundary-side columns",
                row_count=len(path_rows),
            )
        ]
    for scenario_slug, station_inside, event_inside, scenario_label in scenarios:
        scenario_rows = path_rows.loc[
            path_rows["station_inside_polygon"].astype(bool).eq(station_inside)
            & path_rows["event_inside_polygon"].astype(bool).eq(event_inside)
        ].copy()
        output = output_dir / f"observed_synthetic_record_section__{scenario_slug}.png"
        if scenario_rows.empty:
            continue
        if output.exists() and not overwrite:
            rows.append(
                _figure_status_row(
                    f"corridor_waveform:{scenario_slug}",
                    "exists",
                    output,
                    f"reused waveform section for {scenario_label}",
                    row_count=len(scenario_rows),
                )
            )
            continue
        waveform_pair_rows = _step_05_sample_corridor_waveform_pairs(scenario_rows)
        selected_eligible = _step_05_comparison_rows_for_pairs(comparison_by_pair, waveform_pair_rows)
        if selected_eligible.empty:
            continue
        waveform_records = pd.DataFrame()
        message = ""
        try:
            waveform_records = build_qc_waveform_comparison_records(
                inputs.event_stations,
                comparison_eligible=selected_eligible,
                component="R",
                passband=None,
                max_distance_km=None,
                max_records=6,
            )
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
        if waveform_records.empty:
            continue
        waveform_records = _bandpass_waveform_records(waveform_records, min_period_s=1.0, max_period_s=5.0)
        try:
            plot_observed_synthetic_record_section(
                waveform_records,
                output_path=output,
                components=["R"],
                normalize=True,
                scale=2.5,
                title=f"{title_prefix}\n{scenario_label}",
                filter_label=f"R component; 1-5 s bandpass; {_waveform_record_summary_label(waveform_records)}",
                time_limit_s=60,
                annotate_records=True,
                savefig=True,
                showfig=False,
                write_sidecar=False,
            )
            _close_all_figures()
            rows.append(
                _figure_status_row(
                    f"corridor_waveform:{scenario_slug}",
                    "wrote",
                    output,
                    f"wrote R-component 1-5 s waveform section for {scenario_label}",
                    row_count=len(waveform_records),
                )
            )
        except Exception as exc:
            _close_all_figures()
            rows.append(
                _figure_status_row(
                    f"corridor_waveform:{scenario_slug}",
                    "plot_failed",
                    output,
                    f"{type(exc).__name__}: {exc}",
                    row_count=len(waveform_records),
                )
            )
    return rows


def _step_05_sample_corridor_waveform_pairs(path_rows: pd.DataFrame, *, max_pairs: int = 48) -> pd.DataFrame:
    """Return a bounded, deterministic path subset for waveform loading."""

    if len(path_rows) <= max_pairs:
        return path_rows
    sort_cols = [column for column in ("distance_km", "event_id", "station") if column in path_rows.columns]
    if sort_cols:
        ordered = path_rows.sort_values(sort_cols, kind="stable")
    else:
        ordered = path_rows
    return ordered.head(max_pairs).copy()


def _write_step_05_corridor_review_composite(
    map_row: dict[str, Any],
    scenario_rows: Sequence[dict[str, Any]],
    *,
    output_path: Path,
    title: str,
    overwrite: bool,
) -> dict[str, Any]:
    """Write one corridor review image containing the matching map and waveform panels."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not overwrite:
        return _figure_status_row(
            "corridor_review_composite",
            "exists",
            output_path,
            "reused composite corridor review figure",
        )

    map_path = Path(str(map_row.get("figure_path", "")))
    if not map_path.exists():
        return _figure_status_row(
            "corridor_review_composite",
            "missing_input",
            output_path,
            "matching corridor map was not written",
        )

    waveform_paths: list[Path] = []
    for row in scenario_rows:
        if str(row.get("artifact", "")).startswith("corridor_waveform:") and row.get("status") in {"wrote", "exists"}:
            path = Path(str(row.get("figure_path", "")))
            if path.exists():
                waveform_paths.append(path)

    try:
        import matplotlib.image as mpimg
        import matplotlib.pyplot as plt

        panels = [("Corridor map", map_path), *[(path.stem.replace("observed_synthetic_record_section__", "").replace("_", " ").title(), path) for path in waveform_paths]]
        n_waveforms = len(waveform_paths)
        if n_waveforms:
            wave_cols = min(2, n_waveforms)
            wave_rows = int(math.ceil(n_waveforms / wave_cols))
            fig = plt.figure(figsize=(13.5, 7.6 + 2.55 * wave_rows), dpi=180)
            gs = fig.add_gridspec(1 + wave_rows, wave_cols, height_ratios=[2.35, *([1.0] * wave_rows)], wspace=0.03, hspace=0.08)
            map_ax = fig.add_subplot(gs[0, :])
            map_ax.imshow(_trim_step_05_composite_panel_image(mpimg.imread(map_path), dense_content=True))
            map_ax.set_anchor("N")
            map_ax.set_axis_off()
            for index, (label, path) in enumerate(panels[1:]):
                row = 1 + index // wave_cols
                col = index % wave_cols
                ax = fig.add_subplot(gs[row, col])
                ax.imshow(_trim_step_05_composite_panel_image(mpimg.imread(path)))
                ax.set_anchor("N")
                ax.set_axis_off()
        else:
            fig, map_ax = plt.subplots(figsize=(8.0, 7.0), dpi=180)
            map_ax.imshow(_trim_step_05_composite_panel_image(mpimg.imread(map_path), dense_content=True))
            map_ax.set_axis_off()
        fig.subplots_adjust(left=0.015, right=0.985, top=0.985, bottom=0.015)
        fig.savefig(output_path, bbox_inches="tight", pad_inches=0.05)
        _close_all_figures()
        return _figure_status_row(
            "corridor_review_composite",
            "wrote",
            output_path,
            f"combined corridor map with {n_waveforms:,} waveform scenario panel(s)",
            row_count=1 + n_waveforms,
        )
    except Exception as exc:
        _close_all_figures()
        return _figure_status_row(
            "corridor_review_composite",
            "plot_failed",
            output_path,
            f"{type(exc).__name__}: {exc}",
            row_count=1 + len(waveform_paths),
        )


def _trim_step_05_composite_panel_image(image: Any, *, pad_px: int = 12, dense_content: bool = False) -> Any:
    """Trim outer white margins from a rendered panel image before compositing."""

    import numpy as np

    arr = np.asarray(image)
    if arr.ndim < 3 or arr.shape[0] < 2 or arr.shape[1] < 2:
        return image
    rgb = arr[..., :3].astype(float)
    threshold = 0.985 if rgb.max(initial=0.0) <= 1.0 else 251.0
    non_white = np.any(rgb < threshold, axis=2)
    if arr.shape[-1] >= 4:
        alpha = arr[..., 3].astype(float)
        alpha_threshold = 0.02 if alpha.max(initial=0.0) <= 1.0 else 5.0
        non_white &= alpha > alpha_threshold
    if not bool(non_white.any()):
        return image
    if dense_content:
        row_fraction = non_white.mean(axis=1)
        col_fraction = non_white.mean(axis=0)
        dense_rows = np.where(row_fraction >= 0.08)[0]
        dense_cols = np.where(col_fraction >= 0.08)[0]
        if dense_rows.size and dense_cols.size:
            y0 = max(int(dense_rows.min()) - pad_px, 0)
            y1 = min(int(dense_rows.max()) + pad_px + 1, arr.shape[0])
            x0 = max(int(dense_cols.min()) - pad_px, 0)
            x1 = min(int(dense_cols.max()) + pad_px + 1, arr.shape[1])
            return arr[y0:y1, x0:x1]
    y_idx, x_idx = np.where(non_white)
    y0 = max(int(y_idx.min()) - pad_px, 0)
    y1 = min(int(y_idx.max()) + pad_px + 1, arr.shape[0])
    x0 = max(int(x_idx.min()) - pad_px, 0)
    x1 = min(int(x_idx.max()) + pad_px + 1, arr.shape[1])
    return arr[y0:y1, x0:x1]


def _step_05_comparison_rows_for_pairs(comparison_by_pair: pd.DataFrame | None, pairs: pd.DataFrame) -> pd.DataFrame:
    """Return comparison-eligible rows for selected event/station pairs."""

    if comparison_by_pair is None or pairs.empty or not {"event_id", "station"}.issubset(pairs.columns):
        return pd.DataFrame()
    pair_frame = pairs.loc[:, ["event_id", "station"]].copy()
    pair_frame["event_id"] = pair_frame["event_id"].astype(str)
    pair_frame["station"] = pair_frame["station"].astype(str)
    pair_frame = pair_frame.drop_duplicates()
    eligible = comparison_by_pair.copy()
    eligible["event_id"] = eligible["event_id"].astype(str)
    eligible["station"] = eligible["station"].astype(str)
    return eligible.merge(pair_frame, on=["event_id", "station"], how="inner")


def _bandpass_waveform_records(records: pd.DataFrame, *, min_period_s: float, max_period_s: float) -> pd.DataFrame:
    """Apply a period-domain bandpass to plotted waveform records when possible."""

    out = records.copy()
    freqmin = 1.0 / float(max_period_s)
    freqmax = 1.0 / float(min_period_s)
    for column in ("observed", "synthetic"):
        if column in out.columns:
            out[column] = out[column].map(lambda value: _bandpass_waveform_value(value, freqmin=freqmin, freqmax=freqmax))
    return out


def _bandpass_waveform_value(value: Any, *, freqmin: float, freqmax: float) -> Any:
    """Return a bandpassed copy of one waveform-like value where supported."""

    if value is None:
        return value
    if hasattr(value, "copy") and hasattr(value, "filter"):
        try:
            trace = value.copy()
            trace.detrend("demean")
            trace.taper(max_percentage=0.05, type="hann")
            trace.filter("bandpass", freqmin=freqmin, freqmax=freqmax, corners=4, zerophase=True)
            return trace
        except Exception:
            return value
    if isinstance(value, dict) and "data" in value:
        filtered = dict(value)
        try:
            data = _bandpass_array_like(filtered.get("data"), value, freqmin=freqmin, freqmax=freqmax)
        except Exception:
            return value
        filtered["data"] = data
        return filtered
    try:
        return _bandpass_array_like(value, value, freqmin=freqmin, freqmax=freqmax)
    except Exception:
        return value


def _bandpass_array_like(data_value: Any, metadata_value: Any, *, freqmin: float, freqmax: float) -> Any:
    """Bandpass a numeric array-like waveform using scipy when available."""

    import numpy as np

    data = np.asarray(data_value, dtype=float)
    if data.size < 8:
        return data_value
    dt = _waveform_value_dt(metadata_value)
    if dt is None or dt <= 0:
        return data_value
    nyquist = 0.5 / float(dt)
    high = min(float(freqmax) / nyquist, 0.999)
    low = max(float(freqmin) / nyquist, 1.0e-6)
    if low >= high:
        return data_value
    try:
        from scipy.signal import butter, filtfilt

        b, a = butter(4, [low, high], btype="band")
        return filtfilt(b, a, data)
    except Exception:
        return data_value


def _waveform_value_dt(value: Any) -> float | None:
    """Resolve waveform sample interval from trace-like or dict-like metadata."""

    stats = None
    if isinstance(value, dict):
        stats = value.get("stats", {})
    else:
        stats = getattr(value, "stats", None)
    if stats is None:
        return None
    dt = stats.get("delta") if isinstance(stats, dict) else getattr(stats, "delta", None)
    if dt is not None:
        return float(dt)
    sampling_rate = stats.get("sampling_rate") if isinstance(stats, dict) else getattr(stats, "sampling_rate", None)
    return 1.0 / float(sampling_rate) if sampling_rate else None


def _step_05_restore_corridor_geometries(corridors: pd.DataFrame) -> pd.DataFrame:
    """Restore Shapely corridor geometries from WKT columns when needed."""

    out = corridors.copy()
    if out.empty:
        return out
    try:
        from shapely import wkt
    except Exception:
        return out
    for column in ("corridor_geometry", "polygon_geometry"):
        wkt_col = f"{column}_wkt"
        if column not in out.columns and wkt_col in out.columns:
            out[column] = out[wkt_col].map(lambda value: wkt.loads(value) if isinstance(value, str) and value else None)
    return out


def _step_05_corridor_key_columns(corridors: pd.DataFrame, corridor_paths: pd.DataFrame) -> list[str]:
    """Return stable columns that identify one corridor segment."""

    candidates = [
        "polygon_name",
        "corridor_mode",
        "anchor_source",
        "anchor_label",
        "anchor_index",
        "shell_index",
    ]
    keys = [column for column in candidates if column in corridors.columns and column in corridor_paths.columns]
    if keys:
        return keys
    return [column for column in ("polygon_safe_name", "corridor_mode", "anchor_index") if column in corridors.columns and column in corridor_paths.columns]


def _step_05_corridor_rows_for_key(corridors: pd.DataFrame, key_cols: Sequence[str], key_values: Sequence[object]) -> pd.DataFrame:
    """Return corridor rows matching one grouped path key."""

    mask = pd.Series(True, index=corridors.index)
    for column, value in zip(key_cols, key_values):
        if pd.isna(value):
            mask &= corridors[column].isna()
        else:
            mask &= corridors[column].astype(str).eq(str(value))
    return corridors.loc[mask].copy()


def _step_05_corridor_endpoint_frames(path_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return station, event, and path layers for a corridor map."""

    records = path_rows.copy()
    station_lon = _first_existing_column(records, ["station_lon", "station_longitude", "sta_lon", "lon"])
    station_lat = _first_existing_column(records, ["station_lat", "station_latitude", "sta_lat", "lat"])
    event_lon = _first_existing_column(records, ["event_lon", "event_longitude", "source_lon", "source_longitude"])
    event_lat = _first_existing_column(records, ["event_lat", "event_latitude", "source_lat", "source_latitude"])
    station_cols = [column for column in ("station", "network", station_lon, station_lat) if column is not None and column in records.columns]
    event_cols = [column for column in ("event_id", "event_name", event_lon, event_lat) if column is not None and column in records.columns]
    stations = records.loc[:, station_cols].drop_duplicates("station") if "station" in station_cols and not records.empty else pd.DataFrame()
    events = records.loc[:, event_cols].drop_duplicates("event_id") if "event_id" in event_cols and not records.empty else pd.DataFrame()
    return stations.reset_index(drop=True), events.reset_index(drop=True), records.reset_index(drop=True)


def _write_step_05_station_metric_map(
    metrics_by_regions: pd.DataFrame,
    inputs: Any,
    *,
    settings: Any,
    overwrite: bool,
) -> pd.DataFrame:
    """Write Step 5 station metric maps for every metric/passband."""

    from spatial_vtk.spatial.map import plot_station_metric_map

    base_path = Path(inputs.outputs.station_metric_map_path)
    root = base_path.parent
    rows: list[dict[str, Any]] = []
    subset = metrics_by_regions.copy()
    metric_col = _first_existing_column(subset, ["metric", "metric_name"])
    band_col = _first_existing_column(subset, ["passband", "band"])
    lon_col = _first_existing_column(subset, ["sta_lon", "station_lon", "lon"])
    lat_col = _first_existing_column(subset, ["sta_lat", "station_lat", "lat"])
    if metric_col is None or lon_col is None or lat_col is None:
        return _figure_status_frame(
            "station_metric_map",
            "missing_columns",
            base_path,
            "missing metric or station coordinate columns",
        )
    models = _step_05_selected_models(subset, settings)
    metrics = _ordered_nonempty_values(subset[metric_col])
    passbands = _ordered_nonempty_values(subset[band_col]) if band_col is not None else [None]
    for model in models:
        model_rows = _step_05_filter_model(subset, model)
        if model_rows.empty:
            rows.append(
                _figure_status_row(
                    "station_metric_map",
                    "no_data",
                    base_path,
                    f"no rows match model {model!r}",
                )
            )
            continue
        model_label = _folder_token(model or "all-models")
        for metric in metrics:
            metric_rows = model_rows.loc[model_rows[metric_col].astype(str).eq(str(metric))].copy()
            if metric_rows.empty:
                continue
            for passband in passbands:
                if passband is None:
                    plot_rows = metric_rows.copy()
                    passband_label = "all-passbands"
                else:
                    plot_rows = metric_rows.loc[metric_rows[band_col].astype(str).eq(str(passband))].copy()
                    passband_label = str(passband)
                value_col = _step_05_region_boxplot_value_column(
                    plot_rows,
                    metric=metric,
                    default_value_col="log2_residual",
                    band_col=band_col,
                )
                if value_col not in plot_rows.columns:
                    rows.append(
                        _figure_status_row(
                            "station_metric_map",
                            "missing_input",
                            base_path,
                            f"missing value column {value_col!r}",
                        )
                    )
                    continue
                plot_rows = plot_rows.loc[pd.to_numeric(plot_rows[value_col], errors="coerce").notna()].copy()
                if plot_rows.empty:
                    rows.append(
                        _figure_status_row(
                            "station_metric_map",
                            "no_data",
                            base_path,
                            "no finite station metric rows are available",
                        )
                    )
                    continue
                plot_value_col = _step_05_station_map_value_column(metric, value_col)
                group_cols = [column for column in ("station", "model", "metric", "passband") if column in plot_rows.columns]
                station_map = (
                    plot_rows.groupby(group_cols, dropna=False)
                    .agg(
                        sta_lon=(lon_col, "first"),
                        sta_lat=(lat_col, "first"),
                        **{
                            plot_value_col: (value_col, "mean"),
                            "event_count": ("event_id", "nunique") if "event_id" in plot_rows.columns else (value_col, "size"),
                        },
                    )
                    .reset_index()
                )
                station_map = station_map.loc[pd.to_numeric(station_map[plot_value_col], errors="coerce").notna()].copy()
                if station_map.empty:
                    rows.append(
                        _figure_status_row(
                            "station_metric_map",
                            "no_data",
                            base_path,
                            "station aggregation produced no finite values",
                        )
                    )
                    continue
                output = (
                    root
                    / model_label
                    / _folder_token(metric)
                    / _passband_folder_token(passband_label)
                    / (
                        f"station_metric_map__{model_label}__{_folder_token(metric)}"
                        f"__{_passband_folder_token(passband_label)}__{_folder_token(plot_value_col)}.png"
                    )
                )
                output.parent.mkdir(parents=True, exist_ok=True)
                if output.exists() and not overwrite:
                    rows.append(
                        _figure_status_row(
                            "station_metric_map",
                            "exists",
                            output,
                            "reused existing station metric map",
                            row_count=len(station_map),
                        )
                    )
                    continue
                try:
                    title = f"Step 5 Station Metric Map - {metric}"
                    if model is not None:
                        title = f"{title}\nModel: {model}"
                    plot_station_metric_map(
                        station_map,
                        output_path=output,
                        value_col=plot_value_col,
                        lon_col="sta_lon",
                        lat_col="sta_lat",
                        geojson_path=None,
                        label_polygons=False,
                        title=title,
                        add_basemap=bool(getattr(settings, "add_basemap", True)),
                        savefig=True,
                        showfig=False,
                        write_sidecar=bool(getattr(settings, "write_sidecar", False)),
                        sidecar_rows=getattr(settings, "sidecar_rows", None),
                    )
                    _close_all_figures()
                    row = _figure_status_row(
                        "station_metric_map",
                        "wrote",
                        output,
                        "wrote station-focused metric map",
                        row_count=len(station_map),
                    )
                    row["model"] = model
                    rows.append(row)
                except Exception as exc:
                    _close_all_figures()
                    row = _figure_status_row(
                        "station_metric_map",
                        "plot_failed",
                        output,
                        f"{type(exc).__name__}: {exc}",
                        row_count=len(station_map),
                    )
                    row["model"] = model
                    rows.append(row)
    return pd.DataFrame(rows)


def _write_step_05_waveform_review(inputs: Any, *, waveform_settings: Any, overwrite: bool) -> pd.DataFrame:
    """Write a bounded waveform review figure for Step 5."""

    from spatial_vtk.qc import build_qc_waveform_comparison_records
    from spatial_vtk.visualize.waveforms import plot_observed_synthetic_record_section

    path = Path(inputs.outputs.record_section_figure_path)
    if path.exists() and not overwrite:
        return _figure_status_frame("observed_synthetic_record_section", "exists", path, "reused existing waveform review")
    attempts = [("R", "1-2 sec"), ("Z", "1-2 sec"), ("R", None), ("Z", None)]
    records = pd.DataFrame()
    selected_component = None
    selected_passband = None
    message = ""
    for component, passband in attempts:
        try:
            records = build_qc_waveform_comparison_records(
                inputs.event_stations,
                comparison_eligible=inputs.comparison_eligible,
                component=component,
                passband=passband,
                max_distance_km=None,
                max_records=12,
            )
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            continue
        if not records.empty:
            selected_component = component
            selected_passband = passband
            break
    if records.empty:
        return _figure_status_frame("observed_synthetic_record_section", "no_data", path, message or "no waveform pairs matched")
    try:
        plot_observed_synthetic_record_section(
            records,
            output_path=path,
            components=[selected_component] if selected_component else None,
            normalize=True,
            scale=2.5,
            title="Observed vs Synthetic Records for Step 5 Review",
            filter_label=(
                f"{selected_component} component; {selected_passband or 'all passbands'}; "
                f"{_waveform_record_summary_label(records)}"
            ),
            time_limit_s=60,
            annotate_records=True,
            savefig=True,
            showfig=False,
            write_sidecar=bool(getattr(waveform_settings, "write_sidecar", False)),
            sidecar_rows=getattr(waveform_settings, "sidecar_rows", None),
        )
        _close_all_figures()
        return _figure_status_frame(
            "observed_synthetic_record_section",
            "wrote",
            path,
            f"wrote waveform review for {selected_component} / {selected_passband or 'all passbands'}",
            row_count=len(records),
        )
    except Exception as exc:
        _close_all_figures()
        return _figure_status_frame("observed_synthetic_record_section", "plot_failed", path, f"{type(exc).__name__}: {exc}", row_count=len(records))


def _waveform_record_summary_label(records: pd.DataFrame) -> str:
    """Return a compact count label for plotted waveform records."""

    if records.empty:
        return "0 records"
    event_count = records["event_id"].nunique() if "event_id" in records.columns else 0
    station_count = records["station"].nunique() if "station" in records.columns else 0
    return f"{len(records):,} records; {event_count:,} events; {station_count:,} stations"


def _relocated_step_06_output_group(outputs: Any, figure_dir: str | Path) -> Any:
    """Return a Step 6 output group whose figure artifacts live under ``figure_dir``."""

    return _relocated_output_group_figures(
        outputs,
        figure_dir,
        {
            "event_trace_comparison_path": "waveforms/event_trace_comparison.png",
            "station_event_waveform_map_path": "waveforms/station_event_waveform_map.png",
            "pattern_similarity_figure_path": "patterns/pattern_similarity.png",
            "scatterplot_figure_path": "metric_relationships/scatterplot.png",
            "boxplot_figure_path": "region_boxplots/boxplot.png",
            "heatmap_figure_path": "region_heatmaps/heatmap.png",
        },
    )


def _relocated_output_group_figures(outputs: Any, figure_dir: str | Path, relative_paths: dict[str, str]) -> Any:
    """Copy an output group while replacing selected figure paths."""

    from spatial_vtk.io import OutputGroup

    root = Path(figure_dir)
    paths = dict(getattr(outputs, "paths", {}))
    for name, relative in relative_paths.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        paths[name] = path
    return OutputGroup(name=getattr(outputs, "name", "relocated_outputs"), paths=paths)


def _figure_status_frame(
    artifact: str,
    status: str,
    path: str | Path,
    message: str,
    *,
    row_count: int | None = None,
) -> pd.DataFrame:
    """Return a one-row notebook figure status frame."""

    return pd.DataFrame([_figure_status_row(artifact, status, path, message, row_count=row_count)])


def _figure_status_row(
    artifact: str,
    status: str,
    path: str | Path,
    message: str,
    *,
    row_count: int | None = None,
) -> dict[str, Any]:
    """Return one compact notebook figure status row."""

    figure_path = Path(path)
    row: dict[str, Any] = {
        "artifact": artifact,
        "status": status,
        "figure_path": str(figure_path),
        "figure_exists": figure_path.exists(),
        "message": message,
    }
    if row_count is not None:
        row["row_count"] = int(row_count)
    return row


def _close_all_figures() -> None:
    """Close any Matplotlib figures opened by synchronous notebook helpers."""

    try:
        import matplotlib.pyplot as plt

        plt.close("all")
    except Exception:
        return


def _load_step_06_additional_plotting_inputs_from_outputs(cfg: Any) -> Any:
    """Load Step 6 plotting inputs from standard workflow output tables."""

    from spatial_vtk.io import output_group, read_table
    from spatial_vtk.spatial.plot.large_run import StandardAdditionalPlottingInputResult

    ingest_outputs = output_group("step_01_ingest", cfg=cfg)
    plotting_outputs = output_group("step_06_plotting", cfg=cfg)
    metric_path = plotting_outputs.first_existing_path(
        ("metrics_enriched_path", "metrics_long_path"),
        default="metrics_long_path",
    )
    return StandardAdditionalPlottingInputResult(
        metrics=read_table(metric_path),
        event_stations=read_table(ingest_outputs.event_station_path),
        events=read_table(ingest_outputs.prepared_events_path),
        comparison_eligible=read_table(plotting_outputs.comparison_eligible_path),
        outputs=plotting_outputs,
    )


def _step_05_metrics_with_station_event_regions(
    metrics: pd.DataFrame,
    *,
    stations: pd.DataFrame,
    events: pd.DataFrame,
    geojson_path: str | Path,
) -> pd.DataFrame:
    """Attach station/event GeoJSON labels to metric rows using metadata-level geometry work."""

    from spatial_vtk.spatial import geojson_metric_region_frame
    from spatial_vtk.spatial.plot.large_run import _merge_geojson_region_class_metadata

    station_regions = geojson_metric_region_frame(
        stations,
        geojson_path,
        target="station",
        selector="all",
        region_col="station_region",
        require_inside=True,
    )
    event_regions = geojson_metric_region_frame(
        events,
        geojson_path,
        target="event",
        selector="all",
        region_col="event_region",
        require_inside=False,
        require_overlap=False,
    )
    out = metrics.copy()
    station_key = _common_key_pair(out, station_regions, (("station", "station"), ("station", "station_name"), ("station_id", "station_id"), ("station_code", "station")))
    if station_key is not None:
        left_key, right_key = station_key
        station_cols = [
            column
            for column in (
                right_key,
                "station_geojson_inside_any",
                "station_geojson_labels",
                "station_region",
            )
            if column in station_regions.columns
        ]
        station_cols.extend(
            column
            for column in ("mapped_region_type", "geomorphology", "target_region_zone", "mapped_region", "region_class")
            if column in station_regions.columns and column not in station_cols
        )
        station_lookup = station_regions[station_cols].drop_duplicates(right_key)
        if right_key != left_key:
            station_lookup = station_lookup.rename(columns={right_key: left_key})
        out = out.merge(station_lookup, on=left_key, how="left")
    if "station_region" in out.columns:
        out = _merge_geojson_region_class_metadata(out, Path(geojson_path), region_col="station_region")
    event_key = _common_key_pair(out, event_regions, (("event_id", "event_id"), ("event", "event"), ("event_id", "event")))
    if event_key is not None:
        left_key, right_key = event_key
        event_cols = [
            column
            for column in (
                right_key,
                "event_geojson_inside_any",
                "event_geojson_labels",
                "event_region",
            )
            if column in event_regions.columns
        ]
        event_lookup = event_regions[event_cols].drop_duplicates(right_key)
        if right_key != left_key:
            event_lookup = event_lookup.rename(columns={right_key: left_key})
        out = out.merge(event_lookup, on=left_key, how="left")
    if "station_region" in out.columns:
        out = out.loc[out["station_region"].fillna("").astype(str).str.strip().ne("")].copy()
    return out


def _preferred_step_05_boundary_region(geojson_path: str | Path) -> str:
    """Return the best basin selector available in the configured GeoJSON."""

    import json

    try:
        data = json.loads(Path(geojson_path).read_text(encoding="utf-8"))
    except Exception:
        return "LA Basin"
    features = data.get("features", []) if isinstance(data, dict) else []
    names: list[str] = []
    for feature in features:
        properties = feature.get("properties", {}) if isinstance(feature, dict) else {}
        if not isinstance(properties, dict):
            continue
        for key in ("name", "long_name", "short_name", "label", "region_name"):
            value = properties.get(key)
            if value is not None and str(value).strip():
                names.append(str(value).strip())
    for preferred in ("LA Basin", "Los Angeles Basin"):
        if preferred in names:
            return preferred
    for name in names:
        if "los angeles" in name.casefold() and "basin" in name.casefold():
            return name
    for name in names:
        if "basin" in name.casefold():
            return name
    return names[0] if names else "LA Basin"


def _first_nonempty_metric_value(df: pd.DataFrame, column: str, *, fallback: str) -> str:
    """Return the first non-empty dataframe value for a column."""

    if column not in df.columns:
        return str(fallback)
    values = df[column].dropna().astype(str)
    values = values.loc[values.str.strip().ne("")]
    return str(values.iloc[0]) if not values.empty else str(fallback)


def _common_key_pair(
    left: pd.DataFrame,
    right: pd.DataFrame,
    candidates: Sequence[tuple[str, str]],
) -> tuple[str, str] | None:
    """Return the first usable pair of key columns across two dataframes."""

    for left_key, right_key in candidates:
        if left_key in left.columns and right_key in right.columns:
            return left_key, right_key
    return None


def _write_step_05_region_boxplot_sweep(
    metrics_by_regions: pd.DataFrame,
    *,
    settings: Any,
    output_dir: str | Path,
    overwrite: bool,
    compare_to: str | None,
) -> pd.DataFrame:
    """Write station-region boxplots for every metric/passband available in Step 5 inputs."""

    if metrics_by_regions is None or metrics_by_regions.empty:
        return pd.DataFrame(
            [{"artifact": "region_boxplot_sweep", "status": "empty_input", "message": "no Step 5 metrics available"}]
        )
    from spatial_vtk.spatial.plot.metrics import boxplot

    metric_col = _first_existing_column(metrics_by_regions, ("metric", "metric_name"))
    band_col = _first_existing_column(metrics_by_regions, ("band", "passband", "period_band"))
    region_col = _first_existing_column(metrics_by_regions, ("station_region", "station_geojson_region"))
    value_col = str(getattr(settings, "value_col", "log2_residual") or "log2_residual")
    if metric_col is None or region_col is None or value_col not in metrics_by_regions.columns:
        return pd.DataFrame(
            [
                {
                    "artifact": "region_boxplot_sweep",
                    "status": "missing_columns",
                    "message": "Step 5 metric, station-region, or value columns are unavailable.",
                }
            ]
        )

    color_col = _first_existing_column(
        metrics_by_regions,
        (
            "mapped_region_type",
            "geomorphology",
            "target_region_zone",
            "mapped_region",
            "station_region_class",
            "region_class",
        ),
    )
    models = _step_05_selected_models(metrics_by_regions, settings)
    metrics = _ordered_nonempty_values(metrics_by_regions[metric_col])
    passbands = _ordered_nonempty_values(metrics_by_regions[band_col]) if band_col is not None else [None]
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    sidecar_kwargs = getattr(settings, "sidecars", None).kwargs() if getattr(settings, "sidecars", None) is not None else {}
    for model in models:
        model_rows = _step_05_filter_model(metrics_by_regions, model)
        if model_rows.empty:
            rows.append(
                {
                    "artifact": "region_boxplot",
                    "model": model,
                    "status": "no_data",
                    "figure_path": None,
                    "message": f"no rows match model {model!r}",
                }
            )
            continue
        model_label = _folder_token(model or "all-models")
        for metric in metrics:
            metric_rows = model_rows.loc[model_rows[metric_col].astype(str).eq(str(metric))]
            if metric_rows.empty:
                continue
            for passband in passbands:
                if passband is None:
                    plot_rows = metric_rows
                    passband_label = "all-passbands"
                    passband_arg = None
                else:
                    plot_rows = metric_rows.loc[metric_rows[band_col].astype(str).eq(str(passband))]
                    passband_label = str(passband)
                    passband_arg = passband
                plot_rows = plot_rows.copy()
                plot_value_col = _step_05_region_boxplot_value_column(
                    plot_rows,
                    metric=metric,
                    default_value_col=value_col,
                    band_col=band_col,
                )
                finite = pd.to_numeric(plot_rows[plot_value_col], errors="coerce").dropna()
                if plot_rows.empty or finite.empty:
                    rows.append(
                        {
                            "artifact": "region_boxplot",
                            "model": model,
                            "metric": metric,
                            "passband": passband_label,
                            "status": "no_data",
                            "figure_path": None,
                            "message": "no finite values to plot",
                        }
                    )
                    continue
                if color_col is not None and color_col in plot_rows.columns:
                    split_values = _ordered_nonempty_values(plot_rows[color_col])
                    split_values = [
                        value
                        for value in split_values
                        if str(value).strip().casefold() not in {"unknown", "none", "nan", "null", ""}
                    ]
                else:
                    split_values = [None]
                for region_type in split_values:
                    if region_type is None:
                        split_rows = plot_rows
                        region_type_label = "all-region-types"
                        region_type_filter = None
                    else:
                        split_rows = plot_rows.loc[plot_rows[color_col].astype(str).eq(str(region_type))].copy()
                        region_type_label = str(region_type)
                        region_type_filter = region_type_label
                    split_finite = pd.to_numeric(split_rows[plot_value_col], errors="coerce").dropna()
                    if split_rows.empty or split_finite.empty:
                        rows.append(
                            {
                                "artifact": "region_boxplot",
                                "model": model,
                                "metric": metric,
                                "passband": passband_label,
                                "mapped_region_type": region_type_label,
                                "status": "no_data",
                                "figure_path": None,
                                "message": "no finite values to plot for this mapped region type",
                            }
                        )
                        continue
                    figure_dir = (
                        root
                        / model_label
                        / _folder_token(metric)
                        / _passband_folder_token(passband_label)
                        / "mapped_region_type"
                        / _folder_token(region_type_label)
                    )
                    figure_dir.mkdir(parents=True, exist_ok=True)
                    output = figure_dir / (
                        f"region_boxplot__{model_label}__{_folder_token(metric)}__{_passband_folder_token(passband_label)}"
                        f"__{_folder_token(region_type_label)}__all-components__{_folder_token(plot_value_col)}.png"
                    )
                    if output.exists() and not overwrite:
                        rows.append(
                            {
                                "artifact": "region_boxplot",
                                "model": model,
                                "metric": metric,
                                "passband": passband_label,
                                "mapped_region_type": region_type_label,
                                "status": "exists",
                                "figure_path": str(output),
                                "message": f"skip {output.name}: exists",
                            }
                        )
                        continue
                    split_compare_to = getattr(settings, "compare_to", None) or compare_to
                    if split_compare_to is not None:
                        available_regions = {str(value) for value in split_rows[region_col].dropna().astype(str).unique()}
                        compare_values = [str(value) for value in ([split_compare_to] if isinstance(split_compare_to, str) else split_compare_to)]
                        if not any(value in available_regions for value in compare_values):
                            split_compare_to = None
                    try:
                        title = (
                            f"{metric} Residuals by Station Region\n"
                            f"Mapped Region Type: {region_type_label}"
                            if region_type_filter is not None
                            else f"{metric} Residuals by Station Region"
                        )
                        if model is not None:
                            title = f"{title}\nModel: {model}"
                        boxplot(
                            data=split_rows,
                            output_path=output,
                            dep=str(metric),
                            indep=region_col,
                            value_col=plot_value_col,
                            passband=passband_arg,
                            model=model,
                            component=None,
                            colorby=None,
                            compare_to=split_compare_to,
                            table=split_compare_to is not None,
                            title=title,
                            showfig=bool(getattr(settings, "showfig", False)),
                            savefig=True,
                            **sidecar_kwargs,
                        )
                        rows.append(
                            {
                                "artifact": "region_boxplot",
                                "model": model,
                                "metric": metric,
                                "passband": passband_label,
                                "mapped_region_type": region_type_label,
                                "status": "wrote",
                                "figure_path": str(output),
                                "message": f"wrote {output}",
                            }
                        )
                    except Exception as exc:
                        rows.append(
                            {
                                "artifact": "region_boxplot",
                                "model": model,
                                "metric": metric,
                                "passband": passband_label,
                                "mapped_region_type": region_type_label,
                                "status": "plot_failed",
                                "figure_path": str(output),
                                "message": f"{type(exc).__name__}: {exc}",
                            }
                        )
    return pd.DataFrame(rows)


def _step_05_selected_models(df: pd.DataFrame, settings: Any) -> list[object | None]:
    """Return requested or available models for Step 5 figure splitting."""

    requested = getattr(settings, "model", None)
    if requested is not None:
        if isinstance(requested, str):
            values = [requested]
        elif isinstance(requested, Sequence):
            values = list(requested)
        else:
            values = [requested]
        return [value for value in values if str(value).strip()] or [None]
    model_col = _first_existing_column(df, ("model", "model_name", "synthetic_model"))
    if model_col is None:
        return [None]
    values = _ordered_nonempty_values(df[model_col])
    return values or [None]


def _step_05_filter_model(df: pd.DataFrame, model: object | None) -> pd.DataFrame:
    """Filter Step 5 rows to one model when a model column is available."""

    if model is None:
        return df.copy()
    model_col = _first_existing_column(df, ("model", "model_name", "synthetic_model"))
    if model_col is None:
        return df.copy()
    return df.loc[df[model_col].astype(str).eq(str(model))].copy()


def _step_05_region_boxplot_value_column(
    plot_rows: pd.DataFrame,
    *,
    metric: object,
    default_value_col: str,
    band_col: str | None,
) -> str:
    """Return the scientifically appropriate plotted value for one Step 5 region boxplot."""

    metric_key = str(metric).strip().casefold()
    if metric_key in {"original_cc", "delay_corrected_cc"} and "value" in plot_rows.columns:
        return "value"
    if metric_key == "traveltime_delay" and "value" in plot_rows.columns:
        output_col = "delay_fraction_dominant_period"
        if output_col not in plot_rows.columns:
            periods = (
                plot_rows[band_col].map(_dominant_period_seconds_from_label)
                if band_col is not None and band_col in plot_rows.columns
                else pd.Series(1.0, index=plot_rows.index)
            )
            periods = pd.to_numeric(periods, errors="coerce").replace(0.0, pd.NA)
            plot_rows[output_col] = pd.to_numeric(plot_rows["value"], errors="coerce") / periods
        return output_col
    if default_value_col in plot_rows.columns and pd.to_numeric(plot_rows[default_value_col], errors="coerce").notna().any():
        return default_value_col
    if "value" in plot_rows.columns:
        return "value"
    return default_value_col


def _step_05_station_map_value_column(metric: object, source_value_col: str) -> str:
    """Return a readable value-column name for Step 5 station metric maps."""

    metric_key = str(metric).strip().casefold()
    if metric_key in {"original_cc", "delay_corrected_cc"} and source_value_col == "value":
        return "cross_correlation"
    if metric_key == "traveltime_delay":
        return "delay_fraction_dominant_period"
    if source_value_col == "value":
        return "metric_value"
    return source_value_col


def _dominant_period_seconds_from_label(value: object) -> float:
    """Return a representative period for labels such as ``1-2 sec``."""

    import re

    numbers = [float(item) for item in re.findall(r"\d+(?:\.\d+)?", str(value))]
    if len(numbers) >= 2:
        return sum(numbers[:2]) / 2.0
    if len(numbers) == 1:
        return numbers[0]
    return 1.0


def _first_existing_column(df: pd.DataFrame, candidates: Sequence[str]) -> str | None:
    """Return the first candidate column present in a dataframe."""

    for column in candidates:
        if column in df.columns:
            return column
    return None


def _ordered_nonempty_values(series: pd.Series) -> list[object]:
    """Return non-empty values in dataframe order."""

    values = []
    seen: set[str] = set()
    for value in series.dropna():
        text = str(value).strip()
        if not text or text.casefold() in {"nan", "none", "null"} or text in seen:
            continue
        seen.add(text)
        values.append(value)
    return values


def _figure_set_filters(spec: dict[str, Any]) -> dict[str, object]:
    """Return row filters requested by a notebook figure-set spec."""

    filters: dict[str, object] = {}
    aliases = {
        "passband": "band",
        "components": "component",
        "component": "component",
        "model": "model",
        "metric": "metric",
        "station_family": "station_family",
        "stations": "station",
        "station": "station",
        "network": "network",
    }
    for key, column in aliases.items():
        if spec.get(key) is not None:
            value = spec[key]
            if key == "station_family":
                value = str(value).strip().lower()
            filters[column] = value
    return filters


def _figure_set_dir(base_figure_dir: str | Path, label: str, *, prefix: str) -> Path:
    """Return the output directory for one filtered figure set."""

    base = Path(base_figure_dir)
    root = base.parent if base.name in {"metrics", "default"} else base
    safe_label = _folder_token(label)
    if safe_label.startswith(prefix):
        return root / safe_label
    return root / f"{prefix}{safe_label}"


def _metric_figure_set_label(filters: dict[str, object]) -> str:
    """Build a concise default label from figure-set filters."""

    parts: list[str] = []
    if "metric" in filters:
        parts.append(f"metric_{_folder_token(filters['metric'])}")
    if "band" in filters:
        parts.append(_passband_folder_token(filters["band"]))
    if "component" in filters:
        value = filters["component"]
        if isinstance(value, (list, tuple)):
            prefix = "component" if len(value) == 1 else "components"
            parts.append(prefix + "_" + "-".join(_folder_token(item) for item in value))
        else:
            parts.append(f"component_{_folder_token(value)}")
    if "model" in filters:
        parts.append(f"model_{_folder_token(filters['model'])}")
    if "station_family" in filters:
        parts.append(f"{_folder_token(filters['station_family'])}_only")
    if "network" in filters:
        parts.append(f"network_{_folder_token(filters['network'])}")
    if "station" in filters:
        value = filters["station"]
        if isinstance(value, (list, tuple)):
            preview = "-".join(_folder_token(item) for item in list(value)[:3])
            suffix = f"{preview}_and_more" if len(value) > 3 else preview
            parts.append(f"stations_{suffix}")
        else:
            parts.append(f"station_{_folder_token(value)}")
    return "_".join(parts) or "custom"


def _metric_figure_set_result_name(figure_dir: Path) -> str:
    """Return a compact result key for one filtered figure-set directory."""

    return _figure_set_result_name(figure_dir, "metrics_figures_")


def _figure_set_result_name(figure_dir: Path, prefix: str) -> str:
    """Return a compact result key for one filtered figure-set directory."""

    return figure_dir.name.replace(prefix, "", 1)


def _region_figure_set_label(spec: dict[str, Any], filters: dict[str, object]) -> str:
    """Build a concise default label for one Step 5 figure-set spec."""

    parts = [_metric_figure_set_label(filters)]
    if spec.get("compare_to") is not None:
        parts.append(f"compare_{_folder_token(spec['compare_to'])}")
    if spec.get("geojson_path") is not None:
        parts.append("custom_geojson")
    if spec.get("corridor_filters"):
        parts.append("corridors_filtered")
    return "_".join(part for part in parts if part and part != "custom") or "custom"


def _single_filter_value(value: object) -> str | None:
    """Return the first scalar value from a filter setting."""

    if isinstance(value, (list, tuple)):
        return None if not value else str(value[0])
    return str(value)


def _passband_folder_token(value: object) -> str:
    """Return a compact passband token for figure-set folder names."""

    text = str(value).strip().lower()
    text = text.replace(" seconds", "s").replace(" second", "s").replace(" sec", "s")
    text = text.replace(" ", "")
    return _folder_token(text)


def _folder_token(value: object) -> str:
    """Return a readable filesystem token for notebook-created figure sets."""

    import re

    text = str(value).strip().replace("/", "-")
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_")
    return text or "custom"


def _ignore_display(_: Any) -> None:
    """Suppress detailed readiness tables in action-oriented notebooks."""

    return None


def _env_bool(name: str, *, default: bool = False) -> bool:
    """Return a permissive boolean parsed from an environment variable."""

    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _print_session(session: LargeRunSession) -> None:
    """Print concise controls for the active session."""

    print("Large-run config activated.")
    print(f"Config: {session.context.config_path}")
    print(
        "Controls: "
        f"overwrite={session.overwrite}, submit_slurm={session.submit_slurm}, "
        f"run_local={session.run_local}, make_figures={session.make_figures}"
    )


def _announce_long_step(action: str, message: str, session: LargeRunSession) -> None:
    """Print a concise warning before a potentially long-running action."""

    print(f"{action}: {message}")
    if session.submit_slurm:
        print("Slurm submission is enabled; eligible heavy work may be submitted.")
    else:
        print("Slurm submission is disabled; eligible heavy work will write scripts/commands instead.")


def _finish_action(action: str, message: str, results: dict[str, Any]) -> LargeRunActionResult:
    """Print and return one compact action result."""

    print(f"{action}: {message}")
    for name, result in results.items():
        print(f"- {name}: {_result_message(result)}")
    return LargeRunActionResult(action=action, message=message, results=results)


def _result_message(result: Any) -> str:
    """Return a compact message for common workflow result objects."""

    if result is None:
        return "no action needed"
    if isinstance(result, dict):
        message = result.get("message")
        if message:
            return str(message)
        status = result.get("status") or ("current" if result.get("reused") else None)
        if status:
            return str(status)
    if hasattr(result, "status_frame"):
        try:
            frame = result.status_frame()
        except Exception:
            frame = None
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            dashboard_message = _dashboard_result_message(frame)
            if dashboard_message:
                return dashboard_message
            statuses = []
            for column in ("status", "Status"):
                if column in frame.columns:
                    statuses = [str(item) for item in frame[column].dropna().unique()[:4]]
                    break
            if statuses:
                return ", ".join(statuses)
    if hasattr(result, "job_id"):
        job_id = getattr(result, "job_id", None)
        return f"submitted Slurm job {job_id}" if job_id else "Slurm script prepared"
    return "completed"


def _dashboard_result_message(frame: pd.DataFrame) -> str:
    """Return actionable dashboard launch guidance from a status frame."""

    if "dashboard" not in frame.columns or "status" not in frame.columns:
        return ""
    row = frame.iloc[0]
    status = str(row.get("status", "") or "")
    url = str(row.get("url", "") or "")
    command = str(row.get("terminal_command", "") or "")
    message = str(row.get("message", "") or "")
    if status == "running":
        return f"running at {url}" if url else (message or "running")
    if status == "command":
        if command:
            return f"run in a terminal: {command}"
        return message or "launch command available"
    if status == "error":
        return message or "launch failed"
    return message


__all__ = [
    "LargeRunActionResult",
    "LargeRunSession",
    "activate_large_run",
    "calculate_metrics",
    "launch_metrics_dashboard",
    "launch_qc_dashboard",
    "make_additional_diagnostic_figures",
    "make_context_figures",
    "make_filtered_metric_figures",
    "make_filtered_region_corridor_figures",
    "make_filtered_spatial_figures",
    "make_metric_figures",
    "make_qc_figures",
    "make_region_corridor_figures",
    "make_spatial_figures",
    "prepare_metrics_dashboard",
    "run_geojson_corridors",
    "run_ingest",
    "run_quality_control",
    "run_spatial_statistics",
]
