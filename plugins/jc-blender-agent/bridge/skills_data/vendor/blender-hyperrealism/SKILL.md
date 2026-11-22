---
name: blender-hyperrealism
description: Use when the user explicitly asks for hyper-realistic or photorealistic results in Blender - renders or animations meant to read as real photos/footage ("hyper realism", "photorealism", "make it look real", "fotorealizm", "hiperrealizm") - or when diagnosing why a Blender render looks fake/CG. Covers lighting, materials, texturing, camera, color management, compositing, animation realism. NOT for stylized/NPR/cartoon looks.
---

# Blender Hyperrealism

Knowledge base distilled from 57 YouTube tutorials/talks by top Blender realism practitioners (Blender Guru, Blender Official/BCON talks, Kaizen, Max Hay, Gleb Alexandrov, Robin Squares, stache, Maarten Nauta, CG Cookie, pwnisher, Rob Tuytel/Poly Haven, Vilem Duha, PixelicaCG, Zircron45, and others). Every technique is consensus-ranked (N independent creators) with exact parameter values.

Applies both when ADVISING a human and when DRIVING Blender programmatically (bpy scripts, blender-mcp).

## Core principle

**You are not simulating reality - you are simulating a PHOTOGRAPH of reality.** Every decision (exposure, DOF, blur, grain, lens artifacts, clipping) must answer: "what would a real camera, with a real lens, held by a real operator, in this real lighting, have captured?" The moment any element could not have come out of a camera, the brain flags the image as CG - even if the viewer can't name why.

Weighting (Blender Guru's four building blocks): **materials + lighting ≈ 90% of realism**; modeling and post split the rest. Spend effort accordingly.

## The 10 Laws

1. **Color management first, before touching anything else.** Never render on Standard/sRGB (clips at ~8 stops). AgX on Blender 4.0+ (highlights roll to white like film), Filmic on older (up to ~25 stops), plus a contrast Look (Punchy / Medium High / High Contrast). 9/57 creators independently name this the single first move. → `references/06-color-management-render.md`
2. **Real-world scale, always metric.** Type in looked-up dimensions; never scale by eye. Scale physically drives DOF blur, light falloff, displacement height and texture density - wrong scale "cannot be fixed later by materials or lighting". → `references/04-geometry-scale.md`
3. **Light with real sources, built from black.** HDRI as the default environment (10 sources - strongest consensus in the corpus). Kelvin/blackbody colors for natural light. Shadows are shaped, never eliminated - gobos/cookies break flat light (6 sources). Add lights one at a time from a pitch-black scene. → `references/01-lighting.md`
4. **No flat values anywhere.** Every material property varies spatially: roughness from maps/noise (never a bare slider), AO/pointiness crevice dirt as "the last node before output", stacked imperfection layers. Specular stays ~0.5; Metallic is binary 0/1; non-color maps set to Non-Color. → `references/02-materials.md`, `references/03-texturing-imperfections.md`
5. **Nothing is perfectly sharp, clean, or aligned.** Bevel every hard edge (0.01 width / 3 segments minimum - "a dead giveaway that's something CG", 6 sources). Wear, dust, fingerprints scaled to what the implied camera distance could resolve. Rotate objects slightly off-axis; sculpt-grab straight lines. → `references/04-geometry-scale.md`, `references/03-texturing-imperfections.md`
6. **The camera is a physical object.** Focal length is a deliberate choice (35mm ≈ human eye; 100mm product; 24mm wide). DOF always on, f-stop by shot type, blur amount MUST match scene scale ("the blur is lying about the scale"). Aperture blades 6-8. Motion blur on everything that moves, shutter tied to implied lighting. → `references/05-camera-optics.md`
7. **Render clean, then rebuild the photograph in post.** Fully denoise (Denoise node + Normal + Albedo passes), then composite REAL grain on top - render noise is never film grain. Grade via Color Balance in Offset/Power/Slope (ASC CDL), never Lift/Gamma/Gain on scene-referred data. EXR output, never PNG, for stills you'll grade. → `references/07-post-compositing.md`
8. **Post artifacts: tiny and physically justified.** Glare only around genuinely bright sources. Chromatic aberration 0.004-0.02 ("0.1 is far too much"). Lens distortion "very very low values or it will look fake as hell". A 2-3px softening pass kills "3D sharpness". → `references/07-post-compositing.md`
9. **Reference discipline + attention budget.** Never work from memory - keep real photos loaded in the viewport (8 sources - top workflow consensus). Backdrop/HDRI light direction MUST match key light. Lock camera before detailing; spend detail only where the eye lands. → `references/08-composition-workflow.md`
10. **Restraint.** "What makes the movie realistic is actually restraint" (BCON). Dial every effect back from where it looks cool to where it stops being noticeable. When two settings both look plausible, choose the subtler one.

## Order of work

1. Gather reference photos of the exact lighting/material/mood (PureRef or viewport Reference images). Write down what to replicate.
2. Set units to metric; block out at real dimensions. Verify with a 1.8m human reference or Ruler tool.
3. Trial 6-7 camera angles; LOCK the camera and focal length before detailing (detail outside frame is wasted).
4. Set View Transform (AgX/Filmic + Look) and verify exposure with False Color while lighting.
5. Light from pitch black, one source at a time. HDRI base → key → practicals → gobos.
6. Materials: correct PBR wiring first, then imperfection stacking. Photo textures for hero surfaces, procedural masks for adaptive wear.
7. Geometry pass: bevels, displacement where silhouette matters, scatter with layered randomization, break perfect alignment.
8. Micro-detail ONLY where the viewer will look (attention budget).
9. Render settings: bounces raised for glass/volumes, denoise data passes on, EXR out.
10. Post: AO multiply ~0.4 → grade (CDL) → glare (justified) → CA/distortion (tiny) → soften → grain. In that order.
11. Animation only: motion blur, physically-grounded camera movement, procedural wind/motion. → `references/09-animation-motion.md`

## Pre-render checklist ("why does it look fake?" scan)

Run through this before any final render; each miss is a documented realism killer:

- [ ] View Transform ≠ Standard? (AgX/Filmic + contrast Look)
- [ ] Scene at real-world metric scale?
- [ ] Every hard edge beveled?
- [ ] Roughness varied spatially on every visible material? (no bare sliders)
- [ ] Metallic strictly 0 or 1? Non-color maps set to Non-Color? Normal map through a Normal Map node?
- [ ] AO/pointiness crevice dirt on hero materials?
- [ ] HDRI (or physically justified rig) lighting the scene? Light direction matches any backdrop?
- [ ] Shadows visible and shaped (gobo/blocker somewhere)?
- [ ] Kelvin-plausible light colors?
- [ ] DOF on, f-stop matched to shot type AND scene scale? Aperture blades set?
- [ ] Motion blur on (if anything moves)?
- [ ] Exposure verified with False Color (some gray on subject; deliberate clipping allowed)?
- [ ] Bounces raised if glass/liquid/volume present? (black patches = ray starvation)
- [ ] Fully denoised + real grain composited on top (not raw render noise)?
- [ ] Every post effect subtle and physically justified? (glare has a source; CA ≤0.02)
- [ ] Something imperfect in frame: dust, wear, clutter, slight misalignment?
- [ ] Nothing 100% black, 100% white, or 100% saturated?

## Routing

| Task | Read |
|---|---|
| Scene lighting, HDRI, gobos, volumetrics, god rays | `references/01-lighting.md` |
| Shaders, PBR wiring, glass, liquids, skin, roughness | `references/02-materials.md` |
| Imperfections, wear, grime, decals, texture sourcing | `references/03-texturing-imperfections.md` |
| Modeling, bevels, scale, displacement, scattering | `references/04-geometry-scale.md` |
| Camera, focal length, DOF, bokeh, lens simulation | `references/05-camera-optics.md` |
| Color management, AgX/Filmic, samples, bounces, EEVEE | `references/06-color-management-render.md` |
| Compositing, glare, grain, grading, film emulation | `references/07-post-compositing.md` |
| Reference workflow, composition, attention budget | `references/08-composition-workflow.md` |
| Animation, motion blur, camera movement, particles | `references/09-animation-motion.md` |
| Full mistake list, tools/addons/asset libraries, quotes | `references/10-mistakes-tools.md` |
| Techniques beyond the research corpus (marked, verify per version) | `references/11-beyond-the-corpus.md` |

Conflicting advice between creators is resolved inline in each chapter under "Judgment calls" - follow the resolution unless the user's context matches the exception.
