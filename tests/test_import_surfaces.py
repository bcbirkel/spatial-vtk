from __future__ import annotations

import pathlib


def test_public_imports():
    import spatial_vtk
    from spatial_vtk.config import abbreviate_model, configured_output_registry_frame, run_notebook_step_if_needed
    from spatial_vtk.metrics import METRIC_NAMES, amplitude_spectrum, calculate_metrics_for_pairs, compute_metrics_pair
    from spatial_vtk.metrics.plot import MetricFigureContext
    from spatial_vtk.io import OutputGroup, inspect_synthetic_format, output_group, prepare_station_metadata, resolve_model_aliases
    from spatial_vtk.qc import load_trace_inventory_lookup, slurm_settings_from_config
    from spatial_vtk.qc.build import slurm_settings_from_config as build_slurm_settings_from_config
    from spatial_vtk.spatial import (
        run_boundary_corridor_workflow_from_config,
        run_geojson_region_summary_workflow_from_config,
        run_spatial_derived_outputs_workflow_from_config,
        run_spatial_statistics_workflow_from_config,
    )
    from spatial_vtk.spatial.calculate import annotate_points_with_geojson, build_station_edge_corridors, classify_paths_with_geojson, geojson_polygon_preview_table
    from spatial_vtk.visualize.dashboard import build_dashboard_summaries, dashboard_readiness_summary_frame
    from spatial_vtk.spatial.map import add_contextily_basemap, plot_corridor_map, plot_event_residual_map
    from spatial_vtk.visualize.context import plot_distance_amplitude_diagnostics, plot_station_event_context, plot_study_domain_map
    from spatial_vtk.visualize.record_sections import plot_observed_synthetic_record_section, plot_record_section

    assert spatial_vtk.__version__
    assert "C1" in METRIC_NAMES
    assert callable(abbreviate_model)
    assert callable(configured_output_registry_frame)
    assert callable(run_notebook_step_if_needed)
    assert callable(amplitude_spectrum)
    assert callable(calculate_metrics_for_pairs)
    assert callable(compute_metrics_pair)
    assert callable(MetricFigureContext.from_frame)
    assert callable(inspect_synthetic_format)
    assert callable(output_group)
    assert callable(OutputGroup)
    assert callable(prepare_station_metadata)
    assert callable(resolve_model_aliases)
    assert callable(load_trace_inventory_lookup)
    assert callable(slurm_settings_from_config)
    assert callable(build_slurm_settings_from_config)
    assert callable(run_boundary_corridor_workflow_from_config)
    assert callable(run_geojson_region_summary_workflow_from_config)
    assert callable(run_spatial_derived_outputs_workflow_from_config)
    assert callable(run_spatial_statistics_workflow_from_config)
    assert callable(annotate_points_with_geojson)
    assert callable(build_station_edge_corridors)
    assert callable(classify_paths_with_geojson)
    assert callable(geojson_polygon_preview_table)
    assert callable(build_dashboard_summaries)
    assert callable(dashboard_readiness_summary_frame)
    assert callable(add_contextily_basemap)
    assert callable(plot_corridor_map)
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
    assert 'requires-python = ">=3.10,<3.14"' in text
    assert '"ipykernel>=' in text
    assert '"gmprocess>=' in text


def test_metrics_api_docs_use_public_plot_entry_point():
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "api" / "metrics.rst"
    text = docs.read_text(encoding="utf-8")
    assert ".. automodule:: spatial_vtk.metrics.workflow\n" in text
    assert "from spatial_vtk.metrics.plot import (" in text
    assert ".. automodule:: spatial_vtk.metrics.plot\n" in text
    assert ".. autoclass:: spatial_vtk.metrics.plot.MetricFigureContext" in text
    assert ".. autofunction:: spatial_vtk.metrics.plot.prepare_large_run_metric_figure_context" in text
    assert "station_summary_for_item" in text
    assert "item_source_rows" in text
    forbidden = (
        "spatial_vtk.metrics.plot.example_metric_plots",
        "spatial_vtk.metrics.plot.model_comparison",
        "spatial_vtk.metrics.plot.periods",
        "spatial_vtk.metrics.plot.site_terms",
        "spatial_vtk.metrics.plot.trends",
        "spatial_vtk.metrics.plot.large_run",
    )
    for token in forbidden:
        assert token not in text


def test_spatial_api_docs_use_public_plot_and_map_entry_points():
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "api" / "spatial.rst"
    text = docs.read_text(encoding="utf-8")
    assert ".. automodule:: spatial_vtk.spatial.calculate\n" in text
    assert "from spatial_vtk.spatial.plot import (" in text
    assert "from spatial_vtk.spatial.map import (" in text
    assert ".. automodule:: spatial_vtk.spatial.plot\n" in text
    assert ".. automodule:: spatial_vtk.spatial.map\n" in text
    assert ".. autoclass:: spatial_vtk.spatial.plot.SpatialFigureContext" in text
    assert ".. autofunction:: spatial_vtk.spatial.plot.prepare_spatial_figure_context" in text
    assert "station_summary_for_item" in text
    assert "item_source_rows" in text
    forbidden = (
        "spatial_vtk.spatial.plot.correlation",
        "spatial_vtk.spatial.plot.large_run",
        "spatial_vtk.spatial.plot.metrics",
        "spatial_vtk.spatial.plot.pca",
        "spatial_vtk.spatial.map.basemaps",
        "spatial_vtk.spatial.map.correlation",
        "spatial_vtk.spatial.map.geojson",
        "spatial_vtk.spatial.map.metrics",
        "spatial_vtk.spatial.map.pca",
        "spatial_vtk.spatial.map.path.corridors",
        "spatial_vtk.spatial.map.path.residuals",
    )
    for token in forbidden:
        assert token not in text


def test_visualize_api_docs_use_public_entry_points():
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "api" / "visualize.rst"
    text = docs.read_text(encoding="utf-8")
    assert ".. automodule:: spatial_vtk.visualize.context\n" in text
    assert ".. automodule:: spatial_vtk.visualize.dashboard\n" in text
    assert ".. automodule:: spatial_vtk.visualize.qc\n" in text
    assert ".. automodule:: spatial_vtk.visualize.waveforms\n" in text


def test_reference_docs_map_python_workflow_entry_points():
    """Docs should expose task-oriented Python workflow helpers for notebooks."""

    root = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference"
    index = (root / "index.rst").read_text(encoding="utf-8")
    python_api = (root / "python_api.rst").read_text(encoding="utf-8")
    workflows = (root / "python_workflows.rst").read_text(encoding="utf-8")

    assert "python_workflows" in index
    assert ":doc:`python_workflows`" in python_api
    required_helpers = [
        "spatial_vtk.config.run_notebook_step_if_needed",
        "spatial_vtk.io.output_group",
        "spatial_vtk.io.preprocess_waveforms_from_config",
        "spatial_vtk.io.build_record_coverage_from_config",
        "spatial_vtk.qc.run_qc_inventory_from_config",
        "spatial_vtk.qc.write_qc_inventory_overlap_from_config",
        "spatial_vtk.qc.run_qc_summary_workflow_from_config",
        "spatial_vtk.metrics.build_metric_waveform_inventories_from_config",
        "spatial_vtk.metrics.plan_metric_tasks_from_config",
        "spatial_vtk.metrics.write_metrics_slurm_script_from_config",
        "spatial_vtk.metrics.merge_metric_batches_from_config",
        "spatial_vtk.metrics.write_metric_outputs_from_config",
        "spatial_vtk.spatial.run_spatial_statistics_workflow_from_config",
        "spatial_vtk.spatial.run_spatial_derived_outputs_workflow_from_config",
        "spatial_vtk.spatial.run_geojson_region_summary_workflow_from_config",
        "spatial_vtk.spatial.run_boundary_corridor_workflow_from_config",
        "spatial_vtk.visualize.dashboard.dashboard_readiness_summary_frame",
        "spatial_vtk.visualize.dashboard.write_configured_dashboard_datasets",
    ]
    for helper in required_helpers:
        assert helper in workflows
    assert "run_notebook_step_if_needed" in workflows
    assert "notebooks should use package functions" in workflows.lower()
    assert "configured_output_registry_frame" in workflows
    assert "metric_manifest_path" in workflows
    assert "geojson_region_summaries_path" in workflows
    assert "compatibility aliases" in workflows
    assert "svtk metrics plan" not in workflows
    assert "svtk qc" not in workflows


def test_spatial_plot_public_entry_point_is_lazy():
    import spatial_vtk.spatial.plot as spatial_plot

    assert "plot_correlogram" in spatial_plot.__all__
    assert "prepare_spatial_figure_context" in spatial_plot.__all__
    assert callable(spatial_plot.plot_correlogram)
    assert callable(spatial_plot.prepare_spatial_figure_context)
    assert spatial_plot.plot_correlogram is spatial_plot.plot_correlogram
