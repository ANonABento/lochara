"""Where a character stands, and what happens next: read from its folder, never stored.

Any driver uses this: a person (`lochara next`), an agent that read AGENTS.md, or a chat runner that only parses
JSON (`lochara next --json`). Each stage of the pipeline adds its rule here, in the order the stages run; the first
rule with something to do wins.

    {"character": "aiko", "stage": "parts", "waiting": "pick",
     "say": "Pick a picture for visor: s12, s40, h1.",
     "show": ["/.../parts/visor/candidates/sheet.png"],
     "options": ["s12", "s40", "h1"],
     "run": {"pick": ["part", "pick", "aiko", "visor", "<option>"]}}

`waiting` is one of:
    pick      choose one of `options`, then run `run["pick"]` with it in place of <option>
    approve   look at `show`; run what `run` offers, or change something first
    pictures  a picture request is open: draw them (see `request`), then `lochara deliver`
    run       nothing to decide: run `run["next"]` (it may take minutes)
    input     something only a person can do (`say` says what)
    done      nothing left to do

Commands in `run` are argument lists for the `lochara` command, never shell strings. `<option>` is one of `options`;
`<name>` is a new character's short id (lowercase letters, digits, -), chosen by whoever asked for it.

Without a character, `start()` is the step before any: pick a character to continue, or make a new one.
"""
from __future__ import annotations

from pathlib import Path

from . import bases, handoff
from .character import Character, expand
from .env import Problem

PICTURE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
WAITING = ("pick", "approve", "pictures", "run", "input", "done")


def _step(c: Character, stage: str, waiting: str, say: str, show: list[Path] | None = None,
          options: list[str] | None = None, run: dict[str, list[str]] | None = None, **extra) -> dict:
    assert waiting in WAITING, waiting
    return {"character": c.id, "stage": stage, "waiting": waiting, "say": say,
            "show": [str(p) for p in show or []], "options": options or [], "run": run or {}, **extra}


def _mtime(p: Path | None) -> float:
    return p.stat().st_mtime if p and p.exists() else 0.0


def _pictures(d: Path) -> list[Path]:
    return sorted(p for p in d.iterdir() if p.suffix.lower() in PICTURE_EXTS and p.stem != "sheet") if d.is_dir() else []


def _request_step(c: Character, req: dict) -> dict:
    return _step(c, "pictures", "pictures",
                 f"Picture request {req['id']} is open: draw {req['count']} picture(s) as it describes, then deliver them.",
                 show=[Path(r) for r in req["references"]],
                 run={"deliver": ["deliver", c.id, req["id"], "--from", "<folder>"]},
                 request={k: req[k] for k in ("id", "kind", "prompt", "count", "size", "references", "notes")})


def _part_step(c: Character, part: dict) -> dict | None:
    pid = part["id"]
    d = c.part_dir(pid)
    model = c.path(part.get("model"))
    if model and model.exists():
        if part.get("bone"):
            return None  # placed (and on, or switched off on purpose)
        preview = d / "preview.png"
        return _step(c, "parts", "input",
                     f"Place {pid}: set its bone, offset and size in character.json and set \"enabled\": true.",
                     show=[preview] if preview.exists() else [])
    picture = d / "picture.png"
    if picture.exists():
        return _step(c, "parts", "run", f"Turn the picked picture of {pid} into a 3D model (about 20 minutes).",
                     show=[picture], run={"next": ["part", "model", c.id, pid]})
    cands = _pictures(d / "candidates")
    if cands:
        sheet = d / "candidates" / "sheet.png"
        names = [p.stem for p in cands]
        return _step(c, "parts", "pick", f"Pick a picture for {pid}: {', '.join(names)}.",
                     show=[sheet] if sheet.exists() else cands, options=names,
                     run={"pick": ["part", "pick", c.id, pid, "<option>"],
                          "redraw": ["part", "draw", c.id, pid]})
    if (d / "prompt.txt").exists():
        return _step(c, "parts", "run", f"Draw candidate pictures for {pid}.", run={"next": ["part", "draw", c.id, pid]})
    return None  # a part with nothing yet (a scripted one, or not started)


def _build_inputs(c: Character) -> list[Path]:
    data = c.data
    files = [c.file, c.path(data.get("base", {}).get("file"))]
    script = data.get("style", {}).get("script")
    if script:
        files.append(c.path(script))
    files += [c.path(p.get("model")) for p in data.get("parts", []) if p.get("enabled", True) and p.get("model")]
    return [f for f in files if f]


def _exported(c: Character, glb: Path) -> bool | None:
    """True when every export target is at least as new as the build; None when there are no targets."""
    targets = [t["to"] for t in c.data.get("export", [])]
    if not targets:
        return None
    try:
        return all(_mtime(expand(t, c.root)) >= _mtime(glb) for t in targets)
    except Problem:
        return False


def next_step(c: Character) -> dict:
    """The first thing to do for this character, in pipeline order (a picture request already open comes first)."""
    for req in handoff.open_requests(c):
        return _request_step(c, req)

    base = c.path(c.data.get("base", {}).get("file"))
    if not base or not base.exists():
        stock = bases.available()
        if stock and not c.data.get("base", {}).get("source"):
            return _step(c, "base", "pick", f"Pick a base body to start from: {', '.join(b.name for b in stock)}.",
                         show=[b.preview for b in stock if b.preview.exists()], options=[b.name for b in stock],
                         run={"pick": ["base", c.id, "<option>"]})
        src = c.data.get("base", {}).get("source")
        return _step(c, "base", "input",
                     f"Put a rigged base model (VRM or GLB) at {base}" + (f" (from {src})." if src else "."))

    for part in c.data.get("parts", []):
        step = _part_step(c, part)
        if step:
            return step

    glb = c.build / f"{c.id}.glb"
    newest_input = max(_mtime(f) for f in _build_inputs(c))
    if not glb.exists() or _mtime(glb) < newest_input:
        return _step(c, "build", "run", "Build the character (style, parts, optimise, check).",
                     run={"next": ["build", c.id]})

    render = c.root / "renders" / "latest.png"
    if _mtime(render) < _mtime(glb):
        return _step(c, "review", "run", "Render the build from the front, three-quarter and back.",
                     run={"next": ["render", c.id]})

    exported = _exported(c, glb)
    if exported is None:
        return _step(c, "review", "approve", "Check the render. Add export targets to character.json to ship it.",
                     show=[render])
    if not exported:
        return _step(c, "review", "approve", "Check the render; export it if it looks right.",
                     show=[render], options=["export"], run={"export": ["export", c.id]})
    return _step(c, "done", "done", "Built, checked and exported. Change the recipe or a part to go again.",
                 show=[render])


def start(characters: list[Character]) -> dict:
    """Before any character: continue one, or start a new one."""
    ids = [c.id for c in characters]
    run = {"new": ["new", "<name>"]}
    if not ids:
        return {"character": None, "stage": "start", "waiting": "input", "show": [], "options": [], "run": run,
                "say": "No characters yet. Start one: choose a short name for it and run `new <name>`."}
    return {"character": None, "stage": "start", "waiting": "pick", "show": [], "options": ids,
            "run": {"pick": ["next", "<option>"], **run},
            "say": f"Characters: {', '.join(ids)}. Continue one, or start a new one with `new <name>`."}


def describe(step: dict) -> str:
    """The step as text for a person."""
    lines = [f"{step['character'] or 'lochara'}: {step['stage']} ({step['waiting']})", f"  {step['say']}"]
    lines += [f"  see: {p}" for p in step["show"]]
    if "request" in step:
        lines.append(f"  prompt: {step['request']['prompt']}")
    for name, args in step["run"].items():
        lines.append(f"  {name}: lochara {' '.join(args)}")
    return "\n".join(lines)
