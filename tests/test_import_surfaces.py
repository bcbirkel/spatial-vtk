from __future__ import annotations

import pathlib


def test_public_imports():
    import spatial_vtk
    from spatial_vtk.config import abbreviate_model
    from spatial_vtk.metrics import METRIC_NAMES, amplitude_spectrum, calculate_metrics_for_pairs, compute_metrics_pair
    from spatial_vtk.io import inspect_synthetic_format, prepare_station_metadata, resolve_model_aliases
    from spatial_vtk.qc import load_trace_inventory_lookup
    from spatial_vtk.spatial.calculate import annotate_points_with_geojson, build_station_edge_corridors, classify_paths_with_geojson
    from spatial_vtk.visualize.dashboard import build_dashboard_summaries
    from spatial_vtk.spatial.map import add_contextily_basemap
    from spatial_vtk.spatial.map.path import plot_event_residual_map
    from spatial_vtk.visualize.context import plot_distance_amplitude_diagnostics, plot_station_event_context, plot_study_domain_map
    from spatial_vtk.visualize.record_sections import plot_observed_synthetic_record_section, plot_record_section

    assert spatial_vtk.__version__
    assert "C1" in METRIC_NAMES
    assert callable(abbreviate_model)
    assert callable(amplitude_spectrum)
    assert callable(calculate_metrics_for_pairs)
    assert callable(compute_metrics_pair)
    assert callable(inspect_synthetic_format)
    assert callable(prepare_station_metadata)
    assert callable(resolve_model_aliases)
    assert callable(load_trace_inventory_lookup)
    assert callable(annotate_points_with_geojson)
    assert callable(build_station_edge_corridors)
    assert callable(classify_paths_with_geojson)
    assert callable(build_dashboard_summaries)
    assert callable(add_contextily_basemap)
    assert callable(plot_event_residual_map)
    assert callable(plot_distance_amplitude_diagnostics)
    assert callable(plot_observed_synthetic_record_section)
    assert callable(plot_record_section)
    assert callable(plot_station_event_context)
    assert callable(plot_study_domain_map)


def test_public_package_discovery_excludes_legacy_namespace():
    pyproject = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    legacy_namespace = "validation" + "_toolkit"
    assert 'include = ["spatial_vtk*"]' in text
    assert legacy_namespace not in text
    assert not (pyproject.parent / "src" / legacy_namespace).exists()


def test_waveform_extra_includes_pickle_runtime_dependencies():
    pyproject = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    assert '"gmprocess>=' in text
