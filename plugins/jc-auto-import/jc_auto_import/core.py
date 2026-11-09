"""Conversion planning and process control. Deliberately independent of bpy."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

VERSION = '1.0.0'
EXTERNAL_EXTENSIONS = ('.c4d', '.max', '.3ds', '.3d', '.dae', '.dxf', '.lwo', '.lws', '.lxo', '.ase', '.off', '.x', '.ac', '.ms3d', '.b3d', '.3mf', '.x3d', '.md2', '.md3', '.md5mesh', '.pmx', '.ifc', '.stp', '.step', '.wrl', '.vrml', '.skp', '.dwg', '.igs', '.iges', '.sat')
NATIVE_EXTENSIONS = ('.fbx', '.obj', '.glb', '.gltf', '.stl', '.ply', '.usd', '.usda', '.usdc', '.usdz', '.abc')
TARGETS = {'GLB': '.glb', 'FBX': '.fbx', 'OBJ': '.obj'}
ROOT = Path(__file__).resolve().parent


def external_extensions():
    path = ROOT / 'capabilities.json'
    extra = json.loads(path.read_text(encoding='utf-8'))['assimp_extensions'] if path.is_file() else []
    return tuple(sorted((set(EXTERNAL_EXTENSIONS) | set(extra)) - set(NATIVE_EXTENSIONS) - {'.blend'}))


def engines():
    return {'c4d': str(ROOT / 'bin/jc_converter.exe'),
            'assimp': str(ROOT / 'bin/jc_converter.exe')}


def backend_for(path):
    suffix = Path(path).suffix.lower()
    if suffix in NATIVE_EXTENSIONS:
        return 'native'
    if suffix == '.3ds':
        return '3ds'
    if suffix == '.c4d':
        return 'c4d'
    if suffix == '.max':
        return 'max'
    if suffix in external_extensions():
        return 'assimp'
    raise ValueError('Unsupported source format: ' + suffix)


def requirement(path):
    try:
        backend = backend_for(path)
    except ValueError:
        return '此版本没有该格式的独立读取器。'
    if os.name != 'nt':
        return '此版本仅打包 Windows x64 独立引擎。'
    if backend in ('c4d', 'assimp') and not Path(engines()[backend]).is_file():
        return '安装包中的独立转换引擎缺失，请重新安装完整 ZIP。'
    if backend == 'assimp':
        capabilities = json.loads((ROOT / 'capabilities.json').read_text(encoding='utf-8'))
        if Path(path).suffix.lower() not in capabilities['assimp_extensions']:
            return '内置引擎不支持此格式；本插件不会调用或要求安装原软件。'
    return ''


def fingerprint(source, target, blender_version):
    """Conservative cache: include all adjacent assets, up to 10000 files.

    Huge trees bypass reuse. The full source is hashed; sidecars use size/mtime.
    """
    source = Path(source).resolve()
    digest = hashlib.sha256()
    digest.update(json.dumps([VERSION, str(source), target, blender_version], sort_keys=True).encode())
    digest.update((ROOT / 'capabilities.json').read_bytes())
    with source.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    count = 0
    for parent, directories, files in os.walk(source.parent, followlinks=False):
        directories[:] = sorted(d for d in directories if d not in {'.git', '__pycache__'} and not Path(parent, d).is_symlink())
        for name in sorted(files):
            path = Path(parent, name)
            if path.is_symlink():
                continue
            count += 1
            if count > 10000:
                return hashlib.sha256(os.urandom(32)).hexdigest()
            stat = path.stat()
            digest.update(str((str(path.relative_to(source.parent)), stat.st_size, stat.st_mtime_ns)).encode())
    return digest.hexdigest()


def atomic_json(path, data):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def spawn(command, log_path, env=None, cwd=None):
    # No command shell, no terminal window, output goes to disk rather than a PIPE.
    with open(log_path, 'ab') as log:
        return subprocess.Popen(command, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                                env=env, cwd=cwd, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def stop_process(process):
    if process and process.poll() is None:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=15)
        else:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def run_external(command, timeout, log_path, cwd=None):
    process = spawn(command, log_path, cwd=cwd)
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        stop_process(process)
        raise RuntimeError('转换引擎超时，请检查源文件或增加超时。') from None
    if process.returncode:
        raise RuntimeError('转换引擎退出码 %s，详情见日志。' % process.returncode)
