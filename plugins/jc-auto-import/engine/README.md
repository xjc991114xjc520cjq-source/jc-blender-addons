# Rebuild the independent Windows x64 component

The runtime requires no original application. Rebuilding requires Visual Studio 2022 C++ tools, CMake, Git, and a locally obtained official Cineware S22.008 SDK. Those development dependencies are not required by end users.

1. Clone Assimp v6.0.5 at `392a658f9c271be965271f45e7521a1b80ea4392` into an external build directory.
2. Obtain `Cineware_22_008.zip` from [Maxon's SDK downloads](https://developers.maxon.net/downloads/), read its license, and extract it outside the repository.
3. Run `python engine/rebuild.py --assimp <checkout> --sdk <extracted-sdk> --build <build-directory> --cmake <cmake.exe>`.

The build uses the SDK's `includes` and MSVC 2019 MT release libraries. The patch adapts SDK wrapper casts, cached mesh traversal, inherited editor visibility, layer/polygon hiding, ordinary instance references, consistent handedness/winding, UV metadata, UTF-8 names, and the Windows Unicode command-line entry point. It does not use or modify SDK programming examples. Only the resulting integrated executable is copied to the add-on. The SDK, headers, sample scenes, prebuilt SDK libraries and documentation are excluded from Git and the ZIP.

## Original visibility regression fixture

`tests/fixture.cpp` is original test code that creates a small scene through the public SDK API; it contains no SDK sample scene or code. Build it outside this repository using the same development SDK (not required by end users):

```powershell
cmake -S engine/tests -B <external-fixture-build> -A x64 -DSDK=<sdk-directory>
cmake --build <external-fixture-build> --config Release
<external-fixture-build>/Release/fixture.exe <external-output>/visibility.c4d
python tests/test_c4d_fidelity.py --blender D:/Blender/blender.exe --fixture <external-output>/visibility.c4d
```

The fixture covers hiding, transformed parents, same-name parts, and an instance of a hidden group. The check compares actual output geometry after Blender reimport in all three output formats. It does not establish full Cinema 4D evaluation or all cached-generator semantics.
