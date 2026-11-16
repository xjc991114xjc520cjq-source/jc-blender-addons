"""Isolated Open CASCADE STEP tessellation; run with the bundled Python only."""
from pathlib import Path
import json
import sys
import traceback

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'bin/cad/packages'))


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
            if mesh is None or mesh.NbTriangles() == 0:
                missing += 1
            else:
                triangles += mesh.NbTriangles()
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
    return {'roots': roots.Length(), 'triangles': triangles, 'missing_faces': missing}


if __name__ == '__main__':
    try:
        report = convert(Path(sys.argv[1]).resolve(strict=True), Path(sys.argv[2]).resolve())
        print(json.dumps(report), flush=True)
    except Exception as error:
        print('ERROR: ' + str(error), flush=True)
        traceback.print_exc()
        sys.exit(12)
