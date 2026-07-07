#!/usr/bin/env python3
"""Plot basin-station PGA event median residuals against magnitude."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DEFAULT_INPUT = Path(
    "outputs/review/user_requested_large_run_figures/"
    "basin_metric_maps_pga_fas/pga_basin_event_residual_summary.csv"
)
DEFAULT_OUTPUT_DIR = Path(
    "outputs/review/user_requested_large_run_figures/basin_metric_maps_pga_fas"
)
DEFAULT_EVENT_METADATA = DEFAULT_OUTPUT_DIR / "prepared_events.csv"
PASSBANDS = ("1-2 sec", "2-3 sec", "3-5 sec")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--event-metadata", type=Path, default=DEFAULT_EVENT_METADATA)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--min-stations", type=int, default=1)
    return parser.parse_args()


def linear_fit(x: pd.Series, y: pd.Series) -> tuple[float, float] | None:
    valid = np.isfinite(x.to_numpy(dtype=float)) & np.isfinite(y.to_numpy(dtype=float))
    if valid.sum() < 2:
        return None
    return tuple(np.polyfit(x.to_numpy(dtype=float)[valid], y.to_numpy(dtype=float)[valid], 1))


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.input)
    required = {"passband", "event_id", "event_median", "row_count", "station_count"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns in {args.input}: {missing}")
    if "magnitude" not in df.columns:
        df["magnitude"] = np.nan

    df["magnitude"] = pd.to_numeric(df["magnitude"], errors="coerce")
    if df["magnitude"].notna().sum() == 0 and args.event_metadata.exists():
        events = pd.read_csv(args.event_metadata, usecols=["event_id", "magnitude"])
        events["magnitude"] = pd.to_numeric(events["magnitude"], errors="coerce")
        df = df.drop(columns=["magnitude"]).merge(events.drop_duplicates("event_id"), on="event_id", how="left")

    df = df.loc[df["passband"].astype(str).isin(PASSBANDS)].copy()
    df["event_median"] = pd.to_numeric(df["event_median"], errors="coerce")
    df["magnitude"] = pd.to_numeric(df["magnitude"], errors="coerce")
    df["station_count"] = pd.to_numeric(df["station_count"], errors="coerce")
    df["row_count"] = pd.to_numeric(df["row_count"], errors="coerce")
    df = df.dropna(subset=["event_median", "magnitude", "station_count"])
    df = df.loc[df["station_count"] >= args.min_stations].copy()

    y_absmax = float(np.nanmax(np.abs(df["event_median"]))) if len(df) else 1.0
    y_limit = max(1.0, np.ceil((y_absmax + 0.15) * 2.0) / 2.0)

    fig, axes = plt.subplots(1, 3, figsize=(15.2, 4.8), sharey=True, constrained_layout=True)
    cmap = plt.get_cmap("viridis")
    scatter_for_colorbar = None
    for ax, passband in zip(axes, PASSBANDS, strict=True):
        band = df.loc[df["passband"].astype(str).eq(passband)].copy()
        sizes = 20 + 2.0 * np.sqrt(band["row_count"].clip(lower=1).to_numpy(dtype=float))
        scatter_for_colorbar = ax.scatter(
            band["magnitude"],
            band["event_median"],
            s=sizes,
            c=band["station_count"],
            cmap=cmap,
            edgecolor="#222222",
            linewidth=0.45,
            alpha=0.85,
        )
        ax.axhline(0.0, color="#303030", linewidth=1.0, linestyle="--", alpha=0.8)
        fit = linear_fit(band["magnitude"], band["event_median"])
        if fit is not None:
            slope, intercept = fit
            xs = np.linspace(float(band["magnitude"].min()), float(band["magnitude"].max()), 100)
            ax.plot(xs, slope * xs + intercept, color="#B2182B", linewidth=1.8)
            corr = band[["magnitude", "event_median"]].corr(method="spearman").iloc[0, 1]
            fit_text = f"Spearman rho={corr:+.2f}\nslope={slope:+.2f} log2/Mw"
        else:
            fit_text = "insufficient events"
        ax.text(
            0.03,
            0.97,
            f"events={len(band)}\n{fit_text}",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox={"facecolor": "white", "edgecolor": "#BBBBBB", "alpha": 0.88, "pad": 4},
        )
        ax.set_title(passband)
        ax.set_xlabel("Magnitude (Mw)")
        ax.grid(True, color="#D4D4D4", linewidth=0.8, alpha=0.75)
        ax.set_ylim(-y_limit, y_limit)

    axes[0].set_ylabel("Event median PGA log2(observed / synthetic)\nwithin basin stations")
    if scatter_for_colorbar is not None:
        cbar = fig.colorbar(scatter_for_colorbar, ax=axes, shrink=0.88, pad=0.015)
        cbar.set_label("Basin station count per event")
    fig.suptitle(
        "PGA Event Median Residual vs Magnitude for Basin Stations",
        fontsize=16,
        y=1.04,
    )

    suffix = "" if args.min_stations <= 1 else f"__min{args.min_stations}stations"
    png = args.output_dir / f"pga_event_median_residual_vs_magnitude_by_passband{suffix}.png"
    csv = args.output_dir / f"pga_event_median_residual_vs_magnitude_by_passband{suffix}.csv"
    fig.savefig(png, dpi=220, bbox_inches="tight")
    plt.close(fig)

    keep = ["passband", "event_id", "magnitude", "event_median", "event_mean", "row_count", "station_count", "distance_median_km"]
    df.loc[:, [column for column in keep if column in df.columns]].sort_values(["passband", "magnitude", "event_id"]).to_csv(csv, index=False)
    print(f"Wrote {png}")
    print(f"Wrote {csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
