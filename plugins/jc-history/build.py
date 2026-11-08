"""Reproducible installation archive: only extension source, never test scenes."""
from pathlib import Path
import hashlib
import zipfile

BASE = Path(__file__).resolve().parent
SOURCE = BASE / "src" / "jc_history"
OUTPUT = BASE / "dist" / "JC_History_1.0.1_Blender52.zip"
OUTPUT.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(SOURCE.iterdir()):
        if path.is_file() and path.suffix in {".py", ".toml", ".txt"}:
            info = zipfile.ZipInfo(path.name, date_time=(2026, 11, 8, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
with zipfile.ZipFile(OUTPUT) as archive:
    assert archive.testzip() is None
    assert "blender_manifest.toml" in archive.namelist()
digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
OUTPUT.with_suffix(".zip.sha256").write_text(digest + "  " + OUTPUT.name + "\n", encoding="utf-8")
print(OUTPUT)
print("SHA256", digest)
