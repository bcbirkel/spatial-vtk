"""Reusable figure row-provenance sidecar helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import pandas as pd

from spatial_vtk.visualize.figure_io import finish_figure


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


def finish_figure_with_sidecar(
    fig: Any,
    output_path: str | Path | None = None,
    *,
    outpath: str | Path | None = None,
    output_key: str | None = None,
    cfg: Any | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    close: bool | None = None,
    bbox_inches: str = "tight",
    sidecar_df: pd.DataFrame | None = None,
    source_rows: pd.DataFrame | None = None,
    write_sidecar: bool = False,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
    metadata: dict[str, Any] | None = None,
    **savefig_kwargs: Any,
) -> Any:
    """Finish a Matplotlib figure and optionally write row sidecars.

    This is a convenience wrapper for plotting functions that can identify the
    exact rows handed to Matplotlib. Sidecars are written only when the figure
    is saved, because the figure path is used as the stable sidecar basename.
    """

    finished = finish_figure(
        fig,
        output_path,
        outpath=outpath,
        output_key=output_key,
        cfg=cfg,
        showfig=showfig,
        savefig=savefig,
        close=close,
        bbox_inches=bbox_inches,
        **savefig_kwargs,
    )
    saved_path = getattr(finished, "spatial_vtk_saved_path", None)
    if write_sidecar and saved_path is not None and sidecar_df is not None:
        write_figure_row_sidecar(
            saved_path,
            sidecar_df,
            sidecar_rows=sidecar_rows,
            sidecar_dir=sidecar_dir,
            source_rows=source_rows,
            metadata=metadata,
        )
    return finished


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


def layered_figure_rows(layers: list[tuple[str, pd.DataFrame | None]] | tuple[tuple[str, pd.DataFrame | None], ...]) -> pd.DataFrame:
    """Return one sidecar table with a ``_figure_layer`` column.

    Parameters
    ----------
    layers
        Ordered ``(layer_name, rows)`` pairs. ``None`` rows are skipped.

    Returns
    -------
    pandas.DataFrame
        Concatenated rows with one leading ``_figure_layer`` column.
    """

    frames: list[pd.DataFrame] = []
    for layer, frame in layers:
        if frame is None:
            continue
        rows = frame.copy()
        rows.insert(0, "_figure_layer", str(layer))
        frames.append(rows)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


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
    "finish_figure_with_sidecar",
    "layered_figure_rows",
    "sidecar_rows_for_write",
    "write_figure_row_sidecar",
]
