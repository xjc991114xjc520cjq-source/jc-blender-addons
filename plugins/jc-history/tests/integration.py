"""Run with the installed Blender 5.2.1, in a disposable factory scene."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import base64
import importlib

import bpy

BASE = Path(__file__).resolve().parents[1]
module_name = "bl_ext.user_default.jc_history" if "--extension" in sys.argv else "jc_history"
if module_name == "jc_history":
    sys.path.insert(0, str(BASE / "src"))
addon = importlib.import_module(module_name)
storage = importlib.import_module(module_name + ".storage")

TEST = Path(tempfile.mkdtemp(prefix="jc_history_qa_"))
bpy.ops.preferences.addon_enable(module=module_name)
addon.settings().storage_root = str(TEST / "snapshots")

checks = []


def check(name, condition):
    assert condition, name
    checks.append(name)


try:
    source = TEST / "中文项目.blend"
    cube = bpy.data.objects["Cube"]
    cube.name = "历史测试方块"
    texture = TEST / "贴图.png"
    texture.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="))
    image = bpy.data.images.load(str(texture))
    image.name = "快照外部贴图"
    image.use_fake_user = True
    image.filepath = "//贴图.png"
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.ed.undo_push(message="起点")
    cube.location.x = 2
    bpy.ops.ed.undo_push(message="移动两米")
    before_selected = [o.name for o in bpy.context.selected_objects]
    first = addon.capture_snapshot("初版 中文快照")
    check("snapshot_keeps_working_path", bpy.data.filepath == str(source))
    check("snapshot_keeps_selection", before_selected == [o.name for o in bpy.context.selected_objects])
    check("snapshot_does_not_overwrite_source", hashlib.sha256(source.read_bytes()).hexdigest() == original_hash)
    bucket, catalog = addon.get_catalog(force=True)
    check("snapshot_file_exists", storage.entry_path(bucket, first).is_file())
    check("catalog_unicode", catalog["snapshots"][0]["name"] == "初版 中文快照")

    cube.location.x = 5
    bpy.ops.ed.undo_push(message="移动五米")
    # Native jump, including redo, uses actual stack positions, not operator count.
    bpy.ops.ed.undo_history(item=1)
    check("native_history_jumps_back", bpy.data.objects["历史测试方块"].location.x == 2)
    bpy.ops.ed.undo_history(item=2)
    check("native_history_jumps_forward", bpy.data.objects["历史测试方块"].location.x == 5)
    # A new edit must truncate the native redo branch.
    bpy.ops.ed.undo_history(item=1)
    bpy.data.objects["历史测试方块"].location.x = 8
    bpy.ops.ed.undo_push(message="新分支")
    check("native_branch", bpy.data.objects["历史测试方块"].location.x == 8)
    second = addon.capture_snapshot("新分支快照")
    check("snapshots_survive_native_branch", len(addon.get_catalog(force=True)[1]["snapshots"]) == 2)
    bpy.ops.jch.snapshot_rename(snapshot_id=second["id"], name="改名成功")
    check("rename_persists", storage.read_catalog(bucket)["snapshots"][-1]["name"] == "改名成功")

    # Snapshot save is intentionally Object-mode only: no implicit mode changes.
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        addon.capture_snapshot("不应保存")
    except RuntimeError:
        checks.append("edit_mode_rejected_without_switching")
    else:
        raise AssertionError("edit mode should be rejected")
    check("mode_unchanged", bpy.context.mode == 'EDIT_MESH')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.jch.snapshot_restore(snapshot_id=first["id"])
    check("pre_restore_backup_created", len(addon.get_catalog(force=True)[1]["snapshots"]) == 3)
    check("restore_uses_separate_working_copy", Path(addon._pending_path).name.startswith("work_"))
    snapshot_hash = hashlib.sha256(storage.entry_path(bucket, first).read_bytes()).hexdigest()
    bpy.app.timers.unregister(addon.finish_restore)
    addon.finish_restore()
    check("snapshot_reopens_expected_geometry", bpy.data.objects["历史测试方块"].location.x == 2)
    check("relative_external_texture_survives_restore", Path(bpy.path.abspath(bpy.data.images["快照外部贴图"].filepath)).resolve() == texture.resolve())
    reopened_bucket, reopened = addon.get_catalog(force=True)
    check("reopened_snapshot_resolves_original_catalog", reopened_bucket == bucket)
    check("pre_restore_backup_is_persistent", reopened["snapshots"][-1]["name"].startswith("恢复前自动备份"))
    check("original_file_still_unchanged", hashlib.sha256(source.read_bytes()).hexdigest() == original_hash)
    bpy.data.objects["历史测试方块"].location.x = 100
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    check("save_after_restore_does_not_change_named_snapshot", hashlib.sha256(storage.entry_path(bucket, first).read_bytes()).hexdigest() == snapshot_hash)

    # Reject corrupted catalogs/path traversal instead of guessing or overwriting.
    bad = storage.new_entry("test")
    bad["file"] = "../outside.blend"
    try:
        storage.entry_path(bucket, bad)
    except ValueError:
        checks.append("reject_path_traversal")
    else:
        raise AssertionError("path traversal accepted")
    corrupt = TEST / "corrupt"
    corrupt.mkdir()
    (corrupt / "catalog.json").write_text('{bad json', encoding="utf-8")
    try:
        storage.read_catalog(corrupt)
    except ValueError:
        checks.append("corrupt_catalog_not_overwritten")
    else:
        raise AssertionError("corrupted catalog accepted")

    bpy.ops.preferences.addon_disable(module=module_name)
    check("unregister_cleans_timer", not bpy.app.timers.is_registered(addon.tick))
    check("unregister_cleans_handler", addon.on_load not in bpy.app.handlers.load_post)
    bpy.ops.preferences.addon_enable(module=module_name)
    checks.append("register_after_disable")
    result = {"blender": bpy.app.version_string, "module": module_name, "checks": checks,
              "passed": len(checks), "test_directory": str(TEST)}
    result_name = "results_packaged.json" if module_name.startswith("bl_ext.") else "results.json"
    (BASE / "tests" / result_name).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("JC_HISTORY_TESTS_PASS", len(checks), str(TEST))
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
