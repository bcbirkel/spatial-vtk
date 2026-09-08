"""Create labeled contact sheets for reviewing generated tutorial figure layouts."""
import argparse
import json
import hashlib
from pathlib import Path
from PIL import Image, ImageDraw

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--figures', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--execution-manifest', type=Path, required=True, help='Successful imagery-required execution manifest for the figures.')
args = parser.parse_args()
execution = json.loads(args.execution_manifest.read_text())
if not execution.get('visual_review_eligible') or not execution.get('basemaps_required') or not execution.get('steps') or any(s.get('status') != 'passed' for s in execution['steps']):
    parser.error('Final contact sheets require a successful imagery-required run; computation-only outputs are not eligible.')
audit = Path(execution['basemap_audit'])
events = [json.loads(line) for line in audit.read_text().splitlines() if line]
if not events or not all(event['success'] for event in events):
    parser.error('Basemap audit is missing successful imagery or records a failure.')
args.output.mkdir(parents=True, exist_ok=True)
files = sorted(args.figures.glob('*.png'))
for path in files:
    if execution.get('figure_sha256', {}).get(str(path.resolve())) != hashlib.sha256(path.read_bytes()).hexdigest():
        parser.error(f'Figure does not match the validated execution: {path}')
manifest = []
for start in range(0, len(files), 9):
    sheet = Image.new('RGB', (1800, 1800), 'white')
    draw = ImageDraw.Draw(sheet)
    for i, path in enumerate(files[start:start+9]):
        with Image.open(path) as original:
            manifest.append({'file': str(path), 'pixels': original.size})
            thumbnail = original.convert('RGB')
            thumbnail.thumbnail((590, 560))
        x, y = (i % 3) * 600, (i // 3) * 600
        draw.text((x+4, y+4), path.name, fill='black')
        sheet.paste(thumbnail, (x, y+30))
    sheet.save(args.output / f'contact_{start//9+1}.png')
(args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(f'{len(files)} figures, {(len(files)+8)//9} contact sheets')
