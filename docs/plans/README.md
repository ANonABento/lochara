# Roadmap

lochara's focus is **anime-style avatars** (toon-shaded, like VTuber and VRChat models) made locally from your own
design, for the web, VTubing and VRChat.

| | Milestone | Status |
|---|---|---|
| M0 | **Restyle route**: a rigged base (VRoid) styled by a recipe, generated rigid parts on bones, contract and budget checks, GLB export. CLI, docs, skills, two examples. | Done |
| M1 | **Setup and spikes** S1–S7 for the design route: views, 3D hair and outfit, split, paint, fit and rig on a template, springs, a character LoRA. | Next ([plan](generated-character.md), [setup](#setup-for-m1)) |
| M2 | **Design route, commands**: `views`, `model`, `split`, `paint`, `fit`, `rig`, `springs`, the `anime-avatar` profile. | After M1 |
| M3 | **Targets**: web and VTuber (VRM 1.0 and 0.x) first, then VRChat PC and Quest. | With M2 ([plan](targets.md)) |
| M4 | **Robot maid v2**: Kevin's design, shipped to BentoSite (and as a VRM). | Design in progress ([plan](maid-v2.md)) |
| M5 | **Polish for others**: a local viewer (proportion sliders, motion and spring check), tests and CI on `examples/basic`, ARKit 52 shapes. | Later |

## Setup for M1
Downloads, with sizes and licences. Nothing is fetched without a yes.

| What | For | Size | Licence |
|---|---|---|---|
| **Qwen-Image-Edit 2511** | views from the design (S1) | 57.7 GB download (runs quantised in ~25 GB memory) | Apache-2.0 |
| Turnaround LoRA for Qwen edit (Civitai) | consistent views (S1) | < 1 GB | per the LoRA's page |
| **ComfyUI** | runs Hunyuan3D-2mv and Illustrious on the Mac GPU | ~2 GB with its Python environment | GPL-3.0 |
| **Hunyuan3D-2mv** (one variant) | 3D hair and outfit from 4 views (S2) | ~5 GB of the 29.6 GB repo | Tencent Hunyuan Community (not the EU, UK or South Korea) |
| **Illustrious XL 2.0** | anime concepts and finish | 6.9 GB | CreativeML OpenRAIL-M |
| **VRM Add-on for Blender** | VRM 0.x / 1.0 export, spring bones (S6) | a few MB | MIT |
| SAM 2 (small) | click-to-label for the split (S3), only if colour regions aren't enough | ~0.2 GB | Apache-2.0 |

Already here: FLUX.2 klein 4B and 9B, mflux (including `mflux-train` for S7), Blender 5.2, AssetFurnace with
Hunyuan3D-MLX, VRoid Studio, the CC0 template (AvatarSample E). Disk: 452 GB free.

## Smaller items
- Spring bones from VRM bases are dropped today (VRM-only data); keep them when the output is VRM.
- Report the AssetFurnace engine-lookup bug upstream and drop `third_party/assetfurnace/backend-spec.patch`.
- Pixal3D and TRELLIS.2 are out on a Mac (both need Xcode, which needs an Apple ID).
- `examples/robot-maid`: retune the generated ear (its antenna is hidden in the hair).
