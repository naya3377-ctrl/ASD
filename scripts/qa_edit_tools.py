"""Edit tool QA: drawing a text box on a scrolled page, and removing images.

A vertical drag with the text tool draws the box instead of scrolling the page
list. A placed image is removed with its delete button, the Delete key or the
right-click menu; a right click during a drag cancels the move.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
from pathlib import Path
import sys, time
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))


def build(path, png):
    import fitz
    pix=fitz.Pixmap(fitz.csRGB,fitz.IRect(0,0,120,80),False);pix.clear_with(90);pix.save(png)
    doc=fitz.open()
    for index in range(6):
        page=doc.new_page(width=595,height=842)
        page.insert_text((40,60),f'Page {index+1} heading',fontsize=18)
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
    out=root/'test-output';out.mkdir(exist_ok=True);pdf=out/'Edit Tools.pdf';png=out/'edit-tools.png';build(pdf,png)
    QQuickStyle.setStyle(os.environ.get('YOONDF_QA_STYLE','Basic'));app=QApplication([])
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
    def scene(page,x,y):
        paper=find('paper%d'%page);f=paper.property('width')/b.pageWidth(page)
        return paper.mapToScene(QPointF(x*f,y*f)).toPoint()
    def drag(start,end,steps=20,cancel=False):
        QTest.mousePress(w,Qt.LeftButton,Qt.NoModifier,start)
        for i in range(1,steps+1):
            QTest.mouseMove(w,start+(end-start)*i/steps);QTest.qWait(12)
            if cancel and i==steps//2:
                QTest.mousePress(w,Qt.RightButton,Qt.NoModifier,start+(end-start)*i/steps);QTest.mouseRelease(w,Qt.RightButton,Qt.NoModifier,start+(end-start)*i/steps)
        QTest.mouseRelease(w,Qt.LeftButton,Qt.NoModifier,end);QTest.qWait(150)
    def images(page): return b.movableImages(page)
    try:
        docs.openPaths([str(pdf)]);b=docs.activeBridge;b.setAutomaticOcr(False)
        wait(lambda:b.document['count']==6 and not b.busy)
        C.QMetaObject.invokeMethod(w,'goPage',C.Q_ARG('QVariant',3));wait(lambda:b.currentPage==3 and find('paper3') is not None)
        # Text box: an upward drag on a scrolled page draws the box, the list stays put
        w.useTool('addText');QTest.qWait(150);pages=find('pageList');y=pages.property('contentY')
        drag(scene(3,80,260),scene(3,300,120))
        assert abs(pages.property('contentY')-y)<1,('list scrolled',y,pages.property('contentY'))
        wait(lambda:find('legacyTextEditor3').property('visible'))
        find('replacementText').setProperty('text','added box');C.QMetaObject.invokeMethod(w,'commitEdit',C.Q_ARG('QVariant',None))
        wait(lambda:not b.busy and not find('legacyTextEditor3').property('visible'))
        # Three images on page 3
        for top in (90,160,230): b.edit('add_image',{'page':3,'rect':[300,top,420,top+60],'path':str(png)});wait(lambda:not b.busy)
        w.useTool('imageMove');wait(lambda:len(images(3))==3 and find('imageHandle'+images(3)[0]['id']) is not None)
        # Right click during a drag cancels the move
        first=sorted(images(3),key=lambda i:i['rect'][1])[0];before=list(first['rect'])
        drag(scene(3,360,120),scene(3,200,200),cancel=True);wait(lambda:not b.busy)
        assert any(all(abs(a-c)<.1 for a,c in zip(i['rect'],before)) for i in images(3)),('cancelled move applied',images(3))
        # Delete button on the selected image
        click(find('imageHandle'+first['id']));wait(lambda:find('imageDelete'+first['id']).property('visible'))
        click(find('imageDelete'+first['id']));wait(lambda:not b.busy and len(images(3))==2)
        # Delete key on the selected image
        second=sorted(images(3),key=lambda i:i['rect'][1])[0]
        click(find('imageHandle'+second['id']));QTest.keyClick(w,Qt.Key_Delete);wait(lambda:not b.busy and len(images(3))==1)
        # Right-click menu
        third=images(3)[0];r=third['rect']
        QTest.mouseClick(w,Qt.RightButton,Qt.NoModifier,scene(3,(r[0]+r[2])/2,(r[1]+r[3])/2))
        wait(lambda:find('deleteImageItem') is not None and find('deleteImageItem').property('visible'))
        item=find('deleteImageItem');click(item);wait(lambda:not b.busy and len(images(3))==0)
        # Undo brings the last one back
        b.undo();wait(lambda:not b.busy and len(images(3))==1)
        # Ctrl+S while a paragraph is open: the edit is applied, then saved.
        import fitz
        b.save(False);wait(lambda:not b.busy and not b.document['dirty'])
        w.useTool('editText');b.loadBlocks(3);wait(lambda:bool(b.blocksAt(3)))
        block=next(x for x in b.blocksAt(3) if 'heading' in x['text'])
        b.editBlock(block);wait(lambda:find('replacementText') is not None and not b.liveEditor.loading)
        field=find('replacementText');field.forceActiveFocus();QTest.keyClick(w,Qt.Key_End,Qt.ControlModifier)
        for ch in ' done':QTest.keyClick(w,ch)
        wait(lambda:b.liveEditor.canApply)
        QTest.keyClick(w,Qt.Key_S,Qt.ControlModifier)
        wait(lambda:not b.busy and not b.document['dirty'] and not w.findChild(QObject,'textEditorSession').property('visible'))
        with fitz.open(pdf) as saved: assert 'heading done' in ' '.join(saved[3].get_text().split()),saved[3].get_text()
        assert not warnings,warnings
        print('PASS: Ctrl+S while editing applies then saves; text box drawn by vertical drag on a scrolled page; image removed by button, Delete key and right-click menu; right click cancels a drag; undo restores')
    finally:
        b._state['dirty']=False;w.setVisible(False);docs.shutdown();del engine


if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
