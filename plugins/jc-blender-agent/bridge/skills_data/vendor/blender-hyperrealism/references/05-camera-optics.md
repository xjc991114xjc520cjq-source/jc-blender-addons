# 05 - Camera & optics

The camera is where "simulating a photograph" becomes literal. DOF was the single most cross-validated realism lever in the whole corpus.

## Rules (do these by default)

1. **DOF always on, aimed with an Empty, f-stop by shot intent** (5 sources). "There's no possible way that a completely crisp, perfect, in-focus thing could ever exist" (Blender Guru). Focus target = Empty at the subject, never a raw distance number. F-stop guide (Guru): **f/5.6** general default, **f/3-5.6** portraits, **f/11** city/street, **f/22-24+** landscapes. Calibrate blur against real photo reference - over-applied DOF reads as "microscopic"/macro (Ducky 3D).
2. **DOF amount is a SCALE cue, not a style dial** (2 sources, hard rule). Close subject = shallow; distant/huge subject = deep. Heavy background blur on a building/spaceship = miniature effect - "the blur is lying about the scale, and people feel that lie even if they can't name why" (Deayan). If the scene is modeled at real-world scale, the same f-stop physics renders correctly without hand-tuning (BCON).
3. **Aperture blades 6-8** (2 sources) - real iris blades shape bokeh polygons (5=pentagon, 6=hex, more=circular); "a tiny change that transforms the quality" (Deayan). Anamorphic look: camera Bokeh anamorphic ratio = 2 (stretched-oval highlights, no compositing - BCON).
4. **Focal length is a deliberate choice, not the 50mm default** (4 sources). 50mm neutral; **~35mm ≈ human eye**; 80-100mm product/furniture (reduces distortion, pulled back); ~30mm landscape establishing; 20mm first-person walkthrough; 24mm deep-focus wide; 85-135mm compressed shallow-DOF portraits; 200mm "dreamy isolated subject". Longer lens + pull back = flattering compression; wide + close = distortion (only if the implied shot wants it).
5. **Motion blur on every render with movement, shutter tied to implied light** (4 sources). "One click... 99% of the time" (Max Hay, Shutter ~7-8 for fire/sparks). Night/dim = longer implied shutter = MORE blur; bright day = short shutter = less (Guru). Extreme speeds need subframes (Dune ornithopter: 11/frame). Works on stills too: keyframe two poses + motion blur = implied mid-motion (Bad Normals).
6. **Exposure logic: one exposure, one priority.** You cannot hold detail in extreme highlights AND shadows - let one clip deliberately (headlight → full white in Toy Story 4). Verify with False Color (ch. 06).
7. **Lens artifacts belong to the implied lens** (4+ sources, resolved conflict below): barrel distortion + chromatic aberration via compositor Lens Distortion node - Dispersion **0.004-0.02** (0.1 "far too much"), Distortion "very very low values or it will look fake as hell" (Kaizen), stronger only on wide-angle shots; crop the black corners (Fit). Vignette: compositor ellipse mask, blurred, Alpha Over - subtle.

## Recipes

**Standard photoreal camera setup:** metric-scale scene → pick focal length by shot table above → DOF on, Empty focus target, f-stop by shot type → blades 6-8 → (animation) motion blur on, shutter by light level → exposure via False Color.

**Camera matching to a real photo (stache):** F-Spy - align vanishing-point guides, import via add-on (auto camera with matched focal/perspective); validate by snapping a plane to the photo's floor. Video: Blender Motion Tracking - match FPS, Motion Model per movement type, Detect Features (Threshold ~0.001, Distance ~75), ≥8 markers, Normalized on, Refine Focal+Optical Center, Keyframe A/B at max-motion frames. Solve error target <0.5px (1080p) / <1px (4K); Filter Tracks at 15→10→5px if high.

**Physical lens simulation (Zircron45 - the deep end):** native DOF math cannot produce swirly bokeh, spherical aberration, or Petzval field curvature at ANY setting. Full physical build: source a lens patent (fast prime f/1.4-1.5, e.g. Canon Serenar 85/1.5) → trace optical-bench cross-section (248-vert circle) → Screw modifier 256 steps → Refraction BSDF (NOT Glass - fireflies) with per-element real IOR (Nd 1.45-1.9) → physical aperture iris disc (unstopped edge leaks are "the dominant source of artifacts") → orthographic "sensor camera" rotated 180°, focus by sliding the sensor (0.14-0.19 units) → transmission bounces ~208+, ~20k samples (cheap: ray-only), light clamping DISABLED (ruins bokeh). Off-axis sensor rotation = true tilt-shift. Practical alternative: **Lens Sim addon** (Håvard Dalen; Helios/Canon/Zeiss presets; Cycles-only, leave "ray guiding" on - Gleb). Lens Sim extras (Gleb): custom aperture-shape textures (star/heart/onion-ring bokeh - one click, boost DOF after since custom shapes shrink bokeh balls); lens-dirt simulation (Type 1 = real texture with front-of-sensor geometry, contrast/diffusion/mesh-distance controls; Type 2 = cheaper shading-only); split diopter + focal-length/global-scale overrides for stylized dual-focus and tilt-shift-miniature looks.

## Judgment calls

- **Native DOF vs physical lens sim:** native f-stop DOF is sufficient for most photoreal work (majority position). Physical lens sim (patent-traced or Lens Sim addon) when the shot lives on its bokeh character: portraits, product hero shots, vintage/anamorphic looks. Gleb's counterpoint to the minimal-artifacts camp: focus breathing and swirly bokeh, though "defects", make footage "100% more photorealistic".
- **CA/distortion as default vs contextual:** DECODED/Robin Squares/CG Geek apply tiny CA routinely; Blender Guru objects - a professional shot implies a lens corrected for it ("an overused trend"). RESOLUTION: derive from the implied camera - phone/vintage/documentary = subtle artifacts on; pro-photography look = near zero. Never above 0.02 dispersion either way.

## Parameter quick-table

| Parameter | Value | Source |
|---|---|---|
| f-stop: general/portrait/street/landscape | 5.6 / 3-5.6 / 11 / 22-24+ | Guru |
| Aperture blades | 6-8 (5 = visible pentagons) | Deayan, CG Geek |
| Anamorphic bokeh ratio | 2 | BCON |
| Focal: eye/product/landscape/walkthrough | 35 / 80-100 / 30 / 20mm | multiple |
| Focal: compression portrait / isolation | 85-135 / 200mm | Deayan |
| Dispersion (CA) | 0.004-0.02, never 0.1 | CG Geek→DECODED |
| Motion blur shutter (fire/sparks) | ~7-8 | Max Hay |
| Extreme-motion subframes | 11/frame (Dune) | BCON |
| Tracking solve error | <0.5px @1080p, <1px @4K | stache |
| Lens-sim transmission bounces / samples | 208+ / ~20k | Zircron45 |
