"""Original implementation using Blender's own undo UI and local .blend copies.

The built-in C menu is embedded with UILayout.menu_contents. It reads the real
stack, including skipped internal steps, active state and redo states. We never
infer stack indexes from the operator log or inspect Blender memory structures.
"""
from pathlib import Path
import shutil
import uuid
from datetime import datetime

import bpy
from bpy.app.handlers import persistent
from bpy.props import IntProperty, StringProperty
from . import storage

bl_info = {
    "name": "JC History / JC 历史记录", "author": "JC", "version": (1, 0, 0),
    "blender": (5, 2, 0), "location": "3D 视图 > N 侧栏 > JC历史",
    "description": "常驻真实撤销历史、命名场景快照与恢复前自动备份",
    "category": "Interface",
}

_unsaved_id = uuid.uuid4().hex
_status = ""
_busy = False
_pending_path = None
_cache_key = None
_catalog = storage.empty_catalog()


def settings():
    addon = bpy.context.preferences.addons.get(__package__)
    return addon.preferences if addon else None


def root_path():
    prefs = settings()
    custom = prefs.storage_root if prefs else ""
    if custom:
        return Path(bpy.path.abspath(custom)).expanduser().resolve()
    return Path(bpy.utils.user_resource("CONFIG")) / "jc_history_data"


def current_bucket():
    root = root_path().resolve()
    current = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    # An opened snapshot belongs to its original catalog, even after a restart.
    if current and current.parent.parent == root:
        if (current.parent / "catalog.json").is_file():
            catalog = storage.read_catalog(current.parent)
            if (any(item["file"] == current.name for item in catalog["snapshots"])
                    or current.name in catalog.get("restores", [])):
                return current.parent
    return root / storage.project_key(bpy.data.filepath, _unsaved_id)


def get_catalog(force=False):
    global _cache_key, _catalog
    bucket = current_bucket()
    catalog_file = bucket / "catalog.json"
    stamp = catalog_file.stat().st_mtime_ns if catalog_file.exists() else 0
    key = (str(bucket), stamp)
    if force or key != _cache_key:
        _catalog = storage.read_catalog(bucket)
        _cache_key = key
    return bucket, _catalog


def invalidate():
    global _cache_key
    _cache_key = None


def notify(text):
    global _status
    _status = text
    redraw()


def redraw():
    wm = bpy.context.window_manager
    if wm:
        for window in wm.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D' and area.spaces.active.show_region_ui:
                    area.tag_redraw()


def capture_snapshot(name):
    """Save a copy without changing the current project, selection or undo stack."""
    global _busy
    if _busy:
        raise RuntimeError("正在处理快照，请稍候")
    if bpy.context.mode != 'OBJECT':
        raise RuntimeError("请先按 Tab 回到物体模式，再保存场景快照")
    _busy = True
    try:
        bucket, catalog = get_catalog(force=True)
        bucket.mkdir(parents=True, exist_ok=True)
        item = storage.new_entry(name)
        target = storage.entry_path(bucket, item)
        source_before = bpy.data.filepath
        result = bpy.ops.wm.save_as_mainfile(
            filepath=str(target), copy=True, compress=True,
            relative_remap=True, check_existing=False)
        if 'FINISHED' not in result or not target.is_file():
            raise RuntimeError("Blender 未完成快照保存")
        if bpy.data.filepath != source_before:
            raise RuntimeError("保存副本时当前工程路径发生变化，请检查文件标题")
        item["bytes"] = target.stat().st_size
        if not catalog["source"]:
            catalog["source"] = source_before
        catalog["snapshots"].append(item)
        storage.write_catalog(bucket, catalog)
        invalidate()
        notify("快照已保存，可从下方列表恢复。")
        return item
    finally:
        _busy = False


def finish_restore():
    global _busy, _pending_path
    path = _pending_path
    _pending_path = None
    try:
        if path is None:
            return None
        result = bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
        if 'FINISHED' not in result:
            raise RuntimeError("Blender 无法打开恢复副本")
        notify("已恢复；原快照保留，请另存为作品。")
    except Exception as exc:
        notify("恢复失败；恢复前备份已保留。" + str(exc))
    finally:
        _busy = False
        invalidate()
    return None


class JCH_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    storage_root: StringProperty(
        name="快照存放目录", subtype='DIR_PATH', default="",
        description="留空使用 Blender 配置目录；更换目录不会移动已有快照")
    snapshot_rows: IntProperty(name="面板显示的最近快照数", default=8, min=1, max=100)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "storage_root")
        layout.prop(self, "snapshot_rows")
        layout.label(text="快照为本机文件，不上传网络，也不会自动定时保存。")
        layout.label(text="修改存放目录后，原快照仍保留在旧目录。")


class JCH_OT_snapshot_add(bpy.types.Operator):
    bl_idname = "jch.snapshot_add"
    bl_label = "保存命名快照"
    bl_description = "将当前完整场景保存为独立副本，保留当前工程路径"
    name: StringProperty(name="快照名称", default="")

    @classmethod
    def poll(cls, context):
        return not _busy and context.mode == 'OBJECT' and not context.window_manager.is_interface_locked

    def invoke(self, context, event):
        self.name = datetime.now().strftime("阶段 %m-%d %H:%M:%S")
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        try:
            capture_snapshot(self.name)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            notify("快照保存失败：" + str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


class JCH_OT_snapshot_restore(bpy.types.Operator):
    bl_idname = "jch.snapshot_restore"
    bl_label = "恢复场景快照"
    bl_description = "先备份当前场景，再打开所选快照；恢复后请另存为作品"
    snapshot_id: StringProperty(options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return not _busy and context.mode == 'OBJECT' and not context.window_manager.is_interface_locked

    def invoke(self, context, event):
        try:
            _, catalog = get_catalog(force=True)
            item = storage.find_entry(catalog, self.snapshot_id)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return context.window_manager.invoke_confirm(
            self, event, title="恢复快照：" + item["name"],
            message="将先保存当前场景的备份，再打开快照。恢复后请另存为作品。",
            confirm_text="备份并恢复", icon='QUESTION')

    def execute(self, context):
        global _busy, _pending_path
        try:
            bucket, catalog = get_catalog(force=True)
            target = storage.entry_path(bucket, storage.find_entry(catalog, self.snapshot_id))
            if not target.is_file():
                raise RuntimeError("快照文件已丢失，未执行恢复")
            with target.open("rb") as file:
                header = file.read(7)
            # Blender compressed files can use zstd or gzip, besides raw BLENDER.
            if header != b'BLENDER' and not header.startswith((b'\x28\xb5\x2f\xfd', b'\x1f\x8b')):
                raise RuntimeError("快照文件头无效，未执行恢复")
            capture_snapshot(datetime.now().strftime("恢复前自动备份 %m-%d %H:%M:%S"))
            # Open a WORKING COPY in the same directory. Ctrl+S after restoring
            # can never overwrite the named snapshot. Same-directory placement
            # also preserves all relative external paths in the saved file.
            work_name = "work_" + uuid.uuid4().hex + ".blend"
            work_path = bucket / work_name
            with target.open("rb") as source, work_path.open("xb") as dest:
                shutil.copyfileobj(source, dest)
            _, updated_catalog = get_catalog(force=True)
            updated_catalog.setdefault("restores", []).append(work_name)
            storage.write_catalog(bucket, updated_catalog)
            _pending_path = str(work_path)
            _busy = True
            bpy.app.timers.register(finish_restore, first_interval=0.15)
        except Exception as exc:
            _busy = False
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


class JCH_OT_snapshot_rename(bpy.types.Operator):
    bl_idname = "jch.snapshot_rename"
    bl_label = "重命名快照"
    snapshot_id: StringProperty(options={'HIDDEN'})
    name: StringProperty(name="快照名称")

    def invoke(self, context, event):
        try:
            _, catalog = get_catalog(force=True)
            self.name = storage.find_entry(catalog, self.snapshot_id)["name"]
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        try:
            bucket, catalog = get_catalog(force=True)
            storage.find_entry(catalog, self.snapshot_id)["name"] = self.name.strip() or "未命名快照"
            storage.write_catalog(bucket, catalog)
            invalidate()
            redraw()
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


class JCH_OT_refresh(bpy.types.Operator):
    bl_idname = "jch.refresh"
    bl_label = "刷新"
    bl_description = "刷新快照目录和真实撤销历史"

    def execute(self, context):
        invalidate()
        redraw()
        return {'FINISHED'}


class JCH_OT_open_folder(bpy.types.Operator):
    bl_idname = "jch.open_folder"
    bl_label = "打开快照文件夹"

    def execute(self, context):
        try:
            bucket, _ = get_catalog(force=True)
            bucket.mkdir(parents=True, exist_ok=True)
            bpy.ops.wm.path_open(filepath=str(bucket))
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


class JCH_OT_save_work(bpy.types.Operator):
    bl_idname = "jch.save_work"
    bl_label = "另存为作品"
    bl_description = "将恢复的场景保存到你选择的位置，保留快照原件"

    def execute(self, context):
        try:
            _, catalog = get_catalog()
            source = catalog.get("source", "")
            base = Path(source) if source else Path.home() / "Documents" / "新作品.blend"
            filename = base.stem + datetime.now().strftime("_恢复_%Y%m%d_%H%M%S.blend")
            bpy.ops.wm.save_as_mainfile('INVOKE_DEFAULT', filepath=str(base.parent / filename))
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


class JCH_PT_history(bpy.types.Panel):
    bl_label = "操作历史"
    bl_idname = "JCH_PT_history"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "JC历史"

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator("ed.undo", text="撤销", icon='LOOP_BACK')
        row.operator("ed.redo", text="重做", icon='LOOP_FORWARDS')
        row.operator("jch.refresh", text="", icon='FILE_REFRESH')
        layout.label(text="点击回到该步 · 圆点标记当前位置", icon='INFO')
        if not context.preferences.edit.use_global_undo:
            box = layout.box()
            box.alert = True
            box.label(text="全局撤销未开启")
            box.prop(context.preferences.edit, "use_global_undo", text="开启全局撤销")
        if context.preferences.edit.undo_steps == 0:
            layout.label(text="撤销步数为 0，请在下方增加步数", icon='ERROR')
        box = layout.box()
        box.operator_context = 'EXEC_DEFAULT'
        # Native history menu: genuine stack indices/current marker, safe in edit,
        # sculpt and object modes. More than ~20 entries wrap into native columns.
        box.menu_contents("TOPBAR_MT_undo_history")


class JCH_PT_snapshots(bpy.types.Panel):
    bl_label = "场景快照"
    bl_idname = "JCH_PT_snapshots"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "JC历史"
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        layout.operator("jch.snapshot_add", text="保存命名快照", icon='ADD')
        if _status:
            # Short lines stay legible in a standard N-panel width.
            for offset in range(0, len(_status), 22):
                layout.label(text=_status[offset:offset + 22])
        if context.mode != 'OBJECT':
            layout.label(text="快照操作请先回到物体模式", icon='INFO')
        try:
            bucket, catalog = get_catalog()
        except Exception as exc:
            layout.label(text="读取快照目录失败", icon='ERROR')
            layout.label(text=str(exc)[:60])
            return
        current = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
        if current and current.parent == bucket.resolve():
            box = layout.box()
            box.label(text="当前为恢复工作副本", icon='INFO')
            box.operator("jch.save_work", icon='FILE_TICK')
        prefs = settings()
        count = prefs.snapshot_rows if prefs else 8
        items = catalog["snapshots"]
        if not items:
            layout.label(text="还没有快照。满意一个阶段时保存一次。")
        for item in reversed(items[-count:]):
            box = layout.box()
            row = box.row(align=True)
            row.label(text=item["name"], icon='BOOKMARKS')
            row.operator("jch.snapshot_rename", text="", icon='GREASEPENCIL').snapshot_id = item["id"]
            row = box.row(align=True)
            row.label(text=item["time"][5:16].replace("T", " "))
            row.operator("jch.snapshot_restore", text="恢复", icon='LOOP_BACK').snapshot_id = item["id"]
        if len(items) > count:
            layout.label(text=f"共 {len(items)} 个快照，显示最近 {count} 个")
            layout.label(text="可在插件偏好设置中增加显示数量")
        row = layout.row(align=True)
        row.operator("jch.open_folder", text="快照文件夹", icon='FILE_FOLDER')
        row.operator("jch.refresh", text="", icon='FILE_REFRESH')
        layout.label(text="快照会保留；普通撤销历史仅限本次会话。")


class JCH_PT_options(bpy.types.Panel):
    bl_label = "历史设置与说明"
    bl_idname = "JCH_PT_options"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "JC历史"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        layout.prop(context.preferences.edit, "undo_steps", text="撤销步数")
        layout.prop(context.preferences.edit, "undo_memory_limit", text="撤销内存上限 MB")
        layout.label(text="0 MB 表示不限制内存。步数越多，内存占用越高。")
        layout.label(text="回退后再修改，会清除后面的普通历史。")
        layout.label(text="历史较多时会分列，可拉宽侧栏查看。")
        layout.label(text="快照不打包外部贴图，请保留原素材文件。")


@persistent
def on_load(_):
    global _unsaved_id, _status
    if not bpy.data.filepath:
        _unsaved_id = uuid.uuid4().hex
    _status = ""
    invalidate()
    redraw()


def tick():
    # Only request redraws; the timer never scans operators, changes scenes,
    # captures screenshots, writes files, or inserts extra undo steps.
    if not _busy and not bpy.context.window_manager.is_interface_locked:
        redraw()
    return 0.75


CLASSES = (JCH_Preferences, JCH_OT_snapshot_add, JCH_OT_snapshot_restore,
           JCH_OT_snapshot_rename, JCH_OT_refresh, JCH_OT_open_folder,
           JCH_OT_save_work, JCH_PT_history, JCH_PT_snapshots, JCH_PT_options)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    if on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(on_load)
    if not bpy.app.timers.is_registered(tick):
        bpy.app.timers.register(tick, first_interval=0.75, persistent=True)


def unregister():
    global _busy, _pending_path
    if bpy.app.timers.is_registered(finish_restore):
        bpy.app.timers.unregister(finish_restore)
    _pending_path = None
    _busy = False
    if bpy.app.timers.is_registered(tick):
        bpy.app.timers.unregister(tick)
    if on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(on_load)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    invalidate()
