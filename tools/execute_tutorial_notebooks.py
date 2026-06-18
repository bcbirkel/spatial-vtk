#!/usr/bin/env python3
"""Execute the standard tutorial notebooks from a source checkout.

This is a lightweight release/source-check helper. It runs the committed
standard tutorial notebooks against the committed example data, optionally
clears the tutorial output directory first, and writes a JSON execution report.
The script does not save executed notebooks back to the repository.
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
    "docs/examples/large_run/step_07_large_run_dashboards.ipynb",
)

WARNING_PATTERN = re.compile(
    r"traceback \(most recent call last\)|"
    r"\b(?:runtime|user|future|deprecation|pendingdeprecation|syntax|resource|import|unicode|bytes|encoding|numpy|pandas|matplotlib)?warning\s*:|"
    r"\bwarning\s+\[[^\]]+\]|"
    r"\bWARNING\s*:",
    re.IGNORECASE,
)
NOTEBOOK_RUNTIME_MODULES = {
    "nbformat": "nbformat",
    "nbclient": "nbclient",
    "ipykernel": "ipykernel",
    "IPython": "IPython",
}
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
    "run_or_submit_notebook_cli_command(",
    "write_notebook_cli_slurm_script(",
    "from spatial_vtk.metrics.plot.",
    "from spatial_vtk.spatial.map.",
    "from spatial_vtk.spatial.plot.",
    "resolve_output_path(",
    "load_output_table(",
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
    ".loc[",
    ".merge(",
)
NOTEBOOK_CONTRACT_FORBIDDEN_LINE_PATTERNS = (
    re.compile(r"^\s*![^\n]*\bsvtk\b", re.MULTILINE),
    re.compile(r"^\s*%%bash\b", re.MULTILINE),
    re.compile(r"\[\s*['\"]svtk['\"]\s*,"),
)
NOTEBOOK_CONTRACT_FORBIDDEN_IMPORT_PATTERNS = (
    re.compile(r"^\s*from\s+spatial_vtk\.metrics\.plot\.[\w.]+\s+import\b", re.MULTILINE),
    re.compile(r"^\s*import\s+spatial_vtk\.metrics\.plot\.[\w.]+(?:\s+as\s+\w+)?", re.MULTILINE),
    re.compile(r"^\s*from\s+spatial_vtk\.spatial\.map\.[\w.]+\s+import\b", re.MULTILINE),
    re.compile(r"^\s*import\s+spatial_vtk\.spatial\.map\.[\w.]+(?:\s+as\s+\w+)?", re.MULTILINE),
    re.compile(r"^\s*from\s+spatial_vtk\.spatial\.plot\.[\w.]+\s+import\b", re.MULTILINE),
    re.compile(r"^\s*import\s+spatial_vtk\.spatial\.plot\.[\w.]+(?:\s+as\s+\w+)?", re.MULTILINE),
)
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

    missing = missing_notebook_runtime_modules(required)
    if not missing:
        return
    missing_text = ", ".join(missing)
    raise SystemExit(
        "Notebook execution requires the notebook runtime modules: "
        f"{missing_text}. Install the tutorial extras with "
        'python -m pip install -e ".[notebooks,waveforms]".'
    )


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
        records = list(csv.DictReader(handle))
    if not records:
        missing.append(str(records_path.relative_to(repo_root)) + " (empty)")
        return missing

    for row in records:
        event_id = str(row.get("event_id", "")).strip()
        station = str(row.get("station", "")).strip()
        model = str(row.get("synthetic_model", "")).strip() or TUTORIAL_SYNTHETIC_MODEL
        if not event_id or not station:
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
        if _is_example_notebook(notebook_path, repo_root):
            if "_source_bootstrap.py" not in source_text or "runpy.run_path(str(_bootstrap))" not in source_text:
                violations.append(f"{label}: missing shared source-checkout bootstrap cell")

        cell_ids = [str(cell.get("id", "")).strip() for cell in cells]
        duplicated_ids = sorted({cell_id for cell_id in cell_ids if cell_id and cell_ids.count(cell_id) > 1})
        if duplicated_ids:
            violations.append(f"{label}: duplicate cell ids: {', '.join(duplicated_ids[:10])}")

        for index, cell in enumerate(cells, start=1):
            cell_label = f"{label} cell {index}"
            source = "".join(cell.get("source", []))
            if not str(cell.get("id", "")).strip():
                violations.append(f"{cell_label}: missing cell id")
            if cell.get("cell_type") == "code":
                if cell.get("execution_count") is not None:
                    violations.append(f"{cell_label}: committed execution_count should be empty")
                if cell.get("outputs"):
                    violations.append(f"{cell_label}: committed outputs should be empty")
            for token in NOTEBOOK_CONTRACT_FORBIDDEN_SNIPPETS:
                if token in source:
                    violations.append(f"{cell_label}: forbidden source snippet {token!r}")
            for pattern in NOTEBOOK_CONTRACT_FORBIDDEN_LINE_PATTERNS:
                if pattern.search(source):
                    violations.append(f"{cell_label}: forbidden shell/CLI workflow pattern {pattern.pattern!r}")
            for pattern in NOTEBOOK_CONTRACT_FORBIDDEN_IMPORT_PATTERNS:
                if pattern.search(source):
                    violations.append(f"{cell_label}: forbidden implementation import pattern {pattern.pattern!r}")
            for pattern in NOTEBOOK_CONTRACT_PRIVATE_PATH_PATTERNS:
                match = pattern.search(source)
                if match:
                    violations.append(f"{cell_label}: user-specific path or address {match.group(0)!r}")
            if cell.get("cell_type") == "code":
                violations.extend(_notebook_package_callable_violations(source, cell_label))
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
