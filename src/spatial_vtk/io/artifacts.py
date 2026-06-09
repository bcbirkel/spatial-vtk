"""Deterministic output artifact planning helpers.

Purpose
-------
This module creates stable file paths and JSON manifests for public
Spatial-VTK outputs such as figures, metrics, dashboard tables, and spatial
statistics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json
import re


@dataclass(frozen=True)
class ArtifactSpec:
    """Describe one planned output artifact.

    Parameters
    ----------
    kind
        Broad artifact type such as ``"figure"``, ``"metrics"``, or
        ``"dashboard"``.
    name
        Human-readable artifact name.
    scope
        Stable row/plot identity such as metric, event, station, or model.
    config
        Compute-relevant configuration.
    extension
        Output filename extension, including the leading dot.
    subdir
        Optional subdirectory under the artifact root.

    Returns
    -------
    ArtifactSpec
        Immutable artifact planning record.
    """

    kind: str
    name: str
    scope: Mapping[str, Any] | None = None
    config: Mapping[str, Any] | None = None
    extension: str = ".json"
    subdir: str | None = None

    def payload(self) -> dict[str, Any]:
        """Return the deterministic payload used for hashing."""

        return {
            "kind": self.kind,
            "name": self.name,
            "scope": dict(self.scope or {}),
            "config": dict(self.config or {}),
            "extension": self.extension,
            "subdir": self.subdir,
        }


@dataclass(frozen=True)
class ArtifactRecord:
    """Record one workflow artifact in a public registry.

    Parameters
    ----------
    artifact_path
        Artifact path on disk.
    kind
        Broad artifact group such as ``"metrics"`` or ``"qc"``.
    name
        Human-readable artifact name.
    status
        Status label such as ``"planned"``, ``"written"``, or ``"missing"``.
    artifact_hash
        Optional deterministic hash from an artifact spec.
    metadata
        Optional user-provided metadata.
    recorded_at
        UTC ISO timestamp.

    Returns
    -------
    ArtifactRecord
        Immutable registry entry.
    """

    artifact_path: str
    kind: str
    name: str
    status: str = "planned"
    artifact_hash: str = ""
    metadata: Mapping[str, Any] | None = None
    recorded_at: str = ""


def canonical_json(value: Mapping[str, Any]) -> str:
    """Serialize one mapping to stable JSON.

    Parameters
    ----------
    value
        Mapping to serialize.

    Returns
    -------
    str
        Deterministic compact JSON string.
    """

    return json.dumps(dict(value), sort_keys=True, separators=(",", ":"), default=str)


def stable_hash(value: Mapping[str, Any], *, length: int | None = None) -> str:
    """Return a stable SHA256 hash for one mapping.

    Parameters
    ----------
    value
        Mapping to hash.
    length
        Optional prefix length.

    Returns
    -------
    str
        Full hash or hash prefix.
    """

    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return digest[: int(length)] if length else digest


def slugify(value: object, *, max_length: int = 96) -> str:
    """Return a filesystem-safe lowercase token.

    Parameters
    ----------
    value
        Raw label.
    max_length
        Maximum returned string length.

    Returns
    -------
    str
        Safe filename token.
    """

    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return (text or "artifact")[: int(max_length)].strip("_") or "artifact"


def artifact_path_for_spec(root: str | Path, spec: ArtifactSpec, *, hash_length: int = 10) -> Path:
    """Return the deterministic output path for one artifact spec.

    Parameters
    ----------
    root
        Artifact root directory.
    spec
        Artifact planning record.
    hash_length
        Hash prefix length in the filename.

    Returns
    -------
    pathlib.Path
        Planned artifact path.
    """

    root_path = Path(root).expanduser()
    subdir = slugify(spec.subdir or spec.kind)
    name = slugify(spec.name)
    suffix = stable_hash(spec.payload(), length=hash_length)
    extension = spec.extension if str(spec.extension).startswith(".") else f".{spec.extension}"
    return root_path / subdir / f"{name}__{suffix}{extension}"


def artifact_manifest_path(artifact_path: str | Path) -> Path:
    """Return the JSON manifest sidecar path for one artifact path."""

    return Path(artifact_path).expanduser().with_suffix(".manifest.json")


def write_artifact_manifest(
    artifact_path: str | Path,
    spec: ArtifactSpec,
    *,
    extra: Mapping[str, Any] | None = None,
) -> Path:
    """Write a JSON manifest next to a planned artifact.

    Parameters
    ----------
    artifact_path
        Output artifact path.
    spec
        Artifact planning record.
    extra
        Optional additional manifest fields.

    Returns
    -------
    pathlib.Path
        Written manifest path.
    """

    path = Path(artifact_path).expanduser()
    manifest = artifact_manifest_path(path)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_path": str(path),
        "artifact_hash": stable_hash(spec.payload()),
        "spec": asdict(spec),
    }
    if extra:
        payload["extra"] = dict(extra)
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return manifest


def read_artifact_manifest(manifest_path: str | Path) -> dict[str, Any]:
    """Read a JSON artifact manifest.

    Parameters
    ----------
    manifest_path
        Manifest JSON path.

    Returns
    -------
    dict
        Parsed manifest payload.
    """

    return json.loads(Path(manifest_path).expanduser().read_text(encoding="utf-8"))


class ArtifactRegistry:
    """Append-only JSON-lines artifact registry.

    Parameters
    ----------
    registry_path
        Path to the registry file.

    Returns
    -------
    ArtifactRegistry
        Registry object used to append and inspect artifact records.
    """

    def __init__(self, registry_path: str | Path) -> None:
        """Create one registry object."""

        self.registry_path = Path(registry_path).expanduser()

    def record(
        self,
        artifact_path: str | Path,
        *,
        kind: str,
        name: str,
        status: str = "written",
        spec: ArtifactSpec | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ArtifactRecord:
        """Append one artifact record.

        Parameters
        ----------
        artifact_path
            Output path being recorded.
        kind, name, status
            Registry classification fields.
        spec
            Optional artifact spec used to compute a stable hash.
        metadata
            Optional metadata copied into the registry.

        Returns
        -------
        ArtifactRecord
            Appended record.
        """

        record = ArtifactRecord(
            artifact_path=str(Path(artifact_path).expanduser()),
            kind=str(kind),
            name=str(name),
            status=str(status),
            artifact_hash=stable_hash(spec.payload()) if spec else "",
            metadata=dict(metadata or {}),
            recorded_at=datetime.now(timezone.utc).isoformat(),
        )
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with self.registry_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True, default=str) + "\n")
        return record

    def records(self) -> list[ArtifactRecord]:
        """Read all registry records.

        Parameters
        ----------
        None

        Returns
        -------
        list of ArtifactRecord
            Registry records in file order.
        """

        if not self.registry_path.exists():
            return []
        out: list[ArtifactRecord] = []
        with self.registry_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                out.append(ArtifactRecord(**json.loads(text)))
        return out

    def to_frame(self):
        """Return records as a pandas DataFrame.

        Parameters
        ----------
        None

        Returns
        -------
        pandas.DataFrame
            Registry table.
        """

        import pandas as pd

        return pd.DataFrame([asdict(record) for record in self.records()])

    def missing(self) -> list[ArtifactRecord]:
        """Return registry records whose paths do not exist.

        Parameters
        ----------
        None

        Returns
        -------
        list of ArtifactRecord
            Records for missing files.
        """

        return [record for record in self.records() if not Path(record.artifact_path).expanduser().exists()]
