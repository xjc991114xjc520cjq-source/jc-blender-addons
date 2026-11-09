# Third-party components

## Autodesk MAX Importer 1.9.2

Source: https://github.com/nrgsille76/io_scene_max

`vendor/import_max.py` is an unmodified snapshot of the upstream reader. Copyright notices are preserved in its header. Authors include Sebastian Schrand / Sebastian Sille, Jens M. Plonka and Philippe Lagadec. Source header: GPL-2.0-or-later; used here under GPL-3.0-or-later. See `vendor/MAX_IMPORTER_LICENSE`.

## Independent conversion component

`bin/jc_converter.exe` is a separate command-line program invoked as a subprocess. It is not linked into Blender or into the GPL Python importer.

- Assimp v6.0.5, commit `392a658f9c271be965271f45e7521a1b80ea4392`; BSD-3-Clause and bundled third-party notices in `bin/ASSIMP-LICENSE.txt`.
- Maxon Cineware SDK S22.008: compiled static library integrated into this conversion component. Maxon retains its rights. See `bin/CINEWARE-LICENSE.txt` and https://developers.maxon.net/downloads/. The SDK source archive, static library files, programming examples and documentation are not distributed in this package.

The Python add-on license does not relicense Maxon Cineware. Source and rebuild instructions for the Assimp changes are in the repository's `engine/` folder. No third-party trademarks imply endorsement.
