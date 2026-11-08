bl_info = {"name": "JC Blender Agent", "author": "JCOne / Codex", "version": (0, 1, 5),
    "blender": (4, 2, 0), "location": "3D View > Sidebar > JC Agent", "description": "用自然语言通过本地 Agent 或 API 控制 Blender，包含 MCP 服务", "category": "3D View"}

import bpy
from bpy.props import StringProperty, EnumProperty, BoolProperty, PointerProperty, IntProperty, CollectionProperty
import base64
import contextlib
import io
import json
import math
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
import urllib.error
import urllib.request
import uuid
import mathutils
import re
import signal
import importlib.util
from bpy.app.handlers import persistent

_instance = None
_root = None
_url = None
_token = None
_last_heartbeat = 0
_last_status = 0
_job = ""
_last_checkpoint = ""
_last_edit_checkpoint = ""
_busy = False
_broker_proc = None
_models_due = 0
_model_request = None
_loading_models = False
_task_window_pointer = None
_pin_requests = set()
_api_restoring = False
_api_key_scope = ""
_local_api = None


def schedule_models(self,context):
    global _models_due,_loading_models,_model_request
    _model_request=None
    if hasattr(self,"models"):
        _loading_models=True
        try:self.models.clear();self.model_index=-1
        finally:_loading_models=False
    if getattr(self,"auto_models",True):
        _models_due=time.monotonic()+.7
    else:_models_due=0


def select_model(self,context):
    if _loading_models or not 0<=self.model_index<len(self.models):return
    identifier=self.models[self.model_index].identifier
    setattr(self,"api_model" if self.agent=="api" else self.agent+"_model",identifier)


def model_profile():
    rt=runtime();prefs=preferences()
    profile={"kind":rt.agent}
    if rt.agent=="api":profile.update(base_url=rt.base_url,key_env=rt.key_env,api_key=effective_api_key())
    else:profile["executable"]=getattr(prefs,rt.agent+"_executable","") if prefs else ""
    return profile


def model_signature():
    rt=runtime()
    return (rt.agent,rt.base_url if rt.agent=="api" else "",rt.key_env if rt.agent=="api" else "")


def model_tick():
    global _models_due,_model_request,_loading_models
    try:
        rt=runtime()
        if _models_due and time.monotonic()>=_models_due:
            _models_due=0
            if not _url:connect()
            _models_due=0
            profile=model_profile()
            response=http("/models/refresh",{"profile":profile},timeout=.75)
            _model_request=(response["id"],model_signature(),time.monotonic())
            rt.model_status="正在获取模型列表…"
        if _model_request:
            identifier,signature,started=_model_request
            data=read_json(state_root()/"models"/(identifier+".json"),{})
            if data.get("state") in ("ready","failed"):
                _model_request=None
                if signature!=model_signature():return .3
                if data["state"]=="failed":rt.model_status=data.get("error","获取失败")
                else:
                    current=getattr(rt,"api_model" if rt.agent=="api" else rt.agent+"_model")
                    _loading_models=True
                    try:
                        rt.models.clear()
                        for item in data["models"]:
                            entry=rt.models.add();entry.identifier=item["id"];entry.name=item["name"]
                        rt.model_index=next((i for i,m in enumerate(rt.models) if m.identifier==current),-1)
                    finally:_loading_models=False
                    rt.model_status=str(len(rt.models))+" 个模型 · "+data["source"]
            elif time.monotonic()-started>40:
                _model_request=None;rt.model_status="获取模型列表超时，可点击刷新或手填 ID"
    except Exception as e:
        _model_request=None
        try:runtime().model_status=str(e)[:220]
        except Exception:pass
    return .3


def source_window(context):
    return context.window


def state_root():
    return pathlib.Path(os.environ.get("JC_BLENDER_STATE", pathlib.Path(os.environ.get("LOCALAPPDATA", pathlib.Path.home() / ".local/share")) / "JCBlenderAgent"))


def atomic_json(path, value):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False)
        for attempt in range(6):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if attempt == 5: raise
                time.sleep(.005 * (attempt + 1))
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def read_json(path, default=None):
    try: return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (ValueError, OSError): return default


def preferences():
    addon = bpy.context.preferences.addons.get(__package__)
    return addon.preferences if addon else None


def runtime():
    return bpy.context.window_manager.jc_agent


def render_knowledge_enabled():
    prefs = preferences()
    return prefs.use_render_knowledge if prefs else runtime().use_render_knowledge


def update_render_knowledge(self, context):
    if _root and _instance:
        hb = read_json(_root/"heartbeat.json", {})
        if hb:
            hb.update(time=time.time(), use_render_knowledge=render_knowledge_enabled())
            atomic_json(_root/"heartbeat.json", hb)


def bridge_root():
    here = pathlib.Path(__file__).resolve().parent
    # Release ZIP includes runtime/bridge. Source checkout uses the top-level bridge.
    bundled = here / "runtime"
    return bundled if (bundled / "bridge/broker.py").is_file() else here.parents[1]


def local_api():
    global _local_api
    if _local_api is None:
        spec=importlib.util.spec_from_file_location('_jc_local_api',bridge_root()/'bridge/local_api.py')
        _local_api=importlib.util.module_from_spec(spec);spec.loader.exec_module(_local_api)
    return _local_api


def persist_api_settings():
    if _api_restoring:return
    rt=runtime()
    local_api().save_settings(state_root(),{key:getattr(rt,key) for key in local_api().FIELDS})


def refresh_key_status():
    rt=runtime()
    if not rt.remember_api_key:
        rt.api_key_status='本轮临时使用，不读取已保存的 Key';return
    try:
        saved=bool(local_api().read_key(rt.base_url))
        rt.api_key_status='已保存当前地址的 Key，留空自动使用' if saved else '输入后自动保存到 Windows 凭据管理器'
    except Exception:
        rt.api_key_status='本机凭据暂不可用；仍可临时输入 Key'


def effective_api_key():
    rt=runtime();scope=local_api().normalize_endpoint(rt.base_url)
    if rt.api_key.strip():
        if _api_key_scope!=scope:raise ValueError('API 地址已变更，请为当前地址重新填写 Key')
        return rt.api_key.strip()
    if rt.remember_api_key:
        try:return local_api().read_key(scope)
        except Exception:
            rt.api_key_status='本机凭据暂不可用；可重新输入或使用环境变量'
    return ''


def update_api_settings(self,context):
    if _api_restoring:return
    try:persist_api_settings()
    except Exception:self.api_key_status='地址或本机设置未保存，请检查基础地址'


def update_api_connection_settings(self,context):
    if _api_restoring:return
    update_api_settings(self,context)
    schedule_models(self,context)


def update_api_endpoint(self,context):
    global _api_key_scope,_api_restoring
    if _api_restoring:return
    _api_restoring=True
    try:self.api_key='';_api_key_scope=''
    finally:_api_restoring=False
    refresh_key_status();update_api_connection_settings(self,context)


def update_api_key(self,context):
    global _api_key_scope
    if _api_restoring:return
    try:
        _api_key_scope=local_api().normalize_endpoint(self.base_url)
        if self.api_key.strip() and self.remember_api_key:
            local_api().save_key(self.base_url,self.api_key)
        refresh_key_status();persist_api_settings()
    except Exception:
        self.api_key_status='Key 未保存到本机；当前输入仍可临时使用'
    schedule_models(self,context)


@persistent
def restore_api_settings(*_):
    global _api_restoring,_api_key_scope
    if not hasattr(bpy.context.window_manager,'jc_agent'):return
    _api_restoring=True
    try:
        rt=runtime();rt.api_key='';_api_key_scope=''
        for key,value in local_api().load_settings(state_root()).items():setattr(rt,key,value)
    finally:_api_restoring=False
    refresh_key_status()


def python_exe():
    prefs = preferences()
    if prefs and prefs.python_executable:
        return bpy.path.abspath(prefs.python_executable)
    candidate = shutil.which("python")
    if candidate and "WindowsApps" not in candidate:
        return candidate
    root = pathlib.Path(bpy.app.binary_path).parent
    version = f"{bpy.app.version[0]}.{bpy.app.version[1]}"
    for rel in (f"{version}/python/bin/python.exe", f"{version}/python/bin/python3", "../Resources/" + version + "/python/bin/python3.11"):
        p = (root / rel).resolve()
        if p.is_file(): return str(p)
    raise RuntimeError("找不到独立 Python。请在插件偏好设置指定 Python 3.10+ 可执行文件")


def http(path, payload=None, timeout=.35):
    if not _url or not _token: raise RuntimeError("服务未连接")
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(_url + path, data=data, headers={"Authorization": "Bearer " + _token, "Content-Type": "application/json"})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try: message = json.loads(e.read()).get("error", str(e))
        except Exception: message = str(e)
        raise RuntimeError(message) from None


def scene_info():
    scene = bpy.context.scene
    objects = list(scene.objects)
    return {"blender_version": bpy.app.version_string, "file": bpy.data.filepath, "scene": scene.name,
        "frame": scene.frame_current, "frame_start": scene.frame_start, "frame_end": scene.frame_end,
        "engine": scene.render.engine, "camera": scene.camera.name if scene.camera else None,
        "selected": [o.name for o in bpy.context.selected_objects],
        "active": bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
        "object_count": len(objects), "objects_truncated": len(objects) > 250,
        "objects": [{"name":o.name,"type":o.type,"location":list(o.location),"selected":o.select_get()} for o in objects[:250]]}


def object_info(name):
    obj = bpy.data.objects.get(name)
    if obj is None: raise ValueError("找不到对象：" + name)
    result = {"name":obj.name,"type":obj.type,"location":list(obj.location),"rotation_euler":list(obj.rotation_euler),
        "scale":list(obj.scale),"dimensions":list(obj.dimensions),"parent":obj.parent.name if obj.parent else None,
        "modifiers":[{"name":m.name,"type":m.type} for m in obj.modifiers],
        "materials":[m.name if m else None for m in getattr(obj.data,"materials",[])],
        "custom_properties":{k:str(v)[:500] for k,v in obj.items()}}
    if obj.type == "MESH": result["geometry"] = {"vertices":len(obj.data.vertices),"faces":len(obj.data.polygons)}
    anim = obj.animation_data
    result["animation"] = {"action":anim.action.name if anim and anim.action else None,"drivers":len(anim.drivers) if anim else 0}
    return result


def artifact_dir(command):
    path = pathlib.Path(command["artifact_dir"]).resolve()
    allowed = (state_root() / "artifacts" / _instance).resolve()
    if path != allowed and allowed not in path.parents: raise ValueError("Invalid artifact path")
    path.mkdir(parents=True, exist_ok=True)
    return path


def checkpoint(directory, label="checkpoint"):
    global _last_checkpoint
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)[:36]
    path = directory / (time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8] + "-" + safe + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(path), copy=True, check_existing=False)
    _last_checkpoint = str(path)
    return str(path)


@contextlib.contextmanager
def view_context():
    windows = list(bpy.context.window_manager.windows)
    windows.sort(key=lambda w: w.as_pointer() != _task_window_pointer)
    for window in windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                region = next((r for r in area.regions if r.type == "WINDOW"), None)
                with bpy.context.temp_override(window=window, area=area, region=region):
                    yield
                return
    raise RuntimeError("需要打开含 3D View 的交互窗口；后台模式不能提供真实视口截图")


def execute_command(command):
    global _busy, _last_edit_checkpoint
    name, args = command["name"], command.get("arguments", {})
    directory = artifact_dir(command)
    if name == "blender_scene": return scene_info()
    if name == "blender_object": return object_info(args["name"])
    if name == "blender_checkpoint": return {"checkpoint":checkpoint(directory, args.get("label", "manual"))}
    if name == "blender_restore":
        path = pathlib.Path(args["checkpoint"]).resolve()
        allowed = (state_root() / "artifacts" / _instance).resolve()
        if allowed not in path.parents or path.suffix.lower() != ".blend" or not path.is_file():
            raise ValueError("只能恢复本 Blender 实例由此插件创建的 .blend 快照")
        before = checkpoint(directory, "before-restore")
        bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
        _last_edit_checkpoint = before
        return {"restored":str(path),"before_restore":before}
    if name == "blender_execute":
        prefs = preferences()
        if prefs and not prefs.allow_python: raise RuntimeError("插件设置中关闭了 Agent Python 执行")
        code = args["code"]
        if not isinstance(code,str) or len(code)>200000: raise ValueError("代码过长或格式错误")
        # Compile before checkpoint so syntax errors do not create misleading edit records.
        compiled = compile(code, "<JC Agent>", "exec")
        saved = checkpoint(directory, args.get("description", "edit"))
        _last_edit_checkpoint = saved
        stdout = io.StringIO()
        namespace = {"bpy":bpy,"mathutils":mathutils,"math":math,"Vector":mathutils.Vector,"Matrix":mathutils.Matrix,"result":None}
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stdout):
                if bpy.app.background:
                    exec(compiled, namespace, namespace)
                else:
                    with view_context(): exec(compiled, namespace, namespace)
            result = namespace.get("result")
            json.dumps(result)
            bpy.context.view_layer.update()
            return {"result":result,"stdout":stdout.getvalue()[-12000:],"checkpoint":saved}
        except Exception:
            return {"error":traceback.format_exc()[-8000:],"stdout":stdout.getvalue()[-8000:],"checkpoint":saved,
                "partial_changes_possible":True,"notice":"操作可能已部分生效；读取场景后修复，或按快照回退"}
    if name == "blender_viewport":
        path = directory / (uuid.uuid4().hex + "-viewport.png")
        with view_context():
            bpy.ops.screen.screenshot_area(filepath=str(path))
        return {"image_path":str(path),"source":"interactive viewport screenshot"}
    if name == "blender_preview":
        scene = bpy.context.scene
        if not scene.camera: raise RuntimeError("场景没有相机，请先设置相机")
        size = int(args.get("max_size", 768))
        if not 64<=size<=1536: raise ValueError("max_size 应在 64 至 1536")
        render = scene.render
        fields = ("resolution_x","resolution_y","resolution_percentage","filepath","use_file_extension")
        old = {k:getattr(render,k) for k in fields}
        old_fmt = render.image_settings.file_format
        path = directory / (uuid.uuid4().hex + "-preview.png")
        try:
            ratio = size / max(render.resolution_x,render.resolution_y)
            render.resolution_x=max(16,round(render.resolution_x*ratio));render.resolution_y=max(16,round(render.resolution_y*ratio))
            render.resolution_percentage=100;render.filepath=str(path);render.image_settings.file_format="PNG";render.use_file_extension=True
            bpy.ops.render.render(write_still=True)
        finally:
            for k,v in old.items():setattr(render,k,v)
            render.image_settings.file_format=old_fmt
        return {"image_path":str(path),"source":"Blender camera render"}
    raise ValueError("Unknown command: " + str(name))


def write_log(job):
    text = bpy.data.texts.get("JC_Agent_Log") or bpy.data.texts.new("JC_Agent_Log")
    lines = ["JC Blender Agent", "Task: " + job.get("id", ""), "State: " + job.get("state", ""), "", "用户：" + job.get("prompt", ""), ""]
    lines += [time.strftime("%H:%M:%S",time.localtime(e["time"]))+" ["+e["kind"]+"] "+e["message"] for e in job.get("events",[])]
    lines += ["", "Agent：", job.get("answer", "")]
    text.clear();text.write("\n".join(lines))


def tick():
    global _last_heartbeat, _last_status, _busy, _job
    if not _instance or not _root: return None
    try:
        now=time.time()
        service=read_json(state_root()/"service-heartbeat.json",{})
        if now-service.get("time",0)>8:
            rt=runtime();rt.connected=False;rt.status="本地服务已退出；检查场景后点击连接重新启动。未重发任何操作。"
            if rt.job_state in ("running","cancelling"):rt.job_state="interrupted"
            return .5
        if now-_last_heartbeat>1:
            atomic_json(_root/"heartbeat.json", {"instance":_instance,"pid":os.getpid(),"time":now,"version":bpy.app.version_string,"file":bpy.data.filepath,"scene":bpy.context.scene.name,"use_render_knowledge":render_knowledge_enabled()})
            _last_heartbeat=now
        # A claimed command is never replayed, even if Blender exits during execution.
        for path in sorted((_root/"inbox").glob("*.json"))[:1]:
            cmd=read_json(path,{})
            claimed=path.with_suffix(".running")
            try:path.rename(claimed)
            except OSError:continue
            try:
                if cmd.get("instance")!=_instance or path.with_suffix(".cancel").exists() or cmd.get("expires",0)<now:
                    result={"error":"Command expired, cancelled, or wrong Blender instance; not executed"}
                else:
                    _busy=True
                    target=next((w for w in bpy.context.window_manager.windows if w.as_pointer()==_task_window_pointer),None)
                    if _task_window_pointer and target is None:raise RuntimeError("任务原窗口已关闭，停止操作")
                    if target:
                        with bpy.context.temp_override(window=target):result=execute_command(cmd)
                    else:result=execute_command(cmd)
            except Exception:
                result={"error":traceback.format_exc()[-8000:]}
            finally:_busy=False
            atomic_json(_root/"heartbeat.json", {"instance":_instance,"pid":os.getpid(),"time":time.time(),"version":bpy.app.version_string,"file":bpy.data.filepath,"scene":bpy.context.scene.name,"use_render_knowledge":render_knowledge_enabled()})
            atomic_json(_root/"outbox"/path.name,result)
            claimed.rename(claimed.with_suffix(".done"))
        if now-_last_status>.7:
            _last_status=now
            rt=runtime();rt.connected=True
            for item in rt.attachments:
                record=read_json(state_root()/"attachments"/_instance/(item.identifier+".json"),{})
                if record:
                    item.state=record.get("state","checking");item.status=record.get("status","");item.size=record.get("size",0)
            if _job:
                # Local file read: no HTTP or Agent network waits on Blender's UI thread.
                job=read_json(state_root()/"jobs"/(_job+".json"),{})
                if job:
                    rt.job_state=job.get("state","")
                    event=job.get("events",[{}])[-1] if job.get("events") else {}
                    kind=event.get("kind","")
                    names={"blender_scene":"读取场景","blender_object":"检查对象","blender_execute":"修改场景","blender_viewport":"查看实际视口","blender_preview":"渲染预览","blender_checkpoint":"保存快照","blender_restore":"恢复快照"}
                    if kind=="tool":rt.status=names.get(event.get("message"),"正在操作 Blender")
                    elif kind=="tool_result":rt.status="Blender 已返回操作结果"
                    else:rt.status=event.get("message","等待 Agent")[:220]
                    rt.answer=job.get("answer","")[:10000]
                    rt.artifact_dir=job.get("artifact_dir","")
                    if rt.log_updated < job.get("updated",0):write_log(job);rt.log_updated=job.get("updated",0)
            for win in bpy.context.window_manager.windows:
                for area in win.screen.areas:
                    if area.type=="VIEW_3D":area.tag_redraw()
    except Exception as e:
        try:runtime().status=str(e)[:220]
        except Exception:pass
    return .25


def connect():
    global _instance,_root,_url,_token,_last_heartbeat,_broker_proc,_models_due
    root=state_root();root.mkdir(parents=True,exist_ok=True)
    # Reuse an existing authenticated service; no global config or account changes.
    discovery=read_json(root/"broker.json",{})
    token_file=root/"token"
    ready=False
    if token_file.is_file() and discovery.get("url"):
        _token=token_file.read_text(encoding="ascii").strip();_url=discovery["url"]
        try:
            health=http("/health",timeout=.5)
            ready=bool(health.get("ok"))
            expected=".".join(map(str,bl_info["version"]))
            if ready and health.get("version")!=expected:
                active=[j for p in (root/"jobs").glob("*.json") if (j:=read_json(p,{})).get("state") in ("running","cancelling")]
                if active:raise RuntimeError("旧版服务还有任务运行，请结束任务后再连接新版")
                pid=discovery.get("pid")
                if type(pid) is not int or pid<=0 or pid==os.getpid():raise RuntimeError("本地服务进程信息无效")
                # Version upgrade: authenticated service, no active jobs, only its own recorded PID.
                os.kill(pid,signal.SIGTERM)
                time.sleep(.2)
                ready=False
        except RuntimeError:raise
        except Exception:pass
    if not ready:
        flags={"creationflags":subprocess.CREATE_NO_WINDOW} if os.name=="nt" else {}
        log=(root/"broker-stderr.log").open("ab")
        try:
            _broker_proc=subprocess.Popen([python_exe(),"-m","bridge.broker","--state",str(root)],cwd=str(bridge_root()),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=log,**flags)
        finally:log.close()
        # Start operator may wait briefly; ongoing task execution never waits here.
        for _ in range(40):
            time.sleep(.1)
            discovery=read_json(root/"broker.json",{})
            if token_file.is_file() and discovery.get("url"):
                _token=token_file.read_text(encoding="ascii").strip();_url=discovery["url"]
                try:
                    if http("/health",timeout=.15).get("ok"):ready=True;break
                except Exception:pass
        if not ready:raise RuntimeError("服务未启动，请查看 "+str(root/"broker-stderr.log"))
    new_instance=not _instance
    if new_instance:_instance=uuid.uuid4().hex
    _root=root/"instances"/_instance
    (_root/"inbox").mkdir(parents=True,exist_ok=True);(_root/"outbox").mkdir(parents=True,exist_ok=True)
    _last_heartbeat=0
    if not bpy.app.timers.is_registered(tick):bpy.app.timers.register(tick,first_interval=.1,persistent=True)
    runtime().connected=True;runtime().status="已连接："+_url
    atomic_json(_root/"heartbeat.json",{"instance":_instance,"pid":os.getpid(),"time":time.time(),"version":bpy.app.version_string,"file":bpy.data.filepath,"scene":bpy.context.scene.name,"use_render_knowledge":render_knowledge_enabled()})
    if new_instance and runtime().attachments:
        paths=[a.filepath for a in runtime().attachments]
        runtime().attachments.clear()
        add_attachment_paths(paths)
    if runtime().auto_models and not runtime().models:_models_due=time.monotonic()+.1


class JCPreferences(bpy.types.AddonPreferences):
    bl_idname=__package__
    python_executable:StringProperty(name="Python 可执行文件",subtype="FILE_PATH",default="",description="留空自动检测 Python 3.10+；不能填写 blender.exe")
    codex_executable:StringProperty(name="Codex 可执行文件",subtype="FILE_PATH",default="")
    claude_executable:StringProperty(name="Claude 可执行文件",subtype="FILE_PATH",default="")
    allow_python:BoolProperty(name="允许 Agent 执行 Blender Python（具备本机 Python 权限）",default=True)
    use_render_knowledge:BoolProperty(name="参考产品渲染经验库",default=True,update=update_render_knowledge,description="开启时参考随插件携带的材质、布光和爆炸图经验；关闭时自主调试。新任务生效")
    def draw(self,context):
        layout=self.layout
        for key in ("python_executable","codex_executable","claude_executable","allow_python","use_render_knowledge"):layout.prop(self,key)
        layout.label(text="API Key 可保存在本机 Windows 凭据管理器，不写入 .blend。")


class JCModelItem(bpy.types.PropertyGroup):
    identifier:StringProperty()


class JCAttachmentItem(bpy.types.PropertyGroup):
    identifier:StringProperty()
    filepath:StringProperty(subtype="FILE_PATH")
    kind:StringProperty(default="file")
    state:StringProperty(default="checking")
    status:StringProperty(default="正在检查路径…")
    size:bpy.props.FloatProperty(default=0)


class JCRuntime(bpy.types.PropertyGroup):
    use_render_knowledge:BoolProperty(name="参考产品渲染经验库",default=True,options={"SKIP_SAVE"},update=update_render_knowledge,description="开启：参考内置经验；关闭：自主调试。对下一任务生效")
    agent:EnumProperty(name="Agent",items=[("codex","Codex 本地 Agent","使用已登录 Codex CLI"),("claude","Claude Code 本地 Agent","使用已登录 Claude Code CLI"),("api","API Agent","自填模型和网关，内置工具循环通过 MCP 控制 Blender")],default="codex",update=schedule_models)
    prompt:StringProperty(name="描述",default="",options={"SKIP_SAVE"},description="Blender 5.2+：Shift+Enter 换行，可粘贴多行；拖动输入框右下角调高度")
    prompt_text:PointerProperty(name="多行描述文本",type=bpy.types.Text,options={"SKIP_SAVE"})
    codex_model:StringProperty(name="Codex 模型",default="",description="留空沿用本地 Agent 默认模型")
    claude_model:StringProperty(name="Claude 模型",default="")
    api_model:StringProperty(name="API 模型 ID",default="",options={"SKIP_SAVE"},update=update_api_settings)
    base_url:StringProperty(name="API 基础地址",default="https://api.openai.com/v1",options={"SKIP_SAVE"},update=update_api_endpoint)
    protocol:EnumProperty(name="API 协议",items=[("chat","Chat Completions","兼容此协议的模型和网关"),("responses","Responses","兼容 Responses 的模型和网关")],default="chat",options={"SKIP_SAVE"},update=update_api_settings)
    key_env:StringProperty(name="Key 环境变量",default="OPENAI_API_KEY",options={"SKIP_SAVE"},update=update_api_connection_settings)
    api_key:StringProperty(name="API Key",subtype="PASSWORD",default="",options={"SKIP_SAVE"},update=update_api_key)
    remember_api_key:BoolProperty(name="记住 API Key（仅本机）",default=True,options={"SKIP_SAVE"},update=update_api_key)
    api_key_status:StringProperty(default="输入后自动保存到 Windows 凭据管理器",options={"SKIP_SAVE"})
    auto_models:BoolProperty(name="自动获取模型列表",default=True,update=schedule_models)
    models:CollectionProperty(type=JCModelItem,options={"SKIP_SAVE"})
    model_index:IntProperty(default=-1,min=-1,update=select_model,options={"SKIP_SAVE"})
    model_status:StringProperty(default="连接后自动获取，也可点击刷新",options={"SKIP_SAVE"})
    vision:BoolProperty(name="模型支持图像输入",default=True,options={"SKIP_SAVE"},update=update_api_settings,description="将真实视口或渲染图交给模型核查；纯文本模型请关闭")
    max_steps:IntProperty(name="最多推理轮数",min=1,max=100,default=24,options={"SKIP_SAVE"},update=update_api_settings)
    attachments:CollectionProperty(type=JCAttachmentItem,options={"SKIP_SAVE"})
    attachment_index:IntProperty(default=0,min=0,options={"SKIP_SAVE"})
    video_frames:IntProperty(name="视频采样帧",default=8,min=1,max=24,description="Agent 按需读取的均匀采样帧数量；不是完整视频观看，不含音频")
    connected:BoolProperty(default=False,options={"SKIP_SAVE"})
    status:StringProperty(default="点击连接开始",options={"SKIP_SAVE"})
    job_state:StringProperty(default="",options={"SKIP_SAVE"})
    answer:StringProperty(default="",options={"SKIP_SAVE"})
    artifact_dir:StringProperty(default="",options={"SKIP_SAVE"})
    log_updated:bpy.props.FloatProperty(default=0,options={"SKIP_SAVE"})


class JCConnect(bpy.types.Operator):
    bl_idname="jc_agent.connect";bl_label="连接 / 启动服务"
    def execute(self,context):
        try:connect();return {"FINISHED"}
        except Exception as e:self.report({"ERROR"},str(e));return {"CANCELLED"}


class JCDisconnect(bpy.types.Operator):
    bl_idname="jc_agent.disconnect";bl_label="断开控制"
    def execute(self,context):
        global _instance,_root,_job
        if _job:
            try:http("/cancel",{"id":_job})
            except Exception:pass
        if _root:
            atomic_json(_root/"heartbeat.json",{"instance":_instance,"time":0})
        if bpy.app.timers.is_registered(tick):bpy.app.timers.unregister(tick)
        _instance=None;_root=None;_job="";runtime().connected=False;runtime().status="已断开"
        return {"FINISHED"}


class JCSend(bpy.types.Operator):
    bl_idname="jc_agent.send";bl_label="交给 Agent 执行"
    use_text:BoolProperty(default=False)
    def execute(self,context):
        global _job,_task_window_pointer
        try:
            if not _instance:connect()
            rt=runtime();prefs=preferences()
            prompt=rt.prompt_text.as_string() if self.use_text and rt.prompt_text else rt.prompt
            if not prompt.strip():raise ValueError("请先填写描述，说明如何使用所附文件")
            if any(a.state!="ready" for a in rt.attachments):raise ValueError("附件路径尚未就绪，请等待检查或移除失效附件")
            profile={"kind":rt.agent,"max_steps":rt.max_steps}
            if rt.agent=="api":
                profile.update(model=rt.api_model,base_url=rt.base_url,protocol=rt.protocol,key_env=rt.key_env,api_key=effective_api_key(),vision=rt.vision)
            else:
                profile["model"]=getattr(rt,rt.agent+"_model")
                profile["executable"]=getattr(prefs,rt.agent+"_executable","") if prefs else ""
            target=source_window(context)
            _task_window_pointer=target.as_pointer()
            with context.temp_override(window=target):
                sent_context={"scene":bpy.context.scene.name,"file":bpy.data.filepath,"selected":[o.name for o in bpy.context.selected_objects],
                    "active":bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,"frame":bpy.context.scene.frame_current,"blender_version":bpy.app.version_string}
            result=http("/jobs",{"instance":_instance,"prompt":prompt,"profile":profile,"use_render_knowledge":render_knowledge_enabled(),"previous_job":_job,"scene_context":sent_context,"attachments":[a.identifier for a in rt.attachments]},timeout=2)
            _job=result["id"];rt.job_state="running";rt.answer="";rt.log_updated=0
            rt.status="任务已发送："+_job[:8]
            return {"FINISHED"}
        except Exception as e:self.report({"ERROR"},str(e));return {"CANCELLED"}


class JCCancel(bpy.types.Operator):
    bl_idname="jc_agent.cancel";bl_label="停止后续操作"
    def execute(self,context):
        try:
            if _job:http("/cancel",{"id":_job},timeout=1)
            return {"FINISHED"}
        except Exception as e:self.report({"ERROR"},str(e));return {"CANCELLED"}


def add_attachment_paths(paths):
    if not _instance:connect()
    rt=runtime()
    existing={a.filepath for a in rt.attachments}
    paths=list(dict.fromkeys(str(pathlib.Path(p)) for p in paths if str(pathlib.Path(p)) not in existing))
    if not paths:return
    if len(paths)+len(rt.attachments)>8:raise ValueError("每个任务最多引用 8 个附件；请先移除不需要的文件")
    result=http("/attachments/add",{"instance":_instance,"paths":paths,"blender_executable":bpy.app.binary_path,"video_frames":rt.video_frames},timeout=1.5)
    for data in result["attachments"]:
        item=rt.attachments.add();item.identifier=data["id"];item.name=data["name"];item.filepath=data["path"]
        item.kind=data["kind"];item.state=data["state"];item.status=data["status"]
    rt.attachment_index=len(rt.attachments)-1


class JCAddAttachments(bpy.types.Operator):
    bl_idname="jc_agent.add_attachments";bl_label="添加附件引用"
    bl_description="选择本地文件，仅记录路径；发送后 Agent 通过 MCP 按需读取，不复制原文件"
    files:CollectionProperty(type=bpy.types.OperatorFileListElement)
    directory:StringProperty(subtype="DIR_PATH")
    filepath:StringProperty(subtype="FILE_PATH")
    filter_glob:StringProperty(default="*",options={"HIDDEN"})
    def invoke(self,context,event):
        context.window_manager.fileselect_add(self);return {"RUNNING_MODAL"}
    def draw(self,context):
        self.layout.label(text="仅引用本地路径；原文件不复制到插件")
        self.layout.prop(runtime(),"video_frames")
    def execute(self,context):
        try:
            paths=[str(pathlib.Path(self.directory)/f.name) for f in self.files] if self.files else [self.filepath]
            add_attachment_paths(paths)
            return {"FINISHED"}
        except Exception as e:self.report({"ERROR"},str(e));return {"CANCELLED"}


class JCPasteAttachments(bpy.types.Operator):
    bl_idname="jc_agent.paste_attachments";bl_label="粘贴文件引用"
    bl_description="读取资源管理器复制的文件路径；请先复制文件，然后点此按钮"
    def execute(self,context):
        try:
            if os.name!="nt":raise ValueError("当前系统请使用添加附件按钮")
            import ctypes
            from ctypes import wintypes
            user=ctypes.WinDLL("user32",use_last_error=True);shell=ctypes.WinDLL("shell32",use_last_error=True)
            user.GetClipboardData.argtypes=[wintypes.UINT];user.GetClipboardData.restype=wintypes.HANDLE
            shell.DragQueryFileW.argtypes=[wintypes.HANDLE,wintypes.UINT,wintypes.LPWSTR,wintypes.UINT]
            shell.DragQueryFileW.restype=wintypes.UINT
            if not user.IsClipboardFormatAvailable(15):raise ValueError("剪贴板里没有文件。请复制资源管理器中的文件，或点击添加附件")
            if not user.OpenClipboard(None):raise ValueError("剪贴板忙，请稍后重试")
            try:
                handle=user.GetClipboardData(15);count=shell.DragQueryFileW(handle,0xFFFFFFFF,None,0)
                if not 1<=count<=8:raise ValueError("请复制 1 至 8 个文件")
                paths=[]
                for index in range(count):
                    length=shell.DragQueryFileW(handle,index,None,0)
                    if length>32767:raise ValueError("文件路径过长")
                    buffer=ctypes.create_unicode_buffer(length+1)
                    shell.DragQueryFileW(handle,index,buffer,length+1);paths.append(buffer.value)
            finally:user.CloseClipboard()
            add_attachment_paths(paths)
            return {"FINISHED"}
        except Exception as e:self.report({"ERROR"},str(e));return {"CANCELLED"}


class JCRemoveAttachment(bpy.types.Operator):
    bl_idname="jc_agent.remove_attachment";bl_label="移除附件引用"
    bl_description="只移除列表中的路径引用，不删除原文件"
    def execute(self,context):
        rt=runtime()
        if rt.attachments:
            rt.attachments.remove(min(rt.attachment_index,len(rt.attachments)-1))
            rt.attachment_index=max(0,min(rt.attachment_index,len(rt.attachments)-1))
        return {"FINISHED"}


class JCAttachmentList(bpy.types.UIList):
    bl_idname="JC_AGENT_UL_attachments"
    def draw_item(self,context,layout,data,item,icon,active_data,active_propname,index):
        icons={"image":"IMAGE_DATA","video":"FILE_MOVIE","text":"TEXT","file":"FILE"}
        row=layout.row(align=True)
        row.label(text=item.name,icon=icons.get(item.kind,"FILE"))
        row.label(text="",icon="CHECKMARK" if item.state=="ready" else "ERROR" if item.state=="failed" else "TIME")


class JCNewText(bpy.types.Operator):
    bl_idname="jc_agent.new_text";bl_label="新建多行描述"
    def execute(self,context):
        text=bpy.data.texts.new("JC_Agent_Request")
        text.write(runtime().prompt or "只修改选中的对象：\n1. 描述形状、材质、灯光或动画要求。\n2. 保留其他对象。\n3. 完成后核查结果。")
        runtime().prompt_text=text
        self.report({"INFO"},"已创建 JC_Agent_Request，可在文本编辑器编辑后点击从文本发送")
        return {"FINISHED"}


class JCClearAPIKey(bpy.types.Operator):
    bl_idname='jc_agent.clear_api_key';bl_label='清除本机 Key'
    bl_description='删除当前 API 地址保存在本机的 Key，并清空本轮输入；不删除其他地址的 Key'
    def execute(self,context):
        try:
            local_api().delete_key(runtime().base_url)
            runtime().api_key='';refresh_key_status();schedule_models(runtime(),context)
            self.report({'INFO'},'当前地址保存在本机的 Key 已清除');return {'FINISHED'}
        except Exception:
            self.report({'ERROR'},'无法清除本机凭据，请检查 Windows 凭据管理器');return {'CANCELLED'}


class JCShowLog(bpy.types.Operator):
    bl_idname="jc_agent.show_log";bl_label="复制完整回复 / 日志"
    def execute(self,context):
        text=bpy.data.texts.get("JC_Agent_Log")
        if not text:self.report({"INFO"},"尚无任务日志");return {"CANCELLED"}
        context.window_manager.clipboard=text.as_string()
        self.report({"INFO"},"完整日志已复制；也可在文本编辑器选择 JC_Agent_Log")
        return {"FINISHED"}


class JCOpenArtifacts(bpy.types.Operator):
    bl_idname="jc_agent.artifacts";bl_label="打开快照 / 截图目录"
    def execute(self,context):
        path=runtime().artifact_dir or str(state_root()/"artifacts")
        pathlib.Path(path).mkdir(parents=True,exist_ok=True)
        bpy.ops.wm.path_open(filepath=path)
        return {"FINISHED"}


class JCExportMCP(bpy.types.Operator):
    bl_idname="jc_agent.export_mcp";bl_label="复制外部 MCP 配置"
    def execute(self,context):
        try:
            if not _instance:connect()
            config={"mcpServers":{"jc_blender":{"command":python_exe(),"args":[str(bridge_root()/"bridge/mcp_server.py"),"--state",str(state_root()),"--instance",_instance]}}}
            context.window_manager.clipboard=json.dumps(config,ensure_ascii=False,indent=2)
            self.report({"INFO"},"当前 Blender 实例的 MCP JSON 配置已复制；重连新实例后需重新复制")
            return {"FINISHED"}
        except Exception as e:self.report({"ERROR"},str(e));return {"CANCELLED"}


class JCRestore(bpy.types.Operator):
    bl_idname="jc_agent.restore";bl_label="回到最近一次修改前"
    def invoke(self,context,event):return context.window_manager.invoke_confirm(self,event)
    def execute(self,context):
        if runtime().job_state in ("running","cancelling"):
            self.report({"ERROR"},"请先停止 Agent，并等待当前 Blender 操作结束");return {"CANCELLED"}
        if not _last_edit_checkpoint:self.report({"ERROR"},"当前会话尚无修改前快照");return {"CANCELLED"}
        before=_last_edit_checkpoint
        directory=state_root()/"artifacts"/_instance/"manual-restore"
        directory.mkdir(parents=True,exist_ok=True)
        execute_command({"name":"blender_restore","arguments":{"checkpoint":before},"artifact_dir":str(directory)})
        return {"FINISHED"}


class JCOpenWindow(bpy.types.Operator):
    bl_idname="jc_agent.open_window";bl_label="固定 Agent，与其他工具同时显示"
    bl_description="使用 Blender 原生固定面板；切换到历史记录后 Agent 仍显示，可同时操作"
    def execute(self,context):
        global _task_window_pointer
        if bpy.app.background:return {"CANCELLED"}
        window=context.window
        area=context.area if context.area and context.area.type=="VIEW_3D" else next((a for a in window.screen.areas if a.type=="VIEW_3D"),None)
        if not area:return {"CANCELLED"}
        area.spaces.active.show_region_ui=True
        region=next((r for r in area.regions if r.type=="UI"),None)
        if not region:return {"CANCELLED"}
        old_category=region.active_panel_category
        _task_window_pointer=window.as_pointer()
        _pin_requests.add(area.as_pointer())
        region.active_panel_category="JC Agent"
        area.tag_redraw()
        pointer=area.as_pointer()
        attempts=[0]
        def restore_category():
            live=next((a for a in window.screen.areas if a.as_pointer()==pointer),None)
            if not live:return None
            attempts[0]+=1
            if pointer in _pin_requests and attempts[0]<10:return .1
            ui=next((r for r in live.regions if r.type=="UI"),None)
            if ui and old_category and old_category!="JC Agent":
                try:ui.active_panel_category=old_category
                except (ValueError,TypeError):pass
            live.tag_redraw()
            return None
        bpy.app.timers.register(restore_category,first_interval=.15)
        return {"FINISHED"}


class JCRefreshModels(bpy.types.Operator):
    bl_idname="jc_agent.refresh_models";bl_label="刷新模型列表"
    def execute(self,context):
        global _models_due
        _models_due=time.monotonic()
        runtime().model_status="正在获取模型列表…"
        return {"FINISHED"}


class JCModelList(bpy.types.UIList):
    bl_idname="JC_AGENT_UL_models"
    def draw_item(self,context,layout,data,item,icon,active_data,active_propname,index):
        layout.label(text=item.name,icon="RADIOBUT_ON" if index==data.model_index else "RADIOBUT_OFF")


class JCPanel(bpy.types.Panel):
    bl_label="JC Blender Agent";bl_idname="VIEW3D_PT_jc_agent";bl_space_type="VIEW_3D";bl_region_type="UI";bl_category="JC Agent"
    def draw(self,context):
        if not self.is_popover and context.area.as_pointer() in _pin_requests:
            self.use_pin=True
            _pin_requests.discard(context.area.as_pointer())
        layout=self.layout;rt=runtime()
        row=layout.row(align=True);row.operator("jc_agent.connect",text="连接 / 检查",icon="LINKED")
        if rt.connected:row.operator("jc_agent.disconnect",text="断开",icon="UNLINKED")
        layout.label(text="已连接 Blender" if rt.connected else "未连接",icon="CHECKMARK" if rt.connected else "INFO")
        col=layout.column();col.enabled=rt.job_state not in ("running","cancelling")
        col.prop(rt,"agent")
        col.prop(preferences() or rt,"use_render_knowledge")
        col.label(text="参考内置经验 · 随插件携带" if render_knowledge_enabled() else "自主调试 · 不读取经验库",icon="BOOKMARKS" if render_knowledge_enabled() else "PREFERENCES")
        if rt.agent=="api":
            box=col.box()
            for key in ("base_url","protocol","key_env","api_key"):box.prop(rt,key)
            row=box.row(align=True);row.prop(rt,'remember_api_key');row.operator('jc_agent.clear_api_key',text='',icon='TRASH')
            for line in textwrap.wrap(rt.api_key_status,width=28)[:2]:box.label(text=line)
            for key in ("vision","max_steps"):box.prop(rt,key)
        row=col.row(align=True);row.prop(rt,"auto_models",text="自动获取模型");row.operator("jc_agent.refresh_models",text="",icon="FILE_REFRESH")
        if rt.models:
            col.template_list("JC_AGENT_UL_models","",rt,"models",rt,"model_index",rows=3,maxrows=4)
        for line in textwrap.wrap(rt.model_status,width=28)[:3]:col.label(text=line)
        col.prop(rt,"api_model" if rt.agent=="api" else rt.agent+"_model",text="模型 ID")
        if hasattr(col,"textbox"):
            col.label(text="要求")
            col.textbox(rt,"prompt",initial_visible_lines=3,placeholder="描述需要实现的内容和效果…")
        else:
            col.prop(rt,"prompt",text="要求")
        row=col.row(align=True)
        row.operator("jc_agent.add_attachments",text="添加附件",icon="FILEBROWSER")
        row.operator("jc_agent.paste_attachments",text="粘贴文件",icon="PASTEDOWN")
        if rt.attachments:
            row=col.row()
            row.template_list("JC_AGENT_UL_attachments","",rt,"attachments",rt,"attachment_index",rows=2,maxrows=3,item_dyntip_propname="filepath")
            row.operator("jc_agent.remove_attachment",text="",icon="X")
            current=rt.attachments[min(rt.attachment_index,len(rt.attachments)-1)]
            for line in textwrap.wrap(current.status,width=28)[:2]:col.label(text=line)
        col.operator("jc_agent.send",text="发送描述",icon="PLAY")
        row=col.row(align=True);row.prop(rt,"prompt_text",text="多行");row.operator("jc_agent.new_text",text="",icon="ADD")
        op=col.operator("jc_agent.send",text="从多行文本发送");op.use_text=True
        if rt.job_state in ("running","cancelling"):layout.operator("jc_agent.cancel",icon="CANCEL")
        states={"running":"Agent 执行中","cancelling":"停止中","completed":"Agent 已结束","inspected":"已检查，未修改场景","failed":"任务失败","cancelled":"已停止","interrupted":"执行中断"}
        if rt.job_state:layout.label(text=states.get(rt.job_state,rt.job_state))
        box=layout.box()
        for line in textwrap.wrap(rt.status, width=34)[:5]:box.label(text=line)
        if rt.answer:
            for raw in rt.answer.splitlines()[:12]:
                raw=re.sub(r'[`*#]', '', raw).lstrip('- ')
                for line in textwrap.wrap(raw,width=28)[:3]:box.label(text=line)
        layout.operator("jc_agent.show_log",icon="TEXT")
        row=layout.row(align=True);row.operator("jc_agent.artifacts",text="快照 / 截图",icon="FILE_FOLDER");row.operator("jc_agent.restore",text="回退",icon="LOOP_BACK")
        layout.operator("jc_agent.export_mcp",icon="COPYDOWN")
        if self.is_popover or not self.use_pin:
            layout.operator("jc_agent.open_window",text="与历史等工具同时显示",icon="PINNED")


class JCHeaderPanel(bpy.types.Panel):
    bl_label="JC Blender Agent";bl_idname="VIEW3D_PT_jc_agent_popover"
    bl_space_type="VIEW_3D";bl_region_type="HEADER";bl_ui_units_x=24
    def draw(self,context):
        JCPanel.draw(self,context)


def draw_agent_entry(self,context):
    self.layout.popover(panel="VIEW3D_PT_jc_agent_popover",text="Agent",icon="COMMUNITY")


CLASSES=(JCPreferences,JCModelItem,JCAttachmentItem,JCRuntime,JCConnect,JCDisconnect,JCSend,JCCancel,JCAddAttachments,JCPasteAttachments,JCRemoveAttachment,JCAttachmentList,JCNewText,JCClearAPIKey,JCShowLog,JCOpenArtifacts,JCExportMCP,JCRestore,JCOpenWindow,JCRefreshModels,JCModelList,JCPanel,JCHeaderPanel)


def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.WindowManager.jc_agent=PointerProperty(type=JCRuntime)
    bpy.types.VIEW3D_MT_editor_menus.append(draw_agent_entry)
    restore_api_settings()
    bpy.app.handlers.load_post.append(restore_api_settings)
    bpy.app.timers.register(model_tick,first_interval=.5,persistent=True)


def unregister():
    global _instance,_root,_job,_model_request,_models_due
    if _job:
        try:http("/cancel",{"id":_job})
        except Exception:pass
    if bpy.app.timers.is_registered(tick):bpy.app.timers.unregister(tick)
    if _root:
        atomic_json(_root/"heartbeat.json",{"instance":_instance,"time":0})
    _instance=None;_root=None;_job=""
    _model_request=None;_models_due=0
    _pin_requests.clear()
    if bpy.app.timers.is_registered(model_tick):bpy.app.timers.unregister(model_tick)
    if restore_api_settings in bpy.app.handlers.load_post:bpy.app.handlers.load_post.remove(restore_api_settings)
    bpy.types.VIEW3D_MT_editor_menus.remove(draw_agent_entry)
    if hasattr(bpy.types.WindowManager,"jc_agent"):del bpy.types.WindowManager.jc_agent
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
