#!/usr/bin/env python3
"""Second-pass interaction scan for CVM-SI residual hypotheses.

This is private research code. It assumes the first-pass
``cvmsi_hypothesis_study.py`` workflow has already written pair-level outputs,
then adds broader source/path/site/frequency/component/support analyses without
changing the public spatial-vtk package API.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import textwrap
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
from pyproj import Transformer

try:
    import seaborn as sns
except Exception:  # pragma: no cover - environment dependent
    sns = None


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

DEFAULT_ANALYSIS_ROOT = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/analysis/cvmsi_hypothesis_study")
DEFAULT_OUTPUT = DEFAULT_ANALYSIS_ROOT / "extended"
DEFAULT_METRICS = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/tables/metrics_final_enriched.parquet")
DEFAULT_MODEL = "cvmsi_20260506_material_0p6x1p2_asdf"
DEFAULT_METRIC_SET = ("PGA", "PGV", "arias_duration", "energy_intensity")
DEFAULT_COMPONENT_METRICS = ("PGA", "PGV")
DEFAULT_BANDS = ("1-2 sec", "2-3 sec", "3-5 sec")
WGS84 = "EPSG:4326"
WEB_MERCATOR = "EPSG:3857"
DEFAULT_BASEMAP_SOURCE = "CartoDB.Positron"
DEFAULT_BASEMAP_ZOOM = 9
RANDOM_SEED = 20260701

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}

NEUTRAL_MARKS = {
    "open": TOKENS["panel"],
    "xlight": "#F4F5F7",
    "light": "#E2E5EA",
    "base": "#C5CAD3",
    "mid": "#7A828F",
    "dark": "#464C55",
}

COLOR_FAMILIES = {
    "blue": {"open": TOKENS["panel"], "xlight": "#EAF1FE", "light": "#CEDFFE", "base": "#A3BEFA", "mid": "#5477C4", "dark": "#2E4780"},
    "gold": {"open": TOKENS["panel"], "xlight": "#FFF4C2", "light": "#FFEA8F", "base": "#FFE15B", "mid": "#B8A037", "dark": "#736422"},
    "orange": {"open": TOKENS["panel"], "xlight": "#FFEDDE", "light": "#FFBDA1", "base": "#F0986E", "mid": "#CC6F47", "dark": "#804126"},
    "olive": {"open": TOKENS["panel"], "xlight": "#D8ECBD", "light": "#BEEB96", "base": "#A3D576", "mid": "#71B436", "dark": "#386411"},
    "pink": {"open": TOKENS["panel"], "xlight": "#FCDAD6", "light": "#F5BACC", "base": "#F390CA", "mid": "#BD569B", "dark": "#8A3A6F"},
}

PATH_COLORS = {
    "LA basin local": COLOR_FAMILIES["blue"]["mid"],
    "terminates in LA basin": COLOR_FAMILIES["blue"]["base"],
    "crosses LA basin": COLOR_FAMILIES["gold"]["base"],
    "other basin-influenced": COLOR_FAMILIES["olive"]["base"],
    "mountain to mountain": COLOR_FAMILIES["orange"]["base"],
    "mixed non-basin": NEUTRAL_MARKS["mid"],
    "offshore source": COLOR_FAMILIES["pink"]["base"],
}

SECTOR_ORDER = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
DISTANCE_BINS = [0, 25, 50, 75, 100, 150, 200, 300, np.inf]
DISTANCE_LABELS = ["0-25", "25-50", "50-75", "75-100", "100-150", "150-200", "200-300", "300+"]
MAG_BINS = [-np.inf, 3.0, 3.5, 4.0, 4.5, np.inf]
MAG_LABELS = ["<3.0", "3.0-3.5", "3.5-4.0", "4.0-4.5", ">=4.5"]
DEPTH_BINS = [-np.inf, 5, 10, 15, 20, np.inf]
DEPTH_LABELS = ["<5", "5-10", "10-15", "15-20", ">=20"]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-root", type=Path, default=DEFAULT_ANALYSIS_ROOT)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--metric", action="append", dest="metrics_focus", default=None)
    parser.add_argument("--band", action="append", dest="bands", default=None)
    parser.add_argument("--component-metric", action="append", dest="component_metrics", default=None)
    parser.add_argument("--skip-raw-components", action="store_true")
    parser.add_argument("--skip-mixed-effects", action="store_true")
    parser.add_argument("--max-mixed-rows", type=int, default=45000)
    parser.add_argument("--bootstrap-samples", type=int, default=400)
    parser.add_argument("--min-summary-rows", type=int, default=80)
    parser.add_argument("--basemap-source", default=DEFAULT_BASEMAP_SOURCE)
    parser.add_argument("--basemap-zoom", type=int, default=DEFAULT_BASEMAP_ZOOM)
    parser.add_argument("--basemap-cache-dir", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    analysis_root = args.analysis_root.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    report_dir = output_dir / "report"
    for directory in (tables_dir, figures_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)
    basemap_cache_dir = args.basemap_cache_dir or (output_dir / "basemap_cache")

    metrics_focus = tuple(args.metrics_focus or DEFAULT_METRIC_SET)
    bands = tuple(args.bands or DEFAULT_BANDS)
    component_metrics = tuple(args.component_metrics or DEFAULT_COMPONENT_METRICS)
    rng = np.random.default_rng(RANDOM_SEED)
    use_chart_theme()

    pairs = load_pairs(analysis_root / "tables" / "pairs.parquet", metrics_focus=metrics_focus, bands=bands)
    pairs = engineer_features(pairs)

    source_event_summary = build_source_event_summary(pairs)
    source_factor_summary = build_source_factor_summary(source_event_summary, rng, args.bootstrap_samples, args.min_summary_rows)
    distance_summary = build_distance_attenuation_summary(pairs, rng, args.bootstrap_samples, args.min_summary_rows)
    distance_regression = run_distance_regressions(pairs)
    geomorphology_summary = build_geomorphology_summary(pairs, rng, args.bootstrap_samples, args.min_summary_rows)
    support_tables = build_support_tables(pairs)
    support_effects = build_support_effects(pairs)
    path_azimuth_summary = build_path_azimuth_summary(pairs, rng, args.bootstrap_samples, args.min_summary_rows)
    band_contrast_driver_regression = run_band_contrast_regressions(pairs)
    if args.skip_mixed_effects:
        interaction_mixed_effects = pd.DataFrame()
        interaction_mixed_effect_variance = pd.DataFrame()
    else:
        interaction_mixed_effects, interaction_mixed_effect_variance = run_interaction_mixed_effects(pairs, args.max_mixed_rows)

    if args.skip_raw_components:
        component_azimuth_summary = pd.DataFrame()
    else:
        raw_components = load_raw_components(
            args.metrics,
            model=args.model,
            metrics_focus=component_metrics,
            bands=bands,
        )
        component_azimuth_summary = build_component_azimuth_summary(
            raw_components,
            rng,
            args.bootstrap_samples,
            args.min_summary_rows,
        )

    write_tables(
        tables_dir,
        source_event_summary=source_event_summary,
        source_factor_summary=source_factor_summary,
        distance_attenuation_summary=distance_summary,
        distance_regression=distance_regression,
        geomorphology_summary=geomorphology_summary,
        station_support=support_tables["station_support"],
        event_support=support_tables["event_support"],
        support_effects=support_effects,
        path_azimuth_summary=path_azimuth_summary,
        band_contrast_driver_regression=band_contrast_driver_regression,
        interaction_mixed_effects=interaction_mixed_effects,
        interaction_mixed_effect_variance=interaction_mixed_effect_variance,
        component_azimuth_summary=component_azimuth_summary,
    )

    figure_paths = []
    figure_paths.append(plot_source_magnitude_depth(source_event_summary, figures_dir))
    figure_paths.append(plot_distance_attenuation(distance_summary, figures_dir))
    if not component_azimuth_summary.empty:
        figure_paths.append(plot_component_azimuth_heatmaps(component_azimuth_summary, figures_dir))
    figure_paths.append(
        plot_support_density(
            support_tables["station_support"],
            support_tables["event_support"],
            figures_dir,
            basemap_source=str(args.basemap_source),
            basemap_cache_dir=basemap_cache_dir,
            basemap_zoom=args.basemap_zoom,
        )
    )
    figure_paths.append(plot_geomorphology_effects(geomorphology_summary, figures_dir))
    figure_paths.append(plot_path_azimuth_heatmap(path_azimuth_summary, figures_dir))

    manifest = {
        "inputs": {
            "analysis_root": str(analysis_root),
            "pairs": str(analysis_root / "tables" / "pairs.parquet"),
            "metrics": str(args.metrics),
            "model": args.model,
            "metrics_focus": list(metrics_focus),
            "bands": list(bands),
            "component_metrics": list(component_metrics),
            "basemap_source": str(args.basemap_source),
            "basemap_cache_dir": str(basemap_cache_dir),
            "basemap_zoom": args.basemap_zoom,
        },
        "outputs": {
            "output_dir": str(output_dir),
            "tables_dir": str(tables_dir),
            "figures_dir": str(figures_dir),
            "report_dir": str(report_dir),
        },
        "counts": {
            "pair_rows": int(len(pairs)),
            "events": int(pairs["event_id"].nunique()),
            "stations": int(pairs["station"].nunique()),
            "component_rows": int(component_azimuth_summary["rows"].sum()) if not component_azimuth_summary.empty else 0,
        },
        "figures": [str(path) for path in figure_paths],
        "random_seed": RANDOM_SEED,
        "notes": [
            "Event demeaning is used only as a descriptive diagnostic in some tables.",
            "The interaction mixed-effects tables fit raw log2 residuals with station and event random intercepts.",
            "Band contrast regressions use within event-station metric differences across period bands.",
        ],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report_scaffold(report_dir / "cvmsi_extended_scan_report.md", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def use_chart_theme() -> None:
    if sns is not None:
        sns.set_theme(
            style="whitegrid",
            rc={
                "figure.facecolor": TOKENS["surface"],
                "figure.edgecolor": "none",
                "savefig.facecolor": TOKENS["surface"],
                "savefig.edgecolor": "none",
                "axes.facecolor": TOKENS["panel"],
                "axes.edgecolor": TOKENS["axis"],
                "axes.labelcolor": TOKENS["ink"],
                "axes.labelsize": 11.5,
                "axes.titlesize": 11.5,
                "axes.grid": True,
                "axes.spines.top": False,
                "axes.spines.right": False,
                "grid.color": TOKENS["grid"],
                "grid.linewidth": 0.8,
                "font.size": 11,
                "font.family": "sans-serif",
                "font.sans-serif": ["Aptos", "Inter", "Segoe UI", "DejaVu Sans", "Arial", "sans-serif"],
                "xtick.labelsize": 10,
                "ytick.labelsize": 10,
                "patch.linewidth": 1.0,
            },
        )
    else:
        plt.rcParams.update(
            {
                "figure.facecolor": TOKENS["surface"],
                "savefig.facecolor": TOKENS["surface"],
                "axes.facecolor": TOKENS["panel"],
                "axes.edgecolor": TOKENS["axis"],
                "axes.labelcolor": TOKENS["ink"],
                "axes.labelsize": 11.5,
                "axes.titlesize": 11.5,
                "axes.spines.top": False,
                "axes.spines.right": False,
                "axes.grid": True,
                "grid.color": TOKENS["grid"],
                "grid.linewidth": 0.8,
                "font.size": 11,
                "font.family": "sans-serif",
                "font.sans-serif": ["Aptos", "Inter", "Segoe UI", "DejaVu Sans", "Arial", "sans-serif"],
                "xtick.labelsize": 10,
                "ytick.labelsize": 10,
            }
        )


def add_chart_header(fig: plt.Figure, ax: plt.Axes, title: str, subtitle: str, *, title_width: int = 78, subtitle_width: int = 112) -> None:
    title = textwrap.fill(str(title).strip(), width=title_width, break_long_words=False)
    subtitle = textwrap.fill(str(subtitle).strip(), width=subtitle_width, break_long_words=False)
    if not title or not subtitle:
        raise ValueError("Every chart needs a non-empty title and subtitle.")
    title_lines = title.count("\n") + 1
    subtitle_lines = subtitle.count("\n") + 1
    ax.set_title("")
    fig.subplots_adjust(top=max(0.62, 0.87 - 0.045 * (title_lines - 1) - 0.032 * (subtitle_lines - 1)))
    left = ax.get_position().x0
    fig.text(left, 0.985, title, ha="left", va="top", fontsize=16, fontweight="semibold", color=TOKENS["ink"], linespacing=1.08)
    fig.text(left, 0.925 - 0.045 * (title_lines - 1), subtitle, ha="left", va="top", fontsize=11.5, color=TOKENS["muted"], linespacing=1.18)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)


def save_figure(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220, bbox_inches="tight")
    fig.savefig(path.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)
    return path


def load_pairs(path: Path, *, metrics_focus: Sequence[str], bands: Sequence[str]) -> pd.DataFrame:
    if path.exists():
        df = pd.read_parquet(path)
    else:
        csv_path = path.with_suffix(".csv")
        if not csv_path.exists():
            raise FileNotFoundError(f"First-pass pair table is required: {path} or {csv_path}")
        df = pd.read_csv(csv_path)
    df = df.loc[df["metric"].astype(str).isin(metrics_focus) & df["band"].astype(str).isin(bands)].copy()
    df = standardize_columns(df)
    required = ["event_id", "station", "metric", "band", "log2_residual"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Pair table missing required columns: {missing}")
    for column in ["event_id", "station", "metric", "band"]:
        df[column] = df[column].astype(str)
    numeric = [
        "log2_residual",
        "residual_event_centered",
        "event_lat",
        "event_lon",
        "sta_lat",
        "sta_lon",
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
        "path_mountains_fraction",
        "Vs30",
        "log2_model_vs30_ratio",
    ]
    for column in numeric:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df.replace([np.inf, -np.inf], np.nan)


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    aliases = {
        "azimuth": "azimuth_deg",
        "backazimuth": "backazimuth_deg",
        "event_depth": "event_depth_km",
        "depth_km": "event_depth_km",
    }
    for source, target in aliases.items():
        if target not in out.columns and source in out.columns:
            out[target] = out[source]
    defaults = {
        "station_region": "unknown",
        "station_region_type": "unknown",
        "station_geomorphology": "unknown",
        "event_region": "unknown",
        "event_region_type": "unknown",
        "event_geomorphology": "unknown",
        "geologic_description": "unknown",
        "path_class": "unknown",
        "path_basin_fraction": 0.0,
        "path_la_basin_fraction": 0.0,
        "path_mountains_fraction": 0.0,
    }
    for column, default in defaults.items():
        if column not in out.columns:
            out[column] = default
    return out


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["faulting_type"] = out.get("rake", pd.Series(np.nan, index=out.index)).apply(classify_faulting)
    out["magnitude_bin"] = pd.cut(pd.to_numeric(out.get("magnitude", np.nan), errors="coerce"), MAG_BINS, labels=MAG_LABELS)
    out["depth_bin_km"] = pd.cut(pd.to_numeric(out.get("event_depth_km", np.nan), errors="coerce"), DEPTH_BINS, labels=DEPTH_LABELS)
    out["distance_bin_km"] = pd.cut(pd.to_numeric(out.get("distance_km", np.nan), errors="coerce"), DISTANCE_BINS, labels=DISTANCE_LABELS)
    out["distance_bin_mid_km"] = out["distance_bin_km"].map(distance_label_midpoint).astype(float)
    out["azimuth_sector"] = sectorize_degrees(out.get("azimuth_deg", pd.Series(np.nan, index=out.index)))
    out["backazimuth_sector"] = sectorize_degrees(out.get("backazimuth_deg", pd.Series(np.nan, index=out.index)))
    out["log_distance"] = np.log10(pd.to_numeric(out.get("distance_km", np.nan), errors="coerce").clip(lower=1.0))
    if "residual_event_centered" not in out.columns:
        out["residual_event_centered"] = out["log2_residual"] - out.groupby(["event_id", "metric", "band"])["log2_residual"].transform("median")
    for column in [
        "station_region",
        "station_region_type",
        "station_geomorphology",
        "event_region",
        "event_region_type",
        "event_geomorphology",
        "geologic_description",
        "path_class",
    ]:
        out[column] = out[column].fillna("unknown").astype(str)
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


def sectorize_degrees(values: pd.Series) -> pd.Categorical:
    numeric = pd.to_numeric(values, errors="coerce")
    shifted = (numeric + 22.5) % 360.0
    indices = np.floor(shifted / 45.0).astype("float")
    labels = pd.Series(np.nan, index=values.index, dtype=object)
    valid = indices.notna()
    labels.loc[valid] = [SECTOR_ORDER[int(index) % 8] for index in indices.loc[valid]]
    return pd.Categorical(labels, categories=SECTOR_ORDER, ordered=True)


def distance_label_midpoint(label: object) -> float:
    mapping = {
        "0-25": 12.5,
        "25-50": 37.5,
        "50-75": 62.5,
        "75-100": 87.5,
        "100-150": 125.0,
        "150-200": 175.0,
        "200-300": 250.0,
        "300+": 350.0,
    }
    return mapping.get(str(label), np.nan)


def first_valid(series: pd.Series) -> object:
    values = series.dropna()
    return values.iloc[0] if not values.empty else np.nan


def build_source_event_summary(pairs: pd.DataFrame) -> pd.DataFrame:
    agg = {
        "event_lat": ("event_lat", "median"),
        "event_lon": ("event_lon", "median"),
        "magnitude": ("magnitude", "median"),
        "event_depth_km": ("event_depth_km", "median"),
        "strike": ("strike", "median"),
        "dip": ("dip", "median"),
        "rake": ("rake", "median"),
        "faulting_type": ("faulting_type", first_valid),
        "magnitude_bin": ("magnitude_bin", first_valid),
        "depth_bin_km": ("depth_bin_km", first_valid),
        "event_region": ("event_region", first_valid),
        "event_region_type": ("event_region_type", first_valid),
        "event_geomorphology": ("event_geomorphology", first_valid),
        "stations": ("station", "nunique"),
        "rows": ("log2_residual", "size"),
        "distance_median_km": ("distance_km", "median"),
        "distance_max_km": ("distance_km", "max"),
        "path_basin_fraction_median": ("path_basin_fraction", "median"),
        "path_la_basin_fraction_median": ("path_la_basin_fraction", "median"),
        "event_median_residual": ("log2_residual", "median"),
        "event_mean_residual": ("log2_residual", "mean"),
        "event_median_centered_residual": ("residual_event_centered", "median"),
    }
    return pairs.groupby(["event_id", "metric", "band"], as_index=False).agg(**agg)


def build_source_factor_summary(event_summary: pd.DataFrame, rng: np.random.Generator, samples: int, min_rows: int) -> pd.DataFrame:
    factors = ["faulting_type", "magnitude_bin", "depth_bin_km", "event_region_type", "event_region", "event_geomorphology"]
    rows = []
    for factor in factors:
        if factor not in event_summary.columns:
            continue
        work = event_summary.loc[event_summary[factor].notna()].copy()
        work["factor_name"] = factor
        work["factor_value"] = work[factor].astype(str)
        rows.append(
            summarize_groups(
                work,
                ["metric", "band", "factor_name", "factor_value"],
                "event_median_residual",
                rng,
                samples,
                min_rows=max(8, min_rows // 6),
                extra_counts=("event_id",),
            )
        )
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def build_distance_attenuation_summary(pairs: pd.DataFrame, rng: np.random.Generator, samples: int, min_rows: int) -> pd.DataFrame:
    work = pairs.loc[pairs["distance_bin_km"].notna()].copy()
    summary = summarize_groups(
        work,
        ["metric", "band", "path_class", "distance_bin_km", "distance_bin_mid_km"],
        "log2_residual",
        rng,
        samples,
        min_rows=min_rows,
    )
    centered = summarize_groups(
        work,
        ["metric", "band", "path_class", "distance_bin_km", "distance_bin_mid_km"],
        "residual_event_centered",
        rng,
        samples,
        min_rows=min_rows,
    )
    if centered.empty:
        return summary
    centered = centered.rename(
        columns={
            "median": "event_centered_median",
            "mean": "event_centered_mean",
            "bootstrap_ci_low": "event_centered_ci_low",
            "bootstrap_ci_high": "event_centered_ci_high",
        }
    )
    keep = ["metric", "band", "path_class", "distance_bin_km", "distance_bin_mid_km", "event_centered_median", "event_centered_mean", "event_centered_ci_low", "event_centered_ci_high"]
    return summary.merge(centered[keep], on=["metric", "band", "path_class", "distance_bin_km", "distance_bin_mid_km"], how="left")


def build_geomorphology_summary(pairs: pd.DataFrame, rng: np.random.Generator, samples: int, min_rows: int) -> pd.DataFrame:
    factors = ["station_geomorphology", "event_geomorphology", "geologic_description", "station_region_type"]
    pieces = []
    for factor in factors:
        if factor not in pairs.columns:
            continue
        work = pairs.loc[pairs[factor].notna()].copy()
        work["factor_name"] = factor
        work["factor_value"] = work[factor].astype(str)
        pieces.append(
            summarize_groups(
                work,
                ["metric", "band", "factor_name", "factor_value"],
                "residual_event_centered",
                rng,
                samples,
                min_rows=min_rows,
            )
        )
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()


def build_support_tables(pairs: pd.DataFrame) -> dict[str, pd.DataFrame]:
    station_support = (
        pairs.groupby("station", as_index=False)
        .agg(
            sta_lon=("sta_lon", "median"),
            sta_lat=("sta_lat", "median"),
            station_region=("station_region", first_valid),
            station_region_type=("station_region_type", first_valid),
            station_geomorphology=("station_geomorphology", first_valid),
            geologic_description=("geologic_description", first_valid),
            events=("event_id", "nunique"),
            rows=("log2_residual", "size"),
            metrics=("metric", "nunique"),
            bands=("band", "nunique"),
            distance_median_km=("distance_km", "median"),
            residual_median=("log2_residual", "median"),
            centered_residual_median=("residual_event_centered", "median"),
        )
        .sort_values(["events", "rows"], ascending=False)
    )
    event_support = (
        pairs.groupby("event_id", as_index=False)
        .agg(
            event_lon=("event_lon", "median"),
            event_lat=("event_lat", "median"),
            magnitude=("magnitude", "median"),
            event_depth_km=("event_depth_km", "median"),
            faulting_type=("faulting_type", first_valid),
            event_region=("event_region", first_valid),
            event_region_type=("event_region_type", first_valid),
            event_geomorphology=("event_geomorphology", first_valid),
            stations=("station", "nunique"),
            rows=("log2_residual", "size"),
            distance_median_km=("distance_km", "median"),
            distance_max_km=("distance_km", "max"),
            residual_median=("log2_residual", "median"),
        )
        .sort_values(["stations", "rows"], ascending=False)
    )
    return {"station_support": station_support, "event_support": event_support}


def build_support_effects(pairs: pd.DataFrame) -> pd.DataFrame:
    try:
        from scipy.stats import spearmanr
    except Exception as exc:  # pragma: no cover - environment dependent
        return pd.DataFrame([{"scope": "unavailable", "note": f"scipy import failed: {exc!r}"}])

    station_counts = pairs.groupby("station")["event_id"].nunique().rename("station_event_count")
    event_counts = pairs.groupby("event_id")["station"].nunique().rename("event_station_count")
    work = pairs.merge(station_counts, on="station", how="left").merge(event_counts, on="event_id", how="left")
    rows = []
    for metric, band in work.groupby(["metric", "band"]).groups:
        subset = work.loc[work["metric"].eq(metric) & work["band"].eq(band)].copy()
        for scope, x_col, y_col, group_col in [
            ("station_support", "station_event_count", "residual_event_centered", "station"),
            ("event_support", "event_station_count", "log2_residual", "event_id"),
        ]:
            reduced = subset.groupby(group_col, as_index=False).agg(x=(x_col, "median"), y=(y_col, "median"))
            x = pd.to_numeric(reduced["x"], errors="coerce")
            y = pd.to_numeric(reduced["y"], errors="coerce")
            valid = x.notna() & y.notna()
            if valid.sum() < 10:
                continue
            if x.loc[valid].nunique() < 2 or y.loc[valid].nunique() < 2:
                rows.append(
                    {
                        "scope": scope,
                        "metric": metric,
                        "band": band,
                        "statistic": "spearman_rho",
                        "rho": np.nan,
                        "pvalue": np.nan,
                        "n": int(valid.sum()),
                        "x": x_col,
                        "y": y_col,
                        "interpretation": "Skipped because one variable is constant at this grain.",
                    }
                )
                continue
            rho, pvalue = spearmanr(x[valid], y[valid])
            rows.append(
                {
                    "scope": scope,
                    "metric": metric,
                    "band": band,
                    "statistic": "spearman_rho",
                    "rho": float(rho),
                    "pvalue": float(pvalue),
                    "n": int(valid.sum()),
                    "x": x_col,
                    "y": y_col,
                    "interpretation": "Checks whether sampling support itself is associated with residual structure.",
                }
            )
    return pd.DataFrame(rows)


def build_path_azimuth_summary(pairs: pd.DataFrame, rng: np.random.Generator, samples: int, min_rows: int) -> pd.DataFrame:
    work = pairs.loc[pairs["azimuth_sector"].notna()].copy()
    return summarize_groups(
        work,
        ["metric", "band", "azimuth_sector", "path_class"],
        "residual_event_centered",
        rng,
        samples,
        min_rows=min_rows,
    )


def load_raw_components(path: Path, *, model: str, metrics_focus: Sequence[str], bands: Sequence[str]) -> pd.DataFrame:
    import pyarrow.parquet as pq

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
        "event_depth_km",
        "strike",
        "dip",
        "rake",
        "station_region_type",
        "event_region_type",
    ]
    available = set(pq.ParquetFile(path).schema.names)
    columns = [column for column in wanted if column in available]
    if "component" not in columns:
        return pd.DataFrame()
    try:
        df = pd.read_parquet(
            path,
            columns=columns,
            filters=[("model", "==", model), ("metric", "in", list(metrics_focus)), ("band", "in", list(bands))],
        )
    except Exception:
        df = pd.read_parquet(path, columns=columns)
        df = df.loc[
            df["model"].astype(str).eq(str(model))
            & df["metric"].astype(str).isin(metrics_focus)
            & df["band"].astype(str).isin(bands)
        ].copy()
    df = standardize_columns(df)
    for column in ["event_id", "station", "component", "metric", "band"]:
        if column in df.columns:
            df[column] = df[column].astype(str)
    for column in ["log2_residual", "distance_km", "azimuth_deg", "backazimuth_deg", "magnitude", "event_depth_km", "rake"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["event_id", "station", "component", "metric", "band", "log2_residual"])
    df["azimuth_sector"] = sectorize_degrees(df.get("azimuth_deg", pd.Series(np.nan, index=df.index)))
    df["backazimuth_sector"] = sectorize_degrees(df.get("backazimuth_deg", pd.Series(np.nan, index=df.index)))
    df["faulting_type"] = df.get("rake", pd.Series(np.nan, index=df.index)).apply(classify_faulting)
    df["component_residual_event_centered"] = df["log2_residual"] - df.groupby(["event_id", "metric", "band"])["log2_residual"].transform("median")
    return df


def build_component_azimuth_summary(raw: pd.DataFrame, rng: np.random.Generator, samples: int, min_rows: int) -> pd.DataFrame:
    if raw.empty or "component" not in raw.columns:
        return pd.DataFrame()
    work = raw.loc[raw["azimuth_sector"].notna()].copy()
    return summarize_groups(
        work,
        ["metric", "band", "component", "azimuth_sector"],
        "component_residual_event_centered",
        rng,
        samples,
        min_rows=max(20, min_rows // 2),
    )


def summarize_groups(
    df: pd.DataFrame,
    group_cols: Sequence[str],
    value_col: str,
    rng: np.random.Generator,
    samples: int,
    *,
    min_rows: int,
    extra_counts: Iterable[str] = ("event_id", "station"),
) -> pd.DataFrame:
    rows = []
    for keys, group in df.groupby(list(group_cols), dropna=False, observed=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        values = pd.to_numeric(group[value_col], errors="coerce").dropna().to_numpy(dtype=float)
        if values.size < min_rows:
            continue
        low, high = bootstrap_ci(values, rng, samples)
        row = {column: value for column, value in zip(group_cols, keys)}
        row.update(
            {
                "value_column": value_col,
                "rows": int(values.size),
                "median": float(np.nanmedian(values)),
                "mean": float(np.nanmean(values)),
                "q25": float(np.nanpercentile(values, 25)),
                "q75": float(np.nanpercentile(values, 75)),
                "bootstrap_ci_low": low,
                "bootstrap_ci_high": high,
            }
        )
        for column in extra_counts:
            if column in group.columns:
                row[f"{column}_count"] = int(group[column].nunique())
        if "distance_km" in group.columns:
            row["distance_median_km"] = float(pd.to_numeric(group["distance_km"], errors="coerce").median())
        rows.append(row)
    return pd.DataFrame(rows)


def bootstrap_ci(values: np.ndarray, rng: np.random.Generator, samples: int, alpha: float = 0.05) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return (float("nan"), float("nan"))
    if values.size == 1 or samples <= 0:
        value = float(np.nanmedian(values))
        return (value, value)
    draw = rng.integers(0, values.size, size=(samples, values.size))
    medians = np.nanmedian(values[draw], axis=1)
    low, high = np.nanpercentile(medians, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(low), float(high)


def zscore(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    std = float(values.std(skipna=True))
    if not np.isfinite(std) or std <= 0:
        return pd.Series(np.nan, index=series.index)
    return (values - float(values.mean(skipna=True))) / std


def prepare_regression_frame(df: pd.DataFrame, y_col: str) -> pd.DataFrame:
    out = df.copy()
    for source, target in [
        ("log_distance", "log_distance_z"),
        ("path_basin_fraction", "path_basin_fraction_z"),
        ("path_la_basin_fraction", "path_la_basin_fraction_z"),
        ("path_mountains_fraction", "path_mountains_fraction_z"),
        ("magnitude", "magnitude_z"),
        ("event_depth_km", "event_depth_km_z"),
    ]:
        out[target] = zscore(out[source]) if source in out.columns else np.nan
    for column in ["band", "path_class", "station_region_type", "faulting_type"]:
        if column in out.columns:
            out[column] = out[column].fillna("unknown").astype(str)
        else:
            out[column] = "unknown"
    needed = [
        y_col,
        "log_distance_z",
        "path_basin_fraction_z",
        "path_la_basin_fraction_z",
        "magnitude_z",
        "event_depth_km_z",
        "band",
        "path_class",
        "station_region_type",
        "faulting_type",
    ]
    return out.replace([np.inf, -np.inf], np.nan).dropna(subset=[column for column in needed if column in out.columns])


def run_distance_regressions(pairs: pd.DataFrame) -> pd.DataFrame:
    try:
        import statsmodels.formula.api as smf
    except Exception as exc:  # pragma: no cover - environment dependent
        return pd.DataFrame([{"model_name": "distance_regression_unavailable", "term": "error", "note": repr(exc)}])

    rows = []
    formula = "log2_residual ~ log_distance_z + path_basin_fraction_z + path_la_basin_fraction_z + C(path_class) + C(station_region_type)"
    for metric in sorted(pairs["metric"].dropna().unique()):
        for band in DEFAULT_BANDS:
            data = prepare_regression_frame(pairs.loc[pairs["metric"].eq(metric) & pairs["band"].eq(band)], "log2_residual")
            if len(data) < 300:
                continue
            try:
                result = smf.ols(formula, data=data).fit(cov_type="HC3")
                rows.extend(model_rows_from_result(result, "distance_path_ols_hc3", metric, band, len(data)))
            except Exception as exc:
                rows.append({"model_name": "distance_path_ols_hc3", "metric": metric, "band_scope": band, "term": "model_fit_error", "note": repr(exc), "nobs": int(len(data))})
    return pd.DataFrame(rows)


def run_band_contrast_regressions(pairs: pd.DataFrame) -> pd.DataFrame:
    try:
        import statsmodels.formula.api as smf
    except Exception as exc:  # pragma: no cover - environment dependent
        return pd.DataFrame([{"model_name": "band_contrast_regression_unavailable", "term": "error", "note": repr(exc)}])

    meta_cols = [
        "event_id",
        "station",
        "metric",
        "path_class",
        "station_region_type",
        "faulting_type",
        "path_basin_fraction",
        "path_la_basin_fraction",
        "path_mountains_fraction",
        "distance_km",
        "log_distance",
        "magnitude",
        "event_depth_km",
    ]
    wide = pairs.pivot_table(index=["event_id", "station", "metric"], columns="band", values="log2_residual", aggfunc="median").reset_index()
    if {"3-5 sec", "1-2 sec"}.issubset(wide.columns):
        wide["delta_3_5_minus_1_2"] = wide["3-5 sec"] - wide["1-2 sec"]
    if {"2-3 sec", "1-2 sec"}.issubset(wide.columns):
        wide["delta_2_3_minus_1_2"] = wide["2-3 sec"] - wide["1-2 sec"]
    meta = pairs[[column for column in meta_cols if column in pairs.columns]].drop_duplicates(["event_id", "station", "metric"])
    contrasts = wide.merge(meta, on=["event_id", "station", "metric"], how="left")
    rows = []
    formula = (
        "{target} ~ log_distance_z + path_basin_fraction_z + path_la_basin_fraction_z + "
        "magnitude_z + event_depth_km_z + C(path_class) + C(station_region_type) + C(faulting_type)"
    )
    for metric in sorted(contrasts["metric"].dropna().unique()):
        for target in ["delta_3_5_minus_1_2", "delta_2_3_minus_1_2"]:
            if target not in contrasts.columns:
                continue
            data = prepare_regression_frame(contrasts.loc[contrasts["metric"].eq(metric)], target)
            if len(data) < 300:
                continue
            try:
                result = smf.ols(formula.format(target=target), data=data).fit(cov_type="HC3")
                rows.extend(model_rows_from_result(result, "band_contrast_ols_hc3", metric, target, len(data)))
            except Exception as exc:
                rows.append({"model_name": "band_contrast_ols_hc3", "metric": metric, "band_scope": target, "term": "model_fit_error", "note": repr(exc), "nobs": int(len(data))})
    return pd.DataFrame(rows)


def run_interaction_mixed_effects(pairs: pd.DataFrame, max_rows: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        import statsmodels.formula.api as smf
    except Exception as exc:  # pragma: no cover - environment dependent
        return (
            pd.DataFrame([{"model_name": "interaction_mixed_effects_unavailable", "term": "error", "note": repr(exc)}]),
            pd.DataFrame(),
        )

    fixed_rows: list[dict[str, object]] = []
    variance_rows: list[dict[str, object]] = []
    formula = (
        "log2_residual ~ C(band) * log_distance_z + C(band) * path_basin_fraction_z + "
        "path_la_basin_fraction_z + magnitude_z + event_depth_km_z + "
        "C(path_class) + C(station_region_type) + C(faulting_type)"
    )
    for metric in ["PGA", "PGV", "arias_duration", "energy_intensity"]:
        data = prepare_regression_frame(pairs.loc[pairs["metric"].eq(metric)].copy(), "log2_residual")
        if len(data) < 800:
            continue
        if max_rows > 0 and len(data) > max_rows:
            data = data.sample(n=max_rows, random_state=RANDOM_SEED).copy()
        data["event_id"] = data["event_id"].astype(str)
        data["station"] = data["station"].astype(str)
        try:
            model = smf.mixedlm(
                formula,
                data=data,
                groups=data["station"],
                re_formula="1",
                vc_formula={"event": "0 + C(event_id)"},
            )
            result = model.fit(reml=False, method="lbfgs", maxiter=180, disp=False)
            fixed_rows.extend(model_rows_from_result(result, "interaction_source_path_site", metric, "all_bands", int(result.nobs)))
            station_var = float(result.cov_re.iloc[0, 0]) if result.cov_re.shape[0] else np.nan
            event_var = float(result.vcomp[0]) if len(result.vcomp) else np.nan
            variance_rows.append(
                {
                    "model_name": "interaction_source_path_site",
                    "metric": metric,
                    "band_scope": "all_bands",
                    "nobs": int(result.nobs),
                    "station_random_intercept_var": station_var,
                    "event_random_intercept_var": event_var,
                    "residual_var": float(result.scale),
                    "aic": float(result.aic),
                    "bic": float(result.bic),
                    "converged": bool(getattr(result, "converged", False)),
                    "note": "",
                }
            )
        except Exception as exc:
            fixed_rows.append(
                {
                    "model_name": "interaction_source_path_site",
                    "metric": metric,
                    "band_scope": "all_bands",
                    "term": "model_fit_error",
                    "coef": np.nan,
                    "se": np.nan,
                    "z": np.nan,
                    "pvalue": np.nan,
                    "ci_low": np.nan,
                    "ci_high": np.nan,
                    "nobs": int(len(data)),
                    "converged": False,
                    "note": repr(exc),
                }
            )
    return pd.DataFrame(fixed_rows), pd.DataFrame(variance_rows)


def model_rows_from_result(result: object, model_name: str, metric: str, band_scope: str, nobs: int) -> list[dict[str, object]]:
    rows = []
    params = result.params
    bse = result.bse
    conf = result.conf_int()
    pvalues = result.pvalues
    for term, coef in params.items():
        if str(term).endswith(" Var") or str(term).endswith(" x event Var"):
            continue
        se = float(bse.get(term, np.nan))
        rows.append(
            {
                "model_name": model_name,
                "metric": metric,
                "band_scope": band_scope,
                "term": term,
                "coef": float(coef),
                "se": se,
                "z": float(coef / se) if np.isfinite(se) and se > 0 else np.nan,
                "pvalue": float(pvalues.get(term, np.nan)),
                "ci_low": float(conf.loc[term, 0]) if term in conf.index else np.nan,
                "ci_high": float(conf.loc[term, 1]) if term in conf.index else np.nan,
                "nobs": int(nobs),
                "converged": bool(getattr(result, "converged", True)),
                "note": "",
            }
        )
    return rows


def write_tables(tables_dir: Path, **tables: pd.DataFrame) -> None:
    for name, table in tables.items():
        if table is None or table.empty:
            continue
        table.to_csv(tables_dir / f"{name}.csv", index=False)
        if name in {"source_event_summary", "station_support", "event_support", "component_azimuth_summary"}:
            try:
                table.to_parquet(tables_dir / f"{name}.parquet", index=False)
            except Exception:
                pass


def plot_source_magnitude_depth(event_summary: pd.DataFrame, figures_dir: Path) -> Path:
    plot_df = event_summary.loc[event_summary["band"].eq("3-5 sec") & event_summary["metric"].isin(["PGA", "PGV", "arias_duration"])].copy()
    plot_df = plot_df.dropna(subset=["magnitude", "event_depth_km", "event_median_residual"])
    if plot_df.empty:
        return figures_dir / "fig_07_source_magnitude_depth_faulting.png"
    metrics = ["PGA", "PGV", "arias_duration"]
    fig, axes = plt.subplots(1, len(metrics), figsize=(16.4, 5.6), sharex=True, sharey=True)
    vmax = float(np.nanpercentile(np.abs(plot_df["event_median_residual"]), 95))
    norm = TwoSlopeNorm(vcenter=0.0, vmin=-max(vmax, 0.5), vmax=max(vmax, 0.5))
    cmap = plt.get_cmap("coolwarm")
    marker_map = {"strike-slip": "o", "reverse": "^", "normal": "s", "oblique": "D", "unknown": "P"}
    for ax, metric in zip(axes, metrics):
        subset = plot_df.loc[plot_df["metric"].eq(metric)]
        for faulting_type, group in subset.groupby("faulting_type", dropna=False):
            ax.scatter(
                group["magnitude"],
                group["event_depth_km"],
                c=group["event_median_residual"],
                cmap=cmap,
                norm=norm,
                s=np.clip(group["stations"].to_numpy(dtype=float) * 1.6, 18, 110),
                marker=marker_map.get(str(faulting_type), "o"),
                edgecolor=TOKENS["ink"],
                linewidth=0.4,
                alpha=0.82,
                label=str(faulting_type),
            )
        ax.invert_yaxis()
        ax.set_title(metric, fontsize=11.5, color=TOKENS["ink"])
        ax.set_xlabel("Magnitude")
        ax.grid(True, axis="both", color=TOKENS["grid"], linewidth=0.8)
    axes[0].set_ylabel("Event depth (km, inverted)")
    handles = [
        plt.Line2D([0], [0], marker=marker, color="none", markerfacecolor=NEUTRAL_MARKS["light"], markeredgecolor=TOKENS["ink"], label=label, markersize=7)
        for label, marker in marker_map.items()
    ]
    add_chart_header(
        fig,
        axes[0],
        "Source controls are tested at event level",
        "Points are events in the 3-5 sec band; color is event median residual, marker is rake-derived faulting type, size scales with station support.",
    )
    fig.subplots_adjust(bottom=0.20, right=0.86, wspace=0.24)
    cbar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=axes, fraction=0.024, pad=0.022)
    cbar.set_label("Event median log2(obs/syn)")
    cbar.ax.tick_params(labelsize=10)
    cbar.ax.yaxis.label.set_size(11.5)
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.50, 0.01), frameon=False, ncol=len(handles), title="Faulting")
    return save_figure(fig, figures_dir / "fig_07_source_magnitude_depth_faulting.png")


def plot_distance_attenuation(distance_summary: pd.DataFrame, figures_dir: Path) -> Path:
    plot_df = distance_summary.loc[
        distance_summary["metric"].isin(["PGA", "arias_duration"])
        & distance_summary["band"].eq("3-5 sec")
        & distance_summary["path_class"].isin(["crosses LA basin", "terminates in LA basin", "mountain to mountain", "mixed non-basin", "other basin-influenced"])
    ].copy()
    if plot_df.empty:
        return figures_dir / "fig_08_distance_attenuation_binned.png"
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8), sharex=True, sharey=False)
    for ax, metric in zip(axes, ["PGA", "arias_duration"]):
        subset = plot_df.loc[plot_df["metric"].eq(metric)].sort_values("distance_bin_mid_km")
        for path_class, group in subset.groupby("path_class", sort=False):
            color = PATH_COLORS.get(str(path_class), NEUTRAL_MARKS["mid"])
            group = group.sort_values("distance_bin_mid_km")
            ax.plot(group["distance_bin_mid_km"], group["median"], color=color, marker="o", linewidth=1.1, label=str(path_class))
            ax.fill_between(group["distance_bin_mid_km"], group["bootstrap_ci_low"], group["bootstrap_ci_high"], color=color, alpha=0.16, linewidth=0)
        ax.axhline(0, color=TOKENS["ink"], linestyle=":", linewidth=1.0)
        ax.set_title(metric, fontsize=10, color=TOKENS["ink"])
        ax.set_xlabel("Distance bin midpoint (km)")
        ax.set_ylabel("Median log2(obs/syn)")
    axes[-1].legend(loc="lower left", bbox_to_anchor=(1.02, 0.0), frameon=False, title="Path class")
    add_chart_header(
        fig,
        axes[0],
        "Distance trends vary by path class",
        "Binned 3-5 sec residual medians with bootstrap median intervals; raw residuals are used so source and site terms remain visible.",
    )
    return save_figure(fig, figures_dir / "fig_08_distance_attenuation_binned.png")


def plot_component_azimuth_heatmaps(component_summary: pd.DataFrame, figures_dir: Path) -> Path:
    plot_df = component_summary.loc[component_summary["metric"].isin(["PGA", "PGV"]) & component_summary["band"].eq("3-5 sec")].copy()
    if plot_df.empty:
        return figures_dir / "fig_09_component_azimuth_heatmaps.png"
    metrics = [metric for metric in ["PGA", "PGV"] if metric in set(plot_df["metric"])]
    fig, axes = plt.subplots(1, len(metrics), figsize=(6.8 * len(metrics), 4.9), squeeze=False)
    vmax = max(0.25, float(np.nanpercentile(np.abs(plot_df["median"]), 95)))
    for ax, metric in zip(axes.flat, metrics):
        matrix = (
            plot_df.loc[plot_df["metric"].eq(metric)]
            .pivot_table(index="component", columns="azimuth_sector", values="median", aggfunc="median")
            .reindex(columns=SECTOR_ORDER)
        )
        if sns is not None:
            sns.heatmap(matrix, ax=ax, cmap="coolwarm", vmin=-vmax, vmax=vmax, center=0.0, linewidths=1.0, linecolor=TOKENS["panel"], annot=True, fmt=".2f", cbar=metric == metrics[-1])
        else:
            im = ax.imshow(matrix.to_numpy(dtype=float), cmap="coolwarm", vmin=-vmax, vmax=vmax, aspect="auto")
            ax.set_xticks(np.arange(matrix.shape[1]), matrix.columns)
            ax.set_yticks(np.arange(matrix.shape[0]), matrix.index)
            if metric == metrics[-1]:
                fig.colorbar(im, ax=ax)
        ax.set_title(metric, fontsize=10, color=TOKENS["ink"])
        ax.set_xlabel("Path azimuth sector")
        ax.set_ylabel("Component")
    add_chart_header(
        fig,
        axes.flat[0],
        "Component residuals have directional structure",
        "Cells show event-centered component residual medians in the 3-5 sec band; sectors use source-to-station path azimuth.",
    )
    return save_figure(fig, figures_dir / "fig_09_component_azimuth_heatmaps.png")


def plot_support_density(
    station_support: pd.DataFrame,
    event_support: pd.DataFrame,
    figures_dir: Path,
    *,
    basemap_source: str,
    basemap_cache_dir: Path,
    basemap_zoom: int | None,
) -> Path:
    transformer = Transformer.from_crs(WGS84, WEB_MERCATOR, always_xy=True)
    station_x, station_y = transformer.transform(station_support["sta_lon"].to_numpy(dtype=float), station_support["sta_lat"].to_numpy(dtype=float))
    event_x, event_y = transformer.transform(event_support["event_lon"].to_numpy(dtype=float), event_support["event_lat"].to_numpy(dtype=float))
    x_values = np.concatenate([station_x, event_x])
    y_values = np.concatenate([station_y, event_y])
    x_pad = max(22_000.0, 0.04 * (float(np.nanmax(x_values)) - float(np.nanmin(x_values))))
    y_pad = max(22_000.0, 0.04 * (float(np.nanmax(y_values)) - float(np.nanmin(y_values))))
    xlim = (float(np.nanmin(x_values)) - x_pad, float(np.nanmax(x_values)) + x_pad)
    ylim = (float(np.nanmin(y_values)) - y_pad, float(np.nanmax(y_values)) + y_pad)
    fig, axes = plt.subplots(1, 2, figsize=(16.8, 6.4), sharex=True, sharey=True)
    for ax in axes:
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        add_required_basemap(ax, source=basemap_source, cache_dir=basemap_cache_dir, zoom=basemap_zoom)
    scatter0 = axes[0].scatter(
        station_x,
        station_y,
        c=station_support["events"],
        s=np.clip(station_support["events"].to_numpy(dtype=float) * 1.5, 15, 130),
        cmap="viridis",
        edgecolor=TOKENS["ink"],
        linewidth=0.25,
        alpha=0.82,
        zorder=4,
    )
    cbar0 = fig.colorbar(scatter0, ax=axes[0], fraction=0.035, pad=0.035)
    cbar0.set_label("Events per station")
    cbar0.ax.tick_params(labelsize=10)
    cbar0.ax.yaxis.label.set_size(11.5)
    scatter1 = axes[1].scatter(
        event_x,
        event_y,
        c=event_support["stations"],
        s=np.clip(event_support["stations"].to_numpy(dtype=float) * 1.2, 18, 150),
        cmap="magma",
        edgecolor=TOKENS["ink"],
        linewidth=0.25,
        alpha=0.82,
        zorder=4,
    )
    cbar1 = fig.colorbar(scatter1, ax=axes[1], fraction=0.035, pad=0.035)
    cbar1.set_label("Stations per event")
    cbar1.ax.tick_params(labelsize=10)
    cbar1.ax.yaxis.label.set_size(11.5)
    for ax in axes:
        format_projected_map_axis(ax)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.grid(True, color="#FFFFFF", linewidth=0.55, alpha=0.55, zorder=1.1)
    add_chart_header(
        fig,
        axes[0],
        "Sampling support is spatially uneven",
        "Station marker color and size encode number of contributing events; event marker color and size encode number of contributing stations.",
        subtitle_width=130,
    )
    axes[0].set_title("Stations", fontsize=12, color=TOKENS["ink"], pad=9)
    axes[1].set_title("Events", fontsize=12, color=TOKENS["ink"], pad=9)
    return save_figure(fig, figures_dir / "fig_10_support_density_maps.png")


def add_required_basemap(ax: plt.Axes, *, source: str, cache_dir: Path, zoom: int | None) -> str:
    from spatial_vtk.spatial.map.basemaps import add_contextily_basemap

    ok, resolved_source = add_contextily_basemap(
        ax,
        crs=WEB_MERCATOR,
        primary_source=source,
        fallback_sources=("Esri.WorldTopoMap", "OpenStreetMap.Mapnik", "Esri.WorldImagery"),
        zoom=zoom,
        attribution=False,
        cache_dir=cache_dir,
        cache_download=True,
        on_error="raise",
    )
    if not ok:
        raise RuntimeError(f"Required basemap was not rendered: {resolved_source}")
    return str(resolved_source)


def format_projected_map_axis(ax: plt.Axes) -> None:
    ax.set_aspect("equal", adjustable="box")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000.0:.0f}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000.0:.0f}"))
    ax.set_xlabel("Web Mercator x (km)")
    ax.set_ylabel("Web Mercator y (km)")


def plot_geomorphology_effects(geomorphology_summary: pd.DataFrame, figures_dir: Path) -> Path:
    plot_df = geomorphology_summary.loc[
        geomorphology_summary["factor_name"].eq("station_geomorphology")
        & geomorphology_summary["metric"].isin(["PGA", "arias_duration"])
        & geomorphology_summary["band"].eq("3-5 sec")
    ].copy()
    if plot_df.empty:
        return figures_dir / "fig_11_geomorphology_effects.png"
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.1), sharex=True)
    for ax, metric in zip(axes, ["PGA", "arias_duration"]):
        subset = plot_df.loc[plot_df["metric"].eq(metric)].copy()
        subset = subset.reindex(subset["median"].abs().sort_values(ascending=False).index).head(12)
        subset = subset.sort_values("median")
        colors = np.where(subset["median"] >= 0, COLOR_FAMILIES["olive"]["base"], COLOR_FAMILIES["orange"]["base"])
        edges = np.where(subset["median"] >= 0, COLOR_FAMILIES["olive"]["dark"], COLOR_FAMILIES["orange"]["dark"])
        y = np.arange(len(subset))
        ax.barh(y, subset["median"], color=colors, edgecolor=edges, linewidth=1.0)
        ax.errorbar(
            subset["median"],
            y,
            xerr=[subset["median"] - subset["bootstrap_ci_low"], subset["bootstrap_ci_high"] - subset["median"]],
            fmt="none",
            ecolor=TOKENS["ink"],
            elinewidth=0.9,
            capsize=2,
        )
        ax.set_yticks(y, [shorten_label(label, 28) for label in subset["factor_value"]])
        ax.axvline(0, color=TOKENS["ink"], linestyle=":", linewidth=1.0)
        ax.set_title(metric, fontsize=10, color=TOKENS["ink"])
        ax.set_xlabel("Median event-centered residual")
    add_chart_header(
        fig,
        axes[0],
        "Station geomorphology remains a useful residual grouping",
        "Top absolute 3-5 sec station-geomorphology effects by metric; intervals are bootstrap median intervals over event-station pairs.",
    )
    return save_figure(fig, figures_dir / "fig_11_geomorphology_effects.png")


def plot_path_azimuth_heatmap(path_azimuth_summary: pd.DataFrame, figures_dir: Path) -> Path:
    plot_df = path_azimuth_summary.loc[path_azimuth_summary["metric"].eq("PGA") & path_azimuth_summary["band"].eq("3-5 sec")].copy()
    if plot_df.empty:
        return figures_dir / "fig_12_path_azimuth_pga_heatmap.png"
    keep_paths = (
        plot_df.groupby("path_class")["rows"].sum().sort_values(ascending=False).head(7).index.tolist()
    )
    matrix = (
        plot_df.loc[plot_df["path_class"].isin(keep_paths)]
        .pivot_table(index="path_class", columns="azimuth_sector", values="median", aggfunc="median")
        .reindex(columns=SECTOR_ORDER)
    )
    matrix = matrix.loc[keep_paths]
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    vmax = max(0.2, float(np.nanpercentile(np.abs(matrix.to_numpy(dtype=float)), 95)))
    if sns is not None:
        sns.heatmap(matrix, ax=ax, cmap="coolwarm", vmin=-vmax, vmax=vmax, center=0.0, linewidths=1.0, linecolor=TOKENS["panel"], annot=True, fmt=".2f")
    else:
        im = ax.imshow(matrix.to_numpy(dtype=float), cmap="coolwarm", vmin=-vmax, vmax=vmax, aspect="auto")
        ax.set_xticks(np.arange(matrix.shape[1]), matrix.columns)
        ax.set_yticks(np.arange(matrix.shape[0]), matrix.index)
        fig.colorbar(im, ax=ax)
    ax.set_xlabel("Path azimuth sector")
    ax.set_ylabel("Path class")
    add_chart_header(
        fig,
        ax,
        "PGA residuals vary with path azimuth and corridor type",
        "Cells show median event-centered PGA residuals in the 3-5 sec band, grouped by source-to-station azimuth and mapped path class.",
    )
    return save_figure(fig, figures_dir / "fig_12_path_azimuth_pga_heatmap.png")


def shorten_label(value: object, width: int) -> str:
    text = str(value)
    if len(text) <= width:
        return text
    return textwrap.shorten(text, width=width, placeholder="...")


def write_report_scaffold(path: Path, manifest: dict[str, object]) -> None:
    path.write_text(
        "\n".join(
            [
                "# CVM-SI Extended Interaction Scan",
                "",
                "This second-pass scan broadens the first hypothesis study beyond event-demeaned diagnostic maps.",
                "Event-centered residuals remain useful for descriptive grouping, but the mixed-effects tables use raw log2(obs/syn) residuals with station and event random intercepts.",
                "",
                "## Output Tables",
                "",
                "- `source_event_summary.csv`: event-level residuals with magnitude, depth, mechanism, source region, geomorphology, and support.",
                "- `source_factor_summary.csv`: event-level source factor summaries.",
                "- `distance_attenuation_summary.csv`: distance-bin residuals by band and path class.",
                "- `distance_regression.csv`: OLS attenuation/path regressions with HC3 standard errors.",
                "- `geomorphology_summary.csv`: station/event geomorphology and geologic-map descriptive effects.",
                "- `component_azimuth_summary.csv`: component residuals by path azimuth sector.",
                "- `path_azimuth_summary.csv`: path-class residuals by azimuth sector.",
                "- `support_effects.csv`: Spearman checks for station/event support associations.",
                "- `band_contrast_driver_regression.csv`: within-pair period-contrast regressions.",
                "- `interaction_mixed_effects.csv`: mixed-effects source/path/site/frequency interaction models.",
                "",
                "## Figures",
                "",
                *[f"- `{Path(item).name}`" for item in manifest.get("figures", [])],
                "",
                "## Interpretation Notes",
                "",
                "- Treat this as hypothesis-generating evidence, not a final causal model.",
                "- Compare descriptive event-centered effects with raw-residual mixed-effects terms before asserting a physical interpretation.",
                "- Strong terms with weak support or uneven azimuth/station coverage should be followed by waveform examples and model cross sections.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
