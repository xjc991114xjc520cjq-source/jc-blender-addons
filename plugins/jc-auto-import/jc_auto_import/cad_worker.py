"""Isolated Open CASCADE STEP tessellation; run with the bundled Python only."""
from pathlib import Path
import json
import sys
import traceback
import math

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'bin/cad/packages'))


def remove_tiny_crossings(points, plane):
    """Remove only bounded, near-zero-area loops in sampled planar trims."""
    from OCP.gp import gp_Vec
    if len(points) > 2000:
        return None
    origin = plane.Location()
    x_axis, y_axis = gp_Vec(plane.Position().XDirection()), gp_Vec(plane.Position().YDirection())
    def cross(a, b):
        return a[0] * b[1] - a[1] * b[0]
    def sub(a, b):
        return (a[0] - b[0], a[1] - b[1])
    for _ in range(8):
        coords = [(gp_Vec(origin, p).Dot(x_axis), gp_Vec(origin, p).Dot(y_axis)) for p in points]
        count = len(points)
        crossing = None
        for i in range(count):
            a, b = coords[i], coords[(i + 1) % count]
            r = sub(b, a)
            for j in range(i + 2, count):
                if i == 0 and j == count - 1:
                    continue
                c, d = coords[j], coords[(j + 1) % count]
                s = sub(d, c)
                denominator = cross(r, s)
                if abs(denominator) < 1e-15:
                    continue
                t = cross(sub(c, a), s) / denominator
                u = cross(sub(c, a), r) / denominator
                if 0 < t < 1 and 0 < u < 1:
                    q = (a[0] + t * r[0], a[1] + t * r[1])
                    loops = ([q] + coords[i + 1:j + 1], [q] + coords[j + 1:] + coords[:i + 1])
                    small = None
                    for side, loop in enumerate(loops):
                        area = abs(sum(cross(loop[k], loop[(k + 1) % len(loop)]) for k in range(len(loop))) / 2)
                        spans = [max(p[k] for p in loop) - min(p[k] for p in loop) for k in range(2)]
                        if area <= 1e-4 and max(spans) <= .5:
                            small = side
                            break
                    if small is None:
                        return None
                    point = origin.Translated(x_axis.Multiplied(q[0]).Added(y_axis.Multiplied(q[1])))
                    crossing = (i, j, point, small)
                    break
            if crossing:
                break
        if crossing is None:
            return points
        i, j, point, small = crossing
        points = points[:i + 1] + [point] + points[j + 1:] if small == 0 else [point] + points[i + 1:j + 1]
    return None


def recover_parametric_mesh(face):
    """Mesh bounded trim polygons in normalized UV, then sample the source surface.

    Only used after OCCT's normal/fresh-face meshing fails. No source topology,
    assembly placement or analytic surface is changed. Reject oversized work,
    non-finite samples, large boundary repairs and area/deflection violations.
    """
    from OCP.BRep import BRep_Tool, BRep_Builder
    from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    from OCP.GCPnts import GCPnts_QuasiUniformDeflection
    from OCP.TopAbs import TopAbs_WIRE, TopAbs_REVERSED
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    from OCP.TopLoc import TopLoc_Location
    from OCP.gp import gp_Pnt, gp_Pnt2d, gp_Pln, gp_Dir, gp_Vec
    from OCP.Poly import Poly_Triangulation, Poly_Triangle

    local = TopoDS.Face_s(face.Located(TopLoc_Location()))
    surface = BRep_Tool.Surface_s(local)
    bounds = BRepTools.UVBounds_s(local)
    u0, u1, v0, v1 = bounds
    if not all(math.isfinite(x) for x in bounds) or u1 <= u0 or v1 <= v0:
        return None
    props = GProp_GProps()
    BRepGProp.SurfaceProperties_s(local, props)
    area = abs(props.Mass())
    if not math.isfinite(area):
        return None
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(local, box, False, False)
    if box.IsVoid():
        return None
    limits = box.Get()
    plane = gp_Pln(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1))
    wires = TopExp_Explorer(local, TopAbs_WIRE)
    polygons, edge_groups = [], []
    total = 0
    while wires.More():
        wire = TopoDS.Wire_s(wires.Current())
        wires.Next()
        explorer = BRepTools_WireExplorer(wire, local)
        points, curves = [], []
        while explorer.More():
            edge = explorer.Current()
            explorer.Next()
            curve = BRepAdaptor_Curve(edge)
            pc = BRep_Tool.CurveOnSurface_s(edge, local, 0., 0.)
            if pc is None:
                return None
            first, last = curve.FirstParameter(), curve.LastParameter()
            curves.append((pc, first, last))
            sample = GCPnts_QuasiUniformDeflection(curve, 1e-6)
            if not sample.IsDone() or sample.NbPoints() > 10000:
                return None
            parameters = [sample.Parameter(i) for i in range(1, sample.NbPoints() + 1)]
            if edge.Orientation() == TopAbs_REVERSED:
                parameters.reverse()
            for parameter in parameters:
                uv = pc.Value(parameter)
                point = gp_Pnt((uv.X() - u0) / (u1 - u0) * 100,
                               (uv.Y() - v0) / (v1 - v0) * 100, 0)
                if not points or points[-1].Distance(point) > 1e-7:
                    points.append(point)
                    total += 1
                    if total > 10000:
                        return None
        edge_groups.append(curves)
        # Two coincident trims with vanishing analytic area describe a collapsed
        # edge, not a missing shell. Require agreement along both entire trims.
        if area < 1e-10 and len(curves) == 2:
            samples = []
            for pc, first, last in curves:
                samples.append([surface.Value(*pc.Value(first + (last-first)*i/64).Coord()) for i in range(65)])
            distance = min(max(a.Distance(b) for a, b in zip(samples[0], samples[1])),
                           max(a.Distance(b) for a, b in zip(samples[0], reversed(samples[1]))))
            if distance <= 1e-7 and not wires.More() and len(edge_groups) == 1:
                return 'degenerate-edge'
        if len(points) < 3:
            return None
        if points[-1].Distance(points[0]) < 1e-7:
            points.pop()
        points = remove_tiny_crossings(points, plane)
        if points is None or len(points) < 3:
            return None
        polygon = BRepBuilderAPI_MakePolygon()
        for point in points:
            polygon.Add(point)
        polygon.Close()
        if not polygon.IsDone():
            return None
        polygons.append((wire.IsSame(BRepTools.OuterWire_s(local)), polygon.Wire()))
    outer = [wire for is_outer, wire in polygons if is_outer]
    if len(outer) != 1 or area <= 1e-12:
        return None
    maker = BRepBuilderAPI_MakeFace(outer[0], True)
    for is_outer, wire in polygons:
        if not is_outer:
            maker.Add(wire)
    if not maker.IsDone():
        return None
    uv_face = maker.Face()
    BRepMesh_IncrementalMesh(uv_face, .01, False, .1, False)
    mesh = BRep_Tool.Triangulation_s(uv_face, TopLoc_Location())
    if mesh is None or not mesh.NbTriangles():
        return None
    uv = [(u0 + mesh.Node(i).X()/100*(u1-u0), v0 + mesh.Node(i).Y()/100*(v1-v0))
          for i in range(1, mesh.NbNodes()+1)]
    xyz = [surface.Value(*point) for point in uv]
    triangles = [tuple(j-1 for j in mesh.Triangle(i).Get()) for i in range(1, mesh.NbTriangles()+1)]
    tolerance = min(.002, max(1e-7, math.sqrt(area)*.005))
    for _ in range(7):
        marked = set()
        for a, b, c in triangles:
            for x, y in ((a,b), (b,c), (c,a)):
                mid = surface.Value(*[(uv[x][k]+uv[y][k])/2 for k in range(2)])
                chord = gp_Pnt(*[(xyz[x].Coord()[k]+xyz[y].Coord()[k])/2 for k in range(3)])
                if mid.Distance(chord) > tolerance:
                    marked.add(tuple(sorted((x,y))))
            center = surface.Value(*[(uv[a][k]+uv[b][k]+uv[c][k])/3 for k in range(2)])
            chord = gp_Pnt(*[(xyz[a].Coord()[k]+xyz[b].Coord()[k]+xyz[c].Coord()[k])/3 for k in range(3)])
            if center.Distance(chord) > tolerance:
                marked.update(tuple(sorted(pair)) for pair in ((a,b),(b,c),(c,a)))
        current_area = sum(gp_Vec(xyz[a],xyz[b]).Crossed(gp_Vec(xyz[a],xyz[c])).Magnitude()/2 for a,b,c in triangles)
        if not marked and math.isfinite(current_area) and abs(current_area-area) <= max(1e-10,area*.002):
            break
        # Uniform shared-edge subdivision avoids folded skinny fans on curved trims.
        marked = {tuple(sorted(pair)) for a,b,c in triangles for pair in ((a,b),(b,c),(c,a))}
        if len(uv)+len(marked) > 300000 or len(triangles)*4 > 1000000:
            return None
        mids = {}
        for x,y in sorted(marked):
            mids[(x,y)] = len(uv)
            point = tuple((uv[x][k]+uv[y][k])/2 for k in range(2))
            uv.append(point)
            xyz.append(surface.Value(*point))
        refined = []
        for a,b,c in triangles:
            ab,bc,ca = [mids[tuple(sorted(edge))] for edge in ((a,b),(b,c),(c,a))]
            refined.extend(((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)))
        triangles = refined
    else:
        return None
    for point in xyz:
        coord = point.Coord()
        if any(not math.isfinite(coord[k]) or coord[k] < limits[k]-.0001 or coord[k] > limits[k+3]+.0001 for k in range(3)):
            return None
    mesh_area = sum(gp_Vec(xyz[a],xyz[b]).Crossed(gp_Vec(xyz[a],xyz[c])).Magnitude()/2 for a,b,c in triangles)
    if not math.isfinite(mesh_area) or abs(mesh_area-area) > max(1e-10,area*.002):
        return None
    recovered = Poly_Triangulation(len(uv),len(triangles),True,False)
    for i, point in enumerate(xyz,1):
        recovered.SetNode(i,point)
        recovered.SetUVNode(i,gp_Pnt2d(*uv[i-1]))
    for i,(a,b,c) in enumerate(triangles,1):
        # OCCT's writer applies the source face orientation itself. Store the
        # forward surface orientation, irrespective of the temporary UV plane.
        if ((uv[b][0]-uv[a][0])*(uv[c][1]-uv[a][1]) -
                (uv[b][1]-uv[a][1])*(uv[c][0]-uv[a][0])) < 0:
            b,c = c,b
        recovered.SetTriangle(i,Poly_Triangle(a+1,b+1,c+1))
    recovered.Deflection(tolerance)
    BRep_Builder().UpdateFace(face,recovered)
    return 'parametric-trim'


def repair_face_mesh(face):
    """Recover a failed face without altering the document's B-rep topology.

    Retry on an independent geometry copy, then (only for planar surfaces)
    discretize trim wires with tight error/area bounds. Attach recovered local
    triangulation to the original face so assembly placement remains unchanged.
    """
    from OCP.BRep import BRep_Tool, BRep_Builder
    from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy, BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
    from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.IMeshTools import IMeshTools_Parameters
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS
    from OCP.TopAbs import TopAbs_WIRE, TopAbs_REVERSED
    from OCP.TopExp import TopExp_Explorer
    from OCP.GeomAbs import GeomAbs_Plane
    from OCP.GCPnts import GCPnts_QuasiUniformDeflection
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.gp import gp_Vec

    local = TopoDS.Face_s(face.Located(TopLoc_Location()))
    bounds = Bnd_Box()
    BRepBndLib.AddOptimal_s(local, bounds, False, False)
    if bounds.IsVoid():
        return None
    limits = bounds.Get()

    def attach(candidate, method):
        triangle = BRep_Tool.Triangulation_s(candidate, TopLoc_Location())
        if triangle is None or triangle.NbTriangles() == 0:
            return None
        for i in range(1, triangle.NbNodes() + 1):
            xyz = triangle.Node(i).Coord()
            if any(not math.isfinite(xyz[j]) or xyz[j] < limits[j] - .05 or
                   xyz[j] > limits[j + 3] + .05 for j in range(3)):
                return None
        # A fresh local copy retains the source orientation. Planar reconstruction
        # must use the same face orientation before RWGltf handles winding.
        BRep_Builder().UpdateFace(face, triangle)
        return method

    copy = TopoDS.Face_s(BRepBuilderAPI_Copy(local, True, False).Shape())
    BRepTools.Clean_s(copy, True)
    parameters = IMeshTools_Parameters()
    parameters.Deflection = .01
    parameters.Angle = .05
    parameters.MinSize = 1e-7
    parameters.AdjustMinSize = True
    parameters.InParallel = False
    BRepMesh_IncrementalMesh(copy, parameters)
    method = attach(copy, 'fresh-face')
    if method:
        return method
    surface = BRepAdaptor_Surface(local)
    if surface.GetType() != GeomAbs_Plane:
        return recover_parametric_mesh(face)
    plane = surface.Plane()
    normal = gp_Vec(plane.Axis().Direction())
    origin = plane.Location()
    wires = TopExp_Explorer(local, TopAbs_WIRE)
    rebuilt = []
    point_count = 0
    while wires.More():
        wire = TopoDS.Wire_s(wires.Current())
        wires.Next()
        edges = BRepTools_WireExplorer(wire, local)
        points = []
        while edges.More():
            edge = edges.Current()
            edges.Next()
            sample = GCPnts_QuasiUniformDeflection(BRepAdaptor_Curve(edge), .005)
            if not sample.IsDone():
                return None
            part = [sample.Value(i) for i in range(1, sample.NbPoints() + 1)]
            if edge.Orientation() == TopAbs_REVERSED:
                part.reverse()
            for point in part:
                distance = gp_Vec(origin, point).Dot(normal)
                if abs(distance) > .005:
                    return None
                point = point.Translated(normal.Multiplied(-distance))
                if not points or point.Distance(points[-1]) > 1e-7:
                    points.append(point)
                    point_count += 1
                    if point_count > 100000:
                        return None
        if len(points) < 3:
            return None
        if points[-1].Distance(points[0]) < 1e-7:
            points.pop()
        points = remove_tiny_crossings(points, plane)
        if points is None or len(points) < 3:
            return None
        polygon = BRepBuilderAPI_MakePolygon()
        for point in points:
            polygon.Add(point)
        polygon.Close()
        if not polygon.IsDone():
            return None
        rebuilt.append((wire.IsSame(BRepTools.OuterWire_s(local)), polygon.Wire()))
    outer = [wire for is_outer, wire in rebuilt if is_outer]
    if len(outer) != 1:
        return None
    maker = BRepBuilderAPI_MakeFace(plane, outer[0], True)
    for is_outer, wire in rebuilt:
        if not is_outer:
            maker.Add(wire)
    if not maker.IsDone():
        return None
    replacement = maker.Face()
    if not BRepCheck_Analyzer(replacement).IsValid():
        return None
    original_area, rebuilt_area = GProp_GProps(), GProp_GProps()
    BRepGProp.SurfaceProperties_s(local, original_area)
    BRepGProp.SurfaceProperties_s(replacement, rebuilt_area)
    area = abs(original_area.Mass())
    if not math.isfinite(area) or area <= 1e-12 or abs(abs(rebuilt_area.Mass()) - area) > max(.001, area * .002):
        return None
    # Mesh nodes are in local coordinates; do not apply the assembly placement.
    replacement.Orientation(local.Orientation())
    BRepMesh_IncrementalMesh(replacement, .01, False, .1, False)
    return attach(replacement, 'planar-trim')


def convert(source, output):
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.TDocStd import TDocStd_Document
    from OCP.TCollection import TCollection_ExtendedString, TCollection_AsciiString
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
    from OCP.TDF import TDF_LabelSequence
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRep import BRep_Tool
    from OCP.TopoDS import TopoDS
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopLoc import TopLoc_Location
    from OCP.RWGltf import RWGltf_CafWriter
    from OCP.RWMesh import RWMesh_CoordinateSystem_Zup
    from OCP.TColStd import TColStd_IndexedDataMapOfStringString
    from OCP.Message import Message_ProgressRange

    document = TDocStd_Document(TCollection_ExtendedString('BinXCAF'))
    reader = STEPCAFControl_Reader()
    reader.SetColorMode(True)
    reader.SetNameMode(True)
    if reader.ReadFile(str(source)) != IFSelect_RetDone:
        raise RuntimeError('无法读取 STEP 文件：文件损坏、缺少外部引用或不是有效 STEP。')
    if not reader.Transfer(document):
        raise RuntimeError('STEP 实体传输失败，没有可转换的曲面。')
    tool = XCAFDoc_DocumentTool.ShapeTool_s(document.Main())
    roots = TDF_LabelSequence()
    tool.GetFreeShapes(roots)
    if not roots.Length():
        raise RuntimeError('STEP 中没有可恢复实体。')
    triangles = 0
    missing = 0
    repaired = {}
    for index in range(1, roots.Length() + 1):
        shape = tool.GetShape_s(roots.Value(index))
        # OCCT reads STEP's declared units into millimetres by default.
        # Absolute chord error 0.05 mm, angular error ~17 degrees.
        mesher = BRepMesh_IncrementalMesh(shape, 0.05, False, 0.3, True)
        mesher.Perform()
        if not mesher.IsDone():
            raise RuntimeError('STEP 曲面网格化失败。')
        faces = TopExp_Explorer(shape, TopAbs_FACE)
        while faces.More():
            face = TopoDS.Face_s(faces.Current())
            mesh = BRep_Tool.Triangulation_s(face, TopLoc_Location())
            method = None
            if mesh is None or mesh.NbTriangles() == 0:
                try:
                    method = repair_face_mesh(face)
                except Exception:
                    method = None
                if method:
                    repaired[method] = repaired.get(method, 0) + 1
                mesh = BRep_Tool.Triangulation_s(face, TopLoc_Location())
            if mesh is not None and mesh.NbTriangles() > 0:
                triangles += mesh.NbTriangles()
            elif method != 'degenerate-edge':
                missing += 1
            faces.Next()
    if missing:
        raise RuntimeError('STEP 有 %d 个面无法网格化；已停止导入，避免静默丢失外壳。' % missing)
    if not triangles:
        raise RuntimeError('STEP 没有可转换的面，仅含线、点或未解析实体。')
    writer = RWGltf_CafWriter(TCollection_AsciiString(str(output)), True)
    writer.SetMergeFaces(True)
    coordinates = writer.ChangeCoordinateSystemConverter()
    coordinates.SetInputCoordinateSystem(RWMesh_CoordinateSystem_Zup)
    coordinates.SetInputLengthUnit(0.001)
    if not writer.Perform(document, TColStd_IndexedDataMapOfStringString(), Message_ProgressRange()):
        raise RuntimeError('CAD 引擎无法写出 GLB。')
    return {'roots': roots.Length(), 'triangles': triangles, 'missing_faces': missing, 'repaired_faces': repaired}


if __name__ == '__main__':
    try:
        report = convert(Path(sys.argv[1]).resolve(strict=True), Path(sys.argv[2]).resolve())
        print(json.dumps(report), flush=True)
    except Exception as error:
        print('ERROR: ' + str(error), flush=True)
        traceback.print_exc()
        sys.exit(12)
