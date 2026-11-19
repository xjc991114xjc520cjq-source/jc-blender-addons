"""Run existing credential and CLI prompt regressions against the Mac source tree."""
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'macos/jc-blender-agent'))
# Import Mac modules first, before the original tests insert their own source path.
from bridge import agents, local_api


if __name__ == '__main__':
    suite = unittest.TestSuite()
    for name in ('test_local_api', 'test_render_guidance'):
        spec = importlib.util.spec_from_file_location(name, ROOT / 'plugins/jc-blender-agent/tests' / (name + '.py'))
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        if name == 'test_render_guidance':
            suite.addTest(module.RenderGuidanceTests('test_both_cli_adapters_respect_switch'))
        else:
            suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
