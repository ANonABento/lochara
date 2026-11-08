---
name: lochara-build
description: Build a lochara character - style the base, place parts on bones, render for review, check the contract and export the GLB. Use when placing or adjusting parts, changing a character's style, checking a build, or shipping it to an app.
---

# lochara build: style, place, check, export

```
./lochara build  <char>
./lochara render <char> [--focus <bone>] [--span 0.45] [--name <file>] [--open]
./lochara check  <char> [--file <glb>]
./lochara export <char> [--to <path>] [--force]
```
Format reference: docs/character-format.md.

## Placing a part
1. Pick the bone it moves with (`Head` for anything on the head, `Spine2` for the chest, `LeftForeArm` ...). The
   bone names are in the check output, or `./lochara check` with a missing bone lists them.
2. Start from a known spot: `offset` is `[right, up, forward]` metres from the bone's head, in the character's own
   directions. A Head bone's head is at the base of the skull, about chin height: ears are about
   `[±0.11, +0.03, -0.02]` for an adult-sized VRoid head.
3. `size` is the longest side in metres, antennas and all; measure against the thing it replaces.
4. `rotation` `[pitch, yaw, roll]`: at zero the part's front faces forward; yaw `-90` faces the character's right
   (use with `mirror: true` for pairs: the copy faces left).
5. `glow: {"hue": [10, 45]}` for orange lights, `[170, 200]` cyan; the build prints what percentage lights up
   (a few percent for a light ring; tens of percent means the range catches the body colour).
6. Enable it, build, `render --focus <bone>`, read the render, adjust, repeat. Show the user when it sits right.

## Style
Generic rules first (bones preset, morph detect/keep, material delete/tint/emissive). When a character needs more
(sculpted geometry, texture repainting), give it its own `style.script`, as `examples/robot-maid` does, with
switches passed through `style.env`.

## Render gotcha
An optimised GLB re-imported in Blender has its skinned meshes' rest data far from the character (quantisation).
The renderer already frames the skinned result and posed bones; if you write Blender code that reads positions from
a build, use the evaluated mesh, not `mesh.vertices`.

## Check and export
The build ends with the check. A failing contract means the app will break: fix the recipe (bones preset, morphs)
rather than `--force`. Export only after the user has seen the render, then tell them where it went and what to
re-check in their app.
