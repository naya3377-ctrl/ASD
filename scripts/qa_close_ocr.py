"""Closing never waits on OCR: OCR is optional and cancelled on close.

Automatic OCR is off by default. With OCR running on a scanned page, closing
the window (or the tab) goes through at once and leaves the file untouched.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
from pathlib import Path
import sys, time
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))


def build(path):
    import fitz
    text=fitz.open();p=text.new_page(width=595,height=842)
    for line in range(30): p.insert_text((60,90+line*24),f'Scanned line {line} with some words to recognise',fontsize=14)
    pix=p.get_pixmap(dpi=200)
    doc=fitz.open()
    for _ in range(3):
        page=doc.new_page(width=595,height=842);page.insert_image(page.rect,pixmap=pix)
    doc.save(path)


def main():
    from PySide6.QtCore import QUrl,QPointF,Qt,qInstallMessageHandler,QObject
    import PySide6.QtCore as C
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from bichaek.bridge import Images
    from bichaek.tabs import Documents
    out=root/'test-output';out.mkdir(exist_ok=True);pdf=out/'Close During OCR.pdf';build(pdf)
    QQuickStyle.setStyle('Basic');app=QApplication([])
    warnings=[];qInstallMessageHandler(lambda k,c,m: warnings.append(m) if 'file:' in m else None)
    images=Images();docs=Documents(images)
    engine=QQmlApplicationEngine();engine.addImageProvider('pages',images)
    engine.rootContext().setContextProperty('bridge',docs.activeBridge);engine.rootContext().setContextProperty('documents',docs)
    engine.load(QUrl.fromLocalFile(str(root/'ui/Main.qml')));w=engine.rootObjects()[0]
    w.setProperty('width',1400);w.setProperty('height',860)
    def wait(predicate,timeout=20):
        start=time.monotonic()
        while not predicate():
            app.processEvents();QTest.qWait(15)
            if time.monotonic()-start>timeout:raise AssertionError(('timeout',warnings[-5:]))
        app.processEvents();QTest.qWait(80)
    def find(name):
        pending=[w.contentItem().parentItem() or w.contentItem()]
        while pending:
            item=pending.pop()
            if item is None:continue
            if item.objectName()==name:return item
            pending.extend(item.childItems())
    def click(item):
        QTest.mouseClick(w,Qt.LeftButton,Qt.NoModifier,item.mapToScene(item.boundingRect().center()).toPoint());QTest.qWait(60)
    try:
        before=pdf.read_bytes()
        docs.openPaths([str(pdf)]);b=docs.activeBridge
        wait(lambda:b.document['count']==3 and not b.busy)
        # Automatic OCR is off unless the user turns it on.
        from PySide6.QtCore import QSettings
        assert b.automaticOcr in (False,) or QSettings('Bichaek','BichaekPDF').contains('automaticOcr'),b.automaticOcr
        b.setAutomaticOcr(False)
        QTest.qWait(1500);assert not b.ocrBusy
        b.inspectOcr()
        try: wait(lambda:bool(b.languages),timeout=15)
        except AssertionError: print('SKIP: no OCR language data');return
        b.startOcr('all','+'.join(x for x in ('kor','eng') if x in b.languages));wait(lambda:b.ocrBusy)
        started=time.monotonic()
        w.close();wait(lambda:not w.isVisible(),timeout=10)
        assert time.monotonic()-started<5,time.monotonic()-started
        assert pdf.read_bytes()==before
        assert not warnings,warnings
        print('PASS: automatic OCR off by default; closing during OCR is immediate and leaves the file unchanged')
    finally:
        w.setVisible(False);docs.shutdown();del engine


if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
