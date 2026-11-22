# 02 - Materials & shaders for hyperrealism

## Rules (do these by default)

1. **Texture stacking is THE differentiator** (7 sources - top materials consensus). Photoreal materials = correctly-wired PBR base + many stacked imperfection mask layers (edge wear, AO grime, curvature wear, spatially-varying roughness), each layer adding ONE real-world flaw (discoloration, cracks, overspill, dust). One flat high-quality texture is never enough. See chapter 03 for the mask recipes.
2. **PBR plumbing, non-negotiable**:
   - Every non-albedo map (roughness, metallic, normal, displacement, cavity, specular) → color space **Non-Color** (5 sources). Only base color stays sRGB.
   - Normal maps go through a dedicated **Normal Map node** (never straight into the Normal socket), strength baseline 1.0 (3 sources).
   - **Metallic is binary 0 or 1** (4 sources) - real surfaces are almost never in-between; a metalness map (white=metal, black=dielectric) mixes rust/paint over bare metal within one shader.
   - **Specular stays ~0.5** (= IOR 1.5) for dielectrics, Specular Tint 0 (Guru, BCON). All real objects reflect roughly the same base amount - only roughness differs.
   - Second-layer Principled inputs (Guru, Principled tutorial): **Clearcoat/Coat** = a second, sharper specular layer independent of base roughness (car paint = soft metallic base + crisp lacquer); **Coat Normal** takes its own scratch/bump map (scratches in a floor's lacquer without touching the wood's normal). **Anisotropic** + Tangent input (Radial for pan bottoms, UV Map for brushed sheet metal) = stretched machined-metal highlights. **Sheen/Sheen Tint** = grazing-angle velvet glow for fabric (negligible elsewhere).
3. **Never zero roughness/reflectivity to fake "non-reflective"** (5 sources). Raise roughness instead - "next time you're thinking of eliminating a reflection, think of just increasing the roughness" (Blender Guru). Glass: roughness **0.01, not exactly 0** ("a perfectly smooth mirror literally reflects nothing" - Vilem Duha).
4. **Roughness varies spatially, always** (5 sources). Map or noise, never a bare slider: "a map has all those tiny intricacies built in - way better than a slider." Kaizen's composite: edge-mask Color Ramp + AO-mask Color Ramp mixed so "no part is either completely reflective or completely rough", plus a ~0.25-factor micro-noise pass. JessWiseman: real grunge photo into Roughness, contrast-compressed toward mid-gray (avoid pure black/white).
5. **Crevice dirt via AO node** (5 sources): AO → Color Ramp → Mix(Multiply) → Base Color. Factor 1.0 base recipe (Blender Guru), ~0.5 subtle, ~0.8 terrain. Drive AO Distance with noise for organic spread; AO Samples 1-2 + "Inside" for rusty edges (Poly Playground). Feed the same mask into Bump (~0.25) so grime reads recessed.
6. **Edge wear from geometry, procedurally** (5 sources). Recipes:
   - Dual-Bevel: Bevel(r=0) + Bevel(r≈0.002) → MixRGB Difference (Fac 1) → Constant Color Ramp (~0.01) (Jamie Dunbar; Cycles-only, bake for EEVEE).
   - Bevel + Geometry Normal → Vector Math Dot Product → Map Range (To Min 1/To Max 0) (Kaizen).
   - Map Range minimum **0.01** so no edge is ever 100% clean (Christopher Fraser).
   - Pick by geometry type (Dunbar): Bevel = hard-surface, AO = curved, Pointiness = organic/dense mesh.
7. **Glass/liquid tint comes from Volume Absorption tied to thickness - never Base Color** (4 sources). Real glass's green edge tint appears only over ~1m+ path length; one Volume Absorption material self-tints correctly at every angle. Glass Base Color = pure 1.0 white (not default 0.906). Absorption density: 0.75 subtle bottom-tint → ~100 fully saturated stained glass (Kriegel).
8. **Liquid IOR 1.33, distinct from its glass** (3 sources) - otherwise it "reads as glass inside a glass". Glass roughly 1.1-1.5 by type (Kriegel), diamond ~2.5. Look up real IOR values, never guess.
9. **Dedicated surface-imperfection overlay layer** (5 sources): scan-library maps (Megascans grain/stain/fingerprints - 3-4 unique fingerprint maps suffice) or a photographed grime shot with crushed blacks as alpha (Scenefiller). Route by PHYSICAL CAUSE (aumission): scratches displace → Normal/Bump/Displacement, never Roughness; fingerprints are oily residue → Roughness, never Bump.

## Recipes

**Weathered painted metal (Jamie Dunbar, full stack):** metal base → painted top coat → dual-Bevel edge wear mask into Metallic + Color → Voronoi cracks (shared scale ~10 via Value node) → gradient dirt pass; each layer via its own Mix; bump strength ~2 for damage depth.

**Realistic glass (Kriegel + Duha):** solid-walled mesh (see chapter 04) · roughness 0.01 · IOR per type · Base Color white 1.0 · tint via Volume Absorption · raise Glossy bounces (simple convex 1-3; bumpy needs 20-40+, 30 usually clears it) OR the escape hatch: Light Path ray-depth > ~10 → switch Glass to Transparent (kills black holes cheaply). Stacked window panes: Fresnel × 0.1-0.2 per extra ray-depth level.

**Fake chromatic dispersion (Duha, jewelry):** Separate RGB → three Glass BSDFs summed, IORs offset ±~0.05 around base (diamond ~2.5). To brighten under-lit dispersive glass, "lie": roughness ~0.05, IOR +0.05 - the one sanctioned physics violation.

**Skin (PixelicaCG, scan-based - no sculpted pores needed):** scanned map set (color/spec/glossy/normal/cavity/translucency, bake up to 16K via XNormal) · invert Glossy → Roughness · Cavity → Displacement at tiny scale · SSS built from the Translucency map (base color through Hue/Sat: saturation up, hue toward red → Subsurface Color; raw translucency drives Subsurface amount via Color Ramp) · finish: micro-normal tiled small, Overlay-mixed at Factor 1.0 over the baked normal - "this is what produces really realistic pores". Render skin in Cycles, not EEVEE (SSS quality).

**Water (stache):** barely-matters Base Color (water mostly reflects environment) · murk via Volume Absorption · roughness AND bump masked separately by two Noise/ColorRamp chains (water is never uniformly bumpy or reflective) · foam: two Noise textures (scale ~1000 + ~100-200) combined via Linear Light, placed by AO (contact foam) or Pointiness (crest foam) · caustics: subtracted-Voronoi fake.

**Wetness (DECODED):** hand-paint a grayscale wetness mask → drives Clearcoat + inverted-roughness mix + Overlay toward darker base color (wet = glossier AND darker). Save painted textures explicitly.

**Cloudy/frosted liquid (DECODED)** - for milk/smoothies/frosted cocktails, NOT the clear-tinted-liquid recipe above: Transmission 1 + nonzero **Transmission Roughness**, color via a plain RGB node into the material's Volume input. Tested against a gradient-texture volume setup - just as good, far less effort.

## Judgment calls

- **Photo textures vs procedural:** photos = "free realism" (chaos of the real world, zero authoring); procedural = adaptive, reusable, updates with mesh. RESOLUTION: hybrid - photo/scan sets for hero surface character, procedural geometry-driven masks (AO/Bevel/Pointiness) for wear that must fit the object. For tiling problems, procedural wins; for one-off hero closeups, photos win.
- **Normal + displacement together:** never on the same height data (Brecht via Blender Guru: "it's just going to wreck it") - pick displacement. EXCEPTION: distant terrain deliberately mixes bump + normal with Bump Distance ~35 for at-distance readability (Maarten Nauta) - a knowing physical lie for far-away macro detail.
- **Physical accuracy vs pragmatic lies:** default sacred (Fresnel, Specular 0.5, real IOR). Sanctioned exceptions only where accuracy makes the render unreadable/too dark (Duha's dispersion brightening; Nauta's distance bump).

## Parameter quick-table

| Parameter | Value | Source |
|---|---|---|
| Specular / Specular Tint (dielectric) | 0.5 / 0 | Guru, BCON |
| Glass roughness | 0.01 (never 0) | Kriegel |
| Water IOR / glass IOR / diamond IOR | 1.33 / 1.1-1.5 by type / ~2.5 | multiple |
| Volume Absorption density | 0.75 subtle → 100 stained glass | Kriegel |
| Volume Bounces (colored liquid) | ~12 (default 0 leaves OJ gray) | Kriegel |
| Ray-depth Glass→Transparent switch | > ~10 | Duha |
| Glossy bounces for bumpy glass | 20-40+ (30 typical fix) | Duha |
| AO multiply into Base Color | 1.0 base / 0.5 subtle / 0.8 terrain | Guru, CG Geek |
| Dual-Bevel radii / ramp pos | 0 + 0.002 / ~0.01 | Dunbar |
| Map Range wear floor | 0.01 | Fraser |
| Micro-roughness noise factor | ~0.25 | Kaizen |
| Roughness anchors | mirror ≈0, rubber ≈1.0 | Graffinity3D |
| Displacement strength | 0.02-0.05 (default 1.0 too much); Poliigon standard 0.2 = 20cm | Guru |
| Skin micro-normal overlay | Overlay, Factor 1.0 | PixelicaCG |
| Fingerprint maps needed | 3-4 unique | aumission |
