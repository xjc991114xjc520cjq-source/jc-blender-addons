# 11 - Beyond the corpus

PROVENANCE WARNING: this chapter is NOT distilled from the 57-video research corpus. It contains techniques the corpus missed or under-covered, added from Claude's own knowledge during the final gap-analysis pass. Treat version-specific claims as "verify against the current Blender release" before relying on exact UI paths.

## Engine features the corpus never mentioned

- **Nishita Sky Texture** (Cycles): physically-based sun+atmosphere - sun elevation/rotation gives art-directable golden hour with physically plausible color gradients; Air/Dust/Ozone densities set haze character. Pairs with the corpus HDRI doctrine: Nishita when you need a specific sun angle no stock HDRI has. Keep **Sun angular diameter ~0.526-0.545°** (the real sun) - larger softens shadows unrealistically fast.
- **Light Portals** (Cycles): Area light + "Portal" checkbox fitted into window/door openings massively cleans noise in HDRI-lit interiors - the corpus raised samples instead; portals attack the cause.
- **Shadow Caustics / MNEE** (Cycles, 3.2+): real refractive caustics (glass on a table, water light patterns) via flags on light + caster + receiver - the corpus only had gobo-faked caustics and "use LuxCore". Also **Path Guiding** (CPU, 3.4+) improves caustic-adjacent light transport.
- **Filter Glossy** (Cycles setting, ~0.5-1.0): kills fireflies from sharp glossy highlights at minor accuracy cost - complements the corpus's clamp/bounce advice.
- **Bevel node as render-time bevel**: the corpus used the Bevel shader node only for wear masks - its primary use is normals-only edge rounding (radius 0.005-0.02, samples 4-8) giving real edge highlights on unbeveled geometry. Cheapest possible compliance with Law 5 on dense scenes.
- **White Balance in Color Management** (Blender 4.3+): temperature/tint at the view-transform level - matches the "shot on a camera with a white-balance setting" story without compositor work.
- **Blue-noise sampling pattern** (4.4+) + **OIDN GPU denoising** (4.1+, quality High, prefilter Accurate): visibly steadier animation denoising - the corpus's Super Image Denoiser answer is partly superseded.
- **Cryptomatte**: per-object/material post isolation - the modern replacement for the corpus's Object Index → ID Mask workflow.

## Physical-camera workflow

- **The 180° shutter rule**: Blender's Shutter is in frames - **0.5 = 180° = standard cinematic motion blur at any fps**. CORRECTION TO CORPUS: Max Hay's "Shutter 7-8" is a stylized long-streak spark look, NOT a default; use 0.5 as baseline, deviate only with a story reason (night = toward 1.0+, action-cam crispness = 0.2-0.3).
- **Photographer addon** (Chafouin): true physical camera (ISO/shutter/f-stop exposure, white balance, physical light units in lumen/candela/lux, light mixer, bokeh textures). The cleanest way to make "simulate a photograph" literal - every exposure decision becomes a real camera decision. The corpus reached the same goals with manual exposure + False Color.
- **Physical light sanity values** (with physical units): household bulb ≈ 800 lm, bright interior ≈ 300-500 lux, overcast sky ≈ 1000-2000 W-equivalent HDRI... when a scene's lights are within real ratios, Filmic/AgX renders them believably without cheating - this is the corpus's "push real values" law made concrete.

## Material physics the corpus under-covered

- **Albedo discipline**: real-world albedo lives in ~0.02-0.9 - nothing is 0 or 1. Anchors: coal ~0.04, asphalt ~0.05-0.12, grass ~0.15-0.25, concrete ~0.25-0.4, fresh snow ~0.8. Base colors outside these ranges break GI energy balance and make lighting look wrong no matter the rig (the physical basis behind Ducky 3D's "nothing is 100% black").
- **Skin SSS concrete values** (Principled, Random Walk - use "Random Walk (Skin)" on 4.0+): radius RGB ≈ **1.0 / 0.2 / 0.1** (red penetrates deepest), scale ≈ 0.02-0.05 for a human head at real-world scale. Too-high scale = waxy; too-low = plastic - the two classic CG-skin failure modes.
- **Peach fuzz / vellus hair**: a sparse hair system (~0.3-0.5mm, very fine, slightly transparent) across face/body edges catching rim light is one of the highest-impact close-up skin upgrades - completely absent from the corpus.
- **Sheen** (Principled): velvet/fabric retro-reflection at grazing angles - the physically-correct version of "fabric looks flat" fixes. Sheen weight ~0.1-0.3 on most cloth.
- **Thin Film** (Principled, 4.0+): interference iridescence - soap bubbles, oil slicks, coated optics, beetle shells. Thickness 200-800nm range produces the classic rainbow sweep.
- **Car paint**: base metallic coat + **Coat** layer + noise-driven micro-normal flakes in the coat normal - the three-layer structure real paint has; single-layer metallic always reads as toy.
- **Contact grounding**: objects deform/displace what they rest on (grass bends, cushions dent, dust displaces at feet). A 5-minute proximity-weighted displace or manual sculpt pass at contact points sells weight better than any shadow trick.

## Integration & product visualization

- The full backplate-compositing workflow turned out to BE in the corpus (stache) and now lives in **ch. 08 "Compositing CG into a real photo/video plate"** - use that as the primary reference.
- Additions beyond it: sample the backplate's deepest shadow and brightest highlight as hard limits for the CG layer's levels; for animation, lock white balance and exposure across shots before grading; Cryptomatte (above) replaces manual masks when re-grading the CG element against the plate.

## Modern finishing (use with care)

- **AI detail pass on hero stills** (SUPIR/Magnific-class img2img at low denoise): can add photographic micro-texture the render lacks. Risks: geometry drift, text/logo corruption, inconsistency across animation frames - stills only, low strength, hero-asset masking. This is a taste call, not a default.
- **Perceptual QA tricks** (artist folklore, works): flip the image horizontally to reset your eye's adaptation; squint test (realism survives blur, CG-ness doesn't); walk away for an hour before the final verdict; reverse-image-search your render - if results are photos of the same subject, you're close.

## Priority order for this chapter

If adding only three things from here to a corpus-built scene: (1) 180° shutter correction for animation, (2) albedo discipline + skin SSS values, (3) shadow catcher pipeline for product/integration work. The rest are per-scene escalations.
