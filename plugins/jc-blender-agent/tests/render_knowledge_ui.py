"""Native Blender panel draw check in an isolated, disposable GUI process."""
import bpy,addon_utils,importlib,os,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
assert Path(bpy.utils.user_resource('CONFIG')).resolve()==Path(os.environ['BLENDER_USER_CONFIG']).resolve()
addon_utils.enable('jc_blender_agent',default_set=True)
addon=importlib.import_module('jc_blender_agent')
addon.runtime().auto_models=False
addon.preferences().use_render_knowledge=True
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.show_region_ui=True
            area.tag_redraw()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'evidence/knowledge-014-ui.blend'))

def disabled():
    bpy.ops.screen.screenshot(filepath=str(ROOT/'evidence/knowledge-014-ui-disabled.png'))
    (ROOT/'evidence/knowledge-014-ui.json').write_text(json.dumps({'addon_version':list(addon.bl_info['version']),'enabled_and_disabled_panel_drawn':True,'objects_unchanged':[o.name for o in bpy.context.scene.objects]},indent=2),encoding='utf-8')
    bpy.ops.wm.quit_blender()

def enabled():
    bpy.ops.screen.screenshot(filepath=str(ROOT/'evidence/knowledge-014-ui-enabled.png'))
    addon.preferences().use_render_knowledge=False
    for a in bpy.context.screen.areas:a.tag_redraw()
    bpy.app.timers.register(disabled,first_interval=2)

def select_panel():
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':
            next(r for r in area.regions if r.type=='UI').active_panel_category='JC Agent'
            area.tag_redraw()
    bpy.app.timers.register(enabled,first_interval=2)

bpy.app.timers.register(select_panel,first_interval=1)
