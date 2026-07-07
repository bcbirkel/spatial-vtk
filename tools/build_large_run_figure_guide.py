"""Build a review-friendly guide and symlink tree for large-run figures."""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import subprocess
import time
from collections import Counter
from pathlib import Path


STEP_LABELS = {
    "step_01": "Step 1 ingest and data preparation",
    "step_02": "Step 2 quality control",
    "step_03_metrics": "Step 3 metric figures",
    "step_04_spatial": "Step 4 spatial statistics figures",
    "step_05_regions": "Step 5 GeoJSON regions and corridors",
    "step_06_additional_diagnostics": "Step 6 additional diagnostics",
    "user_requested_la_basin_event_region_boxplots": "User-requested LA Basin event-region boxplots",
    "user_requested_region_type_boxplots": "User-requested mapped-region-type boxplots",
}

ROOT_FIGURE_STEPS = {
    "data_synthetic_availability": "step_01",
    "event_beachball_map": "step_01",
    "event_coverage": "step_01",
    "record_coverage": "step_01",
    "redcap_cluster_map": "step_01",
    "station_coverage": "step_01",
    "station_event_context": "step_01",
    "drop_cause_diagnostics": "step_02",
    "drop_cause_diagnostics_overlap": "step_02",
    "event_station_retention": "step_02",
    "post_qc_station_event_map": "step_02",
    "retention_summary": "step_02",
    "event_trace_comparison": "step_06_additional_diagnostics",
    "geojson_polygons_map": "step_05_regions",
}

FIGURE_TYPE_DESCRIPTIONS = {
    "data_synthetic_availability": "Context figure showing observed/synthetic data availability.",
    "drop_cause_diagnostics": "QC diagnostic showing why records were dropped.",
    "drop_cause_diagnostics_overlap": "QC diagnostic for overlap-filter drop causes.",
    "event_beachball_map": "Context map of event mechanisms and locations.",
    "event_coverage": "Context figure showing event/station coverage.",
    "event_station_retention": "QC retention summary for event-station records.",
    "post_qc_station_event_map": "QC map of retained station-event records.",
    "record_coverage": "Context figure showing record coverage across inputs.",
    "redcap_cluster_map": "Context map of REDCap/cluster coverage.",
    "retention_summary": "QC retention summary after filtering.",
    "station_coverage": "Context figure showing station coverage.",
    "station_event_context": "Context map of station-event geometry.",
    "band_log2_residual_distribution": "Box/distribution plots summarizing metric values by passband and component.",
    "boxplot": "Metric comparison boxplots with statistical summary tables where available.",
    "event_residual_map": "Event-level residual maps.",
    "heatmap": "Combined metric heatmap across models, metrics, or regions.",
    "metric_by_model_map": "Station map by model for a selected metric and value scale.",
    "period_log2_residual_distribution": "Spectral-period residual distribution plot.",
    "psa_period_curve": "PSA period curve diagnostic.",
    "residual_grid": "Spatial residual grid/interpolated map.",
    "residuals_vs_depth": "Metric value versus event depth.",
    "residuals_vs_distance": "Metric value versus station-event distance.",
    "scatterplot": "Metric relationship scatterplot.",
    "station_metric_map": "Station-level metric map.",
    "spatial_azimuthal_residuals": "Spatial-statistics azimuthal residual diagnostic.",
    "spatial_block_holdout_scatter": "Block holdout spatial prediction diagnostic.",
    "spatial_correlation_distance_by_metric": "Spatial correlation by distance, grouped by metric.",
    "spatial_correlogram": "Spatial correlogram diagnostic.",
    "spatial_event_residual_map": "Step 4 event residual map.",
    "spatial_event_residual_map_event_centered": "Step 4 event-centered residual map.",
    "spatial_geology_contrast": "Residual boxplots by mapped geology class with contrast statistics.",
    "spatial_geomorphology_contrast": "Residual boxplots by broad geomorphology class with pairwise contrasts.",
    "spatial_metric_by_model_map": "Step 4 station metric map by model, raw event mean not removed.",
    "spatial_metric_by_model_map_event_centered": "Step 4 station metric map by model with event mean removed.",
    "spatial_morans_i": "Moran's I spatial autocorrelation diagnostic.",
    "spatial_pca_summary": "PCA spatial mode summary.",
    "spatial_residual_grid": "Step 4 residual grid map, raw event mean not removed.",
    "spatial_residual_grid_event_centered": "Step 4 residual grid map with event mean removed.",
    "spatial_station_bias_map": "Station bias map; marker size encodes station event count.",
    "spatial_station_metric_map": "Step 4 station metric summary map.",
    "spatial_station_metric_map_event_centered": "Step 4 station metric summary map with event mean removed.",
    "geojson_polygons_map": "GeoJSON region overview map with unique region colors and legend.",
    "corridor_map": "Overview or segment map of configured region corridors.",
    "corridor_composite": "One corridor segment map plus available waveform scenario panels.",
    "corridor_waveform": "Observed/synthetic waveform panels for paths in a corridor segment.",
    "region_station_metric_map": "Step 5 station metric map over GeoJSON regions.",
    "region_boxplot": "Metric boxplots by GeoJSON region or mapped region class.",
    "observed_synthetic_record_section": "Observed versus synthetic waveform record section.",
    "station_event_waveform_map": "Map of stations/events selected for waveform review.",
    "metric_heatmap": "Step 6 region heatmap for selected comparison metrics.",
    "model_delta_heatmap": "Step 6 model-difference heatmap after separate per-model aggregation; residual, phase-delay, and cross-correlation quantities use separate color scales.",
    "model_boxplot": "Step 6 model-separated boxplots; one box per model at each category tick.",
    "model_metric_map": "Step 6 side-by-side station metric maps comparing models.",
    "metric_boxplot": "Step 6 metric boxplot by GeoJSON region.",
    "metric_scatterplot": "Step 6 metric relationship scatterplot.",
    "pattern_similarity": "Observed/synthetic station-pattern similarity diagnostic.",
    "station_event_waveform_map": "Step 6 selected station/event waveform map.",
    "la_basin_event_region_boxplot": "User-requested LA Basin event-region boxplot.",
    "mapped_region_type_boxplot": "User-requested mapped-region-type boxplot.",
}

MODEL_ALIASES = {
    "cvmsi-20260506-material-0p6x1p2-asdf": "CVM-S",
    "cvmsi_20260506_material_0p6x1p2_asdf": "CVM-S",
    "cvmh-20260506-material-0p6x1p2-mseed": "CVM-H",
    "cvmh_20260506_material_0p6x1p2_mseed": "CVM-H",
    "all-models": "shared_workflow",
    "all_models": "shared_workflow",
    "model_comparison": "CVM-S_vs_CVM-H_comparison",
}

METRIC_TOKENS = {
    "CAV",
    "FAS",
    "PGA",
    "PGD",
    "PGV",
    "PSA",
    "arias_duration",
    "arias_intensity",
    "energy_duration",
    "energy_intensity",
    "original_cc",
    "delay_corrected_cc",
    "traveltime_delay",
}


def slug(text: object) -> str:
    """Return a filesystem-safe path segment."""

    value = str(text or "unknown").strip()
    value = re.sub(r"[^A-Za-z0-9._+-]+", "_", value)
    return value.strip("_") or "unknown"


def parse_filename(path: Path) -> dict[str, str]:
    """Parse standard ``figure__metric__passband__component__model__value`` names."""

    parts = path.stem.split("__")
    figure_type = parts[0]
    metric = parts[1] if len(parts) > 1 else "overview"
    passband = parts[2] if len(parts) > 2 else "all"
    component = parts[3] if len(parts) > 3 else "all"
    model = parts[4] if len(parts) > 4 else "all-models"
    value = parts[5] if len(parts) > 5 else "value"
    if len(parts) == 5 and parts[3] in MODEL_ALIASES:
        component = parts[2]
        model = parts[3]
        value = parts[4]
    return {
        "figure_type": figure_type,
        "metric": metric,
        "passband": passband,
        "component": component,
        "model": MODEL_ALIASES.get(model, model),
        "value": value,
    }


def infer_from_path(path: Path, root: Path) -> dict[str, str]:
    """Infer review metadata from path folders and filename."""

    info = parse_filename(path)
    parts = path.relative_to(root).parts
    if len(parts) == 1:
        stem = path.stem
        info["figure_type"] = stem
        info["model"] = "shared_workflow"
        if ROOT_FIGURE_STEPS.get(stem) == "step_01":
            info["metric"] = "workflow_context"
        elif ROOT_FIGURE_STEPS.get(stem) == "step_02":
            info["metric"] = "qc_review"
        elif ROOT_FIGURE_STEPS.get(stem) == "step_05_regions":
            info["metric"] = "geojson_overview"
        elif ROOT_FIGURE_STEPS.get(stem) == "step_06_additional_diagnostics":
            info["metric"] = "waveform_review"
        return info
    text_parts = set(parts)
    if parts[0] == "step_06_additional_diagnostics":
        info.update(parse_step06_filename(path))
        if "model_comparison" in text_parts:
            info["model"] = "CVM-S_vs_CVM-H_comparison"
    for raw, alias in MODEL_ALIASES.items():
        if raw in text_parts:
            info["model"] = alias
    if "corridors" in text_parts:
        info["figure_type"] = "corridor_composite" if "composite" in path.stem else "corridor_map"
        if "waveforms" in text_parts and "composite" not in path.stem:
            info["figure_type"] = "corridor_waveform"
        idx = parts.index("corridors")
        if len(parts) > idx + 1:
            info["metric"] = parts[idx + 1]
        if "segment_" in path.stem:
            info["passband"] = path.stem
    if "region_boxplots" in text_parts:
        info["figure_type"] = "region_boxplot" if info["figure_type"].startswith("step_05") else info["figure_type"]
        has_model_folder = any(raw in text_parts for raw in MODEL_ALIASES)
        if parts[0] == "step_05_regions" and not has_model_folder:
            info["model"] = "shared_workflow"
        for token in parts:
            if token in METRIC_TOKENS:
                info["metric"] = token
                break
    if "maps" in text_parts and parts[0] == "step_05_regions":
        info["figure_type"] = "region_station_metric_map"
    if "overview" in text_parts:
        if "geojson" in path.stem:
            info["figure_type"] = "geojson_polygons_map"
        elif "corridor" in path.stem:
            info["figure_type"] = "corridor_map"
    if parts[0].startswith("user_requested"):
        info["model"] = "custom_review"
        stem_parts = path.stem.split("__")
        if stem_parts:
            info["value"] = stem_parts[-1]
        if "la_basin_event_region" in parts[0]:
            info["figure_type"] = "la_basin_event_region_boxplot"
        elif "region_type" in parts[0]:
            info["figure_type"] = "mapped_region_type_boxplot"
    return info


def parse_step06_filename(path: Path) -> dict[str, str]:
    """Parse Step 6 names that use single underscores instead of ``__`` fields."""

    stem = path.stem
    info = parse_filename(path)
    if stem.startswith("step_06_model_delta_heatmap__"):
        parts = stem.split("__")
        info["figure_type"] = "model_delta_heatmap"
        if len(parts) > 1:
            info["metric"] = parts[1]
        else:
            info["metric"] = "model_delta"
        if len(parts) > 2:
            info["passband"] = parts[2]
        info["model"] = "CVM-S_vs_CVM-H_comparison"
        return info
    if stem.startswith("step_06_model_boxplot__"):
        parts = stem.split("__")
        info["figure_type"] = "model_boxplot"
        if len(parts) > 1:
            info["metric"] = parts[1]
        if len(parts) > 2:
            info["passband"] = parts[2]
        if len(parts) > 3:
            info["component"] = parts[3]
        info["model"] = "CVM-S_vs_CVM-H_comparison"
        return info
    if stem.startswith("step_06_model_map__"):
        parts = stem.split("__")
        info["figure_type"] = "model_metric_map"
        if len(parts) > 1:
            info["metric"] = parts[1]
        if len(parts) > 2:
            info["passband"] = parts[2]
        info["model"] = "CVM-S_vs_CVM-H_comparison"
        return info
    if stem.startswith("step_06_metric_boxplot_"):
        info["figure_type"] = "metric_boxplot"
        remainder = stem.removeprefix("step_06_metric_boxplot_")
    elif stem.startswith("step_06_metric_scatterplot_"):
        info["figure_type"] = "metric_scatterplot"
        remainder = stem.removeprefix("step_06_metric_scatterplot_")
    elif stem.startswith("step_06_metric_heatmap_"):
        info["figure_type"] = "metric_heatmap"
        remainder = stem.removeprefix("step_06_metric_heatmap_")
    elif stem.startswith("step_06_pattern_similarity_"):
        info["figure_type"] = "pattern_similarity"
        remainder = stem.removeprefix("step_06_pattern_similarity_")
    elif stem.startswith("step_06_station_event_waveform_map_"):
        info["figure_type"] = "station_event_waveform_map"
        remainder = stem.removeprefix("step_06_station_event_waveform_map_")
    else:
        return info

    model_key = next((key for key in MODEL_ALIASES if remainder.startswith(f"{key}_")), None)
    if model_key is not None:
        info["model"] = MODEL_ALIASES[model_key]
        remainder = remainder.removeprefix(f"{model_key}_")
    metric_key = next((token for token in sorted(METRIC_TOKENS, key=len, reverse=True) if remainder.startswith(f"{token.lower()}_")), None)
    if metric_key is not None:
        info["metric"] = metric_key.lower()
        remainder = remainder.removeprefix(f"{metric_key.lower()}_")
    elif remainder.startswith("requested_metric_comparison_"):
        info["metric"] = "requested_metric_comparison"
        remainder = remainder.removeprefix("requested_metric_comparison_")

    for passband in ("all_passbands", "1_2_sec", "2_3_sec", "3_5_sec"):
        if remainder.startswith(f"{passband}_"):
            info["passband"] = passband.replace("_", "-").replace("all-passbands", "all-passbands")
            remainder = remainder.removeprefix(f"{passband}_")
            break
    for component in ("all_components", "r", "t", "z"):
        if remainder.startswith(f"{component}_") or remainder == component:
            info["component"] = component.upper() if len(component) == 1 else component.replace("_", "-")
            remainder = remainder.removeprefix(f"{component}_")
            if remainder == component:
                remainder = ""
            break
    if remainder:
        info["value"] = remainder
    return info


def top_key(path: Path, root: Path) -> str:
    """Return the top-level figure folder for one output path."""

    parts = path.relative_to(root).parts
    if len(parts) == 1:
        return ROOT_FIGURE_STEPS.get(path.stem, "legacy_root")
    return parts[0] if parts else "unknown"


def source_roots(root: Path) -> list[Path]:
    """Return canonical roots to include in the guide."""

    return [
        root / "step_03_metrics",
        root / "step_04_spatial",
        root / "step_05_regions",
        root / "step_06_additional_diagnostics",
        root / "user_requested_la_basin_event_region_boxplots",
        root / "user_requested_region_type_boxplots",
    ]


def remove_existing_tree(path: Path) -> None:
    """Remove an existing review tree, retrying NFS directory cleanup races."""

    if not path.exists():
        return
    last_error: Exception | None = None
    for _attempt in range(3):
        try:
            shutil.rmtree(path)
            return
        except OSError as exc:
            last_error = exc
            time.sleep(1)
    subprocess.run(["rm", "-rf", str(path)], check=True)
    if path.exists() and last_error is not None:
        raise last_error


def flatten_single_figure_dirs(tree_root: Path, *, inventory_root: Path) -> dict[str, str]:
    """Flatten single-figure leaf directories and return inventory path updates."""

    figure_exts = {".png", ".jpg", ".jpeg", ".pdf", ".svg"}
    moved: dict[str, str] = {}

    def folder_token(value: object) -> str:
        text = str(value or "").strip()
        text = re.sub(r"[^A-Za-z0-9._+-]+", "_", text)
        return text.strip("_") or "folder"

    def candidate(directory: Path) -> Path | None:
        if not directory.is_dir():
            return None
        children = [path for path in directory.iterdir() if not path.name.startswith(".")]
        subdirs = [path for path in children if path.is_dir()]
        figures = [path for path in children if path.is_file() and path.suffix.lower() in figure_exts]
        other = [path for path in children if path.is_file() and path.suffix.lower() not in figure_exts]
        if len(figures) == 1 and not subdirs and not other:
            return figures[0]
        return None

    def destination_for(figure: Path, folder: Path) -> Path:
        parent = folder.parent
        token = folder_token(folder.name)
        if token.casefold() in figure.stem.casefold():
            name = figure.name
        else:
            name = f"{figure.stem}__{token}{figure.suffix}"
        destination = parent / name
        if not destination.exists() and not destination.is_symlink():
            return destination
        stem = destination.stem
        suffix = destination.suffix
        counter = 2
        while True:
            alternate = parent / f"{stem}__{counter}{suffix}"
            if not alternate.exists() and not alternate.is_symlink():
                return alternate
            counter += 1

    while True:
        batch = []
        for directory in tree_root.rglob("*"):
            figure = candidate(directory)
            if figure is not None:
                batch.append((len(directory.parts), directory, figure))
        if not batch:
            break
        changed = False
        for _depth, folder, figure in sorted(batch, reverse=True):
            if not figure.exists() and not figure.is_symlink():
                continue
            if candidate(folder) is None:
                continue
            destination = destination_for(figure, folder)
            old_rel = str(figure.relative_to(inventory_root))
            if figure.is_symlink():
                target = figure.resolve(strict=False)
                figure.unlink()
                os.symlink(os.path.relpath(target, destination.parent), destination)
            else:
                figure.rename(destination)
            try:
                folder.rmdir()
            except OSError:
                pass
            moved[old_rel] = str(destination.relative_to(inventory_root))
            changed = True
        if not changed:
            break
    return moved


def build_guide(root: Path) -> tuple[int, Path, Path, Path]:
    """Create the organized symlink tree, CSV inventory, and Markdown guide."""

    root = root.resolve()
    organized = root / "organized_review"
    guide = root / "FIGURE_OUTPUT_GUIDE.md"
    inventory_csv = root / "figure_inventory.csv"
    pngs: list[Path] = []
    for source in source_roots(root):
        if source.exists():
            pngs.extend(sorted(path for path in source.rglob("*.png") if organized not in path.parents))
    pngs.extend(sorted(root.glob("*.png")))

    remove_existing_tree(organized)
    organized.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    for path in pngs:
        info = infer_from_path(path, root)
        step = top_key(path, root)
        dest_dir = organized / slug(step) / slug(info["model"]) / slug(info["figure_type"]) / slug(info["metric"])
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / path.name
        if dest.exists() or dest.is_symlink():
            dest.unlink()
        os.symlink(os.path.relpath(path, dest_dir), dest)
        rows.append(
            {
                "step": step,
                "step_label": STEP_LABELS.get(step, step),
                "model": info["model"],
                "figure_type": info["figure_type"],
                "metric": info["metric"],
                "passband": info["passband"],
                "component": info["component"],
                "value": info["value"],
                "source_path": str(path.relative_to(root)),
                "organized_path": str(dest.relative_to(root)),
                "description": FIGURE_TYPE_DESCRIPTIONS.get(info["figure_type"], "Generated scientific review figure."),
            }
        )

    moved_organized_paths = flatten_single_figure_dirs(organized, inventory_root=root)
    if moved_organized_paths:
        for row in rows:
            current = row["organized_path"]
            while current in moved_organized_paths:
                current = moved_organized_paths[current]
            row["organized_path"] = current

    with inventory_csv.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(rows[0].keys()) if rows else ["step"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    write_markdown_guide(root, guide, rows)
    return len(rows), organized, guide, inventory_csv


def write_markdown_guide(root: Path, guide: Path, rows: list[dict[str, str]]) -> None:
    """Write a human-readable figure guide."""

    by_step = Counter(row["step"] for row in rows)
    by_group = Counter((row["step"], row["model"], row["figure_type"]) for row in rows)
    lines = [
        "# Spatial-VTK Large-Run Figure Output Guide",
        "",
        f"Generated from current CARC outputs under `{root}`.",
        "",
        "## Review Entry Points",
        "",
        "- Canonical notebook outputs remain in `runs/outputs/figures/step_*` and `runs/outputs/figures/user_requested_*`.",
        "- Review-friendly symlinks are in `runs/outputs/figures/organized_review/<step>/<model>/<figure_type>/<metric>/`.",
        "- Machine-readable inventory is in `runs/outputs/figures/figure_inventory.csv`.",
        "",
        "## Step 1-6 Status",
        "",
        "| Step | Figure count | Notes |",
        "|---|---:|---|",
    ]
    for key in [
        "step_01",
        "step_02",
        "step_03_metrics",
        "step_04_spatial",
        "step_05_regions",
        "step_06_additional_diagnostics",
    ]:
        count = by_step.get(key, 0)
        note = STEP_LABELS.get(key, key)
        if key in {"step_01", "step_02"} and count == 0:
            note += "; no standalone PNG figure directory was produced by this step in the current workflow."
        lines.append(f"| `{key}` | {count} | {note} |")

    lines.extend(
        [
            "",
            "## Included User-Requested Spatial Outputs",
            "",
            "| Folder | Figure count | Description |",
            "|---|---:|---|",
        ]
    )
    for key in ["user_requested_la_basin_event_region_boxplots", "user_requested_region_type_boxplots"]:
        lines.append(f"| `{key}` | {by_step.get(key, 0)} | {STEP_LABELS.get(key, key)} included in the organized review tree. |")

    lines.extend(
        [
            "",
            "## Organized Review Tree Summary",
            "",
            "Counts below are grouped by step, model, and figure type. Use the organized path pattern to browse by scientific question rather than filename.",
            "",
        ]
    )
    for step in sorted(by_step):
        lines.extend(
            [
                f"### {STEP_LABELS.get(step, step)} (`{step}`)",
                "",
                "| Model/group | Figure type | Count | What it shows | Organized path |",
                "|---|---|---:|---|---|",
            ]
        )
        for _step, model, figure_type in sorted(key for key in by_group if key[0] == step):
            count = by_group[(_step, model, figure_type)]
            desc = FIGURE_TYPE_DESCRIPTIONS.get(figure_type, "Generated scientific review figure.")
            path_hint = f"organized_review/{slug(step)}/{slug(model)}/{slug(figure_type)}/"
            lines.append(f"| {model} | {figure_type} | {count} | {desc} | `{path_hint}` |")
        lines.append("")

    lines.extend(
        [
            "## Parameter Conventions",
            "",
            "Most filenames use `figure_type__metric__passband__component__model__value.png`. The inventory CSV exposes these fields directly as columns.",
            "",
            "- `model`: `CVM-S`, `CVM-H`, `CVM-S_vs_CVM-H_comparison`, or `shared_workflow` for non-model setup/review figures.",
            "- `passband`: period band such as `1-2-sec`, `2-3-sec`, `3-5-sec`, or `all-passbands`.",
            "- `value`: plotted quantity, including `log2-residual`, `field-centered`, `metric-comparison-value`, raw `value`, or delay-fraction diagnostics.",
            "- Step 5 corridor composites are grouped by region/corridor segment and include the corridor map plus available waveform panels.",
            "- Step 6 metric heatmaps use PGA, Arias duration, FAS, phase delay, and delay-corrected cross correlation; phase delay and delay-corrected cross correlation use raw values.",
        ]
    )
    guide.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--figures-root",
        type=Path,
        default=Path("runs/outputs/figures"),
        help="Large-run figures root to index.",
    )
    args = parser.parse_args()
    count, organized, guide, inventory = build_guide(args.figures_root)
    print(f"figures indexed: {count}")
    print(f"organized review: {organized}")
    print(f"guide: {guide}")
    print(f"inventory: {inventory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
