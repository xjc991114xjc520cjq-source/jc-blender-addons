"""Small, bounded 3DS static mesh reader. Original implementation, no vendored code.

Animation/keyframes are intentionally not interpreted. Invalid chunk lengths,
indices, strings and excess data raise errors instead of producing a false success.
"""
from pathlib import Path
import struct


class FormatError(ValueError):
    pass


class Reader:
    def __init__(self, path):
        if Path(path).stat().st_size > 512 * 1024 * 1024:
            raise FormatError('3DS 文件超过内置读取器的 512 MiB 限制。请改用外部转换。')
        self.data = Path(path).read_bytes()
        self.objects = []
        self.materials = {}
        self.scale = 1.0
        self.animated = False

    def unpack(self, fmt, offset, end):
        size = struct.calcsize('<' + fmt)
        if offset + size > end:
            raise FormatError('Truncated 3DS record')
        return struct.unpack_from('<' + fmt, self.data, offset)

    def string(self, offset, end):
        stop = self.data.find(b'\0', offset, end)
        if stop < 0:
            raise FormatError('Unterminated 3DS string')
        return self.data[offset:stop].decode('cp1252', errors='replace'), stop + 1

    def chunks(self, start, end, depth=0):
        if depth > 32:
            raise FormatError('3DS nesting too deep')
        while start < end:
            kind, length = self.unpack('HI', start, end)
            if length < 6 or start + length > end:
                raise FormatError('Invalid 3DS chunk length')
            yield kind, start + 6, start + length
            start += length

    def parse(self):
        kind, length = self.unpack('HI', 0, len(self.data))
        if kind != 0x4D4D or length != len(self.data):
            raise FormatError('不是完整的 3DS 文件（不能通过修改后缀转换）。')
        self.walk(6, length)
        if not self.objects:
            raise FormatError('3DS 文件中没有可导入的静态网格。')
        return self

    def walk(self, start, end, depth=0):
        for kind, a, b in self.chunks(start, end, depth):
            if kind == 0x3D3D:
                self.walk(a, b, depth + 1)
            elif kind == 0x0100:
                self.scale = self.unpack('f', a, b)[0]
            elif kind == 0xAFFF:
                self.material(a, b)
            elif kind == 0x4000:
                name, a = self.string(a, b)
                for typ, c, d in self.chunks(a, b):
                    if typ == 0x4100:
                        self.mesh(name, c, d)
            elif kind == 0xB000:
                self.animated = True

    def material(self, start, end):
        material = {'color': (0.8, 0.8, 0.8), 'texture': '', 'alpha': 1.0}
        name = 'Material'
        for kind, a, b in self.chunks(start, end):
            if kind == 0xA000:
                name, _ = self.string(a, b)
            elif kind == 0xA020:
                colors = list(self.chunks(a, b))
                for typ, c, d in colors:
                    if typ in (0x0010, 0x0013):
                        material['color'] = self.unpack('fff', c, d)
                    elif typ in (0x0011, 0x0012):
                        material['color'] = tuple(v / 255 for v in self.unpack('BBB', c, d))
            elif kind == 0xA050:
                for typ, c, d in self.chunks(a, b):
                    if typ == 0x0030:
                        material['alpha'] = 1.0 - self.unpack('H', c, d)[0] / 100
                    elif typ == 0x0031:
                        material['alpha'] = 1.0 - self.unpack('f', c, d)[0]
            elif kind == 0xA200:
                for typ, c, d in self.chunks(a, b):
                    if typ == 0xA300:
                        material['texture'], _ = self.string(c, d)
        self.materials[name] = material

    def mesh(self, name, start, end):
        obj = {'name': name, 'vertices': [], 'faces': [], 'uv': [], 'groups': {}, 'matrix': None, 'smooth': []}
        for kind, a, b in self.chunks(start, end):
            if kind in (0x4110, 0x4120, 0x4140):
                count = self.unpack('H', a, b)[0]
                fmt, key = {0x4110: ('fff', 'vertices'), 0x4120: ('HHHH', 'faces'), 0x4140: ('ff', 'uv')}[kind]
                stride = struct.calcsize('<' + fmt)
                obj[key] = [self.unpack(fmt, a + 2 + i * stride, b) for i in range(count)]
                if kind == 0x4120:
                    obj['faces'] = [face[:3] for face in obj['faces']]
                    for typ, c, d in self.chunks(a + 2 + count * stride, b):
                        if typ == 0x4130:
                            mat, c = self.string(c, d)
                            n = self.unpack('H', c, d)[0]
                            obj['groups'][mat] = self.unpack('H' * n, c + 2, d)
                        elif typ == 0x4150:
                            obj['smooth'] = list(self.unpack('I' * count, c, d))
            elif kind == 0x4160:
                obj['matrix'] = self.unpack('f' * 12, a, b)
        if any(index >= len(obj['vertices']) for face in obj['faces'] for index in face):
            raise FormatError('3DS vertex index out of bounds')
        if any(index >= len(obj['faces']) for faces in obj['groups'].values() for index in faces):
            raise FormatError('3DS material face index out of bounds')
        if obj['uv'] and len(obj['uv']) != len(obj['vertices']):
            raise FormatError('3DS UV count does not match vertex count')
        if obj['vertices'] and obj['faces']:
            self.objects.append(obj)


def load(path):
    import bpy
    from mathutils import Matrix
    reader = Reader(path).parse()
    materials = {}
    warnings = ['3DS 使用静态网格导入：不保留动画、摄像机、灯光和关键帧层级。']
    for name, data in reader.materials.items():
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        shader = mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (*data['color'], data['alpha'])
        shader.inputs['Alpha'].default_value = data['alpha']
        if data['texture']:
            texture = Path(path).parent / data['texture'].replace('\\', '/')
            if not texture.is_file():
                texture = Path(path).parent / 'textures' / Path(data['texture'].replace('\\', '/')).name
            if texture.is_file():
                node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                node.image = bpy.data.images.load(str(texture), check_existing=True)
                mat.node_tree.links.new(node.outputs['Color'], shader.inputs['Base Color'])
            else:
                warnings.append('缺失纹理：' + data['texture'])
        materials[name] = mat
    for item in reader.objects:
        mesh = bpy.data.meshes.new(item['name'])
        # 3DS stores vertices in world coordinates; retain the mesh matrix as
        # object transform and invert it on vertices (avoid applying it twice).
        mesh.from_pydata(item['vertices'], [], item['faces'])
        mesh.update()
        obj = bpy.data.objects.new(item['name'], mesh)
        bpy.context.collection.objects.link(obj)
        if item['matrix']:
            m = item['matrix']
            matrix = Matrix(((m[0], m[3], m[6], m[9]), (m[1], m[4], m[7], m[10]), (m[2], m[5], m[8], m[11]), (0, 0, 0, 1)))
            if abs(matrix.determinant()) > 1e-10:
                mesh.transform(matrix.inverted())
                obj.matrix_world = matrix
        obj.matrix_world = Matrix.Scale(reader.scale, 4) @ obj.matrix_world
        for mat_name, indices in item['groups'].items():
            if mat_name not in materials:
                materials[mat_name] = bpy.data.materials.new(mat_name)
            slot = len(mesh.materials)
            mesh.materials.append(materials[mat_name])
            for index in indices:
                mesh.polygons[index].material_index = slot
        if item['uv']:
            uv = mesh.uv_layers.new(name='UVMap')
            for loop in mesh.loops:
                uv.data[loop.index].uv = item['uv'][loop.vertex_index]
        for polygon, smoothing in zip(mesh.polygons, item['smooth']):
            polygon.use_smooth = bool(smoothing)
    return warnings
