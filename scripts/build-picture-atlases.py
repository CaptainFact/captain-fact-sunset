#!/usr/bin/env python3
"""Pack user thumbs into sprite atlases for the sunset matrix rain.

Variants:
  std  24px mini thumbs → assets/picture-atlases/
  hq   96px thumbs      → assets/picture-atlases-hq/

Usage:
  python3 scripts/build-picture-atlases.py
  python3 scripts/build-picture-atlases.py hq
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
VARIANTS = {
    "std": {
        "src": ROOT / "assets" / "user-pictures",
        "glob": "*_mini_thumb.jpg",
        "out": ROOT / "assets" / "picture-atlases",
        "cell": 24,
        "grid": 32,
    },
    "hq": {
        "src": ROOT / "assets" / "user-pictures-hq",
        "glob": "*_thumb.jpg",
        "out": ROOT / "assets" / "picture-atlases-hq",
        "cell": 96,
        "grid": 16,
    },
}

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


def circle_mask(cell: int) -> Image.Image:
    mask = Image.new("L", (cell, cell), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, cell - 1, cell - 1), fill=255)
    return mask


def circle_thumb(path: Path, mask: Image.Image, cell: int) -> Image.Image:
    src = Image.open(path).convert("RGBA")
    if src.size != (cell, cell):
        src = src.resize((cell, cell), Image.LANCZOS)
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


def build(variant: str) -> None:
    cfg = VARIANTS[variant]
    src: Path = cfg["src"]
    out: Path = cfg["out"]
    cell: int = cfg["cell"]
    grid: int = cfg["grid"]
    per_atlas = grid * grid

    files = sorted(src.glob(cfg["glob"]))
    if not files:
        print(f"No thumbs in {src}", file=sys.stderr)
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

    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("atlas-*"):
        old.unlink()

    mask = circle_mask(cell)
    atlases = []
    for i in range(0, len(files), per_atlas):
        chunk = files[i : i + per_atlas]
        idx = i // per_atlas
        name = f"atlas-{idx:02d}.png"
        dest = out / name
        rows = math.ceil(len(chunk) / grid)
        sheet = Image.new("RGBA", (grid * cell, rows * cell), (255, 255, 255, 0))
        for n, path in enumerate(chunk):
            x = (n % grid) * cell
            y = (n // grid) * cell
            sheet.paste(circle_thumb(path, mask, cell), (x, y))
        sheet.save(dest, "PNG", optimize=True)
        atlases.append({"src": name, "count": len(chunk)})
        print(f"Wrote {name} ({len(chunk)} cells)")

    manifest = {"cellSize": cell, "grid": grid, "atlases": atlases}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Packed {len(files)} pictures into {len(atlases)} {variant} atlases")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "variant",
        nargs="?",
        choices=sorted(VARIANTS),
        default="std",
        help="std: 24px mini thumbs; hq: 96px thumbs (default: std)",
    )
    args = parser.parse_args()
    build(args.variant)


if __name__ == "__main__":
    main()
