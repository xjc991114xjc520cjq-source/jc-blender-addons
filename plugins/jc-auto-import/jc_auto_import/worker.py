"""Executed only inside a disposable, factory-startup background Blender."""
from pathlib import Path
import json
import os
import shutil
import sys
import traceback

ROOT = Path(__file__).resolve().parent
if __package__:
    from . import core
else:
    sys.path.insert(0, str(ROOT))
    import core


def import_model(path):
    import bpy
    suffix = Path(path).suffix.lower()
    if suffix in ('.glb', '.gltf'):
        result = bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix == '.fbx':
        result = bpy.ops.import_scene.fbx(filepath=str(path), use_anim=True)
    elif suffix == '.obj':
        result = bpy.ops.wm.obj_import(filepath=str(path))
    elif suffix == '.stl':
        result = bpy.ops.wm.stl_import(filepath=str(path))
    elif suffix == '.ply':
        result = bpy.ops.wm.ply_import(filepath=str(path))
    elif suffix in ('.usd', '.usda', '.usdc', '.usdz'):
        result = bpy.ops.wm.usd_import(filepath=str(path))
    elif suffix == '.abc':
        result = bpy.ops.wm.alembic_import(filepath=str(path), as_background_job=False)
    else:
        raise RuntimeError('No Blender importer for ' + suffix)
    if 'FINISHED' not in result:
        raise RuntimeError('Blender importer cancelled')


def export_model(path, target):
    import bpy
    # Pack external textures into GLB/FBX wherever supported. OBJ uses COPY.
    if target == 'GLB':
        result = bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB')
    elif target == 'FBX':
        result = bpy.ops.export_scene.fbx(filepath=str(path), path_mode='COPY', embed_textures=True)
    else:
        result = bpy.ops.wm.obj_export(filepath=str(path), path_mode='COPY', export_materials=True)
    if 'FINISHED' not in result or not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError('Exporter did not produce a nonempty model')


def main(job_path):
    import bpy
    job = json.loads(job_path.read_text(encoding='utf-8'))
    status = job_path.parent / 'status.json'
    result = job_path.parent / 'result.json'
    def progress(message):
        core.atomic_json(status, {'message': message})
    work = None
    try:
        source = Path(job['source']).resolve(strict=True)
        if not source.is_file():
            raise ValueError('源路径不是文件')
        target = job['target']
        if target not in core.TARGETS:
            raise ValueError('Invalid target')
        backend = core.backend_for(source)
        missing = core.requirement(source)
        if missing:
            raise RuntimeError(missing)
        progress('正在检查源文件与缓存…')
        key = core.fingerprint(source, target, bpy.app.version_string)
        cache = Path(job['cache']).resolve()
        # Cache must not be under the model asset tree (it invalidates itself).
        if source.parent == cache or source.parent in cache.parents:
            raise RuntimeError('缓存目录不能放在源模型目录内。')
        cache.mkdir(parents=True, exist_ok=True)
        final = cache / key
        output_name = 'model' + core.TARGETS[target]
        output = final / output_name
        manifest = final / 'manifest.json'
        if job['reuse'] and manifest.is_file() and output.is_file():
            metadata = json.loads(manifest.read_text(encoding='utf-8'))
            if output.stat().st_size > 0 and all((final / entry).is_file() for entry in metadata['files']):
                core.atomic_json(result, dict(metadata, output=str(output), cached=True))
                return
        work = cache / (key + '-' + job_path.parent.name + '.partial')
        work.mkdir(exist_ok=False)
        output = work / output_name
        warnings = []
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        progress('正在使用 %s 转换…' % backend)
        if backend == '3ds':
            import three_ds
            warnings.extend(three_ds.load(source))
        elif backend == 'native':
            import_model(source)
        elif backend == 'max':
            from vendor import import_max
            if not import_max.is_maxfile(str(source)):
                raise RuntimeError('不是有效的 MAX 文件，不能通过更改后缀转换。')
            # read() avoids UI cursor operations in the upstream load() wrapper.
            from mathutils import Matrix
            import_max.read(bpy.context, str(source), Matrix.Identity(4),
                            {'MATERIAL', 'UV', 'PRIMITIVE', 'EMPTY', 'ARMATURE'}, True, True)
            warnings.append('MAX 独立读取器：仅恢复可识别网格、基础材质、UV 与部分基本体；不执行修改器或第三方插件。')
        else:
            intermediate = work / 'bridge.glb'
            command = [core.engines()[backend], 'export', str(source), str(intermediate), '-fglb2', '-l']
            try:
                core.run_external(command, job['timeout'], job_path.parent / 'engine.log', cwd=str(source.parent))
            except RuntimeError:
                # Some source skin/animation structures cannot pass through the
                # Assimp GLB exporter. Recover static geometry through OBJ.
                (work / 'bridge.glb').unlink(missing_ok=True)
                intermediate = work / 'bridge.obj'
                command = [core.engines()[backend], 'export', str(source), str(intermediate), '-fobj', '-ptv', '-l']
                core.run_external(command, job['timeout'], job_path.parent / 'engine.log', cwd=str(source.parent))
                warnings.append('GLB 中间转换失败，已使用 OBJ 恢复静态网格；该文件的动画 / 骨骼未保留。')
            if backend == 'c4d':
                warnings.append('C4D 独立读取依赖文件内的多边形缓存；不执行生成器、MoGraph 或第三方渲染器。')
            if not intermediate.is_file() or not intermediate.stat().st_size:
                raise RuntimeError('引擎没有生成模型，请查看 engine.log。')
            import_model(intermediate)
            warnings.append('独立格式转换可能简化材质与动画，请检查导入结果。')
        if not any(obj.type == 'MESH' and len(obj.data.vertices) for obj in bpy.context.scene.objects):
            raise RuntimeError('文件中没有可恢复的网格。可能缺少缓存，或使用了不支持的对象类型。')
        progress('正在打包 %s 与纹理…' % target)
        for image in bpy.data.images:
            if image.source == 'FILE' and not image.packed_file:
                try:
                    image.pack()
                except RuntimeError:
                    warnings.append('无法打包纹理：' + image.name)
        export_model(output, target)
        # Store only final exports, never proprietary intermediate scene data.
        for name in ('bridge.json', 'bridge.fbx', 'bridge.glb', 'bridge.obj', 'bridge.mtl'):
            (work / name).unlink(missing_ok=True)
        files = [str(p.relative_to(work)) for p in work.rglob('*') if p.is_file()]
        metadata = dict(backend=backend, target=target, warnings=warnings, files=files,
                        objects=len(bpy.context.scene.objects), cached=False)
        core.atomic_json(work / 'manifest.json', metadata)
        # A bypass-cache run uses its own completed directory, avoiding replacement
        # of files that another Blender instance may still be using.
        if final.exists():
            final = cache / (key + '-' + job_path.parent.name)
        work.rename(final)
        work = None
        core.atomic_json(result, dict(metadata, output=str(final / output_name)))
    except Exception as error:
        core.atomic_json(result, {'error': str(error), 'traceback': traceback.format_exc()})
        raise
    finally:
        if work and work.is_dir():
            shutil.rmtree(work)


if __name__ == '__main__':
    main(Path(sys.argv[sys.argv.index('--') + 1]))
