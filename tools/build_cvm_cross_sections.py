#!/usr/bin/env python
"""Build CVM-H/CVM-SI Vs cross-section figures for GeoJSON regions."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import string
from typing import Iterable

import h5py
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import numpy as np
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon, box, shape
from shapely.ops import transform as shapely_transform, unary_union


DEFAULT_GEOJSON = Path("/project2/jvidale_1700/spatial-vtk/runs/inputs/geospatial/regions_no_offshore.geojson")
DEFAULT_OUTPUT_DIR = Path("/project2/jvidale_1700/spatial-vtk/runs/outputs/cvm_cross_sections")
DEFAULT_MODELS = {
    "cvmsi": {
        "label": "CVM-SI",
        "h5": Path(
            "/project2/jvidale_1700/Salvus_HPC/codebase/slurm_material_meshes/"
            "cvmsi_0.6x1.2_slurm_meshing/cvmsi_0.6x1.2_material_CSrules.h5"
        ),
    },
    "cvmh": {
        "label": "CVM-H",
        "h5": Path(
            "/project2/jvidale_1700/Salvus_HPC/codebase/slurm_material_meshes/"
            "cvmh_0.6x1.2_slurm_meshing/cvmh_0.6x1.2_material_CSrules.h5"
        ),
    },
}
FIELD_INDEX = {"qkappa": 0, "qmu": 1, "rho": 2, "vp": 3, "vs": 4}
UTM_CRS = "EPSG:32611"
WGS84_CRS = "EPSG:4326"


@dataclass(frozen=True)
class RegionFeature:
    name: str
    properties: dict[str, object]
    geometry_lonlat: Polygon | MultiPolygon
    geometry_utm: Polygon | MultiPolygon
    outline_geometries_lonlat: tuple[object, ...] = ()


@dataclass(frozen=True)
class VerticalSection:
    label: str
    orientation: str
    fraction: float
    line_utm: LineString
    line_lonlat: LineString

    @property
    def title(self) -> str:
        midpoint = self.line_lonlat.interpolate(0.5, normalized=True)
        if self.orientation.lower() == "ns":
            orientation = "N-S"
            coordinate = f"Longitude {midpoint.x:.2f}°"
        elif self.orientation.lower() == "ew":
            orientation = "E-W"
            coordinate = f"Latitude {midpoint.y:.2f}°"
        else:
            orientation = self.orientation.upper()
            coordinate = f"Fraction {self.fraction:.2f}"
        return f"{self.label}-{self.label}' | {orientation} | {coordinate}"


@dataclass
class ModelSampler:
    model_key: str
    model_label: str
    h5_path: Path
    field: str = "vs"
    node_stride: int = 1

    def __post_init__(self) -> None:
        if self.field.lower() not in FIELD_INDEX:
            raise ValueError(f"Unsupported field {self.field!r}; choose one of {sorted(FIELD_INDEX)}")
        if self.node_stride < 1:
            raise ValueError("--node-stride must be >= 1")
        self._tree: cKDTree | None = None
        self._values: np.ndarray | None = None
        self._z_bounds_m: tuple[float, float] | None = None
        self._xyz_bounds_m: tuple[float, float, float, float, float, float] | None = None

    @property
    def z_bounds_m(self) -> tuple[float, float]:
        self._ensure_tree()
        assert self._z_bounds_m is not None
        return self._z_bounds_m

    @property
    def xy_bounds_m(self) -> tuple[float, float, float, float]:
        self._ensure_tree()
        assert self._xyz_bounds_m is not None
        minx, miny, _minz, maxx, maxy, _maxz = self._xyz_bounds_m
        return minx, miny, maxx, maxy

    def _ensure_tree(self) -> None:
        if self._tree is not None:
            return
        field_index = FIELD_INDEX[self.field.lower()]
        with h5py.File(self.h5_path, "r") as h5:
            coords = np.asarray(h5["/MODEL/coordinates"][:], dtype=np.float64).reshape(-1, 3)
            values = np.asarray(h5["/MODEL/data"][:, field_index, :], dtype=np.float64).reshape(-1)
        if self.node_stride > 1:
            coords = coords[:: self.node_stride]
            values = values[:: self.node_stride]
        finite = np.isfinite(coords).all(axis=1) & np.isfinite(values)
        coords = coords[finite]
        values = values[finite]
        self._z_bounds_m = (float(np.nanmin(coords[:, 2])), float(np.nanmax(coords[:, 2])))
        self._xyz_bounds_m = (
            float(np.nanmin(coords[:, 0])),
            float(np.nanmin(coords[:, 1])),
            float(np.nanmin(coords[:, 2])),
            float(np.nanmax(coords[:, 0])),
            float(np.nanmax(coords[:, 1])),
            float(np.nanmax(coords[:, 2])),
        )
        self._tree = cKDTree(coords)
        self._values = values

    def sample(self, points_xyz: np.ndarray, *, max_distance_m: float | None = None) -> np.ndarray:
        self._ensure_tree()
        assert self._tree is not None
        assert self._values is not None
        assert self._xyz_bounds_m is not None
        distances, indices = self._tree.query(points_xyz, k=1, workers=-1)
        out = self._values[indices].astype(float)
        minx, miny, minz, maxx, maxy, maxz = self._xyz_bounds_m
        outside = (
            (points_xyz[:, 0] < minx)
            | (points_xyz[:, 0] > maxx)
            | (points_xyz[:, 1] < miny)
            | (points_xyz[:, 1] > maxy)
            | (points_xyz[:, 2] < minz)
            | (points_xyz[:, 2] > maxz)
        )
        out[outside] = np.nan
        if max_distance_m is not None:
            out[np.asarray(distances) > float(max_distance_m)] = np.nan
        return out


def safe_token(value: object) -> str:
    text = str(value).strip().lower()
    token = "".join(ch if ch.isalnum() else "_" for ch in text)
    return "_".join(part for part in token.split("_") if part)


def display_name(properties: dict[str, object], fallback: str) -> str:
    for key in ("long_name", "short_name", "Subregion", "subregion", "Region", "region", "name", "Name"):
        value = properties.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return fallback


def load_region(geojson_path: Path, selector: str) -> RegionFeature:
    data = json.loads(Path(geojson_path).read_text(encoding="utf-8"))
    features = data.get("features", [data] if data.get("type") == "Feature" else [])
    if not features:
        raise ValueError(f"No GeoJSON features found in {geojson_path}")

    wanted = {selector.strip().lower(), safe_token(selector)}
    matches: list[RegionFeature] = []
    to_utm = Transformer.from_crs(WGS84_CRS, UTM_CRS, always_xy=True).transform
    selector_token = safe_token(selector)
    if selector.strip().lower() in {"all", "full"} or selector_token in {"all_regions", "all_regions_no_offshore", "full_region"}:
        geometries = [shape(feature.get("geometry")) for feature in features]
        geometry = unary_union(geometries)
        return RegionFeature(
            name="All Regions No Offshore",
            properties={"selector": selector, "feature_count": len(features)},
            geometry_lonlat=geometry,
            geometry_utm=shapely_transform(to_utm, geometry),
            outline_geometries_lonlat=tuple(geometries),
        )
    for index, feature in enumerate(features, start=1):
        properties = dict(feature.get("properties") or {})
        geometry = shape(feature.get("geometry"))
        name = display_name(properties, f"feature_{index}")
        searchable = {name, safe_token(name)}
        searchable.update(str(value) for value in properties.values() if value is not None)
        searchable.update(safe_token(value) for value in properties.values() if value is not None)
        if not wanted.intersection({str(item).strip().lower() for item in searchable}):
            continue
        matches.append(
            RegionFeature(
                name=name,
                properties=properties,
                geometry_lonlat=geometry,
                geometry_utm=shapely_transform(to_utm, geometry),
            )
        )
    if not matches:
        examples = ", ".join(
            display_name(dict(f.get("properties") or {}), f"feature_{i}")
            for i, f in enumerate(features[:10], start=1)
        )
        raise ValueError(f"No GeoJSON region matched {selector!r}. Examples: {examples}")
    if len(matches) > 1:
        labels = ", ".join(match.name for match in matches)
        raise ValueError(f"Selector {selector!r} matched multiple regions: {labels}")
    return matches[0]


def label_sequence(count: int) -> list[str]:
    letters = list(string.ascii_uppercase)
    labels: list[str] = []
    for index in range(count):
        if index < len(letters):
            labels.append(letters[index])
        else:
            labels.append(f"A{index - len(letters) + 1}")
    return labels


def sections_from_fractions(
    region: RegionFeature,
    specs: dict[str, list[float]],
    *,
    bounds_utm: tuple[float, float, float, float] | None = None,
) -> list[VerticalSection]:
    minx, miny, maxx, maxy = bounds_utm or region.geometry_utm.bounds
    spanx = maxx - minx
    spany = maxy - miny
    raw: list[tuple[str, float, LineString]] = []
    for orientation, fractions in specs.items():
        for fraction in fractions:
            if not 0.0 < fraction < 1.0:
                raise ValueError(f"Vertical-section fractions must be within (0, 1); got {fraction}")
            if orientation == "ns":
                x = minx + spanx * fraction
                line = LineString([(x, maxy), (x, miny)])
            elif orientation == "ew":
                y = maxy - spany * fraction
                line = LineString([(minx, y), (maxx, y)])
            else:
                raise ValueError(f"Unknown orientation {orientation!r}; use ns or ew")
            raw.append((orientation, fraction, line))
    labels = label_sequence(len(raw))
    to_lonlat = Transformer.from_crs(UTM_CRS, WGS84_CRS, always_xy=True).transform
    return [
        VerticalSection(
            label=labels[index],
            orientation=orientation,
            fraction=fraction,
            line_utm=line,
            line_lonlat=shapely_transform(to_lonlat, line),
        )
        for index, (orientation, fraction, line) in enumerate(raw)
    ]


def sections_from_spacing(
    region: RegionFeature,
    spacing_km: dict[str, float],
    *,
    bounds_utm: tuple[float, float, float, float] | None = None,
) -> list[VerticalSection]:
    minx, miny, maxx, maxy = bounds_utm or region.geometry_utm.bounds
    specs: dict[str, list[float]] = {}
    if "ns" in spacing_km:
        spacing_m = spacing_km["ns"] * 1000.0
        positions = np.arange(minx + spacing_m, maxx, spacing_m)
        specs["ns"] = [float((x - minx) / (maxx - minx)) for x in positions]
    if "ew" in spacing_km:
        spacing_m = spacing_km["ew"] * 1000.0
        positions = np.arange(maxy - spacing_m, miny, -spacing_m)
        specs["ew"] = [float((maxy - y) / (maxy - miny)) for y in positions]
    return sections_from_fractions(region, specs, bounds_utm=bounds_utm)


def longest_line(geometry: object) -> LineString | None:
    if geometry.is_empty:
        return None
    if isinstance(geometry, LineString):
        return geometry
    if isinstance(geometry, MultiLineString):
        return max(geometry.geoms, key=lambda line: line.length)
    lines = [geom for geom in getattr(geometry, "geoms", []) if isinstance(geom, LineString)]
    return max(lines, key=lambda line: line.length) if lines else None


def parse_fraction_specs(values: Iterable[str]) -> dict[str, list[float]]:
    specs: dict[str, list[float]] = {}
    for value in values:
        orientation, raw = split_spec(value)
        if raw.isdigit():
            count = int(raw)
            fractions = [(index + 1) / (count + 1) for index in range(count)]
        else:
            fractions = [float(item) for item in raw.split(",") if item.strip()]
        specs.setdefault(orientation, []).extend(fractions)
    return specs


def parse_spacing_specs(values: Iterable[str]) -> dict[str, float]:
    specs: dict[str, float] = {}
    for value in values:
        orientation, raw = split_spec(value)
        specs[orientation] = float(raw)
    return specs


def split_spec(value: str) -> tuple[str, str]:
    if ":" in value:
        left, right = value.split(":", 1)
    elif "=" in value:
        left, right = value.split("=", 1)
    else:
        raise ValueError(f"Expected ORIENTATION:VALUE, got {value!r}")
    orientation = left.strip().lower().replace("-", "")
    if orientation not in {"ns", "ew"}:
        raise ValueError(f"Unknown orientation {left!r}; use ns or ew")
    return orientation, right.strip()


def vertical_grid(
    section: VerticalSection,
    depth_min_km: float,
    depth_max_km: float,
    dx_km: float,
    dz_km: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    length_km = section.line_utm.length / 1000.0
    n_dist = max(2, int(math.ceil(length_km / dx_km)) + 1)
    depths = np.arange(depth_min_km, depth_max_km + dz_km * 0.5, dz_km)
    distances = np.linspace(0.0, length_km, n_dist)
    points_along = [section.line_utm.interpolate(distance * 1000.0) for distance in distances]
    xyz = np.empty((len(depths) * len(distances), 3), dtype=float)
    row = 0
    for depth in depths:
        z = -depth * 1000.0
        for point in points_along:
            xyz[row] = (point.x, point.y, z)
            row += 1
    return distances, depths, xyz


def sample_vertical_sections(
    sampler: ModelSampler,
    sections: list[VerticalSection],
    *,
    depth_min_km: float,
    depth_max_km: float | None,
    dx_km: float,
    dz_km: float,
    max_distance_m: float | None,
) -> list[tuple[VerticalSection, np.ndarray, np.ndarray, np.ndarray]]:
    min_z, max_z = sampler.z_bounds_m
    model_bottom_km = abs(min_z) / 1000.0
    model_top_km = max(0.0, -max_z / 1000.0)
    resolved_min = max(depth_min_km, model_top_km)
    resolved_max = min(depth_max_km if depth_max_km is not None else model_bottom_km, model_bottom_km)
    outputs = []
    for section in sections:
        distances, depths, xyz = vertical_grid(section, resolved_min, resolved_max, dx_km, dz_km)
        values = sampler.sample(xyz, max_distance_m=max_distance_m).reshape(len(depths), len(distances))
        outputs.append((section, distances, depths, values / 1000.0))
    return outputs


def horizontal_depths(sampler: ModelSampler, count: int | None, explicit_depths_km: list[float] | None) -> list[float]:
    if explicit_depths_km:
        return explicit_depths_km
    if count is None:
        return []
    min_z, max_z = sampler.z_bounds_m
    top = max(0.0, -max_z / 1000.0)
    bottom = abs(min_z) / 1000.0
    return [float(value) for value in np.linspace(top, bottom, int(count))]


def sample_horizontal_sections(
    sampler: ModelSampler,
    region: RegionFeature,
    depths_km: list[float],
    *,
    spacing_km: float,
    max_distance_m: float | None,
    bounds_utm: tuple[float, float, float, float] | None = None,
) -> list[tuple[float, np.ndarray, np.ndarray, np.ndarray]]:
    minx, miny, maxx, maxy = bounds_utm or region.geometry_utm.bounds
    spacing_m = spacing_km * 1000.0
    xs = np.arange(minx, maxx + spacing_m * 0.5, spacing_m)
    ys = np.arange(miny, maxy + spacing_m * 0.5, spacing_m)
    xx, yy = np.meshgrid(xs, ys)
    outputs = []
    for depth_km in depths_km:
        xyz = np.column_stack([xx.ravel(), yy.ravel(), np.full(xx.size, -depth_km * 1000.0)])
        values = sampler.sample(xyz, max_distance_m=max_distance_m).reshape(xx.shape) / 1000.0
        outputs.append((depth_km, xx, yy, values))
    return outputs


def sample_vs_threshold_depths(
    sampler: ModelSampler,
    region: RegionFeature,
    thresholds_kmps: list[float],
    *,
    spacing_km: float,
    depth_min_km: float,
    depth_max_km: float | None,
    dz_km: float,
    max_distance_m: float | None,
    bounds_utm: tuple[float, float, float, float] | None = None,
) -> list[tuple[float, np.ndarray, np.ndarray, np.ndarray]]:
    min_z, max_z = sampler.z_bounds_m
    model_bottom_km = abs(min_z) / 1000.0
    model_top_km = max(0.0, -max_z / 1000.0)
    resolved_min = max(depth_min_km, model_top_km)
    resolved_max = min(depth_max_km if depth_max_km is not None else model_bottom_km, model_bottom_km)
    if resolved_max < resolved_min:
        raise ValueError(f"Invalid depth interval {resolved_min:.2f}-{resolved_max:.2f} km")

    minx, miny, maxx, maxy = bounds_utm or region.geometry_utm.bounds
    spacing_m = spacing_km * 1000.0
    xs = np.arange(minx, maxx + spacing_m * 0.5, spacing_m)
    ys = np.arange(miny, maxy + spacing_m * 0.5, spacing_m)
    xx, yy = np.meshgrid(xs, ys)
    flat_xy = np.column_stack([xx.ravel(), yy.ravel()])
    depths = np.arange(resolved_min, resolved_max + dz_km * 0.5, dz_km)
    thresholds = [float(value) for value in thresholds_kmps]
    crossing = {threshold: np.full(xx.size, np.nan, dtype=float) for threshold in thresholds}
    previous_values: np.ndarray | None = None
    previous_depth: float | None = None

    for depth in depths:
        xyz = np.column_stack([flat_xy, np.full(xx.size, -float(depth) * 1000.0)])
        values = sampler.sample(xyz, max_distance_m=max_distance_m) / 1000.0
        finite = np.isfinite(values)
        for threshold in thresholds:
            target = crossing[threshold]
            unresolved = np.isnan(target)
            if previous_values is None or previous_depth is None:
                hit = unresolved & finite & (values >= threshold)
                target[hit] = float(depth)
                continue
            prev_finite = np.isfinite(previous_values)
            crossed = unresolved & finite & prev_finite & (previous_values < threshold) & (values >= threshold)
            if not np.any(crossed):
                continue
            denom = values[crossed] - previous_values[crossed]
            fraction = np.zeros_like(denom, dtype=float)
            nonzero = np.abs(denom) > 1.0e-12
            fraction[nonzero] = (threshold - previous_values[crossed][nonzero]) / denom[nonzero]
            target[crossed] = float(previous_depth) + fraction * (float(depth) - float(previous_depth))
        previous_values = values
        previous_depth = float(depth)

    outputs = []
    for threshold in thresholds:
        depth_grid = crossing[threshold].reshape(xx.shape)
        outputs.append((threshold, xx, yy, depth_grid))
    return outputs


def add_region_map(
    ax: plt.Axes,
    region: RegionFeature,
    *,
    sections: list[VerticalSection] | None = None,
    horizontal_box_lonlat: Polygon | None = None,
    title: str,
    basemap_source: str,
    basemap_zoom: int | None,
    basemap_cache_dir: Path,
) -> None:
    extent_geometry = horizontal_box_lonlat if horizontal_box_lonlat is not None else region.geometry_lonlat
    min_lon, min_lat, max_lon, max_lat = extent_geometry.bounds
    pad_lon = (max_lon - min_lon) * 0.12
    pad_lat = (max_lat - min_lat) * 0.12
    ax.set_xlim(min_lon - pad_lon, max_lon + pad_lon)
    ax.set_ylim(min_lat - pad_lat, max_lat + pad_lat)
    from spatial_vtk.spatial.map.basemaps import add_contextily_basemap

    add_contextily_basemap(
        ax,
        crs=WGS84_CRS,
        primary_source=basemap_source,
        fallback_sources=(),
        zoom=basemap_zoom,
        cache_dir=basemap_cache_dir,
        cache_download=True,
        on_error="raise",
    )
    plot_region_outlines(ax, region, color="white", linewidth=3.0, zorder=5)
    plot_region_outlines(ax, region, color="#111111", linewidth=1.25, zorder=6)
    if horizontal_box_lonlat is not None:
        plot_geometry_outline(ax, horizontal_box_lonlat, color="#ffcc33", linewidth=2.0, zorder=7)
    if sections:
        for section in sections:
            x, y = section.line_lonlat.xy
            ax.plot(x, y, color="#ffcc33", linewidth=2.0, zorder=8)
            endpoints = list(section.line_lonlat.coords)
            ax.text(
                endpoints[0][0],
                endpoints[0][1],
                section.label,
                ha="right",
                va="center",
                fontsize=8,
                weight="bold",
                color="black",
                bbox=label_box(),
                zorder=9,
            )
            ax.text(
                endpoints[-1][0],
                endpoints[-1][1],
                f"{section.label}'",
                ha="left",
                va="center",
                fontsize=8,
                weight="bold",
                color="black",
                bbox=label_box(),
                zorder=9,
            )
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, alpha=0.22, zorder=10)
    set_lonlat_equal_aspect(ax)


def plot_geometry_outline(ax: plt.Axes, geometry: object, *, color: str, linewidth: float, zorder: int) -> None:
    geoms = geometry.geoms if hasattr(geometry, "geoms") else [geometry]
    for geom in geoms:
        if not hasattr(geom, "exterior"):
            continue
        x, y = geom.exterior.xy
        ax.plot(x, y, color=color, linewidth=linewidth, zorder=zorder)
        for interior in getattr(geom, "interiors", []):
            ix, iy = interior.xy
            ax.plot(ix, iy, color=color, linewidth=max(0.6, linewidth * 0.6), zorder=zorder)


def plot_region_outlines(ax: plt.Axes, region: RegionFeature, *, color: str, linewidth: float, zorder: int) -> None:
    geometries = region.outline_geometries_lonlat or (region.geometry_lonlat,)
    for geometry in geometries:
        plot_geometry_outline(ax, geometry, color=color, linewidth=linewidth, zorder=zorder)


def region_box_lonlat(
    region: RegionFeature,
    *,
    bounds_utm: tuple[float, float, float, float] | None = None,
) -> Polygon:
    minx, miny, maxx, maxy = bounds_utm or region.geometry_utm.bounds
    to_lonlat = Transformer.from_crs(UTM_CRS, WGS84_CRS, always_xy=True).transform
    return shapely_transform(to_lonlat, box(minx, miny, maxx, maxy))


def set_lonlat_equal_aspect(ax: plt.Axes) -> None:
    lat_min, lat_max = ax.get_ylim()
    lat_mid = 0.5 * (float(lat_min) + float(lat_max))
    cos_lat = math.cos(math.radians(lat_mid))
    if math.isfinite(cos_lat) and abs(cos_lat) > 1.0e-6:
        ax.set_aspect(1.0 / cos_lat, adjustable="box")


def set_lonlat_box_limits(
    ax: plt.Axes,
    region: RegionFeature,
    *,
    bounds_utm: tuple[float, float, float, float] | None = None,
) -> None:
    min_lon, min_lat, max_lon, max_lat = region_box_lonlat(region, bounds_utm=bounds_utm).bounds
    ax.set_xlim(min_lon, max_lon)
    ax.set_ylim(min_lat, max_lat)
    set_lonlat_equal_aspect(ax)


def label_box() -> dict[str, object]:
    return {"boxstyle": "round,pad=0.18", "facecolor": "white", "edgecolor": "none", "alpha": 0.86}


def plot_vertical_figure(
    sampler: ModelSampler,
    region: RegionFeature,
    sampled_sections: list[tuple[VerticalSection, np.ndarray, np.ndarray, np.ndarray]],
    output_path: Path,
    *,
    basemap_source: str,
    basemap_zoom: int | None,
    basemap_cache_dir: Path,
    bounds_utm: tuple[float, float, float, float] | None = None,
) -> Path:
    all_values = np.concatenate([item[3].ravel() for item in sampled_sections])
    finite = all_values[np.isfinite(all_values)]
    if finite.size == 0:
        raise ValueError(f"No finite samples for {sampler.model_label} vertical sections")
    norm = Normalize(vmin=float(np.nanpercentile(finite, 2.0)), vmax=float(np.nanpercentile(finite, 98.0)))
    grouped_sections = group_vertical_sections_by_orientation(sampled_sections)
    row_count = max(len(group) for _, group in grouped_sections)
    section_col_count = len(grouped_sections)
    width = 13.5 if section_col_count == 1 else 18.5
    height = max(7.0, 2.05 * row_count)
    fig = plt.figure(figsize=(width, height), dpi=180, constrained_layout=True)
    gs = fig.add_gridspec(
        row_count,
        section_col_count + 1,
        width_ratios=[1.02, *([1.45] * section_col_count)],
    )
    map_ax = fig.add_subplot(gs[:, 0])
    all_sections = [item[0] for item in sampled_sections]
    add_region_map(
        map_ax,
        region,
        sections=all_sections,
        horizontal_box_lonlat=region_box_lonlat(region, bounds_utm=bounds_utm),
        title=f"{region.name}: {sampler.model_label} section map",
        basemap_source=basemap_source,
        basemap_zoom=basemap_zoom,
        basemap_cache_dir=basemap_cache_dir,
    )
    mappable = None
    section_axes: list[plt.Axes] = []
    for col_index, (orientation, group) in enumerate(grouped_sections, start=1):
        for row_index in range(row_count):
            ax = fig.add_subplot(gs[row_index, col_index])
            if row_index >= len(group):
                ax.axis("off")
                continue
            section, distances, depths, values = group[row_index]
            mappable = ax.pcolormesh(distances, depths, values, shading="auto", cmap="rainbow", norm=norm)
            ax.invert_yaxis()
            ax.set_title(section.title, pad=18)
            ax.set_ylabel("Depth (km)")
            add_cross_section_ticks(ax, section, all_sections)
            ax.text(
                0.01,
                0.05,
                section.label,
                transform=ax.transAxes,
                ha="left",
                va="bottom",
                fontsize=9,
                weight="bold",
                bbox=label_box(),
            )
            ax.text(
                0.99,
                0.05,
                f"{section.label}'",
                transform=ax.transAxes,
                ha="right",
                va="bottom",
                fontsize=9,
                weight="bold",
                bbox=label_box(),
            )
            if row_index == len(group) - 1:
                ax.set_xlabel("Distance along section (km)")
            ax.grid(True, alpha=0.18)
            section_axes.append(ax)
    assert mappable is not None
    cbar = fig.colorbar(mappable, ax=section_axes, pad=0.015, fraction=0.035)
    cbar.set_label("Vs (km/s)")
    fig.suptitle(f"{sampler.model_label} Vs Vertical Cross Sections: {region.name}", fontsize=14)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path


def add_cross_section_ticks(ax: plt.Axes, section: VerticalSection, all_sections: list[VerticalSection]) -> None:
    tick_items: list[tuple[float, str]] = []
    for other in all_sections:
        if other.label == section.label or other.orientation.lower() == section.orientation.lower():
            continue
        intersection = section.line_utm.intersection(other.line_utm)
        points = [intersection] if getattr(intersection, "geom_type", "") == "Point" else list(getattr(intersection, "geoms", []))
        for point in points:
            if getattr(point, "geom_type", "") != "Point":
                continue
            distance_km = section.line_utm.project(point) / 1000.0
            if -1.0e-6 <= distance_km <= section.line_utm.length / 1000.0 + 1.0e-6:
                tick_items.append((float(distance_km), other.label))
                break
    if not tick_items:
        return
    transform = ax.get_xaxis_transform()
    for distance_km, label in sorted(tick_items):
        ax.plot(
            [distance_km, distance_km],
            [1.0, 1.035],
            transform=transform,
            color="black",
            linewidth=0.8,
            clip_on=False,
            zorder=10,
        )
        ax.text(
            distance_km,
            1.04,
            label,
            transform=transform,
            ha="center",
            va="bottom",
            fontsize=7.5,
            weight="bold",
            color="black",
            bbox={"boxstyle": "round,pad=0.08", "facecolor": "white", "edgecolor": "none", "alpha": 0.72},
            clip_on=False,
            zorder=11,
        )


def group_vertical_sections_by_orientation(
    sampled_sections: list[tuple[VerticalSection, np.ndarray, np.ndarray, np.ndarray]],
) -> list[tuple[str, list[tuple[VerticalSection, np.ndarray, np.ndarray, np.ndarray]]]]:
    groups: dict[str, list[tuple[VerticalSection, np.ndarray, np.ndarray, np.ndarray]]] = {}
    for item in sampled_sections:
        groups.setdefault(item[0].orientation.lower(), []).append(item)
    ordered: list[tuple[str, list[tuple[VerticalSection, np.ndarray, np.ndarray, np.ndarray]]]] = []
    for orientation in ("ns", "ew"):
        if orientation in groups:
            ordered.append((orientation, groups.pop(orientation)))
    ordered.extend((orientation, group) for orientation, group in groups.items())
    return ordered


def plot_horizontal_figure(
    sampler: ModelSampler,
    region: RegionFeature,
    sampled_sections: list[tuple[float, np.ndarray, np.ndarray, np.ndarray]],
    output_path: Path,
    *,
    basemap_source: str,
    basemap_zoom: int | None,
    basemap_cache_dir: Path,
    bounds_utm: tuple[float, float, float, float] | None = None,
) -> Path:
    if not sampled_sections:
        return output_path
    all_values = np.concatenate([item[3].ravel() for item in sampled_sections])
    finite = all_values[np.isfinite(all_values)]
    if finite.size == 0:
        raise ValueError(f"No finite samples for {sampler.model_label} horizontal sections")
    norm = Normalize(vmin=float(np.nanpercentile(finite, 2.0)), vmax=float(np.nanpercentile(finite, 98.0)))
    count = len(sampled_sections)
    ncols = min(3, count)
    nrows = int(math.ceil(count / ncols))
    fig = plt.figure(figsize=(4.6 * (ncols + 1), 3.7 * max(1, nrows)), dpi=180, constrained_layout=True)
    gs = fig.add_gridspec(nrows, ncols + 1, width_ratios=[1.05, *([1.0] * ncols)])
    map_ax = fig.add_subplot(gs[:, 0])
    add_region_map(
        map_ax,
        region,
        horizontal_box_lonlat=region_box_lonlat(region, bounds_utm=bounds_utm),
        title=f"{region.name}: horizontal box",
        basemap_source=basemap_source,
        basemap_zoom=basemap_zoom,
        basemap_cache_dir=basemap_cache_dir,
    )
    to_lonlat_transformer = Transformer.from_crs(UTM_CRS, WGS84_CRS, always_xy=True)
    mappable = None
    for index, (depth_km, xx, yy, values) in enumerate(sampled_sections):
        row, col = divmod(index, ncols)
        ax = fig.add_subplot(gs[row, col + 1])
        lon, lat = to_lonlat_transformer.transform(xx, yy)
        mappable = ax.pcolormesh(lon, lat, values, shading="auto", cmap="rainbow", norm=norm)
        plot_region_outlines(ax, region, color="white", linewidth=1.7, zorder=5)
        plot_region_outlines(ax, region, color="#111111", linewidth=0.8, zorder=6)
        plot_geometry_outline(ax, region_box_lonlat(region, bounds_utm=bounds_utm), color="#ffcc33", linewidth=0.9, zorder=4)
        ax.set_title(f"Depth {depth_km:.2f} km")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(True, alpha=0.18)
        set_lonlat_box_limits(ax, region, bounds_utm=bounds_utm)
    for empty in range(count, nrows * ncols):
        row, col = divmod(empty, ncols)
        ax = fig.add_subplot(gs[row, col + 1])
        ax.axis("off")
    assert mappable is not None
    cbar = fig.colorbar(mappable, ax=fig.axes[1:], pad=0.015, fraction=0.035)
    cbar.set_label("Vs (km/s)")
    fig.suptitle(f"{sampler.model_label} Vs Horizontal Cross Sections: {region.name}", fontsize=14)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_threshold_depth_figure(
    sampler: ModelSampler,
    region: RegionFeature,
    sampled_thresholds: list[tuple[float, np.ndarray, np.ndarray, np.ndarray]],
    output_path: Path,
    *,
    basemap_source: str,
    basemap_zoom: int | None,
    basemap_cache_dir: Path,
    bounds_utm: tuple[float, float, float, float] | None = None,
) -> Path:
    if not sampled_thresholds:
        return output_path
    all_values = np.concatenate([item[3].ravel() for item in sampled_thresholds])
    finite = all_values[np.isfinite(all_values)]
    if finite.size == 0:
        raise ValueError(f"No finite Vs-threshold depths for {sampler.model_label}")
    vmax = max(0.5, float(np.nanpercentile(finite, 98.0)))
    thresholds_count = len(sampled_thresholds)
    fig = plt.figure(figsize=(5.0 * (thresholds_count + 1), 5.0), dpi=180, constrained_layout=True)
    gs = fig.add_gridspec(1, thresholds_count + 1, width_ratios=[1.05, *([1.0] * thresholds_count)])
    map_ax = fig.add_subplot(gs[0, 0])
    add_region_map(
        map_ax,
        region,
        horizontal_box_lonlat=region_box_lonlat(region, bounds_utm=bounds_utm),
        title=f"{region.name}: threshold map",
        basemap_source=basemap_source,
        basemap_zoom=basemap_zoom,
        basemap_cache_dir=basemap_cache_dir,
    )

    to_lonlat_transformer = Transformer.from_crs(UTM_CRS, WGS84_CRS, always_xy=True)
    panel_axes: list[plt.Axes] = []
    mappable = None
    for index, (threshold, xx, yy, depth_values) in enumerate(sampled_thresholds, start=1):
        ax = fig.add_subplot(gs[0, index])
        panel_axes.append(ax)
        lon, lat = to_lonlat_transformer.transform(xx, yy)
        mappable = ax.pcolormesh(lon, lat, depth_values, shading="auto", cmap="rainbow", vmin=0.0, vmax=vmax)
        add_depth_contours(ax, lon, lat, depth_values)
        plot_geometry_outline(ax, region_box_lonlat(region, bounds_utm=bounds_utm), color="#ffcc33", linewidth=0.9, zorder=4)
        plot_region_outlines(ax, region, color="white", linewidth=1.7, zorder=5)
        plot_region_outlines(ax, region, color="#111111", linewidth=0.8, zorder=6)
        ax.set_title(f"Depth to Vs = {threshold:g} km/s")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(True, alpha=0.18)
        set_lonlat_box_limits(ax, region, bounds_utm=bounds_utm)
    assert mappable is not None
    cbar = fig.colorbar(mappable, ax=panel_axes, pad=0.015, fraction=0.035)
    cbar.set_label("Depth (km)")
    fig.suptitle(f"{sampler.model_label} Depth to Vs Thresholds: {region.name}", fontsize=14)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path


def add_depth_contours(ax: plt.Axes, lon: np.ndarray, lat: np.ndarray, depth_values: np.ndarray) -> None:
    finite = depth_values[np.isfinite(depth_values)]
    if finite.size == 0:
        return
    min_depth = float(np.nanmin(finite))
    max_depth = float(np.nanmax(finite))
    if max_depth - min_depth < 0.25:
        return
    step = 0.5 if max_depth <= 5.0 else 1.0
    start = math.ceil(min_depth / step) * step
    stop = math.floor(max_depth / step) * step
    levels = np.arange(start, stop + step * 0.5, step)
    if levels.size == 0:
        return
    contours = ax.contour(lon, lat, depth_values, levels=levels, colors="black", linewidths=0.55, alpha=0.78)
    ax.clabel(contours, inline=True, fontsize=6.5, fmt=lambda value: f"{value:g} km")


def parse_depth_list(value: str | None) -> list[float] | None:
    if value is None or not value.strip():
        return None
    return [float(item) for item in value.split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geojson", type=Path, default=DEFAULT_GEOJSON)
    parser.add_argument("--region", default="San Joaquin Hills")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--models", nargs="+", default=["cvmsi", "cvmh"], choices=sorted(DEFAULT_MODELS))
    parser.add_argument("--field", default="vs", choices=sorted(FIELD_INDEX))
    parser.add_argument("--preset", choices=["san-joaquin-hills-test"], default=None)
    parser.add_argument(
        "--vertical",
        action="append",
        default=[],
        metavar="ORIENTATION:COUNT_OR_FRACTIONS",
        help="Examples: ns:2, ew:0.25,0.5,0.75",
    )
    parser.add_argument(
        "--vertical-spacing-km",
        action="append",
        default=[],
        metavar="ORIENTATION:KM",
        help="Examples: ns:1, ew:1",
    )
    parser.add_argument("--horizontal-count", type=int, default=0)
    parser.add_argument("--horizontal-depths-km", default=None, help="Comma-separated depths, e.g. 0,2,5")
    parser.add_argument("--vertical-dx-km", type=float, default=0.5)
    parser.add_argument("--vertical-dz-km", type=float, default=0.25)
    parser.add_argument("--depth-min-km", type=float, default=0.0)
    parser.add_argument("--depth-max-km", type=float, default=None)
    parser.add_argument("--horizontal-spacing-km", type=float, default=0.5)
    parser.add_argument("--threshold-depths-vs-kmps", default=None, help="Comma-separated Vs thresholds in km/s, e.g. 1.0,2.5")
    parser.add_argument("--threshold-depth-max-km", type=float, default=None)
    parser.add_argument("--threshold-dz-km", type=float, default=0.25)
    parser.add_argument("--bounds", choices=["region", "model"], default="region", help="Box used for sections and map panels.")
    parser.add_argument("--node-stride", type=int, default=1, help="Use every Nth mesh node for faster approximate sampling.")
    parser.add_argument("--max-nearest-distance-m", type=float, default=5000.0)
    parser.add_argument("--basemap-source", default="Esri.WorldImagery")
    parser.add_argument("--basemap-zoom", type=int, default=None)
    parser.add_argument("--basemap-cache-dir", type=Path, default=DEFAULT_OUTPUT_DIR / "basemap_cache")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.preset == "san-joaquin-hills-test":
        args.region = "San Joaquin Hills"
        args.vertical = ["ns:0.3333333333,0.6666666667", "ew:0.25,0.5,0.75"]
        args.horizontal_count = 0
        if args.depth_max_km is None:
            args.depth_max_km = 12.0
    region = load_region(args.geojson, args.region)
    vertical_specs = parse_fraction_specs(args.vertical)
    spacing_specs = parse_spacing_specs(args.vertical_spacing_km)
    has_vertical_request = bool(vertical_specs or spacing_specs)
    if not has_vertical_request and not args.horizontal_count and not args.horizontal_depths_km and not args.threshold_depths_vs_kmps:
        raise ValueError(
            "No sections requested. Use --vertical, --vertical-spacing-km, --horizontal-count, "
            "--horizontal-depths-km, --threshold-depths-vs-kmps, or --preset."
        )

    written: list[Path] = []
    for model_key in args.models:
        model = DEFAULT_MODELS[model_key]
        sampler = ModelSampler(
            model_key=model_key,
            model_label=str(model["label"]),
            h5_path=Path(model["h5"]),
            field=args.field,
            node_stride=args.node_stride,
        )
        region_token = safe_token(region.name)
        bounds_utm = sampler.xy_bounds_m if args.bounds == "model" else None
        if args.bounds == "model":
            region_token = f"{region_token}_simulation_domain"
        vertical_sections: list[VerticalSection] = []
        if vertical_specs:
            vertical_sections.extend(sections_from_fractions(region, vertical_specs, bounds_utm=bounds_utm))
        if spacing_specs:
            vertical_sections.extend(sections_from_spacing(region, spacing_specs, bounds_utm=bounds_utm))
        if vertical_sections:
            sampled = sample_vertical_sections(
                sampler,
                vertical_sections,
                depth_min_km=args.depth_min_km,
                depth_max_km=args.depth_max_km,
                dx_km=args.vertical_dx_km,
                dz_km=args.vertical_dz_km,
                max_distance_m=args.max_nearest_distance_m,
            )
            out = args.output_dir / f"{model_key}_{region_token}_vs_vertical_sections.png"
            written.append(
                plot_vertical_figure(
                    sampler,
                    region,
                    sampled,
                    out,
                    basemap_source=args.basemap_source,
                    basemap_zoom=args.basemap_zoom,
                    basemap_cache_dir=args.basemap_cache_dir,
                    bounds_utm=bounds_utm,
                )
            )
        depths = horizontal_depths(sampler, args.horizontal_count or None, parse_depth_list(args.horizontal_depths_km))
        if depths:
            sampled_h = sample_horizontal_sections(
                sampler,
                region,
                depths,
                spacing_km=args.horizontal_spacing_km,
                max_distance_m=args.max_nearest_distance_m,
                bounds_utm=bounds_utm,
            )
            out = args.output_dir / f"{model_key}_{region_token}_vs_horizontal_sections.png"
            written.append(
                plot_horizontal_figure(
                    sampler,
                    region,
                    sampled_h,
                    out,
                    basemap_source=args.basemap_source,
                    basemap_zoom=args.basemap_zoom,
                    basemap_cache_dir=args.basemap_cache_dir,
                    bounds_utm=bounds_utm,
                )
            )
        thresholds = parse_depth_list(args.threshold_depths_vs_kmps)
        if thresholds:
            sampled_thresholds = sample_vs_threshold_depths(
                sampler,
                region,
                thresholds,
                spacing_km=args.horizontal_spacing_km,
                depth_min_km=args.depth_min_km,
                depth_max_km=args.threshold_depth_max_km if args.threshold_depth_max_km is not None else args.depth_max_km,
                dz_km=args.threshold_dz_km,
                max_distance_m=args.max_nearest_distance_m,
                bounds_utm=bounds_utm,
            )
            out = args.output_dir / f"{model_key}_{region_token}_vs_threshold_depths.png"
            written.append(
                plot_threshold_depth_figure(
                    sampler,
                    region,
                    sampled_thresholds,
                    out,
                    basemap_source=args.basemap_source,
                    basemap_zoom=args.basemap_zoom,
                    basemap_cache_dir=args.basemap_cache_dir,
                    bounds_utm=bounds_utm,
                )
            )
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
