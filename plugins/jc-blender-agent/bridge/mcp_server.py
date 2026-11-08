"""MCP stdio server, also used by the API runner as a real MCP subprocess.

No Blender imports or model credentials. JSON-RPC only on stdout.
"""
import argparse
import base64
import json
import os
import pathlib
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from bridge.common import VERSION, request, state_root, get_token
from bridge.render_guidance import render_instructions, resource_list, read_resource


def tool(name, description, properties=None, required=None, readonly=False):
    return {"name": name, "description": description, "inputSchema": {
        "type": "object", "properties": properties or {}, "required": required or [], "additionalProperties": False},
        "annotations": {"readOnlyHint": readonly, "destructiveHint": not readonly, "idempotentHint": readonly, "openWorldHint": False}}


TOOLS = [
    tool("blender_render_knowledge", "Read bundled product-rendering lessons when the user enables the reference database. topic: workflow, case, recipe or preview (actual approved historical image). Case numbers are scale-specific starting points, not universal settings. Reading this database does not inspect or modify the current Blender scene.", {"topic":{"type":"string","enum":["workflow","case","recipe","preview"]}}, readonly=True),
    tool("blender_attachment", "Read this task's local attachment references. Empty identifier lists IDs/paths. For an ID: text is bounded; images return actual pixels; video returns sampled frame index (0-based). Request multiple indices to inspect motion. Video sampling is not full viewing and has no audio. PDF/models return path only, not parsed contents. Reference reading does not inspect the Blender scene.", {"identifier":{"type":"string"},"index":{"type":"integer","minimum":0,"maximum":23}}, readonly=True),
    tool("blender_scene", "Read active Blender scene, version, objects and selection. Always inspect before editing.", readonly=True),
    tool("blender_object", "Inspect a named object including modifiers, materials, transform and geometry counts.", {"name": {"type": "string"}}, ["name"], True),
    tool("blender_execute", "Execute Python on Blender main thread. bpy, mathutils, math, Vector, Matrix, result are available. Set result to a JSON-safe value. A .blend checkpoint is made before each edit. Do not clear unrelated objects. Code has full local Python privileges, not a sandbox.", {"code": {"type": "string"}, "description": {"type": "string"}}, ["code", "description"]),
    tool("blender_viewport", "Return an actual viewport screenshot as an MCP image for visual inspection. Requires interactive Blender window.", readonly=True),
    tool("blender_preview", "Render a preview from the scene camera and return an MCP image. Long synchronous render blocks Blender until finished. Prefer low resolution/samples.", {"max_size": {"type": "integer", "minimum": 64, "maximum": 1536}}),
    tool("blender_checkpoint", "Save a recoverable .blend copy to the local task artifacts without overwriting the user's file.", {"label": {"type": "string"}}),
    tool("blender_restore", "Restore a checkpoint made by this bridge. Replaces the current scene. Use only when user requests rollback.", {"checkpoint": {"type": "string"}}, ["checkpoint"]),
]


class Server:
    def __init__(self, url, token, instance, job=None):
        self.url, self.token, self.instance, self.job = url, token, instance, job
        self.initialized = False

    def knowledge_enabled(self):
        return request(self.url, self.token, "/knowledge/config", {"instance": self.instance, "job": self.job}, timeout=3)["enabled"]

    def call(self, name, arguments):
        schemas = {t["name"]: t["inputSchema"] for t in TOOLS}
        if name not in schemas:
            raise ValueError("Unknown tool: " + str(name))
        schema = schemas[name]
        if not isinstance(arguments, dict) or set(arguments) - set(schema["properties"]):
            raise ValueError("Invalid tool arguments")
        if any(k not in arguments for k in schema["required"]):
            raise ValueError("Missing required arguments")
        for key, v in arguments.items():
            s = schema["properties"][key]
            if s["type"] == "string" and not isinstance(v, str):
                raise ValueError(key + " must be a string")
            if s["type"] == "integer" and (type(v) is not int or not s["minimum"] <= v <= s["maximum"]):
                raise ValueError(key + " out of range")
        r = request(self.url, self.token, "/tools/call", {"instance": self.instance, "job": self.job, "name": name, "arguments": arguments}, timeout=620)
        content = [{"type": "text", "text": json.dumps({k: v for k, v in r.items() if k != "image"}, ensure_ascii=False)}]
        if r.get("image"):
            content.append({"type": "image", "mimeType": r.get("mime_type","image/png"), "data": r["image"]})
        return {"content": content, "isError": bool(r.get("error"))}

    def dispatch(self, msg):
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
            return {"jsonrpc": "2.0", "id": msg.get("id") if isinstance(msg, dict) else None, "error": {"code": -32600, "message": "Invalid Request"}}
        if "id" not in msg:
            if msg["method"] == "notifications/initialized":
                self.initialized = True
            return None
        rid, method, params = msg["id"], msg["method"], msg.get("params", {})
        try:
            if method == "initialize":
                version = params.get("protocolVersion")
                version = version if version in ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25") else "2025-06-18"
                enabled = self.knowledge_enabled()
                value = {"protocolVersion": version, "capabilities": {"tools": {}, "resources": {}}, "serverInfo": {"name": "jc_blender", "version": VERSION}, "instructions": "Inspect scene, make scoped edits, verify visually. Do not assume stdout means success." + ("\n\n" + render_instructions() if enabled else "\n产品渲染经验库已关闭：本轮自主调试，不注入或读取内置案例。")}
            elif method == "ping":
                value = {}
            elif method == "tools/list":
                enabled = self.knowledge_enabled()
                value = {"tools": [t for t in TOOLS if enabled or t["name"] != "blender_render_knowledge"]}
            elif method == "tools/call":
                try:
                    value = self.call(params.get("name"), params.get("arguments", {}))
                except Exception as e:
                    value = {"content": [{"type": "text", "text": str(e)}], "isError": True}
            elif method == "resources/list":
                value = {"resources": resource_list() if self.knowledge_enabled() else []}
            elif method == "resources/read":
                uri = params.get("uri")
                if not self.knowledge_enabled():
                    raise ValueError("渲染经验库已关闭")
                metadata = next((r for r in resource_list() if r["uri"] == uri), None)
                if metadata is None:raise ValueError("Unknown rendering knowledge resource")
                value = {"contents": [{"uri": uri, "mimeType": metadata["mimeType"], "text": read_resource(uri)}]}
            elif method in ("prompts/list", "resources/templates/list"):
                value = {"prompts/list": {"prompts": []}, "resources/templates/list": {"resourceTemplates": []}}[method]
            else:
                return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "Method not found"}}
            return {"jsonrpc": "2.0", "id": rid, "result": value}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32602, "message": str(e)}}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--state", default=str(state_root()))
    p.add_argument("--url")
    p.add_argument("--instance", default=os.environ.get("JC_BLENDER_INSTANCE"))
    p.add_argument("--job", default=os.environ.get("JC_BLENDER_JOB"))
    args = p.parse_args()
    if not args.instance:
        p.error("--instance or JC_BLENDER_INSTANCE required")
    discovery = pathlib.Path(args.state) / "broker.json"
    url = args.url or json.loads(discovery.read_text(encoding="utf-8"))["url"]
    server = Server(url, get_token(args.state), args.instance, args.job)
    for raw in sys.stdin.buffer:
        try:
            if len(raw) > 4 * 1024 * 1024:
                raise ValueError("Message too large")
            msg = json.loads(raw.decode("utf-8"))
            out = server.dispatch(msg)
        except Exception:
            out = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if out is not None:
            sys.stdout.buffer.write((json.dumps(out, ensure_ascii=False) + "\n").encode("utf-8"))
            sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
