"""Draw the 윤DF logo and the application icons.

The mark is a seal (낙관): a black sheet with its top-right corner folded
away, like a page, holding 윤 in Nanum Myeongjo. From 48 px up the icon adds
"DF" in YoonDF Display below it. Glyphs are converted to outlines, so the
files do not depend on installed fonts.

Writes assets/logo/mark.svg, assets/logo/mark-inverse.svg (white seal for black
bars), assets/icon.svg, assets/icon/<size>.png and assets/icon.ico.

Usage: python scripts/make_logo.py [HANGUL_FONT]
  HANGUL_FONT defaults to assets/fonts/NanumMyeongjo-Bold.ttf; the release
  logo uses NanumMyeongjo-ExtraBold.ttf from the same OFL family.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import struct
import sys
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
SHEET = "M0 0H100L128 28V128H0Z"   # a 128 unit page with its corner folded away
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def outline(font_path, text, size, x=0.0, baseline=0.0, tracking=0.0):
    """SVG path data and bounds for `text` set at `size` units per em."""
    font = TTFont(font_path)
    glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
    scale = size / font["head"].unitsPerEm
    pen, bounds = SVGPathPen(glyphs), BoundsPen(glyphs)
    for char in text:
        glyph = glyphs[cmap[ord(char)]]
        for target in (pen, bounds):
            glyph.draw(TransformPen(target, (scale, 0, 0, -scale, x, baseline)))
        x += glyph.width * scale + tracking
    return pen.getCommands(), bounds.bounds


def placed(font_path, text, box, centre, tracking=0.0):
    """Outline of `text` scaled to fit `box` (w, h) and centred on `centre`."""
    _, (x0, y0, x1, y1) = outline(font_path, text, 100, tracking=tracking)
    scale = min(box[0] / (x1 - x0), box[1] / (y1 - y0))
    _, (x0, y0, x1, y1) = outline(font_path, text, 100 * scale, tracking=tracking * scale)
    return outline(font_path, text, 100 * scale, centre[0] - (x0 + x1) / 2, centre[1] - (y0 + y1) / 2, tracking * scale)[0]


def svg(hangul, sheet="#000", ink="#fff", initials=False):
    if initials:
        yoon = placed(hangul, "윤", (78, 70), (64, 55))
        df = placed(FONTS / "YoonDFDisplay-Black.ttf", "DF", (40, 20), (64, 108), tracking=4)
        glyphs = f'<path d="{yoon}" fill="{ink}"/><path d="{df}" fill="{ink}"/>'
    else:
        glyphs = f'<path d="{placed(hangul, "윤", (90, 86), (63, 67))}" fill="{ink}"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">'
            f'<path d="{SHEET}" fill="{sheet}"/>{glyphs}</svg>\n')


def png(source, size):
    from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRectF, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(QByteArray(source.encode())).render(painter, QRectF(0, 0, size, size))
    painter.end()
    data = QByteArray(); buffer = QBuffer(data); buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def ico(images):
    """A Windows icon holding PNG images (supported since Windows Vista)."""
    header = struct.pack("<HHH", 0, 1, len(images))
    offset, entries, blobs = 6 + 16 * len(images), b"", b""
    for size, data in images:
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset)
        blobs += data; offset += len(data)
    return header + entries + blobs


def main(hangul):
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    (ROOT / "assets" / "logo").mkdir(exist_ok=True)
    (ROOT / "assets" / "icon").mkdir(exist_ok=True)
    mark, full = svg(hangul), svg(hangul, initials=True)
    (ROOT / "assets" / "logo" / "mark.svg").write_text(mark, encoding="utf-8")
    (ROOT / "assets" / "logo" / "mark-inverse.svg").write_text(svg(hangul, sheet="#fff", ink="#000"), encoding="utf-8")
    (ROOT / "assets" / "icon.svg").write_text(full, encoding="utf-8")
    images = []
    for size in SIZES:
        data = png(full if size >= 48 else mark, size)
        images.append((size, data))
        if size in (16, 24, 32, 48, 64, 128, 256):
            (ROOT / "assets" / "icon" / f"{size}.png").write_bytes(data)
    (ROOT / "assets" / "icon.ico").write_bytes(ico(images))
    del app


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else FONTS / "NanumMyeongjo-Bold.ttf")
