#!/usr/bin/env python3
"""Build targeted CVM-SI waveform and model case studies.

This private analysis script turns the strongest path-azimuth/component
residual patterns into concrete examples. It selects event-station pairs that
have both observed gmprocess pickles and CVM-SI ASDF synthetics, then writes
case tables, waveform comparison panels, and CVM-SI Vs cross sections.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import pickle
from pathlib import Path
import sys
from typing import Sequence

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.legend import Legend
from matplotlib.text import Text
from matplotlib.ticker import FuncFormatter
from matplotlib.colors import Normalize
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.geometry import shape


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

DEFAULT_ANALYSIS_ROOT = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/analysis/cvmsi_hypothesis_study")
DEFAULT_OUTPUT = DEFAULT_ANALYSIS_ROOT / "case_studies"
DEFAULT_OBS_DIR = Path("/project2/jvidale_1700/data/all_merged_gmprocess/5_comp")
DEFAULT_SYN_DIR = Path("/project2/jvidale_1700/ValidationToolkit/_synthetic_inventory/converted/cvmsi_20260506_material_0p6x1p2_asdf")
DEFAULT_REGIONS = Path("/project2/jvidale_1700/spatial-vtk/runs/inputs/geospatial/regions_updated.geojson")
DEFAULT_MODEL_H5 = Path(
    "/project2/jvidale_1700/Salvus_HPC/codebase/slurm_material_meshes/"
    "cvmsi_0.6x1.2_slurm_meshing/cvmsi_0.6x1.2_material_CSrules.h5"
)
CVM_UTM = "EPSG:32611"
WGS84 = "EPSG:4326"
WEB_MERCATOR = "EPSG:3857"
DEFAULT_BASEMAP_SOURCE = "CartoDB.Positron"
FIELD_INDEX = {"rho": 2, "vp": 3, "vs": 4}
SECTOR_ORDER = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
TARGET_SPECS = (
    ("case_a_crosses_la_basin_se", "crosses LA basin", "SE", "high"),
    ("case_b_terminates_la_basin_w", "terminates in LA basin", "W", "high"),
    ("case_c_other_basin_sw", "other basin-influenced", "SW", "high"),
    ("case_d_mountain_control_e", "mountain to mountain", "E", "low"),
)
COMPONENTS = ("R", "T", "Z")
TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}
COLORS = {
    "observed": "#1F2430",
    "synthetic": "#CC6F47",
    "case": "#5477C4",
    "low": "#2E4780",
    "section": "#A3BEFA",
}


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    path_class: str
    azimuth_sector: str
    mode: str


@dataclass(frozen=True)
class FigureResult:
    path: Path
    qa: dict[str, object]


@dataclass
class ModelSampler:
    h5_path: Path
    node_stride: int = 4

    def __post_init__(self) -> None:
        self.coords: np.ndarray | None = None
        self.values: dict[str, np.ndarray] = {}
        self.tree: cKDTree | None = None

    def load(self) -> None:
        if self.tree is not None:
            return
        with h5py.File(self.h5_path, "r") as h5:
            coords = np.asarray(h5["/MODEL/coordinates"][:: self.node_stride], dtype=np.float64).reshape(-1, 3)
            data = h5["/MODEL/data"]
            values = {
                field: np.asarray(data[:: self.node_stride, index, :], dtype=np.float32).reshape(-1)
                for field, index in FIELD_INDEX.items()
            }
        finite = np.isfinite(coords).all(axis=1)
        for value in values.values():
            finite &= np.isfinite(value)
        self.coords = coords[finite]
        self.values = {field: value[finite] for field, value in values.items()}
        self.tree = cKDTree(self.coords)

    def sample(self, xyz: np.ndarray) -> pd.DataFrame:
        self.load()
        assert self.tree is not None
        distances, indices = self.tree.query(np.asarray(xyz, dtype=np.float64), k=1, workers=1)
        out = pd.DataFrame({"sample_distance_m": distances.astype(float)})
        for field, value in self.values.items():
            out[field] = value[indices].astype(float)
        return out


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-root", type=Path, default=DEFAULT_ANALYSIS_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--obs-dir", type=Path, default=DEFAULT_OBS_DIR)
    parser.add_argument("--synthetic-dir", type=Path, default=DEFAULT_SYN_DIR)
    parser.add_argument("--regions", type=Path, default=DEFAULT_REGIONS)
    parser.add_argument("--model-h5", type=Path, default=DEFAULT_MODEL_H5)
    parser.add_argument("--model-node-stride", type=int, default=4)
    parser.add_argument("--max-candidates-per-cell", type=int, default=80)
    parser.add_argument("--basemap-source", default=DEFAULT_BASEMAP_SOURCE)
    parser.add_argument("--basemap-zoom", type=int, default=9)
    parser.add_argument("--basemap-cache-dir", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = args.output_dir.expanduser().resolve()
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    report_dir = output_dir / "report"
    for directory in (tables_dir, figures_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)
    set_plot_theme()
    basemap_cache_dir = args.basemap_cache_dir or (output_dir / "basemap_cache")

    pairs = load_pair_rows(args.analysis_root / "tables" / "pairs.parquet")
    cases = select_cases(
        pairs,
        obs_dir=args.obs_dir,
        synthetic_dir=args.synthetic_dir,
        max_candidates_per_cell=args.max_candidates_per_cell,
    )
    if cases.empty:
        raise RuntimeError("No event-station cases with observed and synthetic waveforms were found.")
    cases.to_csv(tables_dir / "case_selection.csv", index=False)

    regions = load_regions(args.regions)
    sampler = ModelSampler(args.model_h5, node_stride=args.model_node_stride)
    cross_sections = build_cross_sections(cases, sampler)
    cross_sections.to_csv(tables_dir / "case_cross_section_samples.csv", index=False)
    waveform_ratios = build_waveform_ratio_table(cases, args.obs_dir, args.synthetic_dir)
    waveform_ratios.to_csv(tables_dir / "case_waveform_peak_ratios.csv", index=False)

    figure_records = [
        plot_corridors_and_sections(
            cases,
            cross_sections,
            regions,
            figures_dir,
            basemap_source=str(args.basemap_source),
            basemap_cache_dir=basemap_cache_dir,
            basemap_zoom=args.basemap_zoom,
        ),
        plot_waveform_examples(cases, args.obs_dir, args.synthetic_dir, figures_dir, waveform_ratios),
    ]
    figure_paths = [record.path for record in figure_records]
    figure_qa = [record.qa for record in figure_records]
    (output_dir / "figure_qa.json").write_text(json.dumps(figure_qa, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_figure_qa_report(report_dir / "figure_qa.md", figure_records)
    write_report(report_dir / "cvmsi_case_study_notes.md", cases, figure_paths, waveform_ratios)

    manifest = {
        "inputs": {
            "analysis_root": str(args.analysis_root),
            "obs_dir": str(args.obs_dir),
            "synthetic_dir": str(args.synthetic_dir),
            "model_h5": str(args.model_h5),
            "regions": str(args.regions),
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
            "cases": int(len(cases)),
            "cross_section_samples": int(len(cross_sections)),
            "waveform_ratio_rows": int(len(waveform_ratios)),
        },
        "figures": [str(path) for path in figure_paths],
        "figure_qa": figure_qa,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def set_plot_theme() -> None:
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
            "legend.fontsize": 10,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
        }
    )


def load_pair_rows(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df = df.loc[df["metric"].astype(str).eq("PGA") & df["band"].astype(str).eq("3-5 sec")].copy()
    df["station"] = df["station"].astype(str)
    df["event_id"] = df["event_id"].astype(str)
    df["azimuth_sector"] = sectorize(df["azimuth_deg"])
    return df.replace([np.inf, -np.inf], np.nan)


def sectorize(values: pd.Series) -> pd.Categorical:
    numeric = pd.to_numeric(values, errors="coerce")
    labels = pd.Series(np.nan, index=values.index, dtype=object)
    valid = numeric.notna()
    labels.loc[valid] = [SECTOR_ORDER[int(((float(value) + 22.5) % 360.0) // 45.0) % 8] for value in numeric.loc[valid]]
    return pd.Categorical(labels, categories=SECTOR_ORDER, ordered=True)


def select_cases(
    pairs: pd.DataFrame,
    *,
    obs_dir: Path,
    synthetic_dir: Path,
    max_candidates_per_cell: int,
) -> pd.DataFrame:
    obs_events = {path.name.replace("_proc.pkl", "") for path in obs_dir.glob("*_proc.pkl")}
    synthetic_events = {path.stem for path in synthetic_dir.glob("*.asdf")}
    available_events = obs_events & synthetic_events
    rows = []
    station_cache: dict[tuple[str, str], bool] = {}
    for case_id, path_class, azimuth_sector, mode in TARGET_SPECS:
        subset = pairs.loc[
            pairs["event_id"].isin(available_events)
            & pairs["path_class"].astype(str).eq(path_class)
            & pairs["azimuth_sector"].astype(str).eq(azimuth_sector)
        ].copy()
        subset = subset.sort_values("residual_event_centered", ascending=mode == "low").head(max_candidates_per_cell)
        selected = None
        for row in subset.itertuples(index=False):
            key = (row.event_id, row.station)
            if key not in station_cache:
                station_cache[key] = has_waveforms(row.event_id, row.station, obs_dir, synthetic_dir)
            if station_cache[key]:
                selected = row
                break
        if selected is None:
            continue
        record = selected._asdict()
        record["case_id"] = case_id
        record["selection_path_class"] = path_class
        record["selection_azimuth_sector"] = azimuth_sector
        record["selection_mode"] = mode
        rows.append(record)
    out = pd.DataFrame(rows)
    keep = [
        "case_id",
        "event_id",
        "station",
        "selection_path_class",
        "selection_azimuth_sector",
        "selection_mode",
        "path_class",
        "azimuth_sector",
        "log2_residual",
        "residual_event_centered",
        "distance_km",
        "azimuth_deg",
        "backazimuth_deg",
        "magnitude",
        "event_depth_km",
        "event_lon",
        "event_lat",
        "sta_lon",
        "sta_lat",
        "event_region",
        "station_region",
        "station_region_type",
        "station_geomorphology",
        "geologic_description",
        "path_basin_fraction",
        "path_la_basin_fraction",
        "model_0m_vs",
        "model_1000m_vs",
        "model_0m_impedance",
        "model_1000m_impedance",
    ]
    return out[[column for column in keep if column in out.columns]]


def has_waveforms(event_id: str, station: str, obs_dir: Path, synthetic_dir: Path) -> bool:
    obs_path = obs_dir / f"{event_id}_proc.pkl"
    syn_path = synthetic_dir / f"{event_id}.asdf"
    if not obs_path.exists() or not syn_path.exists():
        return False
    try:
        obs = pickle.load(open(obs_path, "rb"))
        if not any(str(trace.stats.station) == str(station) for trace in obs):
            return False
        import pyasdf

        dataset = pyasdf.ASDFDataSet(str(syn_path), mode="r")
        return any(name.split(".")[-1] == str(station) for name in dataset.waveforms.list())
    except Exception:
        return False


def load_regions(path: Path) -> list[object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    regions = []
    for feature in payload.get("features", []):
        props = feature.get("properties") or {}
        geom = shape(feature.get("geometry"))
        regions.append((str(props.get("long_name") or props.get("name") or props.get("short_name") or "region"), geom))
    return regions


def build_cross_sections(cases: pd.DataFrame, sampler: ModelSampler) -> pd.DataFrame:
    transformer = Transformer.from_crs(WGS84, CVM_UTM, always_xy=True)
    rows = []
    n_distance = 95
    depths_km = np.linspace(0.0, 10.0, 61)
    for case in cases.itertuples(index=False):
        event_x, event_y = transformer.transform(float(case.event_lon), float(case.event_lat))
        sta_x, sta_y = transformer.transform(float(case.sta_lon), float(case.sta_lat))
        fractions = np.linspace(0.0, 1.0, n_distance)
        xs = event_x + (sta_x - event_x) * fractions
        ys = event_y + (sta_y - event_y) * fractions
        path_km = np.sqrt((sta_x - event_x) ** 2 + (sta_y - event_y) ** 2) / 1000.0
        xyz = []
        meta = []
        for ix, frac in enumerate(fractions):
            for depth_km in depths_km:
                xyz.append((xs[ix], ys[ix], -depth_km * 1000.0))
                meta.append((frac * path_km, depth_km))
        sampled = sampler.sample(np.asarray(xyz))
        for (distance_km, depth_km), sample in zip(meta, sampled.itertuples(index=False)):
            rows.append(
                {
                    "case_id": case.case_id,
                    "distance_along_path_km": float(distance_km),
                    "depth_km": float(depth_km),
                    "vs_m_per_s": float(sample.vs),
                    "vp_m_per_s": float(sample.vp),
                    "rho_kg_per_m3": float(sample.rho),
                    "sample_distance_m": float(sample.sample_distance_m),
                }
            )
    return pd.DataFrame(rows)


def plot_corridors_and_sections(
    cases: pd.DataFrame,
    sections: pd.DataFrame,
    regions: list[object],
    figures_dir: Path,
    *,
    basemap_source: str,
    basemap_cache_dir: Path,
    basemap_zoom: int | None,
) -> FigureResult:
    n = len(cases)
    fig, axes = plt.subplots(
        n,
        2,
        figsize=(17.0, 4.25 * n),
        constrained_layout=False,
        gridspec_kw={"width_ratios": [1.05, 2.25]},
    )
    if n == 1:
        axes = np.asarray([axes])
    map_transformer = Transformer.from_crs(WGS84, WEB_MERCATOR, always_xy=True)
    event_x, event_y = map_transformer.transform(
        cases["event_lon"].to_numpy(dtype=float),
        cases["event_lat"].to_numpy(dtype=float),
    )
    sta_x, sta_y = map_transformer.transform(
        cases["sta_lon"].to_numpy(dtype=float),
        cases["sta_lat"].to_numpy(dtype=float),
    )
    x_min = float(min(np.nanmin(event_x), np.nanmin(sta_x)))
    x_max = float(max(np.nanmax(event_x), np.nanmax(sta_x)))
    y_min = float(min(np.nanmin(event_y), np.nanmin(sta_y)))
    y_max = float(max(np.nanmax(event_y), np.nanmax(sta_y)))
    pad = max(25_000.0, 0.055 * max(x_max - x_min, y_max - y_min))
    xlim = (x_min - pad, x_max + pad)
    ylim = (y_min - pad, y_max + pad)
    projected_regions = [(name, project_geometry(geom, map_transformer)) for name, geom in regions]
    basemap_records: list[dict[str, object]] = []
    image = None
    for ax_map, ax_sec, case in zip(axes[:, 0], axes[:, 1], cases.itertuples(index=False)):
        event_map_x, event_map_y = map_transformer.transform(float(case.event_lon), float(case.event_lat))
        sta_map_x, sta_map_y = map_transformer.transform(float(case.sta_lon), float(case.sta_lat))
        ax_map.set_xlim(*xlim)
        ax_map.set_ylim(*ylim)
        ok, source = add_required_basemap(
            ax_map,
            source=basemap_source,
            cache_dir=basemap_cache_dir,
            zoom=basemap_zoom,
            crs=WEB_MERCATOR,
        )
        basemap_records.append({"case_id": str(case.case_id), "ok": bool(ok), "source": str(source)})
        for _, geom in projected_regions:
            plot_geometry_boundary(ax_map, geom, color="#FFFFFF", linewidth=0.8, alpha=0.82, zorder=2.0)
        ax_map.plot(
            [event_map_x, sta_map_x],
            [event_map_y, sta_map_y],
            color=COLORS["case"],
            linewidth=1.7,
            zorder=3.4,
        )
        ax_map.scatter(
            [event_map_x],
            [event_map_y],
            marker="*",
            s=105,
            color="#CC6F47",
            edgecolor=TOKENS["ink"],
            linewidth=0.6,
            label="Event",
            zorder=4.2,
        )
        ax_map.scatter(
            [sta_map_x],
            [sta_map_y],
            marker="^",
            s=82,
            color="#A3BEFA",
            edgecolor=TOKENS["ink"],
            linewidth=0.6,
            label="Station",
            zorder=4.2,
        )
        label_box = {"boxstyle": "round,pad=0.18", "facecolor": "#FFFFFF", "edgecolor": "none", "alpha": 0.78}
        ax_map.annotate(
            case.event_id,
            xy=(event_map_x, event_map_y),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8.8,
            color=TOKENS["ink"],
            ha="left",
            va="bottom",
            bbox=label_box,
            zorder=5,
        )
        ax_map.annotate(
            str(case.station),
            xy=(sta_map_x, sta_map_y),
            xytext=(5, -7),
            textcoords="offset points",
            fontsize=8.8,
            color=TOKENS["ink"],
            ha="left",
            va="top",
            bbox=label_box,
            zorder=5,
        )
        ax_map.set_xlim(*xlim)
        ax_map.set_ylim(*ylim)
        ax_map.set_aspect("equal", adjustable="box")
        format_projected_map_axis(ax_map)
        ax_map.grid(color="#FFFFFF", linewidth=0.55, alpha=0.55, zorder=1.1)
        ax_map.set_title(
            f"{case.case_id}: {case.path_class}, {case.azimuth_sector}",
            fontsize=11,
            color=TOKENS["ink"],
        )
        subset = sections.loc[sections["case_id"].eq(case.case_id)]
        matrix = subset.pivot_table(index="depth_km", columns="distance_along_path_km", values="vs_m_per_s", aggfunc="median").sort_index()
        image = ax_sec.imshow(
            matrix.to_numpy(),
            extent=[matrix.columns.min(), matrix.columns.max(), matrix.index.max(), matrix.index.min()],
            aspect="auto",
            cmap="viridis",
            norm=Normalize(vmin=500, vmax=4200),
        )
        ax_sec.scatter([0.0], [0.0], marker="*", s=80, color="#CC6F47", edgecolor=TOKENS["ink"], linewidth=0.5, clip_on=False)
        ax_sec.scatter(
            [float(matrix.columns.max())],
            [0.0],
            marker="^",
            s=65,
            color="#FFFFFF",
            edgecolor=TOKENS["ink"],
            linewidth=0.7,
            clip_on=False,
        )
        ax_sec.set_xlabel("Distance from event (km)")
        ax_sec.set_ylabel("Depth (km)")
        ax_sec.set_ylim(10.0, -0.35)
        ax_sec.set_title(
            f"PGA 3-5 residual={case.log2_residual:+.2f}, event-centered={case.residual_event_centered:+.2f}",
            fontsize=11,
            color=TOKENS["ink"],
        )
    axes[0, 0].legend(loc="lower left", frameon=True, facecolor="#FFFFFF", edgecolor="none", framealpha=0.78, fontsize=10)
    add_header(
        fig,
        "Targeted residual corridors through CVM-SI",
        "Selected event-station pairs have observed and synthetic waveforms; sections sample CVM-SI Vs along each source-to-station corridor.",
        top=0.905,
        bottom=0.075,
        left=0.055,
        right=0.905,
        hspace=0.72,
        wspace=0.30,
    )
    if image is None:
        raise RuntimeError("No CVM-SI section image was created for the corridor figure.")
    cbar_ax = fig.add_axes([0.928, 0.115, 0.014, 0.735])
    cbar = fig.colorbar(image, cax=cbar_ax)
    cbar.set_label("CVM-SI Vs (m/s)")
    cbar.ax.tick_params(labelsize=10)
    cbar.ax.yaxis.label.set_size(11.5)
    qa = collect_layout_qa(fig, "fig_13_case_study_corridors_and_cvm_sections.png")
    qa["basemap_records"] = basemap_records
    qa["basemap_required"] = True
    path = save_figure(fig, figures_dir / "fig_13_case_study_corridors_and_cvm_sections.png")
    qa["png_path"] = str(path)
    qa["svg_path"] = str(path.with_suffix(".svg"))
    return FigureResult(path=path, qa=qa)


def add_required_basemap(ax: plt.Axes, *, source: str, cache_dir: Path, zoom: int | None, crs: str) -> tuple[bool, str]:
    from spatial_vtk.spatial.map.basemaps import add_contextily_basemap

    ok, resolved_source = add_contextily_basemap(
        ax,
        crs=crs,
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
    return ok, resolved_source


def project_geometry(geom: object, transformer: Transformer) -> object:
    from shapely.ops import transform as transform_geometry

    return transform_geometry(transformer.transform, geom)


def format_projected_map_axis(ax: plt.Axes) -> None:
    ax.set_aspect("equal", adjustable="box")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000.0:.0f}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000.0:.0f}"))
    ax.set_xlabel("Web Mercator x (km)")
    ax.set_ylabel("Web Mercator y (km)")


def plot_geometry_boundary(ax: plt.Axes, geom: object, **kwargs: object) -> None:
    if geom.geom_type == "Polygon":
        x, y = geom.exterior.xy
        ax.plot(x, y, **kwargs)
    elif geom.geom_type == "MultiPolygon":
        for part in geom.geoms:
            x, y = part.exterior.xy
            ax.plot(x, y, **kwargs)


def build_waveform_ratio_table(cases: pd.DataFrame, obs_dir: Path, synthetic_dir: Path) -> pd.DataFrame:
    rows = []
    for case in cases.itertuples(index=False):
        origin = load_origin_time(obs_dir / f"{case.event_id}.json")
        obs_stream = load_observed_stream(obs_dir / f"{case.event_id}_proc.pkl", str(case.station))
        syn_stream = load_synthetic_stream(synthetic_dir / f"{case.event_id}.asdf", str(case.station))
        for component in COMPONENTS:
            obs_trace = select_component(obs_stream, component)
            syn_trace = select_component(syn_stream, component)
            if obs_trace is None or syn_trace is None:
                continue
            _, obs_y = preprocess_trace(obs_trace, origin)
            _, syn_y = preprocess_trace(syn_trace, origin)
            obs_peak = float(np.nanmax(np.abs(obs_y)))
            syn_peak = float(np.nanmax(np.abs(syn_y)))
            ratio = obs_peak / syn_peak if np.isfinite(obs_peak) and np.isfinite(syn_peak) and syn_peak > 0 else np.nan
            rows.append(
                {
                    "case_id": case.case_id,
                    "event_id": case.event_id,
                    "station": case.station,
                    "component": component,
                    "obs_peak_3_5_sec": obs_peak,
                    "syn_peak_3_5_sec": syn_peak,
                    "obs_to_syn_peak_ratio": float(ratio),
                }
            )
    return pd.DataFrame(rows)


def plot_waveform_examples(
    cases: pd.DataFrame,
    obs_dir: Path,
    synthetic_dir: Path,
    figures_dir: Path,
    waveform_ratios: pd.DataFrame,
) -> FigureResult:
    n = len(cases)
    fig, axes = plt.subplots(n, len(COMPONENTS), figsize=(16, 3.15 * n), sharex=True, sharey=False)
    if n == 1:
        axes = np.asarray([axes])
    ratio_lookup = {
        (str(row.case_id), str(row.component)): float(row.obs_to_syn_peak_ratio)
        for row in waveform_ratios.itertuples(index=False)
    }
    for row_idx, case in enumerate(cases.itertuples(index=False)):
        origin = load_origin_time(obs_dir / f"{case.event_id}.json")
        obs_stream = load_observed_stream(obs_dir / f"{case.event_id}_proc.pkl", str(case.station))
        syn_stream = load_synthetic_stream(synthetic_dir / f"{case.event_id}.asdf", str(case.station))
        for col_idx, component in enumerate(COMPONENTS):
            ax = axes[row_idx, col_idx]
            obs_trace = select_component(obs_stream, component)
            syn_trace = select_component(syn_stream, component)
            if obs_trace is None or syn_trace is None:
                ax.text(0.5, 0.5, "missing", transform=ax.transAxes, ha="center", va="center")
                continue
            obs_t, obs_y = preprocess_trace(obs_trace, origin)
            syn_t, syn_y = preprocess_trace(syn_trace, origin)
            scale = np.nanmax(np.abs(obs_y))
            if not np.isfinite(scale) or scale <= 0:
                scale = 1.0
            ratio = ratio_lookup.get((str(case.case_id), component), np.nan)
            obs_norm = obs_y / scale
            syn_norm = syn_y / scale
            ax.plot(obs_t, obs_norm, color=COLORS["observed"], linewidth=1.0, label="Observed" if row_idx == 0 and col_idx == 0 else None)
            ax.plot(syn_t, syn_norm, color=COLORS["synthetic"], linewidth=0.9, alpha=0.9, label="Synthetic" if row_idx == 0 and col_idx == 0 else None)
            ax.axhline(0, color=TOKENS["grid"], linewidth=0.8)
            ax.set_xlim(0, 80)
            panel_limit = np.nanmax(np.abs(np.concatenate([obs_norm, syn_norm])))
            if not np.isfinite(panel_limit) or panel_limit <= 0:
                panel_limit = 1.0
            ax.set_ylim(-max(1.15, panel_limit * 1.08), max(1.15, panel_limit * 1.08))
            ax.set_title(f"{component} component, peak obs/syn={ratio:.1f}", fontsize=11, color=TOKENS["ink"])
            if col_idx == 0:
                ax.set_ylabel(f"{case.event_id}\n{case.station}\nnormalized")
            if row_idx == n - 1:
                ax.set_xlabel("Seconds after origin")
            ax.grid(True, color=TOKENS["grid"], linewidth=0.7)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper right", frameon=False, ncol=2, bbox_to_anchor=(0.965, 0.925), fontsize=11)
    add_header(
        fig,
        "Observed and CVM-SI synthetic waveform examples",
        "Traces are 3-5 sec bandpassed and scaled by observed component peak; smaller synthetic traces show underprediction in the selected residual cases.",
        top=0.885,
        bottom=0.060,
        left=0.075,
        right=0.985,
        hspace=0.78,
        wspace=0.28,
    )
    qa = collect_layout_qa(fig, "fig_14_case_study_waveform_examples.png")
    path = save_figure(fig, figures_dir / "fig_14_case_study_waveform_examples.png")
    qa["png_path"] = str(path)
    qa["svg_path"] = str(path.with_suffix(".svg"))
    return FigureResult(path=path, qa=qa)


def load_origin_time(path: Path):
    from obspy import UTCDateTime

    payload = json.loads(path.read_text(encoding="utf-8"))
    millis = payload.get("properties", {}).get("time")
    return UTCDateTime(float(millis) / 1000.0)


def load_observed_stream(path: Path, station: str):
    stream = pickle.load(open(path, "rb"))
    return stream.select(station=str(station)).copy()


def load_synthetic_stream(path: Path, station: str):
    import pyasdf

    dataset = pyasdf.ASDFDataSet(str(path), mode="r")
    station_key = next(name for name in dataset.waveforms.list() if name.split(".")[-1] == str(station))
    tags = dataset.waveforms[station_key].get_waveform_tags()
    return dataset.waveforms[station_key][tags[0]].copy()


def select_component(stream: object, component: str):
    for trace in stream:
        if str(trace.stats.channel).upper().endswith(component):
            return trace
    return None


def preprocess_trace(trace: object, origin: object) -> tuple[np.ndarray, np.ndarray]:
    tr = trace.copy()
    tr.detrend("demean")
    tr.detrend("linear")
    tr.taper(max_percentage=0.05)
    tr.filter("bandpass", freqmin=0.2, freqmax=1.0 / 3.0, corners=4, zerophase=True)
    try:
        tr.resample(50.0)
    except Exception:
        pass
    tr.trim(origin, origin + 80.0, pad=True, fill_value=0.0)
    times = tr.times(reftime=origin)
    return times, np.asarray(tr.data, dtype=float)


def add_header(
    fig: plt.Figure,
    title: str,
    subtitle: str,
    *,
    top: float = 0.90,
    bottom: float | None = None,
    left: float | None = None,
    right: float | None = None,
    hspace: float = 0.55,
    wspace: float = 0.25,
) -> None:
    adjust = {"top": top, "hspace": hspace, "wspace": wspace}
    if bottom is not None:
        adjust["bottom"] = bottom
    if left is not None:
        adjust["left"] = left
    if right is not None:
        adjust["right"] = right
    fig.subplots_adjust(**adjust)
    fig.text(0.055, 0.985, title, ha="left", va="top", fontsize=18, fontweight="semibold", color=TOKENS["ink"])
    fig.text(0.055, 0.947, subtitle, ha="left", va="top", fontsize=12, color=TOKENS["muted"])


def collect_layout_qa(fig: plt.Figure, figure_name: str) -> dict[str, object]:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    # The figures are exported with bbox_inches="tight"; use the same effective
    # bounds here so QA reflects the delivered PNG/SVG instead of the pre-tight
    # canvas.
    fig_bbox = fig.get_tightbbox(renderer).transformed(fig.dpi_scale_trans)
    tick_label_ids = {
        id(label)
        for ax in fig.axes
        for label in [*ax.get_xticklabels(), *ax.get_yticklabels()]
    }
    clipped_text: list[str] = []
    for text in fig.findobj(Text):
        if id(text) in tick_label_ids:
            continue
        value = text.get_text()
        if not text.get_visible() or not str(value).strip():
            continue
        bbox = text.get_window_extent(renderer=renderer)
        if bbox.width <= 0 or bbox.height <= 0:
            continue
        tolerance = 16.0
        if (
            bbox.x0 < fig_bbox.x0 - tolerance
            or bbox.y0 < fig_bbox.y0 - tolerance
            or bbox.x1 > fig_bbox.x1 + tolerance
            or bbox.y1 > fig_bbox.y1 + tolerance
        ):
            clipped_text.append(str(value).replace("\n", " ")[:120])

    axes_overlap_pairs: list[str] = []
    axes = [ax for ax in fig.axes if ax.get_visible()]
    for index, ax in enumerate(axes):
        bbox = ax.get_window_extent(renderer=renderer)
        for other_index, other_ax in enumerate(axes[index + 1 :], start=index + 1):
            other_bbox = other_ax.get_window_extent(renderer=renderer)
            overlap_width = max(0.0, min(bbox.x1, other_bbox.x1) - max(bbox.x0, other_bbox.x0))
            overlap_height = max(0.0, min(bbox.y1, other_bbox.y1) - max(bbox.y0, other_bbox.y0))
            if overlap_width * overlap_height > 4.0:
                axes_overlap_pairs.append(f"axes_{index}_axes_{other_index}")

    visible_legends = [legend for legend in fig.findobj(Legend) if legend.get_visible()]
    return {
        "figure": figure_name,
        "programmatic_checks": {
            "text_clipped": len(clipped_text) == 0,
            "clipped_text_count": len(clipped_text),
            "clipped_text_examples": clipped_text[:10],
            "axes_overlap": len(axes_overlap_pairs) == 0,
            "axes_overlap_count": len(axes_overlap_pairs),
            "axes_overlap_examples": axes_overlap_pairs[:10],
            "visible_legend_count": len(visible_legends),
        },
        "manual_review": {
            "status": "pending visual inspection after export",
            "items": ["text", "colorbars", "legends", "basemap under map panels"],
        },
    }


def save_figure(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220, bbox_inches="tight")
    fig.savefig(path.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)
    return path


def write_figure_qa_report(path: Path, figure_records: list[FigureResult]) -> None:
    lines = [
        "# Case-Study Figure QA",
        "",
        "Programmatic checks were run on the Matplotlib layout before export. Manual visual inspection is still required after copying the rendered PNGs back locally.",
        "",
    ]
    for record in figure_records:
        checks = dict(record.qa.get("programmatic_checks", {}))
        lines.extend(
            [
                f"## {record.path.name}",
                "",
                f"- Text clipped: {checks.get('clipped_text_count', 'unknown')}",
                f"- Axes overlaps: {checks.get('axes_overlap_count', 'unknown')}",
                f"- Visible legends: {checks.get('visible_legend_count', 'unknown')}",
            ]
        )
        basemap_records = record.qa.get("basemap_records")
        if isinstance(basemap_records, list):
            sources = sorted({str(item.get("source")) for item in basemap_records if isinstance(item, dict)})
            lines.append(f"- Basemap sources: {', '.join(sources)}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_report(path: Path, cases: pd.DataFrame, figure_paths: list[Path], waveform_ratios: pd.DataFrame) -> None:
    lines = [
        "# CVM-SI Targeted Case Studies",
        "",
        "These cases are selected from high-support PGA 3-5 sec path-azimuth bins and require both observed gmprocess waveforms and CVM-SI ASDF synthetics.",
        "",
        "## Figures",
        "",
        *[f"- `{figure.name}`" for figure in figure_paths],
        "",
        "## Selected Cases",
        "",
    ]
    for case in cases.itertuples(index=False):
        lines.extend(
            [
                f"### {case.case_id}",
                "",
                f"- Event/station: `{case.event_id}` / `{case.station}`",
                f"- Path/azimuth: {case.path_class}, {case.azimuth_sector} ({case.azimuth_deg:.1f} degrees)",
                f"- PGA 3-5 sec residual: raw {case.log2_residual:+.2f}, event-centered {case.residual_event_centered:+.2f}",
                f"- Distance: {case.distance_km:.1f} km; basin path fraction {case.path_basin_fraction:.2f}; LA basin fraction {case.path_la_basin_fraction:.2f}",
                f"- Station context: {case.station_region}, {case.geologic_description}",
                f"- Peak observed/synthetic waveform ratios (R/T/Z): {format_case_ratios(waveform_ratios, str(case.case_id))}",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def format_case_ratios(waveform_ratios: pd.DataFrame, case_id: str) -> str:
    subset = waveform_ratios.loc[waveform_ratios["case_id"].astype(str).eq(case_id)].copy()
    if subset.empty:
        return "not available"
    values = []
    for component in COMPONENTS:
        component_rows = subset.loc[subset["component"].astype(str).eq(component)]
        if component_rows.empty:
            values.append("na")
            continue
        ratio = float(component_rows["obs_to_syn_peak_ratio"].iloc[0])
        values.append(f"{ratio:.1f}" if np.isfinite(ratio) else "na")
    return " / ".join(values)


if __name__ == "__main__":
    raise SystemExit(main())
