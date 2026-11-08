"""Local API settings and scoped Windows generic credentials; stdlib only.

No credential enumeration, plaintext key files or roaming credentials.
Only the credential for the explicit current API endpoint is read/written.
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.parse

PREFIX = "JCBlenderAgent/API/" + os.environ.get("JC_BLENDER_CREDENTIAL_PROFILE", "default") + "/"
SETTINGS = "api-settings.json"
FIELDS = {"base_url": str, "protocol": str, "api_model": str, "key_env": str,
          "vision": bool, "max_steps": int, "remember_api_key": bool}


def normalize_endpoint(base):
    base = str(base).strip().rstrip("/")
    parts = urllib.parse.urlsplit(base)
    if not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("API 地址必须是无凭据、无 query 的基础地址")
    if parts.scheme != "https" and not (parts.scheme == "http" and parts.hostname in ("localhost", "127.0.0.1", "::1")):
        raise ValueError("远程 API 必须使用 HTTPS；本机模型可用 HTTP")
    host = parts.hostname.lower()
    host = "[" + host + "]" if ":" in host else host
    port = parts.port
    if port and port != (443 if parts.scheme == "https" else 80):
        host += ":" + str(port)
    return urllib.parse.urlunsplit((parts.scheme.lower(), host, parts.path.rstrip("/"), "", ""))


def target_name(base, namespace=PREFIX):
    return namespace + hashlib.sha256(normalize_endpoint(base).encode("utf-8")).hexdigest()


class Credential(ctypes.Structure):
    _fields_ = [("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
                ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
                ("LastWritten", wintypes.FILETIME), ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)), ("Persist", wintypes.DWORD),
                ("AttributeCount", wintypes.DWORD), ("Attributes", ctypes.c_void_p),
                ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR)]


def api():
    if os.name != "nt":
        raise RuntimeError("本机 Key 保存目前支持 Windows；此系统可临时输入或使用环境变量")
    dll = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    ptr = ctypes.POINTER(Credential)
    dll.CredWriteW.argtypes = [ptr, wintypes.DWORD]; dll.CredWriteW.restype = wintypes.BOOL
    dll.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ptr)]; dll.CredReadW.restype = wintypes.BOOL
    dll.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]; dll.CredDeleteW.restype = wintypes.BOOL
    dll.CredFree.argtypes = [ctypes.c_void_p]; dll.CredFree.restype = None
    return dll


def save_key(base, key, namespace=PREFIX):
    target = target_name(base, namespace)
    raw = key.strip().encode("utf-8")
    if not raw or len(raw) > 2560 or b"\r" in raw or b"\n" in raw:
        raise ValueError("API Key 不能为空、包含换行或超过2560字节")
    buffer = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
    c = Credential(); c.Type = 1; c.TargetName = target
    c.Comment = "JC Blender Agent: local API key"; c.UserName = "JCBlenderAgent"
    c.CredentialBlobSize = len(raw); c.CredentialBlob = buffer; c.Persist = 2
    try:
        if not api().CredWriteW(ctypes.byref(c), 0):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        ctypes.memset(buffer, 0, len(raw))


def read_key(base, namespace=PREFIX):
    dll = api(); ptr = ctypes.POINTER(Credential)()
    if not dll.CredReadW(target_name(base, namespace), 1, 0, ctypes.byref(ptr)):
        error = ctypes.get_last_error()
        if error == 1168:return ""
        raise ctypes.WinError(error)
    try:
        return ctypes.string_at(ptr.contents.CredentialBlob, ptr.contents.CredentialBlobSize).decode("utf-8")
    finally:
        dll.CredFree(ptr)


def delete_key(base, namespace=PREFIX):
    dll = api()
    if not dll.CredDeleteW(target_name(base, namespace), 1, 0):
        error = ctypes.get_last_error()
        if error != 1168:raise ctypes.WinError(error)


def clean_settings(values):
    data = {key: value for key, value in values.items() if key in FIELDS and type(value) is FIELDS[key]}
    if "base_url" in data:data["base_url"] = normalize_endpoint(data["base_url"])
    if data.get("protocol") not in (None, "chat", "responses"):data.pop("protocol")
    if "max_steps" in data:data["max_steps"] = min(100, max(1, data["max_steps"]))
    return data


def save_settings(root, values):
    data = clean_settings(values)
    path = Path(root) / SETTINGS;path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".api-settings-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def load_settings(root):
    try:
        data = json.loads((Path(root) / SETTINGS).read_text(encoding="utf-8"))
        return clean_settings(data) if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}
