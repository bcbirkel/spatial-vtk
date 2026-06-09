"""Workflow plan objects read from public Spatial-VTK configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
import argparse
import re

import pandas as pd

from spatial_vtk.config.metric_catalog import metric_group_for
from spatial_vtk.config.metrics import metrics_settings_from_config, transform_columns
from spatial_vtk.config.runtime import SpatialVTKConfig


@dataclass(frozen=True)
class MetricPlan:
    """Resolved metric-calculation plan.

    Parameters
    ----------
    metrics
        Metric names/codes to calculate.
    passbands
        Period passbands as ``(period_min_s, period_max_s)`` pairs.
    components
        Waveform components to process.
    models
        Synthetic model aliases or names.
    output_path
        Optional output path for the metric table.

    Returns
    -------
    MetricPlan
        Immutable metric-calculation plan.
    """

    metrics: tuple[str, ...]
    passbands: tuple[tuple[float, float], ...]
    components: tuple[str, ...]
    models: tuple[str, ...]
    metric_groups: tuple[str, ...] = ()
    transforms: tuple[str, ...] = ()
    spectral_periods_s: tuple[float, ...] = ()
    output_mode: str = "full"
    synthetic_max_frequency_hz: float | None = None
    waveform_lowpass_hz: float | None = None
    waveform_resample_hz: float | None = None
    waveform_filter_order: int | None = None
    output_path: Path | None = None

    @property
    def transform_columns(self) -> tuple[str, ...]:
        """Return requested transform output columns."""

        return transform_columns(self.transforms)


@dataclass(frozen=True)
class MetricCompleteness:
    """Summary of expected, present, and missing metric rows."""

    expected: int
    present: int
    missing: int
    key_columns: tuple[str, ...]


def metric_plan_from_config(
    config: SpatialVTKConfig,
    *,
    command: str = "metrics.calculate",
    overrides: dict[str, Any] | None = None,
) -> MetricPlan:
    """Build a metric plan from public config sections and run defaults.

    Parameters
    ----------
    config
        Loaded Spatial-VTK config.
    command
        Dotted command key used to merge run defaults.
    overrides
        Explicit values for this run. These override the config file and any
        selected run scenario.

    Returns
    -------
    MetricPlan
        Resolved metric plan.
    """

    settings = metrics_settings_from_config(config, command=command, overrides=overrides)
    metric_cfg = dict(config.section("metrics", {}) or {})
    defaults = config.run_defaults(command)
    merged: dict[str, Any] = {**metric_cfg, **defaults}
    merged = {**merged, **dict(overrides or {})}
    metrics = settings.metrics
    passbands = _parse_passbands(merged.get("passbands") or merged.get("period_bands") or ())
    components = _as_tuple(merged.get("components") or ("Z",))
    models = _as_tuple(merged.get("models") or ())
    output_value = merged.get("output_path") or merged.get("output_metrics") or config.section("outputs.metrics")
    output_path = None
    if output_value:
        output_path = config.path("outputs.metrics") if output_value == config.section("outputs.metrics") else config.path_from_value(output_value)
    waveform_cfg = dict(config.section("waveforms.preprocessing", {}) or {})
    return MetricPlan(
        metrics=metrics,
        passbands=passbands,
        components=components,
        models=models,
        metric_groups=settings.groups,
        transforms=settings.transforms,
        spectral_periods_s=settings.spectral.periods_s,
        output_mode=settings.output_mode,
        synthetic_max_frequency_hz=settings.synthetic_max_frequency_hz,
        waveform_lowpass_hz=_optional_float(waveform_cfg.get("lowpass_hz")),
        waveform_resample_hz=_optional_float(waveform_cfg.get("resample_hz") or waveform_cfg.get("target_sampling_rate_hz")),
        waveform_filter_order=_optional_int(waveform_cfg.get("filter_order")),
        output_path=output_path,
    )


def expected_metric_rows_from_inventory(
    inventory_df: pd.DataFrame,
    plan: MetricPlan,
    *,
    model_column: str = "model",
) -> pd.DataFrame:
    """Build expected metric row keys from an inventory table and plan.

    Parameters
    ----------
    inventory_df
        QC inventory with ``event_id``, ``station``, and ``component`` fields.
    plan
        Resolved metric plan.
    model_column
        Output column used for model identity.

    Returns
    -------
    pandas.DataFrame
        Expected row-key table.
    """

    required = {"event_id", "station", "component"}
    missing = sorted(required - set(inventory_df.columns))
    if missing:
        raise ValueError(f"Inventory is missing required metric-planning columns: {missing}")
    rows: list[dict[str, Any]] = []
    models = plan.models or ("",)
    passbands = plan.passbands or (("", ""),)
    metric_names = plan.metrics or ("",)
    metric_groups = plan.metric_groups or ("",)
    transform_cols = transform_columns(plan.transforms)
    base = inventory_df.loc[:, ["event_id", "station", "component"]].drop_duplicates()
    for _, item in base.iterrows():
        for model in models:
            for passband in passbands:
                pmin, pmax = passband
                passband_label = f"{_format_period_token(pmin)}-{_format_period_token(pmax)}s" if pmin != "" and pmax != "" else ""
                for metric in metric_names:
                    metric_group = metric_group_for(metric) or (metric_groups[0] if metric_groups else "")
                    period_values: tuple[float | None, ...] = (None,)
                    if str(metric).upper() in {"PSA", "FAS"} and plan.spectral_periods_s:
                        period_values = tuple(float(period) for period in plan.spectral_periods_s)
                    for period in period_values:
                        payload = {
                            "event_id": str(item["event_id"]),
                            "station": str(item["station"]).upper(),
                            "component": str(item["component"]).upper(),
                            model_column: str(model),
                            "passband": passband_label,
                            "metric_group": str(metric_group),
                            "metric": str(metric),
                            "period_s": period,
                            "output_mode": plan.output_mode,
                            "requested_transforms": ",".join(plan.transforms),
                        }
                        for column in transform_cols:
                            payload[column] = pd.NA
                        rows.append(payload)
    return pd.DataFrame(rows)


def compare_metric_plan_to_table(
    expected_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    *,
    key_columns: Sequence[str] = ("event_id", "station", "component", "model", "passband", "metric_group", "metric", "period_s"),
) -> tuple[pd.DataFrame, MetricCompleteness]:
    """Compare expected metric rows to an existing metrics table.

    Parameters
    ----------
    expected_df
        Expected key table.
    metrics_df
        Existing metrics table.
    key_columns
        Columns used for comparison.

    Returns
    -------
    tuple
        Missing-row table and completeness summary.
    """

    keys = tuple(str(column) for column in key_columns if column in expected_df.columns)
    if not keys:
        raise ValueError("No key columns are shared with the expected metric table.")
    missing_in_metrics = [column for column in keys if column not in metrics_df.columns]
    if missing_in_metrics:
        raise ValueError(f"Metrics table is missing key columns required for comparison: {missing_in_metrics}")
    expected_keys = _normalized_key_frame(expected_df, keys).drop_duplicates()
    present_keys = _normalized_key_frame(metrics_df, keys).drop_duplicates()
    merged = expected_keys.merge(present_keys.assign(_present=True), on=list(keys), how="left")
    missing = merged[merged["_present"].isna()].drop(columns=["_present"]).reset_index(drop=True)
    summary = MetricCompleteness(
        expected=len(expected_keys),
        present=len(expected_keys) - len(missing),
        missing=len(missing),
        key_columns=keys,
    )
    return missing, summary


def _as_tuple(value: object) -> tuple[str, ...]:
    """Normalize a scalar or sequence to a tuple of strings."""

    if value in (None, ""):
        return ()
    if isinstance(value, str):
        return tuple(part for part in re.split(r"[\s,]+", value.strip()) if part)
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value if item not in (None, ""))
    return (str(value),)


def _normalized_key_frame(df: pd.DataFrame, keys: Sequence[str]) -> pd.DataFrame:
    """Normalize comparable metric key columns."""

    out = df.loc[:, list(keys)].copy()
    for column in out.columns:
        out[column] = out[column].astype(str).str.strip()
    for column in ("station", "component"):
        if column in out.columns:
            out[column] = out[column].str.upper()
    return out


def _format_period_token(value: object) -> str:
    """Format one period value for a compact passband label."""

    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:g}"


def _parse_passbands(value: object) -> tuple[tuple[float, float], ...]:
    """Parse config passbands into period-min/period-max pairs."""

    if value in (None, ""):
        return ()
    items = value if isinstance(value, (list, tuple)) else [value]
    bands: list[tuple[float, float]] = []
    for item in items:
        if isinstance(item, str):
            text = item.strip()
            match = re.fullmatch(r"\s*([0-9]*\.?[0-9]+)\s*[-:]\s*([0-9]*\.?[0-9]+)\s*", text)
            if not match:
                raise ValueError(f"Could not parse passband string: {item!r}")
            bands.append((float(match.group(1)), float(match.group(2))))
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            bands.append((float(item[0]), float(item[1])))
        else:
            raise ValueError(f"Passbands must be strings like '1-2' or two-number pairs, got {item!r}.")
    return tuple(bands)


def _optional_float(value: object) -> float | None:
    """Return a finite float or None for empty/unset values."""

    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if pd.notna(number) else None


def _optional_int(value: object) -> int | None:
    """Return an integer or None for empty/unset values."""

    number = _optional_float(value)
    return int(number) if number is not None else None


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the module-level metric-plan CLI parser."""

    parser = argparse.ArgumentParser(description="Check expected metric rows against an existing metrics table.")
    parser.add_argument("--inventory", required=True, help="QC inventory CSV.")
    parser.add_argument("--metrics", required=True, help="Existing metrics CSV.")
    parser.add_argument("--config", default=None, help="Spatial-VTK config YAML/JSON.")
    parser.add_argument("--missing-output", default=None, help="Optional output CSV for missing rows.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the metric completeness CLI wrapper."""

    args = build_arg_parser().parse_args(argv)
    config = SpatialVTKConfig.from_file(args.config) if args.config else SpatialVTKConfig.empty(root_dir=Path.cwd())
    plan = metric_plan_from_config(config)
    expected = expected_metric_rows_from_inventory(pd.read_csv(args.inventory), plan)
    missing, summary = compare_metric_plan_to_table(expected, pd.read_csv(args.metrics))
    if args.missing_output:
        output = Path(args.missing_output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        missing.to_csv(output, index=False)
    print(f"expected={summary.expected} present={summary.present} missing={summary.missing}")
    return 0 if summary.missing == 0 else 1
