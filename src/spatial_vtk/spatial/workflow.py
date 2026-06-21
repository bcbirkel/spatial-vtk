"""Lightweight spatial workflow loader wrappers.

These wrappers keep the top-level ``spatial_vtk.spatial`` workflow import
surface available without importing the plotting backend at package import
time. The concrete loaders are imported lazily from ``spatial_vtk.spatial.plot``
because the returned objects also own figure-writing methods.
"""

from __future__ import annotations

from typing import Any


def load_standard_geojson_workflow_output_status(*args: Any, **kwargs: Any) -> Any:
    """Return standard Step 5 GeoJSON output status and runner helpers.

    The returned result owns ``status_frame()``, bounded
    ``display_table_previews(...)``, ``run_geojson_summary_step_if_needed(...)``,
    ``run_corridor_step_if_needed(...)``, and the configured Step 5 figure
    writers, so large-run notebooks do not need output-group or path plumbing.
    """

    from spatial_vtk.spatial.plot import load_standard_geojson_workflow_output_status as _loader

    return _loader(*args, **kwargs)


def load_standard_geojson_plotting_inputs(*args: Any, **kwargs: Any) -> Any:
    """Return standard Step 5 GeoJSON plotting inputs and figure helpers.

    The result loads the configured metric, metadata, comparison-eligible, and
    GeoJSON inputs needed by the standard Step 5 region and corridor figure
    suites.
    """

    from spatial_vtk.spatial.plot import load_standard_geojson_plotting_inputs as _loader

    return _loader(*args, **kwargs)


def load_standard_additional_plotting_output_status(*args: Any, **kwargs: Any) -> Any:
    """Return standard Step 6 additional-plotting output status helpers.

    The returned result owns ``status_frame()``, bounded
    ``display_metric_source_preview(...)``, ``write_waveform_comparison(...)``,
    and ``write_region_boxplot(...)`` so large-run notebooks can inspect and
    render Step 6 products without loading full metric tables.
    """

    from spatial_vtk.spatial.plot import load_standard_additional_plotting_output_status as _loader

    return _loader(*args, **kwargs)


def load_standard_additional_plotting_inputs(*args: Any, **kwargs: Any) -> Any:
    """Return standard Step 6 additional-plotting inputs and figure helpers.

    The result loads the configured metric snapshot, prepared event metadata,
    event-station records, comparison-eligible records, and Step 6 output group
    used by the standard additional-plotting figure suite.
    """

    from spatial_vtk.spatial.plot import load_standard_additional_plotting_inputs as _loader

    return _loader(*args, **kwargs)


__all__ = [
    "load_standard_additional_plotting_inputs",
    "load_standard_additional_plotting_output_status",
    "load_standard_geojson_plotting_inputs",
    "load_standard_geojson_workflow_output_status",
]
