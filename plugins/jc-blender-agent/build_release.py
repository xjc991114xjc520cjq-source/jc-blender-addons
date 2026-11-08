"""Build a self-contained Blender addon ZIP with an explicit source allowlist."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parent
VERSION='0.1.5'
DIST=ROOT/'dist';DIST.mkdir(exist_ok=True)
addon=DIST/f'JC-Blender-Agent-{VERSION}.zip'
with zipfile.ZipFile(addon,'w',zipfile.ZIP_DEFLATED) as z:
    z.write(ROOT/'addon/jc_blender_agent/__init__.py','jc_blender_agent/__init__.py')
    for path in sorted((ROOT/'bridge').glob('*.py')):
        z.write(path,'jc_blender_agent/runtime/bridge/'+path.name)
    for path in sorted((ROOT/'bridge/knowledge').iterdir()):
        if path.suffix not in ('.md','.json','.png'):continue
        z.write(path,'jc_blender_agent/runtime/bridge/knowledge/'+path.name)
    z.write(ROOT/'LICENSE','jc_blender_agent/LICENSE')
    z.write(ROOT/'README.md','jc_blender_agent/README.md')

source=DIST/f'JC-Blender-Agent-{VERSION}-source.zip'
with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED) as z:
    files=[ROOT/'README.md',ROOT/'LICENSE',ROOT/'build_release.py']
    for directory in ('bridge','addon','tests','docs'):
        files += [p for p in (ROOT/directory).rglob('*') if p.is_file() and (p.suffix in ('.py','.md','.toml') or (p.parent == ROOT/'bridge/knowledge' and p.suffix in ('.json','.png'))) and '__pycache__' not in p.parts]
    for path in sorted(set(files)):
        z.write(path,'JC-Blender-Agent/'+path.relative_to(ROOT).as_posix())

manifest={'version':VERSION,'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (addon,source)],
    'runtime_dependencies':'Python standard library only; Blender builtin bpy',
    'excluded':['API keys','login state','local service tokens','video files','test runtime directories','Python analysis/test dependencies']}
(DIST/'release-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
