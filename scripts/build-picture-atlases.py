#!/usr/bin/env python3
"""Pack user mini-thumbs into sprite atlases for the sunset matrix rain."""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

CELL = 24
GRID = 32
PER_ATLAS = GRID * GRID
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "user-pictures"
OUT = ROOT / "assets" / "picture-atlases"

# Gravatar wavatars / identicons / PNG RoboHash were stored as PNG bytes under
# a .jpg name. Real photos went through Arc as JPEG.
#
# RoboHash JPEGs share ImageMagick's ~quality-92 quantization tables (the same
# tables Arc used when converting the Gravatar `d=robohash` default) plus a
# large near-white background. Some real photos reuse those tables, so white
# background is required as well.
_ROBOHASH_QT = ((0, 3, 2, 592), (1, 3, 3, 891))
_WHITE_CHANNEL = 250
_ROBOHASH_WHITE_FRAC = 0.35


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


def _jpeg_qt_sig(im: Image.Image) -> tuple | None:
    qt = getattr(im, "quantization", None)
    if not qt:
        return None
    return tuple((k, qt[k][0], qt[k][1], sum(qt[k])) for k in sorted(qt))


def _white_fraction(im: Image.Image) -> float:
    rgb = im.convert("RGB")
    pixels = rgb.getdata()
    n = 0
    white = 0
    for r, g, b in pixels:
        n += 1
        if r >= _WHITE_CHANNEL and g >= _WHITE_CHANNEL and b >= _WHITE_CHANNEL:
            white += 1
    return white / n if n else 0.0


def generated_avatar_reason(path: Path) -> str | None:
    """Return a skip reason for Gravatar/RoboHash defaults, else None."""
    with Image.open(path) as im:
        if im.format == "PNG":
            return "png-generated"
        if im.format != "JPEG":
            return None
        if _jpeg_qt_sig(im) != _ROBOHASH_QT:
            return None
        if _white_fraction(im) >= _ROBOHASH_WHITE_FRAC:
            return "robohash"
    return None


def main() -> None:
    files = sorted(SRC.glob("*_mini_thumb.jpg"))
    if not files:
        print(f"No thumbs in {SRC}", file=sys.stderr)
        sys.exit(1)

    skipped: Counter[str] = Counter()
    kept: list[Path] = []
    for path in files:
        reason = generated_avatar_reason(path)
        if reason:
            skipped[reason] += 1
        else:
            kept.append(path)

    if skipped:
        print(
            "Skipped "
            f"{skipped['png-generated']} PNG generated avatars, "
            f"{skipped['robohash']} RoboHash robots "
            f"({sum(skipped.values())} / {len(files)})"
        )
    files = kept
    if not files:
        print("No user pictures left after filtering", file=sys.stderr)
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
