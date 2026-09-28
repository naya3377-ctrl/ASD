"""Tab rename QA: clicking the title of the current tab renames its file.

Enter applies, Esc cancels, clicking another tab only switches to it, and a
document with unsaved edits keeps them after the rename.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
from pathlib import Path
import sys, time
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))


def build(path, pages):
    import fitz
    doc=fitz.open()
    for index in range(pages):
        doc.new_page(width=595,height=842).insert_text((60,80),f'{path.stem} page {index+1}',fontsize=22)
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
    out=root/'test-output';out.mkdir(exist_ok=True);folder=out/'rename';import shutil;shutil.rmtree(folder,ignore_errors=True);folder.mkdir();first=folder/'첫 문서.pdf';second=folder/'둘째 문서.pdf';build(first,3);build(second,2)
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
    def tab(i): return find('documentTab%d'%i)
    from PySide6.QtGui import QGuiApplication
    slow=QGuiApplication.styleHints().mouseDoubleClickInterval()+120
    def title_click(i,pause=True):
        # A separate click, as a person makes it: after the double-click interval.
        if pause: QTest.qWait(slow)
        t=tab(i);QTest.mouseClick(w,Qt.LeftButton,Qt.NoModifier,t.mapToScene(QPointF(40,t.height()/2+3)).toPoint());QTest.qWait(60)
    try:
        docs.openPaths([str(first),str(second)])
        wait(lambda:docs.activeBridge.document['count']==2 and not docs.activeBridge.busy)
        # Clicking a tab that is not current only switches to it
        title_click(0);wait(lambda:docs.activeBridge.document['count']==3)
        assert not find('tabRenameField0').isVisible()
        # A quick double click on the current tab does not rename
        title_click(0,pause=False);QTest.qWait(40);title_click(0,pause=False);QTest.qWait(200)
        assert not find('tabRenameField0').isVisible()
        # Clicking the current tab opens the name field with the name selected
        title_click(0);field=find('tabRenameField0');wait(lambda:field.isVisible() and field.hasActiveFocus())
        assert field.property('text')=='첫 문서' and field.property('selectedText')=='첫 문서'
        # Esc cancels
        QTest.keyClick(w,Qt.Key_Escape);wait(lambda:not field.isVisible())
        assert first.exists() and w.property('workspaceMode')=='read'
        # Enter renames the file on disk; the document stays open
        title_click(0);wait(lambda:field.isVisible())
        field.setProperty('text','바뀐 이름');QTest.keyClick(w,Qt.Key_Return)
        b=docs.activeBridge;wait(lambda:not b.busy and b.document['name']=='바뀐 이름.pdf')
        assert not first.exists() and (folder/'바뀐 이름.pdf').exists() and b.document['count']==3
        wait(lambda:docs.tab_data(docs._tabs[0])['name']=='바뀐 이름.pdf' and find('documentTab0') is not None)
        # Unsaved edits survive a rename
        b.edit('delete_pages',{'pages':[2]});wait(lambda:not b.busy and b.document['dirty'] and b.document['count']==2)
        title_click(0);wait(lambda:field.isVisible());field.setProperty('text','편집 중');QTest.keyClick(w,Qt.Key_Return)
        wait(lambda:not b.busy and b.document['name']=='편집 중.pdf')
        assert b.document['dirty'] and b.document['count']==2
        # A name already taken in the folder is refused and nothing moves
        errors=[];b.showError.connect(errors.append)
        title_click(0);wait(lambda:field.isVisible());field.setProperty('text','둘째 문서');QTest.keyClick(w,Qt.Key_Return)
        wait(lambda:bool(errors) and not b.busy)
        assert b.document['name']=='편집 중.pdf' and (folder/'편집 중.pdf').exists()
        # Tab list menu: close all tabs, the window stays with an empty tab
        second_tab=[x for x in docs._tabs if x is not b][0]
        from unittest.mock import patch
        from PySide6.QtWidgets import QMessageBox
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Discard):
            docs.closeAll()
        wait(lambda:len(docs._tabs)==1 and not docs.activeBridge.document['count'])
        assert w.isVisible()
        assert not [m for m in warnings if 'Binding loop' in m or 'TypeError' in m],warnings
        print('PASS: click current tab to rename; Enter applies on disk, Esc cancels, other tabs just switch; unsaved edits kept; taken names refused; close all tabs keeps the window')
    finally:
        for bridge in list(getattr(docs,'_tabs',[])): bridge._state['dirty']=False
        w.setVisible(False);docs.shutdown();del engine


if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
