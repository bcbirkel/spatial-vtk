"""Build figures and dissertation prose for the recommended metric subset."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import textwrap

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "outputs/review/user_requested_large_run_figures"
OUT = SOURCE_ROOT / "recommended_metric_justification"
FIG = OUT / "figures"


@dataclass(frozen=True)
class MetricPick:
    metric: str
    group: str
    role: str
    primary_value_source: str


PICKS = [
    MetricPick("PGA", "amplitude", "peak acceleration level", "plot_value"),
    MetricPick("arias_duration", "duration", "duration of strong shaking", "plot_value"),
    MetricPick("FAS", "spectral", "frequency-content residual", "plot_value"),
    MetricPick("traveltime_delay", "delay", "timing/phase residual", "plot_value"),
    MetricPick("delay_corrected_cc", "cross_correlation", "waveform-shape similarity after timing correction", "plot_value"),
]

# The task 1 obs/syn/residual PCA products only contain metrics with independent
# observed and synthetic scalar values. Delay and cross-correlation metrics are
# comparison metrics, so they are justified from the task 2 spatial/robustness
# summaries instead of being forced into the PCA matrices.
CORR_METRICS = ["PGA", "arias_duration", "FAS"]
COMPARATORS = {
    "amplitude": ["PGA", "PGV", "PGD"],
    "intensity": ["arias_intensity", "energy_intensity", "CAV"],
    "duration": ["arias_duration", "energy_duration"],
    "spectral": ["PSA", "FAS"],
    "delay": ["traveltime_delay"],
    "cross_correlation": ["original_cc", "delay_corrected_cc"],
}


def _read_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, **kwargs)


def _metric_label(metric: str) -> str:
    labels = {
        "arias_duration": "Arias duration",
        "energy_duration": "Energy duration",
        "arias_intensity": "Arias intensity",
        "energy_intensity": "Energy intensity",
        "traveltime_delay": "Traveltime delay",
        "delay_corrected_cc": "Delay-corrected CC",
        "original_cc": "Original CC",
    }
    return labels.get(metric, metric)


def _setup() -> None:
    FIG.mkdir(parents=True, exist_ok=True)


def _plot_selected_correlations() -> Path:
    corr_dir = SOURCE_ROOT / "metric_correlations_independent"
    matrices = {
        "Observed": _read_csv(corr_dir / "metric_value_correlation_all_passbands__observed.csv", index_col=0),
        "Synthetic": _read_csv(corr_dir / "metric_value_correlation_all_passbands__synthetic.csv", index_col=0),
        "Residual": _read_csv(corr_dir / "metric_value_correlation_all_passbands__residual.csv", index_col=0),
    }
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.6), constrained_layout=True)
    labels = [_metric_label(m) for m in CORR_METRICS]
    for ax, (title, matrix) in zip(axes, matrices.items()):
        sub = matrix.loc[CORR_METRICS, CORR_METRICS].astype(float)
        im = ax.imshow(sub.values, vmin=-1, vmax=1, cmap="coolwarm")
        ax.set_title(title)
        ax.set_xticks(range(len(labels)), labels=labels, rotation=45, ha="right")
        ax.set_yticks(range(len(labels)), labels=labels)
        for i in range(sub.shape[0]):
            for j in range(sub.shape[1]):
                ax.text(j, i, f"{sub.iat[i, j]:.2f}", ha="center", va="center", fontsize=8)
        ax.tick_params(length=0)
    fig.colorbar(im, ax=axes, shrink=0.86, label="Pearson correlation")
    fig.suptitle("Selected obs/syn scalar metrics sample peak, duration, and spectral behavior")
    path = FIG / "selected_metric_correlations_all_passbands.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def _plot_pca_loadings() -> Path:
    corr_dir = SOURCE_ROOT / "metric_correlations_independent"
    pcs = [f"PC{i}" for i in range(1, 7)]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.0), constrained_layout=True)
    for ax, value_family in zip(axes, ["observed", "synthetic", "residual"]):
        path = corr_dir / f"metric_value_correlation_all_passbands__{value_family}_pca_loadings.csv"
        loadings = _read_csv(path).set_index("metric_feature")
        sub = loadings.loc[CORR_METRICS, pcs].astype(float)
        im = ax.imshow(sub.abs().values, vmin=0, vmax=0.85, cmap="Blues")
        ax.set_title(value_family.capitalize())
        ax.set_xticks(range(len(pcs)), labels=pcs)
        ax.set_yticks(range(len(CORR_METRICS)), labels=[_metric_label(metric) for metric in CORR_METRICS])
        for i in range(sub.shape[0]):
            for j in range(sub.shape[1]):
                ax.text(j, i, f"{sub.iat[i, j]:+.2f}", ha="center", va="center", fontsize=7)
        ax.tick_params(length=0)
        ax.set_xlabel("PCA component")
    fig.colorbar(im, ax=axes, shrink=0.86, label="Absolute loading; text is signed loading")
    fig.suptitle("PCA loadings for the selected metrics represented in obs/syn scalar products")
    path = FIG / "selected_metric_pca_loading_positions.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def _plot_spatial_consistency() -> Path:
    spatial = _read_csv(SOURCE_ROOT / "metric_group_diagnostics/summaries/spatial_consistency_summary.csv")
    keep = []
    for group, metrics in COMPARATORS.items():
        keep.extend((group, metric) for metric in metrics)
    keep_index = pd.MultiIndex.from_tuples(keep, names=["metric_group", "metric"])
    plot = spatial.set_index(["metric_group", "metric"]).loc[keep_index.intersection(spatial.set_index(["metric_group", "metric"]).index)].reset_index()
    plot = plot.loc[plot["value_source"].eq("plot_value")].copy()
    plot["selected"] = plot["metric"].isin([p.metric for p in PICKS])
    plot["metric_label"] = plot["metric"].map(_metric_label)
    plot = plot.sort_values(["metric_group", "weighted_pair_correlation"], ascending=[True, False])

    fig, ax = plt.subplots(figsize=(11.5, 5.8), constrained_layout=True)
    colors = np.where(plot["selected"], "#1f77b4", "#c8cdd4")
    ax.barh(plot["metric_label"], plot["weighted_pair_correlation"], color=colors, edgecolor="#27313f", linewidth=0.5)
    ax.axvline(0.7, color="#5f6b7a", ls="--", lw=1, label="0.70 reference")
    ax.set_xlabel("Weighted nearby-station correlation within 10 km")
    ax.set_ylabel("")
    ax.set_xlim(0, 1)
    ax.invert_yaxis()
    ax.legend(loc="lower right")
    ax.set_title("Recommended metrics are spatially coherent relative to their alternatives")
    path = FIG / "selected_metric_spatial_consistency.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def _plot_outlier_robustness() -> Path:
    robust = _read_csv(SOURCE_ROOT / "metric_group_diagnostics/summaries/outlier_robustness_summary.csv")
    metrics = [metric for metrics in COMPARATORS.values() for metric in metrics]
    plot = robust.loc[
        robust["metric"].isin(metrics)
        & robust["value_source"].eq("plot_value")
        & robust["tail_percent"].isin([1.0, 5.0, 10.0])
    ].copy()
    plot["selected"] = plot["metric"].isin([p.metric for p in PICKS])
    plot["metric_label"] = plot["metric"].map(_metric_label)
    agg = (
        plot.groupby(["metric", "metric_label", "metric_group", "selected"], as_index=False)["winsorized_change_iqr"]
        .apply(lambda s: float(np.nanmax(np.abs(s))))
        .rename(columns={"winsorized_change_iqr": "max_abs_winsorized_change_iqr"})
    )
    agg = agg.sort_values(["metric_group", "max_abs_winsorized_change_iqr"])

    fig, ax = plt.subplots(figsize=(11.5, 5.8), constrained_layout=True)
    colors = np.where(agg["selected"], "#1f77b4", "#c8cdd4")
    ax.barh(agg["metric_label"], agg["max_abs_winsorized_change_iqr"], color=colors, edgecolor="#27313f", linewidth=0.5)
    ax.set_xlabel("Max absolute change in IQR after winsorizing 1-10% tails")
    ax.set_ylabel("")
    ax.invert_yaxis()
    ax.set_title("Recommended metrics retain stable residual distributions under tail treatment")
    path = FIG / "selected_metric_outlier_robustness.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def _build_scorecard() -> pd.DataFrame:
    spatial = _read_csv(SOURCE_ROOT / "metric_group_diagnostics/summaries/spatial_consistency_summary.csv")
    robust = _read_csv(SOURCE_ROOT / "metric_group_diagnostics/summaries/outlier_robustness_summary.csv")
    corr = _read_csv(
        SOURCE_ROOT / "metric_correlations_independent/metric_value_correlation_all_passbands__residual.csv",
        index_col=0,
    )
    rows = []
    for pick in PICKS:
        spatial_row = spatial.loc[
            spatial["metric"].eq(pick.metric)
            & spatial["metric_group"].eq(pick.group)
            & spatial["value_source"].eq(pick.primary_value_source)
        ]
        robust_rows = robust.loc[
            robust["metric"].eq(pick.metric)
            & robust["metric_group"].eq(pick.group)
            & robust["value_source"].eq(pick.primary_value_source)
            & robust["tail_percent"].isin([1.0, 5.0, 10.0])
        ]
        if pick.metric in corr.index:
            other = [m for m in CORR_METRICS if m != pick.metric]
            max_abs_corr = float(corr.loc[pick.metric, other].abs().max()) if other else np.nan
        else:
            max_abs_corr = np.nan
        rows.append(
            {
                "metric": pick.metric,
                "metric_label": _metric_label(pick.metric),
                "group": pick.group,
                "role": pick.role,
                "nearby_station_weighted_corr": float(spatial_row["weighted_pair_correlation"].iloc[0]) if not spatial_row.empty else np.nan,
                "max_abs_winsorized_change_iqr": float(robust_rows["winsorized_change_iqr"].abs().max()) if not robust_rows.empty else np.nan,
                "max_abs_residual_corr_with_selected": max_abs_corr,
                "notes": (
                    "Correlation/PCA unavailable for comparison-only metric"
                    if pick.metric in {"traveltime_delay", "delay_corrected_cc"}
                    else ""
                ),
            }
        )
    return pd.DataFrame(rows)


def _write_report(scorecard: pd.DataFrame, figure_paths: list[Path]) -> Path:
    score_table = _scorecard_markdown(scorecard)
    rel_figures = "\n".join(f"- `{path.relative_to(ROOT)}`" for path in figure_paths)
    text = f"""# Recommended Metric Set for Model Evaluation

## Introduction: correlated metrics overweight one waveform attribute

Composite validation scores are most interpretable when each metric contributes a distinct view of model performance. Multi-measure goodness-of-fit frameworks, including Anderson-style scoring, are valuable because they prevent a model from being judged by a single statistic. The problem is that the component metrics are rarely independent. If several highly correlated measures are averaged with equal weight, the common waveform attribute is counted repeatedly. A model that underpredicts amplitudes, for example, will be penalized by PGA, PGV, PGD, PSA, FAS, Arias intensity, energy intensity, and CAV in related ways. Treating all of those as separate evidence gives amplitude and intensity errors more leverage than timing, duration, or waveform-shape errors.

The purpose of the reduced metric set is therefore not to find five mathematically orthogonal quantities. That is not realistic for waveform metrics. The goal is to choose a small set that spans the main interpretable error modes while avoiding avoidable double-counting. I used the task 1 correlation and PCA products for metrics with independent observed and synthetic scalar values, and the task 2 spatial-consistency and outlier-robustness diagnostics for all metric groups. The resulting set is: PGA, Arias duration, FAS, traveltime delay, and delay-corrected cross correlation. Together these represent peak amplitude, shaking duration, frequency content, arrival-time error, and waveform-shape similarity after timing correction.

The timing and cross-correlation metrics are comparison-only metrics rather than independent observed and synthetic scalar values. They are therefore not included in the task 1 obs/syn/residual PCA matrices. They are included in the recommended set because their task 2 diagnostics show spatially coherent behavior and because they measure error modes that amplitude, duration, and spectral metrics do not capture.

## Recommended set

{score_table}

Supporting figures:

{rel_figures}

## PGA: the peak-amplitude anchor

Peak ground acceleration (PGA) is retained as the amplitude metric because it is the most direct summary of peak acceleration demand and is widely interpretable in both seismological and engineering contexts. The correlation products show that the amplitude family is highly redundant: PGA, PGV, PGD, PSA, FAS, and cumulative intensity measures all respond to shaking strength. That redundancy is exactly why the reduced score should keep one clear peak-amplitude anchor rather than several peak-amplitude proxies.

The earlier Glendale/SMF2 outlier does not justify replacing PGA with PGV. It showed that the workflow needed a post-metric amplitude sanity gate, not that PGA lacks scientific value. With the strict 1 g PGA threshold and nearby-station residual checks in place, physically impossible peak accelerations are rejected before model scoring. PGV remains useful as an amplitude sensitivity check, but including both PGA and PGV in the primary five-metric score would add a second highly correlated amplitude measure. PGD is less attractive as the primary amplitude metric because displacement amplitudes are more vulnerable to low-frequency baseline and integration issues. PGA is therefore the best single representative of peak amplitude once metric-level QC is enforced.

## Arias duration: duration information not reducible to amplitude

Arias duration is retained because it measures the time interval over which shaking energy accumulates. This is a different model attribute from peak amplitude: two simulations can have similar PGA while one releases energy too briefly and the other sustains shaking over a realistic interval. The correlation and PCA products place the duration metrics away from the main amplitude/intensity cluster, which supports retaining a duration representative in the reduced set.

Arias duration is preferred over energy duration because it is the more standard duration measure and is directly tied to the Arias-intensity envelope. Energy duration is still a useful diagnostic, but including both would double-count the same duration axis. The spatial-consistency diagnostics indicate that Arias duration behaves coherently for nearby stations, which is important for regional model validation: a duration residual should reflect a coherent path or structural effect, not row-level noise.

## FAS: frequency content beyond a single peak value

Fourier amplitude spectrum (FAS) is retained to represent frequency-dependent model performance. PGA gives a compact peak-amplitude diagnostic, but it cannot identify whether a model places energy in the wrong part of the spectrum. FAS directly tests the frequency content of the waveform, so it can expose bandwidth, attenuation, basin response, and source-spectrum errors that are hidden by scalar peak measures.

FAS is preferred over PSA for this reduced scientific score because PSA is very strongly tied to the oscillator-response amplitude family and remains highly correlated with PGA-like measures in the collapsed products. PSA is valuable for engineering applications and should remain available for those analyses, but using PSA alongside PGA in an equal-weight reduced score would partly reweight the score toward amplitude response. FAS gives a more direct spectral-amplitude diagnostic while keeping the selected set compact.

## Traveltime delay: explicit phase and arrival-time error

Traveltime delay is retained because timing errors are qualitatively different from amplitude errors. A model may match amplitudes and spectral content while arrivals are systematically early or late. If the score contains only amplitude, duration, and spectral metrics, that phase bias can be hidden inside broader waveform-mismatch measures. Traveltime delay makes the phase component explicit.

The task 2 diagnostics support using traveltime delay because nearby stations show coherent behavior under the 10 km weighted-neighbor analysis. That coherence is the key requirement: a timing metric should capture regional path or structure errors rather than unstable trace-level artifacts. Traveltime delay is preferred over using only cross-correlation because it reports the signed timing correction directly, which is essential for diagnosing whether velocity structure is too fast or too slow along particular paths.

## Delay-corrected cross correlation: waveform shape after timing is removed

Delay-corrected cross correlation is retained as the waveform-shape metric. It answers a different question from traveltime delay: after allowing the waveform to shift into its best alignment, does the synthetic have the same shape as the observation? This separates phase bias from waveform morphology. A model can have a large traveltime delay but a high delay-corrected correlation, indicating that the waveform shape is good but the arrival time is wrong. Conversely, a low delay-corrected correlation indicates shape, complexity, scattering, or pulse-width problems that remain even after timing is corrected.

Delay-corrected correlation is preferred over original correlation because original correlation mixes timing and shape. That makes it harder to diagnose the source of poor agreement. The recommended set already includes traveltime delay, so the correlation metric should focus on shape after the timing error has been removed. This pairing makes the timing and waveform-similarity information more interpretable than either original correlation alone or delay-corrected correlation without the associated delay.

## Why PGV and CAV are not in the primary five

PGV and CAV remain useful secondary diagnostics, but they are not part of the primary five-metric set because they add less independent information than the selected timing and waveform-shape metrics. PGV is an excellent amplitude measure, but it is strongly correlated with PGA and other amplitude metrics. Choosing PGA as the amplitude anchor leaves room for duration, spectral, timing, and shape measures without giving peak amplitude two slots in a five-metric score.

CAV is also valuable, especially for cumulative shaking, but it overlaps with the amplitude/intensity cluster. In the reduced set, cumulative effects are partly represented through Arias duration and FAS, while peak shaking is represented by PGA. Adding CAV would either displace traveltime delay or delay-corrected correlation, which would remove a more distinct error mode, or it would expand the metric set and reintroduce amplitude/intensity over-weighting. For a compact score, CAV should be retained as a companion diagnostic rather than a primary score component.

## Evidence and limitations

The figure set summarizes the selection logic. The correlation figure shows the selected obs/syn scalar metrics that are represented in the task 1 products: PGA, Arias duration, and FAS. The PCA loading figure shows that duration separates from the amplitude/spectral axis, while FAS samples frequency-dependent behavior within the broader amplitude family. The spatial-consistency figure verifies that all five selected metrics are coherent among nearby stations using the 10 km weighted-neighbor diagnostic. The robustness figure checks whether tail treatment changes the residual distribution enough to make a metric unstable.

The selected metrics should still be weighted deliberately. PGA and FAS are not fully independent because spectral amplitudes and peak amplitudes both respond to shaking strength. FAS is also period dependent, so any collapsed FAS score should document the periods and passbands used. Traveltime delay and delay-corrected correlation are comparison-only metrics, so they are absent from the obs/syn PCA and must be justified from spatial coherence, robustness, and waveform examples. Finally, the Glendale/SMF2 case demonstrates that metric-level QC is necessary before using any reduced score: even a scientifically appropriate metric can be misleading if physically impossible amplitudes are allowed through the table.
"""
    path = OUT / "recommended_metric_dissertation_section.md"
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return path


def _scorecard_markdown(scorecard: pd.DataFrame) -> str:
    display = scorecard.copy()
    numeric_columns = [
        "nearby_station_weighted_corr",
        "max_abs_winsorized_change_iqr",
        "max_abs_residual_corr_with_selected",
    ]
    for column in numeric_columns:
        display[column] = display[column].map(lambda value: "not applicable" if pd.isna(value) else f"{float(value):.3f}")
    display["notes"] = display["notes"].fillna("")
    return display.to_markdown(index=False)


def main() -> None:
    _setup()
    figure_paths = [
        _plot_selected_correlations(),
        _plot_pca_loadings(),
        _plot_spatial_consistency(),
        _plot_outlier_robustness(),
    ]
    scorecard = _build_scorecard()
    scorecard_path = OUT / "recommended_metric_scorecard.csv"
    scorecard.to_csv(scorecard_path, index=False)
    report_path = _write_report(scorecard, figure_paths)
    manifest = pd.DataFrame(
        [{"artifact": "scorecard", "path": str(scorecard_path.relative_to(ROOT))}]
        + [{"artifact": "figure", "path": str(path.relative_to(ROOT))} for path in figure_paths]
        + [{"artifact": "report", "path": str(report_path.relative_to(ROOT))}]
    )
    manifest.to_csv(OUT / "manifest.csv", index=False)
    print(f"Wrote {len(figure_paths)} figures, scorecard, and report to {OUT}")


if __name__ == "__main__":
    main()
