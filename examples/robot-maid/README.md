# Robot maid (B-01, v1)

The robot maid in the prologue of [BentoSite](https://github.com/ANonABento/BentoSite), and lochara's example of a
character styled by **its own Blender script** (for the recipe-only route, see `../basic`).

She is VRoid's CC0 AvatarSample E, restyled: black hair, a black, white and orange outfit, porcelain skin, a mouthless
face with glowing orange irises, and rigid robot hardware parented to bones (ear units, a lace headdress, neck rings,
elbow, wrist and knee joints, and segmented robot hands in place of the skin hands).

v1 is a restyle of a stock body. Her successor is a fully custom design built with the generated-character pipeline
(`docs/plans/`).

```
./lochara build robot-maid
./lochara render robot-maid --focus Head --open
BENTOSITE=~/BentoSite ./lochara export robot-maid
```

It needs `assets/AvatarSample_E.vrm`, which isn't committed. Get `avatarsample_e.zip` from
https://opengameart.org/content/vroid-studio-cc0-models (CC0; VRoid Hub terms allow modification, redistribution and
commercial use, no credit needed) and unzip it into `assets/`.

## Files
| | |
|---|---|
| `style/vroid_maid.py` | The style script (`style.script`): everything below. |
| `style/vroid_model.py` | The base conversion it starts from: Mixamo bone names, porcelain skin, emissive irises, brows removed, the mouth painted out, and the blink, happy and irisOff morphs found by what they move. |
| `style/temp_maid.py` | Shared recolour and mouth helpers. |
| `parts/ear/` | A generated ear unit (FLUX.2 klein, seed 8 → Hunyuan3D-MLX → 3k triangles). It's disabled by default: to use it instead of the scripted ears, set its `enabled` to true and `style.env.MAID_EARS` to `"none"`. |
| `renders/` | `front`, `face`, `dark`; `hands` (the hand designs compared); `bases` (other CC0 VRoid samples restyled the same way); `parts-p1-ear-hy*` and `lochara-generated-ears` (the generated ear, alone and on her); `prologue-contact` (her in the prologue). |

## Switches (`style.env`)
| | |
|---|---|
| `MAID_EARS` | `scripted` (default) or `none`. |
| `MAID_HANDS` | `primitive` brings back the earlier cylinder hands instead of the sculpted ones. |
| `MAID_CLOTH` | `generic` recolours any VRoid outfit: its main colour goes black, other colours orange, light neutrals white. |

## What the site needs from her
The `contract` in `character.json` lists what BentoSite's `src/components/Prologue/engine/robot.js` uses: Mixamo
names for the spine, neck, head, eyes, arms and every finger bone, and the `blink` morph. The loader scales the model
so shoulder-to-wrist is 0.97 and the head centre sits at y = 0.59, so any model that passes the contract fits the
prologue's camera and poses.
