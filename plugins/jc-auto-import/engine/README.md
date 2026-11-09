# Rebuild the independent Windows x64 component

The runtime requires no original application. Rebuilding requires Visual Studio 2022 C++ tools, CMake, Git, and a locally obtained official Cineware S22.008 SDK. Those development dependencies are not required by end users.

1. Clone Assimp v6.0.5 at `392a658f9c271be965271f45e7521a1b80ea4392` into an external build directory.
2. Obtain `Cineware_22_008.zip` from [Maxon's SDK downloads](https://developers.maxon.net/downloads/), read its license, and extract it outside the repository.
3. Run `python engine/rebuild.py --assimp <checkout> --sdk <extracted-sdk> --build <build-directory> --cmake <cmake.exe>`.

The build uses the SDK's `includes` and MSVC 2019 MT release libraries. The patch adapts SDK wrapper casts, cached mesh traversal, UV metadata, UTF-8 names, and the Windows Unicode command-line entry point. It does not use or modify SDK programming examples. Only the resulting integrated executable is copied to the add-on. The SDK, headers, sample scenes, prebuilt SDK libraries and documentation are excluded from Git and the ZIP.
