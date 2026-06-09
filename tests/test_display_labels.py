from __future__ import annotations

from spatial_vtk.config.labels import display_label


def test_display_label_preserves_common_spatial_acronyms():
    """Generic labels should stay readable for map and GeoJSON outputs."""

    assert display_label("station_geojson_region") == "Station GeoJSON Region"
    assert display_label("LA Basin") == "LA Basin"
    assert display_label("East LA") == "East LA"
    assert display_label("qc_status") == "QC Status"
    assert display_label("vs30") == "Vs30"
