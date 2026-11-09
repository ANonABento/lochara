"""`lochara next`: each rule, in pipeline order, on a throwaway character; and the --json contract."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from PIL import Image

from lochara import handoff, state
from lochara.character import Character, create

REPO = Path(__file__).resolve().parents[1]


def png(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), "white").save(path)
    return path


def touch_later(path: Path) -> None:
    """Make `path` newer than everything written so far (mtime resolution varies by filesystem)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(path.read_bytes() if path.exists() else b"x")
    later = time.time() + 5
    os.utime(path, (later, later))


@pytest.fixture
def char(tmp_path: Path) -> Character:
    base = tmp_path / "src" / "base.vrm"
    base.parent.mkdir()
    base.write_bytes(b"glTF")
    return create(tmp_path / "aiko", "Aiko", str(base))


def add_part(c: Character, pid: str, **fields) -> dict:
    part = {"id": pid, "bone": "", "enabled": False, **fields}
    c.data["parts"].append(part)
    c.save()
    return part


def step(c: Character) -> dict:
    return state.next_step(Character(c.root))


def test_no_base(tmp_path: Path):
    c = create(tmp_path / "bare", "Bare", None)
    s = step(c)
    assert (s["stage"], s["waiting"]) == ("base", "input")


def test_part_rules_in_order(char: Character):
    d = char.part_dir("visor")
    add_part(char, "visor")
    assert step(char)["stage"] == "build"  # a part with nothing yet doesn't block

    (d).mkdir(parents=True)
    (d / "prompt.txt").write_text("a visor\n")
    s = step(char)
    assert (s["waiting"], s["run"]["next"]) == ("run", ["part", "draw", "aiko", "visor"])

    png(d / "candidates" / "s12.png")
    png(d / "candidates" / "h1.jpg")
    png(d / "candidates" / "sheet.png")
    s = step(char)
    assert s["waiting"] == "pick"
    assert s["options"] == ["h1", "s12"]  # the sheet isn't an option
    assert s["show"] == [str(d / "candidates" / "sheet.png")]
    assert s["run"]["pick"] == ["part", "pick", "aiko", "visor", "<option>"]

    png(d / "picture.png")
    s = step(char)
    assert (s["waiting"], s["run"]["next"]) == ("run", ["part", "model", "aiko", "visor"])

    (d / "model.glb").write_bytes(b"glTF")
    char.data["parts"][0]["model"] = "parts/visor/model.glb"
    char.save()
    assert step(char)["waiting"] == "input"  # placed by a person

    char.data["parts"][0]["bone"] = "Head"  # placed, still off: switched off on purpose
    char.save()
    assert step(char)["stage"] == "build"


def test_open_request_comes_before_parts(char: Character):
    add_part(char, "visor")
    ref = png(char.root / "design" / "front.png")
    req = handoff.create(char, "part-visor", "a visor", char.part_dir("visor") / "candidates", "h", 2, [ref])
    s = step(char)
    assert s["waiting"] == "pictures"
    assert s["request"]["id"] == req["id"]
    assert s["show"] == [str(ref.resolve())]
    assert s["run"]["deliver"] == ["deliver", "aiko", req["id"], "--from", "<folder>"]


def test_build_render_export_done(char: Character):
    assert step(char)["stage"] == "build"
    glb = char.build / "aiko.glb"
    char.build.mkdir()
    touch_later(glb)
    s = step(char)
    assert (s["stage"], s["run"]["next"]) == ("review", ["render", "aiko"])

    render = char.root / "renders" / "latest.png"
    png(render)
    later = time.time() + 10
    os.utime(render, (later, later))
    s = step(char)
    assert (s["waiting"], s["options"]) == ("approve", [])  # no export targets yet

    char.data["export"] = [{"to": "out/aiko.glb"}]
    char.save()
    touch_later(glb)  # the recipe changed, so the build is stale again
    os.utime(glb, (later + 5, later + 5))
    os.utime(render, (later + 6, later + 6))
    s = step(char)
    assert (s["waiting"], s["run"]["export"]) == ("approve", ["export", "aiko"])

    out = char.root / "out" / "aiko.glb"
    out.parent.mkdir()
    out.write_bytes(b"glTF")
    os.utime(out, (later + 7, later + 7))
    assert step(char)["waiting"] == "done"


def lochara(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "lochara", *args], capture_output=True, text=True, cwd=REPO)


def test_json_result_and_next(char: Character):
    r = lochara("next", str(char.root), "--json")
    assert r.returncode == 0
    out = json.loads(r.stdout)  # stdout is only the JSON
    assert out["ok"] and out["next"]["stage"] == "build"
    assert "build" in r.stderr  # the text went to stderr


def test_json_problem(tmp_path: Path):
    r = lochara("next", str(tmp_path / "nobody"), "--json")
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["ok"] is False and out["problem"].startswith("no character")


def test_deliver_from_folder(char: Character, tmp_path: Path):
    add_part(char, "visor")
    req = handoff.create(char, "part-visor", "a visor", char.part_dir("visor") / "candidates", "h", 2)
    made = tmp_path / "made"
    png(made / "b.png")
    png(made / "a.jpg")
    (made / "notes.txt").write_text("not a picture")
    r = lochara("deliver", str(char.root), req["id"], "--from", str(made), "--json")
    out = json.loads(r.stdout)
    assert out["ok"], r.stderr
    assert [Path(p).name for p in out["wrote"]] == ["h1.jpg", "h2.png"]
    assert out["next"]["waiting"] == "pick"  # every --json result carries the next step
    assert out["next"]["options"] == ["h1", "h2"]
