"""Picture -> 3D through AssetFurnace (github.com/Bingeljell/image-to-3dlab, Apache-2.0), installed in vendor/.

AssetFurnace runs in its own Python environment, so its functions are called through a small driver
in that interpreter. Its studio (a local web server on :8777) starts on the first call.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from .env import ASSETFURNACE, ASSETFURNACE_REF, REPO, Problem, assetfurnace_python

PATCH = REPO / "third_party" / "assetfurnace" / "backend-spec.patch"

DRIVER = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from image_to_3dlab import mcp_server as m
tool, kwargs, out = sys.argv[2], json.loads(sys.argv[3]), sys.argv[4]
fn = getattr(m, tool)
res = fn(**kwargs) if tool in ("options", "blender_helpers") else fn(m.Studio(), **kwargs)
if isinstance(res, tuple) and isinstance(res[0], (bytes, bytearray)):   # preview: (png, info)
    open(out, "wb").write(res[0]); res = res[1]
print(json.dumps(res, default=str))
"""


def installed() -> bool:
    return assetfurnace_python().exists()


def patched() -> bool:
    if not (ASSETFURNACE / ".git").exists():
        return False
    r = subprocess.run(["git", "-C", str(ASSETFURNACE), "apply", "--check", "-R", str(PATCH)],
                       capture_output=True)
    return r.returncode == 0


def call(tool: str, out: Path | None = None, **kwargs):
    if not installed():
        raise Problem("AssetFurnace is not installed. Run `lochara setup assetfurnace`.")
    r = subprocess.run([str(assetfurnace_python()), "-I", "-c", DRIVER, str(ASSETFURNACE), tool,
                        json.dumps(kwargs), str(out or "")], capture_output=True, text=True)
    if r.returncode != 0:
        msg = (r.stderr.strip().splitlines() or ["(no output)"])[-1]
        raise Problem(f"AssetFurnace {tool} failed: {msg}")
    return json.loads(r.stdout.strip().splitlines()[-1])


def setup() -> None:
    """Clone the pinned release, install its Python packages, apply our fix. No model weights."""
    if not (ASSETFURNACE / ".git").exists():
        ASSETFURNACE.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", "--branch", ASSETFURNACE_REF,
                        "https://github.com/Bingeljell/image-to-3dlab.git", str(ASSETFURNACE)], check=True)
    if not installed():
        # the release's own installer matches its code (the one on assetfurnace.com tracks main)
        subprocess.run(["bash", str(ASSETFURNACE / "install.sh"), "--dir", str(ASSETFURNACE), "--ref",
                        ASSETFURNACE_REF, "--yes", "--no-start"], check=True)
    if not patched():
        subprocess.run(["git", "-C", str(ASSETFURNACE), "apply", str(PATCH)], check=True)
    print("AssetFurnace ready. Engines download separately: `lochara setup engine <id>` (see `lochara engines`).")


def engines() -> list[dict]:
    return call("list_engines")


def install_engine(engine: str, yes: bool) -> dict:
    return call("install_backend", backend_id=engine, confirm=yes)


def wait(run_id: str, label: str) -> dict:
    last = ""
    while True:
        s = call("run_status", run_id=run_id, wait_seconds=40)
        line = f"{s.get('current')}: {s.get('message')}"
        if line != last:
            print(f"  {label} {line}")
            last = line
        if s.get("status") in ("done", "failed", "error", "cancelled"):
            if s.get("status") != "done":
                raise Problem(f"AssetFurnace run {run_id} {s.get('status')}: {s.get('error') or s.get('message')}")
            return s
        if s.get("stalled"):
            # v0.5.7 marks a run stalled when its worker died without saying so (see third_party/assetfurnace)
            time.sleep(60)
            again = call("run_status", run_id=run_id)
            if again.get("stalled") and again.get("current") == s.get("current"):
                raise Problem(f"AssetFurnace run {run_id} stalled at {s.get('current')}. Check "
                              f"{ASSETFURNACE}/output/.studio-mcp.log, and that `lochara doctor` shows the patch.")


def make_model(picture: Path, engine: str, triangles: int) -> tuple[Path, str]:
    """picture -> finished GLB at about `triangles` triangles. Returns the GLB path and the asset id."""
    started = call("create", want="prop", image_path=str(picture), engine=engine, front_and_back=False,
                   finish_detail=triangles)
    done = wait(started["run_id"], "3D")
    made = done.get("made") or {}
    finished = made.get("finished") or made.get("model")
    if not finished:
        raise Problem(f"AssetFurnace finished without a model: {done}")
    return ASSETFURNACE / finished, done["asset_id"]


def preview(asset_id: str, out: Path) -> None:
    call("preview", out=out, asset_id=asset_id)
