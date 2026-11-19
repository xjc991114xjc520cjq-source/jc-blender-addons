"""Shared Blender conversion regression, usable on Windows and Apple Silicon.

Run at repository root: python macos/tests/test_blender.py --blender <binary>
"""
from pathlib import Path
import argparse
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('conversion_tests', ROOT / 'plugins/jc-auto-import/tests/test_conversion.py')
tests = importlib.util.module_from_spec(spec); spec.loader.exec_module(tests)
tests.PLUGIN = ROOT / 'macos/jc-auto-import/jc_auto_import'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--blender', required=True)
    args = parser.parse_args()
    tests.BLENDER = args.blender
    names = ['test_static_parser_geometry_uv_material', 'test_corrupt_chunk_rejected',
             'test_cache_changes_with_adjacent_texture', 'test_cancel_stops_owned_process',
             'test_three_formats_cache_and_original_unchanged',
             'test_failure_never_marks_complete_or_leaves_partial']
    suite = unittest.TestSuite(tests.ConversionTests(name) for name in names)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
