# Roadmap

lochara's focus is **anime-style avatars** (toon-shaded, like VTuber and VRChat models) made locally from your own
design, for the web, VTubing and VRChat.

| | Milestone | Status |
|---|---|---|
| M0 | **Restyle route**: a rigged base (VRoid) styled by a recipe, generated rigid parts on bones, contract and budget checks, GLB export. CLI, docs, skills, two examples. | Done |
| M1 | **Spikes** S1–S7 (setup done) for the design route: views, 3D hair and outfit, split, paint, fit and rig on a template, springs, a character LoRA. | Next ([plan](generated-character.md), [setup](#setup-for-m1)) |
| M2 | **Design route, commands**: `views`, `model`, `split`, `paint`, `fit`, `rig`, `springs`, the `anime-avatar` profile. | After M1 |
| M3 | **Targets**: web and VTuber (VRM 1.0 and 0.x) first, then VRChat PC and Quest. | With M2 ([plan](targets.md)) |
| M4 | **Robot maid v2**: Kevin's design, shipped to BentoSite (and as a VRM). | Design in progress ([plan](maid-v2.md)) |
| M5 | **Polish for others**: a local viewer (proportion sliders, motion and spring check), tests and CI on `examples/basic`, ARKit 52 shapes. | Later |

## Setup for M1
Installed 2026-11-08 into `vendor/` (gitignored) and the Hugging Face cache. Everything below was found ready-made
(pre-quantized repos, ComfyUI's own templates and nodes) rather than built.

| What | For | Size | Licence | Where |
|---|---|---|---|---|
| **Qwen-Image-Edit 2511, 4-bit for mflux** (`mflux-community/qwen-image-edit-2511-mflux-q4`) | views from the design (S1) | 29.0 GB | Apache-2.0 | HF cache |
| **Lightning LoRA** 4- and 8-step (`lightx2v/Qwen-Image-Edit-2511-Lightning`) | 5–10x faster Qwen edits | 1.7 GB | Apache-2.0 | HF cache |
| **Multiple-Angles LoRA** (`fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA`) | one view per run at a set camera angle (96 poses) | 0.3 GB | Apache-2.0 | HF cache |
| **ComfyUI** | runs the 3D engines and SDXL on the Mac GPU; its templates `3d_pixal3d_multi_views`, `3d_hunyuan3d_multiview_to_model` are the starting workflows | ~2 GB with its Python environment | GPL-3.0 | `vendor/comfyui` |
| **Pixal3D multiview** (ComfyUI's PyTorch port: front, left, back, right in; no Xcode) + DINOv3 encoder + TRELLIS.2 VAEs | 3D with texture from 4 views (S2) | 14.3 GB | MIT | `vendor/comfyui/models` |
| **Hunyuan3D-2mv** (ComfyUI repackaged) | 3D shape from 4 views (S2, the comparison) | 4.9 GB | Tencent Hunyuan Community (not the EU, UK or South Korea) | `vendor/comfyui/models` |
| **BiRefNet** | background removal | 0.4 GB | MIT | `vendor/comfyui/models` |
| **Illustrious XL 2.0** | anime concepts and finish | 6.9 GB | CreativeML OpenRAIL-M | `vendor/comfyui/models` |
| **VRM Add-on for Blender** | VRM 0.x / 1.0 export, spring bones (S6) | 2 MB | MIT | Blender extensions |

Not fetched: the full-precision Qwen edit (57.7 GB; the 4-bit one fits 25.8 GB of memory), the Civitai turnaround
LoRA (it draws a sheet of all angles at once and narrows characters; the angles LoRA does one view at a time), and
SAM 2 (only if colour regions aren't enough for the split).

Already here before: FLUX.2 klein 4B and 9B, mflux (including `mflux-train` for S7), Blender 5.2, AssetFurnace with
Hunyuan3D-MLX, VRoid Studio, the CC0 template (AvatarSample E).

Run ComfyUI: `vendor/comfyui/.venv/bin/python vendor/comfyui/main.py --listen 127.0.0.1 --port 8188`.

## Smaller items
- Chat driving, Claude or Waymond, through one pipeline runner in Choomfie ([plan](drivers.md)). Steps 1 (`askBrain`,
  choomfie #101) and 2 (`lochara next --json`) are done; next is the runner in Choomfie.
- Spring bones from VRM bases are dropped today (VRM-only data); keep them when the output is VRM.
- Report the AssetFurnace engine-lookup bug upstream and drop `third_party/assetfurnace/backend-spec.patch`.
- AssetFurnace's own Pixal3D and TRELLIS.2 builds need Xcode (an Apple ID); ComfyUI's Pixal3D port doesn't.
- `examples/robot-maid`: retune the generated ear (its antenna is hidden in the hair).
