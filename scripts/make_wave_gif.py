"""Record the character's hello (ui/WavingCharacter.qml) as an animated GIF.

The frames are grabbed from the real QML animation on white, so the GIF shows
exactly what the start screen plays. Writes docs/wave.gif.
Needs Pillow (tools only; the app does not use it).
Usage: python scripts/make_wave_gif.py
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
from pathlib import Path
import time
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
QML = b"""
import QtQuick
import "../ui"
Rectangle {
    width: 300; height: 330; color: "white"
    WavingCharacter { id: c; objectName: "c"; playOnShow: false; height: 300; width: height/ratio; anchors.centerIn: parent; anchors.verticalCenterOffset: 6 }
}
"""


def main():
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuick import QQuickView
    from PySide6.QtTest import QTest
    app = QGuiApplication.instance() or QGuiApplication([])
    view = QQuickView()
    source = ROOT / "test-output" / "wave-preview.qml"
    source.parent.mkdir(exist_ok=True)
    source.write_bytes(QML)
    view.setSource(QUrl.fromLocalFile(str(source)))
    assert not view.errors(), [e.toString() for e in view.errors()]
    view.show(); QTest.qWait(300)
    character = view.rootObject().childItems()[0]
    frames, step = [], 40
    character.wave(); started = time.monotonic()
    while character.property("playing") or time.monotonic() - started < .2:
        frames.append(view.grabWindow())
        QTest.qWait(step)
    for _ in range(12):   # hold the last pose for half a second
        frames.append(frames[-1])
    from PySide6.QtGui import QImage
    images = []
    for frame in frames:
        frame = frame.convertToFormat(QImage.Format.Format_RGB888)
        images.append(Image.frombytes("RGB", (frame.width(), frame.height()), bytes(frame.constBits()), "raw", "RGB", frame.bytesPerLine()))
    # One shared palette, taken from poses across the whole wave, keeps the
    # file small and stops the colours flickering from frame to frame.
    sheet = Image.new("RGB", (images[0].width * 8, images[0].height), "white")
    for i in range(8):
        sheet.paste(images[i * (len(images) - 1) // 7], (i * images[0].width, 0))
    palette = sheet.quantize(colors=96, method=Image.Quantize.MEDIANCUT)
    images = [image.quantize(palette=palette, dither=Image.Dither.NONE) for image in images]
    out = ROOT / "docs" / "wave.gif"
    images[0].save(out, save_all=True, append_images=images[1:], duration=step, loop=0, optimize=True)
    print(out.relative_to(ROOT), len(images), "frames", out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
