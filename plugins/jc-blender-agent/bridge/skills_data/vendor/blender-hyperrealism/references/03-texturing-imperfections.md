# 03 - Texturing & imperfections

"The extra 10% that sells realism" (BCON Illusion Engine) - the layer most artists skip.

## Rules (do these by default)

1. **Finish almost every material with crevice dirt: AO or Pointiness → Color Ramp → Mix(Multiply) → Base Color/Roughness/Bump** (8 sources - top texturing consensus). Multiply factor: 1.0 "almost always" (Blender Guru), 0.8 terrain (CG Geek), 0.5 kept subtle. Drive the AO input with Noise first so darkening isn't mechanically uniform; feed the same mask into Bump (~0.25) so grime reads recessed. Inverse use: Pointiness → highlights on raised ridges (JessWiseman: "my absolute favorite node").
2. **Photographed/scanned textures over procedural math for strict photorealism** (6 sources). "If your goal is photorealism, use image textures - they're literally photos of real things" (Ducky 3D). Real satellite imagery for terrain patterns beats "any procedural crazy customizable way" (Maarten Nauta). A photograph "snapshots the chaos of the real world" (Scenefiller). BUT: a bare diffuse photo is "printing the texture on paper and sticking it to a wall" - derive a full map stack (Normal/Displacement/AO/Specular) via CrazyBump-class tooling, or at minimum reuse the photo across color/bump/roughness/alpha channels (Šime Bugarija built whole scenes from 2 photos).
3. **Hand-painted masks where procedural noise fails** (5 sources). Vertex-paint (not UV image paint) on tiling surfaces - a tiled UV mask repeats with the tile; subdivide past the 10-cap (to ~20) for vertex density, blend the painted mask with the surface's own displacement map via **Color Burn** so mold/efflorescence "hugs" the brick detail (Blender Guru). Keep painted masks deliberately loose with overspill blobs - "the least perfect it is, the more realistic" (JessWiseman).
4. **Weathering must obey physical logic** (Covingsworth): write down WHERE and WHY wear occurs from reference before painting - surfaces under a roof overhang weather less than exposed faces; drips run down; wear concentrates where hands/feet touch. Random distribution reads fake.
5. **Imperfection overlays routed by physical cause** (aumission, 5-source consensus with ch. 02): scratches = displaced surface → Normal/Bump/Displacement; fingerprints/oil = reflectivity change → Roughness only. Dust sits on up-facing surfaces (use Geometry normal Z masking).
6. **Match imperfection density to implied camera distance** (DECODED, resolved conflict below): fingerprints and stray fibers belong ONLY in shots where a real camera would resolve them (macro/close product) - "they wouldn't be in a real photograph either" at normal viewing distance.
7. **No visible tiling, ever** (4 sources - instant tell). Fixes: triplanar/box projection (Object coords → Mapping scale ~0.01 → Image Texture Box + Blend) for sloped terrain; a second blended texture breaking the repeat; hand-painted breakup with downloaded brush alphas (Strength ~4, Mask Mapping Random - Nauta); scale UVs to the texture's authored physical size (×1.25 for a 2.5m texture on a 2m grid; terrain UVs ~40x after unwrap - CG Geek).

## Recipes

**Grime/decal layering on architecture (Blender Guru, How to Texture):** base PBR wiring → vertex-paint masks per effect: sun fade, black mold (Color Burn), graffiti decals, efflorescence (Subtract/Screen), spalling damage (mask driving displacement + darker exposed-brick color). Each mask its own paint layer; blend-mode math against the wall's own displacement height.

**Decal mechanics (Blender Guru - the three gotchas):** route the decal image's **Alpha output** (not Color) into the Mix node's Factor so the decal stays recolorable; set the image texture's Extension mode to **Clip** (default Repeat tiles the graffiti across the whole UV space); position/scale via its own **Mapping node** (Texture Coordinate > UV) - no second UV map needed, base tiling untouched.

**Plaster-over-brick blend (Rob Tuytel/Poly Haven):** two full PBR sets (brick + plaster) → Mix Shader driven by vertex paint → custom "blend falloff" node group (Subtract/Divide on the brick's displacement height) so plaster sinks INTO mortar grooves instead of floating on top; second vertex layer for proud-vs-keyed plaster. Matched against reference photos of real weathered walls.

**Edge wear pack (see ch. 02 recipes):** dual-Bevel Difference / Bevel+Dot-Product / Pointiness ramp - pick by geometry type: Bevel = hard-surface, AO = curved, Pointiness = organic (Jamie Dunbar's reusable triad, "build once, reuse forever").

**Photo-bash workflow (BCON Illusion Engine):** bash reference photos in an editor into one 4K texture; reuse the same image desaturated as its own alpha/mask. Hand-drawn crack alphas stamped where the story needs damage.

**Distant-terrain texturing (Maarten Nauta):** triplanar projection, coarse scale (~0.01), exaggerated Bump Distance ~35 (macro readability lie), cavity mask baked from Sculpt-Mode cavity brush (Factor 0.5-1, Blur 1 → Color Attribute → Diffuse-only bake, Margin 0), micro-displacement 1-1.5 raising grass above rock at seams (fakes contact AO between layers).

## Judgment calls

- **Single photo vs derived map stack:** for background/mid-ground, one good photo reused across channels suffices (Bugarija/Scenefiller); for hero surfaces, derive the full stack (Guru). Distance decides.
- **Always-imperfections vs camera-resolvable-imperfections:** dominant position = some imperfection on nearly every surface ("nothing in the real world is ever perfect"); DECODED's correction = only what the implied lens would resolve. RESOLUTION: macro-level flaws (fingerprints, fibers) scale with camera proximity; meso-level (wear, grime, roughness variation) belongs everywhere.
- **Procedural vs hand-painted placement:** procedural = reusable but "mechanical"; hand-painted = art-directed but per-object labor. RESOLUTION: procedural base pass (edge wear, AO dirt) + hand-painted override where the story or reference demands specific placement. Pure-procedural weathering placement was rejected by both Tuytel and Nauta after trying it.

## Parameter quick-table

| Parameter | Value | Source |
|---|---|---|
| AO multiply factor | 1.0 default / 0.8 terrain / 0.5 subtle | Guru / CG Geek |
| AO Samples for rusty edges | 1-2 + "Inside" | Poly Playground |
| Grime bump strength | ~0.25 | Kaizen |
| Dual-Bevel radii / ramp | 0 + 0.002 / pos ~0.01 Constant | Dunbar |
| Map Range wear floor | 0.01 | Fraser |
| Vertex-paint subdivision | ~20 (override 10-cap) | Guru |
| Texture-paint brush strength (masks) | 4 | Nauta |
| Triplanar mapping scale | ~0.01 | Nauta |
| Bump Distance (distant terrain) | ~35 | Nauta |
| Terrain UV scale | ~40x | CG Geek |
| Physical texture scale | ×(authored size / grid size), e.g. 1.25 | Guru |
| Displacement bit depth | 16-bit (8-bit bands) | Guru |
| Noise Detail cost | ~2x per increment; keep ≤5-6 | Guru |
| Sculpt cavity brush | Factor 0.5-1, Blur 1 | Nauta |
| Seam micro-displacement | 1-1.5 (2 = too much) | Nauta |
| Skin bake resolution | up to 16K (XNormal) | PixelicaCG |
