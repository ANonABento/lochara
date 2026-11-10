"""lochara: make a rigged 3D character on your own machine.

A character = a rigged base body (VRoid Studio, or any rigged VRM/GLB) + rigid parts generated from text
(FLUX -> AssetFurnace), each attached to one bone, built into one web-ready GLB.

`lochara next <character>` says what to do next. Every command takes --json: one JSON result on stdout (what it
showed, and the next step), its progress on stderr.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import assetfurnace as af
from PIL import Image

from . import glb, handoff, pictures, state
from .character import Character, create, expand, find, set_base
from .env import REPO, Problem, blender, mflux, npx, run_blender, vroid_studio

DEFAULT_ENGINE = "hunyuan_xiong"


# ------------------------------------------------------------------ setup
def cmd_doctor(a):
    rows = [
        ("Blender (build, render)", blender(), "install Blender 4.2+, or set LOCHARA_BLENDER"),
        ("npx (optimise with gltf-transform)", npx(), "install Node.js 18+"),
        ("mflux (FLUX pictures)", mflux(), "uv tool install mflux   (Apple Silicon)"),
        ("AssetFurnace (picture -> 3D)", str(af.ASSETFURNACE) if af.installed() else None, "lochara setup assetfurnace"),
        ("  with lochara's patch", "applied" if af.patched() else None, "lochara setup assetfurnace"),
        ("VRoid Studio (design a base body)", vroid_studio(), "optional: https://vroid.com/en/studio"),
    ]
    ok = True
    for name, found, hint in rows:
        print(f"{'ok ' if found else '-- '} {name:38} {found or hint}")
        ok &= bool(found) or name.startswith("VRoid")
    if af.installed():
        try:
            ready = [e["id"] for e in af.engines() if e.get("state") == "ready" and e["makes"] == "3D models"]
            print(f"{'ok ' if ready else '-- '} {'3D engines ready':38} {', '.join(ready) or 'none: lochara engines'}")
        except Problem as e:
            print(f"--  3D engines: {e}")
    sys.exit(0 if ok else 1)


def cmd_setup(a):
    if a.what == "assetfurnace":
        af.setup()
    elif a.what == "engine":
        if not a.engine:
            raise Problem("which engine? `lochara engines` lists them")
        res = af.install_engine(a.engine, a.yes)
        print(json.dumps(res, indent=1))
        if not a.yes:
            print("\nNothing downloaded yet. Run again with --yes to download it.")


def cmd_engines(a):
    for e in af.engines():
        if e["makes"] != "3D models":
            continue
        print(f"{e['id']:15} {e.get('state', ''):12} {e.get('download_size', ''):>8}  runs here: "
              f"{'yes' if e.get('runs_here') else 'no '}  {e.get('licence', '')}")
        print(f"{'':15} {e.get('best_for', '')}")


# ------------------------------------------------------------------ characters
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


def cmd_new(a):
    if not a.path and not NAME.match(a.name):
        raise Problem(f"name {a.name!r}: use lowercase letters, digits and - (it becomes the folder name)")
    root = Path(a.path) if a.path else REPO / "characters" / a.name
    if a.source:
        designs = pictures_in(a.source)  # checked before anything is made
    c = create(root, a.title or a.name, a.base)
    out = {"wrote": [str(c.file)]}
    if a.source:
        out = add_designs(c, designs, "c", a.prompt)
        out["wrote"].insert(0, str(c.file))
    step = state.next_step(c)
    print(f"made {c.root}\n{state.describe(step)}")
    return {**out, "next": step}


def cmd_base(a):
    c = Character(find(a.character))
    dest = set_base(c, a.base)
    print(f"base: {dest}")
    return {"wrote": [str(dest)]}


def all_characters() -> list[Path]:
    return [f for folder in ("characters", "examples") for f in sorted((REPO / folder).glob("*/character.json"))]


def cmd_list(a):
    for folder in ("characters", "examples"):
        for f in sorted((REPO / folder).glob("*/character.json")):
            data = json.loads(f.read_text())
            print(f"{folder}/{f.parent.name:20} {data.get('name', '')}  ({len(data.get('parts', []))} parts)")


def seeds_for(a) -> list[int]:
    return a.seeds or random.sample(range(1, 100000), a.n)


def add_designs(c: Character, files: list[Path], tag: str, prompt: str | None) -> dict:
    """Keep pictures drawn elsewhere (by the agent in the chat, by hand) as concepts: <tag>-d<n>, numbered on."""
    out = c.root / "concepts"
    out.mkdir(parents=True, exist_ok=True)
    if prompt:
        (out / f"{tag}-prompt.txt").write_text(prompt + "\n")
    n = len(list(out.glob(f"{tag}-d*")))
    placed = []
    for f in files:
        n += 1
        dest = out / f"{tag}-d{n}{f.suffix.lower()}"
        shutil.copyfile(f, dest)
        placed.append(dest)
        print(f"  {dest}")
    every = sorted(p for p in out.glob(f"{tag}-*") if p.suffix.lower() in state.PICTURE_EXTS and p.stem != f"{tag}-sheet")
    s = pictures.sheet(every, out / f"{tag}-sheet.png", tile=384)
    print(f"sheet: {s}")
    return {"wrote": [str(p) for p in placed], "show": [str(s)]}


def cmd_concept(a):
    c = Character(find(a.character))
    if a.source:
        return add_designs(c, pictures_in(a.source), a.tag, a.prompt)
    if not a.prompt:
        raise Problem("describe the design: lochara concept <character> \"<prompt>\" (or keep pictures with --from <folder>)")
    prompt = f"{a.prompt}. {pictures.CONCEPT_STYLE}" if not a.raw else a.prompt
    out = c.root / "concepts"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{a.tag}-prompt.txt").write_text(prompt + "\n")
    if a.via == "handoff":
        req = handoff.create(c, "concept", prompt, out, f"{a.tag}-h", a.n, [Path(r) for r in a.ref or []], (768, 1344),
                             notes="full body, whole figure in frame, plain background")
        print(handoff.describe(req))
        return {"request": req["id"]}
    made = pictures.draw(prompt, out, seeds_for(a), (768, 1344), prefix=f"{a.tag}-s")
    s = pictures.sheet(made, out / f"{a.tag}-sheet.png", tile=384)
    print(f"sheet: {s}")
    return {"show": [str(s)]}


def cmd_part(a):
    c = Character(find(a.character))
    d = c.part_dir(a.id)
    part = c.part(a.id)
    if a.action == "draw":
        if not a.prompt and not (d / "prompt.txt").exists():
            raise Problem("describe the part: lochara part draw <character> <id> \"<what it looks like>\"")
        text = a.prompt or (d / "prompt.txt").read_text().strip()
        prompt = text if (a.raw or not a.prompt) else f"{text}. {pictures.PART_STYLE}"
        (d).mkdir(parents=True, exist_ok=True)
        (d / "prompt.txt").write_text(prompt + "\n")
        if not part:
            part = {"id": a.id, "bone": "", "enabled": False}
            c.data.setdefault("parts", []).append(part)
        part["via"] = a.via
        c.save()
        if a.via == "handoff":
            req = handoff.create(c, f"part-{a.id}", prompt, d / "candidates", "h", a.n, [Path(r) for r in a.ref or []],
                                 notes="one isolated object, whole object in frame, plain background")
            print(handoff.describe(req))
            print(f"after delivery: lochara part pick {c.id} {a.id} h<n>")
            return {"request": req["id"]}
        pictures.draw(prompt, d / "candidates", seeds_for(a), (1024, 1024))
        sheet = candidate_sheet(d)
        print(f"sheet: {sheet}")
        print(f"next: lochara part pick {c.id} {a.id} <seed>")
        return {"show": [str(sheet)]}
    elif a.action == "pick":
        name = f"s{a.seed}" if str(a.seed).isdigit() else str(a.seed)
        found = sorted((d / "candidates").glob(f"{name}.*"))
        if not found:
            raise Problem(f"no candidate {name} in {d / 'candidates'}")
        Image.open(found[0]).convert("RGBA").save(d / "picture.png")
        if part is not None:
            if str(a.seed).isdigit():
                part["seed"] = int(a.seed)
            else:
                part.pop("seed", None)
                part["picture"] = name
            c.save()
        print(f"picked {found[0].name}. next: lochara part model {c.id} {a.id}")
        return {"show": [str(d / "picture.png")]}
    elif a.action == "model":
        pic = d / "picture.png"
        if not pic.exists():
            raise Problem(f"no {pic}: draw and pick first, or put your own picture there")
        print(f"building {a.id} with {a.engine} at about {a.triangles} triangles (Hunyuan takes about 20 min) ...")
        model, asset = af.make_model(pic, a.engine, a.triangles)
        shutil.copy(model, d / "model.glb")
        af.preview(asset, d / "preview.png")
        if part is None:
            part = {"id": a.id, "bone": "", "enabled": False}
            c.data.setdefault("parts", []).append(part)
        part.update({"model": f"parts/{a.id}/model.glb", "engine": a.engine, "triangles": a.triangles})
        c.save()
        print(f"model: {d / 'model.glb'}\npreview: {d / 'preview.png'}")
        print(f"next: set its bone/offset/size in character.json, enable it, then lochara build {c.id}")
        return {"show": [str(d / "preview.png")]}


def optimise(src: Path, dest: Path, texture_size: int) -> None:
    exe = npx()
    if not exe:
        print("  npx not found: skipping optimisation")
        shutil.copy(src, dest)
        return
    subprocess.run([exe, "-y", "@gltf-transform/cli@4", "optimize", str(src), str(dest), "--compress", "meshopt",
                    "--texture-compress", "webp", "--texture-size", str(texture_size), "--join", "false"],
                   check=True, capture_output=True)


def cmd_build(a):
    c = Character(find(a.character))
    data = c.data
    c.build.mkdir(exist_ok=True)
    base = c.path(data["base"]["file"])
    if not base or not base.exists():
        src = data["base"].get("source")
        raise Problem(f"no base model at {base}." + (f" Get it from {src}" if src else ""))
    styled = c.build / "styled.glb"
    script = data.get("style", {}).get("script")
    print(f"[1/4] style {'with ' + script if script else '(bones, morphs, materials)'}")
    if script:
        exe = blender()
        env = {**os.environ, **{k: str(v) for k, v in data["style"].get("env", {}).items()}}
        r = subprocess.run([exe, "-b", "--factory-startup", "-P", str(c.path(script)), "--", str(base), str(styled)],
                           capture_output=True, text=True, env=env)
        if r.returncode != 0 or not styled.exists() or "Traceback" in r.stdout + r.stderr:
            raise Problem(f"style script failed:\n" + "\n".join((r.stdout + r.stderr).splitlines()[-25:]))
    else:
        run_blender("style", {"base": str(base), "style": data.get("style", {}), "out": str(styled)})
    parts = [dict(p, model=str(c.path(p["model"]))) for p in data.get("parts", [])
             if p.get("enabled", True) and p.get("model") and p.get("bone")]
    raw = c.build / f"{c.id}.raw.glb"
    print(f"[2/4] parts ({len(parts)})")
    run_blender("parts", {"styled": str(styled), "parts": parts, "out": str(raw)})
    out = c.build / f"{c.id}.glb"
    print("[3/4] optimise")
    optimise(raw, out, data.get("output", {}).get("textureSize", 1024))
    print("[4/4] check")
    return {"contract_ok": report(c, out)}


def report(c: Character, path: Path) -> bool:
    info = glb.inspect(path)
    print(f"  {path}\n  {info['bytes'] / 1e6:.2f} MB, {info['triangles']:,} triangles, {len(info['bones'])} bones, "
          f"morphs: {', '.join(info['morphs']) or 'none'}, parts: {', '.join(info['parts']) or 'none'}")
    problems = glb.check(info, c.data.get("contract", {}), c.data.get("output", {}).get("maxBytes"))
    for p in problems:
        print(f"  !! {p}")
    if not problems:
        print("  contract ok")
    return not problems


def cmd_check(a):
    c = Character(find(a.character))
    path = Path(a.file) if a.file else c.build / f"{c.id}.glb"
    if not path.exists():
        raise Problem(f"no {path}: run lochara build {c.id}")
    ok = report(c, path)
    return {"contract_ok": ok, "exit": 0 if ok else 1}


def cmd_render(a):
    c = Character(find(a.character))
    path = Path(a.file) if a.file else c.build / f"{c.id}.glb"
    if not path.exists():
        raise Problem(f"no {path}: run lochara build {c.id}")
    (c.root / "renders").mkdir(exist_ok=True)
    out = c.root / "renders" / f"{a.name}.png"
    job = {"model": str(path), "out": str(out)}
    if a.focus:
        job.update(focus=a.focus, span=a.span)
    run_blender("render", job)
    if a.open:
        subprocess.run(["open", str(out)])
    return {"show": [str(out)]}


def cmd_export(a):
    c = Character(find(a.character))
    src = c.build / f"{c.id}.glb"
    if not src.exists():
        raise Problem(f"no {src}: run lochara build {c.id}")
    if not report(c, src) and not a.force:
        raise Problem("the build doesn't meet its contract (use --force to export anyway)")
    targets = a.to or [t["to"] for t in c.data.get("export", [])]
    if not targets:
        raise Problem("nowhere to export: add \"export\": [{\"to\": \"...\"}] to character.json or pass --to")
    wrote = []
    for t in targets:
        dest = expand(t, c.root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dest)
        print(f"exported {dest}")
        wrote.append(str(dest))
    return {"wrote": wrote}


# ------------------------------------------------------------------ parser
def candidate_sheet(d: Path) -> Path:
    files = sorted(p for p in (d / "candidates").iterdir() if p.suffix.lower() in state.PICTURE_EXTS
                   and p.stem != "sheet")
    return pictures.sheet(files, d / "candidates" / "sheet.png")


def cmd_requests(a):
    chars = [Character(find(a.character))] if a.character else [Character(f.parent) for f in all_characters()]
    reqs = [dict(req, character=c.id) for c in chars for req in handoff.open_requests(c)]
    for req in reqs:
        print(handoff.describe(req) + "\n")
    if not reqs:
        print("no open requests")
    return {"requests": reqs}


def pictures_in(source: str) -> list[Path]:
    """Every picture in a folder, in name order."""
    folder = Path(source)
    if not folder.is_dir():
        raise Problem(f"not a folder: {folder}")
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in state.PICTURE_EXTS)
    if not files:
        raise Problem(f"no pictures in {folder}")
    return files


def delivered_files(a) -> list[Path]:
    """The files named, plus every picture in --from (in name order)."""
    files = [Path(f) for f in a.files] + (pictures_in(a.source) if a.source else [])
    if not files:
        raise Problem("nothing to deliver: name the files, or a folder with --from")
    return files


def cmd_deliver(a):
    c = Character(find(a.character))
    placed = handoff.deliver(c, a.request, delivered_files(a))
    req = handoff.load(c, a.request)
    for p in placed:
        print(f"  {p}")
    dest = Path(req["deliver_to"])
    if req["kind"] == "concept":
        tag = req["prefix"].rsplit("-", 1)[0]
        files = sorted(p for p in dest.glob(f"{tag}-*") if p.suffix.lower() in state.PICTURE_EXTS)
        sheet = pictures.sheet(files, dest / f"{tag}-sheet.png", tile=384)
    else:
        sheet = candidate_sheet(dest.parent)
        print(f"next: lochara part pick {c.id} {req['kind'].removeprefix('part-')} {placed[0].stem}")
    print(f"sheet: {sheet}")
    return {"wrote": [str(p) for p in placed], "show": [str(sheet)]}


def cmd_next(a):
    if not a.character:
        step = state.start([Character(f.parent) for f in all_characters()])
        print(state.describe(step))
        return {"next": step}
    step = state.next_step(Character(find(a.character)), a.at)
    print(state.describe(step))
    return {"next": step}


def run_json(a) -> int:
    """Run the command with its progress on stderr, then print one JSON result on stdout.

    Redirects file descriptor 1, not just sys.stdout, so tools the command runs (Blender, mflux) can't write into
    the JSON either.
    """
    sys.stdout.flush()
    saved = os.dup(1)
    os.dup2(2, 1)
    try:
        try:
            out = {"ok": True, "command": a.cmd, **(a.fn(a) or {})}
        except Problem as e:
            out = {"ok": False, "command": a.cmd, "problem": str(e.code).removeprefix("lochara: ")}
        character = getattr(a, "character", None)
        if character and "next" not in out:
            try:
                out["next"] = state.next_step(Character(find(character)))
            except Problem:
                if NAME.match(character):
                    out["next"] = state.missing(character)
    finally:
        sys.stdout.flush()
        os.dup2(saved, 1)
        os.close(saved)
    code = out.pop("exit", 0 if out["ok"] else 1)
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return code


def main(argv=None):
    p = argparse.ArgumentParser(prog="lochara", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="print one JSON result (progress goes to stderr)")

    def command(name: str, help: str, fn) -> argparse.ArgumentParser:
        s = sub.add_parser(name, help=help, parents=[common])
        s.set_defaults(fn=fn)
        return s

    command("doctor", "check the tools lochara needs", cmd_doctor)
    s = command("setup", "install AssetFurnace, or download a 3D engine's weights", cmd_setup)
    s.add_argument("what", choices=["assetfurnace", "engine"]); s.add_argument("engine", nargs="?")
    s.add_argument("--yes", action="store_true", help="really download (engines are several GB)")
    command("engines", "list picture -> 3D engines", cmd_engines)

    s = command("new", "make a character folder", cmd_new)
    s.add_argument("name"); s.add_argument("--base", help="a stock base by name, or a rigged VRM/GLB to start from (copied into assets/)")
    s.add_argument("--title"); s.add_argument("--path", help="where (default characters/<name>)")
    s.add_argument("--from", dest="source", help="keep every picture in this folder as its design (drawn elsewhere)")
    s.add_argument("--prompt", help="with --from: what the design pictures show")
    command("list", "list characters", cmd_list)
    s = command("base", "set a character's base body: a stock base by name, or a VRM/GLB file", cmd_base)
    s.add_argument("character"); s.add_argument("base")
    s = command("next", "what to do next for a character (none: list them, or start one)", cmd_next)
    s.add_argument("character", nargs="?")
    s.add_argument("--at", choices=state.AT, help="go back to an earlier choice (the art, the body), even one made")

    def seeds(s):
        s.add_argument("-n", type=int, default=4, help="how many candidates")
        s.add_argument("--seeds", type=int, nargs="+", help="exact seeds instead of random ones")
        s.add_argument("--raw", action="store_true", help="send the prompt as written (no style wording added)")

    def via(s):
        s.add_argument("--via", choices=["local", "handoff"], default="local",
                       help="local: draw with FLUX here; handoff: write a request for another tool or agent to fill")
        s.add_argument("--ref", nargs="+", help="reference pictures for a handoff (the design)")

    s = command("concept", "draw full-body concepts", cmd_concept)
    s.add_argument("character"); s.add_argument("prompt", nargs="?"); s.add_argument("--tag", default="c")
    s.add_argument("--from", dest="source", help="keep every picture in this folder as concepts instead of drawing")
    seeds(s); via(s)

    s = command("part", "draw / pick / model a part", cmd_part)
    s.add_argument("action", choices=["draw", "pick", "model"]); s.add_argument("character"); s.add_argument("id")
    s.add_argument("prompt", nargs="?", help="draw: what the part looks like")
    s.add_argument("seed", nargs="?", help="pick: the seed of the candidate")
    s.add_argument("--engine", default=DEFAULT_ENGINE); s.add_argument("--triangles", type=int, default=3000)
    seeds(s); via(s)

    s = command("requests", "list open picture requests (handoffs)", cmd_requests)
    s.add_argument("character", nargs="?")
    s = command("deliver", "fill a picture request with files made elsewhere", cmd_deliver)
    s.add_argument("character"); s.add_argument("request"); s.add_argument("files", nargs="*")
    s.add_argument("--from", dest="source", help="deliver every picture in this folder")

    s = command("build", "base + style + parts -> optimised GLB, then check", cmd_build)
    s.add_argument("character")
    s = command("check", "check a build against the character's contract", cmd_check)
    s.add_argument("character"); s.add_argument("--file")
    s = command("render", "front / three-quarter / back contact sheet", cmd_render)
    s.add_argument("character"); s.add_argument("--file"); s.add_argument("--name", default="latest")
    s.add_argument("--focus", help="a bone to frame, e.g. Head"); s.add_argument("--span", type=float, default=0.45)
    s.add_argument("--open", action="store_true")
    s = command("export", "copy the build to the character's export targets", cmd_export)
    s.add_argument("character"); s.add_argument("--to", nargs="+"); s.add_argument("--force", action="store_true")

    a = p.parse_args(argv)
    if a.cmd == "part" and a.action == "pick":
        a.seed, a.prompt = a.prompt, None
    if a.json:
        sys.exit(run_json(a))
    result = a.fn(a) or {}
    sys.exit(result.get("exit", 0))


if __name__ == "__main__":
    main()
