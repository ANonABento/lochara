"""Stock base models: rigged VRoid bodies a new character can start from, so starting one needs no file.

Only CC0 samples are listed (VRoid's own sample characters have their own terms). They live in vendor/vroid/<dir>/,
unpacked from the zips on https://opengameart.org/content/vroid-studio-cc0-models, with a full-body preview beside
each folder (<dir>_full.png). A base that isn't downloaded isn't offered.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .env import VENDOR, Problem

SOURCE = "https://opengameart.org/content/vroid-studio-cc0-models"
FOLDER = VENDOR / "vroid"


@dataclass(frozen=True)
class Base:
    name: str
    dir: str
    file: str

    @property
    def path(self) -> Path:
        return FOLDER / self.dir / self.file

    @property
    def preview(self) -> Path:
        return FOLDER / f"{self.dir}_full.png"

    @property
    def source(self) -> str:
        return f"{SOURCE} ({self.dir}.zip)"

    licence = "CC0"


STOCK = (
    Base("sample-d", "avatarsample_d_0", "AvatarSample_D.vrm"),
    Base("sample-d-dark", "avatarsample_d_darkness", "AvatarSample_D_Darkness.vrm"),
    Base("sample-e", "avatarsample_e", "AvatarSample_E.vrm"),
    Base("sample-f", "avatarsample_f", "AvatarSample_F.vrm"),
    Base("sample-g", "avatarsample_g", "AvatarSample_G.vrm"),
)


def available() -> list[Base]:
    return [b for b in STOCK if b.path.is_file()]


def stock(name: str) -> Base | None:
    """The stock base called `name`, if it's downloaded. A known name that isn't downloaded is a Problem."""
    for b in STOCK:
        if b.name == name:
            if not b.path.is_file():
                raise Problem(f"stock base {name} isn't downloaded (expected {b.path}; from {b.source})")
            return b
    return None
