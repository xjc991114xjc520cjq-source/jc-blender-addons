"""Native Keychain integration in a disposable CI-only keychain; fake key only."""
from pathlib import Path
import os
import shlex
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'macos/jc-blender-agent'))
from bridge import local_api


def security(*args):
    return subprocess.check_output(['/usr/bin/security', *args], text=True, timeout=20).strip()


if sys.platform != 'darwin' or not os.environ.get('CI'):
    raise RuntimeError('Run only in a disposable macOS CI environment')
previous_default = shlex.split(security('default-keychain', '-d', 'user'))[0]
previous_search = shlex.split(security('list-keychains', '-d', 'user'))
with tempfile.TemporaryDirectory(prefix='jc-test-keychain-') as temp:
    path = str(Path(temp) / 'jc-test.keychain-db')
    password = 'FAKE-CI-PASSWORD-' + uuid.uuid4().hex
    namespace = 'JCBlenderAgent/TEST/' + uuid.uuid4().hex + '/'
    endpoint = 'https://key-fixture.invalid/v1'
    value = 'FAKE-API-KEY-' + uuid.uuid4().hex
    security('create-keychain', '-p', password, path)
    try:
        security('unlock-keychain', '-p', password, path)
        security('set-keychain-settings', '-lut', '120', path)
        security('list-keychains', '-d', 'user', '-s', path)
        security('default-keychain', '-d', 'user', '-s', path)
        local_api.save_key(endpoint, value, namespace)
        assert local_api.read_key(endpoint, namespace) == value
        assert local_api.read_key('https://other-fixture.invalid/v1', namespace) == ''
        child = '''import sys
sys.path.insert(0,sys.argv[1])
from bridge.local_api import read_key
assert read_key(sys.argv[2],sys.argv[3])==sys.argv[4]
print('KEYCHAIN_FRESH_PROCESS_PASS')
'''
        subprocess.run([sys.executable, '-I', '-c', child, str(ROOT / 'macos/jc-blender-agent'),
                        endpoint, namespace, value], check=True, timeout=30)
        local_api.delete_key(endpoint, namespace)
        assert local_api.read_key(endpoint, namespace) == ''
        local_api.delete_key(endpoint, namespace)
        print('NATIVE_KEYCHAIN_SAVE_READ_ISOLATION_DELETE_PASS', flush=True)
    finally:
        security('default-keychain', '-d', 'user', '-s', previous_default)
        security('list-keychains', '-d', 'user', '-s', *previous_search)
        security('delete-keychain', path)
