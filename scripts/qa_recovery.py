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
    QQuickStyle.setStyle('Basic');app=QApplication([])
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
        import shutil
        shutil.copy2(source,second)
        documents.openPaths([str(source),str(second)])
        wait(lambda:all(x.document['count'] and not x.busy for x in documents._tabs))
        documents.activate(0);wait(ready)
        click('editModeButton');wait(lambda:b.blocksAt(0))
        block=b.blocksAt(0)[0];original_command=b.command;late=[]
        def deferred(op,args=None,callback=None,**kwargs):
            if op=='editor_fonts':late.append(callback);return
            return original_command(op,args,callback,**kwargs)
        b.liveEditor.watchdog.setInterval(250)
        with patch.object(b,'command',side_effect=deferred):
            b.editBlock(block);wait(lambda:item('textEditorSession').property('visible'))
            window.close();wait(lambda:item('draftCloseDialog').property('visible'))
            click('continueEditing')
            wait(lambda:not b.liveEditor.loading and '지연' in b.liveEditor.status)
        assert window.isVisible() and len(documents.tabs)==2
        late.pop()({'fonts':[]});assert not b.liveEditor.canApply
        b.liveEditor.watchdog.setInterval(25000)
        click('retryFont');wait(lambda:b.liveEditor.ready and b.liveEditor.canApply)
        from PySide6.QtGui import QInputMethodEvent
        field=item('replacementText');field.forceActiveFocus();QTest.keyClick(window,Qt.Key_End,Qt.ControlModifier)
        pre=QInputMethodEvent('막',[]);QGuiApplication.sendEvent(window.focusObject(),pre);QTest.qWait(100)
        event=QInputMethodEvent();event.setCommitString(' 마지막');QGuiApplication.sendEvent(window.focusObject(),event)
        wait(lambda:b.liveEditor.canUseFallback and not b.liveEditor.loading)
        assert '마지막' in b.liveEditor.doc.toPlainText()
        click('useMissingFont');wait(lambda:b.liveEditor.canApply)
        window.grabWindow().save(str(out/'YoonDF-0.9.2-missing-glyph.png'))
        expected=b.liveEditor.doc.toPlainText()
        window.close();wait(lambda:item('draftCloseDialog').property('visible'))
        window.grabWindow().save(str(out/'YoonDF-0.9.2-close-draft.png'))
        click('continueEditing');assert b.liveEditor.doc.toPlainText()==expected
        window.close();wait(lambda:item('draftCloseDialog').property('visible'))
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Save):
            click('applyDraftClose');wait(lambda:item('closeChoiceDialog').property('visible'))
            click('closeThisTab');wait(lambda:len(documents.tabs)==1 and ready())
        assert window.isVisible()
        with fitz.open(source) as saved:assert '마지막' in saved[0].get_text()
        # The remaining tab is still a clean original. Closing during a stalled
        # font request can discard just the draft and exit without waiting for it.
        current=documents.activeBridge;current.loadBlocks(0);wait(lambda:current.blocksAt(0))
        command=current.command
        def stalled(op,args=None,callback=None,**kwargs):
            if op=='editor_fonts':return
            return command(op,args,callback,**kwargs)
        with patch.object(current,'command',side_effect=stalled):
            current.editBlock(current.blocksAt(0)[0]);wait(lambda:item('textEditorSession').property('visible'))
            window.close();wait(lambda:item('draftCloseDialog').property('visible'))
            assert not item('applyDraftClose').property('enabled')
            click('discardDraftClose');wait(lambda:not window.isVisible())
        with fitz.open(second) as saved:assert '마지막' not in saved[0].get_text()
        assert not errors and not warnings,(errors,warnings)
        print('PASS: stalled font request stays closable, timeout and retry, late response ignored, Hangul preedit/마지막 fallback, continue/apply-save-close active tab/discard-close final window; saved PDF and clean original verified',flush=True)
    finally:
        documents.activeBridge.setAutomaticOcr(saved_auto)
        window.setVisible(False);documents.shutdown();del engine
        qInstallMessageHandler(None)

if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support();main()
