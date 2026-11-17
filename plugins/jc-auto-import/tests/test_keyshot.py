"""Synthetic data only: parser boundaries, representations and model selection."""
from pathlib import Path
import ctypes
import importlib.util
import json
import struct
import tempfile
import unittest
import zipfile

SOURCE = Path(__file__).resolve().parents[1] / 'jc_auto_import'
spec = importlib.util.spec_from_file_location('keyshot', SOURCE / 'keyshot.py')
keyshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(keyshot)


def rec(op, payload=b''):
    return bytes([op | 1]) + bytes([len(payload)]) + payload if len(payload) < 256 else bytes([op & 254]) + struct.pack('<I', len(payload)) + payload


def prop(name, value):
    encoded = value.encode()
    return rec(0x2e, struct.pack('<I', len(encoded)) + encoded + name.encode())


def numbers(name, fmt, values):
    name = name.encode()
    return struct.pack('<I', len(name)) + name + struct.pack('<' + fmt * len(values), *values)


def instance(ident, ref):
    return rec(0x4a, b'same name') + rec(0x38, struct.pack('<I', ident)) + rec(0x5a, b'instance') + rec(0x1c, struct.pack('<I', ref) + b'id') + rec(0x5c) + rec(0x4e)


def fixture():
    geometry = (rec(0x4c, b'mesh') + rec(0x38, struct.pack('<I', 1)) + rec(0x5a, b'triangles') +
                rec(0x74, numbers('vertices', 'f', [0, 0, 0, 10, 0, 0, 0, 10, 0])) +
                rec(0x7e, numbers('triangles', 'i', [0, 1, 2])) + rec(0x5c) + rec(0x4e) +
                rec(0x4c, b'CAD') + rec(0x38, struct.pack('<I', 2)) + rec(0x5a, b'nurbs') + rec(0x5c) + rec(0x4e))
    active = (rec(0x54, b'A') + prop('model set', 'A') + instance(11, 1) + instance(12, 1) + instance(13, 2) +
              rec(0x54, b'suppressed source') + rec(0x3a, struct.pack('<I', keyshot.SUPPRESSED_GEOMETRY)) + instance(14, 2) + rec(0x58) + rec(0x58))
    other = rec(0x54, b'B') + prop('model set', 'B') + instance(15, 2) + rec(0x58)
    body = rec(0x6a, b'scene-command-is-data-only.so') + prop('active_scene_set', 'A') + rec(0x16, struct.pack('<f', 1000.) + b'meter_scale') + geometry + active + other
    return b'//---luxion:dal:024---\n' + b'\x00' * 32 + rec(0x86, struct.pack('<QQ', len(body), 0x40000)) + body + rec(0x88)


class KeyShotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / '样例.bip'
        self.path.write_bytes(fixture())

    def test_model_sets_and_duplicate_named_instances(self):
        scene = keyshot.parse(self.path)
        roots, chosen = keyshot.select_roots(scene)
        self.assertEqual(chosen, 'A')
        self.assertEqual(keyshot.mesh_plan(scene, roots), (2, 1))
        self.assertEqual([x['id'] for x in roots[0]['children'][:2]], [11, 12])
        self.assertEqual(len(scene['roots']), 2)

    def test_nurbs_without_saved_mesh_fails(self):
        scene = keyshot.parse(self.path)
        roots, _ = keyshot.select_roots(scene, 'B')
        with self.assertRaisesRegex(keyshot.KeyShotError, 'NURBS'):
            keyshot.mesh_plan(scene, roots)

    def test_missing_reference_fails(self):
        scene = keyshot.parse(self.path)
        del scene['definitions'][1]
        with self.assertRaisesRegex(keyshot.KeyShotError, '引用缺失'):
            keyshot.mesh_plan(scene, keyshot.select_roots(scene)[0])

    def test_missing_model_set_fails(self):
        with self.assertRaisesRegex(keyshot.KeyShotError, '唯一确定'):
            keyshot.select_roots(keyshot.parse(self.path), 'absent')

    def test_truncated_segment_fails(self):
        self.path.write_bytes(fixture()[:-1])
        with self.assertRaises(keyshot.KeyShotError):
            keyshot.parse(self.path)

    def test_unknown_dal_version_fails(self):
        self.path.write_bytes(fixture().replace(b':024---', b':999---'))
        with self.assertRaisesRegex(keyshot.KeyShotError, 'DAL 999'):
            keyshot.parse(self.path)

    def test_mesh_index_range_fails(self):
        scene = keyshot.parse(self.path)
        scene['definitions'][1]['arrays']['triangles'][2] = 99
        with self.assertRaisesRegex(keyshot.KeyShotError, '顶点索引越界'):
            keyshot.mesh_plan(scene, keyshot.select_roots(scene)[0])

    def test_uv_index_range_fails(self):
        scene = keyshot.parse(self.path)
        scene['definitions'][1]['arrays']['uv_tex'] = [0., 0.]
        with self.assertRaisesRegex(keyshot.KeyShotError, 'UV 索引越界'):
            keyshot.mesh_plan(scene, keyshot.select_roots(scene)[0])

    def test_valid_ksp_reads_without_extracting_assets(self):
        path = self.path.with_suffix('.ksp')
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('scene/scene.bip', fixture())
            archive.writestr('textures/image.png', b'asset')
        scene = keyshot.parse(path)
        self.assertEqual(keyshot.mesh_plan(scene, keyshot.select_roots(scene)[0]), (2, 1))
        self.assertFalse((path.parent / 'textures').exists())

    def test_ksp_traversal_fails(self):
        path = self.path.with_suffix('.ksp')
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('../outside.txt', b'asset')
            archive.writestr('scene.bip', fixture())
        with self.assertRaisesRegex(keyshot.KeyShotError, '越界路径'):
            keyshot.parse(path)

    def test_ksp_ambiguous_scene_fails(self):
        path = self.path.with_suffix('.ksp')
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('a.bip', fixture())
            archive.writestr('b.bip', fixture())
        with self.assertRaisesRegex(keyshot.KeyShotError, '恰好'):
            keyshot.parse(path)

    def test_zstd_stream_bounded_and_truncated(self):
        dll = next((SOURCE / 'bin/cad/packages/cadquery_ocp_novtk.libs').glob('zstd-*.dll'))
        library = ctypes.CDLL(str(dll))
        library.ZSTD_compress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
        library.ZSTD_compress.restype = ctypes.c_size_t
        raw = b'bounded data' * 10000
        source = ctypes.create_string_buffer(raw)
        target = ctypes.create_string_buffer(len(raw) * 2)
        length = library.ZSTD_compress(target, len(target), source, len(raw), 1)
        frame = target.raw[:length]
        self.assertEqual(keyshot.decompress(frame, len(raw)), raw)
        with self.assertRaisesRegex(keyshot.KeyShotError, '限制'):
            keyshot.decompress(frame, len(raw) - 1)
        with self.assertRaises(keyshot.KeyShotError):
            keyshot.decompress(frame[:-1], len(raw))

    def test_color_graph_and_environment_id_scope(self):
        body = (rec(0x9c) + rec(0x38, struct.pack('<I', 77)) + rec(0x28, struct.pack('<4f', .1, .2, .3, 1) + b'color') + rec(0x9e) +
                rec(0x06, struct.pack('<I', 1) + b'lux_const_color_extended') + rec(0xa0, struct.pack('<I', 77) + b'color') + rec(0x08) +
                rec(0x06, struct.pack('<I', 2) + b'lux_composite') + rec(0x7e, numbers('shaders', 'i', [1])) + rec(0x08) +
                rec(0x06, struct.pack('<I', 1) + b'lux_envmap') + rec(0x08))
        self.path.write_bytes(fixture() + body)
        scene = keyshot.parse(self.path)
        self.assertEqual(scene['shaders'][1]['type'], 'lux_const_color_extended')
        result = keyshot.basic_color(scene, {'shader': 2})
        for actual, expected in zip(result, (.1, .2, .3, 1.)):
            self.assertAlmostEqual(actual, expected, places=6)

    def test_color_graph_cycle_has_bounded_fallback(self):
        scene = {'shaders': {1: {'props': {'shader': ('shader', 2)}}, 2: {'props': {'shader': ('shader', 1)}}}, 'colors': {}}
        self.assertEqual(keyshot.basic_color(scene, {'shader': 1}), (.65, .65, .65, 1.))

    def test_model_set_is_part_of_cache_key_and_format_routing(self):
        spec = importlib.util.spec_from_file_location('keyshot_test_core', SOURCE / 'core.py')
        core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(core)
        self.assertEqual(core.backend_for('scene.BIP'), 'keyshot')
        self.assertEqual(core.backend_for('scene.KSP'), 'keyshot')
        a = core.fingerprint(self.path, 'GLB', 'test', {'keyshot_model_set': 'A'})
        b = core.fingerprint(self.path, 'GLB', 'test', {'keyshot_model_set': 'B'})
        self.assertNotEqual(a, b)


if __name__ == '__main__':
    unittest.main()
