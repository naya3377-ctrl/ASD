"""Comment flows as a reader performs them, on PDFs that used to fail.

Drag over words then press the note button, click a place for a note, mark
with the highlighter, use the right-click menu, edit, reply, delete, undo and
save; on a report with a damaged unused object (the "code=8: invalid key in
dict" failure), a PDF that allows comments but not copying, and a turned page.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QT_QUICK_BACKEND','software')
from pathlib import Path
import sys,time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))

TITLE='『문화예술활동현황조사』'


def build(out):
    import fitz
    def report(doc,rotation=0):
        for index in range(4):
            p=doc.new_page(width=595,height=842)
            if index==0:
                p.insert_text((110,300),TITLE,fontname='korea',fontsize=30)
                p.insert_text((190,360),'통계정보보고서',fontname='korea',fontsize=30)
                p.insert_text((250,440),'2023. 12.',fontsize=24)
            else:
                p.insert_text((72,100),f'{index+1}. 조사 개요',fontname='korea',fontsize=18)
                for line in range(8):p.insert_text((72,150+line*24),f'문화예술 활동 건수와 분야별 현황 {line+1}',fontname='korea',fontsize=12)
            p.set_rotation(rotation)
    paths={}
    # The failing report: a damaged object nothing uses, as some exporters write.
    with fitz.open() as doc:
        report(doc);x=doc.get_new_xref();doc.update_object(x,'<< /Hancom 1 >>')
        paths['damaged']=out/'손상된 보고서.pdf';doc.save(paths['damaged'])
    data=paths['damaged'].read_bytes().replace(b'<</Hancom 1>>',b'<</Hancom 1 (x) 2>>',1)
    paths['damaged'].write_bytes(data)
    with fitz.open() as doc:
        report(doc);paths['nocopy']=out/'복사 금지 보고서.pdf'
        doc.save(paths['nocopy'],encryption=fitz.PDF_ENCRYPT_AES_128,owner_pw='owner',user_pw='',
                 permissions=fitz.PDF_PERM_PRINT|fitz.PDF_PERM_ANNOTATE)
    with fitz.open() as doc:
        report(doc,90);paths['rotated']=out/'가로 보고서.pdf';doc.save(paths['rotated'])
    return paths


def main():
    import fitz
    from unittest.mock import patch
    from PySide6.QtCore import QUrl,QObject,Qt,QByteArray,QPointF,qInstallMessageHandler
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication,QMessageBox
    from PySide6.QtTest import QTest
    from bichaek.bridge import Images
    from bichaek.tabs import Documents
    root=Path(__file__).resolve().parent.parent;out=root/'test-output';out.mkdir(exist_ok=True)
    paths=build(out)
    QQuickStyle.setStyle('Basic');app=QApplication([])
    QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font('korea').buffer))
    warnings=[]
    def log(kind,context,message):
        if 'file:' in message or 'ReferenceError' in message or 'TypeError' in message:warnings.append(message)
    qInstallMessageHandler(log)
    images=Images();documents=Documents(images);b=documents.activeBridge
    saved=(b.automaticOcr,b.annotationAuthor,b.annotationColor)
    b.setAutomaticOcr(False);b.setAnnotationAuthor('큐레이터');b.setAnnotationColor('#ffd54f')
    errors=[];documents.showError.connect(errors.append)
    engine=QQmlApplicationEngine();engine.addImageProvider('pages',images)
    engine.rootContext().setContextProperty('bridge',b);engine.rootContext().setContextProperty('documents',documents)
    engine.load(QUrl.fromLocalFile(str(root/'ui/Main.qml')))
    assert engine.rootObjects(),warnings
    window=engine.rootObjects()[0];window.setProperty('uiFontFamily','Droid Sans Fallback')
    window.setProperty('width',1500);window.setProperty('height',940)
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
    def click(name,button=Qt.LeftButton):
        x=item(name);pos=x.mapToScene(x.boundingRect().center())
        QTest.mouseClick(window,button,Qt.NoModifier,pos.toPoint());QTest.qWait(100)
    def span(c,text,page=0):
        chars=c.textLayout(page)['chars'];joined=''.join(ch[0] for ch in chars)
        if text in joined:start=joined.index(text)
        else:start=0   # placeholders on a no-copy PDF: the first characters
        return chars[start:start+len(text)]
    def drag(c,text,page=0):
        """Select words with the pointer, the way a reader does."""
        layer=item('textLayer%d'%page);f=layer.property('factor');chosen=span(c,text,page)
        a=layer.mapToScene(QPointF(chosen[0][1]*f+1,(chosen[0][2]+chosen[0][4])/2*f))
        z=layer.mapToScene(QPointF(chosen[-1][3]*f-1,(chosen[-1][2]+chosen[-1][4])/2*f))
        QTest.mousePress(window,Qt.LeftButton,Qt.NoModifier,a.toPoint())
        for i in range(1,9):QTest.mouseMove(window,(a+(z-a)*(i/8)).toPoint(),12)
        QTest.mouseRelease(window,Qt.LeftButton,Qt.NoModifier,z.toPoint());QTest.qWait(80)
        wait(lambda:c.textSelection['count']>=len(text)-1)
        return chosen
    def write(text):
        wait(lambda:item('annotationEditor').property('visible'))
        item('commentBody').setProperty('text',text);click('applyComment')
        wait(lambda:not documents.activeBridge.busy and not item('annotationEditor').property('visible'))
    def mine(c):return [a for a in c.annotations if a['name'].startswith('bichaek-')]

    def flows(label,path):
        documents.openPaths([str(path)]);c=documents.activeBridge
        wait(lambda:c.document.get('name')==path.name and c.document['count']==4 and not c.busy)
        wait(lambda:c.imageUrl(0,'main') and c.textLayout(0)['chars'])
        if window.property('workspaceMode')!='comments':click('commentsModeButton')
        wait(lambda:window.property('commentsOpen') and not c.annotationsLoading)
        window.setProperty('zoom',.9);QTest.qWait(250)
        # 1. Drag over the title, then the note button: a note on those words.
        chosen=drag(c,TITLE);click('commentNoteButton')
        wait(lambda:item('annotationEditor').property('visible'))
        assert item('annotationEditor').property('targetData').toVariant()['kind']=='highlight'
        write('안녕')
        wait(lambda:len(mine(c))==1)
        note=mine(c)[0];assert note['type']=='Highlight' and note['content']=='안녕' and note['author']=='큐레이터',note
        region=note['regions'][0];assert region[0]<=chosen[0][1]+2 and region[2]>=chosen[-1][3]-2,(region,chosen[0],chosen[-1])
        if label!='nocopy':assert TITLE[1:5] in note['quote'],note['quote']
        # 2. Note button with nothing selected, then a click on the page.
        c.clearTextSelection();click('commentNoteButton')
        paper=item('paper0');pos=paper.mapToScene(QPointF(paper.width()*.75,paper.height()*.2))
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,pos.toPoint())
        write('여기에 메모');wait(lambda:len(mine(c))==2)
        assert any(a['type']=='Text' and a['content']=='여기에 메모' for a in mine(c))
        # 3. Highlighter on selected words.
        drag(c,'통계정보보고서');click('commentHighlightButton');wait(lambda:len(mine(c))==3 and not c.busy)
        window.setProperty('tool','read');QTest.qWait(60)
        # 4. Right-click on a selection: the menu offers a note on it.
        chosen=drag(c,'2023. 12.')
        layer=item('textLayer0');f=layer.property('factor')
        at=layer.mapToScene(QPointF((chosen[0][1]+chosen[-1][3])/2*f,(chosen[0][2]+chosen[0][4])/2*f))
        QTest.mouseClick(window,Qt.RightButton,Qt.NoModifier,at.toPoint());QTest.qWait(150)
        menu_item=item('addMemoMenuItem');assert menu_item.property('text')=='선택한 글자에 메모',menu_item.property('text')
        menu_item.triggered.emit();write('날짜 확인')
        wait(lambda:len(mine(c))==4)
        # 5. Edit, reply, delete with its reply, undo.
        first=next(a for a in mine(c) if a['content']=='안녕');c.selectAnnotation(0,first['id'])
        c.editSelectedAnnotation('edit');write('안녕하세요, 제목 확인 부탁해요')
        c.editSelectedAnnotation('reply');write('확인했어요')
        wait(lambda:len(mine(c))==5)
        assert any(a['reply'] and a['content']=='확인했어요' for a in mine(c))
        target=next(a for a in mine(c) if a['content']=='날짜 확인');c.selectAnnotation(0,target['id'])
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):c.deleteSelectedAnnotation()
        wait(lambda:not c.busy and len(mine(c))==4)
        c.undo();wait(lambda:not c.busy and len(mine(c))==5)
        # 6. Save and read it back with an independent open.
        c.save(False);wait(lambda:not c.busy and not c.document['dirty'])
        with fitz.open(path) as check:
            if check.needs_pass:check.authenticate('')
            found={a.info['content'] for a in check[0].annots()}
        assert {'안녕하세요, 제목 확인 부탁해요','확인했어요','여기에 메모','날짜 확인'}<=found,found
        assert not errors,errors
        print(f'PASS {label}: note on dragged words, note by click, highlighter, right-click note, edit/reply/delete/undo, save',flush=True)

    try:
        for label in ('damaged','nocopy','rotated'):flows(label,paths[label])
        # The no-copy PDF still refuses copying.
        documents.activate(1);c=documents.activeBridge;wait(lambda:c.textLayout(0)['chars'])
        c.selectCharacters(0,0,4);c.copySelection()
        assert '복사' in c.property('status') and '제한' in c.property('status'),c.property('status')
        assert set(''.join(ch[0] for ch in c.textLayout(0)['chars']).split())<={'•'*n for n in range(1,40)}
        window.grabWindow().save(str(out/'comment-flows.png'))
        assert not warnings,warnings
        print('PASS: no-copy PDF keeps copying blocked, no QML warnings',flush=True)
    finally:
        active=documents.activeBridge;active.setAutomaticOcr(saved[0]);active.setAnnotationAuthor(saved[1]);active.setAnnotationColor(saved[2])
        window.setVisible(False);documents.shutdown();del engine;qInstallMessageHandler(None)

if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support();main()
