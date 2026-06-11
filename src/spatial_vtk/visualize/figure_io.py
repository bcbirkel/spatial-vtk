"""Shared Matplotlib figure display and save helpers.

Purpose
-------
This module keeps Spatial-VTK plotting functions consistent in notebooks,
scripts, and CLI calls. Plot functions return a Matplotlib figure, can display
automatically in notebooks, and can save either through a one-line plotting
call or a separate ``savefig`` call.

Usage examples
--------------
Create and display a figure in a notebook:
  ``fig = plot_retention_summary(retention_table)``

Save a returned figure:
  ``savefig(fig, outpath="retention_summary.png")``

Show and save in one call:
  ``plot_retention_summary(retention_table, showfig=True, savefig=True, outpath="retention_summary.png")``
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import warnings

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from spatial_vtk.config.outputs import resolve_output_path
from spatial_vtk.config.runtime import SpatialVTKConfig

DEFAULT_FIGURE_NAMES: tuple[str, ...] = (
    "station_event_context",
    "event_magnitude_map",
    "station_coverage",
    "event_coverage",
    "record_coverage",
    "retention_summary",
    "data_synthetic_availability",
    "post_qc_station_event_map",
    "event_trace_comparison",
    "drop_cause_diagnostics",
    "psa_period_curve",
    "residuals_vs_distance",
    "score_trends",
    "station_event_network_map",
    "event_beachball_map",
    "station_residual_map",
    "score_map",
    "metric_map_by_model",
    "residual_grid",
    "spatial_correlation_distance",
    "pca_mode_map",
    "pca_explained_variance",
    "pca_feature_loadings",
    "geology_contrast",
    "scatterplot",
    "boxplot",
    "heatmap",
    "event_residual_map",
    "geojson_polygons_map",
    "corridor_map",
    "station_event_waveform_map",
    "pattern_similarity",
    "block_holdout_summary",
    "cluster_summary",
    "redcap_cluster_map",
    "model_metric_heatmap",
    "winner_heatmap",
    "band_score_distribution",
)


def default_figure_paths(
    figure_dir: str | Path,
    names: tuple[str, ...] | list[str] | None = None,
    *,
    suffix: str = ".png",
    create_dir: bool = True,
) -> SimpleNamespace:
    """Return a namespace of standard figure paths.

    Parameters
    ----------
    figure_dir
        Directory where figures should be written.
    names
        Optional figure basenames. When omitted, common tutorial/workflow
        figure names are returned.
    suffix
        File extension to append when a name has no extension.
    create_dir
        Whether to create ``figure_dir``.

    Returns
    -------
    types.SimpleNamespace
        Namespace with one attribute per figure basename.
    """

    root = Path(figure_dir).expanduser()
    if create_dir:
        root.mkdir(parents=True, exist_ok=True)
    paths = {}
    for raw_name in names or DEFAULT_FIGURE_NAMES:
        name = str(raw_name).strip()
        if not name:
            continue
        path = Path(name)
        attr = path.stem.replace("-", "_").replace(" ", "_")
        filename = path.name if path.suffix else f"{path.name}{suffix}"
        paths[attr] = root / filename
    return SimpleNamespace(**paths)


def savefig(
    fig: Figure,
    outpath: str | Path,
    *,
    close: bool = False,
    bbox_inches: str = "tight",
    **kwargs: Any,
) -> Path:
    """Save a Matplotlib figure and return the written path.

    Parameters
    ----------
    fig
        Matplotlib figure to save.
    outpath
        Destination image path.
    close
        Whether to close the figure after saving.
    bbox_inches
        Matplotlib bounding-box setting used by ``Figure.savefig``.
    **kwargs
        Additional keyword arguments passed to ``Figure.savefig``.

    Returns
    -------
    pathlib.Path
        Written figure path.
    """

    path = Path(outpath).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches=bbox_inches, **kwargs)
    setattr(fig, "spatial_vtk_saved_path", path)
    setattr(fig, "exists", path.exists)
    setattr(fig, "stat", path.stat)
    if close:
        plt.close(fig)
    return path


def finish_figure(
    fig: Figure,
    output_path: str | Path | None = None,
    *,
    outpath: str | Path | None = None,
    output_key: str | None = None,
    cfg: SpatialVTKConfig | None = None,
    showfig: bool | None = None,
    savefig: bool | None = None,
    close: bool | None = None,
    bbox_inches: str = "tight",
    **savefig_kwargs: Any,
) -> Figure:
    """Apply standard show/save behavior and return the figure.

    Parameters
    ----------
    fig
        Matplotlib figure to finish.
    output_path, outpath
        Optional destination path. ``outpath`` is the preferred public keyword;
        ``output_path`` preserves older positional usage.
    output_key
        Optional default-output registry key. When omitted and ``savefig`` is
        true, Spatial-VTK infers a key from the plotting function name.
    cfg
        Optional config object used to resolve default output folders.
    showfig
        Whether to display the figure. When ``None``, figures display inside
        notebooks and stay quiet in scripts/tests.
    savefig
        Whether to save the figure. When ``None``, the figure is saved if a
        path is provided.
    close
        Whether to close the figure after saving/display handling. When
        ``None``, finished figures that are saved or explicitly displayed are
        closed after handling. This prevents notebook backends from auto-
        rendering a second copy after Spatial-VTK has already displayed one.
    bbox_inches
        Matplotlib bounding-box setting used by ``Figure.savefig``.
    **savefig_kwargs
        Additional keyword arguments passed to ``Figure.savefig``.

    Returns
    -------
    matplotlib.figure.Figure
        The input figure.
    """

    path = outpath if outpath is not None else output_path
    should_show = _in_notebook() if showfig is None else bool(showfig)
    should_save = (path is not None) if savefig is None else bool(savefig)
    should_close = bool(should_save or should_show) if close is None else bool(close)
    if should_save:
        resolved_path = resolve_output_path(output_key, kind="figure", outpath=path, cfg=cfg, create_parent=True)
        globals()["savefig"](fig, resolved_path, close=False, bbox_inches=bbox_inches, **savefig_kwargs)
    if should_show:
        _display_figure(fig, bbox_inches=bbox_inches)
    if should_close:
        plt.close(fig)
    return fig


def _in_notebook() -> bool:
    """Return whether the current Python process is an IPython notebook kernel."""

    try:
        shell = get_ipython().__class__.__name__  # type: ignore[name-defined]
    except NameError:
        return False
    return shell == "ZMQInteractiveShell"


def _display_figure(fig: Figure, *, bbox_inches: str = "tight") -> None:
    """Display a Matplotlib figure in notebooks and scripts.

    Parameters
    ----------
    fig
        Figure to show. In notebook kernels this uses IPython's rich display so
        executed notebooks retain an embedded image even when the figure is
        assigned to a variable. Outside notebooks it falls back to
        ``matplotlib.pyplot.show``.
    bbox_inches
        Matplotlib bounding-box setting used when rendering the notebook PNG.

    Returns
    -------
    None
    """

    if _in_notebook():
        try:
            from IPython.display import Image, display

            buffer = BytesIO()
            fig.savefig(buffer, format="png", bbox_inches=bbox_inches)
            display(Image(data=buffer.getvalue()))
            return
        except Exception:
            pass
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="FigureCanvasAgg is non-interactive.*", category=UserWarning)
        plt.show()


__all__ = ["DEFAULT_FIGURE_NAMES", "default_figure_paths", "finish_figure", "savefig"]
