---
name: lochara
description: Make or change a rigged 3D character with lochara (local character creation): set up the tools, start a character, and run the workflow concept → base body → parts → build → check → export with a checkpoint at each stage. Use for any request to create, restyle, add parts to, or export a character in this repo.
---

# lochara: the workflow

1. **Where are we?** `./lochara doctor` (tools), `./lochara list` (characters). For a character, read its
   `character.json` and look at what exists: `concepts/`, `parts/*/`, `build/`, `renders/`. Tell the user which
   stage it's at.
2. **Missing tools:** `./lochara setup assetfurnace` installs code only. Engine weights: show `./lochara engines`,
   say the size and licence, and wait for a yes before `./lochara setup engine <id> --yes`. Pixal3D needs full
   Xcode; TRELLIS.2 needs approved DINOv3 access on Hugging Face; Hunyuan3D-MLX (`hunyuan_xiong`) needs neither.
3. **Run the stage the user wants**, following docs/workflow.md. Parts: the `lochara-part` skill. Building, placing,
   styling, rendering, exporting: the `lochara-build` skill.

## Checkpoints (stop and show each one, then wait)
| After | Show |
|---|---|
| `lochara concept` | `concepts/<tag>-sheet.png`, and a proposed parts list (id, look, bone, glow) |
| base body in place | `lochara render <c>` |
| `lochara part draw` | `parts/<id>/candidates/sheet.png` |
| `lochara part model` | `parts/<id>/preview.png` |
| `lochara build` | `lochara render <c>` (and `--focus <bone>` for the parts) plus the check line |
| `lochara export` | where it went |

Open images for the user with `open <png>` on macOS when they ask to see them; read them yourself first.

## Starting a character
`./lochara new <name> [--base <rigged.vrm|glb>]` makes `characters/<name>/`. No base yet: suggest VRoid Studio
(free; export VRM 0.x or 1.0) or a CC0 VRoid sample (https://opengameart.org/content/vroid-studio-cc0-models), and
offer `lochara concept` to design against.

Set the contract early: ask what app will load the character and which bones and morphs its code needs
(e.g. Mixamo names for Mixamo animations, `blink` for blinking), and put them in `contract`.
