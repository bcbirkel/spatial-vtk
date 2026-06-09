"""Shared helpers for adding consistent basemaps to geographic figures.

Purpose
-------
This module centralizes the package's simple lon/lat basemap behavior so map
figures default to an Esri imagery basemap and fall back cleanly when
``contextily`` or remote tiles are unavailable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import math
import re

from spatial_vtk.config.paths import ROOT_DIR


def _canonical_provider_name(provider_name: str | None) -> str:
    """Return one normalized provider name for cache and lookup decisions.

    Parameters
    ----------
    provider_name
        Short or fully qualified provider selector.

    Returns
    -------
    str
        Canonical provider name used throughout the basemap helper.
    """

    if provider_name is None:
        return "Esri.WorldImagery"

    alias = str(provider_name).strip().lower()
    aliases = {
        "esri": "Esri.WorldImagery",
        "esriimagery": "Esri.WorldImagery",
        "esri_worldimagery": "Esri.WorldImagery",
        "esri.worldimagery": "Esri.WorldImagery",
        "worldimagery": "Esri.WorldImagery",
        "google": "Esri.WorldImagery",
        "google-satellite": "Esri.WorldImagery",
        "satellite": "Esri.WorldImagery",
        "esritopo": "Esri.WorldTopoMap",
        "esri_worldtopomap": "Esri.WorldTopoMap",
        "esri.worldtopomap": "Esri.WorldTopoMap",
        "topo": "Esri.WorldTopoMap",
        "osm": "OpenStreetMap.Mapnik",
        "openstreetmap": "OpenStreetMap.Mapnik",
        "openstreetmap_mapnik": "OpenStreetMap.Mapnik",
        "cartodb": "CartoDB.Positron",
        "cartodb_positron": "CartoDB.Positron",
        "cartodb.positron": "CartoDB.Positron",
        "positron": "CartoDB.Positron",
    }
    return aliases.get(alias, str(provider_name).strip())


def _cache_source_slugs(provider_name: str | None) -> tuple[str, ...]:
    """Return cache filename slugs compatible with one logical provider.

    Parameters
    ----------
    provider_name
        Short or fully qualified provider selector.

    Returns
    -------
    tuple of str
        Cache filename prefixes to treat as interchangeable for lookup.
    """

    canonical = _canonical_provider_name(provider_name)
    canonical_slug = canonical.strip().lower().replace(".", "_")
    alias_map = {
        "esri_worldimagery": ("esri_worldimagery", "esriimagery", "esri"),
        "esri_worldtopomap": ("esri_worldtopomap", "esritopo"),
        "openstreetmap_mapnik": ("openstreetmap_mapnik", "openstreetmap", "osm"),
        "cartodb_positron": ("cartodb_positron", "cartodb", "positron"),
    }
    return alias_map.get(canonical_slug, (canonical_slug,))


def _resolve_contextily_provider(ctx: Any, provider_name: str | None):
    """Resolve a contextily provider from a short or fully qualified name.

    Parameters
    ----------
    ctx
        Imported :mod:`contextily` module.
    provider_name
        Provider selector such as ``"Esri.WorldImagery"`` or ``"osm"``.

    Returns
    -------
    object
        Provider object accepted by :func:`contextily.add_basemap`.
    """

    resolved_name = _canonical_provider_name(provider_name)
    provider = ctx.providers
    for part in resolved_name.split("."):
        provider = getattr(provider, part)
    return provider


def draw_static_basemap_fallback(ax: Any) -> None:
    """Draw a lightweight static background when tiled basemaps are unavailable.

    Parameters
    ----------
    ax
        Matplotlib axes with longitude on x and latitude on y.

    Returns
    -------
    None
        The helper mutates ``ax`` in place.
    """

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    ax.set_facecolor("#eef2f4")
    ax.axhspan(ylim[0], ylim[1], facecolor="#e7ecef", alpha=0.85, zorder=0)
    ax.axhspan(ylim[0], ylim[0] + 0.22 * (ylim[1] - ylim[0]), facecolor="#dde6ea", alpha=0.9, zorder=0)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)


def _draw_cached_geotiff_basemap(ax: Any, *, tif_path: Path, xlim: tuple[float, float], ylim: tuple[float, float], crs: str) -> bool:
    """Draw one cached GeoTIFF basemap directly with rasterio.

    Parameters
    ----------
    ax
        Matplotlib axes with geographic longitude/latitude limits already set.
    tif_path
        Cached GeoTIFF path to render.
    xlim, ylim
        Original axis bounds to restore after drawing.
    crs
        CRS string for the current axes.

    Returns
    -------
    bool
        ``True`` when the raster was drawn successfully, else ``False``.
    """

    try:
        import numpy as np
        import rasterio
        from rasterio.transform import array_bounds
        from rasterio.warp import Resampling, calculate_default_transform, reproject
    except Exception:
        return False

    try:
        with rasterio.open(tif_path) as src:
            dst_crs = str(crs)
            band_count = int(src.count)
            if band_count >= 3:
                band_indexes = (1, 2, 3)
            elif band_count == 1:
                band_indexes = (1,)
            else:
                return False
            src_crs = src.crs
            if src_crs is not None and str(src_crs).upper() != dst_crs.upper():
                dst_transform, dst_width, dst_height = calculate_default_transform(
                    src_crs,
                    dst_crs,
                    src.width,
                    src.height,
                    *src.bounds,
                )
                bands = np.zeros((len(band_indexes), dst_height, dst_width), dtype=src.dtypes[0])
                for out_index, band_index in enumerate(band_indexes):
                    reproject(
                        source=rasterio.band(src, band_index),
                        destination=bands[out_index],
                        src_transform=src.transform,
                        src_crs=src_crs,
                        dst_transform=dst_transform,
                        dst_crs=dst_crs,
                        resampling=Resampling.bilinear,
                    )
                left, bottom, right, top = array_bounds(dst_height, dst_width, dst_transform)
            else:
                bands = np.stack([src.read(index) for index in band_indexes], axis=0)
                bounds = src.bounds
                left, right, bottom, top = bounds.left, bounds.right, bounds.bottom, bounds.top
            if len(band_indexes) == 1:
                bands = np.repeat(bands, 3, axis=0)
            rgb = np.moveaxis(bands, 0, -1)
        ax.imshow(
            rgb,
            extent=(left, right, bottom, top),
            origin="upper",
            interpolation="bilinear",
            zorder=0,
        )
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        _set_geographic_aspect(ax, crs=crs)
        return True
    except Exception:
        return False


def _set_geographic_aspect(ax: Any, *, crs: str) -> None:
    """Apply a geographic 1:1 aspect for lon/lat axes.

    Parameters
    ----------
    ax
        Matplotlib axes.
    crs
        CRS string for the plotted coordinates.

    Returns
    -------
    None
        The helper mutates ``ax`` in place.
    """

    if str(crs).upper() != "EPSG:4326":
        return
    lat_min, lat_max = ax.get_ylim()
    lat_mid = 0.5 * (float(lat_min) + float(lat_max))
    cos_lat = math.cos(math.radians(lat_mid))
    if not math.isfinite(cos_lat) or abs(cos_lat) < 1.0e-6:
        return
    ax.set_aspect(1.0 / cos_lat, adjustable="box")


def _recommended_zoom_for_extent(*, xlim: tuple[float, float], ylim: tuple[float, float], crs: str) -> int | None:
    """Return a sharper default tile zoom for small geographic extents.

    Parameters
    ----------
    xlim, ylim
        Current axis bounds.
    crs
        CRS string for the plotted coordinates.

    Returns
    -------
    int or None
        Suggested zoom level, or ``None`` when no recommendation is available.
    """

    if str(crs).upper() != "EPSG:4326":
        return None
    lon_span = abs(float(xlim[1]) - float(xlim[0]))
    lat_span = abs(float(ylim[1]) - float(ylim[0]))
    span = max(lon_span, lat_span)
    if span <= 0.03:
        return 15
    if span <= 0.06:
        return 14
    if span <= 0.12:
        return 13
    if span <= 0.25:
        return 12
    if span <= 0.5:
        return 11
    if span <= 1.0:
        return 10
    if span <= 2.0:
        return 9
    return 8


def default_basemap_cache_dir() -> Path:
    """Return the default local cache directory for basemap rasters."""

    return (ROOT_DIR / ".cache" / "contextily").resolve()


def _basemap_cache_path(
    *,
    source_name: str,
    zoom: int,
    xlim: tuple[float, float],
    ylim: tuple[float, float],
    cache_dir: Path,
) -> Path:
    """Build a deterministic cache filename for one basemap extent."""

    def _fmt(value: float) -> str:
        text = f"{value:.3f}"
        return text.replace("-", "m").replace(".", "p")

    slug = _cache_source_slugs(source_name)[0]
    filename = (
        f"{slug}_z{int(zoom)}"
        f"_w{_fmt(xlim[0])}_e{_fmt(xlim[1])}"
        f"_s{_fmt(ylim[0])}_n{_fmt(ylim[1])}.tif"
    )
    return cache_dir / filename


def _cached_basemap_covering_extent(
    *,
    source_name: str,
    xlim: tuple[float, float],
    ylim: tuple[float, float],
    cache_dir: Path,
    allow_any_source: bool = False,
) -> Path | None:
    """Return one cached basemap whose bounds cover the requested extent.

    Parameters
    ----------
    source_name
        Preferred provider name.
    xlim, ylim
        Requested west/east and south/north bounds.
    cache_dir
        Cache directory holding GeoTIFF basemap rasters.

    Returns
    -------
    pathlib.Path or None
        Best matching cached raster when one covers the requested extent.
    """

    slugs = _cache_source_slugs(source_name)
    pattern = re.compile(
        r"^(?P<slug>[a-z0-9_]+)_z(?P<zoom>\d+)"
        r"_w(?P<w>m?\d+p\d+)_e(?P<e>m?\d+p\d+)"
        r"_s(?P<s>m?\d+p\d+)_n(?P<n>m?\d+p\d+)\.tif$"
    )

    def _parse_token(token: str) -> float:
        return float(token.replace("m", "-").replace("p", "."))

    west, east = float(min(xlim)), float(max(xlim))
    south, north = float(min(ylim)), float(max(ylim))
    candidates: list[tuple[int, float, int, Path]] = []
    for path in cache_dir.glob("*_z*.tif"):
        match = pattern.match(path.name)
        if match is None:
            continue
        slug = str(match.group("slug")).strip().lower()
        if not allow_any_source and slug not in slugs:
            continue
        bounds = {
            "west": _parse_token(match.group("w")),
            "east": _parse_token(match.group("e")),
            "south": _parse_token(match.group("s")),
            "north": _parse_token(match.group("n")),
        }
        if (
            bounds["west"] <= west
            and bounds["east"] >= east
            and bounds["south"] <= south
            and bounds["north"] >= north
        ):
            area = (bounds["east"] - bounds["west"]) * (bounds["north"] - bounds["south"])
            slug_penalty = 0 if slug in slugs else 1
            candidates.append((int(match.group("zoom")), float(area), int(slug_penalty), path))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[2], -item[0], item[1], item[3].name))
    return candidates[0][3]


def basemap_cache_path_for_extent(
    *,
    west: float,
    south: float,
    east: float,
    north: float,
    source_name: str = "Esri.WorldImagery",
    zoom: int = 8,
    cache_dir: str | Path | None = None,
) -> Path:
    """Return the deterministic cache path for one basemap extent."""

    cache_root = Path(cache_dir).expanduser().resolve() if cache_dir is not None else default_basemap_cache_dir()
    cache_root.mkdir(parents=True, exist_ok=True)
    return _basemap_cache_path(
        source_name=source_name,
        zoom=int(zoom),
        xlim=(float(west), float(east)),
        ylim=(float(south), float(north)),
        cache_dir=cache_root,
    )


def cache_contextily_basemap_raster(
    *,
    west: float,
    south: float,
    east: float,
    north: float,
    source_name: str = "Esri.WorldImagery",
    zoom: int = 8,
    cache_dir: str | Path | None = None,
    ll: bool = True,
) -> Path:
    """Download and cache one basemap raster for later offline reuse.

    Parameters
    ----------
    west, south, east, north
        Bounds for the requested raster. For lon/lat inputs, keep ``ll=True``.
    source_name
        Contextily provider name. Defaults to ``Esri.WorldImagery``.
    zoom
        Tile zoom level.
    cache_dir
        Optional cache directory. Defaults to ``.cache/contextily``.
    ll
        Whether the bounds are longitude/latitude.

    Returns
    -------
    pathlib.Path
        Written GeoTIFF path.
    """

    import contextily as ctx  # type: ignore

    cache_path = basemap_cache_path_for_extent(
        west=west,
        south=south,
        east=east,
        north=north,
        source_name=source_name,
        zoom=zoom,
        cache_dir=cache_dir,
    )
    provider = _resolve_contextily_provider(ctx, source_name)
    ctx.bounds2raster(
        float(west),
        float(south),
        float(east),
        float(north),
        str(cache_path),
        source=provider,
        zoom=int(zoom),
        ll=bool(ll),
    )
    return cache_path


def add_contextily_basemap(
    ax: Any,
    *,
    crs: str = "EPSG:4326",
    primary_source: str = "Esri.WorldImagery",
    fallback_sources: Iterable[str] = ("Esri.WorldTopoMap", "OpenStreetMap.Mapnik", "CartoDB.Positron"),
    zoom: int | None = None,
    attribution: bool = False,
    cache_dir: str | Path | None = None,
    cache_download: bool = True,
) -> tuple[bool, str]:
    """Add a tiled basemap with provider fallbacks.

    Parameters
    ----------
    ax
        Matplotlib axes with geographic longitude/latitude limits already set.
    crs
        CRS string describing the current axes coordinates.
    primary_source
        Preferred provider name. Defaults to Esri imagery.
    fallback_sources
        Additional providers to try before falling back to a static background.
    zoom
        Optional contextily zoom level.
    attribution
        Whether to draw tile attribution text.
    cache_dir
        Optional local cache directory for downloaded rasters. When omitted,
        the helper uses ``.cache/contextily`` under the repository root.
    cache_download
        Whether to save the preferred provider raster into the cache when the
        local file is missing and network tile access is available.

    Returns
    -------
    tuple
        ``(success, source_name)``. When ``success`` is ``False``, a static
        background has already been drawn and ``source_name`` contains the last
        error string.
    """

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    cache_root = Path(cache_dir).expanduser().resolve() if cache_dir is not None else default_basemap_cache_dir()
    cache_root.mkdir(parents=True, exist_ok=True)
    recommended_zoom = _recommended_zoom_for_extent(
        xlim=(float(xlim[0]), float(xlim[1])),
        ylim=(float(ylim[0]), float(ylim[1])),
        crs=crs,
    )
    effective_zoom = recommended_zoom if zoom is None else max(int(zoom), int(recommended_zoom or zoom))

    try:
        import contextily as ctx  # type: ignore
    except Exception as exc:
        if effective_zoom is not None:
            covering_cache = _cached_basemap_covering_extent(
                source_name=primary_source,
                xlim=(float(xlim[0]), float(xlim[1])),
                ylim=(float(ylim[0]), float(ylim[1])),
                cache_dir=cache_root,
                allow_any_source=True,
            )
            if covering_cache is not None and _draw_cached_geotiff_basemap(
                ax,
                tif_path=covering_cache,
                xlim=(float(xlim[0]), float(xlim[1])),
                ylim=(float(ylim[0]), float(ylim[1])),
                crs=crs,
            ):
                return True, str(covering_cache)
        draw_static_basemap_fallback(ax)
        return False, f"contextily unavailable: {exc}"

    if effective_zoom is not None:
        cache_path = _basemap_cache_path(
            source_name=primary_source,
            zoom=int(effective_zoom),
            xlim=(float(xlim[0]), float(xlim[1])),
            ylim=(float(ylim[0]), float(ylim[1])),
            cache_dir=cache_root,
        )
        if cache_path.exists():
            if _draw_cached_geotiff_basemap(
                ax,
                tif_path=cache_path,
                xlim=(float(xlim[0]), float(xlim[1])),
                ylim=(float(ylim[0]), float(ylim[1])),
                crs=crs,
            ):
                return True, str(cache_path)
            try:
                ctx.add_basemap(ax, source=str(cache_path), crs=crs, attribution=attribution)
                ax.set_xlim(xlim)
                ax.set_ylim(ylim)
                _set_geographic_aspect(ax, crs=crs)
                return True, str(cache_path)
            except Exception:
                pass

        covering_cache = _cached_basemap_covering_extent(
            source_name=primary_source,
            xlim=(float(xlim[0]), float(xlim[1])),
            ylim=(float(ylim[0]), float(ylim[1])),
            cache_dir=cache_root,
        )
        if covering_cache is not None:
            if _draw_cached_geotiff_basemap(
                ax,
                tif_path=covering_cache,
                xlim=(float(xlim[0]), float(xlim[1])),
                ylim=(float(ylim[0]), float(ylim[1])),
                crs=crs,
            ):
                return True, str(covering_cache)
            try:
                ctx.add_basemap(ax, source=str(covering_cache), crs=crs, attribution=attribution)
                ax.set_xlim(xlim)
                ax.set_ylim(ylim)
                _set_geographic_aspect(ax, crs=crs)
                return True, str(covering_cache)
            except Exception:
                pass
        covering_cache = _cached_basemap_covering_extent(
            source_name=primary_source,
            xlim=(float(xlim[0]), float(xlim[1])),
            ylim=(float(ylim[0]), float(ylim[1])),
            cache_dir=cache_root,
            allow_any_source=True,
        )
        if covering_cache is not None:
            if _draw_cached_geotiff_basemap(
                ax,
                tif_path=covering_cache,
                xlim=(float(xlim[0]), float(xlim[1])),
                ylim=(float(ylim[0]), float(ylim[1])),
                crs=crs,
            ):
                return True, str(covering_cache)
            try:
                ctx.add_basemap(ax, source=str(covering_cache), crs=crs, attribution=attribution)
                ax.set_xlim(xlim)
                ax.set_ylim(ylim)
                _set_geographic_aspect(ax, crs=crs)
                return True, str(covering_cache)
            except Exception:
                pass
        elif cache_download:
            try:
                provider = _resolve_contextily_provider(ctx, primary_source)
                ctx.bounds2raster(
                    float(xlim[0]),
                    float(ylim[0]),
                    float(xlim[1]),
                    float(ylim[1]),
                    str(cache_path),
                    source=provider,
                    zoom=int(effective_zoom),
                    ll=str(crs).upper() == "EPSG:4326",
                )
                ctx.add_basemap(ax, source=str(cache_path), crs=crs, attribution=attribution)
                ax.set_xlim(xlim)
                ax.set_ylim(ylim)
                _set_geographic_aspect(ax, crs=crs)
                return True, str(cache_path)
            except Exception:
                pass

    attempts = [primary_source, *list(fallback_sources)]
    last_error = "unknown basemap failure"
    for source_name in attempts:
        try:
            provider = _resolve_contextily_provider(ctx, source_name)
            kwargs = {"source": provider, "crs": crs, "attribution": attribution}
            if effective_zoom is not None:
                kwargs["zoom"] = int(effective_zoom)
            ctx.add_basemap(ax, **kwargs)
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
            _set_geographic_aspect(ax, crs=crs)
            return True, str(source_name)
        except Exception as exc:
            last_error = str(exc)
            continue

    draw_static_basemap_fallback(ax)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    _set_geographic_aspect(ax, crs=crs)
    return False, last_error
