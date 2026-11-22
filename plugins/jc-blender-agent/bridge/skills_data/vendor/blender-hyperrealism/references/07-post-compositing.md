# 07 - Post-processing & compositing

Doctrine: **render clean and neutral, then rebuild the photographic look deliberately.** Post is where "simulating a photograph" is finished - and where overdoing anything instantly reads fake.

## The post stack, in order

1. **Denoise** - Denoise node + Normal + Albedo passes (Denoising Data on), placed before the final color-space step. Fully denoise; leftover render noise is never grain.
2. **AO grounding** - AO pass (Distance ~0.2m) Multiply over the pre-denoise beauty at **0.3-0.5**. Never the World AO checkbox (it brightens globally).
3. **Grade** - Color Balance in **Offset/Power/Slope (ASC CDL)**, never Lift/Gamma/Gain ("fundamentally incorrect" for scene-referred data - Guru). Avoid display-referred blend modes on scene-referred pixels: Multiply, Screen, Overlay, Color Dodge/Burn, Soft/Hard Light, Difference, Exclusion. Split-tone (teal shadows / warm highlights, Factor ~0.6) is "very common in Hollywood" and easy to overuse (Robin Squares). Decide low-key (crush shadows) or high-key (blow highlights) - never both.
4. **Glare** - only around genuinely bright in-scene sources ("a sensor's inability to cleanly resolve a bright light" - BCON). Fog Glow: two tiers - tight (threshold ~0.5) + large (Size 8-9), low mix (~-0.7 pattern in CG Geek's setup). Streaks: iterations 5-16, threshold 0.5-2 (or 4-10 to isolate only bulbs), Color Modulation ~0.8 or off (rainbow risk). Ghosting: Mix pulled way down (~-0.96) - "can break your image". Isolate via threshold or Object Index → ID Mask.
5. **Lens artifacts** - Lens Distortion node: Dispersion (CA) **0.004-0.02**; Distortion very low, stronger only on wides; Fit/crop the black corners. Vignette: blurred ellipse mask, Alpha Over, subtle. Halation (film red highlight bleed): bright-isolate via B-Spline Color Ramp → red tint ~0.5 → slight blur → Add back "so subtly it shouldn't even be visible through YouTube" (Robin Squares).
6. **Soften** - a deliberate blur pass specifically to kill "3D sharpness": Gaussian 2-3px (aumission), Soften node 0.05-0.2 (Robin Squares), "some blurs to defeat that 3D sharpness" as the opening move of an external grade (Covingsworth). If sharpening instead: build a high-pass sharpener (Map Range clamp → grayscale → Blur → Divide → Overlay composite; NOT Soft Light - broken in Blender's compositor; Blender's Box/Diamond Sharpen are "pretty terrible" - Robin Squares).
7. **Grain LAST, on top of the denoised image** (7 sources): real 16mm film-grain scan (Non-Color, Overlay, aspect-corrected - Robin Squares), 8K grain overlay packs (aumission), or per-RGB-channel Voronoi displacement concentrated in underexposed regions (paper cited by CG Cookie). Match grain scale to the implied camera; blend Linear Light (shadows-grain) or Overlay (highlights-grain) (Kaizen). Know the three noise types (BCON): digital sensor noise = colored/pixel-sized/uneven; film grain = grayscale/varying-size/uniform; render noise = neither.

## Atmosphere / depth in post

- **Mist pass** for cheap aerial perspective: Start ~5m, Depth ~80m; mix via Color Ramp - "super essential for outdoor environments" (Covingsworth). For complex scenes the native Mist pass may not suffice: custom depth fog = Depth → Map Value (Offset ~-2, Size ~0.02, Max ~0.9) → Despeckle (0.4/0.6) → Fast Gaussian 2px → tint → mix ~0.6 (CG Geek's forest).
- **Faked god rays**: Mist pass → Filter > Sunbeams (Mist Length ~8.3, source at the window) → Color Ramp isolation → warm/cool Color Balance → Add at 0.07-0.08 (CG Geek). Full shaft look, zero volumetric render cost.
- **Boost real volumetrics** without re-render: Volume Direct/Indirect passes, Multiply or Screen over beauty (stache).

## Film emulation (Robin Squares' full chain, for the cinematic ceiling)

Denoise → white balance (divide by HSV-normalized sampled neutral, Value forced to 1) → CDL grade → halation → Glare stack (Streaks 16 / Ghosting Mix -0.96 / Fog Glow 8) → soften/low-pass haze (Mix ~0.1) → high-pass sharpen (Overlay) → film-grain scan overlay → optional OCIO export: replicate Blender's exact pipeline in Resolve/Fusion via Blender's own `config.ocio` (datafiles/color_management), Source = ACEScg, Output = AgX Base sRGB.

## Judgment calls

- **Pass-splitting pipeline vs direct beauty grade:** Robin Squares' full View-Layer/Pass-Mixer system (Diffuse/Glossy/Volume/Emission recombined, Indirect Only + Hold Out tricks) enables surgical edits (re-color only the fog) - but his own caveat rules: "if you don't know why you need this, you don't need it." Ian Hubert grades a single beauty pass with one Denoise node. Default to the simple path; go multi-pass when a specific need appears.
- **Effect strength calibration:** universal method - crank the effect to clearly-visible to place it, then dial back to the point where it stops being consciously noticeable (CG Geek dials AO/mist/sunbeams/glare all back from test values). "What makes the movie realistic is actually restraint."

## Parameter quick-table

| Parameter | Value | Source |
|---|---|---|
| AO pass mix / distance | 0.3-0.5 multiply / 0.2m | Guru, CG Geek |
| Dispersion (CA) | 0.004-0.02 (0.1 far too much) | CG Geek→DECODED |
| Fog Glow size/threshold | 8-9 / 0.5-0.8, two tiers | Robin Squares, CG Geek |
| Streaks iterations/threshold | 5-16 / 0.5-2 (4-10 bulbs-only) | CG Geek, Robin Squares |
| Ghosting mix | ~-0.96 | Robin Squares |
| Halation red factor | ~0.5, other channels 0 | Robin Squares |
| Split-tone factor | ~0.6 | Robin Squares |
| Soften | Gaussian 2-3px / Soften 0.05-0.2 | aumission, Robin Squares |
| Mist start/depth | ~5m / ~80m | CG Geek |
| Sunbeams mist length / mix | ~8.3 / 0.07-0.08 | CG Geek |
| Custom depth-fog mix | ~0.6 | CG Geek |
| Grain overlay | real scan, Overlay, Non-Color | Robin Squares |
| Lightroom clarity (external finish) | ~20 max | CG Geek |
