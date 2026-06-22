from __future__ import annotations

import importlib.util
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


def test_validation_environment_rejects_unsupported_python_versions() -> None:
    """The checker should mirror the package's public Python range."""

    module = _load_checker_module()

    assert module.python_version_supported((3, 10, 0))
    assert module.python_version_supported((3, 13, 9))
    assert not module.python_version_supported((3, 9, 18))
    assert not module.python_version_supported((3, 14, 0))
