"""Build a portable legacy Blender add-on ZIP with no cache or machine settings."""
import ast, hashlib, json, zipfile
from pathlib import Path
root=Path(__file__).resolve().parent
source=root/'jc_view_navigator'
ast.parse((source/'__init__.py').read_text(encoding='utf-8'))
dist=root/'dist'
dist.mkdir(exist_ok=True)
target=dist/'JC-View-Navigator-1.1.0.zip'
files=['__init__.py','使用说明.md','LICENSE.txt']
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for name in files:
        z.write(source/name,'jc_view_navigator/'+name)
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    assert len(z.namelist()) == len(files)
report={'archive':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'size':target.stat().st_size,'files':files}
(dist/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
