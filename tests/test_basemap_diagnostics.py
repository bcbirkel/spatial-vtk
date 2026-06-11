from __future__ import annotations

import builtins

import matplotlib.pyplot as plt
import pytest

from spatial_vtk.spatial.map.basemaps import add_contextily_basemap


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
