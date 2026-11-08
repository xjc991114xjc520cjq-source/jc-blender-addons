"""Local snapshot catalog. No Blender dependencies; no background file saves."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid
from datetime import datetime

SCHEMA = 1


def project_key(filepath, unsaved_id):
    if not filepath:
        return "unsaved_" + unsaved_id
    normalized = os.path.normcase(os.path.realpath(filepath))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


def empty_catalog(source=""):
    return {"schema": SCHEMA, "source": source, "snapshots": [], "restores": []}


def read_catalog(bucket):
    path = Path(bucket) / "catalog.json"
    if not path.exists():
        return empty_catalog()
    data = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or data.get("schema") != SCHEMA
            or not isinstance(data.get("snapshots"), list)
            or not isinstance(data.get("source"), str)):
        raise ValueError("快照目录格式无效，请保留文件并检查 catalog.json")
    seen = set()
    for item in data["snapshots"]:
        if not isinstance(item, dict):
            raise ValueError("快照条目无效")
        if not re.fullmatch(r"[0-9a-f]{32}", item.get("id", "")):
            raise ValueError("快照编号无效")
        if item["id"] in seen:
            raise ValueError("快照编号重复")
        seen.add(item["id"])
        if item.get("file") != item["id"] + ".blend":
            raise ValueError("快照文件名无效")
        if not all(isinstance(item.get(k), str) for k in ("name", "time")):
            raise ValueError("快照名称或时间无效")
        if not isinstance(item.get("bytes"), int) or item["bytes"] < 0:
            raise ValueError("快照大小无效")
    restores = data.setdefault("restores", [])
    if (not isinstance(restores, list) or any(not isinstance(name, str)
            or not re.fullmatch(r"work_[0-9a-f]{32}\.blend", name) for name in restores)):
        raise ValueError("恢复副本清单无效")
    return data


def write_catalog(bucket, data):
    bucket = Path(bucket)
    bucket.mkdir(parents=True, exist_ok=True)
    # Replace the catalog only after a complete, flushed write.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=bucket,
                                     prefix="catalog_", suffix=".tmp", delete=False) as f:
        temporary = Path(f.name)
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    try:
        os.replace(temporary, bucket / "catalog.json")
    finally:
        if temporary.exists():
            temporary.unlink()


def new_entry(name):
    identifier = uuid.uuid4().hex
    return {"id": identifier, "file": identifier + ".blend",
            "name": name.strip() or "未命名快照",
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "bytes": 0}


def entry_path(bucket, item):
    identifier = item.get("id", "")
    if not re.fullmatch(r"[0-9a-f]{32}", identifier):
        raise ValueError("快照编号无效")
    if item.get("file") != identifier + ".blend":
        raise ValueError("快照文件名无效")
    bucket = Path(bucket).resolve()
    target = (bucket / item["file"]).resolve()
    if target.parent != bucket:
        raise ValueError("快照路径超出当前项目目录")
    return target


def find_entry(catalog, identifier):
    for item in catalog["snapshots"]:
        if item["id"] == identifier:
            return item
    raise ValueError("快照已不存在，请刷新列表")
