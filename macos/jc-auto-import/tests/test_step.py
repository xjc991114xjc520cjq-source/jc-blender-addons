"""Independent STEP curved-solid/assembly regression. No original CAD app.

Run with normal Python: python tests/test_step.py --blender D:/Blender/blender.exe
"""
from pathlib import Path
import argparse,hashlib,json,subprocess,tempfile,sys

ROOT=Path(__file__).resolve().parents[1]
PLUGIN=ROOT/'jc_auto_import'


def verify(outputs):
    import bpy,bmesh,math
    sys.path.insert(0,str(ROOT))
    from jc_auto_import.worker import import_model
    for target,result in outputs.items():
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        import_model(result['output'])
        meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
        assert len(meshes)==3,(target,[o.name for o in meshes])
        bounds=[];volume=0
        for obj in meshes:
            points=[obj.matrix_world@v.co for v in obj.data.vertices]
            bounds.append([tuple(fn(v[i] for v in points) for i in range(3)) for fn in (min,max)])
            bm=bmesh.new();bm.from_mesh(obj.data);bm.transform(obj.matrix_world)
            volume+=abs(bm.calc_volume());bm.free()
        bounds.sort(key=lambda b:b[0][0])
        expected=[((0,0,0),(.02,.03,.01)),((.04,0,0),(.06,.03,.01)),((.078,-.002,0),(.082,.002,.025))]
        assert max(abs(bounds[j][b][i]-expected[j][b][i]) for j in range(3) for b in range(2) for i in range(3))<1e-5,(target,bounds)
        exact=(2*(6000-math.pi*90)+math.pi*100)*1e-9
        assert abs(volume/exact-1)<.01,(target,volume,exact)
        colors={tuple(round(c,2) for c in slot.material.diffuse_color[:3]) for obj in meshes for slot in obj.material_slots if slot.material}
        assert len(colors)>=2,(target,colors)
        print('STEP_ROUNDTRIP_PASS',target,'3 parts, units, bounds, holes, colors',flush=True)


def verify_repairs():
    sys.path.insert(0,str(PLUGIN/'bin/cad/packages'))
    sys.path.insert(0,str(PLUGIN))
    import cad_worker
    from OCP.gp import gp_Pnt,gp_Pln,gp_Dir
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon,BRepBuilderAPI_MakeFace
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    plane=gp_Pln(gp_Pnt(0,0,0),gp_Dir(0,0,1))
    clean=[gp_Pnt(0,0,0),gp_Pnt(2,0,0),gp_Pnt(2,2,0),gp_Pnt(0,2,0)]
    assert cad_worker.remove_tiny_crossings(clean,plane)==clean
    # Reject a materially self-intersecting bow-tie rather than deleting its area.
    large=[gp_Pnt(0,0,0),gp_Pnt(2,2,0),gp_Pnt(0,2,0),gp_Pnt(2,0,0)]
    assert cad_worker.remove_tiny_crossings(large,plane) is None
    # A microscopic sliver at a sampled trim is recoverable with bounded change.
    tiny=[gp_Pnt(0,0,0),gp_Pnt(1,0,0),gp_Pnt(1.2,.0001,0),gp_Pnt(1,.0001,0),gp_Pnt(1.2,0,0),gp_Pnt(2,0,0),gp_Pnt(2,2,0),gp_Pnt(0,2,0)]
    result=cad_worker.remove_tiny_crossings(tiny,plane)
    assert result is not None and len(result)<len(tiny)
    polygon=BRepBuilderAPI_MakePolygon()
    for p in clean:polygon.Add(p)
    polygon.Close();face=BRepBuilderAPI_MakeFace(plane,polygon.Wire(),True).Face()
    assert cad_worker.repair_face_mesh(face)=='fresh-face'
    assert BRep_Tool.Triangulation_s(face,TopLoc_Location()).NbTriangles()==2
    # Force only the first copied-face mesher attempt to fail, so the bounded
    # planar reconstruction branch is exercised without private CAD fixtures.
    from unittest.mock import patch
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    polygon=BRepBuilderAPI_MakePolygon()
    for p in clean:polygon.Add(p)
    polygon.Close();face=BRepBuilderAPI_MakeFace(plane,polygon.Wire(),True).Face()
    attempts=[]
    def mesh_after_first(*args):
        attempts.append(1)
        if len(attempts)>1:return BRepMesh_IncrementalMesh(*args)
    with patch('OCP.BRepMesh.BRepMesh_IncrementalMesh',side_effect=mesh_after_first):
        assert cad_worker.repair_face_mesh(face)=='planar-trim'
    assert BRep_Tool.Triangulation_s(face,TopLoc_Location()).NbTriangles()==2
    print('STEP_FACE_REPAIR_TESTS_PASS')


def main():
    if '--repair-check' in sys.argv:
        verify_repairs()
        return
    if '--' in sys.argv:
        verify(json.loads(Path(sys.argv[-1]).read_text(encoding='utf-8')))
        return
    parser=argparse.ArgumentParser();parser.add_argument('--blender',required=True);args=parser.parse_args()
    python=PLUGIN/'bin/cad/python/bin/python3.13'
    subprocess.run([str(python),'-B','-X','utf8',str(Path(__file__).resolve()),'--repair-check'],check=True,timeout=60)
    with tempfile.TemporaryDirectory(prefix='jc-step-') as temporary:
        root=Path(temporary)
        subprocess.run([str(python),'-B','-X','utf8',str(ROOT/'engine/tests/step_fixture.py'),str(root)],check=True,timeout=60)
        source=root/'中文 STEP 测试/带孔零件 装配.stp'
        original=hashlib.sha256(source.read_bytes()).hexdigest()
        outputs={}
        def run(target,source=source,reuse=False):
            run=root/('run-'+str(len(list(root.glob('run-*')))));run.mkdir()
            path=run/'job.json';path.write_text(json.dumps(dict(source=str(source),target=target,cache=str(root/'cache'),reuse=reuse,timeout=60)),encoding='utf-8')
            with (run/'worker.log').open('wb') as log:
                p=subprocess.run([args.blender,'--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python',str(PLUGIN/'worker.py'),'--',str(path)],stdout=log,stderr=log,timeout=90)
            return p.returncode,json.loads((run/'result.json').read_text(encoding='utf-8'))
        for target in ['GLB','FBX','OBJ']:
            code,result=run(target);assert code==0,result;outputs[target]=result
        code,result=run('GLB',source=root/'中文 STEP 测试/英寸 装配.STEP')
        assert code==0,result
        outputs['AP242-inch-GLB']=result
        code,cached=run('GLB',reuse=True);assert code==0 and cached['cached']
        assert hashlib.sha256(source.read_bytes()).hexdigest()==original
        bad=root/'损坏.step';bad.write_bytes(b'not a STEP file')
        code,result=run('GLB',source=bad);assert code!=0 and 'error' in result,result
        assert not list((root/'cache').glob('*.partial'))
        report=root/'outputs.json';report.write_text(json.dumps(outputs),encoding='utf-8')
        subprocess.run([args.blender,'--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python',str(Path(__file__).resolve()),'--',str(report)],check=True,timeout=90)
        print('STEP_TESTS_PASS: outputs / geometry / cache / corrupt-file / original unchanged')


if __name__=='__main__':main()
