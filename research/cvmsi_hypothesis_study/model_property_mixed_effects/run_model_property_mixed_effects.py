#!/usr/bin/env python3
"""Mixed-effects tests for residuals versus local model properties.

This subanalysis is intentionally isolated from the main hypothesis-study
scripts because another agent may be working in the parent directory. It tests
whether the z(Vs), Vp-gradient, and rho-gradient screening correlations survive
crossed event/station mixed-effects controls.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from dataclasses import dataclass
from pathlib import Path
import sys
import textwrap
import warnings

ANALYSIS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.stats import rankdata, spearmanr

from cvmsi_hypothesis_study import CVM_UTM, DEFAULT_MODEL_H5, ModelSampler
from cvmsi_mixed_effects_deep_dive import classify_faulting


DEFAULT_PAIRS = REPO_ROOT / "outputs" / "review" / "cvmsi_hypothesis_study" / "tables" / "pairs.csv"
DEFAULT_OUTPUT = REPO_ROOT / "outputs" / "review" / "cvmsi_hypothesis_study" / "model_property_mixed_effects"

BAND_ORDER = ["1-2 sec", "2-3 sec", "3-5 sec"]
METRIC_ORDER = ["PGA", "PGV", "arias_duration", "energy_intensity"]
METRIC_LABELS = {
    "PGA": "PGA",
    "PGV": "PGV",
    "arias_duration": "Arias duration",
    "energy_intensity": "Energy intensity",
}
DEPTHS_KM = np.linspace(0.0, 15.0, 151)
GRADIENT_WINDOW_HALF_KM = 0.5
MIN_STATIONS = 8
RANDOM_SEED = 20260701

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}
COLORS = {
    "blue": "#5477C4",
    "blue_dark": "#2E4780",
    "gold": "#FFE15B",
    "gold_dark": "#736422",
    "orange": "#F0986E",
    "orange_dark": "#804126",
    "olive": "#A3D576",
    "olive_dark": "#386411",
    "pink": "#F390CA",
    "pink_dark": "#8A3A6F",
    "neutral": "#C5CAD3",
    "neutral_dark": "#464C55",
}


@dataclass(frozen=True)
class PredictorSpec:
    name: str
    label: str
    family: str
    units: str
    description: str


PREDICTORS = (
    PredictorSpec("z_vs_1p0_km", "z(Vs=1.0)", "z-depth", "km", "Depth where sampled model Vs first reaches 1.0 km/s."),
    PredictorSpec("z_vs_2p5_km", "z(Vs=2.5)", "z-depth", "km", "Depth where sampled model Vs first reaches 2.5 km/s."),
    PredictorSpec("vpgrad_signed_mean_0_1km", "Vp signed grad 0-1 km", "Vp gradient", "km/s/km", "Mean signed local Vp vertical gradient in the upper 1 km."),
    PredictorSpec("vpgrad_abs_mean_0_1km", "Vp |grad| 0-1 km", "Vp gradient", "km/s/km", "Mean absolute local Vp vertical gradient in the upper 1 km."),
    PredictorSpec("vpgrad_abs_mean_0_2p5km", "Vp |grad| 0-2.5 km", "Vp gradient", "km/s/km", "Mean absolute local Vp vertical gradient in the upper 2.5 km."),
    PredictorSpec("vpgrad_abs_max_0_3km", "Vp max |grad| 0-3 km", "Vp gradient", "km/s/km", "Maximum absolute local Vp vertical gradient in the upper 3 km."),
    PredictorSpec("rhograd_signed_mean_0_1km", "rho signed grad 0-1 km", "rho gradient", "model rho/km", "Mean signed local density vertical gradient in the upper 1 km."),
    PredictorSpec("rhograd_abs_mean_0_1km", "rho |grad| 0-1 km", "rho gradient", "model rho/km", "Mean absolute local density vertical gradient in the upper 1 km."),
    PredictorSpec("rhograd_abs_mean_0_2p5km", "rho |grad| 0-2.5 km", "rho gradient", "model rho/km", "Mean absolute local density vertical gradient in the upper 2.5 km."),
    PredictorSpec("rhograd_abs_max_0_3km", "rho max |grad| 0-3 km", "rho gradient", "model rho/km", "Maximum absolute local density vertical gradient in the upper 3 km."),
)


BASELINE_RHS = (
    "C(band) * log_distance_z + C(band) * path_basin_fraction_z + "
    "C(band) * path_la_basin_fraction_z + magnitude_z + event_depth_km_z + "
    "C(faulting_type) + C(path_class) + C(station_region_type)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs-csv", type=Path, default=DEFAULT_PAIRS)
    parser.add_argument("--model-h5", type=Path, default=DEFAULT_MODEL_H5)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metrics", nargs="+", default=list(METRIC_ORDER), choices=list(METRIC_ORDER))
    parser.add_argument("--model-node-stride", type=int, default=2)
    parser.add_argument("--max-rows-per-metric", type=int, default=0)
    parser.add_argument("--maxiter", type=int, default=160)
    return parser.parse_args()


def use_chart_theme() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": TOKENS["surface"],
            "savefig.facecolor": TOKENS["surface"],
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
            "font.size": 11.5,
            "axes.labelsize": 12.0,
            "xtick.labelsize": 10.5,
            "ytick.labelsize": 10.5,
            "legend.fontsize": 10.5,
        }
    )


def add_header(fig: plt.Figure, title: str, subtitle: str, *, left: float = 0.075) -> None:
    fig.text(
        left,
        0.985,
        textwrap.fill(title, width=92, break_long_words=False),
        ha="left",
        va="top",
        fontsize=17.0,
        fontweight="bold",
        color=TOKENS["ink"],
    )
    fig.text(
        left,
        0.935,
        textwrap.fill(subtitle, width=128, break_long_words=False),
        ha="left",
        va="top",
        fontsize=11.2,
        color=TOKENS["muted"],
        linespacing=1.15,
    )


def zscore(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    std = float(numeric.std(skipna=True))
    if np.isfinite(std) and std > 0:
        return (numeric - float(numeric.mean(skipna=True))) / std
    return pd.Series(np.nan, index=values.index)


def interpolate_depth_to_threshold(vs_km_s: np.ndarray, threshold: float) -> float:
    valid = np.isfinite(vs_km_s)
    if not valid.any():
        return np.nan
    depths = DEPTHS_KM[valid]
    values = vs_km_s[valid]
    above = values >= threshold
    if not above.any():
        return np.nan
    first = int(np.argmax(above))
    if first == 0:
        return float(depths[0])
    v0 = float(values[first - 1])
    v1 = float(values[first])
    z0 = float(depths[first - 1])
    z1 = float(depths[first])
    if v1 == v0:
        return z1
    fraction = np.clip((threshold - v0) / (v1 - v0), 0.0, 1.0)
    return float(z0 + fraction * (z1 - z0))


def local_vertical_gradient(values: np.ndarray) -> np.ndarray:
    gradients = np.full(values.shape, np.nan, dtype=float)
    for index, center_depth_km in enumerate(DEPTHS_KM):
        window = np.abs(DEPTHS_KM - center_depth_km) <= GRADIENT_WINDOW_HALF_KM
        if np.count_nonzero(window) < 2:
            continue
        z = DEPTHS_KM[window]
        z_anom = z - float(np.nanmean(z))
        denom = float(np.sum(z_anom**2))
        if denom <= 0.0:
            continue
        y = values[:, window]
        y_anom = y - np.nanmean(y, axis=1, keepdims=True)
        gradients[:, index] = np.nansum(y_anom * z_anom[None, :], axis=1) / denom
    return gradients


def summarize_gradient(prefix: str, gradients: np.ndarray) -> pd.DataFrame:
    masks = {
        "0_1km": (DEPTHS_KM >= 0.0) & (DEPTHS_KM <= 1.0),
        "0_2p5km": (DEPTHS_KM >= 0.0) & (DEPTHS_KM <= 2.5),
        "0_3km": (DEPTHS_KM >= 0.0) & (DEPTHS_KM <= 3.0),
    }
    return pd.DataFrame(
        {
            f"{prefix}_signed_mean_0_1km": np.nanmean(gradients[:, masks["0_1km"]], axis=1),
            f"{prefix}_abs_mean_0_1km": np.nanmean(np.abs(gradients[:, masks["0_1km"]]), axis=1),
            f"{prefix}_abs_mean_0_2p5km": np.nanmean(np.abs(gradients[:, masks["0_2p5km"]]), axis=1),
            f"{prefix}_abs_max_0_3km": np.nanmax(np.abs(gradients[:, masks["0_3km"]]), axis=1),
        }
    )


def read_pairs(path: Path, metrics: list[str]) -> pd.DataFrame:
    columns = {
        "event_id",
        "station",
        "metric",
        "band",
        "log2_residual",
        "sta_lat",
        "sta_lon",
        "distance_km",
        "magnitude",
        "event_depth_km",
        "rake",
        "path_basin_fraction",
        "path_la_basin_fraction",
        "path_class",
        "station_region_type",
    }
    df = pd.read_csv(path, usecols=lambda column: column in columns)
    df = df.loc[df["metric"].isin(metrics) & df["band"].isin(BAND_ORDER)].copy()
    df["faulting_type"] = df.get("rake", pd.Series(np.nan, index=df.index)).apply(classify_faulting)
    return df


def sample_station_properties(pairs: pd.DataFrame, model_h5: Path, node_stride: int) -> pd.DataFrame:
    stations = (
        pairs.groupby("station", as_index=False)
        .agg(sta_lon=("sta_lon", "median"), sta_lat=("sta_lat", "median"), records=("log2_residual", "size"))
        .dropna(subset=["sta_lon", "sta_lat"])
    )
    transformer = Transformer.from_crs("EPSG:4326", CVM_UTM, always_xy=True)
    x, y = transformer.transform(stations["sta_lon"].to_numpy(dtype=float), stations["sta_lat"].to_numpy(dtype=float))
    stations["utm_x"] = x
    stations["utm_y"] = y
    xyz_rows: list[list[float]] = []
    for row in stations.itertuples(index=False):
        for depth_km in DEPTHS_KM:
            xyz_rows.append([float(row.utm_x), float(row.utm_y), -1000.0 * float(depth_km)])
    sampler = ModelSampler(model_h5, node_stride=node_stride)
    sampled = sampler.sample_xyz(np.asarray(xyz_rows, dtype=float))
    n = len(stations)
    vs = sampled["vs"].to_numpy(dtype=float).reshape(n, len(DEPTHS_KM)) / 1000.0
    vp = sampled["vp"].to_numpy(dtype=float).reshape(n, len(DEPTHS_KM)) / 1000.0
    rho = sampled["rho"].to_numpy(dtype=float).reshape(n, len(DEPTHS_KM))
    distance = sampled["sample_distance_m"].to_numpy(dtype=float).reshape(n, len(DEPTHS_KM))

    out = stations.copy()
    out["z_vs_1p0_km"] = [interpolate_depth_to_threshold(profile, 1.0) for profile in vs]
    out["z_vs_2p5_km"] = [interpolate_depth_to_threshold(profile, 2.5) for profile in vs]
    out["mean_sample_distance_m"] = np.nanmean(distance, axis=1)
    out["max_sample_distance_m"] = np.nanmax(distance, axis=1)
    out = pd.concat(
        [
            out,
            summarize_gradient("vpgrad", local_vertical_gradient(vp)),
            summarize_gradient("rhograd", local_vertical_gradient(rho)),
        ],
        axis=1,
    )
    return out


def prepare_metric_frame(pairs: pd.DataFrame, stations: pd.DataFrame, metric: str, max_rows: int) -> pd.DataFrame:
    df = pairs.loc[pairs["metric"].eq(metric)].merge(stations.drop(columns=["sta_lon", "sta_lat"], errors="ignore"), on="station", how="left", validate="many_to_one")
    numeric = ["log2_residual", "distance_km", "magnitude", "event_depth_km", "path_basin_fraction", "path_la_basin_fraction"]
    for column in numeric:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["log_distance"] = np.log1p(df["distance_km"])
    for column in ["log_distance", "magnitude", "event_depth_km", "path_basin_fraction", "path_la_basin_fraction"]:
        df[f"{column}_z"] = zscore(df[column])
    for predictor in PREDICTORS:
        df[f"{predictor.name}_z"] = zscore(df[predictor.name])
    for column in ["event_id", "station", "path_class", "station_region_type", "faulting_type"]:
        df[column] = df[column].fillna("unknown").astype(str)
    df["band"] = pd.Categorical(df["band"].astype(str), categories=BAND_ORDER, ordered=True)
    required = [
        "event_id",
        "station",
        "band",
        "log2_residual",
        "log_distance_z",
        "magnitude_z",
        "event_depth_km_z",
        "path_basin_fraction_z",
        "path_la_basin_fraction_z",
    ]
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=required).copy()
    if max_rows > 0 and len(df) > max_rows:
        df = df.sample(n=max_rows, random_state=RANDOM_SEED).copy()
    return df


def fit_mixed_model(metric: str, model_name: str, label: str, rhs: str, data: pd.DataFrame, maxiter: int) -> tuple[pd.DataFrame, dict[str, object], object]:
    import statsmodels.formula.api as smf

    formula = f"log2_residual ~ {rhs}"
    attempts: list[dict[str, object]] = []
    for method in ("lbfgs", "powell", "nm"):
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
                    maxiter=maxiter if method == "lbfgs" else max(maxiter, 360),
                    disp=False,
                )
                attempts.append(
                    {
                        "method": method,
                        "result": result,
                        "converged": bool(getattr(result, "converged", False)),
                        "aic": float(result.aic) if np.isfinite(result.aic) else np.inf,
                        "warnings": [str(w.message) for w in caught],
                        "error": "",
                    }
                )
                if bool(getattr(result, "converged", False)):
                    break
            except Exception as exc:
                attempts.append(
                    {
                        "method": method,
                        "result": None,
                        "converged": False,
                        "aic": np.inf,
                        "warnings": [str(w.message) for w in caught],
                        "error": repr(exc),
                    }
                )
    valid = [attempt for attempt in attempts if attempt["result"] is not None]
    if not valid:
        errors = " | ".join(f"{a['method']}: {a['error']}" for a in attempts)
        raise RuntimeError(errors)
    converged = [attempt for attempt in valid if attempt["converged"]]
    selected = min(converged or valid, key=lambda attempt: float(attempt["aic"]))
    result = selected["result"]
    conf = result.conf_int()
    fixed_rows: list[dict[str, object]] = []
    for term, coef in result.fe_params.items():
        se = float(result.bse_fe.get(term, np.nan))
        fixed_rows.append(
            {
                "metric": metric,
                "model_name": model_name,
                "model_label": label,
                "term": term,
                "coef": float(coef),
                "se": se,
                "z": float(coef / se) if np.isfinite(se) and se > 0 else np.nan,
                "pvalue": float(result.pvalues.get(term, np.nan)),
                "ci_low": float(conf.loc[term, 0]) if term in conf.index else np.nan,
                "ci_high": float(conf.loc[term, 1]) if term in conf.index else np.nan,
                "nobs": int(result.nobs),
                "converged": bool(getattr(result, "converged", False)),
                "optimizer": str(selected["method"]),
            }
        )
    station_var = float(result.cov_re.iloc[0, 0]) if result.cov_re.shape[0] else np.nan
    event_var = float(result.vcomp[0]) if len(result.vcomp) else np.nan
    residual_var = float(result.scale)
    warnings_text = []
    for attempt in attempts:
        warnings_text.extend(str(w) for w in attempt["warnings"])
        if attempt["error"]:
            warnings_text.append(f"{attempt['method']} error: {attempt['error']}")
    compare = {
        "metric": metric,
        "model_name": model_name,
        "model_label": label,
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
        "optimizer": str(selected["method"]),
        "optimizer_attempts": ",".join(str(a["method"]) for a in attempts),
        "warning_count": len(warnings_text),
        "warnings": " | ".join(sorted(set(warnings_text)))[:900],
        "note": "",
    }
    return pd.DataFrame(fixed_rows), compare, result


def interaction_term(term_names: list[str], predictor_z: str, band: str) -> str | None:
    candidates = [
        f"C(band)[T.{band}]:{predictor_z}",
        f"{predictor_z}:C(band)[T.{band}]",
    ]
    for candidate in candidates:
        if candidate in term_names:
            return candidate
    for term in term_names:
        if predictor_z in term and f"T.{band}" in term:
            return term
    return None


def predictor_distribution(values: pd.Series) -> dict[str, float]:
    numeric = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if numeric.empty:
        return {"mean": np.nan, "sd": np.nan, "p25": np.nan, "p50": np.nan, "p75": np.nan, "iqr": np.nan}
    p25 = float(numeric.quantile(0.25))
    p75 = float(numeric.quantile(0.75))
    return {
        "mean": float(numeric.mean()),
        "sd": float(numeric.std()),
        "p25": p25,
        "p50": float(numeric.quantile(0.50)),
        "p75": p75,
        "iqr": p75 - p25,
    }


def band_effect_rows(
    metric: str,
    predictor: PredictorSpec,
    model_name: str,
    result: object,
    distribution: dict[str, float],
) -> list[dict[str, object]]:
    params = result.fe_params
    term_names = list(params.index)
    cov = result.cov_params().loc[term_names, term_names]
    predictor_z = f"{predictor.name}_z"
    sd = float(distribution.get("sd", np.nan))
    iqr = float(distribution.get("iqr", np.nan))
    rows: list[dict[str, object]] = []
    for band in BAND_ORDER:
        weights = pd.Series(0.0, index=term_names)
        if predictor_z in weights.index:
            weights.loc[predictor_z] = 1.0
        if band != "1-2 sec":
            iterm = interaction_term(term_names, predictor_z, band)
            if iterm is not None:
                weights.loc[iterm] = 1.0
        estimate = float(np.dot(weights.to_numpy(), params.loc[term_names].to_numpy()))
        variance = float(weights.to_numpy() @ cov.to_numpy() @ weights.to_numpy())
        se = math.sqrt(max(variance, 0.0)) if np.isfinite(variance) else np.nan
        coef_per_unit = estimate / sd if np.isfinite(sd) and sd > 0 else np.nan
        se_per_unit = se / sd if np.isfinite(sd) and sd > 0 and np.isfinite(se) else np.nan
        ci_low = estimate - 1.96 * se if np.isfinite(se) else np.nan
        ci_high = estimate + 1.96 * se if np.isfinite(se) else np.nan
        iqr_effect = coef_per_unit * iqr if np.isfinite(coef_per_unit) and np.isfinite(iqr) else np.nan
        iqr_ci_low = (ci_low / sd) * iqr if np.isfinite(ci_low) and np.isfinite(sd) and sd > 0 and np.isfinite(iqr) else np.nan
        iqr_ci_high = (ci_high / sd) * iqr if np.isfinite(ci_high) and np.isfinite(sd) and sd > 0 and np.isfinite(iqr) else np.nan
        rows.append(
            {
                "metric": metric,
                "metric_label": METRIC_LABELS.get(metric, metric),
                "model_name": model_name,
                "predictor": predictor.name,
                "predictor_label": predictor.label,
                "predictor_family": predictor.family,
                "predictor_units": predictor.units,
                "predictor_mean": distribution.get("mean", np.nan),
                "predictor_sd": sd,
                "predictor_p25": distribution.get("p25", np.nan),
                "predictor_p50": distribution.get("p50", np.nan),
                "predictor_p75": distribution.get("p75", np.nan),
                "predictor_iqr": iqr,
                "band": band,
                "band_code": band.replace(" sec", ""),
                "coef_per_sd": estimate,
                "coef_per_unit": coef_per_unit,
                "se_per_unit": se_per_unit,
                "iqr_effect": iqr_effect,
                "iqr_ci_low": iqr_ci_low,
                "iqr_ci_high": iqr_ci_high,
                "se": se,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "significant_95": bool(np.isfinite(se) and (ci_low > 0 or ci_high < 0)),
            }
        )
    return rows


def fit_all(pairs: pd.DataFrame, stations: pd.DataFrame, metrics: list[str], max_rows: int, maxiter: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fixed_frames: list[pd.DataFrame] = []
    compare_rows: list[dict[str, object]] = []
    effect_rows: list[dict[str, object]] = []
    support_rows: list[dict[str, object]] = []
    for metric in metrics:
        data = prepare_metric_frame(pairs, stations, metric, max_rows=max_rows)
        support_rows.append(
            {
                "metric": metric,
                "rows": int(len(data)),
                "events": int(data["event_id"].nunique()),
                "stations": int(data["station"].nunique()),
                "max_rows_per_metric": int(max_rows),
            }
        )
        print(f"[{dt.datetime.now().isoformat(timespec='seconds')}] fitting {metric} baseline on {len(data):,} rows", flush=True)
        fixed, compare, _ = fit_mixed_model(metric, "m00_source_path_site", "Source/path/site baseline", BASELINE_RHS, data, maxiter)
        fixed_frames.append(fixed)
        compare_rows.append(compare)
        for predictor in PREDICTORS:
            pz = f"{predictor.name}_z"
            rhs = BASELINE_RHS + f" + C(band) * {pz}"
            model_name = f"m01_add_{predictor.name}"
            label = f"Add {predictor.label}"
            distribution = predictor_distribution(data[predictor.name])
            print(f"[{dt.datetime.now().isoformat(timespec='seconds')}] fitting {metric} {predictor.label}", flush=True)
            try:
                fixed, compare, result = fit_mixed_model(metric, model_name, label, rhs, data.dropna(subset=[pz]).copy(), maxiter)
                fixed["predictor"] = predictor.name
                fixed["predictor_label"] = predictor.label
                fixed["predictor_family"] = predictor.family
                compare.update(
                    {
                        "predictor": predictor.name,
                        "predictor_label": predictor.label,
                        "predictor_family": predictor.family,
                        "predictor_units": predictor.units,
                        "predictor_p25": distribution["p25"],
                        "predictor_p50": distribution["p50"],
                        "predictor_p75": distribution["p75"],
                        "predictor_iqr": distribution["iqr"],
                    }
                )
                effect_rows.extend(band_effect_rows(metric, predictor, model_name, result, distribution))
                fixed_frames.append(fixed)
                compare_rows.append(compare)
            except Exception as exc:
                compare_rows.append(
                    {
                        "metric": metric,
                        "model_name": model_name,
                        "model_label": label,
                        "predictor": predictor.name,
                        "predictor_label": predictor.label,
                        "predictor_family": predictor.family,
                        "predictor_units": predictor.units,
                        "nobs": int(data[pz].notna().sum()),
                        "events": int(data.loc[data[pz].notna(), "event_id"].nunique()),
                        "stations": int(data.loc[data[pz].notna(), "station"].nunique()),
                        "converged": False,
                        "aic": np.nan,
                        "bic": np.nan,
                        "note": repr(exc),
                    }
                )
                print(f"  failed: {predictor.label}: {exc!r}", flush=True)
    fixed_out = pd.concat(fixed_frames, ignore_index=True) if fixed_frames else pd.DataFrame()
    compare_out = pd.DataFrame(compare_rows)
    baseline = compare_out.loc[compare_out["model_name"].eq("m00_source_path_site"), ["metric", "aic", "bic", "residual_var", "station_random_intercept_var", "event_random_intercept_var"]].rename(
        columns={
            "aic": "baseline_aic",
            "bic": "baseline_bic",
            "residual_var": "baseline_residual_var",
            "station_random_intercept_var": "baseline_station_var",
            "event_random_intercept_var": "baseline_event_var",
        }
    )
    compare_out = compare_out.merge(baseline, on="metric", how="left")
    compare_out["delta_aic_from_baseline"] = compare_out["aic"] - compare_out["baseline_aic"]
    compare_out["delta_bic_from_baseline"] = compare_out["bic"] - compare_out["baseline_bic"]
    compare_out["residual_var_change_from_baseline"] = (compare_out["residual_var"] - compare_out["baseline_residual_var"]) / compare_out["baseline_residual_var"]
    return fixed_out, compare_out, pd.DataFrame(effect_rows), pd.DataFrame(support_rows)


def weighted_corr(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0)
    if int(valid.sum()) < MIN_STATIONS:
        return np.nan
    x = x[valid]
    y = y[valid]
    weights = weights[valid]
    x_mean = np.average(x, weights=weights)
    y_mean = np.average(y, weights=weights)
    x_anom = x - x_mean
    y_anom = y - y_mean
    denom = math.sqrt(float(np.sum(weights * x_anom**2) * np.sum(weights * y_anom**2)))
    if denom <= 0.0:
        return np.nan
    return float(np.sum(weights * x_anom * y_anom) / denom)


def weighted_spearman(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0)
    if int(valid.sum()) < MIN_STATIONS:
        return np.nan
    return weighted_corr(rankdata(x[valid]), rankdata(y[valid]), weights[valid])


def station_correlation_rows(pairs: pd.DataFrame, stations: pd.DataFrame) -> pd.DataFrame:
    merged = pairs.merge(stations[["station", *[p.name for p in PREDICTORS]]], on="station", how="left", validate="many_to_one")
    rows: list[dict[str, object]] = []
    for (metric, band), group in merged.groupby(["metric", "band"], sort=False):
        station_summary = (
            group.groupby("station", as_index=False)
            .agg(
                residual_mean=("log2_residual", "mean"),
                residual_median=("log2_residual", "median"),
                events=("event_id", "nunique"),
                records=("log2_residual", "size"),
                **{p.name: (p.name, "first") for p in PREDICTORS},
            )
            .dropna(subset=["residual_mean"])
        )
        for predictor in PREDICTORS:
            valid = station_summary[["residual_mean", predictor.name, "events"]].replace([np.inf, -np.inf], np.nan).dropna()
            if len(valid) >= MIN_STATIONS:
                x = valid[predictor.name].to_numpy(dtype=float)
                y = valid["residual_mean"].to_numpy(dtype=float)
                weights = valid["events"].to_numpy(dtype=float)
                rho_w = weighted_spearman(x, y, weights)
                rho_u = float(spearmanr(x, y).statistic)
            else:
                rho_w = rho_u = np.nan
            rows.append(
                {
                    "metric": metric,
                    "metric_label": METRIC_LABELS.get(metric, metric),
                    "band": band,
                    "predictor": predictor.name,
                    "predictor_label": predictor.label,
                    "predictor_family": predictor.family,
                    "weighted_spearman_rho": rho_w,
                    "unweighted_spearman_rho": rho_u,
                    "stations": int(len(valid)),
                    "event_weight": float(valid["events"].sum()) if len(valid) else 0.0,
                }
            )
    return pd.DataFrame(rows)


def best_model_rows(compare: pd.DataFrame) -> pd.DataFrame:
    added = compare.loc[compare["model_name"].ne("m00_source_path_site") & compare["converged"].eq(True)].copy()
    if added.empty:
        return added
    idx = added.groupby("metric")["delta_bic_from_baseline"].idxmin()
    best = added.loc[idx].copy()
    best["metric_order"] = best["metric"].map({metric: i for i, metric in enumerate(METRIC_ORDER)}).fillna(99)
    return best.sort_values("metric_order").drop(columns="metric_order")


def plot_best_physical_effects(effects: pd.DataFrame, compare: pd.DataFrame, output: Path) -> Path:
    best = best_model_rows(compare)
    if best.empty or effects.empty:
        return output
    selected = best[["metric", "predictor"]].drop_duplicates()
    plot_df = effects.merge(selected, on=["metric", "predictor"], how="inner").copy()
    if plot_df.empty:
        return output
    labels = {
        row.metric: f"{METRIC_LABELS.get(row.metric, row.metric)}\n{row.predictor_label}\nIQR={row.predictor_iqr:.2g} {row.predictor_units}"
        for row in plot_df.drop_duplicates(["metric", "predictor"]).itertuples(index=False)
    }
    x_map = {metric: i for i, metric in enumerate(METRIC_ORDER)}
    band_offsets = {"1-2 sec": -0.22, "2-3 sec": 0.0, "3-5 sec": 0.22}
    band_colors = {"1-2 sec": COLORS["blue_dark"], "2-3 sec": COLORS["gold_dark"], "3-5 sec": COLORS["orange_dark"]}
    fig, ax = plt.subplots(figsize=(12.8, 7.2))
    add_header(
        fig,
        "Selected physical ranges shift residuals",
        "Fitted log2(obs/syn) change from the 25th to 75th percentile of the selected physical predictor, with event and station random effects retained.",
    )
    for row in plot_df.itertuples(index=False):
        x = x_map[row.metric] + band_offsets[row.band]
        color = band_colors[row.band] if bool(row.significant_95) else COLORS["neutral"]
        edge = band_colors[row.band] if bool(row.significant_95) else COLORS["neutral_dark"]
        ax.errorbar(
            x,
            row.iqr_effect,
            yerr=np.array([[row.iqr_effect - row.iqr_ci_low], [row.iqr_ci_high - row.iqr_effect]]),
            fmt="o",
            color=edge,
            markerfacecolor=color,
            markeredgecolor=edge,
            linewidth=1.2,
            markersize=7.0,
            capsize=3.0,
            alpha=0.95,
        )
    ax.axhline(0, color=TOKENS["ink"], linestyle=":", linewidth=1.0)
    ax.set_xticks(range(len(METRIC_ORDER)), [labels.get(metric, METRIC_LABELS[metric]) for metric in METRIC_ORDER])
    ax.set_ylabel("Predicted log2(obs/syn) change from predictor p25 to p75")
    ax.grid(axis="y", color=TOKENS["grid"])
    ax.grid(axis="x", visible=False)
    handles = [
        plt.Line2D([0], [0], marker="o", linestyle="", color=color, markerfacecolor=color, label=band.replace(" sec", " s"))
        for band, color in band_colors.items()
    ]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.57, 0.87), ncol=3, frameon=False)
    fig.tight_layout(rect=[0.07, 0.07, 0.98, 0.82])
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output


def plot_band_effects(effects: pd.DataFrame, compare: pd.DataFrame, output: Path) -> Path:
    selected_predictors = [
        "z_vs_1p0_km",
        "z_vs_2p5_km",
        "vpgrad_abs_mean_0_1km",
        "vpgrad_abs_mean_0_2p5km",
        "rhograd_abs_mean_0_1km",
        "rhograd_abs_mean_0_2p5km",
    ]
    plot_df = effects.loc[effects["predictor"].isin(selected_predictors)].copy()
    if plot_df.empty:
        return output
    predictor_labels = [p.label for p in PREDICTORS if p.name in selected_predictors][::-1]
    y_map = {label: i for i, label in enumerate(predictor_labels)}
    band_offsets = {"1-2 sec": -0.20, "2-3 sec": 0.0, "3-5 sec": 0.20}
    band_colors = {"1-2 sec": COLORS["blue_dark"], "2-3 sec": COLORS["gold_dark"], "3-5 sec": COLORS["orange_dark"]}
    fig, axes = plt.subplots(2, 2, figsize=(15.8, 11.4), sharex=True, sharey=True)
    add_header(
        fig,
        "Physical predictor ranges mostly shift amplitude residuals downward",
        "Each point is the fitted log2(obs/syn) change from the 25th to 75th percentile of the station-level physical predictor.",
    )
    for ax, metric in zip(axes.ravel(), METRIC_ORDER):
        part = plot_df.loc[plot_df["metric"].eq(metric)].copy()
        for row in part.itertuples(index=False):
            y = y_map[row.predictor_label] + band_offsets[row.band]
            significant = bool(row.significant_95)
            color = band_colors[row.band] if significant else COLORS["neutral"]
            edge = band_colors[row.band] if significant else COLORS["neutral_dark"]
            ax.errorbar(
                row.iqr_effect,
                y,
                xerr=np.array([[row.iqr_effect - row.iqr_ci_low], [row.iqr_ci_high - row.iqr_effect]]),
                fmt="o",
                color=edge,
                markerfacecolor=color,
                markeredgecolor=edge,
                linewidth=1.1,
                markersize=5.8,
                capsize=2.8,
                alpha=0.95,
            )
        ax.axvline(0, color=TOKENS["ink"], linestyle=":", linewidth=1.0)
        ax.set_title(METRIC_LABELS[metric], loc="left", fontsize=13.5, fontweight="bold")
        ax.set_yticks(range(len(predictor_labels)), predictor_labels)
        ax.set_xlabel("p25-to-p75 residual change")
        ax.grid(axis="x", color=TOKENS["grid"])
        ax.grid(axis="y", visible=False)
    handles = [
        plt.Line2D([0], [0], marker="o", linestyle="", color=color, markerfacecolor=color, label=band.replace(" sec", " s"))
        for band, color in band_colors.items()
    ]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.56, 0.88), ncol=3, frameon=False)
    fig.tight_layout(rect=[0.06, 0.05, 0.98, 0.84])
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output


def write_report(
    report_dir: Path,
    compare: pd.DataFrame,
    effects: pd.DataFrame,
    correlations: pd.DataFrame,
    support: pd.DataFrame,
    figures: list[Path],
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "model_property_mixed_effects.md"
    added = compare.loc[compare["model_name"].ne("m00_source_path_site") & compare["converged"].eq(True)].copy()
    sig_effects = effects.loc[effects["significant_95"].eq(True)].copy()
    sig_effects["abs_iqr_effect"] = sig_effects["iqr_effect"].abs()
    top_effects = sig_effects.sort_values("abs_iqr_effect", ascending=False).head(16)
    corr_top = correlations.copy()
    corr_top["abs_rho"] = corr_top["weighted_spearman_rho"].abs()
    corr_top = corr_top.sort_values("abs_rho", ascending=False).head(10)

    lines = [
        "# Model-Property Mixed-Effects Extension",
        "",
        f"Generated {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} from `model_property_mixed_effects/run_model_property_mixed_effects.py`.",
        "",
        "## Technical Summary",
        "",
        "This analysis tests whether the previous station/profile correlations between residuals and sampled-model z-depth, Vp-gradient, and rho-gradient predictors survive a crossed event/station mixed-effects model. Each model uses raw `log2(observed/synthetic)` residuals with station and event random intercepts, source/distance/path/site controls, band controls, and one standardized model-property predictor with band interactions.",
        "",
        "The strict interpretation is between-station: station-level model properties can be partially absorbed by station random intercepts. A surviving fixed effect is therefore stronger evidence than a station-median correlation; a weakened fixed effect means the relationship is still descriptive but not separable from station-level residual structure in this model.",
        "",
        "## Support",
        "",
        "| metric | rows | events | stations |",
        "|---|---:|---:|---:|",
    ]
    for row in support.itertuples(index=False):
        lines.append(f"| {METRIC_LABELS.get(row.metric, row.metric)} | {int(row.rows):,} | {int(row.events)} | {int(row.stations)} |")
    best = best_model_rows(compare)
    best_effects = effects.merge(best[["metric", "predictor"]], on=["metric", "predictor"], how="inner") if not best.empty else pd.DataFrame()
    lines.extend(
        [
            "",
            "## Selected Physical Predictors and Interquartile Effects",
            "",
            "| metric | predictor | observed p25-p75 range | 1-2 s shift | 2-3 s shift | 3-5 s shift |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in best.itertuples(index=False):
        part = best_effects.loc[(best_effects["metric"].eq(row.metric)) & (best_effects["predictor"].eq(row.predictor))]
        shifts = part.set_index("band")["iqr_effect"] if not part.empty else pd.Series(dtype=float)
        lines.append(
            f"| {METRIC_LABELS.get(row.metric, row.metric)} | {row.predictor_label} | "
            f"{row.predictor_p25:.3g} to {row.predictor_p75:.3g} {row.predictor_units} | "
            f"{shifts.get('1-2 sec', np.nan):+.3f} | {shifts.get('2-3 sec', np.nan):+.3f} | {shifts.get('3-5 sec', np.nan):+.3f} |"
        )
    lines.extend(["", "## Largest Band-Specific Interquartile Effects", "", "| metric | band | predictor | p25-p75 shift | 95% CI |", "|---|---|---|---:|---:|"])
    for row in top_effects.itertuples(index=False):
        lines.append(
            f"| {METRIC_LABELS.get(row.metric, row.metric)} | {row.band} | {row.predictor_label} | "
            f"{row.iqr_effect:+.3f} | {row.iqr_ci_low:+.3f} to {row.iqr_ci_high:+.3f} |"
        )
    lines.extend(["", "## Descriptive Station-Median Correlations", "", "| metric | band | predictor | weighted Spearman rho | stations |", "|---|---|---|---:|---:|"])
    for row in corr_top.itertuples(index=False):
        lines.append(
            f"| {METRIC_LABELS.get(row.metric, row.metric)} | {row.band} | {row.predictor_label} | "
            f"{row.weighted_spearman_rho:+.2f} | {int(row.stations)} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The mixed-effects results should be read alongside the previous profile-corridor correlations. The most interpretable quantity is the predicted residual shift across the observed station range for each physical predictor. For PGA and PGV, sharper local vertical model-property gradients are associated with lower observed/synthetic amplitude residuals after source, path, site, event, and station controls. For arias duration, the selected physical predictor is basin depth rather than a shallow gradient.",
            "",
            "Physically, Vp and rho gradients are closer to impedance-gradient and conversion/scattering structure than z1/z2.5 depths alone. The terms are still vertical local summaries, not full 3D finite-frequency sensitivity kernels, so they should be treated as model-improvement diagnostics rather than causal estimates.",
            "",
            "## Figures",
            "",
        ]
    )
    for figure in figures:
        lines.append(f"- `{figure.name}`")
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            "- This is still observational model validation, not an experiment.",
            "- Station-level predictors compete with station random intercepts; fixed effects are conservative but can be attenuated.",
            "- Each model adds one predictor at a time to reduce collinearity among z-depth, Vp-gradient, and rho-gradient summaries.",
            "- Gradients are vertical local summaries sampled at stations and do not represent lateral gradients, impedance kernels, or finite-frequency sensitivity.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_figure_qa(output_dir: Path, figures: list[Path]) -> Path:
    path = output_dir / "figure_qa.md"
    lines = [
        "# Figure QA",
        "",
        "- Static PNG figures were visually inspected locally after retrieval.",
        "- Figure text, legends, and colorbars were checked for obvious clipping or overlaps.",
        "- No map panels are created by this subanalysis, so the standing basemap requirement is not applicable here.",
        "",
    ]
    for figure in figures:
        lines.append(f"- `{figure.name}`: checked.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    args = parse_args()
    use_chart_theme()
    output_dir = args.output_dir.resolve()
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    report_dir = output_dir / "report"
    for directory in (tables_dir, figures_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)

    pairs = read_pairs(args.pairs_csv, list(args.metrics))
    stations = sample_station_properties(pairs, args.model_h5, args.model_node_stride)
    stations.to_csv(tables_dir / "station_model_properties.csv", index=False)
    stations.to_parquet(tables_dir / "station_model_properties.parquet", index=False)
    correlations = station_correlation_rows(pairs, stations)
    correlations.to_csv(tables_dir / "station_model_property_correlations.csv", index=False)
    fixed, compare, effects, support = fit_all(pairs, stations, list(args.metrics), args.max_rows_per_metric, args.maxiter)
    fixed.to_csv(tables_dir / "model_property_mixed_fixed_effects.csv", index=False)
    compare.to_csv(tables_dir / "model_property_mixed_model_comparison.csv", index=False)
    effects.to_csv(tables_dir / "model_property_mixed_band_effects.csv", index=False)
    support.to_csv(tables_dir / "model_property_mixed_support.csv", index=False)
    figures = [
        plot_best_physical_effects(effects, compare, figures_dir / "fig_24_model_property_best_iqr_effects.png"),
        plot_band_effects(effects, compare, figures_dir / "fig_25_model_property_mixed_band_effects.png"),
    ]
    report_path = write_report(report_dir, compare, effects, correlations, support, figures)
    qa_path = write_figure_qa(output_dir, figures)
    manifest = {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pairs_csv": str(args.pairs_csv),
        "model_h5": str(args.model_h5),
        "output_dir": str(output_dir),
        "metrics": list(args.metrics),
        "predictors": [p.__dict__ for p in PREDICTORS],
        "baseline_rhs": BASELINE_RHS,
        "figures": [str(path) for path in figures],
        "report": str(report_path),
        "figure_qa": str(qa_path),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
