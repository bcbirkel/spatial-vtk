from __future__ import annotations

import ast
import importlib
import os
import pathlib
import re
import subprocess
import sys
import textwrap


def test_public_imports():
    import spatial_vtk
    from spatial_vtk.config import (
        NotebookFigureRenderGate,
        abbreviate_model,
        configured_output_registry_frame,
        display_output_table_previews,
        run_notebook_step_if_needed,
    )
    from spatial_vtk.metrics import (
        METRIC_NAMES,
        amplitude_spectrum,
        calculate_metrics_for_pairs,
        compute_metrics_pair,
        metric_batch_merge_readiness_from_config,
        metric_manifest_batch_status,
        metric_outputs_readiness_from_config,
        metric_slurm_submission_readiness,
        metric_slurm_submission_readiness_from_config,
    )
    from spatial_vtk.metrics.plot import MetricFigureContext
    from spatial_vtk.io import (
        load_configured_input_paths,
        load_configured_input_tables,
        OutputGroup,
        inspect_synthetic_format,
        output_group,
        prepare_metadata_tables_from_config,
        prepare_station_metadata,
        record_coverage_readiness_from_config,
        resolve_model_aliases,
    )
    from spatial_vtk.qc import load_trace_inventory_lookup, slurm_settings_from_config
    from spatial_vtk.qc.build import slurm_settings_from_config as build_slurm_settings_from_config
    from spatial_vtk.spatial import (
        annotate_points_with_geojson,
        build_station_edge_corridors,
        classify_paths_with_geojson,
        geojson_polygon_preview_table,
        run_boundary_corridor_workflow_from_config,
        run_geojson_region_summary_workflow_from_config,
        run_spatial_derived_outputs_workflow_from_config,
        run_spatial_statistics_workflow_from_config,
    )
    from spatial_vtk.visualize.dashboard import (
        build_dashboard_summaries,
        dashboard_readiness_summary_frame,
        launch_configured_metrics_dashboard,
        launch_configured_qc_dashboard,
        preview_dashboard_summary_tables,
    )
    from spatial_vtk.spatial.map import add_contextily_basemap, plot_corridor_map, plot_event_residual_map
    from spatial_vtk.visualize.context import plot_distance_amplitude_diagnostics, plot_station_event_context, plot_study_domain_map
    from spatial_vtk.visualize.record_sections import plot_observed_synthetic_record_section, plot_record_section

    assert spatial_vtk.__version__
    assert "C1" in METRIC_NAMES
    assert callable(NotebookFigureRenderGate)
    assert callable(abbreviate_model)
    assert callable(configured_output_registry_frame)
    assert callable(display_output_table_previews)
    assert callable(run_notebook_step_if_needed)
    assert callable(amplitude_spectrum)
    assert callable(calculate_metrics_for_pairs)
    assert callable(compute_metrics_pair)
    assert callable(metric_batch_merge_readiness_from_config)
    assert callable(metric_manifest_batch_status)
    assert callable(metric_outputs_readiness_from_config)
    assert callable(metric_slurm_submission_readiness)
    assert callable(metric_slurm_submission_readiness_from_config)
    assert callable(MetricFigureContext.from_frame)
    assert callable(inspect_synthetic_format)
    assert callable(load_configured_input_paths)
    assert callable(load_configured_input_tables)
    assert callable(output_group)
    assert callable(OutputGroup)
    assert callable(prepare_metadata_tables_from_config)
    assert callable(prepare_station_metadata)
    assert callable(record_coverage_readiness_from_config)
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
    assert callable(launch_configured_metrics_dashboard)
    assert callable(launch_configured_qc_dashboard)
    assert callable(preview_dashboard_summary_tables)
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


def test_public_package_entry_points_keep_optional_imports_lazy():
    """Package entry points should not import heavy plotting/QC modules on inspection."""

    root = pathlib.Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    code = textwrap.dedent(
        """
        import sys

        import spatial_vtk.qc
        import spatial_vtk.qc.build
        import spatial_vtk.visualize
        import spatial_vtk.visualize.qc
        import spatial_vtk.visualize.dashboard

        forbidden_after_package_import = {
            "spatial_vtk.qc.build.inventory",
            "spatial_vtk.visualize.figure_io",
            "spatial_vtk.visualize.qc.retention",
            "spatial_vtk.visualize.qc.samples",
            "spatial_vtk.visualize.dashboard.charts",
            "spatial_vtk.visualize.dashboard.maps",
            "spatial_vtk.visualize.dashboard.streamlit_metrics",
            "spatial_vtk.visualize.dashboard.streamlit_qc",
        }
        loaded = forbidden_after_package_import & set(sys.modules)
        if loaded:
            raise SystemExit(f"unexpected eager imports: {sorted(loaded)}")

        from spatial_vtk.qc import load_trace_inventory_lookup, slurm_settings_from_config
        from spatial_vtk.visualize import read_figure_sidecar_metadata, write_figure_row_sidecar
        from spatial_vtk.visualize.qc import load_trace_qc_summary
        from spatial_vtk.visualize.dashboard import dashboard_readiness_summary_frame, launch_configured_metrics_dashboard

        assert load_trace_inventory_lookup.__module__ == "spatial_vtk.qc.build.filtering"
        assert slurm_settings_from_config.__module__ == "spatial_vtk.qc.build.slurm"
        assert read_figure_sidecar_metadata.__module__ == "spatial_vtk.visualize.figure_sidecars"
        assert write_figure_row_sidecar.__module__ == "spatial_vtk.visualize.figure_sidecars"
        assert load_trace_qc_summary.__module__ == "spatial_vtk.visualize.qc.overview"
        assert dashboard_readiness_summary_frame.__module__ == "spatial_vtk.visualize.dashboard.contracts"
        assert launch_configured_metrics_dashboard.__module__ == "spatial_vtk.visualize.dashboard.launch"

        forbidden_after_light_import = {
            "spatial_vtk.qc.build.inventory",
            "spatial_vtk.visualize.figure_io",
            "spatial_vtk.visualize.qc.retention",
            "spatial_vtk.visualize.qc.samples",
            "spatial_vtk.visualize.dashboard.charts",
            "spatial_vtk.visualize.dashboard.maps",
            "spatial_vtk.visualize.dashboard.streamlit_metrics",
            "spatial_vtk.visualize.dashboard.streamlit_qc",
        }
        loaded = forbidden_after_light_import & set(sys.modules)
        if loaded:
            raise SystemExit(f"unexpected eager imports after light helpers: {sorted(loaded)}")
        """
    )
    subprocess.run([sys.executable, "-c", code], cwd=root, env=env, check=True)


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
    assert ".. automodule:: spatial_vtk.metrics.workflow.inventory\n" in text
    assert ".. automodule:: spatial_vtk.metrics.workflow.cache\n" in text
    assert "helpers from the stable ``spatial_vtk.metrics`` package entry" in text
    assert "from spatial_vtk.metrics.plot import (" in text
    assert ".. automodule:: spatial_vtk.metrics.plot\n" in text
    assert ".. autoclass:: spatial_vtk.metrics.plot.MetricFigureContext" in text
    assert ".. autofunction:: spatial_vtk.metrics.plot.prepare_large_run_metric_figure_context" in text
    assert "Public plotting helpers exposed by ``spatial_vtk.metrics.plot``" in text
    for helper in (
        "plot_band_score_distribution",
        "plot_period_score_distribution",
        "plot_psa_period_curve",
        "plot_residuals_vs_distance",
        "plot_phase_delay_vs_distance",
        "plot_vs30_scatter",
        "plot_model_metric_heatmap",
        "plot_example_metric_pairs",
    ):
        assert helper in text
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


def test_public_docs_avoid_plot_implementation_import_paths():
    root = pathlib.Path(__file__).resolve().parents[1]
    docs = list((root / "docs").rglob("*.rst")) + [root / "README.md"]
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in docs
        if "_build" not in path.parts
    )
    forbidden = (
        "spatial_vtk.metrics.plot.example_metric_plots",
        "spatial_vtk.metrics.plot.model_comparison",
        "spatial_vtk.metrics.plot.periods",
        "spatial_vtk.metrics.plot.site_terms",
        "spatial_vtk.metrics.plot.trends",
        "spatial_vtk.metrics.plot.large_run",
        "spatial_vtk.spatial.plot.large_run",
        "spatial_vtk.spatial.map.basemaps",
        "spatial_vtk.spatial.map.correlation",
        "spatial_vtk.spatial.map.geojson",
        "spatial_vtk.spatial.map.metrics",
        "spatial_vtk.spatial.map.path.corridors",
        "spatial_vtk.spatial.map.path.residuals",
        "spatial_vtk.spatial.map.pca",
    )
    for token in forbidden:
        assert token not in text


def test_config_api_docs_include_compute_helpers():
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "api" / "config.rst"
    text = docs.read_text(encoding="utf-8")

    assert "Compute and Slurm" in text
    assert ".. automodule:: spatial_vtk.config.compute\n" in text


def test_qc_api_docs_use_public_package_entry_point():
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "api" / "qc.rst"
    text = docs.read_text(encoding="utf-8")

    assert "Start with ``spatial_vtk.qc``" in text
    assert "Public helpers exposed by ``spatial_vtk.qc``" in text
    assert ".. automodule:: spatial_vtk.qc\n" in text
    for helper in (
        "run_qc_inventory_from_config",
        "write_qc_inventory_overlap_from_config",
        "run_qc_summary_workflow_from_config",
        "build_metric_pair_retention_table_from_qc_inventory",
        "build_event_station_pair_retention_table_from_qc_inventory",
        "build_post_qc_record_table_from_qc_inventory",
        "build_qc_drop_cause_table_from_qc_inventory",
        "export_manual_review_queue_from_qc_inventory",
        "filter_event_station_records_for_source_overlap",
        "load_trace_inventory_lookup",
    ):
        assert helper in text


def test_io_api_docs_use_public_workflow_helpers():
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "api" / "io.rst"
    text = docs.read_text(encoding="utf-8")

    assert "Start with ``spatial_vtk.io``" in text
    assert "Public helpers exposed by ``spatial_vtk.io``" in text
    assert ".. automodule:: spatial_vtk.io\n" in text
    for helper in (
        "output_group",
        "preprocessed_waveform_output_group",
        "output_readiness",
        "OutputReadiness",
        "load_configured_input_paths",
        "load_configured_input_tables",
        "prepare_metadata_tables_from_config",
        "preprocess_waveforms_from_config",
        "record_coverage_readiness_from_config",
        "build_record_coverage_from_config",
        "read_bounded_table",
        "preview_table",
        "write_output_table",
        "load_output_table",
    ):
        assert helper in text
    assert "instead of repeating output-path variables" in text
    assert "notebooks." in text


def test_metrics_package_reexports_workflow_surface():
    """Top-level metrics should expose the curated workflow API used by docs and CLI."""

    root = pathlib.Path(__file__).resolve().parents[1]
    workflow_tree = ast.parse((root / "src" / "spatial_vtk" / "metrics" / "workflow" / "__init__.py").read_text(encoding="utf-8"))
    metrics_tree = ast.parse((root / "src" / "spatial_vtk" / "metrics" / "__init__.py").read_text(encoding="utf-8"))

    def literal_items(tree: ast.Module, name: str) -> set[str]:
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == name:
                        if isinstance(node.value, (ast.List, ast.Set)):
                            return {str(elt.value) for elt in node.value.elts if isinstance(elt, ast.Constant)}
        return set()

    workflow_exports = literal_items(workflow_tree, "__all__")
    metrics_workflow_exports = literal_items(metrics_tree, "_WORKFLOW_EXPORTS")
    assert workflow_exports <= metrics_workflow_exports


def test_spatial_api_docs_use_public_plot_and_map_entry_points():
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "api" / "spatial.rst"
    text = docs.read_text(encoding="utf-8")
    assert ".. automodule:: spatial_vtk.spatial.calculate\n" in text
    assert "helpers from the stable ``spatial_vtk.spatial`` package entry" in text
    assert "Start with ``spatial_vtk.spatial`` for spatial-statistics" in text
    assert "from spatial_vtk.spatial import (" in text
    assert "run_spatial_statistics_workflow_from_config" in text
    assert "run_geojson_region_summary_workflow_from_config" in text
    assert "run_boundary_corridor_workflow_from_config" in text
    assert "Public helpers exposed by ``spatial_vtk.spatial``" in text
    for helper in (
        "run_spatial_derived_outputs_workflow_from_config",
        "spatial_statistics_settings_from_config",
        "build_path_table",
        "summarize_residuals_by_path_bin",
        "annotate_points_with_geojson",
        "classify_paths_with_geojson",
        "build_station_edge_corridors",
        "select_records_by_corridors",
    ):
        assert helper in text
    assert "from spatial_vtk.spatial.plot import (" in text
    assert "from spatial_vtk.spatial.map import (" in text
    assert ".. automodule:: spatial_vtk.spatial.plot\n" in text
    assert ".. automodule:: spatial_vtk.spatial.map\n" in text
    assert "Public helpers exposed by ``spatial_vtk.spatial.plot``" in text
    for helper in (
        "plot_correlogram",
        "plot_semivariogram",
        "plot_directional_correlogram",
        "plot_distance_correlation_by_metric",
        "plot_residual_correlation",
        "plot_block_holdout_scatter",
        "plot_cluster_solution_scores",
        "plot_cluster_feature_heatmap",
        "plot_geology_contrast",
        "plot_path_bin_summary",
        "plot_pca_explained_variance",
        "plot_pca_feature_loadings",
        "write_large_run_region_boxplot_from_outputs",
    ):
        assert helper in text
    assert "Public helpers exposed by ``spatial_vtk.spatial.map``" in text
    for helper in (
        "plot_station_metric_map",
        "plot_station_metric_map_by_period",
        "plot_metric_map_by_model",
        "plot_model_improvement_map",
        "plot_residual_grid",
        "plot_score_map",
        "plot_event_residual_map",
        "plot_corridor_map",
        "plot_geojson_polygons_map",
        "plot_station_bias_map",
        "plot_cluster_map",
        "plot_pca_mode_map",
        "plot_pca_summary",
    ):
        assert helper in text
    assert ".. autoclass:: spatial_vtk.spatial.plot.SpatialFigureContext" in text
    assert ".. autofunction:: spatial_vtk.spatial.plot.prepare_spatial_figure_context" in text
    assert ".. autofunction:: spatial_vtk.spatial.plot.write_large_run_region_boxplot_from_outputs" in text
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


def test_core_api_docs_show_stable_start_here_imports():
    """Major API pages should name the routine package-level import surfaces."""

    docs_root = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "api"
    expectations = {
        "io.rst": [
            "Start with ``spatial_vtk.io``",
            "from spatial_vtk.io import (",
            "output_group",
            "prepare_event_station_table",
            "preprocess_waveform_files",
            "record_coverage_readiness_from_config",
        ],
        "metrics.rst": [
            "Start with ``spatial_vtk.metrics``",
            "from spatial_vtk.metrics import (",
            "plan_metric_tasks_from_config",
            "metric_manifest_batch_status",
            "metric_slurm_submission_readiness",
            "metric_slurm_submission_readiness_from_config",
            "write_metric_outputs_from_config",
        ],
        "qc.rst": [
            "Start with ``spatial_vtk.qc``",
            "from spatial_vtk.qc import (",
            "run_qc_inventory_from_config",
            "write_qc_inventory_overlap_from_config",
            "run_qc_summary_workflow_from_config",
        ],
        "spatial.rst": [
            "Start with ``spatial_vtk.spatial``",
            "from spatial_vtk.spatial import (",
            "from spatial_vtk.spatial.plot import",
            "from spatial_vtk.spatial.map import",
        ],
    }
    for filename, snippets in expectations.items():
        text = (docs_root / filename).read_text(encoding="utf-8")
        for snippet in snippets:
            assert snippet in text, f"{filename} does not document {snippet!r}"


def test_spatial_package_docstring_describes_namespace_boundary():
    """The top-level spatial package should explain where plotting imports live."""

    source = (
        pathlib.Path(__file__).resolve().parents[1] / "src" / "spatial_vtk" / "spatial" / "__init__.py"
    ).read_text(encoding="utf-8")
    assert "stable import surface for spatial calculations" in source
    assert "spatial_vtk.spatial.plot" in source
    assert "spatial_vtk.spatial.map" in source


def test_visualize_api_docs_use_public_entry_points():
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "api" / "visualize.rst"
    text = docs.read_text(encoding="utf-8")
    assert "Public helpers exposed by ``spatial_vtk.visualize``" in text
    for helper in (
        "plot_station_event_beachball_map",
        "plot_retention_summary",
        "plot_event_station_retention_heatmap",
        "plot_observed_synthetic_record_section",
        "finish_figure_with_sidecar",
        "write_figure_row_sidecar",
        "figure_sidecar_status_frame",
        "write_configured_dashboard_datasets",
        "dashboard_readiness_summary_frame",
        "dashboard_output_status_frame",
        "preview_dashboard_summary_tables",
        "launch_configured_metrics_dashboard",
        "launch_configured_qc_dashboard",
    ):
        assert helper in text
    assert ".. automodule:: spatial_vtk.visualize.context\n" in text
    assert ".. automodule:: spatial_vtk.visualize.dashboard\n" in text
    assert ".. automodule:: spatial_vtk.visualize.qc\n" in text
    assert ".. automodule:: spatial_vtk.visualize.waveforms\n" in text
    assert "When a dashboard tab is blank or unexpectedly sparse" in text
    assert "from spatial_vtk.visualize.dashboard import (" in text
    assert "dashboard_output_status_frame" in text
    assert "dashboard_readiness_summary_frame" in text
    assert "dashboard_summary_table_contracts" in text
    assert "The readiness and status frames are intentionally small" in text
    assert "``artifact_label``" in text
    assert "``dashboard_tabs``" in text
    assert "``suggested_action``" in text
    assert "``required_columns`` / ``missing_columns`` / ``map_message``" in text
    assert "SVTK_METRICS_DASHBOARD_ROW_LIMIT" in text
    assert "Maximum row-level records" in text
    assert "SVTK_QC_DASHBOARD_MAX_ROWS" in text
    assert "Maximum trace-summary rows" in text
    assert "Public helpers exposed by ``spatial_vtk.visualize.dashboard``" in text
    for helper in (
        "dashboard_summary_table_contracts",
        "dashboard_summary_table_paths",
        "dashboard_metric_dataset_readiness_frame",
        "dashboard_qc_trace_readiness_frame",
        "load_dashboard_metric_dataset",
        "load_dashboard_summary_tables",
        "preview_dashboard_summary_tables",
        "filter_dashboard_metrics",
        "filter_qc_dashboard_rows",
    ):
        assert helper in text
    assert "Public sidecar helpers exposed by ``spatial_vtk.visualize``" in text
    for helper in (
        "layered_figure_rows",
        "sidecar_rows_for_write",
        "read_figure_sidecar_metadata",
        "figure_sidecar_dimension_counts",
    ):
        assert helper in text


def test_reference_docs_map_python_workflow_entry_points():
    """Docs should expose task-oriented Python workflow helpers for notebooks."""

    root = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference"
    index = (root / "index.rst").read_text(encoding="utf-8")
    python_api = (root / "python_api.rst").read_text(encoding="utf-8")
    workflows = (root / "python_workflows.rst").read_text(encoding="utf-8")
    normalized_workflows = " ".join(workflows.split())

    assert "python_workflows" in index
    assert ":doc:`python_workflows`" in python_api
    required_helpers = [
        "spatial_vtk.config.run_notebook_step_if_needed",
        "spatial_vtk.config.display_output_table_previews",
        "spatial_vtk.io.load_configured_input_paths",
        "spatial_vtk.io.load_configured_input_tables",
        "spatial_vtk.io.output_group",
        "spatial_vtk.io.prepare_metadata_tables_from_config",
        "spatial_vtk.io.preprocess_waveforms_from_config",
        "spatial_vtk.io.build_record_coverage_from_config",
        "spatial_vtk.qc.run_qc_inventory_from_config",
        "spatial_vtk.qc.write_qc_inventory_overlap_from_config",
        "spatial_vtk.qc.run_qc_summary_workflow_from_config",
        "spatial_vtk.metrics.build_metric_waveform_inventories_from_config",
        "spatial_vtk.metrics.plan_metric_tasks_from_config",
        "spatial_vtk.metrics.summarize_metric_snapshot_tasks_from_config",
        "spatial_vtk.metrics.metric_slurm_submission_readiness_from_config",
        "spatial_vtk.metrics.write_metrics_slurm_script_from_config",
        "spatial_vtk.metrics.merge_metric_batches_from_config",
        "spatial_vtk.metrics.write_metric_outputs_from_config",
        "spatial_vtk.spatial.run_spatial_statistics_workflow_from_config",
        "spatial_vtk.spatial.run_spatial_derived_outputs_workflow_from_config",
        "spatial_vtk.spatial.run_geojson_region_summary_workflow_from_config",
        "spatial_vtk.spatial.run_boundary_corridor_workflow_from_config",
        "spatial_vtk.visualize.dashboard.dashboard_readiness_summary_frame",
        "spatial_vtk.visualize.dashboard.preview_dashboard_summary_tables",
        "spatial_vtk.visualize.dashboard.write_configured_dashboard_datasets",
    ]
    for helper in required_helpers:
        assert helper in workflows
    assert "display_table_previews()" in workflows
    assert "display_first_existing_table_preview()" in workflows
    assert "run_notebook_step_if_needed" in workflows
    assert "notebooks should use package functions" in workflows.lower()
    assert "configured_output_registry_frame" in workflows
    assert "metric_manifest_path" in workflows
    assert "geojson_region_summaries_path" in workflows
    assert "descriptive keys are the public notebook contract" in workflows
    assert "docs should not depend on generic" in workflows
    assert "tutorial notebook preflight fails cells that pass compatibility strings" in workflows
    assert "imported callable ``run_qc_inventory_from_config``" in workflows
    assert "Preview dashboard summary tables without loading full tab inputs" in workflows
    assert "without resolving dashboard summary paths in cells" in normalized_workflows
    assert "compatibility aliases" not in workflows
    assert "from spatial_vtk.config import notebook_figure_settings" in workflows
    assert "from spatial_vtk.config.notebook import" not in workflows
    assert "Prefer direct attributes such as ``step_outputs.metrics_long_path``" in workflows
    assert "``bind()`` remains available for older notebooks" in workflows
    assert "bind(globals())" not in workflows
    assert "svtk metrics plan" not in workflows
    assert "svtk qc" not in workflows


def test_notebook_cli_compat_helper_is_not_top_level_config_api():
    """Notebook CLI wrappers should not be advertised as the standard config API."""

    root = pathlib.Path(__file__).resolve().parents[1]
    config_init = (root / "src" / "spatial_vtk" / "config" / "__init__.py").read_text(encoding="utf-8")
    notebook_helpers = (root / "src" / "spatial_vtk" / "config" / "notebook.py").read_text(encoding="utf-8")

    assert "run_or_submit_notebook_cli_command" not in config_init
    assert '"run_or_submit_notebook_cli_command"' not in notebook_helpers
    assert "run_or_submit_notebook_cli_command is deprecated for notebooks" in notebook_helpers
    assert "use run_notebook_step_if_needed with an importable package function" in notebook_helpers


def test_python_workflow_docs_reference_importable_entry_points():
    """Every documented workflow helper should resolve through its public module."""

    docs = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "python_workflows.rst"
    text = docs.read_text(encoding="utf-8")
    dotted_names = sorted(set(re.findall(r"``(spatial_vtk\.[A-Za-z0-9_\.]+)``", text)))
    assert dotted_names

    missing: list[str] = []
    for dotted_name in dotted_names:
        module_name, _, attribute_name = dotted_name.rpartition(".")
        if not module_name or not attribute_name:
            missing.append(dotted_name)
            continue
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:  # pragma: no cover - assertion message records the import failure.
            missing.append(f"{dotted_name} import failed: {exc}")
            continue
        if not hasattr(module, attribute_name):
            missing.append(dotted_name)

    assert not missing


def test_package_overview_points_to_public_workflow_helpers():
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs" / "package_overview.rst"
    text = docs.read_text(encoding="utf-8")

    required = [
        "Start with public helpers from ``spatial_vtk.io``",
        "``prepare_event_station_table``",
        "``preprocess_waveforms_from_config``",
        "``output_group`` and ``output_readiness``",
        "Start with public helpers from ``spatial_vtk.qc``",
        "``run_qc_inventory_from_config``",
        "``write_qc_inventory_overlap_from_config``",
        "Start with public helpers from ``spatial_vtk.metrics``",
        "``plan_metric_tasks_from_config``",
        "``summarize_metric_snapshot_tasks_from_config``",
        "``metric_manifest_batch_status`` and ``metric_slurm_submission_readiness``",
        "``write_metric_outputs_from_config``",
        "Start with public helpers from ``spatial_vtk.spatial``",
        "``run_spatial_statistics_workflow_from_config``",
        "``run_geojson_region_summary_workflow_from_config``",
        "``run_boundary_corridor_workflow_from_config``",
        "``spatial_vtk.spatial.plot`` and ``spatial_vtk.spatial.map``",
    ]
    for snippet in required:
        assert snippet in text

    forbidden = (
        "``io.metadata``",
        "``io.preprocessing``",
        "``qc.build``",
        "``metrics.workflow`` for",
        "``spatial.calculate``",
    )
    for snippet in forbidden:
        assert snippet not in text

    future = (docs.parent / "future_features.rst").read_text(encoding="utf-8")
    assert "public ``spatial_vtk.spatial`` GeoJSON and corridor" in future
    assert "helpers." in future
    assert "``spatial_vtk.spatial.calculate.geojson``" not in future
    assert "``spatial_vtk.spatial.calculate.corridors``" not in future


def test_notebook_helper_docs_prefer_readiness_wrapper():
    """API-facing docstrings should not steer notebooks to lower-level wrappers."""

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    notebook_helpers = (repo_root / "src" / "spatial_vtk" / "config" / "notebook.py").read_text(encoding="utf-8")
    metric_configured = (
        repo_root / "src" / "spatial_vtk" / "metrics" / "workflow" / "configured.py"
    ).read_text(encoding="utf-8")

    assert "New notebooks should" in notebook_helpers
    assert "prefer :func:`run_notebook_step_if_needed`" in notebook_helpers
    assert "This lower-level helper powers :func:`run_notebook_step_if_needed`" in notebook_helpers
    assert "Large-run notebooks use this helper" not in notebook_helpers
    assert "Large-run notebooks should pass these helpers to" in metric_configured
    assert "``run_notebook_step_if_needed()``" in metric_configured
    assert "through\n``run_or_submit_notebook_function()``" not in metric_configured


def test_spatial_plot_public_entry_point_is_lazy():
    import spatial_vtk.spatial.plot as spatial_plot

    assert "plot_correlogram" in spatial_plot.__all__
    assert "prepare_spatial_figure_context" in spatial_plot.__all__
    assert "write_large_run_region_boxplot_from_outputs" in spatial_plot.__all__
    assert callable(spatial_plot.plot_correlogram)
    assert callable(spatial_plot.prepare_spatial_figure_context)
    assert callable(spatial_plot.write_large_run_region_boxplot_from_outputs)
    assert spatial_plot.plot_correlogram is spatial_plot.plot_correlogram
