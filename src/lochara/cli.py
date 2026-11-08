"""lochara: make a rigged 3D character on your own machine.

A character = a rigged base body (VRoid Studio, or any rigged VRM/GLB) + rigid parts generated from text
(FLUX -> AssetFurnace), each attached to one bone, built into one web-ready GLB.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

from . import assetfurnace as af
from . import glb, pictures
from .character import Character, create, expand, find
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
def cmd_new(a):
    root = Path(a.path) if a.path else REPO / "characters" / a.name
    c = create(root, a.title or a.name, a.base)
    print(f"made {c.root}\nnext: put a rigged base model in assets/ (or pass --base), then `lochara build {a.name}`")


def cmd_list(a):
    for folder in ("characters", "examples"):
        for f in sorted((REPO / folder).glob("*/character.json")):
            data = json.loads(f.read_text())
            print(f"{folder}/{f.parent.name:20} {data.get('name', '')}  ({len(data.get('parts', []))} parts)")


def seeds_for(a) -> list[int]:
    return a.seeds or random.sample(range(1, 100000), a.n)


def cmd_concept(a):
    c = Character(find(a.character))
    prompt = f"{a.prompt}. {pictures.CONCEPT_STYLE}" if not a.raw else a.prompt
    out = c.root / "concepts"
    made = pictures.draw(prompt, out, seeds_for(a), (768, 1344), prefix=f"{a.tag}-s")
    (out / f"{a.tag}-prompt.txt").write_text(prompt + "\n")
    s = pictures.sheet(made, out / f"{a.tag}-sheet.png", tile=384)
    print(f"sheet: {s}")


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
        made = pictures.draw(prompt, d / "candidates", seeds_for(a), (1024, 1024))
        print(f"sheet: {pictures.sheet(sorted((d / 'candidates').glob('s*.png')), d / 'candidates' / 'sheet.png')}")
        if not part:
            c.data.setdefault("parts", []).append({"id": a.id, "bone": "", "enabled": False})
            c.save()
        print(f"next: lochara part pick {c.id} {a.id} <seed>")
    elif a.action == "pick":
        src = d / "candidates" / f"s{a.seed}.png"
        if not src.exists():
            raise Problem(f"no candidate {src}")
        shutil.copy(src, d / "picture.png")
        if part is not None:
            part["seed"] = int(a.seed)
            c.save()
        print(f"picked {src.name}. next: lochara part model {c.id} {a.id}")
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
    report(c, out)


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
    sys.exit(0 if report(c, path) else 1)


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
    for t in targets:
        dest = expand(t, c.root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dest)
        print(f"exported {dest}")


# ------------------------------------------------------------------ parser
def main(argv=None):
    p = argparse.ArgumentParser(prog="lochara", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="check the tools lochara needs").set_defaults(fn=cmd_doctor)
    s = sub.add_parser("setup", help="install AssetFurnace, or download a 3D engine's weights")
    s.add_argument("what", choices=["assetfurnace", "engine"]); s.add_argument("engine", nargs="?")
    s.add_argument("--yes", action="store_true", help="really download (engines are several GB)")
    s.set_defaults(fn=cmd_setup)
    sub.add_parser("engines", help="list picture -> 3D engines").set_defaults(fn=cmd_engines)

    s = sub.add_parser("new", help="make a character folder")
    s.add_argument("name"); s.add_argument("--base", help="a rigged VRM/GLB to start from (copied into assets/)")
    s.add_argument("--title"); s.add_argument("--path", help="where (default characters/<name>)")
    s.set_defaults(fn=cmd_new)
    sub.add_parser("list", help="list characters").set_defaults(fn=cmd_list)

    def seeds(s):
        s.add_argument("-n", type=int, default=4, help="how many candidates")
        s.add_argument("--seeds", type=int, nargs="+", help="exact seeds instead of random ones")
        s.add_argument("--raw", action="store_true", help="send the prompt as written (no style wording added)")

    s = sub.add_parser("concept", help="draw full-body concepts")
    s.add_argument("character"); s.add_argument("prompt"); s.add_argument("--tag", default="c")
    seeds(s); s.set_defaults(fn=cmd_concept)

    s = sub.add_parser("part", help="draw / pick / model a part")
    s.add_argument("action", choices=["draw", "pick", "model"]); s.add_argument("character"); s.add_argument("id")
    s.add_argument("prompt", nargs="?", help="draw: what the part looks like")
    s.add_argument("seed", nargs="?", help="pick: the seed of the candidate")
    s.add_argument("--engine", default=DEFAULT_ENGINE); s.add_argument("--triangles", type=int, default=3000)
    seeds(s)
    s.set_defaults(fn=cmd_part)

    s = sub.add_parser("build", help="base + style + parts -> optimised GLB, then check")
    s.add_argument("character"); s.set_defaults(fn=cmd_build)
    s = sub.add_parser("check", help="check a build against the character's contract")
    s.add_argument("character"); s.add_argument("--file"); s.set_defaults(fn=cmd_check)
    s = sub.add_parser("render", help="front / three-quarter / back contact sheet")
    s.add_argument("character"); s.add_argument("--file"); s.add_argument("--name", default="latest")
    s.add_argument("--focus", help="a bone to frame, e.g. Head"); s.add_argument("--span", type=float, default=0.45)
    s.add_argument("--open", action="store_true"); s.set_defaults(fn=cmd_render)
    s = sub.add_parser("export", help="copy the build to the character's export targets")
    s.add_argument("character"); s.add_argument("--to", nargs="+"); s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_export)

    a = p.parse_args(argv)
    if a.cmd == "part" and a.action == "pick":
        a.seed, a.prompt = a.prompt, None
    a.fn(a)


if __name__ == "__main__":
    main()
