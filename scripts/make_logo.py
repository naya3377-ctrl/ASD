"""Draw the 윤DF application icon from the character.

A rounded square (the continuous corner of macOS icons) of indigo denim,
faintly twilled, with tan contrast stitching like a pair of jeans; the
character's head and bow tie stand in front and run off the bottom edge.
Small sizes (32 px and below) drop the stitching and show the face larger,
so it still reads in a taskbar.

Writes assets/icon/<size>.png and assets/icon.ico.
Needs Pillow and NumPy (tools only; the app does not use them).
Usage: python scripts/make_logo.py
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import io
import math
import struct
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_character import ART, cut_out

ROOT = Path(__file__).resolve().parent.parent
S = 1024
DENIM_TOP, DENIM_BOTTOM = (64, 94, 146), (33, 55, 96)
STITCH = (214, 160, 92)
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256, 512)


def squircle(size, inset=0.0, n=5.0, steps=1440):
    c, r = size / 2, size / 2 - inset
    points = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        ct, st = math.cos(t), math.sin(t)
        points.append((c + r * math.copysign(abs(ct) ** (2 / n), ct), c + r * math.copysign(abs(st) ** (2 / n), st)))
    return points


def gradient(top, bottom):
    g = np.linspace(0, 1, S)[:, None, None]
    rows = np.array(top)[None, None, :] * (1 - g) + np.array(bottom)[None, None, :] * g
    return Image.fromarray(np.repeat(rows, S, axis=1).astype(np.uint8), "RGB").convert("RGBA")


def twill(step=10, alpha=14):
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0)); draw = ImageDraw.Draw(layer)
    for k in range(-S, 2 * S, step):
        draw.line([(k, 0), (k - S, S)], fill=(255, 255, 255, alpha), width=2)
    return layer


def stitching(inset, dash=22, gap=14, width=7):
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0)); draw = ImageDraw.Draw(layer)
    points = squircle(S, inset)
    run, on, segment = 0.0, True, [points[0]]
    for a, b in zip(points, points[1:] + points[:1]):
        run += math.dist(a, b)
        if on: segment.append(b)
        if run >= (dash if on else gap):
            if on and len(segment) > 1: draw.line(segment, fill=STITCH + (255,), width=width)
            on, run, segment = not on, 0.0, [b]
    return layer


def figure(character, crop_height, width, top):
    """The character cropped at `crop_height`, `width` wide, with a soft shadow."""
    bust = character.crop((0, 0, character.width, crop_height))
    height = round(bust.height * width / bust.width)
    bust = bust.resize((width, height), Image.LANCZOS)
    shadow = Image.new("RGBA", bust.size, (20, 18, 30, 0))
    shadow.putalpha(bust.getchannel("A").point(lambda v: int(v * .5)))
    layer = Image.new("RGBA", (S, S + height), (0, 0, 0, 0))
    x = (S - width) // 2
    layer.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)), (x, top + 16))
    layer.alpha_composite(bust, (x, top))
    return layer.crop((0, 0, S, S))


def icon(character, small=False):
    art = gradient(DENIM_TOP, DENIM_BOTTOM)
    art.alpha_composite(twill())
    if small:
        art.alpha_composite(figure(character, int(character.height * .62), int(S * 1.02), int(S * .06)))
    else:
        art.alpha_composite(stitching(S * .085))
        art.alpha_composite(figure(character, int(character.height * .9), int(S * .86), int(S * .1)))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).polygon(squircle(S, S * .04), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1))
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0)); out.paste(art, (0, 0), mask)
    return out


def ico(images):
    """A Windows icon holding PNG images (supported since Windows Vista)."""
    header = struct.pack("<HHH", 0, 1, len(images))
    offset, entries, blobs = 6 + 16 * len(images), b"", b""
    for size, data in images:
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset)
        blobs += data; offset += len(data)
    return header + entries + blobs


def main():
    character = cut_out(Image.open(ART / "standing.webp"))
    large, small = icon(character), icon(character, small=True)
    folder = ROOT / "assets" / "icon"; folder.mkdir(parents=True, exist_ok=True)
    entries = []
    for size in SIZES:
        image = (small if size <= 32 else large).resize((size, size), Image.LANCZOS)
        buffer = io.BytesIO(); image.save(buffer, "PNG", optimize=True)
        if size <= 256: entries.append((size, buffer.getvalue()))
        if size in (16, 24, 32, 48, 64, 128, 256, 512):
            (folder / f"{size}.png").write_bytes(buffer.getvalue())
    (ROOT / "assets" / "icon.ico").write_bytes(ico(entries))


if __name__ == "__main__":
    main()
