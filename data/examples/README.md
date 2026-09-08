# Example Data Provenance

Spatial-VTK includes small example files so you can run the tutorials from a
source checkout and see the expected table, waveform, map, and dashboard
outputs. The example files are not included in the PyPI wheel.

## Included Example Bundle

`example_five_event_subset/` contains the five-event LA Basin tutorial bundle:
event metadata, 30 selected stations, GeoJSON regions, and ten original MiniSEED
files (five observed and five CVM-SI synthetic files, about 245 MB total).
These inputs retain all original samples and Z/R/T components; no fabricated
waveforms or previously processed copies are substituted. The existing five-event
subset is retained to preserve regional/corridor coverage and documented missing
station records. Step 1 generates the 1 Hz lowpass products under `outputs/`.

`metadata/waveform_manifest.json` lists every distributed waveform's byte count
and SHA-256. Run `python -c 'from spatial_vtk.tutorials import verify_waveforms;
verify_waveforms()'` from the source checkout before starting. Obtain the files
from the matching source checkout; no separately hosted bundle URL is required.
This repair is not available from public main until the maintainer publishes it.


`data_formats/` contains tiny preview inputs and outputs used by the Data
Formats page. These examples show file structure and column conventions; they
are not intended to be a complete scientific dataset.

## Scientific Sources

Observed records come from public southern California waveform sources:

- Southern California Seismic Network (SCSN), network code `CI`, DOI
  `10.7914/SN/CI`.
- Center for Engineering Strong Motion Data (CESMD).

Observed records were processed with `gmprocess` before being packaged for the
examples.

Synthetic records were generated with Salvus for a CVM-SI/CVM-S4.26.M01
southern California velocity-model context. UCVM and SCEC CVM-S4.26.M01 should
be cited when using the example synthetics or adapting the workflow to similar
southern California simulations.

Event metadata include public USGS event-page links where available. Station
coordinates and event-station tables are subset products derived from the
public waveform and metadata sources above.

## Geospatial Examples

The example GeoJSON files are small tutorial polygons for demonstrating
region-label joins, regional contrasts, and corridor/path selection. They are
included to teach Spatial-VTK workflows and should be replaced with your own
project regions for scientific analysis.

Map figures do not ship basemap rasters. Spatial-VTK downloads tiles through
`contextily` for static maps and through Folium/Leaflet tile providers for
dashboards. Static examples default to Esri World Imagery. Dashboard maps can
also use CARTO and OpenStreetMap tile layers. You need network access, or a
local tile cache, for basemap-backed maps.

## How to Cite

If you use these examples, cite Spatial-VTK and the data, model, processing,
simulation, and basemap sources that apply to your workflow. The root
`CITATION.cff` lists the package citation and the main software/data sources
used by the public examples.
