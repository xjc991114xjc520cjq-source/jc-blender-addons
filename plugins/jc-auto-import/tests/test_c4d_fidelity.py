"""C4D visibility/placement regressions using our own public-SDK fixture.

Build engine/tests/fixture.cpp outside the repo, then pass its generated .c4d.
The SDK and original applications are not needed to run this test.
"""
from pathlib import Path
import argparse, hashlib, json, subprocess, sys, tempfile

PLUGIN = Path(__file__).resolve().parents[1] / 'jc_auto_import'


def check_outputs(report):
    import bpy
    from mathutils import Vector
    sys.path.insert(0, str(PLUGIN.parent))
    from jc_auto_import.worker import import_model
    for target, output in report.items():
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        import_model(output)
        objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        names = {o.name for o in objects}
        assert len(objects) == 7, (target, names)
        assert sum(len(o.data.polygons) for o in objects) == 13, (target, names)
        assert not names & {'HiddenDirect', 'HiddenInherited', 'LayerHidden',
                            'AllFacesHidden', 'UnrelatedSibling'}, (target, names)
        assert {'VisibleOverride', 'VisibleRenderOff', 'PartiallyHidden', 'Transformed'} <= names
        same = [o for o in objects if o.name.startswith('SameName')]
        assert len(same) == 2, (target, names)
        centers = [sum((o.matrix_world @ v.co).x for v in o.data.vertices) / len(o.data.vertices) for o in same]
        assert abs(centers[0] - centers[1]) > .04
        partial = next(o for o in objects if o.name == 'PartiallyHidden')
        assert len(partial.data.polygons) == 1
        expected = {'Transformed': ((.25, .27, .04), (.31, .27, .08)),
                    'ReferenceBody': ((.50, .05, .03), (.52, .05, .05))}
        for name, bounds in expected.items():
            matches = [o for o in objects if name in o.name]
            assert len(matches) == 1, (target, name, names)
            obj = matches[0]
            points = [obj.matrix_world @ v.co for v in obj.data.vertices]
            actual = [tuple(fn(v[i] for v in points) for i in range(3)) for fn in (min, max)]
            assert max(abs(actual[b][i] - bounds[b][i]) for b in range(2) for i in range(3)) < 2e-6, (target, name, actual)
            assert obj.matrix_world.determinant() > 0
            # C4D +Z reflects to glTF -Z, which becomes Blender +Y.
            for face in obj.data.polygons:
                a, b, c = (obj.matrix_world @ obj.data.vertices[i].co for i in face.vertices[:3])
                assert (b - a).cross(c - a).normalized().dot(Vector((0, 1, 0))) > .99
        print('C4D_FIDELITY_PASS', target, '7 meshes / 13 faces', flush=True)


def main():
    if '--' in sys.argv and sys.argv[sys.argv.index('--') + 1] == 'check':
        check_outputs(json.loads(Path(sys.argv[-1]).read_text(encoding='utf-8')))
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', required=True)
    parser.add_argument('--fixture', required=True)
    args = parser.parse_args()
    source = Path(args.fixture).resolve(strict=True)
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='jc-c4d-fidelity-') as temporary:
        root = Path(temporary)
        report = {}
        for target in ('GLB', 'FBX', 'OBJ'):
            run = root / target
            run.mkdir()
            job = dict(source=str(source), target=target, cache=str(root / 'cache'), reuse=False, timeout=60)
            path = run / 'job.json'
            path.write_text(json.dumps(job), encoding='utf-8')
            with (run / 'worker.log').open('wb') as log:
                process = subprocess.run([args.blender, '--background', '--factory-startup', '--disable-autoexec',
                                          '--python-exit-code', '1', '--python', str(PLUGIN / 'worker.py'), '--', str(path)],
                                         stdout=log, stderr=log, timeout=90)
            result = json.loads((run / 'result.json').read_text(encoding='utf-8'))
            assert process.returncode == 0, result
            report[target] = result['output']
        path = root / 'outputs.json'
        path.write_text(json.dumps(report), encoding='utf-8')
        subprocess.run([args.blender, '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1',
                        '--python', str(Path(__file__).resolve()), '--', 'check', str(path)], check=True, timeout=90)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original


if __name__ == '__main__':
    main()
