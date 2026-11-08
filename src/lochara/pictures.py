"""Text -> picture with FLUX.2 klein (Apache-2.0) through mflux, on Apple Silicon. Plus contact sheets."""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from .env import mflux, need

PART_STYLE = ("product render of a single isolated object, three-quarter view, centred, whole object in frame, "
              "soft studio lighting, plain light grey background, no person")
CONCEPT_STYLE = ("full body character design, standing in a relaxed A-pose, whole figure from head to feet in "
                 "frame, front view, plain light grey background")


def draw(prompt: str, out_dir: Path, seeds: list[int], size: tuple[int, int], prefix: str = "s") -> list[Path]:
    exe = need(mflux(), "mflux", "Install it with `uv tool install mflux` (Apple Silicon).")
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for s in seeds:
        out = out_dir / f"{prefix}{s}.png"
        print(f"  drawing seed {s} ...")
        subprocess.run([exe, "--model", "flux2-klein-4b", "--quantize", "8", "--prompt", prompt, "--seed", str(s),
                        "--width", str(size[0]), "--height", str(size[1]), "--steps", "4", "--output", str(out)],
                       check=True, capture_output=True)
        made.append(out)
    return made


def sheet(images: list[Path], out: Path, tile: int = 512) -> Path:
    """Side by side, each labelled with its file stem (the seed), for picking."""
    ims = [Image.open(p).convert("RGB") for p in images]
    scaled = [im.resize((tile, round(tile * im.height / im.width))) for im in ims]
    h = max(im.height for im in scaled)
    canvas = Image.new("RGB", (tile * len(scaled), h + 36), (24, 24, 24))
    d = ImageDraw.Draw(canvas)
    for i, (im, p) in enumerate(zip(scaled, images)):
        canvas.paste(im, (i * tile, 36))
        d.text((i * tile + 10, 10), p.stem, fill=(255, 140, 60))
    canvas.save(out)
    return out
