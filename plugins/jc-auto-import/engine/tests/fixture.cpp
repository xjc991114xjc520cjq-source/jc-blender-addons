// Original regression-fixture generator; uses only the public Cineware API.
#include "c4d_file.h"
#include "default_alien_overloads.h"
#include <cstdio>
using namespace cineware;
void GetWriterInfo(int& id,String& name) {id=2424226;name="JC regression fixtures";}
static PolygonObject* mesh(BaseDocument* d,const char* name,BaseObject* parent=nullptr,Int32 mode=MODE_UNDEF,Float x=0) {
    auto* p=PolygonObject::Alloc(4,2);
    p->SetName(String(name));p->SetEditorMode(mode);p->SetRenderMode(MODE_UNDEF);
    Vector* v=p->GetPointW();v[0]=Vector(0,0,0);v[1]=Vector(2,0,0);v[2]=Vector(0,2,0);v[3]=Vector(2,2,0);
    auto* f=p->GetPolygonW();f[0]=CPolygon(0,1,2);f[1]=CPolygon(1,3,2);
    Matrix m;m.off=Vector(x,3,5);p->SetMl(m);d->InsertObject(p,parent);return p;
}
int main(int argc,char** argv) {
    if(argc!=2)return 2;
    auto* d=BaseDocument::Alloc();if(!d)return 3;
    auto* p=BaseObject::Alloc(Onull);p->SetName("HiddenParent");p->SetEditorMode(MODE_OFF);d->InsertObject(p,nullptr);
    mesh(d,"HiddenInherited",p);mesh(d,"VisibleOverride",p,MODE_ON,5);
    mesh(d,"HiddenDirect",nullptr,MODE_OFF,10);
    auto* visible=mesh(d,"VisibleRenderOff",nullptr,MODE_UNDEF,15);visible->SetRenderMode(MODE_OFF);
    mesh(d,"SameName",nullptr,MODE_UNDEF,20);mesh(d,"SameName",nullptr,MODE_UNDEF,25);
    auto* component=mesh(d,"PartiallyHidden",nullptr,MODE_UNDEF,30);component->GetPolygonH()->Select(1);
    auto* all=mesh(d,"AllFacesHidden",nullptr,MODE_UNDEF,35);all->GetPolygonH()->Select(0);all->GetPolygonH()->Select(1);
    auto* layer=LayerObject::Alloc();layer->SetName("HiddenLayer");d->InsertLayer(layer,nullptr);
    layer->SetParameter(ID_LAYER_VIEW,GeData(Int32(0)));
    layer->SetParameter(ID_LAYER_RENDER,GeData(Int32(1)));
    auto* layerMesh=mesh(d,"LayerHidden",nullptr,MODE_ON,40);layerMesh->SetLayerObject(layer);
    auto* transform=BaseObject::Alloc(Onull);transform->SetName("TransformParent");Matrix m;m.off=Vector(40,4,7);m.v1=Vector(0,2,0);m.v2=Vector(-3,0,0);m.v3=Vector(0,0,4);transform->SetMl(m);d->InsertObject(transform,nullptr);
    mesh(d,"Transformed",transform);
    // A hidden reference group has its own placement, which must not be added
    // to the placement of a visible instance. Its source sibling is unrelated.
    auto* ref=BaseObject::Alloc(Onull);ref->SetName("HiddenReference");ref->SetEditorMode(MODE_OFF);
    Matrix rm;rm.off=Vector(1000,0,0);ref->SetMl(rm);d->InsertObject(ref,nullptr);
    mesh(d,"ReferenceBody",ref);
    auto* inst=BaseObject::Alloc(Oinstance);inst->SetName("VisibleInstance");Matrix im;im.off=Vector(50,0,0);inst->SetMl(im);d->InsertObject(inst,nullptr);
    auto* link=BaseLink::Alloc();link->SetLink(ref);inst->SetParameter(INSTANCEOBJECT_LINK,GeData(*link));BaseLink::Free(link);
    mesh(d,"UnrelatedSibling",nullptr,MODE_OFF,55);
    Bool ok=SaveDocument(d,Filename(String(argv[1])),SAVEDOCUMENTFLAGS_0);
    BaseDocument::Free(d);return ok?0:4;
}
