"""Platform selection, credential routing and archive integrity regression tests."""
from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import hashlib
import os

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'macos/jc-blender-agent'))
from bridge import mac_platform, local_api, mac_keychain


def load_core():
    path = ROOT / 'macos/jc-auto-import/jc_auto_import/core.py'
    spec = importlib.util.spec_from_file_location('mac_auto_core', path)
    core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core)
    return core


class MacTests(unittest.TestCase):
    def test_full_formats_use_mac_engines_and_match_windows_declarations(self):
        core = load_core()
        with patch.object(core.os, 'name', 'posix'), \
             patch.object(Path, 'is_file', return_value=True), \
             patch.object(core.os, 'access', return_value=True):
            for suffix in core.NATIVE_EXTENSIONS + ('.max', '.3ds', '.c4d', '.stp', '.step', '.dae', '.dxf', '.lwo', '.3mf'):
                self.assertEqual(core.requirement('fixture' + suffix), '')
            for suffix in ('.dwg', '.skp', '.igs', '.sat'):
                self.assertTrue(core.requirement('fixture' + suffix), suffix)
        windows = json.loads((ROOT / 'plugins/jc-auto-import/jc_auto_import/capabilities.json').read_text())
        mac = json.loads((core.ROOT / 'capabilities.json').read_text())
        self.assertEqual(set(mac['assimp_extensions']), set(windows['assimp_extensions']))
        self.assertTrue(all('.exe' not in p for p in core.engines().values()))

    def test_keychain_routes_normalized_endpoint_without_plaintext_settings(self):
        with patch.object(local_api.sys, 'platform', 'darwin'), \
             patch.object(mac_keychain, 'save_key') as save, \
             patch.object(mac_keychain, 'read_key', return_value='fake') as read, \
             patch.object(mac_keychain, 'delete_key') as delete:
            base = 'https://EXAMPLE.invalid:443/v1/'
            local_api.save_key(base, 'FAKE_TEST_KEY', 'test/')
            self.assertEqual(local_api.read_key(base, 'test/'), 'fake')
            local_api.delete_key(base, 'test/')
            save.assert_called_once_with('https://example.invalid/v1', 'FAKE_TEST_KEY', 'test/')
            read.assert_called_once_with('https://example.invalid/v1', 'test/')
            delete.assert_called_once_with('https://example.invalid/v1', 'test/')
        with tempfile.TemporaryDirectory() as temp:
            local_api.save_settings(temp, {'api_key': 'FAKE_TEST_KEY', 'api_model': 'test'})
            self.assertNotIn('FAKE_TEST_KEY', (Path(temp) / local_api.SETTINGS).read_text())

    def test_python_finds_app_bundle_without_hardcoded_minor(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / 'Blender.app/Contents/MacOS/Blender'
            folder = binary.parent.parent / 'Resources/5.2/python/bin'
            folder.mkdir(parents=True)
            candidate = folder / 'python3.13'; candidate.touch()
            candidate = candidate.resolve()  # /var is a /private/var symlink on macOS.
            with patch.object(mac_platform, 'executable', side_effect=lambda p: p == candidate), \
                 patch.object(mac_platform.subprocess, 'run') as run:
                run.return_value.returncode = 0
                self.assertEqual(mac_platform.find_python(binary, (5, 2, 2)), str(candidate))

    def test_cli_finder_path_and_node_environment(self):
        expected = Path('/opt/homebrew/bin/codex')
        with patch.object(mac_platform.shutil, 'which', return_value=None), \
             patch.object(mac_platform, 'executable', side_effect=lambda p: p == expected):
            self.assertEqual(mac_platform.find_cli('codex'), str(expected))
        expected_prefix = str(Path('/opt/homebrew/bin/claude').parent) + os.pathsep
        self.assertTrue(mac_platform.cli_environment('/opt/homebrew/bin/claude')['PATH'].startswith(expected_prefix))

    def test_packages_match_sources_and_contain_no_windows_runtime(self):
        catalog = json.loads((ROOT / 'packages/macos/catalog.json').read_text(encoding='utf-8'))
        self.assertEqual(len(catalog['plugins']), 4)
        for item in catalog['plugins']:
            archive = ROOT / item['package']
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), item['sha256'])
            with zipfile.ZipFile(archive) as z:
                self.assertIsNone(z.testzip())
                for name in z.namelist():
                    self.assertNotIn('..', Path(name).parts)
                    self.assertNotIn(Path(name).suffix.lower(), ('.exe', '.dll', '.pyd'))
                    if 'files_sha256' in item:
                        self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(), item['files_sha256'][name])
                    if name in item['sources']:
                        self.assertEqual(z.read(name), (ROOT / item['sources'][name]).read_bytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)
