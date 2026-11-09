# SPDX-License-Identifier: GPL-3.0-or-later
"""JC Auto Import: native Blender UI, independent offline converters."""
import json
from pathlib import Path
import shutil
import tempfile
import time

import bpy
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty, StringProperty
from bpy_extras.io_utils import poll_file_object_drop
from . import core

bl_info = {'name': 'JC 自动转换导入', 'author': 'JC', 'version': (1, 0, 1),
           'blender': (4, 2, 0), 'location': 'File > Import / 3D View > Sidebar > JC',
           'description': 'Offline format conversion and import without Cinema 4D or 3ds Max',
           'category': 'Import-Export'}

_active = None
_message = '就绪 · 无需安装原软件'
_last_run = ''
_last_output = ''


def redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def settings(context):
    addon = context.preferences.addons.get(__package__)
    return addon.preferences if addon else None


def cache_path(context):
    prefs = settings(context)
    configured = prefs.cache_directory if prefs else ''
    return Path(bpy.path.abspath(configured)) if configured else Path(bpy.utils.user_resource('DATAFILES', path='jc_auto_import', create=True)) / 'cache'


def sources(operator):
    if operator.files and operator.directory:
        return list(dict.fromkeys(str(Path(operator.directory, item.name).resolve()) for item in operator.files))
    return [str(Path(bpy.path.abspath(operator.filepath)).resolve())] if operator.filepath else []


class JCImportPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    cache_directory: StringProperty(name='转换缓存', subtype='DIR_PATH', description='留空使用 Blender 用户数据目录；不要放入模型素材目录')
    timeout: IntProperty(name='单个文件超时（秒）', default=300, min=30, max=3600)
    def draw(self, context):
        layout = self.layout
        layout.label(text='独立离线转换 · 不调用 C4D / 3ds Max · 不上传模型', icon='CHECKMARK')
        layout.prop(self, 'cache_directory')
        layout.prop(self, 'timeout')
        layout.label(text='MAX / C4D 只恢复独立读取器能够识别的数据。', icon='INFO')
        layout.operator('jc_auto_import.help', icon='HELP')


class JCImportHelp(bpy.types.Operator):
    bl_idname = 'jc_auto_import.help'
    bl_label = '格式与兼容性说明'
    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=520)
    def draw(self, context):
        layout = self.layout
        for line in ('将模型拖入三维视图，或使用「文件 → 导入 → JC 自动转换导入」。',
                     'GLB：适合基础 PBR 材质；FBX：适合层级与可恢复的动画；OBJ：静态网格。',
                     'MAX：支持部分网格、基本体、材质与 UV，不计算原软件修改器。',
                     'C4D：读取已保存的网格及缓存；不能重新计算 MoGraph / 生成器。',
                     'DWG / SKP / IGES 等没有内置读取器的格式会明确提示，不调用原软件。',
                     '转换在后台运行，可在右侧 JC 面板取消；已导入的文件可用原生撤销。',
                     '转换缓存保留纹理，源文件不修改；模型不会上传网络。'):
            layout.label(text=line)
    def execute(self, context):
        return {'FINISHED'}


class JCImportChoose(bpy.types.Operator):
    """选择需要转换的模型文件"""
    bl_idname = 'jc_auto_import.choose'
    bl_label = 'JC 自动转换导入'
    filepath: StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE'})
    directory: StringProperty(subtype='DIR_PATH', options={'SKIP_SAVE'})
    files: CollectionProperty(type=bpy.types.OperatorFileListElement, options={'SKIP_SAVE'})
    filter_glob: StringProperty(default='*.*', options={'HIDDEN'})
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    def execute(self, context):
        args = {'filepath': self.filepath, 'directory': self.directory,
                'files': [{'name': item.name} for item in self.files]}
        result = bpy.ops.jc_auto_import.convert('INVOKE_DEFAULT', **args)
        return {'FINISHED'} if result & {'RUNNING_MODAL', 'FINISHED'} else {'CANCELLED'}


class JCImportConvert(bpy.types.Operator):
    """后台转换后导入当前场景，不需要安装源软件"""
    bl_idname = 'jc_auto_import.convert'
    bl_label = '转换并导入'
    bl_options = {'INTERNAL', 'UNDO'}
    filepath: StringProperty(subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'})
    directory: StringProperty(subtype='DIR_PATH', options={'HIDDEN', 'SKIP_SAVE'})
    files: CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'})
    target: EnumProperty(name='转换格式', items=[('GLB', 'GLB', '材质与几何体，推荐'), ('FBX', 'FBX', '层级与可恢复的动画'), ('OBJ', 'OBJ', '静态几何体与基础材质')], default='GLB')
    reuse: BoolProperty(name='复用转换缓存', default=True, description='源文件或相邻素材变化后会重新转换')
    scale: FloatProperty(name='导入缩放', default=1.0, min=0.000001, max=1000000.0)
    _process = None
    _timer = None
    _run = None
    _queue = None
    _done = 0
    _cancel_requested = False
    _warnings = None

    def invoke(self, context, event):
        if _active:
            self.report({'WARNING'}, '已有转换任务，请等待完成或取消。')
            return {'CANCELLED'}
        if not sources(self):
            return bpy.ops.jc_auto_import.choose('INVOKE_DEFAULT')
        return context.window_manager.invoke_props_dialog(self, width=510, title='JC 自动转换导入', confirm_text='转换并导入')

    def draw(self, context):
        layout = self.layout
        paths = sources(self)
        layout.label(text=Path(paths[0]).name if len(paths) == 1 else '%d 个模型文件' % len(paths), icon='FILE_3D')
        layout.label(text='独立离线转换 · 无需安装 C4D / 3ds Max', icon='CHECKMARK')
        layout.separator()
        layout.prop(self, 'target', expand=True)
        layout.prop(self, 'scale')
        layout.prop(self, 'reuse')
        suffixes = {Path(path).suffix.lower() for path in paths}
        if '.max' in suffixes:
            layout.label(text='MAX：恢复支持的网格 / UV / 基础材质，不能计算修改器。', icon='INFO')
        if '.c4d' in suffixes:
            layout.label(text='C4D：需有可读取网格或缓存，不计算生成器与 MoGraph。', icon='INFO')
        if '.3ds' in suffixes:
            layout.label(text='3DS：静态网格、UV、基础材质，不保留动画。', icon='INFO')
        for path in paths:
            error = core.requirement(path)
            if error:
                box = layout.box()
                box.alert = True
                box.label(text=Path(path).suffix.upper() + '：' + error, icon='ERROR')

    def execute(self, context):
        global _active, _message
        if _active:
            self.report({'WARNING'}, '已有转换任务。')
            return {'CANCELLED'}
        self._queue = sources(self)
        if not self._queue:
            return {'CANCELLED'}
        for source in self._queue:
            error = core.requirement(source)
            if error or not Path(source).is_file():
                self.report({'ERROR'}, error or '源文件不存在：' + source)
                return {'CANCELLED'}
            cache = cache_path(context).resolve()
            folder = Path(source).parent.resolve()
            if folder == cache or folder in cache.parents:
                self.report({'ERROR'}, '缓存不能位于源模型目录内，请在插件设置中修改。')
                return {'CANCELLED'}
        self._done = 0
        self._warnings = []
        self._cancel_requested = False
        self._started = time.monotonic()
        self._window = context.window
        self._scene = context.scene
        self._view_layer = context.view_layer
        self._cache = cache_path(context).resolve()
        _active = self
        try:
            self._launch(context)
            self._timer = context.window_manager.event_timer_add(0.25, window=context.window)
            context.window_manager.modal_handler_add(self)
        except Exception as error:
            self._finish(context)
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        _message = '正在启动独立转换…'
        redraw()
        return {'RUNNING_MODAL'}

    def _launch(self, context):
        global _last_run
        self._run = Path(tempfile.mkdtemp(prefix='jc-import-'))
        _last_run = str(self._run)
        prefs = settings(context)
        self._timeout = prefs.timeout if prefs else 300
        self._file_started = time.monotonic()
        job = dict(source=self._queue[self._done], target=self.target, cache=str(self._cache),
                   reuse=self.reuse, timeout=self._timeout)
        core.atomic_json(self._run / 'job.json', job)
        command = [bpy.app.binary_path, '--background', '--factory-startup', '--disable-autoexec',
                   '--python-exit-code', '1', '--python', str(core.ROOT / 'worker.py'), '--', str(self._run / 'job.json')]
        self._process = core.spawn(command, self._run / 'worker.log')

    def _finish(self, context):
        global _active
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        if _active == self:
            _active = None
        if self._window:
            self._window.workspace.status_text_set(None)
        redraw()

    def cancel(self, context):
        if _active is self:
            self._stop(context, '已取消转换。')

    def _stop(self, context, message):
        global _message
        core.stop_process(self._process)
        # Only remove this job's partial cache, never completed caches or source.
        for partial in self._cache.glob('*-' + self._run.name + '.partial'):
            if partial.resolve().parent == self._cache:
                shutil.rmtree(partial)
        _message = message
        self._finish(context)
        # Successful files in a cancelled batch still need an undo entry.
        return {'FINISHED'} if self._done else {'CANCELLED'}

    def modal(self, context, event):
        global _message, _last_output
        if event.type == 'ESC' or self._cancel_requested:
            return self._stop(context, '已取消 · 已导入 %d 个文件' % self._done)
        if event.type != 'TIMER':
            return {'PASS_THROUGH'}
        if self._window.scene != self._scene:
            return self._stop(context, '场景已切换，转换已取消。')
        if time.monotonic() - self._file_started > self._timeout + 30:
            self.report({'ERROR'}, '转换超时，详情见日志。')
            return self._stop(context, '转换超时')
        status = self._run / 'status.json'
        if status.is_file():
            try:
                phase = json.loads(status.read_text(encoding='utf-8'))['message']
                _message = '%d/%d · %s · %.0f 秒' % (self._done + 1, len(self._queue), phase, time.monotonic() - self._started)
                self._window.workspace.status_text_set('JC ' + _message + '  |  Esc 取消')
            except (OSError, ValueError, KeyError):
                pass
        redraw()
        if self._process.poll() is None:
            return {'PASS_THROUGH'}
        try:
            result_path = self._run / 'result.json'
            if not result_path.is_file():
                raise RuntimeError('独立引擎未返回结果，请打开日志检查。')
            result = json.loads(result_path.read_text(encoding='utf-8'))
            if result.get('error') or self._process.returncode:
                raise RuntimeError(result.get('error', '转换进程失败'))
            output = Path(result['output']).resolve(strict=True)
            if self._cache not in output.parents:
                raise RuntimeError('转换结果路径不在缓存目录内')
            self._import(context, output, self._queue[self._done])
            _last_output = str(output)
            self._warnings.extend(result.get('warnings', []))
            self._done += 1
            if self._done < len(self._queue):
                self._launch(context)
                return {'PASS_THROUGH'}
            _message = '已导入 %d 个文件 · %.1f 秒' % (self._done, time.monotonic() - self._started)
            self.report({'INFO'}, _message)
            if self._warnings:
                self.report({'WARNING'}, '部分源数据可能无法恢复，详情见转换日志。')
            self._finish(context)
            return {'FINISHED'}
        except Exception as error:
            self.report({'ERROR'}, str(error))
            return self._stop(context, '失败：' + str(error))

    def _import(self, context, output, source):
        from .worker import import_model
        buckets = ('objects', 'collections', 'meshes', 'materials', 'images', 'armatures', 'actions', 'cameras', 'lights', 'curves')
        before = {name: set(getattr(bpy.data, name)) for name in buckets}
        collection = bpy.data.collections.new(Path(source).stem)
        self._scene.collection.children.link(collection)
        self._view_layer.update()
        previous_layer = self._view_layer.active_layer_collection
        self._view_layer.active_layer_collection = self._view_layer.layer_collection.children[collection.name]
        try:
            with context.temp_override(window=self._window, scene=self._scene, view_layer=self._view_layer, collection=collection):
                import_model(output)
            objects = set(bpy.data.objects) - before['objects']
            if not objects:
                raise RuntimeError('导入器未创建对象')
            from mathutils import Matrix
            for obj in objects:
                if obj.parent not in objects:
                    obj.matrix_world = Matrix.Scale(self.scale, 4) @ obj.matrix_world
        except Exception:
            created = [item for name in buckets for item in set(getattr(bpy.data, name)) - before[name]]
            bpy.data.batch_remove(ids=created)
            raise
        finally:
            self._view_layer.active_layer_collection = previous_layer


class JCImportCancel(bpy.types.Operator):
    bl_idname = 'jc_auto_import.cancel'
    bl_label = '取消转换'
    def execute(self, context):
        if _active:
            _active._cancel_requested = True
        return {'FINISHED'}


class JCImportOpenLog(bpy.types.Operator):
    bl_idname = 'jc_auto_import.open_log'
    bl_label = '打开转换日志'
    def execute(self, context):
        if _last_run and Path(_last_run).is_dir():
            bpy.ops.wm.path_open(filepath=_last_run)
        return {'FINISHED'}


class JCImportOpenOutput(bpy.types.Operator):
    bl_idname = 'jc_auto_import.open_output'
    bl_label = '打开转换后的文件夹'
    def execute(self, context):
        if _last_output and Path(_last_output).is_file():
            bpy.ops.wm.path_open(filepath=str(Path(_last_output).parent))
        return {'FINISHED'}


class JCImportPanel(bpy.types.Panel):
    bl_label = '自动转换导入'
    bl_idname = 'JC_PT_auto_import'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'JC'
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.enabled = _active is None
        row.operator('jc_auto_import.choose', icon='IMPORT', text='选择模型并转换')
        layout.label(text=_message[:62], icon='TIME' if _active else 'INFO')
        if _active:
            layout.operator('jc_auto_import.cancel', icon='CANCEL')
        if _last_run:
            layout.operator('jc_auto_import.open_log', icon='TEXT')
        if _last_output:
            layout.operator('jc_auto_import.open_output', icon='FILE_FOLDER')
        layout.operator('jc_auto_import.help', icon='HELP')


class JCImportFileHandler(bpy.types.FileHandler):
    bl_idname = 'JC_FH_auto_import'
    bl_label = 'JC 自动转换导入'
    bl_import_operator = 'jc_auto_import.convert'
    bl_file_extensions = ';'.join(core.external_extensions())
    @classmethod
    def poll_drop(cls, context):
        return _active is None and poll_file_object_drop(context)


_classes = (JCImportPreferences, JCImportHelp, JCImportChoose, JCImportConvert, JCImportCancel,
            JCImportOpenLog, JCImportOpenOutput, JCImportPanel, JCImportFileHandler)


def menu(self, context):
    self.layout.operator(JCImportChoose.bl_idname, text='JC 自动转换导入', icon='IMPORT')


@bpy.app.handlers.persistent
def before_load(_unused):
    if _active:
        _active._stop(bpy.context, '场景已关闭，转换已取消。')


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu)
    bpy.app.handlers.load_pre.append(before_load)


def unregister():
    global _active
    if _active:
        _active._stop(bpy.context, '插件已停用，转换已取消。')
    bpy.types.TOPBAR_MT_file_import.remove(menu)
    if before_load in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(before_load)
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
