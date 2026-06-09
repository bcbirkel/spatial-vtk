from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from spatial_vtk.config import abbreviate_model
from spatial_vtk.io import (
    aggregate_metric_by_station_over_events,
    classify_model_folder,
    inspect_station_event_layouts,
    load_csv_bundle,
    resolve_model_aliases,
    wide_to_long_metrics,
    write_station_event_kml,
)
from spatial_vtk.metrics.calculate import (
    amplitude_spectrum,
    bandpass_with_metadata,
    bands_from_list,
    bands_from_logspace,
)


def test_naming_and_model_aliases(tmp_path):
    model_root = tmp_path / "synthetics"
    model_root.mkdir()
    (model_root / "cvmsi_cvmhlabn_cvmhsgbn_cvmhsbbn_cvmhvbn_elygtl").mkdir()
    (model_root / "bbp1d_reference").mkdir()

    assert abbreviate_model("cvmsi_cvmhlabn_cvmhsgbn_cvmhsbbn_cvmhvbn_elygtl") == "allBasins+SI+Ely"
    assert classify_model_folder("bbp1d_reference").default_alias == "bbp1d"

    resolution = resolve_model_aliases(["cvmsi-basins-ely", "bbp1d"], model_root)
    assert resolution.model_folders["cvmsi-basins-ely"].endswith("elygtl")
    assert resolution.model_folders["bbp1d"] == "bbp1d_reference"


def test_band_and_waveform_helpers():
    bands = bands_from_list([0.1, 0.2, 0.4])
    assert list(bands.values()) == [(0.1, 0.2), (0.2, 0.4)]
    assert len(bands_from_logspace(0.1, 1.0, 3)) == 3

    dt = 0.01
    time = np.arange(0, 5, dt)
    signal = np.sin(2 * np.pi * 2.0 * time)
    freq, amp = amplitude_spectrum(signal, dt)
    assert freq[np.argmax(amp)] == pytest.approx(2.0, abs=0.05)

    filtered = bandpass_with_metadata(signal, dt, 1.0, 4.0)
    assert filtered.data.shape == signal.shape
    assert filtered.valid_mask.any()


def test_table_helpers(tmp_path):
    csv_path = tmp_path / "metrics.csv"
    pd.DataFrame(
        {
            "simulation_model": ["m1", "m1"],
            "event_title": ["e1", "e2"],
            "station_name": ["S1", "S1"],
            "station_latitude": [34.0, 34.0],
            "station_longitude": [-118.0, -118.0],
            "C1_obs": [1.0, 2.0],
            "C1_syn": [2.0, 4.0],
        }
    ).to_csv(csv_path, index=False)

    loaded = load_csv_bundle(csv_path)
    long = wide_to_long_metrics(loaded)
    assert set(["metric", "value_obs", "value_syn", "residual"]).issubset(long.columns)
    assert long["metric"].tolist() == ["C1", "C1"]

    aggregated = aggregate_metric_by_station_over_events(long, metric_col="residual")
    assert aggregated.loc[0, "n_events"] == 2


def test_kml_and_layout_helpers(tmp_path):
    stations = pd.DataFrame({"station": ["S1"], "lat": [34.0], "lon": [-118.0]})
    events = pd.DataFrame({"event_id": ["E1"], "lat": [34.2], "lon": [-118.2]})
    kml_path = write_station_event_kml(stations, events, tmp_path / "context.kml")
    text = kml_path.read_text(encoding="utf-8")
    assert "Station S1" in text
    assert "Event E1" in text

    (tmp_path / "metadata.json").write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    layout = inspect_station_event_layouts(tmp_path)
    assert {"context.kml", "metadata.json"}.intersection(set(layout["relative_path"]))
    assert "json_keys" in layout.columns
