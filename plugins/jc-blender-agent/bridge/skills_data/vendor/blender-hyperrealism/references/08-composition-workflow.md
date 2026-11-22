# 08 - Composition, reference & workflow

The meta-layer: HOW top artists work. The single most repeated principle in the entire corpus lives here.

## Rules (do these by default)

1. **Never work from memory - always against real reference photos** (8 sources - #1 workflow consensus). Search out photos/film stills of the EXACT lighting condition before lighting anything (Max Hay). Keep reference loaded in the viewport (Shift+A > Image > Reference) through the whole texturing pass (JessWiseman). Match at every stage; if it doesn't match, go back rather than push forward (Kaizen). Ground moods in established photographic conventions (Rembrandt light, automotive-photo setups) - "the viewer's brain already recognizes these patterns from real life." Practice method: recreate one reference photo end-to-end.
2. **Attention budget - detail only where the eye lands** (7 sources). The viewer's attention, not render completeness, is the real constraint (BCON): a face from one iPhone reference + texture stacking took ~10% of the time of a 4-week ZBrush sculpt and was "good enough" for a 5-second locked shot with focal blur. Corollaries: large negative space/shadow beats fully-lit scenes ("a fully-lit environment invites scrutiny the model can't survive" - Ducky 3D); high-res bakes only for hero elements (Bad Normals); reposition/remove secondary elements that steal the eye - blurred/moving things attract attention (Guru removed a distracting car outright).
3. **Lock camera + composition BEFORE detailing** (5 sources). Detail outside frame or too small/blurred to read is wasted (DECODED's over-detailed salt-shaker lid never appeared in-frame). Lighting is view-dependent - finalize framing before placing lights (Guru, "Lock Camera to View"). Trial 6-7 candidate angles first (Nauta). Blockout → proportions → then refine features (CG Cookie's Loomis method for faces).
4. **License assets instead of hand-modeling generic elements** (4 sources). "There's little value in creating your own trees" (Guru); downloaded props are "100 fold" faster (Blender Breakdown); paying for quality assets is "the easiest thing you can do as an artist to improve an image". Marketplaces: CGTrader, TurboSquid, Sketchfab (check real CC0), Quixel Megascans, Kitbash3D, Botaniq, BlenderKit. CAVEAT (Nauta): hand-build the HERO asset - 100% library reads as "asset flipping".
5. **Dress with lived-in clutter as storytelling** (2 sources). Decide the narrative explicitly ("a forgotten life"), then add supporting details from reference: trash, breakage, wealth-signifiers (straightened books, ceramic bowls), clutter off the walking paths, objects off-frame casting shadows (signals the world extends beyond frame). "Somebody lives here" is a feeling built from imperfect tidiness - "usually takes the longest but makes a big difference" (Scenefiller).
6. **Isolate one variable, A/B against render slots** (2 sources). Tune one light with all others hidden; render to slots and flip; occasionally try a wildly different setup to escape local optima; borrow fresh eyes against tunnel vision (Guru). Start each lighting experiment from a fully black scene (Max Hay).
7. **Pre-production before opening Blender** (2 sources): define scope/mood/season/colors, collect the full reference set (PureRef), explore the real location via Google Street View; skipping this cost Nauta three full scene redos. Write down the specific characteristics to replicate before texturing (Covingsworth).

## Composition specifics

- Rule of thirds via camera composition guide overlays; subject off-center (aumission).
- Deliberate color scheme per shot (Kaizen): monochromatic = harmony, complementary = tension (most used), analogous = "realistic feelings" (nature-frequent), triadic = vibrant but cartoonish-risk.
- Background plates extend past frame edges in every direction - a visible cutoff/reflection edge reads as a flat card (Max Hay).
- Start reference-matching with SINGLE-light-direction photos; ambiguous multi-source shadows are near-impossible to replicate credibly (stache: "I fell a bunch of times because I picked the wrong kind of photograph").
- Mine community feedback for authenticity details (aumission's medicine box: Braille from a Reddit comment, barcode from Google Images, cardboard slits from reference).

## Compositing CG into a real photo/video plate (stache - "A New way to Approach Photorealism")

Often the fastest route to a photoreal result: real environment does 90% of the realism work.

1. **Camera match**: still photo → F-Spy (align vanishing-point guides, import via add-on; validate by snapping a test plane flush to the photo's floor with zero manual adjustment). Footage → Motion Tracking (full recipe + QA targets in ch. 05).
2. **Light match**: use a plain SPHERE + Shadow Catcher first, not the final model - a sphere reads highlight/shadow direction far more easily; rotate/scale the HDRI until the sphere's highlights and shadow direction match the plate. Best HDRI: shot on location (pwnisher's capture pipeline - details in ch. 01 Advanced) or extracted at a matched angle from Poly Haven's 3D viewer.
3. **Shadow catcher**: ground plane flagged Shadow Catcher; tint or texture-project it to the real floor color; model simple proxy geometry for anything the CG shadow falls across so it bends over real surfaces.
4. **Integrate**: match the plate's black/white points with B&W Levels → Hue/Saturation color match → one unifying grade over both layers + dust particles + blur. CG must never exceed the plate's sharpness or dynamic range.

## Judgment calls

- **Photos sufficient vs physical reference:** photos are the practical default (whole scenes from 1-2 photos - Bugarija). The ideal standard when photos can't cover every angle: source the physical object or location (Pixar's Paris/Australia trips; Guru's jerry-can handle). Escalate only when the asset is hero-grade and photos genuinely fail.
- **Shoot your own HDRI vs extract from a library:** pwnisher shoots on location (best match possible); stache pans Poly Haven's 3D viewer to extract a matched angle → F-Spy (no shoot needed, works when a suitable stock HDRI exists). Try the library path first.
- **Library vs hand-built line:** bulk/background = library; hero = hand-built or heavily customized. The line moves with how close the camera gets.
