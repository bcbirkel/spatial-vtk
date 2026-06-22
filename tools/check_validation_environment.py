#!/usr/bin/env python3
"""Check that the active Python can run Spatial-VTK validation gates."""

from __future__ import annotations

import argparse
import importlib.util
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

MIN_PYTHON = (3, 10)
MAX_PYTHON = (3, 14)
INSTALL_COMMAND = 'python -m pip install -e ".[validation,docs,dashboard,notebooks,waveforms]"'
CONDA_COMMAND = "conda env create -f svtk_environment.yaml"


@dataclass(frozen=True)
class ModuleRequirement:
    """One importable module required by a validation group."""

    label: str
    module: str


MODULE_GROUPS: dict[str, tuple[ModuleRequirement, ...]] = {
    "core": (
        ModuleRequirement("spatial_vtk", "spatial_vtk"),
        ModuleRequirement("branca", "branca"),
        ModuleRequirement("contextily", "contextily"),
        ModuleRequirement("folium", "folium"),
        ModuleRequirement("geopandas", "geopandas"),
        ModuleRequirement("matplotlib", "matplotlib"),
        ModuleRequirement("numpy", "numpy"),
        ModuleRequirement("pandas", "pandas"),
        ModuleRequirement("phasenet", "phasenet"),
        ModuleRequirement("plotly", "plotly"),
        ModuleRequirement("pyarrow", "pyarrow"),
        ModuleRequirement("pyproj", "pyproj"),
        ModuleRequirement("PyYAML", "yaml"),
        ModuleRequirement("rasterio", "rasterio"),
        ModuleRequirement("scikit-learn", "sklearn"),
        ModuleRequirement("scipy", "scipy"),
        ModuleRequirement("shapely", "shapely"),
        ModuleRequirement("statsmodels", "statsmodels"),
        ModuleRequirement("streamlit", "streamlit"),
        ModuleRequirement("streamlit-folium", "streamlit_folium"),
    ),
    "validation": (
        ModuleRequirement("build", "build"),
        ModuleRequirement("coverage", "coverage"),
        ModuleRequirement("IPython", "IPython"),
        ModuleRequirement("pytest", "pytest"),
        ModuleRequirement("twine", "twine"),
    ),
    "docs": (
        ModuleRequirement("IPython", "IPython"),
        ModuleRequirement("sphinx", "sphinx"),
        ModuleRequirement("sphinx-rtd-theme", "sphinx_rtd_theme"),
    ),
    "dashboard": (
        ModuleRequirement("branca", "branca"),
        ModuleRequirement("folium", "folium"),
        ModuleRequirement("plotly", "plotly"),
        ModuleRequirement("streamlit", "streamlit"),
        ModuleRequirement("streamlit-folium", "streamlit_folium"),
    ),
    "notebooks": (
        ModuleRequirement("ipykernel", "ipykernel"),
        ModuleRequirement("IPython", "IPython"),
        ModuleRequirement("nbclient", "nbclient"),
        ModuleRequirement("nbformat", "nbformat"),
    ),
    "waveforms": (
        ModuleRequirement("gmprocess", "gmprocess"),
        ModuleRequirement("h5py", "h5py"),
        ModuleRequirement("obspy", "obspy"),
        ModuleRequirement("pyasdf", "pyasdf"),
    ),
}
GROUP_ALIASES = {
    "release": ("core", "validation", "docs", "dashboard", "notebooks", "waveforms"),
    "tutorial": ("core", "dashboard", "notebooks", "waveforms"),
}


def configure_source_checkout_imports(repo_root: Path | None = None) -> None:
    """Make ``src`` importable when the checker runs from a source checkout."""

    root = Path.cwd() if repo_root is None else repo_root
    if not (root / "pyproject.toml").exists():
        return
    src_path = root / "src"
    if src_path.exists():
        sys.path.insert(0, str(src_path))


def python_version_supported(version_info: Sequence[int] | None = None) -> bool:
    """Return whether ``version_info`` satisfies Spatial-VTK's public range."""

    info = sys.version_info if version_info is None else version_info
    version = (int(info[0]), int(info[1]))
    return MIN_PYTHON <= version < MAX_PYTHON


def normalize_groups(groups: Iterable[str]) -> tuple[str, ...]:
    """Expand validation group aliases and reject unknown group names."""

    expanded: list[str] = []
    for group in groups:
        if group in GROUP_ALIASES:
            expanded.extend(GROUP_ALIASES[group])
        elif group in MODULE_GROUPS:
            expanded.append(group)
        else:
            choices = sorted([*MODULE_GROUPS, *GROUP_ALIASES])
            raise ValueError(f"Unknown validation group {group!r}. Choose from: {', '.join(choices)}")
    deduped: list[str] = []
    for group in expanded:
        if group not in deduped:
            deduped.append(group)
    return tuple(deduped)


def missing_validation_modules(
    groups: Iterable[str],
    *,
    module_available: Callable[[str], bool] | None = None,
) -> list[ModuleRequirement]:
    """Return missing modules for the selected validation groups."""

    available = _module_available if module_available is None else module_available
    missing: list[ModuleRequirement] = []
    checked: set[str] = set()
    for group in normalize_groups(groups):
        for requirement in MODULE_GROUPS[group]:
            if requirement.module in checked:
                continue
            checked.add(requirement.module)
            if not available(requirement.module):
                missing.append(requirement)
    return missing


def _module_available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def format_missing_modules(missing: Sequence[ModuleRequirement]) -> str:
    """Return a readable missing-module list."""

    return ", ".join(f"{item.label} ({item.module})" for item in missing)


def current_python_install_command() -> str:
    """Return the tutorial/release install command for the active Python."""

    return f'{shlex.quote(sys.executable)} -m pip install -e ".[validation,docs,dashboard,notebooks,waveforms]"'


def validation_check_command(groups: Iterable[str], *, executable: str = "python") -> str:
    """Return a command that reruns this checker for ``groups``."""

    args = " ".join(shlex.quote(str(group)) for group in groups)
    return f"{shlex.quote(executable)} tools/check_validation_environment.py --groups {args}"


def current_python_validation_check_command(groups: Iterable[str]) -> str:
    """Return the checker rerun command for the active Python executable."""

    return validation_check_command(groups, executable=sys.executable)


def build_parser() -> argparse.ArgumentParser:
    """Build the command parser."""

    choices = sorted([*MODULE_GROUPS, *GROUP_ALIASES])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--groups",
        nargs="+",
        default=["release"],
        choices=choices,
        help=(
            "Validation dependency groups to check. Use 'release' for the full "
            "release-checklist environment or 'tutorial' for notebook execution."
        ),
    )
    parser.add_argument(
        "--no-source-checkout",
        action="store_true",
        help="Do not add ./src to sys.path before checking imports.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the validation-environment check."""

    args = build_parser().parse_args(argv)
    if not args.no_source_checkout:
        configure_source_checkout_imports()

    groups = normalize_groups(args.groups)
    if not python_version_supported():
        current = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        print(
            "Spatial-VTK validation requires Python >=3.10,<3.14. "
            f"Current Python executable: {sys.executable}. Current version: {current}.",
            file=sys.stderr,
        )
        return 1

    missing = missing_validation_modules(groups)
    if missing:
        print(
            "Missing Spatial-VTK validation modules: "
            f"{format_missing_modules(missing)}.",
            file=sys.stderr,
        )
        print(f"Current Python executable: {sys.executable}.", file=sys.stderr)
        print(f"From a source checkout, install with: {INSTALL_COMMAND}", file=sys.stderr)
        print(
            "For this exact Python environment, install with: "
            f"{current_python_install_command()}",
            file=sys.stderr,
        )
        print(
            "After installing, rerun this check with: "
            f"{validation_check_command(args.groups)}",
            file=sys.stderr,
        )
        print(
            "For this exact Python environment, rerun: "
            f"{current_python_validation_check_command(args.groups)}",
            file=sys.stderr,
        )
        print(
            "If compiled geospatial or waveform dependencies are difficult to "
            f"solve with pip, create the conda environment with: {CONDA_COMMAND}",
            file=sys.stderr,
        )
        return 1

    print(
        "Spatial-VTK validation environment ready: "
        f"{', '.join(groups)} group(s) available for Python {sys.version_info.major}."
        f"{sys.version_info.minor}.{sys.version_info.micro}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
