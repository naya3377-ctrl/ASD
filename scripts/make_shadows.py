"""Soft shadows for the interface, as nine-slice images.

A blurred rounded rectangle per level; ui/Shadow.qml stretches the middle and
keeps the corners, so any card, page or dialog gets a soft macOS-like
shadow that also works in the software renderer (no shader effects).
The numbers here must match LEVELS in ui/Shadow.qml.

Writes assets/ui/shadow-<level>.png. Needs Pillow (tools only).
Usage: python scripts/make_shadows.py
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
# level: (margin, corner radius, blur, opacity); a warm near-black like the character's fur
LEVELS = {"small": (8, 6, 3, .20), "medium": (16, 10, 7, .17), "large": (36, 12, 16, .26), "page": (14, 0, 5, .22)}
INK = (38, 28, 20)


def main():
    folder = ROOT / "assets" / "ui"; folder.mkdir(parents=True, exist_ok=True)
    for name, (margin, radius, blur, opacity) in LEVELS.items():
        # Blur a large shape, then keep its corners and one row/column of its
        # edges: a small shape would lose its middle to the blur.
        inner, scale = 160, 4
        big_size = 2 * margin + inner
        big = Image.new("L", (big_size * scale, big_size * scale), 0)
        ImageDraw.Draw(big).rounded_rectangle(
            [margin * scale, margin * scale, (margin + inner) * scale - 1, (margin + inner) * scale - 1],
            radius=radius * scale, fill=int(255 * opacity))
        big = big.resize((big_size, big_size), Image.LANCZOS).filter(ImageFilter.GaussianBlur(blur))
        edge = margin + radius
        size = 2 * edge + 1
        alpha = Image.new("L", (size, size), 0)
        for sx, dx in ((0, 0), (big_size // 2, edge), (big_size - edge, edge + 1)):
            for sy, dy in ((0, 0), (big_size // 2, edge), (big_size - edge, edge + 1)):
                w = 1 if sx == big_size // 2 else edge
                h = 1 if sy == big_size // 2 else edge
                alpha.paste(big.crop((sx, sy, sx + w, sy + h)), (dx, dy))
        image = Image.new("RGBA", (size, size), INK + (0,)); image.putalpha(alpha)
        image.save(folder / f"shadow-{name}.png", optimize=True)
        print(name, size)


if __name__ == "__main__":
    main()
