#!/usr/bin/env python3
"""Pack user mini-thumbs into sprite atlases for the sunset matrix rain."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

CELL = 24
GRID = 32
PER_ATLAS = GRID * GRID
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "user-pictures"
OUT = ROOT / "assets" / "picture-atlases"


def circle_mask() -> Image.Image:
    mask = Image.new("L", (CELL, CELL), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, CELL - 1, CELL - 1), fill=255)
    return mask


def circle_thumb(path: Path, mask: Image.Image) -> Image.Image:
    src = Image.open(path).convert("RGBA")
    if src.size != (CELL, CELL):
        src = src.resize((CELL, CELL), Image.LANCZOS)
    src.putalpha(mask)
    return src


def main() -> None:
    files = sorted(SRC.glob("*_mini_thumb.jpg"))
    if not files:
        print(f"No thumbs in {SRC}", file=sys.stderr)
        sys.exit(1)

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("atlas-*"):
        old.unlink()

    mask = circle_mask()
    atlases = []
    for i in range(0, len(files), PER_ATLAS):
        chunk = files[i : i + PER_ATLAS]
        idx = i // PER_ATLAS
        name = f"atlas-{idx:02d}.png"
        dest = OUT / name
        rows = math.ceil(len(chunk) / GRID)
        sheet = Image.new("RGBA", (GRID * CELL, rows * CELL), (255, 255, 255, 0))
        for n, path in enumerate(chunk):
            x = (n % GRID) * CELL
            y = (n // GRID) * CELL
            sheet.paste(circle_thumb(path, mask), (x, y))
        sheet.save(dest, "PNG", optimize=True)
        atlases.append({"src": name, "count": len(chunk)})
        print(f"Wrote {name} ({len(chunk)} cells)")

    manifest = {"cellSize": CELL, "grid": GRID, "atlases": atlases}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Packed {len(files)} pictures into {len(atlases)} atlases")


if __name__ == "__main__":
    main()
