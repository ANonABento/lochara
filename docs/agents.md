# Driving lochara from an agent or a chat

lochara is a CLI plus instructions for agents (`AGENTS.md`, and the Claude Code skills in `.claude/skills/`). Any
coding agent that can run commands on the machine with the GPU can drive it: Claude Code, Codex, or a chat bot
built on one. The agent does the work; you make the choices at each checkpoint.

## Where a character stands: `lochara next`
`lochara next <character>` reads the character's folder and says the stage, what it's waiting for, what to show and
the command to run. With `--json` it's data, for a script or a chat runner:

```json
{"ok": true, "command": "next",
 "next": {"character": "aiko", "stage": "parts", "waiting": "pick",
          "say": "Pick a picture for visor: h1, h2, s12.",
          "show": ["/…/aiko/parts/visor/candidates/sheet.png"], "options": ["h1", "h2", "s12"],
          "run": {"pick": ["part", "pick", "aiko", "visor", "<option>"], "redraw": ["part", "draw", "aiko", "visor"]}}}
```

| `waiting` | What the driver does |
|---|---|
| `pick` | Show `show`, ask the user, run `run.pick` with their choice in place of `<option>` |
| `approve` | Show `show`; run what `run` offers when the user agrees, or change something first |
| `pictures` | A picture request is open (`request`: prompt, references, count, size): make them, `deliver` |
| `run` | Nothing to decide: run `run.next` (3D takes about 20 min) |
| `input` | Something only a person can do: tell them `say` |
| `done` | Nothing left |

Every command takes `--json`: one JSON result on stdout (`ok`, what it showed or wrote, and `next`, the step after
it), with its progress on stderr; a failure is `{"ok": false, "problem": ...}` and exit 1. Commands in `run` are
argument lists for `lochara`, never shell strings.

## In a terminal
Open the repo in your agent and ask for what you want ("make a character from this design", "add ear units to
robot-maid"). The agent reads `AGENTS.md` and the skills and stops at every checkpoint.

## From a chat app
A chat bot that runs a coding agent on the same machine works the same way, with two adjustments:
- **Start the chat in the lochara folder**, so the agent loads `AGENTS.md` and the skills. For
  [Choomfie](https://github.com/ANonABento/choomfie) (a Discord agent on Claude Code): `/clear cwd:<path to lochara>`
  starts a chat there.
- **Checkpoints become messages:** the agent attaches the sheet, preview or render to its reply (for Choomfie, the
  `reply` tool's `files`), and you answer with your pick ("h2", "seed 8").

To run `lochara` from any folder, link it onto your PATH: `ln -s "$PWD/lochara" ~/.local/bin/lochara`.

## Pictures from somewhere else (handoff)
lochara draws pictures locally (FLUX.2 klein, Qwen-Image-Edit). When a better model is available elsewhere, such as a
hosted image model your agent can reach or an app you use yourself, hand the drawing off:

```sh
lochara concept mychar "a robot maid, black and white" --via handoff --ref design.png -n 4
lochara part draw mychar visor "a glowing visor" --via handoff --ref design.png -n 4
lochara requests                       # what's open: prompt, references, size, how to deliver
lochara deliver mychar <request-id> a.png b.png c.png d.png   # or --from <folder> for every picture in it
lochara part pick mychar visor h2      # delivered pictures are named h1, h2, ...
```

A request is a folder `requests/<id>/request.json` in the character: the prompt, the reference pictures (absolute
paths), how many, the size, and where they go. Whoever fills it makes the pictures any way they like and runs
`lochara deliver`. Delivered pictures land where local ones would, so sheets, picking and every later step are
unchanged. lochara holds no API keys and calls no services.

**Filling a request from an agent:** read `lochara requests`, send the prompt and the references to the image
model, save what comes back, `lochara deliver`. With Choomfie and Waymond (whose image generation is a hosted
model):

```
ask_brain(brain="waymond", chat_id=<this chat>,
          prompt=<the request's prompt, plus: "N separate images, one character per image, plain background">,
          files=<the request's references>, save_to=<a temp folder>)
→ lochara deliver <character> <request-id> --from <the save_to folder>
→ attach the sheet to the reply; the user picks
```

Hosted models upload your design to that service and can't be re-run exactly (no seeds). Local drawing stays the
default; the recipe records which way each picture was made.
