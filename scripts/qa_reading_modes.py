"""Reading modes QA: 읽기 · 주석 · 편집 and focus reading.

The mode bar switches the right-hand panels. Focus reading hides every panel,
fills the screen with the page column on a chosen backdrop, keeps the page,
and returns zoom, mode and window state on Esc.
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
    doc=fitz.open()
    for index in range(8):
        page=doc.new_page(width=595,height=842)
        page.insert_text((60,80),f'Page {index+1} heading',fontsize=22)
        for line in range(30):
            page.insert_text((60,130+line*22),f'Line {line+1}: a paragraph of text to read calmly in focus mode.',fontsize=12)
    page=doc[2];a=page.add_highlight_annot(page.search_for('Line 3:'));a.set_info(content='check this',title='QA');a.update()
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
    out=root/'test-output';out.mkdir(exist_ok=True);pdf=out/'Reading Modes.pdf';build(pdf)
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
    def shown(name):
        item=find(name);return item is not None and item.isVisible()
    try:
        docs.openPaths([str(pdf)]);b=docs.activeBridge;b.setAutomaticOcr(False)
        wait(lambda:b.document['count']==8 and not b.busy)
        # Mode bar
        click(find('commentsModeButton'));wait(lambda:w.property('workspaceMode')=='comments' and shown('commentsDock'))
        wait(lambda:not b.annotationsLoading and len(b.annotations)==1)
        click(find('editModeButton'));wait(lambda:w.property('workspaceMode')=='edit' and not shown('commentsDock') and shown('editTextButton'))
        click(find('readModeButton'));wait(lambda:w.property('workspaceMode')=='read' and not shown('commentsDock') and not shown('editTextButton'))
        click(find('commentsModeButton'));wait(lambda:shown('commentsDock'))
        # Focus reading keeps the page and hides every panel
        C.QMetaObject.invokeMethod(w,'goPage',C.Q_ARG('QVariant',2));wait(lambda:b.currentPage==2)
        zoom=w.property('zoom')
        click(find('focusReadingButton'));wait(lambda:w.property('focusReading'))
        wait(lambda:not shown('readerHeader') and not shown('commentsDock') and not shown('readerFooter'))
        from PySide6.QtGui import QWindow;assert w.visibility()==QWindow.FullScreen,w.visibility()
        wait(lambda:b.currentPage==2)
        assert abs(w.property('zoom')-.62)<.01,w.property('zoom')
        # Column width and backdrop
        w.setProperty('zoom',.5);wait(lambda:abs(w.property('focusWidth')-.5)<.01)
        QTest.mouseMove(w,C.QPoint(int(w.width()/2),w.height()-30));wait(lambda:find('focusBar').property('opacity')==1)
        click(find('focusTone_paper'));assert w.property('focusTone')=='paper'
        w.grabWindow().save(str(out/'focus-reading.png'))
        # Esc returns everything
        QTest.keyClick(w,Qt.Key_Escape);wait(lambda:not w.property('focusReading'))
        wait(lambda:shown('readerHeader') and shown('commentsDock') and w.property('workspaceMode')=='comments')
        assert abs(w.property('zoom')-zoom)<.001 and b.currentPage==2
        # F11 toggles, and the chosen width is remembered
        QTest.keyClick(w,Qt.Key_F11);wait(lambda:w.property('focusReading') and abs(w.property('zoom')-.5)<.01)
        QTest.keyClick(w,Qt.Key_F11);wait(lambda:not w.property('focusReading'))
        assert not warnings,warnings
        print('PASS: read/comments/edit modes switch panels; focus reading hides chrome, keeps page, width and backdrop adjust, Esc/F11 restore')
    finally:
        b._state['dirty']=False;w.setVisible(False);docs.shutdown();del engine


if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
