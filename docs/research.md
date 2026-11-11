# Research: character pipelines and tools

What we looked at for building a rigged web character from scratch, and what we took from each. Last updated
2026-11-10.

## What went wrong before (October 2026, in BentoSite)
About 40 commits tried to get one anime maid out of FLUX → TRELLIS in one pass. Generating the whole body at once
gives one fused shell: hair, frills and body in a single mesh, so nothing can move separately. Skin weights guessed
from vertex distance then tore the hand. Scripted primitive busts were rejected as not good-looking enough. What
works now is a CC0 VRoid sample (AvatarSample E) restyled by `examples/robot-maid/style/vroid_maid.py` with rigid robot parts attached
to bones.

**Lesson:** never generate the whole character as one mesh. Build it in parts, and take skin weights from a body
that is already rigged.

## Charakuru (nanocle/Charakuru)
A local app plus 9 agent skills that turn one illustration into a VRM 1.0, sponsored by Tripo. Released October 2026,
about 1.4k stars, marked as in development. Source-available: free for personal and commercial use while your revenue
and your funding are each under ¥100M; the bundled base body can't be taken out of the kit.

**Its workflow** (stages run by the agent, with the human at checkpoints):
1. **8 part images.** The agent paints the head with hair, and the body with the outfit, in 4 views each (front,
   left, right, back), plus full-body balance references. The head is straightened with a calm, closed mouth; the
   body is in a T-pose. *Human checkpoint:* review all 8, ask for fixes to single images.
2. **3D candidates.** Tripo makes 4 candidates each for the head and the body from the views. *Checkpoint:* compare
   (turntable, wireframe) and pick one of each.
3. **Parts and textures.** Tripo splits the parts and sorts them into 5 texture groups (hair, head, upper body, lower
   body, accessories) and separate physics groups (the skirt stays its own mesh). UV unwrap, 4K re-texture. Joined
   shapes that can't be split go to the human with a picture.
4. **Proportions.** *Checkpoint:* the human scales and moves the head, hair and body against translucent reference
   views at a shared height and foot level.
5. **Rig.** Tripo rigs the head (no hair) and body, but only the bone *positions* are kept. Weights are **copied from
   a bundled, hand-weighted base body**. Hair goes back on, physics for hair, skirt and ribbons.
6. **Motion check.** *Checkpoint:* a walk cycle with physics; drag the model to test springs; load other motions.
7. **Export.** VRM with name, author and licence; the editable .blend is kept too.
8. Optional **expressions**: eye, mouth and brow poses fitted from a library.

**What it gets right, and what we copy:**
- Head with hair and body are separate generations, then joined.
- Weights come from a known-good base body, not a guess.
- The agent never picks for you: it stops at each visual checkpoint.
- Everything lives in one project file, with no "final2" copies.
- Skills hold the know-how per stage, so the process can be repeated.

**Inside the kit** (release 1.1.1, read 2026-11-08; the skills only ship in the release ZIP, not the repo): a local
Node app holds one project file per character and hands each stage to the agent as a copied request; ten skills,
one per stage. What the skills add to the summary above:
- **Picture rules** do most of the work: head = face + all hair (never a bald head plus a separate wig); body =
  neck down, no hair; head upright with a neutral closed mouth; true T-pose with a gap between the shoes (it helps
  later steps tell the legs apart); sides named from the character's own point of view, never mirrored; one part,
  one view per generation, front first, the others given the approved front; stop after two failed fixes.
- **Balance views** (full-body front, own right side, back) come *after* the part pictures and are only used to
  check proportions; they never feed back into the parts.
- **Two separate groupings** of the same pieces: five texture groups (hair, head, upper body, lower body with legs
  and shoes, accessories) and the things that swing. A skirt separated from the legs for physics still shares the
  lower body's texture.
- **Retexture** uses new front and back pictures per texture group, drawn over a wireframe guide of the real mesh, so
  the paint matches the geometry.
- **Rig:** only the joint positions come from the auto-rig. The bundled body is fitted to them (torso stretched
  along one vertical, limbs matched by bone length, width and depth corrected within 0.8–1.2), its weights copied by
  nearest triangle and trimmed to 4, hands weighted by Blender's automatic weights on a local patch, blended at the
  wrist. Then the arms are levelled and the rest pose baked, refusing models with constraints, animations or shape
  keys rather than silently dropping them.
- **Springs:** VRM 1.0 chains (root fixed, weights fading to the tip), skirt colliders on the legs, and a check that
  compares vertex positions with physics on and off over 90 frames, per part. Checks prove it works, not that it
  looks good; looks are the user's call.
- **Expressions** (optional lab): eye, mouth and brow shapes fitted from a library onto the new face.

**Why we don't run it as shipped:** it is built for Codex, whose built-in image generation paints the 8 images and
which drives Tripo's website. Tripo's Smart Mesh, which the workflow depends on, is paid: the free plan is about
200–300 credits a month (sources disagree) with only a one-day Smart Mesh trial, so realistically one month of Pro
at about $20. It also needs Blender 5.2, the VRM add-on and Blender MCP.

## Local tools (all on the M5 Mac, 25.8 GB memory)

| Tool | Role | Status for us |
|---|---|---|
| **VRoid Studio** (installed) | Base body: separate hair, outfit and body, a proper humanoid rig with fingers, expressions, physics. Free, local. | **In use** (sample E). The base for any custom character. |
| **FLUX.2 klein 4B** via `mflux` (cached) | Concept and part pictures, about 15 s each. Apache-2.0. | **In use** (`lochara concept`, `lochara part draw`). |
| **AssetFurnace** (Bingeljell/image-to-3dlab, Apache-2.0) | Local studio around several picture → 3D engines; Finish (cleanup to a set triangle count, compression); SkinTokens auto-rig; MCP server for agents. | **Installed** in `vendor/assetfurnace`, v0.5.7 plus our patch (`third_party/assetfurnace/`). |
| ↳ its other tools | `photo_paint` paints a model with the real pixels of its source pictures; a front + back route (Pixal3D) with a Qwen-Image-Edit back drawer; a "hero" route that builds the head on its own and grafts it on; background removal (BiRefNet). | The pieces the generated route (`docs/plans/`) builds on. |
| ↳ Hunyuan3D-MLX (Xiong) | Shape plus painted texture, about 20 min per part. 13.9 GB. Tencent licence (not the EU, UK or South Korea). | **Works.** Ear unit test: clean from all sides. |
| ↳ Pixal3D | AssetFurnace's best engine; can paint the source picture's real pixels back onto the model. 8.6 GB, MIT. | AssetFurnace's build needs full **Xcode**; ComfyUI's PyTorch port (multiview: front, left, back, right) runs without it. |
| ↳ TRELLIS.2 | Highest fidelity. 16.7 GB, MIT. | Needs Meta to approve **DINOv3 access** on Hugging Face. |
| ↳ SkinTokens auto-rig | Skeleton plus weights for a generated humanoid. 1.5 GB, MIT. | Not installed. Only needed if we ever generate a whole body. |
| **trellis-mac** | TRELLIS.2 on its own, on the Mac's GPU; about 18 GB peak memory, colours on vertices. | Superseded by AssetFurnace. |
| **StdGEN** | Research: anime character split into body, clothes and hair. Closest match on paper. | Needs an NVIDIA GPU; its online demo was out of free quota. |
| **PartCrafter**, **Hunyuan3D-Part** | Generation already split into parts. | NVIDIA only; online demos broken (October). |
| **UniRig** (MIT) | Automatic rigging. | NVIDIA only; SkinTokens (in AssetFurnace) is its successor. |
| **Tripo** (cloud) | Charakuru's engine: candidates, Smart Mesh, part split, retexture, rig. | Paid for Smart Mesh; keep as a fallback. |

## First test: ear unit (2026-11-08)
FLUX concept (seed 8 of 4) → Hunyuan3D-MLX → Finish. Shape faithful from front, ¾, side and back, nothing fused. At
the default 20k triangles it was 870 KB after compression (texture seams block simplification); at 3k triangles
171 KB and still clean at prologue scale. The orange ring is painted, not glowing, and came out a little burnt, so
glow is a material we add when fitting. Renders: `examples/robot-maid/renders/parts-p1-ear-hy*.png`; on the maid, `examples/robot-maid/renders/lochara-generated-ears.png`.

## Anime-style avatars (2026-11-08)
The target style is anime avatars: toon-shaded (MToon for VRM; lilToon or Poiyomi in VRChat), with expressions by
shape keys and hair and skirts on spring bones.
- **Image models:** the community favours anime-trained models over general ones: Illustrious XL and NoobAI-XL
  (SDXL family) for concepts, Qwen-Image-Edit 2511/2509 with turnaround LoRAs for views of one character (one known
  flaw: the Civitai turnaround LoRA draws characters a little narrow). An experimental anime-consistency adapter exists
  for Qwen-Image 2.1. A LoRA of the character itself is the usual way to keep one face across many pictures.
- **3D:** generated anime faces are lumpy and have no shape keys, so the face comes from a template (VRoid) and only
  hair, outfit and accessories are generated. Hunyuan3D-2mv takes 4 views (ComfyUI supports it natively; shape only).
- **Commercial tools** (Neural4D AnimeArt, img2avatar, Meshy, Tripo) do image → rigged avatar in the cloud; most
  export FBX or GLB, a few VRM.
- **VRChat:** performance ranks cap Quest avatars at 7.5k triangles for Excellent, 10k Good, 15k Medium; PhysBones
  and colliders are limited on mobile. Uploads go through Unity and VRChat's SDK.
- **VTubing apps** read VRM; some (VSeeFace) only VRM 0.x. iPhone "perfect sync" tracking needs the 52 ARKit shapes.

## Revisit after S2 (2026-11-10)
The S2 models (Pixal3D, Hunyuan3D-2mv) of bastet-smol weren't good enough. Why, and what others do:
- **We broke our own rule.** S2 fed the engines the whole character, so the face came out lumpy and the hair, dress
  and body fused: the October lesson again. The plan only generates hair, outfit and accessories, each on its own;
  the face and body come from the VRoid template.
- **The views were off-spec:** the design is in an A-pose (the rules want a T-pose with a gap between the shoes), and
  the heads cropped from the body views are only about 270 px.
- **The best engines aren't local on a Mac:** Tripo and Rodin are cloud; TRELLIS.2, StdGEN, PartCrafter and HairDeck
  need an NVIDIA GPU.
- **How others get good results:**
  - Charakuru: head with hair and body generated separately, Tripo candidates picked by a person, Tripo's part split
    and retexture, weights from a hand-weighted body.
  - VRChat and VTuber creators: mostly VRoid Studio for hair and outfit, textures painted from the design; AI 3D is
    used for props.
  - 2026 comparisons: Tripo fastest and best for stylized models, Rodin most detail (more cleanup), Hunyuan3D the
    best open option. None test VRM.
- **New research that fits:**
  - **HairDeck** (Nov 2026, Apache-2.0): anime hair cards with spring bones from one picture, exported as VRM.
    Linux and an NVIDIA GPU only (PyTorch 2.8, CUDA 12.8); SAM 3 and DINOv3 are gated downloads.
  - **Anime-Ready** (ICLR 2026): garments fitted to an anime body, piece by piece. No code yet.
  - CharacterGen (SIGGRAPH 2024, multiview, no parts), CHARM (anime hair, superseded by HairDeck), See-through
    (SIGGRAPH 2026, splits an anime picture into up to 23 2D layers: could mask hair and outfit for the views).
- **Next, in order:**
  1. Rerun S2 the planned way: Pixal3D on the hair alone (head views, face masked) and the outfit alone, from T-pose
     views; face and body from the VRoid template.
  2. If the hair is still weak, rent a cloud NVIDIA GPU for HairDeck (and TRELLIS.2).
  3. Fallbacks: Tripo as Charakuru uses it (about $20 for a month of Pro), or hair and outfit by hand in VRoid Studio.

## Sources
- https://github.com/nanocle/Charakuru (README, docs/tutorial.md, docs/license.md)
- https://github.com/Bingeljell/image-to-3dlab
- https://costbench.com/software/ai-3d-generation/tripo-ai/free-plan/
- https://www.tripo3d.ai/getting-started/zero-to-3d-getting-started-credits-pricing-guide
- https://github.com/shivampkumar/trellis-mac/wiki
- https://arxiv.org/html/2411.05738v1 (StdGEN)
- https://github.com/Tencent-Hunyuan/Hunyuan3D-Part
- https://github.com/VAST-AI-Research/UniRig
- https://civitai.com/models/2149265/character-turnaround-sheet-qwen-image-edit-25112509
- https://comfyui-wiki.com/en/news/2026-09-27-qwen-image-2-1-loras
- https://docs.comfy.org/tutorials/3d/hunyuan3d-2
- https://wiki.vrchat.com/wiki/Avatar_Performance_Ranking
- https://www.3daistudio.com/blog/best-ai-tools-for-vrchat-vtuber-avatars-2026
- https://github.com/hyz317/HairDeck/wiki
- https://comfyui-wiki.com/en/news/2026-11-02-hairdeck
- https://explainx.ai/blog/hairdeck-hair-cards-single-image-tsinghua-2026
- https://en.papernotes.org/ICLR2026/3d_vision/anime-ready_controllable_3d_anime_character_generation_with_body-aligned_compone/
- https://github.com/zjp-shadow/CharacterGen
- https://github.com/hyz317/CHARM
- https://github.com/shitagaki-lab/see-through
- https://www.3daistudio.com/blog/best-ai-3d-character-and-avatar-generators-2026
- https://zeroatoms.com/blog/ai-3d-model-generators-for-games
- https://ideate.xyz/blogs/posts/ai-3d-model-comparison-trellis-tripo-meshy-rodin-hunyuan
- https://www.vitalify.asia/en/blog/ai-image-to-3d-generators-comparison
