"""Portable integration tests. Run: python tests/test_conversion.py --blender /path/to/blender.

Fixtures are generated here. No original application or downloaded models are needed.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, struct, subprocess, tempfile, time, unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'jc_auto_import'
BLENDER = None


def module(name):
    spec = importlib.util.spec_from_file_location(name, PLUGIN / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def chunk(kind, data):
    return struct.pack('<HI', kind, len(data) + 6) + data


def make_3ds(path):
    vertices = chunk(0x4110, struct.pack('<H9f', 3, 0, 0, 0, 1, 0, 0, 0, 1, 0))
    groups = chunk(0x4130, b'Red\0' + struct.pack('<HH', 1, 0))
    faces = chunk(0x4120, struct.pack('<H4H', 1, 0, 1, 2, 0) + groups)
    uv = chunk(0x4140, struct.pack('<H6f', 3, 0, 0, 1, 0, 0, 1))
    material = chunk(0xAFFF, chunk(0xA000, b'Red\0') + chunk(0xA020, chunk(0x0011, bytes((255, 0, 0)))))
    mesh = chunk(0x4000, b'Triangle\0' + chunk(0x4100, vertices + faces + uv))
    path.write_bytes(chunk(0x4D4D, chunk(0x3D3D, material + mesh)))


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='jc-conversion-test-')
        self.root = Path(self.tmp.name)
        self.sources = self.root / 'models'; self.sources.mkdir()
        self.source = self.sources / '中文 模型.3ds'
        make_3ds(self.source)
        self.core = module('core')

    def tearDown(self):
        self.tmp.cleanup()

    def run_worker(self, target='GLB', source=None, reuse=True):
        run = self.root / ('run-' + str(time.time_ns())); run.mkdir()
        job = dict(source=str(source or self.source), target=target, cache=str(self.root / 'cache'), timeout=60, reuse=reuse)
        (run / 'job.json').write_text(json.dumps(job), encoding='utf-8')
        with (run / 'console.log').open('w', encoding='utf-8') as log:
            process = subprocess.run([BLENDER, '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1',
                                      '--python', str(PLUGIN / 'worker.py'), '--', str(run / 'job.json')], stdout=log, stderr=log, timeout=90)
        self.assertTrue((run / 'result.json').is_file(), (run / 'console.log').read_text(encoding='utf-8'))
        return process.returncode, json.loads((run / 'result.json').read_text(encoding='utf-8'))

    def test_static_parser_geometry_uv_material(self):
        data = module('three_ds').Reader(self.source).parse()
        self.assertEqual(len(data.objects[0]['vertices']), 3)
        self.assertEqual(data.objects[0]['faces'], [(0, 1, 2)])
        self.assertEqual(len(data.objects[0]['uv']), 3)
        self.assertEqual(data.materials['Red']['color'], (1, 0, 0))

    def test_corrupt_chunk_rejected(self):
        self.source.write_bytes(b'\x4d\x4d\xff\xff\xff\xff')
        with self.assertRaises(ValueError):
            module('three_ds').Reader(self.source).parse()

    def test_dependency_free_routing(self):
        self.assertEqual(self.core.backend_for('file.max'), 'max')
        self.assertEqual(self.core.backend_for('file.c4d'), 'c4d')
        self.assertEqual(self.core.backend_for('file.3ds'), '3ds')
        self.assertEqual(self.core.backend_for('file.dae'), 'assimp')
        self.assertEqual(self.core.backend_for('file.obj'), 'native')
        self.assertTrue(self.core.requirement('file.dwg'))
        self.assertFalse(self.core.requirement('file.max'))
        self.assertFalse(self.core.requirement('file.c4d'))

    def test_cache_changes_with_adjacent_texture(self):
        first = self.core.fingerprint(self.source, 'GLB', 'test')
        (self.sources / 'texture.png').write_bytes(b'texture')
        self.assertNotEqual(first, self.core.fingerprint(self.source, 'GLB', 'test'))

    def test_cancel_stops_owned_process(self):
        process = self.core.spawn([BLENDER, '--background', '--factory-startup', '--python-expr', 'import time;time.sleep(30)'], self.root / 'cancel.log')
        self.core.stop_process(process)
        self.assertIsNotNone(process.poll())

    def test_three_formats_cache_and_original_unchanged(self):
        original = hashlib.sha256(self.source.read_bytes()).hexdigest()
        for target in ('GLB', 'FBX', 'OBJ'):
            with self.subTest(target=target):
                code, result = self.run_worker(target)
                self.assertEqual(code, 0, result)
                self.assertTrue(Path(result['output']).is_file())
                self.assertGreater(Path(result['output']).stat().st_size, 0)
                code, cached = self.run_worker(target)
                self.assertEqual(code, 0, cached)
                self.assertTrue(cached['cached'])
                self.assertEqual(cached['output'], result['output'])
        self.assertEqual(original, hashlib.sha256(self.source.read_bytes()).hexdigest())

    def test_failure_never_marks_complete_or_leaves_partial(self):
        self.source.write_bytes(b'not a model')
        code, result = self.run_worker()
        self.assertNotEqual(code, 0)
        self.assertIn('error', result)
        self.assertFalse(list((self.root / 'cache').glob('*.partial')))
        self.assertFalse(list((self.root / 'cache').glob('*/manifest.json')))

    def test_engine_unicode_input_output_and_working_directory(self):
        folder=self.sources/'中文路径 空格 😀'; folder.mkdir()
        source=folder/'三角 模型.off'
        source.write_text('OFF\n3 1 0\n0 0 0\n1 0 0\n0 1 0\n3 0 1 2\n',encoding='utf-8')
        output=folder/'导出 结果.glb'
        process=subprocess.run([self.core.engines()['assimp'],'export',str(source),str(output),'-fglb2','-l'],
                               cwd=folder,capture_output=True,timeout=30)
        self.assertEqual(process.returncode,0,process.stdout.decode('utf-8','replace')+process.stderr.decode('utf-8','replace'))
        self.assertTrue(output.is_file())
        self.assertEqual(output.read_bytes()[:4],b'glTF')

    def test_error_10_reports_actual_cause(self):
        source=self.sources/'损坏模型.off'
        source.write_bytes(b'not a valid OFF model')
        log=self.root/'engine.log'
        with self.assertRaises(self.core.ConversionError) as caught:
            self.core.run_external([self.core.engines()['assimp'],'export',str(source),str(self.root/'bad.glb'),'-fglb2','-l'],30,log)
        self.assertEqual(caught.exception.returncode,10)
        self.assertIn('无法读取源模型',str(caught.exception))
        self.assertIn('ERROR:',str(caught.exception))
        self.assertNotIn('没有提供具体原因',str(caught.exception))

    def test_unreadable_input_is_not_retried_with_obj(self):
        source=self.sources/'损坏.off'; source.write_bytes(b'invalid')
        code,result=self.run_worker(source=source)
        self.assertNotEqual(code,0)
        self.assertIn('代码 10',result['error'])
        run=max(self.root.glob('run-*'),key=lambda p:p.stat().st_mtime_ns)
        self.assertEqual((run/'engine.log').read_text(encoding='utf-8',errors='replace').count('select file format:'),1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--blender', required=True)
    args, rest = parser.parse_known_args()
    BLENDER = args.blender
    unittest.main(argv=[__file__, *rest])
