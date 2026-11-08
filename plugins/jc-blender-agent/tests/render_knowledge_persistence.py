import bpy,addon_utils,importlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
assert Path(bpy.utils.user_resource('CONFIG')).resolve()==Path(os.environ['BLENDER_USER_CONFIG']).resolve()
addon_utils.enable('jc_blender_agent',default_set=False)
addon=importlib.import_module('jc_blender_agent')
assert addon.preferences().use_render_knowledge is False
print('JC_RENDER_KNOWLEDGE_PREFERENCE_PERSISTED')
addon_utils.disable('jc_blender_agent',default_set=False)
