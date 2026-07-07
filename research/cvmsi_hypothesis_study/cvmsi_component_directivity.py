#!/usr/bin/env python3
"""Component-specific CVM-SI residual models with mechanism/directivity terms.

This private analysis adds approximate double-couple radiation and simple
directivity predictors to the raw component residuals. It is intentionally
separate from package runtime code because the predictors are diagnostic:
takeoff angles are straight-line approximations and the radiation amplitudes
are not finite-frequency sensitivity kernels.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    import seaborn as sns
except Exception:  # pragma: no cover - CARC environments can vary.
    sns = None


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_METRICS = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/tables/metrics_final_enriched.parquet")
DEFAULT_PAIRS = REPO_ROOT / "outputs" / "review" / "cvmsi_hypothesis_study" / "tables" / "pairs.csv"
DEFAULT_OUTPUT = REPO_ROOT / "outputs" / "review" / "cvmsi_hypothesis_study" / "component_directivity"
DEFAULT_MODEL = "cvmsi_20260506_material_0p6x1p2_asdf"
DEFAULT_METRICS_FOCUS = ("PGA", "PGV")
DEFAULT_BANDS = ("1-2 sec", "2-3 sec", "3-5 sec")
DEFAULT_COMPONENTS = ("R", "T", "Z")
RANDOM_SEED = 20260702

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}
COLOR_FAMILIES = {
    "blue": {"light": "#CEDFFE", "base": "#A3BEFA", "mid": "#5477C4", "dark": "#2E4780"},
    "gold": {"light": "#FFEA8F", "base": "#FFE15B", "mid": "#B8A037", "dark": "#736422"},
    "orange": {"light": "#FFBDA1", "base": "#F0986E", "mid": "#CC6F47", "dark": "#804126"},
    "olive": {"light": "#BEEB96", "base": "#A3D576", "mid": "#71B436", "dark": "#386411"},
    "pink": {"light": "#F5BACC", "base": "#F390CA", "mid": "#BD569B", "dark": "#8A3A6F"},
}
NEUTRAL = {"light": "#E2E5EA", "base": "#C5CAD3", "mid": "#7A828F", "dark": "#464C55"}


@dataclass(frozen=True)
class ModelSpec:
    name: str
    label: str
    formula_rhs: str
    description: str


BASE_RHS = (
    "C(band) + log_distance_z + magnitude_z + event_depth_km_z + "
    "C(faulting_type) + path_basin_fraction_z + path_la_basin_fraction_z + "
    "C(path_class) + C(station_region_type)"
)
AZIMUTH_TAKEOFF_RHS = BASE_RHS + (
    " + takeoff_angle_z + rel_az_cos_z + rel_az_sin_z + "
    "rel_az2_cos_z + rel_az2_sin_z"
)
RADIATION_RHS = AZIMUTH_TAKEOFF_RHS + (
    " + radiation_p_abs_z + radiation_sv_abs_z + radiation_sh_abs_z"
)
DIRECTIVITY_RHS = RADIATION_RHS + (
    " + slip_alignment_z + slip_takeoff_alignment_z"
)

MODEL_SPECS = (
    ModelSpec(
        "m00_source_path_site",
        "Source/path/site",
        BASE_RHS,
        "Band, distance, source magnitude/depth/faulting, basin-path fractions, path class, and station geomorphology.",
    ),
    ModelSpec(
        "m01_takeoff_azimuth",
        "Add takeoff/azimuth",
        AZIMUTH_TAKEOFF_RHS,
        "Adds approximate straight-line takeoff angle and source-to-station azimuth relative to strike.",
    ),
    ModelSpec(
        "m02_radiation",
        "Add radiation",
        RADIATION_RHS,
        "Adds approximate double-couple P, SV, and SH radiation amplitudes.",
    ),
    ModelSpec(
        "m03_directivity",
        "Add directivity",
        DIRECTIVITY_RHS,
        "Adds slip-vector and slip-takeoff alignment terms after relative azimuth and radiation controls.",
    ),
)

DIRECTIVITY_TERMS = {
    "takeoff_angle_z": "Takeoff angle",
    "rel_az_cos_z": "cos(az-strike)",
    "rel_az_sin_z": "sin(az-strike)",
    "rel_az2_cos_z": "cos(2 az-strike)",
    "rel_az2_sin_z": "sin(2 az-strike)",
    "radiation_p_abs_z": "|P radiation|",
    "radiation_sv_abs_z": "|SV radiation|",
    "radiation_sh_abs_z": "|SH radiation|",
    "slip_alignment_z": "Slip align.",
    "slip_takeoff_alignment_z": "Slip x takeoff",
}

CATEGORICAL_TERMS = {
    "band": "C(band)",
    "faulting_type": "C(faulting_type)",
    "path_class": "C(path_class)",
    "station_region_type": "C(station_region_type)",
}
CONTINUOUS_TERMS = {
    "m00_source_path_site": [
        "log_distance_z",
        "magnitude_z",
        "event_depth_km_z",
        "path_basin_fraction_z",
        "path_la_basin_fraction_z",
    ],
    "m01_takeoff_azimuth": [
        "log_distance_z",
        "magnitude_z",
        "event_depth_km_z",
        "path_basin_fraction_z",
        "path_la_basin_fraction_z",
        "takeoff_angle_z",
        "rel_az_cos_z",
        "rel_az_sin_z",
        "rel_az2_cos_z",
        "rel_az2_sin_z",
    ],
    "m02_radiation": [
        "log_distance_z",
        "magnitude_z",
        "event_depth_km_z",
        "path_basin_fraction_z",
        "path_la_basin_fraction_z",
        "takeoff_angle_z",
        "rel_az_cos_z",
        "rel_az_sin_z",
        "rel_az2_cos_z",
        "rel_az2_sin_z",
        "radiation_p_abs_z",
        "radiation_sv_abs_z",
        "radiation_sh_abs_z",
    ],
    "m03_directivity": [
        "log_distance_z",
        "magnitude_z",
        "event_depth_km_z",
        "path_basin_fraction_z",
        "path_la_basin_fraction_z",
        "takeoff_angle_z",
        "rel_az_cos_z",
        "rel_az_sin_z",
        "rel_az2_cos_z",
        "rel_az2_sin_z",
        "radiation_p_abs_z",
        "radiation_sv_abs_z",
        "radiation_sh_abs_z",
        "slip_alignment_z",
        "slip_takeoff_alignment_z",
    ],
}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS, help="Enriched metric parquet with raw component rows.")
    parser.add_argument("--pairs-csv", type=Path, default=DEFAULT_PAIRS, help="Optional pair-level context table with path fractions/classes.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--metric", action="append", dest="metrics_focus", default=None)
    parser.add_argument("--band", action="append", dest="bands", default=None)
    parser.add_argument("--component", action="append", dest="components", default=None)
    parser.add_argument("--min-rows", type=int, default=600, help="Minimum rows required for each metric/component model.")
    parser.add_argument("--max-rows-per-fit", type=int, default=0, help="Optional deterministic sample cap per metric/component; 0 uses all rows.")
    parser.add_argument("--maxiter", type=int, default=180)
    parser.add_argument("--skip-figures", action="store_true")
    return parser.parse_args(argv)


def use_chart_theme() -> None:
    rc = {
        "figure.facecolor": TOKENS["surface"],
        "figure.edgecolor": "none",
        "savefig.facecolor": TOKENS["surface"],
        "savefig.edgecolor": "none",
        "axes.facecolor": TOKENS["panel"],
        "axes.edgecolor": TOKENS["axis"],
        "axes.labelcolor": TOKENS["ink"],
        "axes.grid": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.color": TOKENS["grid"],
        "grid.linewidth": 0.8,
        "font.family": "sans-serif",
        "font.sans-serif": ["Aptos", "Inter", "Segoe UI", "DejaVu Sans", "Arial", "sans-serif"],
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "xtick.labelsize": 10.5,
        "ytick.labelsize": 10.5,
        "legend.fontsize": 10.5,
    }
    if sns is not None:
        sns.set_theme(style="whitegrid", rc=rc)
    else:
        plt.rcParams.update(rc)


def add_chart_header(fig: plt.Figure, ax: plt.Axes, title: str, subtitle: str) -> None:
    import textwrap

    title = textwrap.fill(title, width=96, break_long_words=False)
    subtitle = textwrap.fill(subtitle, width=132, break_long_words=False)
    title_lines = title.count("\n") + 1
    left = ax.get_position().x0
    fig.text(left, 0.985, title, ha="left", va="top", fontsize=18, fontweight="semibold", color=TOKENS["ink"], linespacing=1.08)
    fig.text(left, 0.938 - 0.041 * (title_lines - 1), subtitle, ha="left", va="top", fontsize=12.5, color=TOKENS["muted"], linespacing=1.18)


def load_components(path: Path, *, model: str, metrics_focus: Sequence[str], bands: Sequence[str], components: Sequence[str]) -> pd.DataFrame:
    import pyarrow.parquet as pq

    if not path.exists():
        raise FileNotFoundError(f"metrics parquet not found: {path}")
    wanted = [
        "event_id",
        "station",
        "component",
        "model",
        "metric",
        "band",
        "log2_residual",
        "distance_km",
        "azimuth_deg",
        "backazimuth_deg",
        "magnitude",
        "Mw",
        "event_depth_km",
        "depth_km",
        "strike",
        "dip",
        "rake",
        "path_basin_fraction",
        "path_la_basin_fraction",
        "path_class",
        "station_region_type",
        "event_region_type",
    ]
    available = set(pq.ParquetFile(path).schema.names)
    columns = [column for column in wanted if column in available]
    required = {"event_id", "station", "component", "model", "metric", "band", "log2_residual"}
    missing = required - set(columns)
    if missing:
        raise ValueError(f"metrics parquet missing required component columns: {sorted(missing)}")

    try:
        df = pd.read_parquet(
            path,
            columns=columns,
            filters=[
                ("model", "==", model),
                ("metric", "in", list(metrics_focus)),
                ("band", "in", list(bands)),
                ("component", "in", list(components)),
            ],
        )
    except Exception:
        df = pd.read_parquet(path, columns=columns)
        df = df.loc[
            df["model"].astype(str).eq(str(model))
            & df["metric"].astype(str).isin(metrics_focus)
            & df["band"].astype(str).isin(bands)
            & df["component"].astype(str).str.upper().isin({str(c).upper() for c in components})
        ].copy()

    df = standardize_columns(df)
    for column in ["event_id", "station", "component", "metric", "band", "model"]:
        df[column] = df[column].astype(str)
    df["component"] = df["component"].str.upper()
    numeric = [
        "log2_residual",
        "distance_km",
        "azimuth_deg",
        "backazimuth_deg",
        "magnitude",
        "event_depth_km",
        "strike",
        "dip",
        "rake",
        "path_basin_fraction",
        "path_la_basin_fraction",
    ]
    for column in numeric:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["event_id", "station", "component", "metric", "band", "log2_residual"])
    return df


def merge_pair_context(raw: pd.DataFrame, pairs_csv: Path | None) -> pd.DataFrame:
    if pairs_csv is None or not pairs_csv.exists():
        return raw
    wanted = [
        "event_id",
        "station",
        "metric",
        "band",
        "path_basin_fraction",
        "path_la_basin_fraction",
        "path_class",
        "station_region_type",
        "station_region",
        "station_geomorphology",
        "event_region_type",
        "event_region",
        "event_geomorphology",
        "Vs30",
        "geologic_description",
    ]
    pairs = pd.read_csv(pairs_csv, usecols=lambda column: column in wanted)
    for column in ["event_id", "station", "metric", "band"]:
        pairs[column] = pairs[column].astype(str)
    pairs = pairs.drop_duplicates(["event_id", "station", "metric", "band"])
    merged = raw.merge(pairs, on=["event_id", "station", "metric", "band"], how="left", suffixes=("", "_pair"))
    for column in [
        "path_basin_fraction",
        "path_la_basin_fraction",
        "path_class",
        "station_region_type",
        "station_region",
        "station_geomorphology",
        "event_region_type",
        "event_region",
        "event_geomorphology",
        "Vs30",
        "geologic_description",
    ]:
        pair_col = f"{column}_pair"
        if pair_col in merged.columns:
            if column in {"path_basin_fraction", "path_la_basin_fraction", "path_class"}:
                merged[column] = merged[pair_col].combine_first(merged[column]) if column in merged.columns else merged[pair_col]
            elif column in merged.columns:
                merged[column] = merged[column].combine_first(merged[pair_col])
            else:
                merged[column] = merged[pair_col]
            merged = merged.drop(columns=[pair_col])
    return merged


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "magnitude" not in out.columns and "Mw" in out.columns:
        out["magnitude"] = out["Mw"]
    elif "magnitude" in out.columns and "Mw" in out.columns:
        out["magnitude"] = out["magnitude"].combine_first(out["Mw"])
    if "event_depth_km" not in out.columns and "depth_km" in out.columns:
        out["event_depth_km"] = out["depth_km"]
    elif "event_depth_km" in out.columns and "depth_km" in out.columns:
        out["event_depth_km"] = out["event_depth_km"].combine_first(out["depth_km"])
    for column, default in {
        "path_basin_fraction": 0.0,
        "path_la_basin_fraction": 0.0,
        "path_class": "unknown",
        "station_region_type": "unknown",
        "event_region_type": "unknown",
    }.items():
        if column not in out.columns:
            out[column] = default
    return out


def classify_faulting(rake: object) -> str:
    try:
        value = float(rake)
    except Exception:
        return "unknown"
    if not np.isfinite(value):
        return "unknown"
    wrapped = ((value + 180.0) % 360.0) - 180.0
    if abs(wrapped) <= 30.0 or abs(abs(wrapped) - 180.0) <= 30.0:
        return "strike-slip"
    if 45.0 <= wrapped <= 135.0:
        return "reverse"
    if -135.0 <= wrapped <= -45.0:
        return "normal"
    return "oblique"


def wrap_degrees(values: pd.Series | np.ndarray) -> np.ndarray:
    return (np.asarray(values, dtype=float) + 180.0) % 360.0 - 180.0


def zscore(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    std = float(values.std(skipna=True))
    if not np.isfinite(std) or std <= 0:
        return pd.Series(0.0, index=series.index).where(values.notna(), np.nan)
    return (values - float(values.mean(skipna=True))) / std


def engineer_directivity(raw: pd.DataFrame) -> pd.DataFrame:
    out = raw.copy()
    out["faulting_type"] = out["rake"].apply(classify_faulting)
    out["event_depth_km_effective"] = pd.to_numeric(out["event_depth_km"], errors="coerce").clip(lower=1.0)
    out["takeoff_angle_deg"] = np.degrees(
        np.arctan2(
            pd.to_numeric(out["distance_km"], errors="coerce").clip(lower=0.05),
            out["event_depth_km_effective"],
        )
    ).clip(1.0, 89.5)

    strike = np.deg2rad(pd.to_numeric(out["strike"], errors="coerce"))
    dip = np.deg2rad(pd.to_numeric(out["dip"], errors="coerce"))
    rake = np.deg2rad(pd.to_numeric(out["rake"], errors="coerce"))
    azimuth = np.deg2rad(pd.to_numeric(out["azimuth_deg"], errors="coerce") % 360.0)
    takeoff = np.deg2rad(out["takeoff_angle_deg"])
    phi = np.deg2rad(wrap_degrees(pd.to_numeric(out["azimuth_deg"], errors="coerce") - pd.to_numeric(out["strike"], errors="coerce")))

    out["rel_az_deg"] = np.degrees(phi)
    out["rel_az_cos"] = np.cos(phi)
    out["rel_az_sin"] = np.sin(phi)
    out["rel_az2_cos"] = np.cos(2.0 * phi)
    out["rel_az2_sin"] = np.sin(2.0 * phi)

    radiation = double_couple_radiation(strike=strike, dip=dip, rake=rake, phi=phi, takeoff=takeoff)
    for column, values in radiation.items():
        out[column] = values
        out[f"{column}_abs"] = np.abs(values)
    out["radiation_total_abs"] = np.sqrt(
        out["radiation_p"].pow(2) + out["radiation_sv"].pow(2) + out["radiation_sh"].pow(2)
    )

    sta_e = np.sin(azimuth)
    sta_n = np.cos(azimuth)
    strike_e = np.sin(strike)
    strike_n = np.cos(strike)
    dip_az = strike + (np.pi / 2.0)
    dip_e = np.sin(dip_az)
    dip_n = np.cos(dip_az)
    slip_e = np.cos(rake) * strike_e + np.sin(rake) * np.cos(dip) * dip_e
    slip_n = np.cos(rake) * strike_n + np.sin(rake) * np.cos(dip) * dip_n
    slip_norm = np.sqrt(slip_e**2 + slip_n**2)
    slip_e = np.divide(slip_e, slip_norm, out=np.full_like(slip_e, np.nan, dtype=float), where=slip_norm > 0)
    slip_n = np.divide(slip_n, slip_norm, out=np.full_like(slip_n, np.nan, dtype=float), where=slip_norm > 0)

    out["fault_parallel_alignment"] = sta_e * strike_e + sta_n * strike_n
    out["fault_normal_alignment"] = sta_e * dip_e + sta_n * dip_n
    out["slip_alignment"] = sta_e * slip_e + sta_n * slip_n
    out["slip_takeoff_alignment"] = out["slip_alignment"] * np.sin(takeoff)
    out["updip_alignment"] = -(sta_e * dip_e + sta_n * dip_n)

    component_radiation = []
    for row in out.itertuples(index=False):
        component = str(getattr(row, "component")).upper()
        if component == "R":
            component_radiation.append(abs(getattr(row, "radiation_sv")))
        elif component == "T":
            component_radiation.append(abs(getattr(row, "radiation_sh")))
        elif component == "Z":
            component_radiation.append(abs(getattr(row, "radiation_p")))
        else:
            component_radiation.append(np.nan)
    out["radiation_component_abs"] = component_radiation

    z_columns = [
        "log_distance",
        "magnitude",
        "event_depth_km",
        "path_basin_fraction",
        "path_la_basin_fraction",
        "rel_az_cos",
        "rel_az_sin",
        "rel_az2_cos",
        "rel_az2_sin",
        "radiation_p_abs",
        "radiation_sv_abs",
        "radiation_sh_abs",
        "radiation_component_abs",
        "fault_parallel_alignment",
        "fault_normal_alignment",
        "slip_alignment",
        "slip_takeoff_alignment",
        "updip_alignment",
    ]
    out["log_distance"] = np.log1p(pd.to_numeric(out["distance_km"], errors="coerce"))
    for column in z_columns:
        out[f"{column}_z"] = zscore(out[column]) if column in out.columns else np.nan
    out["takeoff_angle_z"] = zscore(out["takeoff_angle_deg"])

    for column in ["band", "path_class", "station_region_type", "event_region_type", "faulting_type"]:
        out[column] = out[column].fillna("unknown").astype(str)
    return out.replace([np.inf, -np.inf], np.nan)


def double_couple_radiation(
    *,
    strike: np.ndarray,
    dip: np.ndarray,
    rake: np.ndarray,
    phi: np.ndarray,
    takeoff: np.ndarray,
) -> dict[str, np.ndarray]:
    """Return approximate Aki-Richards P, SV, and SH radiation coefficients."""

    sd = np.sin(dip)
    cd = np.cos(dip)
    s2d = np.sin(2.0 * dip)
    c2d = np.cos(2.0 * dip)
    sl = np.sin(rake)
    cl = np.cos(rake)
    si = np.sin(takeoff)
    ci = np.cos(takeoff)
    s2i = np.sin(2.0 * takeoff)
    c2i = np.cos(2.0 * takeoff)
    sp = np.sin(phi)
    cp = np.cos(phi)
    s2p = np.sin(2.0 * phi)
    c2p = np.cos(2.0 * phi)

    radiation_p = (
        cl * sd * si**2 * s2p
        - cl * cd * s2i * cp
        + sl * s2d * (ci**2 - si**2 * sp**2)
        + sl * c2d * s2i * sp
    )
    radiation_sv = (
        sl * c2d * c2i * sp
        - cl * cd * c2i * cp
        + 0.5 * cl * sd * s2i * s2p
        - 0.5 * sl * s2d * s2i * (1.0 + sp**2)
    )
    radiation_sh = (
        cl * cd * ci * sp
        + cl * sd * si * c2p
        + sl * c2d * ci * cp
        - 0.5 * sl * s2d * si * s2p
    )
    return {
        "radiation_p": radiation_p,
        "radiation_sv": radiation_sv,
        "radiation_sh": radiation_sh,
    }


def prepare_fit_frame(data: pd.DataFrame, *, metric: str, component: str, max_rows: int) -> pd.DataFrame:
    out = data.loc[data["metric"].eq(metric) & data["component"].eq(component)].copy()
    required = [
        "event_id",
        "station",
        "log2_residual",
        "log_distance_z",
        "magnitude_z",
        "event_depth_km_z",
        "path_basin_fraction_z",
        "path_la_basin_fraction_z",
        "takeoff_angle_z",
        "rel_az_cos_z",
        "rel_az_sin_z",
        "rel_az2_cos_z",
        "rel_az2_sin_z",
        "radiation_p_abs_z",
        "radiation_sv_abs_z",
        "radiation_sh_abs_z",
        "radiation_component_abs_z",
        "fault_parallel_alignment_z",
        "fault_normal_alignment_z",
        "slip_alignment_z",
        "slip_takeoff_alignment_z",
        "updip_alignment_z",
    ]
    out = out.dropna(subset=[column for column in required if column in out.columns]).copy()
    if max_rows > 0 and len(out) > max_rows:
        out = out.sample(n=max_rows, random_state=RANDOM_SEED).copy()
    return out


def fit_mixed_model(
    metric: str,
    component: str,
    spec: ModelSpec,
    data: pd.DataFrame,
    *,
    maxiter: int,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    import statsmodels.formula.api as smf

    formula_rhs = build_formula_rhs(data, spec)
    formula = f"log2_residual ~ {formula_rhs}"
    attempts = []
    for method in ("lbfgs", "powell", "nm", "cg"):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                model = smf.mixedlm(
                    formula,
                    data=data,
                    groups=data["station"],
                    re_formula="1",
                    vc_formula={"event": "0 + C(event_id)"},
                )
                result = model.fit(
                    reml=False,
                    method=method,
                    maxiter=maxiter if method == "lbfgs" else max(maxiter, 420),
                    disp=False,
                )
                attempts.append(
                    {
                        "method": method,
                        "result": result,
                        "converged": bool(getattr(result, "converged", False)),
                        "aic": float(result.aic) if np.isfinite(result.aic) else np.inf,
                        "warnings": list(caught),
                        "error": "",
                    }
                )
                if attempts[-1]["converged"]:
                    break
            except Exception as exc:
                attempts.append(
                    {
                        "method": method,
                        "result": None,
                        "converged": False,
                        "aic": np.inf,
                        "warnings": list(caught),
                        "error": repr(exc),
                    }
                )

    valid = [attempt for attempt in attempts if attempt["result"] is not None]
    if not valid:
        raise RuntimeError("; ".join(f"{attempt['method']}: {attempt['error']}" for attempt in attempts))
    converged = [attempt for attempt in valid if attempt["converged"]]
    selected = min(converged or valid, key=lambda attempt: attempt["aic"])
    result = selected["result"]
    warning_text = []
    for attempt in attempts:
        warning_text.extend(str(w.message) for w in attempt["warnings"])
        if attempt["error"]:
            warning_text.append(f"{attempt['method']} error: {attempt['error']}")

    fixed_rows = fixed_rows_from_result(result, metric, component, spec, str(selected["method"]))
    station_var = float(result.cov_re.iloc[0, 0]) if result.cov_re.shape[0] else np.nan
    event_var = float(result.vcomp[0]) if len(result.vcomp) else np.nan
    residual_var = float(result.scale)
    total_var = np.nansum([station_var, event_var, residual_var])
    compare_row = {
        "metric": metric,
        "component": component,
        "model_name": spec.name,
        "model_label": spec.label,
        "description": spec.description,
        "formula_rhs": formula_rhs,
        "nobs": int(result.nobs),
        "events": int(data["event_id"].nunique()),
        "stations": int(data["station"].nunique()),
        "fixed_terms": int(len(result.fe_params)),
        "log_likelihood": float(result.llf),
        "aic": float(result.aic),
        "bic": float(result.bic),
        "converged": bool(getattr(result, "converged", False)),
        "station_random_intercept_var": station_var,
        "event_random_intercept_var": event_var,
        "residual_var": residual_var,
        "total_variance": float(total_var),
        "station_variance_share": safe_divide(station_var, total_var),
        "event_variance_share": safe_divide(event_var, total_var),
        "residual_variance_share": safe_divide(residual_var, total_var),
        "optimizer": str(selected["method"]),
        "optimizer_attempts": ",".join(str(attempt["method"]) for attempt in attempts),
        "warning_count": len(warning_text),
        "warnings": " | ".join(sorted(set(warning_text)))[:1200],
        "note": "",
    }
    return fixed_rows, compare_row


def build_formula_rhs(data: pd.DataFrame, spec: ModelSpec) -> str:
    terms: list[str] = []
    for column, term in CATEGORICAL_TERMS.items():
        if column in data.columns and data[column].dropna().astype(str).nunique() > 1:
            terms.append(term)
    for column in CONTINUOUS_TERMS[spec.name]:
        if is_varying_numeric(data, column):
            terms.append(column)
    return " + ".join(terms) if terms else "1"


def is_varying_numeric(data: pd.DataFrame, column: str) -> bool:
    if column not in data.columns:
        return False
    values = pd.to_numeric(data[column], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if values.size < 2:
        return False
    return bool(values.nunique() > 1 and float(values.std()) > 1e-12)


def fixed_rows_from_result(result: object, metric: str, component: str, spec: ModelSpec, optimizer: str) -> list[dict[str, object]]:
    conf = result.conf_int()
    rows = []
    for term, coef in result.fe_params.items():
        se = float(result.bse_fe.get(term, np.nan))
        rows.append(
            {
                "metric": metric,
                "component": component,
                "model_name": spec.name,
                "model_label": spec.label,
                "term": term,
                "coef": float(coef),
                "se": se,
                "z": float(coef / se) if np.isfinite(se) and se > 0 else np.nan,
                "pvalue": float(result.pvalues.get(term, np.nan)),
                "ci_low": float(conf.loc[term, 0]) if term in conf.index else np.nan,
                "ci_high": float(conf.loc[term, 1]) if term in conf.index else np.nan,
                "nobs": int(result.nobs),
                "converged": bool(getattr(result, "converged", False)),
                "optimizer": optimizer,
                "note": "",
            }
        )
    return rows


def safe_divide(numerator: float, denominator: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0:
        return np.nan
    return float(numerator / denominator)


def fit_all(data: pd.DataFrame, *, metrics: Sequence[str], components: Sequence[str], min_rows: int, max_rows: int, maxiter: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fixed_rows: list[dict[str, object]] = []
    compare_rows: list[dict[str, object]] = []
    support_rows: list[dict[str, object]] = []
    predictor_rows: list[dict[str, object]] = []

    for metric in metrics:
        for component in components:
            raw_subset = data.loc[data["metric"].eq(metric) & data["component"].eq(component)].copy()
            fit_data = prepare_fit_frame(data, metric=metric, component=str(component).upper(), max_rows=max_rows)
            support_rows.append(
                {
                    "metric": metric,
                    "component": component,
                    "raw_rows": int(len(raw_subset)),
                    "fit_rows": int(len(fit_data)),
                    "events": int(fit_data["event_id"].nunique()) if not fit_data.empty else 0,
                    "stations": int(fit_data["station"].nunique()) if not fit_data.empty else 0,
                    "raw_events": int(raw_subset["event_id"].nunique()) if not raw_subset.empty else 0,
                    "raw_stations": int(raw_subset["station"].nunique()) if not raw_subset.empty else 0,
                    "geometry_complete_share": safe_divide(float(len(fit_data)), float(len(raw_subset))),
                }
            )
            if len(fit_data) < min_rows or fit_data["event_id"].nunique() < 10 or fit_data["station"].nunique() < 20:
                compare_rows.append(
                    {
                        "metric": metric,
                        "component": component,
                        "model_name": "skipped_insufficient_support",
                        "model_label": "Skipped",
                        "description": "Not enough complete geometry rows for component-specific mixed model.",
                        "nobs": int(len(fit_data)),
                        "events": int(fit_data["event_id"].nunique()) if not fit_data.empty else 0,
                        "stations": int(fit_data["station"].nunique()) if not fit_data.empty else 0,
                        "converged": False,
                        "note": f"Need at least {min_rows} rows, 10 events, and 20 stations.",
                    }
                )
                continue
            predictor_rows.extend(summarize_predictors(fit_data, metric, component))
            for spec in MODEL_SPECS:
                try:
                    rows, compare = fit_mixed_model(metric, component, spec, fit_data, maxiter=maxiter)
                    fixed_rows.extend(rows)
                    compare_rows.append(compare)
                except Exception as exc:
                    compare_rows.append(
                        {
                        "metric": metric,
                        "component": component,
                        "model_name": spec.name,
                        "model_label": spec.label,
                        "description": spec.description,
                        "formula_rhs": build_formula_rhs(fit_data, spec),
                        "nobs": int(len(fit_data)),
                            "events": int(fit_data["event_id"].nunique()),
                            "stations": int(fit_data["station"].nunique()),
                            "fixed_terms": np.nan,
                            "log_likelihood": np.nan,
                            "aic": np.nan,
                            "bic": np.nan,
                            "converged": False,
                            "station_random_intercept_var": np.nan,
                            "event_random_intercept_var": np.nan,
                            "residual_var": np.nan,
                            "total_variance": np.nan,
                            "station_variance_share": np.nan,
                            "event_variance_share": np.nan,
                            "residual_variance_share": np.nan,
                            "optimizer": "",
                            "optimizer_attempts": "",
                            "warning_count": np.nan,
                            "warnings": "",
                            "note": repr(exc),
                        }
                    )

    fixed = pd.DataFrame(fixed_rows)
    compare = add_model_deltas(pd.DataFrame(compare_rows))
    support = pd.DataFrame(support_rows)
    predictor_summary = pd.DataFrame(predictor_rows)
    return fixed, compare, support, predictor_summary


def summarize_predictors(data: pd.DataFrame, metric: str, component: str) -> list[dict[str, object]]:
    rows = []
    columns = [
        "takeoff_angle_deg",
        "radiation_p_abs",
        "radiation_sv_abs",
        "radiation_sh_abs",
        "radiation_component_abs",
        "fault_parallel_alignment",
        "fault_normal_alignment",
        "slip_alignment",
        "slip_takeoff_alignment",
        "updip_alignment",
    ]
    for column in columns:
        values = pd.to_numeric(data[column], errors="coerce").dropna()
        if values.empty:
            continue
        rows.append(
            {
                "metric": metric,
                "component": component,
                "predictor": column,
                "rows": int(values.size),
                "mean": float(values.mean()),
                "median": float(values.median()),
                "std": float(values.std()),
                "q05": float(values.quantile(0.05)),
                "q95": float(values.quantile(0.95)),
            }
        )
    return rows


def add_model_deltas(compare: pd.DataFrame) -> pd.DataFrame:
    if compare.empty or "model_name" not in compare.columns:
        return compare
    out = compare.copy()
    out["delta_aic_from_baseline"] = np.nan
    out["delta_bic_from_baseline"] = np.nan
    out["delta_aic_from_best"] = np.nan
    out["delta_bic_from_best"] = np.nan
    out["residual_variance_change_from_baseline"] = np.nan
    for _, group in out.loc[out["model_name"].isin([spec.name for spec in MODEL_SPECS])].groupby(["metric", "component"], dropna=False):
        idx = group.index
        baseline = group.loc[group["model_name"].eq("m00_source_path_site")]
        if not baseline.empty:
            base = baseline.iloc[0]
            for source, target in [("aic", "delta_aic_from_baseline"), ("bic", "delta_bic_from_baseline")]:
                if np.isfinite(base.get(source, np.nan)):
                    out.loc[idx, target] = group[source] - float(base[source])
            if np.isfinite(base.get("residual_var", np.nan)) and float(base["residual_var"]) != 0:
                out.loc[idx, "residual_variance_change_from_baseline"] = (group["residual_var"] - float(base["residual_var"])) / float(base["residual_var"])
        out.loc[idx, "delta_aic_from_best"] = group["aic"] - group["aic"].min(skipna=True)
        out.loc[idx, "delta_bic_from_best"] = group["bic"] - group["bic"].min(skipna=True)
    return out


def build_key_effects(fixed: pd.DataFrame) -> pd.DataFrame:
    if fixed.empty:
        return pd.DataFrame()
    out = fixed.loc[fixed["model_name"].eq("m03_directivity") & fixed["term"].isin(DIRECTIVITY_TERMS)].copy()
    if out.empty:
        return out
    out["term_label"] = out["term"].map(DIRECTIVITY_TERMS)
    out["significant_95"] = (out["ci_low"] > 0) | (out["ci_high"] < 0)
    out["metric_component"] = out["metric"].astype(str) + " " + out["component"].astype(str)
    order = {term: idx for idx, term in enumerate(DIRECTIVITY_TERMS)}
    out["term_order"] = out["term"].map(order)
    return out.sort_values(["metric", "component", "term_order"])


def plot_model_comparison(compare: pd.DataFrame, figures_dir: Path) -> Path:
    path = figures_dir / "fig_21_component_directivity_model_comparison.png"
    plot_df = compare.loc[compare["model_name"].isin([spec.name for spec in MODEL_SPECS])].copy()
    plot_df = plot_df.loc[plot_df["converged"].eq(True)]
    if plot_df.empty:
        return path
    plot_df["metric_component"] = plot_df["metric"].astype(str) + " " + plot_df["component"].astype(str)
    model_order = [spec.name for spec in MODEL_SPECS[1:]]
    label_map = {spec.name: spec.label for spec in MODEL_SPECS}
    matrix = (
        plot_df.loc[plot_df["model_name"].isin(model_order)]
        .pivot_table(index="metric_component", columns="model_name", values="delta_bic_from_baseline", aggfunc="median")
        .reindex(columns=model_order)
    )
    columns = [label_map.get(column, column) for column in matrix.columns]
    fig, ax = plt.subplots(figsize=(10.5, max(5.2, 0.48 * len(matrix) + 2.2)))
    vmax = max(10.0, float(np.nanpercentile(np.abs(matrix.to_numpy(dtype=float)), 95)))
    if sns is not None:
        sns.heatmap(
            matrix,
            ax=ax,
            cmap="coolwarm",
            center=0.0,
            vmin=-vmax,
            vmax=vmax,
            annot=True,
            fmt=".0f",
            linewidths=1.0,
            linecolor=TOKENS["panel"],
            cbar_kws={"label": "Delta BIC from baseline; negative improves"},
        )
        ax.set_xticklabels(columns, rotation=20, ha="right")
    else:
        im = ax.imshow(matrix.to_numpy(dtype=float), cmap="coolwarm", vmin=-vmax, vmax=vmax, aspect="auto")
        ax.set_xticks(np.arange(len(columns)), columns, rotation=20, ha="right")
        ax.set_yticks(np.arange(len(matrix.index)), matrix.index)
        fig.colorbar(im, ax=ax, label="Delta BIC from baseline; negative improves")
    ax.set_xlabel("")
    ax.set_ylabel("")
    add_chart_header(
        fig,
        ax,
        "Radiation/directivity predictors are tested as nested component-specific model additions",
        "Cells show BIC change relative to the source/path/site baseline fit to the same complete-geometry rows.",
    )
    fig.tight_layout(rect=[0.05, 0.04, 0.98, 0.84])
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_key_effects(key: pd.DataFrame, figures_dir: Path) -> Path:
    path = figures_dir / "fig_22_component_directivity_key_effects.png"
    if key.empty:
        return path
    plot_df = key.copy()
    term_order = list(DIRECTIVITY_TERMS.values())
    col_order = sorted(plot_df["metric_component"].unique())
    matrix = (
        plot_df.pivot_table(index="term_label", columns="metric_component", values="coef", aggfunc="median")
        .reindex(index=term_order, columns=col_order)
        .dropna(axis=0, how="all")
    )
    sig = (
        plot_df.pivot_table(index="term_label", columns="metric_component", values="significant_95", aggfunc="max")
        .reindex(index=matrix.index, columns=matrix.columns)
        .fillna(False)
    )
    annot = matrix.copy().astype(object)
    for row in matrix.index:
        for col in matrix.columns:
            value = matrix.loc[row, col]
            annot.loc[row, col] = "" if pd.isna(value) else f"{value:+.2f}{'*' if bool(sig.loc[row, col]) else ''}"
    fig, ax = plt.subplots(figsize=(12.8, max(7.0, 0.42 * len(matrix) + 2.8)))
    vmax = max(0.15, float(np.nanpercentile(np.abs(matrix.to_numpy(dtype=float)), 95)))
    if sns is not None:
        sns.heatmap(
            matrix,
            ax=ax,
            cmap="coolwarm",
            center=0.0,
            vmin=-vmax,
            vmax=vmax,
            annot=annot,
            fmt="",
            linewidths=1.0,
            linecolor=TOKENS["panel"],
            cbar_kws={"label": "Coefficient, log2(obs/syn)"},
        )
    else:
        im = ax.imshow(matrix.to_numpy(dtype=float), cmap="coolwarm", vmin=-vmax, vmax=vmax, aspect="auto")
        ax.set_xticks(np.arange(len(matrix.columns)), matrix.columns, rotation=30, ha="right")
        ax.set_yticks(np.arange(len(matrix.index)), matrix.index)
        fig.colorbar(im, ax=ax, label="Coefficient, log2(obs/syn)")
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.tick_params(axis="x", rotation=30)
    add_chart_header(
        fig,
        ax,
        "Component-specific directivity coefficients separate radiation, azimuth, and slip-alignment effects",
        "Asterisks mark 95% intervals excluding zero in the full directivity model. Predictors are standardized within each fit.",
    )
    fig.tight_layout(rect=[0.04, 0.04, 0.98, 0.84])
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_support(support: pd.DataFrame, figures_dir: Path) -> Path:
    path = figures_dir / "fig_23_component_directivity_support.png"
    if support.empty:
        return path
    plot_df = support.copy()
    plot_df["metric_component"] = plot_df["metric"].astype(str) + " " + plot_df["component"].astype(str)
    fig, ax = plt.subplots(figsize=(10.8, 5.8))
    x = np.arange(len(plot_df))
    ax.bar(x - 0.18, plot_df["raw_rows"], width=0.36, label="Raw component rows", color=NEUTRAL["light"], edgecolor=NEUTRAL["dark"], linewidth=0.8)
    ax.bar(x + 0.18, plot_df["fit_rows"], width=0.36, label="Complete geometry rows", color=COLOR_FAMILIES["blue"]["base"], edgecolor=COLOR_FAMILIES["blue"]["dark"], linewidth=0.8)
    ax.set_xticks(x, plot_df["metric_component"], rotation=30, ha="right")
    ax.set_ylabel("Rows")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.10), ncol=2)
    add_chart_header(
        fig,
        ax,
        "Component directivity models use the complete focal-mechanism and path-geometry subset",
        "Support is shown before and after requiring strike, dip, rake, azimuth, distance, and event depth.",
    )
    fig.tight_layout(rect=[0.05, 0.06, 0.98, 0.80])
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def write_tables(
    tables_dir: Path,
    *,
    fixed: pd.DataFrame,
    compare: pd.DataFrame,
    support: pd.DataFrame,
    key: pd.DataFrame,
    predictor_summary: pd.DataFrame,
) -> None:
    tables_dir.mkdir(parents=True, exist_ok=True)
    fixed.to_csv(tables_dir / "component_directivity_fixed_effects.csv", index=False)
    compare.to_csv(tables_dir / "component_directivity_model_comparison.csv", index=False)
    support.to_csv(tables_dir / "component_directivity_support.csv", index=False)
    key.to_csv(tables_dir / "component_directivity_key_effects.csv", index=False)
    predictor_summary.to_csv(tables_dir / "component_directivity_predictor_summary.csv", index=False)


def write_report(
    report_dir: Path,
    *,
    compare: pd.DataFrame,
    support: pd.DataFrame,
    key: pd.DataFrame,
    figures: list[Path],
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "cvmsi_component_directivity_report.md"
    support_lines = []
    for row in support.itertuples(index=False):
        support_lines.append(
            f"- {row.metric} {row.component}: {int(row.fit_rows):,} complete-geometry rows "
            f"from {int(row.events)} events and {int(row.stations)} stations "
            f"({row.geometry_complete_share:.1%} of raw component rows)."
        )

    improvement_lines = []
    if not compare.empty and "delta_bic_from_baseline" in compare.columns:
        best_additions = compare.loc[
            compare["model_name"].isin([spec.name for spec in MODEL_SPECS[1:]]) & compare["converged"].eq(True)
        ].copy()
        best_additions = best_additions.sort_values(["metric", "component", "delta_bic_from_baseline"])
        for (metric, component), group in best_additions.groupby(["metric", "component"], dropna=False):
            best = group.iloc[0]
            improvement_lines.append(
                f"- {metric} {component}: best added model is {best.model_label} "
                f"(Delta BIC {best.delta_bic_from_baseline:+.1f}; Delta AIC {best.delta_aic_from_baseline:+.1f})."
            )

    key_lines = []
    if not key.empty:
        sig = key.loc[key["significant_95"].eq(True)].copy()
        for (metric, component), group in sig.groupby(["metric", "component"], dropna=False):
            strongest = group.assign(abs_coef=group["coef"].abs()).sort_values("abs_coef", ascending=False).head(5)
            effects = ", ".join(f"{row.term_label} {row.coef:+.2f}" for row in strongest.itertuples(index=False))
            key_lines.append(f"- {metric} {component}: {effects}.")

    figure_lines = [f"- `{figure.name}`" for figure in figures]
    content = f"""# CVM-SI Component Radiation/Directivity Mixed Models

Generated {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} from `cvmsi_component_directivity.py`.

## Scope

This analysis refits component-specific mixed-effects models to raw component
`log2(observed/synthetic)` residuals. The models use crossed station and event
random intercepts and are fit separately for each metric/component pair.

The added predictors are diagnostic radiation/directivity controls derived from
strike, dip, rake, source-to-station azimuth, hypocentral distance, and event
depth. Takeoff angle is approximated as a straight-line angle from vertical at
the source. These terms do not replace finite-frequency sensitivity kernels or
rupture simulations.

## Nested Model Sequence

1. source/path/site baseline
2. plus relative azimuth and approximate takeoff angle
3. plus double-couple P, SV, and SH radiation amplitudes
4. plus slip-vector and slip-takeoff alignment proxies

## Support

{chr(10).join(support_lines) if support_lines else '- No support rows were available.'}

## Model Comparison

{chr(10).join(improvement_lines) if improvement_lines else '- No converged added models were available for comparison.'}

## Significant Directivity Terms

{chr(10).join(key_lines) if key_lines else '- No directivity/radiation terms had 95% intervals excluding zero in the full model.'}

## Figures

{chr(10).join(figure_lines) if figure_lines else '- No figures were generated.'}

## Tables

- `component_directivity_model_comparison.csv`
- `component_directivity_fixed_effects.csv`
- `component_directivity_key_effects.csv`
- `component_directivity_support.csv`
- `component_directivity_predictor_summary.csv`
"""
    path.write_text(content, encoding="utf-8")
    return path


def write_manifest(output_dir: Path, args: argparse.Namespace, figures: list[Path], report_path: Path) -> Path:
    manifest = {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "metrics": str(args.metrics),
        "pairs_csv": str(args.pairs_csv) if args.pairs_csv else "",
        "output_dir": str(output_dir),
        "model": args.model,
        "metrics_focus": list(args.metrics_focus or DEFAULT_METRICS_FOCUS),
        "bands": list(args.bands or DEFAULT_BANDS),
        "components": list(args.components or DEFAULT_COMPONENTS),
        "min_rows": int(args.min_rows),
        "max_rows_per_fit": int(args.max_rows_per_fit),
        "models": [spec.__dict__ for spec in MODEL_SPECS],
        "figures": [str(figure) for figure in figures],
        "report": str(report_path),
        "radiation_note": "Approximate double-couple terms and straight-line takeoff geometry; diagnostic, not finite-frequency kernels.",
    }
    path = output_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    use_chart_theme()
    output_dir = args.output_dir.expanduser().resolve()
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    report_dir = output_dir / "report"
    for directory in (tables_dir, figures_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)

    metrics_focus = tuple(args.metrics_focus or DEFAULT_METRICS_FOCUS)
    bands = tuple(args.bands or DEFAULT_BANDS)
    components = tuple(str(item).upper() for item in (args.components or DEFAULT_COMPONENTS))

    raw = load_components(args.metrics.expanduser(), model=args.model, metrics_focus=metrics_focus, bands=bands, components=components)
    raw = merge_pair_context(raw, args.pairs_csv.expanduser() if args.pairs_csv else None)
    engineered = engineer_directivity(raw)
    fixed, compare, support, predictor_summary = fit_all(
        engineered,
        metrics=metrics_focus,
        components=components,
        min_rows=int(args.min_rows),
        max_rows=int(args.max_rows_per_fit),
        maxiter=int(args.maxiter),
    )
    key = build_key_effects(fixed)
    write_tables(tables_dir, fixed=fixed, compare=compare, support=support, key=key, predictor_summary=predictor_summary)

    figures: list[Path] = []
    if not args.skip_figures:
        figures_dir.mkdir(parents=True, exist_ok=True)
        figures = [
            plot_model_comparison(compare, figures_dir),
            plot_key_effects(key, figures_dir),
            plot_support(support, figures_dir),
        ]
    report_path = write_report(report_dir, compare=compare, support=support, key=key, figures=figures)
    manifest = write_manifest(output_dir, args, figures, report_path)
    print(f"Wrote {output_dir}")
    print(f"Wrote {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
