"""Metric waveform inventory builders.

Purpose
-------
This module converts preprocessing trace metadata into the observed and
synthetic waveform inventories consumed by the metric workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from spatial_vtk.io.metric_inputs import normalize_metric_waveform_inventory


TRACE_METADATA_COLUMNS = (
    "source",
    "source_type",
    "event_id",
    "station",
    "component",
    "input_file",
    "output_file",
    "delta",
    "dt",
    "sampling_rate",
    "starttime",
    "endtime",
)


@dataclass(frozen=True)
class MetricWaveformInventoryResult:
    """Paths and row counts written by the inventory builder."""

    observed_path: Path
    synthetic_path: Path
    observed_rows: int | None
    synthetic_rows: int | None
    reused: bool = False

    @property
    def observed_metric_inventory_path(self) -> Path:
        """Path to the observed metric waveform inventory table."""

        return self.observed_path

    @property
    def synthetic_metric_inventory_path(self) -> Path:
        """Path to the synthetic metric waveform inventory table."""

        return self.synthetic_path

    def status_frame(self) -> pd.DataFrame:
        """Return a compact summary of metric inventory outputs."""

        rows = [
            {
                "name": "observed_metric_inventory_path",
                "artifact": "observed_metric_inventory",
                "artifact_label": "observed metric waveform inventory",
                "artifact_role": "metric_inventory",
                "status": "ready" if self.observed_metric_inventory_path.exists() else "missing",
                "resolved_path": str(self.observed_metric_inventory_path),
                "path": str(self.observed_metric_inventory_path),
                "exists": self.observed_metric_inventory_path.exists(),
                "rows": self.observed_rows,
                "reused": self.reused,
            },
            {
                "name": "synthetic_metric_inventory_path",
                "artifact": "synthetic_metric_inventory",
                "artifact_label": "synthetic metric waveform inventory",
                "artifact_role": "metric_inventory",
                "status": "ready" if self.synthetic_metric_inventory_path.exists() else "missing",
                "resolved_path": str(self.synthetic_metric_inventory_path),
                "path": str(self.synthetic_metric_inventory_path),
                "exists": self.synthetic_metric_inventory_path.exists(),
                "rows": self.synthetic_rows,
                "reused": self.reused,
            },
        ]
        return pd.DataFrame(rows)


def build_metric_waveform_inventories_from_trace_metadata(
    trace_metadata: pd.DataFrame | str | Path,
    observed_output: str | Path,
    synthetic_output: str | Path,
    *,
    config: Any | None = None,
    synthetic_model: str | None = None,
    observed_path_column: str = "output_file",
    synthetic_path_column: str = "input_file",
    overwrite: bool = True,
    verbose: bool = False,
) -> MetricWaveformInventoryResult:
    """Build observed and synthetic metric inventories from trace metadata.

    Parameters
    ----------
    trace_metadata
        Preprocessing trace metadata table or path.
    observed_output, synthetic_output
        Destination inventory tables. The extension controls CSV vs Parquet.
    config
        Optional run config used to infer a single synthetic model name from
        ``metrics.models`` when ``synthetic_model`` is not supplied.
    synthetic_model
        Model label assigned to synthetic inventory rows.
    observed_path_column
        Trace-metadata column used as observed ``waveform_path``. The default
        uses processed observed waveforms.
    synthetic_path_column
        Trace-metadata column used as synthetic ``waveform_path``. The default
        uses original synthetic input files.
    overwrite
        Whether to replace existing inventory outputs.
    verbose
        Whether to print row counts and output paths.

    Returns
    -------
    MetricWaveformInventoryResult
        Output paths and row counts. Row counts are ``None`` when both outputs
        already existed and ``overwrite`` was false.
    """

    observed_path = Path(observed_output).expanduser()
    synthetic_path = Path(synthetic_output).expanduser()
    if observed_path.exists() and synthetic_path.exists() and not overwrite:
        if verbose:
            print(f"Metric inventories already exist: {observed_path}, {synthetic_path}", flush=True)
        return MetricWaveformInventoryResult(
            observed_path=observed_path,
            synthetic_path=synthetic_path,
            observed_rows=None,
            synthetic_rows=None,
            reused=True,
        )

    metadata = _read_trace_metadata(trace_metadata)
    model = _resolve_synthetic_model(config, synthetic_model)
    observed, synthetic = _metric_inventories_from_trace_metadata_frame(
        metadata,
        synthetic_model=model,
        observed_path_column=observed_path_column,
        synthetic_path_column=synthetic_path_column,
    )
    _write_table(observed, observed_path)
    _write_table(synthetic, synthetic_path)
    if verbose:
        print(f"Wrote observed metric inventory: {observed_path} ({len(observed)} row(s))", flush=True)
        print(f"Wrote synthetic metric inventory: {synthetic_path} ({len(synthetic)} row(s))", flush=True)
    return MetricWaveformInventoryResult(
        observed_path=observed_path,
        synthetic_path=synthetic_path,
        observed_rows=len(observed),
        synthetic_rows=len(synthetic),
        reused=False,
    )


def _metric_inventories_from_trace_metadata_frame(
    metadata: pd.DataFrame,
    *,
    synthetic_model: str = "",
    observed_path_column: str = "output_file",
    synthetic_path_column: str = "input_file",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return normalized observed/synthetic inventories from metadata."""

    df = metadata.copy()
    if "source_type" in df.columns and "source" not in df.columns:
        df = df.rename(columns={"source_type": "source"})
    if "delta" in df.columns and "dt" not in df.columns:
        df = df.rename(columns={"delta": "dt"})
    _require_columns(df, ["source", "event_id", "station", "component"], table_name="trace metadata")
    _require_columns(df, [observed_path_column], table_name="trace metadata")
    _require_columns(df, [synthetic_path_column], table_name="trace metadata")

    df["source"] = df["source"].astype(str).str.strip().str.lower()
    df["model"] = ""
    if synthetic_model:
        df.loc[df["source"].eq("synthetic"), "model"] = str(synthetic_model)
    df["waveform_path"] = ""
    observed_mask = df["source"].eq("observed")
    synthetic_mask = df["source"].eq("synthetic")
    df.loc[observed_mask, "waveform_path"] = df.loc[observed_mask, observed_path_column]
    df.loc[synthetic_mask, "waveform_path"] = df.loc[synthetic_mask, synthetic_path_column]

    keep = [
        "source",
        "event_id",
        "station",
        "component",
        "model",
        "waveform_path",
        "dt",
        "sampling_rate",
        "starttime",
        "endtime",
    ]
    present = [column for column in keep if column in df.columns]
    inventory = df.loc[observed_mask | synthetic_mask, present].drop_duplicates()
    observed = normalize_metric_waveform_inventory(
        inventory.loc[inventory["source"].eq("observed")].copy(),
        source="observed",
    )
    synthetic = normalize_metric_waveform_inventory(
        inventory.loc[inventory["source"].eq("synthetic")].copy(),
        source="synthetic",
    )
    return observed, synthetic


def _read_trace_metadata(table: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Read only trace-metadata columns needed for metric inventories."""

    if isinstance(table, pd.DataFrame):
        return table.copy()
    path = Path(table).expanduser()
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        try:
            return pd.read_parquet(path, columns=list(TRACE_METADATA_COLUMNS))
        except Exception:
            return _read_table(path)
    requested = set(TRACE_METADATA_COLUMNS)
    return pd.read_csv(path, usecols=lambda column: column in requested, low_memory=False)


def _resolve_synthetic_model(config: Any | None, synthetic_model: str | None) -> str:
    """Return explicit or config-derived synthetic model label."""

    if synthetic_model is not None:
        return str(synthetic_model)
    if config is None:
        return ""
    models = config.section("metrics.models", []) or []
    if len(models) == 1:
        return str(models[0])
    return ""


def _read_table(*args: Any, **kwargs: Any) -> pd.DataFrame:
    """Read a CSV or Parquet table only when inventory inputs need fallback I/O."""

    from spatial_vtk.io.tables import read_table

    return read_table(*args, **kwargs)


def _write_table(*args: Any, **kwargs: Any) -> Path:
    """Write a CSV or Parquet table only when inventory outputs are produced."""

    from spatial_vtk.io.tables import write_table

    return write_table(*args, **kwargs)


def _require_columns(df: pd.DataFrame, columns: list[str], *, table_name: str) -> None:
    """Raise a clear error when required columns are absent."""

    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise KeyError(f"Missing required {table_name} column(s): {missing}")


__all__ = [
    "MetricWaveformInventoryResult",
    "build_metric_waveform_inventories_from_trace_metadata",
]
