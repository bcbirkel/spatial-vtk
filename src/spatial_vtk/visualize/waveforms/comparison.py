"""Observed/synthetic trace comparison figures.

Purpose
-------
This module hosts waveform-oriented trace comparison APIs. The implementation
currently reuses the tested public context helper while making the preferred
module path `spatial_vtk.visualize.waveforms`.
"""

from __future__ import annotations

from spatial_vtk.visualize.context.figures import plot_event_trace_comparison

__all__ = ["plot_event_trace_comparison"]
