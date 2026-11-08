"""Independent verification of the actual Agent-produced .blend, not its self-report."""
import bpy
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'evidence/demo-check';out.mkdir(exist_ok=True)
scene=bpy.context.scene
ctrl=bpy.data.objects['JC_Demo_Controller']
cube=bpy.data.objects['Cube']
assert cube.hide_render and cube.hide_get()
assert len(cube.data.vertices)==8 and len(cube.data.polygons)==6
assert ctrl.animation_data and ctrl.animation_data.action
assert len(ctrl.children)>=14
assert scene.camera and scene.camera.name.startswith('JC_Demo_')
for name in ('JC_Demo_Cap','JC_Demo_Stem','JC_Demo_Eye_L','JC_Demo_Eye_R'):
    obj=bpy.data.objects[name];assert obj.type=='MESH' and len(obj.data.vertices)>8
    assert obj.parent==ctrl
    assert obj.data.materials and obj.data.materials[0].use_nodes
samples=[]
eye=bpy.data.objects['JC_Demo_Eye_L']
for frame in (1,7,13,19,25,31,37,43,48):
    scene.frame_set(frame);bpy.context.view_layer.update()
    samples.append({'frame':frame,'controller_z':round(ctrl.location.z,6),'eye_world_z':round(eye.matrix_world.translation.z,6)})
assert max(x['controller_z'] for x in samples)-min(x['controller_z'] for x in samples)>.5
assert abs(samples[0]['eye_world_z']-samples[-1]['eye_world_z'])<.01
assert max(x['eye_world_z'] for x in samples)-min(x['eye_world_z'] for x in samples)>.5
report={'passed':True,'source':bpy.data.filepath,'blender_version':bpy.app.version_string,'objects':len(scene.objects),'controller_children':len(ctrl.children),
    'action':ctrl.animation_data.action.name,'materials':[m.name for m in bpy.data.materials if m.name.startswith('JC_Demo_')],
    'cube_preserved':True,'animation_samples':samples,'checks':['actual mesh geometry','editable node materials','preserved default cube','camera','animated child movement and loop endpoints']}
(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
scene.render.resolution_x=256;scene.render.resolution_y=256;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
for frame in range(1,49,4):
    scene.frame_set(frame);scene.render.filepath=str(out/f'frame-{frame:02d}.png')
    bpy.ops.render.render(write_still=True)
print('JC_DEMO_INDEPENDENT_PASS')
