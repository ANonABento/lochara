---
name: lochara-part
description: Generate one rigid part for a lochara character (armour, ears, headgear, props) from a text prompt - draw candidates with FLUX, let the user pick, build the 3D model with AssetFurnace, and check the result. Use when adding or redoing a part.
---

# lochara part: picture → 3D

```
./lochara part draw  <char> <id> "<prompt>" [-n 4] [--seeds ...] [--raw]
./lochara part pick  <char> <id> <seed>
./lochara part model <char> <id> [--engine hunyuan_xiong] [--triangles 3000]
```

## Prompts that work
- One isolated object, three-quarter view, centred, whole object in frame, plain light grey background, no person
  (`part draw` appends this unless `--raw`).
- Say the materials and colours plainly: "glossy white ceramic", "black recessed ring", "thin glowing orange light
  ring". Name the details you want to survive into 3D (screws, seams); small ones come out as paint.
- Lights come out painted, not glowing: plan a `glow` hue range for the part (see lochara-build).
- Rigid only. Anything that must bend (fingers, cloth, hair) belongs to the base, not a part.

## Picking
Show `parts/<id>/candidates/sheet.png`. A good candidate for 3D has a clear silhouette, no cropping, nothing
touching the frame, and no busy background. The user picks; you don't.

## The 3D run
- Hunyuan3D-MLX takes about 20 min on an M-series Mac (shape about 5 min, paint about 13, then Finish). Run it in
  the background and report progress briefly.
- 3000 triangles is the default: about 150-200 KB after optimisation, and still clean at a character's scale. At
  20k, the texture seams stop simplification and a part is about 870 KB.
- **If it stalls:** a run whose step and message stop changing for more than a few minutes, with no
  `hunyuan_mlx_xiong_generate` process running, has died. Check
  `vendor/assetfurnace/output/.studio-mcp.log`. A `KeyError: 'hunyuan_xiong'` means our patch isn't applied:
  `./lochara doctor`, then `./lochara setup assetfurnace` and restart the studio (kill its `serve.py` process).
- After a model: read `parts/<id>/preview.png` (front, three-quarter, side, back) before showing it. Look for missing
  pieces, fused bits, a wrong back side, and burnt or muddy paint where lights were.

## After the user accepts
The part is recorded in `character.json`, disabled and without a bone. Placing it is lochara-build's job.
