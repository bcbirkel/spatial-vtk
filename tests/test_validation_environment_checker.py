from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


def _load_checker_module():
    """Load the validation checker without requiring tools as a package."""

    path = Path(__file__).resolve().parents[1] / "tools" / "check_validation_environment.py"
    spec = importlib.util.spec_from_file_location("check_validation_environment", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _pyproject_dependency_names(pyproject_text: str) -> set[str]:
    """Return normalized dependency package names declared in ``pyproject.toml``."""

    names: set[str] = set()
    for requirement in re.findall(r'"([^"]+)"', pyproject_text):
        if any(token in requirement for token in ("://", "@")):
            continue
        name = re.split(r"[\[<>=!~\s]", requirement, maxsplit=1)[0].strip().lower()
        if name:
            names.add(name)
    return names


def _checker_distribution_names(module) -> set[str]:
    """Return normalized package/distribution names required by the checker."""

    label_to_distribution_name = {
        "IPython": "ipython",
        "PyYAML": "pyyaml",
        "scikit-learn": "scikit-learn",
        "spatial_vtk": None,
        "sphinx-rtd-theme": "sphinx-rtd-theme",
    }
    names: set[str] = set()
    for requirements in module.MODULE_GROUPS.values():
        for requirement in requirements:
            mapped = label_to_distribution_name.get(requirement.label, requirement.label.lower())
            if mapped is not None:
                names.add(mapped)
    return names


def test_validation_environment_group_aliases_expand_and_deduplicate() -> None:
    """Release aliases should resolve to the full validation gate once."""

    module = _load_checker_module()

    assert module.normalize_groups(["tutorial", "dashboard"]) == (
        "core",
        "dashboard",
        "notebooks",
        "waveforms",
    )
    assert module.normalize_groups(["release"]) == (
        "core",
        "validation",
        "docs",
        "dashboard",
        "notebooks",
        "waveforms",
    )


def test_validation_environment_missing_report_uses_package_labels() -> None:
    """Missing-module output should name both package and import module."""

    module = _load_checker_module()
    missing = module.missing_validation_modules(
        ["validation", "docs"],
        module_available=lambda name: name in {"coverage", "IPython", "pytest"},
    )

    assert [item.label for item in missing] == ["build", "twine", "sphinx", "sphinx-rtd-theme"]
    assert module.format_missing_modules(missing) == (
        "build (build), twine (twine), sphinx (sphinx), "
        "sphinx-rtd-theme (sphinx_rtd_theme)"
    )


def test_validation_environment_modules_are_declared_package_dependencies() -> None:
    """The validation preflight should not check undeclared pip dependencies."""

    module = _load_checker_module()
    root = Path(__file__).resolve().parents[1]
    pyproject_text = (root / "pyproject.toml").read_text(encoding="utf-8")

    declared_names = _pyproject_dependency_names(pyproject_text)
    checker_names = _checker_distribution_names(module)

    undeclared = sorted(checker_names - declared_names)
    assert not undeclared, f"Validation modules missing from pyproject.toml: {undeclared}"


def test_validation_environment_rejects_unsupported_python_versions() -> None:
    """The checker should mirror the package's public Python range."""

    module = _load_checker_module()

    assert module.python_version_supported((3, 10, 0))
    assert module.python_version_supported((3, 13, 9))
    assert not module.python_version_supported((3, 9, 18))
    assert not module.python_version_supported((3, 14, 0))


def test_validation_environment_missing_report_names_exact_python(monkeypatch, capsys) -> None:
    """Missing-module failures should show commands for the active environment."""

    module = _load_checker_module()
    monkeypatch.setattr(module, "_module_available", lambda name: name == "spatial_vtk")

    result = module.main(["--groups", "tutorial"])

    captured = capsys.readouterr()
    assert result == 1
    assert "Missing Spatial-VTK validation modules:" in captured.err
    assert f"Current Python executable: {sys.executable}." in captured.err
    assert module.INSTALL_COMMAND in captured.err
    assert module.current_python_install_command() in captured.err
    assert module.validation_check_command(["tutorial"]) in captured.err
    assert module.current_python_validation_check_command(["tutorial"]) in captured.err
