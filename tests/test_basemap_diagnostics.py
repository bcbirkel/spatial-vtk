from __future__ import annotations

import builtins

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from spatial_vtk.spatial.map.basemaps import add_contextily_basemap
import spatial_vtk.visualize.context.maps as context_maps


def test_add_contextily_basemap_warns_when_tiles_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Basemap failures should be visible instead of silently drawing fallback."""

    original_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object):
        if name == "contextily":
            raise ModuleNotFoundError("No module named 'contextily'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    fig, ax = plt.subplots()
    ax.set_xlim(-119.0, -117.0)
    ax.set_ylim(33.0, 35.0)

    with pytest.warns(RuntimeWarning, match="Basemap tiles could not be drawn"):
        success, message = add_contextily_basemap(ax, cache_dir=tmp_path)

    assert success is False
    assert "contextily unavailable" in message
    assert "cache=" in message
    plt.close(fig)


def test_add_contextily_basemap_can_raise_when_tiles_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Callers should be able to hard-fail when a real basemap is required."""

    original_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object):
        if name == "contextily":
            raise ModuleNotFoundError("No module named 'contextily'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    fig, ax = plt.subplots()
    ax.set_xlim(-119.0, -117.0)
    ax.set_ylim(33.0, 35.0)

    with pytest.raises(RuntimeError, match="Basemap tiles could not be drawn"):
        add_contextily_basemap(ax, cache_dir=tmp_path, on_error="raise")

    plt.close(fig)


def test_station_event_beachball_map_uses_basemap_helper(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Beachball maps should use and report the shared basemap helper."""

    events = pd.DataFrame(
        {
            "event_id": ["E01", "E02"],
            "event_lon": [-118.25, -118.0],
            "event_lat": [34.08, 34.25],
            "magnitude": [4.2, 4.8],
            "strike": [120.0, 220.0],
            "dip": [45.0, 50.0],
            "rake": [90.0, 10.0],
        }
    )
    stations = pd.DataFrame({"station": ["S1", "S2"], "lon": [-118.4, -118.1], "lat": [34.0, 34.2]})
    calls: list[dict[str, object]] = []

    def fake_add_basemap(ax, **kwargs):
        calls.append(kwargs)
        ax.imshow(
            [[[0.2, 0.4, 0.7], [0.2, 0.4, 0.7]], [[0.2, 0.4, 0.7], [0.2, 0.4, 0.7]]],
            extent=(*ax.get_xlim(), *ax.get_ylim()),
            origin="lower",
            zorder=0,
        )
        return True, "unit-test-basemap"

    monkeypatch.setattr(context_maps, "add_contextily_basemap", fake_add_basemap)

    fig = context_maps.plot_station_event_beachball_map(
        events,
        stations_df=stations,
        add_basemap=True,
        basemap_kwargs={"cache_dir": tmp_path, "on_error": "raise"},
        showfig=False,
    )

    assert len(calls) == 1
    assert calls[0]["crs"] == "EPSG:4326"
    assert calls[0]["cache_dir"] == tmp_path
    assert calls[0]["on_error"] == "raise"
    assert fig.spatial_vtk_basemap == {"success": True, "source": "unit-test-basemap"}
    assert fig.axes[0].spatial_vtk_basemap == {"success": True, "source": "unit-test-basemap"}
    assert fig.axes[0].images
    assert fig.axes[0].get_xlim() == pytest.approx((-118.432, -117.968))
    assert fig.axes[0].get_ylim() == pytest.approx((33.97, 34.28))
    plt.close(fig)


def test_required_basemaps_reject_opt_out_and_record_failure(monkeypatch, tmp_path):
    import json
    monkeypatch.setenv("SVTK_REQUIRE_BASEMAP", "1")
    monkeypatch.setenv("SVTK_NO_BASEMAP", "1")
    audit = tmp_path / "audit.jsonl"
    monkeypatch.setenv("SVTK_BASEMAP_AUDIT", str(audit))
    fig, ax = plt.subplots()
    with pytest.raises(RuntimeError, match="SVTK_NO_BASEMAP"):
        add_contextily_basemap(ax, on_error="ignore")
    assert not ax.spatial_vtk_basemap["success"]
    assert not json.loads(audit.read_text())["success"]
    plt.close(fig)


def test_required_basemaps_override_silent_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("SVTK_REQUIRE_BASEMAP", "1")
    monkeypatch.delenv("SVTK_NO_BASEMAP", raising=False)
    original_import = builtins.__import__
    def missing(name, *args, **kwargs):
        if name == "contextily":
            raise ModuleNotFoundError("contextily unavailable")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", missing)
    fig, ax = plt.subplots()
    with pytest.raises(RuntimeError, match="contextily unavailable"):
        add_contextily_basemap(ax, on_error="ignore", cache_dir=tmp_path)
    plt.close(fig)


def test_basemap_cache_can_be_shared_between_checkouts(monkeypatch, tmp_path):
    from spatial_vtk.spatial.map.basemaps import default_basemap_cache_dir
    monkeypatch.setenv("SVTK_BASEMAP_CACHE", str(tmp_path))
    assert default_basemap_cache_dir() == tmp_path.resolve()
