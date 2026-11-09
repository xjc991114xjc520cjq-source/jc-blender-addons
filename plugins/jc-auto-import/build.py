"""Build the extension ZIP from an explicit file allowlist, excluding test/user data."""
from pathlib import Path
import ast, hashlib, json, zipfile
ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'jc_auto_import'
FILES = ['__init__.py', 'core.py', 'worker.py', 'three_ds.py', 'blender_manifest.toml',
         'capabilities.json', '使用说明.md', 'LICENSE.txt', 'THIRD_PARTY_NOTICES.md',
         'vendor/__init__.py', 'vendor/import_max.py', 'vendor/MAX_IMPORTER_LICENSE',
         'bin/jc_converter.exe', 'bin/ASSIMP-LICENSE.txt', 'bin/CINEWARE-LICENSE.txt']
capabilities=json.loads((SOURCE/'capabilities.json').read_text(encoding='utf-8'))
capabilities['engine_sha256']=hashlib.sha256((SOURCE/'bin/jc_converter.exe').read_bytes()).hexdigest()
capabilities['max_reader_sha256']=hashlib.sha256((SOURCE/'vendor/import_max.py').read_bytes()).hexdigest()
(SOURCE/'capabilities.json').write_text(json.dumps(capabilities,indent=2)+'\n',encoding='utf-8')
for name in FILES:
    path = SOURCE / name
    if path.suffix == '.py':
        ast.parse(path.read_text(encoding='utf-8-sig'), filename=name)
    if not path.is_file():
        raise FileNotFoundError(path)
dist = ROOT / 'dist'; dist.mkdir(exist_ok=True)
archive = dist / 'JC-Auto-Import-1.0.0-Windows.zip'
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
    for name in FILES:
        info = zipfile.ZipInfo(name, date_time=(2026, 11, 9, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (0o755 if name.endswith('.exe') else 0o644) << 16
        out.writestr(info, (SOURCE / name).read_bytes())
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
(dist / (archive.name + '.sha256')).write_text(digest + '  ' + archive.name + '\n', encoding='ascii')
print(json.dumps({'archive': str(archive), 'sha256': digest, 'bytes': archive.stat().st_size}))
