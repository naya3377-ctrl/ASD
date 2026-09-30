"""Pointer-level tab, facing-page, markup, image and font regression QA.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
from pathlib import Path
import sys, time
root=Path(os.environ.get('YOONDF_QA_SOURCE',Path(__file__).resolve().parent.parent))
sys.path.insert(0,str(root))


def main():
    import fitz
    from unittest.mock import patch
    from PySide6.QtCore import QUrl,QObject,Qt,QByteArray,QPointF,qInstallMessageHandler
    from PySide6.QtGui import QFontDatabase,QImage,QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
    from PySide6.QtTest import QTest
    from bichaek.bridge import Images
    from bichaek.tabs import Documents
    out=root/'test-output';out.mkdir(exist_ok=True)
    source=out/'Direct Editing Review.pdf';second=out/'Second Tab.pdf';png=out/'Transparent Image.png'
    pix=fitz.Pixmap(fitz.csRGB,fitz.IRect(0,0,160,80),True)
    pix.set_rect(pix.irect,(40,80,120,160));pix.save(png)
    from tests.test_inline_fonts import subset_fixture
    subset_fixture(source,multi=True)
    QQuickStyle.setStyle(os.environ.get('YOONDF_QA_STYLE','Basic'));app=QApplication([])
    QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font('korea').buffer))
    warnings=[]
    def log(kind,context,message):
        if 'file:' in message or 'ReferenceError' in message or 'TypeError' in message:warnings.append(message)
    qInstallMessageHandler(log)
    images=Images();documents=Documents(images);b=documents.activeBridge
    saved_auto=b.automaticOcr;b.setAutomaticOcr(False)
    errors=[];documents.showError.connect(errors.append)
    engine=QQmlApplicationEngine();engine.addImageProvider('pages',images)
    engine.rootContext().setContextProperty('bridge',b);engine.rootContext().setContextProperty('documents',documents)
    engine.load(QUrl.fromLocalFile(str(root/'ui/Main.qml')))
    assert engine.rootObjects(),warnings
    window=engine.rootObjects()[0];window.setProperty('uiFontFamily','Droid Sans Fallback')
    def wait(predicate,timeout=30):
        started=time.monotonic()
        while not predicate():
            app.processEvents();QTest.qWait(20)
            if time.monotonic()-started>timeout:raise AssertionError(('timeout',errors,warnings[-10:]))
        app.processEvents();QTest.qWait(100)
    retained=[]
    def keep(obj):
        retained.append(obj)
        return obj
    def item(name):
        if name.startswith('pageContextMenu'):
            value=item('textLayer'+name.removeprefix('pageContextMenu')).findChild(QObject,name)
            if value:return keep(value)
        if name.endswith('MenuItem'):
            value=item('pageContextMenu0').findChild(QObject,name)
            if value:return keep(value)
        pending=[window.contentItem()]
        while pending:
            obj=pending.pop()
            if obj.objectName()==name:return keep(obj)
            pending.extend(obj.childItems())
        obj=window.findChild(QObject,name)
        if obj:return keep(obj)
        raise AssertionError(name)
    def click(name):
        obj=item(name);point=obj.mapToScene(obj.boundingRect().center())
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point.toPoint());QTest.qWait(100)
    def ready():return not window.property('switching') and not window.property('restoring')
    def right_at(x,y):
        layer=item('textLayer0');factor=layer.property('factor')
        point=layer.mapToScene(QPointF(x*factor,y*factor))
        QTest.mouseClick(window,Qt.RightButton,Qt.NoModifier,point.toPoint())
        wait(lambda:item('pageContextMenu0').property('visible'))
    def drag(a,z,modifiers=Qt.NoModifier):
        QTest.mousePress(window,Qt.LeftButton,modifiers,a.toPoint())
        for i in range(1,15):QTest.mouseMove(window,(a+(z-a)*(i/14)).toPoint(),20)
        QTest.mouseRelease(window,Qt.LeftButton,modifiers,z.toPoint());QTest.qWait(100)
    def page_point(page,x,y):
        paper=item('paper'+str(page));return paper.mapToScene(QPointF(x*paper.width()/b.pageWidth(page),y*paper.width()/b.pageWidth(page)))
    def close_rect(a,z):
        assert all(abs(x-y)<2 for x,y in zip(a,z)),(a,z)
    try:
        window.resize(1450,1000)
        documents.openPaths([str(source)])
        wait(lambda:b.document['count']==1 and not b.busy and ready())
        click('editModeButton');click('editTextButton')
        wait(lambda:b.blocksAt(0))
        block=b.blocksAt(0)[0];pos=page_point(0,80,60)
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,pos.toPoint())
        wait(lambda:b.liveEditor.ready)
        assert b.fontOptions[b.fontChoiceIndex]['key']=='original'
        initial=b.liveEditor.height
        # Compare the actual document attached to the visible editor against
        # original PDF character origins, before any key has been pressed.
        assert len(block['textLines'])==2
        qblock=b.liveEditor.doc.begin()
        for line in block['textLines']:
            layout=qblock.layout();assert layout.lineCount()==1
            qline=layout.lineAt(0);index=0
            for run in line['runs']:
                for char in run['chars']:
                    x=layout.position().x()+qline.cursorToX(index)[0]+block['rect'][0]
                    y=layout.position().y()+qline.y()+qline.ascent()+b.liveEditor.offset+block['rect'][1]
                    assert abs(x-char['origin'][0])<.08 and abs(y-char['origin'][1])<.08,(char,x,y)
                    index+=len(char['c'].encode('utf-16-le'))//2
            qblock=qblock.next()
        window.grabWindow().save(str(out/'YoonDF-0.9.1-original-layout.png'))
        # Real IME commit on the bound document, including unavailable new glyphs.
        from PySide6.QtGui import QInputMethodEvent
        field=item('replacementText');field.forceActiveFocus();QTest.keyClick(window,Qt.Key_End,Qt.ControlModifier)
        event=QInputMethodEvent();event.setCommitString(' 새로운 글자')
        QGuiApplication.sendEvent(window.focusObject(),event)
        wait(lambda:not b.liveEditor.canApply and '새' in b.liveEditor.doc.toPlainText())
        QTest.qWait(700)
        assert not errors and item('inlineFontStatus').property('visible')
        assert item('textEditorSession').property('visible')
        # Pick a full font once; then find it by its Korean filename in the popup.
        full=out/'한글시험.ttf';full.write_bytes(fitz.Font('korea').buffer)
        with patch.object(QFileDialog,'getOpenFileName',return_value=(str(full),'TTF')):b.chooseFont()
        wait(lambda:b.liveEditor.canApply)
        field.forceActiveFocus();QTest.keyClick(window,Qt.Key_End,Qt.ControlModifier)
        text=' 가나다라 원본 글꼴 ABC'*9
        event=QInputMethodEvent();event.setCommitString(text);QGuiApplication.sendEvent(window.focusObject(),event)
        wait(lambda:b.liveEditor.height>initial*2)
        assert b.liveEditor.doc.toPlainText().endswith(text)
        picker=item('fontChoice');point=picker.mapToScene(picker.boundingRect().center());QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point.toPoint())
        wait(lambda:item('fontSearchPopup').property('visible'))
        item('fontSearchInput').setProperty('text','한글시험')
        wait(lambda:item('fontSearchResults').property('count')==1)
        window.grabWindow().save(str(out/'YoonDF-0.9.1-font-search.png'))
        click('fontResult0');wait(lambda:not item('fontSearchPopup').property('visible') and b.liveEditor.canApply)
        assert b._font_path==str(full)
        click('fontChoice');wait(lambda:item('fontSearchPopup').property('visible'))
        QTest.keyClick(window,Qt.Key_Escape);wait(lambda:not item('fontSearchPopup').property('visible'))
        assert item('textEditorSession').property('visible') and b.liveEditor.canApply
        before=b.liveEditor.height;b.liveEditor.setWidth(b.liveEditor.width+80);QTest.qWait(150)
        assert b.liveEditor.height<before
        # Capture actual live document before applying; PDF uses these very lines.
        expected=b.liveEditor.doc.toPlainText()
        window.grabWindow().save(str(out/'YoonDF-0.9.1-live-text.png'))
        click('applyTextButton');wait(lambda:not b.busy and not item('textEditorSession').property('visible'))
        b.save(False);wait(lambda:not b.busy and not b.document['dirty'])
        with fitz.open(source) as saved:
            assert ''.join(saved[0].get_text().split())==''.join(expected.split())
        assert not errors and not warnings,(errors,warnings)
        print('PASS: multiline Korean subset keeps every original character origin within 0.08pt in attached UI; IME edits, inline missing glyph notice, full-font recovery, Korean font search, live height/width reflow, saved text',flush=True)
    finally:
        documents.activeBridge.setAutomaticOcr(saved_auto)
        window.setVisible(False);documents.shutdown();del engine
        qInstallMessageHandler(None)

if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support();main()
