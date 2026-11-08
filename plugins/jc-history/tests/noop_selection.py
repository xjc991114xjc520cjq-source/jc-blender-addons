"""GUI/GPU integration: execute real native picks with undo, using an isolated profile."""
import bpy,sys,os,json,traceback
from pathlib import Path
from mathutils import Quaternion,Vector
from bpy_extras.view3d_utils import location_3d_to_region_2d
BASE=Path(__file__).resolve().parents[1]
OUT=Path(os.environ['JC_HISTORY_TEST_OUT'])
assert Path(bpy.utils.user_resource('CONFIG')).resolve()==Path(os.environ['BLENDER_USER_CONFIG']).resolve()
sys.path.insert(0,str(BASE/'src'))
import addon_utils
addon=addon_utils.enable('jc_history',default_set=True)
assert addon
bpy.context.preferences.view.show_splash=False
bpy.context.preferences.edit.undo_steps=64
bpy.context.preferences.view.smooth_view=0
area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D')
region=next(r for r in area.regions if r.type=='WINDOW')
rv=area.spaces.active.region_3d
rv.view_rotation=Quaternion((1,0,0,0))
rv.view_perspective='ORTHO'
rv.view_location=(0,0,0)
rv.view_distance=5
checks=[]; trace=[]

def check(name, condition):
    assert condition,name
    checks.append(name)

def pick(point):
    before=addon.selection.selection_state(bpy.context)
    result=bpy.ops.jch.select_changed('EXEC_DEFAULT',True,location=point,deselect_all=True)
    after=addon.selection.selection_state(bpy.context)
    trace.append({'point':point,'result':sorted(result),'changed':before!=after,'before':before,'after':after})
    return result

def run_object():
    try:
        with bpy.context.temp_override(area=area,region=region):
            check('addon_overlay_installed',len(addon.selection._bindings)>0)
            native_before=[(km.name,item.id,item.idname,item.active) for km in bpy.context.window_manager.keyconfigs.default.keymaps for item in km.keymap_items]
            point=location_3d_to_region_2d(region,rv,Vector((0,0,0)))
            center=(round(point.x),round(point.y)); blank=(80,80)
            bpy.ops.object.select_all('EXEC_DEFAULT',False,action='DESELECT')
            bpy.ops.ed.undo_push(message='Object selection baseline')
            check('blank_with_no_selection_cancelled',pick(blank)=={'CANCELLED'})
            check('effective_object_pick_finished',pick(center)=={'FINISHED'})
            check('repeat_object_pick_cancelled',pick(center)=={'CANCELLED'})
            bpy.ops.ed.undo()
            check('one_undo_restores_before_effective_pick',not bpy.context.selected_objects)
            check('noop_while_on_redo_branch_cancelled',pick(blank)=={'CANCELLED'})
            bpy.ops.ed.redo()
            check('noop_does_not_destroy_redo',bpy.context.selected_objects[0].name=='Cube')
            check('effective_deselect_finished',pick(blank)=={'FINISHED'})
            check('repeat_blank_pick_cancelled',pick(blank)=={'CANCELLED'})
            bpy.ops.ed.undo()
            check('one_undo_restores_effective_deselect',bpy.context.selected_objects[0].name=='Cube')
            bpy.ops.transform.translate('EXEC_DEFAULT',True,value=(1,0,0))
            bpy.ops.ed.undo()
            check('normal_transform_undo_preserved',abs(bpy.data.objects['Cube'].location.x)<1e-5)
            bpy.ops.ed.redo()
            check('normal_transform_redo_preserved',abs(bpy.data.objects['Cube'].location.x-1)<1e-5)
            bpy.ops.ed.undo()
            addon.selection.remove_bindings(); addon.selection.install_bindings()
            check('native_default_keymaps_unchanged',native_before==[(km.name,item.id,item.idname,item.active) for km in bpy.context.window_manager.keyconfigs.default.keymaps for item in km.keymap_items])
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all('EXEC_DEFAULT',False,action='DESELECT')
            bpy.ops.ed.undo_push(message='Mesh selection baseline')
        bpy.app.timers.register(run_mesh,first_interval=1)
    except Exception:
        finish_error()
    return None

def run_mesh():
    try:
        import bmesh
        with bpy.context.temp_override(area=area,region=region):
            # Top orthographic view, large cube: one visible vertex well away from others.
            point=location_3d_to_region_2d(region,rv,Vector((1,1,1)))
            vertex=(round(point.x),round(point.y))
            check('mesh_blank_noop_cancelled',pick((80,80))=={'CANCELLED'})
            check('effective_vertex_pick_finished',pick(vertex)=={'FINISHED'})
            check('repeat_vertex_pick_cancelled',pick(vertex)=={'CANCELLED'})
            bpy.ops.ed.undo()
            bm=bmesh.from_edit_mesh(bpy.context.edit_object.data)
            check('one_undo_restores_before_vertex_pick',not any(v.select for v in bm.verts))
            bpy.ops.ed.redo()
            bm=bmesh.from_edit_mesh(bpy.context.edit_object.data)
            check('vertex_redo_preserved',sum(v.select for v in bm.verts)==1)
            bpy.ops.object.mode_set(mode='OBJECT')
            prefs=addon.settings()
            prefs.ignore_unchanged_selection=False
            check('switch_off_uses_native_fallback',not bpy.ops.jch.select_changed.poll())
            prefs.ignore_unchanged_selection=True
            check('switch_on_restores_filter',bpy.ops.jch.select_changed.poll())
            addon_utils.disable('jc_history',default_set=True)
            check('overlay_removed_on_disable',not addon.selection._bindings)
            check('install_timer_removed_on_disable',not bpy.app.timers.is_registered(addon.selection.install_bindings))
        (OUT/'noop-results.json').write_text(json.dumps({'passed':len(checks),'checks':checks,'trace':trace,'blender':bpy.app.version_string},indent=2))
        print('JC_HISTORY_NOOP_PASS',len(checks),flush=True)
        bpy.ops.wm.quit_blender()
    except Exception:
        finish_error()
    return None

def finish_error():
    (OUT/'noop-error.txt').write_text(traceback.format_exc()+'\n'+json.dumps(trace,indent=2))
    print(traceback.format_exc(),flush=True)
    bpy.ops.wm.quit_blender()

bpy.app.timers.register(run_object,first_interval=3)
