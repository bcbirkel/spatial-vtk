"""Execute the large-run workflow notebooks and save execution logs."""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path

import nbformat
from nbclient import NotebookClient


DEFAULT_NOTEBOOKS = (
    "step_01_large_run_ingest_and_prepare_data.ipynb",
    "step_02_large_run_quality_control.ipynb",
    "step_03_large_run_calculate_metrics.ipynb",
    "step_04_large_run_spatial_statistics.ipynb",
    "step_05_large_run_geojson_corridors.ipynb",
    "step_06_large_run_additional_plotting.ipynb",
)


def _output_text(cell: nbformat.NotebookNode) -> str:
    """Return compact text from one executed code cell."""

    chunks: list[str] = []
    for output in cell.get("outputs", []):
        output_type = output.get("output_type")
        if output_type == "stream":
            chunks.append(str(output.get("text", "")))
        elif output_type in {"execute_result", "display_data"}:
            data = output.get("data", {})
            text = data.get("text/plain")
            if text:
                chunks.append(str(text))
        elif output_type == "error":
            chunks.append("\n".join(output.get("traceback", [])))
    return "".join(chunks).strip()


def _write_execution_log(path: Path, notebook: nbformat.NotebookNode, *, status: str, elapsed_s: float) -> None:
    """Write a plain-text execution log for one notebook."""

    lines = [f"status: {status}", f"elapsed_s: {elapsed_s:.1f}", ""]
    for index, cell in enumerate(notebook.get("cells", []), start=1):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", [])).strip()
        text = _output_text(cell)
        lines.append(f"## cell {index}")
        lines.append("source:")
        lines.append(source)
        if text:
            lines.append("output:")
            lines.append(text)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def execute_notebook(
    notebook_path: Path,
    *,
    repo_root: Path,
    output_dir: Path,
    log_dir: Path,
    timeout: int,
    kernel_name: str,
) -> bool:
    """Execute one notebook and write an executed copy plus text log."""

    start = time.monotonic()
    print(f"START {notebook_path}", flush=True)
    notebook = nbformat.read(notebook_path, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=timeout,
        kernel_name=kernel_name,
        resources={"metadata": {"path": str(repo_root)}},
        allow_errors=False,
    )
    status = "completed"
    try:
        client.execute()
    except Exception:
        status = "failed"
        traceback.print_exc()
    elapsed_s = time.monotonic() - start
    output_path = output_dir / f"{notebook_path.stem}.executed.ipynb"
    log_path = log_dir / f"{notebook_path.stem}.log"
    nbformat.write(notebook, output_path)
    _write_execution_log(log_path, notebook, status=status, elapsed_s=elapsed_s)
    print(f"END {notebook_path} status={status} elapsed_s={elapsed_s:.1f}", flush=True)
    print(f"executed_notebook={output_path}", flush=True)
    print(f"log={log_path}", flush=True)
    return status == "completed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--notebook-dir", type=Path, default=Path("runs/large_run"))
    parser.add_argument("--output-dir", type=Path, default=Path("runs/outputs/notebook_runs"))
    parser.add_argument("--log-dir", type=Path, default=Path("logs/notebook_runs"))
    parser.add_argument("--timeout", type=int, default=-1)
    parser.add_argument("--kernel-name", default="python3")
    parser.add_argument("--notebook", action="append", default=None, help="Notebook filename to execute; repeat to limit/order.")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    notebook_dir = (repo_root / args.notebook_dir).resolve() if not args.notebook_dir.is_absolute() else args.notebook_dir
    output_dir = (repo_root / args.output_dir).resolve() if not args.output_dir.is_absolute() else args.output_dir
    log_dir = (repo_root / args.log_dir).resolve() if not args.log_dir.is_absolute() else args.log_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    names = tuple(args.notebook) if args.notebook else DEFAULT_NOTEBOOKS
    ok = True
    for name in names:
        notebook_path = notebook_dir / name
        if not notebook_path.exists():
            print(f"MISSING {notebook_path}", file=sys.stderr, flush=True)
            ok = False
            continue
        ok = execute_notebook(
            notebook_path,
            repo_root=repo_root,
            output_dir=output_dir,
            log_dir=log_dir,
            timeout=args.timeout,
            kernel_name=args.kernel_name,
        ) and ok
        if not ok:
            break
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
