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


def test_tutorial_notebook_runtime_preflight_reports_unsupported_python() -> None:
    """The notebook runner should report unsupported Python before dependency imports."""

    module = _load_executor_module()

    assert module.SUPPORTED_TUTORIAL_PYTHON_RANGE == ">=3.10,<3.14"
    assert module.tutorial_python_version_supported((3, 10, 0)) is True
    assert module.tutorial_python_version_supported((3, 13, 9)) is True
    assert module.tutorial_python_version_supported((3, 9, 18)) is False
    assert module.tutorial_python_version_supported((3, 14, 0)) is False
    assert module.python_version_label((3, 9, 18)) == "3.9.18"
    with pytest.raises(SystemExit) as excinfo:
        module.check_tutorial_python_version((3, 9, 18))
    message = str(excinfo.value)
    assert "Spatial-VTK tutorial notebooks require Python >=3.10,<3.14" in message
    assert "Current Python executable:" in message
    assert "Current Python version: 3.9.18" in message
    assert "Activate a supported environment before installing tutorial dependencies" in message
    assert module.SOURCE_CHECKOUT_TUTORIAL_CONDA_COMMAND in message
    assert module.SOURCE_CHECKOUT_TUTORIAL_INSTALL_COMMAND in message
    assert module.current_python_tutorial_install_command() not in message


def test_tutorial_notebook_runtime_preflight_reports_missing_modules(monkeypatch) -> None:
    """The notebook runner should explain missing runtime dependencies up front."""

    module = _load_executor_module()

    missing = module.missing_notebook_runtime_modules({"demo": "definitely_missing_svtk_module"})

    assert missing == ["demo"]
    expected_install = 'python -m pip install -e ".[validation,docs,dashboard,notebooks,waveforms]"'
    assert module.SOURCE_CHECKOUT_TUTORIAL_INSTALL_COMMAND == expected_install
    assert module.SOURCE_CHECKOUT_TUTORIAL_CONDA_COMMAND == "conda env create -f svtk_environment.yaml"
    assert (
        module.SOURCE_CHECKOUT_TUTORIAL_RUNTIME_CHECK_COMMAND
        == "MPLCONFIGDIR=/tmp/mplconfig_svtk "
        "python tools/execute_tutorial_notebooks.py --runtime-check-only --include-large-run"
    )
    assert sys.executable in module.current_python_tutorial_install_command()
    assert sys.executable in module.current_python_tutorial_runtime_check_command()
    assert module.current_python_tutorial_runtime_check_command().startswith("MPLCONFIGDIR=/tmp/mplconfig_svtk ")
    monkeypatch.setattr(module, "check_tutorial_python_version", lambda: None)
    with pytest.raises(SystemExit) as excinfo:
        module.check_notebook_runtime({"demo": "definitely_missing_svtk_module"})
    message = str(excinfo.value)
    assert "Missing tutorial runtime modules: demo" in message
    assert "Jupyter, mapping, dashboard, and waveform readers" in message
    assert f"Current Python executable: {sys.executable}" in message
    assert "Make sure the install command targets this environment" in message
    assert module.SOURCE_CHECKOUT_TUTORIAL_INSTALL_COMMAND in message
    assert module.SOURCE_CHECKOUT_TUTORIAL_RUNTIME_CHECK_COMMAND in message
    assert module.current_python_tutorial_install_command() in message
    assert module.current_python_tutorial_runtime_check_command() in message
    assert module.SOURCE_CHECKOUT_TUTORIAL_CONDA_COMMAND in message


def test_tutorial_notebook_runtime_preflight_includes_package_runtime_modules() -> None:
    """The runtime check should cover more than the Jupyter kernel packages."""

    module = _load_executor_module()

    assert set(module.NOTEBOOK_RUNTIME_MODULES) == {
        "spatial_vtk",
        "nbformat",
        "nbclient",
        "ipykernel",
        "IPython",
        "branca",
        "contextily",
        "folium",
        "geopandas",
        "gmprocess",
        "h5py",
        "matplotlib",
        "numpy",
        "obspy",
        "pandas",
        "plotly",
        "pyarrow",
        "pyasdf",
        "pyproj",
        "PyYAML",
        "rasterio",
        "scikit-learn",
        "scipy",
        "shapely",
        "statsmodels",
        "streamlit",
        "streamlit-folium",
    }
    assert module.NOTEBOOK_RUNTIME_MODULES["spatial_vtk"] == "spatial_vtk"
    assert module.NOTEBOOK_RUNTIME_MODULES["pandas"] == "pandas"
    assert module.NOTEBOOK_RUNTIME_MODULES["PyYAML"] == "yaml"
    assert module.NOTEBOOK_RUNTIME_MODULES["gmprocess"] == "gmprocess"
    assert module.NOTEBOOK_RUNTIME_MODULES["h5py"] == "h5py"
    assert module.NOTEBOOK_RUNTIME_MODULES["obspy"] == "obspy"
    assert module.NOTEBOOK_RUNTIME_MODULES["plotly"] == "plotly"
    assert module.NOTEBOOK_RUNTIME_MODULES["streamlit-folium"] == "streamlit_folium"


def test_tutorial_notebook_runtime_preflight_supports_source_checkouts(monkeypatch) -> None:
    """Runtime checks should find spatial_vtk from src without requiring editable install state."""

    module = _load_executor_module()
    repo_root = Path(__file__).resolve().parents[1]
    src_text = str(repo_root / "src")
    monkeypatch.setattr(sys, "path", [item for item in sys.path if item != src_text])

    module.configure_source_checkout_imports(repo_root)

    assert sys.path[0] == src_text
    assert importlib.util.find_spec("spatial_vtk") is not None


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


def test_tutorial_example_data_preflight_reports_malformed_event_station_table(tmp_path: Path) -> None:
    """Malformed tutorial event-station metadata should fail before notebook execution."""

    module = _load_executor_module()
    records_dir = tmp_path / "data" / "examples" / "example_five_event_subset" / "metadata"
    records_dir.mkdir(parents=True)
    records_path = records_dir / "selected_event_stations.csv"
    records_path.write_text("event_id,network\nci1,CI\n", encoding="utf-8")

    missing = module.missing_tutorial_example_data(tmp_path)

    assert (
        "data/examples/example_five_event_subset/metadata/selected_event_stations.csv "
        "(missing columns: station)"
    ) in missing


def test_tutorial_example_data_preflight_reports_blank_event_station_values(tmp_path: Path) -> None:
    """Blank event-station identifiers should not silently skip waveform checks."""

    module = _load_executor_module()
    records_dir = tmp_path / "data" / "examples" / "example_five_event_subset" / "metadata"
    records_dir.mkdir(parents=True)
    records_path = records_dir / "selected_event_stations.csv"
    records_path.write_text("event_id,station\nci1,\n,STA1\n", encoding="utf-8")

    missing = module.missing_tutorial_example_data(tmp_path)

    assert (
        "data/examples/example_five_event_subset/metadata/selected_event_stations.csv "
        "(row 2 missing values: station)"
    ) in missing
    assert (
        "data/examples/example_five_event_subset/metadata/selected_event_stations.csv "
        "(row 3 missing values: event_id)"
    ) in missing


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


def test_tutorial_notebooks_use_stable_config_import_surface() -> None:
    """Tutorial notebooks should import notebook helpers from spatial_vtk.config."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    assert notebooks
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        assert "from spatial_vtk.config.notebook import" not in source, f"{notebook_path.relative_to(repo_root)}"
        assert 'os.environ.setdefault("LOKY_MAX_CPU_COUNT"' not in source, f"{notebook_path.relative_to(repo_root)}"


def test_standard_tutorial_notebooks_use_notebook_run_context() -> None:
    """Standard tutorial notebooks should use the same package run-context helper as large-run notebooks."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").glob("step_*.ipynb"))
    assert notebooks
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        assert "notebook_run_context(" in source, f"{notebook_path.relative_to(repo_root)}"
        assert "SpatialVTKConfig" not in source, f"{notebook_path.relative_to(repo_root)}"
        assert "from spatial_vtk.config import find_repo_root" not in source, f"{notebook_path.relative_to(repo_root)}"
        assert 'cfg.path("outputs.figures")' not in source, f"{notebook_path.relative_to(repo_root)}"


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


def test_tutorial_notebooks_are_committed_without_execution_state() -> None:
    """Committed notebooks should start clean for fresh-checkout users."""

    module = _load_executor_module()
    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    assert notebooks
    dirty = []
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        metadata = notebook.get("metadata", {})
        if isinstance(metadata, dict):
            for key in module.NOTEBOOK_CONTRACT_FORBIDDEN_METADATA_KEYS:
                if key in metadata:
                    dirty.append(f"{notebook_path.relative_to(repo_root)} has saved metadata key {key}")
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            cell_label = f"{notebook_path.relative_to(repo_root)} cell {index}"
            metadata = cell.get("metadata", {})
            if isinstance(metadata, dict):
                for key in module.NOTEBOOK_CONTRACT_FORBIDDEN_CELL_METADATA_KEYS:
                    if key in metadata:
                        dirty.append(f"{cell_label} has saved cell metadata key {key}")
            if cell.get("cell_type") != "code":
                continue
            if cell.get("execution_count") is not None:
                dirty.append(f"{cell_label} has execution_count")
            if cell.get("outputs"):
                dirty.append(f"{cell_label} has saved outputs")

    assert dirty == []


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


def test_tutorial_notebook_contract_preflight_detects_brittle_cells(tmp_path: Path) -> None:
    """The public runner should catch source-level notebook contract violations."""

    module = _load_executor_module()
    repo = tmp_path / "repo"
    examples = repo / "docs" / "examples"
    examples.mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='spatial-vtk'\n", encoding="utf-8")
    notebook = examples / "step_01.ipynb"
    notebook.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "id": "undocumented-section",
                        "metadata": {},
                        "source": ["## Run Expensive Work\n", "\n", "Do the step.\n"],
                    },
                    {
                        "cell_type": "code",
                        "id": "bad-cell",
                        "execution_count": 1,
                        "metadata": {"execution": {"iopub.status.busy": "stale"}},
                        "outputs": [{"output_type": "stream", "name": "stdout", "text": "stale"}],
                        "source": [
                            "import subprocess\n",
                            "!svtk metrics plan\n",
                            "get_ipython().system('svtk metrics plan')\n",
                            "from spatial_vtk.metrics.plot.periods import plot_period_spectra\n",
                            "import spatial_vtk.metrics.plot.periods\n",
                            "from spatial_vtk.config.metrics import metrics_settings_from_config\n",
                            "from spatial_vtk.config.notebook import notebook_run_context\n",
                            "from spatial_vtk.metrics.workflow.execution import run_manifest_batch\n",
                            "from spatial_vtk.qc.build.workflow import run_qc_inventory_from_config\n",
                            "from spatial_vtk.spatial.calculate.workflow import run_spatial_summaries_from_config\n",
                            "from spatial_vtk.io.preprocessing import preprocess_waveform_files\n",
                            "import spatial_vtk.spatial.map.metrics as metric_maps\n",
                            "repo_root = Path('../')\n",
                            "alternate_repo_root = Path(\"..\")\n",
                            "pathlib_repo_root = pathlib.Path('../docs')\n",
                            "metrics = pd.read_csv('/Users/example/project/metrics.csv')\n",
                            "path = resolve_output_path('metrics_long')\n",
                            "write_output_table('metrics_long', metrics)\n",
                            "write_output_tables(metric_field=metrics)\n",
                            "metrics.to_csv('metrics.csv')\n",
                            "metrics.to_parquet('metrics.parquet')\n",
                            "subprocess.run(['svtk', 'metrics', 'plan'])\n",
                            "outputs = output_group_namespace('step_03_metrics')\n",
                            "step_outputs['metrics_long_path']\n",
                            "subset = metrics.loc[metrics['metric'].eq('PGA')]\n",
                            "joined = subset.merge(metrics, on='event_id')\n",
                            "layout = 'runs/outputs/tables'\n",
                            "def local_helper():\n",
                            "    return joined\n",
                            "class LocalNotebookHelper:\n",
                            "    pass\n",
                        ],
                    },
                    {
                        "cell_type": "code",
                        "id": "string-function-target",
                        "execution_count": None,
                        "metadata": {},
                        "outputs": [],
                        "source": [
                            "run_notebook_step_if_needed(\n",
                            "    context,\n",
                            "    readiness,\n",
                            "    \"spatial_vtk.qc.run_qc_inventory_from_config\",\n",
                            "    script_name=\"qc.slurm\",\n",
                            "    job_name=\"svtk-qc\",\n",
                            ")\n",
                        ],
                    }
                ],
                "metadata": {"widgets": {"application/vnd.jupyter.widget-state+json": {}}},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )

    violations = module.tutorial_notebook_contract_violations([notebook], repo_root=repo)

    combined = "\n".join(violations)
    assert "missing shared source-checkout bootstrap cell" in combined
    assert "committed execution_count should be empty" in combined
    assert "committed outputs should be empty" in combined
    assert "committed cell metadata should not contain saved runtime state keys: execution" in combined
    assert "committed notebook metadata should not contain saved runtime state keys: widgets" in combined
    assert "markdown section should include Purpose: and Outputs:" in combined
    assert "import subprocess" in combined
    assert "forbidden shell/CLI workflow pattern" in combined
    assert "get_ipython().system(" in combined
    assert "pd.read_" in combined
    assert "resolve_output_path(" in combined
    assert "write_output_table(" in combined
    assert "write_output_tables(" in combined
    assert ".to_csv(" in combined
    assert ".to_parquet(" in combined
    assert "subprocess.run(" in combined
    assert "from spatial_vtk.metrics.plot." in combined
    assert "Path('../')" in combined
    assert "Path('..')" in combined
    assert "Path('../docs')" in combined
    assert "parent-directory Path(" in combined
    assert "forbidden implementation import pattern" in combined
    assert "metrics" in combined
    assert "notebook" in combined
    assert "workflow" in combined
    assert "qc" in combined
    assert "build" in combined
    assert "spatial" in combined
    assert "calculate" in combined
    assert "io" in combined
    assert "preprocessing" in combined
    assert "spatial_vtk\\.spatial\\.map\\." in combined
    assert "output_group_namespace" in combined
    assert "step_outputs[" in combined
    assert ".loc[" in combined
    assert ".merge(" in combined
    assert "runs/outputs" in combined
    assert "notebook-local function 'local_helper' should move to an importable package helper" in combined
    assert "notebook-local class 'LocalNotebookHelper' should move to an importable package helper" in combined
    assert "should receive an imported package callable" in combined
    assert "spatial_vtk.qc.run_qc_inventory_from_config" in combined
    assert "user-specific path or address" in combined


def test_tutorial_notebook_contract_preflight_runs_before_clean(tmp_path: Path) -> None:
    """Contract failures should not erase existing tutorial outputs."""

    module = _load_executor_module()
    repo = tmp_path / "repo"
    examples = repo / "docs" / "examples"
    examples.mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='spatial-vtk'\n", encoding="utf-8")
    notebook = examples / "step_01.ipynb"
    notebook.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "id": "bad-cell",
                        "execution_count": None,
                        "metadata": {},
                        "outputs": [],
                        "source": ["!svtk qc build\n"],
                    }
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )
    marker = repo / "outputs" / "tutorials" / "keep.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("do not delete", encoding="utf-8")

    with pytest.raises(SystemExit, match="Tutorial notebook source contract failed"):
        module.main(["--repo-root", str(repo), "--notebook", str(notebook), "--clean", "--skip-example-data-check"])

    assert marker.exists()


def test_tutorial_notebook_preflight_only_skips_runtime_and_clean(tmp_path: Path, monkeypatch, capsys) -> None:
    """The CLI should support cheap source/data preflights without notebook runtimes."""

    module = _load_executor_module()
    repo = tmp_path / "repo"
    examples = repo / "docs" / "examples"
    examples.mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='spatial-vtk'\n", encoding="utf-8")
    notebook = examples / "step_01.ipynb"
    notebook.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "id": "bootstrap",
                        "execution_count": None,
                        "metadata": {},
                        "outputs": [],
                        "source": [
                            "import runpy\n",
                            "_bootstrap = 'docs/examples/_source_bootstrap.py'\n",
                            "runpy.run_path(str(_bootstrap))\n",
                        ],
                    }
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )
    marker = repo / "outputs" / "tutorials" / "keep.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("do not delete", encoding="utf-8")
    monkeypatch.setattr(module, "check_notebook_runtime", lambda: (_ for _ in ()).throw(AssertionError("runtime checked")))

    result = module.main(
        [
            "--repo-root",
            str(repo),
            "--notebook",
            str(notebook),
            "--clean",
            "--skip-example-data-check",
            "--preflight-only",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "Notebook preflight clean for 1 notebook(s)." in captured.out
    assert marker.exists()


def test_tutorial_notebook_runtime_check_only_skips_clean_and_execution(tmp_path: Path, monkeypatch, capsys) -> None:
    """The CLI should let users verify execution dependencies without running notebooks."""

    module = _load_executor_module()
    repo = tmp_path / "repo"
    examples = repo / "docs" / "examples"
    examples.mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='spatial-vtk'\n", encoding="utf-8")
    notebook = examples / "step_01.ipynb"
    notebook.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "id": "bootstrap",
                        "execution_count": None,
                        "metadata": {},
                        "outputs": [],
                        "source": [
                            "import runpy\n",
                            "_bootstrap = 'docs/examples/_source_bootstrap.py'\n",
                            "runpy.run_path(str(_bootstrap))\n",
                        ],
                    }
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )
    marker = repo / "outputs" / "tutorials" / "keep.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("do not delete", encoding="utf-8")
    checks = {"runtime": 0}

    def fake_check_runtime() -> None:
        checks["runtime"] += 1

    monkeypatch.setattr(module, "check_notebook_runtime", fake_check_runtime)
    monkeypatch.setattr(
        module,
        "execute_notebook",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("executed")),
    )

    result = module.main(
        [
            "--repo-root",
            str(repo),
            "--notebook",
            str(notebook),
            "--clean",
            "--skip-example-data-check",
            "--runtime-check-only",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert checks["runtime"] == 1
    assert "Notebook runtime dependencies available for 1 notebook(s)." in captured.out
    assert marker.exists()


def test_ci_runs_clean_tutorial_notebooks_with_notebook_extras() -> None:
    """CI should prove source-checkout tutorial notebooks run from example data."""

    repo_root = Path(__file__).resolve().parents[1]
    workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    docs_workflow = (repo_root / ".github" / "workflows" / "docs.yml").read_text(encoding="utf-8")

    install = 'python -m pip install -e ".[validation,docs,dashboard,notebooks,waveforms]"'
    assert install in workflow
    assert install in docs_workflow
    assert (
        "MPLCONFIGDIR=/tmp/mplconfig_svtk "
        "python tools/execute_tutorial_notebooks.py --preflight-only --include-large-run"
    ) in workflow
    assert (
        "MPLCONFIGDIR=/tmp/mplconfig_svtk "
        "python tools/execute_tutorial_notebooks.py --clean --include-large-run"
    ) in workflow


def test_examples_docs_advertise_fresh_checkout_large_run_gate_and_sidecars() -> None:
    """Public tutorial docs should expose the clean-run and figure-audit contract."""

    repo_root = Path(__file__).resolve().parents[1]
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    installation = (repo_root / "docs" / "installation.rst").read_text(encoding="utf-8")
    examples_index = (repo_root / "docs" / "examples" / "index.rst").read_text(encoding="utf-8")
    large_run_readme = (repo_root / "docs" / "examples" / "large_run" / "README.md").read_text(encoding="utf-8")
    combined = f"{readme}\n{installation}\n{examples_index}\n{large_run_readme}"

    assert "standard and large-run tutorial notebooks" in installation
    assert 'python -m pip install -e ".[validation,docs,dashboard,notebooks,waveforms]"' in readme
    assert "\n    python -m pip install -e .\n" not in readme
    assert 'python -m pip install -e ".[dashboard,docs,notebooks,validation,waveforms]"' not in combined
    assert "source-checkout extras" in readme
    assert "If pip has trouble solving compiled geospatial or waveform packages" in readme
    assert "conda env create -f svtk_environment.yaml" in readme
    assert "If pip has trouble solving compiled geospatial or waveform packages" in examples_index
    assert "If pip has trouble solving compiled geospatial or waveform packages" in large_run_readme
    assert "## Run the Tutorial Notebooks" in readme
    assert "python tools/execute_tutorial_notebooks.py --preflight-only --include-large-run" in readme
    assert (
        "MPLCONFIGDIR=/tmp/mplconfig_svtk "
        "python tools/execute_tutorial_notebooks.py --runtime-check-only --include-large-run"
    ) in readme
    assert (
        "MPLCONFIGDIR=/tmp/mplconfig_svtk "
        "python tools/execute_tutorial_notebooks.py --clean --include-large-run"
    ) in readme
    assert "The runtime check does not execute notebooks or clean outputs." in readme
    assert "keeps matplotlib font/cache files in a writable" in readme
    assert 'python -m pip install -e ".[validation,docs,dashboard,notebooks,waveforms]"' in examples_index
    assert 'python -m pip install -e ".[validation,docs,dashboard,notebooks,waveforms]"' in large_run_readme
    assert (
        "MPLCONFIGDIR=/tmp/mplconfig_svtk "
        "python tools/execute_tutorial_notebooks.py --clean --include-large-run"
    ) in installation
    assert (
        "MPLCONFIGDIR=/tmp/mplconfig_svtk "
        "python tools/execute_tutorial_notebooks.py --runtime-check-only --include-large-run"
    ) in installation
    assert (
        "MPLCONFIGDIR=/tmp/mplconfig_svtk "
        "python tools/execute_tutorial_notebooks.py --clean --include-large-run"
    ) in combined
    assert "python tools/execute_tutorial_notebooks.py --preflight-only --include-large-run" in combined
    assert (
        "MPLCONFIGDIR=/tmp/mplconfig_svtk "
        "python tools/execute_tutorial_notebooks.py --runtime-check-only --include-large-run"
    ) in combined
    assert "The runtime check does not execute notebooks or clean outputs." in examples_index
    assert "active Python version plus the Jupyter" in examples_index
    assert "Unsupported Python versions and missing dependency extras are reported" in examples_index
    assert "The command executes the seven notebooks" not in examples_index
    assert "The clean command executes the standard and large-run notebooks" in examples_index
    assert "outputs/tutorials/notebook_execution_report.json" in examples_index
    assert "scientific Python, mapping, dashboard, and waveform modules" in combined
    assert "SVTK_FIGURE_SIDECARS=1" in combined
    assert "SVTK_FIGURE_SIDECAR_ROWS=all" in combined
    assert "*.source.csv" in combined
    assert "pre-aggregation" in combined
    assert "committed example data" in combined
    assert "source-contract preflight" in combined
    assert "shell/CLI workflow cells" in combined
    assert "implementation plotting/workflow imports" in combined
    assert "fixed run" in combined
    assert "raw output-path/table reads" in combined
    assert "notebook-local dataframe filtering" in combined
    assert "Notebook cells use importable ``spatial_vtk`` package functions" in examples_index
    assert "Notebook cells call importable `spatial_vtk` package functions directly" in large_run_readme
    assert "do not shell out to `svtk` CLI commands for workflow work" in large_run_readme
    assert "PSA` and `FAS` are broadband spectral metrics" in large_run_readme
    assert "blank passband" in large_run_readme
    assert "PSA figures use oscillator periods instead" in large_run_readme
    assert "rebuild the metric manifest and metric rows" in large_run_readme


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
    assert "load_standard_ingest_workflow_outputs" in configuration
    assert "load_standard_metric_workflow_outputs" in configuration
    assert "ingest_outputs.metadata_summary_frame()" in configuration
    assert "In notebooks, use the Step 1 result object instead of shelling out to the CLI." in configuration
    assert 'cfg = SpatialVTKConfig.from_file("spatial-vtk.yaml", run_scenario="tutorial").activate()' in configuration
    assert "context = notebook_run_context()" in configuration
    assert "preprocessing_result = ingest_outputs.run_preprocessing_step_if_needed(" in configuration
    assert "preprocessing_result.status_frame()" in configuration
    assert 'output_group("step_01_ingest").load_tables' not in configuration
    assert "load_output_table(" not in configuration
    assert "write_output_table(" not in configuration
    assert "write_output_tables(" not in configuration
    assert "resolve_output_path(" not in configuration
    assert "ingest_outputs.write_context_figures(...)" in configuration
    assert "custom_record_coverage.png" not in configuration
    assert 'outpath="figures/custom_record_coverage.png"' not in configuration


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
    standard_notebook = json.loads(
        (repo_root / "docs" / "examples" / "step_02_quality_control.ipynb").read_text(encoding="utf-8")
    )
    standard_text = "\n".join("".join(cell.get("source", [])) for cell in standard_notebook.get("cells", []))
    large_run_text = (
        repo_root / "docs" / "examples" / "large_run" / "step_02_large_run_quality_control.ipynb"
    ).read_text(encoding="utf-8")

    assert "run_qc_inventory_from_config(" not in standard_text
    assert "metrics_settings_from_config," in standard_text
    assert "from spatial_vtk.config.metrics import" not in standard_text
    assert "write_qc_inventory_overlap_from_config(" not in standard_text
    assert "run_qc_summary_workflow_from_config(" not in standard_text
    assert "run_notebook_step_if_needed(" not in standard_text
    assert "notebook_step_result(" not in standard_text
    assert "display_notebook_step_result," in standard_text
    assert "qc_inputs.step_result(" not in standard_text
    assert "qc_inputs.qc_inventory_step_result(" not in standard_text
    assert "qc_inputs.qc_overlap_step_result(" not in standard_text
    assert "qc_inputs.qc_summary_step_result(" not in standard_text
    assert "qc_readiness = qc_inventory_readiness_from_config(" not in standard_text
    assert "overlap_readiness = qc_overlap_readiness_from_config(" not in standard_text
    assert "summary_readiness = qc_summary_readiness_from_config(" not in standard_text
    assert "qc_outputs.readiness(" not in standard_text
    assert '"reused": not qc_readiness.should_run' not in standard_text
    assert '"reused": not overlap_readiness.should_run' not in standard_text
    assert '"reused": not summary_readiness.should_run' not in standard_text
    assert "run_local=True" in standard_text
    assert "load_standard_qc_inputs," in standard_text
    assert "load_standard_qc_workflow_outputs," in standard_text
    assert "qc_inventory_readiness_from_config," not in standard_text
    assert "qc_overlap_readiness_from_config," not in standard_text
    assert "qc_summary_readiness_from_config," not in standard_text
    assert "qc_inputs = load_standard_qc_inputs(cfg=cfg)" in standard_text
    assert "qc_outputs = load_standard_qc_workflow_outputs(cfg=cfg)" in standard_text
    assert "qc_outputs.run_inventory_step_if_needed(" in standard_text
    assert "qc_outputs.run_overlap_step_if_needed(" in standard_text
    assert "qc_outputs.run_summary_step_if_needed(" in standard_text
    assert 'display_notebook_step_result(qc_inventory_result, label="Full QC inventory", display=display)' in standard_text
    assert 'display_notebook_step_result(qc_overlap_result, label="Overlap QC inventory", display=display)' in standard_text
    assert 'display_notebook_step_result(qc_summary_workflow_result, label="QC summary tables", display=display)' in standard_text
    assert "print(qc_inventory_result)" not in standard_text
    assert "print(qc_overlap_result)" not in standard_text
    assert "print(qc_summary_workflow_result)" not in standard_text
    assert "scope=overlap_scope" in standard_text
    assert "qc_inputs.status_frame()" in standard_text
    assert "ingest_outputs.load_tables(" not in standard_text
    assert 'qc_outputs = output_group("step_02_qc", cfg=cfg)' not in standard_text
    assert "qc_inputs.write_figures(" in standard_text
    assert "write_qc_figures_from_outputs(" not in standard_text
    assert "qc_figure_result.status_frame()" in standard_text
    assert "qc_inputs.write_waveform_comparison(" in standard_text
    assert "display(waveform_comparison_result.status_frame())" in standard_text
    assert "print(waveform_comparison_result.message)" not in standard_text
    assert 'print(f"Waveform pairs shown:' not in standard_text
    assert "qc_outputs = qc_inputs.outputs" not in standard_text
    assert '"availability_path"' in standard_text
    assert "qc_figure_tables = qc_outputs.load_tables(" not in standard_text
    assert "qc_outputs.display_table_previews(" not in standard_text
    assert "qc_inputs.display_inventory_preview(nrows=5)" in standard_text
    assert "qc_outputs.preview_table(" not in standard_text
    assert "qc_outputs.display_path_table_previews(" not in standard_text
    assert "qc_inputs.display_summary_previews(nrows=5)" in standard_text
    assert "qc_inputs.compact_output_summary_frame()" in standard_text
    assert "qc_outputs.preview_path_table(" not in standard_text
    assert "qc_outputs.trace_qc_path" not in standard_text
    assert "qc_outputs.qc_inventory_path" not in standard_text
    assert "qc_outputs.qc_inventory_overlap_path" not in standard_text
    assert "qc_outputs.comparison_eligible_path" not in standard_text
    assert "comparison_eligible_preview =" not in standard_text
    assert "manual-review queue:" not in standard_text
    assert "QC overlap inventory:" not in standard_text
    assert "comparison-eligible records:" not in standard_text
    assert "plot_retention_summary(" not in standard_text
    assert "plot_event_station_retention_heatmap(" not in standard_text
    assert "plot_post_qc_station_event_map(" not in standard_text
    assert "plot_qc_drop_cause_diagnostics(" not in standard_text
    assert "qc_sidecars" not in standard_text
    assert "savefig=True" not in standard_text
    assert "showfig=True" not in standard_text
    assert "write_waveform_comparison_from_notebook_settings(" not in standard_text
    assert "write_waveform_comparison_from_outputs(" not in standard_text
    assert "waveform_sidecars" not in standard_text
    assert "build_qc_waveform_comparison_records(" not in standard_text
    assert "load_comparison_eligible_records(" not in standard_text
    assert "plot_event_trace_comparison(" not in standard_text
    assert "comparison_preview_rows" not in standard_text
    assert "qc_outputs.qc_inventory_path.exists()" not in standard_text
    assert "qc_outputs.qc_inventory_overlap_path.exists()" not in standard_text
    assert "export_manual_review_queue_from_qc_inventory(" not in standard_text
    assert "trace_qc_output=trace_qc_path" not in standard_text
    assert "qc_inventory_output=qc_inventory_path" not in standard_text
    assert "qc_inventory_overlap_output=qc_inventory_overlap_path" not in standard_text
    assert "preview_output_table(" not in standard_text
    assert "notebook_dashboard_launch_commands(" in standard_text
    assert "launch_configured_dashboards_from_notebook_settings(" in standard_text
    assert 'dashboards=("qc",)' in standard_text
    assert "launch_configured_qc_dashboard(" not in standard_text
    assert "dashboard_launch.qc_launch_kwargs(show=True)" not in standard_text
    assert "display(dashboard_launch_result.status_frame())" in standard_text
    assert "launch_qc_dashboard(" not in standard_text
    assert 'os.environ.get("SVTK_QC_DASHBOARD_PORT"' not in standard_text
    assert 'os.environ.get("SVTK_LAUNCH_QC_DASHBOARD"' not in standard_text
    assert "run_notebook_step_if_needed(" not in large_run_text
    assert "from spatial_vtk.qc import (" in large_run_text
    assert "load_standard_qc_workflow_outputs," in large_run_text
    assert "qc_outputs = load_standard_qc_workflow_outputs(cfg=cfg)" in large_run_text
    assert "step_outputs = qc_outputs.outputs" not in large_run_text
    assert "display(qc_outputs.status_frame())" in large_run_text
    assert 'from spatial_vtk.io import output_group' not in large_run_text
    assert 'step_outputs = output_group("step_02_qc")' not in large_run_text
    assert "run_qc_inventory_from_config," not in large_run_text
    assert "write_qc_inventory_overlap_from_config," not in large_run_text
    assert "run_qc_summary_workflow_from_config," not in large_run_text
    assert "qc_outputs.run_inventory_step_if_needed(" in large_run_text
    assert "qc_outputs.run_overlap_step_if_needed(" in large_run_text
    assert "qc_outputs.run_summary_step_if_needed(" in large_run_text
    assert "qc_outputs.write_figures(" in large_run_text
    assert "write_large_run_qc_figures_from_outputs(" not in large_run_text
    assert "qc_figure_result.status_frame()" in large_run_text
    assert "qc_figure_tables = step_outputs.load_tables(" not in large_run_text
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


def test_large_run_notebooks_use_direct_grouped_output_attributes() -> None:
    """Large-run notebooks should keep grouped path ownership visible."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples" / "large_run").glob("*.ipynb"))
    assert notebooks

    output_paths_tree = ast.parse((repo_root / "src" / "spatial_vtk" / "io" / "output_paths.py").read_text(encoding="utf-8"))
    output_group_names: dict[str, set[str]] = {}
    for node in output_paths_tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "OUTPUT_GROUPS" for target in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        for key_node, value_node in zip(node.value.keys, node.value.values):
            if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
                continue
            names: set[str] = set()
            if isinstance(value_node, ast.Tuple):
                for item in value_node.elts:
                    if (
                        isinstance(item, ast.Call)
                        and isinstance(item.func, ast.Name)
                        and item.func.id == "OutputArtifact"
                        and item.args
                        and isinstance(item.args[0], ast.Constant)
                        and isinstance(item.args[0].value, str)
                    ):
                        names.add(item.args[0].value)
            output_group_names[key_node.value] = names

    assert output_group_names
    alias_pattern = re.compile(r"^\s*\w+_path\s*=\s*\w+_outputs\.\w+_path\b", re.MULTILINE)
    assignment_pattern = re.compile(r"(\w+_outputs)\s*=\s*output_group\(\"([^\"]+)\"")
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        assert ".bind(globals())" not in source, notebook_path.relative_to(repo_root)
        matches = alias_pattern.findall(source)
        assert not matches, f"{notebook_path.relative_to(repo_root)} repeats grouped path aliases: {matches}"
        owners = {owner: group for owner, group in assignment_pattern.findall(source)}
        grouped_path_names = set().union(*(output_group_names.get(group, set()) for group in owners.values()))
        if "preprocessed_waveform_output_group(" in source:
            grouped_path_names.update(
                {
                    "preprocessed_event_station_path",
                    "preprocessed_manifest_path",
                    "preprocessed_trace_metadata_path",
                }
            )
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            if cell.get("cell_type") != "code":
                continue
            cell_source = "".join(cell.get("source", []))
            tree = ast.parse(cell_source)
            bare = sorted(
                {
                    node.id
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Name) and node.id in grouped_path_names
                }
            )
            assert not bare, f"{notebook_path.relative_to(repo_root)} cell {index} uses bare grouped paths: {bare}"


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
    """Large-run notebooks should use package-owned output helpers."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples" / "large_run").glob("*.ipynb"))
    assert notebooks
    for notebook_path in notebooks:
        source = notebook_path.read_text(encoding="utf-8")
        if notebook_path.name == "step_07_large_run_dashboards.ipynb":
            continue
        assert (
            "output_group(" in source
            or "load_standard_ingest_workflow_outputs(" in source
            or "load_standard_qc_workflow_outputs(" in source
            or "load_standard_metric_workflow_outputs(" in source
            or "load_standard_spatial_workflow_output_status(" in source
            or "load_standard_geojson_workflow_output_status(" in source
            or "load_standard_additional_plotting_output_status(" in source
        ), notebook_path.relative_to(repo_root)
        assert "output_group_namespace" not in source, notebook_path.relative_to(repo_root)
        assert "output_group_status_frame" not in source, notebook_path.relative_to(repo_root)
        assert "vars(step_outputs)" not in source, notebook_path.relative_to(repo_root)


def test_large_run_notebooks_do_not_use_fake_missing_config_paths() -> None:
    """Large-run notebooks should pass unconfigured optional paths through readiness helpers."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_05_large_run_geojson_corridors.ipynb"
    source = notebook_path.read_text(encoding="utf-8")

    assert ("__missing_" + "region_geojson__") not in source
    assert 'geojson_input = {"region_geojson_path": geojson_path}' in source


def test_large_run_notebooks_do_not_bind_unused_context_aliases() -> None:
    """Large-run setup cells should not copy unused context fields into local names."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples" / "large_run").glob("*.ipynb"))
    assert notebooks
    forbidden = (
        "repo_root = context.repo_" + "root",
        "outputs_root = context.outputs_" + "root",
        "tables_dir = context.tables_" + "dir",
        "figures_dir = context.figures_" + "dir",
        "slurm_dir = context.slurm_" + "dir",
        "logs_dir = context.logs_" + "dir",
        "RUN_LOCAL = context.run_" + "local",
        "METRICS_FIGURE_" + "DIR",
        'figures_dir / "metrics"',
    )
    for notebook_path in notebooks:
        source = notebook_path.read_text(encoding="utf-8")
        matches = [pattern for pattern in forbidden if pattern in source]
        assert not matches, f"{notebook_path.relative_to(repo_root)} binds unused context aliases: {matches}"


def test_large_run_setup_markdown_describes_package_context() -> None:
    """Large-run setup prose should not teach notebook-local path plumbing."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples" / "large_run").glob("*.ipynb"))
    assert notebooks
    stale_phrases = (
        "load config/output paths",
        "printed paths and helper variables",
        "printed repository/config/output paths",
        "reusable helper variables",
    )
    expected = "Purpose: load the active config and shared notebook settings through package helpers."
    for notebook_path in notebooks:
        source = notebook_path.read_text(encoding="utf-8")
        matches = [phrase for phrase in stale_phrases if phrase in source]
        assert not matches, f"{notebook_path.relative_to(repo_root)} has stale setup prose: {matches}"
        assert expected in source, f"{notebook_path.relative_to(repo_root)} does not describe package context setup"


def test_large_run_source_bootstrap_does_not_bind_unused_repo_root() -> None:
    """Large-run notebooks should import the checkout without keeping unused root paths."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples" / "large_run").glob("*.ipynb"))
    assert notebooks
    for notebook_path in notebooks:
        source = notebook_path.read_text(encoding="utf-8")
        assert "runpy.run_path(str(_bootstrap))" in source, notebook_path.relative_to(repo_root)
        assert "repo_root = runpy.run_path(str(_bootstrap))" not in source, notebook_path.relative_to(repo_root)


def test_tutorial_notebooks_use_public_plot_and_map_imports() -> None:
    """Tutorial notebooks should teach stable public plotting imports."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    forbidden = (
        "from spatial_vtk.metrics.plot.",
        "import spatial_vtk.metrics.plot.",
        "from spatial_vtk.spatial.map.",
        "import spatial_vtk.spatial.map.",
        "from spatial_vtk.spatial.plot.",
        "import spatial_vtk.spatial.plot.",
        "from spatial_vtk.visualize.context.",
        "import spatial_vtk.visualize.context.",
        "from spatial_vtk.visualize.qc.",
        "import spatial_vtk.visualize.qc.",
        "from spatial_vtk.visualize.waveforms.",
        "import spatial_vtk.visualize.waveforms.",
        "from spatial_vtk.visualize.dashboard.",
        "import spatial_vtk.visualize.dashboard.",
    )
    assert notebooks
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            source = "".join(cell.get("source", []))
            matches = [pattern for pattern in forbidden if pattern in source]
            assert not matches, f"{notebook_path.relative_to(repo_root)} cell {index} uses {matches}"


def test_tutorial_notebooks_avoid_implementation_module_imports() -> None:
    """Tutorial notebooks should stay on public package surfaces."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    forbidden_import_patterns = (
        re.compile(r"^\s*from\s+spatial_vtk\.io\.(metadata|preprocessing|tables)\b", re.MULTILINE),
        re.compile(r"^\s*import\s+spatial_vtk\.io\.(metadata|preprocessing|tables)\b", re.MULTILINE),
        re.compile(r"^\s*from\s+spatial_vtk\.config\.(metrics|notebook|outputs|runtime)\b", re.MULTILINE),
        re.compile(r"^\s*import\s+spatial_vtk\.config\.(metrics|notebook|outputs|runtime)\b", re.MULTILINE),
        re.compile(r"^\s*from\s+spatial_vtk\.qc\.build\b", re.MULTILINE),
        re.compile(r"^\s*import\s+spatial_vtk\.qc\.build\.", re.MULTILINE),
        re.compile(r"^\s*from\s+spatial_vtk\.metrics\.workflow\.(execution|outputs|run|tasks)\b", re.MULTILINE),
        re.compile(r"^\s*import\s+spatial_vtk\.metrics\.workflow\.(execution|outputs|run|tasks)\b", re.MULTILINE),
        re.compile(r"^\s*from\s+spatial_vtk\.spatial\.(calculate|map\.|plot\.)", re.MULTILINE),
        re.compile(r"^\s*import\s+spatial_vtk\.spatial\.(calculate|map\.|plot\.)", re.MULTILINE),
        re.compile(r"^\s*from\s+spatial_vtk\.visualize\.(context\.|dashboard\.|qc\.|waveforms\.)", re.MULTILINE),
        re.compile(r"^\s*import\s+spatial_vtk\.visualize\.(context\.|dashboard\.|qc\.|waveforms\.)", re.MULTILINE),
    )
    assert notebooks
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            matches = [pattern.pattern for pattern in forbidden_import_patterns if pattern.search(source)]
            assert not matches, f"{notebook_path.relative_to(repo_root)} cell {index} uses {matches}"


def test_large_run_readme_distinguishes_public_and_implementation_imports() -> None:
    """Large-run docs should describe the same public-import boundary as preflight."""

    repo_root = Path(__file__).resolve().parents[1]
    readme = (repo_root / "docs" / "examples" / "large_run" / "README.md").read_text(encoding="utf-8")
    public_namespaces = (
        "spatial_vtk.metrics.plot",
        "spatial_vtk.spatial.plot",
        "spatial_vtk.spatial.map",
        "spatial_vtk.visualize",
    )
    for namespace in public_namespaces:
        assert namespace in readme
    for helper in (
        "notebook_run_context",
        "load_standard_ingest_workflow_outputs",
        "load_standard_metric_workflow_outputs",
        "metric_outputs.write_large_run_figure_suite(",
        "load_standard_qc_workflow_outputs",
        "load_standard_spatial_workflow_output_status",
        "load_standard_geojson_workflow_output_status",
        "prepare_configured_dashboard_datasets_from_notebook_settings",
    ):
        assert helper in readme
    assert "from spatial_vtk.metrics.plot import write_large_run_metric_figure_suite_from_notebook_settings" not in readme
    assert "spatial_outputs.write_figure_suite(" in readme
    assert "write_large_run_spatial_figure_suite_from_notebook_settings" not in readme
    assert "Import from stable public packages" in readme
    assert "deeper implementation modules below those packages" in readme
    for pattern in (
        "from spatial_vtk.metrics.plot.periods",
        "from spatial_vtk.spatial.map.station",
        "from spatial_vtk.visualize.context.figures",
        "import spatial_vtk.visualize.dashboard.streamlit_metrics",
    ):
        assert pattern not in readme
    for ambiguous_prefix in (
        "spatial_vtk.metrics.plot.*",
        "spatial_vtk.spatial.plot.*",
        "spatial_vtk.spatial.map.*",
        "spatial_vtk.visualize.context.*",
        "spatial_vtk.visualize.dashboard.*",
    ):
        assert ambiguous_prefix not in readme


def test_standard_tutorial_notebooks_avoid_raw_table_preview_helpers() -> None:
    """Standard tutorials should preview/load workflow tables through package helpers."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").glob("*.ipynb"))
    assert notebooks
    raw_preview = re.compile(r"(?<![._A-Za-z0-9])preview_table\(")
    forbidden = ("preview_output_table(", "load_output_table(")
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            source = "".join(cell.get("source", []))
            matches = [pattern for pattern in forbidden if pattern in source]
            if raw_preview.search(source):
                matches.append("preview_table(")
            assert not matches, f"{notebook_path.relative_to(repo_root)} cell {index} uses {matches}"


def test_standard_step01_uses_configured_io_workflows() -> None:
    """The ingest tutorial should use config-backed IO workflows, not inline table construction."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "step_01_ingest_and_prepare_data.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "prepare_metadata_tables_from_config(" in source
    assert "preprocess_waveforms_from_config(" in source
    assert "build_record_coverage_from_config(" in source
    assert "display_notebook_step_result," in source
    assert "load_standard_ingest_workflow_outputs," in source
    assert "ingest_outputs = load_standard_ingest_workflow_outputs(cfg=cfg)" in source
    assert "display(ingest_outputs.status_frame())" in source
    assert "ingest_outputs.write_context_figures(" in source
    assert "write_context_figures_from_outputs(" not in source
    assert "ingest_outputs.outputs," not in source
    assert "context_figure_result.status_frame()" in source
    assert "ingest_outputs.display_station_preview(nrows=5)" in source
    assert "ingest_outputs.display_event_preview(nrows=5)" in source
    assert "ingest_outputs.display_preprocessing_manifest_preview(nrows=5)" in source
    assert 'display_notebook_step_result(metadata_result, label="Metadata tables", display=display)' in source
    assert 'display_notebook_step_result(preprocessing_result, label="Preprocessed waveforms", display=display)' in source
    assert 'display_notebook_step_result(coverage_result, label="Record coverage", display=display)' in source
    assert "print(metadata_result.summary_message())" not in source
    assert "print(preprocessing_result.summary_message())" not in source
    assert "print(coverage_result.summary_message())" not in source
    assert "metadata_result['station_rows']" not in source
    assert "metadata_result['event_rows']" not in source
    assert "metadata_result['event_station_rows']" not in source
    assert "preprocessing_result['event_station_rows']" not in source
    assert "preprocessing_result['trace_metadata_rows']" not in source
    assert "preprocessing_result['manifest_rows']" not in source
    assert "coverage_result['record_coverage_path']" not in source
    assert 'step_outputs = output_group("step_01_ingest", cfg=cfg)' not in source
    assert "preprocessed_outputs = preprocessed_waveform_output_group(config=cfg)" not in source
    assert "step_outputs.display_table_previews(" not in source
    assert "metadata_tables = step_outputs.load_tables(" not in source
    assert "context_tables = step_outputs.load_tables(" not in source
    assert "stations.head(" not in source
    assert "events[[\"event_id\"" not in source
    assert "preprocessed_outputs.display_path_table_previews(" not in source
    assert 'preprocessed_outputs.preview_path_table("preprocessed_manifest_path"' not in source
    assert "manifest_preview =" not in source
    assert "continue_on_error=False" in source
    assert 'component="Z"' in source
    assert "prepare_station_metadata(" not in source
    assert "prepare_event_metadata(" not in source
    assert "prepare_event_station_table(" not in source
    assert "preprocess_waveform_files(" not in source
    assert "build_record_coverage_table_from_trace_metadata(" not in source
    assert "write_output_tables(" not in source
    assert "read_table(" not in source
    assert "plot_station_event_context(" not in source
    assert "plot_station_event_beachball_map(" not in source
    assert "plot_station_coverage(" not in source
    assert "plot_event_coverage(" not in source
    assert "plot_record_coverage(" not in source
    assert "context_sidecars" not in source
    assert "add_basemap =" not in source
    assert "savefig=True" not in source
    assert "showfig=True" not in source


def test_step04_uses_spatial_workflow_instead_of_recomputing_tables() -> None:
    """The spatial tutorial should use the package workflow for standard tables."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "step_04_spatial_statistics.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "load_standard_spatial_workflow_output_status(" in source
    assert "run_spatial_statistics_workflow_from_config(" not in source
    assert 'metrics="paths.metric_figure_snapshot"' not in source
    assert 'station_metadata="paths.site_metadata"' not in source
    assert "load_standard_spatial_workflow_outputs(" in source
    assert "spatial_status = load_standard_spatial_workflow_output_status(cfg=cfg)" in source
    assert "spatial_result = spatial_status.run_summary_step_if_needed(" in source
    assert "spatial_outputs = load_standard_spatial_workflow_outputs(spatial_result, cfg=cfg)" in source
    assert "spatial_outputs.status_frame()" in source
    assert 'step_outputs = output_group("step_04_spatial", cfg=cfg)' not in source
    assert "spatial_tables = step_outputs.load_tables(" not in source
    assert "render_notebook_figure(" not in source
    assert "step_outputs.figure_path(" not in source
    assert "outpath=" not in source
    assert "savefig=True" not in source
    assert "showfig=True" not in source
    assert "spatial_sidecars" not in source
    assert "spatial_workflow_failure_frame(" in source
    assert "summarize_standard_spatial_products(" not in source
    assert "summarize_standard_spatial_products," not in source
    assert "spatial_outputs.summary_frame()" in source
    assert "spatial_outputs.station_bias_preview_frame()" in source
    assert "spatial_tables = spatial_outputs.tables" not in source
    assert "spatial_products = spatial_outputs.spatial_products" not in source
    assert "spatial_metrics_run = spatial_outputs.metrics" not in source
    assert "step_outputs = spatial_outputs.outputs" not in source
    assert "spatial_metric_product_frames(" not in source
    assert "spatial_metric_product_summary_frame(" not in source
    assert "station_bias_preview_frame(bias" not in source
    assert "for metric_name in spatial_metrics_run" not in source
    assert "write_standard_spatial_map_figures(" not in source
    assert "write_standard_spatial_diagnostic_figures(" not in source
    assert "spatial_outputs.write_map_figures(" in source
    assert "spatial_outputs.write_diagnostic_figures(" in source
    assert "spatial_map_result.status_frame()" in source
    assert "spatial_diagnostic_result.preview_frame()" in source
    assert "spatial_diagnostic_result.status_frame()" in source
    assert "plot_station_bias_map(" not in source
    assert "plot_residual_grid(" not in source
    assert "plot_distance_correlation_by_metric(" not in source
    assert "plot_pca_summary(" not in source
    assert "plot_geology_contrast(" not in source
    assert "spatial_correlation_preview_frame(" not in source
    assert "spatial_metric_table_frame(" not in source
    assert "spatial_pca_product_frames(" not in source
    assert "display(bias.head())" not in source
    assert 'metric_field.loc[metric_field["metric"].astype(str).eq(metric_name)]' not in source
    assert 'event_centered_residuals.loc[event_centered_residuals["metric"].astype(str).eq(metric_name)]' not in source
    assert 'station_bias.loc[station_bias["metric"].astype(str).eq(metric_name)]' not in source
    assert 'pca_station_scores.loc[pca_station_scores["metric"].astype(str).eq(metric_name)]' not in source
    assert 'geology_contrasts.loc[geology_contrasts["metric"].astype(str).eq(metric_name)]' not in source
    assert 'distance_bins.loc[distance_bins["metric"].astype(str).eq(metric_name)].head()' not in source
    assert 'morans_i.loc[morans_i["metric"].astype(str).eq(metric_name)]' not in source
    assert "figure_dir /" not in source
    assert "pd.DataFrame(" not in source
    assert "import pandas as pd" not in source
    assert 'metric_field = spatial_tables["metric_field"]' in source
    assert "load_configured_input_tables(" not in source
    assert 'read_config_table("paths.site_metadata")' not in source
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

    assert "geojson_inputs.write_region_figures(" in source
    assert "geojson_inputs.write_corridor_figures(" in source
    assert "geojson_region_result.summary_frame()" in source
    assert "geojson_region_result.status_frame()" in source
    assert "geojson_corridor_result.boundary_crossing_frame()" in source
    assert "geojson_corridor_result.outward_event_frame()" in source
    assert "geojson_corridor_result.status_frame()" in source
    assert "write_standard_geojson_region_figures," not in source
    assert "write_standard_geojson_corridor_figures," not in source
    assert "from spatial_vtk.spatial import load_standard_geojson_workflow_output_status" in source
    assert "from spatial_vtk.spatial.plot import load_standard_geojson_workflow_output_status" not in source
    assert "load_standard_geojson_plotting_inputs" in source
    assert "geojson_inputs = load_standard_geojson_plotting_inputs(cfg=cfg)" in source
    assert "geojson_inputs.status_frame()" in source
    assert "geojson_path = geojson_inputs.geojson_path" not in source
    assert "step_outputs = geojson_inputs.outputs" not in source
    assert "metrics = geojson_inputs.metrics" not in source
    assert "stations = geojson_inputs.stations" not in source
    assert "events = geojson_inputs.events" not in source
    assert "event_stations = geojson_inputs.event_stations" not in source
    assert "comparison_eligible = geojson_inputs.comparison_eligible" not in source
    assert "load_configured_input_paths(" not in source
    assert "load_configured_input_tables(" not in source
    assert "output_group(" not in source
    assert "ingest_outputs.load_tables(" not in source
    assert "step_outputs.load_tables(" not in source
    assert "output_group(\"step_03_metrics\"" not in source
    assert "render_notebook_figure(" not in source
    assert "geojson_metric_region_frame(" not in source
    assert "geojson_metric_subset_frame(" not in source
    assert "corridor_record_pair_frame(" not in source
    assert "corridor_record_preview_frame(" not in source
    assert "event_ids_from_records(" not in source
    assert "event_rows_for_records(" not in source
    assert "event_label_preview_frame(" not in source
    assert "event_station_records_matching_pairs(" not in source
    assert "geojson_matched_record_frame(" not in source
    assert "classify_paths_with_geojson(" not in source
    assert "build_boundary_corridors(" not in source
    assert "build_qc_waveform_comparison_records(" not in source
    assert "plot_corridor_map(" not in source
    assert "plot_station_metric_map(" not in source
    assert "plot_observed_synthetic_record_section(" not in source
    assert "metrics_by_station_region.loc[" not in source
    assert "metrics_by_regions.loc[" not in source
    assert 'metrics_by_regions["metric"].astype(str).eq' not in source
    assert 'drop_duplicates(["event_id", "station"])' not in source
    assert '[[\"event_id\", \"station\"]].drop_duplicates()' not in source
    assert "drop_duplicates().head()" not in source
    assert "read_config_table(\"paths.metric_figure_snapshot\")" not in source
    assert "step_outputs.figure_path(" not in source
    assert "outpath=" not in source
    assert "savefig=True" not in source
    assert "showfig=False" not in source
    assert "plt.close(" not in source
    assert "spatial_sidecars" not in source
    assert "waveform_sidecars" not in source
    assert 'summary_metrics_table="paths.metric_figure_snapshot"' not in source
    assert 'summary_geojson_path="paths.region_geojson"' not in source
    assert "from spatial_vtk.spatial.calculate import" not in source
    assert 'cfg.path("paths.region_geojson"' not in source
    assert 'cfg.path("paths.metric_figure_snapshot")' not in source
    assert "read_table(metric_source_path)" not in source


def test_step03_station_map_uses_package_aggregation_and_source_sidecar() -> None:
    """The metric tutorial should not hand-roll station aggregation in notebook code."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "step_03_calculate_metrics.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "metric_outputs.write_station_metric_map(" in source
    assert "write_station_metric_map_from_notebook_settings(" not in source
    assert "station_metric_result.status_frame()" in source
    assert "station_metric_result.preview" in source
    assert "MetricFigureContext.from_frame(" not in source
    assert "station_summary_for_metric(" not in source
    assert "write_station_metric_map_for_metric(" not in source
    assert "metric_figure_settings.sidecars.kwargs(plural=True)" not in source
    assert "plot_station_metric_map" not in source
    assert "plot_station_metric_map_by_period" not in source
    assert "station_summary_for_map(" not in source
    assert "station_pga_source" not in source
    assert "source_df=station_pga_source" not in source
    assert ".groupby([" not in source


def test_large_run_step03_documents_metric_source_sidecars() -> None:
    """Large-run metric figures should document plotted rows and source rows."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_03_large_run_calculate_metrics.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "metric_outputs.write_large_run_figure_suite(" in source
    assert "write_large_run_metric_figure_suite_from_notebook_settings(" not in source
    assert "metric_figure_suite.status_frame()" in source
    assert "metric_figure_suite.display_context_status(display=display)" in source
    assert "metric_plot_context = metric_figure_suite.context" not in source
    assert "metric_plot_context.write_station_metric_maps(" not in source
    assert "metric_plot_context.write_residual_grid_maps(" not in source
    assert "metric_plot_context.write_metric_by_model_maps(" not in source
    assert "metric_plot_context.write_event_residual_maps(" not in source
    assert "write_psa_period_sheet = metric_plot_context.write_psa_period_sheet" not in source
    assert "write_metric_plot = metric_plot_context.write_metric_plot" not in source
    assert "reload_metric_plot_modules" not in source
    assert "globals().update(" not in source
    assert "station_summary_for_item = metric_plot_context.station_summary_for_item" not in source
    assert "item_source_rows = metric_plot_context.item_source_rows" not in source
    assert "source_df=item_source_rows(item)" not in source
    assert "source_df_factory=item_source_rows" not in source
    assert "source_df=item[\"df\"]" not in source
    assert "source_df_factory=lambda period_item" not in source
    assert "metric_plot_context.write_score_trend_plots(" not in source
    assert "plot_score_trends" not in source
    assert 'SCORE_TREND_FIGURE_SETTINGS = notebook_figure_settings(' not in source
    assert 'if not SCORE_TREND_FIGURE_SETTINGS.make_figures:' not in source
    assert 'SCORE_TREND_COLUMNS = SCORE_TREND_FIGURE_SETTINGS.score_columns or ["anderson_2004_gof"]' not in source
    assert 'os.environ.get("SVTK_MAKE_SCORE_TRENDS"' not in source
    assert 'os.environ.get("SVTK_SCORE_TREND_COLUMNS"' not in source
    assert "Skipping optional GOF score trends. Set SVTK_MAKE_SCORE_TRENDS=1" not in source
    assert "The main large-run figure suite uses `log2_residual`" in source
    assert "METRIC_FIGURE_SETTINGS = notebook_figure_settings(" in source
    assert "METRIC_FIGURE_SETTINGS.plot_selection_kwargs(" not in source
    assert "compare_to=METRIC_FIGURE_SETTINGS.compare_to" not in source
    assert "table=METRIC_FIGURE_SETTINGS.comparison_table" not in source
    assert "SCORE_TREND_COLUMNS" not in source
    assert "raw event-level rows used for the station summaries" in source
    assert "STATION_AGGREGATION = METRIC_FIGURE_SETTINGS.station_aggregation" not in source
    assert "DEFAULT_PLOT_" not in source
    assert "METRIC_FIGURE_SIDECARS" not in source
    for helper in (
        "write_residuals_vs_distance_plots",
        "write_residuals_vs_depth_plots",
        "write_vs30_scatter_plots",
        "write_station_metric_maps",
        "write_residual_grid_maps",
        "write_metric_by_model_maps",
        "write_event_residual_maps",
        "write_log2_residual_distribution_plots",
        "write_psa_period_curve_plots",
    ):
        assert f"metric_plot_context.{helper}(" not in source
    for plot_name in (
        "plot_residuals_vs_distance",
        "plot_residuals_vs_depth",
        "plot_vs30_scatter",
        "plot_station_metric_map",
        "plot_station_metric_map_by_period",
        "plot_residual_grid",
        "plot_metric_map_by_model",
        "plot_event_residual_map",
        "plot_band_score_distribution",
        "plot_psa_period_curve",
        "scatterplot",
        "boxplot",
        "heatmap",
    ):
        assert plot_name not in source


def test_metric_plot_package_does_not_export_notebook_reload_hook() -> None:
    """Development-only notebook reload helpers should stay out of the public plotting API."""

    repo_root = Path(__file__).resolve().parents[1]
    package_init = repo_root / "src" / "spatial_vtk" / "metrics" / "plot" / "__init__.py"
    large_run_module = repo_root / "src" / "spatial_vtk" / "metrics" / "plot" / "large_run.py"

    assert "reload_metric_plot_modules" not in package_init.read_text(encoding="utf-8")
    assert "reload_metric_plot_modules" not in large_run_module.read_text(encoding="utf-8")


def test_large_run_step04_uses_spatial_context_row_factories() -> None:
    """Large-run spatial figures should use package row factories, not notebook lambdas."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_04_large_run_spatial_statistics.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "run_notebook_step_if_needed(" not in source
    assert "display_notebook_step_result," in source
    assert "from spatial_vtk.spatial import load_standard_spatial_workflow_output_status" in source
    assert "config_path = context.config_path" not in source
    assert "run_spatial_statistics_workflow_from_config," not in source
    assert "run_spatial_derived_outputs_workflow_from_config," not in source
    assert "spatial_outputs = load_standard_spatial_workflow_output_status(cfg=context.cfg)" in source
    assert "spatial_summary_readiness_from_config," not in source
    assert "spatial_derived_outputs_readiness_from_config," not in source
    assert "spatial_summary_readiness = spatial_summary_readiness_from_config(" not in source
    assert "derived_readiness = spatial_derived_outputs_readiness_from_config(" not in source
    assert "spatial_outputs.run_summary_step_if_needed(" in source
    assert "spatial_outputs.run_derived_outputs_step_if_needed(" in source
    assert "spatial_summary_result = spatial_outputs.run_summary_step_if_needed(" in source
    assert "spatial_derived_result = spatial_outputs.run_derived_outputs_step_if_needed(" in source
    assert 'display_notebook_step_result(spatial_summary_result, label="Spatial summary tables", display=display)' in source
    assert 'display_notebook_step_result(spatial_derived_result, label="Spatial derived tables", display=display)' in source
    assert "print(spatial_summary_result)" not in source
    assert "print(spatial_derived_result)" not in source
    assert "core_spatial_output_names" not in source
    assert "derived_spatial_output_names" not in source
    assert "step_outputs.readiness(" not in source
    assert "spatial_outputs.display_table_previews(nrows=PREVIEW_ROWS)" in source
    assert "spatial_outputs.display_table_previews(cfg=context.cfg" not in source
    assert "step_outputs" not in source
    assert 'step_outputs = output_group("step_04_spatial")' not in source
    assert "display_output_table_previews(" not in source
    assert '"spatial_vtk.spatial.run_spatial_statistics_workflow_from_config"' not in source
    assert '"spatial_vtk.spatial.run_spatial_derived_outputs_workflow_from_config"' not in source
    assert "run_or_submit_notebook_function(" not in source
    assert "run_or_submit_notebook_cli_command(" not in source
    assert '"svtk", "spatial"' not in source
    assert "should_rebuild_paths(" not in source
    assert "spatial_outputs.write_figure_suite(" in source
    assert "write_large_run_spatial_figure_suite_from_notebook_settings(" not in source
    assert "spatial_figure_suite.status_frame()" in source
    assert "spatial_figures.write_station_metric_maps(" not in source
    assert "spatial_figures.write_residual_grid_maps(" not in source
    assert "spatial_figures.write_metric_by_model_maps(" not in source
    assert "spatial_figures.write_event_residual_maps(" not in source
    assert "spatial_figures.write_event_centered_azimuthal_plots(" not in source
    assert "spatial_figures.write_event_centered_polar_plots(" not in source
    assert "station_summary_for_item = spatial_figures.station_summary_for_item" not in source
    assert "item_source_rows = spatial_figures.item_source_rows" not in source
    assert "for item in iter_metric_frames(" not in source
    assert "plot_pca_summary" not in source
    assert "spatial_figures.write_pca_summary_plots(" not in source
    assert "prepare_spatial_figure_context_from_notebook_settings(" not in source
    assert "mode=SPATIAL_FIGURE_SETTINGS.pca_mode" not in source
    assert "SPATIAL_FIGURE_SETTINGS.plot_selection_kwargs(" not in source
    assert "PLOT_PASSBAND =" not in source
    assert "PLOT_COMPONENTS =" not in source
    assert "PLOT_SHOWFIG =" not in source
    assert "PLOT_MODEL =" not in source
    assert "PCA_MODE =" not in source
    assert "robust_axis_percentile=SPATIAL_FIGURE_SETTINGS.robust_axis_percentile" not in source
    assert "DEFAULT_PCA_MODE =" not in source
    assert "DEFAULT_PLOT_PASSBAND =" not in source
    assert "SPATIAL_FIGURE_SIDECARS =" not in source
    assert 'os.environ.get("SVTK_PCA_MODE"' not in source
    assert "source_df=item_source_rows(item)" not in source
    assert "source_df_factory=item_source_rows" not in source
    assert "source_df=item[\"df\"]" not in source
    assert "source_df_factory=lambda period_item" not in source
    assert "spatial_figures.write_overview_plots(" not in source
    assert "spatial_outputs.write_summary_figures(" in source
    assert "write_large_run_spatial_summary_figures_from_outputs(" not in source
    assert "quick_spatial_result.status_frame()" in source
    assert "### Spatial Event-Centered Azimuthal Residuals" not in source
    assert "### Spatial Event-Centered Polar Residuals" not in source
    assert "plot_station_metric_map" not in source
    assert "plot_station_metric_map_by_period" not in source
    assert "plot_residual_grid" not in source
    assert "plot_metric_map_by_model" not in source
    assert "plot_event_residual_map" not in source
    assert "plot_azimuthal_residuals" not in source
    assert "plot_polar_residuals" not in source
    assert 'write_spatial_plot("spatial_correlogram"' not in source
    assert "plot_correlogram" not in source
    assert "preview_output_table(" not in source
    assert "for name, key in [" not in source
    assert "spatial_outputs.load_table(" not in source
    assert "load_output_table(" not in source


def test_large_run_markdown_sections_document_purpose_and_outputs() -> None:
    """Large-run section cells should state the task and the produced artifact."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_dir = repo_root / "docs" / "examples" / "large_run"

    missing: list[str] = []
    for notebook_path in sorted(notebook_dir.glob("step_*.ipynb")):
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            if cell.get("cell_type") != "markdown":
                continue
            source = "".join(cell.get("source", []))
            first_line = next((line.strip() for line in source.splitlines() if line.strip()), "")
            if not first_line.startswith("##"):
                continue
            if first_line.startswith("# ") or ("Purpose:" in source and "Outputs:" in source):
                continue
            missing.append(f"{notebook_path.name} cell {index}: {first_line}")

    assert not missing


def test_large_run_step05_uses_package_functions_for_heavy_steps() -> None:
    """Large-run GeoJSON notebook should call package helpers, not CLI command cells."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_05_large_run_geojson_corridors.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "run_notebook_step_if_needed(" not in source
    assert "from spatial_vtk.spatial import (" not in source
    assert "config_path = context.config_path" not in source
    assert "load_configured_input_paths(" not in source
    assert "display_notebook_step_result," in source
    assert "geojson_region_summary_readiness_from_config," not in source
    assert "boundary_corridor_readiness_from_config," not in source
    assert "run_geojson_region_summary_workflow_from_config," not in source
    assert "run_boundary_corridor_workflow_from_config," not in source
    assert "load_standard_geojson_workflow_output_status" in source
    assert "geojson_outputs = load_standard_geojson_workflow_output_status(cfg=cfg)" in source
    assert "geojson_outputs.run_geojson_summary_step_if_needed(" in source
    assert "geojson_outputs.run_corridor_step_if_needed(" in source
    assert "geojson_summary_result = geojson_outputs.run_geojson_summary_step_if_needed(" in source
    assert "corridor_result = geojson_outputs.run_corridor_step_if_needed(" in source
    assert 'display_notebook_step_result(geojson_summary_result, label="GeoJSON region summaries", display=display)' in source
    assert 'display_notebook_step_result(corridor_result, label="Boundary corridors", display=display)' in source
    assert "print(geojson_summary_result)" not in source
    assert "print(corridor_result)" not in source
    assert "geojson_outputs.display_table_previews(nrows=PREVIEW_ROWS)" in source
    assert "geojson_outputs.display_table_previews(cfg=cfg" not in source
    assert "step_outputs" not in source
    assert 'step_outputs = output_group("step_05_geojson")' not in source
    assert "display_output_table_previews(" not in source
    assert "geojson_outputs.write_region_figures(" in source
    assert "    REGION_FIGURE_SETTINGS,\n" in source
    assert "geojson_path=geojson_path" not in source
    assert "ingest_outputs," not in source
    assert "write_large_run_geojson_region_figures_from_notebook_settings(" not in source
    assert "region_figure_gate = REGION_FIGURE_SETTINGS.render_gate(" not in source
    assert "write_large_run_geojson_region_figures_from_outputs(" not in source
    assert "region_figure_result.status_frame()" in source
    assert "ingest_outputs.load_tables(" not in source
    assert "geojson_outputs.load_table(" not in source
    assert "write_large_run_region_boxplot_from_outputs(" not in source
    assert "geojson_outputs.first_existing_path(" not in source
    assert "step_outputs.corridors_path.exists()" not in source
    assert "metrics_enriched_path if metrics_enriched_path.exists() else metrics_long_path" not in source
    assert 'cfg.path("paths.region_geojson"' not in source
    assert "load_output_table(" not in source
    assert '"spatial_vtk.spatial.run_geojson_region_summary_workflow_from_config"' not in source
    assert '"spatial_vtk.spatial.run_boundary_corridor_workflow_from_config"' not in source
    assert "geojson_readiness = geojson_region_summary_readiness_from_config(" not in source
    assert "corridor_readiness = boundary_corridor_readiness_from_config(" not in source
    assert "geojson_readiness = step_outputs.readiness(" not in source
    assert "corridor_readiness = step_outputs.readiness(" not in source
    assert "geojson_input" not in source
    assert "corridor_required_inputs" not in source
    assert "corridor_source_paths" not in source
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
    assert "preview_output_table(" not in source


def test_step07_dashboard_notebook_uses_configured_export_helper() -> None:
    """Dashboard tutorial should keep dataset path plumbing inside package helpers."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "step_07_dashboards.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "prepare_configured_dashboard_datasets_from_notebook_settings," in source
    assert "display_dashboard_preparation_result," in source
    assert "dashboard_preparation = prepare_configured_dashboard_datasets_from_notebook_settings(" in source
    assert "display_dashboard_preparation_result(dashboard_preparation, display=display)" in source
    assert "print(dashboard_preparation.message)" not in source
    assert "display(display_table(dashboard_preparation.summary_frame(), max_rows=20))" not in source
    assert "display(display_table(dashboard_preparation.status_frame(), max_rows=30))" not in source
    assert "display(display_table(dashboard_preparation.written_frame(), max_rows=20))" not in source
    assert "dashboard_summary_table_contracts," not in source
    assert "display_table," not in source
    assert "dashboard_output_readiness," not in source
    assert "dashboard_output_status_frame," not in source
    assert "write_configured_dashboard_datasets," not in source
    assert "dashboard_readiness = dashboard_output_readiness(cfg=cfg, overwrite=False)" not in source
    assert "if dashboard_readiness.should_run:" not in source
    assert "print(dashboard_readiness.message)" not in source
    assert "display(dashboard_output_status_frame(cfg=cfg))" not in source
    assert "launch_configured_dashboards_from_notebook_settings(" in source
    assert "launch_configured_metrics_dashboard(" not in source
    assert "launch_configured_qc_dashboard(" not in source
    assert "notebook_dashboard_launch_commands(" in source
    assert 'launch_metrics_dashboard=notebook_overrides["launch_metrics_dashboard"]' in source
    assert 'launch_qc_dashboard=notebook_overrides["launch_qc_dashboard"]' in source
    assert "dashboard_launch.metrics_launch_kwargs(show=True)" not in source
    assert "dashboard_launch.qc_launch_kwargs(show=True)" not in source
    assert "display(dashboard_launch.status_frame())" in source
    assert "display(dashboard_launch_result.status_frame())" in source
    assert "qc_trace_summary_table" not in source
    assert "trace_summary_table" not in source
    assert "Launch options:" not in source
    assert "server_port=notebook_overrides" not in source
    assert "display_dashboard_output_previews," not in source
    assert "display_dashboard_output_previews(" not in source
    assert "dashboard_preparation.display_output_previews(" in source
    assert "dashboard_outputs = output_group(\"step_07_dashboards\", cfg=cfg)" not in source
    assert "dashboard_outputs.preview_table(" not in source
    assert "dashboard_outputs.qc_trace_summary_path" not in source
    assert "dashboard_outputs.metrics_long_path" not in source
    assert "metrics_path = dashboard_outputs.metrics_long_path" not in source
    assert "qc_trace_summary_path = dashboard_outputs.qc_trace_summary_path" not in source
    assert "dashboard_output_namespace" not in source
    assert "preview_output_table(" not in source
    assert "preview_output_table(" not in source
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

    assert "prepare_configured_dashboard_datasets_from_notebook_settings," in source
    assert "display_notebook_step_result," in source
    assert "display_dashboard_preparation_result," in source
    assert "readiness/Data Status messages to diagnose blank or sparse tabs" in source
    assert "dashboard table contracts" in source
    assert "dashboard_preparation = prepare_configured_dashboard_datasets_from_notebook_settings(" in source
    assert "prepare_locally=False" in source
    assert "display_dashboard_preparation_result(dashboard_preparation, display=display)" in source
    assert "print(dashboard_preparation.message)" not in source
    assert "dashboard_preparation_result = dashboard_preparation.run_if_needed(" in source
    assert 'display_notebook_step_result(dashboard_preparation_result, label="Dashboard datasets", display=display)' in source
    assert "post_dashboard_preparation = prepare_configured_dashboard_datasets_from_notebook_settings(" in source
    assert "display_dashboard_preparation_result(post_dashboard_preparation, display=display, include_contracts=False)" in source
    assert "dashboard_output_status_frame," not in source
    assert "dashboard_readiness_summary_frame," not in source
    assert "dashboard_summary_table_contracts," not in source
    assert "dashboard_output_readiness," not in source
    assert "dashboard_status = dashboard_output_status_frame(cfg=cfg)" not in source
    assert "dashboard_readiness_summary = dashboard_readiness_summary_frame(cfg=cfg, overwrite=OVERWRITE)" not in source
    assert "display(dashboard_readiness_summary)" not in source
    assert "dashboard_readiness = dashboard_output_readiness(cfg=cfg, overwrite=OVERWRITE)" not in source
    assert "run_notebook_step_if_needed(" not in source
    assert "write_configured_dashboard_datasets," not in source
    assert "write_configured_dashboard_datasets(" not in source
    assert "display_dashboard_output_previews," not in source
    assert "post_dashboard_preparation.display_output_previews(nrows=PREVIEW_ROWS, missing=\"skip\")" in source
    assert "preview_dashboard_summary_tables," not in source
    assert '"spatial_vtk.visualize.dashboard.write_configured_dashboard_datasets"' not in source
    assert "launch_configured_dashboards_from_notebook_settings(" in source
    assert "launch_configured_metrics_dashboard(" not in source
    assert "launch_configured_qc_dashboard(" not in source
    assert "notebook_dashboard_launch_commands(" in source
    assert "run_scenario=context.run_scenario" in source
    assert 'run_scenario=os.environ.get("SVTK_RUN_SCENARIO", "tutorial")' not in source
    assert 'os.environ.get("SVTK_RUN_SCENARIO"' not in source
    assert "if dashboard_launch.launch_metrics_dashboard:" not in source
    assert "if dashboard_launch.launch_qc_dashboard:" not in source
    assert 'os.environ.get("SVTK_LAUNCH_METRICS_DASHBOARD"' not in source
    assert 'os.environ.get("SVTK_LAUNCH_QC_DASHBOARD"' not in source
    assert "dashboard_launch.metrics_launch_kwargs(show=True)" not in source
    assert "dashboard_launch.qc_launch_kwargs(show=True)" not in source
    assert "display(dashboard_launch.status_frame())" in source
    assert "display(dashboard_launch_result.status_frame())" in source
    assert "qc_trace_summary_table" not in source
    assert "trace_summary_table" not in source
    assert "Launch options:" not in source
    assert "server_port=dashboard_" not in source
    assert '"cfg": str(config_path)' not in source
    assert "dashboard_outputs = output_group(\"step_07_dashboards\")" not in source
    assert "dashboard_outputs.preview_table(" not in source
    assert "post_dashboard_readiness = dashboard_readiness_summary_frame(cfg=cfg, overwrite=False)" not in source
    assert "post_dashboard_status = dashboard_output_status_frame(cfg=cfg)" not in source
    assert "post_dashboard_preparation.display_output_previews(nrows=PREVIEW_ROWS, missing=\"skip\")" in source
    assert "preview_output_table(" not in source
    assert "dashboard_output_namespace" not in source
    assert "dashboard_summary_root" not in source
    assert "dashboard_paths" not in source
    assert "metrics_long_path" not in source
    assert "metrics_dashboard_root" not in source
    assert "dashboard_summary_root" not in source
    assert "qc_trace_summary_path" not in source
    assert "run_or_submit_notebook_cli_command(" not in source
    assert '"svtk", "metrics"' not in source
    assert '"--metrics", str(' not in source


def test_large_run_notebooks_use_context_run_scenario_resolution() -> None:
    """Large-run notebooks should let notebook_run_context resolve SVTK_RUN_SCENARIO."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples" / "large_run").glob("*.ipynb"))
    assert notebooks
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        assert "notebook_run_context()" in source, notebook_path.relative_to(repo_root)
        assert 'run_scenario=os.environ.get("SVTK_RUN_SCENARIO"' not in source, notebook_path.relative_to(repo_root)


def test_standard_notebooks_reuse_context_run_scenario_after_setup() -> None:
    """Standard notebooks should not repeat literal tutorial scenarios in workflow cells."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").glob("step_*.ipynb"))
    assert notebooks
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        source_without_setup = source.replace(
            'context = notebook_run_context(config_path, run_scenario="tutorial")',
            "",
        )
        assert '"run_scenario": "tutorial"' not in source_without_setup, notebook_path.relative_to(repo_root)
        assert 'run_scenario="tutorial"' not in source_without_setup, notebook_path.relative_to(repo_root)
    combined_source = "\n".join(
        "\n".join(
            "".join(cell.get("source", []))
            for cell in json.loads(path.read_text(encoding="utf-8")).get("cells", [])
        )
        for path in notebooks
    )
    assert "run_scenario=context.run_scenario" in combined_source


def test_large_run_notebooks_display_output_readiness_tables() -> None:
    """Large-run driver cells should show named readiness status tables."""

    repo_root = Path(__file__).resolve().parents[1]
    required = {
        "large_run/step_01_large_run_ingest_and_prepare_data.ipynb": [
            "ingest_outputs.run_metadata_step_if_needed(",
            "ingest_outputs.run_preprocessing_step_if_needed(",
            "ingest_outputs.run_record_coverage_step_if_needed(",
        ],
        "large_run/step_02_large_run_quality_control.ipynb": [
            "qc_outputs.run_inventory_step_if_needed(",
            "qc_outputs.run_overlap_step_if_needed(",
        ],
        "large_run/step_03_large_run_calculate_metrics.ipynb": [
            "metric_outputs.run_inventory_step_if_needed(",
            "metric_outputs.run_slurm_step_if_needed(",
        ],
        "large_run/step_07_large_run_dashboards.ipynb": ["dashboard_preparation.run_if_needed("],
    }
    for relative, snippets in required.items():
        notebook_path = repo_root / "docs" / "examples" / relative
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        missing = [snippet for snippet in snippets if snippet not in source]
        assert not missing, f"{notebook_path.relative_to(repo_root)} missing readiness displays: {missing}"


def test_large_run_grouped_steps_use_output_group_readiness() -> None:
    """Large-run notebooks should not fall back to generic output_readiness calls."""

    repo_root = Path(__file__).resolve().parents[1]
    for relative in (
        "large_run/step_03_large_run_calculate_metrics.ipynb",
    ):
        notebook_path = repo_root / "docs" / "examples" / relative
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        assert "output_readiness(" not in source, notebook_path.relative_to(repo_root)
        assert "output_readiness," not in source, notebook_path.relative_to(repo_root)


def test_large_run_step03_uses_metric_batch_status_before_submit_and_merge() -> None:
    """Metric Slurm and merge cells should be gated by manifest batch completion."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_03_large_run_calculate_metrics.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "metric_outputs.run_inventory_step_if_needed(" in source
    assert "metric_outputs.run_manifest_step_if_needed(" in source
    assert "metric_outputs.run_slurm_step_if_needed(" in source
    assert "metric_outputs.run_merge_step_if_needed(" in source
    assert "metric_outputs.run_downstream_outputs_step_if_needed(" in source
    assert "metric_slurm_submission_readiness_from_config," not in source
    assert "metric_inventories_readiness_from_config," not in source
    assert "metric_manifest_readiness_from_config," not in source
    assert "metric_batch_merge_readiness_from_config," not in source
    assert "metric_outputs_readiness_from_config," not in source
    assert "from spatial_vtk.metrics.workflow import metric_manifest_batch_status" not in source
    assert "from spatial_vtk.metrics import metric_manifest_batch_status" not in source
    assert "metric_manifest_batch_status(" not in source
    assert "metric_slurm_submission_readiness(" not in source
    assert "inventory_readiness = metric_inventories_readiness_from_config(" not in source
    assert "manifest_readiness = metric_manifest_readiness_from_config(" not in source
    assert "slurm_readiness = metric_slurm_submission_readiness_from_config(" not in source
    assert "merge_readiness = metric_batch_merge_readiness_from_config(" not in source
    assert "downstream_readiness = metric_outputs_readiness_from_config(" not in source
    assert "step_outputs.readiness(" not in source
    assert "incomplete_only=not OVERWRITE" in source
    assert "overwrite_batches=OVERWRITE" in source
    assert "metric_manifest_path.exists()" not in source
    assert "metric_rows_path.exists()" not in source
    assert "sources=(metric_manifest_path, *batch_status.completed_outputs)" not in source


def test_large_run_step03_uses_package_functions_for_heavy_steps() -> None:
    """Step 3 should call metric workflow helpers instead of CLI command cells."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_03_large_run_calculate_metrics.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "run_notebook_step_if_needed(" not in source
    assert "run_or_submit_notebook_function(" not in source
    assert "from spatial_vtk.metrics import (" in source
    assert "metric_settings_summary," in source
    assert "metrics_settings_from_config," in source
    assert "load_standard_metric_workflow_outputs," in source
    assert "METRIC_BATCH_COUNT = context.metric_batch_count" in source
    assert "metric_settings = metrics_settings_from_config(cfg)" in source
    assert "metric_outputs = load_standard_metric_workflow_outputs(cfg=cfg)" in source
    assert "load_task_estimate=False" not in source
    assert "metric_outputs.metrics_long_path" in source
    assert "step_outputs = metric_outputs.outputs" not in source
    assert "trace_metadata_path = metric_outputs.trace_metadata_path" not in source
    assert "display(metric_outputs.status_frame())" in source
    assert 'step_outputs = output_group("step_03_metrics")' not in source
    assert "preprocessed_waveform_metadata_paths(config=cfg)" not in source
    assert "build_metric_waveform_inventories_from_config," not in source
    assert "plan_metric_tasks_from_config," not in source
    assert "metric_inventories_readiness_from_config," not in source
    assert "metric_manifest_readiness_from_config," not in source
    assert "write_metrics_slurm_script_from_config," not in source
    assert "merge_metric_batches_from_config," not in source
    assert "write_metric_outputs_from_config," not in source
    assert "metric_outputs.run_inventory_step_if_needed(" in source
    assert "metric_outputs.run_manifest_step_if_needed(" in source
    assert "metric_outputs.run_slurm_step_if_needed(" in source
    assert "metric_outputs.run_merge_step_if_needed(" in source
    assert "metric_outputs.run_downstream_outputs_step_if_needed(" in source
    assert "metric_outputs.display_metrics_preview(nrows=PREVIEW_ROWS)" in source
    assert "display(metric_settings_summary(metric_settings))" in source
    assert 'print(f"Metric batch count: {METRIC_BATCH_COUNT}")' not in source
    assert "step_outputs.display_table_previews(" not in source
    assert "step_outputs.preview_table(" not in source
    assert "metrics_preview =" not in source
    assert "Metric output is not ready yet" not in source
    assert "preview_output_table(" not in source
    assert "batch_count=METRIC_BATCH_COUNT" in source
    assert "batch_count=context.metric_batch_count" not in source
    assert 'os.environ.get("SVTK_METRIC_BATCH_COUNT"' not in source
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
    assert "metric_outputs.write_configured_outputs(" in source
    assert "display_notebook_step_result," in source
    assert "write_metric_outputs_from_config(" not in source
    assert "metric_settings_summary," in source
    assert "metrics_settings_from_config," in source
    assert "from spatial_vtk.config.metrics import" not in source
    assert "load_standard_metric_workflow_outputs," in source
    assert "metric_outputs = load_standard_metric_workflow_outputs(cfg=cfg)" in source
    assert "load_task_estimate=False" not in source
    assert "metric_outputs = metric_outputs.with_task_estimate()" in source
    assert 'step_outputs = output_group("step_03_metrics", cfg=cfg)' not in source
    assert "render_notebook_figure(" not in source
    assert "write_standard_metric_diagnostic_figures(" not in source
    assert "metric_outputs.write_standard_diagnostic_figures(" in source
    assert "metric_outputs.write_station_metric_map(" in source
    assert "metric_diagnostic_result.preview_frame()" in source
    assert "metric_diagnostic_result.status_frame()" in source
    assert "standard residual-distance, score-trend, and band residual-distribution diagnostics" in source
    assert "standard residual-distance, GOF-distance, and band-distribution diagnostics" not in source
    assert "metric_outputs.display_task_previews(nrows=12)" in source
    assert "metric_outputs.display_metrics_preview(nrows=5)" in source
    assert 'display_notebook_step_result(task_preview_result, label="Metric task preview", display=display)' in source
    assert 'display_notebook_step_result(metric_output_result, label="Metric output tables", display=display)' in source
    assert "print(task_preview_result)" not in source
    assert "print(metric_output_result)" not in source
    assert "figure_metrics = metric_outputs.load_metrics_long()" not in source
    assert "metric_outputs.outputs," not in source
    assert "step_outputs.display_table_previews(" not in source
    assert 'metric_names=("PGA", "PGV", "PGD")' in source
    assert "metric_rows_for_metrics(" not in source
    assert "station_pga[[" not in source
    assert 'figure_metrics.loc[figure_metrics["metric"].isin' not in source
    assert "plot_residuals_vs_distance(" not in source
    assert "plot_score_trends(" not in source
    assert "plot_band_score_distribution(" not in source
    assert "metric_tasks.head(" not in source
    assert "metrics_long.head(" not in source
    assert "load_output_table(" not in source
    assert "summarize_metric_tasks(" not in source
    assert "write_metric_outputs(" not in source
    assert "drop_duplicates().copy()" not in source
    assert 'read_config_table("paths.metric_figure_snapshot")' not in source
    assert "metric_sidecars" not in source
    assert "savefig=True" not in source
    assert "showfig=True" not in source


def test_large_run_step01_uses_package_functions_for_heavy_steps() -> None:
    """Step 1 should call package workflow helpers instead of CLI or inline worker code."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_01_large_run_ingest_and_prepare_data.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "run_notebook_step_if_needed(" not in source
    assert "ingest_outputs.run_metadata_step_if_needed(" in source
    assert "ingest_outputs.run_preprocessing_step_if_needed(" in source
    assert "ingest_outputs.run_record_coverage_step_if_needed(" in source
    assert "metadata_readiness = metadata_tables_readiness_from_config(" not in source
    assert "preprocess_readiness = preprocessing_readiness_from_config(" not in source
    assert "record_coverage_readiness = record_coverage_readiness_from_config(" not in source
    assert "step_outputs.readiness(" not in source
    assert "preprocessed_outputs.readiness(" not in source
    assert "run_or_submit_notebook_function(" not in source
    assert "from spatial_vtk.io import (" in source
    assert "load_standard_ingest_workflow_outputs," in source
    assert "metadata_tables_readiness_from_config," not in source
    assert "preprocessing_readiness_from_config," not in source
    assert "ingest_outputs = load_standard_ingest_workflow_outputs(cfg=cfg)" in source
    assert "step_outputs = ingest_outputs.outputs" not in source
    assert "preprocessed_outputs = ingest_outputs.preprocessed_outputs" not in source
    assert "display(ingest_outputs.status_frame())" in source
    assert 'step_outputs = output_group("step_01_ingest")' not in source
    assert "preprocessed_outputs = preprocessed_waveform_output_group(config=cfg)" not in source
    assert "display(ingest_outputs.metadata_summary_frame())" in source
    assert "metadata_tables = step_outputs.load_tables(" not in source
    assert "stations = metadata_tables" not in source
    assert "event_stations = metadata_tables" not in source
    assert "print(f\"stations={len(stations):,}" not in source
    assert "ingest_outputs.write_context_figures(" in source
    assert "write_large_run_context_figures_from_outputs(" not in source
    assert "context_figure_result.status_frame()" in source
    assert "context_tables = step_outputs.load_tables(" not in source
    assert "load_output_table(" not in source
    assert "prepare_metadata_tables_from_config," not in source
    assert "preprocess_waveforms_from_config," not in source
    assert "build_record_coverage_from_config," not in source
    assert "record_coverage_readiness_from_config," not in source
    assert "PREPROCESS_CONTINUE_ON_ERROR = context.preprocess_continue_on_error" in source
    assert 'print(f"PREPROCESS_CONTINUE_ON_ERROR={PREPROCESS_CONTINUE_ON_ERROR}")' not in source
    assert 'os.environ.get("SVTK_PREPROCESS_CONTINUE_ON_ERROR"' not in source
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


def test_large_run_step02_uses_qc_result_figure_writer() -> None:
    """The large-run QC notebook should let the QC result own compact figures."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_02_large_run_quality_control.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "step_outputs.bind(globals())" not in source
    assert "step_outputs" not in source
    assert "availability_path," not in source
    assert "qc_outputs.write_figures(" in source
    assert "write_large_run_qc_figures_from_outputs(" not in source
    assert "qc_figure_result.status_frame()" in source
    assert '"qc_availability": "availability_path"' not in source
    assert 'qc_availability = qc_figure_tables["qc_availability"]' not in source
    assert 'load_output_table("qc_availability")' not in source
    assert "plot_data_synthetic_availability(" not in source
    assert "Observed/Synthetic Availability (Post-QC Trace Overlap)" not in source


def test_large_run_step02_uses_package_functions_for_heavy_steps() -> None:
    """Step 2 should call package workflow helpers instead of CLI or inline worker code."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_02_large_run_quality_control.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "run_notebook_step_if_needed(" not in source
    assert "run_or_submit_notebook_function(" not in source
    assert "from spatial_vtk.qc import (" in source
    assert "metric_settings_summary," in source
    assert "load_standard_qc_workflow_outputs," in source
    assert "metrics_settings_from_config," in source
    assert "QC_OVERLAP_SCOPE = metric_settings.source_overlap_scope" in source
    assert "display(metric_settings_summary(metric_settings))" in source
    assert 'print(f"QC overlap scope: {QC_OVERLAP_SCOPE}")' not in source
    assert "qc_outputs = load_standard_qc_workflow_outputs(cfg=cfg)" in source
    assert "step_outputs = qc_outputs.outputs" not in source
    assert "display(qc_outputs.status_frame())" in source
    assert "qc_outputs.display_summary_previews(nrows=PREVIEW_ROWS)" in source
    assert 'from spatial_vtk.io import output_group' not in source
    assert 'step_outputs = output_group("step_02_qc")' not in source
    assert "run_qc_inventory_from_config," not in source
    assert "write_qc_inventory_overlap_from_config," not in source
    assert "run_qc_summary_workflow_from_config," not in source
    assert "qc_inventory_readiness_from_config," not in source
    assert "qc_overlap_readiness_from_config," not in source
    assert "qc_summary_readiness_from_config," not in source
    assert "qc_outputs.run_inventory_step_if_needed(" in source
    assert "qc_outputs.run_overlap_step_if_needed(" in source
    assert "scope=QC_OVERLAP_SCOPE" in source
    assert "qc_outputs.run_summary_step_if_needed(" in source
    assert "qc_outputs.write_figures(" in source
    assert "write_large_run_qc_figures_from_outputs(" not in source
    assert "qc_readiness = qc_inventory_readiness_from_config(" not in source
    assert "overlap_readiness = qc_overlap_readiness_from_config(" not in source
    assert "summary_readiness = qc_summary_readiness_from_config(" not in source
    assert "step_outputs.readiness(" not in source
    assert "qc_figure_tables = step_outputs.load_tables(" not in source
    assert "step_outputs.qc_inventory_overlap_path.exists()" not in source
    assert '"spatial_vtk.qc.run_qc_inventory_from_config"' not in source
    assert '"spatial_vtk.qc.write_qc_inventory_overlap_from_config"' not in source
    assert '"spatial_vtk.qc.run_qc_summary_workflow_from_config"' not in source
    assert "run_or_submit_notebook_cli_command(" not in source
    assert "write_notebook_python_slurm_script" not in source
    assert "submit_notebook_slurm_script" not in source
    assert "write_qc_slurm_script(" not in source


def test_large_run_optional_figure_cells_use_package_settings() -> None:
    """Large-run optional figure cells should centralize figure settings."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = [
        repo_root / "docs" / "examples" / "large_run" / "step_01_large_run_ingest_and_prepare_data.ipynb",
        repo_root / "docs" / "examples" / "large_run" / "step_02_large_run_quality_control.ipynb",
        repo_root / "docs" / "examples" / "large_run" / "step_03_large_run_calculate_metrics.ipynb",
        repo_root / "docs" / "examples" / "large_run" / "step_04_large_run_spatial_statistics.ipynb",
        repo_root / "docs" / "examples" / "large_run" / "step_05_large_run_geojson_corridors.ipynb",
        repo_root / "docs" / "examples" / "large_run" / "step_06_large_run_additional_plotting.ipynb",
    ]
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        assert "notebook_figure_settings(" in source
        assert 'os.environ.get("SVTK_MAKE_FIGURES"' not in source
        assert 'os.environ.get("SVTK_ADD_BASEMAP"' not in source
        assert 'notebook_figure_sidecar_settings(' not in source

    step_01_source = "\n".join(
        "".join(cell.get("source", []))
        for cell in json.loads(notebooks[0].read_text(encoding="utf-8")).get("cells", [])
    )
    assert "CONTEXT_FIGURE_SETTINGS.plot_kwargs(include_basemap=True)" in step_01_source
    step_02_source = "\n".join(
        "".join(cell.get("source", []))
        for cell in json.loads(notebooks[1].read_text(encoding="utf-8")).get("cells", [])
    )
    assert "QC_FIGURE_SETTINGS.plot_kwargs(include_basemap=True)" in step_02_source


def test_large_run_step02_overlap_sidecar_has_separate_rebuild_gate() -> None:
    """Step 2 should rebuild full QC only from full-QC readiness inputs."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_02_large_run_quality_control.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "qc_outputs.run_inventory_step_if_needed(" in source
    assert "qc_outputs.run_overlap_step_if_needed(" in source
    assert "scope=QC_OVERLAP_SCOPE" in source
    assert "qc_outputs.run_summary_step_if_needed(" in source
    assert "qc_readiness = qc_inventory_readiness_from_config(" not in source
    assert "config_path=config_path" not in source
    assert "overwrite=OVERWRITE" in source
    assert "run_notebook_step_if_needed(" not in source
    assert "Full QC outputs are current; skipping QC Slurm submission." in source
    assert '"event_station_records": str(step_outputs.event_station_path)' not in source
    assert '"trace_qc_output": str(step_outputs.trace_qc_path)' not in source
    assert '"qc_inventory_output": str(step_outputs.qc_inventory_path)' not in source
    assert '"qc_inventory_overlap_output": str(step_outputs.qc_inventory_overlap_path)' not in source
    assert "should_rebuild_paths(trace_qc_path, qc_inventory_path, overwrite=OVERWRITE)" not in source
    assert "should_rebuild_paths(trace_qc_path, qc_inventory_path, qc_inventory_overlap_path" not in source
    assert "overlap_readiness = qc_overlap_readiness_from_config(" not in source
    assert "summary_readiness = qc_summary_readiness_from_config(" not in source
    assert "step_outputs.readiness(" not in source
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
        if notebook_path == step_01:
            assert "ingest_outputs = load_standard_ingest_workflow_outputs(cfg=cfg)" in source
            assert "preprocessed_outputs = ingest_outputs.preprocessed_outputs" not in source
            assert "preprocessed_waveform_output_group(config=cfg)" not in source
            assert "ingest_outputs.run_preprocessing_step_if_needed(" in source
            assert "preprocess_readiness = preprocessing_readiness_from_config(" not in source
            assert "preprocessed_outputs.readiness(" not in source
            assert "record_coverage_readiness_from_config(" not in source
            assert "source_event_station_path" not in source
            assert "preprocess_readiness = output_readiness(" not in source
            assert "record_coverage_readiness = output_readiness(" not in source
            assert "preview_output_table" not in source
            assert "preview_table" not in source
        else:
            assert "metric_outputs.metrics_long_path" in source
            assert "trace_metadata_path = metric_outputs.trace_metadata_path" not in source
            assert "preprocessed_waveform_metadata_paths(config=cfg)" not in source
        assert re.search(r"(?<!waveform_)preprocessing_manifest\.csv", source) is None
        assert 'outputs_root / "preprocessed_waveforms"' not in source


def test_step05_uses_geojson_preview_helper() -> None:
    """The map tutorial should use package helpers and public spatial imports."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "step_05_maps_and_figures.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "from spatial_vtk.spatial import load_standard_geojson_plotting_inputs" in source
    assert "from spatial_vtk.spatial.plot import load_standard_geojson_plotting_inputs" not in source
    assert "load_standard_geojson_plotting_inputs" in source
    assert "geojson_inputs = load_standard_geojson_plotting_inputs(cfg=cfg)" in source
    assert "geojson_inputs.status_frame()" in source
    assert "from spatial_vtk.spatial import (" not in source
    assert "from spatial_vtk.spatial.map import" not in source
    assert "step_outputs = output_group(\"step_05_geojson\", cfg=cfg)" not in source
    assert "plotting_tables = step_outputs.load_tables(" not in source
    assert "render_notebook_figure(" not in source
    assert "station_metric_map_path" not in source
    assert "corridor_map_path" not in source
    assert "record_section_figure_path" not in source
    assert "from spatial_vtk.spatial.calculate import" not in source
    assert "from spatial_vtk.spatial.map." not in source
    assert "from spatial_vtk.spatial.plot." not in source
    assert "geojson_inputs.write_region_figures(" in source
    assert "geojson_inputs.write_corridor_figures(" in source
    assert "write_standard_geojson_region_figures(" not in source
    assert "write_standard_geojson_corridor_figures(" not in source
    assert "geojson_region_result.metrics_by_regions" in source
    assert "plot_geojson_polygons_map(" not in source
    assert "boxplot(" not in source
    assert "first_nonempty_table_value(metrics, \"model\", fallback=\"model\")" not in source
    assert "metrics[\"model\"].dropna().astype(str).iloc[0]" not in source
    assert "event_ids_from_records(" not in source
    assert "event_rows_for_records(" not in source
    assert "event_label_preview_frame(" not in source
    assert "event_station_records_matching_pairs(" not in source
    assert "geojson_matched_record_frame(" not in source
    assert 'events.loc[events["event_id"].astype(str).isin' not in source
    assert '["event_id"].dropna().astype(str).unique()' not in source
    assert '[["event_id", "event_name"]].drop_duplicates()' not in source
    assert 'central_boundary_paths.loc[central_boundary_paths["path_geojson_matches"]]' not in source
    assert '.merge(selected_pairs, on=["event_id", "station"], how="inner")' not in source
    assert '.merge(pgv_corridor_pairs, on=["event_id", "station"], how="inner")' not in source
    assert "geojson_polygon_preview_table(" not in source
    assert "load_configured_input_paths(" not in source
    assert "ingest_outputs = output_group(\"step_01_ingest\", cfg=cfg)" not in source
    assert "ingest_tables = ingest_outputs.load_tables(" not in source
    assert "output_group(\"step_01_ingest\", cfg=cfg).load_tables(" not in source
    assert "figure_dir /" not in source
    assert "load_output_table(" not in source
    assert "load_geojson_polygons(" not in source
    assert "region_preview = pd.DataFrame(" not in source


def test_step06_uses_comparison_eligible_output_table() -> None:
    """The plotting tutorial should reuse QC outputs instead of re-filtering metrics."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "step_06_additional_plotting_options.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "plotting_inputs = load_standard_additional_plotting_inputs(cfg=cfg)" in source
    assert "from spatial_vtk.spatial import load_standard_additional_plotting_inputs" in source
    assert "from spatial_vtk.spatial.plot import load_standard_additional_plotting_inputs" not in source
    assert "plotting_inputs.status_frame()" in source
    assert "ingest_outputs = output_group(\"step_01_ingest\", cfg=cfg)" not in source
    assert "ingest_tables = ingest_outputs.load_tables(" not in source
    assert "output_group(\"step_01_ingest\", cfg=cfg).load_tables(" not in source
    assert "step_outputs = output_group(\"step_06_plotting\", cfg=cfg)" not in source
    assert "plotting_tables = step_outputs.load_tables(" not in source
    assert "write_standard_additional_plotting_figures(" not in source
    assert "plotting_inputs.write_figures(" in source
    assert "metrics = plotting_inputs.metrics" not in source
    assert "event_stations = plotting_inputs.event_stations" not in source
    assert "events = plotting_inputs.events" not in source
    assert "comparison_eligible = plotting_inputs.comparison_eligible" not in source
    assert "step_outputs = plotting_inputs.outputs" not in source
    assert "additional_plot_result.metric_summary_frame()" in source
    assert "additional_plot_result.waveform_order_frame()" in source
    assert "additional_plot_result.pattern_preview_frame()" in source
    assert "additional_plot_result.pattern_frame().head()" not in source
    assert "additional_plot_result.status_frame()" in source
    assert "render_notebook_figure(" not in source
    assert "station_event_waveform_map_path" not in source
    assert "pattern_similarity_figure_path" not in source
    assert "scatterplot_figure_path" not in source
    assert "boxplot_figure_path" not in source
    assert "heatmap_figure_path" not in source
    assert "step_outputs.figure_path(" not in source
    assert "outpath=" not in source
    assert "savefig=True" not in source
    assert "showfig=True" not in source
    assert "waveform_sidecars" not in source
    assert "metric_sidecars" not in source
    assert "load_output_table(" not in source
    assert "figure_dir /" not in source
    assert "geojson_metric_region_frame(" not in source
    assert "from spatial_vtk.spatial import add_geojson_metadata_to_metrics" not in source
    assert "metric_plot_input_summary_frame(" not in source
    assert "event_display_label(events, waveform_event_id)" not in source
    assert "station_event_waveform_order_frame(waveform_records, max_traces=12)" not in source
    assert "build_qc_waveform_comparison_records(" not in source
    assert "plot_station_event_waveform_map(" not in source
    assert "plot_pattern_similarity(" not in source
    assert "scatterplot(" not in source
    assert "boxplot(" not in source
    assert "heatmap(" not in source
    assert 'waveform_records[["station", "distance_km"]].sort_values("distance_km").head(12)' not in source
    assert '.eq(waveform_event_id), "event_name"' not in source
    assert "pd.DataFrame(" not in source
    assert "from spatial_vtk.spatial.calculate import" not in source
    assert "load_configured_input_tables(" not in source
    assert 'read_config_table("paths.metric_figure_snapshot")' not in source
    assert 'cfg.path("paths.metric_figure_snapshot")' not in source
    assert "read_table(metric_source_path)" not in source
    assert "comparison_qc_status" not in source


def test_large_run_step06_uses_grouped_table_loading() -> None:
    """The large-run plotting notebook should delegate workflow plotting to helpers."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_06_large_run_additional_plotting.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "load_standard_additional_plotting_output_status" in source
    assert "from spatial_vtk.spatial import load_standard_additional_plotting_output_status" in source
    assert "from spatial_vtk.spatial.plot import load_standard_additional_plotting_output_status" not in source
    assert "plotting_outputs = load_standard_additional_plotting_output_status(cfg=cfg)" in source
    assert "plotting_outputs.write_waveform_comparison(" in source
    assert "write_waveform_comparison_from_notebook_settings(" not in source
    assert "step_outputs" not in source
    assert "waveform_result.status_frame()" in source
    assert "waveform_figure_gate = WAVEFORM_FIGURE_SETTINGS.render_gate(" not in source
    assert "write_waveform_comparison_from_outputs(" not in source
    assert "write_large_run_waveform_comparison_from_outputs(" not in source
    assert "build_qc_waveform_comparison_records(" not in source
    assert "load_comparison_eligible_records(" not in source
    assert "plot_event_trace_comparison(" not in source
    assert "event_stations = plotting_outputs.load_table(" not in source
    assert "plotting_outputs.display_metric_source_preview(nrows=PREVIEW_ROWS)" in source
    assert "plotting_outputs.display_metric_source_preview(cfg=cfg" not in source
    assert "plotting_outputs.display_first_existing_table_preview(" not in source
    assert "plotting_outputs.preview_first_existing_table(" not in source
    assert "plotting_outputs.write_region_boxplot(" in source
    assert "display(region_result.status_frame())" in source
    assert "print(region_result.message)" not in source
    assert "write_large_run_region_boxplot_from_notebook_settings(" not in source
    assert "write_large_run_region_boxplot_from_outputs(" not in source
    assert "region_figure_gate = REGION_FIGURE_SETTINGS.render_gate(" not in source
    assert "step_outputs.first_existing_path(" not in source
    assert "load_output_table(" not in source
    assert "preview_output_table(" not in source
    assert "preview_output_table(" not in source


def test_large_run_step03_metric_figures_are_auditable_station_aggregations() -> None:
    """Large-run metric figures should expose provenance for station summaries."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_03_large_run_calculate_metrics.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "METRIC_FIGURE_SETTINGS = notebook_figure_settings(" in source
    assert 'figure_subdir="metrics"' in source
    assert "METRICS_FIGURE_DIR" not in source
    assert 'figures_dir / "metrics"' not in source
    assert "STATION_AGGREGATION = METRIC_FIGURE_SETTINGS.station_aggregation" not in source
    assert "**METRIC_FIGURE_SETTINGS.context_kwargs(include_station_aggregation=True)" not in source
    assert "METRIC_FIGURE_SETTINGS.plot_selection_kwargs(" not in source
    assert "metric_outputs.write_large_run_figure_suite(" in source
    assert "write_large_run_metric_figure_suite_from_notebook_settings(" not in source
    assert "metric_plot_context = metric_figure_suite.context" not in source
    assert "display(metric_figure_suite.status_frame())" in source
    assert "metric_figure_suite.display_context_status(display=display)" in source
    assert "display(metric_plot_context.spectral_metric_contract_status())" not in source
    assert "if metric_plot_context.ready:" not in source
    assert "MAKE_METRIC_FIGURES and step_outputs.metrics_long_path.exists()" not in source
    assert "PLOT_VALUE_COL in metrics_for_figures.columns" not in source
    assert "MAKE_METRIC_FIGURES and metric_plot_context.ready" not in source

    assert "metric_plot_context.write_station_metric_maps(" not in source
    assert "metric_plot_context.write_residual_grid_maps(" not in source
    assert "metric_plot_context.write_metric_by_model_maps(" not in source
    assert "metric_plot_context.write_event_residual_maps(" not in source
    assert "for item in iter_metric_frames(" not in source
    assert "station_summary_for_item(item, PLOT_VALUE_COL)" not in source
    assert "station_grid_for_item(item, PLOT_VALUE_COL)" not in source
    assert "source_df=item_source_rows(item)" not in source
    assert "source_df_factory=item_source_rows" not in source


def test_large_run_step04_spatial_figures_show_spectral_contract_status() -> None:
    """Large-run spatial figures should expose PSA/FAS contract checks."""

    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = repo_root / "docs" / "examples" / "large_run" / "step_04_large_run_spatial_statistics.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "spatial_figure_suite = spatial_outputs.write_figure_suite(" in source
    assert "write_large_run_spatial_figure_suite_from_notebook_settings(" not in source
    assert "spatial_figures = spatial_figure_suite.context" not in source
    assert "spatial_figure_suite.display_context_status(display=display)" in source
    assert 'figure_subdir="metrics"' in source
    assert "SPATIAL_FIGURE_SETTINGS.figure_dir" not in source
    assert "METRICS_FIGURE_DIR" not in source
    assert 'figures_dir / "metrics"' not in source
    assert "display(spatial_figures.status_frame())" not in source
    assert "display(spatial_figures.dimension_summary_frame())" not in source
    assert "display(spatial_figures.spectral_metric_contract_status())" not in source
    assert "display(spatial_figure_suite.status_frame())" in source


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
    """Notebook sidecar calls should use package-managed figure directories."""

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


def test_tutorial_notebooks_use_package_figure_settings() -> None:
    """Tutorial notebooks should centralize figure settings in package helpers."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = [
        repo_root / "docs" / "examples" / f"step_{index:02d}_{name}.ipynb"
        for index, name in (
            (1, "ingest_and_prepare_data"),
            (2, "quality_control"),
            (3, "calculate_metrics"),
            (4, "spatial_statistics"),
            (5, "maps_and_figures"),
            (6, "additional_plotting_options"),
        )
    ]
    notebooks.extend(sorted((repo_root / "docs" / "examples" / "large_run").glob("step_0*.ipynb")))

    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        assert "notebook_figure_settings(" in source, notebook_path.relative_to(repo_root)
        assert 'notebook_figure_sidecar_settings(' not in source, notebook_path.relative_to(repo_root)
        assert 'os.environ.get("SVTK_ADD_BASEMAP"' not in source, notebook_path.relative_to(repo_root)
        if "large_run" not in notebook_path.parts:
            assert "figure_dir = context.figures_dir" not in source, notebook_path.relative_to(repo_root)
            assert "figure_dir.mkdir(" not in source, notebook_path.relative_to(repo_root)
            assert "figure_dir=figure_dir" not in source, notebook_path.relative_to(repo_root)


def test_tutorial_notebooks_avoid_low_level_io_and_shell_workflow_cells() -> None:
    """Tutorial notebooks should use task-level package helpers, not path plumbing."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = sorted((repo_root / "docs" / "examples").rglob("*.ipynb"))
    assert notebooks
    forbidden_patterns = (
        "resolve_output_path(",
        "load_output_table(",
        "write_output_table(",
        "write_output_tables(",
        "read_config_table(",
        "pd.read_",
        ".to_csv(",
        ".to_parquet(",
        "subprocess.run(",
        "run_or_submit_notebook_cli_command(",
        "run_or_submit_notebook_function(",
        "display_table_previews(cfg=",
        "display_metric_source_preview(cfg=",
        "display_dashboard_output_previews(",
        "preview_dashboard_summary_tables(",
        "preview_output_table(",
        "display_output_table_previews(",
        "svtk ",
    )
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            matches = [pattern for pattern in forbidden_patterns if pattern in source]
            assert not matches, f"{notebook_path.relative_to(repo_root)} cell {index} uses {matches}"


def test_large_run_notebooks_use_figure_render_gates_for_prerequisite_tables() -> None:
    """Large-run figure cells should report missing inputs through package gates."""

    repo_root = Path(__file__).resolve().parents[1]
    notebooks = [
        repo_root / "docs" / "examples" / "large_run" / "step_01_large_run_ingest_and_prepare_data.ipynb",
        repo_root / "docs" / "examples" / "large_run" / "step_02_large_run_quality_control.ipynb",
        repo_root / "docs" / "examples" / "large_run" / "step_04_large_run_spatial_statistics.ipynb",
        repo_root / "docs" / "examples" / "large_run" / "step_05_large_run_geojson_corridors.ipynb",
        repo_root / "docs" / "examples" / "large_run" / "step_06_large_run_additional_plotting.ipynb",
    ]
    for notebook_path in notebooks:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        assert ".render_gate(" in source, notebook_path.relative_to(repo_root)
        assert "gate.status_frame()" in source, notebook_path.relative_to(repo_root)
        assert "all(path.exists() for path in required)" not in source, notebook_path.relative_to(repo_root)


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
        "docs/examples/step_03_calculate_metrics.ipynb": (
            "metric_figure_settings.sidecars.readiness_frame()",
            "metric_figure_settings.sidecars.status_frame()",
        ),
        "docs/examples/step_04_spatial_statistics.ipynb": (
            "spatial_figure_settings.sidecars.readiness_frame()",
            "spatial_figure_settings.sidecars.status_frame()",
        ),
        "docs/examples/large_run/step_03_large_run_calculate_metrics.ipynb": (
            "METRIC_FIGURE_SETTINGS.sidecars.readiness_frame()",
            "METRIC_FIGURE_SETTINGS.sidecars.status_frame()",
        ),
        "docs/examples/large_run/step_04_large_run_spatial_statistics.ipynb": (
            "SPATIAL_FIGURE_SETTINGS.sidecars.readiness_frame()",
            "SPATIAL_FIGURE_SETTINGS.sidecars.status_frame()",
        ),
    }
    for relative_path, calls in expected.items():
        notebook = json.loads((repo_root / relative_path).read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        for call in calls:
            assert call in source
        for forbidden in (
            "metric_figure_settings.status_frame()",
            "spatial_figure_settings.status_frame()",
            "METRIC_FIGURE_SETTINGS.status_frame()",
            "SPATIAL_FIGURE_SETTINGS.status_frame()",
        ):
            assert forbidden not in source


def test_large_run_aggregated_station_figures_pass_source_rows_to_sidecars() -> None:
    """Large-run station aggregation figures should keep raw-row provenance."""

    repo_root = Path(__file__).resolve().parents[1]
    metric_context_source = (
        repo_root / "src" / "spatial_vtk" / "metrics" / "plot" / "large_run.py"
    ).read_text(encoding="utf-8")
    spatial_context_source = (
        repo_root / "src" / "spatial_vtk" / "spatial" / "plot" / "large_run.py"
    ).read_text(encoding="utf-8")
    requirements = {
        "docs/examples/large_run/step_03_large_run_calculate_metrics.ipynb": (
            "metric_outputs.write_large_run_figure_suite(",
            "metric_figure_suite.status_frame()",
            "metric_figure_suite.display_context_status(display=display)",
        ),
        "docs/examples/large_run/step_04_large_run_spatial_statistics.ipynb": (
            "spatial_outputs.write_figure_suite(",
            "spatial_figure_suite.status_frame()",
            "spatial_figure_suite.display_context_status(display=display)",
        ),
    }
    for relative_path, snippets in requirements.items():
        notebook = json.loads((repo_root / relative_path).read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
        for snippet in snippets:
            assert snippet in source, f"{relative_path} is missing provenance snippet {snippet!r}"
    assert "source_df=self.item_source_rows(item)" in spatial_context_source
    assert "source_df_factory=self.item_source_rows" in spatial_context_source
    assert "source_df=self.item_source_rows(item)" in metric_context_source
    assert "source_df_factory=self.item_source_rows" in metric_context_source


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
