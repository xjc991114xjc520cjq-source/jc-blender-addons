"""Experimental, data-only KeyShot DAL 024 mesh reader.

No KeyShot libraries, commands or executable paths from a scene are loaded.
Saved polygon representations take precedence over the accompanying NURBS
representation in the same geometry group. Unsupported representations fail.
"""
from pathlib import Path, PurePosixPath
from array import array
import ctypes
import math
import re
import struct
import zipfile

ROOT = Path(__file__).resolve().parent
MAX_BYTES = 512 * 1024 * 1024
IDENTITY = (1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.)
SUPPRESSED_GEOMETRY = 0x400000


class KeyShotError(ValueError):
    pass


def text(data):
    return bytes(data).decode('utf-8', errors='replace')


def decompress(data, limit):
    """Use the already bundled, trusted Zstandard DLL with bounded output."""
    class Buffer(ctypes.Structure):
        _fields_ = [('data', ctypes.c_void_p), ('size', ctypes.c_size_t), ('pos', ctypes.c_size_t)]
    candidates = list((ROOT / 'bin/cad/packages/cadquery_ocp_novtk.libs').glob('zstd-*.dll'))
    if len(candidates) != 1:
        raise KeyShotError('安装包中的 Zstandard 组件缺失或不唯一。')
    library = ctypes.CDLL(str(candidates[0]))
    for name, args, result in (
            ('ZSTD_createDStream', [], ctypes.c_void_p),
            ('ZSTD_freeDStream', [ctypes.c_void_p], ctypes.c_size_t),
            ('ZSTD_initDStream', [ctypes.c_void_p], ctypes.c_size_t),
            ('ZSTD_DCtx_setParameter', [ctypes.c_void_p, ctypes.c_int, ctypes.c_int], ctypes.c_size_t),
            ('ZSTD_decompressStream', [ctypes.c_void_p, ctypes.POINTER(Buffer), ctypes.POINTER(Buffer)], ctypes.c_size_t),
            ('ZSTD_isError', [ctypes.c_size_t], ctypes.c_uint),
            ('ZSTD_getErrorName', [ctypes.c_size_t], ctypes.c_char_p)):
        function = getattr(library, name)
        function.argtypes, function.restype = args, result
    def check(code):
        if library.ZSTD_isError(code):
            raise KeyShotError('BIP 压缩数据损坏：' + library.ZSTD_getErrorName(code).decode('ascii', 'replace'))
        return code
    context = library.ZSTD_createDStream()
    if not context:
        raise KeyShotError('无法分配解压内存。')
    try:
        check(library.ZSTD_initDStream(context))
        check(library.ZSTD_DCtx_setParameter(context, 100, 27))  # max 128 MiB window
        source = ctypes.create_string_buffer(bytes(data))
        incoming = Buffer(ctypes.cast(source, ctypes.c_void_p), len(data), 0)
        target = ctypes.create_string_buffer(1024 * 1024)
        output = bytearray()
        remaining = 1
        while incoming.pos < incoming.size or remaining:
            previous = incoming.pos
            outgoing = Buffer(ctypes.cast(target, ctypes.c_void_p), len(target), 0)
            remaining = check(library.ZSTD_decompressStream(context, ctypes.byref(outgoing), ctypes.byref(incoming)))
            if len(output) + outgoing.pos > limit:
                raise KeyShotError('BIP 解压数据超过本版本 512 MiB 限制。')
            output.extend(target.raw[:outgoing.pos])
            if incoming.pos == previous and not outgoing.pos:
                raise KeyShotError('BIP 压缩数据被截断。')
        return output
    finally:
        library.ZSTD_freeDStream(context)


def record(data, position):
    start = position
    if position >= len(data):
        raise KeyShotError('BIP 记录被截断。')
    raw = data[position]
    width = 1 if raw & 1 else 4
    position += 1
    if position + width > len(data):
        raise KeyShotError('BIP 记录长度被截断。')
    length = int.from_bytes(data[position:position + width], 'little')
    position += width
    end = position + length
    if end > len(data):
        raise KeyShotError('BIP 记录超出文件边界：%d。' % start)
    return raw & 254, data[position:end], end


def records(data):
    position = 0
    while position < len(data):
        op, value, position = record(data, position)
        yield op, value


def read_source(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise KeyShotError('KeyShot 源文件超过本版本 512 MiB 限制。')
    if path.suffix.lower() != '.ksp':
        return path.read_bytes()
    # Read members directly: no extraction or archive-supplied filesystem paths.
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > 10000 or sum(x.file_size for x in entries) > MAX_BYTES:
                raise KeyShotError('KSP 解包大小或文件数量超过本版本限制。')
            for member in entries:
                name = member.filename.replace('\\', '/')
                parts = PurePosixPath(name)
                if parts.is_absolute() or '..' in parts.parts or ':' in name or member.flag_bits & 1:
                    raise KeyShotError('不支持加密 KSP 或含越界路径的包。')
            scenes = [x for x in entries if x.filename.lower().endswith('.bip')]
            if len(scenes) != 1:
                raise KeyShotError('KSP 需要恰好包含一个 BIP 场景；此包无法自动确定场景。')
            return archive.read(scenes[0])
    except zipfile.BadZipFile as error:
        raise KeyShotError('不是本版本可读取的 ZIP 型 KSP 包。') from error


def dal_records(data):
    header = re.match(rb'//---luxion:dal:(\d+)---\r?\n', data[:80])
    if not header:
        raise KeyShotError('不是可识别的 KeyShot BIP 文件。')
    if header[1] != b'024':
        raise KeyShotError('当前 KeyShot 独立读取器仅验证 DAL 024；此文件为 DAL %s，不能保证全版本兼容。' % text(header[1]))
    # DAL 024 has a variable metadata preamble before the first segment. Locate
    # only a bounded, structurally validated raw segment, never arbitrary strings.
    start = -1
    for position in range(header.end(), min(len(data) - 18, 4096)):
        if data[position:position + 2] != b'\x87\x10':
            continue
        length, mode = struct.unpack_from('<QQ', data, position + 2)
        begin = position + 18
        end = begin + length
        if mode == 0x40000 and length and end + 2 <= len(data) and data[end:end + 2] == b'\x89\x00' and data[begin] in (0x6a, 0x6b):
            start = position
            break
    if start < 0:
        raise KeyShotError('此 DAL 024 文件封装尚未支持，或文件已损坏。')
    position = start
    total = 0
    while position < len(data):
        op, value, position = record(data, position)
        if op == 0x86:
            if len(value) != 16:
                raise KeyShotError('BIP 段头长度错误。')
            length, mode = struct.unpack('<QQ', value)
            end = position + length
            if length > MAX_BYTES or end + 2 > len(data) or data[end:end + 2] != b'\x89\x00':
                raise KeyShotError('BIP 段被截断。')
            block = data[position:end]
            position = end + 2
            if mode in (8, 0x10008):
                block = decompress(block, MAX_BYTES - total)
            elif mode != 0x40000:
                raise KeyShotError('未支持的 BIP 段编码。')
            total += len(block)
            if total > MAX_BYTES:
                raise KeyShotError('BIP 解包数据超过本版本 512 MiB 限制。')
            yield from records(memoryview(block))
        elif op == 0x88:
            raise KeyShotError('BIP 出现未配对的段结束标记。')
        else:
            yield op, value


def numeric_array(value, code):
    if len(value) < 4:
        raise KeyShotError('BIP 数组头损坏。')
    length = int.from_bytes(value[:4], 'little')
    if length > len(value) - 4:
        raise KeyShotError('BIP 数组名称长度错误。')
    name = text(value[4:4 + length])
    result = array(code)
    raw = value[4 + length:]
    if len(raw) % result.itemsize:
        raise KeyShotError('BIP 数组大小错误：' + name)
    result.frombytes(raw)
    return name, result


def parse(path):
    scene = {'roots': [], 'definitions': {}, 'settings': {}, 'materials': {}, 'shaders': {}, 'colors': {}, 'cameras': []}
    stack = []
    current = None
    shader = material = None
    color_node = None
    matrix_key = None
    for op, value in dal_records(read_source(path)):
        if op == 0x02:
            current = {'name': text(value), 'props': {}, 'transforms': {}, 'kind': 'camera'}
            scene['cameras'].append(current)
        elif op == 0x04:
            current = None
        elif op in (0x54, 0x4a, 0x4c):
            node = {'name': text(value), 'kind': {0x54: 'group', 0x4a: 'instance', 0x4c: 'definition'}[op],
                    'children': [], 'props': {}, 'arrays': {}, 'transforms': {}, 'flags': 0}
            if op != 0x4c:
                (stack[-1]['children'] if stack else scene['roots']).append(node)
            stack.append(node)
            current = node
        elif op in (0x58, 0x4e):
            kind = 'group' if op == 0x58 else ('definition', 'instance')
            if not stack or stack[-1]['kind'] not in ((kind,) if isinstance(kind, str) else kind):
                raise KeyShotError('BIP 场景层级未配对。')
            node = stack.pop()
            if node['kind'] == 'definition':
                if node.get('id') in scene['definitions'] or 'id' not in node:
                    raise KeyShotError('BIP 几何定义 ID 重复或缺失。')
                scene['definitions'][node['id']] = node
            current = stack[-1] if stack else None
            matrix_key = None
        elif op == 0x5a and current is not None:
            current['geometry'] = text(value)
        elif op == 0x38 and current is not None:
            if len(value) != 4:
                raise KeyShotError('BIP ID 大小错误。')
            current['id'] = int.from_bytes(value, 'little')
        elif op == 0x9c:
            color_node = {'props': {}}
        elif op == 0x9e:
            color_node = None
        elif op == 0x38 and color_node is not None:
            scene['colors'][int.from_bytes(value, 'little')] = color_node
        elif op == 0x3a and current is not None:
            current['flags'] = int.from_bytes(value, 'little')
        elif op == 0x5e and current is not None:
            matrix_key = text(value)
        elif op in (0x60, 0x72) and current is not None:
            if len(value) != 128:
                raise KeyShotError('BIP 变换矩阵大小错误。')
            matrix = struct.unpack('<16d', value)
            if not all(math.isfinite(x) for x in matrix):
                raise KeyShotError('BIP 含无效变换矩阵。')
            current['transforms'][matrix_key if op == 0x60 else 'local'] = matrix
            matrix_key = None
        elif op == 0x6e and current is not None:
            current['material'] = int.from_bytes(value, 'little')
        elif op in (0x74, 0x78, 0x7a, 0x7c, 0x7e) and current is not None:
            # Keep only saved triangle arrays. NURBS data is never interpreted
            # as polygons, nor silently imported over an existing mesh cache.
            if current.get('geometry') == 'triangles':
                name, numbers = numeric_array(value, {0x74: 'f', 0x78: 'f', 0x7a: 'd', 0x7c: 'i', 0x7e: 'i'}[op])
                current['arrays'][name] = numbers
        elif op in (0x74, 0x78, 0x7a, 0x7c, 0x7e) and shader is not None:
            name, numbers = numeric_array(value, {0x74: 'f', 0x78: 'f', 0x7a: 'd', 0x7c: 'i', 0x7e: 'i'}[op])
            shader['props'][name] = numbers
        elif op == 0x06:
            if len(value) < 4:
                raise KeyShotError('BIP 着色器头损坏。')
            shader = {'type': text(value[4:]), 'props': {}}
            # Camera-local environment shaders reuse IDs from the material
            # shader pool; they must not overwrite actual material definitions.
            ident = int.from_bytes(value[:4], 'little')
            if shader['type'] != 'lux_envmap' and (current is None or current.get('kind') != 'camera'):
                if ident in scene['shaders']:
                    raise KeyShotError('BIP 材质着色器 ID 重复。')
                scene['shaders'][ident] = shader
        elif op == 0x08:
            shader = None
        elif op == 0x0a:
            material = {'name': text(value), 'props': {}}
        elif op == 0x0e:
            material = None
        elif op == 0x38 and material is not None and 'id' not in material:
            material['id'] = int.from_bytes(value, 'little')
            scene['materials'][material['id']] = material
        elif op == 0x10 and material is not None and len(value) == 8:
            material['shader'] = int.from_bytes(value[4:], 'little')
        elif op in (0x16, 0x1a, 0x1c, 0x24, 0x26, 0x28, 0x2a, 0x2c, 0x2e, 0x3c, 0x30, 0x32, 0x9a, 0xa0):
            props = current['props'] if current else shader['props'] if shader else color_node['props'] if color_node else material['props'] if material else scene['settings']
            if op in (0x2e, 0x3c):
                if len(value) < 4:
                    raise KeyShotError('BIP 字符串头损坏。')
                length = int.from_bytes(value[:4], 'little')
                if length > len(value) - 4:
                    raise KeyShotError('BIP 字符串长度错误。')
                name, result = text(value[4 + length:]), text(value[4:4 + length])
            else:
                fmt = {0x16: '<f', 0x1a: '<4f', 0x1c: '<i', 0x24: '<i', 0x26: '<3f', 0x28: '<4f', 0x2a: '<3d', 0x2c: '<16d', 0x30: '<I', 0x32: '<I', 0x9a: '<I', 0xa0: '<I'}[op]
                size = struct.calcsize(fmt)
                if len(value) < size:
                    raise KeyShotError('BIP 属性被截断。')
                result = struct.unpack_from(fmt, value)
                result = result[0] if len(result) == 1 else result
                name = text(value[size:])
                if op in (0x30, 0x32, 0x9a):
                    result = ('shader', result)
                elif op == 0xa0:
                    result = ('color', result)
            props[name] = result
            if current and current['kind'] == 'instance' and name == 'id' and isinstance(result, int):
                props[name] = result & 0xffffffff
    if stack:
        raise KeyShotError('BIP 场景层级被截断。')
    if not scene['roots']:
        raise KeyShotError('BIP 没有可读取的场景。')
    return scene


def select_roots(scene, model_set=''):
    sets = [node for node in scene['roots'] if 'model set' in node['props']]
    if not sets:
        if model_set:
            raise KeyShotError('此 BIP 没有可选择的模型集。')
        return scene['roots'], ''
    chosen = model_set or str(scene['settings'].get('active_scene_set', ''))
    matches = [node for node in sets if chosen in (node['name'], str(node['props']['model set']))]
    if len(matches) != 1:
        raise KeyShotError('无法唯一确定 KeyShot 模型集“%s”。可选：%s。' %
                           (chosen, '、'.join(node['name'] for node in sets)))
    return matches, matches[0]['name']


def mesh_plan(scene, roots):
    """Resolve everything before mutating Blender; never deduplicate instances."""
    count = 0
    represented_nurbs = 0
    def visit(node):
        nonlocal count, represented_nurbs
        if node['flags'] & SUPPRESSED_GEOMETRY:
            return
        if node['kind'] != 'group':
            raise KeyShotError('不支持位于组外的 KeyShot 实例。')
        triangles, nurbs = [], []
        for child in node['children']:
            if child['flags'] & SUPPRESSED_GEOMETRY:
                continue
            if child['kind'] == 'group':
                visit(child)
                continue
            ref = child['props'].get('id')
            definition = scene['definitions'].get(ref)
            if definition is None:
                raise KeyShotError('BIP 实例引用缺失：%s。' % ref)
            geometry = definition.get('geometry')
            if geometry == 'triangles':
                validate_mesh(definition)
                triangles.append(child)
            elif geometry == 'nurbs':
                nurbs.append(child)
            else:
                raise KeyShotError('当前 KeyShot 读取器不支持几何：%s。' % geometry)
        if nurbs and not triangles:
            raise KeyShotError('零件“%s”仅包含 NURBS，未保存对应三角网格；已停止，避免缺件。' % node['name'])
        count += len(triangles)
        represented_nurbs += len(nurbs)
    for root in roots:
        visit(root)
    if not count:
        raise KeyShotError('所选 KeyShot 模型集中没有可恢复的三角网格。')
    return count, represented_nurbs


def validate_mesh(definition):
    data = definition['arrays']
    vertices, triangles = data.get('vertices', ()), data.get('triangles', ())
    if not vertices or not triangles or len(vertices) % 3 or len(triangles) % 3:
        raise KeyShotError('BIP 三角网格为空或数组长度错误：' + definition['name'])
    if not all(math.isfinite(value) for value in vertices):
        raise KeyShotError('BIP 网格坐标含无效数值。')
    if min(triangles) < 0 or max(triangles) >= len(vertices) // 3:
        raise KeyShotError('BIP 三角形顶点索引越界。')
    for name, size, indices in (('normals', 3, 'triangles_norm'), ('uv_tex', 2, 'triangles_uv')):
        values = data.get(name)
        if values is None:
            continue
        if len(values) % size or not all(math.isfinite(value) for value in values):
            raise KeyShotError('BIP 法线或 UV 数组错误。')
        mapping = data.get(indices, triangles)
        if len(mapping) != len(triangles) or min(mapping) < 0 or max(mapping) >= len(values) // size:
            raise KeyShotError('BIP 法线或 UV 索引越界。')


def basic_color(scene, material):
    visited = set()
    def color(shader_id):
        if shader_id in visited or len(visited) > 64:
            return None
        visited.add(shader_id)
        node = scene['shaders'].get(shader_id, {})
        properties = node.get('props', {})
        for name in ('diffuse', 'base', 'default_color', 'color', 'shader'):
            value = properties.get(name)
            if isinstance(value, (list, tuple)):
                if len(value) == 2 and value[0] == 'shader':
                    result = color(value[1])
                    if result:
                        return result
                elif len(value) == 2 and value[0] == 'color':
                    result = scene['colors'].get(value[1], {}).get('props', {}).get('color')
                    if result and all(math.isfinite(x) for x in result):
                        return tuple(max(0., min(1., x)) for x in result[:3]) + (1.,)
                elif len(value) in (3, 4) and all(isinstance(x, (int, float)) and math.isfinite(x) for x in value):
                    return tuple(max(0., min(1., x)) for x in value[:3]) + (1.,)
        for ident in properties.get('shaders', ()):
            result = color(ident)
            if result:
                return result
        return None
    return color(material.get('shader')) or (.65, .65, .65, 1.)


def load(path, model_set=''):
    """Build native Blender data from the selected saved mesh representations."""
    import bpy
    from mathutils import Matrix
    scene = parse(path)
    roots, chosen = select_roots(scene, model_set)
    mesh_count, nurbs_count = mesh_plan(scene, roots)
    units = scene['settings'].get('meter_scale')
    if not isinstance(units, (int, float)) or not math.isfinite(units) or units <= 0:
        raise KeyShotError('无法确定 KeyShot 尺寸单位，已停止导入。')
    container = bpy.data.objects.new(Path(path).stem, None)
    bpy.context.collection.objects.link(container)
    # KeyShot coordinates are Y-up. Convert to Blender Z-up and metres once.
    axis = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    container.matrix_world = axis @ Matrix.Scale(1. / units, 4)
    meshes, materials = {}, {}
    def material_for(ident):
        if ident not in materials:
            original = scene['materials'].get(ident, {'name': 'KeyShot material %s' % ident})
            material = bpy.data.materials.new(original['name'])
            material.diffuse_color = basic_color(scene, original)
            material.use_nodes = True
            bsdf = material.node_tree.nodes.get('Principled BSDF')
            bsdf.inputs['Base Color'].default_value = material.diffuse_color
            bsdf.inputs['Roughness'].default_value = .45
            materials[ident] = material
        return materials[ident]
    def mesh_for(definition, material_id):
        key = definition['id'], material_id
        if key in meshes:
            return meshes[key]
        arrays = definition['arrays']
        vertices, triangles = arrays['vertices'], arrays['triangles']
        mesh = bpy.data.meshes.new(definition['name'])
        mesh.vertices.add(len(vertices) // 3)
        mesh.vertices.foreach_set('co', vertices)
        mesh.loops.add(len(triangles))
        mesh.loops.foreach_set('vertex_index', triangles)
        mesh.polygons.add(len(triangles) // 3)
        mesh.polygons.foreach_set('loop_start', list(range(0, len(triangles), 3)))
        mesh.polygons.foreach_set('loop_total', [3] * (len(triangles) // 3))
        mesh.update()
        if 'uv_tex' in arrays:
            mapping = arrays.get('triangles_uv', triangles)
            values = arrays['uv_tex']
            uv = mesh.uv_layers.new(name='UVMap')
            uv.data.foreach_set('uv', [values[index * 2 + component] for index in mapping for component in (0, 1)])
        if 'normals' in arrays:
            mapping = arrays.get('triangles_norm', triangles)
            values = arrays['normals']
            mesh.polygons.foreach_set('use_smooth', [True] * len(mesh.polygons))
            mesh.normals_split_custom_set([tuple(values[index * 3:index * 3 + 3]) for index in mapping])
        mesh.materials.append(material_for(material_id))
        meshes[key] = mesh
        return mesh
    def visit(node, parent):
        if node['flags'] & SUPPRESSED_GEOMETRY:
            return
        if node['kind'] == 'instance':
            definition = scene['definitions'][node['props']['id']]
            if definition['geometry'] == 'nurbs':
                return
            obj = bpy.data.objects.new(node['name'], mesh_for(definition, node.get('material')))
        else:
            obj = bpy.data.objects.new(node['name'], None)
        bpy.context.collection.objects.link(obj)
        obj.parent = parent
        transforms = node['transforms']
        # An explicit local matrix already contains the node's evaluated
        # placement. Its saved editing matrix must not be applied a second time.
        values = transforms.get('local', transforms.get('group_local_transform', IDENTITY))
        if any(abs(values[i]) > 1e-12 for i in (3, 7, 11)) or abs(values[15] - 1.) > 1e-12:
            raise KeyShotError('BIP 含不支持的投影变换矩阵。')
        matrix = Matrix([values[i:i + 4] for i in range(0, 16, 4)]).transposed()
        if abs(matrix.determinant()) < 1e-15:
            raise KeyShotError('BIP 含退化的实例变换矩阵。')
        obj.matrix_local = matrix
        obj['jc_keyshot_node_id'] = str(node.get('id', ''))
        obj['jc_keyshot_flags'] = str(node['flags'])
        for child in node['children']:
            visit(child, obj)
    for root in roots:
        visit(root, container)
    bpy.context.view_layer.update()
    warnings = [
        'KeyShot 实验性读取：仅验证 DAL 024 的已保存三角网格；不保证所有 KeyShot 版本。',
        'KeyShot 仅导入模型集“%s”，%d 个网格实例；同组的 %d 片 NURBS 使用已保存网格表示，避免两套表示重复。' % (chosen or '无模型集', mesh_count, nurbs_count),
        'KeyShot 排除带停用几何标记的组；其他隐藏状态、模型集覆盖与动画可见性仍需人工核查。',
        'KeyShot 仅恢复基础颜色、网格法线和 UV；程序化材质、纹理贴图、灯光、摄像机和动画未恢复。',
    ]
    return warnings
