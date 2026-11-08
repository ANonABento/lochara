# Workflow: a character, end to end

**You decide, the agent works.** Each stage ends at a checkpoint where you look and choose; an agent following
lochara's skills never moves past one by itself. Without an agent, the same commands work by hand.

```
 1 concept ─▶ 2 base body ─▶ 3 parts ─▶ 4 build ─▶ 5 check ─▶ 6 export
     ✋             ✋          ✋ each       ✋        (auto)       ✋
```

## How a character is split
| Piece | Comes from | Why |
|---|---|---|
| Body, skin, face, eyes, rig, expressions | A rigged base: VRoid Studio, or any rigged VRM/GLB | Clean topology and real weights. Generated whole bodies fuse hair, clothes and body into one shell, and guessed weights tear. |
| Hair, outfit | The base, recoloured by the style stage | Separate meshes with physics in the source. (Charakuru needs a paid part-split service for this; a VRoid base has it already.) |
| Rigid hardware and props | Generated: FLUX → AssetFurnace, about 3k triangles each | Rigid, so each hangs off one bone with no weights; generation is good at exactly this. |
| Anything articulated (hands, tails, cloth) | The base, or a style script | Needs bones and weights; a generated mesh comes out as one fused piece. |
| Glow | `glow` on a part, or `emissive` material rules | Generated textures paint lights on; glow has to be a real emissive material. |

Charakuru generates the head and body meshes, then copies weights from a bundled base body. lochara starts from
the base body and generates only what doesn't need weights.

## 1. Concept ✋
```
lochara new mychar
lochara concept mychar "<who they are, palette, silhouette, the parts they wear>" -n 6
```
- *Agent:* writes the prompt from your brief, draws candidates, shows `concepts/c-sheet.png`, then proposes a
  parts list: id, what it looks like, the bone it hangs from, its glow.
- *You:* pick a concept (or ask for another round); edit the parts list.

## 2. Base body ✋
- *You:* make the base in VRoid Studio against the concept (face, hair, outfit, proportions) and export a VRM, or
  bring any rigged VRM/GLB. Put it in `assets/` and set `base.file`. This is the hands-on step: it's the art
  direction, and VRoid makes it fast.
- *Agent:* sets `style` (bone names your app expects, morphs, material rules), runs `lochara build`, and shows
  `lochara render`.

## 3. Parts ✋ for each part
```
lochara part draw  mychar <id> "<what it looks like>"     # 4 candidates -> parts/<id>/candidates/sheet.png
lochara part pick  mychar <id> <seed>                     # -> parts/<id>/picture.png
lochara part model mychar <id>                            # ~20 min -> parts/<id>/model.glb, preview.png
```
- *You:* pick a candidate (or ask for a new prompt or seeds); then accept the 3D preview, or ask for a redo (new
  seed, new picture, another engine, more triangles).
- Prompts work best as a product shot: one isolated object, three-quarter view, plain background, no person.
  `part draw` adds that wording unless `--raw`.

## 4. Build ✋
```
lochara build  mychar
lochara render mychar               # front / three-quarter / back
lochara render mychar --focus Head  # close-up on a bone
```
- *Agent:* places each part (`bone`, `offset`, `size`, `rotation`, `mirror`, `glow`), builds and renders,
  adjusting numbers until the part sits right, then shows you.
- *You:* review. Fixes are numbers in `character.json`, not code.

## 5. Check (automatic)
`lochara build` ends with the check, and `lochara check` runs it alone: the bones and morphs in `contract`, and the
size budget in `output.maxBytes`. Expect about 150 KB per part at 3k triangles.

## 6. Export ✋
```
lochara export mychar                       # to the targets in character.json
lochara export mychar --to path/to/app.glb
```
- *You:* check it in your app, then commit the character folder (not `build/` or `assets/`).

## Agent skills
Claude Code picks these up from `.claude/skills/` in this repo; other agents read `AGENTS.md`.

| Skill | Covers |
|---|---|
| `lochara` | The whole workflow: setup, which stage you're at, the checkpoint rules. Start here. |
| `lochara-part` | Stage 3: prompts that work, picking, the 3D run, what can go wrong. |
| `lochara-build` | Stages 4–6: placing parts, styling, renders, the contract, export. |

Each records what has actually worked; when a stage changes, update its skill in the same commit.
