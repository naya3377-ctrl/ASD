"""Real-QML multi-document isolation, navigation, close and resource regression.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
from pathlib import Path
import sys,time,shutil,json
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
    from bichaek.bridge import Images
    from bichaek.tabs import Documents
    root=Path(__file__).resolve().parent.parent;out=root/'test-output';out.mkdir(exist_ok=True)
    fixture=out/'Reference Manual.pdf'
    with fitz.open() as doc:
        for i in range(120):
            page=doc.new_page(width=600 if i%2==0 else 700,height=800 if i%2==0 else 950)
            page.insert_text((45,70),f'REFERENCE MANUAL / PAGE {i+1}',fontsize=20)
            if i in (37,80,119):
                page.insert_text((80,620),'Needle: precise search navigation',fontsize=18)
                if i==80:page.insert_text((80,700),'Another Needle in the same page',fontsize=18)
        doc.save(fixture)
    second=out/'Design Notes.pdf';shutil.copy2(root/'samples/sample.pdf',second)
    QQuickStyle.setStyle(os.environ.get('YOONDF_QA_STYLE','Basic'));app=QApplication([])
    QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font('korea').buffer))
    warnings=[]
    def qt_message(kind,context,message):
        if 'file:' in message or 'ReferenceError' in message or 'TypeError' in message:warnings.append(message)
    qInstallMessageHandler(qt_message)
    images=Images();documents=Documents(images);first=documents.activeBridge
    saved_auto=first.automaticOcr;first.setAutomaticOcr(False)
    errors=[];documents.showError.connect(errors.append)
    engine=QQmlApplicationEngine();engine.addImageProvider('pages',images)
    engine.rootContext().setContextProperty('bridge',first)
    engine.rootContext().setContextProperty('documents',documents)
    engine.load(QUrl.fromLocalFile(str(root/'ui/Main.qml')))
    assert engine.rootObjects(),warnings
    window=engine.rootObjects()[0];window.setProperty('uiFontFamily','Droid Sans Fallback')
    def wait(predicate,timeout=30):
        started=time.monotonic()
        while not predicate():
            app.processEvents();QTest.qWait(20)
            if time.monotonic()-started>timeout:raise AssertionError(('timeout',errors,warnings[-10:]))
        app.processEvents();QTest.qWait(80)
    def item(name):
        value=window.findChild(QObject,name)
        if value:return value
        pending=[window.contentItem()]
        while pending:
            value=pending.pop()
            if value.objectName()==name:return value
            pending.extend(value.childItems())
        raise AssertionError(name)
    def click(name):
        value=item(name);pos=value.mapToScene(value.boundingRect().center())
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,pos.toPoint());QTest.qWait(80)
    def settled():return not window.property('restoring') and not window.property('switching')
    def hit_visible(b):
        hit=b.activeSearchHit
        if not hit:return False
        try:paper=item('paper'+str(hit['page']))
        except AssertionError:return False
        pos=paper.mapToItem(item('pageList'),QPointF(hit['rect'][0]*paper.width()/b.pageWidth(hit['page']),hit['rect'][1]*paper.width()/b.pageWidth(hit['page'])))
        return 0 <= pos.y() <= item('pageList').height()-12 and 0<=pos.x()<item('pageList').width()
    try:
        documents.openPaths([str(fixture),QUrl.fromLocalFile(str(second))])
        wait(lambda:len(documents.tabs)==2 and all(b.document['count'] for b in documents._tabs) and settled())
        assert documents.activeIndex==1
        b=documents.activeBridge
        assert b.document['count']==4 and first.document['count']==120
        assert b.frames is first.frames and b.process.pid==first.process.pid
        documents.activate(0);wait(lambda:first.imageUrl(0,'main') and settled())
        window.setProperty('zoom',1.15);window.setProperty('searchOpen',True)
        search=item('searchInput');search.forceActiveFocus()
        
        for ch in 'Needle': QTest.keyClick(window,ord(ch.upper()),Qt.ShiftModifier if ch.isupper() else Qt.NoModifier)
        QTest.keyClick(window,Qt.Key_Return)
        wait(lambda:not first.searching and first.searchCount==4 and settled() and hit_visible(first))
        assert first.currentPage==37 and first.searchIndex==0,(first.currentPage,first.searchIndex)
        QTest.keyClick(window,Qt.Key_Return)
        wait(lambda:first.searchIndex==1 and first.currentPage==80 and settled() and hit_visible(first))
        QTest.keyClick(window,Qt.Key_Return)
        wait(lambda:first.searchIndex==2 and settled() and hit_visible(first))
        QTest.keyClick(window,Qt.Key_Return,Qt.ShiftModifier)
        wait(lambda:first.searchIndex==1 and settled() and hit_visible(first))
        QTest.keyClick(window,Qt.Key_F3)
        wait(lambda:first.searchIndex==2 and settled())
        click('searchResult119')
        wait(lambda:first.currentPage==119 and first.searchIndex==3 and settled() and hit_visible(first))
        QTest.keyClick(window,Qt.Key_F3)
        wait(lambda:first.currentPage==37 and first.searchIndex==0 and settled() and hit_visible(first))
        print('PASS: real Enter/Shift+Enter/F3, same-page next hit, result click, wrap, exact position on pages 38/81/120',flush=True)
        # Switch while a mutation is in flight; its response must stay in A.
        first.edit('add_text',{'page':37,'rect':[45,250,490,290],'text':'ONLY IN TAB A','size':16})
        documents.activate(1)
        wait(lambda:not first.busy and first.document['dirty'] and settled() and b.imageUrl(0,'main'))
        assert not b.document['dirty'] and b.document['count']==4
        assert window.property('zoom')==1 and not window.property('searchOpen')
        window.setProperty('zoom',.65)
        b.edit('add_text',{'page':0,'rect':[45,300,440,340],'text':'ONLY IN TAB B','size':16})
        wait(lambda:not b.busy)
        b.search('ONLY IN TAB B');wait(lambda:not b.searching and b.searchCount==1 and settled())
        documents.activate(0);wait(lambda:settled() and first.imageUrl(first.currentPage,'main'))
        assert abs(window.property('zoom')-1.15)<.01 and window.property('searchOpen')
        assert item('searchInput').property('text').lower()=='needle', (item('searchInput').property('text'),first.searchQuery,first.view_state,b.view_state)
        wait(lambda:not first.searching and first.currentPage==37 and hit_visible(first))
        first.undo();wait(lambda:not first.busy and not first.document['dirty'])
        assert b.document['dirty'],'Undo escaped into the other document'
        first.redo();wait(lambda:not first.busy and first.document['dirty'])
        first.save(False);wait(lambda:not first.busy and not first.document['dirty'])
        b.save(False);wait(lambda:not b.busy and not b.document['dirty'])
        with fitz.open(fixture) as a,fitz.open(second) as bb:
            assert 'ONLY IN TAB A' in a[37].get_text() and 'ONLY IN TAB B' not in a[0].get_text()
            assert 'ONLY IN TAB B' in bb[0].get_text() and 'ONLY IN TAB A' not in bb[0].get_text()
        documents.openPaths([str(fixture)]);assert len(documents.tabs)==2 and documents.activeIndex==0
        print('PASS: asynchronous cross-tab edits, independent undo/save, query/zoom/position restoration, duplicate file activation',flush=True)
        # Pending search in A must not navigate B; pending debounce stays with A.
        first.search('REFERENCE');documents.activate(1)
        wait(lambda:not first.searching and settled());assert b.currentPage==0
        # Open eighteen more documents without creating another PDF worker/frame pool.
        extras=[]
        for i in range(18):
            path=out/f'Project {i+1:02}.pdf';shutil.copy2(fixture,path);extras.append(str(path))
        documents.openPaths(extras)
        wait(lambda:len(documents.tabs)==20 and all(x.document['count'] and not x.busy for x in documents._tabs) and settled(),60)
        assert len({x.process.pid for x in documents._tabs})==1
        assert len({id(x.frames) for x in documents._tabs})==1
        assert len(documents.hub.frames.frames)==2
        assert images.bytes<=images.budget+images.thumb_budget
        assert all(not x._render_queue for x in documents._tabs if not x.active)
        click('openDocumentsButton')
        assert item('openDocumentsMenu').property('visible')
        # 20 documents, a separator and "close all tabs".
        assert item('openDocumentsMenu').property('count')==22, item('openDocumentsMenu').property('count')
        QTest.keyClick(window,Qt.Key_Escape);QTest.qWait(100)
        for i in [0,19,1,17,0,5,0]:documents.activate(i)
        wait(lambda:settled() and documents.activeBridge is first)
        # Keyboard tab cycle and close.
        QTest.keyClick(window,Qt.Key_Tab,Qt.ControlModifier);wait(lambda:documents.activeIndex==1 and settled())
        QTest.keyClick(window,Qt.Key_Tab,Qt.ControlModifier|Qt.ShiftModifier);wait(lambda:documents.activeIndex==0 and settled())
        documents.activate(19);wait(settled)
        QTest.keyClick(window,Qt.Key_W,Qt.ControlModifier);wait(lambda:len(documents.tabs)==19 and settled())
        print('PASS: 20 open files / 2,284 pages; one engine, two shared frames, global cache budget, rapid switch and tab shortcuts',flush=True)
        # Closing a dirty tab: cancel retains; failed save retains; successful save closes.
        documents.activate(1);wait(settled)
        b.edit('add_text',{'page':0,'rect':[45,400,440,440],'text':'CLOSE SAVE CHECK','size':14});wait(lambda:not b.busy)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Cancel):documents.closeTab(1)
        assert b in documents._tabs and b.document['dirty']
        saved_path=b._state['path'];b._state['path']=str(out/'missing-parent'/'impossible.pdf')
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Save):
            documents.closeTab(1);wait(lambda:not b.busy)
        assert b in documents._tabs and b.document['dirty'] and errors
        errors.clear();b._state['path']=saved_path
        # Dismiss expected QML error dialog before continuing keyboard tests.
        QTest.keyClick(window,Qt.Key_Escape);QTest.qWait(100)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Save):
            documents.closeTab(1);wait(lambda:b not in documents._tabs and settled())
        with fitz.open(second) as bb:assert 'CLOSE SAVE CHECK' in bb[0].get_text()
        # Close tab during active render/search; stale responses must release slots.
        owner=documents.activeBridge;owner.requestPage(0,'main',3200);owner.search('REFERENCE')
        documents.closeTab(documents.activeIndex)
        wait(lambda:not documents.hub.frames.busy and settled())
        assert not errors,errors
        assert not warnings,warnings
        # Keep a clean three-tab preview and display exact search navigation.
        while len(documents.tabs)>3:documents.closeTab(len(documents.tabs)-1)
        documents.activate(0);wait(settled)
        item('searchInput').setProperty('text','Needle');first.search('Needle')
        window.setProperty('searchOpen',True);window.setProperty('zoom',.85)
        wait(lambda:not first.searching and settled() and hit_visible(first))
        window.grabWindow().save(str(out/'tabs-040.png'))
        print('PASS: close cancel, failed save recovery, save-and-close persisted, stale render/search disposal, no QML warnings',flush=True)
        # Closing the original context controller and the last document must
        # leave a reusable blank tab, not dangling QML/worker objects.
        while len(documents.tabs)>1:
            documents.closeTab(0);wait(settled)
        documents.closeTab(0);wait(lambda:len(documents.tabs)==1 and settled())
        assert documents.activeBridge.document['count']==0
        documents.openPaths([str(fixture),str(second)])
        wait(lambda:all(x.document['count'] and not x.busy for x in documents._tabs) and settled())
        assert not warnings,warnings
        print('PASS: closing original/last tab, blank tab reuse and QML object disposal',flush=True)
        # App close scans hidden tabs too, without discarding any tab on cancel.
        hidden=documents._tabs[0]
        hidden.edit('add_text',{'page':0,'rect':[45,350,440,390],'text':'HIDDEN TAB CHANGE','size':14});wait(lambda:not hidden.busy)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Cancel):
            assert not documents.mayClose();wait(lambda:not documents.closing)
        assert hidden.document['dirty'] and hidden in documents._tabs
        approved=[];documents.closeApproved.connect(lambda:approved.append(True))
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Save):
            assert not documents.mayClose();wait(lambda:approved)
        with fitz.open(hidden.document['path']) as bb:assert 'HIDDEN TAB CHANGE' in bb[0].get_text()
        print('PASS: application close detects/saves dirty hidden tabs',flush=True)
    finally:
        documents.activeBridge.setAutomaticOcr(saved_auto)
        window.setVisible(False);documents.shutdown();del engine
        qInstallMessageHandler(None)

if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support();main()
