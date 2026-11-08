# SPDX-License-Identifier: GPL-3.0-or-later
"""A fixed six-direction compass drawn by Blender's native navigation gizmo."""

bl_info = {
    'name': 'JC 六向视图导航', 'author': 'JCOne', 'version': (1, 1, 0),
    'blender': (4, 2, 0), 'location': '3D 视图 > 右上角原生导航区',
    'description': '原生轴球绘制，六个固定端点一键直达六向正交视图', 'category': '3D View',
}
import math
import bpy
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, EnumProperty
from mathutils import Matrix, Quaternion

VIEWS = (
    ('FRONT', '正视图', '-Y'), ('BACK', '后视图', '+Y'),
    ('LEFT', '左侧视图', '-X'), ('RIGHT', '右侧视图', '+X'),
    ('TOP', '俯视图', '+Z'), ('BOTTOM', '仰视图', '-Z'),
)
QUATERNIONS = {
    'FRONT': (math.sqrt(.5), math.sqrt(.5), 0, 0),
    'BACK': (0, 0, math.sqrt(.5), math.sqrt(.5)),
    'LEFT': (.5, .5, -.5, -.5), 'RIGHT': (.5, .5, .5, .5),
    'TOP': (1, 0, 0, 0), 'BOTTOM': (0, 1, 0, 0),
}
# A fixed isometric presentation keeps all six targets separated at every view angle.
COMPASS_MATRIX = Quaternion((.820473, .424708, .17592, .339852)).normalized().inverted().to_matrix().to_4x4()
_spaces = {}
_registered = False


def preferences(context):
    addon = context.preferences.addons.get(__package__)
    return addon.preferences if addon else None


def redraw():
    if bpy.context.window_manager is None:
        return
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def restore_native(clear=True):
    for space, original in list(_spaces.values()):
        try:
            space.show_gizmo_navigate = original
        except (ReferenceError, RuntimeError):
            pass
    if clear:
        _spaces.clear()


def sync_native():
    prefs = preferences(bpy.context)
    if not _registered or (prefs and not prefs.enabled):
        restore_native()
        return
    live = set()
    # Splitting a viewport copies the temporarily hidden native flag into the new space.
    inherited_replacement = bool(_spaces) and any(original for _, original in _spaces.values())
    for screen in bpy.data.screens:
        for area in screen.areas:
            for space in area.spaces:
                if space.type != 'VIEW_3D':
                    continue
                ptr = space.as_pointer()
                live.add(ptr)
                if ptr not in _spaces:
                    _spaces[ptr] = (space, space.show_gizmo_navigate or inherited_replacement)
                if space.show_gizmo_navigate:
                    space.show_gizmo_navigate = False
    for ptr in set(_spaces) - live:
        _spaces.pop(ptr, None)


def sync_timer():
    if not _registered:
        return None
    sync_native()
    return .5


def changed(self, context):
    sync_native()
    redraw()


@persistent
def before_save(_):
    # Files retain ordinary navigation when opened on a machine without this add-on.
    restore_native(clear=False)


@persistent
def after_save(_):
    sync_native()


@persistent
def before_load(_):
    restore_native()


@persistent
def after_load(_):
    sync_native()


def visible_bounds(context):
    region = context.region
    left, bottom, right, top = 0, 0, region.width, region.height
    for other in context.area.regions:
        if other == region or other.width <= 1 or other.height <= 1:
            continue
        x0, y0 = other.x - region.x, other.y - region.y
        x1, y1 = x0 + other.width, y0 + other.height
        if other.type in {'UI', 'TOOLS'} and y1 > bottom and y0 < top:
            if x1 >= right and x0 > left:
                right = min(right, x0)
            elif x0 <= left and x1 < right:
                left = max(left, x1)
        elif other.type in {'HEADER', 'TOOL_HEADER', 'ASSET_SHELF', 'ASSET_SHELF_HEADER'}:
            if y1 >= top and y0 > bottom:
                top = min(top, y0)
            elif y0 <= bottom and y1 < top:
                bottom = max(bottom, y1)
    return left, bottom, right, top


def layout(context):
    scale = context.preferences.system.ui_scale
    size = context.preferences.view.gizmo_size_navigate_v3d * scale
    _, _, right, top = visible_bounds(context)
    # Native visible rectangles use an inclusive right edge (width - 1).
    return round(right - 1 - size / 2 - 10 * scale), round(top - size / 2 - 10 * scale), size / 2


class JCViewPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    enabled: BoolProperty(name='用六向导航替换原生导航', default=True, update=changed)

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, 'enabled')
        col.label(text='直接使用 Blender 的原生轴球、字体、配色及尺寸。')
        col.label(text='实心端点：X 右视图 / Y 后视图 / Z 俯视图。')
        col.label(text='空心端点：X 左视图 / Y 正视图 / Z 仰视图（悬停显示名称）。')
        col.label(text='六个目标保持分开。点击立即切换正交视图，重复点击不翻转。')
        col.label(text='“视图”菜单可恢复原生导航；大小跟随 Blender 导航控件尺寸。')


class JC_OT_view_axis(bpy.types.Operator):
    bl_idname = 'view3d.jc_fixed_axis'
    bl_label = '切换六向正交视图'
    bl_options = {'INTERNAL'}
    axis: EnumProperty(items=[(key, name, name) for key, name, _ in VIEWS])

    @classmethod
    def description(cls, context, properties):
        name, direction = next(((name, direction) for key, name, direction in VIEWS if key == properties.axis), ('正交视图', ''))
        return f'{name}（{direction}）· 一键直达，重复点击保持此方向'

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == 'VIEW_3D' and context.region_data is not None

    def execute(self, context):
        smooth = context.preferences.view.smooth_view
        try:
            context.preferences.view.smooth_view = 0
            result = bpy.ops.view3d.view_axis('EXEC_DEFAULT', type=self.axis, align_active=False)
        finally:
            context.preferences.view.smooth_view = smooth
        if 'FINISHED' in result:
            context.region_data.view_perspective = 'ORTHO'
            context.area.tag_redraw()
        return result


class JC_GGT_view_navigator(bpy.types.GizmoGroup):
    bl_idname = 'JC_GGT_view_navigator'
    bl_label = 'JC 六向视图导航'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', 'SCALE', 'SHOW_MODAL_ALL'}

    @classmethod
    def poll(cls, context):
        prefs = preferences(context)
        space = context.space_data
        state = _spaces.get(space.as_pointer())
        return space.type == 'VIEW_3D' and space.show_gizmo and (prefs is None or prefs.enabled) and bool(state and state[1])

    def setup(self, context):
        # The same compiled gizmo type used by Blender's own XYZ ball, including its text.
        self.ball = self.gizmos.new('VIEW3D_GT_navigate_rotate')
        self.ball.color, self.ball.alpha = (.5, .5, .5), 0
        self.ball.color_highlight, self.ball.alpha_highlight = (.5, .5, .5), .5
        self.ball.use_tooltip = True
        for index, axis in enumerate(('LEFT', 'RIGHT', 'FRONT', 'BACK', 'BOTTOM', 'TOP'), 1):
            self.ball.target_set_operator(JC_OT_view_axis.bl_idname, index=index).axis = axis
        # No drag/rotate operator in slot 0: every end is an explicit destination.
        self.controls = {}
        for role, icon, operator in (
                ('ZOOM', 'VIEW_ZOOM', 'view3d.zoom'), ('PAN', 'VIEW_PAN', 'view3d.move'),
                ('CAMERA_OFF', 'VIEW_CAMERA_UNSELECTED', 'view3d.view_camera'),
                ('CAMERA_ON', 'VIEW_CAMERA', 'view3d.view_camera'),
                ('PERSP', 'VIEW_PERSPECTIVE', 'view3d.view_persportho'),
                ('ORTHO', 'VIEW_ORTHO', 'view3d.view_persportho'),
                ('LOCKED', 'VIEW_LOCKED', 'wm.context_toggle'),
                ('UNLOCKED', 'VIEW_UNLOCKED', 'wm.context_toggle')):
            g = self.gizmos.new('GIZMO_GT_button_2d')
            g.icon = icon
            g.draw_options = {'OUTLINE', 'BACKDROP'}
            g.color, g.alpha = (.5, .5, .5), 0
            g.color_highlight, g.alpha_highlight = (.5, .5, .5), .5
            g.use_draw_modal = True
            g.show_drag = operator in {'view3d.zoom', 'view3d.move'}
            op = g.target_set_operator(operator)
            if g.show_drag:
                op.use_cursor_init = False
            if role in {'LOCKED', 'UNLOCKED'}:
                op.data_path = 'space_data.lock_camera'
            self.controls[role] = g

    def draw_prepare(self, context):
        scale = context.preferences.system.ui_scale
        x, y, radius = layout(context)
        self.ball.matrix_basis = Matrix.Translation((x, y, 0))
        self.ball.matrix_offset = COMPASS_MATRIX
        # GizmoGroup SCALE already applies UI scaling to the basis size.
        self.ball.scale_basis = context.preferences.view.gizmo_size_navigate_v3d / 2
        self.ball.hide = context.region.width < 120 or context.region.height < 160
        _, _, right, top = visible_bounds(context)
        mini_x = round(right - 1 - 22.5 * scale)
        mini_y = round(top - (radius / scale + 10) * 2.2 * scale)
        rv3d = context.region_data
        in_camera = rv3d.view_perspective == 'CAMERA'
        roles = []
        if not getattr(rv3d, 'lock_zoom_and_dolly', False):
            roles.append('ZOOM')
        if not getattr(rv3d, 'lock_location', False):
            roles.append('PAN')
        if not getattr(rv3d, 'lock_rotation', False):
            roles.append('CAMERA_ON' if in_camera else 'CAMERA_OFF')
            if not in_camera:
                roles.append('PERSP' if rv3d.is_perspective else 'ORTHO')
        if in_camera:
            roles.append('LOCKED' if context.space_data.lock_camera else 'UNLOCKED')
        for g in self.controls.values():
            g.hide = True
        for i, role in enumerate(roles):
            g = self.controls[role]
            g.matrix_basis = Matrix.Translation((mini_x, mini_y - 30 * scale * i, 0))
            g.scale_basis = 14
            g.hide = self.ball.hide


class JC_OT_toggle_navigator(bpy.types.Operator):
    bl_idname = 'view3d.jc_toggle_navigator'
    bl_label = 'JC 六向导航 / 恢复原生导航'
    bl_description = '切换固定六向轴球与 Blender 原生导航'

    def execute(self, context):
        prefs = preferences(context)
        if prefs:
            prefs.enabled = not prefs.enabled
        return {'FINISHED'}


def menu(self, context):
    self.layout.separator()
    self.layout.operator(JC_OT_toggle_navigator.bl_idname, icon='ORIENTATION_VIEW')


CLASSES = (JCViewPreferences, JC_OT_view_axis, JC_GGT_view_navigator, JC_OT_toggle_navigator)
HANDLERS = (('save_pre', before_save), ('save_post', after_save), ('load_pre', before_load), ('load_post', after_load))


def register():
    global _registered
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    _registered = True
    bpy.types.VIEW3D_MT_view.append(menu)
    for name, fn in HANDLERS:
        getattr(bpy.app.handlers, name).append(fn)
    # Blender restricts bpy.data while enabling an add-on; initialize on the next UI tick.
    bpy.app.timers.register(sync_timer, first_interval=.05, persistent=True)


def unregister():
    global _registered
    _registered = False
    if bpy.app.timers.is_registered(sync_timer):
        bpy.app.timers.unregister(sync_timer)
    restore_native()
    for name, fn in HANDLERS:
        handlers = getattr(bpy.app.handlers, name)
        if fn in handlers:
            handlers.remove(fn)
    bpy.types.VIEW3D_MT_view.remove(menu)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    redraw()
