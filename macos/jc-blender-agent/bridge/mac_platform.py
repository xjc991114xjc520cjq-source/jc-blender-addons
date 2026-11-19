"""macOS paths without depending on the GUI application's inherited PATH."""
import os
from pathlib import Path
import shutil
import subprocess


def executable(path):
    return path.is_file() and os.access(path, os.X_OK)


def find_cli(kind):
    if kind not in ('codex', 'claude'):
        return ''
    home = Path.home()
    candidates = [home / '.local/bin' / kind, Path('/opt/homebrew/bin') / kind,
                  Path('/usr/local/bin') / kind, home / '.npm-global/bin' / kind]
    candidates += sorted((home / '.nvm/versions/node').glob('*/bin/' + kind),
                         key=lambda p: p.stat().st_mtime, reverse=True)
    # The desktop application's bundled CLI is a fallback, not a requirement.
    if kind == 'codex':
        candidates.append(Path('/Applications/Codex.app/Contents/Resources/codex'))
    found = shutil.which(kind)
    if found:
        candidates.insert(0, Path(found))
    return next((str(p) for p in candidates if executable(p)), '')


def find_python(blender_binary, version):
    root = Path(blender_binary).resolve().parent
    bundled = root.parent / 'Resources' / f'{version[0]}.{version[1]}' / 'python/bin'
    candidates = sorted(bundled.glob('python3*'))
    candidates += [Path('/opt/homebrew/bin/python3'), Path('/usr/local/bin/python3')]
    for name in ('python3', 'python'):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    for path in candidates:
        if not executable(path):
            continue
        try:
            result = subprocess.run([str(path), '-I', '-c',
                'import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)'],
                capture_output=True, timeout=8)
            if result.returncode == 0:
                return str(path)
        except (OSError, subprocess.TimeoutExpired):
            continue
    raise RuntimeError('找不到 Python 3.10+；请在插件偏好设置指定可执行文件')


def cli_environment(executable_path):
    env = os.environ.copy()
    # npm entry points use /usr/bin/env node. GUI PATH may omit Node's directory.
    paths = [str(Path(executable_path).parent), str(Path.home() / '.local/bin'),
             '/opt/homebrew/bin', '/usr/local/bin', env.get('PATH', '/usr/bin:/bin')]
    env['PATH'] = os.pathsep.join(paths)
    return env
