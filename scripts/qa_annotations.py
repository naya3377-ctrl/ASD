"""Native annotation UI, independent PDF parse and Poppler render regression.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QT_QUICK_BACKEND','software')
from pathlib import Path
import sys,time,shutil,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))


def main():
    import fitz
    from unittest.mock import patch
    from PySide6.QtCore import QUrl,QObject,Qt,QByteArray,QPointF,qInstallMessageHandler
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication,QMessageBox
    from PySide6.QtTest import QTest
    from pypdf import PdfReader
    from bichaek.bridge import Images
    from bichaek.tabs import Documents
    from tests.test_annotations import foreign_fixture
    root=Path(__file__).resolve().parent.parent;out=root/'test-output';out.mkdir(exist_ok=True)
    source=out/'Comments Review.pdf';foreign=out/'External Comments.pdf';foreign_fixture(foreign)
    with fitz.open() as doc:
        p=doc.new_page(width=600,height=800)
        p.insert_font(fontname="Review",fontbuffer=fitz.Font("helv").buffer)
        p.insert_text((50,65),'DOCUMENT REVIEW',fontname="Review",fontsize=28,color=(.17,.28,.20))
        p.insert_text((50,110),'A shared space for careful reading.',fontname="Review",fontsize=16)
        p.insert_text((50,190),'Highlight a sentence to begin a conversation.',fontname="Review",fontsize=16)
        p.insert_text((50,225),'Keep the original text and share your comments.',fontname="Review",fontsize=16)
        p.insert_text((50,305),'Underline the details that deserve another look.',fontname="Review",fontsize=16)
        p.insert_text((50,385),'Strike out the words that need to be revised.',fontname="Review",fontsize=16)
        p.insert_text((50,520),'Comments stay editable inside the PDF.',fontname="Review",fontsize=15,color=(.40,.47,.40))
        p.insert_text((50,745),'BICHAEK PDF / ANNOTATION REVIEW',fontname="Review",fontsize=10,color=(.55,.61,.53))
        doc.save(source)
    QQuickStyle.setStyle(os.environ.get('YOONDF_QA_STYLE','Basic'));app=QApplication([])
    QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font('korea').buffer))
    warnings=[]
    def log(kind,context,message):
        if 'file:' in message or 'ReferenceError' in message or 'TypeError' in message:warnings.append(message)
    qInstallMessageHandler(log)
    images=Images();documents=Documents(images);b=documents.activeBridge
    saved_auto=b.automaticOcr;saved_author=b.annotationAuthor;saved_color=b.annotationColor
    b.setAutomaticOcr(False);b.setAnnotationAuthor('검토자');b.setAnnotationColor('#ffd54f')
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
            if time.monotonic()-started>timeout:raise AssertionError(('timeout',errors,warnings[-8:]))
        app.processEvents();QTest.qWait(80)
    def item(name):
        x=window.findChild(QObject,name)
        if x:return x
        todo=[window.contentItem()]
        while todo:
            x=todo.pop()
            if x.objectName()==name:return x
            todo.extend(x.childItems())
        raise AssertionError(name)
    def click(name):
        x=item(name);pos=x.mapToScene(x.boundingRect().center())
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,pos.toPoint());QTest.qWait(100)
    def select_line(text):
        chars=b.textLayout(0)['chars'];joined=''.join(c[0] for c in chars)
        start=joined.index(text);end=start+len(text)
        b.selectCharacters(0,start,end)
    def apply_editor(text):
        wait(lambda:item('annotationEditor').property('visible'))
        item('commentBody').setProperty('text',text);click('applyComment')
        wait(lambda:not b.busy and not item('annotationEditor').property('visible'))
    try:
        documents.openPaths([str(source)]);wait(lambda:b.document['count']==1 and b.imageUrl(0,'main') and b.textLayout(0)['chars'])
        click('commentsModeButton');wait(lambda:window.property('commentsOpen') and not b.annotationsLoading)
        window.setProperty('zoom',.8);QTest.qWait(250)
        # Actual pointer selection with an active highlighter, including two lines.
        click('commentHighlightButton');layer=item('textLayer0');factor=layer.property('factor')
        a=layer.mapToScene(QPointF(49*factor,185*factor));z=layer.mapToScene(QPointF(410*factor,224*factor))
        QTest.mousePress(window,Qt.LeftButton,Qt.NoModifier,a.toPoint())
        for i in range(1,9):QTest.mouseMove(window,(a+(z-a)*(i/8)).toPoint(),12)
        QTest.mouseRelease(window,Qt.LeftButton,Qt.NoModifier,z.toPoint())
        wait(lambda:not b.busy and len(b.annotations)==1 and not b.annotationsLoading)
        assert b.annotations[0]['type']=='Highlight' and len(b.annotations[0]['regions'])>=2
        b.editSelectedAnnotation('edit');apply_editor('이 문장은 유지하고, 뒤에 설명을 보태면 좋겠어요.')
        assert b.annotations[0]['author']=='검토자'
        b.editSelectedAnnotation('reply');apply_editor('확인했어요. 다음 교정에 반영할게요.')
        wait(lambda:len(b.annotations)==2)
        assert b.annotations[1]['reply'] and b.annotations[1]['parentId']==b.annotations[0]['id']
        # Use selection then toolbar for the other two standard markups.
        select_line('Underline the details');click('commentUnderlineButton')
        wait(lambda:not b.busy and len(b.annotations)==3)
        select_line('words that need to be revised');click('commentStrikeoutButton')
        wait(lambda:not b.busy and len(b.annotations)==4)
        click('commentNoteButton');paper=item('paper0');pos=paper.mapToScene(QPointF(paper.width()*.7,paper.height()*.58))
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,pos.toPoint())
        wait(lambda:item('annotationEditor').property('visible'))
        # Native validation failure keeps the typed draft. Auto OCR cannot
        # change the PDF revision while the comment editor is open.
        item('commentBody').setProperty('text','작성 중인 메모는 사라지면 안 됩니다.')
        item('annotationEditor').setProperty('selectedColor','invalid-color')
        click('applyComment');wait(lambda:not b.busy)
        assert item('annotationEditor').property('visible')
        assert item('commentBody').property('text')=='작성 중인 메모는 사라지면 안 됩니다.'
        assert errors;errors.clear()
        QTest.keyClick(window,Qt.Key_Escape);QTest.qWait(100)
        assert item('annotationEditor').property('visible')
        with patch.object(b,'startOcr') as start:
            b._auto_ocr=True;b.auto_recognize();b._auto_ocr=False
            start.assert_not_called()
        item('annotationEditor').setProperty('selectedColor','#ffd54f')
        apply_editor('검토 완료 후 PDF로 저장해서 공유해 주세요.')
        wait(lambda:len(b.annotations)==5)
        b.save(False);wait(lambda:not b.busy and not b.document['dirty'] and len(b.annotations)==5)
        found=[a.get_object() for a in PdfReader(source).pages[0]['/Annots'] if a.get_object()['/Subtype']!='/Popup']
        assert {a['/Subtype'] for a in found}=={'/Highlight','/Underline','/StrikeOut','/Text'}
        assert any(a.get('/RT')=='/R' and a['/Contents'].startswith('확인') for a in found)
        print('PASS: real multi-line drag highlight, toolbar underline/strikeout, note click, author, edit/reply, native PDF save',flush=True)
        # Opening another PDF retains comments and per-document selection.
        documents.openPaths([str(foreign)]);c=documents.activeBridge
        wait(lambda:c.document['count'] and not c.busy)
        click('commentsModeButton');wait(lambda:len(c.annotations)==5 and not c.annotationsLoading)
        assert any(x['content']=='외부 프로그램의 답글' and x['reply'] for x in c.annotations)
        unsupported=next(x for x in c.annotations if x['type']=='FreeText');assert not unsupported['editable']
        c.selectAnnotation(0,'nm:foreign-markup');c.editSelectedAnnotation('edit')
        wait(lambda:item('annotationEditor').property('visible'))
        item('commentBody').setProperty('text','비책 PDF에서 수정한 외부 주석');click('applyComment')
        wait(lambda:not c.busy and any(x['content']=='비책 PDF에서 수정한 외부 주석' for x in c.annotations))
        c.save(False);wait(lambda:not c.busy and not c.document['dirty'])
        documents.activate(0);wait(lambda:documents.activeBridge is b and len(b.annotations)==5)
        parent=next(x for x in b.annotations if x['type']=='Highlight');b.selectAnnotation(0,parent['id'])
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):b.deleteSelectedAnnotation()
        wait(lambda:not b.busy and len(b.annotations)==3)
        b.undo();wait(lambda:not b.busy and len(b.annotations)==5)
        b.save(False);wait(lambda:not b.busy and not b.document['dirty'])
        # Click the rendered native highlight in read mode to open its comment.
        window.setProperty('workspaceMode','read');window.setProperty('tool','read');window.setProperty('commentsOpen',False)
        wait(lambda:not window.property('restoring'));QTest.qWait(200)
        layer=item('textLayer0');factor=layer.property('factor')
        p=layer.mapToScene(QPointF(120*factor,185*factor))
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,p.toPoint())
        wait(lambda:window.property('commentsOpen') and bool(b.selectedAnnotation))
        print('PASS: independent writer PDF comments/replies, unsupported object preservation, tab isolation, delete thread/undo, click native annotation',flush=True)
        # Compact final preview without a hover tooltip; preserve review PDF.
        window.setProperty('zoom',.75);window.setProperty('tool','read');QTest.qWait(200)
        page_list=item('pageList');page_list.setProperty('contentY',-24)
        QTest.mouseMove(window,window.contentItem().mapToScene(QPointF(5,880)).toPoint());QTest.qWait(900)
        window.grabWindow().save(str(out/'annotations-050.png'))
        assert not errors,errors
        assert not warnings,warnings
        # Poppler is independent of the renderer used by the application.
        result=subprocess.run(['pdftoppm','-f','1','-singlefile','-scale-to','1100','-png',str(source),str(out/'comments-poppler')],capture_output=True,text=True)
        assert result.returncode==0,result.stderr
        assert 'Syntax Error' not in result.stderr,result.stderr
        print('PASS: Poppler rendering and independent PDF parsing; no QML warnings',flush=True)
    finally:
        active=documents.activeBridge;active.setAutomaticOcr(saved_auto);active.setAnnotationAuthor(saved_author);active.setAnnotationColor(saved_color)
        window.setVisible(False);documents.shutdown();del engine;qInstallMessageHandler(None)

if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support();main()
