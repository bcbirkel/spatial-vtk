"""Prepare documentation with validated outputs, without editing source notebooks."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--execution-root", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
execution = args.execution_root.resolve() / "outputs/tutorial_execution"
manifest = json.loads((execution / "manifest.json").read_text())
assert manifest["visual_review_eligible"] and manifest["basemaps_required"]
steps = manifest["steps"]
assert len(steps) == 7 and all(s["status"] == "passed" for s in steps)
for step in steps:
    source = root / step["notebook"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == step["sha256"], source
    assert (execution / source.name).is_file()
preview = root / "outputs/documentation_preview"
preview.mkdir(parents=True, exist_ok=True)
shutil.copytree(root / "docs", preview / "docs", dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("_build", "__pycache__"))
shutil.copy2(root / "ValidationToolkit_Workflow.png", preview / "ValidationToolkit_Workflow.png")
if not (preview / "data").exists():
    (preview / "data").symlink_to(root / "data", target_is_directory=True)
for step in steps:
    shutil.copy2(execution / Path(step["notebook"]).name, preview / step["notebook"])
shutil.copy2(execution / "manifest.json", preview / "execution_manifest.json")
print(preview / "docs")
