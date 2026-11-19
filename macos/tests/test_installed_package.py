"""Verify the actual ZIP after relocation and normal zipfile extraction on a Mac.

Uses original generated C4D/STEP/OFF fixtures and pinned upstream test models,
never user models. All inputs are hashed before/after conversion.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = {
    'SourceFiles/RotatingCube.max': 'bdc6170e0c76a2b362102e21816d175a86cfc6f251f065223c83717baa4040c4',
    'Collada/box_nested_animation.dae': '669b797dd5784e4e5dcd9ae9067e0b2f06161a813f8a08b6a7ed78d0d8d1534f',
    'DXF/PinkEggFromLW.dxf': '65734e4d5772274f1f3bf419fc1238565495ab9e7974edf801fd561c24469d39',
    'LWO/LWO2/boxuv.lwo': 'a2e2f7aba857df5c88bf0116a0189eb0acac451cd7e72740cb82c16a9c6f184b',
    '3MF/box.3mf': 'de20508dff06f8faf8ca992c00238d4affc916ba4b812e8ff9ec1571fec533a1',
}


def run(command, **kwargs):
    subprocess.run(list(map(str, command)), check=True, timeout=180, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--blender', required=True)
    parser.add_argument('--fixture', required=True)
    parser.add_argument('--archive', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='jc-installed-') as temp:
        root = Path(temp)
        extracted = root / '安装 路径'; extracted.mkdir()
        plugin = extracted / 'jc_auto_import'; plugin.mkdir()
        with zipfile.ZipFile(args.archive) as z:
            z.extractall(plugin)
        spec = importlib.util.spec_from_file_location('installed_core', plugin / 'core.py')
        core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core)
        # Normal zipfile extraction does not retain Unix executable bits.
        assert not core.requirement('fixture.step')
        assert not core.requirement('fixture.c4d')
        sources = root / '中文 素材'; sources.mkdir()
        samples = []
        for name, digest in SAMPLES.items():
            target = sources / Path(name).name
            url = 'https://raw.githubusercontent.com/assimp/assimp/392a658f9c271be965271f45e7521a1b80ea4392/test/models/' + name
            urllib.request.urlretrieve(url, target)
            assert hashlib.sha256(target.read_bytes()).hexdigest() == digest, name
            samples.append(target)
        c4d = sources / '场景.c4d'; shutil.copy2(args.fixture, c4d); samples.append(c4d)
        off = sources / '三角.off'; off.write_text('OFF\n3 1 0\n0 0 0\n1 0 0\n0 1 0\n3 0 1 2\n'); samples.append(off)
        fixture = extracted / 'engine/tests/step_fixture.py'; fixture.parent.mkdir(parents=True)
        shutil.copy2(ROOT / 'macos/jc-auto-import/engine/tests/step_fixture.py', fixture)
        run([core.engines()['cad'], fixture, sources])
        samples.append(sources / '中文 STEP 测试/带孔零件 装配.stp')
        outputs = []
        for source in samples:
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            for target in ('GLB', 'FBX', 'OBJ'):
                work = root / ('run-' + str(len(outputs))); work.mkdir()
                job = work / 'job.json'
                job.write_text(json.dumps(dict(source=str(source), target=target, cache=str(root / 'cache'), reuse=False, timeout=120)))
                with (work / 'console.log').open('wb') as log:
                    try:
                        run([args.blender, '--background', '--factory-startup', '--disable-autoexec',
                             '--python-exit-code', '1', '--python', plugin / 'worker.py', '--', job], stdout=log, stderr=log)
                    except subprocess.CalledProcessError:
                        print((work / 'console.log').read_text(errors='replace'))
                        raise
                result = json.loads((work / 'result.json').read_text())
                assert 'error' not in result, result
                outputs.append(result['output'])
                print('INSTALLED_CONVERSION_PASS', source.suffix, target, flush=True)
            assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
        report = root / 'outputs.json'; report.write_text(json.dumps(outputs))
        check = root / 'check.py'
        check.write_text('''from pathlib import Path
import sys,json,bpy
sys.path.insert(0,sys.argv[sys.argv.index('--')+1])
from jc_auto_import.worker import import_model
for output in json.loads(Path(sys.argv[-1]).read_text()):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    import_model(output)
    assert any(o.type=='MESH' and len(o.data.polygons)>0 for o in bpy.context.scene.objects),output
print('INSTALLED_REIMPORT_PASS',flush=True)
''')
        run([args.blender, '--background', '--factory-startup', '--disable-autoexec',
             '--python-exit-code', '1', '--python', check, '--', extracted, report])
        print('INSTALLED_PACKAGE_PASS: 8 inputs / 24 conversions / 24 reimports / original files unchanged', flush=True)


if __name__ == '__main__':
    main()
