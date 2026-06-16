"""Reusable figure row-provenance sidecar helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class FigureSidecarResult:
    """Paths and metadata written for one figure sidecar."""

    sidecar_path: Path
    metadata_path: Path
    source_sidecar_path: Path | None
    metadata: dict[str, Any]


def write_figure_row_sidecar(
    figure_path: str | Path,
    rows: pd.DataFrame,
    *,
    enabled: bool = True,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
    source_rows: pd.DataFrame | None = None,
    metadata: dict[str, Any] | None = None,
    write_source_sidecar: bool = True,
    random_state: int = 42,
) -> FigureSidecarResult | None:
    """Write CSV and JSON sidecars describing rows used by one figure.

    Parameters
    ----------
    figure_path
        Figure file whose stem should be reused for sidecar filenames.
    rows
        Exact rows handed to the plotting function.
    enabled
        Whether sidecar writing is enabled.
    sidecar_rows
        Maximum rows to write. ``None`` or values less than one write all rows.
    sidecar_dir
        Optional output directory. When omitted, sidecars are written under a
        ``sidecars`` directory next to the figure.
    source_rows
        Optional pre-aggregation rows used to produce ``rows``.
    metadata
        Additional metadata merged into the JSON sidecar. Values here override
        default keys when keys overlap.
    write_source_sidecar
        Whether to write ``*.source.csv`` when ``source_rows`` is provided.
    random_state
        Random seed for deterministic row sampling.

    Returns
    -------
    FigureSidecarResult or None
        Written sidecar paths and JSON metadata, or ``None`` when disabled.
    """

    if not enabled:
        return None

    figure = Path(figure_path)
    output_dir = Path(sidecar_dir).expanduser() if sidecar_dir is not None else figure.parent / "sidecars"
    output_dir.mkdir(parents=True, exist_ok=True)

    sidecar_path = output_dir / f"{figure.stem}.csv"
    sampled_rows, sampled = sidecar_rows_for_write(rows, limit=sidecar_rows, random_state=random_state)
    sampled_rows.to_csv(sidecar_path, index=False)

    source_path = None
    source_sampled = False
    source_written_count = None
    source_row_count = None
    if source_rows is not None:
        source_row_count = int(len(source_rows))
        source_sampled_rows, source_sampled = sidecar_rows_for_write(
            source_rows,
            limit=sidecar_rows,
            random_state=random_state,
        )
        source_written_count = int(len(source_sampled_rows))
        if write_source_sidecar:
            source_path = output_dir / f"{figure.stem}.source.csv"
            source_sampled_rows.to_csv(source_path, index=False)

    result_metadata: dict[str, Any] = {
        "figure": str(figure),
        "sidecar": str(sidecar_path),
        "plot_row_count": int(len(rows)),
        "written_row_count": int(len(sampled_rows)),
        "sampled": bool(sampled),
    }
    result_metadata.update(figure_sidecar_dimension_counts(rows, prefix="plot"))
    if source_rows is not None:
        result_metadata.update(
            {
                "source_row_count": source_row_count,
                "source_written_row_count": source_written_count,
                "source_sampled": bool(source_sampled),
            }
        )
        if source_path is not None:
            result_metadata["source_sidecar"] = str(source_path)
        result_metadata.update(figure_sidecar_dimension_counts(source_rows, prefix="source"))
    else:
        result_metadata["source_row_count"] = int(len(rows))
        result_metadata.update(figure_sidecar_dimension_counts(rows, prefix="source"))
    if metadata:
        result_metadata.update(metadata)

    metadata_path = sidecar_path.with_suffix(".json")
    metadata_path.write_text(json.dumps(_json_ready(result_metadata), indent=2, sort_keys=True), encoding="utf-8")
    return FigureSidecarResult(sidecar_path, metadata_path, source_path, result_metadata)


def sidecar_rows_for_write(
    rows: pd.DataFrame,
    *,
    limit: int | None,
    random_state: int = 42,
) -> tuple[pd.DataFrame, bool]:
    """Return sidecar rows and whether deterministic sampling was applied."""

    if limit is not None and limit > 0 and len(rows) > limit:
        return rows.sample(n=int(limit), random_state=random_state).copy(), True
    return rows.copy(), False


def figure_sidecar_dimension_counts(df: pd.DataFrame | None, *, prefix: str) -> dict[str, int]:
    """Return cheap dimension counts for figure sidecar metadata."""

    if df is None:
        return {}
    keys = {
        "event": "event_id",
        "station": "station",
        "component": "component",
        "model": "model",
        "metric": "metric",
        "passband": "band",
        "period": "period_s",
    }
    counts: dict[str, int] = {}
    for label, column in keys.items():
        if column in df.columns:
            counts[f"{prefix}_{label}_count"] = int(df[column].nunique(dropna=True))
    return counts


def _json_ready(value: Any) -> Any:
    """Return a JSON-serializable representation for common metadata values."""

    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


__all__ = [
    "FigureSidecarResult",
    "figure_sidecar_dimension_counts",
    "sidecar_rows_for_write",
    "write_figure_row_sidecar",
]
