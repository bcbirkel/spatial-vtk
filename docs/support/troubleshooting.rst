Troubleshooting
===============

This page tracks common setup, data, basemap, and notebook-rendering problems
for the public package.

Basemap downloads fail
   Map examples use contextily to fetch tiles at render time. Check network
   access or configure a local tile cache. If a map draws a plain gray
   background instead of imagery, rerun the plotting call with
   ``basemap_kwargs={"on_error": "raise"}`` to show the dependency, cache, or
   network error directly.
