"""Pictures made somewhere else: a request lochara writes, filled by whoever has the better picture model.

lochara draws locally by default. With `--via handoff` it writes a request instead: what to draw, the reference
pictures, how many, and where they go. Anything can fill it: an agent with a hosted image model (Choomfie asking
Waymond, Codex, ...), another machine, or a person with any app. Delivering puts the files where the local drawer
would have, so picking, sheets and every later step work the same. lochara holds no keys and knows no services.

    <character>/requests/<id>/request.json   the request (also printed as text for a person or an agent)
    lochara requests [<character>]           what's open
    lochara deliver <character> <id> <files> fill it
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from .character import Character
from .env import Problem


def _dir(c: Character) -> Path:
    return c.root / "requests"


def create(c: Character, kind: str, prompt: str, deliver_to: Path, prefix: str, count: int,
           refs: list[Path] | None = None, size: tuple[int, int] = (1024, 1024), notes: str = "") -> dict:
    for r in refs or []:
        if not r.exists():
            raise Problem(f"reference picture not found: {r}")
    rid = time.strftime("%Y%m%d-%H%M%S") + f"-{kind}"
    req = {
        "id": rid,
        "kind": kind,
        "status": "open",
        "prompt": prompt,
        "count": count,
        "size": list(size),
        "references": [str(r.resolve()) for r in refs or []],
        "deliver_to": str(deliver_to.resolve()),
        "prefix": prefix,
        "notes": notes,
        "deliver": f"lochara deliver {c.id} {rid} <file> ...",
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    d = _dir(c) / rid
    d.mkdir(parents=True, exist_ok=True)
    (d / "request.json").write_text(json.dumps(req, indent=2) + "\n")
    return req


def describe(req: dict) -> str:
    w, h = req["size"]
    lines = [f"request {req['id']} ({req['kind']}, {req['status']})",
             f"  draw {req['count']} picture(s), about {w}x{h}, each a separate image:",
             f"  {req['prompt']}"]
    if req["references"]:
        lines.append("  references (the design is the authority):")
        lines += [f"    {r}" for r in req["references"]]
    if req["notes"]:
        lines.append(f"  notes: {req['notes']}")
    lines.append(f"  then: {req['deliver']}")
    return "\n".join(lines)


def load(c: Character, rid: str) -> dict:
    f = _dir(c) / rid / "request.json"
    if not f.exists():
        raise Problem(f"no request {rid} for {c.id} (lochara requests {c.id})")
    return json.loads(f.read_text())


def open_requests(c: Character) -> list[dict]:
    out = []
    for f in sorted(_dir(c).glob("*/request.json")):
        req = json.loads(f.read_text())
        if req.get("status") == "open":
            out.append(req)
    return out


def deliver(c: Character, rid: str, files: list[Path]) -> list[Path]:
    req = load(c, rid)
    for f in files:
        if not f.exists():
            raise Problem(f"not found: {f}")
    dest = Path(req["deliver_to"])
    dest.mkdir(parents=True, exist_ok=True)
    prefix = req["prefix"]
    taken = {p.stem for p in dest.glob(f"{prefix}*")}
    placed = []
    n = 1
    for f in files:
        while f"{prefix}{n}" in taken:
            n += 1
        out = dest / f"{prefix}{n}{f.suffix.lower() or '.png'}"
        shutil.copy(f, out)
        taken.add(out.stem)
        placed.append(out)
    req["status"] = "delivered"
    req["delivered"] = [str(p) for p in placed]
    req["delivered_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (_dir(c) / rid / "request.json").write_text(json.dumps(req, indent=2) + "\n")
    return placed
