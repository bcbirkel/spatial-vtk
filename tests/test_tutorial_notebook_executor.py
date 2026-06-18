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
        ids = [str(cell.get("id", "")).strip() for cell in notebook.get("cells", [])]
        missing = [
            index
            for index, cell_id in enumerate(ids, start=1)
            if not cell_id
        ]
        duplicated = sorted({cell_id for cell_id in ids if cell_id and ids.count(cell_id) > 1})
        assert missing == [], f"{notebook_path.relative_to(repo_root)} missing cell ids: {missing}"
        assert duplicated == [], f"{notebook_path.relative_to(repo_root)} duplicate cell ids: {duplicated}"


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


def test_public_docs_describe_committed_tutorial_waveforms() -> None:
    """Fresh-checkout docs should not imply a separate tutorial waveform download."""

    repo_root = Path(__file__).resolve().parents[1]
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    configuration = (repo_root / "docs" / "configuration.rst").read_text(encoding="utf-8")
    data_formats = (repo_root / "docs" / "data_formats.rst").read_text(encoding="utf-8")
    index = (repo_root / "docs" / "index.rst").read_text(encoding="utf-8")

    combined = f"{readme}\n{configuration}\n{data_formats}\n{index}"
    assert "observed/synthetic NPZ waveform subset" in combined
    assert "No extra waveform download is needed" in combined
    assert "companion waveform bundle" not in combined
    assert "download or generate the larger observed" not in combined
    assert "ValidationToolkit_Workflow.png" not in combined
    assert "docs/_static/spatial_vtk_workflow.png" in readme
    assert "_static/spatial_vtk_workflow.png" in index
    assert 'record_coverage = load_output_table("record_coverage")' in configuration


def test_public_docs_describe_registered_table_formats() -> None:
    """Docs should explain CSV/Parquet defaults through registered output names."""

    repo_root = Path(__file__).resolve().parents[1]
    configuration = (repo_root / "docs" / "configuration.rst").read_text(encoding="utf-8")
    data_formats = (repo_root / "docs" / "data_formats.rst").read_text(encoding="utf-8")
    combined = f"{configuration}\n{data_formats}"

    assert "Registered table outputs also carry their default file format" in configuration
    assert "configured_output_registry_frame(kinds=(\"table\",), include_paths=True)" in configuration
    assert "Registered output names" in data_formats
    assert "default table format" in data_formats
    assert "load_output_table" in data_formats
    assert "write_output_table" in data_formats
    for key in (
        "qc_inventory_overlap",
        "observed_metric_inventory",
        "synthetic_metric_inventory",
        "metric_rows",
        "metrics_long",
        "metric_field",
        "station_bias",
        "corridors",
    ):
        assert key in combined


def test_qc_notebooks_use_public_workflow_helpers() -> None:
    """Tutorial notebooks should use public QC workflow helpers."""

    repo_root = Path(__file__).resolve().parents[1]
    standard_text = (repo_root / "docs" / "examples" / "step_02_quality_control.ipynb").read_text(encoding="utf-8")
    large_run_text = (
        repo_root / "docs" / "examples" / "large_run" / "step_02_large_run_quality_control.ipynb"
    ).read_text(encoding="utf-8")

    assert "run_qc_inventory_from_config(" in standard_text
    assert "write_qc_inventory_overlap_from_config(" in standard_text
    assert "run_qc_summary_workflow_from_config(" in standard_text
    assert "ingest_outputs.load_tables(" in standard_text
    assert "qc_figure_tables = qc_outputs.load_tables(" in standard_text
    assert "run_notebook_step_if_needed(" in large_run_text
    assert "from spatial_vtk.qc import (" in large_run_text
    assert "run_qc_inventory_from_config," in large_run_text
    assert "write_qc_inventory_overlap_from_config," in large_run_text
    assert "run_qc_summary_workflow_from_config," in large_run_text
    assert "qc_figure_tables = step_outputs.load_tables(" in large_run_text
    assert '"spatial_vtk.qc.run_qc_inventory_from_config"' not in large_run_text
    assert '"spatial_vtk.qc.write_qc_inventory_overlap_from_config"' not in large_run_text
    assert '"spatial_vtk.qc.run_qc_summary_workflow_from_config"' not in large_run_text
    for forbidden in (
        "build_waveform_qc_summary",
        "build_metric_qc_summary",
        "write_qc_inventory_overlap_from_full",
        "submit_qc_slurm_job",
        "slurm_settings_from_config",
        "from spatial_vtk.qc.build.slurm import",
    ):
        assert forbidden not in standard_text
    assert "from spatial_vtk.qc.build.slurm import" not in standard_text
    assert "from spatial_vtk.qc.build.slurm import" not in large_run_text


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


def test_tutorial_notebooks_use_output_group_objects_for_paths() -> None:
    """Workflow notebooks should use OutputGroup objects for grouped paths."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    assert notebooks
    forbidden = (
        "step_outputs[",
        "dashboard_paths[",
        "output_group_namespace",
        "output_group_status_frame",
    )
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            source = "".join(cell.get("source", []))
            matches = [pattern for pattern in forbidden if pattern in source]
            assert not matches, f"{notebook_path.relative_to(repo_root)} cell {index} uses {matches}"


def test_large_run_notebooks_bind_grouped_output_paths() -> None:
    """Large-run notebooks should avoid repeated ``x_path = step_outputs.x_path`` blocks."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples" / "large_run").glob("*.ipynb"))
    assert notebooks
    alias_pattern = re.compile(r"^\s*\w+_path\s*=\s*step_outputs\.\w+_path\b", re.MULTILINE)
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        if "output_group(" in source:
            assert "step_outputs.bind(globals())" in source, notebook_path.relative_to(repo_root)
        matches = alias_pattern.findall(source)
        assert not matches, f"{notebook_path.relative_to(repo_root)} repeats grouped path aliases: {matches}"


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


def test_tutorial_notebook_code_uses_python_package_apis_not_cli_calls() -> None:
    """Tutorial notebooks should drive workflows through package APIs, not shell commands."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    assert notebooks
    forbidden_snippets = (
        "import subprocess",
        "from subprocess",
        "subprocess.",
        "os.system(",
        "os.popen(",
        "run_or_submit_notebook_cli_command(",
        "write_notebook_cli_slurm_script(",
    )
    forbidden_line_patterns = (
        re.compile(r"^\s*![^\n]*\bsvtk\b", re.MULTILINE),
        re.compile(r"^\s*%%bash\b", re.MULTILINE),
        re.compile(r"\[\s*['\"]svtk['\"]\s*,"),
    )
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            matches = [snippet for snippet in forbidden_snippets if snippet in source]
            pattern_matches = [pattern.pattern for pattern in forbidden_line_patterns if pattern.search(source)]
            assert not matches and not pattern_matches, (
                f"{notebook_path.relative_to(repo_root)} cell {index} should use "
                f"spatial_vtk package APIs, not CLI/shell calls: {matches + pattern_matches}"
            )


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


def test_large_run_notebooks_use_output_group_helper() -> None:
    """Large-run notebooks should use the consolidated output group helper."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples" / "large_run").glob("*.ipynb"))
    assert notebooks
    for notebook_path in notebooks:
        source = notebook_path.read_text(encoding="utf-8")
        if notebook_path.name == "step_07_large_run_dashboards.ipynb":
            continue
        assert "output_group(" in source, notebook_path.relative_to(repo_root)
        assert "output_group_namespace" not in source, notebook_path.relative_to(repo_root)
        assert "output_group_status_frame" not in source, notebook_path.relative_to(repo_root)
        assert "vars(step_outputs)" not in source, notebook_path.relative_to(repo_root)


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

    assert "run_spatial_statistics_workflow_from_config(" in source
    assert 'metrics="paths.metric_figure_snapshot"' in source
    assert 'station_metadata="paths.site_metadata"' in source
    assert 'step_outputs = output_group("step_04_spatial", cfg=cfg)' in source
    assert "spatial_tables = step_outputs.load_tables(" in source
    assert 'metric_field = spatial_tables["metric_field"]' in source
    assert 'load_output_table("metric_field")' not in source
    assert "run_spatial_statistics_workflow(" not in source
    assert 'cfg.path("paths.metric_figure_snapshot")' not in source
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


def test_step05_uses_configured_geojson_workflow_and_table_io() -> None:
    """The GeoJSON tutorial should use config-backed package helpers for standard inputs."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "step_05_maps_and_figures.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "run_geojson_region_summary_workflow_from_config(" in source
    assert "from spatial_vtk.spatial import (" in source
    assert "read_config_table(\"paths.metric_figure_snapshot\")" in source
    assert 'metrics_table="paths.metric_figure_snapshot"' in source
    assert 'geojson_path="paths.region_geojson"' in source
    assert "from spatial_vtk.spatial.calculate import" not in source
    assert 'cfg.path("paths.metric_figure_snapshot")' not in source
    assert "read_table(metric_source_path)" not in source


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
    assert "write_score_trend_plots = metric_plot_context.write_score_trend_plots" in source
    assert "station_summary_for_item = metric_plot_context.station_summary_for_item" in source
    assert "station_period_summary_for_item = metric_plot_context.station_period_summary_for_item" in source
    assert "station_grid_for_item = metric_plot_context.station_grid_for_item" in source
    assert "station_model_summary_for_item = metric_plot_context.station_model_summary_for_item" in source
    assert "item_source_rows = metric_plot_context.item_source_rows" in source
    assert "source_df=item_source_rows(item)" in source
    assert "source_df_factory=item_source_rows" in source
    assert "source_df=item[\"df\"]" not in source
    assert "source_df_factory=lambda period_item" not in source
    assert "write_score_trend_plots(" in source
    assert "plot_score_trends" in source
    assert 'MAKE_SCORE_TRENDS = os.environ.get("SVTK_MAKE_SCORE_TRENDS", "0") == "1"' in source
    assert "Skipping optional GOF score trends. Set SVTK_MAKE_SCORE_TRENDS=1" in source
    assert "The main large-run figure suite uses `log2_residual`" in source
    assert 'PLOT_COMPARE_TO = os.environ.get("SVTK_FIGURE_COMPARE_TO") or None' in source
    assert 'PLOT_COMPARISON_TABLE = os.environ.get("SVTK_FIGURE_COMPARISON_TABLE", "0") == "1"' in source
    assert "compare_to=PLOT_COMPARE_TO" in source
    assert "table=PLOT_COMPARISON_TABLE" in source
    assert "SCORE_TREND_COLUMNS" in source
    assert "raw event-level rows used for the station summaries" in source
    assert 'STATION_AGGREGATION = os.environ.get("SVTK_STATION_AGGREGATION", "mean")' in source
    for base in ("station_metric_map", "residual_grid", "metric_by_model_map"):
        assert f'"{base}"' in source
    assert source.count("source_df=item_source_rows(item)") >= 3
    assert source.count("source_df_factory=item_source_rows") >= 2


def test_large_run_step04_uses_spatial_context_row_factories() -> None:
    """Large-run spatial figures should use package row factories, not notebook lambdas."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_04_large_run_spatial_statistics.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "run_notebook_step_if_needed(" in source
    assert "from spatial_vtk.spatial import (" in source
    assert "run_spatial_statistics_workflow_from_config," in source
    assert "run_spatial_derived_outputs_workflow_from_config," in source
    assert "display_output_table_previews(" in source
    assert '"spatial_vtk.spatial.run_spatial_statistics_workflow_from_config"' not in source
    assert '"spatial_vtk.spatial.run_spatial_derived_outputs_workflow_from_config"' not in source
    assert "run_or_submit_notebook_function(" not in source
    assert "run_or_submit_notebook_cli_command(" not in source
    assert '"svtk", "spatial"' not in source
    assert "should_rebuild_paths(" not in source
    assert "station_summary_for_item = spatial_figures.station_summary_for_item" in source
    assert "station_period_summary_for_item = spatial_figures.station_period_summary_for_item" in source
    assert "station_grid_for_item = spatial_figures.station_grid_for_item" in source
    assert "station_model_summary_for_item = spatial_figures.station_model_summary_for_item" in source
    assert "item_source_rows = spatial_figures.item_source_rows" in source
    assert "write_pca_summary_plots = spatial_figures.write_pca_summary_plots" in source
    assert "plot_pca_summary" in source
    assert "write_pca_summary_plots(" in source
    assert "PCA_MODE" in source
    assert "source_df=item_source_rows(item)" in source
    assert "source_df_factory=item_source_rows" in source
    assert "source_df=item[\"df\"]" not in source
    assert "source_df_factory=lambda period_item" not in source
    assert "spatial_figures.write_overview_plots(" in source
    assert "### Spatial Event-Centered Azimuthal Residuals" in source
    assert "### Spatial Event-Centered Polar Residuals" in source
    assert 'write_spatial_plot("spatial_correlogram"' not in source
    assert "plot_correlogram" not in source
    assert "preview_output_table(" not in source
    assert "for name, key in [" not in source
    assert "step_outputs.load_tables(" in source
    assert "load_output_table(" not in source


def test_large_run_step05_uses_package_functions_for_heavy_steps() -> None:
    """Large-run GeoJSON notebook should call package helpers, not CLI command cells."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_05_large_run_geojson_corridors.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "run_notebook_step_if_needed(" in source
    assert "from spatial_vtk.spatial import (" in source
    assert "run_geojson_region_summary_workflow_from_config," in source
    assert "run_boundary_corridor_workflow_from_config," in source
    assert "display_output_table_previews(" in source
    assert "ingest_outputs.load_tables(" in source
    assert "step_outputs.load_tables(" in source
    assert "load_output_table(" not in source
    assert '"spatial_vtk.spatial.run_geojson_region_summary_workflow_from_config"' not in source
    assert '"spatial_vtk.spatial.run_boundary_corridor_workflow_from_config"' not in source
    assert "geojson_readiness = step_outputs.readiness(" in source
    assert "corridor_readiness = step_outputs.readiness(" in source
    assert "geojson_readiness = output_readiness(" not in source
    assert "corridor_readiness = output_readiness(" not in source
    assert "run_or_submit_notebook_cli_command(" not in source
    assert '"svtk", "spatial"' not in source
    assert "should_rebuild_paths(" not in source
    assert "write_notebook_python_slurm_script" not in source
    assert "submit_notebook_slurm_script" not in source
    assert "run_geojson_region_summary_workflow(" not in source
    assert "run_boundary_corridor_workflow(" not in source
    assert "preview_output_table(" not in source


def test_step07_dashboard_notebook_uses_configured_export_helper() -> None:
    """Dashboard tutorial should keep dataset path plumbing inside package helpers."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "step_07_dashboards.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "write_configured_dashboard_datasets(" in source
    assert "launch_configured_metrics_dashboard(" in source
    assert "launch_configured_qc_dashboard(" in source
    assert "notebook_dashboard_launch_commands(" in source
    assert "dashboard_launch.metrics_launch_kwargs(show=True)" in source
    assert "dashboard_launch.qc_launch_kwargs(show=True)" in source
    assert "display(dashboard_launch.status_frame())" in source
    assert "Launch options:" not in source
    assert "server_port=notebook_overrides" not in source
    assert "write_dashboard_metric_dataset(" not in source
    assert "write_dashboard_summary_dataset(" not in source
    assert "metrics_outputs_command" not in source
    assert '"svtk", "metrics", "outputs"' not in source
    assert '"--metrics", str(metrics_path)' not in source
    assert '"--output-dir", str(Path(metrics_path).parent)' not in source


def test_large_run_step07_dashboard_driver_uses_config_defaults() -> None:
    """Large-run dashboard driver should use config-backed package helpers."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_07_large_run_dashboards.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "dashboard_status = dashboard_output_status_frame(cfg=cfg)" in source
    assert "dashboard_readiness_summary = dashboard_readiness_summary_frame(cfg=cfg, overwrite=OVERWRITE)" in source
    assert "display(dashboard_readiness_summary)" in source
    assert "dashboard_readiness = dashboard_output_readiness(cfg=cfg, overwrite=OVERWRITE)" in source
    assert "run_notebook_step_if_needed(" in source
    assert "write_configured_dashboard_datasets," in source
    assert '"spatial_vtk.visualize.dashboard.write_configured_dashboard_datasets"' not in source
    assert "launch_configured_metrics_dashboard(" in source
    assert "launch_configured_qc_dashboard(" in source
    assert "notebook_dashboard_launch_commands(" in source
    assert 'run_scenario=os.environ.get("SVTK_RUN_SCENARIO", "tutorial")' in source
    assert "dashboard_launch.metrics_launch_kwargs(show=True)" in source
    assert "dashboard_launch.qc_launch_kwargs(show=True)" in source
    assert "display(dashboard_launch.status_frame())" in source
    assert "Launch options:" not in source
    assert "server_port=dashboard_" not in source
    assert '"cfg": str(config_path)' in source
    assert "preview_output_table(\"metrics_long\", cfg=cfg" in source
    assert "dashboard_output_namespace" not in source
    assert "dashboard_paths" not in source
    assert "metrics_long_path" not in source
    assert "metrics_dashboard_root" not in source
    assert "dashboard_summary_root" not in source
    assert "qc_trace_summary_path" not in source
    assert "run_or_submit_notebook_cli_command(" not in source
    assert '"svtk", "metrics"' not in source
    assert '"--metrics", str(' not in source


def test_large_run_notebooks_display_output_readiness_tables() -> None:
    """Large-run driver cells should show named readiness status tables."""

    repo_root = Path(__file__).resolve().parents[1]
    required = {
        "large_run/step_01_large_run_ingest_and_prepare_data.ipynb": [
            "run_notebook_step_if_needed(",
        ],
        "large_run/step_02_large_run_quality_control.ipynb": ["run_notebook_step_if_needed("],
        "large_run/step_03_large_run_calculate_metrics.ipynb": [
            "run_notebook_step_if_needed(",
            "metric_slurm_submission_readiness(",
        ],
        "large_run/step_07_large_run_dashboards.ipynb": ["run_notebook_step_if_needed("],
    }
    for relative, snippets in required.items():
        notebook_path = repo_root / "docs" / "examples" / relative
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        missing = [snippet for snippet in snippets if snippet not in source]
        assert not missing, f"{notebook_path.relative_to(repo_root)} missing readiness displays: {missing}"


def test_large_run_grouped_steps_use_output_group_readiness() -> None:
    """Grouped large-run steps should keep path-readiness plumbing in OutputGroup."""

    repo_root = Path(__file__).resolve().parents[1]
    for relative in (
        "large_run/step_02_large_run_quality_control.ipynb",
        "large_run/step_03_large_run_calculate_metrics.ipynb",
        "large_run/step_04_large_run_spatial_statistics.ipynb",
        "large_run/step_05_large_run_geojson_corridors.ipynb",
    ):
        notebook_path = repo_root / "docs" / "examples" / relative
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        assert "step_outputs.readiness(" in source, notebook_path.relative_to(repo_root)
        assert "output_readiness(" not in source, notebook_path.relative_to(repo_root)
        assert "output_readiness," not in source, notebook_path.relative_to(repo_root)


def test_large_run_step03_uses_metric_batch_status_before_submit_and_merge() -> None:
    """Metric Slurm and merge cells should be gated by manifest batch completion."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_03_large_run_calculate_metrics.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "from spatial_vtk.metrics import metric_manifest_batch_status, metric_slurm_submission_readiness" in source
    assert "from spatial_vtk.metrics.workflow import metric_manifest_batch_status" not in source
    assert "batch_status = metric_manifest_batch_status(metric_manifest_path)" in source
    assert "slurm_readiness = metric_slurm_submission_readiness(batch_status, overwrite=OVERWRITE)" in source
    assert "All metric batch outputs already exist; skipping metric Slurm submission." in source
    assert '"incomplete_only": not OVERWRITE' in source
    assert '"overwrite_batches": OVERWRITE' in source
    assert "Metric batches are incomplete:" in source
    assert "sources=(metric_manifest_path, *batch_status.completed_outputs)" in source


def test_large_run_step03_uses_package_functions_for_heavy_steps() -> None:
    """Step 3 should call metric workflow helpers instead of CLI command cells."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_03_large_run_calculate_metrics.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "run_notebook_step_if_needed(" in source
    assert "run_or_submit_notebook_function(" not in source
    assert "from spatial_vtk.metrics import (" in source
    assert "build_metric_waveform_inventories_from_config," in source
    assert "plan_metric_tasks_from_config," in source
    assert "write_metrics_slurm_script_from_config," in source
    assert "merge_metric_batches_from_config," in source
    assert "write_metric_outputs_from_config," in source
    assert '"spatial_vtk.metrics.build_metric_waveform_inventories_from_config"' not in source
    assert '"spatial_vtk.metrics.plan_metric_tasks_from_config"' not in source
    assert '"spatial_vtk.metrics.write_metrics_slurm_script_from_config"' not in source
    assert '"spatial_vtk.metrics.merge_metric_batches_from_config"' not in source
    assert '"spatial_vtk.metrics.write_metric_outputs_from_config"' not in source
    assert "run_or_submit_notebook_cli_command(" not in source
    assert "submit_notebook_slurm_script" not in source
    assert "write_notebook_python_slurm_script" not in source
    assert '"svtk", "metrics"' not in source


def test_standard_step03_uses_configured_metric_helpers() -> None:
    """The standard metric tutorial should use package helpers, not hand-rolled workflow code."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "step_03_calculate_metrics.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "summarize_metric_snapshot_tasks_from_config(" in source
    assert "write_metric_outputs_from_config(" in source
    assert 'load_output_table("metrics_long")' in source
    assert "summarize_metric_tasks(" not in source
    assert "write_metric_outputs(" not in source
    assert "drop_duplicates().copy()" not in source
    assert 'read_config_table("paths.metric_figure_snapshot")' not in source


def test_large_run_step01_uses_package_functions_for_heavy_steps() -> None:
    """Step 1 should call package workflow helpers instead of CLI or inline worker code."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_01_large_run_ingest_and_prepare_data.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "run_notebook_step_if_needed(" in source
    assert "metadata_readiness = step_outputs.readiness(" in source
    assert "run_or_submit_notebook_function(" not in source
    assert "from spatial_vtk.io import (" in source
    assert "metadata_tables = step_outputs.load_tables(" in source
    assert "context_tables = step_outputs.load_tables(" in source
    assert "load_output_table(" not in source
    assert "prepare_metadata_tables_from_config," in source
    assert "preprocess_waveforms_from_config," in source
    assert "build_record_coverage_from_config," in source
    assert "prepare_station_metadata(" not in source
    assert "prepare_event_metadata(" not in source
    assert "prepare_event_station_table(" not in source
    assert "write_output_table(" not in source
    assert '"spatial_vtk.io.prepare_metadata_tables_from_config"' not in source
    assert '"spatial_vtk.io.preprocess_waveforms_from_config"' not in source
    assert '"spatial_vtk.io.build_record_coverage_from_config"' not in source
    assert "run_or_submit_notebook_cli_command(" not in source
    assert "write_notebook_python_slurm_script" not in source
    assert "submit_notebook_slurm_script" not in source
    assert "should_rebuild_paths(" not in source
    assert "preprocess_waveform_files(" not in source
    assert "build_record_coverage_table_from_trace_metadata(" not in source


def test_large_run_step02_uses_qc_availability_output() -> None:
    """The large-run QC notebook should render the standard availability sidecar."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_02_large_run_quality_control.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "step_outputs.bind(globals())" in source
    assert "availability_path," in source
    assert '"qc_availability": "availability_path"' in source
    assert 'qc_availability = qc_figure_tables["qc_availability"]' in source
    assert 'load_output_table("qc_availability")' not in source
    assert "plot_data_synthetic_availability(" in source
    assert "Observed/Synthetic Availability (Post-QC Trace Overlap)" in source


def test_large_run_step02_uses_package_functions_for_heavy_steps() -> None:
    """Step 2 should call package workflow helpers instead of CLI or inline worker code."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_02_large_run_quality_control.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "run_notebook_step_if_needed(" in source
    assert "run_or_submit_notebook_function(" not in source
    assert "from spatial_vtk.qc import (" in source
    assert "run_qc_inventory_from_config," in source
    assert "write_qc_inventory_overlap_from_config," in source
    assert "run_qc_summary_workflow_from_config," in source
    assert '"spatial_vtk.qc.run_qc_inventory_from_config"' not in source
    assert '"spatial_vtk.qc.write_qc_inventory_overlap_from_config"' not in source
    assert '"spatial_vtk.qc.run_qc_summary_workflow_from_config"' not in source
    assert "run_or_submit_notebook_cli_command(" not in source
    assert "write_notebook_python_slurm_script" not in source
    assert "submit_notebook_slurm_script" not in source
    assert "write_qc_slurm_script(" not in source


def test_large_run_optional_figure_cells_define_basemap_flag() -> None:
    """Large-run optional figure cells should not fail when figures are enabled."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = [
        repo_root / "docs" / "examples" / "large_run" / "step_01_large_run_ingest_and_prepare_data.ipynb",
        repo_root / "docs" / "examples" / "large_run" / "step_02_large_run_quality_control.ipynb",
    ]
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        assert 'ADD_BASEMAP = os.environ.get("SVTK_ADD_BASEMAP", "0") == "1"' in source
        assert "add_basemap=ADD_BASEMAP" in source


def test_large_run_step02_overlap_sidecar_has_separate_rebuild_gate() -> None:
    """Step 2 should rebuild full QC only from full-QC readiness inputs."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_02_large_run_quality_control.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "qc_readiness = step_outputs.readiness(" in source
    assert '("trace_qc_path", "qc_inventory_path")' in source
    assert 'inputs=("event_station_path",)' in source
    assert 'sources=("event_station_path",)' in source
    assert "run_notebook_step_if_needed(" in source
    assert "Full QC outputs are current; skipping QC Slurm submission." in source
    assert "should_rebuild_paths(trace_qc_path, qc_inventory_path, overwrite=OVERWRITE)" not in source
    assert "should_rebuild_paths(trace_qc_path, qc_inventory_path, qc_inventory_overlap_path" not in source
    assert "overlap_readiness = step_outputs.readiness(" in source
    assert "qc_readiness = output_readiness(" not in source
    assert "overlap_readiness = output_readiness(" not in source


def test_large_run_preprocessing_metadata_paths_are_package_backed() -> None:
    """Large-run notebooks should use preprocessing's public path helper."""

    repo_root = Path(__file__).resolve().parents[1]
    step_01 = repo_root / "docs" / "examples" / "large_run" / "step_01_large_run_ingest_and_prepare_data.ipynb"
    step_03 = repo_root / "docs" / "examples" / "large_run" / "step_03_large_run_calculate_metrics.ipynb"

    for notebook_path in (step_01, step_03):
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        assert "preprocessed_waveform_metadata_paths(config=cfg)" in source
        assert re.search(r"(?<!waveform_)preprocessing_manifest\.csv", source) is None
        assert 'outputs_root / "preprocessed_waveforms"' not in source


def test_step05_uses_geojson_preview_helper() -> None:
    """The map tutorial should use package helpers for GeoJSON feature previews."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "step_05_maps_and_figures.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "geojson_polygon_preview_table(" in source
    assert "output_group(\"step_01_ingest\", cfg=cfg).load_tables(" in source
    assert "output_group(\"step_05_geojson\", cfg=cfg).load_tables(" in source
    assert "load_output_table(" not in source
    assert "load_geojson_polygons(" not in source
    assert "region_preview = pd.DataFrame(" not in source


def test_step06_uses_comparison_eligible_output_table() -> None:
    """The plotting tutorial should reuse QC outputs instead of re-filtering metrics."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "step_06_additional_plotting_options.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "output_group(\"step_01_ingest\", cfg=cfg).load_tables(" in source
    assert "output_group(\"step_06_plotting\", cfg=cfg).load_tables(" in source
    assert "load_output_table(" not in source
    assert "from spatial_vtk.spatial import add_geojson_metadata_to_metrics" in source
    assert "from spatial_vtk.spatial.calculate import" not in source
    assert 'read_config_table("paths.metric_figure_snapshot")' in source
    assert 'cfg.path("paths.metric_figure_snapshot")' not in source
    assert "read_table(metric_source_path)" not in source
    assert "comparison_qc_status" not in source


def test_large_run_step06_uses_grouped_table_loading() -> None:
    """The large-run plotting notebook should read workflow outputs through OutputGroup."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_06_large_run_additional_plotting.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "step_outputs = output_group(\"step_06_plotting\")" in source
    assert "event_stations = step_outputs.load_tables(" in source
    assert "load_output_table(" not in source


def test_large_run_step03_metric_figures_are_auditable_station_aggregations() -> None:
    """Large-run metric figures should expose provenance for station summaries."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_03_large_run_calculate_metrics.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert 'PLOT_VALUE_COL = "log2_residual"' in source
    assert 'STATION_AGGREGATION = os.environ.get("SVTK_STATION_AGGREGATION", "mean")' in source
    assert "**METRIC_FIGURE_SIDECARS.kwargs(plural=True)" in source
    assert "station_aggregation=STATION_AGGREGATION" in source

    station_cells = [
        "".join(cell.get("source", []))
        for cell in notebook.get("cells", [])
        if any(
            marker in "".join(cell.get("source", []))
            for marker in (
                '"station_metric_map"',
                '"residual_grid"',
                '"metric_by_model_map"',
            )
        )
    ]
    station_source = "\n".join(station_cells)

    assert "station_summary_for_item(item, PLOT_VALUE_COL)" in station_source
    assert "station_period_summary_for_item(item, PLOT_VALUE_COL)" in station_source
    assert "station_grid_for_item(item, PLOT_VALUE_COL)" in station_source
    assert "station_model_summary_for_item(item, PLOT_VALUE_COL)" in station_source
    assert "source_df=item_source_rows(item)" in station_source
    assert "source_df_factory=item_source_rows" in station_source


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


def test_metric_and_spatial_notebooks_show_sidecar_status_frames() -> None:
    """Metric and spatial tutorials should expose package-native provenance review cells."""

    repo_root = Path(__file__).resolve().parents[1]
    expected = {
        "docs/examples/step_03_calculate_metrics.ipynb": "metric_sidecars.status_frame()",
        "docs/examples/step_04_spatial_statistics.ipynb": "spatial_sidecars.status_frame()",
        "docs/examples/large_run/step_03_large_run_calculate_metrics.ipynb": "METRIC_FIGURE_SIDECARS.status_frame()",
        "docs/examples/large_run/step_04_large_run_spatial_statistics.ipynb": "SPATIAL_FIGURE_SIDECARS.status_frame()",
    }
    for relative_path, call in expected.items():
        notebook = json.loads((repo_root / relative_path).read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        assert call in source


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
