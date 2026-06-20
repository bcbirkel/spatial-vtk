"""Lightweight spatial workflow loader wrappers.

These wrappers keep the top-level ``spatial_vtk.spatial`` workflow import
surface available without importing the plotting backend at package import
time. The implementation lives in ``spatial_vtk.spatial.plot`` because the
returned objects also own figure-writing methods.
"""

from __future__ import annotations

from typing import Any


def load_standard_geojson_workflow_output_status(*args: Any, **kwargs: Any) -> Any:
    """Return standard Step 5 GeoJSON output status and runner helpers."""

    from spatial_vtk.spatial.plot import load_standard_geojson_workflow_output_status as _loader

    return _loader(*args, **kwargs)


def load_standard_geojson_plotting_inputs(*args: Any, **kwargs: Any) -> Any:
    """Return standard Step 5 GeoJSON plotting inputs and figure helpers."""

    from spatial_vtk.spatial.plot import load_standard_geojson_plotting_inputs as _loader

    return _loader(*args, **kwargs)


def load_standard_additional_plotting_output_status(*args: Any, **kwargs: Any) -> Any:
    """Return standard Step 6 additional-plotting output status helpers."""

    from spatial_vtk.spatial.plot import load_standard_additional_plotting_output_status as _loader

    return _loader(*args, **kwargs)


def load_standard_additional_plotting_inputs(*args: Any, **kwargs: Any) -> Any:
    """Return standard Step 6 additional-plotting inputs and figure helpers."""

    from spatial_vtk.spatial.plot import load_standard_additional_plotting_inputs as _loader

    return _loader(*args, **kwargs)


__all__ = [
    "load_standard_additional_plotting_inputs",
    "load_standard_additional_plotting_output_status",
    "load_standard_geojson_plotting_inputs",
    "load_standard_geojson_workflow_output_status",
]
