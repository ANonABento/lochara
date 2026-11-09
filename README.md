# lochara

**Local character creation.** Make anime-style 3D avatars (toon-shaded, VTuber and VRChat style) on your own
computer, for the web, VTubing and games. Today: a rigged base body restyled by a recipe, with rigid parts generated
from a prompt and attached to bones, built into one GLB you can drop into three.js, Godot, Unity or Blender. Next:
characters from your own design, with hair, outfit and accessories generated from your pictures, exported as GLB,
VRM and VRChat-ready FBX ([roadmap](docs/plans/)). No cloud services or credits, and no uploading your art anywhere.

lochara is a CLI plus agent skills. The agent (Claude Code, Codex, ...) does the work and stops at each checkpoint
for you to look and choose. Its method comes from [Charakuru](https://github.com/nanocle/Charakuru): build the
character in parts, and take skin weights from a body that is already rigged rather than guessing them. Charakuru
does this with a cloud service (Tripo); lochara uses only local tools.

```
 concept  ──▶  base body  ──▶  parts  ──────────▶  build  ──▶  check  ──▶  export
 FLUX          VRoid Studio     FLUX → AssetFurnace   Blender     contract     your app
 you pick      you design       you pick, per part    you review  automatic
```

| Piece | From | Why |
|---|---|---|
| Body, face, hair, outfit, rig, expressions | **a rigged base** (VRoid Studio, or any rigged VRM/GLB) | Clean topology and real skin weights. Generated bodies come out fused and tear when they move. |
| Rigid parts: armour, ears, headgear, props | **generated**: FLUX draws, AssetFurnace builds the 3D | Rigid, so each hangs off one bone and needs no weights: exactly what generation is good at. |
| Style: colours, glow, removed bits | a recipe (`character.json`), or your own Blender script | Small fixes are numbers, not code. |

## Status
Early (0.1). Works on an Apple Silicon Mac; the picture and 3D steps depend on Apple-Silicon or NVIDIA builds of the
models. Tested end to end with the example character, the robot maid in `examples/robot-maid`.

Next: the design route (hair, outfit and accessories generated from your pictures, on a template body and face that
bring the rig and expressions) and export targets for web, VTubing (VRM) and VRChat. See [docs/plans/](docs/plans/).

## Quick start
```sh
git clone https://github.com/ANonABento/lochara && cd lochara
./lochara doctor                         # what's installed, what's missing (needs uv: https://docs.astral.sh/uv/)
./lochara setup assetfurnace             # picture -> 3D studio (code only, ~1-2 GB of Python packages)
./lochara engines                        # 3D engines, their sizes and licences
./lochara setup engine hunyuan_xiong --yes   # 13.9 GB of weights; check the licence first

./lochara new mychar --base ~/Downloads/MyAvatar.vrm     # a rigged VRM/GLB, e.g. exported from VRoid Studio,
                                                          # or a stock base: --base sample-e (CC0 VRoid samples;
                                                          # unzip them from opengameart.org/content/vroid-studio-cc0-models
                                                          # into vendor/vroid/<zip name>/)
./lochara concept mychar "a knight with a fox mask"      # optional: concepts to design the base against
./lochara part draw mychar visor "a sleek black visor with a cyan light strip"
./lochara part pick mychar visor 377                      # the seed you liked from the sheet
./lochara part model mychar visor                         # about 20 min; writes parts/visor/model.glb + preview
# set the part's bone, offset and size in characters/mychar/character.json, then:
./lochara build mychar
./lochara render mychar --focus Head --open
./lochara export mychar --to ~/my-game/assets/mychar.glb
```

Lost your place? `./lochara next mychar` says what's next (`./lochara next` alone lists your characters) and the command for it (`--json` on any command gives
one JSON result, for scripts and chat bots).

Pictures from another tool (a hosted image model, an agent, your own art app): add `--via handoff` to `concept` or
`part draw`, then `./lochara requests` and `./lochara deliver mychar <request-id> --from <folder>`
([docs/agents.md](docs/agents.md)).

## What you need
| Tool | Used for | |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | runs the CLI | required |
| [Blender](https://www.blender.org/) 4.2+ (tested on 5.2) | build, render | required |
| Node.js 18+ (`npx`) | optimising GLBs with gltf-transform | recommended |
| [mflux](https://github.com/filipstrand/mflux) | FLUX.2 klein pictures (Apache-2.0), Apple Silicon | for concepts and parts |
| [AssetFurnace](https://github.com/Bingeljell/image-to-3dlab) (Apache-2.0) | picture → 3D, cleanup | for parts; `lochara setup assetfurnace` |
| [VRoid Studio](https://vroid.com/en/studio) | designing a base body | optional; any rigged VRM/GLB works |

## The recipe
Each character is a folder with a `character.json`: the base model, how to style it, its parts, a size budget, a
**contract** (bones and morphs your app needs; the check fails without them) and where to export.
See [docs/character-format.md](docs/character-format.md).

```json
{
  "name": "My character",
  "base": {"file": "assets/base.vrm", "licence": "mine"},
  "style": {"bones": "mixamo", "morphs": {"detect": "vroid-eyes", "keep": ["blink", "happy"]},
            "materials": [{"match": "FaceBrow", "delete": true}, {"match": "HAIR", "tint": [0.35, 0.5, 1]}]},
  "parts": [{"id": "visor", "model": "parts/visor/model.glb", "bone": "Head",
             "offset": [0, 0.05, 0.09], "size": 0.2, "glow": {"hue": [170, 200], "strength": 4}}],
  "output": {"textureSize": 1024, "maxBytes": 2000000},
  "contract": {"bones": ["Head", "RightHand"], "morphs": ["blink"]},
  "export": [{"to": "$GAME/assets/mychar.glb"}]
}
```

## Docs
- [docs/workflow.md](docs/workflow.md): the end-to-end workflow, with each checkpoint.
- [docs/character-format.md](docs/character-format.md): `character.json` reference.
- [docs/agents.md](docs/agents.md): driving lochara from an agent or a chat app, and pictures from other tools (handoff).
- [docs/plans/](docs/plans/): the roadmap and setup list, the design route, export targets (web, VTuber, VRChat), the robot maid v2.
- [docs/research.md](docs/research.md): the tools we evaluated (Charakuru, Tripo, TRELLIS.2, Hunyuan3D, Pixal3D,
  StdGEN, UniRig ...) and why lochara is built this way.
- [AGENTS.md](AGENTS.md): instructions for coding agents; the Claude Code skills are in `.claude/skills/`.
- [third_party/assetfurnace/](third_party/assetfurnace/): the AssetFurnace version we pin and the fix we apply.
- [examples/basic/](examples/basic/): a recipe-only character (no custom code).
- [examples/robot-maid/](examples/robot-maid/): the worked example, the robot maid for a portfolio site's intro, with
  its own style script.

## Licences
lochara is MIT. The tools it drives have their own licences, and so do the models: check each engine's licence
(`lochara engines`) and your base model's terms before shipping a character. The example's base is VRoid's CC0
AvatarSample E.
