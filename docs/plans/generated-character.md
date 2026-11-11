# Plan: characters from your own design (anime avatars)

Today lochara restyles a body that is already rigged (VRoid) and adds rigid parts. This plan adds the route for
**a character made from your own design**: an anime-style avatar (toon-shaded, like VTuber and VRChat models) whose
hair, outfit and accessories are generated from your pictures, on a template body and face that bring a clean rig and
expressions. It follows the shape of [Charakuru](https://github.com/nanocle/Charakuru)'s workflow (see
`docs/research.md`) with every cloud step replaced by something that runs on the machine. Where the result goes (web,
VTubing, VRChat) and what each needs is in [targets.md](targets.md).

Ideas only: Charakuru's licence doesn't allow redistributing its code, skills or bundled body, so nothing of it is
copied here.

## What changes for anime
- **Don't generate the face.** Anime faces are nearly flat: the eyes, brows and mouth live in the texture and move
  by shape keys. Generated faces come out lumpy and have no shape keys. So the face and head come from a template
  (a VRoid face, which already has blink, emotions and mouth shapes) and are **painted from your design**.
- **Do generate what makes the design yours:** hair, outfit, accessories, robot parts. Those are shapes, and shapes
  are what 3D generation is good at.
- **The body bends with real weights:** skin comes from the template; generated clothing gets the template's weights.
- **Flat colour, no painted light.** The toon shader adds the shading (and outlines), so pictures and textures are
  flat cel colour with clean lines. Light painted into a texture reads as dirt.
- **Anime image models.** General models drift on anime faces; anime models and LoRAs hold them.

## The route at a glance

```
design ─► character ─► views ─► 3D ─────► split ─► paint ─► fit ──────► rig ───► face, springs ─► export
(you)     LoRA         8 + 3    hair,      locks,   from     to the      donor    expressions,     per target:
          (optional)   pictures outfit,    skirt,   your     template    weights  spring bones     GLB, VRM,
                                parts      shells   pictures body, face                            Unity FBX
   ▲                    ▲        ▲                   ▲        ▲                    ▲
   checkpoint           checkpoint (pick)            checkpoint                    checkpoint (motion)
```

Every arrow is one `lochara` command that writes into the character folder and stops for review. Everything generated
is kept beside the prompt, seed and model that made it.

## Stage by stage

### 1. Design (human)
One full-body picture is the authority for the design: face, hair (full length), outfit, colours, asymmetry. Your own
drawing (a clean sketch with colour notes is enough), a commission, or concepts iterated with `lochara concept`.
`design.md` adds what the picture can't show: the back, materials, what glows, what moves.

### 2. Character LoRA (optional, recommended)
Once the design is approved, train a small LoRA of this one character on the design picture plus the best approved
views (`mflux-train`, installed, runs locally). Every later picture (views, expressions, texture fixes) then keeps the
same face and outfit. Spike S7.

### 3. Views
**Charakuru:** an image model paints the head with all its hair, and the clothed body in a T-pose, front, left,
right and back (8 pictures), then three full-body balance views.

**lochara:** `lochara views <char>`, the same 8 + 3, one part and one view per run, front first; the other views
also get the approved front.

| Job | Model | Runs with |
|---|---|---|
| Views from the design | **Qwen-Image-Edit 2511** (4-bit) + the **Multiple-Angles LoRA** (set camera angle per view) + the **Lightning LoRA** (4–8 steps) | `mflux-generate-qwen-edit` |
| Concepts, anime finish | **Illustrious XL 2.0** (SDXL anime) + style LoRAs | ComfyUI |
| Quick drafts | FLUX.2 klein (installed) | mflux |
| Bring your own | any tool, or your own hand | drop PNGs into `views/` |

The picture rules (our wording of what Charakuru enforces, plus the anime ones):
- **Split:** `head` = face, ears, all hair to the longest tips, head accessories; no neck. `body` = neck down,
  outfit, hands, legs, shoes; no head, no hair.
- **Pose:** head upright, eyes level, neutral face, mouth closed. Body in a true T-pose, feet hip-width apart with a
  gap between the shoes.
- **Sides are the character's own** (in `left` the nose points screen left). Never mirror one side to make the other.
- **Same canvas:** square, transparent, same scale and baseline across a part's four views.
- **Flat cel colour, clean lines, no lighting or cast shadows** (the shader does that).
- **Two tries:** if a fix doesn't improve after two edits, stop and say what's still wrong.

*Checkpoint:* review all 11.

### 4. 3D: hair, outfit, accessories
`lochara model <char> hair|outfit|<part>` makes several candidates from the views, each Finished to a triangle
budget and previewed from four sides.

| Engine | Input | Notes |
|---|---|---|
| **Pixal3D multiview** | front, left, back, right | ComfyUI's own PyTorch port (template `3d_pixal3d_multi_views`): shape *and* texture painted from the views, plus decimate, remesh and UV atlas nodes. No Xcode. MIT. |
| **Hunyuan3D-2mv** | front, left, back, right | ComfyUI template `3d_hunyuan3d_multiview_to_model`. Shape only. Tencent licence. |
| Hunyuan3D-MLX (AssetFurnace) | front | Works today (the ear). For small rigid parts. |

Spike S2 compares the two multiview engines on the same views.

For the hair and outfit, the views are masked to just that piece (the head views without the face for hair; the body
views as they are for the outfit), so the engine builds only what will be used.

*Checkpoint:* pick one candidate of each.

### 5. Split
`lochara split <char>`:
1. Connected pieces first.
2. Labels from the pictures: each view is a known orthographic camera, so a 2D label map per view (colour regions or
   SAM 2 clicks) is projected onto the mesh, and each face takes the majority vote.
3. Groups: hair locks (each a spring chain later), skirt, apron, ribbons, rigid shells (robot plates).

When something that should move is fused to something that shouldn't, stop and show it (spike S3).

### 6. Paint
`lochara paint <char>`: UV unwrap per group in Blender, then project the approved views' real pixels onto the surface
(AssetFurnace's `photo_paint`, Apache-2.0). The template face gets your design's eyes, brows and mouth painted into its
texture, on the face's existing UV layout, so its expressions keep working. Bake at 2K–4K, ship at the target's size.

### 7. Fit to the template
The template is a VRoid body and face: a CC0 sample (AvatarSample E, already used) or your own VRoid Studio export.
`lochara fit <char>`:
- Body proportions from the balance views (height, head size, limb lengths) applied to the template by bone scale.
- Hair placed on the head, outfit on the body, checked against the balance views (`lochara render --compare`).
- The template's own hair and clothes removed.

*Checkpoint:* proportions and fit.

### 8. Rig
Weights for generated clothing are copied from the fitted template body (Blender Data Transfer, nearest face,
interpolated, top 4, normalised). Rigid pieces are parented to one bone, as parts are today. Report: vertices far from
the body (loose cloth), plus renders of bent elbows, knees and shoulders.

*Checkpoint:* the bend renders.

### 9. Face and springs
- **Expressions:** the template's shape keys, renamed per target: VRM presets (blink, emotions, aa/ih/ou/ee/oh,
  look), VRChat visemes, and optionally the 52 ARKit shapes for iPhone face tracking (see `targets.md`).
- **Springs:** chains for hair locks, skirt, ribbons (root fixed, weights fading to the tip) with colliders on the
  head, chest, hips and legs. VRM spring bones via the VRM Add-on for Blender; for VRChat, PhysBones are added in Unity
  (the export carries a list of the chains).

*Checkpoint:* a walk and a drag test in a local three-vrm viewer, like Charakuru's motion check.

### 10. Export
Per target in `targets.md`: GLB (web), VRM 0.x and 1.0 (VTubing), FBX plus a setup note (VRChat), each with its
contract and budget checked. Name, author and licence come from `character.json`, never guessed.

## Format sketch
```jsonc
{
  "route": "generated",
  "profile": "anime-avatar",
  "design": {"picture": "design/front.png", "brief": "design/design.md", "lora": "design/lora.safetensors"},
  "template": {"file": "assets/AvatarSample_E.vrm", "keep": ["body", "face"]},
  "views": {"engine": "qwen-edit-2511", "loras": ["multiple-angles", "lightning-8"], "seed": 3},
  "model": {"hair": {"engine": "pixal3d-mv", "pick": "hair-2", "triangles": 8000},
            "outfit": {"engine": "pixal3d-mv", "pick": "outfit-1", "triangles": 15000}},
  "split": {"groups": {"hair_back": [...], "skirt": [...]}, "moving": ["hair_back", "skirt"]},
  "fit": {"height": 1.55, "head": 1.0, "arms": 1.0, "legs": 1.0},
  "springs": [{"group": "skirt", "stiffness": 1.0, "gravity": 0.15, "drag": 0.4}],
  "targets": ["web", "vtuber"],
  "meta": {"name": "...", "author": "...", "licence": "..."}
  // parts, style (materials), output, contract and export work as they do now
}
```

## Spikes first
Each answers one question on a real character before its command is written. S1 and S2 decide whether the route
works here.

| | Question | Done when |
|---|---|---|
| S1 views | Can Qwen-Image-Edit 2511 (+ the angles and Lightning LoRAs) make 4 consistent views of the head and the T-posed body from one design picture? | 8 views a human would accept, under 10 tries each. |
| S2 3D | Pixal3D multiview vs Hunyuan3D-2mv on the hair and the outfit: are the sides and back right, are locks and skirt separate? | One hair and one outfit we'd keep. |
| S3 split | Does projecting per-view labels give clean groups? | Groups match the pictures from 4 sides. |
| S4 paint | Projected pixels on the hair, outfit and the template face. | Renders that read as the design. |
| S5 fit + rig | Template fitted, clothing weighted: clean bends? | Bend renders with no tearing. |
| S6 springs | VRM Add-on spring chains on the skirt and hair, checked in three-vrm. | A drag test that swings. |
| S7 LoRA | Does a character LoRA trained locally make views and expressions more consistent? | Same face across 10 pictures. |

### S1 so far (2026-11-10, bastet-smol)
- **Setup:** 4-bit Qwen-Image-Edit 2511 in mflux, plus Lightning 8-step and the angles LoRA (`<sks> <azimuth> <elevation> <distance>`).
  - Both LoRAs are baked into `vendor/hf/qwen-edit-2511-views-q4` (`mflux-save --bake-lora`, 33 GB). The pictures are
    the same as with the LoRAs loaded at run time.
  - mflux won't read the angles LoRA's key names, so it's renamed first (`vendor/hf/angles-lora-mflux.safetensors`).
    It applies 12 of its 14 layer types; mflux has no mapping for `img_mod`/`txt_mod`.
- **Runner:** `spikes/s1_views.py` encodes every view's prompt, then drops the 14 GB text encoder (mflux never
  quantizes it). It runs the image model once per step: at guidance 1 the negative pass changes nothing.
  - One 768×1152 view: 9.5 min, against 22 min with `mflux-generate-qwen-edit`. Peak is about 25 GB, but swap doesn't
    grow, so the limit now is the M5's 10-core GPU (about 70 s per step), not memory.
- **Results:**
  - **Body views pass.** Front, right, back and left all match the design and each other: the tail, bands, collar
    and sandals are right from every side.
  - 4 steps fade and ghost the harder angles. 8 steps are clean.
  - **Head views:** "close-up" doesn't reframe a full-body picture, and a head cropped from the design fails (ghosted,
    no turn). The heads cropped from the body views are clean and consistent, but only about 270 px; upscale them
    (`mflux-upscale-seedvr2`) if S2 needs more.
- **Left to check:** the T-pose (the design is an A-pose), and a second design.

### S2 so far (2026-11-10, bastet-smol)
- **Runner:** `spikes/comfy_run.py` runs a ComfyUI template through the API, with pictures and settings swapped in.
  It turns the editor's lists of values into named inputs, and runs the side views the templates switch off.
- **Input:** the 4 body views from S1 (Hunyuan gets them cut out on white; Pixal3D cuts them out itself with BiRefNet).
- **Hunyuan3D-2mv:** 11.5 min, 186k triangles, shape only.
  - The shape matches the design from every side, and the tail is its own piece.
  - The skirt is streaky and fused to the legs; the face and bands are mush.
- **Pixal3D (picked):** 13.5 min, 700k triangles (44 MB), shape and colour.
  - The colours match the design, the face, headband and bands are readable, the skirt is clean and the legs separate.
  - It needs simplifying, and its front faces the other way from Hunyuan's.
- **Pixal3D needs a ComfyUI patch on a Mac.** Its colour step's `grid_sample` overflows int32 on MPS, at any detail
  setting. `vendor/comfyui/comfy/ldm/trellis2/model.py` `_sample_features` now falls back to the CPU on that error
  (the original is `model.py.orig`). A ComfyUI update will undo the patch.
- **Both are one fused mesh:** hair, body and dress need splitting (S3).

## Risks
- **Anime faces from generated views** may still drift; the LoRA (S7) and painting the face on the template are the
  mitigations.
- **Fused geometry:** hair fused to the back, skirts to legs. Multiview input helps; else generate the piece on its
  own (the part route).
- **Every avatar looking like VRoid:** the template's face shape stays. Mitigation: a face shape set by sliders
  (VRoid Studio itself) or a sculpted template later.
- **Memory:** 25.8 GB; Qwen-Image-Edit runs quantised (4- or 8-bit), one big model at a time.
