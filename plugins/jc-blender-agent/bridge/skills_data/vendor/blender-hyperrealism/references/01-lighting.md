# 01 - Lighting for hyperrealism

Consensus base: 23 techniques from 20+ creators. Strongest consensus in the whole corpus lives here.

## Rules (do these by default)

1. **HDRI as the primary environment light** (10 sources - top consensus). A 360° HDR photo delivers light, color AND physically-accurate reflections in one step; no hand-built lamp rig reproduces sky+cloud+bounce complexity. Blender Guru explicitly retired his old sun-lamp + blue-fill rig in favor of one HDRI. Strength is context-dependent: Poly Haven HDRI ~1000 (Blender Breakdown convention) vs product-shot 1.6 (aumission) vs World 3 (Kriegel, glass) - judge with False Color, not by a magic number. Sky Texture instead: strength ~0.15 (default "always too hot" - Blender Guru). Set World **Multiple Importance Sampling ~2000** to kill HDRI hot-spot noise. HDRI reads flat or clips? Split it with two Math nodes after the Environment Texture: **Multiply** isolates/boosts the bright regions into sharp directional light, **Add** reintroduces the soft ambient sky - sharp+soft balance restored without a single flat exposure value (Guru).
2. **Gobos/cookies on the key light** (6 sources). A plane between light and scene with noise or a cutout image driving material Alpha (1=blocks, 0=passes) turns flat light into irregular, patchy, REAL light. Boost noise contrast via Color Ramp; soften edges via light Radius or blocker distance; parent gobo to light (Max Hay). Works for window shafts (Gleb: wood/Transparent Mix Shader through a UV-masked Color Ramp), terrain cloud shadows (Maarten Nauta: "the depth this adds is unreal"), caustic-shaped patches around water (stache).
3. **Shadows are shaped, never eliminated** (4 sources). Piling on fill to kill shadows is the classic beginner tell. Never light from the camera axis (shadows fall out of frame → flat image - Max Hay: "the single biggest cause of a boring/unrealistic image"). No fixed fill-to-key ratio - "the half-the-value rule is bogus", judge by eye (Blender Guru).
4. **Kelvin/blackbody color for every natural source** (4 sources). Blackbody node, not guessed RGB: candle/fire ≈1500K, incandescent 2000-2500K, warm interior ≈4000K, daylight/cool ≥6000K; production example: lantern 1800K + moonlight 4000K locked pre-grade (BCON/Fincher's Bad Traveling). Plain Color only for non-natural sources (neon/sci-fi - blackbody can't make purple).
5. **Build from pitch black, one source at a time** (3 sources). Zero World strength, disable all lamps, add back one at a time; never tune a lamp with others visible ("muddles the eye"). Keep alternative rigs in hidden collections for A/B.
6. **Light size/radius = shadow hardness = detail visibility** (3 sources). Larger radius → softer shadows → suppressed fine detail (pores, scratches); small/hard source reveals it. Faces/characters get large soft sources (soft = flattering); moving a light closer softens like enlarging it. Default Radius 0 gives "tack sharp" CG shadows - raise it.
7. **Respect inverse-square falloff** (2 sources). Intensity = 1/4 per doubled distance (people guess 70-80%). Move a light CLOSER to create local contrast that steers the eye without extra fill. Outdoors use a Sun lamp or HDRI - solar distance makes falloff imperceptible.
8. **Verify exposure with False Color, not by eye** (2 sources). Gray ≈ correct (~0 EV), cyan ≈ 1 stop under, hot green ≈ 1 stop over, red/white = clipping. Keep some gray on the subject; deliberately let direct sun clip - real cameras do.
9. **Push real physical light values on Filmic/AgX** (2 sources). Under sRGB a sun of ~17-20 already clips (that's why people cheat with fill 50 and hidden bounce lamps); under Filmic the same scene takes sun 100-130+ cleanly. CG Geek: Filmic + Exposure ~3.7 to brighten an interior without blowing the exterior.
10. **Ground objects with an AO pass in post, not the World AO checkbox.** AO Distance ~0.2m (default 10m is "insane... city-block scale"), Multiply over the pre-denoise beauty at ~0.3-0.5.
11. **One exposure cannot hold both extremes - let one end clip** (2 sources). "No sensor could see both... and no film could either." Toy Story 4 lets headlights clip to full white; attic sunbeams blow out. Choosing what clips IS the photographic look.

## Volumetrics / god rays

- **Build volumes as a CUBE with a volume material, never in the World tab's Volume socket** (stache - "the default beginner mistake"): a World-tab volume is NOT illuminated by the HDRI or Sun lamp (only mesh/emissive lights), so god rays silently die.
- Default Volume Density is "like a brick" - lower it: **0.2-0.3 for god rays, 0.02 for fire-glow ambience** (Max Hay); first move is always "lower Density substantially" (stache).
- Non-uniform density: disable **"Homogeneous Volume"** on the shader first or a texture in Density does nothing visible (Gleb - easy-to-miss gotcha). For height fog and for blending seams between multiple volume cubes, prefer a **Gradient texture** over Noise/Musgrave - clean exponential falloff instead of a "mechanical and procedural" look (stache).
- **2D fog cards - the most render-efficient localized fog** (2 sources: stache, CG Geek): fog/steam image or footage via Import Images as Planes, always billboarded to camera. CG Geek's node recipe: Emission↔Transparent Mix driven by Noise (Scale ~4, Detail ~5, Distortion ~0.7) → Color Ramp crushed to ~0.18 white point (faint wisps only), × spherical Gradient (Object coords, Multiply, factor 1) fading the card to nothing at its edges (no visible rectangle); scatter many as billboarded hair-particle instances. Cheaper than any real volume; stache calls Mantaflow "too finicky" for fog anyway (Embergen VDBs for hero shots).
- Visible shafts need BOTH a hard-edged shadow caster (gobo/real object) AND a small-but-not-zero light radius. Soft/large lights give no rays.
- Anisotropy = character dial: 0 even scatter, positive toward light (golden hour ↑, fire ~0.7); at 0.95 sharp shafts vanish into soft glow (Gleb).
- Cheap alternative to true volumetrics: Mist pass → Filter > Sunbeams (Mist Length ~8.3), isolated with a Color Ramp, mixed back at only 0.07-0.08 (CG Geek). See 07-post.
- Intensify existing god rays via Volume Direct/Indirect passes multiplied/screened over beauty - no density or exposure change (stache).

## Judgment calls (resolved conflicts)

- **Non-physical helper lights / Light Linking:** Kaizen (pro: "light like a gaffer", reflectors even in daylight) vs aumission (contra: physically impossible ratios "the brain can recognize"). RESOLUTION: default to physically-plausible; a fake bounce/fill is fine ONLY where a real reflector could stand, color-matched and subtle (Max Hay's rule: strength ~100 where 1000 was "too bright", placed only near a plausible bounce source). Light Linking for art direction of emphasis, never to create impossible ratios on one object. Physical alternative for directional control of ambient light: a **"black flag"** - large black-material plane/cube just out of frame absorbing HDRI light from one side (Max Hay via Super 3D) - real-set technique, zero physics violation.
- **Sun lamp outdoors:** Blender Guru ("tends to look flat, use HDRI") vs BCON (physically correct choice). RESOLUTION: HDRI default; Sun+Nishita sky when you need art-directable sun angle; if bare Sun, tune angular size (sharp shadows, strength ~10 with reduced angular diameter) and pair with sky fill.

## Advanced (high-value singles)

- **Custom on-location HDRI** (pwnisher): shoot at the exact CG-object spot. Fast: Insta360-class 360 cam. Proper: DSLR bracketed 3 sweeps (level/+45°/-45°), monopod not tripod, Photomerge → Merge to HDR Pro, "Complete Toning in ACR" checked, **Mode 32-bit mandatory** or it's not an HDR.
- **Real softbox** (Kaizen): enlarging an Area light softens diffuse but NOT reflections; parent a plane below it with a Translucent BSDF - a true diffuser softening both.
- **IES profiles** (Kaizen, Cycles): free .ies files from fixture makers → IES Texture node into Emission Strength - authentic architectural light distribution.
- **CG-look reflections in product shots** (Kaizen): disable the light's Glossy Ray Visibility, or use an emissive plane with a gradient alpha, or a light-shape pack (NIS Light Pack). Camera-invisible emissive planes = studio freedom no photographer has. (A deliberate physicality break - commercial-product convention; apply with Law-10 restraint.)
- **Saturated-light trick** (CG Cookie): a pixel can't be max-bright AND max-saturated; lower the light's strength for camera rays only (Light Path) keeping full indirect - source reads colored, scene stays lit. Red→orange hue skew reads brighter at equal luminance.
- **Two-tone falloff gradient** (Max Hay): Light Falloff (Linear) → Color Ramp → Emission Color = color shifting across distance (client work: blending two brand colors in one glow).
- **Image as the light's own color** (Max Hay): Use Nodes on the light, a photo (e.g. sunlight through a doorway) into Emission Color - projects complex organic light patterns straight from the source; raise light Radius to blur the image past photo-recognition (too high = pattern vanishes); route the image's luminance through a Color Ramp (Ease/B-spline) into Emission Strength so bright parts also emit more. Same mechanism + noise-animated mapping = fake caustics from a water-surface photo.
- **EEVEE (legacy) HDRI fix** (Bad Normals): HDRIs cast no real GI in old EEVEE - Light Path "Is Camera Ray" keeps HDRI visible, hand-matched Sun + Area (strength ~2000) fakes its light, Irradiance Volume bake for bounce, Reflection Cubemap for SSR gaps. (EEVEE Next in 4.2+ has real GI - see chapter 06.)
- **Architecture surgery over interior fill** (CG Geek): rotate a low-sun HDRI (mapping Z until the beam hits the window) and REMOVE off-camera walls blocking light rather than adding fake interior lights.

## Parameter quick-table

| Parameter | Value | Source |
|---|---|---|
| World MIS | ~2000 | Blender Guru |
| Sky Texture strength | ~0.15 | Blender Guru |
| Kelvin: candle / bulb / warm / cool | 1500K / 2000-2500K / 4000K / 6000K+ | multiple |
| Volume density: rays / ambience | 0.2-0.3 / 0.02 | Max Hay |
| Volume anisotropy: fire / too-much | ~0.7 / 0.95 kills shafts | Max Hay / Gleb |
| Fake bounce light strength | ~100 (1000 = too much) | Max Hay |
| AO distance / post mix | 0.2m / 0.3-0.5 multiply | Blender Guru, CG Geek |
| Sun strength under Filmic | 100-130+ (sRGB clipped at 17-20) | Blender Guru |
| Interior exposure push (Filmic) | ~+3.7 EV | CG Geek |
| Falloff | 25% at 2x distance | physics |
