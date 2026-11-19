"""Build native arm64 converters on a macOS host. No SDK files are redistributed."""
from pathlib import Path
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AUTO = ROOT / 'macos/jc-auto-import/jc_auto_import'
TEMP = Path(os.environ.get('RUNNER_TEMP', ROOT / 'work')) / 'jc-native-build'
TEMP.mkdir(parents=True, exist_ok=True)
DOWNLOADS = [
    ('Cineware_22_008.zip', 'https://developers.maxon.net/downloads/Cineware_22_008.zip',
     '44f3372322161f7062c3f664181758d7e2938929f2257717c54f61d6ff1f3c2b'),
    ('python.tar.gz', 'https://github.com/astral-sh/python-build-standalone/releases/download/20261110/cpython-3.13.18%2B20261110-aarch64-apple-darwin-install_only_stripped.tar.gz',
     '7a2384641584ab9984221fcb0fc9265df465922af71be71410529e2a9c3f0540'),
    ('cadquery_ocp_novtk-7.9.3.1.1-cp313-cp313-macosx_11_0_arm64.whl', 'https://files.pythonhosted.org/packages/f7/80/dc46dac2ebb6ae6bcce27bc7f717438b99897199be25323cda559a76e0a1/cadquery_ocp_novtk-7.9.3.1.1-cp313-cp313-macosx_11_0_arm64.whl',
     '2287812f213af7020f8bbc69b07d6039e529f5e0e154c0192221aff3fdac6676'),
    ('cadquery_ocp_proxy-7.9.3.1.1-py3-none-any.whl', 'https://files.pythonhosted.org/packages/30/c0/04e9363a99fee892de2776820e3dcf04f8825b6edc9580efe3416c9465a7/cadquery_ocp_proxy-7.9.3.1.1-py3-none-any.whl',
     'ca4164ec4b54956d9fc3e68c67d555b5486cb963c2f71e18df005ba16b921c91'),
]


def run(*args, **kwargs):
    print('RUN', *map(str, args), flush=True)
    subprocess.run(list(map(str, args)), check=True, **kwargs)


if sys.platform != 'darwin' or platform.machine() != 'arm64':
    raise RuntimeError('Build on native macOS arm64')
for name, url, digest in DOWNLOADS:
    path = TEMP / name
    if not path.is_file():
        print('Downloading', name, flush=True)
        run('curl', '--fail', '--location', '--retry', '3', '--user-agent',
            'Mozilla/5.0 (compatible; JC-Blender-Build)', url, '--output', path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError('Download hash mismatch: ' + name)

sdk = TEMP / 'sdk'
sdk.mkdir(exist_ok=True)
with zipfile.ZipFile(TEMP / 'Cineware_22_008.zip') as z:
    # Only headers, static libraries and license are needed, never SDK examples.
    for name in z.namelist():
        if name.startswith(('includes/', 'libraries/osx/')) and '._' not in name or name == 'EULA.txt':
            z.extract(name, sdk)
run('lipo', '-archs', sdk / 'libraries/osx/release/libcinewarelib.a')
assimp = TEMP / 'assimp'
if not assimp.exists():
    run('git', 'clone', '--depth', '1', '--branch', 'v6.0.5', 'https://github.com/assimp/assimp.git', assimp)
assert subprocess.check_output(['git', '-C', str(assimp), 'rev-parse', 'HEAD'], text=True).strip() == '392a658f9c271be965271f45e7521a1b80ea4392'
patch = ROOT / 'plugins/jc-auto-import/engine/assimp-jc.patch'
run('git', '-C', assimp, 'apply', '--check', patch)
run('git', '-C', assimp, 'apply', patch)
shutil.copytree(sdk / 'includes', assimp / 'contrib/Cineware/includes', dirs_exist_ok=True)
shutil.copytree(sdk / 'libraries/osx', assimp / 'contrib/Cineware/libraries/osx', dirs_exist_ok=True)
cpp = assimp / 'code/AssetLib/C4D/C4DImporter.cpp'
t = cpp.read_text()
t = t.replace('defined(__amd64__)', 'defined(__amd64__) || defined(__aarch64__) || defined(__arm64__)')
t = t.replace('#define __PC', '#ifdef __APPLE__\n#define __MAC\n#else\n#define __PC\n#endif')
cpp.write_text(t)
build = TEMP / 'assimp-build'
run('cmake', '-S', assimp, '-B', build, '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_OSX_ARCHITECTURES=arm64',
    '-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0', '-DASSIMP_BUILD_TESTS=OFF', '-DASSIMP_BUILD_ASSIMP_TOOLS=ON',
    '-DASSIMP_BUILD_SAMPLES=OFF', '-DBUILD_SHARED_LIBS=OFF', '-DASSIMP_BUILD_ZLIB=OFF', '-DASSIMP_INSTALL=OFF',
    '-DCMAKE_EXE_LINKER_FLAGS=-framework AppKit -framework CoreFoundation -framework CoreAudio -framework CoreServices -framework Carbon -framework IOKit',
    '-DASSIMP_BUILD_ALL_IMPORTERS_BY_DEFAULT=ON', '-DASSIMP_BUILD_NONFREE_C4D_IMPORTER=ON',
    '-DASSIMP_BUILD_ALL_EXPORTERS_BY_DEFAULT=OFF', '-DASSIMP_BUILD_GLTF_EXPORTER=ON',
    '-DASSIMP_BUILD_OBJ_EXPORTER=ON', '-DASSIMP_BUILD_ASSBIN_EXPORTER=ON', '-DASSIMP_BUILD_ASSXML_EXPORTER=ON',
    '-DASSIMP_WARNINGS_AS_ERRORS=OFF')
run('cmake', '--build', build, '--parallel', '3')
bin_dir = AUTO / 'bin'; bin_dir.mkdir(exist_ok=True)
shutil.copy2(build / 'bin/assimp', bin_dir / 'jc_converter')
shutil.copy2(assimp / 'LICENSE', bin_dir / 'ASSIMP-LICENSE.txt')
shutil.copy2(sdk / 'EULA.txt', bin_dir / 'CINEWARE-LICENSE.txt')
run('file', bin_dir / 'jc_converter')
run(bin_dir / 'jc_converter', 'listext')

cad = bin_dir / 'cad'; cad.mkdir(exist_ok=True)
with tarfile.open(TEMP / 'python.tar.gz') as t:
    t.extractall(cad, filter='data')
packages = cad / 'packages'; packages.mkdir(exist_ok=True)
for name, _, _ in DOWNLOADS:
    if name.endswith('.whl'):
        with zipfile.ZipFile(TEMP / name) as z:
            z.extractall(packages)
python = cad / 'python/bin/python3.13'
env = os.environ.copy(); env['PYTHONPATH'] = str(packages)
run(python, '-c', 'import OCP;from OCP.STEPControl import STEPControl_Reader;print("NATIVE_ARM64_OCP_PASS")', env=env)
notice = '''Independent macOS arm64 STEP runtime. CPython 3.13.18 from python-build-standalone,
CadQuery OCP novtk/proxy 7.9.3.1.1 and Open CASCADE 7.9.3. Included upstream licenses
remain in the Python tree and wheel dist-info directories. Dynamic libraries remain
replaceable under their licenses. No Windows runtime or Rosetta is used.
Sources: https://github.com/astral-sh/python-build-standalone
https://github.com/CadQuery/OCP https://github.com/CadQuery/ocp-build-system
https://github.com/Open-Cascade-SAS/OCCT/tree/V7_9_3
'''
(cad / 'NOTICE.md').write_text(notice)
(cad / 'downloads.json').write_text(json.dumps([{'name': n, 'url': u, 'sha256': d} for n, u, d in DOWNLOADS if n != 'Cineware_22_008.zip'], indent=2))
records = {p.relative_to(cad).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted(cad.rglob('*')) if p.is_file() and p.name != 'runtime-files.json' and '__pycache__' not in p.parts}
(cad / 'runtime-files.json').write_text(json.dumps({'files': records}, indent=2))
cap = json.loads((ROOT / 'plugins/jc-auto-import/jc_auto_import/capabilities.json').read_text())
cap.update(platform='macos-arm64', edition='macos.2',
           engine_sha256=hashlib.sha256((bin_dir / 'jc_converter').read_bytes()).hexdigest(),
           cad_runtime_sha256=hashlib.sha256((cad / 'runtime-files.json').read_bytes()).hexdigest())
(AUTO / 'capabilities.json').write_text(json.dumps(cap, indent=2) + '\n')

# Original, generated C4D fixture; SDK examples are neither built nor published.
fixture = TEMP / 'fixture'
run('clang++', '-std=c++17', '-arch', 'arm64', '-D__MAC', '-D__C4D_64BIT',
    '-I' + str(sdk / 'includes'), ROOT / 'plugins/jc-auto-import/engine/tests/fixture.cpp',
    sdk / 'libraries/osx/release/libcinewarelib.a', sdk / 'libraries/osx/release/libjpeglib.a',
    '-framework', 'AppKit', '-framework', 'CoreFoundation', '-framework', 'CoreAudio',
    '-framework', 'CoreServices', '-framework', 'Carbon', '-framework', 'IOKit', '-o', fixture)
run(fixture, TEMP / 'visibility.c4d')
print('NATIVE_ENGINES_BUILT', flush=True)
