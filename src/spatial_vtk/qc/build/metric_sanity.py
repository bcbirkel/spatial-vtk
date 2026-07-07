"""Post-metric QC gates for absolute values and residual outliers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd


G_M_PER_S2 = 9.80665
G_CM_PER_S2 = 980.665
QC_SOURCES = ("observed", "synthetic")


@dataclass(frozen=True)
class MetricValueLimit:
    """Absolute-value sanity limit for one metric."""

    metric: str
    max_abs: float
    sources: tuple[str, ...] = QC_SOURCES
    reason: str = "metric_value_above_sanity_limit"


@dataclass(frozen=True)
class MetricResidualLimit:
    """Absolute residual sanity limit."""

    column: str = "log2_residual"
    max_abs: float | None = None
    reason: str = "metric_residual_above_sanity_limit"


@dataclass(frozen=True)
class SpatialResidualOutlierSettings:
    """Nearby-station residual outlier settings."""

    enabled: bool = False
    column: str = "log2_residual"
    radius_km: float = 10.0
    min_neighbors: int = 3
    z_threshold: float = 8.0
    min_abs_difference: float = 4.0
    mad_floor: float = 0.25
    reason: str = "metric_residual_spatial_outlier"


@dataclass(frozen=True)
class MetricSanityQCSettings:
    """Combined post-metric sanity QC settings."""

    value_limits: tuple[MetricValueLimit, ...] = ()
    residual_limit: MetricResidualLimit = field(default_factory=MetricResidualLimit)
    spatial_residual: SpatialResidualOutlierSettings = field(default_factory=SpatialResidualOutlierSettings)


def metric_sanity_settings_from_config(cfg: Any | None) -> MetricSanityQCSettings:
    """Return post-metric QC settings from ``qc.automatic`` config values."""

    if cfg is None:
        return MetricSanityQCSettings()
    section = dict(cfg.section("qc.automatic", {}) or {})
    post_metric = dict(section.get("post_metric", {}) or section.get("metric_sanity", {}) or {})
    value_limits = _parse_value_limits(post_metric.get("value_limits") or section.get("metric_value_limits") or {})
    residual_limit = _parse_residual_limit(post_metric.get("residual_limit") or section.get("metric_residual_limit") or {})
    spatial = _parse_spatial_settings(post_metric.get("spatial_residual") or section.get("spatial_residual_outliers") or {})
    return MetricSanityQCSettings(
        value_limits=tuple(value_limits),
        residual_limit=residual_limit,
        spatial_residual=spatial,
    )


def build_metric_sanity_rejection_table(
    metrics: pd.DataFrame | str | Path,
    *,
    settings: MetricSanityQCSettings | None = None,
    value_limits: Sequence[MetricValueLimit] | None = None,
    residual_limit: MetricResidualLimit | None = None,
    spatial_residual: SpatialResidualOutlierSettings | None = None,
) -> pd.DataFrame:
    """Build side-specific QC rejection rows from computed metric values.

    Absolute observed/synthetic value limits reject only the offending side.
    Residual and spatial-neighbor outliers reject the comparison pair by
    emitting both observed and synthetic side rows.
    """

    frame = _read_table(metrics)
    effective = settings or MetricSanityQCSettings()
    limits = tuple(value_limits) if value_limits is not None else effective.value_limits
    residual = residual_limit if residual_limit is not None else effective.residual_limit
    spatial = spatial_residual if spatial_residual is not None else effective.spatial_residual

    rows: list[dict[str, object]] = []
    rows.extend(_value_limit_rejections(frame, limits))
    if residual.max_abs is not None:
        rows.extend(_residual_limit_rejections(frame, residual))
    if spatial.enabled:
        rows.extend(_spatial_residual_rejections(frame, spatial))
    if not rows:
        return _empty_rejection_table()
    out = pd.DataFrame(rows)
    out = out.drop_duplicates(
        ["source", "event_id", "station", "component", "passband", "metric", "period_key", "qc_reason"],
        keep="first",
    )
    return out.reset_index(drop=True)


def apply_metric_sanity_rejections_to_qc_inventory(
    qc_inventory: pd.DataFrame | str | Path,
    rejections: pd.DataFrame | str | Path,
    output_path: str | Path | None = None,
) -> pd.DataFrame | Path:
    """Apply post-metric rejections to a side-specific QC inventory."""

    qc = _read_table(qc_inventory)
    reject = _read_table(rejections)
    if reject.empty:
        if output_path is not None:
            return _write_table(qc, output_path)
        return qc
    required = ["source", "event_id", "station", "component", "passband", "metric", "period_s"]
    missing = [column for column in required if column not in qc.columns]
    if missing:
        raise KeyError(f"QC inventory is missing required columns: {missing}")
    reject = _normalize_rejection_keys(reject)
    work = _normalize_qc_keys(qc)
    grouped = (
        reject.groupby(["source_key", "event_id_key", "station_key", "component_key", "passband_key", "metric_key", "period_key"])
        .agg(metric_sanity_qc_reason=("qc_reason", _join_reasons))
        .reset_index()
    )
    merged = work.merge(
        grouped,
        on=["source_key", "event_id_key", "station_key", "component_key", "passband_key", "metric_key", "period_key"],
        how="left",
    )
    hit = merged["metric_sanity_qc_reason"].fillna("").astype(str).str.len().gt(0)
    merged.loc[hit, "qc_status"] = "fail"
    merged.loc[hit, "qc_reason"] = [
        _append_reason(existing, new)
        for existing, new in zip(merged.loc[hit, "qc_reason"], merged.loc[hit, "metric_sanity_qc_reason"])
    ]
    helper_cols = [
        "source_key",
        "event_id_key",
        "station_key",
        "component_key",
        "passband_key",
        "metric_key",
        "period_key",
        "metric_sanity_qc_reason",
    ]
    out = merged.drop(columns=[column for column in helper_cols if column in merged.columns])
    if output_path is not None:
        return _write_table(out, output_path)
    return out


def apply_metric_sanity_rejections_to_metric_table(
    metrics: pd.DataFrame,
    rejections: pd.DataFrame | str | Path,
) -> pd.DataFrame:
    """Apply side-specific sanity rejections to an enriched metric table."""

    reject = _read_table(rejections)
    if reject.empty:
        return metrics.copy()
    out = metrics.copy()
    reject = _normalize_rejection_keys(reject)
    work = _normalize_metric_keys(out)
    grouped = (
        reject.groupby(["event_id_key", "station_key", "component_key", "passband_key", "metric_key", "period_key"])
        .agg(
            observed_reason=("qc_reason", lambda values: _join_reasons(_source_reason_values(reject, values.index, "observed"))),
            synthetic_reason=("qc_reason", lambda values: _join_reasons(_source_reason_values(reject, values.index, "synthetic"))),
        )
        .reset_index()
    )
    merged = work.merge(
        grouped,
        on=["event_id_key", "station_key", "component_key", "passband_key", "metric_key", "period_key"],
        how="left",
    )
    obs_hit = merged["observed_reason"].fillna("").astype(str).str.len().gt(0)
    syn_hit = merged["synthetic_reason"].fillna("").astype(str).str.len().gt(0)
    if "obs_qc_status" in merged.columns:
        merged.loc[obs_hit, "obs_qc_status"] = "fail"
    if "obs_qc_reason" in merged.columns:
        merged.loc[obs_hit, "obs_qc_reason"] = [
            _append_reason(existing, new) for existing, new in zip(merged.loc[obs_hit, "obs_qc_reason"], merged.loc[obs_hit, "observed_reason"])
        ]
    if "syn_qc_status" in merged.columns:
        merged.loc[syn_hit, "syn_qc_status"] = "fail"
    if "syn_qc_reason" in merged.columns:
        merged.loc[syn_hit, "syn_qc_reason"] = [
            _append_reason(existing, new) for existing, new in zip(merged.loc[syn_hit, "syn_qc_reason"], merged.loc[syn_hit, "synthetic_reason"])
        ]
    comparison_hit = obs_hit | syn_hit
    if "comparison_qc_status" in merged.columns:
        merged.loc[comparison_hit, "comparison_qc_status"] = "fail"
    if "comparison_qc_reason" in merged.columns:
        merged.loc[comparison_hit, "comparison_qc_reason"] = [
            _append_reason(existing, "metric_sanity_qc_failed")
            for existing in merged.loc[comparison_hit, "comparison_qc_reason"]
        ]
    for column in ["value_obs"]:
        if column in merged.columns:
            merged.loc[obs_hit, column] = np.nan
    for column in ["value_syn"]:
        if column in merged.columns:
            merged.loc[syn_hit, column] = np.nan
    for column in ["value", "residual", "log2_residual", "ln_residual", "anderson_2004_gof", "olsen_mayhew_gof", "score"]:
        if column in merged.columns:
            merged.loc[comparison_hit, column] = np.nan
    helper_cols = [
        "event_id_key",
        "station_key",
        "component_key",
        "passband_key",
        "metric_key",
        "period_key",
        "observed_reason",
        "synthetic_reason",
    ]
    return merged.drop(columns=[column for column in helper_cols if column in merged.columns])


def summarize_metric_sanity_removals(
    current_qc: pd.DataFrame | str | Path,
    updated_qc: pd.DataFrame | str | Path,
) -> pd.DataFrame:
    """Summarize newly failed QC rows relative to an existing QC inventory."""

    before = _normalize_qc_keys(_read_table(current_qc))
    after = _normalize_qc_keys(_read_table(updated_qc))
    keys = ["source_key", "event_id_key", "station_key", "component_key", "passband_key", "metric_key", "period_key"]
    status_cols = [*keys, "qc_status", "qc_reason"]
    merged = before[status_cols].merge(
        after[status_cols],
        on=keys,
        how="inner",
        suffixes=("_before", "_after"),
    )
    before_pass = merged["qc_status_before"].fillna("").astype(str).str.lower().eq("pass")
    after_fail = merged["qc_status_after"].fillna("").astype(str).str.lower().eq("fail")
    removed = merged.loc[before_pass & after_fail].copy()
    if removed.empty:
        return pd.DataFrame(columns=["qc_reason_after", "source", "metric", "passband", "newly_failed_rows"])
    removed = removed.rename(
        columns={
            "source_key": "source",
            "metric_key": "metric",
            "passband_key": "passband",
        }
    )
    return (
        removed.groupby(["qc_reason_after", "source", "metric", "passband"], dropna=False)
        .size()
        .reset_index(name="newly_failed_rows")
        .sort_values("newly_failed_rows", ascending=False, kind="stable")
        .reset_index(drop=True)
    )


def _value_limit_rejections(frame: pd.DataFrame, limits: Sequence[MetricValueLimit]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not limits:
        return rows
    for limit in limits:
        metric_rows = frame.loc[frame.get("metric", "").astype(str).eq(limit.metric)].copy()
        if metric_rows.empty:
            continue
        for source in limit.sources:
            source_key = str(source).strip().lower()
            value_col = {"observed": "value_obs", "synthetic": "value_syn"}.get(source_key)
            if value_col is None or value_col not in metric_rows.columns:
                continue
            values = pd.to_numeric(metric_rows[value_col], errors="coerce")
            selected = metric_rows.loc[values.abs() > float(limit.max_abs)].copy()
            for _, row in selected.iterrows():
                rows.append(_rejection_row(row, source_key, limit.reason, rejected_value=float(values.loc[row.name])))
    return rows


def _residual_limit_rejections(frame: pd.DataFrame, setting: MetricResidualLimit) -> list[dict[str, object]]:
    if setting.column not in frame.columns or setting.max_abs is None:
        return []
    values = pd.to_numeric(frame[setting.column], errors="coerce")
    selected = frame.loc[values.abs() > float(setting.max_abs)].copy()
    rows: list[dict[str, object]] = []
    for _, row in selected.iterrows():
        for source in QC_SOURCES:
            rows.append(_rejection_row(row, source, setting.reason, residual_value=float(values.loc[row.name])))
    return rows


def _spatial_residual_rejections(frame: pd.DataFrame, setting: SpatialResidualOutlierSettings) -> list[dict[str, object]]:
    required = {"event_id", "station", "component", "passband", "metric", setting.column, "sta_lat", "sta_lon"}
    if not required <= set(frame.columns):
        return []
    work = frame.copy()
    work["residual_value"] = pd.to_numeric(work[setting.column], errors="coerce")
    work["sta_lat"] = pd.to_numeric(work["sta_lat"], errors="coerce")
    work["sta_lon"] = pd.to_numeric(work["sta_lon"], errors="coerce")
    work["period_key"] = work.get("period_s", np.nan).map(_period_key) if "period_s" in work.columns else "__nan__"
    group_cols = ["model", "event_id", "component", "passband", "metric", "period_key"]
    group_cols = [column for column in group_cols if column in work.columns]
    rows: list[dict[str, object]] = []
    for _, group in work.dropna(subset=["residual_value", "sta_lat", "sta_lon"]).groupby(group_cols, dropna=False):
        if len(group) <= int(setting.min_neighbors):
            continue
        lat = group["sta_lat"].to_numpy(dtype=float)
        lon = group["sta_lon"].to_numpy(dtype=float)
        residuals = group["residual_value"].to_numpy(dtype=float)
        for pos, (_, row) in enumerate(group.iterrows()):
            distances = _haversine_km(lat[pos], lon[pos], lat, lon)
            neighbor_mask = (distances > 0.0) & (distances <= float(setting.radius_km)) & np.isfinite(residuals)
            if int(neighbor_mask.sum()) < int(setting.min_neighbors):
                continue
            neighbor_values = residuals[neighbor_mask]
            center = float(np.nanmedian(neighbor_values))
            mad = float(1.4826 * np.nanmedian(np.abs(neighbor_values - center)))
            scale = max(mad, float(setting.mad_floor))
            diff = abs(float(row["residual_value"]) - center)
            z_score = diff / scale if scale > 0.0 else np.inf
            if diff >= float(setting.min_abs_difference) and z_score >= float(setting.z_threshold):
                for source in QC_SOURCES:
                    rows.append(
                        _rejection_row(
                            row,
                            source,
                            setting.reason,
                            residual_value=float(row["residual_value"]),
                            neighbor_median=center,
                            neighbor_count=int(neighbor_mask.sum()),
                            neighbor_robust_z=float(z_score),
                        )
                    )
    return rows


def _rejection_row(row: pd.Series, source: str, reason: str, **extra: object) -> dict[str, object]:
    out = {
        "source": str(source).strip().lower(),
        "event_id": str(row.get("event_id", "")).strip(),
        "station": str(row.get("station", "")).strip().upper(),
        "component": str(row.get("component", "")).strip().upper(),
        "passband": str(row.get("passband", "")).strip(),
        "metric": str(row.get("metric", "")).strip(),
        "period_s": row.get("period_s", np.nan),
        "period_key": _period_key(row.get("period_s", np.nan)),
        "qc_reason": reason,
    }
    out.update(extra)
    return out


def _parse_value_limits(raw: object) -> list[MetricValueLimit]:
    if not isinstance(raw, Mapping):
        return []
    limits: list[MetricValueLimit] = []
    for metric, spec in raw.items():
        metric_name = str(metric).strip()
        if not metric_name:
            continue
        if isinstance(spec, Mapping):
            max_abs = _limit_max_abs(spec)
            raw_sources = spec.get("sources", QC_SOURCES)
            if isinstance(raw_sources, str):
                raw_sources = [raw_sources]
            sources = tuple(str(value).strip().lower() for value in raw_sources)
            reason = str(spec.get("reason", f"{metric_name.lower()}_above_sanity_limit"))
        else:
            max_abs = float(spec)
            sources = QC_SOURCES
            reason = f"{metric_name.lower()}_above_sanity_limit"
        if np.isfinite(max_abs):
            limits.append(MetricValueLimit(metric=metric_name, max_abs=float(max_abs), sources=sources, reason=reason))
    return limits


def _limit_max_abs(spec: Mapping[str, object]) -> float:
    if "max_abs" in spec:
        return float(spec["max_abs"])
    if "max_value" in spec:
        return float(spec["max_value"])
    if "max_g" in spec:
        unit = str(spec.get("value_unit", spec.get("data_unit", "cm/s2"))).strip().lower()
        scale = {
            "g": 1.0,
            "gravity": 1.0,
            "m/s2": G_M_PER_S2,
            "m/s^2": G_M_PER_S2,
            "m/s/s": G_M_PER_S2,
            "cm/s2": G_CM_PER_S2,
            "cm/s^2": G_CM_PER_S2,
            "cm/s/s": G_CM_PER_S2,
        }.get(unit)
        if scale is None:
            raise ValueError(f"Unsupported acceleration value_unit for max_g limit: {unit!r}")
        return float(spec["max_g"]) * scale
    return float("nan")


def _parse_residual_limit(raw: object) -> MetricResidualLimit:
    if not isinstance(raw, Mapping):
        return MetricResidualLimit()
    max_abs = raw.get("max_abs", raw.get("max_abs_log2_residual"))
    return MetricResidualLimit(
        column=str(raw.get("column", "log2_residual")),
        max_abs=None if max_abs in (None, "") else float(max_abs),
        reason=str(raw.get("reason", "metric_residual_above_sanity_limit")),
    )


def _parse_spatial_settings(raw: object) -> SpatialResidualOutlierSettings:
    if not isinstance(raw, Mapping):
        return SpatialResidualOutlierSettings()
    return SpatialResidualOutlierSettings(
        enabled=bool(raw.get("enabled", False)),
        column=str(raw.get("column", "log2_residual")),
        radius_km=float(raw.get("radius_km", 10.0)),
        min_neighbors=int(raw.get("min_neighbors", 3)),
        z_threshold=float(raw.get("z_threshold", 8.0)),
        min_abs_difference=float(raw.get("min_abs_difference", raw.get("min_abs_log2_difference", 4.0))),
        mad_floor=float(raw.get("mad_floor", 0.25)),
        reason=str(raw.get("reason", "metric_residual_spatial_outlier")),
    )


def _normalize_qc_keys(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["source_key"] = out["source"].astype(str).str.strip().str.lower()
    out["event_id_key"] = out["event_id"].astype(str).str.strip()
    out["station_key"] = out["station"].astype(str).str.strip().str.upper()
    out["component_key"] = out["component"].astype(str).str.strip().str.upper()
    out["passband_key"] = out["passband"].astype(str).str.strip()
    out["metric_key"] = out["metric"].astype(str).str.strip()
    out["period_key"] = out["period_s"].map(_period_key)
    return out


def _normalize_metric_keys(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["event_id_key"] = out["event_id"].astype(str).str.strip()
    out["station_key"] = out["station"].astype(str).str.strip().str.upper()
    out["component_key"] = out["component"].astype(str).str.strip().str.upper()
    out["passband_key"] = out["passband"].astype(str).str.strip()
    out["metric_key"] = out["metric"].astype(str).str.strip()
    out["period_key"] = out["period_s"].map(_period_key) if "period_s" in out.columns else "__nan__"
    return out


def _normalize_rejection_keys(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["source_key"] = out["source"].astype(str).str.strip().str.lower()
    out["event_id_key"] = out["event_id"].astype(str).str.strip()
    out["station_key"] = out["station"].astype(str).str.strip().str.upper()
    out["component_key"] = out["component"].astype(str).str.strip().str.upper()
    out["passband_key"] = out["passband"].astype(str).str.strip()
    out["metric_key"] = out["metric"].astype(str).str.strip()
    out["period_key"] = out["period_s"].map(_period_key) if "period_s" in out.columns else out["period_key"].astype(str)
    return out


def _source_reason_values(reject: pd.DataFrame, index: Sequence[int], source: str) -> list[object]:
    subset = reject.loc[list(index)]
    return subset.loc[subset["source_key"].eq(source), "qc_reason"].tolist()


def _period_key(value: object) -> str:
    try:
        number = float(value)
    except Exception:
        return "__nan__"
    if not np.isfinite(number):
        return "__nan__"
    return f"{number:.8g}"


def _append_reason(existing: object, new: object) -> str:
    reasons = []
    for item in [existing, new]:
        if item is None:
            continue
        text = str(item).strip()
        if not text or text.lower() == "nan":
            continue
        reasons.extend(part.strip() for part in text.split(";") if part.strip())
    return _join_reasons(reasons)


def _join_reasons(values: Sequence[object]) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text.lower() == "nan" or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return ";".join(out)


def _haversine_km(lat0: float, lon0: float, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    radius = 6371.0088
    phi1 = np.radians(float(lat0))
    phi2 = np.radians(lat.astype(float))
    dphi = np.radians(lat.astype(float) - float(lat0))
    dlambda = np.radians(lon.astype(float) - float(lon0))
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0) ** 2
    return radius * 2.0 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def _empty_rejection_table() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "source",
            "event_id",
            "station",
            "component",
            "passband",
            "metric",
            "period_s",
            "period_key",
            "qc_reason",
        ]
    )


def _read_table(table: pd.DataFrame | str | Path) -> pd.DataFrame:
    if isinstance(table, pd.DataFrame):
        return table.copy()
    path = Path(table).expanduser()
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path, low_memory=False)


def _write_table(df: pd.DataFrame, output_path: str | Path) -> Path:
    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in {".parquet", ".pq"}:
        df.to_parquet(path, index=False)
    else:
        df.to_csv(path, index=False)
    return path


__all__ = [
    "G_CM_PER_S2",
    "G_M_PER_S2",
    "MetricResidualLimit",
    "MetricSanityQCSettings",
    "MetricValueLimit",
    "SpatialResidualOutlierSettings",
    "apply_metric_sanity_rejections_to_metric_table",
    "apply_metric_sanity_rejections_to_qc_inventory",
    "build_metric_sanity_rejection_table",
    "metric_sanity_settings_from_config",
    "summarize_metric_sanity_removals",
]
