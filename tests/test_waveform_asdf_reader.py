"""Tests for ASDF waveform loading."""

from __future__ import annotations

import sys
from types import SimpleNamespace

from spatial_vtk.io.waveforms import read_waveform_file


class FakeStream(list):
    """Minimal ObsPy Stream stand-in for ASDF reader tests."""

    def __iadd__(self, other):
        self.extend(other)
        return self


class FakeStationWaveforms:
    """Minimal pyasdf station waveform accessor."""

    def get_waveform_tags(self):
        return ["raw"]

    def __getitem__(self, tag):
        return FakeStream([f"trace:{tag}"])


class FakeWaveforms:
    """Minimal pyasdf waveform collection."""

    def list(self):
        return ["CI.STA01"]

    def __getitem__(self, station_name):
        return FakeStationWaveforms()


class FakeASDFDataSet:
    """Minimal pyasdf dataset context manager."""

    def __init__(self, path, mode):
        self.path = path
        self.mode = mode
        self.waveforms = FakeWaveforms()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


def test_read_waveform_file_reads_asdf_with_pyasdf(monkeypatch, tmp_path) -> None:
    """ASDF files should be read through pyasdf, not passed to ObsPy read."""

    path = tmp_path / "event.asdf"
    path.write_bytes(b"asdf")
    monkeypatch.setitem(sys.modules, "obspy", SimpleNamespace(Stream=FakeStream))
    monkeypatch.setitem(sys.modules, "pyasdf", SimpleNamespace(ASDFDataSet=FakeASDFDataSet))

    stream = read_waveform_file(path)

    assert stream == ["trace:raw"]
