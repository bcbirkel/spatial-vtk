"""Check natural-log defaults and explicit legacy compatibility."""
import numpy as np
import pandas as pd
import pytest

from spatial_vtk.config.metrics import DEFAULT_TRANSFORMS
from spatial_vtk.metrics.calculate.transforms import compare_metric_values
from spatial_vtk.metrics.calculate.enrich import _apply_transform_columns
from spatial_vtk.spatial.calculate.prepare_stats import build_metric_field
from spatial_vtk.spatial.calculate.geology import _effect_interpretation
from spatial_vtk.tutorials import with_natural_log_residual


def test_default_and_explicit_logarithms():
    assert DEFAULT_TRANSFORMS == ("ln_residual",)
    assert compare_metric_values(np.e, 1) == {"ln_residual": pytest.approx(1)}
    assert compare_metric_values(2, 1, transforms=("log2_residual",)) == {"log2_residual": pytest.approx(1)}


def test_legacy_snapshot_conversion_preserves_qc_and_source():
    legacy = pd.DataFrame({"log2_residual": [1., -1., np.nan]})
    converted = with_natural_log_residual(legacy)
    np.testing.assert_allclose(converted.ln_residual, [np.log(2), -np.log(2), np.nan])
    assert "ln_residual" not in legacy
    uncomputed = legacy.assign(ln_residual=np.nan)
    pd.testing.assert_frame_equal(with_natural_log_residual(uncomputed), converted)
    pd.testing.assert_series_equal(converted.log2_residual, legacy.log2_residual)


def test_spatial_default_converts_legacy_with_provenance():
    data = pd.DataFrame({"metric": ["PGA", "PGA"], "event_id": ["e", "e"],
        "station": ["A", "B"], "lat": [34., 34.1], "lon": [-118., -118.1],
        "log2_residual": [1., np.nan]})
    result = build_metric_field(data, "PGA", field_mode="auto")
    assert len(result) == 1
    assert result.field_value.iloc[0] == pytest.approx(np.log(2))
    assert result.field_source.iloc[0] == "ln_residual"
    explicit = build_metric_field(data, "PGA", value_column="log2_residual")
    assert explicit.field_value.iloc[0] == 1


def test_percent_effect_is_invariant_to_log_base():
    ln_row = dict(effect=np.log(2), ci_low=0., ci_high=np.log(3), bootstrap_p=.02)
    result = _effect_interpretation(ln_row, log2_context=False, ln_context=True)
    assert result["percent_effect"] == pytest.approx(100)
    assert result["percent_ci_high"] == pytest.approx(200)
    legacy = _effect_interpretation(dict(ln_row, effect=1), log2_context=True)
    assert legacy["percent_effect"] == pytest.approx(100)


def test_enrichment_prefers_ln_but_accepts_explicit_legacy_rows():
    data = pd.DataFrame({"ln_residual": [np.log(2)], "log2_residual": [1.]})
    result = _apply_transform_columns(data, residual_column=None, score_column=None)
    assert result.residual.iloc[0] == pytest.approx(np.log(2))
    data["ln_residual"] = np.nan
    result = _apply_transform_columns(data, residual_column=None, score_column=None)
    assert result.residual.iloc[0] == 1


def test_published_notebooks_use_native_metric_handoff():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for step in (3, 4, 5, 6, 7):
        notebook = next((root / "docs/examples").glob(f"step_{step:02d}_*.ipynb"))
        text = "\n".join("".join(c["source"]) for c in json.loads(notebook.read_text())["cells"])
        assert "with_natural_log_residual" not in text
        assert "metric_figure_snapshot" not in text
        assert "ln_residual" in text
        if step in (4, 5, 6):
            assert 'load_output_table("metrics_enriched")' in text
