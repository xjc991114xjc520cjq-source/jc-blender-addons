# Independent STEP runtime

This separate process is distributed so STEP conversion needs no installed CAD
application, FreeCAD, system Python, pip, or Internet connection. It does not load
native libraries into Blender. Output is tessellated mesh, not editable CAD history.

- CPython 3.13.13, official Windows embeddable distribution. License and bundled
  dependency notices: `LICENSE.txt`. Source: https://www.python.org/downloads/source/
- CadQuery OCP / cadquery-ocp-novtk 7.9.3.1.1 and cadquery-ocp-proxy 7.9.3.1.1,
  Apache-2.0. Source: https://github.com/CadQuery/OCP and
  https://github.com/CadQuery/ocp-build-system (release 7.9.3.1.1).
- Open CASCADE Technology 7.9.3, LGPL-2.1 with OCCT exception. Corresponding
  source: https://github.com/Open-Cascade-SAS/OCCT/tree/V7_9_3 . License and
  exception are included under `licenses/`. These libraries remain dynamically
  linked DLLs; users may replace/relink them under their licenses. Reverse
  engineering for debugging modifications to these LGPL libraries is permitted.

The upstream wheel also includes dynamically linked dependencies. Their included
notices are in `licenses/`: FreeImage (FreeImage Public License), FreeType (FTL),
libdeflate (MIT), OpenEXR and Imath (BSD), libjpeg-turbo (IJG/BSD), Little CMS (MIT),
Lerc (Apache-2.0), XZ/liblzma, libpng, WebP (BSD), OpenJPEG (BSD), OpenJPH (BSD),
LibRaw (LGPL-2.1), libtiff (permissive), zlib, and Zstandard (BSD).
Microsoft runtime DLLs included by the upstream wheel/CPython retain Microsoft's
redistributable runtime terms; https://visualstudio.microsoft.com/license-terms/ .

Sources for dynamically linked dependencies:
https://github.com/WinMerge/freeimage ; https://github.com/freetype/freetype ;
https://github.com/ebiggers/libdeflate ; https://github.com/AcademySoftwareFoundation/openexr ;
https://github.com/AcademySoftwareFoundation/Imath ; https://github.com/libjpeg-turbo/libjpeg-turbo ;
https://github.com/mm2/Little-CMS ; https://github.com/Esri/lerc ;
https://github.com/tukaani-project/xz ; https://github.com/pnggroup/libpng ;
https://github.com/webmproject/libwebp ; https://github.com/uclouvain/openjpeg ;
https://github.com/aous72/OpenJPH ; https://github.com/LibRaw/LibRaw ;
https://gitlab.com/libtiff/libtiff ; https://github.com/madler/zlib ;
https://github.com/facebook/zstd . No ownership or endorsement is implied.

The download provenance and SHA-256 records are in `downloads.json`. The complete
runtime allowlist and per-file SHA-256 are in `runtime-files.json`. Replacements
require regeneration of that manifest before creating a new add-on package.
