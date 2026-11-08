"""Draw the packaged API save controls; isolated state and fake endpoint only."""
import bpy,addon_utils,importlib,os,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
assert Path(bpy.utils.user_resource('CONFIG')).resolve()==Path(os.environ['BLENDER_USER_CONFIG']).resolve()
assert 'api-015-' in os.environ['JC_BLENDER_CREDENTIAL_PROFILE']
bpy.ops.preferences.addon_install(filepath=str(ROOT/'dist/JC-Blender-Agent-0.1.5.zip'),overwrite=False)
addon_utils.enable('jc_blender_agent',default_set=False)
addon=importlib.import_module('jc_blender_agent');rt=addon.runtime()
rt.auto_models=False;rt.agent='api';rt.base_url='https://your-api.example/v1';rt.api_model='';rt.protocol='chat';rt.remember_api_key=True
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':area.spaces.active.show_region_ui=True;area.tag_redraw()

def capture():
    bpy.ops.screen.screenshot(filepath=str(ROOT/'evidence/local-api-015-ui.png'))
    (ROOT/'evidence/local-api-015-ui.json').write_text(json.dumps({'addon_version':list(addon.bl_info['version']),'remember_checkbox':rt.remember_api_key,'key_field_name':rt.bl_rna.properties['api_key'].name,'key_field_password':rt.bl_rna.properties['api_key'].subtype=='PASSWORD','key_status':rt.api_key_status,'module':addon.__file__},ensure_ascii=False,indent=2),encoding='utf-8')
    bpy.ops.wm.quit_blender()

def panel():
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':
            next(r for r in area.regions if r.type=='UI').active_panel_category='JC Agent';area.tag_redraw()
    bpy.app.timers.register(capture,first_interval=2)

bpy.app.timers.register(panel,first_interval=1)
