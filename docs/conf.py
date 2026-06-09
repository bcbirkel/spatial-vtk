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
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "nbsphinx"]
templates_path = ["_templates"]
exclude_patterns = ["_build", ".ipynb_checkpoints"]
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
nbsphinx_execute = "never"
nbsphinx_prolog = r"""
{% set notebook_stem = env.docname.rsplit('/', 1)[-1] %}
.. raw:: html

   <p class="notebook-download"><a class="reference download" href="../_static/notebooks/{{ notebook_stem }}.ipynb.zip" download>Download this notebook</a></p>

"""


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
    "spatial_vtk.metrics.calculate.gof": "GOF Calculation",
    "spatial_vtk.spatial.calculate.geojson": "GeoJSON Calculations",
    "spatial_vtk.spatial.calculate.pca": "PCA Calculations",
    "spatial_vtk.spatial.map.geojson": "GeoJSON Maps",
    "spatial_vtk.spatial.map.pca": "PCA Maps",
    "spatial_vtk.spatial.plot.pca": "PCA Plots",
    "spatial_vtk.visualize.figure_io": "Figure I/O",
    "spatial_vtk.visualize.qc.overview": "Quality Control",
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
        return "Additional positional arguments passed to the function."
    if parameter.kind is inspect.Parameter.VAR_KEYWORD:
        return "Additional keyword arguments passed to the function."
    if parameter.default is inspect.Signature.empty:
        return "Required function argument."
    return f"Optional function argument. Defaults to ``{parameter.default!r}``."


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
    lines.append(":returns: Return value produced by the function.")
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
    for notebook_path in sorted(examples_dir.glob("step_*.ipynb")):
        zip_path = download_dir / f"{notebook_path.name}.zip"
        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
            archive.write(notebook_path, arcname=notebook_path.name)


def setup(app) -> None:
    """Register Spatial-VTK docs build hooks."""

    app.connect("autodoc-process-docstring", _name_module_docstring_sections)
    app.connect("autodoc-process-docstring", _complete_function_docstrings)
    app.connect("build-finished", _write_notebook_download_zips)
