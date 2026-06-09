"""Synthetic model alias discovery and folder resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelFolderCandidate:
    """Describe one discovered synthetic model folder."""

    folder: str
    base_model: str
    basin_scope: str
    has_ely: bool
    implementation_tokens: tuple[str, ...]
    default_alias: str


@dataclass(frozen=True)
class ModelResolution:
    """Resolved model aliases and backing folders."""

    models: tuple[str, ...]
    model_folders: dict[str, str]
    ambiguous: dict[str, tuple[ModelFolderCandidate, ...]]


COMPAT_ALIASES = {
    "bbp1D": "bbp1d",
    "bbp1d": "bbp1d",
    "lab-si": "cvmsi-lab",
    "lab-si-ely": "cvmsi-lab-ely",
    "basins-si": "cvmsi-basins",
    "basins-si-ely": "cvmsi-basins-ely",
    "basins-s5": "cvms5-basins",
    "basins-s5-ely": "cvms5-basins-ely",
    "cvmh-bbp1d": "bbp1d",
    "basins-bbp1d": "bbp1d-basins",
}


def scan_synthetic_model_folders(input_syn_path: str | Path) -> list[ModelFolderCandidate]:
    """Scan a synthetic root and classify immediate child folders.

    Parameters
    ----------
    input_syn_path
        Synthetic root directory or path template containing ``{model}``.

    Returns
    -------
    list of ModelFolderCandidate
        Classified folders sorted by folder name.
    """

    root = _scan_root(input_syn_path)
    if not root.exists() or not root.is_dir():
        return []
    candidates: list[ModelFolderCandidate] = []
    for child in sorted(root.iterdir(), key=lambda path: path.name.lower()):
        if not child.is_dir():
            continue
        candidate = classify_model_folder(child.name)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def classify_model_folder(folder_name: str) -> ModelFolderCandidate | None:
    """Classify one folder name into a model candidate.

    Parameters
    ----------
    folder_name
        Folder name to classify.

    Returns
    -------
    ModelFolderCandidate or None
        Classified model candidate, or None when no known model token is found.
    """

    name = str(folder_name)
    lower = name.lower()
    base = _detect_base_model(lower)
    if base is None:
        return None
    has_ely = bool(re.search(r"(^|[_\-.])ely(gtl|jordan)?([_\-.]|$)", lower)) or "elygtl" in lower
    basin_scope = _detect_basin_scope(lower)
    alias = base
    if basin_scope == "lab":
        alias = f"{alias}-lab"
    elif basin_scope == "all-basins":
        alias = f"{alias}-basins"
    if has_ely:
        alias = f"{alias}-ely"
    return ModelFolderCandidate(
        folder=name,
        base_model=base,
        basin_scope=basin_scope,
        has_ely=has_ely,
        implementation_tokens=_implementation_tokens(lower, base),
        default_alias=alias,
    )


def normalize_model_alias(alias: str) -> str:
    """Normalize model alias spelling.

    Parameters
    ----------
    alias
        User-supplied model alias.

    Returns
    -------
    str
        Normalized alias.
    """

    raw = str(alias).strip()
    if not raw:
        return raw
    compat = COMPAT_ALIASES.get(raw) or COMPAT_ALIASES.get(raw.lower())
    if compat:
        return compat
    lower = raw.lower().replace("_", "-")
    if lower == "bbp1d":
        return "bbp1d"
    return lower


def resolve_model_aliases(
    requested: list[str],
    input_syn_path: str | Path,
    *,
    model_folders: dict[str, str] | None = None,
    allow_ambiguous: bool = False,
) -> ModelResolution:
    """Resolve requested model aliases to folders under a synthetic root.

    Parameters
    ----------
    requested
        Requested aliases or folder names.
    input_syn_path
        Synthetic root directory or path template containing ``{model}``.
    model_folders
        Optional explicit alias-to-folder mapping.
    allow_ambiguous
        If true, keep all folder matches by adding variant suffixes.

    Returns
    -------
    ModelResolution
        Resolved aliases, selected folders, and any ambiguous matches.
    """

    explicit = dict(model_folders or {})
    candidates = scan_synthetic_model_folders(input_syn_path)
    by_alias: dict[str, list[ModelFolderCandidate]] = {}
    by_folder = {candidate.folder: candidate for candidate in candidates}
    for candidate in candidates:
        by_alias.setdefault(candidate.default_alias, []).append(candidate)

    resolved_models: list[str] = []
    resolved_folders: dict[str, str] = {}
    ambiguous: dict[str, tuple[ModelFolderCandidate, ...]] = {}

    for item in requested:
        alias = normalize_model_alias(item)
        if item in by_folder and alias not in by_alias:
            candidate = by_folder[item]
            alias = candidate.default_alias
            matches = [candidate]
        elif alias in explicit:
            resolved_models.append(alias)
            resolved_folders[alias] = explicit[alias]
            continue
        else:
            matches = by_alias.get(alias, [])
        if not matches:
            resolved_models.append(alias)
            resolved_folders[alias] = item
            continue
        if len(matches) > 1 and not allow_ambiguous:
            ambiguous[alias] = tuple(matches)
            continue
        for index, candidate in enumerate(matches):
            selected_alias = alias
            if len(matches) > 1:
                suffix = _variant_suffix(candidate)
                selected_alias = f"{alias}-{suffix}" if suffix else f"{alias}-{index + 1}"
            resolved_models.append(selected_alias)
            resolved_folders[selected_alias] = candidate.folder

    return ModelResolution(tuple(resolved_models), resolved_folders, ambiguous)


def available_base_models(input_syn_path: str | Path) -> list[str]:
    """Return discovered base model families.

    Parameters
    ----------
    input_syn_path
        Synthetic root directory or template path.

    Returns
    -------
    list of str
        Sorted base-model family names.
    """

    return sorted({candidate.base_model for candidate in scan_synthetic_model_folders(input_syn_path)})


def _scan_root(input_syn_path: str | Path) -> Path:
    """Infer the model folder parent from a root or template path."""

    raw = str(input_syn_path)
    if "{model" in raw:
        return Path(raw.split("{model", 1)[0]).expanduser()
    if "{model_name" in raw:
        return Path(raw.split("{model_name", 1)[0]).expanduser()
    path = Path(raw).expanduser()
    if path.is_file():
        return path.parent
    return path


def _detect_base_model(lower: str) -> str | None:
    """Detect a known base model family."""

    if "cvmsi" in lower or "cvm-si" in lower:
        return "cvmsi"
    if "cvms5" in lower or "cvms-5" in lower:
        return "cvms5"
    if "cvms4" in lower or "cvms-4" in lower:
        return "cvms4"
    if "bbp1d" in lower or "bbp_1d" in lower or "bbp-1d" in lower:
        return "bbp1d"
    if "cvmh" in lower or "cvm-h" in lower:
        return "cvmh"
    return None


def _detect_basin_scope(lower: str) -> str:
    """Detect basin-scope tokens from a folder name."""

    has_lab = "cvmhlabn" in lower
    has_all = all(token in lower for token in ("cvmhlabn", "cvmhsgbn", "cvmhsbbn", "cvmhvbn"))
    if has_all:
        return "all-basins"
    if has_lab:
        return "lab"
    return "base"


def _implementation_tokens(lower: str, base: str) -> tuple[str, ...]:
    """Extract coarse implementation variant tokens."""

    tokens: list[str] = []
    for token in ("csrules", "poissoncap", "dropsr", "unstructuredmesh", "h5", "asdf", "mseed"):
        if token in lower and token != base:
            tokens.append(token)
    return tuple(tokens)


def _variant_suffix(candidate: ModelFolderCandidate) -> str:
    """Return a readable suffix for an implementation variant."""

    for token in candidate.implementation_tokens:
        if token not in {"unstructuredmesh"}:
            return token
    return candidate.implementation_tokens[0] if candidate.implementation_tokens else ""
