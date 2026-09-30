"""Edit-mode layout stability and text-anchored memo regression.
Clicking a paragraph must not move the page under the pointer; memos written
on selected text or on an existing mark attach to that text, as in Acrobat.
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
    from PySide6.QtCore import QUrl,QObject,Qt,QByteArray,QPointF,qInstallMessageHandler
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from bichaek.bridge import Images
    from bichaek.tabs import Documents
    out=root/'test-output';out.mkdir(exist_ok=True)
    source=out/'Edit Stability.pdf'
    with fitz.open() as doc:
        for i in range(4):
            p=doc.new_page(width=600,height=800)
            p.insert_font(fontname='Original',fontbuffer=fitz.Font('tiro').buffer)
            for n in range(8):
                p.insert_text((50,90+n*80),f'Paragraph {n+1} on page {i+1} for stable editing',fontname='Original',fontsize=16)
        doc.save(source)
    QQuickStyle.setStyle(os.environ.get('YOONDF_QA_STYLE','Basic'));app=QApplication([])
    QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font('korea').buffer))
    warnings=[]
    def log(kind,context,message):
        if 'file:' in message or 'ReferenceError' in message or 'TypeError' in message:warnings.append(message)
    qInstallMessageHandler(log)
    images=Images();documents=Documents(images);b=documents.activeBridge
    b.setAutomaticOcr(False)
    errors=[];documents.showError.connect(errors.append)
    engine=QQmlApplicationEngine();engine.addImportPath(str(root/'ui/style'));engine.addImageProvider('pages',images)
    engine.rootContext().setContextProperty('bridge',b);engine.rootContext().setContextProperty('documents',documents)
    engine.load(QUrl.fromLocalFile(str(root/'ui/Main.qml')))
    assert engine.rootObjects(),warnings
    window=engine.rootObjects()[0]
    def wait(predicate,timeout=30):
        started=time.monotonic()
        while not predicate():
            app.processEvents();QTest.qWait(20)
            if time.monotonic()-started>timeout:raise AssertionError(('timeout',errors,warnings[-10:]))
        app.processEvents();QTest.qWait(100)
    retained=[]
    def item(name):
        pending=[window.contentItem().parentItem() or window.contentItem()]
        while pending:
            obj=pending.pop()
            if obj is None:continue
            if obj.objectName()==name:retained.append(obj);return obj
            pending.extend(obj.childItems())
        obj=window.findChild(QObject,name)
        if obj:retained.append(obj);return obj
        raise AssertionError(name)
    def ready():return not window.property('switching') and not window.property('restoring')
    def page_point(page,x,y):
        paper=item('paper'+str(page));f=paper.width()/b.pageWidth(page)
        return paper.mapToScene(QPointF(x*f,y*f))
    try:
        window.resize(1300,900)
        documents.openPaths([str(source)])
        wait(lambda:b.document['count']==4 and not b.busy and ready() and b.textLayout(0).get('chars'))
        view=item('pageList');view.setProperty('contentY',view.property('contentY')+260);QTest.qWait(200)
        window.setProperty('tool','editText');wait(lambda:b.blocksAt(b.currentPage) and ready())
        page=b.currentPage;QTest.qWait(300);window.grabWindow().save(str(out/'edit-stability-idle.png'))
        block=b.blocksAt(page)[5]
        x,y=block['displayRect'][0]+30,(block['displayRect'][1]+block['displayRect'][3])/2
        before=page_point(page,x,y)
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,before.toPoint())
        wait(lambda:item('textEditorSession').property('visible') and b.liveEditor.ready)
        QTest.qWait(300)
        after=page_point(page,x,y);window.grabWindow().save(str(out/'edit-stability-open.png'))
        assert abs(after.y()-before.y())<1 and abs(after.x()-before.x())<1,(before,after)
        # A late status row (font warning) must not move the page either.
        b.liveEditor._status='테스트 경고';b.liveEditor.changed.emit()
        QTest.qWait(200);late=page_point(page,x,y)
        assert abs(late.y()-before.y())<1,(before,late)
        QTest.keyClick(window,Qt.Key_Escape);wait(lambda:not item('textEditorSession').property('visible'))
        QTest.qWait(200);closed=page_point(page,x,y)
        assert abs(closed.y()-before.y())<1,(before,closed)
        print('PASS: paragraph click, late status and close keep the page under the pointer',flush=True)

        # Memo on selected text attaches to the text, not a page icon.
        window.setProperty('tool','read');wait(ready);b.navigateRequested.emit(0,0,0);wait(lambda:b.currentPage==0 and ready())
        wait(lambda:b.textLayout(0).get('chars'))
        b.selectCharacters(0,0,9);b.composeComment(0,60,80)
        wait(lambda:item('annotationEditor').property('visible'))
        item('commentBody').setProperty('text','글자에 붙는 각주');item('annotationEditor').apply()
        wait(lambda:not b.busy and len(b.pageAnnotations(0))==1)
        a=b.pageAnnotations(0)[0]
        assert a['type']=='Highlight' and a['content']=='글자에 붙는 각주' and a['label']=='메모' and a['quote'].startswith('Paragraph'),a
        # Adding a memo to an existing plain highlight edits that mark.
        b.selectCharacters(0,60,69);b.annotateSelection('underline');wait(lambda:not b.busy and len(b.pageAnnotations(0))==2)
        mark=next(x for x in b.pageAnnotations(0) if x['type']=='Underline')
        b.clearTextSelection();b.annotateItem(mark)
        wait(lambda:item('annotationEditor').property('visible'))
        item('commentBody').setProperty('text','밑줄에 단 메모');item('annotationEditor').apply()
        wait(lambda:not b.busy and any(x['content']=='밑줄에 단 메모' for x in b.pageAnnotations(0)))
        assert len(b.pageAnnotations(0))==2 and not any(x['type']=='Text' for x in b.pageAnnotations(0))
        # A point memo gets the redesigned bubble icon.
        b.clearTextSelection();b.composeComment(0,500,40);wait(lambda:item('annotationEditor').property('visible'))
        item('commentBody').setProperty('text','위치 메모');item('annotationEditor').apply()
        wait(lambda:not b.busy and any(x['type']=='Text' for x in b.pageAnnotations(0)))
        QTest.qWait(400);window.grabWindow().save(str(out/'edit-stability-memos.png'))
        assert not errors and not warnings,(errors,warnings)
        print('PASS: text memo as highlight note, memo on existing mark, point memo',flush=True)
    finally:
        documents.shutdown();window.hide();app.processEvents()
    del window;del engine;app.processEvents()
    return 0

if __name__=='__main__':sys.exit(main())
