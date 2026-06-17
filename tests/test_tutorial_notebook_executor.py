from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def _load_executor_module():
    """Load the tutorial notebook executor without requiring tools as a package."""

    path = Path(__file__).resolve().parents[1] / "tools" / "execute_tutorial_notebooks.py"
    spec = importlib.util.spec_from_file_location("execute_tutorial_notebooks", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_tutorial_notebook_warning_scan_detects_warning_like_outputs() -> None:
    """The tutorial verifier should flag warning-like cell output."""

    module = _load_executor_module()
    notebook = SimpleNamespace(
        cells=[
            {"outputs": [{"output_type": "stream", "text": "all clear"}]},
            {"outputs": [{"output_type": "stream", "text": "RuntimeWarning: example"}]},
            {"outputs": [{"output_type": "display_data", "data": {"text/plain": "Traceback (most recent call last)"}}]},
        ]
    )

    warnings = module.scan_notebook_outputs(notebook)

    assert [item["cell"] for item in warnings] == [1, 2]
    assert "RuntimeWarning" in warnings[0]["text"]


def test_tutorial_notebook_warning_scan_ignores_plain_warning_words() -> None:
    """Diagnostic text that names warnings should not fail clean notebooks."""

    module = _load_executor_module()
    notebook = SimpleNamespace(
        cells=[
            {"outputs": [{"output_type": "stream", "text": "warnings=0"}]},
            {"outputs": [{"output_type": "display_data", "data": {"text/plain": "No warnings detected"}}]},
            {"outputs": [{"output_type": "display_data", "data": {"text/plain": "Non-fatal workflow warnings"}}]},
            {"outputs": [{"output_type": "stream", "text": "WARNING: real logger warning"}]},
        ]
    )

    warnings = module.scan_notebook_outputs(notebook)

    assert [item["cell"] for item in warnings] == [3]


def test_tutorial_notebook_clean_guard_only_allows_tutorial_outputs(tmp_path: Path) -> None:
    """The clean helper should refuse paths outside outputs/tutorials."""

    module = _load_executor_module()
    allowed = tmp_path / "outputs" / "tutorials"
    allowed.mkdir(parents=True)

    module._clean_path(allowed)

    assert not allowed.exists()
    with pytest.raises(SystemExit, match="Refusing to clean"):
        module._clean_path(tmp_path / "outputs")


def test_tutorial_notebook_runtime_preflight_reports_missing_modules() -> None:
    """The notebook runner should explain missing runtime dependencies up front."""

    module = _load_executor_module()

    missing = module.missing_notebook_runtime_modules({"demo": "definitely_missing_svtk_module"})

    assert missing == ["demo"]
    with pytest.raises(SystemExit, match=r"demo.*\[notebooks,waveforms\]"):
        module.check_notebook_runtime({"demo": "definitely_missing_svtk_module"})


def test_tutorial_notebook_executor_isolates_runtime_dirs_and_quiets_kernel(monkeypatch, tmp_path: Path) -> None:
    """The notebook runner should avoid user-level runtime files and noisy kernel logs."""

    module = _load_executor_module()
    for key in (
        "JUPYTER_PLATFORM_DIRS",
        "MPLCONFIGDIR",
        "IPYTHONDIR",
        "JUPYTER_CONFIG_DIR",
        "JUPYTER_DATA_DIR",
        "JUPYTER_RUNTIME_DIR",
    ):
        monkeypatch.delenv(key, raising=False)

    tutorial_output = tmp_path / "outputs" / "tutorials"
    module.configure_notebook_runtime_environment(tutorial_output)

    assert os.environ["JUPYTER_PLATFORM_DIRS"] == "1"
    assert os.environ["MPLCONFIGDIR"] == str(tutorial_output / ".mplconfig")
    assert os.environ["IPYTHONDIR"] == str(tutorial_output / ".ipython")
    assert os.environ["JUPYTER_CONFIG_DIR"] == str(tutorial_output / ".jupyter_config")
    assert os.environ["JUPYTER_DATA_DIR"] == str(tutorial_output / ".jupyter_data")
    assert os.environ["JUPYTER_RUNTIME_DIR"] == str(tutorial_output / ".jupyter_runtime")
    assert "--IPKernelApp.log_level=ERROR" in module.KERNEL_EXTRA_ARGUMENTS


def test_tutorial_example_data_preflight_matches_committed_checkout() -> None:
    """The standard notebooks should have their committed example input files."""

    module = _load_executor_module()
    repo_root = Path(__file__).resolve().parents[1]

    assert module.missing_tutorial_example_data(repo_root) == []


def test_tutorial_example_data_preflight_runs_before_clean(tmp_path: Path, monkeypatch) -> None:
    """Missing example data should be reported before tutorial outputs are cleaned."""

    module = _load_executor_module()
    repo = tmp_path / "repo"
    examples = repo / "docs" / "examples"
    examples.mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='spatial-vtk'\n", encoding="utf-8")
    notebook = examples / "step_01.ipynb"
    notebook.write_text("{}", encoding="utf-8")
    marker = repo / "outputs" / "tutorials" / "keep.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("do not delete", encoding="utf-8")
    monkeypatch.setattr(module, "check_notebook_runtime", lambda: None)

    with pytest.raises(SystemExit, match="Tutorial example data is incomplete"):
        module.main(["--repo-root", str(repo), "--notebook", str(notebook), "--clean"])

    assert marker.exists()


def test_tutorial_source_bootstrap_helper_works_from_repo_and_examples_dir(monkeypatch) -> None:
    """The notebook bootstrap helper should support fresh source checkouts."""

    repo_root = Path(__file__).resolve().parents[1]
    helper_path = repo_root / "docs" / "examples" / "_source_bootstrap.py"
    spec = importlib.util.spec_from_file_location("_source_bootstrap_test", helper_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    for start in (repo_root, repo_root / "docs" / "examples"):
        monkeypatch.chdir(start)
        found = module.use_source_checkout()
        assert found == repo_root
        assert str(repo_root / "src") in sys.path


def test_tutorial_notebooks_use_shared_source_bootstrap() -> None:
    """Tutorial notebooks should not duplicate source-checkout path plumbing."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    assert notebooks
    forbidden = (
        "repo_root = next(",
        "src_path = repo_root",
        "src_path = repo_root /",
        "str(src_path)",
        "import sys",
    )
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        assert "_source_bootstrap.py" in source, f"{notebook_path.relative_to(repo_root)}"
        assert "runpy.run_path(str(_bootstrap))" in source, f"{notebook_path.relative_to(repo_root)}"
        matches = [pattern for pattern in forbidden if pattern in source]
        assert not matches, f"{notebook_path.relative_to(repo_root)} embeds bootstrap plumbing: {matches}"


def test_tutorial_notebooks_have_stable_cell_ids() -> None:
    """Committed notebooks should not trigger nbformat cell-id warnings."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    assert notebooks
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        missing = [
            index
            for index, cell in enumerate(notebook.get("cells", []), start=1)
            if not str(cell.get("id", "")).strip()
        ]
        assert missing == [], f"{notebook_path.relative_to(repo_root)} missing cell ids: {missing}"


def test_tutorial_notebook_preflight_runs_before_clean(tmp_path: Path, monkeypatch) -> None:
    """A missing notebook runtime should not erase existing tutorial outputs."""

    module = _load_executor_module()
    repo = tmp_path / "repo"
    examples = repo / "docs" / "examples"
    examples.mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='spatial-vtk'\n", encoding="utf-8")
    notebook = examples / "step_01.ipynb"
    notebook.write_text("{}", encoding="utf-8")
    marker = repo / "outputs" / "tutorials" / "keep.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("do not delete", encoding="utf-8")
    monkeypatch.setattr(module, "check_notebook_runtime", lambda: (_ for _ in ()).throw(SystemExit("missing runtime")))

    with pytest.raises(SystemExit, match="missing runtime"):
        module.main(["--repo-root", str(repo), "--notebook", str(notebook), "--clean"])

    assert marker.exists()


def test_ci_runs_clean_tutorial_notebooks_with_notebook_extras() -> None:
    """CI should prove source-checkout tutorial notebooks run from example data."""

    repo_root = Path(__file__).resolve().parents[1]
    workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    docs_workflow = (repo_root / ".github" / "workflows" / "docs.yml").read_text(encoding="utf-8")

    install = 'python -m pip install -e ".[validation,docs,dashboard,notebooks,waveforms]"'
    assert install in workflow
    assert install in docs_workflow
    assert "python tools/execute_tutorial_notebooks.py --clean --include-large-run" in workflow


def test_examples_docs_advertise_fresh_checkout_large_run_gate_and_sidecars() -> None:
    """Public tutorial docs should expose the clean-run and figure-audit contract."""

    repo_root = Path(__file__).resolve().parents[1]
    examples_index = (repo_root / "docs" / "examples" / "index.rst").read_text(encoding="utf-8")
    large_run_readme = (repo_root / "docs" / "examples" / "large_run" / "README.md").read_text(encoding="utf-8")
    combined = f"{examples_index}\n{large_run_readme}"

    assert "python tools/execute_tutorial_notebooks.py --clean --include-large-run" in combined
    assert "SVTK_FIGURE_SIDECARS=1" in combined
    assert "SVTK_FIGURE_SIDECAR_ROWS=all" in combined
    assert "*.source.csv" in combined
    assert "pre-aggregation" in combined
    assert "committed example data" in combined


def test_tutorial_notebook_executor_can_include_large_run_notebooks() -> None:
    """The clean notebook gate should be able to cover scalable large-run tutorials."""

    module = _load_executor_module()
    repo_root = Path(__file__).resolve().parents[1]

    standard = module._resolve_notebooks(repo_root, None)
    all_tutorials = module._resolve_notebooks(repo_root, None, include_large_run=True)
    large_only = module._resolve_notebooks(repo_root, None, large_run_only=True)

    assert len(standard) == len(module.STANDARD_TUTORIAL_NOTEBOOKS)
    assert len(large_only) == len(module.LARGE_RUN_TUTORIAL_NOTEBOOKS)
    assert len(all_tutorials) == len(module.STANDARD_TUTORIAL_NOTEBOOKS) + len(module.LARGE_RUN_TUTORIAL_NOTEBOOKS)
    assert all("large_run" not in str(path) for path in standard)
    assert all("large_run" in str(path) for path in large_only)
    assert all_tutorials[: len(standard)] == standard
    assert all_tutorials[len(standard) :] == large_only


def test_committed_tutorial_notebooks_do_not_embed_private_paths() -> None:
    """Tutorial notebooks should be runnable from a fresh public checkout."""

    repo_root = Path(__file__).resolve().parents[1]
    private_tokens = tuple(
        "".join(parts)
        for parts in (
            ("/pro", "ject2/"),
            ("jvi", "dale"),
            ("bir", "kel@"),
            ("/Us", "ers/", "bcb", "irkel"),
            ("CA", "RC"),
            ("ca", "rc"),
            ("dis", "covery"),
            ("h", "pc"),
            ("geo", "sys"),
            ("on", "demand"),
        )
    )
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    assert notebooks
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            source = "".join(cell.get("source", []))
            matches = [token for token in private_tokens if token in source]
            assert not matches, f"{notebook_path.relative_to(repo_root)} cell {index} contains {matches}"


def test_tutorial_notebooks_use_grouped_output_paths() -> None:
    """Workflow notebooks should avoid inline output-path plumbing."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    assert notebooks
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            source = "".join(cell.get("source", []))
            assert "resolve_output_path(" not in source, f"{notebook_path.relative_to(repo_root)} cell {index}"


def test_tutorial_notebooks_use_output_namespaces_instead_of_dict_path_lookups() -> None:
    """Workflow notebooks should use attribute namespaces for grouped paths."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    assert notebooks
    forbidden = ("step_outputs[", "dashboard_paths[")
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            source = "".join(cell.get("source", []))
            matches = [pattern for pattern in forbidden if pattern in source]
            assert not matches, f"{notebook_path.relative_to(repo_root)} cell {index} uses {matches}"


def test_tutorial_notebooks_use_table_helpers_for_file_reads() -> None:
    """Tutorial notebooks should centralize table-format handling in package helpers."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    assert notebooks
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            source = "".join(cell.get("source", []))
            assert "pd.read_" not in source, f"{notebook_path.relative_to(repo_root)} cell {index}"


def test_large_run_notebooks_describe_configured_output_locations() -> None:
    """Large-run notebooks should not teach one machine-specific run layout."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples" / "large_run").glob("*.ipynb"))
    assert notebooks
    forbidden = ("runs/outputs", "runs/spatial_vtk_config.yaml")
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        matches = [pattern for pattern in forbidden if pattern in source]
        assert not matches, f"{notebook_path.relative_to(repo_root)} contains fixed run paths: {matches}"


def test_tutorial_notebooks_use_public_plot_and_map_imports() -> None:
    """Tutorial notebooks should teach stable public plotting imports."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    forbidden = (
        "from spatial_vtk.metrics.plot.",
        "from spatial_vtk.spatial.map.",
        "from spatial_vtk.spatial.plot.",
    )
    assert notebooks
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            source = "".join(cell.get("source", []))
            matches = [pattern for pattern in forbidden if pattern in source]
            assert not matches, f"{notebook_path.relative_to(repo_root)} cell {index} uses {matches}"


def test_step04_uses_spatial_workflow_instead_of_recomputing_tables() -> None:
    """The spatial tutorial should use the package workflow for standard tables."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "step_04_spatial_statistics.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "run_spatial_statistics_workflow(" in source
    for helper in (
        "build_metric_field",
        "center_field_by_event",
        "compute_global_morans_i",
        "run_residual_feature_clustering",
        "compute_pca_spatial_modes",
        "bootstrap_contrast_table",
        "write_output_tables(",
    ):
        assert helper not in source


def test_step03_station_map_uses_package_aggregation_and_source_sidecar() -> None:
    """The metric tutorial should not hand-roll station aggregation in notebook code."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "step_03_calculate_metrics.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "MetricFigureContext.from_frame(" in source
    assert "station_summary_for_map(" in source
    assert "source_df=station_pga_source" in source
    assert ".groupby([" not in source


def test_large_run_step03_documents_metric_source_sidecars() -> None:
    """Large-run metric figures should document plotted rows and source rows."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_03_large_run_calculate_metrics.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "write_psa_period_sheet = metric_plot_context.write_psa_period_sheet" in source
    assert "station_summary_for_map = metric_plot_context.station_summary_for_map" in source
    assert "station_period_summary_for_map = metric_plot_context.station_period_summary_for_map" in source
    assert "source_df=item[\"df\"]" in source
    assert "source_df_factory=lambda period_item: period_item[\"df\"]" in source
    assert "raw event-level rows used for the station summaries" in source


def test_large_run_notebooks_display_output_readiness_tables() -> None:
    """Large-run driver cells should show named readiness status tables."""

    repo_root = Path(__file__).resolve().parents[1]
    required = {
        "large_run/step_02_large_run_quality_control.ipynb": ["overlap_readiness.status_frame()"],
        "large_run/step_03_large_run_calculate_metrics.ipynb": [
            "inventory_readiness.status_frame()",
            "manifest_readiness.status_frame()",
            "merge_readiness.status_frame()",
        ],
        "large_run/step_07_large_run_dashboards.ipynb": ["dashboard_readiness.status_frame()"],
    }
    for relative, snippets in required.items():
        notebook_path = repo_root / "docs" / "examples" / relative
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        missing = [snippet for snippet in snippets if snippet not in source]
        assert not missing, f"{notebook_path.relative_to(repo_root)} missing readiness displays: {missing}"


def test_step05_uses_geojson_preview_helper() -> None:
    """The map tutorial should use package helpers for GeoJSON feature previews."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "step_05_maps_and_figures.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "geojson_polygon_preview_table(" in source
    assert "load_geojson_polygons(" not in source
    assert "region_preview = pd.DataFrame(" not in source


def test_step06_uses_comparison_eligible_output_table() -> None:
    """The plotting tutorial should reuse QC outputs instead of re-filtering metrics."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "step_06_additional_plotting_options.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert 'load_output_table("comparison_eligible_records")' in source
    assert "comparison_qc_status" not in source


def test_tutorial_figure_sidecar_calls_include_directory_control() -> None:
    """Notebook figure sidecar calls should honor configured sidecar directories."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    assert notebooks
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            source = "".join(cell.get("source", []))
            if "write_sidecar=" in source:
                assert "sidecar_dir=" in source, f"{notebook_path.relative_to(repo_root)} cell {index}"


def test_tutorial_figure_sidecar_calls_do_not_hardcode_figure_sidecar_dirs() -> None:
    """Notebook sidecar calls should use notebook_figure_sidecar_settings directories."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    assert notebooks
    forbidden = (
        'sidecar_dir=figures_dir / "sidecars"',
        'sidecar_dir=figures_dir / "metrics" / "sidecars"',
        "sidecar_dir=figures_dir / 'sidecars'",
        "sidecar_dir=figures_dir / 'metrics' / 'sidecars'",
    )
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            source = "".join(cell.get("source", []))
            matches = [pattern for pattern in forbidden if pattern in source]
            assert not matches, f"{notebook_path.relative_to(repo_root)} cell {index} hardcodes {matches}"


def test_tutorial_notebooks_use_sidecar_settings_kwargs() -> None:
    """Notebook figure sidecar calls should not expand settings into local variables."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    assert notebooks
    forbidden_names = (
        "write_context_figure_sidecars",
        "context_figure_sidecar_rows",
        "context_figure_sidecar_dir",
        "write_qc_figure_sidecars",
        "qc_figure_sidecar_rows",
        "qc_figure_sidecar_dir",
        "write_metric_figure_sidecars",
        "metric_figure_sidecar_rows",
        "metric_figure_sidecar_dir",
        "write_spatial_figure_sidecars",
        "spatial_figure_sidecar_rows",
        "spatial_figure_sidecar_dir",
        "write_waveform_figure_sidecars",
        "waveform_figure_sidecar_rows",
        "waveform_figure_sidecar_dir",
        "WRITE_CONTEXT_FIGURE_SIDECARS",
        "CONTEXT_FIGURE_SIDECAR_ROWS",
        "CONTEXT_FIGURE_SIDECAR_DIR",
        "WRITE_QC_FIGURE_SIDECARS",
        "QC_FIGURE_SIDECAR_ROWS",
        "QC_FIGURE_SIDECAR_DIR",
        "WRITE_FIGURE_SIDECARS",
        "FIGURE_SIDECAR_ROWS",
        "WRITE_SPATIAL_FIGURE_SIDECARS",
        "SPATIAL_FIGURE_SIDECAR_ROWS",
        "SPATIAL_FIGURE_SIDECAR_DIR",
        "WRITE_REGION_FIGURE_SIDECARS",
        "REGION_FIGURE_SIDECAR_ROWS",
        "REGION_FIGURE_SIDECAR_DIR",
        "WRITE_WAVEFORM_FIGURE_SIDECARS",
        "WAVEFORM_FIGURE_SIDECAR_ROWS",
        "WAVEFORM_FIGURE_SIDECAR_DIR",
    )
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        matches = [
            name
            for name in forbidden_names
            if re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", source)
        ]
        assert not matches, f"{notebook_path.relative_to(repo_root)} expands sidecar settings: {matches}"


def test_public_saved_plot_functions_expose_sidecar_controls() -> None:
    """Saved plotting helpers should let users write row-provenance sidecars."""

    repo_root = Path(__file__).resolve().parents[1]
    roots = (
        repo_root / "src" / "spatial_vtk" / "metrics" / "plot",
        repo_root / "src" / "spatial_vtk" / "spatial" / "plot",
        repo_root / "src" / "spatial_vtk" / "spatial" / "map",
        repo_root / "src" / "spatial_vtk" / "visualize" / "context",
        repo_root / "src" / "spatial_vtk" / "visualize" / "qc",
        repo_root / "src" / "spatial_vtk" / "visualize" / "waveforms",
    )
    missing: list[str] = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, ast.FunctionDef) or not node.name.startswith("plot_"):
                    continue
                arguments = [arg.arg for arg in node.args.args + node.args.kwonlyargs]
                if not {"savefig", "output_path", "outpath"} & set(arguments):
                    continue
                absent = [name for name in ("write_sidecar", "sidecar_rows", "sidecar_dir") if name not in arguments]
                if absent:
                    missing.append(f"{path.relative_to(repo_root)}:{node.lineno}:{node.name} missing {absent}")

    assert missing == []
