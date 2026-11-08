import bpy,sys,json
from pathlib import Path
assert bpy.data.filepath, 'Open the saved sentinel checkpoint in this fresh process first'
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'addon'))
import jc_blender_agent as addon
addon.register()
assert not addon.runtime().api_key
assert not addon.runtime().attachments
print('FRESH_PROCESS_RUNTIME_PATHS_NOT_LOADED')
addon.unregister()
