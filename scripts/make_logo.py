"""Draw the 윤DF mark: an ink-charcoal Y on a plain white rounded tile.

The Y follows the refined logo (art/logo/YoonDF-Refined-Logo.png): two
arms with flat tops meeting in a sharp notch, a straight stem, softly
rounded ends. It is drawn here as a vector path so every size is crisp;
the tile keeps a hairline edge so it still reads on a white taskbar or
window. Pixel sizes get an edge exactly one device pixel wide.

Writes assets/logo/mark.svg (the tile and Y, for the interface),
assets/icon/<size>.png and assets/icon.ico.
Needs PySide6 only.
Usage: python scripts/make_logo.py
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import math
import os
import struct
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
INK = "#29313A"          # the Y, and the interface's primary ink
TILE = "#FFFFFF"
EDGE = "#D9DCE0"
BOX = 1024               # viewBox edge
MARGIN = 0.035           # space around the tile, as a share of the box
CORNER = 0.22            # tile corner radius, as a share of the tile edge
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256, 512)
ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def fillet_path(points, radii):
    """A closed SVG path through `points` with each corner rounded by the
    matching radius (a circular fillet tangent to both edges)."""
    parts = []
    n = len(points)
    for i in range(n):
        (px, py), (x, y), (nx, ny) = points[i - 1], points[i], points[(i + 1) % n]
        r = radii[i]
        ax, ay, bx, by = px - x, py - y, nx - x, ny - y
        la, lb = math.hypot(ax, ay), math.hypot(bx, by)
        ax, ay, bx, by = ax / la, ay / la, bx / lb, by / lb
        angle = math.acos(max(-1.0, min(1.0, ax * bx + ay * by)))
        d = min(r / math.tan(angle / 2) if r else 0, la / 2, lb / 2)
        start, end = (x + ax * d, y + ay * d), (x + bx * d, y + by * d)
        cross = ax * by - ay * bx
        rr = d * math.tan(angle / 2)
        sweep = 0 if cross > 0 else 1
        parts.append(("M" if i == 0 else "L") + f"{start[0]:.2f},{start[1]:.2f}")
        if d > 0:
            parts.append(f"A{rr:.2f},{rr:.2f} 0 0 {sweep} {end[0]:.2f},{end[1]:.2f}")
    return " ".join(parts) + " Z"


def y_path(left, top, width):
    """The Y in a box `width` wide whose top-left is (left, top). Proportions
    are measured from the refined logo: arm slope 0.72, arm and stem about
    0.27 of the width, the notch at 0.33 of the height."""
    s = width / 744.0            # the measured Y is 744 units wide, 653 tall
    cx = 372.0
    def p(x, y): return (left + x * s, top + y * s)
    outer = lambda y: .713 * y                 # left arm, outside edge
    inner = lambda y: 211.8 + .743 * y         # left arm, inside edge
    notch = (cx - 211.8) / .743                # where the two inside edges meet
    half = 96.5                                # half the stem
    joint = (cx - half) / .713                 # outside edge meets the stem
    points = [p(outer(0), 0), p(inner(0), 0), p(cx, notch), p(2 * cx - inner(0), 0),
              p(2 * cx - outer(0), 0), p(cx + half, joint), p(cx + half, 653), p(cx - half, 653),
              p(cx - half, joint)]
    radii = [r * s for r in (20, 20, 4, 20, 20, 14, 20, 20, 14)]
    return fillet_path(points, radii)


def svg(edge_width, small=False):
    """Tile and Y on a BOX viewBox; `edge_width` in viewBox units. Small
    icons fill the square and enlarge the Y so it reads in a taskbar."""
    m = 0 if small else BOX * MARGIN
    tile = BOX - 2 * m
    radius = tile * (.18 if small else CORNER)
    inset = edge_width / 2
    y_width = tile * (.86 if small else .775)
    y_left = m + (tile - y_width) / 2
    y_top = m + tile * (.12 if small else .178)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {BOX} {BOX}">'
            f'<rect x="{m + inset:.2f}" y="{m + inset:.2f}" width="{tile - 2 * inset:.2f}" height="{tile - 2 * inset:.2f}" '
            f'rx="{radius - inset:.2f}" fill="{TILE}" stroke="{EDGE}" stroke-width="{edge_width:.2f}"/>'
            f'<path d="{y_path(y_left, y_top, y_width)}" fill="{INK}"/></svg>')


def render(size):
    from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRectF, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    renderer = QSvgRenderer(QByteArray(svg(BOX / size, small=size <= 24).encode()))
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    buffer = QBuffer(); buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


def ico(entries):
    """A Windows icon holding PNG images (supported since Windows Vista)."""
    header = struct.pack("<HHH", 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    directory, blobs = b"", b""
    for size, data in entries:
        edge = 0 if size >= 256 else size
        directory += struct.pack("<BBBBHHII", edge, edge, 0, 0, 1, 32, len(data), offset + len(blobs))
        blobs += data
    return header + directory + blobs


def main():
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication.instance() or QGuiApplication([])
    (ROOT / "assets" / "logo").mkdir(parents=True, exist_ok=True)
    # The interface draws the mark at many sizes; a hairline of 1/96 of the
    # tile reads as one pixel at about 96 px and stays light when larger.
    (ROOT / "assets" / "logo" / "mark.svg").write_text(svg(BOX / 96), encoding="utf-8")
    folder = ROOT / "assets" / "icon"; folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.png"):
        old.unlink()
    rendered = {size: render(size) for size in SIZES}
    for size, data in rendered.items():
        (folder / f"{size}.png").write_bytes(data)
    (ROOT / "assets" / "icon.ico").write_bytes(ico([(size, rendered[size]) for size in ICO_SIZES]))
    print("wrote assets/logo/mark.svg,", len(SIZES), "PNG sizes and assets/icon.ico")
    del app


if __name__ == "__main__":
    main()
