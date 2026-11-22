# 06 - Color management & render settings

The #1 first move in the corpus: 9 independent creators converge on killing the default view transform before anything else.

## Rules (do these by default)

1. **Never render on Standard/sRGB** (9 sources). It clips at ~8 stops and forces fake lighting to compensate (sun capped at ~17-20, cheated fill at 50, hidden bounce lamps). Filmic extends to ~25 stops - the same scene takes sun 100-130+ cleanly. "sRGB was designed to approximate a CRT monitor... it should never be used for rendering" (Guru).
2. **AgX on Blender 4.0+, Filmic on older** (Kaizen's comparison): AgX rolls overexposed highlights to white like a real camera (Filmic skews "neon"), handles saturation better. AgX desaturated first-look "is a feature, not a bug" (CG Cookie). Fire under AgX renders salmon-pink - nudge post gamma toward orange (art direction).
3. **Pick a stronger contrast Look immediately**: Medium High / High Contrast (Very High "a little too extreme" for most), or AgX "Punchy". Default "None" looks washed out.
4. **False Color to verify exposure** (2 sources): gray ≈ 0 EV correct, cyan ≈ 1 under, hot green ≈ 1 over, red/white = clipping. Keep some gray on the subject; deliberately push direct sun into clipping.
5. **Raise Light Path bounces whenever glass/liquid/volumes stack** (7 sources - black patches = ray starvation, not a mystery): Transmission ~208+ for stacked lens elements (Zircron45); Transparent ~128 for overlapping fog cards (CG Geek); Glossy 20-40+ for bumpy glass (30 typical - Duha); Volume ~12 for colored liquid (default 0 leaves OJ gray - Kriegel). Cheaper than bounces: ray-depth escape shader (Light Path depth >10 → Transparent).
6. **Denoise via compositor Denoise node + Normal + Albedo passes** (4 sources) - never the naive built-in alone. Enable Denoising Data pass; place Denoise right before the final color-space conversion (Robin Squares).
7. **EXR out, never PNG, for anything you'll grade** (3 sources): OpenEXR MultiLayer, DWAA codec, Half Float; save into File > Defaults (Robin Squares). Stay linear/ACEScg if finishing externally (Resolve understands ACES). 32-bit EXR + no view transform when compositing in Nuke/Resolve.
8. **Fully denoise, then add real grain on top** (majority, resolved below). Path-tracer noise converges unevenly (small lights, glass, caustics resolve slower) - it never reads as film grain or sensor noise.

## EEVEE realism (when Cycles isn't an option)

- EEVEE Next (Blender 4.2+) has real GI; legacy EEVEE needs: Irradiance Volume bake for bounce light (probe fitted to interior, resolution up against blotchiness; emissive materials dark until baked), Reflection Cubemap probes for SSR blind spots, samples ≥256 with Soft Shadows, AO tuned against a Cycles reference (Bad Normals).
- EEVEE shadow-bleed fixes (Bad Normals): light leaking through thin walls → Solidify modifier OR lower the lamp's Shadow Bias to a very small value; still leaking → enable High Bit Depth on the shadow, Contact Shadows only as last resort (can glitch); Sun lamps → raise Cascade Size. Bake resolution scales to hero-element importance only, never scene-wide.
- HDRI lighting split: Light Path "Is Camera Ray" keeps HDRI visible, hand-matched Sun + Area (~2000) fakes its light (ch. 01).
- Cycles still wins for SSS/skin (PixelicaCG) and anything caustic-adjacent.

## Render performance with zero realism cost

- GPU Compute + OptiX on RTX (CG Geek).
- Adaptive sampling + ~1000 samples covers most stills (DECODED); 64-100 samples viable with strong denoising for animation (Covingsworth, Max Hay).
- Volumes: Step Rate 0.1 for dense hero volumetrics, 1.0 for thin haze; Branched Path Tracing multiplies volume samples (~120 effective - Gleb); Clamp Indirect 0.2 kills bounce fireflies.
- Light Groups (Cycles 3.2+): each light its own pass - re-grade per-light in post without re-rendering (Kaizen).
- Per-light Multiple Importance OFF on fake-bounce lights to remove their sharp reflections/volume glow artifacts (Max Hay, two videos).

## Judgment calls

- **Leave some render noise as "grain"?** NO - Ducky 3D's position loses to the higher-rated majority (BCON, Gleb, Robin Squares, Guru): render clean → denoise fully → composite genuine grain (real 16mm scan / plugin / per-channel Voronoi displacement). See ch. 07.
- **Look presets vs compositor grading:** Looks are display-referred curve presets - fine for speed and most work (Guru himself uses High Contrast "essentially always" in one video); for hero grading, Guru's other video is right: grade in the compositor via Color Balance CDL on scene-referred data and keep the Look moderate. Never Lift/Gamma/Gain, never display-referred blend modes (Multiply/Screen/Overlay/Color Dodge...) on scene-referred pixels.
- **Finish in Blender vs Photoshop/Lightroom:** external tools force a lossy 8/16-bit round-trip; Blender's compositor stays 32-bit throughout (CG Cookie). Stay inside for grading-heavy stills; go external only for workflows that need raster tools (Ducky 3D's Filmic Log 16-bit → Photoshop path is legitimate but caps push-room).
- **Raw + manual AgX (advanced):** View Transform Raw + Convert Color Space node = grading both pre-transform (exposure → gamma → Color Boost, which raises saturation more where a pixel is LESS saturated so nothing clips → White Balance node Temperature/Tint) and post-transform (curves, perceptual OkLab/YUV saturation - HSV silently shifts perceived brightness). Leaving View Transform set directly to AgX locks ALL compositor edits pre-transform and colors can't reach display-white without clipping. The Render Raw addon packages this. Only worth it when the standard AgX+Look ceiling is actually hit.

## Parameter quick-table

| Parameter | Value | Source |
|---|---|---|
| Dynamic range sRGB vs Filmic | ~8 vs ~25 stops | Guru |
| View transform | AgX (4.0+) / Filmic + Look Medium-High/High/Punchy | 9 sources |
| Sun strength Filmic | 100-130+ (sRGB clips 17-20) | Guru |
| Transmission bounces (stacked glass) | 208+ | Zircron45 |
| Transparent bounces (fog cards) | ~128 | CG Geek |
| Glossy bounces (bumpy glass) | 20-40+, 30 typical | Duha |
| Volume bounces (colored liquid) | ~12 | Kriegel |
| Ray-depth escape threshold | >10 → Transparent | Duha |
| World MIS | ~2000 | Guru |
| Clamp Indirect | 0.2 | Gleb |
| Volume Step Rate | 0.1 dense / 1.0 haze | stache |
| Samples | ~1000 stills (adaptive); 64-100 anim + denoise; 20k ray-only lens sim | multiple |
| EEVEE soft-shadow samples | ≥256 | Bad Normals |
| Output | EXR MultiLayer, DWAA, Half Float | Robin Squares |
