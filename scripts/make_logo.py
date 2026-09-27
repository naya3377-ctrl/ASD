"""Draw the 윤DF mark: a white page with a folded corner on a blue tile.

The design follows art/logo/YoonDF-Document-Logo.png: a rounded square in
the app's blue, a white page with softly rounded corners, its top right
corner folded over in pale blue, and "윤DF" set in the same blue at the foot
of the page. It is drawn here as vectors so every size is crisp; the
lettering is Pretendard Bold (assets/fonts), outlined and thickened to the
weight of the original. Small icons leave the lettering out and enlarge the
page so it still reads in a taskbar.

Writes assets/logo/mark.svg (for the interface), assets/icon/<size>.png and
assets/icon.ico. Needs PySide6 only.
Usage: python scripts/make_logo.py
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import math
import os
import struct
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
BLUE = "#017ADA"         # the tile and the lettering; the interface accent
FOLD = "#A0CFFA"         # the folded corner
PAGE = "#FFFFFF"
BOX = 1024               # viewBox edge
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256, 512)
ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
WORD = "윤DF"


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


def word_path(centre_x, baseline, width):
    """"윤DF" as SVG path data, `width` wide, centred, sitting on `baseline`."""
    from PySide6.QtGui import QFont, QFontDatabase, QPainterPath, QTransform
    QFontDatabase.addApplicationFont(str(ROOT / "assets" / "fonts" / "Pretendard-Bold.otf"))
    font = QFont("Pretendard"); font.setWeight(QFont.Weight.Bold); font.setPixelSize(200)
    path = QPainterPath(); path.addText(0, 0, font, WORD)
    box = path.boundingRect()
    scale = width / box.width()
    path = QTransform().translate(centre_x, baseline).scale(scale, scale).translate(-box.center().x(), 0).map(path)
    data, i = [], 0
    while i < path.elementCount():
        e = path.elementAt(i)
        if e.type == QPainterPath.ElementType.MoveToElement:
            data.append(("Z " if data else "") + f"M{e.x:.2f},{e.y:.2f}"); i += 1
        elif e.type == QPainterPath.ElementType.LineToElement:
            data.append(f"L{e.x:.2f},{e.y:.2f}"); i += 1
        else:
            c1, c2 = path.elementAt(i + 1), path.elementAt(i + 2)
            data.append(f"C{e.x:.2f},{e.y:.2f} {c1.x:.2f},{c1.y:.2f} {c2.x:.2f},{c2.y:.2f}"); i += 3
    return " ".join(data) + " Z", box.height() * scale


def svg(small=False):
    """The mark on a BOX viewBox. Small icons fill the square, drop the
    lettering and enlarge the page."""
    margin = 0 if small else BOX * .035
    tile = BOX - 2 * margin
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {BOX} {BOX}">',
             f'<rect x="{margin:.2f}" y="{margin:.2f}" width="{tile:.2f}" height="{tile:.2f}" rx="{tile * (.2 if small else .19):.2f}" fill="{BLUE}"/>']
    # Proportions measured from the original: the page is half the tile wide.
    pw, ph = tile * (.6 if small else .5055), tile * (.74 if small else .676)
    left = margin + (tile - pw) / 2
    top = margin + tile * (.13 if small else .173)
    right, bottom = left + pw, top + ph
    radius, fold = pw * .127, pw * (.36 if small else .322)
    parts.append(f'<path d="{fillet_path([(left, top), (right - fold, top), (right, top + fold), (right, bottom), (left, bottom)], [radius, pw * .03, pw * .015, radius, radius])}" fill="{PAGE}"/>')
    parts.append(f'<path d="{fillet_path([(right - fold, top), (right, top + fold), (right - fold, top + fold)], [pw * .03, pw * .008, pw * .088])}" fill="{FOLD}"/>')
    if not small:
        word, height = word_path(left + pw / 2, top + ph * .885, pw * .503)
        # Pretendard Bold, thickened by a stroke to the original's heavier weight.
        parts.append(f'<path d="{word}" fill="{BLUE}" fill-rule="nonzero" stroke="{BLUE}" stroke-width="{height * .045:.2f}" stroke-linejoin="round"/>')
    parts.append("</svg>")
    return "".join(parts)


def render(size):
    from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRectF, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    renderer = QSvgRenderer(QByteArray(svg(small=size <= 48).encode()))
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
    (ROOT / "assets" / "logo" / "mark.svg").write_text(svg(), encoding="utf-8")
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
