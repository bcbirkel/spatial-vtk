"""Standard metric notebook workflow helpers."""

from __future__ import annotations

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
