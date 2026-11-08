"""Bundled product-rendering lessons, shared by every agent and MCP client."""
from pathlib import Path
import base64

KNOWLEDGE = Path(__file__).with_name("knowledge")
RENDER_GUIDE_URI = "jc-render://product-rendering-guide"
CASE_URI = "jc-render://g603-approved-case"
RECIPE_URI = "jc-render://g603-recipe"
RESOURCES = {
    RENDER_GUIDE_URI: ("产品渲染经验与自检流程", "product_rendering_zh.md"),
    CASE_URI: ("已确认的 G603 橙黑爆炸图案例", "g603_approved_case_zh.md"),
    RECIPE_URI: ("G603 案例结构化参数", "g603_recipe.json"),
}


def read_resource(uri):
    if uri not in RESOURCES:
        raise ValueError("Unknown rendering knowledge resource")
    return (KNOWLEDGE / RESOURCES[uri][1]).read_text(encoding="utf-8")


def render_instructions():
    return read_resource(RENDER_GUIDE_URI)


def resource_list():
    return [{"uri": uri, "name": name, "mimeType": "application/json" if uri == RECIPE_URI else "text/markdown"}
            for uri, (name, _) in RESOURCES.items()]


def knowledge_result(topic="workflow"):
    topics = {"workflow": RENDER_GUIDE_URI, "case": CASE_URI, "recipe": RECIPE_URI}
    if topic == "preview":
        return {"topic": topic, "description": "用户已确认的历史案例预览，不是当前任务渲染。",
                "image": base64.b64encode((KNOWLEDGE / "g603_approved_preview.png").read_bytes()).decode("ascii"), "mime_type": "image/png"}
    if topic not in topics:
        raise ValueError("Unknown rendering knowledge topic")
    return {"topic": topic, "text": read_resource(topics[topic])}
