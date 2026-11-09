# Agent guide: lochara

lochara makes rigged 3D characters locally: a rigged base body + rigid generated parts attached to bones, built into
one GLB. Read README.md for the idea and docs/workflow.md for the stages. The CLI is `./lochara` (run `./lochara
doctor` first).

## Rules
- **Start from `lochara next <character>`** (no character: it lists them, or says how to start one). It reads the folder and says the stage, what it's waiting for (`pick`,
  `approve`, `pictures`, `run`, `input`, `done`), what to show and the command to run. Don't guess the stage. Every
  command takes `--json` (one result on stdout, with the next step; progress on stderr) for scripts and chat runners.
- **Stop at every checkpoint.** Concept picks, base body, each part's picture, each part's 3D result, the built
  character: show the user the image (sheet, preview or render) and wait. Never choose for them, never continue past
  a checkpoint on your own.
- **Look before you show.** Read every sheet, preview and render yourself first; fix what's obviously wrong
  (a part inside the head, facing the wrong way, wrong size) before presenting it.
- **Downloads ask first.** Engine weights are several GB with their own licences: say the size and licence and get
  a yes before `lochara setup engine <id> --yes`.
- **Check what exists first.** Before writing a step or planning a download, look for something that already does
  it: ComfyUI's workflow templates (they list their model files and URLs), pre-quantized models (`mflux-community`,
  `Comfy-Org` repackaged), popular LoRAs (Hugging Face sorted by downloads, Civitai), AssetFurnace's modules. Use
  them over new code, and say what you found.
- **In a chat app** (Discord through Choomfie, ...), the user can't see your terminal: attach every checkpoint's image
  (sheet, preview, render) to your reply, and keep the text short. See `docs/agents.md`.
- **Pictures from elsewhere:** when the user wants a hosted image model, use `--via handoff` and fill the request
  with `lochara deliver` (`--from <folder>` delivers every picture in it; `docs/agents.md`). Say that the design is uploaded to that service.
- **Fixes are numbers.** Placement, size, glow and style go in `character.json`. Change code only for things a
  recipe can't express, and then prefer a character's own `style.script` over changing lochara.
- **Never commit** `vendor/`, `assets/`, `build/` or third-party models. Note the base model's licence in the recipe.
- Long runs (3D: about 20 min) go in the background; report progress briefly, and treat a run that stops moving as
  failed (see `.claude/skills/lochara-part`).

## Layout
| Path | |
|---|---|
| `src/lochara/` | the CLI (Python, run with uv) |
| `blender/lochara_blender.py` | Blender stages: style, parts, render (headless) |
| `presets/bones/` | bone-name maps (VRoid → Mixamo) |
| `third_party/assetfurnace/` | the pinned AssetFurnace release and our patch |
| `examples/robot-maid/` | the worked example, with a custom style script |
| `docs/plans/` | the roadmap and plans: read before working on a planned feature, and update its status |
| `characters/` | users' characters (gitignored) |
| `vendor/` | tools and weights (gitignored) |

## Skills
`.claude/skills/lochara` (start here), `lochara-part`, `lochara-build`. Other agents: read those SKILL.md files as
plain instructions.

## Checks
`uv run pytest` (state rules and the `--json` contract); `./lochara doctor`; after changing the Blender stages, `./lochara build robot-maid && ./lochara check robot-maid`
(needs the example's CC0 base, see examples/robot-maid/README.md) and look at `./lochara render robot-maid`.
