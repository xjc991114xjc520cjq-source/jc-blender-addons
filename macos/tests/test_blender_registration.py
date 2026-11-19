"""Headless registration smoke check; does not establish interactive UI acceptance."""
from pathlib import Path
import importlib.util
import sys
import bpy

ROOT = Path(__file__).resolve().parents[2]
modules = {
    'jc_blender_agent': ROOT / 'macos/jc-blender-agent/addon/jc_blender_agent',
    'jc_auto_import': ROOT / 'macos/jc-auto-import/jc_auto_import',
    'jc_history': ROOT / 'plugins/jc-history/src/jc_history',
    'jc_view_navigator': ROOT / 'plugins/jc-view-navigator/jc_view_navigator',
}
for name, folder in modules.items():
    spec = importlib.util.spec_from_file_location(name, folder / '__init__.py',
                                                submodule_search_locations=[str(folder)])
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module)
    module.register()
    module.unregister()
    print('BLENDER_REGISTER_UNREGISTER_PASS', name, flush=True)
