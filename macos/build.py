"""Reproducible Mac packages. Standard library only; never includes Windows runtimes."""
from pathlib import Path
import ast
import hashlib
import json
import zipfile
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'packages/macos'
OUT.mkdir(parents=True, exist_ok=True)
FULL = '--full' in sys.argv
catalog = {'updated': '2026-11-19', 'platform': 'macos-arm64',
           'validation': 'Windows regression checks only; Mac hardware acceptance pending', 'plugins': []}


def package(pid, name, version, edition, files):
    records = {}
    archive = OUT / name
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for arcname, source in sorted(files.items()):
            content = source.read_bytes()
            if source.suffix == '.py':
                ast.parse(content.decode('utf-8-sig'), filename=str(source))
            assert source.suffix.lower() not in ('.exe', '.dll', '.pyd'), source
            info = zipfile.ZipInfo(arcname, date_time=(2026, 11, 19, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if source.stat().st_mode & 0o111 else 0o100644) << 16
            z.writestr(info, content)
            records[arcname] = source.relative_to(ROOT).as_posix()
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    catalog['plugins'].append({'id': pid, 'version': version, 'edition': edition,
        'package': archive.relative_to(ROOT).as_posix(), 'bytes': archive.stat().st_size,
        'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'sources': records})
    print(name)


base = ROOT / 'macos/jc-blender-agent'
files = {'jc_blender_agent/__init__.py': base / 'addon/jc_blender_agent/__init__.py',
         'jc_blender_agent/LICENSE': base / 'LICENSE', 'jc_blender_agent/README.md': ROOT / 'macos/README.md'}
for source in sorted((base / 'bridge').glob('*.py')):
    files['jc_blender_agent/runtime/bridge/' + source.name] = source
for source in sorted((base / 'bridge/knowledge').iterdir()):
    if source.suffix in ('.md', '.json', '.png'):
        files['jc_blender_agent/runtime/bridge/knowledge/' + source.name] = source
package('jc-blender-agent', 'JC-Blender-Agent-0.1.5-macOS-AppleSilicon-r1.zip', '0.1.5', 'macos.1', files)

base = ROOT / 'plugins/jc-history/src/jc_history'
files = {p.name: p for p in base.iterdir() if p.suffix in ('.py', '.toml', '.txt')}
files['macOS说明.md'] = ROOT / 'macos/README.md'
package('jc-history', 'JC-History-1.0.1-macOS-AppleSilicon-r1.zip', '1.0.1', 'macos.1', files)

base = ROOT / 'plugins/jc-view-navigator/jc_view_navigator'
files = {'jc_view_navigator/' + name: base / name for name in ('__init__.py', '使用说明.md', 'LICENSE.txt')}
files['jc_view_navigator/macOS说明.md'] = ROOT / 'macos/README.md'
package('jc-view-navigator', 'JC-View-Navigator-1.1.0-macOS-AppleSilicon-r1.zip', '1.1.0', 'macos.1', files)

base = ROOT / 'macos/jc-auto-import/jc_auto_import'
names = ['__init__.py', 'core.py', 'worker.py', 'three_ds.py', 'blender_manifest.toml',
         'capabilities.json', 'LICENSE.txt', 'THIRD_PARTY_NOTICES.md',
         'vendor/__init__.py', 'vendor/import_max.py', 'vendor/MAX_IMPORTER_LICENSE']
files = {name: base / name for name in names}
files['使用说明.md'] = ROOT / 'macos/README.md'
if not FULL:
    raise RuntimeError('Full Mac engines required. Build with python macos/build_full.py then python macos/build.py --full')
files['cad_worker.py'] = base / 'cad_worker.py'
runtime = base / 'bin/cad'
records = json.loads((runtime / 'runtime-files.json').read_text())['files']
for name, digest in records.items():
    path = runtime / name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
    files['bin/cad/' + name] = path
files['bin/cad/runtime-files.json'] = runtime / 'runtime-files.json'
for name in ('jc_converter', 'ASSIMP-LICENSE.txt', 'CINEWARE-LICENSE.txt'):
    files['bin/' + name] = base / 'bin' / name
package('jc-auto-import', 'JC-Auto-Import-1.0.4-macOS-AppleSilicon-r2.zip', '1.0.4', 'macos.2', files)
(OUT / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
(OUT / 'SHA256SUMS').write_text(''.join(p['sha256'] + '  ' + Path(p['package']).name + '\n'
                                        for p in catalog['plugins']), encoding='utf-8', newline='\n')
