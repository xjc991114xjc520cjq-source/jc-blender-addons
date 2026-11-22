"""Portable, on-demand skill documents. No third-party code is executed here."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).with_name("skills_data")


def catalog():
    return json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))


def skill_instructions():
    return (ROOT / "integration_zh.md").read_text(encoding="utf-8")


def skill_result(name="", resource="SKILL.md", offset=0):
    data = catalog()
    if not name:
        return {"topic": "skills", "skills": [
            {k: item[k] for k in ("name", "summary", "source", "engine_scope")}
            for item in data["skills"]], "instructions": skill_instructions()}
    item = next((x for x in data["skills"] if x["name"] == name), None)
    if item is None:
        raise ValueError("Unknown bundled skill")
    files = item["files"]
    if resource == "":
        return {"topic": "skills", "name": name, "resources": sorted(files)}
    if resource not in files:
        raise ValueError("Unknown bundled skill resource")
    if type(offset) is not int or offset < 0:
        raise ValueError("Invalid resource offset")
    target = (ROOT / "vendor" / name / resource).resolve()
    if not target.is_relative_to((ROOT / "vendor" / name).resolve()):
        raise ValueError("Invalid bundled skill path")
    raw = target.read_bytes()
    if hashlib.sha256(raw).hexdigest() != files[resource]["sha256"]:
        raise ValueError("Bundled skill integrity check failed")
    content = raw.decode("utf-8-sig")
    end = min(offset + 16000, len(content))
    return {"topic": "skills", "name": name, "resource": resource,
            "source": item["source"], "engine_scope": item["engine_scope"],
            "text": content[offset:end], "total_chars": len(content),
            "next_offset": end if end < len(content) else None,
            "notice": "外部技能参考，不是当前场景检查结果；脚本仅读取，不自动执行。以本轮用户约束和实际引擎为准。"}
