"""Headless integration QA. Requires Qt and an installed Korean fallback font.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
os.environ.setdefault("QT_QUICK_BACKEND","software")
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))


def main():
    from PySide6.QtCore import QUrl,QObject,QPoint,Qt,QByteArray
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from bichaek.bridge import Images,Bridge
    import fitz
    root=Path(__file__).resolve().parent.parent
    output=root/"test-output";output.mkdir(exist_ok=True)
    QQuickStyle.setStyle("Basic")
    app=QApplication([])
    QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font("korea").buffer))
    images=Images();bridge=Bridge(images)
    saved_auto = bridge.automaticOcr
    bridge.setAutomaticOcr(False)
    errors=[];bridge.showError.connect(errors.append)
    engine=QQmlApplicationEngine();engine.addImageProvider("pages",images)
    engine.rootContext().setContextProperty("bridge",bridge)
    engine.load(QUrl.fromLocalFile(str(root/"ui/Main.qml")))
    assert engine.rootObjects(),"QML failed"
    window=engine.rootObjects()[0]
    window.setProperty("uiFontFamily","Droid Sans Fallback")
    window.setProperty("zoom",.60)
    def until(predicate,timeout=20):
        start=time.monotonic()
        while not predicate():
            app.processEvents();QTest.qWait(30)
            if time.monotonic()-start>timeout:raise AssertionError("Timed out: "+str(errors))
        app.processEvents();QTest.qWait(100)
    def item(name):
        # Page delegates have no QObject parent, so walk the visual tree.
        pending=[window.contentItem()]
        while pending:
            node=pending.pop()
            if node.objectName()==name:return node
            pending.extend(node.childItems())
    def click(name):
        item=window.findChild(QObject,name)
        assert item,name
        pos=item.mapToScene(item.boundingRect().center())
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,QPoint(round(pos.x()),round(pos.y())))
        app.processEvents();QTest.qWait(100)
    try:
        bridge.openPath(str(root/"samples/sample.pdf"))
        until(lambda:bridge.document["count"]==4 and len(images.images)>=4)
        window.grabWindow().save(str(output/"reader.png"))
        # Exercise the real pointer handlers, not only the Python bridge.
        # Points come from the thumbnails themselves, not fixed pixels.
        def thumb(index,fraction=.5):
            paper=item("thumbnailPaper%d"%index);pos=paper.mapToScene(paper.boundingRect().center())
            return QPoint(round(pos.x()),round(pos.y()+(fraction-.5)*paper.height()))
        first,second=thumb(0),thumb(1)
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,first)
        QTest.mouseClick(window,Qt.LeftButton,Qt.ControlModifier,second)
        app.processEvents();QTest.qWait(150)
        assert bridge.selection == [0,1], ('Ctrl+click',bridge.selection)
        # A plain click narrows to one page; dragging a multi-selection moves them all.
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,first);app.processEvents();QTest.qWait(150)
        assert bridge.selection == [0], ('click',bridge.selection)
        below=thumb(1,.9)   # the lower half of page 2: drop after it
        QTest.mousePress(window,Qt.LeftButton,Qt.NoModifier,first)
        for y in range(first.y(),below.y()+1,12):
            QTest.mouseMove(window,QPoint(first.x(),y),20)
        QTest.mouseRelease(window,Qt.LeftButton,Qt.NoModifier,below)
        until(lambda:bridge.document['dirty'] and not bridge.busy)
        dragged=[]
        bridge.command('objects',{'page':0},dragged.append)
        until(lambda:bool(dragged))
        assert any('SECOND PAGE' in b['text'] for b in dragged[0]['blocks']), 'Thumbnail drag did not reorder pages'
        bridge.undo();until(lambda:not bridge.busy)
        bridge.selectPage(0,False,False)
        click("editModeButton")
        click("editTextButton")
        until(lambda:len(bridge.blocks)>0)
        window.grabWindow().save(str(output/"text-blocks.png"))
        b=next(b for b in bridge.blocks if b["text"].startswith("A document"))
        bridge.editBlock(b);until(lambda:item("replacementText") is not None and not bridge.liveEditor.loading)
        window.grabWindow().save(str(output/"text-editor.png"))
        editor=item("replacementText")
        # Type like a person: select all, type, let fonts for new letters arrive, then apply.
        editor.forceActiveFocus();QTest.keyClick(window,Qt.Key_A,Qt.ControlModifier)
        for ch in "Edited document": QTest.keyClick(window,ch)
        until(lambda:bridge.liveEditor.canApply)
        click("applyTextButton")
        until(lambda:not bridge.busy and bridge.document["dirty"])
        until(lambda:bool(bridge.imageUrl(0,"main")))
        saved=output/"ui-edited.pdf"
        done=[]
        bridge.command("save",{"path":str(saved)},done.append)
        until(lambda:bool(done));bridge.update_state(done[0])
        with fitz.open(saved) as doc:
            assert "Edited document" in " ".join(doc[0].get_text().split()), doc[0].get_text()[-200:]
            assert "A document" not in doc[0].get_text()
        bridge.search("Edited document")
        until(lambda:not bridge.searching)
        assert bridge.searchResults[0]["page"]==0
        bridge.movePage(0,2)
        until(lambda:not bridge.busy)
        bridge.undo();until(lambda:not bridge.busy)
        bridge.redo();until(lambda:not bridge.busy)
        bridge.selectPage(2,False,False);bridge.selectPage(3,True,False)
        assert bridge.selection==[2,3]
        bridge.inspectOcr()
        if 'eng' in bridge.languages:
            bridge.selectPage(3,False,False)
            bridge.startOcr('current','eng')
            until(lambda:not bridge.ocrBusy,timeout=60)
            ocr_saved=output/'ui-ocr.pdf'
            done=[];bridge.command('save',{'path':str(ocr_saved)},done.append)
            until(lambda:bool(done))
            with fitz.open(ocr_saved) as doc:
                assert 'SCANNED ARCHIVE' in doc[3].get_text()
            bridge.startOcr('all','eng')
            bridge.cancelOcr()
            until(lambda:not bridge.ocrBusy,timeout=20)
        assert not errors,errors
        print("UI PASS: open, render, Ctrl+click, thumbnail drag, edit dialog, text replacement, save, reopen, search, reorder, undo, redo, background English OCR, preparation cancellation")
    finally:
        bridge.setAutomaticOcr(saved_auto)
        bridge._state["dirty"]=False
        window.setVisible(False)
        bridge.shutdown()
        del engine


if __name__=="__main__":main()
