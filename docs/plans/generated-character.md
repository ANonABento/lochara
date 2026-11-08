# Plan: generated characters (the Charakuru route, locally)

Today lochara restyles a body that is already rigged (VRoid) and adds rigid parts. This plan adds the other route:
**a character made from your own design**, where the head, hair, body and outfit are generated as 3D models and then
rigged. It follows the shape of [Charakuru](https://github.com/nanocle/Charakuru)'s workflow (see
`docs/research.md`), with every cloud step replaced by something that runs on the machine.

Ideas only: Charakuru's licence doesn't allow redistributing its code, skills or bundled body, so nothing of it is
copied here. Its donor body is replaced by a CC0 one (below).

## The route at a glance

```
design ──► views ──► 3D candidates ──► split ──► paint ──► assemble ──► rig ──► springs, face ──► export
(you)      8 + 3      head, body ×4    parts     4K from   proportions   donor     VRM spring       GLB / VRM
           pictures   (you pick)       by label  pictures  (you adjust)  weights   bones, blink
   ▲          ▲            ▲              ▲                    ▲            ▲           ▲
   checkpoint  checkpoint   checkpoint    checkpoint if joined  checkpoint   checkpoint   checkpoint (motion)
```

Every arrow is one `lochara` command that writes into the character folder and stops for review. Everything
generated is kept beside the prompt and seed that made it.

## Stage by stage

### 1. Design (human)
One full-body picture of the character is the authority for its design: face, hair (full length), outfit, colours,
asymmetry. It can be your own drawing (any fidelity: a clean sketch with colour notes works), a commission, or a
concept you pick and edit with `lochara concept`. A written brief (`design.md`) adds what the picture can't show: the
back, materials, which parts glow, which parts move.

### 2. Views
**Charakuru:** an image model paints the head with all its hair, and the clothed body in a T-pose, each from front,
left, right and back (8 pictures), then three full-body balance views (front, own right side, back).

**lochara:** `lochara views <char>` draws the same 8 + 3 with a local editing model given the design picture as a
reference, one part and one view per run, front first; the other views also get the approved front.

| Model | Run with | Notes |
|---|---|---|
| FLUX.2 klein 4B / 9B, edit mode | `mflux-generate-flux2-edit` (installed) | Fast (seconds). Multi-reference. Consistency across views is the open question (spike S1). |
| Qwen-Image-Edit 2511 | `mflux-generate-qwen-edit` | Slower, larger; AssetFurnace already uses Qwen edit for back views and documents what works. |
| Bring your own | any tool | Drop PNGs into `views/`. A cloud model or your own hand is fine; lochara only checks the files. |

The rules that make the pictures usable for 3D (our own wording of what Charakuru enforces):
- **Split:** `head` = face, ears, all hair to the longest tips, head accessories; no neck. `body` = neck down,
  outfit, hands, legs, shoes; no head, no hair (fill in what the hair hid).
- **Pose:** head upright, eyes level, neutral face, mouth closed. Body in a true T-pose (arms horizontal, elbows and
  wrists straight), feet about hip-width apart with a visible gap between the shoes.
- **Sides are the character's own:** in `left` the character's left side is visible and its nose points screen
  left; in `right`, screen right. Never mirror one side to make the other: asymmetric details must be on the right
  side.
- **Same canvas:** square, transparent, same scale and baseline for all four views of a part.
- **Finish:** paint everything (hair, skin, cloth, metal) to finished-illustration quality; generated textures are
  never better than these pictures.
- **Two tries:** if a fix doesn't improve after two edits, stop and say what's still wrong.

*Checkpoint:* review all 11; redo single views.

### 3. 3D candidates
**Charakuru:** Tripo multiview, four candidates per part, ~25k quads.

**lochara:** `lochara model <char> head|body` sends the views to AssetFurnace and makes several candidates (seeds or
engines), each Finished to a triangle budget and previewed from four sides.

| Engine | Input | Status here |
|---|---|---|
| Pixal3D | front + back | Best results; AssetFurnace's own front+back route. **Needs full Xcode** to compile (free, App Store). |
| Hunyuan3D-MLX | front | Works today. Single view, so the back is invented. |
| TRELLIS.2 | front | Needs Meta's DINOv3 approval. |

*Checkpoint:* pick one head and one body (turntable and wireframe in the contact sheet).

### 4. Split
**Charakuru:** Tripo's segmentation, then the agent labels the pieces by eye: hair, head, upper body, lower body,
accessories for textures, and separately the things that swing (skirt, ribbons, hair locks).

**lochara:** `lochara split <char>`:
1. Connected pieces first (generated meshes are often several shells).
2. Labels from the pictures: each of the 4 views is a known orthographic camera, so a 2D label map per view (by
   colour region, or SAM 2 clicks) is projected onto the mesh and each face takes the majority vote.
3. Seams follow face boundaries; nothing is welded or deleted.

Labels go in `character.json` (`split.groups`); the result is a labelled preview. When a piece that should move
(a skirt) is fused to something that shouldn't (the legs), stop and show it (spike S3).

### 5. Paint
**Charakuru:** Tripo Smart UV and 4K retexture per texture group, guided by new front/back pictures of each group.

**lochara:** `lochara paint <char>`: UV unwrap per group in Blender, then project the approved views' real pixels
onto the surface (AssetFurnace's `photo_paint`, Apache-2.0: blends views by how squarely each sees the surface, keeps
the generated paint only where no picture looks). Our pictures are the design, so copying their pixels beats
re-painting. Bake to one texture per group at the output size.

### 6. Assemble and proportions
**Charakuru:** the user scales and moves the head, hair and body against the translucent balance views.

**lochara:** `assembly` in `character.json` (head scale and offset, height in metres). `lochara render --compare`
overlays the model on the three balance views. Later, a small local viewer with sliders that writes the numbers back
(three.js; optional).

*Checkpoint:* proportions.

### 7. Rig
**Charakuru:** Tripo rigs the head and body with VRM bones; only the bone **positions** are kept. A bundled,
hand-weighted body is fitted to those positions and its weights are copied onto the outfit (nearest triangle,
top 4 influences); hands get Blender's automatic weights; the arms are levelled and the rest pose is baked.

**lochara:** the same idea, locally:
1. **Joint positions:** found from the T-pose mesh (cross-sections give shoulders, elbows, wrists, hips, knees,
   ankles; the split gives the neck), or from SkinTokens (AssetFurnace, MIT, 1.5 GB). Shown as markers on renders,
   stored in `rig.joints`, editable as numbers.
2. **Donor:** a CC0 VRoid sample body (we already use AvatarSample E), or any rigged body you own (a VRoid Studio
   export). Its skeleton is fitted joint by joint; bone names stay the donor's (then the bone preset applies).
3. **Weights:** Blender Data Transfer from the fitted donor (nearest face, interpolated), top 4, normalised; head and
   hair fixed to `Head`; rigid parts parented as today.
4. **Report:** vertices more than 5 cm from the donor (loose cloth), fingers without weights; renders of bent
   elbows, knees and shoulders.

*Checkpoint:* the bend renders.

### 8. Springs and face
- **Springs:** chains for hair locks, skirt, ribbons, from the split's moving groups (root fixed, weights fading to the
  tip), with colliders for the head, chest, hips and legs. Written as VRM 1.0 spring bones with the VRM Add-on for
  Blender (MIT). GLB has no spring bones, so for a web app they are either run by three-vrm (export VRM) or left to
  the app.
- **Face:** the standard route keeps a neutral face. `blink` (what most apps need first): either a morph authored on
  the eyelids, or, for stylised faces, eyes as separate decal meshes squashed by a morph. Other expressions are later.

*Checkpoint:* a walk and a drag test in a local viewer (three-vrm), like Charakuru's motion check.

### 9. Export
GLB (as today, with the contract check and the size budget), plus VRM 1.0 with name, author and licence from
`character.json` (never guessed).

## Format sketch
```jsonc
{
  "route": "generated",                         // "restyle" is today's route
  "design": {"picture": "design/front.png", "brief": "design/design.md"},
  "views": {"engine": "flux2-klein-edit", "seed": 3},
  "model": {"head": {"engine": "pixal3d", "pick": "head-2", "triangles": 12000},
            "body": {"engine": "pixal3d", "pick": "body-1", "triangles": 20000}},
  "split": {"groups": {"hair": [...], "skirt": [...]}, "moving": ["skirt", "hair_back"]},
  "assembly": {"height": 1.55, "head": {"scale": 1.0, "offset": [0, 0, 0]}},
  "rig": {"donor": "assets/AvatarSample_E.vrm", "joints": {...}},
  "springs": [{"group": "skirt", "stiffness": 1.0, "gravity": 0.15, "drag": 0.4}],
  "face": {"blink": "decal"},
  // parts, style (materials), output, contract and export work as they do now
}
```

## Spikes first
Each answers one question on a real character before the command is written. Order matters: S1 and S2 decide
whether the route works at all here.

| | Question | Done when |
|---|---|---|
| S1 views | Can FLUX.2 klein edit (or Qwen edit) make 4 consistent views of a head and a T-posed body from one design picture? | 8 views a human would accept, under 10 tries each. |
| S2 3D | Hunyuan (front) vs Pixal3D (front + back) on that head and body: is the back usable, are hair locks and skirt separate shells? | One head and one body we'd keep. Needs Xcode for Pixal3D. |
| S3 split | Does projecting per-view labels give clean hair / face / skirt groups? | Groups match the pictures from 4 sides. |
| S4 paint | Does projecting the views' pixels beat the engine's own paint? | Side-by-side renders. |
| S5 rig | Fit AvatarSample E's body to the generated T-pose and transfer weights: do shoulders, elbows and knees bend cleanly? | Bend renders with no tearing. |
| S6 springs | Blender VRM Add-on: spring chains on the skirt, exported, checked in three-vrm. | A drag test that swings. |

## Risks
- **View consistency** with a 4B model may be the weak link; Qwen edit or bring-your-own pictures are the fallbacks.
- **Fused geometry:** single-image engines fuse hair to the back and skirts to legs. Front + back (Pixal3D) helps; if
  not, generate the moving parts as separate rigid or spring parts (lochara's part route).
- **Texture budget:** 4K per group doesn't fit a web budget (BentoSite allows 1.5 MB in total); paint at 4K, ship at
  1K.
- **Memory:** 25.8 GB; one big model at a time, as now.
