# Blender Hyperrealism - a Claude Code skill

A knowledge-base skill for [Claude Code](https://claude.com/claude-code) that teaches Claude how to make Blender renders and animations read as **real photographs** - and how to diagnose why a render looks fake/CG.

Distilled from **57 YouTube tutorials and conference talks** by top Blender realism practitioners (Blender Guru, Blender Official/BCON talks, Kaizen, Max Hay, Gleb Alexandrov, Robin Squares, stache, Maarten Nauta, CG Cookie, pwnisher, Rob Tuytel/Poly Haven, Vilem Duha, PixelicaCG, Zircron45, and others). Every technique is consensus-ranked - the more independent creators teach the same move, the higher it ranks - and comes with exact parameter values, not vague advice.

Works both when Claude is **advising you** (you drive Blender, Claude tells you what to change) and when Claude is **driving Blender programmatically** (bpy scripts, blender-mcp).

## What's inside

- **The 10 Laws** - the non-negotiables of photorealism (color management first, real-world scale, light from black, no flat values, nothing perfectly sharp/clean/aligned, physical camera, rebuild the photograph in post, restraint...)
- **Order of work** - the 11-step workflow from reference gathering to final grain
- **Pre-render checklist** - a "why does it look fake?" scan of documented realism killers
- **11 reference chapters** loaded on demand:

| Chapter | Covers |
|---|---|
| `01-lighting.md` | HDRI, gobos, volumetrics, god rays, building light from black |
| `02-materials.md` | PBR wiring, glass, liquids, skin, roughness strategy |
| `03-texturing-imperfections.md` | wear, grime, decals, imperfection stacking, texture sourcing |
| `04-geometry-scale.md` | bevels, real-world scale, displacement, scattering |
| `05-camera-optics.md` | focal length, DOF, bokeh, lens simulation |
| `06-color-management-render.md` | AgX/Filmic, samples, bounces, EEVEE vs Cycles |
| `07-post-compositing.md` | denoise + real grain, glare, CDL grading, film emulation |
| `08-composition-workflow.md` | reference discipline, composition, attention budget |
| `09-animation-motion.md` | motion blur, camera movement, procedural motion |
| `10-mistakes-tools.md` | full mistake list, tools/addons/asset libraries |
| `11-beyond-the-corpus.md` | techniques beyond the research corpus (marked, verify per version) |

## Installation

One command - clone straight into your Claude Code skills folder:

```bash
# globally (all projects)
git clone https://github.com/Bartindigital/blender-hyperrealism-skill.git ~/.claude/skills/blender-hyperrealism

# or per project
git clone https://github.com/Bartindigital/blender-hyperrealism-skill.git <your-project>/.claude/skills/blender-hyperrealism
```

No dependencies - it's pure Markdown. Restart Claude Code (or start a new session) and the skill is picked up automatically.

## Usage

The skill triggers when you explicitly ask for hyper-realistic / photorealistic results in Blender, or ask why a render looks fake:

```
make this render photorealistic
why does my Blender render look CG?
set up hyperrealistic lighting for this product shot
```

It is deliberately **not** for stylized/NPR/cartoon looks.

## How it was built

Research pipeline: 57 full video transcripts from the leading Blender realism educators, extracted and cross-compared claim by claim, then consolidated into thematic chapters. Where creators disagree, the conflict is resolved inline under "Judgment calls" in each chapter instead of silently picking a side. Techniques that come from outside the corpus live in a separate chapter (`11-beyond-the-corpus.md`) with an explicit provenance warning.

## PL - skrót po polsku

Skill do Claude Code uczący Claude'a fotorealizmu w Blenderze (destylat 57 tutoriali czołowych twórców, techniki rankowane konsensusem). Instalacja jedną komendą:

```bash
git clone https://github.com/Bartindigital/blender-hyperrealism-skill.git ~/.claude/skills/blender-hyperrealism
```

Potem nowa sesja Claude Code i piszesz np. "zrób z tego fotorealizm" albo "czemu ten render wygląda jak CG?". Treść skilla jest po angielsku (Claude czyta ją tak samo dobrze, a społeczność Blendera jest globalna).

## License

MIT - see [LICENSE](LICENSE).
