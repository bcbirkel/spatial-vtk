"""Standard metric notebook workflow helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StandardMetricWorkflowOutputResult:
    """Configured Step 3 output group and bounded preview helpers."""

    outputs: object
    cfg: Any | None = None
    task_estimate: object | None = None
    trace_metadata_path: object | None = None

    def status_frame(self) -> object:
        """Return Step 3 output status, including trace metadata when known."""

        extra_paths = (
            {"trace_metadata_path": self.trace_metadata_path}
            if self.trace_metadata_path is not None
            else None
        )
        return self.outputs.status_frame(extra_paths=extra_paths)

    @property
    def metrics_long_path(self) -> object:
        """Return the configured ``metrics_long`` table path."""

        return self.outputs.metrics_long_path

    def display_task_previews(
        self,
        *,
        nrows: int = 12,
        display_fn: Any | None = None,
    ) -> dict[str, object]:
        """Display the configured metric task preview table."""

        return self.outputs.display_table_previews(
            {"metric_tasks": "metric_tasks_path"},
            cfg=self.cfg,
            nrows=nrows,
            display_fn=display_fn,
        )

    def display_metrics_preview(
        self,
        *,
        nrows: int = 5,
        display_fn: Any | None = None,
    ) -> dict[str, object]:
        """Display a bounded preview of the configured ``metrics_long`` table."""

        return self.outputs.display_table_previews(
            {"metrics_long": "metrics_long_path"},
            cfg=self.cfg,
            nrows=nrows,
            display_fn=display_fn,
        )

    def load_metrics_long(self, **kwargs: Any) -> object:
        """Load the configured ``metrics_long`` table for plotting helpers."""

        return self.outputs.load_table("metrics_long", cfg=self.cfg, **kwargs)

    def with_task_estimate(self) -> "StandardMetricWorkflowOutputResult":
        """Return a copy with the configured metric task estimate loaded."""

        return StandardMetricWorkflowOutputResult(
            outputs=self.outputs,
            cfg=self.cfg,
            task_estimate=self.outputs.load_table("metric_task_estimate_path", cfg=self.cfg, missing="skip"),
            trace_metadata_path=self.trace_metadata_path,
        )

    def write_standard_diagnostic_figures(
        self,
        settings: Any,
        *,
        metric_names: Sequence[object] = ("PGA", "PGV", "PGD"),
        **kwargs: Any,
    ) -> object:
        """Load ``metrics_long`` and write the standard Step 3 diagnostic figures.

        The standard tutorial uses this method so the result object owns the
        configured metric table, output group, and diagnostic figure writer.
        Additional keyword arguments are forwarded to
        :func:`spatial_vtk.metrics.plot.write_standard_metric_diagnostic_figures`.
        """

        from spatial_vtk.metrics.plot import write_standard_metric_diagnostic_figures

        return write_standard_metric_diagnostic_figures(
            self.load_metrics_long(),
            self.outputs,
            settings,
            metric_names=metric_names,
            **kwargs,
        )

    def write_configured_outputs(
        self,
        *,
        metric_rows: object | None = None,
        events: object | None = None,
        stations: object | None = None,
        residual_column: str | None = None,
        score_column: str | None = None,
        table_format: str = "parquet",
        dashboard_partitioned: bool = True,
    ) -> dict[str, str]:
        """Write downstream metric outputs using this result's active config."""

        from spatial_vtk.metrics.workflow.configured import write_metric_outputs_from_config

        return write_metric_outputs_from_config(
            config_path=getattr(self.cfg, "config_path", None),
            run_scenario=getattr(self.cfg, "run_scenario", None),
            metric_rows=metric_rows,
            events=events,
            stations=stations,
            residual_column=residual_column,
            score_column=score_column,
            table_format=table_format,
            dashboard_partitioned=dashboard_partitioned,
        )

    def write_station_metric_map(
        self,
        settings: Any,
        *,
        metric: str,
        value_col: str = "log2_residual",
        passband: str | None = None,
        components: list[str] | str | None = None,
        model: str | None = None,
        title: str | None = None,
        preview_rows: int = 5,
        make_figures: bool = True,
        overwrite: bool = True,
    ) -> object:
        """Load ``metrics_long`` and write one standard station metric map."""

        from spatial_vtk.metrics.plot import write_station_metric_map_from_notebook_settings

        return write_station_metric_map_from_notebook_settings(
            self.load_metrics_long(),
            settings,
            metric=metric,
            value_col=value_col,
            passband=passband,
            components=components,
            model=model,
            title=title,
            preview_rows=preview_rows,
            make_figures=make_figures,
            overwrite=overwrite,
        )

    def run_inventory_step_if_needed(
        self,
        context: Any,
        *,
        overwrite: bool = False,
        verbose: bool = True,
        current_message: str | None = "Metric waveform inventories are current; skipping.",
        script_name: str = "step03_metric_inventories.slurm",
        job_name: str = "svtk-step03-inventory",
        walltime: str = "04:00:00",
        memory: str = "32G",
        cpus: int = 1,
        run_local: bool | None = None,
        section: str | None = "compute.slurm",
        display_fn: Any | None = None,
    ) -> object:
        """Run or submit Step 3 metric inventory building when outputs are stale."""

        from spatial_vtk.config import run_notebook_step_if_needed
        from spatial_vtk.metrics.workflow.configured import (
            build_metric_waveform_inventories_from_config,
            metric_inventories_readiness_from_config,
        )

        config_path = _metric_result_config_path(self.cfg, context)
        run_scenario = _metric_result_run_scenario(self.cfg, context)
        readiness = metric_inventories_readiness_from_config(
            config_path=config_path,
            run_scenario=run_scenario,
            overwrite=overwrite,
            current_message=current_message,
        )
        return run_notebook_step_if_needed(
            context,
            readiness,
            build_metric_waveform_inventories_from_config,
            kwargs={
                "config_path": str(config_path) if config_path is not None else None,
                "run_scenario": run_scenario,
                "overwrite": overwrite,
                "verbose": verbose,
            },
            script_name=script_name,
            job_name=job_name,
            walltime=walltime,
            memory=memory,
            cpus=cpus,
            run_local=run_local,
            section=section,
            display_fn=display_fn,
        )

    def run_manifest_step_if_needed(
        self,
        context: Any,
        *,
        overwrite: bool = False,
        batch_count: int | None = None,
        manifest: bool = True,
        current_message: str | None = "Metric manifest is current; skipping planning.",
        script_name: str = "step03_metric_plan.slurm",
        job_name: str = "svtk-step03-plan",
        walltime: str = "12:00:00",
        memory: str = "32G",
        cpus: int = 1,
        run_local: bool | None = True,
        section: str | None = "compute.slurm",
        display_fn: Any | None = None,
    ) -> object:
        """Run Step 3 metric manifest planning when the manifest is stale."""

        from spatial_vtk.config import run_notebook_step_if_needed
        from spatial_vtk.metrics.workflow.configured import (
            metric_manifest_readiness_from_config,
            plan_metric_tasks_from_config,
        )

        config_path = _metric_result_config_path(self.cfg, context)
        run_scenario = _metric_result_run_scenario(self.cfg, context)
        readiness = metric_manifest_readiness_from_config(
            config_path=config_path,
            run_scenario=run_scenario,
            overwrite=overwrite,
            current_message=current_message,
        )
        return run_notebook_step_if_needed(
            context,
            readiness,
            plan_metric_tasks_from_config,
            kwargs={
                "config_path": str(config_path) if config_path is not None else None,
                "run_scenario": run_scenario,
                "manifest": manifest,
                "batch_count": batch_count,
            },
            script_name=script_name,
            job_name=job_name,
            walltime=walltime,
            memory=memory,
            cpus=cpus,
            run_local=run_local,
            section=section,
            display_fn=display_fn,
        )

    def run_slurm_step_if_needed(
        self,
        context: Any,
        *,
        overwrite: bool = False,
        submit: bool = False,
        incomplete_only: bool | None = None,
        overwrite_batches: bool | None = None,
        script_name: str = "step03_write_metric_slurm.slurm",
        job_name: str = "svtk-step03-slurm",
        walltime: str = "12:00:00",
        memory: str = "32G",
        cpus: int = 1,
        run_local: bool | None = True,
        section: str | None = "compute.slurm",
        display_fn: Any | None = None,
    ) -> object:
        """Write or submit the Step 3 metric Slurm array when work remains."""

        from spatial_vtk.config import run_notebook_step_if_needed
        from spatial_vtk.metrics.workflow.configured import (
            metric_slurm_submission_readiness_from_config,
            write_metrics_slurm_script_from_config,
        )

        config_path = _metric_result_config_path(self.cfg, context)
        run_scenario = _metric_result_run_scenario(self.cfg, context)
        readiness = metric_slurm_submission_readiness_from_config(
            config_path=config_path,
            run_scenario=run_scenario,
            overwrite=overwrite,
        )
        return run_notebook_step_if_needed(
            context,
            readiness,
            write_metrics_slurm_script_from_config,
            kwargs={
                "config_path": str(config_path) if config_path is not None else None,
                "run_scenario": run_scenario,
                "incomplete_only": (not overwrite) if incomplete_only is None else incomplete_only,
                "overwrite_batches": overwrite if overwrite_batches is None else overwrite_batches,
                "submit": submit,
            },
            script_name=script_name,
            job_name=job_name,
            walltime=walltime,
            memory=memory,
            cpus=cpus,
            run_local=run_local,
            section=section,
            display_fn=display_fn,
        )

    def run_merge_step_if_needed(
        self,
        context: Any,
        *,
        overwrite: bool = False,
        script_name: str = "step03_merge_metric_batches.slurm",
        job_name: str = "svtk-step03-merge",
        walltime: str = "02:00:00",
        memory: str = "32G",
        cpus: int = 1,
        run_local: bool | None = None,
        section: str | None = "compute.slurm",
        display_fn: Any | None = None,
    ) -> object:
        """Run or submit Step 3 metric batch merging when outputs are stale."""

        from spatial_vtk.config import run_notebook_step_if_needed
        from spatial_vtk.metrics.workflow.configured import (
            merge_metric_batches_from_config,
            metric_batch_merge_readiness_from_config,
        )

        config_path = _metric_result_config_path(self.cfg, context)
        run_scenario = _metric_result_run_scenario(self.cfg, context)
        readiness = metric_batch_merge_readiness_from_config(
            config_path=config_path,
            run_scenario=run_scenario,
            overwrite=overwrite,
        )
        return run_notebook_step_if_needed(
            context,
            readiness,
            merge_metric_batches_from_config,
            kwargs={
                "config_path": str(config_path) if config_path is not None else None,
                "run_scenario": run_scenario,
            },
            script_name=script_name,
            job_name=job_name,
            walltime=walltime,
            memory=memory,
            cpus=cpus,
            run_local=run_local,
            section=section,
            display_fn=display_fn,
        )

    def run_downstream_outputs_step_if_needed(
        self,
        context: Any,
        *,
        overwrite: bool = False,
        table_format: str = "parquet",
        dashboard_partitioned: bool = True,
        script_name: str = "step03_metric_outputs.slurm",
        job_name: str = "svtk-step03-outputs",
        walltime: str = "08:00:00",
        memory: str = "32G",
        cpus: int = 1,
        run_local: bool | None = None,
        section: str | None = "compute.slurm",
        display_fn: Any | None = None,
    ) -> object:
        """Run or submit downstream Step 3 metric output writing when stale."""

        from spatial_vtk.config import run_notebook_step_if_needed
        from spatial_vtk.metrics.workflow.configured import (
            metric_outputs_readiness_from_config,
            write_metric_outputs_from_config,
        )

        config_path = _metric_result_config_path(self.cfg, context)
        run_scenario = _metric_result_run_scenario(self.cfg, context)
        readiness = metric_outputs_readiness_from_config(
            config_path=config_path,
            run_scenario=run_scenario,
            overwrite=overwrite,
        )
        return run_notebook_step_if_needed(
            context,
            readiness,
            write_metric_outputs_from_config,
            kwargs={
                "config_path": str(config_path) if config_path is not None else None,
                "run_scenario": run_scenario,
                "table_format": table_format,
                "dashboard_partitioned": dashboard_partitioned,
            },
            script_name=script_name,
            job_name=job_name,
            walltime=walltime,
            memory=memory,
            cpus=cpus,
            run_local=run_local,
            section=section,
            display_fn=display_fn,
        )

    def write_large_run_figure_suite(
        self,
        settings: Any,
        *,
        overwrite: bool = False,
    ) -> object:
        """Write the large-run Step 3 metric figure suite from configured outputs."""

        from spatial_vtk.metrics.plot import write_large_run_metric_figure_suite_from_notebook_settings

        return write_large_run_metric_figure_suite_from_notebook_settings(
            self.metrics_long_path,
            settings,
            overwrite=overwrite,
        )


def load_standard_metric_workflow_outputs(
    *,
    cfg: Any | None = None,
    output_group_name: str = "step_03_metrics",
    load_task_estimate: bool = True,
) -> StandardMetricWorkflowOutputResult:
    """Load standard Step 3 output handles and small preview tables.

    Parameters
    ----------
    cfg
        Active Spatial-VTK config. When omitted, the active config is used by
        the underlying output-group helpers.
    output_group_name
        Configured output group that owns the standard Step 3 metric tables.
    load_task_estimate
        Whether to load ``metric_task_estimate`` immediately. Set ``False`` in
        setup cells before the task preview has been generated.

    Returns
    -------
    StandardMetricWorkflowOutputResult
        Configured Step 3 output group plus convenience methods for the task
        preview, ``metrics_long`` preview, and plotting-table load.
    """

    from spatial_vtk.io import output_group, preprocessed_waveform_metadata_paths

    outputs = output_group(output_group_name, cfg=cfg)
    trace_metadata_path = preprocessed_waveform_metadata_paths(config=cfg).trace_metadata_path
    task_estimate = (
        outputs.load_table("metric_task_estimate_path", cfg=cfg, missing="skip")
        if load_task_estimate
        else None
    )
    return StandardMetricWorkflowOutputResult(
        outputs=outputs,
        cfg=cfg,
        task_estimate=task_estimate,
        trace_metadata_path=trace_metadata_path,
    )


def _metric_result_config_path(cfg: Any | None, context: Any | None) -> object | None:
    """Return the config path carried by a metric result or notebook context."""

    value = getattr(cfg, "config_path", None)
    return value if value is not None else getattr(context, "config_path", None)


def _metric_result_run_scenario(cfg: Any | None, context: Any | None) -> str | None:
    """Return the active run scenario carried by a metric result or context."""

    value = getattr(cfg, "run_scenario", None)
    return value if value is not None else getattr(context, "run_scenario", None)


__all__ = [
    "StandardMetricWorkflowOutputResult",
    "load_standard_metric_workflow_outputs",
]
