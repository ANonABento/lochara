"""A character is a folder with a recipe, character.json, and the files it names.

    my-character/
      character.json   the recipe: base model, style, parts, output budget, contract, exports
      concepts/        concept pictures and sheets
      parts/<id>/      prompt.txt, candidates/, picture.png (the pick), model.glb, preview.png
      assets/          base models and other third-party files (not committed)
      build/           build output (not committed)
      renders/         review renders
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .env import REPO, Problem

TEMPLATE = {
    "name": "",
    "base": {"file": "assets/base.vrm", "source": "", "licence": ""},
    "style": {"bones": "keep", "morphs": {}, "materials": []},
    "parts": [],
    "output": {"textureSize": 1024, "maxBytes": 3_000_000},
    "contract": {"bones": [], "morphs": []},
    "export": [],
}


def find(name_or_path: str) -> Path:
    """A character by path, or by name under characters/ then examples/."""
    for cand in (Path(name_or_path), REPO / "characters" / name_or_path, REPO / "examples" / name_or_path):
        if (cand / "character.json").is_file():
            return cand.resolve()
    raise Problem(f"no character {name_or_path!r} (looked for character.json at that path, in characters/ and in "
                  "examples/). `lochara new <name>` makes one.")


class Character:
    def __init__(self, root: Path):
        self.root = root
        self.file = root / "character.json"
        self.data = json.loads(self.file.read_text())
        self.id = root.name

    # -- paths
    def path(self, rel: str | None) -> Path | None:
        return None if not rel else (self.root / rel).resolve()

    @property
    def build(self) -> Path:
        return self.root / "build"

    def part(self, pid: str) -> dict | None:
        return next((p for p in self.data.get("parts", []) if p["id"] == pid), None)

    def part_dir(self, pid: str) -> Path:
        return self.root / "parts" / pid

    def save(self) -> None:
        self.file.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + "\n")


def expand(text: str, base: Path) -> Path:
    """$VAR and ${VAR:-default} from the environment; relative results are taken from the character folder."""
    def sub(m: re.Match) -> str:
        name, default = m.group(1) or m.group(3), m.group(2)
        val = os.environ.get(name)
        if val is None and default is None:
            raise Problem(f"{name} is not set (used in {text!r})")
        return val if val is not None else default
    out = re.sub(r"\$\{(\w+)(?::-([^}]*))?\}|\$(\w+)", sub, text)
    p = Path(os.path.expanduser(out))
    return p if p.is_absolute() else (base / p).resolve()


def create(root: Path, name: str, base: str | None) -> Character:
    if (root / "character.json").exists():
        raise Problem(f"{root} already has a character.json")
    for d in ("concepts", "parts", "assets", "renders"):
        (root / d).mkdir(parents=True, exist_ok=True)
    data = json.loads(json.dumps(TEMPLATE))
    data["name"] = name
    (root / "character.json").write_text(json.dumps(data, indent=2) + "\n")
    (root / ".gitignore").write_text("build/\nassets/\nparts/*/candidates/\n")
    c = Character(root)
    if base:
        set_base(c, base)
    return c


def set_base(c: Character, base: str) -> Path:
    """Copy a base model into the character's assets and point the recipe at it: a stock base by name, or a file."""
    from . import bases
    stock = bases.stock(base)
    src = stock.path if stock else Path(base).expanduser().resolve()
    if not src.is_file():
        names = ", ".join(b.name for b in bases.available()) or "none downloaded"
        raise Problem(f"no file {base} (stock bases: {names})")
    dest = c.root / "assets" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src != dest.resolve():
        dest.write_bytes(src.read_bytes())
    c.data["base"] = {"file": f"assets/{src.name}",  # a file of your own: fill in where it's from and its licence
                      "source": stock.source if stock else "", "licence": stock.licence if stock else ""}
    c.save()
    return dest
