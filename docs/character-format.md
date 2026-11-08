# character.json

A character is a folder:

```
mychar/
  character.json      the recipe (below)
  assets/             the base model and other third-party files (gitignored)
  concepts/           `lochara concept` output: <tag>-s<seed>.png, <tag>-sheet.png, <tag>-prompt.txt
  parts/<id>/         prompt.txt, candidates/ (gitignored), picture.png, model.glb, preview.png
  style/              optional: your own Blender style script
  build/              styled.glb, <id>.raw.glb, <id>.glb (the optimised result; gitignored)
  renders/            `lochara render` contact sheets
```

`lochara new <name>` makes one in `characters/` (gitignored, so your characters stay yours). Commands take a
character's name (looked up in `characters/`, then `examples/`) or a path to its folder.

## Fields

### name, about
Free text.

### base
| Key | |
|---|---|
| `file` | The rigged base model, relative to the folder: `.vrm` (0.x or 1.0) or `.glb`. VRM-only data such as spring bones isn't carried through. |
| `source`, `licence` | Where it came from and its terms. Shown when the file is missing. |

### style
How the base is changed before parts go on. Either the generic rules:

| Key | |
|---|---|
| `bones` | `"keep"`, or a preset in `presets/bones/` that renames bones: `"mixamo"` maps VRoid's `J_Bip_*` names to Mixamo names (`Hips`, `Spine1`, `RightHandIndex1`, ...). |
| `morphs.detect` | `"vroid-eyes"`: VRoid VRM 0.x morphs come through unnamed; this finds and names `blink`, `happy` and `irisOff` by what they move. |
| `morphs.keep` | Morph names to keep; the rest are removed. Leave it out to keep all. |
| `materials` | Rules matched against material names (a fragment, first match wins): `{"match": "FaceBrow", "delete": true}`, `{"match": "HAIR", "tint": [r, g, b]}` (multiplies the texture), `{"match": "Visor", "emissive": [r, g, b], "strength": 3}`. Colours are linear 0–1. Tints are baked into a copy of the texture. Emissive only applies to lit materials: VRoid's are unlit (`KHR_materials_unlit`) and already show at full colour. |

Or your own Blender script, for anything the rules can't do:

| Key | |
|---|---|
| `script` | Run as `Blender -b --factory-startup -P <script> -- <base> <out.glb>`. It must write a GLB to `<out.glb>`. |
| `env` | Environment variables for the script, e.g. switches it reads with `os.environ`. |

### parts
A list. Each part is a rigid mesh attached to one bone; it moves with that bone and needs no skin weights.

| Key | |
|---|---|
| `id` | Folder name under `parts/`. |
| `model` | Its GLB, usually `parts/<id>/model.glb` (written by `lochara part model`). |
| `enabled` | `false` leaves it out of the build (new parts start disabled until you place them). |
| `bone` | The bone it hangs from. |
| `offset` | `[right, up, forward]` in metres from the bone's head, in the character's own directions (worked out from its hands and feet, so it doesn't matter which way the model faces in its file). |
| `size` | The part's longest side in metres. |
| `rotation` | `[pitch, yaw, roll]` degrees about the character's right, up and forward. At `[0, 0, 0]` the part's front (the "Front" of its preview) faces the character's forward; yaw `-90` turns it to face the character's right. |
| `mirror` | `true` adds a mirrored copy on the other side (on the mirrored bone: Left↔Right, `_L`↔`_R`, `.L`↔`.R`). |
| `glow` | `{"hue": [lo, hi], "strength": 3}`: generated textures paint lights on; this makes the pixels in that hue range (degrees, saturated and bright) emissive. Orange is about `[10, 45]`, cyan `[170, 200]`. |
| `seed`, `engine`, `triangles`, `notes` | Recorded by the CLI for reproducibility. |

The built GLB names each part's node `part_<id>` (and `part_<id>_mirror`), so your app can find it.

### output
| Key | |
|---|---|
| `textureSize` | Longest texture side after optimisation (gltf-transform, WebP, meshopt). |
| `maxBytes` | Size budget; the check fails above it. |

### contract
What your app needs from the model. `lochara build` and `lochara check` fail when the build doesn't have it, and
`lochara export` refuses to export (unless `--force`).

| Key | |
|---|---|
| `bones` | Bone names that must exist. |
| `morphs` | Morph target names that must exist. |

### export
`[{"to": "path"}]`. `$VAR` and `${VAR:-default}` come from the environment; relative paths start at the character
folder. `lochara export <name> --to <path>` overrides them.
