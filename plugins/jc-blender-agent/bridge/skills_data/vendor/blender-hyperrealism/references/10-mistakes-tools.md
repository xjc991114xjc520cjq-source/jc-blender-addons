# 10 - The "looks fake" list, tools & quotes

## Ranked realism killers (consolidated mistakes, by corpus frequency)

1. **No/wrong DOF** (6 sources) - zero DOF = physically impossible crispness; excessive DOF = miniature look. Calibrate to lens/scale physics (ch. 05).
2. **Perfectly sharp 90° edges** (5) - "a dead giveaway that's something CG". Bevel everything (ch. 04).
3. **Flat/uniform material values** (4) - reads "distinctly CG/plastic". Vary roughness/color/bump spatially (ch. 02).
4. **Zeroed reflectivity** (4) - everything reflects; raise roughness instead (ch. 02).
5. **Missing motion blur** (4) - the cheapest win skipped (ch. 09).
6. **Backdrop/HDRI light direction mismatch** (4) - "instantly ruins everything" (ch. 01, 08).
7. **Procedural/guessed sky instead of a real HDRI** (4) - "nothing beats an HDRI" (ch. 01).
8. **Cheap/low-quality vegetation, humans, animals** (4) - anything organic below top quality "immediately reads as amateur"; be sparing with them (ch. 08).
9. **Visible texture tiling** (4) - instant tell (ch. 03).
10. **Diffuse-map-only texturing** (4) - "printing the texture on paper and sticking it to a wall" (ch. 03).
11. **Unjustified/overdone post effects** (4) - glow without a source, CA above ~0.02, distortion above "very low" - "will look fake as hell" (ch. 07).
12. **Guessed IOR values** (3) - look them up; liquid = glass IOR reads as "glass inside a glass" (ch. 02).
13. **Default Standard view transform** (9 - the biggest of all, ranked here by its own chapter) (ch. 06).
14. **100% black / 100% white / 100% saturated anything** - "nothing will ever be 100% black or 100% pure red" (Ducky 3D).
15. **Perfect cleanliness / perfect alignment** - no wear, no dust, no clutter, everything axis-aligned = CG (ch. 03, 04, 08).

## Tools & assets (what the pros actually use)

**HDRI/sky:** Poly Haven (free, 7+ creators cite) · Pro Lighting Skies (Guru's 80+ sky addon) · HDRI Maker (dome projection) · EasyHDRI · custom capture: Insta360 One R (fast) or DSLR bracketed + Photoshop Merge to HDR Pro (32-bit mandatory) (pwnisher).

**PBR/materials:** Poliigon (+ browser addon) · Quixel Megascans (photoscans; "janky" with newest Blender - Max Hay) · ambientCG (CC0) · textures.com · BlenderKit (free water/cloud/dirt).

**Scattering/vegetation:** Geo-Scatter · G-Scatter (free, geo-nodes, Mask/Proximity/Wind) · Botaniq (trees) · SpeedTree · Gaia / World Creator 3 (terrain masks).

**Wear/detail:** Node Wrangler (built-in; auto-wires PBR sets - used in ~12/57 videos; Ctrl+Shift+T) · imperfection overlay packs (Poliigon overlays, Behance 8K grain packs) · Space Opera Textures (scratch scans).

**Camera/lens:** Lens Sim addon (Håvard Dalen - physical lens optics, Helios/Canon/Zeiss presets, Cycles-only, keep ray guiding on) · F-Spy (free photo camera-matching) · lens patents via Google Patents for DIY lens builds.

**Skin/scan:** scanned skin map sets (PixelicaCG's source unnamed in-video, linked in description) · XNormal (free 16K baking) · KeenTools FaceBuilder · Kiri Engine (phone photogrammetry) · CrazyBump (full map stack from one photo).

**Color/grading:** AgX/Filmic native · Render Raw addon (CG Cookie's Raw+AgX workflow packaged) · DaVinci Resolve/Fusion via Blender's own OCIO config · Robin Squares' node pack (Bleach Bypass, Color Density, Sensor Emulation).

**Fluids/VFX:** Embergen (external fog/steam VDBs - preferred over Mantaflow) · Real Water / Bagger Rain Generator · Super Image Denoiser (temporal volumetric denoise) · Dynamic Paint (native, the cheap fluid-motion fake).

**Engines:** Cycles default · LuxCoreRender for true caustics/jewelry · EEVEE Next (4.2+) for speed with real GI.

## The quotes that compress the doctrine

1. "What makes the movie realistic is actually restraint." - BCON, Secrets of Photorealism
2. "Depth of field should always be on... there's no possible way that a completely crisp, perfect, in-focus thing could ever exist." - Blender Guru
3. "The blur is lying about the scale. And people feel that lie even if they can't really name why." - Deayan Studios
4. "Perfect 90 degree edges are extremely rare in real life and they're a dead giveaway that's something CG." - DECODED
5. "Real world materials - nothing is produced to absolute perfection... you have to really focus on getting the imperfections perfect." - JessWiseman
6. "Grain is not the same texture as render noise - render a clean image and then put a grain node over it." - Robin Squares
7. "Roughness of zero is not good... a perfectly smooth mirror literally reflects nothing." - Vilem Duha
8. "sRGB was designed to approximate a CRT monitor... it should never be used for rendering." - Blender Guru
9. "You cannot expose for a bright object and a dark object within the same photograph." - BCON
10. "Simply choose better assets - it's actually the easiest thing you can do as an artist to improve an image." - Blender Guru
11. "Nothing will ever be 100% black or 100% pure red." - Ducky 3D
12. "The initial desaturated look of AgX is actually an important feature and not a bug." - CG Cookie
13. "Focus breathing is often considered a defect. Yet it makes everything look 100% more photorealistic if you ask me." - Gleb Alexandrov
