"""Archive a completed natural-log tutorial run with durable provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--execution-root", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
source = args.execution_root.resolve()
dest = root / "outputs/native_ln_residual_review"
dest.mkdir(parents=True, exist_ok=True)
manifest = json.loads((source / "outputs/tutorial_execution/manifest.json").read_text())
assert len(manifest["steps"]) == 7 and all(s["status"] == "passed" for s in manifest["steps"])
for name in ["figures", "tables"]:
    shutil.copytree(source / "outputs/tutorials" / name, dest / name, dirs_exist_ok=True)
shutil.copytree(source / "outputs/tutorial_execution", dest / "execution", dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("jupyter"))
manifest["basemap_audit"] = str(dest / "execution/basemaps.jsonl")
manifest["figure_sha256"] = {str(dest / "figures" / Path(p).name): h for p, h in manifest["figure_sha256"].items()}
manifest["residual_convention"] = "ln(observed / synthetic) calculated directly in Step 3 from waveform metric values; all metric figures load that output."
manifest["builders"] = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
    for folder, pattern in [("src", "*.py"), ("tools", "*.py"), ("docs/examples", "*.ipynb")]
    for p in sorted((root / folder).rglob(pattern))}
(dest / "execution/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
subprocess.run([sys.executable, str(root / "tools/tutorial_figure_contact_sheets.py"),
    "--figures", str(dest / "figures"), "--output", str(dest / "contacts"),
    "--execution-manifest", str(dest / "execution/manifest.json")], check=True)
(dest / "README.md").write_text("""# Natural-log residual review

The default is ln(observed / synthetic). All seven tutorials were executed with
required Esri imagery. Newly calculated residuals satisfy the natural-log ratio
identity; all metric figures use the native Step 3 results, without log2 snapshot conversion.
Explicit log2 transforms remain supported.

- [Residual scatter](figures/step_06_metric_scatterplot.png)
- [Regional boxplot](figures/step_06_metric_boxplot.png)
- [Residual trends](figures/residuals_vs_distance.png)
- [Execution, input and builder hashes](execution/manifest.json)
- [Numerical validation](execution/validation.json)
- [Figure contact sheets](contacts/)

LOWESS curves carry no global slope or correlation label. Regional percentage
effects use 100*(exp(effect)-1) for natural-log residuals.
""")
print(dest)
