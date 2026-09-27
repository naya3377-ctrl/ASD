"""Comment list ↔ page navigation QA on a mixed page-size document.

Clicking a card moves to its page and outlines the mark; clicking a mark on the
page selects its card and scrolls the list to it without moving the page;
editing inside the card keeps the list and selection while pages reload.
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
    for index in range(9):
        page=doc.new_page(width=420 if index%3==0 else 840,height=595)
        page.insert_text((40,60),f'Page {index+1} heading',fontsize=18)
        for line in range(6):
            page.insert_text((40,120+line*18),f'Line {line} of page {index+1} with words to mark',fontsize=11)
        if index in (1,4,7):
            words=page.search_for(f'Line 2 of page {index+1}')
            a=page.add_highlight_annot(words);a.set_info(content=f'comment on page {index+1}',title='QA');a.update()
    doc[4].add_text_annot((300,80),'loose note').update()
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
    out=root/'test-output';out.mkdir(exist_ok=True);pdf=out/'Comment Navigation.pdf';build(pdf)
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
    try:
        docs.openPaths([str(pdf)]);b=docs.activeBridge;b.setAutomaticOcr(False)
        wait(lambda:b.document['count']==9 and not b.busy)
        assert [round(s[0]) for s in b.document['pageSizes'][:3]]==[420,840,840]
        click(find('commentsModeButton'));wait(lambda:not b.annotationsLoading and len(b.annotations)==4)
        # Card → page
        target=next(i for i,a in enumerate(b.annotations) if a['page']==7)
        C.QMetaObject.invokeMethod(find('commentsList'),'positionViewAtIndex',C.Q_ARG(int,target),C.Q_ARG(int,1));wait(lambda:find('commentCard%d'%target) is not None)
        click(find('commentCard%d'%target));wait(lambda:b.currentPage==7)
        wait(lambda:find('selectedMark7') is not None and find('selectedMark7').property('shown'))
        pages=find('pageList');paper=find('paper7')
        top=paper.mapToItem(pages,0,0).y();assert -paper.property('height')<top<pages.property('height'),('page 8 on screen',top)
        # Page mark → card, page does not move
        C.QMetaObject.invokeMethod(w,'goPage',C.Q_ARG('QVariant',1));wait(lambda:b.currentPage==1 and find('paper1') is not None)
        wait(lambda:len(b.pageAnnotations(1))==1)
        mark=b.pageAnnotations(1)[0];paper=find('paper1');f=paper.property('width')/b.pageWidth(1);r=mark['regions'][0]
        QTest.mouseClick(w,Qt.LeftButton,Qt.NoModifier,paper.mapToScene(QPointF((r[0]+r[2])/2*f,(r[1]+r[3])/2*f)).toPoint())
        wait(lambda:b.selectedAnnotation.get('id')==mark['id']);assert b.currentPage==1
        index=next(i for i,a in enumerate(b.annotations) if a['id']==mark['id']);wait(lambda:find('commentCard%d'%index) is not None)
        # Edit inside the card; the list stays put while pages reload
        click(find('editComment%d'%index));wait(lambda:find('commentBody') is not None)
        body=find('commentBody');body.setProperty('text','edited in place');click(find('applyComment'))
        wait(lambda:not b.busy and not find('commentBody'))
        sizes=set()
        for _ in range(30):sizes.add(len(b.annotations));QTest.qWait(20)
        assert sizes=={4},sizes
        wait(lambda:b.selectedAnnotation.get('content')=='edited in place')
        # A new note is written at the top of the list, not over it
        b.composeComment(4,200,300);wait(lambda:find('commentBody') is not None and w.findChild(QObject,'annotationEditor').property('visible'))
        find('commentBody').setProperty('text','new note');click(find('applyComment'))
        wait(lambda:not b.busy and len(b.annotations)==5 and not b.annotationsLoading)
        assert not warnings,warnings
        print('PASS: card jumps to its page with outlined mark, page mark selects and reveals its card, in-card edit keeps list and selection, new note composed in list; mixed page sizes known up front')
    finally:
        b._state['dirty']=False;w.setVisible(False);docs.shutdown();del engine


if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
