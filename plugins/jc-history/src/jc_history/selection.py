"""Suppress no-op viewport picks without editing Blender's undo stack or user keymaps."""
import bpy
from bpy.props import BoolProperty, IntVectorProperty

_bindings = []
_registered = False


def enabled():
    addon = bpy.context.preferences.addons.get(__package__)
    return addon is None or addon.preferences.ignore_unchanged_selection


def selection_state(context):
    """Compare selection and active elements, not names of undo steps."""
    layer = context.view_layer
    objects = tuple(sorted(obj.as_pointer() for obj in context.selected_objects))
    active = layer.objects.active.as_pointer() if layer.objects.active else None
    if context.mode == 'OBJECT':
        return objects, active
    if context.mode != 'EDIT_MESH':
        return None
    import bmesh
    meshes = []
    for obj in context.objects_in_mode_unique_data:
        bm = bmesh.from_edit_mesh(obj.data)
        # Store immutable element identifiers, never live BMesh wrappers (native
        # operators may invalidate/recreate those wrappers even for the same mesh).
        for elements in (bm.verts, bm.edges, bm.faces):
            elements.index_update()
        selected = tuple(tuple(elem.index for elem in elements if elem.select)
                         for elements in (bm.verts, bm.edges, bm.faces))
        history = tuple((type(elem).__name__, elem.index) for elem in bm.select_history)
        meshes.append((obj.data.as_pointer(), selected, history,
                       bm.faces.active.index if bm.faces.active else None))
    return objects, active, tuple(meshes)


class JCH_OT_select_changed(bpy.types.Operator):
    bl_idname = 'jch.select_changed'
    bl_label = 'Select'
    bl_description = '选择元素；只有选择或活动元素实际改变时才记录撤销'
    bl_options = {'UNDO', 'INTERNAL'}

    extend: BoolProperty(default=False, options={'SKIP_SAVE'})
    deselect: BoolProperty(default=False, options={'SKIP_SAVE'})
    toggle: BoolProperty(default=False, options={'SKIP_SAVE'})
    deselect_all: BoolProperty(default=False, options={'SKIP_SAVE'})
    select_passthrough: BoolProperty(default=False, options={'SKIP_SAVE'})
    center: BoolProperty(default=False, options={'SKIP_SAVE'})
    enumerate: BoolProperty(default=False, options={'SKIP_SAVE'})
    object: BoolProperty(default=False, options={'SKIP_SAVE'})
    location: IntVectorProperty(size=2, options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        return (enabled() and context.area is not None and context.area.type == 'VIEW_3D'
                and context.region is not None and context.region.type == 'WINDOW'
                and context.mode in {'OBJECT', 'EDIT_MESH'})

    def run(self, context, invoke):
        before = selection_state(context)
        kwargs = {name: getattr(self, name) for name in (
            'extend', 'deselect', 'toggle', 'deselect_all', 'select_passthrough',
            'center', 'enumerate', 'object', 'location')}
        # Suppress the inner undo push. The outer UNDO operator pushes once only
        # when the native pick actually changes selection/active-element state.
        result = bpy.ops.view3d.select('INVOKE_DEFAULT' if invoke else 'EXEC_DEFAULT', False, **kwargs)
        if 'FINISHED' in result and before != selection_state(context):
            return {'FINISHED'}
        return {'CANCELLED'}

    def invoke(self, context, event):
        self.location = (event.mouse_region_x, event.mouse_region_y)
        return self.run(context, True)

    def execute(self, context):
        return self.run(context, False)


def remove_bindings():
    for km, item in reversed(_bindings):
        try:
            km.keymap_items.remove(item)
        except (ReferenceError, RuntimeError):
            pass
    _bindings.clear()


def install_bindings():
    if not _registered:
        return None
    wm = bpy.context.window_manager
    if wm is None or wm.keyconfigs.addon is None:
        return None
    remove_bindings()
    # Read final user bindings, but only ADD our own overlay. Never mutate, disable
    # or save a native/user keymap item, so disabling leaves shortcuts intact.
    candidates = []
    for km in wm.keyconfigs.user.keymaps:
        if km.is_modal:
            continue
        for item in km.keymap_items:
            if item.idname != 'view3d.select' or not item.active:
                continue
            if item.properties.enumerate or item.properties.object:
                continue  # Native popup/object-parenting selection keeps its own flow.
            if item.value == 'PRESS' and item.properties.select_passthrough:
                # Native press-through is what starts tweak/drag gestures. Leave
                # that phase intact and filter its separate completed CLICK binding.
                continue
            values = {name: getattr(item.properties, name) for name in item.properties.keys()}
            event = {key: getattr(item, key) for key in (
                'any', 'shift', 'ctrl', 'alt', 'oskey', 'key_modifier', 'repeat')}
            candidates.append((km.name, km.space_type, km.region_type, item.type, item.value, event, values))
    for name, space, region, kind, value, event, values in candidates:
        km = wm.keyconfigs.addon.keymaps.new(name=name, space_type=space, region_type=region)
        item = km.keymap_items.new(JCH_OT_select_changed.bl_idname, kind, value, **event)
        for key, val in values.items():
            if hasattr(item.properties, key):
                setattr(item.properties, key, val)
        _bindings.append((km, item))
    return None


def register():
    global _registered
    bpy.utils.register_class(JCH_OT_select_changed)
    _registered = True
    bpy.app.timers.register(install_bindings, first_interval=.2, persistent=True)


def unregister():
    global _registered
    _registered = False
    if bpy.app.timers.is_registered(install_bindings):
        bpy.app.timers.unregister(install_bindings)
    remove_bindings()
    bpy.utils.unregister_class(JCH_OT_select_changed)
