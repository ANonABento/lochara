"""Read a GLB's structure without Blender: bones, morphs, triangles, textures, size."""
from __future__ import annotations

import json
import struct
from pathlib import Path


def read_json(path: Path) -> dict:
    with open(path, "rb") as f:
        magic, _version, _length = struct.unpack("<4sII", f.read(12))
        if magic != b"glTF":
            raise ValueError(f"{path} is not a GLB")
        chunk_len, chunk_type = struct.unpack("<II", f.read(8))
        return json.loads(f.read(chunk_len))


def inspect(path: Path) -> dict:
    gl = read_json(path)
    nodes = gl.get("nodes", [])
    bones = sorted({nodes[j].get("name", f"node{j}") for s in gl.get("skins", []) for j in s.get("joints", [])})
    morphs = sorted({n for m in gl.get("meshes", []) for n in (m.get("extras") or {}).get("targetNames", [])})
    acc = gl.get("accessors", [])
    tris = 0
    for m in gl.get("meshes", []):
        for p in m.get("primitives", []):
            if p.get("mode", 4) != 4:
                continue
            count = acc[p["indices"]]["count"] if "indices" in p else acc[p["attributes"]["POSITION"]]["count"]
            tris += count // 3
    return {
        "bytes": path.stat().st_size,
        "triangles": tris,
        "meshes": len(gl.get("meshes", [])),
        "materials": len(gl.get("materials", [])),
        "textures": len(gl.get("images", [])),
        "bones": bones,
        "morphs": morphs,
        "parts": sorted(n.get("name", "") for n in nodes if n.get("name", "").startswith("part_")),
    }


def check(info: dict, contract: dict, max_bytes: int | None) -> list[str]:
    """What the model is missing from its contract, as plain sentences (empty when it passes)."""
    problems = []
    missing_bones = [b for b in contract.get("bones", []) if b not in info["bones"]]
    if missing_bones:
        problems.append(f"missing bones: {', '.join(missing_bones)}")
    missing_morphs = [m for m in contract.get("morphs", []) if m not in info["morphs"]]
    if missing_morphs:
        problems.append(f"missing morphs: {', '.join(missing_morphs)}")
    if max_bytes and info["bytes"] > max_bytes:
        problems.append(f"{info['bytes'] / 1e6:.2f} MB is over the {max_bytes / 1e6:.2f} MB budget")
    return problems
