"""Run post-metric sanity QC and compare against an existing QC inventory."""

from __future__ import annotations

import argparse
from io import StringIO
from pathlib import Path

import pandas as pd

from spatial_vtk.qc.build import (
    G_CM_PER_S2,
    G_M_PER_S2,
    MetricResidualLimit,
    MetricSanityQCSettings,
    MetricValueLimit,
    SpatialResidualOutlierSettings,
    apply_metric_sanity_rejections_to_qc_inventory,
    build_event_station_pair_retention_table,
    build_metric_pair_retention_table,
    build_metric_sanity_rejection_table,
    summarize_metric_sanity_removals,
)


def _read_table(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.suffix.lower() in {".parquet", ".pq"} else pd.read_csv(path, low_memory=False)


def _write_table(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in {".parquet", ".pq"}:
        df.to_parquet(path, index=False)
    else:
        df.to_csv(path, index=False)
    return path


def _pair_table(qc: pd.DataFrame) -> pd.DataFrame:
    key_columns = ["event_id", "station", "component", "passband", "metric_group", "metric", "period_s"]
    observed = qc.loc[qc["source"].astype(str).str.lower().eq("observed"), key_columns + ["qc_status", "qc_reason"]].copy()
    synthetic = qc.loc[qc["source"].astype(str).str.lower().eq("synthetic"), key_columns + ["qc_status", "qc_reason"]].copy()
    pairs = observed.merge(synthetic, on=key_columns, how="inner", suffixes=("_observed", "_synthetic"))
    pairs["is_retained_pair"] = (
        pairs["qc_status_observed"].astype(str).str.lower().eq("pass")
        & pairs["qc_status_synthetic"].astype(str).str.lower().eq("pass")
    )
    return pairs


def _removed_pairs(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    keys = ["event_id", "station", "component", "passband", "metric_group", "metric", "period_s"]
    before_pairs = _pair_table(before)
    after_pairs = _pair_table(after)
    merged = before_pairs[keys + ["is_retained_pair"]].merge(
        after_pairs[keys + ["is_retained_pair", "qc_reason_observed", "qc_reason_synthetic"]],
        on=keys,
        how="inner",
        suffixes=("_before", "_after"),
    )
    removed = merged.loc[merged["is_retained_pair_before"] & ~merged["is_retained_pair_after"]].copy()
    if removed.empty:
        return pd.DataFrame(columns=[*keys, "qc_reason_observed", "qc_reason_synthetic"])
    return removed.sort_values(["metric", "event_id", "station", "component", "passband"], kind="stable").reset_index(drop=True)


def _write_markdown_report(
    output_dir: Path,
    *,
    rejections: pd.DataFrame,
    removed_pairs: pd.DataFrame,
    row_summary: pd.DataFrame,
    pair_retention_before: pd.DataFrame,
    pair_retention_after: pd.DataFrame,
    args: argparse.Namespace,
) -> Path:
    unit_scale = {"cm/s2": G_CM_PER_S2, "m/s2": G_M_PER_S2, "g": 1.0}[args.pga_value_unit]
    threshold = args.pga_max_g * unit_scale
    lines = [
        "# Metric Sanity QC Rerun",
        "",
        "## Configuration",
        "",
        f"- PGA hard threshold: {args.pga_max_g:g} g = {threshold:g} {args.pga_value_unit}",
        f"- Absolute residual threshold: |{args.residual_column}| > {args.residual_max_abs:g}",
        (
            "- Spatial residual threshold: "
            f"radius={args.spatial_radius_km:g} km, min_neighbors={args.spatial_min_neighbors}, "
            f"robust_z>={args.spatial_z_threshold:g}, "
            f"min_abs_difference>={args.spatial_min_abs_difference:g}"
        ),
        "",
        "## Removal Summary",
        "",
        f"- Rejection rows emitted: {len(rejections):,}",
        f"- Comparison pairs newly removed from the overlap QC set: {len(removed_pairs):,}",
        "",
        "### Newly failed QC rows by reason/source/metric/passband",
        "",
        _markdown_table(row_summary) if not row_summary.empty else "No newly failed QC rows.",
        "",
        "### Pair retention before",
        "",
        _markdown_table(pair_retention_before) if not pair_retention_before.empty else "No pair-retention rows.",
        "",
        "### Pair retention after",
        "",
        _markdown_table(pair_retention_after) if not pair_retention_after.empty else "No pair-retention rows.",
        "",
        "### Top removed comparison pairs",
        "",
        (
            _markdown_table(removed_pairs.head(50))
            if not removed_pairs.empty
            else "No comparison pairs were newly removed."
        ),
        "",
    ]
    path = output_dir / "metric_sanity_qc_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _markdown_table(df: pd.DataFrame) -> str:
    """Render a compact Markdown table without pandas' optional tabulate dependency."""

    if df.empty:
        return ""
    text = df.copy()
    for column in text.columns:
        text[column] = text[column].map(lambda value: "" if pd.isna(value) else str(value))
    rows = [list(text.columns), ["---"] * len(text.columns)]
    rows.extend(text.astype(str).values.tolist())
    widths = [max(len(row[idx]) for row in rows) for idx in range(len(rows[0]))]
    output = StringIO()
    for row_idx, row in enumerate(rows):
        output.write("| ")
        output.write(" | ".join(value.ljust(widths[idx]) for idx, value in enumerate(row)))
        output.write(" |\n")
        if row_idx == 1:
            continue
    return output.getvalue().rstrip()


def run(args: argparse.Namespace) -> dict[str, Path]:
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    unit_scale = {"cm/s2": G_CM_PER_S2, "m/s2": G_M_PER_S2, "g": 1.0}[args.pga_value_unit]
    pga_limit = MetricValueLimit(
        metric="PGA",
        max_abs=float(args.pga_max_g) * unit_scale,
        sources=("observed", "synthetic"),
        reason="pga_above_1g",
    )
    settings = MetricSanityQCSettings(
        value_limits=(pga_limit,),
        residual_limit=MetricResidualLimit(
            column=args.residual_column,
            max_abs=float(args.residual_max_abs),
            reason="log2_residual_extreme",
        ),
        spatial_residual=SpatialResidualOutlierSettings(
            enabled=not args.disable_spatial,
            column=args.residual_column,
            radius_km=float(args.spatial_radius_km),
            min_neighbors=int(args.spatial_min_neighbors),
            z_threshold=float(args.spatial_z_threshold),
            min_abs_difference=float(args.spatial_min_abs_difference),
            mad_floor=float(args.spatial_mad_floor),
            reason="spatial_neighbor_residual_outlier",
        ),
    )
    rejections = build_metric_sanity_rejection_table(args.metrics_long, settings=settings)
    paths: dict[str, Path] = {}
    paths["rejections"] = _write_table(rejections, output_dir / "metric_sanity_rejections.csv")
    if args.qc_inventory:
        qc_inventory_out = output_dir / "qc_inventory_metric_sanity.csv"
        paths["qc_inventory"] = apply_metric_sanity_rejections_to_qc_inventory(args.qc_inventory, rejections, qc_inventory_out)

    overlap_before = _read_table(Path(args.qc_inventory_overlap))
    overlap_after = apply_metric_sanity_rejections_to_qc_inventory(overlap_before, rejections)
    overlap_out = output_dir / "qc_inventory_overlap_metric_sanity.parquet"
    paths["qc_inventory_overlap"] = _write_table(overlap_after, overlap_out)

    row_summary = summarize_metric_sanity_removals(overlap_before, overlap_after)
    paths["row_summary"] = _write_table(row_summary, output_dir / "metric_sanity_new_failures_summary.csv")

    removed_pairs = _removed_pairs(overlap_before, overlap_after)
    paths["removed_pairs"] = _write_table(removed_pairs, output_dir / "metric_sanity_removed_pairs.csv")

    before_retention = build_metric_pair_retention_table(overlap_before)
    after_retention = build_metric_pair_retention_table(overlap_after)
    event_station_after = build_event_station_pair_retention_table(overlap_after)
    paths["pair_retention_before"] = _write_table(before_retention, output_dir / "qc_metric_pair_retention_before.csv")
    paths["pair_retention_after"] = _write_table(after_retention, output_dir / "qc_metric_pair_retention_after.csv")
    paths["event_station_retention_after"] = _write_table(event_station_after, output_dir / "qc_event_station_pair_retention_after.csv")
    paths["report"] = _write_markdown_report(
        output_dir,
        rejections=rejections,
        removed_pairs=removed_pairs,
        row_summary=row_summary,
        pair_retention_before=before_retention,
        pair_retention_after=after_retention,
        args=args,
    )
    manifest = pd.DataFrame([{"artifact": key, "path": str(path)} for key, path in paths.items()])
    paths["manifest"] = _write_table(manifest, output_dir / "manifest.csv")
    return paths


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-long", required=True, help="metrics_long table with values and residuals.")
    parser.add_argument("--qc-inventory", default=None, help="Optional current full qc_inventory table. Large runs can omit this.")
    parser.add_argument("--qc-inventory-overlap", required=True, help="Current overlap qc_inventory table.")
    parser.add_argument("--output-dir", required=True, help="Directory for sanity-QC rerun outputs.")
    parser.add_argument("--pga-max-g", type=float, default=1.0, help="Strict PGA max in g.")
    parser.add_argument("--pga-value-unit", choices=["cm/s2", "m/s2", "g"], default="cm/s2", help="Metric-table acceleration unit.")
    parser.add_argument("--residual-column", default="log2_residual")
    parser.add_argument("--residual-max-abs", type=float, default=8.0)
    parser.add_argument("--disable-spatial", action="store_true")
    parser.add_argument("--spatial-radius-km", type=float, default=10.0)
    parser.add_argument("--spatial-min-neighbors", type=int, default=3)
    parser.add_argument("--spatial-z-threshold", type=float, default=8.0)
    parser.add_argument("--spatial-min-abs-difference", type=float, default=4.0)
    parser.add_argument("--spatial-mad-floor", type=float, default=0.25)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    paths = run(args)
    for key, path in paths.items():
        print(f"{key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
