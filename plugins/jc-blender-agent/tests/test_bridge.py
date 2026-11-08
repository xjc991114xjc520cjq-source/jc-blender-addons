"""Protocol tests use a simulated Blender worker and simulated API, never a real paid API.

Independent MCP SDK client validates the stdio server, schemas, and image content.
Actual bpy checks and GUI Agent checks are separate evidence.
"""
import asyncio
import base64
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
sys.path.insert(0,str(PROJECT/'.test_tools'))
if os.name=='nt':
    for rel in ('win32','win32/lib','pywin32_system32'):
        sys.path.insert(0,str(PROJECT/'.test_tools'/rel))
    _dll=os.add_dll_directory(str(PROJECT/'.test_tools/pywin32_system32'))
from bridge.broker import Broker, handler_for
from bridge.common import atomic_json, request
from bridge.agents import run_api, api_request
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PIXEL='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jZ1kAAAAASUVORK5CYII='


class FakeAPI(BaseHTTPRequestHandler):
    seen=[]
    def log_message(self,*a):pass
    def do_GET(self):
        body={'data':[{'id':'test-model-a'},{'id':'test-model-b'},{'id':'test-model-a'}]}
        raw=json.dumps(body).encode()
        self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_POST(self):
        data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.seen.append((self.path,data))
        messages=data.get('input',data.get('messages',[]))
        outputs=sum(1 for x in messages if x.get('role')=='tool' or x.get('type')=='function_call_output')
        toolnames=getattr(self,'toolnames',['blender_scene','blender_execute','blender_viewport'])
        if outputs<len(toolnames):
            name=toolnames[outputs]
            args={'code':"result={'demo':True}",'description':'simulated-edit'} if name=='blender_execute' else {'identifier':self.identifier} if name=='blender_attachment' else {}
            if self.path.endswith('/responses'):
                body={'status':'completed','output':[{'type':'function_call','name':name,'call_id':f'c{outputs}','arguments':json.dumps(args)}]}
            else:
                body={'choices':[{'message':{'role':'assistant','content':None,'tool_calls':[{'id':f'c{outputs}','type':'function','function':{'name':name,'arguments':json.dumps(args)}}]},'finish_reason':'tool_calls'}]}
        elif self.path.endswith('/responses'):
            body={'status':'completed','output':[{'type':'message','role':'assistant','content':[{'type':'output_text','text':'模拟任务结束'}]}]}
        else:
            body={'choices':[{'message':{'role':'assistant','content':'模拟任务结束'},'finish_reason':'stop'}]}
        raw=json.dumps(body).encode()
        self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)


class AttachmentAPI(FakeAPI):
    toolnames=['blender_attachment','blender_scene']
    identifier=''


class KnowledgeOnlyAPI(FakeAPI):
    toolnames=['blender_render_knowledge']


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='jc-blender-test-')
        self.root=Path(self.tmp.name);self.instance='a'*32
        self.knowledge_enabled=False
        self.dir=self.root/'instances'/self.instance
        (self.dir/'inbox').mkdir(parents=True);(self.dir/'outbox').mkdir()
        atomic_json(self.dir/'heartbeat.json',{'instance':self.instance,'time':time.time()})
        self.broker=Broker(self.root)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(self.broker));self.server.daemon_threads=True
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        atomic_json(self.root/'broker.json',{'url':self.url})
        self.stop=threading.Event()
        self.worker=threading.Thread(target=self.work,daemon=True);self.worker.start()
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
    def tearDown(self):
        self.stop.set();self.worker.join(timeout=2)
        self.server.shutdown();self.server.server_close()
        self.tmp.cleanup()
    def work(self):
        while not self.stop.is_set():
            atomic_json(self.dir/'heartbeat.json',{'instance':self.instance,'time':time.time(),'use_render_knowledge':self.knowledge_enabled})
            for f in (self.dir/'inbox').glob('*.json'):
                cmd=json.loads(f.read_text(encoding='utf-8'));f.rename(f.with_suffix('.done'))
                if f.with_suffix('.cancel').exists():result={'error':'cancelled'}
                elif cmd['name']=='blender_execute':result={'result':{'simulated':True},'checkpoint':'simulated.blend'}
                elif cmd['name']=='blender_viewport':
                    image=Path(cmd['artifact_dir'])/'simulated.png';image.write_bytes(base64.b64decode(PIXEL));result={'image_path':str(image)}
                else:result={'scene':'Simulated','object_count':3}
                atomic_json(self.dir/'outbox'/f.name,result)
            self.stop.wait(.02)
    def test_http_auth_origin_host(self):
        for headers,code in [({},401),({'Authorization':'Bearer '+self.broker.token,'Origin':'https://evil.example'},403),({'Authorization':'Bearer '+self.broker.token,'Host':'evil.example'},403)]:
            req=urllib.request.Request(self.url+'/health',headers=headers)
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req)
            self.assertEqual(error.exception.code,code)
        self.assertTrue(request(self.url,self.broker.token,'/health')['ok'])
    def test_independent_mcp_sdk(self):
        async def run():
            params=StdioServerParameters(command=sys.executable,args=[str(PROJECT/'bridge/mcp_server.py'),'--state',str(self.root),'--instance',self.instance])
            async with stdio_client(params) as (r,w):
                async with ClientSession(r,w) as session:
                    init=await session.initialize();self.assertEqual(init.serverInfo.name,'jc_blender')
                    schemas=await session.list_tools();self.assertEqual(len(schemas.tools),8)
                    result=await session.call_tool('blender_scene',{});self.assertFalse(result.isError)
                    self.assertEqual(json.loads(result.content[0].text)['object_count'],3)
                    bad=await session.call_tool('blender_execute',{'code':3});self.assertTrue(bad.isError)
                    picture=await session.call_tool('blender_viewport',{});self.assertEqual(picture.content[1].type,'image')
                    self.assertEqual(picture.content[1].mimeType,'image/png')
        asyncio.run(run())
    def test_api_chat_and_responses_through_real_mcp_process(self):
        api=ThreadingHTTPServer(('127.0.0.1',0),FakeAPI);FakeAPI.seen=[]
        threading.Thread(target=api.serve_forever,daemon=True).start()
        try:
            for protocol in ('chat','responses'):
                profile={'kind':'api','model':'simulated-model','base_url':f'http://127.0.0.1:{api.server_port}/v1','protocol':protocol,'vision':True,'api_key':'test-credential-not-a-real-key'}
                submitted=self.broker.submit({'instance':self.instance,'prompt':'模拟协议测试','profile':profile})
                deadline=time.time()+20
                while time.time()<deadline:
                    job=self.broker.get_job(submitted['id'])
                    if job['state']!='running':break
                    time.sleep(.05)
                self.assertEqual(job['state'],'completed',job)
                self.assertEqual(job['successful_calls'],3)
                self.assertEqual(job['edits'],1);self.assertEqual(job['visual_checks'],1)
                persisted=(self.root/'jobs'/(job['id']+'.json')).read_text(encoding='utf-8')
                self.assertNotIn('test-credential-not-a-real-key',persisted)
            chat=[d for p,d in FakeAPI.seen if p.endswith('completions')][-1]
            responses=[d for p,d in FakeAPI.seen if p.endswith('responses')][-1]
            self.assertTrue(any(isinstance(m.get('content'),list) and any(c['type']=='image_url' for c in m['content']) for m in chat['messages']))
            self.assertTrue(any(isinstance(m.get('content'),list) and any(c['type']=='input_image' for c in m['content']) for m in responses['input']))
            self.assertFalse(responses['store'])
        finally:api.shutdown();api.server_close()
    def test_cancel_and_instance_ownership(self):
        from unittest.mock import patch
        def pending(profile,prompt,root,instance,job,cancel,event):
            cancel.wait(5);raise RuntimeError('cancelled')
        with patch('bridge.broker.run_api',pending):
            j=self.broker.submit({'instance':self.instance,'prompt':'cancel test','profile':{'kind':'api','model':'test'}})
            with self.assertRaises(ValueError):self.broker.submit({'instance':self.instance,'prompt':'conflict','profile':{'kind':'api','model':'test'}})
            with self.assertRaises(ValueError):self.broker.call_tool({'instance':self.instance,'name':'blender_scene'})
            self.broker.cancel(j['id'])
            deadline=time.time()+2
            while self.broker.get_job(j['id'])['state']=='cancelling' and time.time()<deadline:time.sleep(.02)
            self.assertEqual(self.broker.get_job(j['id'])['state'],'cancelled')
    def test_text_only_reply_is_not_execution(self):
        from unittest.mock import patch
        with patch('bridge.broker.run_api',return_value='I did it'):
            j=self.broker.submit({'instance':self.instance,'prompt':'no fake success','profile':{'kind':'api','model':'test'}})
            deadline=time.time()+2
            while self.broker.get_job(j['id'])['state']=='running' and time.time()<deadline:time.sleep(.02)
            job=self.broker.get_job(j['id']);self.assertEqual(job['state'],'failed')
            self.assertIn('没有成功调用',job['answer'])
    def test_path_and_api_address_validation(self):
        for instance in ('../escape','x'*32,'a'*31):
            with self.assertRaises(ValueError):self.broker.instance_dir(instance)
        with self.assertRaises(ValueError):api_request({'base_url':'http://example.com/v1'}, {})
        with self.assertRaises(ValueError):api_request({'base_url':'https://user:pass@example.com/v1'}, {})

    def attach(self,path):
        data=request(self.url,self.broker.token,'/attachments/add',{'instance':self.instance,'paths':[str(path)]})
        identifier=data['attachments'][0]['id']
        deadline=time.time()+3
        while time.time()<deadline:
            try:return self.broker.attachments.records(self.instance,[identifier])[0]
            except ValueError:time.sleep(.02)
        self.fail('path reference check timed out')

    def test_attachment_paths_no_copy_scope_and_changed_file(self):
        original=self.root/'source-reference.txt';original.write_text('reference text',encoding='utf-8')
        record=self.attach(original)
        self.assertEqual(record['path'],str(original))
        self.assertEqual(list((self.root/'attachments').rglob('*.txt')),[])
        with self.assertRaises(ValueError):self.broker.attachments.records('b'*32,[record['id']])
        with self.assertRaises(ValueError):self.broker.attachments.records(self.instance,['../escape'])
        result=self.broker.attachments.read(self.instance,[record['id']],record['id'],0,self.root/'derived')
        self.assertEqual(result['text'],'reference text')
        original.write_text('changed content',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'发生变化'):
            self.broker.attachments.read(self.instance,[record['id']],record['id'],0,self.root/'derived')

    def test_attachment_images_through_both_api_protocols_and_real_mcp(self):
        image=self.root/'original-reference.png';image.write_bytes(base64.b64decode(PIXEL))
        record=self.attach(image);AttachmentAPI.identifier=record['id'];AttachmentAPI.seen=[]
        api=ThreadingHTTPServer(('127.0.0.1',0),AttachmentAPI)
        threading.Thread(target=api.serve_forever,daemon=True).start()
        try:
            for protocol in ('chat','responses'):
                profile={'kind':'api','model':'simulated-vision','base_url':f'http://127.0.0.1:{api.server_port}/v1','protocol':protocol,'vision':True}
                submitted=self.broker.submit({'instance':self.instance,'prompt':'read the attached image and Blender scene','profile':profile,'attachments':[record['id']]})
                deadline=time.time()+15
                while time.time()<deadline:
                    job=self.broker.get_job(submitted['id'])
                    if job['state']!='running':break
                    time.sleep(.05)
                self.assertEqual(job['state'],'inspected',job)
                self.assertEqual(job['attachment_reads'],1)
                self.assertEqual(job['successful_calls'],1)
                self.assertEqual(job['edits'],0)
            for path,data in AttachmentAPI.seen:
                if path.endswith('/responses'):
                    has_image=any(any(c.get('type')=='input_image' for c in m.get('content',[]) if isinstance(c,dict)) for m in data['input'] if isinstance(m.get('content'),list))
                else:
                    has_image=any(any(c.get('type')=='image_url' for c in m.get('content',[]) if isinstance(c,dict)) for m in data['messages'] if isinstance(m.get('content'),list))
                if any(m.get('role')=='tool' or m.get('type')=='function_call_output' for m in data.get('input',data.get('messages',[]))):
                    self.assertTrue(has_image)
            with self.assertRaisesRegex(ValueError,'图像输入'):
                self.broker.submit({'instance':self.instance,'prompt':'test','profile':dict(profile,vision=False),'attachments':[record['id']]})
        finally:api.shutdown();api.server_close()

    def test_model_discovery_async_and_no_credential_persistence(self):
        api=ThreadingHTTPServer(('127.0.0.1',0),FakeAPI)
        threading.Thread(target=api.serve_forever,daemon=True).start()
        try:
            response=request(self.url,self.broker.token,'/models/refresh',{'profile':{
                'kind':'api','base_url':f'http://127.0.0.1:{api.server_port}/v1','api_key':'model-discovery-test-key'}})
            path=self.root/'models'/(response['id']+'.json')
            deadline=time.time()+5
            while time.time()<deadline:
                value=json.loads(path.read_text(encoding='utf-8'))
                if value['state']!='loading':break
                time.sleep(.02)
            self.assertEqual(value['state'],'ready',value)
            self.assertEqual([m['id'] for m in value['models']],['test-model-a','test-model-b'])
            self.assertNotIn('model-discovery-test-key',path.read_text(encoding='utf-8'))
        finally:api.shutdown();api.server_close()

    def test_render_knowledge_switch_resources_and_preview(self):
        async def run():
            from mcp import McpError
            params=StdioServerParameters(command=sys.executable,args=[str(PROJECT/'bridge/mcp_server.py'),'--state',str(self.root),'--instance',self.instance])
            async with stdio_client(params) as (r,w):
                async with ClientSession(r,w) as session:
                    init=await session.initialize()
                    self.assertNotIn('材质真实感必须来自材质响应',init.instructions)
                    self.assertEqual(len((await session.list_resources()).resources),0)
                    denied=await session.call_tool('blender_render_knowledge',{'topic':'recipe'})
                    self.assertTrue(denied.isError)
                    with self.assertRaises(McpError):await session.read_resource('jc-render://g603-recipe')
            self.knowledge_enabled=True
            atomic_json(self.dir/'heartbeat.json',{'instance':self.instance,'time':time.time(),'use_render_knowledge':True})
            async with stdio_client(params) as (r,w):
                async with ClientSession(r,w) as session:
                    init=await session.initialize()
                    self.assertIn('材质真实感必须来自材质响应',init.instructions)
                    self.assertEqual(len((await session.list_tools()).tools),9)
                    self.assertEqual(len((await session.list_resources()).resources),3)
                    recipe=await session.read_resource('jc-render://g603-recipe')
                    self.assertEqual(json.loads(recipe.contents[0].text)['output']['width'],3000)
                    case=await session.call_tool('blender_render_knowledge',{'topic':'case'})
                    self.assertFalse(case.isError);self.assertIn('为什么前面大量返工',case.content[0].text)
                    preview=await session.call_tool('blender_render_knowledge',{'topic':'preview'})
                    self.assertFalse(preview.isError);self.assertEqual(preview.content[1].type,'image')
                    self.assertIn('历史案例',preview.content[0].text)
                    with self.assertRaises(McpError):await session.read_resource('jc-render://../../token')
                    bad=await session.call_tool('blender_render_knowledge',{'topic':'../../token'})
                    self.assertTrue(bad.isError)
        asyncio.run(run())

    def test_render_knowledge_api_modes_and_job_snapshot(self):
        api=ThreadingHTTPServer(('127.0.0.1',0),FakeAPI);FakeAPI.seen=[]
        threading.Thread(target=api.serve_forever,daemon=True).start()
        try:
            for protocol in ('chat','responses'):
                for enabled in (False,True):
                    FakeAPI.seen=[]
                    profile={'kind':'api','model':'simulated-model','base_url':f'http://127.0.0.1:{api.server_port}/v1','protocol':protocol,'vision':True}
                    j=self.broker.submit({'instance':self.instance,'prompt':'产品渲染验证','profile':profile,'use_render_knowledge':enabled})
                    deadline=time.time()+20
                    while time.time()<deadline:
                        job=self.broker.get_job(j['id'])
                        if job['state']!='running':break
                        time.sleep(.03)
                    self.assertEqual(job['state'],'completed',job)
                    self.assertEqual(job['use_render_knowledge'],enabled)
                    # External heartbeat changes must not change the submitted job's choice.
                    self.knowledge_enabled=not enabled
                    self.assertEqual(self.broker.knowledge_config({'instance':self.instance,'job':j['id']})['enabled'],enabled)
                    for _,data in FakeAPI.seen:
                        instructions=data.get('instructions') or data['messages'][0]['content']
                        self.assertEqual('材质真实感必须来自材质响应' in instructions,enabled)
                        names=[t.get('name') or t['function']['name'] for t in data['tools']]
                        self.assertEqual('blender_render_knowledge' in names,enabled)
        finally:api.shutdown();api.server_close()

    def test_knowledge_only_does_not_count_as_blender_work(self):
        api=ThreadingHTTPServer(('127.0.0.1',0),KnowledgeOnlyAPI)
        threading.Thread(target=api.serve_forever,daemon=True).start()
        try:
            j=self.broker.submit({'instance':self.instance,'prompt':'仅读取经验库','profile':{'kind':'api','model':'test','base_url':f'http://127.0.0.1:{api.server_port}/v1'},'use_render_knowledge':True})
            deadline=time.time()+15
            while time.time()<deadline:
                job=self.broker.get_job(j['id'])
                if job['state']!='running':break
                time.sleep(.03)
            self.assertEqual(job['state'],'failed',job)
            self.assertEqual(job['knowledge_reads'],1);self.assertEqual(job['successful_calls'],0);self.assertEqual(job['edits'],0)
            self.assertIn('没有成功调用',job['answer'])
        finally:api.shutdown();api.server_close()

    def test_switching_modes_does_not_inherit_previous_mode_reply(self):
        from unittest.mock import patch
        captured=[]
        def runner(profile,prompt,root,instance,jid,cancel,event):
            captured.append((profile['use_render_knowledge'],prompt))
            self.broker.call_tool({'instance':instance,'job':jid,'name':'blender_scene','arguments':{}})
            return 'DATABASE_REPLY_MARKER' if profile['use_render_knowledge'] else 'INDEPENDENT_REPLY_MARKER'
        previous=None
        with patch('bridge.broker.run_api',side_effect=runner):
            for enabled in (True,False,False):
                j=self.broker.submit({'instance':self.instance,'prompt':'继续检查','profile':{'kind':'api','model':'test'},'use_render_knowledge':enabled,'previous_job':previous})
                deadline=time.time()+5
                while time.time()<deadline:
                    job=self.broker.get_job(j['id'])
                    if job['state']!='running':break
                    time.sleep(.02)
                self.assertEqual(job['state'],'inspected',job);previous=j['id']
        self.assertNotIn('DATABASE_REPLY_MARKER',captured[1][1])
        self.assertIn('INDEPENDENT_REPLY_MARKER',captured[2][1])


if __name__=='__main__':unittest.main(verbosity=2)
