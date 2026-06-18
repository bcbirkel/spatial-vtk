"""Spatial-statistics workflow helpers.

``spatial_vtk.spatial`` is the stable import surface for spatial calculations,
GeoJSON summaries, corridors, geometry, PCA, clustering, path summaries, and
pattern-comparison helpers. Plotting and mapping helpers live in the public
``spatial_vtk.spatial.plot`` and ``spatial_vtk.spatial.map`` subpackages so
users can import figure code without mixing it into the calculation namespace.
"""

from __future__ import annotations

from spatial_vtk.spatial.calculate import *  # noqa: F401,F403
from spatial_vtk.spatial.calculate import __all__ as _CALCULATE_EXPORTS

__all__ = sorted(_CALCULATE_EXPORTS)
