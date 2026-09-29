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
    with fitz.open() as doc:
        for i in range(8):
            p=doc.new_page(width=600 if i!=3 else 700,height=800 if i!=3 else 900)
            p.insert_font(fontname='Original',fontbuffer=fitz.Font('tiro').buffer)
            p.insert_text((40,70),'ORIGINAL TEXT FOR REVIEW',fontname='Original',fontsize=20)
            p.insert_text((40,350),f'Facing Needle {i+1}',fontname='Original',fontsize=18)
            if i==0:p.insert_image([60,150,300,270],filename=str(png))
        doc.save(source);doc.save(second)
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
        window.resize(1600,1200)
        documents.openPaths([str(source)])
        wait(lambda:b.document['count']==8 and not b.busy and ready() and b.textLayout(0).get('chars'))
        # Right dock is a sibling of the viewport; both facing pages stay visible.
        window.setProperty('twoPageView',True);wait(ready)
        b.composeComment(1,440,200);wait(lambda:item('annotationEditor').property('visible'))
        dock=item('commentsDock');view=item('pageList')
        assert view.mapToScene(QPointF(view.width(),0)).x()<=dock.mapToScene(QPointF(0,0)).x()+1
        p0=item('paper0');p1=item('paper1');assert p1.mapToScene(QPointF(p1.width(),0)).x()<dock.mapToScene(QPointF(0,0)).x(), (p0.width(),p1.width(),p1.mapToScene(QPointF(p1.width(),0)).x(),dock.mapToScene(QPointF(0,0)).x(),view.width(),window.width(),window.property('zoom'))
        item('commentBody').setProperty('text','자유롭게 배치하는 메모')
        old=view.property('contentY');view.setProperty('contentY',old+100);QTest.qWait(100)
        assert item('commentBody').property('text')=='자유롭게 배치하는 메모'
        view.setProperty('contentY',old);QTest.qWait(150)
        window.grabWindow().save(str(out/'YoonDF-0.8.0-note-sidebar.png'))
        click('applyComment');wait(lambda:not b.busy and not item('annotationEditor').property('visible'))
        wait(lambda:len(b.pageAnnotations(1))==1)
        note=b.pageAnnotations(1)[0];b.selectAnnotation(1,note['id']);b.editSelectedAnnotation('reply')
        wait(lambda:item('annotationEditor').property('visible'))
        item('commentBody').setProperty('text','위치를 옮겨도 남는 답글');click('applyComment')
        wait(lambda:not b.busy and len(b.pageAnnotations(1))==2)
        b.navigateRequested.emit(0,0,0);wait(lambda:b.currentPage==0 and ready())
        window.setProperty('tool','read');note=b.pageAnnotations(1)[0];before=note['rect'][:]
        factor=item('paper1').width()/b.pageWidth(1)
        a=page_point(1,before[0]+9,before[1]+9);z=a+QPointF(-90*factor,130*factor)
        drag(a,z);wait(lambda:not b.busy and len(b.pageAnnotations(1))==2 and abs(b.pageAnnotations(1)[0]['rect'][1]-(before[1]+130))<2)
        note=b.pageAnnotations(1)[0];close_rect(note['rect'],[before[0]-90,before[1]+130,before[2]-90,before[3]+130])
        assert b.pageAnnotations(1)[1]['parentId']==note['id'] and note['content']=='자유롭게 배치하는 메모'
        b.undo();wait(lambda:not b.busy and len(b.pageAnnotations(1))==2 and abs(b.pageAnnotations(1)[0]['rect'][0]-before[0])<2)
        b.redo();wait(lambda:not b.busy and len(b.pageAnnotations(1))==2 and abs(b.pageAnnotations(1)[0]['rect'][0]-(before[0]-90))<2)
        print('PASS: non-overlapping two-page memo sidebar, scroll-safe draft, real right-page marker drag, reply and undo/redo',flush=True)
        # Native markup right-click deletion and undo.
        click('readModeButton');window.setProperty('twoPageView',False);b.navigateRequested.emit(0,0,0)
        wait(lambda:b.currentPage==0 and ready() and b.textLayout(0).get('chars'))
        b.selectCharacters(0,0,8);b.annotateSelection('highlight');wait(lambda:not b.busy and len(b.pageAnnotations(0))==1)
        right_at(100,62);assert item('deleteAnnotationMenuItem').property('visible');click('deleteAnnotationMenuItem')
        wait(lambda:not b.busy and not b.pageAnnotations(0));b.undo();wait(lambda:not b.busy and len(b.pageAnnotations(0))==1)
        assert b.pageAnnotations(0)[0]['type']=='Highlight'
        print('PASS: real right-click highlight deletion and undo',flush=True)
        # Direct inline editing on right page; draft survives delegate eviction.
        click('editModeButton');window.setProperty('twoPageView',True);window.setProperty('tool','editText')
        wait(lambda:b.blocksAt(1) and ready())
        block=next(x for x in b.blocksAt(1) if x['text'].startswith('ORIGINAL'))
        pos=page_point(1,100,62);QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,pos.toPoint())
        wait(lambda:item('textEditorSession').property('visible') and b.liveEditor.ready)
        field=item('replacementText');paper=item('paper1');pos=field.mapToItem(paper,QPointF(0,0))
        close_rect([pos.x(),pos.y()],[block['displayRect'][0]*paper.width()/b.pageWidth(1),block['displayRect'][1]*paper.width()/b.pageWidth(1)])
        field.forceActiveFocus();QTest.keyClick(window,Qt.Key_A,Qt.ControlModifier)
        for char in 'INLINE REVISED TEXT':QTest.keyClick(window,ord(char),Qt.ShiftModifier if char.isalpha() else Qt.NoModifier)
        assert item('textEditorSession').property('text')=='INLINE REVISED TEXT'
        b.navigateRequested.emit(7,0,0);wait(lambda:b.currentPage==7 and ready());assert item('textEditorSession').property('text')=='INLINE REVISED TEXT'
        b.navigateRequested.emit(1,0,0);wait(lambda:b.currentPage==1 and ready());assert b.liveEditor.doc.toPlainText()=='INLINE REVISED TEXT'
        window.grabWindow().save(str(out/'YoonDF-0.8.0-inline.png'))
        click('applyTextButton');wait(lambda:not b.busy and not item('textEditorSession').property('visible'))
        b.loadBlocksForPage(1);wait(lambda:any(x['text'].startswith('INLINE REVISED') for x in b.blocksAt(1)))
        assert 'NimbusRoman' in next(x for x in b.blocksAt(1) if x['text'].startswith('INLINE'))['font']
        print('PASS: real right-page body click/keyboard edit, original font, draft survives paging and commits on its own page',flush=True)
        # Insert, drag and resize using actual pointer handlers.
        window.setProperty('twoPageView',False);b.navigateRequested.emit(0,0,0);wait(lambda:b.currentPage==0 and ready())
        with patch.object(QFileDialog,'getOpenFileName',return_value=(str(png),'PNG')):
            click('insertImageButton');wait(lambda:not b.busy and len(b.textLayout(0).get('movableImages',[]))==2 and ready())
        focus=b.imageFocus['id'];image=next(x for x in b.textLayout(0)['movableImages'] if x['id']==focus);r=image['rect'][:]
        box=item('imageHandle'+focus);a=box.mapToScene(box.boundingRect().center());factor=item('paper0').width()/b.pageWidth(0)
        drag(a,a+QPointF(45*factor,60*factor))
        wait(lambda:not b.busy and b.imageFocus.get('id')!=focus and bool(b.imageFocus.get('id')))
        focus=b.imageFocus['id'];wait(lambda:any(x['id']==focus for x in b.textLayout(0).get('movableImages',[])))
        image=next(x for x in b.textLayout(0)['movableImages'] if x['id']==focus);close_rect(image['rect'],[r[0]+45,r[1]+60,r[2]+45,r[3]+60]);r=image['rect'][:]
        handle=item('imageResize'+focus);assert handle.isVisible();a=handle.mapToScene(handle.boundingRect().center())
        drag(a,a+QPointF(30*factor,15*factor))
        wait(lambda:not b.busy and b.imageFocus.get('id')!=focus and bool(b.imageFocus.get('id')))
        focus=b.imageFocus['id'];wait(lambda:any(x['id']==focus for x in b.textLayout(0).get('movableImages',[])))
        image=next(x for x in b.textLayout(0)['movableImages'] if x['id']==focus);assert image['rect'][2]>r[2]+25
        final_image=image['rect'][:]
        window.grabWindow().save(str(out/'YoonDF-0.8.0-image-move.png'))
        print('PASS: actual inserted-image drag and corner resize, focus follows persistent native image object',flush=True)
        # Ctrl selects disjoint pages; Shift ranges use an anchor. Drag retains order.
        window.setProperty('twoPageView',True);window.setProperty('tool','read');window.setProperty('zoom',.65);b.navigateRequested.emit(0,0,0)
        wait(lambda:b.currentPage==0 and ready())
        thumbs=item('thumbnailList');assert thumbs.property('count')==8
        for n,modifier in [(0,Qt.NoModifier),(2,Qt.ControlModifier)]:
            thumb=item('thumbnailPaper'+str(n));point=thumb.mapToScene(thumb.boundingRect().center())
            QTest.mouseClick(window,Qt.LeftButton,modifier,point.toPoint());QTest.qWait(200)
        assert b.selection==[0,2],b.selection
        first=item('thumbnailPaper0');last=item('thumbnailPaper3')
        a=first.mapToScene(first.boundingRect().center());z=last.mapToScene(QPointF(last.width()/2,last.height()-2))
        drag(a,z);wait(lambda:not b.busy and b.selection==[2,3])
        b.save(False);wait(lambda:not b.busy and not b.document['dirty'])
        with fitz.open(source) as saved:
            order=[p.get_text().split('Facing Needle ')[1][0] for p in saved]
            assert order==['2','4','1','3','5','6','7','8'],order
            assert 'INLINE REVISED TEXT' in saved[0].get_text()
            saved_page=saved[0]
            note=next(a for a in saved_page.annots() if a.type[1]=='Text' and a.info.get('content')=='자유롭게 배치하는 메모')
            assert abs(note.rect.x0-(before[0]-90))<2
            assert any(all(abs(a-z)<2 for a,z in zip(im['bbox'],final_image)) for im in saved[2].get_image_info())
        b.undo();wait(lambda:not b.busy)
        b.navigateRequested.emit(0,0,0);wait(lambda:b.currentPage==0 and ready())
        for n,modifier in [(0,Qt.NoModifier),(2,Qt.ShiftModifier)]:
            thumb=item('thumbnailPaper'+str(n));point=thumb.mapToScene(thumb.boundingRect().center())
            QTest.mouseClick(window,Qt.LeftButton,modifier,point.toPoint());QTest.qWait(200)
        assert b.selection==[0,1,2],b.selection
        print('PASS: actual Ctrl/Shift thumbnail selection, multi-page drag, full thumbnail count in spreads, saved order and one-step undo',flush=True)
        assert not errors and not warnings,(errors,warnings)
    finally:
        documents.activeBridge.setAutomaticOcr(saved_auto)
        window.setVisible(False);documents.shutdown();del engine
        qInstallMessageHandler(None)

if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support();main()
