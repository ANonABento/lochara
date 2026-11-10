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
    pictures  pictures are wanted (art to design from, or an open request: see `request`): run `run["deliver"]`
              with a folder of them in place of <folder>
    run       nothing to decide: run `run["next"]` (it may take minutes)
    input     something only a person can do (`say` says what), then `run["refresh"]` (`next` again)
    done      nothing left to do

Every other key in `run` is a choice too: `art` and `body` go back to those steps (`next <c> --at <stage>`), and
steps add their own (`skip`, `redraw`, `export`, `new`).

For a person in a chat, a step also carries (a chat runner shows these, and needs nothing else to know about lochara):
    title     the character's name
    labels    a short button label for keys of `run` (a key without one is shown as it is)
    progress  the stages so far and to come: [{"label": "Body", "state": "done" | "now" | "todo"}]

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
# The stages a person sees, in order (parts only for a character that has some). "done" is past all of them.
STAGES = (("art", "Art"), ("base", "Body"), ("parts", "Parts"), ("build", "Build"), ("review", "Review"))
AT = ("art", "base")  # the steps `next --at` goes back to: the choices; the rest follow from them
LABELS = {"refresh": "✅ Done, continue", "art": "← Art", "body": "← Body", "deliver": "🖼 Choose pictures",
          "redraw": "🔁 Draw new options", "export": "📦 Export", "new": "➕ New character"}


def _progress(c: Character, stage: str) -> list[dict]:
    names = [s for s in STAGES if s[0] != "parts" or c.data.get("parts")]
    ids = [s[0] for s in names]
    at = len(ids) if stage == "done" else ids.index(stage)
    return [{"label": label, "state": "done" if i < at else "now" if i == at else "todo"}
            for i, (_, label) in enumerate(names)]


def _step(c: Character, stage: str, waiting: str, say: str, show: list[Path] | None = None,
          options: list[str] | None = None, run: dict[str, list[str]] | None = None,
          labels: dict[str, str] | None = None, **extra) -> dict:
    assert waiting in WAITING, waiting
    run = dict(run or {})
    if waiting == "input":
        run.setdefault("refresh", ["next", c.id])  # look again once a person has done their part
    if stage in ("base", "parts", "build", "review", "done"):
        run.setdefault("art", ["next", c.id, "--at", "art"])
    if stage in ("parts", "build", "review", "done"):
        run.setdefault("body", ["next", c.id, "--at", "base"])
    labels = {**{k: LABELS[k] for k in run if k in LABELS}, **(labels or {})}
    out = {"character": c.id, "title": c.data.get("name") or c.id, "stage": stage, "waiting": waiting, "say": say,
           "show": [str(p) for p in show or []], "options": options or [], "run": run, "labels": labels, **extra}
    if stage != "pictures":
        out["progress"] = _progress(c, stage)
    return out


def _mtime(p: Path | None) -> float:
    return p.stat().st_mtime if p and p.exists() else 0.0


def _pictures(d: Path) -> list[Path]:
    return sorted(p for p in d.iterdir() if p.suffix.lower() in PICTURE_EXTS
                  and p.stem != "sheet" and not p.stem.endswith("-sheet")) if d.is_dir() else []


def _request_step(c: Character, req: dict) -> dict:
    return _step(c, "pictures", "pictures",
                 f"Picture request {req['id']}: draw {req['count']} picture(s) as described, then hand them over.",
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
                     show=[preview] if preview.exists() else [], labels={"refresh": "✅ Placed it, continue"})
    picture = d / "picture.png"
    if picture.exists():
        return _step(c, "parts", "run", f"Turn the chosen picture of {pid} into a 3D part (about 20 minutes).",
                     show=[picture], run={"next": ["part", "model", c.id, pid]}, labels={"next": f"▶ Make {pid} in 3D"})
    cands = _pictures(d / "candidates")
    if cands:
        sheet = d / "candidates" / "sheet.png"
        names = [p.stem for p in cands]
        return _step(c, "parts", "pick", f"Pick a picture for {pid}: {', '.join(names)}.",
                     show=[sheet] if sheet.exists() else cands, options=names,
                     run={"pick": ["part", "pick", c.id, pid, "<option>"],
                          "redraw": ["part", "draw", c.id, pid]})
    if (d / "prompt.txt").exists():
        return _step(c, "parts", "run", f"Draw some options for {pid}.", run={"next": ["part", "draw", c.id, pid]},
                     labels={"next": f"▶ Draw options for {pid}"})
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


def _art_step(c: Character, has_base: bool) -> dict:
    """Pictures to design the character from: drawn in the chat, or files of your own. Optional."""
    concepts = c.root / "concepts"
    have = _pictures(concepts)
    sheet = concepts / "c-sheet.png"
    later = have or has_base  # skipping just carries on; before any art or body it goes to the body
    return _step(c, "art", "pictures",
                 f"Art so far: {', '.join(p.name for p in have)}. Add more, or carry on." if have else
                 "Add art to design it from: pictures from this chat or your computer. Or skip and start from a "
                 "sample body.",
                 show=[sheet] if sheet.exists() else have,
                 run={"deliver": ["concept", c.id, "--from", "<folder>"],
                      "skip": ["next", c.id] if later else ["next", c.id, "--at", "base"]},
                 labels={"skip": "⏭ Continue" if later else "⏭ Skip: pick a sample body"})


def _base_step(c: Character, base: Path | None) -> dict:
    stock = bases.available()
    if stock and not c.data.get("base", {}).get("source") or stock and base and base.exists():
        return _step(c, "base", "pick", f"Pick a body to start from: {', '.join(b.name for b in stock)}.",
                     show=[b.preview for b in stock if b.preview.exists()], options=[b.name for b in stock],
                     run={"pick": ["base", c.id, "<option>"]})
    src = c.data.get("base", {}).get("source")
    return _step(c, "base", "input",
                 f"Put a rigged base model (VRM or GLB) at {base}" + (f" (from {src})." if src else "."),
                 labels={"refresh": "✅ Added it, continue"})


def next_step(c: Character, at: str | None = None) -> dict:
    """The first thing to do for this character, in pipeline order (a picture request already open comes first).

    `at` goes back to an earlier choice instead (one of AT), even one already made.
    """
    base = c.path(c.data.get("base", {}).get("file"))
    has_base = bool(base and base.exists())
    if at == "art":
        return _art_step(c, has_base)
    if at == "base":
        return _base_step(c, base)
    if at is not None:
        raise Problem(f"can't go back to {at!r}: only to {', '.join(AT)}")

    for req in handoff.open_requests(c):
        return _request_step(c, req)

    if not has_base:
        if not _pictures(c.root / "concepts"):
            return _art_step(c, False)
        return _base_step(c, base)

    for part in c.data.get("parts", []):
        step = _part_step(c, part)
        if step:
            return step

    glb = c.build / f"{c.id}.glb"
    newest_input = max(_mtime(f) for f in _build_inputs(c))
    if not glb.exists() or _mtime(glb) < newest_input:
        return _step(c, "build", "run", "Ready to build the 3D model (style, parts, optimise, check: a few minutes).",
                     run={"next": ["build", c.id]}, labels={"next": "▶ Build the 3D model"})

    render = c.root / "renders" / "latest.png"
    if _mtime(render) < _mtime(glb):
        return _step(c, "review", "run", "Built. Next, preview pictures from the front, side and back.",
                     run={"next": ["render", c.id]}, labels={"next": "▶ Make preview pictures"})

    exported = _exported(c, glb)
    if exported is None:
        return _step(c, "review", "approve", "Here's how it looks. To export it, add export targets to character.json.",
                     show=[render])
    if not exported:
        return _step(c, "review", "approve", "Here's how it looks. Export it if you're happy.",
                     show=[render], options=["export"], run={"export": ["export", c.id]})
    return _step(c, "done", "done", "Built and exported. Go back to the art or body, or change a part, to go again.",
                 show=[render])


def start(characters: list[Character]) -> dict:
    """Before any character: continue one, or start a new one."""
    ids = [c.id for c in characters]
    run = {"new": ["new", "<name>"]}
    labels = {"new": LABELS["new"]}
    if not ids:
        return {"character": None, "stage": "start", "waiting": "input", "show": [], "options": [], "run": run,
                "labels": labels, "say": "No characters yet: make a new one."}
    return {"character": None, "stage": "start", "waiting": "pick", "show": [], "options": ids,
            "run": {"pick": ["next", "<option>"], **run}, "labels": labels,
            "say": "Pick a character to keep working on, or make a new one."}


def missing(name: str) -> dict:
    """A command named a character that doesn't exist yet."""
    return {"character": None, "stage": "start", "waiting": "run", "show": [], "options": [],
            "run": {"next": ["new", name]}, "labels": {"next": f"➕ Make {name}"},
            "say": f"There's no character {name} yet. Make it first: `new {name}` (add `--from <folder>` to keep "
                   "design pictures you already have)."}


def describe(step: dict) -> str:
    """The step as text for a person."""
    lines = [f"{step['character'] or 'lochara'}: {step['stage']} ({step['waiting']})", f"  {step['say']}"]
    lines += [f"  see: {p}" for p in step["show"]]
    if "request" in step:
        lines.append(f"  prompt: {step['request']['prompt']}")
    for name, args in step["run"].items():
        lines.append(f"  {name}: lochara {' '.join(args)}")
    return "\n".join(lines)
