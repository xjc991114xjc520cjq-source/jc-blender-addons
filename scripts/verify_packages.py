"""Offline archive integrity and source correspondence checks; no Blender execution."""
from pathlib import Path, PurePosixPath
import ast, hashlib, json, zipfile

ROOT=Path(__file__).resolve().parents[1]
catalog=json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))
for plugin in catalog['plugins']:
    package=ROOT/plugin['package']
    assert package.stat().st_size==plugin['bytes'], package.name
    assert hashlib.sha256(package.read_bytes()).hexdigest()==plugin['sha256'], package.name
    source=ROOT/plugin['source']
    with zipfile.ZipFile(package) as archive:
        assert archive.testzip() is None
        for info in archive.infolist():
            path=PurePosixPath(info.filename)
            assert not path.is_absolute() and '..' not in path.parts
            assert '__pycache__' not in path.parts
            if plugin['id']=='jc-blender-agent':
                relative=path.relative_to('jc_blender_agent')
                if relative.parts[:2]==('runtime','bridge'):
                    original=source/'bridge'/Path(*relative.parts[2:])
                elif relative.name=='__init__.py':
                    original=source/'addon/jc_blender_agent/__init__.py'
                else:
                    original=source/Path(*relative.parts)
            elif plugin['id']=='jc-history':
                original=source/'src/jc_history'/info.filename
            elif plugin['id']=='jc-auto-import':
                original=source/'jc_auto_import'/info.filename
            else:
                original=source/info.filename
            assert original.read_bytes()==archive.read(info), str(original)
    for script in source.rglob('*.py'):
        ast.parse(script.read_text(encoding='utf-8-sig'),filename=str(script))
    print(f"PASS {plugin['id']} {plugin['version']}")
print('All packages match the archived final source.')
