#!/usr/bin/env python3
"""Build a self-contained PDF companion for the CVM-SI hypothesis report.

The analysis report intentionally stays as lightweight Markdown for review and
versioning. This script turns that Markdown into a readable PDF and appends the
reviewed figure PNGs so the delivered report can be opened without navigating
the output tree.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_ROOT = REPO_ROOT / "outputs" / "review" / "cvmsi_hypothesis_study"
DEFAULT_REPORT_MD = DEFAULT_REPORT_ROOT / "report" / "cvmsi_integrated_hypothesis_report.md"
DEFAULT_OUTPUT_PDF = DEFAULT_REPORT_ROOT / "report" / "cvmsi_integrated_hypothesis_report.pdf"
DEFAULT_MANIFEST = DEFAULT_REPORT_ROOT / "report" / "cvmsi_integrated_hypothesis_report_pdf_manifest.json"


@dataclass(frozen=True)
class FigureSpec:
    label: str
    caption: str
    path: Path


FIGURES: tuple[FigureSpec, ...] = (
    FigureSpec(
        "Figure 1",
        "Observed site anomaly versus residual map.",
        Path("figures/fig_01_observed_site_anomaly_vs_residual_map.png"),
    ),
    FigureSpec(
        "Figure 2",
        "Region-period residual heatmap.",
        Path("figures/fig_02_region_period_residual_heatmap.png"),
    ),
    FigureSpec(
        "Figure 3",
        "Path-period residual contrasts.",
        Path("figures/fig_03_path_period_contrasts.png"),
    ),
    FigureSpec(
        "Figure 4",
        "CVM-SI surface Vs versus Vs30 mismatch.",
        Path("figures/fig_04_model_vs30_site_mismatch.png"),
    ),
    FigureSpec(
        "Figure 5",
        "Geologic unit residual effects.",
        Path("figures/fig_05_geologic_unit_residual_effects.png"),
    ),
    FigureSpec(
        "Figure 6",
        "CVM-SI cross sections with residual markers.",
        Path("figures/fig_06_cvm_si_cross_sections_with_residuals.png"),
    ),
    FigureSpec(
        "Figure 7",
        "Source magnitude, depth, and faulting residuals.",
        Path("extended/figures/fig_07_source_magnitude_depth_faulting.png"),
    ),
    FigureSpec(
        "Figure 8",
        "Distance attenuation by path class.",
        Path("extended/figures/fig_08_distance_attenuation_binned.png"),
    ),
    FigureSpec(
        "Figure 9",
        "Component-azimuth residual heatmaps.",
        Path("extended/figures/fig_09_component_azimuth_heatmaps.png"),
    ),
    FigureSpec(
        "Figure 10",
        "Station and event support density maps.",
        Path("extended/figures/fig_10_support_density_maps.png"),
    ),
    FigureSpec(
        "Figure 11",
        "Station geomorphology effects.",
        Path("extended/figures/fig_11_geomorphology_effects.png"),
    ),
    FigureSpec(
        "Figure 12",
        "PGA path-azimuth heatmap.",
        Path("extended/figures/fig_12_path_azimuth_pga_heatmap.png"),
    ),
    FigureSpec(
        "Figure 13",
        "Targeted residual corridors on basemaps with CVM-SI Vs sections.",
        Path("case_studies/figures/fig_13_case_study_corridors_and_cvm_sections.png"),
    ),
    FigureSpec(
        "Figure 14",
        "Observed and CVM-SI synthetic waveform examples for targeted corridors.",
        Path("case_studies/figures/fig_14_case_study_waveform_examples.png"),
    ),
    FigureSpec(
        "Figure 15",
        "Mixed-effects variance decomposition across nested models.",
        Path("mixed_effects/figures/fig_15_mixed_effects_variance_decomposition.png"),
    ),
    FigureSpec(
        "Figure 16",
        "Key mixed-effects fixed-effect intervals after event and station controls.",
        Path("mixed_effects/figures/fig_16_mixed_effects_key_fixed_effects.png"),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--output-pdf", type=Path, default=DEFAULT_OUTPUT_PDF)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def strip_inline_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = text.replace("*", "")
    return text


def trim_image_whitespace(image: Image.Image, *, threshold: int = 248, padding: int = 24) -> Image.Image:
    """Trim large white margins from a figure while preserving a small border."""

    rgb = image.convert("RGB")
    array = np.asarray(rgb)
    mask = np.any(array < threshold, axis=2)
    if not mask.any():
        return rgb

    ys, xs = np.where(mask)
    left = max(int(xs.min()) - padding, 0)
    right = min(int(xs.max()) + padding + 1, rgb.width)
    top = max(int(ys.min()) - padding, 0)
    bottom = min(int(ys.max()) + padding + 1, rgb.height)
    return rgb.crop((left, top, right, bottom))


class TextReportWriter:
    def __init__(self, pdf: PdfPages, title: str) -> None:
        self.pdf = pdf
        self.title = title
        self.page_number = 0
        self.fig = None
        self.y = 0.0
        self.new_page()

    def new_page(self) -> None:
        if self.fig is not None:
            self._footer()
            self.pdf.savefig(self.fig)
            plt.close(self.fig)
        self.page_number += 1
        self.fig = plt.figure(figsize=(8.5, 11), facecolor="white")
        self.y = 0.935
        self.fig.text(
            0.075,
            0.965,
            self.title,
            ha="left",
            va="top",
            fontsize=8.5,
            color="#5f6368",
        )

    def close(self) -> None:
        if self.fig is not None:
            self._footer()
            self.pdf.savefig(self.fig)
            plt.close(self.fig)
            self.fig = None

    def _footer(self) -> None:
        assert self.fig is not None
        self.fig.text(
            0.5,
            0.035,
            f"{self.page_number}",
            ha="center",
            va="center",
            fontsize=8.0,
            color="#5f6368",
        )

    def add_text(
        self,
        text: str,
        *,
        fontsize: float = 10.5,
        weight: str = "normal",
        color: str = "#202124",
        family: str = "DejaVu Sans",
        indent: float = 0.075,
        width_chars: int = 92,
        top_space: float = 0.0,
        bottom_space: float = 0.006,
    ) -> None:
        assert self.fig is not None
        if top_space:
            self.y -= top_space

        wrapped = textwrap.wrap(
            text,
            width=width_chars,
            break_long_words=True,
            break_on_hyphens=False,
        ) or [""]
        line_height = (fontsize / 72.0 / 11.0) * 1.34
        for line in wrapped:
            if self.y - line_height < 0.072:
                self.new_page()
            self.fig.text(
                indent,
                self.y,
                line,
                ha="left",
                va="top",
                fontsize=fontsize,
                fontweight=weight,
                color=color,
                family=family,
            )
            self.y -= line_height
        self.y -= bottom_space

    def add_blank(self, height: float = 0.014) -> None:
        self.y -= height
        if self.y < 0.09:
            self.new_page()


def markdown_lines(markdown: str) -> Iterable[tuple[str, str]]:
    in_code = False
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            in_code = not in_code
            yield ("blank", "")
            continue
        if in_code:
            yield ("code", line)
        elif not line.strip():
            yield ("blank", "")
        elif line.startswith("# "):
            yield ("h1", strip_inline_markdown(line[2:].strip()))
        elif line.startswith("## "):
            yield ("h2", strip_inline_markdown(line[3:].strip()))
        elif line.startswith("### "):
            yield ("h3", strip_inline_markdown(line[4:].strip()))
        elif line.lstrip().startswith("- "):
            indent_level = len(line) - len(line.lstrip())
            bullet_text = strip_inline_markdown(line.lstrip()[2:].strip())
            yield ("bullet", f"{'  ' * (indent_level // 2)}- {bullet_text}")
        elif re.match(r"^\d+\.\s+", line.lstrip()):
            indent_level = len(line) - len(line.lstrip())
            item = strip_inline_markdown(line.lstrip())
            yield ("number", f"{'  ' * (indent_level // 2)}{item}")
        else:
            yield ("body", strip_inline_markdown(line))


def add_markdown_pages(pdf: PdfPages, markdown_path: Path) -> int:
    title = "CVM-SI Observed/Synthetic Hypothesis Report"
    writer = TextReportWriter(pdf, title=title)
    writer.add_text(
        title,
        fontsize=20,
        weight="bold",
        width_chars=42,
        top_space=0.018,
        bottom_space=0.02,
    )
    writer.add_text(
        "Private working report. Do not push to the public repository.",
        fontsize=11.5,
        color="#5f6368",
        width_chars=80,
        bottom_space=0.018,
    )
    writer.add_text(
        f"Generated {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} from {markdown_path.name}. "
        "The PDF includes a figure appendix with the reviewed PNG exports.",
        fontsize=10.5,
        color="#5f6368",
        width_chars=86,
        bottom_space=0.03,
    )

    markdown = markdown_path.read_text(encoding="utf-8")
    skipped_initial_title = False
    skipped_initial_private_note = False
    for kind, line in markdown_lines(markdown):
        if kind == "h1" and not skipped_initial_title:
            skipped_initial_title = True
            continue
        if (
            kind == "body"
            and skipped_initial_title
            and not skipped_initial_private_note
            and line == "Private working report. Do not push to the public repository."
        ):
            skipped_initial_private_note = True
            continue
        if kind == "blank":
            writer.add_blank(0.012)
        elif kind == "h1":
            writer.add_text(line, fontsize=19, weight="bold", width_chars=58, top_space=0.018, bottom_space=0.014)
        elif kind == "h2":
            writer.add_text(line, fontsize=15, weight="bold", width_chars=68, top_space=0.018, bottom_space=0.012)
        elif kind == "h3":
            writer.add_text(line, fontsize=12.5, weight="bold", width_chars=78, top_space=0.012, bottom_space=0.009)
        elif kind == "bullet":
            writer.add_text(line, fontsize=10.1, width_chars=86, indent=0.095, bottom_space=0.004)
        elif kind == "number":
            writer.add_text(line, fontsize=10.1, width_chars=86, indent=0.095, bottom_space=0.004)
        elif kind == "code":
            writer.add_text(
                line,
                fontsize=8.5,
                width_chars=88,
                family="DejaVu Sans Mono",
                color="#3c4043",
                indent=0.095,
                bottom_space=0.002,
            )
        else:
            writer.add_text(line, fontsize=10.3, width_chars=91, bottom_space=0.005)
    writer.close()
    return writer.page_number


def add_figure_appendix(pdf: PdfPages, report_root: Path) -> tuple[int, list[dict[str, object]]]:
    records: list[dict[str, object]] = []
    page_count = 0

    cover = plt.figure(figsize=(8.5, 11), facecolor="white")
    cover.text(0.075, 0.90, "Figure Appendix", fontsize=22, weight="bold", ha="left", va="top")
    appendix_note = (
        "Reviewed figures from the CVM-SI observed/synthetic hypothesis study. "
        "Map figures use rendered basemaps and equal projected-axis scaling where geographic scale matters."
    )
    cover.text(
        0.075,
        0.84,
        "\n".join(textwrap.wrap(appendix_note, width=82, break_long_words=False, break_on_hyphens=False)),
        fontsize=11.5,
        ha="left",
        va="top",
    )
    pdf.savefig(cover)
    plt.close(cover)
    page_count += 1

    for spec in FIGURES:
        figure_path = report_root / spec.path
        exists = figure_path.exists()
        record: dict[str, object] = {
            "label": spec.label,
            "caption": spec.caption,
            "path": str(figure_path),
            "exists": exists,
        }
        if not exists:
            fig = plt.figure(figsize=(8.5, 11), facecolor="white")
            fig.text(0.075, 0.92, f"{spec.label}: {spec.caption}", fontsize=14, weight="bold", va="top")
            fig.text(0.075, 0.84, f"Missing figure file: {figure_path}", fontsize=11, color="#b3261e", va="top")
            pdf.savefig(fig)
            plt.close(fig)
            page_count += 1
            records.append(record)
            continue

        with Image.open(figure_path) as image:
            original_width, original_height = image.size
            image = trim_image_whitespace(image)
            width, height = image.size
            aspect = width / max(height, 1)
            record["pixels"] = [original_width, original_height]
            record["trimmed_pixels"] = [width, height]
            array = np.asarray(image)

        if aspect >= 1.08:
            fig = plt.figure(figsize=(11, 8.5), facecolor="white")
            caption_y = 0.965
            ax_rect = [0.035, 0.045, 0.93, 0.86]
            caption_width = 118
        else:
            fig = plt.figure(figsize=(8.5, 11), facecolor="white")
            caption_y = 0.955
            ax_rect = [0.055, 0.055, 0.89, 0.82]
            caption_width = 88

        caption = f"{spec.label}: {spec.caption}"
        wrapped_caption = "\n".join(
            textwrap.wrap(caption, width=caption_width, break_long_words=False, break_on_hyphens=False)
        )
        fig.text(0.045, caption_y, wrapped_caption, fontsize=12.5, weight="bold", ha="left", va="top")
        ax = fig.add_axes(ax_rect)
        ax.imshow(array)
        ax.set_axis_off()
        pdf.savefig(fig)
        plt.close(fig)
        page_count += 1
        records.append(record)

    return page_count, records


def main() -> None:
    args = parse_args()
    report_md = args.report_md.resolve()
    report_root = args.report_root.resolve()
    output_pdf = args.output_pdf.resolve()
    manifest_path = args.manifest.resolve()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    if not report_md.exists():
        raise FileNotFoundError(f"Markdown report not found: {report_md}")
    if not report_root.exists():
        raise FileNotFoundError(f"Report root not found: {report_root}")

    with PdfPages(output_pdf) as pdf:
        info = pdf.infodict()
        info["Title"] = "CVM-SI Observed/Synthetic Hypothesis Report"
        info["Author"] = "spatial-vtk private analysis"
        info["Subject"] = "CVM-SI observed/synthetic residual hypotheses"
        info["Keywords"] = "CVM-SI, observed synthetic residuals, spatial statistics, seismology"
        info["CreationDate"] = dt.datetime.now()
        text_pages = add_markdown_pages(pdf, report_md)
        figure_pages, figures = add_figure_appendix(pdf, report_root)

    manifest = {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "report_md": str(report_md),
        "output_pdf": str(output_pdf),
        "text_pages": text_pages,
        "figure_pages": figure_pages,
        "total_pages": text_pages + figure_pages,
        "figures": figures,
        "missing_figures": [record for record in figures if not record["exists"]],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_pdf}")
    print(f"Wrote {manifest_path}")
    print(f"Pages: {manifest['total_pages']} ({text_pages} text, {figure_pages} figure appendix)")
    if manifest["missing_figures"]:
        print(f"Missing figures: {len(manifest['missing_figures'])}")


if __name__ == "__main__":
    main()
