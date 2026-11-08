"""Where things are: the repo, the external tools lochara drives, and how to run them."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VENDOR = REPO / "vendor"
BLENDER_SCRIPT = REPO / "blender" / "lochara_blender.py"
ASSETFURNACE = Path(os.environ.get("LOCHARA_ASSETFURNACE", VENDOR / "assetfurnace"))
ASSETFURNACE_REF = "v0.5.7"


class Problem(SystemExit):
    """A user-facing failure: printed without a traceback."""

    def __init__(self, message: str):
        super().__init__(f"lochara: {message}")


def blender() -> str | None:
    if os.environ.get("LOCHARA_BLENDER"):
        return os.environ["LOCHARA_BLENDER"]
    for p in ("/Applications/Blender.app/Contents/MacOS/Blender", shutil.which("blender")):
        if p and Path(p).exists():
            return p
    return None


def mflux() -> str | None:
    return shutil.which("mflux-generate-flux2") or (
        str(Path.home() / ".local/bin/mflux-generate-flux2")
        if (Path.home() / ".local/bin/mflux-generate-flux2").exists() else None)


def npx() -> str | None:
    return shutil.which("npx")


def vroid_studio() -> str | None:
    for p in ("/Applications/VRoidStudio.app", Path.home() / "Applications/VRoidStudio.app"):
        if Path(p).exists():
            return str(p)
    return None


def assetfurnace_python() -> Path:
    return ASSETFURNACE / ".venv" / "bin" / "python"


def need(tool: str | None, name: str, hint: str) -> str:
    if not tool:
        raise Problem(f"{name} not found. {hint}")
    return tool


def run_blender(stage: str, job: dict) -> None:
    exe = need(blender(), "Blender", "Install Blender 4.2+ or set LOCHARA_BLENDER to its executable.")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(job, f)
        job_file = f.name
    try:
        proc = subprocess.run([exe, "-b", "--factory-startup", "-P", str(BLENDER_SCRIPT), "--", stage, job_file],
                              capture_output=True, text=True)
    finally:
        os.remove(job_file)
    lines = (proc.stdout + proc.stderr).splitlines()
    for line in lines:
        if line.startswith(("WROTE", "bones:", "morphs detected", "part ", "glow:", "note:")):
            print("  " + line)
    failed = proc.returncode != 0 or any("Traceback" in line or line.startswith("lochara:") for line in lines)
    if failed:
        tail = "\n".join(lines[-25:])
        raise Problem(f"Blender stage '{stage}' failed:\n{tail}")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kw)


def python() -> str:
    return sys.executable
