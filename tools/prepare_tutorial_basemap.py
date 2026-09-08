"""Cache Esri imagery covering the Southern California tutorial maps."""
import argparse
import hashlib
import json
from pathlib import Path
from spatial_vtk.spatial.map.basemaps import cache_contextily_basemap_raster, basemap_cache_path_for_extent

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cache-dir', type=Path, required=True)
args = parser.parse_args()
bounds = dict(west=-121.0, south=31.0, east=-114.0, north=37.0, zoom=8, cache_dir=args.cache_dir)
path = basemap_cache_path_for_extent(**bounds)
if not path.is_file():
    path = cache_contextily_basemap_raster(**bounds)
manifest = dict(provider='Esri.WorldImagery', extent=[-121, 31, -114, 37], zoom=8,
                raster=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
path.with_suffix('.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest))
