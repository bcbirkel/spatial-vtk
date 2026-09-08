"""Write observed/synthetic CLI metric inventories from Step 1 outputs."""
from spatial_vtk.config import SpatialVTKConfig
from spatial_vtk.io import load_output_table
from spatial_vtk.tutorials import CONFIG, build_metric_inventories, tutorial_root

root = tutorial_root()
cfg = SpatialVTKConfig.from_file(root / CONFIG, run_scenario='tutorial').activate()
for source, inventory in zip(('observed', 'synthetic'), build_metric_inventories(load_output_table('event_station_records'), config=cfg)):
    path = cfg.path('outputs.tables') / f'{source}_metric_inventory.csv'
    inventory.to_csv(path, index=False)
    print(path)
