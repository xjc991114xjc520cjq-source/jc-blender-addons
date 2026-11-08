"""Launch an independent GUI for actual native-menu clicks and restore testing."""
from pathlib import Path
import importlib
import sys
import tempfile
import bpy

BASE = Path(__file__).resolve().parents[1]
module_name = "bl_ext.user_default.jc_history" if "--extension" in sys.argv else "jc_history"
if module_name == "jc_history":
    sys.path.insert(0, str(BASE / "src"))
bpy.ops.preferences.addon_enable(module=module_name)
addon = importlib.import_module(module_name)
TEST = Path(tempfile.mkdtemp(prefix="jc_history_gui_"))
addon.settings().storage_root = str(TEST / "snapshots")
bpy.context.preferences.view.language = 'zh_HANS'
bpy.context.preferences.view.use_translate_interface = True
cube = bpy.data.objects["Cube"]
cube.name = "JC历史插件测试"
bpy.ops.wm.save_as_mainfile(filepath=str(TEST / "JC历史插件测试.blend"))
bpy.ops.ed.undo_push(message="初始方块")
cube.location.x = 1
bpy.ops.ed.undo_push(message="移动 X = 1")
addon.capture_snapshot("第一版：移动完成")
cube.scale = (1, 1, 2)
bpy.ops.ed.undo_push(message="拉高方块")
addon.capture_snapshot("第二版：拉高完成")
cube.location.x = 3
bpy.ops.ed.undo_push(message="移动 X = 3")
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        area.spaces.active.show_region_ui = True
        for region in area.regions:
            if region.type == 'UI':
                try:
                    region.active_panel_category = "JC历史"
                except Exception:
                    pass
        area.tag_redraw()
(BASE / "tests" / "gui_directory.txt").write_text(str(TEST), encoding="utf-8")
