Future Features
===============

This page tracks planned package additions that are not part of the current
public migration milestone.

Interactive GeoJSON and Corridor Drawing
----------------------------------------

Add an optional interactive map workflow for creating GeoJSON inputs directly
from Spatial-VTK.

Planned behavior:

* Use ``leafmap`` as the preferred optional backend through an interactive
  dependency extra, such as ``spatial-vtk[interactive]``.
* Provide notebook and CLI entry points for opening a map with stations and
  events shown by default.
* Allow optional reference GeoJSON layers for regions, faults, geologic units,
  or other project context.
* Let users draw arbitrary polygons, corridor polygons, and line features.
* Save drawn features to standard GeoJSON with clear feature properties so the
  files can be used by ``spatial_vtk.spatial.calculate.geojson`` and
  ``spatial_vtk.spatial.calculate.corridors``.
* Keep drawing/editing dependencies optional so the core package remains usable
  in non-interactive or server environments.

Open design details:

* Decide whether the CLI opens a local notebook-style app, writes a temporary
  HTML map, or launches a lightweight local web app around ``leafmap``.
* Define the saved GeoJSON property schema for ``region``, ``corridor``, and
  ``annotation`` features.
* Add round-trip tests that create a small context map, save drawn GeoJSON, and
  pass that GeoJSON into the corridor and polygon-selection functions.
