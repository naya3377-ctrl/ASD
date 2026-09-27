"""Record the interface motion of the real window as docs/motion.gif.

Plays, in real time: the start mark's one-time fade, a toolbar press, the
sidebar closing and opening, the comment mode (segment glide and the comment
panel), the ⋯ menu opening and closing, and the return to reading. Frames are
grabbed from the running app, so the clip shows exactly what the app does.
Needs Pillow (tools only; the app does not use it).
Usage: python scripts/record_motion.py
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen'); os.environ.setdefault('QT_QUICK_BACKEND', 'software')
from pathlib import Path
import sys, time
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
SCALE = .6


def main():
    import fitz
    from PIL import Image
    from PySide6.QtCore import QUrl, QObject, Qt, QByteArray
    from PySide6.QtGui import QFont, QFontDatabase, QImage
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from bichaek.bridge import Images
    from bichaek.tabs import Documents
    from bichaek.typefaces import install
    out = root / 'test-output'; out.mkdir(exist_ok=True); source = out / '전시 서문 초안.pdf'
    with fitz.open() as pdf:
        for index in range(4):
            page = pdf.new_page(width=595, height=842); page.insert_font(fontname='K', fontbuffer=fitz.Font('korea').buffer)
            page.insert_text((72, 110), '전시 서문' if index == 0 else f'{index}. 작품 해설', fontname='K', fontsize=22)
            for line in range(14):
                page.insert_text((72, 170 + line * 28), f'작가는 재료의 시간을 화면 위에 겹쳐 둔다 {line + 1}', fontname='K', fontsize=12)
        first = pdf[0]
        mark = first.add_highlight_annot(first.search_for('작가는 재료의 시간을 화면 위에 겹쳐 둔다 2')[0])
        mark.set_info(content='도록 표기와 맞춰 주세요.', title='큐레이터'); mark.update()
        pdf.subset_fonts(); pdf.save(source)
    QQuickStyle.setStyle('Basic'); app = QApplication([])
    install(root / 'assets' / 'fonts'); app.setFont(QFont('Pretendard', 10))
    QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font('korea').buffer))
    images = Images(); documents = Documents(images); b = documents.activeBridge
    saved = (b.automaticOcr, b.reduceMotion, b.themeMode)
    b.setAutomaticOcr(False); b.setReduceMotion(False); b.setThemeMode('light')
    engine = QQmlApplicationEngine(); engine.addImageProvider('pages', images)
    engine.addImageProvider('icon', __import__('bichaek.icons', fromlist=['Icons']).Icons(root / 'assets' / 'icons'))
    ctx = engine.rootContext(); ctx.setContextProperty('bridge', b); ctx.setContextProperty('documents', documents); ctx.setContextProperty('iconTint', True)
    frames = []   # [image, grabbed at, fixed seconds or None]

    def grab(fixed=None):
        image = w.grabWindow().convertToFormat(QImage.Format.Format_RGB888)
        pil = Image.frombytes('RGB', (image.width(), image.height()), bytes(image.constBits()), 'raw', 'RGB', image.bytesPerLine())
        frames.append([pil.resize((round(pil.width * SCALE), round(pil.height * SCALE)), Image.LANCZOS), time.monotonic(), fixed])

    def film(seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            grab(); app.processEvents(); QTest.qWait(8)

    def hold(seconds):
        app.processEvents(); grab(seconds)

    def item(name):
        pending = [w.contentItem()]
        while pending:
            obj = pending.pop()
            if obj.objectName() == name: return obj
            pending.extend(obj.childItems())
        return w.findChild(QObject, name)

    def centre(obj): return obj.mapToScene(obj.boundingRect().center()).toPoint()

    engine.load(QUrl.fromLocalFile(str(root / 'ui/Main.qml')))
    w = engine.rootObjects()[0]; w.setProperty('width', 1320); w.setProperty('height', 900)
    try:
        film(.6); hold(.7)                                        # the start mark fades in once
        documents.openPaths([str(source)])
        c = documents.activeBridge
        while not (c.document.get('count') == 4 and c.imageUrl(0, 'main') and not w.property('restoring')):
            app.processEvents(); QTest.qWait(20)
        QTest.qWait(400); hold(.8)
        # A toolbar press: the content shrinks a touch, the sidebar closes.
        target = centre(item('sidebarButton'))
        QTest.mouseMove(w, target); film(.15)
        QTest.mousePress(w, Qt.LeftButton, Qt.NoModifier, target); film(.1)
        QTest.mouseRelease(w, Qt.LeftButton, Qt.NoModifier, target); film(.45); hold(.5)
        QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, target); film(.45); hold(.5)
        # Comment mode: the segment glides, the list opens beside the page.
        QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, centre(item('commentsModeButton'))); film(.6); hold(.8)
        # The ⋯ menu opens and closes.
        QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, centre(item('moreButton'))); film(.4); hold(.6)
        QTest.keyClick(w, Qt.Key_Escape); film(.3); hold(.3)
        # Back to reading.
        QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, centre(item('readModeButton'))); film(.5); hold(1.0)
        # One shared palette keeps the file small and the colours steady.
        sheet = Image.new('RGB', (frames[0][0].width, frames[0][0].height * 4))
        for i, k in enumerate((0, len(frames) // 3, 2 * len(frames) // 3, len(frames) - 1)):
            sheet.paste(frames[k][0], (0, i * frames[0][0].height))
        palette = sheet.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
        images_out = [f[0].quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
        # Real time between grabs; held frames keep their pause. Browsers slow
        # frames under 20 ms, so none is shorter.
        durations = []
        for i, (_, at, fixed) in enumerate(frames):
            seconds = fixed if fixed is not None else (frames[i + 1][1] - at if i + 1 < len(frames) else .5)
            durations.append(max(20, round(seconds * 100) * 10))
        target_path = root / 'docs' / 'motion.gif'
        images_out[0].save(target_path, save_all=True, append_images=images_out[1:], duration=durations, loop=0, optimize=True)
        print(target_path.relative_to(root), len(frames), 'frames', round(sum(durations) / 1000, 1), 's', target_path.stat().st_size // 1024, 'KB')
    finally:
        active = documents.activeBridge
        active.setAutomaticOcr(saved[0]); active.setReduceMotion(saved[1]); active.setThemeMode(saved[2])
        w.setVisible(False); documents.shutdown(); del engine


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support(); main()
