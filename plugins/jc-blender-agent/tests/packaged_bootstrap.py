"""Install the actual release ZIP into isolated Blender preferences/scripts."""
import bpy
import addon_utils
from pathlib import Path
import json
import importlib

ROOT=Path(__file__).resolve().parents[1]
bpy.ops.preferences.addon_install(filepath=str(ROOT/'dist/JC-Blender-Agent-0.1.3.zip'),overwrite=False)
addon_utils.enable('jc_blender_agent',default_set=False)
addon=importlib.import_module('jc_blender_agent')
addon.connect()
rt=addon.runtime();rt.codex_model='gpt-6.1-sol'
rt.prompt='只修改蘑菇的菌盖颜色，保留其他对象与动画。完成后检查实际预览。'
rt.status='发行 ZIP 已安装并连接，可继续输入描述'
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.show_region_ui=True
def ready():
    (ROOT/'evidence/packaged-ready.json').write_text(json.dumps({'instance':addon._instance,'module':addon.__file__,'runtime':str(addon.bridge_root()),'connected':rt.connected},ensure_ascii=False,indent=2),encoding='utf-8')
    return None
bpy.app.timers.register(ready,first_interval=2)
