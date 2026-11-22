# 09 - Animation & motion realism

Motion is a realism multiplier: Kaizen estimates subtle environmental motion adds ~5% perceived realism even to "still" shots - and bad motion destroys realism faster than any material flaw.

## Rules (do these by default)

1. **Motion blur on essentially every animated render** (6 sources - top animation consensus). "The single easiest realism win... one click" (Ducky 3D); "99% of the time" (Max Hay). BASELINE: **Shutter 0.5 = the 180° rule = standard cinematic blur** (see ch. 11 correction); Max Hay's Shutter 7-8 is a stylized long-streak spark look, NOT a default. Shutter follows implied lighting: night = longer shutter = more blur; bright day = less (Guru/BCON). Extreme speeds: subframes (Dune ornithopter 11/frame). Stills too: keyframe two poses + motion blur = implied motion (Bad Normals). Identical in Cycles and EEVEE.
2. **Camera movement derives from an implied physical operator** (2 sources, complementary):
   - Smooth/professional: Polyfjord's mocap method - Walk Navigation + Auto Key, walk the scene at ~170cm eye height with gravity, then Sample Keyframes (fill gaps) + Smooth Keys iterated 30-90x; anchor start/end keys first so smoothing doesn't drift bookends. 20mm lens for first-person feel.
   - Deliberately imperfect: work backward from "who is filming and why" (BCON/Ossian Lut) - dolly on rails = slow/smooth ("near-impossible to make look bad"); gimbal = slight floaty drift; handheld phone/drone = jitter, imprecise framing, wandering attention; parent the camera to a rigged Mixamo character via IK for true human motion.
   - RESOLUTION: pick the implied rig FIRST, then the technique. Too-smooth motion on a scene meant to read as candid is itself a tell.
3. **Particle systems for airborne debris: Gravity OFF** (3 sources - dust, sparks, bubbles all float/rise; falling reads as rain). Emission Source = Volume (not Faces) + Normal velocity 0 so particles start stationary instead of bursting outward (IanHubert).
4. **Turbulence Force Field for natural particle motion** (2 sources): Size = eddy scale (large = "birds in flight" group sweeps), Strength ~2-2.5 (4 = "too much" - Max Hay); subtle "gusts in a room" for dust (IanHubert).
5. **Hide the emitter, bake the sim** (2+2 sources): "Show Emitter" off in Render + Viewport (visible emitter plane "looks terrible"); Bake All Dynamics before rendering - unbaked cache is the #1 cause of particles glitching/vanishing in renders.
6. **Wind on foliage: procedural (geo-nodes/noise), not physics sim** (2 sources): infinitely-looping noise into rotation (no loop seam - Covingsworth); G-Scatter Wind effect (low speed, low strength, HIGH detail so plants move independently - Kaizen). No bake needed.
7. **Fake fluid motion with Dynamic Paint before reaching for Mantaflow** (2 sources): water plane = Canvas (Waves, Speed ~0.15), object = Brush (Waves Factor ~0.5); more subdivisions = more defined waves (stache). BCON: bake ripples from dropped balls, apply as displacement under a static surface - "three steps versus troubleshooting a true fluid sim". stache on Mantaflow after 4 days of testing: "too finicky... buggy and hard to dial in".

## Recipes

**Sunbeam dust (IanHubert):** domain box sized off the ~2m default cube → particles: Lifetime 500, Scale 0.01-0.001, Scale Randomness ~1.0 in shrink-only mode (set the max size, randomness only shrinks - avoids fake oversized flecks) → Gravity off, Turbulence small → duplicate a fleck stretched into a hair shape (~⅓ of instances read as fibers) with rotation randomness + Dynamic rotation → bake. Details: give the domain box a Blend Mode Alpha Blend + Shadow Mode None material so it never renders; particle shading is a 3-tier tradeoff - Principled (solid, cheapest), Emission-mix (glows even outside the beam - fast but physically wrong), Translucent BSDF (only particles actually in the beam light up - correct, needs more samples). Zero-simulation alternative: layered 2D dust/bug footage planes on an Add shader (Transparent + Emission, Shadow None), stacked at different depths/scales.

**Fire sparks (Max Hay):** icosphere emitter, count ~1000, Normal velocity 1-2 m/s, Frame Start **-150 to -200** (pre-roll: fire was burning before the camera rolled), Lifetime ~400, Turbulence 2-2.5, Render As Object, emitter hidden, Shutter 7-8, fps 24 ("more cinematic"). Fire video texture: Frames = timeline length, Cyclic + Auto Refresh on.

**Rising bubbles (DECODED):** icosphere 1-subdiv smooth, count 10-15k, Gravity off, foam mesh = Collision with **Kill Particles** (bubbles die at the foam physically instead of shooting through).

**Condensation droplets (DECODED):** duplicate the glass's side loops into an emitter → Hair system rendering a Collection of 2-3 hand-modeled teardrops → Distribution Random (not Jittered) + optional Clouds texture driving placement.

**Salt rim / granular (DECODED):** rim duplicate → hair particles, icosphere instance → Child Particles Interpolated 40/parent (handful of parents → ~40k grains).

**Water ripple drift (stache):** 4D Musgrave, driver on W: `#frame/5000`; animate Mapping X/Y too (directional drift breaks the "obviously procedural" single-axis wobble).

**Turntable (Guru):** Empty at subject (3D cursor), camera parented Keep Transform, keyframe Empty rotation, **Linear interpolation** (default Bezier ease-in/out reads wrong for a turntable). Note: this is a CAMERA ORBIT (lighting/reflections stay fixed to the world); spinning the object instead animates its reflections - choose deliberately. Seamless loop: keyframe 0°→360° at frame N+1 and render frames 1..N (frame N+1 duplicates frame 1).

**Animated glass/caustic flicker:** glass converges unevenly frame-to-frame → temporal denoise shimmer. Mitigations: more samples on those shots, Super Image Denoiser (stache), and on 4.1+/4.4+ OIDN GPU quality High + blue-noise sampling pattern (ch. 11).

**Static-to-dynamic hero shot (Guru):** parent camera to the moving subject and animate the subject (car photographer's rig-shot trick).

## Judgment calls

- **Always-on blur vs calibrated shutter:** everyone agrees blur exists; sophistication gap is flat-default vs shutter tied to the same exposure logic as lighting. Match blur amount to implied light level and subject speed; escalate to subframes only when blur visibly steps.
- **Smooth vs shaky camera:** neither is "more realistic" in itself - realism = consistency with the implied capture device. A drone shot with Steadicam smoothness and a phone clip with dolly steadiness are both tells.

## Parameter quick-table

| Parameter | Value | Source |
|---|---|---|
| Shutter baseline (180° rule) | 0.5 | ch. 11 correction |
| Shutter stylized spark streaks ONLY | ~7-8 | Max Hay |
| Extreme-motion subframes | 11/frame | BCON/Dune |
| Dust: lifetime/scale/randomness | 500 / 0.01-0.001 / 1.0 shrink-only | IanHubert |
| Sparks: count/velocity/pre-roll/lifetime | 1000 / 1-2 m/s / -150..-200 / 400 | Max Hay |
| Turbulence strength | 2-2.5 (4 too much) | Max Hay |
| Bubbles count | 10-15k + Kill Particles collision | DECODED |
| Salt children | 40/parent → ~40k | DECODED |
| Dynamic Paint speed / waves factor | ~0.15 / ~0.5 | stache |
| Ripple driver | #frame/5000 | stache |
| Operator eye height | ~170cm | Polyfjord |
| Smooth Keys iterations | 30-90 | Polyfjord |
| Walkthrough focal | 20mm | Polyfjord |
