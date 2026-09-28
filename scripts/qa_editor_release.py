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
    source=out/'Editor Review.pdf';second=out/'Second Tab.pdf';png=out/'Transparent Image.png'
    pix=fitz.Pixmap(fitz.csRGB,fitz.IRect(0,0,160,80),True)
    pix.set_rect(pix.irect,(40,80,120,160));pix.save(png)
    with fitz.open() as doc:
        for i in range(5):
            p=doc.new_page(width=600 if i!=3 else 700,height=800 if i!=3 else 900)
            p.insert_font(fontname='Original',fontbuffer=fitz.Font('tiro').buffer)
            p.insert_text((40,70),'ORIGINAL TEXT FOR REVIEW',fontname='Original',fontsize=20)
            p.insert_text((40,350),f'Facing Needle {i+1}',fontname='Original',fontsize=18)
            if i==0:p.insert_image([60,150,300,270],filename=str(png))
        doc.save(source);doc.save(second)
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
    try:
        documents.openPaths([str(source),str(second)])
        wait(lambda:all(x.document['count'] and not x.busy for x in documents._tabs) and ready())
        strip=item('documentTabs')
        assert strip.property('currentIndex')==documents.activeIndex,(strip.property('currentIndex'),documents.activeIndex)
        # Press a real delegate, force many asynchronous state changes, release.
        tab=item('documentTab0');point=tab.mapToScene(QPointF(70,20))
        QTest.mousePress(window,Qt.LeftButton,Qt.NoModifier,point.toPoint())
        for _ in range(12):
            documents.activeBridge.stateChanged.emit();QTest.qWait(20)
        QTest.mouseRelease(window,Qt.LeftButton,Qt.NoModifier,point.toPoint())
        wait(lambda:documents.activeIndex==0 and ready())
        assert strip.property('currentIndex')==0
        assert item('documentTab0') is tab,'Live tab delegate was recreated'
        for n in [1,0,1,0]:
            tab=item('documentTab'+str(n));point=tab.mapToScene(QPointF(70,20))
            QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point.toPoint())
            wait(lambda:documents.activeIndex==n and ready())
            assert strip.property('currentIndex')==n
        print('PASS: real tab press/state updates/release and rapid clicks; active document, title and strip agree',flush=True)
        if '--tabs-only' in sys.argv:return
        # Facing pages through the actual view-mode selector.
        mode=item('pageViewMode');mode.forceActiveFocus()
        QTest.keyClick(window,Qt.Key_Down);QTest.keyClick(window,Qt.Key_Return)
        wait(lambda:window.property('twoPageView') and ready())
        paper0=item('paper0');paper1=item('paper1')
        p0=paper0.mapToScene(QPointF(0,0));p1=paper1.mapToScene(QPointF(0,0))
        assert abs(p0.y()-p1.y())<1 and p1.x()>=p0.x()+paper0.width()
        item('pageList').forceActiveFocus();QTest.keyClick(window,Qt.Key_Right)
        wait(lambda:b.currentPage==2 and ready())
        b.search('Facing Needle 4');wait(lambda:not b.searching and b.currentPage==3 and ready())
        paper=item('paper3');hit=b.activeSearchHit;factor=paper.width()/b.pageWidth(3)
        pos=paper.mapToItem(item('pageList'),QPointF(hit['rect'][0]*factor,hit['rect'][1]*factor))
        assert 0<=pos.y()<item('pageList').height() and 0<=pos.x()<item('pageList').width(),pos
        item('pageList').forceActiveFocus();QTest.keyClick(window,Qt.Key_End)
        wait(lambda:b.currentPage==4 and ready())
        last=item('paper4');assert last.width()<item('pageList').width()*.55
        documents.activate(1);wait(ready);assert not window.property('twoPageView')
        documents.activate(0);wait(ready);assert window.property('twoPageView') and b.currentPage==4
        QTest.keyClick(window,Qt.Key_F5);wait(lambda:window.property('presenting'))
        QTest.keyClick(window,Qt.Key_Escape);wait(lambda:not window.property('presenting') and ready())
        assert window.property('twoPageView')
        b.search('');b.navigateRequested.emit(0,0,0);wait(lambda:b.currentPage==0 and ready())
        window.grabWindow().save(str(out/'YoonDF-0.8.0-facing.png'))
        mode.forceActiveFocus();QTest.keyClick(window,Qt.Key_Up);QTest.keyClick(window,Qt.Key_Return)
        wait(lambda:not window.property('twoPageView') and ready())
        print('PASS: two-page layout, paired keys, right-page search, odd last page, per-tab state and slideshow return',flush=True)
        # Highlight never composes a note or opens the comment sidebar.
        wait(lambda:b.textLayout(0).get('chars'))
        b.selectCharacters(0,0,8);right_at(100,62);click('highlightMenuItem')
        wait(lambda:not b.busy and b.document['dirty'])
        assert window.property('workspaceMode')=='read'
        assert not item('annotationEditor').property('visible')
        assert b.pageAnnotations(0)[0]['type']=='Highlight'
        # Sticky highlighter remains the selected tool and can be used twice.
        window.setProperty('tool','highlight')
        for start in [9,14]:
            b.selectCharacters(0,start,start+4);b.annotateSelection('highlight');wait(lambda:not b.busy)
            assert window.property('tool')=='highlight' and window.property('workspaceMode')=='read'
        window.setProperty('tool','read')
        right_at(400,290);click('addMemoMenuItem')
        wait(lambda:item('annotationEditor').property('visible'))
        item('commentBody').setProperty('text','각주는 형광펜과 별도 메모입니다.');click('applyComment')
        wait(lambda:not b.busy and not item('annotationEditor').property('visible'))
        assert len([a for a in b.annotations if a['type']=='Text'])==1
        click('readModeButton')
        print('PASS: right-click highlight leaves reading mode; sticky markup stays active; separate right-click memo',flush=True)
        # Image copy is actual pixel data, not a path or a page screenshot.
        wait(lambda:b.textLayout(0).get('images'))
        right_at(170,200);click('copyImageMenuItem')
        wait(lambda:QGuiApplication.clipboard().image().width()==160)
        copied=QGuiApplication.clipboard().image();assert copied.height()==80 and copied.hasAlphaChannel()
        assert copied.pixelColor(0,0).alpha()==160
        export=out/'Exported image.png'
        with patch.object(QFileDialog,'getSaveFileName',return_value=(str(export),'PNG')):
            right_at(170,200);click('saveImageMenuItem');wait(export.exists)
        saved=QImage(str(export));assert saved==copied
        click('editModeButton')
        old=len(b.textLayout(0)['images'])
        with patch.object(QFileDialog,'getOpenFileName',return_value=(str(png),'PNG')) as picker:
            click('insertImageButton');wait(lambda:not b.busy and len(b.textLayout(0).get('images',[]))==old+1)
            picker.assert_called_once()
        print('PASS: image context copy/save native 160×80 alpha pixels; insertion button opens picker and renders inserted image',flush=True)
        # Original font by default; failed new glyph retains the draft; user chooses Korean font.
        b.loadBlocks(0);wait(lambda:len(b.blocks)>0)
        block=next(x for x in b.blocks if x['text'].startswith('ORIGINAL'))
        b.editBlock(block);wait(lambda:item('textEditorSession').property('visible') and b.liveEditor.ready)
        assert b.fontOptions[b.fontChoiceIndex]['key']=='original'
        item('replacementText').setProperty('text','REVISED TEXT');click('applyTextButton')
        wait(lambda:not b.busy and not item('textEditorSession').property('visible'))
        b.loadBlocks(0);wait(lambda:any(x['text'].startswith('REVISED') for x in b.blocks))
        block=next(x for x in b.blocks if x['text'].startswith('REVISED'))
        assert 'NimbusRoman' in block['font'],block
        b.editBlock(block);wait(lambda:item('textEditorSession').property('visible') and b.liveEditor.ready)
        item('replacementText').setProperty('text','한글 본문 수정')
        wait(lambda:not b.liveEditor.canApply and bool(b.liveEditor.status))
        QTest.qWait(500)
        assert not errors and item('textEditorSession').property('visible') and b.liveEditor.doc.toPlainText()=='한글 본문 수정'
        fontpath=out/'Korean.ttf';fontpath.write_bytes(fitz.Font('korea').buffer)
        with patch.object(QFileDialog,'getOpenFileName',return_value=(str(fontpath),'TTF')):b.chooseFont()
        wait(lambda:b.liveEditor.canApply);assert item('fontChoice').property('currentIndex')==b.fontChoiceIndex
        click('applyTextButton');wait(lambda:not b.busy and not item('textEditorSession').property('visible'))
        b.save(False);wait(lambda:not b.busy and not b.document['dirty'])
        with fitz.open(source) as saved_pdf:
            assert '한글 본문 수정' in saved_pdf[0].get_text()
            assert len(saved_pdf[0].get_image_info())==2
            types=[a.type[1] for a in saved_pdf[0].annots()]
            assert types.count('Highlight')==3 and types.count('Text')==1,types
        assert not errors and not warnings,(errors,warnings)
        print('PASS: original embedded font retained; missing glyph draft retained; selected Korean font and images/markups persist after PDF reopen',flush=True)
        # With several tabs, window X asks: this tab only, or all of them.
        b.edit('add_text',{'page':0,'rect':[40,600,440,650],'text':'CLOSE TAB SAVE','size':16})
        wait(lambda:not b.busy)
        choice=window.findChild(QObject,'closeChoiceDialog')
        assert not window.close();wait(lambda:choice.property('visible'))
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Cancel):
            click('closeThisTab')
        assert len(documents.tabs)==2 and window.isVisible() and not choice.property('visible')
        assert not window.close();wait(lambda:choice.property('visible'))
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Save):
            click('closeThisTab')
            wait(lambda:len(documents.tabs)==1 and ready())
        assert window.isVisible()
        with fitz.open(source) as saved_pdf:assert 'CLOSE TAB SAVE' in saved_pdf[0].get_text()
        hidden=documents.activeBridge
        documents.openPaths([str(source)]);wait(lambda:len(documents.tabs)==2 and ready())
        hidden.edit('add_text',{'page':0,'rect':[40,600,440,650],'text':'HIDDEN DIRTY TAB','size':16})
        wait(lambda:not hidden.busy)
        item('pageList').forceActiveFocus()
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Cancel):
            QTest.keyClick(window,Qt.Key_Q,Qt.ControlModifier|Qt.ShiftModifier)
            wait(lambda:not documents.closing)
        assert len(documents.tabs)==2 and window.isVisible()
        # X, then Enter: close all tabs, still asking about the unsaved hidden one.
        assert not window.close();wait(lambda:choice.property('visible'))
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Discard):
            QTest.keyClick(window,Qt.Key_Return)
            wait(lambda:not window.isVisible())
        assert not warnings,warnings
        print('PASS: window X offers this tab or all tabs; dirty-tab cancel/save; Ctrl+Shift+Q cancel; X+Enter closes all with dirty hidden tab',flush=True)
    finally:
        documents.activeBridge.setAutomaticOcr(saved_auto)
        window.setVisible(False);documents.shutdown();del engine
        qInstallMessageHandler(None)

if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support();main()
