"""Actual bpy integration check. Run with Blender --background --factory-startup."""
import bpy
import importlib
import json
import os
from pathlib import Path
import sys
import uuid

PROJECT=Path(__file__).resolve().parents[1]
os.environ['JC_BLENDER_STATE']=str(PROJECT/'evidence'/'background-state')
sys.path.insert(0,str(PROJECT/'addon'))
addon=importlib.import_module('jc_blender_agent')
addon.register()
addon._instance=uuid.uuid4().hex
directory=addon.state_root()/'artifacts'/addon._instance/'integration'
directory.mkdir(parents=True,exist_ok=True)
def call(name,args=None):
    return addon.execute_command({'name':name,'arguments':args or {},'artifact_dir':str(directory)})

reports=[]
scene=call('blender_scene');assert scene['blender_version'].startswith('5.2')
reports.append('registered and read actual Blender scene')
original=bpy.data.filepath
r=call('blender_execute',{'code':"bpy.ops.mesh.primitive_uv_sphere_add(); o=bpy.context.object; o.name='JC_Background_Test'; o.location=(1,2,3); result={'name':o.name,'vertices':len(o.data.vertices)}",'description':'actual-bpy-edit'})
assert not r.get('error'),r
assert r['result']['vertices']>100
assert Path(r['checkpoint']).is_file()
assert bpy.data.filepath==original, (bpy.data.filepath,original)
reports.append('real bpy edit and pre-edit .blend checkpoint, source path unchanged')
assert call('blender_object',{'name':'JC_Background_Test'})['location']==[1.0,2.0,3.0]
bad=call('blender_execute',{'code':"bpy.data.objects['JC_Background_Test'].location.x=99; raise RuntimeError('expected test failure')",'description':'partial-failure-test'})
assert bad['partial_changes_possible'] and Path(bad['checkpoint']).is_file()
reports.append('partial failure reported with recoverable checkpoint')
call('blender_restore',{'checkpoint':bad['checkpoint']})
assert tuple(bpy.data.objects['JC_Background_Test'].location)==(1,2,3)
reports.append('actual .blend restore recovered transform')
addon.runtime().remember_api_key=False
addon.runtime().api_key='JC_SENTINEL_KEY_SHOULD_NOT_PERSIST'
attachment=addon.runtime().attachments.add();attachment.filepath='JC_SENTINEL_ATTACHMENT_PATH_SHOULD_NOT_PERSIST';attachment.identifier='a'*32
last_edit=addon._last_edit_checkpoint
secret_checkpoint=call('blender_checkpoint',{'label':'key-persistence-check'})['checkpoint']
assert addon._last_edit_checkpoint==last_edit, 'Manual/final checkpoint replaced edit rollback target'
addon.runtime().api_key=''
addon.runtime().attachments.clear()
bpy.ops.wm.open_mainfile(filepath=secret_checkpoint,load_ui=False)
assert addon.runtime().api_key=='', 'Temporary API key persisted in .blend'
assert len(addon.runtime().attachments)==0, 'Attachment paths persisted in .blend'
reports.append('temporary API key and attachment path references absent after saving and reopening .blend')
try:call('blender_restore',{'checkpoint':str(PROJECT/'outside.blend')})
except ValueError:reports.append('restore rejects paths outside owned artifacts')
else:raise AssertionError('restore path guard')
assert bpy.ops.screen.screenshot_area is not None
addon.unregister()
(PROJECT/'evidence'/'background-result.json').write_text(json.dumps({'passed':True,'checks':reports},ensure_ascii=False,indent=2),encoding='utf-8')
print('JC_BACKGROUND_PASS',len(reports))
