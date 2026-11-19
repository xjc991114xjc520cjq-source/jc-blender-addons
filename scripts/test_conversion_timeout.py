"""Exercise both platforms' timeout policy with real subprocesses and a controlled clock."""
from pathlib import Path
import importlib.util
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for relative in ('plugins/jc-auto-import', 'macos/jc-auto-import'):
    spec = importlib.util.spec_from_file_location('timeout_core', ROOT / relative / 'jc_auto_import/core.py')
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    old = SimpleNamespace(timeout=300, limit_conversion_time=False)
    assert core.conversion_timeout(old) == 0
    assert core.make_deadline(core.conversion_timeout(old)) is None
    old.limit_conversion_time = True
    assert core.conversion_timeout(old) == 300
    assert core.conversion_timeout(None) == 0
    for invalid in (-1, float('inf'), float('nan')):
        try:
            core.make_deadline(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(invalid)
    with patch.object(core.time, 'monotonic', return_value=100):
        deadline = core.make_deadline(300)
    with patch.object(core.time, 'monotonic', return_value=390):
        assert core.remaining_timeout(deadline) == 10
    with patch.object(core.time, 'monotonic', return_value=401):
        try:
            core.remaining_timeout(deadline)
        except core.ConversionError:
            pass
        else:
            raise AssertionError('Expired budget reset')
    # Simulate conversion far beyond the old 330-second cutoff, without waiting.
    with patch.object(core.time, 'monotonic', return_value=100000):
        assert core.remaining_timeout(None) is None
    with tempfile.TemporaryDirectory() as temp:
        log = Path(temp) / 'engine.log'
        marker = Path(temp) / 'finished'
        command = [sys.executable, '-c', 'import time; from pathlib import Path; time.sleep(.3); Path(%r).write_text("done")' % str(marker)]
        core.run_external(command, 0, log)
        assert marker.read_text() == 'done'
        marker.unlink()
        try:
            core.run_external(command, .05, log)
        except core.ConversionError as error:
            assert '手动设置' in str(error)
        else:
            raise AssertionError('Explicit limit did not terminate child')
        time.sleep(.35)
        assert not marker.exists()
    print('PASS timeout policy, legacy settings, shared deadline and child termination:', relative)
