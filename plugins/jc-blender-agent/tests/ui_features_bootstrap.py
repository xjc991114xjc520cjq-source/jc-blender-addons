"""Native panel pinning + 5.2 textbox, in a separate factory scene."""
import bpy
import sys
import json
import os
from pathlib import Path
import importlib
ROOT=Path(__file__).resolve().parents[1]
if os.environ.get('JC_TEST_PACKAGE'):
    import addon_utils
    bpy.ops.preferences.addon_install(filepath=str(ROOT/'dist/JC-Blender-Agent-0.1.3.zip'),overwrite=False)
    addon_utils.enable('jc_blender_agent',default_set=False)
else:
    sys.path.insert(0,str(ROOT/'addon'))
sys.path.insert(0,'F:/Tools/JCBlenderHistory/src')
agent=importlib.import_module('jc_blender_agent')
if not os.environ.get('JC_TEST_PACKAGE'):agent.register()
history=importlib.import_module('jc_history');history.register()
main=bpy.context.window
area=next(a for a in main.screen.areas if a.type=='VIEW_3D')
area.spaces.active.show_region_ui=True
original_area_count=len(main.screen.areas)
bpy.context.object.name='UI_Main_Target'
agent.runtime().prompt='只检查选中对象的名称和数量。\n保留现有对象、材质与动画。'
agent.runtime().codex_model='gpt-6.1-sol'
agent.connect()
if os.environ.get('JC_TEST_ATTACHMENTS'):
    agent.runtime().video_frames=2
    agent.add_attachment_paths([str(ROOT/'evidence/attachment-fixtures/reference-video.mp4'),str(ROOT/'evidence/attachment-fixtures/reference-notes.txt'),str(ROOT/'dist/demo/preview.png')])
    agent.runtime().prompt='请用附件工具查看视频的两张参考帧、读取文本附件，并检查当前 Blender 场景。只报告两个采样画面的颜色和当前选中对象，不修改场景。不要声称看过完整视频或听过音频。'
def pin():
    ui=next(r for r in area.regions if r.type=='UI')
    try:ui.active_panel_category='JC历史'
    except ValueError:return .2
    with bpy.context.temp_override(window=main,area=area,region=next(r for r in area.regions if r.type=='WINDOW')):
        assert bpy.ops.jc_agent.open_window()=={'FINISHED'}
    bpy.app.timers.register(finalize,first_interval=1)
    return None

def finalize():
    assert len(bpy.context.window_manager.windows)==1
    assert len(main.screen.areas)==original_area_count
    assert not agent._pin_requests
    result={'instance':agent._instance,'pid':os.getpid(),'main_window':main.as_pointer(),
        'blender_windows':len(bpy.context.window_manager.windows),'area_count':len(main.screen.areas),
        'source_category':next(r.active_panel_category for r in area.regions if r.type=='UI'),
        'module':agent.__file__,'runtime':str(agent.bridge_root()),'native_textbox_available':'textbox' in bpy.types.UILayout.bl_rna.functions,
        'extra_text_editors':sum(a.type=='TEXT_EDITOR' for a in main.screen.areas),'model_count':len(agent.runtime().models),'attachments':[{'id':a.identifier,'path':a.filepath,'kind':a.kind,'state':a.state} for a in agent.runtime().attachments]}
    assert result['source_category']=='JC历史'
    (ROOT/('evidence/ui-attachments-ready.json' if os.environ.get('JC_TEST_ATTACHMENTS') else 'evidence/ui-native-ready.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return None
bpy.app.timers.register(pin,first_interval=1)
