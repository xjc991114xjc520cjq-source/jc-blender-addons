"""Start a separate factory scene. Never edits the user's existing Blender instance."""
import bpy
import importlib
import os
from pathlib import Path
import sys
import time

PROJECT=Path(__file__).resolve().parents[1]
os.environ['JC_BLENDER_STATE']=str(PROJECT/'evidence'/'gui-state')
sys.path.insert(0,str(PROJECT/'addon'))
addon=importlib.import_module('jc_blender_agent')
addon.register()
addon.connect()
rt=addon.runtime()
rt.agent='codex'
rt.prompt='这是独立测试场景。请直接通过 jc_blender MCP 工具创建一只可爱的红色白斑蘑菇，命名使用 JC_Demo_ 前缀。模型需有圆润菌盖、米白菌柄、两只黑眼睛、地面、相机和柔和三点灯光，材质可编辑。只隐藏默认 Cube 的显示和渲染，保留它。给蘑菇整体添加 1 至 48 帧的上下弹跳关键帧，创建用于整体控制的空物体。相机朝向蘑菇，画面中心完整可见。最后读取场景，取得实际视口截图，并渲染一张 512 像素的 EEVEE 预览检查。不要只输出代码。'
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.show_region_ui=True
            # Select our native panel tab when supported.
            try:area.spaces.active.active_panel_category='JC Agent'
            except Exception:pass

def send():
    result=bpy.ops.jc_agent.send()
    (PROJECT/'evidence'/'gui-submit.txt').write_text(str(result)+'\n'+str(addon._instance)+'\n'+str(addon._job),encoding='utf-8')
    return None
bpy.app.timers.register(send,first_interval=2.0)
