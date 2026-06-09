# Data Provenance

Spatial-VTK does not download observed waveforms or run simulations for you.
The public examples start from waveform and metadata files that have already
been prepared so you can focus on the validation workflow.

## Example Dataset

The tutorial dataset is a five-event LA Basin subset under
`data/examples/20260605_five_event_subset/`. It includes observed and synthetic
MiniSEED files, event metadata, station metadata, and event-station tables for
the tutorial notebooks.

The supporting `data/examples/la_basin_five_event_subset/` folder contains
lightweight event, station, and GeoJSON files used by the data-format examples
and regional/corridor tutorials.

The example events are southern California earthquakes with public USGS event
pages:

- `ci38038071`: M 4.4, 4 km N of La Verne, CA, 2018-08-29.
- `ci38695658`: M 4.5, 3 km WSW of South El Monte, CA, 2020-09-19.
- `ci39812319`: M 4.3, 2 km E of Carson, CA, 2021-09-18.
- `ci39756418`: M 4.2, 3 km SW of San Bernardino, CA, 2024-01-25.
- `ci40699207`: M 4.4, 4 km SSE of Highland Park, CA, 2024-08-12.

## Observed Records

Observed records in the public examples are derived from public southern
California waveform sources:

- Southern California Seismic Network (SCSN), network code `CI`,
  DOI `10.7914/SN/CI`.
- Center for Engineering Strong Motion Data (CESMD).

The observed records were processed with `gmprocess` before they were packaged
for the tutorial subset. The tutorial workflow applies a configurable 1 Hz
lowpass preprocessing step to both observed and synthetic records before QC,
metric calculations, waveform figures, spatial analysis, and dashboards.

## Synthetic Records

Synthetic records in the public examples were generated with Salvus for a
southern California CVM-SI/CVM-S4.26.M01 velocity-model context. The model and
simulation provenance should be cited as:

- Salvus, for the waveform simulation software.
- UCVM, for the velocity-model software context.
- SCEC CVM-S4.26.M01, for the southern California velocity-model context.
- SCEC, for the community model and regional seismic-modeling context.

The synthetic files in the example bundle are tutorial-scale MiniSEED exports,
not a complete simulation archive.

## Geospatial Files

The example GeoJSON files under `data/examples/**` are small tutorial regions
used to demonstrate polygon joins, regional contrasts, and corridor/path
selection. They are intended to show how the package works. For a real project,
replace them with your own mapped geologic, geomorphic, administrative, or
analysis-region polygons and cite those sources separately.

The site/geology metadata examples are derived tutorial tables that show the
expected column structure for mapped region labels, long region names, broad
region classes, and geomorphology classes.

## Basemaps

Basemap files are not redistributed in this repository or in the PyPI wheel.
Static map figures fetch basemap tiles at render time with `contextily` and
default to Esri World Imagery. Dashboard maps are rendered with Folium/Leaflet
and can use Esri, CARTO, or OpenStreetMap tile layers.

You need network access for basemap-backed maps unless you configure a local
tile cache. If you use basemaps in figures or dashboards, cite the tile provider
required by your chosen basemap source. The root `CITATION.cff` includes
references for `contextily`, Esri World Imagery, CARTO basemaps, and
OpenStreetMap.

## Package Dependencies

Spatial-VTK depends on the scientific Python and geospatial ecosystem,
including NumPy, pandas, GeoPandas, Matplotlib, SciPy, scikit-learn,
statsmodels, Shapely, pyproj, ObsPy, PyArrow, Folium, Streamlit, and
contextily. The root `CITATION.cff` lists the major package dependencies and
example-data sources that should be cited when they are material to your work.
