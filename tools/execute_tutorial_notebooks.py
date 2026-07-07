#!/usr/bin/env python3
"""Execute the standard tutorial notebooks from a source checkout.

This is a lightweight release/source-check helper. It runs the committed
standard tutorial notebooks against the committed example data, optionally
clears the tutorial output directory first, and writes a JSON execution report.
The runtime check verifies both Jupyter execution modules and the package
runtime modules the notebooks import. The script does not save executed
notebooks back to the repository.
"""

from __future__ import annotations

import argparse
import ast
import csv
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys
import time
from typing import Any


STANDARD_TUTORIAL_NOTEBOOKS = (
    "docs/examples/step_01_ingest_and_prepare_data.ipynb",
    "docs/examples/step_02_quality_control.ipynb",
    "docs/examples/step_03_calculate_metrics.ipynb",
    "docs/examples/step_04_spatial_statistics.ipynb",
    "docs/examples/step_05_maps_and_figures.ipynb",
    "docs/examples/step_06_additional_plotting_options.ipynb",
    "docs/examples/step_07_dashboards.ipynb",
)
LARGE_RUN_TUTORIAL_NOTEBOOKS = (
    "docs/examples/large_run/step_01_large_run_ingest_and_prepare_data.ipynb",
    "docs/examples/large_run/step_02_large_run_quality_control.ipynb",
    "docs/examples/large_run/step_03_large_run_calculate_metrics.ipynb",
    "docs/examples/large_run/step_04_large_run_spatial_statistics.ipynb",
    "docs/examples/large_run/step_05_large_run_geojson_corridors.ipynb",
    "docs/examples/large_run/step_06_large_run_additional_plotting.ipynb",
)

WARNING_PATTERN = re.compile(
    r"traceback \(most recent call last\)|"
    r"\b(?:runtime|user|future|deprecation|pendingdeprecation|syntax|resource|import|unicode|bytes|encoding|numpy|pandas|matplotlib)?warning\s*:|"
    r"\bwarning\s+\[[^\]]+\]|"
    r"\bWARNING\s*:",
    re.IGNORECASE,
)
FALLBACK_SUPPORTED_TUTORIAL_PYTHON_RANGE = ">=3.10,<3.14"
FALLBACK_NOTEBOOK_RUNTIME_MODULES = {
    "spatial_vtk": "spatial_vtk",
    "nbformat": "nbformat",
    "nbclient": "nbclient",
    "ipykernel": "ipykernel",
    "IPython": "IPython",
    "branca": "branca",
    "contextily": "contextily",
    "folium": "folium",
    "geopandas": "geopandas",
    "gmprocess": "gmprocess",
    "h5py": "h5py",
    "matplotlib": "matplotlib",
    "numpy": "numpy",
    "obspy": "obspy",
    "pandas": "pandas",
    "phasenet": "phasenet",
    "plotly": "plotly",
    "pyarrow": "pyarrow",
    "pyasdf": "pyasdf",
    "pyproj": "pyproj",
    "PyYAML": "yaml",
    "rasterio": "rasterio",
    "scikit-learn": "sklearn",
    "scipy": "scipy",
    "shapely": "shapely",
    "statsmodels": "statsmodels",
    "streamlit": "streamlit",
    "streamlit-folium": "streamlit_folium",
}


def _validation_checker_module() -> Any | None:
    """Return the validation checker module when it can be loaded."""

    checker_path = Path(__file__).with_name("check_validation_environment.py")
    if not checker_path.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location("_svtk_validation_checker", checker_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


def _tutorial_runtime_modules_from_validation_checker() -> dict[str, str]:
    """Return tutorial runtime imports from the validation checker contract."""

    module = _validation_checker_module()
    if module is None:
        return dict(FALLBACK_NOTEBOOK_RUNTIME_MODULES)
    try:
        runtime: dict[str, str] = {}
        for group in module.normalize_groups(["tutorial"]):
            for requirement in module.MODULE_GROUPS[group]:
                runtime.setdefault(requirement.label, requirement.module)
        return runtime or dict(FALLBACK_NOTEBOOK_RUNTIME_MODULES)
    except Exception:
        return dict(FALLBACK_NOTEBOOK_RUNTIME_MODULES)


NOTEBOOK_RUNTIME_MODULES = _tutorial_runtime_modules_from_validation_checker()
SOURCE_CHECKOUT_TUTORIAL_INSTALL_COMMAND = (
    'python -m pip install -e ".[validation,docs,dashboard,notebooks,waveforms]"'
)
SOURCE_CHECKOUT_TUTORIAL_CONDA_COMMAND = "conda env create -f svtk_environment.yaml"
SOURCE_CHECKOUT_TUTORIAL_VALIDATION_COMMAND = "python tools/check_validation_environment.py --groups tutorial"
SOURCE_CHECKOUT_TUTORIAL_RUNTIME_CHECK_COMMAND = (
    "MPLCONFIGDIR=/tmp/mplconfig_svtk "
    "python tools/execute_tutorial_notebooks.py --runtime-check-only --include-large-run"
)
KERNEL_EXTRA_ARGUMENTS = ("--IPKernelApp.log_level=ERROR",)
TUTORIAL_EXAMPLE_ROOT = Path("data/examples/example_five_event_subset")
TUTORIAL_SYNTHETIC_MODEL = "cvmsi_20260506_material_0p6x1p2_asdf"
TUTORIAL_REQUIRED_FILES = (
    Path("data/examples/configuration/example_spatial_vtk_config.yaml"),
    TUTORIAL_EXAMPLE_ROOT / "metadata" / "events.csv",
    TUTORIAL_EXAMPLE_ROOT / "metadata" / "selected_stations.csv",
    TUTORIAL_EXAMPLE_ROOT / "metadata" / "selected_event_stations.csv",
    TUTORIAL_EXAMPLE_ROOT / "metadata" / "example_path_regions.geojson",
    Path("data/examples/data_formats/example_site_metadata.csv"),
    Path("data/examples/data_formats/example_metrics_snapshot.csv"),
    Path("data/examples/data_formats/example_metrics_large_qc_passed.parquet"),
)
NOTEBOOK_CONTRACT_FORBIDDEN_SNIPPETS = (
    "import subprocess",
    "from subprocess",
    "subprocess.",
    "os.system(",
    "os.popen(",
    "get_ipython().system(",
    "run_or_submit_notebook_cli_command(",
    "write_notebook_cli_slurm_script(",
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
    "resolve_output_path(",
    "load_output_table(",
    "write_output_table(",
    "write_output_tables(",
    "preview_output_table(",
    "read_config_table(",
    "output_group_namespace",
    "output_group_status_frame",
    "step_outputs[",
    "dashboard_paths[",
    ".bind(globals())",
    "vars(step_outputs)",
    "runs/outputs",
    "runs/spatial_vtk_config.yaml",
    "pd.read_",
    ".to_csv(",
    ".to_parquet(",
    "subprocess.run(",
    ".loc[",
    ".query(",
    ".isin(",
    ".merge(",
    ".groupby(",
    ".pivot",
    ".sort_values(",
    ".drop_duplicates(",
)
NOTEBOOK_CONTRACT_SNIPPET_REMEDIATIONS = {
    "import subprocess": "Use package workflow helpers from spatial_vtk instead of shelling out from notebooks.",
    "from subprocess": "Use package workflow helpers from spatial_vtk instead of shelling out from notebooks.",
    "subprocess.": "Use package workflow helpers from spatial_vtk instead of shelling out from notebooks.",
    "subprocess.run(": "Use package workflow helpers from spatial_vtk instead of shelling out from notebooks.",
    "os.system(": "Use package workflow helpers from spatial_vtk instead of shelling out from notebooks.",
    "os.popen(": "Use package workflow helpers from spatial_vtk instead of shelling out from notebooks.",
    "get_ipython().system(": "Use package workflow helpers from spatial_vtk instead of shelling out from notebooks.",
    "run_or_submit_notebook_cli_command(": "Use imported package callables with run_notebook_step_if_needed.",
    "write_notebook_cli_slurm_script(": "Use imported package callables with run_notebook_step_if_needed.",
    "resolve_output_path(": "Use standard workflow result objects or notebook_run_context helpers for configured outputs.",
    "load_output_table(": "Use load_standard_*_workflow_outputs result loaders and their bounded preview/status helpers.",
    "write_output_table(": "Use the relevant workflow result method so configured output paths stay inside package code.",
    "write_output_tables(": "Use the relevant workflow result method so configured output paths stay inside package code.",
    "preview_output_table(": "Use standard workflow result preview/status helpers.",
    "read_config_table(": "Use task-level package loaders or standard workflow result objects.",
    "output_group_namespace": "Use standard workflow result loaders instead of exposing output groups in notebook cells.",
    "output_group_status_frame": "Use standard workflow result status_frame methods.",
    "step_outputs[": "Use standard workflow result attributes instead of dictionary-style path plumbing.",
    "dashboard_paths[": "Use dashboard workflow/status helpers instead of notebook-local dashboard path dictionaries.",
    ".bind(globals())": "Keep workflow outputs on result objects; do not inject path variables into notebook globals.",
    "vars(step_outputs)": "Use result-object status_frame methods instead of expanding path dictionaries.",
    "runs/outputs": "Resolve output paths through the active config and workflow helpers.",
    "runs/spatial_vtk_config.yaml": "Load configs through the shared source-checkout bootstrap and notebook_run_context.",
    "pd.read_": "Use package table/workflow loaders so CSV or Parquet handling and bounded reads stay centralized.",
    ".to_csv(": "Use package workflow/table writers so output formats and atomic writes stay centralized.",
    ".to_parquet(": "Use package workflow/table writers so output formats and atomic writes stay centralized.",
    ".loc[": "Move reusable filtering into package helpers when it is part of the tutorial workflow.",
    ".query(": "Move reusable filtering into package helpers when it is part of the tutorial workflow.",
    ".isin(": "Move reusable set-membership filtering into package helpers when it is part of the tutorial workflow.",
    ".merge(": "Move reusable joins into package helpers when they are part of the tutorial workflow.",
    ".groupby(": "Move reusable aggregations into package helpers when they are part of the tutorial workflow.",
    ".pivot": "Move reusable reshaping into package helpers when it is part of the tutorial workflow.",
    ".sort_values(": "Move reusable ordering into package helpers when it is part of the tutorial workflow.",
    ".drop_duplicates(": "Move reusable de-duplication into package helpers when it is part of the tutorial workflow.",
}
NOTEBOOK_CONTRACT_SHELL_PATTERN_REMEDIATION = (
    "Use imported package workflow helpers; notebooks should not run svtk commands through shell cells."
)
NOTEBOOK_CONTRACT_IMPORT_PATTERN_REMEDIATION = (
    "Import from the public spatial_vtk package namespace or the standard workflow result helpers."
)
NOTEBOOK_CONTRACT_FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "widgets",
        "widget_state",
        "varInspector",
        "toc",
    }
)
NOTEBOOK_CONTRACT_FORBIDDEN_CELL_METADATA_KEYS = frozenset(
    {
        "execution",
        "ExecuteTime",
        "widgets",
        "widget_state",
    }
)
NOTEBOOK_CONTRACT_FORBIDDEN_LINE_PATTERNS = (
    re.compile(r"^\s*![^\n]*\bsvtk\b", re.MULTILINE),
    re.compile(r"^\s*%%bash\b", re.MULTILINE),
    re.compile(r"\[\s*['\"]svtk['\"]\s*,"),
)
NOTEBOOK_CONTRACT_FORBIDDEN_IMPORT_PATTERNS = (
    re.compile(r"^\s*from\s+spatial_vtk\.io\.(metadata|preprocessing|tables)\b", re.MULTILINE),
    re.compile(r"^\s*import\s+spatial_vtk\.io\.(metadata|preprocessing|tables)\b", re.MULTILINE),
    re.compile(r"^\s*from\s+spatial_vtk\.config\.(metrics|notebook|outputs|paths|runtime)\b", re.MULTILINE),
    re.compile(r"^\s*import\s+spatial_vtk\.config\.(metrics|notebook|outputs|paths|runtime)\b", re.MULTILINE),
    re.compile(r"^\s*from\s+spatial_vtk\.qc\.build\b", re.MULTILINE),
    re.compile(r"^\s*import\s+spatial_vtk\.qc\.build\.", re.MULTILINE),
    re.compile(r"^\s*from\s+spatial_vtk\.metrics\.workflow\.(execution|outputs|run|tasks)\b", re.MULTILINE),
    re.compile(r"^\s*import\s+spatial_vtk\.metrics\.workflow\.(execution|outputs|run|tasks)\b", re.MULTILINE),
    re.compile(r"^\s*from\s+spatial_vtk\.spatial\.(calculate|map\.|plot\.)", re.MULTILINE),
    re.compile(r"^\s*import\s+spatial_vtk\.spatial\.(calculate|map\.|plot\.)", re.MULTILINE),
    re.compile(r"^\s*from\s+spatial_vtk\.visualize\.(context\.|dashboard\.|qc\.|waveforms\.)", re.MULTILINE),
    re.compile(r"^\s*import\s+spatial_vtk\.visualize\.(context\.|dashboard\.|qc\.|waveforms\.)", re.MULTILINE),
    re.compile(r"^\s*from\s+spatial_vtk\.metrics\.plot\.[\w.]+\s+import\b", re.MULTILINE),
    re.compile(r"^\s*import\s+spatial_vtk\.metrics\.plot\.[\w.]+(?:\s+as\s+\w+)?", re.MULTILINE),
    re.compile(r"^\s*from\s+spatial_vtk\.spatial\.map\.[\w.]+\s+import\b", re.MULTILINE),
    re.compile(r"^\s*import\s+spatial_vtk\.spatial\.map\.[\w.]+(?:\s+as\s+\w+)?", re.MULTILINE),
    re.compile(r"^\s*from\s+spatial_vtk\.spatial\.plot\.[\w.]+\s+import\b", re.MULTILINE),
    re.compile(r"^\s*import\s+spatial_vtk\.spatial\.plot\.[\w.]+(?:\s+as\s+\w+)?", re.MULTILINE),
)


def _python_bound_tuple(version_text: str) -> tuple[int, int]:
    """Return ``(major, minor)`` from a Python version constraint fragment."""

    parts = version_text.strip().split(".")
    return (int(parts[0]), int(parts[1]))


def _requires_python_from_pyproject(repo_root: Path | None = None) -> str:
    """Return the package ``requires-python`` value when available."""

    root = Path.cwd() if repo_root is None else repo_root
    candidates = [root / "pyproject.toml", Path(__file__).resolve().parents[1] / "pyproject.toml"]
    for path in candidates:
        if not path.exists():
            continue
        match = re.search(r'^\s*requires-python\s*=\s*"([^"]+)"', path.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            return match.group(1)
    return FALLBACK_SUPPORTED_TUTORIAL_PYTHON_RANGE


def _python_range_from_requires_python(requires_python: str) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return inclusive lower and exclusive upper bounds from ``requires-python``."""

    lower_match = re.search(r">=\s*([0-9]+(?:\.[0-9]+)+)", requires_python)
    upper_match = re.search(r"<\s*([0-9]+(?:\.[0-9]+)+)", requires_python)
    if lower_match is None or upper_match is None:
        requires_python = FALLBACK_SUPPORTED_TUTORIAL_PYTHON_RANGE
        lower_match = re.search(r">=\s*([0-9]+(?:\.[0-9]+)+)", requires_python)
        upper_match = re.search(r"<\s*([0-9]+(?:\.[0-9]+)+)", requires_python)
    assert lower_match is not None and upper_match is not None
    return _python_bound_tuple(lower_match.group(1)), _python_bound_tuple(upper_match.group(1))


def _tutorial_python_contract_from_validation_checker() -> tuple[str, tuple[int, int], tuple[int, int]] | None:
    """Return supported Python bounds from the validation checker contract."""

    module = _validation_checker_module()
    if module is None:
        return None
    try:
        requires_python = str(module.REQUIRES_PYTHON)
        return requires_python, tuple(module.MIN_PYTHON), tuple(module.MAX_PYTHON)
    except Exception:
        return None


_TUTORIAL_PYTHON_CONTRACT = _tutorial_python_contract_from_validation_checker()
if _TUTORIAL_PYTHON_CONTRACT is None:
    SUPPORTED_TUTORIAL_PYTHON_RANGE = _requires_python_from_pyproject()
    MIN_TUTORIAL_PYTHON, MAX_TUTORIAL_PYTHON = _python_range_from_requires_python(SUPPORTED_TUTORIAL_PYTHON_RANGE)
else:
    SUPPORTED_TUTORIAL_PYTHON_RANGE, MIN_TUTORIAL_PYTHON, MAX_TUTORIAL_PYTHON = _TUTORIAL_PYTHON_CONTRACT
NOTEBOOK_CONTRACT_PRIVATE_PATH_PATTERNS = (
    re.compile(r"(?<![\w.-])/(?:Users|home|home\d*|project\d*|scratch|work|lustre)/[^\s'\"),\]]+"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
)


def main(argv: list[str] | None = None) -> int:
    """Run the command-line notebook executor."""

    args = _parse_args(argv)
    repo_root = _find_repo_root(Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve())
    notebooks = _resolve_notebooks(
        repo_root,
        args.notebooks,
        include_large_run=args.include_large_run,
        large_run_only=args.large_run_only,
    )
    report_path = (repo_root / args.report).resolve() if not Path(args.report).is_absolute() else Path(args.report)
    tutorial_output = repo_root / args.tutorial_output

    configure_notebook_runtime_environment(tutorial_output)
    if not args.skip_notebook_contract_check:
        check_tutorial_notebook_contracts(notebooks, repo_root=repo_root)
    if not args.skip_example_data_check:
        check_tutorial_example_data(repo_root)
    if args.preflight_only:
        print(f"Notebook preflight clean for {len(notebooks)} notebook(s).")
        return 0
    configure_source_checkout_imports(repo_root)
    check_notebook_runtime()
    if args.runtime_check_only:
        print(f"Notebook runtime dependencies available for {len(notebooks)} notebook(s).")
        return 0
    if args.clean:
        _clean_path(tutorial_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report: list[dict[str, Any]] = []
    for notebook in notebooks:
        result = execute_notebook(notebook, repo_root=repo_root, timeout=args.timeout)
        report.append(result)
        print(
            f"{result['status'].upper()} {notebook.relative_to(repo_root)} "
            f"elapsed={result['elapsed_s']:.1f}s warnings={len(result['warnings'])} "
            f"errors={len(result['errors'])}",
            flush=True,
        )
        if result["status"] != "passed" and args.stop_on_failure:
            break

    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    failures = [item for item in report if item["errors"] or item["status"] != "passed"]
    warning_items = [item for item in report if item["warnings"]]
    if failures:
        print(f"Notebook execution failed; report: {report_path}", file=sys.stderr)
        return 1
    if warning_items and not args.allow_warnings:
        print(f"Notebook warnings detected; report: {report_path}", file=sys.stderr)
        return 2
    print(f"Notebook execution clean; report: {report_path}")
    return 0


def execute_notebook(notebook_path: Path, *, repo_root: Path, timeout: int) -> dict[str, Any]:
    """Execute one notebook and return a report dictionary."""

    import nbformat
    from nbclient import NotebookClient

    start = time.time()
    result: dict[str, Any] = {
        "path": str(notebook_path.relative_to(repo_root)),
        "elapsed_s": 0.0,
        "status": "passed",
        "warnings": [],
        "errors": [],
    }
    try:
        notebook = nbformat.read(notebook_path, as_version=4)
        client = NotebookClient(
            notebook,
            timeout=timeout,
            kernel_name="python3",
            resources={"metadata": {"path": str(repo_root)}},
            extra_arguments=list(KERNEL_EXTRA_ARGUMENTS),
            allow_errors=False,
            force_raise_errors=True,
        )
        client.execute()
        result["warnings"] = scan_notebook_outputs(notebook)
        result["errors"] = _notebook_errors(notebook)
    except Exception as exc:
        result["status"] = "failed"
        result["errors"].append({"cell": None, "ename": type(exc).__name__, "evalue": str(exc)})
    result["elapsed_s"] = round(time.time() - start, 1)
    if result["errors"]:
        result["status"] = "failed"
    return result


def check_notebook_runtime(required: dict[str, str] | None = None) -> None:
    """Exit with an actionable message when notebook execution dependencies are missing."""

    check_tutorial_python_version()
    missing = missing_notebook_runtime_modules(required)
    if not missing:
        return
    missing_text = ", ".join(missing)
    raise SystemExit(
        "Missing tutorial runtime modules: "
        f"{missing_text}. These modules are required before executing the "
        "tutorial notebooks, including Jupyter, mapping, dashboard, and "
        f"waveform readers. Current Python executable: {sys.executable}. "
        "Make sure the install command targets this environment, or activate "
        "the intended environment first. From a source checkout, first run "
        f"{SOURCE_CHECKOUT_TUTORIAL_VALIDATION_COMMAND} to get the same "
        "lightweight environment check used by the public docs. Install the "
        "package runtime plus tutorial extras with "
        f"{SOURCE_CHECKOUT_TUTORIAL_INSTALL_COMMAND}. For this exact Python "
        f"environment, run {current_python_tutorial_install_command()}. "
        f"After installing, rerun {SOURCE_CHECKOUT_TUTORIAL_RUNTIME_CHECK_COMMAND}. "
        f"For this exact Python environment, rerun {current_python_tutorial_runtime_check_command()}. "
        "If compiled mapping or waveform dependencies are difficult to solve "
        f"with pip, create the full conda environment with {SOURCE_CHECKOUT_TUTORIAL_CONDA_COMMAND}."
    )


def check_tutorial_python_version(version_info: Any | None = None) -> None:
    """Exit with a clear message when the tutorial runner uses unsupported Python."""

    info = sys.version_info if version_info is None else version_info
    if tutorial_python_version_supported(info):
        return
    raise SystemExit(
        "Spatial-VTK tutorial notebooks require Python "
        f"{SUPPORTED_TUTORIAL_PYTHON_RANGE}. Current Python executable: {sys.executable}. "
        f"Current Python version: {python_version_label(info)}. Activate a supported "
        "environment before installing tutorial dependencies. From a source checkout, "
        "create the full conda environment with "
        f"{SOURCE_CHECKOUT_TUTORIAL_CONDA_COMMAND}, or activate a supported Python "
        f"environment and run {SOURCE_CHECKOUT_TUTORIAL_INSTALL_COMMAND}."
    )


def tutorial_python_version_supported(version_info: Any | None = None) -> bool:
    """Return whether ``version_info`` satisfies the package tutorial Python range."""

    info = sys.version_info if version_info is None else version_info
    version = (int(info[0]), int(info[1]))
    return MIN_TUTORIAL_PYTHON <= version < MAX_TUTORIAL_PYTHON


def python_version_label(version_info: Any | None = None) -> str:
    """Return a compact Python version label for runtime-check messages."""

    info = sys.version_info if version_info is None else version_info
    parts = [int(info[0]), int(info[1])]
    if len(info) > 2:
        parts.append(int(info[2]))
    return ".".join(str(part) for part in parts)


def configure_source_checkout_imports(repo_root: Path) -> None:
    """Make the source tree importable for runtime checks run from a checkout."""

    src_path = repo_root / "src"
    if not src_path.exists():
        return
    src_text = str(src_path)
    if src_text not in sys.path:
        sys.path.insert(0, src_text)


def configure_notebook_runtime_environment(tutorial_output: Path) -> None:
    """Keep notebook runtime files under the ignored tutorial output tree."""

    os.environ.setdefault("JUPYTER_PLATFORM_DIRS", "1")
    os.environ.setdefault("MPLCONFIGDIR", str(tutorial_output / ".mplconfig"))
    os.environ.setdefault("IPYTHONDIR", str(tutorial_output / ".ipython"))
    os.environ.setdefault("JUPYTER_CONFIG_DIR", str(tutorial_output / ".jupyter_config"))
    os.environ.setdefault("JUPYTER_DATA_DIR", str(tutorial_output / ".jupyter_data"))
    os.environ.setdefault("JUPYTER_RUNTIME_DIR", str(tutorial_output / ".jupyter_runtime"))


def missing_notebook_runtime_modules(required: dict[str, str] | None = None) -> list[str]:
    """Return notebook-runtime dependency labels whose import modules are unavailable."""

    modules = NOTEBOOK_RUNTIME_MODULES if required is None else required
    return [label for label, module in modules.items() if importlib.util.find_spec(module) is None]


def current_python_tutorial_install_command() -> str:
    """Return the tutorial install command for the currently running Python."""

    executable = shlex.quote(sys.executable)
    return f'{executable} -m pip install -e ".[validation,docs,dashboard,notebooks,waveforms]"'


def current_python_tutorial_runtime_check_command() -> str:
    """Return the tutorial runtime-check command for the currently running Python."""

    executable = shlex.quote(sys.executable)
    return (
        "MPLCONFIGDIR=/tmp/mplconfig_svtk "
        f"{executable} tools/execute_tutorial_notebooks.py --runtime-check-only --include-large-run"
    )


def check_tutorial_example_data(repo_root: Path) -> None:
    """Exit with a clear message when committed tutorial example data is incomplete."""

    missing = missing_tutorial_example_data(repo_root)
    if not missing:
        return
    preview = ", ".join(missing[:20])
    suffix = f", ... {len(missing) - 20} more" if len(missing) > 20 else ""
    raise SystemExit(
        "Tutorial example data is incomplete. The standard notebooks expect "
        f"the committed five-event NPZ subset. Missing {len(missing)} file(s): {preview}{suffix}"
    )


def missing_tutorial_example_data(repo_root: Path) -> list[str]:
    """Return required tutorial data files that are missing from a checkout."""

    missing: list[str] = []
    for relative_path in TUTORIAL_REQUIRED_FILES:
        if not (repo_root / relative_path).exists():
            missing.append(str(relative_path))

    records_path = repo_root / TUTORIAL_EXAMPLE_ROOT / "metadata" / "selected_event_stations.csv"
    if not records_path.exists():
        return missing

    with records_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or ())
        missing_columns = sorted({"event_id", "station"} - fieldnames)
        if missing_columns:
            missing.append(
                f"{records_path.relative_to(repo_root)} (missing columns: {', '.join(missing_columns)})"
            )
            return missing
        records = list(reader)
    if not records:
        missing.append(str(records_path.relative_to(repo_root)) + " (empty)")
        return missing

    for row_number, row in enumerate(records, start=2):
        event_id = str(row.get("event_id", "")).strip()
        station = str(row.get("station", "")).strip()
        model = str(row.get("synthetic_model", "")).strip() or TUTORIAL_SYNTHETIC_MODEL
        missing_values = [name for name, value in (("event_id", event_id), ("station", station)) if not value]
        if missing_values:
            missing.append(
                f"{records_path.relative_to(repo_root)} (row {row_number} missing values: {', '.join(missing_values)})"
            )
            continue
        observed = TUTORIAL_EXAMPLE_ROOT / "waveforms_npz" / "observed" / event_id / f"{station}.npz"
        synthetic = TUTORIAL_EXAMPLE_ROOT / "waveforms_npz" / "synthetics" / model / event_id / f"{station}.npz"
        if not (repo_root / observed).exists():
            missing.append(str(observed))
        if not (repo_root / synthetic).exists():
            missing.append(str(synthetic))
    return missing


def check_tutorial_notebook_contracts(notebooks: list[Path], *, repo_root: Path) -> None:
    """Exit when tutorial notebooks violate the public source-checkout contract."""

    violations = tutorial_notebook_contract_violations(notebooks, repo_root=repo_root)
    if not violations:
        return
    preview = "\n".join(f"- {item}" for item in violations[:20])
    suffix = f"\n- ... {len(violations) - 20} more" if len(violations) > 20 else ""
    raise SystemExit(
        "Tutorial notebook source contract failed. Notebooks should run from a "
        "fresh public checkout, use importable spatial_vtk package APIs instead "
        "of shell/CLI workflow cells, and avoid raw output-path/table/dataframe plumbing.\n"
        f"{preview}{suffix}"
    )


def tutorial_notebook_contract_violations(notebooks: list[Path], *, repo_root: Path) -> list[str]:
    """Return source-level tutorial notebook contract violations."""

    violations: list[str] = []
    for notebook_path in notebooks:
        label = _notebook_label(notebook_path, repo_root)
        try:
            notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        except Exception as exc:
            violations.append(f"{label}: could not read notebook JSON: {type(exc).__name__}: {exc}")
            continue

        cells = notebook.get("cells", [])
        source_text = "\n".join("".join(cell.get("source", [])) for cell in cells)
        metadata = notebook.get("metadata", {})
        if isinstance(metadata, dict):
            saved_state_keys = sorted(NOTEBOOK_CONTRACT_FORBIDDEN_METADATA_KEYS & set(metadata))
            if saved_state_keys:
                violations.append(
                    f"{label}: committed notebook metadata should not contain saved runtime state keys: "
                    f"{', '.join(saved_state_keys)}"
                )
        if _is_example_notebook(notebook_path, repo_root) and "docs/examples/large_run/" not in label:
            if "_source_bootstrap.py" not in source_text or "runpy.run_path(str(_bootstrap))" not in source_text:
                violations.append(f"{label}: missing shared source-checkout bootstrap cell")

        cell_ids = [str(cell.get("id", "")).strip() for cell in cells]
        duplicated_ids = sorted({cell_id for cell_id in cell_ids if cell_id and cell_ids.count(cell_id) > 1})
        if duplicated_ids:
            violations.append(f"{label}: duplicate cell ids: {', '.join(duplicated_ids[:10])}")

        for index, cell in enumerate(cells, start=1):
            cell_label = f"{label} cell {index}"
            source = "".join(cell.get("source", []))
            cell_metadata = cell.get("metadata", {})
            if isinstance(cell_metadata, dict):
                saved_cell_state_keys = sorted(NOTEBOOK_CONTRACT_FORBIDDEN_CELL_METADATA_KEYS & set(cell_metadata))
                if saved_cell_state_keys:
                    violations.append(
                        f"{cell_label}: committed cell metadata should not contain saved runtime state keys: "
                        f"{', '.join(saved_cell_state_keys)}"
                    )
            if cell.get("cell_type") == "markdown":
                violations.extend(_notebook_markdown_section_violations(source, cell_label))
                violations.extend(_notebook_markdown_flow_violations(cells, index - 1, cell_label))
            if not str(cell.get("id", "")).strip():
                violations.append(f"{cell_label}: missing cell id")
            if cell.get("cell_type") == "code":
                if cell.get("execution_count") is not None:
                    violations.append(f"{cell_label}: committed execution_count should be empty")
                if cell.get("outputs"):
                    violations.append(f"{cell_label}: committed outputs should be empty")
            for token in NOTEBOOK_CONTRACT_FORBIDDEN_SNIPPETS:
                if token in source:
                    violations.append(_notebook_forbidden_snippet_message(cell_label, token))
            for pattern in NOTEBOOK_CONTRACT_FORBIDDEN_LINE_PATTERNS:
                if pattern.search(source):
                    violations.append(
                        f"{cell_label}: forbidden shell/CLI workflow pattern {pattern.pattern!r}. "
                        f"{NOTEBOOK_CONTRACT_SHELL_PATTERN_REMEDIATION}"
                    )
            for pattern in NOTEBOOK_CONTRACT_FORBIDDEN_IMPORT_PATTERNS:
                if pattern.search(source):
                    violations.append(
                        f"{cell_label}: forbidden implementation import pattern {pattern.pattern!r}. "
                        f"{NOTEBOOK_CONTRACT_IMPORT_PATTERN_REMEDIATION}"
                    )
            for pattern in NOTEBOOK_CONTRACT_PRIVATE_PATH_PATTERNS:
                match = pattern.search(source)
                if match:
                    violations.append(f"{cell_label}: user-specific path or address {match.group(0)!r}")
            if cell.get("cell_type") == "code":
                violations.extend(_notebook_local_definition_violations(source, cell_label))
                violations.extend(_notebook_parent_path_violations(source, cell_label))
                violations.extend(_notebook_package_callable_violations(source, cell_label))
    return violations


def _notebook_forbidden_snippet_message(cell_label: str, token: str) -> str:
    """Return an actionable source-contract diagnostic for a forbidden token."""

    remediation = NOTEBOOK_CONTRACT_SNIPPET_REMEDIATIONS.get(token)
    message = f"{cell_label}: forbidden source snippet {token!r}"
    if remediation:
        message = f"{message}. {remediation}"
    return message


def _notebook_markdown_section_violations(source: str, cell_label: str) -> list[str]:
    """Return tutorial section headings that do not document task intent."""

    if "docs/examples/large_run/" in cell_label:
        return []
    first_line = next((line.strip() for line in source.splitlines() if line.strip()), "")
    if not _is_task_markdown_heading(first_line):
        return []
    if "Purpose:" in source and "Outputs:" in source:
        return []
    return [f"{cell_label}: markdown section should include Purpose: and Outputs:"]


def _notebook_markdown_flow_violations(cells: list[dict[str, object]], index: int, cell_label: str) -> list[str]:
    """Return markdown task sections that look disconnected from executable work."""

    source = "".join(cells[index].get("source", []))
    first_line = next((line.strip() for line in source.splitlines() if line.strip()), "")
    if not _is_task_markdown_heading(first_line):
        return []
    if "Purpose:" not in source or "Outputs:" not in source:
        return []
    for next_cell in cells[index + 1 :]:
        next_source = "".join(next_cell.get("source", []))
        if not next_source.strip():
            continue
        if next_cell.get("cell_type") == "markdown":
            next_first_line = next((line.strip() for line in next_source.splitlines() if line.strip()), "")
            return [
                f"{cell_label}: markdown section with Purpose:/Outputs: is followed by another "
                f"markdown section {next_first_line!r}; combine the text with the package helper "
                "section or add the missing package-helper code cell."
            ]
        return []
    return []


def _is_task_markdown_heading(first_line: str) -> bool:
    """Return whether ``first_line`` is a notebook task-section heading."""

    return first_line.startswith("##")


def _notebook_local_definition_violations(source: str, cell_label: str) -> list[str]:
    """Return notebook-local function/class definitions that should live in the package."""

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    violations: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            violations.append(
                f"{cell_label}: notebook-local function {node.name!r} should move to an importable package helper"
            )
        elif isinstance(node, ast.ClassDef):
            violations.append(
                f"{cell_label}: notebook-local class {node.name!r} should move to an importable package helper"
            )
    return violations


def _notebook_package_callable_violations(source: str, cell_label: str) -> list[str]:
    """Return notebook calls that use compatibility import-path strings."""

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _ast_call_name(node.func)
        if call_name not in {"run_notebook_step_if_needed", "run_or_submit_notebook_function"}:
            continue
        function_node: ast.AST | None = node.args[2] if len(node.args) >= 3 else None
        for keyword in node.keywords:
            if keyword.arg == "function":
                function_node = keyword.value
                break
        if isinstance(function_node, ast.Constant) and isinstance(function_node.value, str):
            violations.append(
                f"{cell_label}: {call_name} should receive an imported package callable, "
                f"not compatibility import path {function_node.value!r}"
            )
    return violations


def _notebook_parent_path_violations(source: str, cell_label: str) -> list[str]:
    """Return brittle ``Path("..")`` style source-checkout bootstrap paths."""

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _ast_call_name(node.func) != "Path" or not node.args:
            continue
        first_arg = node.args[0]
        if not (isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str)):
            continue
        path_text = first_arg.value.strip()
        if path_text == ".." or path_text.startswith("../") or path_text.startswith("..\\"):
            violations.append(
                f"{cell_label}: parent-directory Path({path_text!r}) bootstrap should use "
                "the shared _source_bootstrap.py helper"
            )
    return violations


def _ast_call_name(node: ast.AST) -> str | None:
    """Return the terminal name for a call expression."""

    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def scan_notebook_outputs(notebook: Any) -> list[dict[str, Any]]:
    """Return cell outputs that look like warnings or tracebacks."""

    warnings: list[dict[str, Any]] = []
    for index, cell in enumerate(notebook.cells):
        for output in cell.get("outputs", []):
            text = _output_text(output)
            if WARNING_PATTERN.search(text):
                warnings.append({"cell": index, "text": text[:800]})
    return warnings


def _notebook_errors(notebook: Any) -> list[dict[str, Any]]:
    """Return explicit notebook error outputs."""

    errors: list[dict[str, Any]] = []
    for index, cell in enumerate(notebook.cells):
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                errors.append(
                    {
                        "cell": index,
                        "ename": output.get("ename"),
                        "evalue": output.get("evalue"),
                    }
                )
    return errors


def _output_text(output: Any) -> str:
    """Return text content from one notebook output."""

    if output.get("output_type") == "stream":
        text = output.get("text", "")
    else:
        data = output.get("data", {})
        text = data.get("text/plain", "") if isinstance(data, dict) else ""
    if isinstance(text, list):
        return "".join(str(part) for part in text)
    return str(text)


def _notebook_label(notebook_path: Path, repo_root: Path) -> str:
    """Return a readable notebook path for diagnostics."""

    try:
        return str(notebook_path.relative_to(repo_root))
    except ValueError:
        return str(notebook_path)


def _is_example_notebook(notebook_path: Path, repo_root: Path) -> bool:
    """Return True when a notebook lives under the public examples tree."""

    try:
        notebook_path.relative_to(repo_root / "docs" / "examples")
    except ValueError:
        return False
    return True


def _find_repo_root(start: Path) -> Path:
    """Return the repository root at or above ``start``."""

    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "docs/examples").exists():
            return candidate
    raise SystemExit(f"Could not find the spatial-vtk repository root from {start}.")


def _resolve_notebooks(
    repo_root: Path,
    notebooks: list[str] | None,
    *,
    include_large_run: bool = False,
    large_run_only: bool = False,
) -> list[Path]:
    """Resolve requested notebook paths relative to the repository root."""

    if notebooks:
        names = list(notebooks)
    elif large_run_only:
        names = list(LARGE_RUN_TUTORIAL_NOTEBOOKS)
    else:
        names = list(STANDARD_TUTORIAL_NOTEBOOKS)
        if include_large_run:
            names.extend(LARGE_RUN_TUTORIAL_NOTEBOOKS)
    paths = [(repo_root / name).resolve() if not Path(name).is_absolute() else Path(name) for name in names]
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise SystemExit("Missing notebook(s): " + ", ".join(str(path) for path in missing))
    return paths


def _clean_path(path: Path) -> None:
    """Remove one ignored output directory before execution."""

    resolved = path.resolve()
    if resolved.name != "tutorials" or resolved.parent.name != "outputs":
        raise SystemExit(f"Refusing to clean unexpected tutorial output path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    print(f"reset {resolved}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", help="Repository root. Defaults to the current directory or a parent.")
    parser.add_argument(
        "--notebook",
        dest="notebooks",
        action="append",
        help=(
            "Notebook path to execute. Repeat to run a subset. Defaults to all "
            "standard tutorial notebooks unless --include-large-run or "
            "--large-run-only is passed."
        ),
    )
    parser.add_argument(
        "--include-large-run",
        action="store_true",
        help=(
            "After the standard tutorial notebooks, also execute the "
            "docs/examples/large_run notebooks against the committed example "
            "data and outputs."
        ),
    )
    parser.add_argument(
        "--large-run-only",
        action="store_true",
        help="Execute only the docs/examples/large_run notebooks.",
    )
    parser.add_argument("--timeout", type=int, default=900, help="Per-notebook timeout in seconds.")
    parser.add_argument(
        "--report",
        default="outputs/tutorials/notebook_execution_report.json",
        help="JSON report path. Relative paths are resolved from the repository root.",
    )
    parser.add_argument(
        "--tutorial-output",
        default="outputs/tutorials",
        help="Tutorial output directory to clean when --clean is set.",
    )
    parser.add_argument("--clean", action="store_true", help="Delete outputs/tutorials before running.")
    parser.add_argument("--allow-warnings", action="store_true", help="Do not fail when warning-like cell output is captured.")
    parser.add_argument("--no-stop-on-failure", dest="stop_on_failure", action="store_false", help="Continue after a notebook failure.")
    parser.add_argument(
        "--skip-example-data-check",
        action="store_true",
        help="Skip the committed tutorial example-data preflight for custom notebook subsets.",
    )
    parser.add_argument(
        "--skip-notebook-contract-check",
        action="store_true",
        help=(
            "Skip source-level tutorial notebook contract checks for custom "
            "notebook subsets. The default protects public tutorials from "
            "private paths, saved outputs, and shell/CLI workflow cells."
        ),
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help=(
            "Run notebook source-contract and example-data preflights, then "
            "exit before checking notebook runtime dependencies, cleaning "
            "outputs, or executing notebooks."
        ),
    )
    parser.add_argument(
        "--runtime-check-only",
        action="store_true",
        help=(
            "Run source-contract, example-data, and notebook-runtime dependency "
            "checks, then exit before cleaning outputs or executing notebooks."
        ),
    )
    parser.set_defaults(stop_on_failure=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
