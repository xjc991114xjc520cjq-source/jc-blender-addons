"""Real Blender integration against the ZIP in isolated scripts/config/state."""
import bpy,addon_utils,importlib,json,subprocess,sys,os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
assert Path(bpy.utils.user_resource('CONFIG')).resolve()==Path(os.environ['BLENDER_USER_CONFIG']).resolve(), 'Refuse to write outside isolated preferences'
release=ROOT/'dist/JC-Blender-Agent-0.1.4.zip'
bpy.ops.preferences.addon_install(filepath=str(release),overwrite=False)
addon_utils.enable('jc_blender_agent',default_set=True,persistent=True)
addon=importlib.import_module('jc_blender_agent')
assert addon.bl_info['version']==(0,1,4)
assert '/runtime' in addon.bridge_root().as_posix()
prefs=addon.preferences();assert prefs is not None
assert prefs.use_render_knowledge is True
addon.runtime().auto_models=False
prefs.use_render_knowledge=False
addon.connect()

def mcp(methods):
    messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'packaged-knowledge-check','version':'1'}}}, {'jsonrpc':'2.0','method':'notifications/initialized'}]
    messages.extend({'jsonrpc':'2.0','id':i+2,'method':method,'params':params} for i,(method,params) in enumerate(methods))
    proc=subprocess.run([addon.python_exe(),str(addon.bridge_root()/'bridge/mcp_server.py'),'--state',str(addon.state_root()),'--instance',addon._instance],input='\n'.join(json.dumps(m) for m in messages)+'\n',capture_output=True,text=True,encoding='utf-8',timeout=20)
    assert proc.returncode==0,proc.stderr
    return [json.loads(line) for line in proc.stdout.splitlines()]

off=mcp([('tools/list',{}),('resources/list',{}),('tools/call',{'name':'blender_render_knowledge','arguments':{'topic':'case'}})])
assert '材质真实感必须来自材质响应' not in off[0]['result']['instructions']
assert len(off[1]['result']['tools'])==8
assert off[2]['result']['resources']==[]
assert off[3]['result']['isError']
prefs.use_render_knowledge=True
on=mcp([('tools/list',{}),('resources/read',{'uri':'jc-render://g603-recipe'}),('tools/call',{'name':'blender_render_knowledge','arguments':{'topic':'preview'}})])
assert '材质真实感必须来自材质响应' in on[0]['result']['instructions']
assert len(on[1]['result']['tools'])==9
assert json.loads(on[2]['result']['contents'][0]['text'])['output']['width']==3000
assert on[3]['result']['content'][1]['type']=='image'
prefs.use_render_knowledge=False
bpy.ops.wm.save_userpref()
result={'passed':True,'blender_version':bpy.app.version_string,'addon_version':list(addon.bl_info['version']),'package_module':addon.__file__,'disabled_mode_tools':8,'enabled_mode_tools':9,'preview_image_returned':True,'saved_preference':False,'source_checkout_used_for_runtime':False}
(ROOT/'evidence/render-knowledge-packaged.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
addon_utils.disable('jc_blender_agent',default_set=False)
print('JC_RENDER_KNOWLEDGE_PACKAGED_PASS')
