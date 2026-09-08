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

Basemaps missing from all tutorial figures
   Check ``SVTK_NO_BASEMAP`` first. It is an explicit opt-out, not a provider
   failure. Final runs with ``tools/execute_tutorial_notebooks.py`` require
   imagery and reject that setting. ``--allow-missing-basemaps`` is reserved
   for computation-only CI; its outputs cannot be used for final contact sheets.

Reuse imagery across runs
   Set ``SVTK_BASEMAP_CACHE`` to a persistent writable directory. Run
   ``python tools/prepare_tutorial_basemap.py --cache-dir PATH`` once to cache
   Esri World Imagery for the Southern California examples. Later renders
   reuse covering GeoTIFFs. Other extents may still require downloads. Keep
   this generated cache out of git. No alternate provider is silently substituted
   when ``SVTK_REQUIRE_BASEMAP=1`` is set by the final tutorial runner.

Verify a final visual review
   Inspect ``outputs/tutorial_execution/basemaps.jsonl`` for actual rendering
   outcomes. Contact sheets require ``--execution-manifest`` pointing to a
   successful imagery-required run; figure hashes must match that execution.
