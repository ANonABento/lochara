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

from lochara import bases, handoff, state
from lochara.character import Character, create, set_base
from lochara.env import Problem

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


@pytest.fixture
def stock(tmp_path: Path, monkeypatch) -> Path:
    """One downloaded stock base (sample-e), in a throwaway vendor folder."""
    folder = tmp_path / "vroid"
    monkeypatch.setattr(bases, "FOLDER", folder)
    (folder / "avatarsample_e").mkdir(parents=True)
    (folder / "avatarsample_e" / "AvatarSample_E.vrm").write_bytes(b"glTF")
    png(folder / "avatarsample_e_full.png")
    return folder


def test_no_base(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(bases, "FOLDER", tmp_path / "nothing")
    c = create(tmp_path / "bare", "Bare", None)
    s = step(c)
    assert (s["stage"], s["waiting"]) == ("base", "input")


def test_pick_a_stock_base(tmp_path: Path, stock: Path):
    c = create(tmp_path / "bare", "Bare", None)
    s = step(c)
    assert (s["stage"], s["waiting"], s["options"]) == ("base", "pick", ["sample-e"])
    assert s["show"] == [str(stock / "avatarsample_e_full.png")]
    assert s["run"]["pick"] == ["base", "bare", "<option>"]

    set_base(Character(c.root), "sample-e")
    c = Character(c.root)
    assert c.data["base"]["licence"] == "CC0" and (c.root / "assets" / "AvatarSample_E.vrm").exists()
    assert step(c)["stage"] == "build"


def test_open_request_comes_before_base(tmp_path: Path, stock: Path):
    c = create(tmp_path / "bare", "Bare", None)
    req = handoff.create(c, "concept", "a design", c.root / "concepts", "c-h", 2)
    s = step(c)
    assert (s["waiting"], s["request"]["id"]) == ("pictures", req["id"])  # the concept in flight, not the base
    assert s["run"]["deliver"] == ["deliver", "bare", req["id"], "--from", "<folder>"]


def test_unknown_base(tmp_path: Path, stock: Path):
    c = create(tmp_path / "bare", "Bare", None)
    with pytest.raises(Problem, match="stock bases: sample-e"):
        set_base(c, "sample-z")


def test_start():
    assert state.start([])["waiting"] == "input"
    s = state.start([Character(REPO / "examples" / "basic")])
    assert (s["waiting"], s["options"], s["run"]["pick"]) == ("pick", ["basic"], ["next", "<option>"])


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


def test_missing_character_points_to_new(tmp_path: Path):
    """What Waymond did: delivered drawn designs for a character it hadn't made yet."""
    made = tmp_path / "made"
    png(made / "design_1.png")
    r = lochara("deliver", "zz-nobody", "c-h", "--from", str(made), "--json")
    out = json.loads(r.stdout)
    assert out["ok"] is False and out["problem"].startswith("no character")
    assert out["next"]["run"]["next"] == ["new", "zz-nobody"]
    assert "--from" in out["next"]["say"]


def test_new_with_designs(tmp_path: Path):
    made = tmp_path / "made"
    png(made / "design_1.png")
    png(made / "design_2.png")
    (made / "meta.json").write_text("{}")
    root = tmp_path / "mika"
    r = lochara("new", "mika", "--path", str(root), "--from", str(made), "--prompt", "a maid", "--json")
    out = json.loads(r.stdout)
    assert out["ok"], r.stderr
    assert sorted(Path(p).name for p in out["wrote"][1:]) == ["c-d1.png", "c-d2.png"]
    assert out["show"] == [str(root / "concepts" / "c-sheet.png")]
    assert (root / "concepts" / "c-prompt.txt").read_text() == "a maid\n"
    assert out["next"]["stage"] == "base"

    png(made / "design_3.png")  # more designs later number on
    r = lochara("concept", str(root), "--from", str(made), "--json")
    out = json.loads(r.stdout)
    assert out["ok"], r.stderr
    assert [Path(p).name for p in out["wrote"]] == ["c-d3.png", "c-d4.png", "c-d5.png"]


def test_new_with_no_pictures_makes_nothing(tmp_path: Path):
    (tmp_path / "empty").mkdir()
    r = lochara("new", "zz", "--path", str(tmp_path / "zz"), "--from", str(tmp_path / "empty"), "--json")
    assert json.loads(r.stdout)["problem"].startswith("no pictures")
    assert not (tmp_path / "zz").exists()
