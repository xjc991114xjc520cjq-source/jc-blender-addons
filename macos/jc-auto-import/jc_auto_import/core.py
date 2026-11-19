"""Conversion planning and process control. Deliberately independent of bpy."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time
import math
import signal

VERSION = '1.0.5-macos.3'
EXTERNAL_EXTENSIONS = ('.c4d', '.max', '.3ds', '.3d', '.dae', '.dxf', '.lwo', '.lws', '.lxo', '.ase', '.off', '.x', '.ac', '.ms3d', '.b3d', '.3mf', '.x3d', '.md2', '.md3', '.md5mesh', '.pmx', '.ifc', '.stp', '.step', '.wrl', '.vrml', '.skp', '.dwg', '.igs', '.iges', '.sat')
NATIVE_EXTENSIONS = ('.fbx', '.obj', '.glb', '.gltf', '.stl', '.ply', '.usd', '.usda', '.usdc', '.usdz', '.abc')
TARGETS = {'GLB': '.glb', 'FBX': '.fbx', 'OBJ': '.obj'}
ROOT = Path(__file__).resolve().parent


def external_extensions():
    path = ROOT / 'capabilities.json'
    extra = json.loads(path.read_text(encoding='utf-8'))['assimp_extensions'] if path.is_file() else []
    return tuple(sorted((set(EXTERNAL_EXTENSIONS) | set(extra)) - set(NATIVE_EXTENSIONS) - {'.blend'}))


def engines():
    return {'c4d': str(ROOT / 'bin/jc_converter'),
            'cad': str(ROOT / 'bin/cad/python/bin/python3.13'),
            'assimp': str(ROOT / 'bin/jc_converter')}


def backend_for(path):
    suffix = Path(path).suffix.lower()
    if suffix in NATIVE_EXTENSIONS:
        return 'native'
    if suffix in ('.stp', '.step'):
        return 'cad'
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
    for executable in engines().values():
        p = Path(executable)
        if p.is_file() and not os.access(p, os.X_OK):
            p.chmod(p.stat().st_mode | 0o700)

    if backend in ('c4d', 'assimp') and not Path(engines()[backend]).is_file():
        return '安装包中的独立转换引擎缺失，请重新安装完整 ZIP。'
    if backend == 'cad' and not all((ROOT / name).is_file() for name in (
            'bin/cad/runtime-files.json', 'bin/cad/python/bin/python3.13', 'cad_worker.py',
            'bin/cad/packages/OCP/__init__.py')):
        return '安装包中的 STEP 曲面转换组件缺失，请安装完整版本。'
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


def spawn(command, log_path, env=None, cwd=None, new_session=False):
    # No command shell, no terminal window, output goes to disk rather than a PIPE.
    with open(log_path, 'ab') as log:
        return subprocess.Popen(command, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                                env=env, cwd=cwd, start_new_session=new_session and os.name != 'nt', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def stop_process(process):
    if process and process.poll() is None:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=15)
        else:
            # The background Blender owns a session; its engines inherit it.
            if os.getpgid(process.pid) == process.pid:
                os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            if os.name != 'nt' and os.getpgid(process.pid) == process.pid:
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()


class ConversionError(RuntimeError):
    def __init__(self, message, returncode=None):
        super().__init__(message)
        self.returncode = returncode


def conversion_timeout(preferences):
    # The new opt-in switch deliberately ignores old saved 300-second values.
    return preferences.timeout if preferences and preferences.limit_conversion_time else 0


def make_deadline(timeout):
    timeout = float(timeout or 0)
    if not math.isfinite(timeout) or timeout < 0:
        raise ValueError('转换时限必须为非负有限秒数')
    return time.monotonic() + timeout if timeout else None


def remaining_timeout(deadline):
    if deadline is None:
        return None
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ConversionError('已达到手动设置的单文件总时限。')
    return remaining


def run_external(command, timeout, log_path, cwd=None):
    log_path = Path(log_path)
    offset = log_path.stat().st_size if log_path.is_file() else 0
    process = spawn(command, log_path, cwd=cwd)
    try:
        process.wait(timeout=timeout or None)
    except subprocess.TimeoutExpired:
        stop_process(process)
        raise ConversionError('已达到手动设置的单文件总时限。') from None
    if process.returncode:
        with log_path.open('rb') as stream:
            stream.seek(max(offset, log_path.stat().st_size - 65536))
            lines = stream.read().decode('utf-8', 'replace').splitlines()
        errors = [line.strip() for line in lines if line.startswith(('ERROR:', 'Error,'))]
        detail = errors[-1][:500] if errors else '引擎没有提供具体原因，请查看转换日志。'
        if process.returncode == 10:
            message = '无法读取源模型（代码 10）：' + detail
        elif process.returncode == 11:
            message = '无法写出转换结果（代码 11）：' + detail
        else:
            message = '转换引擎异常退出（代码 %s）：%s' % (process.returncode, detail)
        raise ConversionError(message, process.returncode)
