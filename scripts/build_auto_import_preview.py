"""Rebuild the experimental installer from this repository's verified sources."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if sys.platform != 'win32':
    raise SystemExit('Build this Windows experimental package on Windows for a reproducible ZIP hash.')
entry = next(item for item in json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))['plugins']
             if item['id'] == 'jc-auto-import')
if entry.get('channel') != 'experimental':
    raise SystemExit('This build command is intended for the experimental source branch.')
subprocess.run([sys.executable, str(ROOT / 'plugins/jc-auto-import/build.py')], check=True)
source = ROOT / 'plugins/jc-auto-import/dist' / entry['archive']
digest = hashlib.sha256(source.read_bytes()).hexdigest()
if digest != entry['sha256'] or source.stat().st_size != entry['bytes']:
    raise SystemExit('Rebuilt ZIP differs from the tested artifact; do not publish it as the verified package.')
destination = ROOT / entry['package']
shutil.copy2(source, destination)
subprocess.run([sys.executable, str(ROOT / 'scripts/verify_packages.py')], check=True)
print('Verified experimental installer:', destination)
print('SHA-256:', digest)
