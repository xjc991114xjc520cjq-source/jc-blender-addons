from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'jc_auto_import/bin/cad/packages'))
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool,XCAFDoc_ColorGen
from OCP.TDataStd import TDataStd_Name
from OCP.Quantity import Quantity_Color,Quantity_TOC_RGB
from OCP.gp import gp_Trsf,gp_Vec,gp_Pnt,gp_Ax2,gp_Dir
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Compound
from OCP.BRep import BRep_Builder
d=TDocStd_Document(TCollection_ExtendedString('BinXCAF'))
s=XCAFDoc_DocumentTool.ShapeTool_s(d.Main());c=XCAFDoc_DocumentTool.ColorTool_s(d.Main())
compound=TopoDS_Compound();BRep_Builder().MakeCompound(compound)
root=s.AddShape(compound,True);TDataStd_Name.Set_s(root,TCollection_ExtendedString('Assembly'))
box=BRepPrimAPI_MakeBox(20,30,10).Shape()
hole=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(10,15,0),gp_Dir(0,0,1)),3,10).Shape()
body=BRepAlgoAPI_Cut(box,hole).Shape()
label=s.AddShape(body,False);TDataStd_Name.Set_s(label,TCollection_ExtendedString('BodyWithHole'))
c.SetColor(label,Quantity_Color(.8,.1,.1,Quantity_TOC_RGB),XCAFDoc_ColorGen)
s.AddComponent(root,label,TopLoc_Location())
tr=gp_Trsf();tr.SetTranslation(gp_Vec(40,0,0));s.AddComponent(root,label,TopLoc_Location(tr))
pin=s.AddShape(BRepPrimAPI_MakeCylinder(2,25).Shape(),False);TDataStd_Name.Set_s(pin,TCollection_ExtendedString('Pin'))
c.SetColor(pin,Quantity_Color(.1,.2,.9,Quantity_TOC_RGB),XCAFDoc_ColorGen)
tr=gp_Trsf();tr.SetTranslation(gp_Vec(80,0,0));s.AddComponent(root,pin,TopLoc_Location(tr))
s.UpdateAssemblies()
p=Path(sys.argv[1])/'中文 STEP 测试';p.mkdir(exist_ok=True)
writer=STEPCAFControl_Writer();assert writer.Transfer(d,STEPControl_AsIs)
assert int(writer.Write(str(p/'带孔零件 装配.stp')))==1
from OCP.Interface import Interface_Static
Interface_Static.SetCVal_s('write.step.unit','INCH')
Interface_Static.SetCVal_s('write.step.schema','AP242DIS')
writer=STEPCAFControl_Writer();assert writer.Transfer(d,STEPControl_AsIs)
assert int(writer.Write(str(p/'英寸 装配.STEP')))==1
print('FIXTURE_READY')
