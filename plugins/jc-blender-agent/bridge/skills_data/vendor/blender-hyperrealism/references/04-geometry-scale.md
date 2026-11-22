# 04 - Geometry, scale & scattering

## Rules (do these by default)

1. **Bevel every hard edge** (6 sources - "a dead giveaway that's something CG"). No real 90° corner exists - "even a razor blade has microscopic curvature". Default recipe: Bevel modifier **width 0.01, 3 segments** + Shade Smooth + Auto Smooth (fakes high-poly cheaply - Covingsworth). If bevels render unevenly: apply Scale (Ctrl+A) first. Glass rims: bevel with exactly 1 added segment so Subsurf holds the shape (Kriegel).
2. **Real-world metric scale, typed in, never eyeballed** (5 sources). Wrong scale "can't be fixed later by materials or lighting" (Guru). Verify with the Ruler tool against reference (DECODED), keep a 6ft/1.8m human reference figure in scene (Covingsworth), remember default cube ≈ 2m (IanHubert). Scale drives: DOF blur amount, light falloff, displacement height, texture density, AO distance (default 10m → 0.2m for product scale).
3. **True mesh displacement where silhouette/parallax matters** (4 sources). Height map → Displacement node → Material Output Displacement (Cycles, Displacement enabled). Strength: default 1.0 unanimously "too intense" → **0.02-0.05** (Guru); Poliigon standard 0.2 = 20cm range. Mesh must be pre-subdivided: Subdivide ~30 cuts (override UI cap) + Subsurf 2-3; brick wall Subdiv level 6-8 set to **Simple** (not Catmull-Clark). Terrain: Displace modifier Mid Level 0, Strength ~250-260 (undoes 0-1 height-map normalization); subdiv budget: 5 levels ≈ 500k verts, 6 ≈ 1.8M, 7 ≈ 7M max - work at 3, render at 5-6 (Nauta). Never stack a normal map on top of the same height data (Brecht: "it's just going to wreck it").
4. **Scatter with layered, independent randomization** (4 sources). Single-species uniform scattering = "a rookie mistake" (Kaizen). Layer multiple species; cluster placement with a mask (plants grow in patches); drive scale variation from a DIFFERENT noise than distribution; Proximity effect against clipping. CG Geek's forest numbers: instance scale ~0.01 particle + ~0.2 object, random rotation ~0.1 + Random Phase, random scale ~0.4, dead-tree ratio ~10x rarer than live. Uneven density: check reference - evenly-spaced trees read as "a manicured garden".
5. **Break CG-perfect regularity after blockout** (2 sources + mistake consensus). Subdivide → Sculpt Grab brush at low strength on straight edges (Scenefiller); edge loops + Proportional Editing to warp boards before beveling (Covingsworth); rotate objects slightly off-axis - "perfectly axis-aligned, perfectly parallel objects are a subtle but reliable tell of CG".
6. **Glass/liquid vessels modeled like real objects** (3 sources): solid walls (Alt+E extrude along normals), base thicker than walls, explicit rim lip ("every glass has a lip - absolutely unrealistic without one"), proximity edge loops before Subsurf (2 loops below the rim; bare Subsurf OR a single Edge Crease are both wrong - Duha). Liquid = separate mesh that INTERPENETRATES the glass wall (never flush - z-fighting/wrong shading; scale barely under 1 inward, or slightly outward - both work). Meniscus: inset top face, pull down, inset again.

## Recipes

**Fake high-poly hard surface:** Bevel 0.01/3seg + Shade Smooth/Auto Smooth + procedural edge-wear mask (ch. 03). Covers 90% of props.

**Terrain (Nauta/CG Geek):** ANT Landscape (scale X/Y ~20-24, Noise Size ~2-2.5, Max height ~5/Height ~1.5, mesh 240-256 subdivs) or World Creator/Gaia height maps → Displace (Mid 0, Strength 250-260) → triplanar texturing (ch. 03) → pointiness/height masks splitting rock/grass → scatter pass.

**Non-destructive road in terrain (Nauta):** road curve → Skin modifier (Mean Radius X ~0.5) → duplicate bottom faces ("connect" mesh) → weight-paint terrain under road → Shrink Wrap (Above Surface, vertex group). Disable modifier = terrain fully restored. Needs dense base (1km² at 40k-600k verts). Curbs: curve Bevel Object with ~0.1 cross-section.

**Trees/vegetation:** license assets (Botaniq, SpeedTree exports, Megascans) - "there's little value in creating your own trees" (Guru). Billboard-cluster trees at distance (full 3D oak ~584k verts vs bare trunk+branches ~180k tris) with sky influence ~1.0 + orientation randomization ~0.25 against the flat-billboard tell (Nauta).

**Visible light fixtures:** model the actual bulb (frosted glass roughness ~0.02) inside fixtures - "a blank emissive blob reads as fake" (CG Geek).

**Hero prop upgrade (Guru, Fixing Your Renders):** under-detailed hero prop → replace with a more intentional complex assembly (rusty pipe → full HVAC duct). Perfectly round lake → irregular choppy lagoon ("a perfectly round lake reads as a swimming pool").

## Judgment calls

- **Solidify for glass:** OK only for simple straight-profile cylinders (1-3mm walls); fails on stemware (hollow stem gap) and flat panes (missing border loops → black patch). Complex silhouettes: manual Bridge Edge Loops topology (DECODED both ways; Duha on panes).
- **Micro-detail in mesh vs texture:** scanned texture sets (normal+cavity+micro-normal) fully replace sculpted pores (PixelicaCG - "you don't need any detail sculpted on the face"); multi-million-poly hand-stamped pores (CG Cookie) only for extreme-closeup hero faces. Default to texture-based; sculpt only when the camera demands it.
- **Character work prerequisite:** anatomy knowledge beats software skill - Blender Guru calls a facial-anatomy course (Scott Eaton, 4 weeks; ~a year of study) "probably the most valuable thing" for character realism. Photoreal humans are the highest-difficulty target; prefer scan-based pipelines.

## Parameter quick-table

| Parameter | Value | Source |
|---|---|---|
| Bevel default | width 0.01, 3 segments | Covingsworth |
| Human reference | 1.8m / 6ft figure in scene | Covingsworth |
| Default cube | ≈2m tall | IanHubert |
| AO Distance product-scale | 0.2m (not 10m) | Guru |
| Displacement strength | 0.02-0.05; Poliigon std 0.2 | Guru |
| Displacement subdivision | ~30 cuts + Subsurf 2-3; brick Simple 6-8 | Guru |
| Terrain Displace | Mid 0, Strength 250-260 | Nauta |
| Terrain subdiv budget | L5 500k / L6 1.8M / L7 7M max | Nauta |
| Scatter randomization | rot 0.1, scale 0.4, dead ratio 1:10 | CG Geek |
| Glass walls | solid, base thicker, rim lip, 2 loops sub-rim | Kriegel/Duha |
| Liquid mesh | interpenetrates wall (never flush) | Kriegel/DECODED |
| Solidify glass walls | 1-3mm, simple profiles only | DECODED |
| Fixture bulb glass roughness | ~0.02 | CG Geek |
