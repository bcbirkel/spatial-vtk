"""Plot wrappers for PCA spatial-mode diagnostics.

Purpose
-------
This module draws non-map PCA diagnostics from public spatial-mode outputs:
explained-variance summaries and feature-loading bars.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from spatial_vtk.config.labels import display_label
from spatial_vtk.visualize.figure_context import apply_figure_context
from spatial_vtk.visualize.figure_io import finish_figure


def _display_label(value: object, label_map: Mapping[str, str] | None = None) -> str:
    """Convert a PCA feature token into a readable figure label."""

    return display_label(value, dict(label_map or {}))


def plot_pca_explained_variance(
    explained_variance_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    title: str = "PCA Explained Variance",
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot explained variance by PCA mode.

    Parameters
    ----------
    explained_variance_df
        Output ``explained_variance`` table from ``compute_pca_spatial_modes``.
    output_path
        Figure path to write.
    title
        Figure title.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    fig, ax = plt.subplots(figsize=(7.0, 4.6), dpi=180)
    if explained_variance_df.empty:
        ax.text(0.5, 0.5, "No PCA modes", ha="center", va="center", transform=ax.transAxes)
    else:
        plot_df = explained_variance_df.sort_values("mode_index").copy()
        x = np.arange(len(plot_df))
        ratios = pd.to_numeric(plot_df["explained_variance_ratio"], errors="coerce").to_numpy(dtype=float)
        cumulative = pd.to_numeric(plot_df["cumulative_explained_variance_ratio"], errors="coerce").to_numpy(dtype=float)
        labels = plot_df["mode"].astype(str).tolist()
        ax.bar(x, ratios, color="#4c78a8", alpha=0.9, label="mode")
        ax.plot(x, cumulative, color="#f58518", marker="o", linewidth=1.4, label="cumulative")
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylim(0.0, min(1.05, max(1.0, float(np.nanmax(cumulative)) + 0.05)))
        ax.set_ylabel("Explained variance ratio")
        ax.legend(frameon=True)
    apply_figure_context(ax, explained_variance_df, value_col="explained_variance_ratio", title=title, max_values=3, include_counts=False)
    ax.grid(True, axis="y", alpha=0.25)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)


def plot_pca_feature_loadings(
    feature_loadings_df: pd.DataFrame,
    output_path: str | Path | None = None,
    *,
    mode: str = "PC1",
    top_n: int = 12,
    feature_label_map: Mapping[str, str] | None = None,
    title: str | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    outpath: str | Path | None = None,
) -> plt.Figure:
    """Plot the strongest feature loadings for one PCA mode.

    Parameters
    ----------
    feature_loadings_df
        Output ``feature_loadings`` table from ``compute_pca_spatial_modes``.
    output_path
        Figure path to write.
    mode
        Mode label to plot, such as ``"PC1"``.
    top_n
        Number of strongest absolute loadings to draw.
    feature_label_map
        Optional mapping from raw feature tokens to display labels.
    title
        Optional figure title.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    fig, ax = plt.subplots(figsize=(8.0, 5.2), dpi=180)
    subset = feature_loadings_df.loc[feature_loadings_df.get("mode", "").astype(str) == str(mode)].copy()
    if subset.empty:
        ax.text(0.5, 0.5, f"No loadings for {mode}", ha="center", va="center", transform=ax.transAxes)
    else:
        subset = subset.sort_values("absolute_loading", ascending=False).head(int(top_n)).copy()
        subset = subset.sort_values("loading", ascending=True)
        colors = np.where(pd.to_numeric(subset["loading"], errors="coerce") >= 0.0, "#d55e00", "#0072b2")
        y = np.arange(len(subset))
        ax.barh(y, subset["loading"].to_numpy(dtype=float), color=colors, alpha=0.9)
        ax.set_yticks(y)
        ax.set_yticklabels([_display_label(value, feature_label_map) for value in subset["feature"]])
        ax.axvline(0.0, color="black", linewidth=0.8)
        ax.set_xlabel("PCA loading")
    apply_figure_context(ax, subset, value_col="loading", title=title or f"{mode} Feature Loadings", max_values=3, include_counts=False)
    ax.grid(True, axis="x", alpha=0.25)
    return finish_figure(fig, output_path, outpath=outpath, showfig=showfig, savefig=savefig)
