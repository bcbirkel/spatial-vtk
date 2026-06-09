"""Arrival-pick catalog helpers."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pandas as pd

DEFAULT_PICKER = "phasenet"

REQUIRED_PICK_COLUMNS = (
    "event_id",
    "station",
    "component",
    "phase",
    "pick_time_abs",
    "pick_time_rel_s",
    "probability",
    "method",
)
OPTIONAL_PICK_COLUMNS = ("source",)

PHASENET_INSTALL_MESSAGE = (
    "PhaseNet is the default arrival picker for spatial-vtk, but no PhaseNet "
    "command was found. Install the package dependency `phasenet`, set "
    "SVTK_PHASENET_COMMAND to the picker command, or pass an explicit picker "
    "command. Use picker='catalog' only when you are intentionally loading an "
    "existing pick catalog."
)


class PhaseNetUnavailableError(RuntimeError):
    """Raised when the default PhaseNet picker cannot be found."""


def find_phasenet_command(explicit_command: str | None = None) -> str | None:
    """Find the configured PhaseNet command.

    Parameters
    ----------
    explicit_command
        Optional user-supplied command or executable path.

    Returns
    -------
    str or None
        Command text when PhaseNet appears available; otherwise ``None``.
    """

    candidates = [
        explicit_command,
        os.environ.get("SVTK_PHASENET_COMMAND"),
        os.environ.get("VTK_PHASENET_COMMAND"),
        "python -m phasenet.predict",
        "phasenet",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        command = str(candidate).strip()
        if " " in command and _python_module_command_available(command):
            return command
        if Path(command).exists():
            return command
        resolved = shutil.which(command)
        if resolved:
            return resolved
    return None


def require_phasenet(explicit_command: str | None = None) -> str:
    """Return a PhaseNet command or raise a clear availability error."""

    command = find_phasenet_command(explicit_command)
    if command is None:
        raise PhaseNetUnavailableError(PHASENET_INSTALL_MESSAGE)
    return command


def resolve_arrival_picker(
    picker: str | None = None,
    *,
    phasenet_command: str | None = None,
    allow_catalog_only: bool = False,
) -> str:
    """Resolve the arrival-picking backend.

    Parameters
    ----------
    picker
        Picker selector. ``None`` defaults to ``"phasenet"``.
    phasenet_command
        Optional explicit PhaseNet command.
    allow_catalog_only
        Whether ``picker="catalog"`` is allowed for workflows that load
        existing picks instead of creating new picks.

    Returns
    -------
    str
        Resolved picker command or ``"catalog"``.
    """

    selected = (picker or DEFAULT_PICKER).strip().lower()
    if selected in {"phasenet", "default", "auto"}:
        return require_phasenet(phasenet_command)
    if selected == "catalog" and allow_catalog_only:
        return "catalog"
    raise ValueError("Arrival picker must be 'phasenet' by default, or 'catalog' when loading existing picks.")


def normalize_pick_catalog(df: pd.DataFrame, *, default_method: str = DEFAULT_PICKER) -> pd.DataFrame:
    """Return a pick table with the public required pick-catalog columns."""

    out = df.copy()
    aliases = {
        "event": "event_id",
        "event_title": "event_id",
        "Station": "station",
        "Component": "component",
        "waveform_source": "source",
        "phase_name": "phase",
        "time": "pick_time_abs",
        "timestamp": "pick_time_abs",
        "time_rel_s": "pick_time_rel_s",
        "pick_time": "pick_time_abs",
        "prob": "probability",
        "score": "probability",
    }
    for old, new in aliases.items():
        if old in out.columns and new not in out.columns:
            out[new] = out[old]
    for column in REQUIRED_PICK_COLUMNS:
        if column not in out.columns:
            out[column] = default_method if column == "method" else ""
    out["phase"] = out["phase"].astype(str).str.upper()
    out["pick_time_rel_s"] = pd.to_numeric(out["pick_time_rel_s"], errors="coerce")
    out["probability"] = pd.to_numeric(out["probability"], errors="coerce")
    for column in OPTIONAL_PICK_COLUMNS:
        if column in out.columns:
            out[column] = out[column].astype(str).str.strip().str.lower()
    columns = [*REQUIRED_PICK_COLUMNS, *(column for column in OPTIONAL_PICK_COLUMNS if column in out.columns)]
    return out.loc[:, list(columns)]


def load_arrival_pick_catalog(path: str | Path) -> pd.DataFrame:
    """Load one arrival-pick catalog from CSV or Parquet."""

    source = Path(path)
    df = pd.read_parquet(source) if source.suffix.lower() in {".parquet", ".pq"} else pd.read_csv(source)
    return normalize_pick_catalog(df)


def write_arrival_pick_catalog(df: pd.DataFrame, path: str | Path, *, overwrite: bool = False) -> Path:
    """Write one normalized pick catalog to CSV or Parquet."""

    output = Path(path)
    if output.exists() and not overwrite:
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_pick_catalog(df)
    if output.suffix.lower() in {".parquet", ".pq"}:
        normalized.to_parquet(output, index=False)
    else:
        normalized.to_csv(output, index=False)
    return output


def _python_module_command_available(command: str) -> bool:
    """Return whether a ``python -m module`` command is importable."""

    try:
        tokens = shlex.split(str(command))
    except ValueError:
        return False
    if len(tokens) < 3 or tokens[1] != "-m":
        return False
    executable = shutil.which(tokens[0]) or tokens[0]
    module = tokens[2]
    try:
        completed = subprocess.run(
            [executable, "-c", f"import {module}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except Exception:
        return False
    return completed.returncode == 0
