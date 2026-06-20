from __future__ import annotations

import ast
import inspect
import importlib
import os
import pathlib
import re
import subprocess
import sys
import textwrap


def _first_list_table_after_marker(text: str, marker: str) -> str:
    """Return the first reStructuredText list table after a section marker."""

    rest = text.split(marker, 1)[1].split(".. list-table::", 1)[1]
    lines = [".. list-table::"] + rest.splitlines()
    table_lines: list[str] = []
    table_started = False
    for line in lines:
        if line.startswith(".. list-table::") or line.startswith("   ") or not line.strip():
            table_lines.append(line)
            table_started = True
        elif table_started:
            break
    return "\n".join(table_lines)


def _public_helper_names_from_list_table(table_text: str) -> set[str]:
    """Extract helper names from the first column of a docs list table."""

    names: set[str] = set()
    lines = table_text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if re.match(r"\s+\* - ``", line):
            cell = line
            index += 1
            while index < len(lines) and re.match(r"\s+``", lines[index]):
                cell += " " + lines[index].strip()
                index += 1
            for raw_name in re.findall(r"``([^`]+)``", cell):
                for part in re.split(r"\s+and\s+|,\s*", raw_name):
                    name = part.strip()
                    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
                        names.add(name)
        else:
            index += 1
    return names


def test_public_imports():
    import spatial_vtk
    from spatial_vtk.config import (
        NotebookFigureRenderGate,
        abbreviate_model,
        configured_output_registry_frame,
        configured_output_registry_preview_frame,
        display_output_table_previews,
        render_notebook_figure,
        run_notebook_step_if_needed,
    )
    from spatial_vtk.metrics import (
        METRIC_NAMES,
        StandardMetricWorkflowOutputResult,
        amplitude_spectrum,
        calculate_metrics_for_pairs,
        compute_metrics_pair,
        load_standard_metric_workflow_outputs,
        metric_batch_merge_readiness_from_config,
        metric_inventories_readiness_from_config,
        metric_manifest_readiness_from_config,
        metric_manifest_batch_status,
        metric_outputs_readiness_from_config,
        metric_slurm_submission_readiness,
        metric_slurm_submission_readiness_from_config,
    )
    from spatial_vtk.metrics.plot import (
        MetricFigureContext,
        MetricFigureSuiteResult,
        StandardMetricDiagnosticFigureResult,
        metric_plot_input_summary_frame,
        metric_rows_for_metrics,
        write_large_run_metric_figure_suite_from_notebook_settings,
        write_standard_metric_diagnostic_figures,
        write_station_metric_map_from_notebook_settings,
    )
    from spatial_vtk.io import (
        MetadataPreparationResult,
        RecordCoverageWorkflowResult,
        StandardIngestWorkflowOutputResult,
        WaveformPreprocessingSummaryResult,
        load_configured_input_paths,
        load_configured_input_tables,
        OutputGroup,
        event_display_label,
        event_ids_from_records,
        event_label_preview_frame,
        event_rows_for_records,
        first_nonempty_table_value,
        inspect_synthetic_format,
        load_standard_ingest_workflow_outputs,
        metadata_tables_readiness_from_config,
        output_group,
        prepare_metadata_tables_from_config,
        preprocessing_readiness_from_config,
        prepare_station_metadata,
        record_coverage_readiness_from_config,
        resolve_model_aliases,
    )
    from spatial_vtk.qc import (
        StandardQCInputResult,
        StandardQCWorkflowOutputResult,
        load_standard_qc_inputs,
        load_standard_qc_workflow_outputs,
        load_trace_inventory_lookup,
        qc_inventory_readiness_from_config,
        qc_overlap_readiness_from_config,
        qc_summary_readiness_from_config,
        slurm_settings_from_config,
    )
    from spatial_vtk.qc.build import slurm_settings_from_config as build_slurm_settings_from_config
    from spatial_vtk.spatial import (
        annotate_points_with_geojson,
        build_station_edge_corridors,
        classify_paths_with_geojson,
        corridor_record_pair_frame,
        corridor_record_preview_frame,
        event_station_records_matching_pairs,
        geojson_matched_record_frame,
        geojson_polygon_preview_table,
        geojson_metric_region_frame,
        geojson_metric_subset_frame,
        run_boundary_corridor_workflow_from_config,
        boundary_corridor_readiness_from_config,
        geojson_region_summary_readiness_from_config,
        load_standard_spatial_workflow_output_status,
        load_standard_spatial_workflow_outputs,
        run_geojson_region_summary_workflow_from_config,
        run_spatial_derived_outputs_workflow_from_config,
        run_spatial_statistics_workflow_from_config,
        spatial_derived_outputs_readiness_from_config,
        StandardSpatialProductSummaryResult,
        spatial_correlation_preview_frame,
        spatial_metric_product_frames,
        spatial_metric_product_summary_frame,
        spatial_metric_table_frame,
        spatial_pca_product_frames,
        spatial_summary_readiness_from_config,
        spatial_workflow_failure_frame,
        station_bias_preview_frame,
        StandardSpatialWorkflowOutputResult,
        StandardSpatialWorkflowOutputStatusResult,
        summarize_standard_spatial_products,
    )
    from spatial_vtk.visualize.dashboard import (
        DashboardDatasetPreparationResult,
        build_dashboard_summaries,
        dashboard_readiness_summary_frame,
        display_dashboard_preparation_result,
        launch_configured_dashboards_from_notebook_settings,
        launch_configured_metrics_dashboard,
        launch_configured_qc_dashboard,
        load_filtered_dashboard_summary_table,
        prepare_configured_dashboard_datasets_from_notebook_settings,
        preview_dashboard_summary_tables,
    )
    from spatial_vtk.spatial.map import add_contextily_basemap, plot_corridor_map, plot_event_residual_map
    from spatial_vtk.spatial.plot import (
        SpatialFigureSuiteResult,
        SpatialSummaryFigureResult,
        StandardAdditionalPlottingFigureResult,
        StandardAdditionalPlottingInputResult,
        StandardAdditionalPlottingOutputStatusResult,
        StandardGeoJSONCorridorFigureResult,
        StandardGeoJSONFigureResult,
        StandardGeoJSONPlottingInputResult,
        StandardGeoJSONWorkflowOutputStatusResult,
        StandardSpatialDiagnosticFigureResult,
        StandardSpatialMapFigureResult,
        load_standard_additional_plotting_output_status,
        load_standard_additional_plotting_inputs,
        load_standard_geojson_workflow_output_status,
        load_standard_geojson_plotting_inputs,
        prepare_spatial_figure_context_from_notebook_settings,
        write_standard_additional_plotting_figures,
        write_standard_geojson_corridor_figures,
        write_standard_geojson_region_figures,
        write_standard_spatial_diagnostic_figures,
        write_standard_spatial_map_figures,
        write_large_run_spatial_figure_suite_from_notebook_settings,
        write_large_run_spatial_summary_figures_from_outputs,
    )
    from spatial_vtk.visualize.context import plot_distance_amplitude_diagnostics, plot_station_event_context, plot_study_domain_map
    from spatial_vtk.visualize.record_sections import plot_observed_synthetic_record_section, plot_record_section

    assert spatial_vtk.__version__
    assert "C1" in METRIC_NAMES
    assert callable(NotebookFigureRenderGate)
    assert callable(SpatialFigureSuiteResult)
    assert callable(StandardAdditionalPlottingFigureResult)
    assert callable(StandardAdditionalPlottingInputResult)
    assert callable(StandardAdditionalPlottingOutputStatusResult)
    assert callable(load_standard_additional_plotting_output_status)
    assert callable(load_standard_additional_plotting_inputs)
    assert callable(write_standard_additional_plotting_figures)
    assert callable(StandardGeoJSONCorridorFigureResult)
    assert callable(write_standard_geojson_corridor_figures)
    assert callable(StandardGeoJSONFigureResult)
    assert callable(StandardGeoJSONPlottingInputResult)
    assert callable(StandardGeoJSONWorkflowOutputStatusResult)
    assert callable(load_standard_geojson_workflow_output_status)
    assert callable(load_standard_geojson_plotting_inputs)
    assert callable(write_standard_geojson_region_figures)
    assert callable(write_large_run_spatial_figure_suite_from_notebook_settings)
    assert callable(abbreviate_model)
    assert callable(configured_output_registry_frame)
    assert callable(configured_output_registry_preview_frame)
    assert callable(display_output_table_previews)
    assert callable(render_notebook_figure)
    assert callable(run_notebook_step_if_needed)
    assert callable(amplitude_spectrum)
    assert callable(calculate_metrics_for_pairs)
    assert callable(compute_metrics_pair)
    assert callable(StandardMetricWorkflowOutputResult)
    assert callable(load_standard_metric_workflow_outputs)
    assert callable(metric_batch_merge_readiness_from_config)
    assert callable(metric_manifest_batch_status)
    assert callable(metric_outputs_readiness_from_config)
    assert callable(metric_inventories_readiness_from_config)
    assert callable(metric_manifest_readiness_from_config)
    assert callable(metric_slurm_submission_readiness)
    assert callable(metric_slurm_submission_readiness_from_config)
    assert callable(MetricFigureContext.from_frame)
    assert callable(MetricFigureSuiteResult)
    assert callable(metric_plot_input_summary_frame)
    assert callable(metric_rows_for_metrics)
    assert callable(write_large_run_metric_figure_suite_from_notebook_settings)
    assert callable(StandardMetricDiagnosticFigureResult)
    assert callable(write_standard_metric_diagnostic_figures)
    assert callable(write_station_metric_map_from_notebook_settings)
    assert callable(inspect_synthetic_format)
    assert callable(StandardIngestWorkflowOutputResult)
    assert callable(MetadataPreparationResult)
    assert callable(RecordCoverageWorkflowResult)
    assert callable(WaveformPreprocessingSummaryResult)
    assert callable(load_configured_input_paths)
    assert callable(load_configured_input_tables)
    assert callable(load_standard_ingest_workflow_outputs)
    assert callable(metadata_tables_readiness_from_config)
    assert callable(event_display_label)
    assert callable(event_ids_from_records)
    assert callable(event_label_preview_frame)
    assert callable(event_rows_for_records)
    assert callable(first_nonempty_table_value)
    assert callable(output_group)
    assert callable(OutputGroup)
    assert callable(prepare_metadata_tables_from_config)
    assert callable(preprocessing_readiness_from_config)
    assert callable(prepare_station_metadata)
    assert callable(record_coverage_readiness_from_config)
    assert callable(resolve_model_aliases)
    assert callable(load_trace_inventory_lookup)
    assert callable(StandardQCInputResult)
    assert callable(StandardQCWorkflowOutputResult)
    assert callable(load_standard_qc_inputs)
    assert callable(load_standard_qc_workflow_outputs)
    assert callable(qc_inventory_readiness_from_config)
    assert callable(qc_overlap_readiness_from_config)
    assert callable(qc_summary_readiness_from_config)
    assert callable(slurm_settings_from_config)
    assert callable(build_slurm_settings_from_config)
    assert callable(run_boundary_corridor_workflow_from_config)
    assert callable(boundary_corridor_readiness_from_config)
    assert callable(geojson_region_summary_readiness_from_config)
    assert callable(load_standard_spatial_workflow_output_status)
    assert callable(load_standard_spatial_workflow_outputs)
    assert callable(run_geojson_region_summary_workflow_from_config)
    assert callable(run_spatial_derived_outputs_workflow_from_config)
    assert callable(run_spatial_statistics_workflow_from_config)
    assert callable(spatial_derived_outputs_readiness_from_config)
    assert callable(StandardSpatialProductSummaryResult)
    assert callable(StandardSpatialWorkflowOutputResult)
    assert callable(StandardSpatialWorkflowOutputStatusResult)
    assert callable(corridor_record_preview_frame)
    assert callable(corridor_record_pair_frame)
    assert callable(event_station_records_matching_pairs)
    assert callable(geojson_matched_record_frame)
    assert callable(spatial_correlation_preview_frame)
    assert callable(spatial_metric_product_frames)
    assert callable(spatial_metric_product_summary_frame)
    assert callable(spatial_metric_table_frame)
    assert callable(spatial_pca_product_frames)
    assert callable(spatial_summary_readiness_from_config)
    assert callable(spatial_workflow_failure_frame)
    assert callable(station_bias_preview_frame)
    assert callable(summarize_standard_spatial_products)
    assert callable(annotate_points_with_geojson)
    assert callable(build_station_edge_corridors)
    assert callable(classify_paths_with_geojson)
    assert callable(SpatialSummaryFigureResult)
    assert callable(StandardSpatialDiagnosticFigureResult)
    assert callable(StandardSpatialMapFigureResult)
    assert callable(prepare_spatial_figure_context_from_notebook_settings)
    assert callable(write_standard_spatial_diagnostic_figures)
    assert callable(write_standard_spatial_map_figures)
    assert callable(write_large_run_spatial_summary_figures_from_outputs)
    assert callable(geojson_polygon_preview_table)
    assert callable(geojson_metric_region_frame)
    assert callable(geojson_metric_subset_frame)
    assert inspect.isclass(DashboardDatasetPreparationResult)
    assert callable(build_dashboard_summaries)
    assert callable(dashboard_readiness_summary_frame)
    assert callable(launch_configured_dashboards_from_notebook_settings)
    assert callable(launch_configured_metrics_dashboard)
    assert callable(launch_configured_qc_dashboard)
    assert callable(load_filtered_dashboard_summary_table)
    assert callable(prepare_configured_dashboard_datasets_from_notebook_settings)
    assert callable(display_dashboard_preparation_result)
    assert callable(preview_dashboard_summary_tables)
    assert callable(add_contextily_basemap)
    assert callable(plot_corridor_map)
    assert callable(plot_event_residual_map)
    assert callable(plot_distance_amplitude_diagnostics)
    assert callable(plot_observed_synthetic_record_section)
    assert callable(plot_record_section)
    assert callable(plot_station_event_context)
    assert callable(plot_study_domain_map)


def test_cli_parser_builds_without_optional_runtime_dependencies():
    """CLI help/reference generation should not import pandas or PyYAML."""

    root = pathlib.Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "from spatial_vtk.cli import build_parser; build_parser(); print('ok')",
        ],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_public_package_discovery_excludes_legacy_namespace():
    pyproject = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    legacy_namespace = "validation" + "_toolkit"
    assert 'include = ["spatial_vtk*"]' in text
    assert legacy_namespace not in text
    assert not (pyproject.parent / "src" / legacy_namespace).exists()


def test_private_agent_plans_are_ignored_for_public_release():
    """Local agent notes and execplans should stay out of public commits."""

    root = pathlib.Path(__file__).resolve().parents[1]
    gitignore = (root / ".gitignore").read_text(encoding="utf-8")
    checklist = (root / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
    for snippet in (
        "AGENTS.md",
        ".agents/",
        ".codex/",
        "EXECPLAN.md",
        "execplan.md",
        "*_execplan.md",
    ):
        assert snippet in gitignore
        assert snippet in checklist


def test_release_checklist_exists_and_matches_public_validation_gates():
    """The public release checklist should name the current validation gates."""

    root = pathlib.Path(__file__).resolve().parents[1]
    checklist_path = root / "RELEASE_CHECKLIST.md"
    agents_path = root / "AGENTS.md"
    agents = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
    text = checklist_path.read_text(encoding="utf-8")

    if agents:
        assert "RELEASE_CHECKLIST.md" in agents
        for snippet in (
            'python -m pip install -e ".[validation,docs,dashboard,notebooks,waveforms]"',
            "python tools/execute_tutorial_notebooks.py --preflight-only --include-large-run",
            "python tools/execute_tutorial_notebooks.py --runtime-check-only --include-large-run",
        ):
            assert snippet in agents
        assert 'python -m pip install -e ".[validation,docs,dashboard,waveforms]"' not in agents
    for snippet in (
        'python -m pip install -e ".[validation,docs,dashboard,notebooks,waveforms]"',
        "python -m pytest -q",
        "PYTHONPYCACHEPREFIX=/tmp/svtk_pycache python -m compileall -q src tests",
        "PYTHONPATH=src python tools/generate_cli_reference.py --check",
        "python tools/execute_tutorial_notebooks.py --preflight-only --include-large-run",
        "python tools/execute_tutorial_notebooks.py --clean --include-large-run",
        "python -m sphinx -W -b html docs docs/_build/html",
        "python -m build --sdist --wheel",
        "python -m twine check dist/*",
        "svtk plot metrics list",
        "svtk map spatial list",
        "svtk dashboard status --help",
    ):
        assert snippet in text
    assert "/pro" + "ject" not in text
    assert "jvi" + "dale" not in text
    assert "CA" + "RC" not in text


def test_public_workflows_check_generated_cli_reference():
    """Public CI should fail when generated CLI reference pages are stale."""

    root = pathlib.Path(__file__).resolve().parents[1]
    workflows = {
        workflow_name: (root / ".github" / "workflows" / workflow_name).read_text(encoding="utf-8")
        for workflow_name in ("ci.yml", "docs.yml")
    }
    for text in workflows.values():
        assert "Check generated CLI reference" in text
        assert "PYTHONPATH=src python tools/generate_cli_reference.py --check" in text
        assert "git diff --exit-code docs/reference/cli docs/reference/cli_api.rst" not in text
    assert workflows["ci.yml"].count("Check generated CLI reference") >= 2
    assert "Build docs with warnings as errors" in workflows["ci.yml"]
    assert '      - "tools/generate_cli_reference.py"' in workflows["docs.yml"]


def test_cli_reference_generator_has_no_write_check_mode():
    """The CLI reference generator should support help and no-write checks."""

    root = pathlib.Path(__file__).resolve().parents[1]
    generator = (root / "tools" / "generate_cli_reference.py").read_text(encoding="utf-8")

    assert "arg_parser = argparse.ArgumentParser" in generator
    assert '"--check"' in generator
    assert "def _check_cli_reference" in generator
    assert "Check whether generated CLI reference files are current without rewriting them." in generator


def test_public_docs_avoid_private_paths_and_cluster_notes():
    """Published docs should not mention local machines or private run paths."""

    root = pathlib.Path(__file__).resolve().parents[1]
    public_paths = [
        root / "README.md",
        root / "RELEASE_CHECKLIST.md",
        *list((root / "docs").rglob("*.rst")),
        *list((root / "docs").rglob("*.md")),
    ]
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in public_paths
        if "_build" not in path.parts
    )
    forbidden = (
        "/pro" + "ject2",
        "jvi" + "dale",
        "CA" + "RC",
        "hpc" + ".usc",
        "on" + "demand",
        "/Users/",
    )
    matches = [token for token in forbidden if token in text]
    assert not matches, f"Public docs contain private/local tokens: {matches}"


def test_changelog_dated_sections_use_bulleted_entries():
    """Dated changelog sections should stay scannable as bullet lists."""

    changelog_path = pathlib.Path(__file__).resolve().parents[1] / "docs" / "changelog.rst"
    lines = changelog_path.read_text(encoding="utf-8").splitlines()
    date_heading = re.compile(r"^20\d{2}-\d{2}-\d{2}$")
    topic_bullet = re.compile(r"^- \*\*.+\*\* \*\(.+\)\*$")

    in_dated_section = False
    topic_open = False
    current_entry_has_detail_bullet = False
    previous_line_was_detail = False
    violations: list[str] = []
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if date_heading.match(stripped):
            if in_dated_section and topic_open and not current_entry_has_detail_bullet:
                violations.append(f"{line_number}: previous changelog entry has no detail bullets")
            in_dated_section = True
            topic_open = False
            current_entry_has_detail_bullet = False
            previous_line_was_detail = False
            continue
        if in_dated_section and stripped == "Future Work":
            if topic_open and not current_entry_has_detail_bullet:
                violations.append(f"{line_number}: previous changelog entry has no detail bullets")
            in_dated_section = False
            continue
        if set(stripped) <= {"-"}:
            continue
        if not in_dated_section:
            continue
        if line.startswith("- "):
            if topic_open and not current_entry_has_detail_bullet:
                violations.append(f"{line_number}: previous changelog entry has no detail bullets")
            if not topic_bullet.match(line):
                violations.append(
                    f"{line_number}: top-level changelog bullets must include a topic and status: {line}"
                )
            topic_open = True
            current_entry_has_detail_bullet = False
            previous_line_was_detail = False
            continue
        if line.startswith("  - "):
            current_entry_has_detail_bullet = True
            previous_line_was_detail = True
            continue
        if line.startswith("    ") and previous_line_was_detail:
            continue
        if line.startswith("  "):
            violations.append(f"{line_number}: changelog entry details must use nested bullets: {line}")
            previous_line_was_detail = False
            continue
        violations.append(f"{line_number}: {line}")
        previous_line_was_detail = False

    assert not violations, "Changelog dated entries must be bullets:\n" + "\n".join(violations)


def test_public_package_entry_points_keep_optional_imports_lazy():
    """Package entry points should not import heavy plotting/QC modules on inspection."""

    root = pathlib.Path(__file__).resolve().parents[1]
    launch_source = (root / "src" / "spatial_vtk" / "visualize" / "dashboard" / "launch.py").read_text(
        encoding="utf-8"
    )
    assert not re.search(r"^from spatial_vtk\.config\b", launch_source, re.MULTILINE)
    assert not re.search(r"^import spatial_vtk\.config\b", launch_source, re.MULTILINE)

    env = dict(os.environ)
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    code = textwrap.dedent(
        """
        import sys

        import spatial_vtk.config
        import spatial_vtk.qc
        import spatial_vtk.qc.build
        import spatial_vtk.io
        import spatial_vtk.metrics.workflow
        import spatial_vtk.spatial
        import spatial_vtk.spatial.calculate
        import spatial_vtk.spatial.map
        import spatial_vtk.spatial.plot
        import spatial_vtk.visualize
        import spatial_vtk.visualize.context
        import spatial_vtk.visualize.qc
        import spatial_vtk.visualize.dashboard
        import spatial_vtk.visualize.waveforms

        forbidden_after_package_import = {
            "pandas",
            "numpy",
            "yaml",
            "spatial_vtk.config.compute",
            "spatial_vtk.config.metrics",
            "spatial_vtk.config.notebook",
            "spatial_vtk.config.outputs",
            "spatial_vtk.config.runtime",
            "spatial_vtk.metrics.workflow.configured",
            "spatial_vtk.metrics.workflow.execution",
            "spatial_vtk.metrics.workflow.outputs",
            "spatial_vtk.metrics.workflow.tasks",
            "spatial_vtk.io.metadata",
            "spatial_vtk.io.preprocessing",
            "spatial_vtk.io.tables",
            "spatial_vtk.io.waveforms",
            "spatial_vtk.io.workflows",
            "spatial_vtk.qc.build.inventory",
            "spatial_vtk.spatial.calculate.workflow",
            "spatial_vtk.spatial.map.metrics",
            "spatial_vtk.spatial.plot.large_run",
            "spatial_vtk.visualize.context.figures",
            "spatial_vtk.visualize.context.maps",
            "spatial_vtk.visualize.figure_io",
            "spatial_vtk.visualize.qc.retention",
            "spatial_vtk.visualize.qc.samples",
            "spatial_vtk.visualize.dashboard.charts",
            "spatial_vtk.visualize.dashboard.maps",
            "spatial_vtk.visualize.dashboard.streamlit_metrics",
            "spatial_vtk.visualize.dashboard.streamlit_qc",
            "spatial_vtk.visualize.waveforms.comparison",
            "spatial_vtk.visualize.waveforms.overlays",
            "spatial_vtk.visualize.waveforms.radial_sections",
            "spatial_vtk.visualize.waveforms.record_sections",
            "spatial_vtk.visualize.waveforms.station_event",
        }
        loaded = forbidden_after_package_import & set(sys.modules)
        if loaded:
            raise SystemExit(f"unexpected eager imports: {sorted(loaded)}")

        from spatial_vtk.config import abbreviate_model, display_label, metric_display_name
        from spatial_vtk.qc import load_trace_inventory_lookup, slurm_settings_from_config
        from spatial_vtk.io import OutputGroup, output_status_rows
        from spatial_vtk.metrics import StandardMetricWorkflowOutputResult, load_standard_metric_workflow_outputs
        from spatial_vtk.spatial import run_spatial_statistics_workflow
        from spatial_vtk.spatial.calculate import load_standard_spatial_workflow_output_status
        from spatial_vtk.visualize import (
            dashboard_output_readiness,
            dashboard_output_status_frame,
            dashboard_readiness_summary_frame,
            display_dashboard_output_previews,
            display_dashboard_preparation_result,
            figure_sidecar_status_frame,
            launch_configured_dashboards_from_notebook_settings,
            preview_dashboard_summary_tables,
            read_figure_sidecar_metadata,
            write_figure_row_sidecar,
        )
        from spatial_vtk.visualize.qc import load_trace_qc_summary
        from spatial_vtk.visualize.dashboard import (
            dashboard_readiness_summary_frame as dashboard_package_readiness_summary_frame,
            launch_configured_metrics_dashboard,
        )

        assert abbreviate_model.__module__ == "spatial_vtk.config.naming"
        assert display_label.__module__ == "spatial_vtk.config.labels"
        assert metric_display_name.__module__ == "spatial_vtk.config.labels"
        assert display_label("log2_residual") == "log2(observed / synthetic)"
        assert StandardMetricWorkflowOutputResult.__module__ == "spatial_vtk.metrics.workflow.standard"
        assert load_standard_metric_workflow_outputs.__module__ == "spatial_vtk.metrics.workflow.standard"
        assert OutputGroup.__module__ == "spatial_vtk.io.output_paths"
        assert output_status_rows.__module__ == "spatial_vtk.io.output_paths"
        assert load_trace_inventory_lookup.__module__ == "spatial_vtk.qc.build.filtering"
        assert slurm_settings_from_config.__module__ == "spatial_vtk.qc.build.slurm"
        assert run_spatial_statistics_workflow.__module__ == "spatial_vtk.spatial.calculate.workflow"
        assert load_standard_spatial_workflow_output_status.__module__ == "spatial_vtk.spatial.calculate.workflow"
        assert read_figure_sidecar_metadata.__module__ == "spatial_vtk.visualize.figure_sidecars"
        assert write_figure_row_sidecar.__module__ == "spatial_vtk.visualize.figure_sidecars"
        assert figure_sidecar_status_frame.__module__ == "spatial_vtk.visualize.figure_sidecars"
        assert load_trace_qc_summary.__module__ == "spatial_vtk.visualize.qc.overview"
        assert dashboard_output_readiness.__module__ == "spatial_vtk.visualize.dashboard.contracts"
        assert dashboard_output_status_frame.__module__ == "spatial_vtk.visualize.dashboard.contracts"
        assert dashboard_readiness_summary_frame.__module__ == "spatial_vtk.visualize.dashboard.contracts"
        assert dashboard_package_readiness_summary_frame.__module__ == "spatial_vtk.visualize.dashboard.contracts"
        assert display_dashboard_output_previews.__module__ == "spatial_vtk.visualize.dashboard.contracts"
        assert display_dashboard_preparation_result.__module__ == "spatial_vtk.visualize.dashboard.export"
        assert launch_configured_dashboards_from_notebook_settings.__module__ == "spatial_vtk.visualize.dashboard.launch"
        assert launch_configured_metrics_dashboard.__module__ == "spatial_vtk.visualize.dashboard.launch"
        assert preview_dashboard_summary_tables.__module__ == "spatial_vtk.visualize.dashboard.contracts"
        assert callable(dashboard_output_readiness)
        assert callable(dashboard_output_status_frame)
        assert callable(dashboard_readiness_summary_frame)
        assert callable(dashboard_package_readiness_summary_frame)
        assert callable(display_dashboard_output_previews)
        assert callable(display_dashboard_preparation_result)
        assert callable(launch_configured_dashboards_from_notebook_settings)
        assert callable(preview_dashboard_summary_tables)
        assert "spatial_vtk.visualize.dashboard.contracts" not in sys.modules

        forbidden_after_light_import = {
            "pandas",
            "numpy",
            "yaml",
            "spatial_vtk.config.compute",
            "spatial_vtk.config.metrics",
            "spatial_vtk.config.notebook",
            "spatial_vtk.config.outputs",
            "spatial_vtk.config.runtime",
            "spatial_vtk.metrics.workflow.configured",
            "spatial_vtk.metrics.workflow.execution",
            "spatial_vtk.metrics.workflow.outputs",
            "spatial_vtk.metrics.workflow.tasks",
            "spatial_vtk.io.metadata",
            "spatial_vtk.io.preprocessing",
            "spatial_vtk.io.tables",
            "spatial_vtk.io.waveforms",
            "spatial_vtk.io.workflows",
            "spatial_vtk.qc.build.inventory",
            "spatial_vtk.spatial.map.metrics",
            "spatial_vtk.spatial.plot.large_run",
            "spatial_vtk.visualize.context.figures",
            "spatial_vtk.visualize.context.maps",
            "spatial_vtk.visualize.figure_io",
            "spatial_vtk.visualize.qc.retention",
            "spatial_vtk.visualize.qc.samples",
            "spatial_vtk.visualize.dashboard.charts",
            "spatial_vtk.visualize.dashboard.maps",
            "spatial_vtk.visualize.dashboard.streamlit_metrics",
            "spatial_vtk.visualize.dashboard.streamlit_qc",
            "spatial_vtk.visualize.waveforms.comparison",
            "spatial_vtk.visualize.waveforms.overlays",
            "spatial_vtk.visualize.waveforms.radial_sections",
            "spatial_vtk.visualize.waveforms.record_sections",
            "spatial_vtk.visualize.waveforms.station_event",
        }
        loaded = forbidden_after_light_import & set(sys.modules)
        if loaded:
            raise SystemExit(f"unexpected eager imports after light helpers: {sorted(loaded)}")
        """
    )
    subprocess.run([sys.executable, "-c", code], cwd=root, env=env, check=True)


def test_notebook_and_waveform_extras_include_runtime_dependencies():
    root = pathlib.Path(__file__).resolve().parents[1]
    pyproject = root / "pyproject.toml"
    environment = root / "svtk_environment.yaml"
    text = pyproject.read_text(encoding="utf-8")
    environment_text = environment.read_text(encoding="utf-8")
    assert 'requires-python = ">=3.10,<3.14"' in text
    assert '"ipykernel>=' in text
    assert '"ipython>=' in text
    assert '"nbclient>=' in text
    assert '"nbformat>=' in text
    assert '"gmprocess>=' in text
    for dependency in ("ipykernel", "ipython", "nbclient", "nbformat"):
        assert f"  - {dependency}" in environment_text


def test_dashboard_extra_names_dashboard_runtime_dependencies():
    """The advertised dashboard extra should not be empty package metadata."""

    root = pathlib.Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    dashboard_section = text.split("dashboard = [", maxsplit=1)[1].split("]", maxsplit=1)[0]

    for dependency in (
        '"branca>=',
        '"folium>=',
        '"plotly>=',
        '"streamlit>=',
        '"streamlit-folium>=',
    ):
        assert dependency in dashboard_section


def test_example_tutorial_scenario_uses_event_station_metric_overlap():
    """The public tutorial scenario should not plan metrics for event-only overlap."""

    root = pathlib.Path(__file__).resolve().parents[1]
    config_text = (root / "data" / "examples" / "configuration" / "example_spatial_vtk_config.yaml").read_text(
        encoding="utf-8"
    )
    tutorial_section = config_text.split("  tutorial:", maxsplit=1)[1].split("  quick_amplitude_check:", maxsplit=1)[0]

    assert "require_source_overlap: true" in tutorial_section
    assert "source_overlap_scope: event_station" in tutorial_section
    assert "source_overlap_scope: event\n" not in tutorial_section


def test_environment_file_covers_tutorial_runtime_modules():
    """The public conda environment should cover the notebook runtime surface."""

    root = pathlib.Path(__file__).resolve().parents[1]
    environment_text = (root / "svtk_environment.yaml").read_text(encoding="utf-8")
    conda_dependencies = (
        "branca",
        "contextily",
        "folium",
        "geopandas",
        "h5py",
        "ipykernel",
        "ipython",
        "matplotlib",
        "nbclient",
        "nbformat",
        "numpy",
        "obspy",
        "pandas",
        "plotly",
        "pyarrow",
        "pyproj",
        "pyyaml",
        "rasterio",
        "scikit-learn",
        "scipy",
        "shapely",
        "statsmodels",
        "streamlit",
    )
    pip_dependencies = (
        "gmprocess>=",
        "phasenet>=",
        "pyasdf>=",
        "streamlit-folium>=",
    )
    for dependency in conda_dependencies:
        assert f"  - {dependency}" in environment_text
    for dependency in pip_dependencies:
        assert f"      - {dependency}" in environment_text


def test_environment_file_covers_release_validation_tools():
    """The public conda environment should support documented local release checks."""

    root = pathlib.Path(__file__).resolve().parents[1]
    environment_text = (root / "svtk_environment.yaml").read_text(encoding="utf-8")
    checklist = (root / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

    assert "python -m pytest -q" in checklist
    assert "python -m build --sdist --wheel" in checklist
    assert "python -m twine check dist/*" in checklist
    for dependency in ("build", "coverage", "pytest", "twine"):
        assert f"  - {dependency}" in environment_text or f"      - {dependency}" in environment_text


def test_autodoc_fallback_parameter_docs_are_descriptive():
    """Generated API docs should not fall back to placeholder parameter text."""

    root = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("svtk_docs_conf", root / "docs" / "conf.py")
    assert spec is not None
    conf = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(conf)

    def parameter(name: str, default: object = inspect.Signature.empty) -> inspect.Parameter:
        return inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD, default=default)

    assert conf._parameter_description(parameter("input_path")).startswith("Path to the input table, file, or configured path artifact")
    assert conf._parameter_description(parameter("output")).startswith("Output table, figure, manifest, or configured artifact")
    assert conf._parameter_description(parameter("summary")).startswith("Summary table, dashboard summary dataset")
    assert conf._parameter_description(parameter("metrics_dataset_dir")).startswith("Metrics dashboard row dataset directory")
    assert "direct ``metrics_long`` CSV/parquet table" in conf._parameter_description(parameter("metrics_dataset_dir"))
    assert conf._parameter_description(parameter("metrics_root")).startswith("Backward-compatible alias for ``metrics_dataset_dir``")
    assert "Prefer ``metrics_dataset_dir``" in conf._parameter_description(parameter("metrics_root"))
    assert conf._parameter_description(parameter("dashboard_summary_table_dir")).startswith("Dashboard summary-table directory")
    assert "``model_metric_band``" in conf._parameter_description(parameter("dashboard_summary_table_dir"))
    assert conf._parameter_description(parameter("summary_root")).startswith(
        "Backward-compatible alias for ``dashboard_summary_table_dir``"
    )
    assert "Prefer ``dashboard_summary_table_dir``" in conf._parameter_description(parameter("summary_root"))
    assert conf._parameter_description(parameter("qc_trace_summary_table")).startswith("QC trace-summary CSV/parquet table")
    assert "``qc_trace_summary``" in conf._parameter_description(parameter("qc_trace_summary_table"))
    assert conf._parameter_description(parameter("trace_summary")).startswith(
        "Backward-compatible alias for ``qc_trace_summary_table``"
    )
    assert "Prefer ``qc_trace_summary_table``" in conf._parameter_description(parameter("trace_summary"))
    assert conf._parameter_description(parameter("dataset_root")).startswith("Directory root or configured output root")
    assert conf._parameter_description(parameter("batch_manifest")).startswith("Manifest value used to plan, resume, or merge workflow work units")
    assert conf._parameter_description(parameter("config_path")).startswith("Path to the Spatial-VTK YAML")
    assert conf._parameter_description(parameter("sidecar_rows", default=100)).endswith("Defaults to ``100``.")
    assert "Required function argument" not in conf._parameter_description(parameter("sample_size"))
    assert "Optional function argument" not in conf._parameter_description(parameter("sample_size", default=10))


def test_autodoc_module_labels_use_public_entry_points():
    """Generated API headings should not special-case implementation modules."""

    root = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("svtk_docs_conf", root / "docs" / "conf.py")
    assert spec is not None
    conf = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(conf)

    for module_name in conf._MODULE_LABELS:
        assert module_name not in {
            "spatial_vtk.metrics.calculate.gof",
            "spatial_vtk.spatial.calculate.geojson",
            "spatial_vtk.spatial.calculate.pca",
            "spatial_vtk.spatial.map.geojson",
            "spatial_vtk.spatial.map.pca",
            "spatial_vtk.spatial.plot.pca",
            "spatial_vtk.visualize.qc.overview",
        }
    assert conf._module_doc_label("spatial_vtk.metrics.calculate") == "Metric Calculations"
    assert conf._module_doc_label("spatial_vtk.spatial.calculate") == "Spatial Calculations"
    assert conf._module_doc_label("spatial_vtk.spatial.map") == "Spatial Maps"
    assert conf._module_doc_label("spatial_vtk.spatial.plot") == "Spatial Plots"
    assert conf._module_doc_label("spatial_vtk.visualize.qc") == "QC Visualization"


def test_io_workflow_uses_public_context_visualization_entry_point():
    """Notebook-facing I/O workflows should call public visualization helpers."""

    workflows = pathlib.Path(__file__).resolve().parents[1] / "src" / "spatial_vtk" / "io" / "workflows.py"
    text = workflows.read_text(encoding="utf-8")
    assert "from spatial_vtk.visualize.context import build_record_coverage_table_from_trace_metadata" in text
    assert "from spatial_vtk.visualize.context.figures import build_record_coverage_table_from_trace_metadata" not in text
    assert "ingest_outputs = load_standard_ingest_workflow_outputs(cfg=cfg)" in text
    assert "preprocessed_waveform_metadata_paths(config=cfg)" not in text


def test_metrics_api_docs_use_public_plot_entry_point():
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "api" / "metrics.rst"
    text = docs.read_text(encoding="utf-8")
    assert ".. automodule:: spatial_vtk.metrics.calculate\n" in text
    assert ".. automodule:: spatial_vtk.metrics.workflow\n" in text
    assert "helpers from the stable ``spatial_vtk.metrics`` package entry" in text
    assert "lower-level calculation modules are implementation" in text
    assert "lower-level workflow modules are implementation" in text
    assert "Public workflow helpers exposed by ``spatial_vtk.metrics``" in text
    assert text.index("load_standard_metric_workflow_outputs") < text.index("plan_metric_tasks_from_config")
    workflow_table = text.split("Public workflow helpers exposed by ``spatial_vtk.metrics``", 1)[1].split(
        "``PSA`` and ``FAS``",
        1,
    )[0]
    assert workflow_table.index("``load_standard_metric_workflow_outputs``") < workflow_table.index(
        "``build_metric_waveform_inventories_from_config``"
    )
    for helper in (
        "build_metric_waveform_inventories_from_config",
        "metric_inventories_readiness_from_config",
        "plan_metric_tasks_from_config",
        "metric_manifest_readiness_from_config",
        "cache_metric_manifest_waveforms",
        "load_standard_metric_workflow_outputs",
        "metric_slurm_submission_readiness_from_config",
        "write_metrics_slurm_script_from_config",
        "read_task_manifest",
        "run_manifest_batch",
        "metric_manifest_batch_status",
        "metric_batch_merge_readiness_from_config",
        "merge_batch_outputs",
        "merge_metric_batches_from_config",
        "write_metric_outputs_from_config",
    ):
        assert f"``{helper}``" in text
    assert "from spatial_vtk.metrics.plot import (" in text
    import_block = text.split("from spatial_vtk.metrics.plot import (", 1)[1].split(")", 1)[0]
    assert "write_large_run_metric_figure_suite_from_notebook_settings," in import_block
    assert "write_standard_metric_diagnostic_figures," in import_block
    assert "metric_rows_for_metrics," not in import_block
    assert ".. automodule:: spatial_vtk.metrics.plot\n" in text
    assert ".. autoclass:: spatial_vtk.metrics.plot.MetricFigureContext" in text
    assert ".. autoclass:: spatial_vtk.metrics.plot.MetricFigureSuiteResult" in text
    assert ".. autoclass:: spatial_vtk.metrics.plot.StandardMetricDiagnosticFigureResult" in text
    assert ".. autoclass:: spatial_vtk.metrics.plot.StationMetricMapResult" in text
    assert ".. autofunction:: spatial_vtk.metrics.plot.metric_plot_input_summary_frame" in text
    assert ".. autofunction:: spatial_vtk.metrics.plot.metric_rows_for_metrics" in text
    assert ".. autofunction:: spatial_vtk.metrics.plot.prepare_large_run_metric_figure_context" in text
    assert ".. autofunction:: spatial_vtk.metrics.plot.write_large_run_metric_figure_suite_from_notebook_settings" in text
    assert ".. autofunction:: spatial_vtk.metrics.plot.write_standard_metric_diagnostic_figures" in text
    assert ".. autofunction:: spatial_vtk.metrics.plot.write_station_metric_map_from_notebook_settings" in text
    assert "Public plotting helpers exposed by ``spatial_vtk.metrics.plot``" in text
    helper_table = text.split("Public plotting helpers exposed by ``spatial_vtk.metrics.plot``", 1)[1].split(
        "Large-Run Figure Suite",
        1,
    )[0]
    assert "metric_rows_for_metrics" not in helper_table
    assert "Notebook-facing metric plotting should use the result-object and suite helpers" in text
    assert "Advanced Figure Extension Helpers" in text
    assert "not the preferred tutorial or notebook entry points" in text
    assert "``PSA`` and ``FAS`` are broadband spectral metrics" in text
    assert "writes blank\n``passband`` values for spectral tasks" in text
    assert "older output table contains PSA rows repeated under passband labels" in text
    assert ".. autoclass:: spatial_vtk.metrics.StandardMetricWorkflowOutputResult" in text
    assert ".. autofunction:: spatial_vtk.metrics.load_standard_metric_workflow_outputs" in text
    assert ".. autoclass:: spatial_vtk.metrics.workflow.StandardMetricWorkflowOutputResult" not in text
    assert ".. autofunction:: spatial_vtk.metrics.workflow.load_standard_metric_workflow_outputs" not in text
    assert "bounded preview helpers such as" in text
    assert "metrics_long`` display helper" in text
    assert "New\nnotebooks should call ``write_large_run_metric_figure_suite_from_notebook_settings``" in text
    forbidden_modules = (
        "spatial_vtk.metrics.calculate.amplitudes",
        "spatial_vtk.metrics.calculate.arrival_picks",
        "spatial_vtk.metrics.calculate.bands",
        "spatial_vtk.metrics.calculate.batch",
        "spatial_vtk.metrics.calculate.enrich",
        "spatial_vtk.metrics.calculate.gof",
        "spatial_vtk.metrics.calculate.phasenet_adapter",
        "spatial_vtk.metrics.calculate.records",
        "spatial_vtk.metrics.calculate.spectra",
        "spatial_vtk.metrics.calculate.summaries",
        "spatial_vtk.metrics.calculate.transforms",
        "spatial_vtk.metrics.calculate.waveforms",
        "spatial_vtk.metrics.workflow.configured",
        "spatial_vtk.metrics.workflow.inventory",
        "spatial_vtk.metrics.workflow.cache",
        "spatial_vtk.metrics.workflow.execution",
        "spatial_vtk.metrics.workflow.outputs",
        "spatial_vtk.metrics.workflow.run",
        "spatial_vtk.metrics.workflow.slurm",
        "spatial_vtk.metrics.workflow.tasks",
    )
    for module_name in forbidden_modules:
        assert f".. automodule:: {module_name}" not in text
    assert "For PSA, large-run figure helpers compare oscillator periods instead of\nwaveform passbands" in text
    assert "``status_frame``\n   also includes ``spectral_contract_status``" in text
    assert "``spectral_metric_contract_status``" in text
    assert "legacy passband-scoped row counts" in text
    assert "``write_station_metric_map_for_metric``" in text
    assert "``write_station_metric_map_from_notebook_settings``" in text
    assert "``write_standard_metric_diagnostic_figures``" in text
    assert "``write_large_run_metric_figure_suite_from_notebook_settings``" in text
    assert "exact ``figure_paths`` lists" in text
    assert "do not parse preview strings" in text
    assert "without notebook-local plot-function imports" in text
    assert "``StationMetricMapResult.status_frame()`` includes the" in text
    assert "``resolved_path`` row for the rendered figure" in text
    assert "preserving\n   ``output_path`` for compatibility" in text
    assert "source-row role/filter" in text
    assert "without hand-filtering\n   dataframes in the notebook" in text
    for helper in (
        "plot_band_score_distribution",
        "plot_period_score_distribution",
        "plot_psa_period_curve",
        "metric_rows_for_metrics",
        "write_standard_metric_diagnostic_figures",
        "write_large_run_metric_figure_suite_from_notebook_settings",
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


def test_metrics_api_docs_workflow_helpers_resolve_from_public_surface():
    """Workflow helpers documented for notebooks should import from spatial_vtk.metrics."""

    import spatial_vtk.metrics as metrics

    helpers = (
        "build_metric_waveform_inventories_from_config",
        "metric_inventories_readiness_from_config",
        "plan_metric_tasks_from_config",
        "metric_manifest_readiness_from_config",
        "cache_metric_manifest_waveforms",
        "metric_slurm_submission_readiness_from_config",
        "write_metrics_slurm_script_from_config",
        "read_task_manifest",
        "run_manifest_batch",
        "metric_manifest_batch_status",
        "metric_batch_merge_readiness_from_config",
        "merge_batch_outputs",
        "merge_metric_batches_from_config",
        "write_metric_outputs_from_config",
    )
    for helper in helpers:
        assert callable(getattr(metrics, helper))


def test_public_docs_avoid_plot_implementation_import_paths():
    root = pathlib.Path(__file__).resolve().parents[1]
    docs = list((root / "docs").rglob("*.rst")) + list((root / "docs").rglob("*.md")) + [root / "README.md"]
    notebooks = list((root / "docs" / "examples").rglob("*.ipynb"))
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [*docs, *notebooks]
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
    assert "Start routine notebooks from ``spatial_vtk.config`` helpers" in text
    assert "notebooks should avoid reaching into it directly" in text
    assert "Use ``spatial_vtk.config`` and ``spatial_vtk.io`` output groups" in text
    assert "lower-level registry and resolver APIs for scripts, CLIs, and helper\nimplementation code" in text
    assert "Import notebook helpers from ``spatial_vtk.config``" in text
    assert "``NotebookRunContext`` and ``notebook_run_context``" in text
    assert "``run_notebook_step_if_needed``" in text
    assert "``NotebookFigureSettings`` and ``notebook_figure_settings``" in text
    assert "``render_notebook_figure``" in text
    assert "``NotebookFigureSidecarSettings`` and" in text
    assert "``readiness_frame()`` reports whether sidecars are enabled" in text
    assert "``status_frame()`` reports per-figure provenance" in text
    assert "``NotebookDashboardCommands`` and" in text
    assert "``notebook_dashboard_launch_commands``" in text
    assert "``metrics_dataset_dir``" in text
    assert "``dashboard_summary_table_dir``" in text
    assert "``qc_trace_summary_table``" in text
    assert "``display_output_table_previews``" in text
    assert ".. automodule:: spatial_vtk.config.notebook" not in text


def test_io_api_docs_distinguish_public_entry_point_from_implementation_modules():
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "api" / "io.rst"
    text = docs.read_text(encoding="utf-8")

    assert "Start with ``spatial_vtk.io`` in notebooks and scripts" in text
    assert "documented for API completeness and advanced scripts" in text
    assert "implementation\norganization for tutorial notebooks" in text
    assert "Routine notebooks should start with standard workflow result loaders" in text
    assert "Use ``output_group()`` only\nwhen no standard workflow result helper exists" in text
    assert "not as notebook path-plumbing examples" in text
    assert ".. automodule:: spatial_vtk.io.metadata\n" in text
    assert ".. automodule:: spatial_vtk.io.preprocessing\n" in text
    assert ".. automodule:: spatial_vtk.io.tables\n" in text


def test_notebook_helper_docstring_prefers_public_config_import():
    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "spatial_vtk"
        / "config"
        / "notebook.py"
    )
    text = source.read_text(encoding="utf-8")

    assert "from spatial_vtk.config import register_svtk_cell_timer" in text
    assert "from spatial_vtk.config.notebook import register_svtk_cell_timer" not in text


def test_output_registry_docstring_prefers_standard_workflow_outputs_for_notebooks():
    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "spatial_vtk"
        / "config"
        / "outputs.py"
    )
    text = source.read_text(encoding="utf-8")

    assert "from spatial_vtk.io import load_standard_ingest_workflow_outputs" in text
    assert "result = load_standard_ingest_workflow_outputs()" in text
    assert "Use ``output_group()`` for reusable helpers" in text
    assert 'step_outputs = output_group("step_01_ingest")' not in text
    assert "Use ``resolve_output_path()`` directly for scripts or single-artifact helpers" in text
    assert "Use ``resolve_output_path()`` directly for lower-level helpers" not in text
    assert 'path = resolve_output_path("record_coverage", kind="figure")' not in text


def test_metric_workflow_docstrings_prefer_standard_step3_output_helper():
    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "spatial_vtk" / "metrics" / "workflow"
    workflow_text = (root / "__init__.py").read_text(encoding="utf-8")
    execution_text = (root / "execution.py").read_text(encoding="utf-8")

    assert "from spatial_vtk.metrics import load_standard_metric_workflow_outputs" in workflow_text
    assert "metric_outputs = load_standard_metric_workflow_outputs(cfg=cfg)" in workflow_text
    assert "result = metric_outputs.run_manifest_step_if_needed(context=context)" in workflow_text
    assert "advanced scripts that intentionally build custom inventories" in workflow_text
    assert "tasks = plan_metric_tasks(observed_inventory, synthetic_inventory, plan=metric_plan)" not in workflow_text

    assert "submission = metric_outputs.run_slurm_step_if_needed(context=context)" in execution_text
    assert "only in advanced scripts that own\ntheir task table directly" in execution_text


def test_preprocessing_docstring_prefers_standard_step1_output_helper():
    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "spatial_vtk"
        / "io"
        / "preprocessing.py"
    )
    text = source.read_text(encoding="utf-8")

    assert "from spatial_vtk.io import load_standard_ingest_workflow_outputs" in text
    assert "ingest_outputs = load_standard_ingest_workflow_outputs(cfg=cfg)" in text
    assert "result = ingest_outputs.run_preprocessing_step_if_needed(context=context)" in text
    assert "only in advanced scripts that\nalready own the event-station records" in text
    assert 'preprocess_waveform_files("event_stations.csv", "outputs/preprocessed", config=cfg)' not in text


def test_master_list_docstring_prefers_standard_step1_metadata_helper():
    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "spatial_vtk"
        / "io"
        / "master_lists.py"
    )
    text = source.read_text(encoding="utf-8")

    assert "from spatial_vtk.io import load_standard_ingest_workflow_outputs" in text
    assert "ingest_outputs = load_standard_ingest_workflow_outputs(cfg=cfg)" in text
    assert "result = ingest_outputs.run_metadata_step_if_needed(context=context)" in text
    assert "only in advanced scripts that already own in-memory station or event tables" in text
    assert 'pd.read_csv("stations.csv")' not in text
    assert 'pd.read_csv("events.csv")' not in text


def test_spatial_workflow_docstring_prefers_standard_step4_status_helper():
    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "spatial_vtk"
        / "spatial"
        / "calculate"
        / "workflow.py"
    )
    text = source.read_text(encoding="utf-8")

    assert "from spatial_vtk.spatial import load_standard_spatial_workflow_output_status" in text
    assert "spatial_outputs = load_standard_spatial_workflow_output_status(cfg=cfg)" in text
    assert "result = spatial_outputs.run_summary_step_if_needed(context=context)" in text
    assert "only in advanced scripts\nthat intentionally own a custom output directory" in text
    assert 'spatial_statistics_output_paths("outputs/tutorials/step_04")' not in text


def test_plot_package_docstrings_prefer_large_run_suite_helpers():
    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "spatial_vtk"
    metric_text = (root / "metrics" / "plot" / "__init__.py").read_text(encoding="utf-8")
    spatial_text = (root / "spatial" / "plot" / "__init__.py").read_text(encoding="utf-8")

    assert "write_large_run_metric_figure_suite_from_notebook_settings" in metric_text
    assert "result = write_large_run_metric_figure_suite_from_notebook_settings(metrics_long_path, settings)" in metric_text
    assert "Use individual functions such as ``plot_psa_period_curve()`` directly only" in metric_text
    assert "Plot PSA residuals by period" not in metric_text

    assert "write_large_run_spatial_figure_suite_from_notebook_settings" in spatial_text
    assert "result = write_large_run_spatial_figure_suite_from_notebook_settings(settings)" in spatial_text
    assert "Use individual functions such as ``plot_correlogram()`` directly only" in spatial_text
    assert "Create a spatial correlation plot" not in spatial_text


def test_context_map_docstring_prefers_standard_step1_context_figures():
    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "spatial_vtk"
        / "visualize"
        / "context"
        / "maps.py"
    )
    text = source.read_text(encoding="utf-8")

    assert "from spatial_vtk.io import load_standard_ingest_workflow_outputs" in text
    assert "ingest_outputs = load_standard_ingest_workflow_outputs(cfg=cfg)" in text
    assert "result = ingest_outputs.write_context_figures(settings, cfg=cfg)" in text
    assert "Use individual map functions such as ``plot_event_magnitude_map()`` directly" in text
    assert 'plot_event_magnitude_map(events, "event_magnitudes.png")' not in text


def test_figure_io_docstring_prefers_configured_output_key():
    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "spatial_vtk"
        / "visualize"
        / "figure_io.py"
    )
    text = source.read_text(encoding="utf-8")

    assert 'finish_figure(fig, output_key="retention_summary", cfg=cfg, savefig=True)' in text
    assert "Use ``outpath=`` only when an advanced script intentionally overrides" in text
    assert 'outpath="retention_summary.png"' not in text


def test_qc_retention_docstring_prefers_standard_step2_figure_helper():
    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "spatial_vtk"
        / "visualize"
        / "qc"
        / "retention.py"
    )
    text = source.read_text(encoding="utf-8")

    assert "from spatial_vtk.qc import load_standard_qc_workflow_outputs" in text
    assert "qc_outputs = load_standard_qc_workflow_outputs(cfg=cfg)" in text
    assert "result = qc_outputs.write_figures(settings, cfg=cfg)" in text
    assert "Use individual functions such as ``plot_retention_summary()`` directly only" in text
    assert 'outpath="retention.png"' not in text


def test_spatial_map_docstring_prefers_standard_map_figure_writer():
    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "spatial_vtk"
        / "spatial"
        / "map"
        / "__init__.py"
    )
    text = source.read_text(encoding="utf-8")

    assert "from spatial_vtk.spatial.plot import write_standard_spatial_map_figures" in text
    assert "result = write_standard_spatial_map_figures(context, settings)" in text
    assert "Use individual map functions such as ``plot_station_metric_map()`` directly" in text
    assert "Create a station residual map" not in text


def test_metric_gof_docstring_prefers_public_metrics_import():
    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "spatial_vtk"
        / "metrics"
        / "calculate"
        / "gof.py"
    )
    text = source.read_text(encoding="utf-8")

    assert "from spatial_vtk.metrics import compute_metrics_pair" in text
    assert "from spatial_vtk.metrics.calculate.gof import compute_metrics_pair" not in text


def test_metric_example_plots_use_public_metric_imports():
    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "spatial_vtk"
        / "metrics"
        / "plot"
        / "example_metric_plots.py"
    )
    text = source.read_text(encoding="utf-8")

    assert "from spatial_vtk.metrics import compute_metrics_pair" in text
    assert "from spatial_vtk.metrics.calculate.gof import compute_metrics_pair" not in text


def test_qc_api_docs_use_public_package_entry_point():
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "api" / "qc.rst"
    text = docs.read_text(encoding="utf-8")

    assert "Start with ``spatial_vtk.qc``" in text
    assert "Public helpers exposed by ``spatial_vtk.qc``" in text
    assert ".. automodule:: spatial_vtk.qc\n" in text
    assert "Use ``spatial_vtk.qc`` for notebook-facing QC build helpers" in text
    assert "lower-level review table module is implementation" in text
    assert "lower-level summary rules module is implementation" in text
    import_block = text.split(".. automodule:: spatial_vtk.qc", maxsplit=1)[0]
    assert import_block.index("load_standard_qc_workflow_outputs") < import_block.index(
        "run_qc_inventory_from_config"
    )
    helper_table = text.split("Public helpers exposed by ``spatial_vtk.qc``:", maxsplit=1)[1]
    assert helper_table.index("load_standard_qc_workflow_outputs") < helper_table.index(
        "run_qc_inventory_from_config"
    )
    assert helper_table.index("load_standard_qc_inputs") < helper_table.index(
        "run_qc_inventory_from_config"
    )
    assert (
        "Routine notebooks should usually call this through\n"
        "       ``load_standard_qc_workflow_outputs(...).run_inventory_step_if_needed(...)``"
    ) in text
    for helper in (
        "run_qc_inventory_from_config",
        "qc_inventory_readiness_from_config",
        "write_qc_inventory_overlap_from_config",
        "qc_overlap_readiness_from_config",
        "run_qc_summary_workflow_from_config",
        "qc_summary_readiness_from_config",
        "load_standard_qc_inputs",
        "load_standard_qc_workflow_outputs",
        "build_metric_pair_retention_table_from_qc_inventory",
        "build_event_station_pair_retention_table_from_qc_inventory",
        "build_post_qc_record_table_from_qc_inventory",
        "build_qc_drop_cause_table_from_qc_inventory",
        "export_manual_review_queue_from_qc_inventory",
        "filter_event_station_records_for_source_overlap",
        "load_trace_inventory_lookup",
    ):
        assert helper in text
    assert "bounded compact-summary previews" in text
    assert "full trace/QC inventory inspection" in text
    forbidden_modules = (
        "spatial_vtk.qc.build.filtering",
        "spatial_vtk.qc.build.inventory",
        "spatial_vtk.qc.build.spectral",
        "spatial_vtk.qc.build.workflow",
        "spatial_vtk.qc.review.tables",
        "spatial_vtk.qc.summary.rules",
    )
    for module_name in forbidden_modules:
        assert f".. automodule:: {module_name}" not in text


def test_io_api_docs_use_public_workflow_helpers():
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "api" / "io.rst"
    text = docs.read_text(encoding="utf-8")

    assert "Start with ``spatial_vtk.io``" in text
    assert "Public helpers exposed by ``spatial_vtk.io``" in text
    assert ".. automodule:: spatial_vtk.io\n" in text
    for helper in (
        "output_group",
        "preprocessed_waveform_output_group",
        "load_standard_ingest_workflow_outputs",
        "MetadataPreparationResult",
        "output_readiness",
        "OutputReadiness",
        "load_configured_input_paths",
        "load_configured_input_tables",
        "event_display_label",
        "event_ids_from_records",
        "event_label_preview_frame",
        "event_rows_for_records",
        "first_nonempty_table_value",
        "metadata_tables_readiness_from_config",
        "prepare_metadata_tables_from_config",
        "preprocessing_readiness_from_config",
        "preprocess_waveforms_from_config",
        "WaveformPreprocessingSummaryResult",
        "record_coverage_readiness_from_config",
        "RecordCoverageWorkflowResult",
        "build_record_coverage_from_config",
        "read_bounded_table",
        "preview_table",
        "write_output_table",
        "load_output_table",
    ):
        assert helper in text
    assert "instead of repeating output-path variables" in text
    assert "metadata row-count summary" in text
    assert "``status_frame()`` and\n       ``output_group_status_frame()`` include clear ``resolved_path`` values\n       plus ``output_key``, ``kind``, ``required``, ``artifact_label``" in text
    assert "``readiness``, ``message``, and ``suggested_action`` columns" in text
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
    assert "calculate implementation modules are\nimplementation organization" in text
    assert "Start with ``spatial_vtk.spatial`` for spatial-statistics" in text
    assert "from spatial_vtk.spatial import (" in text
    assert "load_standard_spatial_workflow_output_status" in text
    assert text.index("load_standard_spatial_workflow_output_status") < text.index("run_spatial_statistics_workflow_from_config")
    assert "run_spatial_statistics_workflow_from_config" in text
    assert "run_geojson_region_summary_workflow_from_config" in text
    assert "run_boundary_corridor_workflow_from_config" in text
    assert "Public helpers exposed by ``spatial_vtk.spatial``" in text
    for helper in (
        "load_standard_spatial_workflow_output_status",
        "load_standard_spatial_workflow_outputs",
        "run_spatial_derived_outputs_workflow_from_config",
        "spatial_workflow_failure_frame",
        "spatial_correlation_preview_frame",
        "spatial_metric_table_frame",
        "spatial_metric_product_frames",
        "spatial_metric_product_summary_frame",
        "spatial_pca_product_frames",
        "station_bias_preview_frame",
        "spatial_statistics_settings_from_config",
        "build_path_table",
        "summarize_residuals_by_path_bin",
        "annotate_points_with_geojson",
        "classify_paths_with_geojson",
        "geojson_metric_region_frame",
        "geojson_metric_subset_frame",
        "build_station_edge_corridors",
        "corridor_record_pair_frame",
        "corridor_record_preview_frame",
        "event_station_records_matching_pairs",
        "geojson_matched_record_frame",
        "select_records_by_corridors",
    ):
        assert helper in text
    assert "Routine notebooks\n       should usually call this through the standard status result above" in text
    assert "remembers the config used to create it" in text
    assert "display_table_previews(nrows=...)" in text
    assert "status result retains its config" in text
    assert "display_metric_source_preview(nrows=...)" in text
    assert "from spatial_vtk.spatial.plot import (" in text
    first_plot_import = text.split("from spatial_vtk.spatial.plot import (", 1)[1].split(")", 1)[0]
    assert "write_large_run_spatial_figure_suite_from_notebook_settings" in first_plot_import
    assert "write_standard_spatial_map_figures" in first_plot_import
    assert "plot_correlogram" not in first_plot_import
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
        "RegionFigureResult",
        "write_large_run_geojson_region_figures_from_outputs",
        "write_large_run_geojson_region_figures_from_notebook_settings",
        "write_large_run_region_boxplot_from_outputs",
        "write_large_run_region_boxplot_from_notebook_settings",
        "write_standard_spatial_diagnostic_figures",
        "write_standard_spatial_map_figures",
    ):
        assert helper in text
    helper_table = text.split("Public helpers exposed by ``spatial_vtk.spatial.plot``", 1)[1].split(
        "Large-Run Spatial Figure Suite",
        1,
    )[0]
    assert "prepare_spatial_figure_context" not in helper_table
    assert "SpatialFigureContext" not in helper_table
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
    assert ".. autoclass:: spatial_vtk.spatial.plot.RegionFigureResult" in text
    assert ".. autoclass:: spatial_vtk.spatial.plot.SpatialSummaryFigureResult" in text
    assert ".. autofunction:: spatial_vtk.spatial.plot.prepare_spatial_figure_context" in text
    assert ".. autofunction:: spatial_vtk.spatial.plot.prepare_spatial_figure_context_from_notebook_settings" in text
    assert ".. autoclass:: spatial_vtk.spatial.plot.SpatialFigureSuiteResult" in text
    assert ".. autofunction:: spatial_vtk.spatial.plot.write_large_run_spatial_figure_suite_from_notebook_settings" in text
    assert ".. autofunction:: spatial_vtk.spatial.plot.write_large_run_spatial_summary_figures_from_outputs" in text
    assert ".. autofunction:: spatial_vtk.spatial.plot.write_large_run_geojson_region_figures_from_outputs" in text
    assert ".. autofunction:: spatial_vtk.spatial.plot.write_large_run_geojson_region_figures_from_notebook_settings" in text
    assert ".. autofunction:: spatial_vtk.spatial.plot.write_large_run_region_boxplot_from_outputs" in text
    assert ".. autofunction:: spatial_vtk.spatial.plot.write_large_run_region_boxplot_from_notebook_settings" in text
    assert ".. autofunction:: spatial_vtk.spatial.plot.write_standard_spatial_map_figures" in text
    assert ".. autofunction:: spatial_vtk.spatial.plot.write_standard_spatial_diagnostic_figures" in text
    assert "write_large_run_spatial_figure_suite_from_notebook_settings," in text
    assert "write_standard_spatial_map_figures," in text
    assert "prepare_spatial_figure_context_from_notebook_settings," not in text
    assert "Notebook-facing spatial plotting should use the result-object and suite helpers" in text
    assert "Advanced Spatial Figure Extension Helpers" in text
    assert "not the preferred tutorial or notebook entry\npoints" in text
    assert "New notebooks should call\n``write_large_run_spatial_figure_suite_from_notebook_settings``" in text
    assert "exact ``figure_paths`` lists" in text
    assert "preview-oriented path fields" in text
    assert "station_summary_for_item" in text
    assert "item_source_rows" in text
    assert "``status_frame`` uses ``resolved_path`` as the clear path\n   column while preserving ``path`` for compatibility" in text
    assert "GeoJSON and region plotting status tables use ``resolved_path``" in text
    assert "internal owner tag" in text
    assert "overlapping dataframe" in text
    assert "``spectral_metric_contract_status``" in text
    assert "legacy passband-scoped spectral rows" in text
    assert "without notebook-local plot-function imports" in text
    forbidden = (
        "spatial_vtk.spatial.calculate.prepare_stats",
        "spatial_vtk.spatial.calculate.correlation",
        "spatial_vtk.spatial.calculate.clustering",
        "spatial_vtk.spatial.calculate.pca",
        "spatial_vtk.spatial.calculate.geology",
        "spatial_vtk.spatial.calculate.geojson",
        "spatial_vtk.spatial.calculate.corridors",
        "spatial_vtk.spatial.calculate.geometry",
        "spatial_vtk.spatial.calculate.paths",
        "spatial_vtk.spatial.calculate.patterns",
        "spatial_vtk.spatial.calculate.polygon_edges",
        "spatial_vtk.spatial.calculate.rotation",
        "spatial_vtk.spatial.calculate.settings",
        "spatial_vtk.spatial.calculate.workflow",
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
            "metadata_tables_readiness_from_config",
            "preprocessing_readiness_from_config",
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
            "load_standard_metric_workflow_outputs",
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


def _documented_import_names(text: str, module_name: str) -> set[str]:
    """Return names imported from one module in literal docs examples."""

    names: set[str] = set()
    block_pattern = re.compile(
        rf"from {re.escape(module_name)} import \(\n(?P<body>.*?)\n\s*\)",
        re.DOTALL,
    )
    for match in block_pattern.finditer(text):
        for line in match.group("body").splitlines():
            name = line.strip().rstrip(",")
            if name and not name.startswith("#"):
                names.add(name)

    line_pattern = re.compile(
        rf"^\s*from {re.escape(module_name)} import (?P<body>[A-Za-z0-9_, ]+)$",
        re.MULTILINE,
    )
    for match in line_pattern.finditer(text):
        for name in match.group("body").split(","):
            name = name.strip()
            if name:
                names.add(name)
    return names


def _literal_export_names(source_path: pathlib.Path, assignment_names: tuple[str, ...]) -> set[str]:
    """Read simple string export assignments without importing optional deps."""

    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    exports: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id in assignment_names
            for target in node.targets
        ):
            continue
        value = node.value
        if isinstance(value, (ast.List, ast.Set, ast.Tuple)):
            exports.update(
                str(elt.value)
                for elt in value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            )
        elif isinstance(value, ast.Dict):
            exports.update(
                str(key.value)
                for key in value.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            )
    return exports


def _public_exports_for_docs_module(root: pathlib.Path, module_name: str) -> set[str]:
    """Return public exports for API-reference import examples."""

    source_root = root / "src" / "spatial_vtk"
    source_map = {
        "spatial_vtk.io": (source_root / "io" / "__init__.py", ("__all__",)),
        "spatial_vtk.metrics": (
            source_root / "metrics" / "__init__.py",
            ("_CALCULATE_EXPORTS", "_WORKFLOW_EXPORTS"),
        ),
        "spatial_vtk.metrics.plot": (
            source_root / "metrics" / "plot" / "__init__.py",
            ("_EXPORT_MODULES",),
        ),
        "spatial_vtk.qc": (
            source_root / "qc" / "__init__.py",
            ("_BUILD_EXPORTS", "_REVIEW_EXPORTS", "_SUMMARY_EXPORTS", "_SLURM_EXPORTS"),
        ),
        "spatial_vtk.spatial": (
            source_root / "spatial" / "calculate" / "__init__.py",
            ("__all__",),
        ),
        "spatial_vtk.spatial.plot": (
            source_root / "spatial" / "plot" / "__init__.py",
            ("_EXPORT_MODULES",),
        ),
        "spatial_vtk.spatial.map": (
            source_root / "spatial" / "map" / "__init__.py",
            ("_EXPORT_MODULES",),
        ),
    }
    source_path, assignment_names = source_map[module_name]
    return _literal_export_names(source_path, assignment_names)


def test_api_reference_import_examples_match_public_exports():
    """Start-here import examples should only name public package exports."""

    root = pathlib.Path(__file__).resolve().parents[1]
    docs_root = root / "docs" / "reference" / "api"
    docs_text = "\n".join(
        (docs_root / name).read_text(encoding="utf-8")
        for name in ("io.rst", "metrics.rst", "qc.rst", "spatial.rst")
    )
    public_modules = (
        "spatial_vtk.io",
        "spatial_vtk.metrics",
        "spatial_vtk.metrics.plot",
        "spatial_vtk.qc",
        "spatial_vtk.spatial",
        "spatial_vtk.spatial.plot",
        "spatial_vtk.spatial.map",
    )
    for module_name in public_modules:
        documented = _documented_import_names(docs_text, module_name)
        assert documented, f"{module_name} has no API-reference import example"
        exports = _public_exports_for_docs_module(root, module_name)
        missing = documented - exports
        assert not missing, f"{module_name} docs import non-public names: {sorted(missing)}"


def test_committed_tutorial_scenario_uses_committed_lightweight_inputs():
    """Fresh-clone tutorials should point at committed NPZ/dataframe inputs."""

    root = pathlib.Path(__file__).resolve().parents[1]
    config_path = root / "data" / "examples" / "configuration" / "example_spatial_vtk_config.yaml"
    text = config_path.read_text(encoding="utf-8")
    expected_snippets = (
        'observed_template: "{root_dir}/data/examples/example_five_event_subset/'
        'waveforms_npz/observed/{event_id}/{station}.npz"',
        'synthetic_template: "{root_dir}/data/examples/example_five_event_subset/'
        'waveforms_npz/synthetics/{model}/{event_id}/{station}.npz"',
        'station_metadata: "{root_dir}/data/examples/example_five_event_subset/'
        'metadata/selected_stations.csv"',
        'event_metadata: "{root_dir}/data/examples/example_five_event_subset/'
        'metadata/events.csv"',
        'event_station_table: "{root_dir}/data/examples/example_five_event_subset/'
        'metadata/selected_event_stations.csv"',
        'site_metadata: "{root_dir}/data/examples/data_formats/'
        'example_site_metadata.csv"',
        'region_geojson: "{root_dir}/data/examples/example_five_event_subset/'
        'metadata/example_path_regions.geojson"',
        'metric_snapshot: "{root_dir}/data/examples/data_formats/'
        'example_metrics_snapshot.csv"',
        'metric_figure_snapshot: "{root_dir}/data/examples/data_formats/'
        'example_metrics_large_qc_passed.parquet"',
    )
    for snippet in expected_snippets:
        assert snippet in text

    required_files = (
        "data/examples/example_five_event_subset/metadata/selected_stations.csv",
        "data/examples/example_five_event_subset/metadata/events.csv",
        "data/examples/example_five_event_subset/metadata/selected_event_stations.csv",
        "data/examples/example_five_event_subset/metadata/example_path_regions.geojson",
        "data/examples/data_formats/example_site_metadata.csv",
        "data/examples/data_formats/example_metrics_snapshot.csv",
        "data/examples/data_formats/example_metrics_large_qc_passed.parquet",
    )
    tracked_files = set(
        subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines()
    )
    for relative_path in required_files:
        assert (root / relative_path).exists(), relative_path
        assert relative_path in tracked_files, relative_path

    observed_npz = sorted(
        (root / "data/examples/example_five_event_subset/waveforms_npz/observed").glob("*/*.npz")
    )
    synthetic_npz = sorted(
        (root / "data/examples/example_five_event_subset/waveforms_npz/synthetics").glob("*/*/*.npz")
    )
    assert len(observed_npz) >= 100
    assert len(synthetic_npz) >= 100
    missing_observed = [
        str(path.relative_to(root))
        for path in observed_npz
        if str(path.relative_to(root)) not in tracked_files
    ]
    missing_synthetic = [
        str(path.relative_to(root))
        for path in synthetic_npz
        if str(path.relative_to(root)) not in tracked_files
    ]
    assert not missing_observed
    assert not missing_synthetic


def test_spatial_package_docstring_describes_namespace_boundary():
    """The top-level spatial package should explain where plotting imports live."""

    source = (
        pathlib.Path(__file__).resolve().parents[1] / "src" / "spatial_vtk" / "spatial" / "__init__.py"
    ).read_text(encoding="utf-8")
    assert "stable import surface for spatial calculations" in source
    assert "spatial_vtk.spatial.plot" in source
    assert "spatial_vtk.spatial.map" in source


def test_core_package_docstrings_describe_public_entry_points():
    """Top-level package docs should steer notebooks to stable import surfaces."""

    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "spatial_vtk"
    io_source = (root / "io" / "__init__.py").read_text(encoding="utf-8")
    config_source = (root / "config" / "__init__.py").read_text(encoding="utf-8")
    visualize_source = (root / "visualize" / "__init__.py").read_text(encoding="utf-8")

    assert "``spatial_vtk.io`` is the public import surface" in io_source
    assert "Routine notebooks should start here" in io_source
    assert "lower-level metadata, preprocessing, table, output-path, or\nmanifest modules" in io_source

    assert "``spatial_vtk.config`` is the public import surface" in config_source
    assert "notebook run contexts" in config_source
    assert "rather than reaching into runtime, output, or notebook\nimplementation modules directly" in config_source

    assert "``spatial_vtk.visualize`` is the public import surface" in visualize_source
    assert "``spatial_vtk.visualize.context``" in visualize_source
    assert "lower-level utility modules" in visualize_source
    assert "package remains lazy" in visualize_source


def test_visualize_api_docs_use_public_entry_points():
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "api" / "visualize.rst"
    text = docs.read_text(encoding="utf-8")
    assert "Public helpers exposed by ``spatial_vtk.visualize``" in text
    assert "from spatial_vtk.visualize import (" in text
    import_block = text.split("from spatial_vtk.visualize import (", 1)[1].split(")", 1)[0]
    assert "dashboard_output_readiness," in import_block
    assert "dashboard_output_status_frame," in import_block
    assert "dashboard_readiness_summary_frame," in import_block
    assert "display_dashboard_output_previews," in import_block
    assert "display_dashboard_preparation_result," in import_block
    assert "figure_sidecar_status_frame," in import_block
    assert "launch_configured_dashboards_from_notebook_settings," in import_block
    assert "prepare_configured_dashboard_datasets_from_notebook_settings," in import_block
    assert "write_waveform_comparison_from_notebook_settings," in import_block
    assert "write_configured_dashboard_datasets," not in import_block
    assert text.index("``write_waveform_comparison_from_notebook_settings``") < text.index(
        "``write_waveform_comparison_from_outputs``"
    )
    assert text.index("``prepare_configured_dashboard_datasets_from_notebook_settings``") < text.index(
        "``write_configured_dashboard_datasets``"
    )
    assert text.index("``launch_configured_dashboards_from_notebook_settings``") < text.index(
        "``launch_configured_metrics_dashboard``"
    )
    for helper in (
        "plot_station_event_beachball_map",
        "write_context_figures_from_outputs",
        "write_large_run_context_figures_from_outputs",
        "plot_retention_summary",
        "plot_event_station_retention_heatmap",
        "write_qc_figures_from_outputs",
        "write_large_run_qc_figures_from_outputs",
        "plot_observed_synthetic_record_section",
        "write_waveform_comparison_from_outputs",
        "write_waveform_comparison_from_notebook_settings",
        "write_large_run_waveform_comparison_from_outputs",
        "finish_figure_with_sidecar",
        "write_figure_row_sidecar",
        "figure_sidecar_status_frame",
        "dashboard_output_readiness",
        "write_configured_dashboard_datasets",
        "prepare_configured_dashboard_datasets_from_notebook_settings",
        "display_dashboard_output_previews",
        "display_dashboard_preparation_result",
        "dashboard_readiness_summary_frame",
        "dashboard_output_status_frame",
        "preview_dashboard_summary_tables",
        "launch_configured_dashboards_from_notebook_settings",
        "launch_configured_metrics_dashboard",
        "launch_configured_qc_dashboard",
    ):
        assert helper in text
    assert ".. automodule:: spatial_vtk.visualize.context\n" in text
    assert ".. automodule:: spatial_vtk.visualize.dashboard\n" in text
    assert ".. automodule:: spatial_vtk.visualize.qc\n" in text
    assert ".. automodule:: spatial_vtk.visualize.waveforms\n" in text
    assert "Import context helpers from ``spatial_vtk.visualize.context``" in text
    assert "Import QC visualization helpers from ``spatial_vtk.visualize.qc``" in text
    assert "Import waveform\nfigure helpers from ``spatial_vtk.visualize.waveforms``" in text
    assert "Import dashboard helpers\nfrom ``spatial_vtk.visualize.dashboard``" in text
    assert "metrics dashboard row dataset" in text
    assert "internal output registry names" in text
    assert "``metrics_dashboard_root``" not in text
    assert "pass ``metrics_dataset_dir`` and\n``dashboard_summary_table_dir`` to ``launch_metrics_dashboard``" in text
    assert "``metrics_root`` and ``summary_root`` keyword arguments remain supported" in text
    assert "pass ``qc_trace_summary_table`` to ``launch_qc_dashboard``" in text
    assert "Missing sidecar directories and existing empty sidecar directories" in text
    assert "``sidecar_dir_exists``" in text

    forbidden_modules = (
        "spatial_vtk.visualize.context.figures",
        "spatial_vtk.visualize.context.maps",
        "spatial_vtk.visualize.qc.overview",
        "spatial_vtk.visualize.qc.retention",
        "spatial_vtk.visualize.qc.samples",
        "spatial_vtk.visualize.waveforms.comparison",
        "spatial_vtk.visualize.waveforms.overlays",
        "spatial_vtk.visualize.waveforms.radial_sections",
        "spatial_vtk.visualize.waveforms.record_sections",
        "spatial_vtk.visualize.waveforms.station_event",
        "spatial_vtk.visualize.dashboard.charts",
        "spatial_vtk.visualize.dashboard.contracts",
        "spatial_vtk.visualize.dashboard.export",
        "spatial_vtk.visualize.dashboard.exports",
        "spatial_vtk.visualize.dashboard.filters",
        "spatial_vtk.visualize.dashboard.labels",
        "spatial_vtk.visualize.dashboard.launch",
        "spatial_vtk.visualize.dashboard.maps",
        "spatial_vtk.visualize.dashboard.tables",
    )
    for module_name in forbidden_modules:
        assert f".. automodule:: {module_name}" not in text
    assert "When a dashboard tab is blank or unexpectedly sparse" in text
    assert "from spatial_vtk.visualize.dashboard import (" in text
    assert "dashboard_output_status_frame" in text
    assert "dashboard_readiness_summary_frame" in text
    assert "dashboard_summary_table_contracts" in text
    assert "The readiness and status frames are intentionally small" in text
    assert "``artifact_label``" in text
    assert "``resolved_path`` as the clear path column" in text
    assert "``dashboard_tabs``" in text
    assert "``suggested_action``" in text
    assert "``required_columns`` / ``missing_columns`` / ``map_message``" in text
    assert "SVTK_METRICS_DASHBOARD_ROW_LIMIT" in text
    assert "Maximum row-level records" in text
    assert "SVTK_QC_DASHBOARD_MAX_ROWS" in text
    assert "Maximum trace-summary rows" in text
    assert "Public helpers exposed by ``spatial_vtk.visualize.dashboard``" in text
    assert "Large-run notebooks\nset ``prepare_locally=False``" in text
    assert "``run_if_needed(...)`` method" in text
    assert "display_output_previews(nrows=...)" in text
    assert "bounded output previews through the\n       returned ``DashboardDatasetPreparationResult``" in text
    assert "Direct script helper for observed/synthetic trace-comparison" in text
    assert "Notebook-facing Step 2/6 waveform-comparison wrapper" in text
    assert "Backward-compatible alias for older large-run notebooks" in text
    assert "Notebook cells should use\n``write_waveform_comparison_from_notebook_settings``" in text
    assert "Scripts can use\n``write_waveform_comparison_from_outputs``" in text
    assert "Lower-level script helper that writes dashboard-ready row and summary" in text
    assert "Lower-level launch helpers for scripts" in text
    for helper in (
        "dashboard_summary_table_contracts",
        "dashboard_summary_table_paths",
        "display_dashboard_output_previews",
        "dashboard_metric_dataset_readiness_frame",
        "dashboard_qc_trace_readiness_frame",
        "load_dashboard_metric_dataset",
        "load_filtered_dashboard_summary_table",
        "load_dashboard_summary_tables",
        "preview_dashboard_summary_tables",
        "filter_dashboard_metrics",
        "filter_qc_dashboard_rows",
    ):
        assert helper in text
    assert "Public sidecar helpers exposed by ``spatial_vtk.visualize``" in text
    assert "Routine notebooks should use the public helpers listed above" in text
    assert "family-specific ``spatial_vtk.visualize.context``" in text
    assert "documented for advanced\nscripts and package extension points" in text
    assert "not notebook workflow entry\npoints" in text
    assert "aggregation_contract" in text
    assert "aggregation_input_row_count" in text
    assert "source_rows_filter" in text
    assert "aggregation_panel_count" in text
    assert "station/event counts" in text
    assert "__svtk_panel_period_s" in text
    assert "rather than a preview or sampled dataframe" in text
    for helper in (
        "layered_figure_rows",
        "sidecar_rows_for_write",
        "read_figure_sidecar_metadata",
        "figure_sidecar_dimension_counts",
    ):
        assert helper in text


def test_public_helper_tables_match_package_exports():
    """Public helper tables should not promise names absent from __all__."""

    root = pathlib.Path(__file__).resolve().parents[1]
    public_helper_tables = {
        "spatial_vtk.io": (
            root / "docs" / "reference" / "api" / "io.rst",
            "Public helpers exposed by ``spatial_vtk.io``:",
        ),
        "spatial_vtk.qc": (
            root / "docs" / "reference" / "api" / "qc.rst",
            "Public helpers exposed by ``spatial_vtk.qc``:",
        ),
        "spatial_vtk.metrics.plot": (
            root / "docs" / "reference" / "api" / "metrics.rst",
            "Public plotting helpers exposed by ``spatial_vtk.metrics.plot``:",
        ),
        "spatial_vtk.spatial": (
            root / "docs" / "reference" / "api" / "spatial.rst",
            "Public helpers exposed by ``spatial_vtk.spatial``:",
        ),
        "spatial_vtk.spatial.plot": (
            root / "docs" / "reference" / "api" / "spatial.rst",
            "Public helpers exposed by ``spatial_vtk.spatial.plot``:",
        ),
        "spatial_vtk.spatial.map": (
            root / "docs" / "reference" / "api" / "spatial.rst",
            "Public helpers exposed by ``spatial_vtk.spatial.map``:",
        ),
        "spatial_vtk.visualize": (
            root / "docs" / "reference" / "api" / "visualize.rst",
            "Public helpers exposed by ``spatial_vtk.visualize``:",
        ),
        "spatial_vtk.visualize.dashboard": (
            root / "docs" / "reference" / "api" / "visualize.rst",
            "Public helpers exposed by ``spatial_vtk.visualize.dashboard``:",
        ),
    }

    missing_by_module: dict[str, list[str]] = {}
    for module_name, (docs_path, marker) in public_helper_tables.items():
        text = docs_path.read_text(encoding="utf-8")
        table = _first_list_table_after_marker(text, marker)
        documented_helpers = _public_helper_names_from_list_table(table)
        exported_helpers = set(importlib.import_module(module_name).__all__)
        missing_helpers = sorted(documented_helpers - exported_helpers)
        if missing_helpers:
            missing_by_module[module_name] = missing_helpers

    assert missing_by_module == {}


def test_dashboard_export_docstring_starts_with_configured_helper():
    """Dashboard export module docs should not lead notebooks to raw dataset writers."""

    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "spatial_vtk"
        / "visualize"
        / "dashboard"
        / "export.py"
    ).read_text(encoding="utf-8")

    assert "prepare_configured_dashboard_datasets_from_notebook_settings(cfg=cfg)" in source
    assert "write_dashboard_metric_dataset(metrics_df, \"dashboard_data\")" not in source
    assert source.index("prepare_configured_dashboard_datasets_from_notebook_settings") < source.index(
        "write_dashboard_metric_dataset(metrics_df, output_root)"
    )


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
        "spatial_vtk.io.event_ids_from_records",
        "spatial_vtk.io.event_rows_for_records",
        "spatial_vtk.io.event_label_preview_frame",
        "spatial_vtk.io.output_group",
        "spatial_vtk.io.load_standard_ingest_workflow_outputs",
        "spatial_vtk.io.metadata_tables_readiness_from_config",
        "spatial_vtk.io.prepare_metadata_tables_from_config",
        "spatial_vtk.io.preprocessing_readiness_from_config",
        "spatial_vtk.io.preprocess_waveforms_from_config",
        "spatial_vtk.io.build_record_coverage_from_config",
        "spatial_vtk.qc.load_standard_qc_inputs",
        "spatial_vtk.qc.load_standard_qc_workflow_outputs",
        "spatial_vtk.qc.qc_inventory_readiness_from_config",
        "spatial_vtk.qc.qc_overlap_readiness_from_config",
        "spatial_vtk.qc.qc_summary_readiness_from_config",
        "spatial_vtk.qc.run_qc_inventory_from_config",
        "spatial_vtk.qc.write_qc_inventory_overlap_from_config",
        "spatial_vtk.qc.run_qc_summary_workflow_from_config",
        "spatial_vtk.metrics.build_metric_waveform_inventories_from_config",
        "spatial_vtk.metrics.metric_inventories_readiness_from_config",
        "spatial_vtk.metrics.plan_metric_tasks_from_config",
        "spatial_vtk.metrics.metric_manifest_readiness_from_config",
        "spatial_vtk.metrics.summarize_metric_snapshot_tasks_from_config",
        "spatial_vtk.metrics.load_standard_metric_workflow_outputs",
        "spatial_vtk.metrics.metric_slurm_submission_readiness_from_config",
        "spatial_vtk.metrics.write_metrics_slurm_script_from_config",
        "spatial_vtk.metrics.merge_metric_batches_from_config",
        "spatial_vtk.metrics.write_metric_outputs_from_config",
        "spatial_vtk.spatial.load_standard_spatial_workflow_output_status",
        "run_summary_step_if_needed",
        "run_derived_outputs_step_if_needed",
        "spatial_vtk.spatial.plot.load_standard_geojson_workflow_output_status",
        "run_geojson_summary_step_if_needed",
        "run_corridor_step_if_needed",
        "spatial_vtk.visualize.dashboard_readiness_summary_frame",
        "spatial_vtk.visualize.preview_dashboard_summary_tables",
        "spatial_vtk.visualize.write_configured_dashboard_datasets",
        "spatial_vtk.visualize.prepare_configured_dashboard_datasets_from_notebook_settings",
        "spatial_vtk.config.render_notebook_figure",
    ]
    for helper in required_helpers:
        assert helper in workflows
    assert "display_table_previews()" in workflows
    assert "display_first_existing_table_preview()" in workflows
    assert "Notebook cells should call those methods instead\nof passing ``cfg`` into standalone preview helpers" in workflows
    assert "``display_summary_previews()``" in workflows
    assert "``display_metrics_preview()``" in workflows
    assert "``display_metric_source_preview()``" in workflows
    assert "``display_output_previews()``" in workflows
    assert "run_notebook_step_if_needed" in workflows
    assert "notebooks should use package functions" in workflows.lower()
    assert "configured_output_registry_preview_frame" in workflows
    assert "configured_output_registry_frame(cfg=cfg, kinds=(\"table\",)).head()" not in workflows
    assert "metric_manifest_path" in workflows
    assert "geojson_region_summaries_path" in workflows
    assert "descriptive keys are the public notebook contract" in workflows
    assert "docs should not depend on generic" in workflows
    assert "Use ``run_notebook_step_if_needed`` directly only for custom" in workflows
    assert "Advanced fallback for workflow steps that do not yet have a standard" in workflows
    assert "Preview dashboard summary tables without loading full tab inputs" in workflows
    assert "without resolving dashboard summary paths in cells" in normalized_workflows
    assert "compatibility aliases" not in workflows
    assert "from spatial_vtk.config import (" in workflows
    assert "qc_inventory_readiness_from_config" in workflows
    assert "qc_outputs = load_standard_qc_workflow_outputs(cfg=cfg)" in workflows
    assert "qc_outputs.run_inventory_step_if_needed(" in workflows
    assert "readiness = qc_inventory_readiness_from_config(config_path=context.config_path)" not in workflows
    assert "run_notebook_step_if_needed(\n       context,\n       readiness,\n       run_qc_inventory_from_config" not in workflows
    assert "spatial_vtk.qc.load_standard_qc_workflow_outputs(...).run_inventory_step_if_needed(...)" in workflows
    assert "spatial_vtk.qc.load_standard_qc_workflow_outputs(...).run_overlap_step_if_needed(...)" in workflows
    assert "spatial_vtk.qc.load_standard_qc_workflow_outputs(...).run_summary_step_if_needed(...)" in workflows
    assert "spatial_vtk.metrics.load_standard_metric_workflow_outputs(...).run_manifest_step_if_needed(...)" in workflows
    assert "spatial_vtk.metrics.load_standard_metric_workflow_outputs(...).run_slurm_step_if_needed(...)" in workflows
    assert "spatial_vtk.metrics.load_standard_metric_workflow_outputs(...).run_downstream_outputs_step_if_needed(...)" in workflows
    assert "spatial_vtk.metrics.load_standard_metric_workflow_outputs(...).write_large_run_figure_suite(...)" in workflows
    assert "notebooks should prefer the standard metric result-object methods above" in workflows
    assert "notebook_figure_settings" in workflows
    assert "render_notebook_figure" in workflows
    assert "from spatial_vtk.config.notebook import" not in workflows
    assert "exact signatures, return contracts, and supporting public helpers" in workflows
    assert "exact signatures and lower-level utilities" not in workflows
    assert "``metric_outputs.metrics_long_path`` for Step 3 metric figures" in workflows
    assert "``bind()`` remains available for older notebooks" in workflows
    assert "Use ``figure_path()`` for figure artifacts" in workflows
    assert "``figure_dir / \"name.png\"``" in workflows
    assert "Legacy helpers such as ``output_group_namespace()`` return only path attributes" in workflows
    assert "New workflow notebooks should prefer the standard\n       ``load_standard_*`` helpers" in workflows
    assert "use ``output_group()`` directly\n       only when a new reusable standard helper does not exist yet" in workflows
    assert "new notebooks should use ``output_group()``" not in workflows
    assert "``PSA`` and\n``FAS`` are broadband spectral calculations" in workflows
    assert "one blank-passband spectral task" in workflows
    assert "PSA figures should use\noscillator-period sheets" in workflows
    assert "legacy metric table repeats PSA rows under waveform\npassbands" in workflows
    assert "bind(globals())" not in workflows
    assert "svtk metrics plan" not in workflows
    assert "svtk qc" not in workflows


def test_python_workflow_docs_define_stable_import_surfaces():
    """Workflow docs should map notebook helpers to importable namespaces."""

    root = pathlib.Path(__file__).resolve().parents[1]
    workflows = (root / "docs" / "reference" / "python_workflows.rst").read_text(encoding="utf-8")

    assert "Stable Import Surfaces" in workflows
    assert "Use these package namespaces as the public workflow import surface." in workflows
    assert "add a\nstable re-export first" in workflows
    assert "Avoid importing tutorial workflow helpers from implementation modules" in workflows
    assert "``spatial_vtk.metrics.workflow.execution``" in workflows
    assert "``spatial_vtk.qc.build.workflow``" in workflows
    assert "``spatial_vtk.spatial.calculate.workflow``" in workflows
    assert "``spatial_vtk.spatial.plot.large_run``" in workflows

    stable_helpers = {
        "spatial_vtk.config": [
            "notebook_run_context",
            "run_notebook_step_if_needed",
            "notebook_figure_settings",
            "render_notebook_figure",
        ],
        "spatial_vtk.io": [
            "load_standard_ingest_workflow_outputs",
            "load_configured_input_tables",
            "preprocessing_readiness_from_config",
            "build_record_coverage_from_config",
        ],
        "spatial_vtk.qc": [
            "load_standard_qc_workflow_outputs",
            "qc_inventory_readiness_from_config",
            "run_qc_inventory_from_config",
            "write_qc_inventory_overlap_from_config",
        ],
        "spatial_vtk.metrics": [
            "load_standard_metric_workflow_outputs",
            "metric_manifest_readiness_from_config",
            "plan_metric_tasks_from_config",
            "write_metric_outputs_from_config",
        ],
        "spatial_vtk.metrics.plot": [
            "write_large_run_metric_figure_suite_from_notebook_settings",
            "write_standard_metric_diagnostic_figures",
            "write_station_metric_map_from_notebook_settings",
        ],
        "spatial_vtk.spatial": [
            "load_standard_spatial_workflow_outputs",
            "load_standard_spatial_workflow_output_status",
            "run_spatial_statistics_workflow_from_config",
        ],
        "spatial_vtk.spatial.plot": [
            "load_standard_geojson_workflow_output_status",
            "load_standard_geojson_plotting_inputs",
            "load_standard_additional_plotting_inputs",
            "write_large_run_spatial_figure_suite_from_notebook_settings",
            "write_standard_spatial_map_figures",
        ],
        "spatial_vtk.spatial.map": [
            "plot_station_metric_map",
            "plot_event_residual_map",
            "add_contextily_basemap",
        ],
        "spatial_vtk.visualize.dashboard": [
            "prepare_configured_dashboard_datasets_from_notebook_settings",
            "dashboard_readiness_summary_frame",
            "launch_configured_dashboards_from_notebook_settings",
        ],
        "spatial_vtk.visualize.waveforms": [
            "write_waveform_comparison_from_notebook_settings",
            "write_waveform_comparison_from_outputs",
            "WaveformComparisonFigureResult",
        ],
    }
    for module_name, helpers in stable_helpers.items():
        assert f"``{module_name}``" in workflows
        module = importlib.import_module(module_name)
        for helper in helpers:
            assert helper in workflows
            assert hasattr(module, helper), f"{module_name}.{helper} is not public"


def test_io_api_docs_cover_output_group_preview_helpers():
    """I/O docs should list table and path-backed preview helpers together."""

    root = pathlib.Path(__file__).resolve().parents[1]
    text = (root / "docs" / "reference" / "api" / "io.rst").read_text(encoding="utf-8")
    assert "``display_table_previews()``" in text
    assert "``display_first_existing_table_preview()``" in text
    assert "``display_path_table_previews()``" in text
    assert "path-backed artifacts outside the registered\n       output table registry" in text


def test_config_api_docs_cover_output_registry_preview_helpers():
    """Config docs should expose full and bounded output-registry helpers."""

    root = pathlib.Path(__file__).resolve().parents[1]
    text = (root / "docs" / "reference" / "api" / "config.rst").read_text(encoding="utf-8")

    assert "``configured_output_registry_frame``" in text
    assert "``configured_output_registry_preview_frame``" in text
    assert "``artifact_label`` and ``resolved_path`` columns" in text
    assert "Use the preview helper\n       in notebooks when only a bounded path listing is needed" in text


def test_configuration_examples_use_registered_output_keys():
    """Configuration examples should not teach stale generic output path keys."""

    root = pathlib.Path(__file__).resolve().parents[1]
    configuration = (root / "docs" / "configuration.rst").read_text(encoding="utf-8")
    runtime_doc = (root / "src" / "spatial_vtk" / "config" / "runtime.py").read_text(encoding="utf-8")

    combined = configuration + "\n" + runtime_doc
    assert 'cfg.path("outputs.metrics")' not in combined
    assert "outputs.metrics" not in combined
    assert 'resolve_output_path("metrics_long", kind="table", cfg=cfg)' in combined
    assert "--qc-slurm-script-output outputs/slurm/build_qc_inventory.slurm" in configuration
    assert "--metrics-slurm-script-output`` are omitted" in configuration
    assert "--output outputs/slurm/build_qc.slurm" not in configuration
    assert "``--manifest`` and ``--output`` are omitted" not in configuration


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


def test_python_workflow_docs_prefer_waveform_notebook_settings_wrapper():
    """Workflow docs should match the package-backed Step 2/6 notebook pattern."""

    root = pathlib.Path(__file__).resolve().parents[1]
    workflows = (root / "docs" / "reference" / "python_workflows.rst").read_text(encoding="utf-8")
    comparison = (root / "src" / "spatial_vtk" / "visualize" / "waveforms" / "comparison.py").read_text(
        encoding="utf-8"
    )

    assert "Step 2 and Step 6 waveform-comparison cells should use" in workflows
    assert "spatial_vtk.visualize.waveforms.write_waveform_comparison_from_notebook_settings" in workflows
    assert "For\nscripts, use\n``spatial_vtk.visualize.waveforms.write_waveform_comparison_from_outputs`` when" in workflows
    assert "Prefer :func:`write_waveform_comparison_from_notebook_settings` in" in comparison
    assert "notebook cells so package code owns render gates" in comparison
    assert "Prefer :func:`write_waveform_comparison_from_outputs` in new notebooks" not in comparison


def test_python_workflow_docs_prefer_region_boxplot_notebook_settings_wrapper():
    """Region boxplot workflow docs should match the Step 6 notebook pattern."""

    workflows_path = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "python_workflows.rst"
    workflows = workflows_path.read_text(encoding="utf-8")

    assert "Region boxplot cells should use" in workflows
    assert "spatial_vtk.spatial.plot.write_large_run_region_boxplot_from_notebook_settings" in workflows
    assert "That wrapper owns the figure render gate, notebook figure settings, sidecar" in workflows
    assert "Use\n``spatial_vtk.spatial.plot.write_large_run_region_boxplot_from_outputs`` from\nscripts" in workflows
    assert "Standard Notebook Input Helpers" in workflows
    assert "the preferred pattern for standard notebooks" in workflows


def test_python_workflow_docs_prefer_metric_figure_suite_wrapper():
    """Metric workflow docs should point notebook users at the task-level figure suite."""

    workflows_path = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "python_workflows.rst"
    workflows = workflows_path.read_text(encoding="utf-8")
    normalized = " ".join(workflows.split())

    assert "spatial_vtk.metrics.plot.write_large_run_metric_figure_suite_from_notebook_settings" in workflows
    assert "That wrapper owns the figure render gate, metric-table readiness checks" in workflows
    assert "without notebook-local row filtering, figure-context construction, or per-plot path plumbing" in normalized
    assert "DashboardDatasetPreparationResult.display_output_previews()" in workflows
    assert "DashboardDatasetPreparationResult.run_if_needed()" in workflows
    assert "the result owns the Slurm/local execution branch" in workflows
    assert "spatial_vtk.metrics.plot.prepare_large_run_metric_figure_context" not in workflows
    assert "spatial_vtk.metrics.plot.metric_rows_for_metrics" not in workflows
    assert "metric row selectors" not in workflows
    assert "tutorials should use the result-object figure-suite methods instead" in workflows
    assert "``spatial_vtk.io.load_standard_ingest_workflow_outputs``" in workflows
    assert "``spatial_vtk.qc.load_standard_qc_inputs``" in workflows
    assert "``spatial_vtk.qc.load_standard_qc_workflow_outputs``" in workflows
    assert "``spatial_vtk.metrics.load_standard_metric_workflow_outputs``" in workflows
    assert "``spatial_vtk.spatial.load_standard_spatial_workflow_outputs``" in workflows
    assert "``spatial_vtk.spatial.plot.load_standard_geojson_plotting_inputs``" in workflows


def test_python_workflow_docs_prefer_spatial_figure_suite_wrapper():
    """Spatial workflow docs should point notebook users at the task-level figure suite."""

    workflows_path = pathlib.Path(__file__).resolve().parents[1] / "docs" / "reference" / "python_workflows.rst"
    workflows = workflows_path.read_text(encoding="utf-8")
    normalized = " ".join(workflows.split())

    assert "spatial_vtk.spatial.plot.write_large_run_spatial_figure_suite_from_notebook_settings" in workflows
    assert "That wrapper owns spatial table readiness checks, figure settings" in workflows
    assert "notebooks do not build spatial figure contexts or per-plot paths by hand" in normalized
    assert "spatial_vtk.spatial.plot.prepare_spatial_figure_context_from_notebook_settings" not in workflows
    assert "``spatial_vtk.spatial.plot.load_standard_additional_plotting_inputs``" in workflows
    assert "fallback path choices in the cell" in workflows


def test_package_overview_points_to_public_workflow_helpers():
    docs = pathlib.Path(__file__).resolve().parents[1] / "docs" / "package_overview.rst"
    text = docs.read_text(encoding="utf-8")

    required = [
        "Start with public helpers from ``spatial_vtk.io``",
        "``prepare_event_station_table``",
        "``preprocess_waveforms_from_config``",
        "``output_group`` and ``output_readiness``",
        "Start with public helpers from ``spatial_vtk.qc``",
        "``load_standard_qc_inputs``",
        "``load_standard_qc_workflow_outputs``",
        "``run_qc_inventory_from_config``",
        "``write_qc_inventory_overlap_from_config``",
        "Routine notebooks should use the standard QC result helpers first.",
        "custom orchestration that need to bypass the\nresult-owned notebook status/skip wrapper",
        "Start with public helpers from ``spatial_vtk.metrics``",
        "``plan_metric_tasks_from_config``",
        "``summarize_metric_snapshot_tasks_from_config``",
        "``metric_manifest_batch_status`` and ``metric_slurm_submission_readiness``",
        "``write_metric_outputs_from_config``",
        "Start with public helpers from ``spatial_vtk.spatial``",
        "``load_standard_spatial_workflow_output_status``",
        "result-owned summary/derived-output runner gates",
        "``load_standard_spatial_workflow_outputs``",
        "``run_spatial_statistics_workflow_from_config`` and",
        "``load_standard_geojson_workflow_output_status``",
        "Step 5 GeoJSON/corridor",
        "``load_standard_geojson_plotting_inputs``",
        "``spatial_vtk.spatial.plot`` and ``spatial_vtk.spatial.map``",
        "Routine notebooks should use the standard spatial and plotting result helpers\nfirst.",
        "custom orchestration that need to bypass the\nresult-owned notebook status/skip wrappers",
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
    assert "prepare_spatial_figure_context_from_notebook_settings" in spatial_plot.__all__
    assert "SpatialFigureSuiteResult" in spatial_plot.__all__
    assert "SpatialSummaryFigureResult" in spatial_plot.__all__
    assert "StandardSpatialDiagnosticFigureResult" in spatial_plot.__all__
    assert "StandardSpatialMapFigureResult" in spatial_plot.__all__
    assert "write_large_run_geojson_region_figures_from_outputs" in spatial_plot.__all__
    assert "write_large_run_geojson_region_figures_from_notebook_settings" in spatial_plot.__all__
    assert "write_large_run_region_boxplot_from_outputs" in spatial_plot.__all__
    assert "write_large_run_region_boxplot_from_notebook_settings" in spatial_plot.__all__
    assert "write_large_run_spatial_figure_suite_from_notebook_settings" in spatial_plot.__all__
    assert "write_large_run_spatial_summary_figures_from_outputs" in spatial_plot.__all__
    assert "write_standard_spatial_diagnostic_figures" in spatial_plot.__all__
    assert "write_standard_spatial_map_figures" in spatial_plot.__all__
    assert callable(spatial_plot.plot_correlogram)
    assert callable(spatial_plot.SpatialFigureSuiteResult)
    assert callable(spatial_plot.SpatialSummaryFigureResult)
    assert callable(spatial_plot.StandardSpatialDiagnosticFigureResult)
    assert callable(spatial_plot.StandardSpatialMapFigureResult)
    assert callable(spatial_plot.prepare_spatial_figure_context)
    assert callable(spatial_plot.prepare_spatial_figure_context_from_notebook_settings)
    assert callable(spatial_plot.write_large_run_geojson_region_figures_from_outputs)
    assert callable(spatial_plot.write_large_run_geojson_region_figures_from_notebook_settings)
    assert callable(spatial_plot.write_large_run_region_boxplot_from_outputs)
    assert callable(spatial_plot.write_large_run_region_boxplot_from_notebook_settings)
    assert callable(spatial_plot.write_large_run_spatial_figure_suite_from_notebook_settings)
    assert callable(spatial_plot.write_large_run_spatial_summary_figures_from_outputs)
    assert callable(spatial_plot.write_standard_spatial_diagnostic_figures)
    assert callable(spatial_plot.write_standard_spatial_map_figures)
    assert spatial_plot.plot_correlogram is spatial_plot.plot_correlogram


def test_metric_plot_public_entry_point_exposes_large_run_suite():
    import spatial_vtk.metrics.plot as metric_plot

    assert "MetricFigureSuiteResult" in metric_plot.__all__
    assert "StandardMetricDiagnosticFigureResult" in metric_plot.__all__
    assert "write_large_run_metric_figure_suite_from_notebook_settings" in metric_plot.__all__
    assert "write_standard_metric_diagnostic_figures" in metric_plot.__all__
    assert callable(metric_plot.MetricFigureSuiteResult)
    assert callable(metric_plot.StandardMetricDiagnosticFigureResult)
    assert callable(metric_plot.write_large_run_metric_figure_suite_from_notebook_settings)
    assert callable(metric_plot.write_standard_metric_diagnostic_figures)
    assert (
        metric_plot.write_large_run_metric_figure_suite_from_notebook_settings
        is metric_plot.write_large_run_metric_figure_suite_from_notebook_settings
    )


def test_waveform_large_run_helper_is_public():
    import spatial_vtk.visualize as visualize
    import spatial_vtk.visualize.waveforms as waveforms

    assert "write_waveform_comparison_from_outputs" in visualize.__all__
    assert "write_waveform_comparison_from_outputs" in waveforms.__all__
    assert "write_waveform_comparison_from_notebook_settings" in visualize.__all__
    assert "write_waveform_comparison_from_notebook_settings" in waveforms.__all__
    assert "write_large_run_waveform_comparison_from_outputs" in visualize.__all__
    assert "write_large_run_waveform_comparison_from_outputs" in waveforms.__all__
    assert "station_event_waveform_order_frame" in visualize.__all__
    assert "station_event_waveform_order_frame" in waveforms.__all__
    assert callable(waveforms.write_waveform_comparison_from_outputs)
    assert callable(waveforms.write_waveform_comparison_from_notebook_settings)
    assert callable(waveforms.station_event_waveform_order_frame)
    assert callable(waveforms.write_large_run_waveform_comparison_from_outputs)
    assert visualize.write_waveform_comparison_from_outputs is waveforms.write_waveform_comparison_from_outputs
    assert visualize.write_waveform_comparison_from_notebook_settings is waveforms.write_waveform_comparison_from_notebook_settings
    assert visualize.write_large_run_waveform_comparison_from_outputs is waveforms.write_large_run_waveform_comparison_from_outputs
