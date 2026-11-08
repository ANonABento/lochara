# Roadmap

| | Milestone | Status |
|---|---|---|
| M0 | **Restyle route**: a rigged base (VRoid) styled by a recipe, generated rigid parts on bones, contract and budget checks, GLB export. CLI, docs, skills, two examples. | Done |
| M1 | **Generated route, spikes** S1–S6: views, 3D from views, split, paint, rig by donor weights, springs. | Next ([plan](generated-character.md)) |
| M2 | **Generated route, commands**: `views`, `model`, `split`, `paint`, `assemble`, `rig`, `springs`, VRM export. | After M1 |
| M3 | **Robot maid v2**: a design by Kevin, built as a hybrid (rigid robot shells, skinned cloth), shipped to BentoSite. | Design in progress ([plan](maid-v2.md)) |
| M4 | **Polish for others**: a small local viewer (proportions sliders, motion and spring check), tests and CI on `examples/basic`, more bone presets. | Later |

## Smaller items
- Spring bones from VRM bases are dropped today (VRM-only data). Keep them when the output is VRM.
- Report the AssetFurnace engine-lookup bug upstream and drop `third_party/assetfurnace/backend-spec.patch`.
- Hunyuan3D-2mv (multiview) as an engine; Pixal3D and TRELLIS.2 only if needed (both need full Xcode on a Mac).
  Hunyuan's licence excludes the EU, UK and South Korea.
- `examples/robot-maid`: retune the generated ear (its antenna is hidden in the hair).
