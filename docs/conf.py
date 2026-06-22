"""Sphinx configuration for the Spatial-VTK public documentation."""

from __future__ import annotations

import inspect
from pathlib import Path
import sys
from typing import Any, get_type_hints
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

project = "Spatial-VTK"
author = "Brianna Birkel"
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon"]
templates_path = ["_templates"]
exclude_patterns = ["_build", ".ipynb_checkpoints"]
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_css_files = ["custom.css"]


_PACKAGE_LABELS = {
    "spatial_vtk.config": "Configuration Package",
    "spatial_vtk.io": "Input and Output Package",
    "spatial_vtk.metrics": "Metrics Package",
    "spatial_vtk.qc": "Quality Control Package",
    "spatial_vtk.spatial": "Spatial Analysis Package",
    "spatial_vtk.visualize": "Visualization Package",
}

_MODULE_LABELS = {
    "spatial_vtk.io.output_paths": "Output Paths",
    "spatial_vtk.metrics.calculate": "Metric Calculations",
    "spatial_vtk.spatial.calculate": "Spatial Calculations",
    "spatial_vtk.spatial.map": "Spatial Maps",
    "spatial_vtk.spatial.plot": "Spatial Plots",
    "spatial_vtk.visualize.figure_io": "Figure I/O",
    "spatial_vtk.visualize.qc": "QC Visualization",
}

_SECTION_PREFIXES = {
    "calculate": "Calculation",
    "config": "Configuration",
    "context": "Context",
    "dashboard": "Dashboard",
    "map": "Mapping",
    "plot": "Plotting",
    "qc": "Quality Control",
    "review": "Review",
    "summary": "Summary",
    "waveforms": "Waveform",
    "workflow": "Workflow",
}

_ACRONYMS = {
    "api": "API",
    "asdf": "ASDF",
    "fas": "FAS",
    "geojson": "GeoJSON",
    "gof": "GOF",
    "io": "I/O",
    "json": "JSON",
    "kml": "KML",
    "pca": "PCA",
    "pgd": "PGD",
    "pga": "PGA",
    "pgv": "PGV",
    "psa": "PSA",
    "qc": "QC",
    "slurm": "SLURM",
    "vs30": "Vs30",
}

_PARAMETER_DESCRIPTIONS = {
    "add_basemap": "Whether to add a configured basemap layer to geospatial figures.",
    "cfg": "Spatial-VTK configuration object used for path and setting resolution.",
    "close": "Whether to close the figure after display or save handling.",
    "component": "Waveform component or component filter used for the calculation or figure.",
    "components": "Waveform components included in the calculation or figure.",
    "config": "Spatial-VTK configuration object or path used to resolve workflow inputs and outputs.",
    "config_path": "Path to the Spatial-VTK YAML configuration file.",
    "event_id": "Canonical event identifier used to select event-scoped records.",
    "figure_dir": "Directory where generated figures should be written; standard workflows resolve this from the active config.",
    "input": (
        "Explicit input table, figure source, or configured artifact key for this workflow step; "
        "standard notebooks usually resolve the matching named input from the active config."
    ),
    "input_path": (
        "Explicit input table/file path or configured artifact path for this workflow step; "
        "standard notebooks usually pass the config or result object instead of hard-coding this path."
    ),
    "manifest": "Metric or QC manifest that lists resumable workflow work units, batch outputs, and checkpoint state.",
    "manifest_path": "Path to the metric or QC manifest file used for resumable planning, execution, or merging.",
    "metric": "Metric name or metric filter used for the calculation or figure.",
    "metrics_dataset_dir": (
        "Metrics dashboard row dataset directory or direct ``metrics_long`` CSV or Parquet table; "
        "standard dashboard workflows resolve this from the active config."
    ),
    "metrics_root": (
        "Backward-compatible alias for ``metrics_dataset_dir``. Prefer "
        "``metrics_dataset_dir`` in new Python code, CLI docs, and notebook helpers."
    ),
    "metrics": "Metric names included in the calculation or figure.",
    "model": "Synthetic model name or model filter used for the calculation or figure.",
    "output": (
        "Explicit output table, figure, manifest, or configured artifact override written by this workflow step; "
        "omit it in standard workflows to use the registered output path from the active config."
    ),
    "output_dir": "Directory where workflow outputs should be written; standard workflows resolve this from the active config.",
    "output_path": (
        "Explicit output table, figure, manifest, or artifact path written by this workflow step; "
        "standard workflow result objects resolve registered output paths from the active config."
    ),
    "overwrite": "Whether existing outputs should be replaced.",
    "passband": "Passband label or passband filter used for the calculation or figure.",
    "path": "Filesystem path, registered artifact key, or dotted config path key accepted by this helper.",
    "qc_trace_summary_table": (
        "QC trace-summary CSV or Parquet table used by the QC dashboard; standard QC dashboard "
        "workflows resolve this from the configured ``qc_trace_summary`` output."
    ),
    "run_scenario": "Configured run scenario name used to resolve scenario-specific settings.",
    "savefig": "Whether to save the generated figure.",
    "showfig": "Whether to display the generated figure interactively.",
    "sidecar_dir": "Directory where figure sidecar CSV/JSON files should be written.",
    "sidecar_rows": "Maximum number of rows to write to each figure sidecar; use ``None`` or ``0`` for all rows.",
    "source": "Source table, path, configured artifact, or source label used by this workflow step.",
    "source_df": "Pre-aggregation rows used to produce the plotted or summarized rows.",
    "summary": "Summary table, dashboard summary dataset, or summary configuration consumed by this helper.",
    "dashboard_summary_table_dir": (
        "Dashboard summary-table directory containing ``model_metric_band``, ``station_rollup``, "
        "``event_rollup``, and ``path_hex`` tables; standard dashboard workflows resolve this from "
        "the active config."
    ),
    "summary_root": (
        "Backward-compatible alias for ``dashboard_summary_table_dir``. Prefer "
        "``dashboard_summary_table_dir`` in new Python code, CLI docs, and notebook helpers."
    ),
    "table": "Input table object, output table object, configured table key, or table selector used by this helper.",
    "trace_summary": (
        "Backward-compatible alias for ``qc_trace_summary_table``. Prefer "
        "``qc_trace_summary_table`` in new Python code, CLI docs, and notebook helpers."
    ),
    "value_col": "Column containing the value to plot, summarize, or validate.",
    "verbose": "Whether to print progress messages.",
    "write_sidecar": "Whether to write row-provenance sidecar files for the figure.",
    "write_sidecars": "Whether to write row-provenance sidecar files for generated figures.",
}

_PARAMETER_NAME_PATTERNS = (
    ("config", "Configuration value used to resolve workflow settings."),
    ("manifest", "Manifest value used to plan, resume, or merge workflow work units and batch outputs."),
    ("sidecar", "Figure sidecar setting used for row-provenance outputs."),
    (
        "output",
        "Explicit output table, figure, manifest, or configured artifact override written or resolved by this workflow step.",
    ),
    (
        "input",
        "Explicit input table, file, figure source, or configured artifact read or resolved by this workflow step.",
    ),
    ("summary", "Summary table, dashboard summary dataset, or summary setting read, written, or displayed by this workflow step."),
    ("figure", "Figure value used for plotting, sidecar writing, or figure output handling."),
    ("table", "Input/output table value, configured table key, or table selector read, written, or selected by this helper."),
    ("path", "Filesystem path, registered artifact key, or dotted config path key used by this helper."),
    ("root", "Directory root or configured output root used by this helper."),
)


def _humanize_module_part(value: str) -> str:
    """Convert one Python module name segment into a reader-facing label."""

    words = value.replace("_", " ").replace("-", " ").split()
    return " ".join(_ACRONYMS.get(word.lower(), word.title()) for word in words)


def _module_doc_label(name: str) -> str:
    """Return a concise reader-facing label for an autodoc module page."""

    if name in _MODULE_LABELS:
        return _MODULE_LABELS[name]
    if name in _PACKAGE_LABELS:
        return _PACKAGE_LABELS[name]
    parts = [part for part in name.split(".") if part not in {"spatial_vtk", "__init__"}]
    if not parts:
        return "Package"
    if len(parts) == 1:
        return _humanize_module_part(parts[0])
    prefix = _SECTION_PREFIXES.get(parts[-2])
    leaf = _humanize_module_part(parts[-1])
    if leaf.lower() in {"overview", "figures", "maps", "plots", "tables"} and prefix:
        return prefix
    if prefix and not leaf.startswith(prefix):
        return f"{prefix} {leaf}"
    return leaf


def _replace_section_heading(lines: list[str], old_title: str, new_title: str) -> None:
    """Replace a simple RST section heading and keep the underline valid."""

    for index in range(len(lines) - 1):
        if lines[index].strip() == old_title and set(lines[index + 1].strip()) == {"-"}:
            lines[index] = new_title
            lines[index + 1] = "-" * len(new_title)


def _name_module_docstring_sections(app, what, name, obj, options, lines) -> None:
    """Give repeated module docstring sections descriptive API headings."""

    if what != "module" or not name.startswith("spatial_vtk."):
        return
    label = _module_doc_label(name)
    _replace_section_heading(lines, "Purpose", f"{label} Overview")
    _replace_section_heading(lines, "Usage examples", f"{label} Examples")


def _has_docstring_section(lines: list[str], section_names: set[str]) -> bool:
    """Return whether an autodoc docstring already has one of the sections."""

    normalized = {line.strip().lower().rstrip(":") for line in lines}
    return any(section.lower() in normalized for section in section_names)


def _format_annotation(annotation: object) -> str:
    """Format one Python type annotation for reader-facing API docs."""

    if annotation is inspect.Signature.empty:
        return "Any"
    if annotation is None:
        return "None"
    if annotation is type(None):
        return "None"
    if isinstance(annotation, str):
        return annotation
    if annotation is Any:
        return "Any"
    module = getattr(annotation, "__module__", "")
    qualname = getattr(annotation, "__qualname__", None)
    if qualname:
        if module == "builtins":
            return qualname
        return f"{module}.{qualname}"
    text = str(annotation)
    return text.replace("typing.", "")


def _parameter_type_text(parameter: inspect.Parameter, type_hints: dict[str, object]) -> str:
    """Return the API docs type text for one function parameter."""

    annotation = type_hints.get(parameter.name, parameter.annotation)
    type_text = _format_annotation(annotation)
    if parameter.default is not inspect.Signature.empty:
        type_text = f"{type_text}, optional"
    return type_text


def _parameter_description(parameter: inspect.Parameter) -> str:
    """Return a concise generic description for an undocumented parameter."""

    if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
        return "Additional positional arguments forwarded to the wrapped function."
    if parameter.kind is inspect.Parameter.VAR_KEYWORD:
        return "Additional keyword options forwarded to the wrapped function."
    name = parameter.name
    if name in _PARAMETER_DESCRIPTIONS:
        description = _PARAMETER_DESCRIPTIONS[name]
    else:
        normalized = name.lower()
        description = next(
            (
                pattern_description
                for pattern, pattern_description in _PARAMETER_NAME_PATTERNS
                if pattern in normalized
            ),
            f"Value supplied for the ``{name}`` parameter.",
        )
    if parameter.default is inspect.Signature.empty:
        return description
    return f"{description} Defaults to ``{parameter.default!r}``."


def _append_missing_parameter_docs(obj, lines: list[str]) -> None:
    """Append a Parameters section when a public API function lacks one."""

    if _has_docstring_section(lines, {"Parameters", "Args", "Arguments"}):
        return
    try:
        signature = inspect.signature(obj)
    except (TypeError, ValueError):
        return
    try:
        type_hints = get_type_hints(obj)
    except Exception:
        type_hints = {}
    parameters = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.name not in {"self", "cls"}
    ]
    if not parameters:
        return
    if lines and lines[-1].strip():
        lines.append("")
    for parameter in parameters:
        lines.append(f":param {parameter.name}: {_parameter_description(parameter)}")
        lines.append(f":type {parameter.name}: {_parameter_type_text(parameter, type_hints)}")


def _append_missing_return_docs(obj, lines: list[str]) -> None:
    """Append a Returns section when a public API function lacks one."""

    if _has_docstring_section(lines, {"Returns", "Return", "Yields", "Yield"}):
        return
    try:
        signature = inspect.signature(obj)
    except (TypeError, ValueError):
        return
    try:
        type_hints = get_type_hints(obj)
    except Exception:
        type_hints = {}
    return_annotation = type_hints.get("return", signature.return_annotation)
    return_type = _format_annotation(return_annotation)
    if lines and lines[-1].strip():
        lines.append("")
    lines.append(":returns: Result produced by the function.")
    lines.append(f":rtype: {return_type}")


def _complete_function_docstrings(app, what, name, obj, options, lines) -> None:
    """Fill missing function parameter and return docs from signatures."""

    if what not in {"function", "method"} or not name.startswith("spatial_vtk."):
        return
    _append_missing_parameter_docs(obj, lines)
    _append_missing_return_docs(obj, lines)


def _write_notebook_download_zips(app, exception) -> None:
    """Write zipped notebook downloads into the HTML static directory."""

    if exception is not None:
        return
    examples_dir = Path(app.srcdir) / "examples"
    download_dir = Path(app.outdir) / "_static" / "notebooks"
    download_dir.mkdir(parents=True, exist_ok=True)
    notebook_paths = list(examples_dir.glob("step_*.ipynb"))
    notebook_paths.extend((examples_dir / "large_run").glob("step_*.ipynb"))
    for notebook_path in sorted(notebook_paths):
        zip_path = download_dir / f"{notebook_path.name}.zip"
        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
            archive.write(notebook_path, arcname=notebook_path.name)


def setup(app) -> None:
    """Register Spatial-VTK docs build hooks."""

    app.connect("autodoc-process-docstring", _name_module_docstring_sections)
    app.connect("autodoc-process-docstring", _complete_function_docstrings)
    app.connect("build-finished", _write_notebook_download_zips)
