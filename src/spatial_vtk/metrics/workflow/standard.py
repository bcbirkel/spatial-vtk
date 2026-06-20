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


__all__ = [
    "StandardMetricWorkflowOutputResult",
    "load_standard_metric_workflow_outputs",
]
