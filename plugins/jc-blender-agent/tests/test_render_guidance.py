"""Conditional CLI prompts and portable release knowledge, without provider logins."""
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bridge.agents import run_cli
from bridge.common import VERSION


class RecordingInput(io.BytesIO):
    def close(self):
        self.recorded=self.getvalue()
        super().close()


class FakeCLI:
    returncode=0
    def __init__(self):
        self.stdin=RecordingInput()
        self.stdout=io.BytesIO(b'{"type":"item.completed","item":{"type":"agent_message","text":"done"}}\n')
        self.stderr=io.BytesIO()
    def poll(self):return 0


class RenderGuidanceTests(unittest.TestCase):
    def test_both_cli_adapters_respect_switch(self):
        with tempfile.TemporaryDirectory() as temp:
            for kind in ('codex','claude'):
                for enabled in (False,True):
                    fake=FakeCLI()
                    with patch('bridge.agents.subprocess.Popen',return_value=fake):
                        answer=run_cli({'kind':kind,'executable':kind+'.exe','use_render_knowledge':enabled},'用户的本轮要求',temp,'a'*32,'b'*32,temp,threading.Event(),lambda *a:None)
                    self.assertEqual(answer,'done')
                    prompt=fake.stdin.recorded.decode('utf-8')
                    self.assertEqual('材质真实感必须来自材质响应' in prompt,enabled)
                    self.assertTrue(prompt.endswith('用户的本轮要求'))

    def test_release_knowledge_works_after_relocation(self):
        release=ROOT/'dist'/f'JC-Blender-Agent-{VERSION}.zip'
        with tempfile.TemporaryDirectory(prefix='jc-portable-knowledge-') as temp:
            dest=Path(temp)
            with zipfile.ZipFile(release) as z:
                z.extractall(dest)
                self.assertTrue(all(not n.endswith(('.blend','.mp4','.exr')) for n in z.namelist()))
            knowledge=dest/'jc_blender_agent/runtime/bridge/knowledge'
            self.assertEqual(len(list(knowledge.iterdir())),4)
            for path in knowledge.iterdir():
                if path.suffix in ('.md','.json'):
                    import re
                    self.assertIsNone(re.search(r'(?<![A-Za-z0-9_-])[A-Za-z]:[/\\]',path.read_text(encoding='utf-8')))
            check="""import sys,json;from pathlib import Path
sys.path.insert(0,str(Path('jc_blender_agent/runtime').resolve()))
from bridge.render_guidance import render_instructions,read_resource,RECIPE_URI,knowledge_result
from bridge.common import VERSION
assert '材质真实感必须来自材质响应' in render_instructions()
r=json.loads(read_resource(RECIPE_URI));assert r['output']['height']==4000
assert len(knowledge_result('preview')['image'])>1000
print(json.dumps({'version':VERSION,'loaded_from':str(Path(__import__('bridge.render_guidance',fromlist=['x']).__file__).resolve())}))
"""
            result=subprocess.run([sys.executable,'-I','-c',check],cwd=temp,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stderr)
            data=json.loads(result.stdout);self.assertEqual(data['version'],VERSION)
            self.assertTrue(Path(data['loaded_from']).is_relative_to(dest))


if __name__=='__main__':unittest.main(verbosity=2)
