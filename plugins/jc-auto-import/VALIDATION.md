# Validation report — 2026-11-09

Environment: Windows x64, Blender 5.2.1 LTS, build `9e2066aef7ef`.

## Completed

- Independent conversion followed by actual Blender re-import: 29 checks passed. Samples: MAX `RotatingCube.max`, Cineware SDK `cube.c4d`, 3DS `cube_with_diffuse_texture.3DS` (GLB/FBX/OBJ), Collada animated box, DXF `PinkEggFromLW.dxf`, LWO `boxuv.lwo`, 3MF `box.3mf`, and a generated OFF triangle. The SDK sample and external test models are not included in this repository or the install ZIP.
- Confirmed nonempty mesh objects after import. Checked 3DS UV layers and materials in all three output formats. The animated DAE requires static OBJ fallback; animation and bones are explicitly reported as not retained. The LWO fixture has a missing external texture, correctly reported instead of claiming full material restoration.
- Seven portable automated tests passed: geometry/UV/material parsing, malformed chunks, independent routing and unsupported-format rejection, cache changes after adjacent asset changes, process cancellation, GLB/FBX/OBJ output with reuse and unchanged source, and failure cleanup with no completed/partial cache.
- Actual native Blender window: inspected the Chinese format-selection popup; clicked conversion; observed a real imported MAX mesh and a completion time around 1.4 seconds for that small fixture; used native undo to remove the import. The original scene was not saved or replaced by the plug-in.
- ZIP manifest validated using Blender's extension validator. ZIP installed and enabled through Blender's extension install operator in an isolated user profile; verified the registered panel and the packaged independent engine.

## Boundaries

- Native FileHandler dispatch was verified in the real GUI by invoking Blender's `wm.drop_import_file` with directory/files: it polled the handler in `VIEW_3D` and automatically opened the format popup. See `docs/native-dialog.png`. Automated mouse drags were inconclusive, including a control drag to Blender's built-in OBJ importer; those attempts are **not** counted as proof of real OS mouse drag/drop end-to-end behavior. The file-picker/dialog import path is the verified fallback.
- No original Cinema 4D or 3ds Max executable is invoked. Runtime conversion does not require either application's installation or license.
- The MAX sample does not prove compatibility with all MAX versions, modifiers, compression or third-party materials. The C4D sample does not prove support for all modern C4D files, generator caches or renderers.
- Small-fixture timing is not a benchmark for production scenes. No second-device portability test or macOS/Linux test has been performed.
