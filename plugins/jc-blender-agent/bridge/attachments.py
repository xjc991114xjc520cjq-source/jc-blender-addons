"""Path references, bounded on-demand reads, and isolated media previews.

Original attachments are never copied into the plugin or the state directory.
"""
import base64
import json
import os
import pathlib
import subprocess
import threading
import time
import uuid

from bridge.common import atomic_json, read_json

IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".exr", ".hdr", ".gif"}
VIDEOS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".mpeg", ".mpg"}
TEXT = {".txt", ".md", ".json", ".csv", ".log", ".py", ".xml", ".yaml", ".yml", ".mtl"}


def kind_for(path):
    suffix = pathlib.Path(path).suffix.lower()
    if suffix in IMAGES:return "image"
    if suffix in VIDEOS:return "video"
    if suffix in TEXT:return "text"
    return "file"  # Other formats are valid path references, without a content parser.


class Attachments:
    def __init__(self, root):
        self.root = pathlib.Path(root).resolve()
        self.media_slots = threading.Semaphore(1)

    def manifest(self, instance, identifier):
        if not isinstance(identifier,str) or len(identifier)!=32 or any(c not in "0123456789abcdef" for c in identifier):
            raise ValueError("Invalid attachment ID")
        return self.root / "attachments" / instance / (identifier + ".json")

    def add(self, instance, payload):
        paths = payload.get("paths", [])
        if not isinstance(paths,list) or not 1 <= len(paths) <= 8 or any(not isinstance(p,str) or len(p)>32768 for p in paths):
            raise ValueError("每次可添加 1 至 8 个本地文件路径")
        blender = payload.get("blender_executable", "")
        frames = payload.get("video_frames", 8)
        if type(frames) is not int or not 1 <= frames <= 24:raise ValueError("视频采样数需为 1 至 24")
        result = []
        for name in paths:
            path = pathlib.Path(name).expanduser()
            if not path.is_absolute():raise ValueError("附件必须是本地绝对路径")
            kind = kind_for(path)
            identifier = uuid.uuid4().hex
            record = {"id":identifier,"instance":instance,"name":path.name,"path":str(path),"kind":kind,
                "state":"checking","status":"正在检查路径…","size":0,"video_frames":frames,"blender_executable":blender}
            target = self.manifest(instance, identifier)
            atomic_json(target, record)
            result.append(record.copy())
            def check(value=record, output=target):
                try:
                    original = pathlib.Path(value["path"])
                    if not original.is_file():raise ValueError("文件不存在或无法读取，请重新选择")
                    stat = original.stat()
                    value.update(state="ready",size=stat.st_size,mtime_ns=stat.st_mtime_ns,
                        status="已引用 · 视频按需采样，不含音频" if value["kind"]=="video" else "已引用 · 仅记录本地路径")
                except Exception as error:value.update(state="failed",status=str(error)[:250])
                atomic_json(output,value)
            threading.Thread(target=check,daemon=True).start()
        return {"attachments":result}

    def records(self, instance, identifiers):
        if not isinstance(identifiers,list) or len(identifiers)>8 or len(set(identifiers))!=len(identifiers):
            raise ValueError("最多附加 8 个不重复的文件引用")
        result = []
        for identifier in identifiers:
            record = read_json(self.manifest(instance,identifier),{})
            if record.get("instance")!=instance:raise ValueError("附件不属于当前 Blender 实例")
            if record.get("state")!="ready":raise ValueError(record.get("name","")+"：路径尚未就绪，请等待检查或移除失效附件")
            result.append(record)
        return result

    def public(self, record):
        return {k:record[k] for k in ("id","name","path","kind","size","status","video_frames") if k in record}

    def read(self, instance, identifiers, identifier, index, directory):
        records = self.records(instance,identifiers)
        if not identifier:
            return {"attachments":[self.public(r) for r in records],"notice":"仅引用路径；图片/视频需按 ID 调用此工具读取。视频为有限采样帧，不含音频；PDF/模型只提供路径，未解析内容。"}
        record = next((r for r in records if r["id"]==identifier),None)
        if not record:raise ValueError("此附件未包含在当前任务中")
        original = pathlib.Path(record["path"])
        stat = original.stat()
        if stat.st_size!=record["size"] or stat.st_mtime_ns!=record["mtime_ns"]:
            raise ValueError("附件自添加后发生变化，请移除后重新添加，避免读取错版本")
        result = self.public(record)
        if record["kind"] == "text":
            with original.open("rb") as file:raw = file.read(256*1024+1)
            try:text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:text = raw.decode("gb18030",errors="replace")
            result.update(text=text[:64000],truncated=len(raw)>256*1024 or len(text)>64000)
        elif record["kind"] == "file":
            result["notice"] = "仅提供本地路径，未解析文件内容。模型可通过 Blender Python 按用户要求导入；不要自行执行附件脚本或 .blend 自动脚本。PDF 请使用支持 PDF 的客户端读取，不能声称已读过其正文。"
        else:
            if type(index) is not int or not 0 <= index < (record["video_frames"] if record["kind"]=="video" else 1):raise ValueError("采样帧索引越界")
            # Small supported images can be passed through without a decoder or copy.
            if record["kind"]=="image" and original.suffix.lower() in (".png",".jpg",".jpeg",".webp") and stat.st_size<=4*1024*1024:
                result.update(image=base64.b64encode(original.read_bytes()).decode("ascii"),
                    mime_type="image/jpeg" if original.suffix.lower() in (".jpg",".jpeg") else "image/"+original.suffix[1:].lower())
                return result
            folder = pathlib.Path(directory).resolve() / "references" / identifier
            output = folder / "result.json"
            with self.media_slots:
                data = read_json(output,{})
                if data.get("state")!="ready":
                    folder.mkdir(parents=True,exist_ok=True)
                    config = folder / "request.json"
                    atomic_json(config,{"source":str(original),"output":str(folder),"kind":record["kind"],"frames":record["video_frames"]})
                    exe = pathlib.Path(record.get("blender_executable", ""))
                    if not exe.is_file() or exe.name.lower() not in ("blender.exe","blender"):
                        raise ValueError("需从 Blender 内添加此媒体附件，以便调用其后台解码器")
                    with (folder / "decoder.log").open("wb") as log:
                        subprocess.run([str(exe),"--background","--factory-startup","--disable-autoexec","--threads","2","--python",
                            str(pathlib.Path(__file__).with_name("media_worker.py")),"--",str(config)],stdout=log,stderr=log,
                            timeout=150,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                    data = read_json(output,{})
                    if data.get("state")!="ready":raise RuntimeError(data.get("error","后台媒体解码失败；请检查附件格式与 decoder.log"))
            frames = data["frames"]
            if index>=len(frames):raise ValueError("采样帧索引越界；此附件共有 "+str(len(frames))+" 帧")
            frame = frames[index]
            image = folder / frame["file"]
            if image.stat().st_size>8*1024*1024:raise ValueError("参考帧过大")
            result.update(frame_index=index,frame_count=len(frames),seconds=frame.get("seconds"),duration=data.get("duration"),
                notice="均匀采样画面，不是完整视频分析，不含音频",image=base64.b64encode(image.read_bytes()).decode("ascii"),mime_type="image/png")
        return result
