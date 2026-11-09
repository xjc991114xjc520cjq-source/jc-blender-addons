# Validation report — 2026-11-09

Environment: Windows x64, Blender 5.2.1 LTS, build `9e2066aef7ef`.

## 1.0.2 fidelity regression

- Reproduced the reported extra wheel with the user's local C4D scene. The source contained hidden alternative meshes; the previous reader ignored editor visibility. Corrected the reader rather than deleting objects by name or shape.
- Audited related paths: inherited visibility, explicit child ON, layer view switches, hidden polygon selections, cache-versus-source traversal, source-reference siblings, and coordinate/normal orientation. Added layer and polygon filtering plus expansion of ordinary uncached instances. A real electronic-component instance in the mouse scene had previously been omitted.
- Converted the same untouched source to GLB and FBX and reimported both. Each has one visible wheel and 60 mesh objects: 59 retained visible source meshes plus one restored instance. All retained meshes match the earlier export's face counts and world bounds within 1e-6 Blender units; 15 hidden meshes are excluded. Upper shell (55,979 triangles), bottom shell (29,465), and side key (6,926) remain at their original positions.
- Inspected actual Blender GUI scenes and workbench renders for both formats: one wheel, visible outer shell. The intermittent shell-disappearance report was not reproduced, so this release does not claim that symptom is conclusively resolved. The reflected-root/face-orientation inconsistency was separately corrected and checked against exported shell normals.
- An original public-SDK regression fixture validates direct and inherited hiding, child ON override, editor-versus-render visibility, layer hiding, partial/all face hiding, two same-name objects at different positions, rotated nonuniform parent scaling, and a visible instance of a hidden source group. GLB, FBX and OBJ round trips each retain 7 expected meshes and 13 faces with checked positions and winding.
- All 10 existing portable conversion tests pass. User source SHA-256 is unchanged. User models, paths, screenshots, converted files and private logs are excluded from the repository and package.
- This is not exhaustive coverage of layer Solo, Takes, multi-instances, generator evaluation, modern C4D versions or third-party renderers. The existing MAX/3DS compatibility boundaries remain in effect; their visibility semantics are not covered by the C4D fixture.

## 1.0.1 regression

- Reproduced a Windows Unicode argument bug: the same valid C4D fixture converted from an ASCII path, but the 1.0.0 engine could not open it when placed under a Chinese directory/name. The CLI accepted narrow ANSI arguments while Assimp file IO expected UTF-8.
- Replaced the Windows entry point with wide Unicode arguments converted to UTF-8. Verified C4D input and GLB output in Chinese directories. The automated engine regression uses Chinese, spaces and a non-BMP emoji in directory and output names.
- Ten automated tests pass, including actual engine error-10 diagnostics and proof that an unreadable source is not retried through another export format.
- Reproduced code 10 with the user's actual local C4D model, then converted and re-imported that same file successfully with 1.0.1, including a test using the installed ZIP in a Unicode installation/cache path. Verified the source SHA-256 was unchanged. The user model, its textures, paths and test logs are not included in this repository or the release. Unsupported/corrupt files can still fail with their actual reader error.

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
