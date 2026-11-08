"""Standard-library-only shared runtime and authenticated local transport."""
import json
import os
import pathlib
import secrets
import tempfile
import time
import urllib.request

VERSION = "0.1.5"


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
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_json(path, default=None):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return default


def get_token(root):
    root = pathlib.Path(root)
    root.mkdir(parents=True, exist_ok=True)
    p = root / "token"
    try:
        with p.open("x", encoding="ascii") as f:
            f.write(secrets.token_urlsafe(32))
        if os.name != "nt":
            p.chmod(0o600)
    except FileExistsError:
        pass
    return p.read_text(encoding="ascii").strip()


def request(url, token, path, payload=None, timeout=10):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url.rstrip("/") + path, data=data, headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json"})
    # Loopback traffic must never enter a user's HTTP proxy.
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))
