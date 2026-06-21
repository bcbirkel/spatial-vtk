"""Reusable figure row-provenance sidecar helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import json
import math
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

    @property
    def figure_path(self) -> Path:
        """Path to the figure described by this sidecar."""

        return Path(str(self.metadata.get("figure") or self.sidecar_path.with_suffix("")))

    def status_frame(self) -> pd.DataFrame:
        """Return a compact notebook status table for this sidecar result."""

        source_sidecar = self.source_sidecar_path
        return pd.DataFrame(
            [
                {
                    "name": "figure_sidecar_path",
                    "figure_path": str(self.figure_path),
                    "figure_exists": self.figure_path.exists(),
                    "sidecar_path": str(self.sidecar_path),
                    "sidecar_exists": self.sidecar_path.exists(),
                    "metadata_path": str(self.metadata_path),
                    "metadata_exists": self.metadata_path.exists(),
                    "source_sidecar_path": "" if source_sidecar is None else str(source_sidecar),
                    "source_sidecar_exists": False if source_sidecar is None else source_sidecar.exists(),
                    "plot_row_count": self.metadata.get("plot_row_count", ""),
                    "written_row_count": self.metadata.get("written_row_count", ""),
                    "plot_sidecar_exact": self.metadata.get("plot_sidecar_exact", ""),
                    "source_row_count": self.metadata.get("source_row_count", ""),
                    "source_written_row_count": self.metadata.get("source_written_row_count", ""),
                    "source_sidecar_exact": self.metadata.get("source_sidecar_exact", ""),
                    "source_sidecar_written": self.metadata.get("source_sidecar_written", ""),
                    "sidecar_row_policy": self.metadata.get("sidecar_row_policy", ""),
                    "sidecar_row_limit": self.metadata.get("sidecar_row_limit", ""),
                    "plot_rows_role": self.metadata.get("plot_rows_role", ""),
                    "source_rows_role": self.metadata.get("source_rows_role", ""),
                }
            ]
        )


def write_figure_row_sidecar(
    figure_path: str | Path,
    rows: pd.DataFrame,
    *,
    enabled: bool = True,
    sidecar_rows: int | None = None,
    sidecar_dir: str | Path | None = None,
    source_rows: pd.DataFrame | None = None,
    metadata: dict[str, Any] | None = None,
    plot_rows_role: str = "figure_plot_rows",
    source_rows_role: str = "figure_source_rows",
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
    plot_rows_role
        Short label describing what the main sidecar rows represent.
    source_rows_role
        Short label describing what ``source_rows`` represent when provided.
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
    _csv_sidecar_rows(sampled_rows).to_csv(sidecar_path, index=False)
    row_limit = _normalized_sidecar_row_limit(sidecar_rows)

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
            _csv_sidecar_rows(source_sampled_rows).to_csv(source_path, index=False)

    result_metadata: dict[str, Any] = {
        "figure": str(figure),
        "sidecar": str(sidecar_path),
        "plot_row_count": int(len(rows)),
        "plot_column_count": int(len(rows.columns)),
        "plot_columns": [str(column) for column in rows.columns],
        "written_row_count": int(len(sampled_rows)),
        "sampled": bool(sampled),
        "sidecar_row_limit": row_limit,
        "sidecar_row_policy": "all_rows" if row_limit is None else "deterministic_sample",
        "plot_sidecar_exact": not bool(sampled),
        "sidecar_random_state": int(random_state),
        "plot_rows_role": plot_rows_role,
        "source_rows_provided": source_rows is not None,
        "source_sidecar_written": source_path is not None,
    }
    result_metadata.update(figure_sidecar_dimension_counts(rows, prefix="plot"))
    if source_rows is not None:
        result_metadata.update(
            {
                "source_row_count": source_row_count,
                "source_column_count": int(len(source_rows.columns)),
                "source_columns": [str(column) for column in source_rows.columns],
                "source_written_row_count": source_written_count,
                "source_sampled": bool(source_sampled),
                "source_sidecar_exact": not bool(source_sampled),
                "source_rows_role": source_rows_role,
            }
        )
        if source_path is not None:
            result_metadata["source_sidecar"] = str(source_path)
        result_metadata.update(figure_sidecar_dimension_counts(source_rows, prefix="source"))
    else:
        result_metadata["source_row_count"] = int(len(rows))
        result_metadata["source_column_count"] = int(len(rows.columns))
        result_metadata["source_columns"] = [str(column) for column in rows.columns]
        result_metadata["source_written_row_count"] = int(len(sampled_rows))
        result_metadata["source_sampled"] = bool(sampled)
        result_metadata["source_sidecar_exact"] = not bool(sampled)
        result_metadata["source_rows_role"] = plot_rows_role
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
    plot_rows_role: str = "figure_plot_rows",
    source_rows_role: str = "figure_source_rows",
    **savefig_kwargs: Any,
) -> Any:
    """Finish a Matplotlib figure and optionally write row sidecars.

    This is a convenience wrapper for plotting functions that can identify the
    exact rows handed to Matplotlib. Sidecars are written only when the figure
    is saved, because the figure path is used as the stable sidecar basename.
    """

    from spatial_vtk.visualize.figure_io import finish_figure

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
            plot_rows_role=plot_rows_role,
            source_rows_role=source_rows_role,
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


def _normalized_sidecar_row_limit(limit: int | None) -> int | None:
    """Return the positive sidecar row limit, or ``None`` when all rows are written."""

    if limit is None:
        return None
    value = int(limit)
    return value if value > 0 else None


def _csv_sidecar_rows(rows: pd.DataFrame) -> pd.DataFrame:
    """Return rows in a CSV-readable shape for sidecar files."""

    if len(rows.columns) == 0:
        marker = pd.Series([""] * len(rows), dtype="object")
        return pd.DataFrame({"__svtk_empty_sidecar": marker})
    return rows


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


def read_figure_sidecar_metadata(path: str | Path) -> dict[str, Any]:
    """Read one figure sidecar JSON metadata file.

    Parameters
    ----------
    path
        Figure path, main sidecar CSV path, source sidecar CSV path, or JSON
        metadata path. Figure paths resolve through the default ``sidecars``
        directory next to the figure. For custom sidecar directories, pass the
        sidecar CSV or JSON path directly.

    Returns
    -------
    dict
        Parsed sidecar metadata.
    """

    metadata_path = figure_sidecar_metadata_path(path)
    if not metadata_path.exists():
        raise FileNotFoundError(f"Figure sidecar metadata does not exist: {metadata_path}")
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def figure_sidecar_metadata_path(path: str | Path) -> Path:
    """Resolve the JSON metadata path for a figure or sidecar path."""

    source = Path(path).expanduser()
    if source.suffix.lower() == ".json":
        return source
    if source.name.endswith(".source.csv"):
        return source.with_name(source.name.removesuffix(".source.csv") + ".json")
    if source.suffix.lower() == ".csv":
        return source.with_suffix(".json")
    default_sidecar_path = source.parent / "sidecars" / f"{source.stem}.json"
    if default_sidecar_path.exists():
        return default_sidecar_path
    return source.with_suffix(".json")


def figure_sidecar_status_frame(sidecar_dir: str | Path | None) -> pd.DataFrame:
    """Return a compact audit table for all figure sidecar metadata files.

    The returned frame is intended for notebooks: each row is one saved figure
    sidecar and includes exactness flags, plot/source row counts, source-sidecar
    availability, and station-aggregation metadata when present. The helper
    reads only the small JSON sidecars, not the potentially large CSV row
    sidecars. Missing and existing-but-empty directories both return an empty
    frame; use the ``svtk visualize sidecars status`` command when callers need
    the additional ``sidecar_dir_exists`` field for notebook or script status
    checks.
    """

    if sidecar_dir is None:
        return pd.DataFrame(columns=_FIGURE_SIDECAR_STATUS_COLUMNS)

    root = Path(sidecar_dir).expanduser()
    rows: list[dict[str, Any]] = []
    for metadata_path in sorted(root.glob("*.json")):
        metadata = read_figure_sidecar_metadata(metadata_path)
        rows.append(_figure_sidecar_status_row(metadata_path, metadata))
    return pd.DataFrame(rows, columns=_FIGURE_SIDECAR_STATUS_COLUMNS)


def _figure_sidecar_status_row(metadata_path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    """Return one display-ready sidecar audit row."""

    figure = Path(str(metadata.get("figure") or metadata_path.stem))
    return {
        "figure": figure.name,
        "metadata_path": str(metadata_path),
        "sidecar": metadata.get("sidecar", ""),
        "source_sidecar": metadata.get("source_sidecar", ""),
        "plot_row_count": metadata.get("plot_row_count", ""),
        "written_row_count": metadata.get("written_row_count", ""),
        "plot_sidecar_exact": metadata.get("plot_sidecar_exact", ""),
        "source_row_count": metadata.get("source_row_count", ""),
        "source_written_row_count": metadata.get("source_written_row_count", ""),
        "source_sidecar_exact": metadata.get("source_sidecar_exact", ""),
        "source_sidecar_written": metadata.get("source_sidecar_written", ""),
        "sidecar_row_policy": metadata.get("sidecar_row_policy", ""),
        "sidecar_row_limit": metadata.get("sidecar_row_limit", ""),
        "plot_rows_role": metadata.get("plot_rows_role", ""),
        "source_rows_role": metadata.get("source_rows_role", ""),
        "source_rows_filter": metadata.get("source_rows_filter", ""),
        "plot_event_count": metadata.get("plot_event_count", ""),
        "plot_station_count": metadata.get("plot_station_count", ""),
        "plot_component_count": metadata.get("plot_component_count", ""),
        "plot_model_count": metadata.get("plot_model_count", ""),
        "plot_metric_count": metadata.get("plot_metric_count", ""),
        "plot_passband_count": metadata.get("plot_passband_count", ""),
        "plot_period_count": metadata.get("plot_period_count", ""),
        "source_event_count": metadata.get("source_event_count", ""),
        "source_station_count": metadata.get("source_station_count", ""),
        "source_component_count": metadata.get("source_component_count", ""),
        "source_model_count": metadata.get("source_model_count", ""),
        "source_metric_count": metadata.get("source_metric_count", ""),
        "source_passband_count": metadata.get("source_passband_count", ""),
        "source_period_count": metadata.get("source_period_count", ""),
        "aggregation_contract": metadata.get("aggregation_contract", ""),
        "aggregation_kind": metadata.get("aggregation_kind", metadata.get("svtk_aggregation_kind", "")),
        "aggregation_method": metadata.get("aggregation_method", metadata.get("svtk_aggregation_method", "")),
        "aggregation_value_col": metadata.get("aggregation_value_col", metadata.get("svtk_aggregation_value_col", "")),
        "aggregation_panel_count": metadata.get("aggregation_panel_count", metadata.get("svtk_aggregation_panel_count", "")),
        "aggregation_group_columns": metadata.get("aggregation_group_columns", metadata.get("svtk_aggregation_group_columns", "")),
        "aggregation_coordinate_columns": metadata.get(
            "aggregation_coordinate_columns",
            metadata.get("svtk_aggregation_coordinate_columns", ""),
        ),
        "aggregation_collapsed_columns": metadata.get(
            "aggregation_collapsed_columns",
            metadata.get("svtk_aggregation_collapsed_columns", ""),
        ),
        "aggregation_collapsed_unique_counts": metadata.get(
            "aggregation_collapsed_unique_counts",
            metadata.get("svtk_aggregation_collapsed_unique_counts", ""),
        ),
        "aggregation_input_row_count": metadata.get("aggregation_input_row_count", metadata.get("svtk_aggregation_input_row_count", "")),
        "aggregation_finite_row_count": metadata.get("aggregation_finite_row_count", metadata.get("svtk_aggregation_finite_row_count", "")),
        "aggregation_dropped_nonfinite_row_count": metadata.get(
            "aggregation_dropped_nonfinite_row_count",
            metadata.get("svtk_aggregation_dropped_nonfinite_row_count", ""),
        ),
        "aggregation_input_station_count": metadata.get(
            "aggregation_input_station_count",
            metadata.get("svtk_aggregation_input_station_count", ""),
        ),
        "aggregation_finite_station_count": metadata.get(
            "aggregation_finite_station_count",
            metadata.get("svtk_aggregation_finite_station_count", ""),
        ),
        "aggregation_input_event_count": metadata.get(
            "aggregation_input_event_count",
            metadata.get("svtk_aggregation_input_event_count", ""),
        ),
        "aggregation_finite_event_count": metadata.get(
            "aggregation_finite_event_count",
            metadata.get("svtk_aggregation_finite_event_count", ""),
        ),
    }


_FIGURE_SIDECAR_STATUS_COLUMNS = list(
    _figure_sidecar_status_row(
        Path("figure_sidecar.json"),
        {
            "figure": "",
        },
    ).keys()
)


def figure_sidecar_dimension_counts(df: pd.DataFrame | None, *, prefix: str) -> dict[str, int]:
    """Return cheap dimension counts for figure sidecar metadata."""

    if df is None:
        return {}
    keys = {
        "event": ("event_id", "event", "event_title"),
        "station": ("station", "station_id", "station_code"),
        "component": ("component", "channel_component"),
        "model": ("model", "model_name"),
        "metric": ("metric", "metric_name"),
        "passband": ("band", "passband", "period_band"),
        "period": ("period_s", "period"),
    }
    counts: dict[str, int] = {}
    for label, candidates in keys.items():
        column = next((candidate for candidate in candidates if candidate in df.columns), None)
        if column is not None:
            counts[f"{prefix}_{label}_count"] = int(df[column].nunique(dropna=True))
    return counts


def _json_ready(value: Any) -> Any:
    """Return a JSON-serializable representation for common metadata values."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, set):
        return [_json_ready(item) for item in sorted(value, key=str)]
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if hasattr(value, "tolist"):
        try:
            return _json_ready(value.tolist())
        except Exception:
            pass
    if hasattr(value, "item"):
        try:
            return _json_ready(value.item())
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return str(value)


__all__ = [
    "FigureSidecarResult",
    "figure_sidecar_dimension_counts",
    "figure_sidecar_metadata_path",
    "figure_sidecar_status_frame",
    "finish_figure_with_sidecar",
    "layered_figure_rows",
    "read_figure_sidecar_metadata",
    "sidecar_rows_for_write",
    "write_figure_row_sidecar",
]
